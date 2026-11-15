"""V14 audit orchestration; standalone Decimal oracle owns financial checks."""
from collections import defaultdict
from datetime import datetime,timedelta,timezone
from pathlib import Path
import numpy as np
from independent_ledger_auditor import V14LedgerOracle,swap_events,audit_v14_path
from prop_portfolio_review import checked_joint_hour
from prop_v14_source import JOB,FIRST,END,read,save
from prop_v14_paths import M1ScenarioQuotes
from quant_core.market_data_store import BAR
from quant_core.ftmo_execution_and_calendar import gold_calendar,execution_schedule

HOUR=3600000


def audit_accounts(expected,trades,readers,calendar,first=FIRST,end=END):
    cases=[V14LedgerOracle(e,trades) for e in expected]
    actions=defaultdict(list)
    for i,t in enumerate(trades):
        actions[(t["entry_msc"],0 if t["asset"]=="XAUUSD" else 1,t["entry_quote_index"])].append(("entry",i,None,None))
    for j,c in enumerate(cases):
        for i in c.accepted:
            t=c.trades[i]
            if first<=t["exit_msc"]<end and t["exit_quote_index"]>=0:
                actions[(t["exit_msc"],0 if t["asset"]=="XAUUSD" else 1,t["exit_quote_index"])].append(("exit",i,j,None))
            for at,_ in swap_events(t["entry_msc"],min(end-1,t["exit_msc"]),t["asset"]):
                if first<=at<end:actions[(at,-1,-1)].append(("swap",i,j,None))
        for kind,key in (("pass","phase_passes"),("reward","payouts")):
            for event in c.e[key]:
                closed=next((r for r in c.e["closed"] if r["at"]==event["at"]),None)
                t=c.trades[closed["trade"]] if closed else None
                key=(event["at"],0 if t["asset"]=="XAUUSD" else 1,t["exit_quote_index"]) if t else (event["at"],-1,-1)
                actions[key].append((kind,None,j,event))
    from zoneinfo import ZoneInfo
    day=datetime.fromtimestamp(first/1000,timezone.utc).date()
    final=datetime.fromtimestamp(end/1000,timezone.utc).date()+timedelta(days=1)
    while day<=final:
        reset=int(datetime.combine(day,datetime.min.time(),ZoneInfo("Europe/Prague")).timestamp()*1000)
        if first<=reset<end:actions[(reset,-1,-1)].append(("reset",None,None,None))
        row=calendar.events.get(day.isoformat(),{})
        if day.weekday()<5 and row.get("kind")!="CLOSED":
            h,m=map(int,(row.get("flat_utc") or "20:30").split(":"))
            at=int(datetime(day.year,day.month,day.day,h,m,tzinfo=timezone.utc).timestamp()*1000)
            if first<=at<end:actions[(at,-1,-1)].append(("session_flat",None,None,None))
        day+=timedelta(days=1)
    keys=sorted(actions);cursor=0;last=None
    priority=dict(reset=0,swap=1,session_flat=2,exit=3,**{"pass":4},reward=5,entry=6)
    def consume(rows):
        nonlocal last
        if not len(rows):return
        cache={}
        for c in cases:
            if c.e["start_msc"]<=int(rows["t"][0]) and int(rows["t"][-1])<c.e["end_msc"]:
                c.segment(rows,cache)
        last=rows[-1]
    for hour in range(first//HOUR*HOUR,end,HOUR):
        rows,maps=checked_joint_hour(readers,hour,last);start=0
        while cursor<len(keys) and keys[cursor][0]<hour+HOUR:
            at,asset,index=keys[cursor]
            stop=int(rows["t"].searchsorted(at)) if asset<0 else int(maps[asset][index])
            consume(rows[start:stop])
            if asset>=0:
                last=rows[stop]
                for c in cases:
                    if c.e["start_msc"]<=at<c.e["end_msc"]:c.point(at,last)
            for kind,i,j,extra in sorted(actions[keys[cursor]],key=lambda a:priority[a[0]]):
                for c in cases if j is None else [cases[j]]:
                    if kind=="exit" and i in c.pending and i in c.closed and c.closed[i].get("execution_override"):
                        t=c.trades[i];request=c.pending[i][0];reader=readers[t["asset"]]
                        found=False
                        for h in range(request//HOUR*HOUR,at//HOUR*HOUR+1,HOUR):
                            q=reader.hour(h) if h in reader.files else []
                            if not len(q):continue
                            n=int(q["t"].searchsorted(request,side="right"))
                            if n<len(q):
                                field="b" if t["side"]=="BUY" else "a"
                                if (int(q["t"][n]),int(q[field][n]),n)!=(at,t["exit_price_units"],t["exit_quote_index"]):
                                    raise ValueError("V14_audit_forced_exit_not_next_quote")
                                found=True;break
                        if not found:raise ValueError("V14_audit_forced_exit_missing")
                    c.action(kind,i,at,last,extra)
            start=stop;cursor+=1
        consume(rows[start:])
        if hour%(5000*HOUR)==0:print(dict(stage="V14_independent_accounts",hour=hour,accounts=len(cases)),flush=True)
    if cursor!=len(keys):raise ValueError("V14_audit_unconsumed_events")
    return [c.finish() for c in cases]


def run(tag):
    order="OPEN_LOW_HIGH_CLOSE" if tag=="OLHC" else "OPEN_HIGH_LOW_CLOSE"
    proofs=read(JOB/"full-source-admission.json")["assets"]
    bars={a:np.memmap(p["path"],mode="r",dtype=BAR) for a,p in proofs.items()}
    calendar=gold_calendar(FIRST,END);schedule=execution_schedule(FIRST,END)
    trades=read(JOB/f"{tag}-strategy-trades.json")
    paths=[]
    for i,t in enumerate(trades):
        r=audit_v14_path(t,bars[t["asset"]],schedule.events,END)
        if not r["passed"]:raise ValueError(f"V14_independent_path:{i}:{r}")
        paths.append(r)
    save(f"{tag}-independent-path-audit.json",dict(passed=True,paths=paths,
        scope="same implementer/feed; scalar Decimal oracle for conditional M1 order, not native tick certification"))
    readers={a:M1ScenarioQuotes(b,order,FIRST,END) for a,b in bars.items()}
    for t in trades:
        if not t["censored"]:
            spread=int(bars[t["asset"]]["ao"][0]-bars[t["asset"]]["bo"][0])
            bid=t["exit_price_units"] if t["side"]=="BUY" else t["exit_price_units"]-spread
            readers[t["asset"]].add(t["exit_msc"],bid,bid+spread)
    cfg=read(JOB/"candidate-freeze.json")
    for candidate in ("A","B"):
        for view in ("NEXT_QUOTE","CLEAN_COHORT"):
            selected=[t for t in trades if t["id"] in cfg["candidate_"+candidate] and
                (view=="NEXT_QUOTE" or not t["source_uncertain"])]
            expected=read(JOB/f"{tag}-{candidate}-{view}-accounts.json")
            result=audit_accounts(expected,selected,readers,calendar)
            save(f"{tag}-{candidate}-{view}-independent-account-audit.json",dict(passed=True,
                accounts=len(result),records=result,same_implementer_and_feed=True))
            print(dict(stage="V14_account_audit_PASS",tag=tag,candidate=candidate,view=view,accounts=len(result)),flush=True)


def development():
    from prop_v14_source import V13,DEV_END
    from prop_v14_paths import build
    from quant_core.gap_aware_execution import GapAwarePathIndex
    cfg=read(JOB/"development.json");chosen=cfg["candidates"]["B"]["selected"]
    rows={r["id"]:r for r in read(V13/"discovery.json")["rows"]}
    bars={a:np.memmap(JOB/f"{a}-Dev-M1.bin",dtype=BAR,mode="r") for a in ("XAUUSD","EURUSD")}
    schedule=execution_schedule(FIRST,DEV_END);measurements={}
    for asset,b in bars.items():
        z=np.load(JOB/f"{asset}-Dev-paths.npz")
        ix=GapAwarePathIndex(b,asset=asset,schedule=schedule)
        for identity in chosen:
            if not identity.startswith(asset+"|"):continue
            j=rows[identity]["source_cell"]
            m={k:z[f"{j}:{k}"] for k in ("at","entry_at","side","entry_price","stop","natural",
                "friction","ratio","years","deadline","admitted")}
            m.update(asset=asset,_index=ix);measurements[identity]=m
    for order in ("OPEN_LOW_HIGH_CLOSE","OPEN_HIGH_LOW_CLOSE"):
        trades,readers,missing=build(measurements,order,bars)
        errors=[]
        for i,t in enumerate(trades):
            r=audit_v14_path(t,bars[t["asset"]],schedule.events,END)
            if not r["passed"]:errors.append(dict(i=i,id=t["id"],audit=r))
        name=f"Dev-rehearsal2-{order}.json"
        save(name,dict(trades=len(trades),missing=missing,errors=errors))
        print(dict(stage="V14_Dev_path_rehearsal",order=order,trades=len(trades),errors=errors[:4]),flush=True)
        if errors:raise ValueError("V14_Dev_path_audit")


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("tag",choices=("OLHC","OHLC","development"))
    arg=p.parse_args().tag
    development() if arg=="development" else run(arg)

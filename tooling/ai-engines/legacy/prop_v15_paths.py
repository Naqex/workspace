"""Shared synthetic gap excursions, preserving the frozen exogenous signal tape."""
from collections import defaultdict,Counter
import hashlib
import numpy as np
from prop_v15_common import *
from prop_v15_evidence import bars_for
from prop_v14_paths import M1ScenarioQuotes,build
from quant_core.market_data_store import BAR
from quant_core.gap_aware_execution import GapAwarePathIndex
from quant_core.ftmo_execution_and_calendar import execution_schedule
from quant_core.prop_lifecycle_and_parity import bindings


def patch_plan(rows,mode):
    selected=[]
    for r in rows:
        if not r["source_uncertain"] or r["first_unknown"] is None:continue
        if mode=="PRIMARY" and r["screen"]["status"] in ("SOURCE_ENVELOPE_EXCLUDES_SL","MODEL_LOW_RISK"):
            continue
        selected.append(r)
    groups=defaultdict(list)
    for r in selected:groups[r["asset"],r["first_unknown"]].append(r)
    return [dict(asset=a,at=at,targets=[dict(id=r["id"],entry=r["entry"],exit=r["exit"],
        side=r["side"],level=r["level"],before=r["before"],after=r["after"]) for r in targets])
        for (a,at),targets in sorted(groups.items())]


def insert_excursions(bars,patches,asset,end):
    synthetic=[]
    times=bars["t"];spread=338 if asset=="XAUUSD" else 10
    for p in patches:
        if p["asset"]!=asset or not FIRST<=p["at"]<end:continue
        at=p["at"];j=int(times.searchsorted(at))
        if j==0 or j==len(bars) or times[j]==at:raise ValueError("V15_patch_not_between_observed_bars")
        opening=int(bars["bc"][j-1]);closing=int(bars["bo"][j])
        low=min([opening,closing]+[t["level"]-1 for t in p["targets"] if t["side"]==1])
        high=max([opening,closing]+[t["level"]-spread+1 for t in p["targets"] if t["side"]==-1])
        r=np.zeros(1,dtype=BAR);r["t"]=at
        for n,v in zip("ohlc",(opening,high,low,closing)):
            r["b"+n]=v;r["a"+n]=v+spread
        synthetic.append(r)
    if not synthetic:return bars,0
    data=np.concatenate([bars,*synthetic])
    data.sort(order="t")
    if np.any(np.diff(data["t"])<=0):raise ValueError("V15_duplicate_stress_timestamp")
    # Exact preservation of every originally observed row, not just hashes of metadata.
    if not np.array_equal(data[np.searchsorted(data["t"],times)],bars):raise ValueError("V15_observed_prices_changed")
    return data,len(synthetic)


def bind_quotes(trades,readers):
    for t in trades:
        for which in ("entry","exit"):
            if which=="exit" and t["censored"]:t["exit_quote_index"]=-1;continue
            at=t[which+"_msc"];q=readers[t["asset"]].hour(at//3600000*3600000)
            field="a" if (which=="entry" and t["side"]=="BUY") or (which=="exit" and t["side"]=="SELL") else "b"
            positions=np.flatnonzero((q["t"]==at)&(q[field]==t[which+"_price_units"]))
            if not len(positions):raise ValueError("V15_quote_binding")
            t[which+"_quote_index"]=int(positions[0])


def readers_for(bars,trades,order,dev,original=None):
    end=DEV_END if dev else END
    readers={a:M1ScenarioQuotes(b,order,FIRST,end) for a,b in bars.items()}
    original=original or []
    injected=set()
    for parent,stream in ((True,original),(False,trades)):
        for t in stream:
            if t["censored"] or not FIRST<=t["exit_msc"]<end:continue
            spread=338 if t["asset"]=="XAUUSD" else 10
            bid=t["exit_price_units"] if t["side"]=="BUY" else t["exit_price_units"]-spread
            key=(t["asset"],t["exit_msc"],bid)
            # Preserve old duplicates for the common original quote grid.
            if key in injected and not parent:continue
            readers[t["asset"]].add(t["exit_msc"],bid,bid+spread);injected.add(key)
    bind_quotes(trades,readers)
    return readers


def prepare(tag,dev,mode="PRIMARY"):
    stage="Dev" if dev else "Full";end=DEV_END if dev else END
    order="OPEN_LOW_HIGH_CLOSE" if tag=="OLHC" else "OPEN_HIGH_LOW_CLOSE"
    cfg=read(V14/"candidate-freeze.json")
    original=read(V14/f"{tag}-strategy-trades.json")
    original=[t for t in original if FIRST<=t["decision_msc"]<end]
    core=[t for t in original if t["id"] in cfg["candidate_A"]]
    evidence=read(JOB/"bridge-evidence.json")
    rows=[r for r in evidence["rows"] if r["entry"]<end]
    plan=patch_plan(rows,mode)
    bars={};measurements={};lookup={}
    schedule=execution_schedule(FIRST,end)
    for asset in ("XAUUSD","EURUSD"):
        raw=bars_for(asset,dev)
        data,count=insert_excursions(raw,plan,asset,end);bars[asset]=data
        ix=GapAwarePathIndex(data,asset=asset,schedule=schedule)
        for identity in cfg["candidate_A"]:
            if not identity.startswith(asset+"|"):continue
            ts=sorted([t for t in core if t["id"]==identity],key=lambda t:t["decision_msc"])
            m={name:np.array([t[field] for t in ts],dtype="int64") for name,field in (
                ("at","decision_msc"),("entry_at","entry_msc"),("entry_price","entry_price_units"),
                ("stop","stop_units"),("deadline","deadline_msc"))}
            m.update(side=np.array([1 if t["side"]=="BUY" else -1 for t in ts],dtype="int8"),
                natural=np.array([t["natural"] for t in ts]),admitted=np.ones(len(ts),dtype=bool),
                asset=asset,_index=ix)
            measurements[identity]=m;lookup[identity]=ts
        if count:
            p=JOB/f"{stage}-{mode}-{asset}-stress-M1.bin"
            if p.exists():
                if sha(p)!=hashlib.sha256(data.tobytes()).hexdigest():raise ValueError("V15_shared_source_drift")
            else:
                with p.open("xb") as f:data.tofile(f)
    if plan:
        import prop_v14_paths as parent_paths
        with bindings(parent_paths,END=end):
            trades,_,missing=build(measurements,order,bars)
    else:
        # The fixed primary screen can select no bridges. Reuse the exact tape;
        # repeating a financial first-passage calculation adds no evidence.
        trades=[dict(t) for t in core];missing=[]
        for t in trades:t["source_event"]=lookup[t["id"]].index(
            next(r for r in lookup[t["id"]] if r["source_event"]==t["source_event"]))
    if missing:raise ValueError("V15_frozen_tape_replay_missing:"+str(missing[:3]))
    for t in trades:
        old=lookup[t["id"]][t["source_event"]]
        t.update(parent_source_event=old["source_event"],original_source_uncertain=old["source_uncertain"],
            scenario_remaining_source_gaps=t["source_uncertain"],synthetic_bridge_stress=bool(plan),
            original_exit=old["exit_msc"],original_reason=old["reason"],source_model="V15_SHARED_SYNTHETIC_GAP_STRESS")
        t["source_uncertain"]=bool(t["source_uncertain"] or old["source_uncertain"])
    readers=readers_for(bars,trades,order,dev,original)
    save(f"{stage}-{tag}-{mode}-trades.json",trades)
    save(f"{stage}-{tag}-{mode}-path-receipt.json",dict(signals=len(trades),patches=plan,
        synthetic_bars={a:len(bars[a])-len(bars_for(a,dev)) for a in bars},
        original_signals=len(core),no_signal_dropped=len(core)==len(trades),observed_bars_unchanged=True,
        changed_exits=sum(t["exit_msc"]!=t["original_exit"] or t["reason"]!=t["original_reason"] for t in trades),
        exits=dict(Counter(t["reason"] for t in trades)),
        mathematical_lower_bound=False,source_certified=False,
        paths={a:dict(path=str(JOB/f"{stage}-{mode}-{a}-stress-M1.bin"),
            sha256=sha(JOB/f"{stage}-{mode}-{a}-stress-M1.bin"))
            if any(p["asset"]==a and FIRST<=p["at"]<end for p in plan) else
            read(V14/("source-dev-admission.json" if dev else "full-source-admission.json"))["assets"][a]
            for a in bars}))
    event("V15_paths_ready",stage_scope=stage,order=tag,mode=mode,signals=len(trades),patches=len(plan))
    return trades,readers,bars


def load(tag,dev,mode="PRIMARY"):
    stage="Dev" if dev else "Full"
    trades=read(JOB/f"{stage}-{tag}-{mode}-trades.json")
    receipt=read(JOB/f"{stage}-{tag}-{mode}-path-receipt.json")
    bars={}
    for a,p in receipt["paths"].items():
        if sha(p["path"])!=p["sha256"]:raise ValueError("V15_synthetic_source_drift")
        bars[a]=np.memmap(p["path"],dtype=BAR,mode="r")
    original=read(V14/f"{tag}-strategy-trades.json")
    original=[t for t in original if t["decision_msc"]<(DEV_END if dev else END)]
    order="OPEN_LOW_HIGH_CLOSE" if tag=="OLHC" else "OPEN_HIGH_LOW_CLOSE"
    readers=readers_for(bars,trades,order,dev,original)
    return trades,readers,bars


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("tag",choices=("OLHC","OHLC"))
    p.add_argument("--full",action="store_true");p.add_argument("--mode",choices=("PRIMARY","ALL_UNCERTIFIED"),default="PRIMARY")
    a=p.parse_args();prepare(a.tag,not a.full,a.mode)

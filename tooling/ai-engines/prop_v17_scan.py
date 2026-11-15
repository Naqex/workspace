"""The registered503 DAY cells, with one causal07:00 entry fence and scalar audit."""
from collections import Counter
from datetime import datetime,timezone
from decimal import Decimal as D
import numpy as np
import independent_ledger_auditor as oracle
import prop_v14_paths as paths
from prop_v17_common import *
from prop_v16_scan import measurement,load_bars,bars_for
from prop_v16_paths import CausalFlatSchedule
from quant_core.gap_aware_execution import GapAwarePathIndex
from quant_core.ftmo_execution_and_calendar import gold_calendar
from quant_core.vectorized_sl_active_kernel import money
from quant_core.prop_lifecycle_and_parity import bindings

DAY=86400000


def session_measurement(archive,row,schedule):
    m=measurement(archive,row);asset=row["asset"]
    ends=np.array([schedule.cutoff(int(t),asset) for t in m["entry_at"]])
    use=((m["entry_at"]>=m["at"])&(m["entry_at"]-m["at"]<=60000)&
        (m["entry_at"]%DAY>=7*3600000)&(m["entry_at"]<ends)&
        (m["at"]>=FIRST)&(m["at"]<DEV_END)&(((m["entry_at"]//DAY+3)%7)<5))
    result={k:(v[use] if isinstance(v,np.ndarray) and len(v)==len(use) else v) for k,v in m.items()}
    result["deadline"]=ends[use]
    return result,int((~use).sum())


def tier_profile(days):
    weights=read(JOB/"tier-selection.json")["tiers"]
    profile=np.zeros(len(days))
    for t in read(V16/"Dev-OLHC-PRIMARY-trades.json"):
        if t["entry_msc"]//DAY!=t["exit_msc"]//DAY:raise ValueError("V17_reference_profile_requires_MTM")
        at=int(days.searchsorted(t["exit_msc"]//DAY))
        if at<len(days) and days[at]==t["exit_msc"]//DAY:
            profile[at]+=weights[t["id"]]*t["reference"]["SYM"]["net_R"]
    return profile


def endpoints(m,bars):
    asset=m["asset"];indices=bars["t"].searchsorted(m["deadline"])
    valid=indices<len(bars);safe=np.minimum(indices,len(bars)-1)
    side=m["side"];px=np.where(side==1,bars["bo"][safe],bars["ao"][safe])
    net=money(asset,"SYM",side,m["entry_price"],px,m["entry_at"],bars["t"][safe],
        np.full(len(safe),"HORIZON"))["net"]
    scale=1000 if asset in ("XAUUSD","US500") else 100000
    contract=100 if asset=="XAUUSD" else 1 if asset=="US500" else 100000
    # Own Decimal cash accounting checks every raw endpoint, not only selected wins.
    for i,j in enumerate(safe):
        t=dict(symbol=asset,direction="BUY" if side[i]==1 else "SELL",lots="1",
            entry_price=str(D(int(m["entry_price"][i]))/scale),exit_price=str(D(int(px[i]))/scale),
            entry_time=int(m["entry_at"][i]),exit_time=int(bars["t"][j]),reason="HORIZON")
        expected=float(oracle.cash_legs(t,"SYM",dict(contract=contract))["net"]/contract)
        if abs(expected-net[i])>1e-8:raise ValueError("V17_independent_endpoint_cash")
    return net/m["natural"],bool(valid.all())


def register():
    parent=read(V16/"scan-registration.json")
    ids=[i for i in parent["ids"] if i.split("|")[0] in ("XAUUSD","EURUSD","US500")]
    if len(ids)!=503:raise ValueError("V17_registered_budget_drift")
    save("scan-registration.json",dict(ids=ids,cells=len(ids),per_asset=dict(Counter(i.split("|")[0] for i in ids)),
        parent_sha256=sha(V16/"scan-registration.json"),protocol_sha256=sha(PROTOCOL),
        entry_start_UTC="07:00",same_recipes_and_costs=True,whole_candidate_gap_gate=True))
    event("V17_scan_registered",cells=len(ids))


def run(asset):
    wanted=set(read(JOB/"scan-registration.json")["ids"])
    rows=[r for r in read(V12/"cent-corrected/discovery.json")["rows"] if r["id"] in wanted and r["asset"]==asset]
    bars=bars_for(asset,True) if asset!="US500" else load_bars(asset,read(V11/"source-admission-v11.json"))
    calendar=gold_calendar(FIRST,DEV_END);schedule=CausalFlatSchedule(calendar.events.values())
    index=GapAwarePathIndex(bars,asset=asset,schedule=schedule)
    archive=np.load(V12/("cent-corrected" if asset=="US500" else "")/f"{asset}-path-matrix.npz")
    days=np.arange(FIRST//DAY,DEV_END//DAY);days=days[(days+3)%7<5]
    base=tier_profile(days);cache={};out=[];packs={"OLHC":[],"OHLC":[]};profiles={};checks=0
    for row in rows:
        cell=row["source_cell"]
        if cell not in cache:
            m,skipped=session_measurement(archive,row,schedule);m["_index"]=index
            endpoint,available=endpoints(m,bars);checks+=len(endpoint)
            clusters=[]
            for first,last in ((2018,2020),(2021,2023)):
                raw=(m["years"]>=first)&(m["years"]<=last);admit=raw&m["admitted"]
                clusters.append(dict(years=[first,last],raw=int(raw.sum()),admitted=int(admit.sum()),
                    retention=float(admit.sum()/raw.sum()) if raw.any() else 0.,
                    scale_ratio=float(np.median(m["friction"][raw])/np.median(m["natural"][raw])) if raw.any() else None,
                    unconditional_endpoint_R=float(endpoint[raw].sum()),endpoint_R=float(endpoint[admit].sum())))
            passed=available and all(c["endpoint_R"]>0 and c["retention"]>=.5 and
                c["scale_ratio"] is not None and c["scale_ratio"]<=.15 for c in clusters)
            cache[cell]=m,skipped,clusters,passed
        m,skipped,clusters,passed=cache[cell]
        record=dict(id=row["id"],asset=asset,family=row["family"],mode=row["mode"],
            skipped_by_known_clock=skipped,stage0_clusters=clusters,stage0_passed=passed)
        if not passed:
            out.append(dict(record,status="STAGE0_ECONOMIC_OR_SCALE_FAIL"));continue
        reasons=set();orders=[];profile=None
        for tag,order in (("OLHC","OPEN_LOW_HIGH_CLOSE"),("OHLC","OPEN_HIGH_LOW_CLOSE")):
            with bindings(paths,END=DEV_END):trades,_,missing=paths.build({row["id"]:m},order,{asset:bars})
            if missing:reasons.add("UNRESOLVED_ENTRY_OR_ENDPOINT")
            for t in trades:
                if asset=="US500":t["scale"]=1000
                check=oracle.audit_v14_path(t,bars,calendar.events,DEV_END,scheduled_override=t["deadline_msc"])
                if not check["passed"]:raise ValueError("V17_independent_path:"+str(check))
            packs[tag]+=trades
            unknown=sum(t["source_uncertain"] for t in trades)
            overnight=sum(t["entry_msc"]//DAY!=t["exit_msc"]//DAY for t in trades)
            cl=[sum(t["reference"]["SYM"]["net_R"] for t in trades
                if first<=datetime.fromtimestamp(t["decision_msc"]/1000,timezone.utc).year<=last)
                for first,last in ((2018,2020),(2021,2023))]
            mean=sum(t["reference"]["SYM"]["net_R"] for t in trades)/len(trades) if trades else None
            daily=np.zeros(len(days))
            for t in trades:
                j=int(days.searchsorted(t["exit_msc"]//DAY))
                if j<len(days):daily[j]+=t["reference"]["SYM"]["net_R"]
            corr=float(np.corrcoef(daily,base)[0,1]) if daily.std()>0 and base.std()>0 else None
            if unknown:reasons.add("SOURCE_UNCERTIFIED_GAPS")
            if overnight:reasons.add("OVERNIGHT_FILL")
            if min(cl)<=0:reasons.add("SL_ACTIVE_ECONOMIC_FAIL")
            if len(trades)/6<40:reasons.add("CADENCE_BELOW40_PER_YEAR")
            if mean is None or mean<.04:reasons.add("MEAN_BELOW004")
            if corr is None or abs(corr)>=.20:reasons.add("CORRELATION")
            orders.append(dict(order=tag,trades=len(trades),cluster_SYM_R=cl,mean_SYM_R=mean,
                source_unknown=unknown,overnight=overnight,correlation=corr))
            if tag=="OLHC":profile=daily
        record.update(status="REJECTED" if reasons else "ELIGIBLE",reasons=sorted(reasons),orders=orders,
            rank=min(v for r in orders for v in r["cluster_SYM_R"])/3)
        out.append(record)
        if not reasons:profiles[row["id"]]=profile
    for tag,trades in packs.items():save(f"{asset}-{tag}-path-pack.json",dict(trades=trades,conditional_M1=True))
    save(f"{asset}-scan.json",dict(rows=out,outcomes=dict(Counter(r["status"] for r in out)),
        eligible=list(profiles),endpoint_cash_checks=checks,
        scalar_paths=sum(len(t) for t in packs.values()),source_gap_records=index.audit["source_uncertain_gaps"],
        no_future_gap_trade_filter=True,same_implementer_and_feed=True))
    np.savez_compressed(JOB/f"{asset}-eligible-profile.npz",days=days,**profiles)
    event("V17_scan_complete",asset=asset,cases=len(rows),eligible=len(profiles),endpoint_checks=checks)


def select():
    all_rows=[];profiles={}
    for asset in ("XAUUSD","EURUSD","US500"):
        all_rows+=read(JOB/f"{asset}-scan.json")["rows"]
        z=np.load(JOB/f"{asset}-eligible-profile.npz");profiles.update({k:z[k] for k in z.files if k!="days"})
    eligible=sorted([r for r in all_rows if r["status"]=="ELIGIBLE"],key=lambda r:(-r["rank"],r["id"]))
    chosen=[]
    for r in eligible:
        if any((p["asset"],p["family"])==(r["asset"],r["family"]) for p in chosen):continue
        if any(abs(float(np.corrcoef(profiles[p["id"]],profiles[r["id"]])[0,1]))>=.2 for p in chosen):continue
        chosen.append(r)
        if len(chosen)==2:break
    save("selection.json",dict(selected=chosen,eligible=len(eligible),cases=len(all_rows),
        status="EMPTY_ADDITIONS" if not chosen else "ADAPTER_REVIEW_REQUIRED"))
    event("V17_selection",selected=[r["id"] for r in chosen])


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("stage",choices=("register","select","XAUUSD","EURUSD","US500"))
    stage=p.parse_args().stage
    globals()[stage]() if stage in ("register","select") else run(stage)

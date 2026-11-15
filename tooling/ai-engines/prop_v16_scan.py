"""Re-screen the existing DAY catalogue under one causal intraday deadline."""
from collections import Counter
import subprocess
import numpy as np
from prop_v16_common import *
from prop_v16_paths import CausalFlatSchedule
from prop_v15_evidence import bars_for
from prop_v12_campaign import load_bars
from quant_core.ftmo_execution_and_calendar import gold_calendar
from quant_core.gap_aware_execution import GapAwarePathIndex,replay_gap_aware
from quant_core.vectorized_sl_active_kernel import money
from quant_core.vectorized_stage0_scanner import DAY


def closed_daily(trades,days):
    out=np.zeros(len(days))
    for t in trades:
        at=min(t["exit_msc"],DEV_END-1)//DAY
        j=int(days.searchsorted(at))
        if j<len(days) and days[j]==at:out[j]+=t["reference"]["SYM"]["net_R"]
    return out


def measurement(archive,row):
    j=row["source_cell"]
    m={k:archive[f"{j}:{k}"] for k in ("at","entry_at","side","entry_price","stop",
        "natural","friction","ratio","years","deadline","admitted")}
    m.update(asset=row["asset"],recipe=row["recipe"],family=row["family"],horizon="DAY")
    m["admitted"]=m["ratio"]<=.15
    return m


def register():
    all_rows=read(V12/"cent-corrected/discovery.json")["rows"]
    cfg=read(V14/"candidate-freeze.json")
    clones={tuple(i.split("|")[:2]) for i in cfg["candidate_A"]}
    day=[r for r in all_rows if r["horizon"]=="DAY"]
    excluded=[r["id"] for r in day if tuple(r["id"].split("|")[:2]) in clones]
    ids=[r["id"] for r in day if r["id"] not in excluded]
    save("scan-registration.json",dict(parent_sha256=sha(V12/"cent-corrected/discovery.json"),
        original_DAY_budget=len(day),excluded_A_mechanism_clones=excluded,ids=ids,
        cases=len(ids),per_asset=dict(Counter(i.split("|")[0] for i in ids)),
        commit=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
        protocol_sha256=sha(PROTOCOL),new_exit_grid=False,development_only=True))
    event("V16_scan_registered",cases=len(ids),excluded=len(excluded))


def run(asset):
    registration=read(JOB/"scan-registration.json");wanted=set(registration["ids"])
    rows=[r for r in read(V12/"cent-corrected/discovery.json")["rows"]
        if r["id"] in wanted and r["asset"]==asset]
    if asset in ("GBPUSD","AUDUSD"):
        # Sparse observed endpoint hours cannot cover six years of stop-active paths.
        census=read(JOB/"raw-source-census.json")
        fine=[r for r in census["records"] if asset.lower() in r["path"].lower() and
            Path(r["path"]).suffix in (".ticks",".bi5",".csv",".parquet")]
        save(f"{asset}-scan.json",dict(asset=asset,rows=[dict(id=r["id"],
            status="DATA_PATH_INCOMPLETE",reason="Admitted six-year source is H1 only; fine fixtures are sparse/outside period, never padded.")
            for r in rows],fine_source_candidates=fine,eligible=[],
            H1_is_not_M1=True,synthetic_minutes=0))
        event("V16_source_resolution_gate",asset=asset,cases=len(rows),status="DATA_PATH_INCOMPLETE")
        return
    bars=(bars_for(asset,True) if asset in ("XAUUSD","EURUSD") else
        load_bars(asset,read(V11/"source-admission-v11.json")))
    schedule=CausalFlatSchedule(gold_calendar(FIRST,DEV_END).events.values())
    index=GapAwarePathIndex(bars,asset=asset,schedule=schedule)
    source=dict(records=len(bars),first=int(bars["t"][0]),last=int(bars["t"][-1]),
        audit=index.audit,existing_source_admission="V14" if asset!="US500" else "V11 accepted quarterly source")
    source_name=f"{asset}-scan-source.json"
    if not (JOB/source_name).exists():save(source_name,source)
    elif read(JOB/source_name)!=source:raise ValueError("V16_source_resume_drift")
    matrices=np.load(V12/("cent-corrected" if asset=="US500" else "")/f"{asset}-path-matrix.npz")
    # Correlation is a diagnostic on daily closed R; all retained components must be same-day.
    days=np.arange(FIRST//DAY,DEV_END//DAY)
    days=days[(days+3)%7<5]
    core=read(JOB/"Dev-OLHC-PRIMARY-trades.json")
    if any(t["entry_msc"]//DAY!=t["exit_msc"]//DAY for t in core):
        raise ValueError("V16_A_daily_profile_requires_MTM_for_overnight")
    base=closed_daily(core,days)
    cache={};out=[];candidates={};cost_rows={}
    for n,row in enumerate(rows):
        j=row["source_cell"]
        if j not in cache:
            m=measurement(matrices,row)
            cutoff=np.array([schedule.cutoff(int(t),asset) for t in m["entry_at"]])
            guard=((m["entry_at"]>=m["at"])&(m["entry_at"]-m["at"]<=60000)&
                (m["entry_at"]<cutoff)&(m["at"]>=FIRST)&(m["at"]<DEV_END)&
                (((m["entry_at"]//DAY+3)%7)<5))
            m={k:(v[guard] if isinstance(v,np.ndarray) and len(v)==len(guard) else v) for k,v in m.items()}
            m["deadline"]=cutoff[guard];m["_index"]=index
            # Endpoint screen uses only a forward observed quote at the known cutoff.
            ix=bars["t"].searchsorted(m["deadline"]);available=ix<len(bars)
            safe=np.minimum(ix,len(bars)-1)
            px=np.where(m["side"]==1,bars["bo"][safe],bars["ao"][safe])
            values=money(asset,"SYM",m["side"],m["entry_price"],px,m["entry_at"],
                bars["t"][safe],np.full(len(safe),"HORIZON"))["net"]
            endpoint_R=values/m["natural"];admit=m["admitted"]
            clusters=[]
            for first,last in ((2018,2020),(2021,2023)):
                q=(m["years"]>=first)&(m["years"]<=last)
                use=q&admit;retention=use.sum()/q.sum() if q.any() else 0
                scale=float(np.median(m["friction"][q])/np.median(m["natural"][q])) if q.any() else None
                clusters.append(dict(years=[first,last],raw=int(q.sum()),admitted=int(use.sum()),
                    retention=float(retention),scale_ratio=scale,endpoint_R=float(endpoint_R[use].sum())))
            stage0=all(c["endpoint_R"]>0 and c["retention"]>=.5 and
                c["scale_ratio"] is not None and c["scale_ratio"]<=.15 for c in clusters) and bool(available.all())
            cache[j]=(m,clusters,stage0,int((~guard).sum()))
        m,clusters,stage0,skip=cache[j]
        record=dict(id=row["id"],asset=asset,family=row["family"],mode=row["mode"],
            pre_entry_clock_skips=skip,stage0_clusters=clusters,stage0_passed=stage0)
        if not stage0:
            out.append(dict(record,status="STAGE0_ECONOMIC_OR_SCALE_FAIL"));continue
        r=replay_gap_aware(index,m,row["mode"])
        use=m["admitted"];priced=r["valid"]&use
        net={c:r["model"][c]["net_R"] for c in ("SYM","ASYM")}
        cl=[float(net["SYM"][priced&(m["years"]>=first)&(m["years"]<=last)].sum())
            for first,last in ((2018,2020),(2021,2023))]
        unknown=int((r["source_uncertain"]&use).sum())
        overnight=int((use&(r["exit_at"]//DAY!=m["entry_at"]//DAY)).sum())
        profile=np.zeros(len(days))
        ix=days.searchsorted(r["exit_at"][priced]//DAY)
        ok=ix<len(days)
        np.add.at(profile,ix[ok],net["SYM"][priced][ok])
        correlation=float(np.corrcoef(profile,base)[0,1]) if profile.std()>0 and base.std()>0 else None
        reasons=[]
        if not bool(r["valid"][use].all()):reasons.append("ENDPOINT_UNRESOLVED")
        if unknown:reasons.append("SOURCE_UNCERTIFIED_GAPS")
        if overnight:reasons.append("OVERNIGHT_EXECUTION")
        if min(cl)<=0:reasons.append("SL_ACTIVE_ECONOMIC_FAIL")
        if int(priced.sum())/6<40:reasons.append("CADENCE_BELOW40_PER_YEAR")
        mean=float(net["SYM"][priced].mean()) if priced.any() else None
        if mean is None or mean<.04:reasons.append("MEAN_BELOW004")
        if correlation is None or abs(correlation)>=.20:reasons.append("CORRELATION")
        record.update(status="ELIGIBLE" if not reasons else "REJECTED",reasons=reasons,
            trades=int(priced.sum()),annual_cadence=float(priced.sum()/6),cluster_SYM_R=cl,
            mean_SYM_R=mean,net_R={c:float(net[c][priced].sum()) for c in net},
            source_unknown=unknown,overnight=overnight,correlation_with_A=correlation,
            rank=min(cl)/3,annual=[dict(year=y,trades=int((priced&(m["years"]==y)).sum()),
                SYM_R=float(net["SYM"][priced&(m["years"]==y)].sum())) for y in range(2018,2024)])
        out.append(record)
        if not reasons:candidates[row["id"]]=profile
        if n%20==0:event("V16_scan_progress",asset=asset,cases=n+1,total=len(rows))
    save(f"{asset}-scan.json",dict(asset=asset,rows=out,eligible=list(candidates),
        outcomes=dict(Counter(r["status"] for r in out)),source_gaps=index.audit["source_uncertain_gaps"]))
    np.savez_compressed(JOB/f"{asset}-eligible-daily.npz",days=days,**candidates)
    event("V16_scan_complete",asset=asset,cases=len(out),eligible=len(candidates),
        outcomes=dict(Counter(r["status"] for r in out)))


def select():
    rows=[]
    for asset in ("XAUUSD","EURUSD","US500","GBPUSD","AUDUSD"):
        rows+=read(JOB/f"{asset}-scan.json")["rows"]
    eligible=sorted([r for r in rows if r["status"]=="ELIGIBLE"],key=lambda r:(-r["rank"],r["id"]))
    profiles={}
    for a in ("XAUUSD","EURUSD","US500"):
        z=np.load(JOB/f"{a}-eligible-daily.npz")
        profiles.update({k:z[k] for k in z.files if k!="days"})
    selected=[]
    for row in eligible:
        if any((r["asset"],r["family"])==(row["asset"],row["family"]) for r in selected):continue
        if any(abs(float(np.corrcoef(profiles[r["id"]],profiles[row["id"]])[0,1]))>=.2 for r in selected):continue
        selected.append(row)
        if len(selected)==2:break
    save("selection.json",dict(selected=selected,eligible=len(eligible),cases=len(rows),
        status="NO_ADDITION_QUALIFIED" if not selected else "SELECTED_PENDING_INDEPENDENT_AUDIT",
        A_Dev_source_unknown=read(JOB/"Dev-OLHC-PRIMARY-path-receipt.json")["source_uncertain"],
        zero_gap_A_qualified=read(JOB/"Dev-OLHC-PRIMARY-path-receipt.json")["source_uncertain"]==0))
    event("V16_Dev_selection",eligible=len(eligible),selected=[r["id"] for r in selected])


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("stage",choices=("register","select","XAUUSD","EURUSD","US500","GBPUSD","AUDUSD"))
    a=p.parse_args().stage
    globals()[a]() if a in ("register","select") else run(a)

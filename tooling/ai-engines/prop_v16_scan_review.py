"""Independent Decimal endpoints and scalar checks of every SL-active scan path."""
from collections import Counter
from decimal import Decimal as D
import numpy as np
import independent_ledger_auditor as oracle
import prop_v14_paths as producer
from prop_v16_common import *
from prop_v16_scan import measurement,load_bars,bars_for
from prop_v16_paths import CausalFlatSchedule
from quant_core.ftmo_execution_and_calendar import gold_calendar
from quant_core.gap_aware_execution import GapAwarePathIndex
from quant_core.prop_lifecycle_and_parity import bindings

DAY=86400000


def run(label=""):
    prefix=label+"-" if label else ""
    counts=Counter();receipts=[];errors=[]
    calendar=gold_calendar(FIRST,DEV_END)
    for asset in ("XAUUSD","EURUSD","US500"):
        rows=read(JOB/f"{asset}-scan.json")["rows"]
        inputs={r["id"]:r for r in read(V12/"cent-corrected/discovery.json")["rows"]}
        archive=np.load(V12/("cent-corrected" if asset=="US500" else "")/f"{asset}-path-matrix.npz")
        bars=bars_for(asset,True) if asset!="US500" else load_bars(asset,read(V11/"source-admission-v11.json"))
        schedule=CausalFlatSchedule(calendar.events.values())
        index=GapAwarePathIndex(bars,asset=asset,schedule=schedule)
        cache={};path_ms={}
        scale=1000 if asset in ("XAUUSD","US500") else 100000
        contract=100 if asset=="XAUUSD" else 1 if asset=="US500" else 100000
        for row in rows:
            original=inputs[row["id"]];cell=original["source_cell"]
            if cell not in cache:
                m=measurement(archive,original)
                deadlines=np.array([oracle.v16_causal_cutoff(int(e),2**62,asset,calendar.events) for e in m["entry_at"]])
                guard=((m["entry_at"]>=m["at"])&(m["entry_at"]-m["at"]<=60000)&
                    (m["entry_at"]<deadlines)&(m["at"]>=FIRST)&(m["at"]<DEV_END)&
                    (((m["entry_at"]//DAY+3)%7)<5))
                m={k:(v[guard] if isinstance(v,np.ndarray) and len(v)==len(guard) else v) for k,v in m.items()}
                m.update(deadline=deadlines[guard],_index=index)
                indices=bars["t"].searchsorted(m["deadline"])
                endpoint_R=[]
                for i,j in enumerate(indices):
                    if j>=len(bars):raise ValueError("V16_audit_missing_endpoint")
                    side=int(m["side"][i]);px=int(bars["bo" if side==1 else "ao"][j])
                    trade=dict(symbol=asset,direction="BUY" if side==1 else "SELL",lots="1",
                        entry_time=int(m["entry_at"][i]),exit_time=int(bars["t"][j]),
                        entry_price=str(D(int(m["entry_price"][i]))/scale),
                        exit_price=str(D(px)/scale),reason="HORIZON")
                    net=oracle.cash_legs(trade,"SYM",dict(contract=contract))["net"]
                    endpoint_R.append(float(net/contract/D(str(m["natural"][i]))))
                endpoint_R=np.array(endpoint_R);clusters=[]
                for first,last in ((2018,2020),(2021,2023)):
                    raw=(m["years"]>=first)&(m["years"]<=last);admit=raw&m["admitted"]
                    clusters.append(dict(years=[first,last],raw=int(raw.sum()),admitted=int(admit.sum()),
                        retention=float(admit.sum()/raw.sum()) if raw.any() else 0.,
                        scale_ratio=float(np.median(m["friction"][raw])/np.median(m["natural"][raw])) if raw.any() else None,
                        endpoint_R=float(endpoint_R[admit].sum())))
                cache[cell]=(m,clusters)
                counts["endpoint_cash_legs"]+=len(endpoint_R)
            m,clusters=cache[cell]
            for a,b in zip(clusters,row["stage0_clusters"]):
                for k in a:
                    if isinstance(a[k],float):
                        if abs(a[k]-b[k])>1e-7:errors.append(dict(id=row["id"],field=k,oracle=a[k],producer=b[k]))
                    elif a[k]!=b[k]:errors.append(dict(id=row["id"],field=k))
            positive=all(c["endpoint_R"]>0 and c["retention"]>=.5 and c["scale_ratio"] is not None and c["scale_ratio"]<=.15 for c in clusters)
            if positive!=row["stage0_passed"]:errors.append(dict(id=row["id"],field="STAGE0_VERDICT"))
            if positive:path_ms[row["id"]]=m
            counts["cells"]+=1
        for tag,order in (("OLHC","OPEN_LOW_HIGH_CLOSE"),("OHLC","OPEN_HIGH_LOW_CLOSE")):
            with bindings(producer,END=DEV_END):
                trades,_,missing=producer.build(path_ms,order,{asset:bars}) if path_ms else ([],{},[])
            if missing:raise ValueError("V16_scan_missing_paths:"+str(missing[:3]))
            by_id={}
            for t in trades:
                audit=oracle.audit_v14_path(t,bars,calendar.events,DEV_END,
                    scheduled_override=t["deadline_msc"])
                if not audit["passed"]:errors.append(dict(id=t["id"],event=t["source_event"],audit=audit))
                by_id.setdefault(t["id"],[]).append(t);counts["scalar_paths"]+=1
            for row in rows:
                if not row["stage0_passed"]:continue
                selected=by_id.get(row["id"],[])
                if len(selected)!=row["trades"] or sum(t["source_uncertain"] for t in selected)!=row["source_unknown"]:
                    errors.append(dict(id=row["id"],field="PATH_COUNTS"))
                for cost in ("SYM","ASYM"):
                    net=sum(t["reference"][cost]["net_R"] for t in selected)
                    if abs(net-row["net_R"][cost])>1e-7:errors.append(dict(id=row["id"],field="SL_ACTIVE_NET",cost=cost,oracle=net,producer=row["net_R"][cost]))
            name=f"{prefix}{asset}-{tag}-scan-path-audit-pack.json"
            save(name,dict(trades=trades,conditional_order=order,
                native_intraminute_certificate=False))
            receipts.append(dict(asset=asset,order=tag,paths=len(trades),pack=name,sha256=sha(JOB/name)))
        event("V16_scan_asset_audited",asset=asset,cells=len(rows),SL_active_cells=len(path_ms),errors=len(errors))
    for asset in ("GBPUSD","AUDUSD"):
        rows=read(JOB/f"{asset}-scan.json")["rows"]
        if any(r["status"]!="DATA_PATH_INCOMPLETE" for r in rows):raise ValueError("V16_H1_only_promoted")
        counts["source_resolution_excluded_cells"]+=len(rows)
    save(prefix+"scan-independent-audit.json",dict(passed=not errors,counts=dict(counts),errors=errors,
        path_packs=receipts,independent_Decimal_cash=True,independent_scalar_paths=True,
        same_implementer_and_feed=True,all_eligible_candidates=0))
    if errors:raise ValueError("V16_scan_audit:"+str(errors[:3]))
    event("V16_scan_audit_PASS",counts=dict(counts))


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("--label",default="")
    run(p.parse_args().label)

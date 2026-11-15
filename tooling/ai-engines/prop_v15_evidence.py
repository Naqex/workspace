"""Frozen V14 duration/attribution census and admitted native-quote envelopes."""
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
from statistics import median
import re
import numpy as np
from prop_v15_common import *
from prop_v14_source import csv_window
from quant_core.market_data_store import BAR
from quant_core.gap_aware_execution import GapAwarePathIndex
from quant_core.ftmo_execution_and_calendar import execution_schedule

MINUTE=60000


def classify_bridge(side,level,before,after,minutes,sigma,adjacent_range,envelope,*,first,end):
    distances=np.array([before-level,after-level])*side
    minimum=int(distances.min())
    complete=(envelope.get("available") and envelope.get("complete_export_assumption") and
        not envelope.get("derived_from_gappy_M1",True) and
        envelope.get("origin") in ("RECORDED_NATIVE_TICK_ENVELOPE","PROVIDER_NATIVE_HTF") and
        envelope["first"]<=first and end<=envelope["end"])
    extreme=envelope.get("bid_low" if side==1 else "ask_high")
    excluded=bool(complete and extreme is not None and side*(extreme-level)>0 and minimum>0)
    valid=sigma is not None and np.isfinite(sigma) and sigma>0
    threshold=float(3*sigma*np.sqrt(minutes)) if valid else None
    log_p=float(-2.*distances[0]*distances[1]/(sigma**2*minutes)) if valid and minimum>0 else (0. if minimum<=0 else None)
    low=bool(valid and minimum>0 and minimum>max(threshold,2*adjacent_range))
    status=("ENDPOINT_TOUCH_OR_BEYOND_STOP" if minimum<=0 else "SOURCE_ENVELOPE_EXCLUDES_SL" if excluded
        else "MODEL_LOW_RISK" if low else "AMBIGUOUS")
    return dict(status=status,signed_distances=distances.tolist(),minimum_distance=minimum,
        sigma_threshold=threshold,adjacent_threshold=2*adjacent_range,model_log_hit_probability=log_p,
        model_hit_probability=float(np.exp(max(log_p,-745))) if log_p is not None else None,
        conditional_source_exclusion=excluded,market_certificate=False,deterministic_bound=False)


def bars_for(asset,dev=False):
    name="source-dev-admission.json" if dev else "full-source-admission.json"
    proof=read(V14/name)["assets"][asset]
    if sha(proof["path"])!=proof["sha256"]:raise ValueError("V15_parent_source_drift")
    return np.memmap(proof["path"],mode="r",dtype=BAR)


def duration_group(trades):
    hours=[(t["exit_msc"]-t["entry_msc"])/3600000 for t in trades]
    return dict(trades=len(trades),median_hours=median(hours) if hours else None,
        wins=sum(t["reference"]["SYM"]["net_R"]>0 for t in trades),
        losses=sum(t["reference"]["SYM"]["net_R"]<0 for t in trades),
        SYM_net_R=sum(t["reference"]["SYM"]["net_R"] for t in trades),
        exits=dict(Counter(t["reason"] for t in trades)))


class NativeEnvelopes:
    """Bounded raw tick reads; a complete-export assumption remains explicit."""
    def __init__(self):
        census=read(V14/"raw-source-census.json")
        self.stats={r["path"].replace("\\","/"):r for r in census["records"]}
        self.hashes=read(V14/"source-dev-admission.json")["native_csv_hashes"]
        self.cache={};self.proofs={};self.lookups=[]

    def source(self,asset,at):
        if asset!="EURUSD":return None
        y=datetime.fromtimestamp(at/1000,timezone.utc).year
        if y<=2023:
            folder=ROOT/f"eurusd-observed-history-v2/{y}/attempt-1"
            p=folder/"export/EURUSD_TICK_TW-TICK-No Session.csv"
            if not p.exists():return None
            receipt=read(folder/"export-command.json")
            digest=self.hashes.get(str(p))
        elif y>=2025:
            folder=ROOT/"prop-v4-harvest-v6-20261115/export-EURUSD"
            receipt=read(folder/"receipt.json");p=Path(receipt["path"]);digest=receipt["sha256"]
        else:return None
        if "timezone=UTC" not in receipt["argv"] or "timeframe=TICK" not in receipt["argv"]:
            raise ValueError("V15_native_clock_or_timeframe")
        if str(p) not in self.proofs:
            stat=p.stat();prior=self.stats.get(p.as_posix(),{})
            reuse=digest and stat.st_size==prior.get("bytes") and stat.st_mtime_ns==prior.get("mtime_ns")
            current=digest if reuse else sha(p)
            if digest and current!=digest:raise ValueError("V15_native_tick_drift")
            self.proofs[str(p)]=dict(sha256=current,bytes=stat.st_size,mtime_ns=stat.st_mtime_ns,
                sha_reused_under_unchanged_census_stat=bool(reuse),UTC=True,kind="NATIVE_TICK_EXPORT",
                coverage_assumption="export contains all recorded provider ticks; not all market/broker prices")
        return p

    def get(self,asset,before,after):
        key=(asset,before,after)
        if key in self.cache:return self.cache[key]
        p=self.source(asset,before)
        result=dict(available=False,market_certificate=False,origin="NO_ADMITTED_HTF")
        if p is not None:
            for minutes in (5,15,60,240):
                step=minutes*MINUTE
                first=(before+MINUTE)//step*step
                end=(after-1)//step*step+step
                if end-first>step:continue
                low=datetime.fromtimestamp(first/1000,timezone.utc).strftime("%Y%m%d %H:%M:%S").encode()
                high=datetime.fromtimestamp(end/1000,timezone.utc).strftime("%Y%m%d %H:%M:%S").encode()
                header,values=csv_window(p,low,high)
                if header!=["DateTime","Bid","Ask","Volume"]:raise ValueError("V15_native_schema")
                if not values:continue
                quotes=[]
                for v in values:
                    at=int(datetime.strptime(v[0],"%Y%m%d %H:%M:%S.%f").replace(tzinfo=timezone.utc).timestamp()*1000)
                    bid,ask=(int(round(float(x)*100000)) for x in v[1:3])
                    if ask<bid or bid<=0:raise ValueError("V15_native_side")
                    quotes.append((at,bid,ask))
                result=dict(available=True,market_certificate=False,origin="RECORDED_NATIVE_TICK_ENVELOPE",
                    path=str(p),source_sha256=self.proofs[str(p)]["sha256"],minutes=minutes,
                    first=first,end=end,bid_low=min(q[1] for q in quotes),ask_high=max(
                        max(q[2],q[1]+10) for q in quotes),
                    quotes=len(quotes),quotes_in_gap=sum(before+MINUTE<=q[0]<after for q in quotes),
                    complete_export_assumption=True,derived_from_gappy_M1=False)
                break
        self.cache[key]=result
        self.lookups.append(dict(asset=asset,before=before,after=after,**result))
        return result


def attribution(trades,ids):
    out=[]
    for identity in ids:
        selected=sorted([t for t in trades if t["id"]==identity],key=lambda t:t["exit_msc"])
        annual=[]
        for y in range(2018,2027):
            rows=[t for t in selected if datetime.fromtimestamp(t["decision_msc"]/1000,timezone.utc).year==y]
            annual.append(dict(year=y,trades=len(rows),BUY=sum(t["side"]=="BUY" for t in rows),
                SELL=sum(t["side"]=="SELL" for t in rows),models={m:sum(t["reference"][m]["net_R"] for t in rows)
                                                              for m in ("SYM","ASYM")}))
        models={}
        for model in ("SYM","ASYM"):
            v=np.array([t["reference"][model]["net_R"] for t in selected])
            curve=np.r_[0,np.cumsum(v)]
            models[model]=dict(total_R=float(v.sum()),closed_R_DD=float((np.maximum.accumulate(curve)-curve).max()),
                validation_R=sum(a["models"][model] for a in annual if a["year"]>=2024))
        out.append(dict(id=identity,asset=identity.split("|")[0],family=identity.split("|")[1][:2],
            horizon=identity.split("|")[-2],mode=identity.split("|")[-1],annual=annual,models=models,
            DD_scope="exit-time cumulative unit-R; floating sleeve DD reported separately if measured"))
    return out


def run():
    cfg=read(V14/"candidate-freeze.json")
    all_trades=read(V14/"OLHC-strategy-trades.json")
    core=[t for t in all_trades if t["id"] in cfg["candidate_A"]]
    native=NativeEnvelopes();rows=[];source_audits={}
    schedule=execution_schedule(FIRST,END)
    for asset in ("XAUUSD","EURUSD"):
        bars=bars_for(asset)
        ix=GapAwarePathIndex(bars,asset=asset,schedule=schedule)
        source_audits[asset]=ix.audit
        gaps=ix.gaps
        for n,t in enumerate(core):
            if t["asset"]!=asset:continue
            crossed=[g for g in gaps if g["after"]>t["entry_msc"] and g["before"]<t["exit_msc"]]
            for g in crossed:
                i,j=map(int,bars["t"].searchsorted([g["before"],g["after"]]))
                side=1 if t["side"]=="BUY" else -1
                level=t["stop_units"]
                first_unknown=next((at for at in range(g["before"]+MINUTE,g["after"],MINUTE)
                    if schedule.off_kind(at,asset) is None),None)
                if t["activation_time"] is not None and first_unknown is not None and t["activation_time"]<=first_unknown:
                    level=t["protection_price"]
                p0=int(bars["bc" if side==1 else "ac"][i]);p1=int(bars["bo" if side==1 else "ao"][j])
                left=max(1,i-240)
                delta=np.diff(bars["bc"][left-1:i+1].astype("int64"))
                valid=np.diff(bars["t"][left-1:i+1])==MINUTE
                observed=delta[valid]
                sigma=float(observed.std(ddof=1)) if len(observed)>=60 else None
                adjacent=max(int(bars["bh"][i]-bars["bl"][i]),int(bars["bh"][j]-bars["bl"][j]))
                envelope=native.get(asset,g["before"],g["after"]) if g["source_uncertain"] else dict(available=False)
                screen=classify_bridge(side,level,p0,p1,g["missing"],sigma,adjacent,envelope,
                    first=g["before"]+MINUTE,end=g["after"])
                rows.append(dict(trade=n,id=t["id"],asset=asset,entry=t["entry_msc"],exit=t["exit_msc"],
                    before=g["before"],after=g["after"],missing_minutes=g["missing"],
                    minutes_by_kind=g["minutes_by_kind"],source_uncertain=g["source_uncertain"],
                    first_unknown=first_unknown,level=level,side=side,before_price=p0,after_price=p1,
                    sigma_prior=sigma,sigma_increment_count=len(observed),adjacent_range=adjacent,
                    envelope=envelope,screen=screen))
        event("V15_bridge_asset",asset=asset,gap_occurrences=sum(r["asset"]==asset for r in rows))
    groups={}
    for period,lo,hi in (("DEV",FIRST,DEV_END),("VALIDATION",DEV_END,END)):
        ts=[t for t in core if lo<=t["decision_msc"]<hi]
        groups[period]={k:duration_group([t for t in ts if t["source_uncertain"]==flag])
            for k,flag in (("NO_UNKNOWN_GAP",False),("UNKNOWN_GAP",True))}
        strata=[]
        for a,b in ((0,3),(3,8),(8,24),(24,48),(48,1000)):
            subset=[t for t in ts if a<=(t["exit_msc"]-t["entry_msc"])/3600000<b]
            strata.append(dict(hours=[a,b],trades=len(subset),uncertain=sum(t["source_uncertain"] for t in subset)))
        groups[period]["duration_strata"]=strata
    save("bridge-evidence.json",dict(groups=groups,rows=rows,native_sources=native.proofs,
        native_envelopes=native.lookups,source_audits=source_audits,
        source_certificate=False,closed_world_native_envelope_only=True,
        Brownian_is_statistical_model=True,protocol_sha256=sha(PROTOCOL)))
    save("sleeve-attribution.json",dict(rows=attribution(all_trades,cfg["candidate_B"]),
        parent_source=V14.as_posix(),B_retired=True))
    event("V15_evidence_complete",groups=groups,unknown_occurrences=sum(r["source_uncertain"] for r in rows),
        screens=dict(Counter(r["screen"]["status"] for r in rows if r["source_uncertain"])))


if __name__=="__main__":run()

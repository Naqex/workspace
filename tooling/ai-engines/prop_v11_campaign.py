"""V11 selection from immutable V10 Development endpoints; no validation price reads."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib
import json
import subprocess
import argparse
from zoneinfo import ZoneInfo
import numpy as np

from prop_campaign_source import ROOT
from prop_v10_source import FIRST,END,sha
from quant_core.zero_tuning_ensemble import mechanical_composition,cumulative_drawdown
from quant_core.native_hourly_source import PairedHourlyStore,native_recipes,IndexedUs500Store
from quant_core.ftmo_execution_and_calendar import gold_calendar
from quant_core.vectorized_stage0_scanner import measure,summaries,daily_statistics
from prop_v10_signals import recipes as m1_recipes

JOB=ROOT/"ensemble-and-storage-v11-20261115"
OLD=ROOT/"enterprise-alpha-v10-20261115"
PROTOCOL=Path("planning/research/ENSEMBLE-AND-STORAGE-V11-PROTOCOL-20261115.md")
DAY=86400000
CORRECT_INDEX_CLOCK=False


def save(name,value):
    p=JOB/name
    if p.exists():
        raise ValueError("preserve_V11_attempt:"+name)
    p.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding="utf-8")


def key(row):
    return row["asset"]+"|"+row["recipe"]+"|"+row["horizon"]


def component_reasons(row):
    reasons=[]
    for c in row["clusters"]:
        if c["retention"]<.5: reasons.append(f'{c["years"][0]}:RETAIN_BELOW50')
        if c["scale_ratio"] is None or c["scale_ratio"]>.15: reasons.append(f'{c["years"][0]}:SCALE')
        if min(c["net"]["SYM"].values())<=0: reasons.append(f'{c["years"][0]}:RAW_OR_ADMITTED_NONPOSITIVE')
    if sum(a["priced"] for a in row["annual"])!=sum(a["raw"] for a in row["annual"]):
        reasons.append("ENDPOINT_INCOMPLETE")
    n=sum(a["admitted"] for a in row["annual"])
    total=sum(a["economics"]["SYM"]["admitted_net_R"] for a in row["annual"])
    if not n or total/n<.04: reasons.append("MEAN_NET_R_BELOW004")
    return reasons


def us500_proxy(rows,bars):
    for m in rows:
        entries=bars["t"].searchsorted(m["entry_at"])
        m["friction"]=(bars["ao"][entries]-bars["bo"][entries])/1000+2.5
        m["ratio"]=np.divide(m["friction"],m["natural"],out=np.full(len(entries),np.inf),where=m["natural"]>0)
        m["admitted"]=m["ok"]&(m["ratio"]<=.15)
        for money in m["model"].values():
            money["commission"]=np.ones(len(entries))
            money["other"]=1.5
            money["funding_multipliers"]=np.maximum(m["exit_at"]//DAY-m["entry_at"]//DAY,0)
            money["funding"]=-2.*money["funding_multipliers"]
            money["net"]=money["gross"]-2.5+money["funding"]
            money["net_R"]=np.divide(money["net"],m["natural"],out=np.zeros(len(entries)),where=m["natural"]>0)
    return rows


def us500_source_clock(rows,bars):
    """Port V3's declared source break repair; never search for a profitable exit."""
    ny=ZoneInfo("America/New_York")
    for m in rows:
        target=m["deadline"].copy()
        changed=np.zeros(len(target),dtype=bool)
        for i,at in enumerate(target):
            local=datetime.fromtimestamp(int(at)/1000,timezone.utc).astimezone(ny)
            if 16*60+15<=local.hour*60+local.minute<18*60:
                target[i]=int(local.replace(hour=16,minute=0,second=0,microsecond=0).timestamp()*1000)
                changed[i]=True
        indices=bars["t"].searchsorted(target)
        safe=np.minimum(indices,len(bars)-1)
        end=bars["t"][safe]
        weekday=(m["entry_at"]//DAY+3)%7
        valid=((m["entry_at"]-m["at"]>=0)&(m["entry_at"]-m["at"]<=60000)&
               (m["natural"]>0)&(m["at"]>=FIRST)&(m["at"]<END)&
               ~((weekday==4)&(m["entry_at"]%DAY>=73800000))&
               (target>=m["entry_at"])&(indices<len(bars))&(end-target<=60000)&
               (end>=target)&(target<END))
        m.update(deadline=target,exit_at=end,ok=valid,source_session_clamp=changed)
        m["exit_price"]=np.where(m["side"]==1,bars["bo"][safe],bars["ao"][safe])
        gross=np.where(m["side"]==1,1,-1)*(m["exit_price"]-m["entry_price"])/1000
        for money in m["model"].values(): money["gross"]=gross.copy()
    return rows


def run():
    inputs=("discovery-reviewed.json","raw-matrix-reviewed.npz","daily-R.npz")
    files=[PROTOCOL,PROTOCOL.with_name("ENSEMBLE-AND-STORAGE-V11-SOURCE-ADDENDUM-20261115.md"),
           Path(__file__),Path(__file__).with_name("quant_core")/"zero_tuning_ensemble.py",
           Path(__file__).with_name("quant_core")/"native_hourly_source.py",
           Path(__file__).with_name("prop_v10_signals.py"),
           Path(__file__).with_name("quant_core")/"vectorized_stage0_scanner.py",
           Path(__file__).with_name("quant_core")/"market_data_store.py",
           Path(__file__).with_name("us500_year_source.py")]
    if CORRECT_INDEX_CLOCK:
        files.append(PROTOCOL.with_name("ENSEMBLE-AND-STORAGE-V11-CLOCK-CORRECTION-20261115.md"))
    index=json.loads((JOB/"source-admission-v11.json").read_text())
    trials=544+sum(368 if a=="US500" else 176 for a in index["new_assets_admitted"])
    save("selection-registration.json",dict(
        utc=datetime.now(timezone.utc).isoformat(),commit=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
        code={str(p):sha(p) for p in files},parent={f:sha(OLD/f) for f in inputs},
        source_index_sha256=sha(JOB/"source-admission-v11.json"),trials=trials,
        protocol="V11 after V10 exposure, changed component/ensemble gates",
        US500_source_clock_corrected=CORRECT_INDEX_CLOCK,
        validation_prices_opened=False,subset_search=False))
    original=json.loads((OLD/"discovery-reviewed.json").read_text())
    matrix=np.load(OLD/"raw-matrix-reviewed.npz")
    native_measurements,audits=[],{}
    calendar=gold_calendar(FIRST,END)
    for asset in index["new_assets_admitted"]:
        print(dict(stage="V11_native_source_start",asset=asset),flush=True)
        store=(IndexedUs500Store(index["minute_indices"][asset],index["seed"],END) if asset=="US500"
               else PairedHourlyStore(index["hourly_indices"][asset],index["seed"],END))
        bars=store.bars()
        print(dict(stage="V11_native_source_loaded",asset=asset,rows=len(bars)),flush=True)
        raw=(m1_recipes(bars,"XAUUSD",FIRST,END,calendar) if asset=="US500"
             else native_recipes(bars,asset,FIRST,END,calendar))
        if len(raw)!=(92 if asset=="US500" else 44): raise ValueError("native_grid_budget_changed")
        start=len(native_measurements)
        for recipe in raw:
            # Same USD-quoted FX stress/lot units; retain actual asset label after summary.
            rows=measure("XAUUSD" if asset=="US500" else "EURUSD",recipe,bars,calendar,FIRST,END)
            if asset=="US500":
                if CORRECT_INDEX_CLOCK: us500_source_clock(rows,bars)
                us500_proxy(rows,bars)
            native_measurements.extend(rows)
        audits[asset]=dict(store.audit,measurement_rows=[start,len(native_measurements)],
                           execution_cost_alias="US500_LEGACY_ATLAS_STRESS" if asset=="US500"
                           else "EURUSD_USD_QUOTED_FX_DECLARED_PROXY")
        audits[asset]["source_clock_clamped_records"]=sum(int(m.get("source_session_clamp",np.zeros(0)).sum())
            for m in native_measurements[start:])
        print(dict(stage="V11_native_measurements",asset=asset,cells=len(native_measurements)-start),flush=True)
    extra=[]
    if native_measurements:
        extra,_=summaries(native_measurements,FIRST,END,trials)
        for asset,audit in audits.items():
            lo,hi=audit["measurement_rows"]
            for i in range(lo,hi):
                extra[i]["asset"]=asset
                if asset=="US500":
                    for annual_ in extra[i]["annual"]:
                        for money in annual_["economics"].values():
                            if money["per_lot_net"] is not None: money["per_lot_net"]/=100
                native_measurements[i]["asset"]=asset
        packed={}
        for j,m in enumerate(native_measurements):
            for field in ("at","entry_at","exit_at","deadline","side","entry_price","exit_price",
                          "stop","natural","friction","ratio","ok","admitted","years"):
                packed[f"{j}:{field}"]=m[field]
            if "source_session_clamp" in m:
                packed[f"{j}:source_session_clamp"]=m["source_session_clamp"]
            for model in ("SYM","ASYM"):
                for field in ("gross","commission","funding","funding_multipliers","net","net_R"):
                    packed[f"{j}:{model}:{field}"]=m["model"][model][field]
        np.savez_compressed(JOB/"native-hourly-matrix.npz",**packed)
        save("native-hourly-source-audit.json",audits)
        save("native-hourly-discovery.json",dict(rows=extra,trials=trials,SL_active=False))
    all_rows=original["rows"]+extra
    if len(all_rows)!=trials: raise ValueError("V11_trial_budget_changed")
    days=np.arange(FIRST//DAY,END//DAY)
    days=days[(days+3)%7<5]
    enriched,components,series,raw_profiles={},[],{},[]
    for j,row in enumerate(all_rows):
        if j<544:
            get=lambda field:matrix[f"{j}:{field}"]
        else:
            m=native_measurements[j-544]
            def get(field):
                if ":" in field:
                    model,name=field.split(":",1)
                    return m["model"][model][name]
                return m[field]
        at,ok,admitted=get("at"),get("ok"),get("admitted")
        daily={}
        money={}
        for model in ("SYM","ASYM"):
            values=get(model+":net_R")
            profile=np.zeros(len(days))
            np.add.at(profile,days.searchsorted(at[admitted]//DAY),values[admitted])
            daily[model]=profile
            money[model]=dict(net_R=float(values[admitted].sum()),
                mean_R=float(values[admitted].mean()) if admitted.any() else None,
                endpoint_R_DD=cumulative_drawdown(profile))
        raw_daily=np.zeros(len(days))
        np.add.at(raw_daily,days.searchsorted(at[ok]//DAY),get("SYM:net_R")[ok])
        raw_profiles.append(raw_daily)
        n=int(admitted.sum())
        rejects=component_reasons(row)
        dual=all(c["net"]["SYM"]["raw"]>0 and c["retention"]>=.5 for c in row["clusters"])
        details=dict(row,id=key(row),direction="BOTH",dual_cluster_positive=dual,
            origin="V10" if j<544 else "V11_NATIVE_H1",
            V10_rejection_reasons=row["reasons"] if j<544 else None,
            component_admitted=not rejects,component_reasons=rejects,economics=money,
            raw_endpoint_R_DD=cumulative_drawdown(raw_daily),
            trades_year=[dict(year=a["year"],raw=a["raw"],admitted=a["admitted"]) for a in row["annual"]],
            trades_per_year=n/6,
            missing_trades_for_V10=[max(0,60-c["admitted"]) for c in row["clusters"]],
            SYM_missing_positive_years_for_V10=max(0,4-sum(a["economics"]["SYM"]["raw_net_R"]>0 for a in row["annual"])))
        enriched[key(row)]=details
        series[key(row)]=daily
        if not rejects:
            components.append(dict(id=key(row),asset=row["asset"],family=row["family"],
                                   daily=raw_daily,events=at))
    statistics=daily_statistics(np.asarray(raw_profiles),trials)
    for j,row in enumerate(enriched.values()):
        row["V11_statistics"]={k:float(v[j]) if isinstance(v,np.ndarray) else v for k,v in statistics.items()}
    composition=mechanical_composition(components)
    selected=composition["selected"]
    profiles={m:sum((series[k][m] for k in selected),np.zeros(len(days))) for m in ("SYM","ASYM")}
    annual=[]
    for year in range(2018,2024):
        date_mask=days.astype("datetime64[D]").astype("datetime64[Y]").astype(int)+1970==year
        count=sum(next(a["admitted"] for a in enriched[k]["annual"] if a["year"]==year) for k in selected)
        annual.append(dict(year=year,trades=count,models={m:dict(net_R=float(p[date_mask].sum()),
            endpoint_R_DD=cumulative_drawdown(p[date_mask])) for m,p in profiles.items()}))
    reasons=[]
    if not 3<=len(selected)<=8: reasons.append("K_OUTSIDE3_8")
    for years in ((2018,2019,2020),(2021,2022,2023)):
        group=[a for a in annual if a["year"] in years]
        if sum(a["trades"] for a in group)<150: reasons.append(f"{years[0]}:ENSEMBLE_CADENCE_BELOW50")
        for model in ("SYM","ASYM"):
            for cohort in ("raw","admitted"):
                total=sum(c["net"][model][cohort] for k in selected for c in enriched[k]["clusters"]
                          if c["years"][0]==years[0])
                if total<=0: reasons.append(f"{years[0]}:{model}:{cohort}:CLUSTER_NONPOSITIVE")
    metrics={}
    for model,p in profiles.items():
        dd=cumulative_drawdown(p)
        ratio=float(p.sum()/dd) if dd else None
        metrics[model]=dict(net_R=float(p.sum()),endpoint_R_DD=dd,netR_DD_ratio=ratio)
        if sum(a["models"][model]["net_R"]>0 for a in annual)<5:
            reasons.append(model+":ENSEMBLE_FEWER_THAN5_POSITIVE_YEARS")
    ratios=[enriched[k]["economics"]["SYM"]["net_R"]/enriched[k]["economics"]["SYM"]["endpoint_R_DD"]
            for k in selected if enriched[k]["economics"]["SYM"]["endpoint_R_DD"]>0]
    if not ratios or metrics["SYM"]["netR_DD_ratio"] is None or metrics["SYM"]["netR_DD_ratio"]<=max(ratios):
        reasons.append("EFFICIENCY_NOT_ABOVE_EVERY_COMPONENT")
    decision=dict(stage="DEVELOPMENT_ENDPOINT_ENSEMBLE",component_count=len(components),K=len(selected),
        selected=selected,passed=not reasons,reasons=reasons,metrics=metrics,annual=annual,
        actual_SL_path_complete=False,composition=None,validation="CLOSED_PENDING_DEV_PATH_AND_COMMIT",
        lifecycle="NOT_RUN",clean_OOS=False)
    if reasons:
        decision.update(validation="CANCELED_FAILED_DEV_ENSEMBLE",lifecycle="CANCELED_FAILED_DEV_ENSEMBLE")
    save("component-atlas.json",dict(rows=list(enriched.values()),
        dual_positive=[r for r in enriched.values() if r["dual_cluster_positive"]],
        V10_top15=[enriched[key(r)] for r in original["top15"]],
        candidates=[enriched[r["id"]] for r in components],
        selection=composition,decision=decision,trials=trials))
    np.savez_compressed(JOB/"ensemble-development-profiles.npz",days=days,
        **{m:profiles[m] for m in profiles},
        **{f"{j}:{m}":series[k][m] for j,k in enumerate(selected) for m in profiles})
    save("decision.json",decision)
    print(dict(dual_positive=sum(r["dual_cluster_positive"] for r in enriched.values()),
               admitted=len(components),selected=len(selected),passed=not reasons,reasons=reasons),flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt",choices=("initial","clock-corrected"),default="initial")
    args=parser.parse_args()
    if args.attempt=="clock-corrected":
        JOB=JOB/"clock-corrected"
        JOB.mkdir(exist_ok=True)
        CORRECT_INDEX_CLOCK=True
    run()

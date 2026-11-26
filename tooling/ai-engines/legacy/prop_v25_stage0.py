"""One source-bound external mechanism; primary8h, diagnostic4h, no exit tuning."""
from pathlib import Path
import numpy as np
from prop_v25_common import *
from prop_v15_evidence import bars_for
from prop_v10_signals import frames
from quant_core.corpus_signals import engulfing_rsi
from quant_core.ftmo_execution_and_calendar import gold_calendar
from quant_core.vectorized_stage0_scanner import endpoint_indices, funding_multipliers
from quant_core.native_paths import read_bounded
from quant_core.cost_gates import exceeds_friction_cap
import hashlib
import subprocess

CARD=PROTOCOL.with_name("CORPUS-ENGULFING-RSI-CARD-20261118.md")
REVIEWED_SOURCE_SHA256="f31d225aa34323541e4834c4f904d9b3a9d43c695afd04c319d4f3bcfed76313"


def run():
    summary=read(JOB/"corpus-funnel-summary.json")
    chosen=summary["chosen_mechanisms"]
    if len(chosen)!=1 or Path(chosen[0]["path"]).name.casefold()!="bullishbearish engulfing rsi.mq5":
        save("external-Stage0-results.json",dict(cases=[],reason="NO_REVIEWED_SOURCE_CANDIDATE",trials=0))
        return
    candidate=chosen[0]
    if candidate["sha256"] != REVIEWED_SOURCE_SHA256:
        raise ValueError("EXTERNAL_RULES_REQUIRE_REVIEW_OF_THIS_SOURCE_HASH")
    for name,value in dict(InpAverBodyPeriod=12,InpMAPeriod=5,InpPeriodRSI=37,InpSL=200,InpTP=200,InpDuration=10).items():
        if candidate["defaults"].get(name)!=value:
            raise ValueError("EXTERNAL_DEFAULTS_DIFFER_FROM_FROZEN_CARD")
    if hashlib.sha256(read_bounded(candidate["path"],1048576)).hexdigest()!=candidate["sha256"]:
        raise ValueError("EXTERNAL_SOURCE_CHANGED_BEFORE_STAGE0")
    registration=dict(card_sha256=sha(CARD),source_sha256=candidate["sha256"],
        source_path=candidate["path"], code={str(p):sha(p) for p in (Path(__file__),
        Path("tooling/ai-engines/quant_core/corpus_signals.py"))},
        committed_head=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
        asset="EURUSD",timeframe="H1",defaults=dict(average_body=12,trend_MA=5,RSI=37,SL_points=200),
        horizons=dict(primary=8,diagnostic=4),cost_cap_pct=12,Development=[FIRST,DEV_END])
    save("external-Stage0-registration.json",registration)
    bars=bars_for("EURUSD",True)
    frame=frames(bars)[0]
    signals=engulfing_rsi(frame)
    use=(signals!=0)&(frame["t"]>=FIRST)&(frame["t"]<DEV_END)
    at,side=frame["t"][use].astype("int64"),signals[use]
    indices,valid_entry=endpoint_indices(bars,at,DEV_END)
    entry_at=bars["t"][indices]
    entry=np.where(side==1,bars["ao"][indices],bars["bo"][indices])
    spread=bars["ao"][indices]-bars["bo"][indices]
    natural=np.maximum(200,spread)
    friction=spread+9
    retained=100*friction<=12*natural
    calendar=gold_calendar(FIRST,DEV_END)
    flats=np.array(calendar.times,dtype="int64")
    at_flat=flats.searchsorted(entry_at,side="right")
    next_flat=np.where(at_flat<len(flats),flats[np.minimum(at_flat,len(flats)-1)],DEV_END)
    years=at.astype("datetime64[ms]").astype("datetime64[Y]").astype(int)+1970
    cases=[]
    for horizon in (8,4):
        deadline=np.minimum(entry_at+horizon*3600000,next_flat)
        exits,priced=endpoint_indices(bars,deadline,DEV_END)
        priced &= valid_entry&(deadline>=entry_at)
        price=np.where(side==1,bars["bo"][exits],bars["ao"][exits])
        gross=side*(price-entry)/100000
        funding=-.0004*funding_multipliers(entry_at,np.maximum(entry_at,bars["t"][exits]))
        net=gross-.00009+funding
        annual=[];reasons=[]
        for year in range(2018,2024):
            raw=years==year;good=raw&priced
            mean=float(net[good].mean()) if good.any() else None
            drag=float(friction[good].mean()/100000) if good.any() else None
            annual.append(dict(year=year,raw=int(raw.sum()),priced=int(good.sum()),
                mean_net_pips=mean*10000 if mean is not None else None,
                mean_friction_pips=drag*10000 if drag is not None else None))
            if raw.sum()<40:reasons.append(str(year)+":CADENCE_BELOW40")
            if mean is None or mean<=0 or mean<drag:reasons.append(str(year)+":MARKOUT_BELOW_FRICTION")
        ratio=float(np.median(friction)/np.median(natural)) if len(at) else None
        if ratio is None or exceeds_friction_cap(float(np.median(friction)),float(np.median(natural)),12):
            reasons.append("MEDIAN_SCALE_FAIL")
        if not len(at) or retained.mean()<.5:reasons.append("RETENTION_BELOW50")
        if not priced.all():reasons.append("ENDPOINT_INCOMPLETE")
        cases.append(dict(horizon_hours=horizon,selection_role="PRIMARY" if horizon==8 else "DIAGNOSTIC_ONLY",
            annual=annual,raw=len(at),natural_SL_median_pips=float(np.median(natural)/10) if len(at) else None,
            friction_SL_ratio=ratio,cost_retention=float(retained.mean()) if len(at) else 0,
            passed=not reasons,reasons=reasons))
        compressed("external-raw-"+str(horizon)+"h",dict(at=at,side=side,deadline=deadline,
            entry=entry,exit=[int(v) if ok else None for v,ok in zip(price,priced)],
            priced=priced,net=[float(v) if ok else None for v,ok in zip(net,priced)],
            natural=natural,friction=friction,
            funding=[float(v) if ok else None for v,ok in zip(funding,priced)],years=years))
    value=dict(cases=cases,trials=1,selected_horizon_hours=8,primary_passed=cases[0]["passed"],
        source_control_flow_reviewed=True,source_execution_performed=False,
        target_calendar="declared inherited holiday/Friday scenario; not EURUSD broker certification",
        literal_MQL_binary_parity=False,external_source_distribution=False,prop_qualified=False)
    save("external-Stage0-results.json",value)
    print(value,flush=True)


if __name__=="__main__":
    run()

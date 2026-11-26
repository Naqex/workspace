"""Every remaining structural profile receives a source/data/cost/Stage-0 verdict."""
from collections import defaultdict
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import time
import numpy as np
import prop_v26_common as common
from prop_v26_common import *
from quant_core.job_workspace import JobWorkspace
from quant_core.native_paths import read_bounded
from quant_core.corpus_batch_signals import signals,oscillator
from quant_core.corpus_batch_execution import normalize_trades
from quant_core.native_hourly_source import PairedHourlyStore,IndexedUs500Store
from quant_core.vectorized_stage0_scanner import endpoint_indices,HOUR,DAY
from quant_core.vectorized_sl_active_kernel import money
from quant_core.ftmo_execution_and_calendar import gold_calendar
from prop_v15_evidence import bars_for
from prop_v6_data import aggregate
from prop_v10_signals import frame
from prop_v14_paths import M1ScenarioQuotes
from prop_v25_risk import decide
import prop_v24_pareto as marked
from prop_v14_accounts import trade_money
from prop_v15_accounts import exact_quantity

CARD=PROTOCOL.with_name("CORPUS-BATCH-V26-CARD-20261118.json")
LAB=JobWorkspace(ROOT/"batch-exact-iso-v26-20261118"/"corpus",Path(__file__).resolve().parents[2])
ASSETS=("XAUUSD","EURUSD","US500","GBPUSD","AUDUSD")


def name_parts(name):
    pattern=next(p for p in ("Engulfing","Harami","Hammer","BlackCrows","MeetingLines","StarDoji") if p in name)
    osc=next(p for p in ("RSI","CCI","MFI","Stoch") if name.endswith(p+".mq5"))
    return pattern,osc


def catalogue():
    corpus=unpack("corpus-classification-v2",V25)["rows"]
    top=read(V25/"corpus-funnel-summary-v2.json")["top10"]
    by_sha={r["sha256"]:r for r in corpus if r["status"]=="CLEAN_STRUCTURAL_CANDIDATE"}
    ordered=[by_sha[t["sha256"]] for t in top]
    ordered += sorted((r for r in by_sha.values() if r["sha256"] not in {t["sha256"] for t in top}),
                      key=lambda r:(Path(r["path"]).name.casefold(),r["sha256"]))
    assert len(ordered)==24
    rows=[]
    for rank,row in enumerate(ordered,1):
        raw=read_bounded(row["path"],1048576)
        assert hashlib.sha256(raw).hexdigest()==row["sha256"]
        name=Path(row["path"]).name
        pattern,osc=name_parts(name)
        rows.append(dict(rank=rank,file=name,sha256=row["sha256"],source_path=row["path"],
            aliases=len(row["aliases"]),pattern=pattern,oscillator=osc,defaults=row["defaults"],
            native_asset="CHART_SYMBOL",native_timeframe="CHART_PERIOD",
            benchmark_timeframe="H1",assets=list(ASSETS),mechanism="CANDLE_PATTERN_OSCILLATOR",
            reused_E1=rank==1,volume_required=osc=="MFI"))
    value=dict(profiles=rows,source={str(p):sha(p) for p in (PROTOCOL,Path(__file__),
        Path("tooling/ai-engines/quant_core/corpus_batch_signals.py"),
        Path("tooling/ai-engines/quant_core/corpus_batch_execution.py"))},
        cells=115,point_units=dict(XAUUSD=10,EURUSD=1,US500=10,GBPUSD=1,AUDUSD=1),
        point_status="DECLARED_BENCHMARK_DIGITS_NOT_TARGET_BROKER_CERTIFICATION",
        MFI="BLOCK_IF_TICK_VOLUME_NOT_ADMITTED",selection_uses_later=False,
        entry_normalization="one position per candidate; no overlapping account entries",
        exit_normalization="SL/TP200point,10 observed H1 bars,source oscillator exit,calendar clamp")
    with CARD.open("x",encoding="utf-8") as out:json.dump(value,out,ensure_ascii=False,indent=2)
    save("catalogue.json",value)
    print(dict(catalogue=24,cells=115,card=str(CARD)),flush=True)


def sources():
    admission=read(ROOT/"ensemble-and-storage-v11-20261115/source-admission-v11.json")
    result={}
    for asset in ASSETS:
        if asset in ("XAUUSD","EURUSD"):
            bars=bars_for(asset,True)
            rows=[r for r in aggregate(bars) if r[5]==60]
            prepared=frame(rows,HOUR)
            resolution="M1"
        elif asset=="US500":
            store=IndexedUs500Store(admission["minute_indices"][asset],FIRST-61*DAY,DEV_END)
            bars=store.bars()
            rows=[r for r in aggregate(bars) if r[5]==60]
            prepared=frame(rows,HOUR);resolution="M1"
        else:
            index=deepcopy(admission["hourly_indices"][asset])
            index["books"]=[b for b in index["books"] if b["last"]<DEV_END]
            bars=PairedHourlyStore(index,FIRST-61*DAY,DEV_END).bars()
            prepared=frame([[int(r[k]) for k in ("t","bo","bh","bl","bc")] for r in bars],HOUR)
            resolution="H1_ONLY"
        result[asset]=dict(bars=bars,frame=prepared,resolution=resolution,volume=None)
        event("batch_source_ready",asset=asset,rows=len(bars),resolution=resolution,tick_volume_admitted=False)
    return result


def deadlines(at,horizon,flats,hourly):
    pos=flats.searchsorted(at,side="right")
    stop=np.where(pos<len(flats),flats[np.minimum(pos,len(flats)-1)],DEV_END)
    if hourly:
        stop=stop//HOUR*HOUR
    return np.minimum(at+horizon*HOUR,stop)


def daily_returns(trades,weight=1):
    values=np.zeros((DEV_END-FIRST)//DAY)
    for t in trades:
        day=(t["exit_msc"]-FIRST)//DAY
        if 0<=day<len(values):
            values[day]+=trade_money(t,exact_quantity(t,150*weight),"SYM_FLAT",150)["net_R"]
    return values


def marked_cases(trades,baseline,bars,order):
    readers={a:M1ScenarioQuotes(b,"OPEN_LOW_HIGH_CLOSE" if order=="OLHC" else "OPEN_HIGH_LOW_CLOSE",
                                FIRST,DEV_END) for a,b in bars.items()}
    own=marked.measure(trades,marked.prepare(trades,readers),{})
    parent=marked.measure(baseline,marked.prepare(baseline,readers),{})
    joined=baseline+trades
    candidate=marked.measure(joined,marked.prepare(joined,readers),{"F6":.25})
    check=decide(candidate,parent)
    a,b=daily_returns(trades),daily_returns(baseline)
    corr=float(np.corrcoef(a,b)[0,1]) if a.std()>0 and b.std()>0 else None
    return dict(sleeve=own,portfolio=check,daily_correlation=corr,
                correlation_scope="UTC daily closed-trade net PnL; zero days included",
                ratio_improved=candidate["net_R"]/candidate["equity_R_DD"]>
                               parent["net_R"]/parent["equity_R_DD"])


def run():
    card=read(CARD)
    assert card==json.loads(subprocess.check_output(["git","show","HEAD:"+CARD.as_posix()]))
    for p,digest in card["source"].items():
        assert sha(p)==digest,p
    save("batch-registration.json",dict(card_sha256=sha(CARD),Development=[FIRST,DEV_END],cells=115,
                                      no_later_prices_for_selection=True))
    prepared=sources()
    flats=np.asarray(gold_calendar(FIRST,DEV_END).times,dtype="int64")
    results=[]
    for profile in card["profiles"][1:]:
        for asset in ASSETS:
            started=time.perf_counter()
            source=prepared[asset]; bars=source["bars"]; f=source["frame"]
            base=dict(rank=profile["rank"],file=profile["file"],asset=asset,
                pattern=profile["pattern"],oscillator=profile["oscillator"],resolution=source["resolution"],
                clusters_R=None,net_R=None,max_R_DD=None,daily_correlation=None,SL_active=False)
            if profile["volume_required"] and source["volume"] is None:
                results.append(dict(base,status="DATA_INPUT_INCOMPLETE",reason="ADMITTED_TICK_VOLUME_REQUIRED"))
                continue
            value=oscillator(f,profile["oscillator"],source["volume"])
            signal=signals(f,profile["pattern"],profile["oscillator"],source["volume"])
            use=(signal!=0)&(f["t"]>=FIRST)&(f["t"]<DEV_END)
            at=f["t"][use].astype("int64");side=signal[use]
            entry_i,valid=endpoint_indices(bars,at,DEV_END)
            at=bars["t"][entry_i]
            scale=1000 if asset in ("XAUUSD","US500") else 100000
            p0=np.where(side==1,bars["ao"][entry_i],bars["bo"][entry_i]).astype("int64")
            spread=(bars["ao"][entry_i]-bars["bo"][entry_i]).astype("int64")
            natural=np.maximum(200*card["point_units"][asset],spread)
            friction_den=1_000_000 if asset=="XAUUSD" else 1
            friction_num=((spread+400)*1_000_000+14*p0 if asset=="XAUUSD" else
                          spread+2500 if asset=="US500" else spread+9)
            friction=friction_num/friction_den
            exact=100*friction_num<=12*natural*friction_den
            years=f["t"][use].astype("datetime64[ms]").astype("datetime64[Y]").astype(int)+1970
            horizons=[]
            for horizon in (8,4):
                end=deadlines(at,horizon,flats,source["resolution"]=="H1_ONLY")
                exits,known=endpoint_indices(bars,end,DEV_END)
                known &= valid&(end>=at)&(bars["t"][exits]>=end)
                px=np.where(side==1,bars["bo"][exits],bars["ao"][exits])
                net=money(asset,"SYM",side,p0,px,at,np.maximum(at,bars["t"][exits]),np.full(len(at),"HORIZON"))["net"]
                annual=[]
                for year in range(2018,2024):
                    selected=years==year; good=selected&known
                    annual.append(dict(year=year,signals=int(selected.sum()),priced=int(good.sum()),
                        friction_pass_rate=float(exact[selected].mean()) if selected.any() else 0.,
                        mean_net=float(net[good].mean()) if good.any() else None,
                        mean_friction=float((friction[good]/scale).mean()) if good.any() else None))
                horizons.append(dict(hours=horizon,role="PRIMARY" if horizon==8 else "DIAGNOSTIC_ONLY",annual=annual))
            retention=float(exact.mean()) if len(at) else 0.
            median_ratio=(Fraction(float(np.median(friction_num)))/
                          (friction_den*Fraction(float(np.median(natural))))) if len(at) else None
            ratio=float(median_ratio) if median_ratio is not None else None
            reasons=[]
            if retention<.5:reasons.append("RETENTION_BELOW50")
            if median_ratio is None or 100*median_ratio>12:reasons.append("MEDIAN_SCALE_FAIL")
            for row in horizons[0]["annual"]:
                if row["signals"]<40:reasons.append(str(row["year"])+":CADENCE_BELOW40")
                if row["mean_net"] is None or row["mean_net"]<=0 or row["mean_net"]<row["mean_friction"]:
                    reasons.append(str(row["year"])+":MARKOUT_FAIL")
                if row["priced"]<row["signals"]:reasons.append(str(row["year"])+":ENDPOINT_INCOMPLETE")
            row=dict(base,raw_signals=len(at),trades_per_year=[r["signals"] for r in horizons[0]["annual"]],
                natural_SL_median=float(np.median(natural)/scale) if len(at) else None,
                friction_pass_rate=retention,friction_SL=ratio,markout=horizons,
                stage0_passed=not reasons,reasons=reasons,status="STAGE0_FAIL" if reasons else "STAGE0_PASS",
                prepared_seconds=time.perf_counter()-started)
            if not reasons:
                if source["resolution"]!="M1":
                    row.update(status="DATA_PATH_INCOMPLETE",reason="H1_INTRAHOUR_NOT_CERTIFIED")
                else:
                    take=exact&valid
                    times=at[take];directions=side[take];stops=natural[take]
                    expiry_index=np.minimum(f["t"].searchsorted(times)+10,len(f["t"])-1)
                    expiry=np.minimum(f["t"][expiry_index],deadlines(times,48,flats,False))
                    cases=[]
                    for order in ("OLHC","OHLC"):
                        trades=normalize_trades(bars,f,signal,value,profile["oscillator"],times,directions,stops,
                            expiry,f"{asset}|F6:corpus={profile['rank']}|SOURCE|P0",order,asset)
                        compressed(f"SL-{profile['rank']}-{asset}-{order}",trades)
                        complete=not any(t.get("incomplete") or t.get("same_minute_SL_TP_ambiguous") for t in trades)
                        case=dict(order=order,trades=len(trades),path_complete=complete,
                                  status="REVIEW_REQUIRED" if not complete else "ELIGIBLE_FOR_MARKED_BOOK")
                        if complete and trades and asset in marked.VALUE:
                            baseline=read(V19/f"Dev-{order}-PRIMARY-trades.json")
                            case.update(marked_cases(trades,baseline,
                                {a:prepared[a]["bars"] for a in ("XAUUSD","EURUSD")},order))
                        cases.append(case)
                    eligible=all(c.get("path_complete") and c.get("portfolio",{}).get("passed") and
                                 c.get("ratio_improved") and min(c["sleeve"]["cluster_R"])>0 for c in cases)
                    measured=next((c for c in cases if "sleeve" in c),None)
                    row.update(SL_active=True,status="DEVELOPMENT_PASS" if eligible else "SL_ACTIVE_FAIL_OR_UNKNOWN",
                               cases=cases,eligible_for_later=eligible)
                    if measured:
                        row.update(clusters_R=measured["sleeve"]["cluster_R"],net_R=measured["sleeve"]["net_R"],
                                   max_R_DD=measured["sleeve"]["equity_R_DD"],
                                   daily_correlation=measured["daily_correlation"])
            results.append(row)
            event("batch_cell",rank=profile["rank"],asset=asset,status=row["status"],signals=len(at))
    assert len(results)==115
    compressed("batch-results",results)
    save("batch-summary.json",dict(cells=115,profiles=23,reused_E1=True,
        stage0_passes=sum(r.get("stage0_passed",False) for r in results),
        statuses={s:sum(r["status"]==s for r in results) for s in sorted({r["status"] for r in results})},
        no_later_prices_for_selection=True))
    print(read(LAB.root/"batch-summary.json"),flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--catalogue-only",action="store_true")
    args=p.parse_args()
    with bindings(common,JOB=LAB.root,RUNTIME=LAB):
        activate_runtime()
        catalogue() if args.catalogue_only else run()

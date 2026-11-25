"""Pass 12 US500 NY opening range from QDM tick-derived M1 Bid/Ask."""

import argparse
from collections import Counter, defaultdict
from datetime import date
from math import fsum, isclose
from pathlib import Path
from statistics import mean, median

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

import pass5_usdjpy_tokyo as clock
import pass7b_qdm_m1 as qdm
import pass11_gbpusd_m1 as ingest
import pass11_portfolio as portfolio
from native_ftmo_monfri_seal import START, STOP, read, sha, write
from pass10_institutional_flow import cohorts, epoch, gate
from pass12_usdjpy_forensic import PROTOCOL, tally, timeline, path_intervals
from quant_core.ftmo_track_replay import commission, profiles
from sealed_m1_review import cash_sessions

SOURCE = "USA500IDXUSD"
SYMBOL = SOURCE + "_PASS12_QUARANTINE"
TARGET = "US500.cash"
GRID = 1000
FLAT = 385
CANCEL = 270
COSTS = {"M1_Base": .25, "M1_Stress_Mid": .50, "M1_Stress_High": .75}
HIGH = "M1_Stress_High"
NY = clock.NEW_YORK


def calendar(year):
    path = Path(__file__).with_name("fixtures") / f"nyse-{year}.json"
    sessions = cash_sessions(read(path))
    return {d: int(ts[0]//1000) for d, ts in sessions.items() if len(ts) == 390}, sha(path)


def spread_bounds(stamps, bid, ask, sessions, histogram):
    if not len(stamps):
        return
    first = max(0, int(sessions.searchsorted(stamps[0]-3600000, side="left")))
    end = int(sessions.searchsorted(stamps[-1], side="right"))
    for start in sessions[first:end]:
        a, b = stamps.searchsorted([start, start+3600000])
        values, nums = np.unique(ask[a:b]-bid[a:b], return_counts=True)
        histogram.update({int(x):int(y) for x,y in zip(values,nums)})


def distribution(histogram):
    prices = sorted(histogram)
    count = sum(histogram.values())
    if not count:
        return None
    cumulative = np.cumsum([histogram[p] for p in prices])
    return {"n":count,"mean":fsum(p*histogram[p] for p in prices)/count/GRID,
            "p50":prices[int(np.searchsorted(cumulative,count*.50))]/GRID,
            "p90":prices[int(np.searchsorted(cumulative,count*.90))]/GRID,
            "p95":prices[int(np.searchsorted(cumulative,count*.95))]/GRID}


def prepare(job, year):
    meta = read(job / "QDM_EXPORT_RECEIPT.json")
    if (meta["status"],meta["protocol_commit"],meta["qdm_cli_version"],
            meta["qdm_cli_sha256"],meta["raw_symbol"]) != (
            "DEVELOPMENT_EXPORTS_READY",PROTOCOL,"125.2692",ingest.QDM_SHA,SYMBOL):
        raise ValueError("US500 QDM receipt identity")
    if [e["year"] for e in meta["exported_development"]] != list(clock.YEAR):
        raise ValueError("US500 QDM years incomplete")
    entry, = [e for e in meta["exported_development"] if e["year"] == year]
    path = ingest.bound_export(job,entry,symbol=SYMBOL)
    source = job / "development-m1"
    source.mkdir(exist_ok=True)
    scan = qdm.preflight(path,year)
    write(source / f"{year}-clock-admission.json",scan)
    sessions, calendar_sha = calendar(year)
    times = np.array(list(sessions.values()),dtype=np.int64)*1000
    histogram = Counter()
    rows = ingest.aggregate(path,year,scan,scale=GRID,
                            inspect_ticks=lambda a,b,c:spread_bounds(a,b,c,times,histogram))
    file = source / f"US500-M1-BIDASK-{year}.parquet"
    pq.write_table(pa.table({k:rows[:,i] for i,k in enumerate(qdm.COLUMNS)}),file,compression="zstd")
    result = {**scan,"parquet":file.name,"parquet_sha256":sha(file),"minutes":len(rows),"codec":"zstd",
              "first_minute": int(rows[0,0]), "last_minute": int(rows[-1,0]),
              "calendar_sha256":calendar_sha,"cash_open_spread_points":distribution(histogram),
              "cash_open_spread_hist_0_001_point":histogram}
    write(source / f"{year}.json",result)
    print(year,scan["rows"],len(rows),flush=True)


def first_signal(offsets, quotes):
    box = quotes[offsets < 60]
    top, bottom = float(box[:,5].max()), float(box[:,2].min())
    if top <= bottom:
        return "flat_box", None
    a, b = offsets.searchsorted([60,CANCEL])
    up, down = quotes[a:b,5] >= top - 1e-10, quotes[a:b,2] <= bottom + 1e-10
    hit = np.flatnonzero(up | down)
    if not len(hit):
        return "no_touch",None
    j = int(hit[0])
    if up[j] and down[j]:
        return "dual_touch",None
    i = int(a) + j
    side = 1 if up[j] else -1
    bid,ask = map(float,quotes[i,[0,4]])
    entry = max(top,ask) if side == 1 else min(bottom,bid)
    stop = bottom if side == 1 else top
    return "first_touch", {"side":side,"entry_idx":i,"entry_price":entry,"stop":stop,
                           "top":top,"bottom":bottom,"entry_spread":ask-bid,"risk":abs(entry-stop)}


def stop_event(quotes, signal):
    entry, side, stop = signal["entry_idx"],signal["side"],signal["stop"]
    liq = quotes[:,:4] if side == 1 else quotes[:,4:8]
    hits = np.flatnonzero(side*(liq[entry:-1,2 if side == 1 else 1]-stop)<=1e-10)
    if not len(hits):
        return len(quotes)-1,float(liq[-1,0]),True,"HARD_FLAT"
    j = entry+int(hits[0])
    gap = j != entry and side*(liq[j,0]-stop)<=1e-10
    return j,float(liq[j,0] if gap else stop),bool(gap),"SL_GAP_OR_TOUCH"


def classify(offsets, quotes):
    missing = np.setdiff1d(np.arange(FLAT+1),offsets,assume_unique=True)
    if not len(missing):
        status, signal = first_signal(offsets,quotes)
        return "strict",status,signal,0
    if (len(missing) > 5 or (np.diff(missing)==1).any()
            or not np.isin([0,60,CANCEL,FLAT],offsets).all()):
        return "empty" if not len(offsets) else "B", "unavailable", None, len(missing)
    nearest = offsets.searchsorted(missing)
    if np.abs(quotes[nearest-1][:,[3,7]] - quotes[nearest][:,[0,4]]).max() > .2 + 1e-9:
        return "B","unavailable",None,len(missing)
    status, signal = first_signal(offsets,quotes)
    box = quotes[offsets<60]
    top,bottom = float(box[:,5].max()),float(box[:,2].min())
    entry = int(offsets[signal["entry_idx"]]) if signal else CANCEL
    stop_idx = stop_event(quotes,signal)[0] if signal else None
    exit_ = int(offsets[stop_idx]) if signal else FLAT
    ends = [entry+d for d in (1+120,1+240) if entry+d<=FLAT] if signal else []
    for index, point in zip(nearest,missing):
        prev,nxt = quotes[index-1],quotes[index]
        if signal and min(abs(point-entry),abs(point-exit_),abs(point-FLAT)) <= 1 or point in ends:
            return "A_unreplayable",status,None,len(missing)
        if 60<=point<CANCEL and point<entry and (ingest.touches_between(prev[7],nxt[4],top)
                                              or ingest.touches_between(prev[3],nxt[0],bottom)):
            return "A_unreplayable",status,None,len(missing)
        if signal and entry<point<exit_:
            bid = signal["side"] == 1
            if ingest.touches_between(prev[3 if bid else 7],nxt[0 if bid else 4],signal["stop"]):
                return "A_unreplayable",status,None,len(missing)
    return "A_admitted",status,signal,len(missing)


def raw_marks(day, start, offsets, quotes, signal):
    idx, side = signal["entry_idx"],signal["side"]
    entry, spread = signal["entry_price"],signal["entry_spread"]
    at = int(offsets[idx])
    marks = []
    for horizon,end in (("2h",at+121),("4h",at+241),("hard_flat",FLAT)):
        j = int(offsets.searchsorted(end))
        if end > FLAT or j == len(offsets) or offsets[j] != end:
            continue
        bid,ask = map(float,quotes[j,[0,4]])
        out = bid if side == 1 else ask
        opposite = ask if side == 1 else bid
        for fee,slip in COSTS.items():
            marks.append({"day":day,"year":int(day[:4]),"side":"BUY" if side==1 else "SELL",
                          "horizon":horizon,"fee":fee,"entry":start+at*60,"exit":start+end*60,
                          "net":side*(out-entry)-2*slip,
                          "fade":-side*(opposite-(entry-side*spread))-2*slip,
                          "friction":.5*(spread+ask-bid)+2*slip,"risk":signal["risk"]})
    return marks


def raw_stats(rows):
    return {"n":len(rows),"net":fsum(r["net"] for r in rows),
            "fade":fsum(r["fade"] for r in rows),"friction":fsum(r["friction"] for r in rows),
            "net_mean":mean(r["net"] for r in rows) if rows else None,
            "fade_mean":mean(r["fade"] for r in rows) if rows else None,
            "friction_mean":mean(r["friction"] for r in rows) if rows else None}


def raw_summary(rows):
    years,clusters = cohorts(rows)
    result = {"total":raw_stats(rows),"years":{k:raw_stats(v) for k,v in years.items()},
              "clusters":{k:raw_stats(v) for k,v in clusters.items()},
              "direction":{s: {"years":{k:raw_stats([r for r in v if r["side"]==s]) for k,v in years.items()},
                              "clusters":{k:raw_stats([r for r in v if r["side"]==s]) for k,v in clusters.items()}}
                           for s in ("BUY","SELL")}}
    scale = {"median_ratio_pct":100*median(r["friction"] for r in rows)/median(r["risk"] for r in rows),
             "share_at_12pct":sum(r["friction"]<=.12*r["risk"] for r in rows)/len(rows)} if rows else None
    result["scale"] = scale
    result["gate"] = gate(result,scale,control_fields=("net_mean","fade_mean","friction_mean"))
    return result


def sl_slice(day, start, offsets, quotes, signal, slip):
    entry, side = signal["entry_price"],signal["side"]
    i = signal["entry_idx"]
    end,exit_price,at_open,reason = stop_event(quotes,signal)
    net = side*(exit_price-entry)-2*slip
    liq = quotes[i:end+1,:4] if side == 1 else quotes[i:end+1,4:8]
    marks = (side*(liq-entry)-slip)[:,[0,1,2,3] if side==1 else [0,2,1,3]]
    marks[0,0] = -signal["entry_spread"]-slip
    marks[0,1] = max(marks[0,0],marks[0,3])
    marks[0,2] = min(marks[0,0],marks[0,2],marks[0,3])
    if at_open or i==end:
        marks[-1] = net
    else:
        opening = marks[-1,0]
        marks[-1] = [opening,max(opening,net),min(opening,net),net]
    stamps = start+offsets[i:end+1]*60
    stop = signal["risk"]
    friction = .5*(signal["entry_spread"]+float(quotes[end,4]-quotes[end,0]))+2*slip
    return ({"day":day,"year":int(day[:4]),"entry":int(stamps[0]),
             "exit":int(stamps[-1])+int(not at_open)*60,"at_open":at_open,"reason":reason,"side":side,
             "entry_price":entry,"margin_quote":entry,"net_usd_per_lot":net,
             "initial_risk_usd":stop,"stop_risk_with_cost_usd":stop+2*slip,"net_R":net/stop,
             "estimated_friction_over_stop_pct":100*friction/stop,"winner_label":"UNCLASSIFIED_MISSING_EVIDENCE",
             "entry_sl_same_minute":end==i},stamps,marks)


def summary_sl(tape):
    groups, clusters = cohorts([r for r,*_ in tape])
    stats = tally(tape)
    stats.update({"years":{k:fsum(r["net_R"] for r in v) for k,v in groups.items()},
                  "clusters":{k:fsum(r["net_R"] for r in v) for k,v in clusters.items()},
                  "net_R_annual":stats["net_R"]/7,
                  "underwater_months":path_intervals(*timeline(tape))["underwater"]["months"],
                  "stop_cost_share_12pct":mean(r["estimated_friction_over_stop_pct"]<=12 for r,*_ in tape),
                  "same_minute":sum(r["entry_sl_same_minute"] for r,*_ in tape),
                  "exit_counts":dict(Counter(r["reason"] for r,*_ in tape))})
    stats["survives"] = (min(stats["clusters"].values())>0
                         and sum(p>0 for p in stats["years"].values())>=5
                         and stats["net_R"]>stats["top10_R"])
    return stats


def combine(jobs, eligible, index, specs):
    reference, ref_days = portfolio.frozen_usdjpy(jobs)
    tapes = {"USDJPY":reference,TARGET:{r["day"]:(r,t,m) for r,t,m in index}}
    shared = {k:eligible[k]&ref_days[k] for k in eligible}
    cluster = {d for d in shared["strict"] if d<"2021-01-01"}
    dd = {s: portfolio.replay(cluster,tapes,{s:.003},10000,specs["Swing"])[0]["peak_dd_pct"] for s in tapes}
    inverse = {s:.003/dd[s]/fsum(1/v for v in dd.values()) for s in dd}
    cases = {"solo":{"USDJPY":.003},"equal":{"USDJPY":.0015,TARGET:.0015},"inverse":inverse}
    books = {f"{profile}_{capital}":{
        k:{case:portfolio.replay(days,tapes,risk,capital,specs[profile])[0] for case,risk in cases.items()}
        for k,days in shared.items()}
        for profile,capital in (("Swing",10000),("Swing",25000),("Standard",50000))}
    return {"matched_days":{k:len(v) for k,v in shared.items()},"inverse_dd_cluster_A":dd,"books":books}


def scan(jobs, job, output):
    lock = clock.ROOT/"planning/research/NATIVE_FTMO_HOLDOUT_LOCK.json"
    if sha(lock)!=clock.LOCK_SHA:
        raise ValueError("Holdout lock drift")
    specs,bindings = profiles()
    for spec in (s[TARGET] for s in specs.values()):
        if spec["trade_contract_size"]!=1 or spec["currency_profit"]!="USD" or commission(TARGET,spec,1.)!=0:
            raise ValueError("Unexpected target US500 execution units")
    src = job/"development-m1"
    records = {str(y):read(src/f"{y}.json") for y in clock.YEAR}
    years = {y:{**m,"cash_open_spread_hist_0_001_point":None} for y,m in records.items()}
    manifest = {"source":SYMBOL,"protocol_commit":PROTOCOL,"years":records,
                "export_receipt_sha256":sha(job/"QDM_EXPORT_RECEIPT.json")}
    write(src/"manifest.json",manifest)
    coverage, raw, events, gaps = defaultdict(Counter), [], [], []
    eligible = {"strict":set(),"extended":set()}
    hist = Counter()
    output.mkdir(exist_ok=False)
    for y,meta in records.items():
        hist.update({int(k):v for k,v in meta["cash_open_spread_hist_0_001_point"].items()})
        times, values = ingest.load_m1(src,int(y),meta,asset="US500",scale=GRID)
        assert START<=times[0]<=times[-1]<STOP
        sessions,digest = calendar(int(y))
        if digest!=meta["calendar_sha256"]:
            raise ValueError("Cash calendar changed since QDM admission")
        for day,start in sessions.items():
            low,high = times.searchsorted([start,start+(FLAT+1)*60])
            offsets = (times[low:high]-start)//60
            quotes = values[low:high]
            group,status,signal,missing = classify(offsets,quotes)
            c = coverage[y]
            c[group]+=1
            if group!="strict":
                gaps.append({"day":day,"group":group,"missing_minutes":missing})
            if group not in ("strict","A_admitted"):
                continue
            eligible["extended"].add(day)
            if group=="strict":
                eligible["strict"].add(day)
            c[status]+=1
            if signal:
                raw.extend(raw_marks(day,start,offsets,quotes,signal))
                events.append((day,start,offsets,quotes,signal))
        print(y,dict(coverage[y]),flush=True)
    result = {"protocol_commit":PROTOCOL,"source_sha256":sha(src/"manifest.json"),"spec":bindings,
              "source_years":years,"cash_open_spread":distribution(hist),"coverage":coverage,
              "holdout_rows":0,"order_send_count":0,"sl":None,"portfolio":None}
    stage0 = {}
    for k,days in eligible.items():
        stage0[k] = {fee:{h:raw_summary([r for r in raw if r["fee"]==fee and r["horizon"]==h and r["day"] in days])
                          for h in ("2h","4h","hard_flat")} for fee in COSTS}
    result["stage0"] = stage0
    main = [stage0[k][HIGH]["hard_flat"]["gate"] for k in eligible]
    if not all(g["tests"]["all_years_observed"] for g in main):
        result["verdict"] = "US500_M1_DATA_UNAVAILABLE"
    elif not all(g["pass"] for g in main):
        result["verdict"] = "US500_FAILED_M1_CHECK"
    else:
        result["sl"] = {}
        index = []
        for fee,slip in COSTS.items():
            tape = [sl_slice(*event,slip) for event in events]
            summaries = {}
            for k,days in eligible.items():
                applicable = [item for item in tape if item[0]["day"] in days]
                summaries[k] = summary_sl(applicable)
                sized,_ = portfolio.replay(days,{TARGET:{r["day"]:(r,t,m) for r,t,m in applicable}},
                                          {TARGET:.003},10000,specs["Swing"])
                summaries[k]["swing_10k_030"] = sized
            result["sl"][fee] = summaries
            write(output/f"{fee}-sl-trades.json",[r for r,*_ in tape])
            if fee==HIGH:
                index = tape
        if all(v["survives"] for v in result["sl"][HIGH].values()):
            result["verdict"] = "US500_SURVIVED_M1_CHECK"
            result["portfolio"] = combine(jobs,eligible,index,specs)
        else:
            result["verdict"] = "US500_FAILED_M1_CHECK"
    result["orb_search"] = ("ORB_ENGINE2_SEARCH_EXHAUSTED"
                            if result["verdict"]=="US500_FAILED_M1_CHECK" else None)
    write(output/"us500-stage0-events.json",raw)
    write(output/"us500-gap-days.json",gaps)
    write(output/"us500-result.json",result)
    print(result["verdict"],flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job",type=Path,required=True)
    parser.add_argument("--year",type=int,choices=clock.YEAR)
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    if args.year:
        prepare(args.job,args.year)
    elif args.output is None:
        parser.error("--output required for scan")
    else:
        scan(args.job.parent,args.job,args.output)

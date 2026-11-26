"""Fixed 28-cell V13 path scenario and mechanical Development decision."""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import json
import subprocess
import time
import numpy as np
from prop_campaign_source import ROOT
from prop_v10_source import FIRST, END, sha
from prop_v12_campaign import summarize
from prop_v12_verify import ledger_row, original_input
from quant_core.ftmo_execution_and_calendar import execution_schedule
from quant_core.gap_aware_execution import GapAwarePathIndex, replay_gap_aware
from quant_core.zero_tuning_ensemble import mechanical_composition, cumulative_drawdown
from quant_core.vectorized_stage0_scanner import DAY
import independent_ledger_auditor as oracle

JOB = ROOT/"path-resolution-and-dedup-v13-20261115"
V12 = ROOT/"sl-active-ensemble-v12-20261115"
PROTOCOL = Path("planning/research/PATH-RESOLUTION-AND-DEDUP-V13-PROTOCOL-20261115.md")


def read(p):
    return json.loads(Path(p).read_text(encoding="utf-8-sig"))


def save(name, value):
    with (JOB/name).open("x", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, indent=2)


def ensemble_gate(selected, annual):
    reasons, metrics = [], {}
    if len(selected) < 2:
        reasons.append("FEWER_THAN_TWO_COMPONENTS")
    if len({(r["asset"], r["family"]) for r in selected}) < 2:
        reasons.append("NO_ASSET_OR_MECHANISM_DIVERSITY")
    if any(a["trades"] < 50 for a in annual):
        reasons.append("CADENCE_BELOW50_IN_A_YEAR")
    for model in ("SYM", "ASYM"):
        yearly = [a["models"][model]["net_R"] for a in annual]
        early, late = sum(yearly[:3]), sum(yearly[3:])
        positive = sum(x > 0 for x in yearly)
        ex_best = sum(yearly)-max(yearly, default=0)
        stable = positive >= 5 or (early > 0 and late > 0 and ex_best > 0)
        metrics[model] = dict(net_R=sum(yearly), early_R=early, late_R=late,
                             positive_years=positive, ex_best_R=ex_best, stability_passed=stable)
        if not stable:
            reasons.append(model+":STABILITY")
    return dict(passed=not reasons, reasons=reasons, metrics=metrics)


def forensics(old, arrays, index):
    """Every original invalid event; no return-based gap classification."""
    j, mode = old["source_cell"], old["mode"]
    gaps = index.gaps
    after = np.array([g["after"] for g in gaps])
    before = np.array([g["before"] for g in gaps])
    b = index.bars
    out = []
    for i in np.flatnonzero(~arrays[f"{j}:{mode}:valid"]):
        entry, deadline, exit_at = (int(arrays[k][i]) for k in
            (f"{j}:entry_at", f"{j}:deadline", f"{j}:{mode}:exit_at"))
        crossed = np.flatnonzero((after > entry) & (before < exit_at))
        records = [gaps[k] for k in crossed]
        counts = Counter()
        for g in records:
            counts.update(g["minutes_by_kind"])
        at = int(b["t"].searchsorted(deadline))
        endpoint_missing = at >= len(b) or int(b["t"][at])-deadline > 60000
        out.append(dict(event=int(i), entry=entry, deadline=deadline, old_exit=exit_at,
                        old_path_gap=bool(arrays[f"{j}:{mode}:path_gap"][i]),
                        endpoint_missing=endpoint_missing, gaps=records,
                        missing_minutes_by_kind=dict(counts)))
    return out


def run():
    JOB.mkdir(exist_ok=True)
    started = time.perf_counter()
    all_old = read(V12/"cent-corrected/discovery.json")["rows"]
    old = [r for r in all_old if r["dual_positive"]]
    assert len(old) == 28
    assert sum(r["reasons"] == ["PATH_OR_ENDPOINT_INCOMPLETE"] for r in old) == 19
    code = [Path(__file__), PROTOCOL, Path(__file__).with_name("independent_ledger_auditor.py"),
            Path(__file__).parent/"quant_core/gap_aware_execution.py",
            Path(__file__).parent/"quant_core/ftmo_execution_and_calendar.py",
            Path(__file__).parent/"quant_core/vectorized_sl_active_kernel.py",
            Path(__file__).parent/"quant_core/zero_tuning_ensemble.py"]
    save("registration.json", dict(
        commit=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
        code={str(p):sha(p) for p in code}, parent=sha(V12/"cent-corrected/discovery.json"),
        source_matrices={a:sha(V12/f"{a}-path-matrix.npz") for a in ("XAUUSD","EURUSD")},
        budget=[r["id"] for r in old], utc=datetime.now(timezone.utc).isoformat(),
        validation_prices_opened=False, execution_scenario="V13_NEXT_QUOTE"))
    schedule = execution_schedule(FIRST, END)
    save("session-calendar.json", dict(version=schedule.version, events=list(schedule.events.values()),
        historical_target_times_certified=False, raw_gaps_do_not_establish_market_closures=True))
    days = np.arange(FIRST//DAY, END//DAY)
    days = days[(days+3)%7 < 5]
    profiles, summaries, forensics_rows, timings = {}, [], [], {}
    source_index = read(ROOT/"ensemble-and-storage-v11-20261115/source-admission-v11.json")
    for asset in ("XAUUSD","EURUSD"):
        tick = time.perf_counter()
        print(dict(stage="V13_source_and_path_index",asset=asset),flush=True)
        bars = original_input(asset, source_index)
        index = GapAwarePathIndex(bars, asset=asset, schedule=schedule)
        save(asset+"-source-gaps.json", index.audit)
        arrays = np.load(V12/f"{asset}-path-matrix.npz")
        packed = {}
        for row in old:
            if row["asset"] != asset:
                continue
            j, mode = row["source_cell"], row["mode"]
            m = {k:arrays[f"{j}:{k}"] for k in (
                "at","entry_at","side","entry_price","stop","natural","friction",
                "ratio","years","deadline","admitted")}
            m.update(asset=asset, recipe=row["recipe"], family=row["family"],
                     horizon=row["horizon"], _index=index)
            detail = forensics(row, arrays, index)
            r = replay_gap_aware(index, m, mode)
            summary, daily = summarize(m, r, days)
            summary.update(source_cell=j, old_priced=row["priced"],
                old_reasons=row["reasons"], only_path_before=row["reasons"] == ["PATH_OR_ENDPOINT_INCOMPLETE"],
                source_uncertain=int(r["source_uncertain"].sum()),
                source_uncertain_admitted=int((r["source_uncertain"] & r["valid"] & m["admitted"]).sum()),
                source_verified_component=bool(summary["admitted_component"] and not r["source_uncertain"].any()),
                execution_scenario="V13_NEXT_QUOTE",
                deferred_endpoint_events=np.flatnonzero(r["deferred_endpoint"]).tolist(),
                open_stop_events=np.flatnonzero(r["open_stop"]).tolist())
            summaries.append(summary)
            profiles[row["id"]] = daily
            forensics_rows.append(dict(id=row["id"],asset=asset,family=row["family"],mode=mode,
                old_raw=row["raw"],old_priced=row["priced"],old_unresolved=row["raw"]-row["priced"],
                only_path_before=summary["only_path_before"],events=detail))
            for field in ("at","entry_at","side","entry_price","stop","natural","friction","ratio","years",
                          "deadline","admitted"):
                packed[f"{j}:{field}"] = m[field]
            for field in ("valid","reason","exit_at","exit_price","path_gap","activation_index","protection_price",
                          "source_uncertain","scheduled_deadline","effective_deadline",
                          "deferred_endpoint","endpoint_open_stop","open_stop"):
                packed[f"{j}:{mode}:{field}"] = r[field]
            for model in ("SYM","ASYM"):
                for field in ("gross","commission","slippage","funding","net","net_R"):
                    packed[f"{j}:{mode}:{model}:{field}"] = r["model"][model][field]
            print(dict(stage="V13_cell",id=row["id"],priced=summary["priced"],raw=summary["raw"],
                       uncertain=summary["source_uncertain"],reasons=summary["reasons"]),flush=True)
        np.savez_compressed(JOB/f"{asset}-path-matrix.npz",**packed)
        timings[asset] = time.perf_counter()-tick
    components = [dict(id=r["id"],asset=r["asset"],family=r["family"],daily=profiles[r["id"]]["SYM"],
                       events=np.load(JOB/f'{r["asset"]}-path-matrix.npz')[f'{r["source_cell"]}:at'])
                  for r in summaries if r["admitted_component"]]
    choice = mechanical_composition(components,correlation_limit=.25)
    selected = [next(r for r in summaries if r["id"] == identity) for identity in choice["selected"]]
    annual = []
    for y in range(2018,2024):
        mask = days.astype("datetime64[D]").astype("datetime64[Y]").astype(int)+1970 == y
        annual.append(dict(year=y,trades=sum(next(a["admitted"] for a in r["annual"] if a["year"]==y)
                                             for r in selected),
            models={model:dict(net_R=float(sum(profiles[r["id"]][model][mask].sum() for r in selected)),
                daily_MTM_R_DD=cumulative_drawdown(sum((profiles[r["id"]][model][mask] for r in selected),
                                                     np.zeros(int(mask.sum())))))
                    for model in ("SYM","ASYM")}))
    decision = ensemble_gate(selected,annual)
    selected_indices = [choice["ids"].index(identity) for identity in choice["selected"]]
    correlations = [dict(left=choice["ids"][i],right=choice["ids"][j],correlation=choice["correlation"][i][j])
                    for n,i in enumerate(selected_indices) for j in selected_indices[:n]]
    if any(r["correlation"] >= .25 for r in correlations):
        raise ValueError("selected_pair_correlation")
    decision.update(selected=choice["selected"],K=len(selected),components=len(components),
        source_verified_components=sum(r["source_verified_component"] for r in summaries),
        pricing_complete_cells=sum(r["complete_path"] for r in summaries),annual=annual,
        pair_correlations=correlations,scope="conditional next-quote scenario; reference risk, not account replay",
        validation="PENDING_COMMITTED_ACCOUNT_ADMISSION" if decision["passed"] else "CANCELED_FAILED_DEVELOPMENT",
        lifecycle="NOT_RUN",actual_account_replayed=False,clean_OOS=False,validation_prices_opened=False)
    save("forensics.json",dict(rows=forensics_rows))
    save("discovery.json",dict(rows=summaries,selection=choice,timings=timings))
    save("decision.json",decision)
    np.savez_compressed(JOB/"daily-profiles.npz",days=days,
        **{f"{i}:{model}":profiles[row["id"]][model] for i,row in enumerate(summaries) for model in ("SYM","ASYM")})
    save("timings.json",dict(assets=timings,total=time.perf_counter()-started))
    print(dict(stage="V13_Development_decision",**decision),flush=True)


def verify():
    start = time.perf_counter()
    data = read(JOB/"discovery.json")
    calendar = read(JOB/"session-calendar.json")
    events = {r["day"]:r for r in calendar["events"]}
    # Independently assemble calendar deadlines from explicit dates, not the producer facade.
    flats = []
    from datetime import timedelta
    d = datetime(2017,11,1,tzinfo=timezone.utc)
    while d.year < 2025:
        base=int(d.timestamp()*1000)
        if d.weekday()==4: flats.append(base+73800000)
        row=events.get(d.date().isoformat(),{})
        if row.get("flat_utc"):
            h,m=map(int,row["flat_utc"].split(":"));flats.append(base+h*3600000+m*60000)
        d += timedelta(days=1)
    source_index = read(ROOT/"ensemble-and-storage-v11-20261115/source-admission-v11.json")
    failures, counts, samples = [], Counter(), []
    for asset in ("XAUUSD","EURUSD"):
        print(dict(stage="V13_independent_audit",asset=asset),flush=True)
        bars = original_input(asset,source_index)
        arrays=np.load(JOB/f"{asset}-path-matrix.npz")
        spec=dict(contract=100 if asset=="XAUUSD" else 100000,scale=1000 if asset=="XAUUSD" else 100000,
                  step=60000,gap_policy="V13_NEXT_QUOTE",session_events=events)
        for row in data["rows"]:
            if row["asset"]!=asset: continue
            j,mode=row["source_cell"],row["mode"];p=f"{j}:{mode}:"
            # Cache NPZ fields once per cell; no repeated decompression per scalar trade.
            z={k:arrays[k] for k in arrays.files if k.startswith(f"{j}:")}
            for i in np.flatnonzero(z[p+"valid"]):
                t=ledger_row(row,z,i,asset,mode,"SYM")
                activation=t.pop("activation_index")
                if activation>=0: t["protection_time"]=int(bars["t"][activation])+60000
                for k in ("scheduled_deadline","effective_deadline","source_uncertain"):
                    t[k]=bool(z[p+k][i]) if k=="source_uncertain" else int(z[p+k][i])
                result=oracle.audit_trade(t,(bars["t"],bars),spec,flats)
                counts["paths"]+=1
                counts["paths_with_source_uncertainty"]+=int(t["source_uncertain"])
                if not result["passed"]:
                    failures.append(dict(id=row["id"],event=int(i),kind="PATH",errors=result["errors"]))
                for model in ("SYM","ASYM"):
                    legs=oracle.cash_legs(t,model,spec)
                    for field,key in (("gross","gross"),("commission","commission"),("slippage","slippage"),
                                      ("funding","swap"),("net","net")):
                        actual=oracle.cent(round(float(z[p+model+":"+field][i])*spec["contract"],8))
                        if actual!=legs[key]:
                            failures.append(dict(id=row["id"],event=int(i),kind=field,model=model,
                                                 producer=str(actual),oracle=str(legs[key])))
                        counts["cash_legs"]+=1
                    counts["cost_views"]+=1
                if t["source_uncertain"] and len(samples)<20: samples.append(dict(id=row["id"],event=int(i),**t))
        print(dict(asset=asset,counts=dict(counts),failures=len(failures)),flush=True)
    out=dict(passed=not failures,counts=dict(counts),failures=failures,failure_count=len(failures),
        examples=samples,seconds=time.perf_counter()-start,same_implementer=True,
        independent_source_feed=False,independent_scalar_and_decimal=True,
        source_coverage_certified=False,producer=sha(JOB/"registration.json"),auditor=sha(Path(oracle.__file__)))
    save("independent-audit.json",out)
    print(dict(stage="V13_audit_complete",passed=out["passed"],counts=dict(counts),failures=len(failures)),flush=True)


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--verify",action="store_true")
    args=p.parse_args()
    verify() if args.verify else run()

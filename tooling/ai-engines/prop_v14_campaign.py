"""Fixed V14 Dev portfolios, committed release, then longitudinal evaluation."""
from collections import Counter
from pathlib import Path
import json
import subprocess
import time
import numpy as np
from prop_v14_source import JOB,V13,ROOT,FIRST,DEV_END,END,SEED,read,save,sha
from prop_v12_campaign import summarize
from quant_core.market_data_store import BAR,MarketDataStore
from quant_core.gap_aware_execution import GapAwarePathIndex,replay_gap_aware
from quant_core.ftmo_execution_and_calendar import execution_schedule,gold_calendar
from quant_core.vectorized_sl_active_kernel import daily_mtm
from quant_core.vectorized_stage0_scanner import DAY
from quant_core.zero_tuning_ensemble import cumulative_drawdown

DECISION=Path("planning/research/EVIDENCE-AND-LIFECYCLE-V14-FREEZE-20261115.json")
PROTOCOL=Path("planning/research/EVIDENCE-AND-LIFECYCLE-V14-PROTOCOL-20261115.md")


def annual(rows,profiles,selected):
    out=[]
    for year in range(2018,2024):
        out.append(dict(year=year,trades=sum(next(a["admitted"] for a in rows[s]["annual"] if a["year"]==year)
                                             for s in selected),
            models={model:dict(net_R=sum(next(a["models"][model]["net_R"] for a in rows[s]["annual"]
                                             if a["year"]==year) for s in selected)) for model in ("SYM","ASYM")}))
    return out


def development():
    start=time.perf_counter()
    parent=read(V13/"discovery.json")["rows"]
    eligible=[r for r in parent if r["complete_path"]]
    source=read(JOB/"source-dev-admission.json")["assets"]
    days=np.arange(FIRST//DAY,DEV_END//DAY);days=days[(days+3)%7<5]
    profiles={};summaries=[];eventsets={};packed_by_asset={}
    for asset in ("XAUUSD","EURUSD"):
        proof=source[asset]
        if sha(proof["path"])!=proof["sha256"]:raise ValueError("V14_source_hash")
        bars=np.memmap(proof["path"],dtype=BAR,mode="r")
        index=GapAwarePathIndex(bars,asset=asset,schedule=execution_schedule(FIRST,DEV_END))
        z=np.load(V13/f"{asset}-path-matrix.npz");packed={}
        for row in eligible:
            if row["asset"]!=asset:continue
            j,mode=row["source_cell"],row["mode"]
            m={k:z[f"{j}:{k}"] for k in ("at","entry_at","side","entry_price","stop","natural",
                "friction","ratio","years","deadline","admitted")}
            m.update(asset=asset,recipe=row["recipe"],family=row["family"],horizon=row["horizon"],_index=index)
            r=replay_gap_aware(index,m,mode)
            summary,daily=summarize(m,r,days)
            summary.update(source_cell=j,source_uncertain=int(r["source_uncertain"].sum()))
            summaries.append(summary);profiles[row["id"]]=daily;eventsets[row["id"]]=set(map(int,m["at"]))
            for k,v in m.items():
                if isinstance(v,np.ndarray):packed[f"{j}:{k}"]=v
            for k,v in r.items():
                if isinstance(v,np.ndarray):packed[f"{j}:{mode}:{k}"]=v
            for model in ("SYM","ASYM"):
                for k,v in r["model"][model].items():packed[f"{j}:{mode}:{model}:{k}"]=v
        np.savez_compressed(JOB/f"{asset}-Dev-paths.npz",**packed)
        packed_by_asset[asset]=packed
    lookup={r["id"]:r for r in summaries}
    core=read(V13/"decision.json")["selected"]
    expanded=core[:];diagnostics=[]
    for row in sorted(summaries,key=lambda r:(r["asset"],r["family"],r["id"])):
        identity=row["id"]
        if identity in expanded or not row["complete_path"]:continue
        conflicts=[]
        for s in expanded:
            corr=float(np.corrcoef(profiles[identity]["SYM"],profiles[s]["SYM"])[0,1])
            overlap=len(eventsets[identity]&eventsets[s])/max(1,min(len(eventsets[identity]),len(eventsets[s])))
            if corr>=.25 or ((row["asset"],row["family"])==(lookup[s]["asset"],lookup[s]["family"]) and overlap>=.5):
                conflicts.append(dict(id=s,correlation=corr,decision_overlap=overlap))
        diagnostics.append(dict(id=identity,conflicts=conflicts,selected=not conflicts,
                                economic_reasons=row["reasons"]))
        if not conflicts:expanded.append(identity)
        if len(expanded)==5:break
    candidates=dict(A=core,B=expanded)
    results={}
    for name,selected in candidates.items():
        a=annual(lookup,profiles,selected)
        results[name]=dict(selected=selected,K=len(selected),annual=a,
            mean_annual_cadence=sum(y["trades"] for y in a)/6,
            cadence_pass=sum(y["trades"] for y in a)/6>=50,
            models={model:dict(net_R=sum(y["models"][model]["net_R"] for y in a),
                ex_best_R=sum(y["models"][model]["net_R"] for y in a)-max(y["models"][model]["net_R"] for y in a),
                early_R=sum(y["models"][model]["net_R"] for y in a[:3]),
                late_R=sum(y["models"][model]["net_R"] for y in a[3:])) for model in ("SYM","ASYM")})
    save("development.json",dict(rows=summaries,candidates=results,expansion_order=diagnostics,
        scope="same frozen Dev signals/stops, versioned missing-minute backfill",seconds=time.perf_counter()-start))
    np.savez_compressed(JOB/"Dev-profiles.npz",days=days,
        **{f"{i}:{m}":profiles[r["id"]][m] for i,r in enumerate(summaries) for m in ("SYM","ASYM")})
    print(dict(stage="V14_Dev",candidates=results),flush=True)


def freeze():
    dev=read(JOB/"development.json")
    files=[PROTOCOL,*sorted(Path("tooling/ai-engines").glob("prop_v14_*.py")),
        Path("tooling/ai-engines/independent_ledger_auditor.py"),
        Path("tooling/ai-engines/quant_core/gap_aware_execution.py"),
        Path("tooling/ai-engines/quant_core/ftmo_execution_and_calendar.py")]
    files += [Path("tooling/ai-engines")/n for n in (
        "prop_v6_account.py","prop_v6_replay.py","prop_v5_account.py","prop_cocore_v4.py",
        "prop_portfolio_accounts.py","prop_campaign_accounts.py","prop_v10_signals.py","prop_v12_signals.py")]
    files += [Path("tooling/ai-engines")/n for n in (
        "quant_core/vectorized_stage0_scanner.py","quant_core/vectorized_sl_active_kernel.py",
        "prop_v8_calendar_correction.py","prop_v8_source.py","prop_v6_signals.py")]
    data=dict(schema="V14-fixed-candidates-v1",selection_years=list(range(2018,2024)),
        candidate_A=dev["candidates"]["A"]["selected"],candidate_B=dev["candidates"]["B"]["selected"],
        B_individual_economic_failures_allowed_for_fixed_comparison=True,
        risk_usd=[200,175,125],reference_risk_usd=150,initial_usd=50000,
        path_models=["NEXT_QUOTE","CLEAN_COHORT"],
        M1_orders=["OPEN_LOW_HIGH_CLOSE","OPEN_HIGH_LOW_CLOSE"],
        models=["SYM","ASYM"],start=FIRST,end=END,
        starts="105 monthly Jan2018–Sep2026",standalone=True,
        cadence="mean over Dev>=50/year; owner authorized V14 change",
        price_exposure_label="POST_EXPOSURE_LONGITUDINAL; F5 first mechanism evaluation on exposed data",
        validation_prices_opened=False,protocol_sha256=sha(PROTOCOL),
        development_sha256=sha(JOB/"development.json"),
        source_dev_sha256=sha(JOB/"source-dev-admission.json"),
        session_calendar_sha256=__import__("hashlib").sha256(json.dumps(
            gold_calendar(FIRST,END).events,sort_keys=True).encode()).hexdigest(),
        pins={str(p):sha(p) for p in files})
    if DECISION.exists():raise ValueError("preserve_original_V14_freeze")
    DECISION.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
    save("candidate-freeze.json",data)
    print(dict(stage="V14_freeze_needs_commit",A=data["candidate_A"],B=data["candidate_B"]),flush=True)


def release():
    cfg=read(DECISION)
    head=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()
    committed=json.loads(subprocess.check_output(["git","show",head+":"+DECISION.as_posix()]))
    if cfg!=committed:raise ValueError("V14_candidate_not_committed")
    for p,digest in cfg["pins"].items():
        if sha(p)!=digest:raise ValueError("V14_frozen_code_drift:"+p)
    save("longitudinal-release.json",dict(commit=head,freeze_sha256=sha(DECISION),
        owner_authorization="3a068d12-5c3e-4595-8838-da3187372d7c",
        first=DEV_END,end=END,clean_OOS=False))
    print(dict(stage="V14_2024_2026_authorized",commit=head),flush=True)


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("stage",choices=("development","freeze","release"))
    globals()[p.parse_args().stage]()

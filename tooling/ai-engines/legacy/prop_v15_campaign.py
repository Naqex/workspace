"""Development-only risk calibration, committed freeze, then historical evaluation."""
from datetime import datetime,timezone
from statistics import median
import json
import subprocess
from prop_v15_common import *
from prop_v15_paths import prepare,load
from prop_v15_accounts import replay_profiles
from quant_core.ftmo_execution_and_calendar import gold_calendar


def metrics(rows):
    challenge=[r for r in rows if r["kind"]=="CHALLENGE"]
    passed=[r for r in challenge if len(r["phase_passes"])==2]
    months=[(r["phase_passes"][1]["at"]-r["start_msc"])/(86400000*365.25/12) for r in passed]
    standalone=next((r for r in rows if r["kind"]=="STANDALONE_FULL"),None)
    return dict(windows=len(challenge),phase1=sum(len(r["phase_passes"])>=1 for r in challenge),
        funded=len(passed),median_months=median(months) if months else None,
        breaches=sum(bool(r["first_breach"]) for r in rows),
        worst_static=max(r["static_loss_pct"] for r in rows),
        worst_daily=max(r["worst_daily_loss_pct"] for r in rows),
        payout_count_windows=sum(len(r["payouts"]) for r in challenge),
        payout_windows_usd=sum(r["trader_payout_usd"] for r in challenge),
        standalone_payout=standalone["trader_payout_usd"] if standalone else None,
        standalone_payout_count=len(standalone["payouts"]) if standalone else None,
        censored_phase1=sum(r["phase"]==1 and not r["first_breach"] for r in challenge),
        censored_phase2=sum(r["phase"]==2 and not r["first_breach"] for r in challenge))


def grid_profiles():
    return [dict(name="V14")]+[dict(name=f"D{f:g}",factor=f) for f in FACTORS]


def development(tag):
    name=f"Dev-{tag}-PRIMARY-trades.json"
    trades,readers,_=load(tag,True) if (JOB/name).exists() else prepare(tag,True)
    rows=replay_profiles(trades,readers,gold_calendar(FIRST,DEV_END),grid_profiles(),True)
    save(f"Dev-{tag}-grid-accounts.json",rows)
    event("V15_Dev_grid_complete",tag=tag,accounts=len(rows))


def select():
    cases=[]
    for profile in grid_profiles():
        models=[]
        for tag in ("OLHC","OHLC"):
            rows=read(JOB/f"Dev-{tag}-grid-accounts.json")
            for cost in ("SYM","ASYM"):
                chosen=[r for r in rows if r["profile"]==profile["name"] and r["cell"].startswith(cost)]
                models.append(dict(tag=tag,cost=cost,**metrics(chosen)))
        maximum_static=max(m["worst_static"] for m in models)
        eligible=all(m["breaches"]==0 and m["worst_daily"]<2.5 and m["worst_static"]<=8.2 for m in models)
        cases.append(dict(profile=profile,models=models,eligible=eligible,
            target_band=7.5<=maximum_static<=8.2,maximum_static=maximum_static,
            worst_completions=min(m["funded"] for m in models),
            slowest_conditional_median=max(m["median_months"] or float("inf") for m in models)))
    allowed=[r for r in cases if r["profile"]["name"]!="V14" and r["eligible"]]
    band=[r for r in allowed if r["target_band"]]
    pool=band or allowed
    choice=min(pool,key=lambda r:(-r["worst_completions"],r["slowest_conditional_median"],r["profile"]["factor"])) if pool else None
    selected=choice["profile"] if choice else dict(name="D1",factor=1.)
    # JSON does not need non-standard Infinity to represent no completed window.
    for row in cases:
        if row["slowest_conditional_median"]==float("inf"):row["slowest_conditional_median"]=None
    save("Dev-selection.json",dict(cases=cases,selected=selected,eligible=choice is not None,
        target_band_met=bool(choice and choice["target_band"]),fallback_diagnostic_only=choice is None,
        cushion=dict(name="CUSHION",factor=selected["factor"],cushion=True),
        selection_uses_only_2018_2023=True,preexposed_2024_2026_not_clean_OOS=True))
    event("V15_selection",selected=selected,eligible=choice is not None)


def cushion_dev(tag):
    selection=read(JOB/"Dev-selection.json")
    trades,readers,_=load(tag,True)
    rows=replay_profiles(trades,readers,gold_calendar(FIRST,DEV_END),[selection["cushion"]],True)
    save(f"Dev-{tag}-cushion-accounts.json",rows)
    event("V15_Dev_cushion_complete",tag=tag,accounts=len(rows))


def freeze():
    selection=read(JOB/"Dev-selection.json")
    files=[PROTOCOL,*sorted(Path("tooling/ai-engines").glob("prop_v15_*.py")),
        Path("tooling/ai-engines/independent_ledger_auditor.py"),
        Path("tooling/ai-engines/prop_v14_accounts.py"),Path("tooling/ai-engines/prop_v14_paths.py"),
        Path("tooling/ai-engines/prop_v14_review.py"),Path("tooling/ai-engines/prop_v6_replay.py"),
        Path("tooling/ai-engines/prop_v6_account.py"),Path("tooling/ai-engines/prop_v5_account.py"),
        Path("tooling/ai-engines/prop_portfolio_accounts.py"),Path("tooling/ai-engines/prop_cocore_v4.py"),
        Path("tooling/ai-engines/quant_core/ftmo_execution_and_calendar.py"),
        Path("tooling/ai-engines/quant_core/gap_aware_execution.py")]
    audit_names=[f"Dev-{tag}-{stage}-audit.json" for tag in ("OLHC","OHLC") for stage in ("grid","cushion")]
    for name in audit_names:
        if not read(JOB/name)["passed"]:raise ValueError("V15_Dev_audit_not_passed")
    if DECISION.exists():raise ValueError("preserve_original_V15_freeze")
    data=dict(schema="V15-risk-freeze-v1",selection=selection,source_parent="V14 immutable",
        code_pins={str(p):sha(p) for p in files},bridge_evidence_sha256=sha(JOB/"bridge-evidence.json"),
        selection_sha256=sha(JOB/"Dev-selection.json"),audits={n:sha(JOB/n) for n in audit_names},
        Dev_end=DEV_END,validation_end=END,full_sizing_evaluated=False,
        mathematical_market_bound=False,original_A=read(V14/"candidate-freeze.json")["candidate_A"])
    DECISION.write_text(json.dumps(data,indent=2),encoding="utf-8")
    save("freeze.json",data);event("V15_freeze_needs_commit",selected=selection["selected"])


def verify_release():
    cfg=read(DECISION)
    blob=json.loads(subprocess.check_output(["git","show","HEAD:"+DECISION.as_posix()]))
    if cfg!=blob:raise ValueError("V15_selection_not_committed")
    for p,digest in cfg["code_pins"].items():
        if sha(p)!=digest:raise ValueError("V15_frozen_code_drift:"+p)
    return cfg


def full(tag):
    cfg=verify_release();selection=cfg["selection"]
    name=f"Full-{tag}-PRIMARY-trades.json"
    trades,readers,_=load(tag,False) if (JOB/name).exists() else prepare(tag,False)
    profiles=[selection["selected"],selection["cushion"]]
    rows=replay_profiles(trades,readers,gold_calendar(FIRST,END),profiles,False)
    save(f"Full-{tag}-sizing-accounts.json",rows)
    event("V15_full_sizing_complete",tag=tag,accounts=len(rows))


def strict(tag):
    verify_release()
    name=f"Full-{tag}-ALL_UNCERTIFIED-trades.json"
    trades,readers,_=load(tag,False,"ALL_UNCERTIFIED") if (JOB/name).exists() else prepare(tag,False,"ALL_UNCERTIFIED")
    rows=replay_profiles(trades,readers,gold_calendar(FIRST,END),[dict(name="V14")],False)
    save(f"Full-{tag}-strict-accounts.json",rows)
    event("V15_full_strict_complete",tag=tag,accounts=len(rows))


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("stage",choices=("development","select","cushion_dev","freeze","full","strict"))
    p.add_argument("--tag",choices=("OLHC","OHLC"),default="OLHC")
    args=p.parse_args()
    globals()[args.stage]() if args.stage in ("select","freeze") else globals()[args.stage](args.tag)

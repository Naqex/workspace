"""V17 fixed tiers over reused price paths; new policy accounts use separate audits."""
from pathlib import Path
import subprocess
import json
import independent_ledger_auditor as oracle
import prop_v14_review as review
import prop_v15_accounts as parent_accounts
from prop_v17_common import *
from prop_v17_accounts import V17Account,execution_bindings
from prop_v16_paths import load as v16_load
from prop_v15_paths import load as v15_load
from prop_v14_accounts import monthly_starts
from quant_core.ftmo_execution_and_calendar import gold_calendar,execution_schedule
from quant_core.prop_lifecycle_and_parity import simulate,bindings


def paths_audit(tag,dev,strict,parent_v15=False):
    scope="Dev" if dev else "Full";mode="STRICT" if strict else "PRIMARY"
    end=DEV_END if dev else END
    if parent_v15:
        trades,readers,bars=v15_load(tag,False,"ALL_UNCERTIFIED")
        events=execution_schedule(FIRST,end).events
        prefix="V15-CUSHION"
    else:
        if read(JOB/"selection.json")["selected"]:raise ValueError("V17_selected_additions_need_admitted_account_adapter")
        trades,readers,bars=v16_load(tag,dev,strict)
        events=gold_calendar(FIRST,end).events;prefix="V17"
    for t in trades:
        local=dict(t,source_uncertain=t["scenario_remaining_source_gaps"])
        check=oracle.audit_v14_path(local,bars[t["asset"]],events,end,
            scheduled_override=None if parent_v15 else t["deadline_msc"])
        if not check["passed"]:raise ValueError("V17_parent_path_drift:"+str(check))
        if not parent_v15 and t["deadline_msc"]!=oracle.v16_causal_cutoff(
                t["entry_msc"],t["parent_deadline"],t["asset"],events):
            raise ValueError("V17_deadline_not_causal")
    source=(V15/f"Full-{tag}-ALL_UNCERTIFIED-trades.json" if parent_v15 else
        V16/f"{scope}-{tag}-{mode}-trades.json")
    save(f"{scope}-{tag}-{prefix}-{mode}-path-audit.json",dict(passed=True,paths=len(trades),
        parent_path=str(source),parent_sha256=sha(source),same_implementer_and_feed=True,
        unchanged_price_and_SL_paths=True,source_uncertain=sum(t["source_uncertain"] for t in trades)))
    return trades,readers


def run(tag,dev,strict):
    if not dev:verify_release()
    scope="Dev" if dev else "Full";mode="STRICT" if strict else "PRIMARY"
    end=DEV_END if dev else END;tiers=read(JOB/"tier-selection.json")["tiers"]
    trades,readers=paths_audit(tag,dev,strict)
    calendar=gold_calendar(FIRST,end);accounts=[];labels=[]
    for model in ("SYM_FLAT","ASYM_FLAT"):
        for at,standalone in [(t,False) for t in monthly_starts(FIRST,end)]+[(FIRST,True)]:
            accounts.append(V17Account(at,end,model,rolling=True,standalone=standalone,tiers=tiers))
            labels.append(dict(kind="STANDALONE_FULL" if standalone else "CHALLENGE",profile="V17"))
    import prop_v6_replay as replay
    with execution_bindings(),bindings(replay,event=event):
        rows=simulate(trades,readers,accounts,FIRST,end,calendar)
    rows=[dict(row,**label) for row,label in zip(rows,labels)]
    save(f"{scope}-{tag}-{mode}-accounts.json",rows)
    event("V17_accounts_complete",scope=scope,order=tag,mode=mode,accounts=len(rows))
    if any(row["tiers"]!=tiers for row in rows):raise ValueError("V17_tier_contract_drift")
    with bindings(review,V14LedgerOracle=oracle.V17LedgerOracle):
        records=review.audit_accounts(rows,trades,readers,calendar,FIRST,end)
    save(f"{scope}-{tag}-{mode}-account-audit.json",dict(passed=True,accounts=len(records),records=records,
        tiers=tiers,same_implementer_and_feed=True))
    event("V17_account_audit_PASS",scope=scope,order=tag,mode=mode,accounts=len(records))


def parent_strict(tag):
    verify_release()
    trades,readers=paths_audit(tag,False,True,True)
    calendar=gold_calendar(FIRST,END);profile=read(V15/"Dev-selection.json")["cushion"]
    with bindings(parent_accounts,event=event):
        rows=parent_accounts.replay_profiles(trades,readers,calendar,[profile],False)
    save(f"Full-{tag}-V15-CUSHION-STRICT-accounts.json",rows)
    with bindings(review,V14LedgerOracle=oracle.V15LedgerOracle):
        records=review.audit_accounts(rows,trades,readers,calendar,FIRST,END)
    save(f"Full-{tag}-V15-CUSHION-STRICT-account-audit.json",dict(passed=True,accounts=len(records),
        records=records,same_implementer_and_feed=True))
    event("V17_parent_CUSHION_strict_audited",order=tag,accounts=len(records))


def freeze():
    tiers=read(JOB/"tier-selection.json");selection=read(JOB/"selection.json")
    if selection["selected"]:raise ValueError("V17_addition_adapter_and_Dev_audit_needed")
    audits={}
    for tag in ("OLHC","OHLC"):
        for mode in ("PRIMARY","STRICT"):
            for suffix in ("account-audit","V17-"+mode+"-path-audit"):
                name=f"Dev-{tag}-{mode}-account-audit.json" if suffix=="account-audit" else f"Dev-{tag}-{suffix}.json"
                if not read(JOB/name)["passed"]:raise ValueError("V17_Dev_audit_missing:"+name)
                audits[name]=sha(JOB/name)
    files=[PROTOCOL,*sorted(Path("tooling/ai-engines").glob("prop_v17_*.py")),
        Path("tooling/ai-engines/independent_ledger_auditor.py"),
        *[Path("tooling/ai-engines")/n for n in ("prop_v16_paths.py","prop_v15_paths.py",
        "prop_v15_accounts.py","prop_v14_paths.py","prop_v14_accounts.py","prop_v14_review.py",
        "prop_v6_replay.py","prop_v6_account.py","prop_v5_account.py","prop_portfolio_accounts.py",
        "quant_core/gap_aware_execution.py","quant_core/vectorized_sl_active_kernel.py",
        "quant_core/ftmo_execution_and_calendar.py")]]
    value=dict(schema="V17-registered-tiered-risk-v1",tiers=tiers,selection=selection,code_pins={str(p):sha(p) for p in files},
        Dev_audits=audits,Dev_end=DEV_END,later_prices_already_exposed=True,new_full_policy_not_yet_measured=True,
        candidate_A=read(V14/"candidate-freeze.json")["candidate_A"],
        parent_source_admission_sha256=sha(V16/"source-admission-v16.json"),
        parent_V16_freeze_sha256=sha("planning/research/GAP-IMMUNE-MULTIASSET-V16-FREEZE-20261116.json"),
        scan_receipts={a:sha(JOB/f"{a}-scan.json") for a in ("XAUUSD","EURUSD","US500")},
        no_ex_ante_future_path_certificate=True)
    if FREEZE.exists():raise ValueError("V17_preserve_freeze")
    FREEZE.write_text(json.dumps(value,indent=2),encoding="utf-8");save("freeze.json",value)
    event("V17_freeze_needs_commit",tiers=tiers["tiers"],selected=[])


def verify_release():
    r=read(FREEZE)
    if json.loads(subprocess.check_output(["git","show","HEAD:"+FREEZE.as_posix()]))!=r:
        raise ValueError("V17_freeze_uncommitted")
    for p,digest in r["code_pins"].items():
        if sha(p)!=digest:raise ValueError("V17_frozen_code_changed:"+p)
    return r


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("stage",choices=("run","freeze","parent_strict"))
    p.add_argument("--tag",choices=("OLHC","OHLC"),default="OLHC")
    p.add_argument("--full",action="store_true");p.add_argument("--strict",action="store_true")
    a=p.parse_args()
    freeze() if a.stage=="freeze" else parent_strict(a.tag) if a.stage=="parent_strict" else run(a.tag,not a.full,a.strict)

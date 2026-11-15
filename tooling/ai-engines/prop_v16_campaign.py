"""Frozen single-policy lifecycle and separate scalar path/cash audits."""
from collections import Counter
import subprocess
import numpy as np
import independent_ledger_auditor as oracle
import prop_v14_review as review
import prop_v15_accounts as accounts
from prop_v16_common import *
from prop_v16_paths import load,make,CausalFlatSchedule
from quant_core.ftmo_execution_and_calendar import gold_calendar
from quant_core.prop_lifecycle_and_parity import bindings


def paths_audit(tag,dev,strict):
    scope="Dev" if dev else "Full";mode="STRICT" if strict else "PRIMARY"
    end=DEV_END if dev else END
    trades,readers,bars=load(tag,dev,strict)
    ids=read(V14/"candidate-freeze.json")["candidate_A"]
    original={(t["id"],t["source_event"]):t for t in read(V14/"OLHC-strategy-trades.json")
        if t["id"] in ids and t["decision_msc"]<end}
    events=gold_calendar(FIRST,end).events;seen=set();errors=[]
    for i,t in enumerate(trades):
        key=t["id"],t["parent_source_event"]
        if key in seen:raise ValueError("V16_duplicate_frozen_signal")
        seen.add(key);old=original[key]
        for field in ("decision_msc","entry_msc","entry_price_units","stop_units","mode","natural"):
            if old[field]!=t[field]:raise ValueError("V16_frozen_signal_drift:"+field)
        deadline=oracle.v16_causal_cutoff(t["entry_msc"],old["deadline_msc"],t["asset"],events)
        if deadline!=t["deadline_msc"]:raise ValueError("V16_noncausal_deadline")
        r=oracle.audit_v14_path(dict(t,source_uncertain=t["scenario_remaining_source_gaps"]),
            bars[t["asset"]],events,end,scheduled_override=deadline)
        if not r["passed"]:errors.append(dict(i=i,id=t["id"],audit=r))
    receipt=read(JOB/f"{scope}-{tag}-{mode}-path-receipt.json")
    if len(original)!=len(seen)+len(receipt["skipped"]):raise ValueError("V16_frozen_signal_count")
    if errors:
        save(f"{scope}-{tag}-{mode}-path-audit-failed.json",dict(errors=errors))
        raise ValueError("V16_path_audit:"+str(errors[:2]))
    save(f"{scope}-{tag}-{mode}-path-audit.json",dict(passed=True,paths=len(trades),
        frozen_entries_unchanged=True,independent_deadline_arithmetic=True,
        source_uncertain=sum(t["source_uncertain"] for t in trades),
        market_certified=False,same_implementer_and_feed=True))
    event("V16_path_audit_PASS",scope=scope,tag=tag,mode=mode,paths=len(trades))
    return trades,readers


def run(tag,dev,strict):
    if not dev:verify_release()
    scope="Dev" if dev else "Full";mode="STRICT" if strict else "PRIMARY"
    if not (JOB/f"{scope}-{tag}-{mode}-trades.json").exists():make(tag,dev,strict)
    trades,readers=paths_audit(tag,dev,strict)
    calendar=gold_calendar(FIRST,DEV_END if dev else END)
    selection=read(V15/"Dev-selection.json")["cushion"]
    if selection["factor"]!=1.5:raise ValueError("V16_parent_risk_policy")
    # replay_profiles closes over its module event. Rebind so old V15 logs stay immutable.
    with bindings(accounts,event=event):
        rows=accounts.replay_profiles(trades,readers,calendar,[selection],dev)
    save(f"{scope}-{tag}-{mode}-accounts.json",rows)
    event("V16_accounts_complete",scope=scope,tag=tag,mode=mode,accounts=len(rows))
    end=DEV_END if dev else END
    with bindings(review,V14LedgerOracle=oracle.V15LedgerOracle):
        checked=review.audit_accounts(rows,trades,readers,calendar,FIRST,end)
    save(f"{scope}-{tag}-{mode}-account-audit.json",dict(passed=True,accounts=len(checked),
        records=checked,same_implementer_and_feed=True,standalone_decimal_arithmetic=True))
    event("V16_accounts_audit_PASS",scope=scope,tag=tag,mode=mode,accounts=len(checked))


def parity():
    from prop_v16_paths import core_inputs
    from prop_v15_paths import insert_excursions
    from quant_core.gap_aware_execution import GapAwarePathIndex
    checks=[]
    for tag in ("OLHC","OHLC"):
        for strict in (False,True):
            mode="STRICT" if strict else "PRIMARY"
            _,bars,schedule,ms,_,_=core_inputs(True)
            if strict:
                receipt=read(JOB/f"Dev-{tag}-{mode}-path-receipt.json")
                bars={a:insert_excursions(b,receipt["synthetic_patches"],a,DEV_END)[0] for a,b in bars.items()}
                for m in ms.values():m["_index"]=GapAwarePathIndex(bars[m["asset"]],asset=m["asset"],schedule=schedule)
            order="OPEN_LOW_HIGH_CLOSE" if tag=="OLHC" else "OPEN_HIGH_LOW_CLOSE"
            import prop_v14_paths as parent
            with bindings(parent,END=DEV_END):current,_,missing=parent.build(ms,order,bars)
            old=read(JOB/f"Dev-{tag}-{mode}-trades.json")
            fields=("id","source_event","decision_msc","entry_msc","entry_price_units",
                "stop_units","deadline_msc","exit_msc","exit_price_units","reason",
                "activation_time","reference","entry_quote_index","exit_quote_index")
            if missing or len(current)!=len(old) or any(t[k]!=p[k] for t,p in zip(current,old) for k in fields):
                raise ValueError("V16_A_grid_correction_financial_drift")
            inactive=[]
            for t,p in zip(current,old):
                if t["protection_price"]==p["protection_price"]:continue
                if t["activation_time"] is not None:raise ValueError("V16_A_active_protection_drift")
                inactive.append(dict(id=t["id"],entry=t["entry_msc"],
                    unused_old_level=p["protection_price"],unused_corrected_level=t["protection_price"]))
            checks.append(dict(tag=tag,mode=mode,trades=len(old),all_financial_and_active_levels_equal=True,
                inactive_protection_metadata_deltas=inactive))
    save("grid-corrected-A-parity.json",dict(passed=True,checks=checks,
        accounts_reused_only_after_exact_financial_and_protection_parity=True))
    event("V16_A_grid_correction_parity_PASS",checks=checks)


def freeze():
    selected=read(JOB/"selection.json")
    if selected["selected"]:raise ValueError("V16_multiasset_integration_needed_before_freeze")
    audits={}
    for tag in ("OLHC","OHLC"):
        for mode in ("PRIMARY","STRICT"):
            for kind in ("path","account"):
                name=f"Dev-{tag}-{mode}-{kind}-audit.json"
                if not read(JOB/name)["passed"]:raise ValueError("V16_Dev_audit_incomplete")
                audits[name]=sha(JOB/name)
    scan_audit="grid-corrected-scan-independent-audit.json"
    if not read(JOB/scan_audit)["passed"]:raise ValueError("V16_scan_audit_incomplete")
    if not read(JOB/"grid-corrected-A-parity.json")["passed"]:raise ValueError("V16_A_grid_parity_missing")
    files=[PROTOCOL,*sorted(Path("tooling/ai-engines").glob("prop_v16_*.py")),
        Path("tooling/ai-engines/independent_ledger_auditor.py"),
        *[Path("tooling/ai-engines")/n for n in ("prop_v14_paths.py","prop_v14_accounts.py",
        "prop_v14_review.py","prop_v15_paths.py","prop_v15_accounts.py","prop_v6_replay.py",
        "prop_v6_account.py","prop_v5_account.py","prop_portfolio_accounts.py",
        "quant_core/gap_aware_execution.py","quant_core/vectorized_sl_active_kernel.py",
        "quant_core/ftmo_execution_and_calendar.py")]]
    result=dict(schema="V16-fixed-causal-policy-v1",selected_additions=[],
        candidate_A=read(V14/"candidate-freeze.json")["candidate_A"],
        code_pins={str(p):sha(p) for p in files},audits=audits,
        source_manifest_sha256=sha(JOB/"source-admission-v16.json"),
        scan_audit_sha256=sha(JOB/scan_audit),
        registration_sha256=sha(JOB/"scan-registration.json"),
        selection=selected,risk=read(V15/"Dev-selection.json")["cushion"],
        Development=[FIRST,DEV_END],evaluation_end=END,
        zero_gap_qualified=selected["zero_gap_A_qualified"],
        later_prices_preexposed=True,new_policy_later_performance_measured=False)
    if FREEZE.exists():raise ValueError("preserve_V16_freeze")
    FREEZE.write_text(json.dumps(result,indent=2),encoding="utf-8")
    save("freeze.json",result);event("V16_freeze_needs_commit")


def verify_release():
    cfg=read(FREEZE)
    blob=json.loads(subprocess.check_output(["git","show","HEAD:"+FREEZE.as_posix()]))
    if cfg!=blob:raise ValueError("V16_freeze_uncommitted")
    for p,digest in cfg["code_pins"].items():
        if sha(p)!=digest:raise ValueError("V16_frozen_code_drift:"+p)
    return cfg


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("stage",choices=("run","freeze","parity"))
    p.add_argument("--tag",choices=("OLHC","OHLC"),default="OLHC")
    p.add_argument("--full",action="store_true");p.add_argument("--strict",action="store_true")
    a=p.parse_args()
    globals()[a.stage]() if a.stage in ("freeze","parity") else run(a.tag,not a.full,a.strict)

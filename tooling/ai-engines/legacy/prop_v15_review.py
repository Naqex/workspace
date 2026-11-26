"""Separate bridge/path checks and the standalone Decimal lifecycle oracle."""
from collections import Counter
import numpy as np
import independent_ledger_auditor as oracle
import prop_v14_review as parent
from prop_v15_common import *
from prop_v15_paths import load,patch_plan
from quant_core.ftmo_execution_and_calendar import gold_calendar,execution_schedule
from quant_core.prop_lifecycle_and_parity import bindings


def audit_evidence():
    evidence=read(JOB/"bridge-evidence.json")
    checked=Counter()
    for row in evidence["rows"]:
        r=oracle.bridge_screen(row["side"],row["level"],row["before_price"],row["after_price"],
            row["missing_minutes"],row["sigma_prior"],row["adjacent_range"],row["envelope"],
            first=row["before"]+60000,end=row["after"])
        for field in ("status","signed_distances","conditional_source_exclusion"):
            if r[field]!=row["screen"][field]:raise ValueError("V15_independent_bridge:"+field)
        checked[r["status"]]+=1
    cfg=read(V14/"candidate-freeze.json")
    trades=[t for t in read(V14/"OLHC-strategy-trades.json") if t["id"] in cfg["candidate_A"]]
    duration={}
    for name,first,end in (("development",FIRST,DEV_END),("validation",DEV_END,END)):
        selected=[t for t in trades if first<=t["decision_msc"]<end]
        duration[name]=oracle.audit_duration_censorship(selected,
            evidence["groups"]["DEV" if name=="development" else "VALIDATION"])
    save("independent-bridge-duration-audit.json",dict(passed=True,bridge_occurrences=dict(checked),
        duration=duration,same_implementer_and_feed=True,deterministic_market_bound=False))


def audit_paths(tag,dev,mode="PRIMARY"):
    end=DEV_END if dev else END;stage="Dev" if dev else "Full"
    trades,readers,bars=load(tag,dev,mode)
    schedule=execution_schedule(FIRST,end)
    cfg=read(V14/"candidate-freeze.json")
    originals=[t for t in read(V14/f"{tag}-strategy-trades.json")
        if t["id"] in cfg["candidate_A"] and t["decision_msc"]<end]
    old={(t["id"],t["source_event"]):t for t in originals}
    seen=set();results=[]
    for t in trades:
        key=t["id"],t["parent_source_event"]
        if key in seen:raise ValueError("V15_duplicate_frozen_event")
        seen.add(key);source=old[key]
        for field in ("entry_msc","entry_price_units","stop_units","decision_msc","deadline_msc"):
            if source[field]!=t[field]:raise ValueError("V15_signal_drift:"+field)
        if source["source_uncertain"]!=t["original_source_uncertain"]:
            raise ValueError("V15_erased_parent_uncertainty")
        local=dict(t,source_uncertain=t["scenario_remaining_source_gaps"])
        r=oracle.audit_v14_path(local,bars[t["asset"]],schedule.events,end)
        if not r["passed"]:raise ValueError(f"V15_path:{key}:{r}")
        results.append(r)
    if seen!=set(old):raise ValueError("V15_frozen_signal_loss")
    receipt=read(JOB/f"{stage}-{tag}-{mode}-path-receipt.json")
    from prop_v15_evidence import bars_for
    for asset,data in bars.items():
        original=bars_for(asset,dev)
        if not np.array_equal(data[np.searchsorted(data["t"],original["t"])],original):
            raise ValueError("V15_observed_source_mutation")
    targeted=Counter()
    for p in receipt["patches"]:
        if not FIRST<=p["at"]<end:raise ValueError("V15_stress_outside_fence")
        # An unknown-source patch must be a time not already recorded, not a market closure.
        if schedule.off_kind(p["at"],p["asset"]) is not None:
            raise ValueError("V15_patch_during_known_closure")
        original=bars_for(p["asset"],dev);j=int(original["t"].searchsorted(p["at"]))
        if j<len(original) and original["t"][j]==p["at"]:raise ValueError("V15_patch_over_observed")
        for target in p["targets"]:
            if not target["entry"]<=p["at"]<=target["exit"]:raise ValueError("V15_inactive_target")
            targeted[target["id"]]+=1
    save(f"{stage}-{tag}-{mode}-independent-path-audit.json",dict(passed=True,paths=len(results),
        source_events=len(seen),target_occurrences=dict(targeted),synthetic_bars=receipt["synthetic_bars"],
        observed_bars_preserved=True,same_implementer_and_feed=True,market_certified=False))
    return trades,readers


def run(tag,stage):
    dev=stage in ("grid","cushion")
    end=DEV_END if dev else END;scope="Dev" if dev else "Full"
    mode="ALL_UNCERTIFIED" if stage=="strict" else "PRIMARY"
    trades,readers=load(tag,dev,mode)[:2]
    expected=read(JOB/f"{scope}-{tag}-{stage}-accounts.json")
    with bindings(parent,V14LedgerOracle=oracle.V15LedgerOracle):
        records=parent.audit_accounts(expected,trades,readers,gold_calendar(FIRST,end),FIRST,end)
    save(f"{scope}-{tag}-{stage}-audit.json",dict(passed=True,accounts=len(records),
        records=records,same_implementer_and_feed=True,independent_decimal_arithmetic=True))
    event("V15_account_audit_PASS",tag=tag,scope=scope,stage_name=stage,accounts=len(records))


def sleeve_books(tag):
    from prop_v15_evidence import bars_for
    from prop_v15_paths import readers_for
    from prop_v15_accounts import SleeveBook,execution_bindings
    from quant_core.prop_lifecycle_and_parity import simulate
    cfg=read(V14/"candidate-freeze.json")
    trades=read(V14/f"{tag}-strategy-trades.json")
    bars={a:bars_for(a) for a in ("XAUUSD","EURUSD")}
    order="OPEN_LOW_HIGH_CLOSE" if tag=="OLHC" else "OPEN_HIGH_LOW_CLOSE"
    readers=readers_for(bars,trades,order,False,trades)
    accounts=[SleeveBook(FIRST,END,model,sleeve_id=identity)
        for identity in cfg["candidate_B"] for model in ("SYM_FLAT","ASYM_FLAT")]
    calendar=gold_calendar(FIRST,END)
    with execution_bindings():rows=simulate(trades,readers,accounts,FIRST,END,calendar)
    save(f"{tag}-sleeve-books.json",rows)
    with bindings(parent,V14LedgerOracle=oracle.V15LedgerOracle):
        records=parent.audit_accounts(rows,trades,readers,calendar,FIRST,END)
    save(f"{tag}-sleeve-books-audit.json",dict(passed=True,accounts=len(records),records=records,
        fixed_reference_risk_usd=150,DD_scope="floating equity R-DD at actual floored lot size, not a portfolio policy",
        same_implementer_and_feed=True))
    event("V15_sleeve_attribution_audit_PASS",tag=tag,books=len(rows))


def baseline_reuse(tag):
    trades,readers=load(tag,False)[:2]
    receipt=read(JOB/f"Full-{tag}-PRIMARY-path-receipt.json")
    if receipt["patches"]:raise ValueError("cannot_reuse_baseline_after_path_change")
    cfg=read(V14/"candidate-freeze.json")
    original=[t for t in read(V14/f"{tag}-strategy-trades.json") if t["id"] in cfg["candidate_A"]]
    fields=("id","asset","side","entry_msc","entry_price_units","stop_units","decision_msc",
        "deadline_msc","exit_msc","exit_price_units","reason","entry_quote_index","exit_quote_index","reference")
    if len(trades)!=len(original) or any(t[k]!=p[k] for t,p in zip(trades,original) for k in fields):
        raise ValueError("V15_primary_baseline_financial_tape_drift")
    source=V14/f"{tag}-A-NEXT_QUOTE-accounts.json"
    expected=[r for r in read(source) if r["kind"] in ("CHALLENGE","STANDALONE_FULL")]
    records=parent.audit_accounts(expected,trades,readers,gold_calendar(FIRST,END),FIRST,END)
    save(f"Full-{tag}-baseline-reuse-audit.json",dict(passed=True,accounts=len(records),records=records,
        unchanged_financial_tape=True,primary_stress_patches=0,source=str(source),
        source_sha256=sha(source),same_implementer_and_feed=True))
    event("V15_baseline_reuse_audit_PASS",tag=tag,accounts=len(records))


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("stage",choices=("evidence","paths_dev","paths_full","paths_strict","grid","cushion","sizing","strict","sleeves","baseline"))
    p.add_argument("--tag",choices=("OLHC","OHLC"),default="OLHC")
    a=p.parse_args()
    if a.stage=="evidence":audit_evidence()
    elif a.stage=="sleeves":sleeve_books(a.tag)
    elif a.stage=="baseline":baseline_reuse(a.tag)
    elif a.stage.startswith("paths_"):audit_paths(a.tag,a.stage=="paths_dev",
        "ALL_UNCERTIFIED" if a.stage=="paths_strict" else "PRIMARY")
    else:run(a.tag,a.stage)

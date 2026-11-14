"""Commit-frozen composition, whitelisted 2024 signals and one joint replay."""
from datetime import datetime, timezone
from pathlib import Path
import subprocess

from prop_campaign_source import Prices, PARENT, CALENDAR, stamp
from prop_atlas_scan import candidates
from prop_portfolio_common import (
    ROOT, JOB, V1, MODELS, PROTOCOL, DECISION, START, END, FINAL,
    read, write_json, digest, event, price_scope,
)
from prop_portfolio_accounts import PortfolioAccount, replay
from prop_portfolio_ticks import collect, realize_ticks


def freeze():
    core = read(JOB / "core-decision.json")
    satellites = read(JOB / "final-satellite-decision.json")
    if core["selected"] != "A_Original":
        raise ValueError("this_validation_adapter_requires_original_core")
    files = list(Path("tooling/ai-engines").glob("prop_portfolio_*.py")) + [
        Path("tooling/ai-engines/prop_campaign_accounts.py"),
        Path("tooling/ai-engines/prop_atlas_scan.py"), PROTOCOL, CALENDAR,
    ]
    result = dict(
        schema="PROP-PORTFOLIO-V3-COMPOSITION-v1", core=core["selected"],
        satellites=satellites["selected"],
        utc=datetime.now(timezone.utc).isoformat(), selection_end_exclusive=END,
        development="2022-2023 only", validation="2024 already exposed",
        holdout="2025-2026 closed", prices2024_used_in_selection=False,
        prices2025_2026_read=False,
        core_risk_usd=[200,175,125], satellite_risk_usd=[100,100,75],
        throttle_equity_usd=[48000,47000], throttle_caps_usd=[150,90],
        daily_realized_halt_usd=1000, shared_open_stop_risk_usd=500,
        internal_projected_equity_floor_usd=46500,
        core_decision_sha256=digest(JOB / "core-decision.json"),
        satellite_decision_sha256=digest(JOB / "final-satellite-decision.json"),
        source_dev_manifest_sha256=digest(JOB / "eur-native-dev-v1/manifest.json"),
        source_dev_trades_sha256=digest(JOB / "eur-satellite-dev-trades.json"),
        code_and_rules=[dict(path=p.as_posix(),sha256=digest(p)) for p in sorted(files)],
        reward_proxy=dict(days=30,min_profit_usd=20,trader_share=.8,
                          cash_debit_share=1,administrative_delay_days=0),
        target_specs_news_margin_and_forward_verified=False,
    )
    write_json(DECISION, result)
    write_json(JOB / "composition-freeze.json", result)
    event("composition_frozen_needs_git_commit", core=result["core"],
          satellites=result["satellites"], decision_sha256=digest(DECISION))


def release():
    head = subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()
    content = subprocess.check_output(["git","show",head+":"+DECISION.as_posix()])
    if content != DECISION.read_bytes():
        raise ValueError("decision_must_be_committed_before_validation")
    decision = read(DECISION)
    for pin in decision["code_and_rules"]:
        if digest(pin["path"]) != pin["sha256"]:
            raise ValueError("code_or_rules_changed_after_freeze:"+pin["path"])
    write_json(JOB / "validation-release.json",dict(
        decision_commit=head,decision_sha256=digest(DECISION),
        utc=datetime.now(timezone.utc).isoformat(),cutoff=FINAL,no2025_2026=True,
    ))
    event("validation_released",decision_commit=head)


def prepare_validation():
    price_scope(FINAL)
    decision = read(DECISION)
    selected = decision["satellites"]
    if selected != ["EURUSD.SWEEP.ASIA.LONDON.DAY"]:
        raise ValueError("unexpected_frozen_satellite_set")
    cfg = read(ROOT / "eurusd-b0-20261113/config-attempt-1.json")
    hours = []
    pins = []
    for first in ("20211101","20220101","20230101","20240101"):
        folder = ROOT / "eurusd-b0-20261113/prepared-v1" / first
        seal = read(folder / "seal.json")
        source = next(s for s in cfg["sources"] if s["first_day"]==first)
        if seal["binding"]["source"] != source:
            raise ValueError("validation_H1_source_binding")
        proof = next(p for p in seal["files"] if p["name"]=="bars.json")
        if digest(folder / "bars.json") != proof["sha256"]:
            raise ValueError("validation_H1_seal")
        hours.extend(read(folder / "bars.json")["h1"])
        pins.append(dict(path=str(folder / "bars.json"),sha256=proof["sha256"]))
    signals, abstentions = candidates(hours,"EURUSD",first=END,end=FINAL,
                                       only_cells=selected)
    write_json(JOB / "eur-satellite-validation-signals.json",signals)
    write_json(JOB / "eur-satellite-validation-signal-proof.json",dict(
        pins=pins,cells=selected,abstentions=abstentions,raw=len(signals),
        code_sha256=digest("tooling/ai-engines/prop_atlas_scan.py"),
        parameter_reselection=False,
    ))
    manifest = collect(signals,FINAL)
    trades, skipped = realize_ticks(signals,manifest,FINAL)
    write_json(JOB / "eur-satellite-validation-trades.json",trades)
    write_json(JOB / "eur-satellite-validation-funnel.json",dict(
        raw=len(signals),filled=len(trades),skipped=skipped,
    ))


def phase3():
    price_scope(FINAL)
    decision = read(DECISION)
    for pin in decision["code_and_rules"]:
        if digest(pin["path"]) != pin["sha256"]:
            raise ValueError("frozen_phase3_code_changed:"+pin["path"])
    baseline = read(V1 / "frozen-system-SYM_FLAT-trades.json")
    other = read(V1 / "frozen-system-ASYM_FLAT-trades.json")
    keys = ("entry_msc","exit_msc","entry_price_units","exit_price_units","stop_units")
    if [[t[k] for k in keys] for t in baseline] != [[t[k] for k in keys] for t in other]:
        raise ValueError("cost_models_must_share_fixed_entry_exit_paths")
    core = [dict(t,asset="XAUUSD",role="CORE",regime_weight=1) for t in baseline]
    satellite = read(JOB / "eur-satellite-dev-trades.json") + read(
        JOB / "eur-satellite-validation-trades.json")
    trades = sorted(core+satellite,key=lambda t:(t["entry_msc"],t["role"]=="SATELLITE"))
    manifest = read(JOB / "eur-native-dev-v1/manifest.json")
    manifest.update(read(JOB / "eur-native-validation-v1/manifest.json"))
    readers = dict(
        XAUUSD=Prices(read(PARENT / "attempt-2/binary-manifest.json"),FINAL),
        EURUSD=Prices(manifest,FINAL),
    )
    write_json(JOB / "system-trades.json",trades)
    write_json(JOB / "system-eur-manifest.json",manifest)
    accounts = []
    for model in MODELS:
        for portfolio in (False,True):
            for year in (2022,2023,2024):
                for month in range(1,13):
                    accounts.append(PortfolioAccount(
                        stamp(f"{year}-{month:02d}-01"),FINAL,model,rolling=True,
                        include_satellite=portfolio,scaled=False,
                    ))
    rows = replay(trades,readers,accounts,end=FINAL,progress=event)
    for model in MODELS:
        for portfolio in (False,True):
            subset=[r for r in rows if r["cell"]==model and r["include_satellite"]==portfolio]
            name="PORTFOLIO" if portfolio else "SINGLE"
            write_json(JOB / f"lifecycle-{model}-{name}.json",subset)
            event("lifecycle_complete",model=model,system=name,starts=len(subset),
                  step1=sum(len(c["phase_passes"])>=1 for c in subset),
                  both=sum(len(c["phase_passes"])==2 for c in subset),
                  payouts=sum(len(c["payouts"]) for c in subset))


if __name__ == "__main__":
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("stage",choices=("freeze","release","prepare_validation","phase3"))
    globals()[parser.parse_args().stage]()

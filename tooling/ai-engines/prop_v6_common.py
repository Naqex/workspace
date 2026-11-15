"""V6's explicitly authorized, one-shot price scope; historical guards stay intact."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import subprocess
from prop_campaign_source import ROOT, START, FINAL, HOUR, DAY, stamp, read, write_json, digest
from prop_portfolio_common import JOB as V3, MODELS
from prop_campaign_source import PARENT

JOB = ROOT / "prop-v4-harvest-v6-20261115"
END = stamp("2026-10-14")
PROTOCOL = Path("planning/research/PROP-V4-HARVEST-V6-PROTOCOL-20261115.md")
DECISION = Path("planning/research/PROP-V4-HARVEST-V6-DECISION-20261115.json")
CALENDAR = Path("planning/research/PROP-V6-SESSION-CALENDAR-20261115.json")


def event(stage, **values):
    JOB.mkdir(parents=True, exist_ok=True)
    row = dict(stage=stage, utc=datetime.now(timezone.utc).isoformat(), **values)
    write_json(JOB / "status.json", row)
    with (JOB / "events.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")
    print(row, flush=True)


def check_freeze(require_release=True):
    release = read(JOB / ("holdout-release.json" if require_release else "freeze-receipt.json"))
    blob = subprocess.check_output(["git", "show", release["commit"] + ":" + DECISION.as_posix()])
    if json.loads(blob) != read(DECISION):
        raise ValueError("V6_committed_candidate_changed")
    for pin in read(DECISION)["pins"]:
        if digest(pin["path"]) != pin["sha256"]:
            raise ValueError("V6_frozen_signal_policy_or_assumption_changed:" + pin["path"])
    return read(DECISION)


def freeze():
    from statistics import median
    historical = read(V3 / "system-trades.json")
    # Estimate an explicit conditional Ask model from admitted Development only.
    spreads = [t["entry_quote"][2] - t["entry_quote"][1] for t in historical
               if t["asset"] == "XAUUSD" and t["entry_msc"] < stamp("2024-01-01")]
    files = [PROTOCOL, CALENDAR, Path("tooling/ai-engines/prop_v6_account.py"),
             Path("tooling/ai-engines/prop_v6_signals.py"),
             Path("tooling/ai-engines/prop_v6_paths.py"),
             Path("tooling/ai-engines/prop_v6_replay.py")]
    files += [Path("tooling/ai-engines") / p for p in (
        "prop_v5_account.py", "prop_cocore_v4.py", "prop_portfolio_accounts.py",
        "prop_campaign_accounts.py", "prop_campaign_exits.py",
        "xau_h1_stage0_source.py", "prop_campaign_source.py")]
    files += [V3 / "system-trades.json", V3 / "system-eur-manifest.json",
              PARENT / "attempt-2/binary-manifest.json"]
    out = dict(schema="PROP-V4-HARVEST-V6-FREEZE-v1",
               utc=datetime.now(timezone.utc).isoformat(), candidate="V4_Harvest",
               signals=["XAUUSD.H1A_ASIA", "EURUSD.SWEEP.ASIA.LONDON.DAY"],
               mechanism="PARENT", ratchet=False, d1=False, d2=False,
               risk_usd=[200, 175, 125], open_cap_usd=800, reserve_floor_usd=46000,
               equity_throttle_usd=[48000, 47000], throttle_caps_usd=[150, 90],
               daily_realized_halt_usd=1000,
               harvest=dict(phase=3, days=14, pre_freeze_balance=50500,
                            due_proximity_hours=48, lock_balance=51000,
                            min_profit=20, trader_share=.8, debit_share=1,
                            administrative_delay_days=0),
               start_inclusive=FINAL, end_exclusive=END,
               gold_m1_ask_proxy_spread_units=int(median(spreads)),
               proxy_estimation="median A entry spread Development 2022-2023, integer .001 USD/oz",
               m1_paths=["OPEN_LOW_HIGH_CLOSE", "OPEN_HIGH_LOW_CLOSE"],
               m1_offsets_ms=[0, 20000, 40000, 59999],
               m1_claim="conditional ordering scenarios; neither observed ticks nor certified DD bound",
               missing_path="retain unresolved exposure; never count an unknown path as a clean pass",
               tail="do not force-close at sample end; open positions are right-censored",
               holdout_history="first V6 evaluation; global pristine OOS not certified",
               pins=[dict(path=p.as_posix(), sha256=digest(p)) for p in files])
    write_json(DECISION, out)
    event("V6_candidate_frozen_needs_commit", spread_units=out["gold_m1_ask_proxy_spread_units"])


def release():
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    blob = subprocess.check_output(["git", "show", head + ":" + DECISION.as_posix()])
    if json.loads(blob) != read(DECISION):
        raise ValueError("V6_freeze_not_committed")
    receipt = dict(commit=head, git_blob_sha256=hashlib.sha256(blob).hexdigest(),
                   utc=datetime.now(timezone.utc).isoformat(),
                   authorized_user_task="ed4d3a18-01c0-4907-8e16-5ffbd13e4440",
                   start_inclusive=FINAL, end_exclusive=END,
                   one_shot=True, parameter_changes_allowed=False)
    if (JOB / "holdout-release.json").exists():
        raise ValueError("V6_holdout_already_released")
    write_json(JOB / "freeze-receipt.json", receipt)
    check_freeze(False)
    write_json(JOB / "holdout-release.json", receipt)
    event("V6_holdout_released", commit=head)


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("stage", choices=("freeze", "release"))
    globals()[p.parse_args().stage]()

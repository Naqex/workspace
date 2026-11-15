"""V7 is an explicitly post-holdout audit, never a new clean OOS claim."""
from datetime import datetime, timezone
from pathlib import Path
import json
import subprocess
from prop_v6_common import (ROOT, START, FINAL, END, HOUR, DAY, V3, PARENT, MODELS,
                            read, write_json, digest, stamp, JOB as V6)

JOB = ROOT / "prop-gold-v7-20261115"
PROTOCOL = Path("planning/research/PROP-GOLD-V7-PROTOCOL-20261115.md")
DECISION = Path("planning/research/PROP-GOLD-V7-DECISION-20261115.json")
CALENDAR = Path("planning/research/PROP-V7-SESSION-CALENDAR-20261115.json")
LABEL = "POST_HOLDOUT_DIAGNOSTIC_FULL_SAMPLE_2022_2026"
POLICIES = {"COCORE_FIXED": (200, 175, 125), "GOLD_V4": (200, 175, 125),
            "GOLD_SCALED": (250, 200, 150)}
ORDERS = ("OPEN_LOW_HIGH_CLOSE", "OPEN_HIGH_LOW_CLOSE")


def event(stage, **values):
    JOB.mkdir(parents=True, exist_ok=True)
    row = dict(stage=stage, utc=datetime.now(timezone.utc).isoformat(), **values)
    write_json(JOB / "status.json", row)
    with (JOB / "events.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")
    print(row, flush=True)


def freeze():
    files = [PROTOCOL, CALENDAR] + list(Path("tooling/ai-engines").glob("prop_v7_*.py"))
    files += [Path("tooling/ai-engines") / n for n in (
        "prop_v6_account.py", "prop_v6_paths.py", "prop_v6_signals.py",
        "prop_v5_account.py", "prop_cocore_v4.py", "prop_portfolio_accounts.py",
        "prop_campaign_accounts.py", "prop_campaign_exits.py")]
    files += [V3 / "system-trades.json", V6 / "OPEN_LOW_HIGH_CLOSE/holdout-trades.json",
              V6 / "eur-manifest.json", V6 / "gold-source-proof.json"]
    write_json(DECISION, dict(
        schema="PROP-GOLD-V7-DECISION-v1", label=LABEL,
        owner_task="66e95afe-4594-4ddf-a63c-0278e67b3b78", utc=datetime.now(timezone.utc).isoformat(),
        policies={k: list(v) for k, v in POLICIES.items()}, main_signal="XAUUSD.A_Original.BOTH",
        eurusd_active=False, eurusd_only_counterfactual=True, ratchet=False,
        cap_usd=800, internal_floor_usd=46000, throttle_equity=[48000, 47000],
        throttle_caps=[150, 90], daily_realized_halt_usd=1000,
        firm_limits=dict(daily_pct=5, static_pct=10),
        calendar_buffer_minutes=2, fallback_on_arbitrary_gap=False,
        calendar_policy="min(legacy conservative holiday guard, verified target close) minus2minutes",
        natural_SL_entry_unchanged=True, extra_horizon_search=False, selection_claim=False,
        funded_starts="Jan1 of each2022-2026, all continued to Oct13,2026",
        reference_risk_usd=150, reference_sides=["BOTH", "BUY", "SELL"],
        source="2022-24 admitted ticks;2025-26 two conditional Gold M1 scenarios/EUR native ticks",
        supplementary="three pre-existing Gold Top10 cells, Development curves only; no new sleeves",
        pins=[dict(path=p.as_posix(), sha256=digest(p)) for p in sorted(files)]))
    event("V7_protocol_frozen_needs_commit", label=LABEL)


def bind():
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    blob = subprocess.check_output(["git", "show", head + ":" + DECISION.as_posix()])
    if json.loads(blob) != read(DECISION):
        raise ValueError("V7_decision_not_committed")
    for p in read(DECISION)["pins"]:
        if digest(p["path"]) != p["sha256"]:
            raise ValueError("V7_frozen_code_changed:" + p["path"])
    write_json(JOB / "run-release.json", dict(commit=head, label=LABEL,
               utc=datetime.now(timezone.utc).isoformat(), clean_OOS=False))
    event("V7_post_holdout_audit_released", commit=head)


def verify():
    r = read(JOB / "run-release.json")
    blob = subprocess.check_output(["git", "show", r["commit"] + ":" + DECISION.as_posix()])
    if json.loads(blob) != read(DECISION):
        raise ValueError("V7_committed_decision_changed")
    for p in read(DECISION)["pins"]:
        if digest(p["path"]) != p["sha256"]:
            raise ValueError("V7_frozen_input_changed:" + p["path"])


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("stage", choices=("freeze", "bind"))
    globals()[p.parse_args().stage]()

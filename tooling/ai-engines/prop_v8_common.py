"""V8 scope, immutable registration and one backward release."""
from pathlib import Path
from datetime import datetime, timezone
import json
import subprocess
from prop_v7_common import ROOT, JOB as V7, V6, V3, PARENT, MODELS, ORDERS, HOUR, DAY
from prop_campaign_source import read, write_json, digest, stamp

JOB = ROOT / "prop-gold-v8-20261115"
PROTOCOL = Path("planning/research/PROP-GOLD-V8-PROTOCOL-20261115.md")
DECISION = Path("planning/research/PROP-GOLD-V8-DECISION-20261115.json")
CALENDAR = Path("planning/research/PROP-V8-SESSION-CALENDAR-20261115.json")
START, DEV_END, END = stamp("2022-01-01"), stamp("2024-01-01"), stamp("2026-10-14")
BACK_START, BACK_END = stamp("2018-01-01"), stamp("2022-01-01")
CELLS = tuple("XAUUSD.SWEEP.PREVDAY.LONDON." + x for x in ("DAY", "24H", "48H"))
CACHE = ROOT / "gold-continuous-B2-20261113-v1/source-cache"


def event(stage, **kwargs):
    JOB.mkdir(parents=True, exist_ok=True)
    row = dict(stage=stage, utc=datetime.now(timezone.utc).isoformat(), **kwargs)
    write_json(JOB / "status.json", row)
    with (JOB / "events.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")
    print(row, flush=True)


def pins():
    paths = [PROTOCOL, CALENDAR] + list(Path("tooling/ai-engines").glob("prop_v8_*.py"))
    paths += [Path("tooling/ai-engines") / f for f in (
        "prop_v6_account.py", "prop_v6_replay.py", "prop_v7_accounts.py", "prop_v7_review.py",
        "prop_v6_review.py", "prop_portfolio_accounts.py", "prop_portfolio_review.py",
        "prop_v5_account.py", "prop_campaign_source.py", "xau_h1_stage0_source.py")]
    return [dict(path=p.as_posix(), sha256=digest(p)) for p in sorted(paths)]


def register():
    if (JOB / "registration.json").exists():
        raise ValueError("V8_registration_already_exists")
    write_json(JOB / "registration.json", dict(pins=pins(), dev_only=True,
        backward_opened=False, holdout_label="BACKWARD_HISTORICAL_VALIDATION_PRIOR_EXPOSURE"))
    event("V8_registered_Dev_only")


def verify(dev=False):
    name = "registration.json" if dev else "release.json"
    data = read(JOB / name)
    for p in data["pins"]:
        if digest(p["path"]) != p["sha256"]:
            raise ValueError("V8_frozen_changed:" + p["path"])
    return data


def release():
    if (JOB / "release.json").exists():
        raise ValueError("V8_release_already_exists")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    expected = subprocess.check_output(["git", "show", head + ":" + DECISION.as_posix()])
    if json.loads(expected) != read(DECISION):
        raise ValueError("V8_composition_not_committed")
    write_json(JOB / "release.json", dict(commit=head, pins=pins(), decision=read(DECISION),
               clean_OOS=False, backward_one_release=True))
    event("V8_composition_released", commit=head)

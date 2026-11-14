"""V3 scope and progress; only this campaign's outputs are mutable."""
from datetime import datetime, timezone
import json
from pathlib import Path

from prop_campaign_source import ROOT, START, END, FINAL, HOUR, DAY, read, write_json, digest

JOB = ROOT / "prop-portfolio-v3-20261114"
ATLAS = ROOT / "prop-atlas-v2-20261114"
V1 = ROOT / "prop-qualification-campaign-20261114"
MODELS = ("SYM_FLAT", "ASYM_FLAT")
PROTOCOL = Path("planning/research/PROP-PORTFOLIO-V3-PROTOCOL-20261114.md")
DECISION = Path("planning/research/PROP-PORTFOLIO-V3-DECISION-20261114.json")


def event(stage, **fields):
    record = {"stage": stage, "utc": datetime.now(timezone.utc).isoformat(), **fields}
    write_json(JOB / "status.json", record)
    with (JOB / "events.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record) + "\n")
    print(record, flush=True)


def price_scope(cutoff):
    if cutoff == END:
        return
    if cutoff != FINAL:
        raise ValueError("V3_price_scope_excludes_2025_2026")
    release = read(JOB / "validation-release.json")
    if release["decision_sha256"] != digest(DECISION):
        raise ValueError("V3_validation_before_committed_composition")

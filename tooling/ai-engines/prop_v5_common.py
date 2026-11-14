"""V5 scope and evidence; older jobs are immutable inputs."""
from datetime import datetime, timezone
from pathlib import Path
import json
from prop_campaign_source import ROOT, START, END, FINAL, HOUR, DAY, read, write_json, digest, Prices, stamp
from prop_portfolio_common import JOB as V3, V1, ATLAS, MODELS
from prop_cocore_v4 import JOB as V4

JOB = ROOT / "prop-overnight-v5-20261115"
PROTOCOL = Path("planning/research/PROP-OVERNIGHT-V5-PROTOCOL-20261115.md")
DECISION = Path("planning/research/PROP-OVERNIGHT-V5-DECISION-20261115.json")


def event(stage, **values):
    JOB.mkdir(parents=True, exist_ok=True)
    row = dict(stage=stage, utc=datetime.now(timezone.utc).isoformat(), **values)
    write_json(JOB / "status.json", row)
    with (JOB / "events.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")
    print(row, flush=True)

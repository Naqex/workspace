"""V18 immutable inputs and append-only job receipts."""
from pathlib import Path
from datetime import datetime, timezone
import json
from prop_v17_common import ROOT, V14, V15, V16, JOB as V17, FIRST, DEV_END, END, read, sha

JOB = ROOT / "final-convergence-v18-20261116"
PROTOCOL = Path("planning/research/FINAL-CONVERGENCE-V18-PROTOCOL-20261116.md")
FREEZE = PROTOCOL.with_name("FINAL-CONVERGENCE-V18-FREEZE-20261116.json")
SEED = 20261116
PATHS = 5000


def save(name, value):
    JOB.mkdir(exist_ok=True)
    with (JOB / name).open("x", encoding="utf-8") as f:
        json.dump(value, f, indent=2, ensure_ascii=False, default=lambda x: x.item())


def event(stage, **values):
    JOB.mkdir(exist_ok=True)
    row = dict(stage=stage, utc=datetime.now(timezone.utc).isoformat(), **values)
    with (JOB / "events.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")
    print(row, flush=True)

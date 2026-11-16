"""V19 exclusive receipts; earlier campaign artifacts are read-only inputs."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
from prop_v18_common import ROOT, V14, V15, V16, V17, JOB as V18, FIRST, DEV_END, END, read

JOB = ROOT / "asymmetric-recovery-and-mt5-v19-20261116"
PROTOCOL = Path("planning/research/ASYMMETRIC-RECOVERY-V19-PROTOCOL-20261116.md")
FREEZE = PROTOCOL.with_name("ASYMMETRIC-RECOVERY-V19-FREEZE-20261116.json")
PATHS = 5000
SEED = 20261116


def sha(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


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

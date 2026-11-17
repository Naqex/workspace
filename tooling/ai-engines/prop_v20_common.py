"""Exclusive V20 receipts; preserve V19 numerical sources and financial freezes."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import gzip
from prop_v19_common import ROOT, JOB as V19, V18, V16, FIRST, DEV_END, END

JOB = ROOT / "voltarget-shadow-v20-20261117"
PROTOCOL = Path("planning/research/VOLTARGET-SHADOW-V20-PROTOCOL-20261117.md")
FREEZE = PROTOCOL.with_name("VOLTARGET-SHADOW-V20-FREEZE-20261117.json")


def read(path):
    path = Path(path)
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8-sig") as f:
            return json.load(f)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8-sig"))
    from evidence_compaction import EvidenceStore
    return json.loads(EvidenceStore(V19).read_bytes(path).decode("utf-8-sig"))


def sha(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def save(name, value):
    JOB.mkdir(parents=True, exist_ok=True)
    if name.endswith(".gz"):
        with gzip.open(JOB / name, "xt", encoding="utf-8", compresslevel=6) as f:
            json.dump(value, f, ensure_ascii=False, default=lambda x: x.item())
        return
    with (JOB / name).open("x", encoding="utf-8", newline="\n") as f:
        json.dump(value, f, indent=2, ensure_ascii=False, default=lambda x: x.item())


def event(stage, **values):
    JOB.mkdir(parents=True, exist_ok=True)
    row = dict(stage=stage, utc=datetime.now(timezone.utc).isoformat(), **values)
    with (JOB / "events.jsonl").open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(row) + "\n")
    print(row, flush=True)

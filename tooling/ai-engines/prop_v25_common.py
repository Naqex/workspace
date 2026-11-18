"""Exclusive V25 evidence; historical producers and attempts stay read-only."""
from pathlib import Path
from prop_v24_common import ROOT, JOB as V24, V19, FIRST, DEV_END, END, read, sha
from prop_v21_common import compressed as parent_compressed, unpack as parent_unpack, event as parent_event
from quant_core.prop_lifecycle_and_parity import bindings
import prop_v21_common as storage
import json

JOB = ROOT / "corpus-isolation-v25-20261118"
PROTOCOL = Path("planning/research/CORPUS-ISOLATION-V25-PROTOCOL-20261118.md")


def save(name, value):
    JOB.mkdir(exist_ok=True)
    with (JOB / name).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)


def compressed(name, value):
    with bindings(storage, JOB=JOB):
        return parent_compressed(name, value)


def unpack(name, job=JOB):
    with bindings(storage, JOB=job):
        return parent_unpack(name)


def event(stage, **values):
    JOB.mkdir(exist_ok=True)
    with bindings(storage, JOB=JOB):
        parent_event(stage, **values)

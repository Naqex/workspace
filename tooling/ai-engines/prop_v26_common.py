"""Exclusive V26 evidence; previously sealed campaigns remain read-only."""
from pathlib import Path
import json
import os
import tempfile
from prop_v25_common import ROOT, JOB as V25, V19, FIRST, DEV_END, END, read, sha
from prop_v21_common import compressed as parent_compressed, unpack as parent_unpack, event as parent_event
from quant_core.prop_lifecycle_and_parity import bindings
import prop_v21_common as storage
from quant_core.job_workspace import JobWorkspace
from quant_core.native_paths import io_path

RUNTIME = JobWorkspace(ROOT / "batch-exact-iso-v26-20261118", Path(__file__).resolve().parents[2])
JOB = RUNTIME.root
PROTOCOL = Path("planning/research/BATCH-EXACT-ISO-V26-PROTOCOL-20261118.md")
FREEZE = PROTOCOL.with_name("BATCH-EXACT-ISO-V26-FREEZE-20261118.json")


def save(name, value):
    RUNTIME.activate()
    with io_path(JOB / name).open("x", encoding="utf-8") as out:
        json.dump(value, out, ensure_ascii=False, indent=2)


def compressed(name, value):
    RUNTIME.activate()
    with bindings(storage, JOB=io_path(JOB)):
        return parent_compressed(name, value)


def unpack(name, job=JOB):
    with bindings(storage, JOB=io_path(job)):
        return parent_unpack(name)


def event(stage, **values):
    RUNTIME.activate()
    with bindings(storage, JOB=io_path(JOB)):
        parent_event(stage, **values)


def activate_runtime():
    env = RUNTIME.environment()
    os.environ.clear()
    os.environ.update(env)
    tempfile.tempdir = None

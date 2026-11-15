"""Measured four-runtime suite; reuse the registered runner's profile sharding."""
import subprocess
import sys
import time
from prop_v16_common import *

BASE="C:/Users/MIIKEY/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe"
RUNTIMES=dict(base=BASE,
    native="D:/ANNAM/TradingWorkspace/projects/trader/foundation_v2/engine_runtime/.venv/Scripts/python.exe",
    statistics="D:/ANNAM/TradingWorkspace/.runtime/research-statistics/Scripts/python.exe",
    worker="D:/ANNAM/TradingWorkspace/projects/integrations/TradingAgents/.venv/Scripts/python.exe")


def run(label):
    started=time.perf_counter();receipts={}
    for group,python in RUNTIMES.items():
        output=JOB/f"tests-{label}-{group}.json"
        if output.exists():raise ValueError("preserve_performance_attempt")
        command=[python,"tooling/ai-engines/quant_test_suite.py","--group",group,
            "--tier","all","--output",str(output)]
        if group=="base":
            command+=["--workers","2"]
            if label!="before":command+=["--profile",str(JOB/"tests-before-base.json")]
        subprocess.run(command,check=True)
        receipts[group]=read(output)
    all_ids={}
    for r in receipts.values():
        if not r["passed"] or r["skipped"]:raise ValueError("V16_matrix_failure_or_skip")
        if set(all_ids)&set(r["timings"]):raise ValueError("duplicate_matrix_ID")
        all_ids.update(r["timings"])
    old=set()
    for group in RUNTIMES:old.update(read(V15/f"tests-{group}-after-runner.json")["timings"])
    if not old<=set(all_ids):raise ValueError("V16_lost_V15_test_ID")
    summary=dict(label=label,total_wall_seconds=time.perf_counter()-started,
        tests=len(all_ids),preserved_baseline_ids=len(old),zero_skip=True,
        top15=sorted(all_ids.items(),key=lambda r:-r[1])[:15],
        groups={k:{n:r.get(n) for n in ("tests","seconds","shard_seconds","import_seconds")}
            for k,r in receipts.items()},new_IDs=sorted(set(all_ids)-old))
    save(f"tests-{label}-matrix.json",summary);event("V16_test_matrix_complete",**summary)


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("label",choices=("before","after"))
    run(p.parse_args().label)

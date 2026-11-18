"""Bounded final correctness/performance run; no retry-until-fast streak."""
from pathlib import Path
import json
import os
import subprocess
import time
from statistics import median
from prop_v25_common import *

PYTHON=Path(".runtime/quant-audit-v24/Scripts/python.exe").resolve()


def run():
    temp=Path(".runtime/v25-test-temp").resolve()
    temp.mkdir(exist_ok=True)
    env=dict(os.environ,TEMP=str(temp),TMP=str(temp),
             PYTHONPATH="projects/trader/foundation_v2;tooling/ai-engines;tooling/ai-engines/tests")
    runner="tooling/ai-engines/quant_test_suite.py"
    save("performance-plan.json",dict(runner_sha256=sha(runner),profile="old same-runtime module timings; six balanced shards",
        full_target_seconds=13.5,smoke_target_seconds=.72,smoke_samples=10,
        startup_and_fixture_IO_included=True,no_retry_until_fast=True,
        change="deduplicate exact search-path strings before resolve; no fixture/cache/coverage removal",
        diagnosis="78 smoke tests: no child CreateProcess; real filesystem fixtures retained"))
    old=read(".runtime/solo-adoption-complete.json")
    full=JOB/"tests-final.json"
    command=[str(PYTHON),runner,"--group","complete","--tier","all","--workers","6",
             "--profile",str(Path(".runtime/solo-adoption-complete.json").resolve()),"--output",str(full)]
    started=time.perf_counter()
    with full.with_suffix(".stdout").open("x") as stream:
        result=subprocess.run(command,env=env,stdout=stream,stderr=subprocess.STDOUT)
    wall=time.perf_counter()-started
    r=read(full)
    if result.returncode or not r["passed"] or r["skipped"]:
        raise ValueError("V25_full_correctness_failed")
    ids=set(r["timings"])
    if not set(old["timings"])<=ids:
        raise ValueError("V25_prior_test_IDs_missing")
    smoke=[]
    expected=set(read(V24/"smoke-release-00.json")["timings"])
    for n in range(10):
        output=JOB/f"smoke-final-{n:02}.json"
        args=[str(PYTHON),runner,"--group","complete","--tier","smoke","--indexed-imports","--output",str(output)]
        started=time.perf_counter()
        with output.with_suffix(".stdout").open("x") as stream:
            status=subprocess.run(args,env=env,stdout=stream,stderr=subprocess.STDOUT)
        elapsed=time.perf_counter()-started
        sample=read(output)
        if status.returncode or not sample["passed"] or sample["skipped"] or set(sample["timings"])!=expected:
            raise ValueError("V25_smoke_IDs_or_correctness_failed")
        smoke.append(dict(attempt=n+1,wall=elapsed,tests=sample["tests"],receipt_sha256=sha(output)))
    summary=dict(tests=len(ids),retained_prior=len(old["timings"]),added=sorted(ids-set(old["timings"])),
        skips=0,full_wall=wall,full_target_pass=wall<13.5,full_receipt_sha256=sha(full),
        smoke=smoke,smoke_IDs=len(expected),below072=sum(s["wall"]<.72 for s in smoke),
        median=median(s["wall"] for s in smoke),maximum=max(s["wall"] for s in smoke))
    save("performance-final-summary.json",summary)
    compressed("final-test-timings",r)
    print(summary,flush=True)


if __name__=="__main__":
    run()

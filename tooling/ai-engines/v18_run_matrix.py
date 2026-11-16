"""Bounded local process supervision; one immutable log pair per fixed case."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
import os
import subprocess
import sys
import time
from prop_v18_common import JOB, save, event


def phase(stage, pcts, workers):
    cases = [(tag, mode, pct) for tag in ("OLHC", "OHLC")
             for mode in ("PRIMARY", "STRICT") for pct in pcts]
    started = time.perf_counter()

    def child(case):
        tag, mode, pct = case
        name = f"matrix-{stage}-{tag}-{mode}-{pct}"
        command = [sys.executable, "tooling/ai-engines/prop_v18_bootstrap.py", stage,
                   "--tag", tag, "--mode", mode, "--friction", str(pct)]
        at = time.perf_counter()
        with (JOB / (name + ".log")).open("x", encoding="utf-8") as out, \
                (JOB / (name + ".stderr")).open("x", encoding="utf-8") as err:
            process = subprocess.Popen(command, stdout=out, stderr=err,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            event("V18_case_started", stage_name=stage, order=tag, mode=mode, friction=pct, pid=process.pid)
            rc = process.wait()
        result = dict(stage_name=stage, order=tag, mode=mode, friction=pct, pid=process.pid,
                      returncode=rc, seconds=time.perf_counter() - at)
        save(name + "-process.json", result)
        return result

    results = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        pending = [pool.submit(child, case) for case in cases]
        for future in as_completed(pending):
            r = future.result()
            results.append(r)
            event("V18_case_finished", **r)
    save(f"matrix-{stage}-processes.json", dict(results=results, workers=workers,
         seconds=time.perf_counter() - started, passed=all(r["returncode"] == 0 for r in results)))
    if any(r["returncode"] for r in results):
        raise ValueError("V18_matrix_has_failed_case:" + stage)


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--workers", type=int, choices=(4, 6, 8), default=8)
    a = p.parse_args()
    phase("historical", (125, 150), a.workers)
    phase("monte", (100, 125, 150), a.workers)

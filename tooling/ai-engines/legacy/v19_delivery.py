"""V19 performance and delivery receipts; never selects financial outcomes."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from statistics import median
import json
import subprocess
import sys
import time
from prop_v19_common import *
from prop_v16_performance import RUNTIMES


def idle():
    path = JOB / "Full-MC-processes.json"
    if not path.exists() or not read(path)["passed"]:
        raise ValueError("V19_final_benchmarks_require_completed_financial_matrix")
    supplement = JOB / "state-payout-supplement.json"
    if not supplement.exists() or not read(supplement)["passed"]:
        raise ValueError("V19_final_benchmarks_require_completed_O3_payout_measurement")
    correction = JOB / "O2-constraint-correction/decision.json"
    if not correction.exists():
        raise ValueError("V19_exact_O2_constraint_audit_incomplete")
    if read(correction)["eligible_upgrade"]:
        raise ValueError("V19_O2_upgrade_requires_frozen_supplementary_validation_before_final_delivery")


def performance():
    idle()
    names = ("base", "native", "statistics", "worker")
    if any((JOB / f"tests-final-{g}.json").exists() for g in names):
        raise ValueError("V19_preserve_full_suite_attempt")
    started = time.perf_counter()
    def run(group):
        output = JOB / f"tests-final-{group}.json"
        command = [RUNTIMES[group], "tooling/ai-engines/quant_test_suite.py", "--group", group,
                   "--tier", "all", "--output", str(output)]
        if group == "base":
            command += ["--workers", "4", "--profile", str(V18 / "tests-final-base.json")]
        with output.with_suffix(".stdout").open("x") as log:
            status = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT).returncode
        return group, status, read(output)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(run, names))
    ids, previous = set(), set()
    for group, code, row in results:
        if code or not row["passed"] or row["skipped"] or ids.intersection(row["timings"]):
            raise ValueError("V19_full_suite_failure_skip_or_duplicate")
        ids.update(row["timings"])
        previous.update(read(V18 / f"tests-final-{group}.json")["timings"])
    if len(previous) != 1153 or not previous <= ids:
        raise ValueError("V19_lost_V18_test_ids")
    wall = time.perf_counter() - started
    save("tests-final-matrix.json", dict(tests=len(ids), preserved_V18_IDs=len(previous), zero_skip=True,
         total_wall_seconds=wall, target_under22=wall < 22, V18_wall_seconds=22.06151020003017,
         concurrency="Four existing runtime groups overlap; base retains four isolated workers.",
         no_claim_identical_workload_or_whole_machine_speed=True,
         new_IDs=sorted(ids - previous), groups={g: {k: r.get(k) for k in ("tests", "seconds", "workers")}
                                               for g, _, r in results}))
    event("V19_full_tests", tests=len(ids), seconds=wall, under22=wall < 22)


def smoke():
    idle()
    plan = dict(attempts=10, threshold_wall_seconds=.78, fresh_process=True, workers=1,
                unchanged_smoke_IDs=78, includes_python_startup=True,
                retries_for_better_streak=False, retain_all_outliers=True)
    save("smoke-final-plan.json", plan)
    rows = []
    old_ids = set(read(V18 / "smoke-00.json")["timings"])
    for i in range(10):
        output = JOB / f"smoke-final-{i:02d}.json"
        if output.exists():
            raise ValueError("V19_preserve_smoke_attempt")
        started = time.perf_counter()
        result = subprocess.run([sys.executable, "tooling/ai-engines/quant_test_suite.py",
            "--group", "base", "--tier", "smoke", "--output", str(output)], capture_output=True)
        elapsed = time.perf_counter() - started
        row = read(output)
        if result.returncode or not row["passed"] or row["skipped"] or set(row["timings"]) != old_ids:
            raise ValueError("V19_smoke_functionality_or_coverage_changed")
        rows.append(dict(attempt=i + 1, wall=elapsed, suite=row["seconds"],
                         import_seconds=row["import_seconds"], tests=row["tests"], passed=True, skipped=0))
    save("smoke-final-results.json", dict(plan=plan, rows=rows,
         wall_max=max(r["wall"] for r in rows), wall_median=median(r["wall"] for r in rows),
         below078=sum(r["wall"] < .78 for r in rows), below080=sum(r["wall"] < .80 for r in rows),
         all_ten_below078=all(r["wall"] < .78 for r in rows), same_78_IDs=True))
    event("V19_final_smoke", below078=sum(r["wall"] < .78 for r in rows), max=max(r["wall"] for r in rows))


def storage():
    idle()
    roots = {}
    old = read(V18 / "storage-summary.json")
    for label, root in (("D", "D:/ANNAM/TradingWorkspace"), ("E", "E:/BACKUP-TRADINGWORKSPACE")):
        output = JOB / f"storage-final-{label}.json"
        if output.exists():
            raise ValueError("V19_preserve_storage_attempt")
        subprocess.run([sys.executable, "tooling/workspace_maintenance.py", "inventory",
                        "--root", root, "--output", str(output)], check=True)
        row = read(output)
        current, before = row["groups"]["/"], old["roots"][label]["current"]
        roots[label] = dict(current=current, V18=before,
            delta_since_V18={k: current[k] - before[k] for k in ("bytes", "files", "folders")},
            errors=row["errors"], skipped_links=len(row["skipped_links"]), receipt_sha256=sha(output))
    save("storage-final-summary.json", dict(roots=roots, newly_deleted_files=0,
         broad_cleanup=False, raw_data_or_research_deleted=False, physical_reclaimed_bytes=None,
         snapshot_not_atomic=True, research_audit_artifacts_are_intentional_growth=True))
    event("V19_storage_checked", roots={k: r["delta_since_V18"] for k, r in roots.items()})


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("performance", "smoke", "storage"))
    globals()[parser.parse_args().stage]()

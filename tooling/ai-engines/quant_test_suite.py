"""Disjoint Fast CI / historical suites with per-test timing and runtime groups."""
import argparse
from collections import defaultdict
import contextlib
import json
from pathlib import Path
import sys
import time
import unittest

NATIVE = {
    "test_multiframe_runner_recovery", "test_run_us500_multiframe",
    "test_run_us500_recent_screen", "test_us500_channel_history",
    "test_us500_frequency_audit", "test_us500_ma_reclaim",
    "test_us500_multiframe", "test_us500_opportunities", "test_us500_recent_setups",
}
SPECIAL = NATIVE | {"test_fx_pair_formation", "test_engine_worker"}
FAST = {
    "test_prop_campaign", "test_prop_atlas_v2", "test_prop_portfolio_v3",
    "test_prop_cocore_v4", "test_prop_v5", "test_prop_v6", "test_prop_v7", "test_prop_v8",
    "test_quant_core", "test_prop_v9", "test_workspace_maintenance",
    "test_eurusd_b0", "test_xau_intraday_b0", "test_xau_scale_horizon_audit",
    "test_xau_h1_stage0", "test_xau_h1_execution", "test_xau_a_validation",
    "test_eurusd_funnel_audit", "test_gold_intraday_quality",
}


def modules(group, tier):
    names = sorted(p.stem for p in Path(__file__).with_name("tests").glob("test_*.py"))
    match = {
        "base": lambda m: m not in SPECIAL,
        "native": lambda m: m in NATIVE,
        "statistics": lambda m: m == "test_fx_pair_formation",
        "worker": lambda m: m == "test_engine_worker",
    }[group]
    return [m for m in names if match(m) and
            (tier == "all" or (m in FAST or m.startswith("test_shadow")) == (tier == "fast"))]


class TimedResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.timings = {}

    def startTest(self, test):
        self.started = time.perf_counter()
        super().startTest(test)

    def stopTest(self, test):
        self.timings[test.id()] = time.perf_counter() - self.started
        super().stopTest(test)


def run(group, tier, output):
    selected = modules(group, tier)
    sys.path[:0] = [str(Path(__file__).parent), str(Path(__file__).with_name("tests"))]
    start = time.perf_counter()
    with output.with_suffix(".log").open("w", encoding="utf-8") as log, \
            contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        load_start = time.perf_counter()
        suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(m) for m in selected)
        load_seconds = time.perf_counter() - load_start
        result = unittest.TextTestRunner(stream=log, verbosity=2, resultclass=TimedResult).run(suite)
    totals = defaultdict(float)
    for name, duration in result.timings.items():
        totals[name.split(".")[0]] += duration
    receipt = dict(group=group, tier=tier, modules=selected, passed=result.wasSuccessful(),
                   tests=result.testsRun, skipped=len(result.skipped),
                   failures=len(result.failures), errors=len(result.errors),
                   seconds=time.perf_counter() - start, import_seconds=load_seconds,
                   timings=result.timings, module_seconds=dict(sorted(totals.items(), key=lambda x: -x[1])),
                   python=sys.executable)
    output.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in receipt.items() if k not in ("timings", "module_seconds", "modules")}))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--group", choices=("base", "native", "statistics", "worker"), default="base")
    parser.add_argument("--tier", choices=("fast", "historical", "all"), default="all")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(run(args.group, args.tier, args.output))

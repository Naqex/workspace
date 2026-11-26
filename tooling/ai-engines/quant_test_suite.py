"""Disjoint Fast CI / historical suites with per-test timing and runtime groups."""
import argparse
from collections import defaultdict
import contextlib
import json
import importlib.util
import os
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
OBSERVER = {"test_evidence_compaction", "test_ftmo_trial_runner"}
SPECIAL = NATIVE | OBSERVER | {"test_fx_pair_formation", "test_engine_worker"}
FAST = {
    "test_prop_campaign", "test_prop_atlas_v2", "test_prop_portfolio_v3",
    "test_prop_cocore_v4", "test_prop_v5", "test_prop_v6", "test_prop_v7", "test_prop_v8",
    "test_quant_core", "test_prop_v9", "test_workspace_maintenance",
    "test_eurusd_b0", "test_xau_intraday_b0", "test_xau_scale_horizon_audit",
    "test_xau_h1_stage0", "test_xau_h1_execution", "test_xau_a_validation",
    "test_eurusd_funnel_audit", "test_gold_intraday_quality",
    "test_vectorized_stage0", "test_deep_storage", "test_zero_tuning_ensemble",
    "test_sl_active_kernel", "test_independent_ledger_auditor", "test_v12_signals",
    "test_gap_aware_execution", "test_v13_protocol", "test_prop_v14", "test_prop_v15", "test_prop_v16", "test_prop_v17", "test_prop_v18",
    "test_prop_v19", "test_ftmo_free_trial_adapter", "test_v19_covariance", "test_prop_v20",
    "test_evidence_compaction", "test_ftmo_trial_runner", "test_trade_forensics", "test_prop_v22", "test_prop_v23",
    "test_bot_lab", "test_ftmo_connection", "test_research_fast_fail",
    "test_native_paths", "test_prop_v25", "test_corpus_funnel",
    "test_prop_v26", "test_corpus_batch_signals", "test_corpus_batch_execution", "test_mt_report_parser",
    "test_research_entry_admission",
}
SMOKE = {"test_quant_core", "test_vectorized_stage0", "test_workspace_maintenance",
         "test_deep_storage", "test_zero_tuning_ensemble", "test_sl_active_kernel",
         "test_independent_ledger_auditor", "test_gap_aware_execution"}
# Measured LPT shard weights (seconds) so --workers N balances even without --profile (e.g. CI).
DEFAULT_WEIGHTS = {
    "test_shadow_reconcile": 9.44,
    "test_forex_study_batch": 4.08,
    "test_frozen_source_proof": 3.36,
    "test_fx_pair_formation": 2.80,
    "test_us500_euopen_component": 2.53,
    "test_explicit_m1_view": 2.38,
    "test_multiframe_runner_recovery": 2.37,
    "test_shadow_night": 2.36,
    "test_index_cash_close_tick_component": 2.15,
    "test_nasdaq_intraday_momentum_component": 1.59,
    "test_index_rest_of_day_component": 1.59,
    "test_nasdaq_noise14": 1.52,
    "test_us500_inventory_condition": 1.39,
    "test_nasdaq_overnight_reversal_component": 1.36,
    "test_engine_worker": 1.30,
    "test_us500_fomc_momentum_component": 1.27,
    "test_index_consensus_component": 1.26,
    "test_options_expiry_component": 1.15,
    "test_forex_discovery_report": 1.02,
    "test_shadow_sessions": 0.95,
    "test_us500_multiframe": 0.55,
    "test_ny_fx_gap_scenarios": 0.53,
    "test_fixing_clock_probe": 0.51,
    "test_ftmo_spread_sessions": 0.48,
    "test_rd_research": 0.48,
    "test_nasdaq_opening5_bounds": 0.44,
    "test_native_hourly_source": 0.42,
    "test_strategy_evidence": 0.37,
    "test_index_noise_study": 0.37,
    "test_forex_time_fit": 0.37,
    "test_xau_scale_horizon_audit": 0.36,
    "test_sealed_m1_review": 0.35,
    "test_paperclip_strategy_skills": 0.33,
    "test_nasdaq_opening5_orb": 0.32,
    "test_index_preclose_reversion": 0.31,
}


class RepoModuleFinder:
    """Index only these already-prioritized local roots; standard loader reads source/pyc."""
    def __init__(self):
        source = Path(__file__).parent
        self.files = {}
        stdlib = sys.stdlib_module_names
        for folder, prefix in (
            (source, ""),
            (source / "legacy", ""),
            (source / "experiments", ""),
            (source / "tests", ""),
            (source / "quant_core", "quant_core."),
        ):
            if not folder.is_dir():
                continue
            for entry in os.scandir(folder):
                if entry.name.endswith(".py") and entry.is_file() and entry.name != "__init__.py":
                    stem = entry.name[:-3]
                    if not prefix and stem in stdlib:
                        continue
                    self.files.setdefault(prefix + stem, entry.path)

    def find_spec(self, fullname, path=None, target=None):
        filename = self.files.get(fullname)
        return importlib.util.spec_from_file_location(fullname, filename) if filename else None


def modules(group, tier):
    if tier=='smoke':
        return sorted(SMOKE) if group in ('base','complete') else []
    names = sorted(p.stem for p in Path(__file__).with_name("tests").glob("test_*.py"))
    match = {
        "base": lambda m: m not in SPECIAL,
        "native": lambda m: m in NATIVE,
        "statistics": lambda m: m == "test_fx_pair_formation",
        "worker": lambda m: m == "test_engine_worker",
        "observer": lambda m: m in OBSERVER,
        "complete": lambda m: True,
    }[group]
    if tier == "smoke":
        return [m for m in names if match(m) and m in SMOKE]
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


def run(group, tier, output, selected=None, indexed_imports=False):
    selected = modules(group, tier) if selected is None else selected
    # PYTHONPATH and unittest callers can already contain both entries. Repeated
    # search roots add filesystem probes to every import on Windows.
    candidates = [str(Path(__file__).parent), str(Path(__file__).with_name("legacy")),
                  str(Path(__file__).with_name("experiments")), str(Path(__file__).with_name("tests")),
                  str(Path(__file__).resolve().parents[2]), *sys.path]
    sys.path = list(dict.fromkeys(str(Path(p).resolve()) for p in dict.fromkeys(candidates)))
    start = time.perf_counter()
    finder = RepoModuleFinder() if indexed_imports else None
    if finder is not None:
        sys.meta_path.insert(0, finder)
    with output.with_suffix(".log").open("w", encoding="utf-8") as log, \
            contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        load_start = time.perf_counter()
        suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(m) for m in selected)
        load_seconds = time.perf_counter() - load_start
        # Standalone test modules prepend their own import roots during loading.
        # Preserve first-match resolution without probing those same roots again
        # for the lazy imports performed by individual test cases.
        sys.path = list(dict.fromkeys(sys.path))
        result = unittest.TextTestRunner(stream=log, verbosity=2, resultclass=TimedResult).run(suite)
    if finder is not None:
        sys.meta_path.remove(finder)
    totals = defaultdict(float)
    for name, duration in result.timings.items():
        totals[name.split(".")[0]] += duration
    receipt = dict(group=group, tier=tier, modules=selected, passed=result.wasSuccessful(),
                   tests=result.testsRun, skipped=len(result.skipped),
                   failures=len(result.failures), errors=len(result.errors),
                   seconds=time.perf_counter() - start, import_seconds=load_seconds,
                   timings=result.timings, module_seconds=dict(sorted(totals.items(), key=lambda x: -x[1])),
                   python=sys.executable, indexed_imports=indexed_imports)
    output.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in receipt.items() if k not in ("timings", "module_seconds", "modules")}))
    return 0 if result.wasSuccessful() else 1


def assign_shards(selected, workers, durations=None):
    weights_map = DEFAULT_WEIGHTS if durations is None else {**DEFAULT_WEIGHTS, **durations}
    batches, weights = [[] for _ in range(workers)], [0.] * workers
    for name in sorted(selected, key=lambda n: (-weights_map.get(n, .1), n)):
        i = min(range(workers), key=lambda j: weights[j])
        batches[i].append(name)
        weights[i] += weights_map.get(name, .1)
    return batches


def parallel(group, tier, output, workers, profile=None):
    from concurrent.futures import ThreadPoolExecutor
    import subprocess
    selected = modules(group, tier)
    durations = None
    if profile:
        durations = json.loads(profile.read_text(encoding="utf-8-sig")).get("module_seconds", {})
    batches = assign_shards(selected, workers, durations)
    start = time.perf_counter()

    def child(i):
        receipt = output.with_name(output.stem + f"-shard{i}.json")
        command = [sys.executable, "-X", "utf8", str(Path(__file__).resolve()), "--group", group,
                   "--tier", tier, "--indexed-imports", "--output", str(receipt)]
        for module in batches[i]:
            command += ["--module", module]
        with receipt.with_suffix(".stdout").open("w", encoding="utf-8") as log:
            status = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT).returncode
        return status, json.loads(receipt.read_text(encoding="utf-8"))

    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(child, range(workers)))
    timings, totals = {}, {}
    for status, r in results:
        if set(timings) & set(r["timings"]):
            raise ValueError("duplicate_parallel_test_ID")
        timings.update(r["timings"])
        totals.update(r["module_seconds"])
    all_modules = [m for _, r in results for m in r["modules"]]
    if sorted(all_modules) != selected:
        raise ValueError("parallel_module_coverage_changed")
    result = dict(group=group, tier=tier, workers=workers, modules=selected,
                  passed=all(code == 0 and r["passed"] for code, r in results),
                  tests=sum(r["tests"] for _, r in results),
                  skipped=sum(r["skipped"] for _, r in results),
                  errors=sum(r["errors"] for _, r in results),
                  failures=sum(r["failures"] for _, r in results),
                  seconds=time.perf_counter()-start, timings=timings,
                  module_seconds=totals, shard_seconds=[r["seconds"] for _, r in results],
                  parallel_processes=True)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print({k: v for k, v in result.items() if k not in ("timings", "modules", "module_seconds")})
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--group", choices=("base", "native", "statistics", "worker", "observer", "complete"), default="base")
    parser.add_argument("--tier", choices=("smoke", "fast", "historical", "all"), default="all")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, choices=(1, 2, 4, 6), default=1)
    parser.add_argument("--indexed-imports", action="store_true")
    parser.add_argument("--profile", type=Path)
    parser.add_argument("--module", action="append")
    args = parser.parse_args()
    if args.module and (args.workers != 1 or not set(args.module) <= set(modules(args.group, args.tier))):
        parser.error("--module requires a registered serial subset")
    raise SystemExit(parallel(args.group, args.tier, args.output, args.workers, args.profile)
                     if args.workers > 1 else run(args.group, args.tier, args.output, args.module, args.indexed_imports))

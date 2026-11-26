"""Safe Pytest Runtime Optimization & Windows Temp-Handle Reliability Hooks (Wave 2).

Zero test assertions weakened, skipped, or mocked:
  1. Pins BLAS/OMP/Numba thread pools to 1 inside xdist workers (`PYTEST_XDIST_WORKER`) to prevent
     6x6=36 thread oversubscription on 6-core Windows hosts.
  2. Upgrades default xdist `--dist load` to `--dist worksteal` when `-n` is active so fast workers
     steal queued tests instead of sitting idle behind stragglers.
  3. Applies deterministic Longest-Processing-Time-First (LPT) ordering in
     `pytest_collection_modifyitems` so heavy test modules start at t=0.0s across separate workers.
  4. Adds Windows `WinError 32` GC-retry protection on `tempfile.TemporaryDirectory.cleanup` so
     lazy PyArrow/Parquet memory-mapped handles never cause spurious cleanup crashes under `-n 6`.
"""

from __future__ import annotations

import gc
import os
import sys
import tempfile
import time
from pathlib import Path

# Ensure tooling/ai-engines/ and its legacy/ & experiments/ tiers resolve seamlessly under pytest
_AI_ENGINES_DIR = Path(__file__).resolve().parents[1]
for _tier_dir in (_AI_ENGINES_DIR, _AI_ENGINES_DIR / "legacy", _AI_ENGINES_DIR / "experiments"):
    _tier_str = str(_tier_dir)
    if _tier_dir.is_dir() and _tier_str not in sys.path:
        sys.path.append(_tier_str)

# Pin numeric thread pools to 1 inside parallel xdist workers before NumPy/Numba import
if os.environ.get("PYTEST_XDIST_WORKER"):
    for _var in (
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
        "VECLIB_MAXIMUM_THREADS",
        "NUMBA_NUM_THREADS",
    ):
        os.environ.setdefault(_var, "1")

# Empirical profiled heavy modules (ordered slowest -> fastest for LPT scheduling)
_HEAVY_MODULE_PRIORITY: dict[str, int] = {
    "test_wave2_cockpit_and_treasury.py": 0,
    "test_shadow_reconcile.py": 1,
    "test_forex_study_batch.py": 2,
    "test_mql5_parity_and_kit.py": 3,
    "test_frozen_source_proof.py": 4,
    "test_knowledge_brain_and_research.py": 5,
    "test_multiframe_runner_recovery.py": 6,
    "test_explicit_m1_view.py": 7,
    "test_us500_euopen_component.py": 8,
    "test_shadow_night.py": 9,
    "test_index_cash_close_tick_component.py": 10,
    "test_engine_worker.py": 11,
    "test_forex_discovery_report.py": 12,
    "test_us500_inventory_condition.py": 13,
    "test_us500_fomc_momentum_component.py": 14,
    "test_index_rest_of_day_component.py": 15,
    "test_knowledge_audit_upgrade.py": 16,
    "test_red_team_and_ops.py": 17,
    "test_wave2_optimization_and_meta.py": 18,
}

_ORIG_TEMPDIR_CLEANUP = tempfile.TemporaryDirectory.cleanup
_TEMPDIR_PATCHED = False


def _windows_safe_tempdir_cleanup(self: tempfile.TemporaryDirectory) -> None:
    """Retry TemporaryDirectory cleanup after gc.collect() on transient Windows WinError 32 handle locks."""
    for attempt in range(4):
        try:
            _ORIG_TEMPDIR_CLEANUP(self)
            return
        except PermissionError:
            if os.name != "nt" or attempt == 3:
                raise
            gc.collect()
            time.sleep(0.05 * (attempt + 1))


def pytest_configure(config) -> None:
    global _TEMPDIR_PATCHED
    if os.name == "nt" and not _TEMPDIR_PATCHED:
        tempfile.TemporaryDirectory.cleanup = _windows_safe_tempdir_cleanup  # type: ignore[assignment]
        _TEMPDIR_PATCHED = True

    # Upgrade default static `--dist load` to dynamic `--dist worksteal` when xdist is enabled
    numprocs = getattr(config.option, "numprocesses", None)
    dist = getattr(config.option, "dist", None)
    if numprocs and dist == "load":
        config.option.dist = "worksteal"


def pytest_collection_modifyitems(items: list) -> None:
    """Deterministic Longest-Processing-Time-First (LPT) ordering to minimize parallel tail latency."""
    def _sort_key(item) -> tuple[int, str, str]:
        fname = os.path.basename(str(item.fspath))
        prio = _HEAVY_MODULE_PRIORITY.get(fname, 100)
        return (prio, fname, item.nodeid)

    items.sort(key=_sort_key)

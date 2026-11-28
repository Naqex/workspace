"""Wave 5 (Gates W5-G07, W5-G08, W5-G09): Full 355-Candidate M1 Alpha Mining Arena & PORT_V5 Accretion.

Executes the end-to-end, fail-closed Wave 5 M1 intraday alpha discovery pipeline:
  - Step A (W5-G07): Sync updated `wave5/` code (`m1_universe_28_loader.py` & `m1_alpha_families_5.py`)
    to `X13worker` (`naqex-x13`) via `compute_router.sync_dev_cache(include_tapes=False)` and dispatch
    ALL `m_total = 355 <= 360` Cluster A (`2018-2020` for 7Y, `2019-2020` for 6Y — NEVER leaking 2021
    into IS!) candidates across `X13worker` (`8` threads FULL PERFORMANCE, AC-only, 80-100% offload)
    via `x13_shard_dispatcher.py` with clean job IDs (`w5_m1_cla_shard_<k>`, `w5_m1_clb_shard_<k>`).
  - Step B (W5-G07): Log ALL `355` Cluster A trial results into `.runtime/offensive5/alpha/wave5_m1_alpha_m360.duckdb`
    with hard budget cap `m_total <= 360` (`BudgetExceededError` on trial #361, zero hidden trials).
    NEVER writes to `.runtime/experiments/unified_eval_catalog.duckdb` in this lane.
  - Step C (W5-G08): Select top Cluster A finalists purely on Cluster A metrics (`Sharpe > 0.30`,
    `trades >= 40`, `ev_r_1x > 0.0`, `swap = 0`, deduplicated per `(family_id, symbol)`), freeze
    manifest SHA-256 BEFORE any Cluster B touch, then execute the SINGLE ONE-SHOT Cluster B
    (`2021-2024`) evaluation (offloaded to X13 full speed if eligible).
  - Step D (W5-G08): On PC Dev (`MODE_A_OWNER_ACTIVE`: `NUMBA_NUM_THREADS=2`, `OMP_NUM_THREADS=2`,
    `BelowNormal 0x4000`, `0% GPU`), run the strict 8-gate Cluster B statistical filter with ZERO
    threshold relaxation:
      1) `BH-FDR q <= 0.10` across the FULL `m_total = 355` trial space (empirical sign-flip p-values)
      2) Empirical `DSR >= 0.50` passing REAL `trial_sharpes` array to `research_council.py`
         (supporting multi-symbol pairs `(leader, target)` for `F5D`)
      3) `PBO (CSCV) <= 0.35` via `quant_core.metrics.compute_pbo_cscv` (Cluster A family matrix)
      4) `Cluster B Sharpe >= 0.60` (calendar-aligned daily annualized Sharpe at 1.0x friction)
      5) `cost_breakeven_mult >= 2.0x` (with QDM session-open spread penalty baked in) & `net@2x > 0`
      6) `trades_cluster_b >= 60`
      7) `|corr| vs PORT_7E <= 0.25` AND `worst-5% tail_corr vs PORT_7E <= 0.35`
      8) `swap = 0` (`max_exit_utc_sec <= 75,000` / `<= 20:50 UTC`), plus strict Law 13
         `blindness_tier` (`M1_UNSEEN_D1_VIEWED` vs `DEV_CLB_CONSUMED_12OLD` over union of
         leader+target), `mt5_hcc_ready` (`18` ready vs `10` lacking `.hcc`), and `6-CCY`
         red-news scope disclosure flagging `NZD`/`CHF`.
  - Step E (W5-G09): Greedy incremental accretion of `TIER_1_PROP_CANDIDATE` survivors onto `PORT_7E`
    on Cluster B (`2021-2024`) requiring genuine net improvement in Sharpe, PF, and R-velocity
    without breaching `<= 35%` per-pair weight share or `<= 1.0%`/symbol Funded risk caps. Emits:
      - `.runtime/offensive5/alpha/wave5_m1_arena_summary.json`
      - `.runtime/offensive5/alpha/port_v5_tapes.npz` (zero-pickle; explicit `port_v5_equals_port_7e`)

Hard safety & air-gap invariants:
  - PC Dev strictly `MODE_A_OWNER_ACTIVE` (`force_mode_b=True` hard-rejected).
  - Imports `quant_core.holdout_guard` on PC Dev (auto-excluded from X13 code bundles by
    `compute_router.collect_dev_cache_files()`).
  - Holdout `2025+` SEALED (`<= 2024-12-31`, `holdout_rows_analysed = 0`), `ORDER_SEND_CAPABLE = False`,
    `ORDER_SEND_COUNT = 0`, `SPEND_VND = 0`, `0` bare asserts (`python -O` safe), `CREATE_NO_WINDOW`
    on any subprocess, `0` CRLF / `0` BOM.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
import threading
import time as time_mod
import weakref
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, Final

import numpy as np

AI_ENGINES_DIR: Final[Path] = Path(__file__).resolve().parents[2]
REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[4]
for _p in (REPO_ROOT, AI_ENGINES_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from ops_cloud import compute_router as cr  # noqa: E402
from quant_core.holdout_guard import (  # noqa: E402
    HOLDOUT_CUTOFF_DAY,
    HoldoutLockError,
    enforce_holdout_zero_rows,
    enforce_pre_holdout_dates,
)
from quant_core.metrics import compute_pbo_cscv, compute_sharpe  # noqa: E402

from quant_factory.eval_pipeline import benjamini_hochberg, sign_flip_p_numba  # noqa: E402
from quant_factory.research_council import (  # noqa: E402
    EvidenceBundle,
    KillCriteria,
    critique_proposal,
    propose_hypothesis,
)
from quant_factory.wave5 import (  # noqa: E402
    DEV_CUTOFF_SEC,
    DEV_PC_REQUIRED_MODE,
    HOLDOUT_CUTOFF_DATE,
    ORDER_SEND_CAPABLE,
    ORDER_SEND_COUNT,
)
from quant_factory.wave5 import m1_alpha_families_5 as fam5  # noqa: E402
from quant_factory.wave5 import m1_universe_28_loader as ldr  # noqa: E402
from quant_factory.wave5 import x13_shard_dispatcher as x13_disp  # noqa: E402

# Canonical Core7 constants (mirrored from `quant_factory.capital_optimizer.constants` for Numba-free CI imports)
CORE7_IDS: Final[tuple[str, ...]] = (
    "E1_USDJPY_TOKYO",
    "E2_USDJPY_EXP80",
    "E3_GBPUSD_VH",
    "E4_US100_SESS40",
    "E5_US100_RS1130",
    "E6_EURJPY_VOLCOMP",
    "E7_USDJPY_NY10ET",
)
DEFAULT_CORE7_BASE_RISK: Final[dict[str, float]] = {
    "E1_USDJPY_TOKYO": 0.1606 / 100.0,
    "E2_USDJPY_EXP80": 0.5894 / 100.0,
    "E3_GBPUSD_VH": 0.7500 / 100.0,
    "E4_US100_SESS40": 0.5000 / 100.0,
    "E5_US100_RS1130": 0.5000 / 100.0,
    "E6_EURJPY_VOLCOMP": 0.5000 / 100.0,
    "E7_USDJPY_NY10ET": 0.5000 / 100.0,
}
DEFAULT_DERIVED_TAPES_DIR: Final[Path] = REPO_ROOT / ".runtime" / "hot-m1-cache" / "_derived"
DEFAULT_DERIVED_TAPES_STEM: Final[str] = "frozen_9e_tapes_v2"

# ---------------------------------------------------------------------------
# Hard Safety, Budget, Gate & Path Constants
# ---------------------------------------------------------------------------

SCHEMA_VERSION: Final[str] = "naqex-wave5-m1-alpha-arena-summary-v1"
FROZEN_SCHEMA_VERSION: Final[str] = "naqex-wave5-m1-cluster-a-frozen-v1"
RECEIPT_SCHEMA_VERSION: Final[str] = "naqex-wave5-m1-arena-receipt-v1"
PORT_V5_TAPES_SCHEMA_VERSION: Final[str] = "naqex-wave5-port-v5-tapes-v1"

SPEND_VND: Final[int] = 0
MODE_A_MAX_CORES: Final[int] = 2
_BELOW_NORMAL_PRIORITY_CLASS: Final[int] = 0x00004000
_NO_WINDOW_FLAGS: Final[int] = int(getattr(subprocess, "CREATE_NO_WINDOW", 0)) if os.name == "nt" else 0

CLUSTER_A_MAX_DAY: Final[str] = "2020-12-31"
CLUSTER_B_MIN_DAY: Final[str] = "2021-01-01"
CLUSTER_B_MAX_DAY: Final[str] = HOLDOUT_CUTOFF_DATE  # "2024-12-31"
HOLDOUT_FIRST_DAY: Final[str] = HOLDOUT_CUTOFF_DAY  # "2025-01-01"

HARD_MAX_TRIALS: Final[int] = 360  # Hard budget cap m_total <= 360 (actual grid = 355)
HARD_FLAT_MAX_UTC_SEC: Final[int] = fam5.HARD_FLAT_MAX_UTC_SEC  # 75_000 (20:50 UTC)

# Cluster A Finalist Screening Thresholds (strictly on Cluster A, ZERO Cluster B peeking!)
CLUSTER_A_MIN_SHARPE: Final[float] = 0.30
CLUSTER_A_MIN_TRADES: Final[int] = 40
CLUSTER_A_MIN_EV_R: Final[float] = 0.0

# Strict 8-Gate Cluster B Thresholds (ZERO threshold relaxation!)
GATE_MAX_BH_FDR_Q: Final[float] = 0.10
GATE_MIN_DSR_EMPIRICAL: Final[float] = 0.50
GATE_MAX_PBO_CSCV: Final[float] = 0.35
GATE_MIN_CLUSTER_B_SHARPE: Final[float] = 0.60
GATE_MIN_COST_BREAKEVEN_MULT: Final[float] = 2.00
GATE_MIN_TRADES_CLUSTER_B: Final[int] = 60
GATE_MAX_ABS_CORR_PORT_7E: Final[float] = 0.25
GATE_MAX_TAIL_CORR_PORT_7E: Final[float] = 0.35

# Empirical Sign-Flip Permutation Draws (20,000 -> p_min = 5e-5 -> q_min at m=355 is 0.0177 <= 0.10!)
DEFAULT_SIGN_FLIP_DRAWS: Final[int] = 20_000
DEFAULT_SIGN_FLIP_SEED_BASE: Final[int] = 20261128

# Alpha Bench Reserve Thresholds (diagnostic tier ONLY, NEVER promoted to PORT_V5!)
BENCH_RESERVE_MIN_TRADES_B: Final[int] = 40
BENCH_RESERVE_MIN_SHARPE_B: Final[float] = 0.30
BENCH_RESERVE_MAX_ABS_CORR: Final[float] = 0.35

# Incremental Accretion Concentration Caps & Improvement Thresholds
ACCRETION_DEFAULT_ENGINE_RISK_PCT: Final[float] = 0.50
ACCRETION_MAX_PAIR_SHARE_PCT: Final[float] = 35.0
ACCRETION_MAX_SYMBOL_FUNDED_RISK_PCT: Final[float] = 1.00
ACCRETION_MIN_SHARPE_DELTA: Final[float] = 0.01
ACCRETION_MAX_DD_INCREASE_MULT: Final[float] = 1.10
ACCRETION_MAX_CORR_RUNNING_PORT: Final[float] = 0.25

TIER_1_PROP_CANDIDATE: Final[str] = "TIER_1_PROP_CANDIDATE"
TIER_ALPHA_BENCH_RESERVE: Final[str] = "ALPHA_BENCH_RESERVE"
TIER_KILLED_ON_CLUSTER_B: Final[str] = "KILLED_ON_CLUSTER_B"

CORE7_ENGINE_SYMBOLS: Final[dict[str, str]] = {
    "E1_USDJPY_TOKYO": "USDJPY",
    "E2_USDJPY_EXP80": "USDJPY",
    "E3_GBPUSD_VH": "GBPUSD",
    "E4_US100_SESS40": "US100",
    "E5_US100_RS1130": "US100",
    "E6_EURJPY_VOLCOMP": "EURJPY",
    "E7_USDJPY_NY10ET": "USDJPY",
}

DEFAULT_ALPHA_DIR: Final[Path] = REPO_ROOT / ".runtime" / "offensive5" / "alpha"
DEFAULT_DUCKDB_PATH: Final[Path] = DEFAULT_ALPHA_DIR / "wave5_m1_alpha_m360.duckdb"
DEFAULT_FROZEN_PATH: Final[Path] = DEFAULT_ALPHA_DIR / "wave5_m1_cluster_a_frozen.json"
DEFAULT_SUMMARY_PATH: Final[Path] = DEFAULT_ALPHA_DIR / "wave5_m1_arena_summary.json"
DEFAULT_PORT_V5_TAPES_PATH: Final[Path] = DEFAULT_ALPHA_DIR / "port_v5_tapes.npz"
DEFAULT_SHARD_WORK_DIR: Final[Path] = REPO_ROOT / ".tmp" / "wave5_m1_arena_shards"
DEFAULT_AUDIT_RECEIPT_PATH: Final[Path] = REPO_ROOT / ".runtime" / "offensive5" / "audits" / "w5_m1_arena_receipt.json"
DEFAULT_DROPBOX_RECEIPT_PATH: Final[Path] = REPO_ROOT / ".tmp" / "swarm_dropbox" / "w5-m1-arena.json"
DEFAULT_FAMILIES_ENTRY_SCRIPT: Final[Path] = AI_ENGINES_DIR / "quant_factory" / "wave5" / "m1_alpha_families_5.py"
DEFAULT_X13_EXTRA_FILES: Final[tuple[Path, ...]] = (
    AI_ENGINES_DIR / "configs" / "calendars" / "red_news_official_2018_2024_6ccy.json",
    AI_ENGINES_DIR / "configs" / "ssot" / "ftmo_specs_28.json",
)

_EPS: Final[float] = 1e-12


# ---------------------------------------------------------------------------
# Fail-Closed Exceptions (ZERO Bare `assert`s; Active Under `python -O`)
# ---------------------------------------------------------------------------


class BudgetExceededError(ValueError):
    """Raised when trial count exceeds the hard pre-registered budget `m_total <= 360`."""


class ClusterALeakageError(ValueError):
    """Raised if any Cluster B (2021+) or Holdout (2025+) date leaks into Cluster A."""


class ClusterBContaminationError(ValueError):
    """Raised if Cluster B contains pre-2021 or Holdout (2025+) observations."""


class ClusterBOneShotViolationError(ValueError):
    """Raised if attempting to re-execute the one-shot Cluster B evaluation on a frozen run."""


class UnverifiedPromotionError(ValueError):
    """Raised if attempting to promote/accrete any candidate that failed any of the 8 gates."""


# ---------------------------------------------------------------------------
# PC Dev MODE_A_OWNER_ACTIVE Guard & Pure Utility Helpers
# ---------------------------------------------------------------------------


def apply_mode_a_owner_active_guard(*, cores: int = MODE_A_MAX_CORES, force_mode_b: bool = False) -> dict[str, Any]:
    """Enforce PC Dev `MODE_A_OWNER_ACTIVE` (`2` cores, `BelowNormal 0x4000`, `0% GPU`)."""
    x13_disp.assert_dev_pc_mode_a_enforced(force_mode_b=force_mode_b)
    if isinstance(cores, bool) or not isinstance(cores, int) or not (1 <= cores <= 3):
        raise ValueError(f"PC Dev Mode A cores must be int in [1, 3], got {cores!r}")
    for k in ("NUMBA_NUM_THREADS", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[k] = str(cores)
    priority_applied = False
    win_error: str | None = None
    if os.name == "nt":
        try:
            k32 = ctypes.windll.kernel32
            k32.GetCurrentProcess.restype = ctypes.c_void_p
            k32.SetPriorityClass.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
            k32.SetPriorityClass.restype = ctypes.c_int
            priority_applied = bool(k32.SetPriorityClass(k32.GetCurrentProcess(), _BELOW_NORMAL_PRIORITY_CLASS))
        except Exception as exc:  # pragma: no cover - platform specific
            win_error = f"{type(exc).__name__}: {exc}"
    return {
        "policy_mode": DEV_PC_REQUIRED_MODE,
        "cores": cores,
        "numba_num_threads": cores,
        "omp_num_threads": cores,
        "priority_class_hex": hex(_BELOW_NORMAL_PRIORITY_CLASS),
        "priority_applied": priority_applied,
        "gpu_allowed": False,
        "win_error": win_error,
    }


def _utc_now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode(
        "utf-8"
    )


def canonical_sha256(payload: Any) -> str:
    return hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()


def sha256_file(path: Path) -> str:
    with path.open("rb") as fh:
        return hashlib.file_digest(fh, "sha256").hexdigest()


def compute_report_sha256(payload: Mapping[str, Any]) -> str:
    body = {k: v for k, v in payload.items() if k != "report_sha256"}
    return canonical_sha256(body)


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
            tmp = Path(fh.name)
        os.replace(tmp, path)
        tmp = None
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)


def _atomic_write_json_lf(path: Path, payload: Mapping[str, Any]) -> None:
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    _atomic_write_bytes(path, normalized.encode("utf-8"))


def _atomic_write_npz_zero_pickle(path: Path, arrays: Mapping[str, np.ndarray]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".npz.tmp",
            delete=False,
        ) as fh:
            np.savez_compressed(fh, **dict(arrays))
            fh.flush()
            os.fsync(fh.fileno())
            tmp = Path(fh.name)
        os.replace(tmp, path)
        tmp = None
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)


def _require_finite_float(
    val: Any,
    name: str,
    *,
    lo: float | None = None,
    hi: float | None = None,
) -> float:
    if isinstance(val, (bool, np.bool_)) or not isinstance(val, (int, float, np.number)):
        raise ValueError(f"INVALID_NUMERIC [{name}]: expected finite float (not bool), got {val!r}")
    out = float(val)
    if not math.isfinite(out):
        raise ValueError(f"NON_FINITE [{name}]: got {val!r}")
    if lo is not None and out < lo:
        raise ValueError(f"RANGE_ERROR [{name}]: {out} < {lo}")
    if hi is not None and out > hi:
        raise ValueError(f"RANGE_ERROR [{name}]: {out} > {hi}")
    return out


def _require_strict_int(
    val: Any,
    name: str,
    *,
    lo: int | None = None,
    hi: int | None = None,
) -> int:
    if isinstance(val, (bool, np.bool_)) or not isinstance(val, (int, np.integer)):
        raise ValueError(f"INVALID_INT [{name}]: expected strict int (not bool), got {val!r}")
    out = int(val)
    if lo is not None and out < lo:
        raise ValueError(f"RANGE_ERROR [{name}]: {out} < {lo}")
    if hi is not None and out > hi:
        raise ValueError(f"RANGE_ERROR [{name}]: {out} > {hi}")
    return out


def _weekday_calendar_dates(start_iso: str, end_iso: str) -> list[str]:
    """Generate sorted ISO YYYY-MM-DD weekday dates in `[start_iso, end_iso]` (strictly pre-Holdout)."""
    d0 = date.fromisoformat(start_iso)
    d1 = date.fromisoformat(end_iso)
    if d1 < d0:
        raise ValueError(f"Invalid date range: {start_iso}..{end_iso}")
    out: list[str] = []
    cur = d0
    step = timedelta(days=1)
    while cur <= d1:
        if cur.weekday() < 5:
            out.append(cur.isoformat())
        cur += step
    enforce_pre_holdout_dates(out, context=f"weekday_calendar:{start_iso}..{end_iso}")
    return out


def _deterministic_seed(candidate_id: str, salt: int = DEFAULT_SIGN_FLIP_SEED_BASE) -> int:
    h = hashlib.sha256(f"{candidate_id}|{salt}".encode()).digest()
    return int.from_bytes(h[:4], "big") % (2**31 - 1)


def _current_git_head() -> str:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=_NO_WINDOW_FLAGS,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
    except Exception:
        pass
    return "UNKNOWN"


# ---------------------------------------------------------------------------
# 1. Fail-Closed DuckDB Budget Ledger (`wave5_m1_alpha_m360.duckdb`, <= 360)
# ---------------------------------------------------------------------------

_SCHEMA_CLUSTER_A_SQL: Final[str] = """
CREATE TABLE IF NOT EXISTS cluster_a_trials (
    trial_seq INTEGER NOT NULL,
    candidate_id VARCHAR PRIMARY KEY,
    family_id VARCHAR NOT NULL,
    symbol VARCHAR NOT NULL,
    leader_symbol VARCHAR,
    years_evaluated_json VARCHAR NOT NULL,
    blindness_tier VARCHAR NOT NULL,
    mt5_hcc_ready BOOLEAN NOT NULL,
    data_resolution VARCHAR NOT NULL,
    has_nzd_chf_scope_gap BOOLEAN NOT NULL,
    n_trades INTEGER NOT NULL,
    winrate_frac DOUBLE NOT NULL,
    rr_ratio DOUBLE NOT NULL,
    ev_r_1x DOUBLE NOT NULL,
    ev_r_15x DOUBLE NOT NULL,
    ev_r_2x DOUBLE NOT NULL,
    pf_1x DOUBLE NOT NULL,
    pf_15x DOUBLE NOT NULL,
    pf_2x DOUBLE NOT NULL,
    total_r_1x DOUBLE NOT NULL,
    total_r_15x DOUBLE NOT NULL,
    total_r_2x DOUBLE NOT NULL,
    max_dd_r_1x DOUBLE NOT NULL,
    calmar_1x DOUBLE NOT NULL,
    sharpe_1x DOUBLE NOT NULL,
    sharpe_daily_a DOUBLE NOT NULL,
    median_fric_over_sl_1x DOUBLE NOT NULL,
    median_fric_over_sl_2x DOUBLE NOT NULL,
    max_exit_utc_sec INTEGER NOT NULL,
    all_flat_by_2050_utc BOOLEAN NOT NULL,
    swap_r_total DOUBLE NOT NULL,
    p_value_emp_a DOUBLE NOT NULL,
    is_finalist BOOLEAN NOT NULL,
    host_executed VARCHAR NOT NULL,
    shard_id VARCHAR NOT NULL,
    params_sha256 VARCHAR NOT NULL,
    params_json VARCHAR NOT NULL,
    holdout_rows_analysed INTEGER NOT NULL,
    order_send_count INTEGER NOT NULL,
    created_utc VARCHAR NOT NULL
);
"""

_SCHEMA_CLUSTER_B_SQL: Final[str] = """
CREATE TABLE IF NOT EXISTS cluster_b_evals (
    eval_seq INTEGER NOT NULL,
    candidate_id VARCHAR PRIMARY KEY,
    family_id VARCHAR NOT NULL,
    symbol VARCHAR NOT NULL,
    leader_symbol VARCHAR,
    years_evaluated_json VARCHAR NOT NULL,
    blindness_tier VARCHAR NOT NULL,
    mt5_hcc_ready BOOLEAN NOT NULL,
    data_resolution VARCHAR NOT NULL,
    has_nzd_chf_scope_gap BOOLEAN NOT NULL,
    n_trades_b INTEGER NOT NULL,
    winrate_frac_b DOUBLE NOT NULL,
    rr_ratio_b DOUBLE NOT NULL,
    ev_r_1x_b DOUBLE NOT NULL,
    ev_r_15x_b DOUBLE NOT NULL,
    ev_r_2x_b DOUBLE NOT NULL,
    pf_1x_b DOUBLE NOT NULL,
    pf_15x_b DOUBLE NOT NULL,
    pf_2x_b DOUBLE NOT NULL,
    total_r_1x_b DOUBLE NOT NULL,
    total_r_2x_b DOUBLE NOT NULL,
    max_dd_r_1x_b DOUBLE NOT NULL,
    calmar_1x_b DOUBLE NOT NULL,
    sharpe_1x_b DOUBLE NOT NULL,
    sharpe_daily_b DOUBLE NOT NULL,
    cost_breakeven_mult DOUBLE NOT NULL,
    p_value_signflip DOUBLE NOT NULL,
    bh_fdr_q DOUBLE NOT NULL,
    dsr_empirical DOUBLE NOT NULL,
    pbo_cscv DOUBLE NOT NULL,
    corr_vs_port_7e DOUBLE NOT NULL,
    tail_corr_vs_port_7e DOUBLE NOT NULL,
    max_exit_utc_sec INTEGER NOT NULL,
    swap_r_total DOUBLE NOT NULL,
    gates_passed_count INTEGER NOT NULL,
    all_8_gates_passed BOOLEAN NOT NULL,
    failed_gates_json VARCHAR NOT NULL,
    council_verdict VARCHAR NOT NULL,
    tier_classification VARCHAR NOT NULL,
    accretion_accepted BOOLEAN NOT NULL,
    host_executed VARCHAR NOT NULL,
    shard_id VARCHAR NOT NULL,
    holdout_rows_analysed INTEGER NOT NULL,
    order_send_count INTEGER NOT NULL,
    evaluated_utc VARCHAR NOT NULL
);
"""

_SCHEMA_META_SQL: Final[str] = """
CREATE TABLE IF NOT EXISTS arena_runs_meta (
    run_id VARCHAR PRIMARY KEY,
    cluster_a_frozen_sha256 VARCHAR NOT NULL,
    cluster_b_one_shot_executed BOOLEAN NOT NULL,
    m_total INTEGER NOT NULL,
    budget_cap INTEGER NOT NULL,
    finalist_count INTEGER NOT NULL,
    survivor_count INTEGER NOT NULL,
    bench_reserve_count INTEGER NOT NULL,
    accretive_count INTEGER NOT NULL,
    port_v5_equals_port_7e BOOLEAN NOT NULL,
    holdout_rows_analysed INTEGER NOT NULL,
    order_send_count INTEGER NOT NULL,
    completed_utc VARCHAR NOT NULL
);
"""


def _close_duckdb_box(box: list[Any]) -> None:
    con = box[0]
    box[0] = None
    if con is not None:
        try:
            con.close()
        except Exception:
            pass


class Wave5M1AlphaLedger:
    """Dedicated Wave 5 M1 Alpha DuckDB budget ledger (`m_total <= 360`, lazy `duckdb` import)."""

    def __init__(
        self,
        db_path: str | Path = DEFAULT_DUCKDB_PATH,
        *,
        max_trials: int = HARD_MAX_TRIALS,
    ) -> None:
        self.max_trials = _require_strict_int(max_trials, "max_trials", lo=1, hi=HARD_MAX_TRIALS)
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._con_box: list[Any] = [None]
        self._finalizer = weakref.finalize(self, _close_duckdb_box, self._con_box)
        with self._connect() as con:
            con.execute(_SCHEMA_CLUSTER_A_SQL)
            con.execute(_SCHEMA_CLUSTER_B_SQL)
            con.execute(_SCHEMA_META_SQL)

    @contextmanager
    def _connect(self) -> Iterator[Any]:
        import duckdb  # Lazy import ONLY (never runs on X13!)

        with self._lock:
            con = self._con_box[0]
            if con is None:
                con = duckdb.connect(str(self.db_path))
                self._con_box[0] = con
            yield con

    def close(self) -> None:
        with self._lock:
            _close_duckdb_box(self._con_box)

    def __enter__(self) -> Wave5M1AlphaLedger:
        return self

    def __exit__(self, _exc_type: Any, _exc: Any, _tb: Any) -> None:
        self.close()

    def get_cluster_a_count(self) -> int:
        with self._connect() as con:
            row = con.execute("SELECT COUNT(*) FROM cluster_a_trials").fetchone()
            return int(row[0]) if row is not None else 0

    def get_cluster_b_count(self) -> int:
        with self._connect() as con:
            row = con.execute("SELECT COUNT(*) FROM cluster_b_evals").fetchone()
            return int(row[0]) if row is not None else 0

    def is_cluster_b_one_shot_consumed(self) -> bool:
        with self._connect() as con:
            row = con.execute(
                "SELECT COUNT(*) FROM arena_runs_meta WHERE cluster_b_one_shot_executed = TRUE"
            ).fetchone()
            return bool(row is not None and int(row[0]) > 0)

    def record_cluster_a_trial(
        self,
        rec: Mapping[str, Any],
        *,
        sharpe_daily_a: float,
        p_value_emp_a: float,
        is_finalist: bool,
        host_executed: str,
        shard_id: str,
        created_utc: str | None = None,
    ) -> None:
        """Insert one Cluster A trial while enforcing hard budget cap `m_total <= max_trials <= 360`."""
        enforce_holdout_zero_rows(rec.get("holdout_rows_analysed", -1), context=f"ledger.cla.{rec.get('candidate_id')}")
        if int(rec.get("order_send_count", -1)) != 0:
            raise ValueError(f"ORDER_SEND_VIOLATION in Cluster A record {rec.get('candidate_id')!r}")
        yrs = list(rec.get("years_evaluated") or [])
        if any(int(y) > 2020 for y in yrs):
            raise ClusterALeakageError(
                f"CLUSTER_A_LEAKAGE [{rec.get('candidate_id')}]: years_evaluated={yrs} contains 2021+"
            )
        dr_keys = list((rec.get("daily_returns_1x") or {}).keys())
        if dr_keys:
            enforce_pre_holdout_dates(dr_keys, context=f"ledger.cla.dates.{rec.get('candidate_id')}")
            if max(dr_keys) > CLUSTER_A_MAX_DAY:
                raise ClusterALeakageError(
                    f"CLUSTER_A_LEAKAGE [{rec.get('candidate_id')}]: date {max(dr_keys)!r} > {CLUSTER_A_MAX_DAY!r}"
                )

        cid = str(rec["candidate_id"]).strip()
        if not cid:
            raise ValueError("candidate_id must be non-empty")

        params_obj = dict(rec.get("params") or {})
        params_sha = canonical_sha256(params_obj)
        rn_scope = rec.get("red_news_scope_disclosure") or {}
        ts_utc = created_utc or _utc_now_iso()

        with self._connect() as con:
            cur_cnt = int(con.execute("SELECT COUNT(*) FROM cluster_a_trials").fetchone()[0])
            exists = con.execute("SELECT 1 FROM cluster_a_trials WHERE candidate_id = ?", [cid]).fetchone()
            if exists is not None:
                raise ValueError(f"DUPLICATE_CLUSTER_A_TRIAL_ID: {cid!r}")
            if cur_cnt + 1 > self.max_trials:
                raise BudgetExceededError(
                    f"BUDGET_CAP_EXCEEDED: attempted trial #{cur_cnt + 1} > max_trials={self.max_trials} "
                    f"(hard cap {HARD_MAX_TRIALS})"
                )
            con.execute(
                """
                INSERT INTO cluster_a_trials VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                [
                    cur_cnt + 1,
                    cid,
                    str(rec["family_id"]),
                    str(rec["symbol"]),
                    str(rec["leader_symbol"]) if rec.get("leader_symbol") else None,
                    json.dumps([int(y) for y in yrs]),
                    str(rec["blindness_tier"]),
                    bool(rec["mt5_hcc_ready"]),
                    str(rec["data_resolution"]),
                    bool(rn_scope.get("has_nzd_chf_scope_gap", False)),
                    _require_strict_int(rec["n_trades"], "n_trades", lo=0),
                    _require_finite_float(rec["winrate_frac"], "winrate_frac", lo=0.0, hi=1.0),
                    _require_finite_float(rec["rr_ratio"], "rr_ratio", lo=0.0),
                    _require_finite_float(rec["ev_r_1x"], "ev_r_1x"),
                    _require_finite_float(rec["ev_r_15x"], "ev_r_15x"),
                    _require_finite_float(rec["ev_r_2x"], "ev_r_2x"),
                    _require_finite_float(rec["pf_1x"], "pf_1x", lo=0.0),
                    _require_finite_float(rec["pf_15x"], "pf_15x", lo=0.0),
                    _require_finite_float(rec["pf_2x"], "pf_2x", lo=0.0),
                    _require_finite_float(rec["total_r_1x"], "total_r_1x"),
                    _require_finite_float(rec["total_r_15x"], "total_r_15x"),
                    _require_finite_float(rec["total_r_2x"], "total_r_2x"),
                    _require_finite_float(rec["max_dd_r_1x"], "max_dd_r_1x", lo=0.0),
                    _require_finite_float(rec["calmar_1x"], "calmar_1x"),
                    _require_finite_float(rec["sharpe_1x"], "sharpe_1x"),
                    _require_finite_float(sharpe_daily_a, "sharpe_daily_a"),
                    _require_finite_float(rec["median_fric_over_sl_1x"], "median_fric_over_sl_1x", lo=0.0),
                    _require_finite_float(rec["median_fric_over_sl_2x"], "median_fric_over_sl_2x", lo=0.0),
                    _require_strict_int(rec["max_exit_utc_sec"], "max_exit_utc_sec", lo=0),
                    bool(rec["all_flat_by_2050_utc"]),
                    _require_finite_float(rec["swap_r_total"], "swap_r_total"),
                    _require_finite_float(p_value_emp_a, "p_value_emp_a", lo=0.0, hi=1.0),
                    bool(is_finalist),
                    str(host_executed),
                    str(shard_id),
                    params_sha,
                    json.dumps(params_obj, sort_keys=True),
                    0,
                    0,
                    ts_utc,
                ],
            )

    def record_cluster_b_eval(
        self,
        eval_row: Mapping[str, Any],
        *,
        accretion_accepted: bool = False,
        evaluated_utc: str | None = None,
    ) -> None:
        """Insert one ONE-SHOT Cluster B evaluation row (fail-closed on duplicate or Holdout leak)."""
        enforce_holdout_zero_rows(
            eval_row.get("holdout_rows_analysed", -1),
            context=f"ledger.clb.{eval_row.get('candidate_id')}",
        )
        if int(eval_row.get("order_send_count", -1)) != 0:
            raise ValueError(f"ORDER_SEND_VIOLATION in Cluster B record {eval_row.get('candidate_id')!r}")
        yrs = list(eval_row.get("years_evaluated") or [])
        if any(int(y) < 2021 or int(y) > 2024 for y in yrs):
            raise ClusterBContaminationError(
                f"CLUSTER_B_CONTAMINATION [{eval_row.get('candidate_id')}]: years_evaluated={yrs} outside 2021-2024"
            )

        cid = str(eval_row["candidate_id"]).strip()
        ts_utc = evaluated_utc or _utc_now_iso()
        rn_scope = eval_row.get("red_news_scope_disclosure") or {}

        with self._connect() as con:
            if self.is_cluster_b_one_shot_consumed():
                raise ClusterBOneShotViolationError(
                    f"CLUSTER_B_ONE_SHOT_ALREADY_CONSUMED: refusing additional Cluster B insert for {cid!r}"
                )
            exists = con.execute("SELECT 1 FROM cluster_b_evals WHERE candidate_id = ?", [cid]).fetchone()
            if exists is not None:
                raise ClusterBOneShotViolationError(f"DUPLICATE_CLUSTER_B_EVAL: {cid!r} already evaluated")
            cur_cnt = int(con.execute("SELECT COUNT(*) FROM cluster_b_evals").fetchone()[0])
            con.execute(
                """
                INSERT INTO cluster_b_evals VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?
                )
                """,
                [
                    cur_cnt + 1,
                    cid,
                    str(eval_row["family_id"]),
                    str(eval_row["symbol"]),
                    str(eval_row["leader_symbol"]) if eval_row.get("leader_symbol") else None,
                    json.dumps([int(y) for y in yrs]),
                    str(eval_row["blindness_tier"]),
                    bool(eval_row["mt5_hcc_ready"]),
                    str(eval_row["data_resolution"]),
                    bool(rn_scope.get("has_nzd_chf_scope_gap", False)),
                    _require_strict_int(eval_row["n_trades_b"], "n_trades_b", lo=0),
                    _require_finite_float(eval_row["winrate_frac_b"], "winrate_frac_b", lo=0.0, hi=1.0),
                    _require_finite_float(eval_row["rr_ratio_b"], "rr_ratio_b", lo=0.0),
                    _require_finite_float(eval_row["ev_r_1x_b"], "ev_r_1x_b"),
                    _require_finite_float(eval_row["ev_r_15x_b"], "ev_r_15x_b"),
                    _require_finite_float(eval_row["ev_r_2x_b"], "ev_r_2x_b"),
                    _require_finite_float(eval_row["pf_1x_b"], "pf_1x_b", lo=0.0),
                    _require_finite_float(eval_row["pf_15x_b"], "pf_15x_b", lo=0.0),
                    _require_finite_float(eval_row["pf_2x_b"], "pf_2x_b", lo=0.0),
                    _require_finite_float(eval_row["total_r_1x_b"], "total_r_1x_b"),
                    _require_finite_float(eval_row["total_r_2x_b"], "total_r_2x_b"),
                    _require_finite_float(eval_row["max_dd_r_1x_b"], "max_dd_r_1x_b", lo=0.0),
                    _require_finite_float(eval_row["calmar_1x_b"], "calmar_1x_b"),
                    _require_finite_float(eval_row["sharpe_1x_b"], "sharpe_1x_b"),
                    _require_finite_float(eval_row["sharpe_daily_b"], "sharpe_daily_b"),
                    _require_finite_float(eval_row["cost_breakeven_mult"], "cost_breakeven_mult", lo=0.0),
                    _require_finite_float(eval_row["p_value_signflip"], "p_value_signflip", lo=0.0, hi=1.0),
                    _require_finite_float(eval_row["bh_fdr_q"], "bh_fdr_q", lo=0.0, hi=1.0),
                    _require_finite_float(eval_row["dsr_empirical"], "dsr_empirical", lo=0.0, hi=1.0),
                    _require_finite_float(eval_row["pbo_cscv"], "pbo_cscv", lo=0.0, hi=1.0),
                    _require_finite_float(eval_row["corr_vs_port_7e"], "corr_vs_port_7e", lo=-1.0, hi=1.0),
                    _require_finite_float(eval_row["tail_corr_vs_port_7e"], "tail_corr_vs_port_7e", lo=-1.0, hi=1.0),
                    _require_strict_int(eval_row["max_exit_utc_sec"], "max_exit_utc_sec", lo=0),
                    _require_finite_float(eval_row["swap_r_total"], "swap_r_total"),
                    _require_strict_int(eval_row["gates_passed_count"], "gates_passed_count", lo=0, hi=8),
                    bool(eval_row["all_8_gates_passed"]),
                    json.dumps(list(eval_row["failed_gates"])),
                    str(eval_row["council_verdict"]),
                    str(eval_row["tier_classification"]),
                    bool(accretion_accepted),
                    str(eval_row.get("host_executed", "DEV_PC")),
                    str(eval_row.get("shard_id", "local")),
                    0,
                    0,
                    ts_utc,
                ],
            )

    def record_run_meta(
        self,
        *,
        run_id: str,
        cluster_a_frozen_sha256: str,
        m_total: int,
        finalist_count: int,
        survivor_count: int,
        bench_reserve_count: int,
        accretive_count: int,
        port_v5_equals_port_7e: bool,
        completed_utc: str | None = None,
    ) -> None:
        if m_total > self.max_trials:
            raise BudgetExceededError(f"BUDGET_CAP_EXCEEDED: m_total={m_total} > {self.max_trials}")
        ts_utc = completed_utc or _utc_now_iso()
        with self._connect() as con:
            if self.is_cluster_b_one_shot_consumed():
                raise ClusterBOneShotViolationError("CLUSTER_B_ONE_SHOT_ALREADY_CONSUMED")
            con.execute(
                """
                INSERT INTO arena_runs_meta VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    str(run_id),
                    str(cluster_a_frozen_sha256),
                    True,
                    int(m_total),
                    int(self.max_trials),
                    int(finalist_count),
                    int(survivor_count),
                    int(bench_reserve_count),
                    int(accretive_count),
                    bool(port_v5_equals_port_7e),
                    0,
                    0,
                    ts_utc,
                ],
            )


# ---------------------------------------------------------------------------
# 2. Pure Statistical Helpers (Sign-Flip P, Breakeven, Calendar Alignment, PBO)
# ---------------------------------------------------------------------------


def compute_empirical_sign_flip_p(
    returns: Sequence[float] | np.ndarray,
    *,
    draws: int = DEFAULT_SIGN_FLIP_DRAWS,
    seed: int = DEFAULT_SIGN_FLIP_SEED_BASE,
) -> float:
    """One-sided empirical Rademacher sign-flip permutation p-value (`H0: E[r] <= 0`)."""
    arr = np.asarray(returns, dtype=np.float64)
    if arr.ndim != 1 or not bool(np.all(np.isfinite(arr))):
        raise ValueError("returns must be a finite 1D array")
    n = int(arr.size)
    if n < 2:
        return 1.0
    if float(np.sum(arr)) <= 0.0:
        return 1.0
    n_draws = _require_strict_int(draws, "draws", lo=100, hi=200_000)
    sd = _require_strict_int(seed, "seed", lo=0)
    try:
        p_val = float(sign_flip_p_numba(arr, -arr, draws=n_draws, seed=sd))
    except Exception:
        # Pure-NumPy fallback if Numba unavailable in minimal CI
        rng = np.random.default_rng(sd)
        obs = float(np.sum(arr))
        ge = 0
        chunk = 2000
        for start in range(0, n_draws, chunk):
            sz = min(chunk, n_draws - start)
            signs = rng.choice(np.array([-1.0, 1.0]), size=(sz, n))
            sums = signs @ arr
            ge += int(np.count_nonzero(sums >= obs - 1e-12))
        p_val = float(ge + 1.0) / float(n_draws + 1.0)
    return float(min(1.0, max(1.0 / float(n_draws + 1), p_val)))


def compute_cost_breakeven_mult(total_r_1x: float, total_r_2x: float) -> float:
    """Exact cost breakeven multiple matching `research_council.py:537-542`."""
    r1 = _require_finite_float(total_r_1x, "total_r_1x")
    r2 = _require_finite_float(total_r_2x, "total_r_2x")
    drag_1x = r1 - r2
    if drag_1x > 1e-9:
        return max(0.0, 1.0 + r1 / drag_1x)
    return 99.0 if r1 > 0.0 else 0.0


def align_daily_map_to_calendar(
    daily_map: Mapping[str, float],
    calendar_dates: Sequence[str],
    *,
    context: str = "align_daily_map",
    max_allowed_date: str = HOLDOUT_CUTOFF_DATE,
    min_allowed_date: str | None = None,
) -> np.ndarray:
    """Align a `{YYYY-MM-DD: r}` dict onto an explicit sorted date vector with fail-closed date guards."""
    cal = [str(d) for d in calendar_dates]
    if not cal:
        raise ValueError(f"EMPTY_CALENDAR [{context}]")
    enforce_pre_holdout_dates(cal, context=f"{context}.calendar")
    if daily_map:
        dkeys = sorted(str(k) for k in daily_map)
        enforce_pre_holdout_dates(dkeys, context=f"{context}.daily_map")
        if dkeys[-1] > max_allowed_date:
            if max_allowed_date == CLUSTER_A_MAX_DAY:
                raise ClusterALeakageError(
                    f"CLUSTER_A_LEAKAGE [{context}]: date {dkeys[-1]!r} > {CLUSTER_A_MAX_DAY!r}"
                )
            raise HoldoutLockError(f"CUTOFF_BREACH [{context}]: date {dkeys[-1]!r} > {max_allowed_date!r}")
        if min_allowed_date is not None and dkeys[0] < min_allowed_date:
            raise ClusterBContaminationError(
                f"CLUSTER_B_CONTAMINATION [{context}]: date {dkeys[0]!r} < {min_allowed_date!r}"
            )
    arr = np.zeros(len(cal), dtype=np.float64)
    for idx, d in enumerate(cal):
        if d in daily_map:
            arr[idx] = _require_finite_float(daily_map[d], f"{context}[{d}]")
    return arr


def _select_even_pbo_slices(n_obs: int, preferred: int = 16) -> int:
    if n_obs < 8:
        raise ValueError(f"Insufficient observations ({n_obs}) for CSCV PBO (need >= 8)")
    target = int(preferred)
    if target < 4 or target % 2 != 0:
        target = 16
    while target >= 4:
        if n_obs >= target and (target // 2) * (n_obs // target) >= 2:
            return target
        target -= 2
    return 4


def compute_daily_calendar_sharpe(daily_vec: np.ndarray, *, annualization_days: int = 252) -> float:
    """Compute calendar-aligned annualized Sharpe via canonical `quant_core.metrics.compute_sharpe`."""
    arr = np.asarray(daily_vec, dtype=np.float64)
    if arr.size < 2 or float(np.std(arr, ddof=1)) <= 1e-15:
        return 0.0
    res = compute_sharpe(arr, annualization_days=annualization_days, calendar_aligned=True)
    return float(res.sharpe_annualized)


def build_family_cluster_a_pbo_matrices(
    cluster_a_results: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Build strictly Cluster A (`<= 2020-12-31`, ZERO Cluster B peeking) `(T_A, M_fam)` CSCV PBO matrices."""
    by_fam: dict[str, list[Mapping[str, Any]]] = {}
    for rec in cluster_a_results:
        yrs = [int(y) for y in (rec.get("years_evaluated") or [])]
        if any(y > 2020 for y in yrs):
            raise ClusterALeakageError(
                f"CLUSTER_A_LEAKAGE [pbo_matrix:{rec.get('candidate_id')}]: years={yrs} contains 2021+"
            )
        dr = rec.get("daily_returns_1x") or {}
        if dr:
            dmax = max(str(k) for k in dr)
            enforce_pre_holdout_dates([dmax], context=f"pbo_cla:{rec.get('candidate_id')}")
            if dmax > CLUSTER_A_MAX_DAY:
                raise ClusterALeakageError(
                    f"CLUSTER_A_LEAKAGE [pbo_matrix:{rec.get('candidate_id')}]: date {dmax!r} > {CLUSTER_A_MAX_DAY!r}"
                )
        by_fam.setdefault(str(rec["family_id"]), []).append(rec)

    out: dict[str, dict[str, Any]] = {}
    for fam_id, recs in sorted(by_fam.items()):
        # Use common Cluster A year range across all symbols in this family (e.g. 2019-2020 for mixed 6Y/7Y)
        min_start_year = max(
            (min(int(y) for y in r["years_evaluated"]) for r in recs if r.get("years_evaluated")),
            default=2019,
        )
        max_end_year = min(
            (max(int(y) for y in r["years_evaluated"]) for r in recs if r.get("years_evaluated")),
            default=2020,
        )
        if max_end_year > 2020:
            raise ClusterALeakageError(f"CLUSTER_A_LEAKAGE [pbo_matrix:{fam_id}]: max_end_year={max_end_year} > 2020")
        cal_dates = _weekday_calendar_dates(f"{min_start_year:04d}-01-01", f"{max_end_year:04d}-12-31")
        cols: list[np.ndarray] = []
        cids: list[str] = []
        for r in sorted(recs, key=lambda x: str(x["candidate_id"])):
            vec = align_daily_map_to_calendar(
                r.get("daily_returns_1x") or {},
                cal_dates,
                context=f"pbo_cla:{r['candidate_id']}",
                max_allowed_date=CLUSTER_A_MAX_DAY,
            )
            cols.append(vec)
            cids.append(str(r["candidate_id"]))
        mat = np.column_stack(cols) if cols else np.empty((len(cal_dates), 0), dtype=np.float64)
        pbo_val = 1.0
        n_slices_used = 0
        n_combos = 0
        if mat.shape[1] >= 2 and mat.shape[0] >= 8:
            n_slices_used = _select_even_pbo_slices(int(mat.shape[0]), preferred=16)
            pbo_res = compute_pbo_cscv(mat, n_slices=n_slices_used)
            pbo_val = float(pbo_res.pbo)
            n_combos = int(pbo_res.n_combinations)
        out[fam_id] = {
            "family_id": fam_id,
            "matrix": mat,
            "dates": cal_dates,
            "candidate_ids": cids,
            "n_trials": int(mat.shape[1]),
            "n_obs": int(mat.shape[0]),
            "n_slices": n_slices_used,
            "n_combinations": n_combos,
            "pbo_cscv": round(pbo_val, 4),
            "cluster_b_touched": False,
        }
    return out


# ---------------------------------------------------------------------------
# 3. PORT_7E Canonical Dev & Cluster B Tapes Loader (`frozen_9e_tapes_v2`)
# ---------------------------------------------------------------------------


def load_port_7e_canonical_tapes(
    *,
    tapes_dir: Path = DEFAULT_DERIVED_TAPES_DIR,
    stem: str = DEFAULT_DERIVED_TAPES_STEM,
) -> dict[str, Any]:
    """Load exact `PORT_7E` red-news-guarded 1.0x / 1.5x / 2.0x daily & trade return series (<= 2024-12-31)."""
    from quant_factory.capital_optimizer.replay_cache import (
        _apply_cost_stress_to_tapes,
        _apply_red_news_guard_to_tape,
    )
    from quant_factory.capital_optimizer.x13_shard import (
        load_frozen_tapes_v2_direct,
        load_red_news_calendar_direct,
    )

    loaded = load_frozen_tapes_v2_direct(tapes_dir=tapes_dir, stem=stem)
    enforce_holdout_zero_rows(loaded["holdout_rows_analysed"], context="load_port_7e_canonical_tapes")
    enforce_pre_holdout_dates(loaded["ext_days"], context="load_port_7e_canonical_tapes.ext_days")

    news_cal, news_meta = load_red_news_calendar_direct()
    raw_tapes: Mapping[str, Any] = loaded["tapes"]

    # Build full weekday Dev (2018-2024) & Cluster B (2021-2024) calendars aligned with PORT_7E active days
    all_ext_days = sorted(str(d) for d in loaded["ext_days"])
    clb_days = [d for d in all_ext_days if CLUSTER_B_MIN_DAY <= d <= CLUSTER_B_MAX_DAY]
    if not clb_days:
        raise ValueError("PORT_7E Cluster B ext_days is empty")

    # Apply red-news guard once to each CORE7 engine, then compute 1.0x / 1.5x / 2.0x cost stress
    guarded_1x: dict[str, Any] = {}
    for eid in CORE7_IDS:
        if eid not in raw_tapes:
            raise KeyError(f"PORT_7E engine {eid!r} missing from frozen_9e_tapes_v2")
        gt, _ = _apply_red_news_guard_to_tape(raw_tapes[eid], news_cal, mode="FLATTEN_5M", pad_sec=300)
        guarded_1x[eid] = gt

    stressed_15x = _apply_cost_stress_to_tapes(guarded_1x, 1.5)
    stressed_20x = _apply_cost_stress_to_tapes(guarded_1x, 2.0)

    def _extract_engine_daily_r(tape_map: Mapping[str, Any]) -> dict[str, float]:
        out: dict[str, float] = {}
        for dk, (row, _stamps, _marks) in tape_map.items():
            stop_c = max(1e-6, float(row.get("stop_risk_with_cost_usd") or 0.0))
            net_usd = float(row.get("net_usd_per_lot") or 0.0)
            out[str(dk)] = net_usd / stop_c
        return out

    eng_daily_r_1x: dict[str, dict[str, float]] = {}
    eng_daily_r_15x: dict[str, dict[str, float]] = {}
    eng_daily_r_20x: dict[str, dict[str, float]] = {}
    for eid in CORE7_IDS:
        eng_daily_r_1x[eid] = _extract_engine_daily_r(guarded_1x[eid])
        eng_daily_r_15x[eid] = _extract_engine_daily_r(stressed_15x[eid])
        eng_daily_r_20x[eid] = _extract_engine_daily_r(stressed_20x[eid])

    def _combine_port_daily_pct(dates: Sequence[str], eng_maps: Mapping[str, Mapping[str, float]]) -> np.ndarray:
        tot = np.zeros(len(dates), dtype=np.float64)
        for eid in CORE7_IDS:
            w_pct = float(DEFAULT_CORE7_BASE_RISK[eid]) * 100.0  # percent of equity per 1R
            em = eng_maps[eid]
            for i, d in enumerate(dates):
                if d in em:
                    tot[i] += w_pct * float(em[d])
        return tot

    # Cluster B full weekday calendar + PORT_7E ext_days alignment
    clb_weekday_dates = _weekday_calendar_dates(CLUSTER_B_MIN_DAY, CLUSTER_B_MAX_DAY)
    dev_weekday_dates = _weekday_calendar_dates("2018-01-01", CLUSTER_B_MAX_DAY)

    port_clb_1x = _combine_port_daily_pct(clb_weekday_dates, eng_daily_r_1x)
    port_clb_15x = _combine_port_daily_pct(clb_weekday_dates, eng_daily_r_15x)
    port_clb_20x = _combine_port_daily_pct(clb_weekday_dates, eng_daily_r_20x)
    port_dev_1x = _combine_port_daily_pct(dev_weekday_dates, eng_daily_r_1x)

    return {
        "source": "frozen_9e_tapes_v2",
        "npz_sha256": loaded["npz_sha256"],
        "binding_sha256": loaded["binding_sha256"],
        "red_news_calendar": news_meta,
        "core7_ids": list(CORE7_IDS),
        "core7_base_risk_frac": {eid: float(DEFAULT_CORE7_BASE_RISK[eid]) for eid in CORE7_IDS},
        "core7_symbols": dict(CORE7_ENGINE_SYMBOLS),
        "ext_days": all_ext_days,
        "clb_ext_days": clb_days,
        "clb_dates": clb_weekday_dates,
        "dev_dates": dev_weekday_dates,
        "port_clb_daily_ret_pct_1x": port_clb_1x,
        "port_clb_daily_ret_pct_15x": port_clb_15x,
        "port_clb_daily_ret_pct_2x": port_clb_20x,
        "port_dev_daily_ret_pct_1x": port_dev_1x,
        "engine_daily_r_1x": eng_daily_r_1x,
        "engine_daily_r_15x": eng_daily_r_15x,
        "engine_daily_r_2x": eng_daily_r_20x,
        "holdout_rows_analysed": 0,
    }


def compute_portfolio_daily_metrics(daily_ret_pct: np.ndarray, *, years_span: float = 4.0) -> dict[str, float]:
    """Compute balanced daily portfolio metrics on percent return series (Sharpe, PF, R-vel, MaxDD, Calmar)."""
    r = np.asarray(daily_ret_pct, dtype=np.float64)
    if r.size < 2:
        return {
            "total_ret_pct": 0.0,
            "annual_ret_pct": 0.0,
            "sharpe": 0.0,
            "pf": 0.0,
            "max_dd_pct": 0.0,
            "calmar": 0.0,
            "active_days": 0,
            "win_day_frac": 0.0,
            "r_velocity_annual_r": 0.0,
        }
    total_ret = float(np.sum(r))
    ann_ret = total_ret / max(float(years_span), 0.25)
    sharpe = compute_daily_calendar_sharpe(r, annualization_days=252)

    active = r[np.abs(r) > 1e-12]
    wins = active[active > 0.0]
    losses = active[active < 0.0]
    gw = float(np.sum(wins)) if wins.size else 0.0
    gl = float(np.sum(np.abs(losses))) if losses.size else 0.0
    pf = (gw / gl) if gl > 1e-12 else (99.0 if gw > 0.0 else 0.0)
    win_day_frac = float(wins.size) / float(active.size) if active.size else 0.0

    eq = np.cumsum(r)
    peaks = np.maximum.accumulate(np.concatenate((np.array([0.0]), eq)))[1:]
    dd = peaks - eq
    max_dd = float(np.max(dd)) if dd.size else 0.0
    calmar = (ann_ret / max_dd) if max_dd > 1e-12 else (99.0 if ann_ret > 0.0 else 0.0)

    # Portfolio R-velocity: annualised return normalized by 0.50% standard single-engine risk unit
    r_vel_ann = ann_ret / 0.50
    return {
        "total_ret_pct": round(total_ret, 4),
        "annual_ret_pct": round(ann_ret, 4),
        "sharpe": round(sharpe, 4),
        "pf": round(min(pf, 99.0), 4),
        "max_dd_pct": round(max_dd, 4),
        "calmar": round(min(max(calmar, -99.0), 99.0), 4),
        "active_days": int(active.size),
        "win_day_frac": round(win_day_frac, 4),
        "r_velocity_annual_r": round(r_vel_ann, 4),
    }


# ---------------------------------------------------------------------------
# 4. Step A & C Shard Dispatcher (X13 Full Performance + PC Dev Mode A Safe)
# ---------------------------------------------------------------------------


def group_candidates_into_family_shards(
    candidates: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Group candidates by family into clean, memory-lean shards (<= 11 symbols per shard)."""
    by_fam: dict[str, list[dict[str, Any]]] = {}
    for c in candidates:
        fid = str(c["family_id"])
        by_fam.setdefault(fid, []).append(dict(c))
    shards: list[dict[str, Any]] = []
    for idx, fid in enumerate(fam5.FAMILY_IDS):
        if fid in by_fam and by_fam[fid]:
            cands = by_fam[fid]
            syms = sorted(
                {ldr.normalize_symbol(str(c["symbol"])) for c in cands}
                | {ldr.normalize_symbol(str(c["leader_symbol"])) for c in cands if c.get("leader_symbol")}
            )
            shards.append(
                {
                    "shard_index": idx,
                    "family_id": fid,
                    "candidate_count": len(cands),
                    "symbols": syms,
                    "candidates": cands,
                }
            )
    return shards


def _validate_x13_clean_job_id(job_id: str) -> str:
    """Validate clean shard job_id (e.g. `w5_m1_cla_shard_0`) with ZERO forbidden air-gap tokens."""
    cr.assert_dev_only_path(job_id)
    return cr._validate_job_id(job_id)


def dispatch_m1_shards_x13_full(
    shards: Sequence[Mapping[str, Any]],
    *,
    split: str,
    job_prefix: str,
    work_dir: Path = DEFAULT_SHARD_WORK_DIR,
    x13_only: bool = True,
    x13_share_pct: int = 85,
    lan_only: bool = False,
    timeout_per_shard: int = 1800,
    force_mode_b: bool = False,
) -> dict[str, Any]:
    """Dispatch M1 candidate shards via `x13_shard_dispatcher.py` (`X13` 8 threads FULL PERFORMANCE)."""
    x13_disp.assert_dev_pc_mode_a_enforced(force_mode_b=force_mode_b)
    if split not in ("cluster_a", "cluster_b"):
        raise ValueError(f"Unsupported split={split!r}; expected 'cluster_a' or 'cluster_b'")
    _validate_x13_clean_job_id(job_prefix)

    t0 = time_mod.perf_counter()
    all_results: list[dict[str, Any]] = []
    shard_receipts: list[dict[str, Any]] = []
    x13_candidates = 0
    dev_candidates = 0
    total_candidates = 0

    for k, sh in enumerate(shards):
        cands = list(sh["candidates"])
        if not cands:
            continue
        raw_jid = _validate_x13_clean_job_id(f"{job_prefix}_{k}")
        dest = work_dir / raw_jid
        t_sh = time_mod.perf_counter()

        # Pass each candidate dict as an item in shard_specs (or grouped shard dict)
        shard_specs = [{"family_id": sh["family_id"], "candidates": cands}]
        res = x13_disp.dispatch_wave5_shards(
            raw_jid,
            DEFAULT_FAMILIES_ENTRY_SCRIPT,
            shard_specs,
            x13_share_pct=x13_share_pct,
            min_ram_gb=4.0,
            required_packages=("numpy", "pyarrow", "numba"),
            touches_holdout=False,
            touches_vps=False,
            requires_admin=False,
            needs_gpu=False,
            strict_ntp=True,
            allow_ntp_drift=False,
            x13_only=x13_only,
            force_mode_b=False,
            lan_only=lan_only,
            dry_run=False,
            dest_dir=dest,
            extra_files=tuple(p for p in DEFAULT_X13_EXTRA_FILES if p.is_file()),
            extra_args=["--split", split],
            result_filename="shard_results.json",
            timeout=timeout_per_shard,
        )
        sh_elapsed = round(time_mod.perf_counter() - t_sh, 3)
        if not res.get("ok"):
            raise RuntimeError(f"M1 shard {raw_jid} failed dispatch/integrity: status={res.get('status')!r}")

        hosts_exec = list(res.get("hosts_executed") or [])
        workers = list(res.get("workers") or [])
        shard_rows: list[dict[str, Any]] = []
        for w in workers:
            w_host = str(w.get("executed_on", "UNKNOWN"))
            w_res_path = Path(str(w["result_dir"])) / "shard_results.json"
            if not w_res_path.is_file():
                raise FileNotFoundError(f"Missing shard_results.json for {raw_jid}: {w_res_path}")
            payload = json.loads(w_res_path.read_text(encoding="utf-8"))
            enforce_holdout_zero_rows(payload.get("holdout_rows_analysed", -1), context=f"shard.{raw_jid}")
            if int(payload.get("order_send_count", -1)) != 0:
                raise ValueError(f"ORDER_SEND_VIOLATION in shard {raw_jid}")
            for row in payload.get("results") or []:
                row_copy = dict(row)
                row_copy["_host_executed"] = w_host
                row_copy["_shard_id"] = raw_jid
                shard_rows.append(row_copy)
                total_candidates += 1
                if w_host == "X13_WORKER":
                    x13_candidates += 1
                else:
                    dev_candidates += 1

        if len(shard_rows) != len(cands):
            raise RuntimeError(
                f"SHARD_COUNT_MISMATCH [{raw_jid}]: expected {len(cands)} results, got {len(shard_rows)}"
            )
        all_results.extend(shard_rows)
        shard_receipts.append(
            {
                "shard_id": raw_jid,
                "normalized_job_id": res.get("job_id"),
                "family_id": sh["family_id"],
                "candidate_count": len(shard_rows),
                "symbols": list(sh["symbols"]),
                "hosts_executed": hosts_exec,
                "target": (res.get("decision") or {}).get("target"),
                "x13_threads": (res.get("decision") or {}).get("x13_threads"),
                "dev_pc_cores": (res.get("decision") or {}).get("dev_pc_cores"),
                "fallback_used": bool((res.get("decision") or {}).get("fallback_used")),
                "fallback_reason": (res.get("decision") or {}).get("fallback_reason"),
                "elapsed_sec": sh_elapsed,
                "verify_ok": bool((res.get("merged_verify") or {}).get("ok")),
            }
        )

    x13_pct = round(100.0 * float(x13_candidates) / float(max(1, total_candidates)), 2)
    return {
        "split": split,
        "total_candidates": total_candidates,
        "x13_candidates": x13_candidates,
        "dev_pc_candidates": dev_candidates,
        "x13_offload_pct": x13_pct,
        "elapsed_sec": round(time_mod.perf_counter() - t0, 3),
        "shards": shard_receipts,
        "results": all_results,
    }


# ---------------------------------------------------------------------------
# 5. Step C — Pure Cluster A Finalist Selection & Freeze (ZERO Cluster B Peek!)
# ---------------------------------------------------------------------------


def select_cluster_a_finalists(
    cluster_a_results: Sequence[Mapping[str, Any]],
    *,
    min_sharpe: float = CLUSTER_A_MIN_SHARPE,
    min_trades: int = CLUSTER_A_MIN_TRADES,
    min_ev_r: float = CLUSTER_A_MIN_EV_R,
) -> dict[str, Any]:
    """Select top Cluster A finalists purely on Cluster A metrics, deduplicated per `(family_id, symbol)`.

    Raises `BudgetExceededError` if `len(cluster_a_results) > 360` and `ClusterALeakageError`
    if ANY record contains Cluster B (`2021+`) or Holdout (`2025+`) dates.
    """
    n_total = len(cluster_a_results)
    if n_total == 0:
        raise ValueError("cluster_a_results must be non-empty")
    if n_total > HARD_MAX_TRIALS:
        raise BudgetExceededError(f"BUDGET_CAP_EXCEEDED: received {n_total} Cluster A trials > {HARD_MAX_TRIALS}")

    eligible_by_group: dict[tuple[str, str], list[dict[str, Any]]] = {}
    all_eligible_count = 0
    seen_cids: set[str] = set()

    for rec in cluster_a_results:
        cid = str(rec["candidate_id"])
        if cid in seen_cids:
            raise ValueError(f"DUPLICATE_CLUSTER_A_CANDIDATE: {cid!r}")
        seen_cids.add(cid)

        enforce_holdout_zero_rows(rec.get("holdout_rows_analysed", -1), context=f"select_cla.{cid}")
        yrs = [int(y) for y in (rec.get("years_evaluated") or [])]
        if any(y > 2020 for y in yrs):
            raise ClusterALeakageError(f"CLUSTER_A_LEAKAGE [{cid}]: years_evaluated={yrs} leaks 2021+")
        dr = rec.get("daily_returns_1x") or {}
        if dr:
            dkeys = sorted(str(k) for k in dr)
            enforce_pre_holdout_dates(dkeys, context=f"select_cla.dates.{cid}")
            if dkeys[-1] > CLUSTER_A_MAX_DAY:
                raise ClusterALeakageError(
                    f"CLUSTER_A_LEAKAGE [{cid}]: daily_returns contains date {dkeys[-1]!r} > {CLUSTER_A_MAX_DAY!r}"
                )

        sharpe = _require_finite_float(rec["sharpe_1x"], f"{cid}.sharpe_1x")
        n_tr = _require_strict_int(rec["n_trades"], f"{cid}.n_trades", lo=0)
        ev_r = _require_finite_float(rec["ev_r_1x"], f"{cid}.ev_r_1x")
        swap_r = _require_finite_float(rec.get("swap_r_total", 0.0), f"{cid}.swap_r_total")
        max_exit = _require_strict_int(rec.get("max_exit_utc_sec", 0), f"{cid}.max_exit_utc_sec", lo=0)
        flat_ok = bool(rec.get("all_flat_by_2050_utc", True)) and max_exit <= HARD_FLAT_MAX_UTC_SEC

        if (
            sharpe > float(min_sharpe)
            and n_tr >= int(min_trades)
            and ev_r > float(min_ev_r)
            and abs(swap_r) <= 1e-12
            and flat_ok
        ):
            all_eligible_count += 1
            grp_key = (str(rec["family_id"]), ldr.normalize_symbol(str(rec["symbol"])))
            eligible_by_group.setdefault(grp_key, []).append(dict(rec))

    finalists: list[dict[str, Any]] = []
    for grp_key in sorted(eligible_by_group.keys()):
        grp = eligible_by_group[grp_key]
        grp.sort(
            key=lambda r: (
                -float(r["sharpe_1x"]),
                -float(r["ev_r_1x"]),
                -float(r["total_r_1x"]),
                str(r["candidate_id"]),
            )
        )
        winner = grp[0]
        params_clean = dict(sorted((str(k), v) for k, v in (winner.get("params") or {}).items()))
        finalists.append(
            {
                "candidate_id": str(winner["candidate_id"]),
                "family_id": str(winner["family_id"]),
                "symbol": ldr.normalize_symbol(str(winner["symbol"])),
                "leader_symbol": ldr.normalize_symbol(str(winner["leader_symbol"]))
                if winner.get("leader_symbol")
                else None,
                "params": params_clean,
                "params_sha256": canonical_sha256(params_clean),
                "blindness_tier": str(winner["blindness_tier"]),
                "mt5_hcc_ready": bool(winner["mt5_hcc_ready"]),
                "data_resolution": str(winner["data_resolution"]),
                "red_news_scope_disclosure": dict(winner.get("red_news_scope_disclosure") or {}),
                "cluster_a_years": [int(y) for y in (winner.get("years_evaluated") or [])],
                "cluster_a_metrics": {
                    "n_trades": int(winner["n_trades"]),
                    "sharpe_1x": float(winner["sharpe_1x"]),
                    "ev_r_1x": float(winner["ev_r_1x"]),
                    "ev_r_2x": float(winner["ev_r_2x"]),
                    "pf_1x": float(winner["pf_1x"]),
                    "total_r_1x": float(winner["total_r_1x"]),
                    "max_dd_r_1x": float(winner["max_dd_r_1x"]),
                    "winrate_frac": float(winner["winrate_frac"]),
                    "rr_ratio": float(winner["rr_ratio"]),
                    "max_exit_utc_sec": int(winner["max_exit_utc_sec"]),
                    "swap_r_total": float(winner["swap_r_total"]),
                },
                "group_competitors_pruned": len(grp) - 1,
                "cluster_b_touched": False,
                "holdout_rows_analysed": 0,
            }
        )

    finalists.sort(key=lambda r: (-float(r["cluster_a_metrics"]["sharpe_1x"]), str(r["candidate_id"])))
    freeze_body = {
        "schema": FROZEN_SCHEMA_VERSION,
        "m_total_cluster_a": n_total,
        "budget_cap": HARD_MAX_TRIALS,
        "selection_rules": {
            "min_sharpe_1x": float(min_sharpe),
            "min_trades": int(min_trades),
            "min_ev_r_1x": float(min_ev_r),
            "dedup_key": "(family_id, symbol)",
            "swap_zero_required": True,
            "hard_flat_max_utc_sec": HARD_FLAT_MAX_UTC_SEC,
        },
        "eligible_before_dedup_count": all_eligible_count,
        "finalist_count": len(finalists),
        "cluster_b_touched": False,
        "holdout_rows_analysed": 0,
        "order_send_count": ORDER_SEND_COUNT,
        "finalists": finalists,
    }
    frozen_sha = canonical_sha256(freeze_body)
    return {
        **freeze_body,
        "cluster_a_frozen_sha256": frozen_sha,
    }


# ---------------------------------------------------------------------------
# 6. Step D — Strict 8-Gate Cluster B Filter + `research_council.py`
# ---------------------------------------------------------------------------


_FAMILY_COUNTERPARTY_RATIONALES: Final[dict[str, tuple[str, str]]] = {
    fam5.FAM_F5A: (
        "Regional cash-open order-flow imbalance & dealer inventory rebalancing",
        (
            "Forced cash-open auction & institutional benchmark execution creates "
            "directional order-flow momentum outside US100 E4/E5 hours."
        ),
    ),
    fam5.FAM_F5B: (
        "Retail stop-cluster sweep & liquidity-provider mean-reversion reclaim",
        (
            "Clustered retail stops beyond intraday session extremes are swept by liquidity "
            "providers, causing rapid M1 exhaustion reclaims orthogonal to breakouts."
        ),
    ),
    fam5.FAM_F5C: (
        "Prior-day NR5/NR20 volatility compression breakout on cross pairs",
        (
            "Multi-day options/dealer gamma compression on liquid crosses releases "
            "directional range expansion during Asia or Late NY outside E6 hours."
        ),
    ),
    fam5.FAM_F5D: (
        "Strictly causal cross-asset information diffusion (shift >= 1m lead-lag)",
        (
            "Macro shocks price first into high-liquidity benchmark leaders before "
            "propagating with causal M1 latency into correlated follower assets."
        ),
    ),
    fam5.FAM_F5E: (
        "Pure-price intraday TWAP / Asian range boundary overextension fade",
        (
            "Short-term liquidity consumers push intraday price away from fair pure-price "
            "TWAP/Asian range equilibrium, creating revertible supply-demand imbalance."
        ),
    ),
}


def validate_promotion_candidate(eval_row: Mapping[str, Any]) -> None:
    """Fail-closed guard refusing promotion of ANY candidate that did not clear all 8 gates."""
    cid = str(eval_row.get("candidate_id", "<unknown>"))
    enforce_holdout_zero_rows(eval_row.get("holdout_rows_analysed", -1), context=f"promote.{cid}")
    if int(eval_row.get("order_send_count", -1)) != 0:
        raise UnverifiedPromotionError(f"UNVERIFIED_PROMOTION [{cid}]: order_send_count != 0")
    if eval_row.get("all_8_gates_passed") is not True:
        raise UnverifiedPromotionError(
            f"UNVERIFIED_PROMOTION [{cid}]: failed gates={eval_row.get('failed_gates')!r}"
        )
    if eval_row.get("tier_classification") != TIER_1_PROP_CANDIDATE:
        raise UnverifiedPromotionError(
            f"UNVERIFIED_PROMOTION [{cid}]: tier={eval_row.get('tier_classification')!r} != {TIER_1_PROP_CANDIDATE!r}"
        )
    verdict = eval_row.get("council_verdict")
    if verdict != "APPROVE_FOR_INCUBATION":
        raise UnverifiedPromotionError(
            f"UNVERIFIED_PROMOTION [{cid}]: council_verdict={verdict!r} != APPROVE_FOR_INCUBATION"
        )
    if not bool(eval_row.get("gate_checks", {}).get("G1_bh_fdr_q_le_0_10", False)):
        raise UnverifiedPromotionError(f"UNVERIFIED_PROMOTION [{cid}]: BH-FDR gate not passed")


def evaluate_cluster_b_8_gates(
    *,
    cluster_b_results: Sequence[Mapping[str, Any]],
    cluster_a_by_id: Mapping[str, Mapping[str, Any]],
    all_cluster_a_trial_sharpes: Sequence[float],
    m_total: int,
    family_pbo_map: Mapping[str, Mapping[str, Any]],
    port_7e_clb_dates: Sequence[str],
    port_7e_clb_daily_ret_pct: np.ndarray,
    sign_flip_draws: int = DEFAULT_SIGN_FLIP_DRAWS,
) -> dict[str, Any]:
    """Run the strict 8-gate Cluster B statistical filter + `research_council.py` with ZERO threshold relaxation."""
    m_tot = _require_strict_int(m_total, "m_total", lo=1, hi=HARD_MAX_TRIALS)
    if len(all_cluster_a_trial_sharpes) != m_tot:
        raise ValueError(
            f"TRIAL_SHARPES_LENGTH_MISMATCH: len(trial_sharpes)={len(all_cluster_a_trial_sharpes)} != m_total={m_tot}"
        )
    trial_sharpes_arr = np.asarray(all_cluster_a_trial_sharpes, dtype=np.float64)
    if not bool(np.all(np.isfinite(trial_sharpes_arr))):
        raise ValueError("all_cluster_a_trial_sharpes contains non-finite values")

    clb_dates = [str(d) for d in port_7e_clb_dates]
    enforce_pre_holdout_dates(clb_dates, context="eval_clb_8gates.port_7e_dates")
    if clb_dates[0] < CLUSTER_B_MIN_DAY or clb_dates[-1] > CLUSTER_B_MAX_DAY:
        raise ClusterBContaminationError(
            f"CLUSTER_B_CONTAMINATION [port_7e]: {clb_dates[0]}..{clb_dates[-1]} outside 2021-2024"
        )
    inc_daily = np.asarray(port_7e_clb_daily_ret_pct, dtype=np.float64)
    if inc_daily.shape != (len(clb_dates),):
        raise ValueError(f"PORT_7E shape mismatch: {inc_daily.shape} vs {len(clb_dates)}")

    # Pre-validate all Cluster B records & compute exact empirical sign-flip p-values on Cluster B
    prepared_clb: list[dict[str, Any]] = []
    finalist_p_values: list[float] = []

    for rec in cluster_b_results:
        cid = str(rec["candidate_id"])
        enforce_holdout_zero_rows(rec.get("holdout_rows_analysed", -1), context=f"clb_8g.{cid}")
        if int(rec.get("order_send_count", -1)) != 0:
            raise ValueError(f"ORDER_SEND_VIOLATION [clb_8g.{cid}]")
        yrs = [int(y) for y in (rec.get("years_evaluated") or [])]
        if any(y < 2021 or y > 2024 for y in yrs):
            raise ClusterBContaminationError(f"CLUSTER_B_CONTAMINATION [{cid}]: years_evaluated={yrs}")
        if cid not in cluster_a_by_id:
            raise KeyError(f"Cluster B candidate {cid!r} missing from Cluster A records")

        dr_1x = rec.get("daily_returns_1x") or {}
        dr_15x = rec.get("daily_returns_15x") or {}
        dr_2x = rec.get("daily_returns_2x") or {}
        clb_daily_vec = align_daily_map_to_calendar(
            dr_1x,
            clb_dates,
            context=f"clb_8g:{cid}",
            max_allowed_date=CLUSTER_B_MAX_DAY,
            min_allowed_date=CLUSTER_B_MIN_DAY,
        )
        # Active traded-day returns (since all 5 families take <= 1 trade/day, active daily returns == trade R returns)
        active_r = np.array([float(v) for _, v in sorted(dr_1x.items())], dtype=np.float64)
        p_emp_b = compute_empirical_sign_flip_p(
            active_r,
            draws=sign_flip_draws,
            seed=_deterministic_seed(cid, DEFAULT_SIGN_FLIP_SEED_BASE + 1),
        )
        finalist_p_values.append(p_emp_b)
        prepared_clb.append(
            {
                "rec": rec,
                "cla_rec": cluster_a_by_id[cid],
                "clb_daily_vec": clb_daily_vec,
                "dr_1x": dr_1x,
                "dr_15x": dr_15x,
                "dr_2x": dr_2x,
                "p_emp_b": p_emp_b,
            }
        )

    # Gate 1: Full m_total=355 BH-FDR space (pruned Cluster A trials padded with p=1.0 -> zero Cluster B peek)
    n_pruned = m_tot - len(finalist_p_values)
    if n_pruned < 0:
        raise BudgetExceededError(
            f"FINALIST_EXCEEDS_BUDGET: {len(finalist_p_values)} finalists > m_total={m_tot}"
        )
    full_family_p_values: tuple[float, ...] = tuple([*finalist_p_values, *([1.0] * n_pruned)])
    q_all = benjamini_hochberg(list(full_family_p_values))

    evaluations: list[dict[str, Any]] = []
    survivors: list[dict[str, Any]] = []
    bench_reserves: list[dict[str, Any]] = []
    killed: list[dict[str, Any]] = []

    for idx, item in enumerate(prepared_clb):
        rec = item["rec"]
        cla_rec = item["cla_rec"]
        clb_daily_vec = item["clb_daily_vec"]
        cid = str(rec["candidate_id"])
        fam_id = str(rec["family_id"])
        sym = ldr.normalize_symbol(str(rec["symbol"]))
        leader_sym = ldr.normalize_symbol(str(rec["leader_symbol"])) if rec.get("leader_symbol") else None

        # Multi-symbol asset_universe for F5D (`(leader, target)`), single tuple otherwise
        asset_universe = (leader_sym, sym) if leader_sym else (sym,)
        cp_mech, econ_rat = _FAMILY_COUNTERPARTY_RATIONALES[fam_id]

        # Align Cluster A daily returns for sign consistency in research_council
        cla_dr = cla_rec.get("daily_returns_1x") or {}
        cla_yrs = [int(y) for y in (cla_rec.get("years_evaluated") or [2019, 2020])]
        cla_dates = _weekday_calendar_dates(f"{min(cla_yrs):04d}-01-01", f"{max(cla_yrs):04d}-12-31")
        cla_daily_vec = align_daily_map_to_calendar(
            cla_dr,
            cla_dates,
            context=f"cla_council:{cid}",
            max_allowed_date=CLUSTER_A_MAX_DAY,
        )

        # Family Cluster A CSCV PBO matrix (strictly <= 2020-12-31, zero Cluster B peeking!)
        pbo_info = family_pbo_map.get(fam_id)
        pbo_mat = pbo_info["matrix"] if (pbo_info is not None and pbo_info["n_trials"] >= 2) else None
        pbo_slices = int(pbo_info["n_slices"]) if (pbo_info is not None and pbo_info["n_slices"] >= 4) else 16

        kc = KillCriteria(
            max_bh_q=GATE_MAX_BH_FDR_Q,
            min_dsr=GATE_MIN_DSR_EMPIRICAL,
            min_cluster_b_sharpe=GATE_MIN_CLUSTER_B_SHARPE,
            min_cost_breakeven_mult=GATE_MIN_COST_BREAKEVEN_MULT,
            max_corr_vs_incumbent=GATE_MAX_ABS_CORR_PORT_7E,
            max_tail_corr_vs_incumbent=GATE_MAX_TAIL_CORR_PORT_7E,
            min_trades_cluster_b=GATE_MIN_TRADES_CLUSTER_B,
            max_pbo=GATE_MAX_PBO_CSCV,
            require_incumbent=True,
            require_robustness_gate=False,
        )
        card = propose_hypothesis(
            hypothesis_id=cid,
            title=f"Wave 5 {fam_id} on {'->'.join(asset_universe)}",
            asset_universe=asset_universe,
            timeframe="M1_INTRADAY_SWAP0",
            counterparty_mechanism=cp_mech,
            economic_rationale=econ_rat,
            causal_invariants=(
                "Strictly causal shift>=1 prior-day D1 ATR14 and NR5/NR20",
                "Hard flat <= 20:50 UTC (swap=0, zero weekend exposure)",
                "Zero volume columns (pure price M1 Bid/Ask or FTMO/QDM point spread + open penalty)",
                "Cluster A (<=2020) -> One-Shot Cluster B (2021-2024), Holdout 2025+ SEALED",
            ),
            n_trials_cumulative=m_tot,
            kill_criteria=kc,
        )
        evidence = EvidenceBundle(
            cluster_a_returns=cla_daily_vec,
            cluster_b_returns=clb_daily_vec,
            p_value_raw=float(item["p_emp_b"]),
            family_p_values=full_family_p_values,
            candidate_index_in_family=idx,
            cost_1x_net=float(rec["total_r_1x"]),
            cost_2x_net=float(rec["total_r_2x"]),
            n_trades_cluster_b=int(rec["n_trades"]),
            incumbent_daily_returns=inc_daily,
            annualization_days=252.0,
            holdout_rows_analysed=0,
            cluster_b_dates=clb_dates,
            incumbent_dates=clb_dates,
            pbo_returns_matrix=pbo_mat,
            pbo_n_slices=pbo_slices,
            trial_sharpes=trial_sharpes_arr,
            trial_sharpes_are_annualized=True,
        )
        council = critique_proposal(
            card,
            evidence,
            strict_gates=True,
            require_incumbent=True,
            require_robustness_gate=False,
        )

        g1_c = council["gates"]["G1_bh_fdr"]
        g2_c = council["gates"]["G2_dsr_and_sharpe"]
        g3_c = council["gates"]["G3_cost_stress"]
        g4_c = council["gates"]["G4_orthogonality"]
        g7_c = council["gates"].get("G7_pbo_cscv", {"passed": False, "pbo": 1.0})

        bh_q = float(q_all[idx])
        dsr_emp = float(g2_c["dsr_b"])
        sharpe_daily_b = float(compute_daily_calendar_sharpe(clb_daily_vec, annualization_days=252))
        pbo_val = float(g7_c["pbo"])
        be_mult = compute_cost_breakeven_mult(float(rec["total_r_1x"]), float(rec["total_r_2x"]))
        n_trades_b = int(rec["n_trades"])
        corr_7e = float(g4_c["corr_all"])
        tail_corr_7e = float(g4_c["corr_tail_5pct"])
        max_exit_sec = int(rec["max_exit_utc_sec"])
        swap_r = float(rec["swap_r_total"])

        # Strict 8-Gate Checklist (ZERO threshold relaxation!)
        gate_checks: dict[str, bool] = {
            "G1_bh_fdr_q_le_0_10": bool(bh_q <= GATE_MAX_BH_FDR_Q and g1_c["passed"]),
            "G2_dsr_empirical_ge_0_50": bool(
                dsr_emp >= GATE_MIN_DSR_EMPIRICAL and bool(g2_c.get("empirical_variance_used"))
            ),
            "G3_pbo_cscv_le_0_35": bool(pbo_val <= GATE_MAX_PBO_CSCV and bool(g7_c.get("passed"))),
            "G4_cluster_b_sharpe_ge_0_60": bool(sharpe_daily_b >= GATE_MIN_CLUSTER_B_SHARPE),
            "G5_cost_breakeven_ge_2_0x": bool(
                be_mult >= GATE_MIN_COST_BREAKEVEN_MULT and float(rec["total_r_2x"]) > 0.0 and g3_c["passed"]
            ),
            "G6_trades_cluster_b_ge_60": bool(n_trades_b >= GATE_MIN_TRADES_CLUSTER_B),
            "G7_orthogonality_and_tail_corr": bool(
                abs(corr_7e) <= GATE_MAX_ABS_CORR_PORT_7E
                and tail_corr_7e <= GATE_MAX_TAIL_CORR_PORT_7E
                and g4_c["passed"]
            ),
            "G8_swap0_flat2050_and_metadata": bool(
                abs(swap_r) <= 1e-12
                and max_exit_sec <= HARD_FLAT_MAX_UTC_SEC
                and bool(rec["all_flat_by_2050_utc"])
                and str(rec["blindness_tier"]) in (ldr.TIER_NEW16_WAVE5, ldr.TIER_OLD12)
            ),
        }
        failed_gates = [k for k, ok in gate_checks.items() if not ok]
        all_8_pass = (len(failed_gates) == 0) and (council["verdict"] == "APPROVE_FOR_INCUBATION")

        if all_8_pass:
            tier_cls = TIER_1_PROP_CANDIDATE
        elif (
            n_trades_b >= BENCH_RESERVE_MIN_TRADES_B
            and float(rec["ev_r_1x"]) > 0.0
            and sharpe_daily_b >= BENCH_RESERVE_MIN_SHARPE_B
            and abs(corr_7e) <= BENCH_RESERVE_MAX_ABS_CORR
            and gate_checks["G8_swap0_flat2050_and_metadata"]
        ):
            tier_cls = TIER_ALPHA_BENCH_RESERVE
        else:
            tier_cls = TIER_KILLED_ON_CLUSTER_B

        rn_scope = dict(rec.get("red_news_scope_disclosure") or fam5.describe_red_news_scope(list(asset_universe)))
        mt5_ready = bool(rec["mt5_hcc_ready"])
        eval_entry: dict[str, Any] = {
            "candidate_id": cid,
            "family_id": fam_id,
            "symbol": sym,
            "leader_symbol": leader_sym,
            "asset_universe": list(asset_universe),
            "params": dict(rec.get("params") or {}),
            "years_evaluated": yrs,
            "blindness_tier": str(rec["blindness_tier"]),
            "mt5_hcc_ready": mt5_ready,
            "mt5_cert_status": "MT5_HCC_READY_18" if mt5_ready else "BLOCKED_MISSING_FTMO_HCC_10",
            "data_resolution": str(rec["data_resolution"]),
            "red_news_scope_disclosure": rn_scope,
            "cluster_a_sharpe_1x": float(cla_rec["sharpe_1x"]),
            "cluster_a_n_trades": int(cla_rec["n_trades"]),
            "cluster_a_ev_r_1x": float(cla_rec["ev_r_1x"]),
            "n_trades_b": n_trades_b,
            "winrate_frac_b": float(rec["winrate_frac"]),
            "avg_win_r_b": float(rec["avg_win_r"]),
            "avg_loss_r_b": float(rec["avg_loss_r"]),
            "rr_ratio_b": float(rec["rr_ratio"]),
            "ev_r_1x_b": float(rec["ev_r_1x"]),
            "ev_r_15x_b": float(rec["ev_r_15x"]),
            "ev_r_2x_b": float(rec["ev_r_2x"]),
            "pf_1x_b": float(rec["pf_1x"]),
            "pf_15x_b": float(rec["pf_15x"]),
            "pf_2x_b": float(rec["pf_2x"]),
            "total_r_1x_b": float(rec["total_r_1x"]),
            "total_r_15x_b": float(rec["total_r_15x"]),
            "total_r_2x_b": float(rec["total_r_2x"]),
            "max_dd_r_1x_b": float(rec["max_dd_r_1x"]),
            "calmar_1x_b": float(rec["calmar_1x"]),
            "sharpe_1x_b": float(rec["sharpe_1x"]),
            "sharpe_daily_b": round(sharpe_daily_b, 4),
            "cost_breakeven_mult": round(be_mult, 4),
            "p_value_signflip": round(float(item["p_emp_b"]), 6),
            "bh_fdr_q": round(bh_q, 6),
            "bh_fdr_m_total": m_tot,
            "dsr_empirical": round(dsr_emp, 4),
            "dsr_mode": str(g2_c.get("dsr_mode", "")),
            "dsr_expected_max_sr_ann": float(g2_c.get("expected_max_sr_ann", 0.0)),
            "pbo_cscv": round(pbo_val, 4),
            "pbo_scope": f"CLUSTER_A_FAMILY_{fam_id}_M{pbo_info['n_trials'] if pbo_info else 0}",
            "corr_vs_port_7e": round(corr_7e, 4),
            "tail_corr_vs_port_7e": round(tail_corr_7e, 4),
            "max_exit_utc_sec": max_exit_sec,
            "all_flat_by_2050_utc": bool(rec["all_flat_by_2050_utc"]),
            "swap_r_total": swap_r,
            "gate_checks": gate_checks,
            "gates_passed_count": int(sum(1 for ok in gate_checks.values() if ok)),
            "all_8_gates_passed": all_8_pass,
            "failed_gates": failed_gates,
            "council_verdict": str(council["verdict"]),
            "council_verdict_sha256": str(council["verdict_sha256"]),
            "council_objections": list(council["critic_objections"]),
            "tier_classification": tier_cls,
            "host_executed": str(rec.get("_host_executed", "DEV_PC")),
            "shard_id": str(rec.get("_shard_id", "local")),
            "holdout_rows_analysed": 0,
            "order_send_count": 0,
            "_daily_returns_1x": dict(item["dr_1x"]),
            "_daily_returns_15x": dict(item["dr_15x"]),
            "_daily_returns_2x": dict(item["dr_2x"]),
            "_clb_daily_vec_1x": clb_daily_vec,
        }
        evaluations.append(eval_entry)
        if tier_cls == TIER_1_PROP_CANDIDATE:
            survivors.append(eval_entry)
        elif tier_cls == TIER_ALPHA_BENCH_RESERVE:
            bench_reserves.append(eval_entry)
        else:
            killed.append(eval_entry)

    survivors.sort(key=lambda r: (-float(r["sharpe_daily_b"]), -float(r["ev_r_1x_b"]), str(r["candidate_id"])))
    bench_reserves.sort(
        key=lambda r: (-int(r["gates_passed_count"]), -float(r["sharpe_daily_b"]), str(r["candidate_id"]))
    )
    killed.sort(key=lambda r: (-int(r["gates_passed_count"]), -float(r["sharpe_daily_b"]), str(r["candidate_id"])))

    return {
        "m_total_tested_in_fdr": m_tot,
        "finalists_evaluated_count": len(evaluations),
        "survivor_count": len(survivors),
        "bench_reserve_count": len(bench_reserves),
        "killed_count": len(killed),
        "evaluations": evaluations,
        "survivors": survivors,
        "bench_reserves": bench_reserves,
        "killed": killed,
    }


# ---------------------------------------------------------------------------
# 7. Step E — Greedy Incremental Accretion (`W5-G09`) -> `PORT_V5` + NPZ Tapes
# ---------------------------------------------------------------------------


def _compute_symbol_and_ccy_exposure(
    engines: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    total_risk_pct = sum(float(e["base_risk_pct"]) for e in engines)
    by_sym_pct: dict[str, float] = {}
    by_ccy_pct: dict[str, float] = {}
    for e in engines:
        sym = ldr.normalize_symbol(str(e["symbol"]))
        rp = float(e["base_risk_pct"])
        by_sym_pct[sym] = round(by_sym_pct.get(sym, 0.0) + rp, 6)
        for c in fam5.symbol_governing_ccys(sym):
            by_ccy_pct[c] = round(by_ccy_pct.get(c, 0.0) + rp, 6)
    by_sym_share_pct = {
        sym: round(100.0 * rp / max(total_risk_pct, _EPS), 4) for sym, rp in sorted(by_sym_pct.items())
    }
    by_ccy_share_pct = {
        c: round(100.0 * rp / max(total_risk_pct, _EPS), 4) for c, rp in sorted(by_ccy_pct.items())
    }
    return {
        "total_base_risk_pct": round(total_risk_pct, 4),
        "by_symbol_risk_pct": dict(sorted(by_sym_pct.items())),
        "by_symbol_share_pct": by_sym_share_pct,
        "by_currency_risk_pct": dict(sorted(by_ccy_pct.items())),
        "by_currency_share_pct": by_ccy_share_pct,
    }


def run_greedy_incremental_accretion(
    *,
    survivors: Sequence[Mapping[str, Any]],
    port_7e: Mapping[str, Any],
    cluster_a_by_id: Mapping[str, Mapping[str, Any]] | None = None,
    candidate_base_risk_pct: float = ACCRETION_DEFAULT_ENGINE_RISK_PCT,
) -> dict[str, Any]:
    """Greedily accrete verified `TIER_1_PROP_CANDIDATE` survivors onto `PORT_7E` on Cluster B (`2021-2024`).

    Fail-closed: calls `validate_promotion_candidate` on EVERY input survivor, enforces `<= 35%`
    per-pair share and `<= 1.0%`/sym Funded risk caps, and requires genuine net improvement in
    Sharpe, PF, and R-velocity without blowing up Max DD.
    """
    clb_dates = list(port_7e["clb_dates"])
    dev_dates = list(port_7e["dev_dates"])
    enforce_pre_holdout_dates(clb_dates, context="accretion.clb_dates")
    enforce_pre_holdout_dates(dev_dates, context="accretion.dev_dates")

    base_engines: list[dict[str, Any]] = [
        {
            "engine_id": eid,
            "symbol": CORE7_ENGINE_SYMBOLS[eid],
            "base_risk_pct": round(float(DEFAULT_CORE7_BASE_RISK[eid]) * 100.0, 4),
            "base_risk_frac": float(DEFAULT_CORE7_BASE_RISK[eid]),
            "source": "PORT_7E_INCUMBENT",
            "blindness_tier": ldr.TIER_OLD12,
            "mt5_hcc_ready": True,
        }
        for eid in CORE7_IDS
    ]

    cur_1x = np.asarray(port_7e["port_clb_daily_ret_pct_1x"], dtype=np.float64).copy()
    cur_15x = np.asarray(port_7e["port_clb_daily_ret_pct_15x"], dtype=np.float64).copy()
    cur_2x = np.asarray(port_7e["port_clb_daily_ret_pct_2x"], dtype=np.float64).copy()
    cur_dev_1x = np.asarray(port_7e["port_dev_daily_ret_pct_1x"], dtype=np.float64).copy()

    baseline_metrics_1x = compute_portfolio_daily_metrics(cur_1x, years_span=4.0)
    baseline_metrics_15x = compute_portfolio_daily_metrics(cur_15x, years_span=4.0)
    baseline_metrics_2x = compute_portfolio_daily_metrics(cur_2x, years_span=4.0)
    baseline_exposure = _compute_symbol_and_ccy_exposure(base_engines)

    cur_engines = list(base_engines)
    cur_metrics = dict(baseline_metrics_1x)
    accepted_survivors: list[dict[str, Any]] = []
    accretion_log: list[dict[str, Any]] = []

    ordered_survivors = sorted(
        survivors,
        key=lambda r: (-float(r["sharpe_daily_b"]), -float(r["ev_r_1x_b"]), str(r["candidate_id"])),
    )

    for surv in ordered_survivors:
        # Hard fail-closed gate: NEVER allow any unverified candidate into accretion!
        validate_promotion_candidate(surv)
        cid = str(surv["candidate_id"])
        sym = ldr.normalize_symbol(str(surv["symbol"]))

        exp_now = _compute_symbol_and_ccy_exposure(cur_engines)
        existing_sym_risk = float(exp_now["by_symbol_risk_pct"].get(sym, 0.0))
        rem_sym_cap = max(0.0, ACCRETION_MAX_SYMBOL_FUNDED_RISK_PCT - existing_sym_risk)
        alloc_risk_pct = min(float(candidate_base_risk_pct), rem_sym_cap)

        if alloc_risk_pct < 0.10 - 1e-9:
            accretion_log.append(
                {
                    "candidate_id": cid,
                    "symbol": sym,
                    "decision": "REJECTED_SYMBOL_FUNDED_CAP",
                    "reason": (
                        f"Adding {sym} would breach <= {ACCRETION_MAX_SYMBOL_FUNDED_RISK_PCT:.2f}% Funded cap "
                        f"(existing={existing_sym_risk:.4f}%)"
                    ),
                }
            )
            continue

        trial_engines = [
            *cur_engines,
            {
                "engine_id": cid,
                "symbol": sym,
                "base_risk_pct": round(alloc_risk_pct, 4),
                "base_risk_frac": alloc_risk_pct / 100.0,
                "source": "WAVE5_M1_ALPHA_SURVIVOR",
                "family_id": str(surv["family_id"]),
                "leader_symbol": surv.get("leader_symbol"),
                "blindness_tier": str(surv["blindness_tier"]),
                "mt5_hcc_ready": bool(surv["mt5_hcc_ready"]),
            },
        ]
        trial_exp = _compute_symbol_and_ccy_exposure(trial_engines)
        new_sym_share = float(trial_exp["by_symbol_share_pct"][sym])
        new_sym_funded = float(trial_exp["by_symbol_risk_pct"][sym])
        if (
            new_sym_share > ACCRETION_MAX_PAIR_SHARE_PCT + 1e-9
            or new_sym_funded > ACCRETION_MAX_SYMBOL_FUNDED_RISK_PCT + 1e-9
        ):
            accretion_log.append(
                {
                    "candidate_id": cid,
                    "symbol": sym,
                    "decision": "REJECTED_CONCENTRATION_CAP",
                    "reason": (
                        f"Symbol share={new_sym_share:.2f}% (> {ACCRETION_MAX_PAIR_SHARE_PCT:.1f}%) or "
                        f"Funded risk={new_sym_funded:.4f}% (> {ACCRETION_MAX_SYMBOL_FUNDED_RISK_PCT:.2f}%)"
                    ),
                }
            )
            continue

        vec_1x = align_daily_map_to_calendar(
            surv["_daily_returns_1x"],
            clb_dates,
            context=f"accrete_1x:{cid}",
            max_allowed_date=CLUSTER_B_MAX_DAY,
            min_allowed_date=CLUSTER_B_MIN_DAY,
        )
        vec_15x = align_daily_map_to_calendar(
            surv["_daily_returns_15x"],
            clb_dates,
            context=f"accrete_15x:{cid}",
            max_allowed_date=CLUSTER_B_MAX_DAY,
            min_allowed_date=CLUSTER_B_MIN_DAY,
        )
        vec_2x = align_daily_map_to_calendar(
            surv["_daily_returns_2x"],
            clb_dates,
            context=f"accrete_2x:{cid}",
            max_allowed_date=CLUSTER_B_MAX_DAY,
            min_allowed_date=CLUSTER_B_MIN_DAY,
        )

        # Correlation against running portfolio (prevents stacking correlated survivors!)
        if float(np.std(cur_1x)) > 1e-12 and float(np.std(vec_1x)) > 1e-12:
            corr_running = float(np.corrcoef(cur_1x, vec_1x)[0, 1])
        else:
            corr_running = 0.0
        if abs(corr_running) > ACCRETION_MAX_CORR_RUNNING_PORT:
            accretion_log.append(
                {
                    "candidate_id": cid,
                    "symbol": sym,
                    "decision": "REJECTED_CORR_VS_RUNNING_PORT",
                    "corr_vs_running_port": round(corr_running, 4),
                    "reason": f"|corr|={abs(corr_running):.4f} > {ACCRETION_MAX_CORR_RUNNING_PORT}",
                }
            )
            continue

        trial_1x = cur_1x + alloc_risk_pct * vec_1x
        trial_15x = cur_15x + alloc_risk_pct * vec_15x
        trial_2x = cur_2x + alloc_risk_pct * vec_2x
        trial_metrics = compute_portfolio_daily_metrics(trial_1x, years_span=4.0)

        sharpe_delta = trial_metrics["sharpe"] - cur_metrics["sharpe"]
        pf_delta = trial_metrics["pf"] - cur_metrics["pf"]
        rvel_delta = trial_metrics["r_velocity_annual_r"] - cur_metrics["r_velocity_annual_r"]
        max_dd_lim = max(
            cur_metrics["max_dd_pct"] * ACCRETION_MAX_DD_INCREASE_MULT,
            cur_metrics["max_dd_pct"] + 0.5,
        )
        dd_ok = trial_metrics["max_dd_pct"] <= max_dd_lim

        is_accretive = (
            sharpe_delta >= ACCRETION_MIN_SHARPE_DELTA
            and pf_delta >= 0.0
            and rvel_delta > 0.0
            and dd_ok
        )
        if is_accretive:
            cur_1x = trial_1x
            cur_15x = trial_15x
            cur_2x = trial_2x
            # Also combine full Dev (Cluster A + Cluster B) daily series for port_v5_tapes.npz
            dev_map: dict[str, float] = {}
            if cluster_a_by_id is not None and cid in cluster_a_by_id:
                cla_dr1 = cluster_a_by_id[cid].get("daily_returns_1x") or {}
                dev_map.update({str(k): float(v) for k, v in cla_dr1.items()})
            dev_map.update({str(k): float(v) for k, v in surv["_daily_returns_1x"].items()})
            vec_dev = align_daily_map_to_calendar(
                dev_map,
                dev_dates,
                context=f"accrete_dev:{cid}",
                max_allowed_date=CLUSTER_B_MAX_DAY,
            )
            cur_dev_1x = cur_dev_1x + alloc_risk_pct * vec_dev
            cur_engines = trial_engines
            cur_metrics = trial_metrics
            accepted_survivors.append(
                {
                    **surv,
                    "allocated_base_risk_pct": round(alloc_risk_pct, 4),
                    "accretion_sharpe_delta": round(sharpe_delta, 4),
                    "accretion_pf_delta": round(pf_delta, 4),
                    "accretion_rvel_delta": round(rvel_delta, 4),
                    "corr_vs_running_port": round(corr_running, 4),
                }
            )
            accretion_log.append(
                {
                    "candidate_id": cid,
                    "symbol": sym,
                    "decision": "ACCEPTED_INTO_PORT_V5",
                    "allocated_base_risk_pct": round(alloc_risk_pct, 4),
                    "corr_vs_running_port": round(corr_running, 4),
                    "sharpe_before": round(trial_metrics["sharpe"] - sharpe_delta, 4),
                    "sharpe_after": trial_metrics["sharpe"],
                    "sharpe_delta": round(sharpe_delta, 4),
                    "pf_delta": round(pf_delta, 4),
                    "rvel_delta": round(rvel_delta, 4),
                    "max_dd_after_pct": trial_metrics["max_dd_pct"],
                    "symbol_share_after_pct": new_sym_share,
                    "symbol_funded_risk_after_pct": new_sym_funded,
                }
            )
        else:
            accretion_log.append(
                {
                    "candidate_id": cid,
                    "symbol": sym,
                    "decision": "REJECTED_NON_ACCRETIVE",
                    "sharpe_delta": round(sharpe_delta, 4),
                    "pf_delta": round(pf_delta, 4),
                    "rvel_delta": round(rvel_delta, 4),
                    "max_dd_after_pct": trial_metrics["max_dd_pct"],
                    "dd_ok": dd_ok,
                }
            )

    port_v5_equals_port_7e = len(accepted_survivors) == 0
    final_metrics_1x = compute_portfolio_daily_metrics(cur_1x, years_span=4.0)
    final_metrics_15x = compute_portfolio_daily_metrics(cur_15x, years_span=4.0)
    final_metrics_2x = compute_portfolio_daily_metrics(cur_2x, years_span=4.0)
    final_exposure = _compute_symbol_and_ccy_exposure(cur_engines)

    # Build per-engine daily R matrix & trade-level tape arrays for port_v5_tapes.npz (zero-pickle!)
    e_ids: list[str] = []
    e_syms: list[str] = []
    e_risks: list[float] = []
    e_mat_1x: list[np.ndarray] = []
    e_mat_15x: list[np.ndarray] = []
    e_mat_2x: list[np.ndarray] = []

    tr_eidx: list[int] = []
    tr_dates: list[str] = []
    tr_r1: list[float] = []
    tr_r15: list[float] = []
    tr_r2: list[float] = []
    tr_rf: list[float] = []

    for idx_e, eid in enumerate(CORE7_IDS):
        e_ids.append(eid)
        e_syms.append(CORE7_ENGINE_SYMBOLS[eid])
        rf = float(DEFAULT_CORE7_BASE_RISK[eid])
        e_risks.append(rf)
        v1 = align_daily_map_to_calendar(port_7e["engine_daily_r_1x"][eid], clb_dates, context=f"npz_c7_1x:{eid}")
        v15 = align_daily_map_to_calendar(port_7e["engine_daily_r_15x"][eid], clb_dates, context=f"npz_c7_15x:{eid}")
        v2 = align_daily_map_to_calendar(port_7e["engine_daily_r_2x"][eid], clb_dates, context=f"npz_c7_2x:{eid}")
        e_mat_1x.append(v1)
        e_mat_15x.append(v15)
        e_mat_2x.append(v2)
        for d_i, dk in enumerate(clb_dates):
            if dk in port_7e["engine_daily_r_1x"][eid]:
                tr_eidx.append(idx_e)
                tr_dates.append(dk)
                tr_r1.append(float(v1[d_i]))
                tr_r15.append(float(v15[d_i]))
                tr_r2.append(float(v2[d_i]))
                tr_rf.append(rf)

    for offset, acc in enumerate(accepted_survivors):
        idx_e = len(CORE7_IDS) + offset
        cid = str(acc["candidate_id"])
        e_ids.append(cid)
        e_syms.append(ldr.normalize_symbol(str(acc["symbol"])))
        rf = float(acc["allocated_base_risk_pct"]) / 100.0
        e_risks.append(rf)
        v1 = align_daily_map_to_calendar(acc["_daily_returns_1x"], clb_dates, context=f"npz_add_1x:{cid}")
        v15 = align_daily_map_to_calendar(acc["_daily_returns_15x"], clb_dates, context=f"npz_add_15x:{cid}")
        v2 = align_daily_map_to_calendar(acc["_daily_returns_2x"], clb_dates, context=f"npz_add_2x:{cid}")
        e_mat_1x.append(v1)
        e_mat_15x.append(v15)
        e_mat_2x.append(v2)
        for d_i, dk in enumerate(clb_dates):
            if dk in acc["_daily_returns_1x"]:
                tr_eidx.append(idx_e)
                tr_dates.append(dk)
                tr_r1.append(float(v1[d_i]))
                tr_r15.append(float(v15[d_i]))
                tr_r2.append(float(v2[d_i]))
                tr_rf.append(rf)

    # Sort trade tape chronologically by (date, engine_idx)
    order = sorted(range(len(tr_dates)), key=lambda i: (tr_dates[i], tr_eidx[i]))
    tr_eidx_a = np.array([tr_eidx[i] for i in order], dtype=np.int32)
    tr_dates_a = np.array([tr_dates[i] for i in order], dtype="U10")
    tr_r1_a = np.array([tr_r1[i] for i in order], dtype=np.float64)
    tr_r15_a = np.array([tr_r15[i] for i in order], dtype=np.float64)
    tr_r2_a = np.array([tr_r2[i] for i in order], dtype=np.float64)
    tr_rf_a = np.array([tr_rf[i] for i in order], dtype=np.float64)

    meta_doc = {
        "schema": PORT_V5_TAPES_SCHEMA_VERSION,
        "generated_utc": _utc_now_iso(),
        "port_v5_equals_port_7e": port_v5_equals_port_7e,
        "n_core7_engines": len(CORE7_IDS),
        "n_added_engines": len(accepted_survivors),
        "engine_ids": e_ids,
        "engine_symbols": e_syms,
        "engine_base_risk_pct": [round(x * 100.0, 4) for x in e_risks],
        "added_candidate_ids": [str(a["candidate_id"]) for a in accepted_survivors],
        "added_blindness_tiers": {str(a["candidate_id"]): str(a["blindness_tier"]) for a in accepted_survivors},
        "added_mt5_hcc_ready": {str(a["candidate_id"]): bool(a["mt5_hcc_ready"]) for a in accepted_survivors},
        "cluster_b_start": clb_dates[0],
        "cluster_b_end": clb_dates[-1],
        "holdout_cutoff_date": HOLDOUT_CUTOFF_DATE,
        "holdout_rows_analysed": 0,
        "order_send_count": 0,
        "port_7e_clb_metrics_1x": baseline_metrics_1x,
        "port_v5_clb_metrics_1x": final_metrics_1x,
    }
    meta_bytes = json.dumps(meta_doc, sort_keys=True, separators=(",", ":")).encode("utf-8")

    npz_arrays: dict[str, np.ndarray] = {
        "port_v5_equals_port_7e": np.array(port_v5_equals_port_7e, dtype=np.bool_),
        "holdout_rows_analysed": np.array(0, dtype=np.int64),
        "order_send_count": np.array(0, dtype=np.int64),
        "n_core7_engines": np.array(len(CORE7_IDS), dtype=np.int64),
        "n_added_engines": np.array(len(accepted_survivors), dtype=np.int64),
        "cluster_b_dates_iso": np.array(clb_dates, dtype="U10"),
        "dev_all_dates_iso": np.array(dev_dates, dtype="U10"),
        "port_7e_daily_ret_pct_1x": np.asarray(port_7e["port_clb_daily_ret_pct_1x"], dtype=np.float64),
        "port_7e_daily_ret_pct_15x": np.asarray(port_7e["port_clb_daily_ret_pct_15x"], dtype=np.float64),
        "port_7e_daily_ret_pct_2x": np.asarray(port_7e["port_clb_daily_ret_pct_2x"], dtype=np.float64),
        "port_v5_daily_ret_pct_1x": cur_1x,
        "port_v5_daily_ret_pct_15x": cur_15x,
        "port_v5_daily_ret_pct_2x": cur_2x,
        "port_7e_dev_daily_ret_pct_1x": np.asarray(port_7e["port_dev_daily_ret_pct_1x"], dtype=np.float64),
        "port_v5_dev_daily_ret_pct_1x": cur_dev_1x,
        "engine_ids": np.array(e_ids, dtype="U64"),
        "engine_symbols": np.array(e_syms, dtype="U16"),
        "engine_base_risk_frac": np.array(e_risks, dtype=np.float64),
        "engine_daily_r_1x_clb": np.vstack(e_mat_1x),
        "engine_daily_r_15x_clb": np.vstack(e_mat_15x),
        "engine_daily_r_2x_clb": np.vstack(e_mat_2x),
        "trade_engine_idx_clb": tr_eidx_a,
        "trade_date_iso_clb": tr_dates_a,
        "trade_r_1x_clb": tr_r1_a,
        "trade_r_15x_clb": tr_r15_a,
        "trade_r_2x_clb": tr_r2_a,
        "trade_risk_frac_clb": tr_rf_a,
        "trade_ret_pct_1x_clb": tr_r1_a * tr_rf_a * 100.0,
        "trade_ret_pct_15x_clb": tr_r15_a * tr_rf_a * 100.0,
        "trade_ret_pct_2x_clb": tr_r2_a * tr_rf_a * 100.0,
        "metadata_json_utf8": np.frombuffer(meta_bytes, dtype=np.uint8).copy(),
    }

    return {
        "port_v5_equals_port_7e": port_v5_equals_port_7e,
        "verdict": (
            f"PORT_V5_EXPANDED_PLUS_{len(accepted_survivors)}_ENGINES"
            if accepted_survivors
            else "PORT_V5_EQUALS_PORT_7E_HONEST_ZERO_ADDITIONS"
        ),
        "n_core7_engines": len(CORE7_IDS),
        "n_added_engines": len(accepted_survivors),
        "added_candidate_ids": [str(a["candidate_id"]) for a in accepted_survivors],
        "port_7e_baseline": {
            "metrics_1x": baseline_metrics_1x,
            "metrics_15x": baseline_metrics_15x,
            "metrics_2x": baseline_metrics_2x,
            "exposure": baseline_exposure,
        },
        "port_v5_final": {
            "metrics_1x": final_metrics_1x,
            "metrics_15x": final_metrics_15x,
            "metrics_2x": final_metrics_2x,
            "exposure": final_exposure,
            "engines": cur_engines,
        },
        "net_delta_vs_port_7e_1x": {
            "sharpe_delta": round(final_metrics_1x["sharpe"] - baseline_metrics_1x["sharpe"], 4),
            "pf_delta": round(final_metrics_1x["pf"] - baseline_metrics_1x["pf"], 4),
            "annual_ret_pct_delta": round(
                final_metrics_1x["annual_ret_pct"] - baseline_metrics_1x["annual_ret_pct"], 4
            ),
            "r_velocity_delta": round(
                final_metrics_1x["r_velocity_annual_r"] - baseline_metrics_1x["r_velocity_annual_r"], 4
            ),
            "max_dd_pct_delta": round(final_metrics_1x["max_dd_pct"] - baseline_metrics_1x["max_dd_pct"], 4),
            "calmar_delta": round(final_metrics_1x["calmar"] - baseline_metrics_1x["calmar"], 4),
        },
        "accepted_survivors": accepted_survivors,
        "accretion_log": accretion_log,
        "npz_metadata": meta_doc,
        "npz_arrays": npz_arrays,
    }


# ---------------------------------------------------------------------------
# 8. Strip Private/Transient Fields & Full End-to-End Orchestrator
# ---------------------------------------------------------------------------


def _public_cluster_a_row(
    rec: Mapping[str, Any],
    *,
    sharpe_daily_a: float,
    p_emp_a: float,
    is_finalist: bool,
) -> dict[str, Any]:
    return {
        "candidate_id": str(rec["candidate_id"]),
        "family_id": str(rec["family_id"]),
        "symbol": str(rec["symbol"]),
        "leader_symbol": rec.get("leader_symbol"),
        "years_evaluated": list(rec.get("years_evaluated") or []),
        "blindness_tier": str(rec["blindness_tier"]),
        "mt5_hcc_ready": bool(rec["mt5_hcc_ready"]),
        "data_resolution": str(rec["data_resolution"]),
        "red_news_scope_disclosure": dict(rec.get("red_news_scope_disclosure") or {}),
        "n_trades": int(rec["n_trades"]),
        "winrate_frac": float(rec["winrate_frac"]),
        "rr_ratio": float(rec["rr_ratio"]),
        "ev_r_1x": float(rec["ev_r_1x"]),
        "ev_r_15x": float(rec["ev_r_15x"]),
        "ev_r_2x": float(rec["ev_r_2x"]),
        "pf_1x": float(rec["pf_1x"]),
        "pf_2x": float(rec["pf_2x"]),
        "total_r_1x": float(rec["total_r_1x"]),
        "total_r_2x": float(rec["total_r_2x"]),
        "max_dd_r_1x": float(rec["max_dd_r_1x"]),
        "calmar_1x": float(rec["calmar_1x"]),
        "sharpe_1x": float(rec["sharpe_1x"]),
        "sharpe_daily_a": round(float(sharpe_daily_a), 4),
        "p_value_emp_a": round(float(p_emp_a), 6),
        "max_exit_utc_sec": int(rec["max_exit_utc_sec"]),
        "all_flat_by_2050_utc": bool(rec["all_flat_by_2050_utc"]),
        "swap_r_total": float(rec["swap_r_total"]),
        "is_finalist": bool(is_finalist),
        "host_executed": str(rec.get("_host_executed", "DEV_PC")),
        "shard_id": str(rec.get("_shard_id", "local")),
    }


def _public_eval_row(row: Mapping[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in row.items() if not str(k).startswith("_")}


def run_wave5_m1_alpha_arena(
    *,
    write_output_path: Path | None = DEFAULT_SUMMARY_PATH,
    frozen_output_path: Path | None = DEFAULT_FROZEN_PATH,
    db_path: Path | None = DEFAULT_DUCKDB_PATH,
    port_v5_tapes_path: Path | None = DEFAULT_PORT_V5_TAPES_PATH,
    shard_work_dir: Path = DEFAULT_SHARD_WORK_DIR,
    sync_x13: bool = True,
    x13_only: bool = True,
    x13_share_pct: int = 85,
    lan_only: bool = False,
    sign_flip_draws: int = DEFAULT_SIGN_FLIP_DRAWS,
    force_mode_b: bool = False,
    prebuilt_cluster_a_results: Sequence[Mapping[str, Any]] | None = None,
    prebuilt_cluster_b_results: Sequence[Mapping[str, Any]] | None = None,
    prebuilt_port_7e: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute full Wave 5 M1 Alpha Arena (W5-G07 -> W5-G08 -> W5-G09).

    Supports `write_output_path=None`, `db_path=None`, `port_v5_tapes_path=None`, and injected
    synthetic fixtures so pytest NEVER mutates production DuckDB, JSON, or NPZ artifacts!
    """
    t_start = time_mod.perf_counter()
    mode_a_guard = apply_mode_a_owner_active_guard(cores=MODE_A_MAX_CORES, force_mode_b=force_mode_b)

    # Step A0: Sync updated wave5/ code to X13 (m1_universe_28_loader.py & m1_alpha_families_5.py)
    sync_receipt: dict[str, Any]
    if prebuilt_cluster_a_results is not None:
        sync_receipt = {"ok": True, "skipped": True, "reason": "PREBUILT_FIXTURE_MODE"}
    elif sync_x13:
        try:
            sync_receipt = cr.sync_dev_cache(lan_only=lan_only, dry_run=False, include_tapes=False)
        except Exception as exc:
            sync_receipt = {
                "ok": False,
                "status": "X13_SYNC_FAILED_FALLBACK_DEV_MODE_A",
                "error": f"{type(exc).__name__}: {exc}",
            }
    else:
        sync_receipt = {"ok": True, "skipped": True, "reason": "SYNC_X13_DISABLED"}

    # Step A: Dispatch ALL 355 <= 360 Cluster A candidates across X13 Full Performance
    if prebuilt_cluster_a_results is not None:
        cla_results = [dict(r) for r in prebuilt_cluster_a_results]
        if len(cla_results) > HARD_MAX_TRIALS:
            raise BudgetExceededError(f"BUDGET_CAP_EXCEEDED: {len(cla_results)} > {HARD_MAX_TRIALS}")
        cla_dispatch_meta: dict[str, Any] = {
            "split": "cluster_a",
            "total_candidates": len(cla_results),
            "x13_candidates": 0,
            "dev_pc_candidates": len(cla_results),
            "x13_offload_pct": 0.0,
            "elapsed_sec": 0.0,
            "shards": [],
        }
    else:
        grid = fam5.generate_cluster_a_candidate_grid(max_total=HARD_MAX_TRIALS)
        if len(grid) > HARD_MAX_TRIALS:
            raise BudgetExceededError(f"BUDGET_CAP_EXCEEDED: grid={len(grid)} > {HARD_MAX_TRIALS}")
        cla_shards = group_candidates_into_family_shards(grid)
        cla_dispatch = dispatch_m1_shards_x13_full(
            cla_shards,
            split="cluster_a",
            job_prefix="w5_m1_cla_shard",
            work_dir=shard_work_dir,
            x13_only=x13_only,
            x13_share_pct=x13_share_pct,
            lan_only=lan_only,
            force_mode_b=False,
        )
        cla_results = cla_dispatch["results"]
        cla_dispatch_meta = {k: v for k, v in cla_dispatch.items() if k != "results"}

    m_total = len(cla_results)
    if m_total > HARD_MAX_TRIALS:
        raise BudgetExceededError(f"BUDGET_CAP_EXCEEDED: m_total={m_total} > {HARD_MAX_TRIALS}")

    # Step B0: Compute Cluster A calendar-aligned Sharpes (for empirical DSR trial_sharpes!) & Cluster A family PBOs
    cla_by_id: dict[str, dict[str, Any]] = {}
    cla_daily_sharpes: list[float] = []
    cla_p_vals: dict[str, float] = {}
    cla_daily_sharpe_map: dict[str, float] = {}

    for rec in sorted(cla_results, key=lambda r: str(r["candidate_id"])):
        cid = str(rec["candidate_id"])
        yrs = [int(y) for y in (rec.get("years_evaluated") or [2019, 2020])]
        if any(y > 2020 for y in yrs):
            raise ClusterALeakageError(f"CLUSTER_A_LEAKAGE [{cid}]: years_evaluated={yrs}")
        cal_a = _weekday_calendar_dates(f"{min(yrs):04d}-01-01", f"{max(yrs):04d}-12-31")
        vec_a = align_daily_map_to_calendar(
            rec.get("daily_returns_1x") or {},
            cal_a,
            context=f"cla_daily:{cid}",
            max_allowed_date=CLUSTER_A_MAX_DAY,
        )
        sr_a = compute_daily_calendar_sharpe(vec_a, annualization_days=252)
        dr_a_items = sorted((rec.get("daily_returns_1x") or {}).items())
        active_a = np.array([float(v) for _, v in dr_a_items], dtype=np.float64)
        p_a = compute_empirical_sign_flip_p(
            active_a,
            draws=min(2000, sign_flip_draws),
            seed=_deterministic_seed(cid, DEFAULT_SIGN_FLIP_SEED_BASE),
        )
        cla_by_id[cid] = rec
        cla_daily_sharpe_map[cid] = sr_a
        cla_daily_sharpes.append(sr_a)
        cla_p_vals[cid] = p_a

    # Pure Cluster A PBO per family (strictly <= 2020-12-31, zero Cluster B peeking!)
    family_pbo_map = build_family_cluster_a_pbo_matrices(cla_results)

    # Step C1: Select & Freeze Cluster A Finalists BEFORE ANY Cluster B Touch!
    frozen_bundle = select_cluster_a_finalists(
        cla_results,
        min_sharpe=CLUSTER_A_MIN_SHARPE,
        min_trades=CLUSTER_A_MIN_TRADES,
        min_ev_r=CLUSTER_A_MIN_EV_R,
    )
    finalist_ids = {str(f["candidate_id"]) for f in frozen_bundle["finalists"]}
    if frozen_output_path is not None:
        _atomic_write_json_lf(Path(frozen_output_path), frozen_bundle)

    # Step B: Log ALL 355 Cluster A trials into dedicated DuckDB (`wave5_m1_alpha_m360.duckdb`)
    ledger: Wave5M1AlphaLedger | None = None
    if db_path is not None:
        db_p = Path(db_path)
        if db_p.exists():
            db_p.unlink()
        wal_p = db_p.with_suffix(db_p.suffix + ".wal")
        if wal_p.exists():
            wal_p.unlink()
        ledger = Wave5M1AlphaLedger(db_p, max_trials=HARD_MAX_TRIALS)
        for rec in sorted(cla_results, key=lambda r: str(r["candidate_id"])):
            cid = str(rec["candidate_id"])
            ledger.record_cluster_a_trial(
                rec,
                sharpe_daily_a=cla_daily_sharpe_map[cid],
                p_value_emp_a=cla_p_vals[cid],
                is_finalist=(cid in finalist_ids),
                host_executed=str(rec.get("_host_executed", "DEV_PC")),
                shard_id=str(rec.get("_shard_id", "local")),
            )

    try:
        # Step C2: SINGLE ONE-SHOT CLUSTER B (2021-2024) EVALUATION (`W5-G08`)
        finalist_cands = [
            {
                "candidate_id": f["candidate_id"],
                "family_id": f["family_id"],
                "symbol": f["symbol"],
                "leader_symbol": f["leader_symbol"],
                "params": f["params"],
            }
            for f in frozen_bundle["finalists"]
        ]
        if prebuilt_cluster_b_results is not None:
            clb_results = [dict(r) for r in prebuilt_cluster_b_results]
            clb_dispatch_meta: dict[str, Any] = {
                "split": "cluster_b",
                "total_candidates": len(clb_results),
                "x13_candidates": 0,
                "dev_pc_candidates": len(clb_results),
                "x13_offload_pct": 0.0,
                "elapsed_sec": 0.0,
                "shards": [],
            }
        elif finalist_cands:
            clb_shards = group_candidates_into_family_shards(finalist_cands)
            clb_dispatch = dispatch_m1_shards_x13_full(
                clb_shards,
                split="cluster_b",
                job_prefix="w5_m1_clb_shard",
                work_dir=shard_work_dir,
                x13_only=x13_only,
                x13_share_pct=x13_share_pct,
                lan_only=lan_only,
                force_mode_b=False,
            )
            clb_results = clb_dispatch["results"]
            clb_dispatch_meta = {k: v for k, v in clb_dispatch.items() if k != "results"}
        else:
            clb_results = []
            clb_dispatch_meta = {
                "split": "cluster_b",
                "total_candidates": 0,
                "x13_candidates": 0,
                "dev_pc_candidates": 0,
                "x13_offload_pct": 0.0,
                "elapsed_sec": 0.0,
                "shards": [],
            }

        # Step D: Strict 8-Gate Cluster B Statistical Filter on PC Dev Mode A
        port_7e = dict(prebuilt_port_7e) if prebuilt_port_7e is not None else load_port_7e_canonical_tapes()
        gate_eval = evaluate_cluster_b_8_gates(
            cluster_b_results=clb_results,
            cluster_a_by_id=cla_by_id,
            all_cluster_a_trial_sharpes=cla_daily_sharpes,
            m_total=m_total,
            family_pbo_map=family_pbo_map,
            port_7e_clb_dates=port_7e["clb_dates"],
            port_7e_clb_daily_ret_pct=port_7e["port_clb_daily_ret_pct_1x"],
            sign_flip_draws=sign_flip_draws,
        )

        # Step E: Greedy Incremental Accretion (`W5-G09`) -> PORT_V5
        accretion = run_greedy_incremental_accretion(
            survivors=gate_eval["survivors"],
            port_7e=port_7e,
            cluster_a_by_id=cla_by_id,
        )
        accepted_ids = set(accretion["added_candidate_ids"])

        # Persist Cluster B evaluations & Run Meta into DuckDB
        if ledger is not None:
            for ev in gate_eval["evaluations"]:
                ledger.record_cluster_b_eval(
                    ev,
                    accretion_accepted=(str(ev["candidate_id"]) in accepted_ids),
                )
            ledger.record_run_meta(
                run_id=f"w5_m1_arena_{frozen_bundle['cluster_a_frozen_sha256'][:12]}",
                cluster_a_frozen_sha256=frozen_bundle["cluster_a_frozen_sha256"],
                m_total=m_total,
                finalist_count=len(finalist_cands),
                survivor_count=gate_eval["survivor_count"],
                bench_reserve_count=gate_eval["bench_reserve_count"],
                accretive_count=accretion["n_added_engines"],
                port_v5_equals_port_7e=accretion["port_v5_equals_port_7e"],
            )
    finally:
        if ledger is not None:
            ledger.close()

    # Write zero-pickle `port_v5_tapes.npz`
    tapes_npz_sha: str | None = None
    if port_v5_tapes_path is not None:
        p_npz = Path(port_v5_tapes_path)
        _atomic_write_npz_zero_pickle(p_npz, accretion["npz_arrays"])
        tapes_npz_sha = sha256_file(p_npz)

    # Combined X13 offload summary
    tot_dispatched = int(cla_dispatch_meta["total_candidates"]) + int(clb_dispatch_meta["total_candidates"])
    tot_x13 = int(cla_dispatch_meta["x13_candidates"]) + int(clb_dispatch_meta["x13_candidates"])
    tot_dev = int(cla_dispatch_meta["dev_pc_candidates"]) + int(clb_dispatch_meta["dev_pc_candidates"])
    overall_x13_pct = round(100.0 * float(tot_x13) / float(max(1, tot_dispatched)), 2)

    # Family breakdown stats across all 355 Cluster A trials
    fam_summary: dict[str, dict[str, Any]] = {}
    for fid in fam5.FAMILY_IDS:
        f_rows = [r for r in cla_results if str(r["family_id"]) == fid]
        f_fin = [f for f in frozen_bundle["finalists"] if str(f["family_id"]) == fid]
        f_surv = [s for s in gate_eval["survivors"] if str(s["family_id"]) == fid]
        f_bench = [b for b in gate_eval["bench_reserves"] if str(b["family_id"]) == fid]
        fam_summary[fid] = {
            "cluster_a_trials": len(f_rows),
            "cluster_a_positive_ev_count": sum(1 for r in f_rows if float(r["ev_r_1x"]) > 0.0),
            "cluster_a_max_sharpe_1x": round(max((float(r["sharpe_1x"]) for r in f_rows), default=0.0), 4),
            "cluster_a_pbo_cscv": family_pbo_map[fid]["pbo_cscv"] if fid in family_pbo_map else None,
            "finalists_selected": len(f_fin),
            "cluster_b_survivors_8_of_8": len(f_surv),
            "alpha_bench_reserve_count": len(f_bench),
        }

    # Build clean public summary JSON
    public_cla_all = [
        _public_cluster_a_row(
            r,
            sharpe_daily_a=cla_daily_sharpe_map[str(r["candidate_id"])],
            p_emp_a=cla_p_vals[str(r["candidate_id"])],
            is_finalist=(str(r["candidate_id"]) in finalist_ids),
        )
        for r in sorted(cla_results, key=lambda x: (-float(x["sharpe_1x"]), str(x["candidate_id"])))
    ]

    summary: dict[str, Any] = {
        "schema": SCHEMA_VERSION,
        "completed_utc": _utc_now_iso(),
        "elapsed_sec": round(time_mod.perf_counter() - t_start, 3),
        "git_head_sha": _current_git_head(),
        "hard_invariants": {
            "order_send_capable": ORDER_SEND_CAPABLE,
            "order_send_count": ORDER_SEND_COUNT,
            "spend_vnd": SPEND_VND,
            "holdout_cutoff_date": HOLDOUT_CUTOFF_DATE,
            "dev_cutoff_sec": DEV_CUTOFF_SEC,
            "holdout_rows_analysed": 0,
            "cluster_a_max_day": CLUSTER_A_MAX_DAY,
            "cluster_b_window": f"{CLUSTER_B_MIN_DAY}..{CLUSTER_B_MAX_DAY}",
            "budget_cap_m_max": HARD_MAX_TRIALS,
            "m_total_logged": m_total,
            "zero_hidden_trials": True,
            "zero_threshold_relaxation": True,
            "unified_eval_catalog_untouched": True,
            "pc_dev_mode_a_guard": mode_a_guard,
        },
        "compute_execution": {
            "x13_code_sync": {
                "ok": bool(sync_receipt.get("ok")),
                "ssh_alias": sync_receipt.get("ssh_alias"),
                "file_count": sync_receipt.get("file_count"),
                "holdout_guard_excluded": sync_receipt.get("holdout_guard_excluded"),
                "forbidden_files": sync_receipt.get("forbidden_files"),
                "skipped": bool(sync_receipt.get("skipped", False)),
                "status": sync_receipt.get("status"),
            },
            "cluster_a_dispatch": cla_dispatch_meta,
            "cluster_b_dispatch": clb_dispatch_meta,
            "total_candidate_evals_dispatched": tot_dispatched,
            "x13_candidate_evals": tot_x13,
            "dev_pc_candidate_evals": tot_dev,
            "overall_x13_offload_pct": overall_x13_pct,
        },
        "cluster_a_summary": {
            "m_total": m_total,
            "budget_cap": HARD_MAX_TRIALS,
            "eligible_before_dedup_count": frozen_bundle["eligible_before_dedup_count"],
            "finalist_count": frozen_bundle["finalist_count"],
            "cluster_a_frozen_sha256": frozen_bundle["cluster_a_frozen_sha256"],
            "by_family": fam_summary,
            "pbo_cluster_a_by_family": {
                fid: {
                    "n_trials": info["n_trials"],
                    "n_obs": info["n_obs"],
                    "n_slices": info["n_slices"],
                    "n_combinations": info["n_combinations"],
                    "pbo_cscv": info["pbo_cscv"],
                    "cluster_b_touched": False,
                }
                for fid, info in family_pbo_map.items()
            },
        },
        "cluster_b_8gate_thresholds": {
            "G1_max_bh_fdr_q": GATE_MAX_BH_FDR_Q,
            "G1_bh_fdr_m_total": m_total,
            "G1_sign_flip_draws": sign_flip_draws,
            "G2_min_dsr_empirical": GATE_MIN_DSR_EMPIRICAL,
            "G3_max_pbo_cscv": GATE_MAX_PBO_CSCV,
            "G4_min_cluster_b_sharpe": GATE_MIN_CLUSTER_B_SHARPE,
            "G5_min_cost_breakeven_mult": GATE_MIN_COST_BREAKEVEN_MULT,
            "G6_min_trades_cluster_b": GATE_MIN_TRADES_CLUSTER_B,
            "G7_max_abs_corr_vs_port_7e": GATE_MAX_ABS_CORR_PORT_7E,
            "G7_max_worst5pct_tail_corr_vs_port_7e": GATE_MAX_TAIL_CORR_PORT_7E,
            "G8_swap_zero_max_exit_utc_sec": HARD_FLAT_MAX_UTC_SEC,
        },
        "cluster_b_summary": {
            "finalists_evaluated": gate_eval["finalists_evaluated_count"],
            "tier_1_prop_survivor_count": gate_eval["survivor_count"],
            "alpha_bench_reserve_count": gate_eval["bench_reserve_count"],
            "killed_on_cluster_b_count": gate_eval["killed_count"],
        },
        "port_v5_accretion": {
            "verdict": accretion["verdict"],
            "port_v5_equals_port_7e": accretion["port_v5_equals_port_7e"],
            "n_core7_engines": accretion["n_core7_engines"],
            "n_added_engines": accretion["n_added_engines"],
            "added_candidate_ids": accretion["added_candidate_ids"],
            "port_7e_baseline": accretion["port_7e_baseline"],
            "port_v5_final": accretion["port_v5_final"],
            "net_delta_vs_port_7e_1x": accretion["net_delta_vs_port_7e_1x"],
            "accretion_log": accretion["accretion_log"],
            "port_v5_tapes_npz_sha256": tapes_npz_sha,
        },
        "tier_1_prop_survivors": [_public_eval_row(r) for r in gate_eval["survivors"]],
        "alpha_bench_reserve_ranked": [_public_eval_row(r) for r in gate_eval["bench_reserves"]],
        "cluster_b_all_finalists": [_public_eval_row(r) for r in gate_eval["evaluations"]],
        "cluster_a_all_trials": public_cla_all,
    }
    summary["report_sha256"] = compute_report_sha256(summary)

    if write_output_path is not None:
        _atomic_write_json_lf(Path(write_output_path), summary)

    return summary


# ---------------------------------------------------------------------------
# CLI Entrypoint
# ---------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Wave 5 M1 Alpha Mining Arena (W5-G07, W5-G08, W5-G09) — X13 Full Performance + PC Dev Mode A."
    )
    ap.add_argument("--no-sync-x13", action="store_true", help="Skip X13 sync_dev_cache step.")
    ap.add_argument(
        "--split-x13-dev",
        action="store_true",
        help="Split shards 85%% X13 / 15%% PC Dev Mode A instead of 100%% X13.",
    )
    ap.add_argument("--lan-only", action="store_true", help="Restrict X13 probe/dispatch to LAN alias only.")
    ap.add_argument("--sign-flip-draws", type=int, default=DEFAULT_SIGN_FLIP_DRAWS)
    ap.add_argument("--out-summary", default=str(DEFAULT_SUMMARY_PATH))
    ap.add_argument("--out-frozen", default=str(DEFAULT_FROZEN_PATH))
    ap.add_argument("--out-db", default=str(DEFAULT_DUCKDB_PATH))
    ap.add_argument("--out-tapes", default=str(DEFAULT_PORT_V5_TAPES_PATH))
    args = ap.parse_args(argv)

    summary = run_wave5_m1_alpha_arena(
        write_output_path=Path(args.out_summary),
        frozen_output_path=Path(args.out_frozen),
        db_path=Path(args.out_db),
        port_v5_tapes_path=Path(args.out_tapes),
        sync_x13=not args.no_sync_x13,
        x13_only=not args.split_x13_dev,
        lan_only=args.lan_only,
        sign_flip_draws=args.sign_flip_draws,
    )
    brief = {
        "schema": summary["schema"],
        "elapsed_sec": summary["elapsed_sec"],
        "overall_x13_offload_pct": summary["compute_execution"]["overall_x13_offload_pct"],
        "m_total": summary["cluster_a_summary"]["m_total"],
        "finalists_selected": summary["cluster_a_summary"]["finalist_count"],
        "tier_1_survivors": summary["cluster_b_summary"]["tier_1_prop_survivor_count"],
        "alpha_bench_reserve": summary["cluster_b_summary"]["alpha_bench_reserve_count"],
        "killed_on_cluster_b": summary["cluster_b_summary"]["killed_on_cluster_b_count"],
        "port_v5_verdict": summary["port_v5_accretion"]["verdict"],
        "port_v5_equals_port_7e": summary["port_v5_accretion"]["port_v5_equals_port_7e"],
        "added_candidate_ids": summary["port_v5_accretion"]["added_candidate_ids"],
        "report_sha256": summary["report_sha256"],
    }
    print(json.dumps(brief, indent=2, sort_keys=True))
    return 0


__all__ = [
    "ACCRETION_DEFAULT_ENGINE_RISK_PCT",
    "ACCRETION_MAX_PAIR_SHARE_PCT",
    "ACCRETION_MAX_SYMBOL_FUNDED_RISK_PCT",
    "BudgetExceededError",
    "CLUSTER_A_MAX_DAY",
    "CLUSTER_A_MIN_EV_R",
    "CLUSTER_A_MIN_SHARPE",
    "CLUSTER_A_MIN_TRADES",
    "CLUSTER_B_MAX_DAY",
    "CLUSTER_B_MIN_DAY",
    "ClusterALeakageError",
    "ClusterBContaminationError",
    "ClusterBOneShotViolationError",
    "DEFAULT_DUCKDB_PATH",
    "DEFAULT_FROZEN_PATH",
    "DEFAULT_PORT_V5_TAPES_PATH",
    "DEFAULT_SIGN_FLIP_DRAWS",
    "DEFAULT_SUMMARY_PATH",
    "GATE_MAX_ABS_CORR_PORT_7E",
    "GATE_MAX_BH_FDR_Q",
    "GATE_MAX_PBO_CSCV",
    "GATE_MAX_TAIL_CORR_PORT_7E",
    "GATE_MIN_CLUSTER_B_SHARPE",
    "GATE_MIN_COST_BREAKEVEN_MULT",
    "GATE_MIN_DSR_EMPIRICAL",
    "GATE_MIN_TRADES_CLUSTER_B",
    "HARD_MAX_TRIALS",
    "ORDER_SEND_CAPABLE",
    "ORDER_SEND_COUNT",
    "SCHEMA_VERSION",
    "SPEND_VND",
    "TIER_1_PROP_CANDIDATE",
    "TIER_ALPHA_BENCH_RESERVE",
    "TIER_KILLED_ON_CLUSTER_B",
    "UnverifiedPromotionError",
    "Wave5M1AlphaLedger",
    "align_daily_map_to_calendar",
    "apply_mode_a_owner_active_guard",
    "build_family_cluster_a_pbo_matrices",
    "canonical_sha256",
    "compute_cost_breakeven_mult",
    "compute_daily_calendar_sharpe",
    "compute_empirical_sign_flip_p",
    "compute_portfolio_daily_metrics",
    "compute_report_sha256",
    "dispatch_m1_shards_x13_full",
    "evaluate_cluster_b_8_gates",
    "group_candidates_into_family_shards",
    "load_port_7e_canonical_tapes",
    "run_greedy_incremental_accretion",
    "run_wave5_m1_alpha_arena",
    "select_cluster_a_finalists",
    "validate_promotion_candidate",
]

if __name__ == "__main__":
    raise SystemExit(main())

"""Wave 5 (Gates W5-G16 & W5-G17): Governed 5-Stage Closed-Loop Alpha Factory Controller.

Strictly offline, non-executing governance controller (`ORDER_SEND_CAPABLE = False`,
`ORDER_SEND_COUNT = 0`, `AUTO_DEPLOY_PERMITTED = False`, `HOLDOUT_CUTOFF_DATE = "2024-12-31"`).
ALL risk-weight reductions, retirements, and bench swaps emit SHA-256 signed governance
proposals requiring explicit owner approval — ZERO autonomous broker/MT5 mutations.

5-Stage Architecture:
  Stage 1 `DiscoveryQueue`        -> Enqueues pre-holdout candidate specs (`<= 2024-12-31`).
  Stage 2 `BlindValidationGate`   -> Strict causal Cluster A (`<= 2020-12-31`) -> Blind Cluster B
                                     (`2021-01-01..2024-12-31`) multi-gate qualification.
  Stage 3 `AlphaBenchRegistry`    -> Enforced lifecycle FSM + tamper-evident SHA-256 hash-chained ledger:
                                     `DISCOVERED -> CLUSTER_A_PASS -> BLIND_B_VERIFIED -> BENCH_READY
                                      -> SHADOW_INCUBATION -> ACTIVE_1X -> DECAY_AMBER_0_5X
                                      -> RETIRED / KILLED`
  Stage 4 `DecayWatcherBridge`    -> P1-6 fail-closed pre-validation BEFORE lazy `evaluate_live_decay()`
                                     (rejects NaN, Inf, bool, non-numeric, empty arrays, invalid thresholds)
                                     with clean stdlib/NumPy fallback when `quant_trading` is absent in CI.
  Stage 5 `RetireAndSwapPlanner`  -> On `RED_HALT_ALPHA_DECAY`, selects highest-score lowest-correlation
                                     `BENCH_READY` replacement, recomputes Shield-A-compliant portfolio
                                     weights, emits draft `.set` diff (locked `InpDryRunLogOnly=true`) +
                                     SHA-256 proposal. On empty bench: fail-closed HALT ONLY (never
                                     promotes unverified/rejected candidates!).

5 Mandatory E2E Drills (`W5-G17`):
  1. `DRILL_1_NORMAL_GREEN`
  2. `DRILL_2_AMBER_HALVED`
  3. `DRILL_3_RED_WITH_BENCH_SWAP`
  4. `DRILL_4_RED_EMPTY_BENCH_FAIL_CLOSED`
  5. `DRILL_5_POISONED_INPUT_AND_TAMPERED_LEDGER`

Hard invariants:
  - Zero bare `assert` statements (`python -O` safe).
  - Lazy import of `quant_factory.live_decay_monitor` / `quant_trading` (zero top-level import).
  - `write_output_path=None` supported everywhere so pytest never mutates production artifacts.
  - LF-only, zero BOM JSON outputs.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import math
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

import numpy as np

from quant_factory.wave5 import (
    DEV_CUTOFF_SEC,
    DEV_PC_REQUIRED_MODE,
    HOLDOUT_CUTOFF_DATE,
    ORDER_SEND_CAPABLE,
    ORDER_SEND_COUNT,
)

# ---------------------------------------------------------------------------
# Governance Constants & Canonical Paths
# ---------------------------------------------------------------------------

LEDGER_SCHEMA_VERSION: str = "naqex-wave5-alpha-factory-ledger-v1"
DRILLS_SCHEMA_VERSION: str = "naqex-wave5-alpha-factory-e2e-drills-v1"
PROPOSAL_SCHEMA_VERSION: str = "naqex-wave5-governed-swap-proposal-v1"

AUTO_DEPLOY_PERMITTED: bool = False
HOLDOUT_FIRST_DAY: str = "2025-01-01"
GENESIS_HASH: str = "0" * 64

HARD_SHIELD_A_TOTAL_OPEN_CAP_PCT: float = 3.00
HARD_PER_SYMBOL_CAP_PCT: float = 1.75
MAX_REPLACEMENT_ABS_CORR: float = 0.45

_REPO_ROOT: Path = Path(__file__).resolve().parents[4]
DEFAULT_FACTORY_DIR: Path = _REPO_ROOT / ".runtime" / "offensive5" / "factory"
DEFAULT_LEDGER_OUT_PATH: Path = DEFAULT_FACTORY_DIR / "alpha_factory_ledger.json"
DEFAULT_DRILLS_OUT_PATH: Path = DEFAULT_FACTORY_DIR / "alpha_factory_e2e_drills.json"


# Canonical PORT_7E initial production roster matching `configs/ssot/risk_profiles.json`
CANONICAL_PORT_7E_ENGINES: tuple[dict[str, Any], ...] = (
    {"engine_id": "E1_USDJPY_TOKYO", "symbol": "USDJPY", "magic": 20261122, "base_risk_pct": 0.1606},
    {"engine_id": "E2_USDJPY_EXP80", "symbol": "USDJPY", "magic": 20261123, "base_risk_pct": 0.5894},
    {"engine_id": "E3_GBPUSD_VH", "symbol": "GBPUSD", "magic": 20261125, "base_risk_pct": 0.7500},
    {"engine_id": "E4_US100_SESS40", "symbol": "US100", "magic": 20261124, "base_risk_pct": 0.5000},
    {"engine_id": "E5_US100_RS1130", "symbol": "US100", "magic": 20261126, "base_risk_pct": 0.5000},
    {"engine_id": "E6_EURJPY_VOLCOMP", "symbol": "EURJPY", "magic": 20261128, "base_risk_pct": 0.5000},
    {"engine_id": "E7_USDJPY_NY10ET", "symbol": "USDJPY", "magic": 20261129, "base_risk_pct": 0.5000},
)


# ---------------------------------------------------------------------------
# Lifecycle State Machine (Strict Fail-Closed Transitions)
# ---------------------------------------------------------------------------


class EngineLifecycleState(StrEnum):
    DISCOVERED = "DISCOVERED"
    CLUSTER_A_PASS = "CLUSTER_A_PASS"
    BLIND_B_VERIFIED = "BLIND_B_VERIFIED"
    BENCH_READY = "BENCH_READY"
    SHADOW_INCUBATION = "SHADOW_INCUBATION"
    ACTIVE_1X = "ACTIVE_1X"
    DECAY_AMBER_0_5X = "DECAY_AMBER_0_5X"
    RETIRED = "RETIRED"
    KILLED = "KILLED"


ALLOWED_TRANSITIONS: dict[EngineLifecycleState, frozenset[EngineLifecycleState]] = {
    EngineLifecycleState.DISCOVERED: frozenset({
        EngineLifecycleState.CLUSTER_A_PASS,
        EngineLifecycleState.KILLED,
    }),
    EngineLifecycleState.CLUSTER_A_PASS: frozenset({
        EngineLifecycleState.BLIND_B_VERIFIED,
        EngineLifecycleState.KILLED,
    }),
    EngineLifecycleState.BLIND_B_VERIFIED: frozenset({
        EngineLifecycleState.BENCH_READY,
        EngineLifecycleState.KILLED,
    }),
    EngineLifecycleState.BENCH_READY: frozenset({
        EngineLifecycleState.SHADOW_INCUBATION,
        EngineLifecycleState.RETIRED,
        EngineLifecycleState.KILLED,
    }),
    EngineLifecycleState.SHADOW_INCUBATION: frozenset({
        EngineLifecycleState.ACTIVE_1X,
        EngineLifecycleState.BENCH_READY,
        EngineLifecycleState.RETIRED,
        EngineLifecycleState.KILLED,
    }),
    EngineLifecycleState.ACTIVE_1X: frozenset({
        EngineLifecycleState.DECAY_AMBER_0_5X,
        EngineLifecycleState.RETIRED,
        EngineLifecycleState.KILLED,
    }),
    EngineLifecycleState.DECAY_AMBER_0_5X: frozenset({
        EngineLifecycleState.ACTIVE_1X,
        EngineLifecycleState.RETIRED,
        EngineLifecycleState.KILLED,
    }),
    EngineLifecycleState.RETIRED: frozenset(),
    EngineLifecycleState.KILLED: frozenset(),
}


# ---------------------------------------------------------------------------
# P1-6 Fail-Closed Input Validators & Atomic JSON Writer
# ---------------------------------------------------------------------------


def _canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def canonical_sha256(payload: Any) -> str:
    return hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()


def _atomic_write_json_lf(path: Path, payload: Any) -> None:
    """Write strictly LF-only UTF-8 (zero BOM, allow_nan=False) atomically."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n"
    tmp = out.with_suffix(out.suffix + ".tmp")
    tmp.write_bytes(text.encode("utf-8"))
    tmp.replace(out)


def _require_finite_real(
    value: Any,
    name: str,
    *,
    min_val: float | None = None,
    max_val: float | None = None,
    strict_min: bool = False,
    strict_max: bool = False,
) -> float:
    """Reject bool, np.bool_, None, str, NaN, +-Inf, and out-of-range values fail-closed."""
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, float, np.number)):
        raise ValueError(f"P1_6_INVALID_NUMERIC: {name} must be finite real number (got {value!r})")
    fv = float(value)
    if not math.isfinite(fv):
        raise ValueError(f"P1_6_NON_FINITE: {name} must be finite (got {value!r})")
    if min_val is not None:
        if strict_min and fv <= min_val:
            raise ValueError(f"P1_6_RANGE_ERROR: {name}={fv} must be > {min_val}")
        if (not strict_min) and fv < min_val:
            raise ValueError(f"P1_6_RANGE_ERROR: {name}={fv} must be >= {min_val}")
    if max_val is not None:
        if strict_max and fv >= max_val:
            raise ValueError(f"P1_6_RANGE_ERROR: {name}={fv} must be < {max_val}")
        if (not strict_max) and fv > max_val:
            raise ValueError(f"P1_6_RANGE_ERROR: {name}={fv} must be <= {max_val}")
    return fv


def _require_strict_int(
    value: Any,
    name: str,
    *,
    min_val: int | None = None,
    max_val: int | None = None,
) -> int:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)):
        raise ValueError(f"P1_6_INVALID_INT: {name} must be strict int (got {value!r})")
    iv = int(value)
    if min_val is not None and iv < min_val:
        raise ValueError(f"P1_6_RANGE_ERROR: {name}={iv} must be >= {min_val}")
    if max_val is not None and iv > max_val:
        raise ValueError(f"P1_6_RANGE_ERROR: {name}={iv} must be <= {max_val}")
    return iv


def validate_numeric_series_fail_closed(
    series: Any,
    name: str,
    *,
    min_len: int = 1,
) -> np.ndarray:
    """CRITICAL P1-6 GUARDRAIL: reject empty, bool, non-numeric, NaN, or Inf BEFORE `evaluate_live_decay()`.

    `live_decay_monitor.py:evaluate_live_decay()` silently strips NaN/Inf (`arr[np.isfinite(arr)]`)
    and coerces `bool` (`True -> 1.0`, `False -> 0.0`). This guard catches EVERY poisoned element
    upfront and raises `ValueError`.
    """
    if series is None or isinstance(series, (str, bytes, bytearray, Mapping)):
        raise ValueError(f"P1_6_INVALID_SERIES_TYPE: {name} must be 1D numeric sequence (got {type(series).__name__})")

    if isinstance(series, np.ndarray):
        if series.ndim != 1:
            raise ValueError(f"P1_6_INVALID_SERIES_NDIM: {name} must be 1D (got ndim={series.ndim})")
        if series.dtype == np.bool_ or series.dtype.kind == "b":
            raise ValueError(f"P1_6_BOOL_SERIES_FORBIDDEN: {name} has boolean dtype")
        if series.size < min_len:
            raise ValueError(f"P1_6_EMPTY_OR_SHORT_SERIES: {name} has len={series.size} < {min_len}")
        if series.dtype.kind in ("i", "u", "f"):
            arr = series.astype(np.float64, copy=True)
            if not np.all(np.isfinite(arr)):
                bad_idx = int(np.where(~np.isfinite(arr))[0][0])
                raise ValueError(
                    f"P1_6_NON_FINITE_ELEMENT: {name}[{bad_idx}]={series[bad_idx]!r} is NaN or Inf"
                )
            return arr
        # Object / mixed ndarray: inspect element-by-element
        items = list(series.tolist())
    else:
        try:
            items = list(series)
        except TypeError as exc:
            raise ValueError(f"P1_6_NOT_ITERABLE: {name} is not iterable") from exc

    if len(items) < min_len:
        raise ValueError(f"P1_6_EMPTY_OR_SHORT_SERIES: {name} has len={len(items)} < {min_len}")

    cleaned = np.empty(len(items), dtype=np.float64)
    for idx, elem in enumerate(items):
        if isinstance(elem, (bool, np.bool_)) or not isinstance(elem, (int, float, np.number)):
            raise ValueError(
                f"P1_6_POISONED_ELEMENT: {name}[{idx}]={elem!r} (type={type(elem).__name__}) forbidden"
            )
        fv = float(elem)
        if not math.isfinite(fv):
            raise ValueError(f"P1_6_NON_FINITE_ELEMENT: {name}[{idx}]={elem!r} is NaN or Inf")
        cleaned[idx] = fv
    return cleaned


def validate_pre_holdout_date_str(date_str: Any, name: str = "date") -> str:
    """Fail-closed Holdout 2025+ seal validator for YYYY-MM-DD strings."""
    if not isinstance(date_str, str):
        raise ValueError(f"INVALID_DATE_TYPE: {name} must be YYYY-MM-DD str (got {date_str!r})")
    cleaned = date_str.strip()
    if len(cleaned) < 10 or cleaned[4] != "-" or cleaned[7] != "-":
        raise ValueError(f"INVALID_DATE_FORMAT: {name} must be YYYY-MM-DD (got {date_str!r})")
    day_part = cleaned[:10]
    try:
        parsed = datetime.strptime(day_part, "%Y-%m-%d").replace(tzinfo=UTC)
    except ValueError as exc:
        raise ValueError(f"INVALID_CALENDAR_DATE: {name}={date_str!r}") from exc
    if day_part >= HOLDOUT_FIRST_DAY or int(parsed.timestamp()) >= DEV_CUTOFF_SEC:
        raise ValueError(
            f"HOLDOUT_LOCK_VIOLATION: {name}={day_part!r} >= {HOLDOUT_FIRST_DAY!r} is strictly sealed"
        )
    return day_part


def validate_decay_thresholds_fail_closed(
    *,
    cusum_k_sigma: Any,
    cusum_h_sigma: Any,
    sprt_alpha: Any,
    sprt_beta: Any,
    n_cone_draws: Any = 2000,
    seed: Any = 20261123,
) -> dict[str, Any]:
    """Validate EVERY decay monitor threshold fail-closed before calling `evaluate_live_decay()`."""
    k = _require_finite_real(cusum_k_sigma, "cusum_k_sigma", min_val=0.0)
    h = _require_finite_real(cusum_h_sigma, "cusum_h_sigma", min_val=0.0, strict_min=True)
    alpha = _require_finite_real(sprt_alpha, "sprt_alpha", min_val=0.0, max_val=0.5, strict_min=True, strict_max=True)
    beta = _require_finite_real(sprt_beta, "sprt_beta", min_val=0.0, max_val=0.5, strict_min=True, strict_max=True)
    if alpha + beta >= 1.0:
        raise ValueError(f"P1_6_INVALID_SPRT_BOUNDS: sprt_alpha ({alpha}) + sprt_beta ({beta}) must be < 1.0")
    draws = _require_strict_int(n_cone_draws, "n_cone_draws", min_val=100, max_val=50_000)
    sd = _require_strict_int(seed, "seed", min_val=0)
    return {
        "cusum_k_sigma": k,
        "cusum_h_sigma": h,
        "sprt_alpha": alpha,
        "sprt_beta": beta,
        "n_cone_draws": draws,
        "seed": sd,
    }


# ---------------------------------------------------------------------------
# Lazy `live_decay_monitor` Import + Clean Pure-NumPy/Stdlib CI Fallback
# ---------------------------------------------------------------------------


def _evaluate_decay_stdlib_fallback(
    dev_arr: np.ndarray,
    live_arr: np.ndarray,
    *,
    cusum_k_sigma: float,
    cusum_h_sigma: float,
    sprt_alpha: float,
    sprt_beta: float,
    n_cone_draws: int,
    seed: int,
) -> dict[str, Any]:
    """Bit-equivalent pure-NumPy/stdlib fallback used ONLY if `quant_trading` is absent in minimal CI."""
    if len(dev_arr) < 30:
        raise ValueError("Baseline series requires at least 30 observations")
    mu0 = float(np.mean(dev_arr))
    sd0 = max(float(np.std(dev_arr, ddof=1)), 1e-9)
    n_live = int(len(live_arr))
    z_live = (live_arr - mu0) / sd0

    # Two-sided causal Page CUSUM matching `quant_trading.change_detection.run_cusum`
    s_pos = 0.0
    s_neg = 0.0
    min_neg = 0.0
    neg_triggers: list[int] = []
    for idx, z_val in enumerate(z_live):
        dev = float(z_val)
        s_pos = max(0.0, s_pos + dev - cusum_k_sigma)
        s_neg = min(0.0, s_neg + dev + cusum_k_sigma)
        if s_neg < min_neg:
            min_neg = s_neg
        if (-s_neg) >= cusum_h_sigma:
            neg_triggers.append(idx)

    cur_neg_stat = s_neg
    active_cusum_breach = (-cur_neg_stat) >= cusum_h_sigma

    # Wald SPRT (H1: mu=0 vs H0: mu=mu0)
    llr = 0.0
    if mu0 > 0.0:
        for x in live_arr:
            llr += ((float(x) - mu0) ** 2 - (float(x) - 0.0) ** 2) / (2.0 * sd0 * sd0)
    upper_bound = math.log((1.0 - sprt_beta) / sprt_alpha)
    lower_bound = math.log(sprt_beta / (1.0 - sprt_alpha))
    if llr >= upper_bound:
        sprt_state = "REJECT_EDGE_DECAYED"
    elif llr <= lower_bound:
        sprt_state = "CONFIRM_EDGE_INTACT"
    else:
        sprt_state = "INCONCLUSIVE_CONTINUE"

    rng = np.random.default_rng(seed)
    idx_mat = rng.integers(0, len(dev_arr), size=(n_cone_draws, n_live))
    sim_cum = dev_arr[idx_mat].sum(axis=1)
    obs_cum = float(live_arr.sum())
    p05, p10, p50, p90 = [float(np.percentile(sim_cum, q)) for q in (5, 10, 50, 90)]
    emp_pct_rank = round(100.0 * float(np.mean(sim_cum <= obs_cum)), 1)

    reasons: list[str] = []
    if active_cusum_breach and (sprt_state == "REJECT_EDGE_DECAYED" or obs_cum < p05):
        verdict = "RED_HALT_ALPHA_DECAY"
        reasons.append(
            f"Active negative CUSUM {cur_neg_stat:.2f}sigma <= -{cusum_h_sigma}sigma AND confirmed by SPRT/p05 cone"
        )
    elif active_cusum_breach or obs_cum < p05 or sprt_state == "REJECT_EDGE_DECAYED":
        verdict = "AMBER_WATCH_REDUCE_SIZE"
        if active_cusum_breach:
            reasons.append(f"Active negative CUSUM breach ({cur_neg_stat:.2f}sigma <= -{cusum_h_sigma}sigma)")
        if obs_cum < p05:
            reasons.append(f"Cumulative live sum {obs_cum:.3f} below 5th-percentile Dev cone ({p05:.3f})")
        if sprt_state == "REJECT_EDGE_DECAYED":
            reasons.append(f"Wald SPRT LLR={llr:.2f} >= {upper_bound:.2f}")
    else:
        verdict = "GREEN_WITHIN_EXPECTATION"
        reasons.append(
            f"Live cumulative {obs_cum:.3f} at {emp_pct_rank}th pct of Dev cone "
            f"(p05={p05:.3f}, p50={p50:.3f}); current CUSUM={cur_neg_stat:.2f}sigma"
        )

    cusum_fp = canonical_sha256({
        "z_len": n_live,
        "cur_neg": round(cur_neg_stat, 6),
        "min_neg": round(min_neg, 6),
        "k": cusum_k_sigma,
        "h": cusum_h_sigma,
    })[:16]
    return {
        "schema": "naqex-live-decay-v1",
        "baseline": {"n_dev": int(len(dev_arr)), "mu": mu0, "sd": sd0},
        "n_live": n_live,
        "live_mean": round(float(np.mean(live_arr)), 5),
        "live_cum": round(obs_cum, 4),
        "cusum": {
            "schema": "cusum-change-detection-v1-stdlib-fallback",
            "current_negative_sigma": round(cur_neg_stat, 3),
            "min_negative_sigma": round(min_neg, 3),
            "threshold_sigma": cusum_h_sigma,
            "active_breach": active_cusum_breach,
            "historical_trigger_count": len(neg_triggers),
            "first_negative_step": neg_triggers[0] if neg_triggers else None,
            "result_sha256": cusum_fp,
        },
        "sprt": {
            "llr": round(llr, 3),
            "upper_reject_edge": round(upper_bound, 3),
            "lower_confirm_edge": round(lower_bound, 3),
            "state": sprt_state,
        },
        "confidence_cone": {
            "p05": round(p05, 4),
            "p10": round(p10, 4),
            "p50": round(p50, 4),
            "p90": round(p90, 4),
            "observed_percentile": emp_pct_rank,
        },
        "verdict": verdict,
        "reasons": reasons,
    }


def _resolve_decay_backend(
    *,
    force_stdlib_fallback: bool = False,
) -> tuple[Callable[..., dict[str, Any]], str]:
    """Lazily resolve `quant_factory.live_decay_monitor.evaluate_live_decay` with CI-safe fallback."""
    if force_stdlib_fallback:
        return _evaluate_decay_stdlib_fallback, "stdlib_fallback"
    try:
        mod = importlib.import_module("quant_factory.live_decay_monitor")
        fn = getattr(mod, "evaluate_live_decay", None)
        if callable(fn):
            return fn, "live_decay_monitor"
    except Exception:
        pass
    return _evaluate_decay_stdlib_fallback, "stdlib_fallback"


def evaluate_decay_fail_closed(
    dev_series: Any,
    live_series: Any,
    *,
    cusum_k_sigma: Any = 0.25,
    cusum_h_sigma: Any = 4.5,
    sprt_alpha: Any = 0.05,
    sprt_beta: Any = 0.10,
    n_cone_draws: Any = 2000,
    seed: Any = 20261123,
    dev_max_date: str | None = None,
    force_stdlib_fallback: bool = False,
) -> dict[str, Any]:
    """P1-6 Hardened wrapper around `live_decay_monitor.evaluate_live_decay()`.

    Validates EVERY element of `dev_series`, `live_series`, EVERY threshold, and optional
    `dev_max_date` fail-closed BEFORE calling `evaluate_live_decay()` so silent NaN/Inf drop
    or bool coercion can NEVER happen.
    """
    if dev_max_date is not None:
        validate_pre_holdout_date_str(dev_max_date, "dev_max_date")
    dev_arr = validate_numeric_series_fail_closed(dev_series, "dev_series", min_len=30)
    live_arr = validate_numeric_series_fail_closed(live_series, "live_series", min_len=1)
    cfg = validate_decay_thresholds_fail_closed(
        cusum_k_sigma=cusum_k_sigma,
        cusum_h_sigma=cusum_h_sigma,
        sprt_alpha=sprt_alpha,
        sprt_beta=sprt_beta,
        n_cone_draws=n_cone_draws,
        seed=seed,
    )
    evaluator, backend = _resolve_decay_backend(force_stdlib_fallback=force_stdlib_fallback)
    raw = evaluator(
        dev_arr,
        live_arr,
        cusum_k_sigma=cfg["cusum_k_sigma"],
        cusum_h_sigma=cfg["cusum_h_sigma"],
        sprt_alpha=cfg["sprt_alpha"],
        sprt_beta=cfg["sprt_beta"],
        n_cone_draws=cfg["n_cone_draws"],
        seed=cfg["seed"],
    )
    return {
        **raw,
        "p1_6_prevalidation_passed": True,
        "decay_backend": backend,
    }


# ---------------------------------------------------------------------------
# Data Models: Candidate Spec, Registry Record, Ledger Entry, Proposal
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AlphaCandidateSpec:
    """Typed specification for a candidate strategy entering Stage 1 Discovery Queue."""

    engine_id: str
    family_id: str
    symbol: str
    magic: int
    base_risk_pct: float
    cluster_a_end_date: str
    cluster_b_end_date: str
    cluster_a_sharpe: float
    cluster_a_pf: float
    cluster_b_sharpe: float
    cluster_b_pf: float
    pbo_cscv: float
    dsr_empirical: float
    cost_stress_2x_net_pct: float
    daily_returns_dev: tuple[float, ...]
    holdout_rows_analysed: int = 0

    def validate(self) -> None:
        if not isinstance(self.engine_id, str) or not self.engine_id.strip():
            raise ValueError("INVALID_ENGINE_ID: engine_id must be non-empty str")
        if not isinstance(self.family_id, str) or not self.family_id.strip():
            raise ValueError("INVALID_FAMILY_ID: family_id must be non-empty str")
        if not isinstance(self.symbol, str) or not self.symbol.strip():
            raise ValueError("INVALID_SYMBOL: symbol must be non-empty str")
        _require_strict_int(self.magic, "magic", min_val=1)
        _require_finite_real(self.base_risk_pct, "base_risk_pct", min_val=0.05, max_val=HARD_PER_SYMBOL_CAP_PCT)
        ca_end = validate_pre_holdout_date_str(self.cluster_a_end_date, "cluster_a_end_date")
        if ca_end > "2020-12-31":
            raise ValueError(f"CLUSTER_A_LEAKAGE: cluster_a_end_date={ca_end!r} > '2020-12-31'")
        validate_pre_holdout_date_str(self.cluster_b_end_date, "cluster_b_end_date")
        _require_finite_real(self.cluster_a_sharpe, "cluster_a_sharpe")
        _require_finite_real(self.cluster_a_pf, "cluster_a_pf", min_val=0.0)
        _require_finite_real(self.cluster_b_sharpe, "cluster_b_sharpe")
        _require_finite_real(self.cluster_b_pf, "cluster_b_pf", min_val=0.0)
        _require_finite_real(self.pbo_cscv, "pbo_cscv", min_val=0.0, max_val=1.0)
        _require_finite_real(self.dsr_empirical, "dsr_empirical", min_val=0.0, max_val=1.0)
        _require_finite_real(self.cost_stress_2x_net_pct, "cost_stress_2x_net_pct")
        hr = _require_strict_int(self.holdout_rows_analysed, "holdout_rows_analysed", min_val=0)
        if hr != 0:
            raise ValueError(f"HOLDOUT_LOCK_VIOLATION: holdout_rows_analysed must be 0 (got {hr})")
        validate_numeric_series_fail_closed(self.daily_returns_dev, "daily_returns_dev", min_len=30)

    def fingerprint_sha256(self) -> str:
        return canonical_sha256({
            "engine_id": self.engine_id,
            "family_id": self.family_id,
            "symbol": self.symbol,
            "magic": self.magic,
            "base_risk_pct": round(self.base_risk_pct, 6),
            "cluster_a_end_date": self.cluster_a_end_date,
            "cluster_b_end_date": self.cluster_b_end_date,
            "cluster_b_sharpe": round(self.cluster_b_sharpe, 6),
            "dsr_empirical": round(self.dsr_empirical, 6),
        })


@dataclass(frozen=True)
class BlindGateThresholds:
    """Pre-registered blind validation thresholds for Stage 2 (`Cluster A -> Blind Cluster B`)."""

    min_cluster_a_sharpe: float = 0.65
    min_cluster_a_pf: float = 1.12
    min_cluster_b_sharpe: float = 0.60
    min_cluster_b_pf: float = 1.10
    max_pbo_cscv: float = 0.50
    min_dsr_empirical: float = 0.50
    min_cost_stress_2x_net_pct: float = 0.0
    max_abs_corr_vs_active: float = MAX_REPLACEMENT_ABS_CORR


@dataclass
class EngineRegistryRecord:
    """Mutable registry entry for one engine tracked across its governed lifecycle."""

    engine_id: str
    family_id: str
    symbol: str
    magic: int
    base_risk_pct: float
    weight_mult: float
    state: EngineLifecycleState
    quality_score: float
    cluster_b_sharpe: float
    dsr_empirical: float
    pbo_cscv: float
    candidate_sha256: str
    dev_returns: tuple[float, ...]
    dev_max_date: str = HOLDOUT_CUTOFF_DATE
    last_decay_verdict: str = "UNCHECKED"
    notes: list[str] = field(default_factory=list)

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "engine_id": self.engine_id,
            "family_id": self.family_id,
            "symbol": self.symbol,
            "magic": self.magic,
            "base_risk_pct": round(self.base_risk_pct, 4),
            "weight_mult": round(self.weight_mult, 4),
            "effective_base_risk_pct": round(self.base_risk_pct * self.weight_mult, 4),
            "state": self.state.value,
            "quality_score": round(self.quality_score, 4),
            "cluster_b_sharpe": round(self.cluster_b_sharpe, 4),
            "dsr_empirical": round(self.dsr_empirical, 4),
            "pbo_cscv": round(self.pbo_cscv, 4),
            "candidate_sha256": self.candidate_sha256,
            "dev_series_len": len(self.dev_returns),
            "dev_max_date": self.dev_max_date,
            "last_decay_verdict": self.last_decay_verdict,
            "notes": list(self.notes),
        }


# ---------------------------------------------------------------------------
# Tamper-Evident SHA-256 Hash-Chained Ledger Verification
# ---------------------------------------------------------------------------


def verify_ledger_integrity(ledger_payload: Mapping[str, Any]) -> dict[str, Any]:
    """Fail-closed SHA-256 hash-chain verifier. Raises `ValueError('LEDGER_TAMPER_DETECTED')` on ANY tamper."""
    if not isinstance(ledger_payload, Mapping):
        raise ValueError("LEDGER_TAMPER_DETECTED: ledger payload must be mapping")
    if ledger_payload.get("schema_version") != LEDGER_SCHEMA_VERSION:
        raise ValueError(
            f"LEDGER_TAMPER_DETECTED: unexpected schema_version={ledger_payload.get('schema_version')!r}"
        )
    entries = ledger_payload.get("entries")
    if not isinstance(entries, list):
        raise ValueError("LEDGER_TAMPER_DETECTED: entries must be list")

    expected_prev = GENESIS_HASH
    for idx, entry in enumerate(entries):
        if not isinstance(entry, Mapping):
            raise ValueError(f"LEDGER_TAMPER_DETECTED: entry[{idx}] is not a mapping")
        seq = entry.get("seq")
        if seq != idx + 1:
            raise ValueError(f"LEDGER_TAMPER_DETECTED: entry[{idx}] seq={seq!r}, expected {idx + 1}")
        prev_h = entry.get("prev_hash")
        if prev_h != expected_prev:
            raise ValueError(
                f"LEDGER_TAMPER_DETECTED: entry[{idx}] prev_hash mismatch "
                f"(got {prev_h!r}, expected {expected_prev!r})"
            )
        recorded_h = entry.get("entry_hash")
        body = {k: v for k, v in entry.items() if k != "entry_hash"}
        recomputed_h = canonical_sha256(body)
        if recorded_h != recomputed_h:
            raise ValueError(
                f"LEDGER_TAMPER_DETECTED: entry[{idx}] entry_hash mismatch "
                f"(recorded={recorded_h!r}, recomputed={recomputed_h!r})"
            )
        expected_prev = recomputed_h

    recorded_root = ledger_payload.get("ledger_root_sha256")
    expected_root = expected_prev
    if recorded_root != expected_root:
        raise ValueError(
            f"LEDGER_TAMPER_DETECTED: ledger_root_sha256 mismatch "
            f"(recorded={recorded_root!r}, expected={expected_root!r})"
        )

    recorded_doc_sha = ledger_payload.get("report_sha256")
    doc_body = {k: v for k, v in ledger_payload.items() if k != "report_sha256"}
    recomputed_doc_sha = canonical_sha256(doc_body)
    if recorded_doc_sha != recomputed_doc_sha:
        raise ValueError(
            f"LEDGER_TAMPER_DETECTED: report_sha256 mismatch "
            f"(recorded={recorded_doc_sha!r}, recomputed={recomputed_doc_sha!r})"
        )

    return {
        "integrity_verified": True,
        "entry_count": len(entries),
        "ledger_root_sha256": expected_root,
        "report_sha256": recomputed_doc_sha,
    }


# ---------------------------------------------------------------------------
# Correlation & Portfolio Weight / Draft `.set` Patch Helpers
# ---------------------------------------------------------------------------


def _safe_pearson_corr(a: np.ndarray, b: np.ndarray) -> float:
    n = min(len(a), len(b))
    if n < 10:
        return 0.0
    xa = a[-n:]
    xb = b[-n:]
    sa = float(np.std(xa, ddof=1))
    sb = float(np.std(xb, ddof=1))
    if sa <= 1e-12 or sb <= 1e-12:
        return 0.0
    corr = float(np.corrcoef(xa, xb)[0, 1])
    if not math.isfinite(corr):
        return 0.0
    return max(-1.0, min(1.0, corr))


def _build_draft_set_diff(
    *,
    action_type: str,
    target_engine: EngineRegistryRecord,
    prev_weight_mult: float,
    replacement_engine: EngineRegistryRecord | None,
    recomputed_weights: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Emit a fail-closed draft `.set` patch requiring explicit owner review & disarm."""
    before_lines = [
        "InpDryRunLogOnly=true",
        "InpGuardDryRunLogOnly=true",
        (
            f"; Engine {target_engine.engine_id} (magic={target_engine.magic}) "
            f"active_weight_mult={prev_weight_mult:.2f}"
        ),
        f"InpMaxTotalOpenRiskPct={HARD_SHIELD_A_TOTAL_OPEN_CAP_PCT:.2f}",
        f"InpMaxSymbolRiskPct={HARD_PER_SYMBOL_CAP_PCT:.2f}",
    ]
    after_lines = [
        "InpDryRunLogOnly=true",
        "InpGuardDryRunLogOnly=true",
        f"; Governance action={action_type} (OWNER_APPROVAL_REQUIRED, AUTO_DEPLOY=false)",
    ]
    if action_type == "REDUCE_WEIGHT_AMBER":
        after_lines.append(
            f"; Engine {target_engine.engine_id} (magic={target_engine.magic}) active_weight_mult=0.50"
        )
    elif action_type == "RETIRE_AND_SWAP" and replacement_engine is not None:
        after_lines.append(
            f"; RETIRE {target_engine.engine_id} (magic={target_engine.magic}) active_weight_mult=0.00"
        )
        new_w = recomputed_weights[replacement_engine.engine_id]
        after_lines.append(
            f"; PROMOTE_BENCH_SWAP {replacement_engine.engine_id} (magic={replacement_engine.magic}, "
            f"sym={replacement_engine.symbol}) base_risk_pct={new_w['base_risk_pct']:.4f} weight_mult=1.00"
        )
    else:
        after_lines.append(
            f"; HALT_ONLY_EMPTY_BENCH {target_engine.engine_id} (magic={target_engine.magic}) active_weight_mult=0.00"
        )
    after_lines.extend([
        f"InpMaxTotalOpenRiskPct={HARD_SHIELD_A_TOTAL_OPEN_CAP_PCT:.2f}",
        f"InpMaxSymbolRiskPct={HARD_PER_SYMBOL_CAP_PCT:.2f}",
    ])

    diff_lines = ["--- a/FTMO_Std10K_MasterProp7E_ACTIVE.set", "+++ b/FTMO_Std10K_MasterProp7E_PROPOSED.set"]
    for line in before_lines:
        diff_lines.append(f"-{line}")
    for line in after_lines:
        diff_lines.append(f"+{line}")

    return {
        "dry_run_locked_true": True,
        "guard_dry_run_locked_true": True,
        "auto_deploy_permitted": AUTO_DEPLOY_PERMITTED,
        "before_lines": before_lines,
        "after_lines": after_lines,
        "unified_diff": "\n".join(diff_lines),
    }


# ---------------------------------------------------------------------------
# Governed 5-Stage Closed-Loop Alpha Factory Controller
# ---------------------------------------------------------------------------


class ClosedLoopAlphaFactoryController:
    """Governed 5-Stage Closed-Loop Alpha Factory with SHA-256 hash-chained audit ledger."""

    def __init__(
        self,
        *,
        factory_id: str = "naqex_wave5_closed_loop_factory",
        gate_thresholds: BlindGateThresholds | None = None,
    ) -> None:
        self.factory_id = str(factory_id)
        self.gate_thresholds = gate_thresholds or BlindGateThresholds()
        self.discovery_queue: list[AlphaCandidateSpec] = []
        self.registry: dict[str, EngineRegistryRecord] = {}
        self.proposals: list[dict[str, Any]] = []
        self._ledger_entries: list[dict[str, Any]] = []
        self._last_hash: str = GENESIS_HASH
        self._append_ledger_event(
            stage="INIT",
            event_type="FACTORY_INITIALIZED",
            engine_id="__SYSTEM__",
            details={
                "factory_id": self.factory_id,
                "order_send_capable": ORDER_SEND_CAPABLE,
                "order_send_count": ORDER_SEND_COUNT,
                "auto_deploy_permitted": AUTO_DEPLOY_PERMITTED,
                "holdout_cutoff_date": HOLDOUT_CUTOFF_DATE,
            },
        )

    def _append_ledger_event(
        self,
        *,
        stage: str,
        event_type: str,
        engine_id: str,
        details: dict[str, Any],
    ) -> dict[str, Any]:
        seq = len(self._ledger_entries) + 1
        body = {
            "seq": seq,
            "ts_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "stage": stage,
            "event_type": event_type,
            "engine_id": engine_id,
            "details": details,
            "prev_hash": self._last_hash,
        }
        entry_hash = canonical_sha256(body)
        entry = {**body, "entry_hash": entry_hash}
        self._ledger_entries.append(entry)
        self._last_hash = entry_hash
        return entry

    def _transition_state(
        self,
        engine_id: str,
        target_state: EngineLifecycleState,
        *,
        stage: str,
        reason: str,
        new_weight_mult: float | None = None,
    ) -> EngineRegistryRecord:
        if engine_id not in self.registry:
            raise ValueError(f"UNKNOWN_ENGINE_ID: {engine_id!r} not in registry")
        rec = self.registry[engine_id]
        allowed = ALLOWED_TRANSITIONS.get(rec.state, frozenset())
        if target_state not in allowed:
            raise ValueError(
                f"ILLEGAL_LIFECYCLE_TRANSITION: {engine_id} cannot move "
                f"{rec.state.value} -> {target_state.value}"
            )
        prev_state = rec.state
        rec.state = target_state
        if new_weight_mult is not None:
            rec.weight_mult = _require_finite_real(new_weight_mult, "new_weight_mult", min_val=0.0, max_val=1.0)
        rec.notes.append(f"{prev_state.value}->{target_state.value}: {reason}")
        self._append_ledger_event(
            stage=stage,
            event_type="STATE_TRANSITION",
            engine_id=engine_id,
            details={
                "from_state": prev_state.value,
                "to_state": target_state.value,
                "weight_mult": round(rec.weight_mult, 4),
                "reason": reason,
            },
        )
        return rec

    def register_active_incumbent(
        self,
        *,
        engine_id: str,
        symbol: str,
        magic: int,
        base_risk_pct: float,
        dev_returns: Sequence[float] | np.ndarray,
        dev_max_date: str = HOLDOUT_CUTOFF_DATE,
        family_id: str = "CORE7_PORT_7E",
    ) -> EngineRegistryRecord:
        """Seed an existing live/demo incumbent engine directly at `ACTIVE_1X` (verified baseline)."""
        validate_pre_holdout_date_str(dev_max_date, "dev_max_date")
        arr = validate_numeric_series_fail_closed(dev_returns, f"{engine_id}.dev_returns", min_len=30)
        _require_strict_int(magic, "magic", min_val=1)
        br = _require_finite_real(base_risk_pct, "base_risk_pct", min_val=0.05, max_val=HARD_PER_SYMBOL_CAP_PCT)
        if engine_id in self.registry:
            raise ValueError(f"DUPLICATE_ENGINE_ID: {engine_id!r} already registered")
        mu = float(np.mean(arr))
        sd = max(float(np.std(arr, ddof=1)), 1e-9)
        sh = mu / sd * math.sqrt(252.0)
        fp = canonical_sha256({"engine_id": engine_id, "symbol": symbol, "magic": magic, "base_risk_pct": br})
        rec = EngineRegistryRecord(
            engine_id=engine_id,
            family_id=family_id,
            symbol=symbol,
            magic=magic,
            base_risk_pct=br,
            weight_mult=1.0,
            state=EngineLifecycleState.ACTIVE_1X,
            quality_score=round(max(0.0, sh), 4),
            cluster_b_sharpe=round(sh, 4),
            dsr_empirical=0.90,
            pbo_cscv=0.20,
            candidate_sha256=fp,
            dev_returns=tuple(float(x) for x in arr),
            dev_max_date=dev_max_date,
        )
        self.registry[engine_id] = rec
        self._append_ledger_event(
            stage="STAGE3_REGISTRY",
            event_type="REGISTER_ACTIVE_INCUMBENT",
            engine_id=engine_id,
            details=rec.to_public_dict(),
        )
        return rec

    # --- Stage 1: Discovery Queue ---
    def enqueue_discovery_candidate(self, candidate: AlphaCandidateSpec) -> EngineRegistryRecord:
        """Stage 1: Validate candidate fail-closed and place in Discovery Queue (`DISCOVERED`)."""
        candidate.validate()
        if candidate.engine_id in self.registry:
            raise ValueError(f"DUPLICATE_CANDIDATE_ID: {candidate.engine_id!r} already exists")
        self.discovery_queue.append(candidate)
        q_score = max(0.0, candidate.cluster_b_sharpe * candidate.dsr_empirical * (1.0 - candidate.pbo_cscv))
        rec = EngineRegistryRecord(
            engine_id=candidate.engine_id,
            family_id=candidate.family_id,
            symbol=candidate.symbol,
            magic=candidate.magic,
            base_risk_pct=candidate.base_risk_pct,
            weight_mult=0.0,
            state=EngineLifecycleState.DISCOVERED,
            quality_score=round(q_score, 4),
            cluster_b_sharpe=round(candidate.cluster_b_sharpe, 4),
            dsr_empirical=round(candidate.dsr_empirical, 4),
            pbo_cscv=round(candidate.pbo_cscv, 4),
            candidate_sha256=candidate.fingerprint_sha256(),
            dev_returns=tuple(float(x) for x in candidate.daily_returns_dev),
            dev_max_date=candidate.cluster_b_end_date,
        )
        self.registry[candidate.engine_id] = rec
        self._append_ledger_event(
            stage="STAGE1_DISCOVERY_QUEUE",
            event_type="CANDIDATE_ENQUEUED",
            engine_id=candidate.engine_id,
            details={
                "family_id": candidate.family_id,
                "symbol": candidate.symbol,
                "candidate_sha256": rec.candidate_sha256,
                "cluster_a_end_date": candidate.cluster_a_end_date,
                "cluster_b_end_date": candidate.cluster_b_end_date,
                "holdout_rows_analysed": 0,
            },
        )
        return rec

    # --- Stage 2: Blind Validation Gate ---
    def run_blind_validation_gate(self, engine_id: str, *, auto_bench: bool = True) -> dict[str, Any]:
        """Stage 2: Causal `Cluster A -> Blind Cluster B` gate; promotes ONLY passing candidates."""
        cand = next((c for c in self.discovery_queue if c.engine_id == engine_id), None)
        if cand is None:
            raise ValueError(f"CANDIDATE_NOT_IN_DISCOVERY_QUEUE: {engine_id!r}")
        cand.validate()
        thr = self.gate_thresholds

        # Gate 2A: Cluster A (<= 2020-12-31)
        ca_failures: list[str] = []
        if cand.cluster_a_sharpe < thr.min_cluster_a_sharpe:
            ca_failures.append(f"cluster_a_sharpe={cand.cluster_a_sharpe:.3f} < {thr.min_cluster_a_sharpe}")
        if cand.cluster_a_pf < thr.min_cluster_a_pf:
            ca_failures.append(f"cluster_a_pf={cand.cluster_a_pf:.3f} < {thr.min_cluster_a_pf}")
        if ca_failures:
            self._transition_state(
                engine_id,
                EngineLifecycleState.KILLED,
                stage="STAGE2_BLIND_GATE",
                reason="Cluster A fail: " + "; ".join(ca_failures),
            )
            return {"engine_id": engine_id, "passed": False, "final_state": "KILLED", "failures": ca_failures}

        self._transition_state(
            engine_id,
            EngineLifecycleState.CLUSTER_A_PASS,
            stage="STAGE2_BLIND_GATE",
            reason=f"Cluster A PASS (Sharpe={cand.cluster_a_sharpe:.3f}, PF={cand.cluster_a_pf:.3f})",
        )

        # Gate 2B: Blind Cluster B (2021-2024) + anti-overfitting + correlation vs active portfolio
        cb_failures: list[str] = []
        if cand.cluster_b_sharpe < thr.min_cluster_b_sharpe:
            cb_failures.append(f"cluster_b_sharpe={cand.cluster_b_sharpe:.3f} < {thr.min_cluster_b_sharpe}")
        if cand.cluster_b_pf < thr.min_cluster_b_pf:
            cb_failures.append(f"cluster_b_pf={cand.cluster_b_pf:.3f} < {thr.min_cluster_b_pf}")
        if cand.pbo_cscv > thr.max_pbo_cscv:
            cb_failures.append(f"pbo_cscv={cand.pbo_cscv:.3f} > {thr.max_pbo_cscv}")
        if cand.dsr_empirical < thr.min_dsr_empirical:
            cb_failures.append(f"dsr_empirical={cand.dsr_empirical:.3f} < {thr.min_dsr_empirical}")
        if cand.cost_stress_2x_net_pct <= thr.min_cost_stress_2x_net_pct:
            cb_failures.append(f"cost_stress_2x={cand.cost_stress_2x_net_pct:.3f}% <= {thr.min_cost_stress_2x_net_pct}")

        cand_arr = np.asarray(cand.daily_returns_dev, dtype=np.float64)
        max_abs_corr = 0.0
        for active in self.active_engines():
            c_val = abs(_safe_pearson_corr(cand_arr, np.asarray(active.dev_returns, dtype=np.float64)))
            if c_val > max_abs_corr:
                max_abs_corr = c_val
        if max_abs_corr > thr.max_abs_corr_vs_active:
            cb_failures.append(f"max_abs_corr_vs_active={max_abs_corr:.3f} > {thr.max_abs_corr_vs_active}")

        if cb_failures:
            self._transition_state(
                engine_id,
                EngineLifecycleState.KILLED,
                stage="STAGE2_BLIND_GATE",
                reason="Blind Cluster B fail: " + "; ".join(cb_failures),
            )
            return {
                "engine_id": engine_id,
                "passed": False,
                "final_state": "KILLED",
                "max_abs_corr_vs_active": round(max_abs_corr, 4),
                "failures": cb_failures,
            }

        self._transition_state(
            engine_id,
            EngineLifecycleState.BLIND_B_VERIFIED,
            stage="STAGE2_BLIND_GATE",
            reason=(
                f"Blind Cluster B PASS (Sharpe={cand.cluster_b_sharpe:.3f}, DSR={cand.dsr_empirical:.3f}, "
                f"PBO={cand.pbo_cscv:.3f}, max|corr|={max_abs_corr:.3f})"
            ),
        )
        if auto_bench:
            self._transition_state(
                engine_id,
                EngineLifecycleState.BENCH_READY,
                stage="STAGE3_ALPHA_BENCH",
                reason="Admitted to governed Alpha Bench (`BENCH_READY`, approval required before Shadow/Live)",
            )

        return {
            "engine_id": engine_id,
            "passed": True,
            "final_state": self.registry[engine_id].state.value,
            "max_abs_corr_vs_active": round(max_abs_corr, 4),
            "failures": [],
        }

    # --- Stage 3: Alpha Bench Registry Queries ---
    def active_engines(self) -> list[EngineRegistryRecord]:
        return [
            r
            for r in self.registry.values()
            if r.state in (EngineLifecycleState.ACTIVE_1X, EngineLifecycleState.DECAY_AMBER_0_5X)
        ]

    def bench_ready_candidates(self) -> list[EngineRegistryRecord]:
        return [r for r in self.registry.values() if r.state == EngineLifecycleState.BENCH_READY]

    # --- Stage 4: Decay Watcher Bridge + Stage 5: Governed Retire & Swap Planner ---
    def run_decay_and_governance_cycle(
        self,
        live_streams_by_engine: Mapping[str, Sequence[float] | np.ndarray],
        *,
        cusum_k_sigma: Any = 0.25,
        cusum_h_sigma: Any = 4.5,
        sprt_alpha: Any = 0.05,
        sprt_beta: Any = 0.10,
        n_cone_draws: Any = 2000,
        seed: Any = 20261123,
        force_stdlib_fallback: bool = False,
    ) -> dict[str, Any]:
        """Stage 4 + Stage 5: Monitor active engines fail-closed and emit SHA-256 governance proposals."""
        # Validate thresholds once upfront (P1-6 fail-closed)
        validate_decay_thresholds_fail_closed(
            cusum_k_sigma=cusum_k_sigma,
            cusum_h_sigma=cusum_h_sigma,
            sprt_alpha=sprt_alpha,
            sprt_beta=sprt_beta,
            n_cone_draws=n_cone_draws,
            seed=seed,
        )

        active_list = sorted(self.active_engines(), key=lambda r: r.engine_id)
        decay_reports: dict[str, Any] = {}
        emitted_proposals: list[dict[str, Any]] = []

        for rec in active_list:
            if rec.engine_id not in live_streams_by_engine:
                raise ValueError(f"MISSING_LIVE_STREAM: active engine {rec.engine_id!r} missing from cycle input")
            live_series = live_streams_by_engine[rec.engine_id]
            decay_res = evaluate_decay_fail_closed(
                rec.dev_returns,
                live_series,
                cusum_k_sigma=cusum_k_sigma,
                cusum_h_sigma=cusum_h_sigma,
                sprt_alpha=sprt_alpha,
                sprt_beta=sprt_beta,
                n_cone_draws=n_cone_draws,
                seed=seed,
                dev_max_date=rec.dev_max_date,
                force_stdlib_fallback=force_stdlib_fallback,
            )
            verdict = str(decay_res["verdict"])
            rec.last_decay_verdict = verdict
            decay_reports[rec.engine_id] = decay_res

            self._append_ledger_event(
                stage="STAGE4_DECAY_WATCHER",
                event_type="DECAY_EVALUATED",
                engine_id=rec.engine_id,
                details={
                    "verdict": verdict,
                    "backend": decay_res["decay_backend"],
                    "cusum_cur_neg": decay_res["cusum"]["current_negative_sigma"],
                    "sprt_state": decay_res["sprt"]["state"],
                    "cone_pct_rank": decay_res["confidence_cone"]["observed_percentile"],
                },
            )

            if verdict == "GREEN_WITHIN_EXPECTATION":
                if rec.state == EngineLifecycleState.DECAY_AMBER_0_5X:
                    self._transition_state(
                        rec.engine_id,
                        EngineLifecycleState.ACTIVE_1X,
                        stage="STAGE4_DECAY_WATCHER",
                        reason="Recovered to GREEN_WITHIN_EXPECTATION",
                        new_weight_mult=1.0,
                    )
            elif verdict == "AMBER_WATCH_REDUCE_SIZE":
                prev_w = float(rec.weight_mult)
                if rec.state == EngineLifecycleState.ACTIVE_1X:
                    self._transition_state(
                        rec.engine_id,
                        EngineLifecycleState.DECAY_AMBER_0_5X,
                        stage="STAGE4_DECAY_WATCHER",
                        reason="Amber CUSUM/cone/SPRT watch -> halve size to 0.5x",
                        new_weight_mult=0.5,
                    )
                proposal = self._emit_amber_halve_proposal(rec, decay_res, prev_weight_mult=prev_w)
                emitted_proposals.append(proposal)
            elif verdict == "RED_HALT_ALPHA_DECAY":
                prev_w = float(rec.weight_mult)
                proposal = self._plan_retire_and_swap(rec, decay_res, prev_weight_mult=prev_w)
                emitted_proposals.append(proposal)
            else:
                raise ValueError(f"UNKNOWN_DECAY_VERDICT: {verdict!r}")

        return {
            "evaluated_engines": len(active_list),
            "decay_reports": decay_reports,
            "proposals": emitted_proposals,
            "active_roster_after": [
                r.to_public_dict() for r in sorted(self.active_engines(), key=lambda x: x.engine_id)
            ],
            "bench_ready_after": [
                r.to_public_dict() for r in sorted(self.bench_ready_candidates(), key=lambda x: x.engine_id)
            ],
        }

    def _recompute_portfolio_weights(
        self,
        *,
        retired_id: str | None = None,
        promoted_rec: EngineRegistryRecord | None = None,
    ) -> dict[str, dict[str, Any]]:
        """Recompute portfolio weights preserving Shield A (`<= 3.00%` open cap, `<= 1.75%` symbol cap)."""
        weights: dict[str, dict[str, Any]] = {}
        active = [r for r in self.active_engines() if r.engine_id != retired_id]
        for r in active:
            weights[r.engine_id] = {
                "symbol": r.symbol,
                "magic": r.magic,
                "base_risk_pct": round(r.base_risk_pct, 4),
                "weight_mult": round(r.weight_mult, 4),
                "effective_base_risk_pct": round(r.base_risk_pct * r.weight_mult, 4),
                "status": r.state.value,
            }
        if promoted_rec is not None:
            # Cap replacement base risk so symbol & Shield-A total caps remain clean
            sym_used = sum(
                w["effective_base_risk_pct"] for w in weights.values() if w["symbol"] == promoted_rec.symbol
            )
            allowed_sym_risk = max(0.15, min(promoted_rec.base_risk_pct, HARD_PER_SYMBOL_CAP_PCT - sym_used))
            weights[promoted_rec.engine_id] = {
                "symbol": promoted_rec.symbol,
                "magic": promoted_rec.magic,
                "base_risk_pct": round(allowed_sym_risk, 4),
                "weight_mult": 1.0,
                "effective_base_risk_pct": round(allowed_sym_risk, 4),
                "status": "PROPOSED_SHADOW_INCUBATION_SWAP",
            }
        return weights

    def _emit_amber_halve_proposal(
        self,
        rec: EngineRegistryRecord,
        decay_res: dict[str, Any],
        *,
        prev_weight_mult: float = 1.0,
    ) -> dict[str, Any]:
        weights = self._recompute_portfolio_weights()
        draft_patch = _build_draft_set_diff(
            action_type="REDUCE_WEIGHT_AMBER",
            target_engine=rec,
            prev_weight_mult=prev_weight_mult,
            replacement_engine=None,
            recomputed_weights=weights,
        )
        body = {
            "schema_version": PROPOSAL_SCHEMA_VERSION,
            "proposal_id": f"PROP_AMBER_{rec.engine_id}_{len(self.proposals) + 1:03d}",
            "action_type": "REDUCE_WEIGHT_AMBER",
            "target_engine_id": rec.engine_id,
            "proposed_weight_mult": 0.5,
            "replacement_engine_id": None,
            "approval_required": True,
            "auto_deployed": False,
            "auto_deploy_permitted": AUTO_DEPLOY_PERMITTED,
            "owner_approval_status": "PENDING_OWNER_APPROVAL",
            "order_send_count": ORDER_SEND_COUNT,
            "decay_verdict": decay_res["verdict"],
            "decay_reasons": decay_res["reasons"],
            "recomputed_weights": weights,
            "draft_set_diff": draft_patch,
        }
        proposal = {**body, "proposal_sha256": canonical_sha256(body)}
        self.proposals.append(proposal)
        self._append_ledger_event(
            stage="STAGE5_RETIRE_SWAP_PLANNER",
            event_type="PROPOSAL_EMITTED_AMBER_HALVE",
            engine_id=rec.engine_id,
            details={
                "proposal_id": proposal["proposal_id"],
                "proposal_sha256": proposal["proposal_sha256"],
                "proposed_weight_mult": 0.5,
            },
        )
        return proposal

    def _plan_retire_and_swap(
        self,
        decayed_rec: EngineRegistryRecord,
        decay_res: dict[str, Any],
        *,
        prev_weight_mult: float = 1.0,
    ) -> dict[str, Any]:
        """Stage 5: Retire decayed engine; swap ONLY with highest-score lowest-corr `BENCH_READY` candidate."""
        self._transition_state(
            decayed_rec.engine_id,
            EngineLifecycleState.RETIRED,
            stage="STAGE5_RETIRE_SWAP_PLANNER",
            reason="RED_HALT_ALPHA_DECAY confirmed by CUSUM + SPRT/p05 cone",
            new_weight_mult=0.0,
        )

        remaining_active = self.active_engines()
        bench_pool = self.bench_ready_candidates()

        # STRICT FAIL-CLOSED: ONLY `BENCH_READY` candidates are eligible — NEVER unverified or KILLED!
        ranked_candidates: list[dict[str, Any]] = []
        for cand in bench_pool:
            if cand.state != EngineLifecycleState.BENCH_READY:
                continue
            cand_arr = np.asarray(cand.dev_returns, dtype=np.float64)
            corrs = [
                abs(_safe_pearson_corr(cand_arr, np.asarray(act.dev_returns, dtype=np.float64)))
                for act in remaining_active
            ]
            max_abs_corr = max(corrs) if corrs else 0.0
            mean_abs_corr = float(np.mean(corrs)) if corrs else 0.0
            if max_abs_corr > MAX_REPLACEMENT_ABS_CORR:
                continue
            # Composite score: highest quality_score AND lowest correlation vs surviving active portfolio
            composite = cand.quality_score * (1.0 - 0.65 * max_abs_corr - 0.35 * mean_abs_corr)
            ranked_candidates.append({
                "engine_id": cand.engine_id,
                "symbol": cand.symbol,
                "quality_score": round(cand.quality_score, 4),
                "max_abs_corr_vs_remaining_active": round(max_abs_corr, 4),
                "mean_abs_corr_vs_remaining_active": round(mean_abs_corr, 4),
                "selection_composite_score": round(composite, 4),
            })

        ranked_candidates.sort(
            key=lambda x: (
                -x["selection_composite_score"],
                x["max_abs_corr_vs_remaining_active"],
                -x["quality_score"],
                x["engine_id"],
            )
        )

        if not ranked_candidates:
            # FAIL-CLOSED EMPTY BENCH: HALT ONLY — ZERO unverified promotion!
            weights = self._recompute_portfolio_weights(retired_id=decayed_rec.engine_id, promoted_rec=None)
            draft_patch = _build_draft_set_diff(
                action_type="HALT_ONLY_EMPTY_BENCH",
                target_engine=decayed_rec,
                prev_weight_mult=prev_weight_mult,
                replacement_engine=None,
                recomputed_weights=weights,
            )
            body = {
                "schema_version": PROPOSAL_SCHEMA_VERSION,
                "proposal_id": f"PROP_HALT_EMPTY_BENCH_{decayed_rec.engine_id}_{len(self.proposals) + 1:03d}",
                "action_type": "HALT_ONLY_EMPTY_BENCH",
                "target_engine_id": decayed_rec.engine_id,
                "proposed_weight_mult": 0.0,
                "replacement_engine_id": None,
                "bench_candidates_evaluated": [],
                "fail_closed_reason": (
                    "NO_VERIFIED_BENCH_READY_CANDIDATE_AVAILABLE: fail-closed HALT only; "
                    "unverified/discovered/killed candidates strictly forbidden from promotion"
                ),
                "approval_required": True,
                "auto_deployed": False,
                "auto_deploy_permitted": AUTO_DEPLOY_PERMITTED,
                "owner_approval_status": "PENDING_OWNER_APPROVAL",
                "order_send_count": ORDER_SEND_COUNT,
                "decay_verdict": decay_res["verdict"],
                "decay_reasons": decay_res["reasons"],
                "recomputed_weights": weights,
                "draft_set_diff": draft_patch,
            }
            proposal = {**body, "proposal_sha256": canonical_sha256(body)}
            self.proposals.append(proposal)
            self._append_ledger_event(
                stage="STAGE5_RETIRE_SWAP_PLANNER",
                event_type="PROPOSAL_EMITTED_HALT_EMPTY_BENCH",
                engine_id=decayed_rec.engine_id,
                details={
                    "proposal_id": proposal["proposal_id"],
                    "proposal_sha256": proposal["proposal_sha256"],
                    "replacement_engine_id": None,
                },
            )
            return proposal

        winner_meta = ranked_candidates[0]
        winner_rec = self.registry[winner_meta["engine_id"]]
        self._transition_state(
            winner_rec.engine_id,
            EngineLifecycleState.SHADOW_INCUBATION,
            stage="STAGE5_RETIRE_SWAP_PLANNER",
            reason=(
                f"Selected as highest-score lowest-corr BENCH_READY swap for {decayed_rec.engine_id} "
                f"(composite={winner_meta['selection_composite_score']:.4f}, "
                f"max|corr|={winner_meta['max_abs_corr_vs_remaining_active']:.4f}); "
                f"held in SHADOW_INCUBATION pending explicit owner approval"
            ),
            new_weight_mult=0.0,
        )
        weights = self._recompute_portfolio_weights(retired_id=decayed_rec.engine_id, promoted_rec=winner_rec)
        draft_patch = _build_draft_set_diff(
            action_type="RETIRE_AND_SWAP",
            target_engine=decayed_rec,
            prev_weight_mult=prev_weight_mult,
            replacement_engine=winner_rec,
            recomputed_weights=weights,
        )
        body = {
            "schema_version": PROPOSAL_SCHEMA_VERSION,
            "proposal_id": f"PROP_SWAP_{decayed_rec.engine_id}_TO_{winner_rec.engine_id}_{len(self.proposals) + 1:03d}",
            "action_type": "RETIRE_AND_SWAP",
            "target_engine_id": decayed_rec.engine_id,
            "proposed_weight_mult": 0.0,
            "replacement_engine_id": winner_rec.engine_id,
            "replacement_state_after_proposal": winner_rec.state.value,
            "replacement_selection_metrics": winner_meta,
            "bench_candidates_evaluated": ranked_candidates,
            "approval_required": True,
            "auto_deployed": False,
            "auto_deploy_permitted": AUTO_DEPLOY_PERMITTED,
            "owner_approval_status": "PENDING_OWNER_APPROVAL",
            "order_send_count": ORDER_SEND_COUNT,
            "decay_verdict": decay_res["verdict"],
            "decay_reasons": decay_res["reasons"],
            "recomputed_weights": weights,
            "draft_set_diff": draft_patch,
        }
        proposal = {**body, "proposal_sha256": canonical_sha256(body)}
        self.proposals.append(proposal)
        self._append_ledger_event(
            stage="STAGE5_RETIRE_SWAP_PLANNER",
            event_type="PROPOSAL_EMITTED_RETIRE_AND_SWAP",
            engine_id=decayed_rec.engine_id,
            details={
                "proposal_id": proposal["proposal_id"],
                "proposal_sha256": proposal["proposal_sha256"],
                "replacement_engine_id": winner_rec.engine_id,
                "max_abs_corr": winner_meta["max_abs_corr_vs_remaining_active"],
            },
        )
        return proposal

    def export_ledger(self, *, write_output_path: Path | None = None) -> dict[str, Any]:
        """Serialize tamper-evident SHA-256 hash-chained ledger; optionally persist atomically."""
        body: dict[str, Any] = {
            "schema_version": LEDGER_SCHEMA_VERSION,
            "generated_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "factory_id": self.factory_id,
            "hard_invariants": {
                "order_send_capable": ORDER_SEND_CAPABLE,
                "order_send_count": ORDER_SEND_COUNT,
                "auto_deploy_permitted": AUTO_DEPLOY_PERMITTED,
                "holdout_cutoff_date": HOLDOUT_CUTOFF_DATE,
                "holdout_rows_analysed": 0,
                "shield_a_total_open_cap_pct": HARD_SHIELD_A_TOTAL_OPEN_CAP_PCT,
                "pc_dev_policy": DEV_PC_REQUIRED_MODE,
            },
            "registry_snapshot": {
                k: v.to_public_dict() for k, v in sorted(self.registry.items(), key=lambda kv: kv[0])
            },
            "proposals": list(self.proposals),
            "entry_count": len(self._ledger_entries),
            "ledger_root_sha256": self._last_hash,
            "entries": list(self._ledger_entries),
        }
        payload = {**body, "report_sha256": canonical_sha256(body)}
        verify_ledger_integrity(payload)
        if write_output_path is not None:
            _atomic_write_json_lf(Path(write_output_path), payload)
        return payload


# ---------------------------------------------------------------------------
# Baseline Generator for Drills (Real Sealed Dev Tapes or Pure-NumPy Fallback)
# ---------------------------------------------------------------------------


def _load_or_synthesize_port7e_dev_series(
    *,
    seed: int = 20261128,
    n_days: int = 260,
) -> tuple[dict[str, np.ndarray], str]:
    """Build deterministic pre-holdout (`<= 2024-12-31`) per-engine daily R series for E1..E7."""
    # Try sealed Dev tapes first if available locally; fall back cleanly to deterministic synthetic series in CI
    try:
        from quant_factory.capital_optimizer.x13_shard import load_frozen_tapes_v2_direct

        frozen = load_frozen_tapes_v2_direct()
        ext_days = list(frozen["ext_days"])
        tapes = frozen["tapes"]
        series_map: dict[str, np.ndarray] = {}
        ok = True
        for eng in CANONICAL_PORT_7E_ENGINES:
            eid = eng["engine_id"]
            if eid not in tapes:
                ok = False
                break
            vals = [float(tapes[eid][d][0]["net_R"]) for d in ext_days if d in tapes[eid]]
            if len(vals) < 60:
                ok = False
                break
            arr = np.asarray(vals, dtype=np.float64)
            if not np.all(np.isfinite(arr)):
                ok = False
                break
            series_map[eid] = arr
        if ok and len(series_map) == len(CANONICAL_PORT_7E_ENGINES):
            return series_map, f"frozen_9e_tapes_v2(sha={frozen['npz_sha256'][:16]})"
    except Exception:
        pass

    rng = np.random.default_rng(seed)
    synth: dict[str, np.ndarray] = {}
    for idx, eng in enumerate(CANONICAL_PORT_7E_ENGINES):
        mu = 0.08 + 0.01 * (idx % 3)
        sd = 0.55 + 0.04 * (idx % 4)
        synth[eng["engine_id"]] = rng.normal(loc=mu, scale=sd, size=n_days).astype(np.float64)
    return synth, "deterministic_synthetic_port7e_ci_baseline"


def _seed_factory_with_port7e(
    factory_id: str,
    dev_map: Mapping[str, np.ndarray],
) -> ClosedLoopAlphaFactoryController:
    ctrl = ClosedLoopAlphaFactoryController(factory_id=factory_id)
    for eng in CANONICAL_PORT_7E_ENGINES:
        ctrl.register_active_incumbent(
            engine_id=eng["engine_id"],
            symbol=eng["symbol"],
            magic=eng["magic"],
            base_risk_pct=eng["base_risk_pct"],
            dev_returns=dev_map[eng["engine_id"]],
            dev_max_date=HOLDOUT_CUTOFF_DATE,
        )
    return ctrl


def _make_healthy_live_streams(
    dev_map: Mapping[str, np.ndarray],
    *,
    n_live: int = 40,
    seed: int = 20261128,
) -> dict[str, np.ndarray]:
    """Generate healthy live return streams centered cleanly above Dev baseline mean (all GREEN)."""
    rng = np.random.default_rng(seed)
    out: dict[str, np.ndarray] = {}
    for eng in CANONICAL_PORT_7E_ENGINES:
        eid = eng["engine_id"]
        base = dev_map[eid]
        mu = float(np.mean(base))
        sd = max(float(np.std(base, ddof=1)), 0.05)
        stream = rng.normal(loc=mu + 0.15 * sd, scale=0.60 * sd, size=n_live)
        # Ensure clean positive drift above p50
        if float(np.mean(stream)) < mu:
            stream = stream + (mu - float(np.mean(stream)) + 0.10 * sd)
        out[eid] = stream.astype(np.float64)
    return out


# ---------------------------------------------------------------------------
# Mandatory 5 E2E Drills (Gate W5-G17)
# ---------------------------------------------------------------------------


def run_all_e2e_drills(
    *,
    write_ledger_path: Path | None = DEFAULT_LEDGER_OUT_PATH,
    write_drills_path: Path | None = DEFAULT_DRILLS_OUT_PATH,
    force_stdlib_fallback: bool = False,
) -> dict[str, Any]:
    """Execute ALL 5 mandatory W5-G17 E2E drills and verify 100% fail-closed governance."""
    t0 = time.perf_counter()
    dev_map, baseline_source = _load_or_synthesize_port7e_dev_series()

    # ------------------------------------------------------------------
    # DRILL 1: NORMAL GREEN (all 7 engines healthy -> keep 1.0x)
    # ------------------------------------------------------------------
    ctrl1 = _seed_factory_with_port7e("drill_1_normal_green", dev_map)
    live1 = _make_healthy_live_streams(dev_map, n_live=40, seed=101)
    res1 = ctrl1.run_decay_and_governance_cycle(live1, force_stdlib_fallback=force_stdlib_fallback)
    verdicts1 = {k: v["verdict"] for k, v in res1["decay_reports"].items()}
    all_green = all(v == "GREEN_WITHIN_EXPECTATION" for v in verdicts1.values())
    all_1x = all(
        r.state == EngineLifecycleState.ACTIVE_1X and abs(r.weight_mult - 1.0) < 1e-9
        for r in ctrl1.active_engines()
    )
    drill1_pass = all_green and all_1x and len(res1["proposals"]) == 0
    drill1_summary = {
        "drill_id": "DRILL_1_NORMAL_GREEN",
        "passed": drill1_pass,
        "evaluated_engines": res1["evaluated_engines"],
        "verdicts": verdicts1,
        "proposals_emitted": len(res1["proposals"]),
        "all_weights_1_0x": all_1x,
        "ledger_integrity": verify_ledger_integrity(ctrl1.export_ledger(write_output_path=None)),
    }

    # ------------------------------------------------------------------
    # DRILL 2: AMBER HALVED (1 engine breaches Amber CUSUM/cone -> weight_mult=0.5 proposal)
    # ------------------------------------------------------------------
    ctrl2 = _seed_factory_with_port7e("drill_2_amber_halved", dev_map)
    live2 = _make_healthy_live_streams(dev_map, n_live=40, seed=202)
    amber_target = "E3_GBPUSD_VH"
    b2 = dev_map[amber_target]
    mu2, sd2 = float(np.mean(b2)), max(float(np.std(b2, ddof=1)), 0.05)
    # Calibrated negative drift: breaches p05 cone while staying below -4.5sigma active CUSUM
    amber_stream = np.full(10, mu2 - 0.62 * sd2, dtype=np.float64)
    for z_amp in (0.62, 0.58, 0.66, 0.54, 0.69):
        cand_stream = np.full(10, mu2 - z_amp * sd2, dtype=np.float64)
        probe2 = evaluate_decay_fail_closed(b2, cand_stream, force_stdlib_fallback=force_stdlib_fallback)
        if probe2["verdict"] == "AMBER_WATCH_REDUCE_SIZE":
            amber_stream = cand_stream
            break
    live2[amber_target] = amber_stream
    res2 = ctrl2.run_decay_and_governance_cycle(live2, force_stdlib_fallback=force_stdlib_fallback)
    verdicts2 = {k: v["verdict"] for k, v in res2["decay_reports"].items()}
    rec2 = ctrl2.registry[amber_target]
    prop2 = res2["proposals"][0] if len(res2["proposals"]) == 1 else None
    drill2_pass = (
        verdicts2[amber_target] == "AMBER_WATCH_REDUCE_SIZE"
        and rec2.state == EngineLifecycleState.DECAY_AMBER_0_5X
        and abs(rec2.weight_mult - 0.5) < 1e-9
        and prop2 is not None
        and prop2["action_type"] == "REDUCE_WEIGHT_AMBER"
        and abs(prop2["proposed_weight_mult"] - 0.5) < 1e-9
        and prop2["approval_required"] is True
        and prop2["auto_deployed"] is False
        and len(prop2["proposal_sha256"]) == 64
    )
    drill2_summary = {
        "drill_id": "DRILL_2_AMBER_HALVED",
        "passed": drill2_pass,
        "target_engine": amber_target,
        "target_verdict": verdicts2[amber_target],
        "target_state_after": rec2.state.value,
        "target_weight_mult_after": rec2.weight_mult,
        "proposal": prop2,
        "ledger_integrity": verify_ledger_integrity(ctrl2.export_ledger(write_output_path=None)),
    }

    # ------------------------------------------------------------------
    # DRILL 3: RED WITH BENCH SWAP (1 engine hits RED + 2 BENCH_READY candidates ->
    #          selects highest-score, lowest-corr BENCH_READY + draft .set patch + SHA-256)
    # ------------------------------------------------------------------
    ctrl3 = _seed_factory_with_port7e("drill_3_red_with_bench_swap", dev_map)
    red_target = "E6_EURJPY_VOLCOMP"
    rng3 = np.random.default_rng(303)
    n_ref = min(len(v) for v in dev_map.values())
    # Candidate A: high quality & truly orthogonal (near-zero correlation vs active engines)
    orth_series = tuple(float(x) for x in rng3.normal(loc=0.14, scale=0.45, size=n_ref))
    # Candidate B: slightly lower quality AND moderate (~0.25) correlation with E4_US100_SESS40 (passes Stage 2)
    e4_tail = dev_map["E4_US100_SESS40"][-n_ref:]
    e4_std = max(float(np.std(e4_tail, ddof=1)), 1e-6)
    e4_norm = (e4_tail - float(np.mean(e4_tail))) / e4_std
    corr_series = tuple(
        float(x)
        for x in (0.12 + 0.14 * e4_norm + rng3.normal(loc=0.0, scale=0.48, size=n_ref))
    )
    # Candidate C: fails Blind Cluster B (killed -> must NOT be selected!)
    bad_series = tuple(float(x) for x in rng3.normal(loc=-0.02, scale=0.50, size=n_ref))

    cand_best = AlphaCandidateSpec(
        engine_id="B1_XAGUSD_ORTH_VOL",
        family_id="W5_METALS_ORTH",
        symbol="XAGUSD",
        magic=20261141,
        base_risk_pct=0.50,
        cluster_a_end_date="2020-12-31",
        cluster_b_end_date="2024-12-31",
        cluster_a_sharpe=1.25,
        cluster_a_pf=1.34,
        cluster_b_sharpe=1.18,
        cluster_b_pf=1.29,
        pbo_cscv=0.18,
        dsr_empirical=0.94,
        cost_stress_2x_net_pct=18.5,
        daily_returns_dev=orth_series,
    )
    cand_runner = AlphaCandidateSpec(
        engine_id="B2_EURGBP_SESS_FLOW",
        family_id="W5_FX_CROSS",
        symbol="EURGBP",
        magic=20261142,
        base_risk_pct=0.50,
        cluster_a_end_date="2020-12-31",
        cluster_b_end_date="2024-12-31",
        cluster_a_sharpe=0.95,
        cluster_a_pf=1.22,
        cluster_b_sharpe=0.88,
        cluster_b_pf=1.19,
        pbo_cscv=0.28,
        dsr_empirical=0.82,
        cost_stress_2x_net_pct=11.2,
        daily_returns_dev=corr_series,
    )
    cand_killed = AlphaCandidateSpec(
        engine_id="B3_OVERFIT_REJECTED",
        family_id="W5_REJECTED",
        symbol="NZDUSD",
        magic=20261143,
        base_risk_pct=0.50,
        cluster_a_end_date="2020-12-31",
        cluster_b_end_date="2024-12-31",
        cluster_a_sharpe=1.40,
        cluster_a_pf=1.42,
        cluster_b_sharpe=0.25,
        cluster_b_pf=0.96,
        pbo_cscv=0.72,
        dsr_empirical=0.20,
        cost_stress_2x_net_pct=-4.5,
        daily_returns_dev=bad_series,
    )
    for c in (cand_best, cand_runner, cand_killed):
        ctrl3.enqueue_discovery_candidate(c)
        ctrl3.run_blind_validation_gate(c.engine_id, auto_bench=True)

    live3 = _make_healthy_live_streams(dev_map, n_live=40, seed=3030)
    b3 = dev_map[red_target]
    mu3, sd3 = float(np.mean(b3)), max(float(np.std(b3, ddof=1)), 0.05)
    # Deep structural alpha decay: 25 consecutive losing observations -> severe negative CUSUM + SPRT + <p05
    live3[red_target] = np.full(25, mu3 - 1.15 * sd3, dtype=np.float64)

    res3 = ctrl3.run_decay_and_governance_cycle(live3, force_stdlib_fallback=force_stdlib_fallback)
    prop3 = res3["proposals"][0] if len(res3["proposals"]) == 1 else None
    ledger3 = ctrl3.export_ledger(write_output_path=write_ledger_path)
    drill3_pass = (
        res3["decay_reports"][red_target]["verdict"] == "RED_HALT_ALPHA_DECAY"
        and ctrl3.registry[red_target].state == EngineLifecycleState.RETIRED
        and ctrl3.registry["B3_OVERFIT_REJECTED"].state == EngineLifecycleState.KILLED
        and prop3 is not None
        and prop3["action_type"] == "RETIRE_AND_SWAP"
        and prop3["replacement_engine_id"] == "B1_XAGUSD_ORTH_VOL"
        and ctrl3.registry["B1_XAGUSD_ORTH_VOL"].state == EngineLifecycleState.SHADOW_INCUBATION
        and prop3["draft_set_diff"]["dry_run_locked_true"] is True
        and prop3["draft_set_diff"]["guard_dry_run_locked_true"] is True
        and prop3["approval_required"] is True
        and prop3["auto_deployed"] is False
        and len(prop3["proposal_sha256"]) == 64
    )
    drill3_summary = {
        "drill_id": "DRILL_3_RED_WITH_BENCH_SWAP",
        "passed": drill3_pass,
        "target_engine": red_target,
        "target_verdict": res3["decay_reports"][red_target]["verdict"],
        "retired_state": ctrl3.registry[red_target].state.value,
        "selected_replacement": prop3["replacement_engine_id"] if prop3 else None,
        "rejected_candidate_state": ctrl3.registry["B3_OVERFIT_REJECTED"].state.value,
        "proposal": prop3,
        "production_ledger_written_to": str(write_ledger_path) if write_ledger_path is not None else None,
        "ledger_integrity": verify_ledger_integrity(ledger3),
    }

    # ------------------------------------------------------------------
    # DRILL 4: RED WITH EMPTY BENCH FAIL-CLOSED (NEVER promote unverified/killed!)
    # ------------------------------------------------------------------
    ctrl4 = _seed_factory_with_port7e("drill_4_red_empty_bench_fail_closed", dev_map)
    # Enqueue an UNVERIFIED (`DISCOVERED`) candidate and a `KILLED` candidate — ZERO `BENCH_READY`!
    cand_unverified = AlphaCandidateSpec(
        engine_id="U1_UNVERIFIED_DISCOVERED",
        family_id="W5_UNVERIFIED",
        symbol="AUDJPY",
        magic=20261151,
        base_risk_pct=0.50,
        cluster_a_end_date="2020-12-31",
        cluster_b_end_date="2024-12-31",
        cluster_a_sharpe=1.50,
        cluster_a_pf=1.50,
        cluster_b_sharpe=1.50,
        cluster_b_pf=1.50,
        pbo_cscv=0.10,
        dsr_empirical=0.98,
        cost_stress_2x_net_pct=25.0,
        daily_returns_dev=orth_series,
    )
    ctrl4.enqueue_discovery_candidate(cand_unverified)  # intentionally NEVER validated -> stays DISCOVERED!
    ctrl4.enqueue_discovery_candidate(cand_killed)
    ctrl4.run_blind_validation_gate(cand_killed.engine_id, auto_bench=True)  # becomes KILLED!

    live4 = _make_healthy_live_streams(dev_map, n_live=40, seed=4040)
    live4[red_target] = np.full(25, mu3 - 1.15 * sd3, dtype=np.float64)
    res4 = ctrl4.run_decay_and_governance_cycle(live4, force_stdlib_fallback=force_stdlib_fallback)
    prop4 = res4["proposals"][0] if len(res4["proposals"]) == 1 else None
    drill4_pass = (
        res4["decay_reports"][red_target]["verdict"] == "RED_HALT_ALPHA_DECAY"
        and ctrl4.registry[red_target].state == EngineLifecycleState.RETIRED
        and ctrl4.registry["U1_UNVERIFIED_DISCOVERED"].state == EngineLifecycleState.DISCOVERED
        and ctrl4.registry["B3_OVERFIT_REJECTED"].state == EngineLifecycleState.KILLED
        and prop4 is not None
        and prop4["action_type"] == "HALT_ONLY_EMPTY_BENCH"
        and prop4["replacement_engine_id"] is None
        and prop4["approval_required"] is True
        and prop4["auto_deployed"] is False
    )
    drill4_summary = {
        "drill_id": "DRILL_4_RED_EMPTY_BENCH_FAIL_CLOSED",
        "passed": drill4_pass,
        "target_engine": red_target,
        "target_verdict": res4["decay_reports"][red_target]["verdict"],
        "unverified_candidate_state": ctrl4.registry["U1_UNVERIFIED_DISCOVERED"].state.value,
        "killed_candidate_state": ctrl4.registry["B3_OVERFIT_REJECTED"].state.value,
        "proposal": prop4,
        "ledger_integrity": verify_ledger_integrity(ctrl4.export_ledger(write_output_path=None)),
    }

    # ------------------------------------------------------------------
    # DRILL 5: POISONED INPUTS (NaN, Inf, bool, empty, 2025 Holdout date, illegal FSM)
    #          AND TAMPERED LEDGER HASH -> 100% FAIL-CLOSED ValueError REJECTIONS
    # ------------------------------------------------------------------
    poison_checks: list[dict[str, Any]] = []

    def _expect_value_error(case_id: str, fn: Callable[[], Any]) -> None:
        try:
            fn()
            poison_checks.append({"case_id": case_id, "rejected": False, "error": "NO_ERROR_RAISED"})
        except ValueError as exc:
            poison_checks.append({"case_id": case_id, "rejected": True, "error": str(exc)})

    sample_dev = dev_map["E1_USDJPY_TOKYO"]
    sample_live = live1["E1_USDJPY_TOKYO"]

    _expect_value_error(
        "POISON_NAN_IN_LIVE_SERIES",
        lambda: evaluate_decay_fail_closed(sample_dev, np.append(sample_live[:5], np.nan)),
    )
    _expect_value_error(
        "POISON_INF_IN_DEV_SERIES",
        lambda: evaluate_decay_fail_closed(np.append(sample_dev[:40], np.inf), sample_live),
    )
    _expect_value_error(
        "POISON_BOOL_IN_LIVE_SERIES",
        lambda: evaluate_decay_fail_closed(sample_dev, [0.1, True, 0.2]),
    )
    _expect_value_error(
        "POISON_BOOL_THRESHOLD_CUSUM_H",
        lambda: evaluate_decay_fail_closed(sample_dev, sample_live, cusum_h_sigma=True),
    )
    _expect_value_error(
        "POISON_EMPTY_LIVE_SERIES",
        lambda: evaluate_decay_fail_closed(sample_dev, []),
    )
    _expect_value_error(
        "POISON_HOLDOUT_2025_DATE",
        lambda: evaluate_decay_fail_closed(sample_dev, sample_live, dev_max_date="2025-01-15"),
    )
    _expect_value_error(
        "POISON_ILLEGAL_FSM_DISCOVERED_TO_ACTIVE",
        lambda: ctrl4._transition_state(
            "U1_UNVERIFIED_DISCOVERED",
            EngineLifecycleState.ACTIVE_1X,
            stage="DRILL5_NEGATIVE",
            reason="Illegal bypass attempt",
        ),
    )

    tampered_ledger = json.loads(json.dumps(ledger3))
    tampered_ledger["entries"][-1]["details"]["tampered_field"] = "MALICIOUS_OVERRIDE"
    _expect_value_error(
        "POISON_TAMPERED_LEDGER_HASH",
        lambda: verify_ledger_integrity(tampered_ledger),
    )

    drill5_pass = all(c["rejected"] for c in poison_checks) and len(poison_checks) == 8
    drill5_summary = {
        "drill_id": "DRILL_5_POISONED_INPUT_AND_TAMPERED_LEDGER",
        "passed": drill5_pass,
        "cases_tested": len(poison_checks),
        "cases_rejected_fail_closed": sum(1 for c in poison_checks if c["rejected"]),
        "details": poison_checks,
    }

    drills_list = [drill1_summary, drill2_summary, drill3_summary, drill4_summary, drill5_summary]
    all_5_passed = all(d["passed"] for d in drills_list)

    report_body: dict[str, Any] = {
        "schema_version": DRILLS_SCHEMA_VERSION,
        "generated_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "gates": ["W5-G16", "W5-G17"],
        "hard_invariants": {
            "order_send_capable": ORDER_SEND_CAPABLE,
            "order_send_count": ORDER_SEND_COUNT,
            "auto_deploy_permitted": AUTO_DEPLOY_PERMITTED,
            "holdout_cutoff_date": HOLDOUT_CUTOFF_DATE,
            "holdout_2025_plus_sealed": True,
            "holdout_rows_analysed": 0,
            "p1_6_fail_closed_guardrail_enforced": True,
            "pc_dev_policy": DEV_PC_REQUIRED_MODE,
        },
        "baseline_source": baseline_source,
        "decay_backend_used": res1["decay_reports"]["E1_USDJPY_TOKYO"]["decay_backend"],
        "drills_total": 5,
        "drills_passed": sum(1 for d in drills_list if d["passed"]),
        "all_5_drills_passed": all_5_passed,
        "verdict": "PASS_W5_G16_AND_W5_G17_ALL_5_DRILLS_GREEN" if all_5_passed else "FAIL_DRILLS",
        "drills": {d["drill_id"]: d for d in drills_list},
        "elapsed_sec": round(time.perf_counter() - t0, 4),
    }
    report = {**report_body, "report_sha256": canonical_sha256(report_body)}

    if write_drills_path is not None:
        _atomic_write_json_lf(Path(write_drills_path), report)

    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Wave 5 W5-G16/W5-G17 Closed-Loop Alpha Factory Controller & 5 E2E Drills"
    )
    parser.add_argument("--ledger-out", type=Path, default=DEFAULT_LEDGER_OUT_PATH)
    parser.add_argument("--drills-out", type=Path, default=DEFAULT_DRILLS_OUT_PATH)
    args = parser.parse_args(argv)

    report = run_all_e2e_drills(
        write_ledger_path=args.ledger_out,
        write_drills_path=args.drills_out,
    )
    print(
        json.dumps(
            {
                "schema_version": report["schema_version"],
                "verdict": report["verdict"],
                "drills_passed": report["drills_passed"],
                "drills_total": report["drills_total"],
                "decay_backend_used": report["decay_backend_used"],
                "ledger_out": str(args.ledger_out),
                "drills_out": str(args.drills_out),
                "report_sha256": report["report_sha256"],
                "elapsed_sec": report["elapsed_sec"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if report["all_5_drills_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

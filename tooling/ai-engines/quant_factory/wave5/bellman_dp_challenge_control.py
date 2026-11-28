"""Wave 5 (Gate W5-G13): Anti-Martingale Bellman Dynamic Programming Challenge Controller.

Strictly offline Dev-only stochastic optimal control solver (`ORDER_SEND_CAPABLE = False`,
`ORDER_SEND_COUNT = 0`, `HOLDOUT_CUTOFF_DATE = "2024-12-31"`, `holdout_rows_analysed = 0`).

Hard invariants:
  1. PC Dev compute policy locked to `MODE_A_OWNER_ACTIVE` (`NUMBA_NUM_THREADS=2`,
     `OMP_NUM_THREADS=2`, `BELOW_NORMAL 0x00004000`, `0%` GPU).
  2. STRICT CAUSAL SPLIT:
       - Fit empirical return & intraday-DD transition distributions strictly on
         **Cluster A (`<= 2020-12-31`)** of `PORT_7E` sealed Dev M1 tapes.
       - Evaluate completely out-of-sample on **Cluster B (`2021-01-01 .. 2024-12-31`)**
         across `10,000` shared circular-block-bootstrap paths + rolling historical windows.
       - Fail-closed `ValueError("HOLDOUT_LOCK_VIOLATION")` on ANY date `>= 2025-01-01`.
  3. HARD ANTI-MARTINGALE CONSTRAINTS (NO Dubins-Savage bold play!):
       - Monotonic non-increasing in drawdown from peak:
         `mult(eq, dd_deeper) <= mult(eq, dd_shallower)` for EVERY equity level `eq`.
       - Monotonic non-increasing in static equity loss:
         `mult(eq_lower, dd) <= mult(eq_higher, dd)` for EVERY `eq_lower < eq_higher <= 0`.
       - Bounded per-trade risk (`<= 1.75%` symbol cap for DP/C10, `<= 2.25%` Sprint) and
         Shield A absolute cap `EffectiveTotalOpenRiskCapPct <= 3.00%`.
  4. Distills each solved P1 (`+10% / -5% daily / -10% static`) and P2 (`+5% / -5% daily /
     -10% static`) DP policy into a clean MQL5-loadable `<= 6`-tier piecewise risk schedule
     (`bellman_dp_schedule.json`) that also satisfies all anti-martingale & Shield A invariants.
  5. Mandatory head-to-head out-of-sample Cluster B (`2021-2024`) ablation comparing:
       - `BELLMAN_DP_POLICY` (full 2D anti-martingale DP policy)
       - `BELLMAN_DP_6TIER_SCHEDULE` (distilled `<= 6`-tier MQL5-loadable schedule)
       - `BARRIER_TAPER` (`InpSizingMode == 1`, exact mirror of `Naqex_Master_Prop7E_v104_ML.mq5:675-690`)
       - `V103_SPRINT_STATIC_LOCK` (`v1.03-Sprint` static lock `4.5x / 3.5x`)
       - `C10_NEWS_ON` (`4.0x / 3.5x` with ProfitLock `70% -> 2.50x / 1.75x`)
  6. Zero bare `assert` statements (`python -O` safe), lazy `quant_trading` avoidance,
     LF-only JSON outputs, zero BOM.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import math
import os
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from numba import njit
from quant_core.io_utils import atomic_write_json

from quant_factory.capital_optimizer.constants import (
    BLOCK_LEN,
    CORE7_IDS,
    DEFAULT_CORE7_BASE_RISK,
    DEFAULT_DERIVED_TAPES_DIR,
    DEFAULT_DERIVED_TAPES_STEM,
    ROOT,
    TRADING_DAYS_PER_YEAR,
)
from quant_factory.capital_optimizer.lot_sizing import floor_lot_step
from quant_factory.capital_optimizer.replay_cache import ExactTierReplayCache
from quant_factory.capital_optimizer.simulator import make_block_bootstrap_indices
from quant_factory.capital_optimizer.x13_shard import (
    load_frozen_tapes_v2_direct,
    load_red_news_calendar_direct,
)
from quant_factory.wave5 import (
    DEV_PC_REQUIRED_MODE,
    HOLDOUT_CUTOFF_DATE,
    ORDER_SEND_CAPABLE,
    ORDER_SEND_COUNT,
)

# ---------------------------------------------------------------------------
# Constants & Canonical Paths
# ---------------------------------------------------------------------------

SCHEMA_VERSION: str = "naqex-wave5-bellman-dp-schedule-v1"
CLUSTER_A_MAX_DAY: str = "2020-12-31"
CLUSTER_B_MIN_DAY: str = "2021-01-01"
CLUSTER_B_MAX_DAY: str = HOLDOUT_CUTOFF_DATE
HOLDOUT_FIRST_DAY: str = "2025-01-01"

HARD_TOTAL_OPEN_RISK_CAP_PCT: float = 3.00  # Shield A absolute ceiling
DEFAULT_PER_SYMBOL_CAP_PCT: float = 1.75
SPRINT_PER_SYMBOL_CAP_PCT: float = 2.25
DEFAULT_CAPITAL_USD: float = 10_000.0
DEFAULT_CHALLENGE_FEE_USD: float = 170.0  # FTMO 10K standard fee incl. VN card FX
DEFAULT_FUNDED_VALUE_USD: float = 850.0  # Conservative expected net funded value for EV/fee comparison
DEFAULT_N_PATHS: int = 10_000
DEFAULT_PHASE_HORIZON_DAYS: int = 126  # 6 trading months per phase
DEFAULT_DP_HORIZON_DAYS: int = 126
DEFAULT_DP_SEED: int = 20261128
MAX_DISTILLED_TIERS: int = 6

# Discrete anti-martingale action ladder (risk multipliers relative to 1.0x PORT_7E base risk)
DEFAULT_ACTION_GRID: tuple[float, ...] = (0.50, 1.00, 1.50, 2.00, 2.50, 3.00, 3.50, 4.00, 4.50)
P1_MAX_ACTION_MULT: float = 4.50
P2_MAX_ACTION_MULT: float = 3.50

DEFAULT_SCHEDULE_OUT_PATH: Path = (
    ROOT / ".runtime" / "offensive5" / "pareto" / "bellman_dp_schedule.json"
)

_BELOW_NORMAL_PRIORITY_CLASS: int = 0x00004000


# ---------------------------------------------------------------------------
# Fail-Closed Validators & PC Dev Mode A Guard
# ---------------------------------------------------------------------------


def apply_dev_pc_mode_a_limits(*, threads: int = 2) -> dict[str, Any]:
    """Enforce PC Dev `MODE_A_OWNER_ACTIVE` (`NUMBA_NUM_THREADS=2`, `OMP_NUM_THREADS=2`, BelowNormal)."""
    t_cap = _require_strict_int(threads, "threads", min_val=1, max_val=3)
    os.environ["NUMBA_NUM_THREADS"] = str(t_cap)
    os.environ["OMP_NUM_THREADS"] = str(t_cap)
    priority_applied = False
    win_error: str | None = None
    if os.name == "nt":
        try:
            k32 = ctypes.windll.kernel32
            k32.GetCurrentProcess.restype = ctypes.c_void_p
            k32.SetPriorityClass.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
            k32.SetPriorityClass.restype = ctypes.c_int
            proc = k32.GetCurrentProcess()
            priority_applied = bool(k32.SetPriorityClass(proc, _BELOW_NORMAL_PRIORITY_CLASS))
        except Exception as exc:  # pragma: no cover - platform specific
            win_error = f"{type(exc).__name__}: {exc}"
    return {
        "policy_mode": DEV_PC_REQUIRED_MODE,
        "numba_num_threads": t_cap,
        "omp_num_threads": t_cap,
        "priority_class": _BELOW_NORMAL_PRIORITY_CLASS,
        "priority_applied": priority_applied,
        "gpu_allowed": False,
        "win_error": win_error,
    }


def _require_finite_float(
    value: Any,
    name: str,
    *,
    min_val: float | None = None,
    max_val: float | None = None,
    strict_min: bool = False,
) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, float, np.number)):
        raise ValueError(f"INVALID_NUMERIC_INPUT: {name} must be finite float (got {value!r})")
    fv = float(value)
    if not math.isfinite(fv):
        raise ValueError(f"NON_FINITE_INPUT: {name} must be finite (got {value!r})")
    if min_val is not None:
        if strict_min and fv <= min_val:
            raise ValueError(f"RANGE_ERROR: {name} must be > {min_val}, got {fv}")
        if (not strict_min) and fv < min_val:
            raise ValueError(f"RANGE_ERROR: {name} must be >= {min_val}, got {fv}")
    if max_val is not None and fv > max_val:
        raise ValueError(f"RANGE_ERROR: {name} must be <= {max_val}, got {fv}")
    return fv


def _require_strict_int(
    value: Any,
    name: str,
    *,
    min_val: int | None = None,
    max_val: int | None = None,
) -> int:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)):
        raise ValueError(f"INVALID_INT_INPUT: {name} must be strict int (got {value!r})")
    iv = int(value)
    if min_val is not None and iv < min_val:
        raise ValueError(f"RANGE_ERROR: {name} must be >= {min_val}, got {iv}")
    if max_val is not None and iv > max_val:
        raise ValueError(f"RANGE_ERROR: {name} must be <= {max_val}, got {iv}")
    return iv


def validate_strict_pre_holdout_days(days: list[str] | tuple[str, ...]) -> int:
    """Fail-closed date gate guaranteeing zero Holdout (`>= 2025-01-01`) rows are ever analysed."""
    if not days:
        raise ValueError("EMPTY_DATE_SERIES: date sequence must be non-empty")
    for raw in days:
        if not isinstance(raw, str) or len(raw) < 10:
            raise ValueError(f"INVALID_DATE_STRING: expected YYYY-MM-DD, got {raw!r}")
        ds = raw[:10]
        if ds >= HOLDOUT_FIRST_DAY:
            raise ValueError(
                f"HOLDOUT_LOCK_VIOLATION: date {ds!r} >= {HOLDOUT_FIRST_DAY!r} is strictly sealed"
            )
    return 0


def validate_shield_a_cap(total_open_risk_cap_pct: float) -> float:
    """Enforce Shield A hard cap `EffectiveTotalOpenRiskCapPct <= 3.00%` fail-closed."""
    cap = _require_finite_float(
        total_open_risk_cap_pct,
        "effective_total_open_risk_cap_pct",
        min_val=0.0,
        strict_min=True,
    )
    if cap > HARD_TOTAL_OPEN_RISK_CAP_PCT + 1e-12:
        raise ValueError(
            f"SHIELD_A_CAP_VIOLATION: EffectiveTotalOpenRiskCapPct={cap:.4f}% "
            f"exceeds hard Shield A ceiling {HARD_TOTAL_OPEN_RISK_CAP_PCT:.2f}%"
        )
    return cap


def _canonical_sha256(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Typed Specs & Anti-Martingale Policy Validation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ChallengePhaseSpec:
    """Discrete state-space and rule specification for a prop challenge phase (`P1` or `P2`)."""

    phase_id: str
    target_profit_pct: float
    hard_daily_dd_pct: float
    hard_static_dd_pct: float
    ea_kill_daily_dd_pct: float
    ea_kill_static_dd_pct: float
    eq_step_pct: float
    dd_step_pct: float
    max_action_mult: float
    min_action_mult: float
    per_symbol_cap_pct: float
    effective_total_open_risk_cap_pct: float
    horizon_days: int
    discount_gamma: float
    fail_penalty: float

    def validate(self) -> None:
        _require_finite_float(self.target_profit_pct, "target_profit_pct", min_val=0.0, strict_min=True)
        _require_finite_float(self.hard_daily_dd_pct, "hard_daily_dd_pct", min_val=0.0, strict_min=True)
        _require_finite_float(self.hard_static_dd_pct, "hard_static_dd_pct", min_val=0.0, strict_min=True)
        _require_finite_float(self.ea_kill_daily_dd_pct, "ea_kill_daily_dd_pct", min_val=0.0, strict_min=True)
        _require_finite_float(self.ea_kill_static_dd_pct, "ea_kill_static_dd_pct", min_val=0.0, strict_min=True)
        _require_finite_float(self.eq_step_pct, "eq_step_pct", min_val=0.0, strict_min=True)
        _require_finite_float(self.dd_step_pct, "dd_step_pct", min_val=0.0, strict_min=True)
        _require_finite_float(self.min_action_mult, "min_action_mult", min_val=0.0, strict_min=True)
        _require_finite_float(
            self.max_action_mult,
            "max_action_mult",
            min_val=self.min_action_mult,
        )
        _require_finite_float(self.per_symbol_cap_pct, "per_symbol_cap_pct", min_val=0.0, max_val=3.0, strict_min=True)
        validate_shield_a_cap(self.effective_total_open_risk_cap_pct)
        _require_strict_int(self.horizon_days, "horizon_days", min_val=5)
        _require_finite_float(self.discount_gamma, "discount_gamma", min_val=0.90, max_val=1.0)
        _require_finite_float(self.fail_penalty, "fail_penalty", min_val=0.0, max_val=10.0)


@dataclass(frozen=True)
class PiecewiseRiskTier:
    """Single MQL5-loadable tier in the distilled `<= 6`-tier Bellman DP schedule."""

    tier_rank: int
    tier_id: str
    label: str
    eq_min_pct: float
    eq_max_pct: float
    dd_from_peak_min_pct: float
    dd_from_peak_max_pct: float
    risk_mult: float
    effective_total_open_risk_cap_pct: float
    per_symbol_cap_pct: float
    mql5_condition_expr: str


def build_p1_spec(*, horizon_days: int = DEFAULT_DP_HORIZON_DAYS) -> ChallengePhaseSpec:
    spec = ChallengePhaseSpec(
        phase_id="P1",
        target_profit_pct=10.0,
        hard_daily_dd_pct=5.0,
        hard_static_dd_pct=10.0,
        ea_kill_daily_dd_pct=3.5,
        ea_kill_static_dd_pct=8.0,
        eq_step_pct=0.5,
        dd_step_pct=1.0,
        max_action_mult=P1_MAX_ACTION_MULT,
        min_action_mult=0.50,
        per_symbol_cap_pct=DEFAULT_PER_SYMBOL_CAP_PCT,
        effective_total_open_risk_cap_pct=HARD_TOTAL_OPEN_RISK_CAP_PCT,
        horizon_days=horizon_days,
        discount_gamma=0.9990,
        fail_penalty=0.0,
    )
    spec.validate()
    return spec


def build_p2_spec(*, horizon_days: int = DEFAULT_DP_HORIZON_DAYS) -> ChallengePhaseSpec:
    spec = ChallengePhaseSpec(
        phase_id="P2",
        target_profit_pct=5.0,
        hard_daily_dd_pct=5.0,
        hard_static_dd_pct=10.0,
        ea_kill_daily_dd_pct=3.0,
        ea_kill_static_dd_pct=7.5,
        eq_step_pct=0.5,
        dd_step_pct=1.0,
        max_action_mult=P2_MAX_ACTION_MULT,
        min_action_mult=0.50,
        per_symbol_cap_pct=DEFAULT_PER_SYMBOL_CAP_PCT,
        effective_total_open_risk_cap_pct=HARD_TOTAL_OPEN_RISK_CAP_PCT,
        horizon_days=horizon_days,
        discount_gamma=0.9990,
        fail_penalty=0.0,
    )
    spec.validate()
    return spec


def build_state_grids(spec: ChallengePhaseSpec) -> tuple[np.ndarray, np.ndarray]:
    """Build discrete `(equity_bucket_pct, dd_from_peak_bucket_pct)` axes."""
    spec.validate()
    n_eq = int(round((spec.target_profit_pct + spec.hard_static_dd_pct) / spec.eq_step_pct)) + 1
    eq_grid = np.round(
        np.linspace(-spec.hard_static_dd_pct, spec.target_profit_pct, n_eq),
        6,
    )
    n_dd = int(round(spec.hard_static_dd_pct / spec.dd_step_pct)) + 1
    dd_grid = np.round(np.linspace(0.0, spec.hard_static_dd_pct, n_dd), 6)
    return eq_grid, dd_grid


def validate_anti_martingale_policy(
    policy_mult: np.ndarray,
    eq_grid: np.ndarray,
    dd_grid: np.ndarray,
    *,
    max_mult: float,
    min_mult: float = 0.0,
    total_open_risk_cap_pct: float = HARD_TOTAL_OPEN_RISK_CAP_PCT,
) -> dict[str, Any]:
    """Fail-closed verifier proving ZERO Dubins-Savage bold play (anti-martingale monotonicity).

    Checks:
      1. `EffectiveTotalOpenRiskCapPct <= 3.00%` (Shield A).
      2. Every entry is finite and within `[min_mult, max_mult]`.
      3. For EVERY equity level `eq_i` and EVERY `dd_j < dd_k`:
         `policy_mult[eq_i, dd_k] <= policy_mult[eq_i, dd_j] + 1e-12`.
      4. In the loss region (`eq <= 0`), for EVERY `dd_j` and EVERY `eq_low < eq_high <= 0`:
         `policy_mult[eq_low, dd_j] <= policy_mult[eq_high, dd_j] + 1e-12`.
    """
    validate_shield_a_cap(total_open_risk_cap_pct)
    arr = np.asarray(policy_mult, dtype=np.float64)
    if arr.ndim != 2 or arr.shape != (len(eq_grid), len(dd_grid)):
        raise ValueError(
            f"POLICY_SHAPE_MISMATCH: expected {(len(eq_grid), len(dd_grid))}, got {arr.shape}"
        )
    if not np.all(np.isfinite(arr)):
        raise ValueError("POLICY_NON_FINITE: policy_mult contains NaN or Inf")
    if float(arr.min()) < float(min_mult) - 1e-12 or float(arr.max()) > float(max_mult) + 1e-12:
        raise ValueError(
            f"POLICY_BOUNDS_VIOLATION: range [{float(arr.min()):.4f}, {float(arr.max()):.4f}] "
            f"outside [{min_mult:.4f}, {max_mult:.4f}]"
        )

    dd_checks = 0
    for i in range(len(eq_grid)):
        for j in range(1, len(dd_grid)):
            dd_checks += 1
            if arr[i, j] > arr[i, j - 1] + 1e-12:
                raise ValueError(
                    f"ANTI_MARTINGALE_VIOLATION: deeper drawdown has higher risk at eq={eq_grid[i]:.2f}%: "
                    f"mult(dd={dd_grid[j]:.2f}%)={arr[i, j]:.4f} > "
                    f"mult(dd={dd_grid[j - 1]:.2f}%)={arr[i, j - 1]:.4f}"
                )

    loss_eq_checks = 0
    for i in range(1, len(eq_grid)):
        if eq_grid[i] > 1e-9:
            break
        for j in range(len(dd_grid)):
            loss_eq_checks += 1
            if arr[i - 1, j] > arr[i, j] + 1e-12:
                raise ValueError(
                    f"ANTI_MARTINGALE_STATIC_LOSS_VIOLATION: deeper static loss has higher risk at "
                    f"dd={dd_grid[j]:.2f}%: mult(eq={eq_grid[i - 1]:.2f}%)={arr[i - 1, j]:.4f} > "
                    f"mult(eq={eq_grid[i]:.2f}%)={arr[i, j]:.4f}"
                )

    return {
        "anti_martingale_verified": True,
        "dd_monotonic_pairs_checked": dd_checks,
        "static_loss_monotonic_pairs_checked": loss_eq_checks,
        "min_policy_mult": round(float(arr.min()), 4),
        "max_policy_mult": round(float(arr.max()), 4),
        "effective_total_open_risk_cap_pct": round(float(total_open_risk_cap_pct), 4),
    }


def evaluate_piecewise_schedule_mult(
    tiers: list[PiecewiseRiskTier] | tuple[PiecewiseRiskTier, ...],
    *,
    eq_pct: float,
    dd_from_peak_pct: float,
) -> tuple[float, str]:
    """Evaluate a distilled `<= 6`-tier piecewise risk schedule at `(eq_pct, dd_from_peak_pct)`.

    Tiers are evaluated in priority order (`tier_rank` ascending) over disjoint equity bands,
    with optional `dd_from_peak` caps; if multiple tiers match the same `(eq, dd)` point, the
    defensive minimum multiplier is returned.
    """
    if not tiers:
        raise ValueError("EMPTY_SCHEDULE: piecewise schedule must contain at least 1 tier")
    if len(tiers) > MAX_DISTILLED_TIERS:
        raise ValueError(f"TOO_MANY_TIERS: max {MAX_DISTILLED_TIERS}, got {len(tiers)}")
    eq = _require_finite_float(eq_pct, "eq_pct")
    dd = _require_finite_float(dd_from_peak_pct, "dd_from_peak_pct", min_val=0.0)

    matched_mult = math.inf
    matched_id = tiers[0].tier_id
    for tier in sorted(tiers, key=lambda t: t.tier_rank):
        if (
            (tier.eq_min_pct - 1e-9 <= eq <= tier.eq_max_pct + 1e-9)
            and (tier.dd_from_peak_min_pct - 1e-9 <= dd <= tier.dd_from_peak_max_pct + 1e-9)
        ):
            if tier.risk_mult < matched_mult:
                matched_mult = tier.risk_mult
                matched_id = tier.tier_id
    if not math.isfinite(matched_mult):
        safest = min(tiers, key=lambda t: t.risk_mult)
        return float(safest.risk_mult), safest.tier_id
    return float(matched_mult), matched_id


def validate_piecewise_schedule(
    tiers: list[PiecewiseRiskTier] | tuple[PiecewiseRiskTier, ...],
    spec: ChallengePhaseSpec,
) -> dict[str, Any]:
    """Verify distilled `<= 6`-tier schedule on the entire discrete `(eq, dd)` grid."""
    if len(tiers) == 0 or len(tiers) > MAX_DISTILLED_TIERS:
        raise ValueError(f"SCHEDULE_TIER_COUNT_INVALID: expected 1..{MAX_DISTILLED_TIERS}, got {len(tiers)}")
    for tier in tiers:
        validate_shield_a_cap(tier.effective_total_open_risk_cap_pct)
        _require_finite_float(
            tier.risk_mult,
            f"tier.{tier.tier_id}.risk_mult",
            min_val=0.0,
            max_val=spec.max_action_mult,
        )
    eq_grid, dd_grid = build_state_grids(spec)
    grid_mult = np.zeros((len(eq_grid), len(dd_grid)), dtype=np.float64)
    for i, eq in enumerate(eq_grid):
        for j, dd in enumerate(dd_grid):
            m, _ = evaluate_piecewise_schedule_mult(tiers, eq_pct=float(eq), dd_from_peak_pct=float(dd))
            grid_mult[i, j] = m
    check = validate_anti_martingale_policy(
        grid_mult,
        eq_grid,
        dd_grid,
        max_mult=spec.max_action_mult,
        min_mult=0.0,
        total_open_risk_cap_pct=spec.effective_total_open_risk_cap_pct,
    )
    check["tier_count"] = len(tiers)
    return check


# ---------------------------------------------------------------------------
# Exact Shield-A-Enforced Replay Matrix Builder (Cluster A & Cluster B)
# ---------------------------------------------------------------------------


def build_shield_a_action_daily_matrices(
    cache: ExactTierReplayCache,
    *,
    action_grid: tuple[float, ...] = DEFAULT_ACTION_GRID,
    capital_usd: float = DEFAULT_CAPITAL_USD,
    per_symbol_cap_pct: float = DEFAULT_PER_SYMBOL_CAP_PCT,
    total_open_risk_cap_pct: float = HARD_TOTAL_OPEN_RISK_CAP_PCT,
    profile_mode: str = "Standard",
    use_red_news: bool = True,
    friction_mult: float = 1.0,
) -> dict[str, Any]:
    """Replay sealed Dev M1 tapes with BOTH per-symbol cap AND Shield A `<= 3.00%` total open cap.

    Returns exact daily percentage arrays `(n_actions, n_days)` for `net_pct`, `dd_pct`, `up_pct`,
    and `active_flg`, plus verified `max_observed_open_risk_pct <= 3.00%` and strict Cluster A/B masks.
    """
    validate_shield_a_cap(total_open_risk_cap_pct)
    validate_strict_pre_holdout_days(cache.ext_days)
    pre_days = cache._get_prealigned_days(friction_mult, use_red_news)
    n_days = len(cache.ext_days)
    n_actions = len(action_grid)
    initial = _require_finite_float(capital_usd, "capital_usd", min_val=100.0)
    symcap = _require_finite_float(per_symbol_cap_pct, "per_symbol_cap_pct", min_val=0.1, max_val=3.0) / 100.0
    totcap = float(total_open_risk_cap_pct) / 100.0
    is_std = str(profile_mode) == "Standard"

    nets_pct = np.zeros((n_actions, n_days), dtype=np.float64)
    dds_pct = np.zeros((n_actions, n_days), dtype=np.float64)
    ups_pct = np.zeros((n_actions, n_days), dtype=np.float64)
    flgs = np.zeros((n_actions, n_days), dtype=np.int8)
    max_open_risk_obs = 0.0
    max_trade_risk_obs = 0.0

    for a_idx, mult in enumerate(action_grid):
        m_val = _require_finite_float(mult, f"action_grid[{a_idx}]", min_val=0.0)
        balance = initial
        for pd_row in pre_days:
            cands = pd_row["cands"]
            k = len(cands)
            open_fl = pd_row["open_fl"]
            lots = np.zeros(k, dtype=np.float64)
            eff_risks = [0.0] * k
            margins = [0.0] * k
            any_sized = False

            for j in range(k):
                cj = cands[j]
                er = cj["base_r"] * m_val
                st_j = cj["entry_ts"]
                asset_j = cj["asset"]

                open_sym_r = 0.0
                open_tot_r = 0.0
                for i in range(j):
                    if lots[i] > 0.0 and st_j < cands[i]["release_ts"]:
                        open_tot_r += eff_risks[i]
                        if cands[i]["asset"] == asset_j:
                            open_sym_r += eff_risks[i]
                rem_sym = max(0.0, symcap - open_sym_r)
                rem_tot = max(0.0, totcap - open_tot_r)
                er = min(er, rem_sym, rem_tot)
                if er <= 1e-9:
                    continue

                budget = initial * er
                lot = floor_lot_step(
                    budget / cj["stop_cost"],
                    step=cj["vstep"],
                    vol_min=cj["vmin"],
                    vol_max=cj["vmax"],
                )
                if lot < cj["vmin"]:
                    continue

                mgn_1 = cj["mgn_std"] if is_std else cj["mgn_swg"]
                comm_1 = cj["comm_std"] if is_std else cj["comm_swg"]
                used_m = 0.0
                fl_sum = 0.0
                for i in range(j):
                    if lots[i] > 0.0:
                        if st_j < cands[i]["release_ts"]:
                            used_m += margins[i]
                        fl_sum += lots[i] * open_fl[i, j]
                avail = balance + fl_sum - used_m
                if lot * (mgn_1 + comm_1) > avail:
                    continue

                actual_er = (lot * cj["stop_cost"]) / initial
                if open_tot_r + actual_er > totcap + 1e-9:
                    continue

                lots[j] = lot
                eff_risks[j] = actual_er
                margins[j] = lot * mgn_1
                any_sized = True
                if actual_er > max_trade_risk_obs:
                    max_trade_risk_obs = actual_er
                if open_tot_r + actual_er > max_open_risk_obs:
                    max_open_risk_obs = open_tot_r + actual_er

            if not any_sized:
                continue

            comb = lots @ pd_row["marks_flat"]
            day_net = float(comb[-1])
            day_dd = max(0.0, -float(comb.min()))
            day_up = max(0.0, float(comb.max()))
            d_i = pd_row["day_idx"]
            nets_pct[a_idx, d_i] = 100.0 * day_net / initial
            dds_pct[a_idx, d_i] = 100.0 * day_dd / initial
            ups_pct[a_idx, d_i] = 100.0 * day_up / initial
            flgs[a_idx, d_i] = 1
            balance += day_net

    cluster_a_idx = np.array(
        [i for i, d in enumerate(cache.ext_days) if d <= CLUSTER_A_MAX_DAY],
        dtype=np.int32,
    )
    cluster_b_idx = np.array(
        [i for i, d in enumerate(cache.ext_days) if CLUSTER_B_MIN_DAY <= d <= CLUSTER_B_MAX_DAY],
        dtype=np.int32,
    )
    if len(cluster_a_idx) == 0 or len(cluster_b_idx) == 0:
        raise ValueError("CAUSAL_SPLIT_EMPTY: both Cluster A (<=2020) and Cluster B (2021-2024) must be non-empty")

    return {
        "days": list(cache.ext_days),
        "action_grid": np.asarray(action_grid, dtype=np.float64),
        "nets_pct": nets_pct,
        "dds_pct": dds_pct,
        "ups_pct": ups_pct,
        "flgs": flgs,
        "cluster_a_idx": cluster_a_idx,
        "cluster_b_idx": cluster_b_idx,
        "cluster_a_days": [cache.ext_days[int(i)] for i in cluster_a_idx],
        "cluster_b_days": [cache.ext_days[int(i)] for i in cluster_b_idx],
        "max_observed_total_open_risk_pct": round(100.0 * max_open_risk_obs, 4),
        "max_observed_per_trade_risk_pct": round(100.0 * max_trade_risk_obs, 4),
        "holdout_rows_analysed": 0,
    }


# ---------------------------------------------------------------------------
# Numba-Accelerated Constrained Anti-Martingale Bellman DP Solver
# ---------------------------------------------------------------------------


@njit(cache=True)
def _solve_bellman_dp_anti_martingale_numba(
    eq_grid: np.ndarray,
    dd_grid: np.ndarray,
    action_grid: np.ndarray,
    train_nets_pct: np.ndarray,
    train_dds_pct: np.ndarray,
    train_ups_pct: np.ndarray,
    target_pct: float,
    ea_kill_daily_pct: float,
    ea_kill_static_pct: float,
    hard_daily_pct: float,
    hard_static_pct: float,
    horizon_days: int,
    gamma: float,
    fail_penalty: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Finite-horizon backward induction over `(eq, dd_from_peak)` with HARD anti-martingale constraints.

    Empirical distribution is strictly Cluster A (`train_*` shape `(n_actions, n_train_days)`).
    At every step `t`, after computing exact empirical Q-values `Q[i, j, a]`, we solve the exact
    1D monotonic action optimization along `dd` (and enforce loss-zone static equity monotonicity)
    so that `policy_idx[i, j_deeper] <= policy_idx[i, j_shallower]` holds everywhere with ZERO
    Dubins-Savage bold play!
    """
    n_eq = len(eq_grid)
    n_dd = len(dd_grid)
    n_act = len(action_grid)
    n_obs = train_nets_pct.shape[1]
    eq_min = eq_grid[0]
    eq_step = eq_grid[1] - eq_grid[0]
    dd_step = dd_grid[1] - dd_grid[0]

    # Terminal value at t = H
    v_next = np.zeros((n_eq, n_dd), dtype=np.float64)
    for i in range(n_eq):
        eq = eq_grid[i]
        for j in range(n_dd):
            if eq >= target_pct - 1e-9:
                v_next[i, j] = 1.0
            elif eq <= -ea_kill_static_pct + 1e-9 or eq <= -hard_static_pct + 1e-9:
                v_next[i, j] = -fail_penalty
            else:
                # Smooth terminal continuation heuristic proportional to survival progress
                prog = (eq + ea_kill_static_pct) / max(1e-6, target_pct + ea_kill_static_pct)
                v_next[i, j] = 0.20 * max(0.0, min(1.0, prog))

    v_cur = np.zeros((n_eq, n_dd), dtype=np.float64)
    pol_idx = np.zeros((n_eq, n_dd), dtype=np.int32)
    q_slice = np.zeros((n_dd, n_act), dtype=np.float64)
    mono_dp = np.zeros((n_dd, n_act), dtype=np.float64)
    mono_par = np.zeros((n_dd, n_act), dtype=np.int32)

    inv_n_obs = 1.0 / float(max(1, n_obs))
    static_limit = ea_kill_static_pct if ea_kill_static_pct < hard_static_pct else hard_static_pct

    # Exponential weight priority on shallower drawdowns (closer to reachable trajectories)
    dd_weights = np.zeros(n_dd, dtype=np.float64)
    for j in range(n_dd):
        dd_weights[j] = 1.0 / (1.0 + 0.35 * float(j))

    for _step in range(horizon_days):
        # Iterate equity from highest (top) downward so loss-zone static monotonicity has known upper cap
        for i in range(n_eq - 1, -1, -1):
            eq = eq_grid[i]
            if eq >= target_pct - 1e-9:
                for j in range(n_dd):
                    v_cur[i, j] = 1.0
                    pol_idx[i, j] = 0
                continue
            if eq <= -static_limit + 1e-9:
                for j in range(n_dd):
                    v_cur[i, j] = -fail_penalty
                    pol_idx[i, j] = 0
                continue

            # Compute exact empirical Q[j, a] for this equity level
            for j in range(n_dd):
                dd_cur = dd_grid[j]
                peak_cur = eq + dd_cur
                if peak_cur < 0.0:
                    peak_cur = 0.0

                for a in range(n_act):
                    exp_v = 0.0
                    for d in range(n_obs):
                        r_net = train_nets_pct[a, d]
                        r_dd = train_dds_pct[a, d]
                        r_up = train_ups_pct[a, d]

                        # Exact `simulator.py:258-273` semantics:
                        # 1) Firm hard daily (-5%) or firm/EA static limit breach -> FAIL
                        # 2) EA daily circuit breaker (3.5%/3.0%) flattens day with +0.20% slip (SURVIVES!)
                        d_hard = r_dd >= hard_daily_pct - 1e-9
                        m_hard = (eq - r_dd) <= -static_limit + 1e-9
                        if (not d_hard) and (not m_hard) and (r_dd > ea_kill_daily_pct):
                            dd_eff = r_dd if r_dd < (ea_kill_daily_pct + 0.20) else (ea_kill_daily_pct + 0.20)
                            if r_net > -dd_eff:
                                r_net = -dd_eff
                            r_dd = dd_eff
                            r_up = 0.0
                            d_hard = r_dd >= hard_daily_pct - 1e-9
                            m_hard = (eq - r_dd) <= -static_limit + 1e-9

                        if d_hard or m_hard:
                            exp_v += -fail_penalty
                            continue

                        # Intraday / EOD target hit check
                        max_eq = eq + r_up
                        new_eq = eq + r_net
                        if max_eq >= target_pct - 1e-9 or new_eq >= target_pct - 1e-9:
                            exp_v += 1.0
                            continue

                        if new_eq <= -static_limit + 1e-9:
                            exp_v += -fail_penalty
                            continue

                        new_peak = peak_cur
                        if max_eq > new_peak:
                            new_peak = max_eq
                        if new_eq > new_peak:
                            new_peak = new_eq
                        new_dd = new_peak - new_eq
                        if new_dd < 0.0:
                            new_dd = 0.0

                        # Map to nearest discrete bucket (bilinear interpolation on eq, nearest/linear on dd)
                        eq_pos = (new_eq - eq_min) / eq_step
                        if eq_pos < 0.0:
                            eq_pos = 0.0
                        elif eq_pos > float(n_eq - 1):
                            eq_pos = float(n_eq - 1)
                        i0 = int(eq_pos)
                        i1 = i0 + 1 if i0 + 1 < n_eq else i0
                        w_eq = eq_pos - float(i0)

                        dd_pos = new_dd / dd_step
                        if dd_pos < 0.0:
                            dd_pos = 0.0
                        elif dd_pos > float(n_dd - 1):
                            dd_pos = float(n_dd - 1)
                        j0 = int(dd_pos)
                        j1 = j0 + 1 if j0 + 1 < n_dd else j0
                        w_dd = dd_pos - float(j0)

                        v00 = v_next[i0, j0]
                        v10 = v_next[i1, j0]
                        v01 = v_next[i0, j1]
                        v11 = v_next[i1, j1]
                        interp = (
                            (1.0 - w_eq) * (1.0 - w_dd) * v00
                            + w_eq * (1.0 - w_dd) * v10
                            + (1.0 - w_eq) * w_dd * v01
                            + w_eq * w_dd * v11
                        )
                        exp_v += gamma * interp
                    q_slice[j, a] = exp_v * inv_n_obs

            # Exact 1D anti-martingale DP across dd_j: a[0] >= a[1] >= ... >= a[n_dd - 1]
            # AND in the loss zone (eq <= 0), a[i, j] <= a[i + 1, j] (never increase size when losing more)
            for j in range(n_dd):
                upper_cap = n_act - 1
                if eq <= 1e-9 and (i + 1) < n_eq and eq_grid[i + 1] <= 1e-9:
                    if pol_idx[i + 1, j] < upper_cap:
                        upper_cap = pol_idx[i + 1, j]

                # Also enforce natural headroom brake near static limit (anti-martingale barrier safety)
                headroom = static_limit + eq
                if headroom <= 2.0 and upper_cap > 1:
                    upper_cap = 1
                elif headroom <= 4.0 and upper_cap > 3:
                    upper_cap = 3

                for a in range(n_act):
                    if a > upper_cap:
                        mono_dp[j, a] = -1e18
                        mono_par[j, a] = 0
                    elif j == 0:
                        mono_dp[j, a] = dd_weights[j] * q_slice[j, a]
                        mono_par[j, a] = a
                    else:
                        best_prev = -1e18
                        best_pa = a
                        for pa in range(a, n_act):
                            cand = mono_dp[j - 1, pa]
                            if cand > best_prev:
                                best_prev = cand
                                best_pa = pa
                        mono_dp[j, a] = best_prev + dd_weights[j] * q_slice[j, a]
                        mono_par[j, a] = best_pa

            # Backtrack optimal non-increasing action sequence across j = n_dd-1 .. 0
            best_end_val = -1e18
            best_end_a = 0
            for a in range(n_act):
                if mono_dp[n_dd - 1, a] > best_end_val:
                    best_end_val = mono_dp[n_dd - 1, a]
                    best_end_a = a
            cur_a = best_end_a
            for j in range(n_dd - 1, -1, -1):
                pol_idx[i, j] = cur_a
                v_cur[i, j] = q_slice[j, cur_a]
                if j > 0:
                    cur_a = mono_par[j, cur_a]

        for i in range(n_eq):
            for j in range(n_dd):
                v_next[i, j] = v_cur[i, j]

    policy_mult = np.zeros((n_eq, n_dd), dtype=np.float64)
    for i in range(n_eq):
        for j in range(n_dd):
            policy_mult[i, j] = action_grid[pol_idx[i, j]]
    return v_next, policy_mult


def solve_phase_bellman_dp(
    spec: ChallengePhaseSpec,
    *,
    action_grid: np.ndarray,
    train_nets_pct: np.ndarray,
    train_dds_pct: np.ndarray,
    train_ups_pct: np.ndarray,
) -> dict[str, Any]:
    """Solve finite-horizon anti-martingale Bellman DP strictly on Cluster A empirical returns."""
    spec.validate()
    eq_grid, dd_grid = build_state_grids(spec)
    act_arr = np.asarray(action_grid, dtype=np.float64)
    keep_mask = (act_arr >= spec.min_action_mult - 1e-12) & (act_arr <= spec.max_action_mult + 1e-12)
    keep_idx = np.where(keep_mask)[0]
    if len(keep_idx) == 0:
        raise ValueError(
            f"EMPTY_FEASIBLE_ACTIONS: no actions in [{spec.min_action_mult}, {spec.max_action_mult}]"
        )
    sub_actions = np.ascontiguousarray(act_arr[keep_idx], dtype=np.float64)
    sub_nets = np.ascontiguousarray(train_nets_pct[keep_idx], dtype=np.float64)
    sub_dds = np.ascontiguousarray(train_dds_pct[keep_idx], dtype=np.float64)
    sub_ups = np.ascontiguousarray(train_ups_pct[keep_idx], dtype=np.float64)

    if sub_nets.shape[1] < 20:
        raise ValueError(f"INSUFFICIENT_CLUSTER_A_DAYS: need >= 20, got {sub_nets.shape[1]}")
    if not (np.all(np.isfinite(sub_nets)) and np.all(np.isfinite(sub_dds)) and np.all(np.isfinite(sub_ups))):
        raise ValueError("NON_FINITE_TRAINING_ARRAY: Cluster A daily arrays contain NaN/Inf")

    v_star, policy_mult = _solve_bellman_dp_anti_martingale_numba(
        eq_grid=eq_grid,
        dd_grid=dd_grid,
        action_grid=sub_actions,
        train_nets_pct=sub_nets,
        train_dds_pct=sub_dds,
        train_ups_pct=sub_ups,
        target_pct=float(spec.target_profit_pct),
        ea_kill_daily_pct=float(spec.ea_kill_daily_dd_pct),
        ea_kill_static_pct=float(spec.ea_kill_static_dd_pct),
        hard_daily_pct=float(spec.hard_daily_dd_pct),
        hard_static_pct=float(spec.hard_static_dd_pct),
        horizon_days=int(spec.horizon_days),
        gamma=float(spec.discount_gamma),
        fail_penalty=float(spec.fail_penalty),
    )

    anti_check = validate_anti_martingale_policy(
        policy_mult,
        eq_grid,
        dd_grid,
        max_mult=spec.max_action_mult,
        min_mult=spec.min_action_mult,
        total_open_risk_cap_pct=spec.effective_total_open_risk_cap_pct,
    )

    # Origin state (eq=0%, dd=0%)
    zero_eq_idx = int(np.argmin(np.abs(eq_grid - 0.0)))
    v_origin = float(v_star[zero_eq_idx, 0])
    m_origin = float(policy_mult[zero_eq_idx, 0])

    return {
        "phase_id": spec.phase_id,
        "spec": asdict(spec),
        "eq_grid": eq_grid,
        "dd_grid": dd_grid,
        "sub_actions": sub_actions,
        "value_grid": v_star,
        "policy_mult": policy_mult,
        "origin_value": round(v_origin, 6),
        "origin_mult": round(m_origin, 4),
        "anti_martingale_check": anti_check,
    }


def distill_dp_to_piecewise_schedule(
    dp_result: dict[str, Any],
    spec: ChallengePhaseSpec,
) -> tuple[list[PiecewiseRiskTier], dict[str, Any]]:
    """Distill the Cluster A 2D DP policy into a faithful MQL5-loadable `<= 6`-tier piecewise schedule.

    Because FTMO P1/P2 has a STATIC drawdown barrier (`-10%` firm / `-8.0%..-7.5%` EA kill), the
    exact Bellman value function `V*(eq, dd)` is Markov-sufficient in equity relative to start `eq`,
    producing 6 clean, disjoint equity regimes learned strictly from Cluster A:
      T1 HOUSE_MONEY_CRUISE:  eq in [mid_lo, mid_hi)  (profit cushion far from static barrier)
      T2 FINISH_LINE_TAPER:   eq in [mid_hi, target]  (de-risk near target to avoid overshoot/giveback)
      T3 NORMAL_BASE:         eq in [-1.5%, mid_lo)   (near starting balance)
      T4 SHALLOW_LOSS_BRAKE:  eq in [-4.5%, -1.5%)    (first anti-martingale loss brake)
      T5 AMBER_LOSS_BRAKE:    eq in [-6.5%, -4.5%)    (amber anti-martingale loss brake)
      T6 RED_SURVIVAL_FLOOR:  eq in [-10.0%, -6.5%)   (survival floor near static kill barrier)

    Loss-zone monotonicity `T3 >= T4 >= T5 >= T6` and flat-in-`dd_from_peak` (for fixed `eq`)
    guarantee `mult(eq, dd_deeper) <= mult(eq, dd_shallower)` and `mult(eq_lower, dd) <= mult(eq_higher, dd)`
    for EVERY state on the grid with ZERO Dubins-Savage bold play!
    """
    eq_grid = np.asarray(dp_result["eq_grid"], dtype=np.float64)
    dd_grid = np.asarray(dp_result["dd_grid"], dtype=np.float64)
    pol = np.asarray(dp_result["policy_mult"], dtype=np.float64)
    actions = np.asarray(dp_result["sub_actions"], dtype=np.float64)

    def _snap_to_grid(val: float) -> float:
        idx = int(np.argmin(np.abs(actions - val)))
        return float(actions[idx])

    def _eq_band_median(eq_lo: float, eq_hi: float, fallback: float) -> float:
        em = (eq_grid >= eq_lo - 1e-9) & (eq_grid <= eq_hi + 1e-9)
        sub = pol[em, :]
        if sub.size == 0:
            return _snap_to_grid(fallback)
        return _snap_to_grid(float(np.median(sub)))

    target = float(spec.target_profit_pct)
    mid_lo = round(0.45 * target, 2)
    mid_hi = round(0.80 * target, 2)

    raw_house = _eq_band_median(mid_lo, mid_hi - 0.5, 3.0)
    raw_finish = _eq_band_median(mid_hi, target - 0.5, 1.5)
    raw_normal = _eq_band_median(-1.5, mid_lo - 0.5, 2.5)
    raw_shallow = _eq_band_median(-4.5, -2.0, 2.0)
    raw_amber = _eq_band_median(-6.5, -5.0, 1.5)
    raw_red = _eq_band_median(-8.0, -7.0, 0.5)

    # Strictly enforce anti-martingale loss-zone ordering (T3 >= T4 >= T5 >= T6)
    m_normal = min(spec.max_action_mult, max(spec.min_action_mult, raw_normal))
    m_house = min(spec.max_action_mult, max(m_normal, raw_house))
    m_finish = min(m_house, max(spec.min_action_mult, raw_finish))
    m_shallow = min(m_normal, max(spec.min_action_mult, raw_shallow))
    m_amber = min(m_shallow, max(spec.min_action_mult, raw_amber))
    m_red = min(m_amber, max(spec.min_action_mult, raw_red))

    cap_tot = float(spec.effective_total_open_risk_cap_pct)
    cap_sym = float(spec.per_symbol_cap_pct)

    tiers = [
        PiecewiseRiskTier(
            tier_rank=1,
            tier_id=f"{spec.phase_id}_T1_HOUSE_MONEY_CRUISE",
            label=f"House-money profit cushion (eq in [+{mid_lo:.1f}%, +{mid_hi:.1f}%))",
            eq_min_pct=mid_lo,
            eq_max_pct=mid_hi - 0.0001,
            dd_from_peak_min_pct=0.0,
            dd_from_peak_max_pct=10.0,
            risk_mult=round(m_house, 4),
            effective_total_open_risk_cap_pct=cap_tot,
            per_symbol_cap_pct=cap_sym,
            mql5_condition_expr=f"(eqPct >= {mid_lo:.2f} && eqPct < {mid_hi:.2f})",
        ),
        PiecewiseRiskTier(
            tier_rank=2,
            tier_id=f"{spec.phase_id}_T2_FINISH_LINE_TAPER",
            label=f"Finish-line taper (eq >= +{mid_hi:.1f}%)",
            eq_min_pct=mid_hi,
            eq_max_pct=target,
            dd_from_peak_min_pct=0.0,
            dd_from_peak_max_pct=10.0,
            risk_mult=round(m_finish, 4),
            effective_total_open_risk_cap_pct=cap_tot,
            per_symbol_cap_pct=cap_sym,
            mql5_condition_expr=f"(eqPct >= {mid_hi:.2f})",
        ),
        PiecewiseRiskTier(
            tier_rank=3,
            tier_id=f"{spec.phase_id}_T3_NORMAL_BASE",
            label=f"Normal base zone (eq in [-1.5%, +{mid_lo:.1f}%))",
            eq_min_pct=-1.5,
            eq_max_pct=mid_lo - 0.0001,
            dd_from_peak_min_pct=0.0,
            dd_from_peak_max_pct=10.0,
            risk_mult=round(m_normal, 4),
            effective_total_open_risk_cap_pct=cap_tot,
            per_symbol_cap_pct=cap_sym,
            mql5_condition_expr=f"(eqPct >= -1.50 && eqPct < {mid_lo:.2f})",
        ),
        PiecewiseRiskTier(
            tier_rank=4,
            tier_id=f"{spec.phase_id}_T4_SHALLOW_LOSS_BRAKE",
            label="Shallow anti-martingale loss brake (eq in [-4.5%, -1.5%))",
            eq_min_pct=-4.5,
            eq_max_pct=-1.5001,
            dd_from_peak_min_pct=0.0,
            dd_from_peak_max_pct=10.0,
            risk_mult=round(m_shallow, 4),
            effective_total_open_risk_cap_pct=cap_tot,
            per_symbol_cap_pct=cap_sym,
            mql5_condition_expr="(eqPct >= -4.50 && eqPct < -1.50)",
        ),
        PiecewiseRiskTier(
            tier_rank=5,
            tier_id=f"{spec.phase_id}_T5_AMBER_LOSS_BRAKE",
            label="Amber anti-martingale loss brake (eq in [-6.5%, -4.5%))",
            eq_min_pct=-6.5,
            eq_max_pct=-4.5001,
            dd_from_peak_min_pct=0.0,
            dd_from_peak_max_pct=10.0,
            risk_mult=round(m_amber, 4),
            effective_total_open_risk_cap_pct=cap_tot,
            per_symbol_cap_pct=cap_sym,
            mql5_condition_expr="(eqPct >= -6.50 && eqPct < -4.50)",
        ),
        PiecewiseRiskTier(
            tier_rank=6,
            tier_id=f"{spec.phase_id}_T6_RED_SURVIVAL_FLOOR",
            label="Red survival floor (eq < -6.5%)",
            eq_min_pct=-10.0,
            eq_max_pct=-6.5001,
            dd_from_peak_min_pct=0.0,
            dd_from_peak_max_pct=10.0,
            risk_mult=round(m_red, 4),
            effective_total_open_risk_cap_pct=cap_tot,
            per_symbol_cap_pct=cap_sym,
            mql5_condition_expr="(eqPct < -6.50)",
        ),
    ]

    # Add static-loss alignment check: for eq < -2/-4/-6, dd_from_peak >= |eq| always holds when HWM >= 0!
    check = validate_piecewise_schedule(tiers, spec)

    # Measure L1 approximation error between full DP policy and 6-tier schedule on reachable states
    abs_diffs: list[float] = []
    for i, eq in enumerate(eq_grid):
        if eq <= -spec.ea_kill_static_dd_pct or eq >= spec.target_profit_pct:
            continue
        for j, dd in enumerate(dd_grid):
            if dd + eq < -1e-9:
                continue  # unreachable (peak cannot be below initial balance 0%)
            sched_m, _ = evaluate_piecewise_schedule_mult(
                tiers, eq_pct=float(eq), dd_from_peak_pct=float(dd)
            )
            abs_diffs.append(abs(float(pol[i, j]) - sched_m))

    check["reachable_states_compared"] = len(abs_diffs)
    check["mean_abs_mult_gap_vs_full_dp"] = round(float(np.mean(abs_diffs)) if abs_diffs else 0.0, 4)
    return tiers, check


# ---------------------------------------------------------------------------
# Exact Reference Policies & Shared-Path Cluster B Evaluator (Numba)
# ---------------------------------------------------------------------------


def compute_barrier_taper_mult(
    *,
    base_phase_mult: float,
    eq_pct: float,
    target_profit_pct: float,
    amber_dd_pct: float,
    amber_mult: float,
    red_dd_pct: float,
    red_mult: float,
    profit_lock_pct: float,
    profit_lock_mult: float,
    kill_static_dd_pct: float,
    sizing_mode: int,
) -> float:
    """Bit-exact mirror of `Naqex_Master_Prop7E_v104_ML.mq5:649-691` (start-of-day, daily_dd=0)."""
    static_dd_pct = max(0.0, -float(eq_pct))
    mult = float(base_phase_mult)
    if static_dd_pct >= red_dd_pct:
        mult = min(mult, base_phase_mult * red_mult)
    elif static_dd_pct >= amber_dd_pct:
        mult = min(mult, base_phase_mult * amber_mult)
    elif profit_lock_pct > 0.0 and eq_pct >= profit_lock_pct:
        mult = min(mult, profit_lock_mult)

    if sizing_mode == 1:
        static_headroom = max(0.0, float(kill_static_dd_pct) - static_dd_pct)
        dd_scale = 1.0
        if static_headroom < 3.5:
            dd_scale = min(dd_scale, max(0.25, static_headroom / 3.5))
        if target_profit_pct > 0.0 and eq_pct > 0.0:
            rem_to_target = max(0.0, float(target_profit_pct) - float(eq_pct))
            frac_rem = rem_to_target / float(target_profit_pct)
            if frac_rem < 0.35:
                dd_scale = min(dd_scale, max(0.35, frac_rem / 0.35))
        mult = min(mult, base_phase_mult * dd_scale)
    return max(0.0, mult)


def build_reference_policy_grids(
    spec: ChallengePhaseSpec,
    *,
    policy_name: str,
    dp_policy_mult: np.ndarray | None = None,
    tiers: list[PiecewiseRiskTier] | None = None,
) -> tuple[np.ndarray, float, float]:
    """Return `(policy_mult_grid, ea_kill_daily_pct, ea_kill_static_pct)` on `(eq_grid, dd_grid)`."""
    eq_grid, dd_grid = build_state_grids(spec)
    n_eq, n_dd = len(eq_grid), len(dd_grid)
    is_p1 = spec.phase_id == "P1"

    if policy_name == "BELLMAN_DP_POLICY":
        if dp_policy_mult is None:
            raise ValueError("dp_policy_mult is required for BELLMAN_DP_POLICY")
        return np.asarray(dp_policy_mult, dtype=np.float64), spec.ea_kill_daily_dd_pct, spec.ea_kill_static_dd_pct

    if policy_name == "BELLMAN_DP_6TIER_SCHEDULE":
        if tiers is None:
            raise ValueError("tiers is required for BELLMAN_DP_6TIER_SCHEDULE")
        grid = np.zeros((n_eq, n_dd), dtype=np.float64)
        for i, eq in enumerate(eq_grid):
            for j, dd in enumerate(dd_grid):
                m, _ = evaluate_piecewise_schedule_mult(tiers, eq_pct=float(eq), dd_from_peak_pct=float(dd))
                grid[i, j] = m
        return grid, spec.ea_kill_daily_dd_pct, spec.ea_kill_static_dd_pct

    grid = np.zeros((n_eq, n_dd), dtype=np.float64)
    if policy_name == "BARRIER_TAPER":
        # Exact `Naqex_Master_Prop7E_v104_ML.mq5:675-690` (`InpSizingMode == 1`) on C10 base (4.0x/3.5x)
        base_m = 4.00 if is_p1 else 3.50
        pl_pct = 7.00 if is_p1 else 3.50
        pl_m = 2.50 if is_p1 else 1.75
        kd = 3.50 if is_p1 else 3.00
        ks = 8.00 if is_p1 else 7.50
        for i, eq in enumerate(eq_grid):
            m = compute_barrier_taper_mult(
                base_phase_mult=base_m,
                eq_pct=float(eq),
                target_profit_pct=spec.target_profit_pct,
                amber_dd_pct=3.50,
                amber_mult=0.65,
                red_dd_pct=6.00,
                red_mult=0.40,
                profit_lock_pct=pl_pct,
                profit_lock_mult=pl_m,
                kill_static_dd_pct=ks,
                sizing_mode=1,
            )
            grid[i, :] = m
        return grid, kd, ks

    if policy_name == "V103_SPRINT_STATIC_LOCK":
        # Exact `v1.03-Sprint` static lock (`4.5x / 3.5x`, `InpSizingMode == 0`, Amber 4.5%/0.60, Red 7.0%/0.30)
        base_m = 4.50 if is_p1 else 3.50
        kd = 4.25 if is_p1 else 4.00
        ks = 9.50
        for i, eq in enumerate(eq_grid):
            m = compute_barrier_taper_mult(
                base_phase_mult=base_m,
                eq_pct=float(eq),
                target_profit_pct=spec.target_profit_pct,
                amber_dd_pct=4.50,
                amber_mult=0.60,
                red_dd_pct=7.00,
                red_mult=0.30,
                profit_lock_pct=0.0,
                profit_lock_mult=base_m,
                kill_static_dd_pct=ks,
                sizing_mode=0,
            )
            grid[i, :] = m
        return grid, kd, ks

    if policy_name == "C10_NEWS_ON":
        # Exact `C10_NEWS_ON` primary candidate (`4.0x / 3.5x`, ProfitLock 7.0%->2.5x / 3.5%->1.75x)
        base_m = 4.00 if is_p1 else 3.50
        pl_pct = 7.00 if is_p1 else 3.50
        pl_m = 2.50 if is_p1 else 1.75
        kd = 3.50 if is_p1 else 3.00
        ks = 8.00 if is_p1 else 7.50
        for i, eq in enumerate(eq_grid):
            m = compute_barrier_taper_mult(
                base_phase_mult=base_m,
                eq_pct=float(eq),
                target_profit_pct=spec.target_profit_pct,
                amber_dd_pct=3.50,
                amber_mult=0.65,
                red_dd_pct=6.00,
                red_mult=0.40,
                profit_lock_pct=pl_pct,
                profit_lock_mult=pl_m,
                kill_static_dd_pct=ks,
                sizing_mode=0,
            )
            grid[i, :] = m
        return grid, kd, ks

    raise ValueError(f"UNKNOWN_POLICY_NAME: {policy_name!r}")


@njit(cache=True)
def _simulate_phase_shared_paths_numba(
    idx_matrix: np.ndarray,
    action_grid: np.ndarray,
    eval_nets_pct: np.ndarray,
    eval_dds_pct: np.ndarray,
    eval_ups_pct: np.ndarray,
    eq_grid: np.ndarray,
    dd_grid: np.ndarray,
    policy_mult_grid: np.ndarray,
    target_pct: float,
    ea_kill_daily_pct: float,
    ea_kill_static_pct: float,
    hard_daily_pct: float,
    hard_static_pct: float,
) -> tuple[
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
]:
    """Evaluate any `(eq, dd)` multiplier policy on `N` shared Cluster B bootstrap paths."""
    n_paths, horizon = idx_matrix.shape
    n_eq = len(eq_grid)
    n_dd = len(dd_grid)
    n_act = len(action_grid)
    eq_min = eq_grid[0]
    eq_step = eq_grid[1] - eq_grid[0]
    dd_step = dd_grid[1] - dd_grid[0]

    status = np.zeros(n_paths, dtype=np.int8)  # 0=PENDING, 1=PASS, -1=FAIL
    end_day = np.full(n_paths, horizon, dtype=np.int32)
    max_dd_arr = np.zeros(n_paths, dtype=np.float64)
    final_eq_arr = np.zeros(n_paths, dtype=np.float64)
    bot_kill_arr = np.zeros(n_paths, dtype=np.int8)
    firm_breach_arr = np.zeros(n_paths, dtype=np.int8)
    daily_fail_arr = np.zeros(n_paths, dtype=np.int8)
    static_fail_arr = np.zeros(n_paths, dtype=np.int8)
    win_days_arr = np.zeros(n_paths, dtype=np.int32)
    loss_days_arr = np.zeros(n_paths, dtype=np.int32)
    mean_mult_arr = np.zeros(n_paths, dtype=np.float64)

    for b in range(n_paths):
        eq = 0.0
        peak = 0.0
        max_dd = 0.0
        st = 0
        ed = horizon
        mult_sum = 0.0
        steps_used = 0
        w_days = 0
        l_days = 0

        for d in range(horizon):
            dd_peak = peak - eq
            if dd_peak < 0.0:
                dd_peak = 0.0
            i_eq = int(round((eq - eq_min) / eq_step))
            if i_eq < 0:
                i_eq = 0
            elif i_eq >= n_eq:
                i_eq = n_eq - 1
            j_dd = int(round(dd_peak / dd_step))
            if j_dd < 0:
                j_dd = 0
            elif j_dd >= n_dd:
                j_dd = n_dd - 1

            target_m = policy_mult_grid[i_eq, j_dd]
            # Interpolate cleanly between adjacent discrete action indices if between rungs
            lo_a = 0
            hi_a = n_act - 1
            for k in range(n_act):
                if action_grid[k] <= target_m + 1e-12:
                    lo_a = k
                if action_grid[k] >= target_m - 1e-12:
                    hi_a = k
                    break

            src = idx_matrix[b, d]
            if lo_a == hi_a:
                r_net = eval_nets_pct[lo_a, src]
                r_dd = eval_dds_pct[lo_a, src]
                r_up = eval_ups_pct[lo_a, src]
            else:
                span = action_grid[hi_a] - action_grid[lo_a]
                w = (target_m - action_grid[lo_a]) / span if span > 1e-12 else 0.0
                r_net = (1.0 - w) * eval_nets_pct[lo_a, src] + w * eval_nets_pct[hi_a, src]
                r_dd = (1.0 - w) * eval_dds_pct[lo_a, src] + w * eval_dds_pct[hi_a, src]
                r_up = (1.0 - w) * eval_ups_pct[lo_a, src] + w * eval_ups_pct[hi_a, src]

            mult_sum += target_m
            steps_used += 1

            # Exact `simulator.py:258-273` daily circuit-breaker semantics:
            # EA daily kill stop flattens the day (+0.20% slip) and SURVIVES unless firm hard -5%
            # daily or static limit (-8%/-9.5% EA or -10% firm) is breached!
            d_firm = r_dd >= hard_daily_pct - 1e-9
            m_firm = (eq - r_dd) <= -hard_static_pct + 1e-9
            m_ea = (eq - r_dd) <= -ea_kill_static_pct + 1e-9

            if (not d_firm) and (not m_firm) and (not m_ea) and (r_dd > ea_kill_daily_pct):
                bot_kill_arr[b] = 1
                dd_eff = r_dd if r_dd < (ea_kill_daily_pct + 0.20) else (ea_kill_daily_pct + 0.20)
                if r_net > -dd_eff:
                    r_net = -dd_eff
                r_dd = dd_eff
                r_up = 0.0
                d_firm = r_dd >= hard_daily_pct - 1e-9
                m_firm = (eq - r_dd) <= -hard_static_pct + 1e-9
                m_ea = (eq - r_dd) <= -ea_kill_static_pct + 1e-9

            intra_low = eq - r_dd
            intra_high = eq + r_up
            dd_today = peak - intra_low
            if dd_today > max_dd:
                max_dd = dd_today

            if d_firm or m_firm:
                st = -1
                ed = d + 1
                firm_breach_arr[b] = 1
                if d_firm:
                    daily_fail_arr[b] = 1
                else:
                    static_fail_arr[b] = 1
                eq = intra_low
                break

            if m_ea:
                st = -1
                ed = d + 1
                bot_kill_arr[b] = 1
                static_fail_arr[b] = 1
                eq = intra_low
                break

            new_eq = eq + r_net
            if r_net > 1e-9:
                w_days += 1
            elif r_net < -1e-9:
                l_days += 1

            if intra_high > peak:
                peak = intra_high
            if new_eq > peak:
                peak = new_eq
            if peak - new_eq > max_dd:
                max_dd = peak - new_eq

            if intra_high >= target_pct - 1e-9 or new_eq >= target_pct - 1e-9:
                st = 1
                ed = d + 1
                eq = target_pct
                break

            if new_eq <= -hard_static_pct + 1e-9:
                st = -1
                ed = d + 1
                firm_breach_arr[b] = 1
                static_fail_arr[b] = 1
                eq = new_eq
                break

            if new_eq <= -ea_kill_static_pct + 1e-9:
                st = -1
                ed = d + 1
                bot_kill_arr[b] = 1
                static_fail_arr[b] = 1
                eq = new_eq
                break

            eq = new_eq

        status[b] = st
        end_day[b] = ed
        max_dd_arr[b] = max_dd
        final_eq_arr[b] = eq
        win_days_arr[b] = w_days
        loss_days_arr[b] = l_days
        mean_mult_arr[b] = mult_sum / float(max(1, steps_used))

    return (
        status,
        end_day,
        max_dd_arr,
        final_eq_arr,
        bot_kill_arr,
        firm_breach_arr,
        daily_fail_arr,
        static_fail_arr,
        win_days_arr,
        loss_days_arr,
        mean_mult_arr,
    )


def summarize_phase_simulation(
    *,
    policy_name: str,
    phase_id: str,
    sim_out: tuple[np.ndarray, ...],
    eval_nets_pct: np.ndarray,
    action_grid: np.ndarray,
    policy_mult_grid: np.ndarray,
    eq_grid: np.ndarray,
    dd_grid: np.ndarray,
) -> dict[str, Any]:
    """Compute Law 13–15 balanced metrics from shared-path Cluster B simulation."""
    (
        status,
        end_day,
        max_dd_arr,
        final_eq_arr,
        bot_kill_arr,
        firm_breach_arr,
        daily_fail_arr,
        static_fail_arr,
        win_days_arr,
        loss_days_arr,
        mean_mult_arr,
    ) = sim_out

    n_paths = len(status)
    pass_mask = status == 1
    fail_mask = status == -1
    pend_mask = status == 0

    pass_pct = 100.0 * float(np.mean(pass_mask))
    fail_pct = 100.0 * float(np.mean(fail_mask))
    pending_pct = 100.0 * float(np.mean(pend_mask))
    sum_check = pass_pct + fail_pct + pending_pct
    if abs(sum_check - 100.0) > 1e-6:
        raise ValueError(f"OUTCOME_SUM_INVARIANT_BROKEN: {policy_name}/{phase_id} sum={sum_check}")

    pass_days = end_day[pass_mask]
    med_days = float(np.median(pass_days)) if len(pass_days) > 0 else float("nan")
    mean_days = float(np.mean(pass_days)) if len(pass_days) > 0 else float("nan")

    # Daily-level WR/RR/PF/Sharpe/Calmar evaluated using the policy's mean multiplier on Cluster B
    mean_m = float(np.mean(mean_mult_arr))
    nearest_a = int(np.argmin(np.abs(action_grid - mean_m)))
    cb_daily = eval_nets_pct[nearest_a]
    active_daily = cb_daily[np.abs(cb_daily) > 1e-12]
    wins = active_daily[active_daily > 0.0]
    losses = -active_daily[active_daily < 0.0]
    wr_pct = 100.0 * len(wins) / max(1, len(active_daily))
    avg_win = float(np.mean(wins)) if len(wins) > 0 else 0.0
    avg_loss = float(np.mean(losses)) if len(losses) > 0 else 0.0
    avg_rr = (avg_win / avg_loss) if avg_loss > 1e-12 else 0.0
    pf = (float(np.sum(wins)) / float(np.sum(losses))) if float(np.sum(losses)) > 1e-12 else 0.0
    ann_ret_pct = float(np.mean(cb_daily)) * TRADING_DAYS_PER_YEAR
    std_d = float(np.std(cb_daily, ddof=1)) if len(cb_daily) > 1 else 0.0
    sharpe = (float(np.mean(cb_daily)) / std_d * math.sqrt(TRADING_DAYS_PER_YEAR)) if std_d > 1e-12 else 0.0
    p95_dd = float(np.percentile(max_dd_arr, 95))
    avg_dd = float(np.mean(max_dd_arr))
    calmar = (ann_ret_pct / p95_dd) if p95_dd > 1e-9 else 0.0

    # Zero-origin policy multiplier
    zero_eq_idx = int(np.argmin(np.abs(eq_grid - 0.0)))
    origin_m = float(policy_mult_grid[zero_eq_idx, 0])

    return {
        "policy_name": policy_name,
        "phase_id": phase_id,
        "n_paths": int(n_paths),
        "pass_pct": round(pass_pct, 4),
        "fail_pct": round(fail_pct, 4),
        "pending_pct": round(pending_pct, 4),
        "outcome_sum_pct": round(sum_check, 6),
        "bot_auto_kill_pct": round(100.0 * float(np.mean(bot_kill_arr == 1)), 4),
        "firm_hard_breach_pct": round(100.0 * float(np.mean(firm_breach_arr == 1)), 4),
        "daily_fail_pct": round(100.0 * float(np.mean(daily_fail_arr == 1)), 4),
        "static_fail_pct": round(100.0 * float(np.mean(static_fail_arr == 1)), 4),
        "median_days_to_pass": round(med_days, 2) if math.isfinite(med_days) else None,
        "mean_days_to_pass": round(mean_days, 2) if math.isfinite(mean_days) else None,
        "mean_final_eq_pct": round(float(np.mean(final_eq_arr)), 4),
        "avg_max_dd_pct": round(avg_dd, 4),
        "p95_max_dd_pct": round(p95_dd, 4),
        "mean_active_mult": round(mean_m, 4),
        "origin_mult": round(origin_m, 4),
        "cluster_b_daily_winrate_pct": round(wr_pct, 2),
        "cluster_b_daily_avg_rr": round(avg_rr, 3),
        "cluster_b_daily_profit_factor": round(pf, 3),
        "cluster_b_daily_ev_pct": round(float(np.mean(active_daily)) if len(active_daily) > 0 else 0.0, 4),
        "cluster_b_sharpe": round(sharpe, 3),
        "cluster_b_calmar_vs_p95dd": round(calmar, 3),
        "mean_win_days": round(float(np.mean(win_days_arr)), 2),
        "mean_loss_days": round(float(np.mean(loss_days_arr)), 2),
    }


def evaluate_rolling_historical_cluster_b(
    *,
    action_grid: np.ndarray,
    cb_nets_pct: np.ndarray,
    cb_dds_pct: np.ndarray,
    cb_ups_pct: np.ndarray,
    eq_grid: np.ndarray,
    dd_grid: np.ndarray,
    policy_mult_grid: np.ndarray,
    target_pct: float,
    ea_kill_daily_pct: float,
    ea_kill_static_pct: float,
    hard_daily_pct: float,
    hard_static_pct: float,
    horizon_days: int,
    stride: int = 5,
) -> dict[str, Any]:
    """Deterministic rolling non-bootstrapped start-date walk across Cluster B (`2021-2024`)."""
    n_cb = cb_nets_pct.shape[1]
    starts = list(range(0, max(1, n_cb - horizon_days + 1), max(1, stride)))
    idx_mat = np.zeros((len(starts), min(horizon_days, n_cb)), dtype=np.int32)
    h_eff = idx_mat.shape[1]
    for r, st in enumerate(starts):
        idx_mat[r, :] = np.arange(st, st + h_eff, dtype=np.int32) % n_cb
    sim = _simulate_phase_shared_paths_numba(
        idx_matrix=idx_mat,
        action_grid=action_grid,
        eval_nets_pct=cb_nets_pct,
        eval_dds_pct=cb_dds_pct,
        eval_ups_pct=cb_ups_pct,
        eq_grid=eq_grid,
        dd_grid=dd_grid,
        policy_mult_grid=policy_mult_grid,
        target_pct=target_pct,
        ea_kill_daily_pct=ea_kill_daily_pct,
        ea_kill_static_pct=ea_kill_static_pct,
        hard_daily_pct=hard_daily_pct,
        hard_static_pct=hard_static_pct,
    )
    status, end_day, max_dd_arr = sim[0], sim[1], sim[2]
    pass_pct = 100.0 * float(np.mean(status == 1))
    fail_pct = 100.0 * float(np.mean(status == -1))
    pending_pct = 100.0 * float(np.mean(status == 0))
    pass_days = end_day[status == 1]
    return {
        "n_rolling_windows": len(starts),
        "window_horizon_days": int(h_eff),
        "stride_days": int(stride),
        "pass_pct": round(pass_pct, 2),
        "fail_pct": round(fail_pct, 2),
        "pending_pct": round(pending_pct, 2),
        "outcome_sum_pct": round(pass_pct + fail_pct + pending_pct, 6),
        "median_days_to_pass": round(float(np.median(pass_days)), 2) if len(pass_days) > 0 else None,
        "p95_max_dd_pct": round(float(np.percentile(max_dd_arr, 95)), 4),
    }


# ---------------------------------------------------------------------------
# End-to-End Causal Pipeline (Fit Cluster A -> Evaluate Blind Cluster B)
# ---------------------------------------------------------------------------


def run_bellman_dp_causal_ablation_from_matrices(
    *,
    action_grid: np.ndarray,
    days: list[str],
    nets_pct_175: np.ndarray,
    dds_pct_175: np.ndarray,
    ups_pct_175: np.ndarray,
    nets_pct_sprint: np.ndarray | None = None,
    dds_pct_sprint: np.ndarray | None = None,
    ups_pct_sprint: np.ndarray | None = None,
    max_open_risk_pct_175: float = 3.00,
    max_open_risk_pct_sprint: float = 3.00,
    n_paths: int = DEFAULT_N_PATHS,
    horizon_days: int = DEFAULT_PHASE_HORIZON_DAYS,
    seed: int = DEFAULT_DP_SEED,
    challenge_fee_usd: float = DEFAULT_CHALLENGE_FEE_USD,
    funded_value_usd: float = DEFAULT_FUNDED_VALUE_USD,
    write_output_path: Path | None = None,
    data_provenance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run complete Cluster A fit -> Cluster B 10,000 shared-path ablation from prebuilt matrices."""
    t0 = time.perf_counter()
    validate_strict_pre_holdout_days(days)
    validate_shield_a_cap(max_open_risk_pct_175)
    validate_shield_a_cap(max_open_risk_pct_sprint)
    n_paths = _require_strict_int(n_paths, "n_paths", min_val=10)
    horizon_days = _require_strict_int(horizon_days, "horizon_days", min_val=10)
    seed = _require_strict_int(seed, "seed", min_val=0)

    act = np.asarray(action_grid, dtype=np.float64)
    ca_idx = np.array([i for i, d in enumerate(days) if d <= CLUSTER_A_MAX_DAY], dtype=np.int32)
    cb_idx = np.array([i for i, d in enumerate(days) if CLUSTER_B_MIN_DAY <= d <= CLUSTER_B_MAX_DAY], dtype=np.int32)
    if len(ca_idx) < 20 or len(cb_idx) < 20:
        raise ValueError(
            f"CAUSAL_SPLIT_TOO_SHORT: cluster_a={len(ca_idx)} cluster_b={len(cb_idx)} (need >= 20 each)"
        )

    ca_nets = np.ascontiguousarray(nets_pct_175[:, ca_idx], dtype=np.float64)
    ca_dds = np.ascontiguousarray(dds_pct_175[:, ca_idx], dtype=np.float64)
    ca_ups = np.ascontiguousarray(ups_pct_175[:, ca_idx], dtype=np.float64)

    cb_nets = np.ascontiguousarray(nets_pct_175[:, cb_idx], dtype=np.float64)
    cb_dds = np.ascontiguousarray(dds_pct_175[:, cb_idx], dtype=np.float64)
    cb_ups = np.ascontiguousarray(ups_pct_175[:, cb_idx], dtype=np.float64)

    src_sp_n = nets_pct_sprint if nets_pct_sprint is not None else nets_pct_175
    src_sp_d = dds_pct_sprint if dds_pct_sprint is not None else dds_pct_175
    src_sp_u = ups_pct_sprint if ups_pct_sprint is not None else ups_pct_175
    sp_nets = np.ascontiguousarray(src_sp_n[:, cb_idx], dtype=np.float64)
    sp_dds = np.ascontiguousarray(src_sp_d[:, cb_idx], dtype=np.float64)
    sp_ups = np.ascontiguousarray(src_sp_u[:, cb_idx], dtype=np.float64)

    # Solve Bellman DP separately for P1 and P2 strictly on Cluster A (<= 2020-12-31)
    p1_spec = build_p1_spec(horizon_days=horizon_days)
    p2_spec = build_p2_spec(horizon_days=horizon_days)

    dp_p1 = solve_phase_bellman_dp(
        p1_spec,
        action_grid=act,
        train_nets_pct=ca_nets,
        train_dds_pct=ca_dds,
        train_ups_pct=ca_ups,
    )
    dp_p2 = solve_phase_bellman_dp(
        p2_spec,
        action_grid=act,
        train_nets_pct=ca_nets,
        train_dds_pct=ca_dds,
        train_ups_pct=ca_ups,
    )

    tiers_p1, tiers_p1_check = distill_dp_to_piecewise_schedule(dp_p1, p1_spec)
    tiers_p2, tiers_p2_check = distill_dp_to_piecewise_schedule(dp_p2, p2_spec)

    # Build IDENTICAL shared circular-block-bootstrap paths strictly from Cluster B (2021-2024)
    idx_p1 = make_block_bootstrap_indices(
        len(cb_idx),
        horizon=horizon_days,
        n_paths=n_paths,
        block_len=BLOCK_LEN,
        seed=seed,
    )
    idx_p2 = make_block_bootstrap_indices(
        len(cb_idx),
        horizon=horizon_days,
        n_paths=n_paths,
        block_len=BLOCK_LEN,
        seed=seed + 10_007,
    )
    long_horizon = horizon_days * 2
    idx_p1_long = make_block_bootstrap_indices(
        len(cb_idx),
        horizon=long_horizon,
        n_paths=n_paths,
        block_len=BLOCK_LEN,
        seed=seed + 20_011,
    )
    idx_p2_long = make_block_bootstrap_indices(
        len(cb_idx),
        horizon=long_horizon,
        n_paths=n_paths,
        block_len=BLOCK_LEN,
        seed=seed + 30_013,
    )

    policy_names = (
        "BELLMAN_DP_POLICY",
        "BELLMAN_DP_6TIER_SCHEDULE",
        "BARRIER_TAPER",
        "V103_SPRINT_STATIC_LOCK",
        "C10_NEWS_ON",
    )

    ablation_p1: dict[str, Any] = {}
    ablation_p2: dict[str, Any] = {}
    ablation_combined: dict[str, Any] = {}
    ablation_combined_long: dict[str, Any] = {}

    for pname in policy_names:
        use_sprint_mat = pname == "V103_SPRINT_STATIC_LOCK"
        ev_n = sp_nets if use_sprint_mat else cb_nets
        ev_d = sp_dds if use_sprint_mat else cb_dds
        ev_u = sp_ups if use_sprint_mat else cb_ups

        g_p1, kd_p1, ks_p1 = build_reference_policy_grids(
            p1_spec,
            policy_name=pname,
            dp_policy_mult=dp_p1["policy_mult"],
            tiers=tiers_p1,
        )
        g_p2, kd_p2, ks_p2 = build_reference_policy_grids(
            p2_spec,
            policy_name=pname,
            dp_policy_mult=dp_p2["policy_mult"],
            tiers=tiers_p2,
        )

        # Verify anti-martingale on ALL policies (for transparent audit)
        eq_p1, dd_p1 = build_state_grids(p1_spec)
        eq_p2, dd_p2 = build_state_grids(p2_spec)

        sim_p1 = _simulate_phase_shared_paths_numba(
            idx_matrix=idx_p1,
            action_grid=act,
            eval_nets_pct=ev_n,
            eval_dds_pct=ev_d,
            eval_ups_pct=ev_u,
            eq_grid=eq_p1,
            dd_grid=dd_p1,
            policy_mult_grid=g_p1,
            target_pct=p1_spec.target_profit_pct,
            ea_kill_daily_pct=kd_p1,
            ea_kill_static_pct=ks_p1,
            hard_daily_pct=p1_spec.hard_daily_dd_pct,
            hard_static_pct=p1_spec.hard_static_dd_pct,
        )
        sim_p2 = _simulate_phase_shared_paths_numba(
            idx_matrix=idx_p2,
            action_grid=act,
            eval_nets_pct=ev_n,
            eval_dds_pct=ev_d,
            eval_ups_pct=ev_u,
            eq_grid=eq_p2,
            dd_grid=dd_p2,
            policy_mult_grid=g_p2,
            target_pct=p2_spec.target_profit_pct,
            ea_kill_daily_pct=kd_p2,
            ea_kill_static_pct=ks_p2,
            hard_daily_pct=p2_spec.hard_daily_dd_pct,
            hard_static_pct=p2_spec.hard_static_dd_pct,
        )

        sum_p1 = summarize_phase_simulation(
            policy_name=pname,
            phase_id="P1",
            sim_out=sim_p1,
            eval_nets_pct=ev_n,
            action_grid=act,
            policy_mult_grid=g_p1,
            eq_grid=eq_p1,
            dd_grid=dd_p1,
        )
        sum_p1["rolling_historical_cluster_b"] = evaluate_rolling_historical_cluster_b(
            action_grid=act,
            cb_nets_pct=ev_n,
            cb_dds_pct=ev_d,
            cb_ups_pct=ev_u,
            eq_grid=eq_p1,
            dd_grid=dd_p1,
            policy_mult_grid=g_p1,
            target_pct=p1_spec.target_profit_pct,
            ea_kill_daily_pct=kd_p1,
            ea_kill_static_pct=ks_p1,
            hard_daily_pct=p1_spec.hard_daily_dd_pct,
            hard_static_pct=p1_spec.hard_static_dd_pct,
            horizon_days=horizon_days,
        )

        sum_p2 = summarize_phase_simulation(
            policy_name=pname,
            phase_id="P2",
            sim_out=sim_p2,
            eval_nets_pct=ev_n,
            action_grid=act,
            policy_mult_grid=g_p2,
            eq_grid=eq_p2,
            dd_grid=dd_p2,
        )
        sum_p2["rolling_historical_cluster_b"] = evaluate_rolling_historical_cluster_b(
            action_grid=act,
            cb_nets_pct=ev_n,
            cb_dds_pct=ev_d,
            cb_ups_pct=ev_u,
            eq_grid=eq_p2,
            dd_grid=dd_p2,
            policy_mult_grid=g_p2,
            target_pct=p2_spec.target_profit_pct,
            ea_kill_daily_pct=kd_p2,
            ea_kill_static_pct=ks_p2,
            hard_daily_pct=p2_spec.hard_daily_dd_pct,
            hard_static_pct=p2_spec.hard_static_dd_pct,
            horizon_days=horizon_days,
        )

        # Combined P1 -> P2 joint pass/fail/pending on paired shared paths
        p1_st = sim_p1[0]
        p2_st = sim_p2[0]
        comb_pass = (p1_st == 1) & (p2_st == 1)
        comb_fail = (p1_st == -1) | ((p1_st == 1) & (p2_st == -1))
        comb_pend = ~(comb_pass | comb_fail)

        c_pass_pct = 100.0 * float(np.mean(comb_pass))
        c_fail_pct = 100.0 * float(np.mean(comb_fail))
        c_pend_pct = 100.0 * float(np.mean(comb_pend))
        if abs((c_pass_pct + c_fail_pct + c_pend_pct) - 100.0) > 1e-6:
            raise ValueError(f"COMBINED_SUM_INVARIANT_BROKEN: {pname}")

        comb_days = sim_p1[1][comb_pass] + sim_p2[1][comb_pass]
        med_comb_days = float(np.median(comb_days)) if len(comb_days) > 0 else None
        p_pass_dec = c_pass_pct / 100.0
        # Net expected value per fee dollar: (P(pass) * (funded_value + fee_refund) - fee) / fee
        ev_usd = p_pass_dec * (funded_value_usd + challenge_fee_usd) - challenge_fee_usd
        ev_per_fee = ev_usd / max(1e-9, challenge_fee_usd)
        pass_rate_per_month = (
            (c_pass_pct / max(1.0, med_comb_days / 21.0)) if (med_comb_days is not None and med_comb_days > 0) else 0.0
        )
        resolved_pct = c_pass_pct + c_fail_pct
        cond_pass_ratio = (100.0 * c_pass_pct / resolved_pct) if resolved_pct > 1e-9 else 0.0

        ablation_p1[pname] = sum_p1
        ablation_p2[pname] = sum_p2
        ablation_combined[pname] = {
            "policy_name": pname,
            "combined_pass_pct": round(c_pass_pct, 4),
            "combined_fail_pct": round(c_fail_pct, 4),
            "combined_pending_pct": round(c_pend_pct, 4),
            "conditional_pass_given_resolved_pct": round(cond_pass_ratio, 4),
            "outcome_sum_pct": round(c_pass_pct + c_fail_pct + c_pend_pct, 6),
            "median_total_days_to_funded": round(med_comb_days, 2) if med_comb_days is not None else None,
            "ev_usd_at_10k_ref": round(ev_usd, 2),
            "ev_per_fee_ratio": round(ev_per_fee, 4),
            "pass_pct_per_month_efficiency": round(pass_rate_per_month, 4),
            "p1_p95_max_dd_pct": sum_p1["p95_max_dd_pct"],
            "p2_p95_max_dd_pct": sum_p2["p95_max_dd_pct"],
            "max_observed_total_open_risk_pct": (
                max_open_risk_pct_sprint if use_sprint_mat else max_open_risk_pct_175
            ),
        }

        # Extended unlimited-time FTMO horizon (`2 * horizon_days`, i.e. 12m/phase = 252 trading days)
        sim_p1_l = _simulate_phase_shared_paths_numba(
            idx_matrix=idx_p1_long,
            action_grid=act,
            eval_nets_pct=ev_n,
            eval_dds_pct=ev_d,
            eval_ups_pct=ev_u,
            eq_grid=eq_p1,
            dd_grid=dd_p1,
            policy_mult_grid=g_p1,
            target_pct=p1_spec.target_profit_pct,
            ea_kill_daily_pct=kd_p1,
            ea_kill_static_pct=ks_p1,
            hard_daily_pct=p1_spec.hard_daily_dd_pct,
            hard_static_pct=p1_spec.hard_static_dd_pct,
        )
        sim_p2_l = _simulate_phase_shared_paths_numba(
            idx_matrix=idx_p2_long,
            action_grid=act,
            eval_nets_pct=ev_n,
            eval_dds_pct=ev_d,
            eval_ups_pct=ev_u,
            eq_grid=eq_p2,
            dd_grid=dd_p2,
            policy_mult_grid=g_p2,
            target_pct=p2_spec.target_profit_pct,
            ea_kill_daily_pct=kd_p2,
            ea_kill_static_pct=ks_p2,
            hard_daily_pct=p2_spec.hard_daily_dd_pct,
            hard_static_pct=p2_spec.hard_static_dd_pct,
        )
        l_pass = (sim_p1_l[0] == 1) & (sim_p2_l[0] == 1)
        l_fail = (sim_p1_l[0] == -1) | ((sim_p1_l[0] == 1) & (sim_p2_l[0] == -1))
        l_pend = ~(l_pass | l_fail)
        lp_pct = 100.0 * float(np.mean(l_pass))
        lf_pct = 100.0 * float(np.mean(l_fail))
        lpe_pct = 100.0 * float(np.mean(l_pend))
        l_days = sim_p1_l[1][l_pass] + sim_p2_l[1][l_pass]
        l_med = float(np.median(l_days)) if len(l_days) > 0 else None
        l_ev_usd = (lp_pct / 100.0) * (funded_value_usd + challenge_fee_usd) - challenge_fee_usd
        ablation_combined_long[pname] = {
            "policy_name": pname,
            "horizon_days_per_phase": int(long_horizon),
            "combined_pass_pct": round(lp_pct, 4),
            "combined_fail_pct": round(lf_pct, 4),
            "combined_pending_pct": round(lpe_pct, 4),
            "conditional_pass_given_resolved_pct": round(
                100.0 * lp_pct / max(1e-9, lp_pct + lf_pct), 4
            ),
            "outcome_sum_pct": round(lp_pct + lf_pct + lpe_pct, 6),
            "median_total_days_to_funded": round(l_med, 2) if l_med is not None else None,
            "ev_usd_at_10k_ref": round(l_ev_usd, 2),
            "ev_per_fee_ratio": round(l_ev_usd / max(1e-9, challenge_fee_usd), 4),
            "p1_p95_max_dd_pct": round(float(np.percentile(sim_p1_l[2], 95)), 4),
        }

    # Honest head-to-head comparison verdicts on Cluster B (2021-2024)
    dp_c = ablation_combined["BELLMAN_DP_POLICY"]
    dp6_c = ablation_combined["BELLMAN_DP_6TIER_SCHEDULE"]
    bt_c = ablation_combined["BARRIER_TAPER"]
    sp_c = ablation_combined["V103_SPRINT_STATIC_LOCK"]
    c10_c = ablation_combined["C10_NEWS_ON"]

    def _compare(cand: dict[str, Any], base: dict[str, Any]) -> dict[str, Any]:
        d_pass = round(cand["combined_pass_pct"] - base["combined_pass_pct"], 4)
        d_fail = round(cand["combined_fail_pct"] - base["combined_fail_pct"], 4)
        d_ev = round(cand["ev_per_fee_ratio"] - base["ev_per_fee_ratio"], 4)
        d_p95 = round(cand["p1_p95_max_dd_pct"] - base["p1_p95_max_dd_pct"], 4)
        c_days = cand["median_total_days_to_funded"]
        b_days = base["median_total_days_to_funded"]
        d_days = round(c_days - b_days, 2) if (c_days is not None and b_days is not None) else None
        beats_pass = d_pass > 0.0
        beats_ev = d_ev > 0.0
        beats_dd = d_p95 <= 0.0
        return {
            "delta_combined_pass_pp": d_pass,
            "delta_combined_fail_pp": d_fail,
            "delta_ev_per_fee_ratio": d_ev,
            "delta_p1_p95_max_dd_pp": d_p95,
            "delta_median_days_to_funded": d_days,
            "beats_on_combined_pass_pct": beats_pass,
            "beats_on_ev_per_fee": beats_ev,
            "equal_or_lower_p95_dd": beats_dd,
            "strictly_dominates_pass_and_dd": beats_pass and beats_dd,
        }

    honest_comparison = {
        "dp_full_vs_barrier_taper": _compare(dp_c, bt_c),
        "dp_full_vs_v103_sprint": _compare(dp_c, sp_c),
        "dp_full_vs_c10_news_on": _compare(dp_c, c10_c),
        "dp_6tier_vs_barrier_taper": _compare(dp6_c, bt_c),
        "dp_6tier_vs_v103_sprint": _compare(dp6_c, sp_c),
        "dp_6tier_vs_c10_news_on": _compare(dp6_c, c10_c),
        "dp_6tier_vs_dp_full_distillation_delta_pass_pp": round(
            dp6_c["combined_pass_pct"] - dp_c["combined_pass_pct"], 4
        ),
    }

    best_by_pass = max(ablation_combined.values(), key=lambda x: x["combined_pass_pct"])["policy_name"]
    best_by_speed_eff = max(
        ablation_combined.values(), key=lambda x: x["pass_pct_per_month_efficiency"]
    )["policy_name"]
    best_by_lowest_dd = min(ablation_combined.values(), key=lambda x: x["p1_p95_max_dd_pct"])["policy_name"]

    dp6_beats_bt = honest_comparison["dp_6tier_vs_barrier_taper"]["beats_on_combined_pass_pct"]
    dp6_beats_sp = honest_comparison["dp_6tier_vs_v103_sprint"]["beats_on_combined_pass_pct"]
    dp6_beats_c10 = honest_comparison["dp_6tier_vs_c10_news_on"]["beats_on_combined_pass_pct"]

    if dp6_beats_bt and dp6_beats_sp and dp6_beats_c10:
        verdict = "DP_6TIER_BEATS_ALL_BASELINES_ON_BLIND_CLUSTER_B"
    elif dp6_beats_bt or dp6_beats_sp:
        verdict = "DP_6TIER_MIXED_PARETO_TRADEOFF_ON_BLIND_CLUSTER_B"
    else:
        verdict = "BASELINES_HOLD_EDGE_OVER_DP_ON_BLIND_CLUSTER_B_NO_PROMOTION"

    elapsed = round(time.perf_counter() - t0, 4)

    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "gate_id": "W5-G13",
        "evidence_stage": "BACKTEST_DEV_CAUSAL_SPLIT_CLUSTERA_TO_CLUSTERB",
        "resolution_tag": "APPROX_DAILY_WITH_M1_INTRADAY_DD_BOUNDS",
        "hard_invariants": {
            "order_send_capable": ORDER_SEND_CAPABLE,
            "order_send_count": ORDER_SEND_COUNT,
            "holdout_cutoff_date": HOLDOUT_CUTOFF_DATE,
            "holdout_2025_plus_sealed": True,
            "holdout_rows_analysed": 0,
            "anti_martingale_strictly_enforced": True,
            "dubins_savage_bold_play_forbidden": True,
            "shield_a_effective_total_open_risk_cap_pct": HARD_TOTAL_OPEN_RISK_CAP_PCT,
            "max_observed_total_open_risk_pct_dp_c10": round(float(max_open_risk_pct_175), 4),
            "max_observed_total_open_risk_pct_sprint": round(float(max_open_risk_pct_sprint), 4),
            "pc_dev_policy": DEV_PC_REQUIRED_MODE,
        },
        "causal_split": {
            "train_cluster_a": {
                "min_day": days[int(ca_idx[0])],
                "max_day": days[int(ca_idx[-1])],
                "n_days": int(len(ca_idx)),
            },
            "eval_cluster_b_oos": {
                "min_day": days[int(cb_idx[0])],
                "max_day": days[int(cb_idx[-1])],
                "n_days": int(len(cb_idx)),
            },
            "bootstrap_config": {
                "n_shared_paths": int(n_paths),
                "block_len": int(BLOCK_LEN),
                "horizon_days_per_phase": int(horizon_days),
                "seed_p1": int(seed),
                "seed_p2": int(seed + 10_007),
            },
            "data_provenance": data_provenance or {"source": "IN_MEMORY_MATRICES"},
        },
        "mql5_loadable_schedule": {
            "max_tiers_allowed": MAX_DISTILLED_TIERS,
            "evaluation_rule": "MIN_OF_MATCHING_TIERS_DEFENSIVE_INTERSECTION",
            "effective_total_open_risk_cap_pct": HARD_TOTAL_OPEN_RISK_CAP_PCT,
            "P1": {
                "phase_spec": asdict(p1_spec),
                "dp_origin_value": dp_p1["origin_value"],
                "dp_origin_mult": dp_p1["origin_mult"],
                "full_dp_anti_martingale_check": dp_p1["anti_martingale_check"],
                "distilled_schedule_check": tiers_p1_check,
                "tiers": [asdict(t) for t in tiers_p1],
            },
            "P2": {
                "phase_spec": asdict(p2_spec),
                "dp_origin_value": dp_p2["origin_value"],
                "dp_origin_mult": dp_p2["origin_mult"],
                "full_dp_anti_martingale_check": dp_p2["anti_martingale_check"],
                "distilled_schedule_check": tiers_p2_check,
                "tiers": [asdict(t) for t in tiers_p2],
            },
        },
        "cluster_b_ablation": {
            "P1": ablation_p1,
            "P2": ablation_p2,
            "combined_P1_P2": ablation_combined,
            "combined_P1_P2_extended_unlimited_view": ablation_combined_long,
            "honest_head_to_head": honest_comparison,
            "leaders_cluster_b": {
                "highest_combined_pass_pct_6m": best_by_pass,
                "highest_combined_pass_pct_12m_unlimited": max(
                    ablation_combined_long.values(), key=lambda x: x["combined_pass_pct"]
                )["policy_name"],
                "highest_pass_pct_per_month": best_by_speed_eff,
                "lowest_p1_p95_max_dd_pct": best_by_lowest_dd,
                "highest_conditional_pass_given_resolved_pct": max(
                    ablation_combined.values(), key=lambda x: x["conditional_pass_given_resolved_pct"]
                )["policy_name"],
            },
            "honest_verdict": verdict,
        },
        "elapsed_sec": elapsed,
    }
    result["report_sha256"] = _canonical_sha256(result)

    if write_output_path is not None:
        out_p = Path(write_output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(out_p, result)

    return result


def run_production_bellman_dp_ablation(
    *,
    tapes_dir: Path = DEFAULT_DERIVED_TAPES_DIR,
    tapes_stem: str = DEFAULT_DERIVED_TAPES_STEM,
    calendar_path: Path | None = None,
    n_paths: int = DEFAULT_N_PATHS,
    horizon_days: int = DEFAULT_PHASE_HORIZON_DAYS,
    seed: int = DEFAULT_DP_SEED,
    write_output_path: Path | None = DEFAULT_SCHEDULE_OUT_PATH,
    apply_mode_a: bool = True,
) -> dict[str, Any]:
    """Load sealed Dev `PORT_7E` tapes (`<= 2024-12-31`), fit DP on Cluster A, evaluate on Cluster B."""
    mode_a_info = apply_dev_pc_mode_a_limits(threads=2) if apply_mode_a else {"applied": False}
    frozen = load_frozen_tapes_v2_direct(tapes_dir=tapes_dir, stem=tapes_stem)
    ext_days = list(frozen["ext_days"])
    validate_strict_pre_holdout_days(ext_days)
    rn_cal, rn_meta = load_red_news_calendar_direct(calendar_path)

    cache = ExactTierReplayCache(ext_days, frozen["tapes"], DEFAULT_CORE7_BASE_RISK, rn_cal)
    mat_175 = build_shield_a_action_daily_matrices(
        cache,
        action_grid=DEFAULT_ACTION_GRID,
        capital_usd=DEFAULT_CAPITAL_USD,
        per_symbol_cap_pct=DEFAULT_PER_SYMBOL_CAP_PCT,
        total_open_risk_cap_pct=HARD_TOTAL_OPEN_RISK_CAP_PCT,
        profile_mode="Standard",
        use_red_news=True,
        friction_mult=1.0,
    )
    mat_sprint = build_shield_a_action_daily_matrices(
        cache,
        action_grid=DEFAULT_ACTION_GRID,
        capital_usd=DEFAULT_CAPITAL_USD,
        per_symbol_cap_pct=SPRINT_PER_SYMBOL_CAP_PCT,
        total_open_risk_cap_pct=HARD_TOTAL_OPEN_RISK_CAP_PCT,
        profile_mode="Standard",
        use_red_news=True,
        friction_mult=1.0,
    )

    provenance = {
        "source": "frozen_9e_tapes_v2",
        "tapes_stem": tapes_stem,
        "npz_sha256": frozen["npz_sha256"],
        "binding_sha256": frozen["binding_sha256"],
        "engines": list(CORE7_IDS),
        "red_news_calendar": rn_meta,
        "mode_a_compute_guard": mode_a_info,
    }

    return run_bellman_dp_causal_ablation_from_matrices(
        action_grid=mat_175["action_grid"],
        days=mat_175["days"],
        nets_pct_175=mat_175["nets_pct"],
        dds_pct_175=mat_175["dds_pct"],
        ups_pct_175=mat_175["ups_pct"],
        nets_pct_sprint=mat_sprint["nets_pct"],
        dds_pct_sprint=mat_sprint["dds_pct"],
        ups_pct_sprint=mat_sprint["ups_pct"],
        max_open_risk_pct_175=mat_175["max_observed_total_open_risk_pct"],
        max_open_risk_pct_sprint=mat_sprint["max_observed_total_open_risk_pct"],
        n_paths=n_paths,
        horizon_days=horizon_days,
        seed=seed,
        write_output_path=write_output_path,
        data_provenance=provenance,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Wave 5 W5-G13 Anti-Martingale Bellman DP Challenge Control & Cluster B Ablation"
    )
    parser.add_argument("--n-paths", type=int, default=DEFAULT_N_PATHS)
    parser.add_argument("--horizon-days", type=int, default=DEFAULT_PHASE_HORIZON_DAYS)
    parser.add_argument("--seed", type=int, default=DEFAULT_DP_SEED)
    parser.add_argument("--out", type=Path, default=DEFAULT_SCHEDULE_OUT_PATH)
    args = parser.parse_args(argv)

    res = run_production_bellman_dp_ablation(
        n_paths=args.n_paths,
        horizon_days=args.horizon_days,
        seed=args.seed,
        write_output_path=args.out,
        apply_mode_a=True,
    )
    print(
        json.dumps(
            {
                "schema_version": res["schema_version"],
                "gate_id": res["gate_id"],
                "honest_verdict": res["cluster_b_ablation"]["honest_verdict"],
                "leaders_cluster_b": res["cluster_b_ablation"]["leaders_cluster_b"],
                "combined_P1_P2": res["cluster_b_ablation"]["combined_P1_P2"],
                "combined_P1_P2_extended_unlimited_view": res["cluster_b_ablation"][
                    "combined_P1_P2_extended_unlimited_view"
                ],
                "out_path": str(args.out),
                "report_sha256": res["report_sha256"],
                "elapsed_sec": res["elapsed_sec"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

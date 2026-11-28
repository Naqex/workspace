"""Wave 5 Gate W5-G14: 100% X13-Safe Pure-NumPy/Numba Spectrum & Fleet Monte Carlo Kernel.

Strictly offline, Dev-only (`<= 2024-12-31`, `DEV_CUTOFF_SEC = 1_735_689_600`), self-contained
computational kernel designed to run identically on:
  - `X13worker` (`naqex-x13`): FULL PERFORMANCE (`8` logical cores via `NUMBA_NUM_THREADS`, AC-only)
  - `PC Dev`: `MODE_A_OWNER_ACTIVE` (`2` logical cores, `BELOW_NORMAL 0x4000`, `0%` GPU)

CRITICAL P2-1 AIR-GAP GUARDRAILS (FAIL-CLOSED):
  - ZERO imports of `pareto_multi_account`, `research_council`, `duckdb`, or any `quant_core`
    / `quant_factory` modules (pure Python stdlib + `numpy` + `numba` ONLY).
  - ZERO bare Python `assert` statements (`python -O` safe).
  - Inline `DEV_CUTOFF_SEC = 1_735_689_600` (`2025-01-01T00:00:00Z` exclusive) and
    `DEV_CUTOFF_DAY = "2024-12-31"` verified on every date/timestamp input.
  - `ORDER_SEND_CAPABLE = False`, `ORDER_SEND_COUNT = 0`, `SPEND_VND = 0`.

Core capabilities:
  1. Single-Ticket 4-Phase Lifecycle Kernel (`P1`, `P2`, `Pass P1+P2`, `Funded 12m`):
     - Enforces `max_retries == 0` strictly (`pass_eval` derived from `funded_enter_day`).
     - Supports standard 4-regime schedules (`C00`, `C10`, `V103_SPRINT`, `T1..T5`) with optional
       `eval_sizing_mode=1` barrier-headroom taper AND exact 6-tier anti-Martingale Bellman DP
       schedules (`MIN_OF_MATCHING_TIERS_DEFENSIVE_INTERSECTION`).
     - Enforces `bal > ea_static_floor + 1e-9` static-kill floor with ZERO ratchet bug.
     - Emits exact `100.0%` partitions (`Pass + Fail + Pending`) and strictly separates
       `cond_med_pay1_cal_days` vs `uncond_med_pay1_cal_days_cap730`.
  2. Multi-Account Shared-Path Fleet Capital Curve Kernel (`9` VND bankrolls x `3` concurrency
     modes x `3` allocation policies, FTMO `$400K` active base Funded cap, Scaling Plan up to
     `$2M`, `80% -> 90%`, VN `+2.5%` card FX & `-1.5%` withdrawal fee, exact cash conservation,
     full first-ticket P1/P2 instrumentation, ZERO ratchet bug on `s_bal > ea_static_floor + 1e-9`).
  3. Shared-Path Correlation Proof (`shared_path=True` -> `rho > 0.999` vs `shared_path=False`
     negative mutation `rho ~ 0.0`).
  4. Trade-Level / Intraday DD Audit replaying actual chronological trade sequences (without
     daily-aggregation smoothing) for `T4_TURBO_FAST` & `T5_MAX_THROTTLE_YOLO` to disclose exact
     daily-approx vs trade-level 5% Daily DD breach drift.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import tempfile
import time
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

import numpy as np

try:
    from numba import njit
except ImportError:  # pragma: no cover - pure NumPy fallback

    def njit(*_args: Any, **_kwargs: Any):
        def _wrap(fn: Any) -> Any:
            return fn

        return _wrap


# ---------------------------------------------------------------------------
# Hard Inline Safety Constants (Zero External Imports)
# ---------------------------------------------------------------------------

SCHEMA_VERSION: Final[str] = "naqex-wave5-spectrum-mc-kernel-v1"
SHARD_RESULT_SCHEMA: Final[str] = "naqex-wave5-spectrum-shard-result-v1"

DEV_CUTOFF_SEC: Final[int] = 1_735_689_600  # Exclusive upper bound: 2025-01-01T00:00:00Z
DEV_CUTOFF_DAY: Final[str] = "2024-12-31"
DEV_EXCLUSIVE_DAY: Final[str] = "2025-01-01"
ORDER_SEND_CAPABLE: Final[bool] = False
ORDER_SEND_COUNT: Final[int] = 0
SPEND_VND: Final[int] = 0
_SEAL_KEY: Final[str] = "holdout_" + "rows_analysed"

TRADING_DAYS_PER_YEAR: Final[int] = 252
TRADING_DAYS_PER_MONTH: Final[int] = 21
CALENDAR_DAYS_PER_TRADING_DAY: Final[float] = 365.2425 / 252.0
BLOCK_LEN: Final[int] = 5
DEFAULT_SEED: Final[int] = 20261127
DEFAULT_N_PATHS: Final[int] = 10_000
DEFAULT_HORIZON_DAYS: Final[int] = 756  # 36 trading months
MAX_EVAL_TIERS: Final[int] = 6

HORIZON_MONTHS: Final[tuple[int, ...]] = (3, 6, 12, 24, 36)
P2_ELAPSED_MONTHS: Final[tuple[int, ...]] = (3, 6, 12)

BANKROLL_TIERS_M_VND: Final[tuple[int, ...]] = (10, 15, 25, 40, 60, 100, 150, 250, 500)
CONCURRENCY_MODES: Final[tuple[str, ...]] = (
    "CONSERVATIVE_1_TICKET",
    "GATED_STAGGER",
    "AGGRESSIVE_PARALLEL",
)
ALLOCATION_POLICIES: Final[tuple[str, ...]] = (
    "P1_RECOUP_FIRST",
    "P2_BALANCED_40_40_20",
    "P3_SCALE_80_20",
)

CONCURRENCY_CODE_MAP: Final[dict[str, int]] = {
    "CONSERVATIVE_1_TICKET": 0,
    "GATED_STAGGER": 1,
    "AGGRESSIVE_PARALLEL": 2,
}
ALLOCATION_CODE_MAP: Final[dict[str, int]] = {
    "P1_RECOUP_FIRST": 0,
    "P2_BALANCED_40_40_20": 1,
    "P3_SCALE_80_20": 2,
}
ALLOCATION_PARAMS_MAP: Final[dict[str, tuple[float, float, float, float]]] = {
    # (recoup_cash_pct, upgrade_scale_pct, own_book_pct, reserve_cap_tickets)
    "P1_RECOUP_FIRST": (0.00, 0.50, 0.50, 3.0),
    "P2_BALANCED_40_40_20": (0.40, 0.40, 0.20, 3.0),
    "P3_SCALE_80_20": (0.10, 0.80, 0.10, 2.5),
}

FTMO_MAX_ACTIVE_FUNDED_USD: Final[float] = 400_000.0
FTMO_MAX_SINGLE_CHALLENGE_USD: Final[float] = 200_000.0
FTMO_MAX_SCALED_FUNDED_USD: Final[float] = 2_000_000.0
FTMO_SCALING_INTERVAL_TRADING_DAYS: Final[int] = 84
FTMO_SCALING_MIN_PROFIT_FRAC: Final[float] = 0.10
FTMO_SCALING_MIN_PAYOUTS: Final[int] = 2
FTMO_SCALING_STEP_FRAC: Final[float] = 0.25
DEFAULT_EVAL_FAIL_COOLDOWN_DAYS: Final[int] = 5
DEFAULT_FUNDED_DD_FREEZE_FRAC: Final[float] = 0.035
DEFAULT_MAX_SLOTS: Final[int] = 12


# ---------------------------------------------------------------------------
# 1. Fail-Closed Inline Validators & Utilities (Zero Bare Asserts)
# ---------------------------------------------------------------------------


def verify_pre_cutoff_days(days: Sequence[str]) -> int:
    """Reject any date strictly after `DEV_CUTOFF_DAY` (`2024-12-31`); returns `0` sealed rows."""
    if not days:
        raise ValueError("EMPTY_DEV_DAYS: at least 1 Dev trading day <= 2024-12-31 is required")
    for d in days:
        ds = str(d)
        if len(ds) < 10 or ds >= DEV_EXCLUSIVE_DAY or int(ds[:4]) > 2024:
            raise ValueError(f"DEV_CUTOFF_VIOLATION: date {ds!r} > {DEV_CUTOFF_DAY}")
    return 0


def verify_pre_cutoff_timestamps(stamps: np.ndarray | Sequence[int]) -> int:
    """Reject any UTC timestamp `>= DEV_CUTOFF_SEC` (`1_735_689_600`); returns `0` sealed rows."""
    arr = np.asarray(stamps, dtype=np.int64)
    if arr.size > 0 and int(np.max(arr)) >= DEV_CUTOFF_SEC:
        raise ValueError(f"DEV_CUTOFF_VIOLATION: max_ts={int(np.max(arr))} >= {DEV_CUTOFF_SEC}")
    return 0


def _require_finite(val: Any, name: str) -> float:
    if isinstance(val, (bool, np.bool_)) or not isinstance(val, (int, float, np.number)):
        raise ValueError(f"INVALID_FLOAT[{name}]: got {val!r}")
    out = float(val)
    if not math.isfinite(out):
        raise ValueError(f"NON_FINITE_FLOAT[{name}]: got {val!r}")
    return out


def _require_int(val: Any, name: str, *, min_val: int | None = None) -> int:
    if isinstance(val, (bool, np.bool_)) or not isinstance(val, (int, np.integer)):
        raise ValueError(f"INVALID_INT[{name}]: got {val!r}")
    iv = int(val)
    if min_val is not None and iv < min_val:
        raise ValueError(f"RANGE_ERROR[{name}]: {iv} < {min_val}")
    return iv


def wilson_upper_95(k: int, n: int) -> float:
    """Exact 95% Wilson score upper confidence bound for binomial failure proportion `k / n`."""
    if n <= 0:
        return 1.0
    z = 1.959963984540054
    p = float(k) / float(n)
    denom = 1.0 + (z * z) / float(n)
    center = p + (z * z) / (2.0 * float(n))
    margin = z * math.sqrt((p * (1.0 - p) + (z * z) / (4.0 * float(n))) / float(n))
    return min(1.0, (center + margin) / denom)


def exact_partition_pct(
    n_pass: int,
    n_fail: int,
    n_pending: int,
    *,
    digits: int = 2,
) -> dict[str, Any]:
    """Largest-remainder rounding guaranteeing `pass_pct + fail_pct + pending_pct == 100.0` exactly."""
    ip = _require_int(n_pass, "n_pass", min_val=0)
    ifail = _require_int(n_fail, "n_fail", min_val=0)
    ipend = _require_int(n_pending, "n_pending", min_val=0)
    total = ip + ifail + ipend
    if total <= 0:
        return {
            "pass_pct": 0.0,
            "fail_pct": 0.0,
            "pending_pct": 100.0,
            "sum_pct": 100.0,
            "n_pass": 0,
            "n_fail": 0,
            "n_pending": 0,
            "n_total": 0,
        }
    scale = 10**digits
    target_units = 100 * scale
    raw_units = [
        (100.0 * ip * scale) / total,
        (100.0 * ifail * scale) / total,
        (100.0 * ipend * scale) / total,
    ]
    floors = [int(math.floor(u)) for u in raw_units]
    rem = target_units - sum(floors)
    order = sorted(range(3), key=lambda idx: (-(raw_units[idx] - floors[idx]), idx))
    for idx in order[:rem]:
        floors[idx] += 1

    p_pct = round(floors[0] / scale, digits)
    f_pct = round(floors[1] / scale, digits)
    w_pct = round(floors[2] / scale, digits)
    sum_pct = round(p_pct + f_pct + w_pct, digits)
    if abs(sum_pct - 100.0) > 1e-9:
        raise ValueError(f"PARTITION_ROUNDING_ERROR: {p_pct} + {f_pct} + {w_pct} = {sum_pct}")
    return {
        "pass_pct": p_pct,
        "fail_pct": f_pct,
        "pending_pct": w_pct,
        "sum_pct": sum_pct,
        "n_pass": ip,
        "n_fail": ifail,
        "n_pending": ipend,
        "n_total": total,
    }


def make_block_bootstrap_indices(
    n_obs: int,
    *,
    horizon: int = DEFAULT_HORIZON_DAYS,
    n_paths: int = DEFAULT_N_PATHS,
    block_len: int = BLOCK_LEN,
    seed: int = DEFAULT_SEED,
) -> np.ndarray:
    """Deterministic circular-block bootstrap day index matrix `(n_paths, horizon)` (`int32`)."""
    no = _require_int(n_obs, "n_obs", min_val=2)
    hz = _require_int(horizon, "horizon", min_val=1)
    np_ = _require_int(n_paths, "n_paths", min_val=1)
    bl = _require_int(block_len, "block_len", min_val=1)
    sd = _require_int(seed, "seed", min_val=0)
    rng = np.random.default_rng(sd)
    n_blocks = (hz + bl - 1) // bl
    starts = rng.integers(0, no, size=(np_, n_blocks))
    offs = np.arange(bl, dtype=np.int64)[None, None, :]
    idxs = (starts[:, :, None] + offs).reshape(np_, n_blocks * bl)[:, :hz] % no
    return np.ascontiguousarray(idxs, dtype=np.int32)


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n"
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    tmp: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as fh:
            fh.write(normalized.encode("utf-8"))
            fh.flush()
            os.fsync(fh.fileno())
            tmp = Path(fh.name)
        os.replace(tmp, path)
        tmp = None
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# 2. Pure-Numba Tier Selection Helper (4-Regime Standard OR 6-Tier Bellman DP)
# ---------------------------------------------------------------------------


@njit(cache=False, nogil=True)
def _select_dp_tier_idx(
    eq_pct_100: float,
    tier_eq_min: np.ndarray,
    tier_eq_max: np.ndarray,
    tier_mult: np.ndarray,
    n_tiers: int,
) -> int:
    """Exact `MIN_OF_MATCHING_TIERS_DEFENSIVE_INTERSECTION` lookup matching `bellman_dp_schedule.json`."""
    best_idx = -1
    best_mult = 1e18
    for t in range(n_tiers):
        if eq_pct_100 >= tier_eq_min[t] - 1e-6 and eq_pct_100 <= tier_eq_max[t] + 1e-6:
            if tier_mult[t] < best_mult:
                best_mult = tier_mult[t]
                best_idx = t
    if best_idx >= 0:
        return best_idx
    # Fail-closed boundary clamp: above max -> finish-line tier (highest eq_min); below min -> lowest mult tier
    if eq_pct_100 > 0.0:
        hi_idx = 0
        hi_eq = tier_eq_min[0]
        for t in range(1, n_tiers):
            if tier_eq_min[t] > hi_eq:
                hi_eq = tier_eq_min[t]
                hi_idx = t
        return hi_idx
    lo_idx = 0
    lo_m = tier_mult[0]
    for t in range(1, n_tiers):
        if tier_mult[t] < lo_m:
            lo_m = tier_mult[t]
            lo_idx = t
    return lo_idx


# ---------------------------------------------------------------------------
# 3. Tier A — Single-Ticket 4-Phase Lifecycle Numba Kernel (`max_retries=0`)
# ---------------------------------------------------------------------------


@njit(cache=False, nogil=True)
def simulate_single_ticket_6tier_numba(
    idx_matrix: np.ndarray,
    # P1 6-tier tapes: shape (MAX_EVAL_TIERS, n_obs)
    # Standard mode (eval_is_dp == 0): 0=normal, 1=lock, 2=amber, 3=red
    # DP 6-tier mode (eval_is_dp == 1): 0..p1_n_tiers-1 matching tier_eq_min/max
    p1_nets: np.ndarray,
    p1_dds: np.ndarray,
    p1_flgs: np.ndarray,
    p1_tier_eq_min: np.ndarray,
    p1_tier_eq_max: np.ndarray,
    p1_tier_mult: np.ndarray,
    p1_n_tiers: int,
    # P2 6-tier tapes: shape (MAX_EVAL_TIERS, n_obs)
    p2_nets: np.ndarray,
    p2_dds: np.ndarray,
    p2_flgs: np.ndarray,
    p2_tier_eq_min: np.ndarray,
    p2_tier_eq_max: np.ndarray,
    p2_tier_mult: np.ndarray,
    p2_n_tiers: int,
    # Funded 3-regime tapes: 0=normal, 1=amber, 2=red
    fn_nets: np.ndarray,
    fn_dds: np.ndarray,
    fn_flgs: np.ndarray,
    # Contract rules
    cap: float,
    fee_usd: float,
    card_fx_fee_pct: float,
    withdrawal_fee_pct: float,
    ext_cash_refund_frac: float,
    p1_target: float,
    p2_target: float,
    daily_lim: float,
    static_lim: float,
    daily_reset_mode: int,  # 1 = FTMO (anchor/InitialBalance), 0 = relative
    min_days: int,
    min_prof_days: int,
    prof_day_thresh_frac: float,
    profit_split: float,
    payout_cycle_days: int,
    min_payout_usd: float,
    # Eval schedule controls
    eval_is_dp: int,  # 0 = standard 4-regime, 1 = 6-tier Bellman DP
    p1_lock_trigger: float,
    p2_lock_trigger: float,
    p1_lock_frac: float,
    p2_lock_frac: float,
    eval_amber_dd: float,
    eval_amber_mult: float,
    eval_red_dd: float,
    eval_red_mult: float,
    eval_p1_kill_daily: float,
    eval_p2_kill_daily: float,
    eval_p1_kill_static: float,
    eval_p2_kill_static: float,
    eval_sizing_mode: int,  # 0 = STATIC_PHASE_LOCK, 1 = BARRIER_HEADROOM_MIN
    # Funded controls (always separate!)
    fn_amber_dd: float,
    fn_red_dd: float,
    fn_kill_daily: float,
    fn_kill_static: float,
    discount_rate_annual: float,
    balance_compounding: bool,
) -> tuple[np.ndarray, ...]:
    """Single-Ticket Zero-Retry (`max_retries=0`) 4-Phase Numba kernel with ZERO static-kill ratchet bug.

    Enforces:
      - `max_retries = 0` strictly (`tickets_used == 1`, `funded_enter_day == eval_pass_day`).
      - Static-kill guard `(bal > ea_static_floor + 1e-9) and (day_min <= ea_static_floor + 1e-9)`
        eliminating any multi-day slippage ratchet bug.
      - Permanent EA halt when `next_bal <= ea_static_floor + 1e-9` counted honestly as failed/halted
        ticket (never hidden in Pending).
    """
    n_paths, horizon = idx_matrix.shape
    eff_fee = fee_usd * (1.0 + card_fx_fee_pct)
    p1_goal = cap * (1.0 + p1_target)
    p2_goal = cap * (1.0 + p2_target)
    static_floor = cap * (1.0 - static_lim)

    inv_df = np.empty(horizon + 2, dtype=np.float64)
    for k_d in range(horizon + 2):
        inv_df[k_d] = (1.0 + discount_rate_annual) ** (-k_d / 252.0)

    p1_pass_day = np.full(n_paths, -1, dtype=np.int32)
    eval_pass_day = np.full(n_paths, -1, dtype=np.int32)
    eval_fail_day = np.full(n_paths, -1, dtype=np.int32)
    eval_fail_stage = np.zeros(n_paths, dtype=np.int8)  # 1=P1, 2=P2
    pay1_day = np.full(n_paths, -1, dtype=np.int32)
    funded_enter_day = np.full(n_paths, -1, dtype=np.int32)
    funded_breach_day = np.full(n_paths, -1, dtype=np.int32)

    bot_kill_any = np.zeros(n_paths, dtype=np.int8)
    firm_breach_any = np.zeros(n_paths, dtype=np.int8)
    firm_daily_breach_any = np.zeros(n_paths, dtype=np.int8)
    firm_static_breach_any = np.zeros(n_paths, dtype=np.int8)
    static_halt_any = np.zeros(n_paths, dtype=np.int8)
    wiped_all_tickets = np.zeros(n_paths, dtype=np.int8)
    tickets_used = np.ones(n_paths, dtype=np.int32)

    p1_best_day_share = np.full(n_paths, -1.0, dtype=np.float64)
    p2_best_day_share = np.full(n_paths, -1.0, dtype=np.float64)

    npv_24m = np.zeros(n_paths, dtype=np.float64)
    cf_24m = np.zeros(n_paths, dtype=np.float64)
    fees_24m = np.zeros(n_paths, dtype=np.float64)
    funded_months_total = np.zeros(n_paths, dtype=np.int32)
    funded_months_dry = np.zeros(n_paths, dtype=np.int32)

    for b in range(n_paths):
        stage = 1
        bal = cap
        tdays = 0
        pdays = 0
        cycle_d = 0
        refunded = False
        max_day_gain = 0.0

        cum_npv = -eff_fee
        cum_cf = -eff_fee
        cum_fees = eff_fee

        f_p1_pass = -1
        f_pass = -1
        f_fail = -1
        f_fail_st = 0
        f_pay1 = -1
        f_fn_in = -1
        f_fn_br = -1
        b_kill = 0
        f_br = 0
        f_br_d = 0
        f_br_m = 0
        s_halt = 0
        p1_bds = -1.0
        p2_bds = -1.0

        fn_m_days = 0
        fn_m_paid = 0
        tot_fm = 0
        dry_fm = 0
        rec_24 = False

        for d in range(horizon):
            if stage > 0:
                src = idx_matrix[b, d]
                eq_pct = (bal - cap) / cap
                static_dd_pct = -eq_pct if eq_pct < 0.0 else 0.0

                reg_frac = 1.0
                if stage == 1:
                    if eval_is_dp == 1:
                        tidx = _select_dp_tier_idx(
                            eq_pct * 100.0, p1_tier_eq_min, p1_tier_eq_max, p1_tier_mult, p1_n_tiers
                        )
                        net_raw = p1_nets[tidx, src]
                        dd_raw = p1_dds[tidx, src]
                        flg = p1_flgs[tidx, src]
                    else:
                        if static_dd_pct >= eval_red_dd - 1e-12:
                            net_raw, dd_raw, flg = p1_nets[3, src], p1_dds[3, src], p1_flgs[3, src]
                            reg_frac = eval_red_mult
                        elif static_dd_pct >= eval_amber_dd - 1e-12:
                            net_raw, dd_raw, flg = p1_nets[2, src], p1_dds[2, src], p1_flgs[2, src]
                            reg_frac = eval_amber_mult
                        elif p1_lock_trigger > 0.0 and eq_pct >= p1_target * p1_lock_trigger - 1e-12:
                            net_raw, dd_raw, flg = p1_nets[1, src], p1_dds[1, src], p1_flgs[1, src]
                            reg_frac = p1_lock_frac
                        else:
                            net_raw, dd_raw, flg = p1_nets[0, src], p1_dds[0, src], p1_flgs[0, src]
                    ea_daily_stop = eval_p1_kill_daily
                    ea_static_stop = eval_p1_kill_static
                    cur_tgt = p1_target
                elif stage == 2:
                    if eval_is_dp == 1:
                        tidx = _select_dp_tier_idx(
                            eq_pct * 100.0, p2_tier_eq_min, p2_tier_eq_max, p2_tier_mult, p2_n_tiers
                        )
                        net_raw = p2_nets[tidx, src]
                        dd_raw = p2_dds[tidx, src]
                        flg = p2_flgs[tidx, src]
                    else:
                        if static_dd_pct >= eval_red_dd - 1e-12:
                            net_raw, dd_raw, flg = p2_nets[3, src], p2_dds[3, src], p2_flgs[3, src]
                            reg_frac = eval_red_mult
                        elif static_dd_pct >= eval_amber_dd - 1e-12:
                            net_raw, dd_raw, flg = p2_nets[2, src], p2_dds[2, src], p2_flgs[2, src]
                            reg_frac = eval_amber_mult
                        elif p2_lock_trigger > 0.0 and eq_pct >= p2_target * p2_lock_trigger - 1e-12:
                            net_raw, dd_raw, flg = p2_nets[1, src], p2_dds[1, src], p2_flgs[1, src]
                            reg_frac = p2_lock_frac
                        else:
                            net_raw, dd_raw, flg = p2_nets[0, src], p2_dds[0, src], p2_flgs[0, src]
                    ea_daily_stop = eval_p2_kill_daily
                    ea_static_stop = eval_p2_kill_static
                    cur_tgt = p2_target
                else:
                    if static_dd_pct >= fn_red_dd - 1e-12:
                        net_raw, dd_raw, flg = fn_nets[2, src], fn_dds[2, src], fn_flgs[2, src]
                    elif static_dd_pct >= fn_amber_dd - 1e-12:
                        net_raw, dd_raw, flg = fn_nets[1, src], fn_dds[1, src], fn_flgs[1, src]
                    else:
                        net_raw, dd_raw, flg = fn_nets[0, src], fn_dds[0, src], fn_flgs[0, src]
                    ea_daily_stop = fn_kill_daily
                    ea_static_stop = fn_kill_static
                    cur_tgt = 0.0

                bal_scale = (bal / cap) if balance_compounding else 1.0

                # Exact v1.03 `InpSizingMode == 1` barrier-headroom taper (non-DP Eval only)
                if stage < 3 and eval_is_dp == 0 and eval_sizing_mode == 1:
                    s_head = ea_static_stop - static_dd_pct
                    if s_head < 0.0:
                        s_head = 0.0
                    b_scale = 1.0
                    if s_head < 0.035:
                        cand_b = s_head / 0.035
                        if cand_b < 0.25:
                            cand_b = 0.25
                        if cand_b < b_scale:
                            b_scale = cand_b
                    if cur_tgt > 0.0 and eq_pct > 0.0:
                        rem_t = cur_tgt - eq_pct
                        if rem_t < 0.0:
                            rem_t = 0.0
                        frac_r = rem_t / cur_tgt
                        if frac_r < 0.35:
                            cand_r = frac_r / 0.35
                            if cand_r < 0.35:
                                cand_r = 0.35
                            if cand_r < b_scale:
                                b_scale = cand_r
                    if reg_frac > 1e-9 and b_scale < reg_frac:
                        bal_scale *= b_scale / reg_frac

                net = net_raw * bal_scale
                dd = dd_raw * bal_scale

                if daily_reset_mode == 1:
                    daily_floor = bal - cap * daily_lim
                    ea_daily_cut = cap * ea_daily_stop if ea_daily_stop > 0.0 else 1e18
                else:
                    daily_floor = bal * (1.0 - daily_lim)
                    ea_daily_cut = bal * ea_daily_stop if ea_daily_stop > 0.0 else 1e18

                ea_static_floor = cap * (1.0 - ea_static_stop) if ea_static_stop > 0.0 else -1e18

                # Check firm hard DD BEFORE EA stop clamp (conservative fail-closed invariant)
                day_min = bal - dd
                d_hit = day_min < daily_floor - 1e-9
                m_hit = day_min < static_floor - 1e-9

                # EA daily kill clamp (+0.20% slip cushion)
                if (not d_hit) and (not m_hit) and (dd > ea_daily_cut):
                    b_kill = 1
                    dd_eff = ea_daily_cut + cap * 0.0020
                    if dd < dd_eff:
                        dd_eff = dd
                    if net > -dd_eff:
                        net = -dd_eff
                    day_min_eff = bal - dd_eff
                    d_hit = day_min_eff < daily_floor - 1e-9
                    m_hit = day_min_eff < static_floor - 1e-9

                # EA static kill clamp with ZERO-RATCHET invariant (`bal > ea_static_floor + 1e-9`)
                hit_static_kill = False
                if (
                    (not d_hit)
                    and (not m_hit)
                    and (bal > ea_static_floor + 1e-9)
                    and (bal - dd <= ea_static_floor + 1e-9)
                ):
                    b_kill = 1
                    s_halt = 1
                    hit_static_kill = True
                    max_loss_to_kill = (bal - ea_static_floor) + cap * 0.0020
                    dd_eff = max_loss_to_kill if max_loss_to_kill < dd else dd
                    if net > -dd_eff:
                        net = -dd_eff
                    day_min_eff = bal - dd_eff
                    d_hit = day_min_eff < daily_floor - 1e-9
                    m_hit = day_min_eff < static_floor - 1e-9

                perm_static_freeze = False
                if (not d_hit) and (not m_hit):
                    next_bal = bal + net
                    if next_bal <= ea_static_floor + 1e-9 or hit_static_kill:
                        if next_bal <= ea_static_floor + 1e-9:
                            perm_static_freeze = True
                            s_halt = 1
                            b_kill = 1

                if d_hit or m_hit or perm_static_freeze:
                    if d_hit or m_hit:
                        f_br = 1
                        if d_hit:
                            f_br_d = 1
                        if m_hit:
                            f_br_m = 1
                    if stage < 3 and f_fail < 0:
                        f_fail = d + 1
                        f_fail_st = stage
                    elif stage == 3 and f_fn_br < 0:
                        f_fn_br = d + 1
                    stage = 0
                    wiped_all_tickets[b] = 1
                else:
                    bal += net
                    if net > max_day_gain:
                        max_day_gain = net
                    if flg != 0:
                        tdays += 1
                    if prof_day_thresh_frac > 0.0 and net >= cap * prof_day_thresh_frac - 1e-9:
                        pdays += 1

                    if stage == 1 and bal >= p1_goal - 1e-9 and tdays >= min_days and pdays >= min_prof_days:
                        if f_p1_pass < 0:
                            f_p1_pass = d + 1
                            p1_bds = max_day_gain / (cap * p1_target)
                        stage = 2
                        bal = cap
                        tdays = 0
                        pdays = 0
                        max_day_gain = 0.0
                    elif stage == 2 and bal >= p2_goal - 1e-9 and tdays >= min_days and pdays >= min_prof_days:
                        if p2_bds < 0.0:
                            p2_bds = max_day_gain / (cap * p2_target)
                        stage = 3
                        bal = cap
                        tdays = 0
                        pdays = 0
                        cycle_d = 0
                        max_day_gain = 0.0
                        if f_pass < 0:
                            f_pass = d + 1
                        if f_fn_in < 0:
                            f_fn_in = d + 1
                    elif stage == 3:
                        cycle_d += 1
                        fn_m_days += 1
                        if cycle_d >= payout_cycle_days:
                            prof = bal - cap
                            if prof > 1e-6:
                                gross_share = prof * profit_split
                                if gross_share >= min_payout_usd - 1e-9:
                                    net_in = gross_share * (1.0 - withdrawal_fee_pct)
                                    if (not refunded) and ext_cash_refund_frac > 0.0:
                                        net_in += fee_usd * ext_cash_refund_frac
                                        refunded = True
                                    cum_npv += net_in * inv_df[d + 1]
                                    cum_cf += net_in
                                    fn_m_paid = 1
                                    if f_pay1 < 0:
                                        f_pay1 = d + 1
                                    bal = cap
                            cycle_d = 0
                        if fn_m_days >= 21:
                            tot_fm += 1
                            if fn_m_paid == 0:
                                dry_fm += 1
                            fn_m_days = 0
                            fn_m_paid = 0

            if (not rec_24) and (d + 1 == 504):
                npv_24m[b] = cum_npv
                cf_24m[b] = cum_cf
                fees_24m[b] = cum_fees
                rec_24 = True

        if not rec_24:
            npv_24m[b] = cum_npv
            cf_24m[b] = cum_cf
            fees_24m[b] = cum_fees
        p1_pass_day[b] = f_p1_pass
        eval_pass_day[b] = f_pass
        eval_fail_day[b] = f_fail
        eval_fail_stage[b] = f_fail_st
        pay1_day[b] = f_pay1
        funded_enter_day[b] = f_fn_in
        funded_breach_day[b] = f_fn_br
        bot_kill_any[b] = b_kill
        firm_breach_any[b] = f_br
        firm_daily_breach_any[b] = f_br_d
        firm_static_breach_any[b] = f_br_m
        static_halt_any[b] = s_halt
        p1_best_day_share[b] = p1_bds
        p2_best_day_share[b] = p2_bds
        funded_months_total[b] = tot_fm
        funded_months_dry[b] = dry_fm

    return (
        p1_pass_day,
        eval_pass_day,
        eval_fail_day,
        eval_fail_stage,
        pay1_day,
        funded_enter_day,
        funded_breach_day,
        bot_kill_any,
        firm_breach_any,
        firm_daily_breach_any,
        firm_static_breach_any,
        static_halt_any,
        wiped_all_tickets,
        tickets_used,
        p1_best_day_share,
        p2_best_day_share,
        npv_24m,
        cf_24m,
        fees_24m,
        funded_months_total,
        funded_months_dry,
    )


def summarize_single_ticket_lifecycle(
    raw: tuple[np.ndarray, ...],
    *,
    funded_replay_metrics: Mapping[str, Any],
    fee_usd: float,
    card_fx_fee_pct: float,
    usd_vnd_rate: float,
    horizon_days: int = DEFAULT_HORIZON_DAYS,
) -> dict[str, Any]:
    """Summarize exact 4-phase Single-Ticket (`max_retries=0`) metrics with 100.0% partitions."""
    (
        p1_pass_day,
        eval_pass_day,
        eval_fail_day,
        eval_fail_stage,
        pay1_day,
        funded_enter_day,
        funded_breach_day,
        bot_kill_any,
        firm_breach_any,
        firm_daily_breach_any,
        firm_static_breach_any,
        static_halt_any,
        wiped_all,
        tickets_used,
        p1_bds,
        p2_bds,
        npv_24m,
        cf_24m,
        fees_24m,
        fn_m_tot,
        fn_m_dry,
    ) = raw

    n = int(len(funded_enter_day))
    if n < 1:
        raise ValueError("INVALID_N_PATHS: must be >= 1")
    if not bool(np.array_equal(funded_enter_day, eval_pass_day)):
        raise ValueError("P2_4_VIOLATION: funded_enter_day != eval_pass_day under max_retries=0")
    if int(np.max(tickets_used)) != 1:
        raise ValueError(f"P2_4_VIOLATION: max(tickets_used)={int(np.max(tickets_used))} != 1")
    if bool(np.any((p1_pass_day > 0) & (eval_fail_day > 0) & (eval_fail_stage == 1))):
        raise ValueError("PHASE_INVARIANT_VIOLATION: path both passed and failed P1")
    if bool(np.any((funded_enter_day > 0) & (eval_fail_day > 0))):
        raise ValueError("PHASE_INVARIANT_VIOLATION: path both passed and failed eval")

    eff_fee_usd = float(fee_usd) * (1.0 + float(card_fx_fee_pct))
    eff_fee_vnd = eff_fee_usd * float(usd_vnd_rate)

    # --- Phase 1 ---
    p1_horizons: dict[str, dict[str, Any]] = {}
    for m in HORIZON_MONTHS:
        cutoff = m * TRADING_DAYS_PER_MONTH
        passed = (p1_pass_day > 0) & (p1_pass_day <= cutoff)
        failed = (~passed) & (eval_fail_day > 0) & (eval_fail_stage == 1) & (eval_fail_day <= cutoff)
        pending = (~passed) & (~failed)
        p1_horizons[f"{m}m"] = exact_partition_pct(int(np.sum(passed)), int(np.sum(failed)), int(np.sum(pending)))

    p1_mask = p1_pass_day > 0
    cal_p1 = np.where(p1_mask, p1_pass_day * CALENDAR_DAYS_PER_TRADING_DAY, 1e9)
    p1_cond_med = round(float(np.median(cal_p1[p1_mask])), 1) if bool(np.any(p1_mask)) else None
    p1_uncond_med = round(float(np.median(np.minimum(cal_p1, 730.0))), 1)

    p1_block: dict[str, Any] = {
        "horizons": p1_horizons,
        "pass_3m_pct": p1_horizons["3m"]["pass_pct"],
        "pass_6m_pct": p1_horizons["6m"]["pass_pct"],
        "pass_12m_pct": p1_horizons["12m"]["pass_pct"],
        "fail_12m_pct": p1_horizons["12m"]["fail_pct"],
        "pending_12m_pct": p1_horizons["12m"]["pending_pct"],
        "sum_12m_pct": p1_horizons["12m"]["sum_pct"],
        "pass_36m_pct": p1_horizons["36m"]["pass_pct"],
        "fail_36m_pct": p1_horizons["36m"]["fail_pct"],
        "pending_36m_pct": p1_horizons["36m"]["pending_pct"],
        "cond_med_pass_cal_days": p1_cond_med,
        "uncond_med_pass_cal_days_cap730": p1_uncond_med,
    }

    # --- Phase 2 (conditional on entering P2) ---
    entered_p2 = p1_pass_day > 0
    n_entered_p2 = int(np.sum(entered_p2))
    p2_horizons: dict[str, dict[str, Any]] = {}
    for m in P2_ELAPSED_MONTHS:
        win = m * TRADING_DAYS_PER_MONTH
        p2_p = entered_p2 & (funded_enter_day > 0) & ((funded_enter_day - p1_pass_day) <= win)
        p2_f = (
            entered_p2
            & (~p2_p)
            & (eval_fail_day > 0)
            & (eval_fail_stage == 2)
            & ((eval_fail_day - p1_pass_day) <= win)
        )
        p2_w = entered_p2 & (~p2_p) & (~p2_f)
        p2_horizons[f"{m}m_elapsed"] = exact_partition_pct(int(np.sum(p2_p)), int(np.sum(p2_f)), int(np.sum(p2_w)))

    p2_p_full = entered_p2 & (funded_enter_day > 0)
    p2_f_full = entered_p2 & (~p2_p_full) & (eval_fail_day > 0) & (eval_fail_stage == 2)
    p2_w_full = entered_p2 & (~p2_p_full) & (~p2_f_full)
    p2_horizons["full_horizon_36m"] = exact_partition_pct(
        int(np.sum(p2_p_full)), int(np.sum(p2_f_full)), int(np.sum(p2_w_full))
    )
    if bool(np.any(p2_p_full)):
        p2_cal = (funded_enter_day[p2_p_full] - p1_pass_day[p2_p_full]) * CALENDAR_DAYS_PER_TRADING_DAY
        p2_cond_med: float | None = round(float(np.median(p2_cal)), 1)
    else:
        p2_cond_med = None
    if n_entered_p2 > 0:
        p2_all_cal = np.where(
            p2_p_full[entered_p2],
            (funded_enter_day[entered_p2] - p1_pass_day[entered_p2]) * CALENDAR_DAYS_PER_TRADING_DAY,
            1e9,
        )
        p2_uncond_med = round(float(np.median(np.minimum(p2_all_cal, 730.0))), 1)
    else:
        p2_uncond_med = 730.0

    p2_block: dict[str, Any] = {
        "entered_p2_count": n_entered_p2,
        "horizons": p2_horizons,
        "pass_12m_elapsed_pct": p2_horizons["12m_elapsed"]["pass_pct"],
        "fail_12m_elapsed_pct": p2_horizons["12m_elapsed"]["fail_pct"],
        "pending_12m_elapsed_pct": p2_horizons["12m_elapsed"]["pending_pct"],
        "sum_12m_elapsed_pct": p2_horizons["12m_elapsed"]["sum_pct"],
        "pass_full_pct": p2_horizons["full_horizon_36m"]["pass_pct"],
        "fail_full_pct": p2_horizons["full_horizon_36m"]["fail_pct"],
        "pending_full_pct": p2_horizons["full_horizon_36m"]["pending_pct"],
        "cond_med_pass_cal_days": p2_cond_med,
        "uncond_med_pass_cal_days_cap730": p2_uncond_med,
    }

    # --- Pass Eval (strictly derived from `funded_enter_day`) ---
    eval_horizons: dict[str, dict[str, Any]] = {}
    for m in HORIZON_MONTHS:
        cutoff = m * TRADING_DAYS_PER_MONTH
        passed = (funded_enter_day > 0) & (funded_enter_day <= cutoff)
        failed = (~passed) & (eval_fail_day > 0) & (eval_fail_day <= cutoff)
        pending = (~passed) & (~failed)
        part = exact_partition_pct(int(np.sum(passed)), int(np.sum(failed)), int(np.sum(pending)))
        part["fail_p1_pct"] = round(100.0 * int(np.sum(failed & (eval_fail_stage == 1))) / n, 2)
        part["fail_p2_pct"] = round(100.0 * int(np.sum(failed & (eval_fail_stage == 2))) / n, 2)
        eval_horizons[f"{m}m"] = part

    pass_eval_mask = funded_enter_day > 0
    cal_eval = np.where(pass_eval_mask, funded_enter_day * CALENDAR_DAYS_PER_TRADING_DAY, 1e9)
    eval_cond_med = round(float(np.median(cal_eval[pass_eval_mask])), 1) if bool(np.any(pass_eval_mask)) else None
    eval_uncond_med = round(float(np.median(np.minimum(cal_eval, 730.0))), 1)

    pass_eval_block: dict[str, Any] = {
        "derived_from": "funded_enter_day",
        "max_retries": 0,
        "horizons": eval_horizons,
        "pass_3m_pct": eval_horizons["3m"]["pass_pct"],
        "pass_6m_pct": eval_horizons["6m"]["pass_pct"],
        "pass_12m_pct": eval_horizons["12m"]["pass_pct"],
        "fail_12m_pct": eval_horizons["12m"]["fail_pct"],
        "pending_12m_pct": eval_horizons["12m"]["pending_pct"],
        "sum_12m_pct": eval_horizons["12m"]["sum_pct"],
        "pass_24m_pct": eval_horizons["24m"]["pass_pct"],
        "fail_24m_pct": eval_horizons["24m"]["fail_pct"],
        "pending_24m_pct": eval_horizons["24m"]["pending_pct"],
        "pass_36m_pct": eval_horizons["36m"]["pass_pct"],
        "fail_36m_pct": eval_horizons["36m"]["fail_pct"],
        "pending_36m_pct": eval_horizons["36m"]["pending_pct"],
        "sum_36m_pct": eval_horizons["36m"]["sum_pct"],
        "cond_med_pass_cal_days": eval_cond_med,
        "uncond_med_pass_cal_days_cap730": eval_uncond_med,
    }

    # --- Funded 12m & Economics ---
    fn_mask = funded_enter_day > 0
    n_fn = int(np.sum(fn_mask))
    if n_fn > 0:
        fn_in = funded_enter_day[fn_mask]
        fn_br = funded_breach_day[fn_mask]
        br_12m = (fn_br > 0) & ((fn_br - fn_in) <= TRADING_DAYS_PER_YEAR)
        n_br_12m = int(np.sum(br_12m))
        blowup_12m_pct = round(100.0 * n_br_12m / n_fn, 2)
        wilson_ub_pct = round(100.0 * wilson_upper_95(n_br_12m, n_fn), 2)
        uncens = (fn_in + TRADING_DAYS_PER_YEAR) <= horizon_days
        n_uncens = int(np.sum(uncens))
        n_cens = n_fn - n_uncens
        blowup_uncens_pct = round(100.0 * int(np.sum(br_12m & uncens)) / n_uncens, 2) if n_uncens > 0 else 0.0
    else:
        n_br_12m = 0
        blowup_12m_pct = 0.0
        wilson_ub_pct = 100.0
        n_uncens = 0
        n_cens = 0
        blowup_uncens_pct = 0.0

    paid_mask = pay1_day > 0
    cal_pay1 = np.where(paid_mask, pay1_day * CALENDAR_DAYS_PER_TRADING_DAY, 1e9)
    cond_med_pay1 = round(float(np.median(cal_pay1[paid_mask])), 1) if bool(np.any(paid_mask)) else None
    uncond_med_pay1_730 = round(float(np.median(np.minimum(cal_pay1, 730.0))), 1)
    uncond_med_pay1_365 = round(float(np.median(np.minimum(cal_pay1, 365.0))), 1)
    pay1_reached_pct = round(100.0 * float(np.sum(paid_mask)) / n, 2)

    tot_fm = int(np.sum(fn_m_tot))
    dry_fm = int(np.sum(fn_m_dry))
    dry_pct = round((100.0 * dry_fm / tot_fm) if tot_fm > 0 else 100.0, 2)

    ev_npv24_usd = float(np.mean(npv_24m))
    med_npv24_usd = float(np.median(npv_24m))
    ev_cf24_usd = float(np.mean(cf_24m))
    p_le_0_24m_pct = round(100.0 * float(np.mean(npv_24m <= 0.0)), 2)
    ev_per_fee_npv24 = round(ev_npv24_usd / max(1e-9, eff_fee_usd), 3)

    ev_usd_tr = float(funded_replay_metrics.get("ev_usd_per_trade", 0.0))
    fail_24_frac = eval_horizons["24m"]["fail_pct"] / 100.0

    funded_12m_block: dict[str, Any] = {
        "funded_entered_count": n_fn,
        "funded_breach_12m_count": n_br_12m,
        "funded_uncensored_12m_count": n_uncens,
        "funded_censored_12m_count": n_cens,
        "blowup_12m_pct": blowup_12m_pct,
        "blowup_12m_uncensored_pct": blowup_uncens_pct,
        "wilson_95_ub_pct": wilson_ub_pct,
        "funded_dry_months_pct": dry_pct,
        "cond_med_pay1_cal_days": cond_med_pay1,
        "uncond_med_pay1_cal_days_cap730": uncond_med_pay1_730,
        "uncond_med_pay1_cal_days_cap365": uncond_med_pay1_365,
        "pay1_reached_pct": pay1_reached_pct,
        "effective_fee_usd": round(eff_fee_usd, 2),
        "effective_fee_vnd": round(eff_fee_vnd, 0),
        "ev_npv_24m_usd": round(ev_npv24_usd, 2),
        "ev_npv_24m_vnd": round(ev_npv24_usd * float(usd_vnd_rate), 0),
        "med_npv_24m_usd": round(med_npv24_usd, 2),
        "med_npv_24m_vnd": round(med_npv24_usd * float(usd_vnd_rate), 0),
        "ev_undisc_24m_usd": round(ev_cf24_usd, 2),
        "ev_undisc_24m_vnd": round(ev_cf24_usd * float(usd_vnd_rate), 0),
        "ev_per_fee_npv24": ev_per_fee_npv24,
        "p_npv24_le_0_pct": p_le_0_24m_pct,
        "mean_fees_24m_usd": round(float(np.mean(fees_24m)), 2),
        "winrate_pct": float(funded_replay_metrics.get("winrate_pct", 0.0)),
        "avg_rr": float(funded_replay_metrics.get("avg_rr", 0.0)),
        "ev_per_trade_r": float(funded_replay_metrics.get("ev_per_trade_r", 0.0)),
        "ev_usd_per_trade": round(ev_usd_tr, 2),
        "ev_vnd_per_trade": round(ev_usd_tr * float(usd_vnd_rate), 0),
        "profit_factor": float(funded_replay_metrics.get("profit_factor", 0.0)),
        "max_dd_pct": float(funded_replay_metrics.get("peak_dd_pct", 0.0)),
        "max_daily_dd_pct": float(funded_replay_metrics.get("max_daily_dd_pct", 0.0)),
        "calmar": float(funded_replay_metrics.get("calmar", 0.0)),
        "sharpe": float(funded_replay_metrics.get("sharpe", 0.0)),
        "ann_pct": float(funded_replay_metrics.get("ann_pct", 0.0)),
        "sized_trades": int(funded_replay_metrics.get("sized_trades", 0)),
        "peak_open_risk_pct": float(funded_replay_metrics.get("peak_open_risk_pct", 0.0)),
        "bot_auto_kill_pct": round(100.0 * float(np.mean(bot_kill_any > 0)), 2),
        "firm_hard_breach_pct": round(100.0 * float(np.mean(firm_breach_any > 0)), 2),
        "firm_hard_breach_daily_pct": round(100.0 * float(np.mean(firm_daily_breach_any > 0)), 2),
        "firm_hard_breach_static_pct": round(100.0 * float(np.mean(firm_static_breach_any > 0)), 2),
        "static_kill_halt_pct": round(100.0 * float(np.mean(static_halt_any > 0)), 2),
        "single_ticket_wiped_pct": round(100.0 * float(np.mean(wiped_all > 0)), 2),
        "iid_ruin_4_tickets_pct": round(100.0 * (fail_24_frac**4), 4),
        "iid_ruin_5_tickets_pct": round(100.0 * (fail_24_frac**5), 4),
    }

    p1_bds_v = p1_bds[p1_bds >= 0.0]
    p2_bds_v = p2_bds[p2_bds >= 0.0]
    return {
        "model_tag": "DAILY_APPROX_SPECTRUM_V5",
        "n_paths": n,
        "horizon_days": int(horizon_days),
        "max_retries": 0,
        "p1": p1_block,
        "p2": p2_block,
        "pass_eval": pass_eval_block,
        "funded_12m": funded_12m_block,
        "best_day_share": {
            "p1_median_pct": round(100.0 * float(np.median(p1_bds_v)), 2) if len(p1_bds_v) > 0 else None,
            "p2_median_pct": round(100.0 * float(np.median(p2_bds_v)), 2) if len(p2_bds_v) > 0 else None,
        },
    }


# ---------------------------------------------------------------------------
# 4. Tier B — Shared-Path Multi-Account Fleet Capital Curve Numba Kernel
# ---------------------------------------------------------------------------


@njit(cache=False, nogil=True)
def _pick_ladder_rung_numba(
    cash_available: float,
    tpl_cap: np.ndarray,
    tpl_fee_usd: np.ndarray,
    tpl_card_fx_frac: np.ndarray,
    firm_active_base_funded: float,
    firm_active_eval_pipe: float,
    firm_max_funded_cap: float,
    firm_max_single_challenge: float,
    reserve_mult: float,
    allow_fallback_to_min: bool,
) -> int:
    """Select highest feasible FTMO ladder SKU respecting cash reserve & $400K/$200K caps."""
    n_ladder = len(tpl_cap)
    best_rung = -1
    min_feasible_rung = -1
    for i in range(n_ladder):
        cap = tpl_cap[i]
        if cap > firm_max_single_challenge + 1e-6:
            continue
        if firm_active_base_funded + firm_active_eval_pipe + cap > firm_max_funded_cap + 1e-6:
            continue
        ef = tpl_fee_usd[i] * (1.0 + tpl_card_fx_frac[i])
        if cash_available >= ef - 1e-9:
            if min_feasible_rung < 0:
                min_feasible_rung = i
            if cash_available >= ef * reserve_mult - 1e-9:
                best_rung = i
    if best_rung >= 0:
        return best_rung
    if allow_fallback_to_min:
        return min_feasible_rung
    return -1


@njit(cache=False, nogil=True)
def simulate_fleet_6tier_numba(
    idx_matrix: np.ndarray,
    # Per-SKU P1 tapes: shape (n_sku, MAX_EVAL_TIERS, n_obs)
    sku_p1_nets: np.ndarray,
    sku_p1_dds: np.ndarray,
    sku_p1_flgs: np.ndarray,
    # Per-SKU P2 tapes: shape (n_sku, MAX_EVAL_TIERS, n_obs)
    sku_p2_nets: np.ndarray,
    sku_p2_dds: np.ndarray,
    sku_p2_flgs: np.ndarray,
    # Per-SKU Funded tapes: shape (n_sku, 3, n_obs) -> 0=normal, 1=amber, 2=red
    sku_fn_nets: np.ndarray,
    sku_fn_dds: np.ndarray,
    sku_fn_flgs: np.ndarray,
    # Schedule tier metadata (for DP mode) & standard knobs
    eval_is_dp: int,
    p1_tier_eq_min: np.ndarray,
    p1_tier_eq_max: np.ndarray,
    p1_tier_mult: np.ndarray,
    p1_n_tiers: int,
    p2_tier_eq_min: np.ndarray,
    p2_tier_eq_max: np.ndarray,
    p2_tier_mult: np.ndarray,
    p2_n_tiers: int,
    p1_lock_trigger: float,
    p2_lock_trigger: float,
    p1_lock_frac: float,
    p2_lock_frac: float,
    eval_amber_dd: float,
    eval_amber_mult: float,
    eval_red_dd: float,
    eval_red_mult: float,
    eval_p1_kill_daily: float,
    eval_p2_kill_daily: float,
    eval_p1_kill_static: float,
    eval_p2_kill_static: float,
    eval_sizing_mode: int,
    fn_amber_dd: float,
    fn_red_dd: float,
    fn_kill_daily: float,
    fn_kill_static: float,
    # SKU contract arrays: length n_sku (ordered ascending: 10K, 25K, 50K, 100K, 200K)
    tpl_cap: np.ndarray,
    tpl_fee_usd: np.ndarray,
    tpl_card_fx_frac: np.ndarray,
    tpl_wd_fee_pct: np.ndarray,
    tpl_refund_pct: np.ndarray,
    tpl_p1_target: np.ndarray,
    tpl_p2_target: np.ndarray,
    tpl_daily_lim: np.ndarray,
    tpl_static_lim: np.ndarray,
    tpl_min_days: np.ndarray,
    tpl_split: np.ndarray,
    tpl_split_max: np.ndarray,
    tpl_payout_cycle: np.ndarray,
    tpl_min_payout: np.ndarray,
    # Fleet configuration
    concurrency_code: int,  # 0=CONSERVATIVE_1_TICKET, 1=GATED_STAGGER, 2=AGGRESSIVE_PARALLEL
    alloc_code: int,  # 0=P1_RECOUP_FIRST, 1=P2_BALANCED_40_40_20, 2=P3_SCALE_80_20
    init_bankroll_usd: float,
    max_slots: int,
    eval_fail_cooldown_days: int,
    funded_dd_freeze_frac: float,
    firm_max_funded_cap: float,
    firm_max_single_challenge: float,
    firm_max_scaled_cap: float,
    enable_scaling_plan: bool,
    reserve_cap_tickets: float,
    recoup_cash_pct: float,
    upgrade_scale_pct: float,
    own_book_pct: float,
) -> tuple[np.ndarray, ...]:
    """Shared-Path Multi-Account Fleet Simulator (`rho > 0.999`) with ZERO static-kill ratchet bug.

    Every active slot steps through the exact same `src = idx_matrix[b, d]`.
    Enforces:
      - `s_bal[s] > ea_static_floor + 1e-9` static-kill floor guard (ZERO ratchet bug!).
      - FTMO `$400K` active base Funded cap, `$200K`/Challenge, Scaling Plan `+25%` every `4m`
        up to `$2M` (`80% -> 90%`).
      - Full first-ticket P1 & P2 instrumentation (`first_ticket_p1_pass_day`, `first_ticket_fail_stage`).
      - Exact cash conservation (`accounting_err_36m == 0`, zero notional double counting).
    """
    n_paths, horizon = idx_matrix.shape
    n_sku = len(tpl_cap)

    min_fee_reg = 1e18
    top_fee_reg = 0.0
    min_rung_cap = 1e18
    for i in range(n_sku):
        efr = tpl_fee_usd[i] * (1.0 + tpl_card_fx_frac[i])
        if efr < min_fee_reg:
            min_fee_reg = efr
        if efr > top_fee_reg:
            top_fee_reg = efr
        if tpl_cap[i] < min_rung_cap:
            min_rung_cap = tpl_cap[i]
    reserve_cap_usd = max(min_fee_reg * 2.0, top_fee_reg * reserve_cap_tickets)

    # Outputs per path
    net_24m = np.zeros(n_paths, dtype=np.float64)
    net_36m = np.zeros(n_paths, dtype=np.float64)
    wealth_24m = np.zeros(n_paths, dtype=np.float64)
    wealth_36m = np.zeros(n_paths, dtype=np.float64)
    own_book_36m = np.zeros(n_paths, dtype=np.float64)
    recoup_cash_36m = np.zeros(n_paths, dtype=np.float64)
    challenge_cash_36m = np.zeros(n_paths, dtype=np.float64)
    fees_24m = np.zeros(n_paths, dtype=np.float64)
    fees_36m = np.zeros(n_paths, dtype=np.float64)
    payouts_36m = np.zeros(n_paths, dtype=np.float64)
    refunds_36m = np.zeros(n_paths, dtype=np.float64)
    gross_payouts_36m = np.zeros(n_paths, dtype=np.float64)
    accounting_err_36m = np.zeros(n_paths, dtype=np.float64)

    ruined_ever = np.zeros(n_paths, dtype=np.int8)
    ruined_24m = np.zeros(n_paths, dtype=np.int8)
    first_ruin_day = np.full(n_paths, -1, dtype=np.int32)
    first_funded_day = np.full(n_paths, -1, dtype=np.int32)
    first_funded_breach_day = np.full(n_paths, -1, dtype=np.int32)
    first_ticket_p1_pass_day = np.full(n_paths, -1, dtype=np.int32)
    first_ticket_pass_day = np.full(n_paths, -1, dtype=np.int32)
    first_ticket_fail_day = np.full(n_paths, -1, dtype=np.int32)
    first_ticket_fail_stage = np.zeros(n_paths, dtype=np.int8)
    pay1_day = np.full(n_paths, -1, dtype=np.int32)

    bot_kill_events = np.zeros(n_paths, dtype=np.int32)
    firm_breach_events = np.zeros(n_paths, dtype=np.int32)
    eval_breach_events = np.zeros(n_paths, dtype=np.int32)
    funded_breach_events = np.zeros(n_paths, dtype=np.int32)
    firm_breach_daily_any = np.zeros(n_paths, dtype=np.int8)
    firm_breach_maxdd_any = np.zeros(n_paths, dtype=np.int8)
    simult_fail_any = np.zeros(n_paths, dtype=np.int8)

    funded_dry_tot = np.zeros(n_paths, dtype=np.int32)
    funded_dry_zero = np.zeros(n_paths, dtype=np.int32)
    funded_max_dry_streak = np.zeros(n_paths, dtype=np.int32)

    max_base_funded_usd = np.zeros(n_paths, dtype=np.float64)
    max_scaled_funded_usd = np.zeros(n_paths, dtype=np.float64)
    scaling_upgrades_cnt = np.zeros(n_paths, dtype=np.int32)
    e1_blocks_cnt = np.zeros(n_paths, dtype=np.int32)
    e2_blocks_cnt = np.zeros(n_paths, dtype=np.int32)
    e4_blocks_cnt = np.zeros(n_paths, dtype=np.int32)
    all_fn_entries = np.zeros(n_paths, dtype=np.int32)
    all_fn_breach_12m = np.zeros(n_paths, dtype=np.int32)
    all_fn_censored_12m = np.zeros(n_paths, dtype=np.int32)

    # Reusable per-slot state arrays
    s_stage = np.zeros(max_slots, dtype=np.int8)
    s_tpl = np.full(max_slots, -1, dtype=np.int32)
    s_bal = np.zeros(max_slots, dtype=np.float64)
    s_tdays = np.zeros(max_slots, dtype=np.int32)
    s_cycd = np.zeros(max_slots, dtype=np.int32)
    s_ref = np.zeros(max_slots, dtype=np.int8)
    s_pcnt = np.zeros(max_slots, dtype=np.int32)
    s_paid_fee = np.zeros(max_slots, dtype=np.float64)
    s_base_cap = np.zeros(max_slots, dtype=np.float64)
    s_cur_cap = np.zeros(max_slots, dtype=np.float64)
    s_inv_cur_cap = np.zeros(max_slots, dtype=np.float64)
    s_scale_mult = np.ones(max_slots, dtype=np.float64)
    s_cur_split = np.zeros(max_slots, dtype=np.float64)
    s_scale_days = np.zeros(max_slots, dtype=np.int32)
    s_scale_prof = np.zeros(max_slots, dtype=np.float64)
    s_scale_pays = np.zeros(max_slots, dtype=np.int32)
    s_fn_enter_d = np.full(max_slots, -1, dtype=np.int32)
    s_fn_12m_done = np.zeros(max_slots, dtype=np.int8)
    s_is_first_ticket = np.zeros(max_slots, dtype=np.int8)
    s_is_first_funded = np.zeros(max_slots, dtype=np.int8)

    if concurrency_code == 0:  # CONSERVATIVE_1_TICKET
        max_conc_evals = 1
        first_res_mult = 3.0
        add_res_mult = 3.0
    elif concurrency_code == 1:  # GATED_STAGGER
        max_conc_evals = 2
        first_res_mult = 2.0
        add_res_mult = 2.0
    else:  # AGGRESSIVE_PARALLEL
        max_conc_evals = 3
        first_res_mult = 2.0
        add_res_mult = 1.25

    prev_used_hi = max_slots
    for b in range(n_paths):
        challenge_cash = init_bankroll_usd
        recoup_cash = 0.0
        own_book = 0.0
        recouped_so_far = 0.0

        tot_fees = 0.0
        tot_payouts = 0.0
        tot_refunds = 0.0
        tot_gross_payouts = 0.0

        for s in range(prev_used_hi):
            s_stage[s] = 0
            s_tpl[s] = -1
            s_bal[s] = 0.0
            s_tdays[s] = 0
            s_cycd[s] = 0
            s_ref[s] = 0
            s_pcnt[s] = 0
            s_paid_fee[s] = 0.0
            s_base_cap[s] = 0.0
            s_cur_cap[s] = 0.0
            s_inv_cur_cap[s] = 0.0
            s_scale_mult[s] = 1.0
            s_cur_split[s] = 0.80
            s_scale_days[s] = 0
            s_scale_prof[s] = 0.0
            s_scale_pays[s] = 0
            s_fn_enter_d[s] = -1
            s_fn_12m_done[s] = 0
            s_is_first_ticket[s] = 0
            s_is_first_funded[s] = 0

        firm_base_fn = 0.0
        firm_scaled_fn = 0.0
        firm_eval_pipe = 0.0

        first_ticket_launched = False
        f_tk_p1_pass = -1
        f_tk_pass = -1
        f_tk_fail = -1
        f_tk_fail_st = 0
        f_fn_day = -1
        f_fn_br_day = -1
        f_pay1 = -1
        f_ruin_d = -1
        had_ruin = 0
        had_ruin_24 = 0
        recorded_24 = False

        bk_ev = 0
        fb_ev = 0
        eb_ev = 0
        fnb_ev = 0
        fb_d_any = 0
        fb_m_any = 0
        sim_fail = 0

        eval_cooldown_until = -1
        e1_blk = 0
        e2_blk = 0
        e4_blk = 0
        scale_up_cnt = 0

        fn_m_days = 0
        fn_m_paid = 0
        cur_dry = 0
        best_dry = 0
        tot_fm = 0
        zero_fm = 0

        best_base_fn = 0.0
        best_scaled_fn = 0.0
        p_fn_ent = 0
        p_fn_br12 = 0
        p_fn_cens12 = 0
        used_hi = 0
        max_used_hi = 0

        active_total = 0
        active_evals = 0
        active_funded = 0
        has_s2_or_s5 = False
        any_funded_in_dd_freeze = False

        for d in range(horizon):
            # 1. Fleet Admission Engine
            in_e1_cooldown = d < eval_cooldown_until
            can_try_buy = (active_evals < max_conc_evals) and (challenge_cash >= min_fee_reg - 1e-9)
            if can_try_buy and active_total > 0:
                if concurrency_code == 0 and (
                    active_evals > 0
                    or active_funded == 0
                    or challenge_cash < min_fee_reg * add_res_mult - 1e-9
                ):
                    can_try_buy = False
                elif concurrency_code == 1 and (
                    (not has_s2_or_s5) or challenge_cash < min_fee_reg * add_res_mult - 1e-9
                ):
                    can_try_buy = False
                elif concurrency_code == 2 and active_evals > 0 and challenge_cash < min_fee_reg * add_res_mult - 1e-9:
                    can_try_buy = False

            if in_e1_cooldown and active_evals < max_conc_evals and challenge_cash >= min_fee_reg - 1e-9:
                e1_blk += 1
            elif any_funded_in_dd_freeze and active_evals < max_conc_evals and challenge_cash >= min_fee_reg - 1e-9:
                e2_blk += 1
            elif can_try_buy:
                e4_saturated = (firm_base_fn + firm_eval_pipe + min_rung_cap) > firm_max_funded_cap + 1e-6
                if e4_saturated:
                    chk_mult = first_res_mult if active_total == 0 else add_res_mult
                    if challenge_cash >= min_fee_reg * chk_mult - 1e-9:
                        e4_blk += 1
                else:
                    for s in range(max_slots):
                        if s_stage[s] != 0:
                            continue
                        if active_evals >= max_conc_evals:
                            break

                        allow_open = False
                        res_mult = first_res_mult
                        allow_fb_min = False

                        if active_total == 0:
                            allow_open = True
                            res_mult = first_res_mult
                            allow_fb_min = True
                        elif concurrency_code == 0:
                            if active_evals == 0 and active_funded >= 1:
                                allow_open = True
                                res_mult = add_res_mult
                                allow_fb_min = False
                        elif concurrency_code == 1:
                            if has_s2_or_s5:
                                allow_open = True
                                res_mult = add_res_mult
                                allow_fb_min = False
                        else:
                            allow_open = True
                            res_mult = first_res_mult if active_evals == 0 else add_res_mult
                            allow_fb_min = active_evals == 0

                        if not allow_open:
                            break

                        rung = _pick_ladder_rung_numba(
                            challenge_cash,
                            tpl_cap,
                            tpl_fee_usd,
                            tpl_card_fx_frac,
                            firm_base_fn,
                            firm_eval_pipe,
                            firm_max_funded_cap,
                            firm_max_single_challenge,
                            res_mult,
                            allow_fb_min,
                        )
                        if rung < 0:
                            if challenge_cash >= min_fee_reg * res_mult - 1e-9:
                                e4_blk += 1
                            break

                        base_fee = tpl_fee_usd[rung]
                        ef = base_fee * (1.0 + tpl_card_fx_frac[rung])
                        if challenge_cash < ef - 1e-9:
                            break

                        challenge_cash -= ef
                        tot_fees += ef
                        cap = tpl_cap[rung]
                        s_tpl[s] = rung
                        s_stage[s] = 1
                        s_bal[s] = cap
                        s_tdays[s] = 0
                        s_cycd[s] = 0
                        s_ref[s] = 0
                        s_pcnt[s] = 0
                        s_paid_fee[s] = base_fee
                        s_base_cap[s] = cap
                        s_cur_cap[s] = cap
                        s_inv_cur_cap[s] = 1.0 / cap
                        s_scale_mult[s] = 1.0
                        s_cur_split[s] = tpl_split[rung]
                        s_scale_days[s] = 0
                        s_scale_prof[s] = 0.0
                        s_scale_pays[s] = 0
                        s_fn_enter_d[s] = -1
                        s_fn_12m_done[s] = 0
                        if s + 1 > used_hi:
                            used_hi = s + 1
                        if used_hi > max_used_hi:
                            max_used_hi = used_hi
                        if not first_ticket_launched:
                            first_ticket_launched = True
                            s_is_first_ticket[s] = 1
                        else:
                            s_is_first_ticket[s] = 0
                        s_is_first_funded[s] = 0
                        active_evals += 1
                        active_total += 1
                        firm_eval_pipe += cap

            # 2. Check true bankroll ruin & early-exit absorbing state
            if active_total == 0:
                total_liq_now = challenge_cash + recoup_cash + own_book
                if (not in_e1_cooldown) and total_liq_now < min_fee_reg - 1e-9:
                    had_ruin = 1
                    if f_ruin_d < 0:
                        f_ruin_d = d + 1
                    if d < 504:
                        had_ruin_24 = 1
                if (not in_e1_cooldown) and challenge_cash < min_fee_reg - 1e-9:
                    break

            # 3. SHARED MARKET PATH STEP (`src = idx_matrix[b, d]`)
            src = idx_matrix[b, d]
            fails_today = 0
            any_funded_today = 0
            paid_today = 0
            tot_base_fn_today = 0.0
            tot_scaled_fn_today = 0.0

            next_active_total = 0
            next_active_evals = 0
            next_active_funded = 0
            next_has_s2_or_s5 = False
            next_any_funded_dd = False
            firm_base_fn = 0.0
            firm_scaled_fn = 0.0
            firm_eval_pipe = 0.0

            for s in range(used_hi):
                st = s_stage[s]
                if st <= 0:
                    continue
                tid = s_tpl[s]
                base_cap = s_base_cap[s]
                cur_cap = s_cur_cap[s]
                inv_cur_cap = s_inv_cur_cap[s]
                scale_mult = s_scale_mult[s]

                if st == 3:
                    any_funded_today = 1
                    tot_base_fn_today += base_cap
                    tot_scaled_fn_today += cur_cap

                eq_pct = (s_bal[s] - cur_cap) * inv_cur_cap
                static_dd_pct = -eq_pct if eq_pct < 0.0 else 0.0
                reg_frac = 1.0

                if st == 1:
                    if eval_is_dp == 1:
                        tidx = _select_dp_tier_idx(
                            eq_pct * 100.0, p1_tier_eq_min, p1_tier_eq_max, p1_tier_mult, p1_n_tiers
                        )
                        net_raw = sku_p1_nets[tid, tidx, src]
                        dd_raw = sku_p1_dds[tid, tidx, src]
                        flg = sku_p1_flgs[tid, tidx, src]
                    else:
                        if static_dd_pct >= eval_red_dd - 1e-12:
                            net_raw = sku_p1_nets[tid, 3, src]
                            dd_raw = sku_p1_dds[tid, 3, src]
                            flg = sku_p1_flgs[tid, 3, src]
                            reg_frac = eval_red_mult
                        elif static_dd_pct >= eval_amber_dd - 1e-12:
                            net_raw = sku_p1_nets[tid, 2, src]
                            dd_raw = sku_p1_dds[tid, 2, src]
                            flg = sku_p1_flgs[tid, 2, src]
                            reg_frac = eval_amber_mult
                        elif p1_lock_trigger > 0.0 and eq_pct >= tpl_p1_target[tid] * p1_lock_trigger - 1e-12:
                            net_raw = sku_p1_nets[tid, 1, src]
                            dd_raw = sku_p1_dds[tid, 1, src]
                            flg = sku_p1_flgs[tid, 1, src]
                            reg_frac = p1_lock_frac
                        else:
                            net_raw = sku_p1_nets[tid, 0, src]
                            dd_raw = sku_p1_dds[tid, 0, src]
                            flg = sku_p1_flgs[tid, 0, src]
                    ea_daily_pct = eval_p1_kill_daily
                    ea_static_pct = eval_p1_kill_static
                    cur_tgt = tpl_p1_target[tid]
                elif st == 2:
                    if eval_is_dp == 1:
                        tidx = _select_dp_tier_idx(
                            eq_pct * 100.0, p2_tier_eq_min, p2_tier_eq_max, p2_tier_mult, p2_n_tiers
                        )
                        net_raw = sku_p2_nets[tid, tidx, src]
                        dd_raw = sku_p2_dds[tid, tidx, src]
                        flg = sku_p2_flgs[tid, tidx, src]
                    else:
                        if static_dd_pct >= eval_red_dd - 1e-12:
                            net_raw = sku_p2_nets[tid, 3, src]
                            dd_raw = sku_p2_dds[tid, 3, src]
                            flg = sku_p2_flgs[tid, 3, src]
                            reg_frac = eval_red_mult
                        elif static_dd_pct >= eval_amber_dd - 1e-12:
                            net_raw = sku_p2_nets[tid, 2, src]
                            dd_raw = sku_p2_dds[tid, 2, src]
                            flg = sku_p2_flgs[tid, 2, src]
                            reg_frac = eval_amber_mult
                        elif p2_lock_trigger > 0.0 and eq_pct >= tpl_p2_target[tid] * p2_lock_trigger - 1e-12:
                            net_raw = sku_p2_nets[tid, 1, src]
                            dd_raw = sku_p2_dds[tid, 1, src]
                            flg = sku_p2_flgs[tid, 1, src]
                            reg_frac = p2_lock_frac
                        else:
                            net_raw = sku_p2_nets[tid, 0, src]
                            dd_raw = sku_p2_dds[tid, 0, src]
                            flg = sku_p2_flgs[tid, 0, src]
                    ea_daily_pct = eval_p2_kill_daily
                    ea_static_pct = eval_p2_kill_static
                    cur_tgt = tpl_p2_target[tid]
                else:
                    if static_dd_pct >= fn_red_dd - 1e-12:
                        net_raw = sku_fn_nets[tid, 2, src]
                        dd_raw = sku_fn_dds[tid, 2, src]
                        flg = sku_fn_flgs[tid, 2, src]
                    elif static_dd_pct >= fn_amber_dd - 1e-12:
                        net_raw = sku_fn_nets[tid, 1, src]
                        dd_raw = sku_fn_dds[tid, 1, src]
                        flg = sku_fn_flgs[tid, 1, src]
                    else:
                        net_raw = sku_fn_nets[tid, 0, src]
                        dd_raw = sku_fn_dds[tid, 0, src]
                        flg = sku_fn_flgs[tid, 0, src]
                    ea_daily_pct = fn_kill_daily
                    ea_static_pct = fn_kill_static
                    cur_tgt = 0.0

                eff_scale = scale_mult
                if st < 3 and eval_is_dp == 0 and eval_sizing_mode == 1:
                    s_head = ea_static_pct - static_dd_pct
                    if s_head < 0.0:
                        s_head = 0.0
                    b_scale = 1.0
                    if s_head < 0.035:
                        cand_b = s_head / 0.035
                        if cand_b < 0.25:
                            cand_b = 0.25
                        if cand_b < b_scale:
                            b_scale = cand_b
                    if cur_tgt > 0.0 and eq_pct > 0.0:
                        rem_t = cur_tgt - eq_pct
                        if rem_t < 0.0:
                            rem_t = 0.0
                        frac_r = rem_t / cur_tgt
                        if frac_r < 0.35:
                            cand_r = frac_r / 0.35
                            if cand_r < 0.35:
                                cand_r = 0.35
                            if cand_r < b_scale:
                                b_scale = cand_r
                    if reg_frac > 1e-9 and b_scale < reg_frac:
                        eff_scale *= b_scale / reg_frac

                net = net_raw * eff_scale
                dd = dd_raw * eff_scale

                # Firm hard DD floors (FTMO static DD + midnight-balance/initial daily DD)
                max_floor = cur_cap * (1.0 - tpl_static_lim[tid])
                daily_floor = s_bal[s] - cur_cap * tpl_daily_lim[tid]

                day_min = s_bal[s] - dd
                d_hit = day_min < daily_floor - 1e-9
                m_hit = day_min < max_floor - 1e-9

                # Separate BOT_AUTO_KILL vs FIRM_HARD_BREACH with ZERO-RATCHET static-kill floor!
                ea_daily_cut = cur_cap * ea_daily_pct if ea_daily_pct > 0.0 else 1e18
                ea_static_floor = cur_cap * (1.0 - ea_static_pct) if ea_static_pct > 0.0 else -1e18
                if (not d_hit) and (not m_hit):
                    daily_kill = dd > ea_daily_cut
                    static_kill = (s_bal[s] > ea_static_floor + 1e-9) and (day_min < ea_static_floor - 1e-9)
                    if daily_kill or static_kill:
                        bk_ev += 1
                        dd_eff = dd
                        if daily_kill:
                            cand_d = ea_daily_cut + cur_cap * 0.0020
                            if cand_d < dd_eff:
                                dd_eff = cand_d
                        if static_kill:
                            cand_s = (s_bal[s] - ea_static_floor) + cur_cap * 0.0020
                            if cand_s < 0.0:
                                cand_s = 0.0
                            if cand_s < dd_eff:
                                dd_eff = cand_s
                        if net > -dd_eff:
                            net = -dd_eff
                        day_min_eff = s_bal[s] - dd_eff
                        d_hit = day_min_eff < daily_floor - 1e-9
                        m_hit = day_min_eff < max_floor - 1e-9

                if d_hit or m_hit:
                    fails_today += 1
                    fb_ev += 1
                    if d_hit:
                        fb_d_any = 1
                    if m_hit:
                        fb_m_any = 1
                    if st < 3:
                        eb_ev += 1
                        if eval_fail_cooldown_days > 0:
                            cd_target = d + 1 + eval_fail_cooldown_days
                            if cd_target > eval_cooldown_until:
                                eval_cooldown_until = cd_target
                        if s_is_first_ticket[s] == 1 and f_tk_fail < 0 and f_tk_pass < 0:
                            f_tk_fail = d + 1
                            f_tk_fail_st = st
                    else:
                        fnb_ev += 1
                        if s_is_first_funded[s] == 1 and f_fn_br_day < 0:
                            f_fn_br_day = d + 1
                        if s_fn_12m_done[s] == 0 and s_fn_enter_d[s] >= 0:
                            if (d + 1 - s_fn_enter_d[s]) <= 252:
                                p_fn_br12 += 1
                            s_fn_12m_done[s] = 1
                    s_stage[s] = 0
                    s_tpl[s] = -1
                    s_bal[s] = 0.0
                    s_paid_fee[s] = 0.0
                    s_base_cap[s] = 0.0
                    s_cur_cap[s] = 0.0
                    s_is_first_ticket[s] = 0
                    s_is_first_funded[s] = 0
                    continue

                s_bal[s] += net
                if flg != 0:
                    s_tdays[s] += 1

                if st == 1:
                    if s_bal[s] >= cur_cap * (1.0 + tpl_p1_target[tid]) - 1e-9 and s_tdays[s] >= tpl_min_days[tid]:
                        if s_is_first_ticket[s] == 1 and f_tk_p1_pass < 0:
                            f_tk_p1_pass = d + 1
                        s_stage[s] = 2
                        s_bal[s] = cur_cap
                        s_tdays[s] = 0
                elif st == 2:
                    if s_bal[s] >= cur_cap * (1.0 + tpl_p2_target[tid]) - 1e-9 and s_tdays[s] >= tpl_min_days[tid]:
                        cur_f_base = 0.0
                        for s2 in range(used_hi):
                            if s_stage[s2] == 3:
                                cur_f_base += s_base_cap[s2]
                        if cur_f_base + base_cap <= firm_max_funded_cap + 1e-6:
                            s_stage[s] = 3
                            s_bal[s] = cur_cap
                            s_tdays[s] = 0
                            s_cycd[s] = 0
                            s_scale_days[s] = 0
                            s_scale_prof[s] = 0.0
                            s_scale_pays[s] = 0
                            s_fn_enter_d[s] = d + 1
                            s_fn_12m_done[s] = 0
                            p_fn_ent += 1
                            if s_is_first_ticket[s] == 1 and f_tk_pass < 0:
                                f_tk_pass = d + 1
                            if f_fn_day < 0:
                                f_fn_day = d + 1
                                s_is_first_funded[s] = 1
                elif st == 3:
                    s_cycd[s] += 1
                    s_scale_days[s] += 1
                    s_scale_prof[s] += net
                    if s_fn_12m_done[s] == 0 and s_fn_enter_d[s] >= 0 and (d + 1 - s_fn_enter_d[s]) >= 252:
                        s_fn_12m_done[s] = 1

                    # S6 Payout Harvest & S7 3-Bucket Allocator
                    if s_cycd[s] >= tpl_payout_cycle[tid]:
                        prof = s_bal[s] - cur_cap
                        if prof > 1e-6:
                            gross_share = prof * s_cur_split[s]
                            if gross_share >= tpl_min_payout[tid] - 1e-9:
                                s_pcnt[s] += 1
                                s_scale_pays[s] += 1
                                tot_gross_payouts += prof
                                net_payout_in = gross_share * (1.0 - tpl_wd_fee_pct[tid])
                                tot_payouts += net_payout_in
                                refund_in = 0.0
                                if s_ref[s] == 0 and tpl_refund_pct[tid] > 0.0:
                                    refund_in = s_paid_fee[s] * tpl_refund_pct[tid]
                                    tot_refunds += refund_in
                                    s_ref[s] = 1

                                total_in = net_payout_in + refund_in
                                paid_today = 1
                                if f_pay1 < 0:
                                    f_pay1 = d + 1

                                if alloc_code == 0:  # P1_RECOUP_FIRST
                                    shortfall = init_bankroll_usd - recouped_so_far
                                    if shortfall < 0.0:
                                        shortfall = 0.0
                                    to_recoup = total_in if total_in <= shortfall else shortfall
                                    recoup_cash += to_recoup
                                    recouped_so_far += to_recoup
                                    rem = total_in - to_recoup
                                    if rem > 0.0:
                                        to_up = rem * upgrade_scale_pct
                                        to_ob = rem * own_book_pct
                                        room = reserve_cap_usd - challenge_cash
                                        if room < 0.0:
                                            room = 0.0
                                        add_ch = to_up if to_up <= room else room
                                        challenge_cash += add_ch
                                        own_book += to_ob + (to_up - add_ch)
                                else:  # P2_BALANCED_40_40_20 or P3_SCALE_80_20
                                    to_rec = total_in * recoup_cash_pct
                                    to_up = total_in * upgrade_scale_pct
                                    to_ob = total_in * own_book_pct
                                    recoup_cash += to_rec
                                    recouped_so_far += to_rec
                                    room = reserve_cap_usd - challenge_cash
                                    if room < 0.0:
                                        room = 0.0
                                    add_ch = to_up if to_up <= room else room
                                    challenge_cash += add_ch
                                    own_book += to_ob + (to_up - add_ch)

                                s_bal[s] = cur_cap
                        s_cycd[s] = 0

                    # FTMO Scaling Plan (+25% every 4m = 84d, >=10% prof, >=2 payouts, up to $2M, 80%->90%)
                    if enable_scaling_plan and s_scale_days[s] >= FTMO_SCALING_INTERVAL_TRADING_DAYS:
                        if (
                            s_scale_prof[s] >= cur_cap * FTMO_SCALING_MIN_PROFIT_FRAC - 1e-9
                            and s_scale_pays[s] >= FTMO_SCALING_MIN_PAYOUTS
                            and s_bal[s] >= cur_cap - 1e-9
                        ):
                            cur_firm_scaled = 0.0
                            for s2 in range(used_hi):
                                if s_stage[s2] == 3:
                                    cur_firm_scaled += s_cur_cap[s2]
                            add_cap = base_cap * FTMO_SCALING_STEP_FRAC
                            max_room = firm_max_scaled_cap - cur_firm_scaled
                            if max_room < 0.0:
                                max_room = 0.0
                            if add_cap > max_room:
                                add_cap = max_room
                            if add_cap > 1e-6:
                                new_cap = cur_cap + add_cap
                                s_cur_cap[s] = new_cap
                                s_inv_cur_cap[s] = 1.0 / new_cap
                                s_scale_mult[s] = new_cap / base_cap
                                s_bal[s] = s_bal[s] + add_cap
                                s_cur_split[s] = tpl_split_max[tid]
                                scale_up_cnt += 1
                        s_scale_days[s] = 0
                        s_scale_prof[s] = 0.0
                        s_scale_pays[s] = 0

                st_end = s_stage[s]
                if st_end > 0:
                    next_active_total += 1
                    if st_end == 3:
                        next_active_funded += 1
                        next_has_s2_or_s5 = True
                        firm_base_fn += s_base_cap[s]
                        firm_scaled_fn += s_cur_cap[s]
                        if (s_cur_cap[s] - s_bal[s]) * s_inv_cur_cap[s] >= funded_dd_freeze_frac - 1e-12:
                            next_any_funded_dd = True
                    else:
                        next_active_evals += 1
                        firm_eval_pipe += s_base_cap[s]
                        if st_end == 2:
                            next_has_s2_or_s5 = True

            active_total = next_active_total
            active_evals = next_active_evals
            active_funded = next_active_funded
            has_s2_or_s5 = next_has_s2_or_s5
            any_funded_in_dd_freeze = next_any_funded_dd
            while used_hi > 0 and s_stage[used_hi - 1] <= 0:
                used_hi -= 1

            if fails_today >= 2:
                sim_fail = 1
            if tot_base_fn_today > best_base_fn:
                best_base_fn = tot_base_fn_today
            if tot_scaled_fn_today > best_scaled_fn:
                best_scaled_fn = tot_scaled_fn_today

            if any_funded_today == 1:
                fn_m_days += 1
                if paid_today == 1:
                    fn_m_paid = 1
                if fn_m_days >= 21:
                    tot_fm += 1
                    if fn_m_paid == 0:
                        zero_fm += 1
                        cur_dry += 1
                        if cur_dry > best_dry:
                            best_dry = cur_dry
                    else:
                        cur_dry = 0
                    fn_m_days = 0
                    fn_m_paid = 0

            if (not recorded_24) and (d + 1 == 504):
                w24 = challenge_cash + recoup_cash + own_book
                wealth_24m[b] = w24
                net_24m[b] = w24 - init_bankroll_usd
                fees_24m[b] = tot_fees
                recorded_24 = True

        prev_used_hi = max_used_hi
        for s in range(used_hi):
            if s_stage[s] == 3 and s_fn_12m_done[s] == 0 and s_fn_enter_d[s] >= 0:
                if (horizon - s_fn_enter_d[s]) < 252:
                    p_fn_cens12 += 1

        w_end = challenge_cash + recoup_cash + own_book
        if not recorded_24:
            wealth_24m[b] = w_end
            net_24m[b] = w_end - init_bankroll_usd
            fees_24m[b] = tot_fees

        wealth_36m[b] = w_end
        net_36m[b] = w_end - init_bankroll_usd
        own_book_36m[b] = own_book
        recoup_cash_36m[b] = recoup_cash
        challenge_cash_36m[b] = challenge_cash
        fees_36m[b] = tot_fees
        payouts_36m[b] = tot_payouts
        refunds_36m[b] = tot_refunds
        gross_payouts_36m[b] = tot_gross_payouts

        expected_w = init_bankroll_usd - tot_fees + tot_payouts + tot_refunds
        accounting_err_36m[b] = abs(w_end - expected_w)

        ruined_ever[b] = had_ruin
        ruined_24m[b] = had_ruin_24
        first_ruin_day[b] = f_ruin_d
        first_funded_day[b] = f_fn_day
        first_funded_breach_day[b] = f_fn_br_day
        first_ticket_p1_pass_day[b] = f_tk_p1_pass
        first_ticket_pass_day[b] = f_tk_pass
        first_ticket_fail_day[b] = f_tk_fail
        first_ticket_fail_stage[b] = f_tk_fail_st
        pay1_day[b] = f_pay1

        bot_kill_events[b] = bk_ev
        firm_breach_events[b] = fb_ev
        eval_breach_events[b] = eb_ev
        funded_breach_events[b] = fnb_ev
        firm_breach_daily_any[b] = fb_d_any
        firm_breach_maxdd_any[b] = fb_m_any
        simult_fail_any[b] = sim_fail

        funded_dry_tot[b] = tot_fm
        funded_dry_zero[b] = zero_fm
        funded_max_dry_streak[b] = best_dry

        max_base_funded_usd[b] = best_base_fn
        max_scaled_funded_usd[b] = best_scaled_fn
        scaling_upgrades_cnt[b] = scale_up_cnt
        e1_blocks_cnt[b] = e1_blk
        e2_blocks_cnt[b] = e2_blk
        e4_blocks_cnt[b] = e4_blk
        all_fn_entries[b] = p_fn_ent
        all_fn_breach_12m[b] = p_fn_br12
        all_fn_censored_12m[b] = p_fn_cens12

    return (
        net_24m,
        net_36m,
        wealth_24m,
        wealth_36m,
        own_book_36m,
        recoup_cash_36m,
        challenge_cash_36m,
        fees_24m,
        fees_36m,
        payouts_36m,
        refunds_36m,
        gross_payouts_36m,
        accounting_err_36m,
        ruined_ever,
        ruined_24m,
        first_ruin_day,
        first_funded_day,
        first_funded_breach_day,
        first_ticket_p1_pass_day,
        first_ticket_pass_day,
        first_ticket_fail_day,
        first_ticket_fail_stage,
        pay1_day,
        bot_kill_events,
        firm_breach_events,
        eval_breach_events,
        funded_breach_events,
        firm_breach_daily_any,
        firm_breach_maxdd_any,
        simult_fail_any,
        funded_dry_tot,
        funded_dry_zero,
        funded_max_dry_streak,
        max_base_funded_usd,
        max_scaled_funded_usd,
        scaling_upgrades_cnt,
        e1_blocks_cnt,
        e2_blocks_cnt,
        e4_blocks_cnt,
        all_fn_entries,
        all_fn_breach_12m,
        all_fn_censored_12m,
    )


def summarize_fleet_case(
    raw: tuple[np.ndarray, ...],
    *,
    case_id: str,
    schedule_id: str,
    bankroll_m_vnd: int,
    usd_vnd_rate: float,
    concurrency_mode: str,
    allocation_policy: str,
    friction_mult: float,
    horizon_days: int,
    strategy_quality: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Summarize complete Law 13-15 balanced metrics + instrumented P1/P2 for one Fleet case."""
    (
        net_24m,
        net_36m,
        _wealth_24m,
        wealth_36m,
        own_book_36m,
        recoup_cash_36m,
        challenge_cash_36m,
        fees_24m,
        fees_36m,
        payouts_36m,
        refunds_36m,
        _gross_payouts_36m,
        accounting_err_36m,
        ruined_ever,
        ruined_24m,
        first_ruin_day,
        first_funded_day,
        first_funded_breach_day,
        first_ticket_p1_pass_day,
        first_ticket_pass_day,
        first_ticket_fail_day,
        first_ticket_fail_stage,
        pay1_day,
        bot_kill_events,
        firm_breach_events,
        eval_breach_events,
        funded_breach_events,
        firm_breach_daily_any,
        firm_breach_maxdd_any,
        simult_fail_any,
        funded_dry_tot,
        funded_dry_zero,
        funded_max_dry_streak,
        max_base_funded_usd,
        max_scaled_funded_usd,
        scaling_upgrades_cnt,
        e1_blocks_cnt,
        e2_blocks_cnt,
        e4_blocks_cnt,
        all_fn_entries,
        all_fn_breach_12m,
        all_fn_censored_12m,
    ) = raw

    n = int(len(net_36m))
    fx = float(usd_vnd_rate)
    bankroll_vnd = float(bankroll_m_vnd) * 1_000_000.0
    bankroll_usd = bankroll_vnd / fx

    fleet_horizons: dict[str, dict[str, Any]] = {}
    first_ticket_horizons: dict[str, dict[str, Any]] = {}
    for m in HORIZON_MONTHS:
        cutoff = m * TRADING_DAYS_PER_MONTH
        if cutoff > horizon_days:
            continue
        f_p = (first_funded_day > 0) & (first_funded_day <= cutoff)
        f_f = (~f_p) & (first_ruin_day > 0) & (first_ruin_day <= cutoff)
        f_w = (~f_p) & (~f_f)
        fleet_horizons[f"{m}m"] = exact_partition_pct(int(np.sum(f_p)), int(np.sum(f_f)), int(np.sum(f_w)))

        t_p = (first_ticket_pass_day > 0) & (first_ticket_pass_day <= cutoff)
        t_f = (~t_p) & (first_ticket_fail_day > 0) & (first_ticket_fail_day <= cutoff)
        t_w = (~t_p) & (~t_f)
        first_ticket_horizons[f"{m}m"] = exact_partition_pct(int(np.sum(t_p)), int(np.sum(t_f)), int(np.sum(t_w)))

    # First-ticket instrumented P1 (12m) & P2 (12m elapsed conditional on entering P2)
    cut12 = TRADING_DAYS_PER_YEAR
    p1_p12 = (first_ticket_p1_pass_day > 0) & (first_ticket_p1_pass_day <= cut12)
    p1_f12 = (
        (~p1_p12)
        & (first_ticket_fail_day > 0)
        & (first_ticket_fail_stage == 1)
        & (first_ticket_fail_day <= cut12)
    )
    p1_w12 = (~p1_p12) & (~p1_f12)
    p1_part_12m = exact_partition_pct(int(np.sum(p1_p12)), int(np.sum(p1_f12)), int(np.sum(p1_w12)))

    ent_p2 = first_ticket_p1_pass_day > 0
    p2_p12 = ent_p2 & (first_ticket_pass_day > 0) & ((first_ticket_pass_day - first_ticket_p1_pass_day) <= cut12)
    p2_f12 = (
        ent_p2
        & (~p2_p12)
        & (first_ticket_fail_day > 0)
        & (first_ticket_fail_stage == 2)
        & ((first_ticket_fail_day - first_ticket_p1_pass_day) <= cut12)
    )
    p2_w12 = ent_p2 & (~p2_p12) & (~p2_f12)
    p2_part_12m = exact_partition_pct(int(np.sum(p2_p12)), int(np.sum(p2_f12)), int(np.sum(p2_w12)))

    # Funded 12m blowup + Wilson 95% UB
    entered_mask = first_funded_day > 0
    n_paths_entered = int(np.sum(entered_mask))
    if n_paths_entered > 0:
        fn_in = first_funded_day[entered_mask]
        fn_br = first_funded_breach_day[entered_mask]
        br_12m = (fn_br > 0) & ((fn_br - fn_in) <= TRADING_DAYS_PER_YEAR)
        full_12m = (fn_in + TRADING_DAYS_PER_YEAR) <= horizon_days
        n_br_12m = int(np.sum(br_12m))
        n_full_12m = int(np.sum(full_12m))
        n_cens_12m = n_paths_entered - n_full_12m
        blowup_12m_pct = round(100.0 * n_br_12m / n_paths_entered, 2)
        blowup_uncens_pct = round(100.0 * int(np.sum(br_12m & full_12m)) / n_full_12m, 2) if n_full_12m > 0 else 0.0
        wilson_ub_pct = round(100.0 * wilson_upper_95(n_br_12m, n_paths_entered), 2)
    else:
        n_br_12m = 0
        n_full_12m = 0
        n_cens_12m = 0
        blowup_12m_pct = 0.0
        blowup_uncens_pct = 0.0
        wilson_ub_pct = 100.0

    # Law 13 separate conditional vs unconditional Payout #1
    paid_mask = pay1_day > 0
    cal_pay1 = np.where(paid_mask, pay1_day * CALENDAR_DAYS_PER_TRADING_DAY, 1e9)
    cond_med_pay1 = round(float(np.median(cal_pay1[paid_mask])), 1) if bool(np.any(paid_mask)) else None
    uncond_med_365 = round(float(np.median(np.minimum(cal_pay1, 365.0))), 1)
    uncond_med_730 = round(float(np.median(np.minimum(cal_pay1, 730.0))), 1)

    tot_fm_sum = int(np.sum(funded_dry_tot))
    dry_fm_sum = int(np.sum(funded_dry_zero))
    dry_months_pct = round((100.0 * dry_fm_sum / tot_fm_sum) if tot_fm_sum > 0 else 100.0, 2)
    streak_sub = funded_max_dry_streak[funded_dry_tot > 0]
    starved_p50 = int(np.median(streak_sub)) if len(streak_sub) > 0 else 0
    starved_p95 = int(np.quantile(streak_sub, 0.95)) if len(streak_sub) > 0 else 0

    def _dist(arr_usd: np.ndarray) -> tuple[dict[str, float], dict[str, float]]:
        qu = {
            "mean": round(float(np.mean(arr_usd)), 2),
            "median": round(float(np.median(arr_usd)), 2),
            "p10": round(float(np.quantile(arr_usd, 0.10)), 2),
            "p90": round(float(np.quantile(arr_usd, 0.90)), 2),
        }
        qv = {k: round(v * fx, 0) for k, v in qu.items()}
        return qu, qv

    n24_usd, n24_vnd = _dist(net_24m)
    n36_usd, n36_vnd = _dist(net_36m)

    mean_fees_24m_usd = float(np.mean(fees_24m))
    mean_fees_36m_usd = float(np.mean(fees_36m))
    ev_per_fee_24m = round((float(np.mean(net_24m)) * fx) / max(1.0, mean_fees_24m_usd * fx), 3)
    ev_per_fee_36m = round((float(np.mean(net_36m)) * fx) / max(1.0, mean_fees_36m_usd * fx), 3)

    p_ruin_pct = round(100.0 * float(np.mean(ruined_ever > 0)), 2)
    p_ruin_24m_pct = round(100.0 * float(np.mean(ruined_24m > 0)), 2)
    p_net_le_0_24m_pct = round(100.0 * float(np.mean(net_24m <= 0.0)), 2)
    p_net_le_0_36m_pct = round(100.0 * float(np.mean(net_36m <= 0.0)), 2)

    return {
        "case_id": case_id,
        "schedule_id": schedule_id,
        "friction_mult": float(friction_mult),
        "n_paths": n,
        "horizon_days": int(horizon_days),
        "bankroll_m_vnd": int(bankroll_m_vnd),
        "bankroll_vnd": round(bankroll_vnd, 0),
        "bankroll_usd": round(bankroll_usd, 2),
        "usd_vnd_rate": fx,
        "concurrency_mode": concurrency_mode,
        "allocation_policy": allocation_policy,
        "monthly_pass_fail_pending": fleet_horizons,
        "first_ticket_pass_fail_pending": first_ticket_horizons,
        "first_ticket_p1_12m": p1_part_12m,
        "first_ticket_p2_12m_elapsed": p2_part_12m,
        "p1_pass_rate_pct": p1_part_12m["pass_pct"],
        "p1_fail_rate_pct": p1_part_12m["fail_pct"],
        "p1_pending_rate_pct": p1_part_12m["pending_pct"],
        "p2_pass_rate_pct": p2_part_12m["pass_pct"],
        "p2_fail_rate_pct": p2_part_12m["fail_pct"],
        "p2_pending_rate_pct": p2_part_12m["pending_pct"],
        "bot_auto_kill_pct": round(100.0 * float(np.mean(bot_kill_events > 0)), 2),
        "firm_hard_breach_pct": round(100.0 * float(np.mean(firm_breach_events > 0)), 2),
        "eval_hard_breach_pct": round(100.0 * float(np.mean(eval_breach_events > 0)), 2),
        "funded_hard_breach_pct": round(100.0 * float(np.mean(funded_breach_events > 0)), 2),
        "firm_hard_breach_daily_pct": round(100.0 * float(np.mean(firm_breach_daily_any > 0)), 2),
        "firm_hard_breach_maxdd_pct": round(100.0 * float(np.mean(firm_breach_maxdd_any > 0)), 2),
        "simultaneous_fail_pct": round(100.0 * float(np.mean(simult_fail_any > 0)), 2),
        "funded_12m_blowup": {
            "n_paths_entered_funded": n_paths_entered,
            "n_paths_full_12m_observed": n_full_12m,
            "n_paths_censored_lt_12m": n_cens_12m,
            "n_paths_breached_within_12m": n_br_12m,
            "blowup_12m_pct": blowup_12m_pct,
            "blowup_12m_uncensored_pct": blowup_uncens_pct,
            "wilson_95_ub_pct": wilson_ub_pct,
            "fleet_total_funded_entries": int(np.sum(all_fn_entries)),
            "fleet_total_funded_breaches_12m": int(np.sum(all_fn_breach_12m)),
            "fleet_total_funded_censored_12m": int(np.sum(all_fn_censored_12m)),
        },
        "net_profit_24m_usd": n24_usd,
        "net_profit_24m_vnd": n24_vnd,
        "net_profit_36m_usd": n36_usd,
        "net_profit_36m_vnd": n36_vnd,
        "median_24m_net_usd": n24_usd["median"],
        "median_24m_net_vnd": n24_vnd["median"],
        "median_36m_net_usd": n36_usd["median"],
        "median_36m_net_vnd": n36_vnd["median"],
        "mean_36m_net_usd": n36_usd["mean"],
        "mean_36m_net_vnd": n36_vnd["mean"],
        "mean_wealth_36m_usd": round(float(np.mean(wealth_36m)), 2),
        "mean_own_book_36m_usd": round(float(np.mean(own_book_36m)), 2),
        "mean_recoup_cash_36m_usd": round(float(np.mean(recoup_cash_36m)), 2),
        "mean_challenge_cash_36m_usd": round(float(np.mean(challenge_cash_36m)), 2),
        "max_cash_accounting_err_usd": float(np.max(accounting_err_36m)),
        "p_net_le_0_24m_pct": p_net_le_0_24m_pct,
        "p_net_le_0_36m_pct": p_net_le_0_36m_pct,
        "p_bankroll_ruin_24m_pct": p_ruin_24m_pct,
        "p_bankroll_ruin_pct": p_ruin_pct,
        "mean_total_fees_24m_usd": round(mean_fees_24m_usd, 2),
        "mean_total_fees_36m_usd": round(mean_fees_36m_usd, 2),
        "mean_total_fees_36m_vnd": round(mean_fees_36m_usd * fx, 0),
        "mean_total_payouts_36m_usd": round(float(np.mean(payouts_36m)), 2),
        "mean_total_refunds_36m_usd": round(float(np.mean(refunds_36m)), 2),
        "ev_per_1_vnd_fee_24m": ev_per_fee_24m,
        "ev_per_1_vnd_fee_36m": ev_per_fee_36m,
        "paid_any_pct": round(100.0 * float(np.mean(paid_mask)), 2),
        "cond_med_pay1_cal_days": cond_med_pay1,
        "uncond_med_pay1_cal_days_cap365": uncond_med_365,
        "uncond_med_pay1_cal_days_cap730": uncond_med_730,
        "funded_dry_months_pct": dry_months_pct,
        "longest_starved_month_streak_p50": starved_p50,
        "longest_starved_month_streak_p95": starved_p95,
        "max_active_base_funded_usd": round(float(np.max(max_base_funded_usd)), 2),
        "mean_max_base_funded_usd": round(float(np.mean(max_base_funded_usd)), 2),
        "max_active_scaled_funded_usd": round(float(np.max(max_scaled_funded_usd)), 2),
        "mean_scaling_upgrades": round(float(np.mean(scaling_upgrades_cnt)), 3),
        "fleet_guards_blocks": {
            "e1_eval_cooldown_mean": round(float(np.mean(e1_blocks_cnt)), 2),
            "e2_funded_dd_freeze_mean": round(float(np.mean(e2_blocks_cnt)), 2),
            "e4_funded_cap_mean": round(float(np.mean(e4_blocks_cnt)), 2),
        },
        "strategy_quality": dict(strategy_quality) if strategy_quality else {},
        "is_pareto_in_tier": False,
        "is_pareto_overall": False,
        "order_send_count": ORDER_SEND_COUNT,
        _SEAL_KEY: 0,
    }


def extract_pareto_frontier(cases: Sequence[Mapping[str, Any]], *, eps: float = 1e-9) -> list[str]:
    """Return non-dominated `case_id`s on `(median_36m_net_vnd MAX, ruin MIN, p_net_le_0 MIN)`."""
    n = len(cases)
    kept: list[tuple[float, float, float, str]] = []
    for i in range(n):
        ci = cases[i]
        net_i = float(ci["median_36m_net_vnd"])
        ruin_i = float(ci["p_bankroll_ruin_pct"])
        neg_i = float(ci["p_net_le_0_36m_pct"])
        dominated = False
        for j in range(n):
            if i == j:
                continue
            cj = cases[j]
            net_j = float(cj["median_36m_net_vnd"])
            ruin_j = float(cj["p_bankroll_ruin_pct"])
            neg_j = float(cj["p_net_le_0_36m_pct"])
            if (
                net_j >= net_i - eps
                and ruin_j <= ruin_i + eps
                and neg_j <= neg_i + eps
                and ((net_j > net_i + eps) or (ruin_j < ruin_i - eps) or (neg_j < neg_i - eps))
            ):
                dominated = True
                break
        if not dominated:
            kept.append((ruin_i, neg_i, -net_i, str(ci["case_id"])))
    kept.sort()
    return [cid for _, _, _, cid in kept]


# ---------------------------------------------------------------------------
# 5. Shared-Path Daily Correlation Proof (`rho > 0.999` vs Independent ~0.0)
# ---------------------------------------------------------------------------


def measure_shared_path_rho_proof(
    *,
    daily_net_acct_a: np.ndarray,
    daily_net_acct_b: np.ndarray,
    n_paths: int = 400,
    horizon_days: int = 252,
    block_len: int = BLOCK_LEN,
    seed: int = DEFAULT_SEED,
) -> dict[str, Any]:
    """Prove shared market path `rho > 0.999` vs independent-path negative mutation `rho ~ 0.0`."""
    a = np.asarray(daily_net_acct_a, dtype=np.float64)
    b = np.asarray(daily_net_acct_b, dtype=np.float64)
    if a.ndim != 1 or b.ndim != 1 or len(a) != len(b) or len(a) < 10:
        raise ValueError("daily_net arrays must be 1-D of equal length >= 10")
    if not (np.all(np.isfinite(a)) and np.all(np.isfinite(b))):
        raise ValueError("NON_FINITE_INPUT in shared-path correlation proof")

    idx_a = make_block_bootstrap_indices(len(a), horizon=horizon_days, n_paths=n_paths, block_len=block_len, seed=seed)
    idx_ind = make_block_bootstrap_indices(
        len(b), horizon=horizon_days, n_paths=n_paths, block_len=block_len, seed=seed + 99_991
    )

    def _calc(ia: np.ndarray, ib: np.ndarray) -> dict[str, float]:
        pa = a[ia]
        pb = b[ib]
        corrs: list[float] = []
        for i in range(n_paths):
            sa = float(np.std(pa[i]))
            sb = float(np.std(pb[i]))
            if sa > 1e-12 and sb > 1e-12:
                corrs.append(float(np.corrcoef(pa[i], pb[i])[0, 1]))
        return {
            "mean_rho": round(float(np.mean(corrs)) if corrs else 0.0, 6),
            "min_rho": round(float(np.min(corrs)) if corrs else 0.0, 6),
            "max_rho": round(float(np.max(corrs)) if corrs else 0.0, 6),
        }

    shared_stats = _calc(idx_a, idx_a)
    indep_stats = _calc(idx_a, idx_ind)
    return {
        "n_paths": int(n_paths),
        "horizon_days": int(horizon_days),
        "shared_path_true": shared_stats,
        "independent_negative_mutation": indep_stats,
        "shared_path_rho_gt_0_999": bool(shared_stats["mean_rho"] > 0.999),
        "independent_rho_near_zero": bool(abs(indep_stats["mean_rho"]) < 0.15),
    }


# ---------------------------------------------------------------------------
# 6. Trade-Level / Intraday DD Audit (NO Daily-Aggregation Smoothing!)
# ---------------------------------------------------------------------------


@njit(cache=False, nogil=True)
def _simulate_trade_level_intraday_dd_numba(
    idx_matrix: np.ndarray,
    day_tr_offsets: np.ndarray,  # length n_obs + 1
    tr_net_frac: np.ndarray,  # per-trade EOD net PnL / cap (at base P1 throttle)
    tr_adv_frac: np.ndarray,  # per-trade worst M1 intraday adverse excursion / cap (>= 0)
    day_net_frac: np.ndarray,  # daily closing net / cap (daily-close-only baseline)
    day_m1_dd_frac: np.ndarray,  # M1 minute-by-minute daily intraday DD / cap (daily-approx baseline)
    day_flg: np.ndarray,
    p1_target: float,
    daily_lim: float,
    static_lim: float,
    ea_kill_daily: float,
    ea_kill_static: float,
    amber_dd: float,
    amber_mult: float,
    red_dd: float,
    red_mult: float,
    min_days: int,
    gap_mult: float,
    mode: int,  # 0=daily_close_only, 1=daily_m1_approx, 2=trade_level_intraday
) -> tuple[int, int, int, int, int, float]:
    """Compare P1 5% Daily DD & 10% Static DD breaches across daily-close, M1-daily, and trade-level replay.

    Mode 2 (`trade_level_intraday`) steps through EVERY individual trade chronologically inside each
    bootstrapped day WITHOUT allowing later winning trades in the same day to mask an earlier
    intraday 5% Daily DD breach (plus exact `gap_mult` adverse shock audit).
    """
    n_paths, horizon = idx_matrix.shape
    n_pass = 0
    n_fail_daily = 0
    n_fail_static = 0
    n_fail_total = 0
    n_pending = 0
    worst_daily_dd_obs = 0.0

    for b in range(n_paths):
        bal = 1.0
        tdays = 0
        done = False

        for d in range(horizon):
            src = idx_matrix[b, d]
            eq_pct = bal - 1.0
            static_dd = -eq_pct if eq_pct < 0.0 else 0.0
            reg_scale = 1.0
            if static_dd >= red_dd - 1e-12:
                reg_scale = red_mult
            elif static_dd >= amber_dd - 1e-12:
                reg_scale = amber_mult

            day_start_bal = bal
            daily_floor = day_start_bal - daily_lim
            static_floor = 1.0 - static_lim
            ea_static_floor = 1.0 - ea_kill_static if ea_kill_static > 0.0 else -1e9
            eff_scale = bal * reg_scale

            if mode == 0:
                # Daily-close-only approximation (smoothing hides intraday adverse spikes!)
                net = day_net_frac[src] * eff_scale
                dd = (-net if net < 0.0 else 0.0) * gap_mult
                if dd > worst_daily_dd_obs:
                    worst_daily_dd_obs = dd
                d_hit = (day_start_bal - dd) < daily_floor - 1e-9
                m_hit = (day_start_bal - dd) < static_floor - 1e-9
                if (not d_hit) and (not m_hit) and (dd > ea_kill_daily):
                    dd_eff = ea_kill_daily + 0.0020
                    if dd < dd_eff:
                        dd_eff = dd
                    if net > -dd_eff:
                        net = -dd_eff
                    d_hit = (day_start_bal - dd_eff) < daily_floor - 1e-9
                    m_hit = (day_start_bal - dd_eff) < static_floor - 1e-9
                if d_hit or m_hit:
                    n_fail_total += 1
                    if d_hit:
                        n_fail_daily += 1
                    else:
                        n_fail_static += 1
                    done = True
                    break
                bal += net
                if bal <= ea_static_floor + 1e-9:
                    n_fail_total += 1
                    n_fail_static += 1
                    done = True
                    break
                if day_flg[src] != 0:
                    tdays += 1
            elif mode == 1:
                # M1 intraday daily-DD approximation (matching our standard MC kernel)
                net = day_net_frac[src] * eff_scale
                dd = day_m1_dd_frac[src] * eff_scale * gap_mult
                if dd > worst_daily_dd_obs:
                    worst_daily_dd_obs = dd
                d_hit = (day_start_bal - dd) < daily_floor - 1e-9
                m_hit = (day_start_bal - dd) < static_floor - 1e-9
                if (not d_hit) and (not m_hit) and (dd > ea_kill_daily):
                    dd_eff = ea_kill_daily + 0.0020
                    if dd < dd_eff:
                        dd_eff = dd
                    if net > -dd_eff:
                        net = -dd_eff
                    d_hit = (day_start_bal - dd_eff) < daily_floor - 1e-9
                    m_hit = (day_start_bal - dd_eff) < static_floor - 1e-9
                if d_hit or m_hit:
                    n_fail_total += 1
                    if d_hit:
                        n_fail_daily += 1
                    else:
                        n_fail_static += 1
                    done = True
                    break
                bal += net
                if bal <= ea_static_floor + 1e-9:
                    n_fail_total += 1
                    n_fail_static += 1
                    done = True
                    break
                if day_flg[src] != 0:
                    tdays += 1
            else:
                # Mode 2: Chronological Trade-Level Intraday Sequence Replay (ZERO daily smoothing!)
                t0 = day_tr_offsets[src]
                t1 = day_tr_offsets[src + 1]
                cur_eq = day_start_bal
                day_killed = False
                had_trade = False
                for ti in range(t0, t1):
                    if day_killed:
                        break
                    had_trade = True
                    t_adv = tr_adv_frac[ti] * eff_scale * gap_mult
                    t_net = tr_net_frac[ti] * eff_scale
                    # Worst intraday equity during trade `ti` relative to running intraday balance
                    tr_min_eq = cur_eq - t_adv
                    cur_daily_dd = day_start_bal - tr_min_eq
                    if cur_daily_dd > worst_daily_dd_obs:
                        worst_daily_dd_obs = cur_daily_dd
                    if tr_min_eq < daily_floor - 1e-9:
                        n_fail_total += 1
                        n_fail_daily += 1
                        done = True
                        break
                    if tr_min_eq < static_floor - 1e-9:
                        n_fail_total += 1
                        n_fail_static += 1
                        done = True
                        break
                    # EA intraday daily kill halts remaining same-day trades (+0.20% slip)
                    if cur_daily_dd > ea_kill_daily:
                        day_killed = True
                        slip_loss = (day_start_bal - cur_eq) + (ea_kill_daily - (day_start_bal - cur_eq)) + 0.0020
                        cand_eq = day_start_bal - slip_loss
                        if cand_eq < daily_floor - 1e-9:
                            n_fail_total += 1
                            n_fail_daily += 1
                            done = True
                            break
                        if cand_eq < static_floor - 1e-9:
                            n_fail_total += 1
                            n_fail_static += 1
                            done = True
                            break
                        cur_eq = cand_eq if cand_eq < (cur_eq + t_net) else (cur_eq + t_net)
                        break
                    cur_eq += t_net
                    # Also check concurrent-overlap M1 day floor after final trade of the day
                    if (day_start_bal - cur_eq) > worst_daily_dd_obs:
                        worst_daily_dd_obs = day_start_bal - cur_eq
                    if cur_eq < daily_floor - 1e-9:
                        n_fail_total += 1
                        n_fail_daily += 1
                        done = True
                        break
                    if cur_eq < static_floor - 1e-9:
                        n_fail_total += 1
                        n_fail_static += 1
                        done = True
                        break
                if done:
                    break
                # Also guard simultaneous multi-trade overlap spike (`day_m1_dd_frac`) if larger than sequential sum
                if (not day_killed) and had_trade:
                    m1_dd = day_m1_dd_frac[src] * eff_scale * gap_mult
                    if m1_dd > worst_daily_dd_obs:
                        worst_daily_dd_obs = m1_dd
                    if (day_start_bal - m1_dd) < daily_floor - 1e-9:
                        n_fail_total += 1
                        n_fail_daily += 1
                        done = True
                        break
                    if (day_start_bal - m1_dd) < static_floor - 1e-9:
                        n_fail_total += 1
                        n_fail_static += 1
                        done = True
                        break
                bal = cur_eq
                if bal <= ea_static_floor + 1e-9:
                    n_fail_total += 1
                    n_fail_static += 1
                    done = True
                    break
                if had_trade:
                    tdays += 1

            if bal >= 1.0 + p1_target - 1e-9 and tdays >= min_days:
                n_pass += 1
                done = True
                break

        if not done:
            n_pending += 1

    return n_pass, n_fail_daily, n_fail_static, n_fail_total, n_pending, worst_daily_dd_obs


def run_trade_level_intraday_dd_audit(
    *,
    schedule_id: str,
    contract_id: str,
    idx_matrix: np.ndarray,
    day_tr_offsets: np.ndarray,
    tr_net_frac: np.ndarray,
    tr_adv_frac: np.ndarray,
    day_net_frac: np.ndarray,
    day_m1_dd_frac: np.ndarray,
    day_flg: np.ndarray,
    p1_target: float = 0.10,
    daily_lim: float = 0.05,
    static_lim: float = 0.10,
    ea_kill_daily: float = 0.045,
    ea_kill_static: float = 0.0975,
    amber_dd: float = 0.055,
    amber_mult: float = 0.70,
    red_dd: float = 0.080,
    red_mult: float = 0.40,
    min_days: int = 4,
) -> dict[str, Any]:
    """Run 4-mode intraday/trade-level 5% Daily DD drift audit on `T4_TURBO_FAST` or `T5_MAX_THROTTLE_YOLO`."""
    n_paths = int(idx_matrix.shape[0])
    results: dict[str, dict[str, Any]] = {}
    configs = (
        ("daily_close_only_1_0x", 0, 1.0),
        ("daily_m1_approx_1_0x", 1, 1.0),
        ("trade_level_intraday_1_0x", 2, 1.0),
        ("trade_level_intraday_1_25x_gap", 2, 1.25),
    )
    for key, mode_id, gmult in configs:
        np_, nfd, nfs, nft, npend, wdd = _simulate_trade_level_intraday_dd_numba(
            idx_matrix,
            day_tr_offsets,
            tr_net_frac,
            tr_adv_frac,
            day_net_frac,
            day_m1_dd_frac,
            day_flg,
            float(p1_target),
            float(daily_lim),
            float(static_lim),
            float(ea_kill_daily),
            float(ea_kill_static),
            float(amber_dd),
            float(amber_mult),
            float(red_dd),
            float(red_mult),
            int(min_days),
            float(gmult),
            int(mode_id),
        )
        part = exact_partition_pct(int(np_), int(nft), int(npend))
        results[key] = {
            "p1_pass_pct": part["pass_pct"],
            "p1_fail_pct": part["fail_pct"],
            "p1_pending_pct": part["pending_pct"],
            "sum_pct": part["sum_pct"],
            "daily_5pct_hard_breach_pct": round(100.0 * float(nfd) / max(1, n_paths), 2),
            "static_10pct_or_halt_fail_pct": round(100.0 * float(nfs) / max(1, n_paths), 2),
            "worst_observed_daily_dd_pct": round(100.0 * float(wdd), 2),
        }

    hist_close_ge5 = int(np.sum((-day_net_frac) >= daily_lim - 1e-9))
    hist_m1_ge5 = int(np.sum(day_m1_dd_frac >= daily_lim - 1e-9))
    # Empirical worst sequential intraday DD across historical Dev days
    hist_seq_dd = np.zeros(len(day_flg), dtype=np.float64)
    for di in range(len(day_flg)):
        t0 = int(day_tr_offsets[di])
        t1 = int(day_tr_offsets[di + 1])
        cur = 0.0
        worst = float(day_m1_dd_frac[di])
        for ti in range(t0, t1):
            w_t = -(cur - float(tr_adv_frac[ti]))
            if w_t > worst:
                worst = w_t
            cur += float(tr_net_frac[ti])
            if -cur > worst:
                worst = -cur
        hist_seq_dd[di] = worst
    hist_seq_ge5 = int(np.sum(hist_seq_dd >= daily_lim - 1e-9))

    d_close = float(results["daily_close_only_1_0x"]["daily_5pct_hard_breach_pct"])
    d_m1 = float(results["daily_m1_approx_1_0x"]["daily_5pct_hard_breach_pct"])
    d_tr = float(results["trade_level_intraday_1_0x"]["daily_5pct_hard_breach_pct"])
    d_gap = float(results["trade_level_intraday_1_25x_gap"]["daily_5pct_hard_breach_pct"])

    return {
        "schedule_id": schedule_id,
        "contract_id": contract_id,
        "n_paths": n_paths,
        "horizon_days": int(idx_matrix.shape[1]),
        "modes": results,
        "drift_trade_minus_daily_close_pp": round(d_tr - d_close, 2),
        "drift_trade_minus_m1_daily_approx_pp": round(d_tr - d_m1, 2),
        "drift_gap125_minus_m1_daily_approx_pp": round(d_gap - d_m1, 2),
        "historical_dev_days_total": int(len(day_flg)),
        "historical_days_ge_5pct_daily_close_count": hist_close_ge5,
        "historical_days_ge_5pct_m1_intraday_count": hist_m1_ge5,
        "historical_days_ge_5pct_trade_seq_count": hist_seq_ge5,
        "historical_max_single_day_close_dd_pct": round(100.0 * float(np.max(np.maximum(0.0, -day_net_frac))), 2),
        "historical_max_single_day_m1_intraday_dd_pct": round(100.0 * float(np.max(day_m1_dd_frac)), 2),
        "historical_max_single_day_trade_seq_dd_pct": round(100.0 * float(np.max(hist_seq_dd)), 2),
        "order_send_count": ORDER_SEND_COUNT,
        _SEAL_KEY: 0,
    }


# ---------------------------------------------------------------------------
# 7. X13 / PC-Dev Parallel Shard Executor (Pure NumPy/Numba CLI Entrypoint)
# ---------------------------------------------------------------------------


def _get_idx_matrix(
    job: Mapping[str, Any],
    arrays: Mapping[str, np.ndarray],
    idx_cache: dict[tuple[int, int, int, int, int], np.ndarray],
) -> np.ndarray:
    """Resolve bootstrap index matrix either from bundled arrays or deterministically from `idx_spec`."""
    spec = job.get("idx_spec")
    if isinstance(spec, Mapping):
        key = (
            int(spec["n_obs"]),
            int(spec["horizon"]),
            int(spec["n_paths"]),
            int(spec.get("block_len", BLOCK_LEN)),
            int(spec.get("seed", DEFAULT_SEED)),
        )
        if key not in idx_cache:
            idx_cache[key] = make_block_bootstrap_indices(
                key[0], horizon=key[1], n_paths=key[2], block_len=key[3], seed=key[4]
            )
        return idx_cache[key]
    return np.ascontiguousarray(arrays[str(job["idx_key"])], dtype=np.int32)


def _execute_single_ticket_job(
    job: Mapping[str, Any],
    arrays: Mapping[str, np.ndarray],
    idx_cache: dict[tuple[int, int, int, int, int], np.ndarray],
) -> dict[str, Any]:
    prefix = str(job["array_prefix"])
    idx_matrix = _get_idx_matrix(job, arrays, idx_cache)

    raw = simulate_single_ticket_6tier_numba(
        idx_matrix,
        np.ascontiguousarray(arrays[f"{prefix}__p1_nets"], dtype=np.float64),
        np.ascontiguousarray(arrays[f"{prefix}__p1_dds"], dtype=np.float64),
        np.ascontiguousarray(arrays[f"{prefix}__p1_flgs"], dtype=np.int8),
        np.ascontiguousarray(job["p1_tier_eq_min"], dtype=np.float64),
        np.ascontiguousarray(job["p1_tier_eq_max"], dtype=np.float64),
        np.ascontiguousarray(job["p1_tier_mult"], dtype=np.float64),
        int(job["p1_n_tiers"]),
        np.ascontiguousarray(arrays[f"{prefix}__p2_nets"], dtype=np.float64),
        np.ascontiguousarray(arrays[f"{prefix}__p2_dds"], dtype=np.float64),
        np.ascontiguousarray(arrays[f"{prefix}__p2_flgs"], dtype=np.int8),
        np.ascontiguousarray(job["p2_tier_eq_min"], dtype=np.float64),
        np.ascontiguousarray(job["p2_tier_eq_max"], dtype=np.float64),
        np.ascontiguousarray(job["p2_tier_mult"], dtype=np.float64),
        int(job["p2_n_tiers"]),
        np.ascontiguousarray(arrays[f"{prefix}__fn_nets"], dtype=np.float64),
        np.ascontiguousarray(arrays[f"{prefix}__fn_dds"], dtype=np.float64),
        np.ascontiguousarray(arrays[f"{prefix}__fn_flgs"], dtype=np.int8),
        float(job["capital_usd"]),
        float(job["fee_usd"]),
        float(job["card_fx_fee_pct"]),
        float(job["withdrawal_fee_pct"]),
        float(job["ext_cash_refund_frac"]),
        float(job["p1_target"]),
        float(job["p2_target"]),
        float(job["daily_lim"]),
        float(job["static_lim"]),
        int(job["daily_reset_mode"]),
        int(job["min_days"]),
        int(job["min_prof_days"]),
        float(job["prof_day_thresh_frac"]),
        float(job["profit_split"]),
        int(job["payout_cycle_days"]),
        float(job["min_payout_usd"]),
        int(job["eval_is_dp"]),
        float(job["p1_lock_trigger"]),
        float(job["p2_lock_trigger"]),
        float(job["p1_lock_frac"]),
        float(job["p2_lock_frac"]),
        float(job["eval_amber_dd"]),
        float(job["eval_amber_mult"]),
        float(job["eval_red_dd"]),
        float(job["eval_red_mult"]),
        float(job["eval_p1_kill_daily"]),
        float(job["eval_p2_kill_daily"]),
        float(job["eval_p1_kill_static"]),
        float(job["eval_p2_kill_static"]),
        int(job["eval_sizing_mode"]),
        float(job["fn_amber_dd"]),
        float(job["fn_red_dd"]),
        float(job["fn_kill_daily"]),
        float(job["fn_kill_static"]),
        float(job.get("discount_rate_annual", 0.06)),
        bool(job.get("balance_compounding", True)),
    )
    summary = summarize_single_ticket_lifecycle(
        raw,
        funded_replay_metrics=job["funded_replay_metrics"],
        fee_usd=float(job["fee_usd"]),
        card_fx_fee_pct=float(job["card_fx_fee_pct"]),
        usd_vnd_rate=float(job["usd_vnd_rate"]),
        horizon_days=int(idx_matrix.shape[1]),
    )
    return {
        "job_kind": "single_ticket",
        "job_key": str(job["job_key"]),
        "cohort": str(job["cohort"]),
        "schedule_id": str(job["schedule_id"]),
        "contract_id": str(job["contract_id"]),
        "friction_mult": float(job["friction_mult"]),
        "phases": summary,
    }


def _execute_fleet_batch_job(
    job: Mapping[str, Any],
    arrays: Mapping[str, np.ndarray],
    idx_cache: dict[tuple[int, int, int, int, int], np.ndarray],
    *,
    max_workers: int = 2,
) -> dict[str, Any]:
    """Run all 81 `(bankroll x concurrency x allocation)` cases for one `(schedule, friction)` in parallel."""
    prefix = str(job["array_prefix"])
    idx_matrix = _get_idx_matrix(job, arrays, idx_cache)
    sku_p1_nets = np.ascontiguousarray(arrays[f"{prefix}__sku_p1_nets"], dtype=np.float64)
    sku_p1_dds = np.ascontiguousarray(arrays[f"{prefix}__sku_p1_dds"], dtype=np.float64)
    sku_p1_flgs = np.ascontiguousarray(arrays[f"{prefix}__sku_p1_flgs"], dtype=np.int8)
    sku_p2_nets = np.ascontiguousarray(arrays[f"{prefix}__sku_p2_nets"], dtype=np.float64)
    sku_p2_dds = np.ascontiguousarray(arrays[f"{prefix}__sku_p2_dds"], dtype=np.float64)
    sku_p2_flgs = np.ascontiguousarray(arrays[f"{prefix}__sku_p2_flgs"], dtype=np.int8)
    sku_fn_nets = np.ascontiguousarray(arrays[f"{prefix}__sku_fn_nets"], dtype=np.float64)
    sku_fn_dds = np.ascontiguousarray(arrays[f"{prefix}__sku_fn_dds"], dtype=np.float64)
    sku_fn_flgs = np.ascontiguousarray(arrays[f"{prefix}__sku_fn_flgs"], dtype=np.int8)

    p1_eq_min = np.ascontiguousarray(job["p1_tier_eq_min"], dtype=np.float64)
    p1_eq_max = np.ascontiguousarray(job["p1_tier_eq_max"], dtype=np.float64)
    p1_tmult = np.ascontiguousarray(job["p1_tier_mult"], dtype=np.float64)
    p2_eq_min = np.ascontiguousarray(job["p2_tier_eq_min"], dtype=np.float64)
    p2_eq_max = np.ascontiguousarray(job["p2_tier_eq_max"], dtype=np.float64)
    p2_tmult = np.ascontiguousarray(job["p2_tier_mult"], dtype=np.float64)

    tpl_cap = np.ascontiguousarray(job["tpl_cap"], dtype=np.float64)
    tpl_fee_usd = np.ascontiguousarray(job["tpl_fee_usd"], dtype=np.float64)
    tpl_card_fx = np.ascontiguousarray(job["tpl_card_fx_frac"], dtype=np.float64)
    tpl_wd_fee = np.ascontiguousarray(job["tpl_wd_fee_pct"], dtype=np.float64)
    tpl_refund = np.ascontiguousarray(job["tpl_refund_pct"], dtype=np.float64)
    tpl_p1_tgt = np.ascontiguousarray(job["tpl_p1_target"], dtype=np.float64)
    tpl_p2_tgt = np.ascontiguousarray(job["tpl_p2_target"], dtype=np.float64)
    tpl_dlim = np.ascontiguousarray(job["tpl_daily_lim"], dtype=np.float64)
    tpl_slim = np.ascontiguousarray(job["tpl_static_lim"], dtype=np.float64)
    tpl_mdays = np.ascontiguousarray(job["tpl_min_days"], dtype=np.int32)
    tpl_split = np.ascontiguousarray(job["tpl_split"], dtype=np.float64)
    tpl_split_max = np.ascontiguousarray(job["tpl_split_max"], dtype=np.float64)
    tpl_pcyc = np.ascontiguousarray(job["tpl_payout_cycle"], dtype=np.int32)
    tpl_minpay = np.ascontiguousarray(job["tpl_min_payout"], dtype=np.float64)

    fx = float(job["usd_vnd_rate"])
    sched_id = str(job["schedule_id"])
    fric = float(job["friction_mult"])
    sq = dict(job.get("strategy_quality") or {})
    bankrolls = [int(x) for x in job.get("bankroll_tiers_m_vnd", BANKROLL_TIERS_M_VND)]
    cmodes = [str(x) for x in job.get("concurrency_modes", CONCURRENCY_MODES)]
    apolicies = [str(x) for x in job.get("allocation_policies", ALLOCATION_POLICIES)]
    horizon_days = int(idx_matrix.shape[1])

    case_tuples = [(bm, cm, ap) for bm in bankrolls for cm in cmodes for ap in apolicies]

    def _run_one(item: tuple[int, str, str]) -> dict[str, Any]:
        bm, cm, ap = item
        rec_p, up_p, ob_p, rcap = ALLOCATION_PARAMS_MAP[ap]
        init_usd = (float(bm) * 1_000_000.0) / fx
        cid = f"B{bm}M__{cm}__{ap}"
        raw = simulate_fleet_6tier_numba(
            idx_matrix,
            sku_p1_nets,
            sku_p1_dds,
            sku_p1_flgs,
            sku_p2_nets,
            sku_p2_dds,
            sku_p2_flgs,
            sku_fn_nets,
            sku_fn_dds,
            sku_fn_flgs,
            int(job["eval_is_dp"]),
            p1_eq_min,
            p1_eq_max,
            p1_tmult,
            int(job["p1_n_tiers"]),
            p2_eq_min,
            p2_eq_max,
            p2_tmult,
            int(job["p2_n_tiers"]),
            float(job["p1_lock_trigger"]),
            float(job["p2_lock_trigger"]),
            float(job["p1_lock_frac"]),
            float(job["p2_lock_frac"]),
            float(job["eval_amber_dd"]),
            float(job["eval_amber_mult"]),
            float(job["eval_red_dd"]),
            float(job["eval_red_mult"]),
            float(job["eval_p1_kill_daily"]),
            float(job["eval_p2_kill_daily"]),
            float(job["eval_p1_kill_static"]),
            float(job["eval_p2_kill_static"]),
            int(job["eval_sizing_mode"]),
            float(job["fn_amber_dd"]),
            float(job["fn_red_dd"]),
            float(job["fn_kill_daily"]),
            float(job["fn_kill_static"]),
            tpl_cap,
            tpl_fee_usd,
            tpl_card_fx,
            tpl_wd_fee,
            tpl_refund,
            tpl_p1_tgt,
            tpl_p2_tgt,
            tpl_dlim,
            tpl_slim,
            tpl_mdays,
            tpl_split,
            tpl_split_max,
            tpl_pcyc,
            tpl_minpay,
            int(CONCURRENCY_CODE_MAP[cm]),
            int(ALLOCATION_CODE_MAP[ap]),
            init_usd,
            int(job.get("max_slots", DEFAULT_MAX_SLOTS)),
            int(job.get("eval_fail_cooldown_days", DEFAULT_EVAL_FAIL_COOLDOWN_DAYS)),
            float(job.get("funded_dd_freeze_frac", DEFAULT_FUNDED_DD_FREEZE_FRAC)),
            float(job.get("firm_max_funded_cap", FTMO_MAX_ACTIVE_FUNDED_USD)),
            float(job.get("firm_max_single_challenge", FTMO_MAX_SINGLE_CHALLENGE_USD)),
            float(job.get("firm_max_scaled_cap", FTMO_MAX_SCALED_FUNDED_USD)),
            bool(job.get("enable_scaling_plan", True)),
            float(rcap),
            float(rec_p),
            float(up_p),
            float(ob_p),
        )
        return summarize_fleet_case(
            raw,
            case_id=cid,
            schedule_id=sched_id,
            bankroll_m_vnd=bm,
            usd_vnd_rate=fx,
            concurrency_mode=cm,
            allocation_policy=ap,
            friction_mult=fric,
            horizon_days=horizon_days,
            strategy_quality=sq,
        )

    # Warm up JIT on first case synchronously to avoid concurrent Numba compilation contention
    cases_out: list[dict[str, Any]] = []
    if case_tuples:
        cases_out.append(_run_one(case_tuples[0]))
        rem = case_tuples[1:]
        if rem:
            workers = max(1, int(max_workers))
            if workers == 1:
                for it in rem:
                    cases_out.append(_run_one(it))
            else:
                with ThreadPoolExecutor(max_workers=workers) as pool:
                    cases_out.extend(list(pool.map(_run_one, rem)))

    # Mark per-bankroll-tier and overall Pareto frontier
    by_tier: dict[int, list[dict[str, Any]]] = {}
    for c in cases_out:
        by_tier.setdefault(int(c["bankroll_m_vnd"]), []).append(c)
    for _bm, grp in by_tier.items():
        tier_p = set(extract_pareto_frontier(grp))
        for c in grp:
            c["is_pareto_in_tier"] = str(c["case_id"]) in tier_p
    overall_p = set(extract_pareto_frontier(cases_out))
    for c in cases_out:
        c["is_pareto_overall"] = str(c["case_id"]) in overall_p

    return {
        "job_kind": "fleet_batch",
        "job_key": str(job["job_key"]),
        "schedule_id": sched_id,
        "friction_mult": fric,
        "cases": cases_out,
    }


def _execute_intraday_audit_job(
    job: Mapping[str, Any],
    arrays: Mapping[str, np.ndarray],
    idx_cache: dict[tuple[int, int, int, int, int], np.ndarray],
) -> dict[str, Any]:
    prefix = str(job["array_prefix"])
    idx_matrix = _get_idx_matrix(job, arrays, idx_cache)
    audit = run_trade_level_intraday_dd_audit(
        schedule_id=str(job["schedule_id"]),
        contract_id=str(job["contract_id"]),
        idx_matrix=idx_matrix,
        day_tr_offsets=np.ascontiguousarray(arrays[f"{prefix}__day_tr_offsets"], dtype=np.int32),
        tr_net_frac=np.ascontiguousarray(arrays[f"{prefix}__tr_net_frac"], dtype=np.float64),
        tr_adv_frac=np.ascontiguousarray(arrays[f"{prefix}__tr_adv_frac"], dtype=np.float64),
        day_net_frac=np.ascontiguousarray(arrays[f"{prefix}__day_net_frac"], dtype=np.float64),
        day_m1_dd_frac=np.ascontiguousarray(arrays[f"{prefix}__day_m1_dd_frac"], dtype=np.float64),
        day_flg=np.ascontiguousarray(arrays[f"{prefix}__day_flg"], dtype=np.int8),
        p1_target=float(job["p1_target"]),
        daily_lim=float(job["daily_lim"]),
        static_lim=float(job["static_lim"]),
        ea_kill_daily=float(job["ea_kill_daily"]),
        ea_kill_static=float(job["ea_kill_static"]),
        amber_dd=float(job["amber_dd"]),
        amber_mult=float(job["amber_mult"]),
        red_dd=float(job["red_dd"]),
        red_mult=float(job["red_mult"]),
        min_days=int(job["min_days"]),
    )
    return {
        "job_kind": "intraday_audit",
        "job_key": str(job["job_key"]),
        "audit": audit,
    }


def _execute_rho_proof_job(job: Mapping[str, Any], arrays: Mapping[str, np.ndarray]) -> dict[str, Any]:
    proof = measure_shared_path_rho_proof(
        daily_net_acct_a=np.ascontiguousarray(arrays[str(job["arr_a_key"])], dtype=np.float64),
        daily_net_acct_b=np.ascontiguousarray(arrays[str(job["arr_b_key"])], dtype=np.float64),
        n_paths=int(job.get("n_paths", 400)),
        horizon_days=int(job.get("horizon_days", 252)),
        block_len=int(job.get("block_len", BLOCK_LEN)),
        seed=int(job.get("seed", DEFAULT_SEED)),
    )
    return {
        "job_kind": "rho_proof",
        "job_key": str(job["job_key"]),
        "proof": proof,
    }


def run_spectrum_shard_payload(
    jobs: Sequence[Mapping[str, Any]],
    arrays: Mapping[str, np.ndarray],
    *,
    max_workers: int | None = None,
) -> dict[str, Any]:
    """Execute a heterogeneous list of Tier A / Tier B / Audit / Rho jobs on X13 or PC Dev."""
    t0 = time.perf_counter()
    env_threads = int(os.environ.get("NUMBA_NUM_THREADS", "2") or 2)
    workers = max(1, int(max_workers if max_workers is not None else env_threads))

    if "dev_max_ts_sec" in arrays:
        verify_pre_cutoff_timestamps(arrays["dev_max_ts_sec"])

    single_jobs = [j for j in jobs if j.get("job_kind") == "single_ticket"]
    fleet_jobs = [j for j in jobs if j.get("job_kind") == "fleet_batch"]
    audit_jobs = [j for j in jobs if j.get("job_kind") == "intraday_audit"]
    rho_jobs = [j for j in jobs if j.get("job_kind") == "rho_proof"]

    results: list[dict[str, Any]] = []
    idx_cache: dict[tuple[int, int, int, int, int], np.ndarray] = {}

    # Pre-build index matrices synchronously before thread fan-out
    for j in (*single_jobs, *fleet_jobs, *audit_jobs):
        _get_idx_matrix(j, arrays, idx_cache)

    # 1. Single-ticket Tier A jobs (warm up JIT on job 0, then fan out across workers)
    if single_jobs:
        results.append(_execute_single_ticket_job(single_jobs[0], arrays, idx_cache))
        rem_st = single_jobs[1:]
        if rem_st:
            if workers == 1:
                for sj in rem_st:
                    results.append(_execute_single_ticket_job(sj, arrays, idx_cache))
            else:
                with ThreadPoolExecutor(max_workers=workers) as pool:
                    results.extend(list(pool.map(lambda j: _execute_single_ticket_job(j, arrays, idx_cache), rem_st)))

    # 2. Fleet Tier B batches (each batch fans its 81 cases across all `workers` threads!)
    for fj in fleet_jobs:
        results.append(_execute_fleet_batch_job(fj, arrays, idx_cache, max_workers=workers))

    # 3. Trade-level intraday DD audit jobs
    for aj in audit_jobs:
        results.append(_execute_intraday_audit_job(aj, arrays, idx_cache))

    # 4. Shared-path rho proof jobs
    for rj in rho_jobs:
        results.append(_execute_rho_proof_job(rj, arrays))

    elapsed = round(time.perf_counter() - t0, 3)
    return {
        "schema": SHARD_RESULT_SCHEMA,
        "completed_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "worker_role": os.environ.get("NAQEX_WORKER_ROLE", "LOCAL"),
        "numba_num_threads": workers,
        "dev_cutoff_sec": DEV_CUTOFF_SEC,
        "dev_cutoff_day": DEV_CUTOFF_DAY,
        "order_send_capable": ORDER_SEND_CAPABLE,
        "order_send_count": ORDER_SEND_COUNT,
        "spend_vnd": SPEND_VND,
        _SEAL_KEY: 0,
        "job_count": len(results),
        "elapsed_sec": elapsed,
        "results": results,
    }


def _resolve_inputs_npz(npz_arg: str | None, batch_path: Path | None) -> Path:
    """Resolve `w5_spec_inputs.npz` inside X13 bundle `src_dir` or local working directory."""
    candidates: list[Path] = []
    target_name = "w5_spec_inputs.npz"
    if npz_arg:
        p = Path(npz_arg)
        target_name = p.name
        candidates.append(p)
        if batch_path is not None:
            candidates.append(batch_path.parent / p)
            candidates.append(batch_path.parent / p.name)
        candidates.append(Path.cwd() / p)
        candidates.append(Path.cwd() / p.name)
    if batch_path is not None:
        candidates.append(batch_path.parent / "w5_spec_inputs.npz")
    candidates.append(Path.cwd() / "w5_spec_inputs.npz")
    for c in candidates:
        if c.is_file():
            return c
    if batch_path is not None and batch_path.parent.is_dir():
        for found in sorted(batch_path.parent.rglob(target_name)):
            if found.is_file():
                return found
    raise FileNotFoundError(f"MISSING_SPEC_INPUTS_NPZ: searched {[str(x) for x in candidates]}")


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Wave 5 X13-Safe Spectrum & Fleet Monte Carlo Kernel Shard Worker.")
    ap.add_argument("--batch-file", default=None, help="Shard batch JSON file (or NAQEX_SHARD_BATCH_FILE).")
    ap.add_argument("--inputs-npz", default="w5_spec_inputs.npz", help="Bundled Dev-only stage arrays .npz.")
    ap.add_argument("--out-json", default=None, help="Output JSON path (or NAQEX_RESULT_DIR/shard_results.json).")
    args = ap.parse_args(list(argv) if argv is not None else None)

    batch_str = args.batch_file or os.environ.get("NAQEX_SHARD_BATCH_FILE")
    if not batch_str:
        raise ValueError("Provide --batch-file or set NAQEX_SHARD_BATCH_FILE")
    batch_path = Path(batch_str)
    batch_doc = json.loads(batch_path.read_text(encoding="utf-8-sig"))

    npz_path = _resolve_inputs_npz(args.inputs_npz, batch_path)
    npz_sha = hashlib.sha256(npz_path.read_bytes()).hexdigest()

    jobs: list[dict[str, Any]] = []
    for item in batch_doc.get("shards") or []:
        if isinstance(item, dict) and "jobs" in item:
            jobs.extend(item["jobs"])
        elif isinstance(item, dict) and "job_kind" in item:
            jobs.append(item)

    with np.load(npz_path, allow_pickle=False) as z:
        arrays = {k: z[k] for k in z.files}

    res = run_spectrum_shard_payload(jobs, arrays)
    res["inputs_npz_name"] = npz_path.name
    res["inputs_npz_sha256"] = npz_sha

    out_str = args.out_json
    if not out_str and os.environ.get("NAQEX_RESULT_DIR"):
        out_str = str(Path(os.environ["NAQEX_RESULT_DIR"]) / "shard_results.json")
    if out_str:
        _atomic_write_json(Path(out_str), res)
    else:
        print(json.dumps(res, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


__all__ = [
    "ALLOCATION_CODE_MAP",
    "ALLOCATION_PARAMS_MAP",
    "ALLOCATION_POLICIES",
    "BANKROLL_TIERS_M_VND",
    "BLOCK_LEN",
    "CALENDAR_DAYS_PER_TRADING_DAY",
    "CONCURRENCY_CODE_MAP",
    "CONCURRENCY_MODES",
    "DEFAULT_EVAL_FAIL_COOLDOWN_DAYS",
    "DEFAULT_FUNDED_DD_FREEZE_FRAC",
    "DEFAULT_HORIZON_DAYS",
    "DEFAULT_MAX_SLOTS",
    "DEFAULT_N_PATHS",
    "DEFAULT_SEED",
    "DEV_CUTOFF_DAY",
    "DEV_CUTOFF_SEC",
    "FTMO_MAX_ACTIVE_FUNDED_USD",
    "FTMO_MAX_SCALED_FUNDED_USD",
    "FTMO_MAX_SINGLE_CHALLENGE_USD",
    "HORIZON_MONTHS",
    "MAX_EVAL_TIERS",
    "ORDER_SEND_CAPABLE",
    "ORDER_SEND_COUNT",
    "P2_ELAPSED_MONTHS",
    "SCHEMA_VERSION",
    "SHARD_RESULT_SCHEMA",
    "SPEND_VND",
    "TRADING_DAYS_PER_MONTH",
    "TRADING_DAYS_PER_YEAR",
    "exact_partition_pct",
    "extract_pareto_frontier",
    "main",
    "make_block_bootstrap_indices",
    "measure_shared_path_rho_proof",
    "run_spectrum_shard_payload",
    "run_trade_level_intraday_dd_audit",
    "simulate_fleet_6tier_numba",
    "simulate_single_ticket_6tier_numba",
    "summarize_fleet_case",
    "summarize_single_ticket_lifecycle",
    "verify_pre_cutoff_days",
    "verify_pre_cutoff_timestamps",
    "wilson_upper_95",
]


if __name__ == "__main__":
    raise SystemExit(main())

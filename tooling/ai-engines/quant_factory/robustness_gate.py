"""Pre-Promotion Quant Robustness Gate (Dev < 2025-01-01 ONLY; holdout_rows_analysed = 0).

Implements 4 institutional anti-overfitting & drift-separation gates inspired by
live prop-trading forensics and integrated directly into `quant_factory`:

  1. Random-Entry Monte Carlo Benchmark (`>= 90%` beat rate):
     - Evaluates observed trades against `M` matched-duration, matched-SL, matched-friction
       random entries on the EXACT underlying sealed market bars (both 50/50 unbiased side
       and exact matched-side-mix to expose passive secular-trend drift on Gold/Indices/FX).
     - Also supports per-side BUY vs random-BUY and SELL vs random-SELL benchmarks.
  2. Separate Long / Short Edge Audit:
     - Splits BUY (`side > 0`) and SELL (`side < 0`) cohorts independently.
     - For bidirectional strategies, checks that BOTH BUY and SELL retain positive edge
       so a long-only drift bias cannot mask a losing short side.
     - For explicitly unidirectional strategies, enforces matched-side random-entry MC >= 90%.
  3. Top-5% Lucky Outlier Trade Removal:
     - Removes the top `trim_pct` (default 5%) winning trades (both conservative % of ALL
       trades and % of winning trades reported) and verifies net R and Profit Factor remain positive.
  4. Worst-Year Stability & Randomized-Subsample Worst-Year Ranking Score:
     - Evaluates calendar-year breakdown, positive-year ratio, worst calendar year floor,
       rolling 12-month worst window, and `mc_worst_year_p10_R` across `n_subsamples`
       randomized trade-drop / shifted-window variants (ranking candidates by worst year,
       not total historical return).

Hard Invariants:
  - `ORDER_SEND_CAPABLE = False`
  - `holdout_rows_analysed = 0` (asserts `NATIVE_FTMO_HOLDOUT_LOCK.json` + blocks any date >= `2025-01-01`).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from numba import njit

AI_ENGINES = Path(__file__).resolve().parents[1]
if str(AI_ENGINES) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES))

import hot_m1_cache as hcache  # noqa: E402
from native_ftmo_monfri_seal import ROOT, STOP  # noqa: E402
from quant_core.holdout_guard import (  # noqa: E402
    HoldoutLockError,
    enforce_pre_holdout_dates,
    enforce_pre_holdout_ts,
)

from quant_factory.data_store import (  # noqa: E402
    assert_holdout_locked,
    build_or_load_frozen_tapes,
    load_registry,
)
from quant_factory.red_team_auditor import estimate_trade_base_cost_usd_per_lot  # noqa: E402
from quant_factory.report_gen import format_markdown_table, write_verified_receipt  # noqa: E402

ORDER_SEND_CAPABLE: bool = False
HOLDOUT_CUTOFF_DAY: str = "2025-01-01"
HOLDOUT_CUTOFF_TS: int = int(STOP)  # 2025-01-01T00:00:00Z


@dataclass(frozen=True)
class RobustnessThresholds:
    min_mc_beat_rate_unbiased: float = 0.90
    min_mc_beat_rate_same_side: float = 0.90
    mc_draws: int = 1000
    min_side_trades_for_bidirectional: int = 15
    min_side_share_for_bidirectional: float = 0.10
    min_side_pf: float = 1.00
    allow_unidirectional: bool = False
    outlier_trim_pct: float = 0.05
    outlier_trim_basis: str = "winners"  # "winners" (exact 5% of winning trades) or "all" (5% of all trades)
    min_trimmed_pf: float = 1.00
    min_positive_year_ratio: float = 0.57  # >= 4/7 years positive by default
    max_worst_year_loss_r: float = -10.0
    worst_year_subsamples: int = 500
    worst_year_drop_frac: float = 0.10
    allow_weekend_gaps: bool = False
    swap_drag_per_day_r: float = 0.0
    allow_sign_flip_fallback: bool = True


CRISIS_STRESS_WINDOWS: dict[str, tuple[str, str]] = {
    "2020_COVID": ("2020-02-20", "2020-04-30"),
    "2022_INFLATION_BEAR": ("2022-01-01", "2022-10-31"),
    "2024_YEN_UNWIND": ("2024-07-10", "2024-08-20"),
}


def _assert_pre_holdout_days(days: list[str] | tuple[str, ...]) -> None:
    enforce_pre_holdout_dates(days, cutoff_day=HOLDOUT_CUTOFF_DAY, context="robustness_gate.days")


def _assert_pre_holdout_timestamps(ts: np.ndarray) -> None:
    if len(ts) > 0:
        enforce_pre_holdout_ts(ts, stop_ts=HOLDOUT_CUTOFF_TS, context="robustness_gate.timestamps")


def _profit_factor(vals: np.ndarray) -> float:
    if len(vals) == 0:
        return 0.0
    gp = float(np.sum(vals[vals > 0.0]))
    gl = float(-np.sum(vals[vals < 0.0]))
    if gl <= 1e-12:
        return 99.0 if gp > 1e-12 else 0.0
    return gp / gl


def _max_dd_r(vals: np.ndarray) -> float:
    if len(vals) == 0:
        return 0.0
    eq = 0.0
    peak = 0.0
    max_dd = 0.0
    for v in vals:
        eq += float(v)
        if eq > peak:
            peak = eq
        dd = peak - eq
        if dd > max_dd:
            max_dd = dd
    return max_dd


def resample_m1_quotes_to_m5_mid(
    ts_m1: np.ndarray, quotes_m1: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Deterministically resample sealed M1 Bid(/Ask) bars to M5 Mid OHLC arrays (strictly pre-2025)."""
    _assert_pre_holdout_timestamps(ts_m1)
    if quotes_m1.shape[1] >= 8:
        o = 0.5 * (quotes_m1[:, 0] + quotes_m1[:, 4])
        h = 0.5 * (quotes_m1[:, 1] + quotes_m1[:, 5])
        lo = 0.5 * (quotes_m1[:, 2] + quotes_m1[:, 6])
        c = 0.5 * (quotes_m1[:, 3] + quotes_m1[:, 7])
    else:
        o = quotes_m1[:, 0]
        h = quotes_m1[:, 1]
        lo = quotes_m1[:, 2]
        c = quotes_m1[:, 3]

    buckets = (ts_m1 // 300).astype(np.int64)
    if len(buckets) == 0:
        empty = np.empty(0, dtype=np.float64)
        return np.empty(0, dtype=np.int64), empty, empty, empty, empty

    change = np.empty(len(buckets), dtype=np.bool_)
    change[0] = True
    change[1:] = buckets[1:] != buckets[:-1]
    starts = np.flatnonzero(change)
    ends = np.empty_like(starts)
    ends[:-1] = starts[1:] - 1
    ends[-1] = len(buckets) - 1

    ts5 = buckets[starts] * 300
    o5 = np.ascontiguousarray(o[starts], dtype=np.float64)
    c5 = np.ascontiguousarray(c[ends], dtype=np.float64)
    h5 = np.ascontiguousarray(np.maximum.reduceat(h, starts), dtype=np.float64)
    l5 = np.ascontiguousarray(np.minimum.reduceat(lo, starts), dtype=np.float64)
    return ts5, o5, h5, l5, c5


@njit(cache=True)
def _random_entry_mc_ohlc_kernel(
    ts: np.ndarray,
    bar_o: np.ndarray,
    bar_h: np.ndarray,
    bar_l: np.ndarray,
    bar_c: np.ndarray,
    bar_sec: int,
    trade_sides: np.ndarray,
    trade_durs: np.ndarray,
    trade_sl_fracs: np.ndarray,
    trade_frics: np.ndarray,
    obs_sum_r: float,
    mode: int,  # 0 = unbiased 50/50 side, 1 = exact matched side_mix
    draws: int,
    seed: int,
) -> tuple[float, np.ndarray]:
    """Numba-JIT random-entry Monte Carlo over real market OHLC bars.

    Each random trade matches the exact holding duration, SL distance fraction,
    and execution friction `fric_R` of trade `i`, avoiding weekend gaps (`gap <= 2h`).
    """
    n_bars = len(ts)
    n_trades = len(trade_durs)
    totals = np.zeros(draws, dtype=np.float64)
    if n_bars < 50 or n_trades == 0 or draws <= 0:
        return 0.0, totals

    np.random.seed(seed)
    beat = 0
    for d in range(draws):
        acc = 0.0
        for i in range(n_trades):
            dur = int(trade_durs[i])
            if dur < 1:
                dur = 1
            max_start = n_bars - dur - 1
            if max_start <= 1:
                continue

            # Sample a valid entry bar whose holding window does not cross a weekend gap
            start_idx = np.random.randint(0, max_start)
            max_span = dur * bar_sec + 7200
            for _attempt in range(8):
                if (ts[start_idx + dur] - ts[start_idx]) <= max_span:
                    break
                start_idx = np.random.randint(0, max_start)

            side = int(trade_sides[i])
            if mode == 0:
                side = 1 if np.random.random() < 0.5 else -1

            entry = bar_o[start_idx]
            if entry <= 1e-12:
                continue
            sl_frac = trade_sl_fracs[i]
            if sl_frac <= 1e-6:
                sl_frac = 0.005
            sl_dist = entry * sl_frac
            fric = trade_frics[i]
            if fric < 0.0:
                fric = 0.0
            elif fric > 0.5:
                fric = 0.5

            stopped = False
            if side > 0:
                sl_px = entry - sl_dist
                for k in range(start_idx, start_idx + dur + 1):
                    if bar_l[k] <= sl_px:
                        stopped = True
                        break
                if stopped:
                    r_val = -1.0
                else:
                    exit_px = bar_c[start_idx + dur]
                    raw_r = (exit_px - entry) / sl_dist
                    r_val = raw_r * (1.0 - fric) - fric
            else:
                sl_px = entry + sl_dist
                for k in range(start_idx, start_idx + dur + 1):
                    if bar_h[k] >= sl_px:
                        stopped = True
                        break
                if stopped:
                    r_val = -1.0
                else:
                    exit_px = bar_c[start_idx + dur]
                    raw_r = (entry - exit_px) / sl_dist
                    r_val = raw_r * (1.0 - fric) - fric

            acc += r_val

        totals[d] = acc
        if obs_sum_r > acc + 1e-12:
            beat += 1

    beat_rate = beat / float(draws)
    return beat_rate, totals


@njit(cache=True)
def _random_entry_mc_closes_kernel(
    closes: np.ndarray,
    trade_sides: np.ndarray,
    trade_durs: np.ndarray,
    trade_sl_fracs: np.ndarray,
    trade_frics: np.ndarray,
    obs_sum_r: float,
    mode: int,  # 0 = unbiased 50/50, 1 = matched side
    draws: int,
    seed: int,
) -> tuple[float, np.ndarray]:
    """Generic close-only random-entry Monte Carlo (for D1/H1 ETF, Crypto, or Futures series)."""
    n_bars = len(closes)
    n_trades = len(trade_durs)
    totals = np.zeros(draws, dtype=np.float64)
    if n_bars < 20 or n_trades == 0 or draws <= 0:
        return 0.0, totals

    np.random.seed(seed)
    beat = 0
    for d in range(draws):
        acc = 0.0
        for i in range(n_trades):
            dur = int(trade_durs[i])
            if dur < 1:
                dur = 1
            max_start = n_bars - dur - 1
            if max_start <= 1:
                continue
            start_idx = np.random.randint(0, max_start)
            side = int(trade_sides[i])
            if mode == 0:
                side = 1 if np.random.random() < 0.5 else -1

            entry = closes[start_idx]
            if entry <= 1e-12:
                continue
            sl_frac = trade_sl_fracs[i]
            if sl_frac <= 1e-6:
                sl_frac = 0.01
            sl_dist = entry * sl_frac
            fric = trade_frics[i]
            if fric < 0.0:
                fric = 0.0
            elif fric > 0.5:
                fric = 0.5

            stopped = False
            for k in range(start_idx + 1, start_idx + dur + 1):
                move = (closes[k] - entry) * side
                if move <= -sl_dist:
                    stopped = True
                    break
            if stopped:
                r_val = -1.0
            else:
                raw_r = ((closes[start_idx + dur] - entry) * side) / sl_dist
                r_val = raw_r * (1.0 - fric) - fric
            acc += r_val

        totals[d] = acc
        if obs_sum_r > acc + 1e-12:
            beat += 1

    return beat / float(draws), totals


@njit(cache=True)
def _random_entry_mc_ohlc_swing_kernel(
    ts: np.ndarray,
    bar_o: np.ndarray,
    bar_h: np.ndarray,
    bar_l: np.ndarray,
    bar_c: np.ndarray,
    bar_sec: int,
    trade_sides: np.ndarray,
    trade_durs: np.ndarray,
    trade_sl_fracs: np.ndarray,
    trade_frics: np.ndarray,
    obs_sum_r: float,
    mode: int,  # 0 = unbiased 50/50 side, 1 = exact matched side_mix
    draws: int,
    seed: int,
    allow_weekend_gaps: bool,
    swap_drag_per_day_r: float,
) -> tuple[float, np.ndarray]:
    """Swing-safe Numba-JIT Random-Entry MC supporting multi-day holds across weekends & swap drag."""
    n_bars = len(ts)
    n_trades = len(trade_durs)
    totals = np.zeros(draws, dtype=np.float64)
    min_bars = 20 if allow_weekend_gaps else 50
    if n_bars < min_bars or n_trades == 0 or draws <= 0:
        return 0.0, totals

    np.random.seed(seed)
    beat = 0
    for d in range(draws):
        acc = 0.0
        for i in range(n_trades):
            dur = int(trade_durs[i])
            if dur < 1:
                dur = 1
            max_start = n_bars - dur - 1
            if max_start <= 1:
                continue

            start_idx = np.random.randint(0, max_start)
            if not allow_weekend_gaps:
                max_span = dur * bar_sec + 7200
                for _attempt in range(8):
                    if (ts[start_idx + dur] - ts[start_idx]) <= max_span:
                        break
                    start_idx = np.random.randint(0, max_start)

            side = int(trade_sides[i])
            if mode == 0:
                side = 1 if np.random.random() < 0.5 else -1

            entry = bar_o[start_idx]
            if entry <= 1e-12:
                continue
            sl_frac = trade_sl_fracs[i]
            if sl_frac <= 1e-6:
                sl_frac = 0.005
            sl_dist = entry * sl_frac
            fric = trade_frics[i]
            if fric < 0.0:
                fric = 0.0
            elif fric > 0.5:
                fric = 0.5

            stopped = False
            exit_k = start_idx + dur
            if side > 0:
                sl_px = entry - sl_dist
                for k in range(start_idx, start_idx + dur + 1):
                    if bar_l[k] <= sl_px:
                        stopped = True
                        exit_k = k
                        break
                if stopped:
                    r_val = -1.0
                else:
                    exit_px = bar_c[start_idx + dur]
                    raw_r = (exit_px - entry) / sl_dist
                    r_val = raw_r * (1.0 - fric) - fric
            else:
                sl_px = entry + sl_dist
                for k in range(start_idx, start_idx + dur + 1):
                    if bar_h[k] >= sl_px:
                        stopped = True
                        exit_k = k
                        break
                if stopped:
                    r_val = -1.0
                else:
                    exit_px = bar_c[start_idx + dur]
                    raw_r = (entry - exit_px) / sl_dist
                    r_val = raw_r * (1.0 - fric) - fric

            if swap_drag_per_day_r != 0.0:
                held_sec = ts[exit_k] - ts[start_idx]
                held_days = (float(held_sec) / 86400.0) if held_sec > 0 else 0.0
                r_val -= swap_drag_per_day_r * held_days

            acc += r_val

        totals[d] = acc
        if obs_sum_r > acc + 1e-12:
            beat += 1

    return beat / float(draws), totals


@njit(cache=True)
def _random_entry_mc_closes_swing_kernel(
    closes: np.ndarray,
    trade_sides: np.ndarray,
    trade_durs: np.ndarray,
    trade_sl_fracs: np.ndarray,
    trade_frics: np.ndarray,
    obs_sum_r: float,
    mode: int,  # 0 = unbiased 50/50, 1 = matched side
    draws: int,
    seed: int,
    swap_drag_per_day_r: float,
    bar_days: float,
) -> tuple[float, np.ndarray]:
    """Close-only random-entry MC kernel with optional daily swap drag deduction."""
    n_bars = len(closes)
    n_trades = len(trade_durs)
    totals = np.zeros(draws, dtype=np.float64)
    if n_bars < 20 or n_trades == 0 or draws <= 0:
        return 0.0, totals

    np.random.seed(seed)
    beat = 0
    for d in range(draws):
        acc = 0.0
        for i in range(n_trades):
            dur = int(trade_durs[i])
            if dur < 1:
                dur = 1
            max_start = n_bars - dur - 1
            if max_start <= 1:
                continue
            start_idx = np.random.randint(0, max_start)
            side = int(trade_sides[i])
            if mode == 0:
                side = 1 if np.random.random() < 0.5 else -1

            entry = closes[start_idx]
            if entry <= 1e-12:
                continue
            sl_frac = trade_sl_fracs[i]
            if sl_frac <= 1e-6:
                sl_frac = 0.01
            sl_dist = entry * sl_frac
            fric = trade_frics[i]
            if fric < 0.0:
                fric = 0.0
            elif fric > 0.5:
                fric = 0.5

            stopped = False
            exit_k = start_idx + dur
            for k in range(start_idx + 1, start_idx + dur + 1):
                move = (closes[k] - entry) * side
                if move <= -sl_dist:
                    stopped = True
                    exit_k = k
                    break
            if stopped:
                r_val = -1.0
            else:
                raw_r = ((closes[start_idx + dur] - entry) * side) / sl_dist
                r_val = raw_r * (1.0 - fric) - fric

            if swap_drag_per_day_r != 0.0:
                held_days = float(exit_k - start_idx) * bar_days
                r_val -= swap_drag_per_day_r * held_days

            acc += r_val

        totals[d] = acc
        if obs_sum_r > acc + 1e-12:
            beat += 1

    return beat / float(draws), totals


@njit(cache=True)
def _matched_hold_timing_perm_kernel(
    csum: np.ndarray,
    hold_arr: np.ndarray,
    sides_arr: np.ndarray,
    obs_t: float,
    mode: int,  # 0 = unbiased +/-1, 1 = directional/matched sides_arr
    draws: int,
    seed: int,
) -> float:
    """Numba-JIT matched-hold timing permutation p-value over daily return prefix sums."""
    n_days = len(csum) - 1
    n_trades = len(hold_arr)
    if n_days < 5 or n_trades < 2 or draws <= 0:
        return 1.0

    np.random.seed(seed)
    ge = 0
    sqrt_n = math.sqrt(float(n_trades))
    inv_n = 1.0 / float(n_trades)
    inv_nm1 = 1.0 / float(n_trades - 1)

    for _ in range(draws):
        s1 = 0.0
        s2 = 0.0
        for i in range(n_trades):
            h = int(hold_arr[i])
            if h < 1:
                h = 1
            if h >= n_days:
                h = n_days - 1
            max_start = n_days - h
            start_idx = np.random.randint(0, max_start + 1)
            raw_ret = csum[start_idx + h] - csum[start_idx]
            if mode == 0:
                sgn = 1.0 if np.random.random() < 0.5 else -1.0
            else:
                sgn = 1.0 if sides_arr[i] >= 0 else -1.0
            val = raw_ret * sgn
            s1 += val
            s2 += val * val

        mean_v = s1 * inv_n
        var_v = (s2 - s1 * s1 * inv_n) * inv_nm1
        if var_v <= 1e-24:
            if mean_v > 1e-15:
                t_null = 1e6
            elif mean_v < -1e-15:
                t_null = -1e6
            else:
                t_null = 0.0
        else:
            t_null = (mean_v / math.sqrt(var_v)) * sqrt_n

        if t_null >= obs_t - 1e-12:
            ge += 1

    return (ge + 1.0) / float(draws + 1)


@njit(cache=True)
def _sparse_trade_sign_t_perm_kernel(
    trade_r: np.ndarray,
    obs_t: float,
    draws: int,
    seed: int,
) -> float:
    """Numba-JIT sign-flip t-stat permutation fallback when daily series is sparse strategy PnL."""
    n_trades = len(trade_r)
    if n_trades < 2 or draws <= 0:
        return 1.0
    np.random.seed(seed)
    ge = 0
    sqrt_n = math.sqrt(float(n_trades))
    inv_n = 1.0 / float(n_trades)
    inv_nm1 = 1.0 / float(n_trades - 1)
    for _ in range(draws):
        s1 = 0.0
        s2 = 0.0
        for i in range(n_trades):
            val = trade_r[i] if np.random.random() < 0.5 else -trade_r[i]
            s1 += val
            s2 += val * val
        mean_v = s1 * inv_n
        var_v = (s2 - s1 * s1 * inv_n) * inv_nm1
        if var_v <= 1e-24:
            t_null = 0.0 if abs(mean_v) <= 1e-15 else (1e6 if mean_v > 0.0 else -1e6)
        else:
            t_null = (mean_v / math.sqrt(var_v)) * sqrt_n
        if t_null >= obs_t - 1e-12:
            ge += 1
    return (ge + 1.0) / float(draws + 1)


def random_entry_mc_on_bars(
    *,
    ts: np.ndarray,
    bar_o: np.ndarray,
    bar_h: np.ndarray,
    bar_l: np.ndarray,
    bar_c: np.ndarray,
    bar_sec: int,
    trade_r: np.ndarray,
    trade_sides: np.ndarray,
    trade_durs: np.ndarray,
    trade_sl_fracs: np.ndarray,
    trade_frics: np.ndarray,
    draws: int = 1000,
    seed: int = 20261124,
    allow_weekend_gaps: bool = False,
    swap_drag_per_day_r: float = 0.0,
) -> dict:
    """Run real-market Random-Entry Monte Carlo (50/50 unbiased, matched-side, BUY-only, SELL-only).

    When `allow_weekend_gaps=True` (Swing multi-day `2-10d` strategies), bypasses the intraday
    `dur * bar_sec + 7200` weekend filter and optionally deducts `swap_drag_per_day_r` per held day
    directly into the random-entry null.
    """
    _assert_pre_holdout_timestamps(ts)
    if isinstance(swap_drag_per_day_r, bool) or not math.isfinite(float(swap_drag_per_day_r)):
        raise ValueError(f"swap_drag_per_day_r must be a finite float, got {swap_drag_per_day_r!r}")
    swap_drag = float(swap_drag_per_day_r)
    use_swing_kernel = bool(allow_weekend_gaps) or abs(swap_drag) > 1e-15

    ts_c = np.ascontiguousarray(ts, dtype=np.int64)
    o_c = np.ascontiguousarray(bar_o, dtype=np.float64)
    h_c = np.ascontiguousarray(bar_h, dtype=np.float64)
    l_c = np.ascontiguousarray(bar_l, dtype=np.float64)
    c_c = np.ascontiguousarray(bar_c, dtype=np.float64)
    r_c = np.ascontiguousarray(trade_r, dtype=np.float64)
    s_c = np.ascontiguousarray(trade_sides, dtype=np.int64)
    d_c = np.ascontiguousarray(trade_durs, dtype=np.int64)
    sl_c = np.ascontiguousarray(trade_sl_fracs, dtype=np.float64)
    f_c = np.ascontiguousarray(trade_frics, dtype=np.float64)

    def _run_kernel(
        s_sub: np.ndarray,
        d_sub: np.ndarray,
        sl_sub: np.ndarray,
        f_sub: np.ndarray,
        obs_val: float,
        mode_val: int,
        seed_val: int,
    ) -> tuple[float, np.ndarray]:
        if use_swing_kernel:
            return _random_entry_mc_ohlc_swing_kernel(
                ts_c,
                o_c,
                h_c,
                l_c,
                c_c,
                int(bar_sec),
                s_sub,
                d_sub,
                sl_sub,
                f_sub,
                obs_val,
                mode_val,
                int(draws),
                int(seed_val),
                bool(allow_weekend_gaps),
                swap_drag,
            )
        return _random_entry_mc_ohlc_kernel(
            ts_c,
            o_c,
            h_c,
            l_c,
            c_c,
            int(bar_sec),
            s_sub,
            d_sub,
            sl_sub,
            f_sub,
            obs_val,
            mode_val,
            int(draws),
            int(seed_val),
        )

    obs_sum = float(np.sum(r_c))
    beat_unb, tot_unb = _run_kernel(s_c, d_c, sl_c, f_c, obs_sum, 0, int(seed))
    beat_same, tot_same = _run_kernel(s_c, d_c, sl_c, f_c, obs_sum, 1, int(seed + 17))

    out = {
        "mc_mode": "real_market_bars_swing" if bool(allow_weekend_gaps) else "real_market_bars",
        "allow_weekend_gaps": bool(allow_weekend_gaps),
        "swap_drag_per_day_r": round(swap_drag, 6),
        "draws": int(draws),
        "obs_sum_r": round(obs_sum, 2),
        "beat_rate_unbiased": round(float(beat_unb), 4),
        "null_unbiased_median_r": round(float(np.median(tot_unb)), 2) if len(tot_unb) else 0.0,
        "null_unbiased_p90_r": round(float(np.quantile(tot_unb, 0.90)), 2) if len(tot_unb) else 0.0,
        "beat_rate_same_side": round(float(beat_same), 4),
        "null_same_side_median_r": round(float(np.median(tot_same)), 2) if len(tot_same) else 0.0,
        "null_same_side_p90_r": round(float(np.quantile(tot_same, 0.90)), 2) if len(tot_same) else 0.0,
    }

    # Per-side random-entry MC (separates timing skill from secular asset drift on BUY and SELL!)
    buy_mask = s_c > 0
    sell_mask = s_c < 0
    if int(np.sum(buy_mask)) >= 10:
        b_obs = float(np.sum(r_c[buy_mask]))
        b_beat, b_tot = _run_kernel(
            s_c[buy_mask],
            d_c[buy_mask],
            sl_c[buy_mask],
            f_c[buy_mask],
            b_obs,
            1,
            int(seed + 31),
        )
        out["buy_beat_rate_vs_random_buy"] = round(float(b_beat), 4)
        out["buy_null_median_r"] = round(float(np.median(b_tot)), 2)
    else:
        out["buy_beat_rate_vs_random_buy"] = None
        out["buy_null_median_r"] = None

    if int(np.sum(sell_mask)) >= 10:
        s_obs = float(np.sum(r_c[sell_mask]))
        s_beat, s_tot = _run_kernel(
            s_c[sell_mask],
            d_c[sell_mask],
            sl_c[sell_mask],
            f_c[sell_mask],
            s_obs,
            1,
            int(seed + 47),
        )
        out["sell_beat_rate_vs_random_sell"] = round(float(s_beat), 4)
        out["sell_null_median_r"] = round(float(np.median(s_tot)), 2)
    else:
        out["sell_beat_rate_vs_random_sell"] = None
        out["sell_null_median_r"] = None

    return out


def random_entry_mc_on_closes(
    *,
    closes: np.ndarray,
    trade_r: np.ndarray,
    trade_sides: np.ndarray,
    trade_durs: np.ndarray,
    trade_sl_fracs: np.ndarray,
    trade_frics: np.ndarray,
    draws: int = 1000,
    seed: int = 20261124,
    allow_weekend_gaps: bool = True,
    swap_drag_per_day_r: float = 0.0,
    bar_days: float = 1.0,
) -> dict:
    """Generic Random-Entry MC on close-price arrays (ETF, Crypto, Futures, or D1 Swing candidates)."""
    if isinstance(swap_drag_per_day_r, bool) or not math.isfinite(float(swap_drag_per_day_r)):
        raise ValueError(f"swap_drag_per_day_r must be a finite float, got {swap_drag_per_day_r!r}")
    if isinstance(bar_days, bool) or not math.isfinite(float(bar_days)) or float(bar_days) <= 0.0:
        raise ValueError(f"bar_days must be finite > 0, got {bar_days!r}")
    swap_drag = float(swap_drag_per_day_r)

    c_c = np.ascontiguousarray(closes, dtype=np.float64)
    r_c = np.ascontiguousarray(trade_r, dtype=np.float64)
    s_c = np.ascontiguousarray(trade_sides, dtype=np.int64)
    d_c = np.ascontiguousarray(trade_durs, dtype=np.int64)
    sl_c = np.ascontiguousarray(trade_sl_fracs, dtype=np.float64)
    f_c = np.ascontiguousarray(trade_frics, dtype=np.float64)

    obs_sum = float(np.sum(r_c))
    if abs(swap_drag) <= 1e-15:
        beat_unb, tot_unb = _random_entry_mc_closes_kernel(c_c, s_c, d_c, sl_c, f_c, obs_sum, 0, int(draws), int(seed))
        beat_same, tot_same = _random_entry_mc_closes_kernel(
            c_c, s_c, d_c, sl_c, f_c, obs_sum, 1, int(draws), int(seed + 17)
        )
    else:
        beat_unb, tot_unb = _random_entry_mc_closes_swing_kernel(
            c_c, s_c, d_c, sl_c, f_c, obs_sum, 0, int(draws), int(seed), swap_drag, float(bar_days)
        )
        beat_same, tot_same = _random_entry_mc_closes_swing_kernel(
            c_c, s_c, d_c, sl_c, f_c, obs_sum, 1, int(draws), int(seed + 17), swap_drag, float(bar_days)
        )
    return {
        "mc_mode": "close_series_swing" if abs(swap_drag) > 1e-15 else "close_series",
        "allow_weekend_gaps": bool(allow_weekend_gaps),
        "swap_drag_per_day_r": round(swap_drag, 6),
        "draws": int(draws),
        "obs_sum_r": round(obs_sum, 2),
        "beat_rate_unbiased": round(float(beat_unb), 4),
        "null_unbiased_median_r": round(float(np.median(tot_unb)), 2) if len(tot_unb) else 0.0,
        "null_unbiased_p90_r": round(float(np.quantile(tot_unb, 0.90)), 2) if len(tot_unb) else 0.0,
        "beat_rate_same_side": round(float(beat_same), 4),
        "null_same_side_median_r": round(float(np.median(tot_same)), 2) if len(tot_same) else 0.0,
        "null_same_side_p90_r": round(float(np.quantile(tot_same, 0.90)), 2) if len(tot_same) else 0.0,
        "buy_beat_rate_vs_random_buy": None,
        "sell_beat_rate_vs_random_sell": None,
    }


def _normalize_date_series_pre_holdout(
    series: Mapping[str, float] | Mapping[str, object],
    *,
    context: str,
) -> tuple[list[str], np.ndarray]:
    """Normalize `{date: val}` or `{'dates': [...], 'pnl': [...]}` while enforcing `< 2025-01-01`."""
    if "dates" in series and "pnl" in series and isinstance(series["dates"], (list, tuple)):
        dates_raw = [str(d) for d in series["dates"]]
        vals_raw = np.asarray(series["pnl"], dtype=np.float64)
        if len(dates_raw) != len(vals_raw):
            raise ValueError(f"{context}: dates length ({len(dates_raw)}) != pnl length ({len(vals_raw)})")
        _assert_pre_holdout_days(dates_raw)
        order = sorted(range(len(dates_raw)), key=lambda i: dates_raw[i])
        dates_ord = [dates_raw[i] for i in order]
        vals_ord = vals_raw[order]
    else:
        dates_ord = sorted(str(k) for k in series)
        _assert_pre_holdout_days(dates_ord)
        vals_ord = np.array([float(series[k]) for k in dates_ord], dtype=np.float64)

    if vals_ord.size > 0 and not bool(np.all(np.isfinite(vals_ord))):
        raise ValueError(f"{context}: daily series contains non-finite values")
    return dates_ord, vals_ord


def matched_hold_timing_permutation_p(
    daily_returns: np.ndarray | Sequence[float] | Mapping[str, float],
    trade_days: Sequence[str],
    trade_r_values: np.ndarray | Sequence[float],
    draws: int = 5000,
    seed: int = 20261127,
    *,
    hold_bars: int | Sequence[int] | None = None,
    trade_sides: Sequence[int] | np.ndarray | None = None,
    alpha: float = 0.05,
) -> dict:
    """Matched-hold timing permutation test (`p < 0.05` check, strictly Dev < 2025-01-01).

    Tests whether the observed risk-adjusted trade timing statistic (`t_obs` on `trade_r_values`)
    beats `draws` matched-hold random timing entries across `daily_returns` under BOTH unbiased
    `+/-1` direction and drift-aligned/matched-side direction.
    """
    if isinstance(draws, bool) or int(draws) < 1:
        raise ValueError(f"draws must be an integer >= 1, got {draws!r}")
    if isinstance(seed, bool) or not isinstance(seed, (int, np.integer)):
        raise ValueError(f"seed must be an integer, got {seed!r}")
    if isinstance(alpha, bool) or not (0.0 < float(alpha) < 1.0):
        raise ValueError(f"alpha must be in (0, 1), got {alpha!r}")

    tdays = [str(d) for d in trade_days]
    _assert_pre_holdout_days(tdays)

    r_arr = np.asarray(trade_r_values, dtype=np.float64)
    if r_arr.ndim != 1 or (r_arr.size > 0 and not bool(np.all(np.isfinite(r_arr)))):
        raise ValueError("trade_r_values must be a 1D finite numeric array")
    if len(tdays) != len(r_arr):
        raise ValueError(f"trade_days length ({len(tdays)}) != trade_r_values length ({len(r_arr)})")

    n_trades = int(r_arr.size)
    if n_trades < 2:
        return {
            "passed": False,
            "p_value": 1.0,
            "alpha": float(alpha),
            "p_unbiased": 1.0,
            "p_directional": 1.0,
            "obs_t_stat": 0.0,
            "obs_mean_r": float(np.mean(r_arr)) if n_trades else 0.0,
            "n_trades": n_trades,
            "draws": int(draws),
            "median_hold_bars": 1,
            "null_mode": "insufficient_trades",
            "holdout_rows_analysed": 0,
            "order_send_capable": ORDER_SEND_CAPABLE,
        }

    mkt_dates: list[str] | None = None
    if isinstance(daily_returns, Mapping):
        mkt_dates, mkt_arr = _normalize_date_series_pre_holdout(
            daily_returns, context="robustness_gate.matched_hold_timing"
        )
    else:
        mkt_arr = np.asarray(daily_returns, dtype=np.float64)
        if mkt_arr.ndim != 1 or (mkt_arr.size > 0 and not bool(np.all(np.isfinite(mkt_arr)))):
            raise ValueError("daily_returns must be a 1D finite numeric sequence or date mapping")

    obs_mean = float(np.mean(r_arr))
    obs_std = float(np.std(r_arr, ddof=1))
    if obs_std <= 1e-12:
        obs_t = 1e6 if obs_mean > 1e-15 else (-1e6 if obs_mean < -1e-15 else 0.0)
    else:
        obs_t = (obs_mean / obs_std) * math.sqrt(float(n_trades))

    if hold_bars is None:
        h_arr = np.ones(n_trades, dtype=np.int64)
    elif isinstance(hold_bars, (int, np.integer)) and not isinstance(hold_bars, bool):
        h_arr = np.full(n_trades, max(1, int(hold_bars)), dtype=np.int64)
    else:
        h_arr = np.maximum(1, np.asarray(hold_bars, dtype=np.int64))
        if h_arr.ndim != 1 or h_arr.size != n_trades:
            raise ValueError(f"hold_bars length ({h_arr.size}) must match trade_r_values ({n_trades})")

    max_h = int(np.max(h_arr))
    non_zero_frac = float(np.mean(np.abs(mkt_arr) > 1e-12)) if mkt_arr.size > 0 else 0.0

    if mkt_arr.size >= max(20, max_h + 2) and non_zero_frac >= 0.40:
        null_mode = "matched_hold_market_timing"
        csum = np.empty(mkt_arr.size + 1, dtype=np.float64)
        csum[0] = 0.0
        np.cumsum(mkt_arr, out=csum[1:])

        if trade_sides is not None:
            s_raw = np.asarray(trade_sides, dtype=np.int64)
            if s_raw.ndim != 1 or s_raw.size != n_trades:
                raise ValueError(f"trade_sides length ({s_raw.size}) must match trade_r_values ({n_trades})")
            s_dir = np.where(s_raw >= 0, 1, -1).astype(np.int64)
        else:
            # Infer dominant secular-drift alignment so passive trend riding cannot masquerade as timing skill
            inferred_sign = 1 if float(np.mean(mkt_arr)) >= 0.0 else -1
            if mkt_dates is not None:
                m_map = {d: float(v) for d, v in zip(mkt_dates, mkt_arr, strict=True)}
                paired_r = []
                paired_m = []
                for dk, rv in zip(tdays, r_arr, strict=True):
                    if dk in m_map:
                        paired_r.append(float(rv))
                        paired_m.append(m_map[dk])
                if len(paired_r) >= 5 and float(np.std(paired_r)) > 1e-12 and float(np.std(paired_m)) > 1e-12:
                    c_align = float(np.corrcoef(paired_r, paired_m)[0, 1])
                    if math.isfinite(c_align) and abs(c_align) > 0.15:
                        inferred_sign = 1 if c_align > 0.0 else -1
            s_dir = np.full(n_trades, inferred_sign, dtype=np.int64)

        p_unb = float(_matched_hold_timing_perm_kernel(csum, h_arr, s_dir, obs_t, 0, int(draws), int(seed)))
        p_dir = float(_matched_hold_timing_perm_kernel(csum, h_arr, s_dir, obs_t, 1, int(draws), int(seed + 17)))
        p_val = max(p_unb, p_dir)
    else:
        null_mode = "active_trade_sign_permutation"
        p_unb = float(
            _sparse_trade_sign_t_perm_kernel(
                np.ascontiguousarray(r_arr, dtype=np.float64), obs_t, int(draws), int(seed)
            )
        )
        p_dir = p_unb
        p_val = p_unb

    if obs_mean <= 0.0:
        p_val = max(p_val, 0.5)

    return {
        "passed": bool(p_val < float(alpha)),
        "p_value": round(float(p_val), 6),
        "alpha": float(alpha),
        "p_unbiased": round(float(p_unb), 6),
        "p_directional": round(float(p_dir), 6),
        "obs_t_stat": round(float(obs_t), 4),
        "obs_mean_r": round(float(obs_mean), 4),
        "n_trades": n_trades,
        "draws": int(draws),
        "median_hold_bars": int(np.median(h_arr)),
        "null_mode": null_mode,
        "holdout_rows_analysed": 0,
        "order_send_capable": ORDER_SEND_CAPABLE,
    }


def evaluate_crisis_stress_windows(
    daily_pnl_all_dev: Mapping[str, float] | Mapping[str, object],
    *,
    risk_frac: float = 0.005,
    max_window_dd_r: float = 12.0,
    max_single_day_loss_r: float = 6.0,
    min_window_sum_r: float = -12.0,
) -> dict:
    """Evaluate 3 historical Dev crisis stress windows strictly on `2018-2024` AFTER blind Cl.B selection.

    Windows:
      - `2020_COVID`: `2020-02-20..2020-04-30`
      - `2022_INFLATION_BEAR`: `2022-01-01..2022-10-31`
      - `2024_YEN_UNWIND`: `2024-07-10..2024-08-20`
    """
    if isinstance(risk_frac, bool) or not math.isfinite(float(risk_frac)) or float(risk_frac) <= 0.0:
        raise ValueError(f"risk_frac must be finite > 0, got {risk_frac!r}")

    dates_ord, vals_ord = _normalize_date_series_pre_holdout(
        daily_pnl_all_dev, context="robustness_gate.crisis_stress_windows"
    )
    rf = float(risk_frac)
    windows_out: dict[str, dict] = {}
    failed_windows: list[str] = []
    worst_w_name: str | None = None
    worst_dd_r = -1.0
    worst_sum_r = float("inf")

    for w_name, (start_d, end_d) in CRISIS_STRESS_WINDOWS.items():
        w_vals = [float(v) for d, v in zip(dates_ord, vals_ord, strict=True) if start_d <= d <= end_d]
        arr = np.asarray(w_vals, dtype=np.float64)
        n_days = int(arr.size)
        if n_days == 0:
            windows_out[w_name] = {
                "start_date": start_d,
                "end_date": end_d,
                "n_days": 0,
                "active_days": 0,
                "sum_r": 0.0,
                "max_dd_r": 0.0,
                "worst_1d_r": 0.0,
                "max_dd_pct_at_risk": 0.0,
                "worst_1d_pct_at_risk": 0.0,
                "survived": False,
                "reason": "MISSING_WINDOW_DATA",
            }
            failed_windows.append(w_name)
            continue

        active_days = int(np.sum(np.abs(arr) > 1e-12))
        sum_r = float(np.sum(arr))
        max_dd_r = float(_max_dd_r(arr))
        worst_1d_r = float(np.min(arr))
        max_dd_pct = max_dd_r * rf * 100.0
        worst_1d_pct = abs(min(0.0, worst_1d_r)) * rf * 100.0

        reasons: list[str] = []
        if max_dd_r > float(max_window_dd_r) + 1e-12:
            reasons.append(f"DD_BREACH({max_dd_r:.2f}R>{max_window_dd_r:.2f}R)")
        if worst_1d_r < -float(max_single_day_loss_r) - 1e-12:
            reasons.append(f"DAILY_LOSS_BREACH({worst_1d_r:.2f}R<-{max_single_day_loss_r:.2f}R)")
        if sum_r < float(min_window_sum_r) - 1e-12:
            reasons.append(f"NET_LOSS_BREACH({sum_r:.2f}R<{min_window_sum_r:.2f}R)")

        survived = len(reasons) == 0
        if not survived:
            failed_windows.append(w_name)
        if max_dd_r > worst_dd_r:
            worst_dd_r = max_dd_r
            worst_w_name = w_name
        if sum_r < worst_sum_r:
            worst_sum_r = sum_r

        windows_out[w_name] = {
            "start_date": start_d,
            "end_date": end_d,
            "n_days": n_days,
            "active_days": active_days,
            "sum_r": round(sum_r, 4),
            "max_dd_r": round(max_dd_r, 4),
            "worst_1d_r": round(worst_1d_r, 4),
            "max_dd_pct_at_risk": round(max_dd_pct, 3),
            "worst_1d_pct_at_risk": round(worst_1d_pct, 3),
            "survived": survived,
            "reason": "SURVIVED" if survived else "; ".join(reasons),
        }

    survived_count = sum(1 for w in windows_out.values() if w["survived"])
    return {
        "schema": "naqex-crisis-stress-windows-v1",
        "order_send_capable": ORDER_SEND_CAPABLE,
        "holdout_rows_analysed": 0,
        "passed": len(failed_windows) == 0,
        "survived_count": survived_count,
        "total_windows": len(CRISIS_STRESS_WINDOWS),
        "failed_windows": failed_windows,
        "worst_crisis_window": worst_w_name,
        "worst_crisis_dd_r": round(max(0.0, worst_dd_r), 4),
        "worst_crisis_sum_r": round(worst_sum_r if math.isfinite(worst_sum_r) else 0.0, 4),
        "risk_frac": rf,
        "thresholds": {
            "max_window_dd_r": float(max_window_dd_r),
            "max_single_day_loss_r": float(max_single_day_loss_r),
            "min_window_sum_r": float(min_window_sum_r),
        },
        "windows": windows_out,
    }


def buy_sell_symmetry_audit(
    trade_r: np.ndarray,
    trade_sides: np.ndarray,
    thresholds: RobustnessThresholds = RobustnessThresholds(),
) -> dict:
    """Audit BUY and SELL performance independently to prevent trend-drift disguise."""
    r = np.asarray(trade_r, dtype=np.float64)
    s = np.asarray(trade_sides, dtype=np.int64)
    n_tot = len(r)
    buy_r = r[s > 0]
    sell_r = r[s < 0]

    def _side_stats(arr: np.ndarray) -> dict:
        n = len(arr)
        if n == 0:
            return {"n": 0, "share_pct": 0.0, "sum_r": 0.0, "mean_r": 0.0, "win_rate_pct": 0.0, "pf": 0.0}
        return {
            "n": int(n),
            "share_pct": round(100.0 * n / max(1, n_tot), 1),
            "sum_r": round(float(np.sum(arr)), 2),
            "mean_r": round(float(np.mean(arr)), 4),
            "win_rate_pct": round(100.0 * float(np.mean(arr > 0.0)), 1),
            "pf": round(_profit_factor(arr), 2),
        }

    bs = _side_stats(buy_r)
    ss = _side_stats(sell_r)
    min_n = thresholds.min_side_trades_for_bidirectional
    min_sh = thresholds.min_side_share_for_bidirectional * 100.0

    is_bidir = (bs["n"] >= min_n and ss["n"] >= min_n and bs["share_pct"] >= min_sh and ss["share_pct"] >= min_sh)
    warnings: list[str] = []
    if is_bidir:
        directionality = "BIDIRECTIONAL"
        buy_ok = bs["sum_r"] > 0.0 and bs["pf"] >= thresholds.min_side_pf
        sell_ok = ss["sum_r"] > 0.0 and ss["pf"] >= thresholds.min_side_pf
        passed = bool(buy_ok and sell_ok)
        if not buy_ok:
            warnings.append(f"BUY_EDGE_FAIL(sum_r={bs['sum_r']}, pf={bs['pf']})")
        if not sell_ok:
            warnings.append(f"SELL_EDGE_FAIL(sum_r={ss['sum_r']}, pf={ss['pf']})")
        tot_pos = max(0.0, bs["sum_r"]) + max(0.0, ss["sum_r"])
        if passed and tot_pos > 1e-9:
            dom = max(bs["sum_r"], ss["sum_r"]) / tot_pos
            if dom > 0.85:
                warnings.append(f"ONE_SIDE_DOMINANCE({round(dom * 100.0, 1)}%)")
    else:
        directionality = "UNIDIRECTIONAL_LONG" if bs["n"] >= ss["n"] else "UNIDIRECTIONAL_SHORT"
        active = bs if bs["n"] >= ss["n"] else ss
        active_ok = active["sum_r"] > 0.0 and active["pf"] >= thresholds.min_side_pf
        passed = bool(thresholds.allow_unidirectional and active_ok)
        if not thresholds.allow_unidirectional:
            warnings.append(f"UNIDIRECTIONAL_NOT_EXPLICITLY_ALLOWED({directionality})")
        elif not active_ok:
            warnings.append(f"ACTIVE_SIDE_FAIL(sum_r={active['sum_r']}, pf={active['pf']})")

    return {
        "passed": passed,
        "directionality": directionality,
        "buy": bs,
        "sell": ss,
        "warnings": warnings,
    }


def top_outlier_trim_audit(
    trade_r: np.ndarray,
    thresholds: RobustnessThresholds = RobustnessThresholds(),
) -> dict:
    """Drop top `outlier_trim_pct` largest winning trades and verify strategy stays profitable."""
    r = np.asarray(trade_r, dtype=np.float64)
    n = len(r)
    if n < 5:
        return {"passed": False, "n_trades": int(n), "reason": "INSUFFICIENT_TRADES"}

    raw_sum = float(np.sum(r))
    raw_pf = _profit_factor(r)

    # Sort descending so largest winners are at front; only remove strictly positive trades
    order = np.argsort(r)[::-1]
    pos_indices = [int(i) for i in order if r[i] > 0.0]

    # Mode 1 (Conservative hard gate): drop ceil(trim_pct * N_total) largest winners
    k_all = min(len(pos_indices), max(1, math.ceil(thresholds.outlier_trim_pct * n)))
    drop_all = set(pos_indices[:k_all])
    rem_all = np.array([r[i] for i in range(n) if i not in drop_all], dtype=np.float64)
    sum_rem_all = float(np.sum(rem_all))
    pf_rem_all = _profit_factor(rem_all)
    ret_ratio_all = (sum_rem_all / raw_sum) if raw_sum > 1e-9 else 0.0

    # Mode 2 (Default — exact 5% of winning trades, unbiased across breakout vs mean-reversion winrates)
    k_win = min(len(pos_indices), max(1, math.ceil(thresholds.outlier_trim_pct * max(1, len(pos_indices)))))
    drop_win = set(pos_indices[:k_win])
    rem_win = np.array([r[i] for i in range(n) if i not in drop_win], dtype=np.float64)
    sum_rem_win = float(np.sum(rem_win))
    pf_rem_win = _profit_factor(rem_win)
    ret_ratio_win = (sum_rem_win / raw_sum) if raw_sum > 1e-9 else 0.0

    if thresholds.outlier_trim_basis == "all":
        primary_sum, primary_pf = sum_rem_all, pf_rem_all
    elif thresholds.outlier_trim_basis == "winners":
        primary_sum, primary_pf = sum_rem_win, pf_rem_win
    else:
        raise ValueError(f"Unsupported outlier_trim_basis: {thresholds.outlier_trim_basis}")

    passed = bool(primary_sum > 0.0 and primary_pf >= thresholds.min_trimmed_pf)
    return {
        "passed": passed,
        "trim_pct": thresholds.outlier_trim_pct,
        "trim_basis": thresholds.outlier_trim_basis,
        "n_trades": int(n),
        "raw_sum_r": round(raw_sum, 2),
        "raw_pf": round(raw_pf, 2),
        "dropped_k_of_all": int(k_all),
        "trimmed_all_sum_r": round(sum_rem_all, 2),
        "trimmed_all_pf": round(pf_rem_all, 2),
        "retention_ratio_all": round(ret_ratio_all, 3),
        "dropped_k_of_winners": int(k_win),
        "trimmed_winners_sum_r": round(sum_rem_win, 2),
        "trimmed_winners_pf": round(pf_rem_win, 2),
        "retention_ratio_winners": round(ret_ratio_win, 3),
    }


def worst_year_stability_audit(
    trade_r: np.ndarray,
    trade_days: list[str] | tuple[str, ...],
    thresholds: RobustnessThresholds = RobustnessThresholds(),
    *,
    seed: int = 20261124,
) -> dict:
    """Audit calendar-year stability + randomized-variant worst-year ranking score."""
    _assert_pre_holdout_days(trade_days)
    r = np.asarray(trade_r, dtype=np.float64)
    if len(r) != len(trade_days) or len(r) == 0:
        return {"passed": False, "reason": "EMPTY_OR_MISMATCHED_TRADES"}

    # Ensure chronological order
    order = sorted(range(len(trade_days)), key=lambda i: str(trade_days[i]))
    days_ord = [str(trade_days[i]) for i in order]
    r_ord = r[order]

    by_year: dict[str, list[float]] = defaultdict(list)
    for dk, rv in zip(days_ord, r_ord, strict=True):
        by_year[dk[:4]].append(float(rv))

    years_sorted = sorted(by_year.keys())
    year_stats: dict[str, dict] = {}
    year_sums: list[tuple[str, float]] = []
    for y in years_sorted:
        arr = np.asarray(by_year[y], dtype=np.float64)
        s_r = float(np.sum(arr))
        year_sums.append((y, s_r))
        year_stats[y] = {
            "n": int(len(arr)),
            "sum_r": round(s_r, 2),
            "win_rate_pct": round(100.0 * float(np.mean(arr > 0.0)), 1),
            "pf": round(_profit_factor(arr), 2),
            "max_dd_r": round(_max_dd_r(arr), 2),
        }

    worst_y, worst_r = min(year_sums, key=lambda kv: kv[1])
    best_y, best_r = max(year_sums, key=lambda kv: kv[1])
    pos_years = sum(1 for _, v in year_sums if v > 0.0)
    pos_ratio = pos_years / max(1, len(year_sums))

    # Rolling 365-day worst window (eliminates Jan 1 - Dec 31 calendar boundary luck!)
    day_ordinals = np.array([datetime.strptime(d[:10], "%Y-%m-%d").toordinal() for d in days_ord], dtype=np.int64)
    rolling_worst_12m = worst_r
    rolling_worst_start = days_ord[0]
    if len(day_ordinals) >= 2 and (day_ordinals[-1] - day_ordinals[0]) >= 300:
        j = 0
        running = 0.0
        rolling_worst_12m = float("inf")
        for i in range(len(day_ordinals)):
            running += float(r_ord[i])
            while j < i and (day_ordinals[i] - day_ordinals[j]) > 365:
                running -= float(r_ord[j])
                j += 1
            if (day_ordinals[i] - day_ordinals[0]) >= 330:
                if running < rolling_worst_12m:
                    rolling_worst_12m = running
                    rolling_worst_start = days_ord[j]
        if not math.isfinite(rolling_worst_12m):
            rolling_worst_12m = worst_r

    # Multi-variant randomized worst-year score (random 10% trade drop + shifted 365d window offset)
    rng = np.random.default_rng(int(seed))
    n_sub = max(50, int(thresholds.worst_year_subsamples))
    keep_prob = 1.0 - float(thresholds.worst_year_drop_frac)
    min_ord = int(day_ordinals[0])
    max_ord = int(day_ordinals[-1])
    span_days = max(1, max_ord - min_ord)
    mc_worst_scores = np.zeros(n_sub, dtype=np.float64)
    for k in range(n_sub):
        mask = rng.random(len(r_ord)) < keep_prob
        if not np.any(mask):
            mc_worst_scores[k] = 0.0
            continue
        offset = int(rng.integers(0, min(365, span_days)))
        shifted_bins = (day_ordinals[mask] - min_ord + offset) // 365
        vals = r_ord[mask]
        # Exclude tiny trailing/leading partial edge bins (< 5 trades) when >= 2 full bins exist
        uniq = np.unique(shifted_bins)
        bin_sums = []
        for b in uniq:
            bm = shifted_bins == b
            if int(np.sum(bm)) >= 5 or len(uniq) == 1:
                bin_sums.append(float(np.sum(vals[bm])))
        mc_worst_scores[k] = min(bin_sums) if bin_sums else float(np.sum(vals))

    mc_wy_med = float(np.median(mc_worst_scores))
    mc_wy_p10 = float(np.quantile(mc_worst_scores, 0.10))

    passed = bool(
        (pos_ratio >= thresholds.min_positive_year_ratio - 1e-9)
        and (worst_r >= thresholds.max_worst_year_loss_r - 1e-9)
    )
    return {
        "passed": passed,
        "n_years": len(years_sorted),
        "positive_years": int(pos_years),
        "positive_year_ratio": round(pos_ratio, 3),
        "worst_year": worst_y,
        "worst_year_r": round(worst_r, 2),
        "best_year": best_y,
        "best_year_r": round(best_r, 2),
        "rolling_worst_12m_r": round(float(rolling_worst_12m), 2),
        "rolling_worst_12m_start": rolling_worst_start,
        "mc_worst_year_median_r": round(mc_wy_med, 2),
        "mc_worst_year_p10_r": round(mc_wy_p10, 2),
        "ranking_score_worst_year_p10_r": round(mc_wy_p10, 2),
        "years": year_stats,
    }


def evaluate_robustness_gate(
    *,
    strategy_id: str,
    trade_r: np.ndarray | list[float],
    trade_sides: np.ndarray | list[int],
    trade_days: list[str] | tuple[str, ...],
    mc_result: dict | None = None,
    closes: np.ndarray | None = None,
    trade_durs: np.ndarray | list[int] | None = None,
    trade_sl_fracs: np.ndarray | list[float] | None = None,
    trade_frics: np.ndarray | list[float] | None = None,
    thresholds: RobustnessThresholds = RobustnessThresholds(),
    seed: int = 20261124,
) -> dict:
    """Unified 4-pillar pre-promotion robustness gate (strictly Dev < 2025-01-01)."""
    _assert_pre_holdout_days(trade_days)
    r = np.asarray(trade_r, dtype=np.float64)
    s = np.asarray(trade_sides, dtype=np.int64)

    if mc_result is None:
        if closes is not None:
            d_arr = np.asarray(
                trade_durs if trade_durs is not None else np.ones(len(r), dtype=np.int64), dtype=np.int64
            )
            sl_arr = np.asarray(
                trade_sl_fracs if trade_sl_fracs is not None else np.full(len(r), 0.01), dtype=np.float64
            )
            f_arr = np.asarray(
                trade_frics if trade_frics is not None else np.full(len(r), 0.03), dtype=np.float64
            )
            mc = random_entry_mc_on_closes(
                closes=closes,
                trade_r=r,
                trade_sides=s,
                trade_durs=d_arr,
                trade_sl_fracs=sl_arr,
                trade_frics=f_arr,
                draws=thresholds.mc_draws,
                seed=seed,
                allow_weekend_gaps=thresholds.allow_weekend_gaps,
                swap_drag_per_day_r=thresholds.swap_drag_per_day_r,
            )
        else:
            # Explicit sign-flip fallback when caller only supplies trade R outcomes without price series
            rng = np.random.default_rng(int(seed))
            obs_sum = float(np.sum(r))
            signs = rng.choice([-1.0, 1.0], size=(int(thresholds.mc_draws), len(r)))
            totals = signs @ r
            beat = float(np.mean(obs_sum > totals + 1e-12)) if len(r) else 0.0
            mc = {
                "mc_mode": "sign_flip_fallback",
                "draws": int(thresholds.mc_draws),
                "obs_sum_r": round(obs_sum, 2),
                "beat_rate_unbiased": round(beat, 4),
                "null_unbiased_median_r": round(float(np.median(totals)), 2) if len(totals) else 0.0,
                "null_unbiased_p90_r": round(float(np.quantile(totals, 0.90)), 2) if len(totals) else 0.0,
                "beat_rate_same_side": round(beat, 4),
                "null_same_side_median_r": round(float(np.median(totals)), 2) if len(totals) else 0.0,
                "null_same_side_p90_r": round(float(np.quantile(totals, 0.90)), 2) if len(totals) else 0.0,
                "buy_beat_rate_vs_random_buy": None,
                "sell_beat_rate_vs_random_sell": None,
            }
    else:
        mc = dict(mc_result)

    is_sign_flip_fallback = str(mc.get("mc_mode") or "") == "sign_flip_fallback"
    fallback_blocked = is_sign_flip_fallback and (not bool(thresholds.allow_sign_flip_fallback))
    mc_pass = bool(
        (not fallback_blocked)
        and float(mc["beat_rate_unbiased"]) >= thresholds.min_mc_beat_rate_unbiased
        and float(mc["beat_rate_same_side"]) >= thresholds.min_mc_beat_rate_same_side
    )
    if fallback_blocked:
        mc["fallback_blocked"] = True
    mc["passed"] = mc_pass

    sym = buy_sell_symmetry_audit(r, s, thresholds)
    trim = top_outlier_trim_audit(r, thresholds)
    wy = worst_year_stability_audit(r, trade_days, thresholds, seed=seed)

    failed_pillars = []
    if not mc_pass:
        failed_pillars.append("R1_random_entry_mc")
    if not sym["passed"]:
        failed_pillars.append("R2_buy_sell_symmetry")
    if not trim["passed"]:
        failed_pillars.append("R3_top5_outlier_trim")
    if not wy["passed"]:
        failed_pillars.append("R4_worst_year_stability")

    if not failed_pillars:
        verdict = "PASS_ROBUST"
    elif "R1_random_entry_mc" in failed_pillars or "R3_top5_outlier_trim" in failed_pillars or len(failed_pillars) >= 2:
        verdict = "FAIL_FRAGILE"
    else:
        # Passed Random-Entry MC >= 90% and Top-5% trim, but flagged 1 structural asymmetry or worst-year warning
        verdict = "WARN_ASYMMETRY_OR_YEAR"

    return {
        "schema": "naqex-robustness-gate-v1",
        "strategy_id": strategy_id,
        "order_send_capable": ORDER_SEND_CAPABLE,
        "holdout_rows_analysed": 0,
        "n_trades": int(len(r)),
        "total_sum_r": round(float(np.sum(r)), 2),
        "profit_factor": round(_profit_factor(r), 2),
        "passed": len(failed_pillars) == 0,
        "verdict": verdict,
        "failed_pillars": failed_pillars,
        "ranking_score_worst_year_p10_r": wy.get("ranking_score_worst_year_p10_r", 0.0),
        "thresholds": asdict(thresholds),
        "pillars": {
            "R1_random_entry_mc": mc,
            "R2_buy_sell_symmetry": sym,
            "R3_top5_outlier_trim": trim,
            "R4_worst_year_stability": wy,
        },
    }


def _extract_sl_frac(row: dict) -> float:
    ep = float(row.get("entry_price", 0.0))
    if ep <= 1e-9:
        return 0.005
    if "sl_price" in row:
        return max(0.0005, abs(ep - float(row["sl_price"])) / ep)
    if "stop" in row:
        return max(0.0005, abs(ep - float(row["stop"])) / ep)
    asset = str(row.get("asset", ""))
    ir = float(row.get("initial_risk_usd", 0.0))
    if ir <= 1e-9:
        return 0.005
    if asset == "USDJPY":
        return max(0.0005, ir / 100000.0)
    if asset.endswith("USD") and asset not in ("XAUUSD", "BTCUSD"):
        return max(0.0005, ir / (100000.0 * ep))
    return max(0.0005, ir / 100000.0)


def _enforce_holdout_lock_sealed() -> str:
    """Wrap `assert_holdout_locked()` so any missing/corrupt/tampered lock raises `HoldoutLockError`."""
    try:
        return assert_holdout_locked()
    except HoldoutLockError:
        raise
    except Exception as exc:
        raise HoldoutLockError(f"HOLDOUT_LOCK_SEAL_FAILED: {exc}") from exc


def audit_frozen_9e_dev(
    *,
    draws: int = 1000,
    seed: int = 20261124,
    write_report: bool = True,
    verify_sha: bool = True,
) -> dict:
    """Run the 4-pillar Robustness Gate on all 9 frozen Dev engines (2018-2024 ONLY, holdout_rows = 0)."""
    t0 = time.perf_counter()
    lock_sha = _enforce_holdout_lock_sealed()
    data = build_or_load_frozen_tapes(force_rebuild=False)
    tapes = data["tapes"]
    ext_days = data["ext_days"]
    _assert_pre_holdout_days(ext_days)

    reg = load_registry()
    engine_order = reg["frozen_portfolios"]["PORT_9E_P28_TURBO"]["engines"]
    core7_set = set(reg["frozen_portfolios"]["PORT_7E_P28_CORE"]["engines"])

    # Preload M5 resampled real-market Bid/Ask bars from local D: hot_m1_cache (0 holdout rows)
    needed_assets: set[str] = set()
    for eng in engine_order:
        for r, _, _ in tapes[eng].values():
            needed_assets.add(str(r["asset"]))

    m5_cache: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]] = {}
    for sym in sorted(needed_assets):
        ts_m1, q_m1, _ = hcache.load_asset(sym, verify_sha=verify_sha)
        m5_cache[sym] = resample_m1_quotes_to_m5_mid(ts_m1, q_m1)

    engine_results: list[dict] = []
    thresholds = RobustnessThresholds(mc_draws=int(draws))

    for idx_e, eng in enumerate(engine_order):
        dm = tapes[eng]
        days = sorted(dm.keys())
        _assert_pre_holdout_days(days)

        r_list, s_list, dur_m5_list, sl_list, fric_list, asset_list = [], [], [], [], [], []
        for dk in days:
            row, stamps, marks = dm[dk]
            r_list.append(float(row["net_R"]))
            s_list.append(int(row.get("side", 1)))
            dur_min = max(5, len(stamps) - 1)
            dur_m5_list.append(max(1, int(round(dur_min / 5.0))))
            sl_list.append(_extract_sl_frac(row))
            c_usd = estimate_trade_base_cost_usd_per_lot(row, marks)
            fric_list.append(min(0.45, c_usd / max(1e-6, float(row["stop_risk_with_cost_usd"]))))
            asset_list.append(str(row["asset"]))

        r_arr = np.asarray(r_list, dtype=np.float64)
        s_arr = np.asarray(s_list, dtype=np.int64)
        d_arr = np.asarray(dur_m5_list, dtype=np.int64)
        sl_arr = np.asarray(sl_list, dtype=np.float64)
        f_arr = np.asarray(fric_list, dtype=np.float64)

        uniq_assets = sorted(set(asset_list))
        if len(uniq_assets) == 1:
            ts5, o5, h5, l5, c5 = m5_cache[uniq_assets[0]]
            mc = random_entry_mc_on_bars(
                ts=ts5, bar_o=o5, bar_h=h5, bar_l=l5, bar_c=c5, bar_sec=300,
                trade_r=r_arr, trade_sides=s_arr, trade_durs=d_arr,
                trade_sl_fracs=sl_arr, trade_frics=f_arr,
                draws=int(draws), seed=int(seed + idx_e * 101),
            )
        else:
            # Multi-asset basket (e.g. S6_FX_USD_BSK): sum independent per-asset MC draw vectors!
            tot_unb = np.zeros(int(draws), dtype=np.float64)
            tot_same = np.zeros(int(draws), dtype=np.float64)
            buy_tot = np.zeros(int(draws), dtype=np.float64)
            sell_tot = np.zeros(int(draws), dtype=np.float64)
            for a_idx, sym in enumerate(uniq_assets):
                amask = np.array([a == sym for a in asset_list], dtype=np.bool_)
                ts5, o5, h5, l5, c5 = m5_cache[sym]
                _, u_vec = _random_entry_mc_ohlc_kernel(
                    ts5, o5, h5, l5, c5, 300, s_arr[amask], d_arr[amask], sl_arr[amask], f_arr[amask],
                    float(np.sum(r_arr[amask])), 0, int(draws), int(seed + idx_e * 101 + a_idx * 13),
                )
                _, sm_vec = _random_entry_mc_ohlc_kernel(
                    ts5, o5, h5, l5, c5, 300, s_arr[amask], d_arr[amask], sl_arr[amask], f_arr[amask],
                    float(np.sum(r_arr[amask])), 1, int(draws), int(seed + idx_e * 101 + a_idx * 13 + 7),
                )
                tot_unb += u_vec
                tot_same += sm_vec
                bm = amask & (s_arr > 0)
                if np.any(bm):
                    _, b_vec = _random_entry_mc_ohlc_kernel(
                        ts5, o5, h5, l5, c5, 300, s_arr[bm], d_arr[bm], sl_arr[bm], f_arr[bm],
                        float(np.sum(r_arr[bm])), 1, int(draws), int(seed + idx_e * 101 + a_idx * 13 + 19),
                    )
                    buy_tot += b_vec
                sm = amask & (s_arr < 0)
                if np.any(sm):
                    _, s_vec = _random_entry_mc_ohlc_kernel(
                        ts5, o5, h5, l5, c5, 300, s_arr[sm], d_arr[sm], sl_arr[sm], f_arr[sm],
                        float(np.sum(r_arr[sm])), 1, int(draws), int(seed + idx_e * 101 + a_idx * 13 + 29),
                    )
                    sell_tot += s_vec

            obs_sum = float(np.sum(r_arr))
            b_obs = float(np.sum(r_arr[s_arr > 0]))
            s_obs = float(np.sum(r_arr[s_arr < 0]))
            mc = {
                "mc_mode": "real_market_bars_multi_asset",
                "draws": int(draws),
                "obs_sum_r": round(obs_sum, 2),
                "beat_rate_unbiased": round(float(np.mean(obs_sum > tot_unb + 1e-12)), 4),
                "null_unbiased_median_r": round(float(np.median(tot_unb)), 2),
                "null_unbiased_p90_r": round(float(np.quantile(tot_unb, 0.90)), 2),
                "beat_rate_same_side": round(float(np.mean(obs_sum > tot_same + 1e-12)), 4),
                "null_same_side_median_r": round(float(np.median(tot_same)), 2),
                "null_same_side_p90_r": round(float(np.quantile(tot_same, 0.90)), 2),
                "buy_beat_rate_vs_random_buy": round(float(np.mean(b_obs > buy_tot + 1e-12)), 4),
                "buy_null_median_r": round(float(np.median(buy_tot)), 2),
                "sell_beat_rate_vs_random_sell": round(float(np.mean(s_obs > sell_tot + 1e-12)), 4),
                "sell_null_median_r": round(float(np.median(sell_tot)), 2),
            }

        gate_res = evaluate_robustness_gate(
            strategy_id=eng,
            trade_r=r_arr,
            trade_sides=s_arr,
            trade_days=days,
            mc_result=mc,
            thresholds=thresholds,
            seed=int(seed + idx_e * 37),
        )
        gate_res["in_port_7e"] = eng in core7_set
        gate_res["assets"] = uniq_assets
        engine_results.append(gate_res)

    # Sort copy by Worst-Year P10 ranking score (highest resilience first!)
    ranked = sorted(engine_results, key=lambda x: x["ranking_score_worst_year_p10_r"], reverse=True)
    elapsed_sec = round(time.perf_counter() - t0, 2)

    summary = {
        "schema": "naqex-robustness-gate-dev-audit-v1",
        "generated_utc": datetime.now(UTC).isoformat(),
        "holdout_lock_sha256": lock_sha,
        "holdout_rows_analysed": 0,
        "order_send_count": 0,
        "dev_window": f"{ext_days[0]}..{ext_days[-1]}",
        "mc_draws": int(draws),
        "elapsed_sec": elapsed_sec,
        "counts": {
            "total_engines": len(engine_results),
            "pass_robust": sum(1 for x in engine_results if x["verdict"] == "PASS_ROBUST"),
            "warn_asymmetry_or_year": sum(1 for x in engine_results if x["verdict"] == "WARN_ASYMMETRY_OR_YEAR"),
            "fail_fragile": sum(1 for x in engine_results if x["verdict"] == "FAIL_FRAGILE"),
            "mc_unbiased_ge90": sum(
                1 for x in engine_results if x["pillars"]["R1_random_entry_mc"]["beat_rate_unbiased"] >= 0.90
            ),
            "mc_same_side_ge90": sum(
                1 for x in engine_results if x["pillars"]["R1_random_entry_mc"]["beat_rate_same_side"] >= 0.90
            ),
            "top5_trim_positive": sum(1 for x in engine_results if x["pillars"]["R3_top5_outlier_trim"]["passed"]),
            "both_sides_positive": sum(1 for x in engine_results if x["pillars"]["R2_buy_sell_symmetry"]["passed"]),
        },
        "worst_year_ranking": [
            {
                "rank": i + 1,
                "engine": x["strategy_id"],
                "in_port_7e": x["in_port_7e"],
                "verdict": x["verdict"],
                "worst_year_p10_r": x["ranking_score_worst_year_p10_r"],
                "worst_year_r": x["pillars"]["R4_worst_year_stability"]["worst_year_r"],
                "total_sum_r": x["total_sum_r"],
            }
            for i, x in enumerate(ranked)
        ],
        "engines": engine_results,
    }

    if write_report:
        out_dir = ROOT / "planning/research"
        json_path = out_dir / "ROBUSTNESS-GATE-DEV-AUDIT-20261124.json"
        md_path = out_dir / "ROBUSTNESS-GATE-DEV-AUDIT-20261124.md"

        headers = [
            "Engine", "Core", "N", "Raw R", "MC 50/50", "MC Same-Side",
            "BUY R (MC)", "SELL R (MC)", "Trim-5% Win (PF)", "Trim-5% All", "Worst Yr", "WY-P10", "Verdict",
        ]
        rows = []
        for x in engine_results:
            mc = x["pillars"]["R1_random_entry_mc"]
            sym = x["pillars"]["R2_buy_sell_symmetry"]
            tr = x["pillars"]["R3_top5_outlier_trim"]
            wy = x["pillars"]["R4_worst_year_stability"]
            b_rate = mc.get("buy_beat_rate_vs_random_buy")
            s_rate = mc.get("sell_beat_rate_vs_random_sell")
            b_mc = f"{b_rate * 100:.0f}%" if b_rate is not None else "n/a"
            s_mc = f"{s_rate * 100:.0f}%" if s_rate is not None else "n/a"
            rows.append([
                x["strategy_id"],
                "7E" if x["in_port_7e"] else "Sat",
                str(x["n_trades"]),
                f"{x['total_sum_r']:+.1f}R",
                f"{mc['beat_rate_unbiased']*100:.1f}%",
                f"{mc['beat_rate_same_side']*100:.1f}%",
                f"{sym['buy']['sum_r']:+.1f}R ({b_mc})",
                f"{sym['sell']['sum_r']:+.1f}R ({s_mc})",
                f"{tr['trimmed_winners_sum_r']:+.1f}R ({tr['trimmed_winners_pf']:.2f})",
                f"{tr['trimmed_all_sum_r']:+.1f}R",
                f"{wy['worst_year']} {wy['worst_year_r']:+.1f}R",
                f"{wy['mc_worst_year_p10_r']:+.1f}R",
                x["verdict"],
            ])

        c = summary["counts"]
        md = [
            "# Kiểm Toán Cổng Robustness 4 Trụ Cột Trên 9 Động Cơ Dev (`2018–2024`, `holdout_rows = 0`)",
            "",
            (
                f"- **Phạm vi dữ liệu:** `{summary['dev_window']}` "
                "(niêm phong tuyệt đối `Holdout 2025+`, `holdout_rows_analysed = 0`, `order_send_count = 0`)."
            ),
            (
                f"- **Mô phỏng Random-Entry MC trên nến M5 thật (`hot_m1_cache`):** "
                f"`{draws}` lần/động cơ, thời gian chạy `{elapsed_sec}s`."
            ),
            (
                f"- **Tổng hợp nhanh:** `MC 50/50 >= 90%`: **{c['mc_unbiased_ge90']}/9** · "
                f"`MC Same-Side >= 90%`: **{c['mc_same_side_ge90']}/9** · "
                f"`Cả BUY & SELL dương`: **{c['both_sides_positive']}/9** · "
                f"`Cắt Top-5% vẫn dương`: **{c['top5_trim_positive']}/9**."
            ),
            (
                f"- **Phân loại:** `PASS_ROBUST = {c['pass_robust']}/9` · "
                f"`WARN_ASYMMETRY_OR_YEAR = {c['warn_asymmetry_or_year']}/9` · "
                f"`FAIL_FRAGILE = {c['fail_fragile']}/9`."
            ),
            "",
            "## Bảng Kết Quả Chi Tiết 9 Động Cơ (Dev `2018–2024`)",
            "",
            format_markdown_table(headers, rows),
            "",
            "## Bảng Xếp Hạng Theo Điểm Năm Tệ Nhất (`mc_worst_year_p10_r`)",
            "",
            format_markdown_table(
                ["Hạng", "Động cơ", "Nhóm", "WY-P10 Score", "Năm tệ nhất", "Tổng R", "Kết luận"],
                [
                    [
                        str(r["rank"]), r["engine"], "PORT_7E" if r["in_port_7e"] else "Satellite",
                        f"{r['worst_year_p10_r']:+.1f}R", f"{r['worst_year_r']:+.1f}R",
                        f"{r['total_sum_r']:+.1f}R", r["verdict"],
                    ]
                    for r in summary["worst_year_ranking"]
                ],
            ),
            "",
        ]
        write_verified_receipt(json_path, summary, overwrite=True)
        md_path.write_text("\n".join(md) + "\n", encoding="utf-8", newline="\n")

    return summary


def _cli_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Naqex Pre-Promotion 4-Pillar Robustness Gate (Dev < 2025-01-01 ONLY)")
    parser.add_argument(
        "--audit-frozen-9e",
        action="store_true",
        help="Audit all 9 frozen Dev engines on sealed pre-2025 bars",
    )
    parser.add_argument(
        "--draws",
        type=int,
        default=1000,
        help="Number of Random-Entry Monte Carlo draws (default: 1000)",
    )
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="Print JSON summary without writing planning/research report",
    )
    args = parser.parse_args(argv)
    if args.audit_frozen_9e:
        res = audit_frozen_9e_dev(draws=args.draws, write_report=not args.no_write)
        payload = {
            "counts": res["counts"],
            "elapsed_sec": res["elapsed_sec"],
            "ranking": res["worst_year_ranking"],
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli_main())

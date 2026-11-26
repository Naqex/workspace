"""Single canonical quantitative statistics and timezone-reset module (ZERO scipy imports).

Implements:
- `compute_sharpe`: calendar-aligned vs active-day Sharpe reporting.
- `compute_drawdowns`: prop static floor (`dd_of_initial_frac`) and peak-to-trough (`dd_of_peak_frac`).
- `deflated_sharpe_ratio_empirical`: Bailey & Lopez de Prado (2014) empirical-variance DSR (no silent proxy).
- `compute_pbo_cscv`: Bailey, Borwein, Lopez de Prado & Zhu (2014/2017) CSCV Probability of Backtest Overfitting.
- `combinatorial_purged_cv`: Lopez de Prado (2018) CPCV split generator with strict purging & embargoing.
- `hansen_spa_test`: Hansen (2005) studentized Superior Predictive Ability stationary bootstrap test.
- `white_reality_check`: White (2000) Reality Check stationary bootstrap test.
- `firm_reset_day_key` / `firm_reset_midnight_utc`: DST-safe IANA `zoneinfo.ZoneInfo` reset clock.
"""

from __future__ import annotations

import itertools
import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from statistics import NormalDist
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import numpy as np
from numpy.typing import ArrayLike, NDArray

_NORMAL = NormalDist(0.0, 1.0)
_EULER_MASCHERONI = 0.5772156649015329


def _as_finite_1d(values: ArrayLike, name: str) -> NDArray[np.float64]:
    arr = np.asarray(values)
    if arr.dtype == np.bool_:
        raise ValueError(f"{name} must be numeric, not bool")
    if arr.ndim != 1:
        raise ValueError(f"{name} must be 1D, got shape {arr.shape}")
    out = arr.astype(np.float64, copy=False)
    if out.size == 0:
        raise ValueError(f"{name} must not be empty")
    if not np.all(np.isfinite(out)):
        raise ValueError(f"{name} contains NaN or Inf")
    return out


def _as_finite_2d(values: ArrayLike, name: str, *, allow_1d: bool = False) -> NDArray[np.float64]:
    arr = np.asarray(values)
    if arr.dtype == np.bool_:
        raise ValueError(f"{name} must be numeric, not bool")
    if allow_1d and arr.ndim == 1:
        arr = arr[:, None]
    if arr.ndim != 2:
        raise ValueError(f"{name} must be 2D, got shape {arr.shape}")
    out = arr.astype(np.float64, copy=False)
    if out.shape[0] == 0 or out.shape[1] == 0:
        raise ValueError(f"{name} must be non-empty, got shape {out.shape}")
    if not np.all(np.isfinite(out)):
        raise ValueError(f"{name} contains NaN or Inf")
    return out


@dataclass(frozen=True, slots=True)
class SharpeResult:
    sharpe_annualized: float
    sharpe_per_period: float
    mean_return: float
    std_return: float
    active_days: int
    calendar_days: int
    calendar_aligned: bool
    annualization_days: int


@dataclass(frozen=True, slots=True)
class DrawdownResult:
    dd_of_initial_frac: float
    dd_of_peak_frac: float
    max_peak_to_trough_usd: float
    max_peak_to_trough_of_initial_frac: float
    min_equity_usd: float
    peak_equity_usd: float
    used_intraday_lows: bool


@dataclass(frozen=True, slots=True)
class DSRResult:
    dsr: float
    z_stat: float
    observed_sr: float
    observed_sr_annualized: float
    expected_max_sr: float
    sr_trials_var: float
    n_trials: int
    skewness: float
    kurtosis: float
    n_obs: int


@dataclass(frozen=True, slots=True)
class PBOResult:
    pbo: float
    logit_distribution: tuple[float, ...]
    is_overfit: bool
    n_slices: int
    n_combinations: int
    n_trials: int
    prob_oos_nonpositive_sr: float


@dataclass(frozen=True, slots=True)
class CPCVSplit:
    split_id: int
    test_groups: tuple[int, ...]
    train_indices: tuple[int, ...]
    test_indices: tuple[int, ...]
    purged_indices: tuple[int, ...]
    embargoed_indices: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class SPATestResult:
    t_stat: float
    spa_p_consistent: float
    spa_p_lower: float
    spa_p_upper: float
    best_model_index: int
    n_obs: int
    n_models: int
    n_boot: int
    block_len: int
    seed: int


@dataclass(frozen=True, slots=True)
class WhiteRCResult:
    p_value: float
    v_stat: float
    best_model_index: int
    n_obs: int
    n_models: int
    n_boot: int
    block_len: int
    seed: int


def compute_sharpe(
    returns: ArrayLike,
    *,
    annualization_days: int = 252,
    calendar_aligned: bool = True,
) -> SharpeResult:
    """Compute Sharpe ratio while explicitly distinguishing `active_days` vs `calendar_days`."""
    if type(annualization_days) is not int or annualization_days <= 0:
        raise ValueError("annualization_days must be a positive integer")
    if type(calendar_aligned) is not bool:
        raise ValueError("calendar_aligned must be bool")

    r = _as_finite_1d(returns, "returns")
    calendar_days = int(r.size)
    active_mask = np.abs(r) > 0.0
    active_days = int(np.count_nonzero(active_mask))
    sample = r if calendar_aligned else r[active_mask]

    if sample.size < 2:
        mean_val = float(np.mean(sample)) if sample.size == 1 else 0.0
        return SharpeResult(
            sharpe_annualized=0.0,
            sharpe_per_period=0.0,
            mean_return=mean_val,
            std_return=0.0,
            active_days=active_days,
            calendar_days=calendar_days,
            calendar_aligned=calendar_aligned,
            annualization_days=annualization_days,
        )

    mean_val = float(np.mean(sample))
    std_val = float(np.std(sample, ddof=1))
    if std_val <= 1e-15:
        sr_period = 0.0
        sr_ann = 0.0
    else:
        sr_period = mean_val / std_val
        sr_ann = sr_period * math.sqrt(float(annualization_days))

    return SharpeResult(
        sharpe_annualized=sr_ann,
        sharpe_per_period=sr_period,
        mean_return=mean_val,
        std_return=std_val,
        active_days=active_days,
        calendar_days=calendar_days,
        calendar_aligned=calendar_aligned,
        annualization_days=annualization_days,
    )


def compute_drawdowns(
    equity_curve: ArrayLike,
    initial_capital: float,
    intraday_lows: ArrayLike | None = None,
) -> DrawdownResult:
    """Compute BOTH prop static-floor DD (`dd_of_initial_frac`) and peak-to-trough DD (`dd_of_peak_frac`)."""
    if isinstance(initial_capital, bool) or not isinstance(initial_capital, (int, float)):
        raise ValueError("initial_capital must be a positive finite number")
    cap = float(initial_capital)
    if not math.isfinite(cap) or cap <= 0.0:
        raise ValueError("initial_capital must be > 0 and finite")

    eq = _as_finite_1d(equity_curve, "equity_curve")
    used_lows = intraday_lows is not None
    if intraday_lows is not None:
        lows = _as_finite_1d(intraday_lows, "intraday_lows")
        if lows.shape != eq.shape:
            raise ValueError(f"intraday_lows shape {lows.shape} must match equity_curve shape {eq.shape}")
        if np.any(lows > eq + 1e-9):
            raise ValueError("intraday_lows cannot exceed equity_curve close values")
    else:
        lows = eq

    running_peak = cap
    max_dd_peak_frac = 0.0
    max_dd_usd = 0.0
    min_eq = float(min(np.min(eq), np.min(lows)))

    for t in range(eq.size):
        # Evaluate intraday low against causal peak established strictly before/at bar start
        low_t = float(lows[t])
        close_t = float(eq[t])
        dd_low_usd = max(0.0, running_peak - low_t)
        if dd_low_usd > max_dd_usd:
            max_dd_usd = dd_low_usd
        if running_peak > 0.0:
            dd_low_frac = dd_low_usd / running_peak
            if dd_low_frac > max_dd_peak_frac:
                max_dd_peak_frac = dd_low_frac

        if close_t > running_peak:
            running_peak = close_t
        dd_close_usd = max(0.0, running_peak - close_t)
        if dd_close_usd > max_dd_usd:
            max_dd_usd = dd_close_usd
        if running_peak > 0.0:
            dd_close_frac = dd_close_usd / running_peak
            if dd_close_frac > max_dd_peak_frac:
                max_dd_peak_frac = dd_close_frac

    dd_of_initial_frac = max(0.0, (cap - min_eq) / cap)
    return DrawdownResult(
        dd_of_initial_frac=dd_of_initial_frac,
        dd_of_peak_frac=max_dd_peak_frac,
        max_peak_to_trough_usd=max_dd_usd,
        max_peak_to_trough_of_initial_frac=max_dd_usd / cap,
        min_equity_usd=min_eq,
        peak_equity_usd=running_peak,
        used_intraday_lows=used_lows,
    )


def deflated_sharpe_ratio_empirical(
    returns: ArrayLike,
    *,
    trial_sharpes: ArrayLike | None = None,
    sr_trials_var: float | None = None,
    n_trials: int | None = None,
    annualization_days: int = 252,
    sharpes_are_annualized: bool = False,
) -> DSRResult:
    """True Bailey & Lopez de Prado (2014) Deflated Sharpe Ratio using empirical trial variance.

    Raises `ValueError` if `n_trials > 1` and neither `trial_sharpes` nor `sr_trials_var`
    is provided (never substitutes a silent `1/(T-1)` proxy).
    """
    if type(annualization_days) is not int or annualization_days <= 0:
        raise ValueError("annualization_days must be a positive integer")
    r = _as_finite_1d(returns, "returns")
    n_obs = int(r.size)
    if n_obs < 3:
        raise ValueError("returns must contain at least 3 observations for DSR skewness/kurtosis")

    mean_r = float(np.mean(r))
    std_r = float(np.std(r, ddof=1))
    if std_r <= 1e-15:
        raise ValueError("returns have zero variance; Sharpe ratio is undefined")

    sr_obs = mean_r / std_r
    centered = r - mean_r
    m2 = float(np.mean(centered**2))
    m3 = float(np.mean(centered**3))
    m4 = float(np.mean(centered**4))
    skew = m3 / (m2**1.5)
    kurt = m4 / (m2**2)

    if trial_sharpes is not None and sr_trials_var is not None:
        raise ValueError("provide either trial_sharpes or sr_trials_var, not both")

    eff_n_trials: int
    eff_var: float

    if trial_sharpes is not None:
        ts = _as_finite_1d(trial_sharpes, "trial_sharpes")
        if sharpes_are_annualized:
            ts = ts / math.sqrt(float(annualization_days))
        if n_trials is None:
            eff_n_trials = int(ts.size)
        else:
            if type(n_trials) is not int or n_trials < ts.size:
                raise ValueError("n_trials must be an integer >= len(trial_sharpes)")
            eff_n_trials = n_trials
        if eff_n_trials > 1:
            if ts.size < 2:
                raise ValueError("trial_sharpes requires at least 2 entries when n_trials > 1")
            eff_var = float(np.var(ts, ddof=1))
        else:
            eff_var = 0.0
    elif sr_trials_var is not None:
        if isinstance(sr_trials_var, bool) or not isinstance(sr_trials_var, (int, float)):
            raise ValueError("sr_trials_var must be a non-negative finite number")
        raw_var = float(sr_trials_var)
        if not math.isfinite(raw_var) or raw_var < 0.0:
            raise ValueError("sr_trials_var must be finite and >= 0")
        if n_trials is None or type(n_trials) is not int or n_trials < 1:
            raise ValueError("n_trials must be an integer >= 1 when sr_trials_var is supplied")
        eff_n_trials = n_trials
        eff_var = raw_var / float(annualization_days) if sharpes_are_annualized else raw_var
    else:
        if n_trials is None:
            eff_n_trials = 1
            eff_var = 0.0
        else:
            if type(n_trials) is not int or n_trials < 1:
                raise ValueError("n_trials must be a positive integer")
            if n_trials > 1:
                raise ValueError(
                    "empirical DSR requires trial_sharpes or sr_trials_var when n_trials > 1 (no 1/(T-1) proxy)"
                )
            eff_n_trials = 1
            eff_var = 0.0

    if eff_n_trials == 1 or eff_var == 0.0:
        sr_star = 0.0
    else:
        p1 = 1.0 - 1.0 / float(eff_n_trials)
        p2 = 1.0 - 1.0 / (float(eff_n_trials) * math.e)
        z1 = _NORMAL.inv_cdf(p1)
        z2 = _NORMAL.inv_cdf(p2)
        sr_star = math.sqrt(eff_var) * ((1.0 - _EULER_MASCHERONI) * z1 + _EULER_MASCHERONI * z2)

    denom_sq = 1.0 - skew * sr_obs + ((kurt - 1.0) / 4.0) * (sr_obs**2)
    denom = math.sqrt(max(denom_sq, 1e-18))
    z_stat = ((sr_obs - sr_star) * math.sqrt(float(n_obs - 1))) / denom
    dsr = float(_NORMAL.cdf(z_stat))

    return DSRResult(
        dsr=dsr,
        z_stat=z_stat,
        observed_sr=sr_obs,
        observed_sr_annualized=sr_obs * math.sqrt(float(annualization_days)),
        expected_max_sr=sr_star,
        sr_trials_var=eff_var,
        n_trials=eff_n_trials,
        skewness=skew,
        kurtosis=kurt,
        n_obs=n_obs,
    )


def compute_pbo_cscv(returns_matrix: ArrayLike, *, n_slices: int = 16) -> PBOResult:
    """Bailey, Borwein, Lopez de Prado & Zhu (2014/2017) CSCV Probability of Backtest Overfitting.

    Input `returns_matrix` has shape `(T, M)` where `T` is time steps and `M >= 2` is candidate trials.
    """
    mat = _as_finite_2d(returns_matrix, "returns_matrix")
    n_obs, n_trials = mat.shape
    if n_trials < 2:
        raise ValueError(f"returns_matrix requires at least 2 candidate columns, got {n_trials}")
    if type(n_slices) is not int or n_slices < 4 or n_slices % 2 != 0:
        raise ValueError("n_slices must be an even integer >= 4")
    if n_obs < n_slices:
        raise ValueError(f"returns_matrix rows ({n_obs}) must be >= n_slices ({n_slices})")

    slice_len = n_obs // n_slices
    usable_rows = slice_len * n_slices
    trimmed = mat[:usable_rows, :]

    # Subtract full-sample column mean for catastrophic-cancellation-free sufficient statistics
    col_mean = np.mean(trimmed, axis=0)
    centered = trimmed - col_mean[None, :]
    blocks = centered.reshape(n_slices, slice_len, n_trials)
    sum_y = np.sum(blocks, axis=1)  # (S, M)
    sumsq_y = np.sum(blocks * blocks, axis=1)  # (S, M)
    total_sum_y = np.sum(sum_y, axis=0)  # (M,)
    total_sumsq_y = np.sum(sumsq_y, axis=0)  # (M,)

    half_slices = n_slices // 2
    n_half = half_slices * slice_len
    if n_half < 2:
        raise ValueError("each CSCV half-sample must contain at least 2 observations")

    combos = np.array(list(itertools.combinations(range(n_slices), half_slices)), dtype=np.intp)
    n_combos = int(combos.shape[0])

    # Evaluate in memory-bounded chunks so large S*M never spikes RAM
    chunk_size = 2048
    logits_parts: list[NDArray[np.float64]] = []
    oos_nonpos_count = 0

    for start in range(0, n_combos, chunk_size):
        idx_chunk = combos[start : start + chunk_size]  # (C, S/2)
        c_len = idx_chunk.shape[0]
        is_sum_y = np.sum(sum_y[idx_chunk], axis=1)  # (C, M)
        is_sumsq_y = np.sum(sumsq_y[idx_chunk], axis=1)  # (C, M)
        oos_sum_y = total_sum_y[None, :] - is_sum_y
        oos_sumsq_y = total_sumsq_y[None, :] - is_sumsq_y

        is_mean = col_mean[None, :] + is_sum_y / float(n_half)
        oos_mean = col_mean[None, :] + oos_sum_y / float(n_half)

        is_var = np.maximum(0.0, (is_sumsq_y - (is_sum_y * is_sum_y) / float(n_half)) / float(n_half - 1))
        oos_var = np.maximum(0.0, (oos_sumsq_y - (oos_sum_y * oos_sum_y) / float(n_half)) / float(n_half - 1))

        is_sr = np.where(is_var > 1e-24, is_mean / np.sqrt(np.where(is_var > 1e-24, is_var, 1.0)), 0.0)
        oos_sr = np.where(oos_var > 1e-24, oos_mean / np.sqrt(np.where(oos_var > 1e-24, oos_var, 1.0)), 0.0)

        winners = np.argmax(is_sr, axis=1)  # (C,)
        row_ids = np.arange(c_len)
        winner_oos_sr = oos_sr[row_ids, winners]  # (C,)
        oos_nonpos_count += int(np.count_nonzero(winner_oos_sr <= 0.0))

        # Exact tie-aware 1-based rank in [1, M], scaled to omega in (0, 1) via rank / (M + 1)
        win_col = winner_oos_sr[:, None]
        n_less = np.sum(oos_sr < win_col, axis=1)
        n_equal = np.sum(oos_sr == win_col, axis=1)
        ranks = n_less.astype(np.float64) + 0.5 * (n_equal.astype(np.float64) + 1.0)
        omega = ranks / float(n_trials + 1)
        logits_parts.append(np.log(omega / (1.0 - omega)))

    logits = np.concatenate(logits_parts)
    pbo = float(np.mean((logits < 0.0).astype(np.float64) + 0.5 * (logits == 0.0).astype(np.float64)))
    return PBOResult(
        pbo=pbo,
        logit_distribution=tuple(float(x) for x in logits),
        is_overfit=bool(pbo > 0.50),
        n_slices=n_slices,
        n_combinations=n_combos,
        n_trials=n_trials,
        prob_oos_nonpositive_sr=float(oos_nonpos_count) / float(n_combos),
    )


def combinatorial_purged_cv(
    n_samples: int,
    *,
    n_groups: int = 6,
    k_test_groups: int = 2,
    purge_bars: int = 1,
    embargo_bars: int = 1,
) -> list[CPCVSplit]:
    """Lopez de Prado (2018) Combinatorial Purged Cross-Validation split generator.

    Guarantees 0 overlap between train and test, purging `purge_bars` immediately before
    every contiguous test segment and embargoing `embargo_bars` immediately after.
    """
    for val, name, lo in (
        (n_samples, "n_samples", 2),
        (n_groups, "n_groups", 2),
        (k_test_groups, "k_test_groups", 1),
        (purge_bars, "purge_bars", 0),
        (embargo_bars, "embargo_bars", 0),
    ):
        if type(val) is not int or val < lo:
            raise ValueError(f"{name} must be an integer >= {lo}")
    if k_test_groups >= n_groups:
        raise ValueError("k_test_groups must be strictly less than n_groups")
    if n_samples < n_groups:
        raise ValueError(f"n_samples ({n_samples}) must be >= n_groups ({n_groups})")

    blocks = [tuple(int(i) for i in blk) for blk in np.array_split(np.arange(n_samples), n_groups)]
    splits: list[CPCVSplit] = []

    for split_id, test_group_ids in enumerate(itertools.combinations(range(n_groups), k_test_groups)):
        test_set: set[int] = set()
        for gid in test_group_ids:
            test_set.update(blocks[gid])
        test_sorted = tuple(sorted(test_set))

        # Merge adjacent selected groups into contiguous [seg_start, seg_end] test segments
        segments: list[tuple[int, int]] = []
        seg_start = test_sorted[0]
        seg_prev = test_sorted[0]
        for idx in test_sorted[1:]:
            if idx == seg_prev + 1:
                seg_prev = idx
            else:
                segments.append((seg_start, seg_prev))
                seg_start = idx
                seg_prev = idx
        segments.append((seg_start, seg_prev))

        purged: set[int] = set()
        embargoed: set[int] = set()
        for s_start, s_end in segments:
            for p_idx in range(max(0, s_start - purge_bars), s_start):
                if p_idx not in test_set:
                    purged.add(p_idx)
            for e_idx in range(s_end + 1, min(n_samples, s_end + embargo_bars + 1)):
                if e_idx not in test_set:
                    embargoed.add(e_idx)

        excluded = test_set | purged | embargoed
        train_sorted = tuple(i for i in range(n_samples) if i not in excluded)
        splits.append(
            CPCVSplit(
                split_id=split_id,
                test_groups=test_group_ids,
                train_indices=train_sorted,
                test_indices=test_sorted,
                purged_indices=tuple(sorted(purged)),
                embargoed_indices=tuple(sorted(embargoed)),
            )
        )

    return splits


def _stationary_bootstrap_indices(n_obs: int, n_boot: int, block_len: int, seed: int) -> NDArray[np.intp]:
    """Politis & Romano (1994) stationary bootstrap index matrix `(n_boot, n_obs)`."""
    if type(n_boot) is not int or n_boot < 1:
        raise ValueError("n_boot must be a positive integer")
    if type(block_len) is not int or block_len < 1:
        raise ValueError("block_len must be a positive integer")
    if type(seed) is not int:
        raise ValueError("seed must be an integer")

    rng = np.random.default_rng(seed)
    q = 1.0 / float(block_len)
    idx = np.empty((n_boot, n_obs), dtype=np.intp)
    idx[:, 0] = rng.integers(0, n_obs, size=n_boot)
    if n_obs == 1:
        return idx
    jumps = rng.random(size=(n_boot, n_obs - 1)) < q
    fresh = rng.integers(0, n_obs, size=(n_boot, n_obs - 1))
    for t in range(1, n_obs):
        step_forward = (idx[:, t - 1] + 1) % n_obs
        idx[:, t] = np.where(jumps[:, t - 1], fresh[:, t - 1], step_forward)
    return idx


def _hansen_hac_variance(excess: NDArray[np.float64], block_len: int) -> NDArray[np.float64]:
    """Exact Politis-Romano / Hansen (2005) Eq. 5 asymptotic variance `omega_hat^2` of `sqrt(T)*d_bar`."""
    if type(block_len) is not int or block_len < 1:
        raise ValueError("block_len must be an integer >= 1")
    n_obs = excess.shape[0]
    q = 1.0 / float(block_len)
    centered = excess - np.mean(excess, axis=0, keepdims=True)
    # Exact linear sample autocovariances gamma_i = (1/T) sum_{t=0}^{T-1-i} c_t c_{t+i} via zero-padded FFT
    n_fft = 1 << (2 * n_obs - 1).bit_length()
    spec = np.fft.rfft(centered, n=n_fft, axis=0)
    acov = np.fft.irfft(spec.real * spec.real + spec.imag * spec.imag, n=n_fft, axis=0)[:n_obs] / float(n_obs)

    lags = np.arange(1, n_obs, dtype=np.float64)
    one_minus_q = 1.0 - q
    if one_minus_q == 0.0:
        omega_sq = acov[0].copy()
    else:
        kappa = ((float(n_obs) - lags) / float(n_obs)) * (one_minus_q**lags) + (lags / float(n_obs)) * (
            one_minus_q ** (float(n_obs) - lags)
        )
        omega_sq = acov[0] + 2.0 * np.sum(kappa[:, None] * acov[1:], axis=0)
    return np.maximum(omega_sq, 0.0)


def hansen_spa_test(
    benchmark_excess_matrix: ArrayLike,
    *,
    n_boot: int = 1000,
    block_len: int = 5,
    seed: int = 20261127,
) -> SPATestResult:
    """Hansen (2005) studentized Superior Predictive Ability stationary bootstrap test.

    Guarantees `0.0 <= spa_p_lower <= spa_p_consistent <= spa_p_upper <= 1.0`.
    """
    if type(n_boot) is not int or n_boot < 1:
        raise ValueError("n_boot must be an integer >= 1")
    if type(block_len) is not int or block_len < 1:
        raise ValueError("block_len must be an integer >= 1")
    if type(seed) is not int:
        raise ValueError("seed must be an integer")

    d = _as_finite_2d(benchmark_excess_matrix, "benchmark_excess_matrix", allow_1d=True)
    n_obs, n_models = d.shape
    if n_obs < 3:
        raise ValueError("benchmark_excess_matrix requires at least 3 time steps")

    sqrt_t = math.sqrt(float(n_obs))
    d_bar = np.mean(d, axis=0)  # (M,)
    omega_sq = _hansen_hac_variance(d, block_len)
    omega = np.sqrt(omega_sq)

    valid_var = omega > 1e-15
    safe_omega = np.where(valid_var, omega, 1.0)
    studentized_obs = np.where(valid_var, (sqrt_t * d_bar) / safe_omega, 0.0)

    best_idx = int(np.argmax(studentized_obs))
    t_obs = max(0.0, float(studentized_obs[best_idx]))

    if t_obs <= 0.0:
        return SPATestResult(
            t_stat=0.0,
            spa_p_consistent=1.0,
            spa_p_lower=1.0,
            spa_p_upper=1.0,
            best_model_index=best_idx,
            n_obs=n_obs,
            n_models=n_models,
            n_boot=n_boot,
            block_len=block_len,
            seed=seed,
        )

    # Three Hansen (2005) re-centering vectors mu^l <= mu^c <= mu^u = 0
    threshold = math.sqrt(2.0 * math.log(max(math.log(float(n_obs)), 1.000001)))
    mu_lower = np.minimum(d_bar, 0.0)
    mu_consistent = np.where(studentized_obs <= -threshold, d_bar, 0.0)
    mu_upper = np.zeros_like(d_bar)

    boot_idx = _stationary_bootstrap_indices(n_obs, n_boot, block_len, seed)
    # Compute bootstrap means in chunks to keep memory small
    chunk_size = 250
    t_lower_list: list[NDArray[np.float64]] = []
    t_cons_list: list[NDArray[np.float64]] = []
    t_upper_list: list[NDArray[np.float64]] = []

    for start in range(0, n_boot, chunk_size):
        b_idx = boot_idx[start : start + chunk_size]
        boot_means = np.mean(d[b_idx], axis=1)  # (B_c, M)
        centered_boot = boot_means - d_bar[None, :]

        z_l = np.where(valid_var[None, :], sqrt_t * (centered_boot + mu_lower[None, :]) / safe_omega[None, :], 0.0)
        z_c = np.where(valid_var[None, :], sqrt_t * (centered_boot + mu_consistent[None, :]) / safe_omega[None, :], 0.0)
        z_u = np.where(valid_var[None, :], sqrt_t * (centered_boot + mu_upper[None, :]) / safe_omega[None, :], 0.0)

        t_lower_list.append(np.maximum(0.0, np.max(z_l, axis=1)))
        t_cons_list.append(np.maximum(0.0, np.max(z_c, axis=1)))
        t_upper_list.append(np.maximum(0.0, np.max(z_u, axis=1)))

    t_lower = np.concatenate(t_lower_list)
    t_cons = np.concatenate(t_cons_list)
    t_upper = np.concatenate(t_upper_list)

    p_lower = float(np.mean(t_lower > t_obs))
    p_cons = float(np.mean(t_cons > t_obs))
    p_upper = float(np.mean(t_upper > t_obs))

    return SPATestResult(
        t_stat=t_obs,
        spa_p_consistent=p_cons,
        spa_p_lower=p_lower,
        spa_p_upper=p_upper,
        best_model_index=best_idx,
        n_obs=n_obs,
        n_models=n_models,
        n_boot=n_boot,
        block_len=block_len,
        seed=seed,
    )


def white_reality_check(
    benchmark_excess_matrix: ArrayLike,
    *,
    n_boot: int = 1000,
    block_len: int = 5,
    seed: int = 20261127,
) -> WhiteRCResult:
    """White (2000) Reality Check for data snooping via stationary bootstrap."""
    if type(n_boot) is not int or n_boot < 1:
        raise ValueError("n_boot must be an integer >= 1")
    if type(block_len) is not int or block_len < 1:
        raise ValueError("block_len must be an integer >= 1")
    if type(seed) is not int:
        raise ValueError("seed must be an integer")

    d = _as_finite_2d(benchmark_excess_matrix, "benchmark_excess_matrix", allow_1d=True)
    n_obs, n_models = d.shape
    if n_obs < 2:
        raise ValueError("benchmark_excess_matrix requires at least 2 time steps")

    sqrt_t = math.sqrt(float(n_obs))
    d_bar = np.mean(d, axis=0)
    best_idx = int(np.argmax(d_bar))
    v_obs = float(sqrt_t * d_bar[best_idx])

    boot_idx = _stationary_bootstrap_indices(n_obs, n_boot, block_len, seed)
    chunk_size = 250
    v_boot_parts: list[NDArray[np.float64]] = []
    for start in range(0, n_boot, chunk_size):
        b_idx = boot_idx[start : start + chunk_size]
        boot_means = np.mean(d[b_idx], axis=1)
        v_boot_parts.append(np.max(sqrt_t * (boot_means - d_bar[None, :]), axis=1))

    v_boot = np.concatenate(v_boot_parts)
    p_val = float(np.mean(v_boot > v_obs))

    return WhiteRCResult(
        p_value=p_val,
        v_stat=v_obs,
        best_model_index=best_idx,
        n_obs=n_obs,
        n_models=n_models,
        n_boot=n_boot,
        block_len=block_len,
        seed=seed,
    )


def _coerce_utc_datetime(ts_utc: int | float | datetime) -> datetime:
    if isinstance(ts_utc, datetime):
        if ts_utc.tzinfo is None or ts_utc.utcoffset() is None:
            raise ValueError("ts_utc datetime must be timezone-aware")
        return ts_utc.astimezone(UTC)
    if isinstance(ts_utc, bool) or not isinstance(ts_utc, (int, float)):
        raise ValueError("ts_utc must be an epoch timestamp (int/float) or timezone-aware datetime")
    val = float(ts_utc)
    if not math.isfinite(val):
        raise ValueError("ts_utc must be finite")
    return datetime.fromtimestamp(val, tz=UTC)


def _resolve_iana_zone(reset_tz: str) -> ZoneInfo:
    if not isinstance(reset_tz, str) or not reset_tz.strip() or reset_tz.strip() != reset_tz:
        raise ValueError("reset_tz must be a canonical non-empty IANA timezone string")
    if reset_tz.upper().startswith(("UTC+", "UTC-", "GMT+", "GMT-")):
        raise ValueError(f"reset_tz must be a canonical IANA timezone, not fixed offset: {reset_tz!r}")
    try:
        return ZoneInfo(reset_tz)
    except (ZoneInfoNotFoundError, ValueError, KeyError) as exc:
        raise ValueError(f"invalid IANA timezone: {reset_tz!r}") from exc


def firm_reset_day_key(ts_utc: int | float | datetime, reset_tz: str) -> str:
    """Return DST-safe local reset day key (`YYYY-MM-DD`) using `zoneinfo.ZoneInfo`."""
    dt_utc = _coerce_utc_datetime(ts_utc)
    zone = _resolve_iana_zone(reset_tz)
    return dt_utc.astimezone(zone).date().isoformat()


def firm_reset_midnight_utc(ts_utc: int | float | datetime, reset_tz: str) -> int:
    """Return exact UTC epoch seconds of `00:00:00` local reset midnight for `ts_utc` in `reset_tz`."""
    dt_utc = _coerce_utc_datetime(ts_utc)
    zone = _resolve_iana_zone(reset_tz)
    local_dt = dt_utc.astimezone(zone)
    midnight_local = datetime(local_dt.year, local_dt.month, local_dt.day, 0, 0, 0, tzinfo=zone, fold=0)
    return int(midnight_local.astimezone(UTC).timestamp())


def batch_firm_reset_day_keys(timestamps_utc: Sequence[int | float | datetime], reset_tz: str) -> list[str]:
    """Convert a sequence of UTC timestamps to DST-safe local reset day keys."""
    zone = _resolve_iana_zone(reset_tz)
    return [_coerce_utc_datetime(ts).astimezone(zone).date().isoformat() for ts in timestamps_utc]


__all__ = [
    "CPCVSplit",
    "DSRResult",
    "DrawdownResult",
    "PBOResult",
    "SPATestResult",
    "SharpeResult",
    "WhiteRCResult",
    "batch_firm_reset_day_keys",
    "combinatorial_purged_cv",
    "compute_drawdowns",
    "compute_pbo_cscv",
    "compute_sharpe",
    "deflated_sharpe_ratio_empirical",
    "firm_reset_day_key",
    "firm_reset_midnight_utc",
    "hansen_spa_test",
    "white_reality_check",
]

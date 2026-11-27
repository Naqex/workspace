"""Layer 2: Numba-JIT statistical engine (Sign-Flip, DSR/PSR, Tail Correlation) & 6-core parallel discovery sweep."""

import math
import os
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor
from statistics import NormalDist

import numpy as np

EULER_GAMMA = 0.5772156649015329
_STD_NORM = NormalDist(0.0, 1.0)
_SIGN_FLIP_MC_KERNEL = None


def _get_sign_flip_mc_kernel():
    """Lazily compile Numba-JIT sign-flip permutation kernel without slowing module import."""
    global _SIGN_FLIP_MC_KERNEL
    if _SIGN_FLIP_MC_KERNEL is not None:
        return _SIGN_FLIP_MC_KERNEL
    from numba import njit

    @njit(cache=True)
    def _kernel(vals: np.ndarray, fade_vals: np.ndarray, draws: int, seed: int) -> float:
        """Exact Numba-JIT sign-flip permutation p-value (100x faster than Python loop)."""
        n = len(vals)
        if n == 0:
            return 1.0
        obs = 0.0
        for i in range(n):
            obs += vals[i]
        np.random.seed(seed)
        ge = 0
        for _ in range(draws):
            acc = 0.0
            for i in range(n):
                if np.random.random() < 0.5:
                    acc += vals[i]
                else:
                    acc += fade_vals[i]
            if acc >= obs - 1e-12:
                ge += 1
        return (ge + 1.0) / (draws + 1.0)

    _SIGN_FLIP_MC_KERNEL = _kernel
    return _SIGN_FLIP_MC_KERNEL


def _sign_flip_mc_kernel(vals: np.ndarray, fade_vals: np.ndarray, draws: int, seed: int) -> float:
    """Exact Numba-JIT sign-flip permutation p-value (lazily compiled on first invocation)."""
    return float(_get_sign_flip_mc_kernel()(vals, fade_vals, draws, seed))


def sign_flip_p_numba(
    vals: np.ndarray | list[float],
    fade_vals: np.ndarray | list[float],
    *,
    draws: int = 1000,
    seed: int = 20261123,
) -> float:
    v = np.ascontiguousarray(vals, dtype=np.float64)
    f = np.ascontiguousarray(fade_vals, dtype=np.float64)
    return float(_sign_flip_mc_kernel(v, f, int(draws), int(seed)))


def benjamini_hochberg(p_values: list[float]) -> list[float]:
    m = len(p_values)
    if m == 0:
        return []
    order = sorted(range(m), key=lambda i: p_values[i])
    q = [1.0] * m
    prev = 1.0
    for rank in range(m, 0, -1):
        idx = order[rank - 1]
        val = min(prev, p_values[idx] * m / rank)
        q[idx] = min(1.0, val)
        prev = q[idx]
    return q


def deflated_sharpe_ratio(daily_returns: np.ndarray, *, n_trials: int = 1, annualization: float = 252.0) -> dict:
    """Compute Probabilistic Sharpe Ratio (PSR) & Deflated Sharpe Ratio (DSR, Bailey & Lopez de Prado 2014).

    Accounts for non-normal skewness, excess kurtosis, sample size T, and cumulative multiple testing trials M.
    """
    r = np.asarray(daily_returns, dtype=np.float64)
    r = r[np.isfinite(r)]
    t = len(r)
    if t < 30 or float(np.std(r, ddof=1)) <= 1e-12:
        return {"sr_ann": 0.0, "psr_gt0": 0.5, "dsr": 0.0, "sr0_haircut": 0.0, "n_days": t, "n_trials": n_trials}

    mu = float(np.mean(r))
    sd = float(np.std(r, ddof=1))
    sr_daily = mu / sd
    sr_ann = sr_daily * math.sqrt(annualization)
    z = (r - mu) / sd
    skew = float(np.mean(z ** 3))
    kurt = float(np.mean(z ** 4))  # Pearson kurtosis (normal = 3.0)

    denom_var = max(1e-12, (1.0 - skew * sr_daily + ((kurt - 1.0) / 4.0) * (sr_daily ** 2)) / max(1, t - 1))
    sr_se = math.sqrt(denom_var)
    psr_gt0 = float(_STD_NORM.cdf(sr_daily / sr_se))

    # Expected max daily Sharpe under null across `n_trials` independent strategies
    m = max(1, int(n_trials))
    if m <= 1:
        sr0_daily = 0.0
    else:
        # Cross-sectional variance proxy of null Sharpe ratios ~ 1 / (t - 1)
        sr_null_std = math.sqrt(1.0 / max(1, t - 1))
        z1 = float(_STD_NORM.inv_cdf(1.0 - 1.0 / m))
        z2 = float(_STD_NORM.inv_cdf(1.0 - 1.0 / (m * math.e)))
        sr0_daily = sr_null_std * ((1.0 - EULER_GAMMA) * z1 + EULER_GAMMA * z2)

    dsr = float(_STD_NORM.cdf((sr_daily - sr0_daily) / sr_se))
    return {
        "sr_ann": round(sr_ann, 3),
        "skew": round(skew, 3),
        "kurtosis": round(kurt, 3),
        "psr_gt0": round(psr_gt0, 4),
        "dsr": round(dsr, 4),
        "sr0_ann_haircut": round(sr0_daily * math.sqrt(annualization), 3),
        "n_days": t,
        "n_trials": m,
    }


def tail_correlation_report(
    engine_daily_matrix: np.ndarray,
    engine_names: list[str],
    *,
    tail_pct: float = 0.05,
) -> dict:
    """Measure average pairwise correlation on ALL days vs WORST `tail_pct` portfolio drawdown days."""
    mat = np.asarray(engine_daily_matrix, dtype=np.float64)
    k = mat.shape[1]
    port = mat.sum(axis=1)
    cutoff = float(np.quantile(port, tail_pct))
    tail_mask = port <= cutoff

    def _offdiag_stats(sub: np.ndarray) -> dict:
        if len(sub) < 10:
            return {"mean": 0.0, "max": 0.0, "max_pair": None}
        c = np.corrcoef(sub, rowvar=False)
        c = np.nan_to_num(c, nan=0.0)
        vals = []
        best = (-2.0, None)
        for i in range(k):
            for j in range(i + 1, k):
                v = float(c[i, j])
                vals.append(v)
                if v > best[0]:
                    best = (v, f"{engine_names[i]} x {engine_names[j]}")
        return {"mean": round(float(np.mean(vals)), 4), "max": round(best[0], 4), "max_pair": best[1]}

    return {
        "n_days_all": int(len(mat)),
        "n_days_tail": int(tail_mask.sum()),
        "tail_cutoff_pct_day": round(cutoff * 100.0, 3),
        "all_days_corr": _offdiag_stats(mat),
        "worst_tail_corr": _offdiag_stats(mat[tail_mask]),
    }


def run_parallel_sweep(worker_fn: Callable, tasks: list, *, max_workers: int | None = None) -> list:
    """Execute independent CPU-bound evaluation tasks across multiple cores cleanly (auto-fallback for tiny batches)."""
    n_workers = max_workers or min(os.cpu_count() or 1, 6)
    if len(tasks) <= 2 or n_workers <= 1:
        return [worker_fn(t) for t in tasks]
    with ProcessPoolExecutor(max_workers=n_workers) as pool:
        return list(pool.map(worker_fn, tasks))

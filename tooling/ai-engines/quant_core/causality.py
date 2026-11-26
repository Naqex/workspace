"""Strictly causal prefix-invariance verification for NumPy OHLC bundles and 1D series (P0-8).

Runs BOTH:
  1. True prefix truncation (`times[:t+1], quotes[:t+1]`) — catches full-sample
     normalization, lookahead indexing, and tail-dependent state leaks.
  2. Non-monotonic randomized perturbation across ALL columns `> t` (including all
     8 Bid/Ask OHLC columns while preserving valid OHLC & Bid<=Ask invariants) —
     defeats scale-invariant `* const` blind spots, quantile leaks, and mean/vol leaks.

ZERO `scipy` imports and ZERO Python `assert` statements (active even under `python -O`).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

import numpy as np
from numpy.typing import ArrayLike, NDArray


class CausalityViolationError(ValueError):
    """Raised when a signal, feature, or transform violates causal prefix invariance."""


def _validate_probe_indices(n: int, probe_indices: Sequence[int]) -> list[int]:
    if n < 2:
        raise ValueError(f"Need at least 2 observations for causality check, got {n}")
    probes = [int(p) for p in probe_indices]
    if not probes:
        raise ValueError("probe_indices must be non-empty")
    for p in probes:
        if p < 0 or p >= n - 1:
            raise ValueError(f"probe index {p} out of valid range [0, {n - 2}]")
    return probes


def _arrays_match(
    ref: NDArray[Any],
    cand: NDArray[Any],
    *,
    atol: float,
    label: str,
    probe_idx: int,
) -> None:
    if ref.shape != cand.shape:
        raise CausalityViolationError(
            f"CAUSALITY_SHAPE_MISMATCH [{label} @ t={probe_idx}]: expected {ref.shape}, got {cand.shape}"
        )
    if np.issubdtype(ref.dtype, np.floating) or np.issubdtype(cand.dtype, np.floating):
        ref_f = ref.astype(np.float64, copy=False)
        cand_f = cand.astype(np.float64, copy=False)
        if not np.allclose(ref_f, cand_f, rtol=0.0, atol=atol, equal_nan=True):
            diff = np.abs(np.where(np.isnan(ref_f) & np.isnan(cand_f), 0.0, ref_f - cand_f))
            max_diff = float(np.nanmax(diff)) if diff.size else float("inf")
            bad_pos = tuple(int(x) for x in np.argwhere(diff > atol)[0]) if np.any(diff > atol) else (0,)
            raise CausalityViolationError(
                f"CAUSALITY_VIOLATION [{label} @ t={probe_idx}]: prefix drift max_abs_diff={max_diff:.3e} "
                f"(atol={atol:.1e}) at index {bad_pos}"
            )
    else:
        if not np.array_equal(ref, cand):
            bad = np.flatnonzero(ref != cand)
            first_bad = int(bad[0]) if bad.size else 0
            raise CausalityViolationError(
                f"CAUSALITY_VIOLATION [{label} @ t={probe_idx}]: exact mismatch at index {first_bad} "
                f"(ref={ref.ravel()[first_bad]!r}, got={cand.ravel()[first_bad]!r})"
            )


def perturb_future_quotes_non_monotonic(
    quotes: NDArray[np.float64],
    split_idx: int,
    *,
    seed: int = 20261127,
) -> NDArray[np.float64]:
    """Perturb all rows `> split_idx` across all Bid/Ask OHLC columns non-monotonically.

    Preserves valid positive OHLC (`low <= open,close <= high`) and `Bid <= Ask` invariants
    while injecting non-monotonic jumps, volatility regime flips, trend reversals, and
    randomized spread shocks that defeat scale-invariant (`* 100`) and rank-invariant leaks.
    """
    q = np.asarray(quotes, dtype=np.float64)
    if q.ndim != 2 or q.shape[1] < 4:
        raise ValueError(f"quotes must be 2D with >= 4 OHLC columns, got shape {q.shape}")
    out = q.copy()
    tail_len = q.shape[0] - (split_idx + 1)
    if tail_len <= 0:
        return out

    rng = np.random.default_rng(int(seed) + int(split_idx) * 1009)
    anchor_px = max(float(np.median(np.abs(q[: split_idx + 1, 0]))), 1e-4)

    # Non-monotonic oscillating regime shifts + wild alternating shocks + randomized scale
    step_idx = np.arange(tail_len, dtype=np.float64)
    osc = 0.25 * np.sin(0.37 * step_idx + rng.uniform(0.0, 2.0 * np.pi))
    jump_signs = rng.choice([-1.0, 1.0], size=tail_len)
    jump_mags = rng.uniform(0.05, 0.45, size=tail_len)
    log_path = np.clip(osc + jump_signs * jump_mags + rng.normal(0.0, 0.18, size=tail_len), -1.2, 1.2)
    base_scale = anchor_px * np.exp(log_path)

    bo = base_scale * rng.uniform(0.92, 1.08, size=tail_len)
    bc = base_scale * rng.uniform(0.88, 1.14, size=tail_len)
    hi_pad = base_scale * rng.uniform(0.005, 0.12, size=tail_len)
    lo_pad = base_scale * rng.uniform(0.005, 0.12, size=tail_len)
    bh = np.maximum(bo, bc) + hi_pad
    bl = np.maximum(anchor_px * 1e-4, np.minimum(bo, bc) - lo_pad)

    out[split_idx + 1 :, 0] = bo
    out[split_idx + 1 :, 1] = bh
    out[split_idx + 1 :, 2] = bl
    out[split_idx + 1 :, 3] = bc

    if q.shape[1] >= 8:
        # Independent randomized positive spread shocks across all 4 Ask columns
        # while preserving Ask >= Bid and AL <= AO, AC <= AH
        spr_o = base_scale * rng.uniform(0.0005, 0.035, size=tail_len)
        spr_c = base_scale * rng.uniform(0.0005, 0.035, size=tail_len)
        spr_h = base_scale * rng.uniform(0.0005, 0.045, size=tail_len)
        spr_l = base_scale * rng.uniform(0.0005, 0.025, size=tail_len)
        ao = bo + spr_o
        ac = bc + spr_c
        ah = np.maximum(bh + spr_h, np.maximum(ao, ac))
        al = np.minimum(np.maximum(bl + spr_l, bl), np.minimum(ao, ac))
        out[split_idx + 1 :, 4] = ao
        out[split_idx + 1 :, 5] = ah
        out[split_idx + 1 :, 6] = al
        out[split_idx + 1 :, 7] = ac
    elif q.shape[1] > 4:
        # Perturb any auxiliary columns non-monotonically as well
        extra = q.shape[1] - 4
        out[split_idx + 1 :, 4:] = rng.normal(0.0, 5.0, size=(tail_len, extra)) * (1.0 + np.abs(q[split_idx + 1 :, 4:]))

    return out


def perturb_future_series_non_monotonic(
    values: NDArray[np.float64],
    split_idx: int,
    *,
    seed: int = 20261127,
) -> NDArray[np.float64]:
    """Perturb 1D series `> split_idx` non-monotonically (mean, std, skew, sign, and quantile shift)."""
    v = np.asarray(values, dtype=np.float64)
    out = v.copy()
    tail_len = v.shape[0] - (split_idx + 1)
    if tail_len <= 0:
        return out

    rng = np.random.default_rng(int(seed) + int(split_idx) * 2027)
    prefix = v[: split_idx + 1]
    finite_pref = prefix[np.isfinite(prefix)]
    scale = max(float(np.std(finite_pref)) if finite_pref.size >= 2 else 1.0, 1.0)
    shift = float(np.mean(finite_pref)) if finite_pref.size >= 1 else 0.0

    # Mix large positive/negative alternating spikes + regime-shifted Gaussian noise
    signs = rng.choice([-1.0, 1.0], size=tail_len)
    mags = rng.uniform(3.0, 25.0, size=tail_len) * scale
    drift = rng.normal(shift + 5.0 * scale, 8.0 * scale, size=tail_len)
    out[split_idx + 1 :] = drift + signs * mags
    return out


def assert_prefix_invariance_numpy(
    signal_fn: Callable[[NDArray[np.int64], NDArray[np.float64]], ArrayLike],
    times: ArrayLike,
    quotes: ArrayLike,
    probe_indices: Sequence[int],
    *,
    atol: float = 1e-12,
    seed: int = 20261127,
) -> dict[str, Any]:
    """Verify `signal_fn(times, quotes)` is strictly causal on `(times, quotes)` NumPy bundles.

    Checks BOTH (1) true prefix truncation `times[:t+1], quotes[:t+1]` AND
    (2) non-monotonic randomized perturbation of `quotes[t+1:]` across all columns.
    Raises `CausalityViolationError` on any violation (immune to `python -O`).
    """
    ts = np.ascontiguousarray(times, dtype=np.int64)
    qs = np.ascontiguousarray(quotes, dtype=np.float64)
    if ts.ndim != 1:
        raise ValueError(f"times must be 1D, got shape {ts.shape}")
    if qs.ndim != 2 or qs.shape[0] != ts.shape[0]:
        raise ValueError(f"quotes shape {qs.shape} incompatible with times shape {ts.shape}")

    probes = _validate_probe_indices(int(ts.shape[0]), probe_indices)
    full_out = np.asarray(signal_fn(ts, qs))
    if full_out.ndim == 0 or full_out.shape[0] != ts.shape[0]:
        raise ValueError(
            f"signal_fn output first axis ({full_out.shape}) must match len(times) ({ts.shape[0]})"
        )

    for t in probes:
        # 1. True prefix truncation
        trunc_out = np.asarray(signal_fn(ts[: t + 1], qs[: t + 1]))
        _arrays_match(full_out[: t + 1], trunc_out, atol=atol, label="true_truncation", probe_idx=t)

        # 2. Non-monotonic randomized future perturbation across all columns > t
        q_pert = perturb_future_quotes_non_monotonic(qs, t, seed=seed)
        pert_out = np.asarray(signal_fn(ts, q_pert))
        _arrays_match(
            full_out[: t + 1],
            pert_out[: t + 1],
            atol=atol,
            label="non_monotonic_perturbation",
            probe_idx=t,
        )

    return {
        "passed": True,
        "probes_checked": probes,
        "atol": float(atol),
        "checks": ("true_truncation", "non_monotonic_perturbation"),
    }


def assert_prefix_invariance_series(
    fn: Callable[[NDArray[np.float64]], ArrayLike],
    values: ArrayLike,
    probe_indices: Sequence[int],
    *,
    atol: float = 1e-12,
    seed: int = 20261127,
) -> dict[str, Any]:
    """Verify a 1D series transform `fn(values)` is strictly causal via truncation + non-monotonic perturbation."""
    arr = np.ascontiguousarray(values, dtype=np.float64)
    if arr.ndim != 1:
        raise ValueError(f"values must be 1D, got shape {arr.shape}")

    probes = _validate_probe_indices(int(arr.shape[0]), probe_indices)
    full_out = np.asarray(fn(arr))
    if full_out.ndim == 0 or full_out.shape[0] != arr.shape[0]:
        raise ValueError(
            f"fn output first axis ({full_out.shape}) must match len(values) ({arr.shape[0]})"
        )

    for t in probes:
        # 1. True prefix truncation
        trunc_out = np.asarray(fn(arr[: t + 1]))
        _arrays_match(full_out[: t + 1], trunc_out, atol=atol, label="series_truncation", probe_idx=t)

        # 2. Non-monotonic future perturbation
        arr_pert = perturb_future_series_non_monotonic(arr, t, seed=seed)
        pert_out = np.asarray(fn(arr_pert))
        _arrays_match(
            full_out[: t + 1],
            pert_out[: t + 1],
            atol=atol,
            label="series_non_monotonic_perturbation",
            probe_idx=t,
        )

    return {
        "passed": True,
        "probes_checked": probes,
        "atol": float(atol),
        "checks": ("series_truncation", "series_non_monotonic_perturbation"),
    }


__all__ = [
    "CausalityViolationError",
    "assert_prefix_invariance_numpy",
    "assert_prefix_invariance_series",
    "perturb_future_quotes_non_monotonic",
    "perturb_future_series_non_monotonic",
]

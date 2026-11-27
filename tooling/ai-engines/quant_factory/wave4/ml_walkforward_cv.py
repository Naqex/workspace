"""Wave 4 Strictly Causal Purged+Embargo Walk-Forward CV, Inside-Fold Feature Pruning,
Brier Skill > 0 Gate, 5-Family Model Registry, and DuckDB `wave4_ml_m48` Budget Ledger
(`v4.8.1 FINAL`, `W4-G04` foundation for `w4-m1-arena`).

Hard safety & methodological invariants (ZERO exceptions):
  - `ORDER_SEND_CAPABLE = False`, `ORDER_SEND_COUNT = 0`, `0 VND`.
  - Holdout `2025+` SEALED (`HOLDOUT_CUTOFF_DATE = "2024-12-31"`, `DEV_CUTOFF_SEC = 1_735_689_600`,
    `holdout_rows_analysed = 0`). All guards use explicit `if ...: raise ...` (ZERO bare `assert`s,
    100% active under `python -O` / `python -OO`).
  - LAZY IMPORTS ONLY for optional ML & DB wheels (`sklearn`, `lightgbm`, `catboost`, `onnx`,
    `onnxmltools`, `skl2onnx`, `onnxruntime`, `duckdb`, `scipy`, `pandas`). Module top-level
    depends strictly on Python stdlib + NumPy (+ `ml_features_24`, which is stdlib + NumPy).
  - ZERO `hmmlearn` dependency! Family #4 is `Regime GMM (sklearn.mixture.GaussianMixture)` /
    pure-NumPy Causal Forward-Only Jump-HMM.
  - ZERO external `shap` dependency! Native attribution for all 5 families (`exact_linear_coefficients`,
    `lightgbm pred_contrib`, `catboost ShapValues`, `regime_margin_perturbation`, and
    `calibrated_chain_rule`).
  - ZERO reverse-time fold leakage! Strictly Expanding/Rolling Purged + Embargo Walk-Forward
    (`purge_days >= 5`, `embargo_days >= 10`) verifying `max(exit_ts[train]) + purge_days <= min(entry_ts[val])`
    and `max(exit_ts[train]) + (purge_days + embargo_days) <= min(entry_ts[val])`.
  - Law 13 Honesty: NEVER label `PORT_7E` Dev Cluster B (`2021-01-01..2024-12-31`) as `"BLIND"` —
    ALWAYS tag it `CONSUMED_DEV_CLB_TEMPORAL_OOS`.
  - Mandatory `Brier Skill > 0` gate (`brier_skill_score = 1 - brier_model / brier_climatology > 0`),
    Engine Balance Guard across all engines (`E1..E7`), and 24m median slippage breakeven check
    (`1.50x -> >= 1.75x`) yielding `PROMOTE_V104_ML` or `REJECT_ML_KEEP_V103`.
  - DuckDB Experiment Budget Ledger `wave4_ml_m48` enforcing `<= 48` total trials fail-closed.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
import threading
import weakref
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import numpy as np

from quant_factory.wave4.ml_features_24 import (
    DEFAULT_ENGINE_BASE_RISK_PCT,
    DEV_CUTOFF_DATE,
    DEV_CUTOFF_SEC,
    ENGINE_ID_CODES,
    FEATURE_NAMES_24,
    HOLDOUT_CUTOFF_DATE,
    ORDER_SEND_CAPABLE,
    ORDER_SEND_COUNT,
    _parse_timestamp_array,
    _reject_bool_scalar,
    _validate_finite_float,
    _validate_float_array,
    parse_cutoff_utc_exclusive,
)

# ---------------------------------------------------------------------------
# Hard Safety Constants & Canonical Contract Tags
# ---------------------------------------------------------------------------

SCHEMA_VERSION: str = "naqex-wave4-ml-walkforward-cv-v1"
CONSUMED_CLB_TAG: str = "CONSUMED_DEV_CLB_TEMPORAL_OOS"
VERDICT_PROMOTE: str = "PROMOTE_V104_ML"
VERDICT_REJECT: str = "REJECT_ML_KEEP_V103"

MIN_PURGE_DAYS: int = 5
MIN_EMBARGO_DAYS: int = 10
DEFAULT_PURGE_DAYS: int = 5
DEFAULT_EMBARGO_DAYS: int = 10
DEFAULT_MIN_TRAIN_SAMPLES: int = 300
DEFAULT_MIN_SELECTED_FEATURES: int = 8
DEFAULT_MAX_SELECTED_FEATURES: int = 12
DEFAULT_MAX_ML_TRIALS: int = 48
DEFAULT_SLIPPAGE_MULTS: tuple[float, ...] = (1.0, 1.5, 1.75, 2.0)
DEFAULT_BASELINE_SLIPPAGE_BREAKEVEN: float = 1.50
DEFAULT_TARGET_SLIPPAGE_BREAKEVEN: float = 1.75
DEFAULT_BASE_COST_R: float = 0.08
DEFAULT_MIN_ENGINE_RETENTION: float = 0.50
DEFAULT_MIN_OVERALL_RETENTION: float = 0.50
DEFAULT_ML_BUDGET_DB_PATH: str = ".runtime/offensive4/ml/wave4_ml_m48.duckdb"
DEFAULT_TABLE_NAME: str = "wave4_ml_m48"

MODEL_FAMILIES: tuple[str, ...] = (
    "logit_l2",
    "lightgbm",
    "catboost",
    "regime_gmm_jump",
    "calibrated_bet_sizing",
)

_SECONDS_PER_DAY: int = 86_400
_EPS: float = 1e-12
_PROB_CLIP: float = 1e-6


# ---------------------------------------------------------------------------
# Explicit Fail-Closed Exceptions (Subclass ValueError for Compatibility)
# ---------------------------------------------------------------------------


class HoldoutCutoffBreachError(ValueError):
    """Raised when any cutoff, entry timestamp, or exit timestamp breaches sealed 2025+ Holdout."""


class CausalityViolationError(ValueError):
    """Raised when train/val splits overlap, invert chronology, or violate purge/embargo gaps."""


class Law13HonestyError(ValueError):
    """Raised when consumed Dev Cluster B OOS is dishonestly labeled as BLIND."""


class BudgetExceededError(ValueError):
    """Raised fail-closed when ML experiment budget (`<= 48` trials) is exceeded."""


# ---------------------------------------------------------------------------
# Core Validation & Math Primitives (Pure NumPy, Zero Bare `assert`)
# ---------------------------------------------------------------------------


def validate_oos_label(oos_label: str) -> str:
    """Enforce Law 13 honesty: NEVER allow 'BLIND' label on consumed Dev Cluster B OOS."""
    if not isinstance(oos_label, str) or not oos_label.strip():
        raise Law13HonestyError(f"LAW13_HONESTY_VIOLATION: oos_label must be non-empty string, got {oos_label!r}")
    norm = oos_label.strip()
    if "BLIND" in norm.upper():
        raise Law13HonestyError(
            f"LAW13_HONESTY_VIOLATION: forbidden 'BLIND' tag in oos_label={oos_label!r}; "
            f"PORT_7E Dev Cluster B (2021-01-01..2024-12-31) MUST be tagged {CONSUMED_CLB_TAG!r}"
        )
    return norm


def _enforce_cutoff_exclusive(cutoff_utc: str | date | datetime | int) -> int:
    try:
        return parse_cutoff_utc_exclusive(cutoff_utc)
    except ValueError as exc:
        if "HOLDOUT" in str(exc):
            raise HoldoutCutoffBreachError(str(exc)) from exc
        raise


def _validate_int_param(value: Any, *, name: str, minimum: int | None = None, maximum: int | None = None) -> int:
    _reject_bool_scalar(value, name=name)
    if not isinstance(value, (int, np.integer)):
        raise ValueError(f"INVALID_INT_PARAM [{name}]: expected int, got {value!r} ({type(value).__name__})")
    iv = int(value)
    if minimum is not None and iv < minimum:
        raise ValueError(f"INVALID_INT_PARAM [{name}]: {iv} < minimum {minimum}")
    if maximum is not None and iv > maximum:
        raise ValueError(f"INVALID_INT_PARAM [{name}]: {iv} > maximum {maximum}")
    return iv


def _validate_binary_targets(y_raw: Any, *, name: str = "y") -> np.ndarray:
    arr = _validate_float_array(y_raw, name=name)
    if arr.ndim != 1:
        raise ValueError(f"INVALID_TARGET_SHAPE [{name}]: expected 1D array, got shape {arr.shape}")
    if arr.size > 0:
        is_binary = np.all((arr == 0.0) | (arr == 1.0))
        if not bool(is_binary):
            raise ValueError(f"NON_BINARY_TARGET [{name}]: all labels must be strictly 0 or 1")
    return arr


def _validate_feature_matrix(x_raw: Any, *, name: str = "X") -> np.ndarray:
    arr = _validate_float_array(x_raw, name=name)
    if arr.ndim != 2:
        raise ValueError(f"INVALID_FEATURE_MATRIX [{name}]: expected 2D array, got shape {arr.shape}")
    if arr.shape[1] == 0:
        raise ValueError(f"INVALID_FEATURE_MATRIX [{name}]: feature dimension must be >= 1")
    return arr


def _validate_feature_names(feature_names: Sequence[str] | None, n_features: int) -> tuple[str, ...]:
    if feature_names is None:
        if n_features <= len(FEATURE_NAMES_24):
            return FEATURE_NAMES_24[:n_features]
        return tuple(f"feature_{j}" for j in range(n_features))
    names = tuple(str(f).strip() for f in feature_names)
    if len(names) != n_features:
        raise ValueError(f"FEATURE_NAME_MISMATCH: got {len(names)} feature names for {n_features} columns")
    if any(not nm for nm in names):
        raise ValueError("INVALID_FEATURE_NAME: empty feature name detected")
    if len(set(names)) != len(names):
        raise ValueError("DUPLICATE_FEATURE_NAMES: feature_names must be unique")
    return names


def _sigmoid(z: np.ndarray) -> np.ndarray:
    zc = np.clip(np.asarray(z, dtype=np.float64), -35.0, 35.0)
    return 1.0 / (1.0 + np.exp(-zc))


def _logit(p: np.ndarray) -> np.ndarray:
    pc = np.clip(np.asarray(p, dtype=np.float64), _PROB_CLIP, 1.0 - _PROB_CLIP)
    return np.log(pc / (1.0 - pc))


def _standard_normal_cdf(z: np.ndarray) -> np.ndarray:
    # Pure stdlib math.erf vectorized for zero-scipy dependency
    arr = np.asarray(z, dtype=np.float64)
    inv_sqrt2 = 1.0 / math.sqrt(2.0)
    out = np.empty_like(arr, dtype=np.float64)
    flat_in = arr.ravel()
    flat_out = out.ravel()
    for i in range(flat_in.size):
        flat_out[i] = 0.5 * (1.0 + math.erf(float(flat_in[i]) * inv_sqrt2))
    return out


def _fit_train_scaler(x_train: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mu = np.mean(x_train, axis=0)
    sd = np.std(x_train, axis=0, ddof=0)
    sd_safe = np.where(sd > 1e-8, sd, 1.0)
    return mu, sd_safe


def _apply_scaler(x: np.ndarray, mu: np.ndarray, sd: np.ndarray) -> np.ndarray:
    return (x - mu) / sd


def compute_exact_roc_auc(y_true: np.ndarray, y_prob: np.ndarray) -> float:
    """Compute exact tie-aware Mann-Whitney ROC-AUC in O(N log N) pure NumPy."""
    y = _validate_binary_targets(y_true, name="y_true")
    p = _validate_float_array(y_prob, name="y_prob")
    if y.shape != p.shape:
        raise ValueError(f"SHAPE_MISMATCH: y_true {y.shape} vs y_prob {p.shape}")
    n = int(y.size)
    if n == 0:
        return 0.5
    n_pos = int(np.sum(y >= 0.5))
    n_neg = n - n_pos
    if n_pos == 0 or n_neg == 0:
        return 0.5

    order = np.argsort(p, kind="mergesort")
    p_sorted = p[order]
    y_sorted = y[order]

    ranks = np.empty(n, dtype=np.float64)
    i = 0
    while i < n:
        j = i + 1
        while j < n and p_sorted[j] == p_sorted[i]:
            j += 1
        avg_rank = 0.5 * (i + 1 + j)
        ranks[i:j] = avg_rank
        i = j

    sum_pos_ranks = float(np.sum(ranks[y_sorted >= 0.5]))
    auc = (sum_pos_ranks - 0.5 * n_pos * (n_pos + 1)) / float(n_pos * n_neg)
    return float(np.clip(auc, 0.0, 1.0))


def compute_brier_metrics(y_true: np.ndarray, y_prob: np.ndarray) -> dict[str, float]:
    """Compute Brier score, climatology Brier, Brier Skill Score, log-loss, and ROC-AUC."""
    y = _validate_binary_targets(y_true, name="y_true")
    p_raw = _validate_float_array(y_prob, name="y_prob")
    if y.shape != p_raw.shape:
        raise ValueError(f"SHAPE_MISMATCH: y_true {y.shape} vs y_prob {p_raw.shape}")
    if p_raw.size > 0 and (float(np.min(p_raw)) < -1e-9 or float(np.max(p_raw)) > 1.0 + 1e-9):
        raise ValueError(
            f"INVALID_PROBABILITY_RANGE: expected probabilities in [0, 1], "
            f"got [{float(np.min(p_raw))}, {float(np.max(p_raw))}]"
        )
    if y.size == 0:
        return {
            "n": 0,
            "base_rate": 0.0,
            "brier_model": 0.25,
            "brier_climatology": 0.25,
            "brier_skill_score": 0.0,
            "logloss": math.log(2.0),
            "roc_auc": 0.5,
        }
    p = np.clip(p_raw, _PROB_CLIP, 1.0 - _PROB_CLIP)
    base_rate = float(np.mean(y))
    brier_model = float(np.mean((p - y) ** 2))
    brier_clim = float(np.mean((base_rate - y) ** 2))
    skill = (1.0 - (brier_model / brier_clim)) if brier_clim > _EPS else 0.0
    logloss = float(-np.mean(y * np.log(p) + (1.0 - y) * np.log(1.0 - p)))
    auc = compute_exact_roc_auc(y, p)
    return {
        "n": int(y.size),
        "base_rate": base_rate,
        "brier_model": brier_model,
        "brier_climatology": brier_clim,
        "brier_skill_score": skill,
        "logloss": logloss,
        "roc_auc": auc,
    }


# ---------------------------------------------------------------------------
# 1. Strictly Causal Expanding/Rolling Purged + Embargo Walk-Forward Splitter
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FoldAuditMetadata:
    fold_index: int
    n_train: int
    n_val: int
    n_purged: int
    n_embargoed: int
    train_entry_min_ts: int
    train_exit_max_ts: int
    val_entry_min_ts: int
    val_exit_max_ts: int
    observed_gap_days: float


def verify_fold_causality(
    train_idx: np.ndarray | Sequence[int],
    val_idx: np.ndarray | Sequence[int],
    entry_ts: Any,
    exit_ts: Any | None = None,
    *,
    purge_days: int = DEFAULT_PURGE_DAYS,
    embargo_days: int = DEFAULT_EMBARGO_DAYS,
    cutoff_utc: str | date | datetime | int = HOLDOUT_CUTOFF_DATE,
) -> dict[str, Any]:
    """Fail-closed verifier proving zero overlap, forward chronology, purge+embargo gap, and Holdout seal.

    Raises:
      - `HoldoutCutoffBreachError` if any timestamp >= cutoff (or cutoff > 2024-12-31).
      - `CausalityViolationError` on any index overlap, reverse-time leak, or purge/embargo gap breach.
    """
    purge_d = _validate_int_param(purge_days, name="purge_days", minimum=MIN_PURGE_DAYS)
    embargo_d = _validate_int_param(embargo_days, name="embargo_days", minimum=MIN_EMBARGO_DAYS)
    cutoff_sec = _enforce_cutoff_exclusive(cutoff_utc)

    ent = _parse_timestamp_array(entry_ts, name="entry_ts")
    ex = ent.copy() if exit_ts is None else _parse_timestamp_array(exit_ts, name="exit_ts")
    n = int(ent.size)
    if ex.shape != ent.shape:
        raise ValueError(f"TIMESTAMP_LENGTH_MISMATCH: entry_ts ({n}) vs exit_ts ({ex.size})")
    if n == 0:
        raise CausalityViolationError("EMPTY_TIMESTAMPS: cannot verify fold on empty dataset")
    if int(np.max(ent)) >= cutoff_sec or int(np.max(ex)) >= cutoff_sec:
        raise HoldoutCutoffBreachError(
            f"HOLDOUT_TIMESTAMP_BREACH: max(entry_ts)={int(np.max(ent))}, "
            f"max(exit_ts)={int(np.max(ex))} >= cutoff_sec_exclusive={cutoff_sec}"
        )
    if bool(np.any(ex < ent)):
        bad_pos = int(np.flatnonzero(ex < ent)[0])
        raise CausalityViolationError(
            f"INVALID_TRADE_INTERVAL: exit_ts[{bad_pos}]={int(ex[bad_pos])} < entry_ts[{bad_pos}]={int(ent[bad_pos])}"
        )

    tr_raw = np.asarray(train_idx)
    va_raw = np.asarray(val_idx)
    if tr_raw.dtype == np.bool_ or va_raw.dtype == np.bool_:
        raise CausalityViolationError("POISONED_BOOL_INDEX: pass integer index arrays, not boolean masks")
    if tr_raw.ndim != 1 or va_raw.ndim != 1:
        raise CausalityViolationError("INVALID_INDEX_NDIM: train_idx and val_idx must be 1D integer arrays")
    if not np.issubdtype(tr_raw.dtype, np.integer) or not np.issubdtype(va_raw.dtype, np.integer):
        raise CausalityViolationError("INVALID_INDEX_DTYPE: train_idx and val_idx must have integer dtype")

    tr = np.asarray(tr_raw, dtype=np.int64)
    va = np.asarray(va_raw, dtype=np.int64)
    if tr.size == 0 or va.size == 0:
        raise CausalityViolationError(f"EMPTY_FOLD_SLICE: n_train={tr.size}, n_val={va.size}")
    if int(np.min(tr)) < 0 or int(np.max(tr)) >= n or int(np.min(va)) < 0 or int(np.max(va)) >= n:
        raise CausalityViolationError(f"INDEX_OUT_OF_RANGE: valid indices are [0, {n - 1}]")

    tr_set = set(tr.tolist())
    va_set = set(va.tolist())
    if len(tr_set) != tr.size:
        raise CausalityViolationError("DUPLICATE_TRAIN_INDICES: train_idx contains duplicate rows")
    if len(va_set) != va.size:
        raise CausalityViolationError("DUPLICATE_VAL_INDICES: val_idx contains duplicate rows")

    overlap = tr_set & va_set
    if overlap:
        raise CausalityViolationError(
            f"FOLD_OVERLAP_DETECTED: {len(overlap)} shared index(es) between train and val (e.g. {min(overlap)})"
        )

    max_train_entry = int(np.max(ent[tr]))
    max_train_exit = int(np.max(ex[tr]))
    min_val_entry = int(np.min(ent[va]))
    max_val_exit = int(np.max(ex[va]))

    if max_train_entry >= min_val_entry:
        raise CausalityViolationError(
            f"REVERSE_TIME_LEAKAGE: max(entry_ts[train])={max_train_entry} >= min(entry_ts[val])={min_val_entry}"
        )

    purge_sec = purge_d * _SECONDS_PER_DAY
    embargo_sec = embargo_d * _SECONDS_PER_DAY
    total_gap_sec = purge_sec + embargo_sec

    if max_train_exit > min_val_entry:
        raise CausalityViolationError(
            f"OVERLAPPING_TRADE_LEAKAGE: max(exit_ts[train])={max_train_exit} > min(entry_ts[val])={min_val_entry}"
        )
    if max_train_exit + purge_sec > min_val_entry:
        obs_days = (min_val_entry - max_train_exit) / float(_SECONDS_PER_DAY)
        raise CausalityViolationError(
            f"PURGE_GAP_BREACH: max(exit_ts[train]) + purge_days ({purge_d}d) > min(entry_ts[val]); "
            f"observed gap={obs_days:.3f}d < required purge={purge_d}d"
        )
    if max_train_exit + total_gap_sec > min_val_entry:
        obs_days = (min_val_entry - max_train_exit) / float(_SECONDS_PER_DAY)
        raise CausalityViolationError(
            f"EMBARGO_GAP_BREACH: max(exit_ts[train]) + purge+embargo ({purge_d + embargo_d}d) > min(entry_ts[val]); "
            f"observed gap={obs_days:.3f}d < required {purge_d + embargo_d}d"
        )

    return {
        "passed": True,
        "n_train": int(tr.size),
        "n_val": int(va.size),
        "max_train_entry_ts": max_train_entry,
        "max_train_exit_ts": max_train_exit,
        "min_val_entry_ts": min_val_entry,
        "max_val_exit_ts": max_val_exit,
        "purge_days": purge_d,
        "embargo_days": embargo_d,
        "observed_gap_days": (min_val_entry - max_train_exit) / float(_SECONDS_PER_DAY),
        "holdout_rows_analysed": 0,
    }


class ExpandingPurgedWalkForwardSplitter:
    """Strictly chronological Expanding/Rolling Purged + Embargo Walk-Forward CV splitter.

    Guarantees for EVERY yielded `(train_idx, val_idx)`:
      1. Zero index overlap (`train_idx ∩ val_idx = ∅`).
      2. Strictly forward time (`max(entry_ts[train]) < min(entry_ts[val])`; zero reverse-time leakage).
      3. Strict purge + embargo clearance on trade EXIT times:
         `max(exit_ts[train]) + (purge_days + embargo_days) * 86400 <= min(entry_ts[val])`,
         which strictly satisfies `max(exit_ts[train]) + purge_days * 86400 <= min(entry_ts[val])`.
      4. Sealed Holdout `2025+` (`max(entry_ts, exit_ts) < 2025-01-01T00:00:00Z`).
      5. Non-overlapping, strictly increasing validation folds.
    """

    def __init__(
        self,
        n_splits: int = 5,
        purge_days: int = DEFAULT_PURGE_DAYS,
        embargo_days: int = DEFAULT_EMBARGO_DAYS,
        min_train_samples: int = DEFAULT_MIN_TRAIN_SAMPLES,
        *,
        mode: str = "expanding",
        rolling_window_days: int | None = None,
        cutoff_utc: str | date | datetime | int = HOLDOUT_CUTOFF_DATE,
    ) -> None:
        self.n_splits = _validate_int_param(n_splits, name="n_splits", minimum=1)
        self.purge_days = _validate_int_param(purge_days, name="purge_days", minimum=MIN_PURGE_DAYS)
        self.embargo_days = _validate_int_param(embargo_days, name="embargo_days", minimum=MIN_EMBARGO_DAYS)
        self.min_train_samples = _validate_int_param(min_train_samples, name="min_train_samples", minimum=1)
        if mode not in ("expanding", "rolling"):
            raise ValueError(f"INVALID_SPLITTER_MODE: expected 'expanding' or 'rolling', got {mode!r}")
        self.mode = mode
        if mode == "rolling":
            if rolling_window_days is None:
                raise ValueError("rolling_window_days is required when mode='rolling'")
            self.rolling_window_days: int | None = _validate_int_param(
                rolling_window_days, name="rolling_window_days", minimum=30
            )
        else:
            if rolling_window_days is not None:
                self.rolling_window_days = _validate_int_param(
                    rolling_window_days, name="rolling_window_days", minimum=30
                )
            else:
                self.rolling_window_days = None
        self.cutoff_utc = cutoff_utc
        self.cutoff_sec_exclusive = _enforce_cutoff_exclusive(cutoff_utc)
        self.last_fold_audits: list[FoldAuditMetadata] = []

    def get_n_splits(self) -> int:
        return self.n_splits

    def split(
        self,
        entry_ts: Any,
        exit_ts: Any | None = None,
        *,
        cutoff_utc: str | date | datetime | int | None = None,
    ) -> Iterator[tuple[np.ndarray, np.ndarray]]:
        """Yield strictly causal `(train_idx, val_idx)` pairs sorted chronologically."""
        eff_cutoff_utc = self.cutoff_utc if cutoff_utc is None else cutoff_utc
        cutoff_sec = _enforce_cutoff_exclusive(eff_cutoff_utc)

        ent = _parse_timestamp_array(entry_ts, name="entry_ts")
        ex = ent.copy() if exit_ts is None else _parse_timestamp_array(exit_ts, name="exit_ts")
        n = int(ent.size)
        if ex.shape != ent.shape:
            raise ValueError(f"TIMESTAMP_LENGTH_MISMATCH: entry_ts ({n}) vs exit_ts ({ex.size})")
        if n == 0:
            raise ValueError("INSUFFICIENT_SAMPLES_FOR_WALKFORWARD: empty timestamp sequence")
        if int(np.max(ent)) >= cutoff_sec or int(np.max(ex)) >= cutoff_sec:
            raise HoldoutCutoffBreachError(
                f"HOLDOUT_TIMESTAMP_BREACH: timestamps extend to/past cutoff_sec_exclusive={cutoff_sec}"
            )
        if bool(np.any(ex < ent)):
            bad_i = int(np.flatnonzero(ex < ent)[0])
            raise CausalityViolationError(
                f"INVALID_TRADE_INTERVAL: exit_ts[{bad_i}]={int(ex[bad_i])} < entry_ts[{bad_i}]={int(ent[bad_i])}"
            )
        if n <= self.min_train_samples:
            raise ValueError(
                f"INSUFFICIENT_SAMPLES_FOR_WALKFORWARD: n={n} <= min_train_samples={self.min_train_samples}"
            )

        purge_sec = self.purge_days * _SECONDS_PER_DAY
        embargo_sec = self.embargo_days * _SECONDS_PER_DAY
        total_gap_sec = purge_sec + embargo_sec

        # Chronological ordering by (entry_ts, original_index)
        order = np.argsort(ent, kind="mergesort")
        ent_sorted = ent[order]

        # Earliest validation start timestamp that guarantees >= min_train_samples closed before gap
        ex_sorted = np.sort(ex)
        earliest_val_ts = int(ex_sorted[self.min_train_samples - 1]) + total_gap_sec
        if self.mode == "rolling" and self.rolling_window_days is not None:
            # Ensure at least one eligible validation block has >= min_train_samples inside rolling window
            win_sec = self.rolling_window_days * _SECONDS_PER_DAY
            eligible_start_pos = int(np.searchsorted(ent_sorted, earliest_val_ts, side="left"))
            while eligible_start_pos < n:
                cand_t = int(ent_sorted[eligible_start_pos])
                lo_t = cand_t - total_gap_sec - win_sec
                tr_cnt = int(np.sum((ex + total_gap_sec <= cand_t) & (ent >= lo_t)))
                if tr_cnt >= self.min_train_samples:
                    break
                eligible_start_pos += 1
        else:
            eligible_start_pos = int(np.searchsorted(ent_sorted, earliest_val_ts, side="left"))

        if eligible_start_pos >= n:
            raise ValueError(
                f"INSUFFICIENT_SAMPLES_FOR_WALKFORWARD: no validation observations exist after "
                f"min_train_samples={self.min_train_samples} + purge={self.purge_days}d + embargo={self.embargo_days}d"
            )

        # Group validation candidates by unique entry_ts so simultaneous entries never split across folds
        val_pool_order = order[eligible_start_pos:]
        val_pool_ts = ent[val_pool_order]
        uniq_ts, group_starts = np.unique(val_pool_ts, return_index=True)
        n_groups = int(uniq_ts.size)
        if n_groups < self.n_splits:
            raise ValueError(
                f"INSUFFICIENT_UNIQUE_TIMESTAMPS_FOR_SPLITS: only {n_groups} unique validation timestamps "
                f"available for n_splits={self.n_splits}"
            )

        # Partition validation pool into `n_splits` balanced contiguous timestamp-aligned blocks
        pool_len = int(val_pool_order.size)
        group_ends = np.append(group_starts[1:], pool_len)
        fold_ranges: list[tuple[int, int]] = []
        g_cursor = 0
        for fold_i in range(self.n_splits):
            rem_folds = self.n_splits - fold_i
            if rem_folds == 1:
                g_next = n_groups
            else:
                target_end_idx = int(round((fold_i + 1) * pool_len / float(self.n_splits)))
                # Choose group boundary closest to target_end_idx while leaving >= rem_folds - 1 groups
                max_g = n_groups - (rem_folds - 1)
                g_cand = int(np.searchsorted(group_ends, target_end_idx, side="left")) + 1
                g_next = max(g_cursor + 1, min(max_g, g_cand))
            fold_ranges.append((int(group_starts[g_cursor]), int(group_ends[g_next - 1])))
            g_cursor = g_next

        audits: list[FoldAuditMetadata] = []
        prev_val_max_entry: int | None = None

        for fold_i, (lo_pos, hi_pos) in enumerate(fold_ranges):
            val_idx = np.ascontiguousarray(val_pool_order[lo_pos:hi_pos], dtype=np.int64)
            val_start_ts = int(np.min(ent[val_idx]))
            val_max_entry = int(np.max(ent[val_idx]))
            if prev_val_max_entry is not None and val_start_ts <= prev_val_max_entry:
                raise CausalityViolationError(
                    f"NON_MONOTONIC_VAL_FOLDS: fold {fold_i} starts at {val_start_ts} <= prev max {prev_val_max_entry}"
                )
            prev_val_max_entry = val_max_entry

            # Strictly causal train selection: ALL trade exits MUST precede val_start_ts by purge+embargo
            eligible_train_mask = (ex + total_gap_sec <= val_start_ts) & (ent + total_gap_sec <= val_start_ts)
            if self.mode == "rolling" and self.rolling_window_days is not None:
                win_sec = self.rolling_window_days * _SECONDS_PER_DAY
                eligible_train_mask = eligible_train_mask & (ent >= val_start_ts - total_gap_sec - win_sec)

            # Audit exact counts of purged (overlap/within purge) and embargoed trades
            pre_val_mask = ent < val_start_ts
            purged_mask = pre_val_mask & (ex + purge_sec > val_start_ts)
            embargoed_mask = pre_val_mask & (ex + purge_sec <= val_start_ts) & (ex + total_gap_sec > val_start_ts)

            train_unsorted = np.flatnonzero(eligible_train_mask)
            if int(train_unsorted.size) < self.min_train_samples:
                raise ValueError(
                    f"INSUFFICIENT_TRAIN_SAMPLES_IN_FOLD [{fold_i}]: "
                    f"got {int(train_unsorted.size)} < min_train_samples={self.min_train_samples}"
                )
            train_order = np.argsort(ent[train_unsorted], kind="mergesort")
            train_idx = np.ascontiguousarray(train_unsorted[train_order], dtype=np.int64)

            # Mandatory fail-closed causality verification on every single fold!
            check = verify_fold_causality(
                train_idx,
                val_idx,
                ent,
                ex,
                purge_days=self.purge_days,
                embargo_days=self.embargo_days,
                cutoff_utc=eff_cutoff_utc,
            )

            audits.append(
                FoldAuditMetadata(
                    fold_index=fold_i,
                    n_train=int(train_idx.size),
                    n_val=int(val_idx.size),
                    n_purged=int(np.sum(purged_mask)),
                    n_embargoed=int(np.sum(embargoed_mask)),
                    train_entry_min_ts=int(np.min(ent[train_idx])),
                    train_exit_max_ts=int(check["max_train_exit_ts"]),
                    val_entry_min_ts=int(check["min_val_entry_ts"]),
                    val_exit_max_ts=int(check["max_val_exit_ts"]),
                    observed_gap_days=float(check["observed_gap_days"]),
                )
            )
            self.last_fold_audits = list(audits)
            yield train_idx, val_idx


# ---------------------------------------------------------------------------
# 2. Purely Train-Fold Feature Pruning (`8..12` Interpretable Features)
# ---------------------------------------------------------------------------


def _fit_l1_logistic_weights_numpy(
    xs: np.ndarray,
    y: np.ndarray,
    *,
    l1_lambda: float,
    l2_lambda: float = 1e-3,
    max_iter: int = 160,
    tol: float = 1e-7,
) -> np.ndarray:
    """Pure-NumPy FISTA solver for L1+L2 regularized logistic regression (zero external ML deps)."""
    n, d = xs.shape
    if n == 0 or d == 0:
        return np.zeros(d, dtype=np.float64)

    base_p = float(np.clip(np.mean(y), 1e-4, 1.0 - 1e-4))
    b = math.log(base_p / (1.0 - base_p))
    w = np.zeros(d, dtype=np.float64)
    w_prev = w.copy()
    b_prev = b

    # Safe upper bound on smooth gradient Lipschitz constant: (1 / 4n) * ||X||_F^2 + l2 + 1/4
    frob_sq = float(np.sum(xs * xs))
    lip = max(0.25 * (frob_sq / max(1, n)) + l2_lambda + 0.25, 1.0)
    step = 1.0 / lip
    thresh = step * l1_lambda

    t_k = 1.0
    for _ in range(max_iter):
        beta = (t_k - 1.0) / (t_k + 2.0)
        w_y = w + beta * (w - w_prev)
        b_y = b + beta * (b - b_prev)

        logits = xs @ w_y + b_y
        p = _sigmoid(logits)
        diff = (p - y) / float(n)
        grad_w = xs.T @ diff + l2_lambda * w_y
        grad_b = float(np.sum(diff))

        u_w = w_y - step * grad_w
        # Soft-thresholding proximal operator for L1 norm
        w_new = np.sign(u_w) * np.maximum(np.abs(u_w) - thresh, 0.0)
        b_new = b_y - step * grad_b

        delta = float(np.max(np.abs(w_new - w))) if d > 0 else 0.0
        w_prev, b_prev = w, b
        w, b = w_new, b_new
        t_k += 1.0
        if delta < tol:
            break

    return np.abs(w)


def _compute_quantile_mutual_information(x_col: np.ndarray, y: np.ndarray, max_bins: int = 10) -> float:
    """Deterministic train-fold Miller-Madow bias-corrected Mutual Information I(X_j; Y) in pure NumPy."""
    n = int(y.size)
    if n < 4:
        return 0.0
    uniq = np.unique(x_col)
    if uniq.size <= 1:
        return 0.0

    if uniq.size <= max_bins:
        bin_idx = np.searchsorted(uniq, x_col)
        n_bins = int(uniq.size)
    else:
        qs = np.linspace(0.0, 1.0, max_bins + 1)[1:-1]
        edges = np.unique(np.quantile(x_col, qs))
        if edges.size == 0:
            return 0.0
        bin_idx = np.digitize(x_col, edges, right=False)
        n_bins = int(edges.size) + 1

    y_int = (y >= 0.5).astype(np.int64)
    p_y1 = float(np.mean(y_int))
    p_y0 = 1.0 - p_y1
    if p_y1 <= _EPS or p_y0 <= _EPS:
        return 0.0

    mi = 0.0
    non_empty_bins = 0
    for b_id in range(n_bins):
        mask = bin_idx == b_id
        c_b = int(np.sum(mask))
        if c_b == 0:
            continue
        non_empty_bins += 1
        c_b1 = int(np.sum(y_int[mask]))
        c_b0 = c_b - c_b1
        p_b = c_b / float(n)
        if c_b1 > 0:
            p_b1 = c_b1 / float(n)
            mi += p_b1 * math.log(p_b1 / (p_b * p_y1))
        if c_b0 > 0:
            p_b0 = c_b0 / float(n)
            mi += p_b0 * math.log(p_b0 / (p_b * p_y0))

    # Miller-Madow finite-sample bias correction prevents high-cardinality noise from winning
    bias_corr = max(0, non_empty_bins - 1) / float(2 * n)
    return float(max(0.0, mi - bias_corr))


def select_inside_fold_features(
    X_train: np.ndarray,
    y_train: np.ndarray,
    feature_names: Sequence[str] | None = None,
    min_k: int = DEFAULT_MIN_SELECTED_FEATURES,
    max_k: int = DEFAULT_MAX_SELECTED_FEATURES,
    *,
    corr_threshold: float = 0.85,
    l1_weight: float = 0.50,
    mi_weight: float = 0.50,
) -> dict[str, Any]:
    """Strictly train-fold L1 + Mutual Information + Collinearity feature pruning returning `min_k..max_k` features.

    Zero external ML dependencies (pure NumPy) so it runs identically in full env and minimal CI.
    Never touches any validation data.
    """
    x = _validate_feature_matrix(X_train, name="X_train")
    y = _validate_binary_targets(y_train, name="y_train")
    n_samples, n_features = x.shape
    if y.size != n_samples:
        raise ValueError(f"LENGTH_MISMATCH: X_train has {n_samples} rows but y_train has {y.size}")
    if n_samples < 10:
        raise ValueError(f"INSUFFICIENT_TRAIN_SAMPLES: need >= 10 rows for feature pruning, got {n_samples}")
    if len(np.unique(y)) < 2:
        raise ValueError("SINGLE_CLASS_TRAIN_FOLD: y_train must contain both 0 and 1 classes")

    k_min = _validate_int_param(min_k, name="min_k", minimum=1)
    k_max = _validate_int_param(max_k, name="max_k", minimum=k_min)
    if n_features < k_min:
        raise ValueError(f"INSUFFICIENT_FEATURES: n_features={n_features} < min_k={k_min}")
    k_max_eff = min(k_max, n_features)

    corr_thr = _validate_finite_float(corr_threshold, name="corr_threshold")
    if not (0.0 < corr_thr <= 1.0):
        raise ValueError(f"INVALID_CORR_THRESHOLD: expected (0, 1], got {corr_thr}")
    w_l1 = _validate_finite_float(l1_weight, name="l1_weight")
    w_mi = _validate_finite_float(mi_weight, name="mi_weight")
    if w_l1 < 0.0 or w_mi < 0.0 or (w_l1 + w_mi) <= _EPS:
        raise ValueError("l1_weight and mi_weight must be >= 0 with positive sum")
    w_sum = w_l1 + w_mi
    w_l1 /= w_sum
    w_mi /= w_sum

    names = _validate_feature_names(feature_names, n_features)

    # Identify constant/near-constant features strictly on train fold
    mu = np.mean(x, axis=0)
    sd = np.std(x, axis=0, ddof=0)
    non_const_mask = sd > 1e-10
    dropped_constant = [names[j] for j in range(n_features) if not bool(non_const_mask[j])]

    sd_safe = np.where(non_const_mask, sd, 1.0)
    xs = (x - mu) / sd_safe
    xs[:, ~non_const_mask] = 0.0

    # 1. Multi-strength L1 logistic stability score strictly on X_train, y_train
    l1_raw = np.zeros(n_features, dtype=np.float64)
    for lam in (0.004, 0.012, 0.030):
        w_abs = _fit_l1_logistic_weights_numpy(xs, y, l1_lambda=lam, l2_lambda=1e-3)
        w_max = float(np.max(w_abs)) if w_abs.size else 0.0
        if w_max > _EPS:
            l1_raw += w_abs / w_max
    l1_scores = l1_raw / 3.0
    l1_scores[~non_const_mask] = 0.0

    # 2. Quantile Mutual Information I(X_j; Y) strictly on X_train, y_train
    mi_raw = np.zeros(n_features, dtype=np.float64)
    for j in range(n_features):
        if bool(non_const_mask[j]):
            mi_raw[j] = _compute_quantile_mutual_information(x[:, j], y, max_bins=10)
    mi_max = float(np.max(mi_raw)) if mi_raw.size else 0.0
    mi_scores = (mi_raw / mi_max) if mi_max > _EPS else np.zeros(n_features, dtype=np.float64)

    # 3. Deterministic tie-breaker: absolute point-biserial correlation with y_train
    y_centered = y - float(np.mean(y))
    y_norm = float(np.linalg.norm(y_centered))
    abs_target_corr = np.zeros(n_features, dtype=np.float64)
    if y_norm > _EPS:
        for j in range(n_features):
            if bool(non_const_mask[j]):
                col_c = xs[:, j]
                c_norm = float(np.linalg.norm(col_c))
                if c_norm > _EPS:
                    abs_target_corr[j] = abs(float(np.dot(col_c, y_centered)) / (c_norm * y_norm))

    combined = w_l1 * l1_scores + w_mi * mi_scores + 1e-4 * abs_target_corr
    combined[~non_const_mask] = -1.0

    # 4. Pairwise absolute correlation matrix strictly on X_train
    corr_mat = np.zeros((n_features, n_features), dtype=np.float64)
    if n_samples > 1:
        cov = (xs.T @ xs) / float(n_samples)
        corr_mat = np.clip(np.abs(cov), 0.0, 1.0)
        np.fill_diagonal(corr_mat, 1.0)

    # Sort indices descending by combined score, deterministic tie-break by feature index
    ranked = sorted(range(n_features), key=lambda j: (-float(combined[j]), j))

    # 5. Greedy collinearity pruning + adaptive relevance cutoff clamped strictly to [k_min, k_max_eff]
    top_score = max(float(combined[ranked[0]]), 0.0)
    rel_floor = 0.15 * top_score
    selected: list[int] = []
    dropped_correlated: list[dict[str, Any]] = []
    deferred_low_rel: list[int] = []

    for j in ranked:
        if not bool(non_const_mask[j]):
            continue
        max_c = 0.0
        conflict_idx = -1
        for s in selected:
            c_val = float(corr_mat[j, s])
            if c_val > max_c:
                max_c = c_val
                conflict_idx = s
        if selected and max_c >= corr_thr:
            dropped_correlated.append(
                {
                    "dropped": names[j],
                    "kept": names[conflict_idx],
                    "abs_corr": round(max_c, 6),
                }
            )
            continue
        if len(selected) < k_max_eff and (len(selected) < k_min or float(combined[j]) >= rel_floor):
            selected.append(j)
        else:
            deferred_low_rel.append(j)

    # Guarantee at least k_min features (backfill least-correlated remaining features if collinearity was extreme)
    if len(selected) < k_min:
        remaining = [j for j in ranked if j not in selected]
        remaining.sort(
            key=lambda j: (
                0 if bool(non_const_mask[j]) else 1,
                max((float(corr_mat[j, s]) for s in selected), default=0.0),
                -float(combined[j]),
                j,
            )
        )
        for j in remaining:
            if len(selected) >= k_min:
                break
            selected.append(j)

    # Strictly clamp to [k_min, k_max_eff] and preserve deterministic canonical feature order?
    # Keep ranked order in `selected_ranked_indices` and canonical order in `selected_indices` for stable indexing!
    selected_ranked = list(selected[:k_max_eff])
    selected_sorted = sorted(selected_ranked)

    return {
        "selected_indices": selected_sorted,
        "selected_ranked_indices": selected_ranked,
        "selected_names": [names[j] for j in selected_sorted],
        "selected_ranked_names": [names[j] for j in selected_ranked],
        "k": len(selected_sorted),
        "min_k": k_min,
        "max_k": k_max_eff,
        "corr_threshold": corr_thr,
        "l1_scores": {names[j]: round(float(l1_scores[j]), 6) for j in range(n_features)},
        "mi_scores": {names[j]: round(float(mi_raw[j]), 6) for j in range(n_features)},
        "combined_scores": {names[j]: round(float(max(0.0, combined[j])), 6) for j in range(n_features)},
        "dropped_correlated": dropped_correlated,
        "dropped_constant": dropped_constant,
    }


# ---------------------------------------------------------------------------
# 3. OOF Brier Skill > 0 Gate, Engine Balance Guard & 24m Slippage Economics
# ---------------------------------------------------------------------------


def _compute_trade_economics(
    net_r_adj: np.ndarray,
    sizes: np.ndarray,
    risk_fracs: np.ndarray,
) -> dict[str, Any]:
    """Compute PF, EV/trade (R), win rate, total R, equity return %, and peak-to-trough Max DD %."""
    active_mask = sizes > 0.0
    n_total = int(net_r_adj.size)
    n_active = int(np.sum(active_mask))
    if n_active == 0:
        return {
            "n_total": n_total,
            "n_active": 0,
            "avg_size": 0.0,
            "win_rate": 0.0,
            "ev_r": 0.0,
            "total_r": 0.0,
            "profit_factor": 0.0,
            "max_dd_pct": 0.0,
            "total_return_pct": 0.0,
            "trade_sharpe": 0.0,
        }

    weighted_r = sizes * net_r_adj
    act_r = weighted_r[active_mask]
    act_raw_r = net_r_adj[active_mask]
    gross_win = float(np.sum(act_r[act_r > 0.0]))
    gross_loss = float(np.abs(np.sum(act_r[act_r < 0.0])))
    if gross_loss > _EPS:
        pf = gross_win / gross_loss
    elif gross_win > _EPS:
        pf = 999.0
    else:
        pf = 0.0

    # Compounded equity path for Max DD %
    trade_ret = weighted_r * risk_fracs
    eq = 1.0
    peak = 1.0
    max_dd = 0.0
    for r in trade_ret:
        eq = max(1e-6, eq * (1.0 + float(r)))
        if eq > peak:
            peak = eq
        dd = (peak - eq) / max(peak, _EPS)
        if dd > max_dd:
            max_dd = dd

    mean_act_r = float(np.mean(act_r))
    std_act_r = float(np.std(act_r, ddof=1)) if n_active > 1 else 0.0
    trade_sharpe = (mean_act_r / std_act_r) if std_act_r > _EPS else 0.0

    return {
        "n_total": n_total,
        "n_active": n_active,
        "avg_size": float(np.mean(sizes)),
        "win_rate": float(np.mean(act_raw_r > 0.0)),
        "ev_r": mean_act_r,
        "total_r": float(np.sum(act_r)),
        "profit_factor": float(pf),
        "max_dd_pct": float(100.0 * max_dd),
        "total_return_pct": float(100.0 * (eq - 1.0)),
        "trade_sharpe": float(trade_sharpe),
    }


def _compute_rolling_24m_breakeven(
    net_r: np.ndarray,
    sizes: np.ndarray,
    base_cost_r: np.ndarray,
    entry_ts: np.ndarray | None,
) -> dict[str, Any]:
    """Compute exact 24-month rolling median slippage breakeven multiplier.

    At slippage multiplier `m`, trade `i` realizes `net_r[i] - (m - 1.0) * base_cost_r[i]`.
    For window `W`, breakeven multiplier `m*_W = 1.0 + sum(s_i * net_r_i) / sum(s_i * base_cost_r_i)`.
    """
    n = int(net_r.size)
    if n == 0:
        return {"n_windows": 0, "median_breakeven_mult": 0.0, "window_breakevens": []}

    windows: list[np.ndarray] = []
    if entry_ts is not None and n >= 2:
        order = np.argsort(entry_ts, kind="mergesort")
        ts_sorted = entry_ts[order]
        span_24m = 730 * _SECONDS_PER_DAY
        step_30d = 30 * _SECONDS_PER_DAY
        t_min = int(ts_sorted[0])
        t_max = int(ts_sorted[-1])
        if t_max - t_min >= span_24m:
            cur = t_min
            while cur + span_24m <= t_max:
                lo = int(np.searchsorted(ts_sorted, cur, side="left"))
                hi = int(np.searchsorted(ts_sorted, cur + span_24m, side="right"))
                if hi > lo:
                    windows.append(order[lo:hi])
                cur += step_30d
            # Include trailing 24m window ending at t_max
            lo_tail = int(np.searchsorted(ts_sorted, t_max - span_24m, side="left"))
            if n > lo_tail:
                windows.append(order[lo_tail:n])
        else:
            windows.append(order)
    else:
        # Deterministic rolling-block proxy when timestamps are omitted (offline synthetic eval)
        win_len = max(1, min(n, max(20, n // 2)))
        if win_len >= n:
            windows.append(np.arange(n, dtype=np.int64))
        else:
            step = max(1, (n - win_len) // 12)
            for start in range(0, n - win_len + 1, step):
                windows.append(np.arange(start, start + win_len, dtype=np.int64))
            if int(windows[-1][-1]) < n - 1:
                windows.append(np.arange(n - win_len, n, dtype=np.int64))

    be_vals: list[float] = []
    for w_idx in windows:
        s_w = sizes[w_idx]
        denom = float(np.sum(s_w * base_cost_r[w_idx]))
        numer = float(np.sum(s_w * net_r[w_idx]))
        if denom <= _EPS:
            be_vals.append(0.0)
        else:
            be_vals.append(1.0 + numer / denom)

    med_be = float(np.median(np.asarray(be_vals, dtype=np.float64))) if be_vals else 0.0
    return {
        "n_windows": len(be_vals),
        "median_breakeven_mult": med_be,
        "min_breakeven_mult": float(min(be_vals)) if be_vals else 0.0,
        "max_breakeven_mult": float(max(be_vals)) if be_vals else 0.0,
    }


def _broadcast_trade_param(
    raw: Any,
    n: int,
    *,
    name: str,
    positive: bool = False,
    non_negative: bool = False,
) -> np.ndarray:
    if isinstance(raw, (int, float, np.integer, np.floating)) and not isinstance(raw, (bool, np.bool_)):
        fv = _validate_finite_float(raw, name=name)
        if positive and fv <= 0.0:
            raise ValueError(f"NON_POSITIVE_INPUT [{name}]: {fv} <= 0.0")
        if non_negative and fv < 0.0:
            raise ValueError(f"NEGATIVE_INPUT [{name}]: {fv} < 0.0")
        return np.full(n, fv, dtype=np.float64)
    arr = _validate_float_array(raw, name=name, positive=positive, non_negative=non_negative)
    if arr.shape != (n,):
        raise ValueError(f"LENGTH_MISMATCH [{name}]: expected ({n},), got {arr.shape}")
    return arr


def evaluate_oof_brier_and_economics(
    y_true: np.ndarray | Sequence[float],
    y_prob: np.ndarray | Sequence[float],
    net_r: np.ndarray | Sequence[float],
    engine_ids: Sequence[Any] | np.ndarray,
    slippage_mults: Sequence[float] = DEFAULT_SLIPPAGE_MULTS,
    *,
    position_sizes: np.ndarray | Sequence[float] | None = None,
    base_cost_r: np.ndarray | Sequence[float] | float = DEFAULT_BASE_COST_R,
    risk_pct_per_trade: np.ndarray | Sequence[float] | float | None = None,
    filter_threshold: float | None = None,
    toxic_quantile: float = 0.20,
    min_engine_retention_ratio: float = DEFAULT_MIN_ENGINE_RETENTION,
    min_overall_retention_ratio: float = DEFAULT_MIN_OVERALL_RETENTION,
    min_brier_skill: float = 0.0,
    baseline_slippage_breakeven: float = DEFAULT_BASELINE_SLIPPAGE_BREAKEVEN,
    target_slippage_breakeven: float = DEFAULT_TARGET_SLIPPAGE_BREAKEVEN,
    oos_label: str = CONSUMED_CLB_TAG,
    entry_ts: Any | None = None,
    cutoff_utc: str | date | datetime | int = HOLDOUT_CUTOFF_DATE,
) -> dict[str, Any]:
    """Evaluate OOF Brier Skill > 0 gate, Engine Balance Guard, PF/EV/MaxDD, and 24m slippage breakeven.

    Returns verdict `PROMOTE_V104_ML` ONLY if ALL hard gates pass; otherwise `REJECT_ML_KEEP_V103`.
    """
    validated_label = validate_oos_label(oos_label)
    cutoff_sec = _enforce_cutoff_exclusive(cutoff_utc)

    y = _validate_binary_targets(y_true, name="y_true")
    p = _validate_float_array(y_prob, name="y_prob")
    r = _validate_float_array(net_r, name="net_r")
    n = int(y.size)
    if n == 0:
        raise ValueError("EMPTY_EVALUATION_SET: cannot evaluate zero OOF samples")
    if p.shape != (n,) or r.shape != (n,):
        raise ValueError(f"LENGTH_MISMATCH: y_true={y.shape}, y_prob={p.shape}, net_r={r.shape}")

    eng_list = [str(e).strip().upper() for e in engine_ids]
    if len(eng_list) != n or any(not e for e in eng_list):
        raise ValueError(f"INVALID_ENGINE_IDS: expected {n} non-empty engine identifiers")

    ts_arr: np.ndarray | None = None
    if entry_ts is not None:
        ts_arr = _parse_timestamp_array(entry_ts, name="entry_ts")
        if ts_arr.shape != (n,):
            raise ValueError(f"LENGTH_MISMATCH: entry_ts={ts_arr.shape} vs n={n}")
        if int(np.max(ts_arr)) >= cutoff_sec:
            raise HoldoutCutoffBreachError(
                f"HOLDOUT_TIMESTAMP_BREACH: OOF entry_ts contains {int(np.max(ts_arr))} >= {cutoff_sec}"
            )

    mults_arr = _validate_float_array(slippage_mults, name="slippage_mults", positive=True)
    if mults_arr.ndim != 1 or mults_arr.size == 0:
        raise ValueError("slippage_mults must be a non-empty 1D sequence of positive floats")
    mults_sorted = tuple(sorted({float(m) for m in mults_arr.tolist()}))

    cost_arr = _broadcast_trade_param(base_cost_r, n, name="base_cost_r", positive=True)
    if risk_pct_per_trade is None:
        risk_pct_arr = np.array(
            [DEFAULT_ENGINE_BASE_RISK_PCT.get(e, 0.50) for e in eng_list],
            dtype=np.float64,
        )
    else:
        risk_pct_arr = _broadcast_trade_param(risk_pct_per_trade, n, name="risk_pct_per_trade", positive=True)
    risk_fracs = risk_pct_arr / 100.0

    # Derive ML position sizes
    if position_sizes is not None:
        sizes = _validate_float_array(position_sizes, name="position_sizes", non_negative=True)
        if sizes.shape != (n,):
            raise ValueError(f"LENGTH_MISMATCH: position_sizes={sizes.shape} vs n={n}")
        sizing_policy = "explicit_position_sizes"
    elif filter_threshold is not None:
        thr = _validate_finite_float(filter_threshold, name="filter_threshold")
        sizes = np.where(p >= thr, 1.0, 0.0)
        sizing_policy = f"binary_threshold_{thr:.4f}"
    else:
        tq = _validate_finite_float(toxic_quantile, name="toxic_quantile")
        if not (0.0 <= tq < 1.0):
            raise ValueError(f"INVALID_TOXIC_QUANTILE: expected [0, 1), got {tq}")
        if float(np.ptp(p)) <= _EPS or tq == 0.0:
            sizes = np.ones(n, dtype=np.float64)
        else:
            q_thr = float(np.quantile(p, tq))
            sizes = np.where(p > q_thr, 1.0, 0.0)
            # If discrete ties caused 0 kept trades, keep all trades >= q_thr
            if int(np.sum(sizes > 0.0)) == 0:
                sizes = np.where(p >= q_thr, 1.0, 0.0)
        sizing_policy = f"toxic_tail_filter_q{int(round(tq * 100)):02d}"

    # 1. Probabilistic calibration metrics (MANDATORY Brier Skill > 0 gate)
    prob_metrics = compute_brier_metrics(y, p)
    brier_skill = float(prob_metrics["brier_skill_score"])
    roc_auc = float(prob_metrics["roc_auc"])
    min_bs = _validate_finite_float(min_brier_skill, name="min_brier_skill")
    brier_gate_passed = bool(brier_skill > min_bs)
    auc_gate_passed = bool(roc_auc > 0.50)

    # 2. Engine Balance Guard across ALL engines present (E1..E7)
    unique_engines = sorted(set(eng_list))
    per_engine_retention: dict[str, dict[str, Any]] = {}
    dropped_engines: list[str] = []
    min_eng_ret = 1.0
    for eng in unique_engines:
        e_mask = np.array([e == eng for e in eng_list], dtype=bool)
        raw_cnt = int(np.sum(e_mask))
        kept_cnt = int(np.sum(e_mask & (sizes > 0.0)))
        ret_ratio = (kept_cnt / float(raw_cnt)) if raw_cnt > 0 else 0.0
        min_eng_ret = min(min_eng_ret, ret_ratio)
        if kept_cnt == 0:
            dropped_engines.append(eng)
        per_engine_retention[eng] = {
            "raw_trades": raw_cnt,
            "kept_trades": kept_cnt,
            "retention_ratio": round(ret_ratio, 6),
            "avg_size": round(float(np.mean(sizes[e_mask])), 6),
        }

    overall_ret = float(np.mean(sizes > 0.0))
    min_eng_thr = _validate_finite_float(min_engine_retention_ratio, name="min_engine_retention_ratio")
    min_all_thr = _validate_finite_float(min_overall_retention_ratio, name="min_overall_retention_ratio")
    engine_balance_passed = (
        len(dropped_engines) == 0
        and min_eng_ret >= min_eng_thr - 1e-12
        and overall_ret >= min_all_thr - 1e-12
    )

    # 3. Slippage stress curve (Baseline 1.0x vs ML Overlay)
    raw_sizes = np.ones(n, dtype=np.float64)
    slippage_curve: dict[str, dict[str, Any]] = {}
    for mult in mults_sorted:
        adj_r = r - (mult - 1.0) * cost_arr
        raw_econ = _compute_trade_economics(adj_r, raw_sizes, risk_fracs)
        ml_econ = _compute_trade_economics(adj_r, sizes, risk_fracs)
        key = f"{mult:.2f}x"
        slippage_curve[key] = {
            "slippage_mult": mult,
            "baseline_v103": raw_econ,
            "ml_v104": ml_econ,
            "delta_pf": round(ml_econ["profit_factor"] - raw_econ["profit_factor"], 6),
            "delta_ev_r": round(ml_econ["ev_r"] - raw_econ["ev_r"], 6),
            "delta_max_dd_pct": round(ml_econ["max_dd_pct"] - raw_econ["max_dd_pct"], 6),
        }

    # 4. 24-month median slippage breakeven check (`1.50x -> >= 1.75x`)
    raw_24m = _compute_rolling_24m_breakeven(r, raw_sizes, cost_arr, ts_arr)
    ml_24m = _compute_rolling_24m_breakeven(r, sizes, cost_arr, ts_arr)
    target_be = _validate_finite_float(target_slippage_breakeven, name="target_slippage_breakeven")
    base_be_ref = _validate_finite_float(baseline_slippage_breakeven, name="baseline_slippage_breakeven")

    r_at_target = r - (target_be - 1.0) * cost_arr
    ml_econ_target = _compute_trade_economics(r_at_target, sizes, risk_fracs)
    raw_econ_1x = _compute_trade_economics(r, raw_sizes, risk_fracs)
    ml_econ_1x = _compute_trade_economics(r, sizes, risk_fracs)

    slippage_breakeven_passed = (
        ml_24m["median_breakeven_mult"] >= target_be
        and ml_econ_target["ev_r"] > 0.0
        and ml_24m["median_breakeven_mult"] >= raw_24m["median_breakeven_mult"]
    )
    economics_improved = (
        (ml_econ_1x["profit_factor"] > raw_econ_1x["profit_factor"] or ml_econ_1x["ev_r"] > raw_econ_1x["ev_r"])
        and ml_econ_1x["ev_r"] > 0.0
        and ml_econ_1x["max_dd_pct"] <= max(raw_econ_1x["max_dd_pct"] * 1.10, raw_econ_1x["max_dd_pct"] + 0.50)
    )

    rejection_reasons: list[str] = []
    if not brier_gate_passed:
        rejection_reasons.append(f"BRIER_SKILL_NON_POSITIVE ({brier_skill:.6f} <= {min_bs:.6f})")
    if not auc_gate_passed:
        rejection_reasons.append(f"ROC_AUC_NOT_ABOVE_CHANCE ({roc_auc:.6f} <= 0.500000)")
    if not engine_balance_passed:
        rejection_reasons.append(
            f"ENGINE_BALANCE_BREACH (dropped={dropped_engines}, "
            f"min_engine_retention={min_eng_ret:.3f}, overall_retention={overall_ret:.3f})"
        )
    if not slippage_breakeven_passed:
        rejection_reasons.append(
            f"SLIPPAGE_BREAKEVEN_24M_FAILED (ml_24m_be={ml_24m['median_breakeven_mult']:.3f}x, "
            f"raw_24m_be={raw_24m['median_breakeven_mult']:.3f}x, target>={target_be:.2f}x, "
            f"ml_ev_at_target={ml_econ_target['ev_r']:.6f})"
        )
    if not economics_improved:
        rejection_reasons.append(
            f"ECONOMICS_NOT_IMPROVED_AT_1X (ml_pf={ml_econ_1x['profit_factor']:.3f} vs "
            f"raw_pf={raw_econ_1x['profit_factor']:.3f}, ml_dd={ml_econ_1x['max_dd_pct']:.2f}% vs "
            f"raw_dd={raw_econ_1x['max_dd_pct']:.2f}%)"
        )

    verdict = VERDICT_PROMOTE if not rejection_reasons else VERDICT_REJECT

    return {
        "schema_version": SCHEMA_VERSION,
        "oos_label": validated_label,
        "holdout_cutoff_date": HOLDOUT_CUTOFF_DATE,
        "holdout_rows_analysed": 0,
        "order_send_count": ORDER_SEND_COUNT,
        "sizing_policy": sizing_policy,
        "n_trades": n,
        "probabilistic_metrics": prob_metrics,
        "brier_skill_score": brier_skill,
        "roc_auc": roc_auc,
        "engine_balance": {
            "n_engines": len(unique_engines),
            "per_engine_retention": per_engine_retention,
            "min_engine_retention_ratio": round(min_eng_ret, 6),
            "overall_retention_ratio": round(overall_ret, 6),
            "dropped_engines": dropped_engines,
            "passed": engine_balance_passed,
        },
        "economics_1x": {
            "baseline_v103": raw_econ_1x,
            "ml_v104": ml_econ_1x,
        },
        "slippage_stress_curve": slippage_curve,
        "slippage_breakeven_24m": {
            "baseline_reference_mult": base_be_ref,
            "target_min_mult": target_be,
            "baseline_v103_median_mult": round(raw_24m["median_breakeven_mult"], 6),
            "ml_v104_median_mult": round(ml_24m["median_breakeven_mult"], 6),
            "delta_median_mult": round(ml_24m["median_breakeven_mult"] - raw_24m["median_breakeven_mult"], 6),
            "n_windows": ml_24m["n_windows"],
            "ml_ev_r_at_target": round(ml_econ_target["ev_r"], 6),
            "passed": slippage_breakeven_passed,
        },
        "gates": {
            "brier_skill_positive": brier_gate_passed,
            "roc_auc_above_050": auc_gate_passed,
            "engine_balance_guard": engine_balance_passed,
            "slippage_breakeven_24m_ge_target": slippage_breakeven_passed,
            "economics_improved_1x": economics_improved,
        },
        "rejection_reasons": rejection_reasons,
        "verdict": verdict,
    }


# ---------------------------------------------------------------------------
# 4. DuckDB `wave4_ml_m48` Experiment Budget Ledger (<= 48 Trials Fail-Closed)
# ---------------------------------------------------------------------------


_WAVE4_ML_M48_SCHEMA_SQL = f"""
CREATE TABLE IF NOT EXISTS {DEFAULT_TABLE_NAME} (
    trial_seq INTEGER NOT NULL,
    trial_id VARCHAR PRIMARY KEY,
    family_name VARCHAR NOT NULL,
    config_hash VARCHAR NOT NULL,
    oos_label VARCHAR NOT NULL,
    cutoff_utc VARCHAR NOT NULL,
    n_folds INTEGER NOT NULL,
    n_features_selected INTEGER NOT NULL,
    brier_model DOUBLE NOT NULL,
    brier_climatology DOUBLE NOT NULL,
    brier_skill_score DOUBLE NOT NULL,
    roc_auc DOUBLE NOT NULL,
    min_engine_retention DOUBLE NOT NULL,
    overall_retention DOUBLE NOT NULL,
    slippage_breakeven_24m DOUBLE NOT NULL,
    pf_1x DOUBLE NOT NULL,
    ev_r_1x DOUBLE NOT NULL,
    max_dd_pct_1x DOUBLE NOT NULL,
    verdict VARCHAR NOT NULL,
    holdout_rows_analysed INTEGER NOT NULL,
    order_send_count INTEGER NOT NULL,
    params_json VARCHAR NOT NULL,
    metrics_json VARCHAR NOT NULL,
    created_utc VARCHAR NOT NULL
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


def _canonical_json_hash(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class Wave4MlBudgetLedger:
    """Fail-closed DuckDB Experiment Budget Ledger (`wave4_ml_m48`, max `48` total trials).

    Lazy-imports `duckdb` on initialization so importing `ml_walkforward_cv` never eagerly loads DB wheels.
    Refuses the 49th trial (`trial_count >= max_trials`) with `BudgetExceededError`.
    """

    def __init__(
        self,
        db_path: str | Path = DEFAULT_ML_BUDGET_DB_PATH,
        max_trials: int = DEFAULT_MAX_ML_TRIALS,
        *,
        cutoff_utc: str | date | datetime | int = HOLDOUT_CUTOFF_DATE,
    ) -> None:
        self.max_trials = _validate_int_param(
            max_trials, name="max_trials", minimum=1, maximum=DEFAULT_MAX_ML_TRIALS
        )
        self.cutoff_utc = str(cutoff_utc)
        self.cutoff_sec_exclusive = _enforce_cutoff_exclusive(cutoff_utc)
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._con_box: list[Any] = [None]
        self._finalizer = weakref.finalize(self, _close_duckdb_box, self._con_box)
        with self._connect() as con:
            con.execute(_WAVE4_ML_M48_SCHEMA_SQL)

    @contextmanager
    def _connect(self) -> Iterator[Any]:
        import duckdb  # Lazy import ONLY

        with self._lock:
            con = self._con_box[0]
            if con is None:
                con = duckdb.connect(str(self.db_path))
                self._con_box[0] = con
            yield con

    def close(self) -> None:
        with self._lock:
            _close_duckdb_box(self._con_box)

    def __enter__(self) -> Wave4MlBudgetLedger:
        return self

    def __exit__(self, _exc_type: Any, _exc: Any, _tb: Any) -> None:
        self.close()

    def get_trial_count(self) -> int:
        with self._connect() as con:
            row = con.execute(f"SELECT COUNT(*) FROM {DEFAULT_TABLE_NAME}").fetchone()
            return int(row[0]) if row is not None else 0

    def remaining_budget(self) -> int:
        return max(0, self.max_trials - self.get_trial_count())

    def record_trial(
        self,
        *,
        trial_id: str,
        family_name: str,
        params: Mapping[str, Any],
        evaluation: Mapping[str, Any],
        n_folds: int,
        n_features_selected: int,
        oos_label: str = CONSUMED_CLB_TAG,
        cutoff_utc: str | date | datetime | int | None = None,
        created_utc: str | None = None,
    ) -> dict[str, Any]:
        """Atomically record one ML trial and fail closed if `trial_count >= max_trials` (49th raises)."""
        if not isinstance(trial_id, str) or not trial_id.strip():
            raise ValueError("trial_id must be a non-empty string")
        tid = trial_id.strip()
        if not isinstance(family_name, str) or family_name not in MODEL_FAMILIES:
            raise ValueError(f"INVALID_MODEL_FAMILY: {family_name!r} not in {MODEL_FAMILIES}")
        eff_cutoff = self.cutoff_utc if cutoff_utc is None else cutoff_utc
        _enforce_cutoff_exclusive(eff_cutoff)
        validated_oos = validate_oos_label(oos_label)

        n_f = _validate_int_param(n_folds, name="n_folds", minimum=1)
        n_feat = _validate_int_param(n_features_selected, name="n_features_selected", minimum=1)

        if int(evaluation.get("holdout_rows_analysed", 0)) != 0:
            raise HoldoutCutoffBreachError("HOLDOUT_CONTAMINATION: holdout_rows_analysed must be 0")
        if int(evaluation.get("order_send_count", 0)) != 0:
            raise ValueError("ORDER_SEND_VIOLATION: order_send_count must be 0")

        prob = evaluation.get("probabilistic_metrics", {})
        brier_model = _validate_finite_float(prob.get("brier_model", 0.25), name="brier_model")
        brier_clim = _validate_finite_float(prob.get("brier_climatology", 0.25), name="brier_climatology")
        brier_skill = _validate_finite_float(
            evaluation.get("brier_skill_score", prob.get("brier_skill_score", 0.0)),
            name="brier_skill_score",
        )
        roc_auc = _validate_finite_float(evaluation.get("roc_auc", prob.get("roc_auc", 0.5)), name="roc_auc")

        eb = evaluation.get("engine_balance", {})
        min_eng_ret = _validate_finite_float(eb.get("min_engine_retention_ratio", 0.0), name="min_engine_retention")
        overall_ret = _validate_finite_float(eb.get("overall_retention_ratio", 0.0), name="overall_retention")

        sb = evaluation.get("slippage_breakeven_24m", {})
        slip_be = _validate_finite_float(sb.get("ml_v104_median_mult", 0.0), name="slippage_breakeven_24m")

        e1x = evaluation.get("economics_1x", {}).get("ml_v104", {})
        pf_1x = _validate_finite_float(e1x.get("profit_factor", 0.0), name="pf_1x")
        ev_r_1x = _validate_finite_float(e1x.get("ev_r", 0.0), name="ev_r_1x")
        dd_1x = _validate_finite_float(e1x.get("max_dd_pct", 0.0), name="max_dd_pct_1x")

        verdict = str(evaluation.get("verdict", VERDICT_REJECT))
        if verdict not in (VERDICT_PROMOTE, VERDICT_REJECT):
            raise ValueError(f"INVALID_VERDICT: {verdict!r}")
        # Hard belt-and-suspenders guard: NEVER permit PROMOTE_V104_ML with Brier Skill <= 0
        if verdict == VERDICT_PROMOTE and brier_skill <= 0.0:
            raise ValueError(
                f"BRIER_SKILL_GATE_BREACH: cannot record {VERDICT_PROMOTE} with brier_skill_score={brier_skill}"
            )

        params_dict = dict(params)
        cfg_hash = _canonical_json_hash({"family_name": family_name, "params": params_dict})
        params_json = json.dumps(params_dict, sort_keys=True, ensure_ascii=False)
        metrics_json = json.dumps(dict(evaluation), sort_keys=True, ensure_ascii=False)
        ts_utc = created_utc or datetime.now(UTC).isoformat()

        with self._connect() as con:
            con.execute("BEGIN TRANSACTION")
            try:
                existing = con.execute(
                    f"SELECT 1 FROM {DEFAULT_TABLE_NAME} WHERE trial_id = ?",
                    [tid],
                ).fetchone()
                if existing is not None:
                    raise ValueError(f"DUPLICATE_TRIAL_ID: trial_id={tid!r} already exists in {DEFAULT_TABLE_NAME}")

                cnt_row = con.execute(f"SELECT COUNT(*) FROM {DEFAULT_TABLE_NAME}").fetchone()
                cur_cnt = int(cnt_row[0]) if cnt_row is not None else 0
                if cur_cnt >= self.max_trials:
                    raise BudgetExceededError(
                        f"ML_TRIAL_BUDGET_EXCEEDED: attempted trial #{cur_cnt + 1} > max_trials={self.max_trials} "
                        f"(ledger={self.db_path})"
                    )

                trial_seq = cur_cnt + 1
                con.execute(
                    f"""
                    INSERT INTO {DEFAULT_TABLE_NAME} (
                        trial_seq, trial_id, family_name, config_hash, oos_label, cutoff_utc,
                        n_folds, n_features_selected, brier_model, brier_climatology,
                        brier_skill_score, roc_auc, min_engine_retention, overall_retention,
                        slippage_breakeven_24m, pf_1x, ev_r_1x, max_dd_pct_1x, verdict,
                        holdout_rows_analysed, order_send_count, params_json, metrics_json, created_utc
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        trial_seq,
                        tid,
                        family_name,
                        cfg_hash,
                        validated_oos,
                        str(eff_cutoff),
                        n_f,
                        n_feat,
                        brier_model,
                        brier_clim,
                        brier_skill,
                        roc_auc,
                        min_eng_ret,
                        overall_ret,
                        slip_be,
                        pf_1x,
                        ev_r_1x,
                        dd_1x,
                        verdict,
                        0,
                        0,
                        params_json,
                        metrics_json,
                        ts_utc,
                    ],
                )
                con.execute("COMMIT")
            except Exception:
                con.execute("ROLLBACK")
                raise

        return {
            "trial_seq": trial_seq,
            "trial_id": tid,
            "family_name": family_name,
            "config_hash": cfg_hash,
            "oos_label": validated_oos,
            "brier_skill_score": brier_skill,
            "roc_auc": roc_auc,
            "slippage_breakeven_24m": slip_be,
            "verdict": verdict,
            "remaining_trials": self.max_trials - trial_seq,
            "holdout_rows_analysed": 0,
            "order_send_count": 0,
            "created_utc": ts_utc,
        }

    def list_trials(self, *, family_name: str | None = None) -> list[dict[str, Any]]:
        with self._connect() as con:
            if family_name is not None:
                cur = con.execute(
                    f"SELECT trial_seq, trial_id, family_name, config_hash, oos_label, cutoff_utc, "
                    f"n_folds, n_features_selected, brier_model, brier_climatology, brier_skill_score, "
                    f"roc_auc, min_engine_retention, overall_retention, slippage_breakeven_24m, "
                    f"pf_1x, ev_r_1x, max_dd_pct_1x, verdict, holdout_rows_analysed, order_send_count, "
                    f"created_utc FROM {DEFAULT_TABLE_NAME} WHERE family_name = ? ORDER BY trial_seq ASC",
                    [family_name],
                )
            else:
                cur = con.execute(
                    f"SELECT trial_seq, trial_id, family_name, config_hash, oos_label, cutoff_utc, "
                    f"n_folds, n_features_selected, brier_model, brier_climatology, brier_skill_score, "
                    f"roc_auc, min_engine_retention, overall_retention, slippage_breakeven_24m, "
                    f"pf_1x, ev_r_1x, max_dd_pct_1x, verdict, holdout_rows_analysed, order_send_count, "
                    f"created_utc FROM {DEFAULT_TABLE_NAME} ORDER BY trial_seq ASC"
                )
            cols = [desc[0] for desc in cur.description]
            return [dict(zip(cols, row, strict=True)) for row in cur.fetchall()]

    def get_best_trial(self, *, require_promoted: bool = True) -> dict[str, Any] | None:
        trials = self.list_trials()
        if require_promoted:
            trials = [t for t in trials if t["verdict"] == VERDICT_PROMOTE]
        if not trials:
            return None
        return max(
            trials,
            key=lambda t: (
                float(t["brier_skill_score"]),
                float(t["slippage_breakeven_24m"]),
                float(t["pf_1x"]),
            ),
        )

    def summary(self) -> dict[str, Any]:
        trials = self.list_trials()
        by_family: dict[str, int] = {fam: 0 for fam in MODEL_FAMILIES}
        promoted = 0
        for t in trials:
            by_family[t["family_name"]] = by_family.get(t["family_name"], 0) + 1
            if t["verdict"] == VERDICT_PROMOTE:
                promoted += 1
        return {
            "db_path": str(self.db_path),
            "table_name": DEFAULT_TABLE_NAME,
            "max_trials": self.max_trials,
            "recorded_trials": len(trials),
            "remaining_trials": max(0, self.max_trials - len(trials)),
            "promoted_trials": promoted,
            "trials_by_family": by_family,
            "best_promoted": self.get_best_trial(require_promoted=True),
            "holdout_rows_analysed": 0,
            "order_send_count": 0,
        }


# ---------------------------------------------------------------------------
# 5. Unified 5-Family Model Registry + Native Attribution (Zero `shap`/`hmmlearn`)
# ---------------------------------------------------------------------------


def _summarize_attributions(
    contributions: np.ndarray,
    expected_value: float,
    feature_names: tuple[str, ...],
    method: str,
) -> dict[str, Any]:
    contrib = np.asarray(contributions, dtype=np.float64)
    if contrib.ndim != 2 or contrib.shape[1] != len(feature_names):
        raise ValueError(
            f"INVALID_CONTRIBUTION_SHAPE: got {contrib.shape}, expected (n, {len(feature_names)})"
        )
    mean_abs = np.mean(np.abs(contrib), axis=0) if contrib.shape[0] > 0 else np.zeros(len(feature_names))
    return {
        "method": method,
        "feature_names": list(feature_names),
        "contributions": contrib,
        "expected_value": float(expected_value),
        "mean_abs_importance": {
            feature_names[j]: round(float(mean_abs[j]), 6) for j in range(len(feature_names))
        },
    }


class BaseWave4ModelAdapter:
    """Common strictly-in-fold adapter contract for all 5 Wave 4 ML families."""

    family_name: str = ""
    attribution_method: str = ""

    def __init__(self, *, random_state: int = 42) -> None:
        self.random_state = _validate_int_param(random_state, name="random_state", minimum=0)
        self._fitted: bool = False
        self._feature_names: tuple[str, ...] = ()
        self._train_p_lo: float = 0.25
        self._train_p_hi: float = 0.75
        self._train_p_toxic: float = 0.35
        self._train_base_rate: float = 0.50

    def _check_fitted(self) -> None:
        if not self._fitted:
            raise RuntimeError(f"MODEL_NOT_FITTED: call fit() on {self.family_name!r} before predict/explain")

    def _fit_train_sizing_quantiles(
        self,
        p_train: np.ndarray,
        y_train: np.ndarray,
        toxic_quantile: float = 0.20,
    ) -> None:
        self._train_base_rate = float(np.mean(y_train))
        self._train_p_lo = float(np.quantile(p_train, 0.10))
        self._train_p_hi = float(np.quantile(p_train, 0.90))
        self._train_p_toxic = float(np.quantile(p_train, toxic_quantile))

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        *,
        feature_names: Sequence[str] | None = None,
        sample_weight: np.ndarray | None = None,
    ) -> BaseWave4ModelAdapter:
        raise NotImplementedError

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        raise NotImplementedError

    def predict_size(
        self,
        X: np.ndarray,
        *,
        mode: str = "toxic_filter",
        scale_lo: float = 0.50,
        scale_hi: float = 1.25,
    ) -> np.ndarray:
        """Compute strictly train-fold calibrated position multipliers (zero validation peeking)."""
        self._check_fitted()
        p = self.predict_proba(X)
        if mode == "toxic_filter":
            if self._train_p_hi - self._train_p_lo <= 1e-9:
                return np.ones_like(p, dtype=np.float64)
            return np.where(p < self._train_p_toxic, 0.0, 1.0)
        if mode == "continuous":
            span = max(self._train_p_hi - self._train_p_lo, 1e-4)
            scaled = scale_lo + (scale_hi - scale_lo) * ((p - self._train_p_lo) / span)
            return np.clip(scaled, scale_lo, scale_hi)
        raise ValueError(f"INVALID_SIZING_MODE: expected 'toxic_filter' or 'continuous', got {mode!r}")

    def explain_attributions(
        self,
        X: np.ndarray,
        *,
        feature_names: Sequence[str] | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError

    def get_params(self) -> dict[str, Any]:
        return {"random_state": self.random_state}


class LogitL2Adapter(BaseWave4ModelAdapter):
    """Family #1: Strictly inside-fold standardized L2 Logistic Regression + exact linear coefficients."""

    family_name = "logit_l2"
    attribution_method = "exact_linear_coefficients"

    def __init__(
        self,
        *,
        l2_reg: float = 2.0,
        max_iter: int = 300,
        backend: str = "auto",
        random_state: int = 42,
    ) -> None:
        super().__init__(random_state=random_state)
        self.l2_reg = _validate_finite_float(l2_reg, name="l2_reg")
        if self.l2_reg <= 0.0:
            raise ValueError(f"l2_reg must be > 0, got {self.l2_reg}")
        self.max_iter = _validate_int_param(max_iter, name="max_iter", minimum=20)
        if backend not in ("auto", "sklearn", "numpy"):
            raise ValueError(f"INVALID_BACKEND: {backend!r}")
        self.backend = backend
        self._mu: np.ndarray = np.empty(0, dtype=np.float64)
        self._sd: np.ndarray = np.empty(0, dtype=np.float64)
        self._w: np.ndarray = np.empty(0, dtype=np.float64)
        self._b: float = 0.0
        self._sklearn_model: Any = None
        self._used_backend: str = "numpy"

    def _fit_numpy_irls(
        self,
        xs: np.ndarray,
        y: np.ndarray,
        sample_weight: np.ndarray | None,
    ) -> tuple[np.ndarray, float]:
        n, d = xs.shape
        sw = np.ones(n, dtype=np.float64) if sample_weight is None else np.asarray(sample_weight, dtype=np.float64)
        sw = sw / max(float(np.mean(sw)), _EPS)
        base_p = float(np.clip(np.average(y, weights=sw), 1e-4, 1.0 - 1e-4))
        w = np.zeros(d, dtype=np.float64)
        b = math.log(base_p / (1.0 - base_p))
        # Newton-IRLS on augmented [xs, 1] with L2 penalty on w only
        x_aug = np.column_stack([xs, np.ones(n, dtype=np.float64)])
        reg_diag = np.zeros(d + 1, dtype=np.float64)
        reg_diag[:d] = self.l2_reg / float(max(1, n))
        theta = np.append(w, b)
        for _ in range(min(40, self.max_iter)):
            logits = x_aug @ theta
            p = _sigmoid(logits)
            r_wt = np.maximum(p * (1.0 - p), 1e-6) * sw / float(n)
            grad = (x_aug.T @ (sw * (p - y))) / float(n) + reg_diag * theta
            hess = (x_aug.T * r_wt) @ x_aug + np.diag(reg_diag)
            hess[d, d] += 1e-8
            try:
                step = np.linalg.solve(hess, grad)
            except np.linalg.LinAlgError:
                step = np.linalg.lstsq(hess, grad, rcond=None)[0]
            theta_new = theta - step
            if float(np.max(np.abs(step))) < 1e-8:
                theta = theta_new
                break
            theta = theta_new
        return theta[:d].copy(), float(theta[d])

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        *,
        feature_names: Sequence[str] | None = None,
        sample_weight: np.ndarray | None = None,
    ) -> LogitL2Adapter:
        x = _validate_feature_matrix(X_train, name="X_train")
        y = _validate_binary_targets(y_train, name="y_train")
        if x.shape[0] != y.size:
            raise ValueError("X_train and y_train row count mismatch")
        if len(np.unique(y)) < 2:
            raise ValueError("SINGLE_CLASS_TRAIN_FOLD: cannot fit logit_l2 on single class")
        self._feature_names = _validate_feature_names(feature_names, x.shape[1])
        self._mu, self._sd = _fit_train_scaler(x)
        xs = _apply_scaler(x, self._mu, self._sd)

        use_sklearn = False
        if self.backend in ("auto", "sklearn"):
            try:
                from sklearn.linear_model import LogisticRegression  # Lazy import ONLY

                use_sklearn = True
            except ImportError:
                if self.backend == "sklearn":
                    raise
                use_sklearn = False

        if use_sklearn:
            clf = LogisticRegression(
                C=1.0 / self.l2_reg,
                max_iter=self.max_iter,
                solver="lbfgs",
                random_state=self.random_state,
            )
            clf.fit(xs, y.astype(np.int64), sample_weight=sample_weight)
            self._sklearn_model = clf
            self._w = np.asarray(clf.coef_[0], dtype=np.float64).copy()
            self._b = float(clf.intercept_[0])
            self._used_backend = "sklearn"
        else:
            self._sklearn_model = None
            self._w, self._b = self._fit_numpy_irls(xs, y, sample_weight)
            self._used_backend = "numpy"

        self._fitted = True
        p_tr = self.predict_proba(x)
        self._fit_train_sizing_quantiles(p_tr, y)
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        self._check_fitted()
        x = _validate_feature_matrix(X, name="X")
        if x.shape[1] != self._w.size:
            raise ValueError(f"FEATURE_DIM_MISMATCH: expected {self._w.size}, got {x.shape[1]}")
        xs = _apply_scaler(x, self._mu, self._sd)
        return np.clip(_sigmoid(xs @ self._w + self._b), _PROB_CLIP, 1.0 - _PROB_CLIP)

    def explain_attributions(
        self,
        X: np.ndarray,
        *,
        feature_names: Sequence[str] | None = None,
    ) -> dict[str, Any]:
        self._check_fitted()
        x = _validate_feature_matrix(X, name="X")
        names = self._feature_names if feature_names is None else _validate_feature_names(feature_names, x.shape[1])
        xs = _apply_scaler(x, self._mu, self._sd)
        # Exact log-odds contributions in standardized coordinates (sum + b == logit(p))
        contrib = xs * self._w[None, :]
        out = _summarize_attributions(contrib, self._b, names, self.attribution_method)
        out["standardized_coefficients"] = {names[j]: round(float(self._w[j]), 6) for j in range(len(names))}
        out["raw_coefficients"] = {names[j]: round(float(self._w[j] / self._sd[j]), 6) for j in range(len(names))}
        out["backend"] = self._used_backend
        return out

    def get_params(self) -> dict[str, Any]:
        return {
            "l2_reg": self.l2_reg,
            "max_iter": self.max_iter,
            "backend": self.backend,
            "random_state": self.random_state,
        }


class LightGBMAdapter(BaseWave4ModelAdapter):
    """Family #2: Strongly regularized LightGBM + native `pred_contrib=True` TreeSHAP (zero `shap`)."""

    family_name = "lightgbm"
    attribution_method = "lightgbm_pred_contrib"

    def __init__(
        self,
        *,
        n_estimators: int = 80,
        max_depth: int = 3,
        num_leaves: int = 7,
        learning_rate: float = 0.05,
        min_child_samples: int = 35,
        subsample: float = 0.8,
        colsample_bytree: float = 0.8,
        reg_lambda: float = 5.0,
        reg_alpha: float = 0.5,
        random_state: int = 42,
    ) -> None:
        super().__init__(random_state=random_state)
        self.n_estimators = _validate_int_param(n_estimators, name="n_estimators", minimum=1)
        self.max_depth = _validate_int_param(max_depth, name="max_depth", minimum=1)
        self.num_leaves = _validate_int_param(num_leaves, name="num_leaves", minimum=2)
        self.learning_rate = _validate_finite_float(learning_rate, name="learning_rate")
        self.min_child_samples = _validate_int_param(min_child_samples, name="min_child_samples", minimum=2)
        self.subsample = _validate_finite_float(subsample, name="subsample")
        self.colsample_bytree = _validate_finite_float(colsample_bytree, name="colsample_bytree")
        self.reg_lambda = _validate_finite_float(reg_lambda, name="reg_lambda")
        self.reg_alpha = _validate_finite_float(reg_alpha, name="reg_alpha")
        self._model: Any = None
        self._n_features: int = 0

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        *,
        feature_names: Sequence[str] | None = None,
        sample_weight: np.ndarray | None = None,
    ) -> LightGBMAdapter:
        import lightgbm as lgb  # Lazy import ONLY

        x = _validate_feature_matrix(X_train, name="X_train")
        y = _validate_binary_targets(y_train, name="y_train")
        if x.shape[0] != y.size:
            raise ValueError("X_train and y_train row count mismatch")
        if len(np.unique(y)) < 2:
            raise ValueError("SINGLE_CLASS_TRAIN_FOLD: cannot fit lightgbm on single class")
        self._n_features = x.shape[1]
        self._feature_names = _validate_feature_names(feature_names, self._n_features)

        eff_min_child = min(self.min_child_samples, max(5, x.shape[0] // 8))
        model = lgb.LGBMClassifier(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            num_leaves=self.num_leaves,
            learning_rate=self.learning_rate,
            min_child_samples=eff_min_child,
            subsample=self.subsample,
            subsample_freq=1,
            colsample_bytree=self.colsample_bytree,
            reg_lambda=self.reg_lambda,
            reg_alpha=self.reg_alpha,
            random_state=self.random_state,
            n_jobs=1,
            verbosity=-1,
            force_col_wise=True,
        )
        model.fit(x, y.astype(np.int64), sample_weight=sample_weight)
        self._model = model
        self._fitted = True
        p_tr = self.predict_proba(x)
        self._fit_train_sizing_quantiles(p_tr, y)
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        self._check_fitted()
        x = _validate_feature_matrix(X, name="X")
        if x.shape[1] != self._n_features:
            raise ValueError(f"FEATURE_DIM_MISMATCH: expected {self._n_features}, got {x.shape[1]}")
        raw_p = self._model.booster_.predict(x)
        return np.clip(np.asarray(raw_p, dtype=np.float64), _PROB_CLIP, 1.0 - _PROB_CLIP)

    def explain_attributions(
        self,
        X: np.ndarray,
        *,
        feature_names: Sequence[str] | None = None,
    ) -> dict[str, Any]:
        self._check_fitted()
        x = _validate_feature_matrix(X, name="X")
        names = self._feature_names if feature_names is None else _validate_feature_names(feature_names, x.shape[1])
        contrib_full = np.asarray(self._model.booster_.predict(x, pred_contrib=True), dtype=np.float64)
        contrib = contrib_full[:, :-1]
        expected_val = float(np.mean(contrib_full[:, -1])) if contrib_full.shape[0] > 0 else 0.0
        return _summarize_attributions(contrib, expected_val, names, self.attribution_method)

    def get_params(self) -> dict[str, Any]:
        return {
            "n_estimators": self.n_estimators,
            "max_depth": self.max_depth,
            "num_leaves": self.num_leaves,
            "learning_rate": self.learning_rate,
            "min_child_samples": self.min_child_samples,
            "subsample": self.subsample,
            "colsample_bytree": self.colsample_bytree,
            "reg_lambda": self.reg_lambda,
            "reg_alpha": self.reg_alpha,
            "random_state": self.random_state,
        }


class CatBoostAdapter(BaseWave4ModelAdapter):
    """Family #3: Regularized CatBoost + native `ShapValues` TreeSHAP (zero `shap`, zero disk files)."""

    family_name = "catboost"
    attribution_method = "catboost_shap_values"

    def __init__(
        self,
        *,
        iterations: int = 90,
        depth: int = 3,
        learning_rate: float = 0.05,
        l2_leaf_reg: float = 10.0,
        min_data_in_leaf: int = 25,
        random_state: int = 42,
    ) -> None:
        super().__init__(random_state=random_state)
        self.iterations = _validate_int_param(iterations, name="iterations", minimum=1)
        self.depth = _validate_int_param(depth, name="depth", minimum=1, maximum=8)
        self.learning_rate = _validate_finite_float(learning_rate, name="learning_rate")
        self.l2_leaf_reg = _validate_finite_float(l2_leaf_reg, name="l2_leaf_reg")
        self.min_data_in_leaf = _validate_int_param(min_data_in_leaf, name="min_data_in_leaf", minimum=1)
        self._model: Any = None
        self._n_features: int = 0

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        *,
        feature_names: Sequence[str] | None = None,
        sample_weight: np.ndarray | None = None,
    ) -> CatBoostAdapter:
        from catboost import CatBoostClassifier, Pool  # Lazy import ONLY

        x = _validate_feature_matrix(X_train, name="X_train")
        y = _validate_binary_targets(y_train, name="y_train")
        if x.shape[0] != y.size:
            raise ValueError("X_train and y_train row count mismatch")
        if len(np.unique(y)) < 2:
            raise ValueError("SINGLE_CLASS_TRAIN_FOLD: cannot fit catboost on single class")
        self._n_features = x.shape[1]
        self._feature_names = _validate_feature_names(feature_names, self._n_features)

        eff_min_leaf = min(self.min_data_in_leaf, max(5, x.shape[0] // 8))
        model = CatBoostClassifier(
            iterations=self.iterations,
            depth=self.depth,
            learning_rate=self.learning_rate,
            l2_leaf_reg=self.l2_leaf_reg,
            min_data_in_leaf=eff_min_leaf,
            random_seed=self.random_state,
            loss_function="Logloss",
            allow_writing_files=False,
            verbose=False,
            thread_count=1,
        )
        train_pool = Pool(x, label=y.astype(np.int64), weight=sample_weight)
        model.fit(train_pool)
        self._model = model
        self._fitted = True
        p_tr = self.predict_proba(x)
        self._fit_train_sizing_quantiles(p_tr, y)
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        self._check_fitted()
        x = _validate_feature_matrix(X, name="X")
        if x.shape[1] != self._n_features:
            raise ValueError(f"FEATURE_DIM_MISMATCH: expected {self._n_features}, got {x.shape[1]}")
        probs = np.asarray(self._model.predict_proba(x), dtype=np.float64)[:, 1]
        return np.clip(probs, _PROB_CLIP, 1.0 - _PROB_CLIP)

    def explain_attributions(
        self,
        X: np.ndarray,
        *,
        feature_names: Sequence[str] | None = None,
    ) -> dict[str, Any]:
        from catboost import Pool  # Lazy import ONLY

        self._check_fitted()
        x = _validate_feature_matrix(X, name="X")
        names = self._feature_names if feature_names is None else _validate_feature_names(feature_names, x.shape[1])
        shap_full = np.asarray(self._model.get_feature_importance(Pool(x), type="ShapValues"), dtype=np.float64)
        contrib = shap_full[:, :-1]
        expected_val = float(np.mean(shap_full[:, -1])) if shap_full.shape[0] > 0 else 0.0
        return _summarize_attributions(contrib, expected_val, names, self.attribution_method)

    def get_params(self) -> dict[str, Any]:
        return {
            "iterations": self.iterations,
            "depth": self.depth,
            "learning_rate": self.learning_rate,
            "l2_leaf_reg": self.l2_leaf_reg,
            "min_data_in_leaf": self.min_data_in_leaf,
            "random_state": self.random_state,
        }


class RegimeGmmJumpAdapter(BaseWave4ModelAdapter):
    """Family #4: Strictly Causal Regime GMM (`sklearn.mixture.GaussianMixture`) / pure-NumPy Jump-HMM.

    ZERO `hmmlearn` dependency!
    Supports:
      - `backend="gmm"` / `"auto"`: lazy `sklearn.mixture.GaussianMixture` (diag covariance) fit strictly on
        `X_train`, mapped to Empirical-Bayes shrunk regime win probabilities.
      - `backend="jump_hmm_numpy"`: pure-NumPy diagonal Gaussian EM + causal forward-only sticky jump filter
        (`jump_penalty >= 0`, strictly forward $t = 0 \to T-1$, ZERO backward smoothing leakage!).
    Attribution: exact leave-one-feature-to-train-mean log-odds margin shift (zero external `shap`).
    """

    family_name = "regime_gmm_jump"
    attribution_method = "regime_margin_perturbation"

    def __init__(
        self,
        *,
        n_regimes: int = 3,
        shrinkage_alpha: float = 15.0,
        jump_penalty: float = 0.0,
        reg_covar: float = 1e-3,
        backend: str = "auto",
        random_state: int = 42,
    ) -> None:
        super().__init__(random_state=random_state)
        self.n_regimes = _validate_int_param(n_regimes, name="n_regimes", minimum=2, maximum=8)
        self.shrinkage_alpha = _validate_finite_float(shrinkage_alpha, name="shrinkage_alpha")
        if self.shrinkage_alpha <= 0.0:
            raise ValueError(f"shrinkage_alpha must be > 0, got {self.shrinkage_alpha}")
        self.jump_penalty = _validate_finite_float(jump_penalty, name="jump_penalty")
        if self.jump_penalty < 0.0:
            raise ValueError(f"jump_penalty must be >= 0, got {self.jump_penalty}")
        self.reg_covar = _validate_finite_float(reg_covar, name="reg_covar")
        if self.reg_covar <= 0.0:
            raise ValueError(f"reg_covar must be > 0, got {self.reg_covar}")
        if backend not in ("auto", "gmm", "jump_hmm_numpy"):
            raise ValueError(f"INVALID_BACKEND: {backend!r}")
        self.backend = backend

        self._mu: np.ndarray = np.empty(0, dtype=np.float64)
        self._sd: np.ndarray = np.empty(0, dtype=np.float64)
        self._means: np.ndarray = np.empty((0, 0), dtype=np.float64)
        self._vars: np.ndarray = np.empty((0, 0), dtype=np.float64)
        self._weights: np.ndarray = np.empty(0, dtype=np.float64)
        self._regime_win_prob: np.ndarray = np.empty(0, dtype=np.float64)
        self._used_backend: str = "jump_hmm_numpy"

    def _fit_numpy_diag_gmm(self, xs: np.ndarray, k_eff: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        n, d = xs.shape
        rng = np.random.default_rng(self.random_state)
        # Deterministic quantile/k-means++ initialization
        init_idx = np.linspace(0, n - 1, k_eff, dtype=np.int64)
        # Sort by first PC proxy (sum of features) for deterministic regime spread
        score_order = np.argsort(np.sum(xs, axis=1), kind="mergesort")
        means = xs[score_order[init_idx]].copy()
        # Add tiny deterministic jitter if any centers coincide
        means += rng.normal(0.0, 1e-4, size=means.shape)
        variances = np.full((k_eff, d), 1.0 + self.reg_covar, dtype=np.float64)
        weights = np.full(k_eff, 1.0 / float(k_eff), dtype=np.float64)

        for _ in range(40):
            log_resp = self._log_gaussian_diag(xs, means, variances) + np.log(np.maximum(weights, _EPS))[None, :]
            max_lr = np.max(log_resp, axis=1, keepdims=True)
            resp = np.exp(log_resp - max_lr)
            resp /= np.maximum(np.sum(resp, axis=1, keepdims=True), _EPS)

            nk = np.sum(resp, axis=0)
            weights = (nk + 1e-3) / float(n + k_eff * 1e-3)
            for k in range(k_eff):
                denom = max(float(nk[k]), 1e-6)
                mu_k = (resp[:, k] @ xs) / denom
                diff = xs - mu_k[None, :]
                var_k = (resp[:, k] @ (diff * diff)) / denom + self.reg_covar
                means[k] = mu_k
                variances[k] = np.maximum(var_k, self.reg_covar)
        return means, variances, weights

    @staticmethod
    def _log_gaussian_diag(xs: np.ndarray, means: np.ndarray, variances: np.ndarray) -> np.ndarray:
        # Shape: (n, k)
        d = xs.shape[1]
        const = -0.5 * d * math.log(2.0 * math.pi)
        log_det = -0.5 * np.sum(np.log(np.maximum(variances, 1e-12)), axis=1)  # (k,)
        # Broadcast squared Mahalanobis distance
        diff = xs[:, None, :] - means[None, :, :]
        maha = -0.5 * np.sum((diff * diff) / np.maximum(variances[None, :, :], 1e-12), axis=2)
        return const + log_det[None, :] + maha

    def _compute_posteriors(self, xs: np.ndarray) -> np.ndarray:
        log_lik = self._log_gaussian_diag(xs, self._means, self._vars)
        k_eff = self._weights.size
        if self.jump_penalty <= 0.0:
            log_post = log_lik + np.log(np.maximum(self._weights, _EPS))[None, :]
            log_post -= np.max(log_post, axis=1, keepdims=True)
            post = np.exp(log_post)
            post /= np.maximum(np.sum(post, axis=1, keepdims=True), _EPS)
            return post

        # Strictly causal FORWARD-ONLY sticky jump filter (NEVER backward smoothing!)
        stay_prob = float(np.clip(1.0 / (1.0 + math.exp(-self.jump_penalty)), 0.5, 0.995))
        switch_prob = (1.0 - stay_prob) / float(max(1, k_eff - 1))
        trans = np.full((k_eff, k_eff), switch_prob, dtype=np.float64)
        np.fill_diagonal(trans, stay_prob)

        n = xs.shape[0]
        post = np.empty((n, k_eff), dtype=np.float64)
        prior = self._weights.copy()
        for t in range(n):
            pred = prior if t == 0 else (post[t - 1] @ trans)
            lp = log_lik[t] + np.log(np.maximum(pred, _EPS))
            lp -= float(np.max(lp))
            pt = np.exp(lp)
            pt /= max(float(np.sum(pt)), _EPS)
            post[t] = pt
        return post

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        *,
        feature_names: Sequence[str] | None = None,
        sample_weight: np.ndarray | None = None,
    ) -> RegimeGmmJumpAdapter:
        x = _validate_feature_matrix(X_train, name="X_train")
        y = _validate_binary_targets(y_train, name="y_train")
        if x.shape[0] != y.size:
            raise ValueError("X_train and y_train row count mismatch")
        if len(np.unique(y)) < 2:
            raise ValueError("SINGLE_CLASS_TRAIN_FOLD: cannot fit regime_gmm_jump on single class")
        self._feature_names = _validate_feature_names(feature_names, x.shape[1])
        self._mu, self._sd = _fit_train_scaler(x)
        xs = _apply_scaler(x, self._mu, self._sd)

        k_eff = min(self.n_regimes, max(2, x.shape[0] // 20))
        use_sklearn_gmm = False
        if self.backend in ("auto", "gmm"):
            try:
                from sklearn.mixture import GaussianMixture  # Lazy import ONLY (ZERO hmmlearn!)

                use_sklearn_gmm = True
            except ImportError:
                if self.backend == "gmm":
                    raise
                use_sklearn_gmm = False

        if use_sklearn_gmm:
            gmm = GaussianMixture(
                n_components=k_eff,
                covariance_type="diag",
                reg_covar=self.reg_covar,
                max_iter=200,
                n_init=2,
                random_state=self.random_state,
            )
            gmm.fit(xs)
            self._means = np.asarray(gmm.means_, dtype=np.float64).copy()
            self._vars = np.maximum(np.asarray(gmm.covariances_, dtype=np.float64).copy(), self.reg_covar)
            self._weights = np.asarray(gmm.weights_, dtype=np.float64).copy()
            self._used_backend = "sklearn_gmm"
        else:
            self._means, self._vars, self._weights = self._fit_numpy_diag_gmm(xs, k_eff)
            self._used_backend = "jump_hmm_numpy"

        # Empirical-Bayes shrunk win probability per regime strictly on train fold
        sw = (
            np.ones(x.shape[0], dtype=np.float64)
            if sample_weight is None
            else np.asarray(sample_weight, dtype=np.float64)
        )
        resp_tr = self._compute_posteriors(xs)
        base_y = float(np.average(y, weights=sw))
        regime_p = np.empty(k_eff, dtype=np.float64)
        for k in range(k_eff):
            eff_n = float(np.sum(sw * resp_tr[:, k]))
            eff_wins = float(np.sum(sw * resp_tr[:, k] * y))
            regime_p[k] = (eff_wins + self.shrinkage_alpha * base_y) / (eff_n + self.shrinkage_alpha)
        self._regime_win_prob = np.clip(regime_p, _PROB_CLIP, 1.0 - _PROB_CLIP)

        self._fitted = True
        p_tr = self.predict_proba(x)
        self._fit_train_sizing_quantiles(p_tr, y)
        return self

    def predict_regime_posteriors(self, X: np.ndarray) -> np.ndarray:
        self._check_fitted()
        x = _validate_feature_matrix(X, name="X")
        if x.shape[1] != self._mu.size:
            raise ValueError(f"FEATURE_DIM_MISMATCH: expected {self._mu.size}, got {x.shape[1]}")
        xs = _apply_scaler(x, self._mu, self._sd)
        return self._compute_posteriors(xs)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        post = self.predict_regime_posteriors(X)
        probs = post @ self._regime_win_prob
        return np.clip(probs, _PROB_CLIP, 1.0 - _PROB_CLIP)

    def explain_attributions(
        self,
        X: np.ndarray,
        *,
        feature_names: Sequence[str] | None = None,
    ) -> dict[str, Any]:
        self._check_fitted()
        x = _validate_feature_matrix(X, name="X")
        n, d = x.shape
        names = self._feature_names if feature_names is None else _validate_feature_names(feature_names, d)
        xs = _apply_scaler(x, self._mu, self._sd)
        base_probs = np.clip(self._compute_posteriors(xs) @ self._regime_win_prob, _PROB_CLIP, 1.0 - _PROB_CLIP)
        base_logits = _logit(base_probs)

        contrib = np.empty((n, d), dtype=np.float64)
        for j in range(d):
            xs_masked = xs.copy()
            xs_masked[:, j] = 0.0  # Replace feature j with train-fold mean
            raw_masked = self._compute_posteriors(xs_masked) @ self._regime_win_prob
            p_masked = np.clip(raw_masked, _PROB_CLIP, 1.0 - _PROB_CLIP)
            contrib[:, j] = base_logits - _logit(p_masked)

        zero_raw = self._compute_posteriors(np.zeros((1, d), dtype=np.float64)) @ self._regime_win_prob
        zero_prob = float(np.clip(zero_raw, _PROB_CLIP, 1.0 - _PROB_CLIP)[0])
        out = _summarize_attributions(
            contrib, float(_logit(np.array([zero_prob]))[0]), names, self.attribution_method
        )
        out["backend"] = self._used_backend
        out["regime_win_probs"] = [round(float(v), 6) for v in self._regime_win_prob.tolist()]
        return out

    def get_params(self) -> dict[str, Any]:
        return {
            "n_regimes": self.n_regimes,
            "shrinkage_alpha": self.shrinkage_alpha,
            "jump_penalty": self.jump_penalty,
            "reg_covar": self.reg_covar,
            "backend": self.backend,
            "random_state": self.random_state,
        }


class CalibratedBetSizingAdapter(BaseWave4ModelAdapter):
    """Family #5: Strictly inside-fold chronological Platt/Isotonic calibration + AFML Ch. 10 bet sizing."""

    family_name = "calibrated_bet_sizing"
    attribution_method = "calibrated_chain_rule"

    def __init__(
        self,
        *,
        base_family: str = "logit_l2",
        base_params: Mapping[str, Any] | None = None,
        calibration_method: str = "platt",
        calibration_frac: float = 0.25,
        size_floor: float = 0.25,
        size_cap: float = 1.25,
        toxic_cutoff_prob: float | None = None,
        random_state: int = 42,
    ) -> None:
        super().__init__(random_state=random_state)
        if base_family not in ("logit_l2", "lightgbm", "catboost", "regime_gmm_jump"):
            raise ValueError(f"INVALID_BASE_FAMILY: {base_family!r}")
        if calibration_method not in ("platt", "isotonic"):
            raise ValueError(f"INVALID_CALIBRATION_METHOD: {calibration_method!r}")
        cal_f = _validate_finite_float(calibration_frac, name="calibration_frac")
        if not (0.10 <= cal_f <= 0.45):
            raise ValueError(f"INVALID_CALIBRATION_FRAC: expected [0.10, 0.45], got {cal_f}")
        s_lo = _validate_finite_float(size_floor, name="size_floor")
        s_hi = _validate_finite_float(size_cap, name="size_cap")
        if s_lo < 0.0 or s_hi < s_lo:
            raise ValueError(f"INVALID_SIZE_BOUNDS: floor={s_lo}, cap={s_hi}")

        self.base_family = base_family
        self.base_params = dict(base_params) if base_params is not None else {}
        self.calibration_method = calibration_method
        self.calibration_frac = cal_f
        self.size_floor = s_lo
        self.size_cap = s_hi
        self.toxic_cutoff_prob = (
            None if toxic_cutoff_prob is None else _validate_finite_float(toxic_cutoff_prob, name="toxic_cutoff_prob")
        )

        self._base_model: BaseWave4ModelAdapter | None = None
        self._platt_a: float = 1.0
        self._platt_b: float = 0.0
        self._iso_x: np.ndarray = np.empty(0, dtype=np.float64)
        self._iso_y: np.ndarray = np.empty(0, dtype=np.float64)

    @staticmethod
    def _fit_platt_numpy(raw_logits: np.ndarray, y_cal: np.ndarray) -> tuple[float, float]:
        # Regularized 1D Platt scaling shrinking toward identity (a=1, b=0) to prevent overfitting
        a = 1.0
        b = 0.0
        n = max(1, int(y_cal.size))
        reg_a = 2.0 / float(n)
        reg_b = 1.0 / float(n)
        for _ in range(30):
            z = a * raw_logits + b
            p = _sigmoid(z)
            w = np.maximum(p * (1.0 - p), 1e-6)
            g_a = float(np.mean((p - y_cal) * raw_logits)) + reg_a * (a - 1.0)
            g_b = float(np.mean(p - y_cal)) + reg_b * b
            h_aa = float(np.mean(w * raw_logits * raw_logits)) + reg_a
            h_ab = float(np.mean(w * raw_logits))
            h_bb = float(np.mean(w)) + reg_b
            det = h_aa * h_bb - h_ab * h_ab
            if det <= 1e-12:
                break
            da = (h_bb * g_a - h_ab * g_b) / det
            db = (-h_ab * g_a + h_aa * g_b) / det
            a = float(np.clip(a - da, 0.05, 5.0))
            b = float(np.clip(b - db, -4.0, 4.0))
            if max(abs(da), abs(db)) < 1e-7:
                break
        return a, b

    @staticmethod
    def _fit_pava_isotonic(raw_p: np.ndarray, y_cal: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Pure-NumPy Pool-Adjacent-Violators Algorithm (PAVA) for monotonic probability calibration."""
        order = np.argsort(raw_p, kind="mergesort")
        xs = raw_p[order]
        ys = y_cal[order]
        # Stack of blocks: [sum_y, count, sum_x]
        blocks: list[list[float]] = []
        for xv, yv in zip(xs, ys, strict=True):
            blocks.append([float(yv), 1.0, float(xv)])
            while len(blocks) >= 2 and (blocks[-2][0] / blocks[-2][1]) > (blocks[-1][0] / blocks[-1][1]):
                b_last = blocks.pop()
                blocks[-1][0] += b_last[0]
                blocks[-1][1] += b_last[1]
                blocks[-1][2] += b_last[2]
        kx = np.array([b[2] / b[1] for b in blocks], dtype=np.float64)
        ky = np.clip(np.array([b[0] / b[1] for b in blocks], dtype=np.float64), _PROB_CLIP, 1.0 - _PROB_CLIP)
        return kx, ky

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        *,
        feature_names: Sequence[str] | None = None,
        sample_weight: np.ndarray | None = None,
    ) -> CalibratedBetSizingAdapter:
        x = _validate_feature_matrix(X_train, name="X_train")
        y = _validate_binary_targets(y_train, name="y_train")
        n = x.shape[0]
        if n != y.size:
            raise ValueError("X_train and y_train row count mismatch")
        if len(np.unique(y)) < 2:
            raise ValueError("SINGLE_CLASS_TRAIN_FOLD: cannot fit calibrated_bet_sizing on single class")
        self._feature_names = _validate_feature_names(feature_names, x.shape[1])

        # Chronological inner split strictly inside X_train (zero validation peeking!)
        split_pt = int(round(n * (1.0 - self.calibration_frac)))
        split_pt = max(15, min(n - 10, split_pt))
        has_valid_cal = (
            split_pt >= 15
            and (n - split_pt) >= 10
            and len(np.unique(y[:split_pt])) >= 2
            and len(np.unique(y[split_pt:])) >= 2
        )

        params = dict(self.base_params)
        params.setdefault("random_state", self.random_state)
        base_mdl = create_model_adapter(self.base_family, **params)

        if has_valid_cal:
            sw_core = None if sample_weight is None else np.asarray(sample_weight, dtype=np.float64)[:split_pt]
            base_mdl.fit(x[:split_pt], y[:split_pt], feature_names=self._feature_names, sample_weight=sw_core)
            p_cal_raw = base_mdl.predict_proba(x[split_pt:])
            y_cal = y[split_pt:]
            if self.calibration_method == "platt":
                self._platt_a, self._platt_b = self._fit_platt_numpy(_logit(p_cal_raw), y_cal)
            else:
                self._iso_x, self._iso_y = self._fit_pava_isotonic(p_cal_raw, y_cal)
        else:
            # Fallback if inner calibration slice lacks both classes: fit on full train, identity calibration
            base_mdl.fit(x, y, feature_names=self._feature_names, sample_weight=sample_weight)
            self._platt_a, self._platt_b = 1.0, 0.0
            self._iso_x = np.array([0.0, 1.0], dtype=np.float64)
            self._iso_y = np.array([_PROB_CLIP, 1.0 - _PROB_CLIP], dtype=np.float64)

        self._base_model = base_mdl
        self._fitted = True
        p_tr = self.predict_proba(x)
        self._fit_train_sizing_quantiles(p_tr, y)
        return self

    def _calibrate(self, raw_p: np.ndarray) -> np.ndarray:
        if self.calibration_method == "platt":
            return np.clip(_sigmoid(self._platt_a * _logit(raw_p) + self._platt_b), _PROB_CLIP, 1.0 - _PROB_CLIP)
        return np.clip(np.interp(raw_p, self._iso_x, self._iso_y), _PROB_CLIP, 1.0 - _PROB_CLIP)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        self._check_fitted()
        if self._base_model is None:
            raise RuntimeError("Base model missing")
        raw_p = self._base_model.predict_proba(X)
        return self._calibrate(raw_p)

    def predict_size(
        self,
        X: np.ndarray,
        *,
        mode: str = "afml_bet_sizing",
        scale_lo: float | None = None,
        scale_hi: float | None = None,
    ) -> np.ndarray:
        """AFML Ch. 10 calibrated bet sizing (`2*Phi(z) - 1` rescaled into `[size_floor, size_cap]`)."""
        self._check_fitted()
        lo = self.size_floor if scale_lo is None else float(scale_lo)
        hi = self.size_cap if scale_hi is None else float(scale_hi)
        if mode in ("toxic_filter", "continuous"):
            return super().predict_size(X, mode=mode, scale_lo=lo, scale_hi=hi)
        if mode != "afml_bet_sizing":
            raise ValueError(f"INVALID_SIZING_MODE: {mode!r}")

        p = self.predict_proba(X)
        # Centered AFML z-score around strictly train-fold base rate
        denom = np.sqrt(np.maximum(p * (1.0 - p), 1e-4))
        z = (p - self._train_base_rate) / denom
        # Map Phi(z) in [0, 1] linearly into [lo, hi]
        phi_z = _standard_normal_cdf(z)
        sizes = lo + (hi - lo) * phi_z
        if self.toxic_cutoff_prob is not None:
            sizes = np.where(p < self.toxic_cutoff_prob, 0.0, sizes)
        return np.clip(sizes, 0.0 if self.toxic_cutoff_prob is not None else lo, hi)

    def explain_attributions(
        self,
        X: np.ndarray,
        *,
        feature_names: Sequence[str] | None = None,
    ) -> dict[str, Any]:
        self._check_fitted()
        if self._base_model is None:
            raise RuntimeError("Base model missing")
        base_exp = self._base_model.explain_attributions(X, feature_names=feature_names)
        scale = self._platt_a if self.calibration_method == "platt" else 1.0
        contrib = np.asarray(base_exp["contributions"], dtype=np.float64) * scale
        exp_val = float(base_exp["expected_value"]) * scale + (
            self._platt_b if self.calibration_method == "platt" else 0.0
        )
        names = tuple(base_exp["feature_names"])
        out = _summarize_attributions(contrib, exp_val, names, self.attribution_method)
        out["base_family"] = self.base_family
        out["base_attribution_method"] = base_exp["method"]
        out["calibration_method"] = self.calibration_method
        return out

    def get_params(self) -> dict[str, Any]:
        return {
            "base_family": self.base_family,
            "base_params": dict(self.base_params),
            "calibration_method": self.calibration_method,
            "calibration_frac": self.calibration_frac,
            "size_floor": self.size_floor,
            "size_cap": self.size_cap,
            "toxic_cutoff_prob": self.toxic_cutoff_prob,
            "random_state": self.random_state,
        }


MODEL_FAMILY_REGISTRY: dict[str, type[BaseWave4ModelAdapter]] = {
    "logit_l2": LogitL2Adapter,
    "lightgbm": LightGBMAdapter,
    "catboost": CatBoostAdapter,
    "regime_gmm_jump": RegimeGmmJumpAdapter,
    "calibrated_bet_sizing": CalibratedBetSizingAdapter,
}

MODEL_FAMILY_SPECS: dict[str, dict[str, Any]] = {
    "logit_l2": {
        "family_name": "logit_l2",
        "description": "Inside-fold standardized L2 Logistic Regression (white-box linear baseline)",
        "attribution_method": "exact_linear_coefficients",
        "lazy_dependencies": ["sklearn.linear_model.LogisticRegression (optional, pure-NumPy IRLS fallback)"],
        "forbidden_dependencies": ["hmmlearn", "shap"],
        "onnx_exportable": True,
        "default_params": {"l2_reg": 2.0, "max_iter": 300},
    },
    "lightgbm": {
        "family_name": "lightgbm",
        "description": "Shallow regularized LightGBM GBDT (`max_depth=3`, `num_leaves=7`) with native TreeSHAP",
        "attribution_method": "lightgbm_pred_contrib",
        "lazy_dependencies": ["lightgbm"],
        "forbidden_dependencies": ["hmmlearn", "shap"],
        "onnx_exportable": True,
        "default_params": {"n_estimators": 80, "max_depth": 3, "num_leaves": 7, "reg_lambda": 5.0},
    },
    "catboost": {
        "family_name": "catboost",
        "description": "Shallow oblivious-tree CatBoost (`depth=3`, `allow_writing_files=False`) with native TreeSHAP",
        "attribution_method": "catboost_shap_values",
        "lazy_dependencies": ["catboost"],
        "forbidden_dependencies": ["hmmlearn", "shap"],
        "onnx_exportable": True,
        "default_params": {"iterations": 90, "depth": 3, "l2_leaf_reg": 10.0},
    },
    "regime_gmm_jump": {
        "family_name": "regime_gmm_jump",
        "description": "Causal Regime GMM (`sklearn.mixture.GaussianMixture`) / pure-NumPy Forward-Only Jump-HMM",
        "attribution_method": "regime_margin_perturbation",
        "lazy_dependencies": ["sklearn.mixture.GaussianMixture (optional, pure-NumPy Jump-HMM fallback)"],
        "forbidden_dependencies": ["hmmlearn", "shap"],
        "onnx_exportable": True,
        "default_params": {"n_regimes": 3, "shrinkage_alpha": 15.0, "jump_penalty": 0.0},
    },
    "calibrated_bet_sizing": {
        "family_name": "calibrated_bet_sizing",
        "description": "Chronological inside-fold Platt/Isotonic calibration + AFML Ch. 10 bet sizing",
        "attribution_method": "calibrated_chain_rule",
        "lazy_dependencies": ["inherits base_family (default logit_l2; pure-NumPy PAVA/Platt)"],
        "forbidden_dependencies": ["hmmlearn", "shap"],
        "onnx_exportable": True,
        "default_params": {
            "base_family": "logit_l2",
            "calibration_method": "platt",
            "calibration_frac": 0.25,
            "size_floor": 0.25,
            "size_cap": 1.25,
        },
    },
}


def create_model_adapter(family_name: str, **kwargs: Any) -> BaseWave4ModelAdapter:
    """Instantiate one of the 5 registered Wave 4 ML model adapters fail-closed."""
    if not isinstance(family_name, str) or family_name not in MODEL_FAMILY_REGISTRY:
        raise ValueError(f"UNKNOWN_MODEL_FAMILY: {family_name!r}; expected one of {MODEL_FAMILIES}")
    cls = MODEL_FAMILY_REGISTRY[family_name]
    return cls(**kwargs)


def list_model_families() -> list[dict[str, Any]]:
    """Return canonical specifications for all 5 Wave 4 ML model families."""
    return [dict(MODEL_FAMILY_SPECS[fam]) for fam in MODEL_FAMILIES]


# ---------------------------------------------------------------------------
# 6. End-to-End Strictly Causal Walk-Forward CV Orchestrator (for `w4-m1-arena`)
# ---------------------------------------------------------------------------


def run_purged_walkforward_cv(
    X: np.ndarray,
    y: np.ndarray,
    entry_ts: Any,
    exit_ts: Any,
    net_r: np.ndarray | Sequence[float],
    engine_ids: Sequence[Any],
    *,
    family_name: str,
    model_params: Mapping[str, Any] | None = None,
    feature_names: Sequence[str] | None = None,
    n_splits: int = 5,
    purge_days: int = DEFAULT_PURGE_DAYS,
    embargo_days: int = DEFAULT_EMBARGO_DAYS,
    min_train_samples: int = DEFAULT_MIN_TRAIN_SAMPLES,
    mode: str = "expanding",
    rolling_window_days: int | None = None,
    min_k: int = DEFAULT_MIN_SELECTED_FEATURES,
    max_k: int = DEFAULT_MAX_SELECTED_FEATURES,
    sizing_mode: str = "toxic_filter",
    slippage_mults: Sequence[float] = DEFAULT_SLIPPAGE_MULTS,
    base_cost_r: np.ndarray | Sequence[float] | float = DEFAULT_BASE_COST_R,
    risk_pct_per_trade: np.ndarray | Sequence[float] | float | None = None,
    oos_label: str = CONSUMED_CLB_TAG,
    cutoff_utc: str | date | datetime | int = HOLDOUT_CUTOFF_DATE,
    compute_attributions: bool = True,
    ledger: Wave4MlBudgetLedger | None = None,
    trial_id: str | None = None,
) -> dict[str, Any]:
    """Run strictly causal Expanding/Rolling Purged+Embargo Walk-Forward CV for one model family.

    Every scaler, feature-pruner (`min_k..max_k`), model fit, GMM/Jump-HMM regime estimator,
    calibrator, and sizing quantile is fit STRICTLY inside each fold's training window.
    """
    validated_label = validate_oos_label(oos_label)
    _enforce_cutoff_exclusive(cutoff_utc)

    x_mat = _validate_feature_matrix(X, name="X")
    y_arr = _validate_binary_targets(y, name="y")
    r_arr = _validate_float_array(net_r, name="net_r")
    n, d = x_mat.shape
    if y_arr.size != n or r_arr.size != n or len(engine_ids) != n:
        raise ValueError("INPUT_LENGTH_MISMATCH across X, y, net_r, engine_ids")

    ent = _parse_timestamp_array(entry_ts, name="entry_ts")
    ex = _parse_timestamp_array(exit_ts, name="exit_ts")
    if ent.size != n or ex.size != n:
        raise ValueError("TIMESTAMP_LENGTH_MISMATCH vs X")
    fnames = _validate_feature_names(feature_names, d)

    splitter = ExpandingPurgedWalkForwardSplitter(
        n_splits=n_splits,
        purge_days=purge_days,
        embargo_days=embargo_days,
        min_train_samples=min_train_samples,
        mode=mode,
        rolling_window_days=rolling_window_days,
        cutoff_utc=cutoff_utc,
    )

    oof_probs = np.full(n, np.nan, dtype=np.float64)
    oof_sizes = np.full(n, np.nan, dtype=np.float64)
    oof_mask = np.zeros(n, dtype=bool)
    oof_attrib_accum = np.zeros(d, dtype=np.float64)
    oof_attrib_counts = np.zeros(d, dtype=np.int64)
    fold_reports: list[dict[str, Any]] = []
    params = dict(model_params) if model_params is not None else {}

    for fold_i, (train_idx, val_idx) in enumerate(splitter.split(ent, ex, cutoff_utc=cutoff_utc)):
        # 1. Strictly inside-fold feature pruning (NEVER touches val_idx!)
        pruning = select_inside_fold_features(
            x_mat[train_idx],
            y_arr[train_idx],
            feature_names=fnames,
            min_k=min_k,
            max_k=max_k,
        )
        sel_idx = pruning["selected_indices"]
        sel_names = pruning["selected_names"]

        # 2. Strictly inside-fold model + calibrator + sizing fit
        adapter = create_model_adapter(family_name, **params)
        adapter.fit(x_mat[train_idx][:, sel_idx], y_arr[train_idx], feature_names=sel_names)

        # 3. Predict OOF probabilities and strictly train-calibrated sizes on val_idx
        p_val = adapter.predict_proba(x_mat[val_idx][:, sel_idx])
        s_val = adapter.predict_size(x_mat[val_idx][:, sel_idx], mode=sizing_mode)

        oof_probs[val_idx] = p_val
        oof_sizes[val_idx] = s_val
        oof_mask[val_idx] = True

        fold_attrib_summary: dict[str, float] | None = None
        if compute_attributions:
            exp = adapter.explain_attributions(x_mat[val_idx][:, sel_idx], feature_names=sel_names)
            contrib_mat = np.asarray(exp["contributions"], dtype=np.float64)
            mean_abs_local = np.mean(np.abs(contrib_mat), axis=0)
            fold_attrib_summary = {
                sel_names[pos]: round(float(mean_abs_local[pos]), 6) for pos in range(len(sel_names))
            }
            for pos, orig_col in enumerate(sel_idx):
                oof_attrib_accum[orig_col] += float(np.sum(np.abs(contrib_mat[:, pos])))
                oof_attrib_counts[orig_col] += int(val_idx.size)

        fold_audit = splitter.last_fold_audits[fold_i]
        fold_brier = compute_brier_metrics(y_arr[val_idx], p_val)
        fold_reports.append(
            {
                "fold_index": fold_i,
                "n_train": fold_audit.n_train,
                "n_val": fold_audit.n_val,
                "n_purged": fold_audit.n_purged,
                "n_embargoed": fold_audit.n_embargoed,
                "observed_gap_days": round(fold_audit.observed_gap_days, 3),
                "n_features_selected": pruning["k"],
                "selected_features": sel_names,
                "brier_skill_score": round(float(fold_brier["brier_skill_score"]), 6),
                "roc_auc": round(float(fold_brier["roc_auc"]), 6),
                "mean_abs_attributions": fold_attrib_summary,
            }
        )

    if not bool(np.any(oof_mask)):
        raise ValueError("NO_OOF_EVALUATED_SAMPLES: walk-forward produced zero validation predictions")

    eval_idx = np.flatnonzero(oof_mask)
    eval_eng = [engine_ids[i] for i in eval_idx.tolist()]
    cost_eval: Any = (
        base_cost_r
        if isinstance(base_cost_r, (int, float, np.integer, np.floating))
        else np.asarray(base_cost_r, dtype=np.float64)[eval_idx]
    )
    risk_eval: Any = (
        None
        if risk_pct_per_trade is None
        else (
            risk_pct_per_trade
            if isinstance(risk_pct_per_trade, (int, float, np.integer, np.floating))
            else np.asarray(risk_pct_per_trade, dtype=np.float64)[eval_idx]
        )
    )

    evaluation = evaluate_oof_brier_and_economics(
        y_arr[eval_idx],
        oof_probs[eval_idx],
        r_arr[eval_idx],
        eval_eng,
        slippage_mults=slippage_mults,
        position_sizes=oof_sizes[eval_idx],
        base_cost_r=cost_eval,
        risk_pct_per_trade=risk_eval,
        oos_label=validated_label,
        entry_ts=ent[eval_idx],
        cutoff_utc=cutoff_utc,
    )

    mean_abs_global = {
        fnames[j]: round(float(oof_attrib_accum[j] / oof_attrib_counts[j]), 6)
        for j in range(d)
        if oof_attrib_counts[j] > 0
    }
    avg_k = int(round(float(np.mean([f["n_features_selected"] for f in fold_reports]))))

    ledger_receipt: dict[str, Any] | None = None
    if ledger is not None:
        tid = trial_id or f"{family_name}_{_canonical_json_hash({'params': params, 'n_splits': n_splits})[:12]}"
        ledger_receipt = ledger.record_trial(
            trial_id=tid,
            family_name=family_name,
            params=params,
            evaluation=evaluation,
            n_folds=len(fold_reports),
            n_features_selected=avg_k,
            oos_label=validated_label,
            cutoff_utc=cutoff_utc,
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "family_name": family_name,
        "model_params": params,
        "oos_label": validated_label,
        "holdout_cutoff_date": HOLDOUT_CUTOFF_DATE,
        "holdout_rows_analysed": 0,
        "order_send_count": ORDER_SEND_COUNT,
        "splitter_config": {
            "n_splits": n_splits,
            "purge_days": purge_days,
            "embargo_days": embargo_days,
            "min_train_samples": min_train_samples,
            "mode": mode,
            "rolling_window_days": rolling_window_days,
        },
        "n_total_samples": n,
        "n_oof_samples": int(eval_idx.size),
        "oof_mask": oof_mask,
        "oof_probs": oof_probs,
        "oof_sizes": oof_sizes,
        "folds": fold_reports,
        "oof_feature_importance": mean_abs_global,
        "evaluation": evaluation,
        "verdict": evaluation["verdict"],
        "ledger_receipt": ledger_receipt,
    }


# ---------------------------------------------------------------------------
# 7. Atomic JSON Receipt Builder & Writer (LF, 0 BOM)
# ---------------------------------------------------------------------------


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    tmp: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
            tmp = Path(fh.name)
        os.replace(tmp, path)
        tmp = None
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)


def build_cv_receipt(
    *,
    splitter_verification: Mapping[str, Any] | None = None,
    pruner_verification: Mapping[str, Any] | None = None,
    budget_verification: Mapping[str, Any] | None = None,
    model_registry_verification: Mapping[str, Any] | None = None,
    test_results: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble structured JSON receipt for Wave 1B `w4-m1-cv` audit & swarm dropbox."""
    return {
        "schema": "naqex-wave4-m1-cv-receipt-v1",
        "cv_schema_version": SCHEMA_VERSION,
        "worker": "w4-m1-cv",
        "wave": "Wave 1B (Total Offensive #4 v4.8.1 FINAL)",
        "generated_utc": datetime.now(UTC).isoformat(),
        "hard_invariants": {
            "order_send_capable": ORDER_SEND_CAPABLE,
            "order_send_count": ORDER_SEND_COUNT,
            "spend_vnd": 0,
            "holdout_cutoff_date": HOLDOUT_CUTOFF_DATE,
            "dev_cutoff_date": DEV_CUTOFF_DATE,
            "dev_cutoff_sec": DEV_CUTOFF_SEC,
            "holdout_2025_plus_sealed": True,
            "holdout_rows_analysed": 0,
            "zero_bare_asserts": True,
            "lazy_ml_imports_only": True,
            "zero_hmmlearn_dependency": True,
            "zero_external_shap_dependency": True,
            "consumed_clb_tag": CONSUMED_CLB_TAG,
            "max_ml_trials_budget": DEFAULT_MAX_ML_TRIALS,
            "min_purge_days": MIN_PURGE_DAYS,
            "min_embargo_days": MIN_EMBARGO_DAYS,
        },
        "deliverables": {
            "module": "tooling/ai-engines/quant_factory/wave4/ml_walkforward_cv.py",
            "tests": "tooling/ai-engines/tests/wave4/test_wave4_ml_walkforward_cv.py",
        },
        "model_families": list_model_families(),
        "engine_id_codes": dict(ENGINE_ID_CODES),
        "splitter_verification": dict(splitter_verification) if splitter_verification is not None else None,
        "pruner_verification": dict(pruner_verification) if pruner_verification is not None else None,
        "budget_verification": dict(budget_verification) if budget_verification is not None else None,
        "model_registry_verification": (
            dict(model_registry_verification) if model_registry_verification is not None else None
        ),
        "test_results": dict(test_results) if test_results is not None else None,
    }


def write_cv_receipt(
    receipt_path: str | Path,
    *,
    dropbox_path: str | Path | None = None,
    splitter_verification: Mapping[str, Any] | None = None,
    pruner_verification: Mapping[str, Any] | None = None,
    budget_verification: Mapping[str, Any] | None = None,
    model_registry_verification: Mapping[str, Any] | None = None,
    test_results: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Write Wave 1B `w4-m1-cv` receipt atomically (LF, 0 BOM) to audit & dropbox paths."""
    payload = build_cv_receipt(
        splitter_verification=splitter_verification,
        pruner_verification=pruner_verification,
        budget_verification=budget_verification,
        model_registry_verification=model_registry_verification,
        test_results=test_results,
    )
    _atomic_write_json(Path(receipt_path), payload)
    if dropbox_path is not None:
        _atomic_write_json(Path(dropbox_path), payload)
    return payload


__all__ = [
    "CONSUMED_CLB_TAG",
    "DEFAULT_BASE_COST_R",
    "DEFAULT_BASELINE_SLIPPAGE_BREAKEVEN",
    "DEFAULT_EMBARGO_DAYS",
    "DEFAULT_MAX_ML_TRIALS",
    "DEFAULT_MAX_SELECTED_FEATURES",
    "DEFAULT_MIN_ENGINE_RETENTION",
    "DEFAULT_MIN_OVERALL_RETENTION",
    "DEFAULT_MIN_SELECTED_FEATURES",
    "DEFAULT_MIN_TRAIN_SAMPLES",
    "DEFAULT_ML_BUDGET_DB_PATH",
    "DEFAULT_PURGE_DAYS",
    "DEFAULT_SLIPPAGE_MULTS",
    "DEFAULT_TABLE_NAME",
    "DEFAULT_TARGET_SLIPPAGE_BREAKEVEN",
    "DEV_CUTOFF_DATE",
    "DEV_CUTOFF_SEC",
    "HOLDOUT_CUTOFF_DATE",
    "MIN_EMBARGO_DAYS",
    "MIN_PURGE_DAYS",
    "MODEL_FAMILIES",
    "MODEL_FAMILY_REGISTRY",
    "MODEL_FAMILY_SPECS",
    "ORDER_SEND_CAPABLE",
    "ORDER_SEND_COUNT",
    "SCHEMA_VERSION",
    "VERDICT_PROMOTE",
    "VERDICT_REJECT",
    "BaseWave4ModelAdapter",
    "BudgetExceededError",
    "CalibratedBetSizingAdapter",
    "CatBoostAdapter",
    "CausalityViolationError",
    "ExpandingPurgedWalkForwardSplitter",
    "FoldAuditMetadata",
    "HoldoutCutoffBreachError",
    "Law13HonestyError",
    "LightGBMAdapter",
    "LogitL2Adapter",
    "RegimeGmmJumpAdapter",
    "Wave4MlBudgetLedger",
    "build_cv_receipt",
    "compute_brier_metrics",
    "compute_exact_roc_auc",
    "create_model_adapter",
    "evaluate_oof_brier_and_economics",
    "list_model_families",
    "run_purged_walkforward_cv",
    "select_inside_fold_features",
    "validate_oos_label",
    "verify_fold_causality",
    "write_cv_receipt",
]

"""Wave 4 Honest 5-Family ML Arena Runner on Sealed `PORT_7E_P28_CORE` Dev (`W4-G04`, `v4.8.1 FINAL`).

Executes a bounded, pre-registered hyperparameter grid (`36 <= 48` trials) across ALL 5 registered
model families from `ml_walkforward_cv.py` on the strictly causal 24-feature matrix (`ml_features_24.py`)
for sealed `PORT_7E_P28_CORE` Dev (`2018-01-02..2024-12-31`, `3,122` trades).

Hard scientific & safety invariants (ZERO exceptions):
  - `ORDER_SEND_CAPABLE = False`, `ORDER_SEND_COUNT = 0`, `0 VND`.
  - Holdout `2025+` SEALED (`HOLDOUT_CUTOFF_DATE = "2024-12-31"`, `DEV_CUTOFF_SEC = 1_735_689_600`,
    `holdout_rows_analysed = 0`). ZERO bare `assert` statements (100% active under `python -O`).
  - LAZY IMPORTS ONLY for optional ML / DB packages (`sklearn`, `lightgbm`, `catboost`, `duckdb`,
    `scipy`, `pandas`). Module top-level depends strictly on Python stdlib + NumPy + Wave 4 causal
    stdlib/NumPy foundations (`ml_features_24`, `ml_walkforward_cv`).
  - Law 13 Honesty: `PORT_7E` Dev Cluster B (`2021-01-01..2024-12-31`) is ALWAYS tagged
    `CONSUMED_DEV_CLB_TEMPORAL_OOS` (fail-closed rejection if any forbidden tag appears in output).
  - Strict DuckDB budget `<= 48` trials in `.runtime/offensive4/ml/wave4_ml_m48.duckdb`.
  - Strict inside-fold discipline (`ExpandingPurgedWalkForwardSplitter(n_splits=5, purge_days=5,
    embargo_days=10)`): every scaler, feature pruner (`8..12` features), GMM/Jump-HMM fitter,
    and calibrator fits strictly inside each training fold.
  - Zero lowering standards: verdict `PROMOTE_V104_ML` ONLY if `>= 1` trial clears ALL hard gates
    (`brier_skill_score > 0`, `roc_auc > 0.50`, 7-engine retention balanced, 1.0x economics improved,
    AND 24m median slippage breakeven lifted to `>= 1.75x` on full OOF AND `2021-2024` temporal OOS).
    Otherwise emits honest `REJECT_ML_KEEP_V103` (`W4-G04` still PASSES honestly) AND still serializes
    the best tree/linear prototype + `500` deterministic `float32` parity vectors tagged
    `RESEARCH_PROTOTYPE_NOT_LIVE_APPROVED` for `w4-m1-onnx-mq5` / `w4-m1-mt5-onnx` (`W4-G05`).
  - CatBoost runs strictly with `allow_writing_files=False` (`0` `catboost_info/` files left behind).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import pickle
import sys
import tempfile
import time
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import numpy as np

from quant_factory.wave4.ml_features_24 import (
    DEV_CUTOFF_DATE,
    DEV_CUTOFF_SEC,
    ENGINE_ID_CODES,
    FEATURE_NAMES_24,
    HOLDOUT_CUTOFF_DATE,
    ORDER_SEND_CAPABLE,
    ORDER_SEND_COUNT,
    _parse_timestamp_array,
    _validate_float_array,
    parse_cutoff_utc_exclusive,
)
from quant_factory.wave4.ml_walkforward_cv import (
    CONSUMED_CLB_TAG,
    DEFAULT_BASE_COST_R,
    DEFAULT_BASELINE_SLIPPAGE_BREAKEVEN,
    DEFAULT_EMBARGO_DAYS,
    DEFAULT_MAX_ML_TRIALS,
    DEFAULT_MAX_SELECTED_FEATURES,
    DEFAULT_MIN_ENGINE_RETENTION,
    DEFAULT_MIN_OVERALL_RETENTION,
    DEFAULT_MIN_SELECTED_FEATURES,
    DEFAULT_MIN_TRAIN_SAMPLES,
    DEFAULT_ML_BUDGET_DB_PATH,
    DEFAULT_PURGE_DAYS,
    DEFAULT_SLIPPAGE_MULTS,
    DEFAULT_TARGET_SLIPPAGE_BREAKEVEN,
    MODEL_FAMILIES,
    VERDICT_PROMOTE,
    VERDICT_REJECT,
    ExpandingPurgedWalkForwardSplitter,
    HoldoutCutoffBreachError,
    Law13HonestyError,
    Wave4MlBudgetLedger,
    _apply_scaler,
    _atomic_write_json,
    _canonical_json_hash,
    _fit_train_scaler,
    _logit,
    create_model_adapter,
    evaluate_oof_brier_and_economics,
    run_purged_walkforward_cv,
    select_inside_fold_features,
    validate_oos_label,
)

# ---------------------------------------------------------------------------
# Hard Safety & Artifact Schema Constants
# ---------------------------------------------------------------------------

SCHEMA_VERSION: str = "naqex-wave4-ml-arena-5families-v1"
RECEIPT_SCHEMA_VERSION: str = "naqex-wave4-m1-arena-receipt-v1"
PROTOTYPE_SCHEMA_VERSION: str = "naqex-wave4-ml-prototype-v1"

TAG_RESEARCH_PROTOTYPE: str = "RESEARCH_PROTOTYPE_NOT_LIVE_APPROVED"
TAG_PROMOTE_CANDIDATE: str = "PROMOTE_V104_ML_PENDING_W4G05_ONNX_PARITY"

CLB_START_DATE: str = "2021-01-01"
CLB_START_SEC: int = 1_609_459_200  # 2021-01-01T00:00:00Z
DEFAULT_PARITY_SAMPLES: int = 500
TECHNICAL_EXPORT_FAMILIES: tuple[str, ...] = ("logit_l2", "lightgbm", "catboost")

ROOT: Path = Path(__file__).resolve().parents[4]
DEFAULT_ML_OUT_DIR: Path = ROOT / ".runtime" / "offensive4" / "ml"
DEFAULT_AUDIT_RECEIPT_PATH: Path = ROOT / ".runtime" / "offensive4" / "audits" / "w4_m1_arena_receipt.json"
DEFAULT_DROPBOX_RECEIPT_PATH: Path = ROOT / ".tmp" / "swarm_dropbox" / "w4-m1-arena.json"

SUMMARY_FILENAME: str = "wave4_ml_arena_summary.json"
PARITY_NPZ_FILENAME: str = "wave4_ml_parity_500.npz"
BEST_PROTOTYPE_NPZ_FILENAME: str = "wave4_ml_best_prototype.npz"
PROTOTYPE_MODEL_PKL_FILENAME: str = "wave4_ml_prototype_model.pkl"
PROTOTYPE_MODEL_JSON_FILENAME: str = "wave4_ml_prototype_model.json"


# ---------------------------------------------------------------------------
# Helpers: Atomic File Writers, SHA-256 & Fail-Closed Guards (ZERO `assert`)
# ---------------------------------------------------------------------------


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65_536), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_report_sha256(payload: Mapping[str, Any]) -> str:
    """Compute canonical SHA-256 over a JSON-serializable summary excluding `report_sha256`."""
    clean = {k: v for k, v in payload.items() if k != "report_sha256"}
    return _canonical_json_hash(clean)


def _assert_zero_forbidden_blind_label(payload: Mapping[str, Any]) -> None:
    """Fail-closed Law 13 guard ensuring emitted artifacts never mislabel Dev OOS."""
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False).upper()
    forbidden = "BL" + "IND"
    if forbidden in raw:
        raise Law13HonestyError(
            f"LAW13_HONESTY_VIOLATION: forbidden tag detected in emitted arena payload; "
            f"all Dev Cluster B temporal OOS references must use {CONSUMED_CLB_TAG!r}"
        )


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


def _atomic_write_npz(path: Path, arrays: Mapping[str, np.ndarray]) -> None:
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
            np.savez(fh, **dict(arrays))
            fh.flush()
            os.fsync(fh.fileno())
            tmp = Path(fh.name)
        os.replace(tmp, path)
        tmp = None
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)


def _json_safe_float(val: Any, *, digits: int = 6) -> float:
    fv = float(val)
    if not math.isfinite(fv):
        raise ValueError(f"NON_FINITE_METRIC: expected finite float, got {val!r}")
    return round(fv, digits)


def _top_attributions_list(
    importance_map: Mapping[str, float],
    *,
    limit: int = 12,
) -> list[dict[str, Any]]:
    items = sorted(
        ((str(k), float(v)) for k, v in importance_map.items()),
        key=lambda kv: (-kv[1], kv[0]),
    )
    return [
        {"rank": idx + 1, "feature": name, "mean_abs_attribution": _json_safe_float(score)}
        for idx, (name, score) in enumerate(items[:limit])
    ]


# ---------------------------------------------------------------------------
# Pre-Registered Bounded 5-Family Hyperparameter Grid (`36 <= 48` Trials)
# ---------------------------------------------------------------------------


def build_preregistered_arena_grid(*, random_state: int = 42) -> list[dict[str, Any]]:
    """Return the pre-registered bounded 36-trial grid across all 5 Wave 4 ML families (`<= 48`).

    Allocation:
      - Family #1 `logit_l2`:              7 trials (4 toxic_filter + 3 continuous)
      - Family #2 `lightgbm`:              7 trials (4 toxic_filter + 3 continuous)
      - Family #3 `catboost`:              7 trials (4 toxic_filter + 3 continuous)
      - Family #4 `regime_gmm_jump`:       7 trials (5 toxic_filter + 2 continuous; GMM + causal Jump-HMM)
      - Family #5 `calibrated_bet_sizing`: 8 trials (Platt & PAVA Isotonic over all 4 base families)
    Total: 36 trials (`<= 48` DuckDB budget, leaving 12 reserve headroom).
    """
    rs = int(random_state)
    grid: list[dict[str, Any]] = [
        # --- Family #1: logit_l2 (7 trials) ---
        {
            "trial_id": "w4_01_logit_l2_tf_r0p5",
            "family_name": "logit_l2",
            "model_params": {"l2_reg": 0.5, "max_iter": 300, "random_state": rs},
            "sizing_mode": "toxic_filter",
            "label": "Logit-L2 C=2.0 toxic_filter",
        },
        {
            "trial_id": "w4_02_logit_l2_tf_r2p0",
            "family_name": "logit_l2",
            "model_params": {"l2_reg": 2.0, "max_iter": 300, "random_state": rs},
            "sizing_mode": "toxic_filter",
            "label": "Logit-L2 C=0.5 toxic_filter",
        },
        {
            "trial_id": "w4_03_logit_l2_tf_r10p0",
            "family_name": "logit_l2",
            "model_params": {"l2_reg": 10.0, "max_iter": 300, "random_state": rs},
            "sizing_mode": "toxic_filter",
            "label": "Logit-L2 C=0.1 toxic_filter",
        },
        {
            "trial_id": "w4_04_logit_l2_tf_r50p0",
            "family_name": "logit_l2",
            "model_params": {"l2_reg": 50.0, "max_iter": 300, "random_state": rs},
            "sizing_mode": "toxic_filter",
            "label": "Logit-L2 C=0.02 toxic_filter",
        },
        {
            "trial_id": "w4_05_logit_l2_cont_r2p0",
            "family_name": "logit_l2",
            "model_params": {"l2_reg": 2.0, "max_iter": 300, "random_state": rs},
            "sizing_mode": "continuous",
            "label": "Logit-L2 C=0.5 continuous",
        },
        {
            "trial_id": "w4_06_logit_l2_cont_r10p0",
            "family_name": "logit_l2",
            "model_params": {"l2_reg": 10.0, "max_iter": 300, "random_state": rs},
            "sizing_mode": "continuous",
            "label": "Logit-L2 C=0.1 continuous",
        },
        {
            "trial_id": "w4_07_logit_l2_cont_r50p0",
            "family_name": "logit_l2",
            "model_params": {"l2_reg": 50.0, "max_iter": 300, "random_state": rs},
            "sizing_mode": "continuous",
            "label": "Logit-L2 C=0.02 continuous",
        },
        # --- Family #2: lightgbm (7 trials) ---
        {
            "trial_id": "w4_08_lgbm_tf_d2_n40",
            "family_name": "lightgbm",
            "model_params": {
                "n_estimators": 40,
                "max_depth": 2,
                "num_leaves": 4,
                "learning_rate": 0.05,
                "min_child_samples": 40,
                "subsample": 0.8,
                "colsample_bytree": 0.8,
                "reg_lambda": 10.0,
                "reg_alpha": 1.0,
                "random_state": rs,
            },
            "sizing_mode": "toxic_filter",
            "label": "LightGBM d2 n40 reg10 toxic_filter",
        },
        {
            "trial_id": "w4_09_lgbm_tf_d2_n60",
            "family_name": "lightgbm",
            "model_params": {
                "n_estimators": 60,
                "max_depth": 2,
                "num_leaves": 4,
                "learning_rate": 0.03,
                "min_child_samples": 50,
                "subsample": 0.8,
                "colsample_bytree": 0.8,
                "reg_lambda": 20.0,
                "reg_alpha": 1.0,
                "random_state": rs,
            },
            "sizing_mode": "toxic_filter",
            "label": "LightGBM d2 n60 reg20 toxic_filter",
        },
        {
            "trial_id": "w4_10_lgbm_tf_d3_n80",
            "family_name": "lightgbm",
            "model_params": {
                "n_estimators": 80,
                "max_depth": 3,
                "num_leaves": 7,
                "learning_rate": 0.05,
                "min_child_samples": 35,
                "subsample": 0.8,
                "colsample_bytree": 0.8,
                "reg_lambda": 5.0,
                "reg_alpha": 0.5,
                "random_state": rs,
            },
            "sizing_mode": "toxic_filter",
            "label": "LightGBM d3 n80 reg5 toxic_filter",
        },
        {
            "trial_id": "w4_11_lgbm_tf_d3_n100",
            "family_name": "lightgbm",
            "model_params": {
                "n_estimators": 100,
                "max_depth": 3,
                "num_leaves": 7,
                "learning_rate": 0.03,
                "min_child_samples": 50,
                "subsample": 0.8,
                "colsample_bytree": 0.8,
                "reg_lambda": 15.0,
                "reg_alpha": 1.0,
                "random_state": rs,
            },
            "sizing_mode": "toxic_filter",
            "label": "LightGBM d3 n100 reg15 toxic_filter",
        },
        {
            "trial_id": "w4_12_lgbm_cont_d2_n60",
            "family_name": "lightgbm",
            "model_params": {
                "n_estimators": 60,
                "max_depth": 2,
                "num_leaves": 4,
                "learning_rate": 0.03,
                "min_child_samples": 50,
                "subsample": 0.8,
                "colsample_bytree": 0.8,
                "reg_lambda": 20.0,
                "reg_alpha": 1.0,
                "random_state": rs,
            },
            "sizing_mode": "continuous",
            "label": "LightGBM d2 n60 reg20 continuous",
        },
        {
            "trial_id": "w4_13_lgbm_cont_d3_n80",
            "family_name": "lightgbm",
            "model_params": {
                "n_estimators": 80,
                "max_depth": 3,
                "num_leaves": 7,
                "learning_rate": 0.05,
                "min_child_samples": 35,
                "subsample": 0.8,
                "colsample_bytree": 0.8,
                "reg_lambda": 5.0,
                "reg_alpha": 0.5,
                "random_state": rs,
            },
            "sizing_mode": "continuous",
            "label": "LightGBM d3 n80 reg5 continuous",
        },
        {
            "trial_id": "w4_14_lgbm_cont_d2_n120",
            "family_name": "lightgbm",
            "model_params": {
                "n_estimators": 120,
                "max_depth": 2,
                "num_leaves": 4,
                "learning_rate": 0.02,
                "min_child_samples": 60,
                "subsample": 0.8,
                "colsample_bytree": 0.8,
                "reg_lambda": 25.0,
                "reg_alpha": 2.0,
                "random_state": rs,
            },
            "sizing_mode": "continuous",
            "label": "LightGBM d2 n120 reg25 continuous",
        },
        # --- Family #3: catboost (7 trials, allow_writing_files=False inside adapter) ---
        {
            "trial_id": "w4_15_catboost_tf_d2_i60",
            "family_name": "catboost",
            "model_params": {
                "iterations": 60,
                "depth": 2,
                "learning_rate": 0.05,
                "l2_leaf_reg": 15.0,
                "min_data_in_leaf": 30,
                "random_state": rs,
            },
            "sizing_mode": "toxic_filter",
            "label": "CatBoost d2 i60 l2=15 toxic_filter",
        },
        {
            "trial_id": "w4_16_catboost_tf_d3_i90",
            "family_name": "catboost",
            "model_params": {
                "iterations": 90,
                "depth": 3,
                "learning_rate": 0.05,
                "l2_leaf_reg": 10.0,
                "min_data_in_leaf": 25,
                "random_state": rs,
            },
            "sizing_mode": "toxic_filter",
            "label": "CatBoost d3 i90 l2=10 toxic_filter",
        },
        {
            "trial_id": "w4_17_catboost_tf_d3_i120",
            "family_name": "catboost",
            "model_params": {
                "iterations": 120,
                "depth": 3,
                "learning_rate": 0.03,
                "l2_leaf_reg": 20.0,
                "min_data_in_leaf": 40,
                "random_state": rs,
            },
            "sizing_mode": "toxic_filter",
            "label": "CatBoost d3 i120 l2=20 toxic_filter",
        },
        {
            "trial_id": "w4_18_catboost_tf_d4_i100",
            "family_name": "catboost",
            "model_params": {
                "iterations": 100,
                "depth": 4,
                "learning_rate": 0.03,
                "l2_leaf_reg": 25.0,
                "min_data_in_leaf": 40,
                "random_state": rs,
            },
            "sizing_mode": "toxic_filter",
            "label": "CatBoost d4 i100 l2=25 toxic_filter",
        },
        {
            "trial_id": "w4_19_catboost_cont_d2_i60",
            "family_name": "catboost",
            "model_params": {
                "iterations": 60,
                "depth": 2,
                "learning_rate": 0.05,
                "l2_leaf_reg": 15.0,
                "min_data_in_leaf": 30,
                "random_state": rs,
            },
            "sizing_mode": "continuous",
            "label": "CatBoost d2 i60 l2=15 continuous",
        },
        {
            "trial_id": "w4_20_catboost_cont_d3_i90",
            "family_name": "catboost",
            "model_params": {
                "iterations": 90,
                "depth": 3,
                "learning_rate": 0.05,
                "l2_leaf_reg": 10.0,
                "min_data_in_leaf": 25,
                "random_state": rs,
            },
            "sizing_mode": "continuous",
            "label": "CatBoost d3 i90 l2=10 continuous",
        },
        {
            "trial_id": "w4_21_catboost_cont_d3_i120",
            "family_name": "catboost",
            "model_params": {
                "iterations": 120,
                "depth": 3,
                "learning_rate": 0.03,
                "l2_leaf_reg": 20.0,
                "min_data_in_leaf": 40,
                "random_state": rs,
            },
            "sizing_mode": "continuous",
            "label": "CatBoost d3 i120 l2=20 continuous",
        },
        # --- Family #4: regime_gmm_jump (7 trials, ZERO hmmlearn) ---
        {
            "trial_id": "w4_22_gmm_tf_k2_a15",
            "family_name": "regime_gmm_jump",
            "model_params": {
                "n_regimes": 2,
                "shrinkage_alpha": 15.0,
                "jump_penalty": 0.0,
                "backend": "gmm",
                "random_state": rs,
            },
            "sizing_mode": "toxic_filter",
            "label": "Regime-GMM k=2 a=15 toxic_filter",
        },
        {
            "trial_id": "w4_23_gmm_tf_k3_a15",
            "family_name": "regime_gmm_jump",
            "model_params": {
                "n_regimes": 3,
                "shrinkage_alpha": 15.0,
                "jump_penalty": 0.0,
                "backend": "gmm",
                "random_state": rs,
            },
            "sizing_mode": "toxic_filter",
            "label": "Regime-GMM k=3 a=15 toxic_filter",
        },
        {
            "trial_id": "w4_24_gmm_tf_k3_a30_jp1",
            "family_name": "regime_gmm_jump",
            "model_params": {
                "n_regimes": 3,
                "shrinkage_alpha": 30.0,
                "jump_penalty": 1.0,
                "backend": "gmm",
                "random_state": rs,
            },
            "sizing_mode": "toxic_filter",
            "label": "Regime-GMM-Jump k=3 a=30 jp=1.0 toxic_filter",
        },
        {
            "trial_id": "w4_25_gmm_tf_k4_a25",
            "family_name": "regime_gmm_jump",
            "model_params": {
                "n_regimes": 4,
                "shrinkage_alpha": 25.0,
                "jump_penalty": 0.0,
                "backend": "gmm",
                "random_state": rs,
            },
            "sizing_mode": "toxic_filter",
            "label": "Regime-GMM k=4 a=25 toxic_filter",
        },
        {
            "trial_id": "w4_26_jumphmm_tf_k3_a20_jp1p5",
            "family_name": "regime_gmm_jump",
            "model_params": {
                "n_regimes": 3,
                "shrinkage_alpha": 20.0,
                "jump_penalty": 1.5,
                "backend": "jump_hmm_numpy",
                "random_state": rs,
            },
            "sizing_mode": "toxic_filter",
            "label": "Causal Jump-HMM k=3 a=20 jp=1.5 toxic_filter",
        },
        {
            "trial_id": "w4_27_gmm_cont_k3_a30_jp1",
            "family_name": "regime_gmm_jump",
            "model_params": {
                "n_regimes": 3,
                "shrinkage_alpha": 30.0,
                "jump_penalty": 1.0,
                "backend": "gmm",
                "random_state": rs,
            },
            "sizing_mode": "continuous",
            "label": "Regime-GMM-Jump k=3 a=30 jp=1.0 continuous",
        },
        {
            "trial_id": "w4_28_jumphmm_cont_k3_a20_jp1p5",
            "family_name": "regime_gmm_jump",
            "model_params": {
                "n_regimes": 3,
                "shrinkage_alpha": 20.0,
                "jump_penalty": 1.5,
                "backend": "jump_hmm_numpy",
                "random_state": rs,
            },
            "sizing_mode": "continuous",
            "label": "Causal Jump-HMM k=3 a=20 jp=1.5 continuous",
        },
        # --- Family #5: calibrated_bet_sizing (8 trials, inside-fold Platt & PAVA Isotonic) ---
        {
            "trial_id": "w4_29_cal_logit10_platt_025_125",
            "family_name": "calibrated_bet_sizing",
            "model_params": {
                "base_family": "logit_l2",
                "base_params": {"l2_reg": 10.0, "max_iter": 300},
                "calibration_method": "platt",
                "calibration_frac": 0.25,
                "size_floor": 0.25,
                "size_cap": 1.25,
                "random_state": rs,
            },
            "sizing_mode": "afml_bet_sizing",
            "label": "Calibrated(Logit10, Platt) AFML [0.25, 1.25]",
        },
        {
            "trial_id": "w4_30_cal_logit50_platt_050_125",
            "family_name": "calibrated_bet_sizing",
            "model_params": {
                "base_family": "logit_l2",
                "base_params": {"l2_reg": 50.0, "max_iter": 300},
                "calibration_method": "platt",
                "calibration_frac": 0.25,
                "size_floor": 0.50,
                "size_cap": 1.25,
                "random_state": rs,
            },
            "sizing_mode": "afml_bet_sizing",
            "label": "Calibrated(Logit50, Platt) AFML [0.50, 1.25]",
        },
        {
            "trial_id": "w4_31_cal_logit10_iso_025_125",
            "family_name": "calibrated_bet_sizing",
            "model_params": {
                "base_family": "logit_l2",
                "base_params": {"l2_reg": 10.0, "max_iter": 300},
                "calibration_method": "isotonic",
                "calibration_frac": 0.25,
                "size_floor": 0.25,
                "size_cap": 1.25,
                "random_state": rs,
            },
            "sizing_mode": "afml_bet_sizing",
            "label": "Calibrated(Logit10, Isotonic) AFML [0.25, 1.25]",
        },
        {
            "trial_id": "w4_32_cal_lgbm_platt_025_125",
            "family_name": "calibrated_bet_sizing",
            "model_params": {
                "base_family": "lightgbm",
                "base_params": {
                    "n_estimators": 60,
                    "max_depth": 2,
                    "num_leaves": 4,
                    "learning_rate": 0.03,
                    "min_child_samples": 50,
                    "reg_lambda": 20.0,
                    "reg_alpha": 1.0,
                },
                "calibration_method": "platt",
                "calibration_frac": 0.25,
                "size_floor": 0.25,
                "size_cap": 1.25,
                "random_state": rs,
            },
            "sizing_mode": "afml_bet_sizing",
            "label": "Calibrated(LGBM-d2, Platt) AFML [0.25, 1.25]",
        },
        {
            "trial_id": "w4_33_cal_lgbm_iso_050_125",
            "family_name": "calibrated_bet_sizing",
            "model_params": {
                "base_family": "lightgbm",
                "base_params": {
                    "n_estimators": 80,
                    "max_depth": 3,
                    "num_leaves": 7,
                    "learning_rate": 0.05,
                    "min_child_samples": 35,
                    "reg_lambda": 5.0,
                    "reg_alpha": 0.5,
                },
                "calibration_method": "isotonic",
                "calibration_frac": 0.25,
                "size_floor": 0.50,
                "size_cap": 1.25,
                "random_state": rs,
            },
            "sizing_mode": "afml_bet_sizing",
            "label": "Calibrated(LGBM-d3, Isotonic) AFML [0.50, 1.25]",
        },
        {
            "trial_id": "w4_34_cal_catboost_platt_025_125",
            "family_name": "calibrated_bet_sizing",
            "model_params": {
                "base_family": "catboost",
                "base_params": {
                    "iterations": 90,
                    "depth": 3,
                    "learning_rate": 0.05,
                    "l2_leaf_reg": 10.0,
                    "min_data_in_leaf": 25,
                },
                "calibration_method": "platt",
                "calibration_frac": 0.25,
                "size_floor": 0.25,
                "size_cap": 1.25,
                "random_state": rs,
            },
            "sizing_mode": "afml_bet_sizing",
            "label": "Calibrated(CatBoost-d3, Platt) AFML [0.25, 1.25]",
        },
        {
            "trial_id": "w4_35_cal_catboost_iso_050_125",
            "family_name": "calibrated_bet_sizing",
            "model_params": {
                "base_family": "catboost",
                "base_params": {
                    "iterations": 120,
                    "depth": 3,
                    "learning_rate": 0.03,
                    "l2_leaf_reg": 20.0,
                    "min_data_in_leaf": 40,
                },
                "calibration_method": "isotonic",
                "calibration_frac": 0.25,
                "size_floor": 0.50,
                "size_cap": 1.25,
                "random_state": rs,
            },
            "sizing_mode": "afml_bet_sizing",
            "label": "Calibrated(CatBoost-d3, Isotonic) AFML [0.50, 1.25]",
        },
        {
            "trial_id": "w4_36_cal_gmm_platt_025_125",
            "family_name": "calibrated_bet_sizing",
            "model_params": {
                "base_family": "regime_gmm_jump",
                "base_params": {
                    "n_regimes": 3,
                    "shrinkage_alpha": 30.0,
                    "jump_penalty": 1.0,
                    "backend": "gmm",
                },
                "calibration_method": "platt",
                "calibration_frac": 0.25,
                "size_floor": 0.25,
                "size_cap": 1.25,
                "random_state": rs,
            },
            "sizing_mode": "afml_bet_sizing",
            "label": "Calibrated(Regime-GMM-Jump, Platt) AFML [0.25, 1.25]",
        },
    ]
    return grid


def build_numpy_smoke_grid(*, random_state: int = 42) -> list[dict[str, Any]]:
    """Minimal 3-trial pure-NumPy grid requiring zero optional ML wheels (for CI offline tests)."""
    rs = int(random_state)
    return [
        {
            "trial_id": "smoke_01_logit_numpy",
            "family_name": "logit_l2",
            "model_params": {"l2_reg": 2.0, "backend": "numpy", "random_state": rs},
            "sizing_mode": "toxic_filter",
            "label": "Smoke Logit-L2 pure-NumPy",
        },
        {
            "trial_id": "smoke_02_jumphmm_numpy",
            "family_name": "regime_gmm_jump",
            "model_params": {
                "n_regimes": 3,
                "shrinkage_alpha": 15.0,
                "jump_penalty": 1.0,
                "backend": "jump_hmm_numpy",
                "random_state": rs,
            },
            "sizing_mode": "toxic_filter",
            "label": "Smoke Jump-HMM pure-NumPy",
        },
        {
            "trial_id": "smoke_03_cal_numpy",
            "family_name": "calibrated_bet_sizing",
            "model_params": {
                "base_family": "logit_l2",
                "base_params": {"l2_reg": 2.0, "backend": "numpy"},
                "calibration_method": "platt",
                "calibration_frac": 0.25,
                "size_floor": 0.25,
                "size_cap": 1.25,
                "random_state": rs,
            },
            "sizing_mode": "afml_bet_sizing",
            "label": "Smoke Calibrated pure-NumPy",
        },
    ]


def validate_arena_grid(
    grid: Sequence[Mapping[str, Any]],
    *,
    max_trials: int = DEFAULT_MAX_ML_TRIALS,
    require_all_five_families: bool = True,
) -> list[dict[str, Any]]:
    """Validate pre-registered arena grid fail-closed against budget and family registry."""
    items = [dict(spec) for spec in grid]
    if not items:
        raise ValueError("EMPTY_ARENA_GRID: at least 1 trial specification is required")
    if len(items) > int(max_trials):
        raise ValueError(f"ARENA_GRID_EXCEEDS_BUDGET: {len(items)} trials > max_trials={max_trials}")

    seen_ids: set[str] = set()
    seen_families: set[str] = set()
    for idx, spec in enumerate(items):
        tid = str(spec.get("trial_id", "")).strip()
        if not tid:
            raise ValueError(f"INVALID_TRIAL_ID at index {idx}")
        if tid in seen_ids:
            raise ValueError(f"DUPLICATE_GRID_TRIAL_ID: {tid!r}")
        seen_ids.add(tid)

        fam = str(spec.get("family_name", "")).strip()
        if fam not in MODEL_FAMILIES:
            raise ValueError(f"UNKNOWN_MODEL_FAMILY at index {idx}: {fam!r}")
        seen_families.add(fam)

        smode = str(spec.get("sizing_mode", "toxic_filter")).strip()
        valid_modes = ("toxic_filter", "continuous", "afml_bet_sizing")
        if smode not in valid_modes:
            raise ValueError(f"INVALID_SIZING_MODE at index {idx}: {smode!r}")
        if smode == "afml_bet_sizing" and fam != "calibrated_bet_sizing":
            raise ValueError(
                f"SIZING_MODE_FAMILY_MISMATCH: afml_bet_sizing requires calibrated_bet_sizing, got {fam!r}"
            )

    if require_all_five_families:
        missing = [fam for fam in MODEL_FAMILIES if fam not in seen_families]
        if missing:
            raise ValueError(f"INCOMPLETE_5FAMILY_GRID: missing families {missing}")
    return items


# ---------------------------------------------------------------------------
# Prototype Model Fitting, Inspection & Serialization (`W4-G05` Handoff)
# ---------------------------------------------------------------------------


def _extract_whitebox_model_dump(
    adapter: Any,
    *,
    family_name: str,
    selected_feature_names: Sequence[str],
    scaler_mean: np.ndarray,
    scaler_std: np.ndarray,
) -> dict[str, Any]:
    """Serialize auditable white-box coefficients or tree structure (zero stray files on disk)."""
    if family_name == "logit_l2":
        w_std = np.asarray(adapter._w, dtype=np.float64)
        b_std = float(adapter._b)
        mu = np.asarray(adapter._mu, dtype=np.float64)
        sd = np.asarray(adapter._sd, dtype=np.float64)
        w_raw = w_std / sd
        b_raw = b_std - float(np.dot(w_std, mu / sd))
        return {
            "representation": "linear_logistic_whitebox",
            "backend": str(getattr(adapter, "_used_backend", "numpy")),
            "formula": "p = 1 / (1 + exp(-(dot((x - scaler_mean) / scaler_std, coef_std) + intercept_std)))",
            "coefficients_std": [float(v) for v in w_std.tolist()],
            "intercept_std": float(b_std),
            "coefficients_raw": [float(v) for v in w_raw.tolist()],
            "intercept_raw": float(b_raw),
            "named_coefficients_std": {
                selected_feature_names[j]: _json_safe_float(w_std[j]) for j in range(len(selected_feature_names))
            },
        }

    if family_name == "lightgbm":
        booster = adapter._model.booster_
        dump_obj = booster.dump_model()
        return {
            "representation": "lightgbm_tree_ensemble",
            "num_trees": int(booster.num_trees()),
            "objective": str(dump_obj.get("objective", "binary")),
            "tree_dump": dump_obj,
        }

    if family_name == "catboost":
        tmp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                prefix="w4_cb_dump_",
                suffix=".json",
                delete=False,
            ) as fh:
                tmp_path = Path(fh.name)
            adapter._model.save_model(str(tmp_path), format="json")
            cb_json = json.loads(tmp_path.read_text(encoding="utf-8"))
        finally:
            if tmp_path is not None:
                tmp_path.unlink(missing_ok=True)
        return {
            "representation": "catboost_oblivious_trees",
            "tree_count": int(adapter._model.tree_count_),
            "model_json": cb_json,
        }

    return {
        "representation": f"{family_name}_adapter",
        "scaler_mean": [float(v) for v in scaler_mean.tolist()],
        "scaler_std": [float(v) for v in scaler_std.tolist()],
    }


def _build_sklearn_export_estimator(
    adapter: Any,
    *,
    family_name: str,
    x_train_sel_f32: np.ndarray,
    y_train: np.ndarray,
) -> Any:
    """Return raw estimator/Pipeline suitable for `skl2onnx` / `onnxmltools` / `catboost` ONNX export."""
    if family_name == "logit_l2":
        if getattr(adapter, "_sklearn_model", None) is not None:
            try:
                from sklearn.pipeline import Pipeline  # Lazy import ONLY
                from sklearn.preprocessing import StandardScaler  # Lazy import ONLY

                scaler = StandardScaler()
                scaler.fit(x_train_sel_f32.astype(np.float64))
                # Ensure exact scale match with adapter's safe std guard
                scaler.mean_ = np.asarray(adapter._mu, dtype=np.float64).copy()
                scaler.scale_ = np.asarray(adapter._sd, dtype=np.float64).copy()
                scaler.var_ = scaler.scale_ ** 2
                return Pipeline([("scaler", scaler), ("clf", adapter._sklearn_model)])
            except ImportError:
                return None
        return None
    if family_name == "lightgbm":
        return getattr(adapter, "_model", None)
    if family_name == "catboost":
        return getattr(adapter, "_model", None)
    return None


def _select_parity_indices(
    val_idx_last: np.ndarray,
    oof_indices: np.ndarray,
    n_parity_samples: int,
    *,
    random_state: int,
) -> tuple[np.ndarray, str]:
    """Deterministically select `n_parity_samples` pre-cutoff Dev indices for `W4-G05` ONNX/MQL5 parity."""
    if val_idx_last.size >= n_parity_samples:
        return np.ascontiguousarray(val_idx_last[:n_parity_samples], dtype=np.int64), "strict_final_fold_oos"
    if oof_indices.size >= n_parity_samples:
        # Take final fold validation first, then latest preceding OOF rows
        extra_needed = n_parity_samples - int(val_idx_last.size)
        val_set = set(val_idx_last.tolist())
        preceding = [int(i) for i in oof_indices.tolist() if i not in val_set]
        chosen = preceding[-extra_needed:] + val_idx_last.tolist()
        return np.asarray(chosen, dtype=np.int64), "chronological_oof_padded"
    # Tiny synthetic test dataset fallback: deterministic bootstrap over OOF pool
    rng = np.random.default_rng(random_state + 997)
    pool = val_idx_last if val_idx_last.size > 0 else oof_indices
    chosen = rng.choice(pool, size=n_parity_samples, replace=True)
    return np.ascontiguousarray(chosen, dtype=np.int64), "synthetic_oof_bootstrap"


def _select_prototype_candidate(
    trial_records: Sequence[Mapping[str, Any]],
    *,
    overall_verdict: str,
) -> dict[str, Any]:
    """Choose best ONNX/MQL5-exportable tree/linear prototype (or winning promoted trial)."""
    if overall_verdict == VERDICT_PROMOTE:
        promoted = [t for t in trial_records if t["verdict"] == VERDICT_PROMOTE]
        promoted_tech = [t for t in promoted if t["family_name"] in TECHNICAL_EXPORT_FAMILIES]
        pool = promoted_tech if promoted_tech else promoted
    else:
        tech = [t for t in trial_records if t["family_name"] in TECHNICAL_EXPORT_FAMILIES]
        pool = tech if tech else list(trial_records)

    best = max(
        pool,
        key=lambda t: (
            float(t["brier_skill_score"]),
            float(t["roc_auc"]),
            float(t["slippage_breakeven_24m"]),
            float(t["pf_1x"]),
        ),
    )

    # If the best promoted trial is calibrated_bet_sizing, unwrap its tree/linear base for clean ONNX export
    fam = str(best["family_name"])
    params = dict(best["model_params"])
    if fam == "calibrated_bet_sizing":
        base_fam = str(params.get("base_family", "logit_l2"))
        if base_fam in TECHNICAL_EXPORT_FAMILIES:
            base_params = dict(params.get("base_params", {}))
            base_params.setdefault("random_state", int(params.get("random_state", 42)))
            return {
                "source_trial_id": str(best["trial_id"]),
                "source_family_name": fam,
                "export_family_name": base_fam,
                "export_model_params": base_params,
                "source_brier_skill_score": float(best["brier_skill_score"]),
                "source_roc_auc": float(best["roc_auc"]),
                "source_verdict": str(best["verdict"]),
            }

    return {
        "source_trial_id": str(best["trial_id"]),
        "source_family_name": fam,
        "export_family_name": fam,
        "export_model_params": params,
        "source_brier_skill_score": float(best["brier_skill_score"]),
        "source_roc_auc": float(best["roc_auc"]),
        "source_verdict": str(best["verdict"]),
    }


def fit_and_serialize_prototype(
    X: np.ndarray,
    y: np.ndarray,
    entry_ts: np.ndarray,
    exit_ts: np.ndarray,
    *,
    feature_names: Sequence[str],
    splitter_cfg: Mapping[str, Any],
    candidate: Mapping[str, Any],
    overall_verdict: str,
    out_dir: Path,
    min_k: int = DEFAULT_MIN_SELECTED_FEATURES,
    max_k: int = DEFAULT_MAX_SELECTED_FEATURES,
    n_parity_samples: int = DEFAULT_PARITY_SAMPLES,
    cutoff_utc: str | date | datetime | int = HOLDOUT_CUTOFF_DATE,
    random_state: int = 42,
) -> dict[str, Any]:
    """Fit the selected technical prototype strictly on final Dev fold train set & export 500 parity vectors."""
    cutoff_sec = parse_cutoff_utc_exclusive(cutoff_utc)
    if int(np.max(entry_ts)) >= cutoff_sec or int(np.max(exit_ts)) >= cutoff_sec:
        raise HoldoutCutoffBreachError(
            f"HOLDOUT_BREACH_PROTOTYPE: timestamps >= cutoff_sec_exclusive={cutoff_sec}"
        )

    splitter = ExpandingPurgedWalkForwardSplitter(
        n_splits=int(splitter_cfg["n_splits"]),
        purge_days=int(splitter_cfg["purge_days"]),
        embargo_days=int(splitter_cfg["embargo_days"]),
        min_train_samples=int(splitter_cfg["min_train_samples"]),
        mode=str(splitter_cfg.get("mode", "expanding")),
        rolling_window_days=splitter_cfg.get("rolling_window_days"),
        cutoff_utc=cutoff_utc,
    )
    folds = list(splitter.split(entry_ts, exit_ts, cutoff_utc=cutoff_utc))
    train_idx_last, val_idx_last = folds[-1]
    oof_all = np.concatenate([va for _, va in folds])

    # Strictly inside final training fold: feature selection + train-only standardization
    pruning = select_inside_fold_features(
        X[train_idx_last],
        y[train_idx_last],
        feature_names=feature_names,
        min_k=min_k,
        max_k=max_k,
    )
    sel_idx = [int(i) for i in pruning["selected_indices"]]
    sel_names = [str(nm) for nm in pruning["selected_names"]]
    k_sel = len(sel_idx)
    if not (min_k <= k_sel <= max_k):
        raise ValueError(f"INVALID_SELECTED_FEATURE_COUNT: k={k_sel} outside [{min_k}, {max_k}]")

    x_train_sel = np.ascontiguousarray(X[train_idx_last][:, sel_idx], dtype=np.float32)
    y_train_last = np.asarray(y[train_idx_last], dtype=np.float64)
    scaler_mu, scaler_sd = _fit_train_scaler(x_train_sel.astype(np.float64))

    export_fam = str(candidate["export_family_name"])
    export_params = dict(candidate["export_model_params"])
    adapter = create_model_adapter(export_fam, **export_params)
    adapter.fit(x_train_sel.astype(np.float64), y_train_last, feature_names=sel_names)

    # Also fit white-box linear reference on identical final-fold train slice for dual ONNX/MQL5 verification
    ref_backend = "numpy" if export_fam == "logit_l2" and export_params.get("backend") == "numpy" else "auto"
    linear_ref = create_model_adapter(
        "logit_l2",
        l2_reg=10.0,
        max_iter=300,
        backend=ref_backend,
        random_state=random_state,
    )
    linear_ref.fit(x_train_sel.astype(np.float64), y_train_last, feature_names=sel_names)

    parity_idx, parity_source = _select_parity_indices(
        val_idx_last,
        oof_all,
        n_parity_samples,
        random_state=random_state,
    )
    parity_entry_ts = np.ascontiguousarray(entry_ts[parity_idx], dtype=np.int64)
    if int(np.max(parity_entry_ts)) >= cutoff_sec:
        raise HoldoutCutoffBreachError("HOLDOUT_BREACH_PARITY_VECTORS: parity vector timestamp >= 2025-01-01")

    x_parity_24 = np.ascontiguousarray(X[parity_idx], dtype=np.float32)
    x_parity_sel = np.ascontiguousarray(x_parity_24[:, sel_idx], dtype=np.float32)
    x_parity_std = np.ascontiguousarray(
        _apply_scaler(x_parity_sel.astype(np.float64), scaler_mu, scaler_sd),
        dtype=np.float32,
    )
    y_parity = np.ascontiguousarray(y[parity_idx], dtype=np.float32)

    # Evaluate on exact float32 features promoted to float64 so ONNX/MQL5 float32 parity is exact
    p_parity_f64 = np.ascontiguousarray(adapter.predict_proba(x_parity_sel.astype(np.float64)), dtype=np.float64)
    p_parity_f32 = np.ascontiguousarray(p_parity_f64, dtype=np.float32)
    logit_parity_f32 = np.ascontiguousarray(_logit(p_parity_f64), dtype=np.float32)
    size_parity_f32 = np.ascontiguousarray(
        adapter.predict_size(x_parity_sel.astype(np.float64), mode="toxic_filter"),
        dtype=np.float32,
    )
    p_linref_f32 = np.ascontiguousarray(
        linear_ref.predict_proba(x_parity_sel.astype(np.float64)),
        dtype=np.float32,
    )

    if x_parity_sel.shape != (n_parity_samples, k_sel) or x_parity_sel.dtype != np.float32:
        raise ValueError(
            f"INVALID_PARITY_ARRAY: expected ({n_parity_samples}, {k_sel}) float32, "
            f"got {x_parity_sel.shape} {x_parity_sel.dtype}"
        )
    if not bool(np.all(np.isfinite(x_parity_sel))) or not bool(np.all(np.isfinite(p_parity_f32))):
        raise ValueError("NON_FINITE_PARITY_OUTPUT: NaN/Inf detected in parity vectors or probabilities")
    if float(np.min(p_parity_f32)) <= 0.0 or float(np.max(p_parity_f32)) >= 1.0:
        raise ValueError("OUT_OF_RANGE_PARITY_PROBABILITY: expected strictly inside (0, 1)")

    approval_tag = TAG_PROMOTE_CANDIDATE if overall_verdict == VERDICT_PROMOTE else TAG_RESEARCH_PROTOTYPE

    npz_arrays: dict[str, np.ndarray] = {
        "X": x_parity_sel,
        "X_full_24": x_parity_24,
        "X_standardized": x_parity_std,
        "y_true": y_parity,
        "pred_proba": p_parity_f32,
        "pred_proba_f64": p_parity_f64,
        "pred_logit": logit_parity_f32,
        "pred_size_toxic_filter": size_parity_f32,
        "linear_ref_pred_proba": p_linref_f32,
        "selected_feature_indices": np.asarray(sel_idx, dtype=np.int32),
        "selected_feature_names": np.asarray(sel_names, dtype="U64"),
        "scaler_mean": np.asarray(scaler_mu, dtype=np.float32),
        "scaler_std": np.asarray(scaler_sd, dtype=np.float32),
        "entry_ts": parity_entry_ts,
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    parity_npz_path = out_dir / PARITY_NPZ_FILENAME
    best_proto_npz_path = out_dir / BEST_PROTOTYPE_NPZ_FILENAME
    proto_json_path = out_dir / PROTOTYPE_MODEL_JSON_FILENAME
    proto_pkl_path = out_dir / PROTOTYPE_MODEL_PKL_FILENAME

    _atomic_write_npz(parity_npz_path, npz_arrays)
    _atomic_write_npz(best_proto_npz_path, npz_arrays)

    parity_sha = sha256_file(parity_npz_path)
    best_proto_sha = sha256_file(best_proto_npz_path)

    whitebox_dump = _extract_whitebox_model_dump(
        adapter,
        family_name=export_fam,
        selected_feature_names=sel_names,
        scaler_mean=scaler_mu,
        scaler_std=scaler_sd,
    )
    linear_ref_dump = _extract_whitebox_model_dump(
        linear_ref,
        family_name="logit_l2",
        selected_feature_names=sel_names,
        scaler_mean=scaler_mu,
        scaler_std=scaler_sd,
    )

    proto_json_payload: dict[str, Any] = {
        "schema_version": PROTOTYPE_SCHEMA_VERSION,
        "generated_utc": datetime.now(UTC).isoformat(),
        "order_send_capable": ORDER_SEND_CAPABLE,
        "order_send_count": ORDER_SEND_COUNT,
        "holdout_cutoff_date": HOLDOUT_CUTOFF_DATE,
        "holdout_rows_analysed": 0,
        "oos_label": CONSUMED_CLB_TAG,
        "arena_verdict": overall_verdict,
        "approval_tag": approval_tag,
        "source_trial_id": str(candidate["source_trial_id"]),
        "source_family_name": str(candidate["source_family_name"]),
        "family_name": export_fam,
        "model_params": export_params,
        "train_fold_summary": {
            "fold_index": len(folds) - 1,
            "n_train": int(train_idx_last.size),
            "n_val": int(val_idx_last.size),
            "train_max_exit_ts": int(np.max(exit_ts[train_idx_last])),
            "val_min_entry_ts": int(np.min(entry_ts[val_idx_last])),
        },
        "n_features_selected": k_sel,
        "selected_feature_indices": sel_idx,
        "selected_feature_names": sel_names,
        "scaler_mean": [float(v) for v in scaler_mu.tolist()],
        "scaler_std": [float(v) for v in scaler_sd.tolist()],
        "train_base_rate": _json_safe_float(adapter._train_base_rate),
        "train_p_toxic_q20": _json_safe_float(adapter._train_p_toxic),
        "train_p_lo_q10": _json_safe_float(adapter._train_p_lo),
        "train_p_hi_q90": _json_safe_float(adapter._train_p_hi),
        "parity_vectors": {
            "n_samples": n_parity_samples,
            "shape": [n_parity_samples, k_sel],
            "dtype": "float32",
            "source": parity_source,
            "parity_500_npz": str(parity_npz_path),
            "parity_500_sha256": parity_sha,
            "best_prototype_npz": str(best_proto_npz_path),
            "best_prototype_sha256": best_proto_sha,
            "pred_proba_min": _json_safe_float(float(np.min(p_parity_f32))),
            "pred_proba_mean": _json_safe_float(float(np.mean(p_parity_f32))),
            "pred_proba_max": _json_safe_float(float(np.max(p_parity_f32))),
        },
        "model_whitebox": whitebox_dump,
        "linear_reference_logit_l2": linear_ref_dump,
    }
    _assert_zero_forbidden_blind_label(proto_json_payload)
    _atomic_write_json(proto_json_path, proto_json_payload)
    proto_json_sha = sha256_file(proto_json_path)

    raw_estimator = _build_sklearn_export_estimator(
        adapter,
        family_name=export_fam,
        x_train_sel_f32=x_parity_sel if x_train_sel.shape[0] == 0 else x_train_sel,
        y_train=y_train_last,
    )
    pkl_bundle = {
        "schema_version": PROTOTYPE_SCHEMA_VERSION,
        "approval_tag": approval_tag,
        "arena_verdict": overall_verdict,
        "oos_label": CONSUMED_CLB_TAG,
        "holdout_cutoff_date": HOLDOUT_CUTOFF_DATE,
        "holdout_rows_analysed": 0,
        "order_send_count": ORDER_SEND_COUNT,
        "source_trial_id": str(candidate["source_trial_id"]),
        "family_name": export_fam,
        "model_params": export_params,
        "selected_feature_indices": sel_idx,
        "selected_feature_names": sel_names,
        "scaler_mean": scaler_mu.astype(np.float32),
        "scaler_std": scaler_sd.astype(np.float32),
        "adapter": adapter,
        "raw_estimator": raw_estimator,
        "linear_reference_adapter": linear_ref,
        "parity_500_sha256": parity_sha,
    }
    _atomic_write_bytes(proto_pkl_path, pickle.dumps(pkl_bundle, protocol=pickle.HIGHEST_PROTOCOL))
    proto_pkl_sha = sha256_file(proto_pkl_path)

    return {
        "approval_tag": approval_tag,
        "source_trial_id": str(candidate["source_trial_id"]),
        "source_family_name": str(candidate["source_family_name"]),
        "export_family_name": export_fam,
        "export_model_params": export_params,
        "n_features_selected": k_sel,
        "selected_feature_indices": sel_idx,
        "selected_feature_names": sel_names,
        "scaler_mean": [_json_safe_float(v) for v in scaler_mu.tolist()],
        "scaler_std": [_json_safe_float(v) for v in scaler_sd.tolist()],
        "parity_shape": [n_parity_samples, k_sel],
        "parity_dtype": "float32",
        "parity_source": parity_source,
        "parity_500_npz": str(parity_npz_path),
        "parity_500_sha256": parity_sha,
        "best_prototype_npz": str(best_proto_npz_path),
        "best_prototype_sha256": best_proto_sha,
        "prototype_model_json": str(proto_json_path),
        "prototype_model_json_sha256": proto_json_sha,
        "prototype_model_pkl": str(proto_pkl_path),
        "prototype_model_pkl_sha256": proto_pkl_sha,
    }


# ---------------------------------------------------------------------------
# Core 5-Family ML Arena Orchestrator (Offline Synthetic & Real PORT_7E Dev)
# ---------------------------------------------------------------------------


def _compact_trial_record(
    *,
    trial_spec: Mapping[str, Any],
    wf_res: Mapping[str, Any],
    evaluation: Mapping[str, Any],
    clb_eval: Mapping[str, Any] | None,
    ledger_receipt: Mapping[str, Any] | None,
    runtime_sec: float,
) -> dict[str, Any]:
    prob = evaluation["probabilistic_metrics"]
    eb = evaluation["engine_balance"]
    e1x = evaluation["economics_1x"]
    sb = evaluation["slippage_breakeven_24m"]
    avg_k = int(round(float(np.mean([f["n_features_selected"] for f in wf_res["folds"]]))))

    clb_compact: dict[str, Any] | None = None
    if clb_eval is not None:
        clb_compact = {
            "n_trades": int(clb_eval["n_trades"]),
            "oos_label": str(clb_eval["oos_label"]),
            "brier_skill_score": _json_safe_float(clb_eval["brier_skill_score"]),
            "roc_auc": _json_safe_float(clb_eval["roc_auc"]),
            "min_engine_retention_ratio": _json_safe_float(clb_eval["engine_balance"]["min_engine_retention_ratio"]),
            "overall_retention_ratio": _json_safe_float(clb_eval["engine_balance"]["overall_retention_ratio"]),
            "baseline_v103_24m_be": _json_safe_float(clb_eval["slippage_breakeven_24m"]["baseline_v103_median_mult"]),
            "ml_v104_24m_be": _json_safe_float(clb_eval["slippage_breakeven_24m"]["ml_v104_median_mult"]),
            "pf_1x": _json_safe_float(clb_eval["economics_1x"]["ml_v104"]["profit_factor"]),
            "ev_r_1x": _json_safe_float(clb_eval["economics_1x"]["ml_v104"]["ev_r"]),
            "max_dd_pct_1x": _json_safe_float(clb_eval["economics_1x"]["ml_v104"]["max_dd_pct"]),
            "verdict": str(clb_eval["verdict"]),
            "gates": dict(clb_eval["gates"]),
            "rejection_reasons": list(clb_eval["rejection_reasons"]),
        }

    return {
        "trial_seq": int(ledger_receipt["trial_seq"]) if ledger_receipt is not None else 0,
        "trial_id": str(trial_spec["trial_id"]),
        "family_name": str(trial_spec["family_name"]),
        "label": str(trial_spec.get("label", trial_spec["trial_id"])),
        "sizing_mode": str(trial_spec["sizing_mode"]),
        "model_params": dict(trial_spec["model_params"]),
        "oos_label": str(evaluation["oos_label"]),
        "n_folds": len(wf_res["folds"]),
        "n_oof_samples": int(wf_res["n_oof_samples"]),
        "n_features_selected_avg": avg_k,
        "fold_feature_counts": [int(f["n_features_selected"]) for f in wf_res["folds"]],
        "brier_model": _json_safe_float(prob["brier_model"]),
        "brier_climatology": _json_safe_float(prob["brier_climatology"]),
        "brier_skill_score": _json_safe_float(evaluation["brier_skill_score"]),
        "logloss": _json_safe_float(prob["logloss"]),
        "roc_auc": _json_safe_float(evaluation["roc_auc"]),
        "min_engine_retention_ratio": _json_safe_float(eb["min_engine_retention_ratio"]),
        "overall_retention_ratio": _json_safe_float(eb["overall_retention_ratio"]),
        "dropped_engines": list(eb["dropped_engines"]),
        "per_engine_retention": dict(eb["per_engine_retention"]),
        "pf_1x": _json_safe_float(e1x["ml_v104"]["profit_factor"]),
        "ev_r_1x": _json_safe_float(e1x["ml_v104"]["ev_r"]),
        "win_rate_1x": _json_safe_float(e1x["ml_v104"]["win_rate"]),
        "max_dd_pct_1x": _json_safe_float(e1x["ml_v104"]["max_dd_pct"]),
        "baseline_pf_1x": _json_safe_float(e1x["baseline_v103"]["profit_factor"]),
        "baseline_ev_r_1x": _json_safe_float(e1x["baseline_v103"]["ev_r"]),
        "baseline_max_dd_pct_1x": _json_safe_float(e1x["baseline_v103"]["max_dd_pct"]),
        "baseline_slippage_breakeven_24m": _json_safe_float(sb["baseline_v103_median_mult"]),
        "slippage_breakeven_24m": _json_safe_float(sb["ml_v104_median_mult"]),
        "delta_slippage_breakeven_24m": _json_safe_float(sb["delta_median_mult"]),
        "slippage_stress_curve": dict(evaluation["slippage_stress_curve"]),
        "clb_2021_2024_temporal_oos": clb_compact,
        "top_shap_features": _top_attributions_list(wf_res["oof_feature_importance"], limit=12),
        "gates": dict(evaluation["gates"]),
        "rejection_reasons": list(evaluation["rejection_reasons"]),
        "verdict": str(evaluation["verdict"]),
        "runtime_seconds": _json_safe_float(runtime_sec, digits=3),
    }


def _compute_consensus_shap(trial_records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Aggregate normalized feature attribution ranks across best trial per family."""
    accum: dict[str, float] = {}
    counts: dict[str, int] = {}
    for rec in trial_records:
        top_list = rec.get("top_shap_features", [])
        if not top_list:
            continue
        max_val = max((float(x["mean_abs_attribution"]) for x in top_list), default=0.0)
        if max_val <= 1e-12:
            continue
        for item in top_list:
            fname = str(item["feature"])
            norm_v = float(item["mean_abs_attribution"]) / max_val
            accum[fname] = accum.get(fname, 0.0) + norm_v
            counts[fname] = counts.get(fname, 0) + 1
    ranked = sorted(
        ((fname, accum[fname] / float(counts[fname]), counts[fname]) for fname in accum),
        key=lambda x: (-x[1], -x[2], x[0]),
    )
    return [
        {
            "rank": idx + 1,
            "feature": fname,
            "mean_normalized_attribution": _json_safe_float(score),
            "families_appearing": int(cnt),
        }
        for idx, (fname, score, cnt) in enumerate(ranked[:12])
    ]


def run_5family_ml_arena(
    X: np.ndarray,
    y: np.ndarray,
    entry_ts: Any,
    exit_ts: Any,
    net_r: np.ndarray | Sequence[float],
    engine_ids: Sequence[Any],
    *,
    feature_names: Sequence[str] = FEATURE_NAMES_24,
    trial_grid: Sequence[Mapping[str, Any]] | None = None,
    require_all_five_families: bool = True,
    db_path: str | Path = DEFAULT_ML_BUDGET_DB_PATH,
    max_trials: int = DEFAULT_MAX_ML_TRIALS,
    out_dir: str | Path = DEFAULT_ML_OUT_DIR,
    n_splits: int = 5,
    purge_days: int = DEFAULT_PURGE_DAYS,
    embargo_days: int = DEFAULT_EMBARGO_DAYS,
    min_train_samples: int = DEFAULT_MIN_TRAIN_SAMPLES,
    min_k: int = DEFAULT_MIN_SELECTED_FEATURES,
    max_k: int = DEFAULT_MAX_SELECTED_FEATURES,
    slippage_mults: Sequence[float] = DEFAULT_SLIPPAGE_MULTS,
    base_cost_r: np.ndarray | Sequence[float] | float = DEFAULT_BASE_COST_R,
    risk_pct_per_trade: np.ndarray | Sequence[float] | float | None = None,
    oos_label: str = CONSUMED_CLB_TAG,
    cutoff_utc: str | date | datetime | int = HOLDOUT_CUTOFF_DATE,
    n_parity_samples: int = DEFAULT_PARITY_SAMPLES,
    dataset_name: str = "PORT_7E_P28_CORE_DEV_2018_2024",
    portfolio_key: str = "PORT_7E_P28_CORE",
    holdout_lock_sha256: str | None = None,
    random_state: int = 42,
    use_duckdb_ledger: bool = True,
) -> dict[str, Any]:
    """Execute the bounded 5-family ML arena with strict inside-fold discipline & honest verdicts."""
    t0 = time.perf_counter()
    validated_oos = validate_oos_label(oos_label)
    cutoff_sec = parse_cutoff_utc_exclusive(cutoff_utc)

    x_arr = np.ascontiguousarray(_validate_float_array(X, name="X"), dtype=np.float32)
    y_arr = _validate_float_array(y, name="y")
    r_arr = _validate_float_array(net_r, name="net_r")
    ent_arr = _parse_timestamp_array(entry_ts, name="entry_ts")
    ext_arr = _parse_timestamp_array(exit_ts, name="exit_ts")

    n_rows = int(x_arr.shape[0])
    if x_arr.ndim != 2 or n_rows == 0:
        raise ValueError(f"INVALID_X_SHAPE: expected non-empty 2D matrix, got {x_arr.shape}")
    if y_arr.size != n_rows or r_arr.size != n_rows or ent_arr.size != n_rows or ext_arr.size != n_rows:
        raise ValueError("INPUT_LENGTH_MISMATCH across X, y, net_r, entry_ts, exit_ts")
    if len(engine_ids) != n_rows:
        raise ValueError(f"ENGINE_IDS_LENGTH_MISMATCH: expected {n_rows}, got {len(engine_ids)}")
    if int(np.max(ent_arr)) >= cutoff_sec or int(np.max(ext_arr)) >= cutoff_sec:
        raise HoldoutCutoffBreachError(
            f"HOLDOUT_TIMESTAMP_BREACH: max(entry_ts)={int(np.max(ent_arr))}, "
            f"max(exit_ts)={int(np.max(ext_arr))} >= cutoff_sec_exclusive={cutoff_sec}"
        )

    raw_grid = build_preregistered_arena_grid(random_state=random_state) if trial_grid is None else trial_grid
    grid = validate_arena_grid(
        raw_grid,
        max_trials=max_trials,
        require_all_five_families=require_all_five_families,
    )

    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    db_file = Path(db_path)

    trial_records: list[dict[str, Any]] = []
    ledger_summary: dict[str, Any] | None = None
    baseline_full_oof: dict[str, Any] | None = None
    baseline_clb_oof: dict[str, Any] | None = None
    splitter_audits: list[dict[str, Any]] = []

    ledger: Wave4MlBudgetLedger | None = None
    try:
        if use_duckdb_ledger:
            ledger = Wave4MlBudgetLedger(db_path=db_file, max_trials=max_trials, cutoff_utc=cutoff_utc)
            rem = ledger.remaining_budget()
            if len(grid) > rem:
                raise ValueError(
                    f"INSUFFICIENT_DUCKDB_BUDGET: grid needs {len(grid)} trials, "
                    f"but ledger {db_file} only has {rem}/{max_trials} remaining"
                )

        for spec in grid:
            t_trial = time.perf_counter()
            wf = run_purged_walkforward_cv(
                x_arr.astype(np.float64),
                y_arr,
                ent_arr,
                ext_arr,
                r_arr,
                engine_ids,
                family_name=str(spec["family_name"]),
                model_params=dict(spec["model_params"]),
                feature_names=feature_names,
                n_splits=n_splits,
                purge_days=purge_days,
                embargo_days=embargo_days,
                min_train_samples=min_train_samples,
                min_k=min_k,
                max_k=max_k,
                sizing_mode=str(spec["sizing_mode"]),
                slippage_mults=slippage_mults,
                base_cost_r=base_cost_r,
                risk_pct_per_trade=risk_pct_per_trade,
                oos_label=validated_oos,
                cutoff_utc=cutoff_utc,
                compute_attributions=True,
                ledger=None,
            )

            evaluation = dict(wf["evaluation"])
            oof_mask = np.asarray(wf["oof_mask"], dtype=bool)
            eval_idx = np.flatnonzero(oof_mask)

            if not splitter_audits:
                splitter_audits = [
                    {
                        "fold_index": int(f["fold_index"]),
                        "n_train": int(f["n_train"]),
                        "n_val": int(f["n_val"]),
                        "n_purged": int(f["n_purged"]),
                        "n_embargoed": int(f["n_embargoed"]),
                        "observed_gap_days": float(f["observed_gap_days"]),
                        "n_features_selected": int(f["n_features_selected"]),
                    }
                    for f in wf["folds"]
                ]

            if baseline_full_oof is None:
                baseline_full_oof = {
                    "n_oof_trades": int(eval_idx.size),
                    "oos_label": validated_oos,
                    "base_cost_r": (
                        float(base_cost_r)
                        if isinstance(base_cost_r, (int, float, np.integer, np.floating))
                        else _json_safe_float(float(np.mean(base_cost_r)))
                    ),
                    "economics_1x": dict(evaluation["economics_1x"]["baseline_v103"]),
                    "slippage_breakeven_24m": _json_safe_float(
                        evaluation["slippage_breakeven_24m"]["baseline_v103_median_mult"]
                    ),
                    "n_windows_24m": int(evaluation["slippage_breakeven_24m"]["n_windows"]),
                }

            # Explicit 2021-2024 CONSUMED_DEV_CLB_TEMPORAL_OOS temporal sub-slice check
            clb_mask = oof_mask & (ent_arr >= CLB_START_SEC)
            clb_idx = np.flatnonzero(clb_mask)
            clb_eval: dict[str, Any] | None = None
            if clb_idx.size >= 100 and len(np.unique(y_arr[clb_idx])) >= 2:
                clb_eng = [engine_ids[i] for i in clb_idx.tolist()]
                clb_cost: Any = (
                    base_cost_r
                    if isinstance(base_cost_r, (int, float, np.integer, np.floating))
                    else np.asarray(base_cost_r, dtype=np.float64)[clb_idx]
                )
                clb_risk: Any = (
                    None
                    if risk_pct_per_trade is None
                    else (
                        risk_pct_per_trade
                        if isinstance(risk_pct_per_trade, (int, float, np.integer, np.floating))
                        else np.asarray(risk_pct_per_trade, dtype=np.float64)[clb_idx]
                    )
                )
                clb_eval = evaluate_oof_brier_and_economics(
                    y_arr[clb_idx],
                    wf["oof_probs"][clb_idx],
                    r_arr[clb_idx],
                    clb_eng,
                    slippage_mults=slippage_mults,
                    position_sizes=wf["oof_sizes"][clb_idx],
                    base_cost_r=clb_cost,
                    risk_pct_per_trade=clb_risk,
                    min_engine_retention_ratio=DEFAULT_MIN_ENGINE_RETENTION,
                    min_overall_retention_ratio=DEFAULT_MIN_OVERALL_RETENTION,
                    baseline_slippage_breakeven=DEFAULT_BASELINE_SLIPPAGE_BREAKEVEN,
                    target_slippage_breakeven=DEFAULT_TARGET_SLIPPAGE_BREAKEVEN,
                    oos_label=validated_oos,
                    entry_ts=ent_arr[clb_idx],
                    cutoff_utc=cutoff_utc,
                )
                if baseline_clb_oof is None:
                    baseline_clb_oof = {
                        "n_oof_trades": int(clb_idx.size),
                        "window": f"{CLB_START_DATE}..{HOLDOUT_CUTOFF_DATE}",
                        "oos_label": validated_oos,
                        "economics_1x": dict(clb_eval["economics_1x"]["baseline_v103"]),
                        "slippage_breakeven_24m": _json_safe_float(
                            clb_eval["slippage_breakeven_24m"]["baseline_v103_median_mult"]
                        ),
                        "n_windows_24m": int(clb_eval["slippage_breakeven_24m"]["n_windows"]),
                    }

                # Strictly tighten (never loosen) promotion: MUST also clear 2021-2024 temporal OOS
                if evaluation["verdict"] == VERDICT_PROMOTE and clb_eval["verdict"] != VERDICT_PROMOTE:
                    reasons = list(evaluation["rejection_reasons"])
                    reasons.append(
                        f"CLB_2021_2024_TEMPORAL_OOS_FAILED ({'; '.join(clb_eval['rejection_reasons'])})"
                    )
                    gates = dict(evaluation["gates"])
                    gates["clb_2021_2024_temporal_oos_passed"] = False
                    evaluation["gates"] = gates
                    evaluation["rejection_reasons"] = reasons
                    evaluation["verdict"] = VERDICT_REJECT
                else:
                    gates = dict(evaluation["gates"])
                    gates["clb_2021_2024_temporal_oos_passed"] = bool(clb_eval["verdict"] == VERDICT_PROMOTE)
                    evaluation["gates"] = gates

            avg_k = int(round(float(np.mean([f["n_features_selected"] for f in wf["folds"]]))))
            receipt_row: dict[str, Any] | None = None
            if ledger is not None:
                receipt_row = ledger.record_trial(
                    trial_id=str(spec["trial_id"]),
                    family_name=str(spec["family_name"]),
                    params=dict(spec["model_params"]),
                    evaluation=evaluation,
                    n_folds=len(wf["folds"]),
                    n_features_selected=avg_k,
                    oos_label=validated_oos,
                    cutoff_utc=cutoff_utc,
                )

            trial_records.append(
                _compact_trial_record(
                    trial_spec=spec,
                    wf_res=wf,
                    evaluation=evaluation,
                    clb_eval=clb_eval,
                    ledger_receipt=receipt_row,
                    runtime_sec=time.perf_counter() - t_trial,
                )
            )

        if ledger is not None:
            ledger_summary = ledger.summary()
    finally:
        if ledger is not None:
            ledger.close()

    # Verify zero stray catboost_info directory was created in CWD
    catboost_info_absent = not (Path.cwd() / "catboost_info").exists()
    if not catboost_info_absent:
        raise RuntimeError("CATBOOST_INFO_LEAK: catboost_info directory unexpectedly created on disk")

    # Build per-family leaderboard (best trial per family)
    family_leaderboard: dict[str, dict[str, Any]] = {}
    for fam in MODEL_FAMILIES:
        fam_trials = [t for t in trial_records if t["family_name"] == fam]
        if not fam_trials:
            continue
        best_fam = max(
            fam_trials,
            key=lambda t: (
                1 if t["verdict"] == VERDICT_PROMOTE else 0,
                float(t["brier_skill_score"]),
                float(t["slippage_breakeven_24m"]),
                float(t["pf_1x"]),
            ),
        )
        family_leaderboard[fam] = {
            "n_trials_run": len(fam_trials),
            "n_trials_promoted": sum(1 for t in fam_trials if t["verdict"] == VERDICT_PROMOTE),
            "best_trial_id": best_fam["trial_id"],
            "best_label": best_fam["label"],
            "best_sizing_mode": best_fam["sizing_mode"],
            "best_model_params": best_fam["model_params"],
            "brier_model": best_fam["brier_model"],
            "brier_climatology": best_fam["brier_climatology"],
            "brier_skill_score": best_fam["brier_skill_score"],
            "logloss": best_fam["logloss"],
            "roc_auc": best_fam["roc_auc"],
            "n_features_selected_avg": best_fam["n_features_selected_avg"],
            "min_engine_retention_ratio": best_fam["min_engine_retention_ratio"],
            "overall_retention_ratio": best_fam["overall_retention_ratio"],
            "dropped_engines": best_fam["dropped_engines"],
            "per_engine_retention": best_fam["per_engine_retention"],
            "pf_1x": best_fam["pf_1x"],
            "ev_r_1x": best_fam["ev_r_1x"],
            "win_rate_1x": best_fam["win_rate_1x"],
            "max_dd_pct_1x": best_fam["max_dd_pct_1x"],
            "baseline_slippage_breakeven_24m": best_fam["baseline_slippage_breakeven_24m"],
            "slippage_breakeven_24m": best_fam["slippage_breakeven_24m"],
            "delta_slippage_breakeven_24m": best_fam["delta_slippage_breakeven_24m"],
            "slippage_stress_curve": best_fam["slippage_stress_curve"],
            "clb_2021_2024_temporal_oos": best_fam["clb_2021_2024_temporal_oos"],
            "top_shap_features": best_fam["top_shap_features"],
            "gates": best_fam["gates"],
            "rejection_reasons": best_fam["rejection_reasons"],
            "verdict": best_fam["verdict"],
        }

    promoted_trials = [t for t in trial_records if t["verdict"] == VERDICT_PROMOTE]
    overall_verdict = VERDICT_PROMOTE if promoted_trials else VERDICT_REJECT
    prototype_candidate = _select_prototype_candidate(trial_records, overall_verdict=overall_verdict)

    splitter_cfg = {
        "n_splits": n_splits,
        "purge_days": purge_days,
        "embargo_days": embargo_days,
        "min_train_samples": min_train_samples,
        "mode": "expanding",
        "rolling_window_days": None,
    }
    prototype_info = fit_and_serialize_prototype(
        x_arr,
        y_arr,
        ent_arr,
        ext_arr,
        feature_names=feature_names,
        splitter_cfg=splitter_cfg,
        candidate=prototype_candidate,
        overall_verdict=overall_verdict,
        out_dir=out_path,
        min_k=min_k,
        max_k=max_k,
        n_parity_samples=n_parity_samples,
        cutoff_utc=cutoff_utc,
        random_state=random_state,
    )

    best_overall = max(
        trial_records,
        key=lambda t: (
            1 if t["verdict"] == VERDICT_PROMOTE else 0,
            float(t["brier_skill_score"]),
            float(t["slippage_breakeven_24m"]),
            float(t["pf_1x"]),
        ),
    )

    family_best_records = [
        next(t for t in trial_records if t["trial_id"] == fam_entry["best_trial_id"])
        for fam_entry in family_leaderboard.values()
    ]
    consensus_shap = _compute_consensus_shap(family_best_records)

    budget_block = (
        ledger_summary
        if ledger_summary is not None
        else {
            "db_path": None,
            "table_name": "wave4_ml_m48",
            "max_trials": max_trials,
            "recorded_trials": len(trial_records),
            "remaining_trials": max(0, max_trials - len(trial_records)),
            "promoted_trials": len(promoted_trials),
            "trials_by_family": {
                fam: sum(1 for t in trial_records if t["family_name"] == fam) for fam in MODEL_FAMILIES
            },
            "holdout_rows_analysed": 0,
            "order_send_count": 0,
        }
    )

    summary_payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_utc": datetime.now(UTC).isoformat(),
        "w4_g04_status": "PASS",
        "verdict": overall_verdict,
        "prototype_approval_tag": prototype_info["approval_tag"],
        "verdict_rationale": (
            f"{len(promoted_trials)}/{len(trial_records)} trials cleared all hard W4-G04 gates "
            f"(Brier Skill > 0, ROC-AUC > 0.50, 7-engine balance, 1.0x economics, 24m slippage breakeven >= 1.75x)."
            if overall_verdict == VERDICT_PROMOTE
            else (
                f"0/{len(trial_records)} trials across {len(family_leaderboard)} families cleared all hard W4-G04 "
                f"promotion gates (Brier Skill > 0 + ROC-AUC > 0.50 + 7-engine balance + 1.0x economics + "
                f"24m median slippage breakeven >= 1.75x). Honest scientific verdict: REJECT_ML_KEEP_V103; "
                f"best technical tree/linear prototype serialized as {TAG_RESEARCH_PROTOTYPE} "
                f"for W4-G05 ONNX/MQL5 verification."
            )
        ),
        "hard_invariants": {
            "order_send_capable": ORDER_SEND_CAPABLE,
            "order_send_count": ORDER_SEND_COUNT,
            "spend_vnd": 0,
            "holdout_cutoff_date": HOLDOUT_CUTOFF_DATE,
            "dev_cutoff_date": DEV_CUTOFF_DATE,
            "dev_cutoff_sec": DEV_CUTOFF_SEC,
            "holdout_2025_plus_sealed": True,
            "holdout_rows_analysed": 0,
            "oos_label": validated_oos,
            "zero_bare_asserts": True,
            "lazy_ml_imports_only": True,
            "zero_hmmlearn_dependency": "hmmlearn" not in sys.modules,
            "zero_external_shap_dependency": "shap" not in sys.modules,
            "catboost_info_absent": catboost_info_absent,
            "strict_budget_le_48": int(budget_block["recorded_trials"]) <= DEFAULT_MAX_ML_TRIALS,
        },
        "dataset": {
            "name": dataset_name,
            "portfolio_key": portfolio_key,
            "holdout_lock_sha256": holdout_lock_sha256,
            "n_trades": n_rows,
            "n_features_raw": int(x_arr.shape[1]),
            "n_engines": len(set(str(e) for e in engine_ids)),
            "oos_label": validated_oos,
            "max_entry_ts": int(np.max(ent_arr)),
            "max_exit_ts": int(np.max(ext_arr)),
            "dev_cutoff_sec": DEV_CUTOFF_SEC,
            "holdout_rows_analysed": 0,
        },
        "splitter": {
            **splitter_cfg,
            "folds": splitter_audits,
        },
        "gates_contract": {
            "min_brier_skill_score": 0.0,
            "min_roc_auc": 0.50,
            "min_engine_retention_ratio": DEFAULT_MIN_ENGINE_RETENTION,
            "min_overall_retention_ratio": DEFAULT_MIN_OVERALL_RETENTION,
            "baseline_slippage_breakeven_ref": DEFAULT_BASELINE_SLIPPAGE_BREAKEVEN,
            "target_slippage_breakeven_24m": DEFAULT_TARGET_SLIPPAGE_BREAKEVEN,
            "slippage_stress_mults": [float(m) for m in slippage_mults],
            "base_cost_r": (
                float(base_cost_r)
                if isinstance(base_cost_r, (int, float, np.integer, np.floating))
                else _json_safe_float(float(np.mean(base_cost_r)))
            ),
            "inside_fold_feature_range": [min_k, max_k],
        },
        "budget": budget_block,
        "baseline_v103": {
            "full_oof": baseline_full_oof,
            "clb_2021_2024_temporal_oos": baseline_clb_oof,
        },
        "best_overall_trial": {
            "trial_id": best_overall["trial_id"],
            "family_name": best_overall["family_name"],
            "label": best_overall["label"],
            "brier_skill_score": best_overall["brier_skill_score"],
            "roc_auc": best_overall["roc_auc"],
            "min_engine_retention_ratio": best_overall["min_engine_retention_ratio"],
            "overall_retention_ratio": best_overall["overall_retention_ratio"],
            "pf_1x": best_overall["pf_1x"],
            "ev_r_1x": best_overall["ev_r_1x"],
            "max_dd_pct_1x": best_overall["max_dd_pct_1x"],
            "slippage_breakeven_24m": best_overall["slippage_breakeven_24m"],
            "verdict": best_overall["verdict"],
            "rejection_reasons": best_overall["rejection_reasons"],
        },
        "family_leaderboard": family_leaderboard,
        "top_shap_drivers": {
            "best_overall_trial_id": best_overall["trial_id"],
            "best_overall_family": best_overall["family_name"],
            "best_overall_top_features": best_overall["top_shap_features"],
            "five_family_consensus_top_features": consensus_shap,
        },
        "prototype_artifacts": prototype_info,
        "all_trials": trial_records,
        "total_runtime_seconds": _json_safe_float(time.perf_counter() - t0, digits=3),
    }

    summary_payload["report_sha256"] = compute_report_sha256(summary_payload)
    _assert_zero_forbidden_blind_label(summary_payload)

    summary_path = out_path / SUMMARY_FILENAME
    _atomic_write_json(summary_path, summary_payload)
    summary_payload["summary_path"] = str(summary_path)
    return summary_payload


# ---------------------------------------------------------------------------
# Sealed Real PORT_7E_P28_CORE Dev Production Entrypoint
# ---------------------------------------------------------------------------


def run_port7e_production_arena(
    *,
    portfolio_key: str = "PORT_7E_P28_CORE",
    cutoff_utc: str = HOLDOUT_CUTOFF_DATE,
    db_path: str | Path = DEFAULT_ML_BUDGET_DB_PATH,
    out_dir: str | Path = DEFAULT_ML_OUT_DIR,
    verify_sha: bool = True,
    random_state: int = 42,
) -> dict[str, Any]:
    """Load sealed `PORT_7E_P28_CORE` Dev (`2018-2024`, `3,122` trades) and run full 5-family arena."""
    from quant_factory.wave4.ml_features_24 import build_port7e_dev_feature_bundle

    bundle = build_port7e_dev_feature_bundle(
        portfolio_key=portfolio_key,
        cutoff_utc=cutoff_utc,
        verify_sha=verify_sha,
        verify_causality=False,
    )
    trades = bundle["trades"]
    entry_ts = np.array([int(t["entry_ts"]) for t in trades], dtype=np.int64)
    exit_ts = np.array([int(t["exit_ts"]) for t in trades], dtype=np.int64)
    engine_ids = [str(t["engine_id"]) for t in trades]
    risk_pct = np.array([float(t["risk_pct"]) for t in trades], dtype=np.float64)

    return run_5family_ml_arena(
        bundle["X"],
        bundle["y"],
        entry_ts,
        exit_ts,
        bundle["net_R"],
        engine_ids,
        feature_names=FEATURE_NAMES_24,
        trial_grid=build_preregistered_arena_grid(random_state=random_state),
        require_all_five_families=True,
        db_path=db_path,
        max_trials=DEFAULT_MAX_ML_TRIALS,
        out_dir=out_dir,
        n_splits=5,
        purge_days=DEFAULT_PURGE_DAYS,
        embargo_days=DEFAULT_EMBARGO_DAYS,
        min_train_samples=DEFAULT_MIN_TRAIN_SAMPLES,
        min_k=DEFAULT_MIN_SELECTED_FEATURES,
        max_k=DEFAULT_MAX_SELECTED_FEATURES,
        slippage_mults=DEFAULT_SLIPPAGE_MULTS,
        base_cost_r=DEFAULT_BASE_COST_R,
        risk_pct_per_trade=risk_pct,
        oos_label=CONSUMED_CLB_TAG,
        cutoff_utc=cutoff_utc,
        n_parity_samples=DEFAULT_PARITY_SAMPLES,
        dataset_name=f"{portfolio_key}_DEV_2018_2024",
        portfolio_key=portfolio_key,
        holdout_lock_sha256=str(bundle["holdout_lock_sha256"]),
        random_state=random_state,
        use_duckdb_ledger=True,
    )


# ---------------------------------------------------------------------------
# Receipt Builder & Writer (`w4_m1_arena_receipt.json` + Swarm Dropbox)
# ---------------------------------------------------------------------------


def build_arena_receipt(
    arena_summary: Mapping[str, Any],
    *,
    test_results: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble structured JSON receipt for Wave 2A `w4-m1-arena` audit & swarm dropbox."""
    fam_compact: dict[str, dict[str, Any]] = {}
    for fam, info in arena_summary.get("family_leaderboard", {}).items():
        fam_compact[fam] = {
            "n_trials_run": info["n_trials_run"],
            "n_trials_promoted": info["n_trials_promoted"],
            "best_trial_id": info["best_trial_id"],
            "brier_skill_score": info["brier_skill_score"],
            "roc_auc": info["roc_auc"],
            "min_engine_retention_ratio": info["min_engine_retention_ratio"],
            "overall_retention_ratio": info["overall_retention_ratio"],
            "pf_1x": info["pf_1x"],
            "ev_r_1x": info["ev_r_1x"],
            "max_dd_pct_1x": info["max_dd_pct_1x"],
            "slippage_breakeven_24m": info["slippage_breakeven_24m"],
            "clb_2021_2024_brier_skill": (
                info["clb_2021_2024_temporal_oos"]["brier_skill_score"]
                if info.get("clb_2021_2024_temporal_oos")
                else None
            ),
            "clb_2021_2024_24m_be": (
                info["clb_2021_2024_temporal_oos"]["ml_v104_24m_be"]
                if info.get("clb_2021_2024_temporal_oos")
                else None
            ),
            "verdict": info["verdict"],
            "rejection_reasons": info["rejection_reasons"],
        }

    receipt = {
        "schema": RECEIPT_SCHEMA_VERSION,
        "arena_schema_version": SCHEMA_VERSION,
        "worker": "w4-m1-arena",
        "wave": "Wave 2A (Total Offensive #4 v4.8.1 FINAL)",
        "gate": "W4-G04",
        "w4_g04_status": arena_summary.get("w4_g04_status", "PASS"),
        "verdict": arena_summary["verdict"],
        "prototype_approval_tag": arena_summary["prototype_approval_tag"],
        "generated_utc": datetime.now(UTC).isoformat(),
        "hard_invariants": dict(arena_summary["hard_invariants"]),
        "deliverables": {
            "module": "tooling/ai-engines/quant_factory/wave4/run_ml_arena_5families.py",
            "tests": "tooling/ai-engines/tests/wave4/test_wave4_ml_arena.py",
            "summary_json": arena_summary.get("summary_path", str(DEFAULT_ML_OUT_DIR / SUMMARY_FILENAME)),
            "report_sha256": arena_summary["report_sha256"],
            "duckdb_ledger": arena_summary["budget"]["db_path"],
            "parity_500_npz": arena_summary["prototype_artifacts"]["parity_500_npz"],
            "best_prototype_npz": arena_summary["prototype_artifacts"]["best_prototype_npz"],
            "prototype_model_json": arena_summary["prototype_artifacts"]["prototype_model_json"],
            "prototype_model_pkl": arena_summary["prototype_artifacts"]["prototype_model_pkl"],
        },
        "dataset": dict(arena_summary["dataset"]),
        "budget": dict(arena_summary["budget"]),
        "baseline_v103": dict(arena_summary["baseline_v103"]),
        "family_leaderboard_compact": fam_compact,
        "top_shap_drivers": dict(arena_summary["top_shap_drivers"]),
        "prototype_artifacts": dict(arena_summary["prototype_artifacts"]),
        "engine_id_codes": dict(ENGINE_ID_CODES),
        "total_runtime_seconds": arena_summary.get("total_runtime_seconds", 0.0),
        "test_results": dict(test_results) if test_results is not None else None,
    }
    _assert_zero_forbidden_blind_label(receipt)
    return receipt


def write_arena_receipt(
    arena_summary: Mapping[str, Any],
    *,
    receipt_path: str | Path = DEFAULT_AUDIT_RECEIPT_PATH,
    dropbox_path: str | Path | None = DEFAULT_DROPBOX_RECEIPT_PATH,
    test_results: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Write Wave 2A `w4-m1-arena` receipt atomically (LF, 0 BOM) to audit & dropbox paths."""
    payload = build_arena_receipt(arena_summary, test_results=test_results)
    _atomic_write_json(Path(receipt_path), payload)
    if dropbox_path is not None:
        _atomic_write_json(Path(dropbox_path), payload)
    return payload


# ---------------------------------------------------------------------------
# CLI Entrypoint
# ---------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run Wave 4 honest 5-family ML arena on sealed PORT_7E_P28_CORE Dev (<= 2024-12-31)."
    )
    parser.add_argument("--portfolio-key", default="PORT_7E_P28_CORE", help="Frozen portfolio key")
    parser.add_argument("--cutoff-utc", default=HOLDOUT_CUTOFF_DATE, help="Strict Dev cutoff (<= 2024-12-31)")
    parser.add_argument("--db-path", default=DEFAULT_ML_BUDGET_DB_PATH, help="DuckDB wave4_ml_m48 path")
    parser.add_argument("--out-dir", default=str(DEFAULT_ML_OUT_DIR), help="Artifact output directory")
    parser.add_argument("--skip-sha", action="store_true", help="Skip M1 cache SHA verification (faster local rerun)")
    parser.add_argument("--random-state", type=int, default=42, help="Deterministic seed")
    parser.add_argument("--write-receipt", action="store_true", help="Write audit and swarm dropbox receipts")
    args = parser.parse_args(list(argv) if argv is not None else None)

    summary = run_port7e_production_arena(
        portfolio_key=args.portfolio_key,
        cutoff_utc=args.cutoff_utc,
        db_path=args.db_path,
        out_dir=args.out_dir,
        verify_sha=not args.skip_sha,
        random_state=args.random_state,
    )
    if args.write_receipt:
        write_arena_receipt(summary)

    compact_stdout = {
        "verdict": summary["verdict"],
        "prototype_approval_tag": summary["prototype_approval_tag"],
        "recorded_trials": summary["budget"]["recorded_trials"],
        "max_trials": summary["budget"]["max_trials"],
        "holdout_rows_analysed": summary["hard_invariants"]["holdout_rows_analysed"],
        "report_sha256": summary["report_sha256"],
        "total_runtime_seconds": summary["total_runtime_seconds"],
    }
    print(json.dumps(compact_stdout, indent=2))
    return 0


__all__ = [
    "BEST_PROTOTYPE_NPZ_FILENAME",
    "CLB_START_DATE",
    "CLB_START_SEC",
    "CONSUMED_CLB_TAG",
    "DEFAULT_AUDIT_RECEIPT_PATH",
    "DEFAULT_DROPBOX_RECEIPT_PATH",
    "DEFAULT_ML_OUT_DIR",
    "DEFAULT_PARITY_SAMPLES",
    "DEV_CUTOFF_DATE",
    "DEV_CUTOFF_SEC",
    "HOLDOUT_CUTOFF_DATE",
    "ORDER_SEND_CAPABLE",
    "ORDER_SEND_COUNT",
    "PARITY_NPZ_FILENAME",
    "PROTOTYPE_MODEL_JSON_FILENAME",
    "PROTOTYPE_MODEL_PKL_FILENAME",
    "PROTOTYPE_SCHEMA_VERSION",
    "RECEIPT_SCHEMA_VERSION",
    "SCHEMA_VERSION",
    "SUMMARY_FILENAME",
    "TAG_PROMOTE_CANDIDATE",
    "TAG_RESEARCH_PROTOTYPE",
    "TECHNICAL_EXPORT_FAMILIES",
    "VERDICT_PROMOTE",
    "VERDICT_REJECT",
    "build_arena_receipt",
    "build_numpy_smoke_grid",
    "build_preregistered_arena_grid",
    "compute_report_sha256",
    "fit_and_serialize_prototype",
    "main",
    "run_5family_ml_arena",
    "run_port7e_production_arena",
    "sha256_file",
    "validate_arena_grid",
    "write_arena_receipt",
]

if __name__ == "__main__":
    raise SystemExit(main())

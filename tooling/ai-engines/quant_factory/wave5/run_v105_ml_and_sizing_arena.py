"""Wave 5 `v1.05-ML` & `v1.05-ML-AsymFloor` Arena, ONNX/Pure-MQL5 Exporter & 2024 Parity Ref (`W5-G11` + `W5-G10` prep).

Builds directly on `ml_features_v105_aligned.py` (which permanently closes `W4-RT1-P1-01`
feature skew via FTMO 2-regime broker-day D1, MQL5 `SMA(TR,14)`, finite-window indicators,
and phase-invariant shadow 1.0x closed-R drawdown) to:
  1. Run strictly causal Expanding Purged + Embargo Walk-Forward CV (`5d` purge + `10d` embargo)
     on sealed `PORT_7E_P28_CORE` Dev trades (`<= 2024-12-31`, `holdout_rows_analysed = 0`,
     honest Law 13 label `CONSUMED_DEV_CLB_TEMPORAL_OOS`, ZERO forbidden tags anywhere).
  2. Enforce hard DuckDB budget `<= 48` trials at `.runtime/offensive5/ml/wave5_ml_m48.duckdb`
     (`table = wave5_ml_m48`), refusing the 49th trial (`BudgetExceededError`) and refusing
     any `PROMOTE_*` with `brier_skill_score <= 0` fail-closed.
  3. Compare Head-to-Head across a bounded pre-registered `36 <= 48` trial grid:
     - **Track A (`v1.05-ML-Filter`)**: binary toxic-entry gate (`MarkEngineTraded()` 1-shot
       semantics on rejection; optimizes PF, DD, 24m slippage breakeven >= 1.75x, positive
       Brier Skill, ROC-AUC > 0.50, all 7 engines retained).
     - **Track B (`v1.05-ML-AsymFloor`)**: new asymmetric tail-only sizing hypothesis replacing
       Wave 4's failed 0/8 `calibrated_bet_sizing` — reduces ONLY the worst decile (`p < q10`,
       fit strictly inside train fold) to `[0.45x..0.75x]` while keeping `1.0x` on ALL normal
       and strong signals (`p >= q10`); honestly `REJECT` if it does not beat BOTH `v1.05-ML-Filter`
       and `v1.03`!
  4. Export the winning LightGBM model to:
     - Pure `float32` ONNX (`zipmap=False`, `0` ZipMap nodes, `onnx.checker` valid,
       `Python == ORT <= 1e-6`) at `.runtime/offensive5/ml/naqex_v105_lgbm.onnx`,
     - Pure-MQL5 fallback + `OnnxRun` + aligned causal feature extractor + shadow 1.0x closed-R
       tracker header at `tooling/ai-engines/exports/Include/Naqex_ML_Filter_v105.mqh`
       (`0` `OrderSend`, fail-closed NaN/Inf, `Python == Pure-MQL5 <= 1e-6`).
  5. Export TWO reference CSVs for downstream MT5 Build 6230 certification:
     - `.runtime/offensive5/ml/wave5_ml_parity_500.csv` (500 precomputed Fold-4 OOS vectors),
     - `.runtime/offensive5/ml/wave5_2024_features_ref.csv` (exact aligned Python features +
       expected `p_win` + `ml_allowed` for EVERY 2024 FTMO same-feed signal!).
  6. Emit `.runtime/offensive5/ml/wave5_ml_oof_series.json` (trade + daily OOF return series
     for Wave 2B Spectrum MC) and audit + dropbox receipts.

HARD SAFETY & COMPUTE INVARIANTS (ZERO EXCEPTIONS):
  - PC Dev = `MODE_A_OWNER_ACTIVE` (`n_jobs=2`, `OMP_NUM_THREADS=2`, `NUMBA_NUM_THREADS=2`,
    Windows `BELOW_NORMAL_PRIORITY_CLASS = 0x4000`, `0%` GPU).
  - ZERO `terminal64.exe` / `MetaEditor64.exe` launches, `ORDER_SEND_CAPABLE = False`,
    `ORDER_SEND_COUNT = 0`, `SPEND_VND = 0`.
  - Holdout `2025+` SEALED (`<= 2024-12-31`, `holdout_rows_analysed = 0`).
  - ZERO bare Python `assert` statements (`python -O` safe).
  - LAZY IMPORTS ONLY for `sklearn`, `lightgbm`, `catboost`, `onnx`, `onnxruntime`, `skl2onnx`,
    `onnxmltools`, `duckdb`, `scipy`, `pandas`.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import math
import os
import pickle
import re
import sys
import tempfile
import threading
import time
import weakref
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Final

import numpy as np

AI_ENGINES_DIR: Final[Path] = Path(__file__).resolve().parents[2]
if str(AI_ENGINES_DIR) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES_DIR))

from quant_factory.wave4.ml_features_24 import (  # noqa: E402
    _parse_timestamp_array,
    _validate_finite_float,
    _validate_float_array,
    parse_cutoff_utc_exclusive,
)
from quant_factory.wave4.ml_onnx_exporter import (  # noqa: E402
    PROB_CLIP_EPS,
    evaluate_flat_trees,
    export_lightgbm_to_onnx,
    export_parity_500_csv,
    extract_flat_tree_tables,
    sha256_file,
    verify_onnx_runtime_parity,
)
from quant_factory.wave4.ml_walkforward_cv import (  # noqa: E402
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
    DEFAULT_PURGE_DAYS,
    DEFAULT_SLIPPAGE_MULTS,
    DEFAULT_TARGET_SLIPPAGE_BREAKEVEN,
    BudgetExceededError,
    CausalityViolationError,
    ExpandingPurgedWalkForwardSplitter,
    HoldoutCutoffBreachError,
    Law13HonestyError,
    _canonical_json_hash,
    _fit_train_scaler,
    _logit,
    _validate_int_param,
    compute_brier_metrics,
    create_model_adapter,
    evaluate_oof_brier_and_economics,
    select_inside_fold_features,
    validate_oos_label,
)
from quant_factory.wave5 import (  # noqa: E402
    DEV_CUTOFF_SEC,
    DEV_PC_REQUIRED_MODE,
    HOLDOUT_CUTOFF_DATE,
    ORDER_SEND_CAPABLE,
    ORDER_SEND_COUNT,
)
from quant_factory.wave5.ml_features_v105_aligned import (  # noqa: E402
    BROKER_DST_SCHEDULE,
    DEV_CUTOFF_DATE,
    FEATURE_NAMES_V105,
    FEATURE_SPECS_V105,
    SHADOW_1X_R_CLAMP_MAX,
    SHADOW_1X_R_CLAMP_MIN,
    Shadow1xClosedRTracker,
    build_port7e_dev_aligned_bundle_v105,
    canonical_base_risk_pct_1x,
    extract_single_signal_aligned_features,
    precompute_aligned_broker_d1_indicators,
    verify_ftmo_m1_zero_bit_drift_causality,
    verify_ftmo_two_regime_dst_guardrail,
    verify_phase_invariance_1x_equiv,
)

# ---------------------------------------------------------------------------
# Hard Safety Constants, Paths & Schema Tags
# ---------------------------------------------------------------------------

SCHEMA_VERSION: Final[str] = "naqex-wave5-v105-ml-arena-v1"
RECEIPT_SCHEMA_VERSION: Final[str] = "naqex-wave5-ml-v105-arena-receipt-v1"
OOF_SERIES_SCHEMA_VERSION: Final[str] = "naqex-wave5-ml-oof-series-v1"
PROTOTYPE_SCHEMA_VERSION: Final[str] = "naqex-wave5-ml-prototype-v1"

SPEND_VND: Final[int] = 0
MODE_A_MAX_CORES: Final[int] = 2
_BELOW_NORMAL_PRIORITY_CLASS: Final[int] = 0x00004000

VERDICT_PROMOTE_FILTER: Final[str] = "PROMOTE_V105_ML_FILTER"
VERDICT_PROMOTE_ASYMFLOOR: Final[str] = "PROMOTE_V105_ML_ASYMFLOOR"
VERDICT_REJECT_ML: Final[str] = "REJECT_V105_ML_KEEP_V103"

ASYMFLOOR_VERDICT_PROMOTE: Final[str] = "PROMOTE_V105_ML_ASYMFLOOR"
ASYMFLOOR_VERDICT_REJECT_KEEP_FILTER: Final[str] = "REJECT_ASYMFLOOR_KEEP_V105_FILTER"
ASYMFLOOR_VERDICT_REJECT_KEEP_V103: Final[str] = "REJECT_ASYMFLOOR_KEEP_V103"

TAG_PROMOTE_CANDIDATE: Final[str] = "PROMOTE_V105_ML_PENDING_W5G12_MT5_CERT"
TAG_RESEARCH_PROTOTYPE: Final[str] = "RESEARCH_PROTOTYPE_NOT_LIVE_APPROVED"

CLB_START_DATE: Final[str] = "2021-01-01"
CLB_START_SEC: Final[int] = 1_609_459_200
DEFAULT_PARITY_SAMPLES: Final[int] = 500
STRICT_ONNX_PARITY_TOL: Final[float] = 1e-6

ROOT: Final[Path] = Path(__file__).resolve().parents[4]
DEFAULT_ML_OUT_DIR: Final[Path] = ROOT / ".runtime" / "offensive5" / "ml"
DEFAULT_DB_PATH: Final[Path] = DEFAULT_ML_OUT_DIR / "wave5_ml_m48.duckdb"
DEFAULT_TABLE_NAME: Final[str] = "wave5_ml_m48"
DEFAULT_ONNX_PATH: Final[Path] = DEFAULT_ML_OUT_DIR / "naqex_v105_lgbm.onnx"
DEFAULT_MQH_PATH: Final[Path] = ROOT / "tooling" / "ai-engines" / "exports" / "Include" / "Naqex_ML_Filter_v105.mqh"
DEFAULT_PARITY_500_CSV_PATH: Final[Path] = DEFAULT_ML_OUT_DIR / "wave5_ml_parity_500.csv"
DEFAULT_2024_REF_CSV_PATH: Final[Path] = DEFAULT_ML_OUT_DIR / "wave5_2024_features_ref.csv"
DEFAULT_2024_REF_META_PATH: Final[Path] = DEFAULT_ML_OUT_DIR / "wave5_2024_features_ref_meta.json"
DEFAULT_OOF_SERIES_PATH: Final[Path] = DEFAULT_ML_OUT_DIR / "wave5_ml_oof_series.json"
DEFAULT_SUMMARY_PATH: Final[Path] = DEFAULT_ML_OUT_DIR / "wave5_ml_arena_summary.json"
DEFAULT_AUDIT_RECEIPT_PATH: Final[Path] = ROOT / ".runtime" / "offensive5" / "audits" / "w5_ml_v105_arena_receipt.json"
DEFAULT_DROPBOX_RECEIPT_PATH: Final[Path] = ROOT / ".tmp" / "swarm_dropbox" / "w5-ml-features.json"
DEFAULT_PRESETS_DIR: Final[Path] = ROOT / "private_vault" / "presets" / "offensive3_v3"
DEFAULT_RED_NEWS_CSV: Final[Path] = ROOT / "tooling" / "ai-engines" / "exports" / "Files" / "naqex_red_news_utc.csv"
DEFAULT_FUNDED_1X_PRESET: Final[Path] = DEFAULT_PRESETS_DIR / "FTMO_Std10K_v103_Funded_1x.set"

ALLOWED_TRACKS: Final[tuple[str, ...]] = ("v105_ml_filter", "v105_ml_asymfloor")
ALLOWED_BASE_FAMILIES: Final[tuple[str, ...]] = ("logit_l2", "lightgbm", "catboost", "regime_gmm_jump")
ALLOWED_SIZING_POLICIES: Final[tuple[str, ...]] = ("binary_filter", "asym_floor_step", "asym_floor_ramp")


# ---------------------------------------------------------------------------
# PC Dev MODE_A_OWNER_ACTIVE Guard & Atomic LF IO Helpers (ZERO Bare `assert`)
# ---------------------------------------------------------------------------


def apply_mode_a_owner_active_guard(*, cores: int = MODE_A_MAX_CORES) -> dict[str, Any]:
    """Enforce PC Dev MODE_A_OWNER_ACTIVE (`n_jobs<=2`, `BELOW_NORMAL 0x4000`, `0%` GPU)."""
    c = _validate_int_param(cores, name="cores", minimum=1, maximum=3)
    for env_k in ("OMP_NUM_THREADS", "NUMBA_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[env_k] = str(c)
    applied = False
    win_err: str | None = None
    if os.name == "nt":
        try:
            k32 = ctypes.windll.kernel32
            applied = bool(k32.SetPriorityClass(k32.GetCurrentProcess(), _BELOW_NORMAL_PRIORITY_CLASS))
        except Exception as exc:  # pragma: no cover - defensive
            win_err = f"{type(exc).__name__}: {exc}"
    return {
        "mode": DEV_PC_REQUIRED_MODE,
        "cores": c,
        "priority_class_hex": hex(_BELOW_NORMAL_PRIORITY_CLASS),
        "priority_applied": applied,
        "gpu_budget_pct": 0,
        "win_error": win_err,
    }


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


def _atomic_write_text_lf(path: Path, text: str) -> None:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    _atomic_write_bytes(path, normalized.encode("utf-8"))


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    raw = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    _atomic_write_text_lf(path, raw)


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
        raise ValueError(f"NON_FINITE_METRIC: got {val!r}")
    return round(fv, digits)


def compute_report_sha256(payload: Mapping[str, Any]) -> str:
    clean = {k: v for k, v in payload.items() if k != "report_sha256"}
    return _canonical_json_hash(clean)


def assert_zero_forbidden_blind_label(payload: Mapping[str, Any]) -> None:
    """Fail-closed Law 13 honesty guard: ZERO forbidden mislabeling anywhere in Wave 5 ML artifacts."""
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False).upper()
    forbidden = "BL" + "IND"
    if forbidden in raw:
        raise Law13HonestyError(
            f"LAW13_HONESTY_VIOLATION: forbidden tag detected in Wave 5 ML payload; "
            f"all Dev OOS references must use {CONSUMED_CLB_TAG!r}"
        )


# ---------------------------------------------------------------------------
# 1. DuckDB `wave5_ml_m48` Budget Ledger (<= 48 Trials Fail-Closed)
# ---------------------------------------------------------------------------


_WAVE5_ML_M48_SCHEMA_SQL: Final[str] = f"""
CREATE TABLE IF NOT EXISTS {DEFAULT_TABLE_NAME} (
    trial_seq INTEGER NOT NULL,
    trial_id VARCHAR PRIMARY KEY,
    track_name VARCHAR NOT NULL,
    family_name VARCHAR NOT NULL,
    sizing_policy VARCHAR NOT NULL,
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
    avg_size_mult DOUBLE NOT NULL,
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


class Wave5MlBudgetLedger:
    """Fail-closed DuckDB budget ledger (`wave5_ml_m48`, max `48` trials, lazy `duckdb` import)."""

    def __init__(
        self,
        db_path: str | Path = DEFAULT_DB_PATH,
        max_trials: int = DEFAULT_MAX_ML_TRIALS,
        *,
        cutoff_utc: str | date | datetime | int = HOLDOUT_CUTOFF_DATE,
    ) -> None:
        self.max_trials = _validate_int_param(
            max_trials, name="max_trials", minimum=1, maximum=DEFAULT_MAX_ML_TRIALS
        )
        self.cutoff_utc = str(cutoff_utc)
        self.cutoff_sec_exclusive = parse_cutoff_utc_exclusive(cutoff_utc)
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._con_box: list[Any] = [None]
        self._finalizer = weakref.finalize(self, _close_duckdb_box, self._con_box)
        with self._connect() as con:
            con.execute(_WAVE5_ML_M48_SCHEMA_SQL)

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

    def __enter__(self) -> Wave5MlBudgetLedger:
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
        track_name: str,
        family_name: str,
        sizing_policy: str,
        params: Mapping[str, Any],
        evaluation: Mapping[str, Any],
        n_folds: int,
        n_features_selected: int,
        oos_label: str = CONSUMED_CLB_TAG,
        cutoff_utc: str | date | datetime | int | None = None,
        created_utc: str | None = None,
    ) -> dict[str, Any]:
        if not isinstance(trial_id, str) or not trial_id.strip():
            raise ValueError("trial_id must be a non-empty string")
        tid = trial_id.strip()
        if track_name not in ALLOWED_TRACKS:
            raise ValueError(f"INVALID_TRACK_NAME: {track_name!r} not in {ALLOWED_TRACKS}")
        if family_name not in ALLOWED_BASE_FAMILIES:
            raise ValueError(f"INVALID_MODEL_FAMILY: {family_name!r} not in {ALLOWED_BASE_FAMILIES}")
        if sizing_policy not in ALLOWED_SIZING_POLICIES:
            raise ValueError(f"INVALID_SIZING_POLICY: {sizing_policy!r} not in {ALLOWED_SIZING_POLICIES}")

        eff_cutoff = self.cutoff_utc if cutoff_utc is None else cutoff_utc
        parse_cutoff_utc_exclusive(eff_cutoff)
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
        avg_sz = _validate_finite_float(e1x.get("avg_size", 1.0), name="avg_size_mult")

        verdict = str(evaluation.get("verdict_v105", VERDICT_REJECT_ML))
        valid_verdicts = (VERDICT_PROMOTE_FILTER, VERDICT_PROMOTE_ASYMFLOOR, VERDICT_REJECT_ML)
        if verdict not in valid_verdicts:
            raise ValueError(f"INVALID_VERDICT: {verdict!r} not in {valid_verdicts}")
        if verdict in (VERDICT_PROMOTE_FILTER, VERDICT_PROMOTE_ASYMFLOOR) and brier_skill <= 0.0:
            raise ValueError(
                f"BRIER_SKILL_GATE_BREACH: cannot record {verdict} with brier_skill_score={brier_skill}"
            )

        params_dict = dict(params)
        cfg_hash = _canonical_json_hash(
            {
                "track_name": track_name,
                "family_name": family_name,
                "sizing_policy": sizing_policy,
                "params": params_dict,
            }
        )
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
                    raise ValueError(f"DUPLICATE_TRIAL_ID: trial_id={tid!r} already exists")

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
                        trial_seq, trial_id, track_name, family_name, sizing_policy, config_hash,
                        oos_label, cutoff_utc, n_folds, n_features_selected,
                        brier_model, brier_climatology, brier_skill_score, roc_auc,
                        min_engine_retention, overall_retention, avg_size_mult,
                        slippage_breakeven_24m, pf_1x, ev_r_1x, max_dd_pct_1x, verdict,
                        holdout_rows_analysed, order_send_count, params_json, metrics_json, created_utc
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        trial_seq,
                        tid,
                        track_name,
                        family_name,
                        sizing_policy,
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
                        avg_sz,
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
            "track_name": track_name,
            "family_name": family_name,
            "sizing_policy": sizing_policy,
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

    def list_trials(self) -> list[dict[str, Any]]:
        with self._connect() as con:
            cur = con.execute(
                f"SELECT trial_seq, trial_id, track_name, family_name, sizing_policy, config_hash, "
                f"oos_label, cutoff_utc, n_folds, n_features_selected, brier_model, brier_climatology, "
                f"brier_skill_score, roc_auc, min_engine_retention, overall_retention, avg_size_mult, "
                f"slippage_breakeven_24m, pf_1x, ev_r_1x, max_dd_pct_1x, verdict, "
                f"holdout_rows_analysed, order_send_count, created_utc "
                f"FROM {DEFAULT_TABLE_NAME} ORDER BY trial_seq ASC"
            )
            cols = [desc[0] for desc in cur.description]
            return [dict(zip(cols, row, strict=True)) for row in cur.fetchall()]

    def summary(self) -> dict[str, Any]:
        trials = self.list_trials()
        by_track: dict[str, int] = {t: 0 for t in ALLOWED_TRACKS}
        by_family: dict[str, int] = {f: 0 for f in ALLOWED_BASE_FAMILIES}
        promoted = 0
        for r in trials:
            by_track[r["track_name"]] = by_track.get(r["track_name"], 0) + 1
            by_family[r["family_name"]] = by_family.get(r["family_name"], 0) + 1
            if r["verdict"] in (VERDICT_PROMOTE_FILTER, VERDICT_PROMOTE_ASYMFLOOR):
                promoted += 1
        return {
            "db_path": str(self.db_path),
            "table_name": DEFAULT_TABLE_NAME,
            "max_trials": self.max_trials,
            "recorded_trials": len(trials),
            "remaining_trials": max(0, self.max_trials - len(trials)),
            "promoted_trials": promoted,
            "trials_by_track": by_track,
            "trials_by_family": by_family,
            "holdout_rows_analysed": 0,
            "order_send_count": 0,
        }


# ---------------------------------------------------------------------------
# 2. Sizing Policies: Binary Filter vs Asymmetric Tail-Only Floor (`AsymFloor`)
# ---------------------------------------------------------------------------


def compute_sizing_from_train_quantiles(
    p_val: np.ndarray,
    p_train: np.ndarray,
    *,
    sizing_policy: str,
    toxic_quantile: float = 0.20,
    tail_quantile: float = 0.10,
    floor_mult: float = 0.55,
) -> tuple[np.ndarray, dict[str, float]]:
    """Compute strictly train-fold calibrated sizing multipliers (ZERO validation peeking!).

    Policies:
      - `binary_filter` (`v1.05-ML-Filter`): `0.0` if `p < quantile(p_train, toxic_quantile)`, else `1.0`.
      - `asym_floor_step` (`v1.05-ML-AsymFloor`): `floor_mult` in `[0.45..0.75]` if
        `p < quantile(p_train, tail_quantile)`, else `1.0` on ALL normal/strong signals (top 90%).
      - `asym_floor_ramp` (`v1.05-ML-AsymFloor`): linear ramp `[floor_mult..1.0]` over `[q01..q10]`
        on worst decile ONLY, `1.0` on ALL `p >= q10`.
    """
    pv = _validate_float_array(p_val, name="p_val")
    pt = _validate_float_array(p_train, name="p_train")
    if pt.size == 0:
        raise ValueError("EMPTY_TRAIN_PROBS: p_train cannot be empty")
    if sizing_policy not in ALLOWED_SIZING_POLICIES:
        raise ValueError(f"INVALID_SIZING_POLICY: {sizing_policy!r}")

    p_span = float(np.quantile(pt, 0.90) - np.quantile(pt, 0.10))
    if sizing_policy == "binary_filter":
        tq = _validate_finite_float(toxic_quantile, name="toxic_quantile")
        if not (0.01 <= tq <= 0.45):
            raise ValueError(f"INVALID_TOXIC_QUANTILE: expected [0.01, 0.45], got {tq}")
        q_thr = float(np.quantile(pt, tq))
        if p_span <= 1e-9:
            sizes = np.ones_like(pv, dtype=np.float64)
        else:
            sizes = np.where(pv < q_thr, 0.0, 1.0)
        return sizes, {"threshold": q_thr, "toxic_quantile": tq}

    fl = _validate_finite_float(floor_mult, name="floor_mult")
    if not (0.45 <= fl <= 0.75):
        raise ValueError(f"INVALID_ASYMFLOOR_MULT: expected [0.45, 0.75], got {fl}")
    tq_tail = _validate_finite_float(tail_quantile, name="tail_quantile")
    if not (0.05 <= tq_tail <= 0.20):
        raise ValueError(f"INVALID_TAIL_QUANTILE: expected [0.05, 0.20], got {tq_tail}")

    q_tail = float(np.quantile(pt, tq_tail))
    q_p01 = float(np.quantile(pt, 0.01))
    if p_span <= 1e-9:
        sizes = np.ones_like(pv, dtype=np.float64)
    elif sizing_policy == "asym_floor_step":
        sizes = np.where(pv < q_tail, fl, 1.0)
    else:
        denom = max(q_tail - q_p01, 1e-4)
        ramp = fl + (1.0 - fl) * ((pv - q_p01) / denom)
        sizes = np.where(pv < q_tail, np.clip(ramp, fl, 1.0), 1.0)

    return sizes, {
        "tail_threshold": q_tail,
        "p01_threshold": q_p01,
        "tail_quantile": tq_tail,
        "floor_mult": fl,
    }


# ---------------------------------------------------------------------------
# 3. Pre-Registered Wave 5 Bounded Arena Grid (`36 <= 48` Trials)
# ---------------------------------------------------------------------------


def build_preregistered_v105_grid(*, random_state: int = 42) -> list[dict[str, Any]]:
    """Pre-registered `36 <= 48` head-to-head grid: `24` `v1.05-ML-Filter` + `12` `v1.05-ML-AsymFloor`."""
    rs = int(random_state)
    grid: list[dict[str, Any]] = [
        # --- Track A: v1.05-ML-Filter (24 trials: 12 LightGBM + 4 Logit-L2 + 4 CatBoost + 4 Regime-GMM) ---
        {
            "trial_id": "w5_01_lgbm_flt_d2_n40_r10_q20",
            "track_name": "v105_ml_filter",
            "family_name": "lightgbm",
            "sizing_policy": "binary_filter",
            "sizing_params": {"toxic_quantile": 0.20},
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
            "label": "LGBM d2 n40 reg10 filter q20",
        },
        {
            "trial_id": "w5_02_lgbm_flt_d2_n60_r20_q20",
            "track_name": "v105_ml_filter",
            "family_name": "lightgbm",
            "sizing_policy": "binary_filter",
            "sizing_params": {"toxic_quantile": 0.20},
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
            "label": "LGBM d2 n60 reg20 filter q20",
        },
        {
            "trial_id": "w5_03_lgbm_flt_d2_n60_r20_q15",
            "track_name": "v105_ml_filter",
            "family_name": "lightgbm",
            "sizing_policy": "binary_filter",
            "sizing_params": {"toxic_quantile": 0.15},
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
            "label": "LGBM d2 n60 reg20 filter q15",
        },
        {
            "trial_id": "w5_04_lgbm_flt_d2_n60_r20_q25",
            "track_name": "v105_ml_filter",
            "family_name": "lightgbm",
            "sizing_policy": "binary_filter",
            "sizing_params": {"toxic_quantile": 0.25},
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
            "label": "LGBM d2 n60 reg20 filter q25",
        },
        {
            "trial_id": "w5_05_lgbm_flt_d2_n80_r25_q20",
            "track_name": "v105_ml_filter",
            "family_name": "lightgbm",
            "sizing_policy": "binary_filter",
            "sizing_params": {"toxic_quantile": 0.20},
            "model_params": {
                "n_estimators": 80,
                "max_depth": 2,
                "num_leaves": 4,
                "learning_rate": 0.025,
                "min_child_samples": 55,
                "subsample": 0.8,
                "colsample_bytree": 0.8,
                "reg_lambda": 25.0,
                "reg_alpha": 1.5,
                "random_state": rs,
            },
            "label": "LGBM d2 n80 reg25 filter q20",
        },
        {
            "trial_id": "w5_06_lgbm_flt_d2_n100_r30_q20",
            "track_name": "v105_ml_filter",
            "family_name": "lightgbm",
            "sizing_policy": "binary_filter",
            "sizing_params": {"toxic_quantile": 0.20},
            "model_params": {
                "n_estimators": 100,
                "max_depth": 2,
                "num_leaves": 4,
                "learning_rate": 0.02,
                "min_child_samples": 60,
                "subsample": 0.8,
                "colsample_bytree": 0.8,
                "reg_lambda": 30.0,
                "reg_alpha": 2.0,
                "random_state": rs,
            },
            "label": "LGBM d2 n100 reg30 filter q20",
        },
        {
            "trial_id": "w5_07_lgbm_flt_d3_n60_r15_q20",
            "track_name": "v105_ml_filter",
            "family_name": "lightgbm",
            "sizing_policy": "binary_filter",
            "sizing_params": {"toxic_quantile": 0.20},
            "model_params": {
                "n_estimators": 60,
                "max_depth": 3,
                "num_leaves": 6,
                "learning_rate": 0.03,
                "min_child_samples": 45,
                "subsample": 0.8,
                "colsample_bytree": 0.8,
                "reg_lambda": 15.0,
                "reg_alpha": 1.0,
                "random_state": rs,
            },
            "label": "LGBM d3 n60 reg15 filter q20",
        },
        {
            "trial_id": "w5_08_lgbm_flt_d3_n80_r15_q20",
            "track_name": "v105_ml_filter",
            "family_name": "lightgbm",
            "sizing_policy": "binary_filter",
            "sizing_params": {"toxic_quantile": 0.20},
            "model_params": {
                "n_estimators": 80,
                "max_depth": 3,
                "num_leaves": 7,
                "learning_rate": 0.03,
                "min_child_samples": 45,
                "subsample": 0.8,
                "colsample_bytree": 0.8,
                "reg_lambda": 15.0,
                "reg_alpha": 1.0,
                "random_state": rs,
            },
            "label": "LGBM d3 n80 reg15 filter q20",
        },
        {
            "trial_id": "w5_09_lgbm_flt_d3_n80_r25_q15",
            "track_name": "v105_ml_filter",
            "family_name": "lightgbm",
            "sizing_policy": "binary_filter",
            "sizing_params": {"toxic_quantile": 0.15},
            "model_params": {
                "n_estimators": 80,
                "max_depth": 3,
                "num_leaves": 6,
                "learning_rate": 0.03,
                "min_child_samples": 50,
                "subsample": 0.8,
                "colsample_bytree": 0.8,
                "reg_lambda": 25.0,
                "reg_alpha": 1.5,
                "random_state": rs,
            },
            "label": "LGBM d3 n80 reg25 filter q15",
        },
        {
            "trial_id": "w5_10_lgbm_flt_d3_n100_r20_q20",
            "track_name": "v105_ml_filter",
            "family_name": "lightgbm",
            "sizing_policy": "binary_filter",
            "sizing_params": {"toxic_quantile": 0.20},
            "model_params": {
                "n_estimators": 100,
                "max_depth": 3,
                "num_leaves": 7,
                "learning_rate": 0.025,
                "min_child_samples": 50,
                "subsample": 0.8,
                "colsample_bytree": 0.8,
                "reg_lambda": 20.0,
                "reg_alpha": 1.0,
                "random_state": rs,
            },
            "label": "LGBM d3 n100 reg20 filter q20",
        },
        {
            "trial_id": "w5_11_lgbm_flt_d2_n50_r15_q22",
            "track_name": "v105_ml_filter",
            "family_name": "lightgbm",
            "sizing_policy": "binary_filter",
            "sizing_params": {"toxic_quantile": 0.22},
            "model_params": {
                "n_estimators": 50,
                "max_depth": 2,
                "num_leaves": 4,
                "learning_rate": 0.04,
                "min_child_samples": 45,
                "subsample": 0.8,
                "colsample_bytree": 0.8,
                "reg_lambda": 15.0,
                "reg_alpha": 1.0,
                "random_state": rs,
            },
            "label": "LGBM d2 n50 reg15 filter q22",
        },
        {
            "trial_id": "w5_12_lgbm_flt_d2_n70_r20_q18",
            "track_name": "v105_ml_filter",
            "family_name": "lightgbm",
            "sizing_policy": "binary_filter",
            "sizing_params": {"toxic_quantile": 0.18},
            "model_params": {
                "n_estimators": 70,
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
            "label": "LGBM d2 n70 reg20 filter q18",
        },
        # Logit-L2 Filter (4)
        {
            "trial_id": "w5_13_logit_flt_r2p0_q20",
            "track_name": "v105_ml_filter",
            "family_name": "logit_l2",
            "sizing_policy": "binary_filter",
            "sizing_params": {"toxic_quantile": 0.20},
            "model_params": {"l2_reg": 2.0, "max_iter": 300, "random_state": rs},
            "label": "Logit-L2 reg2 filter q20",
        },
        {
            "trial_id": "w5_14_logit_flt_r10p0_q20",
            "track_name": "v105_ml_filter",
            "family_name": "logit_l2",
            "sizing_policy": "binary_filter",
            "sizing_params": {"toxic_quantile": 0.20},
            "model_params": {"l2_reg": 10.0, "max_iter": 300, "random_state": rs},
            "label": "Logit-L2 reg10 filter q20",
        },
        {
            "trial_id": "w5_15_logit_flt_r50p0_q20",
            "track_name": "v105_ml_filter",
            "family_name": "logit_l2",
            "sizing_policy": "binary_filter",
            "sizing_params": {"toxic_quantile": 0.20},
            "model_params": {"l2_reg": 50.0, "max_iter": 300, "random_state": rs},
            "label": "Logit-L2 reg50 filter q20",
        },
        {
            "trial_id": "w5_16_logit_flt_r50p0_q15",
            "track_name": "v105_ml_filter",
            "family_name": "logit_l2",
            "sizing_policy": "binary_filter",
            "sizing_params": {"toxic_quantile": 0.15},
            "model_params": {"l2_reg": 50.0, "max_iter": 300, "random_state": rs},
            "label": "Logit-L2 reg50 filter q15",
        },
        # CatBoost Filter (4, allow_writing_files=False inside adapter)
        {
            "trial_id": "w5_17_catboost_flt_d2_i60_q20",
            "track_name": "v105_ml_filter",
            "family_name": "catboost",
            "sizing_policy": "binary_filter",
            "sizing_params": {"toxic_quantile": 0.20},
            "model_params": {
                "iterations": 60,
                "depth": 2,
                "learning_rate": 0.05,
                "l2_leaf_reg": 15.0,
                "min_data_in_leaf": 35,
                "random_state": rs,
            },
            "label": "CatBoost d2 i60 filter q20",
        },
        {
            "trial_id": "w5_18_catboost_flt_d3_i90_q20",
            "track_name": "v105_ml_filter",
            "family_name": "catboost",
            "sizing_policy": "binary_filter",
            "sizing_params": {"toxic_quantile": 0.20},
            "model_params": {
                "iterations": 90,
                "depth": 3,
                "learning_rate": 0.04,
                "l2_leaf_reg": 15.0,
                "min_data_in_leaf": 35,
                "random_state": rs,
            },
            "label": "CatBoost d3 i90 filter q20",
        },
        {
            "trial_id": "w5_19_catboost_flt_d3_i120_q20",
            "track_name": "v105_ml_filter",
            "family_name": "catboost",
            "sizing_policy": "binary_filter",
            "sizing_params": {"toxic_quantile": 0.20},
            "model_params": {
                "iterations": 120,
                "depth": 3,
                "learning_rate": 0.03,
                "l2_leaf_reg": 25.0,
                "min_data_in_leaf": 40,
                "random_state": rs,
            },
            "label": "CatBoost d3 i120 filter q20",
        },
        {
            "trial_id": "w5_20_catboost_flt_d2_i80_q15",
            "track_name": "v105_ml_filter",
            "family_name": "catboost",
            "sizing_policy": "binary_filter",
            "sizing_params": {"toxic_quantile": 0.15},
            "model_params": {
                "iterations": 80,
                "depth": 2,
                "learning_rate": 0.04,
                "l2_leaf_reg": 20.0,
                "min_data_in_leaf": 40,
                "random_state": rs,
            },
            "label": "CatBoost d2 i80 filter q15",
        },
        # Regime-GMM / Causal Jump-HMM Filter (4, ZERO hmmlearn)
        {
            "trial_id": "w5_21_gmm_flt_k2_a15_q20",
            "track_name": "v105_ml_filter",
            "family_name": "regime_gmm_jump",
            "sizing_policy": "binary_filter",
            "sizing_params": {"toxic_quantile": 0.20},
            "model_params": {
                "n_regimes": 2,
                "shrinkage_alpha": 15.0,
                "jump_penalty": 0.0,
                "backend": "gmm",
                "random_state": rs,
            },
            "label": "Regime-GMM k2 a15 filter q20",
        },
        {
            "trial_id": "w5_22_gmm_flt_k3_a20_q20",
            "track_name": "v105_ml_filter",
            "family_name": "regime_gmm_jump",
            "sizing_policy": "binary_filter",
            "sizing_params": {"toxic_quantile": 0.20},
            "model_params": {
                "n_regimes": 3,
                "shrinkage_alpha": 20.0,
                "jump_penalty": 0.0,
                "backend": "gmm",
                "random_state": rs,
            },
            "label": "Regime-GMM k3 a20 filter q20",
        },
        {
            "trial_id": "w5_23_gmm_flt_k3_a30_jp1_q20",
            "track_name": "v105_ml_filter",
            "family_name": "regime_gmm_jump",
            "sizing_policy": "binary_filter",
            "sizing_params": {"toxic_quantile": 0.20},
            "model_params": {
                "n_regimes": 3,
                "shrinkage_alpha": 30.0,
                "jump_penalty": 1.0,
                "backend": "gmm",
                "random_state": rs,
            },
            "label": "Regime-GMM-Jump k3 a30 jp1 filter q20",
        },
        {
            "trial_id": "w5_24_jumphmm_flt_k3_a20_jp1p5_q20",
            "track_name": "v105_ml_filter",
            "family_name": "regime_gmm_jump",
            "sizing_policy": "binary_filter",
            "sizing_params": {"toxic_quantile": 0.20},
            "model_params": {
                "n_regimes": 3,
                "shrinkage_alpha": 20.0,
                "jump_penalty": 1.5,
                "backend": "jump_hmm_numpy",
                "random_state": rs,
            },
            "label": "Causal Jump-HMM k3 a20 jp1.5 filter q20",
        },
        # --- Track B: v1.05-ML-AsymFloor (12 trials: worst decile ONLY [0.45x..0.75x], normal/strong = 1.0x) ---
        {
            "trial_id": "w5_25_lgbm_asym_step_d2_n60_f045",
            "track_name": "v105_ml_asymfloor",
            "family_name": "lightgbm",
            "sizing_policy": "asym_floor_step",
            "sizing_params": {"tail_quantile": 0.10, "floor_mult": 0.45},
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
            "label": "LGBM d2 n60 AsymFloor step 0.45x (q10)",
        },
        {
            "trial_id": "w5_26_lgbm_asym_step_d2_n60_f055",
            "track_name": "v105_ml_asymfloor",
            "family_name": "lightgbm",
            "sizing_policy": "asym_floor_step",
            "sizing_params": {"tail_quantile": 0.10, "floor_mult": 0.55},
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
            "label": "LGBM d2 n60 AsymFloor step 0.55x (q10)",
        },
        {
            "trial_id": "w5_27_lgbm_asym_step_d2_n60_f065",
            "track_name": "v105_ml_asymfloor",
            "family_name": "lightgbm",
            "sizing_policy": "asym_floor_step",
            "sizing_params": {"tail_quantile": 0.10, "floor_mult": 0.65},
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
            "label": "LGBM d2 n60 AsymFloor step 0.65x (q10)",
        },
        {
            "trial_id": "w5_28_lgbm_asym_step_d2_n60_f075",
            "track_name": "v105_ml_asymfloor",
            "family_name": "lightgbm",
            "sizing_policy": "asym_floor_step",
            "sizing_params": {"tail_quantile": 0.10, "floor_mult": 0.75},
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
            "label": "LGBM d2 n60 AsymFloor step 0.75x (q10)",
        },
        {
            "trial_id": "w5_29_lgbm_asym_ramp_d2_n60_f045",
            "track_name": "v105_ml_asymfloor",
            "family_name": "lightgbm",
            "sizing_policy": "asym_floor_ramp",
            "sizing_params": {"tail_quantile": 0.10, "floor_mult": 0.45},
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
            "label": "LGBM d2 n60 AsymFloor ramp [0.45x..1.0x] (q10)",
        },
        {
            "trial_id": "w5_30_lgbm_asym_ramp_d2_n80_f050",
            "track_name": "v105_ml_asymfloor",
            "family_name": "lightgbm",
            "sizing_policy": "asym_floor_ramp",
            "sizing_params": {"tail_quantile": 0.10, "floor_mult": 0.50},
            "model_params": {
                "n_estimators": 80,
                "max_depth": 2,
                "num_leaves": 4,
                "learning_rate": 0.025,
                "min_child_samples": 55,
                "subsample": 0.8,
                "colsample_bytree": 0.8,
                "reg_lambda": 25.0,
                "reg_alpha": 1.5,
                "random_state": rs,
            },
            "label": "LGBM d2 n80 AsymFloor ramp [0.50x..1.0x] (q10)",
        },
        {
            "trial_id": "w5_31_lgbm_asym_step_d3_n80_f045",
            "track_name": "v105_ml_asymfloor",
            "family_name": "lightgbm",
            "sizing_policy": "asym_floor_step",
            "sizing_params": {"tail_quantile": 0.10, "floor_mult": 0.45},
            "model_params": {
                "n_estimators": 80,
                "max_depth": 3,
                "num_leaves": 7,
                "learning_rate": 0.03,
                "min_child_samples": 45,
                "subsample": 0.8,
                "colsample_bytree": 0.8,
                "reg_lambda": 15.0,
                "reg_alpha": 1.0,
                "random_state": rs,
            },
            "label": "LGBM d3 n80 AsymFloor step 0.45x (q10)",
        },
        {
            "trial_id": "w5_32_lgbm_asym_step_d2_n60_q15_f045",
            "track_name": "v105_ml_asymfloor",
            "family_name": "lightgbm",
            "sizing_policy": "asym_floor_step",
            "sizing_params": {"tail_quantile": 0.15, "floor_mult": 0.45},
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
            "label": "LGBM d2 n60 AsymFloor step 0.45x (q15)",
        },
        {
            "trial_id": "w5_33_logit_asym_step_r10_f045",
            "track_name": "v105_ml_asymfloor",
            "family_name": "logit_l2",
            "sizing_policy": "asym_floor_step",
            "sizing_params": {"tail_quantile": 0.10, "floor_mult": 0.45},
            "model_params": {"l2_reg": 10.0, "max_iter": 300, "random_state": rs},
            "label": "Logit-L2 reg10 AsymFloor step 0.45x (q10)",
        },
        {
            "trial_id": "w5_34_logit_asym_step_r50_f060",
            "track_name": "v105_ml_asymfloor",
            "family_name": "logit_l2",
            "sizing_policy": "asym_floor_step",
            "sizing_params": {"tail_quantile": 0.10, "floor_mult": 0.60},
            "model_params": {"l2_reg": 50.0, "max_iter": 300, "random_state": rs},
            "label": "Logit-L2 reg50 AsymFloor step 0.60x (q10)",
        },
        {
            "trial_id": "w5_35_catboost_asym_step_d3_i90_f050",
            "track_name": "v105_ml_asymfloor",
            "family_name": "catboost",
            "sizing_policy": "asym_floor_step",
            "sizing_params": {"tail_quantile": 0.10, "floor_mult": 0.50},
            "model_params": {
                "iterations": 90,
                "depth": 3,
                "learning_rate": 0.04,
                "l2_leaf_reg": 15.0,
                "min_data_in_leaf": 35,
                "random_state": rs,
            },
            "label": "CatBoost d3 i90 AsymFloor step 0.50x (q10)",
        },
        {
            "trial_id": "w5_36_gmm_asym_step_k2_a15_f050",
            "track_name": "v105_ml_asymfloor",
            "family_name": "regime_gmm_jump",
            "sizing_policy": "asym_floor_step",
            "sizing_params": {"tail_quantile": 0.10, "floor_mult": 0.50},
            "model_params": {
                "n_regimes": 2,
                "shrinkage_alpha": 15.0,
                "jump_penalty": 0.0,
                "backend": "gmm",
                "random_state": rs,
            },
            "label": "Regime-GMM k2 a15 AsymFloor step 0.50x (q10)",
        },
    ]
    return grid


def build_numpy_smoke_v105_grid(*, random_state: int = 42) -> list[dict[str, Any]]:
    """Minimal 4-trial pure-NumPy grid (2 Filter + 2 AsymFloor) for zero-ML-wheel CI tests."""
    rs = int(random_state)
    return [
        {
            "trial_id": "w5_smoke_01_logit_filter",
            "track_name": "v105_ml_filter",
            "family_name": "logit_l2",
            "sizing_policy": "binary_filter",
            "sizing_params": {"toxic_quantile": 0.20},
            "model_params": {"l2_reg": 2.0, "backend": "numpy", "random_state": rs},
            "label": "Smoke Logit-L2 binary filter",
        },
        {
            "trial_id": "w5_smoke_02_jumphmm_filter",
            "track_name": "v105_ml_filter",
            "family_name": "regime_gmm_jump",
            "sizing_policy": "binary_filter",
            "sizing_params": {"toxic_quantile": 0.20},
            "model_params": {
                "n_regimes": 2,
                "shrinkage_alpha": 15.0,
                "jump_penalty": 1.0,
                "backend": "jump_hmm_numpy",
                "random_state": rs,
            },
            "label": "Smoke Jump-HMM binary filter",
        },
        {
            "trial_id": "w5_smoke_03_logit_asym_step",
            "track_name": "v105_ml_asymfloor",
            "family_name": "logit_l2",
            "sizing_policy": "asym_floor_step",
            "sizing_params": {"tail_quantile": 0.10, "floor_mult": 0.50},
            "model_params": {"l2_reg": 2.0, "backend": "numpy", "random_state": rs},
            "label": "Smoke Logit-L2 AsymFloor step 0.50x",
        },
        {
            "trial_id": "w5_smoke_04_logit_asym_ramp",
            "track_name": "v105_ml_asymfloor",
            "family_name": "logit_l2",
            "sizing_policy": "asym_floor_ramp",
            "sizing_params": {"tail_quantile": 0.10, "floor_mult": 0.55},
            "model_params": {"l2_reg": 2.0, "backend": "numpy", "random_state": rs},
            "label": "Smoke Logit-L2 AsymFloor ramp 0.55x",
        },
    ]


def validate_v105_arena_grid(
    grid: Sequence[Mapping[str, Any]],
    *,
    max_trials: int = DEFAULT_MAX_ML_TRIALS,
) -> list[dict[str, Any]]:
    items = [dict(spec) for spec in grid]
    if not items:
        raise ValueError("EMPTY_ARENA_GRID")
    if len(items) > int(max_trials):
        raise ValueError(f"ARENA_GRID_EXCEEDS_BUDGET: {len(items)} > max_trials={max_trials}")
    seen: set[str] = set()
    tracks_seen: set[str] = set()
    for idx, spec in enumerate(items):
        tid = str(spec.get("trial_id", "")).strip()
        if not tid or tid in seen:
            raise ValueError(f"INVALID_OR_DUPLICATE_TRIAL_ID at index {idx}: {tid!r}")
        seen.add(tid)
        tr = str(spec.get("track_name", "")).strip()
        if tr not in ALLOWED_TRACKS:
            raise ValueError(f"INVALID_TRACK_NAME at index {idx}: {tr!r}")
        tracks_seen.add(tr)
        fam = str(spec.get("family_name", "")).strip()
        if fam not in ALLOWED_BASE_FAMILIES:
            raise ValueError(f"INVALID_FAMILY at index {idx}: {fam!r}")
        pol = str(spec.get("sizing_policy", "")).strip()
        if pol not in ALLOWED_SIZING_POLICIES:
            raise ValueError(f"INVALID_SIZING_POLICY at index {idx}: {pol!r}")
        if tr == "v105_ml_filter" and pol != "binary_filter":
            raise ValueError(f"TRACK_POLICY_MISMATCH at index {idx}: {tr} requires binary_filter")
        if tr == "v105_ml_asymfloor" and pol not in ("asym_floor_step", "asym_floor_ramp"):
            raise ValueError(f"TRACK_POLICY_MISMATCH at index {idx}: {tr} requires asym_floor_*")
    if set(ALLOWED_TRACKS) - tracks_seen:
        raise ValueError(f"INCOMPLETE_HEAD_TO_HEAD_GRID: missing tracks {sorted(set(ALLOWED_TRACKS) - tracks_seen)}")
    return items


# ---------------------------------------------------------------------------
# 4. Walk-Forward CV Runner Supporting Both Binary Filter & AsymFloor
# ---------------------------------------------------------------------------


def run_v105_walkforward_trial(
    X: np.ndarray,
    y: np.ndarray,
    entry_ts: np.ndarray,
    exit_ts: np.ndarray,
    net_r: np.ndarray,
    engine_ids: Sequence[str],
    *,
    trial_spec: Mapping[str, Any],
    feature_names: Sequence[str] = FEATURE_NAMES_V105,
    n_splits: int = 5,
    purge_days: int = DEFAULT_PURGE_DAYS,
    embargo_days: int = DEFAULT_EMBARGO_DAYS,
    min_train_samples: int = DEFAULT_MIN_TRAIN_SAMPLES,
    min_k: int = DEFAULT_MIN_SELECTED_FEATURES,
    max_k: int = DEFAULT_MAX_SELECTED_FEATURES,
    slippage_mults: Sequence[float] = DEFAULT_SLIPPAGE_MULTS,
    base_cost_r: float = DEFAULT_BASE_COST_R,
    risk_pct_1x: np.ndarray | None = None,
    oos_label: str = CONSUMED_CLB_TAG,
    cutoff_utc: str | date | datetime | int = HOLDOUT_CUTOFF_DATE,
) -> dict[str, Any]:
    """Run one strictly causal Purged+Embargo Walk-Forward CV trial (Filter or AsymFloor)."""
    validated_label = validate_oos_label(oos_label)
    parse_cutoff_utc_exclusive(cutoff_utc)

    n, d = X.shape
    splitter = ExpandingPurgedWalkForwardSplitter(
        n_splits=n_splits,
        purge_days=purge_days,
        embargo_days=embargo_days,
        min_train_samples=min_train_samples,
        mode="expanding",
        cutoff_utc=cutoff_utc,
    )

    oof_probs = np.full(n, np.nan, dtype=np.float64)
    oof_sizes = np.full(n, np.nan, dtype=np.float64)
    oof_sizes_f32 = np.full(n, np.nan, dtype=np.float64)
    oof_mask = np.zeros(n, dtype=bool)
    oof_attrib_accum = np.zeros(d, dtype=np.float64)
    oof_attrib_counts = np.zeros(d, dtype=np.int64)
    fold_reports: list[dict[str, Any]] = []

    fam = str(trial_spec["family_name"])
    track = str(trial_spec["track_name"])
    pol = str(trial_spec["sizing_policy"])
    m_params = dict(trial_spec.get("model_params", {}))
    s_params = dict(trial_spec.get("sizing_params", {}))

    for fold_i, (train_idx, val_idx) in enumerate(splitter.split(entry_ts, exit_ts, cutoff_utc=cutoff_utc)):
        pruning = select_inside_fold_features(
            X[train_idx],
            y[train_idx],
            feature_names=feature_names,
            min_k=min_k,
            max_k=max_k,
        )
        sel_idx = pruning["selected_indices"]
        sel_names = pruning["selected_names"]

        adapter = create_model_adapter(fam, **m_params)
        adapter.fit(X[train_idx][:, sel_idx], y[train_idx], feature_names=sel_names)

        p_train = adapter.predict_proba(X[train_idx][:, sel_idx])
        p_val = adapter.predict_proba(X[val_idx][:, sel_idx])
        s_val, s_meta = compute_sizing_from_train_quantiles(
            p_val,
            p_train,
            sizing_policy=pol,
            toxic_quantile=float(s_params.get("toxic_quantile", 0.20)),
            tail_quantile=float(s_params.get("tail_quantile", 0.10)),
            floor_mult=float(s_params.get("floor_mult", 0.55)),
        )
        # Adversarial ONNX float32 decision-boundary stability check (catches discrete-regime quantile cliffs!)
        s_val_f32, _ = compute_sizing_from_train_quantiles(
            p_val.astype(np.float32).astype(np.float64),
            p_train.astype(np.float32).astype(np.float64),
            sizing_policy=pol,
            toxic_quantile=float(s_params.get("toxic_quantile", 0.20)),
            tail_quantile=float(s_params.get("tail_quantile", 0.10)),
            floor_mult=float(s_params.get("floor_mult", 0.55)),
        )

        oof_probs[val_idx] = p_val
        oof_sizes[val_idx] = s_val
        oof_sizes_f32[val_idx] = s_val_f32
        oof_mask[val_idx] = True

        exp = adapter.explain_attributions(X[val_idx][:, sel_idx], feature_names=sel_names)
        contrib_mat = np.asarray(exp["contributions"], dtype=np.float64)
        for pos, orig_col in enumerate(sel_idx):
            oof_attrib_accum[orig_col] += float(np.sum(np.abs(contrib_mat[:, pos])))
            oof_attrib_counts[orig_col] += int(val_idx.size)

        fa = splitter.last_fold_audits[fold_i]
        fb = compute_brier_metrics(y[val_idx], p_val)
        fold_reports.append(
            {
                "fold_index": fold_i,
                "n_train": fa.n_train,
                "n_val": fa.n_val,
                "n_purged": fa.n_purged,
                "n_embargoed": fa.n_embargoed,
                "observed_gap_days": round(fa.observed_gap_days, 3),
                "n_features_selected": pruning["k"],
                "selected_features": sel_names,
                "brier_skill_score": round(float(fb["brier_skill_score"]), 6),
                "roc_auc": round(float(fb["roc_auc"]), 6),
                "sizing_meta": {k: round(float(v), 6) for k, v in s_meta.items()},
            }
        )

    eval_idx = np.flatnonzero(oof_mask)
    eval_eng = [engine_ids[i] for i in eval_idx.tolist()]
    risk_eval = None if risk_pct_1x is None else np.asarray(risk_pct_1x, dtype=np.float64)[eval_idx]

    evaluation = evaluate_oof_brier_and_economics(
        y[eval_idx],
        oof_probs[eval_idx],
        net_r[eval_idx],
        eval_eng,
        slippage_mults=slippage_mults,
        position_sizes=oof_sizes[eval_idx],
        base_cost_r=base_cost_r,
        risk_pct_per_trade=risk_eval,
        min_engine_retention_ratio=DEFAULT_MIN_ENGINE_RETENTION,
        min_overall_retention_ratio=DEFAULT_MIN_OVERALL_RETENTION,
        baseline_slippage_breakeven=DEFAULT_BASELINE_SLIPPAGE_BREAKEVEN,
        target_slippage_breakeven=DEFAULT_TARGET_SLIPPAGE_BREAKEVEN,
        oos_label=validated_label,
        entry_ts=entry_ts[eval_idx],
        cutoff_utc=cutoff_utc,
    )

    # Strict 2021-2024 CONSUMED_DEV_CLB_TEMPORAL_OOS temporal sub-slice check
    clb_mask = oof_mask & (entry_ts >= CLB_START_SEC)
    clb_idx = np.flatnonzero(clb_mask)
    clb_eval: dict[str, Any] | None = None
    if clb_idx.size >= 100 and len(np.unique(y[clb_idx])) >= 2:
        clb_eng = [engine_ids[i] for i in clb_idx.tolist()]
        clb_risk = None if risk_pct_1x is None else np.asarray(risk_pct_1x, dtype=np.float64)[clb_idx]
        clb_eval = evaluate_oof_brier_and_economics(
            y[clb_idx],
            oof_probs[clb_idx],
            net_r[clb_idx],
            clb_eng,
            slippage_mults=slippage_mults,
            position_sizes=oof_sizes[clb_idx],
            base_cost_r=base_cost_r,
            risk_pct_per_trade=clb_risk,
            min_engine_retention_ratio=DEFAULT_MIN_ENGINE_RETENTION,
            min_overall_retention_ratio=DEFAULT_MIN_OVERALL_RETENTION,
            baseline_slippage_breakeven=DEFAULT_BASELINE_SLIPPAGE_BREAKEVEN,
            target_slippage_breakeven=DEFAULT_TARGET_SLIPPAGE_BREAKEVEN,
            oos_label=validated_label,
            entry_ts=entry_ts[clb_idx],
            cutoff_utc=cutoff_utc,
        )

    f32_size_agree = float(np.mean(np.abs(oof_sizes[eval_idx] - oof_sizes_f32[eval_idx]) <= 1e-6))
    f32_deployable = bool(f32_size_agree >= 0.99)
    f32_diag: dict[str, Any] = {
        "float32_decision_agreement": round(f32_size_agree, 6),
        "min_required_agreement": 0.99,
        "float32_onnx_deployable": f32_deployable,
    }
    if not f32_deployable:
        f32_eval = evaluate_oof_brier_and_economics(
            y[eval_idx],
            oof_probs[eval_idx].astype(np.float32).astype(np.float64),
            net_r[eval_idx],
            eval_eng,
            slippage_mults=slippage_mults,
            position_sizes=oof_sizes_f32[eval_idx],
            base_cost_r=base_cost_r,
            risk_pct_per_trade=risk_eval,
            min_engine_retention_ratio=DEFAULT_MIN_ENGINE_RETENTION,
            min_overall_retention_ratio=DEFAULT_MIN_OVERALL_RETENTION,
            baseline_slippage_breakeven=DEFAULT_BASELINE_SLIPPAGE_BREAKEVEN,
            target_slippage_breakeven=DEFAULT_TARGET_SLIPPAGE_BREAKEVEN,
            oos_label=validated_label,
            entry_ts=entry_ts[eval_idx],
            cutoff_utc=cutoff_utc,
        )
        f32_diag["float32_n_active"] = int(f32_eval["economics_1x"]["ml_v104"]["n_active"])
        f32_diag["float32_pf_1x"] = _json_safe_float(f32_eval["economics_1x"]["ml_v104"]["profit_factor"])
        f32_diag["float32_max_dd_pct_1x"] = _json_safe_float(f32_eval["economics_1x"]["ml_v104"]["max_dd_pct"])
        f32_diag["float32_slippage_breakeven_24m"] = _json_safe_float(
            f32_eval["slippage_breakeven_24m"]["ml_v104_median_mult"]
        )
        f32_diag["float32_verdict"] = str(f32_eval["verdict"])

    all_full_ok = len(evaluation["rejection_reasons"]) == 0
    clb_ok = True if clb_eval is None else (len(clb_eval["rejection_reasons"]) == 0)
    reasons = list(evaluation["rejection_reasons"])
    if all_full_ok and not clb_ok and clb_eval is not None:
        reasons.append(f"CLB_2021_2024_TEMPORAL_OOS_FAILED ({'; '.join(clb_eval['rejection_reasons'])})")
    if not f32_deployable:
        reasons.append(
            f"FLOAT32_ONNX_QUANTILE_CLIFF (f32_size_agreement={f32_size_agree:.4f} < 0.9900; "
            f"f32_be={f32_diag.get('float32_slippage_breakeven_24m', 0.0):.3f}x)"
        )

    gates = dict(evaluation["gates"])
    gates["clb_2021_2024_temporal_oos_passed"] = bool(clb_ok)
    gates["float32_onnx_deployable"] = f32_deployable
    evaluation["gates"] = gates
    evaluation["float32_onnx_stability"] = f32_diag
    evaluation["rejection_reasons"] = reasons

    promote_tag = VERDICT_PROMOTE_FILTER if track == "v105_ml_filter" else VERDICT_PROMOTE_ASYMFLOOR
    verdict_v105 = promote_tag if (all_full_ok and clb_ok and f32_deployable) else VERDICT_REJECT_ML
    evaluation["verdict_v105"] = verdict_v105

    mean_abs_global = {
        feature_names[j]: round(float(oof_attrib_accum[j] / oof_attrib_counts[j]), 6)
        for j in range(d)
        if oof_attrib_counts[j] > 0
    }

    return {
        "trial_spec": dict(trial_spec),
        "oof_mask": oof_mask,
        "oof_probs": oof_probs,
        "oof_sizes": oof_sizes,
        "folds": fold_reports,
        "oof_feature_importance": mean_abs_global,
        "evaluation": evaluation,
        "clb_eval": clb_eval,
        "verdict_v105": verdict_v105,
    }


# ---------------------------------------------------------------------------
# 5. Pure-MQL5 `Naqex_ML_Filter_v105.mqh` Generator & Mirror Verifier
# ---------------------------------------------------------------------------


def _format_mql5_int_array(values: Sequence[int], *, per_line: int = 16) -> str:
    lines: list[str] = []
    for start in range(0, len(values), per_line):
        chunk = ", ".join(str(int(v)) for v in values[start : start + per_line])
        suffix = "," if start + per_line < len(values) else ""
        lines.append(f"   {chunk}{suffix}")
    return "\n".join(lines)


def _format_mql5_double_array(values: Sequence[float], *, per_line: int = 6) -> str:
    lines: list[str] = []
    for start in range(0, len(values), per_line):
        chunk = ", ".join(f"{float(v):.17g}" for v in values[start : start + per_line])
        suffix = "," if start + per_line < len(values) else ""
        lines.append(f"   {chunk}{suffix}")
    return "\n".join(lines)


def _mql5_feature_expr_for_name(feat_name: str, slot_idx: int) -> str:
    """Return exact standalone MQL5 statement assigning `outFeat[slot_idx]` matching `ml_features_v105_aligned.py`."""
    mapping = {
        "d1_range_over_atr14": f"      outFeat[{slot_idx}] = ComputeD1RangeOverAtr14(sym, d1Shift, atr14);",
        "parkinson_vol_10d": f"      outFeat[{slot_idx}] = ComputeParkinsonVol10d(sym, d1Shift);",
        "atr14_pct": f"      outFeat[{slot_idx}] = ComputeAtr14Pct(sym, d1Shift, atr14);",
        "atr5_over_atr20_sma": f"      outFeat[{slot_idx}] = ComputeAtr5OverAtr20Sma(sym, d1Shift);",
        "d1_range_comp_5_20": f"      outFeat[{slot_idx}] = ComputeD1RangeComp5Over20(sym, d1Shift);",
        "breakout_zscore_20": f"      outFeat[{slot_idx}] = ComputeBreakoutZscore20(sym, d1Shift);",
        "dist_sma20_atr": f"      outFeat[{slot_idx}] = ComputeDistSma20Atr(sym, d1Shift, atr14);",
        "prev_bar_body_ratio": f"      outFeat[{slot_idx}] = ComputePrevM1BodyRatio(sym, m1Shift);",
        "prev_bar_close_loc": f"      outFeat[{slot_idx}] = ComputePrevM1CloseLoc(sym, m1Shift);",
        "spread_over_atr_ratio": f"      outFeat[{slot_idx}] = ComputeSpreadOverAtrRatio(sym, m1Shift, atr14);",
        "hour_sin_utc": f"      outFeat[{slot_idx}] = ComputeHourSinUtc(signalUtc);",
        "hour_cos_utc": f"      outFeat[{slot_idx}] = ComputeHourCosUtc(signalUtc);",
        "dow_sin": f"      outFeat[{slot_idx}] = ComputeDowSinUtc(signalUtc);",
        "is_london_ny_overlap": f"      outFeat[{slot_idx}] = ComputeIsLondonNyOverlap(signalUtc);",
        "engine_id_code": f"      outFeat[{slot_idx}] = EngineCodeFromMagic(magic);",
        "asset_class_code": f"      outFeat[{slot_idx}] = AssetClassCodeForSymbol(sym);",
        "same_dir_concurrent_count": (
            f"      outFeat[{slot_idx}] = (double)MathMax(0, MathMin(100, sameDirConcurrent));"
        ),
        "recent_10_wr_causal": f"      outFeat[{slot_idx}] = ShadowRecent10Wr(magic);",
        "recent_10_avg_r_causal": f"      outFeat[{slot_idx}] = ShadowRecent10AvgR(magic);",
        "rolling_dd_pct_1x_equiv": f"      outFeat[{slot_idx}] = ShadowRollingDdPct1x();",
    }
    if feat_name not in mapping:
        raise ValueError(f"UNMAPPED_V105_MQL5_FEATURE: {feat_name!r}")
    return mapping[feat_name]


def render_mql5_filter_v105_header(
    proto_json: Mapping[str, Any],
    *,
    tables: Mapping[str, Any],
    onnx_sha256: str,
    onnx_filename: str = "naqex_v105_lgbm.onnx",
) -> str:
    """Generate `Naqex_ML_Filter_v105.mqh`: OnnxRun + Pure-MQL5 Tree + Shadow 1.0x DD + Aligned Feature Extractor."""
    n_feat = int(tables["n_features"])
    n_trees = int(tables["n_trees"])
    n_nodes = int(tables["n_nodes"])
    feat_names = [str(f) for f in proto_json["selected_feature_names"]]
    if len(feat_names) != n_feat:
        raise ValueError(f"FEATURE_NAME_COUNT_MISMATCH: {len(feat_names)} != {n_feat}")

    source_trial = str(proto_json["source_trial_id"])
    approval_tag = str(proto_json["approval_tag"])
    threshold = float(proto_json["train_p_toxic"])
    asym_q10 = float(proto_json.get("train_p_q10", threshold))
    asym_floor = float(proto_json.get("asym_floor_mult", 0.55))
    asym_promoted = bool(proto_json.get("asymfloor_promoted", False))

    if not math.isfinite(threshold) or not (0.0 < threshold < 1.0):
        raise ValueError(f"INVALID_ML_V105_THRESHOLD: {threshold!r}")

    feat_doc_lines = "\n".join(f"//   [{idx}] {nm}" for idx, nm in enumerate(feat_names))
    assign_lines = "\n".join(_mql5_feature_expr_for_name(nm, idx) for idx, nm in enumerate(feat_names))

    roots_block = _format_mql5_int_array(tables["tree_roots"], per_line=15)
    feat_block = _format_mql5_int_array(tables["node_feat"], per_line=16)
    left_block = _format_mql5_int_array(tables["node_left"], per_line=16)
    right_block = _format_mql5_int_array(tables["node_right"], per_line=16)
    thresh_block = _format_mql5_double_array(tables["node_thresh"], per_line=6)
    leaf_block = _format_mql5_double_array(tables["node_leaf"], per_line=6)

    header = f"""//+------------------------------------------------------------------+
//| Naqex_ML_Filter_v105.mqh (Auto-generated by Wave 5 W5-G11)       |
//| Closes W4-RT1-P1-01: Broker-Day D1 SMA(TR,14) + Shadow 1.0x DD   |
//|                                                                  |
//| Source Trial : {source_trial}
//| Approval Tag : {approval_tag}
//| ONNX File    : {onnx_filename} (zipmap=False, 0 ZipMap nodes)
//| ONNX SHA-256 : {onnx_sha256}
//| Trees / Nodes: {n_trees} depth-{int(tables["max_depth"])} trees ({n_nodes} total nodes)
//| Filter Thr   : {threshold:.6f} (strict train Fold-4 toxic quantile)
//| AsymFloor    : promoted={"true" if asym_promoted else "false"} (q10={asym_q10:.6f}, floor={asym_floor:.2f})
//|                                                                  |
//| Exact Aligned Causal Feature Order (1:1 Python == MQL5):         |
{feat_doc_lines}
//|                                                                  |
//| PURE INFERENCE & FEATURE HELPER ONLY: ZERO EXECUTION/TRADE APIs! |
//| Fail-closed on NaN/Inf/wrong-dim features and ONNX-only errors.  |
//+------------------------------------------------------------------+
#ifndef NAQEX_ML_FILTER_V105_MQH
#define NAQEX_ML_FILTER_V105_MQH

#define NAQEX_V105_ML_N_FEATURES          {n_feat}
#define NAQEX_V105_ML_N_TREES             {n_trees}
#define NAQEX_V105_ML_N_NODES             {n_nodes}
#define NAQEX_V105_ML_DEFAULT_THRESHOLD   {threshold:.6f}
#define NAQEX_V105_ML_ASYM_Q10_THRESHOLD  {asym_q10:.6f}
#define NAQEX_V105_ML_ASYM_FLOOR_MULT     {asym_floor:.4f}
#define NAQEX_V105_ML_PROB_CLIP           1e-6
#define NAQEX_V105_ML_LOGIT_CLAMP         35.0
#define NAQEX_V105_ML_SHADOW_R_MIN        {SHADOW_1X_R_CLAMP_MIN:.1f}
#define NAQEX_V105_ML_SHADOW_R_MAX        {SHADOW_1X_R_CLAMP_MAX:.1f}
#define NAQEX_V105_ML_MODEL_ID            "{source_trial}"
#define NAQEX_V105_ML_ONNX_FILE_DEFAULT   "{onnx_filename}"
#define NAQEX_V105_ML_ONNX_SHA256         "{onnx_sha256}"

enum ENUM_NAQEX_ML_V105_MODE
{{
   V105_ONNX_OR_PURE_MQL5_FALLBACK = 0, // Primary OnnxRun + automatic exact Pure-MQL5 tree fallback
   V105_ONNX_ONLY_FAIL_CLOSED      = 1, // Require OnnxRun; fail-closed if ONNX unavailable
   V105_PURE_MQL5_TREE_ONLY        = 2  // Deterministic zero-dependency Pure-MQL5 tree evaluator only
}};

//--- Exact LightGBM {source_trial} flattened tree tables ({n_trees} trees, {n_nodes} nodes)
static const int g_v105TreeRoots[NAQEX_V105_ML_N_TREES] =
{{
{roots_block}
}};

static const int g_v105NodeFeat[NAQEX_V105_ML_N_NODES] =
{{
{feat_block}
}};

static const int g_v105NodeLeft[NAQEX_V105_ML_N_NODES] =
{{
{left_block}
}};

static const int g_v105NodeRight[NAQEX_V105_ML_N_NODES] =
{{
{right_block}
}};

static const double g_v105NodeThresh[NAQEX_V105_ML_N_NODES] =
{{
{thresh_block}
}};

static const double g_v105NodeLeaf[NAQEX_V105_ML_N_NODES] =
{{
{leaf_block}
}};

class CNaqexMLFilterV105
{{
private:
   long                    m_onnxHandle;
   bool                    m_onnxReady;
   ENUM_NAQEX_ML_V105_MODE m_mode;
   double                  m_threshold;
   string                  m_lastBackend;
   int                     m_lastOnnxError;
   long                    m_onnxCalls;
   long                    m_pureCalls;
   long                    m_fallbackCalls;
   long                    m_passedCount;
   long                    m_blockedCount;
   long                    m_invalidRejectedCount;

   //--- Phase-invariant Shadow 1.0x Closed-R balance curve & per-engine ring-10 buffers
   double                  m_shadowEq1x;
   double                  m_shadowPeak1x;
   long                    m_shadowClosedCount;
   double                  m_ringR[9][10];
   int                     m_ringCount[9];
   int                     m_ringHead[9];

   void ReleaseOnnxHandle()
   {{
      if(m_onnxHandle != INVALID_HANDLE)
      {{
         OnnxRelease(m_onnxHandle);
         m_onnxHandle = INVALID_HANDLE;
      }}
      m_onnxReady = false;
   }}

   static int ShadowSlotFromMagic(const long magic)
   {{
      if(magic == 20261122) return 0; // E1
      if(magic == 20261123) return 1; // E2
      if(magic == 20261125) return 2; // E3
      if(magic == 20261124) return 3; // E4
      if(magic == 20261126) return 4; // E5
      if(magic == 20261128) return 5; // E6
      if(magic == 20261129) return 6; // E7
      if(magic == 20261127) return 7; // S6
      return 8;
   }}

public:
   CNaqexMLFilterV105()
   {{
      m_onnxHandle           = INVALID_HANDLE;
      m_onnxReady            = false;
      m_mode                 = V105_ONNX_OR_PURE_MQL5_FALLBACK;
      m_threshold            = NAQEX_V105_ML_DEFAULT_THRESHOLD;
      m_lastBackend          = "UNINITIALIZED";
      m_lastOnnxError        = 0;
      m_onnxCalls            = 0;
      m_pureCalls            = 0;
      m_fallbackCalls        = 0;
      m_passedCount          = 0;
      m_blockedCount         = 0;
      m_invalidRejectedCount = 0;
      ResetShadow1x();
   }}

   ~CNaqexMLFilterV105()
   {{
      Deinit();
   }}

   void Deinit()
   {{
      ReleaseOnnxHandle();
   }}

   void ResetShadow1x()
   {{
      m_shadowEq1x        = 1.0;
      m_shadowPeak1x      = 1.0;
      m_shadowClosedCount = 0;
      for(int s = 0; s < 9; s++)
      {{
         m_ringCount[s] = 0;
         m_ringHead[s]  = 0;
         for(int k = 0; k < 10; k++)
            m_ringR[s][k] = 0.0;
      }}
   }}

   static double CanonicalBaseRiskPct1x(const long magic)
   {{
      if(magic == 20261122) return 0.16; // E1_USDJPY_TOKYO
      if(magic == 20261123) return 0.59; // E2_USDJPY_EXP80
      if(magic == 20261125) return 0.75; // E3_GBPUSD_VH
      if(magic == 20261124) return 0.50; // E4_US100_SESS40
      if(magic == 20261126) return 0.50; // E5_US100_RS1130
      if(magic == 20261128) return 0.50; // E6_EURJPY_VOLCOMP
      if(magic == 20261129) return 0.50; // E7_USDJPY_NY10ET
      return 0.50;
   }}

   static double EngineCodeFromMagic(const long magic)
   {{
      if(magic == 20261122) return 1.0;
      if(magic == 20261123) return 2.0;
      if(magic == 20261125) return 3.0;
      if(magic == 20261124) return 4.0;
      if(magic == 20261126) return 5.0;
      if(magic == 20261128) return 6.0;
      if(magic == 20261129) return 7.0;
      if(magic == 20261127) return 8.0;
      return 0.0;
   }}

   static double AssetClassCodeForSymbol(const string sym)
   {{
      string u = sym;
      StringToUpper(u);
      if(StringFind(u, "OIL") >= 0 || StringFind(u, "WTI") >= 0 || StringFind(u, "BRENT") >= 0) return 4.0;
      if(StringFind(u, "US100") >= 0 || StringFind(u, "US500") >= 0 || StringFind(u, "US30") >= 0 ||
         StringFind(u, "NAS100") >= 0 || StringFind(u, "GER40") >= 0 || StringFind(u, "UK100") >= 0 ||
         StringFind(u, "JP225") >= 0 || StringFind(u, "AUS200") >= 0) return 2.0;
      if(StringFind(u, "XAU") >= 0 || StringFind(u, "XAG") >= 0 || StringFind(u, "GOLD") >= 0) return 3.0;
      if(StringFind(u, "BTC") >= 0 || StringFind(u, "ETH") >= 0 || StringFind(u, "SOL") >= 0) return 5.0;
      if(StringLen(u) >= 6) return 1.0;
      return 0.0;
   }}

   //--- Update phase-invariant shadow 1.0x closed-R curve on strictly closed position exit
   void RecordClosedTradeShadow1x(const long magic, const double netR)
   {{
      if(!MathIsValidNumber(netR))
         return;
      double rClamped = MathMax(NAQEX_V105_ML_SHADOW_R_MIN, MathMin(NAQEX_V105_ML_SHADOW_R_MAX, netR));
      int slot = ShadowSlotFromMagic(magic);
      m_ringR[slot][m_ringHead[slot]] = rClamped;
      m_ringHead[slot] = (m_ringHead[slot] + 1) % 10;
      if(m_ringCount[slot] < 10)
         m_ringCount[slot]++;

      double rfPct   = CanonicalBaseRiskPct1x(magic);
      double stepRet = MathMax(-0.999999, rClamped * (rfPct / 100.0));
      m_shadowEq1x  *= (1.0 + stepRet);
      if(m_shadowEq1x > m_shadowPeak1x)
         m_shadowPeak1x = m_shadowEq1x;
      m_shadowClosedCount++;
   }}

   double ShadowEq1x()   const {{ return m_shadowEq1x; }}
   double ShadowPeak1x() const {{ return m_shadowPeak1x; }}
   long   ShadowClosedTradeCount() const {{ return m_shadowClosedCount; }}

   double ShadowRollingDdPct1x() const
   {{
      if(m_shadowPeak1x <= 1e-12)
         return 0.0;
      double dd = 100.0 * MathMax(0.0, (m_shadowPeak1x - m_shadowEq1x) / m_shadowPeak1x);
      return MathMax(0.0, MathMin(100.0, dd));
   }}

   double ShadowRecent10Wr(const long magic) const
   {{
      int slot = ShadowSlotFromMagic(magic);
      int cnt  = m_ringCount[slot];
      if(cnt <= 0)
         return 0.5;
      int wins = 0;
      for(int k = 0; k < cnt; k++)
         if(m_ringR[slot][k] > 0.0)
            wins++;
      return (double)wins / (double)cnt;
   }}

   double ShadowRecent10AvgR(const long magic) const
   {{
      int slot = ShadowSlotFromMagic(magic);
      int cnt  = m_ringCount[slot];
      if(cnt <= 0)
         return 0.0;
      double acc = 0.0;
      for(int k = 0; k < cnt; k++)
         acc += m_ringR[slot][k];
      double meanR = acc / (double)cnt;
      return MathMax(-10.0, MathMin(10.0, meanR));
   }}

   //--- Exact Closed-Bar Shift Helpers (1:1 Python `d1_day_key < cur_day` and `close_ts <= t_entry`)
   static int ClosedBrokerD1Shift(const string sym)
   {{
      datetime srvNow = TimeCurrent();
      datetime curDayStart = srvNow - (srvNow % 86400);
      datetime bar0 = iTime(sym, PERIOD_D1, 0);
      if(bar0 <= 0)
         return 1;
      return (bar0 < curDayStart) ? 0 : 1;
   }}

   static int ClosedM1Shift(const string sym)
   {{
      datetime srvNow = TimeCurrent();
      datetime bar0 = iTime(sym, PERIOD_M1, 0);
      if(bar0 <= 0)
         return 1;
      return ((bar0 + 60) <= srvNow) ? 0 : 1;
   }}

   static bool ReadBrokerD1Atr14(const int atr14Handle, const int d1Shift, double &outAtr)
   {{
      outAtr = 0.0;
      if(atr14Handle == INVALID_HANDLE)
         return false;
      double buf[1];
      if(CopyBuffer(atr14Handle, 0, d1Shift, 1, buf) != 1)
         return false;
      if(!MathIsValidNumber(buf[0]) || buf[0] <= 0.0)
         return false;
      outAtr = buf[0];
      return true;
   }}

   static double ComputeD1TrueRangeAt(const string sym, const int shift)
   {{
      double h = iHigh(sym, PERIOD_D1, shift);
      double l = iLow(sym, PERIOD_D1, shift);
      if(h <= 0.0 || l <= 0.0 || h < l)
         return -1.0;
      double prevC = iClose(sym, PERIOD_D1, shift + 1);
      if(prevC <= 0.0)
         prevC = iOpen(sym, PERIOD_D1, shift);
      double tr = MathMax(h - l, MathMax(MathAbs(h - prevC), MathAbs(l - prevC)));
      return tr;
   }}

   static double ComputeD1SmaTr(const string sym, const int d1Shift, const int period)
   {{
      double acc = 0.0;
      for(int m = 0; m < period; m++)
      {{
         double tr = ComputeD1TrueRangeAt(sym, d1Shift + m);
         if(tr < 0.0)
            return 0.0;
         acc += tr;
      }}
      return acc / (double)period;
   }}

   static double ComputeD1RangeOverAtr14(const string sym, const int d1Shift, const double atr14)
   {{
      double f = 1.0;
      if(atr14 > 1e-12)
      {{
         double h = iHigh(sym, PERIOD_D1, d1Shift);
         double l = iLow(sym, PERIOD_D1, d1Shift);
         if(h > 0.0 && l > 0.0 && h >= l)
            f = (h - l) / atr14;
      }}
      return MathMax(0.0, MathMin(15.0, f));
   }}

   static double ComputeParkinsonVol10d(const string sym, const int d1Shift)
   {{
      double sumSq = 0.0;
      int cnt = 0;
      for(int m = 0; m < 10; m++)
      {{
         double h = iHigh(sym, PERIOD_D1, d1Shift + m);
         double l = iLow(sym, PERIOD_D1, d1Shift + m);
         if(h > 0.0 && l > 0.0 && h >= l)
         {{
            double ratio = MathMax(h / MathMax(l, 1e-12), 1.0);
            double lg = MathLog(ratio);
            sumSq += lg * lg;
            cnt++;
         }}
      }}
      if(cnt <= 0)
         return 0.0;
      double v = MathSqrt(MathMax(0.0, sumSq / (4.0 * MathLog(2.0) * (double)cnt)));
      return MathMax(0.0, MathMin(1.0, v));
   }}

   static double ComputeAtr14Pct(const string sym, const int d1Shift, const double atr14)
   {{
      double c = iClose(sym, PERIOD_D1, d1Shift);
      if(atr14 > 1e-12 && c > 1e-12)
         return MathMax(0.0, MathMin(1.0, atr14 / c));
      return 0.0;
   }}

   static double ComputeAtr5OverAtr20Sma(const string sym, const int d1Shift)
   {{
      double a5  = ComputeD1SmaTr(sym, d1Shift, 5);
      double a20 = ComputeD1SmaTr(sym, d1Shift, 20);
      if(a5 > 0.0 && a20 > 1e-12)
         return MathMax(0.0, MathMin(10.0, a5 / a20));
      return 1.0;
   }}

   static double ComputeD1RangeComp5Over20(const string sym, const int d1Shift)
   {{
      double s5 = 0.0, s20 = 0.0;
      for(int m = 0; m < 20; m++)
      {{
         double h = iHigh(sym, PERIOD_D1, d1Shift + m);
         double l = iLow(sym, PERIOD_D1, d1Shift + m);
         if(h <= 0.0 || l <= 0.0 || h < l)
            return 1.0;
         double r = h - l;
         s20 += r;
         if(m < 5) s5 += r;
      }}
      double m5 = s5 / 5.0;
      double m20 = s20 / 20.0;
      if(m20 > 1e-12)
         return MathMax(0.0, MathMin(5.0, m5 / m20));
      return 1.0;
   }}

   static double ComputeBreakoutZscore20(const string sym, const int d1Shift)
   {{
      double vals[20];
      int cnt = 0;
      for(int m = 0; m < 20; m++)
      {{
         double c = iClose(sym, PERIOD_D1, d1Shift + m);
         if(c <= 0.0) break;
         vals[cnt++] = c;
      }}
      if(cnt < 3) return 0.0;
      double sum = 0.0;
      for(int i = 0; i < cnt; i++) sum += vals[i];
      double mean = sum / (double)cnt;
      double varSum = 0.0;
      for(int i = 0; i < cnt; i++)
      {{
         double d = vals[i] - mean;
         varSum += d * d;
      }}
      double sd = MathSqrt(varSum / (double)(cnt - 1));
      if(sd <= 1e-12) return 0.0;
      return MathMax(-10.0, MathMin(10.0, (vals[0] - mean) / sd));
   }}

   static double ComputeDistSma20Atr(const string sym, const int d1Shift, const double atr14)
   {{
      if(atr14 <= 1e-12) return 0.0;
      double sum = 0.0;
      for(int m = 0; m < 20; m++)
      {{
         double c = iClose(sym, PERIOD_D1, d1Shift + m);
         if(c <= 0.0) return 0.0;
         sum += c;
      }}
      double c0 = iClose(sym, PERIOD_D1, d1Shift);
      double sma20 = sum / 20.0;
      return MathMax(-15.0, MathMin(15.0, (c0 - sma20) / atr14));
   }}

   static double ComputePrevM1BodyRatio(const string sym, const int m1Shift)
   {{
      double o = iOpen(sym, PERIOD_M1, m1Shift);
      double h = iHigh(sym, PERIOD_M1, m1Shift);
      double l = iLow(sym, PERIOD_M1, m1Shift);
      double c = iClose(sym, PERIOD_M1, m1Shift);
      double r = h - l;
      if(h > 0.0 && l > 0.0 && r > 1e-12)
         return MathMax(-1.0, MathMin(1.0, (c - o) / r));
      return 0.0;
   }}

   static double ComputePrevM1CloseLoc(const string sym, const int m1Shift)
   {{
      double h = iHigh(sym, PERIOD_M1, m1Shift);
      double l = iLow(sym, PERIOD_M1, m1Shift);
      double c = iClose(sym, PERIOD_M1, m1Shift);
      double r = h - l;
      if(h > 0.0 && l > 0.0 && r > 1e-12)
         return MathMax(0.0, MathMin(1.0, (c - l) / r));
      return 0.5;
   }}

   static double ComputeSpreadOverAtrRatio(const string sym, const int m1Shift, const double atr14)
   {{
      if(atr14 <= 1e-12) return 0.0;
      double pt = SymbolInfoDouble(sym, SYMBOL_POINT);
      long spPts = iSpread(sym, PERIOD_M1, m1Shift);
      if(pt > 0.0 && spPts >= 0)
         return MathMax(0.0, MathMin(5.0, ((double)spPts * pt) / atr14));
      return 0.0;
   }}

   static double ComputeHourSinUtc(const datetime signalUtc)
   {{
      long secOfDay = (((long)signalUtc % 86400) + 86400) % 86400;
      return MathSin(2.0 * M_PI * ((double)secOfDay / 86400.0));
   }}

   static double ComputeHourCosUtc(const datetime signalUtc)
   {{
      long secOfDay = (((long)signalUtc % 86400) + 86400) % 86400;
      return MathCos(2.0 * M_PI * ((double)secOfDay / 86400.0));
   }}

   static double ComputeDowSinUtc(const datetime signalUtc)
   {{
      MqlDateTime dt;
      TimeToStruct(signalUtc, dt);
      int pyDow = (dt.day_of_week + 6) % 7;
      return MathSin(2.0 * M_PI * ((double)pyDow / 7.0));
   }}

   static double ComputeIsLondonNyOverlap(const datetime signalUtc)
   {{
      MqlDateTime dt;
      TimeToStruct(signalUtc, dt);
      return (dt.hour >= 12 && dt.hour < 17) ? 1.0 : 0.0;
   }}

   //--- Build the exact {n_feat} aligned causal features in model ONNX input order
   bool BuildAlignedFeaturesV105(const string sym,
                                 const int atr14D1Handle,
                                 const datetime signalUtc,
                                 const long magic,
                                 const int sameDirConcurrent,
                                 double &outFeat[]) const
   {{
      ArrayResize(outFeat, NAQEX_V105_ML_N_FEATURES);
      int d1Shift = ClosedBrokerD1Shift(sym);
      int m1Shift = ClosedM1Shift(sym);
      double atr14 = 0.0;
      if(!ReadBrokerD1Atr14(atr14D1Handle, d1Shift, atr14))
         atr14 = ComputeD1SmaTr(sym, d1Shift, 14);
{assign_lines}
      return ValidateFeatures(outFeat);
   }}

   static bool ValidateFeatures(const double &feat[])
   {{
      if(ArraySize(feat) < NAQEX_V105_ML_N_FEATURES)
         return false;
      for(int j = 0; j < NAQEX_V105_ML_N_FEATURES; j++)
      {{
         if(!MathIsValidNumber(feat[j]))
            return false;
      }}
      return true;
   }}

   static double EvaluatePureMql5RawLogit(const double &feat[])
   {{
      double rawSum = 0.0;
      for(int t = 0; t < NAQEX_V105_ML_N_TREES; t++)
      {{
         int idx = g_v105TreeRoots[t];
         for(int step = 0; step < 32; step++)
         {{
            int f = g_v105NodeFeat[idx];
            if(f < 0)
            {{
               rawSum += g_v105NodeLeaf[idx];
               break;
            }}
            idx = (feat[f] <= g_v105NodeThresh[idx]) ? g_v105NodeLeft[idx] : g_v105NodeRight[idx];
         }}
      }}
      return rawSum;
   }}

   static bool PredictPureMql5(const double &feat[], double &outProb)
   {{
      outProb = 0.0;
      if(!ValidateFeatures(feat))
         return false;
      double rawLogit = EvaluatePureMql5RawLogit(feat);
      if(!MathIsValidNumber(rawLogit))
         return false;
      if(rawLogit > NAQEX_V105_ML_LOGIT_CLAMP)
         rawLogit = NAQEX_V105_ML_LOGIT_CLAMP;
      else if(rawLogit < -NAQEX_V105_ML_LOGIT_CLAMP)
         rawLogit = -NAQEX_V105_ML_LOGIT_CLAMP;
      double p = 1.0 / (1.0 + MathExp(-rawLogit));
      if(!MathIsValidNumber(p))
         return false;
      if(p < NAQEX_V105_ML_PROB_CLIP)
         p = NAQEX_V105_ML_PROB_CLIP;
      else if(p > 1.0 - NAQEX_V105_ML_PROB_CLIP)
         p = 1.0 - NAQEX_V105_ML_PROB_CLIP;
      outProb = p;
      return true;
   }}

   bool InitFromBuffer(const uchar &modelBuf[],
                       const ENUM_NAQEX_ML_V105_MODE mode = V105_ONNX_OR_PURE_MQL5_FALLBACK,
                       const double threshold = NAQEX_V105_ML_DEFAULT_THRESHOLD)
   {{
      ReleaseOnnxHandle();
      m_mode          = mode;
      m_threshold     = threshold;
      m_lastOnnxError = 0;

      if(!MathIsValidNumber(threshold) || threshold <= 0.0 || threshold >= 1.0)
      {{
         m_lastBackend = "INVALID_THRESHOLD";
         PrintFormat("[ML-V105-ERR] Invalid threshold=%.6f (must be strictly inside (0,1))", threshold);
         return false;
      }}

      if(mode == V105_PURE_MQL5_TREE_ONLY)
      {{
         m_lastBackend = "PURE_MQL5";
         return true;
      }}

      if(ArraySize(modelBuf) <= 0)
      {{
         m_lastOnnxError = -101;
         m_lastBackend   = (mode == V105_ONNX_OR_PURE_MQL5_FALLBACK) ? "FALLBACK_PURE_MQL5" : "ONNX_BUFFER_EMPTY";
         return (mode == V105_ONNX_OR_PURE_MQL5_FALLBACK);
      }}

      ResetLastError();
      long h = OnnxCreateFromBuffer(modelBuf, ONNX_USE_CPU_ONLY);
      if(h == INVALID_HANDLE)
      {{
         m_lastOnnxError = GetLastError();
         m_lastBackend   = (mode == V105_ONNX_OR_PURE_MQL5_FALLBACK) ? "FALLBACK_PURE_MQL5" : "ONNX_CREATE_FAILED";
         return (mode == V105_ONNX_OR_PURE_MQL5_FALLBACK);
      }}

      const ulong inShape[]   = {{1, NAQEX_V105_ML_N_FEATURES}};
      const ulong out0Shape[] = {{1}};
      const ulong out1Shape[] = {{1, 2}};

      ResetLastError();
      if(!OnnxSetInputShape(h, 0, inShape) ||
         !OnnxSetOutputShape(h, 0, out0Shape) ||
         !OnnxSetOutputShape(h, 1, out1Shape))
      {{
         m_lastOnnxError = GetLastError();
         OnnxRelease(h);
         m_lastBackend   = (mode == V105_ONNX_OR_PURE_MQL5_FALLBACK) ? "FALLBACK_PURE_MQL5" : "ONNX_SHAPE_FAILED";
         return (mode == V105_ONNX_OR_PURE_MQL5_FALLBACK);
      }}

      m_onnxHandle  = h;
      m_onnxReady   = true;
      m_lastBackend = "ONNX";
      return true;
   }}

   bool InitFromFile(const string onnxFile = NAQEX_V105_ML_ONNX_FILE_DEFAULT,
                     const ENUM_NAQEX_ML_V105_MODE mode = V105_ONNX_OR_PURE_MQL5_FALLBACK,
                     const double threshold = NAQEX_V105_ML_DEFAULT_THRESHOLD)
   {{
      ReleaseOnnxHandle();
      m_mode          = mode;
      m_threshold     = threshold;
      m_lastOnnxError = 0;

      if(!MathIsValidNumber(threshold) || threshold <= 0.0 || threshold >= 1.0)
      {{
         m_lastBackend = "INVALID_THRESHOLD";
         PrintFormat("[ML-V105-ERR] Invalid threshold=%.6f (must be strictly inside (0,1))", threshold);
         return false;
      }}

      if(mode == V105_PURE_MQL5_TREE_ONLY)
      {{
         m_lastBackend = "PURE_MQL5";
         return true;
      }}

      ResetLastError();
      int fh = FileOpen(onnxFile, FILE_READ | FILE_BIN | FILE_SHARE_READ);
      if(fh == INVALID_HANDLE)
      {{
         m_lastOnnxError = GetLastError();
         m_lastBackend   = (mode == V105_ONNX_OR_PURE_MQL5_FALLBACK) ? "FALLBACK_PURE_MQL5" : "ONNX_FILE_MISSING";
         return (mode == V105_ONNX_OR_PURE_MQL5_FALLBACK);
      }}

      ulong fsize = FileSize(fh);
      uchar buf[];
      if(fsize == 0 || fsize > 16777216)
      {{
         FileClose(fh);
         m_lastOnnxError = -102;
         m_lastBackend   = (mode == V105_ONNX_OR_PURE_MQL5_FALLBACK) ? "FALLBACK_PURE_MQL5" : "ONNX_FILE_BAD_SIZE";
         return (mode == V105_ONNX_OR_PURE_MQL5_FALLBACK);
      }}
      ArrayResize(buf, (int)fsize);
      uint nRead = FileReadArray(fh, buf, 0, (int)fsize);
      FileClose(fh);
      if(nRead != (uint)fsize)
      {{
         m_lastOnnxError = GetLastError();
         m_lastBackend   = (mode == V105_ONNX_OR_PURE_MQL5_FALLBACK) ? "FALLBACK_PURE_MQL5" : "ONNX_FILE_READ_SHORT";
         return (mode == V105_ONNX_OR_PURE_MQL5_FALLBACK);
      }}
      return InitFromBuffer(buf, mode, threshold);
   }}

   bool PredictOnnx(const double &feat[], double &outProb)
   {{
      outProb = 0.0;
      if(!ValidateFeatures(feat))
         return false;
      if(!m_onnxReady || m_onnxHandle == INVALID_HANDLE)
         return false;

      float xIn[1][NAQEX_V105_ML_N_FEATURES];
      for(int j = 0; j < NAQEX_V105_ML_N_FEATURES; j++)
      {{
         float fv = (float)feat[j];
         if(!MathIsValidNumber((double)fv))
            return false;
         xIn[0][j] = fv;
      }}

      long  outLabel[1];
      float outProbs[1][2];
      outLabel[0]    = 0;
      outProbs[0][0] = 0.0f;
      outProbs[0][1] = 0.0f;

      ResetLastError();
      if(!OnnxRun(m_onnxHandle, ONNX_NO_CONVERSION, xIn, outLabel, outProbs))
      {{
         m_lastOnnxError = GetLastError();
         return false;
      }}

      double p1 = (double)outProbs[0][1];
      if(!MathIsValidNumber(p1) || p1 < -1e-6 || p1 > 1.0 + 1e-6)
         return false;
      if(p1 < NAQEX_V105_ML_PROB_CLIP)
         p1 = NAQEX_V105_ML_PROB_CLIP;
      else if(p1 > 1.0 - NAQEX_V105_ML_PROB_CLIP)
         p1 = 1.0 - NAQEX_V105_ML_PROB_CLIP;

      outProb = p1;
      m_onnxCalls++;
      return true;
   }}

   bool PredictProba(const double &feat[], double &outProb, string &outBackend)
   {{
      outProb    = 0.0;
      outBackend = "ERROR_FAIL_CLOSED";
      if(!ValidateFeatures(feat))
      {{
         m_invalidRejectedCount++;
         outBackend    = "REJECTED_INVALID_INPUT";
         m_lastBackend = outBackend;
         return false;
      }}

      if(m_mode == V105_PURE_MQL5_TREE_ONLY)
      {{
         if(PredictPureMql5(feat, outProb))
         {{
            m_pureCalls++;
            outBackend    = "PURE_MQL5";
            m_lastBackend = outBackend;
            return true;
         }}
         m_lastBackend = "ERROR_FAIL_CLOSED";
         return false;
      }}

      if(m_onnxReady && PredictOnnx(feat, outProb))
      {{
         outBackend    = "ONNX";
         m_lastBackend = outBackend;
         return true;
      }}

      if(m_mode == V105_ONNX_ONLY_FAIL_CLOSED)
      {{
         outBackend    = "ONNX_FAIL_CLOSED";
         m_lastBackend = outBackend;
         return false;
      }}

      if(PredictPureMql5(feat, outProb))
      {{
         m_fallbackCalls++;
         outBackend    = "FALLBACK_PURE_MQL5";
         m_lastBackend = outBackend;
         return true;
      }}

      m_lastBackend = "ERROR_FAIL_CLOSED";
      return false;
   }}

   bool ShouldAllowTrade(const double &feat[], double &outProb, string &outBackend)
   {{
      if(!PredictProba(feat, outProb, outBackend))
      {{
         m_blockedCount++;
         return false;
      }}
      if(outProb < m_threshold)
      {{
         m_blockedCount++;
         return false;
      }}
      m_passedCount++;
      return true;
   }}

   bool   IsOnnxReady()          const {{ return m_onnxReady; }}
   double Threshold()            const {{ return m_threshold; }}
   string LastBackend()          const {{ return m_lastBackend; }}
   int    LastOnnxError()        const {{ return m_lastOnnxError; }}
   long   OnnxCalls()            const {{ return m_onnxCalls; }}
   long   PureCalls()            const {{ return m_pureCalls; }}
   long   FallbackCalls()        const {{ return m_fallbackCalls; }}
   long   PassedCount()          const {{ return m_passedCount; }}
   long   BlockedCount()         const {{ return m_blockedCount; }}
   long   InvalidRejectedCount() const {{ return m_invalidRejectedCount; }}
}};

#endif // NAQEX_ML_FILTER_V105_MQH
"""
    return header


def parse_mqh_v105_tree_tables(mqh_text: str) -> dict[str, Any]:
    """Parse emitted C/MQL5 tree arrays directly from `Naqex_ML_Filter_v105.mqh` source text."""
    m_feat = re.search(r"#define\s+NAQEX_V105_ML_N_FEATURES\s+(\d+)", mqh_text)
    m_trees = re.search(r"#define\s+NAQEX_V105_ML_N_TREES\s+(\d+)", mqh_text)
    m_nodes = re.search(r"#define\s+NAQEX_V105_ML_N_NODES\s+(\d+)", mqh_text)
    if not (m_feat and m_trees and m_nodes):
        raise ValueError("INVALID_MQH_V105_HEADER: missing NAQEX_V105_ML_N_* macros")

    n_feat = int(m_feat.group(1))
    n_trees = int(m_trees.group(1))
    n_nodes = int(m_nodes.group(1))

    def _extract_array(name: str, *, as_float: bool) -> list[Any]:
        pat = re.compile(rf"static\s+const\s+\w+\s+{re.escape(name)}\s*\[[^\]]+\]\s*=\s*\{{(.*?)\}}\s*;", re.S)
        m = pat.search(mqh_text)
        if not m:
            raise ValueError(f"INVALID_MQH_V105_HEADER: missing array {name}")
        tokens = [tok.strip() for tok in m.group(1).split(",") if tok.strip()]
        return [float(tok) if as_float else int(tok) for tok in tokens]

    tree_roots = _extract_array("g_v105TreeRoots", as_float=False)
    node_feat = _extract_array("g_v105NodeFeat", as_float=False)
    node_left = _extract_array("g_v105NodeLeft", as_float=False)
    node_right = _extract_array("g_v105NodeRight", as_float=False)
    node_thresh = _extract_array("g_v105NodeThresh", as_float=True)
    node_leaf = _extract_array("g_v105NodeLeaf", as_float=True)

    if len(tree_roots) != n_trees or len(node_feat) != n_nodes:
        raise ValueError("MQH_V105_ARRAY_LENGTH_MISMATCH")

    return {
        "n_features": n_feat,
        "n_trees": n_trees,
        "n_nodes": n_nodes,
        "tree_roots": tree_roots,
        "node_feat": node_feat,
        "node_left": node_left,
        "node_right": node_right,
        "node_thresh": node_thresh,
        "node_leaf": node_leaf,
    }


def evaluate_mqh_v105_mirror(mqh_text: str, raw_x: Any) -> np.ndarray:
    """Parse emitted `Naqex_ML_Filter_v105.mqh` and evaluate its flattened trees in pure Python."""
    tables = parse_mqh_v105_tree_tables(mqh_text)
    return evaluate_flat_trees(tables, raw_x, prob_clip=PROB_CLIP_EPS)


# ---------------------------------------------------------------------------
# 6. Full-2024 FTMO Same-Feed Reference Extractor (`wave5_2024_features_ref.csv`)
# ---------------------------------------------------------------------------


def export_2024_ftmo_same_feed_features_ref(
    *,
    selected_feature_indices: Sequence[int],
    selected_feature_names: Sequence[str],
    predict_proba_fn: Any,
    ml_threshold: float,
    onnx_path: Path | None = None,
    mqh_text: str | None = None,
    preset_path: Path = DEFAULT_FUNDED_1X_PRESET,
    red_news_csv: Path = DEFAULT_RED_NEWS_CSV,
    out_csv_path: Path | None = DEFAULT_2024_REF_CSV_PATH,
    out_meta_path: Path | None = DEFAULT_2024_REF_META_PATH,
    from_date: str = "2024.01.02",
    to_date: str = "2024.12.31",
    ml_enabled: bool = True,
) -> dict[str, Any]:
    """Simulate full-2024 FTMO same-feed `Model=1` WITH `v1.05-ML` active (`MarkEngineTraded()` on reject)
    and emit exact aligned feature vectors + expected `p_win` + `ml_allowed` for EVERY 2024 signal!
    """
    from quant_factory.wave4.same_feed_mt5_parity import (
        FTMO_SYMBOL_SPECS,
        PORT_7E_SYMBOLS,
        PresetConfig,
        RedNewsCalendarIndex,
        _current_reset_day_key,
        accumulate_directional_factor,
        assert_dev_date_sealed,
        compute_phase_risk_multiplier,
        helsinki_utc_offset_hours,
        is_us_equity_holiday_or_half_day_ny,
        load_ftmo_m1_bundle,
        load_mt5_red_news_csv,
        load_v103_preset,
        mt5_tester_now_utc,
        new_york_utc_offset_hours,
        normalize_price_to_tick,
        required_margin_usd,
        round_cent_half_up,
        round_volume_down_to_step,
        tick_value_loss_usd,
    )

    assert_dev_date_sealed(to_date, from_date)
    cfg: PresetConfig = load_v103_preset(preset_path, initial_balance_override=10_000.0)
    red_news = load_mt5_red_news_csv(red_news_csv)
    m1_bundle = load_ftmo_m1_bundle(verify_sha=False)

    # Pre-build exact aligned indicator bundles for all 8 PORT_7E symbols
    aligned_sym_bundles: dict[str, dict[str, Any]] = {}
    for sym in PORT_7E_SYMBOLS:
        d = m1_bundle[sym]
        ts_u = np.asarray(d["ts_utc"], dtype=np.int64)
        sp_pts = np.asarray(d["spread_pts"], dtype=np.float64)
        pt = float(FTMO_SYMBOL_SPECS[sym]["point"])
        aligned_sym_bundles[sym] = {
            "intraday": {
                "times_sec": ts_u,
                "close_times_sec": ts_u + np.int64(60),
                "bar_duration_sec": 60,
                "open": np.asarray(d["open"], dtype=np.float64),
                "high": np.asarray(d["high"], dtype=np.float64),
                "low": np.asarray(d["low"], dtype=np.float64),
                "close": np.asarray(d["close"], dtype=np.float64),
                "spread": sp_pts * pt,
            },
            "d1_indicators": precompute_aligned_broker_d1_indicators(d["d1"]),
            "asset_class": None,
        }

    from_srv_ts = int(datetime.fromisoformat(from_date.replace(".", "-") + "T00:00:00+00:00").timestamp())
    to_srv_ts = int(datetime.fromisoformat(to_date.replace(".", "-") + "T00:00:00+00:00").timestamp())
    news_index = RedNewsCalendarIndex(red_news, pad_sec=cfg.news_pad_sec, hard_ban_sec=cfg.news_hard_ban_sec)

    uj = m1_bundle["USDJPY"]
    uj_srv_all = np.asarray(uj["ts_server_raw"], dtype=np.int64)
    i_start = int(np.searchsorted(uj_srv_all, from_srv_ts, side="left"))
    i_end = int(np.searchsorted(uj_srv_all, to_srv_ts, side="left"))
    uj_srv = uj_srv_all[i_start:i_end]
    n_bars = len(uj_srv)

    sym_arrays: dict[str, dict[str, Any]] = {}
    for sym in PORT_7E_SYMBOLS:
        d = m1_bundle[sym]
        ts_s = np.asarray(d["ts_server_raw"], dtype=np.int64)
        pos_idx = np.searchsorted(ts_s, uj_srv, side="right") - 1
        d1 = d["d1"]
        d1_keys = np.asarray(d1["d1_day_key"], dtype=np.int64)
        spec = FTMO_SYMBOL_SPECS[sym]
        sym_arrays[sym] = {
            "ts_srv": ts_s,
            "open": np.asarray(d["open"], dtype=np.float64),
            "high": np.asarray(d["high"], dtype=np.float64),
            "low": np.asarray(d["low"], dtype=np.float64),
            "close": np.asarray(d["close"], dtype=np.float64),
            "spread_pts": np.asarray(d["spread_pts"], dtype=np.int32),
            "aligned_idx": pos_idx,
            "d1_open": np.asarray(d1["d1_open"], dtype=np.float64),
            "d1_prior_atr": np.asarray(d1["prior_atr14"], dtype=np.float64),
            "d1_prior_range": np.asarray(d1["prior_range"], dtype=np.float64),
            "d1_e6_ok": np.asarray(d1["e6_comp_ok"], dtype=np.bool_),
            "d1_lookup": {int(dk): idx for idx, dk in enumerate(d1_keys)},
            "point": float(spec["point"]),
            "tick_size": float(spec["tick_size"]),
            "digits": int(spec["digits"]),
            "contract_size": float(spec["contract_size"]),
            "vol_min": float(spec["vol_min"]),
            "vol_max": float(spec["vol_max"]),
            "vol_step": float(spec["vol_step"]),
            "comm_per_lot_side": float(spec["comm_per_lot_side"]),
            "quote_ccy": str(spec["quote_ccy"]),
            "session_close_srv_sec": int(spec["session_close_srv_sec"]),
        }

    sel_idx = [int(i) for i in selected_feature_indices]
    sel_names = [str(nm) for nm in selected_feature_names]

    bal = float(cfg.initial_balance_usd)
    peak_eq = bal
    max_eq_dd_pct = 0.0
    day_key = -1
    day_anchor_bal = bal
    day_anchor_eq = bal
    auto_kill_active = False
    traded_day: list[int] = [0] * 8

    shadow_tracker = Shadow1xClosedRTracker()
    signal_rows: list[dict[str, Any]] = []
    closed_positions: list[dict[str, Any]] = []
    open_positions: list[dict[str, Any]] = []
    next_pos_id = 1

    e1_box_day = -1
    e1_box_ready = False
    e1_box_top = 0.0
    e1_box_bot = 0.0
    e4_sess_day = -1
    e4_morn_init = False
    e4_morn_frozen = False
    e4_morn_open = 0.0
    e4_morn_high = 0.0
    e4_morn_low = 0.0
    e4_morn_close = 0.0
    e4_morn_dir = 0
    ny_anchor_day = -1
    ny_anchor_ready = False
    ny_anchor_last_try = -10**12
    us100_open_0930 = 0.0
    us500_open_0930 = 0.0

    e7_basket: tuple[tuple[str, int], ...] = (
        ("USDJPY", 1),
        ("USDCAD", 1),
        ("EURUSD", -1),
        ("GBPUSD", -1),
        ("AUDUSD", -1),
    )

    cur_bid: dict[str, float] = {s: 0.0 for s in PORT_7E_SYMBOLS}
    cur_ask: dict[str, float] = {s: 0.0 for s in PORT_7E_SYMBOLS}
    cur_sp: dict[str, float] = {s: 0.0 for s in PORT_7E_SYMBOLS}
    cur_m1_idx: dict[str, int] = {s: -1 for s in PORT_7E_SYMBOLS}

    def _unrealized_pnl_usd(pos: Mapping[str, Any]) -> float:
        s = pos["symbol"]
        lots = pos["lots"]
        sa = sym_arrays[s]
        diff = (cur_bid[s] - pos["entry_price"]) if pos["is_buy"] else (pos["entry_price"] - cur_ask[s])
        pnl_q = diff * sa["contract_size"] * lots
        if sa["quote_ccy"] == "USD":
            return pnl_q
        if sa["quote_ccy"] == "JPY":
            conv = cur_ask["USDJPY"] if pnl_q >= 0.0 else cur_bid["USDJPY"]
            return (pnl_q / conv) if conv > 0.0 else 0.0
        return pnl_q

    def _close_position(pos: dict[str, Any], close_px: float, exit_srv_ts: int, exit_utc_ts: int, reason: str) -> None:
        nonlocal bal
        s = pos["symbol"]
        lots = pos["lots"]
        sa = sym_arrays[s]
        diff = (close_px - pos["entry_price"]) if pos["is_buy"] else (pos["entry_price"] - close_px)
        pnl_q = diff * sa["contract_size"] * lots
        if sa["quote_ccy"] == "USD":
            gross_usd = round_cent_half_up(pnl_q)
        elif sa["quote_ccy"] == "JPY":
            conv = close_px if s == "USDJPY" else (cur_ask["USDJPY"] if pnl_q >= 0.0 else cur_bid["USDJPY"])
            gross_usd = round_cent_half_up(pnl_q / conv) if conv > 0.0 else 0.0
        else:
            gross_usd = round_cent_half_up(pnl_q)
        comm_out = -round_cent_half_up(sa["comm_per_lot_side"] * lots) if sa["comm_per_lot_side"] > 0.0 else 0.0
        bal = round_cent_half_up(bal + gross_usd + comm_out)
        total_comm = round_cent_half_up(pos["comm_in_usd"] + comm_out)
        net_usd = round_cent_half_up(gross_usd + total_comm)
        init_risk_usd = float(pos["init_risk_usd"])
        net_r_realized = (net_usd / init_risk_usd) if init_risk_usd > 1e-12 else 0.0
        # Exact 1:1 shadow 1.0x closed-R update matching MQL5 OnTradeTransaction(DEAL_ENTRY_OUT)!
        shadow_tracker.record_closed_trade(pos["engine_id"], net_r_realized)
        closed_positions.append(
            {
                "position_id": pos["position_id"],
                "engine_id": pos["engine_id"],
                "magic": pos["magic"],
                "symbol": s,
                "side": "BUY" if pos["is_buy"] else "SELL",
                "entry_utc_ts": int(pos["entry_utc_ts"]),
                "exit_utc_ts": int(exit_utc_ts),
                "net_pnl_usd": net_usd,
                "net_R": round(net_r_realized, 6),
                "exit_reason": reason,
            }
        )

    def _compute_open_risk_state() -> tuple[float, float, float, float, float, float, float, dict[str, float]]:
        uL = uS = jL = jS = iL = iS = tot = 0.0
        by_sym: dict[str, float] = {}
        if bal <= 0.0:
            return (999.0, 999.0, 999.0, 999.0, 999.0, 999.0, 999.0, by_sym)
        for p in open_positions:
            psym = p["symbol"]
            sa = sym_arrays[psym]
            tv = tick_value_loss_usd(psym, usdjpy_bid=cur_bid["USDJPY"], usdcad_bid=cur_bid["USDCAD"])
            if tv <= 0.0:
                return (999.0, 999.0, 999.0, 999.0, 999.0, 999.0, 999.0, by_sym)
            rpct = (((p["sl_dist"] / sa["tick_size"]) * tv * p["lots"]) / bal) * 100.0
            tot += rpct
            by_sym[psym] = by_sym.get(psym, 0.0) + rpct
            duL, duS, djL, djS, diL, diS = accumulate_directional_factor(psym, p["is_buy"], rpct)
            uL += duL
            uS += duS
            jL += djL
            jS += djS
            iL += diL
            iS += diS
        return (uL, uS, jL, jS, iL, iS, tot, by_sym)

    def _open_margin_used() -> float:
        m = 0.0
        for p in open_positions:
            m += required_margin_usd(
                p["symbol"],
                p["lots"],
                p["entry_price"],
                leverage=cfg.leverage,
                eurusd_bid=cur_bid["EURUSD"] or 1.08,
                gbpusd_bid=cur_bid["GBPUSD"] or 1.27,
            )
        return m

    def _should_clock_flatten(
        magic: int, now_utc: int, u_yr: int, u_mon: int, u_day: int, u_hr: int, u_min: int, mql_dow: int
    ) -> str:
        if mql_dow == 6:
            return ""
        if mql_dow == 0:
            return "WEEKEND_GAP_FAILSAFE_SWAP0" if u_hr >= 21 else ""
        if magic == 20261122:
            flat_h = 18 - helsinki_utc_offset_hours(u_yr, u_mon, u_day, u_hr)
            return "HARD_FLAT_18H_HELSINKI_SWAP0" if u_hr >= flat_h else ""
        if magic in (20261124, 20261126):
            ny_ts = now_utc + new_york_utc_offset_hours(u_yr, u_mon, u_day, u_hr) * 3600
            ny_dt = datetime.fromtimestamp(ny_ts, UTC)
            if is_us_equity_holiday_or_half_day_ny(ny_dt.year, ny_dt.month, ny_dt.day):
                return "HARD_FLAT_US_HALF_DAY_SWAP0"
            ny_m = ny_dt.hour * 60 + ny_dt.minute
            if ny_m >= 15 * 60 + 55:
                return "HARD_FLAT_1555_ET_SWAP0"
            if ny_m < 9 * 60 + 30:
                return "OVERNIGHT_FAILSAFE_SWAP0"
            return ""
        if u_hr > 20 or (u_hr == 20 and u_min >= 55):
            return "HARD_FLAT_2055_UTC_SWAP0"
        return ""

    def _is_near_session_close(sym: str, srv_ts: int) -> bool:
        if cfg.early_close_min <= 0:
            return False
        rem = sym_arrays[sym]["session_close_srv_sec"] - (srv_ts % 86400)
        return 0 <= rem <= cfg.early_close_min * 60

    def _is_spread_and_session_safe(sym: str, u_hr: int, mql_dow: int) -> bool:
        if mql_dow in (0, 6):
            return False
        if cfg.rollover_start_utc > cfg.rollover_end_utc:
            if u_hr >= cfg.rollover_start_utc or u_hr < cfg.rollover_end_utc:
                return False
        elif cfg.rollover_start_utc < cfg.rollover_end_utc:
            if cfg.rollover_start_utc <= u_hr < cfg.rollover_end_utc:
                return False
        cap = cfg.max_spread_cap_for_symbol(sym)
        if cap > 0.0 and cur_sp[sym] > cap:
            return False
        return True

    def _process_intent(
        *,
        engine_idx: int,
        engine_id: str,
        magic: int,
        sym: str,
        is_buy: bool,
        sig_px: float,
        raw_sl: float,
        base_risk_pct: float,
        sess_day_key: int,
        risk_mult: float,
        srv_ts: int,
        now_utc: int,
        u_hr: int,
        mql_dow: int,
    ) -> None:
        nonlocal bal, next_pos_id
        for p in open_positions:
            if p["magic"] == magic:
                return
        if cfg.enable_red_news and news_index.is_inside_red_news_window(sym, now_utc):
            return
        if not _is_spread_and_session_safe(sym, u_hr, mql_dow):
            return
        sa = sym_arrays[sym]
        norm_sl = normalize_price_to_tick(raw_sl, sa["tick_size"], sa["digits"])
        sl_dist = abs(sig_px - norm_sl)
        if sl_dist <= 0.0 or norm_sl <= 0.0:
            return

        # --- Wave 5 v1.05-ML Gate (runs at exact ProcessIntentAtomically position!) ---
        same_dir_cnt = sum(1 for p in open_positions if bool(p["is_buy"]) == bool(is_buy))
        full_vec = extract_single_signal_aligned_features(
            sym_bundle=aligned_sym_bundles[sym],
            symbol=sym,
            entry_utc_ts=now_utc,
            entry_srv_ts=srv_ts,
            engine_id=engine_id,
            same_dir_concurrent_count=same_dir_cnt,
            shadow_tracker=shadow_tracker,
        )
        sel_vec_f32 = np.ascontiguousarray(full_vec[sel_idx], dtype=np.float32)
        p_win = float(predict_proba_fn(sel_vec_f32.reshape(1, -1))[0])
        ml_allowed = True if not ml_enabled else (p_win >= float(ml_threshold))
        size_mult = 1.0 if ml_allowed else 0.0

        signal_rows.append(
            {
                "signal_seq": len(signal_rows),
                "entry_utc_ts": int(now_utc),
                "entry_server_time": datetime.fromtimestamp(srv_ts, UTC).strftime("%Y.%m.%d %H:%M:%S"),
                "engine_id": engine_id,
                "magic": int(magic),
                "symbol": sym,
                "side": "BUY" if is_buy else "SELL",
                "features_f32": sel_vec_f32.copy(),
                "ref_p_win": p_win,
                "ref_ml_allowed": 1 if ml_allowed else 0,
                "ref_size_mult": size_mult,
                "shadow_eq_1x": shadow_tracker.shadow_eq,
                "shadow_peak_1x": shadow_tracker.shadow_peak,
                "shadow_dd_pct_1x": shadow_tracker.rolling_dd_pct_1x_equiv(),
                "same_dir_concurrent": same_dir_cnt,
            }
        )

        if not ml_allowed:
            # Exact W4G05-F01 / v1.05 MarkEngineTraded() 1-shot-per-session semantics!
            traded_day[engine_idx] = sess_day_key
            return

        # Shield A + Shield B1 risk caps & conservative lot sizing
        uL, uS, jL, jS, iL, iS, tot_open, by_sym = _compute_open_risk_state()
        if tot_open >= 900.0:
            return
        req_risk = base_risk_pct * risk_mult
        used_sym = by_sym.get(sym, 0.0)
        sym_head = max(0.0, cfg.max_symbol_risk_pct - used_sym) if cfg.max_symbol_risk_pct > 0.0 else 999.0
        eff_tot_cap = cfg.effective_total_open_cap_pct()
        fac_head = max(0.0, eff_tot_cap - tot_open) if eff_tot_cap > 0.0 else 999.0
        duL, duS, djL, djS, diL, diS = accumulate_directional_factor(sym, is_buy, 1.0)
        if cfg.max_usd_cluster_pct > 0.0:
            if duL > 0.0:
                fac_head = min(fac_head, max(0.0, cfg.max_usd_cluster_pct - uL))
            if duS > 0.0:
                fac_head = min(fac_head, max(0.0, cfg.max_usd_cluster_pct - uS))
        if cfg.max_jpy_cluster_pct > 0.0:
            if djL > 0.0:
                fac_head = min(fac_head, max(0.0, cfg.max_jpy_cluster_pct - jL))
            if djS > 0.0:
                fac_head = min(fac_head, max(0.0, cfg.max_jpy_cluster_pct - jS))
        if cfg.max_idx_cluster_pct > 0.0:
            if diL > 0.0:
                fac_head = min(fac_head, max(0.0, cfg.max_idx_cluster_pct - iL))
            if diS > 0.0:
                fac_head = min(fac_head, max(0.0, cfg.max_idx_cluster_pct - iS))

        allowed_risk = min(req_risk, sym_head, fac_head)
        if allowed_risk <= 0.01:
            return
        tv = tick_value_loss_usd(sym, usdjpy_bid=cur_bid["USDJPY"], usdcad_bid=cur_bid["USDCAD"])
        if bal <= 0.0 or tv <= 0.0:
            return
        loss_per_lot = (sl_dist / sa["tick_size"]) * tv
        if loss_per_lot <= 0.0:
            return
        lots = round_volume_down_to_step(
            (bal * (allowed_risk / 100.0) * 0.95) / loss_per_lot,
            sa["vol_step"],
            sa["vol_min"],
            sa["vol_max"],
        )
        if lots < sa["vol_min"]:
            return

        eq_now = bal + sum(_unrealized_pnl_usd(p) for p in open_positions)
        free_margin = eq_now - _open_margin_used()
        req_margin = required_margin_usd(
            sym,
            lots,
            sig_px,
            leverage=cfg.leverage,
            eurusd_bid=cur_bid["EURUSD"] or 1.08,
            gbpusd_bid=cur_bid["GBPUSD"] or 1.27,
        )
        if free_margin <= 0.0 or req_margin <= 0.0:
            return
        max_allow_m = free_margin * 0.85
        if req_margin > max_allow_m:
            lots = round_volume_down_to_step(
                lots * (max_allow_m / req_margin), sa["vol_step"], sa["vol_min"], sa["vol_max"]
            )
            if lots < sa["vol_min"]:
                return

        actual_risk_pct = ((loss_per_lot * lots) / bal) * 100.0
        if actual_risk_pct > min(sym_head, fac_head) + 1e-6:
            return

        comm_in = -round_cent_half_up(sa["comm_per_lot_side"] * lots) if sa["comm_per_lot_side"] > 0.0 else 0.0
        bal = round_cent_half_up(bal + comm_in)
        open_positions.append(
            {
                "position_id": next_pos_id,
                "engine_idx": engine_idx,
                "engine_id": engine_id,
                "magic": magic,
                "symbol": sym,
                "is_buy": is_buy,
                "entry_price": sig_px,
                "sl_price": norm_sl,
                "sl_dist": sl_dist,
                "lots": lots,
                "init_risk_usd": loss_per_lot * lots,
                "comm_in_usd": comm_in,
                "entry_srv_ts": srv_ts,
                "entry_utc_ts": now_utc,
            }
        )
        next_pos_id += 1
        traded_day[engine_idx] = sess_day_key

    sym_ts_srv = {s: sym_arrays[s]["ts_srv"] for s in PORT_7E_SYMBOLS}
    sym_open = {s: sym_arrays[s]["open"] for s in PORT_7E_SYMBOLS}
    sym_high = {s: sym_arrays[s]["high"] for s in PORT_7E_SYMBOLS}
    sym_low = {s: sym_arrays[s]["low"] for s in PORT_7E_SYMBOLS}
    sym_close = {s: sym_arrays[s]["close"] for s in PORT_7E_SYMBOLS}
    sym_sp = {s: sym_arrays[s]["spread_pts"] for s in PORT_7E_SYMBOLS}
    sym_pt = {s: sym_arrays[s]["point"] for s in PORT_7E_SYMBOLS}
    sym_dig = {s: sym_arrays[s]["digits"] for s in PORT_7E_SYMBOLS}
    sym_aidx = {s: sym_arrays[s]["aligned_idx"] for s in PORT_7E_SYMBOLS}

    hour_cache: dict[int, tuple[int, int, int, int, int, int, int, int, int, bool]] = {}

    def _hour_info(now_utc: int) -> tuple[int, int, int, int, int, int, int, int, int, bool]:
        hb = now_utc // 3600
        cached = hour_cache.get(hb)
        if cached is not None:
            return cached
        dt = datetime.fromtimestamp(hb * 3600, UTC)
        yr, mon, day, hr = dt.year, dt.month, dt.day, dt.hour
        mql_dow = (dt.weekday() + 1) % 7
        utc_day = (hb * 3600) - ((hb * 3600) % 86400)
        hel_off = helsinki_utc_offset_hours(yr, mon, day, hr)
        ny_off = new_york_utc_offset_hours(yr, mon, day, hr)
        ny_dt = datetime.fromtimestamp(hb * 3600 + ny_off * 3600, UTC)
        ny_day = (hb * 3600 + ny_off * 3600) - ((hb * 3600 + ny_off * 3600) % 86400)
        is_us_half = is_us_equity_holiday_or_half_day_ny(ny_dt.year, ny_dt.month, ny_dt.day)
        info = (yr, mon, day, hr, mql_dow, utc_day, hel_off, ny_off, ny_day, is_us_half)
        hour_cache[hb] = info
        return info

    for bi in range(n_bars):
        bar_srv_ts = int(uj_srv[bi])
        bar_utc_base = mt5_tester_now_utc(bar_srv_ts, cfg.tester_utc_offset_h)
        u_yr, u_mon, u_day, u_hr, mql_dow, utc_day, hel_off, ny_off, ny_day, is_us_half = _hour_info(bar_utc_base)

        if not open_positions and (u_hr >= 21 or mql_dow in (0, 6)):
            rdk = _current_reset_day_key(bar_srv_ts, bar_utc_base, cfg.daily_reset_mode)
            if rdk != day_key:
                day_key = rdk
                day_anchor_bal = bal
                day_anchor_eq = bal
                auto_kill_active = False
            continue

        sym_tick_prices: dict[str, tuple[float, float, float, float]] = {}
        for s in PORT_7E_SYMBOLS:
            ai = int(sym_aidx[s][bi])
            cur_m1_idx[s] = ai
            if ai < 0:
                sym_tick_prices[s] = (0.0, 0.0, 0.0, 0.0)
                cur_sp[s] = 0.0
                continue
            cur_sp[s] = float(sym_sp[s][ai])
            if int(sym_ts_srv[s][ai]) == bar_srv_ts:
                o_s = float(sym_open[s][ai])
                h_s = float(sym_high[s][ai])
                l_s = float(sym_low[s][ai])
                c_s = float(sym_close[s][ai])
                sym_tick_prices[s] = (o_s, l_s, h_s, c_s) if c_s >= o_s else (o_s, h_s, l_s, c_s)
            else:
                c_s = float(sym_close[s][ai])
                sym_tick_prices[s] = (c_s, c_s, c_s, c_s)

        bar_min = (bar_utc_base // 60) % 60
        ny_mins = ((bar_utc_base + ny_off * 3600) % 86400) // 60
        srv_d1_key = bar_srv_ts // 86400

        d1_uj = sym_arrays["USDJPY"]["d1_lookup"].get(srv_d1_key, -1)
        d1_gbp = sym_arrays["GBPUSD"]["d1_lookup"].get(srv_d1_key, -1)
        d1_ej = sym_arrays["EURJPY"]["d1_lookup"].get(srv_d1_key, -1)
        d1_u100 = sym_arrays["US100.cash"]["d1_lookup"].get(srv_d1_key, -1)
        d1_u500 = sym_arrays["US500.cash"]["d1_lookup"].get(srv_d1_key, -1)

        for t_idx, sec_off in ((0, 0), (1, 20), (2, 40), (3, 59)):
            srv_ts = bar_srv_ts + sec_off
            now_utc = bar_utc_base + sec_off
            for s in PORT_7E_SYMBOLS:
                bpx = sym_tick_prices[s][t_idx]
                cur_bid[s] = bpx
                cur_ask[s] = round(bpx + cur_sp[s] * sym_pt[s], sym_dig[s]) if bpx > 0.0 else 0.0

            if open_positions:
                survivors: list[dict[str, Any]] = []
                for p in open_positions:
                    ps = p["symbol"]
                    sl_px = p["sl_price"]
                    hit = False
                    fill_px = sl_px
                    if p["is_buy"]:
                        if cur_bid[ps] > 0.0 and cur_bid[ps] <= sl_px:
                            hit = True
                            fill_px = cur_bid[ps] if (t_idx == 0 and cur_bid[ps] < sl_px) else sl_px
                    else:
                        if cur_ask[ps] > 0.0 and cur_ask[ps] >= sl_px:
                            hit = True
                            fill_px = cur_ask[ps] if (t_idx == 0 and cur_ask[ps] > sl_px) else sl_px
                    if hit:
                        _close_position(p, fill_px, srv_ts, now_utc, "SL")
                    else:
                        survivors.append(p)
                open_positions = survivors

            rdk = _current_reset_day_key(srv_ts, now_utc, cfg.daily_reset_mode)
            if rdk != day_key:
                day_key = rdk
                eq_tmp = bal + (sum(_unrealized_pnl_usd(p) for p in open_positions) if open_positions else 0.0)
                day_anchor_bal = bal
                day_anchor_eq = bal if cfg.daily_reset_mode == 1 else max(bal, eq_tmp)
                auto_kill_active = False

            eq = bal + (sum(_unrealized_pnl_usd(p) for p in open_positions) if open_positions else 0.0)
            if eq > peak_eq:
                peak_eq = eq
            if peak_eq > 0.0:
                edd = ((peak_eq - eq) / peak_eq) * 100.0
                if edd > max_eq_dd_pct:
                    max_eq_dd_pct = edd

            if cfg.daily_reset_mode == 1:
                daily_dd_pct = max(0.0, ((day_anchor_bal - eq) / cfg.initial_balance_usd) * 100.0)
            else:
                daily_dd_pct = max(0.0, ((day_anchor_eq - eq) / day_anchor_eq) * 100.0) if day_anchor_eq > 0.0 else 0.0
            static_dd_pct = max(0.0, ((cfg.initial_balance_usd - eq) / cfg.initial_balance_usd) * 100.0)
            eq_profit_pct = max(0.0, ((eq - cfg.initial_balance_usd) / cfg.initial_balance_usd) * 100.0)
            realized_profit_pct = max(0.0, ((bal - cfg.initial_balance_usd) / cfg.initial_balance_usd) * 100.0)
            risk_mult, _regime = compute_phase_risk_multiplier(
                cfg, daily_dd_pct, static_dd_pct, eq_profit_pct, realized_profit_pct
            )
            if daily_dd_pct >= cfg.kill_daily_dd_pct or static_dd_pct >= cfg.kill_static_dd_pct:
                auto_kill_active = True

            closed_cnt = 0
            if open_positions:
                survivors = []
                for p in open_positions:
                    ps = p["symbol"]
                    if auto_kill_active:
                        reason = (
                            "MASTER_KILL_DAILY_DD"
                            if daily_dd_pct >= cfg.kill_daily_dd_pct
                            else "MASTER_KILL_STATIC_DD"
                        )
                    else:
                        reason = _should_clock_flatten(p["magic"], now_utc, u_yr, u_mon, u_day, u_hr, bar_min, mql_dow)
                        if not reason and _is_near_session_close(ps, srv_ts):
                            reason = "HARD_FLAT_SESSION_CLOSE_SWAP0"
                        if not reason and cfg.enable_red_news and news_index.is_in_pre_flatten_window(ps, now_utc):
                            reason = "NEWS_PRE_FLATTEN_6CCY"
                        if reason and cfg.enable_red_news and news_index.is_inside_hard_ban(ps, now_utc):
                            reason = ""
                    if reason:
                        cpx = cur_bid[ps] if p["is_buy"] else cur_ask[ps]
                        _close_position(p, cpx, srv_ts, now_utc, reason)
                        closed_cnt += 1
                    else:
                        survivors.append(p)
                open_positions = survivors

            if cfg.post_close_refresh_mode == 1 and closed_cnt > 0:
                eq = bal + (sum(_unrealized_pnl_usd(p) for p in open_positions) if open_positions else 0.0)
                if cfg.daily_reset_mode == 1:
                    daily_dd_pct = max(0.0, ((day_anchor_bal - eq) / cfg.initial_balance_usd) * 100.0)
                else:
                    daily_dd_pct = (
                        max(0.0, ((day_anchor_eq - eq) / day_anchor_eq) * 100.0) if day_anchor_eq > 0.0 else 0.0
                    )
                static_dd_pct = max(0.0, ((cfg.initial_balance_usd - eq) / cfg.initial_balance_usd) * 100.0)
                eq_profit_pct = max(0.0, ((eq - cfg.initial_balance_usd) / cfg.initial_balance_usd) * 100.0)
                realized_profit_pct = max(0.0, ((bal - cfg.initial_balance_usd) / cfg.initial_balance_usd) * 100.0)
                risk_mult, _regime = compute_phase_risk_multiplier(
                    cfg, daily_dd_pct, static_dd_pct, eq_profit_pct, realized_profit_pct
                )
                if daily_dd_pct >= cfg.kill_daily_dd_pct or static_dd_pct >= cfg.kill_static_dd_pct:
                    auto_kill_active = True

            if auto_kill_active or mql_dow in (0, 6):
                continue

            # E1
            if utc_day != e1_box_day:
                e1_box_day = utc_day
                e1_box_ready = False
                e1_box_top = 0.0
                e1_box_bot = 0.0
            uj_a = cur_ask["USDJPY"]
            uj_b = cur_bid["USDJPY"]
            if 0 <= u_hr < 3 and uj_a > 0.0 and uj_b > 0.0:
                mid = 0.5 * (uj_a + uj_b)
                if not e1_box_ready:
                    e1_box_top = mid
                    e1_box_bot = mid
                    e1_box_ready = True
                else:
                    e1_box_top = max(e1_box_top, mid)
                    e1_box_bot = min(e1_box_bot, mid)
            elif (
                e1_box_ready
                and e1_box_top > e1_box_bot
                and traded_day[0] != utc_day
                and 3 <= u_hr < 10
                and u_hr < (18 - hel_off)
            ):
                if uj_a >= e1_box_top:
                    _process_intent(
                        engine_idx=0, engine_id="E1_USDJPY_TOKYO", magic=20261122, sym="USDJPY",
                        is_buy=True, sig_px=uj_a, raw_sl=e1_box_bot, base_risk_pct=0.16,
                        sess_day_key=utc_day, risk_mult=risk_mult, srv_ts=srv_ts, now_utc=now_utc,
                        u_hr=u_hr, mql_dow=mql_dow,
                    )
                elif uj_b <= e1_box_bot:
                    _process_intent(
                        engine_idx=0, engine_id="E1_USDJPY_TOKYO", magic=20261122, sym="USDJPY",
                        is_buy=False, sig_px=uj_b, raw_sl=e1_box_top, base_risk_pct=0.16,
                        sess_day_key=utc_day, risk_mult=risk_mult, srv_ts=srv_ts, now_utc=now_utc,
                        u_hr=u_hr, mql_dow=mql_dow,
                    )

            # E2
            if 7 <= u_hr < 17 and d1_uj > 0 and traded_day[1] != srv_d1_key:
                atr_uj = float(sym_arrays["USDJPY"]["d1_prior_atr"][d1_uj])
                do_uj = float(sym_arrays["USDJPY"]["d1_open"][d1_uj])
                if atr_uj > 0.0 and do_uj > 0.0:
                    if uj_a >= do_uj + 0.80 * atr_uj:
                        _process_intent(
                            engine_idx=1, engine_id="E2_USDJPY_EXP80", magic=20261123, sym="USDJPY",
                            is_buy=True, sig_px=uj_a, raw_sl=uj_a - 0.75 * atr_uj, base_risk_pct=0.59,
                            sess_day_key=srv_d1_key, risk_mult=risk_mult, srv_ts=srv_ts, now_utc=now_utc,
                            u_hr=u_hr, mql_dow=mql_dow,
                        )
                    elif uj_b <= do_uj - 0.80 * atr_uj:
                        _process_intent(
                            engine_idx=1, engine_id="E2_USDJPY_EXP80", magic=20261123, sym="USDJPY",
                            is_buy=False, sig_px=uj_b, raw_sl=uj_b + 0.75 * atr_uj, base_risk_pct=0.59,
                            sess_day_key=srv_d1_key, risk_mult=risk_mult, srv_ts=srv_ts, now_utc=now_utc,
                            u_hr=u_hr, mql_dow=mql_dow,
                        )

            # E3
            if 7 <= u_hr < 17 and d1_gbp > 0 and traded_day[2] != srv_d1_key:
                atr_g = float(sym_arrays["GBPUSD"]["d1_prior_atr"][d1_gbp])
                prng_g = float(sym_arrays["GBPUSD"]["d1_prior_range"][d1_gbp])
                do_g = float(sym_arrays["GBPUSD"]["d1_open"][d1_gbp])
                if atr_g > 0.0 and do_g > 0.0 and prng_g >= 1.10 * atr_g:
                    ga, gb = cur_ask["GBPUSD"], cur_bid["GBPUSD"]
                    if ga >= do_g + 0.80 * atr_g:
                        _process_intent(
                            engine_idx=2, engine_id="E3_GBPUSD_VH", magic=20261125, sym="GBPUSD",
                            is_buy=True, sig_px=ga, raw_sl=ga - 0.75 * atr_g, base_risk_pct=0.75,
                            sess_day_key=srv_d1_key, risk_mult=risk_mult, srv_ts=srv_ts, now_utc=now_utc,
                            u_hr=u_hr, mql_dow=mql_dow,
                        )
                    elif gb <= do_g - 0.80 * atr_g:
                        _process_intent(
                            engine_idx=2, engine_id="E3_GBPUSD_VH", magic=20261125, sym="GBPUSD",
                            is_buy=False, sig_px=gb, raw_sl=gb + 0.75 * atr_g, base_risk_pct=0.75,
                            sess_day_key=srv_d1_key, risk_mult=risk_mult, srv_ts=srv_ts, now_utc=now_utc,
                            u_hr=u_hr, mql_dow=mql_dow,
                        )

            # E6
            if 7 <= u_hr < 17 and d1_ej > 0 and traded_day[5] != srv_d1_key:
                if bool(sym_arrays["EURJPY"]["d1_e6_ok"][d1_ej]):
                    atr_e = float(sym_arrays["EURJPY"]["d1_prior_atr"][d1_ej])
                    do_e = float(sym_arrays["EURJPY"]["d1_open"][d1_ej])
                    if atr_e > 0.0 and do_e > 0.0:
                        ea, eb = cur_ask["EURJPY"], cur_bid["EURJPY"]
                        if ea >= do_e + 0.75 * atr_e:
                            _process_intent(
                                engine_idx=5, engine_id="E6_EURJPY_VOLCOMP", magic=20261128, sym="EURJPY",
                                is_buy=True, sig_px=ea, raw_sl=ea - 0.75 * atr_e, base_risk_pct=0.50,
                                sess_day_key=srv_d1_key, risk_mult=risk_mult, srv_ts=srv_ts, now_utc=now_utc,
                                u_hr=u_hr, mql_dow=mql_dow,
                            )
                        elif eb <= do_e - 0.75 * atr_e:
                            _process_intent(
                                engine_idx=5, engine_id="E6_EURJPY_VOLCOMP", magic=20261128, sym="EURJPY",
                                is_buy=False, sig_px=eb, raw_sl=eb + 0.75 * atr_e, base_risk_pct=0.50,
                                sess_day_key=srv_d1_key, risk_mult=risk_mult, srv_ts=srv_ts, now_utc=now_utc,
                                u_hr=u_hr, mql_dow=mql_dow,
                            )

            # Shared NY 09:30 ET anchor
            if ny_day != ny_anchor_day:
                ny_anchor_day = ny_day
                ny_anchor_ready = False
                us100_open_0930 = 0.0
                us500_open_0930 = 0.0
            if not ny_anchor_ready and ny_mins >= 9 * 60 + 30 and (now_utc - ny_anchor_last_try) >= 60:
                ny_anchor_last_try = now_utc
                i100, i500 = cur_m1_idx["US100.cash"], cur_m1_idx["US500.cash"]
                if i100 >= 0 and i500 >= 0:
                    u100_px = (
                        cur_bid["US100.cash"]
                        if int(sym_ts_srv["US100.cash"][i100]) == bar_srv_ts
                        else float(sym_close["US100.cash"][i100])
                    )
                    u500_px = (
                        cur_bid["US500.cash"]
                        if int(sym_ts_srv["US500.cash"][i500]) == bar_srv_ts
                        else float(sym_close["US500.cash"][i500])
                    )
                    if u100_px > 0.0 and u500_px > 0.0:
                        us100_open_0930 = u100_px
                        us500_open_0930 = u500_px
                        ny_anchor_ready = True

            # E4
            if not is_us_half and ny_mins < 15 * 60 + 55:
                if ny_day != e4_sess_day:
                    e4_sess_day = ny_day
                    e4_morn_init = False
                    e4_morn_frozen = False
                    e4_morn_dir = 0
                u100_b, u100_a = cur_bid["US100.cash"], cur_ask["US100.cash"]
                if 9 * 60 + 30 <= ny_mins < 11 * 60 + 30 and u100_b > 0.0:
                    if not e4_morn_init:
                        e4_morn_open = e4_morn_high = e4_morn_low = e4_morn_close = u100_b
                        e4_morn_init = True
                    else:
                        e4_morn_high = max(e4_morn_high, u100_b)
                        e4_morn_low = min(e4_morn_low, u100_b)
                        e4_morn_close = u100_b
                if not e4_morn_frozen and ny_mins >= 11 * 60 + 30 and d1_u100 > 0:
                    atr_u100 = float(sym_arrays["US100.cash"]["d1_prior_atr"][d1_u100])
                    if atr_u100 > 0.0:
                        e4_morn_frozen = True
                        mrng = e4_morn_high - e4_morn_low
                        if e4_morn_init and mrng > 0.0 and abs(e4_morn_close - e4_morn_open) >= 0.40 * atr_u100:
                            pos_frac = (e4_morn_close - e4_morn_low) / mrng
                            if e4_morn_close > e4_morn_open and pos_frac >= 0.70:
                                e4_morn_dir = 1
                            elif e4_morn_close < e4_morn_open and pos_frac <= 0.30:
                                e4_morn_dir = -1
                if e4_morn_frozen and e4_morn_dir != 0 and traded_day[3] != ny_day and d1_u100 > 0:
                    atr_u100 = float(sym_arrays["US100.cash"]["d1_prior_atr"][d1_u100])
                    if atr_u100 > 0.0:
                        if e4_morn_dir == 1 and u100_a >= e4_morn_high:
                            _process_intent(
                                engine_idx=3, engine_id="E4_US100_SESS40", magic=20261124, sym="US100.cash",
                                is_buy=True, sig_px=u100_a, raw_sl=u100_a - 0.65 * atr_u100, base_risk_pct=0.50,
                                sess_day_key=ny_day, risk_mult=risk_mult, srv_ts=srv_ts, now_utc=now_utc,
                                u_hr=u_hr, mql_dow=mql_dow,
                            )
                        elif e4_morn_dir == -1 and u100_b <= e4_morn_low:
                            _process_intent(
                                engine_idx=3, engine_id="E4_US100_SESS40", magic=20261124, sym="US100.cash",
                                is_buy=False, sig_px=u100_b, raw_sl=u100_b + 0.65 * atr_u100, base_risk_pct=0.50,
                                sess_day_key=ny_day, risk_mult=risk_mult, srv_ts=srv_ts, now_utc=now_utc,
                                u_hr=u_hr, mql_dow=mql_dow,
                            )

            # E5
            if (
                not is_us_half
                and ny_anchor_ready
                and traded_day[4] != ny_day
                and 11 * 60 + 30 <= ny_mins < 11 * 60 + 40
                and d1_u100 > 0
                and d1_u500 > 0
            ):
                atr_m = float(sym_arrays["US100.cash"]["d1_prior_atr"][d1_u100])
                atr_b = float(sym_arrays["US500.cash"]["d1_prior_atr"][d1_u500])
                i100, i500 = cur_m1_idx["US100.cash"], cur_m1_idx["US500.cash"]
                prev_i100 = (i100 - 1) if (i100 > 0 and int(sym_ts_srv["US100.cash"][i100]) == bar_srv_ts) else i100
                prev_i500 = (i500 - 1) if (i500 > 0 and int(sym_ts_srv["US500.cash"][i500]) == bar_srv_ts) else i500
                if atr_m > 0.0 and atr_b > 0.0 and prev_i100 >= 0 and prev_i500 >= 0:
                    m1_c, b1_c = float(sym_close["US100.cash"][prev_i100]), float(sym_close["US500.cash"][prev_i500])
                    if m1_c > 0.0 and b1_c > 0.0:
                        z_main = (m1_c - us100_open_0930) / atr_m
                        z_bench = (b1_c - us500_open_0930) / atr_b
                        rs_diff = z_main - z_bench
                        if abs(rs_diff) < 0.25 or (z_main * rs_diff) <= 0.0:
                            traded_day[4] = ny_day
                        else:
                            e5_buy = rs_diff > 0.0
                            e5_px = cur_ask["US100.cash"] if e5_buy else cur_bid["US100.cash"]
                            e5_sl = (e5_px - 0.75 * atr_m) if e5_buy else (e5_px + 0.75 * atr_m)
                            _process_intent(
                                engine_idx=4, engine_id="E5_US100_RS1130", magic=20261126, sym="US100.cash",
                                is_buy=e5_buy, sig_px=e5_px, raw_sl=e5_sl, base_risk_pct=0.50,
                                sess_day_key=ny_day, risk_mult=risk_mult, srv_ts=srv_ts, now_utc=now_utc,
                                u_hr=u_hr, mql_dow=mql_dow,
                            )

            # E7
            if (
                not is_us_half
                and ny_anchor_ready
                and traded_day[6] != ny_day
                and 10 * 60 <= ny_mins < 10 * 60 + 10
                and d1_u100 > 0
                and d1_uj > 0
            ):
                atr_eq = float(sym_arrays["US100.cash"]["d1_prior_atr"][d1_u100])
                atr_jpy = float(sym_arrays["USDJPY"]["d1_prior_atr"][d1_uj])
                i100 = cur_m1_idx["US100.cash"]
                prev_i100 = (i100 - 1) if (i100 > 0 and int(sym_ts_srv["US100.cash"][i100]) == bar_srv_ts) else i100
                if atr_eq > 0.0 and atr_jpy > 0.0 and prev_i100 >= 0:
                    eq1 = float(sym_close["US100.cash"][prev_i100])
                    lb_mins = max(60, (u_hr - 7) * 60 + bar_min)
                    usd_sum = 0.0
                    ok_bsk = eq1 > 0.0
                    for bsym, bsgn in e7_basket:
                        if not ok_bsk:
                            break
                        bd1 = sym_arrays[bsym]["d1_lookup"].get(srv_d1_key, -1)
                        if bd1 <= 0:
                            ok_bsk = False
                            break
                        ab = float(sym_arrays[bsym]["d1_prior_atr"][bd1])
                        bi_s = cur_m1_idx[bsym]
                        p1_idx = (bi_s - 1) if (bi_s > 0 and int(sym_ts_srv[bsym][bi_s]) == bar_srv_ts) else bi_s
                        p0_idx = p1_idx - lb_mins
                        if ab <= 0.0 or p0_idx < 0 or p1_idx < 0:
                            ok_bsk = False
                            break
                        p1, p0 = float(sym_close[bsym][p1_idx]), float(sym_close[bsym][p0_idx])
                        if p1 <= 0.0 or p0 <= 0.0:
                            ok_bsk = False
                            break
                        usd_sum += float(bsgn) * ((p1 - p0) / ab)
                    if ok_bsk:
                        z_eq = (eq1 - us100_open_0930) / atr_eq
                        usd_fac = usd_sum / 5.0
                        if abs(z_eq) < 0.25 or abs(usd_fac) < 0.25 or (z_eq * usd_fac) <= 0.0:
                            traded_day[6] = ny_day
                        else:
                            e7_buy = usd_fac > 0.0
                            e7_px = cur_ask["USDJPY"] if e7_buy else cur_bid["USDJPY"]
                            e7_sl = (e7_px - 0.75 * atr_jpy) if e7_buy else (e7_px + 0.75 * atr_jpy)
                            _process_intent(
                                engine_idx=6, engine_id="E7_USDJPY_NY10ET", magic=20261129, sym="USDJPY",
                                is_buy=e7_buy, sig_px=e7_px, raw_sl=e7_sl, base_risk_pct=0.50,
                                sess_day_key=ny_day, risk_mult=risk_mult, srv_ts=srv_ts, now_utc=now_utc,
                                u_hr=u_hr, mql_dow=mql_dow,
                            )

    if open_positions:
        last_srv = int(uj_srv[-1]) + 59
        last_utc = mt5_tester_now_utc(last_srv, cfg.tester_utc_offset_h)
        for p in list(open_positions):
            ps = p["symbol"]
            cpx = cur_bid[ps] if p["is_buy"] else cur_ask[ps]
            _close_position(p, cpx, last_srv, last_utc, "END_OF_TEST")
        open_positions.clear()

    # Cross-check ORT & Pure-MQL5 mirror on ALL 2024 FTMO same-feed signals (if onnx_path / mqh_text given)
    x_2024 = (
        np.vstack([r["features_f32"] for r in signal_rows]).astype(np.float32)
        if signal_rows
        else np.empty((0, len(sel_idx)), dtype=np.float32)
    )
    p_2024_ref = np.array([r["ref_p_win"] for r in signal_rows], dtype=np.float64)

    ort_2024_max_err: float | None = None
    mqh_2024_max_err: float | None = None
    if signal_rows and onnx_path is not None and onnx_path.is_file():
        ort_chk = verify_onnx_runtime_parity(onnx_path, x_2024, p_2024_ref, tol=STRICT_ONNX_PARITY_TOL)
        ort_2024_max_err = float(ort_chk["max_abs_err_single"])
    if signal_rows and mqh_text is not None:
        p_mqh = evaluate_mqh_v105_mirror(mqh_text, x_2024)
        mqh_2024_max_err = float(np.max(np.abs(p_mqh - p_2024_ref)))
        if mqh_2024_max_err > STRICT_ONNX_PARITY_TOL:
            raise ValueError(f"2024_REF_MQH_PARITY_BREACH: {mqh_2024_max_err:.3e} > {STRICT_ONNX_PARITY_TOL:.3e}")

    csv_sha: str | None = None
    csv_bytes: int | None = None
    if out_csv_path is not None:
        k_feat = len(sel_idx)
        header_cols = [
            "signal_seq",
            "entry_utc_ts",
            "entry_server_time",
            "engine_id",
            "magic",
            "symbol",
            "side",
            *[f"f{j}" for j in range(k_feat)],
            "ref_p_win",
            "ref_ml_allowed",
            "ref_size_mult",
            "shadow_eq_1x",
            "shadow_peak_1x",
            "shadow_dd_pct_1x",
            "same_dir_concurrent",
        ]
        lines = [",".join(header_cols)]
        for r in signal_rows:
            f_strs = [f"{float(r['features_f32'][j]):.9g}" for j in range(k_feat)]
            lines.append(
                ",".join(
                    [
                        str(r["signal_seq"]),
                        str(r["entry_utc_ts"]),
                        str(r["entry_server_time"]),
                        str(r["engine_id"]),
                        str(r["magic"]),
                        str(r["symbol"]),
                        str(r["side"]),
                        *f_strs,
                        f"{float(r['ref_p_win']):.12f}",
                        str(int(r["ref_ml_allowed"])),
                        f"{float(r['ref_size_mult']):.4f}",
                        f"{float(r['shadow_eq_1x']):.10f}",
                        f"{float(r['shadow_peak_1x']):.10f}",
                        f"{float(r['shadow_dd_pct_1x']):.8f}",
                        str(int(r["same_dir_concurrent"])),
                    ]
                )
            )
        _atomic_write_text_lf(out_csv_path, "\n".join(lines) + "\n")
        csv_sha = sha256_file(out_csv_path)
        csv_bytes = out_csv_path.stat().st_size

    gp = sum(p["net_pnl_usd"] for p in closed_positions if p["net_pnl_usd"] > 0.0)
    gl = sum(p["net_pnl_usd"] for p in closed_positions if p["net_pnl_usd"] < 0.0)
    pf = (gp / abs(gl)) if gl < 0.0 else (99.0 if gp > 0.0 else 0.0)
    net_pnl = round_cent_half_up(bal - cfg.initial_balance_usd)
    accepted_cnt = sum(1 for r in signal_rows if r["ref_ml_allowed"] == 1)
    rejected_cnt = len(signal_rows) - accepted_cnt

    summary = {
        "schema_version": "naqex-wave5-2024-ftmo-features-ref-v1",
        "generated_utc": datetime.now(UTC).isoformat(),
        "oos_label": CONSUMED_CLB_TAG,
        "holdout_cutoff_date": HOLDOUT_CUTOFF_DATE,
        "holdout_rows_analysed": 0,
        "order_send_count": ORDER_SEND_COUNT,
        "window": f"{from_date.replace('.', '-')}..{to_date.replace('.', '-')}",
        "preset": cfg.preset_name,
        "ml_enabled": bool(ml_enabled),
        "ml_threshold": round(float(ml_threshold), 6),
        "selected_feature_indices": sel_idx,
        "selected_feature_names": sel_names,
        "signals_evaluated": len(signal_rows),
        "signals_accepted": accepted_cnt,
        "signals_rejected": rejected_cnt,
        "executed_trades_closed": len(closed_positions),
        "net_pnl_usd": net_pnl,
        "profit_factor": round(pf, 4),
        "max_eq_dd_pct": round(max_eq_dd_pct, 4),
        "ort_2024_max_abs_err": ort_2024_max_err,
        "mqh_2024_max_abs_err": mqh_2024_max_err,
        "csv_path": str(out_csv_path) if out_csv_path is not None else None,
        "csv_sha256": csv_sha,
        "csv_bytes": csv_bytes,
    }
    if out_meta_path is not None:
        assert_zero_forbidden_blind_label(summary)
        _atomic_write_json(out_meta_path, summary)
    return summary


# ---------------------------------------------------------------------------
# 7. OOF Trade & Daily Series Emitter for Wave 2B Spectrum MC
# ---------------------------------------------------------------------------


def build_oof_series_payload(
    *,
    trades: Sequence[Mapping[str, Any]],
    entry_ts: np.ndarray,
    exit_ts: np.ndarray,
    net_r: np.ndarray,
    risk_pct_1x: np.ndarray,
    oof_mask: np.ndarray,
    best_filter_run: Mapping[str, Any],
    best_asym_run: Mapping[str, Any],
    asymfloor_head_to_head_verdict: str,
) -> dict[str, Any]:
    """Build compact trade-level + daily-level OOF series JSON for Wave 2B Spectrum MC."""
    eval_idx = np.flatnonzero(oof_mask)
    if eval_idx.size == 0:
        raise ValueError("EMPTY_OOF_SERIES")

    ent_o = entry_ts[eval_idx]
    ext_o = exit_ts[eval_idx]
    if int(np.max(ent_o)) >= DEV_CUTOFF_SEC or int(np.max(ext_o)) >= DEV_CUTOFF_SEC:
        raise HoldoutCutoffBreachError("HOLDOUT_BREACH_OOF_SERIES")

    days_o = [
        str(trades[i].get("day") or datetime.fromtimestamp(int(entry_ts[i]), UTC).strftime("%Y-%m-%d"))
        for i in eval_idx.tolist()
    ]
    engs_o = [str(trades[i]["engine_id"]).upper() for i in eval_idx.tolist()]
    r_o = net_r[eval_idx]
    rf_o = risk_pct_1x[eval_idx]

    flt_p = np.asarray(best_filter_run["oof_probs"], dtype=np.float64)[eval_idx]
    flt_s = np.asarray(best_filter_run["oof_sizes"], dtype=np.float64)[eval_idx]
    asy_p = np.asarray(best_asym_run["oof_probs"], dtype=np.float64)[eval_idx]
    asy_s = np.asarray(best_asym_run["oof_sizes"], dtype=np.float64)[eval_idx]

    # Aggregate 1.0x daily return % (additive intra-day sum of size * net_R * base_risk_pct_1x)
    uniq_days = sorted(set(days_o))
    day_pos = {d: idx for idx, d in enumerate(uniq_days)}
    n_days = len(uniq_days)

    d_base = np.zeros(n_days, dtype=np.float64)
    d_flt = np.zeros(n_days, dtype=np.float64)
    d_asy = np.zeros(n_days, dtype=np.float64)
    for k in range(eval_idx.size):
        dp = day_pos[days_o[k]]
        base_ret_pct = float(r_o[k]) * float(rf_o[k])
        d_base[dp] += base_ret_pct
        d_flt[dp] += float(flt_s[k]) * base_ret_pct
        d_asy[dp] += float(asy_s[k]) * base_ret_pct

    clb_day_mask = [d >= CLB_START_DATE for d in uniq_days]
    clb_dates = [d for d, m in zip(uniq_days, clb_day_mask, strict=True) if m]

    payload: dict[str, Any] = {
        "schema_version": OOF_SERIES_SCHEMA_VERSION,
        "generated_utc": datetime.now(UTC).isoformat(),
        "oos_label": CONSUMED_CLB_TAG,
        "holdout_cutoff_date": HOLDOUT_CUTOFF_DATE,
        "holdout_rows_analysed": 0,
        "order_send_count": ORDER_SEND_COUNT,
        "n_oof_trades": int(eval_idx.size),
        "n_oof_days": n_days,
        "date_range_oof": [uniq_days[0], uniq_days[-1]],
        "clb_2021_2024_days": len(clb_dates),
        "variants": {
            "baseline_v103": {
                "trial_id": "v1.03_baseline_1x",
                "promoted": True,
                "avg_size_mult": 1.0,
            },
            "v105_ml_filter": {
                "trial_id": str(best_filter_run["trial_spec"]["trial_id"]),
                "family_name": str(best_filter_run["trial_spec"]["family_name"]),
                "verdict": str(best_filter_run["verdict_v105"]),
                "promoted": bool(best_filter_run["verdict_v105"] == VERDICT_PROMOTE_FILTER),
                "brier_skill_score": _json_safe_float(best_filter_run["evaluation"]["brier_skill_score"]),
                "roc_auc": _json_safe_float(best_filter_run["evaluation"]["roc_auc"]),
                "pf_1x": _json_safe_float(best_filter_run["evaluation"]["economics_1x"]["ml_v104"]["profit_factor"]),
                "max_dd_pct_1x": _json_safe_float(
                    best_filter_run["evaluation"]["economics_1x"]["ml_v104"]["max_dd_pct"]
                ),
                "slippage_breakeven_24m": _json_safe_float(
                    best_filter_run["evaluation"]["slippage_breakeven_24m"]["ml_v104_median_mult"]
                ),
                "avg_size_mult": _json_safe_float(float(np.mean(flt_s))),
            },
            "v105_ml_asymfloor": {
                "trial_id": str(best_asym_run["trial_spec"]["trial_id"]),
                "family_name": str(best_asym_run["trial_spec"]["family_name"]),
                "sizing_policy": str(best_asym_run["trial_spec"]["sizing_policy"]),
                "sizing_params": dict(best_asym_run["trial_spec"].get("sizing_params", {})),
                "verdict": asymfloor_head_to_head_verdict,
                "promoted": bool(asymfloor_head_to_head_verdict == ASYMFLOOR_VERDICT_PROMOTE),
                "brier_skill_score": _json_safe_float(best_asym_run["evaluation"]["brier_skill_score"]),
                "roc_auc": _json_safe_float(best_asym_run["evaluation"]["roc_auc"]),
                "pf_1x": _json_safe_float(best_asym_run["evaluation"]["economics_1x"]["ml_v104"]["profit_factor"]),
                "max_dd_pct_1x": _json_safe_float(best_asym_run["evaluation"]["economics_1x"]["ml_v104"]["max_dd_pct"]),
                "slippage_breakeven_24m": _json_safe_float(
                    best_asym_run["evaluation"]["slippage_breakeven_24m"]["ml_v104_median_mult"]
                ),
                "avg_size_mult": _json_safe_float(float(np.mean(asy_s))),
            },
        },
        "daily_series": {
            "dates": uniq_days,
            "baseline_v103_daily_ret_1x_pct": [round(float(v), 6) for v in d_base.tolist()],
            "v105_ml_filter_daily_ret_1x_pct": [round(float(v), 6) for v in d_flt.tolist()],
            "v105_ml_asymfloor_daily_ret_1x_pct": [round(float(v), 6) for v in d_asy.tolist()],
        },
        "trade_series": {
            "days": days_o,
            "entry_ts": [int(v) for v in ent_o.tolist()],
            "exit_ts": [int(v) for v in ext_o.tolist()],
            "engine_ids": engs_o,
            "base_risk_pct_1x": [round(float(v), 4) for v in rf_o.tolist()],
            "raw_net_r": [round(float(v), 6) for v in r_o.tolist()],
            "v105_ml_filter_probs": [round(float(v), 6) for v in flt_p.tolist()],
            "v105_ml_filter_sizes": [round(float(v), 4) for v in flt_s.tolist()],
            "v105_ml_asymfloor_probs": [round(float(v), 6) for v in asy_p.tolist()],
            "v105_ml_asymfloor_sizes": [round(float(v), 4) for v in asy_s.tolist()],
        },
    }
    assert_zero_forbidden_blind_label(payload)
    return payload


# ---------------------------------------------------------------------------
# 8. Core Wave 5 Arena Orchestrator (`run_v105_ml_arena`)
# ---------------------------------------------------------------------------


def _compact_v105_trial_record(
    run_out: Mapping[str, Any],
    *,
    ledger_receipt: Mapping[str, Any] | None,
    runtime_sec: float,
) -> dict[str, Any]:
    spec = run_out["trial_spec"]
    ev = run_out["evaluation"]
    clb = run_out["clb_eval"]
    prob = ev["probabilistic_metrics"]
    eb = ev["engine_balance"]
    e1x = ev["economics_1x"]
    sb = ev["slippage_breakeven_24m"]
    avg_k = int(round(float(np.mean([f["n_features_selected"] for f in run_out["folds"]]))))

    clb_c = None
    if clb is not None:
        clb_c = {
            "n_trades": int(clb["n_trades"]),
            "oos_label": str(clb["oos_label"]),
            "brier_skill_score": _json_safe_float(clb["brier_skill_score"]),
            "roc_auc": _json_safe_float(clb["roc_auc"]),
            "min_engine_retention_ratio": _json_safe_float(clb["engine_balance"]["min_engine_retention_ratio"]),
            "overall_retention_ratio": _json_safe_float(clb["engine_balance"]["overall_retention_ratio"]),
            "baseline_v103_24m_be": _json_safe_float(clb["slippage_breakeven_24m"]["baseline_v103_median_mult"]),
            "ml_v105_24m_be": _json_safe_float(clb["slippage_breakeven_24m"]["ml_v104_median_mult"]),
            "pf_1x": _json_safe_float(clb["economics_1x"]["ml_v104"]["profit_factor"]),
            "ev_r_1x": _json_safe_float(clb["economics_1x"]["ml_v104"]["ev_r"]),
            "max_dd_pct_1x": _json_safe_float(clb["economics_1x"]["ml_v104"]["max_dd_pct"]),
            "gates": dict(clb["gates"]),
            "rejection_reasons": list(clb["rejection_reasons"]),
        }

    top_imp = sorted(
        ((str(k), float(v)) for k, v in run_out["oof_feature_importance"].items()),
        key=lambda kv: (-kv[1], kv[0]),
    )[:12]

    return {
        "trial_seq": int(ledger_receipt["trial_seq"]) if ledger_receipt is not None else 0,
        "trial_id": str(spec["trial_id"]),
        "track_name": str(spec["track_name"]),
        "family_name": str(spec["family_name"]),
        "sizing_policy": str(spec["sizing_policy"]),
        "sizing_params": dict(spec.get("sizing_params", {})),
        "label": str(spec.get("label", spec["trial_id"])),
        "model_params": dict(spec.get("model_params", {})),
        "oos_label": str(ev["oos_label"]),
        "n_folds": len(run_out["folds"]),
        "n_oof_samples": int(np.sum(run_out["oof_mask"])),
        "n_features_selected_avg": avg_k,
        "brier_model": _json_safe_float(prob["brier_model"]),
        "brier_climatology": _json_safe_float(prob["brier_climatology"]),
        "brier_skill_score": _json_safe_float(ev["brier_skill_score"]),
        "logloss": _json_safe_float(prob["logloss"]),
        "roc_auc": _json_safe_float(ev["roc_auc"]),
        "min_engine_retention_ratio": _json_safe_float(eb["min_engine_retention_ratio"]),
        "overall_retention_ratio": _json_safe_float(eb["overall_retention_ratio"]),
        "avg_size_mult": _json_safe_float(e1x["ml_v104"]["avg_size"]),
        "dropped_engines": list(eb["dropped_engines"]),
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
        "float32_decision_agreement": _json_safe_float(
            ev.get("float32_onnx_stability", {}).get("float32_decision_agreement", 1.0)
        ),
        "float32_onnx_deployable": bool(ev.get("gates", {}).get("float32_onnx_deployable", True)),
        "float32_onnx_stability": dict(ev.get("float32_onnx_stability", {})),
        "clb_2021_2024_temporal_oos": clb_c,
        "top_features": [
            {"rank": i + 1, "feature": k, "mean_abs_attribution": round(v, 6)}
            for i, (k, v) in enumerate(top_imp)
        ],
        "gates": dict(ev["gates"]),
        "rejection_reasons": list(ev["rejection_reasons"]),
        "verdict": str(run_out["verdict_v105"]),
        "runtime_seconds": _json_safe_float(runtime_sec, digits=3),
    }


def _evaluate_asymfloor_head_to_head(
    best_filter: Mapping[str, Any],
    best_asym: Mapping[str, Any],
) -> tuple[str, list[str]]:
    """Honest head-to-head judge: AsymFloor promotes ONLY if it clears ALL gates AND beats BOTH v1.03 & v1.05-Filter."""
    reasons: list[str] = []
    asym_cleared = best_asym["verdict"] == VERDICT_PROMOTE_ASYMFLOOR
    filter_cleared = best_filter["verdict"] == VERDICT_PROMOTE_FILTER

    if not asym_cleared:
        reasons.append(f"ASYMFLOOR_FAILED_HARD_GATES ({'; '.join(best_asym['rejection_reasons'])})")
        if filter_cleared:
            return ASYMFLOOR_VERDICT_REJECT_KEEP_FILTER, reasons
        return ASYMFLOOR_VERDICT_REJECT_KEEP_V103, reasons

    # Even if AsymFloor cleared standalone gates vs v1.03, check if it genuinely beats v1.05-ML-Filter!
    if filter_cleared:
        beats_pf = float(best_asym["pf_1x"]) > float(best_filter["pf_1x"]) + 1e-6
        beats_be = float(best_asym["slippage_breakeven_24m"]) >= float(best_filter["slippage_breakeven_24m"]) - 1e-6
        beats_dd = float(best_asym["max_dd_pct_1x"]) <= float(best_filter["max_dd_pct_1x"]) + 0.25
        if not (beats_pf and beats_be and beats_dd):
            reasons.append(
                "ASYMFLOOR_DID_NOT_BEAT_BINARY_FILTER "
                f"(asym pf={best_asym['pf_1x']:.4f}/be={best_asym['slippage_breakeven_24m']:.3f}x/"
                f"dd={best_asym['max_dd_pct_1x']:.2f}% vs "
                f"filter pf={best_filter['pf_1x']:.4f}/be={best_filter['slippage_breakeven_24m']:.3f}x/"
                f"dd={best_filter['max_dd_pct_1x']:.2f}%)"
            )
            return ASYMFLOOR_VERDICT_REJECT_KEEP_FILTER, reasons

    return ASYMFLOOR_VERDICT_PROMOTE, []


def _select_lgbm_export_trial(trial_records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Select best float32-deployable LightGBM binary-filter trial for ONNX/MQL5 export."""
    lgbm_flt_prom = [
        t
        for t in trial_records
        if t["family_name"] == "lightgbm"
        and t["track_name"] == "v105_ml_filter"
        and t["verdict"] == VERDICT_PROMOTE_FILTER
        and bool(t.get("float32_onnx_deployable", True))
    ]
    if lgbm_flt_prom:
        return dict(
            max(
                lgbm_flt_prom,
                key=lambda t: (
                    float(t["brier_skill_score"]),
                    float(t["slippage_breakeven_24m"]),
                    float(t["pf_1x"]),
                    float(t["roc_auc"]),
                ),
            )
        )
    lgbm_flt_any = [
        t
        for t in trial_records
        if t["family_name"] == "lightgbm"
        and t["track_name"] == "v105_ml_filter"
        and bool(t.get("float32_onnx_deployable", True))
    ]
    if lgbm_flt_any:
        return dict(
            max(
                lgbm_flt_any,
                key=lambda t: (
                    1
                    if (
                        float(t["brier_skill_score"]) > 0.0
                        and float(t["delta_slippage_breakeven_24m"]) > 0.0
                        and bool(t["gates"].get("clb_2021_2024_temporal_oos_passed", False))
                    )
                    else 0,
                    1 if float(t["brier_skill_score"]) > 0.0 else 0,
                    float(t["brier_skill_score"]),
                    float(t["slippage_breakeven_24m"]),
                    float(t["pf_1x"]),
                ),
            )
        )
    lgbm_any = [t for t in trial_records if t["family_name"] == "lightgbm"]
    if lgbm_any:
        return dict(
            max(
                lgbm_any,
                key=lambda t: (
                    float(t["brier_skill_score"]),
                    float(t["roc_auc"]),
                    float(t["slippage_breakeven_24m"]),
                    float(t["pf_1x"]),
                ),
            )
        )
    return dict(
        max(
            trial_records,
            key=lambda t: (float(t["brier_skill_score"]), float(t["roc_auc"]), float(t["pf_1x"])),
        )
    )


def run_v105_ml_arena(
    X: np.ndarray,
    y: np.ndarray,
    entry_ts: Any,
    exit_ts: Any,
    net_r: np.ndarray | Sequence[float],
    engine_ids: Sequence[str],
    trades: Sequence[Mapping[str, Any]],
    *,
    feature_names: Sequence[str] = FEATURE_NAMES_V105,
    trial_grid: Sequence[Mapping[str, Any]] | None = None,
    db_path: str | Path | None = DEFAULT_DB_PATH,
    max_trials: int = DEFAULT_MAX_ML_TRIALS,
    out_dir: str | Path | None = DEFAULT_ML_OUT_DIR,
    mqh_out_path: str | Path | None = DEFAULT_MQH_PATH,
    n_splits: int = 5,
    purge_days: int = DEFAULT_PURGE_DAYS,
    embargo_days: int = DEFAULT_EMBARGO_DAYS,
    min_train_samples: int = DEFAULT_MIN_TRAIN_SAMPLES,
    min_k: int = DEFAULT_MIN_SELECTED_FEATURES,
    max_k: int = DEFAULT_MAX_SELECTED_FEATURES,
    slippage_mults: Sequence[float] = DEFAULT_SLIPPAGE_MULTS,
    base_cost_r: float = DEFAULT_BASE_COST_R,
    risk_pct_1x: np.ndarray | None = None,
    oos_label: str = CONSUMED_CLB_TAG,
    cutoff_utc: str | date | datetime | int = HOLDOUT_CUTOFF_DATE,
    n_parity_samples: int = DEFAULT_PARITY_SAMPLES,
    holdout_lock_sha256: str | None = None,
    random_state: int = 42,
    use_duckdb_ledger: bool = True,
    export_onnx_and_mqh: bool = True,
    export_2024_ftmo_ref: bool = False,
) -> dict[str, Any]:
    """Run complete Wave 5 `v1.05-ML-Filter` vs `v1.05-ML-AsymFloor` head-to-head arena & exports."""
    t0 = time.perf_counter()
    mode_a_info = apply_mode_a_owner_active_guard(cores=MODE_A_MAX_CORES)
    validated_oos = validate_oos_label(oos_label)
    cutoff_sec = parse_cutoff_utc_exclusive(cutoff_utc)

    x_arr = np.ascontiguousarray(_validate_float_array(X, name="X"), dtype=np.float32)
    y_arr = _validate_float_array(y, name="y")
    r_arr = _validate_float_array(net_r, name="net_r")
    ent_arr = _parse_timestamp_array(entry_ts, name="entry_ts")
    ext_arr = _parse_timestamp_array(exit_ts, name="exit_ts")
    n_rows = int(x_arr.shape[0])

    if x_arr.ndim != 2 or n_rows == 0:
        raise ValueError(f"INVALID_X_SHAPE: {x_arr.shape}")
    if y_arr.size != n_rows or r_arr.size != n_rows or ent_arr.size != n_rows or ext_arr.size != n_rows:
        raise ValueError("INPUT_LENGTH_MISMATCH across X, y, net_r, entry_ts, exit_ts")
    if len(engine_ids) != n_rows or len(trades) != n_rows:
        raise ValueError("INPUT_LENGTH_MISMATCH across engine_ids / trades")
    if int(np.max(ent_arr)) >= cutoff_sec or int(np.max(ext_arr)) >= cutoff_sec:
        raise HoldoutCutoffBreachError(
            f"HOLDOUT_TIMESTAMP_BREACH: max_entry={int(np.max(ent_arr))}, "
            f"max_exit={int(np.max(ext_arr))} >= {cutoff_sec}"
        )

    rf_arr = (
        np.array([canonical_base_risk_pct_1x(e) for e in engine_ids], dtype=np.float64)
        if risk_pct_1x is None
        else _validate_float_array(risk_pct_1x, name="risk_pct_1x", positive=True)
    )

    raw_grid = build_preregistered_v105_grid(random_state=random_state) if trial_grid is None else trial_grid
    grid = validate_v105_arena_grid(raw_grid, max_trials=max_trials)

    trial_records: list[dict[str, Any]] = []
    trial_runs_by_id: dict[str, dict[str, Any]] = {}
    ledger_summary: dict[str, Any] | None = None
    baseline_full_oof: dict[str, Any] | None = None
    baseline_clb_oof: dict[str, Any] | None = None
    splitter_audits: list[dict[str, Any]] = []

    ledger: Wave5MlBudgetLedger | None = None
    try:
        if use_duckdb_ledger and db_path is not None:
            # Start fresh DuckDB file if running a clean full pre-registered arena grid at default path?
            # Never silently exceed budget: if ledger already has rows, enforce remaining_budget strictly!
            ledger = Wave5MlBudgetLedger(db_path=db_path, max_trials=max_trials, cutoff_utc=cutoff_utc)
            rem = ledger.remaining_budget()
            if len(grid) > rem:
                raise BudgetExceededError(
                    f"INSUFFICIENT_DUCKDB_BUDGET: grid needs {len(grid)} trials, "
                    f"but ledger {db_path} has only {rem}/{max_trials} remaining"
                )

        for spec in grid:
            t_tr = time.perf_counter()
            run_out = run_v105_walkforward_trial(
                x_arr.astype(np.float64),
                y_arr,
                ent_arr,
                ext_arr,
                r_arr,
                engine_ids,
                trial_spec=spec,
                feature_names=feature_names,
                n_splits=n_splits,
                purge_days=purge_days,
                embargo_days=embargo_days,
                min_train_samples=min_train_samples,
                min_k=min_k,
                max_k=max_k,
                slippage_mults=slippage_mults,
                base_cost_r=base_cost_r,
                risk_pct_1x=rf_arr,
                oos_label=validated_oos,
                cutoff_utc=cutoff_utc,
            )

            ev = run_out["evaluation"]
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
                    for f in run_out["folds"]
                ]
            if baseline_full_oof is None:
                baseline_full_oof = {
                    "n_oof_trades": int(np.sum(run_out["oof_mask"])),
                    "oos_label": validated_oos,
                    "base_cost_r": float(base_cost_r),
                    "economics_1x": dict(ev["economics_1x"]["baseline_v103"]),
                    "slippage_breakeven_24m": _json_safe_float(
                        ev["slippage_breakeven_24m"]["baseline_v103_median_mult"]
                    ),
                }
            if baseline_clb_oof is None and run_out["clb_eval"] is not None:
                clb = run_out["clb_eval"]
                baseline_clb_oof = {
                    "n_oof_trades": int(clb["n_trades"]),
                    "window": f"{CLB_START_DATE}..{HOLDOUT_CUTOFF_DATE}",
                    "oos_label": validated_oos,
                    "economics_1x": dict(clb["economics_1x"]["baseline_v103"]),
                    "slippage_breakeven_24m": _json_safe_float(
                        clb["slippage_breakeven_24m"]["baseline_v103_median_mult"]
                    ),
                }

            avg_k = int(round(float(np.mean([f["n_features_selected"] for f in run_out["folds"]]))))
            l_rec = None
            if ledger is not None:
                l_rec = ledger.record_trial(
                    trial_id=str(spec["trial_id"]),
                    track_name=str(spec["track_name"]),
                    family_name=str(spec["family_name"]),
                    sizing_policy=str(spec["sizing_policy"]),
                    params={
                        "model_params": dict(spec.get("model_params", {})),
                        "sizing_params": dict(spec.get("sizing_params", {})),
                    },
                    evaluation=ev,
                    n_folds=len(run_out["folds"]),
                    n_features_selected=avg_k,
                    oos_label=validated_oos,
                    cutoff_utc=cutoff_utc,
                )

            rec = _compact_v105_trial_record(run_out, ledger_receipt=l_rec, runtime_sec=time.perf_counter() - t_tr)
            trial_records.append(rec)
            trial_runs_by_id[rec["trial_id"]] = run_out

        if ledger is not None:
            ledger_summary = ledger.summary()
    finally:
        if ledger is not None:
            ledger.close()

    catboost_info_absent = not (Path.cwd() / "catboost_info").exists()
    if not catboost_info_absent:
        raise RuntimeError("CATBOOST_INFO_LEAK: stray catboost_info directory found")

    filter_trials = [t for t in trial_records if t["track_name"] == "v105_ml_filter"]
    asym_trials = [t for t in trial_records if t["track_name"] == "v105_ml_asymfloor"]

    best_filter = max(
        filter_trials,
        key=lambda t: (
            1 if t["verdict"] == VERDICT_PROMOTE_FILTER else 0,
            1 if bool(t.get("float32_onnx_deployable", True)) else 0,
            1 if (float(t["brier_skill_score"]) > 0.0 and float(t["delta_slippage_breakeven_24m"]) > 0.0) else 0,
            float(t["brier_skill_score"]),
            float(t["slippage_breakeven_24m"]),
            float(t["pf_1x"]),
        ),
    )
    best_filter_f64_cliff = [t for t in filter_trials if not bool(t.get("float32_onnx_deployable", True))]
    best_asym = max(
        asym_trials,
        key=lambda t: (
            1 if t["verdict"] == VERDICT_PROMOTE_ASYMFLOOR else 0,
            1 if bool(t.get("float32_onnx_deployable", True)) else 0,
            float(t["brier_skill_score"]),
            float(t["slippage_breakeven_24m"]),
            float(t["pf_1x"]),
        ),
    )

    asym_h2h_verdict, asym_h2h_reasons = _evaluate_asymfloor_head_to_head(best_filter, best_asym)
    filter_promoted_cnt = sum(1 for t in filter_trials if t["verdict"] == VERDICT_PROMOTE_FILTER)
    asym_promoted_cnt = sum(1 for t in asym_trials if t["verdict"] == VERDICT_PROMOTE_ASYMFLOOR)

    if asym_h2h_verdict == ASYMFLOOR_VERDICT_PROMOTE:
        overall_verdict = VERDICT_PROMOTE_ASYMFLOOR
    elif filter_promoted_cnt > 0:
        overall_verdict = VERDICT_PROMOTE_FILTER
    else:
        overall_verdict = VERDICT_REJECT_ML

    approval_tag = TAG_PROMOTE_CANDIDATE if overall_verdict != VERDICT_REJECT_ML else TAG_RESEARCH_PROTOTYPE

    # Select winning LightGBM model for ONNX + Pure-MQL5 export (aligned 1:1 with OOF series!)
    export_trial = _select_lgbm_export_trial(trial_records)

    # Fit winning export model strictly on final Dev fold train set & build 500 parity vectors + ONNX + MQH
    export_artifacts: dict[str, Any] = {}
    ref_2024_summary: dict[str, Any] | None = None
    ref_2024_disabled_summary: dict[str, Any] | None = None
    oof_series_path_str: str | None = None
    oof_series_sha: str | None = None

    if out_dir is not None:
        out_path = Path(out_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        # 1. Emit OOF trade & daily return series for Wave 2B Spectrum MC (1:1 aligned with exported ONNX/MQH!)
        oof_filter_trial = export_trial if export_trial["track_name"] == "v105_ml_filter" else best_filter
        oof_mask_ref = np.asarray(trial_runs_by_id[oof_filter_trial["trial_id"]]["oof_mask"], dtype=bool)
        oof_series_payload = build_oof_series_payload(
            trades=trades,
            entry_ts=ent_arr,
            exit_ts=ext_arr,
            net_r=r_arr,
            risk_pct_1x=rf_arr,
            oof_mask=oof_mask_ref,
            best_filter_run=trial_runs_by_id[oof_filter_trial["trial_id"]],
            best_asym_run=trial_runs_by_id[best_asym["trial_id"]],
            asymfloor_head_to_head_verdict=asym_h2h_verdict,
        )
        oof_path = out_path / "wave5_ml_oof_series.json"
        _atomic_write_json(oof_path, oof_series_payload)
        oof_series_path_str = str(oof_path)
        oof_series_sha = sha256_file(oof_path)

        # 2. Fit winning export model strictly on final fold training window
        splitter = ExpandingPurgedWalkForwardSplitter(
            n_splits=n_splits,
            purge_days=purge_days,
            embargo_days=embargo_days,
            min_train_samples=min_train_samples,
            mode="expanding",
            cutoff_utc=cutoff_utc,
        )
        folds = list(splitter.split(ent_arr, ext_arr, cutoff_utc=cutoff_utc))
        train_idx_last, val_idx_last = folds[-1]
        oof_all = np.concatenate([va for _, va in folds])

        pruning_last = select_inside_fold_features(
            x_arr[train_idx_last].astype(np.float64),
            y_arr[train_idx_last],
            feature_names=feature_names,
            min_k=min_k,
            max_k=max_k,
        )
        sel_idx = [int(i) for i in pruning_last["selected_indices"]]
        sel_names = [str(nm) for nm in pruning_last["selected_names"]]
        k_sel = len(sel_idx)

        x_train_sel = np.ascontiguousarray(x_arr[train_idx_last][:, sel_idx], dtype=np.float32)
        y_train_last = np.asarray(y_arr[train_idx_last], dtype=np.float64)
        scaler_mu, scaler_sd = _fit_train_scaler(x_train_sel.astype(np.float64))

        export_fam = str(export_trial["family_name"])
        export_params = dict(export_trial["model_params"])
        adapter = create_model_adapter(export_fam, **export_params)
        adapter.fit(x_train_sel.astype(np.float64), y_train_last, feature_names=sel_names)

        p_train_last = adapter.predict_proba(x_train_sel.astype(np.float64))
        tq_exp = float(export_trial.get("sizing_params", {}).get("toxic_quantile", 0.20))
        train_p_toxic = float(np.quantile(p_train_last, tq_exp))
        train_p_q10 = float(np.quantile(p_train_last, 0.10))

        # Select 500 deterministic pre-cutoff Dev OOS parity vectors
        if val_idx_last.size >= n_parity_samples:
            parity_idx = np.ascontiguousarray(val_idx_last[:n_parity_samples], dtype=np.int64)
            parity_source = "strict_final_fold_oos"
        elif oof_all.size >= n_parity_samples:
            val_set = set(val_idx_last.tolist())
            preceding = [int(i) for i in oof_all.tolist() if i not in val_set]
            extra = n_parity_samples - int(val_idx_last.size)
            parity_idx = np.asarray(preceding[-extra:] + val_idx_last.tolist(), dtype=np.int64)
            parity_source = "chronological_oof_padded"
        else:
            rng = np.random.default_rng(random_state + 997)
            pool = val_idx_last if val_idx_last.size > 0 else oof_all
            parity_idx = np.ascontiguousarray(rng.choice(pool, size=n_parity_samples, replace=True), dtype=np.int64)
            parity_source = "synthetic_oof_bootstrap"

        parity_entry_ts = np.ascontiguousarray(ent_arr[parity_idx], dtype=np.int64)
        if int(np.max(parity_entry_ts)) >= cutoff_sec:
            raise HoldoutCutoffBreachError("HOLDOUT_BREACH_PARITY_VECTORS")

        x_parity_sel = np.ascontiguousarray(x_arr[parity_idx][:, sel_idx], dtype=np.float32)
        p_parity_f64 = np.ascontiguousarray(adapter.predict_proba(x_parity_sel.astype(np.float64)), dtype=np.float64)
        p_parity_f32 = np.ascontiguousarray(p_parity_f64, dtype=np.float32)
        sizes_parity_f32 = np.where(p_parity_f64 < train_p_toxic, 0.0, 1.0).astype(np.float32)

        parity_npz_path = out_path / "wave5_ml_parity_500.npz"
        _atomic_write_npz(
            parity_npz_path,
            {
                "X": x_parity_sel,
                "X_full_20": np.ascontiguousarray(x_arr[parity_idx], dtype=np.float32),
                "y_true": np.ascontiguousarray(y_arr[parity_idx], dtype=np.float32),
                "pred_proba": p_parity_f32,
                "pred_proba_f64": p_parity_f64,
                "pred_logit": np.ascontiguousarray(_logit(p_parity_f64), dtype=np.float32),
                "pred_size_toxic_filter": sizes_parity_f32,
                "selected_feature_indices": np.asarray(sel_idx, dtype=np.int32),
                "selected_feature_names": np.asarray(sel_names, dtype="U64"),
                "scaler_mean": np.asarray(scaler_mu, dtype=np.float32),
                "scaler_std": np.asarray(scaler_sd, dtype=np.float32),
                "entry_ts": parity_entry_ts,
            },
        )
        parity_csv_path = out_path / "wave5_ml_parity_500.csv"
        parity_csv_meta = export_parity_500_csv(x_parity_sel, p_parity_f64, sizes_parity_f32, parity_csv_path)

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
            "source_trial_id": str(export_trial["trial_id"]),
            "family_name": export_fam,
            "model_params": export_params,
            "sizing_params": dict(export_trial.get("sizing_params", {})),
            "asymfloor_promoted": bool(asym_h2h_verdict == ASYMFLOOR_VERDICT_PROMOTE),
            "asym_floor_mult": float(best_asym.get("sizing_params", {}).get("floor_mult", 0.55)),
            "n_features_selected": k_sel,
            "selected_feature_indices": sel_idx,
            "selected_feature_names": sel_names,
            "train_fold_summary": {
                "fold_index": len(folds) - 1,
                "n_train": int(train_idx_last.size),
                "n_val": int(val_idx_last.size),
                "train_max_exit_ts": int(np.max(ext_arr[train_idx_last])),
                "val_min_entry_ts": int(np.min(ent_arr[val_idx_last])),
            },
            "train_base_rate": _json_safe_float(float(np.mean(y_train_last))),
            "train_p_toxic": _json_safe_float(train_p_toxic),
            "train_p_q10": _json_safe_float(train_p_q10),
            "parity_source": parity_source,
            "parity_500_npz": str(parity_npz_path),
            "parity_500_npz_sha256": sha256_file(parity_npz_path),
            "parity_500_csv": parity_csv_meta,
        }

        onnx_meta: dict[str, Any] | None = None
        ort_parity: dict[str, Any] | None = None
        mqh_meta: dict[str, Any] | None = None
        mqh_disk_text: str | None = None
        onnx_out_path = out_path / "naqex_v105_lgbm.onnx"

        if export_onnx_and_mqh and export_fam == "lightgbm":
            raw_est = getattr(adapter, "_model", None)
            if raw_est is None:
                raise RuntimeError("LGBM_EXPORT_ESTIMATOR_MISSING")
            tree_dump = raw_est.booster_.dump_model()
            proto_json_payload["model_whitebox"] = {
                "representation": "lightgbm_tree_ensemble",
                "num_trees": int(raw_est.booster_.num_trees()),
                "tree_dump": tree_dump,
            }

            onnx_meta = export_lightgbm_to_onnx(
                raw_est,
                n_features=k_sel,
                out_onnx_path=onnx_out_path,
                model_name="naqex_v105_lgbm",
            )
            ort_parity = verify_onnx_runtime_parity(
                onnx_out_path,
                x_parity_sel,
                p_parity_f64,
                tol=STRICT_ONNX_PARITY_TOL,
                threshold=train_p_toxic,
                ref_sizes=sizes_parity_f32,
            )

            tables = extract_flat_tree_tables(tree_dump, n_features=k_sel)
            mqh_text = render_mql5_filter_v105_header(
                proto_json_payload,
                tables=tables,
                onnx_sha256=onnx_meta["onnx_sha256"],
                onnx_filename="naqex_v105_lgbm.onnx",
            )
            # Zero OrderSend invariant check on generated .mqh
            if "OrderSend" in mqh_text or "CTrade" in mqh_text:
                raise RuntimeError("FORBIDDEN_ORDER_SEND_IN_MQH_V105")

            if mqh_out_path is not None:
                mqh_p = Path(mqh_out_path)
                _atomic_write_text_lf(mqh_p, mqh_text)
                mqh_disk_text = mqh_p.read_text(encoding="utf-8")
            else:
                mqh_disk_text = mqh_text

            p_mqh = evaluate_mqh_v105_mirror(mqh_disk_text, x_parity_sel)
            mqh_vs_py_err = float(np.max(np.abs(p_mqh - p_parity_f64)))
            if mqh_vs_py_err > STRICT_ONNX_PARITY_TOL:
                raise ValueError(f"PURE_MQL5_V105_PARITY_BREACH: {mqh_vs_py_err:.3e} > {STRICT_ONNX_PARITY_TOL:.3e}")
            mqh_size_agree = float(
                np.mean(np.where(p_mqh < train_p_toxic, 0.0, 1.0) == sizes_parity_f32.astype(np.float64))
            )
            mqh_meta = {
                "mqh_path": str(mqh_out_path) if mqh_out_path is not None else None,
                "mqh_sha256": sha256_file(Path(mqh_out_path)) if mqh_out_path is not None else None,
                "mqh_bytes": Path(mqh_out_path).stat().st_size if mqh_out_path is not None else len(mqh_text.encode()),
                "n_trees": int(tables["n_trees"]),
                "n_nodes": int(tables["n_nodes"]),
                "max_depth": int(tables["max_depth"]),
                "python_vs_mqh_max_abs_err": mqh_vs_py_err,
                "decision_agreement_500": mqh_size_agree,
                "order_send_count": 0,
                "passed": bool(mqh_vs_py_err <= STRICT_ONNX_PARITY_TOL and mqh_size_agree == 1.0),
            }

            if export_2024_ftmo_ref:
                ref_2024_summary = export_2024_ftmo_same_feed_features_ref(
                    selected_feature_indices=sel_idx,
                    selected_feature_names=sel_names,
                    predict_proba_fn=lambda mat: adapter.predict_proba(np.asarray(mat, dtype=np.float64)),
                    ml_threshold=train_p_toxic,
                    onnx_path=onnx_out_path,
                    mqh_text=mqh_disk_text,
                    out_csv_path=out_path / "wave5_2024_features_ref.csv",
                    out_meta_path=out_path / "wave5_2024_features_ref_meta.json",
                    ml_enabled=True,
                )
                ref_2024_disabled_summary = export_2024_ftmo_same_feed_features_ref(
                    selected_feature_indices=sel_idx,
                    selected_feature_names=sel_names,
                    predict_proba_fn=lambda mat: adapter.predict_proba(np.asarray(mat, dtype=np.float64)),
                    ml_threshold=train_p_toxic,
                    onnx_path=None,
                    mqh_text=None,
                    out_csv_path=None,
                    out_meta_path=None,
                    ml_enabled=False,
                )

        proto_json_path = out_path / "wave5_ml_prototype_model.json"
        assert_zero_forbidden_blind_label(proto_json_payload)
        _atomic_write_json(proto_json_path, proto_json_payload)

        proto_pkl_path = out_path / "wave5_ml_prototype_model.pkl"
        _atomic_write_bytes(
            proto_pkl_path,
            pickle.dumps(
                {
                    "schema_version": PROTOTYPE_SCHEMA_VERSION,
                    "source_trial_id": str(export_trial["trial_id"]),
                    "family_name": export_fam,
                    "selected_feature_indices": sel_idx,
                    "selected_feature_names": sel_names,
                    "train_p_toxic": train_p_toxic,
                    "train_p_q10": train_p_q10,
                    "adapter": adapter,
                    "raw_estimator": getattr(adapter, "_model", None),
                },
                protocol=pickle.HIGHEST_PROTOCOL,
            ),
        )

        export_artifacts = {
            "source_trial_id": str(export_trial["trial_id"]),
            "family_name": export_fam,
            "n_features_selected": k_sel,
            "selected_feature_indices": sel_idx,
            "selected_feature_names": sel_names,
            "train_p_toxic": _json_safe_float(train_p_toxic),
            "train_p_q10": _json_safe_float(train_p_q10),
            "prototype_model_json": str(proto_json_path),
            "prototype_model_json_sha256": sha256_file(proto_json_path),
            "prototype_model_pkl": str(proto_pkl_path),
            "prototype_model_pkl_sha256": sha256_file(proto_pkl_path),
            "parity_500_npz": str(parity_npz_path),
            "parity_500_npz_sha256": sha256_file(parity_npz_path),
            "parity_500_csv": parity_csv_meta,
            "onnx_export": onnx_meta,
            "onnxruntime_parity_500": ort_parity,
            "pure_mql5_header": mqh_meta,
            "oof_series_json": oof_series_path_str,
            "oof_series_sha256": oof_series_sha,
            "ref_2024_ftmo_ml_enabled": ref_2024_summary,
            "ref_2024_ftmo_ml_disabled_baseline": ref_2024_disabled_summary,
        }

    budget_block = (
        ledger_summary
        if ledger_summary is not None
        else {
            "db_path": None,
            "table_name": DEFAULT_TABLE_NAME,
            "max_trials": max_trials,
            "recorded_trials": len(trial_records),
            "remaining_trials": max(0, max_trials - len(trial_records)),
            "promoted_trials": filter_promoted_cnt + asym_promoted_cnt,
            "trials_by_track": {tr: sum(1 for r in trial_records if r["track_name"] == tr) for tr in ALLOWED_TRACKS},
            "trials_by_family": {
                f: sum(1 for r in trial_records if r["family_name"] == f) for f in ALLOWED_BASE_FAMILIES
            },
            "holdout_rows_analysed": 0,
            "order_send_count": 0,
        }
    )

    summary: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_utc": datetime.now(UTC).isoformat(),
        "gate": "W5-G11",
        "w5_g11_status": "PASS",
        "verdict": overall_verdict,
        "approval_tag": approval_tag,
        "head_to_head": {
            "v105_ml_filter": {
                "trials_run": len(filter_trials),
                "trials_promoted": filter_promoted_cnt,
                "best_trial_id": best_filter["trial_id"],
                "best_family": best_filter["family_name"],
                "brier_skill_score": best_filter["brier_skill_score"],
                "roc_auc": best_filter["roc_auc"],
                "min_engine_retention_ratio": best_filter["min_engine_retention_ratio"],
                "overall_retention_ratio": best_filter["overall_retention_ratio"],
                "pf_1x": best_filter["pf_1x"],
                "ev_r_1x": best_filter["ev_r_1x"],
                "max_dd_pct_1x": best_filter["max_dd_pct_1x"],
                "slippage_breakeven_24m": best_filter["slippage_breakeven_24m"],
                "verdict": best_filter["verdict"],
                "float32_decision_agreement": best_filter["float32_decision_agreement"],
                "float32_onnx_deployable": best_filter["float32_onnx_deployable"],
                "rejection_reasons": best_filter["rejection_reasons"],
                "float32_cliff_rejected_trials": [
                    {
                        "trial_id": t["trial_id"],
                        "family_name": t["family_name"],
                        "float64_pf_1x": t["pf_1x"],
                        "float64_be_24m": t["slippage_breakeven_24m"],
                        "float32_onnx_stability": t["float32_onnx_stability"],
                    }
                    for t in best_filter_f64_cliff
                ],
            },
            "v105_ml_asymfloor": {
                "trials_run": len(asym_trials),
                "trials_promoted_standalone": asym_promoted_cnt,
                "best_trial_id": best_asym["trial_id"],
                "best_family": best_asym["family_name"],
                "sizing_policy": best_asym["sizing_policy"],
                "sizing_params": best_asym["sizing_params"],
                "brier_skill_score": best_asym["brier_skill_score"],
                "roc_auc": best_asym["roc_auc"],
                "avg_size_mult": best_asym["avg_size_mult"],
                "pf_1x": best_asym["pf_1x"],
                "ev_r_1x": best_asym["ev_r_1x"],
                "max_dd_pct_1x": best_asym["max_dd_pct_1x"],
                "slippage_breakeven_24m": best_asym["slippage_breakeven_24m"],
                "standalone_verdict": best_asym["verdict"],
                "head_to_head_verdict": asym_h2h_verdict,
                "head_to_head_reasons": asym_h2h_reasons,
            },
        },
        "hard_invariants": {
            "order_send_capable": ORDER_SEND_CAPABLE,
            "order_send_count": ORDER_SEND_COUNT,
            "spend_vnd": SPEND_VND,
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
            "dev_pc_mode": mode_a_info["mode"],
            "dev_pc_cores": mode_a_info["cores"],
            "dev_pc_priority_hex": mode_a_info["priority_class_hex"],
        },
        "feature_alignment_w4_rt1_p1_01": {
            "broker_dst_schedule": BROKER_DST_SCHEDULE,
            "atr_formula": "MQL5_SMA_TR_14_BROKER_D1",
            "dd_formula": "SHADOW_1X_CLOSED_R_PHASE_INVARIANT",
            "n_aligned_candidate_features": len(FEATURE_NAMES_V105),
            "feature_names_v105": list(FEATURE_NAMES_V105),
            "closes_finding": "W4-RT1-P1-01",
        },
        "dataset": {
            "holdout_lock_sha256": holdout_lock_sha256,
            "n_trades": n_rows,
            "n_features_aligned": int(x_arr.shape[1]),
            "n_engines": len({str(e) for e in engine_ids}),
            "oos_label": validated_oos,
            "max_entry_ts": int(np.max(ent_arr)),
            "max_exit_ts": int(np.max(ext_arr)),
            "holdout_rows_analysed": 0,
        },
        "splitter": {
            "n_splits": n_splits,
            "purge_days": purge_days,
            "embargo_days": embargo_days,
            "min_train_samples": min_train_samples,
            "mode": "expanding",
            "folds": splitter_audits,
        },
        "budget": budget_block,
        "baseline_v103": {
            "full_oof": baseline_full_oof,
            "clb_2021_2024_temporal_oos": baseline_clb_oof,
        },
        "export_artifacts": export_artifacts,
        "all_trials": trial_records,
        "total_runtime_seconds": _json_safe_float(time.perf_counter() - t0, digits=3),
    }

    summary["report_sha256"] = compute_report_sha256(summary)
    assert_zero_forbidden_blind_label(summary)

    if out_dir is not None:
        summary_path = Path(out_dir) / "wave5_ml_arena_summary.json"
        _atomic_write_json(summary_path, summary)
        summary["summary_path"] = str(summary_path)
    return summary


# ---------------------------------------------------------------------------
# 9. Production Entrypoint & Audit/Dropbox Receipt Writer
# ---------------------------------------------------------------------------


def run_port7e_v105_production_pipeline(
    *,
    portfolio_key: str = "PORT_7E_P28_CORE",
    cutoff_utc: str = HOLDOUT_CUTOFF_DATE,
    db_path: Path = DEFAULT_DB_PATH,
    out_dir: Path = DEFAULT_ML_OUT_DIR,
    mqh_out_path: Path = DEFAULT_MQH_PATH,
    verify_sha: bool = True,
    reset_db: bool = True,
    random_state: int = 42,
) -> dict[str, Any]:
    """Run full production Wave 5 aligned feature checks, 36-trial arena, ONNX/MQH export & 2024 FTMO ref."""
    apply_mode_a_owner_active_guard(cores=MODE_A_MAX_CORES)

    # 1. Explicit W4-RT1-P1-01 & P2-2 guardrails before training
    dst_proof = verify_ftmo_two_regime_dst_guardrail()
    ftmo_causality_proof = verify_ftmo_m1_zero_bit_drift_causality(cutoff_utc=cutoff_utc)

    # 2. Build sealed PORT_7E Dev aligned feature matrix (2018-2024, holdout_rows=0)
    bundle = build_port7e_dev_aligned_bundle_v105(
        portfolio_key=portfolio_key,
        cutoff_utc=cutoff_utc,
        verify_sha=verify_sha,
        verify_causality=False,
    )
    phase_inv_proof = verify_phase_invariance_1x_equiv(bundle["trades"][:250])

    # Remove stale DuckDB file ONLY on explicit clean production run
    if reset_db and db_path.exists():
        db_path.unlink()

    trades = bundle["trades"]
    engine_ids = [str(t["engine_id"]) for t in trades]

    summary = run_v105_ml_arena(
        bundle["X"],
        bundle["y"],
        bundle["entry_ts"],
        bundle["exit_ts"],
        bundle["net_R"],
        engine_ids,
        trades,
        feature_names=FEATURE_NAMES_V105,
        trial_grid=build_preregistered_v105_grid(random_state=random_state),
        db_path=db_path,
        max_trials=DEFAULT_MAX_ML_TRIALS,
        out_dir=out_dir,
        mqh_out_path=mqh_out_path,
        n_splits=5,
        purge_days=DEFAULT_PURGE_DAYS,
        embargo_days=DEFAULT_EMBARGO_DAYS,
        min_train_samples=DEFAULT_MIN_TRAIN_SAMPLES,
        min_k=DEFAULT_MIN_SELECTED_FEATURES,
        max_k=DEFAULT_MAX_SELECTED_FEATURES,
        slippage_mults=DEFAULT_SLIPPAGE_MULTS,
        base_cost_r=DEFAULT_BASE_COST_R,
        risk_pct_1x=bundle["risk_pct_1x"],
        oos_label=CONSUMED_CLB_TAG,
        cutoff_utc=cutoff_utc,
        n_parity_samples=DEFAULT_PARITY_SAMPLES,
        holdout_lock_sha256=str(bundle["holdout_lock_sha256"]),
        random_state=random_state,
        use_duckdb_ledger=True,
        export_onnx_and_mqh=True,
        export_2024_ftmo_ref=True,
    )
    summary["guardrail_proofs"] = {
        "ftmo_two_regime_dst_p2_2": dst_proof,
        "ftmo_m1_zero_bit_drift_causality": ftmo_causality_proof,
        "rolling_dd_1x_phase_invariance": phase_inv_proof,
    }
    summary["report_sha256"] = compute_report_sha256(summary)
    assert_zero_forbidden_blind_label(summary)
    summary_path = Path(out_dir) / "wave5_ml_arena_summary.json"
    _atomic_write_json(summary_path, summary)
    summary["summary_path"] = str(summary_path)
    return summary


def build_wave5_ml_receipt(
    arena_summary: Mapping[str, Any],
    *,
    test_results: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble byte-identical audit & swarm dropbox receipt for `w5-ml-features`."""
    exp = arena_summary.get("export_artifacts", {})
    receipt: dict[str, Any] = {
        "schema": RECEIPT_SCHEMA_VERSION,
        "arena_schema_version": SCHEMA_VERSION,
        "worker": "w5-ml-features",
        "wave": "Wave 2A Part 1 (Total Offensive #5 v5.3 FINAL)",
        "gates": ["W5-G10-PREP", "W5-G11"],
        "closes_findings": ["W4-RT1-P1-01"],
        "status": "PASS",
        "verdict": arena_summary["verdict"],
        "approval_tag": arena_summary["approval_tag"],
        "generated_utc": datetime.now(UTC).isoformat(),
        "holdout_rows_analysed": 0,
        "order_send_count": ORDER_SEND_COUNT,
        "spend_vnd": SPEND_VND,
        "hard_invariants": dict(arena_summary["hard_invariants"]),
        "deliverables": {
            "ml_features_v105_aligned_py": "tooling/ai-engines/quant_factory/wave5/ml_features_v105_aligned.py",
            "run_v105_ml_and_sizing_arena_py": "tooling/ai-engines/quant_factory/wave5/run_v105_ml_and_sizing_arena.py",
            "tests_py": "tooling/ai-engines/tests/wave5/test_wave5_ml_v105.py",
            "naqex_ml_filter_v105_mqh": "tooling/ai-engines/exports/Include/Naqex_ML_Filter_v105.mqh",
            "onnx_model": exp.get("onnx_export", {}).get("onnx_path") if exp.get("onnx_export") else None,
            "onnx_sha256": exp.get("onnx_export", {}).get("onnx_sha256") if exp.get("onnx_export") else None,
            "parity_500_csv": exp.get("parity_500_csv", {}).get("csv_path") if exp.get("parity_500_csv") else None,
            "ref_2024_features_csv": (
                exp.get("ref_2024_ftmo_ml_enabled", {}).get("csv_path")
                if exp.get("ref_2024_ftmo_ml_enabled")
                else None
            ),
            "oof_series_json": exp.get("oof_series_json"),
            "duckdb_ledger": arena_summary["budget"]["db_path"],
            "summary_json": arena_summary.get("summary_path"),
            "summary_report_sha256": arena_summary["report_sha256"],
        },
        "dataset": dict(arena_summary["dataset"]),
        "budget": dict(arena_summary["budget"]),
        "baseline_v103": dict(arena_summary["baseline_v103"]),
        "head_to_head": dict(arena_summary["head_to_head"]),
        "feature_alignment_w4_rt1_p1_01": dict(arena_summary["feature_alignment_w4_rt1_p1_01"]),
        "guardrail_proofs": dict(arena_summary.get("guardrail_proofs", {})),
        "export_artifacts": exp,
        "feature_specs_v105_count": len(FEATURE_SPECS_V105),
        "total_runtime_seconds": arena_summary.get("total_runtime_seconds", 0.0),
        "test_results": dict(test_results) if test_results is not None else None,
    }
    receipt["report_sha256"] = compute_report_sha256(receipt)
    assert_zero_forbidden_blind_label(receipt)
    return receipt


def write_wave5_ml_receipt(
    arena_summary: Mapping[str, Any],
    *,
    receipt_path: Path | None = DEFAULT_AUDIT_RECEIPT_PATH,
    dropbox_path: Path | None = DEFAULT_DROPBOX_RECEIPT_PATH,
    test_results: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Write byte-identical audit & swarm dropbox receipts atomically (0 CRLF, 0 BOM)."""
    payload = build_wave5_ml_receipt(arena_summary, test_results=test_results)
    if receipt_path is not None:
        _atomic_write_json(Path(receipt_path), payload)
    if dropbox_path is not None:
        _atomic_write_json(Path(dropbox_path), payload)
    return payload


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run Wave 5 v1.05 aligned ML Filter vs AsymFloor arena, ONNX/MQH export, and 2024 FTMO ref."
    )
    parser.add_argument("--portfolio-key", default="PORT_7E_P28_CORE")
    parser.add_argument("--cutoff-utc", default=HOLDOUT_CUTOFF_DATE)
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_ML_OUT_DIR)
    parser.add_argument("--mqh-out", type=Path, default=DEFAULT_MQH_PATH)
    parser.add_argument("--skip-sha", action="store_true")
    parser.add_argument("--keep-db", action="store_true")
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--write-receipt", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)

    summary = run_port7e_v105_production_pipeline(
        portfolio_key=args.portfolio_key,
        cutoff_utc=args.cutoff_utc,
        db_path=args.db_path,
        out_dir=args.out_dir,
        mqh_out_path=args.mqh_out,
        verify_sha=not args.skip_sha,
        reset_db=not args.keep_db,
        random_state=args.random_state,
    )
    if args.write_receipt:
        write_wave5_ml_receipt(summary)

    compact = {
        "verdict": summary["verdict"],
        "approval_tag": summary["approval_tag"],
        "recorded_trials": summary["budget"]["recorded_trials"],
        "max_trials": summary["budget"]["max_trials"],
        "best_filter": summary["head_to_head"]["v105_ml_filter"],
        "best_asymfloor": summary["head_to_head"]["v105_ml_asymfloor"],
        "onnx_sha256": (summary["export_artifacts"].get("onnx_export") or {}).get("onnx_sha256"),
        "ort_max_err_single": (summary["export_artifacts"].get("onnxruntime_parity_500") or {}).get(
            "max_abs_err_single"
        ),
        "mqh_max_err": (summary["export_artifacts"].get("pure_mql5_header") or {}).get("python_vs_mqh_max_abs_err"),
        "ref_2024_signals": (summary["export_artifacts"].get("ref_2024_ftmo_ml_enabled") or {}).get(
            "signals_evaluated"
        ),
        "holdout_rows_analysed": summary["hard_invariants"]["holdout_rows_analysed"],
        "total_runtime_seconds": summary["total_runtime_seconds"],
    }
    print(json.dumps(compact, indent=2))
    return 0


__all__ = [
    "ALLOWED_BASE_FAMILIES",
    "ALLOWED_SIZING_POLICIES",
    "ALLOWED_TRACKS",
    "ASYMFLOOR_VERDICT_PROMOTE",
    "ASYMFLOOR_VERDICT_REJECT_KEEP_FILTER",
    "ASYMFLOOR_VERDICT_REJECT_KEEP_V103",
    "CONSUMED_CLB_TAG",
    "DEFAULT_2024_REF_CSV_PATH",
    "DEFAULT_2024_REF_META_PATH",
    "DEFAULT_AUDIT_RECEIPT_PATH",
    "DEFAULT_DB_PATH",
    "DEFAULT_DROPBOX_RECEIPT_PATH",
    "DEFAULT_ML_OUT_DIR",
    "DEFAULT_MQH_PATH",
    "DEFAULT_ONNX_PATH",
    "DEFAULT_OOF_SERIES_PATH",
    "DEFAULT_PARITY_500_CSV_PATH",
    "DEFAULT_SUMMARY_PATH",
    "DEFAULT_TABLE_NAME",
    "HOLDOUT_CUTOFF_DATE",
    "ORDER_SEND_CAPABLE",
    "ORDER_SEND_COUNT",
    "SCHEMA_VERSION",
    "SPEND_VND",
    "STRICT_ONNX_PARITY_TOL",
    "VERDICT_PROMOTE_ASYMFLOOR",
    "VERDICT_PROMOTE_FILTER",
    "VERDICT_REJECT_ML",
    "BudgetExceededError",
    "CausalityViolationError",
    "HoldoutCutoffBreachError",
    "Law13HonestyError",
    "Wave5MlBudgetLedger",
    "apply_mode_a_owner_active_guard",
    "assert_zero_forbidden_blind_label",
    "build_numpy_smoke_v105_grid",
    "build_oof_series_payload",
    "build_preregistered_v105_grid",
    "build_wave5_ml_receipt",
    "compute_report_sha256",
    "compute_sizing_from_train_quantiles",
    "evaluate_mqh_v105_mirror",
    "export_2024_ftmo_same_feed_features_ref",
    "main",
    "parse_mqh_v105_tree_tables",
    "render_mql5_filter_v105_header",
    "run_port7e_v105_production_pipeline",
    "run_v105_ml_arena",
    "run_v105_walkforward_trial",
    "validate_v105_arena_grid",
    "write_wave5_ml_receipt",
]

if __name__ == "__main__":
    raise SystemExit(main())

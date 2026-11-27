"""Wave 4 LightGBM -> Pure float32 ONNX (`zipmap=False`) & Pure-MQL5 Tree Fallback Exporter (`W4-G05`).

Exports the promoted Wave 2A LightGBM prototype (`w4_09_lgbm_tf_d2_n60`, 8 strictly causal features,
60 depth-2 trees) into:
  1. Pure `float32` ONNX graph (`zipmap=False`, verified `0` `ZipMap` nodes, dynamic batch dim `N`)
     at `.runtime/offensive4/ml/naqex_v104_lgbm.onnx` (+ portable MT5 `MQL5/Files/` copy).
  2. Exact `onnxruntime` numerical parity verification (`<= 1e-5` max abs error across ALL 500
     Fold-4 OOS golden vectors in `wave4_ml_parity_500.npz`, tested in both batch=500 and batch=1).
  3. Auto-generated, 100% deterministic, zero-dependency Pure-MQL5 Tree Evaluator Fallback +
     `OnnxCreateFromBuffer` / `OnnxSetInputShape` / `OnnxSetOutputShape` / `OnnxRun` wrapper at
     `tooling/ai-engines/exports/Include/Naqex_ML_Filter_v104.mqh`, verified by parsing the actual
     emitted `.mqh` arrays and checking `Python LightGBM == Pure-MQL5 <= 1e-5` (actually `~0.0`).
  4. Golden 500-vector CSV (`wave4_ml_parity_500.csv`) copied to portable MT5 `MQL5/Files/` for
     in-terminal Strategy Tester `Naqex_ML_Parity500_Probe.mq5` verification.

Hard safety invariants (ZERO exceptions):
  - `ORDER_SEND_CAPABLE = False`, `ORDER_SEND_COUNT = 0`, `0 VND`.
  - Holdout `2025+` SEALED (`HOLDOUT_CUTOFF_DATE = "2024-12-31"`, `DEV_CUTOFF_SEC = 1_735_689_600`,
    `holdout_rows_analysed = 0`).
  - ZERO bare Python `assert` statements (100% active under `python -O` / `python -OO`).
  - LAZY IMPORTS ONLY for `onnx`, `onnxmltools`, `skl2onnx`, `onnxruntime`, `lightgbm`, `sklearn`
    so CI `-m "not local_cache"` runs cleanly with zero ML/ONNX packages installed.
  - `Naqex_Master_Prop7E_v103.mq5` stays bit-for-bit untouched (verified via SHA-256).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import pickle
import re
import shutil
import tempfile
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

# ---------------------------------------------------------------------------
# Hard Safety Constants & Canonical Defaults
# ---------------------------------------------------------------------------

SCHEMA_VERSION: str = "naqex-wave4-ml-onnx-exporter-v1"
ORDER_SEND_CAPABLE: bool = False
ORDER_SEND_COUNT: int = 0
HOLDOUT_CUTOFF_DATE: str = "2024-12-31"
DEV_CUTOFF_DATE: str = "2025-01-01"
DEV_CUTOFF_SEC: int = 1_735_689_600  # 2025-01-01T00:00:00Z exclusive ceiling
CONSUMED_CLB_TAG: str = "CONSUMED_DEV_CLB_TEMPORAL_OOS"

PARITY_MAX_ABS_TOL: float = 1e-5
PROB_CLIP_EPS: float = 1e-6
LOGIT_CLAMP_ABS: float = 35.0
EXPECTED_PARITY_ROWS: int = 500

ROOT: Path = Path(__file__).resolve().parents[4]
DEFAULT_ML_DIR: Path = ROOT / ".runtime" / "offensive4" / "ml"
DEFAULT_PORTABLE_ROOT: Path = ROOT / ".runtime" / "ftmo-demo-portable-1515343166"
DEFAULT_PORTABLE_FILES_DIR: Path = DEFAULT_PORTABLE_ROOT / "MQL5" / "Files"
DEFAULT_EXPORTS_DIR: Path = ROOT / "tooling" / "ai-engines" / "exports"
DEFAULT_MQH_PATH: Path = DEFAULT_EXPORTS_DIR / "Include" / "Naqex_ML_Filter_v104.mqh"
DEFAULT_V103_MQ5_PATH: Path = DEFAULT_EXPORTS_DIR / "Naqex_Master_Prop7E_v103.mq5"
V103_EXPECTED_SHA256: str = "e6b1b88be00a8470505c86dd1878664e08ce12d8e45203c05f733825f35c9ef5"

ONNX_MODEL_FILENAME: str = "naqex_v104_lgbm.onnx"
PARITY_CSV_FILENAME: str = "wave4_ml_parity_500.csv"
EXPORT_REPORT_FILENAME: str = "wave4_ml_onnx_export_report.json"

PROTOTYPE_JSON_FILENAME: str = "wave4_ml_prototype_model.json"
PROTOTYPE_PKL_FILENAME: str = "wave4_ml_prototype_model.pkl"
PARITY_NPZ_FILENAME: str = "wave4_ml_parity_500.npz"


# ---------------------------------------------------------------------------
# Fail-Closed Atomic IO, Hashing & Input Guards (ZERO Bare `assert`)
# ---------------------------------------------------------------------------


def sha256_file(path: Path) -> str:
    """Compute hex SHA-256 digest of a file."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65_536), b""):
            h.update(chunk)
    return h.hexdigest()


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


def verify_v103_immutable(
    v103_path: Path = DEFAULT_V103_MQ5_PATH,
    expected_sha256: str = V103_EXPECTED_SHA256,
) -> dict[str, Any]:
    """Fail-closed check guaranteeing `Naqex_Master_Prop7E_v103.mq5` is bit-for-bit untouched."""
    if not v103_path.is_file():
        raise FileNotFoundError(f"IMMUTABLE_MISSING: {v103_path}")
    actual = sha256_file(v103_path)
    if actual.lower() != expected_sha256.lower():
        raise RuntimeError(
            f"IMMUTABLE_BREACH: Naqex_Master_Prop7E_v103.mq5 SHA-256 mismatch "
            f"(actual={actual}, expected={expected_sha256})"
        )
    return {
        "path": str(v103_path),
        "sha256": actual,
        "expected_sha256": expected_sha256,
        "untouched": True,
    }


def validate_feature_matrix(
    raw_x: Any,
    *,
    expected_dim: int | None = None,
    name: str = "X",
) -> np.ndarray:
    """Validate 1D or 2D feature input fail-closed (rejects bool/None/NaN/Inf under `python -O`).

    Always returns a contiguous 2D `float32` array of shape `(n_samples, n_features)`.
    """
    if raw_x is None:
        raise ValueError(f"MISSING_FEATURES [{name}]: got None")
    if isinstance(raw_x, (bool, np.bool_, str, bytes)):
        raise ValueError(f"INVALID_FEATURES [{name}]: scalar {type(raw_x).__name__} rejected")

    if isinstance(raw_x, np.ndarray):
        arr_raw = raw_x
    else:
        arr_raw = np.asarray(raw_x)

    if arr_raw.dtype == np.bool_:
        raise ValueError(f"POISONED_BOOL_INPUT [{name}]: boolean array rejected")
    if arr_raw.dtype == object:
        for idx, item in enumerate(arr_raw.flat):
            if isinstance(item, (bool, np.bool_)):
                raise ValueError(f"POISONED_BOOL_INPUT [{name}[{idx}]]: boolean {item!r} rejected")
            if item is None or isinstance(item, (str, bytes)):
                raise ValueError(f"INVALID_NUMERIC_INPUT [{name}[{idx}]]: got {item!r}")

    try:
        arr_f64 = np.asarray(arr_raw, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"INVALID_NUMERIC_INPUT [{name}]: cannot cast to float") from exc

    if arr_f64.ndim == 1:
        arr_f64 = arr_f64.reshape(1, -1)
    elif arr_f64.ndim != 2:
        raise ValueError(f"INVALID_FEATURE_SHAPE [{name}]: expected 1D or 2D array, got shape {arr_f64.shape}")

    if arr_f64.shape[0] == 0 or arr_f64.shape[1] == 0:
        raise ValueError(f"EMPTY_FEATURE_MATRIX [{name}]: got shape {arr_f64.shape}")

    if expected_dim is not None and arr_f64.shape[1] != int(expected_dim):
        raise ValueError(
            f"FEATURE_DIM_MISMATCH [{name}]: expected {int(expected_dim)} features, got {arr_f64.shape[1]}"
        )

    if not bool(np.all(np.isfinite(arr_f64))):
        raise ValueError(f"NON_FINITE_FEATURE_INPUT [{name}]: NaN or Inf detected (fail-closed)")

    arr_f32 = np.ascontiguousarray(arr_f64, dtype=np.float32)
    if not bool(np.all(np.isfinite(arr_f32))):
        raise ValueError(f"FLOAT32_OVERFLOW_INPUT [{name}]: value overflowed float32 to Inf (fail-closed)")

    return arr_f32


# ---------------------------------------------------------------------------
# Prototype Artifact Loader (Enforces Holdout 2025+ Seal)
# ---------------------------------------------------------------------------


def load_prototype_bundle(ml_dir: Path = DEFAULT_ML_DIR) -> dict[str, Any]:
    """Load Wave 2A prototype JSON + 500-vector parity NPZ while enforcing Holdout 2025+ seal."""
    proto_json_path = ml_dir / PROTOTYPE_JSON_FILENAME
    parity_npz_path = ml_dir / PARITY_NPZ_FILENAME
    proto_pkl_path = ml_dir / PROTOTYPE_PKL_FILENAME

    for req in (proto_json_path, parity_npz_path):
        if not req.is_file():
            raise FileNotFoundError(f"MISSING_PROTOTYPE_ARTIFACT: {req}")

    proto_json = json.loads(proto_json_path.read_text(encoding="utf-8"))
    if int(proto_json.get("holdout_rows_analysed", -1)) != 0:
        raise ValueError(
            f"HOLDOUT_SEAL_BREACH: prototype JSON holdout_rows_analysed={proto_json.get('holdout_rows_analysed')}"
        )
    if str(proto_json.get("holdout_cutoff_date", "")) != HOLDOUT_CUTOFF_DATE:
        raise ValueError(
            f"HOLDOUT_CUTOFF_MISMATCH: expected {HOLDOUT_CUTOFF_DATE}, got {proto_json.get('holdout_cutoff_date')!r}"
        )
    if int(proto_json.get("order_send_count", -1)) != 0:
        raise ValueError("ORDER_SEND_INVARIANT_BREACH: prototype JSON order_send_count != 0")

    n_feat = int(proto_json["n_features_selected"])
    feat_names = [str(f) for f in proto_json["selected_feature_names"]]
    if len(feat_names) != n_feat or n_feat <= 0:
        raise ValueError(f"INVALID_SELECTED_FEATURES: n={n_feat}, names={feat_names}")

    with np.load(parity_npz_path, allow_pickle=False) as z:
        x_f32 = validate_feature_matrix(z["X"], expected_dim=n_feat, name="parity_npz.X")
        p_f32 = np.ascontiguousarray(z["pred_proba"], dtype=np.float32)
        p_f64 = np.ascontiguousarray(z["pred_proba_f64"], dtype=np.float64)
        sizes_f32 = np.ascontiguousarray(z["pred_size_toxic_filter"], dtype=np.float32)
        entry_ts = np.ascontiguousarray(z["entry_ts"], dtype=np.int64)

    if x_f32.shape[0] != EXPECTED_PARITY_ROWS:
        raise ValueError(f"UNEXPECTED_PARITY_ROW_COUNT: expected {EXPECTED_PARITY_ROWS}, got {x_f32.shape[0]}")
    if entry_ts.shape != (x_f32.shape[0],) or int(np.max(entry_ts)) >= DEV_CUTOFF_SEC:
        raise ValueError(
            f"HOLDOUT_TIMESTAMP_BREACH: parity max entry_ts={int(np.max(entry_ts))} >= {DEV_CUTOFF_SEC}"
        )
    if not bool(np.all(np.isfinite(p_f64))) or float(np.min(p_f64)) <= 0.0 or float(np.max(p_f64)) >= 1.0:
        raise ValueError("INVALID_REFERENCE_PROBA: probabilities must be finite and strictly inside (0, 1)")

    return {
        "proto_json_path": proto_json_path,
        "proto_pkl_path": proto_pkl_path,
        "parity_npz_path": parity_npz_path,
        "proto_json": proto_json,
        "X": x_f32,
        "pred_proba_f32": p_f32,
        "pred_proba_f64": p_f64,
        "pred_size_toxic_filter": sizes_f32,
        "entry_ts": entry_ts,
        "n_features": n_feat,
        "feature_names": feat_names,
    }


# ---------------------------------------------------------------------------
# Pure-Python White-Box Tree Table Extraction & Evaluator (Zero ML Deps!)
# ---------------------------------------------------------------------------


def extract_flat_tree_tables(tree_dump: Mapping[str, Any], *, n_features: int) -> dict[str, Any]:
    """Flatten LightGBM `dump_model()` binary trees into deterministic index tables for MQL5.

    Validates every split node fail-closed (`decision_type == '<='`, finite thresholds/leaves,
    valid feature indices in `[0, n_features)`).
    """
    tree_info = tree_dump.get("tree_info")
    if not isinstance(tree_info, Sequence) or len(tree_info) == 0:
        raise ValueError("INVALID_TREE_DUMP: tree_info missing or empty")

    tree_roots: list[int] = []
    node_feat: list[int] = []
    node_left: list[int] = []
    node_right: list[int] = []
    node_thresh: list[float] = []
    node_leaf: list[float] = []
    max_depth_seen = 0

    def _visit(node: Mapping[str, Any], depth: int) -> int:
        nonlocal max_depth_seen
        if depth > max_depth_seen:
            max_depth_seen = depth
        if depth > 30:
            raise ValueError(f"TREE_DEPTH_EXCEEDS_SAFE_CAP: depth={depth}")

        idx = len(node_feat)
        if "leaf_value" in node:
            lv = float(node["leaf_value"])
            if not math.isfinite(lv):
                raise ValueError(f"NON_FINITE_LEAF_VALUE: {lv!r}")
            node_feat.append(-1)
            node_left.append(-1)
            node_right.append(-1)
            node_thresh.append(0.0)
            node_leaf.append(lv)
            return idx

        dt = str(node.get("decision_type", ""))
        if dt != "<=":
            raise ValueError(f"UNSUPPORTED_DECISION_TYPE: expected '<=', got {dt!r}")
        feat_idx = int(node["split_feature"])
        if feat_idx < 0 or feat_idx >= n_features:
            raise ValueError(f"SPLIT_FEATURE_OUT_OF_RANGE: {feat_idx} not in [0, {n_features})")
        thr = float(node["threshold"])
        if not math.isfinite(thr):
            raise ValueError(f"NON_FINITE_SPLIT_THRESHOLD: {thr!r}")

        # Reserve slot before recursing so parent index is known immediately
        node_feat.append(feat_idx)
        node_left.append(-1)
        node_right.append(-1)
        node_thresh.append(thr)
        node_leaf.append(0.0)

        l_idx = _visit(node["left_child"], depth + 1)
        r_idx = _visit(node["right_child"], depth + 1)
        node_left[idx] = l_idx
        node_right[idx] = r_idx
        return idx

    for t_entry in tree_info:
        struct = t_entry.get("tree_structure")
        if not isinstance(struct, Mapping):
            raise ValueError("INVALID_TREE_ENTRY: missing tree_structure")
        root_idx = _visit(struct, 0)
        tree_roots.append(root_idx)

    return {
        "n_trees": len(tree_roots),
        "n_nodes": len(node_feat),
        "n_features": int(n_features),
        "max_depth": int(max_depth_seen),
        "tree_roots": tree_roots,
        "node_feat": node_feat,
        "node_left": node_left,
        "node_right": node_right,
        "node_thresh": node_thresh,
        "node_leaf": node_leaf,
    }


def evaluate_flat_trees(
    tables: Mapping[str, Any],
    raw_x: Any,
    *,
    prob_clip: float = PROB_CLIP_EPS,
) -> np.ndarray:
    """Evaluate flattened tree tables identically to `CNaqexMLFilterV104::PredictPureMql5`."""
    n_features = int(tables["n_features"])
    x_f32 = validate_feature_matrix(raw_x, expected_dim=n_features, name="X")
    x_f64 = x_f32.astype(np.float64)

    tree_roots: Sequence[int] = tables["tree_roots"]
    node_feat: Sequence[int] = tables["node_feat"]
    node_left: Sequence[int] = tables["node_left"]
    node_right: Sequence[int] = tables["node_right"]
    node_thresh: Sequence[float] = tables["node_thresh"]
    node_leaf: Sequence[float] = tables["node_leaf"]

    n_rows = x_f64.shape[0]
    out_probs = np.empty(n_rows, dtype=np.float64)

    for i in range(n_rows):
        row = x_f64[i]
        raw_sum = 0.0
        for root in tree_roots:
            idx = int(root)
            steps = 0
            while True:
                f = int(node_feat[idx])
                if f < 0:
                    raw_sum += float(node_leaf[idx])
                    break
                steps += 1
                if steps > 32:
                    raise RuntimeError("TREE_TRAVERSAL_STEP_LIMIT_EXCEEDED")
                idx = int(node_left[idx]) if float(row[f]) <= float(node_thresh[idx]) else int(node_right[idx])
        clamped = max(-LOGIT_CLAMP_ABS, min(LOGIT_CLAMP_ABS, raw_sum))
        p = 1.0 / (1.0 + math.exp(-clamped))
        out_probs[i] = max(prob_clip, min(1.0 - prob_clip, p))

    return out_probs


# ---------------------------------------------------------------------------
# Pure-MQL5 Tree Fallback + OnnxRun Header Generator (`Naqex_ML_Filter_v104.mqh`)
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


def render_mql5_filter_header(
    proto_json: Mapping[str, Any],
    *,
    tables: Mapping[str, Any],
    onnx_sha256: str,
    onnx_filename: str = ONNX_MODEL_FILENAME,
) -> str:
    """Generate `Naqex_ML_Filter_v104.mqh` with OnnxCreateFromBuffer + exact pure-MQL5 tree fallback."""
    n_feat = int(tables["n_features"])
    n_trees = int(tables["n_trees"])
    n_nodes = int(tables["n_nodes"])
    feat_names = [str(f) for f in proto_json["selected_feature_names"]]
    source_trial = str(proto_json.get("source_trial_id", "w4_09_lgbm_tf_d2_n60"))
    approval_tag = str(proto_json.get("approval_tag", "PROMOTE_V104_ML_PENDING_W4G05_ONNX_PARITY"))
    threshold = float(proto_json.get("train_p_toxic_q20", 0.457952))
    if not math.isfinite(threshold) or not (0.0 < threshold < 1.0):
        raise ValueError(f"INVALID_ML_THRESHOLD: {threshold!r}")

    feat_doc_lines = "\n".join(f"//   [{idx}] {nm}" for idx, nm in enumerate(feat_names))

    roots_block = _format_mql5_int_array(tables["tree_roots"], per_line=15)
    feat_block = _format_mql5_int_array(tables["node_feat"], per_line=16)
    left_block = _format_mql5_int_array(tables["node_left"], per_line=16)
    right_block = _format_mql5_int_array(tables["node_right"], per_line=16)
    thresh_block = _format_mql5_double_array(tables["node_thresh"], per_line=6)
    leaf_block = _format_mql5_double_array(tables["node_leaf"], per_line=6)

    header = f"""//+------------------------------------------------------------------+
//| Naqex_ML_Filter_v104.mqh (Auto-generated by ml_onnx_exporter.py) |
//| Wave 4 W4-G05: LightGBM ONNX + Deterministic Pure-MQL5 Fallback  |
//|                                                                  |
//| Source Trial : {source_trial}
//| Approval Tag : {approval_tag}
//| ONNX File    : {onnx_filename} (zipmap=False, 0 ZipMap nodes)
//| ONNX SHA-256 : {onnx_sha256}
//| Trees / Nodes: {n_trees} depth-{int(tables["max_depth"])} trees ({n_nodes} total nodes)
//| Threshold    : {threshold:.6f} (train Fold-4 q20 toxic filter)
//|                                                                  |
//| Exact Causal Feature Order (strictly closed past bars ONLY):     |
{feat_doc_lines}
//|                                                                  |
//| PURE INFERENCE ONLY: contains ZERO CTrade / OrderSend calls.     |
//| Fail-closed on NaN/Inf/wrong-dim features and ONNX-only errors.  |
//+------------------------------------------------------------------+
#ifndef NAQEX_ML_FILTER_V104_MQH
#define NAQEX_ML_FILTER_V104_MQH

#define NAQEX_V104_ML_N_FEATURES        {n_feat}
#define NAQEX_V104_ML_N_TREES           {n_trees}
#define NAQEX_V104_ML_N_NODES           {n_nodes}
#define NAQEX_V104_ML_DEFAULT_THRESHOLD {threshold:.6f}
#define NAQEX_V104_ML_PROB_CLIP         1e-6
#define NAQEX_V104_ML_LOGIT_CLAMP       35.0
#define NAQEX_V104_ML_MODEL_ID          "{source_trial}"
#define NAQEX_V104_ML_ONNX_FILE_DEFAULT "{onnx_filename}"
#define NAQEX_V104_ML_ONNX_SHA256       "{onnx_sha256}"

enum ENUM_NAQEX_ML_MODE
{{
   ONNX_OR_PURE_MQL5_FALLBACK = 0, // Primary OnnxRun with automatic exact Pure-MQL5 tree fallback
   ONNX_ONLY_FAIL_CLOSED      = 1, // Require OnnxRun; fail-closed if ONNX unavailable
   PURE_MQL5_TREE_ONLY        = 2  // Deterministic zero-dependency Pure-MQL5 tree evaluator only
}};

//--- Exact LightGBM {source_trial} flattened tree tables ({n_trees} trees, {n_nodes} nodes)
static const int g_v104TreeRoots[NAQEX_V104_ML_N_TREES] =
{{
{roots_block}
}};

static const int g_v104NodeFeat[NAQEX_V104_ML_N_NODES] =
{{
{feat_block}
}};

static const int g_v104NodeLeft[NAQEX_V104_ML_N_NODES] =
{{
{left_block}
}};

static const int g_v104NodeRight[NAQEX_V104_ML_N_NODES] =
{{
{right_block}
}};

static const double g_v104NodeThresh[NAQEX_V104_ML_N_NODES] =
{{
{thresh_block}
}};

static const double g_v104NodeLeaf[NAQEX_V104_ML_N_NODES] =
{{
{leaf_block}
}};

class CNaqexMLFilterV104
{{
private:
   long              m_onnxHandle;
   bool              m_onnxReady;
   ENUM_NAQEX_ML_MODE m_mode;
   double            m_threshold;
   string            m_lastBackend;
   int               m_lastOnnxError;
   long              m_onnxCalls;
   long              m_pureCalls;
   long              m_fallbackCalls;
   long              m_passedCount;
   long              m_blockedCount;
   long              m_invalidRejectedCount;

   void ReleaseOnnxHandle()
   {{
      if(m_onnxHandle != INVALID_HANDLE)
      {{
         OnnxRelease(m_onnxHandle);
         m_onnxHandle = INVALID_HANDLE;
      }}
      m_onnxReady = false;
   }}

public:
   CNaqexMLFilterV104()
   {{
      m_onnxHandle           = INVALID_HANDLE;
      m_onnxReady            = false;
      m_mode                 = ONNX_OR_PURE_MQL5_FALLBACK;
      m_threshold            = NAQEX_V104_ML_DEFAULT_THRESHOLD;
      m_lastBackend          = "UNINITIALIZED";
      m_lastOnnxError        = 0;
      m_onnxCalls            = 0;
      m_pureCalls            = 0;
      m_fallbackCalls        = 0;
      m_passedCount          = 0;
      m_blockedCount         = 0;
      m_invalidRejectedCount = 0;
   }}

   ~CNaqexMLFilterV104()
   {{
      Deinit();
   }}

   void Deinit()
   {{
      ReleaseOnnxHandle();
   }}

   static bool ValidateFeatures(const double &feat[])
   {{
      if(ArraySize(feat) < NAQEX_V104_ML_N_FEATURES)
         return false;
      for(int j = 0; j < NAQEX_V104_ML_N_FEATURES; j++)
      {{
         if(!MathIsValidNumber(feat[j]))
            return false;
      }}
      return true;
   }}

   static double EvaluatePureMql5RawLogit(const double &feat[])
   {{
      double rawSum = 0.0;
      for(int t = 0; t < NAQEX_V104_ML_N_TREES; t++)
      {{
         int idx = g_v104TreeRoots[t];
         for(int step = 0; step < 32; step++)
         {{
            int f = g_v104NodeFeat[idx];
            if(f < 0)
            {{
               rawSum += g_v104NodeLeaf[idx];
               break;
            }}
            idx = (feat[f] <= g_v104NodeThresh[idx]) ? g_v104NodeLeft[idx] : g_v104NodeRight[idx];
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
      if(rawLogit > NAQEX_V104_ML_LOGIT_CLAMP)
         rawLogit = NAQEX_V104_ML_LOGIT_CLAMP;
      else if(rawLogit < -NAQEX_V104_ML_LOGIT_CLAMP)
         rawLogit = -NAQEX_V104_ML_LOGIT_CLAMP;
      double p = 1.0 / (1.0 + MathExp(-rawLogit));
      if(!MathIsValidNumber(p))
         return false;
      if(p < NAQEX_V104_ML_PROB_CLIP)
         p = NAQEX_V104_ML_PROB_CLIP;
      else if(p > 1.0 - NAQEX_V104_ML_PROB_CLIP)
         p = 1.0 - NAQEX_V104_ML_PROB_CLIP;
      outProb = p;
      return true;
   }}

   bool InitFromBuffer(const uchar &modelBuf[],
                       const ENUM_NAQEX_ML_MODE mode = ONNX_OR_PURE_MQL5_FALLBACK,
                       const double threshold = NAQEX_V104_ML_DEFAULT_THRESHOLD)
   {{
      ReleaseOnnxHandle();
      m_mode          = mode;
      m_threshold     = threshold;
      m_lastOnnxError = 0;

      if(!MathIsValidNumber(threshold) || threshold <= 0.0 || threshold >= 1.0)
      {{
         m_lastBackend = "INVALID_THRESHOLD";
         PrintFormat("[ML-V104-ERR] Invalid threshold=%.6f (must be strictly inside (0,1))", threshold);
         return false;
      }}

      if(mode == PURE_MQL5_TREE_ONLY)
      {{
         m_lastBackend = "PURE_MQL5";
         return true;
      }}

      if(ArraySize(modelBuf) <= 0)
      {{
         m_lastOnnxError = -101;
         m_lastBackend   = (mode == ONNX_OR_PURE_MQL5_FALLBACK) ? "FALLBACK_PURE_MQL5" : "ONNX_BUFFER_EMPTY";
         PrintFormat("[ML-V104-WARN] Empty ONNX buffer; fallback_allowed=%s",
                     (mode == ONNX_OR_PURE_MQL5_FALLBACK) ? "true" : "false");
         return (mode == ONNX_OR_PURE_MQL5_FALLBACK);
      }}

      ResetLastError();
      long h = OnnxCreateFromBuffer(modelBuf, ONNX_USE_CPU_ONLY);
      if(h == INVALID_HANDLE)
      {{
         m_lastOnnxError = GetLastError();
         m_lastBackend   = (mode == ONNX_OR_PURE_MQL5_FALLBACK) ? "FALLBACK_PURE_MQL5" : "ONNX_CREATE_FAILED";
         PrintFormat("[ML-V104-WARN] OnnxCreateFromBuffer failed err=%d; fallback_allowed=%s",
                     m_lastOnnxError, (mode == ONNX_OR_PURE_MQL5_FALLBACK) ? "true" : "false");
         return (mode == ONNX_OR_PURE_MQL5_FALLBACK);
      }}

      const ulong inShape[]   = {{1, NAQEX_V104_ML_N_FEATURES}};
      const ulong out0Shape[] = {{1}};
      const ulong out1Shape[] = {{1, 2}};

      ResetLastError();
      if(!OnnxSetInputShape(h, 0, inShape) ||
         !OnnxSetOutputShape(h, 0, out0Shape) ||
         !OnnxSetOutputShape(h, 1, out1Shape))
      {{
         m_lastOnnxError = GetLastError();
         OnnxRelease(h);
         m_lastBackend   = (mode == ONNX_OR_PURE_MQL5_FALLBACK) ? "FALLBACK_PURE_MQL5" : "ONNX_SHAPE_FAILED";
         PrintFormat("[ML-V104-WARN] OnnxSetInput/OutputShape failed err=%d; fallback_allowed=%s",
                     m_lastOnnxError, (mode == ONNX_OR_PURE_MQL5_FALLBACK) ? "true" : "false");
         return (mode == ONNX_OR_PURE_MQL5_FALLBACK);
      }}

      m_onnxHandle  = h;
      m_onnxReady   = true;
      m_lastBackend = "ONNX";
      return true;
   }}

   bool InitFromFile(const string onnxFile = NAQEX_V104_ML_ONNX_FILE_DEFAULT,
                     const ENUM_NAQEX_ML_MODE mode = ONNX_OR_PURE_MQL5_FALLBACK,
                     const double threshold = NAQEX_V104_ML_DEFAULT_THRESHOLD)
   {{
      ReleaseOnnxHandle();
      m_mode          = mode;
      m_threshold     = threshold;
      m_lastOnnxError = 0;

      if(!MathIsValidNumber(threshold) || threshold <= 0.0 || threshold >= 1.0)
      {{
         m_lastBackend = "INVALID_THRESHOLD";
         PrintFormat("[ML-V104-ERR] Invalid threshold=%.6f (must be strictly inside (0,1))", threshold);
         return false;
      }}

      if(mode == PURE_MQL5_TREE_ONLY)
      {{
         m_lastBackend = "PURE_MQL5";
         return true;
      }}

      ResetLastError();
      int fh = FileOpen(onnxFile, FILE_READ | FILE_BIN | FILE_SHARE_READ);
      if(fh == INVALID_HANDLE)
      {{
         m_lastOnnxError = GetLastError();
         m_lastBackend   = (mode == ONNX_OR_PURE_MQL5_FALLBACK) ? "FALLBACK_PURE_MQL5" : "ONNX_FILE_MISSING";
         PrintFormat("[ML-V104-WARN] Could not open ONNX file '%s' err=%d; fallback_allowed=%s",
                     onnxFile, m_lastOnnxError, (mode == ONNX_OR_PURE_MQL5_FALLBACK) ? "true" : "false");
         return (mode == ONNX_OR_PURE_MQL5_FALLBACK);
      }}

      ulong fsize = FileSize(fh);
      uchar buf[];
      if(fsize == 0 || fsize > 16777216)
      {{
         FileClose(fh);
         m_lastOnnxError = -102;
         m_lastBackend   = (mode == ONNX_OR_PURE_MQL5_FALLBACK) ? "FALLBACK_PURE_MQL5" : "ONNX_FILE_BAD_SIZE";
         return (mode == ONNX_OR_PURE_MQL5_FALLBACK);
      }}
      ArrayResize(buf, (int)fsize);
      uint nRead = FileReadArray(fh, buf, 0, (int)fsize);
      FileClose(fh);
      if(nRead != (uint)fsize)
      {{
         m_lastOnnxError = GetLastError();
         m_lastBackend   = (mode == ONNX_OR_PURE_MQL5_FALLBACK) ? "FALLBACK_PURE_MQL5" : "ONNX_FILE_READ_SHORT";
         return (mode == ONNX_OR_PURE_MQL5_FALLBACK);
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

      float xIn[1][NAQEX_V104_ML_N_FEATURES];
      for(int j = 0; j < NAQEX_V104_ML_N_FEATURES; j++)
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
      if(p1 < NAQEX_V104_ML_PROB_CLIP)
         p1 = NAQEX_V104_ML_PROB_CLIP;
      else if(p1 > 1.0 - NAQEX_V104_ML_PROB_CLIP)
         p1 = 1.0 - NAQEX_V104_ML_PROB_CLIP;

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

      if(m_mode == PURE_MQL5_TREE_ONLY)
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

      if(m_mode == ONNX_ONLY_FAIL_CLOSED)
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

#endif // NAQEX_ML_FILTER_V104_MQH
"""
    return header


def parse_mqh_tree_tables(mqh_text: str) -> dict[str, Any]:
    """Parse emitted C/MQL5 tree arrays directly from `Naqex_ML_Filter_v104.mqh` source text.

    Used to prove the ACTUAL serialized `.mqh` file evaluates identically to Python LightGBM.
    """
    m_feat = re.search(r"#define\s+NAQEX_V104_ML_N_FEATURES\s+(\d+)", mqh_text)
    m_trees = re.search(r"#define\s+NAQEX_V104_ML_N_TREES\s+(\d+)", mqh_text)
    m_nodes = re.search(r"#define\s+NAQEX_V104_ML_N_NODES\s+(\d+)", mqh_text)
    if not (m_feat and m_trees and m_nodes):
        raise ValueError("INVALID_MQH_HEADER: missing NAQEX_V104_ML_N_* macros")

    n_feat = int(m_feat.group(1))
    n_trees = int(m_trees.group(1))
    n_nodes = int(m_nodes.group(1))

    def _extract_array(name: str, *, as_float: bool) -> list[Any]:
        pat = re.compile(rf"static\s+const\s+\w+\s+{re.escape(name)}\s*\[[^\]]+\]\s*=\s*\{{(.*?)\}}\s*;", re.S)
        m = pat.search(mqh_text)
        if not m:
            raise ValueError(f"INVALID_MQH_HEADER: missing array {name}")
        tokens = [tok.strip() for tok in m.group(1).split(",") if tok.strip()]
        return [float(tok) if as_float else int(tok) for tok in tokens]

    tree_roots = _extract_array("g_v104TreeRoots", as_float=False)
    node_feat = _extract_array("g_v104NodeFeat", as_float=False)
    node_left = _extract_array("g_v104NodeLeft", as_float=False)
    node_right = _extract_array("g_v104NodeRight", as_float=False)
    node_thresh = _extract_array("g_v104NodeThresh", as_float=True)
    node_leaf = _extract_array("g_v104NodeLeaf", as_float=True)

    if len(tree_roots) != n_trees:
        raise ValueError(f"MQH_TREE_COUNT_MISMATCH: {len(tree_roots)} != {n_trees}")
    for arr_nm, arr_val in (
        ("g_v104NodeFeat", node_feat),
        ("g_v104NodeLeft", node_left),
        ("g_v104NodeRight", node_right),
        ("g_v104NodeThresh", node_thresh),
        ("g_v104NodeLeaf", node_leaf),
    ):
        if len(arr_val) != n_nodes:
            raise ValueError(f"MQH_NODE_COUNT_MISMATCH [{arr_nm}]: {len(arr_val)} != {n_nodes}")

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


def evaluate_mqh_source_python_mirror(mqh_text: str, raw_x: Any) -> np.ndarray:
    """Parse a generated `.mqh` source string and evaluate its embedded trees on `raw_x`."""
    tables = parse_mqh_tree_tables(mqh_text)
    return evaluate_flat_trees(tables, raw_x)


# ---------------------------------------------------------------------------
# Golden 500-Vector CSV Exporter (Exact Float32 Round-Trip for MT5 Tester)
# ---------------------------------------------------------------------------


def export_parity_500_csv(
    x_f32: np.ndarray,
    ref_proba_f64: np.ndarray,
    ref_sizes_f32: np.ndarray,
    out_csv_path: Path,
) -> dict[str, Any]:
    """Export 500 golden float32 parity vectors + reference probabilities to CSV for MT5 Probe EA."""
    x_valid = validate_feature_matrix(x_f32, name="parity_csv.X")
    n_rows, n_feat = x_valid.shape
    if ref_proba_f64.shape != (n_rows,) or ref_sizes_f32.shape != (n_rows,):
        raise ValueError("PARITY_CSV_LENGTH_MISMATCH")

    header_cols = ["row_idx", *[f"f{j}" for j in range(n_feat)], "ref_proba", "ref_size"]
    lines = [",".join(header_cols)]
    for i in range(n_rows):
        feat_strs = [f"{float(x_valid[i, j]):.9g}" for j in range(n_feat)]
        lines.append(f"{i},{','.join(feat_strs)},{float(ref_proba_f64[i]):.12f},{float(ref_sizes_f32[i]):.1f}")
    csv_text = "\n".join(lines) + "\n"
    _atomic_write_text_lf(out_csv_path, csv_text)

    # Verify exact float32 round-trip fidelity (zero precision loss in CSV serialization!)
    parsed_rows = [ln.split(",") for ln in csv_text.splitlines()[1:] if ln.strip()]
    if len(parsed_rows) != n_rows:
        raise ValueError(f"PARITY_CSV_ROW_COUNT_MISMATCH: {len(parsed_rows)} != {n_rows}")
    roundtrip_x = np.array([[float(r[1 + j]) for j in range(n_feat)] for r in parsed_rows], dtype=np.float32)
    max_rt_err = float(np.max(np.abs(roundtrip_x - x_valid)))
    if max_rt_err > 0.0:
        raise ValueError(f"PARITY_CSV_FLOAT32_ROUNDTRIP_DRIFT: max_err={max_rt_err}")

    return {
        "csv_path": str(out_csv_path),
        "csv_sha256": sha256_file(out_csv_path),
        "csv_bytes": out_csv_path.stat().st_size,
        "rows": n_rows,
        "n_features": n_feat,
        "float32_roundtrip_max_abs_err": max_rt_err,
    }


# ---------------------------------------------------------------------------
# Lazy-Import ONNX Exporter (`zipmap=False`) & `onnxruntime` Parity Verifier
# ---------------------------------------------------------------------------


def export_lightgbm_to_onnx(
    estimator: Any,
    *,
    n_features: int,
    out_onnx_path: Path,
    model_name: str = "naqex_v104_lgbm",
) -> dict[str, Any]:
    """Export a fitted LightGBM binary classifier to pure `float32` ONNX with `zipmap=False`.

    LAZY IMPORTS ONLY for `onnx` and `onnxmltools`.
    Verifies `0` `ZipMap` nodes in `ModelProto.graph.node` and passes `onnx.checker.check_model`.
    """
    import onnx  # Lazy import ONLY
    import onnxmltools  # Lazy import ONLY
    from onnxmltools.convert.common.data_types import FloatTensorType  # Lazy import ONLY

    if n_features <= 0:
        raise ValueError(f"INVALID_N_FEATURES: {n_features}")

    initial_types = [("float_input", FloatTensorType([None, int(n_features)]))]
    # onnxmltools.convert_lightgbm accepts zipmap=False; fall back to skl2onnx options if needed.
    model_proto = onnxmltools.convert_lightgbm(
        estimator,
        name=model_name,
        initial_types=initial_types,
        zipmap=False,
    )

    # Normalize dynamic batch axis dim[0] = "N" across input & both outputs (prevents ORT batch-size warning)
    for tensor_info in (
        model_proto.graph.input[0],
        model_proto.graph.output[0],
        model_proto.graph.output[1],
    ):
        if len(tensor_info.type.tensor_type.shape.dim) > 0:
            d0 = tensor_info.type.tensor_type.shape.dim[0]
            d0.ClearField("dim_value")
            d0.dim_param = "N"

    zipmap_nodes = [n.name or n.op_type for n in model_proto.graph.node if n.op_type == "ZipMap"]
    if zipmap_nodes:
        raise RuntimeError(f"ZIPMAP_FORBIDDEN_NODE_DETECTED: found {len(zipmap_nodes)} ZipMap node(s)")

    onnx.checker.check_model(model_proto)
    serialized = model_proto.SerializeToString()
    _atomic_write_bytes(out_onnx_path, serialized)

    return {
        "onnx_path": str(out_onnx_path),
        "onnx_sha256": sha256_file(out_onnx_path),
        "onnx_bytes": len(serialized),
        "ir_version": int(model_proto.ir_version),
        "opset_imports": [(str(op.domain), int(op.version)) for op in model_proto.opset_import],
        "input_name": str(model_proto.graph.input[0].name),
        "output_names": [str(o.name) for o in model_proto.graph.output],
        "node_op_types": [str(n.op_type) for n in model_proto.graph.node],
        "zipmap_node_count": len(zipmap_nodes),
    }


def verify_onnx_runtime_parity(
    onnx_path: Path,
    raw_x: Any,
    ref_proba: np.ndarray,
    *,
    tol: float = PARITY_MAX_ABS_TOL,
    threshold: float | None = None,
    ref_sizes: np.ndarray | None = None,
) -> dict[str, Any]:
    """Verify `onnxruntime` CPU inference matches reference LightGBM probabilities `<= tol`.

    Checks BOTH full batch (`(N, k)`) AND single-sample (`(1, k)`) execution matching MT5 `OnnxRun`,
    plus re-verifies `0` `ZipMap` nodes on disk. LAZY IMPORTS ONLY.
    """
    import onnx  # Lazy import ONLY
    import onnxruntime as ort  # Lazy import ONLY

    if not onnx_path.is_file():
        raise FileNotFoundError(f"ONNX_MODEL_MISSING: {onnx_path}")

    model_proto = onnx.load(str(onnx_path))
    onnx.checker.check_model(model_proto)
    zipmap_count = sum(1 for n in model_proto.graph.node if n.op_type == "ZipMap")
    if zipmap_count != 0:
        raise RuntimeError(f"ZIPMAP_FORBIDDEN_NODE_DETECTED: {zipmap_count} ZipMap nodes in {onnx_path}")

    in_info = model_proto.graph.input[0]
    expected_dim = int(in_info.type.tensor_type.shape.dim[1].dim_value)
    x_f32 = validate_feature_matrix(raw_x, expected_dim=expected_dim, name="onnx_verify.X")
    ref = np.asarray(ref_proba, dtype=np.float64)
    if ref.shape != (x_f32.shape[0],):
        raise ValueError(f"REF_PROBA_SHAPE_MISMATCH: expected ({x_f32.shape[0]},), got {ref.shape}")

    sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    in_name = sess.get_inputs()[0].name

    # 1. Full batch inference
    outs_batch = sess.run(None, {in_name: x_f32})
    if len(outs_batch) < 2:
        raise RuntimeError(f"UNEXPECTED_ONNX_OUTPUT_COUNT: expected >= 2, got {len(outs_batch)}")
    probs_batch = np.asarray(outs_batch[1], dtype=np.float64)
    if probs_batch.ndim != 2 or probs_batch.shape != (x_f32.shape[0], 2):
        raise RuntimeError(f"UNEXPECTED_PROBS_SHAPE: got {probs_batch.shape}, expected ({x_f32.shape[0]}, 2)")
    if not bool(np.all(np.isfinite(probs_batch))):
        raise RuntimeError("NON_FINITE_ONNX_OUTPUT: NaN/Inf emitted by onnxruntime")

    p1_batch = probs_batch[:, 1]
    abs_err_batch = np.abs(p1_batch - ref)
    max_err_batch = float(np.max(abs_err_batch))
    mean_err_batch = float(np.mean(abs_err_batch))
    p99_err_batch = float(np.percentile(abs_err_batch, 99.0))

    # 2. Single-sample (batch=1) inference across ALL rows (exact MT5 OnnxRun execution mode)
    p1_single = np.empty(x_f32.shape[0], dtype=np.float64)
    for i in range(x_f32.shape[0]):
        out_i = sess.run(None, {in_name: x_f32[i : i + 1]})
        p1_single[i] = float(out_i[1][0, 1])

    max_err_single = float(np.max(np.abs(p1_single - ref)))
    max_err_batch_vs_single = float(np.max(np.abs(p1_batch - p1_single)))

    if max_err_batch > tol or max_err_single > tol:
        raise ValueError(
            f"ONNX_PARITY_TOLERANCE_BREACH: max_err_batch={max_err_batch:.3e}, "
            f"max_err_single={max_err_single:.3e} > tol={tol:.3e}"
        )

    size_agreement: float | None = None
    if threshold is not None and ref_sizes is not None:
        pred_sizes = np.where(p1_single < float(threshold), 0.0, 1.0)
        size_agreement = float(np.mean(pred_sizes == np.asarray(ref_sizes, dtype=np.float64)))

    return {
        "passed": True,
        "n_samples": int(x_f32.shape[0]),
        "n_features": int(expected_dim),
        "zipmap_node_count": int(zipmap_count),
        "tolerance": float(tol),
        "max_abs_err_batch": max_err_batch,
        "mean_abs_err_batch": mean_err_batch,
        "p99_abs_err_batch": p99_err_batch,
        "max_abs_err_single": max_err_single,
        "max_abs_err_batch_vs_single": max_err_batch_vs_single,
        "toxic_filter_decision_agreement": size_agreement,
        "onnx_proba_min": float(np.min(p1_single)),
        "onnx_proba_mean": float(np.mean(p1_single)),
        "onnx_proba_max": float(np.max(p1_single)),
    }


# ---------------------------------------------------------------------------
# Full End-to-End W4-G05 Export Pipeline
# ---------------------------------------------------------------------------


def run_w4_g05_export(
    *,
    ml_dir: Path = DEFAULT_ML_DIR,
    mqh_out_path: Path = DEFAULT_MQH_PATH,
    portable_files_dir: Path | None = DEFAULT_PORTABLE_FILES_DIR,
    v103_path: Path = DEFAULT_V103_MQ5_PATH,
    verify_v103: bool = True,
    tol: float = PARITY_MAX_ABS_TOL,
) -> dict[str, Any]:
    """Run complete Wave 4 W4-G05 export: ONNX (`zipmap=False`) + ORT parity + `.mqh` + 500 CSV."""
    v103_check = verify_v103_immutable(v103_path) if verify_v103 else None
    bundle = load_prototype_bundle(ml_dir)
    proto_json = bundle["proto_json"]
    x_f32 = bundle["X"]
    p_ref_f64 = bundle["pred_proba_f64"]
    sizes_f32 = bundle["pred_size_toxic_filter"]
    n_feat = int(bundle["n_features"])
    threshold = float(proto_json["train_p_toxic_q20"])

    pkl_path = bundle["proto_pkl_path"]
    if not pkl_path.is_file():
        raise FileNotFoundError(f"MISSING_PROTOTYPE_PKL: {pkl_path}")
    with pkl_path.open("rb") as fh:
        pkl_payload = pickle.load(fh)
    raw_estimator = pkl_payload.get("raw_estimator")
    if raw_estimator is None:
        raise ValueError("PROTOTYPE_PKL_MISSING_RAW_ESTIMATOR")

    # Double-check pickled estimator still reproduces NPZ reference exactly
    p_live_f64 = np.asarray(raw_estimator.predict_proba(x_f32), dtype=np.float64)[:, 1]
    live_vs_npz_err = float(np.max(np.abs(p_live_f64 - p_ref_f64)))
    if live_vs_npz_err > tol:
        raise ValueError(f"PKL_VS_NPZ_PARITY_BREACH: max_err={live_vs_npz_err:.3e} > {tol:.3e}")

    # 1. Export pure float32 ONNX (zipmap=False, 0 ZipMap nodes)
    onnx_out_path = ml_dir / ONNX_MODEL_FILENAME
    onnx_meta = export_lightgbm_to_onnx(
        raw_estimator,
        n_features=n_feat,
        out_onnx_path=onnx_out_path,
        model_name="naqex_v104_lgbm",
    )

    # 2. Verify Python LightGBM == onnxruntime <= 1e-5 on all 500 golden vectors (batch=500 & batch=1)
    ort_parity = verify_onnx_runtime_parity(
        onnx_out_path,
        x_f32,
        p_ref_f64,
        tol=tol,
        threshold=threshold,
        ref_sizes=sizes_f32,
    )

    # 3. Extract flattened white-box trees & generate deterministic Pure-MQL5 + OnnxRun .mqh header
    tree_dump = proto_json["model_whitebox"]["tree_dump"]
    tables = extract_flat_tree_tables(tree_dump, n_features=n_feat)
    mqh_text = render_mql5_filter_header(
        proto_json,
        tables=tables,
        onnx_sha256=onnx_meta["onnx_sha256"],
        onnx_filename=ONNX_MODEL_FILENAME,
    )
    _atomic_write_text_lf(mqh_out_path, mqh_text)

    # 4. Parse ACTUAL generated .mqh file and verify Python == Pure-MQL5 <= 1e-5!
    mqh_disk_text = mqh_out_path.read_text(encoding="utf-8")
    p_mqh_mirror = evaluate_mqh_source_python_mirror(mqh_disk_text, x_f32)
    mqh_vs_py_err = float(np.max(np.abs(p_mqh_mirror - p_ref_f64)))
    if mqh_vs_py_err > tol:
        raise ValueError(f"PURE_MQL5_PARITY_BREACH: max_err={mqh_vs_py_err:.3e} > {tol:.3e}")
    mqh_size_agree = float(np.mean(np.where(p_mqh_mirror < threshold, 0.0, 1.0) == sizes_f32.astype(np.float64)))

    # 5. Export golden 500-vector CSV for MT5 Strategy Tester Probe EA
    csv_out_path = ml_dir / PARITY_CSV_FILENAME
    csv_meta = export_parity_500_csv(x_f32, p_ref_f64, sizes_f32, csv_out_path)

    # 6. Copy ONNX + parity CSV into portable MT5 MQL5/Files/ (for #property tester_file)
    portable_copies: dict[str, Any] = {"copied": False}
    if portable_files_dir is not None:
        portable_files_dir.mkdir(parents=True, exist_ok=True)
        dst_onnx = portable_files_dir / ONNX_MODEL_FILENAME
        dst_csv = portable_files_dir / PARITY_CSV_FILENAME
        shutil.copy2(onnx_out_path, dst_onnx)
        shutil.copy2(csv_out_path, dst_csv)
        portable_copies = {
            "copied": True,
            "portable_onnx_path": str(dst_onnx),
            "portable_onnx_sha256": sha256_file(dst_onnx),
            "portable_csv_path": str(dst_csv),
            "portable_csv_sha256": sha256_file(dst_csv),
        }
        if portable_copies["portable_onnx_sha256"] != onnx_meta["onnx_sha256"]:
            raise RuntimeError("PORTABLE_ONNX_COPY_SHA_MISMATCH")
        if portable_copies["portable_csv_sha256"] != csv_meta["csv_sha256"]:
            raise RuntimeError("PORTABLE_CSV_COPY_SHA_MISMATCH")

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_utc": datetime.now(UTC).isoformat(),
        "source_trial_id": str(proto_json.get("source_trial_id")),
        "approval_tag": str(proto_json.get("approval_tag")),
        "oos_label": CONSUMED_CLB_TAG,
        "hard_invariants": {
            "order_send_capable": ORDER_SEND_CAPABLE,
            "order_send_count": ORDER_SEND_COUNT,
            "spend_vnd": 0,
            "holdout_cutoff_date": HOLDOUT_CUTOFF_DATE,
            "dev_cutoff_sec": DEV_CUTOFF_SEC,
            "holdout_2025_plus_sealed": True,
            "holdout_rows_analysed": 0,
            "zero_bare_asserts": True,
            "lazy_onnx_ml_imports_only": True,
            "zipmap_node_count": int(onnx_meta["zipmap_node_count"]),
        },
        "v103_immutable_check": v103_check,
        "model_contract": {
            "n_features": n_feat,
            "selected_feature_indices": list(proto_json["selected_feature_indices"]),
            "selected_feature_names": list(proto_json["selected_feature_names"]),
            "n_trees": int(tables["n_trees"]),
            "n_nodes": int(tables["n_nodes"]),
            "max_depth": int(tables["max_depth"]),
            "toxic_filter_threshold": threshold,
            "pkl_vs_npz_max_abs_err": live_vs_npz_err,
        },
        "onnx_export": onnx_meta,
        "onnxruntime_parity_500": ort_parity,
        "pure_mql5_header": {
            "mqh_path": str(mqh_out_path),
            "mqh_sha256": sha256_file(mqh_out_path),
            "mqh_bytes": mqh_out_path.stat().st_size,
            "python_vs_mqh_mirror_max_abs_err": mqh_vs_py_err,
            "toxic_filter_decision_agreement": mqh_size_agree,
            "passed": bool(mqh_vs_py_err <= tol),
        },
        "parity_500_csv": csv_meta,
        "portable_mt5_files": portable_copies,
    }

    report_path = ml_dir / EXPORT_REPORT_FILENAME
    _atomic_write_json(report_path, report)
    report["report_path"] = str(report_path)
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Export promoted Wave 4 LightGBM model to float32 ONNX (zipmap=False) + Pure-MQL5 fallback."
    )
    parser.add_argument("--ml-dir", type=Path, default=DEFAULT_ML_DIR, help="Wave 4 ML runtime artifact directory")
    parser.add_argument(
        "--mqh-out",
        type=Path,
        default=DEFAULT_MQH_PATH,
        help="Output path for Naqex_ML_Filter_v104.mqh",
    )
    parser.add_argument(
        "--portable-files-dir",
        type=Path,
        default=DEFAULT_PORTABLE_FILES_DIR,
        help="Portable MT5 MQL5/Files directory for #property tester_file copy",
    )
    parser.add_argument("--no-portable-copy", action="store_true", help="Skip copying ONNX/CSV into portable MT5 Files")
    parser.add_argument("--tol", type=float, default=PARITY_MAX_ABS_TOL, help="Max abs parity error tolerance")
    args = parser.parse_args(list(argv) if argv is not None else None)

    report = run_w4_g05_export(
        ml_dir=args.ml_dir,
        mqh_out_path=args.mqh_out,
        portable_files_dir=None if args.no_portable_copy else args.portable_files_dir,
        tol=args.tol,
    )
    compact = {
        "source_trial_id": report["source_trial_id"],
        "zipmap_node_count": report["onnx_export"]["zipmap_node_count"],
        "onnx_bytes": report["onnx_export"]["onnx_bytes"],
        "onnx_sha256": report["onnx_export"]["onnx_sha256"],
        "ort_max_abs_err_batch": report["onnxruntime_parity_500"]["max_abs_err_batch"],
        "ort_max_abs_err_single": report["onnxruntime_parity_500"]["max_abs_err_single"],
        "pure_mql5_mirror_max_abs_err": report["pure_mql5_header"]["python_vs_mqh_mirror_max_abs_err"],
        "mqh_path": report["pure_mql5_header"]["mqh_path"],
        "portable_copied": report["portable_mt5_files"]["copied"],
        "v103_untouched": report["v103_immutable_check"]["untouched"],
    }
    print(json.dumps(compact, indent=2))
    return 0


__all__ = [
    "CONSUMED_CLB_TAG",
    "DEFAULT_EXPORTS_DIR",
    "DEFAULT_ML_DIR",
    "DEFAULT_MQH_PATH",
    "DEFAULT_PORTABLE_FILES_DIR",
    "DEFAULT_PORTABLE_ROOT",
    "DEFAULT_V103_MQ5_PATH",
    "DEV_CUTOFF_DATE",
    "DEV_CUTOFF_SEC",
    "EXPECTED_PARITY_ROWS",
    "EXPORT_REPORT_FILENAME",
    "HOLDOUT_CUTOFF_DATE",
    "ONNX_MODEL_FILENAME",
    "ORDER_SEND_CAPABLE",
    "ORDER_SEND_COUNT",
    "PARITY_CSV_FILENAME",
    "PARITY_MAX_ABS_TOL",
    "PARITY_NPZ_FILENAME",
    "PROTOTYPE_JSON_FILENAME",
    "PROTOTYPE_PKL_FILENAME",
    "SCHEMA_VERSION",
    "V103_EXPECTED_SHA256",
    "evaluate_flat_trees",
    "evaluate_mqh_source_python_mirror",
    "export_lightgbm_to_onnx",
    "export_parity_500_csv",
    "extract_flat_tree_tables",
    "load_prototype_bundle",
    "main",
    "parse_mqh_tree_tables",
    "render_mql5_filter_header",
    "run_w4_g05_export",
    "sha256_file",
    "validate_feature_matrix",
    "verify_onnx_runtime_parity",
    "verify_v103_immutable",
]

if __name__ == "__main__":
    raise SystemExit(main())

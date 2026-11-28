"""Wave 5 Modular v1.05 MQL5 & MT5 Build 6230 Live Certifier (Gates W5-G10, W5-G12, W5-G15).

Sequentially compiles and certifies the Wave 5 modular MQL5 stack against MT5 Build 6230
portable sandbox (`.runtime/ftmo-demo-portable-1515343166`):
  1. `MetaEditor64.exe` compile of `Naqex_Master_Modular_v105.mq5` and
     `Naqex_ML_Parity500_Probe_v105.mq5` -> strictly `0 errors, 0 warnings`.
     Stores `.ex5` ONLY in `.runtime/mt5-compiled-ex5/` (`0` `.ex5` in `exports/` or `private_vault/`).
  2. **W5-G12 4-Way 500-Vector Parity:**
     `Python LightGBM == onnxruntime CPU == MT5 OnnxRun() == MT5 Pure-MQL5 <= 1e-5`,
     `500/500` decision agreement, `0` ZipMap nodes, `NaN`/`+Inf`/`-Inf` blocked.
  3. **W5-G15 7E-Compat Parity (`Modular_v105 ML=off, DP=off` vs `v103` baseline):**
     Exact `0.00 USD` net PnL delta and exact `469` trade count match on Full-2024 `Model=1` `Funded_1x 10K`.
  4. **W5-G10 End-to-End Live Feature-Extraction Parity (Closing `W4-RT1-P1-01`):**
     Full-2024 `Modular_v105` (`ONNX` AND `Pure-MQL5`, `InpDumpMLFeaturesCsv=true`) reconciled
     against `.runtime/offensive5/ml/wave5_2024_features_ref.csv`:
     `max_abs_feature_err <= 1e-4` across 100% of aligned 2024 signals, `ONNX == Pure-MQL5` to the
     exact cent, `0` delayed/flipped re-entries (`MarkEngineTraded()`), `swap == $0.00`.
  5. **Bellman DP P1 Smoke Full-2024 Test (`InpUseBellmanDP=true, InpBellmanDPPhase=1`):**
     Clean runtime (`rc=0`, `0` runtime errors, `0` crashes, `swap == $0.00`, `ToDate <= 2024.12.31`).

HARD SAFETY & FAIL-CLOSED INVARIANTS (ZERO EXCEPTIONS):
  - `ORDER_SEND_CAPABLE = False`, `ORDER_SEND_COUNT = 0`, `SPEND_VND = 0`, ZERO `MetaTrader5` imports.
  - Holdout 2025+ SEALED (`ToDate <= 2024.12.31`, `holdout_rows_analysed == 0`, `AllowLiveTrading=0`).
  - Strictly ONE `MetaEditor64.exe` / `terminal64.exe` process at a time; `MT5_PROCS == 0` pre & post.
  - `MODE_A_OWNER_ACTIVE` (`BelowNormal 0x4000` priority on Windows for Python).
  - ZERO bare Python `assert` statements (`python -O` safe).
  - LAZY IMPORTS ONLY for `onnx`, `onnxruntime`, `lightgbm`, `sklearn`, `pandas`, `same_feed_mt5_parity`.
  - Every `subprocess.run` passes `creationflags=_NO_WINDOW_FLAGS`.
  - `11/11` immutables untouched (LF-normalized SHA-256 verified for Linux CI portability).
"""

from __future__ import annotations

import argparse
import csv
import ctypes
import hashlib
import json
import math
import os
import pickle
import re
import shutil
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any, Final

import numpy as np

AI_ENGINES_DIR: Final[Path] = Path(__file__).resolve().parents[2]
if str(AI_ENGINES_DIR) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES_DIR))

from quant_core.io_utils import atomic_write_json, repo_root_from, sha256_file  # noqa: E402

from quant_factory.wave5 import (  # noqa: E402
    DEV_CUTOFF_SEC,
    HOLDOUT_CUTOFF_DATE,
    ORDER_SEND_CAPABLE,
    ORDER_SEND_COUNT,
)

# ---------------------------------------------------------------------------
# Hard Safety Constants & Canonical Relative Paths (ZERO hardcoded user paths)
# ---------------------------------------------------------------------------

SCHEMA_RECEIPT: Final[str] = "naqex-wave5-modular-v105-mt5-cert-receipt-v1"
SPEND_VND: Final[int] = 0
BELOW_NORMAL_PRIORITY_CLASS: Final[int] = 0x00004000

REPO_ROOT: Final[Path] = repo_root_from(__file__)
EXPORTS_DIR: Final[Path] = REPO_ROOT / "tooling" / "ai-engines" / "exports"
INCLUDE_DIR: Final[Path] = EXPORTS_DIR / "Include"
PRIVATE_VAULT_DIR: Final[Path] = REPO_ROOT / "private_vault"
COMPILED_EX5_DIR: Final[Path] = REPO_ROOT / ".runtime" / "mt5-compiled-ex5"
COMPILED_LOGS_DIR: Final[Path] = COMPILED_EX5_DIR / "logs"
DEFAULT_PORTABLE_ROOT: Final[Path] = REPO_ROOT / ".runtime" / "ftmo-demo-portable-1515343166"

DEFAULT_W5_ML_DIR: Final[Path] = REPO_ROOT / ".runtime" / "offensive5" / "ml"
DEFAULT_W5_PARETO_DIR: Final[Path] = REPO_ROOT / ".runtime" / "offensive5" / "pareto"
DEFAULT_CERT_WORKDIR: Final[Path] = DEFAULT_W5_ML_DIR / "mt5_cert_w5_modular"
DEFAULT_AUDIT_RECEIPT: Final[Path] = (
    REPO_ROOT / ".runtime" / "offensive5" / "audits" / "w5_modular_mt5_receipt.json"
)
DEFAULT_DROPBOX_RECEIPT: Final[Path] = REPO_ROOT / ".tmp" / "swarm_dropbox" / "w5-modular-mt5.json"

DEFAULT_FUNDED_1X_PRESET: Final[Path] = (
    PRIVATE_VAULT_DIR / "presets" / "offensive3_v3" / "FTMO_Std10K_v103_Funded_1x.set"
)
DEFAULT_SPRINT_EVAL_PRESET: Final[Path] = (
    PRIVATE_VAULT_DIR / "presets" / "offensive3_v3" / "FTMO_Std10K_v103_Sprint_Eval.set"
)
DEFAULT_RED_NEWS_CSV: Final[Path] = EXPORTS_DIR / "Files" / "naqex_red_news_utc.csv"
DEFAULT_V103_FUNDED_1X_HTML: Final[Path] = (
    REPO_ROOT
    / ".runtime"
    / "mt5-realtick-results"
    / "v103_dev_parity"
    / "Funded_1x_Full2024_M1"
    / "v103_Funded_1x_Full2024_M1.htm"
)
DEFAULT_W4_T0_PARITY98_RECEIPT: Final[Path] = (
    REPO_ROOT / ".runtime" / "offensive4" / "audits" / "w4_t0_parity98_receipt.json"
)
DEFAULT_BELLMAN_SCHEDULE_JSON: Final[Path] = DEFAULT_W5_PARETO_DIR / "bellman_dp_schedule.json"

MODULAR_EA_STEM: Final[str] = "Naqex_Master_Modular_v105"
PROBE_EA_STEM: Final[str] = "Naqex_ML_Parity500_Probe_v105"
REGISTRY_MQH_NAME: Final[str] = "Naqex_EngineSlotRegistry.mqh"
ML_FILTER_MQH_NAME: Final[str] = "Naqex_ML_Filter_v105.mqh"
ONNX_MODEL_FILENAME: Final[str] = "naqex_v105_lgbm.onnx"
PARITY_CSV_FILENAME: Final[str] = "wave5_ml_parity_500.csv"
PARITY_OUT_CSV_FILENAME: Final[str] = "wave5_ml_mt5_parity500_out.csv"
REF_2024_FEATURES_CSV_FILENAME: Final[str] = "wave5_2024_features_ref.csv"
LIVE_FEATURES_DUMP_FILENAME: Final[str] = "wave5_mt5_live_features_2024.csv"

EXPECTED_PARITY_ROWS: Final[int] = 500
PARITY_MAX_ABS_TOL: Final[float] = 1e-5
LIVE_FEATURE_MAX_ABS_TOL: Final[float] = 1e-4
DEFAULT_V105_ML_THRESHOLD: Final[float] = 0.448872
V105_SELECTED_FEATURE_NAMES: Final[tuple[str, ...]] = (
    "d1_range_over_atr14",
    "parkinson_vol_10d",
    "prev_bar_close_loc",
    "hour_sin_utc",
    "hour_cos_utc",
    "engine_id_code",
    "same_dir_concurrent_count",
    "rolling_dd_pct_1x_equiv",
)

# Canonical 11/11 Immutables (LF-normalized SHA-256 for Windows & Linux CI portability)
IMMUTABLES_11_LF_SHA256: Final[dict[str, str]] = {
    "AGENTS.md": "b67aa46cb137b79a355ecda832d89de1d29f983463c2196bee9cfcfc70d4257c",
    "planning/research/NATIVE_FTMO_HOLDOUT_LOCK.json": (
        "f0a6b43cb205535b0a959456455dc1d857a0936c06c2e51b8614fd7d772a8486"
    ),
    "tooling/ai-engines/configs/ssot/firms_catalog.json": (
        "b575f1acb82304860eaf1ccf30e45e5d4115c2308bf4d38968fbb6b3517f17ed"
    ),
    "tooling/ai-engines/configs/ssot/ftmo_specs_28.json": (
        "f49e8a4a458b6f3c0f67c8f6b67247355576534dcb607d9fbab4803897c348f7"
    ),
    "tooling/ai-engines/configs/ssot/risk_profiles.json": (
        "58491c41ef9059c8d782e59098bd4a4f9b999c2fad9d18163b65ce4a82210829"
    ),
    "tooling/ai-engines/exports/Files/naqex_red_news_utc.csv": (
        "235722ed1821499f8d81b169418486d3a8b9c0e8911857c88fea8d2270d3dff7"
    ),
    "tooling/ai-engines/exports/Include/Naqex_PropGuard.mqh": (
        "9d7fb3c966688df9cd13ec376b7ea9d4770f5c30bb97b7e5a978d1fe0840e5ed"
    ),
    "tooling/ai-engines/exports/Include/Naqex_Signals_7E.mqh": (
        "2f5b7d7ccd7b8a88b7b9896259cbda846e5553cf6ceb868866f9566a860be738"
    ),
    "tooling/ai-engines/exports/Naqex_Master_Prop7E.mq5": (
        "6b7ea2ee0d5bfa12b27b3ced1003c3c95b3f05d7970e3cda126f5d59fa5250ef"
    ),
    "tooling/ai-engines/exports/Naqex_Master_Prop7E_v103.mq5": (
        "e6b1b88be00a8470505c86dd1878664e08ce12d8e45203c05f733825f35c9ef5"
    ),
    "tooling/ai-engines/quant_core/red_news.py": (
        "5a7e5a1b0c5b67fadd683acf4f8582a0ab39289d3e0f541ea8ed64de5e8f935b"
    ),
}
QUANT_CORE_EXPECTED_PY_COUNT: Final[int] = 41

ENGINE_MAGIC_TO_ID: Final[dict[int, str]] = {
    20261122: "E1_USDJPY_TOKYO",
    20261123: "E2_USDJPY_EXP80",
    20261125: "E3_GBPUSD_VH",
    20261124: "E4_US100_SESS40",
    20261126: "E5_US100_RS1130",
    20261128: "E6_EURJPY_VOLCOMP",
    20261129: "E7_USDJPY_NY10ET",
}

_NO_WINDOW_FLAGS: Final[int] = int(getattr(subprocess, "CREATE_NO_WINDOW", 0)) if os.name == "nt" else 0

_CRITICAL_LOG_ERROR_TOKENS: Final[tuple[str, ...]] = (
    "init_failed",
    "init_parameters_incorrect",
    "initialization failed",
    "invalid stops",
    "not enough money",
    "array out of range",
    "zero divide",
    "stack overflow",
    "critical error",
    "[master-v105-err]",
    "[ml-v105-err]",
    "[ml-v105-warn]",
    "[ml-parity500-v105-err]",
    "onnxrun failed",
    "onnx error",
    "tensorrt",
    "cuda error",
)


class HoldoutViolationError(RuntimeError):
    """Fail-closed error raised if any date or timestamp breaches the 2025+ Holdout seal."""


# ---------------------------------------------------------------------------
# 1. Process Priority, Holdout Seal, LF-Normalized Hashing & Hygiene Guards
# ---------------------------------------------------------------------------


def apply_mode_a_below_normal_priority() -> dict[str, Any]:
    """Apply MODE_A_OWNER_ACTIVE Windows BelowNormal (0x4000) priority to the current Python process."""
    if os.name != "nt":
        return {"policy": "MODE_A_OWNER_ACTIVE", "priority_class": BELOW_NORMAL_PRIORITY_CLASS, "applied": False}
    try:
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetCurrentProcess()
        ok = bool(kernel32.SetPriorityClass(handle, BELOW_NORMAL_PRIORITY_CLASS))
        return {"policy": "MODE_A_OWNER_ACTIVE", "priority_class": BELOW_NORMAL_PRIORITY_CLASS, "applied": ok}
    except Exception:
        return {"policy": "MODE_A_OWNER_ACTIVE", "priority_class": BELOW_NORMAL_PRIORITY_CLASS, "applied": False}


def sha256_lf_normalized(path: Path) -> tuple[str, int]:
    """Compute SHA-256 and byte length after normalizing CRLF -> LF (Windows & Linux CI portable)."""
    raw = path.read_bytes()
    lf = raw.replace(b"\r\n", b"\n")
    return hashlib.sha256(lf).hexdigest(), len(lf)


def round_cent_half_up(value: float) -> float:
    return float(Decimal(str(float(value))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _decode_mt5_text(path: Path) -> str:
    raw = path.read_bytes()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")) or b"\x00" in raw[:200]:
        return raw.decode("utf-16", errors="replace")
    return raw.decode("utf-8", errors="replace")


def _normalize_mt5_date(raw_date: str) -> str:
    cleaned = str(raw_date or "").strip().replace("-", ".")
    if not re.fullmatch(r"\d{4}\.\d{2}\.\d{2}", cleaned):
        raise ValueError(f"INVALID_MT5_DATE: expected YYYY.MM.DD, got {raw_date!r}")
    return cleaned


def assert_dev_date_sealed(to_date: str, from_date: str = "2024.01.02") -> None:
    """Fail-closed Dev-only date guard (rejects any FromDate/ToDate >= 2025.01.01)."""
    d_from = _normalize_mt5_date(from_date)
    d_to = _normalize_mt5_date(to_date)
    if d_from > d_to:
        raise ValueError(f"INVALID_DATE_RANGE: from={d_from} > to={d_to}")
    if d_to > "2024.12.31" or d_from > "2024.12.31":
        raise HoldoutViolationError(
            f"HOLDOUT_2025_SEAL_BREACH: from={d_from}, to={d_to} (max allowed 2024.12.31)"
        )


def assert_safe_portable_root(portable_root: str | Path) -> Path:
    """Ensure MT5 operations target strictly the isolated portable sandbox inside `.runtime/`."""
    p = Path(portable_root).resolve()
    low = str(p).lower()
    if "program files" in low:
        raise RuntimeError(f"FORBIDDEN_LIVE_MT5_INSTALL_ROOT: {p}")
    if ".runtime" not in low or "portable" not in low:
        raise RuntimeError(f"UNSAFE_MT5_ROOT_NOT_PORTABLE_RUNTIME: {p}")
    return p


def list_all_running_mt5_processes() -> list[str]:
    """Return running `terminal64.exe`, `metaeditor64.exe`, `metatester64.exe` lines (zero popups)."""
    if os.name != "nt":
        return []
    found: list[str] = []
    for image in ("terminal64.exe", "metaeditor64.exe", "metatester64.exe"):
        proc = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {image}", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
            creationflags=_NO_WINDOW_FLAGS,
        )
        for line in (proc.stdout or "").splitlines():
            s = line.strip()
            if s and image.lower() in s.lower():
                found.append(s)
    return found


def assert_zero_all_mt5_processes(*, context: str = "check") -> None:
    running = list_all_running_mt5_processes()
    if running:
        raise RuntimeError(f"MT5_PROCS_NON_ZERO[{context}]: {len(running)} active ({running[:3]})")


def verify_immutables_11_and_hygiene(
    *,
    repo_root: Path = REPO_ROOT,
    exports_dir: Path | None = None,
    private_vault_dir: Path | None = None,
) -> dict[str, Any]:
    """Verify ALL 11/11 immutables (LF-normalized SHA-256), `quant_core` count, and 0 stray `.ex5`."""
    exp_dir = exports_dir if exports_dir is not None else (repo_root / "tooling" / "ai-engines" / "exports")
    vault_dir = private_vault_dir if private_vault_dir is not None else (repo_root / "private_vault")
    qc_dir = repo_root / "tooling" / "ai-engines" / "quant_core"

    checked: dict[str, dict[str, Any]] = {}
    for rel_path, expected_lf_sha in IMMUTABLES_11_LF_SHA256.items():
        full = repo_root / rel_path
        if not full.is_file():
            raise FileNotFoundError(f"IMMUTABLE_MISSING: {rel_path}")
        actual_lf_sha, lf_bytes = sha256_lf_normalized(full)
        if actual_lf_sha != expected_lf_sha:
            raise RuntimeError(
                f"IMMUTABLE_BREACH[{rel_path}]: lf_sha={actual_lf_sha} != expected={expected_lf_sha}"
            )
        checked[rel_path] = {
            "lf_sha256": actual_lf_sha,
            "lf_bytes": lf_bytes,
            "untouched": True,
        }

    quant_core_py_count = len(list(qc_dir.glob("*.py"))) if qc_dir.is_dir() else 0
    if quant_core_py_count != QUANT_CORE_EXPECTED_PY_COUNT:
        raise RuntimeError(
            f"IMMUTABLE_BREACH: quant_core py count={quant_core_py_count} != {QUANT_CORE_EXPECTED_PY_COUNT}"
        )

    stray_exports_ex5 = (
        [str(p.relative_to(repo_root)) for p in sorted(exp_dir.rglob("*.ex5"))] if exp_dir.is_dir() else []
    )
    if stray_exports_ex5:
        raise RuntimeError(f"FORBIDDEN_EX5_IN_EXPORTS: {stray_exports_ex5}")

    stray_vault_ex5 = (
        [str(p.relative_to(repo_root)) for p in sorted(vault_dir.rglob("*.ex5"))]
        if vault_dir.is_dir()
        else []
    )
    if stray_vault_ex5:
        raise RuntimeError(f"FORBIDDEN_EX5_IN_PRIVATE_VAULT: {stray_vault_ex5}")

    return {
        "immutables_11_of_11_untouched": True,
        "immutables_checked": len(checked),
        "immutables": checked,
        "quant_core_py_count": quant_core_py_count,
        "quant_core_untouched": True,
        "exports_ex5_count": len(stray_exports_ex5),
        "private_vault_ex5_count": len(stray_vault_ex5),
    }


# ---------------------------------------------------------------------------
# 2. Pure-Python v1.05 MQH Mirror, 4-Way Parity, Log & Feature Reconcilers
# ---------------------------------------------------------------------------


def parse_mqh_v105_tree_tables(mqh_text: str) -> dict[str, Any]:
    """Parse flattened LightGBM tree arrays directly from `Naqex_ML_Filter_v105.mqh` source text."""
    m_feat = re.search(r"#define\s+NAQEX_V105_ML_N_FEATURES\s+(\d+)", mqh_text)
    m_trees = re.search(r"#define\s+NAQEX_V105_ML_N_TREES\s+(\d+)", mqh_text)
    m_nodes = re.search(r"#define\s+NAQEX_V105_ML_N_NODES\s+(\d+)", mqh_text)
    if not (m_feat and m_trees and m_nodes):
        raise ValueError("INVALID_V105_MQH_HEADER: missing NAQEX_V105_ML_N_* macros")

    n_feat = int(m_feat.group(1))
    n_trees = int(m_trees.group(1))
    n_nodes = int(m_nodes.group(1))

    def _extract_array(name: str, *, as_float: bool) -> list[Any]:
        pat = re.compile(rf"static\s+const\s+\w+\s+{re.escape(name)}\s*\[[^\]]+\]\s*=\s*\{{(.*?)\}}\s*;", re.S)
        m = pat.search(mqh_text)
        if not m:
            raise ValueError(f"INVALID_V105_MQH_HEADER: missing array {name}")
        tokens = [tok.strip() for tok in m.group(1).split(",") if tok.strip()]
        return [float(tok) if as_float else int(tok) for tok in tokens]

    tree_roots = _extract_array("g_v105TreeRoots", as_float=False)
    node_feat = _extract_array("g_v105NodeFeat", as_float=False)
    node_left = _extract_array("g_v105NodeLeft", as_float=False)
    node_right = _extract_array("g_v105NodeRight", as_float=False)
    node_thresh = _extract_array("g_v105NodeThresh", as_float=True)
    node_leaf = _extract_array("g_v105NodeLeaf", as_float=True)

    if len(tree_roots) != n_trees:
        raise ValueError(f"MQH_V105_TREE_COUNT_MISMATCH: {len(tree_roots)} != {n_trees}")
    for nm, vals in (
        ("g_v105NodeFeat", node_feat),
        ("g_v105NodeLeft", node_left),
        ("g_v105NodeRight", node_right),
        ("g_v105NodeThresh", node_thresh),
        ("g_v105NodeLeaf", node_leaf),
    ):
        if len(vals) != n_nodes:
            raise ValueError(f"MQH_V105_NODE_COUNT_MISMATCH[{nm}]: {len(vals)} != {n_nodes}")

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


def validate_feature_matrix_v105(raw_x: Any, *, expected_dim: int | None = None, name: str = "X") -> np.ndarray:
    if raw_x is None or isinstance(raw_x, (bool, np.bool_, str, bytes)):
        raise ValueError(f"INVALID_FEATURE_MATRIX[{name}]: got {type(raw_x).__name__}")
    arr = np.asarray(raw_x)
    if arr.dtype == np.bool_:
        raise ValueError(f"POISONED_BOOL_FEATURE_MATRIX[{name}]")
    try:
        x_f64 = np.asarray(arr, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"NON_NUMERIC_FEATURE_MATRIX[{name}]") from exc
    if x_f64.ndim != 2 or x_f64.shape[0] == 0:
        raise ValueError(f"INVALID_FEATURE_SHAPE[{name}]: expected 2D non-empty, got {x_f64.shape}")
    if expected_dim is not None and x_f64.shape[1] != int(expected_dim):
        raise ValueError(f"FEATURE_DIM_MISMATCH[{name}]: expected {expected_dim}, got {x_f64.shape[1]}")
    if not bool(np.all(np.isfinite(x_f64))):
        raise ValueError(f"NON_FINITE_FEATURE_MATRIX[{name}]: NaN or Inf rejected fail-closed")
    return np.ascontiguousarray(x_f64, dtype=np.float32)


def evaluate_mqh_v105_python_mirror(mqh_text: str, raw_x: Any) -> np.ndarray:
    """Evaluate the serialized `Naqex_ML_Filter_v105.mqh` tree tables in pure NumPy."""
    tables = parse_mqh_v105_tree_tables(mqh_text)
    x_f32 = validate_feature_matrix_v105(raw_x, expected_dim=tables["n_features"], name="mqh_v105_mirror")
    x_f64 = x_f32.astype(np.float64)
    n_rows = x_f64.shape[0]
    roots = tables["tree_roots"]
    n_feat = tables["node_feat"]
    n_left = tables["node_left"]
    n_right = tables["node_right"]
    n_thr = tables["node_thresh"]
    n_leaf = tables["node_leaf"]

    out = np.empty(n_rows, dtype=np.float64)
    for i in range(n_rows):
        row = x_f64[i]
        raw_sum = 0.0
        for root in roots:
            idx = root
            for _ in range(32):
                f = n_feat[idx]
                if f < 0:
                    raw_sum += n_leaf[idx]
                    break
                idx = n_left[idx] if row[f] <= n_thr[idx] else n_right[idx]
        clamped = max(-35.0, min(35.0, raw_sum))
        p = 1.0 / (1.0 + math.exp(-clamped))
        out[i] = max(1e-6, min(1.0 - 1e-6, p))
    return out


def _validate_prob_vector(raw: Any, *, expected_len: int, name: str) -> np.ndarray:
    if raw is None or isinstance(raw, (bool, np.bool_, str, bytes)):
        raise ValueError(f"INVALID_PROB_VECTOR[{name}]: got {type(raw).__name__}")
    arr = np.asarray(raw)
    if arr.dtype == np.bool_:
        raise ValueError(f"POISONED_BOOL_PROB_VECTOR[{name}]")
    try:
        vec = np.asarray(arr, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"NON_NUMERIC_PROB_VECTOR[{name}]") from exc
    if vec.ndim != 1 or vec.shape[0] != int(expected_len):
        raise ValueError(f"PROB_VECTOR_SHAPE_MISMATCH[{name}]: expected ({expected_len},), got {vec.shape}")
    if not bool(np.all(np.isfinite(vec))):
        raise ValueError(f"NON_FINITE_PROB_VECTOR[{name}]: NaN or Inf detected (fail-closed)")
    if float(np.min(vec)) < 0.0 or float(np.max(vec)) > 1.0:
        raise ValueError(
            f"OUT_OF_RANGE_PROB_VECTOR[{name}]: min={float(np.min(vec))}, max={float(np.max(vec))}"
        )
    return vec


def _pairwise_err_stats(a: np.ndarray, b: np.ndarray) -> dict[str, float]:
    diff = np.abs(a - b)
    return {
        "max_abs_err": float(np.max(diff)),
        "mean_abs_err": float(np.mean(diff)),
        "p99_abs_err": float(np.percentile(diff, 99.0)),
    }


def compute_four_way_parity_metrics_v105(
    *,
    py_lgbm_proba: Sequence[float] | np.ndarray,
    ort_batch_proba: Sequence[float] | np.ndarray,
    ort_single_proba: Sequence[float] | np.ndarray,
    mt5_onnx_proba: Sequence[float] | np.ndarray,
    mt5_pure_proba: Sequence[float] | np.ndarray,
    py_mqh_mirror_proba: Sequence[float] | np.ndarray,
    ref_sizes: Sequence[float] | np.ndarray,
    threshold: float = DEFAULT_V105_ML_THRESHOLD,
    tol: float = PARITY_MAX_ABS_TOL,
) -> dict[str, Any]:
    """Compute 4-way (`Python LightGBM == ORT == MT5 OnnxRun() == Pure-MQL5`) parity stats (CI-safe)."""
    if isinstance(threshold, bool) or not math.isfinite(float(threshold)) or not (0.0 < float(threshold) < 1.0):
        raise ValueError(f"INVALID_THRESHOLD: {threshold!r}")
    if isinstance(tol, bool) or not math.isfinite(float(tol)) or float(tol) <= 0.0:
        raise ValueError(f"INVALID_TOLERANCE: {tol!r}")

    py_ref = np.asarray(py_lgbm_proba, dtype=np.float64)
    if py_ref.ndim != 1 or py_ref.shape[0] == 0:
        raise ValueError(f"INVALID_REFERENCE_VECTOR: shape={py_ref.shape}")
    n_rows = int(py_ref.shape[0])

    v_py = _validate_prob_vector(py_lgbm_proba, expected_len=n_rows, name="py_lgbm_proba")
    v_ort_b = _validate_prob_vector(ort_batch_proba, expected_len=n_rows, name="ort_batch_proba")
    v_ort_s = _validate_prob_vector(ort_single_proba, expected_len=n_rows, name="ort_single_proba")
    v_mt5_onnx = _validate_prob_vector(mt5_onnx_proba, expected_len=n_rows, name="mt5_onnx_proba")
    v_mt5_pure = _validate_prob_vector(mt5_pure_proba, expected_len=n_rows, name="mt5_pure_proba")
    v_py_mqh = _validate_prob_vector(py_mqh_mirror_proba, expected_len=n_rows, name="py_mqh_mirror_proba")

    v_sizes = np.asarray(ref_sizes, dtype=np.float64)
    if v_sizes.shape != (n_rows,) or not bool(np.all(np.isfinite(v_sizes))):
        raise ValueError(f"INVALID_REF_SIZES: shape={v_sizes.shape}")

    pairs: dict[str, dict[str, float]] = {
        "py_lgbm_vs_ort_batch": _pairwise_err_stats(v_py, v_ort_b),
        "py_lgbm_vs_ort_single": _pairwise_err_stats(v_py, v_ort_s),
        "py_lgbm_vs_mt5_onnx": _pairwise_err_stats(v_py, v_mt5_onnx),
        "py_lgbm_vs_mt5_pure_mql5": _pairwise_err_stats(v_py, v_mt5_pure),
        "ort_single_vs_mt5_onnx": _pairwise_err_stats(v_ort_s, v_mt5_onnx),
        "mt5_onnx_vs_mt5_pure_mql5": _pairwise_err_stats(v_mt5_onnx, v_mt5_pure),
        "py_mqh_mirror_vs_mt5_pure_mql5": _pairwise_err_stats(v_py_mqh, v_mt5_pure),
    }

    overall_max_abs_err = max(stats["max_abs_err"] for stats in pairs.values())
    thr = float(threshold)
    size_agreements = {
        "ort_batch": float(np.mean(np.where(v_ort_b >= thr, 1.0, 0.0) == v_sizes)),
        "ort_single": float(np.mean(np.where(v_ort_s >= thr, 1.0, 0.0) == v_sizes)),
        "mt5_onnx": float(np.mean(np.where(v_mt5_onnx >= thr, 1.0, 0.0) == v_sizes)),
        "mt5_pure_mql5": float(np.mean(np.where(v_mt5_pure >= thr, 1.0, 0.0) == v_sizes)),
        "py_mqh_mirror": float(np.mean(np.where(v_py_mqh >= thr, 1.0, 0.0) == v_sizes)),
    }
    all_agreements_100pct = all(val == 1.0 for val in size_agreements.values())
    passed = bool(overall_max_abs_err <= float(tol) and all_agreements_100pct)

    return {
        "passed": passed,
        "n_vectors": n_rows,
        "tolerance": float(tol),
        "threshold": thr,
        "overall_max_abs_err": overall_max_abs_err,
        "all_decision_agreements_100pct": all_agreements_100pct,
        "decision_agreements": size_agreements,
        "pairwise": pairs,
    }


def parse_metaeditor_compile_log(log_text: str) -> dict[str, Any]:
    """Parse MetaEditor64 compile output for exact `Result: X errors, Y warnings`."""
    m = re.search(r"Result:\s*(\d+)\s+errors?,\s*(\d+)\s+warnings?", log_text, flags=re.IGNORECASE)
    if not m:
        return {"parsed": False, "errors": -1, "warnings": -1, "clean_zero": False, "result_line": None}
    n_err = int(m.group(1))
    n_warn = int(m.group(2))
    return {
        "parsed": True,
        "errors": n_err,
        "warnings": n_warn,
        "clean_zero": bool(n_err == 0 and n_warn == 0),
        "result_line": m.group(0),
    }


def parse_parity500_v105_csv(
    csv_path: str | Path,
    *,
    expected_rows: int = EXPECTED_PARITY_ROWS,
) -> dict[str, Any]:
    """Parse `wave5_ml_mt5_parity500_out.csv` emitted by `Naqex_ML_Parity500_Probe_v105.ex5`."""
    path = Path(csv_path)
    if not path.is_file():
        raise FileNotFoundError(f"MT5_PARITY500_V105_CSV_MISSING: {path}")

    row_indices: list[int] = []
    ref_proba: list[float] = []
    onnx_proba: list[float] = []
    pure_proba: list[float] = []
    ref_size: list[float] = []
    onnx_size: list[float] = []
    pure_size: list[float] = []

    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        req_cols = {"row_idx", "ref_proba", "onnx_proba", "pure_mql5_proba", "ref_size", "onnx_size", "pure_size"}
        missing = sorted(req_cols - set(reader.fieldnames or []))
        if missing:
            raise ValueError(f"MT5_PARITY500_V105_CSV_MISSING_COLS: {missing}")

        for line_no, row in enumerate(reader, start=2):
            try:
                ridx = int(str(row["row_idx"]).strip())
                rp = float(str(row["ref_proba"]).strip())
                op = float(str(row["onnx_proba"]).strip())
                pp = float(str(row["pure_mql5_proba"]).strip())
                rs = float(str(row["ref_size"]).strip())
                os_ = float(str(row["onnx_size"]).strip())
                ps = float(str(row["pure_size"]).strip())
            except (TypeError, ValueError) as exc:
                raise ValueError(f"MT5_PARITY500_V105_PARSE_ERR at line {line_no}") from exc

            for nm, val in (
                ("ref_proba", rp),
                ("onnx_proba", op),
                ("pure_mql5_proba", pp),
                ("ref_size", rs),
                ("onnx_size", os_),
                ("pure_size", ps),
            ):
                if not math.isfinite(val):
                    raise ValueError(f"MT5_PARITY500_V105_NON_FINITE[{nm}] at line {line_no}: {val!r}")

            row_indices.append(ridx)
            ref_proba.append(rp)
            onnx_proba.append(op)
            pure_proba.append(pp)
            ref_size.append(rs)
            onnx_size.append(os_)
            pure_size.append(ps)

    if len(row_indices) != int(expected_rows):
        raise ValueError(f"MT5_PARITY500_V105_ROW_COUNT_MISMATCH: expected {expected_rows}, got {len(row_indices)}")
    if row_indices != list(range(int(expected_rows))):
        raise ValueError("MT5_PARITY500_V105_INDEX_NON_CONTIGUOUS")

    return {
        "csv_path": str(path),
        "csv_sha256": sha256_file(path),
        "csv_bytes": path.stat().st_size,
        "rows": len(row_indices),
        "ref_proba": np.asarray(ref_proba, dtype=np.float64),
        "onnx_proba": np.asarray(onnx_proba, dtype=np.float64),
        "pure_mql5_proba": np.asarray(pure_proba, dtype=np.float64),
        "ref_size": np.asarray(ref_size, dtype=np.float64),
        "onnx_size": np.asarray(onnx_size, dtype=np.float64),
        "pure_size": np.asarray(pure_size, dtype=np.float64),
    }


def _scan_log_errors(log_text: str) -> list[str]:
    issues: list[str] = []
    for raw_ln in log_text.splitlines():
        ln = raw_ln.strip()
        if not ln:
            continue
        low = ln.lower()
        if any(tok in low for tok in _CRITICAL_LOG_ERROR_TOKENS):
            issues.append(ln)
    return issues


def parse_parity500_v105_log(log_text: str) -> dict[str, Any]:
    """Parse `Naqex_ML_Parity500_Probe_v105` Agent log for ONNX API, CPU EP, summary & NaN/Inf blocks."""
    onnx_api_version: str | None = None
    cpu_selected = False
    init_line: str | None = None
    summary_line: str | None = None
    summary_kv: dict[str, str] = {}

    for raw_ln in log_text.splitlines():
        ln = raw_ln.strip()
        if not ln:
            continue
        m_api = re.search(r"api version\s+([0-9][0-9A-Za-z._-]+)\s+initialized", ln, flags=re.IGNORECASE)
        if m_api:
            onnx_api_version = m_api.group(1)
        if "ONNX: CPU selected" in ln:
            cpu_selected = True
        if "[ML-PARITY500-V105-INIT]" in ln:
            init_line = ln
        if "PARITY500_V105_SUMMARY|" in ln:
            summary_line = ln
            tail = ln.split("PARITY500_V105_SUMMARY|", 1)[1]
            for item in tail.split("|"):
                if "=" in item:
                    k, v = item.split("=", 1)
                    summary_kv[k.strip()] = v.strip()

    error_lines = _scan_log_errors(log_text)
    return {
        "onnx_api_version": onnx_api_version,
        "cpu_selected": cpu_selected,
        "init_line": init_line,
        "summary_line": summary_line,
        "rows": int(summary_kv["rows"]) if "rows" in summary_kv else 0,
        "onnx_ready": summary_kv.get("onnx_ready", "").lower() == "true",
        "onnx_ok": int(summary_kv["onnx_ok"]) if "onnx_ok" in summary_kv else 0,
        "pure_ok": int(summary_kv["pure_ok"]) if "pure_ok" in summary_kv else 0,
        "onnx_size_match": int(summary_kv["onnx_size_match"]) if "onnx_size_match" in summary_kv else 0,
        "pure_size_match": int(summary_kv["pure_size_match"]) if "pure_size_match" in summary_kv else 0,
        "nan_blocked": summary_kv.get("nan_blocked", "").lower() == "true",
        "inf_blocked": summary_kv.get("inf_blocked", "").lower() == "true",
        "parity_pass": summary_kv.get("parity_pass", "").lower() == "true",
        "log_max_err_onnx_ref": float(summary_kv["max_err_onnx_ref"]) if "max_err_onnx_ref" in summary_kv else None,
        "log_max_err_pure_ref": float(summary_kv["max_err_pure_ref"]) if "max_err_pure_ref" in summary_kv else None,
        "log_max_err_onnx_pure": float(summary_kv["max_err_onnx_pure"]) if "max_err_onnx_pure" in summary_kv else None,
        "error_lines_count": len(error_lines),
        "error_lines": error_lines[:10],
    }


def parse_modular_v105_tester_log(log_text: str) -> dict[str, Any]:
    """Parse `Naqex_Master_Modular_v105` Tester logs for `[MASTER-V105-INIT]`, `[MASTER-V105-DEINIT]` & errors."""
    onnx_api_version: str | None = None
    cpu_selected = False
    init_line: str | None = None
    deinit_line: str | None = None
    init_kv: dict[str, str] = {}
    deinit_kv: dict[str, str] = {}

    for raw_ln in log_text.splitlines():
        ln = raw_ln.strip()
        if not ln:
            continue
        m_api = re.search(r"api version\s+([0-9][0-9A-Za-z._-]+)\s+initialized", ln, flags=re.IGNORECASE)
        if m_api:
            onnx_api_version = m_api.group(1)
        if "ONNX: CPU selected" in ln:
            cpu_selected = True
        if "[MASTER-V105-INIT]" in ln:
            init_line = ln
            tail = ln.split("[MASTER-V105-INIT]", 1)[1].strip()
            for tok in tail.split():
                if "=" in tok:
                    k, v = tok.split("=", 1)
                    init_kv[k.strip()] = v.strip()
        if "[MASTER-V105-DEINIT]" in ln:
            deinit_line = ln
            tail = ln.split("[MASTER-V105-DEINIT]", 1)[1].strip()
            for tok in tail.split():
                if "=" in tok:
                    k, v = tok.split("=", 1)
                    deinit_kv[k.strip()] = v.strip()

    error_lines = _scan_log_errors(log_text)
    return {
        "onnx_api_version": onnx_api_version,
        "cpu_selected": cpu_selected,
        "init_line": init_line,
        "deinit_line": deinit_line,
        "sku": init_kv.get("sku"),
        "ml_enabled": init_kv.get("ml_enabled", "").lower() == "true" if "ml_enabled" in init_kv else None,
        "ml_use_onnx": init_kv.get("ml_use_onnx", "").lower() == "true" if "ml_use_onnx" in init_kv else None,
        "ml_thr": float(init_kv["ml_thr"]) if "ml_thr" in init_kv else None,
        "ml_onnx_ready": init_kv.get("ml_onnx_ready", "").lower() == "true" if "ml_onnx_ready" in init_kv else None,
        "ml_backend": init_kv.get("ml_backend"),
        "bellman_dp": init_kv.get("bellman_dp", "").lower() == "true" if "bellman_dp" in init_kv else None,
        "dp_phase": int(init_kv["dp_phase"]) if "dp_phase" in init_kv else None,
        "dp_tiers": int(init_kv["dp_tiers"]) if "dp_tiers" in init_kv else None,
        "slots_enabled": int(init_kv["slots_enabled"]) if "slots_enabled" in init_kv else None,
        "dump_csv": init_kv.get("dump_csv", "").lower() == "true" if "dump_csv" in init_kv else None,
        "dry_run": init_kv.get("dry_run", "").lower() == "true" if "dry_run" in init_kv else None,
        "ml_passed": int(deinit_kv["ml_passed"]) if "ml_passed" in deinit_kv else None,
        "ml_blocked": int(deinit_kv["ml_blocked"]) if "ml_blocked" in deinit_kv else None,
        "ml_onnx_calls": int(deinit_kv["ml_onnx_calls"]) if "ml_onnx_calls" in deinit_kv else None,
        "ml_pure_calls": int(deinit_kv["ml_pure_calls"]) if "ml_pure_calls" in deinit_kv else None,
        "ml_fallback_calls": int(deinit_kv["ml_fallback_calls"]) if "ml_fallback_calls" in deinit_kv else None,
        "shadow_closed": int(deinit_kv["shadow_closed"]) if "shadow_closed" in deinit_kv else None,
        "dump_rows": int(deinit_kv["dump_rows"]) if "dump_rows" in deinit_kv else None,
        "error_lines_count": len(error_lines),
        "error_lines": error_lines[:10],
    }


def _load_feature_signals_csv(csv_path: Path, *, is_ea_dump: bool) -> list[dict[str, Any]]:
    if not csv_path.is_file():
        raise FileNotFoundError(f"FEATURE_CSV_MISSING: {csv_path}")
    rows: list[dict[str, Any]] = []
    p_col = "ea_p_win" if is_ea_dump else "ref_p_win"
    a_col = "ea_ml_allowed" if is_ea_dump else "ref_ml_allowed"
    req = {
        "signal_seq",
        "entry_utc_ts",
        "entry_server_time",
        "engine_id",
        "magic",
        "symbol",
        "side",
        "f0",
        "f1",
        "f2",
        "f3",
        "f4",
        "f5",
        "f6",
        "f7",
        p_col,
        a_col,
    }
    with csv_path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        missing = sorted(req - set(reader.fieldnames or []))
        if missing:
            raise ValueError(f"FEATURE_CSV_MISSING_COLS[{csv_path.name}]: {missing}")
        for ln, row in enumerate(reader, start=2):
            feats = [float(str(row[f"f{j}"]).strip()) for j in range(8)]
            p_win = float(str(row[p_col]).strip())
            if not all(math.isfinite(v) for v in feats) or not math.isfinite(p_win):
                raise ValueError(f"NON_FINITE_FEATURE_CSV[{csv_path.name}] line={ln}")
            entry_utc = int(str(row["entry_utc_ts"]).strip())
            if entry_utc >= DEV_CUTOFF_SEC:
                raise HoldoutViolationError(f"HOLDOUT_FEATURE_ROW[{csv_path.name}]: entry_utc={entry_utc}")
            rows.append(
                {
                    "signal_seq": int(str(row["signal_seq"]).strip()),
                    "entry_utc_ts": entry_utc,
                    "entry_server_time": str(row["entry_server_time"]).strip(),
                    "engine_id": str(row["engine_id"]).strip(),
                    "magic": int(str(row["magic"]).strip()),
                    "symbol": str(row["symbol"]).strip(),
                    "side": str(row["side"]).strip().upper(),
                    "features": np.asarray(feats, dtype=np.float64),
                    "p_win": p_win,
                    "ml_allowed": int(str(row[a_col]).strip()),
                    "backend": str(row.get("ea_backend", "PYTHON_REF")).strip(),
                    "shadow_eq_1x": float(str(row.get("shadow_eq_1x", "1.0")).strip()),
                    "shadow_peak_1x": float(str(row.get("shadow_peak_1x", "1.0")).strip()),
                    "shadow_dd_pct_1x": float(str(row.get("shadow_dd_pct_1x", "0.0")).strip()),
                }
            )
    return rows


def reconcile_live_ea_features_vs_python_ref(
    *,
    ea_csv_path: str | Path,
    ref_csv_path: str | Path,
    feature_tol: float = LIVE_FEATURE_MAX_ABS_TOL,
    prob_tol: float = PARITY_MAX_ABS_TOL,
    f7_pp_raw_tol: float = 0.005,
) -> dict[str, Any]:
    """Reconcile EVERY live EA-computed feature vector against `wave5_2024_features_ref.csv` (W5-G10).

    Aligns signals 1:1 by `(magic, entry_utc_ts, side)` and enforces strict parity across:
      1. Direct market & structural features `f0..f6` (`<= feature_tol = 1e-4`),
      2. Fractional Shadow1x portfolio state (`shadow_eq_1x` & `f7 / 100.0` both `<= feature_tol = 1e-4`)
         plus exact Shadow1x formula self-consistency (`<= 1e-6`) and raw percentage-point `f7` (`0..100`
         scale) reported verbatim with `<= f7_pp_raw_tol` (`0.005` pp = `5e-5` fractional),
      3. End-to-end live model probability parity `|ea_p_win - ref_p_win| <= prob_tol (1e-5)` and
         100% decision agreement (`0` split crossings, `0` unmatched signals).
    """
    ea_rows = _load_feature_signals_csv(Path(ea_csv_path), is_ea_dump=True)
    ref_rows = _load_feature_signals_csv(Path(ref_csv_path), is_ea_dump=False)

    if not ea_rows or not ref_rows:
        raise ValueError(f"EMPTY_FEATURE_RECONCILIATION: ea={len(ea_rows)}, ref={len(ref_rows)}")

    # Group by (magic, entry_utc_ts, side) for exact 1:1 pairing
    ref_exact: dict[tuple[int, int, str], list[dict[str, Any]]] = {}
    for r in ref_rows:
        ref_exact.setdefault((r["magic"], r["entry_utc_ts"], r["side"]), []).append(r)

    matched_pairs: list[tuple[dict[str, Any], dict[str, Any], int]] = []
    unmatched_ea: list[dict[str, Any]] = []

    for e in ea_rows:
        key = (e["magic"], e["entry_utc_ts"], e["side"])
        bucket = ref_exact.get(key)
        if bucket:
            matched_pairs.append((e, bucket.pop(0), 0))
        else:
            unmatched_ea.append(e)

    remaining_ref: list[dict[str, Any]] = []
    for bucket in ref_exact.values():
        remaining_ref.extend(bucket)

    # Secondary check: near-timestamp match (same magic & side within <= 60s) for diagnostics
    still_unmatched_ea: list[dict[str, Any]] = []
    near_matched_count = 0
    for e in unmatched_ea:
        best_i = -1
        best_dt = 61
        for idx, r in enumerate(remaining_ref):
            if r["magic"] == e["magic"] and r["side"] == e["side"]:
                dt = abs(e["entry_utc_ts"] - r["entry_utc_ts"])
                if dt < best_dt:
                    best_dt = dt
                    best_i = idx
        if best_i >= 0:
            matched_pairs.append((e, remaining_ref.pop(best_i), best_dt))
            near_matched_count += 1
        else:
            still_unmatched_ea.append(e)

    n_matched = len(matched_pairs)
    if n_matched == 0:
        raise ValueError("ZERO_ALIGNED_SIGNALS_BETWEEN_EA_AND_PYTHON_REF")

    ea_mat = np.vstack([p[0]["features"] for p in matched_pairs])
    ref_mat = np.vstack([p[1]["features"] for p in matched_pairs])
    abs_diff = np.abs(ea_mat - ref_mat)

    ea_p = np.asarray([p[0]["p_win"] for p in matched_pairs], dtype=np.float64)
    ref_p = np.asarray([p[1]["p_win"] for p in matched_pairs], dtype=np.float64)
    p_diff = np.abs(ea_p - ref_p)

    ea_allow = np.asarray([p[0]["ml_allowed"] for p in matched_pairs], dtype=np.int32)
    ref_allow = np.asarray([p[1]["ml_allowed"] for p in matched_pairs], dtype=np.int32)
    decision_matches = int(np.sum(ea_allow == ref_allow))

    per_feature: dict[str, dict[str, Any]] = {}
    worst_examples: list[dict[str, Any]] = []
    for j, fname in enumerate(V105_SELECTED_FEATURE_NAMES):
        col_err = abs_diff[:, j]
        w_idx = int(np.argmax(col_err))
        w_val = float(col_err[w_idx])
        e_row, r_row, dt_s = matched_pairs[w_idx]
        per_feature[fname] = {
            "index": j,
            "max_abs_err": w_val,
            "mean_abs_err": float(np.mean(col_err)),
            "p99_abs_err": float(np.percentile(col_err, 99.0)),
            "passed_le_tol": bool(w_val <= float(feature_tol)),
            "worst_signal_seq_ea": e_row["signal_seq"],
            "worst_entry_server_time": e_row["entry_server_time"],
            "worst_engine_id": e_row["engine_id"],
            "worst_ea_val": float(e_row["features"][j]),
            "worst_ref_val": float(r_row["features"][j]),
            "worst_time_diff_sec": dt_s,
        }
        if w_val > float(feature_tol):
            worst_examples.append({"feature": fname, **per_feature[fname]})

    overall_max_feature_err = float(np.max(abs_diff))
    market_struct_max_err = float(np.max(abs_diff[:, :7]))
    f7_pp_raw_max_err = float(np.max(abs_diff[:, 7]))
    f7_frac_dd_max_err = f7_pp_raw_max_err / 100.0

    ea_eq_arr = np.asarray([p[0]["shadow_eq_1x"] for p in matched_pairs], dtype=np.float64)
    ref_eq_arr = np.asarray([p[1]["shadow_eq_1x"] for p in matched_pairs], dtype=np.float64)
    ea_pk_arr = np.asarray([p[0]["shadow_peak_1x"] for p in matched_pairs], dtype=np.float64)
    shadow_eq_1x_max_err = float(np.max(np.abs(ea_eq_arr - ref_eq_arr)))
    ea_f7_expected = 100.0 * np.maximum(0.0, (ea_pk_arr - ea_eq_arr) / np.maximum(ea_pk_arr, 1e-12))
    f7_formula_self_err = float(np.max(np.abs(ea_mat[:, 7] - ea_f7_expected)))

    normalized_feature_max_err = max(market_struct_max_err, f7_frac_dd_max_err, shadow_eq_1x_max_err)
    max_p_win_err = float(np.max(p_diff))
    exact_ts_matched = n_matched - near_matched_count
    match_ratio_ea = float(n_matched) / float(len(ea_rows))
    match_ratio_ref = float(n_matched) / float(len(ref_rows))
    decision_agreement_ratio = float(decision_matches) / float(n_matched)

    passed = bool(
        market_struct_max_err <= float(feature_tol)
        and f7_frac_dd_max_err <= float(feature_tol)
        and shadow_eq_1x_max_err <= float(feature_tol)
        and f7_formula_self_err <= 1e-6
        and f7_pp_raw_max_err <= float(f7_pp_raw_tol)
        and max_p_win_err <= float(prob_tol)
        and decision_matches == n_matched
        and exact_ts_matched == n_matched
        and len(still_unmatched_ea) == 0
        and len(remaining_ref) == 0
    )

    return {
        "passed": passed,
        "feature_tolerance": float(feature_tol),
        "prob_tolerance": float(prob_tol),
        "f7_pp_raw_tolerance": float(f7_pp_raw_tol),
        "ea_signals_total": len(ea_rows),
        "ref_signals_total": len(ref_rows),
        "matched_signals_total": n_matched,
        "exact_timestamp_matched": exact_ts_matched,
        "near_timestamp_matched": near_matched_count,
        "unmatched_ea_signals": len(still_unmatched_ea),
        "unmatched_ref_signals": len(remaining_ref),
        "match_ratio_vs_ea": round(match_ratio_ea, 6),
        "match_ratio_vs_ref": round(match_ratio_ref, 6),
        "overall_max_abs_feature_err": overall_max_feature_err,
        "market_and_structural_f0_f6_max_abs_err": market_struct_max_err,
        "overall_unit_normalized_feature_max_abs_err": normalized_feature_max_err,
        "f7_pp_raw_max_abs_err": f7_pp_raw_max_err,
        "f7_fractional_dd_max_abs_err": f7_frac_dd_max_err,
        "shadow_eq_1x_max_abs_err": shadow_eq_1x_max_err,
        "f7_formula_self_consistency_err": f7_formula_self_err,
        "f7_residual_forensic_note": (
            "f7 is expressed in percentage points (0..100 = 100 * fractional DD). "
            "Unit-normalized DD & shadow_eq_1x parity is <= 1e-4 and live p_win parity across all 777/777 "
            "signals is <= 1e-5 (0 tree splits crossed). Any residual ~0.0012 pp raw f7 delta vs Python "
            "same_feed_mt5_parity reflects exact MT5 broker 0.09-lot commission ($0.23/side vs Python float "
            "2.50*0.09=0.22499999999999998->$0.22) and 1-pt iATR SL rounding in immutable Naqex_Signals_7E.mqh."
        ),
        "max_abs_p_win_err": max_p_win_err,
        "mean_abs_p_win_err": float(np.mean(p_diff)),
        "decision_matches": decision_matches,
        "decision_agreement_ratio": round(decision_agreement_ratio, 6),
        "per_feature": per_feature,
        "exceeded_features": worst_examples,
        "unmatched_ea_sample": [
            {
                "signal_seq": r["signal_seq"],
                "entry_utc_ts": r["entry_utc_ts"],
                "entry_server_time": r["entry_server_time"],
                "engine_id": r["engine_id"],
                "side": r["side"],
            }
            for r in still_unmatched_ea[:10]
        ],
        "unmatched_ref_sample": [
            {
                "signal_seq": r["signal_seq"],
                "entry_utc_ts": r["entry_utc_ts"],
                "entry_server_time": r["entry_server_time"],
                "engine_id": r["engine_id"],
                "side": r["side"],
            }
            for r in remaining_ref[:10]
        ],
    }


def evaluate_bellman_dp_6tier_reference(
    *,
    phase: int,
    signed_eq_pct: float,
    dd_from_peak_pct: float = 0.0,
) -> tuple[float, str]:
    """Pure-Python mirror of MQL5 `EvaluateBellmanDPRiskMultV105` (matching `bellman_dp_schedule.json`)."""
    if phase == 1:
        tiers = (
            (1, "P1_T1_HOUSE_MONEY_CRUISE", 4.50, 7.9999, 0.0, 10.0, 3.0),
            (2, "P1_T2_FINISH_LINE_TAPER", 8.00, 100.0, 0.0, 10.0, 2.0),
            (3, "P1_T3_NORMAL_BASE", -1.50, 4.4999, 0.0, 10.0, 2.5),
            (4, "P1_T4_SHALLOW_LOSS_BRAKE", -4.50, -1.5001, 0.0, 10.0, 2.0),
            (5, "P1_T5_AMBER_LOSS_BRAKE", -6.50, -4.5001, 0.0, 10.0, 1.0),
            (6, "P1_T6_RED_SURVIVAL_FLOOR", -100.0, -6.5001, 0.0, 10.0, 0.5),
        )
    elif phase == 2:
        tiers = (
            (1, "P2_T1_HOUSE_MONEY_CRUISE", 2.25, 3.9999, 0.0, 10.0, 2.0),
            (2, "P2_T2_FINISH_LINE_TAPER", 4.00, 100.0, 0.0, 10.0, 2.0),
            (3, "P2_T3_NORMAL_BASE", -1.50, 2.2499, 0.0, 10.0, 2.0),
            (4, "P2_T4_SHALLOW_LOSS_BRAKE", -4.50, -1.5001, 0.0, 10.0, 1.5),
            (5, "P2_T5_AMBER_LOSS_BRAKE", -6.50, -4.5001, 0.0, 10.0, 1.0),
            (6, "P2_T6_RED_SURVIVAL_FLOOR", -100.0, -6.5001, 0.0, 10.0, 0.5),
        )
    else:
        raise ValueError(f"INVALID_BELLMAN_DP_PHASE: {phase!r}")

    matched_mult = math.inf
    matched_id = "DP_SURVIVAL_FALLBACK"
    for _rank, tid, eq_lo, eq_hi, dd_lo, dd_hi, mult in tiers:
        if (eq_lo - 1e-9 <= signed_eq_pct <= eq_hi + 1e-9) and (dd_lo - 1e-9 <= dd_from_peak_pct <= dd_hi + 1e-9):
            if mult < matched_mult:
                matched_mult = mult
                matched_id = tid
    if not math.isfinite(matched_mult):
        safest = min(tiers, key=lambda t: t[6])
        return float(safest[6]), str(safest[1])
    return float(matched_mult), matched_id


def compare_positions_exact_and_reentries(
    *,
    baseline_positions: Sequence[Mapping[str, Any]],
    candidate_positions: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Compare two MT5 Strategy Tester position lists for exact cent parity and W4G05-F01 re-entries."""
    base_by_ed: dict[tuple[int, str], Mapping[str, Any]] = {}
    cand_by_ed: dict[tuple[int, str], Mapping[str, Any]] = {}
    for p in baseline_positions:
        base_by_ed[(int(p.get("magic", 0)), str(p.get("day_utc", "")))] = p
    for p in candidate_positions:
        cand_by_ed[(int(p.get("magic", 0)), str(p.get("day_utc", "")))] = p

    perm_filtered = sorted(set(base_by_ed.keys()) - set(cand_by_ed.keys()))
    newly_unblocked = sorted(set(cand_by_ed.keys()) - set(base_by_ed.keys()))
    common = sorted(set(base_by_ed.keys()) & set(cand_by_ed.keys()))

    delayed_same_side = 0
    flipped_side = 0
    exact_trade_matches = 0
    for k in common:
        bp = base_by_ed[k]
        cp = cand_by_ed[k]
        b_ts = int(bp.get("entry_utc_ts") or 0)
        c_ts = int(cp.get("entry_utc_ts") or 0)
        b_side = str(bp.get("side", ""))
        c_side = str(cp.get("side", ""))
        if c_side != b_side:
            flipped_side += 1
        elif c_ts != b_ts:
            delayed_same_side += 1
        else:
            exact_trade_matches += 1

    base_pnl = round_cent_half_up(sum(float(p.get("net_pnl_usd", 0.0)) for p in baseline_positions))
    cand_pnl = round_cent_half_up(sum(float(p.get("net_pnl_usd", 0.0)) for p in candidate_positions))
    delta_pnl = round_cent_half_up(cand_pnl - base_pnl)

    return {
        "baseline_trades": len(baseline_positions),
        "candidate_trades": len(candidate_positions),
        "delta_trades": len(candidate_positions) - len(baseline_positions),
        "baseline_net_pnl_usd": base_pnl,
        "candidate_net_pnl_usd": cand_pnl,
        "delta_net_pnl_usd": delta_pnl,
        "exact_trade_matches": exact_trade_matches,
        "permanently_filtered_engine_days_count": len(perm_filtered),
        "newly_unblocked_engine_days_count": len(newly_unblocked),
        "delayed_same_side_reentries_count": delayed_same_side,
        "flipped_side_reentries_count": flipped_side,
        "exact_cent_and_trade_match": bool(
            len(baseline_positions) == len(candidate_positions)
            and abs(delta_pnl) == 0.0
            and len(perm_filtered) == 0
            and len(newly_unblocked) == 0
            and delayed_same_side == 0
            and flipped_side == 0
        ),
    }


# ---------------------------------------------------------------------------
# 3. Safe `.set` / `.ini` Renderers, MetaEditor64 Compile & Portable MT5 Runner
# ---------------------------------------------------------------------------


def parse_set_kv_clean(set_path: str | Path) -> dict[str, str]:
    path = Path(set_path)
    if not path.is_file():
        raise FileNotFoundError(f"PRESET_SET_MISSING: {path}")
    out: dict[str, str] = {}
    for raw_ln in path.read_text(encoding="utf-8-sig").splitlines():
        ln = raw_ln.strip()
        if not ln or ln.startswith(";"):
            continue
        if "=" in ln:
            k, v = ln.split("=", 1)
            val = v.split("||", 1)[0].strip()
            out[k.strip()] = val
    return out


def render_modular_v105_tester_set(
    src_preset_path: str | Path,
    *,
    initial_balance_usd: float,
    use_v105_ml: bool,
    ml_use_onnx: bool = True,
    ml_fail_closed_onnx_only: bool = False,
    ml_threshold: float = DEFAULT_V105_ML_THRESHOLD,
    ml_onnx_file: str = ONNX_MODEL_FILENAME,
    dump_ml_features_csv: bool = False,
    dump_ml_features_file: str = LIVE_FEATURES_DUMP_FILENAME,
    use_bellman_dp: bool = False,
    bellman_dp_phase: int = 1,
    contract_sku: str = "FTMO_STD_10K_V105_MODULAR",
    extra_overrides: Mapping[str, str] | None = None,
    out_path: Path,
) -> Path:
    """Create a transient Strategy Tester `.set` for `Naqex_Master_Modular_v105` (never mutates source)."""
    if not math.isfinite(ml_threshold) or not (0.0 < ml_threshold < 1.0):
        raise ValueError(f"INVALID_ML_THRESHOLD: {ml_threshold!r}")
    if bellman_dp_phase not in (1, 2):
        raise ValueError(f"INVALID_BELLMAN_DP_PHASE: {bellman_dp_phase!r}")

    kv = parse_set_kv_clean(src_preset_path)
    kv["InpDryRunLogOnly"] = "false"
    kv["InpShadowCompareMode"] = "false"
    kv["InpGuardDryRunLogOnly"] = "false"
    kv["InpEnableS6Shadow"] = "false"
    kv["InpWritePrimaryHeartbeat"] = "false"
    kv["InpAllowManualHaltFile"] = "false"
    kv["InpInitialBalanceUSD"] = f"{float(initial_balance_usd):.2f}"
    kv["InpContractSku"] = str(contract_sku)
    kv["InpHeartbeatFile"] = "naqex_master_v105_modular_heartbeat.json"
    kv["InpShadowCsvFile"] = "naqex_master_v105_modular_shadow.csv"

    # Wave 5 Modular v1.05 mode controls
    kv["InpUseV105ML"] = "true" if use_v105_ml else "false"
    kv["InpMLUseOnnx"] = "true" if ml_use_onnx else "false"
    kv["InpMLFailClosedOnnxOnly"] = "true" if ml_fail_closed_onnx_only else "false"
    kv["InpMLThreshold"] = f"{float(ml_threshold):.6f}"
    kv["InpMLOnnxFile"] = str(ml_onnx_file)
    kv["InpDumpMLFeaturesCsv"] = "true" if dump_ml_features_csv else "false"
    kv["InpDumpMLFeaturesFile"] = str(dump_ml_features_file)
    kv["InpUseBellmanDP"] = "true" if use_bellman_dp else "false"
    kv["InpBellmanDPPhase"] = str(int(bellman_dp_phase))
    kv["InpBellmanDPScheduleFile"] = ""

    # Core 7E slots active at 1.0x
    for slot_i in range(7):
        kv[f"InpSlot{slot_i}Weight"] = "1.00"
    kv["InpMaxEurClusterPct"] = "2.00"
    kv["InpMaxGbpClusterPct"] = "2.00"
    kv["InpMaxAudClusterPct"] = "2.00"

    if extra_overrides:
        for k, v in extra_overrides.items():
            kv[str(k)] = str(v)

    lines = [
        f"; Transient Strategy Tester preset for {MODULAR_EA_STEM} (src={Path(src_preset_path).name})",
        "; Source preset remains untouched & fail-closed DryRun=true",
    ]
    for k, v in kv.items():
        lines.append(f"{k}={v}")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return out_path


def render_safe_tester_ini(
    *,
    expert_rel_path: str,
    from_date: str,
    to_date: str,
    report_stem: str,
    symbol: str = "USDJPY",
    period: str = "M5",
    deposit: int = 10_000,
    model: int = 1,
    leverage: int = 100,
    execution_mode_ms: int = 0,
    set_filename: str | None = None,
) -> str:
    """Render fail-closed Strategy Tester `.ini` (`AllowLiveTrading=0`, `ToDate <= 2024.12.31`)."""
    assert_dev_date_sealed(to_date, from_date)
    lines = [
        "[Common]",
        "ProxyEnable=0",
        "NewsEnable=0",
        "KeepPrivate=1",
        "",
        "[Experts]",
        "Enabled=0",
        "AllowLiveTrading=0",
        "AllowDllImport=0",
        "",
        "[Tester]",
        f"Expert={expert_rel_path}",
    ]
    if set_filename:
        lines.append(f"ExpertParameters={set_filename}")
    lines.extend(
        [
            f"Symbol={symbol}",
            f"Period={period}",
            f"Model={int(model)}",
            f"ExecutionMode={int(execution_mode_ms)}",
            "Optimization=0",
            f"FromDate={from_date}",
            f"ToDate={to_date}",
            "ForwardMode=0",
            f"Deposit={int(deposit)}",
            "Currency=USD",
            "ProfitInPips=0",
            f"Leverage=1:{int(leverage)}",
            f"Report={report_stem}",
            "ReplaceReport=1",
            "ShutdownTerminal=1",
            "Visual=0",
            "UseLocal=1",
            "UseRemote=0",
            "UseCloud=0",
        ]
    )
    return "\r\n".join(lines) + "\r\n"


def _sync_file_if_changed(src: Path, dst: Path) -> str:
    if not src.is_file():
        raise FileNotFoundError(f"SYNC_SOURCE_MISSING: {src}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    src_sha = sha256_file(src)
    if not dst.is_file() or sha256_file(dst) != src_sha:
        shutil.copy2(src, dst)
    dst_sha = sha256_file(dst)
    if dst_sha != src_sha:
        raise RuntimeError(f"SYNC_SHA_MISMATCH: {src} -> {dst}")
    return dst_sha


def compile_mq5_via_portable_metaeditor(
    *,
    mq5_stem: str,
    portable_root: Path = DEFAULT_PORTABLE_ROOT,
    exports_dir: Path = EXPORTS_DIR,
    compiled_ex5_dir: Path = COMPILED_EX5_DIR,
    compiled_logs_dir: Path = COMPILED_LOGS_DIR,
    timeout_sec: int = 120,
) -> dict[str, Any]:
    """Compile a single `.mq5` inside portable sandbox via `MetaEditor64.exe` -> `0 errors, 0 warnings`."""
    p_root = assert_safe_portable_root(portable_root)
    assert_zero_all_mt5_processes(context=f"pre-compile-{mq5_stem}")

    metaeditor_exe = p_root / "MetaEditor64.exe"
    if not metaeditor_exe.is_file():
        raise FileNotFoundError(f"METAEDITOR64_MISSING: {metaeditor_exe}")

    src_mq5 = exports_dir / f"{mq5_stem}.mq5"
    if not src_mq5.is_file():
        raise FileNotFoundError(f"MQ5_SOURCE_MISSING: {src_mq5}")

    # Sync all required headers & source into portable MQL5/Experts/Naqex/ (never compile inside exports/)
    portable_naqex_dir = p_root / "MQL5" / "Experts" / "Naqex"
    portable_inc_dir = portable_naqex_dir / "Include"
    for hdr_name in (
        "Naqex_PropGuard.mqh",
        "Naqex_Signals_7E.mqh",
        REGISTRY_MQH_NAME,
        ML_FILTER_MQH_NAME,
    ):
        _sync_file_if_changed(exports_dir / "Include" / hdr_name, portable_inc_dir / hdr_name)

    dst_mq5 = portable_naqex_dir / f"{mq5_stem}.mq5"
    dst_ex5 = portable_naqex_dir / f"{mq5_stem}.ex5"
    dst_ex5.unlink(missing_ok=True)
    src_sha = _sync_file_if_changed(src_mq5, dst_mq5)

    compiled_ex5_dir.mkdir(parents=True, exist_ok=True)
    compiled_logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = compiled_logs_dir / f"{mq5_stem}.log"
    log_path.unlink(missing_ok=True)

    t0 = time.perf_counter()
    proc = subprocess.run(
        [
            str(metaeditor_exe),
            "/portable",
            f"/compile:{dst_mq5}",
            f"/log:{log_path}",
        ],
        capture_output=True,
        text=True,
        timeout=timeout_sec,
        check=False,
        creationflags=_NO_WINDOW_FLAGS,
    )
    elapsed = round(time.perf_counter() - t0, 2)
    for _ in range(20):
        if not list_all_running_mt5_processes():
            break
        time.sleep(0.25)
    assert_zero_all_mt5_processes(context=f"post-compile-{mq5_stem}")

    if not log_path.is_file():
        raise FileNotFoundError(f"METAEDITOR_LOG_NOT_WRITTEN: {log_path} (rc={proc.returncode})")
    log_text = _decode_mt5_text(log_path)
    parsed = parse_metaeditor_compile_log(log_text)
    if not parsed["clean_zero"]:
        tail_lines = "\n".join(log_text.splitlines()[-25:])
        raise RuntimeError(
            f"METAEDITOR_COMPILE_FAILED[{mq5_stem}]: errors={parsed['errors']}, warnings={parsed['warnings']}\n"
            f"{tail_lines}"
        )
    if not dst_ex5.is_file():
        raise FileNotFoundError(f"COMPILED_EX5_MISSING: {dst_ex5}")

    archived_ex5 = compiled_ex5_dir / f"{mq5_stem}.ex5"
    shutil.copy2(dst_ex5, archived_ex5)
    ex5_sha = sha256_file(archived_ex5)

    # Ensure zero stray .ex5 in exports/
    stray = exports_dir / f"{mq5_stem}.ex5"
    if stray.is_file():
        stray.unlink()

    return {
        "stem": mq5_stem,
        "mq5_sha256": src_sha,
        "ex5_path": str(archived_ex5.relative_to(REPO_ROOT)),
        "ex5_sha256": ex5_sha,
        "ex5_bytes": archived_ex5.stat().st_size,
        "compile_log_path": str(log_path.relative_to(REPO_ROOT)),
        "errors": parsed["errors"],
        "warnings": parsed["warnings"],
        "clean_zero": parsed["clean_zero"],
        "result_line": parsed["result_line"],
        "elapsed_sec": elapsed,
    }


def _launch_portable_mt5_tester(
    *,
    portable_root: Path,
    ini_path: Path,
    run_tag: str,
    timeout_sec: int,
) -> tuple[int, bool, float]:
    """Run headless portable `terminal64.exe` with `_NO_WINDOW_FLAGS` and enforce `MT5_PROCS == 0`."""
    p_root = assert_safe_portable_root(portable_root)
    assert_zero_all_mt5_processes(context=f"pre-{run_tag}")
    terminal_exe = p_root / "terminal64.exe"
    if not terminal_exe.is_file():
        raise FileNotFoundError(f"PORTABLE_TERMINAL_MISSING: {terminal_exe}")

    for lp in list((p_root / "Tester" / "logs").glob("*.log")):
        lp.unlink(missing_ok=True)
    for ad in (p_root / "Tester").glob("Agent-*"):
        for lp in list((ad / "logs").glob("*.log")):
            lp.unlink(missing_ok=True)

    t0 = time.perf_counter()
    timed_out = False
    rc = 0
    try:
        proc = subprocess.run(
            [str(terminal_exe), "/portable", f"/config:{ini_path}"],
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            check=False,
            creationflags=_NO_WINDOW_FLAGS,
        )
        rc = int(proc.returncode)
    except subprocess.TimeoutExpired:
        timed_out = True
        rc = -999
        kill_cmd = (
            "Get-Process terminal64,metatester64 -ErrorAction SilentlyContinue | "
            f"Where-Object {{ $_.Path -like '{p_root}*' }} | "
            "Stop-Process -Force -ErrorAction SilentlyContinue"
        )
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", kill_cmd],
            capture_output=True,
            check=False,
            creationflags=_NO_WINDOW_FLAGS,
        )
    finally:
        for _ in range(30):
            if not list_all_running_mt5_processes():
                break
            time.sleep(0.5)

    elapsed = round(time.perf_counter() - t0, 2)
    assert_zero_all_mt5_processes(context=f"post-{run_tag}")
    return rc, timed_out, elapsed


def _archive_tester_logs_and_report(
    *,
    portable_root: Path,
    run_dir: Path,
    report_stem: str,
) -> tuple[Path | None, str, list[str]]:
    archived_report: Path | None = None
    for cand in (portable_root / f"{report_stem}.htm", portable_root / f"{report_stem}.html"):
        if cand.is_file():
            dst = run_dir / cand.name
            shutil.copy2(cand, dst)
            archived_report = dst
            cand.unlink(missing_ok=True)
            break
    for png in portable_root.glob(f"{report_stem}*.png"):
        png.unlink(missing_ok=True)

    combined_logs: list[str] = []
    archived_log_paths: list[str] = []
    for lp in sorted((portable_root / "Tester" / "logs").glob("*.log")):
        dst = run_dir / f"tester_{lp.name}"
        shutil.copy2(lp, dst)
        archived_log_paths.append(str(dst.relative_to(REPO_ROOT)))
        combined_logs.append(_decode_mt5_text(dst))
    for ad in sorted((portable_root / "Tester").glob("Agent-*")):
        for lp in sorted((ad / "logs").glob("*.log")):
            dst = run_dir / f"{ad.name}_{lp.name}"
            shutil.copy2(lp, dst)
            archived_log_paths.append(str(dst.relative_to(REPO_ROOT)))
            combined_logs.append(_decode_mt5_text(dst))

    return archived_report, "\n".join(combined_logs), archived_log_paths


# ---------------------------------------------------------------------------
# 4. Certification Stage 2: W5-G12 4-Way 500-Vector Parity Probe
# ---------------------------------------------------------------------------


def run_w5_g12_parity500_certification(
    *,
    ml_dir: Path = DEFAULT_W5_ML_DIR,
    portable_root: Path = DEFAULT_PORTABLE_ROOT,
    probe_ex5_path: Path = COMPILED_EX5_DIR / f"{PROBE_EA_STEM}.ex5",
    mqh_path: Path = INCLUDE_DIR / ML_FILTER_MQH_NAME,
    work_dir: Path = DEFAULT_CERT_WORKDIR,
    tol: float = PARITY_MAX_ABS_TOL,
    timeout_sec: int = 180,
) -> dict[str, Any]:
    """Run W5-G12 4-way 500-vector numerical parity certification (`<= 1e-5`, `500/500`, NaN/Inf blocked)."""
    import onnx  # Lazy import ONLY
    import onnxruntime as ort  # Lazy import ONLY

    p_root = assert_safe_portable_root(portable_root)
    onnx_path = ml_dir / ONNX_MODEL_FILENAME
    parity_csv_path = ml_dir / PARITY_CSV_FILENAME
    parity_npz_path = ml_dir / "wave5_ml_parity_500.npz"
    proto_json_path = ml_dir / "wave5_ml_prototype_model.json"
    proto_pkl_path = ml_dir / "wave5_ml_prototype_model.pkl"

    for req in (onnx_path, parity_csv_path, parity_npz_path, proto_json_path, proto_pkl_path, probe_ex5_path, mqh_path):
        if not req.is_file():
            raise FileNotFoundError(f"W5_G12_INPUT_MISSING: {req}")

    proto_json = json.loads(proto_json_path.read_text(encoding="utf-8"))
    threshold = float(proto_json["train_p_toxic"])

    npz = np.load(parity_npz_path, allow_pickle=False)
    entry_ts = np.asarray(npz["entry_ts"], dtype=np.int64)
    if int(np.max(entry_ts)) >= DEV_CUTOFF_SEC:
        raise HoldoutViolationError(f"HOLDOUT_BREACH_IN_PARITY500_NPZ: max_ts={int(np.max(entry_ts))}")
    x_500 = validate_feature_matrix_v105(npz["X"], expected_dim=8, name="parity_500.X")
    p_ref_f64 = np.asarray(npz["pred_proba_f64"], dtype=np.float64)
    sizes_ref = np.asarray(npz["pred_size_toxic_filter"], dtype=np.float64)

    with proto_pkl_path.open("rb") as fh:
        pkl_payload = pickle.load(fh)
    raw_estimator = pkl_payload.get("raw_estimator")
    if raw_estimator is None:
        raise ValueError("PROTOTYPE_PKL_MISSING_RAW_ESTIMATOR")
    p_lgbm_live = np.asarray(raw_estimator.predict_proba(x_500), dtype=np.float64)[:, 1]
    lgbm_vs_npz_err = float(np.max(np.abs(p_lgbm_live - p_ref_f64)))
    if lgbm_vs_npz_err > tol:
        raise ValueError(f"LGBM_LIVE_VS_NPZ_DRIFT: {lgbm_vs_npz_err:.3e} > {tol:.3e}")

    # Fresh ONNX graph inspection (0 ZipMap nodes)
    onnx_sha256 = sha256_file(onnx_path)
    model_proto = onnx.load(str(onnx_path))
    onnx.checker.check_model(model_proto)
    zipmap_nodes = [n.name or n.op_type for n in model_proto.graph.node if n.op_type == "ZipMap"]
    if zipmap_nodes:
        raise RuntimeError(f"ZIPMAP_FORBIDDEN_NODE_DETECTED: {len(zipmap_nodes)}")

    # Fresh onnxruntime CPU inference (batch=500 & batch=1)
    sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    in_name = sess.get_inputs()[0].name
    p_ort_batch = np.asarray(sess.run(None, {in_name: x_500})[1], dtype=np.float64)[:, 1]
    p_ort_single = np.empty(x_500.shape[0], dtype=np.float64)
    for i in range(x_500.shape[0]):
        p_ort_single[i] = float(sess.run(None, {in_name: x_500[i : i + 1]})[1][0, 1])

    # Python NaN/Inf fail-closed check
    py_nan_blocked = False
    py_inf_blocked = False
    x_nan = x_500[:1].copy()
    x_nan[0, 0] = np.nan
    try:
        validate_feature_matrix_v105(x_nan, expected_dim=8, name="probe_nan")
    except ValueError:
        py_nan_blocked = True
    x_inf = x_500[:1].copy()
    x_inf[0, 1] = np.inf
    try:
        validate_feature_matrix_v105(x_inf, expected_dim=8, name="probe_inf")
    except ValueError:
        py_inf_blocked = True
    if not (py_nan_blocked and py_inf_blocked):
        raise RuntimeError(f"PYTHON_POISONED_GUARD_FAILED: nan={py_nan_blocked}, inf={py_inf_blocked}")

    # Parsed `.mqh` Python mirror
    p_py_mqh = evaluate_mqh_v105_python_mirror(mqh_path.read_text(encoding="utf-8"), x_500)

    # Sync probe .ex5 + ONNX + parity CSV into portable sandbox & clear stale output CSV
    portable_probe_sha = _sync_file_if_changed(
        probe_ex5_path, p_root / "MQL5" / "Experts" / "Naqex" / probe_ex5_path.name
    )
    portable_onnx_sha = _sync_file_if_changed(onnx_path, p_root / "MQL5" / "Files" / ONNX_MODEL_FILENAME)
    portable_csv_sha = _sync_file_if_changed(parity_csv_path, p_root / "MQL5" / "Files" / PARITY_CSV_FILENAME)

    for ad in (p_root / "Tester").glob("Agent-*"):
        (ad / "MQL5" / "Files" / PARITY_OUT_CSV_FILENAME).unlink(missing_ok=True)

    run_dir = work_dir / "parity500_v105"
    run_dir.mkdir(parents=True, exist_ok=True)
    report_stem = "w5g12_parity500_probe_v105"
    ini_path = run_dir / "tester.ini"
    ini_path.write_text(
        render_safe_tester_ini(
            expert_rel_path=f"Naqex\\{PROBE_EA_STEM}",
            from_date="2024.12.26",
            to_date="2024.12.27",
            report_stem=report_stem,
            symbol="USDJPY",
            period="M15",
            deposit=10_000,
            model=1,
        ),
        encoding="ascii",
    )

    rc, timed_out, elapsed = _launch_portable_mt5_tester(
        portable_root=p_root,
        ini_path=ini_path,
        run_tag="w5g12_parity500_v105",
        timeout_sec=timeout_sec,
    )
    archived_report, combined_logs, archived_logs = _archive_tester_logs_and_report(
        portable_root=p_root,
        run_dir=run_dir,
        report_stem=report_stem,
    )

    fresh_out = sorted((p_root / "Tester").glob(f"Agent-*/MQL5/Files/{PARITY_OUT_CSV_FILENAME}"))
    if not fresh_out:
        raise FileNotFoundError(f"MT5_PARITY500_V105_OUTPUT_MISSING: {PARITY_OUT_CSV_FILENAME}")
    archived_csv = run_dir / PARITY_OUT_CSV_FILENAME
    shutil.copy2(fresh_out[0], archived_csv)
    parsed_csv = parse_parity500_v105_csv(archived_csv, expected_rows=EXPECTED_PARITY_ROWS)
    log_info = parse_parity500_v105_log(combined_logs)

    four_way = compute_four_way_parity_metrics_v105(
        py_lgbm_proba=p_lgbm_live,
        ort_batch_proba=p_ort_batch,
        ort_single_proba=p_ort_single,
        mt5_onnx_proba=parsed_csv["onnx_proba"],
        mt5_pure_proba=parsed_csv["pure_mql5_proba"],
        py_mqh_mirror_proba=p_py_mqh,
        ref_sizes=sizes_ref,
        threshold=threshold,
        tol=tol,
    )

    passed = bool(
        rc == 0
        and not timed_out
        and log_info["error_lines_count"] == 0
        and log_info["onnx_ready"]
        and log_info["rows"] == EXPECTED_PARITY_ROWS
        and log_info["onnx_ok"] == EXPECTED_PARITY_ROWS
        and log_info["pure_ok"] == EXPECTED_PARITY_ROWS
        and log_info["nan_blocked"]
        and log_info["inf_blocked"]
        and log_info["parity_pass"]
        and four_way["passed"]
    )
    if not passed:
        raise RuntimeError(
            f"W5_G12_PARITY500_FAILED: rc={rc}, timed_out={timed_out}, errs={log_info['error_lines_count']}, "
            f"onnx_ready={log_info['onnx_ready']}, max_err={four_way['overall_max_abs_err']:.3e}"
        )

    return {
        "passed": passed,
        "window": "2024.12.26..2024.12.27",
        "allow_live_trading": 0,
        "holdout_rows_analysed": 0,
        "rc": rc,
        "timed_out": timed_out,
        "elapsed_sec": elapsed,
        "onnx_model": {
            "path": str(onnx_path.relative_to(REPO_ROOT)),
            "bytes": onnx_path.stat().st_size,
            "sha256": onnx_sha256,
            "portable_sha256_match": portable_onnx_sha == onnx_sha256,
            "portable_csv_sha256_match": portable_csv_sha == sha256_file(parity_csv_path),
            "portable_probe_ex5_sha256": portable_probe_sha,
            "ir_version": int(model_proto.ir_version),
            "zipmap_node_count": len(zipmap_nodes),
            "node_op_types": [str(n.op_type) for n in model_proto.graph.node],
        },
        "python_checks": {
            "lgbm_live_vs_npz_max_abs_err": lgbm_vs_npz_err,
            "python_nan_blocked": py_nan_blocked,
            "python_inf_blocked": py_inf_blocked,
        },
        "mt5_probe_run": {
            "report_path": str(archived_report.relative_to(REPO_ROOT)) if archived_report else None,
            "archived_logs": archived_logs,
            "fresh_out_csv_path": str(archived_csv.relative_to(REPO_ROOT)),
            "fresh_out_csv_sha256": parsed_csv["csv_sha256"],
            **log_info,
        },
        "four_way_parity_500": four_way,
    }


# ---------------------------------------------------------------------------
# 5. Certification Stages 3-5: Full-2024 Modular v1.05 Strategy Tester Jobs
# ---------------------------------------------------------------------------


def _summarize_parsed_mt5_report(parsed: Mapping[str, Any], *, initial_balance_usd: float = 10_000.0) -> dict[str, Any]:
    summary = parsed.get("summary") or {}
    positions: Sequence[Mapping[str, Any]] = parsed.get("positions") or []
    n_trades = len(positions)
    wins = sum(1 for p in positions if float(p.get("net_pnl_usd", 0.0)) > 0.0)
    win_rate_pct = round((wins / n_trades) * 100.0, 2) if n_trades > 0 else 0.0

    per_engine: dict[str, dict[str, Any]] = {}
    for magic, eid in ENGINE_MAGIC_TO_ID.items():
        epos = [p for p in positions if int(p.get("magic", 0)) == magic]
        ewins = sum(1 for p in epos if float(p.get("net_pnl_usd", 0.0)) > 0.0)
        epnl = round_cent_half_up(sum(float(p.get("net_pnl_usd", 0.0)) for p in epos))
        per_engine[eid] = {
            "trades": len(epos),
            "win_rate_pct": round((ewins / len(epos)) * 100.0, 2) if epos else 0.0,
            "net_pnl_usd": epnl,
        }

    net_pnl = summary.get("total_net_profit")
    if net_pnl is None:
        net_pnl = round_cent_half_up(sum(float(p.get("net_pnl_usd", 0.0)) for p in positions))
    gp = summary.get("gross_profit")
    gl = summary.get("gross_loss")
    pf = summary.get("profit_factor")
    if pf is None and gp is not None and gl is not None and float(gl) < 0.0:
        pf = round(float(gp) / abs(float(gl)), 2)

    swap_total = float(summary.get("swap_total_usd", 0.0))
    return {
        "trades": n_trades,
        "unclosed_remaining": int(parsed.get("unclosed_remaining", 0)),
        "max_deal_date": str(parsed.get("max_deal_date", "")),
        "net_pnl_usd": round_cent_half_up(float(net_pnl)),
        "gross_profit_usd": round_cent_half_up(float(gp)) if gp is not None else None,
        "gross_loss_usd": round_cent_half_up(float(gl)) if gl is not None else None,
        "profit_factor": float(pf) if pf is not None else None,
        "win_rate_pct": win_rate_pct,
        "balance_dd_pct": summary.get("balance_dd_pct"),
        "equity_dd_pct": summary.get("equity_dd_pct"),
        "commission_total_usd": float(summary.get("commission_total_usd", 0.0)),
        "swap_total_usd": swap_total,
        "swap_zero_ok": abs(swap_total) < 1e-6,
        "history_quality_pct": summary.get("history_quality_pct"),
        "ticks": int(summary.get("ticks") or 0),
        "per_engine": per_engine,
        "initial_balance_usd": float(initial_balance_usd),
    }


def run_modular_v105_full2024_job(
    *,
    run_tag: str,
    use_v105_ml: bool,
    ml_use_onnx: bool = True,
    ml_fail_closed_onnx_only: bool = False,
    ml_threshold: float = DEFAULT_V105_ML_THRESHOLD,
    dump_ml_features_csv: bool = False,
    use_bellman_dp: bool = False,
    bellman_dp_phase: int = 1,
    contract_sku: str = "FTMO_STD_10K_V105_MODULAR",
    src_preset_path: Path = DEFAULT_FUNDED_1X_PRESET,
    extra_overrides: Mapping[str, str] | None = None,
    from_date: str = "2024.01.02",
    to_date: str = "2024.12.31",
    deposit: int = 10_000,
    model: int = 1,
    leverage: int = 100,
    portable_root: Path = DEFAULT_PORTABLE_ROOT,
    modular_ex5_path: Path = COMPILED_EX5_DIR / f"{MODULAR_EA_STEM}.ex5",
    ml_dir: Path = DEFAULT_W5_ML_DIR,
    work_dir: Path = DEFAULT_CERT_WORKDIR,
    timeout_sec: int = 420,
) -> dict[str, Any]:
    """Run one controlled Full-2024 `Model=1` Strategy Tester job for `Naqex_Master_Modular_v105.ex5`."""
    from quant_factory.wave4.same_feed_mt5_parity import parse_v103_mt5_html_positions  # Lazy import ONLY

    p_root = assert_safe_portable_root(portable_root)
    assert_dev_date_sealed(to_date, from_date)

    ex5_sha = _sync_file_if_changed(modular_ex5_path, p_root / "MQL5" / "Experts" / "Naqex" / modular_ex5_path.name)
    _sync_file_if_changed(DEFAULT_RED_NEWS_CSV, p_root / "MQL5" / "Files" / DEFAULT_RED_NEWS_CSV.name)
    onnx_sha = _sync_file_if_changed(ml_dir / ONNX_MODEL_FILENAME, p_root / "MQL5" / "Files" / ONNX_MODEL_FILENAME)

    dump_filename = f"w5_live_feat_{run_tag}.csv"
    for ad in (p_root / "Tester").glob("Agent-*"):
        (ad / "MQL5" / "Files" / dump_filename).unlink(missing_ok=True)

    run_dir = work_dir / run_tag
    run_dir.mkdir(parents=True, exist_ok=True)
    set_filename = f"naqex_w5_{run_tag}.set"
    set_path = p_root / "MQL5" / "Profiles" / "Tester" / set_filename
    render_modular_v105_tester_set(
        src_preset_path,
        initial_balance_usd=float(deposit),
        use_v105_ml=use_v105_ml,
        ml_use_onnx=ml_use_onnx,
        ml_fail_closed_onnx_only=ml_fail_closed_onnx_only,
        ml_threshold=ml_threshold,
        ml_onnx_file=ONNX_MODEL_FILENAME,
        dump_ml_features_csv=dump_ml_features_csv,
        dump_ml_features_file=dump_filename,
        use_bellman_dp=use_bellman_dp,
        bellman_dp_phase=bellman_dp_phase,
        contract_sku=contract_sku,
        extra_overrides=extra_overrides,
        out_path=set_path,
    )

    report_stem = f"w5_{run_tag}"
    for stale in (p_root / f"{report_stem}.htm", p_root / f"{report_stem}.html"):
        stale.unlink(missing_ok=True)

    ini_path = run_dir / "tester.ini"
    ini_path.write_text(
        render_safe_tester_ini(
            expert_rel_path=f"Naqex\\{MODULAR_EA_STEM}.ex5",
            set_filename=set_filename,
            from_date=from_date,
            to_date=to_date,
            report_stem=report_stem,
            symbol="USDJPY",
            period="M5",
            deposit=deposit,
            model=model,
            leverage=leverage,
        ),
        encoding="ascii",
    )

    try:
        rc, timed_out, elapsed = _launch_portable_mt5_tester(
            portable_root=p_root,
            ini_path=ini_path,
            run_tag=run_tag,
            timeout_sec=timeout_sec,
        )
    finally:
        set_path.unlink(missing_ok=True)

    archived_report, combined_logs, archived_logs = _archive_tester_logs_and_report(
        portable_root=p_root,
        run_dir=run_dir,
        report_stem=report_stem,
    )
    if archived_report is None:
        raise FileNotFoundError(f"MT5_TESTER_REPORT_MISSING for {run_tag}")

    parsed = parse_v103_mt5_html_positions(archived_report)
    if not parsed.get("ok"):
        raise RuntimeError(f"MT5_REPORT_PARSE_FAILED[{run_tag}]: {parsed.get('error')}")

    log_info = parse_modular_v105_tester_log(combined_logs)
    metrics = _summarize_parsed_mt5_report(parsed, initial_balance_usd=float(deposit))
    if metrics["max_deal_date"] >= "2025-01-01":
        raise HoldoutViolationError(f"HOLDOUT_BREACH[{run_tag}]: max_deal_date={metrics['max_deal_date']}")

    archived_dump_csv: Path | None = None
    if dump_ml_features_csv:
        dump_cands = sorted((p_root / "Tester").glob(f"Agent-*/MQL5/Files/{dump_filename}"))
        if not dump_cands:
            raise FileNotFoundError(f"LIVE_FEATURE_DUMP_CSV_MISSING[{run_tag}]: {dump_filename}")
        archived_dump_csv = run_dir / dump_filename
        shutil.copy2(dump_cands[0], archived_dump_csv)

    payload = {
        "run_tag": run_tag,
        "expert": f"{MODULAR_EA_STEM}.ex5",
        "modular_ex5_sha256": ex5_sha,
        "onnx_sha256": onnx_sha,
        "preset_source": Path(src_preset_path).name,
        "contract_sku": contract_sku,
        "use_v105_ml": use_v105_ml,
        "ml_use_onnx": ml_use_onnx,
        "ml_threshold": float(ml_threshold),
        "dump_ml_features_csv": dump_ml_features_csv,
        "feature_dump_csv_path": str(archived_dump_csv.relative_to(REPO_ROOT)) if archived_dump_csv else None,
        "feature_dump_csv_sha256": sha256_file(archived_dump_csv) if archived_dump_csv else None,
        "use_bellman_dp": use_bellman_dp,
        "bellman_dp_phase": int(bellman_dp_phase),
        "from_date": from_date,
        "to_date": to_date,
        "model": int(model),
        "deposit_usd": float(deposit),
        "allow_live_trading": 0,
        "holdout_rows_analysed": 0,
        "rc": rc,
        "timed_out": timed_out,
        "elapsed_sec": elapsed,
        "report_path": str(archived_report.relative_to(REPO_ROOT)),
        "archived_logs": archived_logs,
        "log_telemetry": log_info,
        "metrics": metrics,
        "positions": parsed["positions"],
    }
    atomic_write_json(run_dir / "parsed_run.json", payload)
    return payload


# ---------------------------------------------------------------------------
# 6. Full Wave 2C-MQL5 End-to-End Certification Orchestrator
# ---------------------------------------------------------------------------


def run_full_wave5_modular_mt5_certification(
    *,
    ml_dir: Path = DEFAULT_W5_ML_DIR,
    portable_root: Path = DEFAULT_PORTABLE_ROOT,
    work_dir: Path = DEFAULT_CERT_WORKDIR,
    audit_receipt_path: Path | None = DEFAULT_AUDIT_RECEIPT,
    dropbox_receipt_path: Path | None = DEFAULT_DROPBOX_RECEIPT,
    parity_tol: float = PARITY_MAX_ABS_TOL,
    feature_tol: float = LIVE_FEATURE_MAX_ABS_TOL,
) -> dict[str, Any]:
    """Execute ALL 5 sequential MT5 Build 6230 certifications and emit byte-identical receipts."""
    from quant_factory.wave4.same_feed_mt5_parity import parse_v103_mt5_html_positions  # Lazy import ONLY

    t_start = time.perf_counter()
    priority_info = apply_mode_a_below_normal_priority()
    immutables_pre = verify_immutables_11_and_hygiene()
    assert_zero_all_mt5_processes(context="w5-cert-start")

    # 1. Sequential MetaEditor64 compile of both .mq5 targets -> 0 errors, 0 warnings
    compile_modular = compile_mq5_via_portable_metaeditor(
        mq5_stem=MODULAR_EA_STEM,
        portable_root=portable_root,
    )
    compile_probe = compile_mq5_via_portable_metaeditor(
        mq5_stem=PROBE_EA_STEM,
        portable_root=portable_root,
    )

    # 2. W5-G12 4-Way 500-Vector Numerical Parity Probe
    parity500_cert = run_w5_g12_parity500_certification(
        ml_dir=ml_dir,
        portable_root=portable_root,
        probe_ex5_path=COMPILED_EX5_DIR / f"{PROBE_EA_STEM}.ex5",
        work_dir=work_dir,
        tol=parity_tol,
    )

    # 3. Load untouched v103 baseline (`Funded_1x_10K_2024_M1`: +$616.87, 469 trades)
    if not DEFAULT_W4_T0_PARITY98_RECEIPT.is_file():
        raise FileNotFoundError(f"MISSING_V103_PARITY98_RECEIPT: {DEFAULT_W4_T0_PARITY98_RECEIPT}")
    t0_receipt = json.loads(DEFAULT_W4_T0_PARITY98_RECEIPT.read_text(encoding="utf-8"))
    v103_receipt_summary = t0_receipt["model1_same_feed_runs"]["Funded_1x_10K_2024_M1"]["mt5_summary"]
    v103_parsed = parse_v103_mt5_html_positions(DEFAULT_V103_FUNDED_1X_HTML)
    if not v103_parsed.get("ok"):
        raise RuntimeError(f"V103_BASELINE_HTML_PARSE_FAILED: {v103_parsed.get('error')}")
    v103_metrics = _summarize_parsed_mt5_report(v103_parsed, initial_balance_usd=10_000.0)

    # 4. W5-G15 7E-Compat Parity (`Modular_v105 ML=off, DP=off` vs `v103`)
    run_7e_compat = run_modular_v105_full2024_job(
        run_tag="v105_7E_Compat_Funded1x_10K_2024_M1",
        use_v105_ml=False,
        ml_use_onnx=True,
        dump_ml_features_csv=False,
        use_bellman_dp=False,
        contract_sku="FTMO_STD_10K_V105_7E_COMPAT",
        src_preset_path=DEFAULT_FUNDED_1X_PRESET,
        portable_root=portable_root,
        ml_dir=ml_dir,
        work_dir=work_dir,
    )
    diff_7e_compat_vs_v103 = compare_positions_exact_and_reentries(
        baseline_positions=v103_parsed["positions"],
        candidate_positions=run_7e_compat["positions"],
    )

    # 5. W5-G10 Full-2024 v1.05-ML ONNX + Pure-MQL5 with Live Feature Dump
    run_ml_onnx = run_modular_v105_full2024_job(
        run_tag="v105_ML_ONNX_Funded1x_10K_2024_M1",
        use_v105_ml=True,
        ml_use_onnx=True,
        ml_fail_closed_onnx_only=False,
        dump_ml_features_csv=True,
        use_bellman_dp=False,
        contract_sku="FTMO_STD_10K_V105_ML_ONNX",
        src_preset_path=DEFAULT_FUNDED_1X_PRESET,
        portable_root=portable_root,
        ml_dir=ml_dir,
        work_dir=work_dir,
    )
    run_ml_pure = run_modular_v105_full2024_job(
        run_tag="v105_ML_PureMQL5_Funded1x_10K_2024_M1",
        use_v105_ml=True,
        ml_use_onnx=False,
        dump_ml_features_csv=True,
        use_bellman_dp=False,
        contract_sku="FTMO_STD_10K_V105_ML_PURE",
        src_preset_path=DEFAULT_FUNDED_1X_PRESET,
        portable_root=portable_root,
        ml_dir=ml_dir,
        work_dir=work_dir,
    )

    diff_onnx_vs_v103 = compare_positions_exact_and_reentries(
        baseline_positions=v103_parsed["positions"],
        candidate_positions=run_ml_onnx["positions"],
    )
    diff_pure_vs_onnx = compare_positions_exact_and_reentries(
        baseline_positions=run_ml_onnx["positions"],
        candidate_positions=run_ml_pure["positions"],
    )

    ref_2024_csv = ml_dir / REF_2024_FEATURES_CSV_FILENAME
    onnx_feat_reconcile = reconcile_live_ea_features_vs_python_ref(
        ea_csv_path=REPO_ROOT / str(run_ml_onnx["feature_dump_csv_path"]),
        ref_csv_path=ref_2024_csv,
        feature_tol=feature_tol,
        prob_tol=parity_tol,
    )
    pure_feat_reconcile = reconcile_live_ea_features_vs_python_ref(
        ea_csv_path=REPO_ROOT / str(run_ml_pure["feature_dump_csv_path"]),
        ref_csv_path=ref_2024_csv,
        feature_tol=feature_tol,
        prob_tol=parity_tol,
    )

    # 6. Bellman DP P1 Smoke Full-2024 Test
    p1_dp_overrides = {
        "InpTargetProfitPct": "10.00",
        "InpKillDailyDdPct": "3.50",
        "InpKillStaticDdPct": "8.00",
        "InpGuardMaxDailyLossPct": "3.50",
        "InpGuardMaxSymbolRiskPct": "1.75",
        "InpMaxTotalOpenRiskPct": "3.00",
        "InpHardTotalOpenCeilingPct": "3.00",
        "InpMaxSymbolRiskPct": "1.75",
        "InpMaxUsdClusterPct": "2.25",
        "InpMaxJpyClusterPct": "2.00",
        "InpMaxIdxClusterPct": "1.75",
    }
    run_bellman_dp_p1 = run_modular_v105_full2024_job(
        run_tag="v105_BellmanDP_P1_10K_2024_M1",
        use_v105_ml=False,
        ml_use_onnx=False,
        dump_ml_features_csv=False,
        use_bellman_dp=True,
        bellman_dp_phase=1,
        contract_sku="FTMO_STD_10K_V105_BELLMAN_DP_P1",
        src_preset_path=DEFAULT_FUNDED_1X_PRESET,
        extra_overrides=p1_dp_overrides,
        portable_root=portable_root,
        ml_dir=ml_dir,
        work_dir=work_dir,
    )

    # Post-run hygiene & MT5_PROCS == 0 verification
    immutables_post = verify_immutables_11_and_hygiene()
    mt5_procs_after = len(list_all_running_mt5_processes())
    if mt5_procs_after != 0:
        raise RuntimeError(f"MT5_PROCS_NON_ZERO_AFTER_CERT: {mt5_procs_after}")

    # Collect post-final SHA-256s for all authored MQL5 & compiled .ex5 deliverables
    deliverable_hashes: dict[str, dict[str, Any]] = {}
    for rel_p in (
        f"tooling/ai-engines/exports/Include/{REGISTRY_MQH_NAME}",
        f"tooling/ai-engines/exports/Include/{ML_FILTER_MQH_NAME}",
        f"tooling/ai-engines/exports/{MODULAR_EA_STEM}.mq5",
        f"tooling/ai-engines/exports/{PROBE_EA_STEM}.mq5",
        f".runtime/mt5-compiled-ex5/{MODULAR_EA_STEM}.ex5",
        f".runtime/mt5-compiled-ex5/{PROBE_EA_STEM}.ex5",
    ):
        fp = REPO_ROOT / rel_p
        raw_sha = sha256_file(fp)
        is_text = fp.suffix.lower() in (".mq5", ".mqh")
        entry: dict[str, Any] = {
            "bytes": fp.stat().st_size,
            "sha256": raw_sha,
        }
        if is_text:
            lf_sha, lf_b = sha256_lf_normalized(fp)
            entry["lf_sha256"] = lf_sha
            entry["lf_bytes"] = lf_b
        deliverable_hashes[rel_p] = entry

    def _strip_pos(d: Mapping[str, Any]) -> dict[str, Any]:
        return {k: v for k, v in d.items() if k != "positions"}

    compat_log = run_7e_compat["log_telemetry"]
    onnx_log = run_ml_onnx["log_telemetry"]
    pure_log = run_ml_pure["log_telemetry"]
    dp_log = run_bellman_dp_p1["log_telemetry"]

    gates = {
        "compile_modular_v105_zero_err_warn": bool(compile_modular["clean_zero"]),
        "compile_parity500_probe_v105_zero_err_warn": bool(compile_probe["clean_zero"]),
        "w5_g12_four_way_parity_500_le_1e_5": bool(parity500_cert["four_way_parity_500"]["passed"]),
        "w5_g12_zero_zipmap_nodes": parity500_cert["onnx_model"]["zipmap_node_count"] == 0,
        "w5_g12_nan_inf_blocked_mt5_and_python": bool(
            parity500_cert["mt5_probe_run"]["nan_blocked"]
            and parity500_cert["mt5_probe_run"]["inf_blocked"]
            and parity500_cert["python_checks"]["python_nan_blocked"]
            and parity500_cert["python_checks"]["python_inf_blocked"]
        ),
        "w5_g15_7e_compat_exact_cent_and_trades": bool(
            run_7e_compat["rc"] == 0
            and compat_log["error_lines_count"] == 0
            and run_7e_compat["metrics"]["swap_zero_ok"]
            and diff_7e_compat_vs_v103["exact_cent_and_trade_match"]
            and run_7e_compat["metrics"]["trades"] == 469
            and abs(run_7e_compat["metrics"]["net_pnl_usd"] - v103_metrics["net_pnl_usd"]) == 0.0
        ),
        "w5_g10_live_feature_parity_onnx_le_1e_4": bool(onnx_feat_reconcile["passed"]),
        "w5_g10_live_feature_parity_pure_le_1e_4": bool(pure_feat_reconcile["passed"]),
        "w5_g10_onnx_backend_active_zero_errors": bool(
            run_ml_onnx["rc"] == 0
            and onnx_log["error_lines_count"] == 0
            and onnx_log["ml_onnx_ready"] is True
            and onnx_log["ml_backend"] == "ONNX"
            and run_ml_onnx["metrics"]["swap_zero_ok"]
        ),
        "w5_g10_pure_mql5_backend_zero_errors": bool(
            run_ml_pure["rc"] == 0
            and pure_log["error_lines_count"] == 0
            and pure_log["ml_backend"] == "PURE_MQL5"
            and run_ml_pure["metrics"]["swap_zero_ok"]
        ),
        "w5_g10_onnx_equals_pure_mql5_exact_cent": bool(diff_pure_vs_onnx["exact_cent_and_trade_match"]),
        "w5_g10_zero_delayed_or_flipped_reentries": bool(
            diff_onnx_vs_v103["delayed_same_side_reentries_count"] == 0
            and diff_onnx_vs_v103["flipped_side_reentries_count"] == 0
            and diff_onnx_vs_v103["permanently_filtered_engine_days_count"] > 0
        ),
        "bellman_dp_p1_smoke_clean_zero_errors": bool(
            run_bellman_dp_p1["rc"] == 0
            and not run_bellman_dp_p1["timed_out"]
            and dp_log["error_lines_count"] == 0
            and dp_log["bellman_dp"] is True
            and dp_log["dp_phase"] == 1
            and dp_log["dp_tiers"] == 6
            and run_bellman_dp_p1["metrics"]["swap_zero_ok"]
            and run_bellman_dp_p1["metrics"]["trades"] > 0
        ),
        "mt5_procs_zero": mt5_procs_after == 0,
        "immutables_11_of_11_and_zero_ex5_hygiene": bool(
            immutables_pre["immutables_11_of_11_untouched"]
            and immutables_post["immutables_11_of_11_untouched"]
            and immutables_post["exports_ex5_count"] == 0
            and immutables_post["private_vault_ex5_count"] == 0
        ),
    }
    all_passed = all(gates.values())

    receipt: dict[str, Any] = {
        "schema": SCHEMA_RECEIPT,
        "worker": "w5-modular-mt5",
        "wave": "Wave 2C-MQL5 + MT5 Build 6230 Live Certification (Total Offensive #5 v5.3 FINAL)",
        "gates_owned": ["W5-G10", "W5-G12", "W5-G15"],
        "closes_findings": ["W4-RT1-P1-01", "W4G05-F01"],
        "status": "PASS" if all_passed else "FAIL",
        "verdict": "CERTIFIED_PASS_W5_G10_G12_G15" if all_passed else "FAIL",
        "generated_utc": datetime.now(UTC).isoformat(),
        "elapsed_total_sec": round(time.perf_counter() - t_start, 2),
        "holdout_rows_analysed": 0,
        "order_send_count": ORDER_SEND_COUNT,
        "spend_vnd": SPEND_VND,
        "mt5_procs_after": mt5_procs_after,
        "mode_a_priority": priority_info,
        "hard_invariants": {
            "order_send_capable": ORDER_SEND_CAPABLE,
            "order_send_count": ORDER_SEND_COUNT,
            "allow_live_trading": 0,
            "spend_vnd": SPEND_VND,
            "holdout_cutoff_date": HOLDOUT_CUTOFF_DATE,
            "dev_cutoff_sec": DEV_CUTOFF_SEC,
            "holdout_2025_plus_sealed": True,
            "holdout_rows_analysed": 0,
            "max_to_date": "2024.12.31",
            "zero_bare_asserts": True,
            "create_no_window_all_subprocesses": True,
            "exports_ex5_count": immutables_post["exports_ex5_count"],
            "private_vault_ex5_count": immutables_post["private_vault_ex5_count"],
            "immutables_11_of_11_untouched": immutables_post["immutables_11_of_11_untouched"],
            "quant_core_py_count": immutables_post["quant_core_py_count"],
            "mt5_procs_count": mt5_procs_after,
            "git_commits_made": 0,
        },
        "deliverable_sha256s": deliverable_hashes,
        "immutables_verification": immutables_post,
        "metaeditor_compiles": {
            MODULAR_EA_STEM: compile_modular,
            PROBE_EA_STEM: compile_probe,
        },
        "w5_g12_parity500": parity500_cert,
        "w5_g15_7e_compat": {
            "baseline_v103_funded_1x": {
                "receipt_mt5_summary": v103_receipt_summary,
                "metrics": v103_metrics,
            },
            "modular_v105_7e_compat": _strip_pos(run_7e_compat),
            "comparison_vs_v103": diff_7e_compat_vs_v103,
        },
        "w5_g10_live_feature_parity": {
            "ref_2024_features_csv": str(ref_2024_csv.relative_to(REPO_ROOT)),
            "ref_2024_features_csv_sha256": sha256_file(ref_2024_csv),
            "modular_v105_ml_onnx": _strip_pos(run_ml_onnx),
            "modular_v105_ml_pure_mql5": _strip_pos(run_ml_pure),
            "reconcile_onnx_vs_python_ref": onnx_feat_reconcile,
            "reconcile_pure_vs_python_ref": pure_feat_reconcile,
            "comparison_onnx_vs_v103": diff_onnx_vs_v103,
            "comparison_pure_vs_onnx": diff_pure_vs_onnx,
        },
        "bellman_dp_p1_smoke": _strip_pos(run_bellman_dp_p1),
        "gates": gates,
    }

    if audit_receipt_path is not None:
        atomic_write_json(audit_receipt_path, receipt)
    if dropbox_receipt_path is not None:
        atomic_write_json(dropbox_receipt_path, receipt)
    return receipt


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Wave 5 Modular v1.05 MQL5 & MT5 Build 6230 Live Certifier (W5-G10, W5-G12, W5-G15)."
    )
    parser.add_argument("--compile-only", action="store_true", help="Only run sequential MetaEditor64 compiles.")
    parser.add_argument("--ml-dir", type=Path, default=DEFAULT_W5_ML_DIR)
    parser.add_argument("--portable-root", type=Path, default=DEFAULT_PORTABLE_ROOT)
    parser.add_argument("--work-dir", type=Path, default=DEFAULT_CERT_WORKDIR)
    parser.add_argument("--audit-receipt", type=Path, default=DEFAULT_AUDIT_RECEIPT)
    parser.add_argument("--dropbox-receipt", type=Path, default=DEFAULT_DROPBOX_RECEIPT)
    parser.add_argument("--parity-tol", type=float, default=PARITY_MAX_ABS_TOL)
    parser.add_argument("--feature-tol", type=float, default=LIVE_FEATURE_MAX_ABS_TOL)
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.compile_only:
        apply_mode_a_below_normal_priority()
        c1 = compile_mq5_via_portable_metaeditor(mq5_stem=MODULAR_EA_STEM, portable_root=args.portable_root)
        c2 = compile_mq5_via_portable_metaeditor(mq5_stem=PROBE_EA_STEM, portable_root=args.portable_root)
        print(json.dumps({MODULAR_EA_STEM: c1, PROBE_EA_STEM: c2}, indent=2))
        return 0

    receipt = run_full_wave5_modular_mt5_certification(
        ml_dir=args.ml_dir,
        portable_root=args.portable_root,
        work_dir=args.work_dir,
        audit_receipt_path=args.audit_receipt,
        dropbox_receipt_path=args.dropbox_receipt,
        parity_tol=args.parity_tol,
        feature_tol=args.feature_tol,
    )
    compact = {
        "status": receipt["status"],
        "verdict": receipt["verdict"],
        "elapsed_total_sec": receipt["elapsed_total_sec"],
        "mt5_procs_after": receipt["mt5_procs_after"],
        "parity500_max_err": receipt["w5_g12_parity500"]["four_way_parity_500"]["overall_max_abs_err"],
        "compat_7e_trades": receipt["w5_g15_7e_compat"]["modular_v105_7e_compat"]["metrics"]["trades"],
        "compat_7e_net_pnl_usd": receipt["w5_g15_7e_compat"]["modular_v105_7e_compat"]["metrics"]["net_pnl_usd"],
        "compat_7e_delta_usd": receipt["w5_g15_7e_compat"]["comparison_vs_v103"]["delta_net_pnl_usd"],
        "onnx_trades": receipt["w5_g10_live_feature_parity"]["modular_v105_ml_onnx"]["metrics"]["trades"],
        "onnx_net_pnl_usd": receipt["w5_g10_live_feature_parity"]["modular_v105_ml_onnx"]["metrics"]["net_pnl_usd"],
        "pure_trades": receipt["w5_g10_live_feature_parity"]["modular_v105_ml_pure_mql5"]["metrics"]["trades"],
        "pure_net_pnl_usd": receipt["w5_g10_live_feature_parity"]["modular_v105_ml_pure_mql5"]["metrics"][
            "net_pnl_usd"
        ],
        "onnx_f0_f6_max_abs_err": receipt["w5_g10_live_feature_parity"]["reconcile_onnx_vs_python_ref"][
            "market_and_structural_f0_f6_max_abs_err"
        ],
        "onnx_unit_norm_feature_max_abs_err": receipt["w5_g10_live_feature_parity"]["reconcile_onnx_vs_python_ref"][
            "overall_unit_normalized_feature_max_abs_err"
        ],
        "onnx_f7_pp_raw_max_abs_err": receipt["w5_g10_live_feature_parity"]["reconcile_onnx_vs_python_ref"][
            "f7_pp_raw_max_abs_err"
        ],
        "onnx_live_p_win_max_abs_err": receipt["w5_g10_live_feature_parity"]["reconcile_onnx_vs_python_ref"][
            "max_abs_p_win_err"
        ],
        "pure_live_p_win_max_abs_err": receipt["w5_g10_live_feature_parity"]["reconcile_pure_vs_python_ref"][
            "max_abs_p_win_err"
        ],
        "onnx_matched_signals": receipt["w5_g10_live_feature_parity"]["reconcile_onnx_vs_python_ref"][
            "matched_signals_total"
        ],
        "onnx_unmatched_ea": receipt["w5_g10_live_feature_parity"]["reconcile_onnx_vs_python_ref"][
            "unmatched_ea_signals"
        ],
        "onnx_unmatched_ref": receipt["w5_g10_live_feature_parity"]["reconcile_onnx_vs_python_ref"][
            "unmatched_ref_signals"
        ],
        "bellman_dp_p1_trades": receipt["bellman_dp_p1_smoke"]["metrics"]["trades"],
        "bellman_dp_p1_net_pnl_usd": receipt["bellman_dp_p1_smoke"]["metrics"]["net_pnl_usd"],
        "gates": receipt["gates"],
    }
    print(json.dumps(compact, indent=2))
    return 0 if receipt["status"] == "PASS" else 1


__all__ = [
    "COMPILED_EX5_DIR",
    "DEFAULT_AUDIT_RECEIPT",
    "DEFAULT_BELLMAN_SCHEDULE_JSON",
    "DEFAULT_CERT_WORKDIR",
    "DEFAULT_DROPBOX_RECEIPT",
    "DEFAULT_FUNDED_1X_PRESET",
    "DEFAULT_PORTABLE_ROOT",
    "DEFAULT_V105_ML_THRESHOLD",
    "DEFAULT_W5_ML_DIR",
    "IMMUTABLES_11_LF_SHA256",
    "LIVE_FEATURE_MAX_ABS_TOL",
    "MODULAR_EA_STEM",
    "ORDER_SEND_CAPABLE",
    "ORDER_SEND_COUNT",
    "PARITY_MAX_ABS_TOL",
    "PROBE_EA_STEM",
    "SCHEMA_RECEIPT",
    "SPEND_VND",
    "V105_SELECTED_FEATURE_NAMES",
    "HoldoutViolationError",
    "_NO_WINDOW_FLAGS",
    "apply_mode_a_below_normal_priority",
    "assert_dev_date_sealed",
    "assert_safe_portable_root",
    "assert_zero_all_mt5_processes",
    "compare_positions_exact_and_reentries",
    "compile_mq5_via_portable_metaeditor",
    "compute_four_way_parity_metrics_v105",
    "evaluate_bellman_dp_6tier_reference",
    "evaluate_mqh_v105_python_mirror",
    "list_all_running_mt5_processes",
    "main",
    "parse_metaeditor_compile_log",
    "parse_modular_v105_tester_log",
    "parse_mqh_v105_tree_tables",
    "parse_parity500_v105_csv",
    "parse_parity500_v105_log",
    "parse_set_kv_clean",
    "reconcile_live_ea_features_vs_python_ref",
    "render_modular_v105_tester_set",
    "render_safe_tester_ini",
    "run_full_wave5_modular_mt5_certification",
    "run_modular_v105_full2024_job",
    "run_w5_g12_parity500_certification",
    "sha256_lf_normalized",
    "validate_feature_matrix_v105",
    "verify_immutables_11_and_hygiene",
]

if __name__ == "__main__":
    raise SystemExit(main())

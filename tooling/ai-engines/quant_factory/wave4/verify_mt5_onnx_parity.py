"""Wave 4 Independent MT5 ONNX Parity & Full-2024 Strategy Tester Ablation Certifier (`W4-G05`).

Independently certifies the Wave 2B ONNX + MQL5 deliverables (`w4_09_lgbm_tf_d2_n60`) across:
  1. **Independent 4-Way Numerical Parity (`<= 1e-5` across ALL 500 Fold-4 OOS vectors):**
     - Fresh SHA-256 & ONNX graph inspection (`0` `ZipMap` nodes, `onnx.checker.check_model`)
       on `.runtime/offensive4/ml/naqex_v104_lgbm.onnx` (+ portable MT5 `MQL5/Files/` copy).
     - Fresh `Python LightGBM` (`wave4_ml_prototype_model.pkl` + `wave4_ml_parity_500.npz`),
       `onnxruntime` CPU (`batch=500` and `batch=1`), independent MT5 Strategy Tester
       `Naqex_ML_Parity500_Probe.ex5` (`OnnxRun()` + `Pure-MQL5` fallback), AND parsed
       `Include/Naqex_ML_Filter_v104.mqh` Python mirror all agree `<= 1e-5` (`500/500`),
       with `100%` (`500/500`) toxic-filter decision agreement and fail-closed `NaN`/`Inf`
       rejection verified in both Python and MT5 Strategy Tester.
  2. **Controlled Full-2024 `Model=1` MT5 Strategy Tester Ablation (`Funded_1x` `10K`, `2024.01.02..2024.12.31`):**
     - `v104_ML_ONNX` (`InpEnableMLFilter=true`, `InpMLMode=0` `ONNX_OR_PURE_MQL5_FALLBACK`):
       verifies `ml_onnx_ready=true`, `ml_backend=ONNX`, `0` runtime errors, `swap=$0.00`,
       side-by-side vs untouched `v103` (`Funded_1x_10K_2024_M1` in `w4_t0_parity98_receipt.json`).
     - `v104_ML_Disabled` (`InpEnableMLFilter=false`): proves disabling ML cleanly reproduces
       untouched `v103` (`469` trades, net PnL, PF, EqDD, swap=$0.00).
     - `v104_ML_PureMQL5` (`InpEnableMLFilter=true`, `InpMLMode=2` `PURE_MQL5_TREE_ONLY`):
       proves the zero-dependency Pure-MQL5 tree fallback executes a full calendar year with
       `0` runtime errors and reproduces `v104_ML_ONNX` decisions cleanly.

HARD SAFETY & FAIL-CLOSED INVARIANTS (ZERO EXCEPTIONS):
  - `ORDER_SEND_CAPABLE = False`, `ORDER_SEND_COUNT = 0`, `0 VND`, ZERO `MetaTrader5` imports.
  - ZERO bare Python `assert` statements (100% active under `python -O` / `python -OO`).
  - LAZY IMPORTS ONLY for `onnx`, `onnxruntime`, `lightgbm`, `onnxmltools`, `skl2onnx`, `sklearn`.
  - Every `subprocess.run` passes `creationflags=_NO_WINDOW_FLAGS` (zero Windows popups).
  - Strictly Dev-only (`AllowLiveTrading=0`, `ToDate <= 2024.12.31`, `holdout_rows_analysed == 0`).
  - Portable sandbox ONLY (`.runtime/ftmo-demo-portable-1515343166`), `MT5_PROCS == 0` verified
    before and after every run, `0` `.ex5` in `exports/` or `private_vault/`, `v103.mq5` untouched.
"""

from __future__ import annotations

import argparse
import csv
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
from pathlib import Path
from typing import Any, Final

import numpy as np

AI_ENGINES_DIR: Final[Path] = Path(__file__).resolve().parents[2]
if str(AI_ENGINES_DIR) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES_DIR))

from quant_core.io_utils import atomic_write_json, repo_root_from, sha256_file  # noqa: E402

from quant_factory.wave4 import HOLDOUT_CUTOFF_DATE  # noqa: E402
from quant_factory.wave4.ftmo_m1_exporter import (  # noqa: E402
    DEFAULT_PORTABLE_ROOT,
    HoldoutViolationError,
    assert_safe_portable_root,
)
from quant_factory.wave4.ml_onnx_exporter import (  # noqa: E402
    CONSUMED_CLB_TAG,
    DEFAULT_EXPORTS_DIR,
    DEFAULT_ML_DIR,
    DEFAULT_MQH_PATH,
    DEFAULT_V103_MQ5_PATH,
    DEV_CUTOFF_SEC,
    EXPECTED_PARITY_ROWS,
    ONNX_MODEL_FILENAME,
    PARITY_CSV_FILENAME,
    PARITY_MAX_ABS_TOL,
    V103_EXPECTED_SHA256,
    evaluate_mqh_source_python_mirror,
    load_prototype_bundle,
    validate_feature_matrix,
    verify_onnx_runtime_parity,
    verify_v103_immutable,
)
from quant_factory.wave4.same_feed_mt5_parity import (  # noqa: E402
    DEFAULT_AUDIT_RECEIPT as DEFAULT_W4_T0_PARITY98_RECEIPT,
)
from quant_factory.wave4.same_feed_mt5_parity import (  # noqa: E402
    DEFAULT_PRESETS_DIR,
    DEFAULT_RED_NEWS_CSV,
    ENGINE_SPECS,
    assert_dev_date_sealed,
    assert_zero_all_mt5_processes,
    list_all_running_mt5_processes,
    parse_set_kv,
    parse_v103_mt5_html_positions,
    prague_utc_offset_hours,
    round_cent_half_up,
)

# ---------------------------------------------------------------------------
# Hard Safety Constants & Canonical Paths
# ---------------------------------------------------------------------------

SCHEMA_RECEIPT: Final[str] = "naqex-wave4-m1-mt5-onnx-cert-receipt-v1"
ORDER_SEND_CAPABLE: Final[bool] = False
ORDER_SEND_COUNT: Final[int] = 0
SPEND_VND: Final[int] = 0

REPO_ROOT: Final[Path] = repo_root_from(__file__)
PRIVATE_VAULT_DIR: Final[Path] = REPO_ROOT / "private_vault"
COMPILED_EX5_DIR: Final[Path] = REPO_ROOT / ".runtime" / "mt5-compiled-ex5"
DEFAULT_V104_EX5_PATH: Final[Path] = COMPILED_EX5_DIR / "Naqex_Master_Prop7E_v104_ML.ex5"
DEFAULT_PROBE_EX5_PATH: Final[Path] = COMPILED_EX5_DIR / "Naqex_ML_Parity500_Probe.ex5"
DEFAULT_FUNDED_1X_PRESET: Final[Path] = DEFAULT_PRESETS_DIR / "FTMO_Std10K_v103_Funded_1x.set"
DEFAULT_V103_FUNDED_1X_HTML: Final[Path] = (
    REPO_ROOT
    / ".runtime"
    / "mt5-realtick-results"
    / "v103_dev_parity"
    / "Funded_1x_Full2024_M1"
    / "v103_Funded_1x_Full2024_M1.htm"
)
DEFAULT_W4_M1_ONNX_MQ5_RECEIPT: Final[Path] = (
    REPO_ROOT / ".runtime" / "offensive4" / "audits" / "w4_m1_onnx_mq5_receipt.json"
)
DEFAULT_CERT_WORKDIR: Final[Path] = DEFAULT_ML_DIR / "mt5_cert_w4g05"
DEFAULT_AUDIT_RECEIPT: Final[Path] = REPO_ROOT / ".runtime" / "offensive4" / "audits" / "w4_m1_mt5_onnx_receipt.json"
DEFAULT_DROPBOX_RECEIPT: Final[Path] = REPO_ROOT / ".tmp" / "swarm_dropbox" / "w4-m1-mt5-onnx.json"

PROPGUARD_EXPECTED_SHA256: Final[str] = "9d7fb3c966688df9cd13ec376b7ea9d4770f5c30bb97b7e5a978d1fe0840e5ed"
SIGNALS_7E_EXPECTED_SHA256: Final[str] = "2f5b7d7ccd7b8a88b7b9896259cbda846e5553cf6ceb868866f9566a860be738"
AGENTS_MD_EXPECTED_BYTES: Final[int] = 10901
QUANT_CORE_EXPECTED_PY_COUNT: Final[int] = 41

DEFAULT_ML_THRESHOLD: Final[float] = 0.457952
ML_MODE_ONNX_OR_FALLBACK: Final[int] = 0
ML_MODE_ONNX_ONLY_FAIL_CLOSED: Final[int] = 1
ML_MODE_PURE_MQL5_ONLY: Final[int] = 2

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
    "[master-v104-err]",
    "[ml-v104-err]",
    "[ml-v104-warn]",
    "[ml-parity500-err]",
    "onnxrun failed",
    "onnx error",
    "tensorrt",
    "cuda error",
)


# ---------------------------------------------------------------------------
# 1. Immutables, Binary Hygiene & Log Decoding Helpers (ZERO Bare `assert`)
# ---------------------------------------------------------------------------


def _decode_mt5_text(path: Path) -> str:
    raw = path.read_bytes()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")) or b"\x00" in raw[:200]:
        return raw.decode("utf-16", errors="replace")
    return raw.decode("utf-8", errors="replace")


def verify_immutables_and_binary_hygiene(
    *,
    repo_root: Path = REPO_ROOT,
    exports_dir: Path = DEFAULT_EXPORTS_DIR,
    private_vault_dir: Path = PRIVATE_VAULT_DIR,
) -> dict[str, Any]:
    """Fail-closed check of immutable MQL5/doc hashes, `quant_core` count, and zero stray `.ex5`."""
    v103_path = exports_dir / DEFAULT_V103_MQ5_PATH.name
    v103_check = verify_v103_immutable(v103_path, expected_sha256=V103_EXPECTED_SHA256)

    propguard_path = exports_dir / "Include" / "Naqex_PropGuard.mqh"
    signals_path = exports_dir / "Include" / "Naqex_Signals_7E.mqh"
    agents_path = repo_root / "AGENTS.md"
    quant_core_dir = repo_root / "tooling" / "ai-engines" / "quant_core"

    for req in (propguard_path, signals_path, agents_path):
        if not req.is_file():
            raise FileNotFoundError(f"IMMUTABLE_MISSING: {req}")

    propguard_sha = sha256_file(propguard_path)
    if propguard_sha != PROPGUARD_EXPECTED_SHA256:
        raise RuntimeError(f"IMMUTABLE_BREACH: Naqex_PropGuard.mqh sha={propguard_sha}")

    signals_sha = sha256_file(signals_path)
    if signals_sha != SIGNALS_7E_EXPECTED_SHA256:
        raise RuntimeError(f"IMMUTABLE_BREACH: Naqex_Signals_7E.mqh sha={signals_sha}")

    agents_bytes = agents_path.stat().st_size
    if agents_bytes != AGENTS_MD_EXPECTED_BYTES:
        raise RuntimeError(f"IMMUTABLE_BREACH: AGENTS.md bytes={agents_bytes} != {AGENTS_MD_EXPECTED_BYTES}")

    quant_core_py_count = len(list(quant_core_dir.glob("*.py"))) if quant_core_dir.is_dir() else 0
    if quant_core_py_count != QUANT_CORE_EXPECTED_PY_COUNT:
        raise RuntimeError(
            f"IMMUTABLE_BREACH: quant_core py count={quant_core_py_count} != {QUANT_CORE_EXPECTED_PY_COUNT}"
        )

    stray_exports_ex5 = [str(p.relative_to(repo_root)) for p in sorted(exports_dir.rglob("*.ex5"))]
    if stray_exports_ex5:
        raise RuntimeError(f"FORBIDDEN_EX5_IN_EXPORTS: {stray_exports_ex5}")

    stray_vault_ex5 = (
        [str(p.relative_to(repo_root)) for p in sorted(private_vault_dir.rglob("*.ex5"))]
        if private_vault_dir.is_dir()
        else []
    )
    if stray_vault_ex5:
        raise RuntimeError(f"FORBIDDEN_EX5_IN_PRIVATE_VAULT: {stray_vault_ex5}")

    return {
        "v103_mq5_sha256": v103_check["sha256"],
        "v103_mq5_untouched": True,
        "propguard_mqh_sha256": propguard_sha,
        "propguard_mqh_untouched": True,
        "signals_7e_mqh_sha256": signals_sha,
        "signals_7e_mqh_untouched": True,
        "agents_md_bytes": agents_bytes,
        "agents_md_untouched": True,
        "quant_core_py_count": quant_core_py_count,
        "quant_core_untouched": True,
        "exports_ex5_count": len(stray_exports_ex5),
        "private_vault_ex5_count": len(stray_vault_ex5),
    }


# ---------------------------------------------------------------------------
# 2. Pure-Python 4-Way Numerical Parity & MT5 Probe Parsers (CI-Safe!)
# ---------------------------------------------------------------------------


def parse_parity500_probe_output_csv(
    csv_path: str | Path,
    *,
    expected_rows: int = EXPECTED_PARITY_ROWS,
) -> dict[str, Any]:
    """Parse `wave4_ml_mt5_parity500_out.csv` emitted by `Naqex_ML_Parity500_Probe.ex5` fail-closed."""
    path = Path(csv_path)
    if not path.is_file():
        raise FileNotFoundError(f"MT5_PARITY500_OUT_CSV_MISSING: {path}")

    row_indices: list[int] = []
    ref_proba: list[float] = []
    onnx_proba: list[float] = []
    pure_proba: list[float] = []
    ref_size: list[float] = []
    onnx_size: list[float] = []
    pure_size: list[float] = []

    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        required_cols = {
            "row_idx",
            "ref_proba",
            "onnx_proba",
            "pure_mql5_proba",
            "ref_size",
            "onnx_size",
            "pure_size",
        }
        fieldnames = set(reader.fieldnames or [])
        missing = sorted(required_cols - fieldnames)
        if missing:
            raise ValueError(f"MT5_PARITY500_CSV_MISSING_COLS: {missing}")

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
                raise ValueError(f"MT5_PARITY500_CSV_PARSE_ERROR at line {line_no}") from exc

            for val_name, val in (
                ("ref_proba", rp),
                ("onnx_proba", op),
                ("pure_mql5_proba", pp),
                ("ref_size", rs),
                ("onnx_size", os_),
                ("pure_size", ps),
            ):
                if not math.isfinite(val):
                    raise ValueError(f"MT5_PARITY500_CSV_NON_FINITE [{val_name}] at line {line_no}: {val!r}")

            row_indices.append(ridx)
            ref_proba.append(rp)
            onnx_proba.append(op)
            pure_proba.append(pp)
            ref_size.append(rs)
            onnx_size.append(os_)
            pure_size.append(ps)

    if len(row_indices) != int(expected_rows):
        raise ValueError(f"MT5_PARITY500_ROW_COUNT_MISMATCH: expected {expected_rows}, got {len(row_indices)}")
    if row_indices != list(range(int(expected_rows))):
        raise ValueError("MT5_PARITY500_ROW_INDEX_SEQUENCE_INVALID: expected 0..N-1 contiguous")

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


def parse_parity500_probe_log(log_text: str) -> dict[str, Any]:
    """Parse `Naqex_ML_Parity500_Probe` Agent log for ONNX API version, CPU EP, summary & NaN/Inf blocks."""
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
        if "[ML-PARITY500-INIT]" in ln:
            init_line = ln
        if "PARITY500_SUMMARY|" in ln:
            summary_line = ln
            tail = ln.split("PARITY500_SUMMARY|", 1)[1]
            for item in tail.split("|"):
                if "=" in item:
                    k, v = item.split("=", 1)
                    summary_kv[k.strip()] = v.strip()

    error_lines = _scan_log_errors(log_text)
    rows = int(summary_kv["rows"]) if "rows" in summary_kv else 0
    onnx_ok = int(summary_kv["onnx_ok"]) if "onnx_ok" in summary_kv else 0
    pure_ok = int(summary_kv["pure_ok"]) if "pure_ok" in summary_kv else 0
    onnx_ready = summary_kv.get("onnx_ready", "").lower() == "true"
    nan_blocked = summary_kv.get("nan_blocked", "").lower() == "true"
    inf_blocked = summary_kv.get("inf_blocked", "").lower() == "true"
    parity_pass = summary_kv.get("parity_pass", "").lower() == "true"

    return {
        "onnx_api_version": onnx_api_version,
        "cpu_selected": cpu_selected,
        "init_line": init_line,
        "summary_line": summary_line,
        "rows": rows,
        "onnx_ready": onnx_ready,
        "onnx_ok": onnx_ok,
        "pure_ok": pure_ok,
        "onnx_size_match": int(summary_kv["onnx_size_match"]) if "onnx_size_match" in summary_kv else 0,
        "pure_size_match": int(summary_kv["pure_size_match"]) if "pure_size_match" in summary_kv else 0,
        "nan_blocked": nan_blocked,
        "inf_blocked": inf_blocked,
        "parity_pass": parity_pass,
        "log_max_err_onnx_ref": (
            float(summary_kv["max_err_onnx_ref"]) if "max_err_onnx_ref" in summary_kv else None
        ),
        "log_max_err_pure_ref": (
            float(summary_kv["max_err_pure_ref"]) if "max_err_pure_ref" in summary_kv else None
        ),
        "log_max_err_onnx_pure": (
            float(summary_kv["max_err_onnx_pure"]) if "max_err_onnx_pure" in summary_kv else None
        ),
        "error_lines_count": len(error_lines),
        "error_lines": error_lines[:10],
    }


def parse_v104_ml_tester_log(log_text: str) -> dict[str, Any]:
    """Parse `Naqex_Master_Prop7E_v104_ML` MT5 Tester log for `[MASTER-V104-ML-INIT]`, ONNX EP & errors."""
    onnx_api_version: str | None = None
    cpu_selected = False
    init_line: str | None = None
    init_kv: dict[str, str] = {}
    propguard_ok_line: str | None = None

    for raw_ln in log_text.splitlines():
        ln = raw_ln.strip()
        if not ln:
            continue
        m_api = re.search(r"api version\s+([0-9][0-9A-Za-z._-]+)\s+initialized", ln, flags=re.IGNORECASE)
        if m_api:
            onnx_api_version = m_api.group(1)
        if "ONNX: CPU selected" in ln:
            cpu_selected = True
        if "[PROPGUARD-OK]" in ln:
            propguard_ok_line = ln
        if "[MASTER-V104-ML-INIT]" in ln:
            init_line = ln
            tail = ln.split("[MASTER-V104-ML-INIT]", 1)[1].strip()
            for tok in tail.split():
                if "=" in tok:
                    k, v = tok.split("=", 1)
                    init_kv[k.strip()] = v.strip()

    error_lines = _scan_log_errors(log_text)
    return {
        "onnx_api_version": onnx_api_version,
        "cpu_selected": cpu_selected,
        "propguard_ok_line": propguard_ok_line,
        "init_line": init_line,
        "sku": init_kv.get("sku"),
        "ml_enabled": init_kv.get("ml_enabled", "").lower() == "true" if "ml_enabled" in init_kv else None,
        "ml_thr": float(init_kv["ml_thr"]) if "ml_thr" in init_kv else None,
        "ml_onnx_ready": init_kv.get("ml_onnx_ready", "").lower() == "true" if "ml_onnx_ready" in init_kv else None,
        "ml_backend": init_kv.get("ml_backend"),
        "dry_run": init_kv.get("dry_run", "").lower() == "true" if "dry_run" in init_kv else None,
        "error_lines_count": len(error_lines),
        "error_lines": error_lines[:10],
    }


def _validate_prob_vector(raw: Any, *, expected_len: int, name: str) -> np.ndarray:
    if raw is None or isinstance(raw, (bool, np.bool_, str, bytes)):
        raise ValueError(f"INVALID_PROB_VECTOR [{name}]: got {type(raw).__name__}")
    arr = np.asarray(raw)
    if arr.dtype == np.bool_:
        raise ValueError(f"POISONED_BOOL_PROB_VECTOR [{name}]")
    try:
        vec = np.asarray(arr, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"NON_NUMERIC_PROB_VECTOR [{name}]") from exc
    if vec.ndim != 1 or vec.shape[0] != int(expected_len):
        raise ValueError(f"PROB_VECTOR_SHAPE_MISMATCH [{name}]: expected ({expected_len},), got {vec.shape}")
    if not bool(np.all(np.isfinite(vec))):
        raise ValueError(f"NON_FINITE_PROB_VECTOR [{name}]: NaN or Inf detected (fail-closed)")
    if float(np.min(vec)) < 0.0 or float(np.max(vec)) > 1.0:
        raise ValueError(
            f"OUT_OF_RANGE_PROB_VECTOR [{name}]: min={float(np.min(vec))}, max={float(np.max(vec))}"
        )
    return vec


def _pairwise_err_stats(a: np.ndarray, b: np.ndarray) -> dict[str, float]:
    diff = np.abs(a - b)
    return {
        "max_abs_err": float(np.max(diff)),
        "mean_abs_err": float(np.mean(diff)),
        "p99_abs_err": float(np.percentile(diff, 99.0)),
    }


def compute_four_way_parity_metrics(
    *,
    py_lgbm_proba: Sequence[float] | np.ndarray,
    ort_batch_proba: Sequence[float] | np.ndarray,
    ort_single_proba: Sequence[float] | np.ndarray,
    mt5_onnx_proba: Sequence[float] | np.ndarray,
    mt5_pure_proba: Sequence[float] | np.ndarray,
    py_mqh_mirror_proba: Sequence[float] | np.ndarray,
    ref_sizes: Sequence[float] | np.ndarray,
    threshold: float = DEFAULT_ML_THRESHOLD,
    tol: float = PARITY_MAX_ABS_TOL,
) -> dict[str, Any]:
    """Compute exact 4-way (`Python LightGBM == onnxruntime == MT5 OnnxRun() == MT5 Pure-MQL5`) parity stats.

    Pure NumPy (zero ML/ONNX imports, CI-safe). Fail-closed rejects NaN/Inf/bool/shape drift even under `python -O`.
    """
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


# ---------------------------------------------------------------------------
# 3. Full-2024 Controlled Ablation Metrics & Trade-Level Diff (CI-Safe!)
# ---------------------------------------------------------------------------


def _prague_day_str(utc_ts: int) -> str:
    dt = datetime.fromtimestamp(int(utc_ts), UTC)
    off_h = prague_utc_offset_hours(dt.year, dt.month, dt.day, dt.hour)
    p_dt = datetime.fromtimestamp(int(utc_ts) + off_h * 3600, UTC)
    return p_dt.strftime("%Y-%m-%d")


def compute_worst_day_metrics(
    positions: Sequence[Mapping[str, Any]],
    *,
    initial_balance_usd: float = 10_000.0,
) -> dict[str, Any]:
    """Compute realized daily PnL and worst single-day loss % (both UTC day & FTMO Prague reset day)."""
    if initial_balance_usd <= 0.0 or not math.isfinite(initial_balance_usd):
        raise ValueError(f"INVALID_INITIAL_BALANCE: {initial_balance_usd!r}")

    utc_daily: dict[str, float] = {}
    prague_daily: dict[str, float] = {}
    for pos in positions:
        exit_ts = int(pos.get("exit_utc_ts") or pos.get("entry_utc_ts") or 0)
        pnl = float(pos.get("net_pnl_usd", 0.0))
        if not math.isfinite(pnl):
            raise ValueError(f"NON_FINITE_POSITION_PNL: {pnl!r}")
        u_day = datetime.fromtimestamp(exit_ts, UTC).strftime("%Y-%m-%d") if exit_ts > 0 else str(pos.get("day_utc"))
        p_day = _prague_day_str(exit_ts) if exit_ts > 0 else u_day
        utc_daily[u_day] = round_cent_half_up(utc_daily.get(u_day, 0.0) + pnl)
        prague_daily[p_day] = round_cent_half_up(prague_daily.get(p_day, 0.0) + pnl)

    def _worst(day_map: Mapping[str, float]) -> dict[str, Any]:
        if not day_map:
            return {
                "trading_days": 0,
                "worst_day": None,
                "worst_day_pnl_usd": 0.0,
                "worst_day_pct": 0.0,
                "best_day": None,
                "best_day_pnl_usd": 0.0,
            }
        w_day, w_pnl = min(day_map.items(), key=lambda kv: kv[1])
        b_day, b_pnl = max(day_map.items(), key=lambda kv: kv[1])
        w_loss_pct = round((abs(min(0.0, float(w_pnl))) / float(initial_balance_usd)) * 100.0, 4)
        return {
            "trading_days": len(day_map),
            "worst_day": w_day,
            "worst_day_pnl_usd": round_cent_half_up(float(w_pnl)),
            "worst_day_pct": w_loss_pct,
            "best_day": b_day,
            "best_day_pnl_usd": round_cent_half_up(float(b_pnl)),
        }

    prague_stats = _worst(prague_daily)
    utc_stats = _worst(utc_daily)
    return {
        "worst_day_pct": prague_stats["worst_day_pct"],
        "worst_day_pnl_usd": prague_stats["worst_day_pnl_usd"],
        "worst_day_prague_date": prague_stats["worst_day"],
        "prague_reset_day": prague_stats,
        "utc_day": utc_stats,
    }


def summarize_mt5_ablation_run(
    parsed_report: Mapping[str, Any],
    *,
    initial_balance_usd: float = 10_000.0,
) -> dict[str, Any]:
    """Extract standardized metrics (`trades`, `net_pnl_usd`, `PF`, `EqDD`, `worst_day_pct`, `swap`, per-engine)."""
    summary = parsed_report.get("summary") or {}
    positions: Sequence[Mapping[str, Any]] = parsed_report.get("positions") or []

    n_trades = len(positions)
    wins = sum(1 for p in positions if float(p.get("net_pnl_usd", 0.0)) > 0.0)
    win_rate_pct = round((wins / n_trades) * 100.0, 2) if n_trades > 0 else 0.0
    worst = compute_worst_day_metrics(positions, initial_balance_usd=initial_balance_usd)

    per_engine: dict[str, dict[str, Any]] = {}
    for magic, spec in ENGINE_SPECS.items():
        eid = str(spec["engine_id"])
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
        "unclosed_remaining": int(parsed_report.get("unclosed_remaining", 0)),
        "max_deal_date": str(parsed_report.get("max_deal_date", "")),
        "net_pnl_usd": round_cent_half_up(float(net_pnl)),
        "gross_profit_usd": round_cent_half_up(float(gp)) if gp is not None else None,
        "gross_loss_usd": round_cent_half_up(float(gl)) if gl is not None else None,
        "profit_factor": float(pf) if pf is not None else None,
        "win_rate_pct": win_rate_pct,
        "balance_dd_pct": summary.get("balance_dd_pct"),
        "equity_dd_pct": summary.get("equity_dd_pct"),
        "worst_day_pct": worst["worst_day_pct"],
        "worst_day_pnl_usd": worst["worst_day_pnl_usd"],
        "worst_day_prague_date": worst["worst_day_prague_date"],
        "worst_day_utc_pct": worst["utc_day"]["worst_day_pct"],
        "worst_day_utc_pnl_usd": worst["utc_day"]["worst_day_pnl_usd"],
        "commission_total_usd": float(summary.get("commission_total_usd", 0.0)),
        "swap_total_usd": swap_total,
        "swap_zero_ok": abs(swap_total) < 1e-6,
        "history_quality_pct": summary.get("history_quality_pct"),
        "ticks": int(summary.get("ticks") or 0),
        "per_engine": per_engine,
    }


def compare_ablation_positions(
    *,
    baseline_positions: Sequence[Mapping[str, Any]],
    candidate_positions: Sequence[Mapping[str, Any]],
    initial_balance_usd: float = 10_000.0,
) -> dict[str, Any]:
    """Compare candidate vs baseline positions to compute exact `filtered_trades_count` & retention."""
    base_by_key: dict[tuple[int, str, str], list[Mapping[str, Any]]] = {}
    cand_by_key: dict[tuple[int, str, str], list[Mapping[str, Any]]] = {}

    for p in baseline_positions:
        key = (int(p.get("magic", 0)), str(p.get("day_utc", "")), str(p.get("side", "")))
        base_by_key.setdefault(key, []).append(p)
    for p in candidate_positions:
        key = (int(p.get("magic", 0)), str(p.get("day_utc", "")), str(p.get("side", "")))
        cand_by_key.setdefault(key, []).append(p)

    kept_count = 0
    filtered_positions: list[Mapping[str, Any]] = []
    unblocked_positions: list[Mapping[str, Any]] = []

    all_keys = sorted(set(base_by_key.keys()) | set(cand_by_key.keys()))
    for key in all_keys:
        b_list = base_by_key.get(key, [])
        c_list = cand_by_key.get(key, [])
        n_match = min(len(b_list), len(c_list))
        kept_count += n_match
        if len(b_list) > n_match:
            filtered_positions.extend(b_list[n_match:])
        if len(c_list) > n_match:
            unblocked_positions.extend(c_list[n_match:])

    base_n = len(baseline_positions)
    cand_n = len(candidate_positions)
    filtered_n = len(filtered_positions)
    unblocked_n = len(unblocked_positions)

    filtered_pnl = round_cent_half_up(sum(float(p.get("net_pnl_usd", 0.0)) for p in filtered_positions))
    filtered_wins = sum(1 for p in filtered_positions if float(p.get("net_pnl_usd", 0.0)) > 0.0)
    filtered_wr = round((filtered_wins / filtered_n) * 100.0, 2) if filtered_n > 0 else 0.0

    per_engine_retention: dict[str, dict[str, Any]] = {}
    for magic, spec in ENGINE_SPECS.items():
        eid = str(spec["engine_id"])
        bn = sum(1 for p in baseline_positions if int(p.get("magic", 0)) == magic)
        cn = sum(1 for p in candidate_positions if int(p.get("magic", 0)) == magic)
        fn = sum(1 for p in filtered_positions if int(p.get("magic", 0)) == magic)
        per_engine_retention[eid] = {
            "baseline_trades": bn,
            "candidate_trades": cn,
            "filtered_trades": fn,
            "retention_ratio": round(cn / bn, 6) if bn > 0 else 1.0,
        }

    base_worst = compute_worst_day_metrics(baseline_positions, initial_balance_usd=initial_balance_usd)
    cand_worst = compute_worst_day_metrics(candidate_positions, initial_balance_usd=initial_balance_usd)

    # Engine-day forensic diff to detect ML-reject delayed / flipped re-entries within the same session
    base_by_ed: dict[tuple[int, str], Mapping[str, Any]] = {}
    cand_by_ed: dict[tuple[int, str], Mapping[str, Any]] = {}
    for p in baseline_positions:
        base_by_ed[(int(p.get("magic", 0)), str(p.get("day_utc", "")))] = p
    for p in candidate_positions:
        cand_by_ed[(int(p.get("magic", 0)), str(p.get("day_utc", "")))] = p

    perm_filtered_keys = sorted(set(base_by_ed.keys()) - set(cand_by_ed.keys()))
    same_ed_keys = sorted(set(base_by_ed.keys()) & set(cand_by_ed.keys()))
    delayed_same_side = 0
    flipped_side = 0
    delayed_same_side_pnl_delta = 0.0
    flipped_side_pnl_delta = 0.0
    all_affected_base_pnl = 0.0
    all_affected_base_wins = 0
    affected_by_engine: dict[str, int] = {}

    for k in perm_filtered_keys:
        bp = base_by_ed[k]
        bpnl = float(bp.get("net_pnl_usd", 0.0))
        all_affected_base_pnl += bpnl
        if bpnl > 0.0:
            all_affected_base_wins += 1
        eid = str(bp.get("engine_id") or ENGINE_SPECS.get(k[0], {}).get("engine_id", "UNKNOWN"))
        affected_by_engine[eid] = affected_by_engine.get(eid, 0) + 1

    for k in same_ed_keys:
        bp = base_by_ed[k]
        cp = cand_by_ed[k]
        b_ts = int(bp.get("entry_utc_ts") or 0)
        c_ts = int(cp.get("entry_utc_ts") or 0)
        b_side = str(bp.get("side", ""))
        c_side = str(cp.get("side", ""))
        if c_ts != b_ts or c_side != b_side:
            bpnl = float(bp.get("net_pnl_usd", 0.0))
            cpnl = float(cp.get("net_pnl_usd", 0.0))
            all_affected_base_pnl += bpnl
            if bpnl > 0.0:
                all_affected_base_wins += 1
            eid = str(bp.get("engine_id") or ENGINE_SPECS.get(k[0], {}).get("engine_id", "UNKNOWN"))
            affected_by_engine[eid] = affected_by_engine.get(eid, 0) + 1
            if c_side != b_side:
                flipped_side += 1
                flipped_side_pnl_delta += cpnl - bpnl
            else:
                delayed_same_side += 1
                delayed_same_side_pnl_delta += cpnl - bpnl

    total_affected = len(perm_filtered_keys) + delayed_same_side + flipped_side
    perm_filtered_pnl = round_cent_half_up(
        sum(float(base_by_ed[k].get("net_pnl_usd", 0.0)) for k in perm_filtered_keys)
    )

    return {
        "baseline_trades": base_n,
        "candidate_trades": cand_n,
        "kept_trades_count": kept_count,
        "filtered_trades_count": filtered_n,
        "newly_unblocked_trades_count": unblocked_n,
        "net_trade_delta": cand_n - base_n,
        "overall_retention_ratio": round(cand_n / base_n, 6) if base_n > 0 else 1.0,
        "filtered_trades_baseline_net_pnl_usd": filtered_pnl,
        "filtered_trades_baseline_win_rate_pct": filtered_wr,
        "permanently_filtered_engine_days_count": len(perm_filtered_keys),
        "permanently_filtered_baseline_net_pnl_usd": perm_filtered_pnl,
        "delayed_same_side_reentries_count": delayed_same_side,
        "delayed_same_side_pnl_delta_usd": round_cent_half_up(delayed_same_side_pnl_delta),
        "flipped_side_reentries_count": flipped_side,
        "flipped_side_pnl_delta_usd": round_cent_half_up(flipped_side_pnl_delta),
        "total_ml_affected_engine_days": total_affected,
        "all_ml_blocked_baseline_net_pnl_usd": round_cent_half_up(all_affected_base_pnl),
        "all_ml_blocked_baseline_win_rate_pct": (
            round((all_affected_base_wins / total_affected) * 100.0, 2) if total_affected > 0 else 0.0
        ),
        "affected_by_engine": affected_by_engine,
        "baseline_worst_day_pct": base_worst["worst_day_pct"],
        "candidate_worst_day_pct": cand_worst["worst_day_pct"],
        "delta_worst_day_pct": round(cand_worst["worst_day_pct"] - base_worst["worst_day_pct"], 4),
        "per_engine_retention": per_engine_retention,
    }


# ---------------------------------------------------------------------------
# 4. Safe MT5 Strategy Tester Config Renderers & Runner (`MT5_PROCS == 0`)
# ---------------------------------------------------------------------------


def render_v104_tester_set(
    src_preset_path: str | Path,
    *,
    initial_balance_usd: float,
    enable_ml_filter: bool,
    ml_mode: int = ML_MODE_ONNX_OR_FALLBACK,
    ml_threshold: float = DEFAULT_ML_THRESHOLD,
    ml_onnx_file: str = ONNX_MODEL_FILENAME,
    contract_sku: str = "FTMO_STD_10K_V104_ML_FUNDED_1X",
    out_path: Path,
) -> Path:
    """Create a transient Strategy Tester `.set` for `v104_ML` without mutating source preset on disk."""
    if ml_mode not in (ML_MODE_ONNX_OR_FALLBACK, ML_MODE_ONNX_ONLY_FAIL_CLOSED, ML_MODE_PURE_MQL5_ONLY):
        raise ValueError(f"INVALID_ML_MODE: {ml_mode!r}")
    if not math.isfinite(ml_threshold) or not (0.0 < ml_threshold < 1.0):
        raise ValueError(f"INVALID_ML_THRESHOLD: {ml_threshold!r}")

    kv = parse_set_kv(src_preset_path)
    kv["InpDryRunLogOnly"] = "false"
    kv["InpShadowCompareMode"] = "false"
    kv["InpGuardDryRunLogOnly"] = "false"
    kv["InpEnableS6Shadow"] = "false"
    kv["InpWritePrimaryHeartbeat"] = "false"
    kv["InpAllowManualHaltFile"] = "false"
    kv["InpInitialBalanceUSD"] = f"{float(initial_balance_usd):.2f}"
    kv["InpContractSku"] = str(contract_sku)
    kv["InpHeartbeatFile"] = "naqex_master_v104_ml_heartbeat.json"
    kv["InpShadowCsvFile"] = "naqex_master_v104_ml_shadow.csv"
    # Wave 4 W4-G05 ML filter controls
    kv["InpEnableMLFilter"] = "true" if enable_ml_filter else "false"
    kv["InpMLThreshold"] = f"{float(ml_threshold):.6f}"
    kv["InpMLMode"] = str(int(ml_mode))
    kv["InpMLOnnxFile"] = str(ml_onnx_file)

    lines = [
        f"; Transient Strategy Tester preset for Naqex_Master_Prop7E_v104_ML (src={Path(src_preset_path).name})",
        "; Source preset in private_vault remains untouched & fail-closed DryRun=true",
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

    # Clear prior tester logs so every archived log belongs strictly to this run
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
        for _ in range(25):
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
        archived_log_paths.append(str(dst))
        combined_logs.append(_decode_mt5_text(dst))
    for ad in sorted((portable_root / "Tester").glob("Agent-*")):
        for lp in sorted((ad / "logs").glob("*.log")):
            dst = run_dir / f"{ad.name}_{lp.name}"
            shutil.copy2(lp, dst)
            archived_log_paths.append(str(dst))
            combined_logs.append(_decode_mt5_text(dst))

    return archived_report, "\n".join(combined_logs), archived_log_paths


# ---------------------------------------------------------------------------
# 5. Mission 1: Independent 4-Way 500-Vector Parity Certification
# ---------------------------------------------------------------------------


def run_independent_parity500_certification(
    *,
    ml_dir: Path = DEFAULT_ML_DIR,
    portable_root: Path = DEFAULT_PORTABLE_ROOT,
    probe_ex5_path: Path = DEFAULT_PROBE_EX5_PATH,
    mqh_path: Path = DEFAULT_MQH_PATH,
    work_dir: Path = DEFAULT_CERT_WORKDIR,
    tol: float = PARITY_MAX_ABS_TOL,
    timeout_sec: int = 180,
) -> dict[str, Any]:
    """Re-run `Naqex_ML_Parity500_Probe.ex5` independently and verify 4-way parity `<= 1e-5` (`500/500`).

    LAZY IMPORTS ONLY for `onnx` and `onnxruntime`.
    """
    import onnx  # Lazy import ONLY
    import onnxruntime as ort  # Lazy import ONLY

    p_root = assert_safe_portable_root(portable_root)
    onnx_runtime_path = ml_dir / ONNX_MODEL_FILENAME
    parity_csv_runtime_path = ml_dir / PARITY_CSV_FILENAME
    prior_out_csv_path = ml_dir / "wave4_ml_mt5_parity500_out.csv"

    # 1. Load golden bundle (enforces Holdout 2025+ seal!) and re-verify pickled LightGBM estimator
    bundle = load_prototype_bundle(ml_dir)
    x_500: np.ndarray = bundle["X"]
    p_ref_f64: np.ndarray = bundle["pred_proba_f64"]
    sizes_ref: np.ndarray = bundle["pred_size_toxic_filter"]
    threshold = float(bundle["proto_json"]["train_p_toxic_q20"])

    pkl_path = bundle["proto_pkl_path"]
    if not pkl_path.is_file():
        raise FileNotFoundError(f"PROTOTYPE_PKL_MISSING: {pkl_path}")
    with pkl_path.open("rb") as fh:
        pkl_payload = pickle.load(fh)
    raw_estimator = pkl_payload.get("raw_estimator")
    if raw_estimator is None:
        raise ValueError("PROTOTYPE_PKL_MISSING_RAW_ESTIMATOR")
    p_lgbm_live = np.asarray(raw_estimator.predict_proba(x_500), dtype=np.float64)[:, 1]
    lgbm_live_vs_npz_err = float(np.max(np.abs(p_lgbm_live - p_ref_f64)))
    if lgbm_live_vs_npz_err > tol:
        raise ValueError(f"LGBM_LIVE_VS_NPZ_DRIFT: {lgbm_live_vs_npz_err:.3e} > {tol:.3e}")

    # 2. Fresh ONNX graph inspection (`0` ZipMap nodes, `onnx.checker.check_model`, fresh SHA-256)
    if not onnx_runtime_path.is_file():
        raise FileNotFoundError(f"ONNX_MODEL_MISSING: {onnx_runtime_path}")
    onnx_sha256 = sha256_file(onnx_runtime_path)
    model_proto = onnx.load(str(onnx_runtime_path))
    onnx.checker.check_model(model_proto)
    zipmap_nodes = [n.name or n.op_type for n in model_proto.graph.node if n.op_type == "ZipMap"]
    if zipmap_nodes:
        raise RuntimeError(f"ZIPMAP_FORBIDDEN_NODE_DETECTED: {len(zipmap_nodes)}")

    # 3. Fresh onnxruntime CPU inference (batch=500 AND batch=1) + NaN/Inf fail-closed check
    ort_parity = verify_onnx_runtime_parity(
        onnx_runtime_path,
        x_500,
        p_ref_f64,
        tol=tol,
        threshold=threshold,
        ref_sizes=sizes_ref,
    )
    sess = ort.InferenceSession(str(onnx_runtime_path), providers=["CPUExecutionProvider"])
    in_name = sess.get_inputs()[0].name
    p_ort_batch = np.asarray(sess.run(None, {in_name: x_500})[1], dtype=np.float64)[:, 1]
    p_ort_single = np.empty(x_500.shape[0], dtype=np.float64)
    for i in range(x_500.shape[0]):
        p_ort_single[i] = float(sess.run(None, {in_name: x_500[i : i + 1]})[1][0, 1])

    # Python NaN/Inf fail-closed verification
    py_nan_blocked = False
    py_inf_blocked = False
    x_nan = x_500[:1].copy()
    x_nan[0, 0] = np.nan
    try:
        validate_feature_matrix(x_nan, expected_dim=x_500.shape[1], name="probe_nan")
    except ValueError:
        py_nan_blocked = True
    x_inf = x_500[:1].copy()
    x_inf[0, 1] = np.inf
    try:
        validate_feature_matrix(x_inf, expected_dim=x_500.shape[1], name="probe_inf")
    except ValueError:
        py_inf_blocked = True
    if not (py_nan_blocked and py_inf_blocked):
        raise RuntimeError(f"PYTHON_POISONED_GUARD_FAILED: nan={py_nan_blocked}, inf={py_inf_blocked}")

    # 4. Parsed `.mqh` Python mirror evaluation
    mqh_text = mqh_path.read_text(encoding="utf-8")
    p_py_mqh = evaluate_mqh_source_python_mirror(mqh_text, x_500)

    # 5. Sync probe .ex5 + ONNX + parity CSV into portable MT5 sandbox & purge stale agent output CSV
    portable_probe_sha = _sync_file_if_changed(
        probe_ex5_path, p_root / "MQL5" / "Experts" / "Naqex" / probe_ex5_path.name
    )
    portable_onnx_sha = _sync_file_if_changed(onnx_runtime_path, p_root / "MQL5" / "Files" / ONNX_MODEL_FILENAME)
    portable_csv_sha = _sync_file_if_changed(parity_csv_runtime_path, p_root / "MQL5" / "Files" / PARITY_CSV_FILENAME)

    for ad in (p_root / "Tester").glob("Agent-*"):
        stale_out = ad / "MQL5" / "Files" / "wave4_ml_mt5_parity500_out.csv"
        stale_out.unlink(missing_ok=True)

    run_dir = work_dir / "parity500_independent"
    run_dir.mkdir(parents=True, exist_ok=True)
    report_stem = "w4g05_cert_parity500_probe"
    ini_path = run_dir / "tester.ini"
    ini_path.write_text(
        render_safe_tester_ini(
            expert_rel_path="Naqex\\Naqex_ML_Parity500_Probe",
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
        run_tag="w4g05_parity500_independent",
        timeout_sec=timeout_sec,
    )
    archived_report, combined_logs, archived_logs = _archive_tester_logs_and_report(
        portable_root=p_root,
        run_dir=run_dir,
        report_stem=report_stem,
    )

    # Harvest freshly written output CSV from Tester Agent sandbox
    fresh_out_candidates = sorted((p_root / "Tester").glob("Agent-*/MQL5/Files/wave4_ml_mt5_parity500_out.csv"))
    if not fresh_out_candidates:
        raise FileNotFoundError("MT5_PARITY500_FRESH_OUTPUT_CSV_NOT_EMITTED")
    fresh_out_archived = run_dir / "wave4_ml_mt5_parity500_out.csv"
    shutil.copy2(fresh_out_candidates[0], fresh_out_archived)
    fresh_csv = parse_parity500_probe_output_csv(fresh_out_archived, expected_rows=EXPECTED_PARITY_ROWS)
    prior_out_sha = sha256_file(prior_out_csv_path) if prior_out_csv_path.is_file() else None

    log_info = parse_parity500_probe_log(combined_logs)
    four_way = compute_four_way_parity_metrics(
        py_lgbm_proba=p_lgbm_live,
        ort_batch_proba=p_ort_batch,
        ort_single_proba=p_ort_single,
        mt5_onnx_proba=fresh_csv["onnx_proba"],
        mt5_pure_proba=fresh_csv["pure_mql5_proba"],
        py_mqh_mirror_proba=p_py_mqh,
        ref_sizes=sizes_ref,
        threshold=threshold,
        tol=tol,
    )

    probe_passed = bool(
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
    if not probe_passed:
        raise RuntimeError(
            f"INDEPENDENT_PARITY500_FAILED: rc={rc}, timed_out={timed_out}, "
            f"errs={log_info['error_lines_count']}, onnx_ready={log_info['onnx_ready']}, "
            f"overall_max_abs_err={four_way['overall_max_abs_err']:.3e}"
        )

    return {
        "passed": probe_passed,
        "window": "2024.12.26..2024.12.27",
        "allow_live_trading": 0,
        "holdout_rows_analysed": 0,
        "rc": rc,
        "timed_out": timed_out,
        "elapsed_sec": elapsed,
        "onnx_model": {
            "path": str(onnx_runtime_path),
            "bytes": onnx_runtime_path.stat().st_size,
            "sha256": onnx_sha256,
            "portable_sha256_match": portable_onnx_sha == onnx_sha256,
            "portable_csv_sha256_match": portable_csv_sha == sha256_file(parity_csv_runtime_path),
            "portable_probe_ex5_sha256": portable_probe_sha,
            "ir_version": int(model_proto.ir_version),
            "opset_imports": [(str(op.domain), int(op.version)) for op in model_proto.opset_import],
            "zipmap_node_count": len(zipmap_nodes),
            "node_op_types": [str(n.op_type) for n in model_proto.graph.node],
        },
        "python_checks": {
            "lgbm_live_vs_npz_max_abs_err": lgbm_live_vs_npz_err,
            "ort_batch_max_abs_err": ort_parity["max_abs_err_batch"],
            "ort_single_max_abs_err": ort_parity["max_abs_err_single"],
            "python_nan_blocked": py_nan_blocked,
            "python_inf_blocked": py_inf_blocked,
        },
        "mt5_probe_run": {
            "report_path": str(archived_report) if archived_report else None,
            "archived_logs": archived_logs,
            "fresh_out_csv_path": str(fresh_out_archived),
            "fresh_out_csv_sha256": fresh_csv["csv_sha256"],
            "matches_wave2b_out_csv_sha256": (prior_out_sha == fresh_csv["csv_sha256"]) if prior_out_sha else None,
            **log_info,
        },
        "four_way_parity_500": four_way,
    }


# ---------------------------------------------------------------------------
# 6. Mission 2: Controlled Full-2024 `Model=1` MT5 Strategy Tester Ablation
# ---------------------------------------------------------------------------


def run_v104_full2024_mt5_ablation_job(
    *,
    run_tag: str,
    enable_ml_filter: bool,
    ml_mode: int = ML_MODE_ONNX_OR_FALLBACK,
    ml_threshold: float = DEFAULT_ML_THRESHOLD,
    contract_sku: str = "FTMO_STD_10K_V104_ML_FUNDED_1X",
    from_date: str = "2024.01.02",
    to_date: str = "2024.12.31",
    deposit: int = 10_000,
    model: int = 1,
    leverage: int = 100,
    portable_root: Path = DEFAULT_PORTABLE_ROOT,
    v104_ex5_path: Path = DEFAULT_V104_EX5_PATH,
    src_preset_path: Path = DEFAULT_FUNDED_1X_PRESET,
    ml_dir: Path = DEFAULT_ML_DIR,
    work_dir: Path = DEFAULT_CERT_WORKDIR,
    timeout_sec: int = 420,
) -> dict[str, Any]:
    """Run one controlled full-2024 `Model=1` MT5 Strategy Tester job for `Naqex_Master_Prop7E_v104_ML.ex5`."""
    p_root = assert_safe_portable_root(portable_root)
    assert_dev_date_sealed(to_date, from_date)

    # Sync compiled v104_ML .ex5, immutable red-news CSV, and ONNX file into portable sandbox ONLY
    v104_sha = _sync_file_if_changed(v104_ex5_path, p_root / "MQL5" / "Experts" / "Naqex" / v104_ex5_path.name)
    _sync_file_if_changed(DEFAULT_RED_NEWS_CSV, p_root / "MQL5" / "Files" / DEFAULT_RED_NEWS_CSV.name)
    onnx_sha = _sync_file_if_changed(ml_dir / ONNX_MODEL_FILENAME, p_root / "MQL5" / "Files" / ONNX_MODEL_FILENAME)

    run_dir = work_dir / run_tag
    run_dir.mkdir(parents=True, exist_ok=True)
    set_filename = f"naqex_w4g05_{run_tag}.set"
    set_path = p_root / "MQL5" / "Profiles" / "Tester" / set_filename
    render_v104_tester_set(
        src_preset_path,
        initial_balance_usd=float(deposit),
        enable_ml_filter=enable_ml_filter,
        ml_mode=ml_mode,
        ml_threshold=ml_threshold,
        ml_onnx_file=ONNX_MODEL_FILENAME,
        contract_sku=contract_sku,
        out_path=set_path,
    )

    report_stem = f"w4g05_{run_tag}"
    for stale in (p_root / f"{report_stem}.htm", p_root / f"{report_stem}.html"):
        stale.unlink(missing_ok=True)

    ini_path = run_dir / "tester.ini"
    ini_path.write_text(
        render_safe_tester_ini(
            expert_rel_path="Naqex\\Naqex_Master_Prop7E_v104_ML.ex5",
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

    log_info = parse_v104_ml_tester_log(combined_logs)
    metrics = summarize_mt5_ablation_run(parsed, initial_balance_usd=float(deposit))

    # Fail-closed Holdout check on max deal date
    if metrics["max_deal_date"] >= "2025-01-01":
        raise HoldoutViolationError(f"HOLDOUT_BREACH[{run_tag}]: max_deal_date={metrics['max_deal_date']}")

    payload = {
        "run_tag": run_tag,
        "expert": "Naqex_Master_Prop7E_v104_ML.ex5",
        "v104_ex5_sha256": v104_sha,
        "onnx_sha256": onnx_sha,
        "preset_source": Path(src_preset_path).name,
        "contract_sku": contract_sku,
        "enable_ml_filter": enable_ml_filter,
        "ml_mode": int(ml_mode),
        "ml_threshold": float(ml_threshold),
        "from_date": from_date,
        "to_date": to_date,
        "model": int(model),
        "deposit_usd": float(deposit),
        "allow_live_trading": 0,
        "holdout_rows_analysed": 0,
        "rc": rc,
        "timed_out": timed_out,
        "elapsed_sec": elapsed,
        "report_path": str(archived_report),
        "archived_logs": archived_logs,
        "log_telemetry": log_info,
        "metrics": metrics,
        "positions": parsed["positions"],
    }
    atomic_write_json(run_dir / "parsed_ablation.json", payload)
    return payload


def run_full_w4_g05_certification(
    *,
    ml_dir: Path = DEFAULT_ML_DIR,
    portable_root: Path = DEFAULT_PORTABLE_ROOT,
    work_dir: Path = DEFAULT_CERT_WORKDIR,
    audit_receipt_path: Path = DEFAULT_AUDIT_RECEIPT,
    dropbox_receipt_path: Path = DEFAULT_DROPBOX_RECEIPT,
    tol: float = PARITY_MAX_ABS_TOL,
) -> dict[str, Any]:
    """Execute complete `W4-G05` independent certification and write byte-identical receipts."""
    t_start = time.perf_counter()
    immutables = verify_immutables_and_binary_hygiene()
    assert_zero_all_mt5_processes(context="cert-start")

    # 1. Independent 4-way 500-vector numerical parity certification
    parity500_cert = run_independent_parity500_certification(
        ml_dir=ml_dir,
        portable_root=portable_root,
        work_dir=work_dir,
        tol=tol,
    )

    # 2. Load untouched v103 baseline (`Funded_1x_10K_2024_M1` from w4_t0_parity98_receipt.json + HTML report)
    if not DEFAULT_W4_T0_PARITY98_RECEIPT.is_file():
        raise FileNotFoundError(f"MISSING_V103_PARITY98_RECEIPT: {DEFAULT_W4_T0_PARITY98_RECEIPT}")
    t0_receipt = json.loads(DEFAULT_W4_T0_PARITY98_RECEIPT.read_text(encoding="utf-8"))
    v103_receipt_summary = t0_receipt["model1_same_feed_runs"]["Funded_1x_10K_2024_M1"]["mt5_summary"]

    v103_parsed = parse_v103_mt5_html_positions(DEFAULT_V103_FUNDED_1X_HTML)
    if not v103_parsed.get("ok"):
        raise RuntimeError(f"V103_BASELINE_HTML_PARSE_FAILED: {v103_parsed.get('error')}")
    v103_metrics = summarize_mt5_ablation_run(v103_parsed, initial_balance_usd=10_000.0)
    if v103_metrics["trades"] != int(v103_receipt_summary["positions_count"]):
        raise RuntimeError(
            f"V103_BASELINE_MISMATCH: html_trades={v103_metrics['trades']} != "
            f"receipt={v103_receipt_summary['positions_count']}"
        )

    # 3. Run controlled Full-2024 Model=1 MT5 Strategy Tester ablations (ALL 3 modes!)
    ablation_onnx = run_v104_full2024_mt5_ablation_job(
        run_tag="v104_ML_ONNX_Funded1x_10K_2024_M1",
        enable_ml_filter=True,
        ml_mode=ML_MODE_ONNX_OR_FALLBACK,
        contract_sku="FTMO_STD_10K_V104_ML_ONNX_FUNDED_1X",
        portable_root=portable_root,
        ml_dir=ml_dir,
        work_dir=work_dir,
    )
    ablation_disabled = run_v104_full2024_mt5_ablation_job(
        run_tag="v104_ML_Disabled_Funded1x_10K_2024_M1",
        enable_ml_filter=False,
        ml_mode=ML_MODE_ONNX_OR_FALLBACK,
        contract_sku="FTMO_STD_10K_V104_ML_OFF_FUNDED_1X",
        portable_root=portable_root,
        ml_dir=ml_dir,
        work_dir=work_dir,
    )
    ablation_pure = run_v104_full2024_mt5_ablation_job(
        run_tag="v104_ML_PureMQL5_Funded1x_10K_2024_M1",
        enable_ml_filter=True,
        ml_mode=ML_MODE_PURE_MQL5_ONLY,
        contract_sku="FTMO_STD_10K_V104_ML_PURE_FUNDED_1X",
        portable_root=portable_root,
        ml_dir=ml_dir,
        work_dir=work_dir,
    )

    # 4. Side-by-side comparisons
    diff_onnx_vs_v103 = compare_ablation_positions(
        baseline_positions=v103_parsed["positions"],
        candidate_positions=ablation_onnx["positions"],
        initial_balance_usd=10_000.0,
    )
    diff_disabled_vs_v103 = compare_ablation_positions(
        baseline_positions=v103_parsed["positions"],
        candidate_positions=ablation_disabled["positions"],
        initial_balance_usd=10_000.0,
    )
    diff_pure_vs_onnx = compare_ablation_positions(
        baseline_positions=ablation_onnx["positions"],
        candidate_positions=ablation_pure["positions"],
        initial_balance_usd=10_000.0,
    )

    def _strip_positions(run_dict: Mapping[str, Any]) -> dict[str, Any]:
        return {k: v for k, v in run_dict.items() if k != "positions"}

    # Check hard W4-G05 gates
    onnx_log = ablation_onnx["log_telemetry"]
    dis_log = ablation_disabled["log_telemetry"]
    pure_log = ablation_pure["log_telemetry"]

    disabled_reproduces_v103 = bool(
        ablation_disabled["metrics"]["trades"] == v103_metrics["trades"]
        and abs(ablation_disabled["metrics"]["net_pnl_usd"] - v103_metrics["net_pnl_usd"]) <= 0.05
        and diff_disabled_vs_v103["filtered_trades_count"] == 0
        and diff_disabled_vs_v103["newly_unblocked_trades_count"] == 0
    )
    pure_matches_onnx = bool(
        ablation_pure["metrics"]["trades"] == ablation_onnx["metrics"]["trades"]
        and abs(ablation_pure["metrics"]["net_pnl_usd"] - ablation_onnx["metrics"]["net_pnl_usd"]) <= 0.05
        and diff_pure_vs_onnx["filtered_trades_count"] == 0
        and diff_pure_vs_onnx["newly_unblocked_trades_count"] == 0
    )

    mt5_procs_after = len(list_all_running_mt5_processes())
    if mt5_procs_after != 0:
        raise RuntimeError(f"MT5_PROCS_NON_ZERO_AFTER_CERT: {mt5_procs_after}")

    w4g05_f01_closed = bool(
        diff_onnx_vs_v103["delayed_same_side_reentries_count"] == 0
        and diff_onnx_vs_v103["flipped_side_reentries_count"] == 0
        and diff_onnx_vs_v103["permanently_filtered_engine_days_count"] > 0
    )

    gates = {
        "four_way_parity_500_le_1e_5": parity500_cert["four_way_parity_500"]["passed"],
        "zero_zipmap_nodes": parity500_cert["onnx_model"]["zipmap_node_count"] == 0,
        "nan_inf_fail_closed_mt5_and_python": bool(
            parity500_cert["mt5_probe_run"]["nan_blocked"]
            and parity500_cert["mt5_probe_run"]["inf_blocked"]
            and parity500_cert["python_checks"]["python_nan_blocked"]
            and parity500_cert["python_checks"]["python_inf_blocked"]
        ),
        "v104_onnx_full2024_zero_errors": bool(
            ablation_onnx["rc"] == 0 and not ablation_onnx["timed_out"] and onnx_log["error_lines_count"] == 0
        ),
        "v104_onnx_backend_active": bool(onnx_log["ml_onnx_ready"] is True and onnx_log["ml_backend"] == "ONNX"),
        "v104_onnx_swap_zero": bool(ablation_onnx["metrics"]["swap_zero_ok"]),
        "v104_disabled_reproduces_v103_exact": bool(
            ablation_disabled["rc"] == 0
            and dis_log["error_lines_count"] == 0
            and ablation_disabled["metrics"]["swap_zero_ok"]
            and disabled_reproduces_v103
        ),
        "v104_pure_mql5_fallback_full2024_zero_errors": bool(
            ablation_pure["rc"] == 0
            and not ablation_pure["timed_out"]
            and pure_log["error_lines_count"] == 0
            and pure_log["ml_backend"] == "PURE_MQL5"
            and ablation_pure["metrics"]["swap_zero_ok"]
        ),
        "v104_pure_mql5_matches_onnx_full2024": pure_matches_onnx,
        "w4g05_f01_zero_delayed_or_flipped_reentries": w4g05_f01_closed,
        "mt5_procs_zero": mt5_procs_after == 0,
        "immutables_and_binary_hygiene_ok": bool(
            immutables["v103_mq5_untouched"]
            and immutables["exports_ex5_count"] == 0
            and immutables["private_vault_ex5_count"] == 0
        ),
    }
    all_gates_passed = all(gates.values())

    receipt: dict[str, Any] = {
        "schema": SCHEMA_RECEIPT,
        "worker": "w4-m1-mt5-onnx",
        "wave": "Wave 2C Barrier (Total Offensive #4 v4.8.1 FINAL)",
        "gate": "W4-G05",
        "status": "PASS" if all_gates_passed else "FAIL",
        "w4_g05_verdict": "CERTIFIED_PASS_ONNX_PARITY_AND_FULL2024_ABLATION" if all_gates_passed else "FAIL",
        "mt5_lock_status": "RELEASED",
        "mt5_procs_after": mt5_procs_after,
        "generated_utc": datetime.now(UTC).isoformat(),
        "elapsed_total_sec": round(time.perf_counter() - t_start, 2),
        "source_trial_id": "w4_09_lgbm_tf_d2_n60",
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
            "oos_label": CONSUMED_CLB_TAG,
            "zero_bare_asserts": True,
            "lazy_onnx_ml_imports_only": True,
            "no_window_creationflags": True,
            "zipmap_node_count": int(parity500_cert["onnx_model"]["zipmap_node_count"]),
            "exports_ex5_count": int(immutables["exports_ex5_count"]),
            "private_vault_ex5_count": int(immutables["private_vault_ex5_count"]),
            "mt5_procs_count": mt5_procs_after,
            "git_commits_made": 0,
        },
        "immutables_verification": immutables,
        "gates": gates,
        "independent_parity_500": parity500_cert,
        "full2024_mt5_ablation": {
            "window": "2024.01.02..2024.12.31",
            "model": 1,
            "deposit_usd": 10_000.0,
            "preset": "FTMO_Std10K_v103_Funded_1x.set",
            "baseline_v103_funded_1x": {
                "source_receipt": str(DEFAULT_W4_T0_PARITY98_RECEIPT.relative_to(REPO_ROOT)),
                "source_html": str(DEFAULT_V103_FUNDED_1X_HTML.relative_to(REPO_ROOT)),
                "receipt_mt5_summary": v103_receipt_summary,
                "metrics": v103_metrics,
            },
            "v104_ml_onnx": _strip_positions(ablation_onnx),
            "v104_ml_disabled": _strip_positions(ablation_disabled),
            "v104_ml_pure_mql5": _strip_positions(ablation_pure),
            "comparisons": {
                "v104_ml_onnx_vs_v103_baseline": {
                    "delta_trades": ablation_onnx["metrics"]["trades"] - v103_metrics["trades"],
                    "filtered_trades_count": diff_onnx_vs_v103["filtered_trades_count"],
                    "newly_unblocked_trades_count": diff_onnx_vs_v103["newly_unblocked_trades_count"],
                    "kept_trades_count": diff_onnx_vs_v103["kept_trades_count"],
                    "overall_retention_ratio": diff_onnx_vs_v103["overall_retention_ratio"],
                    "delta_net_pnl_usd": round_cent_half_up(
                        ablation_onnx["metrics"]["net_pnl_usd"] - v103_metrics["net_pnl_usd"]
                    ),
                    "delta_profit_factor": round(
                        float(ablation_onnx["metrics"]["profit_factor"] or 0.0)
                        - float(v103_metrics["profit_factor"] or 0.0),
                        4,
                    ),
                    "delta_equity_dd_pct": round(
                        float(ablation_onnx["metrics"]["equity_dd_pct"] or 0.0)
                        - float(v103_metrics["equity_dd_pct"] or 0.0),
                        4,
                    ),
                    "delta_worst_day_pct": diff_onnx_vs_v103["delta_worst_day_pct"],
                    "filtered_trades_baseline_net_pnl_usd": diff_onnx_vs_v103["filtered_trades_baseline_net_pnl_usd"],
                    "filtered_trades_baseline_win_rate_pct": diff_onnx_vs_v103["filtered_trades_baseline_win_rate_pct"],
                    "permanently_filtered_engine_days_count": diff_onnx_vs_v103[
                        "permanently_filtered_engine_days_count"
                    ],
                    "permanently_filtered_baseline_net_pnl_usd": diff_onnx_vs_v103[
                        "permanently_filtered_baseline_net_pnl_usd"
                    ],
                    "delayed_same_side_reentries_count": diff_onnx_vs_v103["delayed_same_side_reentries_count"],
                    "delayed_same_side_pnl_delta_usd": diff_onnx_vs_v103["delayed_same_side_pnl_delta_usd"],
                    "flipped_side_reentries_count": diff_onnx_vs_v103["flipped_side_reentries_count"],
                    "flipped_side_pnl_delta_usd": diff_onnx_vs_v103["flipped_side_pnl_delta_usd"],
                    "total_ml_affected_engine_days": diff_onnx_vs_v103["total_ml_affected_engine_days"],
                    "all_ml_blocked_baseline_net_pnl_usd": diff_onnx_vs_v103["all_ml_blocked_baseline_net_pnl_usd"],
                    "all_ml_blocked_baseline_win_rate_pct": diff_onnx_vs_v103["all_ml_blocked_baseline_win_rate_pct"],
                    "affected_by_engine": diff_onnx_vs_v103["affected_by_engine"],
                    "per_engine_retention": diff_onnx_vs_v103["per_engine_retention"],
                },
                "v104_ml_disabled_vs_v103_baseline": {
                    "exact_reproduction": disabled_reproduces_v103,
                    "delta_trades": ablation_disabled["metrics"]["trades"] - v103_metrics["trades"],
                    "delta_net_pnl_usd": round_cent_half_up(
                        ablation_disabled["metrics"]["net_pnl_usd"] - v103_metrics["net_pnl_usd"]
                    ),
                    "delta_equity_dd_pct": round(
                        float(ablation_disabled["metrics"]["equity_dd_pct"] or 0.0)
                        - float(v103_metrics["equity_dd_pct"] or 0.0),
                        4,
                    ),
                    "diff": diff_disabled_vs_v103,
                },
                "v104_ml_pure_mql5_vs_v104_ml_onnx": {
                    "exact_match": pure_matches_onnx,
                    "delta_trades": ablation_pure["metrics"]["trades"] - ablation_onnx["metrics"]["trades"],
                    "delta_net_pnl_usd": round_cent_half_up(
                        ablation_pure["metrics"]["net_pnl_usd"] - ablation_onnx["metrics"]["net_pnl_usd"]
                    ),
                    "delta_equity_dd_pct": round(
                        float(ablation_pure["metrics"]["equity_dd_pct"] or 0.0)
                        - float(ablation_onnx["metrics"]["equity_dd_pct"] or 0.0),
                        4,
                    ),
                    "diff": diff_pure_vs_onnx,
                },
            },
            "semantic_findings": [
                {
                    "id": "W4G05-F01",
                    "status": "CLOSED_VERIFIED" if w4g05_f01_closed else "OPEN",
                    "severity": "RESOLVED" if w4g05_f01_closed else "HIGH_PROMOTION_GATE_FINDING",
                    "location": "tooling/ai-engines/exports/Naqex_Master_Prop7E_v104_ML.mq5:934",
                    "summary": (
                        "Added g_signals.MarkEngineTraded(it.magic, it.session_day_key) on !mlAllowed "
                        "to enforce 1-shot session lockout matching Wave 2A Python toxic filter semantics "
                        "(eliminating the pre-fix 107 delayed same-side chases + 14 flipped-side re-entries)."
                        if w4g05_f01_closed
                        else "ProcessIntentAtomicallyV104 returns on !mlAllowed WITHOUT calling "
                        "g_signals.MarkEngineTraded(it.magic, it.session_day_key)."
                    ),
                    "pre_fix_baseline_impact": {
                        "v104_onnx_trades": 467,
                        "v104_onnx_net_pnl_usd": 559.44,
                        "delta_vs_v103_usd": -57.43,
                        "permanently_filtered_engine_days": 2,
                        "delayed_same_side_reentries": 107,
                        "flipped_side_reentries": 14,
                    },
                    "observed_full2024_impact": {
                        "total_ml_affected_engine_days": diff_onnx_vs_v103["total_ml_affected_engine_days"],
                        "permanently_filtered_engine_days": diff_onnx_vs_v103[
                            "permanently_filtered_engine_days_count"
                        ],
                        "delayed_same_side_reentries": diff_onnx_vs_v103["delayed_same_side_reentries_count"],
                        "flipped_side_reentries": diff_onnx_vs_v103["flipped_side_reentries_count"],
                        "all_ml_blocked_baseline_net_pnl_usd": diff_onnx_vs_v103[
                            "all_ml_blocked_baseline_net_pnl_usd"
                        ],
                        "all_ml_blocked_baseline_win_rate_pct": diff_onnx_vs_v103[
                            "all_ml_blocked_baseline_win_rate_pct"
                        ],
                        "delayed_same_side_pnl_delta_usd": diff_onnx_vs_v103["delayed_same_side_pnl_delta_usd"],
                        "flipped_side_pnl_delta_usd": diff_onnx_vs_v103["flipped_side_pnl_delta_usd"],
                        "actual_net_pnl_delta_vs_v103_usd": round_cent_half_up(
                            ablation_onnx["metrics"]["net_pnl_usd"] - v103_metrics["net_pnl_usd"]
                        ),
                    },
                }
            ],
        },
    }

    atomic_write_json(audit_receipt_path, receipt)
    atomic_write_json(dropbox_receipt_path, receipt)
    return receipt


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Independent W4-G05 MT5 ONNX 3-way parity & Full-2024 Strategy Tester ablation certifier."
    )
    parser.add_argument("--ml-dir", type=Path, default=DEFAULT_ML_DIR)
    parser.add_argument("--portable-root", type=Path, default=DEFAULT_PORTABLE_ROOT)
    parser.add_argument("--work-dir", type=Path, default=DEFAULT_CERT_WORKDIR)
    parser.add_argument("--audit-receipt", type=Path, default=DEFAULT_AUDIT_RECEIPT)
    parser.add_argument("--dropbox-receipt", type=Path, default=DEFAULT_DROPBOX_RECEIPT)
    parser.add_argument("--tol", type=float, default=PARITY_MAX_ABS_TOL)
    args = parser.parse_args(list(argv) if argv is not None else None)

    receipt = run_full_w4_g05_certification(
        ml_dir=args.ml_dir,
        portable_root=args.portable_root,
        work_dir=args.work_dir,
        audit_receipt_path=args.audit_receipt,
        dropbox_receipt_path=args.dropbox_receipt,
        tol=args.tol,
    )
    compact = {
        "status": receipt["status"],
        "w4_g05_verdict": receipt["w4_g05_verdict"],
        "mt5_procs_after": receipt["mt5_procs_after"],
        "overall_max_abs_err": receipt["independent_parity_500"]["four_way_parity_500"]["overall_max_abs_err"],
        "v103_trades": receipt["full2024_mt5_ablation"]["baseline_v103_funded_1x"]["metrics"]["trades"],
        "v103_net_pnl_usd": receipt["full2024_mt5_ablation"]["baseline_v103_funded_1x"]["metrics"]["net_pnl_usd"],
        "v104_onnx_trades": receipt["full2024_mt5_ablation"]["v104_ml_onnx"]["metrics"]["trades"],
        "v104_onnx_net_pnl_usd": receipt["full2024_mt5_ablation"]["v104_ml_onnx"]["metrics"]["net_pnl_usd"],
        "filtered_trades_count": receipt["full2024_mt5_ablation"]["comparisons"]["v104_ml_onnx_vs_v103_baseline"][
            "filtered_trades_count"
        ],
        "v104_disabled_exact_v103": receipt["full2024_mt5_ablation"]["comparisons"][
            "v104_ml_disabled_vs_v103_baseline"
        ]["exact_reproduction"],
        "v104_pure_exact_onnx": receipt["full2024_mt5_ablation"]["comparisons"]["v104_ml_pure_mql5_vs_v104_ml_onnx"][
            "exact_match"
        ],
        "gates": receipt["gates"],
    }
    print(json.dumps(compact, indent=2))
    return 0 if receipt["status"] == "PASS" else 1


__all__ = [
    "DEFAULT_AUDIT_RECEIPT",
    "DEFAULT_CERT_WORKDIR",
    "DEFAULT_DROPBOX_RECEIPT",
    "DEFAULT_FUNDED_1X_PRESET",
    "DEFAULT_ML_THRESHOLD",
    "DEFAULT_PROBE_EX5_PATH",
    "DEFAULT_V103_FUNDED_1X_HTML",
    "DEFAULT_V104_EX5_PATH",
    "ML_MODE_ONNX_ONLY_FAIL_CLOSED",
    "ML_MODE_ONNX_OR_FALLBACK",
    "ML_MODE_PURE_MQL5_ONLY",
    "ORDER_SEND_CAPABLE",
    "ORDER_SEND_COUNT",
    "SCHEMA_RECEIPT",
    "SPEND_VND",
    "_NO_WINDOW_FLAGS",
    "compare_ablation_positions",
    "compute_four_way_parity_metrics",
    "compute_worst_day_metrics",
    "main",
    "parse_parity500_probe_log",
    "parse_parity500_probe_output_csv",
    "parse_v104_ml_tester_log",
    "render_safe_tester_ini",
    "render_v104_tester_set",
    "run_full_w4_g05_certification",
    "run_independent_parity500_certification",
    "run_v104_full2024_mt5_ablation_job",
    "summarize_mt5_ablation_run",
    "verify_immutables_and_binary_hygiene",
]

if __name__ == "__main__":
    raise SystemExit(main())

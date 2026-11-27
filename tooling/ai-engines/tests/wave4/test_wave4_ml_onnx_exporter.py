"""Tests for Wave 4 LightGBM ONNX & Pure-MQL5 Tree Fallback Exporter (`W4-G05`).

Covers:
  1. Lazy-import purity & zero bare `assert`s under clean `python -O` subprocess (`-m "not local_cache"`).
  2. Poisoned `NaN`, `+Inf`, `-Inf`, `bool`, and wrong-dim feature vectors rejected fail-closed under `python -O`.
  3. Immutable `Naqex_Master_Prop7E_v103.mq5` SHA-256 unchanged + `Naqex_Master_Prop7E_v104_ML.mq5`
     & `Naqex_ML_Parity500_Probe.mq5` structural safety invariants (`InpDryRunLogOnly=true`, zero
     `OrderSend` in Probe & `.mqh`, zero `.ex5` binaries in `exports/` or `private_vault/`).
  4. Offline synthetic LightGBM -> ONNX (`zipmap=False`, `0` `ZipMap` nodes) + `onnxruntime` parity
     `<= 1e-5` (both batch and single-sample) + generated `.mqh` parsed tree mirror parity `<= 1e-5`
     (gated via `pytest.importorskip` so CI without ONNX/LightGBM wheels stays green!).
  5. `@pytest.mark.local_cache` verification of production `w4_09_lgbm_tf_d2_n60` artifacts:
     `naqex_v104_lgbm.onnx` (`0` `ZipMap` nodes), `Python LightGBM == onnxruntime <= 1e-5` on all
     500 Fold-4 OOS vectors, parsed `Include/Naqex_ML_Filter_v104.mqh` mirror `<= 1e-5`, portable
     MT5 `MQL5/Files/` copies bit-for-bit identical, and `holdout_rows_analysed == 0`.
"""

from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from quant_factory.wave4 import ml_onnx_exporter as exp

ROOT = Path(__file__).resolve().parents[4]
EXPORTS_DIR = ROOT / "tooling" / "ai-engines" / "exports"
PRIVATE_VAULT_DIR = ROOT / "private_vault"


# ---------------------------------------------------------------------------
# 1. Lazy Imports, Zero Bare `assert`s, and Clean `python -O` Execution
# ---------------------------------------------------------------------------


def test_lazy_imports_zero_bare_asserts_and_clean_python_O_import() -> None:
    mod_path = ROOT / "tooling" / "ai-engines" / "quant_factory" / "wave4" / "ml_onnx_exporter.py"
    src = mod_path.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(mod_path))

    assert_nodes = [n for n in ast.walk(tree) if isinstance(n, ast.Assert)]
    assert assert_nodes == [], f"Found bare assert statements at lines {[n.lineno for n in assert_nodes]}"

    code = (
        "import sys; "
        "from quant_factory.wave4 import ml_onnx_exporter as e; "
        "forbidden = ['onnx', 'onnxmltools', 'skl2onnx', 'onnxruntime', 'lightgbm', 'sklearn', 'catboost', 'duckdb']; "
        "loaded = [m for m in forbidden if m in sys.modules]; "
        "assert not loaded, f'Eagerly imported optional packages: {loaded}'; "
        "assert e.ORDER_SEND_CAPABLE is False and e.ORDER_SEND_COUNT == 0; "
        "assert e.HOLDOUT_CUTOFF_DATE == '2024-12-31'; "
        "print('CLEAN_ONNX_EXPORTER_IMPORT_OK')"
    )
    proc = subprocess.run(
        [sys.executable, "-O", "-c", code],
        cwd=str(ROOT / "tooling" / "ai-engines"),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, f"stderr={proc.stderr}\nstdout={proc.stdout}"
    assert "CLEAN_ONNX_EXPORTER_IMPORT_OK" in proc.stdout


# ---------------------------------------------------------------------------
# 2. Poisoned NaN / Inf / Bool Inputs Rejected Fail-Closed Under `python -O`
# ---------------------------------------------------------------------------


def _strip_mql5_comments(src: str) -> str:
    no_block = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    return re.sub(r"//[^\n]*", "", no_block)


def test_poisoned_nan_inf_bool_vectors_rejected_fail_closed_under_python_O() -> None:
    # Run inside an actual `python -O` subprocess to prove zero reliance on bare `assert`!
    code = "\n".join(
        [
            "import numpy as np",
            "from quant_factory.wave4 import ml_onnx_exporter as e",
            "tbl = {",
            "    'n_features': 8, 'n_trees': 1, 'n_nodes': 3,",
            "    'tree_roots': [0], 'node_feat': [0, -1, -1], 'node_left': [1, -1, -1],",
            "    'node_right': [2, -1, -1], 'node_thresh': [0.5, 0.0, 0.0], 'node_leaf': [0.0, -0.2, 0.2],",
            "}",
            "cases = [",
            "    np.array([[np.nan, 0, 0, 0, 0, 1, 0, 0]], dtype=np.float32),",
            "    np.array([[0, np.inf, 0, 0, 0, 1, 0, 0]], dtype=np.float32),",
            "    np.array([[0, -np.inf, 0, 0, 0, 1, 0, 0]], dtype=np.float32),",
            "    np.array([[True, False, 0, 0, 0, 1, 0, 0]], dtype=object),",
            "    np.array([[0.1, 0.2, 0.3]], dtype=np.float32),",
            "]",
            "for idx, bad in enumerate(cases):",
            "    raised = False",
            "    try:",
            "        e.evaluate_flat_trees(tbl, bad)",
            "    except ValueError:",
            "        raised = True",
            "    if not raised:",
            "        raise SystemExit(f'Case {idx} did NOT fail closed under -O')",
            "print('POISONED_FAIL_CLOSED_O_OK')",
        ]
    )
    proc = subprocess.run(
        [sys.executable, "-O", "-c", code],
        cwd=str(ROOT / "tooling" / "ai-engines"),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, f"stderr={proc.stderr}\nstdout={proc.stdout}"
    assert "POISONED_FAIL_CLOSED_O_OK" in proc.stdout


# ---------------------------------------------------------------------------
# 3. Immutable `v103.mq5` SHA-256 & Exported MQL5 Structural Safety Guards
# ---------------------------------------------------------------------------


def test_v103_sha256_unchanged_and_zero_ex5_in_exports_or_private_vault() -> None:
    check = exp.verify_v103_immutable()
    assert check["untouched"] is True
    assert check["sha256"] == exp.V103_EXPECTED_SHA256

    # ZERO .ex5 binaries anywhere inside tracked tooling/ai-engines/exports/ or private_vault/
    stray_exports_ex5 = list(EXPORTS_DIR.rglob("*.ex5"))
    assert stray_exports_ex5 == [], f"FORBIDDEN .ex5 found in exports/: {stray_exports_ex5}"
    if PRIVATE_VAULT_DIR.exists():
        stray_vault_ex5 = list(PRIVATE_VAULT_DIR.rglob("*.ex5"))
        assert stray_vault_ex5 == [], f"FORBIDDEN .ex5 found in private_vault/: {stray_vault_ex5}"

    # Verify v104_ML.mq5 fail-closed defaults & causal-only shift>=1 features
    v104_path = EXPORTS_DIR / "Naqex_Master_Prop7E_v104_ML.mq5"
    assert v104_path.is_file()
    v104_src = v104_path.read_text(encoding="utf-8")
    assert "InpDryRunLogOnly" in v104_src and re.search(r"InpDryRunLogOnly\s*=\s*true", v104_src)
    assert "InpGuardDryRunLogOnly" in v104_src and re.search(r"InpGuardDryRunLogOnly\s*=\s*true", v104_src)
    assert "InpShadowCompareMode" in v104_src and re.search(r"InpShadowCompareMode\s*=\s*true", v104_src)
    assert re.search(r"InpEnableMLFilter\s*=\s*true", v104_src)
    assert re.search(r"InpMLMode\s*=\s*ONNX_OR_PURE_MQL5_FALLBACK", v104_src)
    assert '#include "Include/Naqex_ML_Filter_v104.mqh"' in v104_src
    assert '#property tester_file "naqex_v104_lgbm.onnx"' in v104_src
    # Zero lookahead CopyBuffer shift=0 in v104_ML.mq5
    assert not re.search(r"CopyBuffer\s*\([^,]+,\s*0\s*,\s*0\s*,", v104_src)

    # Verify Parity500 probe EA has ZERO OrderSend / CTrade calls in code
    probe_path = EXPORTS_DIR / "Naqex_ML_Parity500_Probe.mq5"
    assert probe_path.is_file()
    probe_src = probe_path.read_text(encoding="utf-8")
    probe_code = _strip_mql5_comments(probe_src)
    assert "OrderSend" not in probe_code
    assert "CTrade" not in probe_code
    assert '#property tester_file "naqex_v104_lgbm.onnx"' in probe_src
    assert '#property tester_file "wave4_ml_parity_500.csv"' in probe_src


# ---------------------------------------------------------------------------
# 4. Offline Synthetic LightGBM -> ONNX (zipmap=False) + Pure-MQL5 Parity
# ---------------------------------------------------------------------------


def test_offline_synthetic_lightgbm_onnx_zero_zipmap_and_mqh_mirror_parity(tmp_path: Path) -> None:
    lgb = pytest.importorskip("lightgbm")
    onnx = pytest.importorskip("onnx")
    pytest.importorskip("onnxmltools")
    pytest.importorskip("onnxruntime")

    rng = np.random.default_rng(2026)
    n_train, n_val, n_feat = 400, 120, 8
    x_tr = rng.normal(0.0, 1.0, size=(n_train, n_feat)).astype(np.float32)
    z_tr = 0.8 * x_tr[:, 0] - 0.7 * x_tr[:, 2] + 0.6 * x_tr[:, 5] + rng.normal(0.0, 0.5, size=n_train)
    y_tr = (z_tr > 0.0).astype(np.int64)

    x_val = rng.normal(0.0, 1.0, size=(n_val, n_feat)).astype(np.float32)

    clf = lgb.LGBMClassifier(
        n_estimators=20,
        max_depth=2,
        num_leaves=4,
        learning_rate=0.05,
        min_child_samples=20,
        reg_lambda=10.0,
        random_state=42,
        n_jobs=1,
        verbosity=-1,
        force_col_wise=True,
    )
    clf.fit(x_tr, y_tr)
    p_ref = np.asarray(clf.predict_proba(x_val), dtype=np.float64)[:, 1]

    onnx_path = tmp_path / "synth_lgbm.onnx"
    meta = exp.export_lightgbm_to_onnx(clf, n_features=n_feat, out_onnx_path=onnx_path, model_name="synth_lgbm")
    assert meta["zipmap_node_count"] == 0

    proto = onnx.load(str(onnx_path))
    assert all(n.op_type != "ZipMap" for n in proto.graph.node)

    ort_res = exp.verify_onnx_runtime_parity(onnx_path, x_val, p_ref, tol=1e-5)
    assert ort_res["passed"] is True
    assert ort_res["max_abs_err_batch"] <= 1e-5
    assert ort_res["max_abs_err_single"] <= 1e-5

    # Generate pure-MQL5 header from booster dump and verify parsed .mqh mirror <= 1e-5
    tables = exp.extract_flat_tree_tables(clf.booster_.dump_model(), n_features=n_feat)
    synth_proto_json = {
        "source_trial_id": "synth_lgbm_d2_n20",
        "approval_tag": "SYNTHETIC_UNIT_TEST",
        "selected_feature_names": [f"f_{j}" for j in range(n_feat)],
        "train_p_toxic_q20": 0.45,
    }
    mqh_text = exp.render_mql5_filter_header(
        synth_proto_json,
        tables=tables,
        onnx_sha256=meta["onnx_sha256"],
        onnx_filename="synth_lgbm.onnx",
    )
    mqh_code = _strip_mql5_comments(mqh_text)
    assert "OrderSend" not in mqh_code
    assert "CTrade" not in mqh_code
    assert "OnnxCreateFromBuffer" in mqh_code
    assert "OnnxSetInputShape" in mqh_code
    assert "OnnxSetOutputShape" in mqh_code
    assert "OnnxRun" in mqh_code

    p_mqh = exp.evaluate_mqh_source_python_mirror(mqh_text, x_val)
    assert float(np.max(np.abs(p_mqh - p_ref))) <= 1e-5

    # Poisoned NaN/Inf must fail-closed on verify_onnx_runtime_parity as well
    x_bad = x_val.copy()
    x_bad[0, 0] = np.nan
    with pytest.raises(ValueError, match="NON_FINITE_FEATURE_INPUT"):
        exp.verify_onnx_runtime_parity(onnx_path, x_bad, p_ref, tol=1e-5)


# ---------------------------------------------------------------------------
# 5. Production W4-G05 Artifact Parity (`w4_09_lgbm_tf_d2_n60`, 500 Vectors)
# ---------------------------------------------------------------------------


@pytest.mark.local_cache
def test_production_w4_09_onnx_zero_zipmap_and_500_vector_parity() -> None:
    onnx = pytest.importorskip("onnx")
    pytest.importorskip("onnxruntime")

    ml_dir = ROOT / ".runtime" / "offensive4" / "ml"
    onnx_path = ml_dir / exp.ONNX_MODEL_FILENAME
    csv_path = ml_dir / exp.PARITY_CSV_FILENAME
    report_path = ml_dir / exp.EXPORT_REPORT_FILENAME
    mqh_path = exp.DEFAULT_MQH_PATH
    portable_onnx = exp.DEFAULT_PORTABLE_FILES_DIR / exp.ONNX_MODEL_FILENAME
    portable_csv = exp.DEFAULT_PORTABLE_FILES_DIR / exp.PARITY_CSV_FILENAME

    for req in (onnx_path, csv_path, report_path, mqh_path, portable_onnx, portable_csv):
        assert req.is_file(), f"Missing W4-G05 artifact: {req}"

    bundle = exp.load_prototype_bundle(ml_dir)
    x_500 = bundle["X"]
    p_ref = bundle["pred_proba_f64"]
    sizes_ref = bundle["pred_size_toxic_filter"]
    threshold = float(bundle["proto_json"]["train_p_toxic_q20"])

    # 1. ONNX graph has 0 ZipMap nodes and passes checker
    proto = onnx.load(str(onnx_path))
    onnx.checker.check_model(proto)
    zipmap_nodes = [n for n in proto.graph.node if n.op_type == "ZipMap"]
    assert zipmap_nodes == [], f"Unexpected ZipMap nodes in {onnx_path}"

    # 2. Python LightGBM == onnxruntime <= 1e-5 across ALL 500 vectors (batch & single-sample)
    ort_res = exp.verify_onnx_runtime_parity(
        onnx_path,
        x_500,
        p_ref,
        tol=1e-5,
        threshold=threshold,
        ref_sizes=sizes_ref,
    )
    assert ort_res["passed"] is True
    assert ort_res["n_samples"] == 500
    assert ort_res["max_abs_err_batch"] <= 1e-5
    assert ort_res["max_abs_err_single"] <= 1e-5
    assert ort_res["toxic_filter_decision_agreement"] == 1.0

    # 3. Generated Include/Naqex_ML_Filter_v104.mqh parsed tree mirror == Python LightGBM <= 1e-5
    mqh_raw = mqh_path.read_bytes()
    assert not mqh_raw.startswith(b"\xef\xbb\xbf")
    assert b"\r\n" not in mqh_raw
    mqh_text = mqh_raw.decode("utf-8")
    mqh_code = _strip_mql5_comments(mqh_text)
    assert "OrderSend" not in mqh_code
    assert "CTrade" not in mqh_code
    p_mqh = exp.evaluate_mqh_source_python_mirror(mqh_text, x_500)
    assert float(np.max(np.abs(p_mqh - p_ref))) <= 1e-5

    # 4. Portable MT5 MQL5/Files copies match SHA-256 bit-for-bit
    assert exp.sha256_file(portable_onnx) == exp.sha256_file(onnx_path)
    assert exp.sha256_file(portable_csv) == exp.sha256_file(csv_path)

    # 5. Export report invariants
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["hard_invariants"]["order_send_count"] == 0
    assert report["hard_invariants"]["holdout_rows_analysed"] == 0
    assert report["hard_invariants"]["zipmap_node_count"] == 0
    assert report["v103_immutable_check"]["untouched"] is True

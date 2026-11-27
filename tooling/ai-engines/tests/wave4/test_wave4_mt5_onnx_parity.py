"""Offline CI-safe + local_cache certification tests for Wave 4 MT5 ONNX Parity (`W4-G05`).

All checks use `_check(...)` (ZERO bare `assert` statements) so 100% of assertions
remain active under `python -O -m pytest` (`[ARCH-02]`).

Offline CI tests (`-m "not local_cache"`):
  1. Static safety: LF-only, 0 BOM, 0 bare `assert`s, lazy ONNX/ML imports only,
     0 `MetaTrader5` imports, 0 `order_send` refs, `creationflags` on every `subprocess.run`.
  2. Fail-closed Holdout `< 2025-01-01` seal on Tester INI & safe `.set` validation under `python -O`.
  3. 4-way numerical parity math (`<= 1e-5` pass/fail + `NaN`/`Inf`/`bool`/shape fail-closed rejection).
  4. Probe CSV + MT5 Tester log parsers & critical runtime error detection.
  5. Controlled full-2024 ablation diff (`filtered_trades_count`, `worst_day_pct`, `swap_zero_ok`, per-engine).
  6. Immutable `v103.mq5` / `PropGuard` / `Signals_7E` / `AGENTS.md` / `quant_core` & zero stray `.ex5` guard.

Local-cache certification test (`@pytest.mark.local_cache`):
  7. Verifies `.runtime/offensive4/audits/w4_m1_mt5_onnx_receipt.json` & `.tmp/swarm_dropbox/w4-m1-mt5-onnx.json`
     (byte-identical, 4-way parity `<= 1e-5`, `0` `ZipMap`, `NaN`/`Inf` blocked, full-2024 `v104_ML` ONNX vs
     `v103` baseline + `ML=false` reproduction + `PURE_MQL5` fallback, `0` errors, `swap=$0.00`, `MT5_PROCS == 0`).
"""

from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from quant_factory.wave4 import verify_mt5_onnx_parity as cert
from quant_factory.wave4.ftmo_m1_exporter import HoldoutViolationError

ROOT = Path(__file__).resolve().parents[4]


def _check(condition: bool, message: str) -> None:
    """Assertion helper immune to `python -O` bytecode stripping."""
    if not condition:
        raise AssertionError(message)


# ---------------------------------------------------------------------------
# 1. Static Safety, Lazy Imports, Zero Bare `assert`s & `creationflags`
# ---------------------------------------------------------------------------


def test_static_safety_lazy_imports_zero_bare_asserts_and_creationflags() -> None:
    src_path = Path(cert.__file__).resolve()
    raw_bytes = src_path.read_bytes()
    _check(not raw_bytes.startswith(b"\xef\xbb\xbf"), "BOM detected in verify_mt5_onnx_parity.py")
    _check(b"\r\n" not in raw_bytes, "CRLF detected in verify_mt5_onnx_parity.py")

    tree = ast.parse(raw_bytes.decode("utf-8"), filename=str(src_path))
    bare_asserts = [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Assert)]
    _check(not bare_asserts, f"Bare assert statement(s) forbidden: lines {bare_asserts}")

    subprocess_run_calls = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                _check(alias.name != "MetaTrader5", "MetaTrader5 import forbidden")
        elif isinstance(node, ast.ImportFrom):
            _check(node.module != "MetaTrader5", "MetaTrader5 from-import forbidden")
        elif isinstance(node, ast.Attribute):
            _check(node.attr != "order_send", "order_send attribute forbidden")
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "subprocess"
            and node.func.attr == "run"
        ):
            subprocess_run_calls += 1
            kw_names = {kw.arg for kw in node.keywords}
            _check(
                "creationflags" in kw_names,
                f"subprocess.run at line {node.lineno} missing creationflags=_NO_WINDOW_FLAGS",
            )
    _check(subprocess_run_calls >= 2, f"Expected >= 2 subprocess.run calls checked, saw {subprocess_run_calls}")

    # Verify clean `python -O` import loads ZERO optional ML/ONNX packages eagerly
    code = "\n".join(
        [
            "import sys",
            "from quant_factory.wave4 import verify_mt5_onnx_parity as c",
            "forbidden = ['onnx', 'onnxmltools', 'skl2onnx', 'onnxruntime', 'lightgbm',",
            "             'sklearn', 'catboost', 'duckdb', 'MetaTrader5']",
            "loaded = [m for m in forbidden if m in sys.modules]",
            "if loaded:",
            "    raise SystemExit(f'Eagerly imported: {loaded}')",
            "if c.ORDER_SEND_CAPABLE is not False or c.ORDER_SEND_COUNT != 0 or c.SPEND_VND != 0:",
            "    raise SystemExit('Safety constants invalid')",
            "print('CLEAN_MT5_ONNX_CERT_IMPORT_OK')",
        ]
    )
    proc = subprocess.run(
        [sys.executable, "-O", "-c", code],
        cwd=str(ROOT / "tooling" / "ai-engines"),
        capture_output=True,
        text=True,
        check=False,
        creationflags=cert._NO_WINDOW_FLAGS,
    )
    _check(proc.returncode == 0, f"stderr={proc.stderr}\nstdout={proc.stdout}")
    _check("CLEAN_MT5_ONNX_CERT_IMPORT_OK" in proc.stdout, f"unexpected stdout={proc.stdout!r}")


# ---------------------------------------------------------------------------
# 2. Holdout Date Seal & Safe Tester INI / `.set` Rendering Under `python -O`
# ---------------------------------------------------------------------------


def test_holdout_date_seal_and_safe_tester_ini_and_set(tmp_path: Path) -> None:
    with pytest.raises(HoldoutViolationError):
        cert.render_safe_tester_ini(
            expert_rel_path="Naqex\\Naqex_Master_Prop7E_v104_ML.ex5",
            from_date="2024.01.02",
            to_date="2025.01.01",
            report_stem="should_fail",
        )

    ini_text = cert.render_safe_tester_ini(
        expert_rel_path="Naqex\\Naqex_Master_Prop7E_v104_ML.ex5",
        set_filename="test_v104.set",
        from_date="2024.01.02",
        to_date="2024.12.31",
        report_stem="w4g05_test",
    )
    for req_line in (
        "AllowLiveTrading=0",
        "Enabled=0",
        "AllowDllImport=0",
        "KeepPrivate=1",
        "Model=1",
        "FromDate=2024.01.02",
        "ToDate=2024.12.31",
        "ShutdownTerminal=1",
        "Visual=0",
    ):
        _check(req_line in ini_text, f"Missing safe INI line: {req_line}")

    src_set = tmp_path / "src_preset.set"
    src_set.write_text(
        "; sample preset\nInpDryRunLogOnly=true\nInpInitialBalanceUSD=10000.00\nInpBasePhaseMult=1.00\n",
        encoding="utf-8",
    )
    src_before = src_set.read_bytes()
    out_set = tmp_path / "transient.set"
    cert.render_v104_tester_set(
        src_set,
        initial_balance_usd=10_000.0,
        enable_ml_filter=True,
        ml_mode=cert.ML_MODE_PURE_MQL5_ONLY,
        ml_threshold=0.457952,
        out_path=out_set,
    )
    _check(src_set.read_bytes() == src_before, "Source preset must never be modified")
    out_txt = out_set.read_text(encoding="utf-8")
    _check("InpEnableMLFilter=true" in out_txt, "Missing InpEnableMLFilter=true")
    _check("InpMLMode=2" in out_txt, "Missing InpMLMode=2")
    _check("InpMLThreshold=0.457952" in out_txt, "Missing InpMLThreshold")

    with pytest.raises(ValueError, match="INVALID_ML_MODE"):
        cert.render_v104_tester_set(
            src_set, initial_balance_usd=10_000.0, enable_ml_filter=True, ml_mode=9, out_path=out_set
        )
    with pytest.raises(ValueError, match="INVALID_ML_THRESHOLD"):
        cert.render_v104_tester_set(
            src_set, initial_balance_usd=10_000.0, enable_ml_filter=True, ml_threshold=1.2, out_path=out_set
        )


# ---------------------------------------------------------------------------
# 3. 4-Way Numerical Parity Math & Fail-Closed NaN/Inf/Bool Rejection
# ---------------------------------------------------------------------------


def test_four_way_parity_metrics_and_poisoned_nan_inf_rejection() -> None:
    rng = np.random.default_rng(42)
    py_p = rng.uniform(0.35, 0.65, size=500)
    # Keep samples clearly away from threshold 0.457952 so tiny 1e-8 noise doesn't flip synthetic threshold
    py_p = np.where(np.abs(py_p - 0.457952) < 1e-4, py_p + 5e-3, py_p)
    sizes = np.where(py_p >= 0.457952, 1.0, 0.0)

    ort_b = py_p + rng.uniform(-5e-8, 5e-8, size=500)
    ort_s = py_p + rng.uniform(-7e-8, 7e-8, size=500)
    mt5_onnx = ort_s + rng.uniform(-2e-9, 2e-9, size=500)
    mt5_pure = py_p + rng.uniform(-5e-13, 5e-13, size=500)
    py_mqh = py_p.copy()

    res = cert.compute_four_way_parity_metrics(
        py_lgbm_proba=py_p,
        ort_batch_proba=ort_b,
        ort_single_proba=ort_s,
        mt5_onnx_proba=mt5_onnx,
        mt5_pure_proba=mt5_pure,
        py_mqh_mirror_proba=py_mqh,
        ref_sizes=sizes,
        threshold=0.457952,
        tol=1e-5,
    )
    _check(res["passed"] is True, f"Expected 4-way parity PASS, got {res}")
    _check(res["n_vectors"] == 500, "Expected 500 vectors")
    _check(res["overall_max_abs_err"] <= 1e-5, f"Unexpected err: {res['overall_max_abs_err']}")
    _check(res["all_decision_agreements_100pct"] is True, "Expected 100% decision agreement")

    # Exceeding tolerance must fail transparently
    mt5_bad = mt5_onnx.copy()
    mt5_bad[10] += 5e-5
    res_fail = cert.compute_four_way_parity_metrics(
        py_lgbm_proba=py_p,
        ort_batch_proba=ort_b,
        ort_single_proba=ort_s,
        mt5_onnx_proba=mt5_bad,
        mt5_pure_proba=mt5_pure,
        py_mqh_mirror_proba=py_mqh,
        ref_sizes=sizes,
    )
    _check(res_fail["passed"] is False, "Expected parity FAIL when error > 1e-5")

    # Poisoned NaN / Inf / bool must raise ValueError fail-closed (even under python -O!)
    for bad_val in (np.nan, np.inf, -np.inf):
        bad_vec = mt5_onnx.copy()
        bad_vec[0] = bad_val
        with pytest.raises(ValueError, match="NON_FINITE_PROB_VECTOR"):
            cert.compute_four_way_parity_metrics(
                py_lgbm_proba=py_p,
                ort_batch_proba=ort_b,
                ort_single_proba=ort_s,
                mt5_onnx_proba=bad_vec,
                mt5_pure_proba=mt5_pure,
                py_mqh_mirror_proba=py_mqh,
                ref_sizes=sizes,
            )

    with pytest.raises(ValueError, match="POISONED_BOOL_PROB_VECTOR"):
        cert.compute_four_way_parity_metrics(
            py_lgbm_proba=py_p,
            ort_batch_proba=np.ones(500, dtype=bool),
            ort_single_proba=ort_s,
            mt5_onnx_proba=mt5_onnx,
            mt5_pure_proba=mt5_pure,
            py_mqh_mirror_proba=py_mqh,
            ref_sizes=sizes,
        )


# ---------------------------------------------------------------------------
# 4. Probe CSV & MT5 Log Parsers (Fail-Closed Error Detection)
# ---------------------------------------------------------------------------


def test_probe_csv_and_mt5_log_parsers(tmp_path: Path) -> None:
    good_csv = tmp_path / "good_probe.csv"
    header = (
        "row_idx,ref_proba,onnx_proba,pure_mql5_proba,"
        "abs_err_onnx_ref,abs_err_pure_ref,abs_err_onnx_pure,"
        "ref_size,onnx_size,pure_size"
    )
    lines = [header]
    for i in range(5):
        lines.append(f"{i},0.500000000000,0.500000010000,0.500000000000,1e-08,0,1e-08,1.0,1.0,1.0")
    good_csv.write_text("\n".join(lines) + "\n", encoding="utf-8")

    parsed = cert.parse_parity500_probe_output_csv(good_csv, expected_rows=5)
    _check(parsed["rows"] == 5, "Expected 5 parsed rows")
    _check(float(np.max(np.abs(parsed["onnx_proba"] - parsed["ref_proba"]))) <= 1e-7, "Unexpected CSV diff")

    bad_csv = tmp_path / "nan_probe.csv"
    bad_csv.write_text(
        "row_idx,ref_proba,onnx_proba,pure_mql5_proba,ref_size,onnx_size,pure_size\n0,0.5,nan,0.5,1,1,1\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="MT5_PARITY500_CSV_NON_FINITE"):
        cert.parse_parity500_probe_output_csv(bad_csv, expected_rows=1)

    probe_log = (
        "CS\t0\t02:43:25.314\tONNX\tapi version 1.25.1 initialized\n"
        "CS\t0\t02:43:25.314\tNaqex_ML_Parity500_Probe\tONNX: CPU selected\n"
        "CS\t0\t02:43:25.320\tNaqex_ML_Parity500_Probe\t[ML-PARITY500-INIT] init_ok=true onnx_ready=true backend=ONNX\n"
        "CS\t0\t02:43:25.331\tNaqex_ML_Parity500_Probe\tPARITY500_SUMMARY|rows=500|onnx_ready=true|onnx_ok=500|"
        "pure_ok=500|max_err_onnx_ref=7.27e-08|max_err_pure_ref=4.96e-13|max_err_onnx_pure=7.27e-08|"
        "onnx_size_match=500|pure_size_match=500|nan_blocked=true|inf_blocked=true|parity_pass=true\n"
    )
    plog = cert.parse_parity500_probe_log(probe_log)
    _check(plog["onnx_api_version"] == "1.25.1", f"Unexpected API version: {plog}")
    _check(plog["cpu_selected"] is True, "Expected CPU selected")
    _check(plog["nan_blocked"] is True and plog["inf_blocked"] is True, "Expected NaN/Inf blocked")
    _check(plog["error_lines_count"] == 0, "Expected 0 error lines")

    v104_log = (
        "CS\t0\t02:43:31.971\tONNX\tapi version 1.25.1 initialized\n"
        "CS\t0\t02:43:31.971\tNaqex_Master_Prop7E_v104_ML\tONNX: CPU selected\n"
        "CS\t0\t02:43:31.976\tNaqex_Master_Prop7E_v104_ML\t[MASTER-V104-ML-INIT] "
        "sku=FTMO_STD_10K_V104_ML_ONNX_FUNDED_1X ml_enabled=true ml_thr=0.457952 "
        "ml_onnx_ready=true ml_backend=ONNX tot_open_cap=2.00% dry_run=false\n"
    )
    vlog = cert.parse_v104_ml_tester_log(v104_log)
    _check(vlog["ml_enabled"] is True and vlog["ml_onnx_ready"] is True, f"Unexpected v104 log: {vlog}")
    _check(vlog["ml_backend"] == "ONNX" and vlog["error_lines_count"] == 0, f"Unexpected v104 log: {vlog}")

    err_log = v104_log + "CS\t0\t02:43:32.000\tONNX\tTensorRT initialization failed\n"
    elog = cert.parse_v104_ml_tester_log(err_log)
    _check(elog["error_lines_count"] == 1, f"Expected 1 error line caught, got {elog['error_lines_count']}")


# ---------------------------------------------------------------------------
# 5. Ablation Position Diff & Worst-Day Metrics
# ---------------------------------------------------------------------------


def test_ablation_comparison_and_worst_day_metrics() -> None:
    base_positions = [
        {
            "magic": 20261122,
            "engine_id": "E1_USDJPY_TOKYO",
            "day_utc": "2024-03-04",
            "side": "BUY",
            "entry_utc_ts": 1709550000,
            "exit_utc_ts": 1709560000,
            "net_pnl_usd": -120.0,
        },
        {
            "magic": 20261123,
            "engine_id": "E2_USDJPY_EXP80",
            "day_utc": "2024-03-04",
            "side": "SELL",
            "entry_utc_ts": 1709555000,
            "exit_utc_ts": 1709565000,
            "net_pnl_usd": -80.0,
        },
        {
            "magic": 20261124,
            "engine_id": "E4_US100_SESS40",
            "day_utc": "2024-03-05",
            "side": "BUY",
            "entry_utc_ts": 1709640000,
            "exit_utc_ts": 1709650000,
            "net_pnl_usd": 250.0,
        },
    ]
    # ML permanently filters E2 (-$80) and delays E1 entry by 600s
    delayed_e1 = dict(base_positions[0], entry_utc_ts=1709550600, net_pnl_usd=-120.0)
    cand_positions = [delayed_e1, base_positions[2]]

    diff = cert.compare_ablation_positions(
        baseline_positions=base_positions,
        candidate_positions=cand_positions,
        initial_balance_usd=10_000.0,
    )
    _check(diff["baseline_trades"] == 3 and diff["candidate_trades"] == 2, f"Unexpected counts: {diff}")
    _check(diff["kept_trades_count"] == 2, "Expected 2 kept trades")
    _check(diff["filtered_trades_count"] == 1, "Expected 1 filtered trade")
    _check(diff["permanently_filtered_engine_days_count"] == 1, "Expected 1 permanently filtered engine-day")
    _check(diff["delayed_same_side_reentries_count"] == 1, "Expected 1 delayed same-side re-entry")
    _check(diff["total_ml_affected_engine_days"] == 2, "Expected 2 ML-affected engine-days")
    _check(diff["newly_unblocked_trades_count"] == 0, "Expected 0 newly unblocked trades")
    _check(diff["filtered_trades_baseline_net_pnl_usd"] == -80.0, f"Unexpected filtered pnl: {diff}")
    _check(
        abs(diff["baseline_worst_day_pct"] - 2.0) < 1e-6,
        f"Expected 2.0% worst day, got {diff['baseline_worst_day_pct']}",
    )
    _check(
        abs(diff["candidate_worst_day_pct"] - 1.2) < 1e-6,
        f"Expected 1.2% worst day, got {diff['candidate_worst_day_pct']}",
    )


# ---------------------------------------------------------------------------
# 6. Immutables & Zero Stray `.ex5` Hygiene Guard
# ---------------------------------------------------------------------------


def test_immutables_and_zero_ex5_hygiene() -> None:
    audit = cert.verify_immutables_and_binary_hygiene()
    _check(audit["v103_mq5_untouched"] is True, "v103.mq5 modified")
    _check(audit["propguard_mqh_untouched"] is True, "Naqex_PropGuard.mqh modified")
    _check(audit["signals_7e_mqh_untouched"] is True, "Naqex_Signals_7E.mqh modified")
    _check(audit["agents_md_untouched"] is True, "AGENTS.md modified")
    _check(audit["quant_core_untouched"] is True and audit["quant_core_py_count"] == 41, "quant_core count drifted")
    _check(audit["exports_ex5_count"] == 0, "Stray .ex5 in exports/")
    _check(audit["private_vault_ex5_count"] == 0, "Stray .ex5 in private_vault/")


# ---------------------------------------------------------------------------
# 7. Local-Cache Certification Receipt Verification (`W4-G05`)
# ---------------------------------------------------------------------------


@pytest.mark.local_cache
def test_certified_w4_m1_mt5_onnx_receipt_and_dropbox_match() -> None:
    audit_path = cert.DEFAULT_AUDIT_RECEIPT
    dropbox_path = cert.DEFAULT_DROPBOX_RECEIPT
    for req in (audit_path, dropbox_path):
        _check(req.is_file(), f"Missing W4-G05 certification receipt: {req}")

    audit_raw = audit_path.read_bytes()
    dropbox_raw = dropbox_path.read_bytes()
    _check(not audit_raw.startswith(b"\xef\xbb\xbf"), "BOM detected in audit receipt")
    _check(b"\r\n" not in audit_raw, "CRLF detected in audit receipt")
    _check(audit_raw == dropbox_raw, "Audit receipt and swarm dropbox receipt must be byte-identical")

    receipt = json.loads(audit_raw.decode("utf-8"))
    _check(receipt["schema"] == cert.SCHEMA_RECEIPT, f"Unexpected schema: {receipt['schema']}")
    _check(receipt["gate"] == "W4-G05", f"Unexpected gate: {receipt['gate']}")
    _check(receipt["status"] == "PASS", f"Certification status not PASS: {receipt['status']}")
    _check(receipt["mt5_lock_status"] == "RELEASED", "MT5 lock not RELEASED")
    _check(receipt["mt5_procs_after"] == 0, f"MT5_PROCS non-zero: {receipt['mt5_procs_after']}")

    inv = receipt["hard_invariants"]
    _check(inv["order_send_capable"] is False and inv["order_send_count"] == 0, "OrderSend invariant breached")
    _check(inv["allow_live_trading"] == 0, "AllowLiveTrading != 0")
    _check(inv["spend_vnd"] == 0, "spend_vnd != 0")
    _check(inv["holdout_rows_analysed"] == 0, "holdout_rows_analysed != 0")
    _check(inv["max_to_date"] <= "2024.12.31", f"max_to_date breached Holdout: {inv['max_to_date']}")
    _check(inv["zipmap_node_count"] == 0, "ZipMap node count != 0")
    _check(inv["exports_ex5_count"] == 0 and inv["private_vault_ex5_count"] == 0, "Stray .ex5 binaries detected")
    _check(inv["mt5_procs_count"] == 0, "mt5_procs_count != 0")
    _check(inv["git_commits_made"] == 0, "git_commits_made != 0")

    p500 = receipt["independent_parity_500"]
    _check(p500["passed"] is True, "Independent 500-vector parity failed")
    _check(p500["onnx_model"]["zipmap_node_count"] == 0, "ZipMap count != 0")
    _check(p500["onnx_model"]["portable_sha256_match"] is True, "Portable ONNX SHA mismatch")
    _check(p500["mt5_probe_run"]["onnx_ready"] is True, "MT5 Probe onnx_ready != true")
    _check(p500["mt5_probe_run"]["rows"] == 500, "MT5 Probe rows != 500")
    _check(p500["mt5_probe_run"]["nan_blocked"] is True, "MT5 Probe did not block NaN")
    _check(p500["mt5_probe_run"]["inf_blocked"] is True, "MT5 Probe did not block Inf")
    _check(p500["mt5_probe_run"]["error_lines_count"] == 0, "MT5 Probe had error lines")
    fw = p500["four_way_parity_500"]
    _check(fw["passed"] is True, "4-way numerical parity failed")
    _check(fw["overall_max_abs_err"] <= 1e-5, f"4-way max abs err > 1e-5: {fw['overall_max_abs_err']}")
    _check(fw["all_decision_agreements_100pct"] is True, "Decision agreement < 100%")

    abl = receipt["full2024_mt5_ablation"]
    v104_onnx = abl["v104_ml_onnx"]
    _check(v104_onnx["rc"] == 0 and v104_onnx["timed_out"] is False, "v104_ML ONNX run failed")
    _check(v104_onnx["log_telemetry"]["error_lines_count"] == 0, "v104_ML ONNX had runtime errors")
    _check(v104_onnx["log_telemetry"]["ml_onnx_ready"] is True, "v104_ML ONNX ml_onnx_ready != true")
    _check(v104_onnx["log_telemetry"]["ml_backend"] == "ONNX", "v104_ML ONNX ml_backend != ONNX")
    _check(v104_onnx["metrics"]["swap_zero_ok"] is True, "v104_ML ONNX swap != $0.00")
    _check(v104_onnx["metrics"]["max_deal_date"] < "2025-01-01", "v104_ML ONNX breached Holdout")

    v104_dis = abl["v104_ml_disabled"]
    _check(v104_dis["rc"] == 0 and v104_dis["log_telemetry"]["error_lines_count"] == 0, "v104_ML disabled run failed")
    _check(v104_dis["metrics"]["swap_zero_ok"] is True, "v104_ML disabled swap != $0.00")
    _check(
        abl["comparisons"]["v104_ml_disabled_vs_v103_baseline"]["exact_reproduction"] is True,
        "v104_ML with ML disabled did not reproduce v103 baseline cleanly",
    )

    v104_pure = abl["v104_ml_pure_mql5"]
    _check(v104_pure["rc"] == 0 and v104_pure["log_telemetry"]["error_lines_count"] == 0, "v104_ML pure MQL5 failed")
    _check(v104_pure["log_telemetry"]["ml_backend"] == "PURE_MQL5", "Pure MQL5 mode backend mismatch")
    _check(v104_pure["metrics"]["swap_zero_ok"] is True, "v104_ML pure MQL5 swap != $0.00")

    for gate_name, gate_ok in receipt["gates"].items():
        _check(gate_ok is True, f"W4-G05 gate failed: {gate_name}")

    findings = abl.get("semantic_findings") or []
    _check(len(findings) >= 1 and findings[0]["id"] == "W4G05-F01", "Missing W4G05-F01 semantic finding")
    _check(findings[0].get("status") == "CLOSED_VERIFIED", f"W4G05-F01 not closed: {findings[0]}")
    cmp_onnx = abl["comparisons"]["v104_ml_onnx_vs_v103_baseline"]
    _check(cmp_onnx["total_ml_affected_engine_days"] > 0, "Expected non-zero ML-affected engine days")
    _check(cmp_onnx["delayed_same_side_reentries_count"] == 0, "Delayed same-side re-entries must be 0 post-fix")
    _check(cmp_onnx["flipped_side_reentries_count"] == 0, "Flipped-side re-entries must be 0 post-fix")
    _check(cmp_onnx["permanently_filtered_engine_days_count"] > 0, "Expected permanently filtered engine days")

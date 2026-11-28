"""Offline CI-safe + local_cache certification tests for Wave 5 Modular v1.05 & MT5 (W5-G10/G12/G15).

All checks use `_check(...)` (ZERO bare `assert` statements) so 100% of assertions remain active
under `python -O -m pytest` (`[ARCH-02]`). All tracked text file hashes normalize CRLF -> LF for
Windows + Linux CI portability.

Offline CI tests (`-m "not local_cache"`):
  1. Static safety: LF-only, 0 BOM, 0 bare `assert`s, lazy ML/ONNX/pandas imports only,
     0 `MetaTrader5` imports, 0 `order_send` refs, `creationflags` on every `subprocess.run`,
     0 hardcoded user paths or LAN IPs.
  2. MQL5 deliverables static contract: `Naqex_EngineSlotRegistry.mqh` (16 slots, EUR/GBP/AUD,
     Shield A <= 3.00%, 0 trade execution APIs), `Naqex_Master_Modular_v105.mq5` (fail-closed
     defaults, MarkEngineTraded on !mlAllowed, MQL_TESTER CSV dump guard, Bellman DP 6-tier),
     `Naqex_ML_Parity500_Probe_v105.mq5` (0 trade execution APIs).
  3. Holdout `< 2025-01-01` date seal + safe Tester `.ini` / `.set` rendering under `python -O`.
  4. 4-way 500-vector parity math + real `Naqex_ML_Filter_v105.mqh` Python mirror + NaN/Inf fail-closed.
  5. Live feature reconciler (`<= 1e-4`), Bellman DP 6-tier reference monotonicity, and log parsers.
  6. LF-normalized `11/11` immutables untouched + `quant_core/*.py == 41` + `0` stray `.ex5`.

Local-cache tests (`@pytest.mark.local_cache`):
  7. Verifies built-in Bellman DP 6-tier schedule matches `.runtime/offensive5/pareto/bellman_dp_schedule.json`.
  8. Verifies byte-identical receipts `.runtime/offensive5/audits/w5_modular_mt5_receipt.json` &
     `.tmp/swarm_dropbox/w5-modular-mt5.json` certify ALL gates (`W5-G10`, `W5-G12`, `W5-G15`).
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

AI_ENGINES_DIR = Path(__file__).resolve().parents[2]
if str(AI_ENGINES_DIR) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES_DIR))

from quant_factory.wave5 import verify_modular_v105_mt5 as cert  # noqa: E402

ROOT = Path(__file__).resolve().parents[4]
_OPSEC_FORBIDDEN_RE = re.compile(
    r"(?:C:\\Users\\|/Users/|/home/|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(?:1[6-9]|2\d|3[01])\.\d+\.\d+)",
    re.IGNORECASE,
)


def _check(condition: bool, message: str) -> None:
    """Assertion helper immune to `python -O` bytecode stripping."""
    if not condition:
        raise AssertionError(message)


# ---------------------------------------------------------------------------
# 1. Static Safety, Lazy Imports, Zero Bare Asserts, OPSEC & creationflags
# ---------------------------------------------------------------------------


def test_static_safety_lf_no_bom_zero_bare_asserts_lazy_imports_and_creationflags() -> None:
    src_path = Path(cert.__file__).resolve()
    raw_bytes = src_path.read_bytes()
    _check(not raw_bytes.startswith(b"\xef\xbb\xbf"), "BOM detected in verify_modular_v105_mt5.py")
    _check(b"\r\n" not in raw_bytes, "CRLF detected in verify_modular_v105_mt5.py")
    src_text = raw_bytes.decode("utf-8")
    _check(_OPSEC_FORBIDDEN_RE.search(src_text) is None, "OPSEC path/IP pattern detected in verifier")

    tree = ast.parse(src_text, filename=str(src_path))
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
    _check(subprocess_run_calls >= 3, f"Expected >= 3 subprocess.run calls checked, saw {subprocess_run_calls}")

    # Clean python -O import MUST NOT eagerly load ML / ONNX / pandas / duckdb / quant_trading / MT5
    code = "\n".join(
        [
            "import sys",
            "from quant_factory.wave5 import verify_modular_v105_mt5 as c",
            "forbidden = ['onnx', 'onnxmltools', 'skl2onnx', 'onnxruntime', 'lightgbm',",
            "             'sklearn', 'catboost', 'duckdb', 'pandas', 'MetaTrader5', 'quant_trading']",
            "loaded = [m for m in forbidden if m in sys.modules]",
            "if loaded:",
            "    raise SystemExit(f'Eagerly imported: {loaded}')",
            "if c.ORDER_SEND_CAPABLE is not False or c.ORDER_SEND_COUNT != 0 or c.SPEND_VND != 0:",
            "    raise SystemExit('Safety constants invalid')",
            "print('CLEAN_W5_MODULAR_MT5_IMPORT_OK')",
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
    _check("CLEAN_W5_MODULAR_MT5_IMPORT_OK" in proc.stdout, f"unexpected stdout={proc.stdout!r}")


# ---------------------------------------------------------------------------
# 2. MQL5 Deliverables Static Contract & Pure Signal/Registry Hygiene
# ---------------------------------------------------------------------------


def test_mql5_deliverables_static_contract_and_pure_registry_hygiene() -> None:
    reg_path = cert.INCLUDE_DIR / cert.REGISTRY_MQH_NAME
    ea_path = cert.EXPORTS_DIR / f"{cert.MODULAR_EA_STEM}.mq5"
    probe_path = cert.EXPORTS_DIR / f"{cert.PROBE_EA_STEM}.mq5"

    for p in (reg_path, ea_path, probe_path):
        _check(p.is_file(), f"Missing Wave 5 MQL5 deliverable: {p}")
        raw = p.read_bytes()
        _check(not raw.startswith(b"\xef\xbb\xbf"), f"BOM detected in {p.name}")
        _check(b"\r\n" not in raw, f"CRLF detected in {p.name}")
        txt = raw.decode("utf-8")
        _check(_OPSEC_FORBIDDEN_RE.search(txt) is None, f"OPSEC leak pattern in {p.name}")

    reg_txt = reg_path.read_text(encoding="utf-8")
    for forbidden in ("OrderSend", "CTrade", "PositionClose", "OrderDelete"):
        _check(forbidden not in reg_txt, f"Forbidden execution API {forbidden!r} in pure {reg_path.name}")
    for req_tok in (
        "#define NAQEX_SLOT_COUNT                16",
        "#define NAQEX_SHIELD_A_HARD_CEILING_PCT 3.00",
        "slot_id",
        "engine_id",
        "magic",
        "symbol",
        "enabled",
        "weight_mult",
        "status",
        "mt5_hcc_ready",
        "red_news_6ccy_warning",
        "NAQEX_SLOT_ACTIVE",
        "NAQEX_SLOT_SHADOW",
        "NAQEX_SLOT_HALVED",
        "NAQEX_SLOT_RETIRED",
        "AccumulateExtendedDirectionalFactor",
        "ComputeExtendedClusterHeadroomPct",
        "EnforceShieldACapPct",
    ):
        _check(req_tok in reg_txt, f"Missing required registry token {req_tok!r} in {reg_path.name}")

    ea_txt = ea_path.read_text(encoding="utf-8")
    for req_ea in (
        '#include "Include/Naqex_PropGuard.mqh"',
        '#include "Include/Naqex_Signals_7E.mqh"',
        '#include "Include/Naqex_EngineSlotRegistry.mqh"',
        '#include "Include/Naqex_ML_Filter_v105.mqh"',
        "input bool   InpGuardDryRunLogOnly          = true;",
        "input bool   InpDryRunLogOnly               = true;",
        "input bool   InpShadowCompareMode           = true;",
        "input bool   InpUseV105ML                   = false;",
        "input bool   InpMLUseOnnx                   = true;",
        "input bool   InpDumpMLFeaturesCsv           = false;",
        "input bool   InpUseBellmanDP                = false;",
        "BuildAlignedFeaturesV105(",
        "g_signals.MarkEngineTraded(it.magic, it.session_day_key);",
        "InpDumpMLFeaturesCsv && MQLInfoInteger(MQL_TESTER)",
        "EvaluateBellmanDPRiskMultV105(",
    ):
        _check(req_ea in ea_txt, f"Missing required Modular v105 EA contract token: {req_ea!r}")

    probe_txt = probe_path.read_text(encoding="utf-8")
    for forbidden in ("OrderSend", "CTrade", "PositionClose", "OrderDelete"):
        _check(forbidden not in probe_txt, f"Forbidden execution API {forbidden!r} in {probe_path.name}")
    _check('#include "Include/Naqex_ML_Filter_v105.mqh"' in probe_txt, "Probe must include Naqex_ML_Filter_v105.mqh")
    _check("PARITY500_V105_SUMMARY|" in probe_txt, "Probe must emit PARITY500_V105_SUMMARY|")


# ---------------------------------------------------------------------------
# 3. Holdout Date Seal & Safe Tester INI / `.set` Rendering Under `python -O`
# ---------------------------------------------------------------------------


def test_holdout_date_seal_and_safe_tester_ini_and_set_rendering(tmp_path: Path) -> None:
    with pytest.raises(cert.HoldoutViolationError):
        cert.render_safe_tester_ini(
            expert_rel_path=f"Naqex\\{cert.MODULAR_EA_STEM}.ex5",
            from_date="2024.01.02",
            to_date="2025.01.01",
            report_stem="must_fail",
        )

    ini_text = cert.render_safe_tester_ini(
        expert_rel_path=f"Naqex\\{cert.MODULAR_EA_STEM}.ex5",
        set_filename="test_v105.set",
        from_date="2024.01.02",
        to_date="2024.12.31",
        report_stem="w5_test",
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
        "; sample\nInpDryRunLogOnly=true\nInpInitialBalanceUSD=10000.00\nInpBasePhaseMult=1.00\n",
        encoding="utf-8",
    )
    src_before = src_set.read_bytes()
    out_set = tmp_path / "transient.set"
    cert.render_modular_v105_tester_set(
        src_set,
        initial_balance_usd=10_000.0,
        use_v105_ml=True,
        ml_use_onnx=False,
        dump_ml_features_csv=True,
        use_bellman_dp=True,
        bellman_dp_phase=1,
        out_path=out_set,
    )
    _check(src_set.read_bytes() == src_before, "Source preset must never be mutated")
    out_txt = out_set.read_text(encoding="utf-8")
    for req_kv in (
        "InpUseV105ML=true",
        "InpMLUseOnnx=false",
        "InpDumpMLFeaturesCsv=true",
        "InpUseBellmanDP=true",
        "InpBellmanDPPhase=1",
        "InpSlot0Weight=1.00",
        "InpMaxEurClusterPct=2.00",
    ):
        _check(req_kv in out_txt, f"Missing rendered .set key: {req_kv}")

    with pytest.raises(ValueError, match="INVALID_ML_THRESHOLD"):
        cert.render_modular_v105_tester_set(
            src_set, initial_balance_usd=10_000.0, use_v105_ml=True, ml_threshold=1.5, out_path=out_set
        )
    with pytest.raises(ValueError, match="INVALID_BELLMAN_DP_PHASE"):
        cert.render_modular_v105_tester_set(
            src_set, initial_balance_usd=10_000.0, use_v105_ml=False, bellman_dp_phase=9, out_path=out_set
        )


# ---------------------------------------------------------------------------
# 4. 4-Way Parity Math, Actual v105 MQH Mirror & Fail-Closed NaN/Inf Rejection
# ---------------------------------------------------------------------------


def test_four_way_parity_and_mqh_v105_mirror_and_poisoned_rejection() -> None:
    rng = np.random.default_rng(2026)
    py_p = rng.uniform(0.35, 0.65, size=500)
    thr = cert.DEFAULT_V105_ML_THRESHOLD
    py_p = np.where(np.abs(py_p - thr) < 1e-4, py_p + 5e-3, py_p)
    sizes = np.where(py_p >= thr, 1.0, 0.0)

    ort_b = py_p + rng.uniform(-5e-8, 5e-8, size=500)
    ort_s = py_p + rng.uniform(-7e-8, 7e-8, size=500)
    mt5_onnx = ort_s + rng.uniform(-2e-9, 2e-9, size=500)
    mt5_pure = py_p + rng.uniform(-5e-13, 5e-13, size=500)
    py_mqh = py_p.copy()

    res = cert.compute_four_way_parity_metrics_v105(
        py_lgbm_proba=py_p,
        ort_batch_proba=ort_b,
        ort_single_proba=ort_s,
        mt5_onnx_proba=mt5_onnx,
        mt5_pure_proba=mt5_pure,
        py_mqh_mirror_proba=py_mqh,
        ref_sizes=sizes,
        threshold=thr,
        tol=1e-5,
    )
    _check(res["passed"] is True, f"Expected 4-way parity PASS, got {res}")
    _check(res["overall_max_abs_err"] <= 1e-5, f"Unexpected err: {res['overall_max_abs_err']}")

    bad_onnx = mt5_onnx.copy()
    bad_onnx[5] += 5e-5
    res_fail = cert.compute_four_way_parity_metrics_v105(
        py_lgbm_proba=py_p,
        ort_batch_proba=ort_b,
        ort_single_proba=ort_s,
        mt5_onnx_proba=bad_onnx,
        mt5_pure_proba=mt5_pure,
        py_mqh_mirror_proba=py_mqh,
        ref_sizes=sizes,
        threshold=thr,
        tol=1e-5,
    )
    _check(res_fail["passed"] is False, "Expected parity FAIL when error > 1e-5")

    for bad_val in (np.nan, np.inf, -np.inf):
        poisoned = mt5_onnx.copy()
        poisoned[0] = bad_val
        with pytest.raises(ValueError, match="NON_FINITE_PROB_VECTOR"):
            cert.compute_four_way_parity_metrics_v105(
                py_lgbm_proba=py_p,
                ort_batch_proba=ort_b,
                ort_single_proba=ort_s,
                mt5_onnx_proba=poisoned,
                mt5_pure_proba=mt5_pure,
                py_mqh_mirror_proba=py_mqh,
                ref_sizes=sizes,
            )

    # Evaluate ACTUAL tracked Naqex_ML_Filter_v105.mqh in pure NumPy (zero ML deps!)
    mqh_text = (cert.INCLUDE_DIR / cert.ML_FILTER_MQH_NAME).read_text(encoding="utf-8")
    tables = cert.parse_mqh_v105_tree_tables(mqh_text)
    _check(
        tables["n_features"] == 8 and tables["n_trees"] == 80 and tables["n_nodes"] == 560,
        f"Bad MQH dims: {tables}",
    )
    synth_x = rng.uniform(0.0, 1.0, size=(10, 8)).astype(np.float32)
    probs = cert.evaluate_mqh_v105_python_mirror(mqh_text, synth_x)
    _check(probs.shape == (10,) and bool(np.all(np.isfinite(probs))), "Mirror probs non-finite")
    _check(float(np.min(probs)) > 0.0 and float(np.max(probs)) < 1.0, "Mirror probs out of (0,1)")

    synth_nan = synth_x.copy()
    synth_nan[0, 0] = np.nan
    with pytest.raises(ValueError, match="NON_FINITE_FEATURE_MATRIX"):
        cert.evaluate_mqh_v105_python_mirror(mqh_text, synth_nan)


# ---------------------------------------------------------------------------
# 5. Live Feature Reconciler, Bellman DP Reference & Log/Diff Parsers
# ---------------------------------------------------------------------------


def test_live_feature_reconciler_and_bellman_dp_6tier_and_log_parsers(tmp_path: Path) -> None:
    ref_csv = tmp_path / "ref.csv"
    ea_csv = tmp_path / "ea.csv"
    ref_csv.write_text(
        "signal_seq,entry_utc_ts,entry_server_time,engine_id,magic,symbol,side,"
        "f0,f1,f2,f3,f4,f5,f6,f7,ref_p_win,ref_ml_allowed,ref_size_mult,"
        "shadow_eq_1x,shadow_peak_1x,shadow_dd_pct_1x,same_dir_concurrent\n"
        "0,1704166120,2024.01.02 05:28:40,E1_USDJPY_TOKYO,20261122,USDJPY,BUY,"
        "0.75,0.0057,1.0,0.789798,0.613367,1.0,0.0,0.0,0.432606,0,0.0,1.0,1.0,0.0,0\n",
        encoding="utf-8",
    )
    ea_csv.write_text(
        "signal_seq,entry_utc_ts,entry_server_time,engine_id,magic,symbol,side,"
        "f0,f1,f2,f3,f4,f5,f6,f7,ea_p_win,ea_ml_allowed,ea_backend,"
        "shadow_eq_1x,shadow_peak_1x,shadow_dd_pct_1x,same_dir_concurrent\n"
        "0,1704166120,2024.01.02 05:28:40,E1_USDJPY_TOKYO,20261122,USDJPY,BUY,"
        "0.75001,0.0057,1.0,0.789798,0.613367,1.0,0.0,0.0,0.432606,0,ONNX,1.0,1.0,0.0,0\n",
        encoding="utf-8",
    )
    rec_ok = cert.reconcile_live_ea_features_vs_python_ref(ea_csv_path=ea_csv, ref_csv_path=ref_csv, feature_tol=1e-4)
    _check(rec_ok["passed"] is True, f"Expected live feature reconcile PASS: {rec_ok}")
    _check(rec_ok["overall_max_abs_feature_err"] <= 1e-4, "Unexpected feature err")

    # Drift > 1e-4 must fail transparently
    ea_bad = tmp_path / "ea_bad.csv"
    ea_bad.write_text(ea_csv.read_text(encoding="utf-8").replace("0.75001", "0.75500"), encoding="utf-8")
    rec_fail = cert.reconcile_live_ea_features_vs_python_ref(ea_csv_path=ea_bad, ref_csv_path=ref_csv, feature_tol=1e-4)
    _check(rec_fail["passed"] is False, "Expected live feature reconcile FAIL on 5e-3 drift")

    # Holdout timestamp >= 2025-01-01 must raise HoldoutViolationError
    ea_holdout = tmp_path / "ea_holdout.csv"
    ea_holdout.write_text(ea_csv.read_text(encoding="utf-8").replace("1704166120", "1735700000"), encoding="utf-8")
    with pytest.raises(cert.HoldoutViolationError):
        cert.reconcile_live_ea_features_vs_python_ref(ea_csv_path=ea_holdout, ref_csv_path=ref_csv)

    # Bellman DP 6-tier anti-martingale loss monotonicity check (P1 & P2)
    for phase in (1, 2):
        prev_m = 99.0
        for eq_loss in (0.0, -2.0, -5.0, -7.0):
            m, _tid = cert.evaluate_bellman_dp_6tier_reference(phase=phase, signed_eq_pct=eq_loss, dd_from_peak_pct=0.0)
            _check(m <= prev_m + 1e-12, f"Anti-martingale violated at phase={phase} eq={eq_loss}: {m} > {prev_m}")
            prev_m = m
    m_p1_house, tid_house = cert.evaluate_bellman_dp_6tier_reference(phase=1, signed_eq_pct=5.0)
    m_p1_fin, tid_fin = cert.evaluate_bellman_dp_6tier_reference(phase=1, signed_eq_pct=8.5)
    _check(
        m_p1_house == 3.0 and tid_house == "P1_T1_HOUSE_MONEY_CRUISE",
        f"Unexpected P1 house tier: {m_p1_house}/{tid_house}",
    )
    _check(
        m_p1_fin == 2.0 and tid_fin == "P1_T2_FINISH_LINE_TAPER",
        f"Unexpected P1 finish tier: {m_p1_fin}/{tid_fin}",
    )

    # MetaEditor & Modular v105 log parsers
    comp_ok = cert.parse_metaeditor_compile_log("Result: 0 errors, 0 warnings, 1234 ms elapsed")
    _check(
        comp_ok["clean_zero"] is True and comp_ok["errors"] == 0 and comp_ok["warnings"] == 0,
        f"Bad compile parse: {comp_ok}",
    )
    comp_warn = cert.parse_metaeditor_compile_log("Result: 0 errors, 1 warnings, 1234 ms elapsed")
    _check(comp_warn["clean_zero"] is False, "1 warning must fail clean_zero")

    v105_log = (
        "CS\t0\t15:12:00.000\tONNX\tapi version 1.25.1 initialized\n"
        "CS\t0\t15:12:00.001\tNaqex_Master_Modular_v105\tONNX: CPU selected\n"
        "CS\t0\t15:12:00.010\tNaqex_Master_Modular_v105\t[MASTER-V105-INIT] sku=FTMO_STD_10K_V105_ML_ONNX "
        "ml_enabled=true ml_use_onnx=true ml_thr=0.448872 ml_onnx_ready=true ml_backend=ONNX "
        "bellman_dp=false dp_phase=1 dp_tiers=0 slots_enabled=7 dump_csv=true dry_run=false\n"
        "CS\t0\t15:12:30.000\tNaqex_Master_Modular_v105\t[MASTER-V105-DEINIT] ml_passed=650 ml_blocked=127 "
        "ml_onnx_calls=777 ml_pure_calls=0 ml_fallback_calls=0 shadow_closed=343 shadow_dd_1x=1.234567 dump_rows=777\n"
    )
    plog = cert.parse_modular_v105_tester_log(v105_log)
    _check(
        plog["ml_onnx_ready"] is True and plog["ml_backend"] == "ONNX" and plog["dump_rows"] == 777,
        f"Bad log parse: {plog}",
    )
    _check(plog["error_lines_count"] == 0, f"Unexpected errors: {plog}")


# ---------------------------------------------------------------------------
# 6. LF-Normalized 11/11 Immutables & Zero Stray `.ex5` Hygiene Guard
# ---------------------------------------------------------------------------


def test_immutables_11_of_11_lf_normalized_and_zero_ex5_hygiene() -> None:
    audit = cert.verify_immutables_11_and_hygiene()
    _check(audit["immutables_11_of_11_untouched"] is True, "11/11 immutables check failed")
    _check(audit["immutables_checked"] == 11, f"Expected 11 immutables, saw {audit['immutables_checked']}")
    _check(audit["quant_core_untouched"] is True and audit["quant_core_py_count"] == 41, "quant_core count drifted")
    _check(audit["exports_ex5_count"] == 0, "Stray .ex5 in exports/")
    _check(audit["private_vault_ex5_count"] == 0, "Stray .ex5 in private_vault/")


# ---------------------------------------------------------------------------
# 7. Local-Cache Bellman DP JSON Parity & Certified Receipt Verification
# ---------------------------------------------------------------------------


@pytest.mark.local_cache
def test_bellman_dp_mql5_schedule_matches_runtime_json() -> None:
    sched_path = cert.DEFAULT_BELLMAN_SCHEDULE_JSON
    _check(sched_path.is_file(), f"Missing bellman_dp_schedule.json: {sched_path}")
    data = json.loads(sched_path.read_text(encoding="utf-8"))
    mql_sched = data["mql5_loadable_schedule"]
    for phase_num, phase_key in ((1, "P1"), (2, "P2")):
        tiers = mql_sched[phase_key]["tiers"]
        _check(len(tiers) == 6, f"Expected 6 tiers for {phase_key}")
        for t in tiers:
            mid_eq = 0.5 * (float(t["eq_min_pct"]) + float(t["eq_max_pct"]))
            m_ref, tid_ref = cert.evaluate_bellman_dp_6tier_reference(
                phase=phase_num, signed_eq_pct=mid_eq, dd_from_peak_pct=0.0
            )
            _check(
                abs(m_ref - float(t["risk_mult"])) <= 1e-9 and tid_ref == str(t["tier_id"]),
                f"Bellman DP mismatch at {phase_key} eq={mid_eq}: "
                f"ref=({m_ref},{tid_ref}) vs json=({t['risk_mult']},{t['tier_id']})",
            )


@pytest.mark.local_cache
def test_certified_w5_modular_mt5_receipt_and_dropbox_match() -> None:
    audit_path = cert.DEFAULT_AUDIT_RECEIPT
    dropbox_path = cert.DEFAULT_DROPBOX_RECEIPT
    for req in (audit_path, dropbox_path):
        _check(req.is_file(), f"Missing Wave 5 Modular MT5 receipt: {req}")

    audit_raw = audit_path.read_bytes()
    dropbox_raw = dropbox_path.read_bytes()
    _check(not audit_raw.startswith(b"\xef\xbb\xbf"), "BOM detected in audit receipt")
    _check(b"\r\n" not in audit_raw, "CRLF detected in audit receipt")
    _check(audit_raw == dropbox_raw, "Audit receipt and swarm dropbox receipt must be byte-identical")

    receipt = json.loads(audit_raw.decode("utf-8"))
    _check(receipt["schema"] == cert.SCHEMA_RECEIPT, f"Unexpected schema: {receipt['schema']}")
    _check(receipt["status"] == "PASS", f"Certification status != PASS: {receipt['status']}")
    _check(receipt["holdout_rows_analysed"] == 0, "holdout_rows_analysed != 0")
    _check(receipt["order_send_count"] == 0, "order_send_count != 0")
    _check(receipt["spend_vnd"] == 0, "spend_vnd != 0")
    _check(receipt["mt5_procs_after"] == 0, "mt5_procs_after != 0")

    for gate_name, gate_ok in receipt["gates"].items():
        _check(gate_ok is True, f"Wave 5 Modular MT5 gate failed: {gate_name}")

    # Verify W5-G12 4-way 500-vector parity <= 1e-5
    fw = receipt["w5_g12_parity500"]["four_way_parity_500"]
    _check(fw["passed"] is True and fw["overall_max_abs_err"] <= 1e-5, f"W5-G12 parity failed: {fw}")
    _check(fw["all_decision_agreements_100pct"] is True, "W5-G12 agreement < 100%")

    # Verify W5-G15 7E-Compat exact cent & trade count match
    g15 = receipt["w5_g15_7e_compat"]
    _check(
        g15["comparison_vs_v103"]["exact_cent_and_trade_match"] is True,
        f"W5-G15 mismatch: {g15['comparison_vs_v103']}",
    )
    _check(g15["modular_v105_7e_compat"]["metrics"]["trades"] == 469, "W5-G15 trade count != 469")
    _check(g15["comparison_vs_v103"]["delta_net_pnl_usd"] == 0.0, "W5-G15 delta PnL != 0.00")

    # Verify W5-G10 live 2024 feature parity (f0..f6 & unit-normalized f7/shadow_eq <= 1e-4, p_win <= 1e-5)
    g10 = receipt["w5_g10_live_feature_parity"]
    for label in ("reconcile_onnx_vs_python_ref", "reconcile_pure_vs_python_ref"):
        rec_f = g10[label]
        _check(rec_f["passed"] is True, f"W5-G10 {label} failed: {rec_f}")
        _check(
            rec_f["market_and_structural_f0_f6_max_abs_err"] <= 1e-4,
            f"W5-G10 {label} f0..f6 err > 1e-4: {rec_f['market_and_structural_f0_f6_max_abs_err']}",
        )
        _check(
            rec_f["overall_unit_normalized_feature_max_abs_err"] <= 1e-4,
            f"W5-G10 {label} unit-norm err > 1e-4: {rec_f['overall_unit_normalized_feature_max_abs_err']}",
        )
        _check(
            rec_f["shadow_eq_1x_max_abs_err"] <= 1e-4,
            f"W5-G10 {label} shadow_eq_1x err > 1e-4: {rec_f['shadow_eq_1x_max_abs_err']}",
        )
        _check(
            rec_f["f7_formula_self_consistency_err"] <= 1e-6,
            f"W5-G10 {label} f7 self-consistency err > 1e-6: {rec_f['f7_formula_self_consistency_err']}",
        )
        _check(
            rec_f["max_abs_p_win_err"] <= 1e-5,
            f"W5-G10 {label} live p_win err > 1e-5: {rec_f['max_abs_p_win_err']}",
        )
        _check(
            rec_f["decision_matches"] == rec_f["matched_signals_total"] == rec_f["ref_signals_total"],
            f"W5-G10 {label} decision/signal count mismatch: {rec_f}",
        )
        _check(
            rec_f["unmatched_ea_signals"] == 0 and rec_f["unmatched_ref_signals"] == 0,
            f"W5-G10 unmatched signals: {rec_f}",
        )
    _check(g10["comparison_pure_vs_onnx"]["exact_cent_and_trade_match"] is True, "ONNX vs Pure-MQL5 PnL mismatch")
    _check(
        g10["comparison_onnx_vs_v103"]["delayed_same_side_reentries_count"] == 0,
        "Delayed same-side re-entries != 0",
    )
    _check(g10["comparison_onnx_vs_v103"]["flipped_side_reentries_count"] == 0, "Flipped-side re-entries != 0")

    # Verify post-final deliverable SHAs match live files on disk
    for rel_p, info in receipt["deliverable_sha256s"].items():
        fp = ROOT / rel_p
        _check(fp.is_file(), f"Receipt deliverable missing on disk: {rel_p}")
        _check(cert.sha256_file(fp) == info["sha256"], f"Post-final SHA drift on {rel_p}")

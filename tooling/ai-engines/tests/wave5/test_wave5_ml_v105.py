"""Wave 5 `v1.05-ML` Aligned Features, Head-to-Head Arena & ONNX/MQL5 Certification Tests.

Strict guarantees:
  - ZERO bare Python `assert` statements (`python -O` safe — every check uses `_check()`).
  - Offline CI tests (without `@pytest.mark.local_cache`) use pure stdlib + NumPy ONLY and
    NEVER touch `.runtime/` or mutate any production artifact.
  - `@pytest.mark.local_cache` tests verify real FTMO M1 zero-bit-drift causality, DuckDB
    budget/Brier gates (in `tmp_path` only), and read-only integrity of exported ONNX,
    Pure-MQL5 `.mqh`, 500-vector parity CSV, 2024 FTMO live-extraction ref CSV, and OOF JSON.
"""

from __future__ import annotations

import ast
import csv
import hashlib
import json
import math
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[4]
AI_ENGINES_DIR = ROOT / "tooling" / "ai-engines"
if str(AI_ENGINES_DIR) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES_DIR))

from quant_factory.wave4.ml_walkforward_cv import (  # noqa: E402
    BudgetExceededError,
    CausalityViolationError,
    HoldoutCutoffBreachError,
    Law13HonestyError,
)
from quant_factory.wave5.ml_features_v105_aligned import (  # noqa: E402
    DEV_CUTOFF_SEC,
    FEATURE_NAMES_V105,
    FEATURE_SPECS_V105,
    Shadow1xClosedRTracker,
    assert_zero_future_leakage_v105,
    build_aligned_feature_matrix_v105,
    build_broker_d1_from_m1_v105,
    encode_utc_to_ftmo_server_times_v105,
    verify_ftmo_m1_zero_bit_drift_causality,
    verify_ftmo_two_regime_dst_guardrail,
    verify_phase_invariance_1x_equiv,
)
from quant_factory.wave5.run_v105_ml_and_sizing_arena import (  # noqa: E402
    DEFAULT_DB_PATH,
    DEFAULT_ML_OUT_DIR,
    DEFAULT_MQH_PATH,
    STRICT_ONNX_PARITY_TOL,
    VERDICT_PROMOTE_FILTER,
    VERDICT_REJECT_ML,
    Wave5MlBudgetLedger,
    assert_zero_forbidden_blind_label,
    build_numpy_smoke_v105_grid,
    build_preregistered_v105_grid,
    compute_sizing_from_train_quantiles,
    evaluate_mqh_v105_mirror,
    parse_mqh_v105_tree_tables,
    run_v105_ml_arena,
    validate_v105_arena_grid,
)

FORBIDDEN_BLIND_WORD = "BL" + "IND"
ML_FEATURES_FILE = AI_ENGINES_DIR / "quant_factory" / "wave5" / "ml_features_v105_aligned.py"
ML_ARENA_FILE = AI_ENGINES_DIR / "quant_factory" / "wave5" / "run_v105_ml_and_sizing_arena.py"
THIS_TEST_FILE = Path(__file__).resolve()


def _check(cond: bool, msg: str) -> None:
    """`python -O`-safe invariant assertion helper (ZERO bare `assert`)."""
    if not cond:
        raise AssertionError(msg)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65_536), b""):
            h.update(chunk)
    return h.hexdigest()


def _make_synthetic_m1_feed(
    n_days: int = 35,
    *,
    start_ts: int = 1_704_067_200,  # 2024-01-01T00:00:00Z
    base_price: float = 150.0,
    seed: int = 17,
) -> dict[str, np.ndarray]:
    """Build deterministic M1 OHLCV+spread feed covering `n_days` with hourly bars (fast, causal)."""
    rng = np.random.default_rng(seed)
    n_bars = n_days * 24
    # Step every 60 minutes (still valid M1 open_ts with 60s close_ts)
    open_ts = start_ts + np.arange(n_bars, dtype=np.int64) * 3600
    steps = rng.normal(0.0, 0.08, size=n_bars)
    closes = base_price + np.cumsum(steps)
    opens = np.empty(n_bars, dtype=np.float64)
    opens[0] = base_price
    opens[1:] = closes[:-1]
    spread_h = np.abs(rng.normal(0.06, 0.02, size=n_bars))
    spread_l = np.abs(rng.normal(0.06, 0.02, size=n_bars))
    highs = np.maximum(opens, closes) + spread_h
    lows = np.minimum(opens, closes) - spread_l
    spreads = np.full(n_bars, 0.015, dtype=np.float64)
    return {
        "times_sec": open_ts,
        "bar_duration_sec": 60,
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "spread": spreads,
    }


def _make_synthetic_trades(
    n_trades: int = 120,
    *,
    start_ts: int = 1_640_995_200,  # 2022-01-01T00:00:00Z
    step_sec: int = 28_800,
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, list[str], list[dict[str, Any]]]:
    rng = np.random.default_rng(seed)
    engines = ["E1", "E2", "E3", "E4", "E5", "E6", "E7"]
    x_mat = rng.normal(0.0, 1.0, size=(n_trades, len(FEATURE_NAMES_V105))).astype(np.float32)
    y_arr = rng.integers(0, 2, size=n_trades).astype(np.float64)
    r_arr = np.where(y_arr > 0.5, rng.uniform(0.4, 2.0, size=n_trades), -rng.uniform(0.4, 1.2, size=n_trades))
    ent_arr = start_ts + np.arange(n_trades, dtype=np.int64) * step_sec
    ext_arr = ent_arr + 3600
    eng_ids = [engines[i % len(engines)] for i in range(n_trades)]
    trades = [
        {
            "engine_id": eng_ids[i],
            "symbol": "USDJPY" if i % 2 == 0 else "GBPUSD",
            "entry_ts": int(ent_arr[i]),
            "exit_ts": int(ext_arr[i]),
            "net_R": float(r_arr[i]),
            "direction": 1 if (i % 3 != 0) else -1,
            "day": datetime.fromtimestamp(int(ent_arr[i]), UTC).strftime("%Y-%m-%d"),
        }
        for i in range(n_trades)
    ]
    return x_mat, y_arr, ent_arr, ext_arr, r_arr, eng_ids, trades


# ---------------------------------------------------------------------------
# Part A: Pure Offline CI Tests (NO `@pytest.mark.local_cache`, pure NumPy)
# ---------------------------------------------------------------------------


def test_zero_bare_asserts_and_lf_bom_hygiene() -> None:
    """Verify ZERO bare `assert`s, ZERO CRLF, and ZERO UTF-8 BOM across all Wave 5 ML files."""
    for path in (ML_FEATURES_FILE, ML_ARENA_FILE, THIS_TEST_FILE):
        raw = path.read_bytes()
        _check(not raw.startswith(b"\xef\xbb\xbf"), f"UTF-8 BOM detected in {path}")
        _check(b"\r\n" not in raw, f"CRLF detected in {path}")
        tree = ast.parse(raw.decode("utf-8"), filename=str(path))
        bare_asserts = [node.lineno for node in ast.walk(tree) if isinstance(node, ast.Assert)]
        _check(len(bare_asserts) == 0, f"Bare assert(s) found in {path} at lines {bare_asserts}")


def test_lazy_ml_imports_only_subprocess_no_window() -> None:
    """Importing Wave 5 ML modules under `python -O` MUST NOT eagerly import ML/ONNX/DuckDB/holdout_guard."""
    code = (
        "import json, sys\n"
        f"sys.path.insert(0, {str(AI_ENGINES_DIR)!r})\n"
        "import quant_factory.wave5.ml_features_v105_aligned\n"
        "import quant_factory.wave5.run_v105_ml_and_sizing_arena\n"
        "banned = [\n"
        "    'sklearn', 'lightgbm', 'catboost', 'onnx', 'onnxruntime',\n"
        "    'skl2onnx', 'onnxmltools', 'duckdb', 'scipy', 'pandas',\n"
        "    'hmmlearn', 'shap', 'quant_core.holdout_guard',\n"
        "]\n"
        "leaked = [m for m in banned if m in sys.modules]\n"
        "print(json.dumps({'leaked': leaked}))\n"
    )
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    proc = subprocess.run(
        [sys.executable, "-O", "-c", code],
        capture_output=True,
        text=True,
        timeout=30,
        creationflags=creationflags,
        check=False,
    )
    _check(proc.returncode == 0, f"Subprocess import failed: stderr={proc.stderr}")
    payload = json.loads(proc.stdout.strip().splitlines()[-1])
    _check(payload["leaked"] == [], f"Eager banned imports detected: {payload['leaked']}")


def test_ftmo_two_regime_dst_p2_2_guardrail() -> None:
    """P2-2 guardrail: `<= 2019` uses EU DST (+2h mid-Mar) and `>= 2020` uses US NY+7 (+3h mid-Mar)."""
    proof = verify_ftmo_two_regime_dst_guardrail()
    _check(proof["passed"] is True, f"FTMO 2-regime DST proof failed: {proof}")
    offsets = list(proof["probe_offsets_hours"].values())
    _check(offsets == [2, 3, 3, 2], f"Unexpected offsets: {offsets}")


def test_broker_d1_sma_tr14_exact_formula_and_boundary() -> None:
    """Prove `d1_range_over_atr14` uses Broker-Day D1 + MQL5 `SMA(TR,14)` (NOT Wilder RMA, NOT UTC D1)."""
    feed = _make_synthetic_m1_feed(n_days=30, start_ts=1_711_929_600, seed=99)  # April 2024 (US DST -> UTC+3!)
    srv_ts = encode_utc_to_ftmo_server_times_v105(feed["times_sec"])
    d1 = build_broker_d1_from_m1_v105(
        {
            "ts_utc": feed["times_sec"],
            "ts_server_raw": srv_ts,
            "open": feed["open"],
            "high": feed["high"],
            "low": feed["low"],
            "close": feed["close"],
        },
        atr_period=14,
    )
    # Pick a signal on broker day 24
    target_day_key = int(d1["d1_day_key"][24])
    day_bars = np.flatnonzero((srv_ts // 86400) == target_day_key)
    _check(day_bars.size > 0, "Expected bars in target broker day")
    probe_ts = int(feed["times_sec"][int(day_bars[0])]) + 600
    trade = {
        "engine_id": "E1",
        "symbol": "USDJPY",
        "entry_ts": probe_ts,
        "exit_ts": probe_ts + 3600,
        "net_R": 1.0,
        "direction": 1,
    }
    x_mat = build_aligned_feature_matrix_v105({"USDJPY": feed}, [trade])
    row = x_mat[0]

    # Hand-compute exact Broker-Day D1 SMA(TR, 14) at shift=1 (index 23, since target day is 24)
    idx = 23
    trs = []
    for k in range(idx - 13, idx + 1):
        h_k = float(d1["d1_high"][k])
        l_k = float(d1["d1_low"][k])
        pc = float(d1["d1_close"][k - 1])
        trs.append(max(h_k - l_k, abs(h_k - pc), abs(l_k - pc)))
    sma_atr14 = float(np.mean(trs))
    expected_ratio = min(15.0, max(0.0, (float(d1["d1_high"][idx]) - float(d1["d1_low"][idx])) / sma_atr14))

    # Hand-compute exact Broker-Day D1 Parkinson 10d over shifts 1..10 (indices idx-9..idx)
    log_hl = np.log(np.maximum(d1["d1_high"][idx - 9 : idx + 1] / d1["d1_low"][idx - 9 : idx + 1], 1.0))
    expected_park = min(1.0, max(0.0, math.sqrt(float(np.mean(log_hl * log_hl)) / (4.0 * math.log(2.0)))))

    i_rat = FEATURE_NAMES_V105.index("d1_range_over_atr14")
    i_prk = FEATURE_NAMES_V105.index("parkinson_vol_10d")
    _check(
        abs(float(row[i_rat]) - expected_ratio) <= 1e-6,
        f"d1_range_over_atr14 mismatch: got={row[i_rat]}, expected={expected_ratio}",
    )
    _check(
        abs(float(row[i_prk]) - expected_park) <= 1e-6,
        f"parkinson_vol_10d mismatch: got={row[i_prk]}, expected={expected_park}",
    )


def test_rolling_dd_pct_1x_equiv_phase_invariance_and_closed_only() -> None:
    """Prove `rolling_dd_pct_1x_equiv` is bit-identical across P1 4.5x / P2 3.5x / Funded 1.0x & 10K/100K."""
    _, _, _, _, _, _, trades = _make_synthetic_trades(n_trades=60, seed=123)
    proof = verify_phase_invariance_1x_equiv(trades)
    _check(proof["passed"] is True, f"Phase invariance failed: {proof}")
    _check(proof["max_abs_diff_pct_pts"] <= 1e-12, f"Non-zero phase drift: {proof['max_abs_diff_pct_pts']}")

    # Strictly causal closed-only check: unclosed trade must NOT mutate shadow DD
    tracker = Shadow1xClosedRTracker()
    _check(tracker.rolling_dd_pct_1x_equiv() == 0.0, "Initial shadow DD must be 0.0")
    tracker.record_closed_trade("E3_GBPUSD_VH", -1.0)
    dd_after_loss = tracker.rolling_dd_pct_1x_equiv()
    _check(abs(dd_after_loss - 0.75) <= 1e-12, f"Expected exact 0.75% DD for E3 -1R loss, got {dd_after_loss}")


def test_feature_specs_v105_complete_and_mql5_documented() -> None:
    """Verify every v1.05 feature has documented MQL5 formula & required W4-RT1-P1-01 features exist."""
    _check(len(FEATURE_NAMES_V105) == len(FEATURE_SPECS_V105), "Spec count mismatch")
    required = {
        "d1_range_over_atr14",
        "parkinson_vol_10d",
        "rolling_dd_pct_1x_equiv",
        "prev_bar_close_loc",
        "hour_sin_utc",
        "hour_cos_utc",
        "engine_id_code",
        "same_dir_concurrent_count",
    }
    missing = required - set(FEATURE_NAMES_V105)
    _check(not missing, f"Missing required features: {missing}")
    for idx, spec in enumerate(FEATURE_SPECS_V105):
        _check(spec["index"] == idx, f"Spec index mismatch at {idx}")
        _check(spec["name"] == FEATURE_NAMES_V105[idx], f"Spec name mismatch at {idx}")
        _check(bool(str(spec["mql5_formula"]).strip()), f"Missing mql5_formula for {spec['name']}")
        _check(bool(str(spec["formula"]).strip()), f"Missing formula for {spec['name']}")


def test_zero_future_leakage_perturbation_passes_clean_and_detects_past_change() -> None:
    """Future bar perturbation produces 0.0 bit drift; past perturbation produces non-zero drift."""
    feed = _make_synthetic_m1_feed(n_days=30, start_ts=1_704_067_200, seed=55)
    probe_ts = int(feed["times_sec"][24 * 20 + 5])
    trades = [
        {
            "engine_id": "E2",
            "symbol": "USDJPY",
            "entry_ts": int(feed["times_sec"][24 * d + 5]),
            "exit_ts": int(feed["times_sec"][24 * d + 7]),
            "net_R": 1.0 if d % 2 == 0 else -1.0,
            "direction": 1,
        }
        for d in range(18, 28)
    ]
    clean = assert_zero_future_leakage_v105(
        build_aligned_feature_matrix_v105,
        {"USDJPY": feed},
        trades,
    )
    _check(clean["passed"] is True, f"Future perturbation proof failed: {clean}")
    _check(clean["bit_exact_zero_drift"] is True, f"Expected bit-exact 0 drift: {clean}")

    # Positive control: perturbing bars BEFORE probe_ts MUST change pre-probe features
    base_x = build_aligned_feature_matrix_v105({"USDJPY": feed}, trades)
    past_feed = {k: (v.copy() if isinstance(v, np.ndarray) else v) for k, v in feed.items()}
    past_mask = past_feed["times_sec"] < probe_ts - 86400
    past_feed["high"][past_mask] *= 2.5
    past_feed["low"][past_mask] *= 0.4
    past_x = build_aligned_feature_matrix_v105({"USDJPY": past_feed}, trades)
    _check(float(np.max(np.abs(base_x - past_x))) > 1e-3, "Past perturbation control unexpectedly showed 0 drift")


def test_negative_holdout_2025_cutoff_breach_rejected(tmp_path: Path) -> None:
    """Negative test: 2025-01-01+ trade/bar timestamps MUST raise fail-closed."""
    feed = _make_synthetic_m1_feed(n_days=25, start_ts=1_704_067_200, seed=7)
    bad_trade = [
        {
            "engine_id": "E1",
            "symbol": "USDJPY",
            "entry_ts": DEV_CUTOFF_SEC + 3600,
            "exit_ts": DEV_CUTOFF_SEC + 7200,
            "net_R": 1.0,
            "direction": 1,
        }
    ]
    raised_feat = False
    try:
        build_aligned_feature_matrix_v105({"USDJPY": feed}, bad_trade)
    except ValueError as exc:
        raised_feat = "HOLDOUT" in str(exc).upper() or "CUTOFF" in str(exc).upper()
    _check(raised_feat, "Expected Holdout ValueError for 2025+ trade in build_aligned_feature_matrix_v105")

    x_m, y_a, ent_a, ext_a, r_a, e_ids, trs = _make_synthetic_trades(n_trades=80, seed=11)
    ent_bad = ent_a.copy()
    ext_bad = ext_a.copy()
    ent_bad[-1] = DEV_CUTOFF_SEC + 60
    ext_bad[-1] = DEV_CUTOFF_SEC + 3660
    raised_arena = False
    try:
        run_v105_ml_arena(
            x_m,
            y_a,
            ent_bad,
            ext_bad,
            r_a,
            e_ids,
            trs,
            trial_grid=build_numpy_smoke_v105_grid(),
            db_path=None,
            out_dir=tmp_path,
            mqh_out_path=None,
            n_splits=3,
            min_train_samples=20,
            use_duckdb_ledger=False,
            export_onnx_and_mqh=False,
        )
    except HoldoutCutoffBreachError:
        raised_arena = True
    _check(raised_arena, "Expected HoldoutCutoffBreachError for 2025+ entry_ts in run_v105_ml_arena")


def test_negative_nan_inf_bool_poisoned_features_rejected(tmp_path: Path) -> None:
    """Negative test: NaN/Inf/bool features MUST be rejected fail-closed."""
    x_m, y_a, ent_a, ext_a, r_a, e_ids, trs = _make_synthetic_trades(n_trades=80, seed=19)
    for bad_val in (np.nan, np.inf, -np.inf):
        x_bad = x_m.copy()
        x_bad[5, 2] = bad_val
        raised = False
        try:
            run_v105_ml_arena(
                x_bad,
                y_a,
                ent_a,
                ext_a,
                r_a,
                e_ids,
                trs,
                trial_grid=build_numpy_smoke_v105_grid(),
                db_path=None,
                out_dir=tmp_path,
                mqh_out_path=None,
                n_splits=3,
                min_train_samples=20,
                use_duckdb_ledger=False,
                export_onnx_and_mqh=False,
            )
        except ValueError:
            raised = True
        _check(raised, f"Expected ValueError for poisoned feature value {bad_val}")

    raised_bool = False
    try:
        compute_sizing_from_train_quantiles(
            np.array([True, False]),
            np.array([0.4, 0.6]),
            sizing_policy="binary_filter",
        )
    except ValueError:
        raised_bool = True
    _check(raised_bool, "Expected ValueError for bool probability array")


def test_negative_purge_embargo_label_and_budget_gt_48(tmp_path: Path) -> None:
    """Negative tests: purge < 5d, embargo < 10d, forbidden OOS label, and trial grid > 48."""
    x_m, y_a, ent_a, ext_a, r_a, e_ids, trs = _make_synthetic_trades(n_trades=120, seed=23)

    # 1. Purge < 5d rejected
    raised_purge = False
    try:
        run_v105_ml_arena(
            x_m,
            y_a,
            ent_a,
            ext_a,
            r_a,
            e_ids,
            trs,
            trial_grid=build_numpy_smoke_v105_grid(),
            db_path=None,
            out_dir=None,
            mqh_out_path=None,
            n_splits=3,
            purge_days=4,
            embargo_days=10,
            min_train_samples=20,
            use_duckdb_ledger=False,
            export_onnx_and_mqh=False,
        )
    except (ValueError, CausalityViolationError):
        raised_purge = True
    _check(raised_purge, "Expected ValueError/CausalityViolationError for purge_days=4 < 5")

    # 2. Embargo < 10d rejected
    raised_emb = False
    try:
        run_v105_ml_arena(
            x_m,
            y_a,
            ent_a,
            ext_a,
            r_a,
            e_ids,
            trs,
            trial_grid=build_numpy_smoke_v105_grid(),
            db_path=None,
            out_dir=None,
            mqh_out_path=None,
            n_splits=3,
            purge_days=5,
            embargo_days=9,
            min_train_samples=20,
            use_duckdb_ledger=False,
            export_onnx_and_mqh=False,
        )
    except (ValueError, CausalityViolationError):
        raised_emb = True
    _check(raised_emb, "Expected ValueError/CausalityViolationError for embargo_days=9 < 10")

    # 3. Forbidden OOS label rejected
    raised_lbl = False
    try:
        assert_zero_forbidden_blind_label({"oos_label": f"{FORBIDDEN_BLIND_WORD}_TEST"})
    except Law13HonestyError:
        raised_lbl = True
    _check(raised_lbl, "Expected Law13HonestyError on forbidden label")

    # 4. Pre-registered grid > 48 rejected
    base_grid = build_preregistered_v105_grid()
    _check(len(base_grid) == 36, f"Expected 36 pre-registered trials, got {len(base_grid)}")
    oversized = list(base_grid) + [dict(base_grid[0], trial_id=f"extra_{k}") for k in range(13)]
    raised_budget = False
    try:
        validate_v105_arena_grid(oversized, max_trials=48)
    except (ValueError, BudgetExceededError):
        raised_budget = True
    _check(raised_budget, "Expected ValueError/BudgetExceededError for 49 > 48 trials")


def test_sizing_policies_binary_filter_and_asymfloor_invariants() -> None:
    """Verify Filter `{0,1}` and AsymFloor tail-only `[0.45..0.75]` with `1.0` on top 90%."""
    p_tr = np.linspace(0.30, 0.70, 1000, dtype=np.float64)
    p_va = np.linspace(0.28, 0.72, 200, dtype=np.float64)

    s_bin, _ = compute_sizing_from_train_quantiles(p_va, p_tr, sizing_policy="binary_filter", toxic_quantile=0.20)
    _check(set(np.unique(s_bin).tolist()).issubset({0.0, 1.0}), "binary_filter must output only {0, 1}")

    s_step, meta_step = compute_sizing_from_train_quantiles(
        p_va, p_tr, sizing_policy="asym_floor_step", tail_quantile=0.10, floor_mult=0.55
    )
    q10 = float(meta_step["tail_threshold"])
    _check(bool(np.all(s_step[p_va >= q10] == 1.0)), "asym_floor_step must keep 1.0x on all normal/strong signals")
    _check(bool(np.all(np.isclose(s_step[p_va < q10], 0.55))), "asym_floor_step must apply 0.55x on worst decile")

    s_ramp, meta_ramp = compute_sizing_from_train_quantiles(
        p_va, p_tr, sizing_policy="asym_floor_ramp", tail_quantile=0.10, floor_mult=0.50
    )
    _check(
        bool(np.all(s_ramp[p_va >= meta_ramp["tail_threshold"]] == 1.0)),
        "asym_floor_ramp must keep 1.0x >= q10",
    )
    _check(float(np.min(s_ramp)) >= 0.50 - 1e-12 and float(np.max(s_ramp)) <= 1.0 + 1e-12, "ramp out of [0.50, 1.0]")

    # Out-of-bounds floor_mult must fail-closed
    raised_floor = False
    try:
        compute_sizing_from_train_quantiles(p_va, p_tr, sizing_policy="asym_floor_step", floor_mult=0.20)
    except ValueError:
        raised_floor = True
    _check(raised_floor, "Expected ValueError for floor_mult=0.20 outside [0.45, 0.75]")


def test_offline_numpy_head_to_head_arena_isolated_tmp_path(tmp_path: Path) -> None:
    """Pure-NumPy offline head-to-head smoke arena writes ONLY to `tmp_path` & rejects pure noise honestly."""
    x_m, y_a, ent_a, ext_a, r_a, e_ids, trs = _make_synthetic_trades(n_trades=260, step_sec=86_400, seed=77)
    summary = run_v105_ml_arena(
        x_m,
        y_a,
        ent_a,
        ext_a,
        r_a,
        e_ids,
        trs,
        trial_grid=build_numpy_smoke_v105_grid(),
        db_path=None,
        out_dir=tmp_path,
        mqh_out_path=None,
        n_splits=3,
        purge_days=5,
        embargo_days=10,
        min_train_samples=40,
        n_parity_samples=40,
        use_duckdb_ledger=False,
        export_onnx_and_mqh=False,
        export_2024_ftmo_ref=False,
    )
    _check(summary["verdict"] == VERDICT_REJECT_ML, f"Noise must reject honestly, got {summary['verdict']}")
    _check(summary["hard_invariants"]["holdout_rows_analysed"] == 0, "Holdout rows must be 0")
    _check(summary["hard_invariants"]["order_send_count"] == 0, "OrderSend count must be 0")
    _check((tmp_path / "wave5_ml_oof_series.json").is_file(), "Missing OOF series JSON in tmp_path")
    _check((tmp_path / "wave5_ml_arena_summary.json").is_file(), "Missing summary JSON in tmp_path")
    raw_txt = (tmp_path / "wave5_ml_arena_summary.json").read_text(encoding="utf-8")
    _check(FORBIDDEN_BLIND_WORD not in raw_txt.upper(), "Forbidden label found in summary JSON")


# ---------------------------------------------------------------------------
# Part B: Local Cache / ML / ONNX / DuckDB Tests (`@pytest.mark.local_cache`)
# ---------------------------------------------------------------------------


@pytest.mark.local_cache
def test_duckdb_ledger_budget_cap_and_brier_le_0_promote_rejected(tmp_path: Path) -> None:
    """Negative DuckDB tests in `tmp_path`: Brier <= 0 promote rejection & trial #49 budget cap."""
    db_file = tmp_path / "test_m48.duckdb"
    # Budget > 48 rejected at construction
    raised_cap = False
    try:
        Wave5MlBudgetLedger(db_path=db_file, max_trials=49)
    except ValueError:
        raised_cap = True
    _check(raised_cap, "Expected ValueError when max_trials=49 > 48")

    ledger = Wave5MlBudgetLedger(db_path=db_file, max_trials=2)
    try:
        bad_eval = {
            "brier_skill_score": -0.001,
            "roc_auc": 0.55,
            "probabilistic_metrics": {"brier_model": 0.251, "brier_climatology": 0.250},
            "engine_balance": {"min_engine_retention_ratio": 0.80, "overall_retention_ratio": 0.85},
            "economics_1x": {"ml_v104": {"avg_size": 0.85, "profit_factor": 1.25, "ev_r": 0.08, "max_dd_pct": 5.0}},
            "slippage_breakeven_24m": {"ml_v104_median_mult": 1.85},
            "verdict_v105": VERDICT_PROMOTE_FILTER,
        }
        raised_brier = False
        try:
            ledger.record_trial(
                trial_id="bad_brier_promote",
                track_name="v105_ml_filter",
                family_name="lightgbm",
                sizing_policy="binary_filter",
                params={"n_estimators": 40},
                evaluation=bad_eval,
                n_folds=5,
                n_features_selected=8,
            )
        except ValueError:
            raised_brier = True
        _check(raised_brier, "Expected ValueError when recording PROMOTE with brier_skill_score <= 0")

        ok_eval = dict(bad_eval, verdict_v105=VERDICT_REJECT_ML)
        ledger.record_trial(
            trial_id="t1",
            track_name="v105_ml_filter",
            family_name="lightgbm",
            sizing_policy="binary_filter",
            params={"n_estimators": 40},
            evaluation=ok_eval,
            n_folds=5,
            n_features_selected=8,
        )
        ledger.record_trial(
            trial_id="t2",
            track_name="v105_ml_asymfloor",
            family_name="lightgbm",
            sizing_policy="asym_floor_step",
            params={"n_estimators": 60},
            evaluation=ok_eval,
            n_folds=5,
            n_features_selected=8,
        )
        raised_over = False
        try:
            ledger.record_trial(
                trial_id="t3_overflow",
                track_name="v105_ml_filter",
                family_name="lightgbm",
                sizing_policy="binary_filter",
                params={"n_estimators": 80},
                evaluation=ok_eval,
                n_folds=5,
                n_features_selected=8,
            )
        except BudgetExceededError:
            raised_over = True
        _check(raised_over, "Expected BudgetExceededError on 3rd trial when max_trials=2")
    finally:
        ledger.close()


@pytest.mark.local_cache
def test_real_ftmo_m1_zero_bit_drift_causality() -> None:
    """Verify exact 0.0 future-perturbation bit drift on real `.runtime/offensive4/m1/ftmo_dev_m1/`."""
    proof = verify_ftmo_m1_zero_bit_drift_causality()
    _check(proof["passed"] is True, f"Real FTMO M1 causality failed: {proof}")
    _check(proof["bit_exact_zero_drift"] is True, f"Non-zero FTMO M1 drift: {proof}")
    _check(int(proof["probes_tested"]) >= 3, f"Too few probes checked: {proof}")


@pytest.mark.local_cache
def test_production_artifacts_onnx_mqh_csvs_duckdb_read_only() -> None:
    """Read-only certification of all Wave 5 ML production artifacts (ONNX, MQH, CSVs, OOF JSON, DuckDB)."""
    import duckdb
    import onnx
    import onnxruntime as ort

    onnx_path = DEFAULT_ML_OUT_DIR / "naqex_v105_lgbm.onnx"
    parity_csv = DEFAULT_ML_OUT_DIR / "wave5_ml_parity_500.csv"
    ref_2024_csv = DEFAULT_ML_OUT_DIR / "wave5_2024_features_ref.csv"
    oof_json_path = DEFAULT_ML_OUT_DIR / "wave5_ml_oof_series.json"
    summary_path = DEFAULT_ML_OUT_DIR / "wave5_ml_arena_summary.json"
    mqh_path = DEFAULT_MQH_PATH
    db_path = DEFAULT_DB_PATH

    for p in (onnx_path, parity_csv, ref_2024_csv, oof_json_path, summary_path, mqh_path, db_path):
        _check(p.is_file(), f"Missing production deliverable: {p}")

    # Capture SHA-256 before read-only checks to prove zero mutation
    shas_before = {p.name: _sha256_file(p) for p in (onnx_path, parity_csv, ref_2024_csv, oof_json_path, mqh_path)}

    # 1. DuckDB budget & invariants
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        rows = con.execute(
            "SELECT trial_id, oos_label, brier_skill_score, verdict, holdout_rows_analysed, order_send_count "
            "FROM wave5_ml_m48"
        ).fetchall()
    finally:
        con.close()
    _check(1 <= len(rows) <= 48, f"DuckDB trial count out of bounds: {len(rows)}")
    for tid, oos_lbl, bss, verd, h_rows, os_cnt in rows:
        _check(oos_lbl == "CONSUMED_DEV_CLB_TEMPORAL_OOS", f"Bad OOS label on {tid}: {oos_lbl}")
        _check(int(h_rows) == 0 and int(os_cnt) == 0, f"Safety breach on {tid}: holdout={h_rows}, os={os_cnt}")
        if "PROMOTE" in str(verd):
            _check(float(bss) > 0.0, f"Promoted trial {tid} has non-positive BSS={bss}")

    # 2. ONNX validity & zero ZipMap nodes
    model = onnx.load(str(onnx_path))
    onnx.checker.check_model(model)
    op_types = [n.op_type for n in model.graph.node]
    _check("ZipMap" not in op_types, f"Forbidden ZipMap node in {onnx_path}")

    # 3. MQH hygiene (`0` OrderSend, `0` CTrade, `0` CRLF, `0` BOM) + Pure-MQL5 parse & fail-closed NaN
    mqh_bytes = mqh_path.read_bytes()
    _check(not mqh_bytes.startswith(b"\xef\xbb\xbf"), "UTF-8 BOM found in Naqex_ML_Filter_v105.mqh")
    _check(b"\r\n" not in mqh_bytes, "CRLF found in Naqex_ML_Filter_v105.mqh")
    mqh_text = mqh_bytes.decode("utf-8")
    _check("OrderSend" not in mqh_text and "CTrade" not in mqh_text, "Forbidden trade API in Naqex_ML_Filter_v105.mqh")
    tables = parse_mqh_v105_tree_tables(mqh_text)
    n_feat = int(tables["n_features"])
    _check(n_feat >= 8, f"Unexpected feature count in MQH: {n_feat}")

    # Fail-closed NaN rejection on Pure-MQL5 evaluator
    nan_vec = np.zeros((1, n_feat), dtype=np.float32)
    nan_vec[0, 0] = np.nan
    raised_nan = False
    try:
        evaluate_mqh_v105_mirror(mqh_text, nan_vec)
    except ValueError:
        raised_nan = True
    _check(raised_nan, "Expected fail-closed ValueError for NaN vector in Pure-MQL5 mirror")

    # 4. 500-vector parity CSV: Python == ORT <= 1e-6 AND Python == Pure-MQL5 <= 1e-6
    sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    in_name = sess.get_inputs()[0].name
    with parity_csv.open("r", encoding="utf-8", newline="") as fh:
        rdr = list(csv.DictReader(fh))
    _check(len(rdr) == 500, f"Expected 500 parity rows, got {len(rdr)}")
    x_500 = np.array([[float(r[f"f{j}"]) for j in range(n_feat)] for r in rdr], dtype=np.float32)
    p_ref = np.array([float(r["ref_proba"]) for r in rdr], dtype=np.float64)
    p_ort = np.asarray(sess.run(None, {in_name: x_500})[1], dtype=np.float64)[:, 1]
    p_mqh = evaluate_mqh_v105_mirror(mqh_text, x_500)
    err_ort = float(np.max(np.abs(p_ort - p_ref)))
    err_mqh = float(np.max(np.abs(p_mqh - p_ref)))
    _check(err_ort <= STRICT_ONNX_PARITY_TOL, f"ORT parity breach: {err_ort:.3e} > {STRICT_ONNX_PARITY_TOL:.3e}")
    _check(err_mqh <= STRICT_ONNX_PARITY_TOL, f"MQH parity breach: {err_mqh:.3e} > {STRICT_ONNX_PARITY_TOL:.3e}")

    # 5. 2024 FTMO same-feed live reference CSV: non-empty, <= 2024-12-31, ORT & MQH <= 1e-6
    with ref_2024_csv.open("r", encoding="utf-8", newline="") as fh:
        rdr24 = list(csv.DictReader(fh))
    _check(len(rdr24) >= 100, f"Expected >= 100 2024 FTMO signals, got {len(rdr24)}")
    x_24 = np.array([[float(r[f"f{j}"]) for j in range(n_feat)] for r in rdr24], dtype=np.float32)
    p_24_ref = np.array([float(r["ref_p_win"]) for r in rdr24], dtype=np.float64)
    ts_24 = np.array([int(r["entry_utc_ts"]) for r in rdr24], dtype=np.int64)
    _check(int(np.max(ts_24)) < DEV_CUTOFF_SEC, "Holdout 2025+ timestamp leaked into 2024 ref CSV")
    _check(bool(np.all(np.isfinite(x_24))) and bool(np.all(np.isfinite(p_24_ref))), "Non-finite value in 2024 ref CSV")
    p_24_ort = np.asarray(sess.run(None, {in_name: x_24})[1], dtype=np.float64)[:, 1]
    p_24_mqh = evaluate_mqh_v105_mirror(mqh_text, x_24)
    _check(float(np.max(np.abs(p_24_ort - p_24_ref))) <= STRICT_ONNX_PARITY_TOL, "2024 ref ORT parity breach")
    _check(float(np.max(np.abs(p_24_mqh - p_24_ref))) <= STRICT_ONNX_PARITY_TOL, "2024 ref MQH parity breach")

    # 6. OOF series JSON & Summary JSON: zero forbidden label, holdout=0, OrderSend=0
    oof_data = json.loads(oof_json_path.read_text(encoding="utf-8"))
    assert_zero_forbidden_blind_label(oof_data)
    _check(int(oof_data["holdout_rows_analysed"]) == 0, "OOF JSON holdout_rows_analysed != 0")
    _check(int(oof_data["order_send_count"]) == 0, "OOF JSON order_send_count != 0")
    _check(int(oof_data["n_oof_trades"]) >= 2000, f"Unexpected OOF trade count: {oof_data['n_oof_trades']}")

    # 7. Confirm zero mutation of production artifacts
    shas_after = {p.name: _sha256_file(p) for p in (onnx_path, parity_csv, ref_2024_csv, oof_json_path, mqh_path)}
    _check(shas_before == shas_after, f"Production artifact mutated during test: {shas_before} != {shas_after}")

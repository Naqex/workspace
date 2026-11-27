"""Unit, fail-closed, and `W4-G04` causality-mutation tests for Wave 4 24-feature builder."""

from __future__ import annotations

import ast
import math
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from quant_factory.wave4 import ml_features_24 as mf

MODULE_PATH = Path(mf.__file__).resolve()
AI_ENGINES_DIR = MODULE_PATH.parents[2]
_NO_WINDOW_FLAGS = int(getattr(subprocess, "CREATE_NO_WINDOW", 0)) if os.name == "nt" else 0


# ---------------------------------------------------------------------------
# Deterministic Synthetic Offline Fixtures (100% CI-Safe, Zero Local Cache)
# ---------------------------------------------------------------------------


def _make_synthetic_d1_bars(
    *,
    n_bars: int = 160,
    start_ts: int = 1_672_531_200,  # 2023-01-01T00:00:00Z
    base_price: float = 150.0,
    base_spread: float = 0.012,
    seed: int = 42,
) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    times = start_ts + np.arange(n_bars, dtype=np.int64) * np.int64(86400)
    rets = rng.normal(loc=0.0004, scale=0.0085, size=n_bars)
    close = base_price * np.exp(np.cumsum(rets))
    open_px = np.empty(n_bars, dtype=np.float64)
    open_px[0] = base_price
    open_px[1:] = close[:-1] * np.exp(rng.normal(0.0, 0.0015, size=n_bars - 1))
    wick_up = np.abs(rng.normal(0.003, 0.002, size=n_bars)) * close
    wick_dn = np.abs(rng.normal(0.003, 0.002, size=n_bars)) * close
    high = np.maximum(open_px, close) + wick_up
    low = np.maximum(1e-4, np.minimum(open_px, close) - wick_dn)
    spread = base_spread * (1.0 + 0.35 * np.abs(rng.normal(0.0, 1.0, size=n_bars)))
    return {
        "times_sec": times,
        "open": open_px,
        "high": high,
        "low": low,
        "close": close,
        "spread_price": spread,
        "bar_duration_sec": 86400,
    }


def _make_synthetic_m1_bars(
    *,
    n_days: int = 40,
    bars_per_day: int = 30,
    start_ts: int = 1_672_531_200,  # 2023-01-01T00:00:00Z
    base_price: float = 18000.0,
    base_spread: float = 1.5,
    seed: int = 77,
) -> dict[str, Any]:
    """Generate compact M1 Bid/Ask quotes spanning `n_days` UTC calendar days."""
    rng = np.random.default_rng(seed)
    ts_list: list[int] = []
    for d in range(n_days):
        day_base = start_ts + d * 86400 + 8 * 3600  # 08:00..08:29 UTC each day
        for m in range(bars_per_day):
            ts_list.append(day_base + m * 60)
    ts = np.array(ts_list, dtype=np.int64)
    n = ts.size
    rets = rng.normal(0.00005, 0.0012, size=n)
    bc = base_price * np.exp(np.cumsum(rets))
    bo = np.empty(n, dtype=np.float64)
    bo[0] = base_price
    bo[1:] = bc[:-1]
    bh = np.maximum(bo, bc) + np.abs(rng.normal(0.0005, 0.0003, size=n)) * bc
    bl = np.maximum(1.0, np.minimum(bo, bc) - np.abs(rng.normal(0.0005, 0.0003, size=n)) * bc)
    sp = base_spread * (1.0 + 0.4 * np.abs(rng.normal(0.0, 1.0, size=n)))
    ao, ah, al, ac = bo + sp, bh + sp, bl + sp, bc + sp
    quotes = np.column_stack([bo, bh, bl, bc, ao, ah, al, ac])
    return {
        "times_sec": ts,
        "quotes": quotes,
        "bar_duration_sec": 60,
    }


def _make_synthetic_dataset() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    bars_usd = _make_synthetic_d1_bars(n_bars=160, base_price=145.0, base_spread=0.015, seed=11)
    bars_us100 = _make_synthetic_d1_bars(n_bars=160, base_price=16500.0, base_spread=1.8, seed=22)
    bars_xau = _make_synthetic_d1_bars(n_bars=160, base_price=2150.0, base_spread=0.28, seed=33)
    bars = {
        "USDJPY": bars_usd,
        "US100.cash": bars_us100,
        "XAUUSD": bars_xau,
    }
    t0 = int(bars_usd["times_sec"][0])
    trades: list[dict[str, Any]] = []
    specs = [
        ("E1_USDJPY_TOKYO", "USDJPY", 1, 1.8, 0.25),
        ("E2_USDJPY_EXP80", "USDJPY", 1, -1.0, 0.50),
        ("E4_US100_SESS40", "US100", -1, 2.2, 0.50),
        ("S7_XAU_EXP120", "XAUUSD", 1, -0.8, 0.50),
    ]
    for step, day_idx in enumerate(range(70, 140, 3)):
        eng, sym, side, net_r, risk_pct = specs[step % len(specs)]
        entry_ts = t0 + day_idx * 86400 + (13 * 3600 if step % 2 == 0 else 8 * 3600)
        exit_ts = entry_ts + 6 * 3600
        trades.append(
            {
                "engine_id": eng,
                "symbol": sym,
                "entry_ts": entry_ts,
                "exit_ts": exit_ts,
                "side": side,
                "net_R": net_r if step % 3 != 0 else -1.0,
                "risk_pct": risk_pct,
            }
        )
    # Add an explicitly overlapping trade to exercise same_dir_concurrent_count & exit_ts gating
    overlap_base = trades[5]["entry_ts"]
    trades.append(
        {
            "engine_id": "E7_USDJPY_NY10ET",
            "symbol": "USDJPY",
            "entry_ts": overlap_base + 1800,
            "exit_ts": overlap_base + 5 * 3600,
            "side": trades[5]["side"],
            "net_R": 3.5,
            "risk_pct": 0.50,
        }
    )
    return bars, trades


# ---------------------------------------------------------------------------
# 1. Schema, Exact 24 Features, Dtype, Zero NaN/Inf, & CI Hygiene Tests
# ---------------------------------------------------------------------------


def test_exact_24_feature_names_and_safety_invariants() -> None:
    expected = (
        # Group A — Volatility & ATR Regime (6)
        "atr14_pct",
        "atr5_over_atr20",
        "vol_zscore_60d",
        "d1_range_over_atr14",
        "parkinson_vol_10d",
        "vol_brake_mult_causal",
        # Group B — Trend & Breakout Structure (6)
        "adx14_causal",
        "ema20_slope_atr",
        "dist_ema50_atr",
        "breakout_zscore_20",
        "prev_bar_body_ratio",
        "prev_bar_close_loc",
        # Group C — Microstructure, Cost & Session (6)
        "spread_over_atr_ratio",
        "spread_zscore_20",
        "hour_sin_utc",
        "hour_cos_utc",
        "dow_sin",
        "is_london_ny_overlap",
        # Group D — Portfolio State & Engine Context (6)
        "engine_id_code",
        "asset_class_code",
        "same_dir_concurrent_count",
        "recent_10_wr_causal",
        "recent_10_avg_r_causal",
        "rolling_dd_pct_causal",
    )
    assert len(mf.FEATURE_NAMES_24) == 24
    assert mf.FEATURE_NAMES_24 == expected
    assert len(mf.FEATURE_SPECS_24) == 24
    assert tuple(spec["name"] for spec in mf.FEATURE_SPECS_24) == expected
    assert mf.ORDER_SEND_CAPABLE is False
    assert mf.ORDER_SEND_COUNT == 0
    assert mf.HOLDOUT_CUTOFF_DATE == "2024-12-31"
    assert mf.DEV_CUTOFF_SEC == int(datetime(2025, 1, 1, tzinfo=UTC).timestamp())


def test_zero_bare_asserts_and_lazy_ml_imports_only() -> None:
    src = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(MODULE_PATH))
    bare_asserts = [node.lineno for node in ast.walk(tree) if isinstance(node, ast.Assert)]
    assert bare_asserts == [], f"Found bare assert statements on lines {bare_asserts} (unsafe under python -O)"

    # Verify in a clean subprocess under `-O` that importing ml_features_24 loads ZERO optional ML libs
    code = "\n".join(
        [
            "import sys",
            f"sys.path.insert(0, {str(AI_ENGINES_DIR)!r})",
            "import quant_factory.wave4.ml_features_24 as mf",
            "forbidden = ('sklearn', 'lightgbm', 'catboost', 'onnx', 'onnxruntime', "
            "'skl2onnx', 'onnxmltools', 'pandas', 'pyarrow', 'scipy')",
            "loaded = [m for m in forbidden if m in sys.modules]",
            "if loaded:",
            "    raise RuntimeError(f'Unexpected eager imports: {loaded}')",
            "if len(mf.FEATURE_NAMES_24) != 24:",
            "    raise RuntimeError('Expected 24 features')",
        ]
    )
    proc = subprocess.run(
        [sys.executable, "-O", "-c", code],
        capture_output=True,
        text=True,
        check=False,
        creationflags=_NO_WINDOW_FLAGS,
    )
    assert proc.returncode == 0, f"Lazy import check failed:\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"


def test_build_matrix_shape_dtype_finite_and_row_order_invariance() -> None:
    bars, trades = _make_synthetic_dataset()
    x_mat, meta = mf.build_causal_feature_matrix(bars, trades, cutoff_utc="2024-12-31", return_metadata=True)

    assert isinstance(x_mat, np.ndarray)
    assert x_mat.shape == (len(trades), 24)
    assert x_mat.dtype == np.float32
    assert bool(np.all(np.isfinite(x_mat)))
    assert meta["holdout_rows_analysed"] == 0
    assert meta["order_send_count"] == 0
    assert meta["n_features"] == 24

    # Verify key domain bounds
    idx = {name: i for i, name in enumerate(mf.FEATURE_NAMES_24)}
    assert np.all((x_mat[:, idx["vol_brake_mult_causal"]] >= 0.25) & (x_mat[:, idx["vol_brake_mult_causal"]] <= 1.0))
    assert np.all((x_mat[:, idx["adx14_causal"]] >= 0.0) & (x_mat[:, idx["adx14_causal"]] <= 100.0))
    assert np.all((x_mat[:, idx["prev_bar_body_ratio"]] >= -1.0) & (x_mat[:, idx["prev_bar_body_ratio"]] <= 1.0))
    assert np.all((x_mat[:, idx["prev_bar_close_loc"]] >= 0.0) & (x_mat[:, idx["prev_bar_close_loc"]] <= 1.0))
    assert np.all((x_mat[:, idx["recent_10_wr_causal"]] >= 0.0) & (x_mat[:, idx["recent_10_wr_causal"]] <= 1.0))
    assert np.all((x_mat[:, idx["rolling_dd_pct_causal"]] >= 0.0) & (x_mat[:, idx["rolling_dd_pct_causal"]] <= 100.0))
    assert set(np.unique(x_mat[:, idx["is_london_ny_overlap"]]).tolist()).issubset({0.0, 1.0})

    # Verify overlapping trade observed concurrency >= 1 AND did not leak its concurrent trade's unclosed PnL
    assert x_mat[-1, idx["same_dir_concurrent_count"]] >= 1.0

    # Shuffling input rows must produce identical feature rows after aligning back!
    perm = list(reversed(range(len(trades))))
    trades_rev = [trades[i] for i in perm]
    x_rev = mf.build_causal_feature_matrix(bars, trades_rev, cutoff_utc="2024-12-31")
    assert np.array_equal(x_mat[perm], x_rev)

    # Empty trades input returns (0, 24) float32 cleanly
    x_empty = mf.build_causal_feature_matrix(bars, [], cutoff_utc="2024-12-31")
    assert x_empty.shape == (0, 24)
    assert x_empty.dtype == np.float32


def test_m1_quotes_resampling_and_column_dict_input() -> None:
    bars_m1 = {"US100": _make_synthetic_m1_bars(n_days=40, bars_per_day=30, seed=99)}
    start_ts = int(bars_m1["US100"]["times_sec"][0])
    # Entries at 08:15 UTC on days 15..35 (completed D1 bars < entry_day, completed M1 bars <= 08:14)
    trades_col_dict = {
        "engine_id": ["E4_US100_SESS40"] * 10,
        "symbol": ["US100.cash"] * 10,
        "entry_ts": [start_ts + d * 86400 + 15 * 60 for d in range(15, 35, 2)],
        "exit_ts": [start_ts + d * 86400 + 25 * 60 for d in range(15, 35, 2)],
        "side": [1 if i % 2 == 0 else -1 for i in range(10)],
        "net_R": [1.5 if i % 2 == 0 else -1.0 for i in range(10)],
    }
    x_mat = mf.build_causal_feature_matrix(bars_m1, trades_col_dict, cutoff_utc="2024-12-31")
    assert x_mat.shape == (10, 24)
    assert x_mat.dtype == np.float32
    assert bool(np.all(np.isfinite(x_mat)))

    proof = mf.assert_zero_future_leakage(
        mf.build_causal_feature_matrix,
        bars_m1,
        trades_col_dict,
        cutoff_utc="2024-12-31",
        perturbation_factor=10.0,
    )
    assert proof["passed"] is True
    assert proof["bit_exact_zero_drift"] is True
    assert proof["total_bars_mutated"] > 0


# ---------------------------------------------------------------------------
# 2. Exact Portfolio-State Causality (Zero Intra-Day Exit-Outcome Leakage)
# ---------------------------------------------------------------------------


def test_group_d_strictly_gates_on_exit_ts_not_entry_ts() -> None:
    bars = {"USDJPY": _make_synthetic_d1_bars(n_bars=80, seed=5)}
    t_base = int(bars["USDJPY"]["times_sec"][50])
    idx = {name: i for i, name in enumerate(mf.FEATURE_NAMES_24)}

    # Trade 0 enters at 08:00, exits at 16:00 with huge +5.0R win
    # Trade 1 enters at 10:00 (while Trade 0 is STILL OPEN!)
    # Trade 2 enters at 17:00 (AFTER Trade 0 has CLOSED at 16:00!)
    trades = [
        {
            "engine_id": "E1_USDJPY_TOKYO",
            "symbol": "USDJPY",
            "entry_ts": t_base + 8 * 3600,
            "exit_ts": t_base + 16 * 3600,
            "side": 1,
            "net_R": 5.0,
            "risk_pct": 1.0,
        },
        {
            "engine_id": "E1_USDJPY_TOKYO",
            "symbol": "USDJPY",
            "entry_ts": t_base + 10 * 3600,
            "exit_ts": t_base + 15 * 3600,
            "side": 1,
            "net_R": -1.0,
            "risk_pct": 1.0,
        },
        {
            "engine_id": "E1_USDJPY_TOKYO",
            "symbol": "USDJPY",
            "entry_ts": t_base + 17 * 3600,
            "exit_ts": t_base + 19 * 3600,
            "side": 1,
            "net_R": 0.5,
            "risk_pct": 1.0,
        },
    ]
    x = mf.build_causal_feature_matrix(bars, trades, cutoff_utc="2024-12-31")

    # At Trade 1 (10:00): Trade 0 is open (same_dir=1), NOT closed (warmup WR=0.5, avg_r=0.0, dd=0.0)
    assert x[1, idx["same_dir_concurrent_count"]] == np.float32(1.0)
    assert x[1, idx["recent_10_wr_causal"]] == np.float32(0.5)
    assert x[1, idx["recent_10_avg_r_causal"]] == np.float32(0.0)
    assert x[1, idx["rolling_dd_pct_causal"]] == np.float32(0.0)

    # At Trade 2 (17:00): BOTH Trade 1 (exit 15:00, -1R) and Trade 0 (exit 16:00, +5R) are closed!
    assert x[2, idx["same_dir_concurrent_count"]] == np.float32(0.0)
    assert math.isclose(float(x[2, idx["recent_10_wr_causal"]]), 0.5, rel_tol=1e-6)
    assert math.isclose(float(x[2, idx["recent_10_avg_r_causal"]]), 2.0, rel_tol=1e-6)
    # Equity path: 1.0 -> 0.99 (exit 15:00) -> 0.99 * 1.05 = 1.0395 (exit 16:00, new peak -> dd=0%)
    assert math.isclose(float(x[2, idx["rolling_dd_pct_causal"]]), 0.0, abs_tol=1e-5)

    # Now flip Trade 0 to -4.0R loss: Trade 1 MUST remain 0-bit identical, while Trade 2 reflects drawdown!
    trades_alt = [dict(t) for t in trades]
    trades_alt[0]["net_R"] = -4.0
    x_alt = mf.build_causal_feature_matrix(bars, trades_alt, cutoff_utc="2024-12-31")
    assert np.array_equal(x[1], x_alt[1])
    assert float(x_alt[2, idx["rolling_dd_pct_causal"]]) > 4.0


# ---------------------------------------------------------------------------
# 3. Fail-Closed Poisoned Input & Holdout 2025+ Seal Tests (Safe Under -O)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad_val", [float("nan"), float("inf"), float("-inf"), -1.0, 0.0])
def test_rejects_poisoned_ohlc_values_fail_closed(bad_val: float) -> None:
    bars, trades = _make_synthetic_dataset()
    bars["USDJPY"]["close"][10] = bad_val
    with pytest.raises(ValueError):
        mf.build_causal_feature_matrix(bars, trades, cutoff_utc="2024-12-31")


def test_rejects_bool_disguised_as_numeric_across_all_fields() -> None:
    # 1. Boolean ndarray for OHLC
    bars, trades = _make_synthetic_dataset()
    bars["USDJPY"]["open"] = np.ones(len(bars["USDJPY"]["open"]), dtype=bool)
    with pytest.raises(ValueError, match="POISONED_BOOL_INPUT"):
        mf.build_causal_feature_matrix(bars, trades, cutoff_utc="2024-12-31")

    # 2. Python list containing bool in spread
    bars2, trades2 = _make_synthetic_dataset()
    sp_list: list[Any] = list(bars2["USDJPY"]["spread_price"])
    sp_list[5] = True
    bars2["USDJPY"]["spread_price"] = sp_list
    with pytest.raises(ValueError, match="POISONED_BOOL_INPUT"):
        mf.build_causal_feature_matrix(bars2, trades2, cutoff_utc="2024-12-31")

    # 3. Boolean side in trades
    bars3, trades3 = _make_synthetic_dataset()
    trades3[0]["side"] = True
    with pytest.raises(ValueError, match="POISONED_BOOL_INPUT"):
        mf.build_causal_feature_matrix(bars3, trades3, cutoff_utc="2024-12-31")

    # 4. Boolean net_R in trades
    bars4, trades4 = _make_synthetic_dataset()
    trades4[0]["net_R"] = False
    with pytest.raises(ValueError, match="POISONED_BOOL_INPUT"):
        mf.build_causal_feature_matrix(bars4, trades4, cutoff_utc="2024-12-31")

    # 5. Boolean risk_pct in trades
    bars5, trades5 = _make_synthetic_dataset()
    trades5[0]["risk_pct"] = True
    with pytest.raises(ValueError, match="POISONED_BOOL_INPUT"):
        mf.build_causal_feature_matrix(bars5, trades5, cutoff_utc="2024-12-31")

    # 6. Boolean cutoff_utc
    bars6, trades6 = _make_synthetic_dataset()
    with pytest.raises(ValueError, match="POISONED_BOOL_INPUT"):
        mf.build_causal_feature_matrix(bars6, trades6, cutoff_utc=True)  # type: ignore[arg-type]


def test_rejects_holdout_2025_plus_dates_fail_closed() -> None:
    bars, trades = _make_synthetic_dataset()

    # 1. cutoff_utc = "2025-01-01" or "2025-01-02" must be blocked!
    for bad_cutoff in ("2025-01-01", "2025-01-02", "2025-06-15T12:00:00Z", mf.DEV_CUTOFF_SEC + 1):
        with pytest.raises(ValueError, match="HOLDOUT_CUTOFF_BREACH"):
            mf.build_causal_feature_matrix(bars, trades, cutoff_utc=bad_cutoff)

    # 2. Trade entry on 2025-01-02 must be blocked even with valid cutoff_utc="2024-12-31"!
    trades_bad = [dict(t) for t in trades]
    trades_bad[0]["entry_ts"] = "2025-01-02T10:00:00Z"
    trades_bad[0]["exit_ts"] = "2025-01-02T16:00:00Z"
    with pytest.raises(ValueError, match="HOLDOUT_TRADE_BREACH"):
        mf.build_causal_feature_matrix(bars, trades_bad, cutoff_utc="2024-12-31")

    # 3. Bar timestamp on 2025-01-02 must be blocked!
    bars_bad = {k: dict(v) for k, v in bars.items()}
    ts_bad = np.array(bars_bad["USDJPY"]["times_sec"], dtype=np.int64, copy=True)
    ts_bad[-1] = int(datetime(2025, 1, 2, tzinfo=UTC).timestamp())
    bars_bad["USDJPY"]["times_sec"] = ts_bad
    with pytest.raises(ValueError, match="HOLDOUT_BAR_BREACH"):
        mf.build_causal_feature_matrix(bars_bad, trades, cutoff_utc="2024-12-31")


def test_rejects_invalid_geometry_negative_spread_and_non_monotonic_ts() -> None:
    bars, trades = _make_synthetic_dataset()
    bars["USDJPY"]["high"][20] = bars["USDJPY"]["low"][20] - 0.5
    with pytest.raises(ValueError, match="INVALID_OHLC_GEOMETRY"):
        mf.build_causal_feature_matrix(bars, trades, cutoff_utc="2024-12-31")

    bars2, trades2 = _make_synthetic_dataset()
    bars2["USDJPY"]["spread_price"][20] = -0.001
    with pytest.raises(ValueError, match="NEGATIVE_INPUT"):
        mf.build_causal_feature_matrix(bars2, trades2, cutoff_utc="2024-12-31")

    bars3, trades3 = _make_synthetic_dataset()
    bars3["USDJPY"]["times_sec"][20] = bars3["USDJPY"]["times_sec"][19]
    with pytest.raises(ValueError, match="NON_MONOTONIC_TIMESTAMPS"):
        mf.build_causal_feature_matrix(bars3, trades3, cutoff_utc="2024-12-31")

    bars4, trades4 = _make_synthetic_dataset()
    trades4[0]["net_R"] = float("nan")
    with pytest.raises(ValueError, match="NON_FINITE_INPUT"):
        mf.build_causal_feature_matrix(bars4, trades4, cutoff_utc="2024-12-31")


# ---------------------------------------------------------------------------
# 4. Mandatory `W4-G04` Future-Perturbation Mutation Tests (+ Negative Proof)
# ---------------------------------------------------------------------------


def test_w4_g04_future_perturbation_10x_zero_bit_change() -> None:
    bars, trades = _make_synthetic_dataset()

    # Direct explicit 10x future-perturbation check on a middle trade
    sorted_entries = sorted(t["entry_ts"] for t in trades)
    t_mid = sorted_entries[len(sorted_entries) // 2]
    x_orig = mf.build_causal_feature_matrix(bars, trades, cutoff_utc="2024-12-31")
    bars_pert, n_mut = mf.perturb_bars_after_ts(bars, t_mid, factor=10.0)
    assert n_mut > 0
    x_pert = mf.build_causal_feature_matrix(bars_pert, trades, cutoff_utc="2024-12-31")

    pre_mask = np.array([t["entry_ts"] <= t_mid for t in trades], dtype=bool)
    assert bool(np.any(pre_mask))
    # 0-bit change for ALL trades at or before t_mid!
    assert np.array_equal(x_orig[pre_mask], x_pert[pre_mask])
    # Post-t_mid trades DO observe the 10x shifted prices (proving mutation was non-trivial!)
    post_mask = ~pre_mask
    assert bool(np.any(post_mask))
    assert not np.array_equal(x_orig[post_mask], x_pert[post_mask])

    # Full multi-probe `assert_zero_future_leakage` gate check
    proof = mf.assert_zero_future_leakage(
        mf.build_causal_feature_matrix,
        bars,
        trades,
        cutoff_utc="2024-12-31",
        perturbation_factor=10.0,
        max_probes=6,
    )
    assert proof["passed"] is True
    assert proof["probes_tested"] >= 4
    assert proof["bit_exact_zero_drift"] is True
    assert proof["holdout_rows_analysed"] == 0


def test_w4_g04_negative_mutation_catches_leaky_bar_and_trade_features() -> None:
    bars, trades = _make_synthetic_dataset()

    # Negative Mutation 1: deliberately leaky price feature using whole-array mean(close)
    def leaky_price_builder(
        bars_map: dict[str, Any],
        tr_list: list[dict[str, Any]],
        cutoff_utc: str = "2024-12-31",
    ) -> np.ndarray:
        x = mf.build_causal_feature_matrix(bars_map, tr_list, cutoff_utc=cutoff_utc).copy()
        global_mean = float(np.mean(bars_map["USDJPY"]["close"]))
        x[:, 0] = np.float32(global_mean)  # Leaks future prices into atr14_pct!
        return x

    with pytest.raises(ValueError, match="FUTURE_LEAKAGE_DETECTED"):
        mf.assert_zero_future_leakage(
            leaky_price_builder,
            bars,
            trades,
            cutoff_utc="2024-12-31",
            perturbation_factor=10.0,
        )

    # Negative Mutation 2: deliberately leaky same-bar close peek
    # (uses bar_ts <= t_entry instead of close_ts <= t_entry)
    def leaky_same_bar_close_builder(
        bars_map: dict[str, Any],
        tr_list: list[dict[str, Any]],
        cutoff_utc: str = "2024-12-31",
    ) -> np.ndarray:
        x = mf.build_causal_feature_matrix(bars_map, tr_list, cutoff_utc=cutoff_utc).copy()
        usdjpy = bars_map["USDJPY"]
        ts = np.asarray(usdjpy["times_sec"], dtype=np.int64)
        c = np.asarray(usdjpy["close"], dtype=np.float64)
        for i, tr in enumerate(tr_list):
            if mf.normalize_symbol(tr["symbol"]) == "USDJPY":
                # BUG: picks today's unclosed D1 bar whose close happens hours AFTER entry_ts!
                idx_same_day = int(np.searchsorted(ts, tr["entry_ts"], side="right")) - 1
                x[i, 9] = np.float32(c[idx_same_day])
        return x

    with pytest.raises(ValueError, match="FUTURE_LEAKAGE_DETECTED"):
        mf.assert_zero_future_leakage(
            leaky_same_bar_close_builder,
            bars,
            trades,
            cutoff_utc="2024-12-31",
            perturbation_factor=10.0,
        )

    # Negative Mutation 3: deliberately leaky Group D feature peeking at future trade net_R
    def leaky_future_trade_builder(
        bars_map: dict[str, Any],
        tr_list: list[dict[str, Any]],
        cutoff_utc: str = "2024-12-31",
    ) -> np.ndarray:
        x = mf.build_causal_feature_matrix(bars_map, tr_list, cutoff_utc=cutoff_utc).copy()
        future_avg_r = float(np.mean([float(t["net_R"]) for t in tr_list]))
        x[:, 22] = np.float32(future_avg_r)
        return x

    with pytest.raises(ValueError, match="FUTURE_LEAKAGE_DETECTED"):
        mf.assert_zero_future_leakage(
            leaky_future_trade_builder,
            bars,
            trades,
            cutoff_utc="2024-12-31",
            perturbation_factor=10.0,
            mutate_future_trades=True,
        )


def test_prefix_truncation_invariance_duck_df_and_vacuous_guard() -> None:
    bars, trades = _make_synthetic_dataset()
    t_mid = sorted(t["entry_ts"] for t in trades)[len(trades) // 2]
    pre_trades = [t for t in trades if t["entry_ts"] <= t_mid]

    # Truncate all bar series strictly to bars closing <= t_mid (zero future bars present)
    bars_trunc: dict[str, Any] = {}
    for sym, b in bars.items():
        keep = (b["times_sec"] + np.int64(b["bar_duration_sec"])) <= np.int64(t_mid)
        bars_trunc[sym] = {
            "times_sec": b["times_sec"][keep],
            "open": b["open"][keep],
            "high": b["high"][keep],
            "low": b["low"][keep],
            "close": b["close"][keep],
            "spread_price": b["spread_price"][keep],
            "bar_duration_sec": b["bar_duration_sec"],
        }

    x_full = mf.build_causal_feature_matrix(bars, trades, cutoff_utc="2024-12-31")
    pre_mask = np.array([t["entry_ts"] <= t_mid for t in trades], dtype=bool)
    x_trunc = mf.build_causal_feature_matrix(bars_trunc, pre_trades, cutoff_utc="2024-12-31")
    assert np.array_equal(x_full[pre_mask], x_trunc)

    # Vacuous causality check (zero future bars after the latest trade at t_mid) must fail closed!
    last_pre_trade = max(pre_trades, key=lambda t: t["entry_ts"])
    with pytest.raises(ValueError, match="VACUOUS_CAUSALITY_TEST"):
        mf.assert_zero_future_leakage(
            mf.build_causal_feature_matrix,
            bars_trunc,
            [last_pre_trade],
            cutoff_utc="2024-12-31",
        )

    # Lightweight duck-typed DataFrame works cleanly without importing pandas
    class _DuckFrame:
        def __init__(self, rows: list[dict[str, Any]]) -> None:
            self._rows = rows
            self.columns = list(rows[0].keys()) if rows else []

        def to_dict(self, orient: str = "records") -> list[dict[str, Any]]:
            if orient != "records":
                raise ValueError(orient)
            return list(self._rows)

    x_duck = mf.build_causal_feature_matrix(bars, _DuckFrame(trades), cutoff_utc="2024-12-31")
    assert np.array_equal(x_full, x_duck)


# ---------------------------------------------------------------------------
# 5. Real Local Cache Integration Proof (`PORT_7E` Dev 2018-2024, Skipped in CI)
# ---------------------------------------------------------------------------


@pytest.mark.local_cache
def test_port7e_real_dev_cache_24_features_and_w4_g04() -> None:
    bundle = mf.build_port7e_dev_feature_bundle(
        portfolio_key="PORT_7E_P28_CORE",
        cutoff_utc="2024-12-31",
        verify_sha=True,
        verify_causality=True,
    )
    x_mat = bundle["X"]
    assert x_mat.shape[0] > 2500
    assert x_mat.shape[1] == 24
    assert x_mat.dtype == np.float32
    assert bool(np.all(np.isfinite(x_mat)))
    assert bundle["holdout_rows_analysed"] == 0
    assert bundle["order_send_count"] == 0
    assert int(np.max(bundle["entry_ts"])) < mf.DEV_CUTOFF_SEC
    assert bundle["causality_proof"]["passed"] is True
    assert bundle["causality_proof"]["bit_exact_zero_drift"] is True

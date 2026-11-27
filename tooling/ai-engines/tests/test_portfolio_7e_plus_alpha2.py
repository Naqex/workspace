"""Unit, Shadow-Bug-Regression & Local-Cache Tests for Alpha #2 + PORT_7E Combination Study.

Covers:
  1. All 5 verified bug fixes in `crypto_shadow_runner.py`:
     - Bug 1: EMA warmup parity (`valid_streak >= span`, NaN/<=0 reset) matching `causal_universe.py`.
     - Bug 2: Rebalance deadband parity (`0.015`) with bit-for-bit Backtest-vs-Shadow equivalence.
     - Bug 3: 4H kline fetch `limit = 1000` (`>= 600`) eliminating ~11.5% EMA(300) seed drift.
     - Bug 4: Strict 4H bar idempotency lock (`last_4h_close_ms`) preventing repeat fee deduction on 5m polls.
     - Bug 5: Full exited-coin MTM tracking (`top15 | {BTC, ETH} | set(s2_prev_w.keys())`).
  2. Strict `-O`-safe pre-holdout date enforcement (`>= 2025-01-01` -> `ValueError`).
  3. Weekend-preserving 24/7-to-trading-day alignment, CPCV, and monthly starvation math.
  4. `@pytest.mark.local_cache` end-to-end Dev study & Law-15 Markdown report hygiene checks.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest

AI_ENGINES = Path(__file__).resolve().parents[1]
ROOT = AI_ENGINES.parents[1]
QUANT_LAB_SRC = ROOT / "projects" / "quant-trading" / "src"
for _p in (str(AI_ENGINES), str(QUANT_LAB_SRC)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from experiments.portfolio_7e_plus_alpha2_study import (  # noqa: E402
    HOLDOUT_CUTOFF_MS,
    _simulate_dual_account_hwm_cashflow_numba,
    align_24_7_returns_to_trading_days,
    compute_empirical_monthly_starvation,
    evaluate_cpcv_oos_sharpe,
    evaluate_dual_account_cashflow,
    load_dev_funding_panel_from_parquet,
    load_dev_spot_panel_from_parquet,
    run_portfolio_7e_plus_alpha2_study,
    validate_strict_pre_holdout_dates,
)
from quant_factory import crypto_shadow_runner as csr  # noqa: E402

try:
    from quant_lab.causal_universe import causal_rolling_top_n_mask  # noqa: E402
except ModuleNotFoundError:  # Older projects/quant-trading submodule pin on workspace CI
    from quant_factory.crypto_causal_universe import causal_rolling_top_n_mask  # noqa: E402

try:
    from quant_lab import F4EmaConfig, UnifiedSpotEngine  # noqa: E402
except ImportError:  # Older projects/quant-trading submodule pin on workspace CI
    F4EmaConfig = None  # type: ignore[assignment,misc]
    UnifiedSpotEngine = None  # type: ignore[assignment,misc]

REPORT_MD_PATH = ROOT / "planning" / "research" / "ALPHA2-UNIFIED-ENGINE-AND-PORTFOLIO-COMBINATION-20261127.md"


# ==============================================================================
# 1. ALL 5 VERIFIED BUG FIXES IN `crypto_shadow_runner.py` (CI-SAFE, ZERO NETWORK)
# ==============================================================================


def test_shadow_bug1_ema_warmup_and_nan_reset_parity() -> None:
    prices = np.linspace(100.0, 220.0, 360, dtype=np.float64)
    ema = csr._causal_ema_1d(prices, 300)
    assert np.isnan(ema[:299]).all()
    assert np.isfinite(ema[299:]).all()

    # Gap at index 310 must invalidate EMA(300) until 300 consecutive post-gap bars arrive
    gapped = prices.copy()
    gapped[310] = np.nan
    ema_g = csr._causal_ema_1d(gapped, 300)
    assert np.isnan(ema_g[310:]).all()

    # Shadow live weights must return flat `{}` when BTC has a recent NaN gap (< 300 streak)
    res_gap = csr.compute_f4_4h_ema_live_weights({"BTCUSDT": gapped, "ETHUSDT": prices}, ["BTCUSDT", "ETHUSDT"])
    assert res_gap["btc_regime_bull"] is False
    assert res_gap["weights"] == {}
    assert res_gap["reason"] == "INSUFFICIENT_BTC_BARS"


def test_shadow_bug2_deadband_and_backtest_step_parity() -> None:
    rng = np.random.default_rng(20261127)
    n_bars = 220
    idx = pd.date_range("2024-01-01", periods=n_bars, freq="4h", tz="UTC")
    cols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
    rets = rng.normal(0.0008, 0.015, size=(n_bars, len(cols)))
    rets[:, 0] += 0.0015
    close_df = pd.DataFrame(100.0 * np.cumprod(1.0 + rets, axis=0), index=idx, columns=cols)
    qv_df = pd.DataFrame(rng.uniform(1e7, 1e8, size=(n_bars, len(cols))), index=idx, columns=cols)
    mask_df = causal_rolling_top_n_mask(qv_df, close_df, lookback_bars=20, top_n=3)

    # Confirm deadband holds small non-zero perturbations unchanged in Shadow helper
    w_hold = csr.apply_deadband_step(
        {"BTCUSDT": 0.255, "ETHUSDT": 0.200},
        {"BTCUSDT": 0.250, "ETHUSDT": 0.200},
        deadband=0.015,
    )
    assert w_hold == {"BTCUSDT": 0.250, "ETHUSDT": 0.200}

    if UnifiedSpotEngine is None or F4EmaConfig is None:
        # Older projects/quant-trading submodule pin on workspace CI: verify fallback step parity directly
        cfg_fb = csr.F4EmaConfig(fast_span=12, slow_span=40, btc_fast=20, btc_slow=80, vol_window=40, deadband=0.015)
        closed_map = {c: close_df[c].to_numpy(dtype=np.float64) for c in cols}
        elig = [c for c in cols if bool(mask_df[c].iloc[-1])]
        s1 = csr.compute_f4_ema_step(closed_map, elig, config=cfg_fb, prev_weights={})
        s2 = csr.compute_f4_ema_step(closed_map, elig, config=cfg_fb, prev_weights=s1["weights"])
        assert s2["weights"] == s1["weights"]
        assert 0.0 <= float(s2["gross_exposure"]) <= 1.0 + 1e-12
        return

    cfg = F4EmaConfig(fast_span=12, slow_span=40, btc_fast=20, btc_slow=80, vol_window=40, deadband=0.015)
    engine = UnifiedSpotEngine(cfg)
    w_bt = engine.build_f4_weights(close_df, mask_df)

    # Verify full backtest-vs-shadow step-by-step parity with deadband active
    prev_w: dict[str, float] = {}
    for t in range(n_bars):
        closed_map = {c: close_df[c].iloc[: t + 1].to_numpy(dtype=np.float64) for c in cols}
        elig = [c for c in cols if bool(mask_df[c].iloc[t])]
        step = engine.compute_f4_step(closed_map, elig, prev_weights=prev_w)
        for c in cols:
            assert float(step["weights"].get(c, 0.0)) == pytest.approx(float(w_bt[c].iloc[t]), abs=1e-12)
        prev_w = step["weights"]


def test_shadow_bugs_3_4_5_end_to_end_mocked_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify Bug #3 (limit >= 600 -> 1000), Bug #4 (4H idempotency), and Bug #5 (dropped Top-15 exit MTM)."""
    assert csr.SHADOW_4H_KLINE_LIMIT >= 600
    assert csr.SHADOW_4H_KLINE_LIMIT == 1000

    # Bug #3 fail-closed guard against low kline_limit_4h
    with pytest.raises(ValueError, match=">= 600"):
        csr.collect_live_shadow_snapshot(
            state_path=tmp_path / "s.json",
            log_path=tmp_path / "l.jsonl",
            latest_path=tmp_path / "latest.json",
            kline_limit_4h=325,
        )

    # Bug #5 watch-list builder always includes previously held coins
    watch = csr.build_shadow_watch_symbols(["BTCUSDT", "ETHUSDT"], {"DROPPEDUSDT": 0.35})
    assert watch == ["BTCUSDT", "DROPPEDUSDT", "ETHUSDT"]

    # Deterministic mocked Binance public responses across 3 polls:
    #   Poll 1 (bar T1): DROPPEDUSDT in top15 -> enters positions (with limit=1000 verified!)
    #   Poll 2 (SAME bar T1, 5m later): top15 changes & mids move -> ZERO turnover/fees (idempotency lock!)
    #   Poll 3 (NEW bar T2 > T1): DROPPEDUSDT dropped out of top15 & jumped +20% -> exact exit MTM captured!
    state_box: dict[str, Any] = {
        "top15": ["BTCUSDT", "ETHUSDT", "DROPPEDUSDT"],
        "close_ms": 1_704_081_599_999,
        "mids": {"BTCUSDT": 60_000.0, "ETHUSDT": 3_000.0, "DROPPEDUSDT": 100.0, "NEWCOINUSDT": 50.0},
        "kline_limits_seen": [],
        "depth_syms_seen": [],
    }

    rng = np.random.default_rng(7)
    n_kl = 1000
    t_arr = np.arange(n_kl, dtype=np.float64)
    base_series = {
        "BTCUSDT": 40_000.0 * np.exp(0.0005 * t_arr + rng.normal(0.0, 0.003, size=n_kl)),
        "ETHUSDT": 2_000.0 * np.exp(0.0006 * t_arr + rng.normal(0.0, 0.004, size=n_kl)),
        "DROPPEDUSDT": 80.0 * np.exp(0.0007 * t_arr + rng.normal(0.0, 0.004, size=n_kl)),
        "NEWCOINUSDT": 40.0 * np.exp(0.0006 * t_arr + rng.normal(0.0, 0.004, size=n_kl)),
    }

    def fake_select_top15(_client: Any, universe: Any = None) -> list[str]:
        return list(state_box["top15"])

    def fake_fetch_json(_client: Any, url: str, params: dict[str, Any] | None = None) -> Any:
        params = params or {}
        if url.endswith("/api/v3/klines"):
            sym = str(params["symbol"])
            lim = int(params["limit"])
            state_box["kline_limits_seen"].append(lim)
            closes = base_series[sym][-lim:]
            close_ms = int(state_box["close_ms"])
            # Last row is forming candle (dropped by `kl[:-1]`); second-to-last carries `close_ms`
            rows = []
            for i, c in enumerate(closes):
                row_close_ms = close_ms - (len(closes) - 2 - i) * 4 * 3_600_000
                rows.append([0, str(c), str(c * 1.01), str(c * 0.99), str(c), "100", row_close_ms, "1000000", 10])
            return rows
        if url.endswith("/api/v3/depth"):
            sym = str(params["symbol"])
            state_box["depth_syms_seen"].append(sym)
            mid = float(state_box["mids"][sym])
            bid = mid * 0.9999
            ask = mid * 1.0001
            return {"bids": [[str(bid), "100000"]], "asks": [[str(ask), "100000"]]}
        if url.endswith("/fapi/v1/premiumIndex"):
            sym = str(params["symbol"])
            mid = float(state_box["mids"][sym])
            return {"markPrice": str(mid), "indexPrice": str(mid), "lastFundingRate": "0.0001"}
        if url.endswith("/fapi/v1/fundingRate"):
            return [{"fundingRate": "0.0001"} for _ in range(24)]
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(csr, "select_live_top15_causal", fake_select_top15)
    monkeypatch.setattr(csr, "_fetch_json", fake_fetch_json)

    st_p = tmp_path / "shadow_state.json"
    lg_p = tmp_path / "shadow_log.jsonl"
    lt_p = tmp_path / "shadow_latest.json"

    # Poll 1: initial 4H bar T1
    r1 = csr.collect_live_shadow_snapshot(state_path=st_p, log_path=lg_p, latest_path=lt_p)
    assert all(lim == 1000 for lim in state_box["kline_limits_seen"])
    assert r1["sleeve2_f4_4h_ema"]["bar_rebalanced"] is True
    assert r1["sleeve2_f4_4h_ema"]["cycle_turnover"] > 0.0
    assert "DROPPEDUSDT" in r1["sleeve2_f4_4h_ema"]["weights"]
    w1_locked = dict(r1["sleeve2_f4_4h_ema"]["weights"])
    eq1 = float(json.loads(st_p.read_text(encoding="utf-8"))["s2_paper_equity_usd"])

    # Poll 2: 5 minutes later inside the SAME 4H bar T1 (top15 changes & BTC ticks +1%)
    state_box["top15"] = ["BTCUSDT", "ETHUSDT", "NEWCOINUSDT"]
    state_box["mids"]["BTCUSDT"] = 60_600.0  # +1%
    r2 = csr.collect_live_shadow_snapshot(state_path=st_p, log_path=lg_p, latest_path=lt_p)
    assert r2["sleeve2_f4_4h_ema"]["bar_rebalanced"] is False
    assert r2["sleeve2_f4_4h_ema"]["cycle_turnover"] == 0.0
    assert r2["sleeve2_f4_4h_ema"]["cycle_live_tca_bps"] == 0.0
    assert r2["sleeve2_f4_4h_ema"]["weights"] == w1_locked
    eq2 = float(json.loads(st_p.read_text(encoding="utf-8"))["s2_paper_equity_usd"])
    expected_eq2 = eq1 * (1.0 + w1_locked["BTCUSDT"] * 0.01)
    assert eq2 == pytest.approx(expected_eq2, abs=1e-2)

    # Poll 3: NEW 4H bar T2 > T1 — DROPPEDUSDT is OUT of top15 and surged +20% (100 -> 120)!
    state_box["depth_syms_seen"].clear()
    state_box["close_ms"] += 4 * 3_600_000
    state_box["mids"]["DROPPEDUSDT"] = 120.0  # +20% exit gain!
    r3 = csr.collect_live_shadow_snapshot(state_path=st_p, log_path=lg_p, latest_path=lt_p)
    assert "DROPPEDUSDT" in state_box["depth_syms_seen"]
    assert r3["sleeve2_f4_4h_ema"]["bar_rebalanced"] is True
    assert r3["sleeve2_f4_4h_ema"]["missing_exit_mids"] == []
    assert "DROPPEDUSDT" not in r3["sleeve2_f4_4h_ema"]["weights"]
    eq3 = float(json.loads(st_p.read_text(encoding="utf-8"))["s2_paper_equity_usd"])
    # Must capture the +20% * w_dropped exit MTM gain (minus exit/entry TCA)!
    gross_exit_gain = w1_locked["DROPPEDUSDT"] * 0.20
    tca_cost = r3["sleeve2_f4_4h_ema"]["cycle_turnover"] * (r3["sleeve2_f4_4h_ema"]["cycle_live_tca_bps"] / 10_000.0)
    assert eq3 == pytest.approx(eq2 * (1.0 + gross_exit_gain - tca_cost), abs=0.25)


def test_shadow_runner_bool_limit_empty_orderbook_and_mid_carry_forward(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify bool `kline_limit_4h` rejection, strict JSON on empty L2 book, and held-mid carry-forward."""
    with pytest.raises(ValueError, match=">= 600"):
        csr.collect_live_shadow_snapshot(
            state_path=tmp_path / "s.json",
            log_path=tmp_path / "l.jsonl",
            latest_path=tmp_path / "latest.json",
            kline_limit_4h=True,  # type: ignore[arg-type]
        )

    rng = np.random.default_rng(19)
    n_kl = 1000
    t_arr = np.arange(n_kl, dtype=np.float64)
    series = {
        "BTCUSDT": 50_000.0 * np.exp(0.0005 * t_arr + rng.normal(0.0, 0.003, size=n_kl)),
        "ETHUSDT": 2_500.0 * np.exp(0.0006 * t_arr + rng.normal(0.0, 0.004, size=n_kl)),
    }
    box: dict[str, Any] = {
        "close_ms": 1_704_081_599_999,
        "empty_book_syms": set(),
    }

    def fake_top15(_client: Any, universe: Any = None) -> list[str]:
        return ["BTCUSDT", "ETHUSDT"]

    def fake_fetch(_client: Any, url: str, params: dict[str, Any] | None = None) -> Any:
        params = params or {}
        if url.endswith("/api/v3/klines"):
            sym = str(params["symbol"])
            lim = int(params["limit"])
            closes = series[sym][-lim:]
            close_ms = int(box["close_ms"])
            return [
                [
                    0,
                    str(c),
                    str(c * 1.01),
                    str(c * 0.99),
                    str(c),
                    "100",
                    close_ms - (len(closes) - 2 - i) * 14_400_000,
                    "1e6",
                    10,
                ]
                for i, c in enumerate(closes)
            ]
        if url.endswith("/api/v3/depth"):
            sym = str(params["symbol"])
            if sym in box["empty_book_syms"]:
                return {"bids": [], "asks": []}
            mid = 60_000.0 if sym == "BTCUSDT" else 3_000.0
            return {"bids": [[str(mid * 0.9999), "100000"]], "asks": [[str(mid * 1.0001), "100000"]]}
        if url.endswith("/fapi/v1/premiumIndex"):
            mid = 60_000.0 if params.get("symbol") == "BTCUSDT" else 3_000.0
            return {"markPrice": str(mid), "indexPrice": str(mid), "lastFundingRate": "0.0001"}
        if url.endswith("/fapi/v1/fundingRate"):
            return [{"fundingRate": "0.0001"} for _ in range(24)]
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(csr, "select_live_top15_causal", fake_top15)
    monkeypatch.setattr(csr, "_fetch_json", fake_fetch)

    st_p = tmp_path / "shadow_state.json"
    lg_p = tmp_path / "shadow_log.jsonl"
    lt_p = tmp_path / "shadow_latest.json"

    r1 = csr.collect_live_shadow_snapshot(state_path=st_p, log_path=lg_p, latest_path=lt_p)
    assert "BTCUSDT" in r1["sleeve2_f4_4h_ema"]["weights"]

    # Poll 2: transient empty orderbook for BTCUSDT on the SAME 4H bar -> valid strict JSON & carried mid!
    box["empty_book_syms"] = {"BTCUSDT"}
    r2 = csr.collect_live_shadow_snapshot(state_path=st_p, log_path=lg_p, latest_path=lt_p)
    raw_latest = lt_p.read_text(encoding="utf-8")
    assert "NaN" not in raw_latest and "Infinity" not in raw_latest
    parsed_latest = json.loads(raw_latest)
    assert parsed_latest["orderbook_depth_top15"]["BTCUSDT"]["spread_bps"] is None
    assert parsed_latest["orderbook_depth_top15"]["BTCUSDT"]["mid"] is None
    assert "BTCUSDT" in r2["sleeve2_f4_4h_ema"]["missing_exit_mids"]
    saved_state = json.loads(st_p.read_text(encoding="utf-8"))
    assert saved_state["s2_mids"]["BTCUSDT"] == pytest.approx(60_000.0)


def test_dual_account_gross_payout_threshold_and_amber_red_brakes() -> None:
    """Verify gross >= 50 USD payout classification (no 1.5% rail-fee dry bug) and Amber/Red DD brakes."""
    # Exact gross-vs-net threshold boundary: prof=63 USD -> gross share=50.40 >= 50.0, net_out=49.644 < 50.0!
    idx = np.arange(21, dtype=np.int64).reshape(1, 21)
    n_fn = np.zeros(21, dtype=np.float64)
    n_fn[9] = 63.0
    d_fn = np.zeros(21, dtype=np.float64)
    a2_zero = np.zeros(21, dtype=np.float64)

    tot_m, f_dry, d_dry, _f_str, _d_str, cash24 = _simulate_dual_account_hwm_cashflow_numba(
        idx, n_fn, d_fn, n_fn, d_fn, n_fn, d_fn, a2_zero, 10_000.0, 10_000.0, 50.0, 0.035, 0.060
    )
    assert int(tot_m[0]) == 1
    assert int(f_dry[0]) == 0
    assert int(d_dry[0]) == 0
    assert float(cash24[0]) == pytest.approx(50.40 * (1.0 - 0.015), abs=1e-9)

    summary = evaluate_dual_account_cashflow(idx, n_fn, d_fn, a2_zero)
    assert summary["ftmo_only_dry_months_pct"] == 0.0
    assert summary["dual_account_dry_months_pct"] == 0.0
    assert summary["dual_mean_cash_24m_usd"] == pytest.approx(49.64, abs=0.01)

    # Verify Amber (-3.5%) and Red (-6.0%) DD brake array selection matches C10_NEWS_ON
    idx_br = np.arange(21, dtype=np.int64).reshape(1, 21)
    n_fn_b = np.zeros(21, dtype=np.float64)
    d_fn_b = np.zeros(21, dtype=np.float64)
    n_amb_b = np.zeros(21, dtype=np.float64)
    d_amb_b = np.zeros(21, dtype=np.float64)
    n_red_b = np.zeros(21, dtype=np.float64)
    d_red_b = np.zeros(21, dtype=np.float64)
    # Day 0: -200 (bal=9800, -2%); Day 1: -200 (bal=9600, -4% <= -3.5% Amber!)
    n_fn_b[0], d_fn_b[0] = -200.0, 200.0
    n_fn_b[1], d_fn_b[1] = -200.0, 200.0
    # Day 2 in Amber: loses -250 -> bal=9350 (-6.5% <= -6.0% Red!)
    n_amb_b[2], d_amb_b[2] = -250.0, 250.0
    # Day 3 in Red: recovers +800 -> bal=10150 (cycle ends at day 9 with +150 -> share 120 >= 50!)
    n_red_b[3] = 800.0
    # If Amber/Red arrays were ignored, day 2 & day 3 would stay 0 -> bal=9600 -> dry month (cash=0)!
    res_br = evaluate_dual_account_cashflow(
        idx_br,
        n_fn_b,
        d_fn_b,
        a2_zero,
        n_amb=n_amb_b,
        d_amb=d_amb_b,
        n_red=n_red_b,
        d_red=d_red_b,
        amber_dd=0.035,
        red_dd=0.060,
    )
    assert res_br["ftmo_only_dry_months_pct"] == 0.0
    assert res_br["dual_mean_cash_24m_usd"] == pytest.approx(150.0 * 0.80 * 0.985, abs=0.02)


# ==============================================================================
# 2. HOLDOUT GUARD (-O SAFE) & STATISTICAL HELPERS (CI-SAFE)
# ==============================================================================


def test_study_holdout_guard_is_python_dash_o_safe() -> None:
    assert validate_strict_pre_holdout_dates(["2020-01-01", "2024-12-31"], context="unit") == 0
    with pytest.raises(ValueError, match="HOLDOUT_LOCK_VIOLATION"):
        validate_strict_pre_holdout_dates(["2024-12-31", "2025-01-01"], context="unit")

    for bad_cutoff in (HOLDOUT_CUTOFF_MS + 86_400_000, HOLDOUT_CUTOFF_MS + 1, 0, -1, True, float("inf")):
        with pytest.raises(ValueError, match="HOLDOUT_LOCK_VIOLATION"):
            load_dev_spot_panel_from_parquet(
                "4h",
                symbols=("BTCUSDT",),
                cache_dir=ROOT / ".runtime" / "crypto-spot-cache",
                cutoff_ms=bad_cutoff,  # type: ignore[arg-type]
            )
        with pytest.raises(ValueError, match="HOLDOUT_LOCK_VIOLATION"):
            load_dev_funding_panel_from_parquet(
                symbols=("BTCUSDT",),
                cutoff_ms=bad_cutoff,  # type: ignore[arg-type]
            )

    code = (
        "import sys; sys.path.insert(0, 'tooling/ai-engines')\n"
        "from experiments.portfolio_7e_plus_alpha2_study import validate_strict_pre_holdout_dates\n"
        "try:\n"
        "    validate_strict_pre_holdout_dates(['2025-01-01'], context='dash_o')\n"
        "except ValueError:\n"
        "    raise SystemExit(0)\n"
        "raise SystemExit(99)\n"
    )
    proc = subprocess.run([sys.executable, "-O", "-c", code], cwd=str(ROOT), check=False, capture_output=True)
    assert proc.returncode == 0, f"Holdout guard bypassed under python -O: {proc.stderr.decode()}"


def test_weekend_compounding_cpcv_and_monthly_starvation_helpers() -> None:
    # Friday -> Monday compounds Sat + Sun + Mon without dropping weekend returns
    tdays = ["2024-01-05", "2024-01-08"]
    crypto = {"2024-01-05": 0.01, "2024-01-06": 0.02, "2024-01-07": 0.03, "2024-01-08": -0.01}
    ov_d, al = align_24_7_returns_to_trading_days(tdays, crypto)
    assert ov_d == tdays
    assert al[0] == pytest.approx(0.01, abs=1e-12)
    assert al[1] == pytest.approx((1.02 * 1.03 * 0.99) - 1.0, abs=1e-12)

    # CPCV C(6,2)=15 splits
    rng = np.random.default_rng(11)
    mat = rng.normal(0.001, 0.01, size=(240, 4))
    cpcv = evaluate_cpcv_oos_sharpe(
        mat, ["A", "B", "C", "D"], n_groups=6, k_test_groups=2, purge_bars=5, embargo_bars=5
    )
    assert cpcv["n_splits"] == 15
    assert set(cpcv["per_candidate"].keys()) == {"A", "B", "C", "D"}

    # Empirical monthly starvation
    dates = ["2024-01-15", "2024-02-15", "2024-03-15", "2024-04-15"]
    rets = np.array([0.02, -0.01, 0.001, 0.03], dtype=np.float64)
    st = compute_empirical_monthly_starvation(dates, rets, min_month_return_frac=0.005)
    assert st["n_months"] == 4
    assert st["pct_le_zero"] == pytest.approx(25.0)
    assert st["pct_starved"] == pytest.approx(50.0)
    assert st["max_dry_streak"] == 2


# ==============================================================================
# 3. LOCAL-CACHE INTEGRATION & RESEARCH REPORT HYGIENE TESTS
# ==============================================================================


@pytest.mark.local_cache
def test_local_cache_dev_slicing_and_portfolio_7e_plus_alpha2_study() -> None:
    p4h = load_dev_spot_panel_from_parquet(
        "4h",
        symbols=("BTCUSDT", "ETHUSDT"),
        cache_dir=ROOT / ".runtime" / "crypto-spot-cache",
    )
    assert max(p4h["dates"]) <= "2024-12-31"
    assert p4h["holdout_rows_analysed"] == 0

    pfund = load_dev_funding_panel_from_parquet(symbols=("BTCUSDT", "ETHUSDT"))
    assert max(pfund["dates"]) <= "2024-12-31"
    assert pfund["holdout_rows_analysed"] == 0

    res = run_portfolio_7e_plus_alpha2_study(n_mc_paths=500, seed=20261126)
    assert res["holdout_rows_analysed"] == 0
    assert res["order_send_count"] == 0
    assert res["m_total_candidates"] == 8
    assert res["anti_overfit_portfolio_suite"]["cpcv"]["n_splits"] == 15
    assert 0.0 <= res["anti_overfit_portfolio_suite"]["pbo_cscv"]["pbo"] <= 1.0

    # Verify orthogonality (|r| < 0.15) and meaningful starved-payout-month reduction (< 35% dual-account!)
    primary = res["primary_alpha2_selected"]
    assert primary == "A2_CARRY_BTC_ETH_2X"
    assert res["alpha2_candidates"][primary]["abs_corr_vs_port7e"] < 0.15
    assert res["alpha2_candidates"][primary]["dsr_empirical_within_family"] >= 0.50
    base_dry = res["portfolio_combinations"]["BASE_PORT_7E_ONLY_2020_2024"]["ftmo_10k_c10_mc"]["funded_dry_months_pct"]
    dual_dry = res["portfolio_combinations"]["COMBO_7E_PLUS_SPOT_AND_CARRY_DUAL"]["ftmo_10k_c10_mc"][
        "funded_dry_months_pct"
    ]
    assert dual_dry < base_dry
    dual_carry = res["dual_account_cashflow_mc"]["DUAL_10K_FTMO_PLUS_10K_CEX_CARRY"]
    dual_comp = res["dual_account_cashflow_mc"]["DUAL_10K_FTMO_PLUS_10K_CEX_COMPOSITE"]
    assert dual_carry["dual_account_dry_months_pct"] < 35.0
    assert dual_comp["dual_account_dry_months_pct"] < 35.0


@pytest.mark.local_cache
def test_alpha2_markdown_report_hygiene_and_law15_scorecard() -> None:
    assert REPORT_MD_PATH.exists(), f"Missing report: {REPORT_MD_PATH}"
    raw_bytes = REPORT_MD_PATH.read_bytes()
    assert b"\r" not in raw_bytes, "CRLF detected; report must be LF-only."
    text = raw_bytes.decode("utf-8")
    assert text.startswith("---\n"), "Missing YAML frontmatter."
    assert REPORT_MD_PATH.stat().st_size < 900_000

    # Zero bare `$` in prose
    prose = re.sub(r"```.*?```", "", text, flags=re.S)
    assert "$" not in prose, "Bare '$' found in Markdown prose."

    # Mandatory Law-15 vertical dots & Dev/Holdout evidence markings
    for token in ("🔴", "🟡", "🟢", "🏆", "holdout_rows_analysed", "2024-12-31"):
        assert token in text, f"Missing required marker {token!r} in report."

    # Zero broken local relative Markdown links
    for _lbl, tgt in re.findall(r"\[([^\]]+)\]\(([^)]+)\)", text):
        if tgt.startswith(("http://", "https://", "mailto:", "#")):
            continue
        clean = tgt.split("#", 1)[0]
        if not clean:
            continue
        resolved = (REPORT_MD_PATH.parent / clean).resolve()
        assert resolved.exists(), f"Broken relative link {tgt!r} -> {resolved}"

"""Deterministic Unit & Hygiene Tests for Wave 2 Cycle 0 & Cycle 1 Crypto Labs.

Covers:
  - C0.3b: `crypto_shadow_runner.py` (L2 orderbook slippage, closed-bar F4_4H_EMA, Carry hysteresis, live receipt)
  - C1.1 : `crypto_1h_intraday_lab.py` (strict anti-lookahead on 1H & 15m strategies, spot bounds, cost monotonicity)
  - C1.2 : `crypto_statarb_pairs_lab.py` (strict anti-lookahead on all 4 market-neutral families, exact dollar
           neutrality, gross <= 1x cap, 2-leg friction & 8h funding cashflow sign accounting)
  - Artifacts & Governance: Holdout 2025+ seal, `< 900 KB` anti-bloat, YAML frontmatter, zero bare `$`,
    zero broken local links, and `naqex-sleeve-daily-returns-v1` schema integrity.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys

import numpy as np
import pytest

AI_ENGINES = Path(__file__).resolve().parents[1]
ROOT = AI_ENGINES.parents[1]
if str(AI_ENGINES) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES))

from quant_factory.crypto_causal_universe import causal_rolling_top_n_mask, simulate_spot_backtest
from quant_factory.crypto_shadow_runner import (
    DEFAULT_LATEST_PATH,
    compute_carry_btc_eth_live_weights,
    compute_f4_4h_ema_live_weights,
    compute_orderbook_slippage_bps,
)
from quant_factory.crypto_1h_intraday_lab import (
    LAB1_CACHE_DIR,
    LAB1_RETURNS_PATH,
    build_15m_strategies,
    build_1h_strategies,
)
from quant_factory.crypto_statarb_pairs_lab import (
    LAB2_RETURNS_PATH,
    LAB2_SUMMARY_PATH,
    simulate_ls_perp_backtest,
    strat_funding_dislocation_ls,
    strat_mkt_neutral_vol_mom,
    strat_rolling_coint_pairs,
    strat_sector_neutral_residual_rev,
)


def _make_synthetic_panel(
    n_t: int,
    symbols: list[str],
    step_ms: int,
    seed: int = 42,
) -> dict:
    rng = np.random.default_rng(seed)
    n_k = len(symbols)
    start_ms = 1_704_067_200_000  # 2024-01-01T00:00:00Z
    ts = start_ms + np.arange(n_t, dtype=np.int64) * step_ms
    # Correlated market factor + idiosyncratic returns so cointegration & sectors behave realistically
    mkt = rng.normal(0.0002, 0.008, size=(n_t, 1))
    idio = rng.normal(0.0, 0.010, size=(n_t, n_k))
    log_r = 0.7 * mkt + idio
    close = 100.0 * np.exp(np.cumsum(log_r, axis=0))
    high = close * (1.0 + np.abs(rng.normal(0.003, 0.002, size=(n_t, n_k))))
    low = close * (1.0 - np.abs(rng.normal(0.003, 0.002, size=(n_t, n_k))))
    qvol = np.exp(rng.normal(16.0, 0.6, size=(n_t, n_k)))
    return {
        "symbols": symbols,
        "timestamps_ms": ts,
        "close": close,
        "high": high,
        "low": low,
        "quote_volume": qvol,
    }


# ==============================================================================
# C0.3b: Shadow Runner Unit Tests
# ==============================================================================

def test_shadow_orderbook_slippage_exact_vwap() -> None:
    bids = [["99.90", "100.0"], ["99.80", "500.0"]]
    asks = [["100.10", "100.0"], ["100.20", "500.0"]]
    # Mid = 100.00; spread = 20 bps; 10k USD fits inside L1 (~100.10*100 = 10,010 USD)
    res_10k = compute_orderbook_slippage_bps(bids, asks, 10_000.0)
    assert res_10k["depth_ok"] is True
    assert abs(res_10k["spread_bps"] - 20.0) < 1e-3
    assert abs(res_10k["buy_slip_bps"] - 10.0) < 1e-2

    # 30k USD walks into L2 -> higher buy slippage than 10k USD
    res_30k = compute_orderbook_slippage_bps(bids, asks, 30_000.0)
    assert res_30k["depth_ok"] is True
    assert res_30k["buy_slip_bps"] > res_10k["buy_slip_bps"]

    # 500k USD exhausts book -> depth_ok False
    res_huge = compute_orderbook_slippage_bps(bids, asks, 500_000.0)
    assert res_huge["depth_ok"] is False


def test_shadow_f4_4h_ema_regime_and_bounds() -> None:
    t = np.arange(350, dtype=np.float64)
    # Bear BTC -> all weights must be 0
    bear_closes = {
        "BTCUSDT": 100_000.0 * np.exp(-0.002 * t),
        "ETHUSDT": 3_000.0 * np.exp(0.002 * t),
    }
    res_bear = compute_f4_4h_ema_live_weights(bear_closes, ["BTCUSDT", "ETHUSDT"])
    assert res_bear["btc_regime_bull"] is False
    assert res_bear["gross_exposure"] == 0.0
    assert res_bear["weights"] == {}

    # Bull BTC + trending ETH with realistic noise -> positive capped weights
    rng = np.random.default_rng(7)
    bull_closes = {
        "BTCUSDT": 60_000.0 * np.exp(0.0015 * t + rng.normal(0.0, 0.005, size=len(t))),
        "ETHUSDT": 2_500.0 * np.exp(0.0020 * t + rng.normal(0.0, 0.006, size=len(t))),
    }
    res_bull = compute_f4_4h_ema_live_weights(bull_closes, ["BTCUSDT", "ETHUSDT"])
    assert res_bull["btc_regime_bull"] is True
    assert 0.0 < res_bull["gross_exposure"] <= 1.0 + 1e-9
    assert all(0.0 < w <= 1.0 for w in res_bull["weights"].values())


def test_shadow_carry_hysteresis_and_buffer() -> None:
    # +0.0001 per 8h = +10.95% annualized -> enters ON at 0.25 equity per coin (2x buffer = 50% total)
    hi = [0.0001] * 21
    mid = [0.000015] * 21  # ~1.64% ann: between 0% exit and 3% enter
    neg = [-0.00005] * 21
    r1 = compute_carry_btc_eth_live_weights({"BTCUSDT": hi, "ETHUSDT": mid}, prev_state={"BTCUSDT": False, "ETHUSDT": False})
    assert r1["state"]["BTCUSDT"] is True
    assert r1["state"]["ETHUSDT"] is False
    assert r1["notional_weights_of_equity"] == {"BTCUSDT": 0.25}
    assert r1["equity_buffer_mult"] == 2.0

    # Hysteresis: BTC at mid stays ON; ETH still OFF
    r2 = compute_carry_btc_eth_live_weights({"BTCUSDT": mid, "ETHUSDT": mid}, prev_state=r1["state"])
    assert r2["state"]["BTCUSDT"] is True
    assert r2["state"]["ETHUSDT"] is False

    # Negative funding -> turns OFF cleanly
    r3 = compute_carry_btc_eth_live_weights({"BTCUSDT": neg, "ETHUSDT": neg}, prev_state=r2["state"])
    assert r3["state"] == {"BTCUSDT": False, "ETHUSDT": False}
    assert r3["notional_weights_of_equity"] == {}


# ==============================================================================
# C1.1: Lab #1 1H & 15m Intraday Causality & Spot Invariants
# ==============================================================================

def test_lab1_1h_and_15m_zero_lookahead_and_spot_bounds() -> None:
    syms = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT"]
    p1h = _make_synthetic_panel(950, syms, 3_600_000, seed=101)
    top15 = causal_rolling_top_n_mask(p1h["quote_volume"], p1h["close"], lookback_bars=120, top_n=4)
    strats_a = build_1h_strategies(p1h, top15)

    # Mutate all future data strictly after cut = 840
    cut = 840
    p1h_mut = {k: (v.copy() if isinstance(v, np.ndarray) else list(v)) for k, v in p1h.items()}
    p1h_mut["close"][cut + 1 :] *= 3.7
    p1h_mut["high"][cut + 1 :] *= 4.1
    p1h_mut["low"][cut + 1 :] *= 0.25
    p1h_mut["quote_volume"][cut + 1 :] *= 0.01
    top15_mut = causal_rolling_top_n_mask(p1h_mut["quote_volume"], p1h_mut["close"], lookback_bars=120, top_n=4)
    strats_b = build_1h_strategies(p1h_mut, top15_mut)

    assert len(strats_a) == 10
    for name in strats_a:
        wa = strats_a[name]["w"]
        wb = strats_b[name]["w"]
        assert np.allclose(wa[: cut + 1], wb[: cut + 1], atol=0.0, rtol=0.0), f"Look-ahead leak in {name}"
        assert float(np.min(wa)) >= -1e-12
        assert float(np.max(np.sum(wa, axis=1))) <= 1.0 + 1e-9

        # Cost monotonicity: 2x costs <= 1x costs when active
        s1 = simulate_spot_backtest(p1h["close"], wa, cost_bps_oneway=15.0)
        s2 = simulate_spot_backtest(p1h["close"], wa, cost_bps_oneway=30.0)
        assert float(np.sum(s2["net_returns"])) <= float(np.sum(s1["net_returns"])) + 1e-12

    # 15m strategies causality + spot bounds
    p15 = _make_synthetic_panel(800, syms, 15 * 60_000, seed=202)
    s15_a = build_15m_strategies(p15)
    cut15 = 700
    p15_mut = {k: (v.copy() if isinstance(v, np.ndarray) else list(v)) for k, v in p15.items()}
    p15_mut["close"][cut15 + 1 :] *= 2.5
    p15_mut["high"][cut15 + 1 :] *= 3.0
    p15_mut["low"][cut15 + 1 :] *= 0.4
    p15_mut["quote_volume"][cut15 + 1 :] *= 20.0
    s15_b = build_15m_strategies(p15_mut)

    assert len(s15_a) == 2
    for name in s15_a:
        wa, wb = s15_a[name]["w"], s15_b[name]["w"]
        assert np.allclose(wa[: cut15 + 1], wb[: cut15 + 1], atol=0.0, rtol=0.0), f"Look-ahead leak in {name}"
        assert float(np.min(wa)) >= -1e-12
        assert float(np.max(np.sum(wa, axis=1))) <= 1.0 + 1e-9


# ==============================================================================
# C1.2: Lab #2 Stat-Arb, Market-Neutrality, Causality & 2-Leg Funding Accounting
# ==============================================================================

def test_lab2_ls_perp_simulator_exact_2leg_costs_and_funding() -> None:
    # 4 bars, 2 assets: flat prices (100 -> 100 -> 100 -> 100) to isolate funding & 2-leg costs!
    close = np.full((4, 2), 100.0, dtype=np.float64)
    # Bar 0 signal: +0.50 Long asset 0, -0.50 Short asset 1 -> held across bars 1 & 2, closed at bar 2 -> held 0 at bar 3
    target_w = np.array([
        [0.50, -0.50],
        [0.50, -0.50],
        [0.00,  0.00],
        [0.00,  0.00],
    ], dtype=np.float64)
    # Positive funding on asset 0 (+0.001) and asset 1 (+0.003) at bar 1
    # Long 0.50 pays -0.50 * 0.001 = -0.0005; Short -0.50 receives -(-0.50) * 0.003 = +0.0015 -> net +0.0010!
    funding = np.zeros((4, 2), dtype=np.float64)
    funding[1] = [0.001, 0.003]

    sim = simulate_ls_perp_backtest(close, target_w, funding, cost_bps_oneway=15.0)
    # Bar 0: held_w = 0 -> 0 PnL, 0 turnover
    assert np.allclose(sim["held_w"][0], [0.0, 0.0])
    assert sim["net_returns"][0] == 0.0
    # Bar 1: entry turnover = |0.50| + |-0.50| = 1.00 -> cost = 0.0015; funding = +0.0010 -> net = -0.0005
    assert abs(sim["turnover"][1] - 1.0) < 1e-12
    assert abs(sim["funding_pnl"][1] - 0.0010) < 1e-12
    assert abs(sim["cost_drag"][1] - 0.0015) < 1e-12
    assert abs(sim["net_returns"][1] - (0.0010 - 0.0015)) < 1e-12
    # Bar 2: held unchanged -> 0 turnover, 0 funding, 0 net
    assert abs(sim["turnover"][2]) < 1e-12
    assert abs(sim["net_returns"][2]) < 1e-12
    # Bar 3: exit turnover = 1.00 -> cost = 0.0015 -> net = -0.0015
    assert abs(sim["turnover"][3] - 1.0) < 1e-12
    assert abs(sim["net_returns"][3] + 0.0015) < 1e-12

    # Delisting NaN haircut check on held short leg
    close_dl = close.copy()
    close_dl[2, 1] = np.nan
    sim_dl = simulate_ls_perp_backtest(close_dl, target_w, funding, cost_bps_oneway=0.0, delist_haircut_bps=100.0)
    assert abs(sim_dl["net_returns"][2] + 0.50 * 0.01) < 1e-12


def test_lab2_all_four_families_zero_lookahead_and_neutrality() -> None:
    syms = [
        "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT", "AVAXUSDT",
        "UNIUSDT", "AAVEUSDT", "CRVUSDT", "SNXUSDT", "LINKUSDT", "GRTUSDT",
    ]
    panel = _make_synthetic_panel(420, syms, 4 * 3_600_000, seed=303)
    rng = np.random.default_rng(404)
    fund = np.zeros_like(panel["close"])
    # Settlement every 2 bars (8h on 4H grid)
    fund[::2] = rng.normal(0.00015, 0.00025, size=(len(fund[::2]), len(syms)))
    top_m = causal_rolling_top_n_mask(panel["quote_volume"], panel["close"], lookback_bars=60, top_n=12)

    cut = 340
    p_mut = {k: (v.copy() if isinstance(v, np.ndarray) else list(v)) for k, v in panel.items()}
    p_mut["close"][cut + 1 :] *= 2.9
    p_mut["quote_volume"][cut + 1 :] *= 0.02
    fund_mut = fund.copy()
    fund_mut[cut + 1 :] = -0.05
    top_m_mut = causal_rolling_top_n_mask(p_mut["quote_volume"], p_mut["close"], lookback_bars=60, top_n=12)

    pairs_to_test = [
        ("sector_rev",
         strat_sector_neutral_residual_rev(panel["close"], syms, top_m, ret_lb=12, vol_lb=40, deadband=0.08),
         strat_sector_neutral_residual_rev(p_mut["close"], syms, top_m_mut, ret_lb=12, vol_lb=40, deadband=0.08),
         True),
        ("coint_pairs",
         strat_rolling_coint_pairs(panel["close"], syms, window=90, z_entry=1.8, z_exit=0.5, z_stop=4.0),
         strat_rolling_coint_pairs(p_mut["close"], syms, window=90, z_entry=1.8, z_exit=0.5, z_stop=4.0),
         True),
        ("funding_disloc",
         strat_funding_dislocation_ls(panel["close"], fund, fund_lb_bars=18, vol_lb_bars=40, k_side=3, min_spread_ann=0.05, deadband=0.10),
         strat_funding_dislocation_ls(p_mut["close"], fund_mut, fund_lb_bars=18, vol_lb_bars=40, k_side=3, min_spread_ann=0.05, deadband=0.10),
         True),
        ("mkt_neut_mom",
         strat_mkt_neutral_vol_mom(panel["close"], syms, top_m, mom_lb=40, vol_lb=40, k_side=3, beta_neutralize=False, deadband=0.10),
         strat_mkt_neutral_vol_mom(p_mut["close"], syms, top_m_mut, mom_lb=40, vol_lb=40, k_side=3, beta_neutralize=False, deadband=0.10),
         True),
        ("mkt_neut_mom_bn",
         strat_mkt_neutral_vol_mom(panel["close"], syms, top_m, mom_lb=40, vol_lb=40, k_side=3, beta_neutralize=True, beta_lb=60, deadband=0.10),
         strat_mkt_neutral_vol_mom(p_mut["close"], syms, top_m_mut, mom_lb=40, vol_lb=40, k_side=3, beta_neutralize=True, beta_lb=60, deadband=0.10),
         False),
    ]

    for name, wa, wb, strict_dollar_neutral in pairs_to_test:
        assert np.allclose(wa[: cut + 1], wb[: cut + 1], atol=0.0, rtol=0.0), f"Look-ahead leak in {name}"
        assert float(np.max(np.sum(np.abs(wa), axis=1))) <= 1.0 + 1e-9, f"Gross leverage > 1.0 in {name}"
        if strict_dollar_neutral:
            assert float(np.max(np.abs(np.sum(wa, axis=1)))) < 1e-9, f"Non-zero dollar exposure in {name}"


# ==============================================================================
# Artifact, Holdout Seal & Documentation Hygiene Verification
# ==============================================================================

@pytest.mark.local_cache
def test_wave2_artifacts_holdout_seal_and_doc_hygiene() -> None:
    # 1. Holdout 2025+ seal intact
    lock_path = ROOT / "planning" / "research" / "NATIVE_FTMO_HOLDOUT_LOCK.json"
    assert lock_path.exists()
    lock_obj = json.loads(lock_path.read_text(encoding="utf-8"))
    assert "2025-01-01" in json.dumps(lock_obj)

    # 2. Shadow runner live receipt safe
    if DEFAULT_LATEST_PATH.exists():
        sh = json.loads(DEFAULT_LATEST_PATH.read_text(encoding="utf-8"))
        assert sh["schema"] == "naqex-crypto-shadow-telemetry-v1"
        assert sh["order_send_count"] == 0
        assert len(sh["top15_causal_universe"]) == 15

    # 3. Lab #1 & Lab #2 summary JSONs intact & zero holdout touch
    lab1_sum = LAB1_CACHE_DIR / "lab1_summary.json"
    for p, expected_schema in [
        (lab1_sum, "naqex-lab1-crypto-1h-intraday-v1"),
        (LAB2_SUMMARY_PATH, "naqex-lab2-crypto-statarb-v1"),
    ]:
        assert p.exists(), f"Missing summary artifact: {p}"
        obj = json.loads(p.read_text(encoding="utf-8"))
        assert obj["schema"] == expected_schema
        assert obj["order_send_count"] == 0
        assert obj["holdout_rows_analysed"] == 0
        assert obj["m_total"] == 12
        assert len(obj["results"]) == 12

    # 4. Any exported sleeve return JSON matches exact Risk-Auditor v1 schema
    for ret_p in (LAB1_RETURNS_PATH, LAB2_RETURNS_PATH):
        if ret_p.exists():
            r_obj = json.loads(ret_p.read_text(encoding="utf-8"))
            assert r_obj["schema"] == "naqex-sleeve-daily-returns-v1"
            assert float(r_obj["annualization_days"]) == 365.0
            dr = r_obj["daily_returns"]
            assert len(dr) >= 200
            assert list(dr.keys()) == sorted(dr.keys())
            assert all(np.isfinite(float(v)) for v in dr.values())

    # 5. Markdown reports < 900 KB, valid YAML frontmatter, zero bare `$`, zero broken relative links
    reports = [
        ROOT / "planning" / "research" / "LAB1-CRYPTO-1H-INTRADAY-20261124.md",
        ROOT / "planning" / "research" / "LAB2-CRYPTO-STATARB-NEUTRAL-20261124.md",
    ]
    link_re = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    for rep in reports:
        assert rep.exists(), f"Missing report: {rep}"
        raw = rep.read_text(encoding="utf-8")
        assert rep.stat().st_size < 900_000, f"Anti-bloat violation: {rep}"
        assert raw.startswith("---\n"), f"Missing YAML frontmatter in {rep}"
        # Zero bare `$` in prose (strip fenced code blocks first)
        prose = re.sub(r"```.*?```", "", raw, flags=re.S)
        assert "$" not in prose, f"Bare '$' found in prose of {rep}"
        # Verify all local Markdown links resolve
        for m in link_re.finditer(raw):
            tgt = m.group(1).strip()
            if tgt.startswith(("http://", "https://", "mailto:", "#")):
                continue
            tgt_clean = tgt.split("#", 1)[0]
            if not tgt_clean:
                continue
            resolved = (rep.parent / tgt_clean).resolve()
            assert resolved.exists(), f"Broken relative link '{tgt}' in {rep}"

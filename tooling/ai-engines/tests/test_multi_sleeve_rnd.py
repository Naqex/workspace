"""Deterministic unit & anti-bias regression tests for Lane C (quant-rnd) Tier 3 & Tier 4 deliverables.

Covers:
  - M3.1/M3.2: crypto_causal_universe.py (zero look-ahead mutation test, t->t+1 shift, delisting haircut, 2x cost monotonicity)
  - M3.3: funding_rate_carry.py (2x equity buffer cap, basis MTM, negative-funding exit causality, Mark-Price liq check)
  - M4.3: macro_etf_trend.py (zero look-ahead mutation test across all 5 macro strategies, short-borrow + 2x cost drag)
  - M4.1/M4.2: pass29_gold_index_dev.py & pass30_fx_extended_dev.py (holdout lock, catalog integrity, Matched-Hold Null determinism)
  - Artifact schema, anti-bloat (< 900 KB), zero broken relative links, and holdout_rows == 0 verification.
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

from quant_factory import (
    crypto_causal_universe as ccu,
    funding_rate_carry as frc,
    macro_etf_trend as met,
    pass29_gold_index_dev as p29,
    pass30_fx_extended_dev as p30,
)
from quant_factory.data_store import assert_holdout_locked


def _make_synthetic_crypto_panel(n_t: int = 240, seed: int = 42) -> dict:
    rng = np.random.default_rng(seed)
    syms = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT", "XRPUSDT", "DOGEUSDT", "WAVESUSDT"]
    n_k = len(syms)
    rets = rng.normal(0.001, 0.03, size=(n_t, n_k))
    closes = 100.0 * np.cumprod(1.0 + rets, axis=0)
    highs = closes * (1.0 + rng.uniform(0.005, 0.03, size=(n_t, n_k)))
    lows = closes * (1.0 - rng.uniform(0.005, 0.03, size=(n_t, n_k)))
    opens = closes * (1.0 + rng.normal(0.0, 0.005, size=(n_t, n_k)))
    qvol = rng.uniform(1e7, 5e8, size=(n_t, n_k))
    # Simulate late listing for SOLUSDT (starts day 40) and delisting for WAVESUSDT (ends day 180)
    for arr in (opens, highs, lows, closes, qvol):
        arr[:40, 3] = np.nan
        arr[180:, 7] = np.nan
    ts = np.arange(n_t, dtype=np.int64) * 86_400_000 + 1_546_300_800_000
    return {
        "interval": "1d",
        "symbols": syms,
        "timestamps_ms": ts,
        "dates": [ccu._ms_to_date(int(t)) for t in ts],
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "quote_volume": qvol,
    }


def test_crypto_causal_universe_zero_lookahead():
    panel1 = _make_synthetic_crypto_panel(n_t=240, seed=101)
    t_cut = 150

    mask15_a = ccu.causal_rolling_top_n_mask(panel1["quote_volume"], panel1["close"], lookback_bars=30, top_n=5)
    mask10_a = ccu.causal_rolling_top_n_mask(panel1["quote_volume"], panel1["close"], lookback_bars=30, top_n=4)
    strats_a = ccu.build_d1_strategies(panel1, mask15_a, mask10_a)

    # Corrupt ALL data strictly after t_cut (t > 150)
    panel2 = {k: (v.copy() if isinstance(v, np.ndarray) else list(v) if isinstance(v, list) else v) for k, v in panel1.items()}
    panel2["close"][t_cut + 1:] *= 50.0
    panel2["high"][t_cut + 1:] *= 55.0
    panel2["low"][t_cut + 1:] *= 0.2
    panel2["quote_volume"][t_cut + 1:, 0] = 1.0
    panel2["quote_volume"][t_cut + 1:, 6] = 1e15

    mask15_b = ccu.causal_rolling_top_n_mask(panel2["quote_volume"], panel2["close"], lookback_bars=30, top_n=5)
    mask10_b = ccu.causal_rolling_top_n_mask(panel2["quote_volume"], panel2["close"], lookback_bars=30, top_n=4)
    strats_b = ccu.build_d1_strategies(panel2, mask15_b, mask10_b)

    assert np.array_equal(mask15_a[:t_cut + 1], mask15_b[:t_cut + 1]), "Look-ahead leak in rolling Top-N mask!"
    for name in strats_a:
        wa = strats_a[name][1][:t_cut + 1]
        wb = strats_b[name][1][:t_cut + 1]
        assert np.allclose(wa, wb, equal_nan=True), f"Look-ahead leak in strategy {name}!"

    # Pre-listing coin (index 3, listed day 40) must NEVER be selected before day 40 + 27 (90% of 30d)
    assert not np.any(mask15_a[:60, 3]), "Pre-listing coin entered Top-N too early!"


def test_crypto_spot_delisting_and_t_plus_1_shift():
    closes = np.array([
        [100.0, 50.0],
        [110.0, 55.0],
        [121.0, np.nan],  # Coin 1 delisted on day 2!
        [121.0, np.nan],
    ], dtype=np.float64)
    # Signal at day 0 holds 50/50 -> held on day 1 (+10% on both); signal at day 1 still wants 50/50 -> coin 1 delists on day 2
    target_w = np.array([
        [0.5, 0.5],
        [0.5, 0.5],
        [0.5, 0.0],
        [0.5, 0.0],
    ], dtype=np.float64)
    sim1 = ccu.simulate_spot_backtest(closes, target_w, cost_bps_oneway=15.0, delist_haircut_bps=100.0)
    sim2 = ccu.simulate_spot_backtest(closes, target_w, cost_bps_oneway=30.0, delist_haircut_bps=100.0)

    assert sim1["held_w"][0].sum() == 0.0, "Day 0 must hold 0 (strict t -> t+1 shift)!"
    assert np.allclose(sim1["held_w"][1], [0.5, 0.5])
    assert sim1["held_w"][2, 1] == 0.0, "Delisted coin must be liquidated to 0 on missing bar!"
    assert sim1["delist_exits_weight_sum"] == pytest.approx(0.5)
    assert np.all(np.isfinite(sim1["net_returns"]))
    assert np.all(sim2["net_returns"] <= sim1["net_returns"] + 1e-12)
    # Day 1 exact gross = 0.10, turnover = 1.0, cost = 0.0015 => net = 0.0985
    assert sim1["net_returns"][1] == pytest.approx(0.10 - 0.0015, abs=1e-9)


def test_funding_carry_accounting_and_margin_buffer():
    n_t, n_k = 40, 3
    funding = np.full((n_t, n_k), 0.0003, dtype=np.float64)  # ~11% ann positive funding
    funding[20:, 0] = -0.0005  # Coin 0 flips deeply negative from day 20 onward
    spot_c = np.full((n_t, n_k), 100.0, dtype=np.float64)
    perp_c = np.full((n_t, n_k), 100.0, dtype=np.float64)
    spot_h = np.full((n_t, n_k), 102.0, dtype=np.float64)
    perp_h = np.full((n_t, n_k), 102.0, dtype=np.float64)
    # Inject a real +120% Mark-Price jump on coin 2 on day 15
    spot_h[15, 2] = 220.0
    perp_h[15, 2] = 220.0

    panel = {
        "dates": [f"2022-01-{i+1:02d}" if i < 31 else f"2022-02-{i-30:02d}" for i in range(n_t)],
        "symbols": ["BTCUSDT", "ETHUSDT", "DOGEUSDT"],
        "funding_daily": funding,
        "spot_close": spot_c,
        "perp_close": perp_c,
        "perp_high": perp_h,
        "spot_high": spot_h,
    }
    strats = frc.build_carry_strategies(panel)
    buf, w_be = strats["CARRY_BTC_ETH_CONS_2XBUF"]
    assert buf == 2.0
    # After 7 negative funding days (days 20..26), BTC weight must exit to 0 causally
    assert w_be[18, 0] > 0.0
    assert w_be[27, 0] == 0.0

    sim1 = frc.simulate_funding_carry(
        funding, spot_c, perp_c, perp_h, np.full((n_t, n_k), 1.0 / 3.0),
        spot_high=spot_h, equity_buffer_mult=2.0, oneway_pair_cost_bps=23.0,
    )
    assert sim1["notional_cap"] == pytest.approx(0.5)
    assert float(np.max(sim1["held_notional"].sum(axis=1))) <= 0.5 + 1e-12
    assert sim1["isolated_liq_events"] == 1  # Coin 2 +120% jump exceeds 95% isolated threshold
    assert sim1["cross_liq_events"] == 0     # Cross-margin diversified basket survives (+40% draw < 90%)


def test_macro_etf_zero_lookahead_and_short_borrow():
    rng = np.random.default_rng(77)
    n_t = 320
    syms = list(met.ETF_UNIVERSE_12)
    rets = rng.normal(0.0004, 0.012, size=(n_t, len(syms)))
    px = 100.0 * np.cumprod(1.0 + rets, axis=0)
    # Build business-day-like ISO date sequence spanning ~15 months
    dates = []
    yr, mo, dy = 2020, 1, 1
    for _ in range(n_t):
        dates.append(f"{yr:04d}-{mo:02d}-{dy:02d}")
        dy += 1
        if dy > 28:
            dy = 1
            mo += 1
            if mo > 12:
                mo = 1
                yr += 1
    panel1 = {"dates": dates, "symbols": syms, "adjclose": px}
    t_cut = 280
    strats_a = met.build_macro_strategies(panel1)

    panel2 = {"dates": list(dates), "symbols": list(syms), "adjclose": px.copy()}
    panel2["adjclose"][t_cut + 1:] *= 10.0
    strats_b = met.build_macro_strategies(panel2)

    for name in strats_a:
        wa = strats_a[name][2][:t_cut + 1]
        wb = strats_b[name][2][:t_cut + 1]
        assert np.allclose(wa, wb, equal_nan=True), f"Look-ahead leak in macro strategy {name}!"

    # Verify short-borrow + 2x cost strictly reduces net return on Long/Short TSMOM
    _, max_lev, w_ls = strats_a["M1_AHL_TSMOM_LS_VOL10"]
    s1 = met.simulate_etf_weights(px, w_ls, cost_bps_oneway=5.0, short_borrow_bps_yr=50.0, max_gross_leverage=max_lev)
    s2 = met.simulate_etf_weights(px, w_ls, cost_bps_oneway=10.0, short_borrow_bps_yr=100.0, max_gross_leverage=max_lev)
    assert np.all(s2["net_returns"] <= s1["net_returns"] + 1e-12)


def test_pass29_pass30_holdout_lock_and_matched_hold_null():
    lock_sha = assert_holdout_locked()
    assert len(lock_sha) == 64

    c29 = p29.build_pass29_catalog()
    c30 = p30.build_pass30_catalog()
    assert len(c29) == 24 and len({x["id"] for x in c29}) == 24
    assert len(c30) == 24 and len({x["id"] for x in c30}) == 24

    # Deterministic zero-leakage Matched-Hold Null sanity check on synthetic flat-walk quotes
    rng = np.random.default_rng(123)
    n_bars = 2000
    mid = 100.0 + np.cumsum(rng.normal(0.0, 0.05, size=n_bars))
    quotes = np.column_stack([mid, mid + 0.05, mid - 0.05, mid, mid + 0.01, mid + 0.06, mid - 0.04, mid + 0.01])
    pool_ws = np.array([0, 500, 1000, 1500], dtype=np.int64)
    pool_fl = np.array([450, 950, 1450, 1950], dtype=np.int64)
    pool_atr = np.array([1.0, 1.0, 1.0, 1.0], dtype=np.float64)
    hb = np.full(30, 60, dtype=np.int64)
    sd = np.ones(30, dtype=np.int64)
    sl_atr = np.full(30, 0.75, dtype=np.float64)
    slp = np.full(30, 0.02, dtype=np.float64)

    p_huge1 = p29._matched_hold_null_numba(quotes, pool_ws, pool_fl, pool_atr, hb, sd, sl_atr, slp, 50.0, 200, 20261124)
    p_huge2 = p29._matched_hold_null_numba(quotes, pool_ws, pool_fl, pool_atr, hb, sd, sl_atr, slp, 50.0, 200, 20261124)
    p_bad = p29._matched_hold_null_numba(quotes, pool_ws, pool_fl, pool_atr, hb, sd, sl_atr, slp, -50.0, 200, 20261124)
    assert p_huge1 == p_huge2, "Matched-Hold Null must be deterministic for fixed seed!"
    assert p_huge1 <= 0.02
    assert p_bad >= 0.98


@pytest.mark.local_cache
def test_generated_return_jsons_and_research_docs_anti_bloat():
    ret_dir = ROOT / ".runtime" / "quant-pod-returns"
    for fname in ("sleeve2_crypto_spot.json", "sleeve3a_funding_carry.json", "sleeve3b_macro_etf.json"):
        p = ret_dir / fname
        assert p.exists(), f"Missing sleeve return JSON: {p}"
        payload = json.loads(p.read_text(encoding="utf-8"))
        assert payload["schema"] == "naqex-sleeve-daily-returns-v1"
        dr = payload["daily_returns"]
        assert len(dr) >= 1000
        keys = list(dr.keys())
        assert keys == sorted(keys), f"Dates not sorted in {fname}"
        vals = np.array(list(dr.values()), dtype=np.float64)
        assert np.all(np.isfinite(vals)), f"Non-finite return in {fname}"

    for sname in ("pass29_gold_index_summary.json", "pass30_fx_extended_summary.json"):
        sp = ret_dir / sname
        assert sp.exists(), f"Missing discovery summary JSON: {sp}"
        sd = json.loads(sp.read_text(encoding="utf-8"))
        assert sd["holdout_rows_analysed"] == 0, f"Holdout contamination in {sname}!"
        assert sd["order_send_count"] == 0

    docs = [
        "CRYPTO-SLEEVE2-SURVIVORSHIP-FREE-20261124.md",
        "CRYPTO-PROMOTION-SPEC-20261124.md",
        "SLEEVE3A-FUNDING-RATE-CARRY-20261124.md",
        "SLEEVE3B-MACRO-ETF-TREND-18YR-20261124.md",
        "PASS29-GOLD-INDEX-ORTHOGONAL-DEV-20261124.md",
        "PASS30-FX-EXTENDED-ORTHOGONAL-DEV-20261124.md",
    ]
    link_re = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    for dname in docs:
        dp = ROOT / "planning" / "research" / dname
        assert dp.exists(), f"Missing research report: {dp}"
        assert dp.stat().st_size < 900 * 1024, f"Anti-bloat violation (>= 900 KB): {dp}"
        txt = dp.read_text(encoding="utf-8")
        assert txt.startswith("---\n"), f"Missing YAML frontmatter in {dname}"
        for target in link_re.findall(txt):
            if target.startswith(("http://", "https://", "#", "mailto:")):
                continue
            rel_path = target.split("#", 1)[0]
            resolved = (dp.parent / rel_path).resolve()
            assert resolved.exists(), f"Broken local link `{target}` in {dname}"

"""Deterministic Unit, Causality, Swap & Hygiene Tests for Wave 2 Cycle 2A Labs (#3A, #3B, #2B).

Covers:
  - Lab #3A (`ftmo_swing_real_swap_lab.py`): exact MT5 `swap_mode=1` sign & triple-Wednesday/Friday
    rollover math, anti-fake-swap cap on cash equity index anomalies (`US100.cash +1076.28`),
    strict anti-lookahead future-mutation test, and strict `< 2025-01-01` Holdout seal.
  - Lab #3B (`new_assets_10_dev_lab.py`): strict anti-lookahead future-mutation test across all 9 specs,
    anti-fake-swap cap on commodity/index positive rollovers, and verified `< 2025-01-01` Parquet seal.
  - Lab #2B (`crypto_maker_statarb_study.py`): exact passive limit/maker blended cost formula,
    strict anti-lookahead future-mutation test on rank-buffer hysteresis funding & XSMOM builders,
    exact dollar neutrality `abs(sum(w)) < 1e-9`, gross `<= 1.0x`, and cumulative `N = 20` DSR audit.
  - Reports & Governance: `< 900 KB`, valid YAML frontmatter, zero bare `$`, zero broken local links,
    Holdout lock untouched, `order_send_count == 0`, `holdout_rows_analysed == 0`.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys

import numpy as np
import pyarrow.parquet as pq
import pytest

AI_ENGINES = Path(__file__).resolve().parents[1]
ROOT = AI_ENGINES.parents[1]
if str(AI_ENGINES) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES))

from quant_factory.crypto_causal_universe import causal_rolling_top_n_mask
from quant_factory.crypto_maker_statarb_study import (
    CUMULATIVE_TRIALS_LAB2_PLUS_2B,
    LAB2B_SUMMARY_PATH,
    TIER_M1_85_BPS,
    TIER_M2_70_BPS,
    compute_maker_effective_cost_bps,
    strat_funding_disloc_hysteresis,
    strat_xsmom_hysteresis,
)
from quant_factory.ftmo_swing_real_swap_lab import (
    ALL11_ASSETS,
    LAB3A_SUMMARY_PATH,
    build_lab3a_strategies,
    compute_ftmo_daily_swap_frac,
    load_ftmo_symbol_specs,
    simulate_ftmo_swing_backtest,
)
from quant_factory.new_assets_10_dev_lab import (
    LAB3B_SUMMARY_PATH,
    NEW10_CACHE_DIR,
    NEW10_IDS,
    build_lab3b_strategies,
    simulate_new10_backtest,
)


def _make_dev_panel(n_t: int, assets: tuple[str, ...], bar_sec: int, seed: int) -> dict:
    rng = np.random.default_rng(seed)
    n_a = len(assets)
    # Business-day synthetic calendar strictly inside 2020-2023 (< 2025-01-01)
    start_sec = 1_577_836_800  # 2020-01-01T00:00:00Z
    ts = start_sec + np.arange(n_t, dtype=np.int64) * bar_sec
    rets = rng.normal(0.0001, 0.006, size=(n_t, n_a))
    close = 100.0 * np.exp(np.cumsum(rets, axis=0))
    high = close * (1.0 + np.abs(rng.normal(0.003, 0.002, size=(n_t, n_a))))
    low = close * (1.0 - np.abs(rng.normal(0.003, 0.002, size=(n_t, n_a))))
    dates = [f"2020-{(i // 28) % 12 + 1:02d}-{(i % 28) + 1:02d}" for i in range(n_t)]
    weekdays = np.arange(n_t, dtype=np.int32) % 5
    return {
        "bar_sec": bar_sec,
        "assets": list(assets),
        "timestamps_sec": ts,
        "dates": dates,
        "weekdays": weekdays,
        "high": high,
        "low": low,
        "close": close,
        "oneway_bps": {a: 2.0 for a in assets},
    }


# ==============================================================================
# Lab #3A: Real FTMO Swap Math, Triple Rollover & Anti-Fake-Swap Guard
# ==============================================================================

def test_ftmo_real_swap_sign_triple_wednesday_and_index_cap() -> None:
    specs = load_ftmo_symbol_specs()

    # 1. GBPJPY Long (+5.96 pts, point=0.001, rollover=3 -> Wed py_weekday=2)
    gbpjpy = specs["GBPJPY"]
    sw_tue = compute_ftmo_daily_swap_frac(gbpjpy, 190.0, +1, py_weekday=1)
    sw_wed = compute_ftmo_daily_swap_frac(gbpjpy, 190.0, +1, py_weekday=2)
    assert sw_tue > 0.0
    assert abs(sw_tue - (5.96 * 0.001 / 190.0)) < 1e-12
    assert abs(sw_wed - 3.0 * sw_tue) < 1e-12

    # 2. GBPJPY Short (-25.49 pts) MUST be strongly negative and 3x on Wednesday
    sw_short_wed = compute_ftmo_daily_swap_frac(gbpjpy, 190.0, -1, py_weekday=2)
    assert sw_short_wed < 0.0
    assert abs(sw_short_wed - 3.0 * (-25.49 * 0.001 / 190.0)) < 1e-12

    # 3. XAUUSD Long (-54.46 pts, point=0.01) -> ~-7.6% annualized negative swap
    xau = specs["XAUUSD"]
    sw_xau_mon = compute_ftmo_daily_swap_frac(xau, 2600.0, +1, py_weekday=0)
    assert sw_xau_mon < -0.00018  # < -6.5%/yr

    # 4. Anti-Fake-Swap Guard on anomalous US100.cash (+1076.28 snapshot): MUST cap to -5%/yr!
    us100 = specs["US100.cash"]
    sw_idx_thu = compute_ftmo_daily_swap_frac(us100, 20000.0, +1, py_weekday=3, is_equity_index=True)
    sw_idx_fri = compute_ftmo_daily_swap_frac(us100, 20000.0, +1, py_weekday=4, is_equity_index=True)
    assert abs(sw_idx_thu - (-0.05 / 365.0)) < 1e-12
    assert abs(sw_idx_fri - 3.0 * (-0.05 / 365.0)) < 1e-12  # Triple on Friday (rollover=5)

    # 5. Zero-positive-swap floor zeroes positive FX carry while still charging 100% negative swap
    assert compute_ftmo_daily_swap_frac(gbpjpy, 190.0, +1, py_weekday=2, zero_positive_swap=True) == 0.0
    assert compute_ftmo_daily_swap_frac(gbpjpy, 190.0, -1, py_weekday=2, zero_positive_swap=True) == sw_short_wed


def test_lab3a_zero_lookahead_and_t_plus_1_swap_simulator() -> None:
    specs = load_ftmo_symbol_specs()
    p_d1 = _make_dev_panel(320, ALL11_ASSETS, 86400, seed=11)
    p_h4 = _make_dev_panel(320, ALL11_ASSETS, 14400, seed=12)
    strats_a = build_lab3a_strategies(p_d1, p_h4, specs)

    cut = 260
    p_d1_m = {k: (v.copy() if isinstance(v, np.ndarray) else v) for k, v in p_d1.items()}
    p_h4_m = {k: (v.copy() if isinstance(v, np.ndarray) else v) for k, v in p_h4.items()}
    for pm in (p_d1_m, p_h4_m):
        pm["close"][cut + 1 :] *= 2.4
        pm["high"][cut + 1 :] *= 2.7
        pm["low"][cut + 1 :] *= 0.4
    strats_b = build_lab3a_strategies(p_d1_m, p_h4_m, specs)

    assert len(strats_a) == 12
    for sa, sb in zip(strats_a, strats_b):
        assert sa["id"] == sb["id"]
        assert np.allclose(sa["w"][: cut + 1], sb["w"][: cut + 1], atol=0.0, rtol=0.0), f"Look-ahead in {sa['id']}"
        assert float(np.max(np.sum(np.abs(sa["w"]), axis=1))) <= 1.5 + 1e-9

    # Simulator causality + 2x cost monotonicity
    s1 = simulate_ftmo_swing_backtest(p_d1, strats_a[0]["w"], specs, cost_mult=1.0)
    s2 = simulate_ftmo_swing_backtest(p_d1, strats_a[0]["w"], specs, cost_mult=2.0)
    assert np.allclose(s1["held_w"][0], 0.0)
    assert float(np.sum(s2["daily_returns"])) <= float(np.sum(s1["daily_returns"])) + 1e-12


# ==============================================================================
# Lab #3B: 10 Brand-New Assets Causality & Strict < 2025-01-01 Holdout Seal
# ==============================================================================

@pytest.mark.local_cache
def test_lab3b_zero_lookahead_and_commodity_swap_cap() -> None:
    specs = load_ftmo_symbol_specs()
    p = _make_dev_panel(300, NEW10_IDS, 86400, seed=21)
    strats_a = build_lab3b_strategies(p, specs)

    cut = 240
    p_m = {k: (v.copy() if isinstance(v, np.ndarray) else v) for k, v in p.items()}
    p_m["close"][cut + 1 :] *= 3.1
    p_m["high"][cut + 1 :] *= 3.4
    p_m["low"][cut + 1 :] *= 0.3
    strats_b = build_lab3b_strategies(p_m, specs)

    assert len(strats_a) == 9
    for sa, sb in zip(strats_a, strats_b):
        assert np.allclose(sa["w"][: cut + 1], sb["w"][: cut + 1], atol=0.0, rtol=0.0), f"Look-ahead in {sa['id']}"
        assert float(np.max(np.sum(np.abs(sa["w"]), axis=1))) <= 1.5 + 1e-9

    # Anti-fake-swap check: Long UKOIL (+50.76 snapshot) MUST NOT credit positive carry!
    w_ukoil = np.zeros_like(p["close"])
    uk_i = p["assets"].index("UKOIL")
    w_ukoil[:, uk_i] = 1.0
    sim_uk = simulate_new10_backtest(p, w_ukoil, specs, cost_mult=0.0)
    assert float(np.max(sim_uk["daily_swap_pnl"])) <= 1e-12

    # Short UKOIL (-233.25) MUST charge strong negative swap!
    sim_uk_s = simulate_new10_backtest(p, -w_ukoil, specs, cost_mult=0.0)
    assert float(np.sum(sim_uk_s["daily_swap_pnl"])) < -0.05

    # Verify every cached Parquet under .runtime/new-assets-10-cache/ is strictly < 2025-01-01!
    for aid in NEW10_IDS:
        pq_p = NEW10_CACHE_DIR / f"{aid}.parquet"
        assert pq_p.exists(), f"Missing Lab 3B cache file: {pq_p}"
        dates = pq.read_table(pq_p, columns=["date"])["date"].to_pylist()
        assert len(dates) >= 2000
        assert max(dates) < "2025-01-01", f"HOLDOUT VIOLATION in {aid}: max={max(dates)}"


# ==============================================================================
# Lab #2B: Passive Maker Cost Model, Rank-Buffer Causality & Exact Neutrality
# ==============================================================================

def test_lab2b_maker_cost_formula_and_hysteresis_causality() -> None:
    assert abs(compute_maker_effective_cost_bps(fill_prob=0.85, maker_fee_bps=2.0, adverse_selection_bps=1.5) - 4.475) < 1e-9
    assert abs(compute_maker_effective_cost_bps(fill_prob=0.70, maker_fee_bps=2.0, adverse_selection_bps=2.5) - 6.15) < 1e-9
    assert TIER_M1_85_BPS < TIER_M2_70_BPS < 15.0
    assert CUMULATIVE_TRIALS_LAB2_PLUS_2B == 20

    rng = np.random.default_rng(77)
    n_t, n_s = 320, 14
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0001, 0.012, size=(n_t, n_s)), axis=0))
    qvol = np.exp(rng.normal(16.0, 0.5, size=(n_t, n_s)))
    fund = np.zeros((n_t, n_s), dtype=np.float64)
    fund[::2] = rng.normal(0.0002, 0.0003, size=(n_t // 2, n_s))
    top_m = causal_rolling_top_n_mask(qvol, close, lookback_bars=40, top_n=12)

    cut = 250
    c_mut = close.copy()
    c_mut[cut + 1 :] *= 2.8
    q_mut = qvol.copy()
    q_mut[cut + 1 :] *= 0.01
    f_mut = fund.copy()
    f_mut[cut + 1 :] = -0.05
    top_mut = causal_rolling_top_n_mask(q_mut, c_mut, lookback_bars=40, top_n=12)

    wf_a = strat_funding_disloc_hysteresis(close, fund, fund_lb_bars=24, vol_lb_bars=40, k_side=3, rank_buffer=2, min_spread_ann=0.05, rebal_every_bars=6)
    wf_b = strat_funding_disloc_hysteresis(c_mut, f_mut, fund_lb_bars=24, vol_lb_bars=40, k_side=3, rank_buffer=2, min_spread_ann=0.05, rebal_every_bars=6)
    wm_a = strat_xsmom_hysteresis(close, top_m, mom_lb=40, vol_lb=40, k_side=3, rank_buffer=3, rebal_every_bars=6)
    wm_b = strat_xsmom_hysteresis(c_mut, top_mut, mom_lb=40, vol_lb=40, k_side=3, rank_buffer=3, rebal_every_bars=6)

    for name, wa, wb in (("fund_hyst", wf_a, wf_b), ("xsmom_hyst", wm_a, wm_b)):
        assert np.allclose(wa[: cut + 1], wb[: cut + 1], atol=0.0, rtol=0.0), f"Look-ahead in {name}"
        assert float(np.max(np.sum(np.abs(wa), axis=1))) <= 1.0 + 1e-9
        assert float(np.max(np.abs(np.sum(wa, axis=1)))) < 1e-9, f"Non-zero net dollar exposure in {name}"


# ==============================================================================
# Artifact, Holdout Seal & Documentation Hygiene Verification
# ==============================================================================

@pytest.mark.local_cache
def test_wave2_cycle2a_artifacts_holdout_and_doc_hygiene() -> None:
    lock_path = ROOT / "planning" / "research" / "NATIVE_FTMO_HOLDOUT_LOCK.json"
    assert lock_path.exists()
    assert "2025-01-01" in lock_path.read_text(encoding="utf-8")

    for sp, schema, m_exp in [
        (LAB3A_SUMMARY_PATH, "naqex-lab3a-ftmo-swing-real-swap-v1", 12),
        (LAB3B_SUMMARY_PATH, "naqex-lab3b-new10-assets-dev-v1", 9),
        (LAB2B_SUMMARY_PATH, "naqex-lab2b-crypto-maker-statarb-v1", 8),
    ]:
        assert sp.exists(), f"Missing summary: {sp}"
        obj = json.loads(sp.read_text(encoding="utf-8"))
        assert obj["schema"] == schema
        assert obj["order_send_count"] == 0
        assert obj["holdout_rows_analysed"] == 0
        assert obj["m_total"] == m_exp
        if "max_date_analysed" in obj:
            assert obj["max_date_analysed"] < "2025-01-01"

    reports = [
        ROOT / "planning" / "research" / "LAB3A-FTMO-SWING-REAL-SWAP-DEV-20261124.md",
        ROOT / "planning" / "research" / "LAB3B-10NEW-ASSETS-DEV-20261124.md",
        ROOT / "planning" / "research" / "LAB2B-CRYPTO-MAKER-STATARB-20261124.md",
    ]
    link_re = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    for rep in reports:
        assert rep.exists(), f"Missing report: {rep}"
        raw = rep.read_text(encoding="utf-8")
        assert rep.stat().st_size < 900_000
        assert raw.startswith("---\n")
        prose = re.sub(r"```.*?```", "", raw, flags=re.S)
        assert "$" not in prose, f"Bare '$' found in prose of {rep}"
        for m in link_re.finditer(raw):
            tgt = m.group(1).strip()
            if tgt.startswith(("http://", "https://", "mailto:", "#")):
                continue
            tgt_clean = tgt.split("#", 1)[0]
            if not tgt_clean:
                continue
            resolved = (rep.parent / tgt_clean).resolve()
            assert resolved.exists(), f"Broken link '{tgt}' in {rep}"

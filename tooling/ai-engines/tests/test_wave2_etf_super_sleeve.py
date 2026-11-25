"""Wave-2 Cycle 4G Tests — Own-Book ETF Super-Sleeve (9 Approved Engines) & IBKR Integer-Share Lot Audit.

Verifies:
  - Holdout 2025+ SEALED (`holdout_rows_analysed = 0`, `OrderSend = 0`), report `< 14 KB`, zero bare `$`,
    exact 5/5 candidate parity vs `.runtime/etf40-cache/ownbook_etf_super_sleeve_summary.json`,
    and zero overwrite of incumbent `sleeve3b_macro_etf.json` / `sleeve4_etf40_multifactor.json`.
  - Strict Cluster-A-only NCO weights (`<= 2017-12-31`): mutating ALL Cluster B (`>= 2018-01-01`)
    returns produces EXACT `0.0` change in `SUPER_ETF_9ENG_CLA_NCO` weights!
  - Bit-for-bit future-mutation zero-lookahead proof on the full 6-engine `SUPER_ETF_6ENG_EQW` composite!
  - Exact IBKR US Tiered commission math (`$0.0035/sh`, `$0.35` min, `1.0%` cap) & integer-share tracking-error
    monotonicity across `5k` vs `200k USD` and Fractional OFF vs ON.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys

import numpy as np

AI_ENGINES = Path(__file__).resolve().parents[1]
ROOT = AI_ENGINES.parents[1]
if str(AI_ENGINES) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES))

from quant_factory.data_store import assert_holdout_locked
from quant_factory.etf40_multifactor_vrp_lab import ETF40_CACHE_DIR, load_etf40_panel
from quant_factory.lab7_overnight_macro_rd_loop import load_etf40_ohlc_panel, simulate_etf_daily_or_overnight
from quant_factory.ownbook_etf_super_sleeve import (
    CLUSTER_A_END,
    SUMMARY_JSON_PATH,
    SUPER_6_IDS,
    build_all_9_approved_engine_weights,
    compute_cla_nco_9engine_weights,
    compute_ibkr_order_commission,
    simulate_ibkr_integer_shares,
)
from quant_factory.portfolio_allocator import DEFAULT_RETURNS_DIR


def _count_bare_dollar_pairs(md_text: str) -> int:
    in_fence = False
    bad = 0
    for ln in md_text.splitlines():
        if ln.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        cleaned = re.sub(r"`[^`]*`", "", ln)
        if cleaned.count("$") >= 2:
            bad += 1
    return bad


def test_cycle4g_report_json_parity_holdout_and_no_sleeve_overwrite():
    lock_sha = assert_holdout_locked()
    assert len(lock_sha) == 64

    rp = ROOT / "planning/research/OWNBOOK-ETF-SUPER-SLEEVE-AND-IBKR-LOT-AUDIT-20261124.md"
    assert rp.exists(), f"Missing Cycle 4G report: {rp}"
    assert SUMMARY_JSON_PATH.exists(), f"Missing Cycle 4G JSON summary: {SUMMARY_JSON_PATH}"
    assert rp.stat().st_size < 14_336, f"Report {rp.stat().st_size} B exceeds 14 KB cap!"

    txt = rp.read_text(encoding="utf-8")
    summary = json.loads(SUMMARY_JSON_PATH.read_text(encoding="utf-8"))
    assert "holdout_rows_analysed: 0" in txt
    assert "order_send_count: 0" in txt
    assert _count_bare_dollar_pairs(txt) == 0
    assert summary["holdout_rows_analysed"] == 0
    assert summary["order_send_count"] == 0
    assert len(summary["candidates"]) == 5

    # Exact 5/5 candidate ID & Blind Cluster B 1x CAGR parity between MD and JSON
    for c in summary["candidates"]:
        assert c["id"] in txt
        assert f"{c['cl_b_1x_cagr_pct']:+.2f}%" in txt

    # Verify incumbent sleeve3b & sleeve4 files were NOT overwritten!
    s3b = json.loads((DEFAULT_RETURNS_DIR / "sleeve3b_macro_etf.json").read_text(encoding="utf-8"))
    s4 = json.loads((DEFAULT_RETURNS_DIR / "sleeve4_etf40_multifactor.json").read_text(encoding="utf-8"))
    assert s3b["strategy_name"] == "M5_VOL_PARITY_TREND_GUARD"
    assert s4["strategy_name"] == "E40_VRP_VOL_CARRY"


def test_cla_nco_9engine_weights_strictly_independent_of_cluster_b():
    """Mutating ALL Cluster B (>= 2018-01-01) prices/returns MUST produce EXACT 0.0 change in 9-engine NCO weights."""
    p4 = load_etf40_panel(cache_dir=ETF40_CACHE_DIR)
    p7 = load_etf40_ohlc_panel(cache_dir=ETF40_CACHE_DIR)
    eng_w = build_all_9_approved_engine_weights(p4, p7)

    w_map_clean, w_vec_clean = compute_cla_nco_9engine_weights(p7, eng_w, cluster_a_end=CLUSTER_A_END)
    assert len(w_vec_clean) == 9
    assert abs(float(np.sum(w_vec_clean)) - 1.0) <= 1e-9
    assert float(np.min(w_vec_clean)) >= -1e-12
    assert float(np.max(w_vec_clean)) <= 0.35 + 1e-9

    # Violently corrupt ALL Cluster B dates (>= 2018-01-01)
    b_mask = np.array([d > CLUSTER_A_END for d in p7["dates"]], dtype=bool)
    p7_mut = {k: (v.copy() if isinstance(v, np.ndarray) else list(v)) for k, v in p7.items()}
    p7_mut["r_cc"][b_mask] = -0.35
    p7_mut["adj_close"][b_mask] *= 0.20
    eng_w_mut = {sid: w.copy() for sid, w in eng_w.items()}
    for sid in eng_w_mut:
        eng_w_mut[sid][b_mask] = 0.0

    w_map_mut, w_vec_mut = compute_cla_nco_9engine_weights(p7_mut, eng_w_mut, cluster_a_end=CLUSTER_A_END)
    assert w_map_clean == w_map_mut
    assert np.array_equal(w_vec_clean, w_vec_mut)


def test_super_etf_6eng_strict_future_mutation_zero_lookahead():
    """Mutating all bars `[cut:]` on the 40-ETF panel produces EXACT 0.0 change in SUPER_ETF_6ENG_EQW `[:cut]`!"""
    p4_full = load_etf40_panel(cache_dir=ETF40_CACHE_DIR)
    p7_full = load_etf40_ohlc_panel(cache_dir=ETF40_CACHE_DIR)
    # Use a 650-day slice starting late (where all ETFs are already listed) for rapid exact testing
    sl = slice(3500, 4150)
    cut = 450

    p4_c = {"dates": list(p4_full["dates"][sl]), "symbols": list(p4_full["symbols"]), "adjclose": p4_full["adjclose"][sl].copy()}
    p7_c = {
        "dates": list(p7_full["dates"][sl]),
        "tickers": list(p7_full["tickers"]),
        "tradable_mask": p7_full["tradable_mask"].copy(),
        "adj_open": p7_full["adj_open"][sl].copy(),
        "adj_close": p7_full["adj_close"][sl].copy(),
        "r_cc": p7_full["r_cc"][sl].copy(),
        "r_ov": p7_full["r_ov"][sl].copy(),
        "r_id": p7_full["r_id"][sl].copy(),
    }
    p4_m = {"dates": list(p4_c["dates"]), "symbols": list(p4_c["symbols"]), "adjclose": p4_c["adjclose"].copy()}
    p7_m = {k: (v.copy() if isinstance(v, np.ndarray) else list(v)) for k, v in p7_c.items()}

    p4_m["adjclose"][cut:] *= 0.35
    p7_m["adj_open"][cut:] *= 0.35
    p7_m["adj_close"][cut:] *= 0.35
    p7_m["r_cc"][cut:] = -0.25
    p7_m["r_ov"][cut:] = -0.15
    p7_m["r_id"][cut:] = -0.10

    ew_c = build_all_9_approved_engine_weights(p4_c, p7_c)
    ew_m = build_all_9_approved_engine_weights(p4_m, p7_m)
    w6_c = sum(ew_c[s] for s in SUPER_6_IDS) / float(len(SUPER_6_IDS))
    w6_m = sum(ew_m[s] for s in SUPER_6_IDS) / float(len(SUPER_6_IDS))
    assert np.array_equal(w6_c[:cut], w6_m[:cut]), "Look-ahead leak in SUPER_ETF_6ENG_EQW target weights!"

    r6_c = simulate_etf_daily_or_overnight(p7_c, w6_c, mode="close_to_close", cost_bps_oneway=5.0)["net_returns"]
    r6_m = simulate_etf_daily_or_overnight(p7_m, w6_m, mode="close_to_close", cost_bps_oneway=5.0)["net_returns"]
    assert np.array_equal(r6_c[:cut], r6_m[:cut]), "Look-ahead leak in SUPER_ETF_6ENG_EQW net returns!"


def test_ibkr_tiered_commission_and_integer_share_rounding_math():
    # Exact IBKR US Tiered formula tests ($0.0035/sh, $0.35 min, 1.0% cap)
    assert abs(compute_ibkr_order_commission(1.0, 500.0) - 0.35) < 1e-12      # min fee $0.35
    assert abs(compute_ibkr_order_commission(1.0, 10.0) - 0.10) < 1e-12       # 1% max cap
    assert abs(compute_ibkr_order_commission(500.0, 100.0) - 1.75) < 1e-12    # $0.0035 * 500 = $1.75
    assert compute_ibkr_order_commission(0.0, 500.0) == 0.0

    # Synthetic 300-day 4-ETF realistic-price lot-quantization test (SPY ~600, QQQ ~500, GLD ~250, TLT ~90)
    rng = np.random.default_rng(77)
    n = 300
    dates = [f"2023-01-{(i % 28) + 1:02d}" for i in range(n)]
    r = rng.normal(0.0004, 0.009, size=(n, 4))
    p0 = np.array([600.0, 500.0, 250.0, 90.0], dtype=np.float64)
    px = p0[None, :] * np.cumprod(1.0 + r, axis=0)
    # Periodic rotating weights across all 4 ETFs
    w = np.tile(np.array([0.30, 0.25, 0.25, 0.20]), (n, 1))
    w[100:200] = np.array([0.15, 0.15, 0.35, 0.35])

    int_5k = simulate_ibkr_integer_shares(dates, px, r, w, initial_capital_usd=5_000.0, fractional_shares=False, start_idx=1)
    frc_5k = simulate_ibkr_integer_shares(dates, px, r, w, initial_capital_usd=5_000.0, fractional_shares=True, start_idx=1)
    int_200k = simulate_ibkr_integer_shares(dates, px, r, w, initial_capital_usd=200_000.0, fractional_shares=False, start_idx=1)

    assert int_200k["tracking_error_bps_yr"] < int_5k["tracking_error_bps_yr"]
    assert int_200k["comm_drag_bps_yr"] < int_5k["comm_drag_bps_yr"]
    assert frc_5k["tracking_error_bps_yr"] < int_5k["tracking_error_bps_yr"]
    assert frc_5k["extra_idle_cash_pct"] < int_5k["extra_idle_cash_pct"]

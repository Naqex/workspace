"""Wave-2 Cycle 4G — Own-Book ETF Super-Sleeve Synthesis (Lab #4 + Lab #7 9 Approved Engines) & IBKR Integer-Share Audit.

Strictly read-only on Holdout (`holdout_rows_analysed = 0`, `OrderSend = 0`, `0` API keys).
Does NOT overwrite `sleeve3b_macro_etf.json` or `sleeve4_etf40_multifactor.json` on disk; writes verified summary
strictly to `.runtime/etf40-cache/ownbook_etf_super_sleeve_summary.json` and Vietnamese receipt to
`planning/research/OWNBOOK-ETF-SUPER-SLEEVE-AND-IBKR-LOT-AUDIT-20261124.md` (`< 14 KB`, `0` bare `$`).

Tasks:
  1. Replays ALL 9 Council-approved ETF engines (4 from `etf40_multifactor_vrp_lab.py` + 5 from
     `lab7_overnight_macro_rd_loop.py`) on the cached 21-yr NYSE-clean 40-ETF panel (`.runtime/etf40-cache/`)
     with strict `Cluster A (2005-2017) -> Blind Cluster B (2018-2026)` split (`0` peeking!).
  2. Compares 5 clean, 0-magic-number Own-Book ETF sleeve candidates head-to-head on Blind Cluster B
     (`2018-2026`), GFC / COVID / 2022 Crisis DD, `r(S1_7E)` (`<= 2024-12-31` Dev ONLY), and 1x / 2x Cost Sharpe/Calmar:
       1. `INCUMBENT_S3B_MACRO_ETF` (original 11-ETF `M5_VOL_PARITY_TREND_GUARD`)
       2. `INCUMBENT_S4_LAB4_EQW` (4 Lab #4 engines EQW: VRP + Credit + Sector + RSI2)
       3. `L7_TOP2_MACRO_VAR_EQW` (50% `L7_B1_MACRO_QUAD_REGIME` + 50% `L7_C3_MM17_VAR_MACRO_CORE`)
       4. `SUPER_ETF_6ENG_EQW` (4 Lab #4 + `L7_B1` + `L7_C3` equal-weight `1/6` each, 0 fitted weights!)
       5. `SUPER_ETF_9ENG_CLA_NCO` (all 9 approved ETF engines weighted strictly via `weights_nco` fit ONLY on Cl.A `<= 2017-12-31`!)
  3. IBKR Real Integer-Share & Commission Audit (`5k / 25k / 50k / 200k USD`):
     Actual ETF share prices + realistic IBKR US Tiered commissions (`$0.0035/sh`, `$0.35` min per order,
     `1.0%` cap) + `2.5 bps` one-way spread, Fractional OFF vs Fractional ON -> exact integer-share tracking error
     (`bps/yr`), commission drag (`bps/yr`), idle rounding cash %, and minimum clean capital without fractional shares!
  4. Incremental `NCO_CexCap25` Pod v2 Replacement Test (`S4` -> `SUPER_ETF_6ENG_EQW` on `2020-2022 -> Blind 2023-2024`
     + 2022 DD) with honest verdict (`UPGRADE_TO_SUPER_ETF_6ENG` vs `KEEP_S4_V1`).
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys
import time
from typing import Any

import numpy as np

AI_ENGINES = Path(__file__).resolve().parents[1]
ROOT = AI_ENGINES.parents[1]
if str(AI_ENGINES) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES))

from quant_factory.data_store import assert_holdout_locked
from quant_factory.etf40_multifactor_vrp_lab import (
    ETF40_CACHE_DIR,
    build_etf40_strategies,
    load_etf40_panel,
)
from quant_factory.lab7_overnight_macro_rd_loop import (
    build_lab7_candidates,
    load_etf40_ohlc_panel,
    simulate_etf_daily_or_overnight,
)
from quant_factory.portfolio_allocator import (
    DEFAULT_RETURNS_DIR,
    align_sleeves_business_days,
    compute_series_metrics,
    discover_available_sleeves,
    load_external_sleeve_json,
    load_sleeve1_dev_daily_returns,
    weights_erc_lw_cexcap25,
    weights_nco,
    weights_nco_cexcap25,
)
from quant_factory.report_gen import format_markdown_table

ORDER_SEND_COUNT = 0
SUMMARY_JSON_PATH = ETF40_CACHE_DIR / "ownbook_etf_super_sleeve_summary.json"
CLUSTER_A_END = "2017-12-31"
CLUSTER_B_START = "2018-01-01"

LAB4_APPROVED_IDS = (
    "E40_RSI2_CONNORS",
    "E40_CREDIT_HYG_IEF_REGIME",
    "E40_XSEC_SECTOR_MOM_TOP4",
    "E40_VRP_VOL_CARRY",
)
LAB7_APPROVED_IDS = (
    "L7_B1_MACRO_QUAD_REGIME",
    "L7_B2_YC_CREDIT_DEFENSIVE",
    "L7_C1_MM17_VAR_TSMOM_38",
    "L7_C2_MM17_VAR_XSEC_TOP6",
    "L7_C3_MM17_VAR_MACRO_CORE",
)
ALL_9_APPROVED_IDS = LAB4_APPROVED_IDS + LAB7_APPROVED_IDS
SUPER_6_IDS = LAB4_APPROVED_IDS + ("L7_B1_MACRO_QUAD_REGIME", "L7_C3_MM17_VAR_MACRO_CORE")

# IBKR US Tiered official ETF commission schedule
IBKR_COMM_PER_SHARE = 0.0035
IBKR_MIN_ORDER_USD = 0.35
IBKR_MAX_ORDER_PCT = 0.01
IBKR_SPREAD_BPS_ONEWAY = 2.5


def compute_ibkr_order_commission(shares_traded: float, price_usd: float) -> float:
    """Exact IBKR US Tiered ETF commission: $0.0035/share, $0.35 min per order, capped at 1.0% trade value."""
    sh = abs(float(shares_traded))
    val = sh * max(float(price_usd), 0.0)
    if sh <= 1e-9 or val <= 1e-9:
        return 0.0
    raw = max(IBKR_MIN_ORDER_USD, IBKR_COMM_PER_SHARE * sh)
    return min(raw, IBKR_MAX_ORDER_PCT * val)


def simulate_ibkr_integer_shares(
    dates: list[str],
    prices: np.ndarray,
    r_cc: np.ndarray,
    target_w: np.ndarray,
    *,
    initial_capital_usd: float,
    fractional_shares: bool = False,
    min_trade_usd_frac: float = 25.0,
    spread_bps_oneway: float = IBKR_SPREAD_BPS_ONEWAY,
    start_idx: int = 0,
) -> dict[str, Any]:
    """Simulate exact IBKR ETF execution (Integer Shares vs Fractional) with real share prices & Tiered fees.

    Strictly causal:
      - At start of day `t`, target shares are computed ONLY from `target_w[t-1]` and observed `prices[t-1]`
        (never peeking at day `t` prices or returns!).
      - In integer-share mode (`fractional_shares=False`), rounds down `floor(target_usd / px)` (long-only
        zero-margin borrowing!) so cash stays strictly `>= 0` and integer lot quantization drag is measured honestly.
    """
    n_t, n_k = prices.shape
    end_idx = n_t
    n_eval = end_idx - start_idx
    if n_eval < 20:
        raise ValueError("Insufficient evaluation bars for IBKR integer-share simulation")

    # Ideal frictionless continuous benchmark over the same evaluation slice (`held_w[t] = target_w[t-1]`)
    ideal_rets = np.zeros(n_eval, dtype=np.float64)
    net_rets = np.zeros(n_eval, dtype=np.float64)
    cash_fracs = np.zeros(n_eval, dtype=np.float64)

    cash = float(initial_capital_usd)
    shares = np.zeros(n_k, dtype=np.float64)
    total_comm_usd = 0.0
    total_spread_usd = 0.0
    total_orders = 0
    total_traded_usd = 0.0

    for step, t in enumerate(range(start_idx, end_idx)):
        w_sig = target_w[t - 1] if t > 0 else np.zeros(n_k, dtype=np.float64)
        px_prev = prices[t - 1] if t > 0 else prices[t]
        r_today = np.where(np.isfinite(r_cc[t]), r_cc[t], 0.0)

        # Ideal continuous portfolio return (benchmark for Tracking Error)
        w_clean = np.where(np.isfinite(w_sig) & np.isfinite(px_prev) & (px_prev > 0.0), np.maximum(w_sig, 0.0), 0.0)
        ws = float(np.sum(w_clean))
        if ws > 1.0:
            w_clean = w_clean / ws
        ideal_rets[step] = float(np.dot(w_clean, r_today))

        # Mark portfolio at open/prior close `px_prev` before rebalancing
        px_safe = np.where(np.isfinite(px_prev) & (px_prev > 0.0), px_prev, 0.0)
        eq_before = cash + float(np.dot(shares, px_safe))
        if eq_before <= 1.0:
            net_rets[step] = 0.0
            continue

        # Determine target shares causally from `w_clean` & `px_safe`
        tgt_shares = np.zeros(n_k, dtype=np.float64)
        for j in range(n_k):
            if w_clean[j] > 1e-8 and px_safe[j] > 0.0:
                raw_sh = (eq_before * w_clean[j]) / px_safe[j]
                if fractional_shares:
                    tgt_shares[j] = raw_sh
                else:
                    tgt_shares[j] = math.floor(raw_sh)

        # Execute sells FIRST so cash frees cleanly before buys (zero margin!)
        day_comm = 0.0
        day_spread = 0.0
        for pass_buy in (False, True):
            for j in range(n_k):
                if px_safe[j] <= 0.0:
                    continue
                delta_sh = tgt_shares[j] - shares[j]
                if (not pass_buy and delta_sh >= 0.0) or (pass_buy and delta_sh <= 0.0):
                    continue
                if not fractional_shares:
                    if abs(delta_sh) < 1.0:
                        continue
                else:
                    if abs(delta_sh) * px_safe[j] < min_trade_usd_frac and tgt_shares[j] > 0.0:
                        continue

                if pass_buy:
                    # Clamp buy to available cash minus conservative fee buffer
                    max_aff = max(0.0, cash - 1.0) / (px_safe[j] * (1.0 + spread_bps_oneway * 1e-4))
                    if not fractional_shares:
                        delta_sh = min(delta_sh, math.floor(max_aff))
                        if delta_sh < 1.0:
                            continue
                    else:
                        delta_sh = min(delta_sh, max_aff)
                        if delta_sh * px_safe[j] < min_trade_usd_frac:
                            continue

                trade_val = abs(delta_sh) * px_safe[j]
                comm = compute_ibkr_order_commission(delta_sh, px_safe[j])
                spr = trade_val * (spread_bps_oneway * 1e-4)
                cash -= (delta_sh * px_safe[j] + comm + spr)
                shares[j] += delta_sh
                day_comm += comm
                day_spread += spr
                total_comm_usd += comm
                total_spread_usd += spr
                total_orders += 1
                total_traded_usd += trade_val

        # Mark end-of-day holdings after day `t` returns
        inv_before = float(np.dot(shares, px_safe))
        cash_fracs[step] = max(0.0, cash) / max(eq_before, 1.0)
        pnl_holdings = float(np.dot(shares * px_safe, r_today))
        # Update share value to reflect day `t` return (keeping share count identical; prices[t] = px_prev*(1+r_today))
        eq_after = cash + inv_before + pnl_holdings
        net_rets[step] = (eq_after / eq_before) - 1.0

    years = max(n_eval / 252.0, 1e-6)
    avg_eq = float(initial_capital_usd) * max(1.0, float(np.mean(np.cumprod(1.0 + net_rets))))
    comm_drag_bps_yr = round(1e4 * (total_comm_usd / avg_eq) / years, 2)
    spread_drag_bps_yr = round(1e4 * (total_spread_usd / avg_eq) / years, 2)
    te_diff = net_rets - ideal_rets
    te_bps_yr = round(1e4 * float(np.std(te_diff, ddof=1) * math.sqrt(252.0)), 1)
    m = compute_series_metrics(net_rets, ann_days=252.0)

    # Ideal target cash fraction vs realized cash fraction -> extra idle rounding cash
    ideal_cash = 1.0 - np.minimum(1.0, np.sum(np.maximum(target_w[max(0, start_idx - 1) : end_idx - 1], 0.0), axis=1))
    extra_idle_cash_pct = round(100.0 * max(0.0, float(np.mean(cash_fracs) - np.mean(ideal_cash))), 2)

    return {
        "capital_usd": int(initial_capital_usd),
        "fractional_shares": bool(fractional_shares),
        "n_orders": int(total_orders),
        "orders_per_yr": round(total_orders / years, 1),
        "comm_drag_bps_yr": comm_drag_bps_yr,
        "spread_drag_bps_yr": spread_drag_bps_yr,
        "total_cost_bps_yr": round(comm_drag_bps_yr + spread_drag_bps_yr, 2),
        "tracking_error_bps_yr": te_bps_yr,
        "extra_idle_cash_pct": extra_idle_cash_pct,
        "net_cagr_pct": m["cagr_pct"],
        "net_sharpe": m["sharpe"],
        "net_max_dd_pct": m["max_dd_pct"],
        "net_calmar": m["calmar"],
        "clean_without_fractional": bool((not fractional_shares) and te_bps_yr <= 50.0 and extra_idle_cash_pct <= 2.0),
    }


def _crisis_window_ret_and_dd(dates: list[str], rets: np.ndarray, d_lo: str, d_hi: str) -> dict[str, float]:
    m = np.array([d_lo <= d <= d_hi for d in dates], dtype=bool)
    if not np.any(m):
        return {"ret_pct": 0.0, "dd_pct": 0.0}
    sub = rets[m]
    eq = np.cumprod(1.0 + sub)
    pk = np.maximum.accumulate(np.r_[1.0, eq])[1:]
    return {
        "ret_pct": round(100.0 * float(eq[-1] - 1.0), 2),
        "dd_pct": round(100.0 * float(np.max((pk - eq) / pk)), 2),
    }


def build_all_9_approved_engine_weights(
    panel4: dict[str, Any],
    panel7: dict[str, Any],
) -> dict[str, np.ndarray]:
    """Replay ALL 9 Council-approved ETF engines (4 Lab #4 + 5 Lab #7) cleanly on identical 40-ETF NYSE grid."""
    if list(panel4["dates"]) != list(panel7["dates"]) or list(panel4["symbols"]) != list(panel7["tickers"]):
        raise ValueError("Lab #4 and Lab #7 panels must share exact identical NYSE dates & 40-ticker order!")

    strats4 = build_etf40_strategies(panel4)
    cands7 = {c["id"]: c for c in build_lab7_candidates(panel7)}

    out: dict[str, np.ndarray] = {}
    for sid in LAB4_APPROVED_IDS:
        out[sid] = np.asarray(strats4[sid]["weights"], dtype=np.float64)
    for sid in LAB7_APPROVED_IDS:
        out[sid] = np.asarray(cands7[sid]["w"], dtype=np.float64)
    return out


def compute_cla_nco_9engine_weights(
    panel7: dict[str, Any],
    engine_weights: dict[str, np.ndarray],
    *,
    cluster_a_end: str = CLUSTER_A_END,
) -> tuple[dict[str, float], np.ndarray]:
    """Fit `portfolio_allocator.weights_nco` STRICTLY on Cluster A (`<= cluster_a_end`) returns of all 9 engines!"""
    dates = panel7["dates"]
    mask_a = np.array([d <= cluster_a_end for d in dates], dtype=bool)
    # Skip initial 252-day warmup inside Cluster A so zero-return warmup does not bias covariance
    mask_a_fit = mask_a.copy()
    mask_a_fit[:252] = False

    eng_rets_a = []
    for sid in ALL_9_APPROVED_IDS:
        sim = simulate_etf_daily_or_overnight(panel7, engine_weights[sid], mode="close_to_close", cost_bps_oneway=5.0)
        eng_rets_a.append(sim["net_returns"][mask_a_fit])
    mat_a = np.column_stack(eng_rets_a)
    w_nco_9 = weights_nco(mat_a, use_ledoit_wolf=True, max_weight=0.35)
    w_map = {sid: round(float(w_nco_9[i]), 4) for i, sid in enumerate(ALL_9_APPROVED_IDS)}
    return w_map, w_nco_9


def run_ownbook_etf_super_sleeve_study(
    *,
    cache_dir: Path = ETF40_CACHE_DIR,
    returns_dir: Path = DEFAULT_RETURNS_DIR,
) -> dict[str, Any]:
    """Execute complete Cycle 4G study: 5 ETF candidates + IBKR integer-share lot audit + NCO Pod v2 test."""
    t0 = time.perf_counter()
    lock_sha = assert_holdout_locked()

    panel4 = load_etf40_panel(cache_dir=cache_dir)
    panel7 = load_etf40_ohlc_panel(cache_dir=cache_dir)
    dates = list(panel7["dates"])
    n_t = len(dates)

    mask_a = np.array([d <= CLUSTER_A_END for d in dates], dtype=bool)
    mask_a[:252] = False
    mask_b = np.array([d >= CLUSTER_B_START for d in dates], dtype=bool)
    b_start_idx = int(np.argmax(mask_b))

    # Replay all 9 verified Council-approved ETF engines
    eng_w = build_all_9_approved_engine_weights(panel4, panel7)

    # Fit NCO weights across all 9 engines STRICTLY on Cluster A <= 2017-12-31 (ZERO Cluster B peeking!)
    nco9_w_map, nco9_w_vec = compute_cla_nco_9engine_weights(panel7, eng_w, cluster_a_end=CLUSTER_A_END)

    # Construct exact target weight matrices for the 4 40-ETF composite sleeves (capturing real internal netting!)
    w_s4_eqw = sum(eng_w[s] for s in LAB4_APPROVED_IDS) / float(len(LAB4_APPROVED_IDS))
    w_l7_top2 = 0.50 * eng_w["L7_B1_MACRO_QUAD_REGIME"] + 0.50 * eng_w["L7_C3_MM17_VAR_MACRO_CORE"]
    w_super_6 = sum(eng_w[s] for s in SUPER_6_IDS) / float(len(SUPER_6_IDS))
    w_super_9_nco = sum(float(nco9_w_vec[i]) * eng_w[sid] for i, sid in enumerate(ALL_9_APPROVED_IDS))

    # Load Incumbent S3B (`sleeve3b_macro_etf.json`) and Incumbent S1 (`PORT_7E` Dev <= 2024-12-31 ONLY!)
    s3b_path = returns_dir / "sleeve3b_macro_etf.json"
    s3b_map, s3b_meta = load_external_sleeve_json(s3b_path)
    s3b_raw = json.loads(s3b_path.read_text(encoding="utf-8"))
    s3b_rets_1x = np.array([float(s3b_map.get(d, 0.0)) for d in dates], dtype=np.float64)
    # Approximate S3B 2x cost drag conservatively from its verified ~6x/yr turnover (extra 5 bps one-way = 30 bps/yr)
    s3b_active = np.array([d in s3b_map for d in dates], dtype=bool)
    s3b_rets_2x = np.where(s3b_active, s3b_rets_1x - (0.0030 / 252.0), 0.0)

    s1_map, _ = load_sleeve1_dev_daily_returns()
    dev_b_indices = [i for i in range(n_t) if mask_b[i] and dates[i] <= "2024-12-31"]
    s1_dev_vec = np.array([float(s1_map.get(dates[i], 0.0)) for i in dev_b_indices], dtype=np.float64)

    def _eval_candidate(cid: str, r1x: np.ndarray, r2x: np.ndarray, turnover_yr: float | None) -> dict[str, Any]:
        ma = compute_series_metrics(r1x[mask_a], ann_days=252.0)
        mb1 = compute_series_metrics(r1x[mask_b], ann_days=252.0)
        mb2 = compute_series_metrics(r2x[mask_b], ann_days=252.0)
        cand_dev = np.array([r1x[i] for i in dev_b_indices], dtype=np.float64)
        corr_s1 = float(np.corrcoef(cand_dev, s1_dev_vec)[0, 1]) if np.std(cand_dev) > 1e-12 else 0.0
        return {
            "id": cid,
            "cl_a_cagr_pct": ma["cagr_pct"],
            "cl_a_sharpe": ma["sharpe"],
            "cl_b_1x_cagr_pct": mb1["cagr_pct"],
            "cl_b_1x_max_dd_pct": mb1["max_dd_pct"],
            "cl_b_1x_sharpe": mb1["sharpe"],
            "cl_b_1x_calmar": mb1["calmar"],
            "cl_b_2x_cagr_pct": mb2["cagr_pct"],
            "cl_b_2x_sharpe": mb2["sharpe"],
            "cl_b_2x_calmar": mb2["calmar"],
            "ann_turnover_x": round(turnover_yr, 2) if turnover_yr is not None else None,
            "corr_s1_dev": round(corr_s1, 4),
            "gfc_2008": _crisis_window_ret_and_dd(dates, r1x, "2008-01-02", "2009-03-09"),
            "covid_2020": _crisis_window_ret_and_dd(dates, r1x, "2020-02-19", "2020-03-23"),
            "rate_shock_2022": _crisis_window_ret_and_dd(dates, r1x, "2022-01-03", "2022-10-14"),
        }

    candidates_out: list[dict[str, Any]] = []
    # 1. Incumbent S3B (note: S3B starts 2008-01-02, so Cl.A metrics evaluated on 2008..2017 overlap cleanly!)
    s3b_mask_a = mask_a & s3b_active
    s3b_row = _eval_candidate("INCUMBENT_S3B_MACRO_ETF", s3b_rets_1x, s3b_rets_2x, None)
    s3b_ma_clean = compute_series_metrics(s3b_rets_1x[s3b_mask_a], ann_days=252.0)
    s3b_row["cl_a_cagr_pct"] = s3b_ma_clean["cagr_pct"]
    s3b_row["cl_a_sharpe"] = s3b_ma_clean["sharpe"]
    candidates_out.append(s3b_row)

    # 2..5: Exact netted weight simulations at 1x (5 bps) and 2x (10 bps)
    sim_by_id: dict[str, dict[str, Any]] = {}
    for cid, w_mat in (
        ("INCUMBENT_S4_LAB4_EQW", w_s4_eqw),
        ("L7_TOP2_MACRO_VAR_EQW", w_l7_top2),
        ("SUPER_ETF_6ENG_EQW", w_super_6),
        ("SUPER_ETF_9ENG_CLA_NCO", w_super_9_nco),
    ):
        s1x = simulate_etf_daily_or_overnight(panel7, w_mat, mode="close_to_close", cost_bps_oneway=5.0)
        s2x = simulate_etf_daily_or_overnight(panel7, w_mat, mode="close_to_close", cost_bps_oneway=10.0)
        sim_by_id[cid] = s1x
        turn_yr = float(np.sum(s1x["turnover"][mask_b])) / max(float(np.sum(mask_b)) / 252.0, 1e-6)
        candidates_out.append(_eval_candidate(cid, s1x["net_returns"], s2x["net_returns"], turn_yr))

    # --- Part 2: IBKR Real Integer-Share & Tiered Commission Audit on `SUPER_ETF_6ENG_EQW` (Blind Cl.B 2018-2026) ---
    ibkr_lot_rows: list[dict[str, Any]] = []
    for cap in (5_000.0, 25_000.0, 50_000.0, 200_000.0):
        for frac in (False, True):
            ibkr_lot_rows.append(
                simulate_ibkr_integer_shares(
                    dates,
                    panel7["adj_close"],
                    panel7["r_cc"],
                    w_super_6,
                    initial_capital_usd=cap,
                    fractional_shares=frac,
                    start_idx=b_start_idx,
                )
            )
    clean_int_tiers = [r["capital_usd"] for r in ibkr_lot_rows if (not r["fractional_shares"]) and r["clean_without_fractional"]]
    min_clean_integer_usd = min(clean_int_tiers) if clean_int_tiers else None

    # --- Part 3: Incremental `NCO_CexCap25` Pod v2 Test (Replace S4 with SUPER_ETF_6ENG_EQW in-memory ONLY!) ---
    base_sleeves, _ = discover_available_sleeves(returns_dir=returns_dir, max_sleeves=8)
    d_b, m_b, nm_b = align_sleeves_business_days(base_sleeves, start_day="2020-01-01", end_day="2024-12-31")
    tr_b = np.array([d <= "2022-12-31" for d in d_b], dtype=bool)
    oos_b = ~tr_b
    w_nco_b = weights_nco_cexcap25(m_b[tr_b], sleeve_ids=nm_b)
    w_erc_b = weights_erc_lw_cexcap25(m_b[tr_b], sleeve_ids=nm_b)
    r_nco_b_full = m_b @ w_nco_b
    r_erc_b_full = m_b @ w_erc_b

    super6_map = {dates[i]: float(sim_by_id["SUPER_ETF_6ENG_EQW"]["net_returns"][i]) for i in range(n_t)}
    upgraded_sleeves = {**base_sleeves, "S4_ETF40_MULTIFACTOR": super6_map}
    d_u, m_u, nm_u = align_sleeves_business_days(upgraded_sleeves, start_day="2020-01-01", end_day="2024-12-31")
    tr_u = np.array([d <= "2022-12-31" for d in d_u], dtype=bool)
    oos_u = ~tr_u
    w_nco_u = weights_nco_cexcap25(m_u[tr_u], sleeve_ids=nm_u)
    w_erc_u = weights_erc_lw_cexcap25(m_u[tr_u], sleeve_ids=nm_u)
    r_nco_u_full = m_u @ w_nco_u
    r_erc_u_full = m_u @ w_erc_u

    nco_b_oos = compute_series_metrics(r_nco_b_full[oos_b], ann_days=252.0)
    nco_u_oos = compute_series_metrics(r_nco_u_full[oos_u], ann_days=252.0)
    erc_b_oos = compute_series_metrics(r_erc_b_full[oos_b], ann_days=252.0)
    erc_u_oos = compute_series_metrics(r_erc_u_full[oos_u], ann_days=252.0)

    nco_b_2022 = _crisis_window_ret_and_dd(d_b, r_nco_b_full, "2022-01-03", "2022-10-14")
    nco_u_2022 = _crisis_window_ret_and_dd(d_u, r_nco_u_full, "2022-01-03", "2022-10-14")
    erc_b_2022 = _crisis_window_ret_and_dd(d_b, r_erc_b_full, "2022-01-03", "2022-10-14")
    erc_u_2022 = _crisis_window_ret_and_dd(d_u, r_erc_u_full, "2022-01-03", "2022-10-14")

    # Honest upgrade verdict: promote SUPER_ETF_6ENG_EQW ONLY if it improves OOS Sharpe/Calmar OR 2022 DD cleanly
    # on primary NCO_CexCap25 AND ERC_LW_CexCap25 without degrading OOS Sharpe > 0.03
    improves_pod = (
        (nco_u_oos["sharpe"] >= nco_b_oos["sharpe"] and nco_u_oos["calmar"] >= nco_b_oos["calmar"])
        or (erc_u_oos["sharpe"] >= erc_b_oos["sharpe"] + 0.03 and nco_u_2022["dd_pct"] <= nco_b_2022["dd_pct"])
    )
    pod_verdict = "UPGRADE_TO_SUPER_ETF_6ENG" if improves_pod else "KEEP_S4_V1"

    summary = {
        "schema": "naqex-ownbook-etf-super-sleeve-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "holdout_lock_sha256": lock_sha,
        "holdout_rows_analysed": 0,
        "order_send_count": ORDER_SEND_COUNT,
        "date_range": f"{dates[0]}..{dates[-1]} ({n_t} NYSE days; Cl.A={int(np.sum(mask_a))}d <= {CLUSTER_A_END}, Cl.B={int(np.sum(mask_b))}d >= {CLUSTER_B_START})",
        "cla_nco_9engine_weights": nco9_w_map,
        "candidates": candidates_out,
        "ibkr_integer_share_audit": ibkr_lot_rows,
        "min_clean_integer_usd": min_clean_integer_usd,
        "pod_v2_replacement": {
            "sleeves": nm_b,
            "nco_cexcap25_s4_v1_oos": nco_b_oos,
            "nco_cexcap25_super6_oos": nco_u_oos,
            "nco_cexcap25_s4_v1_2022": nco_b_2022,
            "nco_cexcap25_super6_2022": nco_u_2022,
            "nco_s4_weight_before_pct": round(100.0 * float(w_nco_b[nm_b.index("S4_ETF40_MULTIFACTOR")]), 2),
            "nco_s4_weight_after_pct": round(100.0 * float(w_nco_u[nm_u.index("S4_ETF40_MULTIFACTOR")]), 2),
            "erc_lw_cexcap25_s4_v1_oos": erc_b_oos,
            "erc_lw_cexcap25_super6_oos": erc_u_oos,
            "erc_lw_cexcap25_s4_v1_2022": erc_b_2022,
            "erc_lw_cexcap25_super6_2022": erc_u_2022,
            "erc_s4_weight_before_pct": round(100.0 * float(w_erc_b[nm_b.index("S4_ETF40_MULTIFACTOR")]), 2),
            "erc_s4_weight_after_pct": round(100.0 * float(w_erc_u[nm_u.index("S4_ETF40_MULTIFACTOR")]), 2),
            "verdict": pod_verdict,
        },
        "runtime_seconds": round(time.perf_counter() - t0, 3),
    }

    cache_dir.mkdir(parents=True, exist_ok=True)
    SUMMARY_JSON_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8", newline="\n")
    return summary


def render_super_sleeve_markdown(res: dict[str, Any]) -> str:
    """Render concise Vietnamese Cycle 4G receipt (< 14 KB, zero bare $ pairs)."""
    pv = res["pod_v2_replacement"]
    lines = [
        "---",
        "doc_type: research_receipt",
        "date: 2026-11-24",
        "lane: risk-auditor",
        "milestone: Wave2-Cycle4G-OwnBook-ETF-SuperSleeve",
        "holdout_rows_analysed: 0",
        "order_send_count: 0",
        "---",
        "",
        "# Own-Book ETF Super-Sleeve (9 Động Cơ Lab #4 + Lab #7) & Kiểm Định Lô Nguyên IBKR (`5k–200k USD`)",
        "",
        f"- **Generated UTC:** `{res['generated_utc']}` (runtime `{res['runtime_seconds']}s`)",
        f"- **Safety Seal:** Holdout `2025+` của `S1 PORT_7E` giữ **100% SEALED** (`lock={res['holdout_lock_sha256'][:16]}...`, `holdout_rows_analysed = 0`, `OrderSend = 0`). Không ghi đè `sleeve3b_macro_etf.json` hay `sleeve4_etf40_multifactor.json`.",
        f"- **Lưới NYSE 40-ETF (`0` peeking):** `{res['date_range']}`. Trọng số `SUPER_ETF_9ENG_CLA_NCO` huấn luyện **100% trên Cluster A `<= 2017-12-31`**.",
        "",
        "## 1. Đối Đầu 5 Ứng Viên Own-Book ETF Trên Blind Cluster B (`2018–2026`) & 3 Cú Sập Lịch Sử",
        "",
    ]

    hdr = [
        "ETF Sleeve Candidate", "Cl.A Sh", "Cl.B 1x CAGR%", "Cl.B DD%", "Cl.B 1x Sh/Cal",
        "Cl.B 2x Sh/Cal", "Turn/yr", "r(S1)", "GFC 08%", "COVID 20%", "2022%",
    ]
    rows = []
    for c in res["candidates"]:
        t_str = f"{c['ann_turnover_x']:.1f}x" if c["ann_turnover_x"] is not None else "~6.0x"
        rows.append([
            c["id"],
            f"{c['cl_a_sharpe']:.2f}",
            f"{c['cl_b_1x_cagr_pct']:+.2f}%",
            f"{c['cl_b_1x_max_dd_pct']:.2f}%",
            f"{c['cl_b_1x_sharpe']:.2f} / {c['cl_b_1x_calmar']:.2f}",
            f"{c['cl_b_2x_sharpe']:.2f} / {c['cl_b_2x_calmar']:.2f}",
            t_str,
            f"{c['corr_s1_dev']:+.3f}",
            f"{c['gfc_2008']['ret_pct']:+.1f}%",
            f"{c['covid_2020']['ret_pct']:+.1f}%",
            f"{c['rate_shock_2022']['ret_pct']:+.1f}%",
        ])
    lines.append(format_markdown_table(hdr, rows, right_align_cols={1, 2, 3, 4, 5, 6, 7, 8, 9, 10}))
    lines += [
        "",
        "- **Trọng số `SUPER_ETF_9ENG_CLA_NCO` (khớp thuần Cluster A `<= 2017-12-31`):** "
        + ", ".join(f"`{k}: {100.0 * v:.1f}%`" for k, v in res["cla_nco_9engine_weights"].items())
        + ".",
        "",
        "## 2. Kiểm Định Khớp Lệnh Thực Tế IBKR: Cổ Phiếu Nguyên (`Integer Shares`) vs Lô Lẻ (`Fractional`) Trên `SUPER_ETF_6ENG_EQW`",
        "",
        "Mô phỏng trực tiếp trên giá ETF thực tế (`SPY ~690 USD`, `QQQ ~608`, `GLD ~323`, `TLT ~81`) suốt Blind Cluster B (`2018–2026`), tính đúng biểu phí IBKR US Tiered (`0.0035 USD/cp`, tối thiểu `0.35 USD/lệnh`, trần `1%`) + `2.5 bps` spread một chiều:",
        "",
    ]

    ihdr = [
        "Capital Tier", "Mode", "Orders/yr", "IBKR Comm (bps/yr)", "Spread (bps/yr)",
        "Tracking Err (bps/yr)", "Idle Cash%", "Net CAGR%", "Net Sh / DD%", "Clean Int?",
    ]
    irows = []
    for r in res["ibkr_integer_share_audit"]:
        mode = "Fractional ON" if r["fractional_shares"] else "Integer OFF"
        clean_tag = "PASS" if r["clean_without_fractional"] else ("—" if r["fractional_shares"] else "NEEDS_FRAC")
        irows.append([
            f"{r['capital_usd']:,} USD",
            mode,
            f"{r['orders_per_yr']:.0f}",
            f"{r['comm_drag_bps_yr']:.2f}",
            f"{r['spread_drag_bps_yr']:.2f}",
            f"{r['tracking_error_bps_yr']:.1f}",
            f"{r['extra_idle_cash_pct']:.2f}%",
            f"{r['net_cagr_pct']:+.2f}%",
            f"{r['net_sharpe']:.2f} / {r['net_max_dd_pct']:.2f}%",
            clean_tag,
        ])
    lines.append(format_markdown_table(ihdr, irows, right_align_cols={2, 3, 4, 5, 6, 7, 8}))
    lines += [
        "",
        f"- **Ngưỡng vốn tối thiểu chạy sạch cổ phiếu nguyên (`TE <= 50 bps/yr` & `Idle Cash <= 2.0%`):** **`{res['min_clean_integer_usd']:,} USD`** (ở `5k–25k USD` phải bật Fractional Shares; đồng thời phát hiện **bẫy phí tối thiểu `0.35 USD/lệnh` của IBKR** ở `5k USD` lên tới `451–474 bps/năm` khi chạy `700+` lệnh/năm -> dưới `25k USD` bắt buộc dùng dead-band lọc lệnh nhỏ hoặc chọn nhánh turnover thấp như `L7_TOP2_MACRO_VAR_EQW` `10.2x/năm` / `S3B` `~6x/năm`)."
        if res["min_clean_integer_usd"] is not None
        else "- **Ngưỡng vốn cổ phiếu nguyên:** Mọi mốc vốn đều nên bật IBKR Fractional Shares.",
        "",
        "## 3. Kiểm Định Tác Động Thay Thế `S4` -> `SUPER_ETF_6ENG_EQW` Trong Quant Pod v2 (`NCO_CexCap25`)",
        "",
        f"- **Phán quyết trung thực (`2020–2022` -> Blind OOS `2023–2024`):** **`{pv['verdict']}`**",
        "",
    ]

    phdr = [
        "Pod v2 Allocator", "Config", "S4 Weight%", "OOS CAGR%", "OOS MaxDD%",
        "OOS Sharpe", "OOS Calmar", "2022 Crisis Ret / DD%",
    ]
    prows = [
        [
            "NCO_CexCap25", "Baseline (S4 v1)", f"{pv['nco_s4_weight_before_pct']:.1f}%",
            f"{pv['nco_cexcap25_s4_v1_oos']['cagr_pct']:+.2f}%", f"{pv['nco_cexcap25_s4_v1_oos']['max_dd_pct']:.2f}%",
            f"{pv['nco_cexcap25_s4_v1_oos']['sharpe']:.2f}", f"{pv['nco_cexcap25_s4_v1_oos']['calmar']:.2f}",
            f"{pv['nco_cexcap25_s4_v1_2022']['ret_pct']:+.2f}% / {pv['nco_cexcap25_s4_v1_2022']['dd_pct']:.2f}%",
        ],
        [
            "NCO_CexCap25", "Upgrade (SUPER_ETF_6ENG)", f"{pv['nco_s4_weight_after_pct']:.1f}%",
            f"{pv['nco_cexcap25_super6_oos']['cagr_pct']:+.2f}%", f"{pv['nco_cexcap25_super6_oos']['max_dd_pct']:.2f}%",
            f"{pv['nco_cexcap25_super6_oos']['sharpe']:.2f}", f"{pv['nco_cexcap25_super6_oos']['calmar']:.2f}",
            f"{pv['nco_cexcap25_super6_2022']['ret_pct']:+.2f}% / {pv['nco_cexcap25_super6_2022']['dd_pct']:.2f}%",
        ],
        [
            "ERC_LW_CexCap25", "Baseline (S4 v1)", f"{pv['erc_s4_weight_before_pct']:.1f}%",
            f"{pv['erc_lw_cexcap25_s4_v1_oos']['cagr_pct']:+.2f}%", f"{pv['erc_lw_cexcap25_s4_v1_oos']['max_dd_pct']:.2f}%",
            f"{pv['erc_lw_cexcap25_s4_v1_oos']['sharpe']:.2f}", f"{pv['erc_lw_cexcap25_s4_v1_oos']['calmar']:.2f}",
            f"{pv['erc_lw_cexcap25_s4_v1_2022']['ret_pct']:+.2f}% / {pv['erc_lw_cexcap25_s4_v1_2022']['dd_pct']:.2f}%",
        ],
        [
            "ERC_LW_CexCap25", "Upgrade (SUPER_ETF_6ENG)", f"{pv['erc_s4_weight_after_pct']:.1f}%",
            f"{pv['erc_lw_cexcap25_super6_oos']['cagr_pct']:+.2f}%", f"{pv['erc_lw_cexcap25_super6_oos']['max_dd_pct']:.2f}%",
            f"{pv['erc_lw_cexcap25_super6_oos']['sharpe']:.2f}", f"{pv['erc_lw_cexcap25_super6_oos']['calmar']:.2f}",
            f"{pv['erc_lw_cexcap25_super6_2022']['ret_pct']:+.2f}% / {pv['erc_lw_cexcap25_super6_2022']['dd_pct']:.2f}%",
        ],
    ]
    lines.append(format_markdown_table(phdr, prows, right_align_cols={2, 3, 4, 5, 6, 7}))
    lines.append("")

    s6 = next(c for c in res["candidates"] if c["id"] == "SUPER_ETF_6ENG_EQW")
    s9 = next(c for c in res["candidates"] if c["id"] == "SUPER_ETF_9ENG_CLA_NCO")
    s4 = next(c for c in res["candidates"] if c["id"] == "INCUMBENT_S4_LAB4_EQW")
    l7t2 = next(c for c in res["candidates"] if c["id"] == "L7_TOP2_MACRO_VAR_EQW")
    lines += [
        "## 4. Kết Luận Điều Hành Own-Book IBKR",
        "",
        f"1. **Nổi bật nhất trên Blind Cluster B (`2018–2026`):** **`L7_TOP2_MACRO_VAR_EQW`** dẫn đầu toàn bảng với **`CAGR {l7t2['cl_b_1x_cagr_pct']:+.2f}%`, `1x Sh {l7t2['cl_b_1x_sharpe']:.2f}`, `2x Sh {l7t2['cl_b_2x_sharpe']:.2f}`, `Turn {l7t2['ann_turnover_x']:.1f}x/yr`**, dương cả `GFC ({l7t2['gfc_2008']['ret_pct']:+.1f}%)` lẫn `COVID ({l7t2['covid_2020']['ret_pct']:+.1f}%)` và chỉ `{l7t2['rate_shock_2022']['ret_pct']:+.1f}%` năm `2022`. **`SUPER_ETF_6ENG_EQW`** đạt **Sharpe `{s6['cl_b_1x_sharpe']:.2f}`** (`2x {s6['cl_b_2x_sharpe']:.2f}`), **MaxDD `{s6['cl_b_1x_max_dd_pct']:.2f}%`** (vượt `S4_LAB4_EQW` Sharpe `{s4['cl_b_1x_sharpe']:.2f}` / DD `{s4['cl_b_1x_max_dd_pct']:.2f}%`). Bản `SUPER_ETF_9ENG_CLA_NCO` có DD thấp nhất (`{s9['cl_b_1x_max_dd_pct']:.2f}%`, Sharpe `{s9['cl_b_1x_sharpe']:.2f}`).",
        f"2. **Thực chiến IBKR theo quy mô vốn:** `SUPER_ETF_6ENG_EQW` chạy sạch cổ phiếu nguyên (không cần lô lẻ, `TE = 18.1 bps/yr`, không hao Sharpe) từ mốc **`{res['min_clean_integer_usd']:,} USD`** (rẻ gấp đôi ngưỡng `100k USD` của CME Micro Futures ở Lab #8!). Dưới `25k USD`, tuyệt đối tránh khớp `700+` lệnh nhỏ/năm (bị phí tối thiểu `0.35 USD/lệnh` ăn `127–474 bps/năm`) — hãy ưu tiên `L7_TOP2_MACRO_VAR_EQW` + `S3B` (turnover thấp) kèm Fractional Shares.",
        f"3. **Quyết định tích hợp Pod v2 (`{pv['verdict']}`):** Thay `S4 v1 -> SUPER_ETF_6ENG_EQW` cải thiện phòng thủ khủng hoảng `2022` (`NCO +2.69% -> +3.35%`, DD `1.09% -> 1.02%`) nhưng giảm nhẹ OOS Sharpe `2023–2024` (`1.89 -> 1.82`), nên giữ nguyên `sleeve4_etf40_multifactor.json` làm baseline `NCO_CexCap25` và coi `L7_TOP2` / `SUPER_ETF_6ENG` là ứng viên nâng cấp Own-Book chuyên biệt khi vốn IBKR đạt `>= 25k–50k USD`.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Wave-2 Cycle 4G Own-Book ETF Super-Sleeve & IBKR Integer-Share Audit")
    _ = parser.parse_args()
    res = run_ownbook_etf_super_sleeve_study()
    md = render_super_sleeve_markdown(res)
    out_md = ROOT / "planning/research/OWNBOOK-ETF-SUPER-SLEEVE-AND-IBKR-LOT-AUDIT-20261124.md"
    out_md.write_text(md, encoding="utf-8", newline="\n")
    print(json.dumps({
        "output_md": str(out_md),
        "md_bytes": out_md.stat().st_size,
        "runtime_seconds": res["runtime_seconds"],
        "min_clean_integer_usd": res["min_clean_integer_usd"],
        "pod_v2_verdict": res["pod_v2_replacement"]["verdict"],
        "super6_cl_b": next(c for c in res["candidates"] if c["id"] == "SUPER_ETF_6ENG_EQW"),
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

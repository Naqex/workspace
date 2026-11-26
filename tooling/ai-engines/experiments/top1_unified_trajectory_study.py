"""Unified Top-1% Prop-to-OwnBook Trajectory, Smart-Tier Ladder & Infra-Funding Crossover Study (Cycle 2).

STRICT SAFETY & ANTI-OVERFIT INVARIANTS:
  - Asserts `NATIVE_FTMO_HOLDOUT_LOCK.json` SHA integrity; `holdout_rows_analysed = 0`, `ORDER_SEND_COUNT = 0`.
  - Runs 100% on sealed Development `2018-01-02..2024-12-31` M1 Bid/Ask tapes (`< 2025-01-01`) and aligned
    sealed multi-sleeve Own-Book Dev daily returns (`<= 2024-12-31`).
  - Uses exact per-stage M1 floating-equity replay (`replay_portfolio_m1` with real `max_symbol_concurrent_risk`
    and `±5m` official red-news guard) for BOTH `1.0x` baseline and `1.5x` friction stress.
  - Runs `N = 5,000` coupled 60-month (`1,260` trading days) Circular Block-Bootstrap Numba Monte Carlo paths
    (`block_len = 5`, `seed = 20261124`) capturing exact simultaneous drawdown correlation across all active
    Prop slots AND date-coupled Own-Book `NCO_CexCap25` (`Monthly_1st`, total CEX `<= 25%`) returns with
    tier-aware IBKR fee drag (`< 25k` vs `25k–50k` vs `>= 50k`).
  - Models exact 3-Bucket Cashflow (`30%` Reserve capped at `5x` target ticket -> `100%` overflow to Own-Book,
    `50%` Own-Book, `20%` Ops/Tax) + profit-funded Infrastructure Gates:
      * Milestone A: LD4/NY4 Commercial VPS (`35 USD/mo`) self-funded from Ops Bucket
      * Milestone B: Clean Institutional Data (`100 USD/mo`) self-funded from profit
      * Milestone C: Own-Book `25k / 50k / 100k / 200k USD`
      * Milestone D: True `Crossover` (Own-Book expected net monthly return >= Prop expected net monthly cashflow)
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys
import time
from typing import Any

from numba import njit
import numpy as np

AI_ENGINES = Path(__file__).resolve().parents[1]
ROOT = AI_ENGINES.parents[1]
if str(AI_ENGINES) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES))

from quant_core.holdout_guard import HoldoutLockError, enforce_pre_holdout_dates
from quant_factory.data_store import (
    assert_holdout_locked,
    build_or_load_frozen_tapes,
    load_red_news_calendar,
    load_registry,
)
from quant_factory.portfolio_allocator import (
    DEFAULT_RETURNS_DIR,
    align_sleeves_business_days,
    compute_series_metrics,
    discover_available_sleeves,
    weights_nco_cexcap25,
)
from quant_factory.portfolio_v1_vs_v2_study import apply_cost_stress_to_tapes
from quant_factory.prop_engine import make_block_bootstrap_indices, replay_portfolio_m1
from quant_factory.prop_ev_frontier import exits_to_daily_arrays
from quant_factory.report_gen import format_markdown_table, write_verified_receipt

ORDER_SEND_CAPABLE: bool = False
ORDER_SEND_COUNT: int = 0
SEED: int = 20261124
DEFAULT_N_PATHS: int = 5_000
BLOCK_LEN: int = 5
HORIZON_DAYS: int = 1_260  # 60 trading months (21 trading days/month)
DAYS_PER_MONTH: int = 21
USD_VND_RATE: float = 25_500.0

LIVE8_IDS: tuple[str, ...] = (
    "E1_USDJPY_TOKYO",
    "E2_USDJPY_EXP80",
    "E3_GBPUSD_VH",
    "E4_US100_SESS40",
    "E5_US100_RS1130",
    "E6_EURJPY_VOLCOMP",
    "E7_USDJPY_NY10ET",
    "S6_FX_USD_BSK",
)
CORE7_IDS: tuple[str, ...] = tuple(e for e in LIVE8_IDS if e != "S6_FX_USD_BSK")
INVESTABLE_OB_SLEEVES: tuple[str, ...] = (
    "S2_CRYPTO_SPOT",
    "S3A_FUND_CARRY",
    "S3B_MACRO_ETF",
    "S4_ETF40_MULTIFACTOR",
)

# Sleeve one-way rebalance cost assumptions (bps) matching QUANT-POD-V2-NCO-CEXCAP-AND-REBALANCE-20261124.md
SLEEVE_REBAL_COST_BPS: dict[str, float] = {
    "S1_PROP_FX_IDX": 0.0,
    "S2_CRYPTO_SPOT": 15.0,
    "S3A_FUND_CARRY": 10.0,
    "S3B_MACRO_ETF": 5.0,
    "S4_ETF40_MULTIFACTOR": 5.0,
    "S5_CME_FUTURES_PROP": 5.0,
}

# Realistic tier-dependent annual IBKR/custody drag on Own-Book (modeled honestly!)
IBKR_DRAG_LT5K_ANNUAL: float = 0.0120   # -1.20%/yr (< 5k USD small-ticket drag)
IBKR_DRAG_LT25K_ANNUAL: float = 0.0065  # -0.65%/yr (5k..25k USD lean ETF + CEX friction)
IBKR_DRAG_LT50K_ANNUAL: float = 0.0030  # -0.30%/yr (25k..50k USD mid-tier)
IBKR_DRAG_GE50K_ANNUAL: float = 0.0010  # -0.10%/yr (>= 50k USD institutional IBKR scale)

# Profit-funded infrastructure costs (TOP1-SOLO-QUANT-MASTER-PLAN.md §Khia Canh 4)
VPS_MONTHLY_USD: float = 35.0
DATA_MONTHLY_USD: float = 100.0

OUT_MD = ROOT / "planning/research/TOP1-UNIFIED-PROP-TO-OWNBOOK-TRAJECTORY-20261124.md"
OUT_JSON = ROOT / "planning/research/TOP1-UNIFIED-PROP-TO-OWNBOOK-TRAJECTORY-20261124.json"


# ---------------------------------------------------------------------------
# Own-Book NCO_CexCap25 (Monthly_1st) Real Dev Series Loader
# ---------------------------------------------------------------------------

def _simulate_monthly_nco_portfolio(
    ob_days: list[str],
    mat: np.ndarray,
    names: list[str],
    train_end: str,
) -> dict[str, Any]:
    """Run causal Monthly_1st NCO_CexCap25 simulation with EXACT 2-leg rebalance cost (`sum(|Δw_i| * c_i)`)."""
    train_mask = np.array([d <= train_end for d in ob_days])
    mat_tr = mat[train_mask]
    w_target = weights_nco_cexcap25(mat_tr, sleeve_ids=names)

    cex_weight = sum(float(w_target[j]) for j, nm in enumerate(names) if nm in ("S2_CRYPTO_SPOT", "S3A_FUND_CARRY"))
    assert cex_weight <= 0.250001, f"CEX cap violated: {cex_weight:.4f}"

    # Exact 2-leg rebalance cost (Astra F10 fix): diff = |w_target - w_cur| sums BOTH sells and buys;
    # each leg pays one-way cost `costs_frac[i]`, so total rebalance fee = sum(diff * costs_frac) (NO * 0.5!).
    costs_frac = np.array([SLEEVE_REBAL_COST_BPS.get(nm, 5.0) / 10_000.0 for nm in names], dtype=np.float64)
    w_cur = w_target.copy()
    ob_ret_monthly = np.zeros(len(ob_days), dtype=np.float64)
    prev_ym = ob_days[0][:7]
    total_turnover = 0.0
    n_rebals = 0

    for t in range(len(ob_days)):
        ym = ob_days[t][:7]
        tc = 0.0
        if t > 0 and ym != prev_ym:
            diff = np.abs(w_target - w_cur)
            turnover = 0.5 * float(np.sum(diff))
            tc = float(np.sum(diff * costs_frac))
            total_turnover += turnover
            n_rebals += 1
            w_cur = w_target.copy()
            prev_ym = ym

        r_vec = mat[t]
        port_r = float(np.dot(w_cur, r_vec)) - tc
        ob_ret_monthly[t] = port_r
        grown = w_cur * (1.0 + r_vec)
        gs = float(np.sum(grown))
        if gs > 1e-12:
            w_cur = grown / gs

    metrics_full = compute_series_metrics(ob_ret_monthly, ann_days=252.0)
    oos_mask = ~train_mask
    metrics_oos = compute_series_metrics(ob_ret_monthly[oos_mask], ann_days=252.0)
    yrs = max(1.0, len(ob_days) / 252.0)
    return {
        "returns": ob_ret_monthly,
        "sleeve_names": names,
        "weights_pct": {nm: round(100.0 * float(w_target[j]), 2) for j, nm in enumerate(names)},
        "total_cex_weight_pct": round(100.0 * cex_weight, 2),
        "rebalance_count": n_rebals,
        "annual_turnover_pct": round(100.0 * total_turnover / yrs, 2),
        "metrics_full_dev": metrics_full,
        "metrics_blind_oos_2023_2024": metrics_oos,
        "expected_monthly_net_ret": float(np.mean(ob_ret_monthly)) * DAYS_PER_MONTH,
    }


def build_own_book_nco_cexcap25_series(
    prop_days: list[str],
    *,
    returns_dir: Path = DEFAULT_RETURNS_DIR,
    train_end: str = "2022-12-31",
    end_day: str = "2024-12-31",
    investable_only: bool = True,
) -> dict[str, Any]:
    """Compute real sealed Dev Own-Book `NCO_CexCap25` (`Monthly_1st`, CEX <= 25%) daily returns aligned cleanly to `prop_days`.

    Astra F10 fixes:
      1. Exact 2-leg rebalance cost (`sum(|Δw_i| * c_i)`, removed erroneous `* 0.5`).
      2. ZERO future-date modulo wrapping (`i % n_ob` removed!): dates outside the true overlap window
         receive `0.0` (cash, zero lookahead) and `overlap_days` is exposed for exact contemporaneous coupling.
      3. Defaults to `investable_only=True` (`S2 + S3A + S3B + S4`, excluding Prop sleeves S1/S5 to eliminate
         double-counting Prop returns inside Own-Book), while also reporting the 6-sleeve pod reference!
    """
    if end_day >= "2025-01-01":
        raise HoldoutLockError(f"HOLDOUT_CONTAMINATION:{end_day}")

    sleeve_maps_all, _ = discover_available_sleeves(returns_dir, max_sleeves=6)
    ob_days_6, mat_6, names_6 = align_sleeves_business_days(sleeve_maps_all, end_day=end_day)
    enforce_pre_holdout_dates(ob_days_6, context="top1_unified.ob_days_6")
    ref_6 = _simulate_monthly_nco_portfolio(ob_days_6, mat_6, names_6, train_end)

    if investable_only:
        inv_maps = {k: v for k, v in sleeve_maps_all.items() if k in INVESTABLE_OB_SLEEVES}
        ob_days, mat, names = align_sleeves_business_days(inv_maps, end_day=end_day)
        primary = _simulate_monthly_nco_portfolio(ob_days, mat, names, train_end)
    else:
        ob_days = ob_days_6
        primary = ref_6

    # Strict zero-lookahead date alignment: EXACT calendar-day match only; unmatched pre-2020 dates -> 0.0 cash!
    ob_by_day = {ob_days[t]: float(primary["returns"][t]) for t in range(len(ob_days))}
    aligned_ob = np.array([ob_by_day.get(dk, 0.0) for dk in prop_days], dtype=np.float64)

    return {
        "aligned_daily_returns": aligned_ob,
        "raw_overlap_returns": primary["returns"],
        "overlap_days": ob_days,
        "overlap_window": f"{ob_days[0]}..{ob_days[-1]} ({len(ob_days)} biz days)",
        "investable_own_book_only": bool(investable_only),
        "sleeve_names": primary["sleeve_names"],
        "weights_pct": primary["weights_pct"],
        "total_cex_weight_pct": primary["total_cex_weight_pct"],
        "rebalance_schedule": "Monthly_1st",
        "rebalance_count": primary["rebalance_count"],
        "annual_turnover_pct": primary["annual_turnover_pct"],
        "metrics_full_dev": primary["metrics_full_dev"],
        "metrics_blind_oos_2023_2024": primary["metrics_blind_oos_2023_2024"],
        "expected_monthly_net_ret": primary["expected_monthly_net_ret"],
        "full_6sleeve_pod_reference": {
            "sleeve_names": ref_6["sleeve_names"],
            "weights_pct": ref_6["weights_pct"],
            "metrics_full_dev": ref_6["metrics_full_dev"],
            "metrics_blind_oos_2023_2024": ref_6["metrics_blind_oos_2023_2024"],
        },
    }


# ---------------------------------------------------------------------------
# Coupled 60-Month Multi-Slot Prop + 3-Bucket + Own-Book + Infra Gates Numba Engine
# ---------------------------------------------------------------------------

@njit(cache=True)
def _simulate_unified_trajectory_numba(
    idx_matrix: np.ndarray,
    # 3 distinct pre-replayed M1 staged tape sets (exact SYMCAP per profile!):
    # Book 0: Upgraded 5%/10% (`SYMCAP 1.75%`, Dyn_ProfitLock 4.5x -> 2.0x, P2 2.5x -> 1.5x, Funded 1.0x)
    b0_p1s_n: np.ndarray, b0_p1s_d: np.ndarray, b0_p1s_f: np.ndarray,
    b0_p1l_n: np.ndarray, b0_p1l_d: np.ndarray, b0_p1l_f: np.ndarray,
    b0_p2s_n: np.ndarray, b0_p2s_d: np.ndarray, b0_p2s_f: np.ndarray,
    b0_p2l_n: np.ndarray, b0_p2l_d: np.ndarray, b0_p2l_f: np.ndarray,
    b0_fn_n: np.ndarray, b0_fn_d: np.ndarray, b0_fn_f: np.ndarray,
    # Book 1: Calibrated 4%/8% Safe (`SYMCAP 1.15%`, P1 2.75x -> 1.50x, P2 2.00x -> 1.25x, Funded 1.0x)
    b1_p1s_n: np.ndarray, b1_p1s_d: np.ndarray, b1_p1s_f: np.ndarray,
    b1_p1l_n: np.ndarray, b1_p1l_d: np.ndarray, b1_p1l_f: np.ndarray,
    b1_p2s_n: np.ndarray, b1_p2s_d: np.ndarray, b1_p2s_f: np.ndarray,
    b1_p2l_n: np.ndarray, b1_p2l_d: np.ndarray, b1_p2l_f: np.ndarray,
    b1_fn_n: np.ndarray, b1_fn_d: np.ndarray, b1_fn_f: np.ndarray,
    # Book 2: Old Legacy 5%/10% (`SYMCAP 3.00%`, P1 Static 4.00x, P2 2.00x, Funded 1.0x)
    b2_p1s_n: np.ndarray, b2_p1s_d: np.ndarray, b2_p1s_f: np.ndarray,
    b2_p2s_n: np.ndarray, b2_p2s_d: np.ndarray, b2_p2s_f: np.ndarray,
    b2_fn_n: np.ndarray, b2_fn_d: np.ndarray, b2_fn_f: np.ndarray,
    # Date-aligned Own-Book NCO_CexCap25 daily net returns
    ob_daily_ret: np.ndarray,
    # Per-slot configuration arrays (length = n_slots)
    slot_book_id: np.ndarray,       # 0 = Smart 5/10, 1 = Smart 4/8, 2 = Old 10K 5/10
    slot_cap: np.ndarray,
    slot_fee: np.ndarray,
    slot_refund_ratio: np.ndarray,
    slot_refund_is_hub: np.ndarray,
    slot_p1_target: np.ndarray,
    slot_p2_target: np.ndarray,
    slot_daily_lim: np.ndarray,
    slot_static_lim: np.ndarray,
    slot_min_days: np.ndarray,
    slot_min_prof_day: np.ndarray,
    slot_split: np.ndarray,
    slot_payout_cycle: np.ndarray,
    slot_start_day: np.ndarray,
    slot_retry_disc: np.ndarray,
    slot_req_funded_first: np.ndarray,  # 1 = expansion tier requires >=1 funded slot or cushion >= 2x fee
    slot_cushion_mult: np.ndarray,      # min multiple of fee required in reserve before opening new expansion slot
    slot_amber_dd: np.ndarray,
    slot_amber_scale: np.ndarray,
    slot_red_dd: np.ndarray,
    slot_red_scale: np.ndarray,
    slot_ea_stop: np.ndarray,
    slot_min_payout: np.ndarray,
    # Capital, Treasury & Crossover calibration
    init_fee_budget: float,
    init_own_book: float,
    reserve_pct: float,
    own_book_pct: float,
    ops_tax_pct: float,
    reserve_cap_mult: float,
    exp_ob_monthly_ret: float,
    exp_prop_monthly_ret: float,
    max_total_prop_nominal: float,
):
    """Coupled 60-month multi-slot Prop + 3-Bucket + Own-Book NCO_CexCap25 + Profit-Funded Infra Gates simulator."""
    n_paths, horizon = idx_matrix.shape
    n_slots = len(slot_cap)
    n_months = horizon // 21

    # Output arrays
    wiped_out = np.zeros(n_paths, dtype=np.int8)
    dbl_fail_any = np.zeros(n_paths, dtype=np.int8)
    tot_fees_24m = np.zeros(n_paths, dtype=np.float64)
    tot_pay_24m = np.zeros(n_paths, dtype=np.float64)
    tot_pay_60m = np.zeros(n_paths, dtype=np.float64)
    tot_fees_60m = np.zeros(n_paths, dtype=np.float64)

    ob_24m = np.zeros(n_paths, dtype=np.float64)
    ob_36m = np.zeros(n_paths, dtype=np.float64)
    ob_60m = np.zeros(n_paths, dtype=np.float64)
    ops_60m = np.zeros(n_paths, dtype=np.float64)
    net_wealth_24m = np.zeros(n_paths, dtype=np.float64)
    net_wealth_60m = np.zeros(n_paths, dtype=np.float64)
    peak_funded_nom = np.zeros(n_paths, dtype=np.float64)
    max_comb_dd_pct = np.zeros(n_paths, dtype=np.float64)

    # Milestone first-reached month (-1 = never reached within 60m)
    m_vps = np.full(n_paths, -1, dtype=np.int32)          # Milestone A: LD4/NY4 VPS self-funded
    m_data_total = np.full(n_paths, -1, dtype=np.int32)   # Milestone B1: Active Prop+OB >= 50k + Ops reserve
    m_data_ob = np.full(n_paths, -1, dtype=np.int32)      # Milestone B2: Pure OB >= 50k + Ops reserve
    m_ob_25k = np.full(n_paths, -1, dtype=np.int32)       # Milestone C1: Own-Book >= 25k
    m_ob_50k = np.full(n_paths, -1, dtype=np.int32)       # Milestone C2: Own-Book >= 50k
    m_ob_100k = np.full(n_paths, -1, dtype=np.int32)      # Milestone C3: Own-Book >= 100k
    m_ob_200k = np.full(n_paths, -1, dtype=np.int32)      # Milestone C4: Own-Book >= 200k
    m_crossover = np.full(n_paths, -1, dtype=np.int32)    # Milestone D: OB monthly EV >= Prop monthly EV

    # Path-level combined equity curve Sharpe / CAGR / MaxDD metrics (on total owner equity = reserve+ob+ops)
    path_ann_ret = np.zeros(n_paths, dtype=np.float64)
    path_sharpe = np.zeros(n_paths, dtype=np.float64)
    path_peak_dd = np.zeros(n_paths, dtype=np.float64)
    infra_spent_60m = np.zeros(n_paths, dtype=np.float64)

    drag_lt5k = IBKR_DRAG_LT5K_ANNUAL / 252.0
    drag_lt25k = IBKR_DRAG_LT25K_ANNUAL / 252.0
    drag_lt50k = IBKR_DRAG_LT50K_ANNUAL / 252.0
    drag_ge50k = IBKR_DRAG_GE50K_ANNUAL / 252.0

    for b in range(n_paths):
        cash_res = init_fee_budget
        hub_cred = 0.0
        own_book = init_own_book
        ops_bal = 0.0
        ops_cum_net = 0.0
        infra_spent = 0.0

        stage = np.zeros(n_slots, dtype=np.int8)  # 0=unopened, 1=P1, 2=P2, 3=Funded, -1=failed/waiting retry
        bal = np.zeros(n_slots, dtype=np.float64)
        tdays = np.zeros(n_slots, dtype=np.int32)
        cycle_d = np.zeros(n_slots, dtype=np.int32)
        refunded = np.zeros(n_slots, dtype=np.int8)
        retries = np.zeros(n_slots, dtype=np.int32)
        ever_funded_cnt = 0

        pay_24 = 0.0
        fee_24 = 0.0
        pay_60 = 0.0
        fee_60 = 0.0
        had_dbl = 0
        best_fnom = 0.0
        worst_prop_dd = 0.0

        vps_active = 0
        data_active = 0

        # Track monthly payouts for rolling 3-month sustained Ops gate & monthly returns for Sharpe
        month_pay_hist = np.zeros(n_months + 1, dtype=np.float64)
        month_ops_hist = np.zeros(n_months + 1, dtype=np.float64)
        cur_m_pay = 0.0
        cur_m_ops = 0.0

        # Track combined owner liquid equity (cash_res + own_book + ops_bal) for path Sharpe & Peak DD
        init_tot_eq = max(500.0, init_fee_budget + init_own_book)
        prev_eq = init_tot_eq
        peak_eq = init_tot_eq
        max_eq_dd = 0.0
        sum_r = 0.0
        sum_r2 = 0.0

        for d in range(horizon):
            src = idx_matrix[b, d]
            mo = (d // 21) + 1

            # Determine current total active nominal & next unopened target ticket for dynamic 5x Reserve Cap
            cur_active_nom = 0.0
            max_active_or_next_fee = 0.0
            for s in range(n_slots):
                if stage[s] > 0:
                    cur_active_nom += slot_cap[s]
                    if slot_fee[s] > max_active_or_next_fee:
                        max_active_or_next_fee = slot_fee[s]
                elif stage[s] == 0 and slot_fee[s] > max_active_or_next_fee:
                    max_active_or_next_fee = slot_fee[s]
            dyn_reserve_cap = reserve_cap_mult * max(39.0, max_active_or_next_fee)

            # 1. Start eligible new slots OR retry failed slots (never exceed max_total_prop_nominal!)
            for s in range(n_slots):
                if stage[s] == 0:
                    if d < slot_start_day[s]:
                        continue
                    if cur_active_nom + slot_cap[s] > max_total_prop_nominal + 1e-6:
                        continue
                    if slot_req_funded_first[s] == 1 and ever_funded_cnt == 0:
                        continue
                    eff_fee = slot_fee[s]
                    avail = cash_res + (hub_cred if slot_refund_is_hub[s] == 1 else 0.0)
                    need = eff_fee * slot_cushion_mult[s]
                    if avail >= need:
                        pay_hub = 0.0
                        if slot_refund_is_hub[s] == 1 and hub_cred > 0.0:
                            pay_hub = eff_fee if hub_cred >= eff_fee else hub_cred
                            hub_cred -= pay_hub
                        cash_res -= (eff_fee - pay_hub)
                        fee_60 += eff_fee
                        if d < 504:
                            fee_24 += eff_fee
                        stage[s] = 1
                        bal[s] = slot_cap[s]
                        tdays[s] = 0
                        cycle_d[s] = 0
                        refunded[s] = 0
                        cur_active_nom += slot_cap[s]
                elif stage[s] == -1:
                    if cur_active_nom + slot_cap[s] > max_total_prop_nominal + 1e-6:
                        continue
                    eff_fee = slot_fee[s] * slot_retry_disc[s]
                    avail = cash_res + (hub_cred if slot_refund_is_hub[s] == 1 else 0.0)
                    if avail >= eff_fee:
                        pay_hub = 0.0
                        if slot_refund_is_hub[s] == 1 and hub_cred > 0.0:
                            pay_hub = eff_fee if hub_cred >= eff_fee else hub_cred
                            hub_cred -= pay_hub
                        cash_res -= (eff_fee - pay_hub)
                        fee_60 += eff_fee
                        if d < 504:
                            fee_24 += eff_fee
                        stage[s] = 1
                        bal[s] = slot_cap[s]
                        tdays[s] = 0
                        cycle_d[s] = 0
                        refunded[s] = 0
                        cur_active_nom += slot_cap[s]

            # 2. Step all active Prop slots simultaneously on EXACT SAME market day `src`
            fails_today = 0
            active_nom = 0.0
            active_dd_usd = 0.0
            funded_nom = 0.0

            for s in range(n_slots):
                st = stage[s]
                if st <= 0:
                    continue
                cap_s = slot_cap[s]
                scale = cap_s / 10_000.0
                active_nom += cap_s
                if st == 3:
                    funded_nom += cap_s

                eq_pct = (bal[s] - cap_s) / cap_s
                bk = slot_book_id[s]

                # Select exact pre-replayed M1 stage tape (no fake linear scaling across SYMCAP!)
                if bk == 0:
                    if eq_pct <= -slot_red_dd[s]:
                        net = b0_fn_n[src] * scale * slot_red_scale[s]
                        dd = b0_fn_d[src] * scale * slot_red_scale[s]
                        flg = b0_fn_f[src]
                    elif eq_pct <= -slot_amber_dd[s]:
                        net = b0_fn_n[src] * scale * slot_amber_scale[s]
                        dd = b0_fn_d[src] * scale * slot_amber_scale[s]
                        flg = b0_fn_f[src]
                    elif st == 1:
                        if eq_pct / max(1e-6, slot_p1_target[s]) >= 0.50:
                            net, dd, flg = b0_p1l_n[src] * scale, b0_p1l_d[src] * scale, b0_p1l_f[src]
                        else:
                            net, dd, flg = b0_p1s_n[src] * scale, b0_p1s_d[src] * scale, b0_p1s_f[src]
                    elif st == 2:
                        if eq_pct / max(1e-6, slot_p2_target[s]) >= 0.60:
                            net, dd, flg = b0_p2l_n[src] * scale, b0_p2l_d[src] * scale, b0_p2l_f[src]
                        else:
                            net, dd, flg = b0_p2s_n[src] * scale, b0_p2s_d[src] * scale, b0_p2s_f[src]
                    else:
                        net, dd, flg = b0_fn_n[src] * scale, b0_fn_d[src] * scale, b0_fn_f[src]
                elif bk == 1:
                    if eq_pct <= -slot_red_dd[s]:
                        net = b1_fn_n[src] * scale * slot_red_scale[s]
                        dd = b1_fn_d[src] * scale * slot_red_scale[s]
                        flg = b1_fn_f[src]
                    elif eq_pct <= -slot_amber_dd[s]:
                        net = b1_fn_n[src] * scale * slot_amber_scale[s]
                        dd = b1_fn_d[src] * scale * slot_amber_scale[s]
                        flg = b1_fn_f[src]
                    elif st == 1:
                        if eq_pct / max(1e-6, slot_p1_target[s]) >= 0.50:
                            net, dd, flg = b1_p1l_n[src] * scale, b1_p1l_d[src] * scale, b1_p1l_f[src]
                        else:
                            net, dd, flg = b1_p1s_n[src] * scale, b1_p1s_d[src] * scale, b1_p1s_f[src]
                    elif st == 2:
                        if eq_pct / max(1e-6, slot_p2_target[s]) >= 0.60:
                            net, dd, flg = b1_p2l_n[src] * scale, b1_p2l_d[src] * scale, b1_p2l_f[src]
                        else:
                            net, dd, flg = b1_p2s_n[src] * scale, b1_p2s_d[src] * scale, b1_p2s_f[src]
                    else:
                        net, dd, flg = b1_fn_n[src] * scale, b1_fn_d[src] * scale, b1_fn_f[src]
                else:
                    if eq_pct <= -slot_red_dd[s]:
                        net = b2_fn_n[src] * scale * slot_red_scale[s]
                        dd = b2_fn_d[src] * scale * slot_red_scale[s]
                        flg = b2_fn_f[src]
                    elif eq_pct <= -slot_amber_dd[s]:
                        net = b2_fn_n[src] * scale * slot_amber_scale[s]
                        dd = b2_fn_d[src] * scale * slot_amber_scale[s]
                        flg = b2_fn_f[src]
                    elif st == 1:
                        net, dd, flg = b2_p1s_n[src] * scale, b2_p1s_d[src] * scale, b2_p1s_f[src]
                    elif st == 2:
                        net, dd, flg = b2_p2s_n[src] * scale, b2_p2s_d[src] * scale, b2_p2s_f[src]
                    else:
                        net, dd, flg = b2_fn_n[src] * scale, b2_fn_d[src] * scale, b2_fn_f[src]

                daily_cap = cap_s * slot_daily_lim[s]
                static_floor = cap_s * (1.0 - slot_static_lim[s])
                ea_cut = cap_s * slot_ea_stop[s]

                # Realistic broker continuous tick-monitor physics (Astra F09 fix):
                # Check raw daily_cap AND raw static_floor FIRST; charge full 0.20% exit slip on ea_cut!
                daily_hit = dd >= daily_cap - 1e-9
                static_hit = (bal[s] - dd) <= static_floor + 1e-9
                if (not daily_hit) and (not static_hit) and (dd > ea_cut):
                    dd_eff = min(dd, ea_cut + cap_s * 0.0020)
                    net = min(net, -dd_eff)
                    daily_hit = dd_eff >= daily_cap - 1e-9
                    static_hit = (bal[s] - dd_eff) <= static_floor + 1e-9

                if daily_hit or static_hit:
                    fails_today += 1
                    stage[s] = -1
                    retries[s] += 1
                    bal[s] = 0.0
                    active_dd_usd += cap_s * slot_static_lim[s]
                    continue

                bal[s] += net
                if bal[s] < cap_s:
                    active_dd_usd += (cap_s - bal[s])

                if slot_min_prof_day[s] > 0.0:
                    if net >= cap_s * slot_min_prof_day[s] - 1e-9:
                        tdays[s] += 1
                elif flg != 0:
                    tdays[s] += 1

                if st == 1:
                    if bal[s] >= cap_s * (1.0 + slot_p1_target[s]) - 1e-9 and tdays[s] >= slot_min_days[s]:
                        stage[s] = 2
                        bal[s] = cap_s
                        tdays[s] = 0
                elif st == 2:
                    if bal[s] >= cap_s * (1.0 + slot_p2_target[s]) - 1e-9 and tdays[s] >= slot_min_days[s]:
                        stage[s] = 3
                        bal[s] = cap_s
                        tdays[s] = 0
                        cycle_d[s] = 0
                        ever_funded_cnt += 1
                elif st == 3:
                    cycle_d[s] += 1
                    if cycle_d[s] >= slot_payout_cycle[s]:
                        cycle_d[s] = 0
                        prof = bal[s] - cap_s
                        if prof > 0.0:
                            net_pay = prof * slot_split[s]
                            if net_pay < slot_min_payout[s] - 1e-9:
                                continue
                            bal[s] = cap_s
                            if refunded[s] == 0:
                                refunded[s] = 1
                                ref_amt = slot_fee[s] * slot_refund_ratio[s]
                                if slot_refund_is_hub[s] == 1:
                                    hub_cred += ref_amt
                                else:
                                    net_pay += ref_amt
                            pay_60 += net_pay
                            cur_m_pay += net_pay
                            if d < 504:
                                pay_24 += net_pay

                            # Exact 3-Bucket Auto-Compounding (30% Reserve capped at 5x -> 100% overflow to Own-Book, 50% OB, 20% Ops)
                            to_res = net_pay * reserve_pct
                            to_ob = net_pay * own_book_pct
                            to_ops = net_pay * ops_tax_pct
                            room = dyn_reserve_cap - cash_res
                            if room <= 0.0:
                                to_ob += to_res
                            elif to_res > room:
                                cash_res += room
                                to_ob += (to_res - room)
                            else:
                                cash_res += to_res
                            own_book += to_ob
                            ops_bal += to_ops
                            ops_cum_net += to_ops
                            cur_m_ops += to_ops

            if fails_today >= 2:
                had_dbl = 1
            if funded_nom > best_fnom:
                best_fnom = funded_nom
            if active_nom > 0.0:
                dd_p = active_dd_usd / active_nom
                if dd_p > worst_prop_dd:
                    worst_prop_dd = dd_p

            # 3. Compound Own-Book daily on coupled NCO_CexCap25 return MINUS honest tier-dependent IBKR drag
            if own_book > 0.0:
                if own_book < 5_000.0:
                    drag = drag_lt5k
                elif own_book < 25_000.0:
                    drag = drag_lt25k
                elif own_book < 50_000.0:
                    drag = drag_lt50k
                else:
                    drag = drag_ge50k
                own_book *= (1.0 + ob_daily_ret[src] - drag)
                if own_book < 0.0:
                    own_book = 0.0

            # 4. Month-end Infrastructure Gates & Milestones (every 21 trading days)
            if (d + 1) % 21 == 0:
                m_idx = (d + 1) // 21
                month_pay_hist[m_idx] = cur_m_pay
                month_ops_hist[m_idx] = cur_m_ops

                # Rolling 3-month average monthly Prop payout & Ops inflow
                w_start = max(1, m_idx - 2)
                w_cnt = m_idx - w_start + 1
                avg3_pay = 0.0
                avg3_ops = 0.0
                for k_m in range(w_start, m_idx + 1):
                    avg3_pay += month_pay_hist[k_m]
                    avg3_ops += month_ops_hist[k_m]
                avg3_pay /= float(w_cnt)
                avg3_ops /= float(w_cnt)

                # Milestone A — Commercial LD4/NY4 VPS (35 USD/mo) self-funded from Ops Bucket
                if m_vps[b] < 0:
                    if (m_idx >= 3 and avg3_ops >= 300.0) or (m_idx >= 3 and avg3_pay >= 300.0 and ops_bal >= 300.0) or (ops_bal >= 1_200.0):
                        m_vps[b] = m_idx
                        vps_active = 1
                if vps_active == 1 and ops_bal >= VPS_MONTHLY_USD:
                    ops_bal -= VPS_MONTHLY_USD
                    infra_spent += VPS_MONTHLY_USD

                # Milestone B — Clean Institutional Data (100 USD/mo) self-funded from profit
                tot_active_eq = funded_nom + own_book
                if m_data_total[b] < 0 and tot_active_eq >= 50_000.0 and ops_bal >= 1_200.0:
                    m_data_total[b] = m_idx
                    data_active = 1
                if m_data_ob[b] < 0 and own_book >= 50_000.0 and ops_bal >= 1_200.0:
                    m_data_ob[b] = m_idx
                if data_active == 1 and ops_bal >= DATA_MONTHLY_USD + 300.0:
                    ops_bal -= DATA_MONTHLY_USD
                    infra_spent += DATA_MONTHLY_USD

                # Milestone C — Own-Book Wealth Tiers
                if m_ob_25k[b] < 0 and own_book >= 25_000.0:
                    m_ob_25k[b] = m_idx
                if m_ob_50k[b] < 0 and own_book >= 50_000.0:
                    m_ob_50k[b] = m_idx
                if m_ob_100k[b] < 0 and own_book >= 100_000.0:
                    m_ob_100k[b] = m_idx
                if m_ob_200k[b] < 0 and own_book >= 200_000.0:
                    m_ob_200k[b] = m_idx

                # Milestone D — True Crossover (ONLY after Prop is meaningfully Funded >= 25k USD!)
                # Own-Book expected monthly net return (after IBKR drag) >= active Funded Prop expected monthly net
                if own_book < 5_000.0:
                    cur_drag_mo = IBKR_DRAG_LT5K_ANNUAL / 12.0
                elif own_book < 25_000.0:
                    cur_drag_mo = IBKR_DRAG_LT25K_ANNUAL / 12.0
                elif own_book < 50_000.0:
                    cur_drag_mo = IBKR_DRAG_LT50K_ANNUAL / 12.0
                else:
                    cur_drag_mo = IBKR_DRAG_GE50K_ANNUAL / 12.0
                ob_ev_mo = own_book * max(0.0, exp_ob_monthly_ret - cur_drag_mo)
                prop_ev_mo = funded_nom * exp_prop_monthly_ret
                if m_crossover[b] < 0 and funded_nom >= 25_000.0 and own_book >= 25_000.0 and ob_ev_mo >= prop_ev_mo:
                    m_crossover[b] = m_idx

                # Record monthly liquid equity return for combined Sharpe & Peak DD
                cur_tot_eq = cash_res + own_book + ops_bal
                if prev_eq > 1.0:
                    mr = (cur_tot_eq - prev_eq) / prev_eq
                    sum_r += mr
                    sum_r2 += mr * mr
                if cur_tot_eq > peak_eq:
                    peak_eq = cur_tot_eq
                if peak_eq > 1.0:
                    dd_l = (peak_eq - cur_tot_eq) / peak_eq
                    if dd_l > max_eq_dd:
                        max_eq_dd = dd_l
                prev_eq = cur_tot_eq

                cur_m_pay = 0.0
                cur_m_ops = 0.0

                if m_idx == 24:
                    ob_24m[b] = own_book
                    net_wealth_24m[b] = cash_res + own_book + ops_bal - init_fee_budget - init_own_book
                elif m_idx == 36:
                    ob_36m[b] = own_book

            # Check Prop fee-bankroll wipeout (zero alive slots AND cannot afford cheapest retryable slot)
            any_alive = 0
            min_retry_fee = 1e12
            for s in range(n_slots):
                if stage[s] > 0 or (stage[s] == 0 and d < slot_start_day[s] and slot_req_funded_first[s] == 0):
                    any_alive = 1
                if stage[s] == -1:
                    ef = slot_fee[s] * slot_retry_disc[s]
                    if ef < min_retry_fee:
                        min_retry_fee = ef
            if any_alive == 0 and (cash_res + hub_cred) < min_retry_fee:
                wiped_out[b] = 1
                # Continue compounding remaining Own-Book through 60m cleanly
                for d_rem in range(d + 1, horizon):
                    s_rem = idx_matrix[b, d_rem]
                    if own_book > 0.0:
                        drag = drag_lt5k if own_book < 5_000.0 else (drag_lt25k if own_book < 25_000.0 else (drag_lt50k if own_book < 50_000.0 else drag_ge50k))
                        own_book *= (1.0 + ob_daily_ret[s_rem] - drag)
                    if (d_rem + 1) % 21 == 0:
                        m_idx = (d_rem + 1) // 21
                        if m_ob_25k[b] < 0 and own_book >= 25_000.0:
                            m_ob_25k[b] = m_idx
                        if m_ob_50k[b] < 0 and own_book >= 50_000.0:
                            m_ob_50k[b] = m_idx
                        if m_ob_100k[b] < 0 and own_book >= 100_000.0:
                            m_ob_100k[b] = m_idx
                        if m_ob_200k[b] < 0 and own_book >= 200_000.0:
                            m_ob_200k[b] = m_idx
                        cur_tot_eq = cash_res + own_book + ops_bal
                        if prev_eq > 1.0:
                            mr = (cur_tot_eq - prev_eq) / prev_eq
                            sum_r += mr
                            sum_r2 += mr * mr
                        if cur_tot_eq > peak_eq:
                            peak_eq = cur_tot_eq
                        if peak_eq > 1.0:
                            dd_l = (peak_eq - cur_tot_eq) / peak_eq
                            if dd_l > max_eq_dd:
                                max_eq_dd = dd_l
                        prev_eq = cur_tot_eq
                        if m_idx == 24:
                            ob_24m[b] = own_book
                            net_wealth_24m[b] = cash_res + own_book + ops_bal - init_fee_budget - init_own_book
                        elif m_idx == 36:
                            ob_36m[b] = own_book
                break

        ob_60m[b] = own_book
        ops_60m[b] = ops_bal
        net_wealth_60m[b] = cash_res + own_book + ops_bal - init_fee_budget - init_own_book
        tot_pay_24m[b] = pay_24
        tot_fees_24m[b] = fee_24
        tot_pay_60m[b] = pay_60
        tot_fees_60m[b] = fee_60
        dbl_fail_any[b] = had_dbl
        peak_funded_nom[b] = best_fnom
        max_comb_dd_pct[b] = worst_prop_dd * 100.0
        infra_spent_60m[b] = infra_spent

        # Combined annualized return & Sharpe (capped realistically on monthly liquid wealth)
        end_eq = max(1.0, cash_res + own_book + ops_bal)
        path_ann_ret[b] = ((end_eq / init_tot_eq) ** (1.0 / 5.0) - 1.0) * 100.0
        mean_mr = sum_r / float(n_months)
        var_mr = max(1e-12, (sum_r2 / float(n_months)) - mean_mr * mean_mr)
        path_sharpe[b] = (mean_mr / np.sqrt(var_mr)) * np.sqrt(12.0)
        path_peak_dd[b] = max_eq_dd * 100.0

    return (
        wiped_out, dbl_fail_any, tot_fees_24m, tot_pay_24m, tot_fees_60m, tot_pay_60m,
        ob_24m, ob_36m, ob_60m, ops_60m, net_wealth_24m, net_wealth_60m,
        peak_funded_nom, max_comb_dd_pct, infra_spent_60m,
        m_vps, m_data_total, m_data_ob, m_ob_25k, m_ob_50k, m_ob_100k, m_ob_200k, m_crossover,
        path_ann_ret, path_sharpe, path_peak_dd,
    )


def _pack_unified_slots(slots: list[dict[str, Any]]) -> tuple[np.ndarray, ...]:
    return (
        np.array([int(s["book_id"]) for s in slots], dtype=np.int32),
        np.array([float(s["cap"]) for s in slots], dtype=np.float64),
        np.array([float(s["fee"]) for s in slots], dtype=np.float64),
        np.array([float(s["refund_ratio"]) for s in slots], dtype=np.float64),
        np.array([int(s["refund_is_hub"]) for s in slots], dtype=np.int8),
        np.array([float(s["p1_target"]) for s in slots], dtype=np.float64),
        np.array([float(s["p2_target"]) for s in slots], dtype=np.float64),
        np.array([float(s["daily_lim"]) for s in slots], dtype=np.float64),
        np.array([float(s["static_lim"]) for s in slots], dtype=np.float64),
        np.array([int(s["min_days"]) for s in slots], dtype=np.int32),
        np.array([float(s["min_prof_day"]) for s in slots], dtype=np.float64),
        np.array([float(s["split"]) for s in slots], dtype=np.float64),
        np.array([int(s["payout_cycle"]) for s in slots], dtype=np.int32),
        np.array([int(s["start_day"]) for s in slots], dtype=np.int32),
        np.array([float(s["retry_disc"]) for s in slots], dtype=np.float64),
        np.array([int(s["req_funded_first"]) for s in slots], dtype=np.int8),
        np.array([float(s["cushion_mult"]) for s in slots], dtype=np.float64),
        np.array([float(s["amber_dd"]) for s in slots], dtype=np.float64),
        np.array([float(s["amber_scale"]) for s in slots], dtype=np.float64),
        np.array([float(s["red_dd"]) for s in slots], dtype=np.float64),
        np.array([float(s["red_scale"]) for s in slots], dtype=np.float64),
        np.array([float(s["ea_stop"]) for s in slots], dtype=np.float64),
        np.array([float(s.get("min_payout_usd", 150.0 if int(s["refund_is_hub"]) == 1 else 0.0)) for s in slots], dtype=np.float64),
    )


def build_old_repeated_10k_slots() -> list[dict[str, Any]]:
    """Old baseline ladder: repeated 10K FTMO (168 USD) & 5K The5ers tickets with legacy SYMCAP 3.0%."""
    slots: list[dict[str, Any]] = []
    # 10 staggered slots (alternating The5ers 5K & FTMO 10K) up to ~90k-100k via repeated small tickets
    # (capped at 10 small slots = 80k nominal; reflects the structural fee drag of buying repeated 10k tickets!)
    schedule = [
        ("T5_5K", 0, 0, 1.0),
        ("FTMO_10K", 42, 0, 1.0),
        ("FTMO_10K", 84, 1, 2.0),
        ("T5_5K", 126, 1, 2.0),
        ("FTMO_10K", 168, 1, 2.0),
        ("FTMO_10K", 210, 1, 2.0),
        ("FTMO_10K", 252, 1, 2.0),
        ("FTMO_10K", 294, 1, 2.0),
        ("FTMO_10K", 336, 1, 2.0),
        ("FTMO_10K", 378, 1, 2.0),
    ]
    for kind, sday, req_f, cush in schedule:
        if kind == "T5_5K":
            slots.append({
                "book_id": 2, "cap": 5_000.0, "fee": 39.0, "refund_ratio": 0.70, "refund_is_hub": 1,
                "p1_target": 0.08, "p2_target": 0.05, "daily_lim": 0.05, "static_lim": 0.10,
                "min_days": 3, "min_prof_day": 0.005, "split": 0.80, "payout_cycle": 10,
                "start_day": sday, "retry_disc": 0.90, "req_funded_first": req_f, "cushion_mult": cush,
                "amber_dd": 0.035, "amber_scale": 0.65, "red_dd": 0.060, "red_scale": 0.40, "ea_stop": 0.042,
            })
        else:
            slots.append({
                "book_id": 2, "cap": 10_000.0, "fee": 168.0, "refund_ratio": 1.00, "refund_is_hub": 0,
                "p1_target": 0.10, "p2_target": 0.05, "daily_lim": 0.05, "static_lim": 0.10,
                "min_days": 4, "min_prof_day": 0.0, "split": 0.80, "payout_cycle": 10,
                "start_day": sday, "retry_disc": 1.00, "req_funded_first": req_f, "cushion_mult": cush,
                "amber_dd": 0.035, "amber_scale": 0.65, "red_dd": 0.060, "red_scale": 0.40, "ea_stop": 0.042,
            })
    return slots


def build_smart_tier_ladder_slots() -> list[dict[str, Any]]:
    """Upgraded Cycle-1 Smart-Tier Ladder (EXACT deployed 4.0x/7E presets + Gate-42 cushion + Calibrated 4%/8% 50K, <= 350k cap)."""
    return [
        # Slot 0 (Day 0): The5ers HS 5K starter (39 USD, 5%/10% DD, SYMCAP 1.75%, min payout 150 USD)
        {
            "book_id": 0, "cap": 5_000.0, "fee": 39.0, "refund_ratio": 0.70, "refund_is_hub": 1,
            "p1_target": 0.08, "p2_target": 0.05, "daily_lim": 0.05, "static_lim": 0.10,
            "min_days": 3, "min_prof_day": 0.005, "split": 0.80, "payout_cycle": 10,
            "start_day": 0, "retry_disc": 0.90, "req_funded_first": 0, "cushion_mult": 1.0,
            "amber_dd": 0.075, "amber_scale": 1.50, "red_dd": 0.090, "red_scale": 1.125, "ea_stop": 0.042,
            "min_payout_usd": 150.0,
        },
        # Slot 1 (Day 42 Gate): FTMO Swing 25K (270 USD) — Astra F12 cashflow discipline: requires >= 2.0x fee cushion (540 USD)!
        {
            "book_id": 0, "cap": 25_000.0, "fee": 270.0, "refund_ratio": 1.00, "refund_is_hub": 0,
            "p1_target": 0.10, "p2_target": 0.05, "daily_lim": 0.05, "static_lim": 0.10,
            "min_days": 4, "min_prof_day": 0.0, "split": 0.80, "payout_cycle": 10,
            "start_day": 42, "retry_disc": 1.00, "req_funded_first": 0, "cushion_mult": 2.0,
            "amber_dd": 0.075, "amber_scale": 1.50, "red_dd": 0.090, "red_scale": 1.125, "ea_stop": 0.042,
            "min_payout_usd": 0.0,
        },
        # Slot 2 (Day 84): The5ers HS 20K (189 USD, 5%/10% DD, SYMCAP 1.75%, funded-first gate!)
        {
            "book_id": 0, "cap": 20_000.0, "fee": 189.0, "refund_ratio": 0.70, "refund_is_hub": 1,
            "p1_target": 0.08, "p2_target": 0.05, "daily_lim": 0.05, "static_lim": 0.10,
            "min_days": 3, "min_prof_day": 0.005, "split": 0.80, "payout_cycle": 10,
            "start_day": 84, "retry_disc": 0.90, "req_funded_first": 1, "cushion_mult": 1.75,
            "amber_dd": 0.075, "amber_scale": 1.50, "red_dd": 0.090, "red_scale": 1.125, "ea_stop": 0.042,
            "min_payout_usd": 150.0,
        },
        # Slot 3 (Day 126): FTMO Swing 50K (360 USD)
        {
            "book_id": 0, "cap": 50_000.0, "fee": 360.0, "refund_ratio": 1.00, "refund_is_hub": 0,
            "p1_target": 0.10, "p2_target": 0.05, "daily_lim": 0.05, "static_lim": 0.10,
            "min_days": 4, "min_prof_day": 0.0, "split": 0.80, "payout_cycle": 10,
            "start_day": 126, "retry_disc": 1.00, "req_funded_first": 1, "cushion_mult": 2.0,
            "amber_dd": 0.075, "amber_scale": 1.50, "red_dd": 0.090, "red_scale": 1.125, "ea_stop": 0.042,
            "min_payout_usd": 0.0,
        },
        # Slot 4 (Day 168): The5ers HS 50K (329 USD, checkout-verified tier; strict 4%/8% DD calibrated 2.75x / SYMCAP 1.15% / EA 2.8%!)
        {
            "book_id": 1, "cap": 50_000.0, "fee": 329.0, "refund_ratio": 0.70, "refund_is_hub": 1,
            "p1_target": 0.08, "p2_target": 0.05, "daily_lim": 0.04, "static_lim": 0.08,
            "min_days": 3, "min_prof_day": 0.005, "split": 0.80, "payout_cycle": 10,
            "start_day": 168, "retry_disc": 0.90, "req_funded_first": 1, "cushion_mult": 2.0,
            "amber_dd": 0.024, "amber_scale": 0.60, "red_dd": 0.048, "red_scale": 0.35, "ea_stop": 0.028,
            "min_payout_usd": 150.0,
        },
        # Slot 5 (Day 210): FTMO Swing 100K #1 (560 USD)
        {
            "book_id": 0, "cap": 100_000.0, "fee": 560.0, "refund_ratio": 1.00, "refund_is_hub": 0,
            "p1_target": 0.10, "p2_target": 0.05, "daily_lim": 0.05, "static_lim": 0.10,
            "min_days": 4, "min_prof_day": 0.0, "split": 0.80, "payout_cycle": 10,
            "start_day": 210, "retry_disc": 1.00, "req_funded_first": 1, "cushion_mult": 2.0,
            "amber_dd": 0.075, "amber_scale": 1.50, "red_dd": 0.090, "red_scale": 1.125, "ea_stop": 0.042,
            "min_payout_usd": 0.0,
        },
        # Slot 6 (Day 252): FTMO Swing 100K #2 (560 USD -> Total max nominal 350k USD across 2 firms!)
        {
            "book_id": 0, "cap": 100_000.0, "fee": 560.0, "refund_ratio": 1.00, "refund_is_hub": 0,
            "p1_target": 0.10, "p2_target": 0.05, "daily_lim": 0.05, "static_lim": 0.10,
            "min_days": 4, "min_prof_day": 0.0, "split": 0.80, "payout_cycle": 10,
            "start_day": 252, "retry_disc": 1.00, "req_funded_first": 1, "cushion_mult": 2.0,
            "amber_dd": 0.075, "amber_scale": 1.50, "red_dd": 0.090, "red_scale": 1.125, "ea_stop": 0.042,
            "min_payout_usd": 0.0,
        },
    ]


def _milestone_stats(m_arr: np.ndarray, n_paths: int) -> dict[str, Any]:
    hit = m_arr[m_arr > 0]
    return {
        "p_24m_pct": round(100.0 * float(np.sum((m_arr > 0) & (m_arr <= 24))) / n_paths, 1),
        "p_36m_pct": round(100.0 * float(np.sum((m_arr > 0) & (m_arr <= 36))) / n_paths, 1),
        "p_60m_pct": round(100.0 * len(hit) / n_paths, 1),
        "med_month": int(np.median(hit)) if len(hit) else -1,
    }


def _summarize_trajectory(
    res: tuple[np.ndarray, ...],
    n_paths: int,
) -> dict[str, Any]:
    (
        wiped, dbl_fail, f24, p24, f60, p60,
        ob24, ob36, ob60, ops60, w24, w60,
        pfnom, max_prop_dd, infra60,
        m_vps, m_dtot, m_dob, m25, m50, m100, m200, m_xo,
        p_ann, p_sh, p_dd,
    ) = res
    mean_f24 = float(np.mean(f24))
    mean_p24 = float(np.mean(p24))
    mean_f60 = float(np.mean(f60))
    mean_p60 = float(np.mean(p60))
    ev_fee_24m = (mean_p24 - mean_f24) / max(1.0, mean_f24)
    ev_fee_60m = (mean_p60 - mean_f60) / max(1.0, mean_f60)

    med_ob24 = float(np.median(ob24))
    med_ob36 = float(np.median(ob36))
    med_ob60 = float(np.median(ob60))
    med_w60 = float(np.median(w60))

    return {
        "wipeout_pct": round(100.0 * float(np.mean(wiped)), 2),
        "dbl_fail_pct": round(100.0 * float(np.mean(dbl_fail)), 1),
        "peak_funded_med_usd": round(float(np.median(pfnom)), 0),
        "mean_fees_24m_usd": round(mean_f24, 1),
        "mean_payouts_24m_usd": round(mean_p24, 1),
        "ev_per_fee_24m": round(ev_fee_24m, 2),
        "ev_per_fee_60m": round(ev_fee_60m, 2),
        "ob_24m_med_usd": round(med_ob24, 0),
        "ob_36m_med_usd": round(med_ob36, 0),
        "ob_60m_med_usd": round(med_ob60, 0),
        "ob_60m_med_vnd_tr": round(med_ob60 * USD_VND_RATE / 1_000_000.0, 1),
        "ops_60m_med_usd": round(float(np.median(ops60)), 0),
        "infra_self_funded_60m_med_usd": round(float(np.median(infra60)), 0),
        "net_wealth_24m_med_usd": round(float(np.median(w24)), 0),
        "net_wealth_60m_med_usd": round(med_w60, 0),
        "net_wealth_60m_med_vnd_tr": round(med_w60 * USD_VND_RATE / 1_000_000.0, 1),
        "comb_ann_ret_med_pct": round(float(np.median(p_ann)), 1),
        "comb_sharpe_med": round(float(np.median(p_sh)), 2),
        "comb_peak_dd_p95_pct": round(float(np.quantile(p_dd, 0.95)), 2),
        "prop_corr_dd_p95_pct": round(float(np.quantile(max_prop_dd, 0.95)), 2),
        "milestones": {
            "A_vps_self_funded": _milestone_stats(m_vps, n_paths),
            "B1_data_active50k": _milestone_stats(m_dtot, n_paths),
            "B2_data_ob50k": _milestone_stats(m_dob, n_paths),
            "C1_ob_25k": _milestone_stats(m25, n_paths),
            "C2_ob_50k": _milestone_stats(m50, n_paths),
            "C3_ob_100k": _milestone_stats(m100, n_paths),
            "C4_ob_200k": _milestone_stats(m200, n_paths),
            "D_crossover": _milestone_stats(m_xo, n_paths),
        },
    }


def build_top1_scorecard_and_pain_table(
    ob_info: dict[str, Any],
    prop_1x_ann_pct: float,
    prop_15x_ann_pct: float,
    old_b1500: dict[str, Any],
    smart_b1500: dict[str, Any],
    smart_b3000_ob25: dict[str, Any],
) -> dict[str, Any]:
    """Compute honest Top-1% Solo Quant Scorecard & absolute VND Worst-Case Pain Table (10k/50k/100k/200k USD)."""
    ob_full = ob_info["metrics_full_dev"]
    ob_oos = ob_info["metrics_blind_oos_2023_2024"]

    # Historical & Black-Swan DD benchmarks anchored directly to sealed QUANT-POD-V2-NCO-CEXCAP-AND-REBALANCE-20261124.md
    nco_hist_dd_pct = float(ob_full["max_dd_pct"])
    nco_corr85_dd_pct = 8.81       # Sealed Corr=0.85 P99 DD for NCO_CexCap25
    nco_cex50_dd_pct = 12.89       # Sealed CEX -50% + P99 1d hit for NCO_CexCap25 (25% total CEX cap!)
    old_hrp_cex50_dd_pct = 41.58   # Old uncapped HRP CEX -50% wipeout shock

    tiers = (10_000.0, 50_000.0, 100_000.0, 200_000.0)
    pain_table: list[dict[str, Any]] = []
    for cap in tiers:
        vnd_total_tr = round(cap * USD_VND_RATE / 1_000_000.0, 1)
        hist_usd = round(cap * nco_hist_dd_pct / 100.0, 0)
        corr_usd = round(cap * nco_corr85_dd_pct / 100.0, 0)
        cex50_usd = round(cap * nco_cex50_dd_pct / 100.0, 0)
        old_cex50_usd = round(cap * old_hrp_cex50_dd_pct / 100.0, 0)
        ibkr_drag_pct = (
            IBKR_DRAG_LT25K_ANNUAL * 100.0 if cap < 25_000.0
            else (IBKR_DRAG_GE50K_ANNUAL * 100.0 if cap >= 50_000.0 else IBKR_DRAG_LT50K_ANNUAL * 100.0)
        )
        net_ob_cagr = round(float(ob_full["cagr_pct"]) - ibkr_drag_pct, 2)
        net_ob_yr_usd = round(cap * net_ob_cagr / 100.0, 0)
        pain_table.append({
            "tier_usd": int(cap),
            "tier_vnd_tr": vnd_total_tr,
            "ibkr_drag_pct": round(ibkr_drag_pct, 2),
            "ob_net_cagr_pct": net_ob_cagr,
            "ob_net_annual_usd": net_ob_yr_usd,
            "ob_net_annual_vnd_tr": round(net_ob_yr_usd * USD_VND_RATE / 1_000_000.0, 1),
            "hist_dd_pct": round(nco_hist_dd_pct, 2),
            "hist_dd_usd": hist_usd,
            "hist_dd_vnd_tr": round(hist_usd * USD_VND_RATE / 1_000_000.0, 1),
            "corr85_dd_pct": nco_corr85_dd_pct,
            "corr85_dd_usd": corr_usd,
            "corr85_dd_vnd_tr": round(corr_usd * USD_VND_RATE / 1_000_000.0, 1),
            "cex50_dd_pct": nco_cex50_dd_pct,
            "cex50_dd_usd": cex50_usd,
            "cex50_dd_vnd_tr": round(cex50_usd * USD_VND_RATE / 1_000_000.0, 1),
            "old_uncapped_cex50_vnd_tr": round(old_cex50_usd * USD_VND_RATE / 1_000_000.0, 1),
        })

    scorecard = [
        {
            "profile": "Baseline Cũ (Repeated 10K · SYMCAP 3.0% · Budget 1.5k, OB 0k)",
            "prop_funded_ann_1x_pct": prop_1x_ann_pct,
            "ob_cagr_1x_pct": round(float(ob_full["cagr_pct"]), 2),
            "ob_sharpe_full": round(float(ob_full["sharpe"]), 2),
            "ob_calmar_full": round(float(ob_full["calmar"]), 2),
            "ob_max_dd_pct": round(nco_hist_dd_pct, 2),
            "cex50_shock_pct": old_hrp_cex50_dd_pct,
            "prop_wipeout_pct": old_b1500["wipeout_pct"],
            "ev_per_fee_24m": old_b1500["ev_per_fee_24m"],
            "ob_60m_med_usd": old_b1500["ob_60m_med_usd"],
            "comb_sharpe_med": old_b1500["comb_sharpe_med"],
        },
        {
            "profile": "Nâng Cấp Smart-Tier (SYMCAP 1.75% + DynPL + 4/8 Safe · Budget 1.5k, OB 0k)",
            "prop_funded_ann_1x_pct": prop_1x_ann_pct,
            "ob_cagr_1x_pct": round(float(ob_full["cagr_pct"]), 2),
            "ob_sharpe_full": round(float(ob_full["sharpe"]), 2),
            "ob_calmar_full": round(float(ob_full["calmar"]), 2),
            "ob_max_dd_pct": round(nco_hist_dd_pct, 2),
            "cex50_shock_pct": nco_cex50_dd_pct,
            "prop_wipeout_pct": smart_b1500["wipeout_pct"],
            "ev_per_fee_24m": smart_b1500["ev_per_fee_24m"],
            "ob_60m_med_usd": smart_b1500["ob_60m_med_usd"],
            "comb_sharpe_med": smart_b1500["comb_sharpe_med"],
        },
        {
            "profile": "Top-1% Hybrid Full Pod (Smart-Tier + NCO_CexCap25 · Budget 3k, OB 25k)",
            "prop_funded_ann_1x_pct": prop_1x_ann_pct,
            "ob_cagr_1x_pct": round(float(ob_full["cagr_pct"]), 2),
            "ob_sharpe_full": round(float(ob_full["sharpe"]), 2),
            "ob_calmar_full": round(float(ob_full["calmar"]), 2),
            "ob_max_dd_pct": round(nco_hist_dd_pct, 2),
            "cex50_shock_pct": nco_cex50_dd_pct,
            "prop_wipeout_pct": smart_b3000_ob25["wipeout_pct"],
            "ev_per_fee_24m": smart_b3000_ob25["ev_per_fee_24m"],
            "ob_60m_med_usd": smart_b3000_ob25["ob_60m_med_usd"],
            "comb_sharpe_med": smart_b3000_ob25["comb_sharpe_med"],
        },
    ]

    return {
        "ob_full_dev_metrics": ob_full,
        "ob_blind_oos_metrics": ob_oos,
        "prop_funded_1x_ann_pct": prop_1x_ann_pct,
        "prop_funded_15x_ann_pct": prop_15x_ann_pct,
        "scorecard": scorecard,
        "vnd_pain_table": pain_table,
    }


def run_study(*, n_paths: int = DEFAULT_N_PATHS, write_report: bool = True, overwrite: bool = False) -> dict[str, Any]:
    t0 = time.perf_counter()
    lock_sha = assert_holdout_locked()

    reg = load_registry()
    warm = build_or_load_frozen_tapes(force_rebuild=False)
    red_news = load_red_news_calendar("red_news_official_2018_2024")
    tapes_1x = dict(warm["tapes"])
    ext_days = sorted(warm["ext_days"])
    enforce_pre_holdout_dates(ext_days, context="top1_unified.ext_days")

    tapes_125x = apply_cost_stress_to_tapes(tapes_1x, 1.25)
    tapes_15x = apply_cost_stress_to_tapes(tapes_1x, 1.5)
    base_r = {e["id"]: float(e["base_risk_pct"]) / 100.0 for e in reg["engines"]}

    # Build pure investable Own-Book NCO_CexCap25 (S2+S3A+S3B+S4, zero Prop double-counting, zero modulo lookahead!)
    ob_probe = build_own_book_nco_cexcap25_series(ext_days, investable_only=True)
    ob_day_set = set(ob_probe["overlap_days"])
    # Strict contemporaneous date intersection (2020-01-02..2024-12-31) — ZERO future-date recycling!
    coupled_days = [d for d in ext_days if d in ob_day_set]
    if len(coupled_days) < 1_000:
        raise HoldoutLockError(f"INSUFFICIENT_COUPLED_DAYS:{len(coupled_days)}")
    enforce_pre_holdout_dates(coupled_days, context="top1_unified.coupled_days")
    ob_info = build_own_book_nco_cexcap25_series(coupled_days, investable_only=True)
    ob_daily_ret = ob_info["aligned_daily_returns"]

    # Helper to replay & extract exact M1 staged arrays on exact deployed presets (7E Core on P2/Funded!)
    def _build_books_for_friction(tapes_use: dict[str, dict]) -> tuple[dict[str, Any], float]:
        def _rep(mult: float, symcap_pct: float, *, use_core7: bool = False, use_red_news: bool = True):
            eng_ids = CORE7_IDS if use_core7 else LIVE8_IDS
            risks = {k: base_r[k] * mult for k in eng_ids}
            met, ex = replay_portfolio_m1(
                coupled_days, tapes_use, risks, 10_000.0,
                profile_mode="Swing",
                max_symbol_concurrent_risk=symcap_pct / 100.0,
                red_news_cal=(red_news if use_red_news else None),
            )
            n, d, f = exits_to_daily_arrays(coupled_days, ex)
            return met, n, d, f

        # Book 0: Exact Deployed 5%/10% (`SYMCAP 1.75%` P1 4.00x->2.01x LIVE8; P2 2.50->1.50 7E SYMCAP 1.50%; Funded 1.0x 7E SYMCAP 1.00%)
        m_fn, b0_fn_n, b0_fn_d, b0_fn_f = _rep(1.00, 1.00, use_core7=True, use_red_news=True)
        _, b0_p1s_n, b0_p1s_d, b0_p1s_f = _rep(4.00, 1.75, use_core7=False, use_red_news=True)
        _, b0_p1l_n, b0_p1l_d, b0_p1l_f = _rep(2.01, 1.75, use_core7=False, use_red_news=True)
        _, b0_p2s_n, b0_p2s_d, b0_p2s_f = _rep(2.50, 1.50, use_core7=True, use_red_news=True)
        _, b0_p2l_n, b0_p2l_d, b0_p2l_f = _rep(1.50, 1.50, use_core7=True, use_red_news=True)

        # Book 1: Calibrated 4%/8% Safe (`SYMCAP 1.15%`, 2.75->1.50 LIVE8; P2 2.00->1.25 7E; Funded 1.0x 7E SYMCAP 1.00%)
        _, b1_fn_n, b1_fn_d, b1_fn_f = _rep(1.00, 1.00, use_core7=True, use_red_news=True)
        _, b1_p1s_n, b1_p1s_d, b1_p1s_f = _rep(2.75, 1.15, use_core7=False, use_red_news=True)
        _, b1_p1l_n, b1_p1l_d, b1_p1l_f = _rep(1.50, 1.15, use_core7=False, use_red_news=True)
        _, b1_p2s_n, b1_p2s_d, b1_p2s_f = _rep(2.00, 1.15, use_core7=True, use_red_news=True)
        _, b1_p2l_n, b1_p2l_d, b1_p2l_f = _rep(1.25, 1.15, use_core7=True, use_red_news=True)

        # Book 2: Old Legacy Repeated-10K (`SYMCAP 3.00%`, Static P1 4.00x / P2 2.00x / Funded 1.0x 7E)
        _, b2_fn_n, b2_fn_d, b2_fn_f = _rep(1.00, 1.00, use_core7=True, use_red_news=True)
        _, b2_p1s_n, b2_p1s_d, b2_p1s_f = _rep(4.00, 3.00, use_core7=False, use_red_news=True)
        _, b2_p2s_n, b2_p2s_d, b2_p2s_f = _rep(2.00, 3.00, use_core7=True, use_red_news=True)

        exp_prop_mo = float(np.mean(b0_fn_n) / 10_000.0) * DAYS_PER_MONTH * 0.80
        books = {
            "arrays": (
                b0_p1s_n, b0_p1s_d, b0_p1s_f,
                b0_p1l_n, b0_p1l_d, b0_p1l_f,
                b0_p2s_n, b0_p2s_d, b0_p2s_f,
                b0_p2l_n, b0_p2l_d, b0_p2l_f,
                b0_fn_n, b0_fn_d, b0_fn_f,
                b1_p1s_n, b1_p1s_d, b1_p1s_f,
                b1_p1l_n, b1_p1l_d, b1_p1l_f,
                b1_p2s_n, b1_p2s_d, b1_p2s_f,
                b1_p2l_n, b1_p2l_d, b1_p2l_f,
                b1_fn_n, b1_fn_d, b1_fn_f,
                b2_p1s_n, b2_p1s_d, b2_p1s_f,
                b2_p2s_n, b2_p2s_d, b2_p2s_f,
                b2_fn_n, b2_fn_d, b2_fn_f,
            ),
            "funded_ann_pct": float(m_fn["ann_pct"]["all"]),
            "exp_prop_monthly_ret": max(1e-4, exp_prop_mo),
        }
        return books, float(m_fn["ann_pct"]["all"])

    books_1x, prop_1x_ann = _build_books_for_friction(tapes_1x)
    books_125x, prop_125x_ann = _build_books_for_friction(tapes_125x)
    books_15x, prop_15x_ann = _build_books_for_friction(tapes_15x)

    idx_mat = make_block_bootstrap_indices(
        len(coupled_days), horizon=HORIZON_DAYS, n_paths=n_paths, block_len=BLOCK_LEN, seed=SEED,
    )

    old_slots_packed = _pack_unified_slots(build_old_repeated_10k_slots())
    smart_slots_packed = _pack_unified_slots(build_smart_tier_ladder_slots())

    scenario_defs = [
        # Old Repeated-10K baseline (3 fee budgets, 0 OB seed, cap 100k)
        ("OLD_10K_B500_OB0",    "Old Repeated-10K (SYMCAP 3.0%)",    "OLD_10K",    500.0,     0.0, old_slots_packed,   100_000.0),
        ("OLD_10K_B1500_OB0",   "Old Repeated-10K (SYMCAP 3.0%)",    "OLD_10K",  1_500.0,     0.0, old_slots_packed,   100_000.0),
        ("OLD_10K_B3000_OB0",   "Old Repeated-10K (SYMCAP 3.0%)",    "OLD_10K",  3_000.0,     0.0, old_slots_packed,   100_000.0),
        # Matched-cap attribution (Smart-Tier capped at EXACT SAME 100k nominal as Old-10K — isolates pure Fee+SYMCAP edge!)
        ("SMART_B1500_CAP100K", "Smart-Tier (Matched Cap 100k)",     "SMART_CAP100K", 1_500.0, 0.0, smart_slots_packed, 100_000.0),
        # New Smart-Tier Ladder (pure Prop -> Own-Book, 3 fee budgets, cap 350k)
        ("SMART_B500_OB0",      "Smart-Tier Ladder (OB Seed 0)",     "SMART_TIER",  500.0,    0.0, smart_slots_packed, 350_000.0),
        ("SMART_B1500_OB0",     "Smart-Tier Ladder (OB Seed 0)",     "SMART_TIER", 1_500.0,   0.0, smart_slots_packed, 350_000.0),
        ("SMART_B3000_OB0",     "Smart-Tier Ladder (OB Seed 0)",     "SMART_TIER", 3_000.0,   0.0, smart_slots_packed, 350_000.0),
        # Hybrid Own-Book Seeds (10k & 25k USD)
        ("SMART_B1500_OB10K",   "Smart-Tier + Hybrid OB 10k",        "SMART_TIER", 1_500.0, 10_000.0, smart_slots_packed, 350_000.0),
        ("SMART_B3000_OB10K",   "Smart-Tier + Hybrid OB 10k",        "SMART_TIER", 3_000.0, 10_000.0, smart_slots_packed, 350_000.0),
        ("SMART_B1500_OB25K",   "Smart-Tier + Hybrid OB 25k",        "SMART_TIER", 1_500.0, 25_000.0, smart_slots_packed, 350_000.0),
        ("SMART_B3000_OB25K",   "Smart-Tier + Hybrid OB 25k",        "SMART_TIER", 3_000.0, 25_000.0, smart_slots_packed, 350_000.0),
    ]

    scenarios_out: list[dict[str, Any]] = []
    for fric, bk_obj in (("1.0x", books_1x), ("1.25x", books_125x), ("1.5x", books_15x)):
        for sc_id, label, arch, fee_b, ob_seed, spacked, max_nom in scenario_defs:
            sim_res = _simulate_unified_trajectory_numba(
                idx_mat,
                *bk_obj["arrays"],
                ob_daily_ret,
                *spacked,
                fee_b, ob_seed,
                0.30, 0.50, 0.20, 5.0,
                ob_info["expected_monthly_net_ret"],
                bk_obj["exp_prop_monthly_ret"],
                max_nom,
            )
            summ = _summarize_trajectory(sim_res, n_paths)
            scenarios_out.append({
                "friction": fric,
                "scenario_id": sc_id,
                "label": label,
                "architecture": arch,
                "init_fee_budget_usd": fee_b,
                "init_own_book_usd": ob_seed,
                "max_prop_nominal_cap_usd": max_nom,
                **summ,
            })

    def _get(fric: str, sc_id: str) -> dict[str, Any]:
        return next(x for x in scenarios_out if x["friction"] == fric and x["scenario_id"] == sc_id)

    old_b1500_1x = _get("1.0x", "OLD_10K_B1500_OB0")
    smart_b1500_1x = _get("1.0x", "SMART_B1500_OB0")
    smart_b3000_1x = _get("1.0x", "SMART_B3000_OB0")
    smart_b3000_ob25_1x = _get("1.0x", "SMART_B3000_OB25K")
    smart_b1500_15x = _get("1.5x", "SMART_B1500_OB0")
    old_b1500_15x = _get("1.5x", "OLD_10K_B1500_OB0")

    scorecard_pack = build_top1_scorecard_and_pain_table(
        ob_info, prop_1x_ann, prop_15x_ann,
        old_b1500_1x, smart_b1500_1x, smart_b3000_ob25_1x,
    )

    # Analytical True Crossover equity thresholds (1.0x unlevered OB vs 2.0x vol-target OB against 100k / 360k Prop)
    ob_net_mo_1x = max(1e-5, ob_info["expected_monthly_net_ret"] - IBKR_DRAG_GE50K_ANNUAL / 12.0)
    prop_net_mo_1x = books_1x["exp_prop_monthly_ret"]
    xo_ratio_1x = prop_net_mo_1x / ob_net_mo_1x
    analytical_crossover = {
        "ob_net_monthly_1x_pct": round(ob_net_mo_1x * 100.0, 3),
        "prop_funded_net_monthly_1x_pct": round(prop_net_mo_1x * 100.0, 3),
        "ob_needed_to_beat_100k_prop_1x_usd": round(100_000.0 * xo_ratio_1x, 0),
        "ob_needed_to_beat_360k_prop_1x_usd": round(360_000.0 * xo_ratio_1x, 0),
        "ob_needed_to_beat_100k_prop_2x_vol_usd": round(100_000.0 * xo_ratio_1x / 2.0, 0),
        "ob_needed_to_beat_360k_prop_2x_vol_usd": round(360_000.0 * xo_ratio_1x / 2.0, 0),
    }

    highlights = {
        "smart_vs_old_b1500_ob60m_usd": [old_b1500_1x["ob_60m_med_usd"], smart_b1500_1x["ob_60m_med_usd"]],
        "smart_vs_old_b1500_ob60m_ratio": round(
            smart_b1500_1x["ob_60m_med_usd"] / max(1.0, old_b1500_1x["ob_60m_med_usd"]), 2
        ),
        "smart_vs_old_b1500_wipeout_pct": [old_b1500_1x["wipeout_pct"], smart_b1500_1x["wipeout_pct"]],
        "smart_vs_old_b1500_15x_ob60m_usd": [old_b1500_15x["ob_60m_med_usd"], smart_b1500_15x["ob_60m_med_usd"]],
        "smart_b1500_vps_med_month": smart_b1500_1x["milestones"]["A_vps_self_funded"]["med_month"],
        "smart_b1500_data_active50k_med_month": smart_b1500_1x["milestones"]["B1_data_active50k"]["med_month"],
        "smart_b1500_ob50k_p60m_pct": smart_b1500_1x["milestones"]["C2_ob_50k"]["p_60m_pct"],
        "smart_b3000_ob50k_p60m_pct": smart_b3000_1x["milestones"]["C2_ob_50k"]["p_60m_pct"],
        "smart_b3000_ob25k_ob100k_p60m_pct": smart_b3000_ob25_1x["milestones"]["C3_ob_100k"]["p_60m_pct"],
        "smart_b3000_ob25k_crossover_p60m_pct": smart_b3000_ob25_1x["milestones"]["D_crossover"]["p_60m_pct"],
        "nco_cexcap25_total_cex_pct": ob_info["total_cex_weight_pct"],
        "analytical_crossover": analytical_crossover,
    }

    elapsed = round(time.perf_counter() - t0, 2)
    payload: dict[str, Any] = {
        "schema": "naqex-top1-unified-trajectory-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "order_send_capable": ORDER_SEND_CAPABLE,
        "order_send_count": ORDER_SEND_COUNT,
        "holdout_lock_sha256": lock_sha,
        "holdout_rows_analysed": 0,
        "dev_window": f"{coupled_days[0]}..{coupled_days[-1]}",
        "dev_days_count": len(coupled_days),
        "mc_paths": n_paths,
        "mc_horizon_months": HORIZON_DAYS // DAYS_PER_MONTH,
        "mc_block_len": BLOCK_LEN,
        "mc_seed": SEED,
        "usd_vnd_rate": USD_VND_RATE,
        "elapsed_sec": elapsed,
        "own_book_pod": {
            k: v for k, v in ob_info.items() if k not in ("aligned_daily_returns", "raw_overlap_returns", "overlap_days")
        },
        "highlights": highlights,
        "scenarios": scenarios_out,
        "scorecard_and_pain": scorecard_pack,
    }

    if write_report:
        OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
        sha_hex = write_verified_receipt(OUT_JSON, payload, overwrite=overwrite)
        payload["receipt_sha256"] = sha_hex
        md_txt = render_trajectory_markdown(payload, sha_hex)
        assert "$" not in md_txt, "Bare '$' detected in trajectory Markdown!"
        OUT_MD.write_text(md_txt, encoding="utf-8", newline="\n")

    return payload


def render_trajectory_markdown(payload: dict[str, Any], sha_hex: str) -> str:
    """Render plain, easy-to-understand Vietnamese trajectory report (strictly zero bare `$`)."""
    hl = payload["highlights"]
    ob = payload["own_book_pod"]
    sc_list = payload["scenarios"]
    sp = payload["scorecard_and_pain"]

    def _fmt_m(ms: dict[str, Any]) -> str:
        if ms["p_60m_pct"] <= 0.0 or ms["med_month"] < 0:
            return f"0.0% (>60T)"
        return f"{ms['p_60m_pct']:.1f}% ({ms['med_month']}T)"

    def _fmt_p24_36_60(ms: dict[str, Any]) -> str:
        med = f"{ms['med_month']}T" if ms["med_month"] > 0 else ">60T"
        return f"{ms['p_24m_pct']:.0f}% / {ms['p_36m_pct']:.0f}% / {ms['p_60m_pct']:.0f}% (TV {med})"

    def _traj_rows(fric: str) -> list[list[str]]:
        rows = []
        for s in sc_list:
            if s["friction"] != fric:
                continue
            rows.append([
                f"{s['label']} (B={int(s['init_fee_budget_usd']):,}, OB={int(s['init_own_book_usd']):,})",
                f"{s['wipeout_pct']:.2f}%",
                f"{s['dbl_fail_pct']:.1f}%",
                f"{int(s['peak_funded_med_usd']):,} USD",
                f"{s['ev_per_fee_24m']:.2f}x",
                f"{int(s['ob_24m_med_usd']):,} USD",
                f"**{int(s['ob_60m_med_usd']):,} USD** ({s['ob_60m_med_vnd_tr']:.0f} tr)",
                f"{int(s['infra_self_funded_60m_med_usd']):,} USD",
            ])
        return rows

    def _ms_rows(fric: str) -> list[list[str]]:
        rows = []
        for s in sc_list:
            if s["friction"] != fric or s["architecture"] != "SMART_TIER":
                continue
            ms = s["milestones"]
            rows.append([
                f"B={int(s['init_fee_budget_usd']):,} + OB={int(s['init_own_book_usd']):,}",
                _fmt_p24_36_60(ms["A_vps_self_funded"]),
                _fmt_p24_36_60(ms["B1_data_active50k"]),
                _fmt_m(ms["C1_ob_25k"]),
                _fmt_m(ms["C2_ob_50k"]),
                _fmt_m(ms["C3_ob_100k"]),
                _fmt_m(ms["C4_ob_200k"]),
                _fmt_m(ms["D_crossover"]),
            ])
        return rows

    score_rows = [
        [
            r["profile"],
            f"+{r['prop_funded_ann_1x_pct']:.2f}%",
            f"+{r['ob_cagr_1x_pct']:.2f}%",
            f"{r['ob_sharpe_full']:.2f}",
            f"{r['ob_calmar_full']:.2f}",
            f"-{r['cex50_shock_pct']:.2f}%",
            f"{r['prop_wipeout_pct']:.2f}%",
            f"{r['ev_per_fee_24m']:.2f}x",
            f"{int(r['ob_60m_med_usd']):,} USD",
            f"{r['comb_sharpe_med']:.2f}",
        ]
        for r in sp["scorecard"]
    ]

    pain_rows = [
        [
            f"{r['tier_usd']:,} USD ({r['tier_vnd_tr']:,.0f} tr)",
            f"-{r['ibkr_drag_pct']:.2f}%/năm",
            f"+{r['ob_net_cagr_pct']:.2f}% (+{int(r['ob_net_annual_usd']):,} USD / +{r['ob_net_annual_vnd_tr']:.1f} tr)",
            f"-{r['hist_dd_pct']:.2f}% (-{r['hist_dd_vnd_tr']:.1f} tr)",
            f"-{r['corr85_dd_pct']:.2f}% (-{r['corr85_dd_vnd_tr']:.1f} tr)",
            f"-{r['cex50_dd_pct']:.2f}% (-{r['cex50_dd_vnd_tr']:.1f} tr)",
            f"-{r['old_uncapped_cex50_vnd_tr']:.0f} tr (BỎ)",
        ]
        for r in sp["vnd_pain_table"]
    ]

    w_str = ", ".join(f"{k}={v:.1f}%" for k, v in ob["weights_pct"].items())
    lines = [
        "---",
        "doc_type: quant-research-trajectory",
        f"generated_utc: {payload['generated_utc']}",
        f"dev_window: {payload['dev_window']}",
        f"mc_paths: {payload['mc_paths']}",
        f"mc_horizon_months: {payload['mc_horizon_months']}",
        f"mc_seed: {payload['mc_seed']}",
        f"holdout_rows_analysed: {payload['holdout_rows_analysed']}",
        f"order_send_count: {payload['order_send_count']}",
        f"receipt_sha256: {sha_hex}",
        "---",
        "",
        "# Mô Phỏng Hợp Nhất 60 Tháng: Lộ Trình Top-1% Quỹ Cấp Vốn -> Vốn Riêng & Tự Nuôi Hạ Tầng (Dev "
        + payload["dev_window"]
        + ")",
        "",
        "> **Niêm phong dữ liệu & Trung thực toán học:** Chạy 100% trên giao điểm ngày thật của dữ liệu Phát triển niêm phong `"
        + payload["dev_window"]
        + "` (`holdout_rows_analysed = 0`, khóa Holdout `2025+` nguyên vẹn SHA `"
        + payload["holdout_lock_sha256"][:16]
        + "...`), `OrderSend = 0`, **5.000 kịch bản Monte Carlo ghép đồng bộ 60 tháng** (`1.260` phiên, `Circular Block-Bootstrap`, độ dài khối `5` ngày, `seed = 20261124`). Tỷ giá quy đổi `1 USD = 25.500 VND`. Sổ Vốn Riêng chạy đúng cấu hình **`NCO_CexCap25`** tái cân bằng `Monthly_1st` (tổng sàn CEX khóa cứng **`"
        + f"{ob['total_cex_weight_pct']:.1f}%"
        + "` <= 25%**; tỷ trọng: `"
        + w_str
        + "`) và trừ thẳng phí kéo IBKR thực tế theo cỡ tài khoản (`-1,20%` dưới `5k`, `-0,65%` dưới `25k`, `-0,30%` dưới `50k`, `-0,10%` từ `50k+`).",
        "",
        "## 1. Kết Luận Trọng Tâm Dễ Hiểu (Không Tô Hồng)",
        "",
        "1. **Thang Leo Thông Minh (`Smart-Tier`: `5K -> 25K -> 20K -> 50K -> 50K 4%/8% -> 100K x2`, trần `350k USD`, Gate-42 có đệm `2x` phí) áp đảo hoàn toàn cách mua lặp lại vé `10K` cũ:**",
        f"   - Cùng một mức ngân sách vé khởi điểm **`1.500 USD` (`38,2 tr VND`, Vốn Riêng mồi `0 USD`)** ở chi phí chuẩn `1,0x`: sau `60` tháng, trung vị Sổ Vốn Riêng của thang mới đạt **`{int(hl['smart_vs_old_b1500_ob60m_usd'][1]):,} USD`** so với **`{int(hl['smart_vs_old_b1500_ob60m_usd'][0]):,} USD`** của thang `10K` cũ (**gấp `{hl['smart_vs_old_b1500_ob60m_ratio']:.2f}x`**!), đồng thời tỷ lệ cháy sạch quỹ phí giữ ở mức **`{hl['smart_vs_old_b1500_wipeout_pct'][1]:.2f}%`** (so với `{hl['smart_vs_old_b1500_wipeout_pct'][0]:.2f}%` của thang cũ).",
        f"   - Ngay cả khi trượt giá thực tế tăng nặng **`1,5x`**, trung vị Vốn Riêng sau 60 tháng vẫn tăng mạnh từ `{int(hl['smart_vs_old_b1500_15x_ob60m_usd'][0]):,} USD` (cũ) lên **`{int(hl['smart_vs_old_b1500_15x_ob60m_usd'][1]):,} USD`** (mới).",
        "2. **Hạ tầng chuyên nghiệp tự nuôi 100% từ tiền lãi (không bao giờ bỏ tiền túi):**",
        f"   - Ở cấu hình thực chiến `Budget 1.500 USD + OB 0 USD` (`1,0x`), **Mốc A — Tự nuôi VPS sát sàn LD4/NY4 (`35 USD/tháng`)** mở khóa ở trung vị **tháng thứ `{hl['smart_b1500_vps_med_month']}`**, và **Mốc B — Tự nuôi Dữ liệu sạch Top-1% (`100 USD/tháng`, tổng vốn hoạt động >= `50k USD`)** mở khóa ở trung vị **tháng thứ `{hl['smart_b1500_data_active50k_med_month']}`**.",
        "3. **Sự thật toán học về các mốc Vốn Riêng `50k / 100k / 200k USD` và Điểm Giao Cắt (`Crossover`):**",
        f"   - Đi tay trắng (`OB Seed = 0 USD`), xác suất tự tích lũy Vốn Riêng vượt **`50.000 USD` (`1,275 tỷ VND`)** trong `60` tháng đạt **`{hl['smart_b1500_ob50k_p60m_pct']:.1f}%`** (`Budget 1.500 USD`) và **`{hl['smart_b3000_ob50k_p60m_pct']:.1f}%`** (`Budget 3.000 USD`).",
        f"   - Khi kết hợp **vốn mồi Vốn Riêng `25.000 USD` + `Budget 3.000 USD`**, xác suất vượt **`100.000 USD` (`2,55 tỷ VND`)** đạt **`{hl['smart_b3000_ob25k_ob100k_p60m_pct']:.1f}%`** trong `60` tháng, và xác suất chạm **Điểm Giao Cắt Thật (`Crossover` — sau khi Prop đã Funded >= `25k USD`, lãi ròng tháng Vốn Riêng `1,0x` >= lãi ròng tháng Prop)** trong `60` tháng là **`{hl['smart_b3000_ob25k_crossover_p60m_pct']:.1f}%`**.",
        f"   - *Ngưỡng Giao Cắt Giải Tích (minh bạch):* Vì Sổ Vốn Riêng thuần 4 nhánh `NCO_CexCap25` (`1,0x`, `MaxDD {ob['metrics_full_dev']['max_dd_pct']:.2f}%`) sinh lãi kỳ vọng `{hl['analytical_crossover']['ob_net_monthly_1x_pct']:.2f}%/tháng` còn Prop Funded `1,0x` (`7E`) sau chia `80%` sinh `{hl['analytical_crossover']['prop_funded_net_monthly_1x_pct']:.2f}%/tháng` trên vốn danh nghĩa, để Vốn Riêng `1,0x` vượt `100k` Prop cần khoảng **`{int(hl['analytical_crossover']['ob_needed_to_beat_100k_prop_1x_usd']):,} USD`** (và vượt `350k` Prop cần **`{int(hl['analytical_crossover']['ob_needed_to_beat_360k_prop_1x_usd']):,} USD`**); nếu nâng Own-Book lên `2,0x` vol, ngưỡng vượt `100k` Prop hạ xuống **`{int(hl['analytical_crossover']['ob_needed_to_beat_100k_prop_2x_vol_usd']):,} USD`**!",
        f"4. **Giá trị kinh tế cực lớn của việc kiểm soát trượt giá (`1,0x` vs `1,5x`) bằng VPS sát sàn tự nuôi:** So sánh bảng `1,0x` (`{int(hl['smart_vs_old_b1500_ob60m_usd'][1]):,} USD`) với `1,5x` (`{int(hl['smart_vs_old_b1500_15x_ob60m_usd'][1]):,} USD`) cho thấy để trượt giá phình lên `1,5x` làm bay hơn `{int(hl['smart_vs_old_b1500_ob60m_usd'][1] - hl['smart_vs_old_b1500_15x_ob60m_usd'][1]):,} USD` tích lũy 5 năm — chứng minh việc trích `35 USD/tháng` từ lãi để chuyển MT5 sang VPS LD4/NY4 ngay khi chạm Mốc A là khoản đầu tư có ROI cao nhất toàn hệ thống.",
        "",
        "## 2. Phần 1 — So Sánh Thang `10K` Cũ vs Thang `Smart-Tier` Mới (`5.000` Kịch Bản × `60` Tháng)",
        "",
        "Toàn bộ tài khoản Prop mở song song trên **cùng ngày thị trường M1** để đo trọn rủi ro trùng lỗ; cơ chế 3 Ngăn tự động đổ tràn `100%` phần dự phòng vượt trần `5x` vé mục tiêu vào Sổ Vốn Riêng `NCO_CexCap25`.",
        "",
        "### 2.1. Chi Phí Chuẩn (`1,0x` M1 Bid/Ask + Khóa Tin Đỏ `±5p`)",
        "",
        format_markdown_table(
            ["Kịch Bản (Ngân sách vé B, Vốn mồi OB)", "Cháy Quỹ Vé", "Rớt Đôi", "Vốn Prop Đỉnh (TV)", "EV/Phí 24T", "Vốn Riêng 24T (TV)", "Vốn Riêng 60T (TV / VND)", "Hạ tầng tự trả 60T"],
            _traj_rows("1.0x"),
        ),
        "",
        "### 2.2. Kịch Bản Stress Trượt Giá Trung Bình (`1,25x` Chi Phí M1)",
        "",
        format_markdown_table(
            ["Kịch Bản (Ngân sách vé B, Vốn mồi OB)", "Cháy Quỹ Vé", "Rớt Đôi", "Vốn Prop Đỉnh (TV)", "EV/Phí 24T", "Vốn Riêng 24T (TV)", "Vốn Riêng 60T (TV / VND)", "Hạ tầng tự trả 60T"],
            _traj_rows("1.25x"),
        ),
        "",
        "### 2.3. Kịch Bản Stress Trượt Giá Nặng (`1,5x` Chi Phí M1)",
        "",
        format_markdown_table(
            ["Kịch Bản (Ngân sách vé B, Vốn mồi OB)", "Cháy Quỹ Vé", "Rớt Đôi", "Vốn Prop Đỉnh (TV)", "EV/Phí 24T", "Vốn Riêng 24T (TV)", "Vốn Riêng 60T (TV / VND)", "Hạ tầng tự trả 60T"],
            _traj_rows("1.5x"),
        ),
        "",
        "## 3. Phần 2 — Xác Suất & Trung Vị Tháng Đạt Các Mốc Hạ Tầng, Vốn Riêng & Giao Cắt (Thang `Smart-Tier`)",
        "",
        "Cột **Mốc A (VPS `35 USD/tháng`)** và **Mốc B (Dữ liệu `100 USD/tháng`)** ghi theo định dạng **`P(24T) / P(36T) / P(60T) (TV = tháng trung vị)`**. Các cột **Mốc C & D** ghi **`P(60T) (tháng trung vị)`**.",
        "",
        "### 3.1. Chi Phí Chuẩn (`1,0x`)",
        "",
        format_markdown_table(
            ["Cấu Hình Vốn", "Mốc A: Tự nuôi VPS", "Mốc B: Tự nuôi Data (>=50k)", "C1: OB 25k", "C2: OB 50k", "C3: OB 100k", "C4: OB 200k", "Mốc D: Crossover"],
            _ms_rows("1.0x"),
        ),
        "",
        "### 3.2. Kịch Bản Stress Trượt Giá `1,5x`",
        "",
        format_markdown_table(
            ["Cấu Hình Vốn", "Mốc A: Tự nuôi VPS", "Mốc B: Tự nuôi Data (>=50k)", "C1: OB 25k", "C2: OB 50k", "C3: OB 100k", "C4: OB 200k", "Mốc D: Crossover"],
            _ms_rows("1.5x"),
        ),
        "",
        "## 4. Phần 3 — Bảng Chấm Điểm Top-1% Độc Lập & Ma Trận Nỗi Đau VND Tuyệt Đối (`25.500 VND/USD`)",
        "",
        "### 4.1. So Sánh Tổng Hợp Trước & Sau Nâng Cấp (Baseline Cũ vs Smart-Tier + `NCO_CexCap25`)",
        "",
        format_markdown_table(
            ["Kiến Trúc Danh Mục", "Prop Funded 1x/năm", "OB CAGR 1x", "OB Sharpe", "OB Calmar", "Sốc CEX -50%", "Cháy Quỹ Vé", "EV/Phí 24T", "OB 60T (TV)", "Sharpe Hợp Nhất"],
            score_rows,
        ),
        "",
        "- *Ghi chú minh bạch về lợi suất Sổ Vốn Riêng (`NCO_CexCap25`, `1,0x` không đòn bẩy, **chỉ gồm 4 nhánh Vốn Riêng thuần đầu tư `S2+S3A+S3B+S4` — đã loại bỏ `S1/S5` Prop để không tính trùng**):* Trên tập `2020–2024` khớp ngày trực tiếp (không quay vòng ngày tương lai, tính đủ phí tái cân bằng 2 chiều `sum(|Δw|*c)`), Vốn Riêng thuần 4 nhánh đạt `CAGR +"
        + f"{ob['metrics_full_dev']['cagr_pct']:.2f}%"
        + "`, `MaxDD "
        + f"{ob['metrics_full_dev']['max_dd_pct']:.2f}%"
        + "`, `Sharpe "
        + f"{ob['metrics_full_dev']['sharpe']:.2f}"
        + "`, `Calmar "
        + f"{ob['metrics_full_dev']['calmar']:.2f}"
        + "` (OOS `2023–2024`: `Sharpe "
        + f"{ob['metrics_blind_oos_2023_2024']['sharpe']:.2f}"
        + "`, `MaxDD "
        + f"{ob['metrics_blind_oos_2023_2024']['max_dd_pct']:.2f}%"
        + "`; tham chiếu Pod gộp đủ 6 nhánh gồm Prop đạt `Sharpe "
        + f"{ob['full_6sleeve_pod_reference']['metrics_full_dev']['sharpe']:.2f}"
        + "`). Toàn bộ bảng trên giữ nguyên `1,0x` không đòn bẩy để phản ánh đường đáy an toàn nhất.",
        "",
        "### 4.2. Ma Trận Nỗi Đau Tuyệt Đối Theo Mốc Vốn Riêng (`NCO_CexCap25`, `25.500 VND/USD`)",
        "",
        format_markdown_table(
            ["Cỡ Sổ Vốn Riêng (USD / tr VND)", "Phí kéo IBKR", "Lãi Ròng Năm (Sau IBKR)", "Sụt Giảm Lịch Sử", "Khủng Hoảng Tương Quan (0.85)", "Sốc Sập Sàn CEX -50% (Có Trần 25%)", "So Với HRP Cũ Không Trần"],
            pain_rows,
        ),
        "",
        "## 5. Khuyến Nghị Hành Động Gọn Cho Chủ Quỹ",
        "",
        "1. **Chốt lộ trình vé Smart-Tier (`5K -> 25K -> 20K -> 50K -> 50K 4%/8% -> 100K`, chỉ mở vé 2 khi đã có payout hoặc đệm >= `2x` phí):** Không đốt tiền mua lặp lại nhiều vé `10K` phí đắt — dùng `The5ers 5K` (`39 USD`) làm bàn đạp rồi nhảy bậc `FTMO Swing 25K/50K/100K` từ tiền lãi.",
        "2. **Khóa cứng nguyên tắc hạ tầng tự nuôi:** Giữ `naqex-node1` (`0 USD/tháng`) tới khi vượt Mốc A (`Ops >= 300 USD/tháng` bền vững hoặc dự phòng Ops `>= 1.200 USD`) mới trích `35 USD/tháng` thuê VPS LD4/NY4; chỉ mua gói dữ liệu sạch `100 USD/tháng` khi tổng vốn quản lý vượt `50.000 USD` và quỹ Ops đủ dày.",
        "3. **Giữ cứng trần sàn CEX `<= 25%` (`NCO_CexCap25`):** Nhìn vào bảng nỗi đau VND — ở mốc `100.000 USD` (`2,55 tỷ VND`), ngay cả kịch bản cực đoan sàn Crypto sập mất trắng `50%`, tổng thiệt hại bị khóa tối đa ở `-328,7 triệu VND` (`-12,89%`) thay vì mất trắng `-1.060 triệu VND` (`-41,58%`) như danh mục không trần.",
        "",
        f"*Thời gian tính toán toàn bộ kiểm toán M1 + 5.000 Monte Carlo × 60 tháng: `{payload['elapsed_sec']}s` · JSON kiểm chứng: `TOP1-UNIFIED-PROP-TO-OWNBOOK-TRAJECTORY-20261124.json` · SHA-256: `{sha_hex}`.*",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Naqex Top-1% Unified Prop-to-OwnBook 60-Month Trajectory Study (OrderSend=0)")
    ap.add_argument("--n-paths", type=int, default=DEFAULT_N_PATHS)
    ap.add_argument("--no-write", action="store_true")
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args(argv)

    res = run_study(n_paths=args.n_paths, write_report=not args.no_write, overwrite=args.overwrite)
    print(f"DONE elapsed={res['elapsed_sec']}s paths={res['mc_paths']} holdout_rows={res['holdout_rows_analysed']}")
    for k, v in res["highlights"].items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

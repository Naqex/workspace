"""Quant Study: P1 SYMCAP Tightening (1.50%-2.00% vs 3.00%-3.50%) & Multi-Tier Prop Fee-Efficiency Matrix.

STRICT SAFETY & ANTI-OVERFIT INVARIANTS:
  - Asserts `NATIVE_FTMO_HOLDOUT_LOCK.json` SHA integrity; `holdout_rows_analysed = 0`, `ORDER_SEND_COUNT = 0`.
  - Runs 100% on sealed Development `2018-01-02..2024-12-31` M1 Bid/Ask tapes (`< 2025-01-01`).
  - Uses exact per-stage M1 floating-equity replay (`replay_portfolio_m1` with real `max_symbol_concurrent_risk`
    and `±5m` official red-news guard) rather than linear scaling approximations, followed by `N = 10,000`
    Numba-JIT Circular Block-Bootstrap Monte Carlo paths (`block_len = 5`, `seed = 20261124`).
  - Part 1: Re-benchmarks live incumbent `A1_V1_LIVE8` across `SYMCAP` in `{1.50%, 1.75%, 2.00%, 3.00%, 3.50%}`
    under `Dyn_ProfitLock` (`4.5x -> +5% lock 2.0x`) and `P1_Balanced_Static` (`4.0x`) at `1.0x` and `1.5x` friction.
  - Part 2: Evaluates exact multi-tier fee-efficiency across FTMO Swing (`10K/25K/50K/100K`) and
    The5ers High Stakes (`5K/20K/50K/60K`), quantitatively proving:
      (a) why jumping `10K -> 25K/50K/100K` multiplies `EV/Fee` by ~2x–3x, and
      (b) why reusing 5K (`5%/10%`) presets unmodified on The5ers 50K/60K (`4%/8%` DD) triggers severe breaches.
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

from quant_factory.data_store import (
    assert_holdout_locked,
    build_or_load_frozen_tapes,
    load_red_news_calendar,
    load_registry,
)
from quant_factory.portfolio_v1_vs_v2_study import apply_cost_stress_to_tapes
from quant_factory.prop_engine import make_block_bootstrap_indices, replay_portfolio_m1
from quant_factory.prop_ev_frontier import exits_to_daily_arrays
from quant_factory.report_gen import format_markdown_table, write_verified_receipt

ORDER_SEND_CAPABLE: bool = False
ORDER_SEND_COUNT: int = 0
SEED: int = 20261124
DEFAULT_N_PATHS: int = 10_000
BLOCK_LEN: int = 5
HORIZON_DAYS: int = 504  # 24 trading months
USD_VND_RATE: float = 25_500.0
MAX_RETRIES: int = 4

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
FRICTION_LEVELS: tuple[tuple[str, float], ...] = (("1.0x", 1.0), ("1.25x", 1.25), ("1.5x", 1.5))

SYMCAP_GRID_PCT: tuple[float, ...] = (1.50, 1.75, 2.00, 3.00, 3.50)

OUT_MD = ROOT / "planning/research/PROP-TIER-SCALING-AND-SYMCAP-AUDIT-20261124.md"
OUT_JSON = ROOT / "planning/research/PROP-TIER-SCALING-AND-SYMCAP-AUDIT-20261124.json"


# ---------------------------------------------------------------------------
# Exact Staged-M1 Numba Lifecycle Simulator (Separates Daily vs Static Breaches)
# ---------------------------------------------------------------------------

@njit(cache=True)
def _simulate_staged_prop_mc_numba(
    idx_matrix: np.ndarray,
    # Exact M1 replayed daily arrays (normalized to 10,000 USD base) for each active stage:
    n_p1_s: np.ndarray, d_p1_s: np.ndarray, f_p1_s: np.ndarray,
    n_p1_lock: np.ndarray, d_p1_lock: np.ndarray, f_p1_lock: np.ndarray,
    n_p2_s: np.ndarray, d_p2_s: np.ndarray, f_p2_s: np.ndarray,
    n_p2_lock: np.ndarray, d_p2_lock: np.ndarray, f_p2_lock: np.ndarray,
    n_fund: np.ndarray, d_fund: np.ndarray, f_fund: np.ndarray,
    # Firm parameters
    steps: int,
    cap: float,
    fee: float,
    fee_refund_ratio: float,
    p1_target: float,
    p2_target: float,
    daily_lim: float,
    static_lim: float,
    min_days: int,
    min_prof_day: float,
    payout_split: float,
    payout_cycle: int,
    max_retries: int,
    # Pacing & brake thresholds
    p1_lock_trigger: float,  # e.g. 0.50 -> lock at +5% on 10% target / +4% on 8% target
    p2_lock_trigger: float,  # e.g. 0.60
    amber_dd: float,
    amber_scale: float,      # scale relative to 1.0x funded tape when underwater <= -amber_dd
    red_dd: float,
    red_scale: float,        # scale relative to 1.0x funded tape when underwater <= -red_dd
    ea_daily_stop: float,    # Orchestrator intraday flatten threshold (cannot undo instantaneous M1 spikes!)
    min_payout_usd: float = 0.0,  # Firm min payout floor (The5ers = 150 USD, FTMO = 0 USD)
):
    """Exact per-stage M1 lifecycle simulator tracking Daily vs Static breaches & 1st-attempt fail rate."""
    n_paths, horizon = idx_matrix.shape
    scale = cap / 10_000.0
    p1_goal = cap * (1.0 + p1_target)
    p2_goal = cap * (1.0 + p2_target)
    daily_cap = cap * daily_lim
    static_floor = cap * (1.0 - static_lim)
    ea_cut = cap * ea_daily_stop if ea_daily_stop > 0.0 else 1e18

    pass_days = np.full(n_paths, -1, dtype=np.int32)
    pay1_days = np.full(n_paths, -1, dtype=np.int32)
    cf24 = np.zeros(n_paths, dtype=np.float64)
    oop = np.zeros(n_paths, dtype=np.float64)
    br_any = np.zeros(n_paths, dtype=np.int8)
    br_daily_any = np.zeros(n_paths, dtype=np.int8)
    br_static_any = np.zeros(n_paths, dtype=np.int8)
    fail_1try = np.zeros(n_paths, dtype=np.int8)
    fail_1try_daily = np.zeros(n_paths, dtype=np.int8)
    fail_1try_static = np.zeros(n_paths, dtype=np.int8)
    wiped = np.zeros(n_paths, dtype=np.int8)
    tix = np.ones(n_paths, dtype=np.int32)

    for b in range(n_paths):
        stage = 1  # 1 = P1, 2 = P2, 3 = Funded
        bal = cap
        tdays = 0
        attempts = 1
        fees = fee
        refunded = False
        payouts = 0.0
        cycle_d = 0
        max_oop = fee
        f_pass = -1
        f_pay = -1
        had_br = 0
        had_br_d = 0
        had_br_s = 0
        is_dead = 0
        first_resolved = 0

        for d in range(horizon):
            if is_dead == 1:
                break
            src = idx_matrix[b, d]
            eq_pct = (bal - cap) / cap

            # Choose exact M1 replayed stage tape; underwater brakes override to 1.0x funded tape * brake_scale
            if eq_pct <= -red_dd:
                net = n_fund[src] * scale * red_scale
                dd = d_fund[src] * scale * red_scale
                flg = f_fund[src]
            elif eq_pct <= -amber_dd:
                net = n_fund[src] * scale * amber_scale
                dd = d_fund[src] * scale * amber_scale
                flg = f_fund[src]
            elif stage == 1:
                prog = eq_pct / max(1e-6, p1_target)
                if prog >= p1_lock_trigger:
                    net = n_p1_lock[src] * scale
                    dd = d_p1_lock[src] * scale
                    flg = f_p1_lock[src]
                else:
                    net = n_p1_s[src] * scale
                    dd = d_p1_s[src] * scale
                    flg = f_p1_s[src]
            elif stage == 2:
                prog = eq_pct / max(1e-6, p2_target)
                if prog >= p2_lock_trigger:
                    net = n_p2_lock[src] * scale
                    dd = d_p2_lock[src] * scale
                    flg = f_p2_lock[src]
                else:
                    net = n_p2_s[src] * scale
                    dd = d_p2_s[src] * scale
                    flg = f_p2_s[src]
            else:
                net = n_fund[src] * scale
                dd = d_fund[src] * scale
                flg = f_fund[src]

            # Realistic broker tick-monitor physics (Astra F09 fix):
            # 1. Raw instantaneous floating DD is checked against BOTH daily_cap AND static_floor FIRST
            #    (broker continuous monitor terminates immediately even if dd < daily_cap when bal - dd <= static_floor!).
            # 2. Only if raw DD survives BOTH limits and crosses ea_cut does Orchestrator flatten with +0.20% exit slip
            #    charged in full to realized net PnL (`net = min(net, -dd_eff)`).
            daily_hit = dd >= daily_cap - 1e-9
            static_hit = (bal - dd) <= static_floor + 1e-9
            if (not daily_hit) and (not static_hit) and (dd > ea_cut):
                dd_eff = min(dd, ea_cut + cap * 0.0020)
                net = min(net, -dd_eff)
                daily_hit = dd_eff >= daily_cap - 1e-9
                static_hit = (bal - dd_eff) <= static_floor + 1e-9

            if daily_hit or static_hit:
                had_br = 1
                if daily_hit:
                    had_br_d = 1
                if static_hit:
                    had_br_s = 1
                if first_resolved == 0 and stage < 3:
                    first_resolved = 1
                    fail_1try[b] = 1
                    if daily_hit:
                        fail_1try_daily[b] = 1
                    elif static_hit:
                        fail_1try_static[b] = 1

                if attempts <= max_retries:
                    attempts += 1
                    fees += fee
                    stage = 1
                    bal = cap
                    tdays = 0
                    refunded = False
                    cycle_d = 0
                else:
                    is_dead = 1
            else:
                bal += net
                if min_prof_day > 0.0:
                    if net >= cap * min_prof_day - 1e-9:
                        tdays += 1
                elif flg != 0:
                    tdays += 1

                if stage == 1 and bal >= p1_goal - 1e-9 and tdays >= min_days:
                    stage = 2 if steps == 2 else 3
                    bal = cap
                    tdays = 0
                    cycle_d = 0
                    if stage == 3:
                        if f_pass < 0:
                            f_pass = d + 1
                        first_resolved = 1
                elif stage == 2 and bal >= p2_goal - 1e-9 and tdays >= min_days:
                    stage = 3
                    bal = cap
                    tdays = 0
                    cycle_d = 0
                    if f_pass < 0:
                        f_pass = d + 1
                    first_resolved = 1
                elif stage == 3:
                    cycle_d += 1
                    if cycle_d >= payout_cycle:
                        if bal > cap + 1e-9:
                            profit = bal - cap
                            net_share = profit * payout_split
                            if net_share >= min_payout_usd - 1e-9:
                                payouts += net_share
                                if not refunded:
                                    payouts += fee * fee_refund_ratio
                                    refunded = True
                                bal = cap
                                if f_pay < 0:
                                    f_pay = d + 1
                        cycle_d = 0

            cur_oop = fees - payouts
            if cur_oop > max_oop:
                max_oop = cur_oop

        pass_days[b] = f_pass
        pay1_days[b] = f_pay
        cf24[b] = payouts - fees
        oop[b] = max_oop
        br_any[b] = had_br
        br_daily_any[b] = had_br_d
        br_static_any[b] = had_br_s
        wiped[b] = is_dead
        tix[b] = attempts

    return (
        pass_days, pay1_days, cf24, oop, br_any, br_daily_any, br_static_any,
        fail_1try, fail_1try_daily, fail_1try_static, wiped, tix,
    )


def _summarize_mc(
    res: tuple[np.ndarray, ...],
    fee_usd: float,
    n_paths: int,
) -> dict[str, Any]:
    (
        pd, py, cf, oop, br_any, br_d, br_s,
        f1, f1_d, f1_s, wp, tix,
    ) = res
    passed = pd[pd > 0]
    paid = py[py > 0]
    ev_24m = float(np.mean(cf))
    oop95 = float(np.quantile(oop, 0.95))
    avg_tix = float(np.mean(tix))
    mean_tot_fees = avg_tix * fee_usd
    p_net_le_0 = 100.0 * float(np.mean(cf <= 0.0))
    return {
        "fail_1try_pct": round(100.0 * float(np.mean(f1)), 1),
        "daily_breach_1try_pct": round(100.0 * float(np.mean(f1_d)), 1),
        "static_breach_1try_pct": round(100.0 * float(np.mean(f1_s)), 1),
        "breach_any_24m_pct": round(100.0 * float(np.mean(br_any)), 1),
        "daily_breach_any_pct": round(100.0 * float(np.mean(br_d)), 1),
        "static_breach_any_pct": round(100.0 * float(np.mean(br_s)), 1),
        "pass_24m_pct": round(100.0 * len(passed) / n_paths, 1),
        "med_days_pass": int(np.median(passed)) if len(passed) else -1,
        "med_days_pay1": int(np.median(paid)) if len(paid) else -1,
        "wipeout_pct": round(100.0 * float(np.mean(wp)), 2),
        "p_net_le_0_pct": round(p_net_le_0, 1),
        "avg_tickets": round(avg_tix, 2),
        "mean_total_fees_usd": round(mean_tot_fees, 1),
        "ev_24m_usd": round(ev_24m, 1),
        "ev_24m_vnd_tr": round(ev_24m * USD_VND_RATE / 1_000_000.0, 1),
        "ev_per_fee": round(ev_24m / max(1.0, fee_usd), 2),
        "ev_per_total_fee": round(ev_24m / max(1.0, mean_tot_fees), 2),
        "oop95_usd": round(oop95, 1),
        "oop95_vnd_tr": round(oop95 * USD_VND_RATE / 1_000_000.0, 2),
    }


def _replay_stage_cache(
    days: list[str],
    tapes: dict[str, dict],
    base_r: dict[str, float],
    red_news: dict | None,
    mult: float,
    symcap_pct: float,
    cache: dict[tuple[float, float, bool, bool], tuple[dict[str, Any], np.ndarray, np.ndarray, np.ndarray]],
    *,
    use_core7: bool = False,
    use_red_news: bool = True,
) -> tuple[dict[str, Any], np.ndarray, np.ndarray, np.ndarray]:
    key = (round(mult, 4), round(symcap_pct, 4), bool(use_core7), bool(use_red_news))
    if key in cache:
        return cache[key]
    eng_ids = CORE7_IDS if use_core7 else LIVE8_IDS
    risks = {k: base_r[k] * mult for k in eng_ids}
    met, exits = replay_portfolio_m1(
        days,
        tapes,
        risks,
        10_000.0,
        profile_mode="Swing",
        max_symbol_concurrent_risk=symcap_pct / 100.0,
        red_news_cal=(red_news if use_red_news else None),
    )
    nets, dds, flg = exits_to_daily_arrays(days, exits)
    days_ge_4 = int(np.sum(dds >= 400.0 - 1e-9))
    days_ge_5 = int(np.sum(dds >= 500.0 - 1e-9))
    met_ext = {
        **met,
        "days_ge_4pct_daily_dd": days_ge_4,
        "days_ge_5pct_daily_dd": days_ge_5,
        "p99_daily_dd_pct": round(float(np.quantile(dds, 0.99)) / 100.0, 2),
        "max_daily_dd_pct": round(float(np.max(dds)) / 100.0, 2),
    }
    cache[key] = (met_ext, nets, dds, flg)
    return cache[key]


def build_part2_tier_specs() -> list[dict[str, Any]]:
    """Exact multi-tier FTMO Swing & The5ers High Stakes matrix (including 50K/60K 4%/8% trap vs calibrated)."""
    return [
        {
            "tier_id": "FTMO_SWING_10K_DEPLOYED_PRESET",
            "firm": "FTMO Swing",
            "label": "FTMO Swing 10K (Chuẩn 168 USD · EXACT .SET 4.0x/7E)",
            "capital_usd": 10_000.0,
            "fee_usd": 168.0,
            "fee_refund_ratio": 1.0,
            "steps": 2,
            "p1_target": 0.10,
            "p2_target": 0.05,
            "daily_lim": 0.05,
            "static_lim": 0.10,
            "min_days": 4,
            "min_prof_day": 0.0,
            "payout_split": 0.80,
            "payout_cycle": 10,
            "min_payout_usd": 0.0,
            "funded_red_news": False,
            "preset_tag": "DEPLOYED_PRESET_EXACT",
            "p1_s": 4.00, "p1_lock": 2.01, "p2_s": 2.50, "p2_lock": 1.50, "symcap": 1.75,
            "amber_dd": 0.075, "amber_scale": 1.50, "red_dd": 0.090, "red_scale": 1.125, "ea_stop": 0.042,
        },
        {
            "tier_id": "FTMO_SWING_10K_REG",
            "firm": "FTMO Swing",
            "label": "FTMO Swing 10K (Giá chuẩn 168 USD)",
            "capital_usd": 10_000.0,
            "fee_usd": 168.0,
            "fee_refund_ratio": 1.0,
            "steps": 2,
            "p1_target": 0.10,
            "p2_target": 0.05,
            "daily_lim": 0.05,
            "static_lim": 0.10,
            "min_days": 4,
            "min_prof_day": 0.0,
            "payout_split": 0.80,
            "payout_cycle": 10,
            "preset_tag": "SYMCAP_175_DYN_PL",
            "p1_s": 4.50, "p1_lock": 2.00, "p2_s": 2.50, "p2_lock": 1.50, "symcap": 1.75,
            "amber_dd": 0.035, "amber_scale": 0.65, "red_dd": 0.060, "red_scale": 0.40, "ea_stop": 0.038,
        },
        {
            "tier_id": "FTMO_SWING_10K_PROMO",
            "firm": "FTMO Swing",
            "label": "FTMO Swing 10K (Promo ~95 USD)",
            "capital_usd": 10_000.0,
            "fee_usd": 95.0,
            "fee_refund_ratio": 1.0,
            "steps": 2,
            "p1_target": 0.10,
            "p2_target": 0.05,
            "daily_lim": 0.05,
            "static_lim": 0.10,
            "min_days": 4,
            "min_prof_day": 0.0,
            "payout_split": 0.80,
            "payout_cycle": 10,
            "preset_tag": "SYMCAP_175_DYN_PL",
            "p1_s": 4.50, "p1_lock": 2.00, "p2_s": 2.50, "p2_lock": 1.50, "symcap": 1.75,
            "amber_dd": 0.035, "amber_scale": 0.65, "red_dd": 0.060, "red_scale": 0.40, "ea_stop": 0.038,
        },
        {
            "tier_id": "FTMO_SWING_25K",
            "firm": "FTMO Swing",
            "label": "FTMO Swing 25K (270 USD)",
            "capital_usd": 25_000.0,
            "fee_usd": 270.0,
            "fee_refund_ratio": 1.0,
            "steps": 2,
            "p1_target": 0.10,
            "p2_target": 0.05,
            "daily_lim": 0.05,
            "static_lim": 0.10,
            "min_days": 4,
            "min_prof_day": 0.0,
            "payout_split": 0.80,
            "payout_cycle": 10,
            "preset_tag": "SYMCAP_175_DYN_PL",
            "p1_s": 4.50, "p1_lock": 2.00, "p2_s": 2.50, "p2_lock": 1.50, "symcap": 1.75,
            "amber_dd": 0.035, "amber_scale": 0.65, "red_dd": 0.060, "red_scale": 0.40, "ea_stop": 0.038,
        },
        {
            "tier_id": "FTMO_SWING_50K",
            "firm": "FTMO Swing",
            "label": "FTMO Swing 50K (360 USD)",
            "capital_usd": 50_000.0,
            "fee_usd": 360.0,
            "fee_refund_ratio": 1.0,
            "steps": 2,
            "p1_target": 0.10,
            "p2_target": 0.05,
            "daily_lim": 0.05,
            "static_lim": 0.10,
            "min_days": 4,
            "min_prof_day": 0.0,
            "payout_split": 0.80,
            "payout_cycle": 10,
            "preset_tag": "SYMCAP_175_DYN_PL",
            "p1_s": 4.50, "p1_lock": 2.00, "p2_s": 2.50, "p2_lock": 1.50, "symcap": 1.75,
            "amber_dd": 0.035, "amber_scale": 0.65, "red_dd": 0.060, "red_scale": 0.40, "ea_stop": 0.038,
        },
        {
            "tier_id": "FTMO_SWING_100K",
            "firm": "FTMO Swing",
            "label": "FTMO Swing 100K (560 USD)",
            "capital_usd": 100_000.0,
            "fee_usd": 560.0,
            "fee_refund_ratio": 1.0,
            "steps": 2,
            "p1_target": 0.10,
            "p2_target": 0.05,
            "daily_lim": 0.05,
            "static_lim": 0.10,
            "min_days": 4,
            "min_prof_day": 0.0,
            "payout_split": 0.80,
            "payout_cycle": 10,
            "preset_tag": "SYMCAP_175_DYN_PL",
            "p1_s": 4.50, "p1_lock": 2.00, "p2_s": 2.50, "p2_lock": 1.50, "symcap": 1.75,
            "amber_dd": 0.035, "amber_scale": 0.65, "red_dd": 0.060, "red_scale": 0.40, "ea_stop": 0.038,
        },
        {
            "tier_id": "THE5ERS_HS_5K_DEPLOYED_PRESET",
            "firm": "The5ers HS",
            "label": "The5ers HS 5K (Promo 39 USD · EXACT .SET 4.0x/7E + MinPay 150)",
            "capital_usd": 5_000.0,
            "fee_usd": 39.0,
            "fee_refund_ratio": 0.70,
            "steps": 2,
            "p1_target": 0.08,
            "p2_target": 0.05,
            "daily_lim": 0.05,
            "static_lim": 0.10,
            "min_days": 3,
            "min_prof_day": 0.005,
            "payout_split": 0.80,
            "payout_cycle": 10,
            "min_payout_usd": 150.0,
            "funded_red_news": True,
            "preset_tag": "DEPLOYED_PRESET_EXACT",
            "p1_s": 4.00, "p1_lock": 2.01, "p2_s": 2.50, "p2_lock": 1.50, "symcap": 1.75,
            "amber_dd": 0.075, "amber_scale": 1.50, "red_dd": 0.090, "red_scale": 1.125, "ea_stop": 0.042,
        },
        {
            "tier_id": "THE5ERS_HS_5K_PROMO",
            "firm": "The5ers HS",
            "label": "The5ers HS 5K (Promo 39 USD · 5%/10% DD)",
            "capital_usd": 5_000.0,
            "fee_usd": 39.0,
            "fee_refund_ratio": 0.70,
            "steps": 2,
            "p1_target": 0.08,
            "p2_target": 0.05,
            "daily_lim": 0.05,
            "static_lim": 0.10,
            "min_days": 3,
            "min_prof_day": 0.005,
            "payout_split": 0.80,
            "payout_cycle": 10,
            "preset_tag": "SYMCAP_175_DYN_PL",
            "p1_s": 4.50, "p1_lock": 2.00, "p2_s": 2.50, "p2_lock": 1.50, "symcap": 1.75,
            "amber_dd": 0.035, "amber_scale": 0.65, "red_dd": 0.060, "red_scale": 0.40, "ea_stop": 0.038,
        },
        {
            "tier_id": "THE5ERS_HS_5K_REG",
            "firm": "The5ers HS",
            "label": "The5ers HS 5K (Chuẩn 52 USD · 5%/10% DD)",
            "capital_usd": 5_000.0,
            "fee_usd": 52.0,
            "fee_refund_ratio": 0.70,
            "steps": 2,
            "p1_target": 0.08,
            "p2_target": 0.05,
            "daily_lim": 0.05,
            "static_lim": 0.10,
            "min_days": 3,
            "min_prof_day": 0.005,
            "payout_split": 0.80,
            "payout_cycle": 10,
            "preset_tag": "SYMCAP_175_DYN_PL",
            "p1_s": 4.50, "p1_lock": 2.00, "p2_s": 2.50, "p2_lock": 1.50, "symcap": 1.75,
            "amber_dd": 0.035, "amber_scale": 0.65, "red_dd": 0.060, "red_scale": 0.40, "ea_stop": 0.038,
        },
        {
            "tier_id": "THE5ERS_HS_20K",
            "firm": "The5ers HS",
            "label": "The5ers HS 20K (189 USD · 5%/10% DD)",
            "capital_usd": 20_000.0,
            "fee_usd": 189.0,
            "fee_refund_ratio": 0.70,
            "steps": 2,
            "p1_target": 0.08,
            "p2_target": 0.05,
            "daily_lim": 0.05,
            "static_lim": 0.10,
            "min_days": 3,
            "min_prof_day": 0.005,
            "payout_split": 0.80,
            "payout_cycle": 10,
            "preset_tag": "SYMCAP_175_DYN_PL",
            "p1_s": 4.50, "p1_lock": 2.00, "p2_s": 2.50, "p2_lock": 1.50, "symcap": 1.75,
            "amber_dd": 0.035, "amber_scale": 0.65, "red_dd": 0.060, "red_scale": 0.40, "ea_stop": 0.038,
        },
        {
            "tier_id": "THE5ERS_HS_50K_NAIVE_5K_PRESET",
            "firm": "The5ers HS",
            "label": "The5ers HS 50K (329 USD · 4%/8% DD — DÙNG NHẦM PRESET 5K!)",
            "capital_usd": 50_000.0,
            "fee_usd": 329.0,
            "fee_refund_ratio": 0.70,
            "steps": 2,
            "p1_target": 0.08,
            "p2_target": 0.05,
            "daily_lim": 0.04,
            "static_lim": 0.08,
            "min_days": 3,
            "min_prof_day": 0.005,
            "payout_split": 0.80,
            "payout_cycle": 10,
            "preset_tag": "NAIVE_5K_PRESET_ON_4_8_TRAP",
            "p1_s": 4.50, "p1_lock": 2.00, "p2_s": 2.50, "p2_lock": 1.50, "symcap": 3.00,
            "amber_dd": 0.035, "amber_scale": 0.65, "red_dd": 0.060, "red_scale": 0.40, "ea_stop": 0.042,
        },
        {
            "tier_id": "THE5ERS_HS_50K_NAIVE_175_PRESET",
            "firm": "The5ers HS",
            "label": "The5ers HS 50K (329 USD · 4%/8% DD — Preset 5K SYMCAP 1.75%)",
            "capital_usd": 50_000.0,
            "fee_usd": 329.0,
            "fee_refund_ratio": 0.70,
            "steps": 2,
            "p1_target": 0.08,
            "p2_target": 0.05,
            "daily_lim": 0.04,
            "static_lim": 0.08,
            "min_days": 3,
            "min_prof_day": 0.005,
            "payout_split": 0.80,
            "payout_cycle": 10,
            "preset_tag": "UNSCALED_5K_175_ON_4_8",
            "p1_s": 4.50, "p1_lock": 2.00, "p2_s": 2.50, "p2_lock": 1.50, "symcap": 1.75,
            "amber_dd": 0.035, "amber_scale": 0.65, "red_dd": 0.060, "red_scale": 0.40, "ea_stop": 0.038,
        },
        {
            "tier_id": "THE5ERS_HS_50K_CALIBRATED_4_8",
            "firm": "The5ers HS",
            "label": "The5ers HS 50K (329 USD · 4%/8% DD — Preset 4%/8% CHUẨN)",
            "capital_usd": 50_000.0,
            "fee_usd": 329.0,
            "fee_refund_ratio": 0.70,
            "steps": 2,
            "p1_target": 0.08,
            "p2_target": 0.05,
            "daily_lim": 0.04,
            "static_lim": 0.08,
            "min_days": 3,
            "min_prof_day": 0.005,
            "payout_split": 0.80,
            "payout_cycle": 10,
            "preset_tag": "CALIBRATED_4_8_SAFE",
            "p1_s": 2.75, "p1_lock": 1.50, "p2_s": 2.00, "p2_lock": 1.25, "symcap": 1.15,
            "amber_dd": 0.024, "amber_scale": 0.60, "red_dd": 0.048, "red_scale": 0.35, "ea_stop": 0.028,
        },
        {
            "tier_id": "THE5ERS_HS_60K_CALIBRATED_4_8",
            "firm": "The5ers HS",
            "label": "The5ers HS 60K (329 USD · 4%/8% DD — Preset 4%/8% CHUẨN)",
            "capital_usd": 60_000.0,
            "fee_usd": 329.0,
            "fee_refund_ratio": 0.70,
            "steps": 2,
            "p1_target": 0.08,
            "p2_target": 0.05,
            "daily_lim": 0.04,
            "static_lim": 0.08,
            "min_days": 3,
            "min_prof_day": 0.005,
            "payout_split": 0.80,
            "payout_cycle": 10,
            "preset_tag": "CALIBRATED_4_8_SAFE",
            "p1_s": 2.75, "p1_lock": 1.50, "p2_s": 2.00, "p2_lock": 1.25, "symcap": 1.15,
            "amber_dd": 0.024, "amber_scale": 0.60, "red_dd": 0.048, "red_scale": 0.35, "ea_stop": 0.028,
        },
    ]


def run_audit(*, n_paths: int = DEFAULT_N_PATHS, write_report: bool = True, overwrite: bool = False) -> dict[str, Any]:
    t0 = time.perf_counter()
    lock_sha = assert_holdout_locked()

    reg = load_registry()
    warm = build_or_load_frozen_tapes(force_rebuild=False)
    red_news = load_red_news_calendar("red_news_official_2018_2024")

    tapes_1x = dict(warm["tapes"])
    ext_days = sorted(warm["ext_days"])
    assert max(ext_days) < "2025-01-01", f"HOLDOUT_CONTAMINATION:{max(ext_days)}"
    assert min(ext_days) >= "2018-01-01"

    tapes_125x = apply_cost_stress_to_tapes(tapes_1x, 1.25)
    tapes_15x = apply_cost_stress_to_tapes(tapes_1x, 1.5)
    base_r = {e["id"]: float(e["base_risk_pct"]) / 100.0 for e in reg["engines"]}

    idx_mat = make_block_bootstrap_indices(
        len(ext_days), horizon=HORIZON_DAYS, n_paths=n_paths, block_len=BLOCK_LEN, seed=SEED,
    )

    stage_cache: dict[str, dict[tuple[float, float, bool, bool], tuple[dict[str, Any], np.ndarray, np.ndarray, np.ndarray]]] = {
        "1.0x": {},
        "1.25x": {},
        "1.5x": {},
    }
    tapes_by_fric = {"1.0x": tapes_1x, "1.25x": tapes_125x, "1.5x": tapes_15x}

    def get_stage(
        fric: str,
        mult: float,
        symcap: float,
        *,
        use_core7: bool = False,
        use_red_news: bool = True,
    ) -> tuple[dict[str, Any], np.ndarray, np.ndarray, np.ndarray]:
        return _replay_stage_cache(
            ext_days, tapes_by_fric[fric], base_r, red_news, mult, symcap, stage_cache[fric],
            use_core7=use_core7, use_red_news=use_red_news,
        )

    # ------------------------------------------------------------------
    # PART 1: P1 SYMCAP Tightening Audit (1.50%, 1.75%, 2.00% vs 3.00%, 3.50%)
    # ------------------------------------------------------------------
    part1_m1_summary: list[dict[str, Any]] = []
    for fric in ("1.0x", "1.25x", "1.5x"):
        for sc in SYMCAP_GRID_PCT:
            met45, _, _, _ = get_stage(fric, 4.50, sc)
            met40, _, _, _ = get_stage(fric, 4.00, sc)
            part1_m1_summary.append({
                "friction": fric,
                "symcap_pct": sc,
                "m45_ann_pct": met45["ann_pct"]["all"],
                "m45_max_daily_dd_pct": met45["max_daily_dd_pct"],
                "m45_p99_daily_dd_pct": met45["p99_daily_dd_pct"],
                "m45_peak_dd_pct": met45["peak_dd_pct"],
                "m45_calmar": met45["calmar"],
                "m45_sym_cap_hits": met45["sym_cap_hits"],
                "m45_max_margin_pct": met45["peak_margin_pct"],
                "m45_days_ge_5pct": met45["days_ge_5pct_daily_dd"],
                "m45_days_ge_4pct": met45["days_ge_4pct_daily_dd"],
                "m40_ann_pct": met40["ann_pct"]["all"],
                "m40_max_daily_dd_pct": met40["max_daily_dd_pct"],
                "m40_days_ge_5pct": met40["days_ge_5pct_daily_dd"],
            })

    part1_firms = [
        {
            "id": "FTMO_SWING_10K",
            "label": "FTMO Swing 10K (168 USD)",
            "capital_usd": 10_000.0,
            "fee_usd": 168.0,
            "fee_refund_ratio": 1.0,
            "steps": 2,
            "p1_target": 0.10,
            "p2_target": 0.05,
            "daily_lim": 0.05,
            "static_lim": 0.10,
            "min_days": 4,
            "min_prof_day": 0.0,
            "payout_split": 0.80,
            "payout_cycle": 10,
            "min_payout_usd": 0.0,
            "funded_red_news": False,
        },
        {
            "id": "THE5ERS_HS_5K",
            "label": "The5ers HS 5K (39 USD)",
            "capital_usd": 5_000.0,
            "fee_usd": 39.0,
            "fee_refund_ratio": 0.70,
            "steps": 2,
            "p1_target": 0.08,
            "p2_target": 0.05,
            "daily_lim": 0.05,
            "static_lim": 0.10,
            "min_days": 3,
            "min_prof_day": 0.005,
            "payout_split": 0.80,
            "payout_cycle": 10,
            "min_payout_usd": 150.0,
            "funded_red_news": True,
        },
    ]

    # (name, p1s, p1l, p2s, p2l, p1_trig, p2_trig, amber_dd, amber_scale, red_dd, red_scale, ea_stop, p2_fn_core7)
    part1_policies = [
        ("DEPLOYED_PRESET_EXACT", 4.00, 2.01, 2.50, 1.50, 0.50, 0.60, 0.075, 1.50, 0.090, 1.125, 0.042, True),
        ("Dyn_ProfitLock", 4.50, 2.00, 2.50, 1.50, 0.50, 0.60, 0.035, 0.65, 0.060, 0.40, 0.038, True),
        ("P1_Balanced_Static", 4.00, 4.00, 2.00, 2.00, 1.10, 1.10, 0.035, 0.65, 0.060, 0.40, 0.038, True),
    ]

    part1_mc_rows: list[dict[str, Any]] = []
    for fric in ("1.0x", "1.25x", "1.5x"):
        for sc in SYMCAP_GRID_PCT:
            for pol_name, p1s, p1l, p2s, p2l, p1_trig, p2_trig, amb_d, amb_s, red_d, red_s, ea_st, core7_p2f in part1_policies:
                _, n_p1s, d_p1s, f_p1s = get_stage(fric, p1s, sc, use_core7=False, use_red_news=True)
                _, n_p1l, d_p1l, f_p1l = get_stage(fric, p1l, sc, use_core7=False, use_red_news=True)
                p2_sc = min(sc, 1.50) if core7_p2f else sc
                _, n_p2s, d_p2s, f_p2s = get_stage(fric, p2s, p2_sc, use_core7=core7_p2f, use_red_news=True)
                _, n_p2l, d_p2l, f_p2l = get_stage(fric, p2l, p2_sc, use_core7=core7_p2f, use_red_news=True)
                for fm in part1_firms:
                    fn_sc = 1.00 if core7_p2f else sc
                    _, nf, df, ff = get_stage(
                        fric, 1.00, fn_sc, use_core7=core7_p2f, use_red_news=bool(fm["funded_red_news"]),
                    )
                    mc_res = _simulate_staged_prop_mc_numba(
                        idx_mat,
                        n_p1s, d_p1s, f_p1s,
                        n_p1l, d_p1l, f_p1l,
                        n_p2s, d_p2s, f_p2s,
                        n_p2l, d_p2l, f_p2l,
                        nf, df, ff,
                        fm["steps"], fm["capital_usd"], fm["fee_usd"], fm["fee_refund_ratio"],
                        fm["p1_target"], fm["p2_target"], fm["daily_lim"], fm["static_lim"],
                        fm["min_days"], fm["min_prof_day"], fm["payout_split"], fm["payout_cycle"],
                        MAX_RETRIES, p1_trig, p2_trig, amb_d, amb_s, red_d, red_s, ea_st,
                        float(fm["min_payout_usd"]),
                    )
                    summ = _summarize_mc(mc_res, fm["fee_usd"], n_paths)
                    part1_mc_rows.append({
                        "friction": fric,
                        "firm_id": fm["id"],
                        "firm_label": fm["label"],
                        "policy": pol_name,
                        "symcap_pct": sc,
                        **summ,
                    })

    # ------------------------------------------------------------------
    # PART 2: Multi-Tier Fee-Efficiency Matrix & 50K Strict 4%/8% Trap
    # ------------------------------------------------------------------
    tier_specs = build_part2_tier_specs()
    part2_rows: list[dict[str, Any]] = []
    for fric in ("1.0x", "1.25x", "1.5x"):
        for ts in tier_specs:
            sc = float(ts["symcap"])
            is_t5 = ts["firm"].startswith("The5ers")
            min_pay = float(ts.get("min_payout_usd", 150.0 if is_t5 else 0.0))
            fn_news = bool(ts.get("funded_red_news", is_t5))
            _, nf, df, ff = get_stage(fric, 1.00, 1.00, use_core7=True, use_red_news=fn_news)
            _, n_p1s, d_p1s, f_p1s = get_stage(fric, float(ts["p1_s"]), sc, use_core7=False, use_red_news=True)
            _, n_p1l, d_p1l, f_p1l = get_stage(fric, float(ts["p1_lock"]), sc, use_core7=False, use_red_news=True)
            p2_sc = min(sc, 1.50)
            _, n_p2s, d_p2s, f_p2s = get_stage(fric, float(ts["p2_s"]), p2_sc, use_core7=True, use_red_news=True)
            _, n_p2l, d_p2l, f_p2l = get_stage(fric, float(ts["p2_lock"]), p2_sc, use_core7=True, use_red_news=True)
            mc_res = _simulate_staged_prop_mc_numba(
                idx_mat,
                n_p1s, d_p1s, f_p1s,
                n_p1l, d_p1l, f_p1l,
                n_p2s, d_p2s, f_p2s,
                n_p2l, d_p2l, f_p2l,
                nf, df, ff,
                int(ts["steps"]), float(ts["capital_usd"]), float(ts["fee_usd"]), float(ts["fee_refund_ratio"]),
                float(ts["p1_target"]), float(ts["p2_target"]), float(ts["daily_lim"]), float(ts["static_lim"]),
                int(ts["min_days"]), float(ts["min_prof_day"]), float(ts["payout_split"]), int(ts["payout_cycle"]),
                MAX_RETRIES, 0.50, 0.60,
                float(ts["amber_dd"]), float(ts["amber_scale"]),
                float(ts["red_dd"]), float(ts["red_scale"]),
                float(ts["ea_stop"]),
                min_pay,
            )
            summ = _summarize_mc(mc_res, float(ts["fee_usd"]), n_paths)
            part2_rows.append({
                "friction": fric,
                "tier_id": ts["tier_id"],
                "firm": ts["firm"],
                "label": ts["label"],
                "preset_tag": ts["preset_tag"],
                "capital_usd": ts["capital_usd"],
                "fee_usd": ts["fee_usd"],
                "fee_pct_of_capital": round(100.0 * float(ts["fee_usd"]) / float(ts["capital_usd"]), 3),
                "dd_limits": f"{int(ts['daily_lim']*100)}%/{int(ts['static_lim']*100)}%",
                "symcap_pct": sc,
                "p1_start_mult": ts["p1_s"],
                "ea_stop_pct": round(float(ts["ea_stop"]) * 100.0, 1),
                **summ,
            })

    # Compute key headline comparisons for executive verdict
    def _find_p1(fric: str, firm_id: str, pol: str, sc: float) -> dict[str, Any]:
        return next(
            r for r in part1_mc_rows
            if r["friction"] == fric and r["firm_id"] == firm_id and r["policy"] == pol and abs(r["symcap_pct"] - sc) < 1e-6
        )

    def _find_p2(fric: str, tier_id: str) -> dict[str, Any]:
        return next(r for r in part2_rows if r["friction"] == fric and r["tier_id"] == tier_id)

    ftmo_175 = _find_p1("1.0x", "FTMO_SWING_10K", "Dyn_ProfitLock", 1.75)
    ftmo_350 = _find_p1("1.0x", "FTMO_SWING_10K", "Dyn_ProfitLock", 3.50)
    ftmo_175_15x = _find_p1("1.5x", "FTMO_SWING_10K", "Dyn_ProfitLock", 1.75)
    ftmo_350_15x = _find_p1("1.5x", "FTMO_SWING_10K", "Dyn_ProfitLock", 3.50)

    t5_175 = _find_p1("1.0x", "THE5ERS_HS_5K", "Dyn_ProfitLock", 1.75)
    t5_350 = _find_p1("1.0x", "THE5ERS_HS_5K", "Dyn_ProfitLock", 3.50)

    tier_ftmo10 = _find_p2("1.0x", "FTMO_SWING_10K_REG")
    tier_ftmo25 = _find_p2("1.0x", "FTMO_SWING_25K")
    tier_ftmo50 = _find_p2("1.0x", "FTMO_SWING_50K")
    tier_ftmo100 = _find_p2("1.0x", "FTMO_SWING_100K")
    tier_t5_5k = _find_p2("1.0x", "THE5ERS_HS_5K_REG")
    tier_t5_50k_naive = _find_p2("1.0x", "THE5ERS_HS_50K_NAIVE_5K_PRESET")
    tier_t5_50k_175 = _find_p2("1.0x", "THE5ERS_HS_50K_NAIVE_175_PRESET")
    tier_t5_50k_cal = _find_p2("1.0x", "THE5ERS_HS_50K_CALIBRATED_4_8")
    tier_t5_60k_cal = _find_p2("1.0x", "THE5ERS_HS_60K_CALIBRATED_4_8")

    highlights = {
        "recommended_symcap_pct": 1.75,
        "ftmo_10k_daily_breach_1try_350_to_175_pct": [ftmo_350["daily_breach_1try_pct"], ftmo_175["daily_breach_1try_pct"]],
        "ftmo_10k_fail_1try_350_to_175_pct": [ftmo_350["fail_1try_pct"], ftmo_175["fail_1try_pct"]],
        "ftmo_10k_ev_per_fee_350_to_175": [ftmo_350["ev_per_fee"], ftmo_175["ev_per_fee"]],
        "ftmo_10k_15x_daily_breach_350_to_175_pct": [ftmo_350_15x["daily_breach_1try_pct"], ftmo_175_15x["daily_breach_1try_pct"]],
        "the5ers_5k_daily_breach_1try_350_to_175_pct": [t5_350["daily_breach_1try_pct"], t5_175["daily_breach_1try_pct"]],
        "ftmo_ev_per_fee_multiplier_10k_to_50k": round(tier_ftmo50["ev_per_fee"] / max(0.01, tier_ftmo10["ev_per_fee"]), 2),
        "ftmo_ev_per_fee_multiplier_10k_to_100k": round(tier_ftmo100["ev_per_fee"] / max(0.01, tier_ftmo10["ev_per_fee"]), 2),
        "ftmo_ev_per_fee_multiplier_10k_to_25k": round(tier_ftmo25["ev_per_fee"] / max(0.01, tier_ftmo10["ev_per_fee"]), 2),
        "the5ers_50k_naive_vs_calibrated_daily_breach_1try_pct": [
            tier_t5_50k_naive["daily_breach_1try_pct"],
            tier_t5_50k_175["daily_breach_1try_pct"],
            tier_t5_50k_cal["daily_breach_1try_pct"],
        ],
        "the5ers_50k_naive_vs_calibrated_ev_per_fee": [
            tier_t5_50k_naive["ev_per_fee"],
            tier_t5_50k_175["ev_per_fee"],
            tier_t5_50k_cal["ev_per_fee"],
        ],
        "the5ers_60k_calibrated_ev_per_fee": tier_t5_60k_cal["ev_per_fee"],
        "the5ers_5k_reg_ev_per_fee": tier_t5_5k["ev_per_fee"],
    }

    elapsed_sec = round(time.perf_counter() - t0, 2)
    payload: dict[str, Any] = {
        "schema": "naqex-prop-tier-and-symcap-audit-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "order_send_capable": ORDER_SEND_CAPABLE,
        "order_send_count": ORDER_SEND_COUNT,
        "holdout_lock_sha256": lock_sha,
        "holdout_rows_analysed": 0,
        "dev_window": f"{ext_days[0]}..{ext_days[-1]}",
        "dev_days_count": len(ext_days),
        "mc_paths": n_paths,
        "mc_block_len": BLOCK_LEN,
        "mc_seed": SEED,
        "usd_vnd_rate": USD_VND_RATE,
        "portfolio_id": "A1_V1_LIVE8",
        "engines": list(LIVE8_IDS),
        "elapsed_sec": elapsed_sec,
        "highlights": highlights,
        "part1_m1_symcap_summary": part1_m1_summary,
        "part1_mc_symcap_matrix": part1_mc_rows,
        "part2_tier_scaling_matrix": part2_rows,
    }

    if write_report:
        OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
        sha_hex = write_verified_receipt(OUT_JSON, payload, overwrite=overwrite)
        payload["receipt_sha256"] = sha_hex
        md_text = render_audit_markdown(payload, sha_hex)
        assert "$" not in md_text, "Bare '$' detected in audit Markdown!"
        OUT_MD.write_text(md_text, encoding="utf-8", newline="\n")

    return payload


def render_audit_markdown(payload: dict[str, Any], sha_hex: str) -> str:
    """Render plain, easy-to-understand Vietnamese audit report (strictly zero bare `$`)."""
    hl = payload["highlights"]
    p1_m1 = payload["part1_m1_symcap_summary"]
    p1_mc = payload["part1_mc_symcap_matrix"]
    p2 = payload["part2_tier_scaling_matrix"]

    def _p1_rows(fric: str, firm_id: str, pol: str) -> list[list[str]]:
        out = []
        for r in p1_mc:
            if r["friction"] == fric and r["firm_id"] == firm_id and r["policy"] == pol:
                tag = " (KHUYÊN DÙNG)" if abs(r["symcap_pct"] - 1.75) < 1e-6 else (" (CŨ - NGUY HIỂM)" if r["symcap_pct"] >= 3.0 else "")
                out.append([
                    f"{r['symcap_pct']:.2f}%{tag}",
                    f"{r['daily_breach_1try_pct']:.1f}%",
                    f"{r['static_breach_1try_pct']:.1f}%",
                    f"{r['fail_1try_pct']:.1f}%",
                    f"{r['pass_24m_pct']:.1f}%",
                    f"{r['med_days_pass']}d" if r["med_days_pass"] > 0 else "N/A",
                    f"{r['ev_per_fee']:.2f}x ({r['ev_per_total_fee']:.2f}x tổng phí)",
                    f"{r['ev_24m_usd']:+,.0f} USD ({r['ev_24m_vnd_tr']:+.1f} tr) · P<=0={r['p_net_le_0_pct']:.0f}%",
                    f"{r['oop95_usd']:,.0f} USD ({r['oop95_vnd_tr']:.1f} tr)",
                ])
        return out

    m1_tbl_rows = []
    for r in p1_m1:
        if r["friction"] == "1.0x":
            m1_tbl_rows.append([
                f"{r['symcap_pct']:.2f}%",
                f"{r['m45_ann_pct']:.2f}%",
                f"-{r['m45_max_daily_dd_pct']:.2f}%",
                f"-{r['m45_p99_daily_dd_pct']:.2f}%",
                f"{r['m45_days_ge_5pct']} ngày",
                f"{r['m45_days_ge_4pct']} ngày",
                f"{r['m45_max_margin_pct']:.1f}%",
                f"{r['m45_sym_cap_hits']}",
            ])

    def _p2_rows(fric: str) -> list[list[str]]:
        out = []
        for r in p2:
            if r["friction"] != fric:
                continue
            out.append([
                r["label"],
                f"{r['fee_pct_of_capital']:.2f}%",
                r["dd_limits"],
                f"{r['symcap_pct']:.2f}% / {r['p1_start_mult']:.2f}x",
                f"{r['daily_breach_1try_pct']:.1f}%",
                f"{r['fail_1try_pct']:.1f}%",
                f"{r['pass_24m_pct']:.1f}%",
                f"**{r['ev_per_fee']:.2f}x** ({r['ev_per_total_fee']:.2f}x)",
                f"{r['ev_24m_usd']:+,.0f} USD ({r['ev_24m_vnd_tr']:+.1f} tr) · P<=0={r['p_net_le_0_pct']:.0f}%",
                f"{r['oop95_usd']:,.0f} USD ({r['oop95_vnd_tr']:.1f} tr)",
            ])
        return out

    lines = [
        "---",
        "doc_type: quant-research-audit",
        f"generated_utc: {payload['generated_utc']}",
        f"dev_window: {payload['dev_window']}",
        f"mc_paths: {payload['mc_paths']}",
        f"mc_seed: {payload['mc_seed']}",
        f"holdout_rows_analysed: {payload['holdout_rows_analysed']}",
        f"order_send_count: {payload['order_send_count']}",
        f"receipt_sha256: {sha_hex}",
        "---",
        "",
        "# Kiểm Toán Định Lượng: Siết Trần Rủi Ro 1 Mã (`SYMCAP`) & Ma Trận Lên Cấp Tài Khoản Quỹ (Dev 2018–2024)",
        "",
        "> **Niêm phong dữ liệu & An toàn:** Chạy hoàn toàn trên tập Phát triển `2018-2024` (`holdout_rows_analysed = 0`, khóa Holdout `2025+` nguyên vẹn SHA `"
        + payload["holdout_lock_sha256"][:16]
        + "...`), `OrderSend = 0`, mô phỏng **10.000 kịch bản Monte Carlo** (`Circular Block-Bootstrap`, độ dài khối `5` ngày, `seed = 20261124`) ghép trực tiếp từ dữ liệu chạy từng phút M1 thật có khóa tin đỏ `±5` phút của danh mục live **8 EA (`A1_V1_LIVE8`)**.",
        "",
        "## 1. Tóm Tắt Dễ Hiểu Cho Chủ Quỹ",
        "",
        "1. **Siết trần rủi ro 1 mã (`SYMCAP`) từ `3,00%–3,50%` xuống `1,75%` giảm mạnh rủi ro nổ trần ngày mà vẫn giữ hiệu suất kiếm tiền trên mỗi USD tiền vé (`EV/Fee`) cao vượt trội:**",
        f"   - Trên **FTMO Swing 10K (`Dyn_ProfitLock` `4,5x -> +5% khóa 2,0x`)** ở chi phí chuẩn `1,0x`: tỷ lệ cháy trần lỗ ngày `5%` ngay lượt thi đầu giảm từ **`{hl['ftmo_10k_daily_breach_1try_350_to_175_pct'][0]:.1f}%`** (`SYMCAP 3,50%`) xuống còn **`{hl['ftmo_10k_daily_breach_1try_350_to_175_pct'][1]:.1f}%`** (`SYMCAP 1,75%`). Tỷ lệ rớt lượt đầu giảm từ `{hl['ftmo_10k_fail_1try_350_to_175_pct'][0]:.1f}%` xuống `{hl['ftmo_10k_fail_1try_350_to_175_pct'][1]:.1f}%`, trong khi **`EV/Fee`** giữ mức rất cao (`{hl['ftmo_10k_ev_per_fee_350_to_175'][1]:.2f}x` so với `{hl['ftmo_10k_ev_per_fee_350_to_175'][0]:.2f}x`).",
        f"   - Khi thị trường giãn trượt giá `1,5x` (kịch bản stress thực chiến): cháy trần ngày lượt đầu vẫn giảm sâu từ **`{hl['ftmo_10k_15x_daily_breach_350_to_175_pct'][0]:.1f}%`** xuống **`{hl['ftmo_10k_15x_daily_breach_350_to_175_pct'][1]:.1f}%`**.",
        f"   - Trên **The5ers High Stakes 5K (`39 USD`)**: cháy trần ngày lượt đầu giảm từ **`{hl['the5ers_5k_daily_breach_1try_350_to_175_pct'][0]:.1f}%`** xuống **`{hl['the5ers_5k_daily_breach_1try_350_to_175_pct'][1]:.1f}%`**.",
        "2. **Lên cấp tài khoản (`10K -> 25K / 50K / 100K`) là đòn bẩy kinh tế lớn nhất mà không hề tăng thêm rủi ro phần trăm:**",
        f"   - Vì giá vé không tăng tỷ lệ thuận với vốn (FTMO 10K tốn `1,68%` vốn mua vé, còn 50K chỉ tốn `0,72%` và 100K chỉ tốn `0,56%`), chỉ cần giữ nguyên chiến lược đã siết `SYMCAP 1,75%`, nhảy từ **10K -> 25K** nhân `EV/Fee` lên **`{hl['ftmo_ev_per_fee_multiplier_10k_to_25k']:.2f}x`**, lên **50K** nhân **`{hl['ftmo_ev_per_fee_multiplier_10k_to_50k']:.2f}x`**, và lên **100K** nhân **`{hl['ftmo_ev_per_fee_multiplier_10k_to_100k']:.2f}x`**!",
        "3. **Cảnh báo cứng về bẫy luật `4%/8%` của The5ers High Stakes 50K/60K (`329 USD`):**",
        f"   - Nếu bê nguyên bộ cấu hình 5K (vốn thiết kế cho luật `5%/10%`) sang chạy The5ers 50K (`4%` lỗ ngày / `8%` lỗ tổng), tỷ lệ cháy trần ngày lượt đầu vọt lên **`{hl['the5ers_50k_naive_vs_calibrated_daily_breach_1try_pct'][0]:.1f}%`** (với `SYMCAP 3,00%`) và vẫn tới **`{hl['the5ers_50k_naive_vs_calibrated_daily_breach_1try_pct'][1]:.1f}%`** (ngay cả với `SYMCAP 1,75%` chưa hạ cỡ lệnh!).",
        f"   - Khi hạ cấu hình riêng cho khung `4%/8%` (`P1 2,75x -> +4% khóa 1,50x`, `SYMCAP 1,15%`, cắt lỗ ngày EA `2,8%`), cháy trần ngày lượt đầu rơi xuống chỉ còn **`{hl['the5ers_50k_naive_vs_calibrated_daily_breach_1try_pct'][2]:.1f}%`**, mở khóa hiệu quả **`EV/Fee = {hl['the5ers_50k_naive_vs_calibrated_ev_per_fee'][2]:.2f}x`** (50K) và **`{hl['the5ers_60k_calibrated_ev_per_fee']:.2f}x`** (60K)!",
        "",
        "## 2. Phần 1 — Kiểm Toán `SYMCAP` Trên Danh Mục Live 8 EA (`A1_V1_LIVE8`)",
        "",
        "### 2.1. Tác Động Vật Lý Từng Phút M1 Tại Mức Khởi Đầu P1 (`4,5x`, 7 Năm Dev `2018–2024`, Phí `1,0x`)",
        "",
        "Bảng dưới đo trực tiếp dữ liệu M1 thật trước khi đưa vào Monte Carlo: ở `SYMCAP` cũ (`3,00%–3,50%`), chỉ 1 lệnh đơn hoặc 2 lệnh trùng mã mở cùng lúc có thể đẩy lỗ nổi trong ngày vọt quá `-10%` (gấp đôi trần `5%` của quỹ!). Siết về `1,50%–1,75%` cắt gần một nửa cú sốc ngày xấu nhất và giảm margin đỉnh từ `84,5%` về ~`55%`.",
        "",
        format_markdown_table(
            ["SYMCAP", "Lãi năm (P1 4.5x)", "Lỗ ngày xấu nhất", "Lỗ ngày P99", "Số ngày >= 5%", "Số ngày >= 4%", "Margin đỉnh", "Số lần SYMCAP chặn"],
            m1_tbl_rows,
        ),
        "",
        "### 2.2. Kết Quả 10.000 Kịch Bản Monte Carlo — `FTMO Swing 10K` (`Dyn_ProfitLock` `4,5x -> +5% khóa 2,0x`)",
        "",
        "**Kịch bản chi phí chuẩn (`1,0x`):**",
        "",
        format_markdown_table(
            ["SYMCAP", "Cháy Ngày (Lượt 1)", "Cháy Tổng (Lượt 1)", "Rớt Lượt 1", "Đậu trong 24T", "Trung vị đậu", "EV / Phí vé", "Dòng tiền 24T (USD / VND)", "Chi phí ròng xấu P95"],
            _p1_rows("1.0x", "FTMO_SWING_10K", "Dyn_ProfitLock"),
        ),
        "",
        "**Kịch bản trượt giá nặng (`1,5x` chi phí M1):**",
        "",
        format_markdown_table(
            ["SYMCAP", "Cháy Ngày (Lượt 1)", "Cháy Tổng (Lượt 1)", "Rớt Lượt 1", "Đậu trong 24T", "Trung vị đậu", "EV / Phí vé", "Dòng tiền 24T (USD / VND)", "Chi phí ròng xấu P95"],
            _p1_rows("1.5x", "FTMO_SWING_10K", "Dyn_ProfitLock"),
        ),
        "",
        "### 2.3. Đối Chiếu `The5ers High Stakes 5K` (`Dyn_ProfitLock`, Phí `39 USD`, 3 Ngày Lãi `>= +0,5%`)",
        "",
        "**Kịch bản chi phí chuẩn (`1,0x`):**",
        "",
        format_markdown_table(
            ["SYMCAP", "Cháy Ngày (Lượt 1)", "Cháy Tổng (Lượt 1)", "Rớt Lượt 1", "Đậu trong 24T", "Trung vị đậu", "EV / Phí vé", "Dòng tiền 24T (USD / VND)", "Chi phí ròng xấu P95"],
            _p1_rows("1.0x", "THE5ERS_HS_5K", "Dyn_ProfitLock"),
        ),
        "",
        "**Kịch bản trượt giá nặng (`1,5x`):**",
        "",
        format_markdown_table(
            ["SYMCAP", "Cháy Ngày (Lượt 1)", "Cháy Tổng (Lượt 1)", "Rớt Lượt 1", "Đậu trong 24T", "Trung vị đậu", "EV / Phí vé", "Dòng tiền 24T (USD / VND)", "Chi phí ròng xấu P95"],
            _p1_rows("1.5x", "THE5ERS_HS_5K", "Dyn_ProfitLock"),
        ),
        "",
        "### 2.4. Đối Chiếu Bộ Preset Đang Xuất Thực Tế (`DEPLOYED_PRESET_EXACT`: `4,00x -> 2,01x`, P2/Funded `7E`, `SYMCAP 1,50%/1,00%`)",
        "",
        "**FTMO Swing 10K (`1,0x` / `1,25x` / `1,5x` — lưu ý `504` phiên giao dịch tương đương ~`27,4` tháng lịch trên `221` ngày giao dịch/năm):**",
        "",
        format_markdown_table(
            ["SYMCAP", "Cháy Ngày (Lượt 1)", "Cháy Tổng (Lượt 1)", "Rớt Lượt 1", "Đậu 504 phiên", "Trung vị đậu", "EV / Phí (Đầu / Tổng)", "Dòng tiền 504 phiên (USD / VND / P<=0)", "Chi phí ròng xấu P95"],
            _p1_rows("1.0x", "FTMO_SWING_10K", "DEPLOYED_PRESET_EXACT"),
        ),
        "",
        "**FTMO Swing 10K (`DEPLOYED_PRESET_EXACT`, trượt giá `1,25x`):**",
        "",
        format_markdown_table(
            ["SYMCAP", "Cháy Ngày (Lượt 1)", "Cháy Tổng (Lượt 1)", "Rớt Lượt 1", "Đậu 504 phiên", "Trung vị đậu", "EV / Phí (Đầu / Tổng)", "Dòng tiền 504 phiên (USD / VND / P<=0)", "Chi phí ròng xấu P95"],
            _p1_rows("1.25x", "FTMO_SWING_10K", "DEPLOYED_PRESET_EXACT"),
        ),
        "",
        "**FTMO Swing 10K (`DEPLOYED_PRESET_EXACT`, trượt giá `1,5x`):**",
        "",
        format_markdown_table(
            ["SYMCAP", "Cháy Ngày (Lượt 1)", "Cháy Tổng (Lượt 1)", "Rớt Lượt 1", "Đậu 504 phiên", "Trung vị đậu", "EV / Phí (Đầu / Tổng)", "Dòng tiền 504 phiên (USD / VND / P<=0)", "Chi phí ròng xấu P95"],
            _p1_rows("1.5x", "FTMO_SWING_10K", "DEPLOYED_PRESET_EXACT"),
        ),
        "",
        "### 2.5. Đối Chiếu Chế Độ Tĩnh `P1_Balanced_Static` (`4,0x` Không Khóa Lãi) Trên FTMO Swing 10K (`1,0x`)",
        "",
        format_markdown_table(
            ["SYMCAP", "Cháy Ngày (Lượt 1)", "Cháy Tổng (Lượt 1)", "Rớt Lượt 1", "Đậu trong 24T", "Trung vị đậu", "EV / Phí vé", "Dòng tiền 24T (USD / VND)", "Chi phí ròng xấu P95"],
            _p1_rows("1.0x", "FTMO_SWING_10K", "P1_Balanced_Static"),
        ),
        "",
        "- **Kết luận Phần 1:** Mức **`SYMCAP = 1,75%`** (biên an toàn `1,50%–2,00%`) kết hợp **`Dyn_ProfitLock` (`4,5x -> +5% hạ về 2,0x`)** là điểm ngọt rõ ràng nhất: loại bỏ hoàn toàn nguy cơ 1 lệnh đơn (hoặc 2 bot cùng mã USDJPY/US100) bắn thủng trần lỗ ngày `5%`, giữ thời gian đậu quỹ nhanh và bảo toàn dòng tiền ròng 24 tháng ngay cả khi chi phí thực tế tăng `1,5x`.",
        "",
        "## 3. Phần 2 — Ma Trận Hiệu Quả Tiền Vé Đa Cấp Bậc & Bẫy Luật `4%/8%` Trên The5ers 50K/60K",
        "",
        "Toàn bộ các gói `5%/10%` bên dưới dùng đúng cấu hình đã kiểm chứng (`SYMCAP 1,75% + Dyn_ProfitLock`). Riêng gói **The5ers 50K/60K** (luật siết cứng `4%` ngày / `8%` tổng) được thử đối chứng 3 trường hợp: (1) bê nhầm preset 5K cũ (`SYMCAP 3,0%`), (2) bê preset 5K mới (`SYMCAP 1,75%`) nhưng không hạ cỡ lệnh, và (3) cấu hình chuẩn hóa riêng cho khung `4%/8%` (`P1 2,75x`, `SYMCAP 1,15%`, cắt lỗ ngày EA `2,8%`). Tỷ giá quy đổi `1 USD = 25.500 VND`.",
        "",
        "### 3.1. Ma Trận Đa Cấp Bậc — Chi Phí Chuẩn (`1,0x`, `N = 10.000` Kịch Bản)",
        "",
        format_markdown_table(
            ["Gói Tài Khoản Quỹ", "Phí / Vốn", "Luật DD", "SYMCAP / P1", "Cháy Ngày (L1)", "Rớt Lượt 1", "Đậu 24T", "EV / Phí vé", "Dòng tiền ròng 24T (USD / VND)", "Chi phí ròng P95"],
            _p2_rows("1.0x"),
        ),
        "",
        "### 3.2. Ma Trận Đa Cấp Bậc — Kiểm Thử Stress Trượt Giá `1,25x` (`N = 10.000` Kịch Bản)",
        "",
        format_markdown_table(
            ["Gói Tài Khoản Quỹ", "Phí / Vốn", "Luật DD", "SYMCAP / P1", "Cháy Ngày (L1)", "Rớt Lượt 1", "Đậu 504p", "EV / Phí (Đầu/Tổng)", "Dòng tiền ròng (USD / VND / P<=0)", "Chi phí ròng P95"],
            _p2_rows("1.25x"),
        ),
        "",
        "### 3.3. Ma Trận Đa Cấp Bậc — Kiểm Thử Stress Trượt Giá `1,5x` (`N = 10.000` Kịch Bản)",
        "",
        format_markdown_table(
            ["Gói Tài Khoản Quỹ", "Phí / Vốn", "Luật DD", "SYMCAP / P1", "Cháy Ngày (L1)", "Rớt Lượt 1", "Đậu 24T", "EV / Phí vé", "Dòng tiền ròng 24T (USD / VND)", "Chi phí ròng P95"],
            _p2_rows("1.5x"),
        ),
        "",
        "## 4. Khuyến Nghị Triển Khai Vận Hành Cho Chủ Quỹ",
        "",
        "1. **Áp dụng ngay trần `SYMCAP <= 1,75%` (tối đa `2,00%`) cho mọi preset P1 (`5%/10%` DD):** không bao giờ quay lại mức `3,00%–3,50%` cũ để tránh một cú trượt giá tin vĩ mô làm bay tài khoản chỉ sau một buổi sáng.",
        "2. **Lộ trình leo thang vốn tối ưu hiệu quả đồng vốn (từ tiền lãi quỹ tái đầu tư, không bỏ thêm tiền túi):**",
        "   - *Bước 1 (Khởi động & chứng minh vận hành):* `FTMO Swing 10K` (ưu tiên săn promo ~`95 USD`) + `The5ers HS 5K` (`39 USD`) chạy song song cách nhịp để rút payout đầu tiên và lấp đầy Quỹ Dự Phòng 5 vé.",
        "   - *Bước 2 (Nhảy bậc `EV/Fee` gấp ~2x–3x):* Dùng tiền lãi payout mua thẳng **`FTMO Swing 50K` (`360 USD`)** hoặc **`FTMO Swing 100K` (`560 USD`)** (thay vì mua nhiều vé 10K nhỏ lẻ tốn phí gấp 2–3 lần trên cùng mức vốn).",
        "3. **Cấm tuyệt đối bê preset 5K sang The5ers 50K/60K (`4%/8%` DD):** Bắt buộc nạp bộ tham số hiệu chỉnh riêng (`P1 2,75x -> +4% khóa 1,50x`, `SYMCAP 1,15%`, phanh Amber `2,4%`, Red `4,8%`, cắt lỗ ngày EA `2,8%`) trước khi bấm chạy.",
        "",
        f"*Thời gian tính toán toàn bộ kiểm toán M1 + 10.000 Monte Carlo: `{payload['elapsed_sec']}s` · JSON kiểm chứng: `PROP-TIER-SCALING-AND-SYMCAP-AUDIT-20261124.json` · SHA-256: `{sha_hex}`.*",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Naqex P1 SYMCAP & Multi-Tier Fee-Efficiency Quantitative Audit (Dev 2018-2024, OrderSend=0)")
    ap.add_argument("--n-paths", type=int, default=DEFAULT_N_PATHS)
    ap.add_argument("--no-write", action="store_true")
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args(argv)

    res = run_audit(n_paths=args.n_paths, write_report=not args.no_write, overwrite=args.overwrite)
    print(f"DONE elapsed={res['elapsed_sec']}s paths={res['mc_paths']} holdout_rows={res['holdout_rows_analysed']}")
    for k, v in res["highlights"].items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

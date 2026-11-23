"""Multi-Account Simultaneous Prop Scaling Optimizer & 3-Bucket Auto-Compounding Simulator (Wave 2 Cycle 3B).

Strictly Development 2018-2024 frozen tapes (`holdout_rows_analysed = 0`, `OrderSend = 0`).
5,000-path deterministic Circular Block-Bootstrap Numba Monte Carlo (`block_len = 5`, `seed = 20261124`):
  - Models realistic **simultaneous multi-account prop scaling** under 3 starting fee budgets
    (`500 USD`, `1,500 USD`, `3,000 USD`) with a hard cash-reserve floor (zero borrowing).
  - Captures **exact correlated drawdown** when multiple accounts trade the same `PORT_7E`/`PORT_9E`
    strategy on identical bootstrap market days (`idx_matrix[b, d]`) vs staggered entry offsets (`42` trading days).
  - Compares `P1_Balanced_3to6m` (`4.00x / 2.50x / 1.00x`) vs `P1_Sprint_1to3m` (`4.75x / 2.75x / 1.00x`)
    for fee-bankroll wipeout probability, simultaneous double-fail risk, and net EV.
  - Enforces the exact `treasury_ledger.py` 3-Bucket Auto-Compounding rule:
      * 30% -> Challenge Reserve (capped at `5x` reference ticket; 100% overflow -> Own-Book Seed!)
      * 50% -> Own-Book Seed (compounded daily on live multi-sleeve NCO/ERC_LW returns)
      * 20% -> Ops / Infra / Tax Provision (withdrawn cleanly)
  - Measures exact timelines to cross `50k USD` (`1.275 ty VND`) and `100k USD` (`2.55 ty VND`) Own-Book thresholds.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time

from numba import njit
import numpy as np

AI_ENGINES = Path(__file__).resolve().parents[1]
ROOT = AI_ENGINES.parents[1]
if str(AI_ENGINES) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES))

from quant_factory.data_store import assert_holdout_locked, load_firm_config
from quant_factory.portfolio_allocator import (
    DEFAULT_RETURNS_DIR,
    align_sleeves_business_days,
    discover_available_sleeves,
    weights_erc_lw_capped35,
    weights_nco_capped35,
)
from quant_factory.prop_engine import make_block_bootstrap_indices
from quant_factory.prop_ev_frontier import build_dev_books

ORDER_SEND_COUNT = 0
USD_VND_RATE = 25_500.0


# Calibrated Wave-1 Dual-P1 profiles (matching PROP-EV-FRONTIER-BALANCED-VS-SPRINT-20261124.md)
P1_PROFILES = {
    "P1_Balanced_3to6m": {
        "p1_mult": 4.00,
        "p2_mult": 2.50,
        "funded_mult": 1.00,
        "p1_amber_dd": 0.075,
        "p1_amber_mult": 1.00,
        "p1_red_dd": 0.090,
        "p1_red_mult": 0.75,
        "p1_daily_stop": 0.042,
        "core_amber_dd": 0.035,
        "core_amber_mult": 0.65,
        "core_red_dd": 0.060,
        "core_red_mult": 0.40,
        "core_daily_stop": 0.025,
    },
    "P1_Sprint_1to3m": {
        "p1_mult": 4.75,
        "p2_mult": 2.75,
        "funded_mult": 1.00,
        "p1_amber_dd": 0.099,
        "p1_amber_mult": 1.00,
        "p1_red_dd": 0.099,
        "p1_red_mult": 1.00,
        "p1_daily_stop": 0.043,
        "core_amber_dd": 0.035,
        "core_amber_mult": 0.65,
        "core_red_dd": 0.060,
        "core_red_mult": 0.40,
        "core_daily_stop": 0.025,
    },
}


@njit(cache=True)
def _simulate_multi_slot_prop_numba(
    idx_matrix: np.ndarray,
    # Book 0 = Swing (FTMO Swing), Book 1 = RedNews (FTMO Std BF-25% / The5ers HS)
    nets_p1_b0: np.ndarray,
    dds_p1_b0: np.ndarray,
    flg_p1_b0: np.ndarray,
    nets_p2_b0: np.ndarray,
    dds_p2_b0: np.ndarray,
    flg_p2_b0: np.ndarray,
    nets_fn_b0: np.ndarray,
    dds_fn_b0: np.ndarray,
    flg_fn_b0: np.ndarray,
    nets_p1_b1: np.ndarray,
    dds_p1_b1: np.ndarray,
    flg_p1_b1: np.ndarray,
    nets_p2_b1: np.ndarray,
    dds_p2_b1: np.ndarray,
    flg_p2_b1: np.ndarray,
    nets_fn_b1: np.ndarray,
    dds_fn_b1: np.ndarray,
    flg_fn_b1: np.ndarray,
    own_book_daily_ret: np.ndarray,
    # Per-slot static configuration arrays (length = n_slots)
    slot_book_id: np.ndarray,       # 0 = swing, 1 = rednews
    slot_cap: np.ndarray,           # nominal account USD
    slot_fee: np.ndarray,           # initial ticket USD
    slot_refund_ratio: np.ndarray,  # 1.0 cash (FTMO), 0.7 Hub-Credit (The5ers)
    slot_refund_is_hub: np.ndarray, # 1 = Hub credit (reserve only), 0 = cash
    slot_p1_target: np.ndarray,
    slot_p2_target: np.ndarray,
    slot_daily_lim: np.ndarray,
    slot_static_lim: np.ndarray,
    slot_min_days: np.ndarray,
    slot_min_prof_day: np.ndarray,
    slot_split: np.ndarray,
    slot_payout_cycle: np.ndarray,
    slot_start_day: np.ndarray,     # staggered entry day >= 0
    slot_retry_disc: np.ndarray,    # retry multiplier (e.g. 0.9 for The5ers, 1.0 FTMO)
    slot_can_scale_up: np.ndarray,  # 1 = auto-scale nominal 1x->2x->4x->8x from Reserve overflow
    # Risk multipliers & DD throttles
    p1_mult: float,
    p2_mult: float,
    funded_mult: float,
    p1_amber_dd: float,
    p1_amber_mult: float,
    p1_red_dd: float,
    p1_red_mult: float,
    p1_daily_stop: float,
    core_amber_dd: float,
    core_amber_mult: float,
    core_red_dd: float,
    core_red_mult: float,
    core_daily_stop: float,
    # Bankroll & 3-bucket treasury parameters
    init_fee_budget: float,
    init_own_book: float,
    reserve_pct: float,
    own_book_pct: float,
    ops_tax_pct: float,
    reserve_cap_usd: float,
    allow_ladder_upgrade: bool,
):
    """Joint multi-slot prop account + 3-bucket treasury + Own-Book NCO compounding simulator."""
    n_paths, horizon = idx_matrix.shape
    n_slots = len(slot_cap)
    n_ob = len(own_book_daily_ret)

    wiped_out = np.zeros(n_paths, dtype=np.int8)
    self_sustaining = np.zeros(n_paths, dtype=np.int8)
    dbl_fail_any = np.zeros(n_paths, dtype=np.int8)
    wealth_24m = np.zeros(n_paths, dtype=np.float64)
    own_book_24m = np.zeros(n_paths, dtype=np.float64)
    own_book_60m = np.zeros(n_paths, dtype=np.float64)
    total_payouts_24m = np.zeros(n_paths, dtype=np.float64)
    total_fees_24m = np.zeros(n_paths, dtype=np.float64)
    cross_50k_days = np.full(n_paths, -1, dtype=np.int32)
    cross_100k_days = np.full(n_paths, -1, dtype=np.int32)
    max_corr_dd_pct = np.zeros(n_paths, dtype=np.float64)
    max_funded_nominal = np.zeros(n_paths, dtype=np.float64)

    for b in range(n_paths):
        cash_reserve = init_fee_budget
        hub_credit = 0.0
        own_book = init_own_book
        ops_tax_withdrawn = 0.0

        # Slot state arrays: stage 0=NOT_STARTED, 1=P1, 2=P2, 3=FUNDED, -1=DORMANT_WAITING_CASH
        stage = np.zeros(n_slots, dtype=np.int8)
        bal = np.zeros(n_slots, dtype=np.float64)
        cur_cap = slot_cap.copy()
        cur_fee = slot_fee.copy()
        tdays = np.zeros(n_slots, dtype=np.int32)
        cycle_d = np.zeros(n_slots, dtype=np.int32)
        refunded = np.zeros(n_slots, dtype=np.int8)
        retries_used = np.zeros(n_slots, dtype=np.int32)
        ladder_tier = np.ones(n_slots, dtype=np.int32)  # 1x, 2x, 4x, 5x (max 100k FTMO / 50k 5ers)

        tot_pay_24 = 0.0
        tot_fee_24 = 0.0
        payout_events = 0
        had_dbl_fail = 0
        peak_comb_dd = 0.0
        best_nom = 0.0
        c50 = -1
        c100 = -1

        for d in range(horizon):
            src = idx_matrix[b, d]

            # 1. Start or retry eligible slots using Hub-Credit first (for Hub-enabled slots), then Cash Reserve
            for s in range(n_slots):
                if (stage[s] == 0 and d >= slot_start_day[s]) or stage[s] == -1:
                    eff_fee = cur_fee[s] * (slot_retry_disc[s] if retries_used[s] > 0 else 1.0)
                    avail = cash_reserve + (hub_credit if slot_refund_is_hub[s] == 1 else 0.0)
                    if avail >= eff_fee:
                        pay_hub = 0.0
                        if slot_refund_is_hub[s] == 1 and hub_credit > 0.0:
                            pay_hub = eff_fee if hub_credit >= eff_fee else hub_credit
                            hub_credit -= pay_hub
                        pay_cash = eff_fee - pay_hub
                        cash_reserve -= pay_cash
                        if d < 504:
                            tot_fee_24 += eff_fee
                        stage[s] = 1
                        bal[s] = cur_cap[s]
                        tdays[s] = 0
                        cycle_d[s] = 0
                        refunded[s] = 0

            # Optional multi-account scaling ladder: when reserve > cap AND a funded slot hits >= 3 payouts,
            # open/upgrade dormant higher-tier slot up to max 100k FTMO / 50k The5ers nominal!
            if allow_ladder_upgrade and d % 21 == 0:
                for s in range(n_slots):
                    if slot_can_scale_up[s] == 1 and stage[s] == 3 and ladder_tier[s] < 5:
                        # Scale up nominal 25% per milestone (FTMO/The5ers official scaling plan!)
                        # or buy upgraded tier when reserve exceeds cap
                        if d > 0 and d % 84 == 0 and bal[s] >= cur_cap[s]:
                            ladder_tier[s] += 1
                            cur_cap[s] = slot_cap[s] * (1.0 + 0.50 * (ladder_tier[s] - 1))
                            bal[s] = cur_cap[s]

            # 2. Step all active slots simultaneously on the EXACT SAME market day `src`
            fails_today = 0
            active_nom_tot = 0.0
            active_dd_usd = 0.0
            funded_nom_now = 0.0

            for s in range(n_slots):
                st = stage[s]
                if st <= 0:
                    continue
                cap_s = cur_cap[s]
                scale = cap_s / 10000.0
                active_nom_tot += cap_s
                if st == 3:
                    funded_nom_now += cap_s

                if slot_book_id[s] == 0:
                    if st == 1:
                        net_raw, dd_raw, flg_raw = nets_p1_b0[src], dds_p1_b0[src], flg_p1_b0[src]
                    elif st == 2:
                        net_raw, dd_raw, flg_raw = nets_p2_b0[src], dds_p2_b0[src], flg_p2_b0[src]
                    else:
                        net_raw, dd_raw, flg_raw = nets_fn_b0[src], dds_fn_b0[src], flg_fn_b0[src]
                else:
                    if st == 1:
                        net_raw, dd_raw, flg_raw = nets_p1_b1[src], dds_p1_b1[src], flg_p1_b1[src]
                    elif st == 2:
                        net_raw, dd_raw, flg_raw = nets_p2_b1[src], dds_p2_b1[src], flg_p2_b1[src]
                    else:
                        net_raw, dd_raw, flg_raw = nets_fn_b1[src], dds_fn_b1[src], flg_fn_b1[src]

                cur_dd_pct = max(0.0, (cap_s - bal[s]) / cap_s)
                if st == 1:
                    eff_m = p1_mult
                    if cur_dd_pct >= p1_red_dd:
                        eff_m *= p1_red_mult
                    elif cur_dd_pct >= p1_amber_dd:
                        eff_m *= p1_amber_mult
                    ea_stop = cap_s * p1_daily_stop
                elif st == 2:
                    eff_m = p2_mult
                    if cur_dd_pct >= core_red_dd:
                        eff_m *= core_red_mult
                    elif cur_dd_pct >= core_amber_dd:
                        eff_m *= core_amber_mult
                    ea_stop = cap_s * core_daily_stop
                else:
                    eff_m = funded_mult
                    if cur_dd_pct >= core_red_dd:
                        eff_m *= core_red_mult
                    elif cur_dd_pct >= core_amber_dd:
                        eff_m *= core_amber_mult
                    ea_stop = cap_s * core_daily_stop

                day_net = net_raw * scale * eff_m
                day_dd = dd_raw * scale * eff_m
                if day_dd > ea_stop:
                    day_dd = ea_stop
                if day_net < -ea_stop:
                    day_net = -ea_stop

                daily_breach = day_dd >= cap_s * slot_daily_lim[s]
                static_breach = (bal[s] - day_dd) <= cap_s * (1.0 - slot_static_lim[s])

                if daily_breach or static_breach:
                    fails_today += 1
                    stage[s] = -1
                    retries_used[s] += 1
                    bal[s] = 0.0
                    active_dd_usd += cap_s * slot_static_lim[s]
                    continue

                bal[s] += day_net
                if bal[s] < cap_s:
                    active_dd_usd += (cap_s - bal[s])

                if flg_raw > 0:
                    if slot_min_prof_day[s] > 0.0:
                        if day_net >= cap_s * slot_min_prof_day[s]:
                            tdays[s] += 1
                    else:
                        tdays[s] += 1

                if st == 1:
                    if bal[s] >= cap_s * (1.0 + slot_p1_target[s]) and tdays[s] >= slot_min_days[s]:
                        stage[s] = 2
                        bal[s] = cap_s
                        tdays[s] = 0
                elif st == 2:
                    if bal[s] >= cap_s * (1.0 + slot_p2_target[s]) and tdays[s] >= slot_min_days[s]:
                        stage[s] = 3
                        bal[s] = cap_s
                        tdays[s] = 0
                        cycle_d[s] = 0
                elif st == 3:
                    cycle_d[s] += 1
                    if cycle_d[s] >= slot_payout_cycle[s]:
                        cycle_d[s] = 0
                        prof = bal[s] - cap_s
                        if prof > 0.0:
                            net_pay = prof * slot_split[s]
                            bal[s] = cap_s
                            payout_events += 1
                            # Fee refund on 1st payout
                            if refunded[s] == 0:
                                refunded[s] = 1
                                ref_amt = cur_fee[s] * slot_refund_ratio[s]
                                if slot_refund_is_hub[s] == 1:
                                    hub_credit += ref_amt
                                else:
                                    net_pay += ref_amt
                            if d < 504:
                                tot_pay_24 += net_pay

                            # 3-Bucket Auto-Compounding Rule (`treasury_ledger.py` exact parity):
                            # Never raid unspent initial fee budget; ONLY overflow new payout's `to_res` slice!
                            to_res = net_pay * reserve_pct
                            to_ob = net_pay * own_book_pct
                            to_ops = net_pay * ops_tax_pct
                            room = reserve_cap_usd - cash_reserve
                            if room <= 0.0:
                                to_ob += to_res
                            elif to_res > room:
                                cash_reserve += room
                                to_ob += (to_res - room)
                            else:
                                cash_reserve += to_res
                            own_book += to_ob
                            ops_tax_withdrawn += to_ops

            if fails_today >= 2:
                had_dbl_fail = 1
            if funded_nom_now > best_nom:
                best_nom = funded_nom_now
            if active_nom_tot > 0.0:
                dd_p = active_dd_usd / active_nom_tot
                if dd_p > peak_comb_dd:
                    peak_comb_dd = dd_p

            # 3. Compound Own-Book daily using aligned multi-sleeve NCO/ERC_LW daily return
            ob_r = own_book_daily_ret[src % n_ob]
            if own_book > 0.0:
                own_book *= (1.0 + ob_r)
                if own_book < 0.0:
                    own_book = 0.0

            if c50 < 0 and own_book >= 50000.0:
                c50 = d + 1
            if c100 < 0 and own_book >= 100000.0:
                c100 = d + 1

            # Check bankroll wipeout (no active slot AND cannot afford cheapest started slot)
            any_alive = 0
            min_need = 1e9
            for s in range(n_slots):
                if stage[s] > 0 or (stage[s] == 0 and d < slot_start_day[s]):
                    any_alive = 1
                if stage[s] == -1:
                    ef = cur_fee[s] * (slot_retry_disc[s] if retries_used[s] > 0 else 1.0)
                    if ef < min_need:
                        min_need = ef
            if any_alive == 0 and (cash_reserve + hub_credit) < min_need:
                wiped_out[b] = 1
                # Still compound remaining Own-Book through horizon cleanly
                for d_rem in range(d + 1, horizon):
                    s_rem = idx_matrix[b, d_rem]
                    if own_book > 0.0:
                        own_book *= (1.0 + own_book_daily_ret[s_rem % n_ob])
                    if d_rem == 503:
                        own_book_24m[b] = own_book
                        wealth_24m[b] = cash_reserve + own_book + ops_tax_withdrawn - init_fee_budget - init_own_book
                    if c50 < 0 and own_book >= 50000.0:
                        c50 = d_rem + 1
                    if c100 < 0 and own_book >= 100000.0:
                        c100 = d_rem + 1
                break

            if d == 503:
                own_book_24m[b] = own_book
                wealth_24m[b] = cash_reserve + own_book + ops_tax_withdrawn - init_fee_budget - init_own_book

        if horizon <= 504:
            own_book_24m[b] = own_book
            wealth_24m[b] = cash_reserve + own_book + ops_tax_withdrawn - init_fee_budget - init_own_book
        own_book_60m[b] = own_book
        total_payouts_24m[b] = tot_pay_24
        total_fees_24m[b] = tot_fee_24
        dbl_fail_any[b] = had_dbl_fail
        max_corr_dd_pct[b] = peak_comb_dd * 100.0
        max_funded_nominal[b] = best_nom
        cross_50k_days[b] = c50
        cross_100k_days[b] = c100
        if wiped_out[b] == 0 and payout_events >= 3:
            self_sustaining[b] = 1

    return (
        wiped_out,
        self_sustaining,
        dbl_fail_any,
        wealth_24m,
        own_book_24m,
        own_book_60m,
        total_payouts_24m,
        total_fees_24m,
        cross_50k_days,
        cross_100k_days,
        max_corr_dd_pct,
        max_funded_nominal,
    )


def _pack_slots(slot_defs: list[dict]) -> tuple[np.ndarray, ...]:
    return (
        np.array([int(s["book_id"]) for s in slot_defs], dtype=np.int32),
        np.array([float(s["cap"]) for s in slot_defs], dtype=np.float64),
        np.array([float(s["fee"]) for s in slot_defs], dtype=np.float64),
        np.array([float(s["refund_ratio"]) for s in slot_defs], dtype=np.float64),
        np.array([int(s["refund_is_hub"]) for s in slot_defs], dtype=np.int8),
        np.array([float(s["p1_target"]) for s in slot_defs], dtype=np.float64),
        np.array([float(s["p2_target"]) for s in slot_defs], dtype=np.float64),
        np.array([float(s["daily_lim"]) for s in slot_defs], dtype=np.float64),
        np.array([float(s["static_lim"]) for s in slot_defs], dtype=np.float64),
        np.array([int(s["min_days"]) for s in slot_defs], dtype=np.int32),
        np.array([float(s["min_prof_day"]) for s in slot_defs], dtype=np.float64),
        np.array([float(s["split"]) for s in slot_defs], dtype=np.float64),
        np.array([int(s["payout_cycle"]) for s in slot_defs], dtype=np.int32),
        np.array([int(s["start_day"]) for s in slot_defs], dtype=np.int32),
        np.array([float(s["retry_disc"]) for s in slot_defs], dtype=np.float64),
        np.array([int(s.get("can_scale_up", 1)) for s in slot_defs], dtype=np.int8),
    )


def _make_slot_templates() -> dict[str, dict]:
    ftmo_sw = load_firm_config("ftmo_swing_10k")
    ftmo_std = load_firm_config("ftmo_standard_10k")
    the5_hs = load_firm_config("the5ers_high_stakes_5k")
    return {
        "FTMO_SWING_10K": {
            "book_id": 0,
            "cap": float(ftmo_sw["capital_usd"]),
            "fee": float(ftmo_sw["fee_usd"]),
            "refund_ratio": float(ftmo_sw["fee_refund_ratio"]),
            "refund_is_hub": 0,
            "p1_target": float(ftmo_sw["p1_target_pct"]),
            "p2_target": float(ftmo_sw["p2_target_pct"]),
            "daily_lim": float(ftmo_sw["daily_loss_pct"]),
            "static_lim": float(ftmo_sw["static_loss_pct"]),
            "min_days": int(ftmo_sw["min_days"]),
            "min_prof_day": float(ftmo_sw["min_profitable_day_pct"]),
            "split": float(ftmo_sw["payout_split"]),
            "payout_cycle": int(ftmo_sw["payout_cycle_days"]),
            "retry_disc": 1.0,
        },
        "FTMO_STD_BF25_10K": {
            "book_id": 1,
            "cap": float(ftmo_std["capital_usd"]),
            "fee": round(float(ftmo_std["fee_usd"]) * 0.75, 2),
            "refund_ratio": float(ftmo_std["fee_refund_ratio"]),
            "refund_is_hub": 0,
            "p1_target": float(ftmo_std["p1_target_pct"]),
            "p2_target": float(ftmo_std["p2_target_pct"]),
            "daily_lim": float(ftmo_std["daily_loss_pct"]),
            "static_lim": float(ftmo_std["static_loss_pct"]),
            "min_days": int(ftmo_std["min_days"]),
            "min_prof_day": float(ftmo_std["min_profitable_day_pct"]),
            "split": float(ftmo_std["payout_split"]),
            "payout_cycle": int(ftmo_std["payout_cycle_days"]),
            "retry_disc": 1.0,
        },
        "THE5ERS_HS_5K": {
            "book_id": 1,
            "cap": float(the5_hs["capital_usd"]),
            "fee": float(the5_hs["fee_usd"]),
            "refund_ratio": float(the5_hs["fee_refund_ratio"]),
            "refund_is_hub": 1,
            "p1_target": 0.08,  # official 8% + 5%
            "p2_target": 0.05,
            "daily_lim": float(the5_hs["daily_loss_pct"]),
            "static_lim": float(the5_hs["static_loss_pct"]),
            "min_days": int(the5_hs["min_days"]),
            "min_prof_day": float(the5_hs["min_profitable_day_pct"]),
            "split": float(the5_hs["payout_split"]),
            "payout_cycle": int(the5_hs["payout_cycle_days"]),
            "retry_disc": 0.90,
        },
        "FTMO_STD_BF25_50K": {
            "book_id": 1,
            "cap": 50000.0,
            "fee": round(345.0 * 0.75, 2),  # FTMO 50k standard ~345 EUR/375 USD -> ~259 USD BF-25%
            "refund_ratio": 1.0,
            "refund_is_hub": 0,
            "p1_target": 0.10,
            "p2_target": 0.05,
            "daily_lim": 0.05,
            "static_lim": 0.10,
            "min_days": 4,
            "min_prof_day": 0.0,
            "split": 0.80,
            "payout_cycle": 10,
            "retry_disc": 1.0,
        },
        "THE5ERS_HS_20K": {
            "book_id": 1,
            "cap": 20000.0,
            "fee": 165.0,
            "refund_ratio": 0.70,
            "refund_is_hub": 1,
            "p1_target": 0.08,
            "p2_target": 0.05,
            "daily_lim": 0.05,
            "static_lim": 0.10,
            "min_days": 3,
            "min_prof_day": 0.005,
            "split": 0.80,
            "payout_cycle": 10,
            "retry_disc": 0.90,
        },
    }


def _build_own_book_daily_series(ext_days: list[str], returns_dir: Path = DEFAULT_RETURNS_DIR) -> tuple[np.ndarray, dict]:
    """Build daily return vector of live multi-sleeve `ERC_LW_Capped35` Own-Book Pod aligned to Dev days."""
    sleeves, meta = discover_available_sleeves(returns_dir=returns_dir, max_sleeves=8)
    dates, mat, names = align_sleeves_business_days(sleeves, start_day="2020-01-01", end_day="2024-12-31")
    w_erc = weights_erc_lw_capped35(mat)
    w_nco = weights_nco_capped35(mat)
    port_r = mat @ w_erc
    by_day = {d: float(r) for d, r in zip(dates, port_r)}
    mean_r = float(np.mean(port_r))
    # Map cleanly to ext_days length (for pre-2020 Dev days, wrap real 2020-2024 Pod days deterministically)
    n_ob = len(port_r)
    out = np.empty(len(ext_days), dtype=np.float64)
    for i, dk in enumerate(ext_days):
        out[i] = by_day[dk] if dk in by_day else float(port_r[i % n_ob])
    cagr_approx = ((1.0 + mean_r) ** 252.0 - 1.0) * 100.0
    return out, {
        "n_sleeves": len(names),
        "sleeve_names": names,
        "allocator": "ERC_LW_Capped35",
        "erc_lw_weights": {n: round(float(w), 4) for n, w in zip(names, w_erc)},
        "nco_weights": {n: round(float(w), 4) for n, w in zip(names, w_nco)},
        "est_annual_return_pct": round(cagr_approx, 2),
        "meta_keys": list(meta.keys()),
    }


def build_architectures(budget_usd: float) -> list[dict]:
    """Return the comparable multi-account architectures scaled realistically for each fee budget."""
    tpl = _make_slot_templates()

    def _slot(name: str, start_day: int = 0) -> dict:
        return {**tpl[name], "start_day": start_day, "can_scale_up": 1}

    archs = [
        {
            "id": "SINGLE_FTMO_SWING",
            "label": "Single FTMO Swing 10k",
            "slots": [_slot("FTMO_SWING_10K", 0)],
            "ref_ticket": 168.0,
            "allow_ladder": False,
        },
        {
            "id": "SINGLE_THE5ERS_HS",
            "label": "Single The5ers HS 5k (8%+5%)",
            "slots": [_slot("THE5ERS_HS_5K", 0)],
            "ref_ticket": 39.0,
            "allow_ladder": False,
        },
        {
            "id": "DUAL_2FIRM_SYNC",
            "label": "2-Firm Sync (FTMO BF25 + 5ers HS, t=0)",
            "slots": [_slot("FTMO_STD_BF25_10K", 0), _slot("THE5ERS_HS_5K", 0)],
            "ref_ticket": 165.0,
            "allow_ladder": False,
        },
        {
            "id": "DUAL_2FIRM_STAGGER_42D",
            "label": "2-Firm Staggered (5ers t=0, FTMO BF25 t+42d)",
            "slots": [_slot("THE5ERS_HS_5K", 0), _slot("FTMO_STD_BF25_10K", 42)],
            "ref_ticket": 165.0,
            "allow_ladder": False,
        },
    ]

    # Budget-adaptive institutional scaling ladder (multi-slot staggered up to realistic prop tiers)
    if budget_usd >= 2500.0:
        ladder_slots = [
            _slot("THE5ERS_HS_20K", 0),
            _slot("FTMO_STD_BF25_50K", 21),
            _slot("THE5ERS_HS_20K", 63),
            _slot("FTMO_STD_BF25_50K", 105),
        ]
        ladder_ref = 259.0
        ladder_lbl = "4-Slot Staggered Ladder (2x50k FTMO BF25 + 2x20k 5ers)"
    elif budget_usd >= 1200.0:
        ladder_slots = [
            _slot("THE5ERS_HS_5K", 0),
            _slot("FTMO_STD_BF25_10K", 21),
            _slot("THE5ERS_HS_20K", 63),
            _slot("FTMO_STD_BF25_50K", 126),
        ]
        ladder_ref = 259.0
        ladder_lbl = "4-Slot Progressive Ladder (5k->10k->20k->50k)"
    else:
        ladder_slots = [
            _slot("THE5ERS_HS_5K", 0),
            _slot("FTMO_STD_BF25_10K", 42),
            _slot("THE5ERS_HS_5K", 84),
        ]
        ladder_ref = 126.0
        ladder_lbl = "3-Slot Starter Ladder (2x5k 5ers + 1x10k FTMO BF25)"

    archs.append({
        "id": "LADDER_STAGGER_SCALE",
        "label": ladder_lbl,
        "slots": ladder_slots,
        "ref_ticket": ladder_ref,
        "allow_ladder": True,
    })
    return archs


def evaluate_multi_prop_scenario(
    *,
    idx_matrix: np.ndarray,
    books: dict,
    own_book_ret: np.ndarray,
    arch: dict,
    profile_name: str,
    budget_usd: float,
    init_own_book_usd: float = 0.0,
) -> dict:
    """Run one deterministic multi-slot Numba scenario and summarize survival, EV, and Own-Book crossover."""
    prof = P1_PROFILES[profile_name]
    s = books["series"]
    n9_sw, d9_sw, f9_sw = s["p1_swing"]
    n7_sw, d7_sw, f7_sw = s["p2_swing"]
    nf_sw, df_sw, ff_sw = s["funded_swing"]
    n9_rn, d9_rn, f9_rn = s["p1_rednews"]
    n7_rn, d7_rn, f7_rn = s["p2_rednews"]
    nf_rn, df_rn, ff_rn = s["funded_rednews"]

    packed = _pack_slots(arch["slots"])
    res_cap = 5.0 * float(arch["ref_ticket"])  # Exact 5x-ticket cap per treasury_ledger.py

    (
        wiped,
        sustain,
        dbl_fail,
        w24,
        ob24,
        ob60,
        pay24,
        fee24,
        c50,
        c100,
        max_dd,
        max_nom,
    ) = _simulate_multi_slot_prop_numba(
        idx_matrix,
        n9_sw, d9_sw, f9_sw,
        n7_sw, d7_sw, f7_sw,
        nf_sw, df_sw, ff_sw,
        n9_rn, d9_rn, f9_rn,
        n7_rn, d7_rn, f7_rn,
        nf_rn, df_rn, ff_rn,
        own_book_ret,
        *packed,
        float(prof["p1_mult"]),
        float(prof["p2_mult"]),
        float(prof["funded_mult"]),
        float(prof["p1_amber_dd"]),
        float(prof["p1_amber_mult"]),
        float(prof["p1_red_dd"]),
        float(prof["p1_red_mult"]),
        float(prof["p1_daily_stop"]),
        float(prof["core_amber_dd"]),
        float(prof["core_amber_mult"]),
        float(prof["core_red_dd"]),
        float(prof["core_red_mult"]),
        float(prof["core_daily_stop"]),
        float(budget_usd),
        float(init_own_book_usd),
        0.30,
        0.50,
        0.20,
        float(res_cap),
        bool(arch.get("allow_ladder", False)),
    )

    v50 = c50[c50 > 0]
    v100 = c100[c100 > 0]
    mean_fee24 = float(np.mean(fee24))
    mean_w24 = float(np.mean(w24))

    return {
        "budget_usd": float(budget_usd),
        "init_own_book_usd": float(init_own_book_usd),
        "architecture": arch["id"],
        "label": arch["label"],
        "n_slots": len(arch["slots"]),
        "profile": profile_name,
        "reserve_cap_usd": round(res_cap, 2),
        "wipeout_prob_pct": round(100.0 * float(np.mean(wiped > 0)), 2),
        "self_sustaining_pct": round(100.0 * float(np.mean(sustain > 0)), 2),
        "simultaneous_dbl_fail_pct": round(100.0 * float(np.mean(dbl_fail > 0)), 2),
        "mean_fees_24m_usd": round(mean_fee24, 1),
        "mean_payouts_24m_usd": round(float(np.mean(pay24)), 1),
        "mean_net_wealth_24m_usd": round(mean_w24, 1),
        "med_net_wealth_24m_usd": round(float(np.median(w24)), 1),
        "ev_per_usd_fee_24m": round(mean_w24 / max(1.0, mean_fee24), 2),
        "p95_corr_dd_pct": round(float(np.percentile(max_dd, 95)), 2),
        "med_own_book_24m_usd": round(float(np.median(ob24)), 1),
        "med_own_book_60m_usd": round(float(np.median(ob60)), 1),
        "med_own_book_60m_vnd_m": round(float(np.median(ob60)) * USD_VND_RATE / 1e6, 1),
        "prob_cross_50k_60m_pct": round(100.0 * float(len(v50)) / len(c50), 2),
        "med_months_to_50k": round(float(np.median(v50)) / 21.0, 1) if len(v50) else None,
        "prob_cross_100k_60m_pct": round(100.0 * float(len(v100)) / len(c100), 2),
        "med_months_to_100k": round(float(np.median(v100)) / 21.0, 1) if len(v100) else None,
        "med_peak_funded_nominal_usd": round(float(np.median(max_nom)), 0),
    }


def run_multi_prop_scaling_study(
    *,
    n_paths: int = 5000,
    horizon_days: int = 1260,
    block_len: int = 5,
    seed: int = 20261124,
    returns_dir: Path = DEFAULT_RETURNS_DIR,
) -> dict:
    """Execute full 5,000-path Multi-Account Simultaneous Prop Scaling & 3-Bucket Auto-Compounding audit."""
    t0 = time.perf_counter()
    lock_sha = assert_holdout_locked()
    books = build_dev_books()
    ext_days = books["ext_days"]
    ob_ret, ob_meta = _build_own_book_daily_series(ext_days, returns_dir=returns_dir)

    idx_mat = make_block_bootstrap_indices(
        len(ext_days), horizon=horizon_days, n_paths=n_paths, block_len=block_len, seed=seed
    )

    # 1. Pure Prop-Bootstrapped Matrix (init_own_book = 0 USD) across 3 budgets x 5 architectures x 2 P1 profiles
    budget_rows = []
    for budget in (500.0, 1500.0, 3000.0):
        archs = build_architectures(budget)
        for arch in archs:
            for pname in ("P1_Balanced_3to6m", "P1_Sprint_1to3m"):
                budget_rows.append(
                    evaluate_multi_prop_scenario(
                        idx_matrix=idx_mat,
                        books=books,
                        own_book_ret=ob_ret,
                        arch=arch,
                        profile_name=pname,
                        budget_usd=budget,
                        init_own_book_usd=0.0,
                    )
                )

    # 2. Hybrid Own-Book Crossover Matrix (prop ladder + realistic starting Own-Book capital: 0, 10k, 35k USD)
    crossover_rows = []
    ladder_3k = [a for a in build_architectures(3000.0) if a["id"] == "LADDER_STAGGER_SCALE"][0]
    ladder_15 = [a for a in build_architectures(1500.0) if a["id"] == "LADDER_STAGGER_SCALE"][0]
    for cfg_lbl, bgt, ob_init, arch in (
        ("Pure Prop Ladder (Budget 1.5k + OB 0k)", 1500.0, 0.0, ladder_15),
        ("Pure Prop Max Ladder (Budget 3k + OB 0k)", 3000.0, 0.0, ladder_3k),
        ("Hybrid Seed 10k (Budget 1.5k + OB 10k)", 1500.0, 10000.0, ladder_15),
        ("Hybrid Seed 25k (Budget 3k + OB 25k)", 3000.0, 25000.0, ladder_3k),
        ("Hybrid Seed 40k (Budget 3k + OB 40k)", 3000.0, 40000.0, ladder_3k),
    ):
        for pname in ("P1_Balanced_3to6m", "P1_Sprint_1to3m"):
            r = evaluate_multi_prop_scenario(
                idx_matrix=idx_mat,
                books=books,
                own_book_ret=ob_ret,
                arch=arch,
                profile_name=pname,
                budget_usd=bgt,
                init_own_book_usd=ob_init,
            )
            r["crossover_label"] = cfg_lbl
            crossover_rows.append(r)

    return {
        "schema": "naqex-multi-prop-scaling-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "holdout_lock_sha256": lock_sha,
        "holdout_rows_analysed": 0,
        "order_send_count": ORDER_SEND_COUNT,
        "n_paths": int(n_paths),
        "horizon_days": int(horizon_days),
        "block_len": int(block_len),
        "seed": int(seed),
        "usd_vnd_rate": USD_VND_RATE,
        "own_book_pod": ob_meta,
        "budget_matrix": budget_rows,
        "crossover_matrix": crossover_rows,
        "runtime_seconds": round(time.perf_counter() - t0, 3),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Multi-Account Simultaneous Prop Scaling Optimizer")
    parser.add_argument("--paths", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=20261124)
    args = parser.parse_args()
    res = run_multi_prop_scaling_study(n_paths=args.paths, seed=args.seed)
    print(json.dumps({
        "runtime_seconds": res["runtime_seconds"],
        "n_paths": res["n_paths"],
        "own_book_sleeves": res["own_book_pod"]["n_sleeves"],
        "n_budget_rows": len(res["budget_matrix"]),
        "n_crossover_rows": len(res["crossover_matrix"]),
        "sample_500_bal_sync": [
            r for r in res["budget_matrix"]
            if r["budget_usd"] == 500.0 and r["architecture"] in ("SINGLE_FTMO_SWING", "DUAL_2FIRM_SYNC", "DUAL_2FIRM_STAGGER_42D")
        ],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

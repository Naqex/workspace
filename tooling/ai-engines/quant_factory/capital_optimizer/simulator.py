"""Numba-JIT single-ticket lifecycle simulator and bootstrap / hazard generators."""

from __future__ import annotations

import numpy as np
from numba import njit

from quant_factory.capital_optimizer.constants import BLOCK_LEN, DEFAULT_SEED, TRADING_DAYS_PER_YEAR


def make_block_bootstrap_indices(
    n_obs: int,
    *,
    horizon: int = 756,
    n_paths: int = 5_000,
    block_len: int = BLOCK_LEN,
    seed: int = DEFAULT_SEED,
) -> np.ndarray:
    """Deterministic Circular Block-Bootstrap index matrix (`int32`)."""
    rng = np.random.default_rng(seed)
    n_blocks = (horizon + block_len - 1) // block_len
    starts = rng.integers(0, n_obs, size=(n_paths, n_blocks))
    offs = np.arange(block_len, dtype=np.int64)[None, None, :]
    idxs = (starts[:, :, None] + offs).reshape(n_paths, n_blocks * block_len)[:, :horizon] % n_obs
    return idxs.astype(np.int32)


def make_firm_hazard_days(
    n_paths: int,
    n_firms: int,
    annual_hazard_rate: float,
    *,
    horizon: int = 756,
    seed: int = DEFAULT_SEED + 777,
) -> np.ndarray:
    """Generate independent exponential firm-disruption event day (`-1` if none within horizon)."""
    if annual_hazard_rate <= 1e-12:
        return np.full((n_paths, n_firms), -1, dtype=np.int32)
    rng = np.random.default_rng(seed)
    daily_rate = float(annual_hazard_rate) / float(TRADING_DAYS_PER_YEAR)
    u = rng.uniform(1e-12, 1.0, size=(n_paths, n_firms))
    wait_days = np.floor(-np.log(u) / daily_rate).astype(np.int32)
    out = np.where(wait_days < horizon, wait_days, -1).astype(np.int32)
    return out


@njit(cache=True)
def _simulate_single_ticket_rules_numba(
    idx_matrix: np.ndarray,
    n_p1: np.ndarray, d_p1: np.ndarray, u_p1: np.ndarray, f_p1: np.ndarray,
    n_p1l: np.ndarray, d_p1l: np.ndarray, u_p1l: np.ndarray, f_p1l: np.ndarray,
    n_p2: np.ndarray, d_p2: np.ndarray, u_p2: np.ndarray, f_p2: np.ndarray,
    n_p2l: np.ndarray, d_p2l: np.ndarray, u_p2l: np.ndarray, f_p2l: np.ndarray,
    n_fn: np.ndarray, d_fn: np.ndarray, u_fn: np.ndarray, f_fn: np.ndarray,
    n_amb: np.ndarray, d_amb: np.ndarray, u_amb: np.ndarray, f_amb: np.ndarray,
    n_red: np.ndarray, d_red: np.ndarray, u_red: np.ndarray, f_red: np.ndarray,
    steps: int,
    cap: float,
    fee_day0_usd: float,
    fee_regular_usd: float,
    card_fx_fee_pct: float,
    withdrawal_fee_pct: float,
    fee_refund_pct: float,
    p1_target: float,
    p2_target: float,
    daily_lim: float,
    max_dd_lim: float,
    dd_type: int,
    trail_lock_initial: bool,
    best_day_cap_pct: float,
    min_days: int,
    min_prof_days: int,
    min_prof_day_pct: float,
    profit_split: float,
    payout_cycle_days: int,
    min_payout_usd: float,
    strict_lt_breach: bool,
    p1_lock_trigger: float,
    p2_lock_trigger: float,
    amber_dd: float,
    red_dd: float,
    p1_ea_stop: float,
    p2_ea_stop: float,
    fn_ea_stop: float,
    start_day_offset: int,
    discount_rate_annual: float,
    max_retries: int,
    refund_payout_milestone: int = 1,
    payout_buffer_retention_pct: float = 0.0,
    locks_at_initial_after_first_payout: bool = False,
    min_payout_profit_pct: float = 0.0,
    funded_first_payout_min_prof_days: int = 0,
    funded_first_payout_prof_pct: float = 0.0,
    daily_profit_cap_pct: float = 0.0,
    refund_withdrawal_fee_pct: float = 0.0,
    daily_dd_anchor_mode: int = 0,
    shifting_horizon: bool = False,
    funded_first_payout_min_profit_pct: float = 0.0,
    midnight_floating_shock_pct: float = 0.0,
    rollover_anchor_mode: int = -1,
):
    """Exact single-ticket (or retry-enabled) lifecycle simulator with Law-13/15 metrics, NPV & rollover stress."""
    n_paths, horizon = idx_matrix.shape
    eff_fee_day0_out = fee_day0_usd * (1.0 + card_fx_fee_pct)
    eff_fee_reg_out = fee_regular_usd * (1.0 + card_fx_fee_pct)
    p1_goal = cap * (1.0 + p1_target)
    p2_goal = cap * (1.0 + p2_target)
    daily_cap = cap * daily_lim
    static_floor_base = cap * (1.0 - max_dd_lim)
    r_ann = discount_rate_annual
    inv_df = np.empty(horizon + 2, dtype=np.float64)
    for k_d in range(horizon + 2):
        inv_df[k_d] = (1.0 + r_ann) ** (-k_d / 252.0)

    cutoff_24m = (start_day_offset + 504) if shifting_horizon else 504

    eval_pass_day = np.full(n_paths, -1, dtype=np.int32)
    eval_fail_day = np.full(n_paths, -1, dtype=np.int32)
    pay1_day = np.full(n_paths, -1, dtype=np.int32)
    funded_enter_day = np.full(n_paths, -1, dtype=np.int32)
    funded_breach_day = np.full(n_paths, -1, dtype=np.int32)

    bot_kill_any = np.zeros(n_paths, dtype=np.int8)
    firm_breach_any = np.zeros(n_paths, dtype=np.int8)
    firm_breach_daily = np.zeros(n_paths, dtype=np.int8)
    firm_breach_maxdd = np.zeros(n_paths, dtype=np.int8)

    npv_24m = np.zeros(n_paths, dtype=np.float64)
    npv_36m = np.zeros(n_paths, dtype=np.float64)
    cf_24m = np.zeros(n_paths, dtype=np.float64)
    cf_36m = np.zeros(n_paths, dtype=np.float64)
    fees_24m = np.zeros(n_paths, dtype=np.float64)
    payouts_24m = np.zeros(n_paths, dtype=np.float64)
    max_oop = np.zeros(n_paths, dtype=np.float64)
    tickets_used = np.zeros(n_paths, dtype=np.int32)

    funded_months_total = np.zeros(n_paths, dtype=np.int32)
    funded_months_dry = np.zeros(n_paths, dtype=np.int32)
    funded_max_dry_streak = np.zeros(n_paths, dtype=np.int32)

    for b in range(n_paths):
        if start_day_offset >= horizon:
            continue

        stage = 3 if steps == 0 else 1
        bal = cap
        hwm = cap
        tdays = 0
        pdays_cnt = 0
        cycle_d = 0
        max_day_gain = 0.0
        refunded = False
        payout_cnt = 0
        fn_pdays_cnt = 0
        attempts = 1
        first_ticket_active = True
        cur_ticket_fee = fee_day0_usd

        cum_npv = -eff_fee_day0_out * inv_df[start_day_offset]
        cum_cf = -eff_fee_day0_out
        cum_fees = eff_fee_day0_out
        cum_payouts = 0.0
        path_oop = eff_fee_day0_out

        f_eval_pass = start_day_offset if steps == 0 else -1
        f_eval_fail = -1
        f_pay1 = -1
        f_fn_enter = start_day_offset if steps == 0 else -1
        f_fn_breach = -1
        b_kill = 0
        f_br = 0
        f_br_d = 0
        f_br_m = 0

        fn_month_days = 0
        fn_month_paid = 0
        cur_dry_streak = 0
        best_dry_streak = 0
        tot_fn_m = 0
        dry_fn_m = 0

        recorded_24m = False

        for d in range(horizon):
            if d >= start_day_offset and stage > 0:
                src = idx_matrix[b, d]
                eq_pct = (bal - cap) / cap

                if eq_pct <= -red_dd:
                    net, dd, up, flg = n_red[src], d_red[src], u_red[src], f_red[src]
                    ea_stop_pct = fn_ea_stop if stage == 3 else (p2_ea_stop if stage == 2 else p1_ea_stop)
                elif eq_pct <= -amber_dd:
                    net, dd, up, flg = n_amb[src], d_amb[src], u_amb[src], f_amb[src]
                    ea_stop_pct = fn_ea_stop if stage == 3 else (p2_ea_stop if stage == 2 else p1_ea_stop)
                elif stage == 1:
                    prog = eq_pct / max(1e-6, p1_target)
                    if p1_lock_trigger > 0.0 and prog >= p1_lock_trigger:
                        net, dd, up, flg = n_p1l[src], d_p1l[src], u_p1l[src], f_p1l[src]
                    else:
                        net, dd, up, flg = n_p1[src], d_p1[src], u_p1[src], f_p1[src]
                    ea_stop_pct = p1_ea_stop
                elif stage == 2:
                    prog = eq_pct / max(1e-6, p2_target)
                    if p2_lock_trigger > 0.0 and prog >= p2_lock_trigger:
                        net, dd, up, flg = n_p2l[src], d_p2l[src], u_p2l[src], f_p2l[src]
                    else:
                        net, dd, up, flg = n_p2[src], d_p2[src], u_p2[src], f_p2[src]
                    ea_stop_pct = p2_ea_stop
                else:
                    net, dd, up, flg = n_fn[src], d_fn[src], u_fn[src], f_fn[src]
                    ea_stop_pct = fn_ea_stop

                if dd_type == 2:
                    intra_peak = bal + up
                    if intra_peak > hwm:
                        hwm = intra_peak
                    max_floor = hwm * (1.0 - max_dd_lim)
                    if trail_lock_initial and max_floor > cap:
                        max_floor = cap
                elif dd_type == 1:
                    max_floor = hwm * (1.0 - max_dd_lim)
                    if trail_lock_initial and max_floor > cap:
                        max_floor = cap
                else:
                    if locks_at_initial_after_first_payout and stage == 3 and payout_cnt >= 1:
                        max_floor = cap
                    else:
                        max_floor = static_floor_base

                eff_rollover_mode = (
                    rollover_anchor_mode
                    if rollover_anchor_mode >= 0
                    else (1 if daily_dd_anchor_mode == 1 else 0)
                )
                if np.isnan(midnight_floating_shock_pct) or np.isinf(midnight_floating_shock_pct):
                    raise ValueError("INVALID_MIDNIGHT_SHOCK_NON_FINITE")
                f_00 = (cap * midnight_floating_shock_pct) if (flg != 0 and midnight_floating_shock_pct != 0.0) else 0.0
                eq_00 = bal + f_00
                adverse_shock = -f_00 if f_00 < 0.0 else 0.0

                day_min_eq = bal - adverse_shock - dd
                if eff_rollover_mode == 1:
                    anchor_bal_eq = bal if bal >= eq_00 else eq_00
                    daily_floor = anchor_bal_eq * (1.0 - daily_lim)
                elif eff_rollover_mode == 2:
                    daily_floor = eq_00 * (1.0 - daily_lim)
                else:
                    daily_floor = bal - daily_cap
                ea_cut = cap * ea_stop_pct if ea_stop_pct > 0.0 else 1e18

                if strict_lt_breach:
                    d_hit = day_min_eq < daily_floor - 1e-9
                    m_hit = day_min_eq < max_floor - 1e-9
                else:
                    d_hit = day_min_eq <= daily_floor + 1e-9
                    m_hit = day_min_eq <= max_floor + 1e-9

                dd_with_shock = dd + adverse_shock
                if (not d_hit) and (not m_hit) and (dd_with_shock > ea_cut):
                    b_kill = 1
                    dd_tot_eff = min(dd_with_shock, ea_cut + cap * 0.0020)
                    dd_realized = dd_tot_eff - adverse_shock
                    if dd_realized < 0.0:
                        dd_realized = 0.0
                    net = min(net, -dd_realized)
                    day_min_eq_eff = bal - dd_tot_eff
                    if strict_lt_breach:
                        d_hit = day_min_eq_eff < daily_floor - 1e-9
                        m_hit = day_min_eq_eff < max_floor - 1e-9
                    else:
                        d_hit = day_min_eq_eff <= daily_floor + 1e-9
                        m_hit = day_min_eq_eff <= max_floor + 1e-9

                if d_hit or m_hit:
                    f_br = 1
                    if d_hit:
                        f_br_d = 1
                    if m_hit:
                        f_br_m = 1

                    if first_ticket_active:
                        if stage < 3 and f_eval_fail < 0:
                            f_eval_fail = d + 1
                        elif stage == 3 and f_fn_breach < 0:
                            f_fn_breach = d + 1
                        first_ticket_active = False

                    if attempts <= max_retries:
                        attempts += 1
                        cur_ticket_fee = fee_regular_usd
                        cum_npv -= eff_fee_reg_out * inv_df[d]
                        cum_cf -= eff_fee_reg_out
                        cum_fees += eff_fee_reg_out
                        stage = 3 if steps == 0 else 1
                        bal = cap
                        hwm = cap
                        tdays = 0
                        pdays_cnt = 0
                        cycle_d = 0
                        max_day_gain = 0.0
                        refunded = False
                        payout_cnt = 0
                        fn_pdays_cnt = 0
                    else:
                        stage = 0
                else:
                    if daily_profit_cap_pct > 0.0 and net > cap * daily_profit_cap_pct:
                        net = cap * daily_profit_cap_pct
                    bal += net
                    if dd_type == 1 and bal > hwm:
                        hwm = bal
                    if net > max_day_gain:
                        max_day_gain = net

                    if flg != 0:
                        tdays += 1
                    if min_prof_day_pct > 0.0 and net >= cap * min_prof_day_pct - 1e-9:
                        pdays_cnt += 1

                    if stage == 1:
                        met_target = bal >= p1_goal - 1e-9
                        met_days = (tdays >= min_days) and (pdays_cnt >= min_prof_days)
                        met_cons = True
                        if best_day_cap_pct > 0.0:
                            tot_prof = bal - cap
                            if tot_prof <= 0.0 or max_day_gain > best_day_cap_pct * tot_prof + 1e-9:
                                met_cons = False
                        if met_target and met_days and met_cons:
                            if steps == 1:
                                stage = 3
                                bal = cap
                                hwm = cap
                                tdays = 0
                                pdays_cnt = 0
                                cycle_d = 0
                                max_day_gain = 0.0
                                if f_eval_pass < 0:
                                    f_eval_pass = d + 1
                                if first_ticket_active and f_fn_enter < 0:
                                    f_fn_enter = d + 1
                            else:
                                stage = 2
                                bal = cap
                                hwm = cap
                                tdays = 0
                                pdays_cnt = 0
                                max_day_gain = 0.0
                    elif stage == 2:
                        met_target = bal >= p2_goal - 1e-9
                        met_days = (tdays >= min_days) and (pdays_cnt >= min_prof_days)
                        if met_target and met_days:
                            stage = 3
                            bal = cap
                            hwm = cap
                            tdays = 0
                            pdays_cnt = 0
                            cycle_d = 0
                            max_day_gain = 0.0
                            if f_eval_pass < 0:
                                f_eval_pass = d + 1
                            if first_ticket_active and f_fn_enter < 0:
                                f_fn_enter = d + 1
                    elif stage == 3:
                        cycle_d += 1
                        fn_month_days += 1
                        if funded_first_payout_prof_pct > 0.0 and net >= cap * funded_first_payout_prof_pct - 1e-9:
                            fn_pdays_cnt += 1
                        if cycle_d >= payout_cycle_days:
                            prof = bal - cap
                            cons_ok = True
                            if best_day_cap_pct > 0.0 and prof > 0.0:
                                if max_day_gain > best_day_cap_pct * prof + 1e-9:
                                    cons_ok = False
                            if payout_cnt == 0 and funded_first_payout_min_prof_days > 0:
                                if fn_pdays_cnt < funded_first_payout_min_prof_days:
                                    cons_ok = False
                            if payout_cnt == 0 and funded_first_payout_min_profit_pct > 0.0:
                                if prof < cap * funded_first_payout_min_profit_pct - 1e-9:
                                    cons_ok = False
                            if min_payout_profit_pct > 0.0 and prof < cap * min_payout_profit_pct - 1e-9:
                                cons_ok = False
                            if prof > 1e-6 and cons_ok:
                                withdrawable_prof = prof * (1.0 - payout_buffer_retention_pct)
                                gross_share = withdrawable_prof * profit_split
                                if gross_share >= min_payout_usd - 1e-9:
                                    payout_cnt += 1
                                    net_in = gross_share * (1.0 - withdrawal_fee_pct)
                                    if (
                                        not refunded
                                        and fee_refund_pct > 0.0
                                        and refund_payout_milestone > 0
                                        and payout_cnt >= refund_payout_milestone
                                    ):
                                        net_in += cur_ticket_fee * fee_refund_pct * (1.0 - refund_withdrawal_fee_pct)
                                        refunded = True
                                    cum_npv += net_in * inv_df[d + 1]
                                    cum_cf += net_in
                                    cum_payouts += net_in
                                    fn_month_paid = 1
                                    if f_pay1 < 0:
                                        f_pay1 = d + 1
                                    bal = cap + prof * payout_buffer_retention_pct
                                    hwm = bal
                                    max_day_gain = 0.0
                            cycle_d = 0

                        if fn_month_days >= 21:
                            tot_fn_m += 1
                            if fn_month_paid == 0:
                                dry_fn_m += 1
                                cur_dry_streak += 1
                                if cur_dry_streak > best_dry_streak:
                                    best_dry_streak = cur_dry_streak
                            else:
                                cur_dry_streak = 0
                            fn_month_days = 0
                            fn_month_paid = 0

                cur_oop = cum_fees - cum_payouts
                if cur_oop > path_oop:
                    path_oop = cur_oop

            if (not recorded_24m) and (d + 1 == cutoff_24m):
                npv_24m[b] = cum_npv
                cf_24m[b] = cum_cf
                fees_24m[b] = cum_fees
                payouts_24m[b] = cum_payouts
                recorded_24m = True

        if not recorded_24m:
            npv_24m[b] = cum_npv
            cf_24m[b] = cum_cf
            fees_24m[b] = cum_fees
            payouts_24m[b] = cum_payouts

        npv_36m[b] = cum_npv
        cf_36m[b] = cum_cf
        max_oop[b] = path_oop
        tickets_used[b] = attempts
        eval_pass_day[b] = f_eval_pass
        eval_fail_day[b] = f_eval_fail
        pay1_day[b] = f_pay1
        funded_enter_day[b] = f_fn_enter
        funded_breach_day[b] = f_fn_breach
        bot_kill_any[b] = b_kill
        firm_breach_any[b] = f_br
        firm_breach_daily[b] = f_br_d
        firm_breach_maxdd[b] = f_br_m
        funded_months_total[b] = tot_fn_m
        funded_months_dry[b] = dry_fn_m
        funded_max_dry_streak[b] = best_dry_streak

    return (
        eval_pass_day,
        eval_fail_day,
        pay1_day,
        funded_enter_day,
        funded_breach_day,
        bot_kill_any,
        firm_breach_any,
        firm_breach_daily,
        firm_breach_maxdd,
        npv_24m,
        npv_36m,
        cf_24m,
        cf_36m,
        fees_24m,
        payouts_24m,
        max_oop,
        tickets_used,
        funded_months_total,
        funded_months_dry,
        funded_max_dry_streak,
    )

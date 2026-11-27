"""Numba-JIT multi-slot, multi-firm correlated capital scaling policy kernel & template packer."""

from __future__ import annotations

from typing import Any

import numpy as np
from numba import njit

from quant_factory.capital_optimizer.catalog_normalize import _daily_dd_anchor_code, _dd_type_code


@njit(cache=True)
def _init_slot(
    s_tpl: np.ndarray,
    s_stage: np.ndarray,
    s_bal: np.ndarray,
    s_hwm: np.ndarray,
    s_tdays: np.ndarray,
    s_pdays: np.ndarray,
    s_cycd: np.ndarray,
    s_maxg: np.ndarray,
    s_ref: np.ndarray,
    s_pcnt: np.ndarray,
    s_fnpdays: np.ndarray,
    s_paid_fee: np.ndarray,
    slot_idx: int,
    tid: int,
    steps: int,
    cap: float,
    base_fee: float,
) -> None:
    s_tpl[slot_idx] = tid
    s_stage[slot_idx] = 3 if steps == 0 else 1
    s_bal[slot_idx] = cap
    s_hwm[slot_idx] = cap
    s_tdays[slot_idx] = 0
    s_pdays[slot_idx] = 0
    s_cycd[slot_idx] = 0
    s_maxg[slot_idx] = 0.0
    s_ref[slot_idx] = 0
    s_pcnt[slot_idx] = 0
    s_fnpdays[slot_idx] = 0
    s_paid_fee[slot_idx] = base_fee


@njit(cache=True)
def _simulate_capital_policy_numba(
    idx_matrix: np.ndarray,
    hazard_days: np.ndarray,
    tpl_n_p1: np.ndarray, tpl_d_p1: np.ndarray, tpl_u_p1: np.ndarray, tpl_f_p1: np.ndarray,
    tpl_n_p1l: np.ndarray, tpl_d_p1l: np.ndarray, tpl_u_p1l: np.ndarray, tpl_f_p1l: np.ndarray,
    tpl_n_p2: np.ndarray, tpl_d_p2: np.ndarray, tpl_u_p2: np.ndarray, tpl_f_p2: np.ndarray,
    tpl_n_p2l: np.ndarray, tpl_d_p2l: np.ndarray, tpl_u_p2l: np.ndarray, tpl_f_p2l: np.ndarray,
    tpl_n_fn: np.ndarray, tpl_d_fn: np.ndarray, tpl_u_fn: np.ndarray, tpl_f_fn: np.ndarray,
    tpl_n_amb: np.ndarray, tpl_d_amb: np.ndarray, tpl_u_amb: np.ndarray, tpl_f_amb: np.ndarray,
    tpl_n_red: np.ndarray, tpl_d_red: np.ndarray, tpl_u_red: np.ndarray, tpl_f_red: np.ndarray,
    tpl_firm_id: np.ndarray,
    tpl_steps: np.ndarray,
    tpl_cap: np.ndarray,
    tpl_fee_day0_usd: np.ndarray,
    tpl_fee_regular_usd: np.ndarray,
    tpl_refund_pct: np.ndarray,
    tpl_wd_fee_pct: np.ndarray,
    tpl_refund_wd_fee_pct: np.ndarray,
    tpl_p1_target: np.ndarray,
    tpl_p2_target: np.ndarray,
    tpl_daily_lim: np.ndarray,
    tpl_max_dd_lim: np.ndarray,
    tpl_dd_type: np.ndarray,
    tpl_daily_dd_anchor: np.ndarray,
    tpl_best_day_cap: np.ndarray,
    tpl_min_days: np.ndarray,
    tpl_min_prof_days: np.ndarray,
    tpl_min_prof_pct: np.ndarray,
    tpl_split: np.ndarray,
    tpl_payout_cycle: np.ndarray,
    tpl_min_payout: np.ndarray,
    tpl_p1_lock_trig: np.ndarray,
    tpl_p2_lock_trig: np.ndarray,
    tpl_amber_dd: np.ndarray,
    tpl_red_dd: np.ndarray,
    tpl_p1_ea_stop: np.ndarray,
    tpl_p2_ea_stop: np.ndarray,
    tpl_fn_ea_stop: np.ndarray,
    tpl_refund_milestone: np.ndarray,
    tpl_buf_ret_pct: np.ndarray,
    tpl_lock_init_p1: np.ndarray,
    tpl_min_pay_prof_pct: np.ndarray,
    tpl_daily_prof_cap_pct: np.ndarray,
    tpl_fn_p1_prof_days: np.ndarray,
    tpl_fn_p1_prof_pct: np.ndarray,
    policy_mode: int,
    ladder_tpls: np.ndarray,
    max_slots: int,
    allow_downgrade: bool,
    upgrade_buf_mult: float,
    downgrade_buf_mult: float,
    init_bankroll_usd: float,
    monthly_topup_usd: float,
    card_fx_fee_pct: float,
    discount_rate_annual: float,
    own_book_overflow_mult: float,
    own_book_daily_ret: float,
    abort_after_day: int,
    wait_for_top_rung_slot2: bool = False,
):
    """Multi-account, multi-firm correlated capital scaling simulator with Day-0 vs Regular fees & NPV."""
    n_paths, horizon = idx_matrix.shape
    n_ladder = len(ladder_tpls)
    n_firms = hazard_days.shape[1]
    r_ann = discount_rate_annual
    inv_df = np.empty(horizon + 2, dtype=np.float64)
    for k_d in range(horizon + 2):
        inv_df[k_d] = (1.0 + r_ann) ** (-k_d / 252.0)
    top_tpl = ladder_tpls[n_ladder - 1]
    top_eff_fee_reg = tpl_fee_regular_usd[top_tpl] * (1.0 + card_fx_fee_pct)
    ob_cap_usd = top_eff_fee_reg * own_book_overflow_mult if own_book_overflow_mult > 0.0 else 1e18

    npv_24m = np.zeros(n_paths, dtype=np.float64)
    npv_36m = np.zeros(n_paths, dtype=np.float64)
    cf_24m = np.zeros(n_paths, dtype=np.float64)
    cf_36m = np.zeros(n_paths, dtype=np.float64)
    wealth_24m = np.zeros(n_paths, dtype=np.float64)
    wealth_36m = np.zeros(n_paths, dtype=np.float64)
    own_book_36m = np.zeros(n_paths, dtype=np.float64)
    ruined_ever = np.zeros(n_paths, dtype=np.int8)
    ruined_24m = np.zeros(n_paths, dtype=np.int8)
    pay1_day = np.full(n_paths, -1, dtype=np.int32)
    funded_dry_tot = np.zeros(n_paths, dtype=np.int32)
    funded_dry_zero = np.zeros(n_paths, dtype=np.int32)
    funded_max_dry_streak = np.zeros(n_paths, dtype=np.int32)
    total_fees_24m = np.zeros(n_paths, dtype=np.float64)
    total_payouts_24m = np.zeros(n_paths, dtype=np.float64)
    simult_fail_any = np.zeros(n_paths, dtype=np.int8)
    firm_disrupt_hits = np.zeros(n_paths, dtype=np.int32)
    max_funded_nom = np.zeros(n_paths, dtype=np.float64)
    max_oop_arr = np.zeros(n_paths, dtype=np.float64)

    min_policy_fee_day0 = 1e18
    min_policy_fee_reg = 1e18
    for i in range(n_ladder):
        ef0 = tpl_fee_day0_usd[ladder_tpls[i]] * (1.0 + card_fx_fee_pct)
        efr = tpl_fee_regular_usd[ladder_tpls[i]] * (1.0 + card_fx_fee_pct)
        if ef0 < min_policy_fee_day0:
            min_policy_fee_day0 = ef0
        if efr < min_policy_fee_reg:
            min_policy_fee_reg = efr

    s_stage = np.zeros(max_slots, dtype=np.int8)
    s_tpl = np.full(max_slots, -1, dtype=np.int32)
    s_bal = np.zeros(max_slots, dtype=np.float64)
    s_hwm = np.zeros(max_slots, dtype=np.float64)
    s_tdays = np.zeros(max_slots, dtype=np.int32)
    s_pdays = np.zeros(max_slots, dtype=np.int32)
    s_cycd = np.zeros(max_slots, dtype=np.int32)
    s_maxg = np.zeros(max_slots, dtype=np.float64)
    s_ref = np.zeros(max_slots, dtype=np.int8)
    s_pcnt = np.zeros(max_slots, dtype=np.int32)
    s_fnpdays = np.zeros(max_slots, dtype=np.int32)
    s_paid_fee = np.zeros(max_slots, dtype=np.float64)
    firm_dead = np.zeros(n_firms, dtype=np.int8)

    for b in range(n_paths):
        cash_res = init_bankroll_usd
        own_book = 0.0
        pv_fees = 0.0
        pv_payouts = 0.0
        pv_ob_in = 0.0
        tot_ob_in = 0.0
        tot_fees = 0.0
        tot_payouts = 0.0
        path_max_oop = 0.0

        for s in range(max_slots):
            s_stage[s] = 0
            s_tpl[s] = -1
            s_bal[s] = 0.0
            s_hwm[s] = 0.0
            s_tdays[s] = 0
            s_pdays[s] = 0
            s_cycd[s] = 0
            s_maxg[s] = 0.0
            s_ref[s] = 0
            s_pcnt[s] = 0
            s_fnpdays[s] = 0
            s_paid_fee[s] = 0.0
        for f_i in range(n_firms):
            firm_dead[f_i] = 0
        cur_rung = 0
        ever_funded_rung = -1
        f_pay1 = -1
        had_ruin = 0
        had_ruin_24 = 0
        had_sim_fail = 0
        disrupt_cnt = 0
        best_nom = 0.0
        recorded_24 = False

        fn_m_days = 0
        fn_m_paid = 0
        cur_dry = 0
        best_dry = 0
        tot_fm = 0
        zero_fm = 0

        for d in range(horizon):
            if monthly_topup_usd > 0.0 and d > 0 and (d % 21 == 0):
                if abort_after_day < 0 or d < abort_after_day:
                    cash_res += monthly_topup_usd

            for f_i in range(n_firms):
                if firm_dead[f_i] == 0 and hazard_days[b, f_i] == d:
                    firm_dead[f_i] = 1
                    hit_active = 0
                    for s in range(max_slots):
                        if s_stage[s] > 0 and tpl_firm_id[s_tpl[s]] == f_i:
                            s_stage[s] = 0
                            s_tpl[s] = -1
                            s_bal[s] = 0.0
                            s_paid_fee[s] = 0.0
                            hit_active = 1
                    if hit_active == 1:
                        disrupt_cnt += 1

            can_buy = (abort_after_day < 0) or (d < abort_after_day)
            if can_buy:
                active_cnt = 0
                funded_cnt = 0
                for s in range(max_slots):
                    if s_stage[s] > 0:
                        active_cnt += 1
                        if s_stage[s] == 3:
                            funded_cnt += 1

                if policy_mode == 2:
                    for s in range(max_slots):
                        if s_stage[s] == 0 and s < n_ladder:
                            tid = ladder_tpls[s]
                            if firm_dead[tpl_firm_id[tid]] == 1:
                                continue
                            base_fee = tpl_fee_day0_usd[tid] if d == 0 else tpl_fee_regular_usd[tid]
                            ef = base_fee * (1.0 + card_fx_fee_pct)
                            req_cash = ef if active_cnt == 0 else (ef * upgrade_buf_mult)
                            if cash_res >= req_cash - 1e-9:
                                cash_res -= ef
                                pv_fees += ef * inv_df[d]
                                tot_fees += ef
                                _init_slot(
                                    s_tpl, s_stage, s_bal, s_hwm, s_tdays, s_pdays,
                                    s_cycd, s_maxg, s_ref, s_pcnt, s_fnpdays, s_paid_fee,
                                    s, tid, tpl_steps[tid], tpl_cap[tid], base_fee,
                                )
                                active_cnt += 1
                elif policy_mode == 3:
                    tid = ladder_tpls[cur_rung]
                    if firm_dead[tpl_firm_id[tid]] == 0:
                        base_fee = tpl_fee_day0_usd[tid] if d == 0 else tpl_fee_regular_usd[tid]
                        ef = base_fee * (1.0 + card_fx_fee_pct)
                        for s in range(max_slots):
                            if s_stage[s] != 0:
                                continue
                            req_cash = ef if (d == 0 or active_cnt == 0) else (ef * upgrade_buf_mult)
                            if cash_res >= req_cash - 1e-9:
                                cash_res -= ef
                                pv_fees += ef * inv_df[d]
                                tot_fees += ef
                                _init_slot(
                                    s_tpl, s_stage, s_bal, s_hwm, s_tdays, s_pdays,
                                    s_cycd, s_maxg, s_ref, s_pcnt, s_fnpdays, s_paid_fee,
                                    s, tid, tpl_steps[tid], tpl_cap[tid], base_fee,
                                )
                                active_cnt += 1
                else:
                    if policy_mode == 0:
                        while cur_rung + 1 < n_ladder:
                            next_tid = ladder_tpls[cur_rung + 1]
                            next_base = tpl_fee_day0_usd[next_tid] if d == 0 else tpl_fee_regular_usd[next_tid]
                            next_ef = next_base * (1.0 + card_fx_fee_pct)
                            if cash_res >= next_ef * upgrade_buf_mult - 1e-9 and (
                                ever_funded_rung >= cur_rung or d == 0
                            ):
                                cur_rung += 1
                            else:
                                break
                        if allow_downgrade:
                            while cur_rung > 0:
                                cur_tid = ladder_tpls[cur_rung]
                                cur_base = tpl_fee_day0_usd[cur_tid] if d == 0 else tpl_fee_regular_usd[cur_tid]
                                cur_ef = cur_base * (1.0 + card_fx_fee_pct)
                                if cash_res < cur_ef * downgrade_buf_mult - 1e-9:
                                    cur_rung -= 1
                                else:
                                    break
                    else:
                        while cur_rung + 1 < n_ladder:
                            next_tid = ladder_tpls[cur_rung + 1]
                            next_base = tpl_fee_day0_usd[next_tid] if d == 0 else tpl_fee_regular_usd[next_tid]
                            next_ef = next_base * (1.0 + card_fx_fee_pct)
                            if cash_res >= next_ef * upgrade_buf_mult - 1e-9 and funded_cnt >= 1:
                                cur_rung += 1
                            else:
                                break

                    for s in range(max_slots):
                        if s_stage[s] != 0:
                            continue
                        tid = ladder_tpls[cur_rung]
                        if firm_dead[tpl_firm_id[tid]] == 1:
                            continue
                        base_fee = tpl_fee_day0_usd[tid] if d == 0 else tpl_fee_regular_usd[tid]
                        ef = base_fee * (1.0 + card_fx_fee_pct)
                        buy_ok = False
                        if active_cnt == 0:
                            buy_ok = cash_res >= ef - 1e-9
                        elif funded_cnt >= 1 and cash_res >= ef * upgrade_buf_mult - 1e-9:
                            buy_ok = (not wait_for_top_rung_slot2) or (cur_rung == n_ladder - 1)
                        if buy_ok:
                            cash_res -= ef
                            pv_fees += ef * inv_df[d]
                            tot_fees += ef
                            _init_slot(
                                s_tpl, s_stage, s_bal, s_hwm, s_tdays, s_pdays,
                                s_cycd, s_maxg, s_ref, s_pcnt, s_fnpdays, s_paid_fee,
                                s, tid, tpl_steps[tid], tpl_cap[tid], base_fee,
                            )
                            active_cnt += 1

            alive_now = 0
            for s in range(max_slots):
                if s_stage[s] > 0:
                    alive_now += 1
            min_fee_now = min_policy_fee_day0 if d == 0 else min_policy_fee_reg
            if alive_now == 0 and cash_res < min_fee_now - 1e-9 and can_buy:
                had_ruin = 1
                if d < 504:
                    had_ruin_24 = 1

            src = idx_matrix[b, d]
            fails_today = 0
            any_funded_today = 0
            paid_today = 0
            cur_fn_nom = 0.0

            for s in range(max_slots):
                st = s_stage[s]
                if st <= 0:
                    continue
                tid = s_tpl[s]
                cap = tpl_cap[tid]
                if st == 3:
                    any_funded_today = 1
                    cur_fn_nom += cap

                eq_pct = (s_bal[s] - cap) / cap
                if eq_pct <= -tpl_red_dd[tid]:
                    net, dd, up, flg = (
                        tpl_n_red[tid, src], tpl_d_red[tid, src], tpl_u_red[tid, src], tpl_f_red[tid, src],
                    )
                    ea_stop_pct = (
                        tpl_fn_ea_stop[tid] if st == 3 else (tpl_p2_ea_stop[tid] if st == 2 else tpl_p1_ea_stop[tid])
                    )
                elif eq_pct <= -tpl_amber_dd[tid]:
                    net, dd, up, flg = (
                        tpl_n_amb[tid, src], tpl_d_amb[tid, src], tpl_u_amb[tid, src], tpl_f_amb[tid, src],
                    )
                    ea_stop_pct = (
                        tpl_fn_ea_stop[tid] if st == 3 else (tpl_p2_ea_stop[tid] if st == 2 else tpl_p1_ea_stop[tid])
                    )
                elif st == 1:
                    prog = eq_pct / max(1e-6, tpl_p1_target[tid])
                    if tpl_p1_lock_trig[tid] > 0.0 and prog >= tpl_p1_lock_trig[tid]:
                        net, dd, up, flg = (
                            tpl_n_p1l[tid, src], tpl_d_p1l[tid, src], tpl_u_p1l[tid, src], tpl_f_p1l[tid, src],
                        )
                    else:
                        net, dd, up, flg = (
                            tpl_n_p1[tid, src], tpl_d_p1[tid, src], tpl_u_p1[tid, src], tpl_f_p1[tid, src],
                        )
                    ea_stop_pct = tpl_p1_ea_stop[tid]
                elif st == 2:
                    prog = eq_pct / max(1e-6, tpl_p2_target[tid])
                    if tpl_p2_lock_trig[tid] > 0.0 and prog >= tpl_p2_lock_trig[tid]:
                        net, dd, up, flg = (
                            tpl_n_p2l[tid, src], tpl_d_p2l[tid, src], tpl_u_p2l[tid, src], tpl_f_p2l[tid, src],
                        )
                    else:
                        net, dd, up, flg = (
                            tpl_n_p2[tid, src], tpl_d_p2[tid, src], tpl_u_p2[tid, src], tpl_f_p2[tid, src],
                        )
                    ea_stop_pct = tpl_p2_ea_stop[tid]
                else:
                    net, dd, up, flg = (
                        tpl_n_fn[tid, src], tpl_d_fn[tid, src], tpl_u_fn[tid, src], tpl_f_fn[tid, src],
                    )
                    ea_stop_pct = tpl_fn_ea_stop[tid]

                dd_t = tpl_dd_type[tid]
                if dd_t == 2:
                    if s_bal[s] + up > s_hwm[s]:
                        s_hwm[s] = s_bal[s] + up
                    max_floor = s_hwm[s] * (1.0 - tpl_max_dd_lim[tid])
                elif dd_t == 1:
                    max_floor = s_hwm[s] * (1.0 - tpl_max_dd_lim[tid])
                else:
                    if tpl_lock_init_p1[tid] == 1 and st == 3 and s_pcnt[s] >= 1:
                        max_floor = cap
                    else:
                        max_floor = cap * (1.0 - tpl_max_dd_lim[tid])

                if tpl_daily_dd_anchor[tid] == 1:
                    daily_floor = s_bal[s] * (1.0 - tpl_daily_lim[tid])
                else:
                    daily_floor = s_bal[s] - cap * tpl_daily_lim[tid]
                day_min = s_bal[s] - dd
                d_hit = day_min < daily_floor - 1e-9
                m_hit = day_min < max_floor - 1e-9
                ea_cut = cap * ea_stop_pct if ea_stop_pct > 0.0 else 1e18
                if (not d_hit) and (not m_hit) and (dd > ea_cut):
                    dd_eff = min(dd, ea_cut + cap * 0.0020)
                    net = min(net, -dd_eff)
                    day_min_eff = s_bal[s] - dd_eff
                    d_hit = day_min_eff < daily_floor - 1e-9
                    m_hit = day_min_eff < max_floor - 1e-9

                if d_hit or m_hit:
                    fails_today += 1
                    s_stage[s] = 0
                    s_tpl[s] = -1
                    s_bal[s] = 0.0
                    s_paid_fee[s] = 0.0
                    continue

                if tpl_daily_prof_cap_pct[tid] > 0.0 and net > cap * tpl_daily_prof_cap_pct[tid]:
                    net = cap * tpl_daily_prof_cap_pct[tid]
                s_bal[s] += net
                if dd_t == 1 and s_bal[s] > s_hwm[s]:
                    s_hwm[s] = s_bal[s]
                if net > s_maxg[s]:
                    s_maxg[s] = net
                if flg != 0:
                    s_tdays[s] += 1
                if tpl_min_prof_pct[tid] > 0.0 and net >= cap * tpl_min_prof_pct[tid] - 1e-9:
                    s_pdays[s] += 1

                if st == 1:
                    ok_t = s_bal[s] >= cap * (1.0 + tpl_p1_target[tid]) - 1e-9
                    ok_d = (s_tdays[s] >= tpl_min_days[tid]) and (s_pdays[s] >= tpl_min_prof_days[tid])
                    ok_c = True
                    if tpl_best_day_cap[tid] > 0.0:
                        pr = s_bal[s] - cap
                        if pr <= 0.0 or s_maxg[s] > tpl_best_day_cap[tid] * pr + 1e-9:
                            ok_c = False
                    if ok_t and ok_d and ok_c:
                        if tpl_steps[tid] == 1:
                            s_stage[s] = 3
                            s_bal[s] = cap
                            s_hwm[s] = cap
                            s_tdays[s] = 0
                            s_pdays[s] = 0
                            s_cycd[s] = 0
                            s_maxg[s] = 0.0
                            if cur_rung > ever_funded_rung:
                                ever_funded_rung = cur_rung
                        else:
                            s_stage[s] = 2
                            s_bal[s] = cap
                            s_hwm[s] = cap
                            s_tdays[s] = 0
                            s_pdays[s] = 0
                            s_maxg[s] = 0.0
                elif st == 2:
                    ok_t = s_bal[s] >= cap * (1.0 + tpl_p2_target[tid]) - 1e-9
                    ok_d = (s_tdays[s] >= tpl_min_days[tid]) and (s_pdays[s] >= tpl_min_prof_days[tid])
                    if ok_t and ok_d:
                        s_stage[s] = 3
                        s_bal[s] = cap
                        s_hwm[s] = cap
                        s_tdays[s] = 0
                        s_pdays[s] = 0
                        s_cycd[s] = 0
                        s_maxg[s] = 0.0
                        if cur_rung > ever_funded_rung:
                            ever_funded_rung = cur_rung
                elif st == 3:
                    s_cycd[s] += 1
                    if tpl_fn_p1_prof_pct[tid] > 0.0 and net >= cap * tpl_fn_p1_prof_pct[tid] - 1e-9:
                        s_fnpdays[s] += 1
                    if s_cycd[s] >= tpl_payout_cycle[tid]:
                        prof = s_bal[s] - cap
                        ok_c = True
                        if tpl_best_day_cap[tid] > 0.0 and prof > 0.0:
                            if s_maxg[s] > tpl_best_day_cap[tid] * prof + 1e-9:
                                ok_c = False
                        if s_pcnt[s] == 0 and tpl_fn_p1_prof_days[tid] > 0:
                            if s_fnpdays[s] < tpl_fn_p1_prof_days[tid]:
                                ok_c = False
                        if tpl_min_pay_prof_pct[tid] > 0.0 and prof < cap * tpl_min_pay_prof_pct[tid] - 1e-9:
                            ok_c = False
                        if prof > 1e-6 and ok_c:
                            buf_ret = tpl_buf_ret_pct[tid]
                            gross_share = prof * (1.0 - buf_ret) * tpl_split[tid]
                            if gross_share >= tpl_min_payout[tid] - 1e-9:
                                s_pcnt[s] += 1
                                net_in = gross_share * (1.0 - tpl_wd_fee_pct[tid])
                                if (
                                    s_ref[s] == 0
                                    and tpl_refund_pct[tid] > 0.0
                                    and tpl_refund_milestone[tid] > 0
                                    and s_pcnt[s] >= tpl_refund_milestone[tid]
                                ):
                                    net_in += (
                                        s_paid_fee[s] * tpl_refund_pct[tid] * (1.0 - tpl_refund_wd_fee_pct[tid])
                                    )
                                    s_ref[s] = 1
                                pv_payouts += net_in * inv_df[d + 1]
                                tot_payouts += net_in
                                cash_res += net_in
                                paid_today = 1
                                if f_pay1 < 0:
                                    f_pay1 = d + 1
                                s_bal[s] = cap + prof * buf_ret
                                s_hwm[s] = s_bal[s]
                                s_maxg[s] = 0.0
                        s_cycd[s] = 0

            if fails_today >= 2:
                had_sim_fail = 1
            if cur_fn_nom > best_nom:
                best_nom = cur_fn_nom

            if any_funded_today == 1:
                fn_m_days += 1
                if paid_today == 1:
                    fn_m_paid = 1
                if fn_m_days >= 21:
                    tot_fm += 1
                    if fn_m_paid == 0:
                        zero_fm += 1
                        cur_dry += 1
                        if cur_dry > best_dry:
                            best_dry = cur_dry
                    else:
                        cur_dry = 0
                    fn_m_days = 0
                    fn_m_paid = 0

            if own_book > 0.0:
                own_book *= 1.0 + own_book_daily_ret
            if own_book_overflow_mult > 0.0 and cash_res > ob_cap_usd:
                excess = cash_res - ob_cap_usd
                cash_res = ob_cap_usd
                own_book += excess
                tot_ob_in += excess
                pv_ob_in += excess * inv_df[d + 1]

            cur_oop = tot_fees - tot_payouts
            if cur_oop > path_max_oop:
                path_max_oop = cur_oop

            if (not recorded_24) and (d + 1 == 504):
                ob_npv_delta = (own_book * inv_df[504]) - pv_ob_in
                npv_24m[b] = pv_payouts - pv_fees + ob_npv_delta
                cf_24m[b] = tot_payouts - tot_fees + (own_book - tot_ob_in)
                wealth_24m[b] = cash_res + own_book
                total_fees_24m[b] = tot_fees
                total_payouts_24m[b] = tot_payouts
                recorded_24 = True

        ob_npv_delta36 = (own_book * inv_df[horizon]) - pv_ob_in
        if not recorded_24:
            npv_24m[b] = pv_payouts - pv_fees + ob_npv_delta36
            cf_24m[b] = tot_payouts - tot_fees + (own_book - tot_ob_in)
            wealth_24m[b] = cash_res + own_book
            total_fees_24m[b] = tot_fees
            total_payouts_24m[b] = tot_payouts

        npv_36m[b] = pv_payouts - pv_fees + ob_npv_delta36
        cf_36m[b] = tot_payouts - tot_fees + (own_book - tot_ob_in)
        wealth_36m[b] = cash_res + own_book
        own_book_36m[b] = own_book
        ruined_ever[b] = had_ruin
        ruined_24m[b] = had_ruin_24
        pay1_day[b] = f_pay1
        funded_dry_tot[b] = tot_fm
        funded_dry_zero[b] = zero_fm
        funded_max_dry_streak[b] = best_dry
        simult_fail_any[b] = had_sim_fail
        firm_disrupt_hits[b] = disrupt_cnt
        max_funded_nom[b] = best_nom
        max_oop_arr[b] = path_max_oop

    return (
        npv_24m, npv_36m, cf_24m, cf_36m, wealth_24m, wealth_36m, own_book_36m,
        ruined_ever, ruined_24m, pay1_day, funded_dry_tot, funded_dry_zero,
        funded_max_dry_streak, total_fees_24m, total_payouts_24m,
        simult_fail_any, firm_disrupt_hits, max_funded_nom, max_oop_arr,
    )


def _pack_templates_for_numba(templates: list[dict[str, Any]]) -> tuple[Any, ...]:
    """Pack template dicts (exact M1 arrays + Day-0/Regular fees + daily DD anchor) into NumPy arrays."""
    n_tpl = len(templates)
    n_obs = len(templates[0]["stage_arrays"][0])

    def _stack(pos: int, dtype: Any = np.float64) -> np.ndarray:
        arr = np.empty((n_tpl, n_obs), dtype=dtype)
        for i, t in enumerate(templates):
            arr[i] = t["stage_arrays"][pos]
        return np.ascontiguousarray(arr)

    return (
        _stack(0), _stack(1), _stack(2), _stack(3, np.int8),
        _stack(4), _stack(5), _stack(6), _stack(7, np.int8),
        _stack(8), _stack(9), _stack(10), _stack(11, np.int8),
        _stack(12), _stack(13), _stack(14), _stack(15, np.int8),
        _stack(16), _stack(17), _stack(18), _stack(19, np.int8),
        _stack(20), _stack(21), _stack(22), _stack(23, np.int8),
        _stack(24), _stack(25), _stack(26), _stack(27, np.int8),
        np.ascontiguousarray([int(t["firm_idx"]) for t in templates], dtype=np.int32),
        np.ascontiguousarray([int(t["steps"]) for t in templates], dtype=np.int32),
        np.ascontiguousarray([float(t["capital_usd"]) for t in templates], dtype=np.float64),
        np.ascontiguousarray(
            [float(t.get("fee_day0_usd", t.get("fee_usd", 0.0))) for t in templates], dtype=np.float64
        ),
        np.ascontiguousarray(
            [
                float(t.get("fee_regular_usd", t.get("fee_day0_usd", t.get("fee_usd", 0.0))))
                for t in templates
            ],
            dtype=np.float64,
        ),
        np.ascontiguousarray([float(t["fee_refund_pct"]) for t in templates], dtype=np.float64),
        np.ascontiguousarray(
            [float(t.get("payout_withdrawal_fee_pct", t.get("withdrawal_fee_pct", 0.015))) for t in templates],
            dtype=np.float64,
        ),
        np.ascontiguousarray([float(t.get("refund_withdrawal_fee_pct", 0.0)) for t in templates], dtype=np.float64),
        np.ascontiguousarray([float(t["p1_target_pct"]) for t in templates], dtype=np.float64),
        np.ascontiguousarray([float(t["p2_target_pct"]) for t in templates], dtype=np.float64),
        np.ascontiguousarray([float(t["dd_daily_pct"]) for t in templates], dtype=np.float64),
        np.ascontiguousarray([float(t["dd_max_pct"]) for t in templates], dtype=np.float64),
        np.ascontiguousarray([_dd_type_code(t["dd_type"]) for t in templates], dtype=np.int32),
        np.ascontiguousarray(
            [_daily_dd_anchor_code(t.get("daily_dd_anchor", "initial_balance")) for t in templates],
            dtype=np.int32,
        ),
        np.ascontiguousarray([float(t["best_day_cap_pct"]) for t in templates], dtype=np.float64),
        np.ascontiguousarray([int(t["min_trading_days"]) for t in templates], dtype=np.int32),
        np.ascontiguousarray([int(t["min_profitable_days"]) for t in templates], dtype=np.int32),
        np.ascontiguousarray([float(t["min_profitable_day_pct"]) for t in templates], dtype=np.float64),
        np.ascontiguousarray([float(t["profit_split_pct"]) for t in templates], dtype=np.float64),
        np.ascontiguousarray([int(t["payout_cycle_trading_days"]) for t in templates], dtype=np.int32),
        np.ascontiguousarray([float(t["min_payout_usd"]) for t in templates], dtype=np.float64),
        np.ascontiguousarray([float(t["p1_lock_trigger"]) for t in templates], dtype=np.float64),
        np.ascontiguousarray([float(t["p2_lock_trigger"]) for t in templates], dtype=np.float64),
        np.ascontiguousarray([float(t["amber_dd"]) for t in templates], dtype=np.float64),
        np.ascontiguousarray([float(t["red_dd"]) for t in templates], dtype=np.float64),
        np.ascontiguousarray([float(t["p1_ea_stop"]) for t in templates], dtype=np.float64),
        np.ascontiguousarray([float(t["p2_ea_stop"]) for t in templates], dtype=np.float64),
        np.ascontiguousarray([float(t["fn_ea_stop"]) for t in templates], dtype=np.float64),
        np.ascontiguousarray([int(t.get("refund_payout_milestone", 1)) for t in templates], dtype=np.int32),
        np.ascontiguousarray([float(t.get("payout_buffer_retention_pct", 0.0)) for t in templates], dtype=np.float64),
        np.ascontiguousarray(
            [1 if t.get("locks_at_initial_after_first_payout", False) else 0 for t in templates],
            dtype=np.int8,
        ),
        np.ascontiguousarray([float(t.get("min_payout_profit_pct", 0.0)) for t in templates], dtype=np.float64),
        np.ascontiguousarray([float(t.get("daily_profit_cap_pct", 0.0)) for t in templates], dtype=np.float64),
        np.ascontiguousarray(
            [int(t.get("funded_first_payout_min_prof_days", 0)) for t in templates], dtype=np.int32
        ),
        np.ascontiguousarray(
            [float(t.get("funded_first_payout_prof_pct", 0.0)) for t in templates], dtype=np.float64
        ),
    )

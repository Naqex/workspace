"""Dual-horizon dynamic sale-calendar sweep (`Y = 0..180` dense sweep, buy-now vs wait NPV)."""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from quant_factory.capital_optimizer.catalog_normalize import _daily_dd_anchor_code, _dd_type_code
from quant_factory.capital_optimizer.constants import (
    CALENDAR_DAYS_PER_TRADING_DAY,
    TRADING_DAYS_PER_MONTH,
    StageArrays,
)
from quant_factory.capital_optimizer.simulator import _simulate_single_ticket_rules_numba


def _as_stage_arrays(stage_arrays: tuple[np.ndarray, ...]) -> StageArrays:
    if len(stage_arrays) != 28:
        raise ValueError(f"Expected 28 stage arrays, got {len(stage_arrays)}")
    return stage_arrays


def _sale_common_kwargs(
    program_tier: dict[str, Any],
    *,
    card_fx_fee_pct: float,
    discount_rate_annual: float,
    p1_lock_trigger: float = 0.70,
    p2_lock_trigger: float = 0.70,
    amber_dd: float = 0.035,
    red_dd: float = 0.060,
    p1_ea_stop: float = 0.035,
    p2_ea_stop: float = 0.030,
    fn_ea_stop: float = 0.025,
    max_retries: int = 0,
) -> dict[str, Any]:
    return {
        "steps": int(program_tier["steps"]),
        "cap": float(program_tier["capital_usd"]),
        "card_fx_fee_pct": float(card_fx_fee_pct),
        "withdrawal_fee_pct": float(
            program_tier.get("payout_withdrawal_fee_pct", program_tier.get("withdrawal_fee_pct", 0.015))
        ),
        "fee_refund_pct": float(program_tier.get("fee_refund_pct", 1.0)),
        "p1_target": float(program_tier.get("p1_target_pct", 0.10)),
        "p2_target": float(program_tier.get("p2_target_pct", 0.05)),
        "daily_lim": float(program_tier.get("dd_daily_pct", 0.05)),
        "max_dd_lim": float(program_tier.get("dd_max_pct", 0.10)),
        "dd_type": _dd_type_code(program_tier.get("dd_type", "static")),
        "trail_lock_initial": bool(program_tier.get("trail_lock_at_initial", False)),
        "best_day_cap_pct": float(program_tier.get("best_day_cap_pct", 0.0)),
        "min_days": int(program_tier.get("min_trading_days", 4)),
        "min_prof_days": int(program_tier.get("min_profitable_days", 0)),
        "min_prof_day_pct": float(program_tier.get("min_profitable_day_pct", 0.0)),
        "profit_split": float(program_tier.get("profit_split_pct", 0.80)),
        "payout_cycle_days": int(program_tier.get("payout_cycle_trading_days", 10)),
        "min_payout_usd": float(program_tier.get("min_payout_usd", 50.0)),
        "strict_lt_breach": True,
        "p1_lock_trigger": float(p1_lock_trigger),
        "p2_lock_trigger": float(p2_lock_trigger),
        "amber_dd": float(amber_dd),
        "red_dd": float(red_dd),
        "p1_ea_stop": float(p1_ea_stop),
        "p2_ea_stop": float(p2_ea_stop),
        "fn_ea_stop": float(fn_ea_stop),
        "discount_rate_annual": float(discount_rate_annual),
        "max_retries": int(max_retries),
        "refund_payout_milestone": int(program_tier.get("refund_payout_milestone", 1)),
        "payout_buffer_retention_pct": float(program_tier.get("payout_buffer_retention_pct", 0.0)),
        "locks_at_initial_after_first_payout": bool(
            program_tier.get("locks_at_initial_after_first_payout", False)
        ),
        "min_payout_profit_pct": float(program_tier.get("min_payout_profit_pct", 0.0)),
        "funded_first_payout_min_prof_days": int(program_tier.get("funded_first_payout_min_prof_days", 0)),
        "funded_first_payout_prof_pct": float(program_tier.get("funded_first_payout_prof_pct", 0.0)),
        "daily_profit_cap_pct": float(program_tier.get("daily_profit_cap_pct", 0.0)),
        "refund_withdrawal_fee_pct": float(program_tier.get("refund_withdrawal_fee_pct", 0.0)),
        "daily_dd_anchor_mode": _daily_dd_anchor_code(program_tier.get("daily_dd_anchor", "initial_balance")),
    }


def evaluate_wait_vs_buy_npv(
    idx_matrix: np.ndarray,
    stage_arrays: tuple[np.ndarray, ...],
    *,
    program_tier: dict[str, Any],
    orig_fee_usd: float,
    active_discount_pct: float,
    wait_cal_days: int,
    next_sale_discount_pct: float,
    card_fx_fee_pct: float,
    discount_rate_annual: float,
    usd_vnd_rate: float,
    p1_lock_trigger: float = 0.70,
    p2_lock_trigger: float = 0.70,
    amber_dd: float = 0.035,
    red_dd: float = 0.060,
    p1_ea_stop: float = 0.035,
    p2_ea_stop: float = 0.030,
    fn_ea_stop: float = 0.025,
    max_retries: int = 0,
    shifting_horizon: bool = False,
) -> dict[str, Any]:
    """Compare exact MC NPV of buying today vs waiting `Y` calendar days for a `Z%` sale."""
    fee_today = orig_fee_usd * (1.0 - active_discount_pct)
    fee_wait = orig_fee_usd * (1.0 - next_sale_discount_pct)
    wait_tdays = max(0, int(round(wait_cal_days / CALENDAR_DAYS_PER_TRADING_DAY)))

    common = _sale_common_kwargs(
        program_tier,
        card_fx_fee_pct=card_fx_fee_pct,
        discount_rate_annual=discount_rate_annual,
        p1_lock_trigger=p1_lock_trigger,
        p2_lock_trigger=p2_lock_trigger,
        amber_dd=amber_dd,
        red_dd=red_dd,
        p1_ea_stop=p1_ea_stop,
        p2_ea_stop=p2_ea_stop,
        fn_ea_stop=fn_ea_stop,
        max_retries=max_retries,
    )

    st_arrs = _as_stage_arrays(stage_arrays)
    res_today = _simulate_single_ticket_rules_numba(
        idx_matrix,
        *st_arrs,
        fee_day0_usd=float(fee_today),
        fee_regular_usd=float(orig_fee_usd),
        start_day_offset=0,
        shifting_horizon=False,
        **common,
    )
    res_wait = _simulate_single_ticket_rules_numba(
        idx_matrix,
        *st_arrs,
        fee_day0_usd=float(fee_wait),
        fee_regular_usd=float(orig_fee_usd),
        start_day_offset=wait_tdays,
        shifting_horizon=bool(shifting_horizon),
        **common,
    )

    npv24_today = float(np.mean(res_today[9]))
    npv36_today = float(np.mean(res_today[10]))
    npv24_wait = float(np.mean(res_wait[9]))
    npv36_wait = float(np.mean(res_wait[10]))

    delta24 = npv24_wait - npv24_today
    delta36 = npv36_wait - npv36_today
    return {
        "horizon_mode": "SHIFTING_24M_FROM_PURCHASE" if shifting_horizon else "FIXED_CALENDAR_DEADLINE",
        "wait_cal_days": int(wait_cal_days),
        "wait_trading_days": int(wait_tdays),
        "max_retries": int(max_retries),
        "active_discount_pct": round(active_discount_pct * 100.0, 1),
        "next_sale_discount_pct": round(next_sale_discount_pct * 100.0, 1),
        "fee_today_usd": round(fee_today, 2),
        "fee_wait_usd": round(fee_wait, 2),
        "fee_retry_regular_usd": round(orig_fee_usd, 2),
        "upfront_saving_usd": round((fee_today - fee_wait) * (1.0 + card_fx_fee_pct), 2),
        "npv_24m_today_usd": round(npv24_today, 2),
        "npv_24m_wait_usd": round(npv24_wait, 2),
        "delta_npv_24m_usd": round(delta24, 2),
        "delta_npv_24m_vnd_tr": round(delta24 * usd_vnd_rate / 1_000_000.0, 2),
        "npv_36m_today_usd": round(npv36_today, 2),
        "npv_36m_wait_usd": round(npv36_wait, 2),
        "delta_npv_36m_usd": round(delta36, 2),
        "delta_npv_36m_vnd_tr": round(delta36 * usd_vnd_rate / 1_000_000.0, 2),
        "worth_waiting_24m": bool(delta24 > 0.0),
        "worth_waiting_36m": bool(delta36 > 0.0),
    }


def solve_max_wait_days_worth_it(
    idx_matrix: np.ndarray,
    stage_arrays: tuple[np.ndarray, ...],
    *,
    program_tier: dict[str, Any],
    orig_fee_usd: float,
    active_discount_pct: float,
    next_sale_discount_pct: float,
    card_fx_fee_pct: float,
    discount_rate_annual: float,
    usd_vnd_rate: float,
    horizon_months: int = 24,
    max_search_days: int = 180,
    **kwargs: Any,
) -> dict[str, Any]:
    """Dual-Horizon Dynamic Sale Calculator using exact dense sweep (`Y = 0..max_search_days`)."""
    del usd_vnd_rate
    fee_today = orig_fee_usd * (1.0 - active_discount_pct)
    fee_wait = orig_fee_usd * (1.0 - next_sale_discount_pct)
    max_retries = int(kwargs.get("max_retries", 0))

    common = _sale_common_kwargs(
        program_tier,
        card_fx_fee_pct=card_fx_fee_pct,
        discount_rate_annual=discount_rate_annual,
        p1_lock_trigger=float(kwargs.get("p1_lock_trigger", 0.70)),
        p2_lock_trigger=float(kwargs.get("p2_lock_trigger", 0.70)),
        amber_dd=float(kwargs.get("amber_dd", 0.035)),
        red_dd=float(kwargs.get("red_dd", 0.060)),
        p1_ea_stop=float(kwargs.get("p1_ea_stop", 0.035)),
        p2_ea_stop=float(kwargs.get("p2_ea_stop", 0.030)),
        fn_ea_stop=float(kwargs.get("fn_ea_stop", 0.025)),
        max_retries=max_retries,
    )

    target_td = 504 if horizon_months == 24 else int(horizon_months * TRADING_DAYS_PER_MONTH)
    idx_fixed = idx_matrix[:, : min(target_td, idx_matrix.shape[1])]
    npv_idx = 9 if horizon_months == 24 else 10

    st_arrs = _as_stage_arrays(stage_arrays)
    res_today = _simulate_single_ticket_rules_numba(
        idx_fixed,
        *st_arrs,
        fee_day0_usd=float(fee_today),
        fee_regular_usd=float(orig_fee_usd),
        start_day_offset=0,
        shifting_horizon=False,
        **common,
    )
    res_sale_day0 = _simulate_single_ticket_rules_numba(
        idx_fixed,
        *st_arrs,
        fee_day0_usd=float(fee_wait),
        fee_regular_usd=float(orig_fee_usd),
        start_day_offset=0,
        shifting_horizon=False,
        **common,
    )
    base_npv = float(np.mean(res_today[npv_idx]))
    sale_day0_npv = float(np.mean(res_sale_day0[npv_idx]))

    td_cache_fixed: dict[int, float] = {}

    def _delta_fixed_cal(days_y: int) -> float:
        wtd = max(0, int(round(days_y / CALENDAR_DAYS_PER_TRADING_DAY)))
        if wtd not in td_cache_fixed:
            res_w = _simulate_single_ticket_rules_numba(
                idx_fixed,
                *st_arrs,
                fee_day0_usd=float(fee_wait),
                fee_regular_usd=float(orig_fee_usd),
                start_day_offset=wtd,
                shifting_horizon=False,
                **common,
            )
            td_cache_fixed[wtd] = float(np.mean(res_w[npv_idx])) - base_npv
        return td_cache_fixed[wtd]

    can_mc_shift = (horizon_months == 24) and (idx_matrix.shape[1] > 504)
    max_shift_td = max(0, idx_matrix.shape[1] - 504) if can_mc_shift else 0
    td_cache_shift: dict[int, float] = {}

    def _delta_shift_mc_cal(days_y: int) -> float | None:
        if not can_mc_shift:
            return None
        wtd = max(0, int(round(days_y / CALENDAR_DAYS_PER_TRADING_DAY)))
        if wtd > max_shift_td:
            return None
        if wtd not in td_cache_shift:
            res_s = _simulate_single_ticket_rules_numba(
                idx_matrix[:, : (wtd + 504)],
                *st_arrs,
                fee_day0_usd=float(fee_wait),
                fee_regular_usd=float(orig_fee_usd),
                start_day_offset=wtd,
                shifting_horizon=True,
                **common,
            )
            td_cache_shift[wtd] = float(np.mean(res_s[9])) - base_npv
        return td_cache_shift[wtd]

    def _delta_shift_formula_cal(days_y: int) -> float:
        return sale_day0_npv * ((1.0 + discount_rate_annual) ** (-float(days_y) / 365.0)) - base_npv

    assumption_note = (
        "Assumes the future sale discount Z% is 100% guaranteed on calendar day Y; "
        "if uncertain (probability p < 100%), practical maximum wait days shrink accordingly."
    )

    if next_sale_discount_pct <= active_discount_pct + 1e-9:
        d1 = _delta_fixed_cal(1)
        d7 = _delta_fixed_cal(7)
        d14 = _delta_fixed_cal(14)
        d30 = _delta_fixed_cal(30)
        s7_mc = _delta_shift_mc_cal(7)
        s14_mc = _delta_shift_mc_cal(14)
        s30_mc = _delta_shift_mc_cal(30)
        return {
            "search_method": "EXACT_FULL_SWEEP_NO_BINARY_SEARCH",
            "max_retries": max_retries,
            "npv_today_usd": round(base_npv, 2),
            "npv_sale_day0_usd": round(sale_day0_npv, 2),
            "max_wait_days_worth_it": 0,
            "max_wait_days_fixed_deadline": 0,
            "contiguous_max_wait_days_fixed_deadline": 0,
            "non_monotonic_fixed_deadline": False,
            "delta_npv_at_1d_usd": round(d1, 2),
            "delta_npv_at_7d_usd": round(d7, 2),
            "delta_npv_at_14d_usd": round(d14, 2),
            "delta_npv_at_30d_usd": round(d30, 2),
            "shifting_horizon_search_method": "EXACT_DENSE_0_TO_MAX_SWEEP",
            "shifting_horizon_sweep_days_evaluated": 1,
            "shifting_horizon_formula_max_wait_days": 0.0,
            "shifting_horizon_mc_verified_max_wait_days": 0,
            "max_continuous_positive_wait_days": 0,
            "last_positive_wait_day": 0,
            "first_nonpositive_wait_day": 0,
            "non_monotonic_shifting_horizon": False,
            "shifting_horizon_non_monotonic_warning": "",
            "shifting_delta_formula_7d_usd": round(_delta_shift_formula_cal(7), 2),
            "shifting_delta_formula_14d_usd": round(_delta_shift_formula_cal(14), 2),
            "shifting_delta_formula_30d_usd": round(_delta_shift_formula_cal(30), 2),
            "shifting_delta_mc_7d_usd": round(s7_mc, 2) if s7_mc is not None else None,
            "shifting_delta_mc_14d_usd": round(s14_mc, 2) if s14_mc is not None else None,
            "shifting_delta_mc_30d_usd": round(s30_mc, 2) if s30_mc is not None else None,
            "assumption_disclosure": assumption_note,
            "decision": "BUY_TODAY_PROMO_ALREADY_ACTIVE_OR_BETTER",
        }

    best_fixed_y = 0
    contiguous_fixed_y = 0
    seen_nonpos = False
    non_monotonic = False
    prev_val: float | None = None
    for y in range(1, max_search_days + 1):
        val = _delta_fixed_cal(y)
        if prev_val is not None and val > prev_val + 1e-6:
            non_monotonic = True
        prev_val = val
        if val > 0.0:
            best_fixed_y = y
            if not seen_nonpos:
                contiguous_fixed_y = y
            else:
                non_monotonic = True
        else:
            seen_nonpos = True

    d1 = _delta_fixed_cal(1)
    d7 = _delta_fixed_cal(7)
    d14 = _delta_fixed_cal(14)
    d30 = _delta_fixed_cal(30)

    if base_npv > 0.0 and sale_day0_npv > base_npv and discount_rate_annual > 0.0:
        shift_formula_days = 365.0 * math.log(sale_day0_npv / base_npv) / math.log(1.0 + discount_rate_annual)
    elif sale_day0_npv <= base_npv:
        shift_formula_days = 0.0
    else:
        shift_formula_days = float(max_search_days)

    s7_mc = _delta_shift_mc_cal(7)
    s14_mc = _delta_shift_mc_cal(14)
    s30_mc = _delta_shift_mc_cal(30)
    shift_mc_max_cont_y: int | None = None
    shift_mc_last_pos_y: int | None = None
    shift_mc_first_nonpos_y: int | None = None
    shift_non_monotonic = False
    shift_days_evaluated = 0
    shift_warning = ""
    shift_mc_at_formula_minus5: float | None = None
    shift_mc_at_formula_plus5: float | None = None

    if can_mc_shift:
        max_shift_cal_avail = int(max_shift_td * CALENDAR_DAYS_PER_TRADING_DAY)
        sweep_hi = min(int(max_search_days), max_shift_cal_avail)
        if shift_formula_days > 0.0 and sweep_hi >= 1:
            lo_chk = max(1, min(sweep_hi, int(math.floor(shift_formula_days)) - 5))
            hi_chk = max(1, min(sweep_hi, int(math.ceil(shift_formula_days)) + 5))
            shift_mc_at_formula_minus5 = _delta_shift_mc_cal(lo_chk)
            shift_mc_at_formula_plus5 = _delta_shift_mc_cal(hi_chk)

        max_cont = 0
        last_pos = 0
        first_nonpos: int | None = None
        seen_nonpos_s = False
        prev_s_val: float | None = None
        eval_cnt = 0
        for y in range(0, sweep_hi + 1):
            dv = _delta_shift_mc_cal(y)
            if dv is None:
                break
            eval_cnt += 1
            if prev_s_val is not None and dv > prev_s_val + 1e-6:
                shift_non_monotonic = True
            prev_s_val = dv
            if dv > 0.0:
                last_pos = y
                if not seen_nonpos_s:
                    max_cont = y
                else:
                    shift_non_monotonic = True
            else:
                if not seen_nonpos_s:
                    first_nonpos = y
                seen_nonpos_s = True

        shift_days_evaluated = eval_cnt
        shift_mc_max_cont_y = int(max_cont)
        shift_mc_last_pos_y = int(last_pos)
        shift_mc_first_nonpos_y = int(first_nonpos) if first_nonpos is not None else None
        if shift_mc_last_pos_y > shift_mc_max_cont_y:
            shift_non_monotonic = True
            dip_day = (
                shift_mc_first_nonpos_y if shift_mc_first_nonpos_y is not None else (shift_mc_max_cont_y + 1)
            )
            shift_warning = (
                f"NON_MONOTONIC_SHIFTING_HORIZON: continuous positive wait ends at {shift_mc_max_cont_y}d "
                f"(day {dip_day}d already dips <= 0), although later MC noise rebounds positive up to "
                f"last_positive_wait_day={shift_mc_last_pos_y}d. NEVER interpret {shift_mc_last_pos_y}d as "
                f"'waiting any day up to {shift_mc_last_pos_y}d is positive'!"
            )

    if best_fixed_y == 0:
        decision = "BUY_TODAY_FIXED_DEADLINE_OR_WAIT_ONLY_IF_SHIFTING_HORIZON"
    else:
        decision = f"FIXED_DEADLINE_WAIT_LE_{best_fixed_y}D_SHIFTING_WAIT_LE_{int(round(shift_formula_days))}D"

    return {
        "search_method": "EXACT_FULL_SWEEP_NO_BINARY_SEARCH",
        "shifting_horizon_search_method": "EXACT_DENSE_0_TO_MAX_SWEEP",
        "shifting_horizon_sweep_days_evaluated": int(shift_days_evaluated),
        "max_retries": max_retries,
        "npv_today_usd": round(base_npv, 2),
        "npv_sale_day0_usd": round(sale_day0_npv, 2),
        "max_wait_days_worth_it": int(best_fixed_y),
        "max_wait_days_fixed_deadline": int(best_fixed_y),
        "contiguous_max_wait_days_fixed_deadline": int(contiguous_fixed_y),
        "non_monotonic_fixed_deadline": bool(non_monotonic),
        "delta_npv_at_1d_usd": round(d1, 2),
        "delta_npv_at_7d_usd": round(d7, 2),
        "delta_npv_at_14d_usd": round(d14, 2),
        "delta_npv_at_30d_usd": round(d30, 2),
        "shifting_horizon_formula_max_wait_days": round(shift_formula_days, 1),
        "shifting_horizon_mc_verified_max_wait_days": shift_mc_max_cont_y,
        "max_continuous_positive_wait_days": shift_mc_max_cont_y,
        "last_positive_wait_day": shift_mc_last_pos_y,
        "first_nonpositive_wait_day": shift_mc_first_nonpos_y,
        "non_monotonic_shifting_horizon": bool(shift_non_monotonic),
        "shifting_horizon_non_monotonic_warning": shift_warning,
        "shifting_delta_formula_7d_usd": round(_delta_shift_formula_cal(7), 2),
        "shifting_delta_formula_14d_usd": round(_delta_shift_formula_cal(14), 2),
        "shifting_delta_formula_30d_usd": round(_delta_shift_formula_cal(30), 2),
        "shifting_delta_mc_7d_usd": round(s7_mc, 2) if s7_mc is not None else None,
        "shifting_delta_mc_14d_usd": round(s14_mc, 2) if s14_mc is not None else None,
        "shifting_delta_mc_30d_usd": round(s30_mc, 2) if s30_mc is not None else None,
        "shifting_delta_mc_near_breakeven_minus5d_usd": (
            round(shift_mc_at_formula_minus5, 2) if shift_mc_at_formula_minus5 is not None else None
        ),
        "shifting_delta_mc_near_breakeven_plus5d_usd": (
            round(shift_mc_at_formula_plus5, 2) if shift_mc_at_formula_plus5 is not None else None
        ),
        "assumption_disclosure": assumption_note,
        "decision": decision,
    }

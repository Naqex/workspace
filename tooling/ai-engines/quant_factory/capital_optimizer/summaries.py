"""Monte Carlo statistical summaries (Wilson bounds, Law-13/15 single-ticket & policy Pareto winners)."""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from quant_factory.capital_optimizer.constants import (
    CALENDAR_DAYS_PER_TRADING_DAY,
    TRADING_DAYS_PER_MONTH,
    TRADING_DAYS_PER_YEAR,
)


def wilson_upper_95(k: int, n: int) -> float:
    """95% two-sided Wilson upper bound for a binomial proportion `k/n`."""
    if n <= 0:
        return 1.0
    z = 1.959963984540054
    p = k / n
    denom = 1.0 + z * z / n
    center = p + z * z / (2.0 * n)
    margin = z * math.sqrt((p * (1.0 - p) + z * z / (4.0 * n)) / n)
    return min(1.0, (center + margin) / denom)


def summarize_single_ticket_mc(
    res: tuple[np.ndarray, ...],
    *,
    fee_usd: float,
    card_fx_fee_pct: float,
    usd_vnd_rate: float,
    horizon_days: int,
    start_day_offset: int = 0,
    fee_regular_usd: float | None = None,
    refund_withdrawal_fee_pct: float = 0.0,
) -> dict[str, Any]:
    """Summarize Law-13 single-ticket zero-retry & NPV results with strict `Pass + Fail + Pending == 100%`."""
    (
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
        _payouts_24m,
        max_oop,
        tickets_used,
        fn_m_tot,
        fn_m_dry,
        fn_max_dry,
    ) = res
    n = len(eval_pass_day)
    fee_reg = float(fee_usd if fee_regular_usd is None else fee_regular_usd)
    eff_fee = fee_usd * (1.0 + card_fx_fee_pct)
    eff_fee_reg = fee_reg * (1.0 + card_fx_fee_pct)

    monthly_breakdown: dict[str, dict[str, float]] = {}
    for m in (3, 6, 12, 24, 36):
        cutoff = start_day_offset + m * TRADING_DAYS_PER_MONTH
        if cutoff > horizon_days:
            continue
        passed = (eval_pass_day >= 0) & (eval_pass_day <= cutoff)
        failed = (~passed) & (eval_fail_day > 0) & (eval_fail_day <= cutoff)
        pending = (~passed) & (~failed)
        p_pct = 100.0 * float(np.sum(passed)) / n
        f_pct = 100.0 * float(np.sum(failed)) / n
        w_pct = 100.0 * float(np.sum(pending)) / n
        if abs((p_pct + f_pct + w_pct) - 100.0) >= 1e-6:
            raise ValueError(f"Monthly Pass/Fail/Pending partition mismatch: {p_pct + f_pct + w_pct}")
        monthly_breakdown[f"{m}m"] = {
            "pass_pct": round(p_pct, 2),
            "fail_pct": round(f_pct, 2),
            "pending_pct": round(w_pct, 2),
            "sum_pct": round(p_pct + f_pct + w_pct, 2),
        }

    cal_pay1 = np.where(
        pay1_day > 0,
        (pay1_day - start_day_offset) * CALENDAR_DAYS_PER_TRADING_DAY,
        1e9,
    )
    uncond_pay1_cap365 = np.minimum(cal_pay1, 365.0)
    uncond_pay1_cap730 = np.minimum(cal_pay1, 730.0)
    paid_mask = pay1_day > 0
    passed_mask = eval_pass_day >= 0

    entered_fn_mask = funded_enter_day >= 0
    n_fn_entered = int(np.sum(entered_fn_mask))
    if n_fn_entered > 0:
        fn_enter_sub = funded_enter_day[entered_fn_mask]
        fn_br_sub = funded_breach_day[entered_fn_mask]
        br_within_12m = (fn_br_sub > 0) & ((fn_br_sub - fn_enter_sub) <= TRADING_DAYS_PER_YEAR)
        full_12m_obs = (fn_enter_sub + TRADING_DAYS_PER_YEAR) <= horizon_days
        n_censored = int(np.sum(~full_12m_obs))
        n_br_12m = int(np.sum(br_within_12m))
        n_full_12m = int(np.sum(full_12m_obs))
        n_br_full = int(np.sum(br_within_12m & full_12m_obs))
        fn_br_12m_all_pct = 100.0 * n_br_12m / n_fn_entered
        fn_br_12m_uncensored_pct = (100.0 * n_br_full / n_full_12m) if n_full_12m > 0 else 0.0
        wilson_ub_pct = 100.0 * wilson_upper_95(n_br_12m, n_fn_entered)
    else:
        n_censored = 0
        n_br_12m = 0
        n_full_12m = 0
        fn_br_12m_all_pct = 0.0
        fn_br_12m_uncensored_pct = 0.0
        wilson_ub_pct = 100.0

    tot_fn_months_all = int(np.sum(fn_m_tot))
    dry_fn_months_all = int(np.sum(fn_m_dry))
    dry_month_pct = (100.0 * dry_fn_months_all / tot_fn_months_all) if tot_fn_months_all > 0 else 100.0
    fn_paths_with_m = fn_max_dry[fn_m_tot > 0]
    dry_streak_p50 = int(np.median(fn_paths_with_m)) if len(fn_paths_with_m) > 0 else 0
    dry_streak_p95 = int(np.quantile(fn_paths_with_m, 0.95)) if len(fn_paths_with_m) > 0 else 0

    ev_npv24 = float(np.mean(npv_24m))
    med_npv24 = float(np.median(npv_24m))
    ev_cf24 = float(np.mean(cf_24m))
    med_cf24 = float(np.median(cf_24m))
    ev_npv36 = float(np.mean(npv_36m))
    ev_cf36 = float(np.mean(cf_36m))
    mean_fees24 = float(np.mean(fees_24m))

    return {
        "model_tag": "DAILY_APPROX",
        "n_paths": n,
        "pricing_regime": "BF_DAY0_PLUS_REGULAR_RETRIES" if fee_usd < fee_reg - 1e-6 else "ALL_REGULAR",
        "fee_usd": round(fee_usd, 2),
        "fee_day0_usd": round(fee_usd, 2),
        "fee_regular_usd": round(fee_reg, 2),
        "effective_fee_with_vn_fx_usd": round(eff_fee, 2),
        "effective_regular_fee_with_vn_fx_usd": round(eff_fee_reg, 2),
        "effective_fee_vnd_tr": round(eff_fee * usd_vnd_rate / 1_000_000.0, 2),
        "refund_withdrawal_fee_pct": round(refund_withdrawal_fee_pct * 100.0, 2),
        "monthly_pass_fail_pending": monthly_breakdown,
        "pass_24m_pct": monthly_breakdown.get("24m", {}).get("pass_pct", 0.0),
        "fail_eval_24m_pct": monthly_breakdown.get("24m", {}).get("fail_pct", 0.0),
        "pending_eval_24m_pct": monthly_breakdown.get("24m", {}).get("pending_pct", 0.0),
        "paid_any_pct": round(100.0 * float(np.mean(paid_mask)), 2),
        "cond_med_pass_cal_days": (
            round(
                float(np.median((eval_pass_day[passed_mask] - start_day_offset) * CALENDAR_DAYS_PER_TRADING_DAY)),
                1,
            )
            if np.any(passed_mask)
            else -1.0
        ),
        "cond_med_pay1_cal_days": round(float(np.median(cal_pay1[paid_mask])), 1) if np.any(paid_mask) else -1.0,
        "uncond_mean_pay1_cap365_days": round(float(np.mean(uncond_pay1_cap365)), 1),
        "uncond_med_pay1_cap365_days": round(float(np.median(uncond_pay1_cap365)), 1),
        "uncond_mean_pay1_cap730_days": round(float(np.mean(uncond_pay1_cap730)), 1),
        "uncond_med_pay1_cap730_days": round(float(np.median(uncond_pay1_cap730)), 1),
        "funded_12m_breach": {
            "n_entered_funded": n_fn_entered,
            "n_full_12m_observed": n_full_12m,
            "n_censored_lt_12m": n_censored,
            "n_breached_within_12m": n_br_12m,
            "breach_12m_pct": round(fn_br_12m_all_pct, 2),
            "breach_12m_uncensored_pct": round(fn_br_12m_uncensored_pct, 2),
            "wilson_95_upper_pct": round(wilson_ub_pct, 2),
            "note_n299": "De chung minh can tren 95% < 1% tren thuc te can ~299 quan sat doc lap khong chay.",
        },
        "funded_dry_months_pct": round(dry_month_pct, 2),
        "funded_dry_streak_p50_months": dry_streak_p50,
        "funded_dry_streak_p95_months": dry_streak_p95,
        "bot_auto_kill_pct": round(100.0 * float(np.mean(bot_kill_any > 0)), 2),
        "firm_hard_breach_pct": round(100.0 * float(np.mean(firm_breach_any > 0)), 2),
        "firm_hard_breach_daily_pct": round(100.0 * float(np.mean(firm_breach_daily > 0)), 2),
        "firm_hard_breach_maxdd_pct": round(100.0 * float(np.mean(firm_breach_maxdd > 0)), 2),
        "p_net_le_0_24m_pct": round(100.0 * float(np.mean(npv_24m <= 0.0)), 2),
        "avg_tickets": round(float(np.mean(tickets_used)), 2),
        "mean_fees_24m_usd": round(mean_fees24, 2),
        "ev_npv_24m_usd": round(ev_npv24, 2),
        "ev_npv_24m_vnd_tr": round(ev_npv24 * usd_vnd_rate / 1_000_000.0, 2),
        "med_npv_24m_usd": round(med_npv24, 2),
        "med_npv_24m_vnd_tr": round(med_npv24 * usd_vnd_rate / 1_000_000.0, 2),
        "ev_undisc_24m_usd": round(ev_cf24, 2),
        "med_undisc_24m_usd": round(med_cf24, 2),
        "ev_npv_36m_usd": round(ev_npv36, 2),
        "ev_npv_36m_vnd_tr": round(ev_npv36 * usd_vnd_rate / 1_000_000.0, 2),
        "ev_undisc_36m_usd": round(ev_cf36, 2),
        "ev_per_fee_npv24": round(ev_npv24 / max(1.0, eff_fee), 2),
        "ev_per_fee_undisc24": round(ev_cf24 / max(1.0, eff_fee), 2),
        "ev_per_total_fee_npv24": round(ev_npv24 / max(1.0, mean_fees24), 2),
        "oop95_usd": round(float(np.quantile(max_oop, 0.95)), 2),
        "oop95_vnd_tr": round(float(np.quantile(max_oop, 0.95)) * usd_vnd_rate / 1_000_000.0, 2),
    }


def summarize_capital_policy_mc(
    res: tuple[np.ndarray, ...],
    *,
    usd_vnd_rate: float,
    init_bankroll_vnd_tr: float,
    monthly_topup_vnd_tr: float,
) -> dict[str, Any]:
    """Summarize multi-slot capital policy MC run with VND/USD amounts, ruin, NPV & dry-month metrics."""
    (
        npv24, npv36, cf24, cf36, _w24, _w36, ob36,
        ruin_ev, ruin24, pay1, fm_tot, fm_dry, fm_streak,
        fees24, _pays24, sim_fail, disrupt, max_nom, max_oop,
    ) = res
    n = len(npv24)
    paid_mask = pay1 > 0
    cal_pay1 = np.where(paid_mask, pay1 * CALENDAR_DAYS_PER_TRADING_DAY, 1e9)
    uncond_cap365 = np.minimum(cal_pay1, 365.0)
    uncond_cap730 = np.minimum(cal_pay1, 730.0)

    tot_fm_sum = int(np.sum(fm_tot))
    dry_fm_sum = int(np.sum(fm_dry))
    dry_pct = (100.0 * dry_fm_sum / tot_fm_sum) if tot_fm_sum > 0 else 100.0
    streak_sub = fm_streak[fm_tot > 0]
    dry_p50 = int(np.median(streak_sub)) if len(streak_sub) > 0 else 0
    dry_p95 = int(np.quantile(streak_sub, 0.95)) if len(streak_sub) > 0 else 0

    ev_npv24 = float(np.mean(npv24))
    med_npv24 = float(np.median(npv24))
    ev_npv36 = float(np.mean(npv36))
    med_npv36 = float(np.median(npv36))
    ev_cf24 = float(np.mean(cf24))
    ev_cf36 = float(np.mean(cf36))
    mean_fees24 = float(np.mean(fees24))
    ruin_pct = 100.0 * float(np.mean(ruin_ev > 0))
    ruin24_pct = 100.0 * float(np.mean(ruin24 > 0))

    return {
        "model_tag": "DAILY_APPROX",
        "n_paths": n,
        "init_bankroll_vnd_tr": float(init_bankroll_vnd_tr),
        "monthly_topup_vnd_tr": float(monthly_topup_vnd_tr),
        "ruin_pct": round(ruin_pct, 2),
        "ruin_24m_pct": round(ruin24_pct, 2),
        "p_npv24_le_0_pct": round(100.0 * float(np.mean(npv24 <= 0.0)), 2),
        "paid_any_pct": round(100.0 * float(np.mean(paid_mask)), 2),
        "cond_med_pay1_cal_days": round(float(np.median(cal_pay1[paid_mask])), 1) if np.any(paid_mask) else -1.0,
        "uncond_med_pay1_cap365_days": round(float(np.median(uncond_cap365)), 1),
        "uncond_med_pay1_cap730_days": round(float(np.median(uncond_cap730)), 1),
        "ev_npv_24m_usd": round(ev_npv24, 1),
        "ev_npv_24m_vnd_tr": round(ev_npv24 * usd_vnd_rate / 1_000_000.0, 2),
        "med_npv_24m_usd": round(med_npv24, 1),
        "med_npv_24m_vnd_tr": round(med_npv24 * usd_vnd_rate / 1_000_000.0, 2),
        "ev_undisc_24m_usd": round(ev_cf24, 1),
        "ev_npv_36m_usd": round(ev_npv36, 1),
        "ev_npv_36m_vnd_tr": round(ev_npv36 * usd_vnd_rate / 1_000_000.0, 2),
        "med_npv_36m_usd": round(med_npv36, 1),
        "med_npv_36m_vnd_tr": round(med_npv36 * usd_vnd_rate / 1_000_000.0, 2),
        "ev_undisc_36m_usd": round(ev_cf36, 1),
        "ev_per_total_fee_npv24": round(ev_npv24 / max(1.0, mean_fees24), 2),
        "mean_fees_24m_usd": round(mean_fees24, 1),
        "mean_own_book_36m_usd": round(float(np.mean(ob36)), 1),
        "mean_own_book_36m_vnd_tr": round(float(np.mean(ob36)) * usd_vnd_rate / 1_000_000.0, 2),
        "funded_dry_months_pct": round(dry_pct, 2),
        "funded_dry_streak_p50_months": dry_p50,
        "funded_dry_streak_p95_months": dry_p95,
        "simultaneous_fail_pct": round(100.0 * float(np.mean(sim_fail > 0)), 2),
        "firm_disruption_rate_pct": round(100.0 * float(np.mean(disrupt > 0)), 2),
        "mean_max_funded_nom_usd": round(float(np.mean(max_nom)), 0),
        "oop95_usd": round(float(np.quantile(max_oop, 0.95)), 1),
        "oop95_vnd_tr": round(float(np.quantile(max_oop, 0.95)) * usd_vnd_rate / 1_000_000.0, 2),
    }


def _pick_pair_winners(sub_results: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Select Profile A (`<= 5%` ruin, max NPV) and Profile B (`<= 10%` ruin, min wait/dry)."""
    elig_a = [
        (pid, m)
        for pid, m in sub_results.items()
        if float(m["ruin_pct"]) <= 5.0 + 1e-9 and float(m["ev_npv_24m_usd"]) > 0.0
    ]
    if elig_a:
        best_a_id, best_a = max(
            elig_a, key=lambda kv: (kv[1]["ev_npv_36m_usd"], kv[1]["ev_npv_24m_usd"], -kv[1]["ruin_pct"])
        )
        a_status = "FEASIBLE_RUIN_LE_5PCT"
    else:
        best_a_id, best_a = min(
            sub_results.items(), key=lambda kv: (kv[1]["ruin_pct"], -kv[1]["ev_npv_36m_usd"])
        )
        a_status = "NO_POLICY_MEETS_5PCT_RUIN_LOWEST_RUIN_SHOWN"

    elig_b = [
        (pid, m)
        for pid, m in sub_results.items()
        if float(m["ruin_pct"]) <= 10.0 + 1e-9
        and float(m["ev_npv_24m_usd"]) > 0.0
        and float(m["paid_any_pct"]) >= 50.0
    ]
    if elig_b:
        best_b_id, best_b = min(
            elig_b,
            key=lambda kv: (
                kv[1]["uncond_med_pay1_cap730_days"],
                kv[1]["funded_dry_months_pct"],
                -kv[1]["paid_any_pct"],
                -kv[1]["ev_npv_24m_usd"],
            ),
        )
        b_status = "FEASIBLE_RUIN_LE_10PCT"
    else:
        elig_b_safe = [
            (pid, m)
            for pid, m in sub_results.items()
            if float(m["ruin_pct"]) <= 10.0 + 1e-9 and float(m["ev_npv_24m_usd"]) > 0.0
        ]
        if elig_b_safe:
            best_b_id, best_b = min(
                elig_b_safe,
                key=lambda kv: (
                    -kv[1]["paid_any_pct"],
                    kv[1]["funded_dry_months_pct"],
                    kv[1]["cond_med_pay1_cal_days"] if kv[1]["cond_med_pay1_cal_days"] > 0 else 1e9,
                    -kv[1]["ev_npv_24m_usd"],
                ),
            )
            b_status = "FEASIBLE_RUIN_LE_10PCT_PAID_LT_50PCT"
        else:
            best_b_id, best_b = min(
                sub_results.items(),
                key=lambda kv: (kv[1]["ruin_pct"], kv[1]["uncond_med_pay1_cap730_days"]),
            )
            b_status = "NO_POLICY_MEETS_10PCT_RUIN_LOWEST_RUIN_SHOWN"

    return {
        "profile_a_npv_wealth_safe5pct": {
            "status": a_status,
            "winner_policy": best_a_id,
            "ruin_pct": best_a["ruin_pct"],
            "ev_npv_24m_usd": best_a.get("ev_npv_24m_usd", 0.0),
            "ev_npv_24m_vnd_tr": best_a["ev_npv_24m_vnd_tr"],
            "ev_npv_36m_vnd_tr": best_a["ev_npv_36m_vnd_tr"],
            "med_npv_24m_usd": best_a.get("med_npv_24m_usd", 0.0),
            "med_npv_24m_vnd_tr": best_a["med_npv_24m_vnd_tr"],
            "p_npv24_le_0_pct": best_a.get("p_npv24_le_0_pct", 0.0),
            "uncond_med_pay1_days": best_a["uncond_med_pay1_cap730_days"],
            "funded_dry_months_pct": best_a["funded_dry_months_pct"],
        },
        "profile_b_fast_cashflow_safe10pct": {
            "status": b_status,
            "winner_policy": best_b_id,
            "ruin_pct": best_b["ruin_pct"],
            "paid_any_pct": best_b["paid_any_pct"],
            "ev_npv_24m_usd": best_b.get("ev_npv_24m_usd", 0.0),
            "ev_npv_24m_vnd_tr": best_b["ev_npv_24m_vnd_tr"],
            "ev_npv_36m_vnd_tr": best_b["ev_npv_36m_vnd_tr"],
            "med_npv_24m_usd": best_b.get("med_npv_24m_usd", 0.0),
            "med_npv_24m_vnd_tr": best_b.get("med_npv_24m_vnd_tr", 0.0),
            "p_npv24_le_0_pct": best_b.get("p_npv24_le_0_pct", 0.0),
            "uncond_med_pay1_days": best_b["uncond_med_pay1_cap730_days"],
            "cond_med_pay1_days": best_b["cond_med_pay1_cal_days"],
            "funded_dry_months_pct": best_b["funded_dry_months_pct"],
        },
    }


def select_dual_objective_winners(policy_results: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Select Profile A & Profile B winners across ALL policies AND strictly within FTMO-only."""
    all_w = _pick_pair_winners(policy_results)
    ftmo_only = {k: v for k, v in policy_results.items() if not k.startswith("P5")}
    if ftmo_only:
        all_w["ftmo_only_verified_execution"] = _pick_pair_winners(ftmo_only)
    return all_w

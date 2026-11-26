"""Study orchestrator Sections 4–5 (friction/NPV/fee sensitivity & dual-horizon sale calendar)."""

from __future__ import annotations

from typing import Any

import numpy as np

from quant_factory.capital_optimizer.catalog import _daily_dd_anchor_code, get_program_tier
from quant_factory.capital_optimizer.constants import (
    DD_STATIC,
    DEFAULT_DISCOUNT_RATE,
    DISCOUNT_RATES_ANNUAL,
    FRICTION_LEVELS,
    VARIANT_PHASE_CONFIGS,
)
from quant_factory.capital_optimizer.policy_kernel import (
    _pack_templates_for_numba,
    _simulate_capital_policy_numba,
)
from quant_factory.capital_optimizer.promo_sweep import solve_max_wait_days_worth_it
from quant_factory.capital_optimizer.replay_cache import ExactTierReplayCache
from quant_factory.capital_optimizer.simulator import _simulate_single_ticket_rules_numba
from quant_factory.capital_optimizer.summaries import (
    summarize_capital_policy_mc,
    summarize_single_ticket_mc,
)


def run_friction_npv_fee_and_sale_sections(
    *,
    catalog: dict[str, Any],
    ftmo_std: dict[str, Any] | None,
    cache: ExactTierReplayCache,
    idx_single: np.ndarray,
    idx_grid: np.ndarray,
    horizon_days: int,
    primary_var: str,
    use_promo_prices: bool,
    usd_vnd: float,
    card_fx_fee: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Run Section 4 (friction/NPV/fee sensitivity) and Section 5 (dual-horizon sale calendar)."""
    npv_discount_sensitivity: list[dict[str, Any]] = []
    friction_lifecycle_10k_100k: list[dict[str, Any]] = []
    fee_accounting_sensitivity: list[dict[str, Any]] = []
    sale_decision_table: list[dict[str, Any]] = []

    if ftmo_std is None:
        return (
            friction_lifecycle_10k_100k,
            npv_discount_sensitivity,
            fee_accounting_sensitivity,
            sale_decision_table,
        )

    vc = VARIANT_PHASE_CONFIGS[primary_var]
    for cap in (10_000.0, 100_000.0):
        _, merged = get_program_tier(catalog, ftmo_std["program_id"], cap)
        fee_orig = float(merged["orig_usd"])
        fee_day0 = float(merged["active_promo_usd"] if use_promo_prices else fee_orig)
        payout_wd = float(merged.get("payout_withdrawal_fee_pct", merged.get("withdrawal_fee_pct", 0.015)))
        ref_wd_default = float(merged.get("refund_withdrawal_fee_pct", 0.0))
        anchor_ftmo = _daily_dd_anchor_code(merged.get("daily_dd_anchor", "initial_balance"))
        for fmult in FRICTION_LEVELS:
            st_arrs = cache.build_stage_tuple(
                capital_usd=cap,
                p1_mult=vc["p1_mult"],
                p1_lock_mult=vc["p1_lock_mult"],
                p2_mult=vc["p2_mult"],
                p2_lock_mult=vc["p2_lock_mult"],
                funded_mult=vc["funded_mult"],
                amber_mult=vc["amber_mult"],
                red_mult=vc["red_mult"],
                p1_symcap=vc["p1_symcap_pct"],
                p2_symcap=vc["p2_symcap_pct"],
                fn_symcap=vc["funded_symcap_pct"],
                profile_mode="Standard",
                p1_news=vc["p1_news_guard"],
                p2_news=vc["p2_news_guard"],
                fn_news=vc["funded_news_guard"],
                friction_mult=fmult,
            )
            base_kw: dict[str, Any] = {
                "steps": 2,
                "cap": cap,
                "fee_day0_usd": fee_day0,
                "fee_regular_usd": fee_orig,
                "card_fx_fee_pct": card_fx_fee,
                "withdrawal_fee_pct": payout_wd,
                "fee_refund_pct": float(merged["fee_refund_pct"]),
                "p1_target": float(merged["p1_target_pct"]),
                "p2_target": float(merged["p2_target_pct"]),
                "daily_lim": float(merged["dd_daily_pct"]),
                "max_dd_lim": float(merged["dd_max_pct"]),
                "dd_type": DD_STATIC,
                "trail_lock_initial": False,
                "best_day_cap_pct": 0.0,
                "min_days": int(merged["min_trading_days"]),
                "min_prof_days": 0,
                "min_prof_day_pct": 0.0,
                "profit_split": float(merged["profit_split_pct"]),
                "payout_cycle_days": int(merged["payout_cycle_trading_days"]),
                "min_payout_usd": float(merged["min_payout_usd"]),
                "strict_lt_breach": True,
                "p1_lock_trigger": vc["p1_lock_trigger"],
                "p2_lock_trigger": vc["p2_lock_trigger"],
                "amber_dd": vc["amber_dd"],
                "red_dd": vc["red_dd"],
                "p1_ea_stop": vc["p1_ea_daily_stop"],
                "p2_ea_stop": vc["p2_ea_daily_stop"],
                "fn_ea_stop": vc["funded_ea_daily_stop"],
                "start_day_offset": 0,
                "max_retries": 0,
                "daily_dd_anchor_mode": anchor_ftmo,
            }
            res_f = _simulate_single_ticket_rules_numba(
                idx_single,
                *st_arrs,
                discount_rate_annual=DEFAULT_DISCOUNT_RATE,
                refund_withdrawal_fee_pct=ref_wd_default,
                **base_kw,
            )
            summ_f = summarize_single_ticket_mc(
                res_f,
                fee_usd=fee_day0,
                fee_regular_usd=fee_orig,
                card_fx_fee_pct=card_fx_fee,
                usd_vnd_rate=usd_vnd,
                horizon_days=horizon_days,
                refund_withdrawal_fee_pct=ref_wd_default,
            )
            friction_lifecycle_10k_100k.append({
                "capital_usd": cap,
                "variant": primary_var,
                "friction_x": fmult,
                **summ_f,
            })
            if abs(fmult - 1.00) < 1e-9:
                for r_rate in (0.0, *DISCOUNT_RATES_ANNUAL):
                    res_r = _simulate_single_ticket_rules_numba(
                        idx_single,
                        *st_arrs,
                        discount_rate_annual=r_rate,
                        refund_withdrawal_fee_pct=ref_wd_default,
                        **base_kw,
                    )
                    npv_discount_sensitivity.append({
                        "capital_usd": cap,
                        "variant": primary_var,
                        "discount_rate_pct": round(r_rate * 100.0, 1),
                        "ev_npv_24m_usd": round(float(np.mean(res_r[9])), 2),
                        "ev_npv_24m_vnd_tr": round(float(np.mean(res_r[9])) * usd_vnd / 1_000_000.0, 2),
                        "ev_npv_36m_usd": round(float(np.mean(res_r[10])), 2),
                        "ev_npv_36m_vnd_tr": round(float(np.mean(res_r[10])) * usd_vnd / 1_000_000.0, 2),
                    })
            if fmult in (1.00, 1.50):
                res_rail = _simulate_single_ticket_rules_numba(
                    idx_single,
                    *st_arrs,
                    discount_rate_annual=DEFAULT_DISCOUNT_RATE,
                    refund_withdrawal_fee_pct=0.015,
                    **base_kw,
                )
                npv_card = float(np.mean(res_f[9]))
                npv_rail = float(np.mean(res_rail[9]))
                fee_accounting_sensitivity.append({
                    "capital_usd": cap,
                    "variant": primary_var,
                    "friction_x": fmult,
                    "card_fx_buy_fee_pct": round(card_fx_fee * 100.0, 2),
                    "payout_withdrawal_fee_pct": round(payout_wd * 100.0, 2),
                    "refund_card_0pct_npv24_usd": round(npv_card, 2),
                    "refund_rail_1_5pct_npv24_usd": round(npv_rail, 2),
                    "delta_card_minus_rail_usd": round(npv_card - npv_rail, 2),
                    "delta_card_minus_rail_vnd_tr": round((npv_card - npv_rail) * usd_vnd / 1_000_000.0, 3),
                })

    for cap in (10_000.0, 50_000.0, 100_000.0):
        _, merged = get_program_tier(catalog, ftmo_std["program_id"], cap)
        orig_fee = float(merged["orig_usd"])
        bf_disc = float(merged["active_promo_pct"])
        for fmult in (1.00, 1.50):
            st_arrs = cache.build_stage_tuple(
                capital_usd=cap,
                p1_mult=vc["p1_mult"],
                p1_lock_mult=vc["p1_lock_mult"],
                p2_mult=vc["p2_mult"],
                p2_lock_mult=vc["p2_lock_mult"],
                funded_mult=vc["funded_mult"],
                amber_mult=vc["amber_mult"],
                red_mult=vc["red_mult"],
                p1_symcap=vc["p1_symcap_pct"],
                p2_symcap=vc["p2_symcap_pct"],
                fn_symcap=vc["funded_symcap_pct"],
                profile_mode="Standard",
                p1_news=vc["p1_news_guard"],
                p2_news=vc["p2_news_guard"],
                fn_news=vc["funded_news_guard"],
                friction_mult=fmult,
            )
            for retries_m, retry_lbl in ((0, "SINGLE_TICKET_0_RETRY"), (2, "RETRY_UP_TO_2_REGULAR_PRICE")):
                for z_disc in (0.10, 0.20, 0.30):
                    sol24 = solve_max_wait_days_worth_it(
                        idx_grid,
                        st_arrs,
                        program_tier=merged,
                        orig_fee_usd=orig_fee,
                        active_discount_pct=0.0,
                        next_sale_discount_pct=z_disc,
                        card_fx_fee_pct=card_fx_fee,
                        discount_rate_annual=DEFAULT_DISCOUNT_RATE,
                        usd_vnd_rate=usd_vnd,
                        horizon_months=24,
                        max_search_days=180,
                        p1_lock_trigger=vc["p1_lock_trigger"],
                        p2_lock_trigger=vc["p2_lock_trigger"],
                        amber_dd=vc["amber_dd"],
                        red_dd=vc["red_dd"],
                        p1_ea_stop=vc["p1_ea_daily_stop"],
                        p2_ea_stop=vc["p2_ea_daily_stop"],
                        fn_ea_stop=vc["funded_ea_daily_stop"],
                        max_retries=retries_m,
                    )
                    sale_decision_table.append({
                        "scenario": "NON_PROMO_DAY_0PCT",
                        "retry_regime": retry_lbl,
                        "variant": primary_var,
                        "program_id": ftmo_std["program_id"],
                        "capital_usd": cap,
                        "friction_x": fmult,
                        "active_discount_pct": 0.0,
                        "target_sale_discount_pct": round(z_disc * 100.0, 0),
                        "upfront_saving_usd": round(orig_fee * z_disc * (1.0 + card_fx_fee), 2),
                        **sol24,
                    })
                sol_bf = solve_max_wait_days_worth_it(
                    idx_grid,
                    st_arrs,
                    program_tier=merged,
                    orig_fee_usd=orig_fee,
                    active_discount_pct=bf_disc,
                    next_sale_discount_pct=0.10,
                    card_fx_fee_pct=card_fx_fee,
                    discount_rate_annual=DEFAULT_DISCOUNT_RATE,
                    usd_vnd_rate=usd_vnd,
                    horizon_months=24,
                    max_search_days=180,
                    p1_lock_trigger=vc["p1_lock_trigger"],
                    p2_lock_trigger=vc["p2_lock_trigger"],
                    amber_dd=vc["amber_dd"],
                    red_dd=vc["red_dd"],
                    p1_ea_stop=vc["p1_ea_daily_stop"],
                    p2_ea_stop=vc["p2_ea_daily_stop"],
                    fn_ea_stop=vc["funded_ea_daily_stop"],
                    max_retries=retries_m,
                )
                sale_decision_table.append({
                    "scenario": "BLACK_FRIDAY_ACTIVE_TODAY",
                    "retry_regime": retry_lbl,
                    "variant": primary_var,
                    "program_id": ftmo_std["program_id"],
                    "capital_usd": cap,
                    "friction_x": fmult,
                    "active_discount_pct": round(bf_disc * 100.0, 0),
                    "target_sale_discount_pct": 10.0,
                    "upfront_saving_usd": 0.0,
                    **sol_bf,
                    "decision": "BUY_TODAY_BLACK_FRIDAY_DOMINATES",
                })

    return (
        friction_lifecycle_10k_100k,
        npv_discount_sensitivity,
        fee_accounting_sensitivity,
        sale_decision_table,
    )


def _run_sunk_cost_abort_study(
    *,
    catalog: dict[str, Any],
    ftmo_std: dict[str, Any],
    cache: ExactTierReplayCache,
    idx_grid: np.ndarray,
    hazard_0pct: np.ndarray,
    primary_var: str,
    use_promo_prices: bool,
    usd_vnd: float,
    card_fx_fee: float,
) -> list[dict[str, Any]]:
    vc = VARIANT_PHASE_CONFIGS[primary_var]
    out: list[dict[str, Any]] = []
    for adv_f in (1.75, 2.00):
        _, merged_50 = get_program_tier(catalog, ftmo_std["program_id"], 50_000.0)
        st_adv = cache.build_stage_tuple(
            capital_usd=50_000.0,
            p1_mult=vc["p1_mult"],
            p1_lock_mult=vc["p1_lock_mult"],
            p2_mult=vc["p2_mult"],
            p2_lock_mult=vc["p2_lock_mult"],
            funded_mult=vc["funded_mult"],
            amber_mult=vc["amber_mult"],
            red_mult=vc["red_mult"],
            p1_symcap=vc["p1_symcap_pct"],
            p2_symcap=vc["p2_symcap_pct"],
            fn_symcap=vc["funded_symcap_pct"],
            profile_mode="Standard",
            p1_news=vc["p1_news_guard"],
            p2_news=vc["p2_news_guard"],
            fn_news=vc["funded_news_guard"],
            friction_mult=adv_f,
        )
        fee_50_orig = float(merged_50["orig_usd"])
        fee_50_day0 = float(merged_50["active_promo_usd"] if use_promo_prices else fee_50_orig)
        tpl_adv = [{
            "firm_idx": 0,
            "steps": 2,
            "capital_usd": 50_000.0,
            "fee_day0_usd": fee_50_day0,
            "fee_regular_usd": fee_50_orig,
            "fee_refund_pct": 1.0,
            "payout_withdrawal_fee_pct": float(
                merged_50.get("payout_withdrawal_fee_pct", merged_50["withdrawal_fee_pct"])
            ),
            "refund_withdrawal_fee_pct": float(merged_50.get("refund_withdrawal_fee_pct", 0.0)),
            "p1_target_pct": 0.10,
            "p2_target_pct": 0.05,
            "dd_daily_pct": 0.05,
            "dd_max_pct": 0.10,
            "dd_type": "static",
            "daily_dd_anchor": str(merged_50.get("daily_dd_anchor", "initial_balance")),
            "best_day_cap_pct": 0.0,
            "min_trading_days": 4,
            "min_profitable_days": 0,
            "min_profitable_day_pct": 0.0,
            "profit_split_pct": 0.80,
            "payout_cycle_trading_days": 10,
            "min_payout_usd": 50.0,
            "p1_lock_trigger": vc["p1_lock_trigger"],
            "p2_lock_trigger": vc["p2_lock_trigger"],
            "amber_dd": vc["amber_dd"],
            "red_dd": vc["red_dd"],
            "p1_ea_stop": vc["p1_ea_daily_stop"],
            "p2_ea_stop": vc["p2_ea_daily_stop"],
            "fn_ea_stop": vc["funded_ea_daily_stop"],
            "stage_arrays": st_adv,
        }]
        packed_adv = _pack_templates_for_numba(tpl_adv)
        init_35 = (35.0 * 1_000_000.0) / usd_vnd
        adv_common: dict[str, Any] = {
            "policy_mode": 1,
            "ladder_tpls": np.array([0], dtype=np.int32),
            "max_slots": 1,
            "allow_downgrade": False,
            "upgrade_buf_mult": 2.5,
            "downgrade_buf_mult": 2.0,
            "init_bankroll_usd": init_35,
            "monthly_topup_usd": 0.0,
            "card_fx_fee_pct": card_fx_fee,
            "discount_rate_annual": DEFAULT_DISCOUNT_RATE,
            "own_book_overflow_mult": 0.0,
            "own_book_daily_ret": 0.0,
            "wait_for_top_rung_slot2": False,
        }
        r_blind = _simulate_capital_policy_numba(idx_grid, hazard_0pct, *packed_adv, abort_after_day=-1, **adv_common)
        r_abort = _simulate_capital_policy_numba(idx_grid, hazard_0pct, *packed_adv, abort_after_day=42, **adv_common)
        s_blind = summarize_capital_policy_mc(
            r_blind, usd_vnd_rate=usd_vnd, init_bankroll_vnd_tr=35.0, monthly_topup_vnd_tr=0.0
        )
        s_abort = summarize_capital_policy_mc(
            r_abort, usd_vnd_rate=usd_vnd, init_bankroll_vnd_tr=35.0, monthly_topup_vnd_tr=0.0
        )
        out.append({
            "adverse_friction_x": adv_f,
            "variant": primary_var,
            "blind_retry_chasing": s_blind,
            "live_friction_abort_day42": s_abort,
            "fees_saved_usd": round(s_blind["mean_fees_24m_usd"] - s_abort["mean_fees_24m_usd"], 1),
            "fees_saved_vnd_tr": round(
                (s_blind["mean_fees_24m_usd"] - s_abort["mean_fees_24m_usd"]) * usd_vnd / 1_000_000.0, 2
            ),
            "npv24_saved_vnd_tr": round(s_abort["ev_npv_24m_vnd_tr"] - s_blind["ev_npv_24m_vnd_tr"], 2),
        })
    return out

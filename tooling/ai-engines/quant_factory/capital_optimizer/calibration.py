"""Fair per-rule risk-multiplier calibration for tighter prop drawdown families."""

from __future__ import annotations

from typing import Any

import numpy as np

from quant_factory.capital_optimizer.catalog_normalize import _daily_dd_anchor_code, _dd_type_code
from quant_factory.capital_optimizer.constants import VARIANT_PHASE_CONFIGS
from quant_factory.capital_optimizer.replay_cache import ExactTierReplayCache
from quant_factory.capital_optimizer.simulator import _simulate_single_ticket_rules_numba
from quant_factory.capital_optimizer.summaries import summarize_single_ticket_mc


def calibrate_safe_multipliers_for_rule(
    cache: ExactTierReplayCache,
    idx_matrix: np.ndarray,
    *,
    program_tier: dict[str, Any],
    variant: str,
    friction_mult: float,
    card_fx_fee_pct: float,
    discount_rate_annual: float,
    usd_vnd_rate: float,
) -> dict[str, Any]:
    """Calibrate fair, safe P1/P2/Funded risk multipliers for each rule family (`2.5%`, `3%`, `4%`, `5%` DD)."""
    daily_lim = float(program_tier["dd_daily_pct"])
    max_dd = float(program_tier["dd_max_pct"])
    steps = int(program_tier["steps"])
    cap = float(program_tier["capital_usd"])
    fee = float(program_tier["active_promo_usd"] or program_tier["orig_usd"])
    prof_mode = str(program_tier.get("profile_mode", "Standard"))
    vc = VARIANT_PHASE_CONFIGS[variant]

    if steps == 2 and daily_lim >= 0.049 and max_dd >= 0.099:
        p1_news = bool(program_tier.get("news_restricted_eval", False)) or bool(vc["p1_news_guard"])
        p2_news = bool(program_tier.get("news_restricted_eval", False)) or bool(vc["p2_news_guard"])
        fn_news = bool(program_tier.get("news_restricted_funded", True)) or bool(vc["funded_news_guard"])
        return {
            "calibrated_reason": f"EXACT_{variant}_5PCT_10PCT_REGISTERED",
            "p1_mult": vc["p1_mult"],
            "p1_lock_trigger": vc["p1_lock_trigger"],
            "p1_lock_mult": vc["p1_lock_mult"],
            "p2_mult": vc["p2_mult"],
            "p2_lock_trigger": vc["p2_lock_trigger"],
            "p2_lock_mult": vc["p2_lock_mult"],
            "funded_mult": vc["funded_mult"],
            "amber_dd": vc["amber_dd"],
            "amber_mult": vc["amber_mult"],
            "red_dd": vc["red_dd"],
            "red_mult": vc["red_mult"],
            "p1_symcap": vc["p1_symcap_pct"],
            "p2_symcap": vc["p2_symcap_pct"],
            "fn_symcap": vc["funded_symcap_pct"],
            "p1_news": p1_news,
            "p2_news": p2_news,
            "fn_news": fn_news,
            "p1_ea_stop": vc["p1_ea_daily_stop"],
            "p2_ea_stop": vc["p2_ea_daily_stop"],
            "fn_ea_stop": vc["funded_ea_daily_stop"],
        }

    if daily_lim <= 0.026:
        grid = [
            (1.00, 1.00, 0.65),
            (1.25, 1.00, 0.75),
            (1.50, 1.00, 0.75),
            (1.75, 1.00, 0.85),
        ]
        ea_stop_eval = 0.0175
        ea_stop_fn = 0.0150
        amber_dd = 0.020
        red_dd = 0.040
        symcap_eval = 0.85
        symcap_fn = 0.75
    elif daily_lim <= 0.031:
        if steps == 0:
            grid = [
                (0.75, 0.75, 0.75),
                (1.00, 1.00, 1.00),
                (1.25, 1.25, 1.25),
                (1.50, 1.50, 1.50),
            ]
        else:
            grid = [
                (1.50, 1.00, 0.75),
                (1.75, 1.00, 0.85),
                (2.00, 1.00, 1.00),
                (2.25, 1.00, 1.00),
                (2.50, 1.00, 1.00),
                (2.75, 1.00, 1.00),
            ]
        ea_stop_eval = 0.021
        ea_stop_fn = 0.018
        amber_dd = 0.025
        red_dd = 0.045
        symcap_eval = 1.00
        symcap_fn = 0.85
    else:
        grid = [
            (2.25, 1.50, 0.75),
            (2.50, 1.75, 0.85),
            (2.75, 1.75, 0.85),
            (3.00, 2.00, 0.90),
        ]
        ea_stop_eval = 0.028
        ea_stop_fn = 0.022
        amber_dd = 0.025
        red_dd = 0.050
        symcap_eval = 1.25
        symcap_fn = 0.85

    p1_news = bool(program_tier.get("news_restricted_eval", False)) or bool(vc["p1_news_guard"])
    p2_news = bool(program_tier.get("news_restricted_eval", False)) or bool(vc["p2_news_guard"])
    fn_news = bool(program_tier.get("news_restricted_funded", True)) or bool(vc["funded_news_guard"])

    sweep_log: list[dict[str, Any]] = []
    best_cfg: dict[str, Any] | None = None
    best_score = -1e18

    sub_idx = idx_matrix[: min(1_500, len(idx_matrix))]
    fee_reg = float(program_tier.get("orig_usd") or fee)
    payout_wd = float(program_tier.get("payout_withdrawal_fee_pct", program_tier.get("withdrawal_fee_pct", 0.015)))
    for p1_m, p2_m, fn_m in grid:
        st_arrs = cache.build_stage_tuple(
            capital_usd=cap,
            p1_mult=p1_m,
            p1_lock_mult=round(p1_m * 0.55, 2),
            p2_mult=p2_m,
            p2_lock_mult=round(p2_m * 0.55, 2),
            funded_mult=fn_m,
            amber_mult=round(fn_m * 0.65, 2),
            red_mult=round(fn_m * 0.40, 2),
            p1_symcap=symcap_eval,
            p2_symcap=symcap_eval,
            fn_symcap=symcap_fn,
            profile_mode=prof_mode,
            p1_news=p1_news,
            p2_news=p2_news,
            fn_news=fn_news,
            friction_mult=friction_mult,
            steps=steps,
        )
        res = _simulate_single_ticket_rules_numba(
            sub_idx,
            *st_arrs,
            steps=steps,
            cap=cap,
            fee_day0_usd=fee,
            fee_regular_usd=fee_reg,
            card_fx_fee_pct=card_fx_fee_pct,
            withdrawal_fee_pct=payout_wd,
            fee_refund_pct=float(program_tier.get("fee_refund_pct", 0.0)),
            p1_target=float(program_tier.get("p1_target_pct", 0.10)),
            p2_target=float(program_tier.get("p2_target_pct", 0.0)),
            daily_lim=daily_lim,
            max_dd_lim=max_dd,
            dd_type=_dd_type_code(program_tier.get("dd_type", "static")),
            trail_lock_initial=bool(program_tier.get("trail_lock_at_initial", False)),
            best_day_cap_pct=float(program_tier.get("best_day_cap_pct", 0.0)),
            min_days=int(program_tier.get("min_trading_days", 0)),
            min_prof_days=int(program_tier.get("min_profitable_days", 0)),
            min_prof_day_pct=float(program_tier.get("min_profitable_day_pct", 0.0)),
            profit_split=float(program_tier.get("profit_split_pct", 0.90)),
            payout_cycle_days=int(program_tier.get("payout_cycle_trading_days", 10)),
            min_payout_usd=float(program_tier.get("min_payout_usd", 50.0)),
            strict_lt_breach=True,
            p1_lock_trigger=0.50,
            p2_lock_trigger=0.50,
            amber_dd=amber_dd,
            red_dd=red_dd,
            p1_ea_stop=ea_stop_eval,
            p2_ea_stop=ea_stop_eval,
            fn_ea_stop=ea_stop_fn,
            start_day_offset=0,
            discount_rate_annual=discount_rate_annual,
            max_retries=0,
            refund_payout_milestone=int(program_tier.get("refund_payout_milestone", 1)),
            payout_buffer_retention_pct=float(program_tier.get("payout_buffer_retention_pct", 0.0)),
            locks_at_initial_after_first_payout=bool(
                program_tier.get("locks_at_initial_after_first_payout", False)
            ),
            min_payout_profit_pct=float(program_tier.get("min_payout_profit_pct", 0.0)),
            funded_first_payout_min_prof_days=int(program_tier.get("funded_first_payout_min_prof_days", 0)),
            funded_first_payout_prof_pct=float(program_tier.get("funded_first_payout_prof_pct", 0.0)),
            daily_profit_cap_pct=float(program_tier.get("daily_profit_cap_pct", 0.0)),
            refund_withdrawal_fee_pct=float(program_tier.get("refund_withdrawal_fee_pct", 0.0)),
            daily_dd_anchor_mode=_daily_dd_anchor_code(program_tier.get("daily_dd_anchor", "initial_balance")),
        )
        summ = summarize_single_ticket_mc(
            res,
            fee_usd=fee,
            fee_regular_usd=fee_reg,
            card_fx_fee_pct=card_fx_fee_pct,
            usd_vnd_rate=usd_vnd_rate,
            horizon_days=sub_idx.shape[1],
            refund_withdrawal_fee_pct=float(program_tier.get("refund_withdrawal_fee_pct", 0.0)),
        )
        ev_npv = float(summ["ev_npv_24m_usd"])
        fn_br = float(summ["funded_12m_breach"]["breach_12m_pct"])
        d_br = float(summ["firm_hard_breach_daily_pct"])
        penalty = max(0.0, d_br - 15.0) * 40.0 + max(0.0, fn_br - 3.0) * 100.0
        score = ev_npv - penalty
        sweep_log.append({
            "p1_mult": p1_m,
            "p2_mult": p2_m,
            "funded_mult": fn_m,
            "ev_npv_24m_usd": ev_npv,
            "pass_24m_pct": summ["pass_24m_pct"],
            "daily_breach_pct": d_br,
            "funded_12m_breach_pct": fn_br,
        })
        if score > best_score:
            best_score = score
            best_cfg = {
                "calibrated_reason": f"AUTO_SWEPT_FAIR_SAFE_{int(daily_lim * 100)}PCT_DD",
                "p1_mult": p1_m,
                "p1_lock_trigger": 0.50,
                "p1_lock_mult": round(p1_m * 0.55, 2),
                "p2_mult": p2_m,
                "p2_lock_trigger": 0.50,
                "p2_lock_mult": round(p2_m * 0.55, 2),
                "funded_mult": fn_m,
                "amber_dd": amber_dd,
                "amber_mult": round(fn_m * 0.65, 2),
                "red_dd": red_dd,
                "red_mult": round(fn_m * 0.40, 2),
                "p1_symcap": symcap_eval,
                "p2_symcap": symcap_eval,
                "fn_symcap": symcap_fn,
                "p1_news": p1_news,
                "p2_news": p2_news,
                "fn_news": fn_news,
                "p1_ea_stop": ea_stop_eval,
                "p2_ea_stop": ea_stop_eval,
                "fn_ea_stop": ea_stop_fn,
                "calibration_sweep": sweep_log,
            }

    if best_cfg is None:
        raise RuntimeError("Empty calibration grid for rule multiplier sweep")
    return best_cfg

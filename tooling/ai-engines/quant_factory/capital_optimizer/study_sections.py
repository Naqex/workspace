"""Study orchestrator sections 1–5 (lot rounding, friction sweep, mode comparison, E8 audit, sale calendar)."""

from __future__ import annotations

from typing import Any

import numpy as np

from quant_factory.capital_optimizer.calibration import calibrate_safe_multipliers_for_rule
from quant_factory.capital_optimizer.catalog import (
    _daily_dd_anchor_code,
    _dd_rule_verification_tag,
    _dd_type_code,
    _find_program_by_hint,
    get_program_tier,
)
from quant_factory.capital_optimizer.constants import (
    CONTROL_VARIANT_DEFAULT,
    DEFAULT_DISCOUNT_RATE,
    E8_EXCLUDED_FIRM_IDS,
    FRICTION_SWEEP_WITH_BREAKEVEN,
    TIER_SIZES_USD,
)
from quant_factory.capital_optimizer.replay_cache import ExactTierReplayCache
from quant_factory.capital_optimizer.simulator import _simulate_single_ticket_rules_numba
from quant_factory.capital_optimizer.summaries import summarize_single_ticket_mc


def run_lot_rounding_and_friction_sections(
    cache: ExactTierReplayCache,
) -> tuple[dict[str, Any], list[dict[str, Any]], float | None]:
    """Run Section 1 (0.01-lot rounding audit across 5K..200K) and Section 2 (friction break-even sweep)."""
    lot_rounding_audit: dict[str, Any] = {
        "funded_1_0x": [],
        "funded_1_25x": [],
        "red_brake_0_4x": [],
        "p1_4_0x": [],
    }
    for label, mult, symcap in (
        ("funded_1_0x", 1.00, 1.00),
        ("funded_1_25x", 1.25, 1.25),
        ("red_brake_0_4x", 0.40, 1.00),
        ("p1_4_0x", 4.00, 1.75),
    ):
        rows_tier = []
        for cap in TIER_SIZES_USD:
            bal_met, _, _, _, _ = cache.get_exact_tier_stage(
                capital_usd=cap,
                mult=mult,
                symcap_pct=symcap,
                profile_mode="Standard",
                use_red_news=True,
                friction_mult=1.00,
            )
            rows_tier.append(bal_met)
        ref_ann_200k = rows_tier[-1]["ann_pct"]
        for r in rows_tier:
            r["lot_rounding_drag_vs_200k_pct"] = round(
                100.0 * (r["ann_pct"] - ref_ann_200k) / max(1e-6, abs(ref_ann_200k)), 2
            )
        lot_rounding_audit[label] = rows_tier

    lot_rounding_audit["sizing_parity_disclosure"] = {
        "tag": "DAILY_APPROX_PENDING_MT5_MODEL4_CROSSCHECK",
        "python_get_exact_tier_stage": (
            "Sizes each trade from fixed start-of-period capital (`initial * eff_risk`) and rejects the trade "
            "completely (`MARGIN` skip) if `lot * (margin_per_lot + comm_per_lot) > available_margin`."
        ),
        "mql5_ea_production": (
            "Sizes each trade from live `AccountInfoDouble(ACCOUNT_BALANCE) * risk * 0.95` and dynamically scales "
            "lot volume down to `85%` of free margin (`ACCOUNT_MARGIN_FREE`) rather than binary-rejecting on "
            "margin shortfall."
        ),
        "implication": (
            "Exact `5K/10K` lot-rounding drag percentages in Section 3 are `DAILY_APPROX` Python estimates and require "
            "MT5 `Model=4` real-tick cross-check across account tiers before quoting exact live EA drag."
        ),
    }

    friction_sweep_100k: list[dict[str, Any]] = []
    friction_breakeven_x: float | None = None
    prev_f: tuple[float, float] | None = None
    for fmult in FRICTION_SWEEP_WITH_BREAKEVEN:
        bal_met, _, _, _, _ = cache.get_exact_tier_stage(
            capital_usd=100_000.0,
            mult=1.00,
            symcap_pct=1.00,
            profile_mode="Standard",
            use_red_news=True,
            friction_mult=fmult,
        )
        friction_sweep_100k.append({"friction_x": fmult, **bal_met})
        if prev_f is not None and friction_breakeven_x is None:
            if prev_f[1] > 0.0 and bal_met["ann_pct"] <= 0.0:
                frac = prev_f[1] / max(1e-9, prev_f[1] - bal_met["ann_pct"])
                friction_breakeven_x = round(prev_f[0] + frac * (fmult - prev_f[0]), 2)
        prev_f = (fmult, bal_met["ann_pct"])

    return lot_rounding_audit, friction_sweep_100k, friction_breakeven_x


def run_mode_comparison_and_e8_section(
    *,
    catalog: dict[str, Any],
    cache: ExactTierReplayCache,
    idx_single: np.ndarray,
    idx_grid: np.ndarray,
    horizon_days: int,
    primary_var: str,
    use_promo_prices: bool,
    usd_vnd: float,
    card_fx_fee: float,
) -> tuple[
    list[dict[str, Any]],
    dict[str, Any],
    dict[tuple[str, float, str, float], dict[str, Any]],
    dict[tuple[str, float, float, str, str, str, float], dict[str, Any]],
]:
    """Run Section 3 (multi-firm/multi-mode comparison + E8 Pro Payout #1 buffer sensitivity)."""
    ftmo_std = _find_program_by_hint(
        catalog, lambda p: p["firm_id"] == "FTMO" and p["steps"] == 2 and p["profile_mode"] == "Standard"
    )
    ftmo_swg = _find_program_by_hint(
        catalog, lambda p: p["firm_id"] == "FTMO" and p["steps"] == 2 and p["profile_mode"] == "Swing"
    )
    ftmo_1st = _find_program_by_hint(catalog, lambda p: p["firm_id"] == "FTMO" and p["steps"] == 1)
    ftmo_ins = _find_program_by_hint(catalog, lambda p: p["firm_id"] == "FTMO" and p["steps"] == 0)
    other_progs = [p for p in catalog["programs"] if p["firm_id"] != "FTMO"]

    mode_comparison: list[dict[str, Any]] = []
    eval_targets: list[tuple[dict[str, Any], float, str, str]] = []
    default_pmode = "BF_DAY0" if use_promo_prices else "ALL_REGULAR"
    if ftmo_std:
        for cap in (10_000.0, 25_000.0, 50_000.0, 100_000.0, 200_000.0):
            eval_targets.append((ftmo_std, cap, primary_var, default_pmode))
        for cap in (10_000.0, 100_000.0):
            eval_targets.append((ftmo_std, cap, CONTROL_VARIANT_DEFAULT, default_pmode))
        eval_targets.append((ftmo_std, 100_000.0, "C10", default_pmode))
        if use_promo_prices:
            for cap in (10_000.0, 50_000.0, 100_000.0, 200_000.0):
                eval_targets.append((ftmo_std, cap, primary_var, "ALL_REGULAR"))
    if ftmo_swg:
        for cap in (10_000.0, 25_000.0):
            eval_targets.append((ftmo_swg, cap, primary_var, "ALL_REGULAR"))
    if ftmo_1st:
        for cap in (10_000.0, 50_000.0, 100_000.0):
            eval_targets.append((ftmo_1st, cap, primary_var, default_pmode))
    if ftmo_ins:
        for cap in (5_000.0, 10_000.0, 50_000.0, 100_000.0):
            eval_targets.append((ftmo_ins, cap, primary_var, default_pmode))
    for op in other_progs:
        avail_caps = sorted(
            float(t["capital_usd"])
            for t in op["tiers"]
            if t.get("available_vn", True) and float(t.get("orig_usd", 0.0)) > 0.0
        )
        picked_caps: list[float] = []
        for target_c in (5_000.0, 10_000.0, 20_000.0, 50_000.0, 60_000.0, 100_000.0):
            if target_c in avail_caps and target_c not in picked_caps:
                picked_caps.append(target_c)
        if not picked_caps and avail_caps:
            picked_caps = avail_caps[:3]
        for cap in picked_caps:
            eval_targets.append((op, cap, primary_var, default_pmode))

    calibrated_cache: dict[tuple[str, float, str, float], dict[str, Any]] = {}
    rule_family_cal_cache: dict[tuple[str, float, float, str, str, str, float], dict[str, Any]] = {}
    for prog, cap, var_name, pricing_mode in eval_targets:
        try:
            _, merged = get_program_tier(catalog, prog["program_id"], cap)
        except KeyError:
            continue
        if not merged.get("available_vn", True):
            continue
        fee_orig = float(merged["orig_usd"])
        fee_day0 = float(merged["active_promo_usd"]) if pricing_mode == "BF_DAY0" else fee_orig
        if fee_day0 <= 0.0 or fee_orig <= 0.0:
            continue
        ref_wd_fee = float(merged.get("refund_withdrawal_fee_pct", 0.0))
        payout_wd_fee = float(merged.get("payout_withdrawal_fee_pct", merged.get("withdrawal_fee_pct", 0.015)))
        anchor_mode = _daily_dd_anchor_code(merged.get("daily_dd_anchor", "initial_balance"))

        for fmult in (1.00, 1.50):
            rf_key = (
                prog["program_id"],
                round(float(merged["dd_daily_pct"]), 4),
                round(float(merged["dd_max_pct"]), 4),
                str(merged["dd_type"]),
                str(merged.get("daily_dd_anchor", "initial_balance")),
                var_name,
                fmult,
            )
            cal = rule_family_cal_cache.get(rf_key)
            if cal is None:
                cal = calibrate_safe_multipliers_for_rule(
                    cache,
                    idx_grid,
                    program_tier=merged,
                    variant=var_name,
                    friction_mult=fmult,
                    card_fx_fee_pct=card_fx_fee,
                    discount_rate_annual=DEFAULT_DISCOUNT_RATE,
                    usd_vnd_rate=usd_vnd,
                )
                rule_family_cal_cache[rf_key] = cal
            calibrated_cache[(prog["program_id"], cap, var_name, fmult)] = cal
            st_arrs = cache.build_stage_tuple(
                capital_usd=cap,
                p1_mult=cal["p1_mult"],
                p1_lock_mult=cal["p1_lock_mult"],
                p2_mult=cal["p2_mult"],
                p2_lock_mult=cal["p2_lock_mult"],
                funded_mult=cal["funded_mult"],
                amber_mult=cal["amber_mult"],
                red_mult=cal["red_mult"],
                p1_symcap=cal["p1_symcap"],
                p2_symcap=cal["p2_symcap"],
                fn_symcap=cal["fn_symcap"],
                profile_mode=str(merged["profile_mode"]),
                p1_news=cal["p1_news"],
                p2_news=cal["p2_news"],
                fn_news=cal["fn_news"],
                friction_mult=fmult,
                steps=int(merged["steps"]),
            )
            res0 = _simulate_single_ticket_rules_numba(
                idx_single,
                *st_arrs,
                steps=int(merged["steps"]),
                cap=cap,
                fee_day0_usd=fee_day0,
                fee_regular_usd=fee_orig,
                card_fx_fee_pct=card_fx_fee,
                withdrawal_fee_pct=payout_wd_fee,
                fee_refund_pct=float(merged.get("fee_refund_pct", 0.0)),
                p1_target=float(merged.get("p1_target_pct", 0.10)),
                p2_target=float(merged.get("p2_target_pct", 0.0)),
                daily_lim=float(merged.get("dd_daily_pct", 0.05)),
                max_dd_lim=float(merged.get("dd_max_pct", 0.10)),
                dd_type=_dd_type_code(merged.get("dd_type", "static")),
                trail_lock_initial=bool(merged.get("trail_lock_at_initial", False)),
                best_day_cap_pct=float(merged.get("best_day_cap_pct", 0.0)),
                min_days=int(merged.get("min_trading_days", 0)),
                min_prof_days=int(merged.get("min_profitable_days", 0)),
                min_prof_day_pct=float(merged.get("min_profitable_day_pct", 0.0)),
                profit_split=float(merged.get("profit_split_pct", 0.80)),
                payout_cycle_days=int(merged.get("payout_cycle_trading_days", 10)),
                min_payout_usd=float(merged.get("min_payout_usd", 50.0)),
                strict_lt_breach=True,
                p1_lock_trigger=cal["p1_lock_trigger"],
                p2_lock_trigger=cal["p2_lock_trigger"],
                amber_dd=cal["amber_dd"],
                red_dd=cal["red_dd"],
                p1_ea_stop=cal["p1_ea_stop"],
                p2_ea_stop=cal["p2_ea_stop"],
                fn_ea_stop=cal["fn_ea_stop"],
                start_day_offset=0,
                discount_rate_annual=DEFAULT_DISCOUNT_RATE,
                max_retries=0,
                refund_payout_milestone=int(merged.get("refund_payout_milestone", 1)),
                payout_buffer_retention_pct=float(merged.get("payout_buffer_retention_pct", 0.0)),
                locks_at_initial_after_first_payout=bool(
                    merged.get("locks_at_initial_after_first_payout", False)
                ),
                min_payout_profit_pct=float(merged.get("min_payout_profit_pct", 0.0)),
                funded_first_payout_min_prof_days=int(merged.get("funded_first_payout_min_prof_days", 0)),
                funded_first_payout_prof_pct=float(merged.get("funded_first_payout_prof_pct", 0.0)),
                daily_profit_cap_pct=float(merged.get("daily_profit_cap_pct", 0.0)),
                refund_withdrawal_fee_pct=ref_wd_fee,
                daily_dd_anchor_mode=anchor_mode,
            )
            summ = summarize_single_ticket_mc(
                res0,
                fee_usd=fee_day0,
                fee_regular_usd=fee_orig,
                card_fx_fee_pct=card_fx_fee,
                usd_vnd_rate=usd_vnd,
                horizon_days=horizon_days,
                refund_withdrawal_fee_pct=ref_wd_fee,
            )
            mode_comparison.append({
                "program_id": prog["program_id"],
                "firm_id": prog["firm_id"],
                "firm_name": prog["firm_name"],
                "mode_name": prog["mode_name"],
                "execution_evidence_tag": merged["execution_evidence_tag"],
                "dd_rule_verification_tag": merged.get(
                    "dd_rule_verification_tag",
                    _dd_rule_verification_tag(
                        prog["firm_id"],
                        str(merged.get("daily_dd_anchor_raw", "")),
                        str(merged.get("daily_dd_anchor", "initial_balance")),
                    ),
                ),
                "dd_rule_verification_note": merged.get("dd_rule_verification_note", ""),
                "variant": var_name,
                "pricing_mode": (
                    "BF_DAY0_PLUS_REGULAR_RETRIES"
                    if (pricing_mode == "BF_DAY0" and fee_day0 < fee_orig - 1e-6)
                    else "ALL_REGULAR"
                ),
                "capital_usd": cap,
                "friction_x": fmult,
                "orig_usd": fee_orig,
                "promo_usd": fee_day0,
                "fee_ratio_pct": round(100.0 * fee_day0 / cap, 4),
                "dd_daily_pct": round(float(merged["dd_daily_pct"]) * 100.0, 1),
                "dd_max_pct": round(float(merged["dd_max_pct"]) * 100.0, 1),
                "dd_type": merged["dd_type"],
                "daily_dd_anchor": merged.get("daily_dd_anchor", "initial_balance"),
                "daily_dd_anchor_raw": merged.get("daily_dd_anchor_raw", "initial_balance"),
                "payout_withdrawal_fee_pct": round(payout_wd_fee * 100.0, 2),
                "refund_withdrawal_fee_pct": round(ref_wd_fee * 100.0, 2),
                "best_day_cap_pct": round(float(merged.get("best_day_cap_pct", 0.0)) * 100.0, 1),
                "calibrated_mults": {
                    "p1": cal["p1_mult"],
                    "p2": cal["p2_mult"],
                    "funded": cal["funded_mult"],
                    "reason": cal["calibrated_reason"],
                },
                "single_ticket_zero_retry": summ,
            })

    e8_pro_buffer_sensitivity: dict[str, Any] = {
        "excluded_from_p5_portfolios": True,
        "astra_r10_verified_reference": {
            "note": (
                "Astra Round 10 independently verified that even waiting for +8% or +10% profit before "
                "Payout #1 on E8 Pro still breaches 34.18% / 17.38% in 12m at 1.00x due to "
                "floor-lock-at-initial + 50% retention."
            ),
            "wait_8pct_breach_12m_pct": 34.18,
            "wait_10pct_breach_12m_pct": 17.38,
        },
        "mc_buffer_sweep_50k_1_00x": [],
    }
    e8_prog = _find_program_by_hint(catalog, lambda p: p["firm_id"] in E8_EXCLUDED_FIRM_IDS)
    if e8_prog is not None:
        _, m_e8 = get_program_tier(catalog, e8_prog["program_id"], 50_000.0)
        cal_e8 = calibrated_cache.get((e8_prog["program_id"], 50_000.0, primary_var, 1.00))
        if cal_e8 is not None:
            st_e8 = cache.build_stage_tuple(
                capital_usd=50_000.0,
                p1_mult=cal_e8["p1_mult"],
                p1_lock_mult=cal_e8["p1_lock_mult"],
                p2_mult=cal_e8["p2_mult"],
                p2_lock_mult=cal_e8["p2_lock_mult"],
                funded_mult=cal_e8["funded_mult"],
                amber_mult=cal_e8["amber_mult"],
                red_mult=cal_e8["red_mult"],
                p1_symcap=cal_e8["p1_symcap"],
                p2_symcap=cal_e8["p2_symcap"],
                fn_symcap=cal_e8["fn_symcap"],
                profile_mode=str(m_e8["profile_mode"]),
                p1_news=cal_e8["p1_news"],
                p2_news=cal_e8["p2_news"],
                fn_news=cal_e8["fn_news"],
                friction_mult=1.00,
                steps=int(m_e8["steps"]),
            )
            e8_fee0 = float(m_e8["active_promo_usd"] if use_promo_prices else m_e8["orig_usd"])
            e8_feereg = float(m_e8["orig_usd"])
            for wait_buf_pct in (0.01, 0.08, 0.10):
                res_e8b = _simulate_single_ticket_rules_numba(
                    idx_single,
                    *st_e8,
                    steps=int(m_e8["steps"]),
                    cap=50_000.0,
                    fee_day0_usd=e8_fee0,
                    fee_regular_usd=e8_feereg,
                    card_fx_fee_pct=card_fx_fee,
                    withdrawal_fee_pct=float(
                        m_e8.get("payout_withdrawal_fee_pct", m_e8.get("withdrawal_fee_pct", 0.02))
                    ),
                    fee_refund_pct=0.0,
                    p1_target=float(m_e8["p1_target_pct"]),
                    p2_target=0.0,
                    daily_lim=float(m_e8["dd_daily_pct"]),
                    max_dd_lim=float(m_e8["dd_max_pct"]),
                    dd_type=_dd_type_code(m_e8["dd_type"]),
                    trail_lock_initial=False,
                    best_day_cap_pct=0.0,
                    min_days=0,
                    min_prof_days=0,
                    min_prof_day_pct=0.0,
                    profit_split=float(m_e8["profit_split_pct"]),
                    payout_cycle_days=int(m_e8["payout_cycle_trading_days"]),
                    min_payout_usd=float(m_e8["min_payout_usd"]),
                    strict_lt_breach=True,
                    p1_lock_trigger=cal_e8["p1_lock_trigger"],
                    p2_lock_trigger=cal_e8["p2_lock_trigger"],
                    amber_dd=cal_e8["amber_dd"],
                    red_dd=cal_e8["red_dd"],
                    p1_ea_stop=cal_e8["p1_ea_stop"],
                    p2_ea_stop=cal_e8["p2_ea_stop"],
                    fn_ea_stop=cal_e8["fn_ea_stop"],
                    start_day_offset=0,
                    discount_rate_annual=DEFAULT_DISCOUNT_RATE,
                    max_retries=0,
                    refund_payout_milestone=0,
                    payout_buffer_retention_pct=float(m_e8.get("payout_buffer_retention_pct", 0.50)),
                    locks_at_initial_after_first_payout=True,
                    min_payout_profit_pct=float(m_e8.get("min_payout_profit_pct", 0.01)),
                    daily_profit_cap_pct=float(m_e8.get("daily_profit_cap_pct", 0.02)),
                    refund_withdrawal_fee_pct=0.0,
                    daily_dd_anchor_mode=_daily_dd_anchor_code(m_e8.get("daily_dd_anchor", "initial_balance")),
                    funded_first_payout_min_profit_pct=wait_buf_pct,
                )
                summ_e8b = summarize_single_ticket_mc(
                    res_e8b,
                    fee_usd=e8_fee0,
                    fee_regular_usd=e8_feereg,
                    card_fx_fee_pct=card_fx_fee,
                    usd_vnd_rate=usd_vnd,
                    horizon_days=horizon_days,
                )
                e8_pro_buffer_sensitivity["mc_buffer_sweep_50k_1_00x"].append({
                    "first_payout_wait_profit_pct": round(wait_buf_pct * 100.0, 1),
                    "retained_cushion_after_p1_pct": round(wait_buf_pct * 50.0, 2),
                    "funded_12m_breach_pct": summ_e8b["funded_12m_breach"]["breach_12m_pct"],
                    "funded_12m_wilson_95_upper_pct": summ_e8b["funded_12m_breach"]["wilson_95_upper_pct"],
                    "cond_med_pay1_cal_days": summ_e8b["cond_med_pay1_cal_days"],
                    "ev_npv_24m_vnd_tr": summ_e8b["ev_npv_24m_vnd_tr"],
                    "ev_per_fee_npv24": summ_e8b["ev_per_fee_npv24"],
                })

    return mode_comparison, e8_pro_buffer_sensitivity, calibrated_cache, rule_family_cal_cache

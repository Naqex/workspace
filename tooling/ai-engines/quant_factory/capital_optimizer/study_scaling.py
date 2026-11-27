"""Study orchestrator Section 6: multi-slot, multi-firm Pareto grid, H2H, hazard & abort studies."""

from __future__ import annotations

from typing import Any

import numpy as np

from quant_factory.capital_optimizer.calibration import calibrate_safe_multipliers_for_rule
from quant_factory.capital_optimizer.catalog import _pick_tier_near, get_program_tier
from quant_factory.capital_optimizer.constants import (
    BANKROLL_GRID_VND_TR,
    DEFAULT_DISCOUNT_RATE,
    E8_EXCLUDED_FIRM_IDS,
    TOPUP_GRID_VND_TR,
)
from quant_factory.capital_optimizer.policy_kernel import (
    _pack_templates_for_numba,
    _simulate_capital_policy_numba,
)
from quant_factory.capital_optimizer.replay_cache import ExactTierReplayCache
from quant_factory.capital_optimizer.simulator import make_firm_hazard_days
from quant_factory.capital_optimizer.study_sensitivity import _run_sunk_cost_abort_study
from quant_factory.capital_optimizer.summaries import (
    select_dual_objective_winners,
    summarize_capital_policy_mc,
)


def run_capital_scaling_section(
    *,
    catalog: dict[str, Any],
    ftmo_std: dict[str, Any],
    other_progs: list[dict[str, Any]],
    cache: ExactTierReplayCache,
    calibrated_cache: dict[tuple[str, float, str, float], dict[str, Any]],
    rule_family_cal_cache: dict[tuple[str, float, float, str, str, str, float], dict[str, Any]],
    idx_single: np.ndarray,
    idx_grid: np.ndarray,
    horizon_days: int,
    primary_var: str,
    use_promo_prices: bool,
    usd_vnd: float,
    card_fx_fee: float,
    seed: int,
) -> tuple[
    list[str],
    dict[str, dict[str, Any]],
    dict[str, Any],
    dict[str, Any],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    pareto_grid: dict[str, dict[str, Any]] = {}
    head_to_head_2x100k_vs_1x200k: dict[str, Any] = {}
    all_regular_pricing_comparison: dict[str, Any] = {}
    cross_firm_hazard_study: list[dict[str, Any]] = []

    surviving_other_progs = [p for p in other_progs if p["firm_id"] not in E8_EXCLUDED_FIRM_IDS]
    firm_ids_order = ["FTMO"] + [p["firm_id"] for p in surviving_other_progs if p["firm_id"] != "FTMO"]
    firm_ids_unique: list[str] = []
    for fid in firm_ids_order:
        if fid not in firm_ids_unique:
            firm_ids_unique.append(fid)
    firm_to_idx = {fid: i for i, fid in enumerate(firm_ids_unique)}
    n_firms_total = max(3, len(firm_ids_unique))

    hazard_5pct = make_firm_hazard_days(len(idx_grid), n_firms_total, 0.05, horizon=horizon_days, seed=seed + 101)
    hazard_0pct = make_firm_hazard_days(len(idx_grid), n_firms_total, 0.00, horizon=horizon_days, seed=seed + 101)
    hazard_10pct = make_firm_hazard_days(len(idx_grid), n_firms_total, 0.10, horizon=horizon_days, seed=seed + 101)

    for fmult in (1.00, 1.50):
        fkey = f"{fmult:.2f}x"
        templates_bf: list[dict[str, Any]] = []
        templates_reg: list[dict[str, Any]] = []
        tpl_idx_map: dict[str, int] = {}

        def _add_template(
            key_name: str,
            prog: dict[str, Any],
            cap: float,
            *,
            _fmult: float = fmult,
            _tmap: dict[str, int] = tpl_idx_map,
            _tbf: list[dict[str, Any]] = templates_bf,
            _treg: list[dict[str, Any]] = templates_reg,
        ) -> int:
            if key_name in _tmap:
                return _tmap[key_name]
            _, merged = get_program_tier(catalog, prog["program_id"], cap)
            cal = calibrated_cache.get((prog["program_id"], cap, primary_var, _fmult))
            if cal is None:
                rf_k = (
                    prog["program_id"],
                    round(float(merged["dd_daily_pct"]), 4),
                    round(float(merged["dd_max_pct"]), 4),
                    str(merged["dd_type"]),
                    str(merged.get("daily_dd_anchor", "initial_balance")),
                    primary_var,
                    _fmult,
                )
                cal = rule_family_cal_cache.get(rf_k)
            if cal is None:
                cal = calibrate_safe_multipliers_for_rule(
                    cache,
                    idx_grid,
                    program_tier=merged,
                    variant=primary_var,
                    friction_mult=_fmult,
                    card_fx_fee_pct=card_fx_fee,
                    discount_rate_annual=DEFAULT_DISCOUNT_RATE,
                    usd_vnd_rate=usd_vnd,
                )
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
                friction_mult=_fmult,
                steps=int(merged["steps"]),
            )
            fee_orig = float(merged["orig_usd"])
            fee_day0 = float(merged["active_promo_usd"] if use_promo_prices else fee_orig)
            payout_wd = float(merged.get("payout_withdrawal_fee_pct", merged.get("withdrawal_fee_pct", 0.015)))
            ref_wd = float(merged.get("refund_withdrawal_fee_pct", 0.0))
            base_dict = {
                "key": key_name,
                "firm_idx": firm_to_idx.get(prog["firm_id"], 0),
                "firm_id": prog["firm_id"],
                "program_id": prog["program_id"],
                "execution_evidence_tag": merged["execution_evidence_tag"],
                "steps": int(merged["steps"]),
                "capital_usd": cap,
                "fee_day0_usd": fee_day0,
                "fee_regular_usd": fee_orig,
                "fee_refund_pct": float(merged.get("fee_refund_pct", 0.0)),
                "payout_withdrawal_fee_pct": payout_wd,
                "withdrawal_fee_pct": payout_wd,
                "refund_withdrawal_fee_pct": ref_wd,
                "p1_target_pct": float(merged.get("p1_target_pct", 0.10)),
                "p2_target_pct": float(merged.get("p2_target_pct", 0.0)),
                "dd_daily_pct": float(merged.get("dd_daily_pct", 0.05)),
                "dd_max_pct": float(merged.get("dd_max_pct", 0.10)),
                "dd_type": str(merged.get("dd_type", "static")),
                "daily_dd_anchor": str(merged.get("daily_dd_anchor", "initial_balance")),
                "best_day_cap_pct": float(merged.get("best_day_cap_pct", 0.0)),
                "min_trading_days": int(merged.get("min_trading_days", 4)),
                "min_profitable_days": int(merged.get("min_profitable_days", 0)),
                "min_profitable_day_pct": float(merged.get("min_profitable_day_pct", 0.0)),
                "profit_split_pct": float(merged.get("profit_split_pct", 0.80)),
                "payout_cycle_trading_days": int(merged.get("payout_cycle_trading_days", 10)),
                "min_payout_usd": float(merged.get("min_payout_usd", 50.0)),
                "p1_lock_trigger": float(cal["p1_lock_trigger"]),
                "p2_lock_trigger": float(cal["p2_lock_trigger"]),
                "amber_dd": float(cal["amber_dd"]),
                "red_dd": float(cal["red_dd"]),
                "p1_ea_stop": float(cal["p1_ea_stop"]),
                "p2_ea_stop": float(cal["p2_ea_stop"]),
                "fn_ea_stop": float(cal["fn_ea_stop"]),
                "refund_payout_milestone": int(merged.get("refund_payout_milestone", 1)),
                "payout_buffer_retention_pct": float(merged.get("payout_buffer_retention_pct", 0.0)),
                "locks_at_initial_after_first_payout": bool(
                    merged.get("locks_at_initial_after_first_payout", False)
                ),
                "min_payout_profit_pct": float(merged.get("min_payout_profit_pct", 0.0)),
                "daily_profit_cap_pct": float(merged.get("daily_profit_cap_pct", 0.0)),
                "funded_first_payout_min_prof_days": int(merged.get("funded_first_payout_min_prof_days", 0)),
                "funded_first_payout_prof_pct": float(merged.get("funded_first_payout_prof_pct", 0.0)),
                "stage_arrays": st_arrs,
            }
            idx = len(_tbf)
            _tbf.append(base_dict)
            reg_dict = dict(base_dict)
            reg_dict["fee_day0_usd"] = fee_orig
            _treg.append(reg_dict)
            _tmap[key_name] = idx
            return idx

        t_10k = _add_template("FTMO_10K", ftmo_std, 10_000.0)
        t_25k = _add_template("FTMO_25K", ftmo_std, 25_000.0)
        t_50k = _add_template("FTMO_50K", ftmo_std, 50_000.0)
        t_100k = _add_template("FTMO_100K", ftmo_std, 100_000.0)
        t_200k = _add_template("FTMO_200K", ftmo_std, 200_000.0)

        cross_tpls_small: list[int] = [t_10k]
        cross_tpls_big: list[int] = [t_100k]
        seen_other_firms: set[str] = set()
        ordered_other = sorted(
            surviving_other_progs,
            key=lambda p: (
                0 if "THE5ERS" in p["firm_id"] else 1,
                0 if "CLASSIC" in p["program_id"] else 1,
                p["firm_id"],
            ),
        )
        for op in ordered_other:
            if op["firm_id"] in seen_other_firms or op["firm_id"] in E8_EXCLUDED_FIRM_IDS:
                continue
            seen_other_firms.add(op["firm_id"])
            try:
                small_m = _pick_tier_near(op, 10_000.0)
                big_m = _pick_tier_near(op, 50_000.0)
                cross_tpls_small.append(_add_template(f"{op['firm_id']}_SMALL", op, float(small_m["capital_usd"])))
                cross_tpls_big.append(_add_template(f"{op['firm_id']}_BIG", op, float(big_m["capital_usd"])))
            except ValueError:
                continue

        packed = _pack_templates_for_numba(templates_bf)
        packed_reg = _pack_templates_for_numba(templates_reg)

        policies_spec: dict[str, tuple[int, np.ndarray, int, bool, float, float, bool]] = {
            "P1_REPEAT_10K": (0, np.array([t_10k], dtype=np.int32), 2, False, 3.0, 2.0, False),
            "P2_STEP_BY_STEP": (0, np.array([t_10k, t_25k, t_50k, t_100k], dtype=np.int32), 2, False, 2.75, 2.0, False),
            "P3_SMART_SKIP_DOWNGRADE": (0, np.array([t_10k, t_50k, t_100k], dtype=np.int32), 2, True, 2.75, 2.0, False),
            "P4A_DIRECT_50K": (1, np.array([t_50k, t_100k], dtype=np.int32), 2, False, 2.75, 2.0, False),
            "P4A_WAIT_FOR_100K": (1, np.array([t_50k, t_100k], dtype=np.int32), 2, False, 2.75, 2.0, True),
            "P4B_DIRECT_100K": (1, np.array([t_100k], dtype=np.int32), 2, False, 2.75, 2.0, False),
            "P4B_PARALLEL_2X100K": (3, np.array([t_100k], dtype=np.int32), 2, False, 2.00, 2.0, False),
            "P4C_DIRECT_200K": (1, np.array([t_200k], dtype=np.int32), 1, False, 2.75, 2.0, False),
            "P5_CROSS_FIRM_HYBRID": (
                2, np.array(cross_tpls_small[:3], dtype=np.int32), min(3, len(cross_tpls_small)),
                False, 2.50, 2.0, False,
            ),
            "P5B_CROSS_FIRM_SCALE50K_100K": (
                2, np.array(cross_tpls_big[:3], dtype=np.int32), min(3, len(cross_tpls_big)),
                False, 2.50, 2.0, False,
            ),
        }

        grid_cells: dict[str, Any] = {}
        for bank_tr in BANKROLL_GRID_VND_TR:
            for top_tr in TOPUP_GRID_VND_TR:
                cell_key = f"B{int(bank_tr)}tr_T{int(top_tr)}tr"
                init_usd = (bank_tr * 1_000_000.0) / usd_vnd
                topup_usd = (top_tr * 1_000_000.0) / usd_vnd
                pol_res: dict[str, Any] = {}
                for pid, (pmode, ltpls, mslots, allow_dg, up_b, dg_b, wait_top) in policies_spec.items():
                    res_p = _simulate_capital_policy_numba(
                        idx_grid, hazard_5pct, *packed,
                        policy_mode=pmode, ladder_tpls=ltpls, max_slots=mslots,
                        allow_downgrade=allow_dg, upgrade_buf_mult=up_b, downgrade_buf_mult=dg_b,
                        init_bankroll_usd=init_usd, monthly_topup_usd=topup_usd,
                        card_fx_fee_pct=card_fx_fee, discount_rate_annual=DEFAULT_DISCOUNT_RATE,
                        own_book_overflow_mult=0.0, own_book_daily_ret=0.0,
                        abort_after_day=-1, wait_for_top_rung_slot2=wait_top,
                    )
                    pol_res[pid] = summarize_capital_policy_mc(
                        res_p, usd_vnd_rate=usd_vnd,
                        init_bankroll_vnd_tr=bank_tr, monthly_topup_vnd_tr=top_tr,
                    )
                grid_cells[cell_key] = {
                    "bankroll_vnd_tr": bank_tr,
                    "bankroll_usd": round(init_usd, 1),
                    "monthly_topup_vnd_tr": top_tr,
                    "monthly_topup_usd": round(topup_usd, 1),
                    "policies": pol_res,
                    "pareto_winners": select_dual_objective_winners(pol_res),
                }
        pareto_grid[fkey] = grid_cells

        reg_cells: dict[str, Any] = {}
        for bank_tr in BANKROLL_GRID_VND_TR:
            ck = f"B{int(bank_tr)}tr_T0tr"
            init_usd = (bank_tr * 1_000_000.0) / usd_vnd
            reg_pols: dict[str, Any] = {}
            for pid in (
                "P1_REPEAT_10K",
                "P3_SMART_SKIP_DOWNGRADE",
                "P4A_DIRECT_50K",
                "P4A_WAIT_FOR_100K",
                "P4B_DIRECT_100K",
                "P4B_PARALLEL_2X100K",
                "P4C_DIRECT_200K",
                "P5B_CROSS_FIRM_SCALE50K_100K",
            ):
                pmode, ltpls, mslots, allow_dg, up_b, dg_b, wait_top = policies_spec[pid]
                res_pr = _simulate_capital_policy_numba(
                    idx_grid, hazard_5pct, *packed_reg,
                    policy_mode=pmode, ladder_tpls=ltpls, max_slots=mslots,
                    allow_downgrade=allow_dg, upgrade_buf_mult=up_b, downgrade_buf_mult=dg_b,
                    init_bankroll_usd=init_usd, monthly_topup_usd=0.0,
                    card_fx_fee_pct=card_fx_fee, discount_rate_annual=DEFAULT_DISCOUNT_RATE,
                    own_book_overflow_mult=0.0, own_book_daily_ret=0.0,
                    abort_after_day=-1, wait_for_top_rung_slot2=wait_top,
                )
                reg_pols[pid] = summarize_capital_policy_mc(
                    res_pr, usd_vnd_rate=usd_vnd,
                    init_bankroll_vnd_tr=bank_tr, monthly_topup_vnd_tr=0.0,
                )
            reg_cells[ck] = {
                "bankroll_vnd_tr": bank_tr,
                "policies_all_regular": reg_pols,
                "pareto_winners_all_regular": select_dual_objective_winners(reg_pols),
            }
        all_regular_pricing_comparison[fkey] = reg_cells

        h2h_rows = []
        haz_h2h = make_firm_hazard_days(len(idx_single), n_firms_total, 0.05, horizon=horizon_days, seed=seed + 202)
        for bank_tr in (35.0, 50.0, 80.0):
            init_usd = (bank_tr * 1_000_000.0) / usd_vnd
            h2h_common: dict[str, Any] = {
                "allow_downgrade": False,
                "downgrade_buf_mult": 2.0,
                "init_bankroll_usd": init_usd,
                "monthly_topup_usd": 0.0,
                "card_fx_fee_pct": card_fx_fee,
                "discount_rate_annual": DEFAULT_DISCOUNT_RATE,
                "own_book_overflow_mult": 0.0,
                "own_book_daily_ret": 0.0,
                "abort_after_day": -1,
                "wait_for_top_rung_slot2": False,
            }
            r_seq = _simulate_capital_policy_numba(
                idx_single, haz_h2h, *packed,
                policy_mode=1, ladder_tpls=np.array([t_100k], dtype=np.int32),
                max_slots=2, upgrade_buf_mult=2.50, **h2h_common,
            )
            r_par = _simulate_capital_policy_numba(
                idx_single, haz_h2h, *packed,
                policy_mode=3, ladder_tpls=np.array([t_100k], dtype=np.int32),
                max_slots=2, upgrade_buf_mult=2.00, **h2h_common,
            )
            r_1x200 = _simulate_capital_policy_numba(
                idx_single, haz_h2h, *packed,
                policy_mode=1, ladder_tpls=np.array([t_200k], dtype=np.int32),
                max_slots=1, upgrade_buf_mult=2.50, **h2h_common,
            )
            r_par_reg = _simulate_capital_policy_numba(
                idx_single, haz_h2h, *packed_reg,
                policy_mode=3, ladder_tpls=np.array([t_100k], dtype=np.int32),
                max_slots=2, upgrade_buf_mult=2.00, **h2h_common,
            )
            r_200_reg = _simulate_capital_policy_numba(
                idx_single, haz_h2h, *packed_reg,
                policy_mode=1, ladder_tpls=np.array([t_200k], dtype=np.int32),
                max_slots=1, upgrade_buf_mult=2.50, **h2h_common,
            )
            s_seq = summarize_capital_policy_mc(
                r_seq, usd_vnd_rate=usd_vnd, init_bankroll_vnd_tr=bank_tr, monthly_topup_vnd_tr=0.0
            )
            s_par = summarize_capital_policy_mc(
                r_par, usd_vnd_rate=usd_vnd, init_bankroll_vnd_tr=bank_tr, monthly_topup_vnd_tr=0.0
            )
            s_200 = summarize_capital_policy_mc(
                r_1x200, usd_vnd_rate=usd_vnd, init_bankroll_vnd_tr=bank_tr, monthly_topup_vnd_tr=0.0
            )
            s_par_reg = summarize_capital_policy_mc(
                r_par_reg, usd_vnd_rate=usd_vnd, init_bankroll_vnd_tr=bank_tr, monthly_topup_vnd_tr=0.0
            )
            s_200_reg = summarize_capital_policy_mc(
                r_200_reg, usd_vnd_rate=usd_vnd, init_bankroll_vnd_tr=bank_tr, monthly_topup_vnd_tr=0.0
            )
            h2h_rows.append({
                "bankroll_vnd_tr": bank_tr,
                "bankroll_usd": round(init_usd, 1),
                "two_x_100k": s_seq,
                "sequential_2x_100k": s_seq,
                "parallel_2x_100k": s_par,
                "one_x_200k": s_200,
                "parallel_2x_100k_all_regular": s_par_reg,
                "one_x_200k_all_regular": s_200_reg,
                "ruin_reduction_seq_vs_200k_pp": round(s_200["ruin_pct"] - s_seq["ruin_pct"], 2),
                "ruin_reduction_par_vs_200k_pp": round(s_200["ruin_pct"] - s_par["ruin_pct"], 2),
                "delta_ev_npv24_seq_minus_200k_vnd_tr": round(
                    s_seq["ev_npv_24m_vnd_tr"] - s_200["ev_npv_24m_vnd_tr"], 2
                ),
                "delta_ev_npv24_par_minus_200k_vnd_tr": round(
                    s_par["ev_npv_24m_vnd_tr"] - s_200["ev_npv_24m_vnd_tr"], 2
                ),
            })
        head_to_head_2x100k_vs_1x200k[fkey] = h2h_rows

        if abs(fmult - 1.00) < 1e-9:
            init_50 = (50.0 * 1_000_000.0) / usd_vnd
            for h_label, h_arr in (("0%/yr", hazard_0pct), ("5%/yr", hazard_5pct), ("10%/yr", hazard_10pct)):
                for cfg_name, pmode, ltpls, mslots in (
                    ("SINGLE_FIRM_FTMO_2x100K", 1, np.array([t_100k], dtype=np.int32), 2),
                    ("TWO_FIRM_SPLIT", 2, np.array(cross_tpls_big[:2], dtype=np.int32), min(2, len(cross_tpls_big))),
                    (
                        "THREE_FIRM_SURVIVING_SPLIT",
                        2,
                        np.array(cross_tpls_big[:3], dtype=np.int32),
                        min(3, len(cross_tpls_big)),
                    ),
                ):
                    r_h = _simulate_capital_policy_numba(
                        idx_grid, h_arr, *packed,
                        policy_mode=pmode, ladder_tpls=ltpls, max_slots=mslots,
                        allow_downgrade=False, upgrade_buf_mult=2.50, downgrade_buf_mult=2.0,
                        init_bankroll_usd=init_50, monthly_topup_usd=0.0,
                        card_fx_fee_pct=card_fx_fee, discount_rate_annual=DEFAULT_DISCOUNT_RATE,
                        own_book_overflow_mult=0.0, own_book_daily_ret=0.0,
                        abort_after_day=-1, wait_for_top_rung_slot2=False,
                    )
                    cross_firm_hazard_study.append({
                        "hazard_rate": h_label,
                        "allocation": cfg_name,
                        **summarize_capital_policy_mc(
                            r_h, usd_vnd_rate=usd_vnd, init_bankroll_vnd_tr=50.0, monthly_topup_vnd_tr=0.0
                        ),
                    })

    sunk_cost_abort_study = _run_sunk_cost_abort_study(
        catalog=catalog,
        ftmo_std=ftmo_std,
        cache=cache,
        idx_grid=idx_grid,
        hazard_0pct=hazard_0pct,
        primary_var=primary_var,
        use_promo_prices=use_promo_prices,
        usd_vnd=usd_vnd,
        card_fx_fee=card_fx_fee,
    )
    return (
        firm_ids_unique,
        pareto_grid,
        head_to_head_2x100k_vs_1x200k,
        all_regular_pricing_comparison,
        cross_firm_hazard_study,
        sunk_cost_abort_study,
    )

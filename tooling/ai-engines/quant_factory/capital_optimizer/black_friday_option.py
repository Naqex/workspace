"""V3 Black Friday 2-Deadline Real-Option Analysis (`30/11` 0 VND bill lock -> `~14/12` cutoff vs Xmas/NY).

Models the zero-cost 14-day call option created by locking an unpaid Black Friday invoice on `30/11`
(`0 VND` spent upfront, `MODEL_ASSUMPTION`) and deciding whether to pay on `~14/12` AFTER observing:
  - `01/12`: Holdout v2 prospective lock,
  - `04/12`: Live NFP quote/red-news telemetry,
  - `08/12`: FTMO Free Trial 14-day completion,
  - `10/12`: Live CPI quote/red-news telemetry.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from quant_factory.capital_optimizer.catalog import get_program_tier
from quant_factory.capital_optimizer.constants import (
    CALENDAR_DAYS_PER_TRADING_DAY,
    DEFAULT_DISCOUNT_RATE,
    VARIANT_PHASE_CONFIGS,
)
from quant_factory.capital_optimizer.promo_sweep import _as_stage_arrays, _sale_common_kwargs
from quant_factory.capital_optimizer.replay_cache import ExactTierReplayCache
from quant_factory.capital_optimizer.simulator import _simulate_single_ticket_rules_numba

BLACK_FRIDAY_2DEADLINE_MILESTONES: tuple[dict[str, Any], ...] = (
    {
        "id": "bf_bill_lock",
        "date": "2026-11-30",
        "offset_cal_days": 0,
        "spend_vnd": 0,
        "label": "Deadline 1: Lock unpaid BF bill at 0 VND (MODEL_ASSUMPTION — verify on checkout screen)",
    },
    {
        "id": "holdout_v2_lock",
        "date": "2026-12-01",
        "offset_cal_days": 1,
        "spend_vnd": 0,
        "label": "Holdout v2 prospective lock (>= 2026-12-01)",
    },
    {
        "id": "nfp_event",
        "date": "2026-12-04",
        "offset_cal_days": 4,
        "spend_vnd": 0,
        "label": "Live US NFP quote/spread & red-news shield verification",
    },
    {
        "id": "ftmo_free_trial_end",
        "date": "2026-12-08",
        "offset_cal_days": 8,
        "spend_vnd": 0,
        "label": "FTMO Free Trial 14-day completion & full execution telemetry",
    },
    {
        "id": "cpi_event",
        "date": "2026-12-10",
        "offset_cal_days": 10,
        "spend_vnd": 0,
        "label": "Live US CPI quote/spread & red-news shield verification",
    },
    {
        "id": "bf_14day_payment_cutoff",
        "date": "2026-12-14",
        "offset_cal_days": 14,
        "spend_vnd": 0,
        "label": "Deadline 2: 14-day BF payment cutoff (exercise at BF price if GO, else expire at 0 VND)",
    },
    {
        "id": "xmas_new_year_window",
        "date": "2026-12-30",
        "offset_cal_days": 30,
        "spend_vnd": 0,
        "label": "Xmas / New Year window (~30d from 30/11, FTMO 0%-10% HISTORICAL_PATTERN)",
    },
)


def _require_finite_float(
    val: Any,
    name: str,
    *,
    min_val: float | None = None,
    max_val: float | None = None,
    strict_min: bool = False,
    strict_max: bool = False,
) -> float:
    if isinstance(val, bool):
        raise ValueError(f"INVALID_INPUT_BOOL: {name} must be finite float, got bool")
    try:
        x = float(val)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"INVALID_INPUT_FLOAT: {name}={val!r}") from exc
    if not math.isfinite(x):
        raise ValueError(f"INVALID_INPUT_NON_FINITE: {name}={val!r}")
    if min_val is not None and (x <= min_val if strict_min else x < min_val):
        raise ValueError(f"INVALID_INPUT_RANGE: {name}={x} violates min {min_val}")
    if max_val is not None and (x >= max_val if strict_max else x > max_val):
        raise ValueError(f"INVALID_INPUT_RANGE: {name}={x} violates max {max_val}")
    return x


def _require_strict_int(val: Any, name: str, *, min_val: int | None = None) -> int:
    if isinstance(val, bool) or not isinstance(val, int):
        raise ValueError(f"INVALID_INPUT_INT: {name} must be int (not bool), got {type(val).__name__}")
    if min_val is not None and val < min_val:
        raise ValueError(f"INVALID_INPUT_RANGE: {name}={val} < {min_val}")
    return int(val)


def _sim_npv24(
    idx_matrix: np.ndarray,
    stage_arrays: tuple[np.ndarray, ...],
    *,
    fee_day0: float,
    fee_reg: float,
    wait_cal_days: int,
    shifting_horizon: bool,
    common: dict[str, Any],
) -> float:
    wtd = max(0, int(round(wait_cal_days / CALENDAR_DAYS_PER_TRADING_DAY)))
    st = _as_stage_arrays(stage_arrays)
    if shifting_horizon:
        # Use Common Random Numbers (same stationary [0:504] paths) with exact analytical time-shift
        # discounting so MC window-slice noise cannot swamp small 14-day time-value discounts.
        res0 = _simulate_single_ticket_rules_numba(
            idx_matrix[:, : min(504, idx_matrix.shape[1])],
            *st,
            fee_day0_usd=float(fee_day0),
            fee_regular_usd=float(fee_reg),
            start_day_offset=0,
            shifting_horizon=False,
            **common,
        )
        r_ann = float(common["discount_rate_annual"])
        return float(np.mean(res0[9])) * ((1.0 + r_ann) ** (-float(wait_cal_days) / 365.0))

    res = _simulate_single_ticket_rules_numba(
        idx_matrix[:, : min(504, idx_matrix.shape[1])],
        *st,
        fee_day0_usd=float(fee_day0),
        fee_regular_usd=float(fee_reg),
        start_day_offset=wtd,
        shifting_horizon=False,
        **common,
    )
    return float(np.mean(res[9]))


def evaluate_black_friday_2deadline_option(
    *,
    catalog: dict[str, Any],
    ftmo_std: dict[str, Any],
    cache: ExactTierReplayCache,
    idx_matrix: np.ndarray,
    primary_var: str,
    usd_vnd: float,
    card_fx_fee: float,
    tiers_usd: tuple[float, ...] = (10_000.0, 50_000.0, 100_000.0),
    p_go_grid: tuple[float, ...] = (0.50, 0.70, 0.85, 1.00),
    p_xmas_grid: tuple[float, ...] = (0.25, 0.50, 0.75, 1.00),
    xmas_discount_pct: float = 0.10,
    xmas_wait_cal_days: int = 30,
    cutoff_wait_cal_days: int = 14,
    discount_rate_annual: float = DEFAULT_DISCOUNT_RATE,
    nominal_friction_x: float = 1.00,
    adverse_friction_x: float = 2.00,
) -> dict[str, Any]:
    """Quantify 0 VND 14-day BF bill-lock option EV vs blind buy (`30/11`), regular (`14/12`), and Xmas/NY (`30/12`)."""
    usd_vnd = _require_finite_float(usd_vnd, "usd_vnd", min_val=0.0, strict_min=True)
    card_fx_fee = _require_finite_float(card_fx_fee, "card_fx_fee", min_val=0.0, max_val=1.0, strict_max=True)
    xmas_discount_pct = _require_finite_float(
        xmas_discount_pct, "xmas_discount_pct", min_val=0.0, max_val=1.0, strict_max=True
    )
    xmas_wait_cal_days = _require_strict_int(xmas_wait_cal_days, "xmas_wait_cal_days", min_val=0)
    cutoff_wait_cal_days = _require_strict_int(cutoff_wait_cal_days, "cutoff_wait_cal_days", min_val=0)
    discount_rate_annual = _require_finite_float(discount_rate_annual, "discount_rate_annual", min_val=0.0)
    nominal_friction_x = _require_finite_float(nominal_friction_x, "nominal_friction_x", min_val=0.0, strict_min=True)
    adverse_friction_x = _require_finite_float(adverse_friction_x, "adverse_friction_x", min_val=0.0, strict_min=True)
    if not tiers_usd:
        raise ValueError("INVALID_INPUT_EMPTY: tiers_usd must be non-empty")
    tiers_usd = tuple(_require_finite_float(c, "tiers_usd", min_val=0.0, strict_min=True) for c in tiers_usd)
    if not p_go_grid:
        raise ValueError("INVALID_INPUT_EMPTY: p_go_grid must be non-empty")
    p_go_grid = tuple(_require_finite_float(p, "p_go_grid", min_val=0.0, max_val=1.0) for p in p_go_grid)
    if not p_xmas_grid:
        raise ValueError("INVALID_INPUT_EMPTY: p_xmas_grid must be non-empty")
    p_xmas_grid = tuple(_require_finite_float(p, "p_xmas_grid", min_val=0.0, max_val=1.0) for p in p_xmas_grid)

    vc = VARIANT_PHASE_CONFIGS[primary_var]
    tier_results: list[dict[str, Any]] = []
    all_weak_dom = True
    all_bf_beats_reg = True
    all_bf_beats_xmas_ref = True

    for cap in tiers_usd:
        _, merged = get_program_tier(catalog, ftmo_std["program_id"], cap)
        orig_fee = float(merged["orig_usd"])
        bf_fee = float(merged["active_promo_usd"])
        bf_disc_pct = float(merged.get("active_promo_pct", max(0.0, 1.0 - bf_fee / orig_fee)))
        xmas_fee = orig_fee * (1.0 - float(xmas_discount_pct))
        eff_bf_fee_usd = bf_fee * (1.0 + card_fx_fee)
        eff_orig_fee_usd = orig_fee * (1.0 + card_fx_fee)
        bf_saving_usd = (orig_fee - bf_fee) * (1.0 + card_fx_fee)

        st_nom = cache.build_stage_tuple(
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
            friction_mult=nominal_friction_x,
        )
        st_adv = cache.build_stage_tuple(
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
            friction_mult=adverse_friction_x,
        )
        common = _sale_common_kwargs(
            merged,
            card_fx_fee_pct=card_fx_fee,
            discount_rate_annual=discount_rate_annual,
            p1_lock_trigger=vc["p1_lock_trigger"],
            p2_lock_trigger=vc["p2_lock_trigger"],
            amber_dd=vc["amber_dd"],
            red_dd=vc["red_dd"],
            p1_ea_stop=vc["p1_ea_daily_stop"],
            p2_ea_stop=vc["p2_ea_daily_stop"],
            fn_ea_stop=vc["funded_ea_daily_stop"],
            max_retries=0,
        )

        # NO-GO downside if bought blind on 30/11: either abandoned sunk ticket fee (`-eff_bf_fee_usd`)
        # or traded under adverse friction regime (`2.00x`).
        nogo_sunk_fee_usd = -eff_bf_fee_usd
        nogo_adverse_2x_usd = _sim_npv24(
            idx_matrix,
            st_adv,
            fee_day0=bf_fee,
            fee_reg=orig_fee,
            wait_cal_days=0,
            shifting_horizon=False,
            common=common,
        )

        horizons: dict[str, dict[str, Any]] = {}
        for h_key, shift_flag in (("fixed_deadline_24m", False), ("shifting_horizon_24m", True)):
            npv_bf_d0 = _sim_npv24(
                idx_matrix,
                st_nom,
                fee_day0=bf_fee,
                fee_reg=orig_fee,
                wait_cal_days=0,
                shifting_horizon=shift_flag,
                common=common,
            )
            npv_bf_d14 = _sim_npv24(
                idx_matrix,
                st_nom,
                fee_day0=bf_fee,
                fee_reg=orig_fee,
                wait_cal_days=cutoff_wait_cal_days,
                shifting_horizon=shift_flag,
                common=common,
            )
            npv_reg_d14 = _sim_npv24(
                idx_matrix,
                st_nom,
                fee_day0=orig_fee,
                fee_reg=orig_fee,
                wait_cal_days=cutoff_wait_cal_days,
                shifting_horizon=shift_flag,
                common=common,
            )
            npv_xmas_sale_d30 = _sim_npv24(
                idx_matrix,
                st_nom,
                fee_day0=xmas_fee,
                fee_reg=orig_fee,
                wait_cal_days=xmas_wait_cal_days,
                shifting_horizon=shift_flag,
                common=common,
            )
            npv_xmas_reg_d30 = _sim_npv24(
                idx_matrix,
                st_nom,
                fee_day0=orig_fee,
                fee_reg=orig_fee,
                wait_cal_days=xmas_wait_cal_days,
                shifting_horizon=shift_flag,
                common=common,
            )

            delay_cost_14d_usd = max(0.0, npv_bf_d0 - npv_bf_d14)
            # Breakeven p_go* where EV_B(14d option) == EV_A(blind buy 30/11) under sunk-fee loss:
            # p_go * npv_bf_d14 == p_go * npv_bf_d0 + (1 - p_go) * (-eff_bf_fee_usd)
            # => p_go * (delay_cost_14d + eff_bf_fee_usd) == eff_bf_fee_usd
            denom_be = delay_cost_14d_usd + eff_bf_fee_usd
            be_p_go = (eff_bf_fee_usd / denom_be) if denom_be > 1e-9 else 1.0

            grid_rows: list[dict[str, Any]] = []
            for p_go in p_go_grid:
                ev_a_sunk = p_go * npv_bf_d0 + (1.0 - p_go) * nogo_sunk_fee_usd
                ev_a_adv2x = p_go * npv_bf_d0 + (1.0 - p_go) * min(nogo_adverse_2x_usd, 0.0)
                ev_b = p_go * npv_bf_d14
                ev_c = p_go * npv_reg_d14
                if p_go > 0.0 and ev_b <= ev_c:
                    all_bf_beats_reg = False

                for p_xmas in p_xmas_grid:
                    ev_d = p_go * (p_xmas * npv_xmas_sale_d30 + (1.0 - p_xmas) * npv_xmas_reg_d30)
                    # Zero-cost 14-day option gives the RIGHT (not obligation) to exercise BF on 14/12:
                    # choice set expands from {C, D} to {B, C, D} when invoice is honored, else falls back
                    # cleanly to max(C, D) at 0 VND penalty.
                    fallback_best = max(ev_c, ev_d)
                    option_best = max(ev_b, fallback_best)
                    for p_bill in (0.0, 0.5, 1.0):
                        ev_b_comp = p_bill * option_best + (1.0 - p_bill) * fallback_best
                        if ev_b_comp + 1e-6 < fallback_best:
                            all_weak_dom = False

                    grid_rows.append(
                        {
                            "p_go": round(float(p_go), 2),
                            "p_xmas": round(float(p_xmas), 2),
                            "ev_a_buy_blind_30nov_usd": round(ev_a_sunk, 2),
                            "ev_a_buy_blind_30nov_vnd_tr": round(ev_a_sunk * usd_vnd / 1_000_000.0, 2),
                            "ev_a_buy_blind_adverse2x_usd": round(ev_a_adv2x, 2),
                            "ev_b_lock_unpaid_pay_14dec_usd": round(ev_b, 2),
                            "ev_b_lock_unpaid_pay_14dec_vnd_tr": round(ev_b * usd_vnd / 1_000_000.0, 2),
                            "ev_c_skip_bf_regular_14dec_usd": round(ev_c, 2),
                            "ev_c_skip_bf_regular_14dec_vnd_tr": round(ev_c * usd_vnd / 1_000_000.0, 2),
                            "ev_d_skip_bf_wait_xmas_usd": round(ev_d, 2),
                            "ev_d_skip_bf_wait_xmas_vnd_tr": round(ev_d * usd_vnd / 1_000_000.0, 2),
                            "option_value_b_minus_a_usd": round(ev_b - ev_a_sunk, 2),
                            "option_value_b_minus_a_vnd_tr": round((ev_b - ev_a_sunk) * usd_vnd / 1_000_000.0, 2),
                            "lock_value_b_minus_c_usd": round(ev_b - ev_c, 2),
                            "lock_value_b_minus_c_vnd_tr": round((ev_b - ev_c) * usd_vnd / 1_000_000.0, 2),
                            "advantage_b_minus_d_xmas_usd": round(ev_b - ev_d, 2),
                            "advantage_b_minus_d_xmas_vnd_tr": round((ev_b - ev_d) * usd_vnd / 1_000_000.0, 2),
                        }
                    )

            # Representative reference row: p_go = 0.70, p_xmas = 0.50
            ref_row = next(
                (r for r in grid_rows if abs(r["p_go"] - 0.70) < 1e-6 and abs(r["p_xmas"] - 0.50) < 1e-6),
                grid_rows[0],
            )
            if ref_row["advantage_b_minus_d_xmas_usd"] <= 0.0:
                all_bf_beats_xmas_ref = False
            horizons[h_key] = {
                "npv24_bf_day0_usd": round(npv_bf_d0, 2),
                "npv24_bf_day14_usd": round(npv_bf_d14, 2),
                "npv24_regular_day14_usd": round(npv_reg_d14, 2),
                "npv24_xmas_10pct_day30_usd": round(npv_xmas_sale_d30, 2),
                "npv24_xmas_regular_day30_usd": round(npv_xmas_reg_d30, 2),
                "delay_cost_14d_usd": round(delay_cost_14d_usd, 2),
                "delay_cost_14d_vnd_tr": round(delay_cost_14d_usd * usd_vnd / 1_000_000.0, 3),
                "breakeven_p_go_for_blind_buy": round(be_p_go, 4),
                "reference_pgo70_pxmas50": ref_row,
                "sensitivity_grid": grid_rows,
            }

        tier_results.append(
            {
                "program_id": ftmo_std["program_id"],
                "capital_usd": cap,
                "orig_fee_usd": round(orig_fee, 2),
                "bf_fee_usd": round(bf_fee, 2),
                "bf_discount_pct": round(bf_disc_pct * 100.0, 1),
                "xmas_discount_pct": round(float(xmas_discount_pct) * 100.0, 1),
                "effective_bf_fee_with_fx_usd": round(eff_bf_fee_usd, 2),
                "effective_bf_fee_with_fx_vnd_tr": round(eff_bf_fee_usd * usd_vnd / 1_000_000.0, 2),
                "effective_orig_fee_with_fx_usd": round(eff_orig_fee_usd, 2),
                "bf_upfront_saving_with_fx_usd": round(bf_saving_usd, 2),
                "bf_upfront_saving_with_fx_vnd_tr": round(bf_saving_usd * usd_vnd / 1_000_000.0, 2),
                "nogo_sunk_fee_loss_usd": round(nogo_sunk_fee_usd, 2),
                "nogo_adverse_2x_npv24_usd": round(nogo_adverse_2x_usd, 2),
                "horizons": horizons,
            }
        )

    return {
        "schema": "naqex-bf-2deadline-option-v3",
        "variant": primary_var,
        "nominal_friction_x": nominal_friction_x,
        "adverse_friction_x": adverse_friction_x,
        "cutoff_wait_cal_days": int(cutoff_wait_cal_days),
        "xmas_wait_cal_days": int(xmas_wait_cal_days),
        "xmas_discount_pct": round(float(xmas_discount_pct) * 100.0, 1),
        "milestones": list(BLACK_FRIDAY_2DEADLINE_MILESTONES),
        "weak_dominance_verified": bool(all_weak_dom and all_bf_beats_reg),
        "bf_strictly_beats_regular_14dec": bool(all_bf_beats_reg),
        "bf_strictly_beats_xmas_ref": bool(all_bf_beats_xmas_ref),
        "assumption_tag": "MODEL_ASSUMPTION",
        "assumption_disclosure": (
            "MODEL_ASSUMPTION: Locking an unpaid FTMO Black Friday invoice on 30/11 at 0 VND to hold the BF "
            "promo price for ~14 days until 14/12 is NOT guaranteed by contract; verify visually on "
            "trader.ftmo.com checkout on 30/11 without entering payment details. Even if the unpaid invoice "
            "expires early (p_bill_honored = 0%), attempting the 0 VND lock incurs zero penalty and falls back "
            "cleanly to the post-gate 14/12 Regular vs Xmas/NY choice (strictly weakly dominant)."
        ),
        "tiers": tier_results,
    }

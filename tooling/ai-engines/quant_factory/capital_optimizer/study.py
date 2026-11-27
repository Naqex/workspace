"""Full end-to-end sealed-Dev (`<= 2024`) multi-firm capital, rounding, promo & Pareto study orchestrator."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from quant_factory.capital_optimizer.black_friday_option import evaluate_black_friday_2deadline_option
from quant_factory.capital_optimizer.catalog import (
    _find_program_by_hint,
    detect_pricing_traps,
    load_pricing_catalog,
    load_step5_c00_c10_summary,
)
from quant_factory.capital_optimizer.constants import (
    CONTROL_VARIANT_DEFAULT,
    CORE7_IDS,
    DD_ANCHOR_TAG_UNVERIFIED_UNLESS_FLAT,
    DEFAULT_DERIVED_TAPES_DIR,
    DEFAULT_DERIVED_TAPES_STEM,
    DEFAULT_DISCOUNT_RATE,
    DEFAULT_SEED,
    ORDER_SEND_CAPABLE,
    ORDER_SEND_COUNT,
    PRIMARY_VARIANT_DEFAULT,
    TRADING_DAYS_PER_MONTH,
    VARIANT_PHASE_CONFIGS,
)
from quant_factory.capital_optimizer.lot_sizing import assert_strict_pre_holdout_days
from quant_factory.capital_optimizer.replay_cache import ExactTierReplayCache
from quant_factory.capital_optimizer.rollover_reset import (
    run_rollover_reset_sensitivity,
    verify_tapes_flat_at_reset,
)
from quant_factory.capital_optimizer.simulator import make_block_bootstrap_indices
from quant_factory.capital_optimizer.study_scaling import run_capital_scaling_section
from quant_factory.capital_optimizer.study_sections import (
    run_lot_rounding_and_friction_sections,
    run_mode_comparison_and_e8_section,
)
from quant_factory.capital_optimizer.study_sensitivity import run_friction_npv_fee_and_sale_sections


def run_full_capital_promo_study(
    *,
    catalog_path: Path | None = None,
    step5_path: Path | None = None,
    n_paths_grid: int = 5_000,
    n_paths_single: int = 10_000,
    horizon_months: int = 36,
    use_promo_prices: bool = True,
    primary_variant: str = PRIMARY_VARIANT_DEFAULT,
    allow_stale_catalog: bool = False,
    seed: int = DEFAULT_SEED,
) -> dict[str, Any]:
    """Execute the full sealed-Dev (`<= 2024`) multi-firm capital, rounding, promo & Pareto study."""
    t0 = time.perf_counter()
    from quant_factory.data_store import (
        assert_holdout_locked,
        build_or_load_frozen_tapes,
        load_red_news_calendar,
        load_registry,
    )

    lock_sha = assert_holdout_locked()
    frozen = build_or_load_frozen_tapes()
    ext_days = list(frozen["ext_days"])
    holdout_rows = assert_strict_pre_holdout_days(ext_days)
    reg = load_registry()
    base_r = {e["id"]: float(e["base_risk_pct"]) / 100.0 for e in reg["engines"]}
    rn_cal = load_red_news_calendar()

    catalog = load_pricing_catalog(
        catalog_path,
        allow_fallback=False,
        enforce_freshness=True,
        allow_stale=allow_stale_catalog,
    )
    traps = detect_pricing_traps(catalog)
    step5_info = load_step5_c00_c10_summary(step5_path)
    primary_var = str(primary_variant or PRIMARY_VARIANT_DEFAULT)
    if primary_var not in VARIANT_PHASE_CONFIGS:
        raise ValueError(f"Unknown primary_variant: {primary_var!r}")
    step5_info["primary_variant"] = primary_var

    usd_vnd = float(catalog["fx_rates"]["usd_vnd"])
    card_fx_fee = float(catalog["vn_transaction_costs"]["card_fx_buy_fee_pct"])
    horizon_days = int(horizon_months * TRADING_DAYS_PER_MONTH)

    cache = ExactTierReplayCache(ext_days, frozen["tapes"], base_r, rn_cal)
    idx_single = make_block_bootstrap_indices(
        len(ext_days), horizon=horizon_days, n_paths=n_paths_single, seed=seed
    )
    idx_grid = idx_single[: min(n_paths_grid, n_paths_single)]

    lot_rounding_audit, friction_sweep_100k, friction_breakeven_x = run_lot_rounding_and_friction_sections(cache)
    mode_comparison, e8_pro_buffer_sensitivity, calibrated_cache, rule_family_cal_cache = (
        run_mode_comparison_and_e8_section(
            catalog=catalog,
            cache=cache,
            idx_single=idx_single,
            idx_grid=idx_grid,
            horizon_days=horizon_days,
            primary_var=primary_var,
            use_promo_prices=use_promo_prices,
            usd_vnd=usd_vnd,
            card_fx_fee=card_fx_fee,
        )
    )

    ftmo_std = _find_program_by_hint(
        catalog, lambda p: p["firm_id"] == "FTMO" and p["steps"] == 2 and p["profile_mode"] == "Standard"
    )
    other_progs = [p for p in catalog["programs"] if p["firm_id"] != "FTMO"]
    (
        friction_lifecycle_10k_100k,
        npv_discount_sensitivity,
        fee_accounting_sensitivity,
        sale_decision_table,
    ) = run_friction_npv_fee_and_sale_sections(
        catalog=catalog,
        ftmo_std=ftmo_std,
        cache=cache,
        idx_single=idx_single,
        idx_grid=idx_grid,
        horizon_days=horizon_days,
        primary_var=primary_var,
        use_promo_prices=use_promo_prices,
        usd_vnd=usd_vnd,
        card_fx_fee=card_fx_fee,
    )

    if ftmo_std is None:
        raise RuntimeError("FTMO 2-Step Standard program missing from pricing catalog")

    (
        firm_ids_unique,
        pareto_grid,
        head_to_head_2x100k_vs_1x200k,
        all_regular_pricing_comparison,
        cross_firm_hazard_study,
        sunk_cost_abort_study,
    ) = run_capital_scaling_section(
        catalog=catalog,
        ftmo_std=ftmo_std,
        other_progs=other_progs,
        cache=cache,
        calibrated_cache=calibrated_cache,
        rule_family_cal_cache=rule_family_cal_cache,
        idx_single=idx_single,
        idx_grid=idx_grid,
        horizon_days=horizon_days,
        primary_var=primary_var,
        use_promo_prices=use_promo_prices,
        usd_vnd=usd_vnd,
        card_fx_fee=card_fx_fee,
        seed=seed,
    )

    elapsed_core = round(time.perf_counter() - t0, 2)
    flat_at_reset_audit = verify_tapes_flat_at_reset(frozen["tapes"], engine_ids=CORE7_IDS)
    rollover_reset_sensitivity = run_rollover_reset_sensitivity(
        catalog=catalog,
        cache=cache,
        idx_matrix=idx_grid,
        horizon_days=horizon_days,
        primary_var=primary_var,
        use_promo_prices=use_promo_prices,
        usd_vnd=usd_vnd,
        card_fx_fee=card_fx_fee,
        flat_at_reset_audit=flat_at_reset_audit,
        calibrated_cache=calibrated_cache,
    )
    black_friday_2deadline_option = evaluate_black_friday_2deadline_option(
        catalog=catalog,
        ftmo_std=ftmo_std,
        cache=cache,
        idx_matrix=idx_grid,
        primary_var=primary_var,
        usd_vnd=usd_vnd,
        card_fx_fee=card_fx_fee,
    )

    from quant_core.io_utils import sha256_file

    npz_path = DEFAULT_DERIVED_TAPES_DIR / f"{DEFAULT_DERIVED_TAPES_STEM}.npz"
    npz_sha = sha256_file(npz_path) if npz_path.is_file() else ""
    elapsed = round(time.perf_counter() - t0, 2)
    return {
        "schema": "naqex-multi-firm-capital-promo-optimizer-v3",
        "generated_utc": datetime.now(UTC).isoformat(),
        "elapsed_seconds": elapsed,
        "elapsed_core_v2_seconds": elapsed_core,
        "tape_provenance": {
            "stem": DEFAULT_DERIVED_TAPES_STEM,
            "binding_sha256": str(frozen.get("binding_sha256", "")),
            "npz_sha256": npz_sha,
            "min_day": str(ext_days[0]),
            "max_day": str(ext_days[-1]),
            "dev_days_count": len(ext_days),
            "holdout_rows_analysed": holdout_rows,
        },
        "v3_upgrades": {
            "flat_at_reset_verified": flat_at_reset_audit["flat_at_reset_verified"],
            "rollover_floating_equity_sensitivity_enabled": True,
            "black_friday_2deadline_option_enabled": True,
            "black_friday_weak_dominance_verified": black_friday_2deadline_option["weak_dominance_verified"],
            "x13_pure_numpy_numba_shard_mode_enabled": True,
        },
        "safety_invariants": {
            "order_send_capable": ORDER_SEND_CAPABLE,
            "order_send_count": ORDER_SEND_COUNT,
            "holdout_rows_analysed": holdout_rows,
            "holdout_lock_sha256": lock_sha,
            "dev_window": f"{ext_days[0]}..{ext_days[-1]}",
            "dev_days_count": len(ext_days),
            "model_tag": "DAILY_APPROX",
            "evidence_stage": "DEV_BACKTEST_2018_2024_PLUS_FTMO_DEMO_28RT_PROBE_ONLY",
        },
        "astra_r10_q3_closures": {
            "primary_variant": primary_var,
            "control_variant": CONTROL_VARIANT_DEFAULT,
            "fail_closed_catalog_and_staleness": True,
            "purchase_day_pricing_no_perpetual_bf": True,
            "per_contract_daily_dd_anchor": True,
            "own_book_overflow_mult_in_rankings": 0.0,
            "p5_surviving_firms": firm_ids_unique[:3],
            "p5_excluded_firms": [
                {"firm_id": "E8_MARKETS", "reason": "STRUCTURAL_LOCK_AT_INITIAL_FLOOR_HIGH_12M_FUNDED_BREACH"}
            ],
            "p4a_wait_for_100k_enabled": True,
            "p4b_parallel_2x100k_enabled": True,
            "pareto_reports_mean_median_and_p_le_0": True,
            "sale_calendar_exact_sweep_dual_horizon": True,
            "fee_accounting_separated_card_refund_0pct": True,
            "b1_sizing_parity_disclosed": True,
        },
        "astra_r11_closures": {
            "per_tier_verified_utc_strict_no_inheritance": True,
            "reject_nan_inf_and_future_timestamps": True,
            "non_ftmo_dd_anchor_tag": DD_ANCHOR_TAG_UNVERIFIED_UNLESS_FLAT,
            "non_ftmo_dd_anchor_firms": ["THE5ERS", "IC_FUNDED"],
            "shifting_horizon_dense_0_to_180_sweep": True,
            "shifting_horizon_dual_readout_continuous_and_last_positive": True,
        },
        "inputs": {
            "primary_variant": primary_var,
            "control_variant": CONTROL_VARIANT_DEFAULT,
            "pricing_catalog_source": catalog.get("source_path"),
            "pricing_catalog_sha256": catalog.get("source_sha256"),
            "pricing_catalog_is_fallback": catalog.get("is_fallback", False),
            "pricing_catalog_freshness": catalog.get("freshness_report", {}),
            "fx_usd_vnd": usd_vnd,
            "card_fx_buy_fee_pct": round(card_fx_fee * 100.0, 2),
            "ftmo_refund_withdrawal_fee_pct": 0.0,
            "own_book_overflow_mult_in_rankings": 0.0,
            "discount_rate_annual_pct": round(DEFAULT_DISCOUNT_RATE * 100.0, 1),
            "step5_c00_vs_c10": step5_info,
            "n_paths_single": n_paths_single,
            "n_paths_grid": n_paths_grid,
            "horizon_months": horizon_months,
            "use_promo_prices": use_promo_prices,
            "pricing_regime_primary": "BF_DAY0_PLUS_REGULAR_RETRIES" if use_promo_prices else "ALL_REGULAR",
            "seed": seed,
            "unique_exact_m1_replays_cached": len(cache._replay_cache),
        },
        "pricing_traps": traps,
        "lot_rounding_audit": lot_rounding_audit,
        "friction_sweep_100k": friction_sweep_100k,
        "friction_breakeven_x": friction_breakeven_x,
        "mode_comparison": mode_comparison,
        "e8_pro_buffer_sensitivity": e8_pro_buffer_sensitivity,
        "friction_lifecycle_10k_100k": friction_lifecycle_10k_100k,
        "npv_discount_sensitivity": npv_discount_sensitivity,
        "fee_accounting_sensitivity": fee_accounting_sensitivity,
        "sale_decision_table": sale_decision_table,
        "head_to_head_2x100k_vs_1x200k": head_to_head_2x100k_vs_1x200k,
        "all_regular_pricing_comparison": all_regular_pricing_comparison,
        "cross_firm_hazard_study": cross_firm_hazard_study,
        "sunk_cost_abort_study": sunk_cost_abort_study,
        "pareto_grid": pareto_grid,
        "flat_at_reset_audit": flat_at_reset_audit,
        "rollover_reset_sensitivity": rollover_reset_sensitivity,
        "black_friday_2deadline_option": black_friday_2deadline_option,
    }

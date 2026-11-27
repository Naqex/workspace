"""Backward-compatible façade for `quant_factory.capital_optimizer`.

All implementation lives in `tooling/ai-engines/quant_factory/capital_optimizer/`.
This shim preserves 100% of original public/private imports, constants, and CLI entrypoints.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path
from typing import Any

_AI_ENGINES = Path(__file__).resolve().parents[1]
if str(_AI_ENGINES) not in sys.path:
    sys.path.insert(0, str(_AI_ENGINES))

from quant_factory.capital_optimizer import (  # noqa: E402, F401
    AI_ENGINES,
    BANKROLL_GRID_VND_TR,
    BLACK_FRIDAY_2DEADLINE_MILESTONES,
    BLOCK_LEN,
    CALENDAR_DAYS_PER_TRADING_DAY,
    CONTROL_VARIANT_DEFAULT,
    CORE7_IDS,
    DAILY_DD_ANCHOR_INITIAL_BALANCE,
    DAILY_DD_ANCHOR_PREV_DAY_BALANCE,
    DD_ANCHOR_TAG_BALANCE_VERIFIED,
    DD_ANCHOR_TAG_UNVERIFIED_UNLESS_FLAT,
    DD_EOD_TRAILING,
    DD_INTRADAY_TRAILING,
    DD_STATIC,
    DEFAULT_CATALOG_PATH,
    DEFAULT_CORE7_BASE_RISK,
    DEFAULT_DERIVED_TAPES_DIR,
    DEFAULT_DERIVED_TAPES_STEM,
    DEFAULT_DISCOUNT_RATE,
    DEFAULT_OUT_JSON,
    DEFAULT_OUT_JSON_V2,
    DEFAULT_OUT_MD,
    DEFAULT_OUT_MD_V3,
    DEFAULT_SEED,
    DEFAULT_STEP5_REPORT_PATH,
    DEFAULT_X13_SHARD_SEED,
    DISCOUNT_RATES_ANNUAL,
    E8_EXCLUDED_FIRM_IDS,
    FRICTION_LEVELS,
    FRICTION_SWEEP_WITH_BREAKEVEN,
    HOLDOUT_CUTOFF_DAY,
    HOLDOUT_CUTOFF_UTC_TS,
    HOLDOUT_MAX_YEAR,
    MAX_FUTURE_TIMESTAMP_SKEW_DAYS,
    ORDER_SEND_CAPABLE,
    ORDER_SEND_COUNT,
    PRIMARY_VARIANT_DEFAULT,
    ROLLOVER_ANCHOR_BALANCE,
    ROLLOVER_ANCHOR_EQUITY,
    ROLLOVER_ANCHOR_MAX_BAL_EQ,
    ROLLOVER_SHOCK_LEVELS_PCT,
    ROLLOVER_SHOCK_PROBE_LEVELS_PCT,
    ROOT,
    TIER_SIZES_USD,
    TOPUP_GRID_VND_TR,
    TRADING_DAYS_PER_MONTH,
    TRADING_DAYS_PER_YEAR,
    VARIANT_PHASE_CONFIGS,
    X13_FORBIDDEN_TOKENS,
    ExactTierReplayCache,
    __all__,
    _cal_days_to_trading_days,
    _daily_dd_anchor_code,
    _dd_rule_verification_note,
    _dd_rule_verification_tag,
    _dd_type_code,
    _exec_badge_vi,
    _find_program_by_hint,
    _fmt_num,
    _normalize_external_catalog,
    _pack_templates_for_numba,
    _parse_daily_dd_anchor,
    _parse_dd_type,
    _parse_refund_milestone,
    _parse_utc_iso,
    _pct_to_frac,
    _pick_pair_winners,
    _pick_tier_near,
    _policy_vi_name,
    _rank_law15_tier,
    _require_finite_float,
    _sale_common_kwargs,
    _simulate_capital_policy_numba,
    _simulate_single_ticket_rules_numba,
    assert_strict_pre_holdout_days,
    build_default_pricing_catalog,
    calibrate_safe_multipliers_for_rule,
    check_catalog_freshness,
    compute_exits_balanced_metrics,
    detect_pricing_traps,
    evaluate_black_friday_2deadline_option,
    evaluate_wait_vs_buy_npv,
    exits_to_daily_arrays_with_upside,
    floor_lot_step,
    get_program_tier,
    load_frozen_tapes_v2_direct,
    load_pricing_catalog,
    load_red_news_calendar_direct,
    load_step5_c00_c10_summary,
    main,
    make_block_bootstrap_indices,
    make_firm_hazard_days,
    merge_x13_mc_shards,
    render_vietnamese_law15_report,
    resolve_rollover_anchor_mode,
    run_full_capital_promo_study,
    run_rollover_reset_sensitivity,
    run_x13_mc_shard,
    save_results_json,
    select_dual_objective_winners,
    simulate_exact_lot_rounding_on_trade_list,
    solve_max_wait_days_worth_it,
    summarize_capital_policy_mc,
    summarize_single_ticket_mc,
    validate_x13_job_id,
    verify_tapes_flat_at_reset,
    wilson_upper_95,
)


class _SyncedFacadeModule(types.ModuleType):
    """Propagate façade attribute mutations/deletions to backing `capital_optimizer` submodules."""

    _sync_prefix: str = "quant_factory.capital_optimizer"
    _facade_file: str = ""
    _deleted_targets: dict[str, set[str]]

    def _iter_sync_modules(self) -> list[types.ModuleType]:
        prefix = self._sync_prefix
        prefix_dot = f"{prefix}."
        facade_file = self._facade_file
        targets: list[types.ModuleType] = []
        for mod_name, mod in list(sys.modules.items()):
            if mod is None or mod is self:
                continue
            if mod_name == prefix or mod_name.startswith(prefix_dot):
                targets.append(mod)
                continue
            if facade_file:
                mod_file = getattr(mod, "__file__", None)
                if mod_file:
                    try:
                        if str(Path(mod_file).resolve()) == facade_file:
                            targets.append(mod)
                    except OSError:
                        pass
        return targets

    def __setattr__(self, name: str, value: Any) -> None:
        super().__setattr__(name, value)
        if (name.startswith("__") and name.endswith("__")) or name in (
            "_sync_prefix",
            "_facade_file",
            "_deleted_targets",
        ):
            return
        deleted = getattr(self, "_deleted_targets", {}).get(name)
        for mod in self._iter_sync_modules():
            if name in mod.__dict__ or (deleted is not None and mod.__name__ in deleted):
                types.ModuleType.__setattr__(mod, name, value)
                if deleted is not None:
                    deleted.discard(mod.__name__)

    def __delattr__(self, name: str) -> None:
        super().__delattr__(name)
        if (name.startswith("__") and name.endswith("__")) or name in (
            "_sync_prefix",
            "_facade_file",
            "_deleted_targets",
        ):
            return
        deleted_map: dict[str, set[str]] = getattr(self, "_deleted_targets", {})
        recorded = deleted_map.setdefault(name, set())
        for mod in self._iter_sync_modules():
            if name in mod.__dict__:
                recorded.add(mod.__name__)
                types.ModuleType.__delattr__(mod, name)


_this_mod: Any = sys.modules.get(__name__)
if _this_mod is not None and not isinstance(_this_mod, _SyncedFacadeModule):
    _this_mod.__class__ = _SyncedFacadeModule
    types.ModuleType.__setattr__(_this_mod, "_sync_prefix", "quant_factory.capital_optimizer")
    types.ModuleType.__setattr__(_this_mod, "_facade_file", str(Path(__file__).resolve()))
    types.ModuleType.__setattr__(_this_mod, "_deleted_targets", {})

if __name__ == "__main__":
    raise SystemExit(main())

"""Wave 4 (`W4-G06` & `W4-G07`): Production 81-Case x N=10,000 Shared-Path Pareto Runner.

Strictly offline Dev-only simulation orchestrator (`ORDER_SEND_CAPABLE = False`,
`ORDER_SEND_COUNT = 0`, `HOLDOUT_CUTOFF_DATE = "2024-12-31"`, `holdout_rows_analysed = 0`).

Key guarantees:
  1. Probes `ops_cloud.compute_router` (`probe_dev_pc`, `probe_x13_worker`, `decide_route`)
     respecting Mode A/B, AC-only `<X13_WORKER>` gates, and automatic silent fallback to
     `<DEV_PC>` at `BELOW_NORMAL` priority (zero popup, zero GPU).
  2. Loads empirical sealed-Dev (`2018-01-02..2024-12-31`) M1 tapes from
     `.runtime/hot-m1-cache/_derived/frozen_9e_tapes_v2.{json,npz}` + `red_news_official_2018_2024.json`
     via `ExactTierReplayCache` (`C10_NEWS_ON` / `v1.03`, exact per-SKU `0.01`-lot floor rounding).
  3. Runs ALL `81` configurations (`9` VND bankroll tiers `[10..500]` tr VND x `3` concurrency modes
     x `3` after-payout policies) x `N = 10,000` Shared Market Paths x `36` months (`756` trading days)
     under BOTH `1.0x` baseline slippage AND `1.5x` slippage stress on identical shared paths.
  4. Runs micro-tier The5ers 5K reference rows explicitly tagged `TERMS_VERIFIED_EXECUTION_UNMEASURED`
     + `DD_ANCHOR_UNVERIFIED_UNLESS_FLAT_AT_RESET`.
  5. Verifies on EVERY case (`81/81`):
       - `pass_pct + fail_pct + pending_pct == 100.0` at `3m/6m/12m/24m/36m` (`<= 1e-6`)
       - zero notional double-counting (`max_cash_accounting_err_usd < 1e-6`, `max_active_base_funded <= $400K`)
       - `XẤP XỈ CẤP NGÀY` (`APPROX_DAILY_RESOLUTION`) resolution label
  6. Extracts Per-Tier Pareto Frontiers (all 9 VND tiers), Global Sweet-Spot / Inflection Points
     (`P(ruin) < 1%`, `P(net <= 0 at 24m) < 15%`, Own-Book crossover, $400K cap diminishing returns),
     and writes:
       - `.runtime/offensive4/pareto/wave4_pareto_81cases_10k.json` (full production artifact)
       - `.runtime/offensive4/pareto/wave4_pareto_summary.json` (compact `< 500 KB` summary + exact `report_sha256`)
  7. ZERO bare Python `assert` statements (`[ARCH-02]`), 100% safe under `python -O`.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import sys
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from ops_cloud import compute_router as cr
from quant_core.holdout_guard import enforce_pre_holdout_dates
from quant_core.io_utils import atomic_write_json, sha256_file
from quant_core.schemas import SSOTFirmsCatalog, SSOTRiskProfiles

from quant_factory.capital_optimizer.constants import (
    BLOCK_LEN,
    DEFAULT_CORE7_BASE_RISK,
    DEFAULT_DERIVED_TAPES_DIR,
    DEFAULT_DERIVED_TAPES_STEM,
    DEFAULT_SEED,
    ROOT,
)
from quant_factory.capital_optimizer.lot_sizing import assert_strict_pre_holdout_days
from quant_factory.capital_optimizer.policy_kernel import _pack_templates_for_numba
from quant_factory.capital_optimizer.replay_cache import ExactTierReplayCache
from quant_factory.capital_optimizer.simulator import (
    make_block_bootstrap_indices,
    make_firm_hazard_days,
)
from quant_factory.capital_optimizer.x13_shard import (
    load_frozen_tapes_v2_direct,
    load_red_news_calendar_direct,
)
from quant_factory.treasury_ledger import compute_prop_own_crossover
from quant_factory.wave4 import HOLDOUT_CUTOFF_DATE, ORDER_SEND_CAPABLE
from quant_factory.wave4.pareto_multi_account import (
    _ALLOCATION_CODE,
    _CONCURRENCY_CODE,
    ALL_SKU_AUDIT_CAPITALS_USD,
    ALLOCATION_POLICIES,
    ALLOCATION_POLICY_SPECS,
    BANKROLL_TIERS_M_VND,
    CONCURRENCY_MODES,
    DEFAULT_EVAL_FAIL_COOLDOWN_DAYS,
    DEFAULT_FIRMS_CATALOG_PATH,
    DEFAULT_FTMO_LADDER_CONTRACTS,
    DEFAULT_FUNDED_DD_FREEZE_FRAC,
    DEFAULT_FX_RATES_PATH,
    DEFAULT_HORIZON_DAYS,
    DEFAULT_MAX_SLOTS,
    DEFAULT_RISK_PROFILES_PATH,
    EVIDENCE_STAGE,
    FTMO_MAX_ACTIVE_FUNDED_USD,
    FTMO_MAX_SCALED_FUNDED_USD,
    FTMO_MAX_SINGLE_CHALLENGE_USD,
    HOLDOUT_CUTOFF_DAY,
    HORIZON_MONTHS,
    ORDER_SEND_COUNT,
    RESOLUTION_LABEL_VI,
    RESOLUTION_TAG,
    AllocationPolicy,
    ConcurrencyMode,
    _cal_days_to_trading_days,
    _contract_execution_tag,
    _daily_dd_anchor_from_ssot,
    _refund_milestone_code,
    _require_finite_float,
    _require_strict_int,
    _simulate_wave4_pareto_fleet_numba,
    build_81_case_configs,
    extract_pareto_frontier,
    load_ssot_bundle,
    measure_shared_path_daily_correlation,
    summarize_pareto_case,
)

# ---------------------------------------------------------------------------
# Constants & Canonical Output Paths
# ---------------------------------------------------------------------------

FULL_SCHEMA_VERSION: str = "naqex-wave4-pareto-81cases-10k-v1"
SUMMARY_SCHEMA_VERSION: str = "naqex-wave4-pareto-summary-v1"
DEFAULT_PRODUCTION_N_PATHS: int = 10_000
DEFAULT_BASELINE_FRICTION: float = 1.00
DEFAULT_STRESS_FRICTION: float = 1.50
SUMMARY_MAX_BYTES: int = 500_000

DEFAULT_PARETO_OUT_DIR: Path = ROOT / ".runtime" / "offensive4" / "pareto"
DEFAULT_FULL_OUT_PATH: Path = DEFAULT_PARETO_OUT_DIR / "wave4_pareto_81cases_10k.json"
DEFAULT_SUMMARY_OUT_PATH: Path = DEFAULT_PARETO_OUT_DIR / "wave4_pareto_summary.json"
DEFAULT_THE5ERS_REF_CONTRACTS: tuple[str, ...] = (
    "the5ers_hs_5k_classic",
    "the5ers_hs_5k_new",
)
DEFAULT_THE5ERS_REF_TIERS_M_VND: tuple[int, ...] = (10, 15, 25)

_BELOW_NORMAL_PRIORITY_CLASS: int = 0x00004000
_NORMAL_PRIORITY_CLASS: int = 0x00000020


# ---------------------------------------------------------------------------
# 1. Compute Router Probe, Fallback & Process Priority Guard (Zero Popup)
# ---------------------------------------------------------------------------


def apply_local_process_priority(priority: str, *, cores: int) -> dict[str, Any]:
    """Apply `BELOW_NORMAL` / `NORMAL` priority and thread caps cleanly on Windows (zero popup)."""
    prio = str(priority or "BELOW_NORMAL").upper()
    core_cap = max(1, _require_strict_int(cores, "cores", min_val=1))
    os.environ["NUMBA_NUM_THREADS"] = str(core_cap)
    os.environ["OMP_NUM_THREADS"] = str(core_cap)
    applied = False
    win_error: str | None = None
    if os.name == "nt":
        try:
            k32 = ctypes.windll.kernel32
            proc_handle = k32.GetCurrentProcess()
            prio_flag = _BELOW_NORMAL_PRIORITY_CLASS if prio == "BELOW_NORMAL" else _NORMAL_PRIORITY_CLASS
            applied = bool(k32.SetPriorityClass(proc_handle, prio_flag))
        except Exception as exc:  # pragma: no cover - defensive on non-Win32
            win_error = f"{type(exc).__name__}: {exc}"
    return {
        "requested_priority": prio,
        "priority_applied": applied,
        "core_cap": core_cap,
        "numba_num_threads": os.environ["NUMBA_NUM_THREADS"],
        "win_error": win_error,
    }


def resolve_compute_route(
    *,
    est_minutes: float = 3.5,
    ram_gb: float = 2.0,
    shardable: bool = True,
    prefer_x13: bool = False,
    lan_only: bool = False,
    offline_no_probe: bool = False,
    probe_dev_fn: Callable[[], dict[str, Any]] | None = None,
    probe_x13_fn: Callable[[], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Probe `<DEV_PC>` + `<X13_WORKER>` via `compute_router.py` with fail-closed AC-only fallback."""
    est_m = _require_finite_float(est_minutes, "est_minutes", min_val=0.0)
    ram_req = _require_finite_float(ram_gb, "ram_gb", min_val=0.0)

    if offline_no_probe:
        dev_pc: dict[str, Any] = {
            "idle_sec": 0.0,
            "in_overnight_window_ict": False,
            "gpu_util_pct": 0,
            "fullscreen_busy": False,
            "cpu_util_pct": 10.0,
            "free_ram_gb": 16.0,
            "ntp_offset_ms": 0.0,
            "ntp_ok": True,
            "mode": "MODE_A_OWNER_ACTIVE",
            "probe_mode": "OFFLINE_UNIT_SKIP",
        }
        x13_worker: dict[str, Any] = {
            "ssh_alias": "naqex-x13",
            "transport": "NONE",
            "probe_ms": None,
            "reachable": False,
            "ac_online": False,
            "ac_line_status": None,
            "battery_status_code": None,
            "battery_pct": None,
            "cpu_util_pct": None,
            "free_ram_gb": None,
            "disk_free_gb": None,
            "venv_ok": False,
            "active_job_lock": None,
            "ntp_offset_ms": None,
            "forbidden_files": 0,
            "eligible": False,
            "ineligible_reasons": ["offline_no_probe_mode"],
        }
    else:
        dev_pc = (probe_dev_fn or cr.probe_dev_pc)()
        x13_worker = (
            probe_x13_fn
            if probe_x13_fn is not None
            else (lambda: cr.probe_x13_worker(lan_only=lan_only))
        )()

    decision = cr.decide_route(
        dev_pc,
        x13_worker,
        est_minutes=est_m,
        ram_gb=ram_req,
        shardable=shardable,
        touches_holdout=False,
        touches_vps=False,
        requires_admin=False,
        needs_gpu=False,
        force_x13=bool(prefer_x13),
    )

    # Note: Even when X13 is eligible for a >=10m job, this runner executes the Numba 81-case
    # kernel locally unless dispatched through compute_router bundle runner. When target is X13_ONLY
    # inside in-process mode, fall back cleanly to DEV_PC BELOW_NORMAL and record explicit reason.
    executed_on = "DEV_PC"
    in_process_fallback_reason = decision.get("fallback_reason")
    effective_cores = int(decision.get("dev_pc_cores") or 2)
    effective_priority = str(decision.get("dev_pc_priority") or "BELOW_NORMAL")
    if decision.get("target") != "DEV_PC_ONLY":
        dev_mode = str(dev_pc.get("mode") or "MODE_A_OWNER_ACTIVE")
        if dev_mode == "MODE_B_IDLE_OVERNIGHT":
            effective_cores = 5
            effective_priority = "NORMAL"
        else:
            effective_cores = max(2, effective_cores)
            effective_priority = "BELOW_NORMAL"
        in_process_fallback_reason = (
            f"in_process_local_execution(router_target={decision.get('target')}; "
            "short Numba JIT sweep executed locally under router core/priority caps)"
        )

    return {
        "probed_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "est_minutes": est_m,
        "ram_gb": ram_req,
        "dev_pc": dev_pc,
        "x13_worker": x13_worker,
        "route_decision": decision,
        "executed_on": executed_on,
        "effective_dev_cores": effective_cores,
        "effective_dev_priority": effective_priority,
        "in_process_fallback_reason": in_process_fallback_reason,
    }


# ---------------------------------------------------------------------------
# 2. Empirical Sealed-Dev (`<= 2024-12-31`) M1 Per-SKU Template Builder
# ---------------------------------------------------------------------------


def build_empirical_ssot_templates(
    *,
    firms_catalog: SSOTFirmsCatalog,
    risk_profiles: SSOTRiskProfiles,
    replay_cache: ExactTierReplayCache,
    contract_ids: tuple[str, ...] = DEFAULT_FTMO_LADDER_CONTRACTS,
    profile_id: str | None = None,
    friction_mult: float = DEFAULT_BASELINE_FRICTION,
    use_promo_day0: bool = False,
    funded_mult_override: float | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Build SSOT contract templates backed by exact M1 `0.01`-lot `ExactTierReplayCache` arrays."""
    fmult = _require_finite_float(friction_mult, "friction_mult", min_val=0.1, max_val=10.0)
    pid = profile_id or risk_profiles.primary_profile_id
    if pid not in risk_profiles.profiles:
        raise ValueError(f"UNKNOWN_RISK_PROFILE: {pid!r}")
    rp = risk_profiles.profiles[pid]
    p1 = rp.phases["p1"]
    p2 = rp.phases["p2"]
    fn = rp.phases["funded"]

    fn_mult = (
        _require_finite_float(funded_mult_override, "funded_mult_override", min_val=0.0, strict_min=True)
        if funded_mult_override is not None
        else float(fn.base_phase_mult)
    )
    amber_mult = round(fn_mult * float(rp.amber_mult), 4)
    red_mult = round(fn_mult * float(rp.red_mult), 4)
    p1_symcap = round(float(p1.symcap_frac) * 100.0, 4)
    p2_symcap = round(float(p2.symcap_frac) * 100.0, 4)
    fn_symcap = round(float(fn.symcap_frac) * 100.0, 4)

    firms_seen: dict[str, int] = {}
    templates: list[dict[str, Any]] = []
    sku_diags: dict[str, dict[str, Any]] = {}

    for cid in contract_ids:
        if cid not in firms_catalog.contracts:
            raise ValueError(f"UNKNOWN_SSOT_CONTRACT: {cid!r}")
        c = firms_catalog.contracts[cid]
        if not c.available_vn:
            raise ValueError(f"CONTRACT_UNAVAILABLE_VN: {cid!r} ({c.unavailable_reason_vn})")
        if c.fee_orig_usd is None or c.fee_orig_usd <= 0.0:
            raise ValueError(f"MISSING_FEE_ORIG_USD: {cid!r}")

        fid = c.firm_id.upper()
        if fid not in firms_seen:
            firms_seen[fid] = len(firms_seen)
        fidx = firms_seen[fid]

        prof_mode = "Swing" if "swing" in str(c.account_type).lower() else "Standard"
        p1_news = bool(p1.enable_red_news_guard) or bool(c.news_restricted_eval)
        p2_news = bool(p2.enable_red_news_guard) or bool(c.news_restricted_eval)
        fn_news = bool(fn.enable_red_news_guard) or bool(c.news_restricted_funded)

        st_arrs = replay_cache.build_stage_tuple(
            capital_usd=float(c.capital_usd),
            p1_mult=float(p1.base_phase_mult),
            p1_lock_mult=float(p1.profit_lock_mult),
            p2_mult=float(p2.base_phase_mult),
            p2_lock_mult=float(p2.profit_lock_mult),
            funded_mult=fn_mult,
            amber_mult=amber_mult,
            red_mult=red_mult,
            p1_symcap=p1_symcap,
            p2_symcap=p2_symcap,
            fn_symcap=fn_symcap,
            profile_mode=prof_mode,
            p1_news=p1_news,
            p2_news=p2_news,
            fn_news=fn_news,
            friction_mult=fmult,
            steps=int(c.steps),
        )
        fn_diag, _, _, _, _ = replay_cache.get_exact_tier_stage(
            capital_usd=float(c.capital_usd),
            mult=fn_mult,
            symcap_pct=fn_symcap,
            profile_mode=prof_mode,
            use_red_news=fn_news,
            friction_mult=fmult,
        )
        sku_diags[cid] = {
            **fn_diag,
            "friction_mult": fmult,
            "funded_mult": fn_mult,
            "profile_mode": prof_mode,
            "holdout_rows_analysed": 0,
        }

        fee_orig = float(c.fee_orig_usd)
        fee_day0 = float(c.fee_promo_usd) if (use_promo_day0 and c.fee_promo_usd is not None) else fee_orig
        exec_tag = _contract_execution_tag(c)
        is_ftmo = c.firm_id.lower() == "ftmo"

        templates.append(
            {
                "contract_id": cid,
                "firm_idx": fidx,
                "firm_id": fid,
                "program_id": c.program_id,
                "display_name": c.display_name,
                "execution_status": exec_tag,
                "dd_anchor_tag": str(c.dd_anchor_tag),
                "steps": int(c.steps),
                "capital_usd": float(c.capital_usd),
                "fee_day0_usd": fee_day0,
                "fee_regular_usd": fee_orig,
                "fee_refund_pct": float(c.fee_refund_external_cash_frac),
                "fee_refund_hub_credit_frac": float(c.fee_refund_hub_credit_frac),
                "card_fx_fee_frac": float(c.card_fx_fee_frac),
                "payout_withdrawal_fee_pct": float(c.withdrawal_fee_frac),
                "withdrawal_fee_pct": float(c.withdrawal_fee_frac),
                "refund_withdrawal_fee_pct": 0.0 if is_ftmo else float(c.withdrawal_fee_frac),
                "p1_target_pct": float(c.p1_target_frac),
                "p2_target_pct": float(c.p2_target_frac),
                "dd_daily_pct": float(c.daily_loss_limit_frac),
                "dd_max_pct": float(c.static_loss_limit_frac),
                "dd_type": str(c.dd_type),
                "daily_dd_anchor": _daily_dd_anchor_from_ssot(c.daily_dd_anchor_mode),
                "best_day_cap_pct": 0.0,
                "min_trading_days": int(c.min_trading_days),
                "min_profitable_days": int(c.min_profitable_days),
                "min_profitable_day_pct": float(c.profitable_day_threshold_frac),
                "profit_split_pct": float(c.payout_split_frac),
                "profit_split_max_pct": float(c.payout_split_max_frac),
                "payout_cycle_trading_days": _cal_days_to_trading_days(int(c.payout_cycle_cal_days)),
                "min_payout_usd": float(c.min_payout_usd),
                "p1_lock_trigger": float(p1.profit_lock_trigger_of_target_frac),
                "p2_lock_trigger": float(p2.profit_lock_trigger_of_target_frac),
                "amber_dd": float(rp.amber_dd_frac),
                "red_dd": float(rp.red_dd_frac),
                "p1_ea_stop": float(p1.kill_daily_dd_frac),
                "p2_ea_stop": float(p2.kill_daily_dd_frac),
                "fn_ea_stop": float(fn.kill_daily_dd_frac),
                "p1_ea_static_stop": float(p1.kill_static_dd_frac),
                "p2_ea_static_stop": float(p2.kill_static_dd_frac),
                "fn_ea_static_stop": float(fn.kill_static_dd_frac),
                "refund_payout_milestone": _refund_milestone_code(c.fee_refund_milestone),
                "payout_buffer_retention_pct": 0.0,
                "locks_at_initial_after_first_payout": False,
                "min_payout_profit_pct": 0.0,
                "daily_profit_cap_pct": 0.0,
                "funded_first_payout_min_prof_days": 0,
                "funded_first_payout_prof_pct": 0.0,
                "stage_arrays": st_arrs,
            }
        )

    exec_statuses = sorted({str(t["execution_status"]) for t in templates})
    fleet_exec_status = (
        "TERMS_VERIFIED_EXECUTION_UNMEASURED"
        if "TERMS_VERIFIED_EXECUTION_UNMEASURED" in exec_statuses
        else "MEASURED_DEMO_EXECUTION"
    )
    meta = {
        "profile_id": pid,
        "friction_mult": fmult,
        "funded_mult": fn_mult,
        "amber_mult": amber_mult,
        "red_mult": red_mult,
        "p1_symcap_pct": p1_symcap,
        "p2_symcap_pct": p2_symcap,
        "fn_symcap_pct": fn_symcap,
        "use_promo_day0": bool(use_promo_day0),
        "pricing_regime": "MODEL_ASSUMPTION_PROMO_DAY0" if use_promo_day0 else "ALL_REGULAR_SSOT",
        "execution_status": fleet_exec_status,
        "contract_execution_statuses": {t["contract_id"]: t["execution_status"] for t in templates},
        "sku_funded_diagnostics": sku_diags,
        "n_firms": len(firms_seen),
        "firm_index_map": firms_seen,
    }
    return templates, meta


def audit_empirical_per_sku_lot_floor(
    replay_cache: ExactTierReplayCache,
    *,
    funded_mult: float = 1.25,
    fn_symcap_pct: float = 1.25,
    friction_mults: tuple[float, ...] = (1.00, 1.50),
    capitals_usd: tuple[float, ...] = ALL_SKU_AUDIT_CAPITALS_USD,
) -> dict[str, Any]:
    """Audit real M1 `0.01`-lot floor drag across `5K..200K` at `1.0x` and `1.5x` friction."""
    regimes: dict[str, dict[str, Any]] = {}
    for fm in friction_mults:
        fkey = f"{fm:.2f}x"
        skus: dict[str, dict[str, Any]] = {}
        for cap in capitals_usd:
            met, _, _, _, _ = replay_cache.get_exact_tier_stage(
                capital_usd=cap,
                mult=funded_mult,
                symcap_pct=fn_symcap_pct,
                profile_mode="Standard",
                use_red_news=True,
                friction_mult=fm,
            )
            lbl = f"{int(round(cap / 1000.0))}K"
            skus[lbl] = dict(met)
        ref_ann = float(skus.get("100K", {}).get("ann_pct", 0.0))
        for _lbl, r in skus.items():
            if abs(ref_ann) > 1e-9:
                r["drag_vs_100k_pct"] = round(100.0 * (float(r["ann_pct"]) - ref_ann) / abs(ref_ann), 3)
            else:
                r["drag_vs_100k_pct"] = 0.0
        regimes[fkey] = skus
    return {
        "holdout_rows_analysed": 0,
        "resolution_label_vi": RESOLUTION_LABEL_VI,
        "resolution_tag": RESOLUTION_TAG,
        "funded_mult": float(funded_mult),
        "fn_symcap_pct": float(fn_symcap_pct),
        "reference_sku": "100K",
        "regimes": regimes,
    }


# ---------------------------------------------------------------------------
# 3. Core 81-Case Shared-Path Execution + Capital Curve Honesty Enrichment
# ---------------------------------------------------------------------------


def _enrich_case_capital_honesty(case: dict[str, Any], *, friction_mult: float) -> dict[str, Any]:
    """Attach explicit Capital Curve Honesty & Own-Book Crossover fields (zero notional double-count)."""
    fx = float(case["usd_vnd_rate"])
    bank_usd = float(case["bankroll_usd"])
    bank_vnd = float(case["bankroll_vnd"])
    own_book_usd = float(case["mean_own_book_36m_usd"])
    recoup_usd = float(case["mean_recoup_cash_36m_usd"])
    ch_cash_usd = float(case["mean_challenge_cash_36m_usd"])
    mean_wealth_usd = float(case["mean_wealth_36m_usd"])
    mean_max_base_fn = float(case["mean_max_base_funded_usd"])
    max_base_fn = float(case["max_active_base_funded_usd"])
    max_scaled_fn = float(case["max_active_scaled_funded_usd"])
    mean_fees_annual_usd = float(case["mean_total_fees_36m_usd"]) / 3.0

    # Honest Prop -> Own-Book crossover check using actual simulated Own-Book equity & active Prop notional
    crossover = compute_prop_own_crossover(
        own_book_equity_usd=own_book_usd,
        active_prop_nominal_usd=mean_max_base_fn,
        annual_prop_fees_usd=mean_fees_annual_usd,
        usd_vnd_rate=fx,
    )

    # Liquid net worth strictly equals liquid buckets (Challenge Cash + Recoup Cash + Own-Book),
    # NEVER includes active Prop Funded notional!
    liquid_buckets_sum_usd = round(ch_cash_usd + recoup_usd + own_book_usd, 2)
    liquid_median_36m_usd = round(bank_usd + float(case["median_36m_net_usd"]), 2)
    liquid_median_36m_vnd = round(bank_vnd + float(case["median_36m_net_vnd"]), 0)

    case["friction_mult"] = round(float(friction_mult), 3)
    case["capital_curve_honesty"] = {
        "notional_double_counted": False,
        "initial_bankroll_usd": round(bank_usd, 2),
        "initial_bankroll_vnd": round(bank_vnd, 0),
        "liquid_cash_net_worth_36m_median_usd": liquid_median_36m_usd,
        "liquid_cash_net_worth_36m_median_vnd": liquid_median_36m_vnd,
        "liquid_cash_net_worth_36m_mean_usd": round(mean_wealth_usd, 2),
        "liquid_cash_net_worth_36m_mean_vnd": round(mean_wealth_usd * fx, 0),
        "liquid_buckets_sum_36m_mean_usd": liquid_buckets_sum_usd,
        "challenge_cash_36m_mean_usd": round(ch_cash_usd, 2),
        "recoup_cash_36m_mean_usd": round(recoup_usd, 2),
        "own_book_equity_36m_mean_usd": round(own_book_usd, 2),
        "own_book_equity_36m_mean_vnd": round(own_book_usd * fx, 0),
        "active_funded_notional_mean_max_usd": round(mean_max_base_fn, 2),
        "active_funded_notional_cap_max_base_usd": round(max_base_fn, 2),
        "active_funded_notional_cap_max_scaled_usd": round(max_scaled_fn, 2),
        "notional_disclosure_tag": "PROP_NOTIONAL_SEPARATED_NOT_LIQUID_CASH",
        "own_book_crossover": crossover,
    }
    return case


def run_templates_grid(
    *,
    templates: list[dict[str, Any]],
    tpl_meta: dict[str, Any],
    usd_vnd_rate: float,
    idx_matrix: np.ndarray,
    hazard_days: np.ndarray,
    bankroll_tiers_m_vnd: tuple[int, ...] = BANKROLL_TIERS_M_VND,
    concurrency_modes: tuple[ConcurrencyMode, ...] = CONCURRENCY_MODES,
    allocation_policies: tuple[AllocationPolicy, ...] = ALLOCATION_POLICIES,
    eval_fail_cooldown_days: int = DEFAULT_EVAL_FAIL_COOLDOWN_DAYS,
    funded_dd_freeze_frac: float = DEFAULT_FUNDED_DD_FREEZE_FRAC,
    enable_scaling_plan: bool = True,
    own_book_daily_ret: float = 0.0,
    max_slots: int = DEFAULT_MAX_SLOTS,
    friction_mult: float = DEFAULT_BASELINE_FRICTION,
    max_active_funded_usd: float = FTMO_MAX_ACTIVE_FUNDED_USD,
    max_single_challenge_usd: float = FTMO_MAX_SINGLE_CHALLENGE_USD,
    max_scaled_funded_usd: float = FTMO_MAX_SCALED_FUNDED_USD,
) -> tuple[list[dict[str, Any]], dict[str, list[str]], list[str], float]:
    """Run `_simulate_wave4_pareto_fleet_numba` over all configs on pre-built empirical templates."""
    n_paths, horizon_days = idx_matrix.shape
    ladder_order = sorted(range(len(templates)), key=lambda idx: (templates[idx]["capital_usd"], idx))
    ladder_tpls = np.ascontiguousarray(ladder_order, dtype=np.int32)
    packed = _pack_templates_for_numba(templates)

    tpl_card_fx = np.ascontiguousarray([float(t["card_fx_fee_frac"]) for t in templates], dtype=np.float64)
    tpl_split_max = np.ascontiguousarray([float(t["profit_split_max_pct"]) for t in templates], dtype=np.float64)
    tpl_p1_st = np.ascontiguousarray([float(t["p1_ea_static_stop"]) for t in templates], dtype=np.float64)
    tpl_p2_st = np.ascontiguousarray([float(t["p2_ea_static_stop"]) for t in templates], dtype=np.float64)
    tpl_fn_st = np.ascontiguousarray([float(t["fn_ea_static_stop"]) for t in templates], dtype=np.float64)

    n_firms = max(1, int(tpl_meta["n_firms"]))
    firm_max_funded = np.full(n_firms, float(max_active_funded_usd), dtype=np.float64)
    firm_max_single = np.full(n_firms, float(max_single_challenge_usd), dtype=np.float64)
    firm_max_scaled = np.full(n_firms, float(max_scaled_funded_usd), dtype=np.float64)

    configs = build_81_case_configs(
        usd_vnd_rate=usd_vnd_rate,
        bankroll_tiers_m_vnd=bankroll_tiers_m_vnd,
        concurrency_modes=concurrency_modes,
        allocation_policies=allocation_policies,
    )

    ref_ticket_usd = float(templates[ladder_order[0]]["fee_regular_usd"]) * (
        1.0 + float(templates[ladder_order[0]]["card_fx_fee_frac"])
    )
    ref_cid = (
        "ftmo_standard_100k"
        if "ftmo_standard_100k" in tpl_meta["sku_funded_diagnostics"]
        else templates[-1]["contract_id"]
    )
    ref_strategy_quality = tpl_meta["sku_funded_diagnostics"][ref_cid]

    t_sim0 = time.perf_counter()
    cases_out: list[dict[str, Any]] = []
    for cfg in configs:
        spec = ALLOCATION_POLICY_SPECS[cfg.allocation_policy]
        raw_res = _simulate_wave4_pareto_fleet_numba(
            idx_matrix,
            hazard_days,
            *packed,
            tpl_card_fx,
            tpl_split_max,
            tpl_p1_st,
            tpl_p2_st,
            tpl_fn_st,
            firm_max_funded,
            firm_max_single,
            firm_max_scaled,
            ladder_tpls,
            _CONCURRENCY_CODE[cfg.concurrency_mode],
            _ALLOCATION_CODE[cfg.allocation_policy],
            cfg.bankroll_usd,
            max_slots,
            eval_fail_cooldown_days,
            funded_dd_freeze_frac,
            bool(enable_scaling_plan),
            own_book_daily_ret,
            spec.reserve_cap_tickets,
            spec.cash_recoup_pct,
            spec.upgrade_scale_pct,
            spec.own_book_pct,
        )
        case_summary = summarize_pareto_case(
            cfg,
            raw_res,
            horizon_days=horizon_days,
            execution_status=str(tpl_meta["execution_status"]),
            pricing_regime=str(tpl_meta["pricing_regime"]),
            reference_ticket_usd=ref_ticket_usd,
            strategy_quality=ref_strategy_quality,
        )
        _enrich_case_capital_honesty(case_summary, friction_mult=friction_mult)
        cases_out.append(case_summary)
    sim_elapsed = time.perf_counter() - t_sim0

    pareto_by_tier: dict[str, list[str]] = {}
    for tm in bankroll_tiers_m_vnd:
        tier_cases = [c for c in cases_out if int(c["bankroll_m_vnd"]) == int(tm)]
        tier_front = extract_pareto_frontier(tier_cases)
        tier_ids = {c["case_id"] for c in tier_front}
        for c in tier_cases:
            c["is_pareto_in_tier"] = c["case_id"] in tier_ids
        pareto_by_tier[f"{tm}M_VND"] = [c["case_id"] for c in tier_front]

    overall_front = extract_pareto_frontier(cases_out)
    overall_ids = {c["case_id"] for c in overall_front}
    for c in cases_out:
        c["is_pareto_overall"] = c["case_id"] in overall_ids

    if len(cases_out) != len(configs) or n_paths <= 0:
        raise RuntimeError(f"INTERNAL_GRID_MISMATCH: expected {len(configs)} cases, got {len(cases_out)}")

    return cases_out, pareto_by_tier, [c["case_id"] for c in overall_front], sim_elapsed


# ---------------------------------------------------------------------------
# 4. Strict Fail-Closed Invariant Verifier (ZERO Bare Asserts [ARCH-02])
# ---------------------------------------------------------------------------


def verify_pareto_cases_invariants(
    cases: list[dict[str, Any]],
    *,
    expected_count: int | None = None,
    expected_n_paths: int | None = None,
    max_active_base_funded_usd: float = FTMO_MAX_ACTIVE_FUNDED_USD,
    max_active_scaled_funded_usd: float = FTMO_MAX_SCALED_FUNDED_USD,
    sum_tol: float = 1e-6,
    accounting_tol_usd: float = 1e-5,
) -> dict[str, Any]:
    """Fail-closed verifier over all Pareto cases (100%-sum, zero notional double-count, Holdout==0)."""
    if expected_count is not None and len(cases) != expected_count:
        raise ValueError(f"CASE_COUNT_MISMATCH: expected {expected_count}, got {len(cases)}")
    if not cases:
        raise ValueError("EMPTY_CASES: cannot verify empty Pareto case list")

    max_sum_err = 0.0
    max_acc_err = 0.0
    max_base_fn = 0.0
    max_scaled_fn = 0.0
    seen_ids: set[str] = set()

    for c in cases:
        cid = str(c.get("case_id", ""))
        if not cid or cid in seen_ids:
            raise ValueError(f"DUPLICATE_OR_EMPTY_CASE_ID: {cid!r}")
        seen_ids.add(cid)

        ho = c.get("holdout_rows_analysed")
        if isinstance(ho, bool) or ho != 0:
            raise ValueError(f"HOLDOUT_VIOLATION in {cid}: holdout_rows_analysed={ho!r}")
        osc = c.get("order_send_count")
        if isinstance(osc, bool) or osc != 0:
            raise ValueError(f"ORDER_SEND_VIOLATION in {cid}: order_send_count={osc!r}")
        if expected_n_paths is not None and int(c.get("n_paths", -1)) != expected_n_paths:
            raise ValueError(f"N_PATHS_MISMATCH in {cid}: expected {expected_n_paths}, got {c.get('n_paths')}")

        if c.get("resolution_label_vi") != RESOLUTION_LABEL_VI or c.get("resolution_tag") != RESOLUTION_TAG:
            raise ValueError(
                f"MISSING_RESOLUTION_LABEL in {cid}: "
                f"{c.get('resolution_label_vi')!r} / {c.get('resolution_tag')!r}"
            )

        acc_err = _require_finite_float(c.get("max_cash_accounting_err_usd"), f"{cid}.max_cash_accounting_err_usd")
        if acc_err > accounting_tol_usd:
            raise ValueError(f"CASH_ACCOUNTING_ERROR in {cid}: {acc_err} > {accounting_tol_usd}")
        if acc_err > max_acc_err:
            max_acc_err = acc_err

        base_fn = _require_finite_float(c.get("max_active_base_funded_usd"), f"{cid}.max_active_base_funded_usd")
        if base_fn > max_active_base_funded_usd + 1e-6:
            raise ValueError(f"FTMO_400K_CAP_BREACH in {cid}: max_active_base_funded_usd={base_fn}")
        if base_fn > max_base_fn:
            max_base_fn = base_fn

        sc_fn = _require_finite_float(c.get("max_active_scaled_funded_usd"), f"{cid}.max_active_scaled_funded_usd")
        if sc_fn > max_active_scaled_funded_usd + 1e-6:
            raise ValueError(f"FTMO_2M_SCALED_CAP_BREACH in {cid}: max_active_scaled_funded_usd={sc_fn}")
        if sc_fn > max_scaled_fn:
            max_scaled_fn = sc_fn

        # Verify liquid wealth strictly equals sum of liquid cash/own-book buckets (no Funded notional double-count!)
        ch_c = _require_finite_float(c.get("mean_challenge_cash_36m_usd"), f"{cid}.mean_challenge_cash_36m_usd")
        rc_c = _require_finite_float(c.get("mean_recoup_cash_36m_usd"), f"{cid}.mean_recoup_cash_36m_usd")
        ob_c = _require_finite_float(c.get("mean_own_book_36m_usd"), f"{cid}.mean_own_book_36m_usd")
        mw_c = _require_finite_float(c.get("mean_wealth_36m_usd"), f"{cid}.mean_wealth_36m_usd")
        if abs((ch_c + rc_c + ob_c) - mw_c) > 0.05:
            raise ValueError(
                f"LIQUID_NET_WORTH_DOUBLE_COUNT in {cid}: "
                f"buckets={ch_c + rc_c + ob_c:.2f} vs mean_wealth_36m={mw_c:.2f}"
            )
        hon = c.get("capital_curve_honesty")
        if isinstance(hon, dict) and hon.get("notional_double_counted") is not False:
            raise ValueError(f"CAPITAL_CURVE_HONESTY_FLAG_INVALID in {cid}")

        # Verify exact Pass + Fail + Pending == 100.0% across ALL 5 horizons (3m/6m/12m/24m/36m)
        for map_key in ("monthly_pass_fail_pending", "first_ticket_pass_fail_pending"):
            hmap = c.get(map_key)
            if not isinstance(hmap, dict):
                raise ValueError(f"MISSING_HORIZON_MAP in {cid}: {map_key}")
            for m in HORIZON_MONTHS:
                hkey = f"{m}m"
                if hkey not in hmap:
                    raise ValueError(f"MISSING_HORIZON_KEY in {cid}.{map_key}: {hkey}")
                part = hmap[hkey]
                p_v = _require_finite_float(part.get("pass_pct"), f"{cid}.{map_key}.{hkey}.pass_pct", min_val=0.0)
                f_v = _require_finite_float(part.get("fail_pct"), f"{cid}.{map_key}.{hkey}.fail_pct", min_val=0.0)
                w_v = _require_finite_float(part.get("pending_pct"), f"{cid}.{map_key}.{hkey}.pending_pct", min_val=0.0)
                err = abs((p_v + f_v + w_v) - 100.0)
                if err > sum_tol:
                    raise ValueError(
                        f"PARTITION_SUM_VIOLATION in {cid}.{map_key}.{hkey}: "
                        f"{p_v} + {f_v} + {w_v} = {p_v + f_v + w_v} (err={err})"
                    )
                if err > max_sum_err:
                    max_sum_err = err

        # Verify Wilson 95% UB >= point estimate
        fn12 = c.get("funded_12m_blowup") or {}
        br12 = _require_finite_float(fn12.get("blowup_12m_pct"), f"{cid}.blowup_12m_pct", min_val=0.0)
        wub = _require_finite_float(fn12.get("wilson_95_ub_pct"), f"{cid}.wilson_95_ub_pct", min_val=0.0)
        if wub < br12 - 1e-6:
            raise ValueError(f"WILSON_UB_LT_POINT in {cid}: wilson={wub} < blowup={br12}")

    return {
        "status": "PASS",
        "cases_verified": len(cases),
        "max_partition_sum_err_pct": max_sum_err,
        "max_cash_accounting_err_usd": max_acc_err,
        "max_active_base_funded_usd": round(max_base_fn, 2),
        "max_active_scaled_funded_usd": round(max_scaled_fn, 2),
        "holdout_rows_analysed": 0,
        "order_send_count": 0,
        "notional_double_counted": False,
    }


# ---------------------------------------------------------------------------
# 5. Per-Tier Pareto Highlights & Global Sweet-Spot / Inflection Analysis
# ---------------------------------------------------------------------------


def _compact_case_snapshot(c: dict[str, Any], stress_c: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build a compact, complete Law 13–15 snapshot of one case for summary & Explorer HTML."""
    hon = c.get("capital_curve_honesty") or {}
    xo = hon.get("own_book_crossover") or {}
    fn12 = c.get("funded_12m_blowup") or {}
    snap: dict[str, Any] = {
        "case_id": c["case_id"],
        "bankroll_m_vnd": int(c["bankroll_m_vnd"]),
        "bankroll_usd": float(c["bankroll_usd"]),
        "concurrency_mode": str(c["concurrency_mode"]),
        "allocation_policy": str(c["allocation_policy"]),
        "is_pareto_in_tier": bool(c["is_pareto_in_tier"]),
        "is_pareto_overall": bool(c["is_pareto_overall"]),
        "resolution_label_vi": str(c["resolution_label_vi"]),
        "resolution_tag": str(c["resolution_tag"]),
        "execution_status": str(c["execution_status"]),
        "monthly_pass_fail_pending": c["monthly_pass_fail_pending"],
        "net_profit_24m_usd": c["net_profit_24m_usd"],
        "net_profit_24m_vnd": c["net_profit_24m_vnd"],
        "net_profit_36m_usd": c["net_profit_36m_usd"],
        "net_profit_36m_vnd": c["net_profit_36m_vnd"],
        "p_net_le_0_24m_pct": float(c["p_net_le_0_24m_pct"]),
        "p_net_le_0_36m_pct": float(c["p_net_le_0_36m_pct"]),
        "p_bankroll_ruin_24m_pct": float(c["p_bankroll_ruin_24m_pct"]),
        "p_bankroll_ruin_pct": float(c["p_bankroll_ruin_pct"]),
        "ev_per_1_vnd_fee_24m": float(c["ev_per_1_vnd_fee_24m"]),
        "ev_per_1_vnd_fee_36m": float(c["ev_per_1_vnd_fee_36m"]),
        "mean_total_fees_36m_usd": float(c["mean_total_fees_36m_usd"]),
        "mean_total_fees_36m_vnd": float(c["mean_total_fees_36m_vnd"]),
        "uncond_med_pay1_cal_days_cap365": float(c["uncond_med_pay1_cal_days_cap365"]),
        "uncond_med_pay1_cal_days_cap730": float(c["uncond_med_pay1_cal_days_cap730"]),
        "cond_med_pay1_cal_days": float(c["cond_med_pay1_cal_days"]),
        "funded_12m_blowup_pct": float(fn12.get("blowup_12m_pct", 0.0)),
        "funded_12m_wilson_95_ub_pct": float(fn12.get("wilson_95_ub_pct", 100.0)),
        "bot_auto_kill_pct": float(c["bot_auto_kill_pct"]),
        "firm_hard_breach_pct": float(c["firm_hard_breach_pct"]),
        "funded_dry_months_pct": float(c["funded_dry_months_pct"]),
        "longest_starved_month_streak_p50": int(c["longest_starved_month_streak_p50"]),
        "longest_starved_month_streak_p95": int(c["longest_starved_month_streak_p95"]),
        "longest_starved_month_streak_max": int(c["longest_starved_month_streak_max"]),
        "mean_own_book_36m_usd": float(c["mean_own_book_36m_usd"]),
        "mean_recoup_cash_36m_usd": float(c["mean_recoup_cash_36m_usd"]),
        "mean_challenge_cash_36m_usd": float(c["mean_challenge_cash_36m_usd"]),
        "mean_wealth_36m_usd": float(c["mean_wealth_36m_usd"]),
        "max_active_base_funded_usd": float(c["max_active_base_funded_usd"]),
        "mean_max_base_funded_usd": float(c["mean_max_base_funded_usd"]),
        "max_active_scaled_funded_usd": float(c["max_active_scaled_funded_usd"]),
        "mean_scaling_upgrades": float(c["mean_scaling_upgrades"]),
        "own_book_crossover_phase": str(xo.get("recommended_phase", "")),
        "own_book_crossover_progress_pct": float(xo.get("crossover_progress_pct", 0.0)),
        "own_book_beats_prop": bool(xo.get("own_book_beats_prop", False)),
        "law15_grade_code": str((c.get("law15_position") or {}).get("grade_code", "")),
        "law15_grade_vi": str((c.get("law15_position") or {}).get("grade_vi", "")),
    }
    if stress_c is not None:
        snap["stress_1_5x"] = {
            "median_24m_net_vnd": float(stress_c["median_24m_net_vnd"]),
            "median_36m_net_vnd": float(stress_c["median_36m_net_vnd"]),
            "mean_36m_net_vnd": float(stress_c["mean_36m_net_vnd"]),
            "p_net_le_0_24m_pct": float(stress_c["p_net_le_0_24m_pct"]),
            "p_net_le_0_36m_pct": float(stress_c["p_net_le_0_36m_pct"]),
            "p_bankroll_ruin_pct": float(stress_c["p_bankroll_ruin_pct"]),
            "ev_per_1_vnd_fee_36m": float(stress_c["ev_per_1_vnd_fee_36m"]),
            "funded_12m_blowup_pct": float((stress_c.get("funded_12m_blowup") or {}).get("blowup_12m_pct", 0.0)),
            "uncond_med_pay1_cal_days_cap730": float(stress_c["uncond_med_pay1_cal_days_cap730"]),
        }
    return snap


def extract_sweet_spots_and_inflections(
    cases_base: list[dict[str, Any]],
    cases_stress: list[dict[str, Any]] | None = None,
    *,
    bankroll_tiers_m_vnd: tuple[int, ...] = BANKROLL_TIERS_M_VND,
) -> dict[str, Any]:
    """Extract Per-Tier Pareto Highlights and Global Sweet-Spot / Inflection Points."""
    stress_by_id = {c["case_id"]: c for c in (cases_stress or [])}
    tier_highlights: dict[str, dict[str, Any]] = {}

    for tm in bankroll_tiers_m_vnd:
        tier_cases = [c for c in cases_base if int(c["bankroll_m_vnd"]) == int(tm)]
        if not tier_cases:
            continue
        pareto_front = extract_pareto_frontier(tier_cases)
        if not pareto_front:
            pareto_front = tier_cases

        safest = min(
            pareto_front,
            key=lambda c: (
                float(c["p_bankroll_ruin_pct"]),
                float(c["p_net_le_0_36m_pct"]),
                -float(c["median_36m_net_vnd"]),
                str(c["case_id"]),
            ),
        )
        max_upside = max(
            pareto_front,
            key=lambda c: (
                float(c["median_36m_net_vnd"]),
                -float(c["p_bankroll_ruin_pct"]),
                -float(c["p_net_le_0_36m_pct"]),
            ),
        )
        min_ruin = float(safest["p_bankroll_ruin_pct"])
        min_neg = min(float(c["p_net_le_0_36m_pct"]) for c in pareto_front)
        balanced_pool = [
            c
            for c in pareto_front
            if float(c["p_bankroll_ruin_pct"]) <= min_ruin + 2.0 + 1e-9
            and float(c["p_net_le_0_36m_pct"]) <= min_neg + 3.0 + 1e-9
        ]
        balanced = max(
            balanced_pool or [safest],
            key=lambda c: (
                float(c["median_36m_net_vnd"]),
                -float(c["p_bankroll_ruin_pct"]),
                -float(c["p_net_le_0_36m_pct"]),
            ),
        )

        tier_highlights[f"{tm}M_VND"] = {
            "bankroll_m_vnd": int(tm),
            "bankroll_usd": float(tier_cases[0]["bankroll_usd"]),
            "pareto_count": len(pareto_front),
            "pareto_case_ids": [c["case_id"] for c in pareto_front],
            "safest": _compact_case_snapshot(safest, stress_by_id.get(safest["case_id"])),
            "balanced_sweet_spot": _compact_case_snapshot(balanced, stress_by_id.get(balanced["case_id"])),
            "max_upside": _compact_case_snapshot(max_upside, stress_by_id.get(max_upside["case_id"])),
        }

    # Global Inflection 1: Minimum bankroll where P(ruin) < 1%
    ruin_lt_1 = [c for c in cases_base if float(c["p_bankroll_ruin_pct"]) < 1.0]
    min_tier_ruin_lt_1 = min((int(c["bankroll_m_vnd"]) for c in ruin_lt_1), default=None)
    best_at_ruin_lt_1 = (
        max(
            [c for c in ruin_lt_1 if int(c["bankroll_m_vnd"]) == min_tier_ruin_lt_1],
            key=lambda c: (float(c["median_36m_net_vnd"]), -float(c["p_net_le_0_24m_pct"])),
        )
        if min_tier_ruin_lt_1 is not None
        else None
    )

    # Global Inflection 2: Minimum bankroll where P(ruin) < 1% AND P(net <= 0 at 24m) < 15%
    dual_safe = [
        c
        for c in cases_base
        if float(c["p_bankroll_ruin_pct"]) < 1.0 and float(c["p_net_le_0_24m_pct"]) < 15.0
    ]
    min_tier_dual_safe = min((int(c["bankroll_m_vnd"]) for c in dual_safe), default=None)
    best_at_dual_safe = (
        max(
            [c for c in dual_safe if int(c["bankroll_m_vnd"]) == min_tier_dual_safe],
            key=lambda c: (float(c["median_36m_net_vnd"]), -float(c["p_net_le_0_24m_pct"])),
        )
        if min_tier_dual_safe is not None
        else None
    )
    closest_neg24 = min(
        cases_base,
        key=lambda c: (float(c["p_net_le_0_24m_pct"]), float(c["p_bankroll_ruin_pct"]), int(c["bankroll_m_vnd"])),
    )

    # Global Inflection 3: Minimum bankroll where median net profit > 0 at 24m and 36m (1.0x & 1.5x)
    pos_med_24 = [c for c in cases_base if float(c["median_24m_net_vnd"]) > 0.0]
    pos_med_36 = [c for c in cases_base if float(c["median_36m_net_vnd"]) > 0.0]
    min_tier_pos_med_24 = min((int(c["bankroll_m_vnd"]) for c in pos_med_24), default=None)
    min_tier_pos_med_36 = min((int(c["bankroll_m_vnd"]) for c in pos_med_36), default=None)

    pos_med_36_stress = [c for c in (cases_stress or []) if float(c["median_36m_net_vnd"]) > 0.0]
    min_tier_pos_med_36_stress = min((int(c["bankroll_m_vnd"]) for c in pos_med_36_stress), default=None)

    # Global Inflection 4: Own-Book Crossover thresholds (Phase 3 Hybrid Barbell & Phase 4 Own-Book Dominant)
    phase3_cases = [
        c
        for c in cases_base
        if str(
            ((c.get("capital_curve_honesty") or {}).get("own_book_crossover") or {}).get("recommended_phase", "")
        )
        in ("PHASE_3_HYBRID_BARBELL", "PHASE_4_OWN_BOOK_DOMINANT")
    ]
    phase4_cases = [
        c
        for c in cases_base
        if str(
            ((c.get("capital_curve_honesty") or {}).get("own_book_crossover") or {}).get("recommended_phase", "")
        )
        == "PHASE_4_OWN_BOOK_DOMINANT"
    ]
    min_tier_phase3 = min((int(c["bankroll_m_vnd"]) for c in phase3_cases), default=None)
    best_phase3 = (
        max(
            [c for c in phase3_cases if int(c["bankroll_m_vnd"]) == min_tier_phase3],
            key=lambda c: (float(c["mean_own_book_36m_usd"]), float(c["median_36m_net_vnd"])),
        )
        if min_tier_phase3 is not None
        else None
    )
    min_tier_phase4 = min((int(c["bankroll_m_vnd"]) for c in phase4_cases), default=None)
    best_phase4 = (
        max(
            [c for c in phase4_cases if int(c["bankroll_m_vnd"]) == min_tier_phase4],
            key=lambda c: (float(c["mean_own_book_36m_usd"]), float(c["median_36m_net_vnd"])),
        )
        if min_tier_phase4 is not None
        else None
    )
    max_own_book_case = max(cases_base, key=lambda c: float(c["mean_own_book_36m_usd"]))

    # Global Inflection 5: Marginal 36m median net gain per +10M VND bankroll (detect $400K cap saturation)
    tier_curve: list[dict[str, Any]] = []
    prev_tm: int | None = None
    prev_med: float | None = None
    peak_marginal_per_10m: float = 0.0
    for tm in sorted(bankroll_tiers_m_vnd):
        hk = f"{tm}M_VND"
        if hk not in tier_highlights:
            continue
        bal_snap = tier_highlights[hk]["balanced_sweet_spot"]
        med_vnd = float(bal_snap["net_profit_36m_vnd"]["median"])
        marg_per_10m: float | None = None
        if prev_tm is not None and prev_med is not None and tm > prev_tm:
            marg_per_10m = round(((med_vnd - prev_med) / float(tm - prev_tm)) * 10.0, 0)
            if marg_per_10m > peak_marginal_per_10m:
                peak_marginal_per_10m = marg_per_10m
        tier_curve.append(
            {
                "bankroll_m_vnd": int(tm),
                "balanced_case_id": bal_snap["case_id"],
                "median_36m_net_m_vnd": round(med_vnd / 1_000_000.0, 2),
                "p_bankroll_ruin_pct": bal_snap["p_bankroll_ruin_pct"],
                "p_net_le_0_24m_pct": bal_snap["p_net_le_0_24m_pct"],
                "p_net_le_0_36m_pct": bal_snap["p_net_le_0_36m_pct"],
                "ev_per_1_vnd_fee_36m": bal_snap["ev_per_1_vnd_fee_36m"],
                "mean_max_base_funded_usd": bal_snap["mean_max_base_funded_usd"],
                "mean_own_book_36m_usd": bal_snap["mean_own_book_36m_usd"],
                "marginal_median_36m_vnd_per_10m_bankroll": marg_per_10m,
            }
        )
        prev_tm = int(tm)
        prev_med = med_vnd

    diminishing_tier: int | None = None
    seen_peak = False
    for row in tier_curve:
        mv = row["marginal_median_36m_vnd_per_10m_bankroll"]
        if mv is None:
            continue
        if peak_marginal_per_10m > 0.0 and mv >= peak_marginal_per_10m - 1e-6:
            seen_peak = True
        elif seen_peak and peak_marginal_per_10m > 0.0 and mv < 0.35 * peak_marginal_per_10m:
            diminishing_tier = int(row["bankroll_m_vnd"])
            break

    # Stress 1.5x resilience summary across balanced tier sweet spots
    stress_summary_rows: list[dict[str, Any]] = []
    if cases_stress:
        for tm in sorted(bankroll_tiers_m_vnd):
            hk = f"{tm}M_VND"
            if hk not in tier_highlights:
                continue
            b_snap = tier_highlights[hk]["balanced_sweet_spot"]
            sc = stress_by_id.get(b_snap["case_id"])
            if sc is None:
                continue
            base_med_m = round(float(b_snap["net_profit_36m_vnd"]["median"]) / 1_000_000.0, 2)
            str_med_m = round(float(sc["median_36m_net_vnd"]) / 1_000_000.0, 2)
            stress_summary_rows.append(
                {
                    "bankroll_m_vnd": int(tm),
                    "case_id": b_snap["case_id"],
                    "base_1_0x_median_36m_m_vnd": base_med_m,
                    "stress_1_5x_median_36m_m_vnd": str_med_m,
                    "delta_median_36m_m_vnd": round(str_med_m - base_med_m, 2),
                    "base_1_0x_p_net_le_0_36m_pct": float(b_snap["p_net_le_0_36m_pct"]),
                    "stress_1_5x_p_net_le_0_36m_pct": float(sc["p_net_le_0_36m_pct"]),
                    "base_1_0x_p_ruin_pct": float(b_snap["p_bankroll_ruin_pct"]),
                    "stress_1_5x_p_ruin_pct": float(sc["p_bankroll_ruin_pct"]),
                    "base_1_0x_ev_per_fee_36m": float(b_snap["ev_per_1_vnd_fee_36m"]),
                    "stress_1_5x_ev_per_fee_36m": float(sc["ev_per_1_vnd_fee_36m"]),
                    "median_stays_positive_at_1_5x": bool(str_med_m > 0.0),
                }
            )

    global_sweet_spots = {
        "min_bankroll_ruin_lt_1pct_m_vnd": min_tier_ruin_lt_1,
        "best_config_at_ruin_lt_1pct": (
            _compact_case_snapshot(best_at_ruin_lt_1, stress_by_id.get(best_at_ruin_lt_1["case_id"]))
            if best_at_ruin_lt_1 is not None
            else None
        ),
        "min_bankroll_ruin_lt_1pct_and_neg24m_lt_15pct_m_vnd": min_tier_dual_safe,
        "best_config_at_ruin_lt_1pct_and_neg24m_lt_15pct": (
            _compact_case_snapshot(best_at_dual_safe, stress_by_id.get(best_at_dual_safe["case_id"]))
            if best_at_dual_safe is not None
            else None
        ),
        "lowest_p_net_le_0_24m_achieved": {
            "case_id": closest_neg24["case_id"],
            "bankroll_m_vnd": int(closest_neg24["bankroll_m_vnd"]),
            "p_net_le_0_24m_pct": float(closest_neg24["p_net_le_0_24m_pct"]),
            "p_bankroll_ruin_pct": float(closest_neg24["p_bankroll_ruin_pct"]),
            "median_24m_net_vnd": float(closest_neg24["median_24m_net_vnd"]),
            "median_36m_net_vnd": float(closest_neg24["median_36m_net_vnd"]),
        },
        "min_bankroll_positive_median_24m_m_vnd": min_tier_pos_med_24,
        "min_bankroll_positive_median_36m_m_vnd": min_tier_pos_med_36,
        "min_bankroll_positive_median_36m_stress_1_5x_m_vnd": min_tier_pos_med_36_stress,
        "own_book_crossover_inflection": {
            "min_bankroll_phase3_hybrid_barbell_m_vnd": min_tier_phase3,
            "best_phase3_config": (
                _compact_case_snapshot(best_phase3, stress_by_id.get(best_phase3["case_id"]))
                if best_phase3 is not None
                else None
            ),
            "min_bankroll_phase4_own_book_dominant_m_vnd": min_tier_phase4,
            "best_phase4_config": (
                _compact_case_snapshot(best_phase4, stress_by_id.get(best_phase4["case_id"]))
                if best_phase4 is not None
                else None
            ),
            "highest_mean_own_book_36m_case": {
                "case_id": max_own_book_case["case_id"],
                "bankroll_m_vnd": int(max_own_book_case["bankroll_m_vnd"]),
                "mean_own_book_36m_usd": float(max_own_book_case["mean_own_book_36m_usd"]),
                "mean_own_book_36m_vnd": round(
                    float(max_own_book_case["mean_own_book_36m_usd"]) * float(max_own_book_case["usd_vnd_rate"]), 0
                ),
                "crossover": (max_own_book_case.get("capital_curve_honesty") or {}).get("own_book_crossover"),
            },
        },
        "diminishing_returns_400k_cap_inflection_m_vnd": diminishing_tier,
        "capital_curve_by_tier": tier_curve,
    }

    return {
        "tier_pareto_highlights": tier_highlights,
        "global_sweet_spots": global_sweet_spots,
        "stress_1_5x_summary": {
            "friction_mult": DEFAULT_STRESS_FRICTION,
            "n_cases_compared": len(stress_summary_rows),
            "n_tier_sweet_spots_positive_median_at_1_5x": sum(
                1 for r in stress_summary_rows if r["median_stays_positive_at_1_5x"]
            ),
            "tier_comparison_rows": stress_summary_rows,
        },
    }


# ---------------------------------------------------------------------------
# 6. Full Production Orchestrator (`81` Cases x `N = 10,000` x `36m` + `1.5x` Stress)
# ---------------------------------------------------------------------------


def run_production_pareto_81cases(
    *,
    n_paths: int = DEFAULT_PRODUCTION_N_PATHS,
    horizon_days: int = DEFAULT_HORIZON_DAYS,
    block_len: int = BLOCK_LEN,
    seed: int = DEFAULT_SEED,
    baseline_friction: float = DEFAULT_BASELINE_FRICTION,
    stress_friction: float = DEFAULT_STRESS_FRICTION,
    include_stress: bool = True,
    include_the5ers_ref: bool = True,
    profile_id: str | None = None,
    use_promo_day0: bool = False,
    annual_firm_hazard_rate: float = 0.0,
    prefer_x13: bool = False,
    offline_no_probe: bool = False,
    tapes_dir: Path = DEFAULT_DERIVED_TAPES_DIR,
    tapes_stem: str = DEFAULT_DERIVED_TAPES_STEM,
    firms_catalog_path: Path = DEFAULT_FIRMS_CATALOG_PATH,
    fx_rates_path: Path = DEFAULT_FX_RATES_PATH,
    risk_profiles_path: Path = DEFAULT_RISK_PROFILES_PATH,
    full_out_path: Path | None = DEFAULT_FULL_OUT_PATH,
    summary_out_path: Path | None = DEFAULT_SUMMARY_OUT_PATH,
) -> dict[str, Any]:
    """Execute the full Wave 4 production 81-case x N=10,000 Shared-Path Pareto Sweep."""
    t_wall0 = time.perf_counter()
    if ORDER_SEND_CAPABLE:
        raise RuntimeError("SAFETY_VIOLATION: ORDER_SEND_CAPABLE must be False")

    np_int = _require_strict_int(n_paths, "n_paths", min_val=1)
    h_days = _require_strict_int(horizon_days, "horizon_days", min_val=21)
    bl_int = _require_strict_int(block_len, "block_len", min_val=1)
    seed_int = _require_strict_int(seed, "seed", min_val=0)
    b_fric = _require_finite_float(baseline_friction, "baseline_friction", min_val=0.1, max_val=10.0)
    s_fric = _require_finite_float(stress_friction, "stress_friction", min_val=0.1, max_val=10.0)
    haz = _require_finite_float(annual_firm_hazard_rate, "annual_firm_hazard_rate", min_val=0.0, max_val=1.0)

    # Step 1: Probe compute_router & apply BELOW_NORMAL / core cap cleanly (zero popup)
    est_min = round(max(0.5, (np_int / 10_000.0) * (3.2 if include_stress else 1.6)), 2)
    compute_routing = resolve_compute_route(
        est_minutes=est_min,
        ram_gb=2.0,
        shardable=True,
        prefer_x13=prefer_x13,
        offline_no_probe=offline_no_probe,
    )
    prio_info = apply_local_process_priority(
        compute_routing["effective_dev_priority"],
        cores=int(compute_routing["effective_dev_cores"]),
    )
    compute_routing["process_priority"] = prio_info

    # Step 2: Load immutable SSOT bundle & empirical sealed-Dev (`<= 2024-12-31`) M1 tapes
    firms_cat, fx_cfg, risk_cfg, ssot_hashes = load_ssot_bundle(
        firms_catalog_path=firms_catalog_path,
        fx_rates_path=fx_rates_path,
        risk_profiles_path=risk_profiles_path,
    )
    usd_vnd = float(fx_cfg.usd_vnd)

    frozen = load_frozen_tapes_v2_direct(tapes_dir=tapes_dir, stem=tapes_stem)
    ext_days = list(frozen["ext_days"])
    enforce_pre_holdout_dates(ext_days, context="wave4.run_pareto_81cases.ext_days", cutoff_day=HOLDOUT_CUTOFF_DAY)
    holdout_rows = assert_strict_pre_holdout_days(ext_days)
    if holdout_rows != 0:
        raise ValueError(f"HOLDOUT_LOCK_VIOLATION: holdout_rows={holdout_rows}")

    rn_cal, rn_meta = load_red_news_calendar_direct()
    replay_cache = ExactTierReplayCache(ext_days, frozen["tapes"], DEFAULT_CORE7_BASE_RISK, rn_cal)

    # Step 3: Build per-SKU empirical templates for 1.0x baseline (and 1.5x stress)
    t_prep0 = time.perf_counter()
    tpls_base, meta_base = build_empirical_ssot_templates(
        firms_catalog=firms_cat,
        risk_profiles=risk_cfg,
        replay_cache=replay_cache,
        contract_ids=DEFAULT_FTMO_LADDER_CONTRACTS,
        profile_id=profile_id,
        friction_mult=b_fric,
        use_promo_day0=use_promo_day0,
        funded_mult_override=None,
    )
    per_sku_audit = audit_empirical_per_sku_lot_floor(
        replay_cache,
        funded_mult=float(meta_base["funded_mult"]),
        fn_symcap_pct=float(meta_base["fn_symcap_pct"]),
        friction_mults=(b_fric, s_fric) if include_stress else (b_fric,),
    )
    prep_base_sec = round(time.perf_counter() - t_prep0, 3)

    # Step 4: Construct Shared Market Path bootstrap index matrix ONCE (reused across all 81 cases & 1.5x stress!)
    n_obs = len(ext_days)
    idx_matrix = make_block_bootstrap_indices(
        n_obs,
        horizon=h_days,
        n_paths=np_int,
        block_len=bl_int,
        seed=seed_int,
    )
    n_firms = max(1, int(meta_base["n_firms"]))
    hazard_days = make_firm_hazard_days(np_int, n_firms, haz, horizon=h_days, seed=seed_int + 777)

    # Step 5: Execute ALL 81 cases at baseline 1.0x slippage
    cases_base, pareto_by_tier_base, pareto_overall_base, sim_base_sec = run_templates_grid(
        templates=tpls_base,
        tpl_meta=meta_base,
        usd_vnd_rate=usd_vnd,
        idx_matrix=idx_matrix,
        hazard_days=hazard_days,
        friction_mult=b_fric,
    )
    verify_base = verify_pareto_cases_invariants(
        cases_base,
        expected_count=81,
        expected_n_paths=np_int,
    )

    # Step 6: Execute ALL 81 cases at 1.5x slippage stress on identical shared paths
    cases_stress: list[dict[str, Any]] = []
    pareto_by_tier_stress: dict[str, list[str]] = {}
    pareto_overall_stress: list[str] = []
    sim_stress_sec = 0.0
    verify_stress: dict[str, Any] = {"status": "SKIPPED"}
    if include_stress:
        tpls_stress, meta_stress = build_empirical_ssot_templates(
            firms_catalog=firms_cat,
            risk_profiles=risk_cfg,
            replay_cache=replay_cache,
            contract_ids=DEFAULT_FTMO_LADDER_CONTRACTS,
            profile_id=profile_id,
            friction_mult=s_fric,
            use_promo_day0=use_promo_day0,
            funded_mult_override=None,
        )
        cases_stress, pareto_by_tier_stress, pareto_overall_stress, sim_stress_sec = run_templates_grid(
            templates=tpls_stress,
            tpl_meta=meta_stress,
            usd_vnd_rate=usd_vnd,
            idx_matrix=idx_matrix,
            hazard_days=hazard_days,
            friction_mult=s_fric,
        )
        verify_stress = verify_pareto_cases_invariants(
            cases_stress,
            expected_count=81,
            expected_n_paths=np_int,
        )

    # Step 7: Micro-tier The5ers 5K Reference rows (strictly tagged TERMS_VERIFIED_EXECUTION_UNMEASURED!)
    the5ers_ref_rows: list[dict[str, Any]] = []
    sim_the5ers_sec = 0.0
    if include_the5ers_ref:
        for t5_cid in DEFAULT_THE5ERS_REF_CONTRACTS:
            t5_tpls, t5_meta = build_empirical_ssot_templates(
                firms_catalog=firms_cat,
                risk_profiles=risk_cfg,
                replay_cache=replay_cache,
                contract_ids=(t5_cid,),
                profile_id=profile_id,
                friction_mult=b_fric,
                use_promo_day0=False,
                funded_mult_override=None,
            )
            t5_cases, _, _, t5_sec = run_templates_grid(
                templates=t5_tpls,
                tpl_meta=t5_meta,
                usd_vnd_rate=usd_vnd,
                idx_matrix=idx_matrix,
                hazard_days=hazard_days,
                bankroll_tiers_m_vnd=DEFAULT_THE5ERS_REF_TIERS_M_VND,
                concurrency_modes=(ConcurrencyMode.CONSERVATIVE_1_TICKET,),
                allocation_policies=(AllocationPolicy.P2_BALANCED_40_40_20,),
                friction_mult=b_fric,
                enable_scaling_plan=False,
            )
            sim_the5ers_sec += t5_sec
            for row in t5_cases:
                row["contract_id"] = t5_cid
                row["execution_status"] = "TERMS_VERIFIED_EXECUTION_UNMEASURED"
                row["dd_anchor_tag"] = "DD_ANCHOR_UNVERIFIED_UNLESS_FLAT_AT_RESET"
                row["case_id"] = f"THE5ERS__{t5_cid}__{row['case_id']}"
                the5ers_ref_rows.append(row)
        verify_pareto_cases_invariants(the5ers_ref_rows, expected_n_paths=np_int)

    # Step 8: Shared-path daily correlation proof on empirical 50K vs 100K Funded daily PnL
    by_cid = {t["contract_id"]: t for t in tpls_base}
    fn_50 = by_cid["ftmo_standard_50k"]["stage_arrays"][16]
    fn_100 = by_cid["ftmo_standard_100k"]["stage_arrays"][16]
    shared_corr = measure_shared_path_daily_correlation(
        daily_net_acct_a=fn_50,
        daily_net_acct_b=fn_100,
        n_paths=min(np_int, 200),
        horizon_days=min(h_days, 252),
        block_len=bl_int,
        seed=seed_int,
        shared_path=True,
    )

    # Step 9: Extract Per-Tier Pareto Highlights & Global Sweet-Spot / Inflection Points
    analytics = extract_sweet_spots_and_inflections(
        cases_base,
        cases_stress if include_stress else None,
        bankroll_tiers_m_vnd=BANKROLL_TIERS_M_VND,
    )

    total_wall_sec = round(time.perf_counter() - t_wall0, 3)
    generated_utc = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    full_payload: dict[str, Any] = {
        "schema_version": FULL_SCHEMA_VERSION,
        "generated_utc": generated_utc,
        "hard_invariants": {
            "order_send_capable": ORDER_SEND_CAPABLE,
            "order_send_count": ORDER_SEND_COUNT,
            "spend_vnd": 0,
            "holdout_cutoff_date": HOLDOUT_CUTOFF_DATE,
            "holdout_2025_plus_sealed": True,
            "holdout_rows_analysed": 0,
            "shared_market_path_enforced": True,
            "notional_double_counted": False,
            "ftmo_max_active_funded_usd": FTMO_MAX_ACTIVE_FUNDED_USD,
            "ftmo_max_single_challenge_usd": FTMO_MAX_SINGLE_CHALLENGE_USD,
            "ftmo_max_scaled_funded_usd": FTMO_MAX_SCALED_FUNDED_USD,
        },
        "resolution_label_vi": RESOLUTION_LABEL_VI,
        "resolution_tag": RESOLUTION_TAG,
        "evidence_stage": EVIDENCE_STAGE,
        "execution_status": meta_base["execution_status"],
        "pricing_regime": meta_base["pricing_regime"],
        "compute_routing": compute_routing,
        "tape_provenance": {
            "stem": frozen["stem"],
            "schema": frozen["schema"],
            "npz_sha256": frozen["npz_sha256"],
            "binding_sha256": frozen["binding_sha256"],
            "min_day": frozen["min_day"],
            "max_day": frozen["max_day"],
            "dev_days_count": len(ext_days),
            "max_day_strictly_lt_cutoff": bool(frozen["max_day_strictly_lt_cutoff"]),
            "holdout_rows_analysed": 0,
            "red_news_calendar": rn_meta,
        },
        "ssot_provenance": {
            **ssot_hashes,
            "usd_vnd_rate": usd_vnd,
            "fx_verified_utc": fx_cfg.verified_utc.isoformat(),
            "firms_catalog_updated_utc": firms_cat.updated_utc.isoformat(),
            "profile_id": meta_base["profile_id"],
            "funded_mult": meta_base["funded_mult"],
            "amber_mult": meta_base["amber_mult"],
            "red_mult": meta_base["red_mult"],
            "contract_ids": list(DEFAULT_FTMO_LADDER_CONTRACTS),
        },
        "grid_shape": {
            "n_bankroll_tiers": len(BANKROLL_TIERS_M_VND),
            "bankroll_tiers_m_vnd": list(BANKROLL_TIERS_M_VND),
            "n_concurrency_modes": len(CONCURRENCY_MODES),
            "concurrency_modes": [m.value for m in CONCURRENCY_MODES],
            "n_allocation_policies": len(ALLOCATION_POLICIES),
            "allocation_policies": [p.value for p in ALLOCATION_POLICIES],
            "total_cases": len(cases_base),
            "n_paths": np_int,
            "horizon_days": h_days,
            "horizon_months": int(h_days // 21),
            "block_len": bl_int,
            "seed": seed_int,
            "baseline_friction_mult": b_fric,
            "stress_friction_mult": s_fric if include_stress else None,
        },
        "runtime_benchmark": {
            "prep_base_sec": prep_base_sec,
            "sim_baseline_1_0x_sec": round(sim_base_sec, 3),
            "sim_stress_1_5x_sec": round(sim_stress_sec, 3),
            "sim_the5ers_ref_sec": round(sim_the5ers_sec, 3),
            "total_wall_sec": total_wall_sec,
            "python_version": sys.version.split()[0],
        },
        "verification_checks": {
            "baseline_1_0x": verify_base,
            "stress_1_5x": verify_stress,
        },
        "shared_path_correlation_proof": shared_corr,
        "per_sku_001_lot_audit": per_sku_audit,
        "sku_funded_diagnostics_1_0x": meta_base["sku_funded_diagnostics"],
        "pareto_frontier_by_bankroll_tier": pareto_by_tier_base,
        "pareto_frontier_overall_ids": pareto_overall_base,
        "pareto_frontier_by_bankroll_tier_stress_1_5x": pareto_by_tier_stress,
        "pareto_frontier_overall_ids_stress_1_5x": pareto_overall_stress,
        "tier_pareto_highlights": analytics["tier_pareto_highlights"],
        "global_sweet_spots": analytics["global_sweet_spots"],
        "stress_1_5x_summary": analytics["stress_1_5x_summary"],
        "cases": cases_base,
        "cases_stress_1_5x": cases_stress,
        "the5ers_reference_rows": the5ers_ref_rows,
    }

    report_sha256: str
    full_bytes: int
    if full_out_path is not None:
        atomic_write_json(full_out_path, full_payload, indent=2)
        report_sha256 = sha256_file(full_out_path)
        full_bytes = full_out_path.stat().st_size
    else:
        raw_bytes = (json.dumps(full_payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
        report_sha256 = hashlib.sha256(raw_bytes).hexdigest()
        full_bytes = len(raw_bytes)

    # Step 10: Build compact (< 500 KB) summary JSON with exact `report_sha256` for Council & Explorer HTML
    stress_by_id = {c["case_id"]: c for c in cases_stress}
    compact_cases = [_compact_case_snapshot(c, stress_by_id.get(c["case_id"])) for c in cases_base]
    compact_the5ers = [_compact_case_snapshot(c) for c in the5ers_ref_rows]

    summary_payload: dict[str, Any] = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "generated_utc": generated_utc,
        "report_sha256": report_sha256,
        "full_report_path": (
            full_out_path.relative_to(ROOT).as_posix()
            if (full_out_path is not None and full_out_path.is_relative_to(ROOT))
            else (str(full_out_path) if full_out_path is not None else None)
        ),
        "full_report_bytes": full_bytes,
        "hard_invariants": full_payload["hard_invariants"],
        "resolution_label_vi": RESOLUTION_LABEL_VI,
        "resolution_tag": RESOLUTION_TAG,
        "evidence_stage": EVIDENCE_STAGE,
        "execution_status": meta_base["execution_status"],
        "pricing_regime": meta_base["pricing_regime"],
        "compute_routing": {
            "executed_on": compute_routing["executed_on"],
            "dev_pc_mode": compute_routing["dev_pc"].get("mode"),
            "effective_dev_cores": compute_routing["effective_dev_cores"],
            "effective_dev_priority": compute_routing["effective_dev_priority"],
            "x13_reachable": compute_routing["x13_worker"].get("reachable"),
            "x13_ac_online": compute_routing["x13_worker"].get("ac_online"),
            "x13_eligible": compute_routing["x13_worker"].get("eligible"),
            "x13_transport": compute_routing["x13_worker"].get("transport"),
            "route_target": compute_routing["route_decision"].get("target"),
            "fallback_used": compute_routing["route_decision"].get("fallback_used"),
            "fallback_reason": compute_routing["route_decision"].get("fallback_reason"),
            "reasons": compute_routing["route_decision"].get("reasons"),
        },
        "tape_provenance": full_payload["tape_provenance"],
        "ssot_provenance": full_payload["ssot_provenance"],
        "grid_shape": full_payload["grid_shape"],
        "runtime_benchmark": full_payload["runtime_benchmark"],
        "verification_checks": full_payload["verification_checks"],
        "shared_path_correlation_proof": shared_corr,
        "per_sku_001_lot_audit": per_sku_audit,
        "pareto_frontier_by_bankroll_tier": pareto_by_tier_base,
        "pareto_frontier_overall_ids": pareto_overall_base,
        "tier_pareto_highlights": analytics["tier_pareto_highlights"],
        "global_sweet_spots": analytics["global_sweet_spots"],
        "stress_1_5x_summary": analytics["stress_1_5x_summary"],
        "cases_compact": compact_cases,
        "the5ers_reference_compact": compact_the5ers,
    }

    summary_sha256 = ""
    summary_bytes = 0
    if summary_out_path is not None:
        atomic_write_json(summary_out_path, summary_payload, indent=2)
        summary_bytes = summary_out_path.stat().st_size
        if summary_bytes >= SUMMARY_MAX_BYTES:
            # Compact without indentation if needed to guarantee strict < 500 KB budget
            summary_out_path.write_text(
                json.dumps(summary_payload, separators=(",", ":"), ensure_ascii=False, sort_keys=True) + "\n",
                encoding="utf-8",
                newline="\n",
            )
            summary_bytes = summary_out_path.stat().st_size
        if summary_bytes >= SUMMARY_MAX_BYTES:
            raise ValueError(f"SUMMARY_SIZE_BUDGET_EXCEEDED: {summary_bytes} >= {SUMMARY_MAX_BYTES}")
        summary_sha256 = sha256_file(summary_out_path)

    return {
        "full_payload": full_payload,
        "summary_payload": summary_payload,
        "report_sha256": report_sha256,
        "full_bytes": full_bytes,
        "summary_sha256": summary_sha256,
        "summary_bytes": summary_bytes,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Wave 4 Production 81-Case x N=10,000 Shared-Path Pareto Sweep Runner"
    )
    ap.add_argument("--n-paths", type=int, default=DEFAULT_PRODUCTION_N_PATHS, help="Shared paths (default: 10000)")
    ap.add_argument("--horizon-days", type=int, default=DEFAULT_HORIZON_DAYS, help="Trading days (default: 756 = 36m)")
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED, help="RNG seed")
    ap.add_argument("--no-stress", action="store_true", help="Skip 1.5x slippage stress sweep")
    ap.add_argument("--no-the5ers-ref", action="store_true", help="Skip The5ers 5K micro-tier reference rows")
    ap.add_argument("--prefer-x13", action="store_true", help="Request X13 routing preference via compute_router")
    ap.add_argument("--offline-no-probe", action="store_true", help="Skip live SSH/OS probe (unit/offline mode)")
    ap.add_argument("--full-out", type=Path, default=DEFAULT_FULL_OUT_PATH, help="Full JSON output path")
    ap.add_argument("--summary-out", type=Path, default=DEFAULT_SUMMARY_OUT_PATH, help="Compact <500KB summary path")
    args = ap.parse_args(argv)

    out = run_production_pareto_81cases(
        n_paths=args.n_paths,
        horizon_days=args.horizon_days,
        seed=args.seed,
        include_stress=not args.no_stress,
        include_the5ers_ref=not args.no_the5ers_ref,
        prefer_x13=args.prefer_x13,
        offline_no_probe=args.offline_no_probe,
        full_out_path=args.full_out,
        summary_out_path=args.summary_out,
    )
    summ = out["summary_payload"]
    brief = {
        "schema_version": summ["schema_version"],
        "report_sha256": out["report_sha256"],
        "full_bytes": out["full_bytes"],
        "summary_sha256": out["summary_sha256"],
        "summary_bytes": out["summary_bytes"],
        "total_cases": summ["grid_shape"]["total_cases"],
        "n_paths": summ["grid_shape"]["n_paths"],
        "holdout_rows_analysed": summ["hard_invariants"]["holdout_rows_analysed"],
        "order_send_count": summ["hard_invariants"]["order_send_count"],
        "compute_routing": summ["compute_routing"],
        "runtime_benchmark": summ["runtime_benchmark"],
        "verification_checks": summ["verification_checks"],
    }
    print(json.dumps(brief, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

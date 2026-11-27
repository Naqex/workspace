"""Unit & Local-Cache Artifact Tests for Wave 4 Production 81-Case x N=10,000 Pareto Runner.

Covers `W4-G06` & `W4-G07`:
  1. Offline unit tests (`-m "not local_cache"`):
     - Pareto dominance extractor & Per-Tier / Global sweet-spot inflection analyzer.
     - Fail-closed 100%-sum check (`pass + fail + pending == 100.0` at `3m/6m/12m/24m/36m`),
       Holdout==0, OrderSend==0, FTMO $400K cap, Wilson UB, and zero notional double-counting.
     - Capital Curve Honesty enrichment strictly separating liquid cash net worth from Funded notional.
     - `compute_router` AC-only & fallback routing (battery discharging, offline, short local Mode A).
     - AST `[ARCH-02]` zero bare `assert`, zero `MetaTrader5` import, LF-only & no-BOM hygiene.
  2. Production artifact verification (`@pytest.mark.local_cache`):
     - Validates `.runtime/offensive4/pareto/wave4_pareto_81cases_10k.json` & `< 500 KB`
       `.runtime/offensive4/pareto/wave4_pareto_summary.json` (`81` cases x `N=10,000`, `1.0x` &
       `1.5x` stress, `holdout_rows_analysed == 0`, exact `report_sha256` match, The5ers tag,
       shared-path `rho > 0.95`, and mathematical non-dominance of Pareto frontier).
"""

from __future__ import annotations

import ast
import copy
import json
from pathlib import Path
from typing import Any

import pytest
from quant_core.io_utils import sha256_file
from quant_factory.wave4 import pareto_multi_account as pma
from quant_factory.wave4 import run_pareto_81cases as runner

RUNNER_PATH = Path(runner.__file__).resolve()


def _make_stub_case(
    *,
    case_id: str,
    bankroll_m_vnd: int,
    concurrency_mode: str = "CONSERVATIVE_1_TICKET",
    allocation_policy: str = "P2_BALANCED_40_40_20",
    median_24m_net_vnd: float = 40_000_000.0,
    median_36m_net_vnd: float = 120_000_000.0,
    p_ruin_pct: float = 0.5,
    p_neg_24m_pct: float = 12.0,
    p_neg_36m_pct: float = 8.0,
    own_book_usd: float = 12_000.0,
    recoup_usd: float = 8_000.0,
    challenge_cash_usd: float = 2_000.0,
    max_base_funded_usd: float = 200_000.0,
    mean_max_base_funded_usd: float = 120_000.0,
    usd_vnd_rate: float = 25_765.94,
    n_paths: int = 10_000,
) -> dict[str, Any]:
    bank_vnd = float(bankroll_m_vnd) * 1_000_000.0
    bank_usd = round(bank_vnd / usd_vnd_rate, 2)
    mean_wealth_usd = round(challenge_cash_usd + recoup_usd + own_book_usd, 2)
    horizons = {
        "3m": {"pass_pct": 15.0, "fail_pct": 2.0, "pending_pct": 83.0, "sum_pct": 100.0},
        "6m": {"pass_pct": 35.0, "fail_pct": 3.0, "pending_pct": 62.0, "sum_pct": 100.0},
        "12m": {"pass_pct": 55.0, "fail_pct": 4.0, "pending_pct": 41.0, "sum_pct": 100.0},
        "24m": {"pass_pct": 75.0, "fail_pct": 5.0, "pending_pct": 20.0, "sum_pct": 100.0},
        "36m": {"pass_pct": 85.0, "fail_pct": 5.0, "pending_pct": 10.0, "sum_pct": 100.0},
    }
    med_24_usd = round(median_24m_net_vnd / usd_vnd_rate, 2)
    med_36_usd = round(median_36m_net_vnd / usd_vnd_rate, 2)
    case: dict[str, Any] = {
        "case_id": case_id,
        "resolution_label_vi": pma.RESOLUTION_LABEL_VI,
        "resolution_tag": pma.RESOLUTION_TAG,
        "evidence_stage": pma.EVIDENCE_STAGE,
        "execution_status": "MEASURED_DEMO_EXECUTION",
        "pricing_regime": "ALL_REGULAR_SSOT",
        "order_send_count": 0,
        "holdout_rows_analysed": 0,
        "n_paths": n_paths,
        "horizon_days": 756,
        "bankroll_m_vnd": bankroll_m_vnd,
        "bankroll_vnd": bank_vnd,
        "bankroll_usd": bank_usd,
        "usd_vnd_rate": usd_vnd_rate,
        "concurrency_mode": concurrency_mode,
        "allocation_policy": allocation_policy,
        "monthly_pass_fail_pending": copy.deepcopy(horizons),
        "first_ticket_pass_fail_pending": copy.deepcopy(horizons),
        "bot_auto_kill_pct": 12.0,
        "mean_bot_auto_kill_events": 0.4,
        "firm_hard_breach_pct": 25.0,
        "mean_firm_hard_breach_events": 0.5,
        "eval_hard_breach_pct": 24.5,
        "funded_hard_breach_pct": 0.5,
        "firm_hard_breach_daily_pct": 18.0,
        "firm_hard_breach_maxdd_pct": 7.0,
        "simultaneous_fail_pct": 1.0,
        "funded_12m_blowup": {
            "n_paths_entered_funded": 8000,
            "n_paths_full_12m_observed": 6500,
            "n_paths_censored_lt_12m": 1500,
            "n_paths_breached_within_12m": 8,
            "blowup_12m_pct": 0.10,
            "blowup_12m_uncensored_pct": 0.12,
            "wilson_95_ub_pct": 0.20,
            "fleet_total_funded_entries": 12000,
            "fleet_total_funded_breaches_12m": 10,
            "fleet_total_funded_censored_12m": 2000,
        },
        "net_profit_24m_usd": {"mean": med_24_usd * 1.2, "median": med_24_usd, "p10": -200.0, "p90": med_24_usd * 2.5},
        "net_profit_24m_vnd": {
            "mean": round(median_24m_net_vnd * 1.2, 0),
            "median": round(median_24m_net_vnd, 0),
            "p10": -5_000_000.0,
            "p90": round(median_24m_net_vnd * 2.5, 0),
        },
        "net_profit_36m_usd": {"mean": med_36_usd * 1.2, "median": med_36_usd, "p10": 100.0, "p90": med_36_usd * 2.5},
        "net_profit_36m_vnd": {
            "mean": round(median_36m_net_vnd * 1.2, 0),
            "median": round(median_36m_net_vnd, 0),
            "p10": 2_500_000.0,
            "p90": round(median_36m_net_vnd * 2.5, 0),
        },
        "median_24m_net_usd": med_24_usd,
        "median_24m_net_vnd": round(median_24m_net_vnd, 0),
        "median_36m_net_usd": med_36_usd,
        "median_36m_net_vnd": round(median_36m_net_vnd, 0),
        "mean_36m_net_usd": round(med_36_usd * 1.2, 2),
        "mean_36m_net_vnd": round(median_36m_net_vnd * 1.2, 0),
        "mean_wealth_36m_usd": mean_wealth_usd,
        "mean_own_book_36m_usd": own_book_usd,
        "mean_recoup_cash_36m_usd": recoup_usd,
        "mean_challenge_cash_36m_usd": challenge_cash_usd,
        "max_cash_accounting_err_usd": 1e-10,
        "p_net_le_0_24m_pct": p_neg_24m_pct,
        "p_net_le_0_36m_pct": p_neg_36m_pct,
        "p_bankroll_ruin_24m_pct": p_ruin_pct,
        "p_bankroll_ruin_pct": p_ruin_pct,
        "mean_total_fees_24m_usd": 450.0,
        "mean_total_fees_36m_usd": 600.0,
        "mean_total_fees_36m_vnd": round(600.0 * usd_vnd_rate, 0),
        "mean_total_payouts_36m_usd": 6000.0,
        "mean_total_refunds_36m_usd": 200.0,
        "ev_per_1_vnd_fee_24m": 4.5,
        "ev_per_1_vnd_fee_36m": 9.2,
        "paid_any_pct": 82.0,
        "cond_med_pay1_cal_days": 210.0,
        "uncond_med_pay1_cal_days_cap365": 290.0,
        "uncond_med_pay1_cal_days_cap730": 310.0,
        "funded_dry_months_pct": 48.0,
        "longest_starved_month_streak_p50": 3,
        "longest_starved_month_streak_p95": 7,
        "longest_starved_month_streak_max": 12,
        "max_active_base_funded_usd": max_base_funded_usd,
        "mean_max_base_funded_usd": mean_max_base_funded_usd,
        "max_active_scaled_funded_usd": max_base_funded_usd * 1.25,
        "mean_scaling_upgrades": 0.8,
        "law15_position": {"domain_tier": "TIER_1_SINGLE_CFD_PROP_BOT", "grade_code": "TOT", "grade_vi": "Tốt"},
        "is_pareto_in_tier": False,
        "is_pareto_overall": False,
    }
    return runner._enrich_case_capital_honesty(case, friction_mult=1.0)


# ---------------------------------------------------------------------------
# 1. Offline Unit Tests (`-m "not local_cache"`)
# ---------------------------------------------------------------------------


def test_pareto_dominance_extractor_and_sweet_spot_inflections() -> None:
    """Verify non-dominated Pareto filtering & exact sweet-spot / inflection extraction."""
    # Tier 10M: c1_dom is strictly dominated by c1_best
    c1_dom = _make_stub_case(
        case_id="B10M__AGG__P3",
        bankroll_m_vnd=10,
        median_24m_net_vnd=-5_000_000.0,
        median_36m_net_vnd=10_000_000.0,
        p_ruin_pct=15.0,
        p_neg_24m_pct=55.0,
        p_neg_36m_pct=40.0,
        own_book_usd=500.0,
    )
    c1_best = _make_stub_case(
        case_id="B10M__CONS__P2",
        bankroll_m_vnd=10,
        median_24m_net_vnd=5_000_000.0,
        median_36m_net_vnd=25_000_000.0,
        p_ruin_pct=4.0,
        p_neg_24m_pct=42.0,
        p_neg_36m_pct=25.0,
        own_book_usd=1_200.0,
    )
    # Tier 40M: achieves P(ruin) < 1% but P(net<=0 at 24m) >= 15%
    c2_safe = _make_stub_case(
        case_id="B40M__STAG__P2",
        bankroll_m_vnd=40,
        median_24m_net_vnd=60_000_000.0,
        median_36m_net_vnd=180_000_000.0,
        p_ruin_pct=0.4,
        p_neg_24m_pct=22.0,
        p_neg_36m_pct=11.0,
        own_book_usd=6_000.0,
        mean_max_base_funded_usd=80_000.0,
    )
    # Tier 100M: achieves BOTH P(ruin) < 1% AND P(net<=0 at 24m) < 15% AND Phase 3 Hybrid Barbell!
    c3_sweet = _make_stub_case(
        case_id="B100M__STAG__P2",
        bankroll_m_vnd=100,
        median_24m_net_vnd=160_000_000.0,
        median_36m_net_vnd=420_000_000.0,
        p_ruin_pct=0.1,
        p_neg_24m_pct=11.5,
        p_neg_36m_pct=5.0,
        own_book_usd=18_000.0,
        mean_max_base_funded_usd=150_000.0,
    )
    # Tier 250M: reaches Phase 4 Own-Book Dominant (own_book >= $50K and own beats prop!)
    c4_own = _make_stub_case(
        case_id="B250M__AGG__P1",
        bankroll_m_vnd=250,
        median_24m_net_vnd=220_000_000.0,
        median_36m_net_vnd=600_000_000.0,
        p_ruin_pct=0.05,
        p_neg_24m_pct=9.0,
        p_neg_36m_pct=3.5,
        own_book_usd=85_000.0,
        mean_max_base_funded_usd=200_000.0,
    )

    cases = [c1_dom, c1_best, c2_safe, c3_sweet, c4_own]
    front_10m = pma.extract_pareto_frontier([c1_dom, c1_best])
    assert [c["case_id"] for c in front_10m] == ["B10M__CONS__P2"]

    # Create paired stress cases with lower medians
    cases_stress = []
    for c in cases:
        sc = copy.deepcopy(c)
        sc["median_36m_net_vnd"] = c["median_36m_net_vnd"] * 0.4 - 20_000_000.0
        sc["p_net_le_0_36m_pct"] = min(100.0, c["p_net_le_0_36m_pct"] + 25.0)
        cases_stress.append(sc)

    analytics = runner.extract_sweet_spots_and_inflections(
        cases,
        cases_stress,
        bankroll_tiers_m_vnd=(10, 40, 100, 250),
    )
    gs = analytics["global_sweet_spots"]
    assert gs["min_bankroll_ruin_lt_1pct_m_vnd"] == 40
    assert gs["min_bankroll_ruin_lt_1pct_and_neg24m_lt_15pct_m_vnd"] == 100
    assert gs["best_config_at_ruin_lt_1pct_and_neg24m_lt_15pct"]["case_id"] == "B100M__STAG__P2"
    assert gs["own_book_crossover_inflection"]["min_bankroll_phase3_hybrid_barbell_m_vnd"] == 100
    assert gs["own_book_crossover_inflection"]["min_bankroll_phase4_own_book_dominant_m_vnd"] == 250
    assert analytics["tier_pareto_highlights"]["10M_VND"]["pareto_case_ids"] == ["B10M__CONS__P2"]
    assert analytics["stress_1_5x_summary"]["n_cases_compared"] == 4


def test_verify_invariants_100pct_sum_and_capital_curve_non_double_counting() -> None:
    """Verify fail-closed invariant checker catches 100%-sum drift, Holdout leak & notional double-count."""
    good = _make_stub_case(case_id="GOOD_1", bankroll_m_vnd=25)
    res = runner.verify_pareto_cases_invariants([good], expected_count=1, expected_n_paths=10_000)
    assert res["status"] == "PASS"
    assert res["notional_double_counted"] is False
    assert res["holdout_rows_analysed"] == 0

    # Mutation 1: 100%-sum drift at 12m (99.5% != 100.0%)
    bad_sum = copy.deepcopy(good)
    bad_sum["monthly_pass_fail_pending"]["12m"]["pending_pct"] = 40.5
    with pytest.raises(ValueError, match="PARTITION_SUM_VIOLATION"):
        runner.verify_pareto_cases_invariants([bad_sum])

    # Mutation 2: Capital curve notional double-counting (+$10,000 Funded notional leaked into mean_wealth)
    bad_double = copy.deepcopy(good)
    bad_double["mean_wealth_36m_usd"] = good["mean_wealth_36m_usd"] + 10_000.0
    with pytest.raises(ValueError, match="LIQUID_NET_WORTH_DOUBLE_COUNT"):
        runner.verify_pareto_cases_invariants([bad_double])

    # Mutation 3: FTMO $400K active base Funded cap exceeded
    bad_cap = copy.deepcopy(good)
    bad_cap["max_active_base_funded_usd"] = 450_000.0
    with pytest.raises(ValueError, match="FTMO_400K_CAP_BREACH"):
        runner.verify_pareto_cases_invariants([bad_cap])

    # Mutation 4: Holdout leak (`holdout_rows_analysed != 0`)
    bad_ho = copy.deepcopy(good)
    bad_ho["holdout_rows_analysed"] = 1
    with pytest.raises(ValueError, match="HOLDOUT_VIOLATION"):
        runner.verify_pareto_cases_invariants([bad_ho])

    # Mutation 5: OrderSend leak (`order_send_count != 0`)
    bad_os = copy.deepcopy(good)
    bad_os["order_send_count"] = 1
    with pytest.raises(ValueError, match="ORDER_SEND_VIOLATION"):
        runner.verify_pareto_cases_invariants([bad_os])

    # Mutation 6: Missing resolution label
    bad_lbl = copy.deepcopy(good)
    bad_lbl["resolution_label_vi"] = "MISSING"
    with pytest.raises(ValueError, match="MISSING_RESOLUTION_LABEL"):
        runner.verify_pareto_cases_invariants([bad_lbl])

    # Mutation 7: Wilson 95% UB < point estimate
    bad_w = copy.deepcopy(good)
    bad_w["funded_12m_blowup"]["wilson_95_ub_pct"] = 0.01
    with pytest.raises(ValueError, match="WILSON_UB_LT_POINT"):
        runner.verify_pareto_cases_invariants([bad_w])


def test_capital_curve_honesty_separates_funded_notional() -> None:
    """Confirm Funded notional ($200K) is strictly separated from liquid cash net worth ($22K)."""
    c = _make_stub_case(
        case_id="HONESTY_CHECK",
        bankroll_m_vnd=100,
        challenge_cash_usd=2_000.0,
        recoup_usd=8_000.0,
        own_book_usd=12_000.0,
        max_base_funded_usd=200_000.0,
        mean_max_base_funded_usd=150_000.0,
    )
    hon = c["capital_curve_honesty"]
    assert hon["notional_double_counted"] is False
    assert hon["liquid_buckets_sum_36m_mean_usd"] == pytest.approx(22_000.0)
    assert hon["liquid_cash_net_worth_36m_mean_usd"] == pytest.approx(22_000.0)
    assert hon["active_funded_notional_mean_max_usd"] == pytest.approx(150_000.0)
    assert hon["active_funded_notional_cap_max_base_usd"] == pytest.approx(200_000.0)
    assert hon["notional_disclosure_tag"] == "PROP_NOTIONAL_SEPARATED_NOT_LIQUID_CASH"
    assert hon["own_book_crossover"]["own_book_equity_usd"] == pytest.approx(12_000.0)
    assert hon["own_book_crossover"]["active_prop_nominal_usd"] == pytest.approx(150_000.0)


def test_compute_router_ac_only_and_silent_fallback() -> None:
    """Verify AC-only <X13_WORKER> enforcement and clean BELOW_NORMAL fallback without SSH calls."""
    dev_mode_a = {
        "idle_sec": 10.0,
        "in_overnight_window_ict": False,
        "gpu_util_pct": 5,
        "fullscreen_busy": False,
        "cpu_util_pct": 25.0,
        "free_ram_gb": 16.0,
        "ntp_offset_ms": 20.0,
        "ntp_ok": True,
        "mode": "MODE_A_OWNER_ACTIVE",
    }
    x13_on_battery = {
        "ssh_alias": "naqex-x13",
        "transport": "LAN",
        "probe_ms": 250.0,
        "reachable": True,
        "ac_online": False,
        "ac_line_status": 0,
        "battery_status_code": 1,
        "battery_pct": 65,
        "cpu_util_pct": 2.0,
        "free_ram_gb": 10.0,
        "disk_free_gb": 100.0,
        "venv_ok": True,
        "active_job_lock": None,
        "ntp_offset_ms": 30.0,
        "forbidden_files": 0,
        "eligible": False,
        "ineligible_reasons": ["x13_battery_discharging(BatteryStatus=1)"],
    }
    r_bat = runner.resolve_compute_route(
        est_minutes=15.0,
        prefer_x13=True,
        probe_dev_fn=lambda: dev_mode_a,
        probe_x13_fn=lambda: x13_on_battery,
    )
    assert r_bat["route_decision"]["target"] == "DEV_PC_ONLY"
    assert r_bat["route_decision"]["fallback_used"] is True
    assert "battery_discharging" in str(r_bat["route_decision"]["fallback_reason"])
    assert r_bat["effective_dev_priority"] == "BELOW_NORMAL"
    assert r_bat["executed_on"] == "DEV_PC"

    # Short <10m job with healthy X13 on AC runs cleanly on DEV_PC BELOW_NORMAL without fallback
    x13_ac_ready = {
        **x13_on_battery,
        "ac_online": True,
        "ac_line_status": 1,
        "battery_status_code": 2,
        "eligible": True,
        "ineligible_reasons": [],
    }
    r_short = runner.resolve_compute_route(
        est_minutes=3.5,
        prefer_x13=False,
        probe_dev_fn=lambda: dev_mode_a,
        probe_x13_fn=lambda: x13_ac_ready,
    )
    assert r_short["route_decision"]["target"] == "DEV_PC_ONLY"
    assert r_short["route_decision"]["fallback_used"] is False
    assert r_short["x13_worker"]["eligible"] is True
    assert r_short["effective_dev_priority"] == "BELOW_NORMAL"

    # Offline unit skip works without any subprocess/SSH calls
    r_off = runner.resolve_compute_route(est_minutes=2.0, offline_no_probe=True)
    assert r_off["executed_on"] == "DEV_PC"
    assert r_off["effective_dev_priority"] == "BELOW_NORMAL"


def test_static_kill_does_not_delete_recovery_wins_below_ea_floor() -> None:
    """Regression test: once balance is below `ea_static_floor` (-7.5%), winning days MUST recover balance."""
    import numpy as np
    from quant_factory.capital_optimizer.policy_kernel import _pack_templates_for_numba

    # Day 0: -7.7% closing loss (-770 on 10K, within 10% firm cap, crosses 7.5% EA static floor)
    # Day 1..4: +300/day recovery wins (tiny intraday dd=20) -> MUST NOT be zeroed/flipped negative!
    nets = np.array([-770.0, 300.0, 300.0, 300.0, 300.0], dtype=np.float64)
    dds = np.array([770.0, 20.0, 20.0, 20.0, 20.0], dtype=np.float64)
    ups = np.array([10.0, 310.0, 310.0, 310.0, 310.0], dtype=np.float64)
    flgs = np.ones(5, dtype=np.int8)
    st = (
        nets, dds, ups, flgs,
        nets, dds, ups, flgs,
        nets, dds, ups, flgs,
        nets, dds, ups, flgs,
        nets, dds, ups, flgs,
        nets, dds, ups, flgs,
        nets, dds, ups, flgs,
    )
    tpl = {
        "contract_id": "ftmo_standard_10k",
        "firm_idx": 0,
        "firm_id": "FTMO",
        "program_id": "ftmo_2step_standard",
        "execution_status": "MEASURED_DEMO_EXECUTION",
        "steps": 0,
        "capital_usd": 10_000.0,
        "fee_day0_usd": 98.61,
        "fee_regular_usd": 98.61,
        "fee_refund_pct": 1.0,
        "card_fx_fee_frac": 0.025,
        "payout_withdrawal_fee_pct": 0.015,
        "withdrawal_fee_pct": 0.015,
        "refund_withdrawal_fee_pct": 0.0,
        "p1_target_pct": 0.10,
        "p2_target_pct": 0.05,
        "dd_daily_pct": 0.10,
        "dd_max_pct": 0.10,
        "dd_type": "static",
        "daily_dd_anchor": "initial_balance",
        "best_day_cap_pct": 0.0,
        "min_trading_days": 0,
        "min_profitable_days": 0,
        "min_profitable_day_pct": 0.0,
        "profit_split_pct": 0.80,
        "profit_split_max_pct": 0.90,
        "payout_cycle_trading_days": 5,
        "min_payout_usd": 50.0,
        "p1_lock_trigger": 0.70,
        "p2_lock_trigger": 0.70,
        "amber_dd": 0.035,
        "red_dd": 0.060,
        "p1_ea_stop": 0.090,
        "p2_ea_stop": 0.090,
        "fn_ea_stop": 0.090,
        "p1_ea_static_stop": 0.075,
        "p2_ea_static_stop": 0.075,
        "fn_ea_static_stop": 0.075,
        "refund_payout_milestone": 1,
        "payout_buffer_retention_pct": 0.0,
        "locks_at_initial_after_first_payout": False,
        "min_payout_profit_pct": 0.0,
        "daily_profit_cap_pct": 0.0,
        "funded_first_payout_min_prof_days": 0,
        "funded_first_payout_prof_pct": 0.0,
        "stage_arrays": st,
    }
    packed = _pack_templates_for_numba([tpl])
    idx_mat = np.array([[0, 1, 2, 3, 4]], dtype=np.int32)
    haz = np.full((1, 1), -1, dtype=np.int32)
    res = pma._simulate_wave4_pareto_fleet_numba(
        idx_mat,
        haz,
        *packed,
        np.array([0.025]),
        np.array([0.90]),
        np.array([0.075]),
        np.array([0.075]),
        np.array([0.075]),
        np.array([400_000.0]),
        np.array([200_000.0]),
        np.array([2_000_000.0]),
        np.array([0], dtype=np.int32),
        0,
        0,
        200.0,
        1,
        5,
        0.035,
        False,
        0.0,
        3.0,
        0.0,
        0.5,
        0.5,
    )
    # Day 0 triggers static_kill ONCE (at -770), then Days 1..4 recover +1200 -> net +430 -> Payout #1 > 0!
    assert int(res[21][0]) == 1  # exactly 1 BOT_AUTO_KILL on crossing day 0 (NOT 5!)
    assert int(res[22][0]) == 0  # 0 FIRM_HARD_BREACH
    assert float(res[9][0]) > 250.0  # Recovered to profit and received Payout #1!


def test_zero_bare_asserts_no_mt5_and_lf_hygiene_arch02() -> None:
    raw = RUNNER_PATH.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf"), "UTF-8 BOM forbidden"
    assert b"\r\n" not in raw, "CRLF line endings forbidden"
    src = raw.decode("utf-8")
    tree = ast.parse(src)
    asserts = [node.lineno for node in ast.walk(tree) if isinstance(node, ast.Assert)]
    assert asserts == [], f"Forbidden bare assert(s) in production runner [ARCH-02]: lines {asserts}"
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name != "MetaTrader5"
        elif isinstance(node, ast.ImportFrom):
            assert node.module != "MetaTrader5"


# ---------------------------------------------------------------------------
# 2. Local-Cache Production Artifact Tests (`@pytest.mark.local_cache`)
# ---------------------------------------------------------------------------


@pytest.mark.local_cache
def test_production_wave4_pareto_81cases_10k_artifact() -> None:
    """Verify real `.runtime/offensive4/pareto/wave4_pareto_81cases_10k.json` & `< 500 KB` summary."""
    full_path = runner.DEFAULT_FULL_OUT_PATH
    summary_path = runner.DEFAULT_SUMMARY_OUT_PATH
    if not full_path.is_file() or not summary_path.is_file():
        pytest.skip(f"Production Pareto artifacts not generated yet: {full_path}")

    assert summary_path.stat().st_size < runner.SUMMARY_MAX_BYTES, (
        f"Summary exceeds 500 KB budget: {summary_path.stat().st_size} bytes"
    )

    full = json.loads(full_path.read_text(encoding="utf-8"))
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    # Exact SHA-256 verification linking summary -> full 81-case x 10K artifact!
    actual_sha = sha256_file(full_path)
    assert summary["report_sha256"] == actual_sha
    assert len(actual_sha) == 64

    # Hard safety & Holdout invariants
    inv = full["hard_invariants"]
    assert inv["order_send_capable"] is False
    assert inv["order_send_count"] == 0
    assert inv["spend_vnd"] == 0
    assert inv["holdout_cutoff_date"] == "2024-12-31"
    assert inv["holdout_2025_plus_sealed"] is True
    assert inv["holdout_rows_analysed"] == 0
    assert inv["notional_double_counted"] is False
    assert inv["shared_market_path_enforced"] is True

    # Tape provenance strictly pre-Holdout
    tp = full["tape_provenance"]
    assert tp["max_day"] <= "2024-12-31"
    assert tp["max_day_strictly_lt_cutoff"] is True
    assert tp["holdout_rows_analysed"] == 0

    # Grid completeness: 81 cases x N = 10,000 x 756d (both 1.0x baseline and 1.5x stress)
    gs = full["grid_shape"]
    assert gs["total_cases"] == 81
    assert gs["n_paths"] == 10_000
    assert gs["horizon_days"] == 756
    assert gs["bankroll_tiers_m_vnd"] == [10, 15, 25, 40, 60, 100, 150, 250, 500]
    assert len(full["cases"]) == 81
    assert len(full["cases_stress_1_5x"]) == 81
    assert len(summary["cases_compact"]) == 81

    # Re-run fail-closed invariant checker over ALL 81 baseline AND ALL 81 stress cases!
    v_base = runner.verify_pareto_cases_invariants(full["cases"], expected_count=81, expected_n_paths=10_000)
    v_str = runner.verify_pareto_cases_invariants(full["cases_stress_1_5x"], expected_count=81, expected_n_paths=10_000)
    assert v_base["status"] == "PASS"
    assert v_str["status"] == "PASS"

    # Shared-path daily PnL correlation proof (rho > 0.95)
    assert full["shared_path_correlation_proof"]["mean_daily_pnl_rho"] > 0.95

    # Real 0.01-lot floor audit across 5K..200K (5K must reject >=1 signal on real Dev tapes)
    sku_1x = full["per_sku_001_lot_audit"]["regimes"]["1.00x"]
    assert set(sku_1x.keys()) == {"5K", "10K", "25K", "50K", "100K", "200K"}
    assert sku_1x["5K"]["min_lot_rejected"] > 0

    # The5ers rows explicitly tagged TERMS_VERIFIED_EXECUTION_UNMEASURED & XẤP XỈ CẤP NGÀY
    t5_rows = full["the5ers_reference_rows"]
    assert len(t5_rows) >= 6
    for row in t5_rows:
        assert row["execution_status"] == "TERMS_VERIFIED_EXECUTION_UNMEASURED"
        assert row["resolution_label_vi"] == "XẤP XỈ CẤP NGÀY"
        assert row["resolution_tag"] == "APPROX_DAILY_RESOLUTION"
        assert row["holdout_rows_analysed"] == 0

    # Mathematical non-dominance proof of overall Pareto frontier
    assert len(full["pareto_frontier_by_bankroll_tier"]) == 9
    front_overall = [c for c in full["cases"] if c["is_pareto_overall"]]
    assert len(front_overall) == len(full["pareto_frontier_overall_ids"])
    assert len(front_overall) >= 1
    for fa in front_overall:
        for fb in full["cases"]:
            dominates = (
                fb["median_36m_net_vnd"] >= fa["median_36m_net_vnd"] - 1e-9
                and fb["p_bankroll_ruin_pct"] <= fa["p_bankroll_ruin_pct"] + 1e-9
                and fb["p_net_le_0_36m_pct"] <= fa["p_net_le_0_36m_pct"] + 1e-9
                and (
                    fb["median_36m_net_vnd"] > fa["median_36m_net_vnd"] + 1e-9
                    or fb["p_bankroll_ruin_pct"] < fa["p_bankroll_ruin_pct"] - 1e-9
                    or fb["p_net_le_0_36m_pct"] < fa["p_net_le_0_36m_pct"] - 1e-9
                )
            )
            assert not dominates, f"Pareto case {fa['case_id']} dominated by {fb['case_id']}"

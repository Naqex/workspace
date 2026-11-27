"""Unit, Oracle, Performance & Negative-Mutation Tests for Wave 4 Shared-Path 81-Case Pareto Kernel.

Covers `W4-G06` & `W4-G07`:
  1. Exact `81` configs (`9` VND bankrolls x `3` concurrency modes x `3` after-payout policies) + VND/USD SSOT FX.
  2. `Pass + Fail + Pending == 100.0%` at EVERY horizon (`3m/6m/12m/24m/36m`) across all 81 cases.
  3. Shared-Path correlation proof (`rho > 0.95` for 2 parallel accounts on same bot) + negative mutation
     proving independent sampling fails (`rho < 0.25`).
  4. FTMO `$400K` active base Funded cap & `$200K`/Challenge cap enforcement + Scaling Plan (`+25%` every `4m`,
     `80% -> 90%` split, up to `$2M`) with ZERO double-counting of Funded notional as liquid cash net worth.
  5. Exact penny-oracle verification of VN `+2.5%` card FX fee, `-1.5%` withdrawal fee, and P1 fee refund on
     Payout #1 (and non-duplication on Payout #2).
  6. Per-SKU `0.01`-lot floor sensitivity (`5K/10K` vs `100K` — proves non-linear `0.01`-lot drag).
  7. Separate `BOT_AUTO_KILL` vs `FIRM_HARD_BREACH`, 12m Funded blowup + Wilson 95% UB, Pareto frontier
     dominance invariant, The5ers `TERMS_VERIFIED_EXECUTION_UNMEASURED` tag, Holdout `>= 2025-01-01`
     fail-closed rejection (safe under `python -O`), poisoned input rejection (`bool`/`NaN`/`Inf`), AST zero
     bare `assert` check `[ARCH-02]`, and fast Numba smoke-run (`N = 200` paths in `< 2s`).
"""

from __future__ import annotations

import ast
import time
from pathlib import Path

import numpy as np
import pytest
from quant_core.holdout_guard import HoldoutLockError
from quant_factory.capital_optimizer.policy_kernel import _pack_templates_for_numba
from quant_factory.wave4 import pareto_multi_account as pma

KERNEL_PATH = Path(pma.__file__).resolve()


def _deterministic_dev_days(n_days: int = 120) -> list[str]:
    from datetime import date, timedelta

    cur = date(2024, 12, 31)
    rev: list[str] = []
    while len(rev) < n_days:
        if cur.weekday() < 5:
            rev.append(cur.isoformat())
        cur -= timedelta(days=1)
    return list(reversed(rev))


def _make_constant_win_stage_arrays(
    n_obs: int, daily_net_usd: float, daily_dd_usd: float = 10.0
) -> tuple[np.ndarray, ...]:
    nets = np.full(n_obs, daily_net_usd, dtype=np.float64)
    dds = np.full(n_obs, daily_dd_usd, dtype=np.float64)
    ups = np.full(n_obs, max(0.0, daily_net_usd) + 10.0, dtype=np.float64)
    flgs = np.ones(n_obs, dtype=np.int8)
    return (
        nets, dds, ups, flgs,
        nets, dds, ups, flgs,
        nets, dds, ups, flgs,
        nets, dds, ups, flgs,
        nets, dds, ups, flgs,
        nets, dds, ups, flgs,
        nets, dds, ups, flgs,
    )


def _base_ftmo_template(
    *,
    contract_id: str = "ftmo_standard_10k",
    capital_usd: float = 10_000.0,
    fee_usd: float = 98.61,
    stage_arrays: tuple[np.ndarray, ...],
    p1_ea_stop: float = 0.035,
    fn_ea_stop: float = 0.025,
    p1_ea_static_stop: float = 0.080,
    fn_ea_static_stop: float = 0.075,
) -> dict:
    return {
        "contract_id": contract_id,
        "firm_idx": 0,
        "firm_id": "FTMO",
        "program_id": "ftmo_2step_standard",
        "execution_status": "MEASURED_DEMO_EXECUTION",
        "steps": 2,
        "capital_usd": capital_usd,
        "fee_day0_usd": fee_usd,
        "fee_regular_usd": fee_usd,
        "fee_refund_pct": 1.0,
        "card_fx_fee_frac": 0.025,
        "payout_withdrawal_fee_pct": 0.015,
        "withdrawal_fee_pct": 0.015,
        "refund_withdrawal_fee_pct": 0.0,
        "p1_target_pct": 0.10,
        "p2_target_pct": 0.05,
        "dd_daily_pct": 0.05,
        "dd_max_pct": 0.10,
        "dd_type": "static",
        "daily_dd_anchor": "initial_balance",
        "best_day_cap_pct": 0.0,
        "min_trading_days": 4,
        "min_profitable_days": 0,
        "min_profitable_day_pct": 0.0,
        "profit_split_pct": 0.80,
        "profit_split_max_pct": 0.90,
        "payout_cycle_trading_days": 10,
        "min_payout_usd": 50.0,
        "p1_lock_trigger": 0.70,
        "p2_lock_trigger": 0.70,
        "amber_dd": 0.035,
        "red_dd": 0.060,
        "p1_ea_stop": p1_ea_stop,
        "p2_ea_stop": 0.030,
        "fn_ea_stop": fn_ea_stop,
        "p1_ea_static_stop": p1_ea_static_stop,
        "p2_ea_static_stop": 0.075,
        "fn_ea_static_stop": fn_ea_static_stop,
        "refund_payout_milestone": 1,
        "payout_buffer_retention_pct": 0.0,
        "locks_at_initial_after_first_payout": False,
        "min_payout_profit_pct": 0.0,
        "daily_profit_cap_pct": 0.0,
        "funded_first_payout_min_prof_days": 0,
        "funded_first_payout_prof_pct": 0.0,
        "stage_arrays": stage_arrays,
    }


# ---------------------------------------------------------------------------
# 1. Exact 81-Case Grid, Law 13-15 Metrics & Fast Numba Smoke-Run (< 2s)
# ---------------------------------------------------------------------------


def test_exact_81_configs_and_ssot_fx_conversion() -> None:
    _firms, fx, _risk, hashes = pma.load_ssot_bundle()
    assert len(hashes["firms_catalog_sha256"]) == 64
    assert len(hashes["fx_rates_sha256"]) == 64

    configs = pma.build_81_case_configs(usd_vnd_rate=float(fx.usd_vnd))
    assert len(configs) == 81
    assert len({c.case_id for c in configs}) == 81
    assert tuple(sorted({c.bankroll_m_vnd for c in configs})) == (10, 15, 25, 40, 60, 100, 150, 250, 500)
    assert {c.concurrency_mode for c in configs} == set(pma.CONCURRENCY_MODES)
    assert {c.allocation_policy for c in configs} == set(pma.ALLOCATION_POLICIES)

    for cfg in configs:
        assert cfg.bankroll_vnd == pytest.approx(cfg.bankroll_m_vnd * 1_000_000.0)
        assert cfg.bankroll_usd == pytest.approx(cfg.bankroll_vnd / float(fx.usd_vnd), rel=1e-12)
        spec = pma.ALLOCATION_POLICY_SPECS[cfg.allocation_policy]
        bp = spec.to_treasury_bucket_policy(reference_ticket_usd=101.08)
        bp.validate()


def test_full_81_case_smoke_run_partitions_pareto_and_speed_under_2s() -> None:
    dev_days, trades = pma.make_synthetic_dev_trade_fixture(n_days=252, seed=20261128)

    # Warm up Numba JIT cache on 2 paths before timing the N=200 benchmark
    pma.run_pareto_81_grid(
        dev_days=dev_days,
        trades=trades,
        n_paths=2,
        horizon_days=63,
        bankroll_tiers_m_vnd=(10,),
        concurrency_modes=(pma.ConcurrencyMode.CONSERVATIVE_1_TICKET,),
        allocation_policies=(pma.AllocationPolicy.P1_RECOUP_FIRST,),
        seed=20261128,
    )

    t0 = time.perf_counter()
    res = pma.run_pareto_81_grid(
        dev_days=dev_days,
        trades=trades,
        n_paths=200,
        horizon_days=756,
        seed=20261128,
    )
    wall_s = time.perf_counter() - t0

    assert res["hard_invariants"]["order_send_capable"] is False
    assert res["hard_invariants"]["order_send_count"] == 0
    assert res["hard_invariants"]["holdout_rows_analysed"] == 0
    assert res["resolution_label_vi"] == "XẤP XỈ CẤP NGÀY"
    assert res["resolution_tag"] == "APPROX_DAILY_RESOLUTION"
    assert res["grid_shape"]["total_cases"] == 81
    assert len(res["cases"]) == 81
    assert res["runtime_benchmark"]["sim_elapsed_sec"] < 2.0, (
        f"Numba 81-case N=200 sim exceeded 2.0s budget: {res['runtime_benchmark']['sim_elapsed_sec']}s"
    )
    assert wall_s < 6.0

    # Verify EVERY case: Pass + Fail + Pending == 100.0% at 3m/6m/12m/24m/36m,
    # zero accounting error (no notional double-count), FTMO 400K base cap enforced!
    for case in res["cases"]:
        assert case["resolution_label_vi"] == "XẤP XỈ CẤP NGÀY"
        assert case["resolution_tag"] == "APPROX_DAILY_RESOLUTION"
        assert case["holdout_rows_analysed"] == 0
        assert case["max_cash_accounting_err_usd"] < 1e-6
        assert case["max_active_base_funded_usd"] <= pma.FTMO_MAX_ACTIVE_FUNDED_USD + 1e-6
        assert case["max_active_scaled_funded_usd"] <= pma.FTMO_MAX_SCALED_FUNDED_USD + 1e-6
        assert case["funded_12m_blowup"]["wilson_95_ub_pct"] >= case["funded_12m_blowup"]["blowup_12m_pct"] - 1e-9

        for hkey in ("3m", "6m", "12m", "24m", "36m"):
            fb = case["monthly_pass_fail_pending"][hkey]
            assert fb["pass_pct"] + fb["fail_pct"] + fb["pending_pct"] == pytest.approx(100.0, abs=1e-6)
            assert fb["sum_pct"] == pytest.approx(100.0, abs=1e-6)
            tb = case["first_ticket_pass_fail_pending"][hkey]
            assert tb["pass_pct"] + tb["fail_pct"] + tb["pending_pct"] == pytest.approx(100.0, abs=1e-6)

        assert case["uncond_med_pay1_cal_days_cap365"] <= 365.0 + 1e-9
        assert case["uncond_med_pay1_cal_days_cap730"] <= 730.0 + 1e-9
        assert case["median_36m_net_vnd"] == pytest.approx(
            round(case["median_36m_net_usd"] * case["usd_vnd_rate"], 0), abs=2.0
        )

    # Verify Pareto frontier non-dominance mathematically for every bankroll tier & overall
    assert len(res["pareto_frontier_by_bankroll_tier"]) == 9
    assert len(res["pareto_frontier_overall_ids"]) >= 1
    front_overall = [c for c in res["cases"] if c["is_pareto_overall"]]
    assert len(front_overall) == len(res["pareto_frontier_overall_ids"])
    for fa in front_overall:
        for fb in res["cases"]:
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
            assert not dominates, f"Pareto front case {fa['case_id']} was dominated by {fb['case_id']}"


# ---------------------------------------------------------------------------
# 2. Shared-Path Correlation Proof + Negative Mutation (Independent Fails!)
# ---------------------------------------------------------------------------


def test_shared_path_correlation_proof_and_independent_negative_mutation() -> None:
    firms, _fx, risk, _ = pma.load_ssot_bundle()
    dev_days, trades = pma.make_synthetic_dev_trade_fixture(n_days=252, seed=20261128)
    templates, _ = pma.build_ssot_templates(
        firms_catalog=firms,
        risk_profiles=risk,
        contract_ids=("ftmo_standard_50k", "ftmo_standard_100k"),
        dev_days=dev_days,
        trades=trades,
    )
    tpl_50k, tpl_100k = templates[0], templates[1]

    # Positive proof (Shared Market Path): 2 parallel accounts on same bot show rho > 0.95
    shared_stat = pma.trace_two_parallel_accounts_shared_path(
        template_a=tpl_50k,
        template_b=tpl_100k,
        n_paths=100,
        horizon_days=252,
        seed=20261128,
        shared_path=True,
    )
    assert shared_stat["mean_daily_pnl_rho"] > 0.95
    assert shared_stat["min_daily_pnl_rho"] > 0.95

    # Negative mutation proof: independent sampling breaks correlation (rho drops near 0.0!)
    indep_stat = pma.trace_two_parallel_accounts_shared_path(
        template_a=tpl_50k,
        template_b=tpl_100k,
        n_paths=100,
        horizon_days=252,
        seed=20261128,
        shared_path=False,
    )
    assert abs(indep_stat["mean_daily_pnl_rho"]) < 0.20
    assert shared_stat["mean_daily_pnl_rho"] - indep_stat["mean_daily_pnl_rho"] > 0.80

    # Also verify direct helper
    fn_50 = tpl_50k["stage_arrays"][16]
    fn_100 = tpl_100k["stage_arrays"][16]
    direct_shared = pma.measure_shared_path_daily_correlation(
        daily_net_acct_a=fn_50, daily_net_acct_b=fn_100, n_paths=100, horizon_days=252, shared_path=True
    )
    direct_indep = pma.measure_shared_path_daily_correlation(
        daily_net_acct_a=fn_50, daily_net_acct_b=fn_100, n_paths=100, horizon_days=252, shared_path=False
    )
    assert direct_shared["mean_daily_pnl_rho"] > 0.95
    assert abs(direct_indep["mean_daily_pnl_rho"]) < 0.20


# ---------------------------------------------------------------------------
# 3. Exact Penny Oracle: VN +2.5% / -1.5% Fees, P1 Fee Refund & Zero Notional Double-Count
# ---------------------------------------------------------------------------


def test_vn_fees_p1_refund_and_zero_notional_double_counting_oracle() -> None:
    """Hand-calculated deterministic oracle on FTMO 10K:
      - Day 0 buy: fee = 98.61 * 1.025 = 101.07525 USD
      - Days 0..3 (4 days): +250/day -> +1,000 (+10%) -> PASS P1!
      - Days 4..7 (4 days): +125/day? Actually constant +250/day -> 4 days = +1,000 >= +500 (+5%) -> PASS P2 -> FUNDED!
      - Days 8..17 (10 trading days = 1 payout cycle): +100/day -> +1,000 profit -> Payout #1:
          gross_share = 1000 * 0.80 = 800.00
          net_payout_1 = 800 * (1 - 0.015) = 788.00
          refund_1 = 98.61 (base fee refunded on Payout #1; VN +2.5% card FX not refunded)
          total_in_1 = 886.61
      - Days 18..27 (10 trading days): +100/day -> +1,000 profit -> Payout #2:
          net_payout_2 = 788.00, refund_2 = 0.0 (NO second refund!)
      - Total fees = 101.07525, total net payouts = 1576.00, total refund = 98.61
      - Exact net profit = 1576.00 + 98.61 - 101.07525 = 1573.53475 USD
      - Exact liquid wealth = init_bankroll + 1573.53475 USD (10,000 USD Funded notional NEVER added!)
    """
    n_obs = 40
    # Use +250/day in Eval (P1 & P2) and +100/day in Funded
    n_eval = np.full(n_obs, 250.0, dtype=np.float64)
    n_fn = np.full(n_obs, 100.0, dtype=np.float64)
    dd0 = np.full(n_obs, 5.0, dtype=np.float64)
    up_e = np.full(n_obs, 260.0, dtype=np.float64)
    up_f = np.full(n_obs, 110.0, dtype=np.float64)
    flgs = np.ones(n_obs, dtype=np.int8)
    st_arrs = (
        n_eval, dd0, up_e, flgs,
        n_eval, dd0, up_e, flgs,
        n_eval, dd0, up_e, flgs,
        n_eval, dd0, up_e, flgs,
        n_fn, dd0, up_f, flgs,
        n_fn, dd0, up_f, flgs,
        n_fn, dd0, up_f, flgs,
    )
    tpl = _base_ftmo_template(
        contract_id="ftmo_standard_10k", capital_usd=10_000.0, fee_usd=98.61, stage_arrays=st_arrs
    )
    packed = _pack_templates_for_numba([tpl])

    horizon = 28  # 4d P1 + 4d P2 + 10d Pay1 + 10d Pay2 = 28 trading days exact!
    idx_mat = np.tile(np.arange(horizon, dtype=np.int32), (1, 1))
    haz = np.full((1, 1), -1, dtype=np.int32)
    init_bankroll = 250.0  # Enough for 1 ticket ($101.08); max_slots=1 isolates 1-ticket penny oracle

    res = pma._simulate_wave4_pareto_fleet_numba(
        idx_mat,
        haz,
        *packed,
        np.array([0.025], dtype=np.float64),
        np.array([0.90], dtype=np.float64),
        np.array([0.08], dtype=np.float64),
        np.array([0.075], dtype=np.float64),
        np.array([0.075], dtype=np.float64),
        np.array([400_000.0], dtype=np.float64),
        np.array([200_000.0], dtype=np.float64),
        np.array([2_000_000.0], dtype=np.float64),
        np.array([0], dtype=np.int32),
        0,  # CONSERVATIVE_1_TICKET
        0,  # P1_RECOUP_FIRST
        init_bankroll,
        1,
        5,
        0.035,
        False,
        0.0,
        3.0,
        0.0,
        0.50,
        0.50,
    )

    net_36m = float(res[1][0])
    wealth_36m = float(res[3][0])
    own_book = float(res[4][0])
    recoup_cash = float(res[5][0])
    challenge_cash = float(res[6][0])
    fees_36m = float(res[8][0])
    payouts_36m = float(res[9][0])
    refunds_36m = float(res[10][0])
    acc_err = float(res[12][0])
    max_base_fn = float(res[31][0])

    expected_fee = 98.61 * 1.025
    expected_payouts = 2.0 * (1000.0 * 0.80 * (1.0 - 0.015))
    expected_refund = 98.61
    expected_net = expected_payouts + expected_refund - expected_fee

    assert fees_36m == pytest.approx(expected_fee, abs=1e-6)
    assert payouts_36m == pytest.approx(expected_payouts, abs=1e-6)
    assert refunds_36m == pytest.approx(expected_refund, abs=1e-6)
    assert net_36m == pytest.approx(expected_net, abs=1e-6)
    assert wealth_36m == pytest.approx(init_bankroll + expected_net, abs=1e-6)
    assert wealth_36m == pytest.approx(challenge_cash + recoup_cash + own_book, abs=1e-6)
    assert acc_err < 1e-9
    # Verify Funded notional ($10,000) is tracked separately and NEVER double-counted into cash net worth!
    assert max_base_fn == pytest.approx(10_000.0, abs=1e-6)
    assert wealth_36m < 2_500.0  # Nowhere near 10,000 + wealth!
    # Verify P1_RECOUP_FIRST banked exact initial bankroll ($250) into House Money first!
    assert recoup_cash == pytest.approx(init_bankroll, abs=1e-6)

    # Also verify with max_slots=4 that post-recoup 50% upgrade bucket opens ticket #2 cleanly!
    res_multi = pma._simulate_wave4_pareto_fleet_numba(
        idx_mat,
        haz,
        *packed,
        np.array([0.025], dtype=np.float64),
        np.array([0.90], dtype=np.float64),
        np.array([0.08], dtype=np.float64),
        np.array([0.075], dtype=np.float64),
        np.array([0.075], dtype=np.float64),
        np.array([400_000.0], dtype=np.float64),
        np.array([200_000.0], dtype=np.float64),
        np.array([2_000_000.0], dtype=np.float64),
        np.array([0], dtype=np.int32),
        0,
        0,
        init_bankroll,
        4,
        5,
        0.035,
        False,
        0.0,
        3.0,
        0.0,
        0.50,
        0.50,
    )
    assert float(res_multi[8][0]) == pytest.approx(2.0 * expected_fee, abs=1e-6)
    assert float(res_multi[12][0]) < 1e-9


# ---------------------------------------------------------------------------
# 4. FTMO 400K Active Funded Cap & Scaling Plan (+25% / 4m, 80% -> 90%)
# ---------------------------------------------------------------------------


def test_ftmo_400k_active_funded_cap_and_scaling_plan_enforcement() -> None:
    """With huge bankroll ($50,000) and AGGRESSIVE_PARALLEL + P3_SCALE_80_20:
      - Even with fast guaranteed wins, active BASE Funded capital MUST NEVER exceed $400,000 USD!
      - With `enable_scaling_plan=False`, active scaled Funded capital MUST NEVER exceed $400,000 USD!
      - With `enable_scaling_plan=True`, after 4 months (84 trading days) with >=10% profit & >=2 payouts,
        accounts scale by +25% (capped at $2,000,000 total) and split upgrades from 80% to 90%!
    """
    n_obs = 120
    # +$6,000/day on $200K -> passes P1 (+20K) in 4d, P2 (+10K) in 4d, Funded +$600/day -> +$6,000/10d payout
    n_eval = np.full(n_obs, 6_000.0, dtype=np.float64)
    n_fn = np.full(n_obs, 400.0, dtype=np.float64)  # 84 days * 400 = +$33,600 (16.8% > 10% scaling threshold!)
    dd0 = np.full(n_obs, 50.0, dtype=np.float64)
    up_e = np.full(n_obs, 6_100.0, dtype=np.float64)
    up_f = np.full(n_obs, 450.0, dtype=np.float64)
    flgs = np.ones(n_obs, dtype=np.int8)
    st_200k = (
        n_eval, dd0, up_e, flgs,
        n_eval, dd0, up_e, flgs,
        n_eval, dd0, up_e, flgs,
        n_eval, dd0, up_e, flgs,
        n_fn, dd0, up_f, flgs,
        n_fn, dd0, up_f, flgs,
        n_fn, dd0, up_f, flgs,
    )
    tpl_200k = _base_ftmo_template(
        contract_id="ftmo_standard_200k", capital_usd=200_000.0, fee_usd=1196.70, stage_arrays=st_200k
    )
    packed = _pack_templates_for_numba([tpl_200k])
    horizon = 200
    idx_mat = np.tile(np.arange(horizon, dtype=np.int32) % n_obs, (2, 1))
    haz = np.full((2, 1), -1, dtype=np.int32)

    common_args = (
        idx_mat,
        haz,
        *packed,
        np.array([0.025], dtype=np.float64),
        np.array([0.90], dtype=np.float64),
        np.array([0.08], dtype=np.float64),
        np.array([0.075], dtype=np.float64),
        np.array([0.075], dtype=np.float64),
        np.array([400_000.0], dtype=np.float64),
        np.array([200_000.0], dtype=np.float64),
        np.array([2_000_000.0], dtype=np.float64),
        np.array([0], dtype=np.int32),
        2,  # AGGRESSIVE_PARALLEL (tries to open 3x $200K = $600K, MUST cap at 2x $200K = $400K!)
        2,  # P3_SCALE_80_20
        50_000.0,
        8,
        5,
        0.035,
    )

    res_no_scale = pma._simulate_wave4_pareto_fleet_numba(*common_args, False, 0.0, 2.5, 0.10, 0.80, 0.10)
    assert float(np.max(res_no_scale[31])) == pytest.approx(400_000.0, abs=1e-6)
    assert float(np.max(res_no_scale[32])) == pytest.approx(400_000.0, abs=1e-6)
    assert int(np.sum(res_no_scale[33])) == 0  # 0 scaling upgrades when disabled
    assert int(np.min(res_no_scale[36])) > 0  # E4 cap guard actually blocked buying a 3rd 200K ticket!
    assert float(np.max(res_no_scale[12])) < 1e-6  # Exact cash conservation
    assert float(np.min(res_no_scale[4])) > 0.0  # Overflow above reserve cap spilled into Own-Book!

    res_with_scale = pma._simulate_wave4_pareto_fleet_numba(*common_args, True, 0.0, 2.5, 0.10, 0.80, 0.10)
    assert float(np.max(res_with_scale[31])) == pytest.approx(400_000.0, abs=1e-6)  # Base cap STILL 400K!
    assert float(np.max(res_with_scale[32])) > 400_000.0  # Scaled above 400K (+25% every 4m!)
    assert float(np.max(res_with_scale[32])) <= 2_000_000.0 + 1e-6
    assert int(np.min(res_with_scale[33])) >= 2  # Both 200K slots scaled!
    # Higher payouts with 90% split & +25% capital than without scaling
    assert float(np.mean(res_with_scale[9])) > float(np.mean(res_no_scale[9]))
    assert float(np.max(res_with_scale[12])) < 1e-6  # Still ZERO double-counting of +50K notional into cash!


# ---------------------------------------------------------------------------
# 5. Per-SKU 0.01-Lot Floor Sensitivity (Bug Pattern #4: NO Linear Scaling!)
# ---------------------------------------------------------------------------


def test_per_sku_001_lot_floor_sensitivity_breaks_linear_scaling() -> None:
    """Prove `5K` and `10K` suffer real `0.01`-lot rejection/floor drag vs `100K` (never linearly scaled!)."""
    dev_days = _deterministic_dev_days(60)
    # Trades with small base risk (0.1606% like E1_USDJPY_TOKYO) & $1,000 1-lot SL:
    # - On 5K @ 1.0x: budget = $8.03 -> raw_lots = 0.00803 < 0.01 -> 100% REJECTED!
    # - On 10K @ 1.0x: budget = $16.06 -> raw_lots = 0.01606 -> floored to 0.01 (62.3% utilization)
    # - On 100K @ 1.0x: budget = $160.60 -> raw_lots = 0.1606 -> floored to 0.16 (99.6% utilization)
    trades = [
        {
            "day": dk,
            "base_risk_frac": 0.001606,
            "stop_risk_with_cost_usd": 1000.0,
            "net_usd_per_lot": 400.0,
            "intraday_dd_usd_per_lot": 150.0,
            "intraday_up_usd_per_lot": 450.0,
        }
        for dk in dev_days
    ]

    audit = pma.audit_per_sku_lot_floor_sensitivity(dev_days=dev_days, trades=trades, funded_mult=1.0)
    assert audit["holdout_rows_analysed"] == 0
    s5 = audit["skus"]["5K"]
    s10 = audit["skus"]["10K"]
    s100 = audit["skus"]["100K"]

    assert s5["min_lot_reject_pct"] == pytest.approx(100.0)
    assert s5["sized_trades"] == 0
    assert s5["total_net_usd"] == pytest.approx(0.0)

    assert s10["min_lot_reject_pct"] == pytest.approx(0.0)
    assert s10["mean_risk_utilization_pct"] == pytest.approx(62.27, abs=0.1)
    assert s100["mean_risk_utilization_pct"] == pytest.approx(99.63, abs=0.1)
    # Linear scaling from 100K would grossly overstate 5K and 10K EV/capital!
    assert s100["ev_pct_of_capital"] > s10["ev_pct_of_capital"] > s5["ev_pct_of_capital"]
    assert s10["linear_from_100k_overstatement_pct"] > 30.0
    assert s5["linear_from_100k_overstatement_pct"] == pytest.approx(100.0)


# ---------------------------------------------------------------------------
# 6. BOT_AUTO_KILL vs FIRM_HARD_BREACH, The5ers Tag, Holdout & Poisoned Inputs
# ---------------------------------------------------------------------------


def test_bot_auto_kill_separated_from_firm_hard_breach() -> None:
    """Raw daily DD = $400 (4.0% < 5.0% firm cap, > 3.5% EA stop) triggers BOT_AUTO_KILL with 0 FIRM_HARD_BREACH.
    Raw daily DD = $600 (6.0% > 5.0% firm cap) MUST trigger FIRM_HARD_BREACH (Bug A invariant!).
    """
    # Case A: $400 DD -> BOT_AUTO_KILL only, survives!
    st_kill = _make_constant_win_stage_arrays(10, daily_net_usd=-390.0, daily_dd_usd=400.0)
    tpl_a = _base_ftmo_template(stage_arrays=st_kill, p1_ea_stop=0.035)
    packed_a = _pack_templates_for_numba([tpl_a])
    idx_1 = np.zeros((1, 1), dtype=np.int32)
    haz = np.full((1, 1), -1, dtype=np.int32)
    res_a = pma._simulate_wave4_pareto_fleet_numba(
        idx_1, haz, *packed_a,
        np.array([0.025]), np.array([0.90]), np.array([0.08]), np.array([0.075]), np.array([0.075]),
        np.array([400_000.0]), np.array([200_000.0]), np.array([2_000_000.0]),
        np.array([0], dtype=np.int32), 0, 0, 150.0, 2, 5, 0.035, False, 0.0, 3.0, 0.0, 0.5, 0.5,
    )
    assert int(res_a[21][0]) == 1  # bot_kill_events == 1
    assert int(res_a[22][0]) == 0  # firm_breach_events == 0

    # Case B: $600 DD (> 5% firm cap) -> FIRM_HARD_BREACH immediately BEFORE EA stop!
    st_br = _make_constant_win_stage_arrays(10, daily_net_usd=-550.0, daily_dd_usd=600.0)
    tpl_b = _base_ftmo_template(stage_arrays=st_br, p1_ea_stop=0.035)
    packed_b = _pack_templates_for_numba([tpl_b])
    res_b = pma._simulate_wave4_pareto_fleet_numba(
        idx_1, haz, *packed_b,
        np.array([0.025]), np.array([0.90]), np.array([0.08]), np.array([0.075]), np.array([0.075]),
        np.array([400_000.0]), np.array([200_000.0]), np.array([2_000_000.0]),
        np.array([0], dtype=np.int32), 0, 0, 150.0, 2, 5, 0.035, False, 0.0, 3.0, 0.0, 0.5, 0.5,
    )
    assert int(res_b[22][0]) == 1  # firm_breach_events == 1
    assert int(res_b[25][0]) == 1  # firm_breach_daily_any == 1


def test_the5ers_rows_tagged_terms_verified_execution_unmeasured() -> None:
    dev_days, trades = pma.make_synthetic_dev_trade_fixture(n_days=60, seed=42)
    res = pma.run_pareto_81_grid(
        dev_days=dev_days,
        trades=trades,
        n_paths=10,
        horizon_days=63,
        contract_ids=("the5ers_hs_5k_classic", "the5ers_hs_5k_new"),
        bankroll_tiers_m_vnd=(10,),
        concurrency_modes=(pma.ConcurrencyMode.CONSERVATIVE_1_TICKET,),
        allocation_policies=(pma.AllocationPolicy.P1_RECOUP_FIRST,),
        seed=42,
    )
    assert res["execution_status"] == "TERMS_VERIFIED_EXECUTION_UNMEASURED"
    assert res["cases"][0]["execution_status"] == "TERMS_VERIFIED_EXECUTION_UNMEASURED"


def test_holdout_2025_and_poisoned_inputs_fail_closed_under_python_O() -> None:
    # 2025-01-01 Holdout injection MUST raise HoldoutLockError (even under `python -O`!)
    with pytest.raises(HoldoutLockError):
        pma.build_per_sku_stage_arrays_from_trades(
            dev_days=["2024-12-31", "2025-01-01"],
            trades=[],
            capital_usd=10_000.0,
        )

    # Poisoned bool / NaN / Inf inputs MUST fail closed with ValueError (Bug Pattern #3!)
    for bad in (True, False, float("nan"), float("inf"), -1.0):
        with pytest.raises(ValueError):
            pma.build_81_case_configs(usd_vnd_rate=bad)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        pma.build_per_sku_stage_arrays_from_trades(
            dev_days=["2024-12-30"],
            trades=[
                {
                    "day": "2024-12-30",
                    "base_risk_frac": True,
                    "stop_risk_with_cost_usd": 100.0,
                    "net_usd_per_lot": 50.0,
                }
            ],
            capital_usd=10_000.0,
        )

    # Unavailable VN contract (`ftmo_swing_50k`) MUST fail closed
    firms, _fx, risk, _ = pma.load_ssot_bundle()
    with pytest.raises(ValueError, match="CONTRACT_UNAVAILABLE_VN"):
        pma.build_ssot_templates(
            firms_catalog=firms,
            risk_profiles=risk,
            contract_ids=("ftmo_swing_50k",),
            dev_days=["2024-12-30"],
            trades=[],
        )


def test_zero_bare_asserts_in_production_module_arch02() -> None:
    tree = ast.parse(KERNEL_PATH.read_text(encoding="utf-8"))
    asserts = [node.lineno for node in ast.walk(tree) if isinstance(node, ast.Assert)]
    assert asserts == [], f"Forbidden bare assert(s) in production kernel [ARCH-02]: lines {asserts}"

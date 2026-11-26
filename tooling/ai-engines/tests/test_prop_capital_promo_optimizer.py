"""Comprehensive offline & CI-safe unit tests for `prop_capital_promo_optimizer.py` (v2 — Astra R10 Closures).

Strictly zero `.runtime/` dependency, zero `private_vault/` dependency, `OrderSend = 0`, `Holdout = 0`.
Covers ALL 10 v2 invariants & Astra Round 10 Q3 closures:
  1. Hard invariants (`ORDER_SEND_COUNT == 0`, `holdout_rows_analysed == 0`, fail-closed `>= 2025-01-01`).
  2. Exact `0.01`-lot rounding monotonicity (`100K` reject rate `<= 10K <= 5K`, utilization improves with tier).
  3. VN pricing traps (`25K` fee-ratio trap, `200K == 2x 100K` parity, `Swing >= 50K` VN disabled).
  4. NPV discounting monotonicity (`NPV(8%) < NPV(6%) < NPV(4%) < undiscounted(0%)`) & `Pass+Fail+Pending == 100%`.
  5. Exact challenge rule-engine physics: `50%` Best Day (1-Step), `30%` Best Day + Intraday Trailing (Instant),
     `3x >= 0.5%` profitable days (The5ers), E8 `2%` daily profit cap, IC Funded 3rd-payout refund + 5x `0.5%`.
  6. `2x 100K` sequential strictly dominates `1x 200K` on ruin at constrained bankroll.
  7. Primary variant locked to `C10_NEWS_ON` (Red-News ON all phases) with `C00` control.
  8. Fail-closed catalog loader (`allow_fallback=False`) + per-program & per-tier `verified_utc` staleness guard.
  9. Purchase-day ticket pricing (`fee_day0_usd` vs `fee_regular_usd` on retries — NO perpetual BF discount!).
 10. Per-contract `daily_dd_anchor` (`initial_balance` static vs `prev_day_balance` / `balance_or_equity`).
 11. B3 `own_book` OFF (`0.0`) & B4 `E8 Pro` excluded from `P5/P5B` + Payout #1 buffer sensitivity.
 12. B2 `P4A_WAIT_FOR_100K` (`wait_for_top_rung_slot2=True`) holds Slot 2 for `100K` + Pareto exposes `median` & `P(<=0)`.
 13. B5 Dual-Horizon Dynamic Sale Calculator (exact sweep `Y=0..max`, NO binary search, NO `2*d7` shortcut, shifting formula + MC).
 14. B6 Fee accounting separation (`+2.5%` buy FX, `0.0%` FTMO card refund vs `1.5%` rail, payout rail) + `P4B_PARALLEL_2X100K` Day-0 dual open & same-day DD correlation.
 15. Live `prop_pricing_catalog.json` integration, daily DD anchor mapping, and zero bare `$` report guard.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

AI_ENGINES = Path(__file__).resolve().parents[1]
if str(AI_ENGINES) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES))

from quant_factory import prop_capital_promo_optimizer as opt  # noqa: E402


def _make_synthetic_stage_arrays(
    n_obs: int = 300,
    *,
    cap: float = 10_000.0,
    mean_pct: float = 0.0008,
    vol_pct: float = 0.0060,
    seed: int = 42,
) -> tuple[np.ndarray, ...]:
    """Build realistic synthetic daily stage arrays (in exact USD for `cap`) for fast deterministic unit tests."""
    rng = np.random.default_rng(seed)
    base_ret = rng.normal(mean_pct, vol_pct, size=n_obs)
    base_dd = np.abs(rng.normal(vol_pct * 0.8, vol_pct * 0.4, size=n_obs)) + np.maximum(0.0, -base_ret)
    base_up = np.abs(rng.normal(vol_pct * 0.6, vol_pct * 0.3, size=n_obs)) + np.maximum(0.0, base_ret)
    flg = np.ones(n_obs, dtype=np.int8)

    def _scaled(m: float) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        return (
            np.ascontiguousarray(base_ret * cap * m, dtype=np.float64),
            np.ascontiguousarray(base_dd * cap * m, dtype=np.float64),
            np.ascontiguousarray(base_up * cap * m, dtype=np.float64),
            flg.copy(),
        )

    return (
        *_scaled(3.5),  # p1
        *_scaled(2.0),  # p1_lock
        *_scaled(2.0),  # p2
        *_scaled(1.0),  # p2_lock
        *_scaled(1.0),  # funded
        *_scaled(0.65), # amber
        *_scaled(0.40), # red
    )


def _base_tpl(
    cap: float,
    fee_day0: float,
    fee_reg: float,
    arrs: tuple[np.ndarray, ...],
    *,
    firm_idx: int = 0,
    steps: int = 2,
    dd_daily: float = 0.05,
    dd_max: float = 0.10,
    daily_dd_anchor: str = "initial_balance",
    wd_fee: float = 0.015,
    ref_wd_fee: float = 0.0,
    fee_refund: float = 1.0,
) -> dict:
    return {
        "firm_idx": firm_idx,
        "steps": steps,
        "capital_usd": cap,
        "fee_day0_usd": fee_day0,
        "fee_regular_usd": fee_reg,
        "fee_refund_pct": fee_refund,
        "payout_withdrawal_fee_pct": wd_fee,
        "withdrawal_fee_pct": wd_fee,
        "refund_withdrawal_fee_pct": ref_wd_fee,
        "p1_target_pct": 0.10 if steps > 0 else 0.0,
        "p2_target_pct": 0.05 if steps == 2 else 0.0,
        "dd_daily_pct": dd_daily,
        "dd_max_pct": dd_max,
        "dd_type": "static",
        "daily_dd_anchor": daily_dd_anchor,
        "best_day_cap_pct": 0.0,
        "min_trading_days": 4 if steps == 2 else 0,
        "min_profitable_days": 0,
        "min_profitable_day_pct": 0.0,
        "profit_split_pct": 0.80,
        "payout_cycle_trading_days": 10,
        "min_payout_usd": 50.0,
        "p1_lock_trigger": 0.70,
        "p2_lock_trigger": 0.70,
        "amber_dd": 0.035,
        "red_dd": 0.060,
        "p1_ea_stop": 0.035,
        "p2_ea_stop": 0.030,
        "fn_ea_stop": 0.025,
        "stage_arrays": arrs,
    }


class PropCapitalPromoOptimizerTests(unittest.TestCase):
    def test_01_hard_invariants_and_holdout_refusal(self) -> None:
        self.assertFalse(opt.ORDER_SEND_CAPABLE)
        self.assertEqual(opt.ORDER_SEND_COUNT, 0)
        self.assertEqual(opt.assert_strict_pre_holdout_days(["2018-01-02", "2024-12-31"]), 0)

        with self.assertRaisesRegex(ValueError, "HOLDOUT_LOCK_VIOLATION"):
            opt.assert_strict_pre_holdout_days(["2024-12-31", "2025-01-01"])

        bad_trades = [{
            "day": "2025-01-02",
            "year": 2025,
            "base_risk_frac": 0.005,
            "stop_risk_with_cost_usd": 500.0,
            "net_usd_per_lot": 250.0,
        }]
        with self.assertRaisesRegex(ValueError, "HOLDOUT_LOCK_VIOLATION"):
            opt.simulate_exact_lot_rounding_on_trade_list(bad_trades, capital_usd=10_000.0)

    def test_02_exact_001_lot_rounding_monotonicity(self) -> None:
        self.assertEqual(opt.floor_lot_step(0.0099), 0.0)
        self.assertEqual(opt.floor_lot_step(0.0100), 0.01)
        self.assertEqual(opt.floor_lot_step(0.0199), 0.01)
        self.assertEqual(opt.floor_lot_step(0.159), 0.15)

        rng = np.random.default_rng(123)
        trades = []
        for i in range(400):
            stop_c = float(rng.uniform(350.0, 950.0))
            win = (i % 2 == 0)
            net_1lot = stop_c * (1.25 if win else -1.0)
            trades.append({
                "day": f"2023-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}",
                "year": 2023,
                "base_risk_frac": 0.0016 if (i % 4 == 0) else 0.0050,
                "stop_risk_with_cost_usd": stop_c,
                "net_usd_per_lot": net_1lot,
            })

        r5 = opt.simulate_exact_lot_rounding_on_trade_list(trades, capital_usd=5_000.0, risk_mult=1.0)
        r10 = opt.simulate_exact_lot_rounding_on_trade_list(trades, capital_usd=10_000.0, risk_mult=1.0)
        r50 = opt.simulate_exact_lot_rounding_on_trade_list(trades, capital_usd=50_000.0, risk_mult=1.0)
        r100 = opt.simulate_exact_lot_rounding_on_trade_list(trades, capital_usd=100_000.0, risk_mult=1.0)

        self.assertEqual(r5["holdout_rows_analysed"], 0)
        self.assertEqual(r100["holdout_rows_analysed"], 0)
        self.assertGreater(r5["min_lot_reject_pct"], r100["min_lot_reject_pct"])
        self.assertLessEqual(r100["min_lot_reject_pct"], r10["min_lot_reject_pct"])
        self.assertLessEqual(r10["min_lot_reject_pct"], r5["min_lot_reject_pct"])
        self.assertGreater(r100["mean_risk_utilization_pct"], r50["mean_risk_utilization_pct"] - 0.5)
        self.assertGreater(r50["mean_risk_utilization_pct"], r10["mean_risk_utilization_pct"])
        self.assertGreater(r10["mean_risk_utilization_pct"], r5["mean_risk_utilization_pct"])
        self.assertGreater(r100["ann_return_pct"], r5["ann_return_pct"])

    def test_03_vn_pricing_traps_detected(self) -> None:
        cat = opt.build_default_pricing_catalog()
        traps = opt.detect_pricing_traps(cat)
        self.assertTrue(traps["trap_25k_detected"])
        self.assertTrue(traps["parity_200k_vs_2x100k_detected"])
        self.assertTrue(traps["swing_50k_plus_unavailable_vn"])
        ratios = traps["details"]["ftmo_2step_std_fee_ratio_pct"]
        self.assertGreater(ratios["25K_promo_pct"], ratios["10K_promo_pct"])
        self.assertGreater(ratios["25K_promo_pct"], ratios["50K_promo_pct"])
        self.assertAlmostEqual(ratios["100K_promo_pct"], ratios["200K_promo_pct"], places=4)

    def test_04_npv_discounting_strictly_below_undiscounted_and_pass_fail_pending_sum_100(self) -> None:
        idx = opt.make_block_bootstrap_indices(300, horizon=504, n_paths=400, seed=7)
        arrs = _make_synthetic_stage_arrays(300, cap=100_000.0, mean_pct=0.0012, vol_pct=0.0045, seed=7)

        npvs = {}
        for r in (0.0, 0.04, 0.06, 0.08):
            res = opt._simulate_single_ticket_rules_numba(
                idx, *arrs,
                steps=2, cap=100_000.0, fee_day0_usd=478.68, fee_regular_usd=598.35,
                card_fx_fee_pct=0.025, withdrawal_fee_pct=0.015, fee_refund_pct=1.0,
                p1_target=0.10, p2_target=0.05, daily_lim=0.05, max_dd_lim=0.10,
                dd_type=opt.DD_STATIC, trail_lock_initial=False, best_day_cap_pct=0.0,
                min_days=4, min_prof_days=0, min_prof_day_pct=0.0,
                profit_split=0.80, payout_cycle_days=10, min_payout_usd=50.0,
                strict_lt_breach=True, p1_lock_trigger=0.70, p2_lock_trigger=0.70,
                amber_dd=0.035, red_dd=0.060, p1_ea_stop=0.035, p2_ea_stop=0.030, fn_ea_stop=0.025,
                start_day_offset=0, discount_rate_annual=r, max_retries=0,
                refund_withdrawal_fee_pct=0.0, daily_dd_anchor_mode=opt.DAILY_DD_ANCHOR_INITIAL_BALANCE,
            )
            summ = opt.summarize_single_ticket_mc(
                res, fee_usd=478.68, fee_regular_usd=598.35, card_fx_fee_pct=0.025,
                usd_vnd_rate=25_765.94, horizon_days=504,
            )
            npvs[r] = summ["ev_npv_24m_usd"]
            for mkey, row in summ["monthly_pass_fail_pending"].items():
                self.assertAlmostEqual(
                    row["pass_pct"] + row["fail_pct"] + row["pending_pct"],
                    100.0,
                    places=1,
                    msg=f"Pass+Fail+Pending must sum to 100% at {mkey}",
                )

        self.assertGreater(npvs[0.0], 0.0)
        self.assertLess(npvs[0.06], npvs[0.0])
        self.assertLess(npvs[0.08], npvs[0.06])
        self.assertLess(npvs[0.06], npvs[0.04])

    def test_05_rule_engine_best_day_consistency_profitable_days_and_intraday_trailing(self) -> None:
        n_obs = 60
        nets = np.zeros(n_obs, dtype=np.float64)
        dds = np.zeros(n_obs, dtype=np.float64)
        ups = np.zeros(n_obs, dtype=np.float64)
        flg = np.ones(n_obs, dtype=np.int8)
        nets[0] = 1_100.0
        for d in range(1, 20):
            nets[d] = 100.0
        arrs = (nets, dds, ups, flg) * 7
        idx = np.arange(n_obs, dtype=np.int32).reshape(1, n_obs)

        res_cons = opt._simulate_single_ticket_rules_numba(
            idx, *arrs,
            steps=1, cap=10_000.0, fee_day0_usd=60.94, fee_regular_usd=87.53,
            card_fx_fee_pct=0.025, withdrawal_fee_pct=0.015, fee_refund_pct=0.0,
            p1_target=0.10, p2_target=0.0, daily_lim=0.03, max_dd_lim=0.10,
            dd_type=opt.DD_EOD_TRAILING, trail_lock_initial=False, best_day_cap_pct=0.50,
            min_days=0, min_prof_days=0, min_prof_day_pct=0.0,
            profit_split=0.90, payout_cycle_days=10, min_payout_usd=50.0,
            strict_lt_breach=True, p1_lock_trigger=0.50, p2_lock_trigger=0.50,
            amber_dd=0.025, red_dd=0.045, p1_ea_stop=0.021, p2_ea_stop=0.021, fn_ea_stop=0.018,
            start_day_offset=0, discount_rate_annual=0.06, max_retries=0,
        )
        self.assertEqual(int(res_cons[0][0]), 12)

        nets_5 = np.zeros(n_obs, dtype=np.float64)
        nets_5[0] = 850.0
        nets_5[1] = 60.0
        nets_5[2] = 60.0
        arrs_5 = (nets_5, dds, ups, flg) * 7
        res_5 = opt._simulate_single_ticket_rules_numba(
            idx, *arrs_5,
            steps=1, cap=10_000.0, fee_day0_usd=39.0, fee_regular_usd=39.0,
            card_fx_fee_pct=0.025, withdrawal_fee_pct=0.040, fee_refund_pct=0.70,
            p1_target=0.08, p2_target=0.0, daily_lim=0.05, max_dd_lim=0.10,
            dd_type=opt.DD_STATIC, trail_lock_initial=False, best_day_cap_pct=0.0,
            min_days=3, min_prof_days=3, min_prof_day_pct=0.005,
            profit_split=0.80, payout_cycle_days=10, min_payout_usd=150.0,
            strict_lt_breach=True, p1_lock_trigger=0.50, p2_lock_trigger=0.50,
            amber_dd=0.035, red_dd=0.060, p1_ea_stop=0.035, p2_ea_stop=0.025, fn_ea_stop=0.025,
            start_day_offset=0, discount_rate_annual=0.06, max_retries=0,
            daily_dd_anchor_mode=opt.DAILY_DD_ANCHOR_PREV_DAY_BALANCE,
        )
        self.assertEqual(int(res_5[0][0]), 3)

        nets_t = np.zeros(n_obs, dtype=np.float64)
        dds_t = np.zeros(n_obs, dtype=np.float64)
        ups_t = np.zeros(n_obs, dtype=np.float64)
        ups_t[0] = 1_000.0
        dds_t[0] = 150.0
        arrs_t = (nets_t, dds_t, ups_t, flg) * 7
        res_t = opt._simulate_single_ticket_rules_numba(
            idx, *arrs_t,
            steps=0, cap=10_000.0, fee_day0_usd=300.29, fee_regular_usd=375.36,
            card_fx_fee_pct=0.025, withdrawal_fee_pct=0.015, fee_refund_pct=0.0,
            p1_target=0.0, p2_target=0.0, daily_lim=0.03, max_dd_lim=0.10,
            dd_type=opt.DD_INTRADAY_TRAILING, trail_lock_initial=False, best_day_cap_pct=0.30,
            min_days=0, min_prof_days=0, min_prof_day_pct=0.0,
            profit_split=0.90, payout_cycle_days=10, min_payout_usd=50.0,
            strict_lt_breach=True, p1_lock_trigger=0.50, p2_lock_trigger=0.50,
            amber_dd=0.025, red_dd=0.045, p1_ea_stop=0.021, p2_ea_stop=0.021, fn_ea_stop=0.025,
            start_day_offset=0, discount_rate_annual=0.06, max_retries=0,
        )
        self.assertEqual(int(res_t[6][0]), 1)
        self.assertEqual(int(res_t[8][0]), 1)

    def test_06_two_x_100k_strictly_dominates_1x_200k_on_ruin_at_equal_fee_ratio(self) -> None:
        idx = opt.make_block_bootstrap_indices(300, horizon=504, n_paths=1_000, seed=99)
        haz = opt.make_firm_hazard_days(1_000, 1, 0.0, horizon=504, seed=99)
        arr100 = _make_synthetic_stage_arrays(300, cap=100_000.0, mean_pct=0.0005, vol_pct=0.0095, seed=99)
        arr200 = _make_synthetic_stage_arrays(300, cap=200_000.0, mean_pct=0.0005, vol_pct=0.0095, seed=99)

        tpls = [
            _base_tpl(100_000.0, 478.68, 598.35, arr100),
            _base_tpl(200_000.0, 957.36, 1196.70, arr200),
        ]
        packed = opt._pack_templates_for_numba(tpls)
        r100 = opt._simulate_capital_policy_numba(
            idx, haz, *packed,
            policy_mode=1, ladder_tpls=np.array([0], dtype=np.int32), max_slots=2,
            allow_downgrade=False, upgrade_buf_mult=2.5, downgrade_buf_mult=2.0,
            init_bankroll_usd=1_500.0, monthly_topup_usd=0.0, card_fx_fee_pct=0.025,
            discount_rate_annual=0.06, own_book_overflow_mult=0.0, own_book_daily_ret=0.0,
            abort_after_day=-1, wait_for_top_rung_slot2=False,
        )
        r200 = opt._simulate_capital_policy_numba(
            idx, haz, *packed,
            policy_mode=1, ladder_tpls=np.array([1], dtype=np.int32), max_slots=1,
            allow_downgrade=False, upgrade_buf_mult=2.5, downgrade_buf_mult=2.0,
            init_bankroll_usd=1_500.0, monthly_topup_usd=0.0, card_fx_fee_pct=0.025,
            discount_rate_annual=0.06, own_book_overflow_mult=0.0, own_book_daily_ret=0.0,
            abort_after_day=-1, wait_for_top_rung_slot2=False,
        )
        s100 = opt.summarize_capital_policy_mc(r100, usd_vnd_rate=25_765.94, init_bankroll_vnd_tr=38.0, monthly_topup_vnd_tr=0.0)
        s200 = opt.summarize_capital_policy_mc(r200, usd_vnd_rate=25_765.94, init_bankroll_vnd_tr=38.0, monthly_topup_vnd_tr=0.0)
        self.assertLess(s100["ruin_pct"], s200["ruin_pct"])
        self.assertEqual(s100["mean_own_book_36m_usd"], 0.0)
        self.assertEqual(s200["mean_own_book_36m_usd"], 0.0)

    def test_07_sunk_cost_abort_saves_fees_in_negative_ev_regime(self) -> None:
        idx = opt.make_block_bootstrap_indices(300, horizon=504, n_paths=500, seed=77)
        haz = opt.make_firm_hazard_days(500, 1, 0.0, horizon=504, seed=77)
        arr_neg = _make_synthetic_stage_arrays(300, cap=50_000.0, mean_pct=-0.0010, vol_pct=0.0080, seed=77)
        tpl = [_base_tpl(50_000.0, 305.83, 382.28, arr_neg)]
        packed = opt._pack_templates_for_numba(tpl)
        r_blind = opt._simulate_capital_policy_numba(
            idx, haz, *packed,
            policy_mode=1, ladder_tpls=np.array([0], dtype=np.int32), max_slots=1,
            allow_downgrade=False, upgrade_buf_mult=2.5, downgrade_buf_mult=2.0,
            init_bankroll_usd=1_500.0, monthly_topup_usd=0.0, card_fx_fee_pct=0.025,
            discount_rate_annual=0.06, own_book_overflow_mult=0.0, own_book_daily_ret=0.0,
            abort_after_day=-1, wait_for_top_rung_slot2=False,
        )
        r_abort = opt._simulate_capital_policy_numba(
            idx, haz, *packed,
            policy_mode=1, ladder_tpls=np.array([0], dtype=np.int32), max_slots=1,
            allow_downgrade=False, upgrade_buf_mult=2.5, downgrade_buf_mult=2.0,
            init_bankroll_usd=1_500.0, monthly_topup_usd=0.0, card_fx_fee_pct=0.025,
            discount_rate_annual=0.06, own_book_overflow_mult=0.0, own_book_daily_ret=0.0,
            abort_after_day=42, wait_for_top_rung_slot2=False,
        )
        s_blind = opt.summarize_capital_policy_mc(r_blind, usd_vnd_rate=25_765.94, init_bankroll_vnd_tr=38.0, monthly_topup_vnd_tr=0.0)
        s_abort = opt.summarize_capital_policy_mc(r_abort, usd_vnd_rate=25_765.94, init_bankroll_vnd_tr=38.0, monthly_topup_vnd_tr=0.0)
        self.assertLess(s_abort["mean_fees_24m_usd"], s_blind["mean_fees_24m_usd"])
        self.assertGreater(s_abort["ev_npv_24m_usd"], s_blind["ev_npv_24m_usd"])

    def test_08_e8_daily_profit_cap_buffer_wait_and_ic_funded_3rd_payout_refund(self) -> None:
        n_obs = 80
        idx = np.arange(n_obs, dtype=np.int32).reshape(1, n_obs)
        dds = np.zeros(n_obs, dtype=np.float64)
        ups = np.zeros(n_obs, dtype=np.float64)
        flg = np.ones(n_obs, dtype=np.int8)

        # (a) E8 Pro 2% daily profit cap delays 8% target pass from Day 2 to Day 4;
        # AND funded_first_payout_min_profit_pct=0.08 delays Payout #1 until +8% profit!
        nets_e8 = np.full(n_obs, 500.0, dtype=np.float64)  # capped at +$200/day (+2%)
        arrs_e8 = (nets_e8, dds, ups, flg) * 7
        res_e8_p1 = opt._simulate_single_ticket_rules_numba(
            idx, *arrs_e8,
            steps=1, cap=10_000.0, fee_day0_usd=58.0, fee_regular_usd=68.0,
            card_fx_fee_pct=0.025, withdrawal_fee_pct=0.020, fee_refund_pct=0.0,
            p1_target=0.08, p2_target=0.0, daily_lim=0.025, max_dd_lim=0.08,
            dd_type=opt.DD_STATIC, trail_lock_initial=False, best_day_cap_pct=0.0,
            min_days=0, min_prof_days=0, min_prof_day_pct=0.0,
            profit_split=0.80, payout_cycle_days=1, min_payout_usd=100.0,
            strict_lt_breach=True, p1_lock_trigger=0.50, p2_lock_trigger=0.50,
            amber_dd=0.020, red_dd=0.040, p1_ea_stop=0.0175, p2_ea_stop=0.0175, fn_ea_stop=0.015,
            start_day_offset=0, discount_rate_annual=0.0, max_retries=0,
            refund_payout_milestone=0, payout_buffer_retention_pct=0.50,
            locks_at_initial_after_first_payout=True, min_payout_profit_pct=0.01,
            daily_profit_cap_pct=0.02, funded_first_payout_min_profit_pct=0.08,
        )
        # Passes on Day 4 (+8%), then Funded needs 4 days at +2%/day = +8% -> Payout #1 on Day 8!
        self.assertEqual(int(res_e8_p1[0][0]), 4)
        self.assertEqual(int(res_e8_p1[2][0]), 8)

        # (b) IC Funded 3rd-payout refund + 5x >= 0.5% first-payout hurdle
        nets_ic = np.full(n_obs, 60.0, dtype=np.float64)
        arrs_ic = (nets_ic, dds, ups, flg) * 7
        res_ic1 = opt._simulate_single_ticket_rules_numba(
            idx[:, :25], *arrs_ic,
            steps=0, cap=10_000.0, fee_day0_usd=125.0, fee_regular_usd=125.0,
            card_fx_fee_pct=0.0, withdrawal_fee_pct=0.0, fee_refund_pct=1.0,
            p1_target=0.0, p2_target=0.0, daily_lim=0.05, max_dd_lim=0.10,
            dd_type=opt.DD_STATIC, trail_lock_initial=False, best_day_cap_pct=0.0,
            min_days=0, min_prof_days=0, min_prof_day_pct=0.0,
            profit_split=0.80, payout_cycle_days=10, min_payout_usd=100.0,
            strict_lt_breach=True, p1_lock_trigger=0.50, p2_lock_trigger=0.50,
            amber_dd=0.035, red_dd=0.060, p1_ea_stop=0.035, p2_ea_stop=0.025, fn_ea_stop=0.025,
            start_day_offset=0, discount_rate_annual=0.0, max_retries=0,
            refund_payout_milestone=3, funded_first_payout_min_prof_days=5,
            funded_first_payout_prof_pct=0.005, refund_withdrawal_fee_pct=0.0,
        )
        res_ic3 = opt._simulate_single_ticket_rules_numba(
            idx[:, :35], *arrs_ic,
            steps=0, cap=10_000.0, fee_day0_usd=125.0, fee_regular_usd=125.0,
            card_fx_fee_pct=0.0, withdrawal_fee_pct=0.0, fee_refund_pct=1.0,
            p1_target=0.0, p2_target=0.0, daily_lim=0.05, max_dd_lim=0.10,
            dd_type=opt.DD_STATIC, trail_lock_initial=False, best_day_cap_pct=0.0,
            min_days=0, min_prof_days=0, min_prof_day_pct=0.0,
            profit_split=0.80, payout_cycle_days=10, min_payout_usd=100.0,
            strict_lt_breach=True, p1_lock_trigger=0.50, p2_lock_trigger=0.50,
            amber_dd=0.035, red_dd=0.060, p1_ea_stop=0.035, p2_ea_stop=0.025, fn_ea_stop=0.025,
            start_day_offset=0, discount_rate_annual=0.0, max_retries=0,
            refund_payout_milestone=3, funded_first_payout_min_prof_days=5,
            funded_first_payout_prof_pct=0.005, refund_withdrawal_fee_pct=0.0,
        )
        self.assertAlmostEqual(float(res_ic1[14][0]), 960.0, places=2)
        self.assertAlmostEqual(float(res_ic3[14][0]), 1565.0, places=2)

    # -----------------------------------------------------------------------
    # Astra Round 10 Q3 Closure Tests (Fixes 1–10)
    # -----------------------------------------------------------------------

    def test_09_primary_variant_is_c10_news_on_with_c00_control(self) -> None:
        self.assertEqual(opt.PRIMARY_VARIANT_DEFAULT, "C10_NEWS_ON")
        self.assertEqual(opt.CONTROL_VARIANT_DEFAULT, "C00")
        vc = opt.VARIANT_PHASE_CONFIGS["C10_NEWS_ON"]
        self.assertTrue(vc["p1_news_guard"])
        self.assertTrue(vc["p2_news_guard"])
        self.assertTrue(vc["funded_news_guard"])

        with tempfile.TemporaryDirectory() as td:
            s5_path = Path(td) / "s5.json"
            s5_path.write_text(json.dumps({"overall_ranking_stability_verdict": "C10_DOMINATES_ECONOMIC_ZERO_FLIP"}), encoding="utf-8")
            s5 = opt.load_step5_c00_c10_summary(s5_path)
            self.assertEqual(s5["primary_variant"], "C10_NEWS_ON")
            self.assertEqual(s5["control_variant"], "C00")

    def test_10_fail_closed_catalog_load_and_per_tier_staleness_enforcement(self) -> None:
        now = datetime(2026, 11, 26, 16, 0, 0, tzinfo=timezone.utc)
        fresh_ts = "2026-11-26T12:00:00Z"
        stale_ts = "2026-11-10T12:00:00Z"  # 16 days old > 7d staleness_max_days

        with tempfile.TemporaryDirectory() as td:
            missing = Path(td) / "does_not_exist.json"
            # (a) Fail-closed when missing (allow_fallback=False default)
            with self.assertRaises(FileNotFoundError):
                opt.load_pricing_catalog(missing)
            # Explicit opt-in fallback allowed for isolated tests
            fb = opt.load_pricing_catalog(missing, allow_fallback=True, now_utc=now)
            self.assertTrue(fb["is_fallback"])

            # (b) Corrupt JSON fails closed with ValueError
            corrupt = Path(td) / "corrupt.json"
            corrupt.write_text("{bad json", encoding="utf-8")
            with self.assertRaises(ValueError):
                opt.load_pricing_catalog(corrupt, allow_fallback=False)

            # (c) Valid fresh catalog loads cleanly
            sample = {
                "schema": "naqex-prop-pricing-catalog-v1",
                "updated_utc": fresh_ts,
                "staleness_max_days": 7,
                "fx_rates": {"usd_vnd": 25765.94, "eur_vnd": 28238.19, "fetched_utc": fresh_ts},
                "vn_transaction_costs": {"card_fx_buy_fee_pct": 2.5},
                "firms": {
                    "ftmo": {
                        "firm_id": "ftmo",
                        "display_name": "FTMO",
                        "verified_utc": fresh_ts,
                        "execution_evidence_tag": "MEASURED_DEMO_EXECUTION",
                        "programs": {
                            "ftmo_2step_standard": {
                                "program_id": "ftmo_2step_standard",
                                "display_name": "FTMO 2-Step Standard",
                                "verified_utc": fresh_ts,
                                "steps": 2,
                                "dd_daily_pct": 5.0,
                                "dd_max_pct": 10.0,
                                "daily_dd_anchor": "MIDNIGHT_BALANCE_PRAGUE_0000",
                                "tiers": {
                                    "10K": {"capital_usd": 10000, "available_vn": True, "orig_usd": 98.61, "active_promo_usd": 68.70, "verified_utc": fresh_ts},
                                    "100K": {"capital_usd": 100000, "available_vn": True, "orig_usd": 598.35, "active_promo_usd": 478.68, "verified_utc": fresh_ts},
                                },
                            }
                        },
                    }
                },
            }
            p_fresh = Path(td) / "fresh.json"
            p_fresh.write_text(json.dumps(sample), encoding="utf-8")
            loaded = opt.load_pricing_catalog(p_fresh, now_utc=now)
            self.assertFalse(loaded["is_fallback"])
            self.assertEqual(loaded["freshness_report"]["status"], "FRESH")
            self.assertEqual(loaded["freshness_report"]["per_tier_count"], 2)

            # (d) Stale PER-TIER verified_utc (even when top-level & program are fresh!) MUST raise ValueError
            sample_stale_tier = json.loads(json.dumps(sample))
            sample_stale_tier["firms"]["ftmo"]["programs"]["ftmo_2step_standard"]["tiers"]["100K"]["verified_utc"] = stale_ts
            p_stale_tier = Path(td) / "stale_tier.json"
            p_stale_tier.write_text(json.dumps(sample_stale_tier), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "STALE_CATALOG_ERROR"):
                opt.load_pricing_catalog(p_stale_tier, now_utc=now)

            # (e) Explicit historical audit override (`allow_stale=True`) flags status honestly
            loaded_ov = opt.load_pricing_catalog(p_stale_tier, allow_stale=True, now_utc=now)
            self.assertEqual(loaded_ov["freshness_report"]["status"], "STALE_OVERRIDDEN_HISTORICAL_AUDIT")
            self.assertTrue(loaded_ov["freshness_report"]["override_used"])
            self.assertEqual(loaded_ov["freshness_report"]["stale_tier_count"], 1)

            # (f) Invalid promo > orig raises ValueError
            sample_bad_price = json.loads(json.dumps(sample))
            sample_bad_price["firms"]["ftmo"]["programs"]["ftmo_2step_standard"]["tiers"]["10K"]["active_promo_usd"] = 120.0
            p_bad = Path(td) / "bad_price.json"
            p_bad.write_text(json.dumps(sample_bad_price), encoding="utf-8")
            with self.assertRaises(ValueError):
                opt.load_pricing_catalog(p_bad, now_utc=now)

            # (g) Missing per-tier verified_utc MUST fail closed (ZERO silent inheritance from program!)
            sample_missing_tv = json.loads(json.dumps(sample))
            del sample_missing_tv["firms"]["ftmo"]["programs"]["ftmo_2step_standard"]["tiers"]["100K"]["verified_utc"]
            p_miss_tv = Path(td) / "missing_tier_verified.json"
            p_miss_tv.write_text(json.dumps(sample_missing_tv), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "MISSING_TIER_VERIFIED_UTC"):
                opt.load_pricing_catalog(p_miss_tv, now_utc=now)

            # (h) Future timestamp (e.g. year 2099 > now_utc + 1 day) MUST fail closed even with allow_stale=True!
            sample_future = json.loads(json.dumps(sample))
            sample_future["firms"]["ftmo"]["programs"]["ftmo_2step_standard"]["tiers"]["10K"]["verified_utc"] = "2099-01-01T00:00:00Z"
            p_fut = Path(td) / "future_2099.json"
            p_fut.write_text(json.dumps(sample_future), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "FUTURE_TIMESTAMP_CATALOG_ERROR"):
                opt.load_pricing_catalog(p_fut, now_utc=now)
            with self.assertRaisesRegex(ValueError, "FUTURE_TIMESTAMP_CATALOG_ERROR"):
                opt.load_pricing_catalog(p_fut, allow_stale=True, now_utc=now)

            # (i) NaN / Inf / <=0 numeric prices MUST fail closed (math.isfinite guard!)
            for bad_field, bad_val in (
                ("orig_usd", float("nan")),
                ("active_promo_usd", float("nan")),
                ("orig_usd", float("inf")),
                ("active_promo_usd", float("-inf")),
                ("orig_usd", "NaN"),
                ("active_promo_usd", 0.0),
                ("orig_usd", -50.0),
            ):
                sample_nan = json.loads(json.dumps(sample))
                sample_nan["firms"]["ftmo"]["programs"]["ftmo_2step_standard"]["tiers"]["10K"][bad_field] = bad_val
                p_nan = Path(td) / "bad_nan.json"
                p_nan.write_text(json.dumps(sample_nan, allow_nan=True), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "NON_FINITE_PRICE_ERROR"):
                    opt.load_pricing_catalog(p_nan, now_utc=now)

    def test_11_purchase_day_ticket_pricing_no_perpetual_bf_on_retries(self) -> None:
        # Day 0 breaches immediately (-$600 > 5% daily limit on 10K);
        # Ticket #2 (retry on Day 1+) MUST pay regular price ($98.61 * 1.025 = $101.07525), NOT BF ($68.70 * 1.025 = $70.4175)!
        # Then Ticket #2 passes P1, P2, and gets Payout #1 -> refunds REGULAR price ($98.61), NOT BF ($68.70)!
        n_obs = 40
        nets = np.zeros(n_obs, dtype=np.float64)
        dds = np.zeros(n_obs, dtype=np.float64)
        ups = np.zeros(n_obs, dtype=np.float64)
        flg = np.ones(n_obs, dtype=np.int8)
        dds[0] = 600.0
        nets[0] = -600.0
        # Days 1..4: pass P1 (+$260/day = +$1,040 >= $1,000, 4 trading days)
        for d in range(1, 5):
            nets[d] = 260.0
        # Days 5..8: pass P2 (+$150/day = +$600 >= $500, 4 trading days)
        for d in range(5, 9):
            nets[d] = 150.0
        # Days 9..18 (10 trading days): Funded makes +$50/day = +$500 -> Payout #1 = $400 gross
        for d in range(9, 19):
            nets[d] = 50.0
        arrs = (nets, dds, ups, flg) * 7
        idx = np.arange(n_obs, dtype=np.int32).reshape(1, n_obs)

        res = opt._simulate_single_ticket_rules_numba(
            idx, *arrs,
            steps=2, cap=10_000.0, fee_day0_usd=68.70, fee_regular_usd=98.61,
            card_fx_fee_pct=0.025, withdrawal_fee_pct=0.015, fee_refund_pct=1.0,
            p1_target=0.10, p2_target=0.05, daily_lim=0.05, max_dd_lim=0.10,
            dd_type=opt.DD_STATIC, trail_lock_initial=False, best_day_cap_pct=0.0,
            min_days=4, min_prof_days=0, min_prof_day_pct=0.0,
            profit_split=0.80, payout_cycle_days=10, min_payout_usd=50.0,
            strict_lt_breach=True, p1_lock_trigger=0.70, p2_lock_trigger=0.70,
            amber_dd=0.035, red_dd=0.060, p1_ea_stop=0.035, p2_ea_stop=0.030, fn_ea_stop=0.025,
            start_day_offset=0, discount_rate_annual=0.0, max_retries=1,
            refund_withdrawal_fee_pct=0.0,
        )
        expected_fees = (68.70 + 98.61) * 1.025
        expected_payout = (500.0 * 0.80) * (1.0 - 0.015) + 98.61  # Regular fee refunded at 0.0% card refund fee!
        self.assertEqual(int(res[16][0]), 2)  # 2 tickets used
        self.assertAlmostEqual(float(res[13][0]), expected_fees, places=4)
        self.assertAlmostEqual(float(res[14][0]), expected_payout, places=4)

        # Also verify in `_simulate_capital_policy_numba`: Day 0 pays BF, retry on Day 1 pays Regular!
        haz = np.full((1, 1), -1, dtype=np.int32)
        tpl = [_base_tpl(10_000.0, 68.70, 98.61, arrs, wd_fee=0.015, ref_wd_fee=0.0)]
        packed = opt._pack_templates_for_numba(tpl)
        res_pol = opt._simulate_capital_policy_numba(
            idx, haz, *packed,
            policy_mode=1, ladder_tpls=np.array([0], dtype=np.int32), max_slots=1,
            allow_downgrade=False, upgrade_buf_mult=2.75, downgrade_buf_mult=2.0,
            init_bankroll_usd=500.0, monthly_topup_usd=0.0, card_fx_fee_pct=0.025,
            discount_rate_annual=0.0, own_book_overflow_mult=0.0, own_book_daily_ret=0.0,
            abort_after_day=-1, wait_for_top_rung_slot2=False,
        )
        self.assertAlmostEqual(float(res_pol[13][0]), expected_fees, places=4)
        self.assertAlmostEqual(float(res_pol[14][0]), expected_payout, places=4)

    def test_12_per_contract_daily_dd_anchor_initial_vs_prev_day_balance(self) -> None:
        # Day 0: drop -$400 -> bal = 9,600 (safe under both anchors).
        # Day 1: intraday drop $490 -> day_min = 9,110:
        #   - INITIAL_BALANCE (FTMO): daily_floor = 9,600 - 500 = 9,100 -> 9,110 > 9,100 -> SURVIVES!
        #   - PREV_DAY_BALANCE (The5ers/IC): daily_floor = 9,600 * 0.95 = 9,120 -> 9,110 < 9,120 -> BREACHES!
        n_obs = 10
        nets = np.zeros(n_obs, dtype=np.float64)
        dds = np.zeros(n_obs, dtype=np.float64)
        ups = np.zeros(n_obs, dtype=np.float64)
        flg = np.ones(n_obs, dtype=np.int8)
        nets[0] = -400.0
        dds[0] = 400.0
        nets[1] = -490.0
        dds[1] = 490.0
        arrs = (nets, dds, ups, flg) * 7
        idx = np.arange(n_obs, dtype=np.int32).reshape(1, n_obs)

        common = dict(
            steps=2, cap=10_000.0, fee_day0_usd=68.70, fee_regular_usd=98.61,
            card_fx_fee_pct=0.025, withdrawal_fee_pct=0.015, fee_refund_pct=1.0,
            p1_target=0.10, p2_target=0.05, daily_lim=0.05, max_dd_lim=0.10,
            dd_type=opt.DD_STATIC, trail_lock_initial=False, best_day_cap_pct=0.0,
            min_days=4, min_prof_days=0, min_prof_day_pct=0.0,
            profit_split=0.80, payout_cycle_days=10, min_payout_usd=50.0,
            strict_lt_breach=True, p1_lock_trigger=0.70, p2_lock_trigger=0.70,
            amber_dd=0.08, red_dd=0.09, p1_ea_stop=0.0, p2_ea_stop=0.0, fn_ea_stop=0.0,
            start_day_offset=0, discount_rate_annual=0.0, max_retries=0,
        )
        res_init = opt._simulate_single_ticket_rules_numba(
            idx, *arrs, daily_dd_anchor_mode=opt.DAILY_DD_ANCHOR_INITIAL_BALANCE, **common
        )
        res_prev = opt._simulate_single_ticket_rules_numba(
            idx, *arrs, daily_dd_anchor_mode=opt.DAILY_DD_ANCHOR_PREV_DAY_BALANCE, **common
        )
        self.assertEqual(int(res_init[7][0]), 0, "FTMO initial_balance anchor must survive $490 drop at $9,600 bal")
        self.assertEqual(int(res_prev[7][0]), 1, "The5ers/IC prev_day_balance anchor must breach $490 drop (>5% of $9,600=$480)")

        # Verify SAME divergence in `_simulate_capital_policy_numba`!
        haz = np.full((1, 1), -1, dtype=np.int32)
        t_init = _base_tpl(10_000.0, 68.70, 98.61, arrs, daily_dd_anchor="initial_balance")
        t_init["p1_ea_stop"] = 0.0
        t_init["amber_dd"] = 0.08
        t_init["red_dd"] = 0.09
        t_prev = dict(t_init)
        t_prev["daily_dd_anchor"] = "prev_day_balance"
        p_init = opt._pack_templates_for_numba([t_init])
        p_prev = opt._pack_templates_for_numba([t_prev])
        r_pol_init = opt._simulate_capital_policy_numba(
            idx, haz, *p_init,
            policy_mode=1, ladder_tpls=np.array([0], dtype=np.int32), max_slots=1,
            allow_downgrade=False, upgrade_buf_mult=2.75, downgrade_buf_mult=2.0,
            init_bankroll_usd=80.0, monthly_topup_usd=0.0, card_fx_fee_pct=0.025,
            discount_rate_annual=0.0, own_book_overflow_mult=0.0, own_book_daily_ret=0.0,
            abort_after_day=-1, wait_for_top_rung_slot2=False,
        )
        r_pol_prev = opt._simulate_capital_policy_numba(
            idx, haz, *p_prev,
            policy_mode=1, ladder_tpls=np.array([0], dtype=np.int32), max_slots=1,
            allow_downgrade=False, upgrade_buf_mult=2.75, downgrade_buf_mult=2.0,
            init_bankroll_usd=80.0, monthly_topup_usd=0.0, card_fx_fee_pct=0.025,
            discount_rate_annual=0.0, own_book_overflow_mult=0.0, own_book_daily_ret=0.0,
            abort_after_day=-1, wait_for_top_rung_slot2=False,
        )
        self.assertEqual(int(r_pol_init[7][0]), 0)
        self.assertEqual(int(r_pol_prev[7][0]), 1)

    def test_13_b2_p4a_wait_for_100k_holds_slot2_and_pareto_exposes_negative_medians(self) -> None:
        # Deterministic fast-pass tape for 50K & 100K:
        # Starting bankroll = $1,450: buys 50K Day 0 ($305.83*1.025=$313.48) -> cash = $1,136.52.
        # Regular 50K fee = $382.28*1.025 = $391.84 -> 2.75x = $1,077.55 (ALREADY MET when Slot 0 enters Funded!).
        # Regular 100K fee = $598.35*1.025 = $613.31 -> 2.75x = $1,686.60 (met right after 1st Funded payout!).
        # Greedy P4A (`wait_for_top_rung_slot2=False`) immediately fills Slot 2 with a 2nd 50K -> max_funded_nom = $100K.
        # P4A_WAIT_FOR_100K (`wait_for_top_rung_slot2=True`) holds Slot 2 for 100K -> max_funded_nom = $150K!
        n_obs = 60
        dds = np.zeros(n_obs, dtype=np.float64)
        ups = np.zeros(n_obs, dtype=np.float64)
        flg = np.ones(n_obs, dtype=np.int8)
        nets50 = np.full(n_obs, 1_300.0, dtype=np.float64)   # passes P1 in 4d, P2 in 4d, Funded makes $13K/10d!
        nets100 = np.full(n_obs, 2_600.0, dtype=np.float64)
        arr50 = (nets50, dds, ups, flg) * 7
        arr100 = (nets100, dds, ups, flg) * 7
        idx = np.arange(n_obs, dtype=np.int32).reshape(1, n_obs)
        haz = np.full((1, 1), -1, dtype=np.int32)

        tpls = [
            _base_tpl(50_000.0, 305.83, 382.28, arr50),
            _base_tpl(100_000.0, 478.68, 598.35, arr100),
        ]
        packed = opt._pack_templates_for_numba(tpls)
        r_greedy = opt._simulate_capital_policy_numba(
            idx, haz, *packed,
            policy_mode=1, ladder_tpls=np.array([0, 1], dtype=np.int32), max_slots=2,
            allow_downgrade=False, upgrade_buf_mult=2.75, downgrade_buf_mult=2.0,
            init_bankroll_usd=1_450.0, monthly_topup_usd=0.0, card_fx_fee_pct=0.025,
            discount_rate_annual=0.06, own_book_overflow_mult=0.0, own_book_daily_ret=0.0,
            abort_after_day=-1, wait_for_top_rung_slot2=False,
        )
        r_wait = opt._simulate_capital_policy_numba(
            idx, haz, *packed,
            policy_mode=1, ladder_tpls=np.array([0, 1], dtype=np.int32), max_slots=2,
            allow_downgrade=False, upgrade_buf_mult=2.75, downgrade_buf_mult=2.0,
            init_bankroll_usd=1_450.0, monthly_topup_usd=0.0, card_fx_fee_pct=0.025,
            discount_rate_annual=0.06, own_book_overflow_mult=0.0, own_book_daily_ret=0.0,
            abort_after_day=-1, wait_for_top_rung_slot2=True,
        )
        s_greedy = opt.summarize_capital_policy_mc(r_greedy, usd_vnd_rate=25_765.94, init_bankroll_vnd_tr=37.4, monthly_topup_vnd_tr=0.0)
        s_wait = opt.summarize_capital_policy_mc(r_wait, usd_vnd_rate=25_765.94, init_bankroll_vnd_tr=37.4, monthly_topup_vnd_tr=0.0)
        self.assertAlmostEqual(s_greedy["mean_max_funded_nom_usd"], 100_000.0, places=0)
        self.assertAlmostEqual(s_wait["mean_max_funded_nom_usd"], 150_000.0, places=0)
        self.assertGreater(s_wait["ev_npv_24m_usd"], s_greedy["ev_npv_24m_usd"])

        # Pareto selector MUST expose negative medians & P(NPV24 <= 0) on BOTH Profile A and Profile B!
        skewed_pols = {
            "P4B_SKEWED": {
                "ruin_pct": 1.2, "ev_npv_24m_usd": 3100.0, "ev_npv_36m_usd": 5400.0,
                "ev_npv_24m_vnd_tr": 80.0, "ev_npv_36m_vnd_tr": 140.0,
                "med_npv_24m_usd": -465.0, "med_npv_24m_vnd_tr": -12.0,
                "p_npv24_le_0_pct": 58.4,
                "uncond_med_pay1_cap730_days": 730.0, "cond_med_pay1_cal_days": 295.0,
                "funded_dry_months_pct": 69.0, "paid_any_pct": 46.6,
            },
        }
        w = opt.select_dual_objective_winners(skewed_pols)
        for prof_k in ("profile_a_npv_wealth_safe5pct", "profile_b_fast_cashflow_safe10pct"):
            self.assertAlmostEqual(w[prof_k]["med_npv_24m_vnd_tr"], -12.0, places=2)
            self.assertAlmostEqual(w[prof_k]["p_npv24_le_0_pct"], 58.4, places=2)

    def test_14_b5_dual_horizon_sale_calendar_exact_sweep_and_no_2xd7_shortcut(self) -> None:
        cat = opt.build_default_pricing_catalog()
        _, merged = opt.get_program_tier(cat, "FTMO_2STEP_STD", 10_000.0)
        # Horizon 756 allows shifting 24m window `[wait_td, wait_td + 504)` MC verification!
        idx = opt.make_block_bootstrap_indices(300, horizon=756, n_paths=400, seed=55)
        arrs = _make_synthetic_stage_arrays(300, cap=10_000.0, mean_pct=0.0011, vol_pct=0.0045, seed=55)

        sol = opt.solve_max_wait_days_worth_it(
            idx, arrs, program_tier=merged, orig_fee_usd=98.61,
            active_discount_pct=0.0, next_sale_discount_pct=0.20,
            card_fx_fee_pct=0.025, discount_rate_annual=0.06, usd_vnd_rate=25_765.94,
            horizon_months=24, max_search_days=120, max_retries=0,
        )
        self.assertEqual(sol["search_method"], "EXACT_FULL_SWEEP_NO_BINARY_SEARCH")
        self.assertIn("100% guaranteed", sol["assumption_disclosure"])
        # Verify shifting-horizon closed-form formula matches `365 * ln(NPV_sale / NPV_today) / ln(1 + r)`!
        expected_shift = 365.0 * math.log(sol["npv_sale_day0_usd"] / sol["npv_today_usd"]) / math.log(1.06)
        self.assertAlmostEqual(sol["shifting_horizon_formula_max_wait_days"], expected_shift, places=0)
        self.assertIsNotNone(sol["shifting_horizon_mc_verified_max_wait_days"])
        self.assertGreater(sol["shifting_horizon_formula_max_wait_days"], sol["max_wait_days_fixed_deadline"])

        # Black Friday active (-30% vs future -10%): MUST run actual 14d MC evaluation (NOT 2.0 * d7 shortcut!)
        sol_bf = opt.solve_max_wait_days_worth_it(
            idx, arrs, program_tier=merged, orig_fee_usd=98.61,
            active_discount_pct=0.30, next_sale_discount_pct=0.10,
            card_fx_fee_pct=0.025, discount_rate_annual=0.06, usd_vnd_rate=25_765.94,
            horizon_months=24, max_search_days=60, max_retries=0,
        )
        ev14 = opt.evaluate_wait_vs_buy_npv(
            idx[:, :504], arrs, program_tier=merged, orig_fee_usd=98.61,
            active_discount_pct=0.30, wait_cal_days=14, next_sale_discount_pct=0.10,
            card_fx_fee_pct=0.025, discount_rate_annual=0.06, usd_vnd_rate=25_765.94,
            max_retries=0,
        )
        self.assertEqual(sol_bf["max_wait_days_fixed_deadline"], 0)
        self.assertEqual(sol_bf["shifting_horizon_formula_max_wait_days"], 0.0)
        self.assertAlmostEqual(sol_bf["delta_npv_at_14d_usd"], ev14["delta_npv_24m_usd"], places=2)
        # Prove it is NOT a naive `2 * d7` multiple (upfront price loss is constant across 7d & 14d!)
        self.assertNotAlmostEqual(sol_bf["delta_npv_at_14d_usd"], sol_bf["delta_npv_at_7d_usd"] * 2.0, places=1)

    def test_15_b6_fee_accounting_separation_and_parallel_2x100k_day0_correlation(self) -> None:
        # (a) Fee accounting separation: buy FX +2.5% non-refundable, payout rail 1.5%, card refund 0.0% vs 1.5% rail!
        n_obs = 25
        nets = np.full(n_obs, 3_000.0, dtype=np.float64)  # 100K passes P1 (4d), P2 (4d), Funded 10d = +$30K
        dds = np.zeros(n_obs, dtype=np.float64)
        ups = np.zeros(n_obs, dtype=np.float64)
        flg = np.ones(n_obs, dtype=np.int8)
        arrs = (nets, dds, ups, flg) * 7
        idx = np.arange(n_obs, dtype=np.int32).reshape(1, n_obs)

        common = dict(
            steps=2, cap=100_000.0, fee_day0_usd=478.68, fee_regular_usd=598.35,
            card_fx_fee_pct=0.025, withdrawal_fee_pct=0.015, fee_refund_pct=1.0,
            p1_target=0.10, p2_target=0.05, daily_lim=0.05, max_dd_lim=0.10,
            dd_type=opt.DD_STATIC, trail_lock_initial=False, best_day_cap_pct=0.0,
            min_days=4, min_prof_days=0, min_prof_day_pct=0.0,
            profit_split=0.80, payout_cycle_days=10, min_payout_usd=50.0,
            strict_lt_breach=True, p1_lock_trigger=0.70, p2_lock_trigger=0.70,
            amber_dd=0.035, red_dd=0.060, p1_ea_stop=0.035, p2_ea_stop=0.030, fn_ea_stop=0.025,
            start_day_offset=0, discount_rate_annual=0.0, max_retries=0,
        )
        r_card = opt._simulate_single_ticket_rules_numba(idx, *arrs, refund_withdrawal_fee_pct=0.0, **common)
        r_rail = opt._simulate_single_ticket_rules_numba(idx, *arrs, refund_withdrawal_fee_pct=0.015, **common)
        # Exact difference = 1.5% of $478.68 = $7.1802!
        self.assertAlmostEqual(float(r_card[14][0]) - float(r_rail[14][0]), 478.68 * 0.015, places=4)
        # Verify buy FX (+2.5%) is strictly non-refundable (fees paid = 478.68*1.025, refund received = 478.68)
        self.assertAlmostEqual(float(r_card[13][0]), 478.68 * 1.025, places=4)

        # (b) P4B_PARALLEL_2X100K (`policy_mode=3`): opens BOTH 100K on Day 0 when bankroll >= 2 tickets
        #     AND exhibits 100% simultaneous same-day drawdown failure on a crash day!
        haz = np.full((1, 1), -1, dtype=np.int32)
        tpl = [_base_tpl(100_000.0, 478.68, 598.35, arrs)]
        packed = opt._pack_templates_for_numba(tpl)
        r_par = opt._simulate_capital_policy_numba(
            idx, haz, *packed,
            policy_mode=3, ladder_tpls=np.array([0], dtype=np.int32), max_slots=2,
            allow_downgrade=False, upgrade_buf_mult=2.0, downgrade_buf_mult=2.0,
            init_bankroll_usd=3_100.0, monthly_topup_usd=0.0, card_fx_fee_pct=0.025,
            discount_rate_annual=0.06, own_book_overflow_mult=0.0, own_book_daily_ret=0.0,
            abort_after_day=-1, wait_for_top_rung_slot2=False,
        )
        s_par = opt.summarize_capital_policy_mc(r_par, usd_vnd_rate=25_765.94, init_bankroll_vnd_tr=80.0, monthly_topup_vnd_tr=0.0)
        self.assertAlmostEqual(s_par["mean_max_funded_nom_usd"], 200_000.0, places=0)
        self.assertAlmostEqual(s_par["mean_fees_24m_usd"], 2.0 * 478.68 * 1.025, places=1)

        # Crash on Day 0 -> BOTH parallel 100K slots breach simultaneously on the exact same day!
        dds_crash = np.zeros(n_obs, dtype=np.float64)
        dds_crash[0] = 6_000.0  # > 5% daily limit on 100K
        nets_crash = np.zeros(n_obs, dtype=np.float64)
        nets_crash[0] = -6_000.0
        arr_crash = (nets_crash, dds_crash, ups, flg) * 7
        packed_crash = opt._pack_templates_for_numba([_base_tpl(100_000.0, 478.68, 598.35, arr_crash)])
        r_par_crash = opt._simulate_capital_policy_numba(
            idx, haz, *packed_crash,
            policy_mode=3, ladder_tpls=np.array([0], dtype=np.int32), max_slots=2,
            allow_downgrade=False, upgrade_buf_mult=2.0, downgrade_buf_mult=2.0,
            init_bankroll_usd=1_358.0, monthly_topup_usd=0.0, card_fx_fee_pct=0.025,
            discount_rate_annual=0.06, own_book_overflow_mult=0.0, own_book_daily_ret=0.0,
            abort_after_day=-1, wait_for_top_rung_slot2=False,
        )
        s_par_crash = opt.summarize_capital_policy_mc(r_par_crash, usd_vnd_rate=25_765.94, init_bankroll_vnd_tr=35.0, monthly_topup_vnd_tr=0.0)
        self.assertEqual(s_par_crash["simultaneous_fail_pct"], 100.0)
        self.assertEqual(s_par_crash["ruin_pct"], 100.0)

    def test_16_live_catalog_integration_anchors_and_fee_separation(self) -> None:
        if not opt.DEFAULT_CATALOG_PATH.is_file():
            self.skipTest("prop_pricing_catalog.json not present in isolated environment")
        raw = json.loads(opt.DEFAULT_CATALOG_PATH.read_text(encoding="utf-8"))
        ref_now = opt._parse_utc_iso(raw["updated_utc"]) + timedelta(hours=4)
        cat = opt.load_pricing_catalog(allow_fallback=False, enforce_freshness=True, now_utc=ref_now)
        self.assertFalse(cat["is_fallback"])
        self.assertEqual(cat["freshness_report"]["status"], "FRESH")
        firms = {p["firm_id"] for p in cat["programs"]}
        self.assertEqual(firms, {"FTMO", "THE5ERS", "IC_FUNDED", "E8_MARKETS"})

        # Verify per-contract daily_dd_anchor & separated refund_withdrawal_fee_pct
        _, ftmo10 = opt.get_program_tier(cat, "FTMO_2STEP_STANDARD", 10_000.0)
        self.assertEqual(ftmo10["daily_dd_anchor"], "initial_balance")
        self.assertEqual(ftmo10["dd_rule_verification_tag"], opt.DD_ANCHOR_TAG_BALANCE_VERIFIED)
        self.assertAlmostEqual(ftmo10["payout_rail_fee_pct"], 0.010, places=6)
        self.assertAlmostEqual(ftmo10["fx_conversion_spread_pct"], 0.005, places=6)
        self.assertAlmostEqual(ftmo10["payout_withdrawal_fee_pct"], 0.015, places=6)
        self.assertAlmostEqual(ftmo10["refund_withdrawal_fee_pct"], 0.000, places=6)

        _, t5_5k = opt.get_program_tier(cat, "THE5ERS_HIGH_STAKES_CLASSIC", 5_000.0)
        self.assertEqual(t5_5k["daily_dd_anchor"], "prev_day_balance")
        self.assertEqual(t5_5k["execution_evidence_tag"], "TERMS_VERIFIED_EXECUTION_UNMEASURED")
        self.assertEqual(t5_5k["dd_rule_verification_tag"], "DD_ANCHOR_UNVERIFIED_UNLESS_FLAT_AT_RESET")
        self.assertIn("flat", t5_5k["dd_rule_verification_note"].lower())
        self.assertAlmostEqual(t5_5k["min_profitable_day_pct"], 0.005, places=6)
        self.assertAlmostEqual(t5_5k["payout_withdrawal_fee_pct"], 0.040, places=6)
        self.assertAlmostEqual(t5_5k["refund_withdrawal_fee_pct"], 0.040, places=6)

        _, ic_10 = opt.get_program_tier(cat, "IC_FUNDED_2STEP_PRO", 10_000.0)
        self.assertEqual(ic_10["daily_dd_anchor"], "prev_day_balance")
        self.assertEqual(ic_10["execution_evidence_tag"], "TERMS_VERIFIED_EXECUTION_UNMEASURED")
        self.assertEqual(ic_10["dd_rule_verification_tag"], "DD_ANCHOR_UNVERIFIED_UNLESS_FLAT_AT_RESET")
        self.assertIn("flat", ic_10["dd_rule_verification_note"].lower())
        self.assertAlmostEqual(ic_10["payout_withdrawal_fee_pct"], 0.020, places=6)

        self.assertEqual(cat["freshness_report"]["per_tier_count"], 42)

        _, e8_50 = opt.get_program_tier(cat, "E8_PRO_1STEP_STATIC", 50_000.0)
        self.assertEqual(e8_50["daily_dd_anchor"], "initial_balance")
        self.assertAlmostEqual(e8_50["min_payout_profit_pct"], 0.010, places=6)
        self.assertAlmostEqual(e8_50["daily_profit_cap_pct"], 0.020, places=6)
        self.assertAlmostEqual(e8_50["payout_buffer_retention_pct"], 0.500, places=6)

    def test_17_q3c_dense_0_to_180_shifting_horizon_non_monotonic_dual_readout(self) -> None:
        # Construct a deterministic 1-path synthetic Funded tape (`horizon = 650` trading days -> >180 cal days shift!)
        # where shifting-horizon delta NPV is:
        #   - positive continuously for early days (fee savings outweigh small discount),
        #   - dips NEGATIVE in the middle when losing high-return days [10..29] replaced by 0-return [514..533],
        #   - rebounds POSITIVE later when window enters high-return tail [534..580],
        #   - then drops negative again when losing [30..150] replaced by 0-return [581..699]!
        n_obs = 700
        nets = np.full(n_obs, 10.0, dtype=np.float64)
        nets[10:30] = 120.0
        nets[30:140] = 60.0
        nets[514:534] = 0.0
        nets[534:585] = 160.0
        nets[585:] = 0.0
        dds = np.zeros(n_obs, dtype=np.float64)
        ups = np.zeros(n_obs, dtype=np.float64)
        flg = np.ones(n_obs, dtype=np.int8)
        arrs = (nets, dds, ups, flg) * 7
        idx = np.arange(650, dtype=np.int32).reshape(1, 650)

        tpl_prog = {
            "steps": 0,
            "capital_usd": 10_000.0,
            "p1_target_pct": 0.0,
            "p2_target_pct": 0.0,
            "dd_daily_pct": 0.05,
            "dd_max_pct": 0.10,
            "dd_type": "static",
            "daily_dd_anchor": "initial_balance",
            "best_day_cap_pct": 0.0,
            "min_trading_days": 0,
            "min_profitable_days": 0,
            "min_profitable_day_pct": 0.0,
            "profit_split_pct": 0.80,
            "payout_cycle_trading_days": 10,
            "min_payout_usd": 50.0,
            "fee_refund_pct": 0.0,
            "refund_payout_milestone": 0,
            "payout_withdrawal_fee_pct": 0.015,
            "withdrawal_fee_pct": 0.015,
            "refund_withdrawal_fee_pct": 0.0,
        }
        sol = opt.solve_max_wait_days_worth_it(
            idx, arrs,
            program_tier=tpl_prog,
            orig_fee_usd=100.0,
            active_discount_pct=0.0,
            next_sale_discount_pct=0.25,
            card_fx_fee_pct=0.025,
            discount_rate_annual=0.06,
            usd_vnd_rate=25_765.94,
            horizon_months=24,
            max_search_days=180,
            max_retries=0,
        )
        # MUST evaluate ALL 181 integer days 0..180 densely!
        self.assertEqual(sol["shifting_horizon_search_method"], "EXACT_DENSE_0_TO_MAX_SWEEP")
        self.assertEqual(sol["shifting_horizon_sweep_days_evaluated"], 181)
        # Dual readout MUST distinguish continuous positive wait vs later rebound!
        self.assertGreater(sol["max_continuous_positive_wait_days"], 0)
        self.assertGreater(sol["last_positive_wait_day"], sol["max_continuous_positive_wait_days"])
        self.assertEqual(sol["first_nonpositive_wait_day"], sol["max_continuous_positive_wait_days"] + 1)
        self.assertTrue(sol["non_monotonic_shifting_horizon"])
        self.assertIn("NEVER interpret", sol["shifting_horizon_non_monotonic_warning"])
        # Conservative MC threshold MUST equal continuous positive wait, NOT inflated last_positive_wait_day!
        self.assertEqual(sol["shifting_horizon_mc_verified_max_wait_days"], sol["max_continuous_positive_wait_days"])


if __name__ == "__main__":
    unittest.main()

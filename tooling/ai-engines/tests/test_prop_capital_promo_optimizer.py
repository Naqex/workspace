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
 12. B2 `P4A_WAIT_FOR_100K` (`wait_for_top_rung_slot2=True`) holds Slot 2 for `100K` + median/P(<=0).
 13. B5 Dual-Horizon Dynamic Sale Calculator (exact sweep `Y=0..max`, NO binary search, shifting MC).
 14. B6 Fee accounting separation (`+2.5%` buy FX, `0.0%` FTMO refund) + `P4B_PARALLEL_2X100K` Day-0 correlation.
 15. Live `prop_pricing_catalog.json` integration, daily DD anchor mapping, and zero bare `$` report guard.
 16. V3: `flat_at_reset_verified`, midnight rollover shock stress, BF 2-deadline option, & X13 shard worker.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest

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
        s100 = opt.summarize_capital_policy_mc(
            r100, usd_vnd_rate=25_765.94, init_bankroll_vnd_tr=38.0, monthly_topup_vnd_tr=0.0
        )
        s200 = opt.summarize_capital_policy_mc(
            r200, usd_vnd_rate=25_765.94, init_bankroll_vnd_tr=38.0, monthly_topup_vnd_tr=0.0
        )
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
        s_blind = opt.summarize_capital_policy_mc(
            r_blind, usd_vnd_rate=25_765.94, init_bankroll_vnd_tr=38.0, monthly_topup_vnd_tr=0.0
        )
        s_abort = opt.summarize_capital_policy_mc(
            r_abort, usd_vnd_rate=25_765.94, init_bankroll_vnd_tr=38.0, monthly_topup_vnd_tr=0.0
        )
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
            s5_path.write_text(
                json.dumps({"overall_ranking_stability_verdict": "C10_DOMINATES_ECONOMIC_ZERO_FLIP"}),
                encoding="utf-8",
            )
            s5 = opt.load_step5_c00_c10_summary(s5_path)
            self.assertEqual(s5["primary_variant"], "C10_NEWS_ON")
            self.assertEqual(s5["control_variant"], "C00")

    def test_10_fail_closed_catalog_load_and_per_tier_staleness_enforcement(self) -> None:
        now = datetime(2026, 11, 26, 16, 0, 0, tzinfo=UTC)
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
                                    "10K": {
                                        "capital_usd": 10000,
                                        "available_vn": True,
                                        "orig_usd": 98.61,
                                        "active_promo_usd": 68.70,
                                        "verified_utc": fresh_ts,
                                    },
                                    "100K": {
                                        "capital_usd": 100000,
                                        "available_vn": True,
                                        "orig_usd": 598.35,
                                        "active_promo_usd": 478.68,
                                        "verified_utc": fresh_ts,
                                    },
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
            ftmo_tiers_st = sample_stale_tier["firms"]["ftmo"]["programs"]["ftmo_2step_standard"]["tiers"]
            ftmo_tiers_st["100K"]["verified_utc"] = stale_ts
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
            ftmo_tiers_bp = sample_bad_price["firms"]["ftmo"]["programs"]["ftmo_2step_standard"]["tiers"]
            ftmo_tiers_bp["10K"]["active_promo_usd"] = 120.0
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
            ftmo_tiers_fu = sample_future["firms"]["ftmo"]["programs"]["ftmo_2step_standard"]["tiers"]
            ftmo_tiers_fu["10K"]["verified_utc"] = "2099-01-01T00:00:00Z"
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
        # Ticket #2 (Day 1+) MUST pay regular price ($98.61*1.025=$101.07525), NOT BF ($68.70*1.025)!
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
        self.assertEqual(
            int(res_init[7][0]), 0, "FTMO initial_balance anchor must survive $490 drop at $9,600 bal"
        )
        self.assertEqual(
            int(res_prev[7][0]),
            1,
            "The5ers/IC prev_day_balance anchor must breach $490 drop (>5% of $9,600=$480)",
        )

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
        # Greedy P4A (`wait_for_top_rung_slot2=False`) fills Slot 2 with a 2nd 50K -> max_funded_nom = $100K.
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
        s_greedy = opt.summarize_capital_policy_mc(
            r_greedy, usd_vnd_rate=25_765.94, init_bankroll_vnd_tr=37.4, monthly_topup_vnd_tr=0.0
        )
        s_wait = opt.summarize_capital_policy_mc(
            r_wait, usd_vnd_rate=25_765.94, init_bankroll_vnd_tr=37.4, monthly_topup_vnd_tr=0.0
        )
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
        s_par = opt.summarize_capital_policy_mc(
            r_par, usd_vnd_rate=25_765.94, init_bankroll_vnd_tr=80.0, monthly_topup_vnd_tr=0.0
        )
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
        s_par_crash = opt.summarize_capital_policy_mc(
            r_par_crash, usd_vnd_rate=25_765.94, init_bankroll_vnd_tr=35.0, monthly_topup_vnd_tr=0.0
        )
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

    # -----------------------------------------------------------------------
    # Capital Optimizer V3 Tests (Rollover Stress, BF 2-Deadline Option, X13 Shard)
    # -----------------------------------------------------------------------

    @staticmethod
    def _make_synthetic_tapes(
        n_days: int = 80,
        *,
        exit_utc_hour: int = 20,
        exit_utc_min: int = 55,
        seed: int = 123,
    ) -> tuple[list[str], dict[str, dict[str, tuple[dict, np.ndarray, np.ndarray]]]]:
        """Build synthetic pure pre-2025 M1 tapes matching `frozen_9e_tapes_v2` schema."""
        rng = np.random.default_rng(seed)
        base_dt = datetime(2024, 6, 3, 0, 0, tzinfo=UTC)  # EU summer DST active (CEST=+2, EEST=+3)
        ext_days: list[str] = []
        d_cur = base_dt
        while len(ext_days) < n_days:
            if d_cur.weekday() < 5:
                ext_days.append(d_cur.strftime("%Y-%m-%d"))
            d_cur += timedelta(days=1)

        tapes: dict[str, dict[str, tuple[dict, np.ndarray, np.ndarray]]] = {}
        assets = {
            "E1_USDJPY_TOKYO": ("USDJPY", 150.0, 7, 0, 15, 0),
            "E2_USDJPY_EXP80": ("USDJPY", 150.0, 9, 0, exit_utc_hour, exit_utc_min),
            "E3_GBPUSD_VH": ("GBPUSD", 1.27, 9, 0, exit_utc_hour, exit_utc_min),
            "E4_US100_SESS40": ("US100", 19000.0, 15, 30, 19, 55),
            "E5_US100_RS1130": ("US100", 19000.0, 15, 30, 19, 55),
            "E6_EURJPY_VOLCOMP": ("EURJPY", 162.0, 8, 0, exit_utc_hour, exit_utc_min),
            "E7_USDJPY_NY10ET": ("USDJPY", 150.0, 14, 0, exit_utc_hour, exit_utc_min),
        }
        for eng, (asset, ep, eh, em, xh, xm) in assets.items():
            eng_map: dict[str, tuple[dict, np.ndarray, np.ndarray]] = {}
            for dk in ext_days:
                yr, mo, dy = (int(x) for x in dk.split("-"))
                t_ent = int(datetime(yr, mo, dy, eh, em, tzinfo=UTC).timestamp())
                t_ext = int(datetime(yr, mo, dy, xh, xm, tzinfo=UTC).timestamp())
                if t_ext <= t_ent:
                    t_ext = t_ent + 3600
                stamps = np.arange(t_ent, t_ext + 1, 60, dtype=np.int64)
                if len(stamps) > 8:
                    stamps = np.array([t_ent, t_ent + 60, t_ent + 120, t_ext - 60, t_ext], dtype=np.int64)
                stop_cost = 600.0
                net_1lot = float(rng.normal(95.0, 320.0))
                dip = -abs(float(rng.normal(200.0, 110.0)))
                hi = abs(float(rng.normal(200.0, 110.0)))
                marks = np.zeros((len(stamps), 4), dtype=np.float64)
                marks[:, 0] = 0.0
                marks[:, 1] = hi
                marks[:, 2] = dip
                marks[:, 3] = np.linspace(0.0, net_1lot, len(stamps))
                row = {
                    "day": dk,
                    "asset": asset,
                    "entry": t_ent,
                    "exit": t_ext,
                    "at_open": False,
                    "entry_price": ep,
                    "stop_risk_with_cost_usd": stop_cost,
                    "initial_risk_usd": stop_cost * 0.96,
                    "net_usd_per_lot": net_1lot,
                }
                eng_map[dk] = (row, stamps, marks)
            tapes[eng] = eng_map
        return ext_days, tapes

    @staticmethod
    def _write_synthetic_frozen_v2(
        tapes_dir: Path,
        ext_days: list[str],
        tapes: dict[str, dict[str, tuple[dict, np.ndarray, np.ndarray]]],
        stem: str = "frozen_9e_tapes_v2",
    ) -> tuple[Path, Path, str]:
        arrays: dict[str, np.ndarray] = {}
        tape_index: dict[str, dict] = {}
        for eng, day_map in tapes.items():
            sdays = sorted(day_map.keys())
            st_list = []
            mk_list = []
            offs = [0]
            rows = {}
            for dk in sdays:
                r, st, mk = day_map[dk]
                rows[dk] = r
                st_list.append(st)
                mk_list.append(mk)
                offs.append(offs[-1] + len(st))
            tape_index[eng] = {"days": sdays, "rows": rows}
            arrays[f"{eng}__stamps"] = np.concatenate(st_list)
            arrays[f"{eng}__marks"] = np.concatenate(mk_list, axis=0)
            arrays[f"{eng}__offsets"] = np.asarray(offs, dtype=np.int64)
        npz_path = tapes_dir / f"{stem}.npz"
        meta_path = tapes_dir / f"{stem}.json"
        np.savez(npz_path, **arrays)
        npz_sha = hashlib.sha256(npz_path.read_bytes()).hexdigest()
        meta = {
            "schema": "naqex-frozen-tapes-v2",
            "binding_sha256": "a" * 64,
            "npz_sha256": npz_sha,
            "ext_days": ext_days,
            "strict_cluster_a_days": [],
            "tapes": tape_index,
        }
        meta_path.write_text(json.dumps(meta), encoding="utf-8")
        return meta_path, npz_path, npz_sha

    def test_18_v3_flat_at_reset_verified_and_negative_mutations(self) -> None:
        _, tapes = self._make_synthetic_tapes(n_days=20, exit_utc_hour=20, exit_utc_min=55)
        audit = opt.verify_tapes_flat_at_reset(tapes)
        self.assertTrue(audit["flat_at_reset_verified"])
        self.assertTrue(audit["flat_at_reset_verified_by_firm"]["FTMO"])
        self.assertTrue(audit["flat_at_reset_verified_by_firm"]["THE5ERS"])
        self.assertTrue(audit["flat_at_reset_verified_by_firm"]["IC_FUNDED"])
        self.assertEqual(audit["holdout_rows_analysed"], 0)
        # Summer EEST (UTC+3): 20:55 UTC == 23:55 EEST -> exact 5.0 min buffer triggers tight-buffer warning!
        self.assertAlmostEqual(audit["min_buffer_minutes_by_clock"]["MT5_EET_0000"], 5.0, places=1)
        self.assertTrue(any("MT5_EET_0000" in w for w in audit["tight_buffer_warnings"]))

        # Negative Mutation 1 (Vector V7): winter trade crossing 00:00 EET (22:05 UTC) while < 00:00 Prague!
        tapes_cross = {k: dict(v) for k, v in tapes.items()}
        dk_mut = "2024-12-02"
        t_ent = int(datetime(2024, 12, 2, 21, 30, tzinfo=UTC).timestamp())
        t_ext = int(datetime(2024, 12, 2, 22, 5, tzinfo=UTC).timestamp())
        tapes_cross["E2_USDJPY_EXP80"][dk_mut] = (
            {"entry": t_ent, "exit": t_ext, "asset": "USDJPY"},
            np.array([t_ent, t_ext], dtype=np.int64),
            np.zeros((2, 4), dtype=np.float64),
        )
        audit_cross = opt.verify_tapes_flat_at_reset(tapes_cross)
        self.assertFalse(audit_cross["flat_at_reset_verified"])
        self.assertTrue(audit_cross["flat_at_reset_verified_by_firm"]["FTMO"])
        self.assertFalse(audit_cross["flat_at_reset_verified_by_firm"]["THE5ERS"])
        self.assertFalse(audit_cross["flat_at_reset_verified_by_firm"]["IC_FUNDED"])
        self.assertEqual(audit_cross["crossing_trades_by_clock"]["MT5_EET_0000"], 1)

        # Negative Mutation 2 (Vector V2): missing exit timestamp (`None`) MUST fail closed (never coerce to flat!)
        tapes_none = {k: dict(v) for k, v in tapes.items()}
        first_dk = next(iter(tapes_none["E1_USDJPY_TOKYO"]))
        r0, st0, mk0 = tapes_none["E1_USDJPY_TOKYO"][first_dk]
        tapes_none["E1_USDJPY_TOKYO"][first_dk] = ({**r0, "exit": None}, st0, mk0)
        audit_none = opt.verify_tapes_flat_at_reset(tapes_none)
        self.assertFalse(audit_none["flat_at_reset_verified"])
        self.assertEqual(audit_none["invalid_trades"], 1)

        # Negative Mutation 3 (Vector V1): holdout date >= 2025-01-01 MUST raise HOLDOUT_LOCK_VIOLATION!
        tapes_ho = {k: dict(v) for k, v in tapes.items()}
        t_2025 = int(datetime(2025, 1, 2, 10, 0, tzinfo=UTC).timestamp())
        tapes_ho["E1_USDJPY_TOKYO"]["2025-01-02"] = (
            {"entry": t_2025, "exit": t_2025 + 600},
            np.array([t_2025, t_2025 + 600], dtype=np.int64),
            np.zeros((2, 4), dtype=np.float64),
        )
        with self.assertRaisesRegex(ValueError, "HOLDOUT_LOCK_VIOLATION"):
            opt.verify_tapes_flat_at_reset(tapes_ho)

    def test_19_v3_rollover_floating_equity_shock_balance_vs_max_bal_eq_vs_equity(self) -> None:
        # (a) Exact backward compatibility: default shock=0.0, rollover_anchor_mode=-1 matches legacy call bit-for-bit!
        idx = opt.make_block_bootstrap_indices(120, horizon=252, n_paths=100, seed=19)
        arrs = _make_synthetic_stage_arrays(120, cap=10_000.0, mean_pct=0.0009, vol_pct=0.0055, seed=19)
        base_kw = dict(
            steps=2, cap=10_000.0, fee_day0_usd=68.70, fee_regular_usd=98.61,
            card_fx_fee_pct=0.025, withdrawal_fee_pct=0.015, fee_refund_pct=1.0,
            p1_target=0.10, p2_target=0.05, daily_lim=0.05, max_dd_lim=0.10,
            dd_type=opt.DD_STATIC, trail_lock_initial=False, best_day_cap_pct=0.0,
            min_days=4, min_prof_days=0, min_prof_day_pct=0.0,
            profit_split=0.80, payout_cycle_days=10, min_payout_usd=50.0,
            strict_lt_breach=True, p1_lock_trigger=0.70, p2_lock_trigger=0.70,
            amber_dd=0.035, red_dd=0.060, p1_ea_stop=0.035, p2_ea_stop=0.030, fn_ea_stop=0.025,
            start_day_offset=0, discount_rate_annual=0.06, max_retries=0,
            daily_dd_anchor_mode=opt.DAILY_DD_ANCHOR_INITIAL_BALANCE,
        )
        r_old = opt._simulate_single_ticket_rules_numba(idx, *arrs, **base_kw)
        r_new = opt._simulate_single_ticket_rules_numba(
            idx, *arrs, midnight_floating_shock_pct=0.0, rollover_anchor_mode=-1, **base_kw
        )
        np.testing.assert_array_equal(r_old[9], r_new[9])
        np.testing.assert_array_equal(r_old[7], r_new[7])

        # (b) Exact 3-way divergence under ADVERSE -1.0% floating equity shock at midnight when bal = $9,500:
        # Day 0 drops -$500 (bal=9,500); Day 1 has intraday dd=$380 + adverse shock -$100 -> day_min_eq = $9,020.
        #   - FTMO (mode 0, balance): floor = 9,500 - 500 = 9,000 -> SURVIVES!
        #   - The5ers (mode 1, max(bal, eq)): floor = max(9500, 9400)*0.95 = 9,025 -> BREACHES!
        #   - IC Funded (mode 2, equity): floor = 9,400*0.95 = 8,930 (max_floor=9,000) -> SURVIVES!
        n_obs = 5
        nets = np.array([-500.0, -380.0, 0.0, 0.0, 0.0], dtype=np.float64)
        dds = np.array([500.0, 380.0, 0.0, 0.0, 0.0], dtype=np.float64)
        ups = np.zeros(n_obs, dtype=np.float64)
        flg = np.array([0, 1, 1, 1, 1], dtype=np.int8)  # Day 0 sets bal=9500; shock active on Day 1 (flg=1)
        arr_adv = (nets, dds, ups, flg) * 7
        idx1 = np.arange(n_obs, dtype=np.int32).reshape(1, n_obs)
        det_kw = {**base_kw, "p1_ea_stop": 0.0, "p2_ea_stop": 0.0, "fn_ea_stop": 0.0, "amber_dd": 0.09, "red_dd": 0.095}
        r_ftmo = opt._simulate_single_ticket_rules_numba(
            idx1,
            *arr_adv,
            midnight_floating_shock_pct=-0.010,
            rollover_anchor_mode=opt.ROLLOVER_ANCHOR_BALANCE,
            **det_kw,
        )
        r_t5 = opt._simulate_single_ticket_rules_numba(
            idx1,
            *arr_adv,
            midnight_floating_shock_pct=-0.010,
            rollover_anchor_mode=opt.ROLLOVER_ANCHOR_MAX_BAL_EQ,
            **det_kw,
        )
        r_ic = opt._simulate_single_ticket_rules_numba(
            idx1,
            *arr_adv,
            midnight_floating_shock_pct=-0.010,
            rollover_anchor_mode=opt.ROLLOVER_ANCHOR_EQUITY,
            **det_kw,
        )
        self.assertEqual(int(r_ftmo[7][0]), 0)
        self.assertEqual(int(r_t5[7][0]), 1)
        self.assertEqual(int(r_ic[7][0]), 0)

        # (c) Divergence under FAVORABLE +1.0% floating profit ratchet at midnight (bal=10k, dd=480 -> min=9,520):
        #   - FTMO (mode 0): floor = 9,500 -> SURVIVES!
        #   - The5ers (mode 1) & IC Funded (mode 2): floor = 10,100 * 0.95 = 9,595 -> BOTH BREACH!
        nets_p = np.array([-480.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float64)
        dds_p = np.array([480.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float64)
        flg_p = np.ones(n_obs, dtype=np.int8)
        arr_pos = (nets_p, dds_p, ups, flg_p) * 7
        rp_ftmo = opt._simulate_single_ticket_rules_numba(
            idx1,
            *arr_pos,
            midnight_floating_shock_pct=0.010,
            rollover_anchor_mode=opt.ROLLOVER_ANCHOR_BALANCE,
            **det_kw,
        )
        rp_t5 = opt._simulate_single_ticket_rules_numba(
            idx1,
            *arr_pos,
            midnight_floating_shock_pct=0.010,
            rollover_anchor_mode=opt.ROLLOVER_ANCHOR_MAX_BAL_EQ,
            **det_kw,
        )
        rp_ic = opt._simulate_single_ticket_rules_numba(
            idx1,
            *arr_pos,
            midnight_floating_shock_pct=0.010,
            rollover_anchor_mode=opt.ROLLOVER_ANCHOR_EQUITY,
            **det_kw,
        )
        self.assertEqual(int(rp_ftmo[7][0]), 0)
        self.assertEqual(int(rp_t5[7][0]), 1)
        self.assertEqual(int(rp_ic[7][0]), 1)

        # (d) Full rollover sensitivity runner across FTMO 10K, The5ers 5K/20K, and IC Funded 10K on synthetic tapes!
        ext_days, syn_tapes = self._make_synthetic_tapes(n_days=60, seed=19)
        cat = opt.build_default_pricing_catalog()
        cache = opt.ExactTierReplayCache(ext_days, syn_tapes, opt.DEFAULT_CORE7_BASE_RISK, {})
        flat_aud = opt.verify_tapes_flat_at_reset(syn_tapes)
        idx_s = opt.make_block_bootstrap_indices(len(ext_days), horizon=504, n_paths=120, seed=19)
        roll = opt.run_rollover_reset_sensitivity(
            catalog=cat,
            cache=cache,
            idx_matrix=idx_s,
            horizon_days=504,
            primary_var=opt.PRIMARY_VARIANT_DEFAULT,
            use_promo_prices=True,
            usd_vnd=25_765.94,
            card_fx_fee=0.025,
            flat_at_reset_audit=flat_aud,
        )
        self.assertTrue(roll["flat_at_reset_verified"])
        labels_seen = {r["label"] for r in roll["rows"]}
        self.assertIn("FTMO 2-Step Standard 10K", labels_seen)
        self.assertIn("The5ers High Stakes 5K", labels_seen)
        self.assertIn("The5ers High Stakes 20K", labels_seen)
        self.assertTrue(any("IC Funded" in lbl for lbl in labels_seen))
        for r in roll["rows"]:
            self.assertAlmostEqual(
                r["pass_24m_pct"] + r["fail_eval_24m_pct"] + r["pending_eval_24m_pct"], 100.0, places=1
            )
            if abs(r["midnight_floating_shock_pct"]) > 1e-9:
                self.assertFalse(r["flat_at_reset_verified"])

    def test_20_v3_black_friday_2deadline_option_vs_xmas_and_weak_dominance(self) -> None:
        ext_days, syn_tapes = self._make_synthetic_tapes(n_days=80, seed=20)
        cat = opt.build_default_pricing_catalog()
        ftmo_std = opt._find_program_by_hint(
            cat, lambda p: p["firm_id"] == "FTMO" and p["steps"] == 2 and p["profile_mode"] == "Standard"
        )
        self.assertIsNotNone(ftmo_std)
        assert ftmo_std is not None
        cache = opt.ExactTierReplayCache(ext_days, syn_tapes, opt.DEFAULT_CORE7_BASE_RISK, {})
        idx = opt.make_block_bootstrap_indices(len(ext_days), horizon=560, n_paths=150, seed=20)
        bf = opt.evaluate_black_friday_2deadline_option(
            catalog=cat,
            ftmo_std=ftmo_std,
            cache=cache,
            idx_matrix=idx,
            primary_var=opt.PRIMARY_VARIANT_DEFAULT,
            usd_vnd=25_765.94,
            card_fx_fee=0.025,
            tiers_usd=(10_000.0, 50_000.0, 100_000.0),
        )
        self.assertEqual(bf["assumption_tag"], "MODEL_ASSUMPTION")
        self.assertIn("MODEL_ASSUMPTION", bf["assumption_disclosure"])
        self.assertEqual(len(bf["milestones"]), 7)
        self.assertTrue(bf["weak_dominance_verified"])
        self.assertEqual(len(bf["tiers"]), 3)
        for t in bf["tiers"]:
            for h_key in ("fixed_deadline_24m", "shifting_horizon_24m"):
                h = t["horizons"][h_key]
                ref = h["reference_pgo70_pxmas50"]
                # Locking unpaid BF bill strictly dominates paying regular price on 14/12 AND waiting for Xmas/NY!
                self.assertGreater(ref["lock_value_b_minus_c_usd"], 0.0)
                self.assertGreater(ref["advantage_b_minus_d_xmas_usd"], 0.0)
                # Under p_go = 0.50 (below breakeven), 14-day option strictly dominates buying blind on 30/11!
                r50 = next(r for r in h["sensitivity_grid"] if abs(r["p_go"] - 0.50) < 1e-6)
                if 0.50 < h["breakeven_p_go_for_blind_buy"]:
                    self.assertGreater(r50["option_value_b_minus_a_usd"], 0.0)

    def test_21_v3_x13_shard_direct_loader_airgap_guards_and_merger(self) -> None:
        ext_days, syn_tapes = self._make_synthetic_tapes(n_days=40, seed=21)
        with tempfile.TemporaryDirectory() as td:
            tdir = Path(td) / "tapes"
            tdir.mkdir()
            meta_p, npz_p, exp_sha = self._write_synthetic_frozen_v2(tdir, ext_days, syn_tapes)

            # (a) Direct load succeeds and verifies exact npz_sha256 & max_day < 2025-01-01
            loaded = opt.load_frozen_tapes_v2_direct(tapes_dir=tdir)
            self.assertEqual(loaded["npz_sha256"], exp_sha)
            self.assertEqual(loaded["holdout_rows_analysed"], 0)
            self.assertTrue(loaded["max_day_strictly_lt_cutoff"])

            # (b) Negative Mutation: forbidden X13 job_id tokens MUST fail closed!
            for bad_jid in ("cap_2025_run", "cap_2026_shard", "my_holdout_job", "private_vault_0"):
                with self.assertRaisesRegex(ValueError, "X13_AIRGAP_JOB_ID_VIOLATION"):
                    opt.validate_x13_job_id(bad_jid)

            # (c) Run 2 shards and merge deterministically
            out_dir = Path(td) / "results"
            s0 = opt.run_x13_mc_shard(
                job_id="cap_v3_mc_unit",
                shard_id=0,
                num_shards=2,
                n_paths=60,
                horizon_months=24,
                tapes_dir=tdir,
                out_dir=out_dir,
            )
            s1 = opt.run_x13_mc_shard(
                job_id="cap_v3_mc_unit",
                shard_id=1,
                num_shards=2,
                n_paths=60,
                horizon_months=24,
                tapes_dir=tdir,
                out_dir=out_dir,
            )
            self.assertEqual(s0["holdout_rows_analysed"], 0)
            self.assertEqual(s0["order_send_count"], 0)
            self.assertTrue(Path(s0["saved_path"]).is_file())
            self.assertNotIn("2025", Path(s0["saved_path"]).name)
            self.assertNotIn("2026", Path(s0["saved_path"]).name)
            self.assertNotIn("holdout", Path(s0["saved_path"]).name.lower())

            merged = opt.merge_x13_mc_shards([s0, s1])
            self.assertEqual(merged["shards_merged"], 2)
            self.assertEqual(merged["total_paths"], 120)
            self.assertEqual(merged["holdout_rows_analysed"], 0)
            self.assertTrue(merged["flat_at_reset_verified"])

            # Negative Mutation on merger: duplicate shard_id MUST fail closed!
            with self.assertRaisesRegex(ValueError, "DUPLICATE_SHARD_ID"):
                opt.merge_x13_mc_shards([s0, s0])

            # (d) Subprocess CLI `--x13-shard` isolation proof: ZERO data_store / prop_engine / duckdb / holdout_guard!
            cli_out = Path(td) / "cli_out"
            probe_code = (
                "import json, sys; "
                f"sys.path.insert(0, {str(AI_ENGINES)!r}); "
                "from quant_factory.prop_capital_promo_optimizer import main; "
                f"rc = main(['--x13-shard', '--job-id', 'cap_v3_cli_probe', '--shard-id', '0', "
                f"'--num-shards', '1', '--shard-paths', '40', '--horizon-months', '24', "
                f"'--tapes-dir', {str(tdir)!r}, '--shard-out-dir', {str(cli_out)!r}]); "
                "forbidden = [m for m in ('quant_factory.data_store', 'quant_factory.prop_engine', "
                "'quant_core.holdout_guard', 'duckdb') if m in sys.modules]; "
                "print('FORBIDDEN_IMPORTED=' + json.dumps(forbidden)); "
                "raise SystemExit(rc)"
            )
            proc = subprocess.run(
                [sys.executable, "-c", probe_code],
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, msg=f"stderr={proc.stderr}\nstdout={proc.stdout}")
            self.assertIn("FORBIDDEN_IMPORTED=[]", proc.stdout)

            # (e) Negative Mutation: tamper 1 byte of .npz -> MUST raise NPZ_SHA256_MISMATCH!
            orig_npz_bytes = npz_p.read_bytes()
            raw_bytes = bytearray(orig_npz_bytes)
            raw_bytes[-1] ^= 0xFF
            npz_p.write_bytes(bytes(raw_bytes))
            try:
                with self.assertRaisesRegex(ValueError, "NPZ_SHA256_MISMATCH"):
                    opt.load_frozen_tapes_v2_direct(tapes_dir=tdir)
            finally:
                npz_p.write_bytes(orig_npz_bytes)

            # (f) Negative Mutation: inject 2025-01-02 into ext_days -> MUST raise HOLDOUT_LOCK_VIOLATION!
            tdir2 = Path(td) / "tapes_bad"
            tdir2.mkdir()
            meta_p2, _, _ = self._write_synthetic_frozen_v2(tdir2, ext_days + ["2025-01-02"], syn_tapes)
            self.assertTrue(meta_p2.is_file())
            with self.assertRaisesRegex(ValueError, "HOLDOUT_LOCK_VIOLATION"):
                opt.load_frozen_tapes_v2_direct(tapes_dir=tdir2)

            # (g) Defect #1/#3/#4 regressions:
            # - row["exit"] >= 2025-01-01Z even when stamps < 2025 MUST fail closed in load_frozen_tapes_v2_direct!
            tdir3 = Path(td) / "tapes_bad_exit"
            tdir3.mkdir()
            bad_tapes = copy.deepcopy(syn_tapes)
            first_dk = ext_days[0]
            r0, st0, mk0 = bad_tapes["E1_USDJPY_TOKYO"][first_dk]
            bad_tapes["E1_USDJPY_TOKYO"][first_dk] = ({**r0, "exit": 1_735_689_600}, st0, mk0)
            self._write_synthetic_frozen_v2(tdir3, ext_days, bad_tapes)
            with self.assertRaisesRegex(ValueError, "HOLDOUT_LOCK_VIOLATION"):
                opt.load_frozen_tapes_v2_direct(tapes_dir=tdir3)

            # - Unsorted stamps [1735689600, t_e+60] MUST fail closed in verify_tapes_flat_at_reset!
            bad_unsorted = copy.deepcopy(syn_tapes)
            r0, st0, mk0 = bad_unsorted["E1_USDJPY_TOKYO"][first_dk]
            bad_unsorted["E1_USDJPY_TOKYO"][first_dk] = (
                r0,
                np.array([1_735_689_600, int(r0["entry"]) + 60], dtype=np.int64),
                np.array([0.0, 0.0], dtype=np.float64),
            )
            with self.assertRaisesRegex(ValueError, "HOLDOUT_LOCK_VIOLATION"):
                opt.verify_tapes_flat_at_reset(bad_unsorted)

            # - Merger enforces calendar SHA, primary_variant, horizon_months, valid n_paths, finite metrics,
            #   and omits unmerged shard-0 med_npv_24m_vnd_tr!
            #   Verify fresh-process runtime isolation flags on the subprocess CLI shard output (avoids
            #   cross-test sys.modules pollution under shared pytest-xdist workers).
            cli_shard = json.loads((cli_out / "cap_v3_cli_probe_shard0.json").read_text(encoding="utf-8"))
            self.assertFalse(cli_shard["runtime"]["holdout_guard_imported"])
            self.assertFalse(cli_shard["runtime"]["data_store_imported"])
            self.assertFalse(cli_shard["runtime"]["prop_engine_imported"])
            self.assertFalse(cli_shard["runtime"]["duckdb_imported"])
            self.assertEqual(merged["median_merge_policy"], "OMITTED_CANNOT_AVERAGE_MEDIANS")
            self.assertTrue(all("med_npv_24m_vnd_tr" not in r for r in merged["rollover_rows"]))

            s1_bad_cal = copy.deepcopy(s1)
            s1_bad_cal["red_news_calendar"]["sha256"] = "0" * 64
            with self.assertRaisesRegex(ValueError, "SHARD_CALENDAR_SHA_MISMATCH"):
                opt.merge_x13_mc_shards([s0, s1_bad_cal])

            s1_bad_var = copy.deepcopy(s1)
            s1_bad_var["primary_variant"] = "C00"
            with self.assertRaisesRegex(ValueError, "SHARD_VARIANT_MISMATCH"):
                opt.merge_x13_mc_shards([s0, s1_bad_var])

            s1_bad_hm = copy.deepcopy(s1)
            s1_bad_hm["horizon_months"] = 12
            with self.assertRaisesRegex(ValueError, "SHARD_HORIZON_MISMATCH"):
                opt.merge_x13_mc_shards([s0, s1_bad_hm])

            s1_zero_n = copy.deepcopy(s1)
            s1_zero_n["n_paths"] = 0
            with self.assertRaisesRegex(ValueError, "INVALID_X13_RANGE"):
                opt.merge_x13_mc_shards([s0, s1_zero_n])

            s1_nan = copy.deepcopy(s1)
            s1_nan["rollover_reset_sensitivity"]["rows"][0]["ev_npv_24m_usd"] = float("nan")
            with self.assertRaisesRegex(ValueError, "NON_FINITE_SHARD_METRIC"):
                opt.merge_x13_mc_shards([s0, s1_nan])

            # - Bool & invalid coords fail closed on run_x13_mc_shard!
            with self.assertRaisesRegex(ValueError, "INVALID_X13_INT"):
                opt.run_x13_mc_shard(job_id="cap_v3_bool", shard_id=True, num_shards=2, n_paths=10, tapes_dir=tdir)
            with self.assertRaisesRegex(ValueError, "INVALID_X13_RANGE"):
                opt.run_x13_mc_shard(job_id="cap_v3_hm0", horizon_months=0, n_paths=10, tapes_dir=tdir)

            # - Explicit nonexistent --catalog with --x13-shard MUST fail closed!
            missing_cat = Path(td) / "no_such_catalog.json"
            with self.assertRaisesRegex(FileNotFoundError, "X13_CATALOG_NOT_FOUND"):
                opt.main([
                    "--x13-shard",
                    "--job-id",
                    "cap_v3_bad_cat",
                    "--tapes-dir",
                    str(tdir),
                    "--catalog",
                    str(missing_cat),
                ])

            # - NAQEX_WORKSPACE_ROOT is honored when repo_root_from fails (bundled X13 layout)!
            from quant_factory.capital_optimizer.constants import _resolve_workspace_root

            fake_bundle_file = Path(td) / "jobs" / "j1" / "src" / "tooling" / "ai-engines" / "a" / "b" / "c.py"
            old_env = os.environ.get("NAQEX_WORKSPACE_ROOT")
            try:
                os.environ["NAQEX_WORKSPACE_ROOT"] = str(Path(td))
                self.assertEqual(_resolve_workspace_root(fake_bundle_file), Path(td).resolve())
            finally:
                if old_env is None:
                    os.environ.pop("NAQEX_WORKSPACE_ROOT", None)
                else:
                    os.environ["NAQEX_WORKSPACE_ROOT"] = old_env

    def test_21b_v3_poisoned_nan_inf_bool_inputs_and_crn_shifting_option(self) -> None:
        ext_days, syn_tapes = self._make_synthetic_tapes(n_days=60, seed=210)
        cat = opt.build_default_pricing_catalog()
        ftmo_std = opt._find_program_by_hint(
            cat, lambda p: p["firm_id"] == "FTMO" and p["steps"] == 2 and p["profile_mode"] == "Standard"
        )
        assert ftmo_std is not None
        cache = opt.ExactTierReplayCache(ext_days, syn_tapes, opt.DEFAULT_CORE7_BASE_RISK, {})
        flat_aud = opt.verify_tapes_flat_at_reset(syn_tapes)
        idx_s = opt.make_block_bootstrap_indices(len(ext_days), horizon=560, n_paths=120, seed=210)

        # (a) NaN / Inf / bool shocks MUST fail closed in rollover sensitivity AND Numba kernel!
        for bad_shock in ((float("nan"),), (float("inf"),), (True,)):
            with self.assertRaisesRegex(ValueError, "INVALID_INPUT"):
                opt.run_rollover_reset_sensitivity(
                    catalog=cat,
                    cache=cache,
                    idx_matrix=idx_s,
                    horizon_days=504,
                    primary_var=opt.PRIMARY_VARIANT_DEFAULT,
                    use_promo_prices=True,
                    usd_vnd=25_765.94,
                    card_fx_fee=0.025,
                    flat_at_reset_audit=flat_aud,
                    shock_levels_pct=bad_shock,  # type: ignore[arg-type]
                )
        with self.assertRaisesRegex(ValueError, "INVALID_INPUT"):
            opt.evaluate_black_friday_2deadline_option(
                catalog=cat,
                ftmo_std=ftmo_std,
                cache=cache,
                idx_matrix=idx_s,
                primary_var=opt.PRIMARY_VARIANT_DEFAULT,
                usd_vnd=25_765.94,
                card_fx_fee=0.025,
                p_go_grid=(float("nan"),),
            )
        with self.assertRaisesRegex(ValueError, "INVALID_INPUT"):
            opt.evaluate_black_friday_2deadline_option(
                catalog=cat,
                ftmo_std=ftmo_std,
                cache=cache,
                idx_matrix=idx_s,
                primary_var=opt.PRIMARY_VARIANT_DEFAULT,
                usd_vnd=25_765.94,
                card_fx_fee=0.025,
                p_xmas_grid=(True,),  # type: ignore[arg-type]
            )

        arrs = _make_synthetic_stage_arrays(60, cap=10_000.0, mean_pct=0.0008, vol_pct=0.005, seed=210)
        with self.assertRaisesRegex(ValueError, "INVALID_MIDNIGHT_SHOCK_NON_FINITE"):
            opt._simulate_single_ticket_rules_numba(
                idx_s[:10, :60],
                *arrs,
                steps=2,
                cap=10_000.0,
                fee_day0_usd=68.70,
                fee_regular_usd=98.61,
                card_fx_fee_pct=0.025,
                withdrawal_fee_pct=0.015,
                fee_refund_pct=1.0,
                p1_target=0.10,
                p2_target=0.05,
                daily_lim=0.05,
                max_dd_lim=0.10,
                dd_type=opt.DD_STATIC,
                trail_lock_initial=False,
                best_day_cap_pct=0.0,
                min_days=4,
                min_prof_days=0,
                min_prof_day_pct=0.0,
                profit_split=0.80,
                payout_cycle_days=10,
                min_payout_usd=50.0,
                strict_lt_breach=True,
                p1_lock_trigger=0.70,
                p2_lock_trigger=0.70,
                amber_dd=0.035,
                red_dd=0.060,
                p1_ea_stop=0.035,
                p2_ea_stop=0.030,
                fn_ea_stop=0.025,
                start_day_offset=0,
                discount_rate_annual=0.06,
                max_retries=0,
                midnight_floating_shock_pct=float("nan"),
                rollover_anchor_mode=opt.ROLLOVER_ANCHOR_EQUITY,
            )

        # (b) CRN shifting-horizon option math: delay_cost_14d > 0 & breakeven p_go* strictly in (0, 1) (NEVER 1.0)!
        bf = opt.evaluate_black_friday_2deadline_option(
            catalog=cat,
            ftmo_std=ftmo_std,
            cache=cache,
            idx_matrix=idx_s,
            primary_var=opt.PRIMARY_VARIANT_DEFAULT,
            usd_vnd=25_765.94,
            card_fx_fee=0.025,
            tiers_usd=(10_000.0,),
        )
        sh_h = bf["tiers"][0]["horizons"]["shifting_horizon_24m"]
        self.assertGreater(sh_h["npv24_bf_day0_usd"], 0.0)
        self.assertGreater(sh_h["delay_cost_14d_usd"], 0.0)
        self.assertLess(sh_h["breakeven_p_go_for_blind_buy"], 1.0)
        self.assertGreater(sh_h["breakeven_p_go_for_blind_buy"], 0.5)
        expected_d14 = sh_h["npv24_bf_day0_usd"] * (1.06 ** (-14.0 / 365.0))
        self.assertAlmostEqual(sh_h["npv24_bf_day14_usd"], expected_d14, delta=0.02)

    @pytest.mark.local_cache
    def test_22_v3_local_cache_post_l7_frozen_tapes_x13_shard_and_parity(self) -> None:
        tapes_dir = opt.DEFAULT_DERIVED_TAPES_DIR
        if not (tapes_dir / f"{opt.DEFAULT_DERIVED_TAPES_STEM}.npz").is_file():
            self.skipTest("Local frozen_9e_tapes_v2 derived cache not present")

        loaded = opt.load_frozen_tapes_v2_direct(tapes_dir=tapes_dir)
        self.assertEqual(loaded["holdout_rows_analysed"], 0)
        self.assertTrue(loaded["max_day_strictly_lt_cutoff"])
        self.assertLess(loaded["max_day"], "2025-01-01")

        # Dev-vs-X13 exact red-news calendar parity (Defect #1: both default to red_news_official_2018_2024.json)!
        from quant_factory.data_store import load_red_news_calendar

        dev_cal = load_red_news_calendar()
        x13_cal, x13_cal_meta = opt.load_red_news_calendar_direct()
        self.assertEqual(x13_cal_meta["source"], "red_news_official_2018_2024.json")
        self.assertEqual(x13_cal, dev_cal)

        # Real post-L7 Core7 flat-at-reset audit & summer EEST 5-minute buffer disclosure!
        audit = opt.verify_tapes_flat_at_reset(loaded["tapes"])
        self.assertTrue(audit["flat_at_reset_verified"])
        self.assertGreater(audit["total_trades_checked"], 2500)
        self.assertEqual(audit["crossing_trades_by_clock"]["PRAGUE_0000"], 0)
        self.assertEqual(audit["crossing_trades_by_clock"]["MT5_EET_0000"], 0)
        self.assertLess(audit["min_buffer_minutes_by_clock"]["MT5_EET_0000"], 10.0)

        # Live X13 shard smoke on real post-L7 frozen_9e_tapes_v2!
        with tempfile.TemporaryDirectory() as td:
            sh = opt.run_x13_mc_shard(
                job_id="cap_v3_live_smoke",
                shard_id=0,
                num_shards=1,
                n_paths=100,
                horizon_months=36,
                tapes_dir=tapes_dir,
                out_dir=Path(td),
            )
            self.assertEqual(sh["holdout_rows_analysed"], 0)
            self.assertEqual(sh["order_send_count"], 0)
            self.assertEqual(sh["red_news_calendar"]["source"], "red_news_official_2018_2024.json")
            self.assertTrue(sh["flat_at_reset_audit"]["flat_at_reset_verified"])
            self.assertTrue(sh["black_friday_2deadline_option"]["weak_dominance_verified"])
            for tier in sh["black_friday_2deadline_option"]["tiers"]:
                self.assertLess(tier["horizons"]["shifting_horizon_24m"]["breakeven_p_go_for_blind_buy"], 1.0)


if __name__ == "__main__":
    unittest.main()

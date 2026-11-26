"""Unit tests for the 4-Pillar Quant Robustness Gate & Research Council G6 integration.

Verifies strictly on synthetic pre-2025 fixtures (zero Holdout 2025+ rows touched):
  1. Random-Entry MC distinguishes true timing skill (>= 90%) from passive bull-trend drift (< 90% same-side).
  2. Separate BUY / SELL symmetry audit fails trend-biased strategies whose short side loses money.
  3. Top-5% outlier trim kills lottery-ticket strategies while passing steady edge strategies.
  4. Worst-Year P10 ranking prefers steady resilience over high-total-return strategies with a blow-up year.
  5. Holdout date cutoff (`>= 2025-01-01`) raises `AssertionError("HOLDOUT_CONTAMINATION")` fail-closed.
  6. `research_council.critique_proposal` enforces optional `G6_robustness_gate` cleanly without breaking legacy callers.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import sys
import unittest

import numpy as np

AI_ENGINES = Path(__file__).resolve().parents[1]
if str(AI_ENGINES) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES))

from quant_core.holdout_guard import HoldoutLockError
from quant_factory.research_council import EvidenceBundle, KillCriteria, critique_proposal, propose_hypothesis
from quant_factory.robustness_gate import (
    ORDER_SEND_CAPABLE,
    RobustnessThresholds,
    buy_sell_symmetry_audit,
    evaluate_robustness_gate,
    random_entry_mc_on_bars,
    random_entry_mc_on_closes,
    top_outlier_trim_audit,
    worst_year_stability_audit,
)


def _gen_days(start: date, count: int, step_days: int = 5) -> list[str]:
    return [(start + timedelta(days=i * step_days)).isoformat() for i in range(count)]


class TestRobustnessGate(unittest.TestCase):
    def test_01_random_entry_mc_catches_passive_bull_drift_and_passes_true_edge(self):
        self.assertFalse(ORDER_SEND_CAPABLE)
        # Construct a strong steady uptrend (like Gold 2018-2024): +0.02% per bar with small noise
        rng = np.random.default_rng(42)
        n_bars = 4000
        ts = np.array([1577836800 + i * 300 for i in range(n_bars)], dtype=np.int64)  # 2020-01-01+
        rets = 0.00025 + rng.normal(0.0, 0.0012, size=n_bars)
        bar_o = 100.0 * np.exp(np.cumsum(rets))
        bar_c = bar_o * (1.0 + rng.normal(0.0001, 0.0008, size=n_bars))
        bar_h = np.maximum(bar_o, bar_c) * 1.0010
        bar_l = np.minimum(bar_o, bar_c) * 0.9990

        n_trades = 120
        sides_long = np.ones(n_trades, dtype=np.int64)
        durs = np.full(n_trades, 12, dtype=np.int64)
        sl_fracs = np.full(n_trades, 0.015, dtype=np.float64)
        frics = np.full(n_trades, 0.02, dtype=np.float64)

        # Fake "trend-rider" long strategy: earns roughly the passive uptrend drift (+0.18R/trade)
        # -> beats 50/50 random entry easily, but CANNOT beat >= 90% of random-LONG entries!
        drift_r = np.full(n_trades, 0.18, dtype=np.float64)
        mc_drift = random_entry_mc_on_bars(
            ts=ts, bar_o=bar_o, bar_h=bar_h, bar_l=bar_l, bar_c=bar_c, bar_sec=300,
            trade_r=drift_r, trade_sides=sides_long, trade_durs=durs,
            trade_sl_fracs=sl_fracs, trade_frics=frics, draws=300, seed=101,
        )
        self.assertGreaterEqual(mc_drift["beat_rate_unbiased"], 0.90)
        self.assertLess(mc_drift["beat_rate_same_side"], 0.90)

        # Genuine edge strategy: earns +0.65R/trade net -> beats BOTH 50/50 and same-side >= 90%!
        strong_r = np.full(n_trades, 0.65, dtype=np.float64)
        mc_strong = random_entry_mc_on_bars(
            ts=ts, bar_o=bar_o, bar_h=bar_h, bar_l=bar_l, bar_c=bar_c, bar_sec=300,
            trade_r=strong_r, trade_sides=sides_long, trade_durs=durs,
            trade_sl_fracs=sl_fracs, trade_frics=frics, draws=300, seed=101,
        )
        self.assertGreaterEqual(mc_strong["beat_rate_unbiased"], 0.95)
        self.assertGreaterEqual(mc_strong["beat_rate_same_side"], 0.95)

    def test_02_buy_sell_symmetry_audit_separates_long_and_short(self):
        # Bidirectional with losing short side -> FAIL
        r_asym = np.concatenate([np.full(50, 0.6), np.full(50, -0.2)])
        s_asym = np.concatenate([np.ones(50, dtype=np.int64), -np.ones(50, dtype=np.int64)])
        res_fail = buy_sell_symmetry_audit(r_asym, s_asym)
        self.assertFalse(res_fail["passed"])
        self.assertEqual(res_fail["directionality"], "BIDIRECTIONAL")
        self.assertTrue(any("SELL_EDGE_FAIL" in w for w in res_fail["warnings"]))

        # Bidirectional with both sides positive -> PASS
        r_sym = np.concatenate([np.full(40, 0.4), np.full(40, 0.35), np.full(20, -0.5)])
        s_sym = np.concatenate([np.ones(40, dtype=np.int64), -np.ones(40, dtype=np.int64), np.ones(10, dtype=np.int64), -np.ones(10, dtype=np.int64)])
        res_ok = buy_sell_symmetry_audit(r_sym, s_sym)
        self.assertTrue(res_ok["passed"])

        # Unidirectional disallowed by default, passes when explicitly allowed
        r_uni = np.full(40, 0.4)
        s_uni = np.ones(40, dtype=np.int64)
        self.assertFalse(buy_sell_symmetry_audit(r_uni, s_uni, RobustnessThresholds(allow_unidirectional=False))["passed"])
        self.assertTrue(buy_sell_symmetry_audit(r_uni, s_uni, RobustnessThresholds(allow_unidirectional=True))["passed"])

    def test_03_top5_outlier_trim_catches_lottery_tickets(self):
        # 100 trades: 48 losses (-0.5R = -24R), 50 tiny wins (+0.1R = +5R), 2 lottery wins (+16R = +32R)
        # Raw = +13R, but dropping top 5% of winners (ceil(0.05*52)=3 wins) removes BOTH lottery wins -> -19.1R!
        r_lottery = np.concatenate([np.full(48, -0.5), np.full(50, 0.1), np.full(2, 16.0)])
        res_lot_win = top_outlier_trim_audit(r_lottery, RobustnessThresholds(outlier_trim_basis="winners"))
        self.assertGreater(res_lot_win["raw_sum_r"], 10.0)
        self.assertFalse(res_lot_win["passed"])
        self.assertLess(res_lot_win["trimmed_winners_sum_r"], 0.0)

        res_lot_all = top_outlier_trim_audit(r_lottery, RobustnessThresholds(outlier_trim_basis="all"))
        self.assertFalse(res_lot_all["passed"])
        self.assertLess(res_lot_all["trimmed_all_sum_r"], 0.0)

        # Steady strategy: 60 wins at +1.0R, 40 losses at -1.0R => raw +20R, trim top 5% wins => +17R > 0
        r_steady = np.concatenate([np.full(60, 1.0), np.full(40, -1.0)])
        res_st = top_outlier_trim_audit(r_steady)
        self.assertTrue(res_st["passed"])
        self.assertGreater(res_st["trimmed_winners_sum_r"], 15.0)
        self.assertGreater(res_st["trimmed_winners_pf"], 1.3)

    def test_04_worst_year_stability_and_p10_ranking(self):
        days = _gen_days(date(2018, 1, 5), 350, step_days=7)  # ~2018..2024
        days = [d for d in days if d < "2025-01-01"]
        n = len(days)

        # Steady candidate: modest positive edge every year (~+0.25R/trade)
        r_steady = np.array([0.8 if (i % 2 == 0) else -0.3 for i in range(n)], dtype=np.float64)
        wy_steady = worst_year_stability_audit(r_steady, days, seed=7)

        # Boom-and-bust candidate: huge profit overall, but 2022 blows up (-20R)
        r_boom = np.array(
            [-0.5 if d.startswith("2022") else (1.5 if (i % 2 == 0) else -0.3) for i, d in enumerate(days)],
            dtype=np.float64,
        )
        wy_boom = worst_year_stability_audit(r_boom, days, seed=7)

        self.assertTrue(wy_steady["passed"])
        self.assertFalse(wy_boom["passed"])  # 2022 loss breaches max_worst_year_loss_r (-10R)
        self.assertGreater(float(np.sum(r_boom)), float(np.sum(r_steady)))
        # Worst-year P10 ranking MUST rank steady ABOVE boom-and-bust!
        self.assertGreater(wy_steady["ranking_score_worst_year_p10_r"], wy_boom["ranking_score_worst_year_p10_r"])

    def test_05_holdout_date_guard_fails_closed(self):
        with self.assertRaises((HoldoutLockError, ValueError)) as ctx:
            evaluate_robustness_gate(
                strategy_id="LEAK_TEST",
                trade_r=[1.0, 1.0],
                trade_sides=[1, -1],
                trade_days=["2024-12-30", "2025-01-02"],
            )
        self.assertIn("HOLDOUT_CONTAMINATION", str(ctx.exception))

    def test_06_research_council_g6_integration_and_backward_compat(self):
        rng = np.random.default_rng(123)
        card = propose_hypothesis(
            hypothesis_id="H_ROBUST_TEST",
            title="Synthetic Balanced Alpha",
            asset_universe=["USDJPY"],
            timeframe="M15",
            counterparty_mechanism="Intraday session rebalancing flow",
            economic_rationale="Institutional fixing rebalance creates predictable mean reversion with bounded stop risk.",
            causal_invariants=["No look-ahead", "Swap=0 flat before 21:00 UTC"],
            n_trials_cumulative=10,
            kill_criteria=KillCriteria(min_dsr=0.50, min_cluster_b_sharpe=0.40),
        )
        ret_a = rng.normal(0.0012, 0.004, size=250)
        ret_b = rng.normal(0.0012, 0.004, size=250)

        # 1. Legacy caller without robustness_report -> still APPROVE_FOR_INCUBATION
        ev_legacy = EvidenceBundle(
            cluster_a_returns=ret_a,
            cluster_b_returns=ret_b,
            p_value_raw=0.005,
            family_p_values=(0.005, 0.2, 0.4),
            candidate_index_in_family=0,
            cost_1x_net=120.0,
            cost_2x_net=80.0,
            n_trades_cluster_b=80,
        )
        v_legacy = critique_proposal(card, ev_legacy)
        self.assertEqual(v_legacy["verdict"], "APPROVE_FOR_INCUBATION")
        self.assertNotIn("G6_robustness_gate", v_legacy["gates"])

        # 2. Caller passing a FAIL_FRAGILE robustness report -> HARD KILL!
        days = _gen_days(date(2018, 1, 5), 100, step_days=20)
        closes = 100.0 + np.cumsum(rng.normal(0.0, 0.3, size=1000))
        bad_gate = evaluate_robustness_gate(
            strategy_id="H_ROBUST_TEST",
            trade_r=np.concatenate([np.full(48, -0.5), np.full(50, 0.1), np.full(2, 16.0)]),
            trade_sides=np.concatenate([np.ones(50, dtype=np.int64), -np.ones(50, dtype=np.int64)]),
            trade_days=days,
            closes=closes,
            thresholds=RobustnessThresholds(mc_draws=200),
        )
        self.assertEqual(bad_gate["verdict"], "FAIL_FRAGILE")
        ev_bad = EvidenceBundle(
            cluster_a_returns=ret_a,
            cluster_b_returns=ret_b,
            p_value_raw=0.005,
            family_p_values=(0.005, 0.2, 0.4),
            candidate_index_in_family=0,
            cost_1x_net=120.0,
            cost_2x_net=80.0,
            n_trades_cluster_b=80,
            robustness_report=bad_gate,
        )
        v_bad = critique_proposal(card, ev_bad)
        self.assertEqual(v_bad["verdict"], "REJECT_KILLED")
        self.assertIn("G6_robustness_gate", v_bad["failed_gates"])

        # 3. Caller passing a PASS_ROBUST report -> APPROVE_FOR_INCUBATION!
        good_r = np.array([1.2 if (i % 2 == 0) else -0.4 for i in range(100)], dtype=np.float64)
        good_s = np.array([1 if (i % 4 < 2) else -1 for i in range(100)], dtype=np.int64)
        good_gate = evaluate_robustness_gate(
            strategy_id="H_ROBUST_TEST",
            trade_r=good_r,
            trade_sides=good_s,
            trade_days=days,
            closes=closes,
            thresholds=RobustnessThresholds(mc_draws=200),
        )
        self.assertEqual(good_gate["verdict"], "PASS_ROBUST")
        ev_good = EvidenceBundle(
            cluster_a_returns=ret_a,
            cluster_b_returns=ret_b,
            p_value_raw=0.005,
            family_p_values=(0.005, 0.2, 0.4),
            candidate_index_in_family=0,
            cost_1x_net=120.0,
            cost_2x_net=80.0,
            n_trades_cluster_b=80,
            robustness_report=good_gate,
        )
        v_good = critique_proposal(card, ev_good)
        self.assertEqual(v_good["verdict"], "APPROVE_FOR_INCUBATION")
        self.assertTrue(v_good["gates"]["G6_robustness_gate"]["passed"])


if __name__ == "__main__":
    unittest.main()

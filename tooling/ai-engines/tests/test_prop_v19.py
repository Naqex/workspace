from types import SimpleNamespace
from unittest.mock import patch
import unittest
import numpy as np
from quant_core.asymmetric_opportunity_optimizer import (
    state_geometry, cushion_risk, first_passage_summary, inverse_volatility_weights, volatility_drag)
from prop_v19_paths import preceding_continuity, timeout_request


class V19MathTests(unittest.TestCase):
    def test_static_buffer_recovery_is_not_account_return(self):
        r = state_geometry(-.05)
        self.assertEqual(r["remaining_buffer_pct"], 5)
        self.assertEqual(r["remaining_buffer_ROI_required_pct"], 300)
        self.assertAlmostEqual(r["current_equity_ROI_to_recover_pct"], 100 * 5 / 95)

    def test_near_floor_target_cost_and_positive_state(self):
        self.assertEqual(state_geometry(-.08)["remaining_buffer_ROI_required_pct"], 900)
        self.assertAlmostEqual(state_geometry(.08)["remaining_buffer_ROI_required_pct"], 100 / 9)
        self.assertEqual(state_geometry(.10)["remaining_buffer_ROI_required_pct"], 0)
        with self.assertRaises(ValueError):
            state_geometry(-.10)

    def test_square_root_reduces_less_than_linear_but_is_not_incumbent_increase(self):
        risk = cushion_risk(1, 48000000, 48000000, .5)
        self.assertGreater(risk, 300 * .6)
        self.assertLess(risk, 300)
        self.assertEqual(cushion_risk(1, 45000000, 45000000, .5), 0)

    def test_house_money_bonus_recomputed_and_capped(self):
        self.assertEqual(cushion_risk(1, 52000000, 52000000, .5), 500)
        self.assertEqual(cushion_risk(1, 54000000, 54000000, .5), 600)
        self.assertEqual(cushion_risk(1, 50000000, 50000000, .5), 300)

    def test_funded_does_not_use_challenge_bonus(self):
        self.assertEqual(cushion_risk(3, 54000000, 54000000, .35), 187.5)
        self.assertEqual(cushion_risk(2, 52000000, 52000000, .5), 462.5)

    def test_risk_budget_rejects_unregistered_gamma_and_weight(self):
        for gamma, weight in ((.4, 1), (.5, 3)):
            with self.assertRaises(ValueError):
                cushion_risk(1, 50000000, 50000000, gamma, weight)

    def test_nonfinishers_not_discarded_from_expected_time(self):
        r = first_passage_summary([2, None], 36, failures=1)
        self.assertEqual(r["hit_pct"], 50)
        self.assertEqual(r["conditional_mean_months"], 2)
        self.assertEqual(r["restricted_mean_months"], 19)
        self.assertIsNone(r["unconditional_expected_months"])

    def test_zero_hit_first_passage_remains_censored(self):
        r = first_passage_summary([None] * 4, 36)
        self.assertEqual(r["restricted_mean_months"], 36)
        self.assertIsNone(r["conditional_median_months"])
        with self.assertRaises(ValueError):
            first_passage_summary([37], 36)

    def test_inverse_vol_matches_positive_mean_without_claiming_global_optimum(self):
        rng = np.random.default_rng(42)
        x = rng.normal(size=(1000, 3)) * [1, 1.5, 2] + [2, 2, 2]
        r = inverse_volatility_weights(x)
        self.assertTrue(r["eligible"])
        self.assertAlmostEqual(r["equal_mean"], r["weighted_mean"])
        self.assertIn("not claimed", r["objective"])

    def test_negative_unit_expectancy_cannot_be_fixed_by_weight_normalization(self):
        r = inverse_volatility_weights(-np.ones((200, 3)))
        self.assertFalse(r["eligible"])

    def test_drag_uses_fractional_returns_and_labels_approximation(self):
        r = volatility_drag([-.01, .01, -.01, .01])
        self.assertAlmostEqual(r["approximate_daily_log_drag"], np.var([-.01, .01, -.01, .01], ddof=1) / 2)
        self.assertTrue(r["approximation_not_exact_growth"])


class V19ContinuityTests(unittest.TestCase):
    def test_closed_bar_window_excludes_future_information(self):
        schedule = SimpleNamespace(off_kind=lambda at, asset: None)
        times = np.arange(0, 30 * 60000, 60000)
        self.assertTrue(preceding_continuity(times, 30 * 60000, schedule, "XAUUSD"))
        self.assertTrue(preceding_continuity(np.r_[times, 99 * 60000], 30 * 60000, schedule, "XAUUSD"))

    def test_missing_recent_bar_blocks_entry(self):
        schedule = SimpleNamespace(off_kind=lambda at, asset: None)
        times = np.delete(np.arange(0, 30 * 60000, 60000), 15)
        self.assertFalse(preceding_continuity(times, 30 * 60000, schedule, "EURUSD"))

    def test_known_closed_minutes_not_mistaken_for_source_gaps(self):
        schedule = SimpleNamespace(off_kind=lambda at, asset: "DAILY_BREAK" if at < 10 * 60000 else None)
        self.assertTrue(preceding_continuity(np.arange(10 * 60000, 30 * 60000, 60000),
                                            30 * 60000, schedule, "XAUUSD"))

    def test_timeout_request_is_after_last_observation_not_hindsight_close(self):
        g = dict(before=1000000, after=2000000, source_uncertain=True)
        request = timeout_request([g], 900000, 3000000)
        self.assertEqual(request, 1180000)
        self.assertLess(request, g["after"])
        self.assertGreater(request, g["before"])

    def test_known_session_break_or_future_gap_does_not_create_timeout(self):
        self.assertIsNone(timeout_request([dict(before=1000000, after=2000000, source_uncertain=False)],
                                         900000, 3000000))
        self.assertIsNone(timeout_request([dict(before=1000000, after=2000000, source_uncertain=True)],
                                         900000, 1100000))

    def test_reused_probe_binds_writer_as_well_as_input_directory(self):
        import prop_v19_sources as current
        import prop_v16_sources as previous
        from quant_core.prop_lifecycle_and_parity import bindings
        def intercepted():
            self.assertEqual(previous.JOB, current.JOB)
            self.assertIs(previous.save, current.save)
            raise RuntimeError("probe_stopped_before_IO")
        with patch.object(previous, "native_probe", intercepted):
            with self.assertRaisesRegex(RuntimeError, "probe_stopped_before_IO"):
                current.probes()


class V19AccountTests(unittest.TestCase):
    def test_import_gate_statement_walk_keeps_all_nested_imports(self):
        import ast
        from pathlib import Path
        import independent_ledger_auditor
        from test_independent_ledger_auditor import imported_from_modules
        fixtures = [Path(independent_ledger_auditor.__file__).read_text(),
            "def f():\n try:\n  from prop_bad import x\n except Exception:\n  from quant_core.bad import y\n",
            "class A:\n def g(self):\n  if True:\n   from nested import z\n",
            "match 1:\n case 1:\n  from inside_case import a\n"]
        for text in fixtures:
            tree = ast.parse(text)
            self.assertCountEqual(imported_from_modules(tree),
                [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)])

    def test_scalar_oracle_point_keeps_equality_breach_and_all_drawdowns(self):
        from independent_ledger_auditor import V14LedgerOracle
        from prop_v19_stress import FastV16Oracle
        for cash in (47500010, 47500000, 47499990):
            objects = [object.__new__(klass) for klass in (V14LedgerOracle, FastV16Oracle)]
            for obj in objects:
                obj.e = dict(rolling=True)
                obj.open, obj.carry, obj.trades = {}, {}, []
                obj.coeff, obj.basis = [0] * 4, 0
                obj.cash, obj.anchor, obj.peak = cash, 50000000, 51000000
                obj.dd = obj.daily = obj.static = 0
                obj.breach = None
                obj.observe = lambda at: None
                obj.point(123, {})
            for key in ("dd", "daily", "static", "peak", "breach"):
                self.assertEqual(getattr(objects[0], key), getattr(objects[1], key))

    def test_costs_admissions_and_equity_match_separate_oracle(self):
        from test_sl_active_kernel import fixture
        from prop_v14_paths import build
        from quant_core.gap_aware_execution import GapAwarePathIndex
        from quant_core.ftmo_execution_and_calendar import SessionSchedule
        from quant_core.prop_lifecycle_and_parity import simulate, bindings
        from prop_v18_costs import cost_bindings
        from prop_v19_accounts import V19Account, V19LedgerOracle
        import prop_v14_review as review
        bars, m = fixture([(100, 101, 99, 100), (100, 104, 99, 103), (103, 108, 101, 107)])
        m.update(asset="XAUUSD", _index=GapAwarePathIndex(bars, asset="XAUUSD", schedule=SessionSchedule([])))
        trades, readers, missing = build({"XAUUSD|F3:test|DAY|P0": m}, "OPEN_LOW_HIGH_CLOSE",
                                         {"XAUUSD": bars, "EURUSD": bars})
        self.assertFalse(missing)
        for t in trades:
            t["spread_units"] = int(bars["ao"][0]) - int(bars["bo"][0])
        for gamma in (None, .35, .5):
            for pct in (100, 150):
                profile = dict(name="BASE_GUARD" if gamma is None else "O1_G035" if gamma == .35 else "O1_G050",
                               gamma=gamma, weights={trades[0]["id"]: 1.})
                first, end = int(bars["t"][0]), int(bars["t"][-1]) + 60000
                account = V19Account(first, end, "SYM_FLAT", rolling=True, profile=profile, friction_pct=pct)
                with cost_bindings(pct):
                    rows = simulate(trades, readers, [account], first, end, SimpleNamespace(events={}))
                    with bindings(review, V14LedgerOracle=V19LedgerOracle):
                        checked = review.audit_accounts(rows, trades, readers, SimpleNamespace(events={}), first, end)
                self.assertEqual(checked[0]["entries"], 1)

    def test_hypothetical_opening_loss_keeps_static_floor_and_cash_bridge(self):
        from test_sl_active_kernel import fixture
        from prop_v14_paths import build
        from quant_core.gap_aware_execution import GapAwarePathIndex
        from quant_core.ftmo_execution_and_calendar import SessionSchedule
        from quant_core.prop_lifecycle_and_parity import simulate, bindings
        from prop_v18_costs import cost_bindings
        from prop_v19_stress import OpeningV19, OpeningV19Oracle
        import prop_v14_review as review
        bars, m = fixture([(100, 101, 99, 100), (100, 104, 99, 103), (103, 108, 101, 107)])
        m.update(asset="XAUUSD", _index=GapAwarePathIndex(bars, asset="XAUUSD", schedule=SessionSchedule([])))
        trades, readers, _ = build({"XAUUSD|F3:test|DAY|P0": m}, "OPEN_LOW_HIGH_CLOSE",
                                   {"XAUUSD": bars, "EURUSD": bars})
        for t in trades:
            t["spread_units"] = int(bars["ao"][0]) - int(bars["bo"][0])
        profile = dict(name="O1_G050", gamma=.5, weights={trades[0]["id"]: 1.})
        for shift in (-4000000, 4000000):
            first, end = int(bars["t"][0]), int(bars["t"][-1]) + 60000
            account = OpeningV19(first, end, "SYM_FLAT", rolling=True, profile=profile,
                                 friction_pct=100, opening_adjustment=shift)
            with cost_bindings(100):
                rows = simulate(trades, readers, [account], first, end, SimpleNamespace(events={}))
                with bindings(review, V14LedgerOracle=OpeningV19Oracle):
                    checked = review.audit_accounts(rows, trades, readers, SimpleNamespace(events={}), first, end)
            self.assertTrue(checked[0]["cash_bridge"])
            self.assertEqual(rows[0]["opening_adjustment_milli"], shift)
            self.assertGreaterEqual(rows[0]["static_loss_pct"], 8 if shift < 0 else 0)


if __name__ == "__main__":
    unittest.main()

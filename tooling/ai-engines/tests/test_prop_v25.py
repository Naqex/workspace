import unittest
from fractions import Fraction
from prop_v25_risk import iso_weights, decide
from prop_v25_gbp import exact_pass, H1ScenarioQuotes, scenario_trades
from quant_core.market_data_store import BAR
from prop_v25_cost_audit import frozen_entry_cost_units
import numpy as np


class RiskScreenTests(unittest.TestCase):
    def test_iso_uses_both_caps_and_preserves_relative_weights(self):
        c, weights = iso_weights(dict(baseline=dict(equity_R_DD=12, max_open_risk_USD=300),
                                      candidate=dict(equity_R_DD=15, max_open_risk_USD=301)))
        self.assertEqual(c, Fraction(4, 5))
        self.assertAlmostEqual(weights["F5"] / weights["F3"], 13 / 7)
        c, _ = iso_weights(dict(baseline=dict(equity_R_DD=12, max_open_risk_USD=300),
                               candidate=dict(equity_R_DD=13, max_open_risk_USD=600)))
        self.assertEqual(c, Fraction(1, 2))

    def test_exact_equal_dd_is_allowed_but_actual_increase_still_fails(self):
        base = dict(net_R=23, equity_R_DD=12, static_R_loss=4, worst_daily_R=2,
                    max_open_risk_USD=300, cluster_R=[10, 13])
        candidate = dict(base, net_R=26)
        self.assertTrue(decide(candidate, base)["passed"])
        for change in (dict(equity_R_DD=12.001), dict(max_open_risk_USD=300.01),
                       dict(cluster_R=[-1, 27]), dict(net_R=23),
                       dict(equity_R_DD=float("nan")), dict(net_R=True), dict(cluster_R=[1])):
            self.assertFalse(decide(dict(candidate, **change), base)["passed"])


class GBPResolutionTests(unittest.TestCase):
    def test_cost_boundary_uses_price_units(self):
        self.assertGreater((9/100000+.00009)/(120/100000), .15)
        self.assertTrue(exact_pass(9, 120, 15))
        self.assertFalse(exact_pass(9, 119, 15))
        self.assertTrue(exact_pass(9, 121, 15))

    def test_hourly_extrema_are_not_disguised_as_minute_observations(self):
        bars = np.array([(0,100,130,90,110,109,139,99,119)], dtype=BAR)
        q = H1ScenarioQuotes(bars, "OLHC").points(0, 3599999)
        self.assertEqual(q["t"].tolist(), [0,1200000,2400000,3599999])
        self.assertEqual(q["b"].tolist(), [100,90,130,110])
        self.assertEqual(len(H1ScenarioQuotes(bars, "OHLC").points(0, 0)), 1)

    def test_frozen_raw_admission_does_not_silently_adopt_native_fee_rounding(self):
        cost, scale = frozen_entry_cost_units("XAUUSD", 1340879, 338)
        self.assertEqual(cost / scale, Fraction("0.756772306"))
        self.assertNotEqual(cost / scale, Fraction("0.7568"))

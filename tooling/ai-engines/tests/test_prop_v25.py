import unittest
from fractions import Fraction
from prop_v25_risk import iso_weights, decide


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

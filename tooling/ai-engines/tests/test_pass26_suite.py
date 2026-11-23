"""Unit tests for Pass 26 (Cross-Asset Relative Strength, G6 Factor Decomposition, and strict causal timestamp lookup)."""

import unittest
import numpy as np

import pass26_cross_asset_rs as p26


class TestPass26Suite(unittest.TestCase):
    def test_pass26_catalog_has_34_unique_specs_across_5_families(self):
        cat = p26.build_pass26_catalog()
        self.assertEqual(len(cat), 34)
        self.assertEqual(len({c["id"] for c in cat}), 34)
        self.assertEqual(len({c["fam"] for c in cat}), 5)

    def test_causal_completed_bid_never_reads_at_or_after_decision_timestamp(self):
        # Bar 0 at t=1000 closes at 1.10; Bar 1 at t=1060 closes at 1.99 (future relative to ts=1060!)
        times = np.array([1000, 1060, 1120], dtype=np.int64)
        quotes = np.array([
            [1.09, 1.11, 1.08, 1.10, 1.091, 1.111, 1.081, 1.101],
            [1.10, 2.00, 1.10, 1.99, 1.101, 2.001, 1.101, 1.991],
            [1.99, 2.05, 1.95, 2.00, 1.991, 2.051, 1.951, 2.001],
        ], dtype=np.float64)
        # Asking for completed bid BEFORE ts=1060 MUST return 1.10 (Bar 0), NEVER 1.99 (Bar 1)!
        self.assertAlmostEqual(p26.causal_completed_bid(times, quotes, 1060), 1.10, places=6)
        # Stale check: ts=20000 (>7200s after last bar) returns None
        self.assertIsNone(p26.causal_completed_bid(times, quotes, 20000))

    def test_g6_currency_factor_decomposition_signs(self):
        # Pure USD rally: USDJPY +1, USDCAD +1, EURUSD -1, GBPUSD -1, AUDUSD -1, EURJPY 0, GBPJPY 0
        z = {"USDJPY": 1.0, "USDCAD": 1.0, "EURUSD": -1.0, "GBPUSD": -1.0, "AUDUSD": -1.0, "EURJPY": 0.0, "GBPJPY": 0.0}
        fac = p26.compute_g6_factors(z)
        self.assertAlmostEqual(fac["USD"], 1.0, places=6)
        self.assertLess(fac["EUR"], 0.0)
        self.assertLess(fac["CAD"], 0.0)


if __name__ == "__main__":
    unittest.main()

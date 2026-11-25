"""Unit & causality tests for Pass 14 batch screener, USDJPY JPY-quote conversion, FDR, and 3-tier tagging."""

import sys
from pathlib import Path
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pass14_intel_top15_batch as p14


class Pass14BatchTests(unittest.TestCase):
    def test_jpy_quote_conversion_and_usdjpy_positive_long_swap(self):
        jpy_spec = {
            "trade_contract_size": 100000.0,
            "point": 0.001,
            "currency_profit": "JPY",
            "swap_long": 2.61,
            "swap_short": -17.6,
            "swap_rollover3days": 3,
        }
        # +1.00 JPY move on 1 lot USDJPY at exit=150.00 -> 100,000 / 150 = $666.6667
        usd = p14.price_to_usd_per_lot("USDJPY", 1.0, 150.0, jpy_spec)
        self.assertAlmostEqual(usd, 666.6666667, places=4)

        # Tue 2024-01-09 01:00 UTC -> Thu 2024-01-11 01:00 UTC crosses Tue 17:00 NY (1x) + Wed 17:00 NY (3x) = 4x!
        t0 = 1704762000  # 2024-01-09 01:00 UTC
        t1 = 1704934800  # 2024-01-11 01:00 UTC
        sw_l, n1, n3 = p14.swap_usd_per_lot("USDJPY", t0, t1, 1, jpy_spec, 150.0)
        self.assertEqual((n1, n3), (1, 1))
        self.assertGreater(sw_l, 0.0)
        self.assertAlmostEqual(sw_l, 2.61 * 0.001 * 100000.0 / 150.0 * 4.0, places=4)

    def test_benjamini_hochberg_fdr_monotonicity(self):
        ps = [0.001, 0.04, 0.20, 0.80]
        qs = p14.benjamini_hochberg(ps)
        self.assertAlmostEqual(qs[0], 0.004, places=6)
        self.assertAlmostEqual(qs[1], 0.08, places=6)
        self.assertAlmostEqual(qs[2], 0.2666667, places=5)
        self.assertAlmostEqual(qs[3], 0.80, places=6)
        self.assertTrue(qs[0] <= qs[1] <= qs[2] <= qs[3])

    def test_three_tier_classification_distinguishes_ftmo_vs_personal_vault_vs_dead(self):
        def make_trades(ftmo_r_val, ex_sf_val, n_per_year=6):
            out = []
            for y in range(2018, 2025):
                for k in range(n_per_year):
                    out.append({
                        "year": y, "side": 1, "reason": "TP_GAP_OR_TOUCH",
                        "gross_usd": 100.0, "ftmo_comm_slip": 10.0, "ftmo_swap": -80.0,
                        "ftmo_net": ftmo_r_val * 100.0, "ftmo_R": ftmo_r_val,
                        "ex_R_normal": ex_sf_val, "ex_R_swapfree": ex_sf_val,
                    })
            return out

        # Case 1: Survives FTMO + MC Null -> TIER_1_FTMO_READY
        mc_pass = {"gross_p_value": 0.01, "ftmo_net_p_value": 0.01}
        r1 = p14.summarize_pair("TEST1", "EURUSD", True, make_trades(0.6, 0.7), mc_pass)
        self.assertEqual(r1["tier"], "TIER_1_FTMO_READY")

        # Case 2: Killed by FTMO Swap (-0.1R) but strong price alpha (gross_p=0.01) & positive Exness -> TIER_2_PERSONAL_VAULT
        mc_swap_killed = {"gross_p_value": 0.01, "ftmo_net_p_value": 0.60}
        r2 = p14.summarize_pair("TEST2", "EURUSD", True, make_trades(-0.1, 0.5), mc_swap_killed)
        self.assertEqual(r2["tier"], "TIER_2_PERSONAL_VAULT")

        # Case 3: Fails random-entry null (p=0.30) even if positive -> TIER_3_DEAD_NO_EDGE (drift illusion!)
        mc_fail = {"gross_p_value": 0.30, "ftmo_net_p_value": 0.30}
        r3 = p14.summarize_pair("TEST3", "XAUUSD", False, make_trades(0.5, 0.6), mc_fail)
        self.assertEqual(r3["tier"], "TIER_3_DEAD_NO_EDGE")


if __name__ == "__main__":
    unittest.main()

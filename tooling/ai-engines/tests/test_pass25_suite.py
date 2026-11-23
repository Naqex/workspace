"""Unit tests for Pass 25 (USDCAD CAD-quote conversion, BTCUSD % slippage accounting, and 34-spec catalog)."""

import unittest
import numpy as np

import pass24_mtf_new_archetypes as p24
import pass25_new_assets_engine56 as p25


class TestPass25Suite(unittest.TestCase):
    def test_pass25_catalog_has_34_specs_per_asset(self):
        cat = p25.build_pass25_catalog()
        self.assertEqual(len(cat), 34)
        self.assertEqual(len({c["id"] for c in cat}), 34)

    def test_usdcad_cad_currency_conversion_is_exact(self):
        t0 = 1577952000
        times = np.array([t0, t0 + 60], dtype=np.int64)
        # USDCAD moves +0.0100 (100 pips) from 1.3000 to 1.3100 -> 1 lot = 1000 CAD / 1.31 = $763.3588 USD
        quotes = np.array([
            [1.2999, 1.3000, 1.2995, 1.3000, 1.3000, 1.3001, 1.2996, 1.3001],
            [1.3100, 1.3100, 1.3100, 1.3100, 1.3101, 1.3101, 1.3101, 1.3101],
        ], dtype=np.float64)
        spec = {"trade_contract_size": 100000.0, "currency_profit": "CAD"}
        tr = p24.replay_causal_intraday("USDCAD", times, quotes, 0, 1, 1, 1.3000, 1.2900, spec=spec)
        self.assertAlmostEqual(tr["gross_usd"], 1000.0 / 1.3100, places=3)

    def test_btcusd_percentage_slippage_tiers_are_monotonic(self):
        t0 = 1577952000
        times = np.array([t0, t0 + 60], dtype=np.int64)
        # BTCUSD entry 50000, SL 49000 (risk 1000), exit 51000 (gross +1000)
        # Base 0.05% = $25 -> R = 975/1025; Stress 0.15% = $75 -> R = 925/1075; Double 0.30% = $150 -> R = 850/1150
        quotes = np.array([
            [49990.0, 50010.0, 49950.0, 50000.0, 50000.0, 50020.0, 49960.0, 50010.0],
            [51000.0, 51000.0, 51000.0, 51000.0, 51010.0, 51010.0, 51010.0, 51010.0],
        ], dtype=np.float64)
        tr = p24.replay_causal_intraday("BTCUSD", times, quotes, 0, 1, 1, 50000.0, 49000.0)
        self.assertAlmostEqual(tr["base_R"], 975.0 / 1025.0, places=4)
        self.assertAlmostEqual(tr["ftmo_R"], 925.0 / 1075.0, places=4)
        self.assertAlmostEqual(tr["double_R"], 850.0 / 1150.0, places=4)
        self.assertGreater(tr["base_R"], tr["ftmo_R"])
        self.assertGreater(tr["ftmo_R"], tr["double_R"])


if __name__ == "__main__":
    unittest.main()

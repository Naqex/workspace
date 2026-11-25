"""Unit & causality tests for Pass 15 FTMO-native Engine #2 screen (XAU intraday zero-swap + FX positive carry)."""

from datetime import date
import sys
from pathlib import Path
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pass15_ftmo_native_engine2 as p15


class Pass15FtmoNativeTests(unittest.TestCase):
    def test_xau_intraday_envelope_reconciles_terminal_cash_and_zero_swap(self):
        # 120 minutes synthetic XAUUSD bar path starting 2024-01-09 13:00 UTC
        start_sec = 1704805200
        times = start_sec + np.arange(120, dtype=np.int64) * 60
        bid = np.tile(np.array([2030.0, 2031.0, 2029.5, 2030.5]), (120, 1))
        bid[-1] = [2040.0, 2041.0, 2039.5, 2040.5]
        quotes = np.hstack([bid, bid + 0.50])
        spec = {"trade_contract_size": 100.0, "point": 0.01, "currency_profit": "USD",
                "swap_long": -56.28, "swap_short": -4.2, "swap_rollover3days": 3}
        ctx = {"asset": "XAUUSD", "times": times, "quotes": quotes, "spec": spec}
        slc = p15._m1_portfolio_slice(ctx, 0, 1, 2030.5, 2020.0, int(times[-1]))
        self.assertIsNotNone(slc)
        row, stamps, marks = slc
        self.assertEqual(row["reason"], "HARD_FLAT")
        self.assertAlmostEqual(float(marks[-1, -1]), row["net_usd_per_lot"], places=6)
        self.assertGreater(row["net_R"], 0.0)

        # Verify zero swap on intraday replay
        tr = p15.p14.replay_trade_m1("XAUUSD", times, quotes, 0, 1, 2030.5, 2020.0, None, int(times[-1]), spec, intraday_flat=True)
        self.assertEqual(tr["ftmo_swap"], 0.0)
        self.assertEqual(tr["ftmo_n3"], 0)


if __name__ == "__main__":
    unittest.main()

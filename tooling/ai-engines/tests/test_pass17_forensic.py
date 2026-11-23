"""Regression & reconciliation tests for Pass 17 USDJPY M1 floating equity and US500 expansion."""

from datetime import date, datetime, timezone
import sys
from pathlib import Path
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pass17_usdjpy_forensic_cross as p17


class Pass17ForensicTests(unittest.TestCase):
    def test_usdjpy_exp_tape_terminal_mark_reconciles_with_cash_and_prague_same_day(self):
        # Build 1 synthetic UTC trading day 2024-01-09 (1300 minutes 00:00..21:39 UTC)
        day_sec = int(datetime(2024, 1, 9, 0, 0, tzinfo=timezone.utc).timestamp())
        times = day_sec + np.arange(1300, dtype=np.int64) * 60
        quotes = np.zeros((1300, 8), dtype=np.float64)
        # Base price 144.000 bid / 144.010 ask
        quotes[:, :4] = 144.000
        quotes[:, 4:8] = 144.010
        # At 09:00 UTC (minute 540), spike above open_0 + 0.80 * 1.00 = 144.800
        quotes[540:, :4] = 145.000
        quotes[540:, 4:8] = 145.010
        quotes[540, 5] = 145.050
        quotes[1255:, :4] = 145.600
        quotes[1255:, 4:8] = 145.610

        d0 = {"date": date(2024, 1, 8), "day_sec": day_sec - 86400, "fi": -1, "ei": -1, "o": 143.0, "h": 144.0, "l": 143.0, "c": 144.0}
        d1 = {"date": date(2024, 1, 9), "day_sec": day_sec, "fi": 0, "ei": 1300, "o": 144.0, "h": 145.6, "l": 144.0, "c": 145.6}
        ctx = {
            "times": times, "quotes": quotes,
            "full_d1": [d0, d1], "d1_offset": 1,
            "d1_atr": np.array([1.0, 1.0]), "d1_c": np.array([144.0, 145.6]),
        }
        tape = p17.build_usdjpy_exp_tape(ctx, trig_atr=0.80, sl_atr=0.75, addon=0.005)
        self.assertEqual(len(tape), 1)
        row, stamps, marks = tape[0]
        self.assertEqual(row["side"], 1)
        self.assertEqual(row["reason"], "HARD_FLAT")
        self.assertAlmostEqual(float(marks[-1, -1]), row["net_usd_per_lot"], places=6)
        self.assertEqual(p17.jpy_eq.prague_day(int(stamps[0])), p17.jpy_eq.prague_day(int(stamps[-1])))


if __name__ == "__main__":
    unittest.main()

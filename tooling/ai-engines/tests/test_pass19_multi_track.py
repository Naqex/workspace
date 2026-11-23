"""Unit tests for Pass 19: US500 overnight exact FTMO swap, causal SuperTrend(10,3), and step-trailing stop."""

from datetime import datetime, timezone
import unittest

import numpy as np

import pass19_us500_supertrend_yencross as p19
from quant_core.ftmo_track_replay import profiles


class TestPass19MultiTrack(unittest.TestCase):
    def test_supertrend_causal_direction_flip(self):
        """Verify SuperTrend(10, 3.0) flips causally from downtrend to uptrend on clean break."""
        n = 40
        closes = np.concatenate([np.linspace(100.0, 90.0, 20), np.linspace(91.0, 115.0, 20)])
        highs = closes + 0.5
        lows = closes - 0.5
        st_dir, st_band, st_atr = p19.supertrend(highs, lows, closes, period=10, mult=3.0)
        self.assertEqual(int(st_dir[15]), -1)
        self.assertEqual(int(st_dir[-1]), 1)
        self.assertTrue(np.isfinite(st_band[-1]))
        self.assertLess(st_band[-1], closes[-1])

    def test_step_trailing_locks_profit_after_1r_without_lookahead(self):
        """Verify step-trailing checks SL BEFORE moving SL on bar k, and locks +0.5R after +1.0R."""
        specs, _ = profiles()
        t0 = int(datetime(2020, 1, 2, 14, 30, tzinfo=timezone.utc).timestamp())
        times = np.array([t0 + i * 60 for i in range(4)], dtype=np.int64)
        # Entry Ask=100.0, init SL=90.0 (1R=10.0)
        quotes = np.array([
            [99.5, 100.0, 99.0, 99.5, 100.0, 100.5, 99.5, 100.0],
            # Bar 1 rises to Bid High=111.0 (+1.1R -> step=1 locks SL at 105.0 for Bar 2+)
            [100.0, 111.0, 99.5, 110.5, 100.5, 111.5, 100.0, 111.0],
            # Bar 2 pulls back to Bid Low=104.0 -> must trigger TRAIL_SL at 105.0!
            [110.0, 110.5, 104.0, 104.5, 110.5, 111.0, 104.5, 105.0],
            [104.5, 105.0, 104.0, 104.5, 105.0, 105.5, 104.5, 105.0],
        ], dtype=np.float64)
        tr = p19.replay_step_trailing_m1(
            "US500", times, quotes, entry_idx=0, side=1, entry_p=100.0, init_sl=90.0,
            max_exit_sec=t0 + 3600, spec=specs["Swing"]["US500.cash"], is_us500=True,
        )
        self.assertIsNotNone(tr)
        self.assertEqual(tr["reason"], "TRAIL_SL")
        self.assertAlmostEqual(tr["gross_usd"], 5.0, places=6)
        self.assertEqual(tr["ftmo_swap"], 0.0)

    def test_us500_multiday_charges_exact_ftmo_swap_and_friday_3x(self):
        """Verify Friday-to-Monday US500 LONG hold charges exact 3x FTMO Swing swap (-$4.1409)."""
        specs, _ = profiles()
        # Fri 2020-01-03 20:50 UTC (15:50 ET) -> Mon 2020-01-06 14:35 UTC (09:35 ET)
        t_fri = int(datetime(2020, 1, 3, 20, 50, tzinfo=timezone.utc).timestamp())
        t_mon = int(datetime(2020, 1, 6, 14, 35, tzinfo=timezone.utc).timestamp())
        times = np.array([t_fri, t_mon], dtype=np.int64)
        quotes = np.array([
            [3230.0, 3231.0, 3229.0, 3230.0, 3230.5, 3231.5, 3229.5, 3230.5],
            [3240.0, 3241.0, 3239.0, 3240.0, 3240.5, 3241.5, 3239.5, 3240.5],
        ], dtype=np.float64)
        tr = p19.sim_us500_multiday_m1(
            times, quotes, 0, 1, 1, 30.0, specs["Swing"]["US500.cash"],
            day_key="2020-01-03", year=2020, slip_side=0.75,
        )
        self.assertIsNotNone(tr)
        self.assertEqual(tr["ftmo_n3"], 1)
        self.assertAlmostEqual(tr["ftmo_swap"], -138.03 * 0.01 * 3.0, places=4)

    def test_timing_permutation_p_detects_real_timing(self):
        nets = [10.0] * 30 + [-10.0] * 70
        mask = [True] * 30 + [False] * 70
        p = p19.timing_permutation_p(nets, mask, draws=300)
        self.assertLess(p, 0.01)


if __name__ == "__main__":
    unittest.main()

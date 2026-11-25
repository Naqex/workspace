"""Regression and causality tests for Pass 13 triple-track Engine #2 modules."""

from datetime import datetime, timezone
import sys
from pathlib import Path
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pass13_fx_sweep as fx
import pass13_intel_cleanroom as intel
import pass13_us500_explicit as us500


class Pass13TripleTrackTests(unittest.TestCase):
    def test_track1_causal_sweep_reclaim_enters_next_minute_and_skips_dual_sweep(self):
        # Build a clean 1021-minute synthetic London session: box [0..480) = [1.2000, 1.2050]
        offsets = np.arange(fx.FLAT + 1, dtype=np.int64)
        quotes = np.zeros((len(offsets), 8), dtype=np.float64)
        # Constant bid=1.2020, ask=1.2022 inside box
        quotes[:, :4] = 1.2020
        quotes[:, 4:8] = 1.2022
        quotes[10, 5] = 1.2050  # box_high (ask_high)
        quotes[20, 2] = 1.2000  # box_low (bid_low)

        # Bar 500: sweeps above box_high (ask_high=1.2060) and closes back inside (bid_close=1.2045 < 1.2050)
        quotes[500, 5] = 1.2060
        quotes[500, 3] = 1.2045
        # Bar 501 (next minute): bid_open=1.2044, ask_open=1.2046 -> causal SELL fill at 1.2044
        quotes[501, 0] = 1.2044
        quotes[501, 4] = 1.2046

        status, sig = fx.detect_sweep(offsets, quotes, box_end=480, buffer_pips=2.0)
        self.assertEqual(status, "sweep_reclaim")
        self.assertEqual(sig["side"], -1)
        self.assertEqual(sig["trigger_idx"], 500)
        self.assertEqual(sig["entry_idx"], 501)
        self.assertAlmostEqual(sig["entry_price"], 1.2044)
        self.assertAlmostEqual(sig["stop"], 1.2062)

        # Worst-case SL-first when both SL and TP touched in the same minute (bar 510)
        quotes[510, 5] = 1.2065  # ask_high hits SL (1.2062)
        quotes[510, 6] = 1.1995  # ask_low hits TP (box_low=1.2000)
        end_j, ex_p, _gap, reason = fx.simulate_exit(quotes, sig, use_opp_tp=True)
        self.assertEqual(end_j, 510)
        self.assertEqual(reason, "SL_GAP_OR_TOUCH")
        self.assertAlmostEqual(ex_p, 1.2062)

        # Dual sweep before reclaim must be skipped
        quotes_dual = quotes.copy()
        quotes_dual[495, 5] = 1.2060  # sweep high, close stays >= 1.2050
        quotes_dual[495, 3] = 1.2055
        quotes_dual[496, 2] = 1.1990  # sweep low before any reclaim
        status2, sig2 = fx.detect_sweep(offsets, quotes_dual, box_end=480, buffer_pips=2.0)
        self.assertEqual(status2, "dual_sweep_skip")
        self.assertIsNone(sig2)

    def test_track2_nen022_causal_fakey_detection_and_wednesday_triple_swap(self):
        # 3 consecutive H4 bars: mother [100, 110], inside [102, 108], bullish fakey low=101, high=107, open=103, close=105
        h4 = [
            {"bucket": 100, "start_sec": 100 * 14400, "end_sec": 101 * 14400, "o": 102.0, "h": 110.0, "l": 100.0, "c": 108.0},
            {"bucket": 101, "start_sec": 101 * 14400, "end_sec": 102 * 14400, "o": 106.0, "h": 108.0, "l": 102.0, "c": 104.0},
            {"bucket": 102, "start_sec": 102 * 14400, "end_sec": 103 * 14400, "o": 103.0, "h": 107.0, "l": 101.0, "c": 105.0},
        ]
        sigs = intel.detect_nen022_signals(h4)
        self.assertEqual(len(sigs), 1)
        self.assertEqual(sigs[0]["side"], 1)
        self.assertEqual(sigs[0]["signal_close_sec"], 103 * 14400)
        self.assertAlmostEqual(sigs[0]["fakey_low"], 101.0)

        # Verify FTMO XAUUSD Wednesday 3x swap math: Tue 2024-01-09 01:00 UTC -> Fri 2024-01-12 20:55 UTC
        # Crosses Tue 17:00 NY (1x), Wed 17:00 NY (3x), Thu 17:00 NY (1x) = 5x swap_long!
        t0 = int(datetime(2024, 1, 9, 1, 0, tzinfo=timezone.utc).timestamp())
        t1 = int(datetime(2024, 1, 12, 20, 55, tzinfo=timezone.utc).timestamp())
        xau_spec = {"swap_long": -56.56, "swap_short": -4.20, "point": 0.01, "trade_contract_size": 100.0, "swap_rollover3days": 3}
        sw, n_norm, n_trip = intel.compute_swap_usd_per_lot(t0, t1, 1, xau_spec)
        self.assertEqual(n_norm, 2)
        self.assertEqual(n_trip, 1)
        self.assertAlmostEqual(sw, -56.56 * 5.0, places=4)

    def test_track3_mc_null_determinism_and_holdout_year_guard(self):
        with self.assertRaises(ValueError):
            us500.load_explicit_year(Path("."), 2025)
        offsets = np.arange(386, dtype=np.int64)
        quotes = np.tile(np.array([4000.0, 4001.0, 3999.0, 4000.5, 4000.5, 4001.5, 3999.5, 4001.0]), (386, 1))
        sig = {"side": 1, "entry_idx": 70, "entry_price": 4000.5, "entry_spread": 0.5, "stop": 3995.0, "risk": 5.5}
        ev = [("2020-05-01", 1588339800, offsets, quotes, sig)]
        a = us500.mc_random_entry_null(ev, 0.75, draws=50, seed=12345)
        b = us500.mc_random_entry_null(ev, 0.75, draws=50, seed=12345)
        self.assertEqual(a, b)
        self.assertEqual(a["n_days"], 1)


if __name__ == "__main__":
    unittest.main()

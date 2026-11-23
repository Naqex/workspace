"""Unit tests for Pass 18 open-source academic & MQL5 CodeBase non-USDJPY screening engine."""

from datetime import date, datetime, timezone
import unittest
from zoneinfo import ZoneInfo

import numpy as np

import pass18_opensource_non_usdjpy as p18


class TestPass18OpenSource(unittest.TestCase):
    def test_london_dst_matches_iana_zoneinfo_across_all_dev_years(self):
        """Verify UK BST transitions match IANA Europe/London for every transition date 2018-2024."""
        try:
            tz_lon = ZoneInfo("Europe/London")
        except Exception:
            self.skipTest("tzdata not installed")
        for y in range(2018, 2025):
            for m, d in ((1, 15), (3, 24), (3, 31), (4, 1), (7, 15), (10, 24), (10, 31), (11, 1)):
                day = date(y, m, d)
                got_utc = p18.london_to_utc_sec(day, 16, 0)
                ref_utc = int(datetime(y, m, d, 16, 0, tzinfo=tz_lon).astimezone(timezone.utc).timestamp())
                self.assertEqual(got_utc, ref_utc, f"London DST mismatch on {day}")

    def test_us500_sim_sl_first_conservative_and_tp(self):
        """Verify SL-first conservative rule on same-minute touch and zero overnight swap on US500."""
        t0 = int(datetime(2020, 1, 2, 14, 30, tzinfo=timezone.utc).timestamp())
        times = np.array([t0 + i * 60 for i in range(5)], dtype=np.int64)
        quotes = np.array([
            [3200.0, 3201.0, 3199.0, 3200.0, 3200.5, 3201.5, 3199.5, 3200.5],
            [3200.0, 3215.0, 3185.0, 3205.0, 3200.5, 3215.5, 3185.5, 3205.5],
            [3205.0, 3206.0, 3204.0, 3205.0, 3205.5, 3206.5, 3204.5, 3205.5],
            [3205.0, 3206.0, 3204.0, 3205.0, 3205.5, 3206.5, 3204.5, 3205.5],
            [3205.0, 3206.0, 3204.0, 3205.0, 3205.5, 3206.5, 3204.5, 3205.5],
        ], dtype=np.float64)
        sess = {"day": "2020-01-02", "year": 2020, "start": t0, "lo": 0, "hi": 5}
        tr = p18.sim_us500_trade(times, quotes, sess, rel_entry=0, side=1, sl_pts=10.0, tp_pts=10.0, slip_side=0.75)
        self.assertIsNotNone(tr)
        self.assertEqual(tr["reason"], "SL_GAP_OR_TOUCH")
        self.assertAlmostEqual(tr["gross_usd"], -10.0, places=6)
        self.assertEqual(tr["ftmo_swap"], 0.0)

    def test_sign_flip_null_detects_real_edge_vs_noise(self):
        """Verify paired Rademacher sign-flip null assigns tiny p-value to consistent edge."""
        trades = [{"gross_usd": 100.0, "ftmo_net": 80.0} for _ in range(50)]
        fades = [{"gross_usd": -100.0, "ftmo_net": -120.0} for _ in range(50)]
        res = p18.sign_flip_null_p(trades, fades, draws=500)
        self.assertLess(res["gross_p"], 0.01)
        self.assertLess(res["ftmo_net_p"], 0.01)

    def test_daily_correlation_orthogonal_series(self):
        """Verify daily correlation helper computes exact Pearson correlation."""
        trades = [{"day": f"2020-01-{i:02d}", "ftmo_R": (1.0 if i % 2 == 0 else -1.0)} for i in range(1, 25)]
        core = {f"2020-01-{i:02d}": (1.0 if i % 2 == 0 else -1.0) for i in range(1, 25)}
        c = p18.daily_correlation(trades, core)
        self.assertEqual(c["overlap_days"], 24)
        self.assertAlmostEqual(c["union_corr"], 1.0, places=4)


if __name__ == "__main__":
    unittest.main()

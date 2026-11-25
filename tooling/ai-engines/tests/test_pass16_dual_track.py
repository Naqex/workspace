"""Unit & causality tests for Pass 16 dual-track screener (CCI20, Camarilla, wide expansion)."""

import sys
from pathlib import Path
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pass16_dual_track as p16


class Pass16DualTrackTests(unittest.TestCase):
    def test_cci20_causal_spike_exceeds_plus_100(self):
        n = 30
        h = np.full(n, 101.0)
        l = np.full(n, 99.0)
        c = np.full(n, 100.0)
        h[-1], l[-1], c[-1] = 115.0, 105.0, 114.0
        vals = p16.cci(h, l, c, 20)
        self.assertTrue(np.isnan(vals[18]))
        self.assertAlmostEqual(vals[19], 0.0, places=6)
        self.assertGreater(vals[-1], 100.0)


if __name__ == "__main__":
    unittest.main()

from pathlib import Path
import sys
import unittest
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from prop_v12_signals import adx14, rejection_recipes
from quant_core.market_data_store import BAR
from quant_core.ftmo_execution_and_calendar import gold_calendar
from prop_campaign_source import stamp
from quant_core.vectorized_stage0_scanner import HOUR, DAY


class RejectionTests(unittest.TestCase):
    def test_flat_market_adx_is_zero_after_warmup_and_no_lookahead(self):
        f = {k: np.full(60, 100.) for k in ("h", "l", "c")}
        a = adx14(f)
        self.assertTrue(np.isnan(a[:26]).all())
        np.testing.assert_array_equal(a[26:], 0.)
        f["h"][40:] += 100;f["c"][40:] += 50
        np.testing.assert_array_equal(adx14(f)[:40], a[:40])

    def test_five_asset_grid_is_six_recipes_and_future_bars_do_not_change_decisions(self):
        at = stamp("2022-01-03");n = 100*24
        rng = np.random.default_rng(620);close = 110000+np.cumsum(rng.integers(-20, 21, n))
        b = np.zeros(n, dtype=BAR);b["t"] = at+np.arange(n)*HOUR
        b["bo"] = np.r_[close[0], close[:-1]];b["bc"] = close
        b["bh"] = np.maximum(b["bo"], close)+100;b["bl"] = np.minimum(b["bo"], close)-100
        end = at+100*DAY;cutoff = at+70*DAY
        cal = gold_calendar(at, end)
        full = rejection_recipes(b, "GBPUSD", at, end, cal, native=True)
        prefix = rejection_recipes(b[:70*24], "GBPUSD", at, cutoff, cal, native=True)
        self.assertEqual(len(full), 6)
        self.assertGreater(sum(len(r["at"]) for r in full), 0)
        for a, p in zip(full, prefix):
            for key in ("at", "side", "stop"):
                np.testing.assert_array_equal(a[key][a["at"] < cutoff], p[key])
            self.assertEqual(len(np.unique(a["at"]//DAY)), len(a["at"]))

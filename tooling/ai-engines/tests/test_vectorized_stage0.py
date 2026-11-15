from pathlib import Path
import sys
import unittest
from fractions import Fraction as F
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from quant_core.vectorized_stage0_scanner import (
    HOUR, DAY, funding_multipliers, deadlines, endpoint_indices, economics, holm,
    daily_statistics, measure, summaries,
)
from quant_core.ftmo_execution_and_calendar import gold_calendar
from quant_core.market_data_store import BAR
from prop_campaign_source import stamp
from prop_v10_signals import catalog, recipes, rolling


class VectorTests(unittest.TestCase):
    def test_fixed_catalog_budget_and_no_side_variants(self):
        self.assertEqual(len(catalog("XAUUSD")), 92)
        self.assertEqual(len(catalog("EURUSD")), 44)
        self.assertEqual((92 + 44) * 4, 544)
        self.assertEqual(len({r["id"] for r in catalog("XAUUSD")}), 92)

    def test_wednesday_triple_rollover_entry_excluded_exit_included(self):
        first = stamp("2023-03-01T21:00")
        values = funding_multipliers(np.array([first, first+HOUR]),
                                     np.array([first+HOUR, first+25*HOUR]))
        self.assertEqual(values.tolist(), [3, 1])

    def test_gold_cost_units_both_directions_and_models(self):
        at = np.array([stamp("2023-03-01T21:00")] * 2)
        p0, px = np.array([1800000, 1800000]), np.array([1810000, 1790000])
        for model, swaps in (("SYM", [-1.2, -1.2]), ("ASYM", [-1.35, -.15])):
            r = economics("XAUUSD", np.array([1, -1]), p0, px, at, at+HOUR, model)
            np.testing.assert_allclose(r["gross"], [10, 10])
            np.testing.assert_allclose(r["funding"], swaps)
            self.assertAlmostEqual(r["net"][0], 10-.4-.0253+swaps[0])

    def test_eur_cost_does_not_reuse_gold_commission_or_units(self):
        at = np.array([stamp("2023-03-02T12:00")])
        r = economics("EURUSD", np.array([1]), np.array([110010]), np.array([110100]), at, at+HOUR, "SYM")
        self.assertAlmostEqual(r["net"][0] * 100000, 81)

    def test_day_and_week_clamp_to_early_close(self):
        first, end = stamp("2023-01-01"), stamp("2024-01-01")
        cal = gold_calendar(first, end)
        at = np.array([stamp("2023-11-24T09:00")])
        for h in ("DAY", "24H", "48H", "FRIDAY"):
            self.assertLess(deadlines(at, h, cal)[0], stamp("2023-11-24T20:30"))

    def test_endpoint_never_fills_unknown_or_reads_past_cutoff(self):
        bars = np.zeros(2, dtype=BAR)
        bars["t"] = [60000, 180000]
        _, ok = endpoint_indices(bars, np.array([0, 60001, 180000]), 180000)
        self.assertEqual(ok.tolist(), [True, False, False])

    def test_holm_known_example_and_monotonicity(self):
        np.testing.assert_allclose(holm([.01, .04, .03]), [.03, .06, .06])
        with self.assertRaises(ValueError):
            holm([float("nan")])

    def test_multiple_testing_filter_rejects_noise_and_tracks_trial_count(self):
        rng = np.random.default_rng(3)
        noise = rng.normal(0, 1, (8, 600))
        positive = np.r_[noise, np.full((1, 600), .3) + rng.normal(0, .2, (1, 600))]
        result = daily_statistics(positive, 544)
        # Holm correction must account for all registered trials, even if only a prefix is measured.
        self.assertEqual(result["trials"], 544)
        self.assertGreater(result["t_stat"][-1], 10)
        self.assertFalse(result["exact_DSR"])

    def test_rolling_levels_are_prior_only(self):
        a = np.array([1, 2, 100, 4], dtype=float)
        out = rolling(a, 2, "max")
        self.assertEqual(out[2], 2)
        self.assertEqual(out[3], 100)

    def test_nonempty_signal_prefix_is_unchanged_by_future_bars(self):
        first = stamp("2022-01-03")
        count = 80 * 24 * 60
        rng = np.random.default_rng(19)
        close = 1800000 + np.cumsum(rng.integers(-150, 151, count))
        bars = np.zeros(count, dtype=BAR)
        bars["t"] = first + np.arange(count) * 60000
        bars["bo"] = np.r_[close[0], close[:-1]]
        bars["bc"] = close
        bars["bh"] = np.maximum(bars["bo"], close) + 100
        bars["bl"] = np.minimum(bars["bo"], close) - 100
        end = first + 80 * DAY
        cal = gold_calendar(first, end)
        full = recipes(bars, "EURUSD", first, end, cal)
        cut = first + 60 * DAY
        prefix = recipes(bars[:60*24*60], "EURUSD", first, cut, cal)
        self.assertGreater(sum(len(r["at"]) for r in prefix), 0)
        for p, f in zip(prefix, full):
            for field in ("at", "side", "stop"):
                np.testing.assert_array_equal(p[field], f[field][f["at"] < cut])

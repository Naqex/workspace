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

    def test_terminal_event_keeps_numeric_stage_without_duplicate_keyword(self):
        from prop_v10_campaign import completion_event
        decision = dict(stage="STAGE0", eligible=[])
        out = completion_event(decision, 1.25)
        self.assertEqual(out["stage"], "STAGE0")
        self.assertEqual(out["event"], "V10_Discovery_complete")
        self.assertEqual(out["scan_seconds"], 1.25)
        self.assertEqual(decision, dict(stage="STAGE0", eligible=[]))

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

    def test_late_day_and_post_friday_flat_never_price_a_backward_or_weekend_trade(self):
        first, end = stamp("2023-01-01"), stamp("2024-01-01")
        times = [stamp(t) for t in ("2023-03-02T20:30", "2023-03-02T23:00",
                                   "2023-03-03T20:30", "2023-03-03T21:00",
                                   "2023-03-06T20:30", "2023-03-10T20:30")]
        bars = np.zeros(len(times), dtype=BAR)
        bars["t"] = times
        bars["bo"], bars["ao"] = 1800000, 1800338
        recipe = dict(id="late", family="F1",
                      at=np.array([times[1], times[3]]),
                      side=np.array([1, 1]), stop=np.array([1790000, 1790000]))
        rows = measure("XAUUSD", recipe, bars, gold_calendar(first,end), first,end)
        self.assertFalse(rows[0]["ok"].any())
        self.assertTrue(all(not r["ok"][1] for r in rows))

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

    def test_scale_gate_uses_pooled_cluster_medians_not_worst_year(self):
        years = np.repeat(np.arange(2018, 2024), [1, 5, 5, 1, 5, 5])
        at = np.array([stamp(f"{y}-01-02") for y in years])
        natural = np.where(np.isin(years, [2018, 2021]), 1., 10.)
        n = len(years)
        money = dict(net_R=np.ones(n), net=np.ones(n), gross=np.ones(n),
                     funding=np.zeros(n))
        m = dict(asset="XAUUSD", recipe="fixture", family="F1", horizon="DAY",
                 years=years, at=at, natural=natural, friction=np.ones(n),
                 ratio=1/natural, ok=np.ones(n, dtype=bool),
                 admitted=1/natural <= .15, model=dict(SYM=money, ASYM=money))
        out, _ = summaries([m], stamp("2018-01-01"), stamp("2024-01-01"), 544)
        self.assertEqual([c["scale_ratio"] for c in out[0]["clusters"]], [.1, .1])
        self.assertFalse(any("SCALE" in r for r in out[0]["reasons"]))

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

from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

import numpy as np

import pass5_usdjpy_tokyo as clock
import pass11_gbpusd_m1 as gbp
import pass11_portfolio as port
from pass10_institutional_flow import epoch


def quotes(bid=1.10000, ask=1.10010):
    return np.tile([bid] * 4 + [ask] * 4 + [bid + ask] * 4, (541, 1))


class M1TruthTests(TestCase):
    def test_qdm_rejects_holdout_before_price_admission(self):
        with TemporaryDirectory() as directory:
            file = Path(directory) / "quarantine.csv"
            file.write_text("DateTime,Bid,Ask,Volume\n20250101 00:00:00.000,1.20,1.21,1\n")
            with self.assertRaisesRegex(ValueError, "outside UTC year"):
                gbp.qdm.preflight(file, 2024)

    def test_tick_to_bid_ask_and_true_midpoint(self):
        with TemporaryDirectory() as directory:
            file = Path(directory) / "ticks.csv"
            file.write_text("DateTime,Bid,Ask,Volume\n"
                            "20240102 08:00:01.000,1.20010,1.20011,1\n"
                            "20240102 08:00:52.000,1.20000,1.20020,1\n"
                            "20240102 08:01:03.000,1.20000,1.20010,1\n")
            sealed = gbp.qdm.preflight(file, 2024)
            rows = gbp.aggregate(file, 2024, sealed)
            self.assertEqual(rows[:, 1].tolist(), [2, 1])
            self.assertEqual(rows[0, gbp.qdm.COLUMNS.index("mh2")], 240021)

    def test_executable_quote_and_same_minute_stop_are_conservative(self):
        offsets = np.arange(541)
        values = quotes()
        values[0, 9], values[0, 10] = 2.201, 2.199
        values[61, 5] = 1.10060
        values[61, 2] = 1.09900
        start = epoch(date(2024, 7, 1), 8, clock.LONDON)
        trade = gbp.execution(start, offsets, values)
        self.assertTrue(trade["dual_entry_minute"])
        self.assertEqual(trade["exit"].index, trade["entry_index"])
        first, times, marks = gbp.valued(trade, offsets, values, 0.)
        stress, _, _ = gbp.valued(trade, offsets, values, .00005)
        self.assertAlmostEqual(first["net_usd_per_lot"] - stress["net_usd_per_lot"], 5.)
        self.assertEqual(len(times), 1)
        self.assertAlmostEqual(marks[0, 0], first["net_usd_per_lot"])

    def test_sparse_group_excludes_barrier_and_boundary_cases(self):
        offsets = np.delete(np.arange(541), [90])
        values = quotes()[offsets]
        self.assertEqual(gbp.gap_classification(offsets, values, None)[0], "A_admitted")
        offsets = np.delete(np.arange(541), [60])
        self.assertEqual(gbp.gap_classification(offsets, quotes()[offsets], None)[0], "B")
        allowed = np.delete(np.arange(541), [90])
        data = quotes()[allowed]
        data[90, 0] += .00003
        self.assertEqual(gbp.gap_classification(allowed, data, None)[0], "B")

    def test_early_close_is_excluded_without_using_ending_price(self):
        offsets = np.arange(330)
        self.assertEqual(gbp.gap_classification(offsets, quotes()[offsets], None)[:2], ("B", 211))


class PortfolioTests(TestCase):
    def test_overlap_margin_drops_at_open_exit_and_preserves_pnl(self):
        times = np.array([0, 60, 120])
        jpy = port.SizedTrade({"at_open": True}, times, np.array([[0.,2.,-2.,0.],
                              [0.,3.,-4.,1.],[1.,1.,1.,1.]]), 1., 300., 1.)
        cable = port.SizedTrade({"at_open": False}, np.array([60, 120]),
                                np.array([[0.,2.,-3.,1.],[0.,0.,-2.,-2.]]), 1., 400., -2.)
        _, marks, margin, positions, gaps = port.combined_marks([jpy, cable])
        self.assertEqual(gaps, 0)
        self.assertEqual(margin.tolist(), [300.,700.,400.])
        self.assertEqual(positions.tolist(), [1,2,1])
        self.assertAlmostEqual(marks[1, 2], -7.)
        self.assertAlmostEqual(marks[-1, -1], -1.)

    def test_group_a_carries_last_mark_for_accounting_and_discloses_it(self):
        trade = port.SizedTrade({"at_open": True}, np.array([0,120]),
                                np.array([[0.,2.,-3.,1.],[-2.,-2.,-2.,-2.]]), 1., 300., -2.)
        _, marks, _, _, missing = port.combined_marks([trade])
        self.assertEqual(missing, 1)
        self.assertTrue(np.array_equal(marks[1], [1.,1.,1.,1.]))

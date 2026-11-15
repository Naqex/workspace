from pathlib import Path
import sys
import unittest
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from quant_core.market_data_store import BAR
from quant_core.vectorized_sl_active_kernel import PathIndex, replay, money, net_level, daily_mtm
from prop_campaign_source import stamp
from quant_core.vectorized_stage0_scanner import HOUR, DAY


def fixture(values, step=60000):
    b = np.zeros(len(values), dtype=BAR)
    at = stamp("2023-03-06T10:00")
    b["t"] = at + np.arange(len(b))*step
    for i, (o, h, l, c) in enumerate(values):
        for f, v in zip(("o", "h", "l", "c"), (o, h, l, c)):
            b["b"+f][i] = int(v*1000)
            b["a"+f][i] = int(v*1000)+100
    m = dict(at=np.array([at]), entry_at=np.array([at]), deadline=np.array([b["t"][-1]]),
             side=np.array([1]), entry_price=np.array([b["ao"][0]]), stop=np.array([90000]),
             natural=np.array([10.1]), admitted=np.array([True]))
    return b, m


class SLKernelTests(unittest.TestCase):
    def test_block_first_passage_matches_scalar_across_partial_blocks_and_sides(self):
        rng = np.random.default_rng(102)
        b = np.zeros(1027, dtype=BAR);b["t"] = stamp("2023-03-06")+np.arange(len(b))*60000
        for f in ("bh", "bl", "ah", "al"):
            b[f] = rng.integers(10, 1000, len(b))
        index = PathIndex(b, asset="US500")
        starts = rng.integers(0, len(b)-1, 400);ends = rng.integers(starts+1, len(b)+1)
        side = rng.choice([-1, 1], 400);level = rng.integers(10, 1000, 400)
        for favorable in (False, True):
            got = index.first(starts, ends, level, side=side, favorable=favorable)
            expected = []
            for lo, hi, s, p in zip(starts, ends, side, level):
                field = ("bh" if s == 1 else "al") if favorable else ("bl" if s == 1 else "ah")
                up = (favorable and s == 1) or (not favorable and s == -1)
                expected.append(next((j for j in range(lo, hi)
                    if (b[field][j] >= p if up else b[field][j] <= p)), hi))
            np.testing.assert_array_equal(got, expected)

    def test_gap_through_stop_is_not_artificially_capped_at_minus_one_R(self):
        b, m = fixture([(100, 101, 99, 100), (87, 90, 85, 88), (88, 89, 87, 88)])
        r = replay(PathIndex(b, asset="XAUUSD"), m, "P0")
        self.assertTrue(r["valid"][0]);self.assertEqual(r["exit_price"][0], 87000)
        self.assertLess(r["model"]["SYM"]["net_R"][0], -1)

    def test_stop_wins_same_bar_tp_and_stop_extremes(self):
        b, m = fixture([(100, 150, 80, 110), (110, 111, 109, 110)])
        r = replay(PathIndex(b, asset="XAUUSD"), m, "P2")
        self.assertEqual(r["reason"][0], "SL")
        self.assertEqual(r["exit_price"][0], 90000)

    def test_short_stop_uses_ask_extreme(self):
        b, m = fixture([(100, 100, 99, 99.5), (99, 109.95, 98, 100), (100, 101, 99, 100)])
        m.update(side=np.array([-1]), entry_price=np.array([100000]), stop=np.array([110000]),
                 natural=np.array([10.]))
        r = replay(PathIndex(b, asset="XAUUSD"), m, "P0")
        self.assertEqual(r["reason"][0], "SL")

    def test_P1_is_activated_after_bar_and_cannot_override_same_bar_old_stop(self):
        b, m = fixture([(100, 120, 85, 100), (100, 101, 98, 99), (99, 100, 98, 99)])
        r = replay(PathIndex(b, asset="XAUUSD"), m, "P1")
        self.assertEqual(r["reason"][0], "SL");self.assertEqual(r["activation_index"][0], -1)

    def test_P1_protection_includes_current_cost_and_starts_next_bar(self):
        b, m = fixture([(100, 120, 99, 118), (118, 119, 101, 102), (102, 103, 101, 102)])
        r = replay(PathIndex(b, asset="XAUUSD"), m, "P1")
        self.assertEqual(r["reason"][0], "PROTECT")
        self.assertEqual(r["activation_index"][0], 0)
        self.assertGreaterEqual(r["model"]["SYM"]["net_R"][0], .15)

    def test_horizon_open_does_not_read_future_extrema(self):
        b, m = fixture([(100, 101, 99, 100), (100, 150, 50, 100)])
        r = replay(PathIndex(b, asset="XAUUSD"), m, "P0")
        self.assertEqual(r["reason"][0], "HORIZON")

    def test_partial_hour_after_deadline_cannot_supply_a_stop(self):
        b, m = fixture([(100, 101, 99, 100), (100, 101, 80, 100), (100, 101, 99, 100)], HOUR)
        m["deadline"] = m["entry_at"]+int(1.5*HOUR)
        r = replay(PathIndex(b, asset="GBPUSD", step=HOUR), m, "P0")
        self.assertFalse(r["valid"][0]);self.assertEqual(r["reason"][0], "HORIZON")

    def test_missing_endpoint_can_be_resolved_by_an_earlier_observed_stop(self):
        b, m = fixture([(100, 101, 89, 90), (90, 91, 89, 90)], HOUR)
        m["deadline"] = m["entry_at"]+int(1.5*HOUR)
        r = replay(PathIndex(b, asset="GBPUSD", step=HOUR), m, "P0")
        self.assertTrue(r["valid"][0]);self.assertEqual(r["reason"][0], "SL")

    def test_unexpected_missing_path_is_unknown_not_a_zero_return(self):
        b, m = fixture([(100, 101, 99, 100), (100, 101, 99, 100), (100, 101, 99, 100)])
        b["t"][1:] += 60000;m["deadline"] = b["t"][-1:]
        r = replay(PathIndex(b, asset="EURUSD"), m, "P0")
        self.assertFalse(r["valid"][0]);self.assertTrue(r["path_gap"][0])

    def test_swap_uses_actual_exit_and_limit_avoids_negative_exit_slip(self):
        at = np.array([stamp("2023-03-08T21:00")]);p = np.array([1900000])
        late = money("XAUUSD", "ASYM", np.array([1]), p, p, at, at+2*HOUR, np.array(["TP"]))
        early = money("XAUUSD", "ASYM", np.array([1]), p, p, at, at+HOUR//2, np.array(["SL"]))
        self.assertAlmostEqual(late["funding"][0], -1.35)
        self.assertEqual(early["funding"][0], 0)
        self.assertAlmostEqual(late["slippage"][0], .2)
        self.assertAlmostEqual(early["slippage"][0], .4)

    def test_daily_mtm_sums_to_realized_net_R(self):
        b, m = fixture([(100, 101, 99, 100)]*3)
        index = PathIndex(b, asset="XAUUSD");r = replay(index, m, "P0")
        days = np.arange(m["entry_at"][0]//DAY, m["entry_at"][0]//DAY+2)
        profile = daily_mtm(index, m, r, "SYM", days)
        self.assertAlmostEqual(profile.sum(), r["model"]["SYM"]["net_R"][0])


if __name__ == "__main__":
    unittest.main()

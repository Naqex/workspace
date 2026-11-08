import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from index_tick_review import decode, first_quote, inspect, minute_ohlc, HOUR, HOLDOUT_START, MAX_SAFE


def fixture():
    raw = dict(timestamp=0, multiplier=.001, bid=100, ask=100.002,
               times=[0, 0, 120000, HOUR-120000], bids=[0, 1, -2, 0],
               asks=[0, 1, -2, 0], bidVolumes=[1000000, 0, 2500000, 1],
               askVolumes=[2000000, 500000, 0, 1])
    rows = [dict(timestamp=t, bidPrice=b, askPrice=a, bidVolume=bv, askVolume=av)
            for t, b, a, bv, av in [(0, 100, 100.002, 1, 2), (0, 100.001, 100.003, 0, .5),
                                     (120000, 99.999, 100.001, 2.5, 0)]]
    return raw, rows


class IndexTickReviewTests(unittest.TestCase):
    def test_equal_stamps_keep_order_missing_minutes_and_end_boundary(self):
        raw, rows = fixture()
        ticks = inspect(rows, raw, start_msc=0, end_msc=HOUR)
        self.assertEqual(list(ticks.timestamps), [0, 0, 120000])
        self.assertEqual(list(ticks.bid_units), [100000, 100001, 99999])
        bars = minute_ohlc(ticks)
        self.assertEqual(set(bars), {0, 120000})
        self.assertEqual(bars[0]['bid'], dict(open=100000, high=100001, low=100000, close=100001))
        self.assertEqual(bars[0]['ask']['close'], 100003)
        self.assertEqual(first_quote(ticks, 0)['source_ordinal'], 0)
        self.assertEqual(first_quote(ticks, 1)['wait_ms'], 119999)
        self.assertEqual(first_quote(ticks, 120000)['bid_volume_millions'], 2.5)
        self.assertIsNone(first_quote(ticks, 120001))
        for at in [-1, HOUR, True, .5]:
            with self.subTest(at=at), self.assertRaises(ValueError): first_quote(ticks, at)

    def test_empty_source_stays_empty_and_cannot_explain_native_rows(self):
        raw, rows = fixture()
        for key in ['times', 'bids', 'asks', 'bidVolumes', 'askVolumes']: raw[key] = []
        ticks = inspect([], raw, start_msc=0, end_msc=HOUR)
        self.assertEqual(minute_ohlc(ticks), {})
        self.assertIsNone(first_quote(ticks, 0))
        with self.assertRaises(ValueError): inspect(rows, raw, start_msc=0, end_msc=HOUR)

    def test_raw_schema_grid_integer_spread_volume_and_overflow_rejected(self):
        raw, _ = fixture()
        cases = [dict(times=[0]), dict(times=[0, -1, 1, 1]), dict(times=[0, .5, 1, 1]),
                 dict(times=[True, 1, 1, 1]), dict(times=[MAX_SAFE+1, 0, 0, 0]),
                 dict(timestamp=True), dict(multiplier='.001'), dict(multiplier=.01),
                 dict(bid=100.00001), dict(ask=99), dict(bids=[0, -100001, 0, 0]),
                 dict(bids=[0, 1, 2, True]), dict(bids=[MAX_SAFE, 0, 0, 0]),
                 dict(askVolumes=[0, float('nan'), 0, 0]), dict(bidVolumes=[0, -1, 0, 0]),
                 dict(bidVolumes=[True, 0, 0, 0]), dict(askVolumes=[0, '1', 0, 0]),
                 dict(askVolumes=[0, 10**400, 0, 0]), dict(times=None)]
        for change in cases:
            with self.subTest(change=change), self.assertRaises(ValueError):
                decode(dict(raw, **change), start_msc=0, end_msc=HOUR)
        for payload in [None, [], {k: v for k, v in raw.items() if k != 'asks'}]:
            with self.subTest(payload=type(payload)), self.assertRaises(ValueError):
                decode(payload, start_msc=0, end_msc=HOUR)

    def test_window_alignment_and_holdout_closed(self):
        raw, _ = fixture()
        for lo, hi in [(0, 1), (1, HOUR+1), (-HOUR, 0), (True, HOUR),
                       (0, float(HOUR)), (HOLDOUT_START, HOLDOUT_START+HOUR)]:
            with self.subTest(lo=lo), self.assertRaises(ValueError): decode(raw, start_msc=lo, end_msc=hi)
        raw['timestamp'] = HOUR
        with self.assertRaises(ValueError): decode(raw, start_msc=0, end_msc=HOUR)

    def test_all_native_fields_order_and_census_bound(self):
        raw, rows = fixture()
        for key, value in [('timestamp', 1), ('timestamp', True), ('bidPrice', 100.00000000000001),
                           ('bidPrice', True), ('askPrice', 100.004), ('bidVolume', 0),
                           ('askVolume', float('inf')), ('askVolume', -1)]:
            changed = copy.deepcopy(rows); changed[0][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                inspect(changed, raw, start_msc=0, end_msc=HOUR)
        for changed in [rows[::-1], rows[:2], {}, [None]*3,
                        [{k: v for k, v in row.items() if k != 'askPrice'} for row in rows]]:
            with self.subTest(changed=type(changed)), self.assertRaises(ValueError):
                inspect(changed, raw, start_msc=0, end_msc=HOUR)

    def test_raw_base_binary_noise_normalizes_but_native_prices_do_not(self):
        raw, rows = fixture(); raw['bid'] = 100.00000000000001
        self.assertEqual(len(inspect(rows, raw, start_msc=0, end_msc=HOUR)), 3)


if __name__ == '__main__': unittest.main()

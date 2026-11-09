from decimal import Decimal as D
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from h4_sma_signal_oracle import H4, completed_h4, indicator_trace, review_decisions, signal


class SmaOracleTests(unittest.TestCase):
    def test_exact_cross_and_held_exit_at_equality(self):
        self.assertEqual(signal(0, 1, None), 'BUY')
        self.assertEqual(signal(0, -1, None), 'SELL')
        self.assertIsNone(signal(None, 1, None))
        self.assertIsNone(signal(-1, 0, None))
        self.assertEqual(signal(1, 0, 'BUY'), 'EXIT')
        self.assertEqual(signal(-1, 0, 'SELL'), 'EXIT')
        self.assertIsNone(signal(-1, 1, 'BUY'))

    def test_seed_and_first_wilder_update_are_hand_calculable(self):
        bars = [(i*H4, (1000, 1010, 990, 1000)) for i in range(14)]
        trace = indicator_trace(bars+[(14*H4, (1000, 1024, 990, 1000))])
        self.assertIsNone(trace[12]['distance'])
        self.assertEqual(trace[13]['distance'], D('.04'))
        self.assertLess(abs(trace[14]['distance']-D('.042')), D('1e-75'))

    def test_warmup_constant_shift_and_future_invariance(self):
        bars = [(i*H4, (1000+i, 1010+i, 990+i, 1000+i)) for i in range(81)]
        trace = indicator_trace(bars)
        self.assertIsNone(trace[78]['difference'])
        self.assertEqual(trace[79]['difference'], 2400)
        shifted = [(at, tuple(p+250 for p in prices)) for at, prices in bars]
        self.assertEqual(trace, indicator_trace(shifted))
        self.assertEqual(trace, indicator_trace(bars+[(81*H4, (2000, 3000, 1000, 2000))])[:81])

    def test_missing_hour_is_excluded_without_padding(self):
        hours = [(i*3600, (1000, 1010, 990, 1000+i)) for i in [0, 1, 3, 4, 5, 6, 7]]
        bars, excluded = completed_h4(hours)
        self.assertEqual(excluded, [0])
        self.assertEqual(bars, [(H4, (1000, 1010, 990, 1007))])
        with self.assertRaises(ValueError):
            completed_h4(hours+hours)

    def test_complete_decision_census_and_mutations(self):
        trace = [dict(at=0, difference=-1, distance=D('1')),
                 dict(at=H4, difference=1, distance=D('1')),
                 dict(at=2*H4, difference=1, distance=D('1'))]
        actual = [dict(time_msc=2*H4*1000, signal='BUY', stop_distance='1', quantity='0.99', status='queued')]
        kwargs = dict(start=H4, end=3*H4, slippage=D('.1'))
        sides = {H4: None, 2*H4: 'BUY'}
        self.assertEqual(review_decisions(trace, sides, actual, **kwargs), dict(decisions=1, bars=2, no_signal=1))
        for key, value in [('time_msc', 1), ('signal', 'SELL'), ('stop_distance', '1.1'), ('quantity', '1')]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                review_decisions(trace, sides, [{**actual[0], key: value}], **kwargs)
        for rows in [[], actual+actual]:
            with self.assertRaises(ValueError):
                review_decisions(trace, sides, rows, **kwargs)


if __name__ == '__main__':
    unittest.main()

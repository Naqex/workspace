from pathlib import Path
import sys
import unittest
from decimal import Decimal as D

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from quote_bar_oracle import aggregate_ticks,require_contains_quotes,require_exact_ohlc


class QuoteBarOracleTests(unittest.TestCase):
    def ticks(self):
        return [dict(timestamp=t,bidPrice=b,askPrice=a) for t,b,a in
                [(1000,3689.768,3690.287),(2000,3690.306,3690.787),
                 (3000,3685.530,3686.068),(4000,3688.260,3688.734)]]

    def test_exact_side_ohlc_and_larger_bar_containment(self):
        derived=aggregate_ticks(self.ticks(),start_msc=1000,end_msc=5000,price_grid='.001')
        self.assertEqual(derived['bid']['low'],D('3685.530'))
        require_exact_ohlc(dict(open=3689.768,high=3690.306,low=3685.53,close=3688.26),derived['bid'])
        require_contains_quotes(dict(low=3680,high=3700),derived['ask'])

    def test_real_failure_shape_rejects_daily_low_above_observed_minute_quotes(self):
        derived=aggregate_ticks(self.ticks(),start_msc=1000,end_msc=5000,price_grid='.001')
        for side,low in [('bid',3692),('ask',3692.095)]:
            with self.subTest(side=side),self.assertRaisesRegex(ValueError,'excludes_observed'):
                require_contains_quotes(dict(low=low,high=3750),derived[side])

    def test_unsorted_scope_grid_or_crossed_quotes_are_not_repaired(self):
        cases=[list(reversed(self.ticks())),self.ticks()+[dict(timestamp=5000,bidPrice=1,askPrice=2)],
               [dict(timestamp=1000,bidPrice=2,askPrice=1)],
               [dict(timestamp=1000,bidPrice=1.0005,askPrice=2)]]
        for ticks in cases:
            with self.subTest(ticks=ticks),self.assertRaises(ValueError):
                aggregate_ticks(ticks,start_msc=1000,end_msc=5000,price_grid='.001')


if __name__=='__main__':unittest.main()

"""Quote-unit PnL retains sub-cent precision; account money rounds separately."""
from decimal import Decimal as D
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_nasdaq_overnight_reversal_component import fixture, evaluate
import nasdaq_h4_study as market


class OvernightCostRoundingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        market.bind_core(Path(__file__).resolve().parents[3]/'projects/trader/foundation_v2')

    def test_subcent_quote_pnl_and_account_money_have_different_units(self):
        for gap, gross, money, net in ((10, '4.803', '4.80', '4.30'), (-10, '4.797', '4.80', '4.30')):
            case = fixture(gap=gap)
            for row in case[1][case[2][2]]:
                row['open'] = str(D(row['open'])+D('.003'))
            costs = evaluate(case)['outcomes']['reference']['primary']['costs']
            self.assertEqual(D(str(costs['gross_quote'])), D(gross))
            self.assertEqual(D(str(costs['gross_account'])), D(money))
            self.assertEqual(D(str(costs['net_account'])), D(net))


if __name__ == '__main__':
    unittest.main()

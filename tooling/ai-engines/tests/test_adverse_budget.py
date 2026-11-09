from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from forex_screen_diagnostics import adverse_budget


class AdverseBudgetTests(unittest.TestCase):
    def test_positive_and_negative_net_share_same_explicit_loss_pool(self):
        for gains, net in (('150','50'),('50','-50')):
            got=adverse_budget(dict(price_losses='70',spread='10',funding='20'),dict(price_wins=gains),net=net)
            self.assertEqual(got['total_adverse_usd'],'100')
            self.assertEqual(got['percent_of_adverse_pool'],dict(price_losses='70.00',spread='10.00',funding='20.00'))
            self.assertFalse(got['causal_attribution_proven'])

    def test_no_adverse_flows_is_na_instead_of_dividing_by_net(self):
        got=adverse_budget(dict(cost='0'),dict(gain='10'),net='10')
        self.assertIsNone(got['percent_of_adverse_pool']['cost'])

    def test_credit_and_rounding_are_explicit_and_reconcile(self):
        got=adverse_budget(dict(trade_loss='1.005',fees='.005'),dict(price_win='2',swap_credit='.02'),net='1.01')
        self.assertEqual(got['total_adverse_usd'],'1.010')
        self.assertEqual(got['percent_of_adverse_pool']['fees'],'0.50')

    def test_mismatch_doublecount_unknown_and_invalid_amounts_rejected(self):
        for debits,credits,net in ((dict(price_loss='100',spread='10'),dict(win='50'),'-50'),
                                  (dict(fee='-1'),dict(win='1'),'2'),
                                  (dict(fee='NaN'),dict(win='1'),'0'),
                                  (dict(fee=None),dict(win='1'),'0'),
                                  (dict(same='1'),dict(same='2'),'1')):
            with self.subTest(debits=debits),self.assertRaises(ValueError):
                adverse_budget(debits,credits,net=net)


if __name__=='__main__':unittest.main()

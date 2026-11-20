from pathlib import Path
from unittest.mock import patch
import unittest

import pass5_usdjpy_tokyo as shared
from pass6_breakout_execution import (SL, entries, explicit_packet, gold_columns,
    gold_mark, jpy_mark, stop_price, value_stop, win_flip)


class Pass6ExecutionTests(unittest.TestCase):
    def test_stop_uses_bid_for_long_and_ask_for_short(self):
        bid=shared.Bar(149.90,150.10,149.80,150.02)
        ask=shared.Bar(149.92,150.12,149.82,150.04)
        self.assertEqual(stop_price(bid,ask,1,149.95),149.90)
        self.assertEqual(stop_price(bid,ask,-1,150.11),150.11)
        self.assertEqual(stop_price(bid,ask,1,149.95,entry_bar=True),149.95)
        self.assertEqual(list(entries(bid,ask,150.11,149.85)),[(1,150.11,149.85),(-1,149.85,150.11)])

    def test_same_entry_bar_loss_excludes_open_before_fill_and_extra_slippage(self):
        day=shared.START
        at=day+3*3600
        bid=shared.Bar(149.80,150.20,149.70,150.01)
        ask=shared.Bar(149.803,150.203,149.703,150.013)
        setup=(1,150.,149.90)
        row=value_stop(day,at,at+3600,3600,setup,lambda _: (bid,ask),jpy_mark,.01)
        self.assertEqual(row['reason'],SL)
        self.assertTrue(row['entry_bar_forced_stop'])
        self.assertEqual(row['mfe_R'],0.)
        self.assertLess(row['net_R'],-1.)
        expected=-(.10+.004+.01)*100000/149.9015-5
        self.assertAlmostEqual(row['net_R']*row['initial_risk_usd'],expected)

    def test_gold_charges_two_notional_commissions_and_each_side_once(self):
        row=gold_mark(1,2000.,2002.,.175,.175)
        self.assertAlmostEqual(row['gross'],200.)
        self.assertAlmostEqual(row['spread'],35.)
        self.assertAlmostEqual(row['commission'],.000007*4002*100)
        self.assertAlmostEqual(row['slippage'],40.)
        self.assertAlmostEqual(row['net'],200-35-40-.000007*4002*100)

    def test_holdout_jpy_packet_rejected_before_file_open(self):
        with patch('pass6_breakout_execution.base.sha') as digest:
            with self.assertRaisesRegex(ValueError,'outside Development'):
                explicit_packet(Path('2025-01-01.json'),'never_read',shared.STOP)
            digest.assert_not_called()

    def test_unregistered_gold_manifest_rejected_before_columns(self):
        with patch('pass6_breakout_execution.base.sha',return_value='unregistered'):
            with patch('pass6_breakout_execution.np.memmap') as market_data:
                with self.assertRaisesRegex(ValueError,'Unregistered Gold'):
                    gold_columns(Path('.'))
                market_data.assert_not_called()

    def test_original_winner_flip_counts_missing_separately(self):
        rows=[dict(day='a',net_R=1),dict(day='b',net_R=-1),dict(day='d',net_R=0)]
        self.assertEqual(win_flip(rows,['a','b','c','d']),dict(win=1,loss=1,missing=1,flat=1))

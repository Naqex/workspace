import unittest
from datetime import date, datetime, timezone

from pass9_bot_round2 import (SnapshotConversion, costs, out_of_scope, paired_returns,
                             pnl_summary, private_rows, stop_risk)
from quant_core.ftmo_track_replay import profiles
from quant_core.live_trade_log import Trade, normalize


def ms(value):
    return int(datetime.fromisoformat(value).replace(tzinfo=timezone.utc).timestamp()*1000)


class Round2Tests(unittest.TestCase):
    def sample(self, **kw):
        o=ms('2024-06-05T20:00:00')
        c=ms('2024-06-05T22:00:00')
        fields=dict(row=1,symbol='EURUSD',direction='BUY',lots=.10,open_price=1.1,
                    close_price=1.102,sl=1.099,open_date='2024-06-05',close_date='2024-06-05',
                    open_time=o,close_time=c,open_wall_ms=o,close_wall_ms=c,profit=20.,
                    profit_currency='EUR')
        return Trade(**(fields|kw))

    def test_euro_cash_proxy_is_converted_to_same_currency_as_stop_risk(self):
        specs={'EURUSD':{'trade_contract_size':100000,'currency_profit':'USD','bid':1.1,'ask':1.1}}
        t=self.sample(profit=-20.)
        cov=pnl_summary([t],specs)
        risk=stop_risk(t,specs,SnapshotConversion(specs))
        self.assertAlmostEqual(risk,10.)
        self.assertAlmostEqual(cov['display_sl_R_dd_proxy']['peak_to_valley'],2.204)
        self.assertIsNone(cov['true_initial_R_dd'])

    def test_triple_swap_and_repeatable_commission_from_sealed_profile(self):
        spec=profiles()[0]['Swing']
        t=self.sample()
        result=costs([t],spec,'Swing')
        tot=result['totals']
        self.assertEqual(result['n'],1)
        self.assertEqual(tot['triple_rollovers'],1)
        self.assertAlmostEqual(tot['commission'],.5)
        self.assertAlmostEqual(tot['swap'],spec['EURUSD']['swap_long']*spec['EURUSD']['point']*30000)
        self.assertAlmostEqual(tot['net_stress'],tot['gross']-tot['commission']+tot['swap']-tot['stress_slippage'])
        off=costs([self.sample(symbol='AUDCAD')],spec,'Swing')
        self.assertEqual(off['missing'],{'OUT_OF_FTMO_13_UNIVERSE':1})
        self.assertIsNone(off['totals'])

    def test_positions_no_sl_columns_leave_exit_unknown(self):
        blob=b'Time;Type;Volume;Symbol;Price;Volume;Time;Price;Commission;Swap;Profit\n2026.11.11 01:00:00;Buy;0.01;EURUSD;1.1;0.01;2026.11.11 02:00:00;1.2;-0.05;;100\n'
        trades,meta=normalize(blob,'.csv')
        self.assertEqual(meta['accepted'],1)
        s=private_rows(blob,trades,profiles()[0]['Swing'])
        self.assertEqual(s['exit_labels'],{'UNKNOWN_EXIT_NO_STOP_TARGET_EVIDENCE':1})

    def test_out_of_universe_does_not_alias_futures_to_cfd(self):
        self.assertTrue(out_of_scope('AUDCAD').startswith('CFD_FX_LISTED'))
        self.assertIn('SEPARATE_FTMO_FUTURES',out_of_scope('NQ_Z'))
        self.assertIn('CONTRACT_NOT_VERIFIED',out_of_scope('ZC_K'))

    def test_correlation_does_not_include_nonoverlap_ranges(self):
        a={date(2025,1,i):x for i,x in [(1,-100),(2,0),(3,2),(4,1)]}
        b={date(2025,1,i):x for i,x in [(2,0),(3,4),(5,900)]}
        result=paired_returns(a,b,date(2025,1,2),date(2025,1,4))
        self.assertEqual(result['both_active'],{'n':2,'pearson':1.})
        self.assertEqual(result['union_active']['n'],3)

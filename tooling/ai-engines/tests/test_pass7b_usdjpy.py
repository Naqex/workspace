import tempfile
import unittest
from pathlib import Path

import numpy as np
import pyarrow as pa

import pass5_usdjpy_tokyo as base
import pass7b_qdm_m1 as qdm
import pass7b_usdjpy_equity as audit
from pass6_breakout_execution import jpy_mark, value_stop
from pass7b_usdjpy_research import verdict


class QdmM1Tests(unittest.TestCase):
    def test_timestamp_fence_before_price_parse_and_no_cross_year(self):
        with tempfile.TemporaryDirectory() as temp:
            f=Path(temp)/'tick.csv'
            f.write_text('DateTime,Bid,Ask,Volume\n20241231 23:59:59.999,x,x,1\n'
                         '20250101 00:00:00.000,x,x,1\n',encoding='ascii')
            with self.assertRaisesRegex(ValueError,'clock outside'):
                qdm.preflight(f,2024)
        with self.assertRaisesRegex(ValueError,'registered Development'):
            qdm.year_limits(2025)

    def test_actual_mid_extrema_and_chunk_rollover(self):
        with tempfile.TemporaryDirectory() as temp:
            f=Path(temp)/'tick.csv'
            f.write_text('DateTime,Bid,Ask,Volume\n'
                         '20180102 00:00:00.033,100.000,100.012,1\n'
                         '20180102 00:00:59.033,100.005,100.007,1\n'
                         '20180102 00:01:00.033,100.004,100.005,1\n',encoding='ascii')
            receipt=qdm.preflight(f,2018)
            rows,hist=qdm.aggregate(f,2018,receipt)
        self.assertEqual(receipt['rows'],3)
        self.assertEqual(rows[:,1].tolist(),[2,1])
        self.assertEqual(rows[0,11],200012)  # true mid high; separate side highs sum to 200017
        self.assertEqual(qdm.spread_stats(hist['Tokyo'])['p95_pips'],1.2)

    def test_same_timestamp_ordinals_are_retained_but_reversal_rejected(self):
        same=pa.array(['20230201 03:45:13.025','20230201 03:45:13.025'])
        self.assertEqual(np.diff(qdm.timestamp_ms(same,2023)).tolist(),[0])
        bad=pa.array(['20230201 03:45:13.026','20230201 03:45:13.025'])
        with self.assertRaisesRegex(ValueError,'out of order'):
            qdm.timestamp_ms(bad,2023)


class EquityTests(unittest.TestCase):
    def market(self):
        quote=np.tile([100.,100.03,99.97,100.,100.01,100.04,99.98,100.01],(901,1))
        quote[:180]=[100.,100.05,99.95,100.,100.01,100.06,99.96,100.01]
        quote[180]=[100.03,100.07,100.02,100.05,100.04,100.08,100.03,100.06]
        return quote

    def test_reuses_pass6_for_realized_pnl_and_adds_entry_stress_once(self):
        q=self.market()
        q[181]=[99.8,100.05,99.79,99.95,99.81,100.06,99.8,99.96]
        trade, _=audit.select(base.START,q)
        self.assertEqual(trade.execution.reason,audit.SL)
        self.assertEqual(trade.execution.price,99.8)
        self.assertTrue(trade.execution.at_open)
        quote=lambda t: (base.Bar(*q[(t-base.START)//60,:4]),base.Bar(*q[(t-base.START)//60,4:]))
        for extra in audit.PROFILE.values():
            row=audit.record(trade,extra)
            old=value_stop(base.START,trade.entry_second,base.START+900*60,60,
                (trade.side,trade.entry_price,trade.edge),quote,jpy_mark,extra)
            self.assertAlmostEqual(row['net_usd_per_lot'],old['net_R']*old['initial_risk_usd'])
            self.assertAlmostEqual(audit.path(trade,extra)[-1,3],row['net_usd_per_lot'])
            self.assertEqual(row['exit'],old['exit'])

    def test_dual_touch_is_counted_and_prefers_base_worst_with_same_minute_stop(self):
        q=self.market()
        q[180]=[100.03,100.09,99.90,100.05,100.04,100.10,99.91,100.06]
        trade,dual=audit.select(base.START,q)
        self.assertEqual(dual,1)
        record=audit.record(trade,0.)
        self.assertTrue(record['entry_bar_forced_stop'])
        self.assertTrue(record['dual_entry'])
        self.assertEqual(len(audit.path(trade,0.)),1)

    def test_equity_accounts_prague_loss_lot_rounding_and_margin(self):
        spec=audit.Account('10k',10000,3333.33,.01,.01,50)
        self.assertEqual(audit.floor_lot(20,83,spec),.24)
        trade, _ = audit.select(base.START,self.market())
        row=audit.record(trade,0.)
        curve=audit.path(trade,0.)
        data, ledger=audit.account_replay(spec,.002,[row],[curve],[base.START//base.DAY])
        self.assertEqual(data['executed'],1)
        self.assertLessEqual(ledger[0]['usable_risk_usd'],20.)
        self.assertAlmostEqual(data['worst_daily_loss_pct'],max(0.,-curve.min()*ledger[0]['lots']/100))
        self.assertAlmostEqual(data['net_usd'],ledger[0]['net_usd'])
        self.assertEqual(audit.prague_day(base.START-1800).isoformat(),'2018-01-01')
        limited=audit.Account('10k',10000,1e7,.01,.01,50)
        data,_=audit.account_replay(limited,.002,[row],[curve],[base.START//base.DAY])
        self.assertEqual(data['skip'],{'initial_margin':1})

    def test_drawdown_underwater_recovery_and_economic_gate(self):
        days=np.arange(base.START//base.DAY,base.START//base.DAY+4)
        metric=audit.EquityMetrics(100.,base.START,days)
        ts=np.array([base.START,base.START+60,base.START+base.DAY,base.START+2*base.DAY])
        metric.add(ts,np.array([100.,98.,94.,101.]),100.)
        self.assertEqual(metric.dd,6.)
        self.assertEqual(metric.daily,6.)
        self.assertEqual(metric.max_age,(2*base.DAY,2))
        self.assertEqual(verdict([],range(84),{'n':7,'clusters':{'A':1,'B':-1}}),
                         'FAILED_FULL_M1_TRUTH_CHECK')
        self.assertEqual(verdict([],range(80),{'n':7,'clusters':{'A':1,'B':1}}),
                         'INCONCLUSIVE_M1_COVERAGE')

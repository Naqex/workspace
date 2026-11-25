import unittest
from datetime import datetime, timezone

import numpy as np

import pass5_usdjpy_tokyo as base
import pass7b_usdjpy_equity as equity
import pass8_mql5_public as mql
import pass8_usdjpy_gaps as gaps


class PublicGateTests(unittest.TestCase):
    def record(self):
        return dict(access='public_statistics',monitor_days=364,detail_trades=150,detail_algo=80,
                    last_trade_days=30,balance_relative_dd=10.,equity_relative_dd=15.,
                    maximal_cash_dd_pct=20.,real_detail=True,avg_profit=8.5,avg_loss=-10.,
                    detail_win=72.,trades_per_week_displayed=20.,detail_weeks=52,
                    deposit_load=20.,disclosed_grid=False)

    def test_exact_thresholds_and_high_win_rule(self):
        row=self.record()
        self.assertEqual(mql.evaluate(row),([],[]))
        row['detail_win']=72.01
        self.assertIn('high_winrate_and_small_wins',mql.evaluate(row)[1])
        row['avg_profit']=10.
        self.assertEqual(mql.evaluate(row),([],[]))

    def test_monitoring_and_dd_can_fail_despite_the_listing(self):
        row=self.record()|{'monitor_days':363,'maximal_cash_dd_pct':20.01}
        self.assertEqual(set(mql.evaluate(row)[0]),{'monitor_days_below_floor','dd_above_20'})
        row=self.record()|{'equity_relative_dd':None}
        self.assertEqual(mql.evaluate(row)[0],['unverified_equity_relative_dd'])

    def test_leverage_observation_and_ratio_are_distinct(self):
        row=self.record()|{'equity_relative_dd':15.01,'deposit_load':20.01}
        self.assertEqual(set(mql.evaluate(row)[1]),{'equity_balance_dd_ratio','deposit_load_above_20'})
        row=self.record()|{'detail_trades':1200,'deposit_load':None}
        self.assertIn('cadence_above_20_or_missing',mql.evaluate(row)[1])

    def test_positive_disclosure_and_explicit_denial(self):
        self.assertTrue(mql.description_risk('It uses a grid system and dynamic sizing'))
        self.assertFalse(mql.description_risk('No grid strategy is used'))
        self.assertFalse(mql.description_risk('No martingale. Multi-symbol breakout.'))
        self.assertAlmostEqual(mql.recency('7 hours ago',datetime.now(timezone.utc)),7/24)

    def test_pass2_ids_and_disabled_pages_are_excluded(self):
        candidate=dict(signal_id='2308133',real=True,weeks=90,trades=500,algo=100,dd=10)
        self.assertFalse(mql.list_gate(candidate))
        result=mql.detail('<div>signal is disabled and unavailable</div>',candidate,datetime.now(timezone.utc))
        self.assertEqual(mql.evaluate(result),(['statistics_unverified'],[]))


class GapTests(unittest.TestCase):
    def quotes(self):
        q=np.tile([100.,100.03,99.97,100.,100.01,100.04,99.98,100.01],(901,1))
        q[:180]=[100.,100.05,99.95,100.,100.01,100.06,99.96,100.01]
        q[200]=[100.03,100.07,100.02,100.05,100.04,100.08,100.03,100.06]
        return q

    def test_observed_sparse_clock_retains_entry_and_flat_minutes(self):
        full=self.quotes()
        minutes=np.delete(np.arange(901),310)
        quotes=full[minutes]
        missing,day=gaps.shape(base.START,minutes,quotes,900)
        self.assertTrue(day['compatible'])
        trade,_=equity.select(base.START,quotes,offsets=minutes)
        self.assertTrue(gaps.replayable(missing,minutes,quotes,trade))
        row=equity.record(trade,.005)
        self.assertEqual(row['entry'],base.START+200*60)
        self.assertEqual(row['exit'],base.START+900*60)
        marks=equity.path(trade,.005)
        actual=base.START+minutes[trade.entry:trade.execution.index+1]*60
        self.assertIn(120,np.diff(actual))
        book=equity.Account('Swing',10000,3333.33,.01,.01,50.)
        result,_=equity.account_replay(book,.003,[row],[marks],[base.START//base.DAY],observed_times=[actual])
        self.assertEqual(result['executed'],1)

    def test_gaps_near_fill_are_not_admitted(self):
        full=self.quotes()
        minutes=np.delete(np.arange(901),199)
        quotes=full[minutes]
        trade,_=equity.select(base.START,quotes,offsets=minutes)
        self.assertFalse(gaps.replayable(np.array([199]),minutes,quotes,trade))

    def test_multi_minute_tail_and_quote_jump_are_distinct(self):
        full=self.quotes()
        full[201] += .02
        for removed in ([310,311],[900],[0],[200]):
            minute=np.delete(np.arange(901),removed)
            _,row=gaps.shape(base.START,minute,full[minute],900)
            self.assertFalse(row['compatible'])
            self.assertEqual(row['has_missing_tail'],900 in removed)
        self.assertTrue(gaps.touches_between(100.,100.001,100.0005))
        self.assertFalse(gaps.touches_between(100.,100.001,100.005))

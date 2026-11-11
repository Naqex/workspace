from copy import deepcopy
from datetime import datetime,timezone
from decimal import Decimal as D
from pathlib import Path
import sys
import unittest
from zoneinfo import ZoneInfo

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from review_us500_strategy_fit import book_fit


def trade(day,net,risk='25'):
    entry=int(datetime.fromisoformat(day).replace(hour=10,tzinfo=ZoneInfo('America/New_York')).timestamp()*1000)
    return dict(entry_time=entry,exit_ns=(entry+60000)*1000000+1,cash_net=net,planned_risk=risk,unresolved=False)


def review(trades,days,capital='10000',**extra):
    cash=D(10000)+sum((D(t['cash_net']) for t in trades),D(0))
    book=dict(trades=trades,position=None,decimal_cash=str(cash),**extra)
    return book_fit(book,year=2022,calendar_days=days,starting_balance=capital)


class FitTests(unittest.TestCase):
    def test_month_start_denominator_changes_without_changing_original_capital(self):
        days=['2022-01-03','2022-02-01']
        r=review([trade(days[0],'200'),trade(days[1],'100')],days)
        self.assertEqual(r['return_on_source_initial_pct'],3)
        self.assertEqual(r['monthly'][0]['full_intraday_month_return_pct'],2)
        self.assertEqual(r['monthly'][1]['full_intraday_month_return_pct'],D(100)/10200*100)
        self.assertEqual(len(r['monthly']),12)
        self.assertEqual(r['monthly'][2]['net'],0)

    def test_zero_days_weeks_and_longest_gap_are_not_dropped(self):
        days=['2022-01-03','2022-01-04','2022-01-10','2022-01-11']
        r=review([trade(days[0],'10')],days)
        self.assertEqual(r['days_without_trade'],3)
        self.assertEqual(r['max_no_trade_scheduled_session_run'],3)
        self.assertEqual(r['weekly_distribution'],{0:1,1:1})
        self.assertEqual(r['weeks_in_proposed_3_to_8_band'],0)

    def test_drawdown_uses_peak_while_return_uses_original_capital(self):
        days=['2022-01-03','2022-01-04']
        r=review([trade(days[0],'500'),trade(days[1],'-300')],days)
        self.assertEqual(r['return_on_source_initial_pct'],2)
        self.assertEqual(r['modeled_closed_balance_dd_usd'],300)
        self.assertEqual(r['modeled_closed_balance_dd_peak_pct'],D(300)/10500*100)
        self.assertIsNone(r['full_intraminute_equity_dd_pct'])

    def test_invalid_capital_is_unknown_not_substituted(self):
        for capital in (None,'0','-1','invalid'):
            r=review([trade('2022-01-03','10')],['2022-01-03'],capital)
            self.assertIsNone(r['return_on_source_initial_pct'])
            self.assertTrue(all(m['full_intraday_month_return_pct'] is None for m in r['monthly']))

    def test_unresolved_or_open_position_prevents_full_return_claim(self):
        for mode in ('path','open'):
            t=trade('2022-01-03','10')
            if mode=='path':t['unresolved']=True
            book=dict(trades=[t],position={} if mode=='open' else None,decimal_cash='10010')
            r=book_fit(book,year=2022,calendar_days=['2022-01-03'],starting_balance='10000')
            self.assertIsNone(r['full_net_usd'])
            self.assertTrue(all(m['full_intraday_month_return_pct'] is None for m in r['monthly']))

    def test_net_profit_factor_rr_r_and_streak(self):
        days=['2022-01-03','2022-01-04','2022-01-05']
        r=review([trade(days[0],'20'),trade(days[1],'-10'),trade(days[2],'-10')],days)
        self.assertEqual(r['net_profit_factor'],1)
        self.assertEqual(r['realized_average_win_loss_ratio'],2)
        self.assertEqual(r['longest_closed_loss_streak'],2)
        self.assertEqual(r['mean_net_R_per_trade'],0)
        self.assertEqual(r['max_planned_risk_pct_initial'],D('.25'))

    def test_no_trade_book_is_zero_profit_not_infinite_profit_factor(self):
        r=review([],['2022-01-03'])
        self.assertEqual(r['net_usd'],0)
        self.assertIsNone(r['net_profit_factor'])
        self.assertIsNone(r['mean_net_R_per_trade'])

    def test_duplicate_offcalendar_and_wrong_cash_are_rejected(self):
        t=trade('2022-01-03','10')
        with self.assertRaises(ValueError):review([t,deepcopy(t)],['2022-01-03'])
        with self.assertRaises(ValueError):review([t],['2022-01-04'])
        with self.assertRaises(ValueError):
            book_fit(dict(trades=[t],position=None,decimal_cash='9999'),year=2022,calendar_days=['2022-01-03'],starting_balance='10000')

    def test_stop_timestamp_before_midnight_does_not_round_into_next_month(self):
        t=trade('2022-01-31','10')
        midnight=int(datetime(2022,2,1,tzinfo=ZoneInfo('America/New_York')).timestamp()*1e9)
        t['exit_ns']=midnight-2
        r=review([t],['2022-01-31'])
        self.assertEqual(r['monthly'][0]['net'],10)
        self.assertEqual(r['monthly'][1]['net'],0)

    def test_vietnam_midnight_wrap_is_relative_to_market_session(self):
        first=trade('2022-01-03','10')
        second=trade('2022-01-04','10')
        second['entry_time']+=4*3600000
        second['exit_ns']+=4*3600000*1000000
        r=review([first,second],['2022-01-03','2022-01-04'])
        self.assertEqual(r['entry_vn_session_relative_first'],dict(day_offset_from_NY_session=0,clock='22:00'))
        self.assertEqual(r['entry_vn_session_relative_last'],dict(day_offset_from_NY_session=1,clock='02:00'))


if __name__=='__main__':unittest.main()

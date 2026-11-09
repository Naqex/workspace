from datetime import datetime, timezone
from decimal import Decimal as D
from pathlib import Path
import sys
import json
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from equity_calendar_component import inspect_day, inspect_sessions, summarize, turn_days
from sealed_m1_review import cash_sessions


def quote(at, bid, ask=None):
    ask = bid+D('.2') if ask is None else ask
    return tuple(dict(timestamp=at,open=str(price),close=str(price),high=str(price),low=str(price),volume=1)
                 for price in [bid,ask])


class CalendarComponentTests(unittest.TestCase):
    def test_calendar_not_observed_prices_selects_last_and_first_three(self):
        dates=['2023-12-27','2023-12-28','2023-12-29','2024-01-02','2024-01-03','2024-01-04','2024-01-05','2024-01-31']
        selected=turn_days({day: [] for day in dates})
        self.assertIn('2023-12-29',selected)
        self.assertTrue({'2024-01-02','2024-01-03','2024-01-04','2024-01-31'} <= selected)
        self.assertNotIn('2024-01-05',selected)

    def test_quote_sides_and_slippage_have_hand_calculated_net(self):
        stamps=[60000,120000,180000,240000]
        pairs={at:quote(at,D(100)) for at in stamps}
        pairs[stamps[-1]]=quote(stamps[-1],D(102))
        row=inspect_day('fixture',stamps,pairs,previous_close=D(100))
        self.assertEqual(row['tradable_net_bps']['reference'],D('1.3')/D('100.2')*10000)
        self.assertEqual(row['tradable_net_bps']['stress'],D('.3')/D('100.2')*10000)

    def test_log_decomposition_and_missing_endpoints_are_explicit(self):
        stamps=[60000,120000,180000,240000]
        pairs={at:quote(at,D(102)) for at in stamps}
        pairs[stamps[-1]]=quote(stamps[-1],D(104))
        row=inspect_day('fixture',stamps,pairs,previous_close=D(100))
        self.assertLess(abs(row['ctc_log_bps']-row['overnight_log_bps']-row['cash_log_bps']),D('1e-24'))
        del pairs[stamps[-1]]
        absent=inspect_day('fixture',stamps,pairs,previous_close=D(100))
        self.assertIsNone(absent['ctc_log_bps'])
        self.assertIsNone(absent['tradable_net_bps'])
        self.assertIn('cash_close',absent['missing'])

    def test_missing_predecessor_cannot_be_forwardfilled_or_treated_as_zero(self):
        sessions={'2024-01-02':[60000,120000,180000,240000],
                  '2024-01-03':[300000,360000,420000,480000]}
        pairs={at:quote(at,D(100)) for stamps in sessions.values() for at in stamps}
        del pairs[240000]
        rows=inspect_sessions(sessions,pairs)
        self.assertIsNone(rows[-1]['ctc_log_bps'])
        self.assertIsNone(rows[-1]['previous_close_stamp'])
        summary=summarize(rows)
        self.assertEqual(summary['TOM']['metrics']['ctc_log_bps']['observed'],0)
        self.assertIsNone(summary['TOM']['metrics']['ctc_log_bps']['mean'])

    def test_summary_keeps_tradable_and_decomposition_availability_separate(self):
        stamps=[60000,120000,180000,240000]
        pairs={at:quote(at,D(100)) for at in stamps}
        pairs[180000][0]['volume']=pairs[180000][1]['volume']=0
        row=inspect_day('fixture',stamps,pairs)
        row['group']='TOM'
        summary=summarize([row])['TOM']
        self.assertEqual(summary['metrics']['ctc_log_bps']['missing'],1)
        self.assertEqual(summary['metrics']['tradable_stress_bps']['observed'],1)
        self.assertEqual(summary['days_with_both_side_zero_volume_fill_minutes'],1)

    def test_frozen_calendar_dst_and_halfday_execution_endpoints(self):
        calendar=Path(__file__).resolve().parents[1]/'fixtures/nyse-2024.json'
        sessions=cash_sessions(json.loads(calendar.read_text()))
        halfday=sessions['2024-11-29']
        pairs={at:quote(at,D(100)) for at in [halfday[0],halfday[0]+120000,halfday[-1]]}
        row=inspect_day('2024-11-29',halfday,pairs)
        self.assertEqual(len(halfday),210)
        self.assertEqual(datetime.fromtimestamp(row['required_timestamps']['exit']/1000,timezone.utc).hour,17)
        for day,utc_hour in [('2024-03-08',14),('2024-03-11',13)]:
            self.assertEqual(datetime.fromtimestamp(sessions[day][0]/1000,timezone.utc).hour,utc_hour)

    def test_source_side_masks_use_bid_for_cash_but_ask_for_entry(self):
        stamps=[60000,120000,180000,240000]
        pairs={at:quote(at,D(100)) for at in stamps}
        sides={at:dict(bid=True,ask=False) for at in stamps}
        row=inspect_day('fixture',stamps,pairs,previous_close=D(100),source_sides=sides)
        self.assertIsNotNone(row['ctc_log_bps'])
        self.assertIsNone(row['tradable_net_bps'])
        self.assertEqual(row['missing'],['entry'])
        sides[180000]=dict(bid=False,ask=True)
        row=inspect_day('fixture',stamps,pairs,previous_close=D(100),source_sides=sides)
        self.assertIsNotNone(row['tradable_net_bps'])
        sides[60000]['bid']=False
        row=inspect_day('fixture',stamps,pairs,previous_close=D(100),source_sides=sides)
        self.assertIsNone(row['ctc_log_bps'])
        self.assertIsNotNone(row['tradable_net_bps'])

    def test_missing_source_evidence_cannot_be_truthy_or_assumed_observed(self):
        stamps=[60000,120000,180000,240000]
        pairs={at:quote(at,D(100)) for at in stamps}
        for sides in [{},{at:dict(bid='true',ask=1) for at in stamps}]:
            row=inspect_day('fixture',stamps,pairs,source_sides=sides)
            self.assertIsNone(row['tradable_net_bps'])
            self.assertEqual(len(row['missing']),4)

    def test_padded_predecessor_bid_cannot_create_a_daily_return(self):
        sessions={'2024-01-02':[60000,120000,180000,240000],
                  '2024-01-03':[300000,360000,420000,480000]}
        pairs={at:quote(at,D(100)) for stamps in sessions.values() for at in stamps}
        sides={at:dict(bid=True,ask=True) for at in pairs}
        sides[240000]['bid']=False
        rows=inspect_sessions(sessions,pairs,source_sides=sides)
        self.assertIsNone(rows[-1]['ctc_log_bps'])
        self.assertIsNone(rows[-1]['previous_close_stamp'])


if __name__=='__main__':unittest.main()

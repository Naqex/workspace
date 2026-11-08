from copy import deepcopy
from fractions import Fraction as F
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sealed_m1_review import cash_sessions
from relative_equity_component import month_schedule, relative_signal, costed_views, positive


class RelativeEquityTests(unittest.TestCase):
    def setUp(self):
        root=Path(__file__).resolve().parents[1]/'fixtures'
        self.sessions=cash_sessions(json.loads((root/'nyse-2022.json').read_text()))
        self.schedule=month_schedule(self.sessions,2022,1)

    def points(self,day,ezu='100',spy='100',fx='1'):
        stamp=self.schedule['equity_stamps'][day]
        return {instrument:dict(stamp=stamp,known_at=stamp+60000,bid=value,ask=value)
                for instrument,value in [('ezuususd',ezu),('spyususd',spy),('eurusd',fx)]}

    def test_currency_conversion_and_direction_match_fraction_oracle(self):
        first=self.points(self.schedule['first'])
        for ezu,spy,fx in [('110','100','1.1'),('110','100','1'),('110','120','1'),('98.313','101.9','1.044')]:
            last=self.points(self.schedule['penultimate'],ezu,spy,fx)
            ratio=F(ezu)/F(fx)/100-(F(spy)/100)
            expected='SELL' if ratio>0 else 'BUY' if ratio<0 else None
            self.assertEqual(relative_signal(first,last,self.schedule)['side'],expected)

    def test_future_or_asynchronous_close_and_invalid_units_are_rejected(self):
        first=self.points(self.schedule['first']);last=self.points(self.schedule['penultimate'])
        for change in [dict(stamp=last['eurusd']['stamp']-60000),dict(known_at=self.schedule['decision_ms'])]:
            bad=deepcopy(last);bad['eurusd'].update(change)
            with self.subTest(change=change),self.assertRaisesRegex(ValueError,'noncausal'):
                relative_signal(first,bad,self.schedule)
        for value in [True,'NaN','Infinity','0','-1']:
            with self.subTest(value=value),self.assertRaises(ValueError): positive(value)

    def test_london_dst_has_known_UTC_entry_and_exit(self):
        from datetime import datetime,timezone
        for month,day,entry,exit_at in [(1,'2022-01-31','15:01','16:03'),(6,'2022-06-30','14:01','15:03')]:
            schedule=month_schedule(self.sessions,2022,month)
            self.assertEqual(schedule['last'],day)
            for key,want in [('entry_ms',entry),('exit_ms',exit_at)]:
                self.assertEqual(datetime.fromtimestamp(schedule[key]/1000,timezone.utc).strftime('%H:%M'),want)

    def test_calendar_early_close_and_closed_holdout_are_preserved(self):
        schedule=month_schedule(self.sessions,2022,11)
        self.assertEqual(schedule['first'],'2022-11-01')
        self.assertEqual(len(self.sessions['2022-11-25']),210)
        with self.assertRaisesRegex(ValueError,'historical'):month_schedule(self.sessions,2025,1)

    def test_missing_side_cannot_be_used_as_zero_and_controls_keep_primary_direction(self):
        signal=dict(side='SELL')
        entry=dict(stamp=self.schedule['entry_ms'],bid='1.1',ask='1.1001')
        exit_at=dict(stamp=self.schedule['exit_ms'],bid='1.09',ask='1.0901')
        calls=[]
        def costs(side,entry,exit_at,scenario):calls.append((side,scenario));return {'net_pips':'stub'}
        views=costed_views(signal,entry,exit_at,self.schedule,costs)
        self.assertEqual([views[v]['side'] for v in views],['SELL','BUY','BUY','SELL'])
        self.assertEqual(len(calls),8)
        with self.assertRaises(KeyError):costed_views(signal,{'stamp':entry['stamp'],'bid':'1.1'},exit_at,self.schedule,costs)


if __name__=='__main__':unittest.main()

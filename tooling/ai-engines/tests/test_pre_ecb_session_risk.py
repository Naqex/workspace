from pathlib import Path
from decimal import Decimal as D
from types import SimpleNamespace as NS
import sys,unittest
sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(Path(__file__).resolve().parents[3]/'projects/trader/foundation_v2')]
from pre_ecb_session_risk import plans,SessionBook,HOUR

def hour(at,askopen='1.10010',askhigh='1.10020',asklow='1.10000',askclose='1.10010'):
    ask=tuple(map(D,(askopen,askhigh,asklow,askclose)));bid=tuple(p-D('.00010') for p in ask)
    return NS(mid=NS(timestamp=at//1000),first_time_msc=at+1,last_time_msc=at+HOUR-1,first_sequence=at//HOUR+1,bid=bid,ask=ask)
def plan(at,distance='.001',stop=None):
    return dict(day='2022-01-03',decision_ms=at-1,entry_target_ms=at,exit_target_ms=at+2*HOUR,status='ready',distance=distance,history=[])

class SessionRiskTests(unittest.TestCase):
    def test_RMS_uses20_previous_sessions_not_current_futureprice(self):
        events=[]
        for i in range(22):
            at=(i+1)*86400000
            events.append(dict(day=str(i),entry_target_ms=at,exit_target_ms=at+HOUR,
                entry=dict(time_msc=at+1,bid='1.1',ask='1.1001'),exit=dict(time_msc=at+HOUR+1,bid='1.101',ask='1.1011')))
        before=plans(events);self.assertEqual(D(before[20]['distance']),D('.002'))
        events[20]['entry']['bid']='999';self.assertEqual(plans(events)[20],before[20])
        events[0]['exit']=None;self.assertEqual(plans(events)[20]['status'],'unavailable_history')
        events[0]['exit']=dict(time_msc=events[20]['entry_target_ms'],bid='1.1',ask='1.1001')
        # Its target-lag is invalid, so it is unavailable rather than silently usable history.
        self.assertEqual(plans(events)[20]['status'],'unavailable_history')
    def test_short_stop_and_costaware_quantity(self):
        at=1641168000000;b=SessionBook([plan(at)],'stress',[])
        b.apply(hour(at,askhigh='1.10200'));t=b.trades[0]
        self.assertEqual(t['reason'],'stop_loss');self.assertLessEqual(D(t['planned_risk']),25)
        self.assertEqual(D(t['quantity'])%D('.01'),0);self.assertLessEqual(-D(t['net']),25)
    def test_delayed_exit_is_not_dropped_and_stop_gap_can_exceed_budget(self):
        at=1641168000000;b=SessionBook([plan(at)],'reference',[])
        b.apply(hour(at));b.apply(hour(at+3*HOUR,askopen='1.09910',askhigh='1.09920',asklow='1.09900',askclose='1.09910'))
        self.assertEqual(b.trades[0]['reason'],'scheduled_exit');self.assertGreater(b.trades[0]['scheduled_exit_delay_ms'],HOUR)
        self.assertTrue(b.trades[0]['missing_hour_intervals']);self.assertIsNone(b.position)
        b=SessionBook([plan(at)],'reference',[]);b.apply(hour(at))
        b.apply(hour(at+HOUR,askopen='1.11010',askhigh='1.11020',asklow='1.11000',askclose='1.11010'))
        self.assertEqual(b.trades[0]['reason'],'stop_gap');self.assertGreater(-D(b.trades[0]['net']),25)
    def test_funding_openmark_continuous_cash_and_overall_halt(self):
        at=1641168000000;terms=NS(scheduled_time_msc=at+HOUR,debit_sell_usd_per_lot=D(20),multiplier=3)
        b=SessionBook([plan(at,'.02')],'stress',[terms]);b.apply(hour(at));b.apply(hour(at+HOUR));b.seal_year(2022)
        result=b.result();self.assertIsNotNone(result['open_position']);self.assertEqual(len(result['funding_events']),1)
        self.assertEqual(D(result['balance']),10000-D(result['funding']))
        self.assertEqual(D(result['ending_equity']),D(result['balance'])+D(result['floating']))
        b._cash(D(-600),at+HOUR+1);self.assertTrue(b.overall_halt);self.assertIsNotNone(b.first_cash_breach)

if __name__=='__main__':unittest.main()

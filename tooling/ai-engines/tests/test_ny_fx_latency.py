from copy import deepcopy
from pathlib import Path
from decimal import Decimal as D
import sys,unittest
WS=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(WS/'tooling/ai-engines'),str(WS/'projects/trader/foundation_v2')]
import ny_fx_latency as m
m.parent.bind_core(WS/'projects/trader/foundation_v2')

def series(day='2019-01-02'):
    at=m.parent.clocks(day)[10];pairs={}
    for i in range(-15*60,5*60+1):
        h=i//60;b=D('1.1')+D(h)*D('.0001') if h<0 else D('1.1')
        pairs[at+i*m.MINUTE]=tuple(dict(timestamp=at+i*m.MINUTE,open=b+s,close=b+s,
            high=b+s+D('.0002'),low=b+s-D('.0002'),volume=1) for s in (D(0),D('.0001')))
    return pairs

class LatencyTests(unittest.TestCase):
    def test_strict_hour_source_grid_and_feature_future_isolation(self):
        pairs=series();hourly=m.aggregate_hours(pairs);t=m.parent.clocks('2019-01-02')[10]
        r=m.parent.decision(hourly,t);self.assertEqual(r['side'],'SELL')
        changed=deepcopy(pairs);changed.pop(t-12*m.parent.HOUR)
        self.assertNotIn(t-12*m.parent.HOUR,m.aggregate_hours(changed))
        self.assertEqual(m.parent.decision(m.aggregate_hours(changed),t)['status'],'feature_unavailable')
        changed=deepcopy(pairs)
        for at,pair in changed.items():
            if at>=t:
                for row in pair:row.update(open=9,close=9,high=10,low=8)
        self.assertEqual(m.parent.decision(m.aggregate_hours(changed),t),r)

    def test_registered_lag_changes_action_only_with_same_intents_and_time_exit(self):
        pairs=series();hourly=m.aggregate_hours(pairs);books=[]
        for lag in (15,60):
            b=m.run(pairs,hourly,2019,'stress',lag_minutes=lag,day_list=['2019-01-02']);books.append(b)
            self.assertEqual(b['closed_trades'],1);self.assertEqual(b['trades'][0]['reason'],'scheduled_exit')
            self.assertEqual(b['events'][0]['entry_msc']-b['events'][0]['decision_msc'],lag*m.MINUTE)
            self.assertEqual(b['trades'][0]['exit_bar_msc'],m.parent.clocks('2019-01-02')[15])
            self.assertLessEqual(b['events'][0]['planned_risk_usd'],25)
        for a,b in zip(books[0]['decisions'],books[1]['decisions']):
            self.assertEqual({k:v for k,v in a.items() if k!='action_msc'},{k:v for k,v in b.items() if k!='action_msc'})
        with self.assertRaises(ValueError):m.run(pairs,hourly,2019,'stress',lag_minutes=30)

    def test_missing_held_minute_and_future_close_quality_do_not_reject_past_entry(self):
        pairs=series();hourly=m.aggregate_hours(pairs);at=m.parent.clocks('2019-01-02')[10]+16*m.MINUTE
        pairs.pop(at);book=m.run(pairs,hourly,2019,'reference',lag_minutes=15,day_list=['2019-01-02'])
        self.assertEqual(len(book['events']),1);self.assertEqual(book['account_state'],'unknown_exposure')
        self.assertIsNone(book['net_equity_usd']);self.assertEqual(book['unknown']['at_msc'],at)
        pairs=series();hourly=m.aggregate_hours(pairs);at-=m.MINUTE;pairs[at][1]['close']=D('1.09')
        b=m.run(pairs,hourly,2019,'reference',lag_minutes=15,day_list=['2019-01-02'])
        self.assertEqual(len(b['events']),1);self.assertIsNotNone(b['unknown'])
        n=m.run(pairs,hourly,2019,'reference',lag_minutes=15,null=True,day_list=['2019-01-02'])
        self.assertEqual(n['net_equity_usd'],0);self.assertEqual(n['closed_trades'],0)

    def test_minute_stop_and_gap_are_seen_before_next_hour(self):
        pairs=series();hourly=m.aggregate_hours(pairs);t=m.parent.clocks('2019-01-02')[10]+17*m.MINUTE
        pairs[t][1]['high']=D('1.11')
        b=m.run(pairs,hourly,2019,'reference',lag_minutes=15,day_list=['2019-01-02'])
        self.assertEqual(b['trades'][0]['exit_bar_msc'],t)
        self.assertFalse(b['trades'][0]['exit_at_open'])
        pairs=series();hourly=m.aggregate_hours(pairs)
        for r in pairs[t]:r.update(open=D('1.11'),high=D('1.12'),low=D('1.10'),close=D('1.11'))
        b=m.run(pairs,hourly,2019,'reference',lag_minutes=15,day_list=['2019-01-02'])
        self.assertEqual(b['trades'][0]['exit_quote'],D('1.11'));self.assertTrue(b['trades'][0]['exit_at_open'])

    def test_flip_uses_previous_hour_signal_and_missing_entry_does_not_look_ahead(self):
        pairs=series();at=m.parent.clocks('2019-01-02')[10]
        for t in range(at,at+m.parent.HOUR,m.MINUTE):
            pairs[t][0].update(close=D('1.09'),low=D('1.0898'))
            pairs[t][1].update(close=D('1.0901'),low=D('1.0899'))
        hourly=m.aggregate_hours(pairs)
        b=m.run(pairs,hourly,2019,'reference',lag_minutes=15,day_list=['2019-01-02'])
        flip=next(t for t in b['trades'] if t['reason']=='target_change')
        self.assertEqual(flip['exit_bar_msc'],at+m.parent.HOUR+15*m.MINUTE)
        self.assertEqual([e['side'] for e in b['events'][:2]],['SELL','BUY'])
        pairs=series();hourly=m.aggregate_hours(pairs);pairs.pop(at+15*m.MINUTE)
        b=m.run(pairs,hourly,2019,'reference',lag_minutes=15,day_list=['2019-01-02'])
        row=next(r for r in b['census'] if r['at_msc']==at+15*m.MINUTE)
        self.assertEqual(row['action'],'missing_or_crossed_entry_Open')

if __name__=='__main__':unittest.main()

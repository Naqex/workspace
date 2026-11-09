from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal as D
from fractions import Fraction as F
from pathlib import Path
import sys,unittest

WS=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(WS/'tooling/ai-engines'),str(WS/'projects/trader/foundation_v2')]
import ny_fx_reversal as m
m.bind_core(WS/'projects/trader/foundation_v2')


def series(day='2019-01-02'):
    t=m.clocks(day)[10];out={}
    for i in range(-15,6):
        b=D('1.1')+D(i)*D('.0001') if i<0 else D('1.1')
        out[t+i*m.HOUR]=tuple(dict(timestamp=t+i*m.HOUR,open=float(b+s),close=float(b+s),
            high=float(b+s+D('.0002')),low=float(b+s-D('.0002')),volume=1)
            for s in (D(0),D('.0001')))
    return out


class NyReversalTests(unittest.TestCase):
    def test_midpoint_ma_tr_oracle_and_future_isolation(self):
        p=series();t=m.clocks('2019-01-02')[10];v=m.decision(p,t)
        self.assertEqual(v['side'],'SELL')
        self.assertEqual(F(v['ma4']),sum((F(str(p[x][0]['close']))+F(str(p[x][1]['close'])))/2
            for x in range(t-4*m.HOUR,t,m.HOUR))/4)
        self.assertEqual(v['distance'],D('.0006'))
        q=deepcopy(p)
        for at in q:
            if at>=t:q[at][0].update(open=9,high=99,low=.01,close=90)
        self.assertEqual(m.decision(q,t),v)
        self.assertEqual(m.decision(p,t,opposite=True)['side'],'BUY')

    def test_missing_exact_history_equality_and_dst(self):
        p=series();t=m.clocks('2019-01-02')[10];p.pop(t-7*m.HOUR)
        self.assertEqual(m.decision(p,t)['status'],'feature_unavailable')
        p=series()
        for pair in p.values():
            for row in pair:row['close']=row['open']=1.1
        self.assertIsNone(m.decision(p,t)['side'])
        for day,hour in [('2019-03-08',15),('2019-03-11',14)]:
            self.assertEqual(m.clocks(day)[10],int(datetime.fromisoformat(day).replace(hour=hour,tzinfo=timezone.utc).timestamp()*1000))
        with self.assertRaises(ValueError):m.dates(2025)

    def test_both_directions_cost_and_risk_manual_fraction(self):
        pair=series()[m.clocks('2019-01-02')[11]]
        for side in ('BUY','SELL'):
            for scenario in ('reference','stress'):
                instrument,model=m.market(scenario)
                intent=dict(side=side,distance=D('.001'),decision_msc=0)
                p,status=m.open_position(intent,pair,m.HOUR,D(10000),instrument,model)
                self.assertEqual(status,'opened')
                slip=F(0) if scenario=='reference' else F('.00002')
                per=(F('.001')+F('.00001')+2*slip)*100000+5
                quantity=F((F(25)/per/F('.01')).numerator//(F(25)/per/F('.01')).denominator)*F('.01')
                self.assertEqual(F(p['quantity']),quantity)
                self.assertLessEqual(p['planned_risk_usd'],25)
                cost=m.calculate_round_trip_cost(model,side,p['quantity'],D(100000),p['entry_bid'],p['entry_ask'],D('1.101'),D('1.101'))
                gross=(F('1.101')-F(p['entry_quote']))*(1 if side=='BUY' else -1)*quantity*100000
                expected=round(gross-quantity*(5+2*slip*100000),2)
                self.assertEqual(F(str(cost['net_account'])),expected)
                self.assertIsNone(m.open_position(intent,pair,m.HOUR,D(25),instrument,model)[0])

    def test_hold_flip_and_scheduled_exit(self):
        p=series();r=m.run(p,2019,'reference',day_list=['2019-01-02'])
        self.assertEqual(r['closed_trades'],1)
        self.assertEqual(r['trades'][0]['reason'],'scheduled_exit')
        self.assertEqual(r['account_state'],'modeled_flat')
        self.assertIsNone(r['position'])
        for trade in r['trades']:
            self.assertLess(trade['decision_msc'],trade['entry_msc'])
            self.assertLessEqual(trade['planned_risk_usd'],25)
        n=m.run(p,2019,'reference',null=True,day_list=['2019-01-02'])
        self.assertEqual(n['closed_trades'],0);self.assertEqual(n['net_equity_usd'],0)
        t=m.clocks('2019-01-02')[10]
        p[t][0].update(close=1.09,low=1.0898)
        p[t][1].update(close=1.0901,low=1.0899)
        r=m.run(p,2019,'reference',day_list=['2019-01-02'])
        self.assertEqual(r['trades'][0]['reason'],'target_change')
        self.assertEqual([e['side'] for e in r['events'][:2]],['SELL','BUY'])

    def test_missing_held_hour_freezes_but_missing_entry_is_skipped(self):
        p=series();t=m.clocks('2019-01-02')[12];p.pop(t)
        r=m.run(p,2019,'reference',day_list=['2019-01-02'])
        self.assertEqual(r['account_state'],'unknown_exposure');self.assertIsNone(r['net_equity_usd'])
        p=series();p.pop(m.clocks('2019-01-02')[11])
        r=m.run(p,2019,'reference',day_list=['2019-01-02'])
        self.assertEqual(r['census'][0]['action'],'missing_or_crossed_entry_Open')

    def test_entry_open_not_filtered_by_future_close(self):
        p=series();t=m.clocks('2019-01-02')[11]
        p[t][1]['close']=p[t][0]['close']-.0001
        r=m.run(p,2019,'reference',day_list=['2019-01-02'])
        self.assertEqual(len(r['events']),1)
        self.assertEqual(r['account_state'],'unknown_exposure')

    def test_stop_intrabar_and_open_gap_precede_time_exit(self):
        p=series();t=m.clocks('2019-01-02')[11];p[t][1]['high']=1.11
        r=m.run(p,2019,'reference',day_list=['2019-01-02'])
        self.assertEqual(r['trades'][0]['exit_bar_msc'],t)
        self.assertIn('stop',r['trades'][0]['reason'])
        p=series();t=m.clocks('2019-01-02')[12]
        for row in p[t]:row.update(open=1.11,high=1.12,low=1.10,close=1.11)
        r=m.run(p,2019,'reference',day_list=['2019-01-02'])
        self.assertTrue(r['trades'][0]['exit_at_open'])
        self.assertEqual(r['trades'][0]['exit_quote'],D('1.11'))

if __name__=='__main__':unittest.main()

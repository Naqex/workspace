from copy import deepcopy
from decimal import Decimal as D
from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import us500_continuation_diagnostics as s


def pair(bid,ask):return tuple(dict(open=D(x),high=D(x),low=D(x),close=D(x)) for x in (bid,ask))


class DiagnosticTests(unittest.TestCase):
    def test_control_uses_prior_channel_and_has_future_prefix_invariance(self):
        events=[]
        for i in range(22):
            events.append(dict(t=i*15*s.M,day='2025-01-02',slot=45 if i==20 else 60,
                blocked=False,full_session=True,m15=dict(high=D(101),low=D(99),close=D(100),atr=D(1),previous={})))
        events[-1]['m15']['close']=D(103)
        prepared=dict(snapshots={e['t']:e for e in events});before=s.control_events(prepared)
        self.assertEqual([e['t'] for e in before],[events[20]['t']])
        changed=deepcopy(prepared);changed['snapshots'][events[-1]['t']]['m15']['close']=D(100)
        after=s.control_events(changed)
        self.assertEqual([e for e in after if e['t']<events[-1]['t']],before)
        changed['snapshots'][events[20]['t']]['blocked']=True
        self.assertNotIn(events[20]['t'],[e['t'] for e in s.control_events(changed)])

    def test_buy_sell_and_costs_by_direct_cash_subtraction(self):
        a=pair('100','100.2');b=pair('102','102.2')
        for side,ref,stress in [('BUY','1.3','.3'),('SELL','-2.7','-3.7')]:
            x=s.components(a,b,side,D(1))
            self.assertEqual(x['reference_points'],D(ref));self.assertEqual(x['stress_points'],D(stress))
            self.assertEqual(x['move_points']-x['spread_points']-D('.5'),D(ref))
        self.assertEqual(s.components(b,a,'SELL',D(1))['reference_points'],D('1.3'))

    def test_flat_price_is_cost_loss_not_zero(self):
        x=s.components(pair('100','100.2'),pair('100','100.2'),'BUY',D(1))
        self.assertEqual(x['move_R'],0);self.assertEqual(x['reference_points'],D('-.7'))
        self.assertEqual(x['stress_points'],D('-1.7'))

    def test_full_path_and_prefix_required_despite_valid_endpoints(self):
        pairs={n*s.M:pair('100','100.2') for n in range(18)}
        minutes={t:dict(day='2025-01-02') for t in pairs}
        self.assertEqual(s.markout(pairs,minutes,0,'BUY',D(1),15)['status'],'known')
        for n in (0,8):
            changed=dict(pairs);del changed[n*s.M]
            self.assertEqual(s.markout(changed,minutes,0,'BUY',D(1),15)['status'],'missing_quotes')
        minutes[16*s.M]['day']='next'
        self.assertEqual(s.markout(pairs,minutes,0,'BUY',D(1),15)['status'],'outside_session')

    def test_exit_minute_extreme_is_not_allowed_before_stop(self):
        pairs={i*s.M:pair('100','100.2') for i in range(5)}
        pairs[s.M][0]['high']=D(102)
        pairs[3*s.M][0]['high']=D(999)
        trade=dict(unresolved=False,entry_time=s.M,exit_ns=4*s.M*1000000-2,side='BUY',entry='100.45',quantity='10',planned_risk='22.5',net='-7')
        x=s.excursion(trade,pairs,'.25')
        self.assertEqual(x['favorable_R'],D('1.30')/D('2.25'))
        self.assertTrue(x['loser_after_half_R'])
        trade['unresolved']=True
        self.assertEqual(s.excursion(trade,pairs,'.25')['status'],'unknown_held_path')

    def test_control_excludes_current_day_and_unknowns(self):
        p=s.new_pool();a=dict(status='known',**{f:D(1) for f in s.FIELDS});b=dict(status='known',**{f:D(3) for f in s.FIELDS})
        s.pool_add(p,dict(day='a'),a);s.pool_add(p,dict(day='b'),b)
        c=s.contrast(p,'a',a)
        self.assertEqual(c['control_n'],1);self.assertEqual(c['control_mean']['move_R'],3)
        self.assertEqual(c['excess_R']['move_R'],-2)
        with self.assertRaisesRegex(ValueError,'duplicate'):s.pool_add(p,dict(day='a'),a)
        x=s.summarize([dict(status='missing_quotes'),dict(status='outside_session')])
        self.assertIsNone(x['means']['stress_R']);self.assertEqual(x['total'],2)

    def test_invalid_side_atr_spread_or_horizon_stops(self):
        for side,atr in [('UP',1),('BUY',0),('SELL',D('NaN'))]:
            with self.assertRaises(ValueError):s.components(pair('100','100.2'),pair('101','101.2'),side,atr)
        with self.assertRaises(ValueError):s.components(pair('101','100'),pair('101','101.2'),'BUY',1)
        with self.assertRaises(ValueError):s.markout({}, {},0,'BUY',1,5)


if __name__=='__main__':unittest.main()

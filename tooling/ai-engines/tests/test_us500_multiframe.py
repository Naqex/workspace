"""Synthetic causal/event/accounting checks; no market data or broker access."""
from copy import deepcopy
from datetime import datetime
from decimal import Decimal as D
from pathlib import Path
import sys
import unittest
from zoneinfo import ZoneInfo

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import us500_multiframe as s
import review_us500_multiframe as reviewer


def event(slot, close, *, side='BUY', day='2022-01-04', m15=True, bias=None):
    start=int(datetime.fromisoformat(day).replace(hour=9,minute=30,tzinfo=ZoneInfo('America/New_York')).timestamp()*1000)
    sign=1 if side=='BUY' else -1
    means={10:D(100),20:D(100),40:D(99 if sign==1 else 101),80:D(99 if sign==1 else 101),160:D(98 if sign==1 else 102)}
    previous=dict(day=day,close=D(101 if sign==1 else 99),means=means)
    bar=dict(close=D(close),high=D(101),low=D(99),means=means,atr=D(1),previous=previous)
    return dict(day=day,slot=slot,t=start+slot*s.M,blocked=False,full_session=True,
                m15=bar if m15 else None,m5=bar,ready=True,bias=dict(side=bias or side,t=start,day=day))


def fixture(*, side='BUY', stop=False, gap=False, missing=None):
    arm=event(30,100,side=side)
    confirm=event(45,102 if side=='BUY' else 98,side=side)
    noon=event(150,102 if side=='BUY' else 98,side=side)
    start=arm['t']-30*s.M
    stamps=list(range(start,start+155*s.M,s.M))
    pairs={t:tuple(dict(timestamp=t,open=100+d,high=101+d,low=99+d,close=100+d,volume=0)
                   for d in (0,.2)) for t in stamps}
    t=stamps[50]
    if stop:
        if side=='BUY':pairs[t][0]['low']=95
        else:pairs[t][1]['high']=105
    if gap:
        if side=='BUY':pairs[t][0].update(open=95,low=94,high=96,close=95)
        else:pairs[t][1].update(open=105,low=104,high=106,close=105)
    if missing is not None:
        del pairs[stamps[missing]]
    prepared=dict(snapshots={e['t']:e for e in (arm,confirm,noon)},missing=set(stamps)-pairs.keys())
    return pairs,prepared,stamps


class PolicyTests(unittest.TestCase):
    def config(self,lane='A',k='0.1'):
        return dict(lane=lane,k=k,fast=20,slow=80,id='fixture')

    def test_census(self):
        cs=s.configurations()
        self.assertEqual(len(cs),27)
        self.assertEqual(len({(c['lane'],c['fast'],c['slow'],c['k']) for c in cs}),27)
        self.assertEqual([c['id'] for c in cs],[f'R{i:03}' for i in range(96,123)])

    def test_long_short_and_strict_threshold(self):
        for side,px in (('BUY','101.1'),('SELL','98.9')):
            p=s.Policy(self.config())
            self.assertIsNone(p.event(event(30,100,side=side)))
            self.assertIsNone(p.event(event(45,px,side=side)))
            action=p.event(event(60,102 if side=='BUY' else 98,side=side))
            self.assertEqual(action['side'],side)
            self.assertEqual(action['arm_time'],event(30,100)['t'])

    def test_h1_reject_consumes_attempt(self):
        p=s.Policy(self.config('B'))
        p.event(event(30,100,bias='SELL'))
        p.event(event(45,100,bias='BUY'))
        self.assertIsNone(p.arm)
        self.assertEqual(p.events[0]['kind'],'reject_h1')

    def test_m5_earlier_but_not_same_arm_and_freezes_h1(self):
        p=s.Policy(self.config('C'))
        p.event(event(30,100))
        self.assertIsNone(p.event(event(30,103,m15=False)))
        a=p.event(event(35,102,m15=False,bias='SELL'))
        self.assertEqual(a['t'],event(35,102)['t'])
        self.assertEqual(a['bias']['side'],'BUY')

    def test_m15_cancellation_before_m5_confirm(self):
        p=s.Policy(self.config('C'))
        p.event(event(30,100))
        e=event(45,103)
        e['m15']['means'][80]=D(100)
        self.assertIsNone(p.event(e))
        self.assertIsNone(p.arm)

    def test_final_expiry_allowed_and_after_expiry_forbidden(self):
        for slot,allowed in ((90,True),(95,False)):
            p=s.Policy(self.config('C'))
            p.event(event(30,100))
            answer=p.event(event(slot,102,m15=False))
            self.assertEqual(answer is not None,allowed)

    def test_gaps_short_days_and_warmup_block(self):
        for key in ('blocked','full_session','ready'):
            p=s.Policy(self.config())
            e=event(30,100)
            e[key]=key=='blocked'
            self.assertIsNone(p.event(e))
            self.assertIsNone(p.arm)

    def test_no_previous_session_arm_and_one_attempt(self):
        p=s.Policy(self.config())
        e=event(30,100)
        e['m15']['previous']['day']='2022-01-03'
        p.event(e)
        self.assertIsNone(p.arm)
        p.event(event(45,100))
        p.event(event(90,100))
        p.event(event(45,100))
        self.assertIsNone(p.arm)

    def test_native_indicator_first_seed_and_exact_sma(self):
        i=s.Indicators()
        atr=None
        for n in range(1,162):
            bar=dict(open=D(100),close=D(100),low=D(100),high=D(100+n))
            got=i.update(bar,'2022-01-04',n)
            atr=D(n) if atr is None else (atr*13+n)/14
        self.assertEqual(got['atr'],atr)
        self.assertTrue(got['common_m15_ready'])
        self.assertEqual(got['means'][160],100)

    def test_cash_h1_asof_partial_and_future_invariance(self):
        sessions,pairs={},{}
        for day in ('2022-01-03','2022-01-04','2022-01-05','2022-01-06','2022-01-07','2022-01-10','2022-01-11'):
            _,_,ts=fixture()
            start=event(0,100,day=day)['t']
            times=list(range(start,start+390*s.M,s.M))
            sessions[day]=times
            pairs.update({t:tuple(dict(timestamp=t,open=100+d,close=100+d,low=99+d,high=101+d,volume=0) for d in (0,.2)) for t in times})
        a=s.prepare(sessions,pairs)
        e=a['snapshots'][event(45,100,day='2022-01-11')['t']]
        self.assertEqual(e['bias']['day'],'2022-01-10')
        at=event(60,100,day='2022-01-11')['t']
        self.assertEqual(a['snapshots'][at]['bias']['t'],at)
        # Last 30 minutes never manufacture a full H1.
        end=event(390,100,day='2022-01-11')['t']
        self.assertEqual(a['snapshots'][end]['bias']['t'],event(360,100,day='2022-01-11')['t'])
        cutoff=event(90,100,day='2022-01-11')['t']
        del pairs[cutoff+10*s.M]
        b=s.prepare(sessions,pairs)
        self.assertEqual(a['snapshots'][cutoff],b['snapshots'][cutoff])
        self.assertFalse(b['snapshots'][cutoff+15*s.M]['ready'])


class NativeTests(unittest.TestCase):
    def run_fixture(self,**kwargs):
        pairs,prepared,stamps=fixture(**kwargs)
        r=s.execute(dict(lane='A',fast=20,slow=80,k='0.1',id='fixture'),prepared,pairs,s.quote_data(pairs),'.25')
        reviewer.inspect(r,pairs)
        return r,stamps

    def test_buy_sell_spread_slippage_noon_cash_and_stop_anchor(self):
        for side in ('BUY','SELL'):
            r,ts=self.run_fixture(side=side)
            self.assertEqual(len(r['trades']),1)
            p=r['trades'][0]
            self.assertEqual(p['entry_time'],ts[46])
            self.assertEqual(p['exit_ns']//1000000,ts[151])
            self.assertEqual(p['entry'],D('100.45') if side=='BUY' else D('99.75'))
            self.assertEqual(p['stop'],D('98.45') if side=='BUY' else D('101.75'))
            self.assertEqual(p['quantity'],D('11.11'))
            self.assertEqual(p['net'],D('-7.777'))
            self.assertEqual(r['native_cash'],D('9992.22'))
            self.assertEqual(r['native_open_positions'],0)
            self.assertEqual(r['native_open_orders'],0)

    def test_native_intraminute_stop_and_adverse_gap(self):
        for side in ('BUY','SELL'):
            for kind,expected in (('stop',D('-24.9975')),('gap',D('-63.327'))):
                r,ts=self.run_fixture(side=side,**{kind:True})
                self.assertEqual(r['trades'][0]['reason'],'stop')
                # BUY gap95-.25; SELL gap105+.25. Native stop matching, no forced exit ledger.
                actual=r['trades'][0]['net']
                if kind=='stop':self.assertEqual(actual,expected)
                else:self.assertLess(actual,D(-25))
                self.assertEqual(len(r['fills']),2)
                self.assertEqual(r['native_open_orders'],0)

    def test_missing_exact_entry_rejects_without_late_fill(self):
        r,_=self.run_fixture(missing=46)
        self.assertEqual(len(r['trades']),0)
        self.assertEqual(r['rejections'][0]['kind'],'missing_exact_fill')

    def test_held_gap_does_not_become_known_profit(self):
        r,_=self.run_fixture(missing=48)
        self.assertTrue(r['trades'][0]['unresolved'])

    def test_gap_followed_by_native_stop_is_also_unresolved(self):
        r,_=self.run_fixture(missing=49,gap=True)
        self.assertTrue(r['trades'][0]['unresolved'])

    def test_gap_before_exact_fill_cancels_entry(self):
        r,_=self.run_fixture(missing=45)
        self.assertEqual(r['trades'],[])
        self.assertEqual(r['rejections'][0]['kind'],'entry_prefix_gap')

    def test_independent_reviewer_rejects_material_mutations(self):
        p,a,_=fixture(stop=True)
        original=s.execute(s.configurations()[0],a,p,s.quote_data(p),'.25')
        for field,value in (('entry_time',original['trades'][0]['entry_time']-s.M),('net',D(999)),('stop',D(90)),('quantity',D(50)),('exit',D(999))):
            changed=deepcopy(original)
            changed['trades'][0][field]=value
            with self.assertRaises(ValueError):reviewer.inspect(changed,p)

    def test_missing_noon_exit_preserves_unknown(self):
        r,_=self.run_fixture(missing=151)
        self.assertIsNotNone(r['position'])
        self.assertTrue(r['position']['unresolved'])

    def test_null_no_orders_or_cash_change(self):
        p,a,_=fixture()
        r=s.execute(s.configurations()[0],a,p,s.quote_data(p),'.25',null=True)
        self.assertEqual(r['native_cash'],10000)
        self.assertEqual(r['fills'],[])

    def test_multiple_roundtrips_netting_history_cash(self):
        pairs,prepared,_=fixture()
        for offset in (1,2):
            p,a,_=fixture(side='SELL' if offset==1 else 'BUY')
            shift=offset*24*60*s.M
            pairs.update({t+shift:tuple(dict(row,timestamp=t+shift) for row in pair) for t,pair in p.items()})
            for t,e in a['snapshots'].items():
                e=deepcopy(e)
                e['t']+=shift
                e['day']=f'2022-01-0{4+offset}'
                e['m15']['previous']['day']=e['day']
                prepared['snapshots'][t+shift]=e
        r=s.execute(s.configurations()[0],prepared,pairs,s.quote_data(pairs),'.25')
        self.assertEqual(len(r['trades']),3)
        self.assertEqual(len(r['native_realized']),3)
        self.assertEqual(r['native_cash'],D('9976.66'))
        reviewer.inspect(r,pairs)


if __name__=='__main__':
    unittest.main()

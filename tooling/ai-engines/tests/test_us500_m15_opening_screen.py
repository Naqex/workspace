from copy import deepcopy
from datetime import datetime
from decimal import Decimal as D
from pathlib import Path
import sys
import unittest
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import us500_m15_opening_screen as study
import review_us500_m15_opening as reviewer
import run_us500_m15_opening_screen as runner

ROOT = Path(__file__).resolve().parents[3]
M = 60000


def fixture(day='2022-01-04', direction=1):
    at=int(datetime.fromisoformat(day).replace(hour=9, minute=30,tzinfo=ZoneInfo('America/New_York')).timestamp()*1000)
    stamps=list(range(at,at+390*M,M))
    pairs={}
    for index,t in enumerate(stamps[:152]):
        price=D(105) if index<15 else D(111) if 15<=index<30 and direction==1 else D(99) if 15<=index<30 else D(105)
        pairs[t]=tuple(dict(timestamp=t,open=float(price+offset),close=float(price+offset),
            high=float(price+offset),low=float(price+offset),volume=0) for offset in (D(0),D('.2')))
    for point,offset in zip(pairs[stamps[0]],(D(0),D('.2'))):
        point.update(high=float(D(110)+offset),low=float(D(100)+offset))
    return {day:stamps},pairs,stamps


class M15OpeningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        study.core.bind_core(ROOT/'projects/trader/foundation_v2')

    def test_registered_break_and_failed_break_are_different_closed_bars(self):
        sessions,pairs,stamps=fixture()
        a,_=study.plans_for(sessions,pairs,'breakout')
        b,_=study.plans_for(sessions,pairs,'failed_break')
        self.assertEqual((a[stamps[30]]['side'],a[stamps[30]]['distance']),('BUY',D(10)))
        self.assertEqual((b[stamps[45]]['side'],b[stamps[45]]['distance']),('SELL',D(10)))
        self.assertNotIn(stamps[30],b)

    def test_sell_break_and_failed_buy(self):
        s,p,t=fixture(direction=-1)
        self.assertEqual(study.plans_for(s,p,'breakout')[0][t[30]]['side'],'SELL')
        self.assertEqual(study.plans_for(s,p,'failed_break')[0][t[45]]['side'],'BUY')

    def test_future_changes_or_missing_exit_cannot_remove_earlier_signal(self):
        s,p,t=fixture()
        original=study.plans_for(s,p,'breakout')[0][t[30]]
        del p[t[151]]
        p[t[100]][0]['close']=1
        self.assertEqual(original,study.plans_for(s,p,'breakout')[0][t[30]])

    def test_missing_causal_prefix_short_day_and_zero_range(self):
        for mode in ('opening','prefix','short','zero'):
            s,p,t=fixture()
            if mode=='opening':del p[t[1]]
            elif mode=='prefix':del p[t[20]]
            elif mode=='short':s={next(iter(s)):t[:210]}
            else:
                for at in t[:15]:p[at][0].update(open=100,high=100,low=100,close=100)
            plans,_=study.plans_for(s,p,'breakout')
            self.assertFalse(any(d['side'] in ('BUY','SELL') for d in plans.values()))

    def test_equality_at_range_boundary_is_not_breakout(self):
        s,p,t=fixture()
        p[t[29]][0]['close']=110
        self.assertNotIn(t[30],study.plans_for(s,p,'breakout')[0])

    def test_one_attempt_even_if_price_breaks_opposite_later(self):
        s,p,t=fixture()
        p[t[59]][0]['close']=99
        plans,_=study.plans_for(s,p,'breakout')
        self.assertEqual(sum(d['side'] in ('BUY','SELL') for d in plans.values()),1)

    def test_delayed_fill_time_exit_and_budget_match_hand_calculation(self):
        s,p,t=fixture()
        r=study.simulate(s,p,policy='breakout',slippage=D('.25'))
        trade=r['trades'][0]
        self.assertEqual(trade['entry_time_msc'],t[31])
        self.assertEqual(trade['exit_time_msc'],t[151])
        self.assertEqual(trade['entry_fill'],'105.2')
        self.assertEqual(D(trade['stop']),D('95.2'))
        self.assertEqual(D(trade['quantity']),D('2.38'))
        self.assertEqual(D(trade['net_usd']),D('-1.67'))
        self.assertEqual(reviewer.inspect(r,s,p)['status'],'signals_and_financial_bindings_verified')

    def test_short_protection_uses_ask_and_first_stop(self):
        s,p,t=fixture()
        p[t[47]][1].update(open=105.2,high=116,low=105.2,close=105.2)
        r=study.simulate(s,p,policy='failed_break',slippage=D('.25'))
        self.assertEqual(r['trades'][0]['reason'],'stop_loss')
        self.assertEqual(D(r['trades'][0]['exit_fill']),D(115))
        reviewer.inspect(r,s,p)

    def test_missing_exact_entry_rejects_without_late_fill(self):
        s,p,t=fixture();del p[t[31]]
        r=study.simulate(s,p,policy='breakout',slippage=D('.25'))
        self.assertEqual(r['entries'],0)
        self.assertIn('missing_fill_minute',[v['reason'] for v in r['rejected']])
        reviewer.inspect(r,s,p)

    def test_missing_held_path_never_gets_full_net(self):
        s,p,t=fixture();del p[t[35]]
        r=study.simulate(s,p,policy='breakout',slippage=D('.25'))
        self.assertIsNone(study.metrics(r)['full_net_usd'])
        self.assertTrue(r['trades'][0]['path_unresolved'])
        reviewer.inspect(r,s,p)

    def test_null_and_unknown_policy(self):
        s,p,_=fixture()
        r=study.simulate(s,p,policy='breakout',slippage=D('.25'),null_control=True)
        self.assertEqual((r['entries'],r['net_equity_usd']),(0,'0'))
        reviewer.inspect(r,s,p)
        with self.assertRaises(ValueError):study.plans_for(s,p,'not_registered')

    def test_signal_and_money_mutations_are_rejected(self):
        s,p,_=fixture()
        good=study.simulate(s,p,policy='breakout',slippage=D('.25'))
        for mode in ('signal','money','early_stop'):
            bad=deepcopy(good);quotes=deepcopy(p)
            if mode=='signal':next(d for d in bad['decisions'] if d['side']=='BUY')['side']='SELL'
            elif mode=='money':bad['trades'][0]['net_usd']='99'
            else:quotes[bad['trades'][0]['entry_time_msc']+M][0]['low']=1
            with self.assertRaises(ValueError):reviewer.inspect(bad,s,quotes)

    def test_ny_dst_and_holdout_rejected(self):
        a=fixture('2022-01-04')[2][0];b=fixture('2022-07-05')[2][0]
        self.assertEqual(datetime.fromtimestamp(a/1000,ZoneInfo('UTC')).hour,14)
        self.assertEqual(datetime.fromtimestamp(b/1000,ZoneInfo('UTC')).hour,13)
        with self.assertRaisesRegex(ValueError,'holdout_closed'):
            runner.load_year(Path('not_read'),2025,lambda *a,**k:None)


if __name__=='__main__':unittest.main()

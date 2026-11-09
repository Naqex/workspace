from copy import deepcopy
from datetime import datetime,timedelta,timezone
from decimal import Decimal as D
from pathlib import Path
import sys,time,unittest
from zoneinfo import ZoneInfo

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import nasdaq_opening5_orb as study
ROOT=Path(__file__).resolve().parents[3]
M=60000


def update(row,**values):row.update({k:float(v) for k,v in values.items()})


def fixture(days=('2019-01-02',),*,side='BUY',halfday=False):
    sessions,pairs={},{}
    for day in days:
        begin=int(datetime.fromisoformat(day).replace(hour=9,minute=30,tzinfo=ZoneInfo('America/New_York')).timestamp()*1000)
        stamps=list(range(begin,begin+(210 if halfday else 390)*M,M));sessions[day]=stamps
        for t in stamps:
            pairs[t]=tuple(dict(timestamp=t,open=float(D(1000)+offset),high=float(D('1000.1')+offset),
                low=float(D('999.9')+offset),close=float(D(1000)+offset),volume=0) for offset in [D(0),D('.2')])
        update(pairs[stamps[0]][0],high=1002,low=998)
        update(pairs[stamps[0]][1],high='1002.2',low='998.2')
        final=D(1001) if side=='BUY' else D(999) if side=='SELL' else D(1000)
        for row,offset in zip(pairs[stamps[4]],[D(0),D('.2')]):
            update(row,open=D(1000)+offset,close=final+offset,high=max(D(1000),final)+offset,low=min(D(1000),final)+offset)
        for row,offset in zip(pairs[stamps[-1]],[D(0),D('.2')]):
            update(row,open=D(1005)+offset,high=D(1006)+offset,low=D(1004)+offset,close=D(1005)+offset)
    start=int(datetime.fromisoformat(days[0]).replace(tzinfo=timezone.utc).timestamp()*1000)
    end=int((datetime.fromisoformat(days[-1])+timedelta(days=1)).replace(tzinfo=timezone.utc).timestamp()*1000)
    return sessions,pairs,start,end


def run(f,scenario='reference',null=False):
    sessions,pairs,start,end=f
    return study.simulate(sessions,pairs,start=start,end=end,scenario=scenario,null_control=null)


class Opening5Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):study.core.bind_core(ROOT/'projects/trader/foundation_v2')

    def test_entry_delay_stop_target_budget_and_cash(self):
        f=fixture();sessions,pairs,start,end=f;stamps=next(iter(sessions.values()));r=run(f);t=r['trades'][0]
        self.assertEqual(t['decision_time_msc'],stamps[4]+M)
        self.assertEqual(t['entry_time_msc'],stamps[6])
        self.assertEqual(t['entry_quote'],D('1000.2'));self.assertEqual(t['stop'],D(998))
        self.assertEqual(t['take_profit'],D('1022.2'));self.assertEqual(t['quantity'],D('9.25'))
        self.assertLessEqual(t['planned_stop_risk_usd'],25)
        self.assertEqual(t['reason'],'scheduled_cash_exit');self.assertEqual(t['exit_bar_open_msc'],stamps[-1])
        self.assertEqual(t['net_usd'],D('39.78'));self.assertEqual(r['balance_usd'],D('10039.78'))
        self.assertEqual(r['account_state'],'known_flat');self.assertFalse(r['execution_authorized'])

    def test_first_stop_and_take_profit_and_gap_use_native_ordering(self):
        for mode,reason,price in [('stop','stop_loss',D(998)),('take','take_profit',D('1022.2')),('gap','stop_loss_gap',D(990))]:
            f=fixture();sessions,pairs,_,_=f;at=next(iter(sessions.values()))[8]
            if mode=='stop':update(pairs[at][0],low=997)
            elif mode=='take':update(pairs[at][0],high=1023)
            else:
                for row,offset in zip(pairs[at],[D(0),D('.2')]):update(row,open=D(990)+offset,high=D(991)+offset,low=D(989)+offset,close=D(990)+offset)
            trade=run(f)['trades'][0]
            self.assertEqual((trade['reason'],trade['exit_quote']),(reason,price))
            if mode=='stop':self.assertEqual(trade['net_usd'],D('-24.98'))
            if mode=='gap':self.assertLess(trade['net_usd'],-25)

    def test_short_stop_is_ask_only(self):
        f=fixture(side='SELL');sessions,pairs,_,_=f;at=next(iter(sessions.values()))[8]
        update(pairs[at][0],high='1001.9');update(pairs[at][1],high=1002)
        t=run(f)['trades'][0]
        self.assertEqual(t['side'],'SELL');self.assertEqual(t['reason'],'stop_loss')
        self.assertEqual(t['exit_quote'],D(1002));self.assertEqual(t['quantity'],D('9.99'))

    def test_ambiguous_protection_freezes_later_sessions_and_equity_is_unknown(self):
        f=fixture(('2019-01-02','2019-01-03'));sessions,pairs,_,_=f;at=next(iter(sessions.values()))[8]
        update(pairs[at][0],high=1023,low=997)
        r=run(f)
        self.assertEqual(r['closed_trades'],0);self.assertEqual(r['entries'],1)
        self.assertEqual(r['unknown_position']['reason'],'ambiguous_SL_TP_same_M1')
        self.assertEqual(r['session_rows'][1]['status'],'blocked_unknown_exposure')
        self.assertIsNone(r['net_equity_usd']);self.assertIsNone(r['funding_total_usd'])
        self.assertEqual(r['balance_usd'],10000)

    def test_missing_held_minute_is_unknown_but_missing_entry_never_fills_late(self):
        for index,status in [(7,'unknown_exposure'),(6,'missing_or_crossed_exact_entry')]:
            f=fixture(('2019-01-02','2019-01-03'));sessions,pairs,_,_=f;del pairs[next(iter(sessions.values()))[index]]
            r=run(f);self.assertEqual(r['session_rows'][0]['status'],status)
            if index==7:self.assertEqual(r['closed_trades'],0)
            else:self.assertEqual(r['closed_trades'],1)

    def test_halfday_exit_and_future_exit_bar_cannot_create_protective_fill(self):
        f=fixture(('2019-11-29',),halfday=True);sessions,pairs,_,_=f;at=next(iter(sessions.values()))[-1]
        update(pairs[at][0],high=2000,low=1)
        r=run(f);trade=r['trades'][0]
        self.assertEqual(trade['reason'],'scheduled_cash_exit')
        self.assertEqual(datetime.fromtimestamp(trade['exit_bar_open_msc']/1000,study.NY).strftime('%H:%M'),'12:59')

    def test_missing_opening_and_doji_skip_without_account_unknown(self):
        for mode in ['missing','doji']:
            f=fixture(side='NONE' if mode=='doji' else 'BUY');sessions,pairs,_,_=f
            if mode=='missing':del pairs[next(iter(sessions.values()))[1]]
            r=run(f);self.assertEqual(r['entries'],0);self.assertEqual(r['net_equity_usd'],0)
            self.assertEqual(r['account_state'],'known_flat')

    def test_future_price_mutation_does_not_change_opening_signal(self):
        f=fixture();sessions,pairs,_,_=f;stamps=next(iter(sessions.values()))
        before=study.opening_plan(stamps,pairs);changed=deepcopy(pairs);del changed[stamps[100]]
        self.assertEqual(study.opening_plan(stamps,changed),before)
        self.assertEqual(run(f,null=True)['net_equity_usd'],0)

    def test_min_margin_and_step_with_stress_costs(self):
        f=fixture();reference=run(f);stress=run(f,scenario='stress')
        self.assertLess(stress['trades'][0]['quantity'],reference['trades'][0]['quantity'])
        self.assertEqual(stress['trades'][0]['quantity']%D('.01'),0)
        self.assertLessEqual(stress['trades'][0]['planned_stop_risk_usd'],25)
        sessions,pairs,_,_=f
        for pair in pairs.values():
            for row in pair:
                for k in ['open','high','low','close']:row[k]+=60_000
        r=run(f);self.assertEqual(r['entries'],0);self.assertEqual(r['session_rows'][0]['status'],'min_max_quantity_margin_or_cash')

    def test_batch_validates_once_and_matches_individual_books(self):
        from unittest.mock import patch
        f=fixture();sessions,pairs,start,end=f;original=deepcopy(f)
        with patch.object(study,'validate_inputs',wraps=study.validate_inputs) as validate:
            batch=study.simulate_batch(sessions,pairs,start=start,end=end)
            self.assertEqual(validate.call_count,1)
        for r in batch['results']:
            expected=run(f,r['scenario'],r['null_control']);omit={'wall_seconds','cpu_seconds'}
            self.assertEqual({k:v for k,v in r.items() if k not in omit},{k:v for k,v in expected.items() if k not in omit})
        self.assertEqual(f,original)

    def test_clock_holdout_deadline_and_summary_guard(self):
        f=fixture();sessions,pairs,start,end=f
        with self.assertRaisesRegex(ValueError,'holdout'):
            study.simulate(sessions,pairs,start=start,end=1767225600000,scenario='reference')
        with self.assertRaises(TimeoutError):
            study.simulate(sessions,pairs,start=start,end=end,scenario='reference',deadline=time.perf_counter()-1)
        with self.assertRaisesRegex(ValueError,'eight'):
            study.summarize(study.simulate_batch(sessions,pairs,start=start,end=end)['results'])

    def test_summary_keeps_unknown_distinct_from_economic_rejection(self):
        results=[]
        for year in [2019,2022]:
            for scenario in ['reference','stress']:
                for null in [False,True]:
                    results.append(dict(year=year,scenario=scenario,null_control=null,candidate=study.CANDIDATE,
                        execution_authorized=False,prop_evaluated=False,broker_calls=0,model_calls=0,
                        entries=0 if null else 100,closed_trades=0 if null else 100,
                        balance_usd=D(10000) if null else D(10100),net_equity_usd=D(0) if null else D(100),account_state='known_flat'))
        self.assertTrue(study.summarize(results)['retained_for_further_research'])
        changed=deepcopy(results);ix=next(i for i,r in enumerate(changed) if r['year']==2022 and r['scenario']=='stress' and not r['null_control'])
        changed[ix].update(account_state='unknown_exposure',net_equity_usd=None)
        verdict=study.summarize(changed)
        self.assertFalse(verdict['retained_for_further_research'])
        self.assertEqual(verdict['year_gates'][1]['verdict'],'inconclusive_unknown_exposure')
        changed=deepcopy(results);changed[ix]['net_equity_usd']=D(-1)
        self.assertEqual(study.summarize(changed)['year_gates'][1]['verdict'],'not_retained')


if __name__=='__main__':unittest.main()

from datetime import date,datetime,timedelta,timezone
from decimal import Decimal as D
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_nasdaq_opening5_orb import fixture,update
from test_nasdaq_opening5_bounds import hours_for
import nasdaq_noise14 as study


def data(extra_warmup=False,second_day=False):
    dev=date(2019,1,2);past=[];d=dev-timedelta(days=1)
    while len(past)<(15 if extra_warmup else 14):
        if d.weekday()<5 and d.isoformat() not in ('2018-12-25','2019-01-01'):past.append(d.isoformat())
        d-=timedelta(days=1)
    days=tuple(reversed(past))+('2019-01-02',)+(('2019-01-03',) if second_day else ())
    f=fixture(days)
    for day,stamps in f[0].items():
        update(f[1][stamps[29]][0],close=1011 if day>='2019-01-02' else 1010,high=1012)
        update(f[1][stamps[29]][1],close='1011.2' if day>='2019-01-02' else '1010.2',high='1012.2')
        if day<'2019-01-02':
            for row,offset in zip(f[1][stamps[-1]],(D(0),D('.2'))):
                update(row,open=1000+offset,high=1001+offset,low=999+offset,close=1000+offset)
    start=int(datetime(2019,1,2,tzinfo=timezone.utc).timestamp()*1000)
    return f,start


def plans(f,start):return study.prepare_plans(f[0],f[1],evaluation_start=start)
def run(f,start,conditional=False,null=False,hours=None):
    return study.simulate(plans(f,start),f[1],hours_for(f[1]) if hours is None else hours,
                          scenario='stress',conditional=conditional,null_control=null)


class Noise14Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        study.source.core.bind_core(Path(__file__).resolve().parents[3]/'projects/trader/foundation_v2')

    def test_bands_prior14_first_signal_latency_and_no_warmup_trades(self):
        f,start=data();p=plans(f,start)
        self.assertEqual(list(p),['2019-01-02'])
        first=p['2019-01-02']['first_signal'];stamps=f[0]['2019-01-02']
        self.assertEqual((first['lower'],first['upper']),(D(990),D(1010)))
        self.assertEqual(first['known_at_msc'],stamps[29]+60000)
        self.assertEqual(first['fill_at_msc'],stamps[29]+120000)
        r=run(f,start);t=r['trades'][0]
        self.assertEqual(t['entry_time_msc'],stamps[31]);self.assertEqual(t['side'],'BUY')
        self.assertLessEqual(t['planned_stop_risk_usd'],25)
        self.assertEqual(r['entries'],1);self.assertEqual(t['stop'],990)
        self.assertEqual(r['net_lower_usd'],r['net_upper_usd'])
        self.assertFalse(r['execution_authorized'])

    def test_equality_is_not_breakout(self):
        f,start=data();at=f[0]['2019-01-02'][29]
        update(f[1][at][0],close=1010)
        self.assertIsNone(plans(f,start)['2019-01-02']['first_signal'])

    def test_missing_required_slot_does_not_backfill_older_day(self):
        f,start=data(extra_warmup=True);warmup=list(f[0])[:-1]
        del f[1][f[0][warmup[-1]][29]]
        p=plans(f,start)['2019-01-02']
        self.assertEqual(p['previous_sessions'],14)
        self.assertFalse(p['decisions'][0]['available'])
        self.assertIsNone(p['first_signal'])

    def test_future_day_prices_cannot_change_prior_plan(self):
        f,start=data(second_day=True);before=plans(f,start)['2019-01-02']
        for stamp in f[0]['2019-01-03']:
            for row in f[1][stamp]:
                for k in ('open','high','low','close'):row[k]+=1000
        self.assertEqual(before,plans(f,start)['2019-01-02'])

    def test_first_attempt_is_not_replaced_after_missing_entry(self):
        f,start=data();ss=f[0]['2019-01-02'];del f[1][ss[31]]
        update(f[1][ss[59]][0],close=999,low=998)
        update(f[1][ss[59]][1],close='999.2',low='998.2')
        r=run(f,start)
        self.assertEqual(r['entries'],0)
        self.assertEqual(r['session_rows'][0]['status'],'missing_or_crossed_exact_entry')

    def test_opposite_exit_has_delay_and_does_not_reverse(self):
        f,start=data();ss=f[0]['2019-01-02']
        update(f[1][ss[59]][0],close=999,low=998)
        update(f[1][ss[59]][1],close='999.2',low='998.2')
        r=run(f,start);t=r['trades'][0]
        self.assertEqual(t['reason'],'opposite_band')
        self.assertEqual(t['terminal_msc'],ss[61]+60000)
        self.assertEqual(r['entries'],1)

    def test_halfday_has_only_six_decisions_and_correct_terminal(self):
        f,start=data();day='2019-01-02';ss=f[0][day]
        f[0][day]=ss[:210]
        for at in ss[210:]:del f[1][at]
        p=plans(f,start)[day]
        self.assertEqual(len(p['decisions']),6)
        self.assertEqual(p['terminal_msc'],ss[209])
        self.assertEqual(run(f,start)['trades'][0]['terminal_msc'],ss[209]+60000)

    def test_missing_held_minute_freezes_exact_future_days(self):
        f,start=data(second_day=True);ss=f[0]['2019-01-02'];del f[1][ss[33]]
        r=run(f,start)
        self.assertIsNone(r['net_lower_usd'])
        self.assertEqual(r['account_state'],'unknown')
        self.assertEqual(r['session_rows'][1]['status'],'blocked_unknown_exposure')

    def test_conditional_no_gap_matches_exact_and_gap_keeps_worse_branch(self):
        f,start=data();a=run(f,start);b=run(f,start,conditional=True)
        self.assertEqual(a['trades'],b['trades'])
        ss=f[0]['2019-01-02'];hs=hours_for(f[1]);at=ss[33];del f[1][at]
        hs[at//3600000*3600000][0]['low']=900
        r=run(f,start,conditional=True,hours=hs)
        self.assertLess(r['net_lower_usd'],-25)
        self.assertGreater(r['net_upper_usd'],0)
        self.assertEqual(r['uncertain_trades'],1)

    def test_short_uses_Ask_stop_and_open_gap_precedes_scheduled_exit(self):
        f,start=data();ss=f[0]['2019-01-02'];at=ss[33]
        position=dict(side='SELL',stop=D(1002),entry_time_msc=at)
        plan=dict(terminal_msc=at,terminal_reason='scheduled_cash_exit')
        for row,offset in zip(f[1][at],(D(0),D('.2'))):
            update(row,open=1003+offset,high=1004+offset,low=1003+offset,close=1003+offset)
        r=study.exit_bounds(position,f[1],{},plan,conditional=False)
        self.assertEqual((r['lower'],r['reason']),(D('1003.2'),'stop_loss_gap'))

    def test_missing_terminal_cannot_be_synthesized_from_H1(self):
        f,start=data();del f[1][f[0]['2019-01-02'][-1]]
        r=run(f,start,conditional=True)
        self.assertIsNone(r['net_lower_usd']);self.assertEqual(r['account_state'],'unknown')

    def test_null_never_enters_or_needs_H1(self):
        f,start=data();del f[1][f[0]['2019-01-02'][33]]
        r=run(f,start,conditional=True,null=True,hours={})
        self.assertEqual((r['entries'],r['net_lower_usd'],r['net_upper_usd']),(0,0,0))

    def test_stop_rounding_and_margin_rejection(self):
        f,start=data()
        for day,ss in f[0].items():
            if day<'2019-01-02':
                update(f[1][ss[29]][0],close='1010.0004')
                update(f[1][ss[29]][1],close='1010.2004')
        self.assertEqual(run(f,start)['trades'][0]['stop'],D('989.999'))
        f,start=data()
        for pair in f[1].values():
            for row in pair:
                for k in ('open','high','low','close'):row[k]+=99000
        r=run(f,start)
        self.assertEqual(r['entries'],0)
        self.assertEqual(r['session_rows'][0]['status'],'min_max_quantity_or_margin')

    def test_H1_must_contain_observed_prices(self):
        f,start=data();ss=f[0]['2019-01-02'];hs=hours_for(f[1]);at=ss[33]
        del f[1][at];hs[at//3600000*3600000][0]['low']=1000
        with self.assertRaisesRegex(ValueError,'excludes_or_crosses'):run(f,start,conditional=True,hours=hs)

    def test_DST_decision_clock_follows_New_York(self):
        f=fixture(('2019-03-08','2019-03-11'));p=plans(f,0)
        utc=lambda day:datetime.fromtimestamp(p[day]['decisions'][0]['known_at_msc']/1000,timezone.utc).hour
        self.assertEqual((utc('2019-03-08'),utc('2019-03-11')),(15,14))

    def test_cash_interval_must_not_choose_entry_branch(self):
        f,start=data(second_day=True);pp=plans(f,start);first=f[0]['2019-01-02'];second=f[0]['2019-01-03']
        # Isolate the account gate with two specified plans and a large conditional gap.
        import copy
        pp['2019-01-03']=copy.deepcopy(pp['2019-01-02'])
        shift=second[0]-first[0]
        pp['2019-01-03']['terminal_msc']+=shift
        for k in ('fill_at_msc','known_at_msc'):pp['2019-01-03']['first_signal'][k]+=shift
        for k in ('lower','upper'):pp['2019-01-03']['first_signal'][k]+=40000
        for at in second:
            for row in f[1][at]:
                for k in ('open','high','low','close'):row[k]+=40000
        hs=hours_for(f[1]);at=first[33];del f[1][at];hs[at//3600000*3600000][0]['low']=1
        r=study.simulate(pp,f[1],hs,scenario='stress',conditional=True)
        self.assertEqual(r['unknown']['reason'],'cash_interval_changes_entry_eligibility')
        self.assertIsNone(r['net_upper_usd'])


if __name__=='__main__':unittest.main()

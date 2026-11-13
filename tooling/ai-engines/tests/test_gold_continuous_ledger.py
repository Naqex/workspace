from datetime import datetime
from decimal import Decimal as D
from pathlib import Path
import random
import sys
import unittest
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from gold_continuous_ledger import (
    START,END,UTC,Source,StreamSummary,Metrics,floating,price_units,build_episode,boundaries,
    advance_cash_reset,native_context,lifecycle_probe,utc,LedgerAccount,evaluate,PointAwareQualityPath,
)
from gold_continuous_b1 import GoldPrefix
from run_gold_continuous_b2 import output_lock

class LedgerTests(unittest.TestCase):
    def test_two_writers_cannot_share_output(self):
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder)
            with output_lock(out):
                with self.assertRaises(FileExistsError):
                    with output_lock(out):pass
            self.assertFalse((out/'RUNNING.lock').exists())
    def test_reset_audit_records_known_cash_with_no_fresh_quote(self):
        audit=[];a=LedgerAccount(START,END,on_reset=audit.append)
        a.cash=4999900;a.roll((START+23*3600)*1000,held=True)
        self.assertEqual(audit[0]['daily_reference_balance'],'49999.00')
        self.assertEqual(audit[0]['current_cash_balance'],'49999.00')
        self.assertEqual(audit[0]['reset_quote_state'],'NO_FRESH_QUOTE_AT_RESET')
    def test_point_after_conditional_peak_keeps_full_envelope_drawdown(self):
        path=PointAwareQualityPath(START,END)
        path.mark(START, D(50000),D(1000),conditional=True)
        path.mark(START+1,D(49000),D(0))
        self.assertEqual(path.points['peak_dd'],1000)
        self.assertEqual(path.envelope['peak_dd'],2000)

    def test_cent_rounding_matches_native_both_sides(self):
        rng=random.Random(17)
        for side in ('BUY','SELL'):
            for q in (1,7,11,17,99):
                engine=GoldPrefix('125');at=START
                engine.pending=dict(time=at,signal=side,distance='100',quantity=str(D(q)/100),status='queued')
                engine.fill(at,D('1000'))
                entry=int(engine.position.entry_fill*1000)
                for _ in range(20):
                    bid=rng.randrange(950000,1050000)
                    self.assertEqual(floating(side,q,entry,bid),int(engine.net(D(bid)/1000)*100))

    def test_reset_without_price_then_fresh_quote_uses_new_anchor(self):
        s,a,p=native_context();at=START+23*3600*1000/1000
        # Jan1 23UTC is Jan2 00Prague; no fresh quote for next60minutes.
        when=(START+23*3600)*1000
        r=advance_cash_reset(s,a,p,when,D('51000'),positions=1)
        a,p,resume=r['attempt'],r['phase'],r['resume_state']
        self.assertEqual(p.daily_anchor,51000)
        self.assertEqual(p.virtual_time_utc,utc(when/1000))
        self.assertEqual(p.last_event_sequence,1)
        self.assertEqual(resume['prop_lifecycle']['reset_quote_state'],'NO_FRESH_QUOTE_AT_RESET')
        r=lifecycle_probe(s,a,p,when/1000+3600,balance='51000',floating='-2500.01',positions=1,
            quality='full_for_declared_model',resume=resume)
        self.assertEqual(r['attempt'].status,'failed_breach')
        self.assertEqual(r['objectives']['money']['daily_loss']['reference'],'51000')
        self.assertTrue(r['resume_state']['prop_lifecycle']['price_coverage_uncertain'])

    def test_reset_bridge_rejects_skipped_boundary(self):
        s,a,p=native_context()
        with self.assertRaises(ValueError):advance_cash_reset(s,a,p,(START+48*3600)*1000,D(50000),positions=1)

    def test_phase2_is_started_after_native_next_phase_transition(self):
        account=LedgerAccount(START,END)
        account.a=account.a.model_copy(update={'status':'phase_passed'})
        account.phase=account.phase.model_copy(update={'balance':D(55000),'equity':D(55000),'high_water_mark':D(55000)})
        account.cash=5500000
        account.next_phase()
        self.assertEqual(account.a.status,'running')
        self.assertEqual(account.phase.phase_index,2)
        self.assertEqual(account.cash,5000000)
        self.assertEqual(account.phase.qualifying_days,0)
        account.mark(START*1000,0,positions=0)

    def test_entry_cost_breach_latches_before_later_segments(self):
        a=LedgerAccount(START,END);a.cash=a.anchor=4500010
        a.phase=a.phase.model_copy(update=dict(balance=D('45000.10'),equity=D('45000.10'),daily_anchor=D('45000.10')))
        episode=dict(status='open',entry=START*1000+1000,exit=None,decision=START*1000,side='BUY',q=1,
            gap_count=0,unordered_stop_minutes=0,events=[dict(kind='entry',at=START*1000+1000,net=-100)])
        self.assertEqual(a.consume(episode,(40,40)),'breach')
        self.assertEqual(a.a.status,'failed_breach')
        self.assertEqual(a.breach['label'],'M1_entry_point')
        self.assertEqual(a.result()['floating_usd'],'-1.00')

    def test_terminal_floating_uses_first_breach_not_prior_segment(self):
        a=LedgerAccount(START,END)
        at=START*1000+1000;s=StreamSummary();s.add(-100,at);s.add(-250001,at+500)
        episode=dict(status='open',entry=at,exit=None,decision=START*1000,side='BUY',q=1,
            events=[dict(kind='entry',at=at,net=-100),dict(kind='segment',start=at,end=at+1000,p=s.dump(),e=s.dump())])
        self.assertEqual(a.consume(episode,(40,40)),'breach')
        self.assertEqual(a.result()['floating_usd'],'-2500.01')
        self.assertEqual(a.result()['marked_net_usd'],'-2500.01')

    def test_ordered_summary_matches_full_marks_and_stop_prefix(self):
        rng=random.Random(69)
        cash=5000000;anchor=5000000;full=Metrics();combined=Metrics()
        values=[rng.randrange(-100000,200000) for _ in range(1000)]
        for index,v in enumerate(values):full.point(v,cash,anchor,index)
        for i in range(0,len(values),100):
            s=StreamSummary()
            for j,v in enumerate(values[i:i+100],i):s.add(v,j)
            combined.apply(s.dump(),cash,anchor)
        self.assertEqual(full.dump(),combined.dump())
        s=StreamSummary()
        for i,v in enumerate((10,30,-5,8,-20,100,-40)):s.add(v,i)
        low=next(x for x in s.lows if x[0]<-10)
        self.assertEqual(low,[-20,4,30,50])

    def test_daily_minimum_must_be_split_at_cash_flow(self):
        metric=Metrics()
        before=StreamSummary();before.add(-10000,1)
        after=StreamSummary();after.add(-8000,3)
        metric.apply(before.dump(),5000000,5000000)
        metric.apply(after.dump(),4996000,5000000)
        self.assertEqual(metric.daily,12000)
        self.assertNotEqual(metric.daily,10000)

    def test_buy_only_reselects_entry_after_skipped_short(self):
        data=Source()
        for i in range(15):
            data.add(START+i*60,(1000000,1001000,970000 if i==1 else 999000,1000000))
        frames=[dict(at=START+60,signal='BUY',distance='20',difference='1'),
            dict(at=START+300,signal='SELL',distance='20',difference='-1'),
            dict(at=START+600,signal='BUY',distance='20',difference='1')]
        episodes=[build_episode(data,frames,i,125,[]) for i in range(3)]
        ledger=dict(episodes={125:episodes})
        both=evaluate(ledger,START,START+900,125,challenge=False)
        long=evaluate(ledger,START,START+900,125,variant='BUY-Only',challenge=False)
        self.assertEqual([d['side'] for d in both['decisions']],['BUY','SELL'])
        self.assertEqual([d['side'] for d in long['decisions']],['BUY','BUY'])

    def test_price_parser_rejects_offgrid_and_invalid(self):
        self.assertEqual(price_units('1234.5670'),1234567)
        for bad in ('NaN','0','12.0001','-1','1e3'):
            with self.assertRaises(ValueError):price_units(bad)

    def test_potential_episode_includes_opposite_flat_entry_not_global_filter(self):
        data=Source()
        for i in range(12):data.add(START+i*60,(1000000,1001000,999000,1000000))
        frames=[dict(at=START+60,signal='BUY',distance='20',difference='1'),
            dict(at=START+300,signal='SELL',distance='20',difference='-1'),
            dict(at=START+600,signal='BUY',distance='20',difference='1')]
        a=build_episode(data,frames,0,125,[]);b=build_episode(data,frames,1,125,[])
        self.assertEqual(a['exit'],(START+300)*1000)
        self.assertEqual(b['entry'],(START+300)*1000)
        ledger=dict(episodes={125:[a,b]})
        full=evaluate(ledger,START,START+700,125,challenge=False)
        fresh=evaluate(ledger,START+120,START+700,125,challenge=False)
        self.assertEqual(full['entries'],1)
        self.assertEqual(fresh['entries'],1)
        self.assertEqual(full['decisions'][0]['side'],'BUY')
        self.assertEqual(fresh['decisions'][0]['side'],'SELL')

    def test_stop_minute_no_postexit_extrema(self):
        data=Source()
        data.add(START+60,(1000000,1500000,1,1000000))
        frames=[dict(at=START+60,signal='BUY',distance='10',difference='1')]
        e=build_episode(data,frames,0,125,[])
        marks=[v for v in e['events'] if v['kind']=='segment']
        self.assertEqual(marks[0]['p'],marks[0]['e'])
        self.assertEqual(e['events'][-1]['reason'],'stop_loss')

    def test_future_outcome_not_used_before_cutoff(self):
        data=Source()
        for i in range(20):data.add(START+i*60,(1000000,1001000,999000,1000000))
        frames=[dict(at=START+60,signal='BUY',distance='20',difference='1'),
            dict(at=START+900,signal='SELL',distance='20',difference='-1')]
        cut=(START+600)*1000
        episode=build_episode(data,frames,0,125,[(cut,'cut',1)])
        result=evaluate(dict(episodes={125:[episode]}),START,START+600,125,challenge=False)
        self.assertEqual(result['closed'],0)
        self.assertEqual(result['entries'],1)
        self.assertLess(D(result['floating_usd']),0)

    def test_gap_events_do_not_precede_earlier_reset_and_cut(self):
        data=Source()
        data.add(START+60,(1000000,1001000,999000,1000000))
        data.add(START+3600,(1000000,1001000,999000,1000000))
        frames=[dict(at=START+60,signal='BUY',distance='20',difference='1')]
        cut=(START+1800)*1000
        episode=build_episode(data,frames,0,125,[(cut,'cut',1)])
        ordered=[e.get('at',e.get('end')) for e in episode['events']]
        self.assertEqual(ordered,sorted(ordered))
        r=evaluate(dict(episodes={125:[episode]}),START,START+1800,125,challenge=False)
        self.assertEqual(r['closed'],0)
        self.assertLess(D(r['floating_usd']),0)

if __name__=='__main__':unittest.main()

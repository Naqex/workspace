from datetime import date
from pathlib import Path
import json,sys,tempfile,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from xau_a_validation_source import Calendar,Quotes,END,REC
from xau_a_validation import (ms,Case,native_terminal,qsize,build_ledger,evaluate,fee,swap)
from xau_h1_execution import economics,CELLS,path_for


def fixture_trade(at,exit,side='BUY',p0=2000000,p1=2010000,stop=1990000):
    t=dict(signal_id=str(at),recipe='H1A_ASIA',decision_msc=at,entry_msc=at,exit_msc=exit,day='2023-01-03',side=side,
        entry_price_units=p0,exit_price_units=p1,stop_units=stop,natural_sl_usd_per_oz=abs(p0-stop)/1000,
        reason='TIME_48H',entry_quote_index=0,exit_quote_index=1)
    t['sizing_costs']={str(risk):{c:economics(dict(t,risk_usd=risk,ounces=qsize(t,risk)),c) for c in ('SYM_FLAT','ASYM_FLAT')} for risk in (150,200)}
    return t


class AValidationTests(unittest.TestCase):
    def test_calendar_black_friday_and_good_friday(self):
        c=Calendar(Path(__file__).resolve().parents[3]/'planning/research/XAUUSD-A-SESSION-CALENDAR-20261114.json')
        self.assertEqual(c.deadline(ms('2023-11-24T09:00:00')),(ms('2023-11-24T17:00:00'),'HOLIDAY_FLAT'))
        self.assertEqual(c.deadline(ms('2023-04-05T08:00:00')),(ms('2023-04-06T20:30:00'),'HOLIDAY_FLAT'))
        self.assertFalse(c.allowed(ms('2023-04-07T09:00:00')))
        self.assertEqual(c.deadline(ms('2024-12-31T15:00:00'))[0],ms('2024-12-31T17:00:00'))

    def test_reader_2025_closed(self):
        with self.assertRaisesRegex(ValueError,'2025'):Quotes({}).hour(END)

    def test_calendar_ordinary_rollover_does_not_force_exit(self):
        c=Calendar(Path(__file__).resolve().parents[3]/'planning/research/XAUUSD-A-SESSION-CALENDAR-20261114.json')
        at=ms('2023-06-20T09:00:00')
        # Juneteenth has passed, and no ordinary one-hour break is a holiday.
        self.assertEqual(c.deadline(at),(at+48*3600000,'TIME_48H'))

    def test_sizing_is_rounded_not_scaled(self):
        t=fixture_trade(1,2,stop=1991000)
        self.assertEqual(qsize(t,150),16);self.assertEqual(qsize(t,200),22)

    def test_native_pass_min_days_and_breach(self):
        start=ms('2023-01-01');at=ms('2023-01-10')
        days={'2023-01-03','2023-01-04','2023-01-05','2023-01-06'}
        self.assertEqual(native_terminal(1,55000000,0,50000000,days,at,start,0,'phase_pass'),'phase_pass')
        self.assertEqual(native_terminal(2,52500000,0,50000000,days,at,start,0,'complete_pass'),'complete_pass')
        self.assertIsNone(native_terminal(1,55000000,0,50000000,set(),at,start,0,None))
        self.assertEqual(native_terminal(1,44999999,0,50000000,set(),at,start,0,'breach'),'breach')

    def test_start_flat_does_not_inherit_old_position(self):
        at=ms('2023-01-03T09:00:00');t=fixture_trade(at,at+3600000)
        c=Case(at+1,at+7200000,150,'SYM_FLAT')
        c.consume(dict(kind='entry',at=[at,0],trade=0,quote=[at,2000000,2000100]),[t])
        c.consume(dict(kind='exit',at=[at+3600000,0],trade=0,quote=[at+3600000,2010000,2010100]),[t])
        self.assertFalse(c.active);self.assertEqual(c.balance,50000000)

    def test_open_swap_and_slip_stay_out_of_balance_reset(self):
        at=ms('2023-01-04T21:00:00');t=fixture_trade(at,at+4*3600000)
        c=Case(at,at+5*3600000,150,'SYM_FLAT',rolling=False)
        q=[at,1999900,2000000]
        c.consume(dict(kind='entry',at=[at,0],trade=0,quote=q),[t]);balance=c.balance
        c.consume(dict(kind='swap',at=[at+3600000,-1],trade=0,mult=3,quote=q),[t])
        self.assertEqual(c.balance,balance)
        c.consume(dict(kind='reset',at=[at+2*3600000,-1],trade=None,quote=q),[t])
        self.assertEqual(c.anchor,balance)
        self.assertEqual(c.floating([t],q),-1500-3000-18000)

    def test_equal_limit_is_touch_not_breach(self):
        at=ms('2023-01-03');c=Case(at,at+1,150,'SYM_FLAT');c.balance=47500000
        c.point([], [at,0],None)
        self.assertIsNone(c.breach);self.assertTrue(c.dump()['daily_limit_touched'])

    def test_phase_pass_resets_capital_and_rejects_same_decision(self):
        at=ms('2023-01-10T09:00:00');c=Case(ms('2023-01-01'),END,150,'SYM_FLAT')
        c.days={'2023-01-03','2023-01-04','2023-01-05','2023-01-06'};c.balance=55000000
        c.point([], [at,0],None)
        self.assertEqual(c.phase,2);self.assertEqual(c.balance,50000000);self.assertFalse(c.days)
        t=fixture_trade(at,at+3600000)
        c.consume(dict(kind='entry',at=[at,0],trade=0,quote=[at,2000000,2000100]),[t])
        self.assertFalse(c.active);self.assertEqual(c.rejections,1)

    def test_first_prefix_loss_witness_and_breach_before_pass(self):
        at=ms('2023-01-03T09:00:00');t=fixture_trade(at,at+3600000)
        c=Case(at,END,150,'SYM_FLAT');c.active={0};c.swaps={0:0}
        c.consume(dict(kind='segment',at=[at+10,1],summaries={'0':{'150':dict(min=-2600000,max=6000000,dd=8600000,last=5000000,lows=[[-100,[at,0],0,100],[-2600000,[at+1,1],0,2600000]])}}),[t])
        self.assertIsNotNone(c.breach);self.assertEqual(c.breach['at'],[at+1,1]);self.assertTrue(c.breach['daily'])

    def test_lossless_subsets_match_direct_integer_marks_at_both_risks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);at=ms('2023-01-03T09:00:00')
            rows=[(at,1999900,2000000),(at+60000,2000500,2000600),
                (at+120000,1999500,1999600),(at+180000,2001000,2001100)]
            p=root/f'{at}.ticks';p.write_bytes(b''.join(REC.pack(*r) for r in rows))
            quotes=Quotes({str(at):dict(path=str(p))})
            a=fixture_trade(at,at+180000,p1=2001000);a['exit_quote_index']=3
            b=fixture_trade(at+60000,at+180000,side='SELL',p0=2000500,p1=2001100,stop=2010500);b['entry_quote_index']=1;b['exit_quote_index']=3
            ledger,gaps=build_ledger([a,b],quotes,root,lambda *a,**k:None)
            self.assertFalse(gaps)
            for risk in (150,200):
                r=evaluate(ledger,[a,b],at,at+3600000,risk,'SYM_FLAT',False)
                expected=sum(t['sizing_costs'][str(risk)]['SYM_FLAT']['net_usd'] for t in [a,b])
                self.assertAlmostEqual(r['balance_usd']-50000,expected)
                # Starting after the first entry must use the stored subset,
                # never the first position's floating profit/loss.
                r=evaluate(ledger,[a,b],at+1,at+3600000,risk,'SYM_FLAT',False)
                self.assertAlmostEqual(r['balance_usd']-50000,b['sizing_costs'][str(risk)]['SYM_FLAT']['net_usd'])

    def test_funded_monitor_starts_flat_at_new_capital(self):
        at=ms('2023-01-10T09:00:00');c=Case(ms('2023-01-01'),END,150,'SYM_FLAT')
        c.phase=2;c.days={'2023-01-03','2023-01-04','2023-01-05','2023-01-06'};c.balance=52500000
        c.point([], [at,0],None)
        self.assertEqual(c.phase,3);self.assertEqual(c.funded_start,at);self.assertEqual(c.balance,50000000)
        self.assertEqual(c.dump()['funded_net_usd'],0)

    def test_cutoff_censors_without_inventing_a_pass(self):
        at=ms('2024-12-31T16:00:00');c=Case(at,END,150,'SYM_FLAT')
        c.consume(dict(kind='reset',at=[END,-1],quote=None),[])
        r=c.dump();self.assertEqual(r['status'],'RIGHT_CENSORED');self.assertFalse(r['phase_passes'])

    def test_long_break_ending_at_an_exit_quote_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);at=ms('2023-01-03T09:00:00');end=at+3*3600000
            rows=[(at,2000000,2000100),(end,2001000,2001100)]
            manifest={}
            for h in (at,end):
                p=root/f'{h}.ticks';p.write_bytes(REC.pack(*(rows[0] if h==at else rows[1])))
                manifest[str(h)]=dict(path=str(p))
            t=fixture_trade(at,end,p1=2001000);t['exit_quote_index']=0
            _,gaps=build_ledger([t],Quotes(manifest),root,lambda *a,**k:None)
            self.assertEqual(len(gaps),1)


if __name__=='__main__':unittest.main()

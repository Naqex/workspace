from datetime import datetime, timezone
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from xau_h1_execution import (deadline,END,HOUR,REC,Quotes,trigger,path_for,
    economics,exit_slip,swap_per_oz,price_summary,Stat,book,CELLS,reset_times)
from xau_h1_execution_review import oracle_book,Reader


def ms(text):return int(datetime.fromisoformat(text).replace(tzinfo=timezone.utc).timestamp()*1000)


def save_quotes(root,rows):
    grouped={}
    for r in rows:grouped.setdefault(r[0]//HOUR*HOUR,[]).append(r)
    for hour,values in grouped.items():
        (Path(root)/f'{hour}.ticks').write_bytes(b''.join(REC.pack(*r) for r in values))


def trade(at,end,side='BUY',entry=2000000,exit=2002000,q=10,reason='TP2R'):
    r=dict(entry_msc=at,exit_msc=end,entry_price_units=entry,exit_price_units=exit,
        side=side,ounces=q,reason=reason)
    r['costs']={c:economics(r,c) for c in CELLS}
    return r


class ExecutionTests(unittest.TestCase):
    def test_calendar_48_not_open_hours(self):
        t=ms('2023-03-06T10:00:00')+25
        self.assertEqual(deadline(t),t+48*HOUR)

    def test_thursday_and_friday_clamp(self):
        self.assertEqual(deadline(ms('2023-03-09T10:00:00')),ms('2023-03-10T20:30:00'))
        self.assertEqual(deadline(ms('2023-03-10T15:00:00')),ms('2023-03-10T20:30:00'))

    def test_year_end_does_not_open_holdout(self):
        self.assertLess(deadline(ms('2023-12-29T15:00:00')),END)
        with self.assertRaises(ValueError):deadline(END)
        with self.assertRaises(ValueError):deadline(ms('2023-12-30T10:00:00'))
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):Quotes(temp).hour(END)

    def test_sell_trigger_uses_ask(self):
        self.assertEqual(trigger('SELL',(1,1990000,2001000),2000000,1980000),('SL',2001000))
        self.assertEqual(trigger('SELL',(1,1979000,1981000),2010000,1980000),(None,None))

    def test_tp_exact_limit_and_stop_gap_quote(self):
        self.assertEqual(trigger('BUY',(1,2005000,2006000),1990000,2004000),('TP2R',2004000))
        self.assertEqual(trigger('BUY',(1,1980000,1981000),1990000,None),('SL',1980000))

    def test_order_slippage_only_changes_tp(self):
        self.assertEqual(exit_slip('SL','ASYM_ORDER'),.2)
        self.assertEqual(exit_slip('FRIDAY_CLOSE','ASYM_ORDER'),.2)
        at=ms('2023-03-06T10:00:00')
        t=trade(at,at+HOUR)
        self.assertAlmostEqual(t['costs']['SYM_ORDER']['net_usd']-t['costs']['SYM_FLAT']['net_usd'],2)

    def test_asymmetric_sell_and_triple_swap(self):
        at=ms('2023-03-08T20:00:00');end=at+3*HOUR
        t=trade(at,end,side='SELL',exit=1998000)
        self.assertEqual(t['costs']['SYM_ORDER']['swap_usd'],-12)
        self.assertEqual(t['costs']['ASYM_ORDER']['swap_usd'],-1.5)
        t=trade(at,end)
        self.assertEqual(t['costs']['ASYM_ORDER']['swap_usd'],-13.5)

    def test_quote_wait_limit_and_no_backfill(self):
        with tempfile.TemporaryDirectory() as temp:
            at=ms('2023-03-06T10:00:00')
            save_quotes(temp,[(at+60001,2000000,2000100)])
            self.assertIsNone(Quotes(temp).endpoint(at))
            self.assertIsNotNone(Quotes(temp).endpoint(at+1))

    def test_first_tick_order_resolves_sl_before_later_tp(self):
        with tempfile.TemporaryDirectory() as temp:
            at=ms('2023-03-06T10:00:00')
            save_quotes(temp,[(at,1999900,2000000),(at+10,1998900,1999000),(at+20,2003000,2003100)])
            row=dict(recipe='H1A_ASIA',side='BUY',decision_msc=at,day='2023-03-06',entry_quote=[at,1999900,2000000],stop_units=1999000)
            r=path_for(row,Quotes(temp),True)
            self.assertEqual(r['reason'],'SL');self.assertEqual(r['exit_price_units'],1998900)
            self.assertEqual(r['exit_msc'],at+10)

    def test_price_summary_preserves_order_not_extrema_sum(self):
        rows=[(1,1000,1100),(2,500,600),(3,2000,2100),(4,1700,1800)]
        self.assertEqual(price_summary(rows,1,0),(0.5,2.,.5,1.7))
        # Equal long/short cancels the common price movement, leaving spread.
        self.assertAlmostEqual(price_summary(rows,1,1)[2],0)

    def test_segment_merge_matches_brute_equity(self):
        s=Stat()
        s.add(10,30,5,25,1);s.add(-10,40,10,35,2)
        self.assertEqual(s.dd,40);self.assertEqual(s.peak,40)

    def test_prague_dst_midnight(self):
        times=reset_times(2023)
        self.assertIn(ms('2023-03-25T23:00:00'),times)
        self.assertIn(ms('2023-03-26T22:00:00'),times)

    def test_overlapping_hedged_book_cash_and_daily_balance(self):
        with tempfile.TemporaryDirectory() as temp:
            at=ms('2023-03-06T22:30:00');reset=ms('2023-03-06T23:00:00')
            rows=[(at,2000000,2000100),(reset,1990000,1990100),
                (reset+60000,1995000,1995100),(reset+120000,1997000,1997100)]
            save_quotes(temp,rows)
            t1=trade(at,rows[-1][0],entry=2000100,exit=1997000,reason='TIME_48H')
            t2=trade(at,rows[-1][0],side='SELL',entry=2000000,exit=1997100,reason='TIME_48H')
            b=book([t1,t2],Quotes(temp),2023)
            self.assertEqual(b['max_concurrent_positions'],2)
            for cell in CELLS:
                self.assertAlmostEqual(b['costs'][cell]['realized_net_usd'],t1['costs'][cell]['net_usd']+t2['costs'][cell]['net_usd'])
                self.assertLess(b['costs'][cell]['max_equity_drawdown_usd'],20)
            oracle,_=oracle_book([t1,t2],Reader(temp),2023)
            for c,r in oracle.items():
                self.assertAlmostEqual(r['dd_usd'],b['costs'][c]['max_equity_drawdown_usd'])
                self.assertAlmostEqual(r['daily_usd'],b['costs'][c]['worst_daily_loss_usd'])

    def test_reset_balance_anchor_differs_from_equity_anchor(self):
        with tempfile.TemporaryDirectory() as temp:
            at=ms('2023-03-06T22:30:00');reset=ms('2023-03-06T23:00:00')
            rows=[(at,2000000,2000100),(reset-1,1990000,1990100),
                (reset,1990000,1990100),(reset+60000,1980000,1980100),(reset+120000,1985000,1985100)]
            save_quotes(temp,rows)
            t=trade(at,rows[-1][0],entry=2000100,exit=1985000,reason='TIME_48H')
            b=book([t],Quotes(temp),2023)['costs']['SYM_FLAT']
            self.assertGreater(b['worst_daily_loss_pct'],b['equity_start_daily_loss_pct'])

    def test_integer_oracle_gap_swap_and_overnight_overlap(self):
        with tempfile.TemporaryDirectory() as temp:
            at=ms('2023-03-08T21:59:00');swap=ms('2023-03-08T22:00:00');reset=ms('2023-03-08T23:00:00')
            rows=[(at,2000000,2000100),(swap,1999000,1999100),
                (reset,2010000,2010100),(reset+60000,2005000,2005100)]
            save_quotes(temp,rows)
            ts=[trade(at,rows[-1][0],entry=2000100,exit=2005000,q=7,reason='SL'),
                trade(at,rows[-1][0],side='SELL',entry=2000000,exit=2005100,q=11,reason='SL')]
            b=book(ts,Quotes(temp),2023)
            oracle,_=oracle_book(ts,Reader(temp),2023)
            for c,r in oracle.items():
                self.assertAlmostEqual(r['dd_usd'],b['costs'][c]['max_equity_drawdown_usd'])
                self.assertAlmostEqual(r['daily_usd'],b['costs'][c]['worst_daily_loss_usd'])
                self.assertAlmostEqual(r['cash_usd'],b['costs'][c]['realized_net_usd'])

    def test_duplicate_millisecond_quotes_keep_source_order(self):
        with tempfile.TemporaryDirectory() as temp:
            at=ms('2023-03-06T10:00:00')
            rows=[(at,1999900,2000000),(at+1,2000500,2000600),
                (at+1,1998900,1999000),(at+1,2003000,2003100)]
            save_quotes(temp,rows)
            row=dict(recipe='H1A_ASIA',side='BUY',decision_msc=at,day='2023-03-06',
                entry_quote=list(rows[0]),stop_units=1999000)
            t=path_for(row,Quotes(temp),True)
            self.assertEqual(t['reason'],'SL');self.assertEqual(t['exit_quote_index'],2)
            b=book([t],Quotes(temp),2023)
            oracle,_=oracle_book([t],Reader(temp),2023)
            for c,r in oracle.items():
                self.assertAlmostEqual(r['dd_usd'],b['costs'][c]['max_equity_drawdown_usd'])
                self.assertAlmostEqual(r['daily_usd'],b['costs'][c]['worst_daily_loss_usd'])


if __name__=='__main__':unittest.main()

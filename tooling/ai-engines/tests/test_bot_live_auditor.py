from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import numpy as np

from bot_live_auditor import audit, behavior, leakage, load_pairs, outcomes
from quant_core.ftmo_track_replay import Market, STOP, calendar_warnings, observe_path, position, profiles, replay
from quant_core.live_trade_log import Trade, normalize
from selective_win_diagnosis import UNKNOWN


def ms(s):
    return int(datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp()*1000)


def ticket(i, at, end, **values):
    return Trade(i,'EURUSD','BUY',open_time=at,close_time=end,**values)


class NormalizerTests(unittest.TestCase):
    def test_myfxbook_timestamps_prices_and_observed_net(self):
        raw=(b'Open Date,Close Date,Symbol,Action,Lots,Open Price,Close Price,Profit (USD),Pips,Stop Loss\n'
             b'07.26.2024 15:24,07.26.2024 16:01,EURUSD,Buy,0.25,1.1000,1.1010,120.5,10,\n')
        rows,m=normalize(raw,'.csv',timezone_name='UTC',profit_basis='net')
        t=rows[0]
        self.assertEqual((t.open_time,t.close_precision,t.lots,t.net_profit,t.profit_currency,t.pips),
                         (ms('2024-07-26T15:24'), 'minute',.25,120.5,'USD',10.))
        self.assertIsNone(t.sl)
        self.assertIsNone(t.initial_sl)
        self.assertEqual(m['unknown_counts']['swap'],1)

    def test_mql_html_named_flat_rows_and_day_only_never_make_midnight_fill(self):
        html=b"""<table><tr><th>Open Time</th><th>Close Time</th><th>Symbol</th><th>Type</th>
        <th>Lots</th><th>Profit</th></tr><tr><td>2024.05.01 15:23:00</td><td>2024.05.02</td>
        <td>USDJPY</td><td>sell</td><td>1.00</td><td>-4</td></tr></table>"""
        t=normalize(html,'.html',timezone_name='UTC')[0][0]
        self.assertEqual((t.direction,t.close_precision,t.close_time),('SELL','day',None))
        self.assertEqual(t.close_date,'2024-05-02')

    def test_named_generic_volume_is_not_assumed_to_be_lots(self):
        raw=b'Opening timestamp;Closing timestamp;Instrument;Side;Volume;Net Profit\n2024-06-01T12:00Z;2024-06-01T12:01Z;GBP/USD;Long;1000;3,00\n'
        a=normalize(raw,'.csv',decimal_mark=',')[0][0]
        self.assertEqual((a.symbol,a.direction,a.net_profit),('GBPUSD','BUY',3.))
        self.assertIsNone(a.lots)

    def test_mt_positions_preserve_close_and_components_without_fabricating_stop(self):
        html=b"""<table><tr><td>Time</td><td>Position</td><td>Symbol</td><td>Type</td>
        <td>Volume</td><td>Price</td><td>S/L</td><td>Time</td><td>Price</td>
        <td>Commission</td><td>Swap</td><td>Profit</td></tr>
        <tr><td>2024.01.02 10:00:00</td><td>441</td><td>EURUSD</td><td>buy</td>
        <td>0.10</td><td>1.10</td><td></td><td>2024.01.02 10:01:00</td><td>1.105</td>
        <td>-0.5</td><td>0</td><td>50</td></tr></table>"""
        t=normalize(html,'.html',timezone_name='UTC')[0][0]
        self.assertEqual((t.close_price,t.lots,t.commission,t.swap,t.net_profit),(1.105,.1,-.5,0.,49.5))
        self.assertIsNone(t.sl)

    def test_mt5_deal_position_id_pair_is_used_and_partial_is_not_guessed(self):
        head=['Time','Deal','Symbol','Type','Direction','Volume','Price','Order','Position ID','Commission','Swap','Profit']
        rows=[['2024.01.02 10:00:00','1','EURUSD','buy','in','0.10','1.1','11','21','-0.2','0','0'],
              ['2024.01.02 11:00:00','2','EURUSD','sell','out','0.10','1.101','12','21','-0.3','-0.2','10']]
        to_table=lambda xs: ('<table>'+''.join('<tr>'+''.join(f'<td>{v}</td>' for v in r)+'</tr>'
                                               for r in xs)+'</table>').encode()
        a,m=normalize(to_table([head,*rows]),'.html',timezone_name='UTC')
        self.assertEqual((a[0].close_price,a[0].commission,a[0].swap,a[0].net_profit),(1.101,-.5,-.2,9.3))
        rows[1][5]='0.05'
        a,m=normalize(to_table([head,*rows]),'.html',timezone_name='UTC')
        self.assertEqual(a,[])
        self.assertIn('DEAL_PAIR_INCOMPLETE',m['warnings'])

    def test_naive_dst_ambiguous_unknown_and_journal_r_not_real_pnl(self):
        raw=b'Open Time,Close Time,Symbol,Lots,Side\n2024-10-27 02:15,2024-10-27 03:15,EURUSD,0.1,buy\n'
        a,_=normalize(raw,'.csv',timezone_name='Europe/Prague')
        self.assertIsNone(a[0].open_time)
        r='Trade Date,Pair,Position,WR,R:R,R:R Potential\n03/04/2026 3:15 (GMT+7),XAU/USD,Buy,Win,2.4,10\n'
        t=normalize(r.encode(),'.csv')[0][0]
        self.assertEqual(t.open_date,'2026-04-03')
        self.assertEqual((t.reported_r,t.net_profit,t.has_execution_clock),(2.4,None,False))


class EvidenceTests(unittest.TestCase):
    def test_holdout_store_rejected_before_price_columns_are_opened(self):
        with TemporaryDirectory() as tmp:
            p=Path(tmp)
            raw=np.array([STOP//1000],dtype='<i8').tobytes()
            (p/'times.bin').write_bytes(raw)
            (p/'manifest.json').write_text(json.dumps({'files':{'times.bin':sha256(raw).hexdigest()}}))
            (p/'bind.json').write_text(json.dumps({'EURUSD':{
                'path':str(p),'scope':'DEVELOPMENT','time_basis':'UTC','bar_seconds':60,'scale':100000}}))
            market=Market(p/'bind.json')
            self.assertIsNone(market.bid('EURUSD',STOP))
            self.assertFalse(market.stores)
            with self.assertRaisesRegex(ValueError,'STORE_CLOCK_OUTSIDE'):
                market.bid('EURUSD',STOP-60_000)
            self.assertFalse(market.stores)

    def test_prelock_m1_path_values_use_held_bars_not_same_entry_minute(self):
        class PreciseMarket(Market):
            def bars(self,asset,first,end):
                self.assertion=(first,end)
                from quant_core.market_data_store import BAR
                q=np.zeros(2,dtype=BAR)
                q['t']=[first,first+60000]; q['bo']=[110000,110100]
                q['bl']=[109900,110000]; q['bh']=[110200,110300]
                return q,100000
        a=ms('2024-01-02T13:00')
        t=ticket(1,a,a+3*60000,lots=.1,open_price=1.1,close_price=1.101,initial_sl=1.09)
        m=PreciseMarket()
        spec=profiles()[0]['Swing']['EURUSD']
        p=position(t,spec,m)
        q=observe_path(t,spec,m,p)
        self.assertTrue(q['complete'])
        self.assertEqual(m.assertion,(a+60000,a+3*60000))
        self.assertAlmostEqual(q['mfe'],295.)
        self.assertAlmostEqual(q['mae'],105.)
        self.assertAlmostEqual(p['net'],95.)

    def test_escalation_requires_settled_losses_and_grid_uses_market_mark(self):
        class MockMarket(Market):
            def bid(self,symbol,at):return 1.09
        a=ms('2024-01-02T13:00')
        trades=[ticket(1,a,a+60000,lots=.1,net_profit=-1.,open_price=1.1),
                ticket(2,a+120000,a+180000,lots=.1,net_profit=-2.,open_price=1.1),
                ticket(3,a+240000,a+420000,lots=.2,net_profit=-3.,open_price=1.1),
                ticket(4,a+300000,a+480000,lots=.1,net_profit=1.,open_price=1.09,sl=0.)]
        b=behavior(trades,outcomes(trades),MockMarket(),profiles()[0]['Swing'])
        self.assertEqual(b['HIDDEN_MARTINGALE_LOT_ESCALATION']['evidence'][0]['row'],3)
        self.assertEqual(b['HIDDEN_GRID_AVERAGING_DOWN']['evidence'][0]['prior_open_row'],3)
        self.assertEqual(b['NO_HARD_SL_OR_WIDE_STOP_GAMBLING']['explicit_no_sl'],1)

    def test_daily_and_static_max_loss_at_observed_marks(self):
        a=ms('2024-01-02T20:00')
        trades=[ticket(1,a,a+60000,open_price=1.10,close_price=1.08,initial_sl=1.099)]
        p=dict(gross=-2000.,open_commission=0.,close_commission=0.,rolls={},risk=100.,margin=100.)
        b=replay(trades,{1:(p,None)},profiles()[0]['Swing'],10000,.01)
        self.assertTrue(b['daily_breach_observed'])
        self.assertTrue(b['overall_breach_observed'])
        self.assertEqual(b['status'],'BREACH_INDICATION_OBSERVED_COHORT')

    def test_daily_reset_is_prague_balance_not_utc_or_peak_equity(self):
        a=ms('2024-07-01T21:57')
        t1=ticket(1,a,a+60000,initial_sl=1.)
        t2=ticket(2,a+120000,a+240000,initial_sl=1.)
        p=dict(gross=400.,open_commission=0.,close_commission=0.,rolls={},risk=100.,margin=100.)
        q=dict(gross=-600.,open_commission=0.,close_commission=0.,rolls={},risk=100.,margin=100.)
        r=replay([t1,t2],{1:(p,None),2:(q,None)},profiles()[0]['Swing'],10000,.01)
        self.assertEqual(r['daily_loss_pct'],6.)
        self.assertEqual(r['maximum_loss_pct'],2.)

    def test_calendar_long_break_and_unknown_without_calendar(self):
        t=ticket(1,ms('2024-01-05T10:00'),ms('2024-01-09T10:00'))
        cut=ms('2024-01-05T21:00')
        data={'valid_from_utc_msc':t.open_time,'valid_to_utc_msc':t.close_time,
              'breaks_by_symbol':{'EURUSD':[(cut,cut+3*3600000)]}}
        self.assertEqual(calendar_warnings([t],data,{'EURUSD'})['breaches'][0]['row'],1)
        self.assertEqual(calendar_warnings([t],None,{'EURUSD'})['weekend_proxy_rows'],[1])

    def test_leakage_reconciles_all_not_just_winners(self):
        rows=[dict(net_R=-1.,mfe_R=0.,mae_R=1.),dict(net_R=-1.,mfe_R=1.,mae_R=1.),
              dict(net_R=.7,mfe_R=3.,mae_R=.04),dict(net_R=-1.,mfe_R=None,mae_R=None)]
        got=leakage(rows,raw={'gate':False},paired={'delta_R':{'gross':-4.}})
        self.assertEqual(got['verdict'],'ENTRY_OR_HOLD_HORIZON_DEFICIT_AND_MEASURED_GIVEBACK')
        self.assertEqual(got['cohorts']['all']['path_n'],3)
        self.assertEqual(got['cohorts']['loss']['favourable_peak_then_loss'],1)
        self.assertEqual(got['cohorts']['all']['mfe_median_R'],1.)

    def test_paired_path_cannot_cross_holdout_and_unknown_journal_never_pretends_pass(self):
        raw=b'Trade Date,Pair,Position,WR,R:R\n03/04/2026 3:15 (GMT+7),EUR/USD,Buy,Win,2.4\n'
        r=audit(raw,'.csv')
        self.assertEqual(r['profiles']['Swing']['winner_diagnosis']['counts'][UNKNOWN],1)
        self.assertIsNone(r['profiles']['Swing']['ftmo_rule_breach_sim'][0]['net_usd'])
        _,bindings=profiles()
        payload=dict(source='sealed',input_sha256='hash',basis='SAME_ENTRY_INITIAL_RISK_AND_TARGET_COSTS',
                     profile_sha256_lf={k:v['sha256_lf'] for k,v in bindings.items()},
                     profiles={'Swing':{'1':dict(entry_utc_msc=STOP-60000,exit_utc_msc=STOP,
                                                 risk_per_lot_usd=1000.,net_R=3.)}})
        with self.assertRaisesRegex(ValueError,'OUTSIDE_DEV'):
            load_pairs(payload,'hash',bindings)

    def test_calendar_winner_requires_bound_same_entry_continuation(self):
        raw=(b'Open Time,Close Time,Symbol,Side,Lots,Open Price,Close Price,Initial SL,Exit Reason\n'
             b'2024-01-02T15:00Z,2024-01-02T16:00Z,EURUSD,BUY,0.10,1.1000,1.1010,1.0990,calendar cutoff\n')
        _,bindings=profiles()
        no_pair=audit(raw,'.csv')
        self.assertEqual(no_pair['profiles']['Swing']['winner_diagnosis']['counts'][UNKNOWN],1)
        payload=dict(source='sealed',input_sha256=sha256(raw).hexdigest(),
                     basis='SAME_ENTRY_INITIAL_RISK_AND_TARGET_COSTS',
                     profile_sha256_lf={k:v['sha256_lf'] for k,v in bindings.items()},
                     profiles={'Swing':{'1':dict(entry_utc_msc=ms('2024-01-02T15:00'),
                         exit_utc_msc=ms('2024-01-02T17:00'),risk_per_lot_usd=105.,net_R=2.)}})
        with_pair=audit(raw,'.csv',pair_payload=payload)
        self.assertEqual(with_pair['profiles']['Swing']['winner_diagnosis']['counts']['CUTOFF_TRUNCATED_WIN'],1)
        self.assertEqual(with_pair['profiles']['Standard']['winner_diagnosis']['counts'][UNKNOWN],1)

    def test_floating_loss_detected_even_when_trade_closes_flat(self):
        t0=ms('2024-01-02T15:00')
        t=ticket(1,t0,t0+180000)
        p=dict(gross=0.,open_commission=0.,close_commission=0.,rolls={},risk=100.,margin=100.)
        path={'marks':{t0+60000:-600.,t0+120000:-10.},'complete':True}
        result=replay([t],{1:(p,path)},profiles()[0]['Swing'],10000,.01)
        self.assertEqual(result['net_usd'],0.)
        self.assertTrue(result['daily_breach_observed'])
        self.assertFalse(result['overall_breach_observed'])
        self.assertEqual(result['status'],'BREACH_AT_MODELED_MARK')

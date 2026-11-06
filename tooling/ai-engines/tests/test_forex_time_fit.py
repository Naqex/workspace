import copy
from decimal import Decimal
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import forex_time_fit as timefit
import forex_h4_pilot as pilot
sys.path.insert(0,str(timefit.V2/'tests'))
from test_forex_pilot_risk import execution,initialize_forex_pilot,advance,queue,tick,ms
from test_forex_financing import terms
from trading_workspace_v2.replay_tick_execution import BrokerReplayTick


class TimeFitTests(unittest.TestCase):
    def test_quote_free_calendar_tail_posts_cash_without_mutating_quotes_or_orders(self):
        state=advance(queue(initialize_forex_pilot(execution(),start_time_msc=ms()),
            quantity='0.01',stop='1.09'),[tick()])
        term=terms(ms()+120000,event='end-fee',buy='20')
        manifest=dict(scenarios=[dict(name='reference',financing_calendar=[term.model_dump(mode='json')])])
        with self.assertRaisesRegex(ValueError,'no quote anchor'):
            timefit.complete_quote_free_financing_tail(
                initialize_forex_pilot(execution(),start_time_msc=ms()),manifest,'reference',ms()+180000)
        before=state.model_dump(mode='json')
        result,adjustments=timefit.complete_quote_free_financing_tail(state,manifest,'reference',ms()+180000)
        self.assertEqual(result.execution.balance,state.execution.balance-Decimal('0.20'))
        self.assertEqual(result.execution.position,state.execution.position)
        self.assertEqual(result.risk.observed_ticks,state.risk.observed_ticks)
        self.assertEqual(result.risk.last_tick,state.risk.last_tick)
        self.assertEqual(result.execution.cursor_index,state.execution.cursor_index)
        self.assertEqual(adjustments[0]['balance_delta_usd'],'-0.20')
        self.assertEqual(state.model_dump(mode='json'),before)
        again,changes=timefit.complete_quote_free_financing_tail(result,manifest,'reference',ms()+180000)
        self.assertEqual(again,result);self.assertEqual(changes,[])
        same,changes=timefit.complete_quote_free_financing_tail(state,manifest,'reference',term.scheduled_time_msc)
        self.assertEqual(same,state);self.assertEqual(changes,[])
        later=advance(state,[tick(when=ms()+240001)])
        with self.assertRaisesRegex(ValueError,'inside executed history'):
            timefit.complete_quote_free_financing_tail(later,manifest,'reference',ms()+300000)

        cutoff=ms()+180000
        manifest.update(run_id='tail-fixture',horizon_cutoffs=[cutoff])
        manifest['scenarios'][0]['slippage']='0'
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            packet=[dict(cutoff_msc=cutoff,checkpoint=before,
                last_observed_tick=state.risk.last_tick.model_dump(mode='json'),decisions=[],
                qualification='historical_snapshot_not_full_prop_lifecycle',promotion_authorized=False,
                accounting=pilot.reconcile(state,Decimal(0)))]
            for name,value in [('reference-horizons.json',packet),('reference-checkpoint.json',before),
                               ('reference-decisions.json',[]),('quality.json',{})]:
                (root/name).write_text(json.dumps(value))
            pilot.seal_scenario(root,manifest,dict(scenario='reference'))
            raw_bytes=(root/'reference-horizons.json').read_bytes()
            row=timefit.inspect_horizons(root,manifest,'reference')[0]
            self.assertEqual(Decimal(row['equity_delta_usd']),Decimal(row['raw_sealed_equity_delta_usd'])-Decimal('0.20'))
            self.assertEqual(row['observation_basis'],'sealed_raw_plus_declared_quote_free_cash_tail')
            self.assertFalse(row['promotion_authorized'])
            self.assertEqual((root/'reference-horizons.json').read_bytes(),raw_bytes)

    def test_trade_diagnostics_match_hand_ledger_with_credit_flat_and_open_fees(self):
        # Statistics fixture only: integration below validates actual sealed engine snapshots.
        rows=[]
        def event(kind,when,equity,**details):
            rows.append(dict(kind=kind,virtual_time_utc=when,equity=str(equity),details=details))
        def entry(position,when,equity):
            event('market_fill',when,equity,position_id=position,time_msc=when*1000,
                  fill_price='1.10000',open_position=dict(stop_loss='1.09000'))
        def fee(position,when,equity,debit):
            event('financing',when,equity,open_position=dict(position_id=position),debit_account=str(debit))
        def close(position,when,equity,net):
            event('protective_fill',when,equity,position_id=position,time_msc=when*1000,
                  fill_price='1.11000',side='BUY',quantity='0.01',reason='pilot_strategy_exit',net_pnl=str(net))
        entry('p1',1,10000);fee('p1',2,9998,2);close('p1',3,10008,10)
        entry('p2',4,10008);fee('p2',5,10009,-1);close('p2',6,10004,-5)
        entry('p3',7,10004);close('p3',8,10004,0)
        entry('p4',9,10004);fee('p4',10,10001,3);event('price_mark',11,10010)
        state=SimpleNamespace(execution=SimpleNamespace(ledger=rows,starting_balance=Decimal(10000),
            balance=Decimal(10001),position=SimpleNamespace(position_id='p4')),
            limits=SimpleNamespace(per_trade_loss=Decimal(25)),risk=SimpleNamespace(start_time_msc=0))
        before=copy.deepcopy(rows)
        result=timefit.ledger_diagnostics(state)
        self.assertEqual((result['wins'],result['losses'],result['flat_trades']), (1,1,1))
        self.assertEqual(Decimal(result['win_rate_fraction']),Decimal(1)/3)
        self.assertEqual(result['net_closed_pl_usd'],'4')
        self.assertEqual(result['open_position_financing_usd'],'3')
        self.assertEqual(result['realized_average_win_loss_ratio'],'2')
        self.assertEqual(result['profit_factor'],'2')
        self.assertEqual(result['ledger_event_max_drawdown_usd'],'8')
        self.assertEqual(result['max_observed_ledger_underwater_span_ms'],6000)
        self.assertEqual(result['longest_closed_loss_streak'],1)
        self.assertEqual([r['net_usd'] for r in result['trades']],['8','-4','0'])
        self.assertEqual(result['trades'][0]['research_budget_r'],'0.32')
        self.assertEqual(rows,before)
        state.execution.balance+=1
        with self.assertRaisesRegex(ValueError,'cash balance'):timefit.ledger_diagnostics(state)

    def test_empty_diagnostic_sample_is_unknown_not_zero_win_rate(self):
        state=SimpleNamespace(execution=SimpleNamespace(ledger=[],starting_balance=Decimal(10000),
            balance=Decimal(10000),position=None),limits=SimpleNamespace(per_trade_loss=Decimal(25)),
            risk=SimpleNamespace(start_time_msc=0))
        result=timefit.ledger_diagnostics(state)
        self.assertIsNone(result['win_rate_fraction'])
        self.assertIsNone(result['profit_factor'])
        self.assertIsNone(result['mean_closed_net_usd'])
        self.assertEqual(result['closed_trades'],0)

    def test_diagnostic_report_keeps_risk_coverage_warning_and_unknown_win_rate(self):
        diagnostics=dict(closed_trades=0,win_rate_fraction=None,mean_closed_net_usd=None,
            ledger_event_max_drawdown_usd='0',longest_closed_loss_streak=0)
        report=dict(rows=[dict(worker='fixture',cutoff_utc=date,scenario=scenario,
            equity_delta_usd='0',entry_fills=0,observed_ticks=100,diagnostics=diagnostics)
            for date in ('2023-04-01','2023-07-01','2024-01-01')
            for scenario in ('reference','cost-stress')])
        output=timefit.render_report(report)
        self.assertIn('N/A',output)
        self.assertIn('có thể bỏ lỡ đáy',output)
        self.assertIn('Chưa đủ mẫu',output)

    def test_summary_distinguishes_cost_screen_from_promotion_and_refuses_missing_rows(self):
        report=dict(rows=[dict(worker='fixture',cutoff_utc=date,scenario=scenario,
            equity_delta_usd=value,entry_fills=5,observed_ticks=100)
            for date in ('2023-04-01','2023-07-01','2024-01-01')
            for scenario,value in (('reference','10'),('cost-stress','5'))])
        self.assertIn('chưa đủ để chọn',timefit.render_report(report))
        report['rows'][-1]['equity_delta_usd']='-1'
        self.assertIn('chưa đạt screen phí',timefit.render_report(report))
        report['rows'].pop()
        with self.assertRaisesRegex(ValueError,'incomplete'):
            timefit.render_report(report)

    def test_no_trades_and_nonfinite_results_cannot_become_positive_screen(self):
        report=dict(rows=[dict(worker='fixture',cutoff_utc=date,scenario=scenario,
            equity_delta_usd='10',entry_fills=0,observed_ticks=100)
            for date in ('2023-04-01','2023-07-01','2024-01-01')
            for scenario in ('reference','cost-stress')])
        self.assertIn('Chưa đủ mẫu',timefit.render_report(report))
        report['rows'][0]['equity_delta_usd']='NaN'
        with self.assertRaisesRegex(ValueError,'nonfinite'):timefit.render_report(report)

    def test_sealed_horizons_reconcile_and_tampering_never_qualifies(self):
        ticks=[BrokerReplayTick(time_msc=pilot.START+i*3600000+1,sequence=i+1,
            bid='1.10000',ask='1.10020') for i in range(10)]
        cutoffs=[pilot.START+4*3600000,pilot.START+8*3600000]
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            with patch.object(pilot,'read_qdm_ticks',return_value=iter(ticks)):
                result=pilot.run_scenario(Path('unused'),[],'reference',Decimal(0),Decimal(0),
                    root,lambda *args:None,horizon_cutoffs=cutoffs)
            manifest=dict(run_id='synthetic',horizon_cutoffs=cutoffs,scenarios=[dict(name='reference',slippage='0')])
            (root/'quality.json').write_text('{}')
            pilot.seal_scenario(root,manifest,result)
            rows=timefit.inspect_horizons(root,manifest,'reference')
            self.assertEqual([row['observed_ticks'] for row in rows],[4,8])
            self.assertEqual(rows[0]['equity_delta_usd'],'0')
            self.assertEqual(rows[0]['full_prop_time_to_pass'],'not_evaluated')
            self.assertFalse(rows[0]['promotion_authorized'])
            self.assertEqual(rows[0]['diagnostics']['closed_trades'],0)
            self.assertEqual(rows[0]['diagnostics']['risk_path_coverage'],
                             'ledger_events_not_all_ticks_not_firm_drawdown')
            file=root/'reference-horizons.json'
            original=json.loads(file.read_bytes())
            for kind in ('money','future','cutoff','promotion'):
                with self.subTest(kind=kind):
                    modified=copy.deepcopy(original)
                    if kind=='money': modified[0]['checkpoint']['execution'].update(balance='10001',equity='10001')
                    if kind=='future': modified[0]['decisions'].append(dict(time_msc=cutoffs[0]+1))
                    if kind=='cutoff': modified[0]['cutoff_msc']+=1
                    if kind=='promotion': modified[0]['promotion_authorized']=True
                    file.write_text(json.dumps(modified))
                    with self.assertRaisesRegex(ValueError,'seal'):
                        timefit.inspect_horizons(root,manifest,'reference')
                    # Even a freshly checksummed bad packet fails semantic checks.
                    pilot.seal_scenario(root,manifest,result)
                    with self.assertRaises(ValueError):
                        timefit.inspect_horizons(root,manifest,'reference')
                    file.write_text(json.dumps(original)); pilot.seal_scenario(root,manifest,result)


if __name__=='__main__': unittest.main()

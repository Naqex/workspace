import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import strategy_evidence as evidence
from trading_workspace_v2 import forex_study_registration as registry


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.run = self.root / 'run'
        self.run.mkdir()
        (self.root / 'protocol.md').write_text('Registered before outcomes', encoding='utf-8')
        (self.root / 'input.csv').write_text('pinned fixture, not market data', encoding='utf-8')
        self.manifest = dict(schema='forex-h4-development-v1', candidate='fixture', source_revision='pinned',
            purpose='registered_development_not_qualification', broker_connected=False,
            validation_holdout_read=False, source_files={'candidate.py': '0'*64},
            research_protocol=dict(path=str(self.root/'protocol.md'), sha256=evidence.digest(self.root/'protocol.md')),
            scenarios=[dict(name='reference')], inputs={
                name: dict(path=str(self.root/'input.csv'), sha256=evidence.digest(self.root/'input.csv'),
                           first_day=first, last_day=last) for name,first,last in
                [('warmup','20211201','20211231'),('development','20220103','20220114')]})
        self.result = dict(scenario='reference', candidate='fixture', strategy_pass=False, prop_pass=False,
            broker_spec_verified=False, independent_accounting='passed', candidate_state_roundtrip='passed',
            balance_delta_usd='-2', realized_trade_net_usd='-1', financing_debit_usd='1',
            balance_usd='9998', equity_usd='10001', minimum_observed_equity_usd='9997',
            observed_ticks=10, entry_fills=1, closed_trades=0, pending_entry=False,
            open_position={'position_id':'p1'}, intrabar_equity_coverage='insufficient')
        self.write('manifest.json', self.manifest)
        self.write('receipt.json', dict(stage='completed_declared_scenarios'))
        self.write('quality.json', dict(warmup=dict(complete_h4=81), development=dict(ticks=10)))
        self.write('results.json', [self.result])
        self.write('reference-checkpoint.json', dict(execution=dict(starting_balance='10000', balance='9998',
            floating_pl='3', equity='10001', position={'position_id':'p1'}, pending_market_order=None)))

    def write(self, name, data):
        (self.run/name).write_text(json.dumps(data), encoding='utf-8')

    def test_valid_dossier_keeps_open_equity_and_never_promotes(self):
        report = evidence.inspect(self.run, verify_inputs=True)
        self.assertEqual(report['scenarios'][0]['equity_usd'], '10001')
        self.assertEqual(report['scenarios'][0]['balance_delta_usd'], '-2')
        self.assertTrue(report['scenarios'][0]['open_position'])
        self.assertTrue(report['protocol_content_verified'])
        self.assertFalse(report['promotion_authorized'])
        self.assertFalse(report['numeric_recalculation_performed'])

    def test_interrupted_run_or_false_promotion_is_rejected(self):
        self.write('receipt.json', dict(stage='running'))
        with self.assertRaisesRegex(ValueError, 'completed'):
            evidence.inspect(self.run)
        self.write('receipt.json', dict(stage='completed_declared_scenarios'))
        for change in ({'prop_pass':True}, {'strategy_pass':True}, {'broker_spec_verified':True},
                       {'candidate':'other'}, {'observed_ticks':11}, {'balance_delta_usd':'123'},
                       {'equity_usd':'NaN'}, {'entry_fills':True}, {'closed_trades':2}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.write('results.json', [dict(self.result, **change)])
                evidence.inspect(self.run)

    def test_positive_cash_and_verified_hashes_do_not_attest_a_validated_strategy(self):
        source=self.root/'source'
        source.mkdir()
        (source/'candidate.py').write_text('fixture source')
        self.manifest['source_files']={'candidate.py':evidence.digest(source/'candidate.py')}
        self.write('manifest.json',self.manifest)
        self.write('results.json',[dict(self.result,realized_trade_net_usd='4',
            balance_delta_usd='3',balance_usd='10003',equity_usd='10006')])
        checkpoint=json.loads((self.run/'reference-checkpoint.json').read_text())
        checkpoint['execution'].update(balance='10003',equity='10006')
        self.write('reference-checkpoint.json',checkpoint)
        report=evidence.inspect(self.run,verify_inputs=True,source_root=source)
        checks=report['review_checks']
        self.assertEqual(checks['input_hashes'],'verified')
        self.assertEqual(checks['current_source'],'matched')
        self.assertEqual(checks['protocol_content'],'verified')
        self.assertEqual(checks['preregistration_timing'],'not_attested_by_content_hash')
        self.assertEqual(checks['out_of_sample'],'not_satisfied_development_only')
        self.assertEqual(checks['causal_implementation'],'not_assessed_by_this_tool')
        self.assertEqual(checks['execution_realism'],'not_established')
        self.assertFalse(report['promotion_authorized'])
        self.assertEqual(report['qualification'],'not_established')

    def test_checkpoint_disagreement_cannot_hide_behind_reported_pass(self):
        checkpoint = json.loads((self.run/'reference-checkpoint.json').read_text())
        checkpoint['execution']['position'] = None
        self.write('reference-checkpoint.json', checkpoint)
        with self.assertRaisesRegex(ValueError, 'checkpoint'):
            evidence.inspect(self.run)

    def test_inputs_and_holdout_scope_are_checked(self):
        (self.root/'input.csv').write_text('changed')
        with self.assertRaisesRegex(ValueError, 'input content'):
            evidence.inspect(self.run, verify_inputs=True)
        bad = copy.deepcopy(self.manifest)
        bad['inputs']['development']['last_day'] = '20230114'
        self.write('manifest.json', bad)
        with self.assertRaisesRegex(ValueError, 'window'):
            evidence.inspect(self.run)

    def test_source_drift_is_separate_and_source_escape_fails(self):
        source = self.root/'source'
        source.mkdir()
        (source/'candidate.py').write_text('new code')
        report = evidence.inspect(self.run, source_root=source)
        self.assertEqual(report['source_drift'], ['candidate.py'])
        self.assertEqual(report['artifact_invariants'], 'checked')
        bad = copy.deepcopy(self.manifest)
        bad['source_files'] = {'../protocol.md': '0'*64}
        self.write('manifest.json', bad)
        with self.assertRaisesRegex(ValueError, 'escapes'):
            evidence.inspect(self.run, source_root=source)

    def test_preflight_cannot_be_mistaken_for_completed_study(self):
        bad = dict(self.manifest, execution_mode='preflight_only_no_simulation')
        self.write('manifest.json', bad)
        with self.assertRaisesRegex(ValueError, 'scope'):
            evidence.inspect(self.run)

    def test_stale_progress_is_unknown_liveness_not_failed(self):
        now=datetime(2026,11,5,tzinfo=timezone.utc)
        self.write('receipt.json',dict(stage='reference',updated_at_utc=(now-timedelta(seconds=300)).isoformat(),pid=123))
        report=evidence.status(self.run,now=now,stale_seconds=120)
        self.assertEqual(report['health'],'stale_progress_process_state_unknown')
        self.assertFalse(report['terminal'])
        self.assertFalse(report['process_liveness_verified'])
        self.write('receipt.json',dict(stage='failed',failed_stage='validate_development',
            updated_at_utc=(now-timedelta(days=1)).isoformat()))
        report=evidence.status(self.run,now=now)
        self.assertTrue(report['terminal'])
        self.assertEqual(report['failed_stage'],'validate_development')

    def historical_fixture(self):
        self.manifest.update(schema=registry.HISTORICAL_SCHEMA,purpose=registry.HISTORICAL_PURPOSE,
            data_role='historical_robustness',prior_exposure='unverified_owner_cannot_recall',
            clean_oos=False,risk_usd=[25,100,500],observed_account_spec=dict(sha256='a'*64))
        windows=dict(warmup=dict(first_day='20221101',last_day='20221231'),
                     evaluation=dict(first_day='20230101',last_day='20230331'))
        for role,target in [('warmup','warmup'),('development','evaluation')]:
            self.manifest['inputs'][role].update(windows[target])
        start=datetime(2023,1,1,tzinfo=timezone.utc)
        calendar=[]
        for day in range(90):
            stamp=start+timedelta(days=day,hours=22)
            if stamp.weekday()<5:
                calendar.append(dict(scheduled_time_msc=int(stamp.timestamp())*1000,
                    known_at_msc=int(start.timestamp())*1000,multiplier=3 if stamp.weekday()==2 else 1,
                    debit_buy_usd_per_lot='1',debit_sell_usd_per_lot='1'))
        self.manifest['scenarios']=[dict(name='reference',commission_usd_per_lot_per_side='2.50',
                                         slippage='0',financing_calendar=calendar)]
        registration=dict(schema='forex-historical-study-registration-v1',study_id='fixture',
            data_role=self.manifest['data_role'],prior_exposure=self.manifest['prior_exposure'],clean_oos=False,
            authorization=dict(promotion_authorized=False),windows=windows,candidates=['fixture'],
            protocol=self.manifest['research_protocol'],account_spec=dict(sha256='a'*64),
            source_files=self.manifest['source_files'],scenarios=[dict(name='reference',
                commission_usd_per_lot_per_side='2.50',slippage_price_per_side='0',
                financing_debit_buy_usd_per_lot='1',financing_debit_sell_usd_per_lot='1')])
        self.write('study-registration.json',registration)
        digest=evidence.digest(self.run/'study-registration.json')
        self.manifest['study_registration']=dict(study_id='fixture',sha256=digest)
        self.write('manifest.json',self.manifest)
        guard=patch.dict(registry.REGISTERED_STUDIES,{digest:'fixture'})
        guard.start()
        self.addCleanup(guard.stop)

    def test_registered_history_is_reviewable_but_never_becomes_clean_oos(self):
        self.historical_fixture()
        report=evidence.inspect(self.run,verify_inputs=True)
        self.assertEqual(report['evidence_scope'],'historical_robustness_exposure_unverified')
        self.assertEqual(report['review_checks']['out_of_sample'],'not_established_prior_exposure_unverified')
        self.assertFalse(report['promotion_authorized'])
        self.manifest['clean_oos']=True
        self.write('manifest.json',self.manifest)
        with self.assertRaisesRegex(ValueError,'scope'):
            evidence.inspect(self.run)

    def test_registered_history_rejects_tampered_core_or_registration(self):
        self.historical_fixture()
        original=copy.deepcopy(self.manifest)
        self.manifest['source_files']['candidate.py']='b'*64
        self.write('manifest.json',self.manifest)
        with self.assertRaisesRegex(ValueError,'source'):
            evidence.inspect(self.run)
        self.write('manifest.json',original)
        (self.run/'study-registration.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'registration'):
            evidence.inspect(self.run)


if __name__ == '__main__':
    unittest.main()

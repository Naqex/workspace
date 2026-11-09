import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import forex_research as research
from engine_worker import JobError


def scenarios():
    return [dict(scenario=name, **expected, entry_fills=3, closed_trades=3, signals=4,
                 observed_ticks=643775, independent_accounting='passed', snapshot_restart='passed',
                 open_position=None, pending_entry=False, risk_stops=[], risk_rejections=[],
                 broker_spec_verified=False, strategy_pass=False, prop_pass=False,
                 terminal_close_forced=False, intrabar_equity_coverage='insufficient')
            for name, expected in research.ORACLE.items()]


class ForexFixtureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.job = self.root / 'job'
        self.job.mkdir()
        self.config = dict(input_dir=str(self.root / 'inputs'), account_spec=str(self.root / 'spec.json'),
                           account_spec_sha256=research.ACCOUNT_SPEC_SHA256)
        self.settings = {'forex_pilot': self.config}
        self.account = dict(path=self.config['account_spec'], sha256=research.ACCOUNT_SPEC_SHA256,
                            captured_at_utc='2026-11-02T08:58:49+00:00',
                            historical_spec_verified=False, commission_account_specific_verified=False)
        self.pilot = SimpleNamespace(observed_account_spec=Mock(return_value=self.account), main=Mock())
        patcher = patch.object(research, '_pilot', return_value=self.pilot)
        patcher.start()
        self.addCleanup(patcher.stop)

    def fixture(self, *, header='DateTime,Bid,Ask,Volume'):
        inputs = {}
        for name, (_, first, last) in research.INPUTS.items():
            file = Path(self.config['input_dir']) / name / 'EURUSD_TICK_TW-TICK-No Session.csv'
            file.parent.mkdir(parents=True, exist_ok=True)
            wire = (header + '\n' + first + ' 00:00:00.001,1.10000,1.10020,1\n').encode()
            file.write_bytes(wire)
            inputs[name] = (hashlib.sha256(wire).hexdigest(), first, last)
        patcher = patch.object(research, 'INPUTS', inputs)
        patcher.start()
        self.addCleanup(patcher.stop)
        return inputs

    def prepared(self):
        self.fixture()
        return research.preflight(self.settings, self.job)

    def emit_replay(self, prepared, *, stage='completed_declared_scenarios', rows=None, gates=None):
        def emit(argv, on_progress):
            replay = Path(argv[argv.index('--output-dir') + 1])
            replay.mkdir()
            manifest = dict(candidate=research.CANDIDATE, source_revision='fixture-source',
                            source_files={'scripts/forex_h4_pilot.py': 'fixture-hash'},
                            inputs=prepared['provenance']['inputs'], observed_account_spec=self.account,
                            validation_holdout_read=False, broker_connected=False, broker_spec_verified=False)
            manifest.update(gates or {})
            for filename, value in [('receipt.json', {'stage': stage}), ('manifest.json', manifest),
                                    ('results.json', scenarios() if rows is None else rows),
                                    ('quality.json', {'warmup': {'ticks': 546210},
                                                      'development': {'ticks': 643775}})]:
                (replay / filename).write_text(json.dumps(value), encoding='utf-8')
            if on_progress:
                on_progress(stage)
        return emit

    def test_preflight_pins_files_spec_and_omits_private_paths_from_evidence(self):
        prepared = self.prepared()
        self.assertEqual(prepared['config'], self.config)
        self.pilot.observed_account_spec.assert_called_once_with(
            Path(self.config['account_spec']), research.ACCOUNT_SPEC_SHA256)
        evidence = json.loads((self.job / 'data-preflight.json').read_text(encoding='utf-8'))
        self.assertNotIn(str(self.root), json.dumps(evidence))
        self.assertFalse(evidence['strategy_qualified'])
        self.assertFalse(evidence['execution_capability'])
        self.assertFalse(evidence['validation_holdout_read'])

    def test_preflight_rejects_unregistered_or_tampered_inputs_before_replay(self):
        self.fixture()
        for change in ({'account_spec_sha256': '0' * 64}, {'input_dir': '../inputs'},
                       {'command': 'anything'}, {'input_manifest': 'wider-window.json'}):
            with self.subTest(change=change), self.assertRaises(JobError):
                research.preflight({'forex_pilot': dict(self.config, **change)}, self.job)
        file = Path(self.config['input_dir']) / 'development/EURUSD_TICK_TW-TICK-No Session.csv'
        file.write_text(file.read_text() + 'changed', encoding='utf-8')
        with self.assertRaises(JobError) as error:
            research.preflight(self.settings, self.job)
        self.assertEqual(error.exception.code, 'forex_fixture_changed')
        self.pilot.main.assert_not_called()

    def test_preflight_rejects_bad_format_and_unsupported_spec(self):
        self.fixture(header='Date,Mid')
        with self.assertRaises(JobError):
            research.preflight(self.settings, self.job)
        self.pilot.observed_account_spec.side_effect = ValueError('unsupported swap mode')
        with self.assertRaises(JobError):
            research.preflight(self.settings, self.job)
        self.pilot.main.assert_not_called()

    def test_run_uses_in_process_registered_runner_and_returns_exact_report(self):
        prepared = self.prepared()
        self.pilot.main.side_effect = self.emit_replay(prepared)
        progress = Mock()
        result = research.run(self.settings, self.job, object(), prepared, 'native-run', on_progress=progress)
        args = self.pilot.main.call_args.kwargs['argv']
        self.assertNotIn('--input-manifest', args)
        self.assertEqual(args[args.index('--input-dir') + 1], self.config['input_dir'])
        self.assertEqual(args[args.index('--account-spec-sha256') + 1], research.ACCOUNT_SPEC_SHA256)
        progress.assert_called_once_with('completed_declared_scenarios')
        self.assertIn('| Thay đổi số dư sau mọi phí | -19.94 | -23.80 |', result['report'])
        self.assertNotIn(str(self.root), result['report'])
        self.assertEqual(result['rating'], 'SYSTEM_FIXTURE_PASSED')
        self.assertTrue(result['validation']['system_fixture_pass'])
        self.assertFalse(result['provenance']['strategy_qualified'])
        self.assertFalse(result['provenance']['execution_capability'])
        self.assertEqual(result['validation']['run_id'], 'native-run')
        self.assertFalse(result['settings']['provider_used'])

    def test_failed_or_partial_replay_does_not_return_completed_validation(self):
        prepared = self.prepared()
        self.pilot.main.side_effect = RuntimeError('interrupted')
        with self.assertRaisesRegex(RuntimeError, 'interrupted'):
            research.run(self.settings, self.job, None, prepared, 'native-run')
        self.pilot.main.side_effect = self.emit_replay(prepared, stage='reference')
        with self.assertRaises(JobError) as error:
            research.run(self.settings, self.job, None, prepared, 'native-run')
        self.assertEqual(error.exception.code, 'forex_fixture_incomplete')

    def test_changed_outcomes_and_promoted_qualification_cannot_reach_report(self):
        for mutation in ('profit', 'missing_scenario', 'strategy_pass', 'accounting'):
            rows = copy.deepcopy(scenarios())
            if mutation == 'profit': rows[0]['balance_delta_usd'] = '1000'
            if mutation == 'missing_scenario': rows.pop()
            if mutation == 'strategy_pass': rows[0]['strategy_pass'] = True
            if mutation == 'accounting': rows[0]['independent_accounting'] = 'failed'
            value = dict(experiment=research.EXPERIMENT, purpose='system_fixture', scenarios=rows,
                         system_fixture_pass=True, strategy_qualified=False, execution_capability=False)
            with self.subTest(mutation=mutation), self.assertRaises(JobError):
                research.build_report(value)

    def test_report_rejects_wrong_purpose_and_authority_even_with_valid_numbers(self):
        base = dict(experiment=research.EXPERIMENT, purpose='system_fixture', scenarios=scenarios(),
                    system_fixture_pass=True, strategy_qualified=False, execution_capability=False)
        for change in ({'purpose': 'strategy_qualification'}, {'strategy_qualified': True},
                       {'execution_capability': True}, {'system_fixture_pass': False}):
            with self.subTest(change=change), self.assertRaises(JobError):
                research.build_report(dict(base, **change))


if __name__ == '__main__':
    unittest.main()

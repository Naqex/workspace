import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import strategy_evidence as evidence


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


if __name__ == '__main__':
    unittest.main()

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import engine_worker as worker
import rd_research as research


CODE = '''import pandas as pd
df = pd.read_hdf('daily_pv.h5', key='data')
prior = df.groupby(level='instrument')['$close'].shift(3)
result = pd.DataFrame({'momentum_3d': df['$close'] / prior - 1}, index=df.index)
result.to_hdf('result.h5', key='data', mode='w')
'''


class ResearchContractTests(unittest.TestCase):
    def test_rate_limit_does_not_repeat_generation(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            error = worker.HTTPError('http://fixture', 429, 'rate limited', {}, None)
            with patch.object(research, 'urlopen', side_effect=error) as request:
                with self.assertRaises(worker.HTTPError):
                    research.generate({'quick_model': 'fixture'}, directory, ('http://fixture/v1', 'fixture'))
            request.assert_called_once()
            self.assertFalse((directory / 'candidate.py').exists())
            attempt = json.loads((directory / 'model-attempt.json').read_text())
            self.assertEqual((attempt['calls'], attempt['retries']), (1, 0))

    def test_only_registered_experiment_is_accepted(self):
        request = dict(version=1, engine='rd-agent', experiment=research.EXPERIMENT)
        text = lambda v: '```naqex-engine\n' + json.dumps(v) + '\n```\n'
        self.assertEqual(worker.parse_request(text(request)), request)
        for changes in [dict(experiment='other'), dict(command='bash'), dict(path='../data')]:
            with self.subTest(changes=changes), self.assertRaises(worker.JobError):
                worker.parse_request(text(dict(request, **changes)))

    def test_transform_surface_rejects_escape_and_future_shift(self):
        research.review_candidate(CODE)
        for code in [CODE.replace('shift(3)', 'shift(-1)'), 'import os\nos.system("whoami")',
                     'open("/etc/passwd")', 'import pandas as pd\npd.read_pickle("input")',
                     'import pandas as pd\nx = pd.__dict__', CODE.replace('result.h5', '../result.h5')]:
            with self.subTest(code=code), self.assertRaises(worker.JobError):
                research.review_candidate(code)

    def test_manifest_mismatch_is_rejected_before_opening_data(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'manifest.json'
            path.write_text('{}')
            settings = {'rd_agent': {'dataset_manifest': str(path.resolve()),
                         'manifest_sha256': '0' * 64, 'image_id': 'sha256:' + '1' * 64}}
            with patch.object(research, 'checked_frame') as reader, self.assertRaises(worker.JobError) as caught:
                research.preflight(settings, Path(temp))
            self.assertEqual(caught.exception.code, 'dataset_changed')
            reader.assert_not_called()

    def test_gaps_and_unclosed_timestamp_fail_quality(self):
        index = pd.date_range('2024-01-01', periods=12, freq='D', tz='UTC')
        frame = pd.DataFrame({'open_time': index, 'close_time': index + pd.Timedelta(days=1) - pd.Timedelta(milliseconds=1),
                              'open': 100., 'high': 101., 'low': 99., 'close': 100., 'volume': 2.})
        contract = dict(research.CONTRACT, start='2024-01-01', end_exclusive='2024-01-13')
        with tempfile.TemporaryDirectory() as temp, patch.object(research, 'CONTRACT', contract):
            path = Path(temp) / 'fixture.csv'
            frame.to_csv(path, index=False)
            checked, _ = research.checked_frame(path)
            self.assertEqual(len(checked), 12)
            for bad in [frame.drop(5), frame.assign(close_time=index + pd.Timedelta(days=1))]:
                bad.to_csv(path, index=False)
                with self.assertRaises(worker.JobError):
                    research.checked_frame(path)

    def test_factor_is_verified_before_shared_oos_and_cost_accounting(self):
        index = pd.date_range('2024-01-01', periods=60, freq='D', tz='UTC', name='datetime')
        close = pd.Series(100 * np.exp(np.sin(np.arange(60) / 7) * .2), index=index)
        frames = {'BTCUSDT': pd.DataFrame({'open_time': index, 'close': close.to_numpy()})}
        factor = pd.DataFrame({'datetime': index.tz_localize(None), 'instrument': 'BTCUSDT',
                               'momentum_3d': (close / close.shift(3) - 1).to_numpy()})
        contract = dict(research.CONTRACT, train_bars=20, test_bars=10, minimum_folds=4)
        with tempfile.TemporaryDirectory() as temp, patch.object(research, 'CONTRACT', contract):
            result = research.evaluate(frames, factor.to_csv(index=False), Path(temp))['BTCUSDT']
            candidate = result['candidate']
            self.assertEqual(len(candidate['folds']), 4)
            self.assertFalse(candidate['execution_capability'])
            self.assertEqual(candidate['input_sha256'], result['baselines']['input_sha256'])
            self.assertLessEqual(candidate['cases'][1]['aggregate_metrics']['total_return'],
                                 candidate['cases'][0]['aggregate_metrics']['total_return'])
            cash = next(v for v in result['baselines']['evaluations'] if v['baseline_id'] == 'cash')
            self.assertEqual(cash['baseline_metrics']['total_return'], 0)
            self.assertIn('Mua và giữ', research.build_report({'BTCUSDT': result}))
            factor.loc[10, 'momentum_3d'] += .01
            with self.assertRaises(AssertionError):
                research.evaluate(frames, factor.to_csv(index=False), Path(temp))

    def test_rd_dispatch_uses_rd_preflight_and_not_tradingagents(self):
        with tempfile.TemporaryDirectory() as temp:
            client = unittest.mock.MagicMock(company='company', run='00000000-0000-4000-8000-000000000001')
            client.assigned_issue.return_value = {'id': 'issue', 'description':
                '```naqex-engine\n' + json.dumps(dict(version=1, engine='rd-agent', experiment=research.EXPERIMENT)) + '\n```\n'}
            settings = dict(artifact_root=temp, quick_model='gemini-test', deep_model='gemini-test')
            with patch.object(worker, 'Paperclip', return_value=client), \
                 patch.object(worker, 'load_settings', return_value=settings), \
                 patch.object(worker, 'source_pin', return_value='pin'), \
                 patch.object(worker, 'gateway', return_value=('base', 'key')), \
                 patch.object(worker, 'run_tradingagents') as analysis, \
                 patch.object(research, 'preflight', return_value={'fixture': True}) as preflight, \
                 patch.object(research, 'run', return_value={'report': '# Research', 'rating': 'research_only',
                                                            'settings': {}, 'provenance': {}, 'validation': {}}) as run:
                self.assertEqual(worker.execute_paperclip('rd-agent', Path('settings')), 0)
                analysis.assert_not_called()
                preflight.assert_called_once()
                run.assert_called_once()
                self.assertTrue(client.report.call_args.kwargs['research'])
                client.call.assert_called_once()

    def test_evidence_delivery_failure_keeps_completed_research_files(self):
        with tempfile.TemporaryDirectory() as temp:
            client = unittest.mock.MagicMock(company='company', run='run')
            client.assigned_issue.return_value = {'id': 'issue', 'description':
                '```naqex-engine\n' + json.dumps(dict(version=1, engine='rd-agent', experiment=research.EXPERIMENT)) + '\n```\n'}
            client.call.side_effect = worker.JobError('paperclip_unavailable', 'offline')
            with patch.object(worker, 'Paperclip', return_value=client), \
                 patch.object(worker, 'load_settings', return_value=dict(artifact_root=temp, quick_model='gemini', deep_model='gemini')), \
                 patch.object(worker, 'source_pin', return_value='pin'), \
                 patch.object(worker, 'gateway', return_value=('base', 'key')), \
                 patch.object(research, 'preflight', return_value={}), \
                 patch.object(research, 'run', return_value=dict(report='# Saved research', rating='research_only',
                     settings={}, provenance={}, validation={})):
                self.assertEqual(worker.execute_paperclip('rd-agent', Path('settings')), 2)
            folder = Path(temp) / 'company/run'
            self.assertEqual((folder / 'report.md').read_text(), '# Saved research')
            self.assertTrue((folder / 'evidence.md').exists())
            receipt = json.loads((folder / 'receipt.json').read_text())
            self.assertEqual(receipt['engine_status'], 'completed')
            self.assertEqual(receipt['delivery_status'], 'failed')


if __name__ == '__main__':
    unittest.main()

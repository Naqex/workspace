import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

SOURCE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE))
import engine_worker as worker


def description(**changes):
    value = dict(version=1, engine='tradingagents', symbol='BTC-USD', as_of='2026-10-31',
                 asset_type='crypto', analysts=['market'])
    value.update(changes)
    return 'Phân tích thị trường\n\n```naqex-engine\n' + json.dumps(value) + '\n```\n'


class ContractTests(unittest.TestCase):
    def test_bounded_crypto_request(self):
        self.assertEqual(worker.parse_request(description())['symbol'], 'BTC-USD')

    def test_rejects_paths_commands_providers_and_future_dates(self):
        for change in [dict(symbol='../BTC'), dict(symbol='BTC;echo'), dict(command='python'),
                       dict(as_of='2099-01-01'), dict(as_of='20261031'),
                       dict(version=True),
                       dict(asset_type='forex'), dict(analysts=['fundamentals']),
                       dict(analysts=['market', 'market']), dict(analysts=['shell'])]:
            with self.subTest(change=change), self.assertRaises(worker.JobError):
                worker.parse_request(description(**change))

    def test_rejects_ambiguous_requests(self):
        for text in ['', description() + description(), '```naqex-engine\n[]\n```\n']:
            with self.subTest(text=text), self.assertRaises(worker.JobError):
                worker.parse_request(text)

    def test_rd_agent_does_not_accept_arbitrary_command(self):
        text = '```naqex-engine\n{"version":1,"engine":"rd-agent"}\n```\n'
        self.assertEqual(worker.parse_request(text)['engine'], 'rd-agent')
        with self.assertRaises(worker.JobError):
            worker.parse_request(text.replace('"rd-agent"', '"rd-agent","command":"bash"'))

    def test_settings_reject_expired_model_before_provider(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'settings.json'
            value = dict(version=1, artifact_root=str(Path(temp).resolve()),
                         gateway_config=str(path.resolve()), quick_model='claude-opus-5.5[1m]',
                         deep_model='gemini-fixture')
            path.write_text(json.dumps(value))
            with self.assertRaises(worker.JobError) as context:
                worker.load_settings(path)
            self.assertEqual(context.exception.code, 'model_expired')

    def test_host_credentials_are_removed(self):
        environment = {'PATH': 'fixture', 'OPENAI_API_KEY': 'do-not-forward',
                       'ANTHROPIC_API_KEY': 'do-not-forward', 'LANGSMITH_API_KEY': 'do-not-forward',
                       'TRADINGAGENTS_BACKEND_URL': 'https://unrelated.invalid',
                       'PAPERCLIP_RUN_ID': 'run'}
        with patch.dict(worker.os.environ, environment, clear=True):
            worker.clean_environment()
            self.assertNotIn('OPENAI_API_KEY', worker.os.environ)
            self.assertNotIn('LANGSMITH_API_KEY', worker.os.environ)
            self.assertNotIn('TRADINGAGENTS_BACKEND_URL', worker.os.environ)
            self.assertEqual(worker.os.environ['PAPERCLIP_RUN_ID'], 'run')

    def test_reject_foreign_paperclip_origin(self):
        environment = dict(PAPERCLIP_AGENT_ID='00000000-0000-4000-8000-000000000001',
                           PAPERCLIP_COMPANY_ID='00000000-0000-4000-8000-000000000002',
                           PAPERCLIP_RUN_ID='00000000-0000-4000-8000-000000000003',
                           PAPERCLIP_API_KEY='fixture', PAPERCLIP_API_URL='http://unrelated.invalid')
        with patch.dict(worker.os.environ, environment, clear=True), self.assertRaises(worker.JobError):
            worker.Paperclip()

    def test_gateway_rejects_foreign_port_before_network(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'gateway.yaml'
            path.write_text('server:\n  host: 127.0.0.1\n  port: 8317\naccess:\n  api-keys: [fixture]\n')
            with patch.object(worker, 'urlopen') as network, self.assertRaises(worker.JobError):
                worker.gateway({'gateway_config': str(path)})
            network.assert_not_called()

    def test_gateway_rejects_missing_model_without_inference(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'gateway.yaml'
            path.write_text('server:\n  host: ' + worker.SERVICES['host'] + '\n  port: '
                            + str(worker.SERVICES['cliProxyApiPort']) + '\naccess:\n  api-keys: [fixture]\n')
            response = MagicMock()
            response.__enter__.return_value.read.return_value = b'{"data":[{"id":"other"}]}'
            with patch.object(worker, 'urlopen', return_value=response) as network:
                with self.assertRaises(worker.JobError) as context:
                    worker.gateway({'gateway_config': str(path), 'quick_model': 'missing', 'deep_model': 'missing'})
            self.assertEqual(context.exception.code, 'model_unavailable')
            self.assertTrue(network.call_args.args[0].full_url.endswith('/v1/models'))


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.settings = dict(version=1, artifact_root=self.temp.name,
                             gateway_config='unused', quick_model='gemini-fixture', deep_model='gemini-fixture')
        self.client = MagicMock(company='company', run='run')
        self.client.assigned_issue.return_value = {'id': 'issue', 'description': description()}
        self.directory = Path(self.temp.name) / 'company/run'
        self.engine = self.start_patch('run_tradingagents', return_value={
            'report': 'Báo cáo thử', 'rating': 'Hold', 'settings': {}, 'provenance': {'mode': 'advisory'}})
        self.gateway = self.start_patch('gateway', return_value=('http://127.0.0.1/v1', 'fixture'))
        self.start_patch('Paperclip', return_value=self.client)
        self.start_patch('load_settings', return_value=self.settings)
        self.start_patch('source_pin', return_value='source-fixture')

    def start_patch(self, name, **kwargs):
        item = patch.object(worker, name, **kwargs)
        result = item.start()
        self.addCleanup(item.stop)
        return result

    def run_job(self):
        return worker.execute_paperclip('tradingagents', Path('unused'))

    def receipt(self):
        return json.loads((self.directory / 'receipt.json').read_text(encoding='utf-8'))

    def test_success_publishes_native_report_with_provenance(self):
        self.assertEqual(self.run_job(), 0)
        receipt = self.receipt()
        self.assertEqual(receipt['delivery_status'], 'published')
        self.assertEqual(receipt['engine_status'], 'completed')
        self.assertFalse(receipt['execution_capability'])
        self.assertIn('source-fixture', self.client.report.call_args.args[1])
        self.assertTrue(self.client.report.call_args.kwargs['completed'])
        self.gateway.assert_called_once()

    def test_preflight_failure_never_starts_analysis(self):
        self.gateway.side_effect = worker.JobError('model_unavailable', 'Model chưa sẵn sàng')
        self.assertEqual(self.run_job(), 2)
        self.engine.assert_not_called()
        self.assertFalse(self.receipt()['provider_work_started'])
        self.assertEqual(self.receipt()['status'], 'blocked')

    def test_delivery_failure_preserves_completed_analysis(self):
        self.client.report.side_effect = worker.JobError('paperclip_unavailable', 'Offline')
        self.assertEqual(self.run_job(), 2)
        receipt = self.receipt()
        self.assertEqual(receipt['engine_status'], 'completed')
        self.assertEqual(receipt['delivery_status'], 'failed')
        self.assertEqual(receipt['rating'], 'Hold')
        self.assertIn('Báo cáo thử', (self.directory / 'report.md').read_text(encoding='utf-8'))
        self.engine.assert_called_once()

    def test_duplicate_dispatch_does_not_replay_or_modify_task(self):
        self.directory.mkdir(parents=True)
        original = '{"status":"running"}'
        (self.directory / 'receipt.json').write_text(original)
        self.assertEqual(self.run_job(), 2)
        self.engine.assert_not_called()
        self.client.report.assert_not_called()
        self.assertEqual((self.directory / 'receipt.json').read_text(), original)


class AssignmentTests(unittest.TestCase):
    def client(self):
        client = object.__new__(worker.Paperclip)
        client.agent, client.company, client.run = 'agent', 'company', 'run'
        client.call = MagicMock()
        return client

    def test_foreign_run_is_rejected_before_reading_task(self):
        client = self.client()
        client.call.return_value = {'agentId': 'other', 'companyId': 'company'}
        with self.assertRaises(worker.JobError):
            client.assigned_issue()
        self.assertEqual(client.call.call_count, 1)

    def test_foreign_assignee_and_terminal_task_are_rejected(self):
        for values in [{'assigneeAgentId': 'other'}, {'status': 'done'}]:
            client = self.client()
            client.call.side_effect = [
                {'agentId': 'agent', 'companyId': 'company',
                 'contextSnapshot': {'issueId': '00000000-0000-4000-8000-000000000004'}},
                {'companyId': 'company', 'assigneeAgentId': 'agent', 'status': 'todo', **values}]
            with self.subTest(values=values), self.assertRaises(worker.JobError):
                client.assigned_issue()
            self.assertEqual(client.call.call_count, 2)

    def test_checkout_conflict_is_not_retried(self):
        client = self.client()
        issue_id = '00000000-0000-4000-8000-000000000004'
        client.call.side_effect = [
            {'agentId': 'agent', 'companyId': 'company', 'contextSnapshot': {'issueId': issue_id}},
            {'id': issue_id, 'companyId': 'company', 'assigneeAgentId': 'agent', 'status': 'todo'},
            worker.JobError('paperclip_http_409', 'Conflict')]
        with self.assertRaises(worker.JobError):
            client.assigned_issue()
        self.assertEqual(client.call.call_count, 3)


if __name__ == '__main__':
    unittest.main()

import json
import subprocess
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
    def test_forex_request_accepts_only_registered_system_fixture(self):
        request = dict(version=1, engine='forex-pilot', experiment='forex-h4-system-v1')
        text = lambda value: '```naqex-engine\n' + json.dumps(value) + '\n```\n'
        self.assertEqual(worker.parse_request(text(request)), request)
        for change in ({'experiment': 'tune-h4'}, {'input_dir': '/tmp/data'},
                       {'model': 'other'}, {'command': 'python'}, {'version': True}):
            with self.subTest(change=change), self.assertRaises(worker.JobError):
                worker.parse_request(text(dict(request, **change)))

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

    def test_forex_execution_publishes_numeric_evidence_without_provider(self):
        request = {'version': 1, 'engine': 'forex-pilot', 'experiment': 'forex-h4-system-v1'}
        self.client.assigned_issue.return_value = {'id': 'issue', 'description':
            '```naqex-engine\n' + json.dumps(request) + '\n```\n'}
        result = dict(report='numeric report', rating='SYSTEM_FIXTURE_PASSED', settings={},
                      provenance={'strategy_qualified': False}, validation={'fixture': True})
        with patch('forex_research.preflight', return_value={}), patch('forex_research.run', return_value=result):
            self.assertEqual(worker.execute_paperclip('forex-pilot', Path('unused')), 0)
        self.gateway.assert_not_called()
        self.engine.assert_not_called()
        self.assertFalse(self.receipt()['provider_work_started'])
        self.assertTrue(self.receipt()['engine_work_started'])
        self.assertEqual(self.receipt()['status'], 'completed')
        evidence = (self.directory / 'evidence.md').read_text(encoding='utf-8')
        self.assertIn('forex_validation', evidence)

    def test_numeric_failure_is_failed_work_not_provider_or_preflight_success(self):
        self.client.assigned_issue.return_value = {'id': 'issue', 'description':
            '```naqex-engine\n{"version":1,"engine":"forex-pilot","experiment":"forex-h4-system-v1"}\n```\n'}
        with patch('forex_research.preflight', return_value={}), \
                patch('forex_research.run', side_effect=RuntimeError('interrupted')):
            self.assertEqual(worker.execute_paperclip('forex-pilot', Path('unused')), 2)
        self.assertEqual(self.receipt()['status'], 'failed')
        self.assertEqual(self.receipt()['error'], 'engine_failed')
        self.assertFalse(self.receipt()['provider_work_started'])
        self.gateway.assert_not_called()

    def test_preflight_failure_never_starts_analysis(self):
        self.gateway.side_effect = worker.JobError('model_unavailable', 'Model chưa sẵn sàng')
        self.assertEqual(self.run_job(), 2)
        self.engine.assert_not_called()
        self.assertFalse(self.receipt()['provider_work_started'])
        self.assertEqual(self.receipt()['status'], 'blocked')

    def test_linked_preflight_failure_notifies_owner_even_if_child_delivery_fails(self):
        self.client.assigned_issue.return_value['parentId'] = 'parent'
        self.gateway.side_effect = worker.JobError('model_unavailable', 'Model chưa sẵn sàng')
        self.client.report.side_effect = worker.JobError('paperclip_unavailable', 'Offline')
        with patch('spot_workflow.bind_research'), patch('spot_workflow.guard_research'), patch(
                'spot_workflow.report_workflow_failure', return_value=True) as notify:
            self.assertEqual(self.run_job(), 2)
        notify.assert_called_once_with(self.client, self.client.assigned_issue.return_value, 'model_unavailable')
        self.assertEqual(self.receipt()['failure_delivery'], 'published')
        self.engine.assert_not_called()
        self.assertFalse(self.receipt()['provider_work_started'])

    def test_delivery_failure_preserves_completed_analysis(self):
        self.client.report.side_effect = worker.JobError('paperclip_unavailable', 'Offline')
        self.assertEqual(self.run_job(), 2)
        receipt = self.receipt()
        self.assertEqual(receipt['engine_status'], 'completed')
        self.assertEqual(receipt['delivery_status'], 'failed')
        self.assertEqual(receipt['rating'], 'Hold')
        self.assertIn('Báo cáo thử', (self.directory / 'report.md').read_text(encoding='utf-8'))
        self.engine.assert_called_once()

    def test_provider_429_blocks_once_without_leaking_diagnostics(self):
        import httpx
        from openai import RateLimitError
        response = httpx.Response(429, request=httpx.Request('POST', 'http://fixture/v1/chat/completions'))
        errors = [worker.HTTPError('http://fixture', 429, 'private-provider-details', {}, None),
                  RateLimitError('private-provider-details', response=response, body=None)]
        for error in errors:
            with self.subTest(sdk=type(error).__name__), tempfile.TemporaryDirectory() as temporary:
                self.settings['artifact_root'] = temporary
                self.engine.reset_mock()
                self.client.report.reset_mock()
                self.engine.side_effect = error
                self.assertEqual(self.run_job(), 2)
                receipt = json.loads((Path(temporary) / 'company/run/receipt.json').read_text())
                self.assertEqual(receipt['error'], 'model_rate_limited')
                self.engine.assert_called_once()
                self.assertFalse(self.client.report.call_args.kwargs['completed'])
                report = self.client.report.call_args.args[1]
                self.assertIn('429', report)
                self.assertNotIn('private-provider-details', report)
                self.assertNotIn('private-provider-details', json.dumps(receipt))

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

    def test_failed_report_supplies_native_unblock_action(self):
        client = self.client()
        client.report('issue', 'Preflight failed', completed=False)
        payload = client.call.call_args.args[1]
        self.assertEqual(payload['status'], 'blocked')
        self.assertEqual(payload['unblockDescriptor']['owner'], {'agentId': client.agent})
        self.assertTrue(payload['unblockDescriptor']['action'])


class CliBootstrapTests(unittest.TestCase):
    def test_cli_and_workflow_share_the_same_error_class_before_any_work(self):
        script = '''
import argparse, runpy, sys
from pathlib import Path
path = Path(sys.argv[1])
sys.path.insert(0, str(path.parent))
def stop_before_work(*args, **kwargs):
    from spot_workflow import JobError
    assert sys._getframe(1).f_globals['JobError'] is JobError, 'CLI loaded a second JobError class'
    raise SystemExit(0)
argparse.ArgumentParser.parse_args = stop_before_work
runpy.run_path(str(path), run_name='__main__')
'''
        result = subprocess.run([sys.executable, '-c', script, str(SOURCE / 'engine_worker.py')],
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()

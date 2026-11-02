import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hermes_worker as worker


class CompletionTests(unittest.TestCase):
    def run_case(self, completed, attached):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            instructions = root / 'tooling/ai-engines/hermes_instructions.md'
            instructions.parent.mkdir(parents=True)
            instructions.write_text('Research review')
            client = Mock(company='company', run='run')
            client.assigned_issue.return_value = {'id': 'issue', 'description': 'x' * 200}
            directory = root / 'artifacts/company/run'
            def converse(prompt):
                if attached:
                    (directory / 'publication.json').write_text('{"status":"attached"}')
                return {'completed': completed, 'api_calls': 1, 'final_response': 'report'}
            agent = Mock(session_id='session', tools=[{'function': {'name': 'research_publish'}}])
            self.last_agent = agent
            agent.run_conversation.side_effect = converse
            modules = {'run_agent': SimpleNamespace(AIAgent=Mock(return_value=agent), __file__='pinned/run_agent.py'),
                       'hermes_state': SimpleNamespace(SessionDB=lambda: DummyDB()),
                       'hermes_yaml': SimpleNamespace(safe_load=Mock())}
            with patch.dict(sys.modules, modules), patch.object(worker, 'ROOT', root), patch.object(
                    worker, 'Paperclip', return_value=client), patch.object(worker, 'load_settings',
                    return_value={'artifact_root': str(root / 'artifacts'), 'quick_model': 'test'}), patch.object(
                    worker, 'gateway', return_value=('http://127.0.0.1/v1', 'fixture')), patch.object(
                    worker, 'source_pin', return_value='pin'), patch.object(worker, 'clean_environment'), patch.dict(
                    worker.os.environ, {}, clear=False):
                code = worker.execute(root / 'settings.json')
            receipt = json.loads((directory / 'receipt.json').read_text())
            return code, client, receipt

    def test_attached_report_is_not_completion_if_model_turn_failed(self):
        code, client, receipt = self.run_case(False, True)
        self.assertEqual(code, 1)
        self.assertEqual(receipt['status'], 'failed')
        client.call.assert_not_called()

    def test_success_requires_model_completion_and_attached_report(self):
        code, client, receipt = self.run_case(True, True)
        self.assertEqual(code, 0)
        self.assertEqual(receipt['status'], 'completed')
        self.assertEqual(client.call.call_args.args[1]['status'], 'done')
        code, client, receipt = self.run_case(True, False)
        self.assertEqual(code, 1)
        client.call.assert_not_called()

    def test_rejected_workflow_source_never_reaches_model(self):
        with patch.object(worker, 'review_source', side_effect=ValueError('invalid source')):
            code, client, receipt = self.run_case(True, True)
        self.assertEqual(code, 1)
        self.assertFalse(receipt['provider_work_started'])
        self.last_agent.run_conversation.assert_not_called()
        client.call.assert_not_called()

    def test_parent_delivery_failure_preserves_review_without_repeating_inference(self):
        source = dict(prompt='verified input', dossier='numbers', binding={'source_run': 'fixture'})
        with patch.object(worker, 'review_source', return_value=source), patch.object(
                worker, 'verify_review_source', return_value=source), patch.object(
                worker, 'finish_review', side_effect=RuntimeError('parent unavailable')):
            code, client, receipt = self.run_case(True, True)
        self.assertEqual(code, 1)
        self.assertEqual(receipt['review_delivery'], 'published')
        self.assertEqual(receipt['status'], 'failed')
        self.last_agent.run_conversation.assert_called_once_with('verified input')
        self.assertEqual(client.call.call_args.args[1]['status'], 'done')


class DummyDB:
    def __enter__(self): return self
    def __exit__(self, *args): return False

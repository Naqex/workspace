import hashlib
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
    def run_case(self, completed, attached, *, linked=False, failure_reason=None, reporting=True):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            instructions = root / 'tooling/ai-engines/hermes_instructions.md'
            instructions.parent.mkdir(parents=True)
            instructions.write_text('Research review')
            reporting_path = instructions.parent / 'paperclip-skills/naqex-research-lead/references/owner-reporting.md'
            if reporting:
                reporting_path.parent.mkdir(parents=True)
                reporting_path.write_text('Owner reporting fixture')
            client = Mock(company='company', run='run')
            client.assigned_issue.return_value = {'id': 'issue', 'description': 'x' * 200}
            if linked:
                client.assigned_issue.return_value['parentId'] = 'parent'
            directory = root / 'artifacts/company/run'
            def converse(prompt):
                if attached:
                    (directory / 'publication.json').write_text('{"status":"attached"}')
                return {'completed': completed, 'api_calls': 1, 'final_response': 'report',
                        'failure_reason': failure_reason}
            agent = Mock(session_id='session', tools=[{'function': {'name': 'research_publish'}}])
            self.last_agent = agent
            agent.run_conversation.side_effect = converse
            modules = {'run_agent': SimpleNamespace(AIAgent=Mock(return_value=agent), __file__='pinned/run_agent.py'),
                       'hermes_state': SimpleNamespace(SessionDB=lambda: DummyDB()),
                       'hermes_yaml': SimpleNamespace(safe_load=Mock())}
            self.agent_constructor = modules['run_agent'].AIAgent
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

    def test_rate_limit_keeps_attached_report_and_requires_manual_reconciliation(self):
        for reason in ('rate_limit', 'upstream_rate_limit'):
            with self.subTest(reason=reason):
                code, client, receipt = self.run_case(False, True, failure_reason=reason)
                self.assertEqual(code, 1)
                self.assertEqual(receipt['error'], 'model_rate_limited')
                self.assertIn('429', receipt['operator_action'])
                self.assertEqual(receipt['api_calls'], 1)
                self.last_agent.run_conversation.assert_called_once()
                client.call.assert_not_called()

    def test_success_requires_model_completion_and_attached_report(self):
        code, client, receipt = self.run_case(True, True)
        self.assertEqual(code, 0)
        self.assertEqual(receipt['status'], 'completed')
        self.assertEqual(client.call.call_args.args[1]['status'], 'done')
        prompt = self.agent_constructor.call_args.kwargs['ephemeral_system_prompt']
        self.assertEqual(prompt, 'Research review\n\nOwner reporting fixture')
        self.assertEqual(receipt['instructions_sha256'], hashlib.sha256(prompt.encode()).hexdigest())
        code, client, receipt = self.run_case(True, False)
        self.assertEqual(code, 1)
        client.call.assert_not_called()

    def test_missing_reporting_instructions_stops_before_provider_work(self):
        code, client, receipt = self.run_case(True, True, reporting=False)
        self.assertEqual(code, 1)
        self.assertFalse(receipt['provider_work_started'])
        self.agent_constructor.assert_not_called()
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

    def test_linked_delivery_failure_notifies_owner_and_keeps_completed_review(self):
        source = dict(prompt='verified input', dossier='numbers', binding={'source_run': 'fixture'})
        with patch.object(worker, 'review_source', return_value=source), patch.object(
                worker, 'verify_review_source', return_value=source), patch.object(
                worker, 'finish_review', side_effect=RuntimeError('parent unavailable')), patch.object(
                worker, 'report_workflow_failure', return_value=True) as notify:
            code, client, receipt = self.run_case(True, True, linked=True)
        self.assertEqual(code, 1)
        notify.assert_called_once_with(client, client.assigned_issue.return_value, 'RuntimeError', review_delivered=True)
        self.assertEqual(receipt['failure_delivery'], 'published')
        self.assertEqual(receipt['review_delivery'], 'published')
        self.last_agent.run_conversation.assert_called_once_with('verified input')
        self.assertEqual([call.args[1]['status'] for call in client.call.call_args_list
                          if len(call.args) > 1 and isinstance(call.args[1], dict) and 'status' in call.args[1]], ['done'])


class DummyDB:
    def __enter__(self): return self
    def __exit__(self, *args): return False

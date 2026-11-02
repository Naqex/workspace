import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock

spec = importlib.util.spec_from_file_location('hermes_project_plugin',
    Path(__file__).resolve().parents[1] / 'hermes_plugin/__init__.py')
plugin = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plugin)


class HermesPluginTests(unittest.TestCase):
    def test_rejects_arbitrary_target_and_host_tools(self):
        with patch.object(plugin, 'Paperclip') as client:
            result = json.loads(plugin.publish({'report': 'x' * 250, 'issue': 'other'}))
            self.assertIn('error', result)
            client.assert_not_called()
        self.assertEqual(plugin.guard('terminal')['action'], 'block')
        self.assertEqual(plugin.guard('skill_manage')['action'], 'block')
        self.assertIsNone(plugin.guard('memory'))

    def test_uses_guarded_current_issue_before_publication(self):
        client = Mock(run='run')
        client.assigned_issue.return_value = {'id': 'assigned'}
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(plugin, 'Paperclip', return_value=client), patch.object(
                    plugin, 'run_directory', return_value=Path(directory)):
                self.assertEqual(json.loads(plugin.publish({'report': 'x' * 250}))['status'], 'attached')
                client.call.assert_called_once_with('/issues/assigned/documents/engine-run',
                    {'title': 'Kết quả phản biện', 'format': 'markdown', 'body': 'x' * 250}, 'PUT')
                client.report.assert_not_called()
                self.assertFalse(json.loads((Path(directory) / 'publication.json').read_text())['execution_authorized'])

    def test_usage_never_records_raw_request_or_secret(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(plugin, 'run_directory', return_value=Path(directory)), patch.dict(
                    plugin.os.environ, {'PAPERCLIP_RUN_ID': 'fixture'}):
                plugin.usage(model='test', usage={'input_tokens': 10}, request={'key': 'secret'}, response='private')
            row = json.loads((Path(directory) / 'usage.jsonl').read_text())
        self.assertEqual(row, {'model': 'test', 'usage': {'input_tokens': 10}})

    def test_failure_does_not_disclose_api_error_or_retry(self):
        with patch.object(plugin, 'Paperclip', side_effect=RuntimeError('secret-key')) as client:
            result = plugin.publish({'report': 'x' * 250})
        self.assertNotIn('secret-key', result)
        client.assert_called_once()


if __name__ == '__main__':
    unittest.main()

import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from uuid import uuid4

from studio_observation import observe_step


class ObservationTests(unittest.TestCase):
    def setUp(self):
        self.company, self.issue, self.agent, self.run_id = [str(uuid4()) for _ in range(4)]
        self.child = dict(id=self.issue, status='done')
        self.run = dict(id=self.run_id, issueId=self.issue, companyId=self.company, agentId=self.agent,
                        status='succeeded', startedAt='2026-11-02T01:00:00Z', finishedAt='2026-11-02T01:01:00Z')
        self.receipt = dict(engine='forex-pilot', run_id=self.run_id, issue_id=self.issue,
                            company_id=self.company, status='completed', delivery_status='published')
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name) / self.company / self.run_id
        self.directory.mkdir(parents=True)

    def api(self, path):
        if path.endswith('/runs?view=recent'):
            return [dict(runId=self.run_id, agentId=self.agent)]
        return copy.deepcopy(self.run)

    def observe(self):
        (self.directory / 'receipt.json').write_text(json.dumps(self.receipt), encoding='utf-8')
        return observe_step(self.api, self.company, self.child, 'forex-pilot', self.tmp.name,
                            datetime(2026, 11, 2, 1, 2, tzinfo=timezone.utc))

    def test_completed_native_and_local_agree_and_zero_defaults_are_not_usage(self):
        self.run['usageJson'] = dict(inputTokens=0, outputTokens=0, billingType='unknown')
        self.run['resultJson'] = {'private': 'never expose this'}
        result = self.observe()
        self.assertEqual(result['state'], 'recorded')
        self.assertEqual(result['run']['seconds'], 60)
        for key in ('input_tokens', 'output_tokens', 'cost_usd', 'reported_model'):
            self.assertIsNone(result['run'][key])
        self.assertNotIn('private', json.dumps(result))

    def test_receipt_model_is_requested_not_claimed_as_reported(self):
        self.receipt.update(provider_work_started=True, models={'quick_model': 'gemini', 'deep_model': 'gemini-pro'})
        self.run.update(usageJson={'inputTokens': 120, 'outputTokens': 25, 'costUsd': 0.002}, costAccountingPending=True)
        result = self.observe()['run']
        self.assertEqual(result['requested_models'], ['gemini', 'gemini-pro'])
        self.assertIsNone(result['reported_model'])
        self.assertEqual(result['cost_usd'], 0.002)
        self.assertTrue(result['accounting_pending'])

    def test_interrupted_is_not_success_or_running_and_saved_delivery_is_separate(self):
        self.run.update(status='failed')
        self.receipt.update(status='running', delivery_status=None)
        self.assertEqual(self.observe()['state'], 'interrupted')
        self.receipt.update(status='failed', engine_status='completed', delivery_status='failed')
        self.assertEqual(self.observe()['state'], 'delivery_pending')
        self.run['status'] = 'cancelled'
        self.assertEqual(self.observe()['state'], 'cancelled')

    def test_active_elapsed_and_terminal_without_finish_is_unknown_duration(self):
        self.run.update(status='running', finishedAt=None)
        self.assertEqual(self.observe()['run']['seconds'], 120)
        self.assertEqual(self.observe()['state'], 'active')
        self.run['status'] = 'failed'
        self.assertIsNone(self.observe()['run']['seconds'])

    def test_scope_or_receipt_mismatch_is_rejected(self):
        for key in ('companyId', 'issueId', 'agentId', 'id'):
            with self.subTest(key=key):
                previous = self.run[key]
                self.run[key] = str(uuid4())
                with self.assertRaisesRegex(ValueError, 'workflow_scope'):
                    self.observe()
                self.run[key] = previous
        self.receipt['issue_id'] = str(uuid4())
        self.assertEqual(self.observe()['state'], 'evidence_mismatch')

    def test_tampered_output_or_oversized_receipt_is_not_accepted(self):
        self.receipt['report_sha256'] = hashlib.sha256(b'original').hexdigest()
        (self.directory / 'report.md').write_text('tampered', encoding='utf-8')
        self.assertEqual(self.observe()['state'], 'evidence_mismatch')

    def test_windows_newlines_match_worker_hash_and_missing_artifact_is_invalid(self):
        self.receipt['report_sha256'] = hashlib.sha256(b'first\nsecond\n').hexdigest()
        (self.directory / 'report.md').write_bytes(b'first\r\nsecond\r\n')
        self.assertEqual(self.observe()['state'], 'recorded')
        (self.directory / 'report.md').unlink()
        self.assertEqual(self.observe()['state'], 'evidence_mismatch')
        self.receipt = {'padding': 'x' * 65537}
        self.assertEqual(self.observe()['state'], 'evidence_mismatch')

    def test_unavailable_and_missing_run_do_not_look_pristine_or_successful(self):
        self.assertEqual(observe_step(lambda _: [], self.company, self.child, 'forex-pilot')['state'], 'unknown')
        def unavailable(_):
            raise ConnectionError('private error')
        self.assertEqual(observe_step(unavailable, self.company, self.child, 'forex-pilot')['state'], 'unavailable')
        self.assertEqual(observe_step(self.api, self.company, self.child, 'forex-pilot', self.tmp.name)['state'], 'unknown')


if __name__ == '__main__':
    unittest.main()

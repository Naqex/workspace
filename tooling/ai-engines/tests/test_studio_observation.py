import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from uuid import uuid4

from studio_observation import hermes_usage_for, observe_step


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

    def usage_row(self, suffix='1', **changes):
        return dict(session_id='naqex-' + self.run_id,
                    api_request_id='naqex-' + self.run_id + ':api:' + suffix,
                    model='gemini-requested', response_model='gemini-reported',
                    usage=dict(input_tokens=120, output_tokens=25, cache_read_tokens=30,
                               cache_write_tokens=0, reasoning_tokens=5), **changes)

    def usage(self, rows):
        (self.directory / 'usage.jsonl').write_text('\n'.join(json.dumps(r) for r in rows), encoding='utf-8')
        return hermes_usage_for(self.tmp.name, self.company, self.run_id,
                                dict(provider_work_started=True, status='completed', api_calls=2))

    def test_hermes_hook_totals_deduplicate_and_preserve_native_unknowns(self):
        row = self.usage_row()
        result = self.usage([row, row, self.usage_row('2')])
        self.assertEqual(result['status'], 'observed')
        self.assertEqual(result['requests'], 2)
        self.assertEqual(result['observed_tokens']['input_tokens'], 240)
        self.assertEqual(result['observed_tokens']['cache_read_tokens'], 60)
        self.assertEqual(result['reported_models'], ['gemini-reported'])
        self.assertIsNone(result['cost_usd'])
        self.receipt.update(engine='hermes', provider_work_started=True, api_calls=2)
        (self.directory / 'receipt.json').write_text(json.dumps(self.receipt), encoding='utf-8')
        result = observe_step(self.api, self.company, self.child, 'hermes', self.tmp.name)['run']
        self.assertEqual(result['provider_usage']['status'], 'observed')
        self.assertIsNone(result['input_tokens'])
        self.assertIsNone(result['reported_model'])

    def test_missing_usage_and_incomplete_hook_counts_are_not_zero_billing(self):
        row = self.usage_row()
        row['usage'] = None
        result = self.usage([row])
        self.assertEqual(result['status'], 'partial')
        self.assertIsNone(result['observed_tokens'])
        result = self.usage([self.usage_row()])
        self.assertEqual(result['status'], 'partial')
        self.assertEqual(result['observed_tokens']['input_tokens'], 120)
        self.assertIsNone(result['cost_usd'])
        result = self.usage([self.usage_row(), self.usage_row('2'), self.usage_row('aux', aux_task='title')])
        self.assertEqual(result['status'], 'observed')
        self.assertEqual(result['requests'], 3)

    def test_conflicting_request_foreign_session_and_invalid_tokens_are_rejected(self):
        row = self.usage_row()
        for changes in ({'session_id': 'other-run'}, {'api_request_id': 'other-request'},
                        {'usage': {'input_tokens': -1}}, {'usage': []}):
            with self.subTest(changes=changes):
                self.assertEqual(self.usage([{**row, **changes}])['status'], 'invalid')
        self.assertEqual(self.usage([row, {**row, 'response_model': 'different'}])['status'], 'invalid')

    def test_usage_read_is_bounded_and_missing_or_truncated_file_stays_unknown(self):
        receipt = dict(provider_work_started=True)
        read = lambda: hermes_usage_for(self.tmp.name, self.company, self.run_id, receipt)
        self.assertEqual(read()['status'], 'missing')
        for wire in ('{"unfinished":', 'x' * 65537):
            (self.directory / 'usage.jsonl').write_text(wire, encoding='utf-8')
            self.assertEqual(read()['status'], 'invalid')
        self.assertEqual(hermes_usage_for(None, self.company, self.run_id, receipt)['status'], 'unavailable')


if __name__ == '__main__':
    unittest.main()

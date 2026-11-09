import contextlib
import copy
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

import shadow_watch as watch


class ProgressTests(unittest.TestCase):
    def test_quality_hold_distinguishes_raw_progress_from_projection(self):
        state=dict(manifest_sha256='a'*64,status='running',observation=dict(
            projection_status='held',quality_reason='shadow_hour_gap_requires_review',pages=61,ticks=120))
        body=watch.render(state,100000)
        self.assertIn('Đang thu tick; tạm giữ tính nến/tín hiệu',body)
        self.assertIn('61 trang',body)
        self.assertIn('shadow_hour_gap_requires_review',body)
        state['status']='complete'
        self.assertIn('Đã thu xong; dữ liệu cần kiểm tra',watch.render(state,100000))

    def test_uncertain_put_is_read_back_without_duplicate_revision(self):
        doc, puts = None, []
        def api(path, body=None, method='GET'):
            nonlocal doc
            if method == 'GET':
                if doc is None:
                    raise HTTPError(path, 404, 'missing', {}, None)
                return doc.copy()
            puts.append(body)
            doc = dict(body, latestRevisionId='revision-1')
            raise TimeoutError('reply lost after commit')
        publisher = watch.Publisher('task', 'a'*64, api)
        body = publisher.marker+'\nstatus'
        with self.assertRaises(TimeoutError):
            publisher.send(body)
        publisher.send(body)
        self.assertEqual(len(puts), 1)
        self.assertIsNone(publisher.pending)

    def test_competing_writer_is_not_overwritten(self):
        doc = None
        def api(path, body=None, method='GET'):
            nonlocal doc
            if method == 'GET':
                if doc is None:
                    raise HTTPError(path, 404, 'missing', {}, None)
                return doc.copy()
            doc = dict(body, latestRevisionId='first')
            return doc.copy()
        publisher = watch.Publisher('task', 'b'*64, api)
        publisher.send(publisher.marker+'\ninitial')
        doc = dict(doc, body=publisher.marker+'\nowner edit', latestRevisionId='owner')
        with self.assertRaisesRegex(ValueError, 'other_writer'):
            publisher.send(publisher.marker+'\nnext')
        self.assertTrue(doc['body'].endswith('owner edit'))

    def test_progress_does_not_invent_percentage_or_hide_missing_heartbeat(self):
        state = dict(manifest_sha256='a'*64, status='running', health='heartbeat_unavailable',
                     observation=dict(ticks=10, pages=2))
        body = watch.render(state, 100000)
        self.assertIn('Bản cũ chưa hỗ trợ', body)
        self.assertNotIn('%', body)
        state.update(health='heartbeat_stale', phase='poll_wait', heartbeat_at_msc=1)
        self.assertIn('Cảnh báo', watch.render(state, 100000))
        state['health'] = 'responsive'
        self.assertIn('Đang chờ trang', watch.render(state, 100000))

    def test_pending_running_message_cannot_acknowledge_later_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            binary = Path(temp)/'fixture.exe'
            binary.touch()
            running = dict(schema_version='mt5-shadow-lifecycle-v1', status='running',
                health='responsive', manifest_sha256='a'*64, deadline_msc=int(watch.time.time()*1000)+60000,
                execution_capability=False)
            failed = dict(running, status='failed', reason='shadow_fixture_failed')
            bodies = []
            class Publisher:
                def __init__(self, *_):
                    pass
                def send(self, body):
                    bodies.append(body)
                    if len(bodies) == 1:
                        raise TimeoutError('delivery failed')
            argv = ['watch', '--binary', str(binary), '--state-dir', temp,
                    '--task', '00000000-0000-0000-0000-000000000001',
                    '--company', '00000000-0000-0000-0000-000000000002']
            with patch.object(sys, 'argv', argv), patch.object(watch, 'status',
                side_effect=[copy.deepcopy(s) for s in [running, running, failed, failed]]), \
                patch.object(watch, 'Publisher', Publisher), patch.object(watch.time, 'sleep'), \
                patch.object(watch, 'api', return_value={'companyId':argv[-1]}), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(watch.main(), 2)
            self.assertEqual(len(bodies), 3)
            self.assertEqual(bodies[0], bodies[1])
            self.assertIn('Đã dừng vì lỗi', bodies[-1])
            self.assertIn('shadow_fixture_failed', bodies[-1])


if __name__ == '__main__':
    unittest.main()

import ctypes
from contextlib import redirect_stdout
from ctypes import wintypes
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch, Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import forex_study_batch as batch


def await_file(path):
    end = time.monotonic()+10
    while not path.exists():
        if time.monotonic() > end:
            raise TimeoutError('test worker did not start')
        time.sleep(0.05)
    return batch.read(path)


@unittest.skipUnless(os.name == 'nt', 'Windows process ownership contract')
class OwnedProcessTests(unittest.TestCase):
    def test_supervisor_crash_also_stops_owned_worker(self):
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            script = root/'child.py'
            script.write_text('import os,sys,time\nfrom pathlib import Path\n'
                              'Path(sys.argv[1]).write_text(str(os.getpid()))\ntime.sleep(60)\n')
            source = ('import sys,time; from pathlib import Path; '
                      f'sys.path[:]={sys.path!r}; from forex_study_batch import OwnedPython; '
                      f'owner=OwnedPython({[str(script), str(root/"pid.json")]!r}, '
                      'stdout=sys.stdout,stderr=sys.stderr); time.sleep(60)')
            with (root/'out.log').open('w') as out, (root/'err.log').open('w') as err:
                parent = subprocess.Popen([sys._base_executable, '-c', source], stdout=out, stderr=err,
                                          creationflags=subprocess.CREATE_NO_WINDOW)
                handle = None
                try:
                    pid = await_file(root/'pid.json')
                    handle = kernel.OpenProcess(0x100000, False, pid)
                    self.assertTrue(handle)
                    parent.terminate()
                    parent.wait(timeout=5)
                    self.assertEqual(kernel.WaitForSingleObject(handle, 5000), 0)
                finally:
                    if parent.poll() is None:
                        parent.terminate()
                    parent.wait(timeout=5)
                    if handle:
                        kernel.CloseHandle(handle)

    def test_closing_owner_kills_worker_and_spawned_grandchild(self):
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            script = root/'child.py'
            script.write_text("import json,subprocess,sys,time,os\nfrom pathlib import Path\nimport pydantic\n"
                "child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'])\n"
                "Path(sys.argv[1]).write_text(json.dumps(dict(pid=os.getpid(),child=child.pid)))\n"
                "time.sleep(60)\n", encoding='utf-8')
            with (root/'out.log').open('w') as out, (root/'err.log').open('w') as err:
                owner = batch.OwnedPython([script, root/'ready.json'], stdout=out, stderr=err)
                handles = []
                try:
                    identity = await_file(root/'ready.json')
                    self.assertEqual(identity['pid'], owner.process.pid)
                    for pid in (identity['pid'], identity['child']):
                        handle = kernel.OpenProcess(0x100000, False, pid)
                        self.assertTrue(handle)
                        handles.append(handle)
                    owner.close()
                    for handle in handles:
                        self.assertEqual(kernel.WaitForSingleObject(handle, 5000), 0)
                finally:
                    owner.close()
                    for handle in handles:
                        kernel.CloseHandle(handle)


class ResultTests(unittest.TestCase):
    def batch_fixture(self, root, names):
        protocol = root/'protocol.md'
        protocol.write_text('registered controller fixture')
        inputs = dict(warmup={}, development={})
        batch.save(root/'input.json', dict(schema='forex-h4-inputs-v1', **inputs))
        expected = dict(input_manifest=str(root/'input.json'), inputs=inputs,
            protocol=str(protocol), protocol_sha256=batch.digest(protocol))
        config = root/'config.json'
        batch.save(config, dict(jobs={name: dict(expected) for name in names}, development_ticks=100))
        return ['--config', str(config), '--output-dir', str(root/'batch'), '--max-workers', '2']

    def test_actual_queue_handoff_retains_success_when_another_job_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            argv = self.batch_fixture(root, ('probe', 'good', 'bad'))
            probe_finished = threading.Event()
            simultaneous = threading.Barrier(2)
            calls = []
            def worker(name, expected, directory, **kwargs):
                calls.append(name)
                directory.mkdir()
                if name == 'probe':
                    probe_finished.set()
                else:
                    self.assertTrue(probe_finished.is_set())
                    simultaneous.wait(timeout=3)
                result = dict(worker=name, status='failed' if name == 'bad' else 'completed_verified',
                              exit_code=1 if name == 'bad' else 0, elapsed_seconds=0.01)
                batch.save(directory/'terminal.json', result)
                return result
            with patch.object(batch, 'run_job', side_effect=worker), redirect_stdout(io.StringIO()):
                code = batch.main(argv)
            final = batch.read(root/'batch/batch-terminal.json')
            self.assertEqual(code, 1)
            self.assertEqual(final['status'], 'incomplete')
            self.assertEqual(final['completed_jobs'], 2)
            self.assertCountEqual(calls, ['probe', 'good', 'bad'])
            self.assertEqual(len(calls), 3)
            self.assertEqual(batch.read(root/'batch/good/terminal.json')['status'], 'completed_verified')

    def test_actual_queue_does_not_dispatch_pending_jobs_after_cancel(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            argv = self.batch_fixture(root, ('probe', 'pending'))
            def worker(name, expected, directory, **kwargs):
                directory.mkdir()
                (directory.parent/'CANCEL').write_text('fixture owner cancel')
                result = dict(worker=name, status='completed_verified', exit_code=0)
                batch.save(directory/'terminal.json', result)
                return result
            with patch.object(batch, 'run_job', side_effect=worker) as run, redirect_stdout(io.StringIO()):
                self.assertEqual(batch.main(argv), 1)
            self.assertEqual(run.call_count, 1)
            states = {r['worker']: r['status'] for r in batch.read(root/'batch/batch-terminal.json')['workers']}
            self.assertEqual(states, dict(probe='completed_verified', pending='not_started_cancelled'))

    def test_progress_accepts_real_terminal_worker_identity(self):
        with tempfile.TemporaryDirectory() as folder:
            result = batch.progress(Path(folder), {'candidate': dict(worker='candidate',
                status='completed_verified', elapsed_seconds=12)}, time.monotonic(), 100, 30)
            self.assertEqual(result['status'], 'completed_verified')
            self.assertEqual(result['completed_jobs'], 1)
            self.assertEqual(result['workers'][0]['worker'], 'candidate')

    def test_console_keeps_progress_without_repeating_provenance_hashes(self):
        with tempfile.TemporaryDirectory() as folder:
            console = io.StringIO()
            with redirect_stdout(console):
                result = batch.progress(Path(folder), {'candidate': dict(worker='candidate',
                    status='reused_verified', artifact_sha256={'results.json': 'a'*64})},
                    time.monotonic(), 100, 30)
            self.assertNotIn('artifact_sha256', console.getvalue())
            self.assertEqual(json.loads(console.getvalue())['completed'], 1)
            self.assertEqual(result['workers'][0]['artifact_sha256'], {'results.json': 'a'*64})

    def test_nonzero_worker_never_becomes_success_and_skips_result_verification(self):
        with tempfile.TemporaryDirectory() as folder:
            owner = Mock()
            owner.process.poll.return_value = 7
            owner.close.return_value = 7
            owner.process.pid = 123
            expected = dict(input_manifest=str(Path(folder)/'input.json'), candidate='registered',
                protocol='registered.md', account_spec='spec.json', account_spec_sha256='a'*64,
                reuse_scenarios_from=str(Path(folder)/'old/replay'))
            with patch.object(batch, 'OwnedPython', return_value=owner) as spawn, \
                 patch.object(batch, 'verified_result') as verify:
                terminal = batch.run_job('candidate', expected, Path(folder)/'attempt', seconds=1)
            worker_argv=spawn.call_args.args[0]
            self.assertEqual(worker_argv[worker_argv.index('--reuse-scenarios-from')+1],expected['reuse_scenarios_from'])
            verify.assert_not_called()
            self.assertEqual(terminal['status'], 'failed')
            self.assertEqual(terminal['exit_code'], 7)

    def test_timeout_closes_job_and_does_not_report_completion(self):
        with tempfile.TemporaryDirectory() as folder:
            owner = Mock()
            owner.process.poll.return_value = None
            owner.close.return_value = 1
            owner.process.pid = 123
            expected = dict(input_manifest=str(Path(folder)/'input.json'), candidate='registered',
                protocol='registered.md', account_spec='spec.json', account_spec_sha256='a'*64)
            clock = iter([0, 2, 2])
            with patch.object(batch, 'OwnedPython', return_value=owner), \
                 patch.object(batch, 'verified_result') as verify:
                terminal = batch.run_job('candidate', expected, Path(folder)/'attempt',
                                         seconds=1, clock=lambda: next(clock))
            verify.assert_not_called()
            self.assertEqual(terminal['status'], 'timed_out')
            self.assertTrue(owner.close.called)

    def test_exit_zero_with_invalid_artifacts_stays_failed(self):
        with tempfile.TemporaryDirectory() as folder:
            owner = Mock()
            owner.process.poll.return_value = 0
            owner.close.return_value = 0
            owner.process.pid = 123
            expected = dict(input_manifest=str(Path(folder)/'input.json'), candidate='registered',
                protocol='registered.md', account_spec='spec.json', account_spec_sha256='a'*64)
            with patch.object(batch, 'OwnedPython', return_value=owner), \
                 patch.object(batch, 'verified_result', side_effect=ValueError('incomplete evidence')):
                terminal = batch.run_job('candidate', expected, Path(folder)/'attempt', seconds=1)
            self.assertEqual(terminal['status'], 'failed')

    def test_completed_job_is_reused_without_dispatching_a_worker(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            protocol = root/'protocol.md'
            protocol.write_text('registered protocol')
            inputs = dict(warmup={}, development={})
            batch.save(root/'input.json', dict(schema='forex-h4-inputs-v1', **inputs))
            expected = dict(input_manifest=str(root/'input.json'), inputs=inputs,
                protocol=str(protocol), protocol_sha256=batch.digest(protocol))
            config = dict(jobs={'candidate': expected}, development_ticks=100)
            batch.save(root/'config.json', config)
            directory = root/'batch'
            (directory/'candidate').mkdir(parents=True)
            batch.save(directory/'candidate/terminal.json', dict(status='completed_verified'))
            with patch.object(batch, 'verified_result') as verify, patch.object(batch, 'run_job') as run:
                self.assertEqual(batch.main(['--config', str(root/'config.json'), '--output-dir', str(directory)]), 0)
            verify.assert_called_once()
            run.assert_not_called()
            self.assertEqual(batch.read(directory/'batch-terminal.json')['status'], 'completed_verified')

    def test_previous_completed_job_is_reused_in_a_new_batch_without_dispatch(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            protocol = root/'protocol.md'
            protocol.write_text('registered protocol')
            inputs = dict(warmup={}, development={})
            batch.save(root/'input.json', dict(schema='forex-h4-inputs-v1', **inputs))
            expected = dict(input_manifest=str(root/'input.json'), inputs=inputs,
                protocol=str(protocol), protocol_sha256=batch.digest(protocol))
            batch.save(root/'config.json', dict(jobs={'candidate': expected}, development_ticks=100))
            old = root/'old/candidate'
            old.mkdir(parents=True)
            batch.save(old/'terminal.json', dict(status='completed_verified'))
            with patch.object(batch, 'verified_result', return_value={'artifact_sha256': {'results.json': 'pinned'}}), \
                 patch.object(batch, 'run_job') as run:
                code = batch.main(['--config', str(root/'config.json'), '--output-dir', str(root/'new'),
                                   '--reuse-from', str(root/'old')])
            self.assertEqual(code, 0)
            run.assert_not_called()
            final = batch.read(root/'new/batch-terminal.json')
            self.assertEqual(final['workers'][0]['result_dir'], str((old/'replay').resolve()))


if __name__ == '__main__':
    unittest.main()

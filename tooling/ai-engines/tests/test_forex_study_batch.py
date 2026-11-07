import ctypes
from contextlib import redirect_stdout
from ctypes import wintypes
import io
import json
import os
from pathlib import Path
import shutil
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


class SourceSelectionTests(unittest.TestCase):
    def test_isolated_checkout_is_used_by_worker_and_evidence_reviewer(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/'scripts').mkdir()
            (root/'scripts/forex_h4_pilot.py').write_text('')
            package = root/'trading_workspace_v2'
            shutil.copytree(batch.V2/'trading_workspace_v2', package,
                            ignore=shutil.ignore_patterns('__pycache__'))
            source = (f'import sys; sys.path[:]={sys.path!r}; '
                      f'import forex_study_batch as batch; batch.configure_source_root({str(root)!r}); '
                      'from trading_workspace_v2 import forex_study_registration as registry; '
                      'import strategy_evidence as evidence; '
                      f'assert registry.__file__.startswith({str(root)!r}); '
                      'assert evidence.inspect_registered_manifest is registry.inspect_registered_manifest; '
                      'from unittest.mock import patch; '
                      'expected=dict(candidate="fixture", inputs={}, account_spec_sha256="a", protocol_sha256="b"); '
                      'dossier=dict(candidate="fixture",protocol_sha256="b",protocol_content_verified=True, '
                      'source_drift=[],unavailable_sources=[]); '
                      'manifest=dict(inputs={},observed_account_spec=dict(sha256="a"),runtime=registry.runtime_binding()); '
                      'inspect_patch=patch.object(evidence,"inspect",return_value=dossier); '
                      'inspect_mock=inspect_patch.start(); '
                      'read_patch=patch.object(batch,"read",return_value=manifest); read_patch.start(); '
                      'batch.verified_result(batch.V2,expected); '
                      'assert inspect_mock.call_args.kwargs["source_root"] == batch.V2; '
                      'print("isolated_source_verified")')
            result = subprocess.run([sys._base_executable, '-c', source], capture_output=True,
                                    text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('isolated_source_verified', result.stdout)

    def test_switching_source_after_product_import_fails_without_mutating_path(self):
        from trading_workspace_v2 import forex_study_registration
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/'scripts').mkdir()
            (root/'trading_workspace_v2').mkdir()
            (root/'scripts/forex_h4_pilot.py').write_text('')
            (root/'trading_workspace_v2/forex_study_registration.py').write_text('')
            previous_root, previous_paths = batch.V2, list(sys.path)
            with self.assertRaisesRegex(ValueError, 'source_modules_already_loaded'):
                batch.configure_source_root(root)
            self.assertEqual(batch.V2, previous_root)
            self.assertEqual(sys.path, previous_paths)


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
    @unittest.skipUnless(os.name == 'nt', 'Windows sharing race')
    def test_locked_progress_receipt_does_not_stop_a_running_job(self):
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                      wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        kernel.CreateFileW.restype = wintypes.HANDLE
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            receipt = root/'candidate/replay/receipt.json'
            receipt.parent.mkdir(parents=True)
            receipt.write_text(json.dumps(dict(stage='reference',observed_ticks=20)))
            handle = kernel.CreateFileW(str(receipt),0x80000000,0,None,3,0x80,None)
            self.assertNotEqual(handle,wintypes.HANDLE(-1).value)
            try:
                with self.assertRaises(PermissionError):
                    batch.read(receipt)
                with redirect_stdout(io.StringIO()):
                    snapshot = batch.progress(root,{'candidate':dict(status='running')},time.monotonic(),100,30)
                self.assertEqual(snapshot['status'],'running')
                self.assertEqual(snapshot['workers'][0]['progress_read_error']['error_type'],'PermissionError')
                self.assertFalse((root/'CANCEL').exists())
            finally:
                kernel.CloseHandle(handle)
            with redirect_stdout(io.StringIO()):
                recovered = batch.progress(root,{'candidate':dict(status='running')},time.monotonic(),100,30)
            self.assertEqual(recovered['workers'][0]['observed_ticks'],20)
            self.assertNotIn('progress_read_error',recovered['workers'][0])

    def test_progress_projection_write_errors_are_reported_without_cancelling_job(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with patch.object(batch,'save',side_effect=PermissionError('private payload')), \
                 patch.object(Path,'replace',side_effect=PermissionError('private payload')), \
                 redirect_stdout(io.StringIO()) as console:
                snapshot = batch.progress(root,{'candidate':dict(status='running')},time.monotonic(),100,30)
            self.assertEqual(snapshot['status'],'running')
            self.assertEqual({e['file'] for e in snapshot['projection_errors']},{'progress.json','PROGRESS.md'})
            self.assertNotIn('private payload',console.getvalue())
            self.assertFalse((root/'CANCEL').exists())

    def test_completed_result_cannot_be_reused_with_changed_runtime(self):
        from trading_workspace_v2.forex_study_registration import runtime_binding
        runtime=runtime_binding()
        expected=dict(candidate='fixture',inputs={},account_spec_sha256='a'*64,protocol_sha256='b'*64)
        dossier=dict(candidate='fixture',protocol_sha256='b'*64,protocol_content_verified=True,
                     source_drift=[],unavailable_sources=[])
        manifest=dict(inputs={},observed_account_spec=dict(sha256='a'*64),runtime=runtime)
        with patch('strategy_evidence.inspect',return_value=dossier),patch.object(batch,'read',return_value=manifest):
            self.assertEqual(batch.verified_result(Path('fixture'),expected),dossier)
            manifest['runtime']=dict(runtime,pydantic='different-version')
            with self.assertRaisesRegex(ValueError,'binding_mismatch'):
                batch.verified_result(Path('fixture'),expected)

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

    def test_parallel_start_dispatches_two_before_either_completes_and_preserves_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            argv = self.batch_fixture(root, ('good', 'bad')) + ['--parallel-start']
            simultaneous = threading.Barrier(2)
            def worker(name, expected, directory, **kwargs):
                directory.mkdir()
                simultaneous.wait(timeout=3)
                result = dict(worker=name, status='failed' if name == 'bad' else 'completed_verified')
                batch.save(directory/'terminal.json', result)
                return result
            with patch.object(batch, 'run_job', side_effect=worker), redirect_stdout(io.StringIO()):
                self.assertEqual(batch.main(argv), 1)
            final = batch.read(root/'batch/batch-terminal.json')
            self.assertEqual(final['completed_jobs'], 1)
            self.assertEqual(final['status'], 'incomplete')
            self.assertTrue(batch.read(root/'batch/batch-manifest.json')['parallel_start'])
            self.assertEqual(batch.read(root/'batch/good/terminal.json')['status'], 'completed_verified')

    def test_shared_preparation_finishes_before_dispatch_and_is_recorded(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            argv = self.batch_fixture(root, ('one', 'two')) + ['--prepare-inputs', '--parallel-start']
            config = batch.read(root/'config.json')
            for job in config['jobs'].values():
                job['prepared_inputs_dir'] = str(root/'shared')
            batch.save(root/'config.json', config)
            seen_ids = []
            def prepare(inputs, **kwargs):
                seen_ids.append(id(kwargs['seen']))
                kwargs['on_progress'](dict(kind='quality', role='warmup', ticks=1, stage='verified'))
                return []
            def worker(name, expected, directory, **kwargs):
                self.assertEqual(batch.read(root/'batch/input-preparation.json')['status'], 'verified')
                self.assertEqual(batch.input_cache_dirs(expected), (str(root/'shared'), str(root/'shared')))
                directory.mkdir()
                terminal = dict(status='completed_verified', worker=name)
                batch.save(directory/'terminal.json', terminal)
                return terminal
            with patch('trading_workspace_v2.forex_input_preparation.prepare_input_set', side_effect=prepare), \
                 patch.object(batch, 'run_job', side_effect=worker), redirect_stdout(io.StringIO()):
                self.assertEqual(batch.main(argv), 0)
            self.assertEqual(len(seen_ids), 2)
            self.assertEqual(len(set(seen_ids)), 1)
            self.assertTrue(batch.read(root/'batch/batch-manifest.json')['prepare_inputs'])

    def test_preparation_cancel_dispatches_no_worker(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            argv = self.batch_fixture(root, ('one',)) + ['--prepare-inputs']
            def prepare(inputs, **kwargs):
                (root/'batch/CANCEL').write_text('owner cancellation')
                kwargs['on_progress'](dict(kind='quality', role='warmup', ticks=0, stage='preparing'))
            with patch('trading_workspace_v2.forex_input_preparation.prepare_input_set', side_effect=prepare), \
                 patch.object(batch, 'run_job') as worker, redirect_stdout(io.StringIO()):
                self.assertEqual(batch.main(argv), 1)
            worker.assert_not_called()
            self.assertEqual(batch.read(root/'batch/input-preparation.json')['status'], 'cancelled')
            self.assertFalse((root/'batch/batch-failure.json').exists())

    def test_hourly_warmup_cache_is_prepared_once_before_workers_start(self):
        from trading_workspace_v2.forex_coarse_input import load_coarse_hours
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            argv = self.batch_fixture(root, ('one', 'two')) + ['--prepare-inputs', '--parallel-start']
            raw = root/'warmup.csv'
            raw.write_text('DateTime,Bid,Ask,Volume\n'
                '20221201 00:00:00.000,1.10000,1.10020,1\n'
                '20221201 00:01:00.000,1.10010,1.10030,1\n'
                '20221201 01:00:00.000,1.10020,1.10040,1\n')
            item = dict(path=str(raw), sha256=batch.digest(raw), first_day='20221201', last_day='20221201')
            config = batch.read(root/'config.json')
            for job in config['jobs'].values():
                job['warmup_hours_cache_dir'] = str(root/'hours')
                job['inputs']['warmup'] = item
            batch.save(root/'input.json', dict(schema='forex-h4-inputs-v1', **config['jobs']['one']['inputs']))
            batch.save(root/'config.json', config)
            def worker(name, expected, directory, **kwargs):
                hours, proof = load_coarse_hours(raw, cache_dir=root/'hours',
                    **{key: item[key] for key in ('sha256', 'first_day', 'last_day')})
                self.assertEqual((len(hours), proof['ticks']), (2, 3))
                self.assertEqual(str(hours[0].mid.open), '1.10010')
                directory.mkdir()
                terminal = dict(status='completed_verified', worker=name)
                batch.save(directory/'terminal.json', terminal)
                return terminal
            with patch('trading_workspace_v2.forex_input_preparation.prepare_input_set', return_value=[]), \
                 patch.object(batch, 'run_job', side_effect=worker), redirect_stdout(io.StringIO()):
                self.assertEqual(batch.main(argv), 0)
            prepared = batch.read(root/'batch/input-preparation.json')
            self.assertEqual(len(prepared['records']), 1)
            self.assertEqual(prepared['records'][0]['kind'], 'hourly_warmup')
            self.assertEqual(len(list((root/'hours').glob('coarse-hours-*.json'))), 1)

    def test_registered_execution_caps_reject_dispatch_before_input_preparation(self):
        cases = [dict(max_numeric_workers=1), dict(worker_timeout_seconds=100),
                 dict(batch_deadline_seconds=100), dict(parallel_start=False),
                 dict(max_numeric_workers=True)]
        for limits in cases:
            with self.subTest(limits=limits), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                argv = self.batch_fixture(root, ('one',)) + ['--prepare-inputs', '--parallel-start']
                config = batch.read(root/'config.json')
                config['jobs']['one'].update(candidate='fixture',account_spec_sha256='a'*64,
                    study_registration=str(root/'registration.json'),study_registration_sha256='b'*64)
                batch.save(root/'config.json', config)
                with patch('trading_workspace_v2.forex_study_registration.load_registration',
                           return_value=dict(execution=limits)), \
                     patch('trading_workspace_v2.forex_study_registration.validate_registration'), \
                     patch.object(batch, 'prepare_pending_inputs') as prepare, \
                     patch.object(batch, 'run_job') as worker, redirect_stdout(io.StringIO()):
                    with self.assertRaisesRegex(ValueError, 'registered_'):
                        batch.main(argv)
                prepare.assert_not_called()
                worker.assert_not_called()
                self.assertEqual(batch.read(root/'batch/batch-failure.json')['error_type'], 'ValueError')

    def test_hourly_preparation_progress_exposes_a_numeric_tick_counter(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            item = dict(path=str(root/'warmup.csv'),sha256='a'*64,first_day='20221201',last_day='20221201')
            jobs = {'one': dict(inputs=dict(warmup=item),warmup_hours_cache_dir=str(root/'hours'))}
            observed = []
            def prepare(*args, **kwargs):
                kwargs['on_progress'](dict(stage='coarse_prepare',ticks=65536,elapsed_seconds=6))
                return [], dict(ticks=65536)
            with patch('trading_workspace_v2.forex_input_preparation.prepare_input_set',return_value=[]), \
                 patch('trading_workspace_v2.forex_coarse_input.prepare_coarse_hours',side_effect=prepare), \
                 redirect_stdout(io.StringIO()):
                batch.prepare_pending_inputs(jobs,['one'],root,began=time.monotonic(),deadline=30,
                                             on_observe=observed.append)
            self.assertEqual(observed[-1]['ticks'],65536)
            self.assertTrue(all(type(event['ticks']) is int for event in observed))

    def test_preparation_observation_write_failure_does_not_invalidate_prepared_data(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            original = batch.save
            def save(path, value):
                if Path(path).name == 'input-preparation.json':
                    raise PermissionError('locked projection')
                return original(path, value)
            def prepare(inputs, **kwargs):
                kwargs['on_progress'](dict(kind='quality', role='warmup', ticks=0, stage='preparing'))
                return [dict(kind='quality', role='warmup', ticks=4)]
            with patch('trading_workspace_v2.forex_input_preparation.prepare_input_set', side_effect=prepare), \
                 patch.object(batch, 'save', side_effect=save), redirect_stdout(io.StringIO()):
                summary = batch.prepare_pending_inputs({'one': dict(inputs={})}, ['one'], output,
                                                       began=time.monotonic(), deadline=30)
            self.assertEqual(summary['status'], 'verified')
            self.assertEqual(len(summary['records']), 1)
            self.assertEqual(summary['projection_errors'][0]['error_type'], 'PermissionError')

    def test_cpu_summary_reports_missing_coverage_and_excludes_reused_work(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name, receipt in (('new', dict(process_cpu_seconds=3)), ('legacy', {})):
                directory = root/name/'replay'
                directory.mkdir(parents=True)
                batch.save(directory/'receipt.json', receipt)
            states = dict(new=dict(status='completed_verified'), legacy=dict(status='completed_verified'),
                          reused=dict(status='reused_verified', process_cpu_seconds=1000))
            with redirect_stdout(io.StringIO()):
                perf = batch.progress(root, states, time.monotonic(), 100, 30)['performance']
            self.assertEqual(perf['cpu_coverage_jobs'], 1)
            self.assertIsNone(perf['new_jobs_cpu_seconds'])
            self.assertEqual(perf['reused_jobs'], 1)

    def test_conflicting_bundle_and_individual_cache_directories_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'choose_prepared_bundle'):
            batch.input_cache_dirs(dict(prepared_inputs_dir='shared', tick_cache_dir='other'))

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
                study_registration='study.json',study_registration_sha256='b'*64,
                inspection_cache_dir=str(Path(folder)/'prepared'),
                tick_cache_dir=str(Path(folder)/'ticks'),
                reuse_scenarios_from=str(Path(folder)/'old/replay'))
            with patch.object(batch, 'OwnedPython', return_value=owner) as spawn, \
                 patch.object(batch, 'verified_result') as verify:
                terminal = batch.run_job('candidate', expected, Path(folder)/'attempt', seconds=1)
            worker_argv=spawn.call_args.args[0]
            self.assertEqual(worker_argv[worker_argv.index('--reuse-scenarios-from')+1],expected['reuse_scenarios_from'])
            self.assertEqual(worker_argv[worker_argv.index('--study-registration')+1],expected['study_registration'])
            self.assertEqual(worker_argv[worker_argv.index('--study-registration-sha256')+1],expected['study_registration_sha256'])
            self.assertEqual(worker_argv[worker_argv.index('--inspection-cache-dir')+1],expected['inspection_cache_dir'])
            self.assertEqual(worker_argv[worker_argv.index('--tick-cache-dir')+1],expected['tick_cache_dir'])
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

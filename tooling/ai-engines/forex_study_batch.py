"""Finite offline study supervisor; retains completed jobs and owns Windows children."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import runpy
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[2]
V2 = ROOT/'projects/trader/foundation_v2'
sys.path.insert(0, str(V2))


def configure_source_root(path):
    """Select one local product checkout before importing its financial models."""
    global V2
    selected = Path(path).resolve()
    required = ('scripts/forex_h4_pilot.py', 'trading_workspace_v2/forex_study_registration.py')
    if any(not (selected/name).is_file() for name in required):
        raise ValueError('invalid_forex_source_root')
    for name, module in tuple(sys.modules.items()):
        if name == 'trading_workspace_v2' or name.startswith('trading_workspace_v2.') or name == 'forex_h4_pilot':
            loaded = getattr(module, '__file__', None)
            if loaded and not Path(loaded).resolve().is_relative_to(selected):
                raise ValueError('source_modules_already_loaded_use_new_process')
    V2 = selected
    sys.path.insert(0, str(V2))


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def observe_receipt(path):
    # Optional telemetry can be briefly inaccessible during Windows replacement.
    # Keep mandatory config/result/terminal reads strict through read().
    for attempt in range(4):
        try:
            receipt = read(path)
            if not isinstance(receipt, dict):
                raise ValueError('receipt is not an object')
            return receipt, None
        except FileNotFoundError:
            return None, None
        except PermissionError as error:
            if getattr(error, 'winerror', None) in (5, 32, 33) and attempt < 3:
                time.sleep(0.05)
                continue
            return None, dict(error_type=type(error).__name__, winerror=getattr(error, 'winerror', None))
        except (OSError, ValueError) as error:
            return None, dict(error_type=type(error).__name__)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    # Reuse the research writer's Windows sharing-lock handling.
    sys.path.insert(0, str(V2/'scripts'))
    from forex_h4_pilot import write_json
    write_json(Path(path), value)


class OwnedPython:
    def __init__(self, argv, *, stdout, stderr):
        from trading_workspace_v2.nautilus_worker import _WorkerOwnedJob
        self.job = _WorkerOwnedJob()
        self.process = None
        try:
            # The base interpreter avoids the venv launcher/real-Python PID split.
            # Restore the parent's import paths only inside this child. Its stdin
            # gate runs no study/subprocess before the Job Object owns it.
            self.process = subprocess.Popen(
                [sys._base_executable, '-u', str(Path(__file__).resolve()), '--_worker'],
                stdin=subprocess.PIPE, stdout=stdout, stderr=stderr, text=True,
                cwd=V2, creationflags=subprocess.CREATE_NO_WINDOW)
            self.job.assign(self.process)
            self.process.stdin.write(json.dumps(dict(argv=list(map(str, argv)), paths=sys.path))+'\n')
            self.process.stdin.close()
        except BaseException:
            self.job.close()
            if self.process is not None:
                # If assignment failed, the direct child is still stdin-gated.
                if self.process.poll() is None:
                    self.process.terminate()
                self.process.wait(timeout=10)
            raise

    def close(self):
        self.job.close()
        return self.process.wait(timeout=10)


def verified_result(directory, expected, *, source_root=None):
    source_root = V2 if source_root is None else source_root
    from strategy_evidence import inspect
    from trading_workspace_v2.forex_study_registration import runtime_binding
    dossier = inspect(directory, source_root=source_root)
    manifest = read(directory/'manifest.json')
    if (dossier['candidate'] != expected['candidate']
            or manifest['inputs'] != expected['inputs']
            or manifest['observed_account_spec']['sha256'] != expected['account_spec_sha256']
            or dossier['protocol_sha256'] != expected['protocol_sha256']
            or (manifest.get('study_registration') or {}).get('sha256') != expected.get('study_registration_sha256')
            or manifest.get('runtime') != runtime_binding()
            or not dossier['protocol_content_verified']
            or (dossier['source_drift'] and not expected.get('benchmark_only'))
            or dossier['unavailable_sources']):
        raise ValueError('completed_result_binding_mismatch')
    return dossier


def input_cache_dirs(expected):
    bundle = expected.get('prepared_inputs_dir')
    if bundle and (expected.get('inspection_cache_dir') or expected.get('tick_cache_dir')):
        raise ValueError('choose_prepared_bundle_or_individual_cache_directories')
    return bundle or expected.get('inspection_cache_dir'), bundle or expected.get('tick_cache_dir')


class PreparationStopped(RuntimeError):
    pass


def prepare_pending_inputs(jobs, pending, output, *, began, deadline, on_observe=None):
    from trading_workspace_v2.forex_input_preparation import prepare_input_set
    seen, hourly_seen, records, observation_errors = set(), set(), [], []
    last_emit = 0
    def record_error(error):
        item = dict(file='input-preparation.json', error_type=type(error).__name__)
        if item not in observation_errors:
            observation_errors.append(item)
    def notify(event):
        nonlocal last_emit
        if (output/'CANCEL').exists():
            raise PreparationStopped('cancelled')
        if time.monotonic()-began > deadline:
            raise PreparationStopped('deadline')
        now = time.monotonic()
        if event['ticks'] == 0 or event['stage'] == 'verified' or now-last_emit >= 5:
            # Observation failure must not invalidate already prepared input data.
            try:
                save(output/'input-preparation.json', dict(status='preparing', records=records,
                    current=event, pid=os.getpid(), updated_at_utc=datetime.now(timezone.utc).isoformat()))
            except OSError as error:
                record_error(error)
            print(json.dumps(dict(event, phase='input_preparation', projection_errors=observation_errors)), flush=True)
            if on_observe:
                on_observe(event)
            last_emit = now
    for name in pending:
        inspection, ticks = input_cache_dirs(jobs[name])
        records.extend(prepare_input_set(jobs[name]['inputs'], inspection_cache_dir=inspection,
            tick_cache_dir=ticks, seen=seen, on_progress=notify))
        hours_dir = jobs[name].get('warmup_hours_cache_dir')
        if hours_dir:
            from trading_workspace_v2.forex_coarse_input import prepare_coarse_hours
            item = jobs[name]['inputs']['warmup']
            key = (str(Path(hours_dir).resolve()), item['sha256'], item['first_day'], item['last_day'])
            if key not in hourly_seen:
                event = dict(kind='hourly_warmup', role='warmup', stage='preparing', ticks=0)
                notify(event)
                _, proof = prepare_coarse_hours(Path(item['path']), cache_dir=hours_dir,
                    **{field: item[field] for field in ('sha256', 'first_day', 'last_day')},
                    on_progress=lambda count: notify(dict(event, ticks=count)),
                    deadline_seconds=max(1, deadline-(time.monotonic()-began)))
                notify(dict(event, stage='verified', ticks=proof['ticks']))
                records.append(dict(kind='hourly_warmup', role='warmup', **proof))
                hourly_seen.add(key)
    summary = dict(status='verified', records=records, projection_errors=observation_errors,
                   elapsed_seconds=round(time.monotonic()-began, 3))
    try:
        save(output/'input-preparation.json', summary)
    except OSError as error:
        record_error(error)
    print(json.dumps(dict(stage='input_preparation_finished', status='verified',
        prepared_entries=len(records), projection_errors=observation_errors)), flush=True)
    return summary


def run_job(name, expected, directory, *, seconds, clock=time.monotonic):
    directory.mkdir(parents=True, exist_ok=False)
    replay = directory/'replay'
    argv = [str(V2/'scripts/forex_h4_pilot.py'), '--input-dir', str(Path(expected['input_manifest']).parent),
        '--input-manifest', expected['input_manifest'], '--output-dir', str(replay),
        '--candidate', expected['candidate'], '--research-protocol', expected['protocol'],
        '--account-spec', expected['account_spec'], '--account-spec-sha256', expected['account_spec_sha256']]
    if expected.get('reuse_scenarios_from'):
        argv.extend(['--reuse-scenarios-from', expected['reuse_scenarios_from']])
    inspection, ticks = input_cache_dirs(expected)
    if inspection:
        argv.extend(['--inspection-cache-dir', inspection])
    if ticks:
        argv.extend(['--tick-cache-dir', ticks])
    if expected.get('warmup_hours_cache_dir'):
        argv.extend(['--warmup-hours-cache-dir', expected['warmup_hours_cache_dir']])
    if expected.get('benchmark_only'):
        argv.append('--benchmark-only')
    if expected.get('study_registration'):
        argv.extend(['--study-registration', expected['study_registration'],
                     '--study-registration-sha256', expected['study_registration_sha256']])
    began = clock()
    terminal = dict(worker=name, status='failed', started_at_utc=datetime.now(timezone.utc).isoformat())
    owner = None
    try:
        with (directory/'stdout.log').open('w', encoding='utf-8') as out, \
             (directory/'stderr.log').open('w', encoding='utf-8') as err:
            owner = OwnedPython(argv, stdout=out, stderr=err)
            save(directory/'process.json', dict(pid=owner.process.pid,
                interpreter=sys._base_executable, stdin_gated_job_ownership=True,
                started_at_utc=terminal['started_at_utc'], argv=argv))
            while owner.process.poll() is None:
                if (directory.parent/'CANCEL').exists():
                    terminal['status'] = 'cancelled'
                    break
                if clock()-began > seconds:
                    terminal['status'] = 'timed_out'
                    break
                time.sleep(0.2)
            code = owner.close()
            terminal['exit_code'] = code
            if terminal['status'] not in {'cancelled', 'timed_out'}:
                if code != 0:
                    terminal['error_code'] = 'worker_nonzero_exit'
                else:
                    dossier = verified_result(replay, expected)
                    save(directory/'dossier.json', dossier)
                    terminal['status'] = 'completed_verified'
    except Exception as error:
        terminal.update(status='failed', error_code='job_verification_or_supervision_failed',
                        error_type=type(error).__name__)
    finally:
        if owner is not None:
            owner.close()
        terminal.update(elapsed_seconds=round(clock()-began, 3),
                        finished_at_utc=datetime.now(timezone.utc).isoformat())
        save(directory/'terminal.json', terminal)
    return terminal


def progress(output, states, began, total_ticks, deadline):
    rows = []
    for name, state in states.items():
        row = dict(state, worker=name)
        row.setdefault('result_dir', str(output/name/'replay'))
        receipt_path = output/name/'replay/receipt.json'
        receipt, observation_error = observe_receipt(receipt_path)
        if observation_error:
            row['progress_read_error'] = observation_error
        if receipt is not None:
            row.update({k: receipt.get(k) for k in ('stage', 'observed_ticks', 'elapsed_seconds', 'pid', 'updated_at_utc',
                'phase_wall_seconds', 'phase_cpu_seconds', 'process_cpu_seconds')})
            row['scenario_fraction'] = (receipt.get('observed_ticks', 0)/total_ticks
                                        if receipt.get('stage') in {'reference', 'cost-stress'} else None)
        rows.append(row)
    elapsed = time.monotonic()-began
    status = 'running' if any(s['status'] in {'queued', 'running'} for s in states.values()) else \
        'completed_verified' if all(s['status'] in {'completed_verified', 'reused_verified'} for s in states.values()) else 'incomplete'
    snapshot = dict(schema='forex-study-batch-v1', status=status, updated_at_utc=datetime.now(timezone.utc).isoformat(),
        elapsed_seconds=round(elapsed, 2), deadline_seconds=deadline, workers=rows,
        completed_jobs=sum(s['status'] in {'completed_verified', 'reused_verified'} for s in states.values()),
        total_jobs=len(states), model_calls=0, broker_calls=0, holdout_read=False)
    new_rows = [row for row in rows if row['status'] == 'completed_verified']
    known_cpu = [row['process_cpu_seconds'] for row in new_rows
                 if type(row.get('process_cpu_seconds')) in (int, float)
                 and math.isfinite(row['process_cpu_seconds']) and row['process_cpu_seconds'] >= 0]
    snapshot['performance'] = dict(wall_seconds=round(elapsed, 2), new_completed_jobs=len(new_rows),
        cpu_coverage_jobs=len(known_cpu), new_jobs_cpu_seconds=sum(known_cpu) if new_rows and len(known_cpu)==len(new_rows) else None,
        reused_jobs=sum(row['status']=='reused_verified' for row in rows))
    projection_errors = []
    lines = ['# Nghiên cứu Forex', '', f'Cập nhật UTC: {snapshot["updated_at_utc"]}',
        f'\nTrạng thái: **{status}** · Xong {snapshot["completed_jobs"]}/{len(states)} ứng viên · Đã chạy {elapsed/60:.1f} phút', '',
        '| Ứng viên | Trạng thái | Bước | Tick / scenario |', '|---|---|---|---:|']
    for row in rows:
        ticks = row.get('observed_ticks')
        stage = 'Tạm không đọc được tiến độ' if row.get('progress_read_error') else row.get('stage') or '—'
        lines.append(f'| {row["worker"]} | {row["status"]} | {stage} | {ticks if ticks is not None else "—"} / {total_ticks} |')
    lines += ['', 'Xác minh dữ liệu chưa có % hoặc ETA đáng tin. Tiến độ tick chỉ áp dụng scenario đang chạy.',
        f'CPU worker mới: {snapshot["performance"]["new_jobs_cpu_seconds"] if snapshot["performance"]["new_jobs_cpu_seconds"] is not None else "chưa đủ số đo"} giây; coverage {len(known_cpu)}/{len(new_rows)}. Không cộng job reused vào thời gian tính mới.',
        'Mỗi ứng viên chạy reference và cost-stress. Chỉ completed_verified mới có dossier đã kiểm.',
        'Giữ kết quả đã xong; không tự retry job lỗi. CANCEL cạnh file này sẽ hủy các job chưa xong.',
        'Dữ liệu development đã dùng; chưa OOS/prop qualification. Không model/broker/holdout.',
        'progress.json là projection của terminal.json + receipt.json; không thay ledger/task Paperclip.']
    temporary = output/'PROGRESS.tmp'
    try:
        temporary.write_text('\n'.join(lines)+'\n', encoding='utf-8')
        temporary.replace(output/'PROGRESS.md')
    except OSError as error:
        projection_errors.append(dict(file='PROGRESS.md', error_type=type(error).__name__))
    snapshot['projection_errors'] = projection_errors
    try:
        save(output/'progress.json', snapshot)
    except OSError as error:
        projection_errors.append(dict(file='progress.json', error_type=type(error).__name__))
    print(json.dumps(dict(status=status, completed=snapshot['completed_jobs'],
        elapsed_seconds=snapshot['elapsed_seconds'], projection_errors=projection_errors, workers=[
            {key: row[key] for key in ('worker', 'status', 'stage', 'observed_ticks', 'progress_read_error') if key in row}
            for row in rows])), flush=True)
    return snapshot


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--max-workers', type=int, choices=(1, 2, 3, 4, 5), default=2)
    parser.add_argument('--source-root', type=Path,
                        help='Explicit local foundation_v2 checkout; must be selected before product imports')
    parser.add_argument('--worker-seconds', type=int, default=1800)
    parser.add_argument('--deadline-seconds', type=int, default=5400)
    parser.add_argument('--reuse-from', type=Path, action='append', default=[],
                        help='Read and verify completed jobs from earlier batches; partial jobs are never resumed')
    parser.add_argument('--parallel-start', action='store_true',
                        help='Start up to max-workers immediately when the study protocol permits; full worker validation remains enabled')
    parser.add_argument('--prepare-inputs', action='store_true',
                        help='Prepare and verify shared caches once before dispatch, using each job cache directory')
    args = parser.parse_args(argv)
    if args.source_root:
        configure_source_root(args.source_root)
    if min(args.worker_seconds, args.deadline_seconds) <= 0:
        parser.error('deadlines must be positive')
    config = read(args.config)
    jobs = config['jobs']
    if not jobs or any(not name.replace('-', '').isalnum() for name in jobs):
        raise ValueError('invalid_job_name')
    args.output_dir.mkdir(parents=True, exist_ok=True)
    lock = args.output_dir/'controller.lock'
    with lock.open('x', encoding='utf-8') as stream:
        stream.write(str(os.getpid()))
    began = time.monotonic()
    states = {name: dict(status='queued') for name in jobs}
    try:
        from trading_workspace_v2.forex_study_registration import runtime_binding
        manifest = dict(config_sha256=digest(args.config), source_revision=subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=V2, text=True).strip(),
            supervisor_sha256=digest(__file__), config=config, max_workers=args.max_workers,
            runtime=runtime_binding(),
            worker_seconds=args.worker_seconds, deadline_seconds=args.deadline_seconds,
            reuse_from=[str(path.resolve()) for path in args.reuse_from])
        if args.source_root:
            manifest['source_root'] = str(V2)
        if args.parallel_start:
            manifest['parallel_start'] = True
        if args.prepare_inputs:
            manifest['prepare_inputs'] = True
        stored = args.output_dir/'batch-manifest.json'
        if stored.exists():
            if read(stored) != manifest:
                raise ValueError('batch_binding_changed_use_new_directory')
        else:
            save(stored, manifest)
        pending = []
        for name, expected in jobs.items():
            input_cache_dirs(expected)
            if read(expected['input_manifest']) != dict(schema='forex-h4-inputs-v1', **expected['inputs']):
                raise ValueError('input_manifest_binding_mismatch')
            if digest(expected['protocol']) != expected['protocol_sha256']:
                raise ValueError('protocol_binding_mismatch')
            if bool(expected.get('study_registration')) != bool(expected.get('study_registration_sha256')):
                raise ValueError('study_registration_requires_path_and_hash')
            if expected.get('study_registration'):
                from trading_workspace_v2.forex_study_registration import load_registration, validate_registration
                registration = load_registration(Path(expected['study_registration']), expected['study_registration_sha256'])
                validate_registration(registration, expected['inputs'], expected['candidate'],
                    protocol_sha256=expected['protocol_sha256'], account_spec_sha256=expected['account_spec_sha256'],
                    allow_source_drift=expected.get('benchmark_only') is True)
                limits = registration.get('execution', {})
                if not isinstance(limits, dict):
                    raise ValueError('invalid_registered_execution_limits')
                for key, requested in (('max_numeric_workers', args.max_workers),
                        ('worker_timeout_seconds', args.worker_seconds),
                        ('batch_deadline_seconds', args.deadline_seconds)):
                    if key in limits and (type(limits[key]) is not int or limits[key] <= 0
                                          or requested > limits[key]):
                        raise ValueError('registered_execution_limit_exceeded:'+key)
                if args.parallel_start and limits.get('parallel_start') is False:
                    raise ValueError('registered_parallel_start_not_allowed')
            directory = args.output_dir/name
            reused = False
            if directory.exists():
                if read(directory/'terminal.json')['status'] != 'completed_verified':
                    raise ValueError('incomplete_job_requires_new_attempt_directory')
                verified_result(directory/'replay', expected)
                states[name] = dict(status='reused_verified', result_dir=str(directory/'replay'))
                reused = True
            if not reused:
                for previous in args.reuse_from:
                    old = previous/name
                    if not (old/'terminal.json').exists() or read(old/'terminal.json')['status'] != 'completed_verified':
                        continue
                    dossier = verified_result(old/'replay', expected)
                    states[name] = dict(status='reused_verified', result_dir=str((old/'replay').resolve()),
                                        artifact_sha256=dossier['artifact_sha256'])
                    reused = True
                    break
            if not reused:
                pending.append(name)
        if args.prepare_inputs and pending:
            for name in pending:
                states[name]['stage'] = 'preparing_shared_inputs'
            progress(args.output_dir, states, began, config['development_ticks'], args.deadline_seconds)
            def observe_preparation(event):
                for name in pending:
                    states[name]['stage'] = 'prepare_'+event['kind']+'_'+event['role']
                progress(args.output_dir, states, began, config['development_ticks'], args.deadline_seconds)
            try:
                preparation = prepare_pending_inputs(jobs, pending, args.output_dir, began=began,
                    deadline=args.deadline_seconds, on_observe=observe_preparation)
                if preparation['projection_errors']:
                    for name in pending:
                        states[name]['input_preparation_projection_errors'] = preparation['projection_errors']
            except PreparationStopped as error:
                reason = 'deadline' if str(error) == 'deadline' else 'cancelled'
                for name in pending:
                    states[name] = dict(status='not_started_deadline' if reason=='deadline' else 'not_started_cancelled')
                pending.clear()
                save(args.output_dir/'input-preparation.json', dict(status=reason))
            for name in pending:
                states[name].pop('stage', None)
        futures = {}
        # Keep the original full-candidate probe unless the new study opts into
        # parallel startup. Every worker still performs its full validation.
        probe_done = args.parallel_start or not pending or states[next(iter(jobs))]['status'] == 'reused_verified'
        pool = ThreadPoolExecutor(max_workers=args.max_workers)
        try:
            while pending or futures:
                cancelled = (args.output_dir/'CANCEL').exists()
                timed_out = time.monotonic()-began > args.deadline_seconds
                if timed_out and not cancelled:
                    (args.output_dir/'CANCEL').write_text('batch_deadline_exceeded\n', encoding='utf-8')
                if cancelled or timed_out:
                    for name in pending:
                        states[name] = dict(status='not_started_deadline' if timed_out else 'not_started_cancelled')
                    pending.clear()
                limit = args.max_workers if probe_done else 1
                while pending and len(futures) < limit:
                    name = pending.pop(0)
                    states[name] = dict(status='running')
                    futures[pool.submit(run_job, name, jobs[name], args.output_dir/name,
                                        seconds=args.worker_seconds)] = name
                progress(args.output_dir, states, began, config['development_ticks'], args.deadline_seconds)
                done, _ = wait(futures, timeout=5, return_when=FIRST_COMPLETED) if futures else (set(), set())
                for future in done:
                    name = futures.pop(future)
                    states[name] = future.result()
                    if not probe_done:
                        probe_done = True
                        if states[name]['status'] != 'completed_verified':
                            (args.output_dir/'CANCEL').write_text('probe_failed\n', encoding='utf-8')
        finally:
            if sys.exc_info()[0] is not None:
                (args.output_dir/'CANCEL').write_text('supervisor_interrupted\n', encoding='utf-8')
            pool.shutdown(wait=True)
        final = progress(args.output_dir, states, began, config['development_ticks'], args.deadline_seconds)
        save(args.output_dir/'batch-terminal.json', final)
        return 0 if final['status'] == 'completed_verified' else 1
    except BaseException as error:
        save(args.output_dir/'batch-failure.json', dict(status='supervisor_failed',
            error_type=type(error).__name__, error_code='study_batch_failed',
            frames=[dict(file=Path(frame.filename).name, line=frame.lineno, function=frame.name)
                    for frame in traceback.extract_tb(error.__traceback__)],
            updated_at_utc=datetime.now(timezone.utc).isoformat()))
        for name, state in states.items():
            terminal = args.output_dir/name/'terminal.json'
            if terminal.exists():
                states[name] = read(terminal)
            elif state['status'] == 'queued':
                states[name] = dict(status='not_started_supervisor_failed')
            elif state['status'] == 'running':
                states[name] = dict(status='interrupted_unknown')
        try:
            final = progress(args.output_dir, states, began, config['development_ticks'], args.deadline_seconds)
            final['status'] = 'supervisor_failed'
            save(args.output_dir/'batch-terminal.json', final)
        except Exception:
            save(args.output_dir/'batch-terminal.json', dict(status='supervisor_failed', workers=states))
        raise
    finally:
        lock.unlink()


if __name__ == '__main__':
    if sys.argv[1:] == ['--_worker']:
        payload = json.loads(sys.stdin.readline())
        sys.path[:] = payload['paths']
        sys.argv[:] = payload['argv']
        runpy.run_path(sys.argv[0], run_name='__main__')
    else:
        try:
            raise SystemExit(main())
        except Exception as error:
            print(json.dumps(dict(error_code='study_batch_failed', error_type=type(error).__name__)), file=sys.stderr)
            raise SystemExit(1)

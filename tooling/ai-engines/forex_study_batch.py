"""Finite offline study supervisor; retains completed jobs and owns Windows children."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from datetime import datetime, timezone
import hashlib
import json
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


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


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


def verified_result(directory, expected, *, source_root=V2):
    from strategy_evidence import inspect
    dossier = inspect(directory, source_root=source_root)
    manifest = read(directory/'manifest.json')
    if (dossier['candidate'] != expected['candidate']
            or manifest['inputs'] != expected['inputs']
            or manifest['observed_account_spec']['sha256'] != expected['account_spec_sha256']
            or dossier['protocol_sha256'] != expected['protocol_sha256']
            or not dossier['protocol_content_verified']
            or dossier['source_drift'] or dossier['unavailable_sources']):
        raise ValueError('completed_result_binding_mismatch')
    return dossier


def run_job(name, expected, directory, *, seconds, clock=time.monotonic):
    directory.mkdir(parents=True, exist_ok=False)
    replay = directory/'replay'
    argv = [str(V2/'scripts/forex_h4_pilot.py'), '--input-dir', str(Path(expected['input_manifest']).parent),
        '--input-manifest', expected['input_manifest'], '--output-dir', str(replay),
        '--candidate', expected['candidate'], '--research-protocol', expected['protocol'],
        '--account-spec', expected['account_spec'], '--account-spec-sha256', expected['account_spec_sha256']]
    if expected.get('reuse_scenarios_from'):
        argv.extend(['--reuse-scenarios-from', expected['reuse_scenarios_from']])
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
        if receipt_path.exists():
            receipt = read(receipt_path)
            row.update({k: receipt.get(k) for k in ('stage', 'observed_ticks', 'elapsed_seconds', 'pid', 'updated_at_utc')})
            row['scenario_fraction'] = (receipt.get('observed_ticks', 0)/total_ticks
                                        if receipt['stage'] in {'reference', 'cost-stress'} else None)
        rows.append(row)
    elapsed = time.monotonic()-began
    status = 'running' if any(s['status'] in {'queued', 'running'} for s in states.values()) else \
        'completed_verified' if all(s['status'] in {'completed_verified', 'reused_verified'} for s in states.values()) else 'incomplete'
    snapshot = dict(schema='forex-study-batch-v1', status=status, updated_at_utc=datetime.now(timezone.utc).isoformat(),
        elapsed_seconds=round(elapsed, 2), deadline_seconds=deadline, workers=rows,
        completed_jobs=sum(s['status'] in {'completed_verified', 'reused_verified'} for s in states.values()),
        total_jobs=len(states), model_calls=0, broker_calls=0, holdout_read=False)
    save(output/'progress.json', snapshot)
    lines = ['# Nghiên cứu Q1/2022', '', f'Cập nhật UTC: {snapshot["updated_at_utc"]}',
        f'\nTrạng thái: **{status}** · Xong {snapshot["completed_jobs"]}/{len(states)} ứng viên · Đã chạy {elapsed/60:.1f} phút', '',
        '| Ứng viên | Trạng thái | Bước | Tick / scenario |', '|---|---|---|---:|']
    for row in rows:
        ticks = row.get('observed_ticks')
        lines.append(f'| {row["worker"]} | {row["status"]} | {row.get("stage") or "—"} | {ticks if ticks is not None else "—"} / {total_ticks} |')
    lines += ['', 'Xác minh dữ liệu chưa có % hoặc ETA đáng tin. Tiến độ tick chỉ áp dụng scenario đang chạy.',
        'Mỗi ứng viên chạy reference và cost-stress. Chỉ completed_verified mới có dossier đã kiểm.',
        'Giữ kết quả đã xong; không tự retry job lỗi. CANCEL cạnh file này sẽ hủy các job chưa xong.',
        'Dữ liệu development đã dùng; chưa OOS/prop qualification. Không model/broker/holdout.',
        'progress.json là projection của terminal.json + receipt.json; không thay ledger/task Paperclip.']
    temporary = output/'PROGRESS.tmp'
    temporary.write_text('\n'.join(lines)+'\n', encoding='utf-8')
    temporary.replace(output/'PROGRESS.md')
    print(json.dumps(dict(status=status, completed=snapshot['completed_jobs'],
        elapsed_seconds=snapshot['elapsed_seconds'], workers=[
            {key: row[key] for key in ('worker', 'status', 'stage', 'observed_ticks') if key in row}
            for row in rows])), flush=True)
    return snapshot


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--max-workers', type=int, choices=(1, 2, 3, 4, 5), default=2)
    parser.add_argument('--worker-seconds', type=int, default=1800)
    parser.add_argument('--deadline-seconds', type=int, default=5400)
    parser.add_argument('--reuse-from', type=Path, action='append', default=[],
                        help='Read and verify completed jobs from earlier batches; partial jobs are never resumed')
    args = parser.parse_args(argv)
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
        manifest = dict(config_sha256=digest(args.config), source_revision=subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=V2, text=True).strip(),
            supervisor_sha256=digest(__file__), config=config, max_workers=args.max_workers,
            worker_seconds=args.worker_seconds, deadline_seconds=args.deadline_seconds,
            reuse_from=[str(path.resolve()) for path in args.reuse_from])
        stored = args.output_dir/'batch-manifest.json'
        if stored.exists():
            if read(stored) != manifest:
                raise ValueError('batch_binding_changed_use_new_directory')
        else:
            save(stored, manifest)
        pending = []
        for name, expected in jobs.items():
            if read(expected['input_manifest']) != dict(schema='forex-h4-inputs-v1', **expected['inputs']):
                raise ValueError('input_manifest_binding_mismatch')
            if digest(expected['protocol']) != expected['protocol_sha256']:
                raise ValueError('protocol_binding_mismatch')
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
        futures = {}
        # First candidate measures the complete real journey alone; later jobs
        # use the explicit bounded concurrency, without changing strategy rules.
        probe_done = not pending or states[next(iter(jobs))]['status'] == 'reused_verified'
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

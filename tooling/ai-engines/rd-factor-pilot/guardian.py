"""WSL job lease: EOF/stale Windows heartbeat stops the group and owned containers.

Runs only in the existing dedicated distro as root. Candidate code runs as the
unprivileged RD controller's Docker child, never inside this guardian process.
"""
import fcntl
import json
import os
from pathlib import Path
import pwd
import re
import select
import signal
import struct
import subprocess
import sys
import time
from uuid import UUID


def main():
    def read_exact(count):
        chunks = bytearray()
        while len(chunks) < count:
            chunk = os.read(sys.stdin.fileno(), count - len(chunks))
            if not chunk:
                raise EOFError('Job payload interrupted')
            chunks.extend(chunk)
        return chunks

    size = struct.unpack('!Q', read_exact(8))[0]
    if size > 4_000_000:
        raise ValueError('Bounded job payload required')
    payload = json.loads(read_exact(size))
    job_id = str(UUID(payload['run_id']))
    image = payload['image']
    if not re.fullmatch(r'sha256:[0-9a-f]{64}', image):
        raise ValueError('Immutable local image ID required')
    files = payload['files']
    if set(files) != {'pilot.py', 'docker-python.sh', 'candidate.py', 'market.csv'}:
        raise ValueError('Unexpected payload files')
    base = Path('/opt/naqex/rd-agent')
    with (base / 'paperclip-runtime.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if subprocess.run(['systemctl', 'is-active', '--quiet', 'docker.service']).returncode == 0:
            raise RuntimeError('Docker already active; inspect its owner before dispatch')
        jobs = base / 'paperclip-jobs'
        jobs.mkdir(exist_ok=True)
        job = jobs / job_id
        job.mkdir()  # Never reuse an interrupted or completed job directory.
        user = pwd.getpwnam('naqex')
        os.chown(job, user.pw_uid, user.pw_gid)
        for name, content in files.items():
            (job / name).write_text(content, encoding='utf-8')
            os.chown(job / name, user.pw_uid, user.pw_gid)
        child = None
        started = False
        reason = 'failed'
        try:
            started = True
            subprocess.run(['systemctl', 'start', 'docker.service'], check=True, timeout=30)
            subprocess.run(['docker', 'image', 'inspect', image], check=True,
                           stdout=subprocess.DEVNULL, timeout=10)
            command = ['runuser', '-u', 'naqex', '--', 'env', '-i',
                       'HOME=/home/naqex', 'USER=naqex', 'PATH=/usr/bin:/bin',
                       'LANG=C.UTF-8', 'DO_NOT_TRACK=1', 'LITELLM_LOCAL_MODEL_COST_MAP=True',
                       'NAQEX_RD_JOB=' + job_id,
                       str(base / 'venv/bin/python'), str(job / 'pilot.py'), str(job),
                       '--candidate', str(job / 'candidate.py'), '--image', image,
                       '--input-csv', str(job / 'market.csv')]
            child = subprocess.Popen(command, cwd=job, stdin=subprocess.DEVNULL,
                                     stdout=sys.stderr, stderr=sys.stderr, start_new_session=True)
            last_ping = time.monotonic()
            # Read the raw fd: buffered readline could retain a ping invisibly to select.
            while child.poll() is None:
                ready, _, _ = select.select([sys.stdin.fileno()], [], [], 0.2)
                if ready:
                    if not os.read(sys.stdin.fileno(), 4096):
                        reason = 'cancelled_eof'
                        break
                    last_ping = time.monotonic()
                if time.monotonic() - last_ping > 6:
                    reason = 'cancelled_lease'
                    break
            else:
                reason = 'completed' if child.returncode == 0 else 'failed'
            if reason == 'completed':
                result = json.loads((job / 'result.json').read_text())
                factor = (job / 'validated-factor.csv').read_text()
                executions = json.loads((job / 'executions.json').read_text())
                print(json.dumps({'result': result, 'factor_csv': factor, 'executions': executions}))
            return 0 if reason == 'completed' else 2
        finally:
            if child is not None and child.poll() is None:
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                child.wait(timeout=5)
            if started:
                try:
                    owned = subprocess.check_output(
                        ['docker', 'ps', '-aq', '--filter', 'label=naqex.rd.job=' + job_id],
                        text=True, timeout=10).split()
                    if owned:
                        subprocess.run(['docker', 'rm', '-f', *owned], check=True,
                                       stdout=subprocess.DEVNULL, timeout=10)
                finally:
                    subprocess.run(['systemctl', 'stop', 'docker.socket', 'docker.service',
                                    'containerd.service'], check=True, timeout=20)
            (job / 'guardian.json').write_text(json.dumps({'status': reason, 'run_id': job_id}))


if __name__ == '__main__':
    raise SystemExit(main())

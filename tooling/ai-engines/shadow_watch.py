"""Read-only finite shadow observer; native Paperclip documents are projections.

No model calls, broker credentials, session starts/resumes or execution controls.
"""
import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys
import time
from urllib.error import HTTPError

from paperclip_setup import api

VN = timezone(timedelta(hours=7))
TERMINAL = {'complete', 'failed', 'stopped', 'expired', 'interrupted', 'monitor_error'}


def stamp(value):
    return datetime.fromtimestamp(value / 1000, VN).strftime('%d/%m %H:%M:%S VN') if value else 'Chưa có'


def render(state, observed):
    status, health = state.get('status'), state.get('health')
    label = {'complete': 'Đã kết thúc lượt quan sát', 'failed': 'Đã dừng vì lỗi',
             'stopped': 'Đã dừng theo yêu cầu', 'expired': 'Đã hết thời hạn',
             'interrupted': 'Tiến trình đã ngắt',
             'monitor_error': 'Không đọc được trạng thái; chưa rõ tiến trình còn chạy hay không'}.get(status)
    if label is None:
        label = {'heartbeat_stale': 'Cảnh báo: tiến trình chưa cập nhật nhịp sống',
                 'overdue': 'Cảnh báo: tiến trình còn giữ khóa sau deadline',
                 'heartbeat_unavailable': 'Bản cũ chưa hỗ trợ nhịp sống'}.get(health)
    if label is None:
        label = {'retry_wait': 'Đang chờ MT5 phục hồi', 'settling': 'Đang chờ chốt dữ liệu',
                 'poll_wait': 'Đang chờ trang dữ liệu kế tiếp', 'worker': 'Đang đọc/kiểm dữ liệu'}.get(
                     state.get('phase'), 'Đang quan sát')
    obs = state.get('observation') or {}
    held = obs.get('projection_status') == 'held'
    if held and status in ('running', 'complete'):
        label = 'Đã thu xong; dữ liệu cần kiểm tra' if status == 'complete' else 'Đang thu tick; tạm giữ tính nến/tín hiệu'
    reason = state.get('reason') or obs.get('quality_reason') or (state.get('transport_retry') or {}).get('reason') or 'Không'
    begin, end, through = (state.get('capture_from_msc'), state.get('capture_to_msc'),
                           obs.get('requested_through_msc'))
    covered = 'Chưa có mốc thời gian từ bản supervisor này'
    if all(isinstance(v, int) for v in (begin, end, through)) and end > begin:
        covered = f'{max(0, min(through, end)-begin)/1000:.0f} / {(end-begin)/1000:.0f} giây dữ liệu đã đọc'
    expected = end + state.get('settle_seconds', 0)*1000 if end else None
    return '\n'.join([
        f'<!-- naqex-shadow-progress:{state["manifest_sha256"]} -->',
        f'## {label}', '', 'Chỉ đọc dữ liệu. Đây là trạng thái quan sát, chưa phải acceptance của task.', '',
        '| Nội dung | Trạng thái |', '|---|---|',
        f'| Bản tin lấy lúc | {stamp(observed)} |',
        f'| Nhịp sống supervisor | {stamp(state.get("heartbeat_at_msc"))} |',
        f'| Tiến độ dữ liệu cập nhật lúc | {stamp(state.get("updated_at_msc"))} |',
        f'| Kết thúc thực tế | {stamp(state.get("ended_at_msc"))} |',
        f'| Phạm vi đã đọc | {covered} |',
        f'| Dữ liệu | {obs.get("ticks", 0)} tick · {obs.get("pages", 0)} trang · {obs.get("closed_hours", 0)} H1 đã chốt |',
        f'| Tính nến / tín hiệu | {"Tạm giữ; chưa đủ chất lượng dữ liệu" if held else "Không có quality hold"} |',
        f'| Dự kiến chốt / deadline | {stamp(expected)} / {stamp(state.get("deadline_msc"))} |',
        f'| Retry đọc / lần tiếp tục | {state.get("transport_retries_total", 0)} / {max(0, state.get("incarnation", 1)-1)} |',
        f'| Mã lỗi hiện tại | `{reason}` |', '',
        'Bản tin thường cập nhật mỗi 60 giây; thay đổi trạng thái được gửi ở lần kiểm kế tiếp (~5 giây, cộng thời gian API).',
        'Nếu bản tin quá 90 giây không đổi khi đang chạy, chưa thể coi hệ thống còn hoạt động bình thường. '
        'Báo tên task, mốc cập nhật và mã lỗi; không tự khởi động một lượt mới.',
    ])


def status(binary, directory):
    result = subprocess.run([str(binary), 'status', '--state-dir', str(directory)],
        capture_output=True, timeout=5,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
    if result.returncode not in (0, 2) or not result.stdout:
        raise ValueError('shadow_monitor_status_unavailable')
    state = json.loads(result.stdout)
    if state.get('schema_version') != 'mt5-shadow-lifecycle-v1' or state.get('execution_capability') is not False:
        raise ValueError('shadow_monitor_status_invalid')
    return state


class Publisher:
    """Read before PUT, reconcile uncertain commits, fence competing writers."""
    def __init__(self, task, manifest, request=api):
        self.path = f'/issues/{task}/documents/shadow-{manifest[:16]}'
        self.marker = f'<!-- naqex-shadow-progress:{manifest} -->'
        self.request = request
        self.revision = None
        self.seen = False
        self.pending = None

    def send(self, body):
        try:
            doc = self.request(self.path)
        except HTTPError as exc:
            if exc.code != 404:
                raise
            doc = None
        revision = doc.get('latestRevisionId') if doc else None
        if doc and (not doc['body'].startswith(self.marker) or
                    (self.seen and revision != self.revision and doc['body'] != self.pending)):
            raise ValueError('shadow_monitor_document_changed_by_other_writer')
        self.seen, self.revision = True, revision
        if doc and doc['body'] == body:
            self.pending = None
            return
        self.pending = body
        saved = self.request(self.path, dict(format='markdown', title='Tiến độ quan sát dữ liệu',
            body=body, baseRevisionId=revision, changeSummary='Cập nhật trạng thái từ lifecycle'), 'PUT')
        self.revision, self.pending = saved['latestRevisionId'], None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path, required=True)
    parser.add_argument('--state-dir', type=Path, required=True)
    parser.add_argument('--task', help='Existing native task UUID; omit for terminal-only observation')
    parser.add_argument('--company', help='Explicit authorized company UUID; required with --task')
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    if bool(args.task) != bool(args.company):
        parser.error('--task and --company must be supplied together')
    state = status(args.binary.resolve(strict=True), args.state_dir.resolve(strict=True))
    publisher = None
    if args.task:
        from uuid import UUID
        UUID(args.task)
        UUID(args.company)
        task = api('/issues/' + args.task)
        if task['companyId'] != args.company:
            raise ValueError('shadow_monitor_company_mismatch')
        publisher = Publisher(args.task, state['manifest_sha256'])
    last_publish, last_transition, failures = 0, None, 0
    # Finite observer; it cannot extend or revive the computation's deadline.
    end = time.monotonic() + min(86400 + 300, max(120, (state['deadline_msc']/1000-time.time())+120))
    pending_body = None
    while True:
        try:
            state = status(args.binary.resolve(), args.state_dir.resolve())
        except (OSError, ValueError, subprocess.TimeoutExpired):
            state = dict(state, status='monitor_error', health='unavailable',
                         reason='shadow_monitor_status_unavailable')
        observed = int(time.time()*1000)
        transition = (state['status'], state.get('health'), state.get('phase'),
                      state.get('reason'), (state.get('transport_retry') or {}).get('reason'))
        final = state['status'] in TERMINAL
        if transition != last_transition or time.monotonic()-last_publish >= 60 or pending_body:
            body = pending_body or render(state, observed)
            print(body, flush=True)
            try:
                if publisher:
                    publisher.send(body)
            except (OSError, ValueError, KeyError) as exc:
                failures += 1
                pending_body = body
                # No raw response/credentials. Keep computation and publication independent.
                print(f'Paperclip chưa nhận bản tin (lần {failures}, {type(exc).__name__}); '
                      'lượt quan sát không bị khởi động lại.', file=sys.stderr, flush=True)
                if args.once or (final and failures >= 3):
                    return 2
            else:
                reconciled_pending = pending_body is not None
                pending_body, failures = None, 0
                if reconciled_pending:
                    # An old in-flight message is not the newest outcome. Publish
                    # the current lifecycle before acknowledging final delivery.
                    last_publish, last_transition = 0, None
                    continue
                last_publish, last_transition = time.monotonic(), transition
                if final or args.once:
                    return 0 if state['status'] == 'complete' else 2 if final else 0
        if time.monotonic() >= end:
            print('Observer đã hết thời hạn; kiểm tra lifecycle trước khi tiếp tục.', file=sys.stderr)
            return 2
        time.sleep(5 if not pending_body else 10)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, subprocess.TimeoutExpired) as error:
        print(f'Không đọc/đăng được trạng thái: {type(error).__name__}; '
              'không suy ra lượt quan sát thành công. Kiểm tra lifecycle/log.', file=sys.stderr)
        sys.exit(2)

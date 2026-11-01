"""Bounded engine jobs launched by Paperclip's native process adapter."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import UUID

ROOT = Path(__file__).resolve().parents[2]
SERVICES = json.loads((ROOT / 'projects/trader/foundation_v2/local-services.json').read_text())
CATALOG = json.loads((ROOT / 'tooling/integrations/catalog.json').read_text())
SOURCES = {row['id']: ROOT / row['path'] for row in CATALOG['sources']}
EXPIRED_MODEL = re.compile(r'opus[-_. ]?5[-_. ]?5', re.I)


class JobError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(code)
        self.code, self.message = code, message


def write_json(path: Path, value: dict):
    temporary = path.with_suffix('.next')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


def uuid(value: str) -> str:
    return str(UUID(value))


def parse_request(description: str) -> dict:
    blocks = re.findall(r'^```naqex-engine\s*\n(.*?)^```\s*$', description, re.M | re.S)
    if len(blocks) != 1 or len(blocks[0]) > 8192:
        raise JobError('invalid_request', 'Cần đúng một khối naqex-engine theo mẫu của công việc.')
    try:
        value = json.loads(blocks[0])
    except ValueError:
        raise JobError('invalid_request', 'Thông tin engine chưa đúng định dạng JSON.') from None
    if not isinstance(value, dict) or type(value.get('version')) is not int or value['version'] != 1:
        raise JobError('invalid_request', 'Phiên bản yêu cầu chưa được hỗ trợ.')
    engine = value.get('engine')
    if engine == 'rd-agent':
        if set(value) != {'version', 'engine'}:
            raise JobError('invalid_request', 'RD-Agent chưa nhận đề tài trước khi môi trường Linux được cấu hình.')
        return value
    if engine != 'tradingagents' or set(value) != {'version', 'engine', 'symbol', 'as_of', 'asset_type', 'analysts'}:
        raise JobError('invalid_request', 'Yêu cầu TradingAgents phải dùng các trường trong mẫu.')
    symbol = value['symbol']
    if not isinstance(symbol, str) or not re.fullmatch(r'[A-Z0-9^][A-Z0-9.^=\-]{0,24}', symbol):
        raise JobError('invalid_symbol', 'Mã tài sản không hợp lệ; ví dụ BTC-USD hoặc AAPL.')
    try:
        as_of = date.fromisoformat(value['as_of'])
        valid_date = as_of.isoformat() == value['as_of']
    except (TypeError, ValueError):
        valid_date = False
    today = datetime.now(timezone(timedelta(hours=7))).date()
    if not valid_date or as_of > today:
        raise JobError('invalid_date', 'Ngày phân tích phải theo YYYY-MM-DD và không nằm trong tương lai.')
    analysts = value['analysts']
    if value['asset_type'] not in ('stock', 'crypto'):
        raise JobError('unsupported_asset', 'Lát đầu hỗ trợ cổ phiếu và crypto; chưa nối dữ liệu Forex/MT5.')
    allowed = {'market', 'news', 'social'} | ({'fundamentals'} if value['asset_type'] == 'stock' else set())
    if (not isinstance(analysts, list) or not analysts or len(analysts) > 4
            or any(not isinstance(a, str) or a not in allowed for a in analysts)
            or len(set(analysts)) != len(analysts)):
        raise JobError('invalid_analysts', 'Nhóm phân tích không hợp lệ cho loại tài sản đã chọn.')
    return value


def load_settings(path: Path) -> dict:
    value = json.loads(path.read_text(encoding='utf-8-sig'))
    if set(value) != {'version', 'artifact_root', 'gateway_config', 'quick_model', 'deep_model'} or value['version'] != 1:
        raise JobError('settings_invalid', 'Cấu hình worker chưa đúng phiên bản.')
    for key in ('artifact_root', 'gateway_config'):
        if not isinstance(value[key], str) or not Path(value[key]).is_absolute():
            raise JobError('settings_invalid', 'Đường dẫn runtime phải là đường dẫn tuyệt đối của project.')
    for key in ('quick_model', 'deep_model'):
        model = value[key]
        if not isinstance(model, str) or not model.strip() or len(model) > 200:
            raise JobError('model_required', 'Chọn model Gemini còn hoạt động cho worker trước khi chạy.')
        if EXPIRED_MODEL.search(model):
            raise JobError('model_expired', 'Model Opus 5.5 đã hết hạn theo owner; chọn model khác.')
    return value


def gateway(settings: dict, *, check_catalog=True) -> tuple[str, str]:
    import yaml

    document = yaml.safe_load(Path(settings['gateway_config']).read_text(encoding='utf-8'))
    server = document.get('server', {})
    if server.get('host') != SERVICES['host'] or server.get('port') != SERVICES['cliProxyApiPort']:
        raise JobError('gateway_scope', 'Gateway phải dùng đúng cổng riêng của project.')
    keys = document.get('access', {}).get('api-keys', [])
    if not keys or not isinstance(keys[0], str) or not keys[0].strip():
        raise JobError('gateway_key_missing', 'Gateway chưa có khóa truy cập nội bộ.')
    base = f"http://{SERVICES['host']}:{SERVICES['cliProxyApiPort']}/v1"
    if check_catalog:
        req = Request(base + '/models', headers={'Authorization': 'Bearer ' + keys[0]})
        try:
            with urlopen(req, timeout=10) as response:
                wire = response.read(2_000_001)
            if len(wire) > 2_000_000:
                raise ValueError('catalog_limit')
            ids = {v['id'] for v in json.loads(wire)['data']}
        except (OSError, ValueError, KeyError, TypeError):
            raise JobError('gateway_unavailable', 'Chưa đọc được model. Mở gateway project và kiểm tra kết nối.') from None
        if any(settings[key] not in ids for key in ('quick_model', 'deep_model')):
            raise JobError('model_unavailable', 'Model đã chọn không còn trong danh sách của gateway.')
    return base, keys[0]


def clean_environment():
    # Provider SDKs must not inherit unrelated host credentials or tracing sinks.
    prefixes = ('PAPERCLIP_', 'NAQEX_')
    keep = {'SYSTEMROOT', 'WINDIR', 'COMSPEC', 'PATH', 'PATHEXT', 'TEMP', 'TMP',
            'USERPROFILE', 'APPDATA', 'LOCALAPPDATA', 'PROGRAMFILES', 'PROGRAMFILES(X86)',
            'NUMBER_OF_PROCESSORS', 'SYSTEMDRIVE', 'HOMEDRIVE', 'HOMEPATH'}
    for key in list(os.environ):
        if key.upper() not in keep and not key.startswith(prefixes):
            del os.environ[key]
    os.environ.update(LANGSMITH_TRACING='false', LANGCHAIN_TRACING_V2='false', PYTHONUTF8='1')


def source_pin(engine: str) -> str:
    options = dict(text=True, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    dirty = subprocess.check_output(['git', '-C', str(SOURCES[engine]), 'status', '--porcelain',
                                     '--untracked-files=no'], **options)
    if dirty.strip():
        raise JobError('engine_source_changed', 'Source engine đang có thay đổi chưa lưu; chốt phiên bản trước khi chạy.')
    return subprocess.check_output(['git', '-C', str(SOURCES[engine]), 'rev-parse', 'HEAD'], **options).strip()


def run_tradingagents(request: dict, settings: dict, directory: Path, connection: tuple[str, str]) -> dict:
    base, key = connection
    os.environ['OPENAI_COMPATIBLE_API_KEY'] = key
    # Import only after removing inherited provider configuration.
    from tradingagents.default_config import build_default_config
    from tradingagents.graph.trading_graph import TradingAgentsGraph
    import tradingagents

    if Path(tradingagents.__file__).resolve().parent != (SOURCES['tradingagents'] / 'tradingagents').resolve():
        raise JobError('engine_import_mismatch', 'Môi trường Python đang trỏ tới source engine khác.')

    config = build_default_config()
    config.update(llm_provider='openai_compatible', backend_url=base,
                  quick_think_llm=settings['quick_model'], deep_think_llm=settings['deep_model'],
                  output_language='Vietnamese', llm_max_retries=0, max_tokens=2048,
                  max_tool_rounds=3, max_debate_rounds=1, max_risk_discuss_rounds=1,
                  max_recur_limit=80, checkpoint_enabled=False,
                  results_dir=str(directory / 'results'), data_cache_dir=str(directory / 'cache'),
                  memory_log_path=str(directory / 'memory.md'))
    graph = TradingAgentsGraph(selected_analysts=request['analysts'], config=config)
    final, rating = graph.propagate(request['symbol'], request['as_of'], asset_type=request['asset_type'])
    # This is the engine's own report exporter, not a replacement analysis pipeline.
    graph.save_reports(final, request['symbol'], save_path=directory / 'report', html=False)
    text = (directory / 'report/complete_report.md').read_text(encoding='utf-8')
    if len(text) > 400_000:
        raise JobError('report_too_large', 'Báo cáo vượt giới hạn hiển thị; bản đầy đủ đã được giữ trong artifacts.')
    return {'report': text, 'rating': str(rating), 'settings': graph.run_settings(),
            'provenance': final.get('run_provenance')}


class Paperclip:
    def __init__(self):
        self.agent = uuid(os.environ['PAPERCLIP_AGENT_ID'])
        self.company = uuid(os.environ['PAPERCLIP_COMPANY_ID'])
        self.run = uuid(os.environ['PAPERCLIP_RUN_ID'])
        self.token = os.environ['PAPERCLIP_API_KEY']
        self.base = os.environ['PAPERCLIP_API_URL'].rstrip('/')
        expected = f"http://{SERVICES['host']}:{SERVICES['paperclipPort']}"
        if self.base != expected:
            raise JobError('paperclip_scope', 'Worker chỉ kết nối instance Paperclip riêng của project.')

    def call(self, path: str, body=None, method='GET'):
        req = Request(self.base + '/api' + path, method=method,
                      data=None if body is None else json.dumps(body, ensure_ascii=False).encode(),
                      headers={'Authorization': 'Bearer ' + self.token,
                               'X-Paperclip-Run-Id': self.run, 'Content-Type': 'application/json'})
        try:
            with urlopen(req, timeout=20) as response:
                wire = response.read(2_000_001)
                if len(wire) > 2_000_000:
                    raise JobError('paperclip_response_limit', 'Phản hồi Paperclip vượt giới hạn worker.')
                return json.loads(wire) if wire else None
        except HTTPError as error:
            # Never put tokens, request bodies or response diagnostics in process logs.
            raise JobError('paperclip_http_' + str(error.code), 'Paperclip chưa chấp nhận thao tác; xem quyền và trạng thái công việc.') from None
        except (URLError, TimeoutError):
            raise JobError('paperclip_unavailable', 'Mất kết nối Paperclip; kết quả local vẫn được giữ.') from None

    def assigned_issue(self) -> dict:
        run = self.call('/heartbeat-runs/' + self.run)
        if run['agentId'] != self.agent or run['companyId'] != self.company:
            raise JobError('run_scope', 'Lượt chạy không thuộc worker này.')
        issue_id = uuid((run.get('contextSnapshot') or {}).get('issueId', ''))
        issue = self.call('/issues/' + issue_id)
        if issue['companyId'] != self.company or issue.get('assigneeAgentId') != self.agent:
            raise JobError('issue_scope', 'Công việc chưa được giao cho worker này.')
        if issue.get('status') in ('done', 'cancelled'):
            raise JobError('issue_terminal', 'Công việc đã kết thúc; tạo công việc mới nếu muốn phân tích lại.')
        if issue.get('checkoutRunId') != self.run:
            self.call('/issues/' + issue_id + '/checkout',
                      {'agentId': self.agent, 'expectedStatuses': ['todo', 'in_progress', 'blocked']}, 'POST')
        return issue

    def report(self, issue_id: str, text: str, *, completed: bool):
        # A unique key preserves every attempt instead of replacing earlier evidence.
        self.call('/issues/' + issue_id + '/documents/engine-' + self.run,
                  {'title': 'Kết quả phân tích' if completed else 'Điều kiện cần để chạy',
                   'format': 'markdown', 'body': text}, 'PUT')
        self.call('/issues/' + issue_id,
                  {'status': 'done' if completed else 'blocked',
                   'comment': 'Đã lưu báo cáo phân tích. Đây chưa phải kết quả kiểm chứng chiến lược.'
                   if completed else 'Chưa chạy xong engine. Xem tài liệu điều kiện cần để chạy trong công việc này.'}, 'PATCH')


def execute_paperclip(engine: str, settings_path: Path) -> int:
    paperclip = Paperclip()
    issue = paperclip.assigned_issue()
    directory = None
    receipt = {'version': 1, 'engine': engine, 'run_id': paperclip.run,
               'issue_id': issue['id'], 'company_id': paperclip.company, 'status': 'preflight',
               'provider_work_started': False, 'execution_capability': False,
               'wrapper_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               'started_at': datetime.now(timezone.utc).isoformat()}
    try:
        request = parse_request(issue.get('description') or '')
        if request['engine'] != engine:
            raise JobError('engine_mismatch', 'Công việc đang được giao nhầm engine.')
        if engine == 'rd-agent':
            raise JobError('rd_agent_runtime_required', 'RD-Agent cần môi trường Linux và Docker cô lập. Máy hiện chưa có runtime đã được kiểm chứng; chưa chạy thí nghiệm.')
        settings = load_settings(settings_path)
        directory = Path(settings['artifact_root']) / paperclip.company / paperclip.run
        directory.parent.mkdir(parents=True, exist_ok=True)
        # A repeated dispatch must not replay uncertain provider work.
        directory.mkdir(exist_ok=False)
        receipt.update(source_commit=source_pin(engine), request=request,
                       request_sha256=hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest(),
                       models={key: settings[key] for key in ('quick_model', 'deep_model')})
        write_json(directory / 'receipt.json', receipt)
        connection = gateway(settings)
        receipt.update(status='running', provider_work_started=True)
        write_json(directory / 'receipt.json', receipt)
        result = run_tradingagents(request, settings, directory, connection)
        receipt.update(status='publishing', engine_status='completed',
                       rating=result['rating'], settings=result['settings'],
                       provenance=result['provenance'], engine_finished_at=datetime.now(timezone.utc).isoformat())
        report = ('# Phân tích ' + request['symbol'] + '\n\n'
                  + 'Ngày dữ liệu yêu cầu: ' + request['as_of'] + '. Engine: TradingAgents.\n\n'
                  + 'Đây là phân tích thị trường, chưa phải backtest hoặc bằng chứng chiến lược có lợi nhuận.\n\n'
                  + result['report'] + '\n\n<details><summary>Nguồn và cấu hình lượt chạy</summary>\n\n```json\n'
                  + json.dumps({key: receipt[key] for key in ('run_id', 'source_commit', 'wrapper_sha256', 'request_sha256', 'models', 'provenance')},
                               ensure_ascii=False, indent=2) + '\n```\n\n</details>\n')
        (directory / 'report.md').write_text(report, encoding='utf-8')
        receipt['report_sha256'] = hashlib.sha256(report.encode()).hexdigest()
        write_json(directory / 'receipt.json', receipt)
        paperclip.report(issue['id'], report, completed=True)
        receipt.update(status='completed', delivery_status='published',
                       finished_at=datetime.now(timezone.utc).isoformat())
        write_json(directory / 'receipt.json', receipt)
        print(json.dumps({'status': 'completed', 'engine': engine, 'run_id': paperclip.run}))
        return 0
    except Exception as error:
        if isinstance(error, FileExistsError):
            # Another invocation may still own this run; do not alter its task or evidence.
            print(json.dumps({'status': 'blocked', 'engine': engine, 'error': 'run_already_exists'}))
            return 2
        known = error if isinstance(error, JobError) else JobError(
            'engine_failed' if receipt['provider_work_started'] else 'engine_preflight_failed',
            'Engine chưa hoàn tất. Kết quả đã có được giữ lại; không tự chạy lại yêu cầu chưa rõ kết quả.')
        receipt.update(status='failed' if receipt['provider_work_started'] else 'blocked',
                       error=known.code, error_type=type(error).__name__,
                       finished_at=datetime.now(timezone.utc).isoformat())
        if receipt.get('engine_status') == 'completed':
            receipt['delivery_status'] = 'failed'
        if directory is not None and directory.is_dir():
            write_json(directory / 'receipt.json', receipt)
        try:
            paperclip.report(issue['id'], '# Chưa hoàn tất\n\n' + known.message + '\n\nMã chẩn đoán: `' + known.code + '`.', completed=False)
        except JobError:
            pass
        print(json.dumps({'status': receipt['status'], 'engine': engine, 'error': known.code}))
        return 2


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--engine', required=True, choices=['tradingagents', 'rd-agent'])
    parser.add_argument('--settings', required=True, type=Path)
    args = parser.parse_args()
    clean_environment()
    return execute_paperclip(args.engine, args.settings)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    try:
        raise SystemExit(main())
    except Exception as error:
        print(json.dumps({'status': 'blocked', 'error': error.code if isinstance(error, JobError) else 'paperclip_context_missing'}))
        raise SystemExit(2)

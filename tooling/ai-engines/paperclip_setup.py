"""Provision engine workers through the native Paperclip API; no source patch."""
import argparse
import json
from pathlib import Path
import sys
from urllib.request import Request, urlopen

from engine_worker import ROOT, SERVICES, uuid


def operator_headers(origin):
    """Use the project-isolated credential approved through Paperclip's CLI login."""
    headers = {'Content-Type': 'application/json', 'Origin': origin}
    store = ROOT / '.runtime/paperclip/auth.json'
    if store.is_file():
        credential = json.loads(store.read_text(encoding='utf-8'))['credentials'].get(origin)
        if credential is not None:
            token = credential.get('token')
            if credential.get('apiBase') != origin or not isinstance(token, str) or not token.strip():
                raise ValueError('Invalid project Paperclip CLI credential; sign in again')
            headers['Authorization'] = 'Bearer ' + token.strip()
    return headers


def api(path, body=None, method='GET'):
    origin = f"http://{SERVICES['host']}:{SERVICES['paperclipPort']}"
    request = Request(origin + '/api' + path, method=method,
                      data=None if body is None else json.dumps(body, ensure_ascii=False).encode(),
                      headers=operator_headers(origin))
    with urlopen(request, timeout=20) as response:
        return json.load(response)


def worker_config(engine: str, settings: Path) -> dict:
    python = ROOT / ('projects/trader/foundation_v2/.venv/Scripts/python.exe' if engine == 'forex-pilot'
                     else 'projects/integrations/TradingAgents/.venv/Scripts/python.exe')
    if not python.is_file() or not settings.is_file():
        raise ValueError('Existing engine Python and private settings are required')
    name = {'tradingagents': 'Chuyên viên phân tích', 'rd-agent': 'Chuyên viên nghiên cứu',
            'forex-pilot': 'Chuyên viên kiểm định'}[engine]
    return {
        'name': name, 'title': name, 'role': 'researcher', 'adapterType': 'process',
        'adapterConfig': {'command': str(python),
                          'args': ['-u', str(ROOT / 'tooling/ai-engines/engine_worker.py'),
                                   '--engine', engine, '--settings', str(settings.resolve())],
                          'cwd': str(ROOT), 'timeoutSec': 900, 'graceSec': 5},
        'capabilities': ('Phân tích cổ phiếu/crypto bằng TradingAgents; báo cáo tiếng Việt; không đặt lệnh.'
                         if engine == 'tradingagents' else
                         'Kiểm dữ liệu và mô phỏng Forex bằng runner Trader trên bài mẫu cố định; không đặt lệnh.'
                         if engine == 'forex-pilot' else
                         'RD-Agent: thí nghiệm factor được đăng ký trên snapshot lịch sử; Quant Lab kiểm chứng; không đặt lệnh.'),
        'runtimeConfig': {'heartbeat': {'enabled': False, 'wakeOnDemand': True,
                                       'maxConcurrentRuns': 1}},
        'permissions': {'canCreateAgents': False, 'canCreateSkills': False},
        'metadata': {'naqexEngine': engine, 'contractVersion': 1},
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--company', required=True, type=uuid)
    parser.add_argument('--settings', required=True, type=Path)
    parser.add_argument('--reports-to', type=uuid)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--engine', choices=['tradingagents', 'rd-agent', 'forex-pilot'], action='append')
    args = parser.parse_args()
    existing = api('/companies/' + args.company + '/agents')
    rows = []
    for engine in args.engine or ('tradingagents', 'rd-agent'):
        matches = [a for a in existing if (a.get('metadata') or {}).get('naqexEngine') == engine]
        if len(matches) > 1:
            raise ValueError('Duplicate engine workers; inspect instead of replacing them')
        if matches:
            rows.append({'engine': engine, 'id': matches[0]['id'], 'action': 'kept_existing'})
            continue
        payload = worker_config(engine, args.settings)
        if args.reports_to:
            payload['reportsTo'] = args.reports_to
        if not args.apply:
            rows.append({'engine': engine, 'action': 'would_create', 'payload': payload})
            continue
        agent = api('/companies/' + args.company + '/agents', payload, 'POST')
        if engine == 'rd-agent':
            api('/agents/' + agent['id'] + '/pause', {}, 'POST')
        rows.append({'engine': engine, 'id': agent['id'], 'action': 'created',
                     'status': 'paused' if engine == 'rd-agent' else agent['status']})
    print(json.dumps(rows, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()

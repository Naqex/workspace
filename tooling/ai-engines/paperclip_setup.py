"""Provision engine workers through the native Paperclip API; no source patch."""
import argparse
import json
from pathlib import Path
import sys
from urllib.request import Request, urlopen

from engine_worker import ROOT, SERVICES, uuid


def api(path, body=None, method='GET'):
    origin = f"http://{SERVICES['host']}:{SERVICES['paperclipPort']}"
    request = Request(origin + '/api' + path, method=method,
                      data=None if body is None else json.dumps(body, ensure_ascii=False).encode(),
                      headers={'Content-Type': 'application/json', 'Origin': origin})
    with urlopen(request, timeout=20) as response:
        return json.load(response)


def worker_config(engine: str, settings: Path) -> dict:
    python = ROOT / 'projects/integrations/TradingAgents/.venv/Scripts/python.exe'
    if not python.is_file() or not settings.is_file():
        raise ValueError('Existing engine Python and private settings are required')
    name = 'Chuyên viên phân tích' if engine == 'tradingagents' else 'Chuyên viên nghiên cứu'
    return {
        'name': name, 'title': name, 'role': 'researcher', 'adapterType': 'process',
        'adapterConfig': {'command': str(python),
                          'args': ['-u', str(ROOT / 'tooling/ai-engines/engine_worker.py'),
                                   '--engine', engine, '--settings', str(settings.resolve())],
                          'cwd': str(ROOT), 'timeoutSec': 900, 'graceSec': 5},
        'capabilities': ('Phân tích cổ phiếu/crypto bằng TradingAgents; báo cáo tiếng Việt; không đặt lệnh.'
                         if engine == 'tradingagents' else
                         'RD-Agent: chuẩn bị nghiên cứu thí nghiệm; đang chờ môi trường Linux/Docker.'),
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
    args = parser.parse_args()
    existing = api('/companies/' + args.company + '/agents')
    rows = []
    for engine in ('tradingagents', 'rd-agent'):
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

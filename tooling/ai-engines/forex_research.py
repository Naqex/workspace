"""Registered Forex system fixture; reuse Trader replay without a provider or broker."""
from __future__ import annotations

import hashlib
import importlib
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re
import sys

from engine_worker import JobError, ROOT, write_json

EXPERIMENT = 'forex-h4-system-v1'
CANDIDATE = 'eurusd-h4-donchian20-10-atr14-r025-v1'
ACCOUNT_SPEC_SHA256 = '930e5670b21b09963d21741258706adeff6b10c454dd9fafa0df7346a0a74756'
INPUTS = {
    'warmup': ('807a05c1e777350f1151674a4c9a1a2288fd11d3f0b1f9fb939509b49d2d83e8', '20211220', '20211231'),
    'development': ('ce49cd3af5f41396b3b831c8e0ea83e2dd9c8e4f5790962052a5b1f4d4fbaf66', '20220103', '20220114'),
}
ORACLE = {
    'reference': {'realized_trade_net_usd': '-17.72', 'financing_debit_usd': '2.22',
                  'balance_delta_usd': '-19.94', 'balance_usd': '9980.06',
                  'equity_usd': '9980.06', 'minimum_observed_equity_usd': '9950.23'},
    'cost-stress': {'realized_trade_net_usd': '-18.20', 'financing_debit_usd': '5.60',
                    'balance_delta_usd': '-23.80', 'balance_usd': '9976.20',
                    'equity_usd': '9976.20', 'minimum_observed_equity_usd': '9948.08'},
}


def _sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def _pilot():
    scripts = ROOT / 'projects/trader/foundation_v2/scripts'
    sys.path.insert(0, str(scripts))
    pilot = importlib.import_module('forex_h4_pilot')
    if Path(pilot.__file__).resolve() != (scripts / 'forex_h4_pilot.py').resolve():
        raise JobError('forex_runner_scope', 'Python đang trỏ tới Forex runner khác của project.')
    if pilot.EXPECTED != INPUTS:
        raise JobError('forex_fixture_contract', 'Runner đã đổi fixture; cần review contract hệ thống trước khi chạy.')
    return pilot


def preflight(settings: dict, directory: Path) -> dict:
    config = settings.get('forex_pilot')
    if not isinstance(config, dict) or set(config) != {'input_dir', 'account_spec', 'account_spec_sha256'}:
        raise JobError('forex_settings_required', 'Chọn fixture QDM và thông số FTMO đã pin trước khi mở worker kiểm định.')
    if (any(not isinstance(config[k], str) or not Path(config[k]).is_absolute()
            for k in ('input_dir', 'account_spec'))
            or not isinstance(config['account_spec_sha256'], str)
            or not re.fullmatch('[0-9a-f]{64}', config['account_spec_sha256'])
            or config['account_spec_sha256'] != ACCOUNT_SPEC_SHA256):
        raise JobError('forex_settings_invalid', 'Fixture hệ thống chỉ nhận đường dẫn tuyệt đối và đúng snapshot FTMO đã đăng ký.')
    pilot = _pilot()
    try:
        account = pilot.observed_account_spec(Path(config['account_spec']), ACCOUNT_SPEC_SHA256)
        for name, (digest, _, _) in INPUTS.items():
            path = Path(config['input_dir']) / name / 'EURUSD_TICK_TW-TICK-No Session.csv'
            if _sha(path) != digest:
                raise ValueError('fixture hash differs')
            with path.open(encoding='utf-8-sig') as stream:
                if stream.readline().rstrip('\r\n') != 'DateTime,Bid,Ask,Volume':
                    raise ValueError('fixture header differs')
    except (OSError, ValueError, KeyError, TypeError, InvalidOperation):
        raise JobError('forex_fixture_changed', 'Dữ liệu hoặc thông số không khớp fixture đã chốt; chưa chạy mô phỏng.') from None
    provenance = {
        'experiment': EXPERIMENT, 'purpose': 'system_fixture', 'candidate': CANDIDATE,
        'inputs': {name: dict(sha256=digest, first_day=first, last_day=last)
                   for name, (digest, first, last) in INPUTS.items()},
        'account_spec': {key: value for key, value in account.items() if key != 'path'},
        'validation_holdout_read': False, 'strategy_qualified': False,
        'execution_capability': False,
    }
    write_json(directory / 'data-preflight.json', provenance)
    return {'config': dict(config), 'provenance': provenance}


def _validate_results(results):
    if (not isinstance(results, list) or len(results) != 2
            or any(not isinstance(row, dict) for row in results)
            or {row.get('scenario') for row in results} != set(ORACLE)):
        raise JobError('forex_fixture_result', 'Mô phỏng thiếu hoặc trùng scenario; không bàn giao sang phản biện.')
    for row in results:
        expected = ORACLE[row['scenario']]
        try:
            for key, value in expected.items():
                actual = Decimal(row[key])
                if not actual.is_finite() or actual != Decimal(value):
                    raise ValueError('changed outcome')
            for key, value in {
                'entry_fills': 3, 'closed_trades': 3, 'signals': 4, 'observed_ticks': 643775,
                'independent_accounting': 'passed', 'snapshot_restart': 'passed',
                'open_position': None, 'pending_entry': False, 'risk_stops': [], 'risk_rejections': [],
                'broker_spec_verified': False, 'strategy_pass': False, 'prop_pass': False,
                'terminal_close_forced': False, 'intrabar_equity_coverage': 'insufficient',
            }.items():
                if key not in row or (row[key] is not value if isinstance(value, bool) else row[key] != value):
                    raise ValueError('changed accounting or qualification')
        except (KeyError, TypeError, ValueError, InvalidOperation):
            raise JobError('forex_fixture_result', 'Kết quả khác fixture đã chốt; giữ artifacts để kiểm tra, không tune hoặc tự chạy lại.') from None


def build_report(validation: dict) -> str:
    if (validation.get('experiment') != EXPERIMENT or validation.get('purpose') != 'system_fixture'
            or validation.get('system_fixture_pass') is not True
            or validation.get('strategy_qualified') is not False
            or validation.get('execution_capability') is not False):
        raise JobError('forex_fixture_contract', 'Hồ sơ không thuộc kiểm tra hệ thống đã đăng ký.')
    _validate_results(validation['scenarios'])
    rows = {row['scenario']: row for row in validation['scenarios']}
    text = ('# Kiểm tra luồng Forex\n\n'
            '**Mô phỏng fixture: hoàn tất.** Lượt này kiểm hệ thống trên dữ liệu đã dùng, '
            'giữ nguyên chiến lược EURUSD/H4 và mức rủi ro. Chưa tối ưu hoặc đánh giá ngoài mẫu.\n\n'
            'Dữ liệu QDM CLI: warmup 20–31/12/2021, mô phỏng 03–14/01/2022; '
            '643.775 tick, vốn mô phỏng 10.000 USD.\n\n'
            '| Kết quả USD | Tham chiếu | Chi phí cao |\n'
            '|---|---:|---:|\n')
    for label, key in [('Lệnh đã đóng', 'closed_trades'),
                       ('Lãi/lỗ giao dịch trước financing', 'realized_trade_net_usd'),
                       ('Financing debit ròng', 'financing_debit_usd'),
                       ('Thay đổi số dư sau mọi phí', 'balance_delta_usd'),
                       ('Số dư cuối', 'balance_usd')]:
        text += f"| {label} | {Decimal(str(rows['reference'][key]))} | {Decimal(str(rows['cost-stress'][key]))} |\n"
    text += ('\n## Kết quả kiểm hệ thống\n\n'
             '- Hash dữ liệu/thông số và hai kết quả khớp fixture đã đăng ký.\n'
             '- Đối soát từng lệnh, financing, số dư và khôi phục snapshot JSON đạt.\n'
             '- Không tìm tham số mới, mở validation/holdout hoặc gửi lệnh broker.\n\n'
             '## Giới hạn cần giữ\n\n'
             '- Swap từ snapshot FTMO hiện tại được áp như một scenario lên giá năm 2022; '
             'commission chưa xác minh trên tài khoản, lịch/rounding chưa tái dựng lịch sử.\n'
             '- Dữ liệu chỉ gồm quotes được cung cấp; coverage và server stop-out chưa được chứng nhận.\n'
             '- Fixture có lãi hay không không quyết định workflow hoàn thiện. '
             'Chiến lược và Prop **chưa được qualification**; paper **NOT_RUN**.\n\n'
             'Bước tiếp theo của workflow là phản biện việc bàn giao, số liệu và các giới hạn hệ thống; '
             'không đề xuất tuning chiến lược trong lượt này.\n')
    return text


def run(settings, directory, connection, prepared, run_id, on_progress=None):
    # No connection/provider is used: Paperclip owns the process and its cancellation.
    pilot = _pilot()
    config = prepared['config']
    replay = directory / 'replay'
    pilot.main(argv=['--input-dir', config['input_dir'], '--output-dir', str(replay),
                     '--account-spec', config['account_spec'],
                     '--account-spec-sha256', config['account_spec_sha256']],
               on_progress=on_progress)
    receipt = json.loads((replay / 'receipt.json').read_text(encoding='utf-8'))
    manifest = json.loads((replay / 'manifest.json').read_text(encoding='utf-8'))
    results = json.loads((replay / 'results.json').read_text(encoding='utf-8'))
    quality = json.loads((replay / 'quality.json').read_text(encoding='utf-8'))
    observed_account = {key: value for key, value in manifest.get('observed_account_spec', {}).items()
                        if key != 'path'}
    if (receipt.get('stage') != 'completed_declared_scenarios'
            or manifest.get('candidate') != CANDIDATE
            or manifest.get('validation_holdout_read') is not False
            or manifest.get('broker_connected') is not False
            or manifest.get('broker_spec_verified') is not False
            or {name: {k: item[k] for k in ('sha256', 'first_day', 'last_day')}
                for name, item in manifest.get('inputs', {}).items()} != prepared['provenance']['inputs']
            or observed_account != prepared['provenance']['account_spec']
            or any(quality.get(name, {}).get('ticks') != count
                   for name, count in [('warmup', 546210), ('development', 643775)])):
        raise JobError('forex_fixture_incomplete', 'Mô phỏng chưa hoàn tất đúng contract; không dùng kết quả một phần.')
    _validate_results(results)
    provenance = dict(prepared['provenance'], trader_source_commit=manifest['source_revision'],
                      source_files=manifest['source_files'], system_fixture_pass=True,
                      replay_manifest_sha256=_sha(replay / 'manifest.json'))
    validation = dict(experiment=EXPERIMENT, purpose='system_fixture', candidate=CANDIDATE,
                      run_id=run_id, inputs=provenance['inputs'], account_spec=provenance['account_spec'],
                      source_files=provenance['source_files'], scenarios=results, quality=quality,
                      system_fixture_pass=True, strategy_qualified=False, execution_capability=False)
    return dict(report=build_report(validation), rating='SYSTEM_FIXTURE_PASSED',
                settings={'experiment': EXPERIMENT, 'provider_used': False},
                provenance=provenance, validation=validation)

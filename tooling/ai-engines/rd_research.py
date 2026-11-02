"""One registered offline research contract, using RD-Agent and Quant Lab.

Only prepare calls a public data endpoint. A dispatched job consumes a pinned
snapshot, makes one model request, executes in WSL/Docker and evaluates locally.
"""
from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import sys
import time
from urllib.request import Request, urlopen

from engine_worker import JobError, ROOT, write_json

TOOLING = Path(__file__).with_name('rd-factor-pilot')
CONTRACT_PATH = TOOLING / 'market-contract.json'
CONTRACT = json.loads(CONTRACT_PATH.read_text())
EXPERIMENT = CONTRACT['experiment']
QUANT = ROOT / 'projects/quant-trading'


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def quant_imports():
    sys.path.insert(0, str(QUANT / 'src'))
    from quant_lab import data
    from quant_trading.data_quality import OHLCVQualityPolicy, audit_ohlcv
    return data, OHLCVQualityPolicy, audit_ohlcv


def checked_frame(path):
    import pandas as pd
    data, Policy, audit = quant_imports()
    frame = data.load_candles(path)
    frame = frame.loc[(frame.open_time >= pd.Timestamp(CONTRACT['start'], tz='UTC'))
                      & (frame.open_time < pd.Timestamp(CONTRACT['end_exclusive'], tz='UTC'))].copy()
    quality = audit(frame, policy=Policy(expected_interval_seconds=86400, max_gap_count=0))
    expected = pd.date_range(CONTRACT['start'], CONTRACT['end_exclusive'],
                             inclusive='left', freq='D', tz='UTC')
    close_time = pd.to_datetime(frame.close_time, utc=True, errors='coerce')
    if (quality.quality_status != 'accepted' or not pd.DatetimeIndex(frame.open_time).equals(expected)
            or close_time.isna().any()
            or not ((close_time >= frame.open_time)
                    & (close_time < frame.open_time + pd.Timedelta(days=1))).all()):
        raise JobError('dataset_quality', 'Dữ liệu thiếu/sai nến hoặc thời điểm đóng nến chưa hợp lệ.')
    return frame, quality.as_dict()


def prepare(directory: Path):
    directory.mkdir(parents=True, exist_ok=False)
    data, _, _ = quant_imports()
    manifest = {'version': 1, 'experiment': EXPERIMENT, 'contract_sha256': sha(CONTRACT_PATH.read_bytes()),
                'source': data.BINANCE_KLINES_URL, 'captured_at': datetime.now(timezone.utc).isoformat(),
                'vintage': 'historical snapshot retrieved now; no revision-vintage guarantee', 'assets': {}}
    for symbol in CONTRACT['symbols']:
        frame = data.download_binance_klines(symbol, CONTRACT['start'], CONTRACT['end_exclusive'])
        path = directory / (symbol + '.csv')
        data.save_candles(frame, path)
        selected, quality = checked_frame(path)
        manifest['assets'][symbol] = {'file': path.name, 'raw_sha256': sha(path.read_bytes()),
                                     'quality': quality, 'rows': len(selected)}
    path = directory / 'manifest.json'
    write_json(path, manifest)
    print(json.dumps({'manifest': str(path.resolve()), 'sha256': sha(path.read_bytes()),
                      'rows_per_asset': {k: v['rows'] for k, v in manifest['assets'].items()}}))


def preflight(settings: dict, directory: Path) -> dict:
    config = settings.get('rd_agent', {})
    if set(config) != {'dataset_manifest', 'manifest_sha256', 'image_id'}:
        raise JobError('rd_settings_required', 'Chọn snapshot đã kiểm chứng và image Linux trước khi mở worker nghiên cứu.')
    path = Path(config['dataset_manifest'])
    if not path.is_absolute() or not re.fullmatch(r'sha256:[0-9a-f]{64}', config['image_id']):
        raise JobError('rd_settings_invalid', 'Snapshot/image nghiên cứu chưa đúng định dạng.')
    wire = path.read_bytes()
    if len(wire) > 100_000 or sha(wire) != config['manifest_sha256']:
        raise JobError('dataset_changed', 'Snapshot đã thay đổi; kiểm tra và chốt lại dữ liệu trước khi chạy.')
    manifest = json.loads(wire)
    if (manifest.get('version') != 1 or manifest.get('experiment') != EXPERIMENT
            or manifest.get('contract_sha256') != sha(CONTRACT_PATH.read_bytes())
            or set(manifest.get('assets', {})) != set(CONTRACT['symbols'])):
        raise JobError('dataset_contract', 'Snapshot không thuộc thí nghiệm đã đăng ký.')
    frames = {}
    for symbol, asset in manifest['assets'].items():
        if asset['file'] != symbol + '.csv':
            raise JobError('dataset_scope', 'Đường dẫn dữ liệu không thuộc snapshot được phép.')
        file = path.parent / asset['file']
        if sha(file.read_bytes()) != asset['raw_sha256']:
            raise JobError('dataset_changed', 'File dữ liệu không còn khớp snapshot đã chốt.')
        frame, quality = checked_frame(file)
        if quality != asset['quality']:
            raise JobError('dataset_changed', 'Kết quả kiểm tra dữ liệu không khớp snapshot.')
        frames[symbol] = frame
    options = dict(text=True, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if subprocess.check_output(['git', '-C', str(QUANT), 'status', '--porcelain'], **options).strip():
        raise JobError('quant_source_changed', 'Quant Lab có thay đổi chưa lưu; chốt phiên bản trước khi nghiên cứu.')
    quant_pin = subprocess.check_output(['git', '-C', str(QUANT), 'rev-parse', 'HEAD'], **options).strip()
    receipt = {'contract': CONTRACT, 'contract_sha256': manifest['contract_sha256'],
               'dataset_manifest_sha256': sha(wire), 'dataset': manifest, 'quant_source_commit': quant_pin}
    write_json(directory / 'data-preflight.json', receipt)
    write_json(directory / 'contract.json', CONTRACT)
    return {'frames': frames, 'provenance': receipt, 'image': config['image_id']}


def review_candidate(code: str):
    """Narrow transform-only surface; independent oracle still checks semantics."""
    if not 0 < len(code.encode()) <= 16000:
        raise JobError('candidate_rejected', 'Code factor vượt giới hạn cho phép.')
    try:
        tree = ast.parse(code)
    except SyntaxError:
        raise JobError('candidate_rejected', 'Code factor chưa đúng cú pháp.') from None
    allowed = {'read_hdf', 'DataFrame', 'groupby', 'shift', 'to_hdf', 'reindex', 'index',
               'rename', 'copy', 'astype', 'columns'}
    forbidden = (ast.ImportFrom, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda,
                 ast.For, ast.AsyncFor, ast.While, ast.With, ast.AsyncWith, ast.Try,
                 ast.ListComp, ast.DictComp, ast.SetComp, ast.GeneratorExp)
    for node in ast.walk(tree):
        bad = isinstance(node, forbidden)
        if isinstance(node, ast.Import):
            bad |= any((a.name, a.asname) not in {('pandas', 'pd'), ('numpy', 'np')} for a in node.names)
        if isinstance(node, ast.Attribute):
            bad |= node.attr not in allowed
        if isinstance(node, ast.Name):
            bad |= node.id.startswith('_')
        if isinstance(node, ast.Call):
            bad |= not isinstance(node.func, ast.Attribute)
            if isinstance(node.func, ast.Attribute):
                method = node.func.attr
                if method in {'read_hdf', 'to_hdf', 'shift'}:
                    expected = {'read_hdf': 'daily_pv.h5', 'to_hdf': 'result.h5', 'shift': 3}[method]
                    bad |= not node.args or not isinstance(node.args[0], ast.Constant) or node.args[0].value != expected
        if bad:
            raise JobError('candidate_rejected', 'Code factor dùng thao tác ngoài phạm vi; đã giữ để review, không tự sửa/chạy lại.')


def generate(settings, directory, connection):
    prompt = ('Return only a short Python script. Use import pandas as pd. Read daily_pv.h5 key data. '
              'DataFrame MultiIndex [datetime, instrument], float column $close, sorted daily UTC bars. '
              'Compute momentum_3d = close[t]/close[t-3]-1 separately per instrument using groupby(level="instrument") '
              'and shift(3). Keep first 3 rows per instrument as NaN. Use pd.DataFrame with one momentum_3d '
              'column, exact input index/order. Write result.h5 key data mode w. '
              'Only straight-line assignments and pandas calls read_hdf, groupby, shift, DataFrame, reindex, '
              'to_hdf are permitted. No functions, loops, built-in calls, other files, network or subprocess. '
              'No data or performance feedback is supplied; implement this fixed formula, do not select a strategy.')
    (directory / 'prompt.txt').write_text(prompt, encoding='utf-8')
    attempt = {'status': 'started', 'requested_model': settings['quick_model'],
               'prompt_sha256': sha(prompt.encode()), 'calls': 1, 'retries': 0}
    write_json(directory / 'model-attempt.json', attempt)
    base, key = connection
    payload = {'model': settings['quick_model'], 'max_tokens': 4096, 'stream': False,
               'messages': [{'role': 'user', 'content': prompt}]}
    request = Request(base + '/chat/completions', data=json.dumps(payload).encode(),
                      headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key})
    with urlopen(request, timeout=150) as response:
        wire = response.read(200_001)
    if len(wire) > 200_000:
        raise JobError('model_response_limit', 'Phản hồi model vượt giới hạn pilot.')
    value = json.loads(wire)
    choice = value['choices'][0]
    code = choice['message']['content'].strip()
    if code.startswith('```') and code.endswith('```'):
        code = '\n'.join(code.splitlines()[1:-1])
    code += '\n'
    (directory / 'candidate.py').write_text(code, encoding='utf-8')
    attempt.update(status='received', reported_model=value.get('model'), usage=value.get('usage'),
                   finish_reason=choice.get('finish_reason'), candidate_sha256=sha(code.encode()))
    write_json(directory / 'model-attempt.json', attempt)
    if choice.get('finish_reason') != 'stop':
        raise JobError('candidate_incomplete', 'Model chưa trả code hoàn chỉnh; không tự retry.')
    review_candidate(code)
    return code, attempt


def execute_linux(directory: Path, run_id: str, image: str, code: str, market_csv: str):
    payload = json.dumps({'run_id': run_id, 'image': image, 'files': {
        'pilot.py': (TOOLING / 'pilot.py').read_text(),
        'docker-python.sh': (TOOLING / 'docker-python.sh').read_text(),
        'candidate.py': code, 'market.csv': market_csv}}).encode()
    if len(payload) > 4_000_000:
        raise JobError('rd_payload_limit', 'Dữ liệu vượt giới hạn pilot.')
    command = ['wsl.exe', '-d', 'NaqexResearch', '-u', 'root', '--cd', '/opt/naqex/rd-agent',
               '--exec', '/usr/bin/python3', '-c', (TOOLING / 'guardian.py').read_text()]
    options = {'creationflags': getattr(subprocess, 'CREATE_NO_WINDOW', 0)}
    with (directory / 'linux-output.json').open('wb') as output, (directory / 'linux.log').open('wb') as log:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=output, stderr=log, **options)
        try:
            process.stdin.write(struct.pack('!Q', len(payload)) + payload)
            process.stdin.flush()
            deadline = time.monotonic() + 240
            while process.poll() is None:
                if time.monotonic() > deadline:
                    raise JobError('rd_timeout', 'Thí nghiệm vượt thời gian cho phép; đang dừng Linux job.')
                try:
                    process.stdin.write(b'ping\n')
                    process.stdin.flush()
                except BrokenPipeError:
                    break
                time.sleep(1)
            process.wait(timeout=35)
        finally:
            process.stdin.close()  # EOF revokes the Linux lease, also on timeout/error.
            if process.poll() is None:
                try:
                    process.wait(timeout=35)
                except subprocess.TimeoutExpired:
                    process.kill()
        if process.returncode != 0:
            raise JobError('rd_execution_failed', 'RD-Agent chưa đạt kiểm chứng; xem artifacts của lượt chạy, không tự retry.')
    if (directory / 'linux-output.json').stat().st_size > 2_000_000:
        raise JobError('rd_output_limit', 'Kết quả Linux vượt giới hạn pilot.')
    return json.loads((directory / 'linux-output.json').read_text(encoding='utf-8'))


def evaluate(frames, factor_csv: str, directory: Path):
    from io import StringIO
    import numpy as np
    import pandas as pd
    quant_imports()
    from quant_lab.strategies import time_series_momentum_signal
    from quant_trading.walk_forward import WalkForwardConfig, run_walk_forward_stress
    from quant_trading.null_baseline import run_null_baselines
    factor = pd.read_csv(StringIO(factor_csv))
    factor['datetime'] = pd.to_datetime(factor['datetime'], utc=True)
    factor = factor.set_index(['datetime', 'instrument'])
    if list(factor.columns) != ['momentum_3d'] or not factor.index.is_unique:
        raise JobError('rd_output_invalid', 'Factor không đúng schema hoặc bị trùng index.')
    config = WalkForwardConfig(train_bars=CONTRACT['train_bars'], test_bars=CONTRACT['test_bars'],
                               minimum_folds=CONTRACT['minimum_folds'],
                               stress_multipliers=tuple(CONTRACT['stress_multipliers']))
    results = {}
    for symbol, frame in frames.items():
        close = pd.Series(frame.close.to_numpy(), index=pd.DatetimeIndex(frame.open_time), name='close')
        generated = factor.xs(symbol, level='instrument').momentum_3d
        expected = close / close.shift(CONTRACT['lookback']) - 1
        pd.testing.assert_index_equal(generated.index, close.index, check_names=False)
        np.testing.assert_allclose(generated.to_numpy(), expected.to_numpy(), rtol=1e-10, atol=1e-12, equal_nan=True)
        # Only the oracle-equivalent verified rule is replayed on each prefix.
        candidate = run_walk_forward_stress(close,
            lambda history: time_series_momentum_signal(history, CONTRACT['lookback']),
            strategy_id=EXPERIMENT, fee_bps=CONTRACT['fee_bps'],
            slippage_bps=CONTRACT['slippage_bps'], config=config)
        baselines = run_null_baselines(close, fee_bps=CONTRACT['fee_bps'],
                                       slippage_bps=CONTRACT['slippage_bps'], config=config)
        if candidate.input_sha256 != baselines.input_sha256:
            raise JobError('baseline_input_mismatch', 'Baseline không cùng dữ liệu với ứng viên.')
        results[symbol] = {'candidate': candidate.as_dict(), 'baselines': baselines.as_dict(),
                           'unused_tail_bars': len(close) - config.train_bars - len(candidate.folds) * config.test_bars}
    if len(factor) != sum(len(frame) for frame in frames.values()):
        raise JobError('rd_output_invalid', 'Factor có thêm hoặc thiếu rows.')
    write_json(directory / 'quant-validation.json', results)
    return results


def build_report(validation):
    lines = ['# Thử nghiệm momentum 3 ngày — BTC và ETH', '',
             'Đã chạy xong workflow nghiên cứu trên dữ liệu lịch sử. Chưa đủ bằng chứng để chạy demo/tiền thật.', '',
             'Một candidate, không tối ưu tham số. Factor > 0 thì long, ngược lại giữ tiền; vị thế từ nến sau.', '',
             '## Kết quả ngoài mẫu theo thời gian', '',
             'Mỗi dòng là median của 4 cửa sổ OOS 180 ngày; drawdown là mức xấu nhất trong các cửa sổ. '
             'Đây không phải lợi nhuận gộp toàn kỳ.', '']
    for symbol, values in validation.items():
        passive = next(v['receipt'] for v in values['baselines']['evaluations'] if v['baseline_id'] == 'buy_hold')
        lines += ['### ' + symbol, '', '| Chi phí | Ứng viên | Mua và giữ |', '|---|---:|---:|']
        for candidate, baseline in zip(values['candidate']['cases'], passive['cases'], strict=True):
            cost = candidate['fee_bps'] + candidate['slippage_bps']
            m, b = candidate['aggregate_metrics'], baseline['aggregate_metrics']
            lines.append(f"| {cost:g} bps | {m['total_return']:.2%} | {b['total_return']:.2%} |")
        m = values['candidate']['cases'][0]['aggregate_metrics']
        lines += ['', f"Sụt giảm lớn nhất của ứng viên ở chi phí cơ sở: **{m['max_drawdown']:.2%}**. "
                  'Giữ tiền có lợi nhuận 0% trong cả hai kịch bản.', '']
    lines += ['', '## Kiểm chứng và giới hạn', '',
              '- Dữ liệu BTC/ETH 2021–2024, UTC; snapshot có nguồn, hash và quality preflight, không lấp nến thiếu.',
              '- Factor khớp oracle độc lập; kiểm tra prefix và thay đổi tương lai đạt; lỗi thực thi được phát hiện.',
              '- Quant Lab replay quy tắc tương đương đã xác minh trên từng prefix, cùng baseline/timing/chi phí. '
              'Metrics đầy đủ gồm CAGR, volatility, turnover, entries và time in market trong tài liệu Dữ liệu và kiểm chứng.',
              '- Chi phí cơ sở 10 bps phí + 5 bps trượt giá, stress gấp đôi; không mô phỏng order book/partial fills.',
              '- OOS hồi cứu, không là final holdout kín. Chưa có kiểm định ý nghĩa thống kê, parameter stability hoặc forward demo.',
              '- Hai tài sản lớn được chọn trước cho pilot; không suy rộng toàn thị trường. Snapshot không bảo đảm vintage của dữ liệu sửa lại.',
              '- Phần cuối chưa đủ một cửa sổ được loại tường minh trong unused_tail_bars; không dùng để tune.',
              '- Kết luận: workflow đã kiểm chứng; chiến lược giữ ở trạng thái nghiên cứu, không tự promote.', '']
    return '\n'.join(lines)


def run(settings: dict, directory: Path, connection, prepared: dict, run_id: str):
    import pandas as pd
    code, attempt = generate(settings, directory, connection)
    rows = [pd.DataFrame({'datetime': frame.open_time, 'instrument': symbol, '$close': frame.close})
            for symbol, frame in prepared['frames'].items()]
    market = pd.concat(rows).sort_values(['datetime', 'instrument']).to_csv(index=False)
    (directory / 'market.csv').write_text(market, encoding='utf-8')
    result = execute_linux(directory, run_id, prepared['image'], code, market)
    checks = result['result']
    if (checks.get('status') != 'passed' or checks.get('synthetic') is not False
            or checks.get('candidate_sha256') != attempt['candidate_sha256']
            or not all(checks.get(key) is True for key in ('prefix_invariance',
                'future_perturbation_invariance', 'leaky_negative_control_rejected', 'execution_failure_detected'))):
        raise JobError('rd_validation_failed', 'Kết quả RD-Agent không khớp candidate hoặc chưa đạt kiểm chứng.')
    validation = evaluate(prepared['frames'], result['factor_csv'], directory)
    provenance = dict(prepared['provenance'], model=attempt, rd_checks=checks,
                      dispatch={'kind': 'paperclip-native-process', 'run_id': run_id},
                      implementation_hashes={name: sha((TOOLING / name).read_bytes())
                        for name in ('pilot.py', 'docker-python.sh', 'guardian.py')},
                      execution_capability=False, strategy_qualified=False)
    return {'report': build_report(validation), 'rating': 'research_only',
            'settings': CONTRACT, 'provenance': provenance, 'validation': validation}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['prepare'])
    parser.add_argument('--directory', type=Path, required=True)
    args = parser.parse_args()
    prepare(args.directory.resolve())

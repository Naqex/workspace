"""Bounded RD-Agent factor execution; synthetic data, no strategy promotion.

Run only inside the dedicated Linux controller venv. Candidate generation is a
separate operator step; this script has no credentials, provider or scheduler.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace

import numpy as np
import pandas as pd


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def fixture():
    rng = np.random.default_rng(20261102)
    dates = pd.date_range('2024-01-01', periods=160, freq='D')
    symbols = [f'SIM{i:02}' for i in range(8)]
    close = 100 * np.exp(np.cumsum(rng.normal(0, .012, (160, 8)), axis=0))
    index = pd.MultiIndex.from_product([dates, symbols], names=['datetime', 'instrument'])
    return pd.DataFrame({'$close': close.ravel()}, index=index)


def oracle(data):
    # Independent loop rather than the candidate's expected groupby/shift path.
    values = dict(data['$close'].items())
    result = []
    for stamp, symbol in data.index:
        previous = values.get((stamp - pd.Timedelta(days=3), symbol))
        result.append(np.nan if previous is None else values[stamp, symbol] / previous - 1)
    return pd.DataFrame({'momentum_3d': result}, index=data.index)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', type=Path)
    parser.add_argument('--candidate', type=Path)
    parser.add_argument('--image')
    args = parser.parse_args()
    root = args.directory.resolve()
    root.mkdir(parents=True, exist_ok=True)
    if not args.candidate:
        prompt = ('Implement one Python factor script, not a trading strategy. '
                  'Input daily_pv.h5 (key data), pandas DataFrame with MultiIndex '
                  '[datetime, instrument], one float column $close, sorted by date then symbol. '
                  'Output result.h5, key data, same complete index and order, one float '
                  'column momentum_3d = close[t]/close[t-3]-1 separately per instrument. '
                  'First three observations per instrument must be NaN. Use only pandas '
                  'and numpy, no future observations, network, subprocess, shell or other files. '
                  'Return only Python source; no Markdown. This is synthetic verification, '
                  'not a profitability test. Preserve all rows including warmup.')
        (root / 'prompt.txt').write_text(prompt)
        dump(root / 'contract.json', dict(seed=20261102, days=160, instruments=8,
             train_days=90, validation_days=30, test_days=40, lookback=3,
             synthetic=True, candidate_attempts=1, execution_seconds=50,
             memory_mb=512, cpus=1, network=False, broker=False))
        print(json.dumps({'prepared': str(root), 'rows': 1280}))
        return

    if (root / 'result.json').exists():
        raise RuntimeError('Completed pilot exists; use a new directory for a new attempt')
    if not args.image or not args.image.startswith('sha256:'):
        raise ValueError('Use the locally built immutable Docker image ID')
    source = subprocess.check_output(
        ['git', '-C', '/opt/naqex/rd-agent/source', 'rev-parse', 'HEAD'], text=True).strip()
    assert source == '484776c211e4fbbeef03e0ec00d6bbee7362a4f4'
    os.environ.update(CACHE_WITH_PICKLE='false', WORKSPACE_PATH=str(root / 'workspaces'),
                      NAQEX_RD_IMAGE=args.image)
    from rdagent.components.coder.factor_coder.factor import FactorTask, FactorFBWorkspace
    from rdagent.components.coder.factor_coder.config import FACTOR_COSTEER_SETTINGS
    from rdagent.components.coder.factor_coder.eva_utils import (
        FactorInfEvaluator, FactorSingleColumnEvaluator, FactorIndexEvaluator,
        FactorRowCountEvaluator, FactorEqualValueRatioEvaluator)
    import rdagent

    FACTOR_COSTEER_SETTINGS.python_bin = 'sh ' + str(Path(__file__).with_name('docker-python.sh'))
    FACTOR_COSTEER_SETTINGS.file_based_execution_timeout = 60
    task = FactorTask('momentum_3d', 'Causal three-day return on synthetic daily closes',
                      'close[t] / close[t-3] - 1', variables={'close': '$close'})
    (root / 'rd-task.txt').write_text(task.get_task_information())
    code = args.candidate.read_text()
    assert 0 < len(code.encode()) <= 16000
    (root / 'candidate.py').write_text(code)
    data = fixture()
    data.to_hdf(root / 'fixture.h5', key='data')
    cutoff = pd.Timestamp('2024-04-29')  # day 120, fixed before seeing output
    prefix = data.loc[data.index.get_level_values('datetime') <= cutoff]
    changed = data.copy()
    future = changed.index.get_level_values('datetime') > cutoff
    changed.loc[future, '$close'] *= np.linspace(2, 4, future.sum())
    execution_logs = {}

    def execute(name, inputs, script):
        folder = root / 'inputs' / name
        folder.mkdir(parents=True, exist_ok=True)
        inputs.to_hdf(folder / 'daily_pv.h5', key='data')
        os.environ['NAQEX_RD_DATA'] = str(folder)
        FACTOR_COSTEER_SETTINGS.data_folder_debug = str(folder)
        workspace = FactorFBWorkspace(target_task=task)
        workspace.inject_files(**{'factor.py': script})
        feedback, frame = workspace.execute()
        execution_logs[name] = {'feedback': feedback, 'workspace': str(workspace.workspace_path)}
        dump(root / 'executions.json', execution_logs)
        return frame

    result = execute('baseline', data, code)
    assert result is not None, execution_logs['baseline']
    expected = oracle(data)
    pd.testing.assert_frame_equal(result, expected, check_exact=False, rtol=1e-10, atol=1e-12)
    prefix_result = execute('prefix', prefix, code)
    changed_result = execute('future-perturbed', changed, code)
    pd.testing.assert_frame_equal(result.loc[prefix.index], prefix_result)
    pd.testing.assert_frame_equal(result.loc[prefix.index], changed_result.loc[prefix.index])
    # A deliberately leaky factor must fail the same causal check.
    leaky = data.groupby(level='instrument')['$close'].shift(-1) / data['$close'] - 1
    leaky_changed = changed.groupby(level='instrument')['$close'].shift(-1) / changed['$close'] - 1
    assert not leaky.loc[prefix.index].equals(leaky_changed.loc[prefix.index])
    failed = execute('expected-failure', prefix, 'raise RuntimeError("EXPECTED_PILOT_FAILURE")\n')
    assert failed is None and 'EXPECTED_PILOT_FAILURE' in execution_logs['expected-failure']['feedback']
    view = lambda frame: SimpleNamespace(execute=lambda: ('already executed', frame))
    checks = {}
    for evaluator in (FactorInfEvaluator, FactorSingleColumnEvaluator,
                      FactorIndexEvaluator, FactorRowCountEvaluator):
        message, score = evaluator().evaluate(view(result), view(expected))
        checks[evaluator.__name__] = {'score': float(score), 'message': message}
        assert score == 1, checks
    message, score = FactorEqualValueRatioEvaluator().evaluate(view(result.dropna()), view(expected.dropna()))
    assert score == 1
    checks['FactorEqualValueRatioEvaluator'] = {'score': float(score), 'message': message}
    dump(root / 'result.json', dict(status='passed', source_commit=source,
         package_paths=[str(Path(p).resolve()) for p in rdagent.__path__], image_id=args.image,
         pilot_sha256=digest(Path(__file__)), candidate_sha256=digest(root / 'candidate.py'),
         fixture_sha256=digest(root / 'fixture.h5'), rows=len(result),
         valid_values=int(result.notna().sum().sum()), checks=checks,
         prefix_invariance=True, future_perturbation_invariance=True,
         leaky_negative_control_rejected=True, execution_failure_detected=True,
         synthetic=True, strategy_qualified=False, paperclip_dispatch=False))
    print((root / 'result.json').read_text())


if __name__ == '__main__':
    main()

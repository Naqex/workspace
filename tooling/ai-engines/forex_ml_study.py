"""Bounded Discovery5 training/export and shared H1 triage; never broker execution."""
import argparse
from bisect import bisect_right
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import time
import traceback

WORKSPACE = Path(__file__).resolve().parents[2]
V2 = WORKSPACE/'projects/trader/foundation_v2'
sys.path.insert(0, str(V2))
sys.path.insert(0, str(V2/'scripts'))
# The isolated training venv owns NumPy/sklearn; only reuse product data libraries.
sys.path.append(str(V2/'.venv/Lib/site-packages'))

from trading_workspace_v2.forex_ml_candidate import (
    FEATURE_NAMES, ML_CANDIDATES, MLH1Candidate, features, pack_digest, predict, validate_pack)
from trading_workspace_v2.forex_coarse_input import load_coarse_hours
from trading_workspace_v2.forex_h4 import HOUR, size_for_stop
from trading_workspace_v2.retained import CostModel, InstrumentSpec, calculate_round_trip_cost
from forex_coarse_screen import simulate_coarse, coarse_source_pins
from forex_h4_pilot import initial_state, financing_calendar

PROTOCOL = WORKSPACE/'planning/research/ML-DISCOVERY5-20261108.md'
INPUTS = {
    '2023': ('77fcaa2722b336e729cb5fcce0b6f2aec1be9a652bbfdc7eabeb58a88a6f518a',
             '0cc3d1206f83f0bd53fbe5eea512542f58f4172a435bfecc590ecb49906531ce'),
    '2024': ('1e247d3f1d8064b19ef6de5bee9d62117566098c157096160e52821b439c923f',
             '3eafa49a7a1cf7bcf6d567d74115dc01b7f05888db13851f7ee0e36133e51ed0'),
}


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(4*1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def atomic(path, value):
    path = Path(path)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, indent=2, allow_nan=False), encoding='utf-8')
    tmp.replace(path)


def timestamp(year, month=1):
    return int(datetime(year, month, 1, tzinfo=timezone.utc).timestamp())


def label_pair(history, current, entry, exit_hour, *, terms, calendar):
    """Four-hour terminal-return surrogate, deliberately without stop-path labels."""
    _, distance = features(history, current.ask[3]-current.bid[3])
    quantity = size_for_stop(distance, slippage=Decimal(0)) if distance else None
    if quantity is None:
        return None
    model, instrument = terms
    values = []
    for side in ('BUY', 'SELL'):
        cost = calculate_round_trip_cost(model, side, quantity, instrument.contract_size,
            entry.bid[0], entry.ask[0], exit_hour.bid[0], exit_hour.ask[0])
        debit = Decimal(0)
        for event in calendar:
            if entry.first_time_msc < event.scheduled_time_msc <= exit_hour.first_time_msc:
                rate = event.debit_buy_usd_per_lot if side == 'BUY' else event.debit_sell_usd_per_lot
                debit += (rate*quantity*event.multiplier).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
        values.append(float((Decimal(str(cost['net_account']))-debit)/25))
    return values


def training_samples(hours, *, buy_debit, sell_debit):
    start = hours[0].mid.timestamp*1000
    end = (hours[-1].mid.timestamp+HOUR)*1000
    state = initial_state('reference', Decimal(0), 'a'*64, start=start).execution
    terms = CostModel.from_mapping(state.cost_model), InstrumentSpec.from_mapping(state.instrument_spec)
    calendar = list(financing_calendar(buy_debit, sell_rate=sell_debit, start=start, end=end))
    fee_times = [p.scheduled_time_msc for p in calendar]
    bars = [p.mid.candle() for p in hours]
    rows = []
    for i in range(99, len(hours)-5):
        history = bars[i-99:i+1]
        x, _ = features(history, hours[i].ask[3]-hours[i].bid[3])
        if x is None:
            continue
        entry, exit_hour = hours[i+1], hours[i+5]
        events = calendar[bisect_right(fee_times, entry.first_time_msc):
                          bisect_right(fee_times, exit_hour.first_time_msc)]
        y = label_pair(history, hours[i], entry, exit_hour, terms=terms, calendar=events)
        if y is not None:
            rows.append(dict(decision=(hours[i].mid.timestamp+HOUR),
                endpoint_msc=exit_hour.first_time_msc, x=x, y=y))
    return rows


def purged_training(rows, cutoff):
    date = datetime.fromtimestamp(cutoff, timezone.utc)
    lower = timestamp(date.year-1, date.month)
    return [r for r in rows if lower <= r['decision'] < cutoff and r['endpoint_msc'] < cutoff*1000]


def export_model(estimator, scaler=None):
    if scaler is not None:
        return dict(kind='ridge', mean=scaler.mean_.tolist(), scale=scaler.scale_.tolist(),
            coef=estimator.coef_.tolist(), intercept=estimator.intercept_.tolist())
    trees = []
    for fitted in estimator.estimators_:
        tree = fitted.tree_
        trees.append([[int(tree.feature[i]), float(tree.threshold[i]),
            int(tree.children_left[i]), int(tree.children_right[i]), tree.value[i, :, 0].tolist()]
            for i in range(tree.node_count)])
    return dict(kind='forest', trees=trees)


def fit_fold(rows, *, cutoff, algorithm, shuffled, fold_index):
    import numpy as np
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.linear_model import Ridge
    from sklearn.preprocessing import StandardScaler
    selected = purged_training(rows, cutoff)
    if len(selected) < 100:
        raise ValueError('insufficient purged training rows')
    x, y = np.asarray([p['x'] for p in selected]), np.asarray([p['y'] for p in selected])
    if shuffled:
        y = y[np.random.default_rng(42+fold_index).permutation(len(y))]
    scaler = None
    if algorithm == 'ridge':
        scaler = StandardScaler().fit(x)
        estimator = Ridge(alpha=10).fit(scaler.transform(x), y)
    elif algorithm == 'forest':
        estimator = RandomForestRegressor(n_estimators=80, max_depth=4,
            min_samples_leaf=100, random_state=42, n_jobs=1).fit(x, y)
    else:
        raise ValueError('unregistered estimator')
    model = export_model(estimator, scaler)
    expected = estimator.predict(scaler.transform(x) if scaler is not None else x)
    observed = np.asarray([predict(model, row.tolist()) for row in x])
    delta = float(np.max(np.abs(expected-observed)))
    if delta > 1e-10:
        raise ValueError('safe JSON model differs from training library')
    return dict(cutoff=cutoff, available_from=cutoff+HOUR,
        train_start=timestamp(datetime.fromtimestamp(cutoff, timezone.utc).year-1,
                              datetime.fromtimestamp(cutoff, timezone.utc).month),
        train_rows=len(selected), last_label_endpoint_msc=max(p['endpoint_msc'] for p in selected),
        model=model, export_max_delta=delta)


def quarter_cash(row):
    values = {q: Decimal(0) for q in range(1, 5)}
    unknown = 0
    for trade in row['trades']:
        if trade['exit_time_msc'] is None:
            bounds = trade['exit_interval_msc']
            a, b = [datetime.fromtimestamp(t/1000, timezone.utc) for t in bounds]
            if (a.month-1)//3 != (b.month-1)//3:
                unknown += 1
                continue
            when = a
        else:
            when = datetime.fromtimestamp(trade['exit_time_msc']/1000, timezone.utc)
        values[(when.month-1)//3+1] += Decimal(trade['net_usd'])
    return dict(realized_by_exit_quarter={str(q):str(v) for q,v in values.items()},
        ambiguous_quarter_trades=unknown, floating_at_end_usd=row['floating_usd'],
        basis='trade net including its full financing attributed to exit quarter; not quarterly equity returns')


def run(args):
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=False)
    began = time.perf_counter()
    def progress(stage, **more):
        atomic(output/'progress.json', dict(stage=stage, pid=os.getpid(),
            updated_at=datetime.now(timezone.utc).isoformat(), wall_seconds=time.perf_counter()-began, **more))
        print(stage, more, flush=True)
    try:
        config = json.loads(Path(args.config).read_bytes())
        if config['schema'] != 'forex-ml-discovery5-v1' or digest(PROTOCOL) != config['protocol_sha256']:
            raise ValueError('ML frozen protocol mismatch')
        if config['costs'] != {
                'reference':dict(slippage='0',buy_debit='9.3000000',sell_debit='-0.31000000'),
                'cost-stress':dict(slippage='0.00002',buy_debit='20',sell_debit='20')}:
            raise ValueError('ML registered cost scenario mismatch')
        source = {str(Path(__file__).resolve().relative_to(WORKSPACE)):digest(__file__)}
        source.update({'projects/trader/foundation_v2/'+name:sha for name,sha in coarse_source_pins().items()})
        if source != config['source_files']:
            raise ValueError('ML source pins mismatch before load')
        atomic(output/'execution-manifest.json', config)
        shutil.copy2(PROTOCOL, output/'protocol.md')
        for relative, sha in source.items():
            path = output/'source-snapshot'/relative
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(WORKSPACE/relative, path)
            if digest(path) != sha:
                raise ValueError('ML snapshot source changed')
        historical = {}
        proofs = {}
        for year in ('2023', '2024'):
            record = config['data'][year]
            inputs = json.loads(Path(record['inputs_path']).read_bytes())
            if tuple(inputs[r]['sha256'] for r in ('warmup','development')) != INPUTS[year]:
                raise ValueError('ML data not registered consumed inputs')
            if inputs['development']['first_day'] != year+'0101' or inputs['development']['last_day'] != year+'1231':
                raise ValueError('ML evaluation scope mismatch')
            progress('loading_'+year)
            roles = ('warmup','development') if year == '2023' else ('development',)
            for role in roles:
                spec = inputs[role]
                hours, proof = load_coarse_hours(spec['path'], cache_dir=record['cache_dir'],
                    sha256=spec['sha256'], first_day=spec['first_day'], last_day=spec['last_day'])
                historical[year+'_'+role] = hours
                proofs[year+'_'+role] = proof
        all_hours = historical['2023_warmup']+historical['2023_development']+historical['2024_development']
        if any(b.mid.timestamp <= a.mid.timestamp for a,b in zip(all_hours, all_hours[1:])):
            raise ValueError('ML data duplicate/overlap')
        reference = config['costs']['reference']
        progress('building_causal_features_labels')
        rows = training_samples(all_hours,buy_debit=Decimal(reference['buy_debit']),
                                sell_debit=Decimal(reference['sell_debit']))
        atomic(output/'samples-summary.json', dict(rows=len(rows), features=list(FEATURE_NAMES),
            first_decision=rows[0]['decision'],last_decision=rows[-1]['decision'],proofs=proofs))
        packs = []
        for index, candidate in enumerate(ML_CANDIDATES):
            algorithm = 'ridge' if 'ridge' in candidate else 'forest'
            shuffled = 'shuffled' in candidate
            pack = dict(schema='forex-ml-h1-pack-v1', candidate=candidate,
                feature_names=list(FEATURE_NAMES), protocol_sha256=config['protocol_sha256'],
                source_files=source,input_proofs=proofs, control=shuffled, folds=[])
            for fold_index, month in enumerate((1,4,7,10)):
                progress('fitting',candidate=candidate,quarter=fold_index+1)
                pack['folds'].append(fit_fold(rows,cutoff=timestamp(2024,month),algorithm=algorithm,
                    shuffled=shuffled,fold_index=fold_index))
            validate_pack(pack,candidate)
            atomic(output/(candidate+'.json'),pack)
            packs.append(pack)
        results = []
        warmup = [h.mid.candle() for h in historical['2023_development'][-100:]]
        start, end = timestamp(2024)*1000, timestamp(2025)*1000
        for pack in packs:
            for name, cost in config['costs'].items():
                progress('screening',candidate=pack['candidate'],scenario=name)
                row = simulate_coarse(pack['candidate'],warmup,historical['2024_development'],
                    start=start,end=end,data_sha256=INPUTS['2024'][1],name=name,
                    slippage=Decimal(cost['slippage']),buy_debit=Decimal(cost['buy_debit']),
                    sell_debit=Decimal(cost['sell_debit']),model_pack=pack)
                row.update(model_pack_sha256=pack_digest(pack),control=pack['control'],quarters=quarter_cash(row))
                results.append(row)
                atomic(output/(pack['candidate']+'-'+name+'-result.json'),row)
        for relative, sha in source.items():
            if digest(WORKSPACE/relative) != sha:
                raise ValueError('ML source drift during execution')
        atomic(output/'result.json',dict(schema='forex-ml-discovery5-results-v1',status='completed_triage_only',
            rows=results,protocol_sha256=config['protocol_sha256'],source_files=source,
            wall_seconds=time.perf_counter()-began,promotion_authorized=False,clean_oos=False,
            broker_calls=0,llm_calls=0))
        progress('completed_triage_only',scenarios=len(results))
    except BaseException as error:
        atomic(output/'failure.json',dict(error=type(error).__name__,message=str(error),traceback=traceback.format_exc()))
        progress('failed',error=type(error).__name__,message=str(error))
        raise


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',required=True)
    parser.add_argument('--output-dir',required=True)
    run(parser.parse_args())

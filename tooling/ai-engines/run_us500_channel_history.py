"""Unchanged FP07 cadence on registered 2013-2021 source views; no PnL."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time
import traceback

import run_us500_multiframe as source
import us500_multiframe as native
import us500_opportunities as study
from us500_year_source import load_year_side

YEARS = tuple(range(2013, 2022))
RECEIPT_SHA = '30cdcf5be9eed1e84953e5d0fd72bbb63028904eb01062a5908b60d4b7e0831f'
MANIFEST_SHA = 'ed9aab08e0d89fddee0e20ee76b83dc6e0ab8a119c7dd88e8eab8d8c18683edc'


def historical_year(root, entry, progress):
    year = entry['year']
    if year not in YEARS:
        raise ValueError('channel_history_registered_year_only')
    bindings = {}
    for name, expected in (('source-observation-proof.json', entry['proof_sha256']),
                           ('source-data-review-v1.json', entry['reader_sha256']),
                           ('native-source-oracle-v1.json', entry['oracle_sha256'])):
        path = root/name
        if source.digest(path) != expected:
            raise ValueError('channel_history_accepted_proof_binding')
        bindings[str(path.resolve())] = expected
    proof = json.loads((root/'source-observation-proof.json').read_text(encoding='utf-8'))
    reader = json.loads((root/'source-data-review-v1.json').read_text(encoding='utf-8'))
    oracle = json.loads((root/'native-source-oracle-v1.json').read_text(encoding='utf-8'))
    if (reader['source_presence_verified'] is not True or reader['year'] != year
            or reader['source_proof_sha256'] != entry['proof_sha256']
            or oracle['status'] != 'native_cached_source_prices_and_pairing_exact'
            or oracle['year'] != year or oracle['proofSha256'] != entry['proof_sha256']):
        raise ValueError('channel_history_source_review_missing')
    matches = [p for p in (root/'source-snapshot').glob(f'*-nyse-{year}.json')
               if source.digest(p) == proof['calendar_sha256']]
    if len(matches) != 1:
        raise ValueError('channel_history_frozen_calendar_binding')
    calendar = matches[0]
    bindings[str(calendar.resolve())] = source.digest(calendar)
    sessions = source.cash_sessions(json.loads(calendar.read_text(encoding='utf-8')))
    needed = {t for times in sessions.values() for t in times}
    sides = []
    lower = int(datetime(year, 1, 1, tzinfo=timezone.utc).timestamp()*1000)
    upper = int(datetime(year+1, 1, 1, tzinfo=timezone.utc).timestamp()*1000)
    for side in ('bid', 'ask'):
        progress('loading', year=year, side=side)
        loaded = load_year_side(root.resolve(), year=year, side=side,
            proof_sha256=entry['proof_sha256'], registered_years=YEARS)
        rows = list(loaded['rows'].values())
        source.validate_rows(rows, lower, upper, .001)
        bindings.update(loaded['bindings'])
        sides.append([r for r in rows if r['timestamp'] in needed])
    source.paired_spreads(*sides)
    pairs = {b['timestamp']: (b, a) for b, a in zip(*sides)}
    return sessions, pairs, dict(bindings=bindings, expected_minutes=len(needed),
        observed_minutes=len(pairs), missing_minutes=len(needed)-len(pairs),
        source_scope='accepted_source_only_four_quarters_and_native_oracle_reused_not_new_raw_validation')


def coverage(sessions, pairs, prepared):
    normal = {day for day, times in sessions.items() if len(times) == 390}
    complete = sum(all(t in pairs for t in sessions[day]) for day in normal)
    windows = {day: [] for day in normal}
    for e in prepared['snapshots'].values():
        if e['day'] in windows and e['slot'] in range(30, 331, 15):
            windows[e['day']].append(not e['blocked'] and e['m15'] is not None)
    unblocked = sum(len(v) == 21 and all(v) for v in windows.values())
    expected = sum(len(v) for v in sessions.values())
    return dict(normal_sessions=len(normal), short_sessions=len(sessions)-len(normal),
        complete_cash_normal_sessions=complete, unblocked_complete_decision_window_normal_sessions=unblocked,
        normal_days_blocked_or_missing_in_decision_window=len(normal)-unblocked,
        paired_cash_minute_coverage_pct=len(pairs)/expected*100,
        scope='retrospective_data_diagnostics_only_never_used_to_filter_prior_signals')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--recent-run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--protocol', type=Path, required=True)
    parser.add_argument('--protocol-sha256', required=True)
    args = parser.parse_args()
    if source.digest(args.protocol) != args.protocol_sha256:
        raise ValueError('channel_history_protocol_binding')
    receipt_path, manifest_path = args.source_root/'result.json', args.source_root/'manifest.json'
    if source.digest(receipt_path) != RECEIPT_SHA or source.digest(manifest_path) != MANIFEST_SHA:
        raise ValueError('channel_history_accepted_receipt_binding')
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    entries = receipt['new_years']
    if receipt['status'] != 'twelve_source_years_verified_no_strategy_simulation' or tuple(e['year'] for e in entries) != YEARS:
        raise ValueError('channel_history_accepted_year_census')
    recent_manifest = json.loads((args.recent_run/'manifest.json').read_text(encoding='utf-8'))
    recent = json.loads((args.recent_run/'result.json').read_text(encoding='utf-8'))
    if (recent['status'] != 'completed_frequency_only_not_edge'
            or source.digest(args.recent_run/'manifest.json') != recent['manifest_sha256']):
        raise ValueError('channel_history_recent_run_binding')
    root = Path(__file__).resolve().parent
    # The loader's registered window changes; rule, preparation and native lock do not.
    identity = [Path(study.__file__), Path(native.__file__), root/'review_us500_strategy_fit.py',
                root/'sealed_m1_review.py', root.parents[1]/'projects/trader/foundation_v2/engine_runtime/uv.lock']
    if any(source.digest(p) != recent_manifest['source_pins'].get(str(p.resolve())) for p in identity):
        raise ValueError('channel_history_rule_or_environment_changed')
    pins = source.source_pins(args.protocol)
    for p in [Path(__file__), Path(study.__file__), root/'us500_ma_reclaim.py', root/'us500_frequency_audit.py',
              root/'review_us500_strategy_fit.py', root/'tests/test_us500_year_source.py',
              root/'tests/test_us500_channel_history.py', receipt_path, manifest_path,
              args.recent_run/'manifest.json', args.recent_run/'result.json']:
        pins[str(p.resolve())] = source.digest(p)
    args.output.mkdir(exist_ok=False)
    source.save(args.output/'manifest.json', dict(schema='us500-channel-history-v1', source_pins=pins,
        years=YEARS, probe='FP07', rule_changed=False, financial_simulations=0, holdout_read=False))
    snapshot = args.output/'source-snapshot'
    snapshot.mkdir()
    for i, name in enumerate(pins):
        if Path(name).suffix in ('.py', '.md', '.lock'):
            (snapshot/f'{i:02}-{Path(name).name}').write_bytes(Path(name).read_bytes())
    lock = args.output/'controller.lock'
    with lock.open('x', encoding='utf-8') as stream: stream.write(str(os.getpid()))
    began, sequence, phase = time.perf_counter(), 0, 'starting'
    rows, timings = [], []

    def progress(stage, **values):
        nonlocal sequence, phase
        if (args.output/'CANCEL').exists(): raise InterruptedError('channel_history_cancelled')
        if time.perf_counter()-began > 600: raise TimeoutError('channel_history_deadline')
        sequence += 1
        phase = stage
        event = dict(stage=stage, sequence=sequence, pid=os.getpid(), completed_years=len(rows), total_years=len(YEARS),
            at_utc=datetime.now(timezone.utc).isoformat(), elapsed_seconds=round(time.perf_counter()-began, 3), **values)
        with (args.output/'events.jsonl').open('a', encoding='utf-8') as stream: stream.write(json.dumps(event)+'\n')
        source.save(args.output/'progress.json', event)
        (args.output/'PROGRESS.md').write_text('# US500 channel history\n\n'+json.dumps(event, indent=2)+'\n', encoding='utf-8')
        print(json.dumps(event), flush=True)

    try:
        for entry in entries:
            year = entry['year']
            start = time.perf_counter()
            sessions, pairs, admission = historical_year(args.source_root/str(year), entry, progress)
            prepared = native.prepare(sessions, pairs, lambda stage, **kw: progress(stage, year=year, **kw))
            source.save(args.output/f'input-{year}.json', admission)
            preparation = time.perf_counter()-start
            progress('counting', year=year)
            start = time.perf_counter()
            result = study.triggers(prepared, 'FP07')
            result['cadence'] = study.cadence(sessions, result['events'], pairs)
            result['coverage'] = coverage(sessions, pairs, prepared)
            source.save(args.output/f'{year}-FP07.json', result)
            row = dict(year=year, cadence=result['cadence'], coverage=result['coverage'],
                       counts=result['counts'], unique_days_by_reason=result['unique_days_by_reason'])
            rows.append(row)
            timings.append(dict(year=year, source_and_prepare_seconds=preparation,
                                count_and_write_seconds=time.perf_counter()-start))
            source.save(args.output/'completed-years.json', rows)
            if any(source.digest(Path(p)) != sha for p, sha in admission['bindings'].items()):
                raise ValueError('channel_history_input_drift')
            del pairs, prepared
        recent_rows = [r for r in recent['rows'] if r['probe'] == 'FP07']
        if (len(rows) != 9 or [r['year'] for r in recent_rows] != [2022, 2023, 2024]
                or any(source.digest(Path(p)) != sha for p, sha in pins.items())):
            raise ValueError('channel_history_final_census_or_source_drift')
        source.save(args.output/'result.json', dict(status='completed_historical_frequency_not_edge', rows=rows,
            reused_recent_rows=recent_rows, timings=timings, wall_seconds=time.perf_counter()-began,
            manifest_sha256=source.digest(args.output/'manifest.json'), new_financial_simulations=0,
            new_rule_versions=0, rule_and_preparation_identity_checked=True))
        progress('completed_historical_frequency_not_edge')
    except BaseException as error:
        source.save(args.output/'failure.json', dict(stage=phase, error_type=type(error).__name__, code=str(error),
            locations=[dict(file=Path(x.filename).name, line=x.lineno, function=x.name) for x in traceback.extract_tb(error.__traceback__)]))
        source.save(args.output/'progress.json', dict(stage='failed', failed_phase=phase, error_type=type(error).__name__))
        raise
    finally:
        lock.unlink(missing_ok=True)


if __name__ == '__main__':
    main()

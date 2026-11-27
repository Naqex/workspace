"""Run three preregistered opportunity counts on admitted development data only."""
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
from us500_frequency_audit import trace


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-root', type=Path, required=True)
    p.add_argument('--baseline', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--protocol', type=Path, required=True)
    p.add_argument('--protocol-sha256', required=True)
    args = p.parse_args()
    if source.digest(args.protocol) != args.protocol_sha256:
        raise ValueError('opportunity_protocol_binding')
    root = Path(__file__).resolve().parent
    pins = source.source_pins(args.protocol)
    for name in (Path(__file__), Path(study.__file__), root/'us500_ma_reclaim.py',
                 root/'us500_frequency_audit.py', root/'review_us500_strategy_fit.py',
                 root/'tests/test_us500_opportunities.py'):
        pins[str(name.resolve())] = source.digest(name)
    baseline_pins = {str(path.resolve()): source.digest(path)
                     for path in [args.baseline/'manifest.json', args.baseline/'result.json'] +
                     [args.baseline/f'frequency-{y}.json' for y in (2022, 2023, 2024)]}
    args.output.mkdir(exist_ok=False)
    source.save(args.output/'manifest.json', dict(schema='us500-opportunities-v1', source_pins=pins,
        baseline_pins=baseline_pins, years=[2022, 2023, 2024], probes=['FP06', 'FP07', 'FP08'],
        financial_simulations=0, holdout_read=False))
    snapshot = args.output/'source-snapshot'
    snapshot.mkdir()
    for i, name in enumerate(pins):
        (snapshot/f'{i:02}-{Path(name).name}').write_bytes(Path(name).read_bytes())
    lock = args.output/'controller.lock'
    with lock.open('x', encoding='utf-8') as stream: stream.write(str(os.getpid()))
    began = time.perf_counter()
    sequence = 0
    phase = 'starting'
    rows, timings = [], []
    combined_events = {k: [] for k in ('baseline', 'FP06', 'FP07', 'FP08')}
    combined_presence, all_sessions = {}, {}

    def progress(stage, **values):
        nonlocal sequence, phase
        if (args.output/'CANCEL').exists(): raise InterruptedError('opportunity_cancelled')
        if time.perf_counter() - began > 600: raise TimeoutError('opportunity_deadline')
        sequence += 1
        phase = stage
        event = dict(stage=stage, sequence=sequence, pid=os.getpid(),
            at_utc=datetime.now(timezone.utc).isoformat(), elapsed_seconds=round(time.perf_counter()-began, 3), **values)
        with (args.output/'events.jsonl').open('a', encoding='utf-8') as stream: stream.write(json.dumps(event)+'\n')
        source.save(args.output/'progress.json', event)
        (args.output/'PROGRESS.md').write_text('# US500 opportunity counts\n\n'+json.dumps(event, indent=2)+'\n', encoding='utf-8')
        print(json.dumps(event), flush=True)

    try:
        for year in (2022, 2023, 2024):
            start = time.perf_counter()
            sessions, pairs, admission = source.load_year(args.data_root/str(year), year, progress)
            prepared = native.prepare(sessions, pairs, lambda stage, **kw: progress(stage, year=year, **kw))
            source.save(args.output/f'input-{year}.json', admission)
            timings.append(dict(year=year, phase='source_and_prepare', seconds=time.perf_counter()-start))
            start = time.perf_counter()
            progress('counting', year=year)
            cases = {'baseline': study.reclaim(prepared), 'FP06': study.reclaim(prepared, retry=True)}
            cases.update({k: study.triggers(prepared, k) for k in ('FP07', 'FP08')})
            saved = json.loads((args.baseline/f'frequency-{year}.json').read_text(encoding='utf-8'))
            if trace(cases['baseline']) != trace(saved):
                raise ValueError('opportunity_saved_reclaim_trace_parity')
            old_days = {prepared['snapshots'][e['t']]['day'] for e in cases['baseline']['events'] if e['kind']=='confirm'}
            retry_days = {prepared['snapshots'][e['t']]['day'] for e in cases['FP06']['events'] if e['kind']=='confirm'}
            if not old_days <= retry_days:
                raise ValueError('opportunity_retry_lost_baseline_day')
            all_sessions.update(sessions)
            for key, result in cases.items():
                result['cadence'] = study.cadence(sessions, result['events'], pairs)
                if key in ('baseline', 'FP06') and result['cadence']['raw_signals'] != result['cadence']['first_signals_per_day']:
                    raise ValueError('opportunity_reclaim_confirmation_cap')
                source.save(args.output/f'{year}-{key}.json', result)
                rows.append(dict(year=year, probe=key, counts=result['counts'], cadence=result['cadence']))
                combined_events[key].extend(result['events'])
                for e in result['events']:
                    if e['kind'] != 'confirm': continue
                    for t in (e['t'], e['t']+native.M):
                        if t in pairs: combined_presence[t] = True
            timings.append(dict(year=year, phase='signals_parity_and_write', seconds=time.perf_counter()-start))
            if any(source.digest(Path(path)) != sha for path, sha in admission['bindings'].items()):
                raise ValueError('opportunity_admitted_input_drift')
            del pairs, prepared
        if len(rows) != 12 or any(source.digest(Path(p)) != sha for p, sha in {**pins, **baseline_pins}.items()):
            raise ValueError('opportunity_census_or_pin_drift')
        combined = {k: study.cadence(all_sessions, ev, combined_presence) for k, ev in combined_events.items()}
        source.save(args.output/'result.json', dict(status='completed_frequency_only_not_edge', rows=rows,
            combined=combined, timings=timings, wall_seconds=time.perf_counter()-began,
            manifest_sha256=source.digest(args.output/'manifest.json'), financial_simulations=0,
            new_frequency_designs=3, positions_fills_and_prop_not_simulated=True))
        progress('completed_frequency_only_not_edge', annual_cases=12)
    except BaseException as error:
        source.save(args.output/'failure.json', dict(stage=phase, error_type=type(error).__name__, code=str(error),
            locations=[dict(file=Path(x.filename).name, line=x.lineno, function=x.name) for x in traceback.extract_tb(error.__traceback__)]))
        source.save(args.output/'progress.json', dict(stage='failed', failed_phase=phase, error_type=type(error).__name__))
        raise
    finally:
        lock.unlink(missing_ok=True)


if __name__ == '__main__':
    main()

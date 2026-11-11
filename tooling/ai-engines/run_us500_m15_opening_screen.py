"""Bounded, cache-only registered US500 2022-24 M15 screen; no broker or models."""
import argparse
from datetime import datetime, timezone
from decimal import Decimal as D
import json
import os
from pathlib import Path
import sys
import time

import index_noise_study as core
from sealed_m1_review import cash_sessions, digest, verify_source_proof, validate_rows, paired_spreads
import us500_m15_opening_screen as study
import review_us500_m15_opening as reviewer

PROOFS = {
    2022: '7a41f021c86a04345ce2591b90efa72112792ef5479c16ff6d1167f7064dc840',
    2023: '61d46d061a870e98a97b696b95d8efab2d28abe190d94f2fc04c1b2255b1909c',
    2024: 'ccda74a3510986a748d11c1a9b19e2d9b62da1ce61397ed8cb5cf0af218d1c1b',
}


def save(path, value):
    with path.open('x', encoding='utf-8') as f:
        json.dump(value, f, indent=2, ensure_ascii=False, default=str, allow_nan=False)
        f.write('\n')


def load_year(root, year, progress):
    if year not in PROOFS:
        raise ValueError('screen_registered_year_only_holdout_closed')
    calendar = Path(__file__).with_name('fixtures')/f'nyse-{year}.json'
    if digest(root/'source-observation-proof.json') != PROOFS[year]:
        raise ValueError('accepted_source_proof_binding')
    manifest = json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    downloaded = json.loads((root/'result.json').read_text(encoding='utf-8'))
    provenance = verify_source_proof(root, manifest, downloaded, calendar, frozen_source=True)
    sessions = cash_sessions(json.loads(calendar.read_text(encoding='utf-8')))
    needed = {t for stamps in sessions.values() for t in stamps[:152]}
    proof = json.loads((root/'source-observation-proof.json').read_text(encoding='utf-8'))
    seals = {r['request']: r for r in proof['output_seals']}
    if set(seals) != {f'q{q}-{s}' for q in range(1, 5) for s in ('bid', 'ask')}:
        raise ValueError('screen_four_quarters_both_sides')
    pairs, bindings = {}, {str(root/'source-observation-proof.json'): PROOFS[year], str(calendar): digest(calendar)}
    for q in range(1, 5):
        progress('loading_quarter', year=year, quarter=q)
        sides = []
        lower = int(datetime(year, q*3-2, 1, tzinfo=timezone.utc).timestamp()*1000)
        upper = int(datetime(year+1, 1, 1, tzinfo=timezone.utc).timestamp()*1000) if q == 4 else int(datetime(year, q*3+1, 1, tzinfo=timezone.utc).timestamp()*1000)
        for side in ('bid', 'ask'):
            path = root/f'q{q}-{side}.json'
            if digest(path) != seals[f'q{q}-{side}']['sha256']:
                raise ValueError('screen_canonical_seal')
            rows = json.loads(path.read_text(encoding='utf-8'))
            if len(rows) != seals[f'q{q}-{side}']['rows']:
                raise ValueError('screen_quarter_census')
            validate_rows(rows, lower, upper, .001)
            bindings[str(path)] = seals[f'q{q}-{side}']['sha256']
            sides.append(rows)
        paired_spreads(*sides)
        pairs.update({b['timestamp']: (b, a) for b, a in zip(*sides) if b['timestamp'] in needed})
    return sessions, pairs, dict(provenance=provenance, bindings=bindings,
                                needed_minutes=len(needed), observed_minutes=len(pairs))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-root', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--protocol', type=Path, required=True)
    p.add_argument('--protocol-sha256', required=True)
    a = p.parse_args()
    if digest(a.protocol) != a.protocol_sha256:
        raise ValueError('screen_protocol_binding')
    workspace = Path(__file__).resolve().parents[2]
    core.bind_core(workspace/'projects/trader/foundation_v2')
    a.output.mkdir(exist_ok=False)
    (a.output/'controller.lock').write_text(str(os.getpid()), encoding='utf-8')
    began, cpu = time.perf_counter(), time.process_time()
    seq, phase = 0, 'starting'
    rows, reviews, timings = [], [], []

    def progress(stage, **values):
        nonlocal seq, phase
        if (a.output/'CANCEL').exists():
            raise InterruptedError('screen_cancelled')
        if time.perf_counter()-began > 600:
            raise TimeoutError('screen_deadline')
        seq += 1
        phase = stage
        event = dict(sequence=seq, stage=stage, updated_at_utc=datetime.now(timezone.utc).isoformat(),
                     pid=os.getpid(), elapsed_seconds=time.perf_counter()-began, **values)
        with (a.output/'events.jsonl').open('a', encoding='utf-8') as f:
            f.write(json.dumps(event, default=str)+'\n')
        tmp = a.output/'progress.tmp'
        tmp.write_text(json.dumps(event, default=str), encoding='utf-8')
        os.replace(tmp, a.output/'progress.json')
        (a.output/'PROGRESS.md').write_text('# US500 M15 screening\n\n'+json.dumps(event, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        print(json.dumps(event), flush=True)

    try:
        paths = {Path(__file__).resolve(), Path(study.__file__), Path(reviewer.__file__),
                 Path(core.__file__), Path(study.book.__file__), Path(__file__).with_name('sealed_m1_review.py'),
                 Path(__file__).with_name('review_index_noise.py')}
        paths.update(Path(m.__file__) for n,m in sys.modules.copy().items()
                     if getattr(m, '__file__', None) and (n.startswith('trading_workspace_v2') or n in ('forex_h4_pilot','forex_study_batch','candle_source_provenance')))
        pins = {str(path.resolve()): digest(path) for path in paths}
        save(a.output/'manifest.json', dict(protocol_sha256=a.protocol_sha256,
            registered_years=list(PROOFS), candidates=study.CANDIDATES, source_pins=pins,
            data_proofs=PROOFS, python=sys.version, clean_oos=False, holdout_read=False,
            network_calls=0, broker_calls=0, model_calls=0))
        snapshot = a.output/'source-snapshot'
        snapshot.mkdir()
        (snapshot/'protocol.md').write_bytes(a.protocol.read_bytes())
        for i,path in enumerate(sorted(paths)):
            (snapshot/f'{i:03}-{path.name}').write_bytes(path.read_bytes())
        for year in PROOFS:
            progress('verifying_source', year=year)
            at = time.perf_counter()
            sessions, pairs, data = load_year(a.data_root/str(year), year, progress)
            save(a.output/f'inputs-{year}.json', data)
            timings.append(dict(year=year, phase='source_validation_load', seconds=time.perf_counter()-at))
            for policy in study.CANDIDATES:
                for scenario,slip,null in [('reference',D('.25'),False), ('stress',D('.75'),False), ('null',D('.25'),True)]:
                    progress('simulating', year=year, policy=policy, scenario=scenario)
                    at,used=time.perf_counter(),time.process_time()
                    result=study.simulate(sessions,pairs,policy=policy,slippage=slip,null_control=null,
                        progress=lambda i,n:progress('simulating',year=year,policy=policy,scenario=scenario,done=i,total=n),
                        deadline=began+600)
                    simulation_seconds=time.perf_counter()-at
                    progress('reviewing',year=year,policy=policy,scenario=scenario)
                    at=time.perf_counter()
                    review=reviewer.inspect(result,sessions,pairs)
                    metric=study.metrics(result)
                    name=f'{year}-{policy}-{scenario}'
                    save(a.output/(name+'.json'),result)
                    save(a.output/(name+'-review.json'),review)
                    row=dict(year=year,policy=policy,scenario=scenario,**metric,
                        result_sha256=digest(a.output/(name+'.json')),
                        review_sha256=digest(a.output/(name+'-review.json')))
                    rows.append(row)
                    save(a.output/(name+'-metrics.json'),row)
                    reviews.append(review['status'])
                    timings.append(dict(year=year,policy=policy,scenario=scenario,simulation_seconds=simulation_seconds,
                        review_seconds=time.perf_counter()-at,cpu_seconds=time.process_time()-used))
            del sessions,pairs
        if any(digest(Path(path))!=sha for path,sha in pins.items()) or digest(a.protocol)!=a.protocol_sha256:
            raise ValueError('screen_source_or_protocol_changed')
        if len(rows)!=18 or len(reviews)!=18:
            raise ValueError('screen_book_census')
        save(a.output/'result.json',dict(status='completed_screen_not_qualified',rows=rows,timings=timings,
            wall_seconds=time.perf_counter()-began,cpu_seconds=time.process_time()-cpu,
            manifest_sha256=digest(a.output/'manifest.json'),reviewed_books=len(reviews)))
        progress('completed_screen_not_qualified',books=len(rows))
    except BaseException as error:
        failure=dict(stage=phase,error_type=type(error).__name__,
            completed_books=len(rows),elapsed_seconds=time.perf_counter()-began)
        save(a.output/'failure.json',failure)
        (a.output/'progress.json').write_text(json.dumps(dict(failure,stage='failed',failed_phase=phase)),encoding='utf-8')
        (a.output/'PROGRESS.md').write_text('# US500 M15 — failed\n\n'+json.dumps(failure,indent=2)+'\n',encoding='utf-8')
        raise
    finally:
        (a.output/'controller.lock').unlink(missing_ok=True)


if __name__=='__main__':
    main()

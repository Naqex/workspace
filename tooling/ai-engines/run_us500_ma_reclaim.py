"""Registered frequency gate then one optional native US500 financial screen."""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import time
import traceback
import warnings

import run_us500_multiframe as source
import us500_multiframe as native
import us500_ma_reclaim as study
import us500_frequency_audit as frequency_parent
import review_us500_multiframe as metrics


def frequency_eligible(rows):
    if sorted(r['year'] for r in rows)!=[2022,2023,2024]:
        raise ValueError('reclaim_three_year_frequency_census')
    values=[r['exact_fill_available'] for r in rows]
    return sum(values)>=200 and min(values)>=50


def cost_screen_registration(path,sha,attempt):
    if source.digest(path)!=sha:
        raise ValueError('reclaim_cost_registration_hash')
    reg=json.loads(path.read_text(encoding='utf-8'))
    expected=dict(schema='us500-ma-reclaim-cost-screen-registration-v1',stage='G2_exploratory_cost_and_execution_only',
        parent_frequency_manifest_sha256=source.digest(attempt/'manifest.json'),
        parent_frequency_result_sha256=source.digest(attempt/'result.json'),config=study.CONFIG,
        years=[2022,2023,2024],observed_exact_signal_counts=[58,50,57],financial_books=6,null_books=3,
        deep_review_frequency_floor_unchanged=200,strategy_rule_change=False,edge_qualified=False,holdout_read=False)
    old=json.loads((attempt/'result.json').read_text(encoding='utf-8'))
    manifest=json.loads((attempt/'manifest.json').read_text(encoding='utf-8'))
    if (reg!=expected or old['status']!='completed_frequency_only_below_priority_floor' or old['rows']
        or old['frequency_eligible'] is not False or manifest['config']!=study.CONFIG
        or [r['exact_fill_available'] for r in old['frequencies']]!=[58,50,57]):
        raise ValueError('reclaim_cost_registration_scope_or_parent')
    return reg


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-root',type=Path,required=True)
    p.add_argument('--parent-frequency',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--protocol',type=Path,required=True)
    p.add_argument('--protocol-sha256',required=True)
    p.add_argument('--cost-screen-registration',type=Path)
    p.add_argument('--cost-screen-registration-sha256')
    p.add_argument('--frequency-attempt',type=Path)
    args=p.parse_args()
    if source.digest(args.protocol)!=args.protocol_sha256:
        raise ValueError('reclaim_protocol_binding')
    extras=(args.cost_screen_registration,args.cost_screen_registration_sha256,args.frequency_attempt)
    if any(extras) and not all(extras):
        raise ValueError('reclaim_cost_registration_complete_binding_required')
    registration=cost_screen_registration(*extras) if all(extras) else None
    pins=source.source_pins(args.protocol)
    for path in (Path(__file__),Path(study.__file__),Path(frequency_parent.__file__),
                 Path(__file__).with_name('tests')/'test_us500_ma_reclaim.py'):
        pins[str(path.resolve())]=source.digest(path)
    if registration:
        pins[str(args.cost_screen_registration.resolve())]=source.digest(args.cost_screen_registration)
        amendment=Path(__file__).resolve().parents[2]/'planning/research/US500-MA-RECLAIM-COST-SCREEN-AMENDMENT-20261111.md'
        pins[str(amendment)]=source.digest(amendment)
    parent_paths=[args.parent_frequency/'result.json',args.parent_frequency/'manifest.json']
    parent_paths += [args.parent_frequency/f'{year}-FP02.json' for year in (2022,2023,2024)]
    parent_pins={str(path.resolve()):source.digest(path) for path in parent_paths}
    if registration:
        for name in ('result.json','manifest.json'):
            path=args.frequency_attempt/name
            parent_pins[str(path.resolve())]=source.digest(path)
    parent_result=json.loads((args.parent_frequency/'result.json').read_text(encoding='utf-8'))
    if parent_result['status']!='completed_frequency_only_not_edge':
        raise ValueError('reclaim_parent_frequency_terminal')
    args.output.mkdir(exist_ok=False)
    source.save(args.output/'manifest.json',dict(schema='us500-ma-reclaim-v1',source_pins=pins,parent_pins=parent_pins,
            config=study.CONFIG,years=[2022,2023,2024],holdout_read=False,financial_books_if_eligible=6,null_books_if_eligible=3,
            cost_screen_registration=registration))
    snapshot=args.output/'source-snapshot'
    snapshot.mkdir()
    for i,(name,sha) in enumerate(pins.items()):
        (snapshot/f'{i:02}-{Path(name).name}').write_bytes(Path(name).read_bytes())
    lock=args.output/'controller.lock'
    with lock.open('x',encoding='utf-8') as stream:stream.write(str(os.getpid()))
    began=time.perf_counter()
    cpu=time.process_time()
    seq=0
    phase='starting'
    frequencies,rows,timings=[],[],[]
    loaded={}

    def progress(stage,**kw):
        nonlocal seq,phase
        if (args.output/'CANCEL').exists():raise InterruptedError('reclaim_cancelled')
        if time.perf_counter()-began>600:raise TimeoutError('reclaim_deadline')
        phase=stage
        seq+=1
        event=dict(stage=stage,sequence=seq,at_utc=datetime.now(timezone.utc).isoformat(),pid=os.getpid(),
                   elapsed_seconds=round(time.perf_counter()-began,3),completed_books=len(rows),**kw)
        with (args.output/'events.jsonl').open('a',encoding='utf-8') as stream:stream.write(json.dumps(event)+'\n')
        source.save(args.output/'progress.json',event)
        (args.output/'PROGRESS.md').write_text('# US500 MA reclaim\n\n'+json.dumps(event,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(event),flush=True)

    try:
        warnings.filterwarnings('ignore',message='Timestamp.utcnow is deprecated.*')
        for year in (2022,2023,2024):
            at=time.perf_counter()
            sessions,pairs,admission=source.load_year(args.data_root/str(year),year,progress)
            prepared=native.prepare(sessions,pairs,lambda stage,**kw:progress(stage,year=year,**kw))
            source.save(args.output/f'input-{year}.json',admission)
            timings.append(dict(year=year,phase='source_and_preparation',seconds=time.perf_counter()-at))
            at=time.perf_counter()
            progress('counting_reclaim',year=year)
            result=study.frequency(prepared,pairs)
            old=json.loads((args.parent_frequency/f'{year}-FP02.json').read_text(encoding='utf-8'))
            old_row=next(r for r in parent_result['rows'] if r['year']==year and r['probe']=='FP02')
            if old['counts']!=old_row['counts']:
                raise ValueError('reclaim_parent_counts_binding')
            arm_trace=lambda data:[{k:e[k] for k in ('t','side')} for e in data['events'] if e['kind']=='arm']
            if arm_trace(result)!=arm_trace(old):
                raise ValueError('reclaim_parent_setup_parity')
            source.save(args.output/f'frequency-{year}.json',result)
            frequencies.append(dict(year=year,counts=result['counts'],exact_fill_available=result['exact_fill_available'],
                                    exact_fill_unavailable=result['exact_fill_unavailable']))
            timings.append(dict(year=year,phase='frequency_and_setup_parity',seconds=time.perf_counter()-at))
            loaded[year]=(pairs,prepared)
        eligible=frequency_eligible(frequencies)
        if registration and [r['exact_fill_available'] for r in frequencies]!=registration['observed_exact_signal_counts']:
            raise ValueError('reclaim_registered_frequency_changed')
        run_financial=eligible or registration is not None
        source.save(args.output/'frequency-gate.json',dict(frequencies=frequencies,eligible=eligible,
                     total_exact_fill_available=sum(r['exact_fill_available'] for r in frequencies),scope='research_priority_not_edge'))
        if run_financial:
            for year in (2022,2023,2024):
                pairs,prepared=loaded.pop(year)
                at=time.perf_counter()
                quotes=native.quote_data(pairs)
                timings.append(dict(year=year,phase='native_quote_preparation',seconds=time.perf_counter()-at))
                for scenario,slip,null in (('reference','.25',False),('stress','.75',False),('null','.25',True)):
                    progress('starting_native_book',year=year,scenario=scenario)
                    at=time.perf_counter()
                    book=native.execute(study.CONFIG,prepared,pairs,quotes,slip,
                        lambda stage,**kw:progress(stage,year=year,scenario=scenario,**kw),null=null,policy_factory=study.ReclaimPolicy)
                    simulation=time.perf_counter()-at
                    name=f'{year}-R123-{scenario}'
                    source.save(args.output/(name+'.json'),book)
                    at=time.perf_counter()
                    durable=json.loads((args.output/(name+'.json')).read_text(encoding='utf-8'))
                    review=study.review(durable,prepared,pairs)
                    source.save(args.output/(name+'-review.json'),review)
                    row=dict(year=year,candidate='R123',scenario=scenario,**metrics.metrics(durable))
                    source.save(args.output/(name+'-metrics.json'),row)
                    source.save(args.output/(name+'-seal.json'),dict(result_sha256=source.digest(args.output/(name+'.json')),
                        review_sha256=source.digest(args.output/(name+'-review.json')),manifest_sha256=source.digest(args.output/'manifest.json')))
                    rows.append(row)
                    timings.append(dict(year=year,scenario=scenario,phase='native_book',simulation_seconds=simulation,review_seconds=time.perf_counter()-at))
                    progress('native_book_verified',year=year,scenario=scenario)
                del pairs,prepared,quotes
        if len(rows)!=(9 if run_financial else 0) or any(source.digest(Path(path))!=sha for path,sha in {**pins,**parent_pins}.items()):
            raise ValueError('reclaim_final_census_or_source_drift')
        status=('completed_exploratory_cost_screen_not_qualified' if registration else
                'completed_native_development_not_qualified' if eligible else 'completed_frequency_only_below_priority_floor')
        source.save(args.output/'result.json',dict(status=status,frequency_eligible=eligible,frequencies=frequencies,rows=rows,timings=timings,
            wall_seconds=time.perf_counter()-began,cpu_seconds=time.process_time()-cpu,financial_books=6 if run_financial else 0,
            null_books=3 if run_financial else 0,edge_qualified=False,manifest_sha256=source.digest(args.output/'manifest.json')))
        progress(status)
    except BaseException as error:
        source.save(args.output/'failure.json',dict(stage=phase,error_type=type(error).__name__,code=str(error),completed_books=len(rows),
            locations=[dict(file=Path(f.filename).name,line=f.lineno,function=f.name) for f in traceback.extract_tb(error.__traceback__)]))
        source.save(args.output/'progress.json',dict(stage='failed',failed_phase=phase,error_type=type(error).__name__))
        raise
    finally:
        lock.unlink(missing_ok=True)


if __name__=='__main__':
    main()

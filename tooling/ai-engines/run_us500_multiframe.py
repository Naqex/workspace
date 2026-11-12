"""Registered cache-only 27-config native Nautilus US500 development batch."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time
import traceback
import warnings

from sealed_m1_review import cash_sessions, digest, validate_rows, paired_spreads
from us500_year_source import load_year_side
from run_us500_m15_opening_screen import admitted_calendar, PROOFS
import us500_multiframe as study
import review_us500_multiframe as reviewer


def save(path,value):
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value,ensure_ascii=False,default=str,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    # Match the existing pilot writer: Windows readers can briefly deny rename.
    for attempt in range(21):
        try:
            os.replace(temp,path)
            return
        except PermissionError as error:
            if getattr(error,'winerror',None) not in (5,32) or attempt==20:
                raise
            time.sleep(.05)


def load_year(root,year,progress):
    if year not in PROOFS:
        raise ValueError('registered_development_years_only')
    proof=json.loads((root/'source-observation-proof.json').read_text(encoding='utf-8'))
    if digest(root/'source-observation-proof.json')!=PROOFS[year]:
        raise ValueError('source_proof_binding')
    calendar,bindings=admitted_calendar(root,year,proof)
    sessions=cash_sessions(calendar)
    needed={t for stamps in sessions.values() for t in stamps}
    sides=[]
    lower=int(datetime(year,1,1,tzinfo=timezone.utc).timestamp()*1000)
    upper=int(datetime(year+1,1,1,tzinfo=timezone.utc).timestamp()*1000)
    for side in ('bid','ask'):
        progress('loading',year=year,side=side)
        loaded=load_year_side(root.resolve(),year=year,side=side,proof_sha256=PROOFS[year])
        rows=list(loaded['rows'].values())
        validate_rows(rows,lower,upper,.001)
        bindings.update(loaded['bindings'])
        sides.append([r for r in rows if r['timestamp'] in needed])
    paired_spreads(*sides)
    pairs={b['timestamp']:(b,a) for b,a in zip(*sides)}
    return sessions,pairs,dict(bindings=bindings,expected_minutes=len(needed),observed_minutes=len(pairs),
                              missing_minutes=len(needed)-len(pairs),sessions=len(sessions),
                              source_scope='reuse_accepted_full_four_quarter_raw_proofs_not_new_raw_decoder_validation')


def source_pins(protocol):
    root=Path(__file__).resolve().parent
    paths=[Path(__file__).resolve(),Path(study.__file__),Path(reviewer.__file__),
           root/'us500_year_source.py',root/'sealed_m1_review.py',root/'run_us500_m15_opening_screen.py',
           root/'tests/test_us500_multiframe.py',root/'tests/test_run_us500_multiframe.py',
           root.parents[1]/'projects/trader/foundation_v2/engine_runtime/uv.lock',protocol]
    return {str(p.resolve()):digest(p) for p in paths}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--protocol',type=Path,required=True)
    parser.add_argument('--protocol-sha256',required=True)
    parser.add_argument('--resume-completed',action='store_true')
    parser.add_argument('--deadline-seconds',type=int,default=1800)
    parser.add_argument('--year',type=int,choices=(2022,2023,2024),help='Isolated year cohort; separate output/writer')
    args=parser.parse_args()
    if digest(args.protocol)!=args.protocol_sha256:
        raise ValueError('protocol_pin_required')
    pins=source_pins(args.protocol)
    args.output.mkdir(exist_ok=args.resume_completed,parents=True)
    years=[args.year] if args.year else [2022,2023,2024]
    total_books=len(years)*57
    manifest=dict(schema='us500-multiframe-native-v1',source_pins=pins,proofs=PROOFS,
                  configurations=study.configurations(),years=years,scenarios=['reference','stress'],
                  financial_books=54*len(years),null_books=3*len(years),engine='NautilusTrader1.231.0',holdout_read=False,
                  data_root=str(args.data_root.resolve()),deadline_seconds=args.deadline_seconds)
    path=args.output/'manifest.json'
    if args.resume_completed:
        if json.loads(path.read_text(encoding='utf-8'))!=json.loads(json.dumps(manifest)):
            raise ValueError('resume_manifest_drift')
    else:
        save(path,manifest)
        snapshot=args.output/'source-snapshot'
        snapshot.mkdir()
        for i,(name,sha) in enumerate(pins.items()):
            (snapshot/f'{i:02}-{Path(name).name}').write_bytes(Path(name).read_bytes())
    began,cpu=time.perf_counter(),time.process_time()
    lock=args.output/'controller.lock'
    with lock.open('x',encoding='utf-8') as stream:
        json.dump(dict(pid=os.getpid(),started_at=datetime.now(timezone.utc).isoformat()),stream)
    rows,timings=[],[]
    sequence=0
    current={}

    def progress(stage,**values):
        nonlocal sequence,current
        if (args.output/'CANCEL').exists():
            raise InterruptedError('batch_cancel_marker')
        if time.perf_counter()-began>args.deadline_seconds:
            raise TimeoutError('batch_deadline')
        sequence+=1
        current=dict(sequence=sequence,stage=stage,pid=os.getpid(),at_utc=datetime.now(timezone.utc).isoformat(),
                     elapsed_seconds=round(time.perf_counter()-began,3),completed_books=len(rows),total_books=total_books,**values)
        with (args.output/'events.jsonl').open('a',encoding='utf-8') as stream:
            stream.write(json.dumps(current,default=str)+'\n')
        save(args.output/'progress.json',current)
        (args.output/'PROGRESS.md').write_text('# US500 native backtest\n\n'+json.dumps(current,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(current),flush=True)

    try:
        warnings.filterwarnings('ignore',message='Timestamp.utcnow is deprecated.*')
        for year in years:
            at=time.perf_counter()
            sessions,pairs,admission=load_year(args.data_root/str(year),year,progress)
            save(args.output/f'input-{year}.json',admission)
            prepared=study.prepare(sessions,pairs,lambda stage,**kw:progress(stage,year=year,**kw))
            save(args.output/f'preparation-{year}.json',dict(counts=prepared['counts']))
            quotes=study.quote_data(pairs)
            timings.append(dict(year=year,phase='source_preparation_quotes',seconds=time.perf_counter()-at,quotes=len(quotes)))
            configs=study.configurations()
            jobs=[(c,scenario,slip,False) for c in configs for scenario,slip in (('reference','.25'),('stress','.75'))]
            jobs += [(next(c for c in configs if c['lane']==lane and c['k']=='0.1'),'null','.25',True) for lane in 'ABC']
            for config,scenario,slip,null in jobs:
                name=f'{year}-{config["id"]}-{scenario}'
                progress('starting_book',year=year,candidate=config['id'],scenario=scenario)
                result_path=args.output/(name+'.json')
                seal_path=args.output/(name+'-seal.json')
                at,used=time.perf_counter(),time.process_time()
                reused=False
                if args.resume_completed and seal_path.exists():
                    seal=json.loads(seal_path.read_text(encoding='utf-8'))
                    if digest(result_path)!=seal['result_sha256'] or digest(path)!=seal['manifest_sha256']:
                        raise ValueError('completed_book_seal_drift')
                    result=json.loads(result_path.read_text(encoding='utf-8'))
                    if result['config']!=config or result['null']!=null or str(result['slippage'])!=str(study.D(slip)):
                        raise ValueError('completed_book_identity')
                    reused=True
                else:
                    result=study.execute(config,prepared,pairs,quotes,slip,
                        lambda stage,**kw:progress(stage,year=year,candidate=config['id'],scenario=scenario,**kw),null=null)
                    save(result_path,result)
                simulation=time.perf_counter()-at
                at=time.perf_counter()
                # Deserialize even fresh results: review exactly the durable artifact.
                result=json.loads(result_path.read_text(encoding='utf-8'))
                review=reviewer.inspect(result,pairs)
                metric=reviewer.metrics(result)
                save(args.output/(name+'-review.json'),review)
                row=dict(year=year,candidate=config['id'],config=config,scenario=scenario,**metric)
                rows.append(row)
                save(args.output/(name+'-metrics.json'),row)
                save(seal_path,dict(result_sha256=digest(result_path),review_sha256=digest(args.output/(name+'-review.json')),
                                    manifest_sha256=digest(path)))
                timings.append(dict(year=year,candidate=config['id'],scenario=scenario,reused=reused,
                                    simulation_seconds=simulation,review_seconds=time.perf_counter()-at,cpu_seconds=time.process_time()-used))
                progress('book_verified',year=year,candidate=config['id'],scenario=scenario)
            del quotes,prepared,pairs,sessions
        if len(rows)!=total_books or any(digest(Path(p))!=sha for p,sha in pins.items()):
            raise ValueError('final_census_or_source_drift')
        save(args.output/'result.json',dict(status='completed_development_screen_not_qualified',rows=rows,timings=timings,
                                          wall_seconds=time.perf_counter()-began,cpu_seconds=time.process_time()-cpu,
                                          manifest_sha256=digest(path)))
        progress('completed_development_screen_not_qualified')
    except BaseException as error:
        save(args.output/'failure.json',dict(error_type=type(error).__name__,code=str(error)[:200],
             location=[dict(file=Path(f.filename).name,line=f.lineno,function=f.name) for f in traceback.extract_tb(error.__traceback__)],
             last_progress=current,completed_books=len(rows)))
        failed=dict(current,stage='failed',error_type=type(error).__name__,failure_file='failure.json')
        save(args.output/'progress.json',failed)
        (args.output/'PROGRESS.md').write_text('# US500 native backtest — failed\n\n'+json.dumps(failed,indent=2)+'\n',encoding='utf-8')
        raise
    finally:
        lock.unlink(missing_ok=True)


if __name__=='__main__':
    main()

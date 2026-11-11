"""Bounded, registered source-only frequency audit; never calculates new PnL."""
import argparse
from collections import Counter
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import time
import traceback

import run_us500_multiframe as source
import us500_multiframe as parent
import us500_frequency_audit as audit


def saved_trace(root,year,candidate):
    path=root/f'{year}-{candidate}-reference.json'
    seal=json.loads((root/f'{year}-{candidate}-reference-seal.json').read_text(encoding='utf-8'))
    if source.digest(path)!=seal['result_sha256'] or source.digest(root/'manifest.json')!=seal['manifest_sha256']:
        raise ValueError('frequency_parent_book_binding')
    book=json.loads(path.read_text(encoding='utf-8'))
    return [{k:v for k,v in e.items() if k in ('kind','t','side')} for e in book['policy_events'] if e['kind'] in ('arm','confirm')]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-root',type=Path,required=True)
    p.add_argument('--parent-base',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--protocol',type=Path,required=True)
    p.add_argument('--protocol-sha256',required=True)
    args=p.parse_args()
    if source.digest(args.protocol)!=args.protocol_sha256:
        raise ValueError('frequency_protocol_binding')
    pins=source.source_pins(args.protocol)
    for path in (Path(__file__),Path(audit.__file__),Path(__file__).with_name('tests')/'test_us500_frequency_audit.py'):
        pins[str(path.resolve())]=source.digest(path)
    args.output.mkdir(exist_ok=False)
    manifest=dict(schema='us500-frequency-audit-v1',source_pins=pins,probes=audit.PROBES,
                  years=[2022,2023,2024],holdout_read=False,financial_simulations=0,
                  data_root=str(args.data_root.resolve()),parent_base=str(args.parent_base.resolve()))
    source.save(args.output/'manifest.json',manifest)
    snapshots=args.output/'source-snapshot'
    snapshots.mkdir()
    for i,(name,sha) in enumerate(pins.items()):
        (snapshots/f'{i:02}-{Path(name).name}').write_bytes(Path(name).read_bytes())
    lock=args.output/'controller.lock'
    with lock.open('x',encoding='utf-8') as stream:stream.write(str(os.getpid()))
    start=time.perf_counter()
    sequence=0
    phase='starting'
    rows,timings=[],[]

    def progress(stage,**kw):
        nonlocal sequence,phase
        if (args.output/'CANCEL').exists():raise InterruptedError('frequency_cancelled')
        if time.perf_counter()-start>600:raise TimeoutError('frequency_deadline')
        phase=stage
        sequence+=1
        e=dict(stage=stage,sequence=sequence,at_utc=datetime.now(timezone.utc).isoformat(),pid=os.getpid(),
               elapsed_seconds=round(time.perf_counter()-start,3),**kw)
        with (args.output/'events.jsonl').open('a',encoding='utf-8') as stream:stream.write(json.dumps(e)+'\n')
        source.save(args.output/'progress.json',e)
        (args.output/'PROGRESS.md').write_text('# US500 frequency audit\n\n'+json.dumps(e,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(e),flush=True)

    try:
        for year in (2022,2023,2024):
            at=time.perf_counter()
            sessions,pairs,admission=source.load_year(args.data_root/str(year),year,progress)
            prepared=parent.prepare(sessions,pairs,lambda stage,**kw:progress(stage,year=year,**kw))
            source.save(args.output/f'input-{year}.json',admission)
            timings.append(dict(year=year,phase='source_and_prepare',seconds=time.perf_counter()-at))
            at=time.perf_counter()
            normal=sum(len(times)==390 for times in sessions.values())
            for probe in audit.PROBES:
                progress('counting',year=year,probe=probe['id'])
                result=audit.audit(prepared,pairs,probe)
                if probe['id']=='FP00':
                    config=dict(lane='A',fast=20,slow=80,k='0.1')
                    original=saved_trace(args.parent_base/f'us500-multiframe-native-v3-review-{year}',year,'R098')
                    if audit.trace(result)!=original or audit.trace(result)!=audit.parent_trace(prepared,config):
                        raise ValueError('frequency_R098_parent_signal_parity')
                source.save(args.output/f'{year}-{probe["id"]}.json',result)
                rows.append(dict(year=year,probe=probe['id'],counts=result['counts'],unique_days_by_reason=result['unique_days_by_reason'],scheduled_days=len(sessions),normal_days=normal))
            r120=audit.audit(prepared,pairs,audit.PROBES[0],fast=40,slow=160)
            if audit.trace(r120)!=saved_trace(args.parent_base/f'us500-multiframe-native-v3-review-{year}',year,'R120'):
                raise ValueError('frequency_R120_parent_signal_parity')
            source.save(args.output/f'{year}-R120-audit.json',r120)
            timings.append(dict(year=year,phase='frequency_and_parity',seconds=time.perf_counter()-at))
        combined={}
        for probe in audit.PROBES:
            these=[r for r in rows if r['probe']==probe['id']]
            counts=Counter()
            for row in these:counts.update(row['counts'])
            combined[probe['id']]=dict(counts=dict(counts),annual_exact_fill_available=[r['counts'].get('exact_fill_available',0) for r in these],
                                      signals_per_scheduled_week=counts['exact_fill_available']/(sum(r['scheduled_days'] for r in these)/5))
        primary=combined['FP04']
        eligible=primary['counts'].get('exact_fill_available',0)>=200 and min(primary['annual_exact_fill_available'])>=50
        if len(rows)!=15 or any(source.digest(Path(path))!=sha for path,sha in pins.items()):
            raise ValueError('frequency_census_or_source_drift')
        source.save(args.output/'result.json',dict(status='completed_frequency_only_not_edge',rows=rows,combined=combined,timings=timings,
                    wall_seconds=time.perf_counter()-start,primary_FP04_eligible_for_separate_financial_registration=eligible,
                    new_financial_simulations=0,manifest_sha256=source.digest(args.output/'manifest.json')))
        progress('completed_frequency_only_not_edge',probes=5,annual_cases=15)
    except BaseException as error:
        source.save(args.output/'failure.json',dict(stage=phase,error_type=type(error).__name__,code=str(error),
             locations=[dict(file=Path(x.filename).name,line=x.lineno,function=x.name) for x in traceback.extract_tb(error.__traceback__)]))
        source.save(args.output/'progress.json',dict(stage='failed',failed_phase=phase,error_type=type(error).__name__))
        raise
    finally:
        lock.unlink(missing_ok=True)


if __name__=='__main__':
    main()

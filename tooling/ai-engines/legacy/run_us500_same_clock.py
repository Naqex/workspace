"""TC01 registered cadence then endpoint-only probe over admitted 2022-24 data."""
import argparse
from datetime import datetime, timezone
from fractions import Fraction as F
import json
import os
from pathlib import Path
import time
import traceback

import run_us500_multiframe as source
import us500_opportunities as counts
import us500_same_clock as study


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--protocol',type=Path,required=True)
    parser.add_argument('--protocol-sha256',required=True)
    args=parser.parse_args()
    if source.digest(args.protocol)!=args.protocol_sha256:
        raise ValueError('same_clock_protocol_pin')
    pins=source.source_pins(args.protocol)
    for p in (Path(__file__),Path(study.__file__),Path(counts.__file__),
              Path(__file__).parent/'tests/test_us500_same_clock.py'):
        pins[str(p.resolve())]=source.digest(p)
    args.output.mkdir(parents=True,exist_ok=False)
    source.save(args.output/'manifest.json',dict(schema='us500-same-clock-v1',source_pins=pins,
        years=[2022,2023,2024],candidate='TC01',lookback=20,decision_ny='10:00',
        endpoints_ny=['10:01','10:31'],controls=['BUY','SELL'],costs=['0.25','0.75'],
        unit='hypothetical_1USD_per_index_point_not_account_return',financial_simulations=0))
    snapshot=args.output/'source-snapshot';snapshot.mkdir()
    for i,p in enumerate(pins):
        (snapshot/f'{i:02}-{Path(p).name}').write_bytes(Path(p).read_bytes())
    started,cpu=time.perf_counter(),time.process_time()
    lock=args.output/'controller.lock'
    lock.write_text(str(os.getpid()),encoding='utf-8')
    sequence=0
    def progress(stage,**fields):
        nonlocal sequence
        if (args.output/'CANCEL').exists():
            raise InterruptedError('same_clock_cancel')
        if time.perf_counter()-started>300:
            raise TimeoutError('same_clock_deadline')
        sequence+=1
        ev=dict(stage=stage,sequence=sequence,pid=os.getpid(),at_utc=datetime.now(timezone.utc).isoformat(),
                elapsed_seconds=round(time.perf_counter()-started,3),**fields)
        source.save(args.output/'progress.json',ev)
        with (args.output/'events.jsonl').open('a',encoding='utf-8') as stream:
            stream.write(json.dumps(ev)+'\n')
        (args.output/'PROGRESS.md').write_text('# TC01: same-clock study\n\n'+json.dumps(ev,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(ev),flush=True)
    records,cadence,timing=[],[],[]
    try:
        for year in (2022,2023,2024):
            before=time.perf_counter()
            sessions,pairs,admission=source.load_year(args.data_root/str(year),year,progress)
            source.save(args.output/f'input-{year}.json',admission)
            signals=study.signals(sessions,pairs)
            item=dict(year=year,reasons=signals['reasons'],cadence=counts.cadence(sessions,signals['events'],pairs))
            cadence.append(item)
            source.save(args.output/f'cadence-{year}.json',dict(item,signals=signals))
            records.append((year,pairs,admission,signals))
            timing.append(dict(year=year,phase='load_validate_signal_cadence',seconds=time.perf_counter()-before))
            progress('cadence_checkpoint',year=year,signals=len(signals['events']),years_done=len(records),years_total=3)
        floor=sum(len(r[3]['events']) for r in records)>=200 and all(len(r[3]['events'])>=50 for r in records)
        source.save(args.output/'cadence-gate.json',dict(passed=floor,floor_total=200,floor_annual=50,rows=cadence))
        annual={s:[] for s in ('reference','stress')}
        all_rows={s:{k:[] for k in ('TC01','BUY','SELL')} for s in annual}
        before=time.perf_counter()
        if floor:
            for year,pairs,admission,signals in records:
                progress('component_probe',year=year)
                for scenario,slip in [('reference',F('.25')),('stress',F('.75'))]:
                    groups={}
                    for label in ('TC01','BUY','SELL'):
                        events=[dict(e,side=label) if label!='TC01' else e for e in signals['events']]
                        rows=[study.endpoint(e,pairs,slip) for e in events]
                        groups[label]=study.aggregate(rows)
                        all_rows[scenario][label]+=rows
                        source.save(args.output/f'{year}-{scenario}-{label}.json',dict(year=year,scenario=scenario,
                            code=label,rows=rows,summary=groups[label]))
                    annual[scenario].append(dict(year=year,**groups))
        timing.append(dict(phase='component_and_write',seconds=time.perf_counter()-before))
        for _,_,admission,_ in records:
            if any(source.digest(Path(p))!=sha for p,sha in admission['bindings'].items()):
                raise ValueError('same_clock_data_drift')
        if any(source.digest(Path(p))!=sha for p,sha in pins.items()):
            raise ValueError('same_clock_source_drift')
        result=dict(status=study.priority(annual['stress']) if floor else 'park_cadence_priority_floor',
            cadence=cadence,cadence_gate=floor,annual=annual,
            combined={s:{k:study.aggregate(rows) for k,rows in groups.items()} for s,groups in all_rows.items()} if floor else None,
            timings=timing,wall_seconds=time.perf_counter()-started,cpu_seconds=time.process_time()-cpu,
            manifest_sha256=source.digest(args.output/'manifest.json'),financial_simulations=0,
            scope='endpoint_component_only_no_stop_account_or_prop_qualification')
        source.save(args.output/'result.json',result)
        progress('completed',verdict=result['status'])
        print(json.dumps(dict(status=result['status'],annual=annual),default=str,indent=2),flush=True)
    except BaseException as error:
        source.save(args.output/'failure.json',dict(error_type=type(error).__name__,error=str(error),traceback=traceback.format_exc()))
        source.save(args.output/'progress.json',dict(stage='failed',error_type=type(error).__name__,error=str(error)))
        raise
    finally:
        lock.unlink(missing_ok=True)


if __name__=='__main__':
    main()

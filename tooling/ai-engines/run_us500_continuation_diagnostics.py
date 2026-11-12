"""Finite registered 2022-25 diagnostics, never a new execution/exit strategy."""
import argparse,json,os,time,traceback
from collections import Counter
from datetime import datetime,timezone
from decimal import Decimal as D
from pathlib import Path
import run_us500_recent_screen as r
import us500_continuation_diagnostics as d


def read(p):return json.loads(p.read_text(encoding='utf-8'))
def expect(ok,label):
    if not ok:raise ValueError(label)
def canonical(value):return json.loads(json.dumps(value,default=str))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--protocol',type=Path,required=True);parser.add_argument('--protocol-sha256',required=True)
    a=parser.parse_args();expect(r.core.digest(a.protocol)==a.protocol_sha256,'diagnostic_protocol_binding')
    parent=a.base/'us500-entry-common14-v1';old=a.base/'us500-recent-development-v2'
    source=Path(__file__).resolve().parent;pins=r.core.source_pins(a.protocol)
    for path in (Path(__file__),Path(d.__file__),Path(r.__file__),Path(r.study.__file__),Path(r.counts.__file__),
                 source/'us500_frequency_audit.py',source/'us500_ma_reclaim.py',source/'review_us500_strategy_fit.py',
                 source/'tests/test_us500_continuation_diagnostics.py',parent/'manifest.json',parent/'result.json',
                 a.base/'us500-recent-admitted-v1/source-proof.json'):
        pins[str(path.resolve())]=r.core.digest(path)
    for y in (2022,2023,2024,2025):
        for path in (parent/f'input-{y}.json',old/f'{y}-RS01-signals.json',old/f'{y}-RS02-signals.json'):
            pins[str(path.resolve())]=r.core.digest(path)
        for code in ('BR01','RS02'):
            for scenario in ('reference','stress'):
                for suffix in ('','-review','-seal'):
                    path=parent/f'{y}-{code}-{scenario}{suffix}.json';pins[str(path.resolve())]=r.core.digest(path)
    expect(r.native.nautilus_trader.__version__=='1.231.0','native_runtime_pin')
    a.output.mkdir(exist_ok=False);began=time.perf_counter();cpu=time.process_time();seq=0;done=0
    r.core.save(a.output/'manifest.json',dict(source_pins=pins,years=[2022,2023,2024,2025],recipes=['BR01','RS02'],horizons=[15,30,60],
        new_strategy_versions=0,new_strategy_replays=0,read_2026=False,clean_OOS=False,broker_calls=0,model_calls=0,
        control='same-year NY-slot same-direction nonbreak closed-M15, exclude event day; retrospective descriptive'))
    snap=a.output/'source-snapshot';snap.mkdir()
    for i,name in enumerate(pins):
        if Path(name).suffix in ('.py','.md','.lock'):(snap/f'{i:02}-{Path(name).name}').write_bytes(Path(name).read_bytes())
    lock=a.output/'controller.lock'
    with lock.open('x',encoding='utf-8') as f:f.write(str(os.getpid()))
    summaries=[];paths=[];all_events=[];timings=[];censuses=[];phase='starting';year=None
    def progress(stage,**values):
        nonlocal seq,phase
        if (a.output/'CANCEL').exists():raise InterruptedError('diagnostic_cancelled')
        if time.perf_counter()-began>600:raise TimeoutError('diagnostic_deadline')
        seq+=1;phase=stage;e=dict(stage=stage,sequence=seq,pid=os.getpid(),at_utc=datetime.now(timezone.utc).isoformat(),
            completed_years=done,total_years=4,elapsed_seconds=round(time.perf_counter()-began,3),**values)
        with (a.output/'events.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(e)+'\n')
        r.core.save(a.output/'progress.json',e)
        (a.output/'PROGRESS.md').write_text('# US500 continuation diagnosis\n\n'+json.dumps(e,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(e),flush=True)
    try:
        for year in (2022,2023,2024,2025):
            at=time.perf_counter()
            if year==2025:sessions,pairs,admission=r.recent_year(a.base/'us500-recent-admitted-v1',year,progress)
            else:sessions,pairs,admission=r.core.load_year(a.base/'us500-explicit-source-v1'/str(year),year,progress)
            expect(admission==read(parent/f'input-{year}.json'),'diagnostic_parent_input_drift')
            prepared=r.native.prepare(sessions,pairs,lambda stage,**v:progress(stage,year=year,**v));signals=r.study.signals(prepared)
            for code in ('RS01','RS02'):
                expect(canonical(dict(events=signals[code],cadence=r.counts.cadence(sessions,signals[code],pairs)))==read(old/f'{year}-{code}-signals.json'),'parent_signal_drift')
            # Cash-session slot270 is exactly14:00 NY; use first parent signal only.
            signals['BR01']=[e for e in signals['RS01'] if prepared['snapshots'][e['t']]['slot']<=270]
            timings.append(dict(year=year,phase='source_prepare_signals',seconds=time.perf_counter()-at));at=time.perf_counter()
            control_events=d.control_events(prepared);pools={};control_status=Counter()
            for i,event in enumerate(control_events):
                for horizon in (15,30,60):
                    for side in ('BUY','SELL'):
                        value=d.markout(pairs,prepared['minutes'],event['t'],side,event['atr'],horizon)
                        key=(event['slot'],horizon,side);pool=pools.setdefault(key,d.new_pool())
                        d.pool_add(pool,event,value);control_status[(horizon,side,value['status'])]+=1
                if i%1000==0:progress('control_windows',year=year,done=i,total=len(control_events))
            censuses.append(dict(year=year,candidate_control_bars=len(control_events),outcomes=[dict(horizon=h,side=s,status=st,count=n) for (h,s,st),n in sorted(control_status.items())]))
            timings.append(dict(year=year,phase='control_markouts',seconds=time.perf_counter()-at));at=time.perf_counter();events=[]
            for code in ('BR01','RS02'):
                reference=None
                for scenario in ('reference','stress'):
                    name=f'{year}-{code}-{scenario}';book=read(parent/(name+'.json'));seal=read(parent/(name+'-seal.json'))
                    expect(r.core.digest(parent/(name+'.json'))==seal['book_sha256'] and r.core.digest(parent/(name+'-review.json'))==seal['review_sha256']
                        and r.core.digest(parent/'manifest.json')==seal['manifest_sha256'],'diagnostic_book_seal')
                    checked=r.reviewer.inspect(book,pairs);checked.update(r.check_policy(book,prepared,signals[code]))
                    expect(book['position'] is None,'open_position_diagnostic_scope')
                    cohort=[(t['decision']['t'],t['entry_time'],t['side'],t['decision']['atr']) for t in book['trades']]
                    if reference is None:reference=book;expected_cohort=cohort
                    else:expect(cohort==expected_cohort,'scenario_entry_cohort_drift')
                    trace=[d.excursion(t,pairs,book['slippage']) for t in book['trades']]
                    r.core.save(a.output/(name+'-path.json'),dict(review=checked,trades=trace))
                    known=[t for t in trace if t['status']=='known_prefix_envelope'];losers=[t for t in known if t['loser']]
                    path=dict(year=year,code=code,scenario=scenario,total=len(trace),known=len(known),unknown=len(trace)-len(known),
                        losers=len(losers),losers_after_half_R=sum(t['loser_after_half_R'] for t in losers),
                        mean_favorable_R=sum((t['favorable_R'] for t in known),D(0))/len(known) if known else None,
                        mean_adverse_R=sum((t['adverse_R'] for t in known),D(0))/len(known) if known else None)
                    paths.append(path)
                expect({t['decision']['t'] for t in reference['trades']}=={e['t'] for e in signals[code]},'traded_vs_signal_census')
                for trade in reference['trades']:
                    decision=trade['decision'];stamp=decision['t'];e=prepared['snapshots'][stamp]
                    for horizon in (15,30,60):
                        value=d.markout(pairs,prepared['minutes'],stamp,trade['side'],decision['atr'],horizon)
                        pool=pools.get((e['slot'],horizon,trade['side']),d.new_pool())
                        control=d.contrast(pool,e['day'],value)
                        events.append(dict(year=year,code=code,day=e['day'],slot=e['slot'],side=trade['side'],decision=stamp,horizon=horizon,
                                           atr=decision['atr'],control=control,**value))
                for horizon in (15,30,60):
                    summary=d.summarize([e for e in events if e['code']==code and e['horizon']==horizon]);summary.update(year=year,code=code,horizon=horizon)
                    summaries.append(summary)
            r.core.save(a.output/f'{year}-events.json',events);r.core.save(a.output/f'{year}-control-census.json',censuses[-1]);all_events.extend(events)
            r.core.save(a.output/'completed-summaries.json',summaries);timings.append(dict(year=year,phase='events_paths_review',seconds=time.perf_counter()-at))
            expect(all(r.core.digest(Path(p))==h for p,h in admission['bindings'].items()),'input_drift')
            done+=1;progress('year_completed',year=year,event_markouts=len(events));del pairs,prepared,pools
        pooled=[]
        for code in ('BR01','RS02'):
            for horizon in (15,30,60):
                summary=d.summarize([e for e in all_events if e['code']==code and e['horizon']==horizon]);summary.update(code=code,horizon=horizon);pooled.append(summary)
        expect(all(r.core.digest(Path(p))==h for p,h in pins.items()),'source_drift')
        r.core.save(a.output/'result.json',dict(status='completed_descriptive_diagnostics_not_edge_or_exit_strategy',summaries=summaries,pooled=pooled,
            path_summaries=paths,control_census=censuses,timings=timings,wall_seconds=time.perf_counter()-began,cpu_seconds=time.process_time()-cpu,
            same_agent_separate_arithmetic=True,new_strategy_replays=0,new_strategy_versions=0,read_2026=False))
        progress('completed_descriptive_diagnostics_not_edge_or_exit_strategy')
    except BaseException as error:
        r.core.save(a.output/'failure.json',dict(stage=phase,year=year,type=type(error).__name__,message=str(error),completed_years=done,
            locations=[dict(file=Path(f.filename).name,line=f.lineno,function=f.name) for f in traceback.extract_tb(error.__traceback__)]));raise
    finally:lock.unlink(missing_ok=True)


if __name__=='__main__':main()

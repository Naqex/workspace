"""Registered Gold ledger preparation, cent parity, then conditional rolling cohorts."""
import argparse
from array import array
from bisect import bisect_left
from collections import Counter
from datetime import datetime,timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys
import time
import traceback
from contextlib import contextmanager

from gold_continuous_ledger import (
    START,END,CUTOFF,UTC,Source,read_source,phase_a,evaluate,direct,GoldPrefix,money,
)
from gold_continuous_b1 import ROOT,V2,RAW_SHA,write_json,digest,peak_working_set_bytes


@contextmanager
def output_lock(out):
    lock=out/'RUNNING.lock'
    with lock.open('x',encoding='utf-8') as stream:
        stream.write(json.dumps(dict(pid=__import__('os').getpid(),started_at_utc=datetime.now(timezone.utc).isoformat())))
    try:
        yield
    finally:
        lock.unlink()


def save_source(data,out):
    cache=out/'source-cache';cache.mkdir()
    manifest={}
    for name in ('times','o','h','l','c'):
        path=cache/(name+'.bin')
        with path.open('wb') as stream:getattr(data,name).tofile(stream)
        manifest[path.name]=digest(path)
    write_json(cache/'hours.json',data.hours);manifest['hours.json']=digest(cache/'hours.json')
    write_json(cache/'manifest.json',dict(raw_sha256=RAW_SHA,files=manifest,rows=len(data.times),
        byteorder=sys.byteorder,price_unit='.001',time_unit='UTCseconds',scope_end_exclusive=CUTOFF))


def load_source(out):
    cache=out/'source-cache';m=json.loads((cache/'manifest.json').read_text())
    if m['raw_sha256']!=RAW_SHA or m['byteorder']!=sys.byteorder:raise ValueError('cache source/platform')
    data=Source()
    for name,sha in m['files'].items():
        if digest(cache/name)!=sha:raise ValueError('source cache binding')
    for name in ('times','o','h','l','c'):
        values=array('q' if name=='times' else 'i')
        with (cache/(name+'.bin')).open('rb') as stream:values.fromfile(stream,m['rows'])
        setattr(data,name,values)
    data.hours=json.loads((cache/'hours.json').read_text())
    return data


def parity(a,b):
    for actual,expected in [('cash_net_usd','net_cash_usd'),('floating_usd','floating_usd'),
            ('marked_net_usd','net_marked_equity_usd'),('entries','entries'),('closed','closed_trades'),
            ('financing_debit_usd','funding_debit_usd')]:
        if Decimal(str(a[actual]))!=Decimal(str(b[expected])):raise AssertionError((actual,a[actual],b[expected]))
    for ak,bk in [('point_metrics','point_metrics'),('conditional_envelope','conditional_held_minute_envelope')]:
        for k in ('peak','peak_dd','daily_loss','static_loss'):
            if Decimal(a[ak][k])!=Decimal(b[bk][k]):raise AssertionError((ak,k,a[ak][k],b[bk][k]))
    entries=[d for d in b['decisions'] if d['signal']!='EXIT' and d['status']=='queued'
        and d['time']*1000<=b['mark_time_proxy_msc']]
    if len(entries)!=a['entries']:raise AssertionError('entry decisions')
    for left,right in zip(a['decisions'],entries):
        if (left['at'],left['side'],left['q'])!=(right['time']*1000,right['signal'],int(__import__('decimal').Decimal(right['quantity'])*100)):
            raise AssertionError('entry intent binding')
    for left,right in zip(a['trades'],b['trades']):
        if (left['entry'],left['exit'],left['price_net'])!=(right['entry_time_msc'],right['exit_time_msc'],int(__import__('decimal').Decimal(right['price_net_usd'])*100)):
            raise AssertionError('closed trade binding')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,required=True);ap.add_argument('--raw',type=Path,required=True)
    ap.add_argument('--protocol',type=Path,required=True);ap.add_argument('--reuse-source-cache',action='store_true')
    ap.add_argument('--reuse-ledger-from',type=Path)
    ap.add_argument('--reuse-direct-from',type=Path)
    args=ap.parse_args();out=args.out
    registered=json.loads((out/'registration.json').read_text())
    if digest(args.protocol)!=registered['sha256']:raise ValueError('protocol changed')
    config=json.loads(args.protocol.read_text());began=time.perf_counter();cpu=time.process_time()
    attempt=out/f'attempt-{time.time_ns()}';attempt.mkdir()
    stage='prepare';phase_started=time.perf_counter()
    def progress(label,count):
        write_json(out/'status.json',dict(stage=stage,subphase=label,count=count,pid=__import__('os').getpid(),
            wall_seconds=time.perf_counter()-began,at_utc=datetime.now(timezone.utc).isoformat()))
        if label!='episodes' or count%40==0:print(json.dumps(dict(stage=stage,subphase=label,count=count)),flush=True)
        if (out/'CANCEL').exists():raise RuntimeError('cancel_requested')
        if time.perf_counter()-phase_started>900:raise TimeoutError('900s_phase_deadline')
    guard=output_lock(out)
    guard.__enter__()
    try:
        binding=dict(source={str(p.relative_to(V2)):digest(p) for p in (V2/'trading_workspace_v2').rglob('*.py')},
            workspace={p.name:digest(p) for p in [Path(__file__),Path(__file__).with_name('gold_continuous_ledger.py'),Path(__file__).with_name('gold_continuous_b1.py')]},
            protocol_sha256=digest(args.protocol),raw_sha256=RAW_SHA)
        write_json(attempt/'source-binding.json',binding)
        data=load_source(out) if args.reuse_source_cache else read_source(args.raw,progress=progress)
        if not args.reuse_source_cache:save_source(data,out)
        prepare=time.perf_counter()-phase_started
        stage='phaseA';phase_started=time.perf_counter()
        if args.reuse_ledger_from:
            import ast
            old=args.reuse_ledger_from
            names=('rounded10','floating','StreamSummary','build_episode','phase_a','canonical_frames','boundaries')
            def selected(path):
                return [ast.dump(n,include_attributes=False) for n in ast.parse(path.read_text(encoding='utf-8-sig')).body if getattr(n,'name',None) in names]
            if selected(old/'source-snapshot/gold_continuous_ledger.py')!=selected(Path(__file__).with_name('gold_continuous_ledger.py')):
                raise ValueError('phaseA source changed; cannot reuse ledger')
            ledger=json.loads((old/'ledger.json').read_text())
            ledger['episodes']={int(k):v for k,v in ledger['episodes'].items()}
            write_json(attempt/'ledger-reuse.json',dict(parent=str(old),sha256=digest(old/'ledger.json'),phaseA_selected_AST_equal=True))
        else:
            ledger=phase_a(data,progress=progress)
        phaseA=time.perf_counter()-phase_started;write_json(attempt/'ledger.json',ledger)
        stage='parity';phase_started=time.perf_counter();checks=[]
        def direct_reference(name,start,end,risk,variant='Original'):
            if not args.reuse_direct_from:return direct(data,start,end,risk,variant=variant,progress=progress)
            import ast
            old=args.reuse_direct_from
            names=('DirectGold','PointAwareQualityPath','direct','floating','rounded10','Source')
            def selected(path):
                return [ast.dump(n,include_attributes=False) for n in ast.parse(path.read_text(encoding='utf-8-sig')).body if getattr(n,'name',None) in names]
            if selected(old/'source-snapshot/gold_continuous_ledger.py')!=selected(Path(__file__).with_name('gold_continuous_ledger.py')):
                raise ValueError('direct semantics changed')
            oldbinding=json.loads((old/'source-binding.json').read_text())
            if oldbinding['source']!=binding['source'] or oldbinding['workspace']['gold_continuous_b1.py']!=binding['workspace']['gold_continuous_b1.py']:
                raise ValueError('direct native/input bindings changed')
            seal=json.loads((old/'direct-seal.json').read_text())
            if digest(old/name)!=seal[name]:raise ValueError('direct sealed result changed')
            r=json.loads((old/name).read_text());r['reused_from']=str(old/name)
            return r
        b1=out.parent/'gold-continuous-B1-20261113-v1'
        for risk in (125,200):
            compressed=evaluate(ledger,START,END,risk,challenge=False)
            baseline=json.loads((b1/f'prefix-{risk}.json').read_text())
            write_json(attempt/f'Q1-2010-ledger-{risk}.json',compressed)
            parity(compressed,baseline)
            checks.append(dict(case=f'Q1/2010-{risk}',cent_parity=True,baseline='sealedB1'))
        for start_text in config['validation']['additional_quarters']:
            start=int(datetime.fromisoformat(start_text).replace(tzinfo=UTC).timestamp())
            dt=datetime.fromisoformat(start_text);month=dt.month+3
            end=int(datetime(dt.year+(month>12),(month-1)%12+1,1,tzinfo=UTC).timestamp())
            for risk in (125,200):
                stage=f'parity-{start_text}-{risk}';phase_started=time.perf_counter()
                reference=direct_reference(f'direct-{start_text}-{risk}.json',start,end,risk)
                write_json(attempt/f'direct-{start_text}-{risk}.json',reference)
                t=time.perf_counter();compressed=evaluate(ledger,start,end,risk,challenge=False)
                elapsed=time.perf_counter()-t
                write_json(attempt/f'ledger-{start_text}-{risk}.json',compressed)
                parity(compressed,reference)
                checks.append(dict(case=f'{start_text}-{risk}',cent_parity=True,direct_wall_seconds=reference['wall_seconds'],
                    ledger_wall_seconds=elapsed,baseline='directM1canonicalseed'))
        # One direct BUY-only path checks causal selection rather than a hindsight
        # subtraction of Short trades from a global original ledger.
        stage='parity-buy-only';phase_started=time.perf_counter()
        reference=direct_reference('direct-buy-only-Q1.json',START,END,125,variant='BUY-Only')
        compressed=evaluate(ledger,START,END,125,variant='BUY-Only',challenge=False)
        write_json(attempt/'direct-buy-only-Q1.json',reference);write_json(attempt/'ledger-buy-only-Q1.json',compressed)
        parity(compressed,reference);checks.append(dict(case='BUY-Only-Q1/2010-125',cent_parity=True))
        write_json(attempt/'parity.json',checks)
        stage='phaseB';phase_started=time.perf_counter();cohorts=[]
        costs=config['costs']['swap_debits_per_lot']
        for risk in (125,200):
            for variant in ('Original','BUY-Only'):
                for label,fees in costs.items():
                    for year in range(2010,2025):
                        for month in (1,4,7,10):
                            start=int(datetime(year,month,1,tzinfo=UTC).timestamp())
                            r=evaluate(ledger,start,CUTOFF,risk,variant=variant,costs=fees)
                            r.update(start_utc=datetime.fromtimestamp(start,UTC).isoformat(),risk_usd=risk,variant=variant,cost_scenario=label)
                            r.pop('trades');r.pop('decisions');cohorts.append(r)
                            if len(cohorts)%10==0:progress('cohorts',len(cohorts))
        phaseB=time.perf_counter()-phase_started
        summary=[]
        for risk in (125,200):
            for variant in ('Original','BUY-Only'):
                for label in costs:
                    rows=[r for r in cohorts if (r['risk_usd'],r['variant'],r['cost_scenario'])==(risk,variant,label)]
                    p1=[r for r in rows if len(r['phase_passes'])>=1];p2=[r for r in rows if len(r['phase_passes'])==2]
                    days=sorted((r['phase_passes'][-1]['at']/1000-datetime.fromisoformat(r['start_utc']).timestamp())/86400 for r in p2)
                    median=(days[(len(days)-1)//2]+days[len(days)//2])/2 if days else None
                    def worst(key):
                        return max(float(m[key]) for r in rows for m in [r['conditional_envelope'],*[p['e'] for p in r['completed_phase_metrics']]])
                    summary.append(dict(risk_usd=risk,variant=variant,cost_scenario=label,starts=60,phase1_model_passes=len(p1),
                        two_step_model_passes=len(p2),model_breaches=sum(r['status']=='failed_model_breach' for r in rows),
                        censored=sum(r['status']=='right_censored' for r in rows),median_two_step_days_among_passes=median,
                        worst_daily_loss_usd=worst('daily_loss'),worst_static_loss_usd=worst('static_loss'),worst_peak_dd_usd=worst('peak_dd'),
                        qualified_full_path_passes=0,interpretation='overlapping_descriptive_conditional_M1_model_counts_not_probability_or_certified_survival'))
        result=dict(schema='gold-B2-conditional-rolling-v1',summary=summary,cohorts=cohorts,parity=checks,
            timings=dict(prepare=prepare,phaseA=phaseA,phaseB=phaseB,total=time.perf_counter()-began,cpu=time.process_time()-cpu,
                peak_working_set_bytes=peak_working_set_bytes()),binding=binding,attempt=str(attempt),
            episodes_per_risk={str(k):len(v) for k,v in ledger['episodes'].items()},full_path_qualified=False)
        write_json(attempt/'results.json',result);write_json(out/'completed.json',dict(attempt=str(attempt),result_sha256=digest(attempt/'results.json')))
        progress('completed',len(cohorts))
    except BaseException as exc:
        write_json(attempt/'failure.json',dict(stage=stage,type=type(exc).__name__,message=str(exc),traceback=traceback.format_exc()))
        raise
    finally:
        guard.__exit__(None,None,None)


if __name__=='__main__':main()

"""Frozen setup screen: development/2025 selection, then bounded 2026/history."""
import argparse,bisect,json,os,time,traceback,warnings
import shutil
from datetime import datetime,timezone
from pathlib import Path
from decimal import Decimal as D
import run_us500_multiframe as core
import us500_multiframe as native
import us500_recent_setups as study
import us500_opportunities as counts
import review_us500_multiframe as reviewer
from run_us500_channel_history import historical_year


def recent_year(root,year,progress):
    if year not in (2025,2026):raise ValueError('registered_recent_year_only')
    proofpath=root/'source-proof.json';proof=json.loads(proofpath.read_text(encoding='utf-8'))
    if proof['status']!='raw_native_paired_prices_verified' or proof['grant']['id']!='us500-recent-discovery-20261112':
        raise ValueError('recent_source_admission_required')
    calpath=root/f'nyse-{year}.json'
    if core.digest(calpath)!=proof['calendars'][str(year)]:raise ValueError('recent_calendar_binding')
    sessions=core.cash_sessions(json.loads(calpath.read_text(encoding='utf-8')))
    if year==2026:sessions={d:v for d,v in sessions.items() if d<='2026-11-11'}
    need={t for ts in sessions.values() for t in ts}; sides=[]
    bindings={str(proofpath.resolve()):core.digest(proofpath),str(calpath.resolve()):core.digest(calpath)}
    lower=int(datetime(year,1,1,tzinfo=timezone.utc).timestamp()*1000)
    upper=int(datetime(2026,11,12,tzinfo=timezone.utc).timestamp()*1000) if year==2026 else int(datetime(year+1,1,1,tzinfo=timezone.utc).timestamp()*1000)
    for side in ('bid','ask'):
        progress('loading_recent',year=year,side=side);rows=[]
        for rec in proof['rows']:
            if rec['year']!=year or rec['side']!=side:continue
            p=root/rec['path']
            if core.digest(p)!=rec['sha256']:raise ValueError('recent_canonical_binding')
            data=json.loads(p.read_text(encoding='utf-8'));core.validate_rows(data,lower,upper,.001)
            rows.extend(r for r in data if r['timestamp'] in need);bindings[str(p.resolve())]=rec['sha256']
        core.validate_rows(rows,lower,upper,.001);sides.append(rows)
    core.paired_spreads(*sides);pairs={b['timestamp']:(b,a) for b,a in zip(*sides)}
    return sessions,pairs,dict(bindings=bindings,expected_minutes=len(need),observed_minutes=len(pairs),missing_minutes=len(need)-len(pairs))


def check_policy(book,prepared,signals):
    mapping={e['t']:e for e in signals};times=sorted(prepared['snapshots']);code=book['config']['id']
    for trade in book['trades']:
        d=trade['decision'];s=mapping.get(d['t'])
        if not s or s['side']!=trade['side'] or D(str(s['atr']))!=D(str(d['atr'])):raise ValueError('recent_trade_signal_binding')
        expected=None
        for t in times[bisect.bisect_right(times,trade['entry_time']):]:
            if (t+native.M)*1000000+1>trade['exit_ns']:break
            e=prepared['snapshots'][t];m=e['m15']
            restored=(code=='RS07' and m and 20 in m['means'] and
                (1 if trade['side']=='BUY' else -1)*(m['close']-m['means'][20])>=0)
            if e['slot']==360 or restored:expected=(t+native.M,'mean_reached' if restored else 'session_flat');break
        if trade['reason']!='stop':
            if expected is None or (expected[0]*1000000+1,expected[1])!=(trade['exit_ns'],trade['reason']):
                if not trade['unresolved']:raise ValueError('recent_first_scheduled_exit_clock')
    return dict(signal_binding=True,closed_bar_exit_checked=True,independent_human_or_feed=False)


def select(rows):
    eligible=[]
    for code in study.ECONOMIC:
        matches=[r for r in rows if r['code']==code and r['year']==2025 and r['scenario']=='stress']
        if len(matches)!=1:raise ValueError('recent_selection_census')
        r=matches[0];net=r['metrics']['sides']['combined']['net_usd']
        if net is not None and r['metrics']['rejections']==0:
            dev=[x['metrics']['sides']['combined']['net_usd'] for x in rows
                 if x['code']==code and x['year'] in (2022,2023,2024) and x['scenario']=='stress']
            devpositive=len(dev)==3 and all(x is not None for x in dev) and sum((D(x) for x in dev),D(0))>0
            eligible.append((devpositive,D(net),code))
    if any(v[0] for v in eligible):eligible=[v for v in eligible if v[0]]
    chosen=[code for _,net,code in sorted(eligible,key=lambda x:(-x[1],x[2]))[:2]]
    return dict(codes=chosen or ['RS01','RS07'],diagnostics_only=not chosen,
                basis='2025 full-known stress net descending; fixed RS01/RS07 if no eligible full-known book')


def recovery(root,contract_path,pins,stage,codes,years):
    """Explicit reviewed source migration, never accept arbitrary pin drift."""
    contract=json.loads(contract_path.read_text(encoding='utf-8'))
    path=root/'manifest.json';old=json.loads(path.read_text(encoding='utf-8'))
    if core.digest(path)!=contract['parent_manifest_sha256']:raise ValueError('reuse_manifest_binding')
    if (old['stage'],old['codes'],old['years'])!=(stage,codes,list(years)):raise ValueError('reuse_scope_drift')
    oldpins=old['source_pins']
    delta={n:dict(old=oldpins.get(n),new=pins.get(n)) for n in oldpins.keys()|pins.keys() if oldpins.get(n)!=pins.get(n)}
    if delta!=contract['source_deltas']:raise ValueError('reuse_unreviewed_source_drift')
    if contract['reason']!='trace_kind_only_no_economic_rule_change':raise ValueError('reuse_economic_change')
    completed=json.loads((root/'completed-books.json').read_text(encoding='utf-8'))
    if core.digest(root/'completed-books.json')!=contract['completed_sha256']:raise ValueError('reuse_completed_binding')
    records={(r['year'],r['code'],r['scenario']):r for r in completed}
    if len(records)!=len(completed):raise ValueError('reuse_duplicate_books')
    return records


def reuse_book(root,name,row,admission,signal_record):
    year=row['year'];code=row['code'];path=root/(name+'.json')
    seal=json.loads((root/(name+'-seal.json')).read_text(encoding='utf-8'))
    if (core.digest(path)!=seal['book_sha256'] or core.digest(root/(name+'-review.json'))!=seal['review_sha256']
        or core.digest(root/'manifest.json')!=seal['manifest_sha256']):raise ValueError('reuse_seal_drift')
    if json.loads((root/f'input-{year}.json').read_text(encoding='utf-8'))!=admission:raise ValueError('reuse_input_drift')
    canonical=json.loads(json.dumps(signal_record,default=str))
    if json.loads((root/f'{year}-{code}-signals.json').read_text(encoding='utf-8'))!=canonical:
        raise ValueError('reuse_signal_drift')
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--protocol',type=Path,required=True);p.add_argument('--protocol-sha256',required=True)
    p.add_argument('--stage',choices=('development','confirm','history'),required=True)
    p.add_argument('--selection',type=Path)
    p.add_argument('--reuse-completed-from',type=Path);p.add_argument('--reuse-contract',type=Path)
    a=p.parse_args()
    if core.digest(a.protocol)!=a.protocol_sha256:raise ValueError('recent_protocol_binding')
    root=Path(__file__).resolve().parent;pins=core.source_pins(a.protocol)
    for f in (Path(__file__),Path(study.__file__),Path(counts.__file__),root/'us500_ma_reclaim.py',root/'us500_frequency_audit.py',
              root/'review_us500_strategy_fit.py',root/'tests/test_us500_recent_setups.py',root/'run_us500_channel_history.py'):
        pins[str(f.resolve())]=core.digest(f)
    pins[str((root/'tests/test_run_us500_recent_screen.py').resolve())]=core.digest(root/'tests/test_run_us500_recent_screen.py')
    proof=a.base/'us500-recent-admitted-v1/source-proof.json';pins[str(proof.resolve())]=core.digest(proof)
    selection=None
    if a.stage!='development':
        if not a.selection:raise ValueError('frozen_selection_required')
        selection=json.loads(a.selection.read_text(encoding='utf-8'));pins[str(a.selection.resolve())]=core.digest(a.selection)
        parent=Path(selection['parent_result']);pins[str(parent.resolve())]=core.digest(parent)
        if pins[str(parent.resolve())]!=selection['parent_result_sha256']:raise ValueError('selection_parent_binding')
    codes=list(study.ECONOMIC) if selection is None else selection['codes']
    years=(2022,2023,2024,2025) if a.stage=='development' else (2026,) if a.stage=='confirm' else (2016,2020,2021)
    reused={}
    if a.reuse_completed_from:
        if not a.reuse_contract:raise ValueError('reviewed_reuse_contract_required')
        reused=recovery(a.reuse_completed_from,a.reuse_contract,pins,a.stage,codes,years)
    elif a.reuse_contract:raise ValueError('reuse_parent_required')
    a.output.mkdir(exist_ok=False)
    core.save(a.output/'manifest.json',dict(stage=a.stage,codes=codes,years=years,source_pins=pins,
        exposure='development_or_current_study_validation_not_certified_pristine_holdout',broker_calls=0,model_calls=0,
        recovery=None if not reused else dict(parent=str(a.reuse_completed_from.resolve()),
            contract=str(a.reuse_contract.resolve()),contract_sha256=core.digest(a.reuse_contract))))
    snap=a.output/'source-snapshot';snap.mkdir()
    for i,n in enumerate(pins):
        if Path(n).suffix in ('.py','.md','.lock'):(snap/f'{i:02}-{Path(n).name}').write_bytes(Path(n).read_bytes())
    lock=a.output/'controller.lock'
    with lock.open('x',encoding='utf-8') as f:f.write(str(os.getpid()))
    began=time.perf_counter();seq=0;phase='starting';rows=[];cadence=[];timings=[]
    def progress(stage,**values):
        nonlocal seq,phase
        if (a.output/'CANCEL').exists():raise InterruptedError('recent_screen_cancelled')
        if time.perf_counter()-began>1800:raise TimeoutError('recent_screen_deadline')
        phase=stage;seq+=1
        e=dict(stage=stage,sequence=seq,pid=os.getpid(),at_utc=datetime.now(timezone.utc).isoformat(),
            elapsed_seconds=round(time.perf_counter()-began,2),completed_books=len(rows),**values)
        with (a.output/'events.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(e)+'\n')
        core.save(a.output/'progress.json',e);(a.output/'PROGRESS.md').write_text('# US500 recent screen\n\n'+json.dumps(e,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(e),flush=True)
    try:
        warnings.filterwarnings('ignore',message='Timestamp.utcnow is deprecated.*')
        for year in years:
            start=time.perf_counter()
            if year>=2025:sessions,pairs,admission=recent_year(a.base/'us500-recent-admitted-v1',year,progress)
            elif year>=2022:sessions,pairs,admission=core.load_year(a.base/'us500-explicit-source-v1'/str(year),year,progress)
            else:
                old=a.base/'us500-long-explicit-source-v1';receipt=json.loads((old/'result.json').read_text(encoding='utf-8'))
                sessions,pairs,admission=historical_year(old/str(year),next(e for e in receipt['new_years'] if e['year']==year),progress)
            prepared=native.prepare(sessions,pairs,lambda stage,**v:progress(stage,year=year,**v))
            sigs=study.signals(prepared);core.save(a.output/f'input-{year}.json',admission)
            reportcodes=study.CODES if a.stage=='development' else codes
            for code in reportcodes:
                c=counts.cadence(sessions,sigs[code],pairs);cadence.append(dict(year=year,code=code,metrics=c))
                core.save(a.output/f'{year}-{code}-signals.json',dict(events=sigs[code],cadence=c))
            quotes=native.quote_data(pairs)
            timings.append(dict(year=year,phase='source_prepare_signals_quotes',seconds=time.perf_counter()-start))
            for code in codes:
                mapping={e['t']:e for e in sigs[code]}
                scenarios=[('reference','.25',False),('stress','.75',False)]
                if code==codes[0]:scenarios.append(('null','.25',True))
                for scenario,slip,null in scenarios:
                    name=f'{year}-{code}-{scenario}';f=a.output/(name+'.json');prior=reused.get((year,code,scenario))
                    progress('rechecking_saved_book' if prior else 'starting_book',year=year,code=code,scenario=scenario);start=time.perf_counter()
                    if prior:
                        book=reuse_book(a.reuse_completed_from,name,prior,admission,
                            dict(events=sigs[code],cadence=counts.cadence(sessions,sigs[code],pairs)))
                        if book['config']!={'id':code} or D(book['slippage'])!=D(slip) or book['null']!=null:
                            raise ValueError('reuse_book_identity')
                        shutil.copyfile(a.reuse_completed_from/(name+'.json'),f)
                    else:
                        book=native.execute(dict(id=code),prepared,pairs,quotes,slip,
                            lambda stage,**v:progress(stage,year=year,code=code,scenario=scenario,**v),
                            policy_factory=lambda config,m=mapping:study.FrozenPolicy(config,m),null=null)
                        core.save(f,book)
                    durable=json.loads(f.read_text(encoding='utf-8'));checked=reviewer.inspect(durable,pairs)
                    if null and (durable['trades'] or D(str(durable['decimal_cash']))!=10000 or durable['position'] is not None):
                        raise ValueError('recent_null_control_nonzero')
                    checked.update(check_policy(durable,prepared,sigs[code]));core.save(a.output/(name+'-review.json'),checked)
                    metric=reviewer.metrics(durable);row=dict(year=year,code=code,scenario=scenario,metrics=metric)
                    if prior and row!=prior:raise ValueError('reuse_metric_drift')
                    rows.append(row);core.save(a.output/'completed-books.json',rows)
                    core.save(a.output/(name+'-seal.json'),dict(book_sha256=core.digest(f),review_sha256=core.digest(a.output/(name+'-review.json')),
                        manifest_sha256=core.digest(a.output/'manifest.json')))
                    timings.append(dict(year=year,code=code,scenario=scenario,phase='reused_and_reviewed' if prior else 'native_and_review',seconds=time.perf_counter()-start))
            del pairs,prepared,quotes
            if any(core.digest(Path(n))!=s for n,s in admission['bindings'].items()):raise ValueError('recent_input_drift')
        if any(core.digest(Path(n))!=s for n,s in pins.items()):raise ValueError('recent_source_pin_drift')
        if a.reuse_contract and core.digest(a.reuse_contract)!=json.loads((a.output/'manifest.json').read_text(encoding='utf-8'))['recovery']['contract_sha256']:
            raise ValueError('reuse_contract_drift')
        result=a.output/'result.json';core.save(result,dict(status='completed_native_screen_not_challenge_qualified',stage=a.stage,
            rows=rows,cadence=cadence,timings=timings,wall_seconds=time.perf_counter()-began,selection=selection))
        if a.stage=='development':
            chosen=select(rows);chosen.update(parent_result=str(result.resolve()),parent_result_sha256=core.digest(result))
            core.save(a.output/'selection.json',chosen)
        progress('completed_native_screen_not_challenge_qualified')
    except BaseException as error:
        core.save(a.output/'failure.json',dict(stage=phase,error_type=type(error).__name__,code=str(error),completed_books=len(rows),
            locations=[dict(file=Path(x.filename).name,line=x.lineno,function=x.name) for x in traceback.extract_tb(error.__traceback__)]))
        raise
    finally:lock.unlink(missing_ok=True)


if __name__=='__main__':main()

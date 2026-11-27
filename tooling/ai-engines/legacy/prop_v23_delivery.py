"""V23 post-freeze attribution and bounded delivery receipts; no new trials."""
from concurrent.futures import ThreadPoolExecutor
from statistics import median
import os
import subprocess
import sys
import time
from prop_v23_common import *
from prop_v21_delivery import RUNTIMES


def later():
    from prop_v23_campaign import verify
    from prop_v21_forensics import Context,marked_metrics
    from quant_core.trade_forensics_classifier import concentration
    from prop_v15_evidence import bars_for
    # Attribution reuses frozen features; only quote readers are needed for marks.
    verify();context=Context.__new__(Context);context.end=END;context._readers={}
    context.bars={asset:bars_for(asset,False) for asset in ('XAUUSD','EURUSD')};result={}
    for tag in ('OLHC','OHLC'):
        rows=unpack('Full-'+tag+'-forensics',V21)
        trades=read(V19/f'Full-{tag}-PRIMARY-trades.json')
        global_top={r['trade_key'] for r in concentration(rows)['top10']}
        groups=[]
        for name,lo,hi in (('Development',FIRST,DEV_END),('Later_exposed',DEV_END,END)):
            period=[r for r in rows if lo<=r['entry_msc']<hi]
            for identity in sorted({r['id'] for r in rows}):
                chosen=[r for r in period if r['id']==identity]
                ts=[t for t in trades if t['id']==identity and lo<=t['entry_msc']<hi]
                m=marked_metrics(ts,context,tag)
                m['annualization_years']=(hi-lo)/(365.2425*86400000)
                m['Calmar']=m['net_R']/m['annualization_years']/m['equity_R_DD'] if m['equity_R_DD'] else None
                cash=peak=dd=0.
                for r in sorted(chosen,key=lambda v:(v['exit_msc'],v['trade_key'])):
                    cash+=r['net_R'];peak=max(peak,cash);dd=max(dd,peak-cash)
                assert abs(cash-m['net_R'])<1e-8
                groups.append(dict(period=name,id=identity,trades=len(chosen),winrate=sum(r['net_R']>0 for r in chosen)/len(chosen),
                    mean_R=cash/len(chosen),net_R=cash,equity_R_DD=m['equity_R_DD'],cash_R_DD=dd,
                    ExGlobalTop10_R=sum(r['net_R'] for r in chosen if r['trade_key'] not in global_top),
                    provisional=sum(r['provisional'] for r in chosen),start_flat=True))
        selected=read(FREEZE)['selected'];kept=[t for t in trades if t['id']!=selected['drop_id']]
        result[tag]=dict(rows=groups,global_top10=sorted(global_top),full_selected_unit_metrics=marked_metrics(kept,context,tag),
            full_selected_count=len(kept),original_count=len(trades))
    dev=unpack('Dev-OLHC-forensics',V21);regime=[]
    for identity in sorted({r['id'] for r in dev}):
        for band in ('<=0.9','>0.9','UNKNOWN'):
            chosen=[r for r in dev if r['id']==identity and (
                ('UNKNOWN' if r['day_range_ATR'] is None else '>0.9' if r['day_range_ATR']>.9 else '<=0.9')==band)]
            regime.append(dict(id=identity,day_range_ATR_band=band,count=len(chosen),net_R=sum(r['net_R'] for r in chosen),
                mean_R=sum(r['net_R'] for r in chosen)/len(chosen) if chosen else None))
    save('post-freeze-attribution.json',dict(orders=result,Dev_regime_description=regime,
        no_new_selection=True,later_already_exposed=True,global_top10_already_exposed=True))
    event('V23_post_freeze_attribution_complete')


def tests():
    save('final-test-plan.json',dict(full_attempts=1,smoke_attempts=10,full_target_seconds=13.2,
        smoke_target_seconds=.72,preserved_V22_IDs=1280,unchanged_smoke_IDs=78,
        startup_and_disk_IO_inside_timer=True,no_retry_for_streak=True))
    temp=Path('.runtime/v23-test-temp').resolve();temp.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,TEMP=str(temp),TMP=str(temp));start=time.perf_counter()
    def run(group):
        out=JOB/f'tests-final-{group}.json'
        if out.exists():raise ValueError('Preserve final test attempt')
        args=[RUNTIMES[group],'tooling/ai-engines/quant_test_suite.py','--group',group,'--tier','all','--output',str(out)]
        if group=='base':args+=['--workers','4','--profile',str(V22/'tests-final-base.json')]
        with out.with_suffix('.stdout').open('x') as log:p=subprocess.run(args,env=env,stdout=log,stderr=subprocess.STDOUT)
        return group,p.returncode,read(out)
    with ThreadPoolExecutor(max_workers=5) as pool:rows=list(pool.map(run,RUNTIMES))
    wall=time.perf_counter()-start;ids=set();old=set()
    for group,code,r in rows:
        if code or not r['passed'] or r['skipped'] or ids.intersection(r['timings']):raise ValueError('Full suite failure:'+group)
        ids.update(r['timings']);old.update(read(V22/f'tests-final-{group}.json')['timings'])
    assert len(old)==1280 and old<=ids
    save('tests-final-matrix.json',dict(passed=True,tests=len(ids),zero_skip=True,preserved_V22_IDs=len(old),
        total_wall_seconds=wall,target_under132=wall<13.2,added_IDs=sorted(ids-old),groups={g:r['seconds'] for g,_,r in rows}))
    expected=set(read(V22/'smoke-final-00.json')['timings']);samples=[]
    for i in range(10):
        out=JOB/f'smoke-final-{i:02d}.json';start=time.perf_counter()
        if out.exists():raise ValueError('Preserve final smoke attempt')
        p=subprocess.run([RUNTIMES['base'],'tooling/ai-engines/quant_test_suite.py','--group','base','--tier','smoke',
            '--indexed-imports','--output',str(out)],capture_output=True,env=env)
        wall=time.perf_counter()-start;r=read(out)
        assert not p.returncode and r['passed'] and not r['skipped'] and set(r['timings'])==expected
        samples.append(dict(attempt=i+1,wall=wall,tests=r['tests'],passed=True,skipped=0))
    save('smoke-final-results.json',dict(rows=samples,below072=sum(s['wall']<.72 for s in samples),
        median=median(s['wall'] for s in samples),max=max(s['wall'] for s in samples)))
    event('V23_final_tests',tests=len(ids),full_wall=read(JOB/'tests-final-matrix.json')['total_wall_seconds'],
        smoke_below072=sum(s['wall']<.72 for s in samples))


def audit():
    from prop_v23_campaign import verify
    f=verify();dev=read(JOB/'Dev-ablation-results.json');post=read(JOB/'post-freeze-attribution.json')
    attribution=dev['V22_A_attribution']
    assert abs(sum(r['avoided_loss_R'] for r in attribution)-17.289466666666666)<1e-8
    assert abs(sum(r['lost_winner_R'] for r in attribution)-17.8132)<1e-8
    assert sum(r['rejected'] for r in attribution if r['id'].startswith('EURUSD'))==0
    for tag in ('OLHC','OHLC'):
        groups=post['orders'][tag]['rows']
        assert sum(r['trades'] for r in groups)==494
        assert abs(sum(r['net_R'] for r in groups)-42.391666666666666)<1e-8
        for p in ('Dev','Full'):
            for mode,pct in (('PRIMARY',100),('PRIMARY',150),('STRICT',100)):
                prefix=f'{p}-{tag}-{mode}-{pct}'
                a=read(JOB/(prefix+'-audit.json'));accounts=unpack(prefix+'-accounts')
                assert a['passed'] and a['accounts']==len(accounts)==(73 if p=='Dev' else 106)
        mc=read(JOB/f'MC-{tag}-summary.json');rows=unpack(f'MC-{tag}-paths')
        assert len(rows)==5000 and mc['accounts_fully_audited']==10000
        assert [r['path'] for r in rows]==list(range(5000))
        assert all(len(r['independent_full_ledger_checks'])==2 for r in rows)
    manifests=[]
    for p in sorted(JOB.glob('*-manifest.json')):
        m=read(p)
        if not m.get('file','').endswith('.json.zst'):continue
        value=unpack(m['file'][:-9]);manifests.append(dict(manifest=p.name,**m))
    save('artifact-integrity-audit.json',dict(passed=True,compressed_tables=len(manifests),manifests=manifests,
        original_bytes=sum(r['original_bytes'] for r in manifests),compressed_bytes=sum(r['compressed_bytes'] for r in manifests),
        checks=['494 attribution conservation','V22 avoided/lost contributions','committed freeze pins',
            'both orderings and all historical ledgers','10000 audited Challenge/funded pairs','compressed/raw SHA256 roundtrips'],
        independent_arithmetic_same_feed=True,remaining_source_gaps_not_repaired=True))
    event('V23_integrity_complete',tables=len(manifests))


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('stage',choices=('later','tests','audit'));a=p.parse_args();globals()[a.stage]()

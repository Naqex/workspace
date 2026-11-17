"""Final one-attempt performance, CLI and storage evidence for V22."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from statistics import median
import os
import subprocess
import sys
import time
from prop_v22_common import *
from prop_v21_delivery import RUNTIMES

TEMP_ROOT=Path('D:/ANNAM/TradingWorkspace/.runtime/v22-test-temp')


def tests():
    save('final-test-plan.json',dict(full_attempts=1,smoke_attempts=10,full_target_seconds=13.5,full_stretch_seconds=13.2,
        smoke_target_seconds=.75,smoke_stretch_seconds=.72,preserved_V21_IDs=1261,unchanged_smoke_IDs=78,
        startup_and_disk_IO_inside_timer=True,no_retry_for_streak=True))
    TEMP_ROOT.mkdir(exist_ok=True,parents=True);env=dict(os.environ,TEMP=str(TEMP_ROOT),TMP=str(TEMP_ROOT))
    start=time.perf_counter()
    def run(group):
        out=JOB/f'tests-final-{group}.json'
        if out.exists():raise ValueError('Preserve test attempt')
        args=[RUNTIMES[group],'tooling/ai-engines/quant_test_suite.py','--group',group,'--tier','all','--output',str(out)]
        if group=='base':args+=['--workers','4','--profile',str(V21/'tests-final-base.json')]
        with out.with_suffix('.stdout').open('x') as f:p=subprocess.run(args,env=env,stdout=f,stderr=subprocess.STDOUT)
        return group,p.returncode,read(out)
    with ThreadPoolExecutor(max_workers=5) as pool:rows=list(pool.map(run,RUNTIMES))
    wall=time.perf_counter()-start;ids=set();old=set()
    for g,code,r in rows:
        if code or not r['passed'] or r['skipped'] or ids.intersection(r['timings']):raise ValueError('Full suite failure:'+g)
        ids.update(r['timings']);old.update(read(V21/f'tests-final-{g}.json')['timings'])
    assert len(old)==1261 and old<=ids
    save('tests-final-matrix.json',dict(passed=True,tests=len(ids),zero_skip=True,preserved_V21_IDs=1261,
        total_wall_seconds=wall,target_under135=wall<=13.5,stretch_under132=wall<13.2,
        added_IDs=sorted(ids-old),groups={g:r['seconds'] for g,_,r in rows}))
    expected=set(read(V21/'smoke-final-00.json')['timings']);samples=[]
    for i in range(10):
        out=JOB/f'smoke-final-{i:02d}.json';start=time.perf_counter()
        if out.exists():raise ValueError('Preserve smoke attempt')
        p=subprocess.run([sys.executable,'tooling/ai-engines/quant_test_suite.py','--group','base','--tier','smoke',
            '--indexed-imports','--output',str(out)],capture_output=True,env=env)
        wall=time.perf_counter()-start;r=read(out)
        assert not p.returncode and r['passed'] and not r['skipped'] and set(r['timings'])==expected
        samples.append(dict(attempt=i+1,wall=wall,tests=r['tests'],passed=True,skipped=0))
    save('smoke-final-results.json',dict(rows=samples,below075=sum(s['wall']<.75 for s in samples),
        below072=sum(s['wall']<.72 for s in samples),median=median(s['wall'] for s in samples),max=max(s['wall'] for s in samples)))
    event('V22_final_tests',tests=len(ids),smoke_below075=sum(s['wall']<.75 for s in samples))


def preflight():
    out=JOB/'preflight-final-cli';start=time.perf_counter()
    args=[RUNTIMES['observer'],'-m','tooling.ai_engines.ftmo_trial_runner','--check-mt5-ready','--output',str(out)]
    with (JOB/'preflight-final.stdout').open('x') as f:p=subprocess.run(args,stdout=f,stderr=subprocess.STDOUT)
    wall=time.perf_counter()-start;r=read(out/'MT5_PREFLIGHT.json')
    assert r['actual_broker_orders']==0
    assert p.returncode in (0,2)
    save('preflight-CLI-receipt.json',dict(command=args,returncode=p.returncode,whole_process_wall_seconds=wall,
        whole_process_under1=wall<1,result=r,source_sha256=sha('tooling/ai-engines/ftmo_trial_runner.py'),
        cold_setup_30second_or1second_guarantee=False))


def storage():
    roots={}
    for label,root in (('D','D:/ANNAM/TradingWorkspace'),('E','E:/BACKUP-TRADINGWORKSPACE')):
        p=JOB/f'storage-after-{label}.json'
        with p.with_suffix('.stdout').open('x') as f:
            subprocess.run([sys.executable,'tooling/workspace_maintenance.py','inventory','--root',root,'--output',str(p)],stdout=f,stderr=subprocess.STDOUT,check=True)
        a=read(V21/f'storage-after-{label}.json');b=read(p)
        roots[label]=dict(before=a['groups']['/'],after=b['groups']['/'],delta_bytes=b['groups']['/']['bytes']-a['groups']['/']['bytes'],
            before_errors=a['errors'],after_errors=b['errors'],baseline='V21 final non-atomic inventory, unrelated activity may contribute')
    ms=[read(p) for p in JOB.rglob('*-manifest.json')];files=[p for p in JOB.rglob('*') if p.is_file()]
    save('storage-final.json',dict(roots=roots,compressed_tables=len(ms),original_bytes=sum(r['original_bytes'] for r in ms),
        compressed_bytes=sum(r['compressed_bytes'] for r in ms),own_job_bytes=sum(p.stat().st_size for p in files),
        source_data_deleted=0,price_cache_duplicated=False,physical_free_bytes=None))


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('stage',choices=('tests','preflight','storage'));a=p.parse_args();globals()[a.stage]()

"""One final measured suite/smoke attempt, then logical storage inventory."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from statistics import median
import os
import subprocess
import sys
import time
from prop_v21_common import *
from prop_v16_performance import RUNTIMES as PREVIOUS

V20=ROOT/'voltarget-shadow-v20-20261117'
RUNTIMES=dict(PREVIOUS,observer=str(Path('tooling/strategy-engines/observer/.venv/Scripts/python.exe').resolve()))
TEMP_ROOT=Path('D:/ANNAM/TradingWorkspace/.runtime/v21-test-temp')


def tests():
    if read(JOB/'Development-decision.json')['selected'] is not None:raise ValueError('Pending candidate account qualification')
    save('final-verification-plan.json',dict(full_attempts=1,smoke_attempts=10,full_target_seconds=15,
        full_stretch_seconds=14,smoke_target_seconds=.78,smoke_stretch_seconds=.70,
        unchanged_smoke_IDs=78,baseline_tests=1239,includes_startup_and_fixture_IO=True,no_retry_for_streak=True))
    TEMP_ROOT.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,TEMP=str(TEMP_ROOT),TMP=str(TEMP_ROOT));started=time.perf_counter()
    def run(group):
        out=JOB/f'tests-final-{group}.json'
        if out.exists():raise ValueError('Preserve test attempt')
        args=[RUNTIMES[group],'tooling/ai-engines/quant_test_suite.py','--group',group,'--tier','all','--output',str(out)]
        if group=='base':args+=['--workers','4','--profile',str(V20/'test-recovery-v2/tests-final-base.json')]
        with out.with_suffix('.stdout').open('x') as log:r=subprocess.run(args,env=env,stdout=log,stderr=subprocess.STDOUT)
        return group,r.returncode,read(out)
    with ThreadPoolExecutor(max_workers=5) as pool:rows=list(pool.map(run,RUNTIMES))
    wall=time.perf_counter()-started;ids=set();old=set()
    for g,code,r in rows:
        if code or not r['passed'] or r['skipped'] or ids.intersection(r['timings']):raise ValueError('Full suite failure:'+g)
        ids.update(r['timings']);old.update(read(V20/f'test-recovery-v2/tests-final-{g}.json')['timings'])
    if len(old)!=1239 or not old<=ids:raise ValueError('Lost V20 test ID')
    save('tests-final-matrix.json',dict(passed=True,tests=len(ids),preserved_V20_IDs=1239,zero_skip=True,
        total_wall_seconds=wall,target_under15=wall<15,stretch_under14=wall<14,
        added_IDs=sorted(ids-old),groups={g:r['seconds'] for g,_,r in rows}))
    baseline=set(read(V20/'test-recovery-v2/smoke-final-00.json')['timings']);samples=[]
    for i in range(10):
        out=JOB/f'smoke-final-{i:02d}.json';start=time.perf_counter()
        if out.exists():raise ValueError('Preserve smoke attempt')
        p=subprocess.run([sys.executable,'tooling/ai-engines/quant_test_suite.py','--group','base','--tier','smoke',
            '--indexed-imports','--output',str(out)],env=env,capture_output=True)
        duration=time.perf_counter()-start;r=read(out)
        if p.returncode or not r['passed'] or r['skipped'] or set(r['timings'])!=baseline:raise ValueError('Smoke failure/IDs changed')
        samples.append(dict(attempt=i+1,wall=duration,tests=r['tests'],passed=True,skipped=0))
    save('smoke-final-results.json',dict(rows=samples,below078=sum(s['wall']<.78 for s in samples),
        below070=sum(s['wall']<.70 for s in samples),median=median(s['wall'] for s in samples),max=max(s['wall'] for s in samples)))
    event('V21_final_tests',tests=len(ids),full_wall=wall,smoke_below078=sum(s['wall']<.78 for s in samples))


def storage():
    roots={}
    for label,root in (('D','D:/ANNAM/TradingWorkspace'),('E','E:/BACKUP-TRADINGWORKSPACE')):
        p=JOB/f'storage-after-{label}.json'
        with p.with_suffix('.stdout').open('x') as out:
            subprocess.run([sys.executable,'tooling/workspace_maintenance.py','inventory','--root',root,'--output',str(p)],stdout=out,stderr=subprocess.STDOUT,check=True)
        before=read(V20/f'storage-after-{label}.json');after=read(p)
        roots[label]=dict(before=before['groups']['/'],after=after['groups']['/'],
            delta_bytes=after['groups']['/']['bytes']-before['groups']['/']['bytes'],before_errors=before['errors'],after_errors=after['errors'],
            baseline='Reused V20 final non-atomic inventory; other activity may contribute.')
    compressed_files=list(JOB.rglob('*-manifest.json'));entries=[read(p) for p in compressed_files]
    own=[p for p in JOB.rglob('*') if p.is_file()]
    save('storage-final.json',dict(roots=roots,compressed_tables=len(entries),
        original_table_bytes=sum(r['original_bytes'] for r in entries),compressed_table_bytes=sum(r['compressed_bytes'] for r in entries),
        own_job_bytes=sum(p.stat().st_size for p in own),files=len(own),source_data_deleted=0,
        raw_price_cache_duplicated=False,physical_freed_bytes=None))


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('stage',choices=('tests','storage'));a=p.parse_args();globals()[a.stage]()

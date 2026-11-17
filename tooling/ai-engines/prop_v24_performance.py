"""Equivalent-ID engineering measurements; preserve failures and startup costs."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from statistics import median
import json,os,subprocess,time
from prop_v24_common import *
from prop_v21_delivery import RUNTIMES

COMPLETE=Path('.runtime/quant-audit-v24/Scripts/python.exe').resolve()
TEMP=Path('.runtime/v24-test-temp').resolve();TEMP.mkdir(parents=True,exist_ok=True)
ENV=dict(os.environ,TEMP=str(TEMP),TMP=str(TEMP),PYTHONPATH='projects/trader/foundation_v2;tooling/ai-engines;tooling/ai-engines/tests')

def command(label,args):
    output=JOB/(label+'.json')
    if output.exists():raise ValueError('Preserve benchmark attempt')
    started=time.perf_counter()
    with output.with_suffix('.stdout').open('x') as log:p=subprocess.run(args+['--output',str(output)],env=ENV,stdout=log,stderr=subprocess.STDOUT)
    elapsed=time.perf_counter()-started;r=read(output)
    if p.returncode or not r['passed'] or r['skipped']:raise ValueError('Correctness failed:'+label)
    return dict(label=label,wall=elapsed,receipt=r)

def baseline():
    save('performance-plan.json',dict(baseline='five established dependency groups',candidate='one CI-pinned complete runtime, four balanced shards',
        baseline_suite_IDs=1295,smoke_IDs=78,smoke_final_attempts=10,no_retry_for_streak=True,
        full_target_seconds=12.5,smoke_aspirational_seconds=.55,smoke_acceptance_seconds=.65,includes_startup_and_fixture_IO=True))
    profile={}
    for g in RUNTIMES:profile.update(read(V23/f'tests-final-{g}.json')['module_seconds'])
    save('combined-test-profile.json',dict(module_seconds=profile))
    started=time.perf_counter()
    def work(g):
        args=[RUNTIMES[g],'tooling/ai-engines/quant_test_suite.py','--group',g,'--tier','all']
        if g=='base':args+=['--workers','4','--profile',str(V23/'tests-final-base.json')]
        return command('tests-before-'+g,args)
    with ThreadPoolExecutor(max_workers=5) as pool:rows=list(pool.map(work,RUNTIMES))
    ids=set()
    for r in rows:
        assert not ids.intersection(r['receipt']['timings']);ids.update(r['receipt']['timings'])
    save('tests-before-matrix.json',dict(passed=True,tests=len(ids),seconds=time.perf_counter()-started,IDs=sorted(ids)))
    samples=[]
    for i in range(3):
        r=command('smoke-before-'+str(i),[RUNTIMES['base'],'tooling/ai-engines/quant_test_suite.py','--group','base','--tier','smoke','--indexed-imports'])
        samples.append(dict(wall=r['wall'],import_seconds=r['receipt']['import_seconds']))
    save('smoke-before-summary.json',dict(rows=samples))

def complete(label,workers=4):
    r=command(label,[str(COMPLETE),'tooling/ai-engines/quant_test_suite.py','--group','complete','--tier','all',
        '--workers',str(workers),'--profile',str(JOB/'combined-test-profile.json')])
    old=set()
    for g in RUNTIMES:old.update(read(V23/f'tests-final-{g}.json')['timings'])
    ids=set(r['receipt']['timings']);assert len(old)==1295 and old<=ids
    save(label+'-summary.json',dict(passed=True,tests=len(ids),preserved_V23_IDs=len(old),zero_skip=True,
        wall=r['wall'],target_under125=r['wall']<12.5,new_IDs=sorted(ids-old),runtime=str(COMPLETE),workers=workers,
        runner_source_sha256=sha('tooling/ai-engines/quant_test_suite.py')))

def final():
    complete('tests-final')
    baseline=set(read(V23/'smoke-final-00.json')['timings']);samples=[]
    for i in range(10):
        r=command(f'smoke-final-{i:02}',[RUNTIMES['base'],'tooling/ai-engines/quant_test_suite.py','--group','base','--tier','smoke','--indexed-imports'])
        assert set(r['receipt']['timings'])==baseline
        samples.append(dict(attempt=i+1,wall=r['wall'],tests=r['receipt']['tests'],import_seconds=r['receipt']['import_seconds']))
    save('smoke-final-summary.json',dict(rows=samples,below055=sum(r['wall']<.55 for r in samples),below065=sum(r['wall']<.65 for r in samples),
        median=median(r['wall'] for r in samples),max=max(r['wall'] for r in samples)))

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('stage',choices=('baseline','candidate','final'));a=p.parse_args()
    baseline() if a.stage=='baseline' else complete('tests-candidate') if a.stage=='candidate' else final()

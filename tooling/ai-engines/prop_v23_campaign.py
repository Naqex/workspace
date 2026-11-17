"""Frozen filtered quote/event tape, full lifecycle and common-draw audit."""
from datetime import datetime,timezone
import hashlib
import json
import subprocess
import time
import numpy as np
from prop_v23_common import *
from prop_v20_campaign import Tape as ParentTape
from prop_v19_accounts import V19Account,V19LedgerOracle
from prop_v18_bootstrap import draw_plan,sequence_for,MC_END,YEAR
from prop_v18_blocks import BlockTape
from prop_v18_costs import cost_bindings
from prop_v19_stress import summarize
from prop_v14_accounts import monthly_starts
from prop_v15_campaign import metrics
from quant_core.sleeve_ablation import admitted,filter_blocks


def freeze():
    results=read(JOB/'Dev-ablation-results.json');f5=read(JOB/'F5-transfer-results.json')
    passing=[v for v in results['cases'] if v['passed']]
    selected=max(passing,key=lambda v:(min(r['candidate']['Calmar'] for r in v['cases']),
        min(r['candidate']['net_R'] for r in v['cases']),v['profile']['name']))['profile'] if passing else None
    sources=[PROTOCOL,Path(__file__),Path('tooling/ai-engines/quant_core/sleeve_ablation.py')]
    value=dict(schema='V23-Dev-freeze-v1',selected=selected,Development=[FIRST,DEV_END],
        later_statistics_not_yet_computed=True,later_history_already_exposed=True,
        Dev_passes=[v['profile']['name'] for v in passing],F5_passes=[r['asset'] for r in f5['rows'] if r['stage0_passed']],
        financial_source_pins={str(p):sha(p) for p in sources},
        bindings={p:sha(JOB/p) for p in ('registration.json','profiles-before-outcomes.json','Dev-ablation-results.json','F5-transfer-results.json','H1-calendar-diagnosis.json')},
        baseline_profile=read('planning/research/ASYMMETRIC-RECOVERY-V19-FREEZE-20261116.json')['selected_profile'],
        baseline_report_sha256=sha('planning/research/ASYMMETRIC-RECOVERY-V19-RESULTS-20261116.json'),
        no_risk_redistribution=True,source_gaps_remain=True,prop_qualified=False)
    save('selection-freeze.json',value)
    with FREEZE.open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,indent=2)
    event('V23_freeze_requires_commit',selected=selected)


def verify():
    f=read(FREEZE)
    assert json.loads(subprocess.check_output(['git','show','HEAD:'+FREEZE.as_posix()]))==f
    for p,digest in f['financial_source_pins'].items():
        if sha(p)!=digest:raise ValueError('V23_financial_source_changed:'+p)
    return f


class Tape(ParentTape):
    def __init__(self,tag,mode,dev=False):
        super().__init__(tag,mode,dev)
        f=verify();p=f['selected']
        if p is None:raise ValueError('No frozen V23 candidate')
        ratios={r['trade_key']:r['day_range_ATR'] for r in unpack('Dev-OLHC-forensics',V21)}
        if not dev and p['name']!='A1_DROP_WEAKEST':
            ratios.update({r['trade_key']:r['day_range_ATR'] for r in unpack('Full-OLHC-forensics',V21)})
        decisions={f"{t['id']}@{t['entry_msc']}":admitted(t,ratios.get(f"{t['id']}@{t['entry_msc']}"),p)
            for b in self.blocks for t in b['trades']}
        self.blocks=filter_blocks(self.blocks,decisions)
        self.profile=f['baseline_profile'];self.selected=p


def audit(tape,sequence,row):
    import prop_v18_audit as parent
    with bindings(parent,FrictionOracle=V19LedgerOracle):return parent.audit_path(tape,sequence,row)


def account(start,end,tape,pct,standalone=False):
    return V19Account(start,end,'SYM_FLAT',rolling=True,standalone=standalone,profile=tape.profile,friction_pct=pct)


def historical(tag,mode,pct,dev=False,preflight=False):
    tape=Tape(tag,mode,dev);end=DEV_END if dev else END
    starts=[(t,False) for t in monthly_starts(FIRST,end)]+[(FIRST,True)]
    if preflight:starts=starts[:1]
    prefix=('preflight' if preflight else 'Dev' if dev else 'Full')+f'-{tag}-{mode}-{pct}'
    if (JOB/(prefix+'-summary.json')).exists():raise ValueError('Preserve completed historical attempt')
    sequence=[(i,0) for i in range(len(tape.blocks))];started=time.perf_counter()
    books=[account(at,end,tape,pct,funded) for at,funded in starts]
    with cost_bindings(pct):
        for slot,(i,shift) in enumerate(sequence):tape.walk(i,shift,slot,books)
        rows=[dict(a.dump(),kind='STANDALONE_FULL' if funded else 'CHALLENGE',profile='V23_'+tape.selected['name']) for a,(_,funded) in zip(books,starts)]
        checks=[]
        for i,r in enumerate(rows):
            checks.append(audit(tape,sequence,r))
            if (i+1)%32==0:event('V23_historical_audit',case=prefix,done=i+1,total=len(rows))
    binding=compressed(prefix+'-accounts',rows)
    save(prefix+'-audit.json',dict(passed=True,accounts=len(rows),checks=checks,account_manifest=binding,same_author_and_feed=True))
    summary=metrics(rows)
    challenges=[r for r in rows if r['kind']=='CHALLENGE']
    recent=[r for r in challenges if r['start_msc']>=DEV_END]
    summary.update(recent_starts=len(recent),recent_completions=sum(any(p['phase']==2 for p in r['phase_passes']) for r in recent))
    save(prefix+'-summary.json',dict(**summary,order=tag,source=mode,friction=pct,accounts=len(rows),seconds=time.perf_counter()-started))
    event('V23_historical_complete',case=prefix,accounts=len(rows),seconds=time.perf_counter()-started)


def monte(tag,preflight=False):
    tape=Tape(tag,'PRIMARY',dev=preflight);draws=draw_plan(tape)
    from prop_v18_common import JOB as V18
    if not preflight:assert np.array_equal(draws,np.load(V18/'bootstrap-common-draws.npy'))
    name=('preflight-MC' if preflight else 'MC')+'-'+tag;count=2 if preflight else 5000
    binding=dict(freeze_sha256=sha(FREEZE),source_sha256=sha(__file__),order=tag,count=count,
        parent_pack_sha256=sha(V19/('Dev-pack' if preflight else 'Full-pack')/f'{tag}-PRIMARY-blocks.json'))
    if (JOB/(name+'-binding.json')).exists():assert read(JOB/(name+'-binding.json'))==binding
    else:save(name+'-binding.json',binding)
    journal=JOB/(name+'-paths.jsonl')
    rows=[json.loads(s) for s in journal.read_text().splitlines()] if journal.exists() else []
    assert [r['path'] for r in rows]==list(range(len(rows)))
    started=time.perf_counter()
    with journal.open('a',encoding='utf-8',newline='\n') as out,cost_bindings(100):
        for path in range(len(rows),count):
            sequence=sequence_for(tape,draws[path]);books=[account(FIRST,MC_END,tape,100,f) for f in (False,True)]
            for slot,(i,shift) in enumerate(sequence):tape.walk(i,shift,slot,books)
            native=[a.dump() for a in books]
            try:checks=[audit(tape,sequence,r) for r in native]
            except Exception:
                compressed(name+f'-failed-{path}',dict(native=native,sequence=sequence));raise
            c,f=native;passes={p['phase']:p['at'] for p in c['phase_passes']}
            r=dict(path=path,phase1=passes.get(1,-1),both=passes.get(2,-1),breach=c['first_breach'],funded_breach=f['first_breach'],
                daily=c['worst_daily_loss_pct'],static=c['static_loss_pct'],
                funded_payout_years=[sum(p['trader_usd'] for p in f['payouts'] if FIRST+y*YEAR<=p['at']<FIRST+(y+1)*YEAR) for y in range(3)],
                post_challenge_payout_USD=c['trader_payout_usd'],independent_full_ledger_checks=checks,
                native_ledger_sha256=[hashlib.sha256(json.dumps(n,sort_keys=True).encode()).hexdigest() for n in native])
            out.write(json.dumps(r)+'\n');out.flush();rows.append(r)
            if (path+1)%100==0:event('V23_MC_progress',order=tag,paths=path+1,seconds=time.perf_counter()-started)
    compressed(name+'-paths',rows)
    save(name+'-summary.json',dict(**summarize(rows),order=tag,mode='PRIMARY',friction=100,accounts_fully_audited=2*len(rows),
        journal_sha256=sha(journal),worst_daily=max(r['daily'] for r in rows),worst_static=max(r['static'] for r in rows),
        mean_post_challenge_payout_USD_per_elapsed_year=float(np.mean([r['post_challenge_payout_USD'] for r in rows]))/3,
        seconds=time.perf_counter()-started))
    event('V23_MC_complete',order=tag,paths=len(rows))


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('stage',choices=('freeze','historical','monte'));p.add_argument('--tag',choices=('OLHC','OHLC'),default='OLHC')
    p.add_argument('--mode',choices=('PRIMARY','STRICT'),default='PRIMARY');p.add_argument('--pct',type=int,choices=(100,150),default=100)
    p.add_argument('--dev',action='store_true');p.add_argument('--preflight',action='store_true');a=p.parse_args()
    if a.stage=='freeze':freeze()
    elif a.stage=='historical':historical(a.tag,a.mode,a.pct,a.dev,a.preflight)
    else:monte(a.tag,a.preflight)

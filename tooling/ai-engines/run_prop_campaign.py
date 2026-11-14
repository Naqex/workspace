"""Registered campaign stages, with an explicit Development/Validation release."""
import argparse
from datetime import datetime,timezone
from pathlib import Path
import time

from prop_campaign_source import (JOB,PARENT,START,END,FINAL,CALENDAR,Prices,Calendar,
    read,write_json,digest,gold_views,signals,stamp)
from prop_campaign_exits import CELLS,path,h1_ma
from prop_campaign_accounts import Account,annual,replay


def phase1():
    prices=Prices(read(JOB/'gold-dev-manifest-v2.json'))
    metrics={}
    baseline=read(PARENT/'attempt-2/result.json')['annual']
    for cell in CELLS:
        for policy in ('A0','E1','E2','E3'):
            trades=read(JOB/f'paths-{cell}-{policy}.json')
            unknown=[t['signal_id'] for t in trades if t.get('exit_policy_unknown')]
            if unknown:
                metrics[cell+':'+policy]=dict(unknown=unknown,annual=None)
            else:
                print('annual compare',cell,policy,flush=True)
                rows=annual(trades,prices,cell)
                metrics[cell+':'+policy]=dict(unknown=[],annual=rows)
                if policy=='A0':
                    for r in rows:
                        parent=next(p for p in baseline if p['cell']==cell and p['risk_usd']==150 and p['year']==r['year'])
                        if abs(parent['annual_net_R']-r['net_R'])>1e-9:
                            raise ValueError('Anchor0_cash_parity')
                        for a,b in (('peak_to_valley_pct','peak_dd_pct'),('static_loss_pct','static_loss_pct'),
                                    ('worst_daily_loss_pct','worst_daily_loss_pct')):
                            if abs(parent[a]-r[b])>1e-9:
                                raise ValueError('Anchor0_equity_parity:'+a+':'+str((parent[a],r[b])))
            write_json(JOB/'phase1-metrics.json',metrics)
    promotions=[]
    for policy in ('E1','E2','E3'):
        reasons=[];gains=[];dds=[]
        for cell in CELLS:
            candidate=metrics[cell+':'+policy]
            if candidate['unknown']:
                reasons.append(cell+':UNKNOWN_DECISION_PRICE');continue
            for old,new in zip(metrics[cell+':A0']['annual'],candidate['annual']):
                ratio=old['net_R']/old['max_equity_R_DD']
                gain=(new['net_R']/new['max_equity_R_DD'])/ratio
                gains.append(gain);dds.append(new['max_equity_R_DD'])
                if new['net_R']<=0:reasons.append(f"{cell}:{new['year']}:NEGATIVE")
                if gain<1.1:reasons.append(f"{cell}:{new['year']}:RETURN_DD_GAIN_LT10")
                if new['net_ex_top3_R']<old['net_ex_top3_R']+1:
                    reasons.append(f"{cell}:{new['year']}:EX_TOP3_GAIN_LT1R")
        promotions.append(dict(policy=policy,reasons=reasons,eligible=not reasons,
            worst_gain=min(gains) if gains else None,worst_dd=max(dds) if dds else None))
    winners=sorted([p for p in promotions if p['eligible']],
        key=lambda p:(-p['worst_gain'],p['worst_dd'],p['policy']))
    sleeves={n:read(JOB/f'stage0-{n}.json') for n in ('S1','S2','S3')}
    survivors=[n for n,r in sleeves.items() if r['pass_stage0']]
    if survivors:
        raise ValueError('stage1_path_admission_required:'+','.join(survivors))
    result=dict(selected_exit=winners[0]['policy'] if winners else 'A0',
        exit_decisions=promotions,selected_sleeves=[],stage0={n:{k:v for k,v in r.items() if k!='measurements'} for n,r in sleeves.items()},
        frozen_at_utc=datetime.now(timezone.utc).isoformat(),
        selection_data_end_exclusive=END,prices2024_for_selection=False,
        prices2025_2026_read=False,
        source_pins={str(p):digest(p) for p in JOB.glob('stage0-*.json') if 'coarse' not in p.name},
        phase1_metrics_sha256=digest(JOB/'phase1-metrics.json'))
    write_json(JOB/'composition-freeze.json',result)
    print('FROZEN COMPOSITION',result['selected_exit'],result['selected_sleeves'],flush=True)


def validation():
    freeze=read(JOB/'composition-freeze.json')
    if freeze['selection_data_end_exclusive']!=END or freeze['selected_sleeves']:
        raise ValueError('invalid_composition_freeze')
    write_json(JOB/'validation-release.json',dict(composition_sha256=digest(JOB/'composition-freeze.json'),
        released_utc=datetime.now(timezone.utc).isoformat(),authorized_end_exclusive=FINAL,
        prices2025_2026_read=False))
    hours=gold_views(validation=True)
    s=[r for r in signals(hours,first=END,end=FINAL) if r['recipe']=='A']
    if len(s)!=98:raise ValueError('validation_A_signal_parity')
    p=Prices(read(PARENT/'attempt-2/binary-manifest.json'),FINAL)
    cal=Calendar(CALENDAR);ma=h1_ma(hours);chosen=freeze['selected_exit']
    for cell in CELLS:
        alltrades=read(JOB/f'paths-{cell}-{chosen}.json')
        v=[]
        for r in s:
            t,_=path(r,p,cal,chosen,cell,ma)
            if t.get('exit_policy_unknown'):raise ValueError('validation_exit_unresolved')
            v.append(t)
        alltrades+=v;write_json(JOB/f'frozen-system-{cell}-trades.json',alltrades)
        print('validation annual',cell,chosen,len(alltrades),flush=True)
        years=annual(alltrades,p,cell,years=(2022,2023,2024))
        write_json(JOB/f'frozen-system-{cell}-annual.json',years)
        cases=[Account(stamp(f'{year}-{month:02d}-01'),FINAL,cell,rolling=True)
               for year in (2022,2023,2024) for month in range(1,13)]
        results=replay(alltrades,p,cases)
        for c in results:
            start=datetime.fromtimestamp(c['start_msc']/1000,timezone.utc)
            c.update(start_year=start.year,start_month=start.month)
        write_json(JOB/f'lifecycle-{cell}.json',results)
        print('monthly completed',cell,'P1',sum(len(c['phase_passes'])>=1 for c in results),
              'P2',sum(len(c['phase_passes'])==2 for c in results),
              'payouts',sum(len(c['payouts']) for c in results),flush=True)
    write_json(JOB/'validation-source-access.json',dict(hours=sorted(p.accessed),cutoff=p.cutoff))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=('phase1','validation'))
    args=parser.parse_args()
    try:
        globals()[args.stage]()
    except BaseException as e:
        import traceback
        failure=JOB/f'failure-{args.stage}-{time.time_ns()}.json'
        write_json(failure,dict(type=type(e).__name__,code=str(e),
            trace=traceback.format_exc(),utc=datetime.now(timezone.utc).isoformat()))
        raise

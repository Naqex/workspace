"""Fixed-budget Development-only B1/B2/B3 screen; no later-price selection."""
import subprocess
import numpy as np
from prop_v21_common import *
from prop_v21_forensics import Context,taxonomy,marked_metrics,refine
from quant_core.behavioral_signals import recipes
from quant_core.vectorized_sl_active_kernel import money,daily_mtm
from quant_core.gap_aware_execution import GapAwarePathIndex,replay_gap_aware
from quant_core.ftmo_execution_and_calendar import gold_calendar
from quant_core.trade_forensics_classifier import summarize
from prop_v16_paths import CausalFlatSchedule
from prop_v12_campaign import load_bars

DAY=86400000
REGISTRATION=JOB/'registration.json'
CORRECTED=False


def register():
    files=[PROTOCOL,*Path('tooling/ai-engines').glob('prop_v21_*.py'),
        Path('tooling/ai-engines/quant_core/trade_forensics_classifier.py'),
        Path('tooling/ai-engines/quant_core/behavioral_signals.py')]
    save('registration.json',dict(commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        code={str(p):sha(p) for p in files},Dev=[FIRST,DEV_END],end=END,budget=dict(B1=1,B2=24,B3=4),
        source_metadata={str(V14/n):sha(V14/n) for n in ('source-dev-admission.json','full-source-admission.json')},
        later_taxonomy_after_Dev_decision=True,already_exposed_history=True))


def check_registration():
    r=read(REGISTRATION)
    for p,digest in r['code'].items():
        if sha(p)!=digest:raise ValueError('V21_registered_code_changed:'+p)


def comparison(base,new,base_tax,new_tax):
    reasons=[]
    if new['net_R']<=base['net_R']+1e-8:reasons.append('NET_NOT_HIGHER')
    if new['Calmar'] is None or base['Calmar'] is None or new['Calmar']<=base['Calmar']:reasons.append('CALMAR_NOT_HIGHER')
    if new['equity_R_DD']>base['equity_R_DD']+1e-8:reasons.append('EQUITY_DD_INCREASE')
    if new['worst_daily_R']>base['worst_daily_R']+1e-8:reasons.append('DAILY_LOSS_INCREASE')
    if new_tax['W1_share']<=base_tax['W1_share']:reasons.append('W1_SHARE_NOT_HIGHER')
    before=sum(base_tax['overlapping_loss_flags'][k]['loss_R'] for k in ('L2','L3'))
    after=sum(new_tax['overlapping_loss_flags'][k]['loss_R'] for k in ('L2','L3'))
    if after>=before:reasons.append('GIVEBACK_EXHAUSTION_NOT_REDUCED')
    return reasons


def b1():
    check_registration();summary=read(JOB/'Dev-forensics-summary.json')
    loss=summary['OLHC']['total']['overlapping_loss_flags']
    choice='B1_EARLY_NET_BE' if loss['L2']['loss_R']>=loss['L3']['loss_R'] else 'B1_EXHAUSTION90'
    save('B1-choice-before-child-outcome.json',dict(choice=choice,Dev_parent_loss=loss,
        prior_exposure='Dev taxonomy only; no 2024-2026 V21 taxonomy yet.',one_change=True))
    c=Context(True);rows=[]
    for tag in ('OLHC','OHLC'):
        parent=read(V19/f'Dev-{tag}-PRIMARY-trades.json');child=refine(parent,c,tag,choice)
        classified,tax=taxonomy(child,c,tag);m=marked_metrics(child,c,tag)
        old=summary[tag];reasons=comparison(old['metrics'],m,old['total'],tax['total'])
        # Both three-year clusters must retain positive realized economics.
        clusters=[sum(r['net_R'] for r in classified if low<=r['year']<=high) for low,high in ((2018,2020),(2021,2023))]
        if min(clusters)<=0:reasons.append('DUAL_CLUSTER_FAIL')
        compressed(f'B1-{tag}-forensics',classified)
        compressed(f'B1-{tag}-trades',child)
        rows.append(dict(order=tag,choice=choice,base=old['metrics'],child=m,trades=len(child),
            taxonomy=tax['total'],reasons=reasons,passed=not reasons,cluster_R=clusters))
    save('B1-result.json',dict(choice=choice,cases=rows,passed=all(r['passed'] for r in rows),
        source_gap_stress_required_before_promotion=any(r['taxonomy']['provisional'] for r in rows)))
    event('B1_complete',choice=choice,passed=all(r['passed'] for r in rows))


def measure(recipe,bars,asset,schedule,*,hourly=False):
    at=recipe['at'];side=recipe['side'];scale=1000 if asset in ('XAUUSD','US500') else 100000
    ix=bars['t'].searchsorted(at);safe=np.minimum(ix,len(bars)-1);entry=bars['t'][safe]
    deadline=np.array([schedule.cutoff(int(t),asset) for t in entry],dtype='int64')
    # H1-only GBP has no20:30 quote: retain missing primary endpoint. A20:00
    # observation is auxiliary only, never eligible for strategy promotion.
    x=bars['t'].searchsorted(deadline);last=np.minimum(x,len(bars)-1)
    end=bars['t'][last]
    p0=np.where(side==1,bars['ao'][safe],bars['bo'][safe]).astype('int64')
    px=np.where(side==1,bars['bo'][last],bars['ao'][last]).astype('int64')
    natural=side*(p0-recipe['stop'])/scale
    valid=(ix<len(bars))&(entry>=at)&(entry-at<=60000)&(end==deadline)&(deadline>entry)&(natural>0)&(((at//DAY+3)%7)<5)
    valid &= np.array([schedule.off_kind(int(t),asset) is None for t in entry],dtype=bool)
    gross=side*(px-p0)/scale
    net=money(asset,'SYM',side,p0,px,entry,np.maximum(end,entry),np.full(len(at),'HORIZON'))['net']
    extra=-money(asset,'SYM',side,p0,p0,entry,entry,np.full(len(at),'HORIZON'))['net']
    friction=(bars['ao'][safe]-bars['bo'][safe])/scale+extra
    ratio=np.divide(friction,natural,out=np.full(len(at),np.inf),where=natural>0)
    years=(at.astype('datetime64[ms]').astype('datetime64[Y]').astype(int)+1970)
    return dict(asset=asset,recipe=recipe['id'],family=recipe['family'],at=at,entry_at=entry,
        deadline=deadline,exit_at=end,side=side,entry_price=p0,exit_price=px,stop=recipe['stop'],natural=natural,
        friction=friction,ratio=ratio,ok=valid,admitted=valid&(ratio<=.12),years=years,net=net,gross=gross,
        primary_endpoint_resolution='H1_ONLY_INCOMPATIBLE_WITH_2030' if hourly else 'M1')


def screen(m):
    annual=[];reasons=[]
    for y in range(2018,2024):
        raw=m['years']==y;use=raw&m['ok'];n=int(raw.sum());priced=int(use.sum())
        mean=float(m['net'][use].mean()) if priced else None
        friction=float(m['friction'][use].mean()) if priced else None
        annual.append(dict(year=y,raw=n,priced=priced,admitted=int((raw&m['admitted']).sum()),
            mean_net_units=mean,mean_friction_units=friction,
            raw_net_R=float((m['net'][use]/m['natural'][use]).sum()) if priced else None))
        if mean is None or mean<=0:reasons.append(f'{y}:NET_NONPOSITIVE_OR_MISSING')
        if mean is None or mean<=friction:reasons.append(f'{y}:MARKOUT_NOT_ABOVE_FRICTION')
    raw=len(m['at']);good=m['ok'];retention=float(m['admitted'].sum()/raw) if raw else 0.
    ratio=float(np.median(m['friction'])/np.median(m['natural'])) if raw and np.median(m['natural'])>0 else None
    clusters=[float(m['net'][good&(m['years']>=lo)&(m['years']<=hi)].sum()) for lo,hi in ((2018,2020),(2021,2023))]
    if min(clusters)<=0:reasons.append('DUAL_CLUSTER_FAIL')
    if not good.all():reasons.append('ENDPOINT_INCOMPLETE')
    if ratio is None or ratio>.12:reasons.append('SCALE_FAIL')
    if retention<.5:reasons.append('RETENTION_BELOW50')
    if m['admitted'].sum()/6<40:reasons.append('CADENCE_BELOW40')
    return dict(asset=m['asset'],recipe=m['recipe'],family=m['family'],raw=raw,priced=int(good.sum()),
        retained=int(m['admitted'].sum()),retention=retention,median_natural=float(np.median(m['natural'])) if raw else None,
        scale_ratio=ratio,annual=annual,cluster_net_units=clusters,reasons=reasons,stage0_passed=not reasons)


def behavioral():
    check_registration();c=Context(True);schedule=c.schedule
    index=read(ROOT/'ensemble-and-storage-v11-20261115/source-admission-v11.json')
    output=[];survivors=[]
    for asset in ('XAUUSD','EURUSD','US500','GBPUSD'):
        bars=c.bars[asset] if asset in c.bars else load_bars(asset,index)
        hourly=asset=='GBPUSD';raw=recipes(bars,asset,FIRST,DEV_END,hourly=hourly)
        if len(raw)!=(8 if asset in ('XAUUSD','US500') else 6):raise ValueError('V21_recipe_budget')
        paths=None
        for recipe in raw:
            if CORRECTED and recipe['family']=='B3':
                parent=read(JOB.parent/'behavioral-results.json')
                reused=next(r for r in parent['rows'] if r['asset']==asset and r['recipe']==recipe['id'])
                output.append(dict(reused,reused_unchanged_B3=True));continue
            m=measure(recipe,bars,asset,schedule,hourly=hourly);r=screen(m)
            compressed(asset+'-'+recipe['id'].replace(':','_')+'-raw',m)
            if r['stage0_passed']:
                if hourly:r['path_status']='M1_DATA_UNAVAILABLE'
                else:
                    if paths is None:paths=GapAwarePathIndex(bars,asset=asset,schedule=schedule)
                    m['_index']=paths
                    p=replay_gap_aware(paths,m,'P0');use=m['admitted']&p['valid']
                    v=p['model']['SYM']['net_R'];cl=[float(v[use&(m['years']>=lo)&(m['years']<=hi)].sum()) for lo,hi in ((2018,2020),(2021,2023))]
                    bad=[]
                    if not p['valid'][m['admitted']].all():bad.append('INVALID_PATH')
                    if (p['source_uncertain']&m['admitted']).any():bad.append('SOURCE_UNCERTIFIED_GAPS')
                    if min(cl)<=0:bad.append('SL_ACTIVE_DUAL_CLUSTER_FAIL')
                    if not use.any() or v[use].mean()<.04:bad.append('MEAN_BELOW004')
                    if use.sum()/6<40:bad.append('CADENCE_BELOW40')
                    r['SL_active']=dict(trades=int(use.sum()),net_R=float(v[use].sum()),cluster_R=cl,reasons=bad)
                    if not bad:survivors.append(dict(asset=asset,recipe=recipe['id'],status='REQUIRES_COMPOSITE_DEV_ACCOUNT_PATH_REPLAY'))
            output.append(r)
        event('behavioral_asset_complete',asset=asset,cases=len(raw),stage0_passed=sum(r['stage0_passed'] for r in output if r['asset']==asset))
    save('behavioral-results.json',dict(rows=output,registered_trials=28,Stage0_survivors=sum(r['stage0_passed'] for r in output),SL_survivors=survivors))


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('stage',choices=('register','b1','behavioral'))
    p.add_argument('--corrected-attempt',action='store_true');a=p.parse_args()
    if a.corrected_attempt:
        if a.stage!='behavioral':p.error('correction scope is behavioral only')
        correction=read(JOB/'behavioral-correction-registration.json')
        for name,digest in correction['code'].items():
            if sha(name)!=digest:raise ValueError('V21_correction_code_changed')
        REGISTRATION=JOB/'behavioral-correction-registration.json'
        CORRECTED=True
        import prop_v21_common as common
        JOB=JOB/'behavioral-corrected-v2';JOB.mkdir(exist_ok=True);common.JOB=JOB
    globals()[a.stage]()

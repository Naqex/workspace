"""Entry anatomy and two Dev-only gates; H1 reruns reuse unchanged V21 cases."""
import subprocess
import numpy as np
from prop_v22_common import *
from prop_v21_forensics import Context,features,marked_metrics
from quant_core.trade_forensics_classifier import summarize,concentration
from quant_core.behavioral_signals import closed_atr,recipes
from quant_core.exhaustion_gate import fit_thresholds,accept,resolution_cutoff
from prop_v10_signals import frames,align

DAY,HOUR=86400000,3600000


def snapshot(t,c,cache):
    asset=t['asset'];b=c.bars[asset];at=t['decision_msc'];start=at//DAY*DAY
    lo,hi=b['t'].searchsorted([start,at]);scale=t['scale']
    if asset not in cache:
        h1,h4,_=frames(b);h4['closed_atr']=closed_atr(h4);cache[asset]=(h1,h4)
    h1,h4=cache[asset];f=h1 if '|F4:' in t['id'] else h4
    j=int(f['t'].searchsorted(at,side='right'))-1
    k=int(h4['t'].searchsorted(at,side='right'))-1
    atr4=float(h4['closed_atr'][k]) if k>=0 and np.isfinite(h4['closed_atr'][k]) else None
    hi_day=int(b['bh'][lo:hi].max()) if hi>lo else None
    lo_day=int(b['bl'][lo:hi].min()) if hi>lo else None
    sign=1 if t['side']=='BUY' else -1;edge=hi_day if sign==1 else lo_day
    ratio=c.day_ratio(t)
    return dict(trade_key=f"{t['id']}@{t['entry_msc']}",id=t['id'],family=t['id'].split('|')[1][:2],
        side=t['side'],asset=asset,decision_msc=at,entry_msc=t['entry_msc'],
        year=int(np.datetime64(at,'ms').astype('datetime64[Y]').astype(int)+1970),
        day_range_ATR=ratio,day_high=hi_day/scale if hi_day else None,day_low=lo_day/scale if lo_day else None,
        D1_ATR=(hi_day-lo_day)/scale/ratio if ratio and hi_day is not None else None,
        latest_closed_M1_end=int(b['t'][hi-1])+60000 if hi>lo else None,
        edge_distance=(sign*(edge-t['entry_price_units'])/scale if edge is not None else None),
        signal_body_H4_ATR=(float(abs(f['c'][j]-f['o'][j])/atr4) if j>=0 and atr4 else None),
        signal_range_H4_ATR=(float((f['h'][j]-f['l'][j])/atr4) if j>=0 and atr4 else None),
        signal_closed_at=int(f['t'][j]) if j>=0 else None,context_source_certified=False)


def register():
    files=[PROTOCOL,*Path('tooling/ai-engines').glob('prop_v22_*.py'),Path('tooling/ai-engines/quant_core/exhaustion_gate.py')]
    save('registration.json',dict(commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        code={str(p):sha(p) for p in files},Development=[FIRST,DEV_END],gates=2,original_behavioral_cells=28,
        unchanged_M1_reused=22,changed_GBP_cells=6,additional_AUD_cells=6,later_exposure_already_exists=True))


def check():
    for p,digest in read(JOB/'registration.json')['code'].items():
        if sha(p)!=digest:raise ValueError('Registered source drift:'+p)


def gates():
    check();c=Context(True);cache={};trades=read(V19/'Dev-OLHC-PRIMARY-trades.json')
    snaps=[snapshot(t,c,cache) for t in trades]
    assert all(s['latest_closed_M1_end'] is None or s['latest_closed_M1_end']<=s['decision_msc'] for s in snaps)
    thresholds=fit_thresholds(snaps)
    save('threshold-fit-before-outcome.json',dict(G_L3_A=.9,G_L3_B=thresholds,quantile=.9,fit_uses_returns_or_labels=False,
        source_covariates=compressed('Dev-entry-snapshots',snaps)))
    by_key={s['trade_key']:s for s in snaps};results=[]
    old_summary=read(V21/'Dev-forensics-summary.json')
    for gate in ('G_L3_A','G_L3_B'):
        cases=[]
        for tag in ('OLHC','OHLC'):
            parent=read(V19/f'Dev-{tag}-PRIMARY-trades.json')
            child=[t for t in parent if accept(by_key[f"{t['id']}@{t['entry_msc']}"],gate,thresholds)]
            original=unpack(f'Dev-{tag}-forensics',V21)
            kept={f"{t['id']}@{t['entry_msc']}" for t in child}
            rows=[r for r in original if r['trade_key'] in kept]
            top=concentration(original)['top10'];retained=sum(t['trade_key'] in kept for t in top)
            m=marked_metrics(child,c,tag);base=old_summary[tag]['metrics']
            ex=concentration(rows);base_ex=concentration(original)
            reasons=[]
            if retained<9:reasons.append('TOP10_RETENTION_BELOW90')
            if m['net_R']<=base['net_R']+1e-9:reasons.append('NET_NOT_HIGHER')
            if m['equity_R_DD']>=base['equity_R_DD']-1e-9:reasons.append('EQUITY_DD_NOT_LOWER')
            if m['worst_daily_R']>base['worst_daily_R']+1e-9:reasons.append('DAILY_LOSS_HIGHER')
            if ex['without_top10']<=base_ex['without_top10']+1e-9:reasons.append('EX_TOP10_NOT_HIGHER')
            rejected=[r for r in original if r['trade_key'] not in kept]
            cases.append(dict(order=tag,gate=gate,trades=len(child),base=base,candidate=m,
                base_concentration=base_ex,concentration=ex,top10_retained=retained,
                ex_original_top10_R=sum(r['net_R'] for r in rows if r['trade_key'] not in {v['trade_key'] for v in top}),
                rejected_trades=len(rejected),rejected_winners=sum(r['net_R']>0 for r in rejected),
                rejected_winner_R=sum(r['net_R'] for r in rejected if r['net_R']>0),
                rejected_loser_R=sum(r['net_R'] for r in rejected if r['net_R']<=0),
                taxonomy=summarize(rows),reasons=reasons,passed=not reasons))
        results.append(dict(gate=gate,cases=cases,passed=all(v['passed'] for v in cases)))
    save('Dev-gate-results.json',dict(cases=results,thresholds=thresholds))
    event('V22_gates_complete',passing=[r['gate'] for r in results if r['passed']])


def h1():
    check()
    from prop_v12_campaign import load_bars
    from prop_v16_paths import CausalFlatSchedule
    from quant_core.ftmo_execution_and_calendar import gold_calendar
    from prop_v21_development import measure,screen
    from quant_core.vectorized_sl_active_kernel import money
    parent=read('planning/research/TRADE-FORENSICS-BEHAVIORAL-V21-RESULTS-20261117.json')['behavioral']['rows']
    rows=[dict(r,reused_from_V21=True) for r in parent if r['asset']!='GBPUSD']
    index=read(ROOT/'ensemble-and-storage-v11-20261115/source-admission-v11.json')
    schedule=CausalFlatSchedule(gold_calendar(FIRST,DEV_END).events.values())
    for asset in ('GBPUSD','AUDUSD'):
        bars=load_bars(asset,index)
        for recipe in recipes(bars,asset,FIRST,DEV_END,hourly=True):
            m=measure(recipe,bars,asset,schedule,hourly=True)
            deadline=np.array([resolution_cutoff(t,step=HOUR) for t in m['deadline']],dtype='int64')
            ix=bars['t'].searchsorted(deadline);safe=np.minimum(ix,len(bars)-1);end=bars['t'][safe]
            entry=m['entry_at'];side=m['side'];px=np.where(side==1,bars['bo'][safe],bars['ao'][safe])
            valid=(ix<len(bars))&(end==deadline)&(deadline>entry)&(entry==m['at'])&(m['natural']>0)&(((entry//DAY+3)%7)<5)
            valid &= np.array([schedule.off_kind(int(t),asset) is None for t in entry],dtype=bool)
            m.update(deadline=deadline,exit_at=end,exit_price=px,ok=valid,admitted=valid&(m['ratio']<=.12),
                net=money(asset,'SYM',side,m['entry_price'],px,entry,np.maximum(entry,end),np.full(len(entry),'HORIZON'))['net'],
                primary_endpoint_resolution='H1_OPEN_AT_REGISTERED_HOUR')
            r=screen(m);r['resolution_seconds']=3600;r['reused_from_V21']=False
            cost_only=int((m['ratio']<=.12).sum());retention=cost_only/r['raw'] if r['raw'] else 0
            r.update(cost_eligible=cost_only,cost_only_retention=retention)
            r['reasons']=[v for v in r['reasons'] if v!='RETENTION_BELOW50' or retention<.5]
            r['stage0_passed']=not r['reasons']
            r['exact_M1_or_tick_path_admitted']=False
            if r['stage0_passed']:r['promotion_blocker']='INTRAHOUR_PATH_AND_ACCOUNT_DD_UNMEASURED'
            compressed(asset+'-'+recipe['id'].replace(':','_')+'-H1-raw',m)
            rows.append(r)
        event('H1_asset_complete',asset=asset,passed=sum(r['stage0_passed'] for r in rows if r['asset']==asset))
    assert len(rows)==34
    save('H1-behavioral-results.json',dict(rows=rows,unchanged_reused=22,GBP_rerun=6,AUD_additional=6))


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('stage',choices=('register','gates','h1'));a=p.parse_args();globals()[a.stage]()

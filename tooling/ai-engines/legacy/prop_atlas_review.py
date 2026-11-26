"""Separate Fraction/cash-posted-funding checks for all V2 financial outputs."""
from datetime import datetime,timezone
from fractions import Fraction as F
from statistics import mean,median
from collections import Counter
from prop_atlas_core import JOB,V1,PARENT,event
from prop_campaign_source import START,END,FINAL,HOUR,DAY,Prices,read,write_json,digest
from prop_campaign_review import oracle
from xau_h1_execution_review import money_parts,funding

MODELS=('SYM_FLAT','ASYM_FLAT')


def check_phase0():
    d=read(JOB/'phase0-diagnostic.json')
    ts=read(V1/'frozen-system-ASYM_FLAT-trades.json')
    p=Prices(read(PARENT/'attempt-2/binary-manifest.json'),FINAL)
    parents={r['start_msc']:r for r in read(V1/'lifecycle-ASYM_FLAT.json')}
    checked=[]
    for r in d['accounts']:
        old=parents[r['start_msc']]
        accepted=[a for a in old['accepted'] if a['phase']==2]
        o=oracle(ts,accepted,[],[],p,old['phase_passes'][0]['at']+1,FINAL,'ASYM_FLAT')
        for k,want in (('max_equity',r['max_equity_profit_pct']),
                       ('max_realized_balance',r['max_realized_profit_pct']),
                       ('max_flat_balance',r['max_flat_profit_pct'])):
            if abs((o[k]-50000000)/500000-want)>1e-9:raise ValueError('phase0_peak_oracle:'+k)
        if abs(o['cash']/1000-r['terminal_balance_usd'])>1e-8:raise ValueError('phase0_cash')
        checked.append(dict(start=r['start_msc'],oracle=o))
    for r in d['annual_side']:
        sub=[t for t in ts if t['day'].startswith(str(r['year'])) and t['side']==r['side']]
        parts=[money_parts(dict(t,ounces=150000//abs(t['entry_price_units']-t['stop_units'])),'ASYM_FLAT') for t in sub]
        for key,value in (('gross_R',sum(t['gross'] for t in parts)/15000),
                          ('net_R',sum(t['net'] for t in parts)/15000),
                          ('swap_R',sum(sum(v for _,v in t['swaps']) for t in parts)/15000)):
            if abs(r[key]-value)>1e-10:raise ValueError('phase0_side_fraction')
    write_json(JOB/'phase0-parity.json',dict(status='PASS',accounts=checked,side_books=6))
    event('phase0_oracle_passed',accounts=13)


def check_core():
    bridges=paths=0
    for model in MODELS:
        old={t['signal_id']:t for t in read(V1/f'paths-{model}-A0.json')}
        for policy in ('CA1','CA2'):
            for t in read(JOB/f'core-{model}-{policy}-dev.json'):
                parent=old[t['signal_id']]
                for key in ('entry_msc','entry_price_units','stop_units','decision_msc'):
                    if t[key]!=parent[key]:raise ValueError('carry_changed_entry_or_stop')
                if t['exit_msc']>parent['exit_msc']:raise ValueError('carry_extended_parent')
                if t['side']=='SELL' and t['exit_msc']!=parent['exit_msc']:
                    raise ValueError('carry_changed_sell')
                from prop_campaign_exits import costs
                for risk in (90,125,150,200):
                    q=risk*1000//abs(t['entry_price_units']-t['stop_units'])
                    p=money_parts(dict(t,ounces=q),model);c=costs(t,model,risk)
                    if int(round(c['net_usd']*100))!=p['net']:raise ValueError('core_cost_oracle')
                    bridges+=1
                paths+=1
    write_json(JOB/'core-parity.json',dict(status='PASS',shortened_paths=paths,cost_bridges=bridges))


def check_stage0():
    atlas=read(JOB/'atlas-stage0.json');n=0;gates=0
    if len(atlas['cells'])!=112 or len({r['cell']['id'] for r in atlas['cells']})!=112:
        raise ValueError('atlas_budget_or_duplicate')
    for v in atlas['cells']:
        cell=v['cell'];asset=cell['asset'];scale=1000 if asset in ('XAUUSD','US500') else 100000
        r=read(JOB/f"stage0-{cell['id']}.json")
        for t in r['rows']:
            if not START<=t['decision_msc']<END:raise ValueError('stage0_holdout')
            if 'money' not in t:continue
            e,x=t['entry_quote'],t['exit_quote']
            if not START<=e[0]<=x[0]<END:raise ValueError('stage0_horizon_fence')
            s=1 if t['side']=='BUY' else -1
            p0=F(e[2] if s==1 else e[1],scale);p1=F(x[1] if s==1 else x[2],scale)
            for model in MODELS:
                if asset=='XAUUSD':
                    commission=(p0+p1)*F(7,10**6);slip=F(2,5)
                    rate=F(-40 if model.startswith('SYM') else -45 if s==1 else -5,100)
                    swap=rate*sum(m for at,m in funding(e[0],x[0]))
                elif asset=='US500':
                    commission=F(1);slip=F(3,2);swap=-2*(x[0]//DAY-e[0]//DAY)
                else:
                    commission=F(5,100000);slip=F(4,100000)
                    swap=F(-40,100000)*sum(m for at,m in funding(e[0],x[0]))
                net=s*(p1-p0)-commission-slip+swap
                for key,want in (('net',net),('swap',swap),('commission',commission),('slippage',slip)):
                    if abs(float(want)-t['money'][model][key])>1e-9:
                        raise ValueError('stage0_fraction_bridge:'+key)
                n+=1
        if r['stage0_pass']!=all(not a['reasons'] for a in r['annual']):
            raise ValueError('stage0_gate_bridge')
        gates+=1
    write_json(JOB/'atlas-parity.json',dict(status='PASS',unit_cost_bridges=n,cells=gates))
    event('atlas_oracle_passed',cells=gates,cost_bridges=n)


def check_lifecycle():
    count=0;records=[];money_checks=0
    reader=Prices(read(PARENT/'attempt-2/binary-manifest.json'),FINAL)
    for model in MODELS:
        ts=read(JOB/f'system-{model}-trades.json')
        cases=read(JOB/f'lifecycle-{model}.json')
        for c in cases:
            for a in c['accepted']:
                state=a['risk_state'];base=125 if a['phase']==3 else 200
                eq=state['equity_milli_usd']
                expected=min(base,90) if eq<47750000 else min(base,150) if eq<48750000 else base
                if state['balance_milli_usd']-state['daily_anchor_milli_usd']<-900000:expected=min(expected,125)
                if expected!=a['risk_usd'] or state['projected_stop_milli_usd']<=46500000:
                    raise ValueError('V2_policy_independent_check')
                t=ts[a['trade']];q=a['ounces'];p=money_parts(dict(t,ounces=q),model)
                realized=next((x for x in c['closed'] if x['trade']==a['trade']),None)
                if realized and int(round(realized['net_usd']*100))!=p['net']:
                    raise ValueError('V2_actual_size_fraction')
                money_checks+=1
            v=oracle(ts,c['accepted'],c['phase_passes'],c['payouts'],reader,
                c['start_msc'],c['end_msc'],model)
            for k,field in (('dd','peak_dd_pct'),('daily','worst_daily_loss_pct'),('static','static_loss_pct')):
                if abs(v[k]-c[field]*500000)>1e-6:raise ValueError('V2_equity_parity:'+k)
            if bool(v['breach'])!=bool(c['first_breach']):raise ValueError('V2_breach_parity')
            if not v['breach'] and abs(v['cash']/1000-c['balance_usd'])>1e-7:raise ValueError('V2_cash_parity')
            count+=1;records.append(dict(model=model,start=c['start_msc'],oracle=v))
            if count%6==0:event('V2_account_oracle',completed=count,total=72)
    write_json(JOB/'lifecycle-parity.json',dict(status='PASS',accounts=count,
        actual_sized_cost_and_policy_checks=money_checks,records=records,
        independent_implementation_same_operator=True,reviewer_sha256=digest(__file__)))


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('stage',choices=('phase0','core','stage0','lifecycle'))
    arg=p.parse_args()
    {'phase0':check_phase0,'core':check_core,'stage0':check_stage0,'lifecycle':check_lifecycle}[arg.stage]()

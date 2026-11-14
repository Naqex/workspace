"""Three frozen exits and unconditional sleeve screens; no parameter search."""
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from statistics import mean, median
import numpy as np

from prop_campaign_source import (JOB, ROOT, PARENT, START, END, FINAL, HOUR, DAY,
    CALENDAR, Prices, Calendar, read, write_json, digest, deadline)
from xau_h1_execution import economics, commission, cents
from xau_h1_stage0_scan import funding_events

CELLS=('SYM_FLAT','ASYM_FLAT')


def funding_rate(side,cell):
    return -.40 if cell.startswith('SYM') else -.45 if side=='BUY' else -.05


def take_first(mask):
    positions=np.flatnonzero(mask)
    return int(positions[0]) if len(positions) else None


def quantity(t,risk=150):
    q=int(risk*1000)//abs(t['entry_price_units']-t['stop_units'])
    if not 1<=q<=5000:
        raise ValueError('lot_spec')
    return q


def costs(t,cell,risk=150):
    return economics(dict(t,risk_usd=risk,ounces=quantity(t,risk)),cell)


def net_per_oz(t,prices,cell):
    p0=t['entry_price_units'];sign=1 if t['side']=='BUY' else -1
    p=prices['b'].astype('int64') if sign==1 else prices['a'].astype('int64')
    funding=np.zeros(len(p))
    for e in funding_events(t['entry_msc'],int(prices['t'][-1])):
        funding[prices['t']>=e['at']]+=funding_rate(t['side'],cell)*e['multiplier']
    return sign*(p-p0)/1000-.4-(p+p0)*.000000007+funding-.02


def covered_stop(t,cell):
    """Conservative future-cost reserve; rounded outwards, never loosens."""
    p0=t['entry_price_units'];buy=t['side']=='BUY';sign=1 if buy else -1
    negative=sum(max(0,-funding_rate(t['side'],cell)*e['multiplier'])
        for e in funding_events(t['entry_msc'],t['deadline_msc']))
    # s*(p-p0)/1000 >= .42 + (p+p0)*7e-9 + all negative funding.
    target=(sign*p0/1000+.42+negative+p0*.000000007)/(sign/1000-.000000007)
    stop=int(np.ceil(target)) if buy else int(np.floor(target))
    return max(t['stop_units'],stop) if buy else min(t['stop_units'],stop)


def path(row,prices,calendar,exit_policy,cell,h1_closes):
    entry=prices.endpoint(row['decision_msc'])
    if entry is None:
        raise ValueError('missing_entry')
    end,why=deadline(row,calendar,entry[0]);last=prices.endpoint(end)
    if last is None:
        raise ValueError('missing_deadline:'+str(end))
    a,ordinal=prices.path(entry[0],last[0])
    buy=row['side']=='BUY';sign=1 if buy else -1;p0=entry[2] if buy else entry[1]
    stop=row['stop_units'];distance=sign*(p0-stop)
    if distance<=0 or (entry[1]<=stop if buy else entry[2]>=stop):
        raise ValueError('invalid_initial_geometry')
    p=a['b'] if buy else a['a']
    hit=take_first((p<=stop if buy else p>=stop)&(a['t']<end))
    finish=int(a['t'].searchsorted(end))
    if hit is not None and hit<finish:
        finish=hit;why='SL'
    t=dict(row,signal_id=f"{row['recipe']}:{row['decision_msc']}:{row['side']}",
        entry_msc=entry[0],entry_quote=entry[:3],entry_quote_index=entry[3],
        entry_price_units=p0,deadline_msc=end,natural_sl_usd_per_oz=distance/1000,
        exit_policy=exit_policy,protected_stop_units=None)
    n=net_per_oz(t,a,cell);trigger=None;decision=None
    if exit_policy=='E1':
        when=entry[0]//DAY*DAY+20*HOUR+HOUR//2
        decision=int(a['t'].searchsorted(when))
        if decision<=finish and a['t'][decision]<end:
            if a['t'][decision]-when>60000:
                raise ValueError('E1_decision_stale')
            if n[decision]<1.5*distance/1000:
                finish=decision;why='E1_FLAT'
            else:
                trigger=decision
    elif exit_policy=='E2':
        trigger=take_first(n[:finish+1]>=1.5*distance/1000)
    elif exit_policy=='E3':
        when=entry[0]//DAY*DAY+21*HOUR+HOUR//2
        decision=int(a['t'].searchsorted(when))
        if decision<=finish and a['t'][decision]<end:
            if a['t'][decision]-when>60000:
                # Preserve a parent path solely for source diagnostics. It is
                # explicitly unknown, never an E3 fill or eligible performance.
                t['exit_policy_unknown']='E3_DECISION_NO_FRESH_QUOTE'
                t['unknown_decision_wait_ms']=int(a['t'][decision]-when)
            else:
                future=sum(max(0,-funding_rate(row['side'],cell)*e['multiplier'])
                    for e in funding_events(int(a['t'][decision]),end))
                if n[decision]<future:
                    finish=decision;why='E3_CARRY_REJECT'
    if trigger is not None:
        protected=covered_stop(t,cell);t['protected_stop_units']=protected
        if (p[trigger]<=protected if buy else p[trigger]>=protected):
            finish=trigger;why='PROTECTION_MARKET_CLOSE'
        else:
            mask=p[trigger+1:finish+1]<=protected if buy else p[trigger+1:finish+1]>=protected
            hit=take_first(mask)
            if hit is not None:
                finish=trigger+1+hit;why='PROTECTED_SL'
            if exit_policy=='E2':
                for when,close,sma in h1_closes:
                    if not int(a['t'][trigger])<when<=int(a['t'][finish]):
                        continue
                    if close<sma if buy else close>sma:
                        ix=int(a['t'].searchsorted(when))
                        if ix<=finish:
                            if a['t'][ix]-when>60000:
                                raise ValueError('E2_h1_fill_stale')
                            finish=ix;why='E2_H1_MA20';break
    t.update(exit_msc=int(a['t'][finish]),exit_price_units=int(p[finish]),
        exit_quote_index=int(ordinal[finish]),reason=why,
        endpoint_wait_ms=max(0,int(a['t'][finish])-end),
        trigger_msc=int(a['t'][trigger]) if trigger is not None else None)
    t['costs']={cell:costs(t,cell)}
    q=quantity(t);r=costs(t,cell)['net_R'];first_roll=entry[0]//DAY*DAY+22*HOUR
    day1=(a['t']<first_roll)&(np.arange(len(a))<=finish)
    # Actual cent-rounded fixed-$150 liquidation, without trigger allowance.
    gross=sign*(p.astype('int64')-p0)*q/1000
    gross=np.sign(gross)*np.floor(np.abs(gross)*100+.50000001)/100
    exit_fees=np.floor(p.astype('int64')*q*.000000007*100+.50000001)/100
    carry=(n+.4+(p.astype('int64')+p0)*.000000007+.02-
           sign*(p.astype('int64')-p0)/1000)*q
    exact=(gross-commission(p0,q)-exit_fees-.4*q+carry)/150
    max_day1=float(np.max(exact[day1]))
    last1=int(np.flatnonzero(day1)[-1])
    before=dict(t,exit_msc=int(a['t'][last1]),exit_price_units=int(p[last1]),reason='DIAGNOSTIC')
    pre=costs(before,cell)['net_R']
    forensic=dict(mfe_day1_R=max_day1,final_net_R=r,pre_rollover_liquidation_R=pre,
        post_rollover_increment_R=r-pre,
        pre_rollover_mark_age_ms=int(first_roll-a['t'][last1]),
        held_after_first_rollover=bool(t['exit_msc']>=first_roll))
    return t,forensic


def h1_ma(hours):
    closes=[];out=[]
    for at,op,hi,lo,c,n in hours:
        if n!=60:
            continue
        if len(closes)>=20:
            out.append((at+HOUR,c,sum(closes[-20:])/20))
        closes.append(c)
    return out


def forensic_summary(rows):
    return dict(trades=len(rows),thresholds={str(k):dict(
        reached=sum(r['mfe_day1_R']>=k for r in rows),
        final_negative=sum(r['mfe_day1_R']>=k and r['final_net_R']<0 for r in rows),
        gave_back_half=sum(r['mfe_day1_R']>=k and r['final_net_R']<=r['mfe_day1_R']/2 for r in rows))
        for k in (1,1.5,2,3)},
        pre_rollover_sum_R=sum(r['pre_rollover_liquidation_R'] for r in rows),
        post_rollover_increment_R=sum(r['post_rollover_increment_R'] for r in rows),
        final_sum_R=sum(r['final_net_R'] for r in rows),
        carried=sum(r['held_after_first_rollover'] for r in rows),
        max_pre_rollover_mark_age_ms=max(r['pre_rollover_mark_age_ms'] for r in rows))


def run_phase1():
    prices=Prices(read(JOB/'gold-dev-manifest.json'));cal=Calendar(CALENDAR)
    signals=[r for r in read(JOB/'gold-dev-signals.json') if r['recipe']=='A']
    ma=h1_ma(read(JOB/'gold-dev-hours.json'))
    alltrades={};forensics={}
    for cell in CELLS:
        for policy in ('A0','E1','E2','E3'):
            trades=[];fs=[]
            for i,r in enumerate(signals):
                t,f=path(r,prices,cal,policy,cell,ma);trades.append(t);fs.append(f)
                if i%50==0:
                    print('phase1',cell,policy,i,flush=True)
            alltrades[cell+':'+policy]=trades
            if policy=='A0':
                forensics[cell]={str(y):forensic_summary([f for t,f in zip(trades,fs) if t['day'].startswith(str(y))])
                                  for y in (2022,2023)}
                write_json(JOB/('forensic-trades-'+cell+'.json'),[dict(t,forensic=f) for t,f in zip(trades,fs)])
            write_json(JOB/('paths-'+cell+'-'+policy+'.json'),trades)
    write_json(JOB/'phase1-forensics.json',forensics)
    write_json(JOB/'phase1-source-access.json',dict(hours=sorted(prices.accessed),cutoff=prices.cutoff))


def screen(signals,prices,calendar,scale=1000,eur=False):
    rows=[]
    for r in signals:
        if not calendar.allowed(r['decision_msc']):
            rows.append(dict(r,blocked='SESSION_CLOSED'));continue
        ent=prices.endpoint(r['decision_msc'])
        if ent is None:
            rows.append(dict(r,blocked='MISSING_ENTRY'));continue
        end,why=deadline(r,calendar,ent[0]);exit=prices.endpoint(end)
        if ent is None or exit is None:
            rows.append(dict(r,blocked='MISSING_ENDPOINT'));continue
        buy=r['side']=='BUY';sign=1 if buy else -1
        p0=ent[2] if buy else ent[1];p1=exit[1] if buy else exit[2]
        sl=sign*(p0-r['stop_units'])/scale
        friction=(ent[2]-ent[1])/scale+(9/100000 if eur else 2*p0/scale*.000007+.4)
        valid=sl>0 and (ent[1]>r['stop_units'] if buy else ent[2]<r['stop_units'])
        efriction=(ent[2]-ent[1]+exit[2]-exit[1])/(2*scale)+(9/100000 if eur else (p0+p1)/scale*.000007+.4)
        mult=sum(e['multiplier'] for e in funding_events(ent[0],exit[0]))
        nets={cell:sign*(p1-p0)/scale-(9/100000 if eur else (p0+p1)/scale*.000007+.4)+
              (-40/100000 if eur else funding_rate(r['side'],cell))*mult for cell in CELLS}
        rows.append(dict(r,entry_quote=ent,exit_quote=exit,deadline=end,deadline_kind=why,
            natural_sl=sl,valid_geometry=bool(valid),friction=friction,
            pass12=bool(valid and friction/sl<=.12),execution_friction=efriction,nets=nets))
    annual=[]
    for year in (2022,2023):
        cohort=[r for r in rows if r['day'].startswith(str(year))];ok=[r for r in cohort if 'nets' in r]
        reasons=[]
        if len(cohort)<40:reasons.append('CADENCE')
        if len(ok)!=len(cohort):reasons.append('SOURCE_OR_SESSION_UNRESOLVED')
        if any(not r['valid_geometry'] for r in ok):reasons.append('INVALID_GEOMETRY')
        ratio=median(r['friction'] for r in ok)/median(r['natural_sl'] for r in ok) if ok else None
        keep=sum(r['pass12'] for r in ok)/len(cohort) if cohort else 0
        if ratio is None or ratio>.12:reasons.append('SCALE')
        if keep<.5:reasons.append('COST_REJECTION_GT50')
        net={c:mean(r['nets'][c] for r in ok) if ok else None for c in CELLS}
        mf=mean(r['execution_friction'] for r in ok) if ok else None
        for c in CELLS:
            if net[c] is None or net[c]<=0:reasons.append('ECONOMIC_'+c)
            elif net[c]<mf:reasons.append('NET_SMALLER_THAN_FRICTION_'+c)
        annual.append(dict(year=year,raw_signals=len(cohort),priced=len(ok),natural_sl_median=median(r['natural_sl'] for r in ok) if ok else None,
            friction_median=median(r['friction'] for r in ok) if ok else None,scale_ratio=ratio,
            pass12_fraction=keep,net_mean=net,mean_execution_friction=mf,reasons=reasons))
    return dict(annual=annual,pass_stage0=all(not r['reasons'] for r in annual),measurements=rows)


if __name__=='__main__':
    run_phase1()

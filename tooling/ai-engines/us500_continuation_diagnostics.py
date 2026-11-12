"""Fixed-horizon diagnostics, not simulated stop/exit policies or edge approval."""
from collections import Counter,deque
from decimal import Decimal as D
from fractions import Fraction as F

M=60000
FIELDS=('move_R','spread_R','reference_R','stress_R')


def components(entry,exit,side,atr):
    if side not in ('BUY','SELL') or not D(str(atr)).is_finite() or D(str(atr))<=0:
        raise ValueError('diagnostic_side_or_atr')
    eb,ea,xb,xa=(D(str(entry[0]['open'])),D(str(entry[1]['open'])),
                 D(str(exit[0]['open'])),D(str(exit[1]['open'])))
    if not 0<eb<=ea or not 0<xb<=xa:raise ValueError('diagnostic_quote_spread')
    sign=1 if side=='BUY' else -1;unit=2*D(str(atr))
    move=sign*((xb+xa)-(eb+ea))/2;spread=(ea-eb+xa-xb)/2
    direct=xb-ea if side=='BUY' else eb-xa
    if F(move)-F(spread)!=F(direct):raise ValueError('markout_cost_bridge')
    return dict(move_points=move,spread_points=spread,reference_points=direct-D('.5'),stress_points=direct-D('1.5'),
                move_R=move/unit,spread_R=spread/unit,reference_R=(direct-D('.5'))/unit,stress_R=(direct-D('1.5'))/unit)


def markout(pairs,minutes,decision,side,atr,horizon):
    if horizon not in (15,30,60):raise ValueError('registered_diagnostic_horizon')
    start=decision+M;end=start+horizon*M;day=minutes.get(start,{}).get('day')
    span=range(decision,end+M,M)
    base=dict(entry=start,endpoint=end)
    if day is None or any(t not in minutes or minutes[t]['day']!=day for t in span):
        return dict(base,status='outside_session')
    if any(t not in pairs for t in span):return dict(base,status='missing_quotes')
    return dict(base,status='known',**components(pairs[start],pairs[end],side,atr))


def control_events(prepared):
    history=deque(maxlen=20);out=[]
    for e in prepared['snapshots'].values():
        m=e['m15']
        if not m:
            if e['slot']%15==0:history.clear()
            continue
        if m['previous'] is None:history.clear()
        if (len(history)==20 and m['atr']>0 and not e['blocked'] and e['full_session']
                and e['slot'] in range(30,331,15)):
            upper=max(b['high'] for b in history);lower=min(b['low'] for b in history)
            if F(lower)-F('.1')*F(m['atr'])<=F(m['close'])<=F(upper)+F('.1')*F(m['atr']):
                out.append(dict(t=e['t'],day=e['day'],slot=e['slot'],atr=m['atr']))
        history.append(m)
    return out


def excursion(trade,pairs,slip):
    if trade['unresolved']:return dict(status='unknown_held_path')
    start=trade['entry_time'];end=trade['exit_ns']//(M*1000000)*M
    stamps=range(start,end,M)
    if any(t not in pairs for t in stamps):raise ValueError('known_trade_prefix_missing')
    side=trade['side'];entry=D(str(trade['entry']));quantity=D(str(trade['quantity']))
    unit=D(str(trade['planned_risk']))/quantity
    if unit<=0:raise ValueError('invalid_planned_risk_unit')
    final=D(str(trade['net']))/quantity;values=[D(0),final]
    for t in stamps:
        b,a=pairs[t]
        if side=='BUY':values.extend((D(str(b['high']))-entry-D(slip),D(str(b['low']))-entry-D(slip)))
        elif side=='SELL':values.extend((entry-D(str(a['low']))-D(slip),entry-D(str(a['high']))-D(slip)))
        else:raise ValueError('diagnostic_trade_side')
    favorable=max(values)/unit;adverse=-min(values)/unit
    return dict(status='known_prefix_envelope',net_R=final/unit,favorable_R=favorable,adverse_R=adverse,
                loser=final<0,loser_after_half_R=final<0 and favorable>=D('.5'),
                omitted_exit_minute=True)


def pool_add(pool,event,value):
    if value['status']!='known':return
    if event['day'] in pool['days']:raise ValueError('duplicate_control_day_slot')
    pool['n']+=1
    pool['days'][event['day']]=value
    for f in FIELDS:pool['sums'][f]+=value[f]


def new_pool():return dict(n=0,sums={f:D(0) for f in FIELDS},days={})


def contrast(pool,day,value):
    own=pool['days'].get(day);n=pool['n']-int(own is not None)
    if value['status']!='known' or not n:return dict(status='no_paired_control',control_n=n)
    mean={f:(pool['sums'][f]-(own[f] if own else 0))/n for f in FIELDS}
    return dict(status='paired_descriptive',control_n=n,control_mean=mean,
                excess_R={f:value[f]-mean[f] for f in FIELDS})


def summarize(rows):
    known=[r for r in rows if r['status']=='known'];paired=[r for r in known if r.get('control',{}).get('status')=='paired_descriptive']
    means={f:sum((r[f] for r in known),D(0))/len(known) if known else None
           for f in (*FIELDS,'move_points','spread_points','reference_points','stress_points')}
    return dict(total=len(rows),status_counts=dict(Counter(r['status'] for r in rows)),known=len(known),means=means,
        reference_positive=sum(r['reference_R']>0 for r in known),stress_positive=sum(r['stress_R']>0 for r in known),
        paired=len(paired),paired_excess_means={f:sum((r['control']['excess_R'][f] for r in paired),D(0))/len(paired) if paired else None for f in FIELDS},
        paired_control_means={f:sum((r['control']['control_mean'][f] for r in paired),D(0))/len(paired) if paired else None for f in FIELDS})

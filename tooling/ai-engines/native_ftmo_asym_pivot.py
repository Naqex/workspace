"""Preregistered Development-only asymmetry screen; no lifecycle or broker calls."""

from collections import Counter, defaultdict
from datetime import timedelta
from pathlib import Path
import sys

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
import pyarrow as pa
import pyarrow.parquet as pq

from native_ftmo_monfri_seal import ASSETS, AUDIT, FRAMES, ROOT, START, STOP, read, sha, write
from native_ftmo_monfri_screen import (
    BOOKS, DAY, HOUR, NEW_YORK, SCENARIOS, Intent, Market, bars, crossing,
    daily_limit, date, ema, results, select, simulate, stage0, wilder,
)
from native_ftmo_asym_forensics import LOCK_PIN, PARENT_PIN

FX = ('EURUSD', 'USDJPY', 'EURJPY', 'GBPUSD')
INTRADAY = (*FX, 'XAUUSD')
CASES = {'ASYM_A': ('US500.cash',), 'ASYM_B': FX, 'ASYM_B_NO_CARRY': FX, 'ASYM_C': INTRADAY}
PROTOCOL = ROOT / 'planning/research/BOTTLENECK2-ASYMMETRIC-PIVOT-PROTOCOL-20261119.md'
BASE_PIN = '653cddf48398e5232ddc2d2ce11e3da63210a51264d471fcd8a98eda627fc53a'
BASE_END = 1704067200
CLUSTERS = {'A':range(2018,2021), 'B':range(2021,2025)}


def sma(values, size):
    out = np.full(len(values), np.nan)
    if len(values) >= size:
        out[size-1:] = sliding_window_view(values, size).mean(axis=1)
    return out


def rsi_two(close):
    change = np.r_[np.nan,np.diff(close)]
    up = wilder(np.maximum(change,0),2)
    down = wilder(np.maximum(-change,0),2)
    ratio = np.divide(up, up+down, out=np.full(len(close), .5), where=up+down>0)
    ratio[:2] = np.nan
    return 100 * ratio


def prior_day(frame, when):
    return int(np.searchsorted(frame['complete'],when,side='right')-1)


def new_york_offset(utc):
    return utc.astimezone(NEW_YORK).utcoffset()+timedelta(hours=7)


def wall_to_utc(t):
    wall = date(t)
    for offset in (2,3):
        option = wall - timedelta(hours=offset)
        if new_york_offset(option)==timedelta(hours=offset):
            return option
    raise ValueError('ambiguous or unavailable server conversion')


def index_signals(asset, d):
    long_ma = sma(d['c'],200)
    oscillator = rsi_two(d['c'])
    exit_ma = sma(d['c'],5)
    signals = []
    for i in range(199,len(d['t'])):
        when = int(d['t'][i]+DAY)
        if START<=when<STOP and d['c'][i]>long_ma[i] and oscillator[i]<10<=oscillator[i-1]:
            signals.append(Intent(asset,'ASYM_A','D1',when,1,float(d['atr'][i])))
    return signals, exit_ma


def macro_signals(asset, source, market):
    d = source['D1']
    fast, slow = sma(d['c'],50),sma(d['c'],200)
    found, levels = [], {}
    for frame,n in (('H4',20),('D1',10)):
        f = source[frame]
        levels[frame] = []
        for i in range(34,len(f['t'])):
            at = int(f['complete'][i])
            if not START<=at<STOP:
                continue
            upper,lower = max(f['h'][i-n:i]),min(f['l'][i-n:i])
            levels[frame].append((at,float(f['c'][i]),float((upper+lower)/2)))
            j=prior_day(d,at)
            if j<199 or f['atr'][i-1]>=np.median(f['atr'][i-21:i-1]):
                continue
            side = int(fast[j]>slow[j] and f['c'][i]>upper)-int(fast[j]<slow[j] and f['c'][i]<lower)
            if side:
                swap = market.spec['swap_long' if side==1 else 'swap_short']
                affordable = max(0,-3*swap*market.spec['point']) <= .05*d['atr'][j]
                found.append((Intent(asset,'BREAKOUT',frame,at,side,float(f['atr'][i])),bool(affordable)))
    levels |= {frame+'_times':np.asarray([v[0] for v in seq],dtype='int64') for frame,seq in list(levels.items())}
    return found, levels


def intraday_signals(asset, source):
    h, d = source['H4'], source['D1']
    day_ema = ema(d['c'],50)
    seen=set()
    found=[]
    for i in range(15,len(h['t'])):
        at=int(h['complete'][i])
        if not START<=at<STOP or date(at).weekday()>4:
            continue
        utc=wall_to_utc(at)
        if not 8<=utc.hour<=15 or utc.date() in seen:
            continue
        j=prior_day(d,at)
        if j<50 or h['tr'][i]<1.5*h['atr'][i-1]:
            continue
        close=h['c'][i]
        high,low=h['h'][i],h['l'][i]
        width=high-low
        if width<=0:
            continue
        side=int(day_ema[j]>day_ema[j-1] and close>max(h['h'][i-5:i]) and close>=high-.2*width)
        side-=int(day_ema[j]<day_ema[j-1] and close<min(h['l'][i-5:i]) and close<=low+.2*width)
        if side:
            seen.add(utc.date())
            found.append(Intent(asset,'ASYM_C','H4',at,side,float(h['atr'][i])))
    return found


def path(m, intent, scenario, markout, exit_ma=None):
    """Single D1-only or exact H1 intraday path."""
    daily = exit_ma is not None
    b=m.feed;ts=b['t'];i=int(np.searchsorted(ts,intent.at))
    if i>=len(ts) or ts[i]-intent.at > (0 if daily else HOUR):
        return None,'NO_CAUSAL_ENTRY'
    start=int(ts[i])
    if daily:
        day=date(start).weekday()
        if day>=4:
            return None,'FRIDAY_OR_WEEKEND_ENTRY'
        # Friday open liquidation. Max three held bars; markout is next open.
        deadline=start+min(4-day,1 if markout else 3)*DAY
        bar_width=DAY
    else:
        if not 8<=wall_to_utc(start).hour<=15 or wall_to_utc(start).date()!=wall_to_utc(intent.at).date():
            return None,'OUTSIDE_LONDON_NY_ENTRY'
        deadline=daily_limit(start)
        bar_width=HOUR
    if deadline>=STOP or start>=deadline:
        return None,'OUTSIDE_DEVELOPMENT_DEADLINE'
    entry=float(b['o'][i])
    slip=m.slip if scenario=='Stress-Real' else 0.
    side=intent.side
    ent=entry,side,slip
    stop=entry+m.spread/2-side*intent.distance
    stop_bid=stop-(m.spread if side<0 else 0)
    if side*(entry-stop_bid)<=0:
        return None,'STOP_ALREADY_CROSSED'
    initial_risk=-m.roundtrip(ent,start,stop_bid,slip,0)['net']
    fixed_cost=m.roundtrip(ent,start,entry,slip,0)
    funding=0.;last=start
    series=[]
    for j in range(i,len(ts)):
        t=int(ts[j])
        if t>deadline or (t-last > (DAY if daily else 2*HOUR)):
            return None,'MISSING_D1_OR_H1_PATH'
        bid=float(b['o'][j])
        if daily and t>last:
            funding+=m.swap(t,bid,side)
        last=t
        structural = daily and j>i and b['c'][j-1]>exit_ma[j-1]
        if t==deadline or (not markout and structural):
            found=('MARKOUT' if markout else 'CUTOFF' if t==deadline else 'REBOUND',bid,True)
        elif markout:
            continue
        else:
            found=crossing(side,bid,float(b['l'][j]),float(b['h'][j]),stop,None,m.spread)
        if found is None:
            close_t=t+bar_width
            series.append((close_t,m.roundtrip(ent,close_t,float(b['c'][j]),slip,funding,closed=True)['net']))
            continue
        why,price,open_fill=found
        end=t if open_fill else t+bar_width
        p=m.roundtrip(ent,end,price,slip,funding,closed=not open_fill)
        series.append((end,p['net']))
        return dict(asset=intent.asset,family=intent.family,frame=intent.frame,decision=intent.at,entry=start,exit=end,
                    side=side,year=date(start).year,reason=why,initial_risk=initial_risk,
                    natural_risk_usd_per_lot=abs(entry-stop_bid)*m.usd_unit(start,entry),
                    natural_stop_crossed_at_entry=False,margin=m.margin(start,entry),
                    friction_at_entry=sum(fixed_cost[k] for k in ('spread','commission','slippage')),
                    path=series,**p),None
    return None,'DEVELOPMENT_END'


def base_guard(tape):
    if sha(tape)!=BASE_PIN:
        raise ValueError('BASE_GUARD Dev tape hash drift')
    pnl=defaultdict(float)
    rows=read(tape)
    for t in rows:
        if not START*1000<=t['decision_msc']<=t['entry_msc']<=t['exit_msc']<BASE_END*1000:
            raise ValueError('BASE_GUARD tape outside Development overlap')
        pnl[t['exit_msc']//(DAY*1000)] += t['reference']['SYM']['net_R']
    return pnl,len(rows)


def correlation(rows, base):
    pnl=defaultdict(float)
    for t in rows:
        exited=wall_to_utc(t['exit']).timestamp()
        if START<=exited<BASE_END:
            pnl[int(exited)//DAY]+=t['net']*t['lots']/50
    days=[t for t in range(START//DAY,BASE_END//DAY) if date(t*DAY).weekday()<5]
    x=[pnl[t] for t in days];y=[base.get(t,0.) for t in days]
    return dict(r=float(np.corrcoef(x,y)[0,1]) if np.std(x)>0 and np.std(y)>0 else None,
                weekday_observations=len(days),candidate_active_days=sum(z!=0 for z in x),
                base_active_days=sum(z!=0 for z in y),shared_active_days=sum(a!=0 and b!=0 for a,b in zip(x,y)))


def top2(rows, budget):
    winners = sorted([r['net']*r['lots']/(budget*.005) for r in rows if r['net']>0],reverse=True)
    total=sum(r['net']*r['lots']/(budget*.005) for r in rows)
    return dict(top2_gross_winner_share=sum(winners[:2])/sum(winners) if winners else None,
                net_R_without_top2=total-sum(winners[:2]))


def gates(value, minimum):
    raw=value['stage0'];m=value['book']['10000']['metrics'];t=m['ALL']
    gross={c:sum(raw['by_year'][str(y)]['totals_R']['gross'] for y in years) for c,years in CLUSTERS.items()}
    return dict(gross_dual_cluster=all(x>0 for x in gross.values()),
                net_dual_cluster=min(m[c]['net_R_per_year'] for c in CLUSTERS)>0,stage0=raw['gate'],
                velocity=t['net_R_per_year']>=minimum,drawdown=t['max_drawdown_R']<=20,
                concentration=t['net_R_without_top2']>0 and (t['top2_gross_winner_share'] or 0)<=.5)


def run(parent, out, tape):
    lock=parent/'NATIVE_FTMO_HOLDOUT_LOCK.json'
    if sha(lock)!=LOCK_PIN or sha(parent/'manifest.json')!=PARENT_PIN or sha(ROOT/'planning/research'/lock.name)!=LOCK_PIN:
        raise ValueError('sealed parent unavailable')
    census=read(lock)
    if census['audit_sha256']!=sha(AUDIT) or census['status']!='LOCKED_HOLDOUT':
        raise ValueError('audit or fence drift')
    f=out/'FORENSICS.json'
    h=read(f)
    if h['parent_manifest_sha256']!=PARENT_PIN or h['holdout_lock_sha256']!=LOCK_PIN:
        raise ValueError('forensics is not tied to the parent')
    sources={}
    for asset in (*INTRADAY,'US500.cash'):
        sources[asset]={}
        for frame in (('D1',) if asset=='US500.cash' else FRAMES):
            info=census['series'][asset][frame]
            p=parent/'development'/f'{asset}-{frame}.parquet'
            if info['development_file']!=p.name or info['development_sha256']!=sha(p):
                raise ValueError('Development file drift')
            sources[asset][frame]=bars(p,FRAMES[frame])
    base,n_base=base_guard(tape)
    audit=read(AUDIT)['symbols']
    groups={}
    data=[]
    for case,assets in CASES.items():
        case_out=groups[case]={}
        qualifying={}
        for scenario in SCENARIOS:
            rejects=defaultdict(Counter);raw_count=Counter()
            s0=defaultdict(list);captured=defaultdict(list)
            for asset in assets:
                src=sources[asset]
                market=Market(asset,src['D1' if case=='ASYM_A' else 'H1'],audit[asset],sources['USDJPY']['H1'])
                exit_ma=None
                if case=='ASYM_A':
                    signals,exit_ma=index_signals(asset,src['D1'])
                elif case.startswith('ASYM_B'):
                    eligible,mids=macro_signals(asset,src,market)
                    signals=[s for s,c in eligible if case=='ASYM_B_NO_CARRY' or c]
                    rejects[asset]['CARRY_EXCLUDED']=len(eligible)-len(signals)
                else:
                    signals=intraday_signals(asset,src)
                raw_count[asset]=len(signals)
                for intent in signals:
                    for mark,store in ((True,s0),(False,captured)):
                        if case.startswith('ASYM_B'):
                            row,why=simulate(market,intent,mids,scenario,'Mon-Fri',markout=mark)
                        else:
                            row,why=path(market,intent,scenario,mark,exit_ma=exit_ma)
                        if row:
                            if not START<=row['decision']<=row['entry']<=row['exit']<STOP or (case=='ASYM_C' and row['swap']):
                                raise ValueError('fill hour, position or swap fence')
                            store[asset].append(row|{'family':case})
                        else:
                            rejects[asset][('STAGE0/' if mark else 'SL_ACTIVE/')+why]+=1
            views={}
            case_out[scenario]=dict(raw_counts=dict(raw_count),rejects={k:dict(v) for k,v in rejects.items()},views=views)
            for name,sub in {'PORTFOLIO':assets,**{a:(a,) for a in assets}}.items():
                raw=[r for a in sub for r in s0[a]]
                resolved=[r for a in sub for r in captured[a]]
                v=views[name]=dict(stage0=stage0(raw,sub),book={})
                for budget in BOOKS:
                    chosen,skips=select(resolved,budget)
                    b=v['book'][str(budget)]=results(chosen,budget,sub)|{'skips':skips}
                    b['metrics']['ALL'].update(top2(chosen,budget))
                    if budget==10000:
                        v['base_guard_daily_exit_correlation']=correlation(chosen,base)
                    if name=='PORTFOLIO':
                        data.extend({k:v for k,v in t.items() if k!='path'} | {'scenario':scenario,'book':budget} for t in chosen)
                if scenario=='Stress-Real':
                    check=gates(v,15 if len(sub)>1 else 5)
                    v['gates']=check
                    v['verdict']='CANDIDATE_FOR_COMBINATION' if all(check.values()) and case!='ASYM_B_NO_CARRY' else 'REJECTED_AT_DEV'
                    if name!='PORTFOLIO' and v['verdict']=='CANDIDATE_FOR_COMBINATION':
                        qualifying[name]=v['book']['10000']['metrics']['ALL']['net_R_per_year']
        case_out['qualifying_asset_sleeves']=qualifying
        accepted=case_out['Stress-Real']['views']['PORTFOLIO']['verdict']=='CANDIDATE_FOR_COMBINATION' or bool(qualifying)
        case_out['verdict']='CANDIDATE_FOR_COMBINATION' if accepted else 'REJECTED_AT_DEV'
        print(case,case_out['verdict'],[(k,round(case_out['Stress-Real']['views']['PORTFOLIO']['book']['10000']['metrics'][k]['net_R_per_year'],3))
            for k in ('A','B','ALL')],flush=True)
    accepted=[k for k in ('ASYM_A','ASYM_B','ASYM_C') if groups[k]['verdict']=='CANDIDATE_FOR_COMBINATION']
    rate=sum(max(sum(groups[k]['qualifying_asset_sleeves'].values()),
                 groups[k]['Stress-Real']['views']['PORTFOLIO']['book']['10000']['metrics']['ALL']['net_R_per_year']
                 if groups[k]['Stress-Real']['views']['PORTFOLIO']['verdict']=='CANDIDATE_FOR_COMBINATION' else 0.) for k in accepted)
    killed=not accepted or rate<10
    write(out/'SCREEN.json',dict(schema='asym-pivot-dev-v1',holdout_sha256=LOCK_PIN,preregistered_sha256=sha(PROTOCOL),
                                 forensics_sha256=sha(f),script_sha256=sha(Path(__file__)),base_guard=dict(tape_sha256=BASE_PIN,
                                 exit_marks='V19 Dev OLHC PRIMARY SYM fixed-risk trade proxy',trades=n_base,end_exclusive=BASE_END),
                                 cases=groups,qualifying_mechanisms=accepted,total_annual_R_qualifiers=rate,
                                 kill_switch='KILL_SWITCH_TRIGGERED' if killed else 'OPEN_FOR_COMBINATION_REVIEW',
                                 research_state='OHLC_STANDARD_SEARCH_EXHAUSTED' if killed else 'DEVELOPMENT_CANDIDATES_PRESENT',
                                 holdout_prices_opened=False,native_us500_frames_opened=['D1']))
    pq.write_table(pa.Table.from_pylist(data),out/'PIVOT_TRADES.parquet',compression='zstd')


if __name__=='__main__':
    run(*map(Path,sys.argv[1:]))

"""Pass 6 Development-only first-touch and paired execution audits."""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import correlation

import numpy as np

import pass5_usdjpy_tokyo as base
from candle_source_provenance import PRICE_KEYS, explicit_candles
from quant_core.market_data_store import Checksums
from selective_win_diagnosis import classify

MINUTE = 60
PROTOCOL = 'e6cec0a5332f4d88ce2b8e2a7c2f6a6dceaac89e'
GOLD_CACHE_SHA = '5a5a23cbe71d63164da20b81496103278de16d11087bbbe1062183b8b05b2cd7'
SL = 'SL_GAP_OR_TOUCH'


def stamp(day, hour, minute, zone):
    return int(datetime(day.year, day.month, day.day, hour, minute, tzinfo=zone).timestamp())


def stop_price(bid, ask, side, edge, *, entry_bar=False):
    if side == 1 and bid.l <= edge + 1e-10:
        return edge if entry_bar else min(edge, bid.o)
    if side == -1 and ask.h >= edge - 1e-10:
        return edge if entry_bar else max(edge, ask.o)
    return None


def entries(bid, ask, top, bottom):
    if ask.h >= top - 1e-10:
        yield 1, max(top, ask.o), bottom
    if bid.l <= bottom + 1e-10:
        yield -1, min(bottom, bid.o), top


def cash(gross, spread, comm, slip, unit):
    cost = spread + comm + slip
    return dict(gross=gross, spread=spread, commission=comm, slippage=slip, swap=0.,
                cost=cost, cost_pips=cost/unit, net=gross-cost,
                gross_pips=gross/unit, net_pips=(gross-cost)/unit)


def jpy_mark(side, entry_mid, exit_mid, half_in, half_out, entry_addon):
    usd = 100_000 / exit_mid
    return cash(side*(exit_mid-entry_mid)*usd, (half_in+half_out)*usd,
                5., (.004+entry_addon)*usd, usd*.01)


def gold_mark(side, entry_mid, exit_mid, half_in, half_out, entry_addon=0.):
    entry_exec = entry_mid + side*half_in
    exit_exec = exit_mid - side*half_out
    return cash(side*(exit_mid-entry_mid)*100, (half_in+half_out)*100,
                .000007*(entry_exec+exit_exec)*100, (.40+entry_addon)*100, 100.)


def shift(bid, spread):
    return base.Bar(bid.o+spread, bid.h+spread, bid.l+spread, bid.c+spread)


def value_stop(day, at, flat, step, setup, quote, mark, extra_slip=0.):
    side, executed, edge = setup
    b, a = quote(at)
    half_in = (a.o-b.o)/2
    entry_mid = executed-side*half_in
    risk_price = abs(executed+side*extra_slip-edge)
    unit = 100_000/entry_mid if mark is jpy_mark else 100.
    risk = risk_price*unit
    if risk <= 0:
        raise ValueError('Zero structural stop')
    entry_stop = stop_price(b,a,side,edge,entry_bar=True)
    low = high = mark(side,entry_mid,entry_mid,half_in,half_in,extra_slip)['net']
    end = at+step
    if entry_stop is not None:
        exit_exec, final_half, reason = entry_stop, half_in, SL
    else:
        for t in range(at+step, flat, step):
            b,a = quote(t)
            half = (a.o-b.o)/2
            stop = stop_price(b,a,side,edge)
            if stop is not None:
                exit_exec, final_half, reason = stop, half, SL
                end = t if stop == (b.o if side==1 else a.o) else t+step
                break
            # For paired Candles, use the liquidation side extremes. Conversion
            # at the minute opening spread is a diagnostic approximation.
            for px in ((b.h,b.l) if side==1 else (a.h,a.l)):
                val = mark(side,entry_mid,px+side*half,half_in,half,extra_slip)['net']
                low,high=min(low,val),max(high,val)
        else:
            b,a=quote(flat)
            exit_exec, final_half, reason = (b.o if side==1 else a.o),(a.o-b.o)/2,'HARD_FLAT'
            end=flat
    out = mark(side,entry_mid,exit_exec+side*final_half,half_in,final_half,extra_slip)
    post = dict(net_R=out['net']/risk, swap_R=0., mfe_R=max(0.,high/risk,out['net']/risk),
                mae_R=max(0.,-low/risk,-out['net']/risk),
                holding_hours=max(0.,(end-at-step)/base.HOUR),
                calendar_exit=reason=='HARD_FLAT', paired_net_R=None)
    return dict(day=base.date(day).date().isoformat(), year=base.date(day).year,
                side=side, reason=reason, entry_bar_forced_stop=entry_stop is not None,
                entry=at,exit=end,entry_price=executed,initial_risk_usd=risk,
                gross_R=out['gross']/risk,friction_R=out['cost']/risk,**post,
                winner_label=classify(post),conditional_geometry_label=classify(post|{'calendar_exit':False}))


def ledger_stats(rows):
    rows = sorted(rows,key=lambda r:r['day'])
    report=base.sl_summary(rows)
    report['winrate']=sum(x['net_R']>0 for x in rows)/len(rows) if rows else None
    report['years']={y:base.sl_summary([x for x in rows if x['year']==y]) for y in base.YEAR}
    report['clusters']={k:base.sl_summary([x for x in rows if x['year'] in ys]) for k,ys in base.CLUSTERS.items()}
    report['net_R_per_year']=report['net_R']/len(base.YEAR)
    report['forced_stops']=sum(r.get('entry_bar_forced_stop',False) for r in rows)
    return report


def weekdays():
    return (t for t in range(base.START,base.STOP,base.DAY) if base.date(t).weekday()<5)


def jpy_h1_stress(hourly, spread_pips, addon_pips):
    spread=spread_pips*.01
    quote=lambda t:(hourly[t],shift(hourly[t],spread))
    out=[]
    for day in weekdays():
        if any(t not in hourly for t in range(day,day+10*base.HOUR,base.HOUR)):
            continue
        box=[hourly[day+i*base.HOUR] for i in range(3)]
        top=max(x.h for x in box)+.0015
        bottom=min(x.l for x in box)+.0015
        flat=base.hard_flat(base.date(day))
        for t in range(day+3*base.HOUR,day+10*base.HOUR,base.HOUR):
            options=list(entries(*quote(t),top,bottom))
            if not options:
                continue
            if all(k in hourly for k in range(day,max(flat,t+9*base.HOUR)+base.HOUR,base.HOUR)):
                out.append(min((value_stop(day,t,flat,base.HOUR,setup,quote,jpy_mark,addon_pips*.01)
                                for setup in options),key=lambda x:x['net_R']))
                out[-1]['dual_entry']=len(options)==2
            break
    return out


def bound_usdjpy_packets(root):
    packets={}
    for name in ('jpy-tokyo-source-v1','jpy-postfix-source-v1'):
        folder=root/name
        receipt=base.read(folder/'result.json')
        for locator,digest in receipt['raw_bindings'].items():
            path=Path(locator)
            parts=path.stem.split('%2F')
            if parts[:3]!=['candles','minute','USD-JPY'] or len(parts)!=7:
                raise ValueError('Unexpected USDJPY source')
            side,y,m,d=parts[3:]
            if not 2018<=int(y)<=2024:
                continue
            at=int(datetime(int(y),int(m),int(d),tzinfo=timezone.utc).timestamp())
            packets.setdefault(at,{})[side]=(folder/'cache'/path.name,digest)
    return packets


def explicit_packet(path, digest, start):
    if not base.START<=start<start+base.DAY<=base.STOP or start % base.DAY:
        raise ValueError('USDJPY source day outside Development fence')
    if base.sha(path)!=digest:
        raise ValueError('USDJPY packet checksum')
    payload=base.read(path)
    first=payload['timestamp']
    last=first+sum(payload['times'])*payload['shift']
    if not start*1000<=first<=last<(start+base.DAY)*1000:
        raise ValueError('USDJPY packet clock outside permitted source day')
    result=explicit_candles(payload)
    if any(not start*1000<=t<(start+base.DAY)*1000 for t in result):
        raise ValueError('USDJPY packet extends outside permitted Development day')
    return {t//1000:base.Bar(*(float(row[k]) for k in PRICE_KEYS)) for t,row in result.items()}


def jpy_m1(root, reference):
    counters=defaultdict(Counter)
    rows=[]
    for day,packet in sorted(bound_usdjpy_packets(root).items()):
        counter=counters[base.date(day).year]
        counter['candidate_days']+=1
        if set(packet)!={'BID','ASK'}:
            counter['unpaired_source_day']+=1
            continue
        streams=[explicit_packet(*packet[s],day) for s in ('BID','ASK')]
        quote=lambda t:(streams[0][t],streams[1][t])
        flat=base.hard_flat(base.date(day))
        path=range(day,flat+MINUTE,MINUTE)
        if any(t not in streams[0] or t not in streams[1] for t in path):
            counter['missing_one_or_more_explicit_minutes']+=1
            continue
        if any(a.o<b.o or a.c<b.c for t in path for b,a in [quote(t)]):
            counter['invalid_side_pair']+=1
            continue
        counter['complete_days']+=1
        box=[quote(t) for t in range(day,day+3*base.HOUR,MINUTE)]
        top=max((b.h+a.h)/2 for b,a in box)
        bottom=min((b.l+a.l)/2 for b,a in box)
        for at in range(day+3*base.HOUR,day+10*base.HOUR,MINUTE):
            options=list(entries(*quote(at),top,bottom))
            if options:
                if len(options)==2:
                    counter['dual_first_touch']+=1
                row=min((value_stop(day,at,flat,MINUTE,v,quote,jpy_mark) for v in options),
                         key=lambda r:r['net_R'])
                rows.append(row)
                counter['fills']+=1
                break
        else:
            counter['no_touch']+=1
    paired_m1=[r for r in rows if r['day'] in reference]
    paired_h1=[reference[r['day']] for r in paired_m1]
    return dict(coverage=counters,m1=ledger_stats(rows),paired_m1=ledger_stats(paired_m1),
                paired_h1=ledger_stats(paired_h1),
                matched_same_side=sum(x['side']==y['side'] for x,y in zip(paired_m1,paired_h1))),rows


def gold_columns(folder):
    manifest = folder/'manifest.json'
    if base.sha(manifest)!=GOLD_CACHE_SHA:
        raise ValueError('Unregistered Gold cache manifest')
    m=base.read(manifest)
    if (m['scope_end_exclusive'],m['time_unit'],m['price_unit'])!=(base.STOP,'UTCseconds','.001'):
        raise ValueError('Unsealed Gold cache clock')
    checks=Checksums()
    clocks=folder/'times.bin'
    checks.verify(clocks,m['files']['times.bin'])
    t=np.memmap(clocks,mode='r',dtype='<i8')
    if len(t)!=m['rows'] or not len(t) or t[-1]>=base.STOP or np.any(np.diff(t)<=0) or np.any(t%60):
        raise ValueError('Gold clock is outside Development fence')
    i=int(t.searchsorted(base.START))
    values=[]
    for key in 'ohlc':
        p=folder/(key+'.bin')
        checks.verify(p,m['files'][p.name])
        a=np.memmap(p,mode='r',dtype='<i4')
        if len(a)!=len(t):
            raise ValueError('Gold column size mismatch')
        values.append(a[i:])
    o,h,l,c=values
    if np.any(l<=0) or np.any(l>np.minimum(o,c)) or np.any(h<np.maximum(o,c)):
        raise ValueError('Invalid Gold OHLC')
    return t[i:],np.column_stack(values)


def gold_stage0(times, values, spread):
    events=[]
    coverage=defaultdict(Counter)
    for day in weekdays():
        d=base.date(day)
        c=coverage[d.year]
        c['weekdays']+=1
        start=stamp(d,3,0,base.HELSINKI)
        activation=stamp(d,6,0,base.HELSINKI)
        expiry=stamp(d,10,0,base.LONDON)
        flat=stamp(d,18,55,base.HELSINKI)
        end=max(flat,expiry+8*base.HOUR)
        if not base.START<=start<=end<base.STOP or not base.valid_exit(activation,end,day):
            c['outside_session']+=1
            continue
        i,j=np.searchsorted(times,[start,end+MINUTE])
        clock=times[i:j]
        if len(clock)!=(end-start)//MINUTE+1:
            c['missing_minutes']+=1
            continue
        c['complete_days']+=1
        bars=values[i:j]
        def quote(t):
            b=base.Bar(*(bars[(t-start)//MINUTE]/1000))
            return b,shift(b,spread)
        box=bars[:(activation-start)//MINUTE]
        top=float(box[:,1].max())/1000+spread/2
        bottom=float(box[:,2].min())/1000+spread/2
        scan=bars[(activation-start)//MINUTE:(expiry-start)//MINUTE]
        up=scan[:,1]/1000+spread>=top-1e-10
        down=scan[:,2]/1000<=bottom+1e-10
        c['any_dual_touch']+=int(np.any(up&down))
        hits=np.flatnonzero(up|down)
        if not len(hits):
            c['no_touch']+=1
            continue
        at=activation+int(hits[0])*MINUTE
        setups=list(entries(*quote(at),top,bottom))
        if len(setups)==2:
            c['dual_first_touch']+=1
            continue
        side,execution,edge=setups[0]
        mid=execution-side*spread/2
        endpoints=(at+MINUTE+4*base.HOUR,at+MINUTE+8*base.HOUR,flat)
        marks={}
        for h,t in zip(base.HORIZONS,endpoints):
            exit_mid=quote(t)[0].o+spread/2
            marks[h]={'Breakout':gold_mark(side,mid,exit_mid,spread/2,spread/2),
                      'Fade':gold_mark(-side,mid,exit_mid,spread/2,spread/2)}
        events.append(dict(day=d.date().isoformat(),year=d.year,side=side,at=at,flat=flat,start=start,
                           setup=setups[0],markouts=marks,width_over_atr=None,
                           natural_stop_pips=abs(execution-edge)))
        c['valued']+=1
    return events,coverage


def win_flip(rows, originals):
    table={r['day']:r['net_R'] for r in rows}
    scores=Counter()
    for k in originals:
        x=table.get(k)
        scores['missing' if x is None else 'loss' if x<0 else 'win' if x>0 else 'flat']+=1
    return dict(scores)


def correlation_table(jpy, gold, gold_sl=None):
    u={r['day']:r['net_R'] for r in jpy}
    g={r['day']:r['net_R'] for r in gold_sl} if gold_sl is not None else {
        r['day']:r['markouts']['4h']['Breakout']['net']/(100*r['natural_stop_pips']) for r in gold}
    rows={}
    for grain in ('day','week'):
        buckets=defaultdict(lambda:[0.,0.])
        for j,series in enumerate((u,g)):
            for d,n in series.items():
                day=datetime.fromisoformat(d)
                label=d if grain=='day' else tuple(day.isocalendar()[:2])
                buckets[label][j]+=n
        values=list(buckets.values())
        for cohort,data in [('all',values),('USDJPY_negative',[p for p in values if p[0]<0])]:
            x,y=zip(*data) if data else ((),())
            rows[f'{grain}/{cohort}']=dict(n=len(data),pearson=correlation(x,y)
                                           if len(set(x))>1 and len(set(y))>1 else None)
    return rows



def gold_stop(events, times, values, spread):
    rows=[]
    for r in events:
        start=r['start']
        offset=int(times.searchsorted(start))
        def quote(t):
            q=base.Bar(*(values[offset+(t-start)//MINUTE]/1000))
            return q,shift(q,spread)
        day=int(datetime.fromisoformat(r['day']+'T00:00:00+00:00').timestamp())
        rows.append(value_stop(day,r['at'],r['flat'],MINUTE,r['setup'],quote,gold_mark))
    return rows


def eligible_gold(result):
    scale=result['friction_scale']
    return bool(result['pass_stage0'] and scale and scale['median_cost_over_median_stop_pct']<=12
                and scale['pass_share_at_12pct']>=.5)


def run(jobs, output):
    lock=base.ROOT/'planning/research/NATIVE_FTMO_HOLDOUT_LOCK.json'
    if base.sha(lock)!=base.LOCK_SHA:
        raise ValueError('Holdout lock changed')
    binding=base.read(lock)
    if base.sha(base.AUDIT)!=binding['audit_sha256']:
        raise ValueError('Target FTMO audit SHA changed')
    standard=base.read(base.AUDIT)['symbols']['XAUUSD']
    spread=standard['spread']['median']
    if standard['spec']['trade_contract_size']!=100 or standard['spec']['volume_min']!=.01:
        raise ValueError('Gold spec drift')
    old=jobs/'pass5-usdjpy-tokyo-box-20261120'
    old_receipt=base.read(old/'manifest.json')
    path=old/'verified/sl_active_ledger.json'
    if base.sha(path)!=old_receipt['files']['verified/sl_active_ledger.json']['sha256']:
        raise ValueError('Parent ledger checksum')
    ledger=base.read(path)
    reference={r['day']:r for r in ledger}
    winners=[r['day'] for r in ledger if r['conditional_geometry_label']=='LUCKY_NOISE_WIN']
    if len(reference)!=1645 or len(winners)!=405:
        raise ValueError('Parent ledger cohort drift')
    source=jobs/'bottleneck2-monfri-20261119/development'
    hourly=base.load_sealed(source,'H1',binding['series']['USDJPY']['H1'])
    seed=jobs/'challenge-discovery4-20261108/execution-v1'
    jpy_m1_stats,jpy_m1_rows=jpy_m1(seed,reference)
    stress={}
    scenarios={}
    for s,a in ((.30,0.),(.60,.50),(.60,1.),(.90,.50),(.90,1.)):
        key=f'{s:.2f}/{a:.2f}'
        rows=jpy_h1_stress(hourly,s,a)
        stress[key]=ledger_stats(rows)|{'original_lucky_noise_outcomes':win_flip(rows,winners),
                                        'ambiguous_entry_days':sum(r['dual_entry'] for r in rows)}
        scenarios[key]=rows
    adverse=stress['0.90/1.00']
    jpy_survived=all(x['net_R']>0 for x in adverse['clusters'].values())
    times,values=gold_columns(seed/'gold-continuous-B2-20261113-v1/source-cache')
    gold,coverage=gold_stage0(times,values,spread)
    gold_results={h:base.evaluate(gold,h) for h in base.HORIZONS}
    for z in gold_results.values():
        z['admitted']=eligible_gold(z)
    gold_pass=any(z['admitted'] for z in gold_results.values())
    gold_sl=gold_stop(gold,times,values,spread) if gold_pass else None
    min_lot=None
    if gold_sl is not None:
        min_lot={str(b):sum(.01*(r['initial_risk_usd']
                            +100*2*.20+100*.000007*2*r['entry_price'])<=b
                            for r in gold_sl) for b in (25,50)}
    pair=correlation_table(ledger,gold,gold_sl)
    summary=dict(schema='pass6-breakout-execution-v1',protocol_commit=PROTOCOL,
          holdout_lock_sha256=base.LOCK_SHA,holdout_price_files_read=0,order_send_count=0,
          jpy=dict(verdict='SURVIVED_HIRES_CHECK' if jpy_survived else 'FAILED_HIRES_ILLUSION',
                   verdict_basis='FULL_PERIOD_WORST_DECLARED_H1_STRESS; PARTIAL_DUKASCOPY_M1_RECONCILIATION',
                   pass5=ledger_stats(ledger),m1=jpy_m1_stats,stress=stress),
          gold=dict(verdict='XAUUSD_ADVANCE_SL_ACTIVE' if gold_pass else 'XAUUSD_REJECTED_AT_STAGE0',
                    m1_bid_rows=len(times),first=base.date(times[0]).isoformat(),last=base.date(times[-1]).isoformat(),
                    gold_cache_manifest_sha256=GOLD_CACHE_SHA,spread_proxy_usd_oz=spread,coverage=coverage,events=len(gold),
                    horizons=gold_results,sl_active=ledger_stats(gold_sl) if gold_sl is not None else None,
                    min_lot_fits_with_cost_allowance=min_lot),
          portfolio=dict(status='BOTH_GATES_PASSED' if jpy_survived and gold_pass else 'NOT_RUN_GATE_FAILED',
                         correlation=pair,
                         correlation_basis='USDJPY_PASS5_SL_R; XAUUSD_SL_R' if gold_sl is not None else
                             'USDJPY_PASS5_SL_R; XAUUSD_4H_NET_OVER_NATURAL_STOP_R; ZERO_FOR_INACTIVE_ON_UNION',
                         double_sl_days=len({r['day'] for r in ledger if r['reason']==SL}
                                            &{r['day'] for r in gold_sl if r['reason']==SL})
                                            if jpy_survived and gold_sl is not None else None))
    output.mkdir(parents=True,exist_ok=False)
    base.write(output/'result.json',summary)
    base.write(output/'usdjpy_m1_ledger.json',jpy_m1_rows)
    base.write(output/'usdjpy_h1_stress_ledgers.json',scenarios)
    base.write(output/'xauusd_stage0_events.json',gold)
    if gold_sl is not None:
        base.write(output/'xauusd_sl_ledger.json',gold_sl)
    print(summary['jpy']['verdict'],summary['gold']['verdict'],summary['portfolio']['status'])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('private_jobs',type=Path)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    run(args.private_jobs,args.output)

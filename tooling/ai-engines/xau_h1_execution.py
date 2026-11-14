"""Execution-aware Development diagnostic; separate paths from paired costs/books."""
from bisect import bisect_left, bisect_right
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from functools import lru_cache
import json
from pathlib import Path
import struct
import time
from zoneinfo import ZoneInfo

from eurusd_b0_source import digest, write_json
from index_tick_review import decode, minute_ohlc
from xau_intraday_source import source_views
from xau_h1_stage0_source import START, END, HOUR
from xau_h1_stage0_scan import funding_events
from xau_h1_execution_prepare import deadline

REC=struct.Struct('<qii')
RATE=.000007
RISK=150
PRAGUE=ZoneInfo('Europe/Prague')
CELLS=('SYM_FLAT','SYM_ORDER','ASYM_FLAT','ASYM_ORDER')


def cents(value):
    return int((Decimal(str(value))*100).quantize(Decimal('1'),rounding=ROUND_HALF_UP))


def round_fee(value):
    return cents(value)/100


def commission(price_units,ounces):
    return round_fee(Decimal(price_units)*ounces*Decimal('.000000007'))


def exit_slip(reason, cell):
    return 0 if reason=='TP2R' and cell.endswith('ORDER') else .20


def swap_per_oz(side, cell):
    return -.40 if cell.startswith('SYM') else -.45 if side=='BUY' else -.05


def quote_exit(side, quote):
    return quote[1] if side=='BUY' else quote[2]


def signal_id(row):
    return f"{row['recipe']}:{row['decision_msc']}:{row['side']}"


def trigger(side, quote, stop, tp):
    price=quote_exit(side,quote)
    if price<=stop if side=='BUY' else price>=stop:
        return 'SL',price
    if tp is not None and (price>=tp if side=='BUY' else price<=tp):
        return 'TP2R',tp
    return None,None


def economics(trade, cell):
    entry=trade['entry_price_units']/1000;exit=trade['exit_price_units']/1000
    q=trade['ounces'];sign=1 if trade['side']=='BUY' else -1
    entry_fee=commission(trade['entry_price_units'],q);exit_fee=commission(trade['exit_price_units'],q)
    funding=sum(round_fee(q*swap_per_oz(trade['side'],cell)*e['multiplier'])
        for e in funding_events(trade['entry_msc'],trade['exit_msc']))
    slip=round_fee(q*.20)+round_fee(q*exit_slip(trade['reason'],cell))
    gross=round_fee(Decimal(sign*(trade['exit_price_units']-trade['entry_price_units'])*q)/1000)
    return dict(gross_usd=gross,commission_usd=entry_fee+exit_fee,slippage_usd=slip,
        swap_usd=funding,net_usd=round_fee(gross-entry_fee-exit_fee-slip+funding),
        net_R=round_fee(gross-entry_fee-exit_fee-slip+funding)/RISK)


class Events:
    def __init__(self,out):
        self.out=Path(out);self.start=time.monotonic();self.seq=0
    def __call__(self,stage,**fields):
        if (self.out/'CANCEL').exists():raise InterruptedError('execution_cancelled')
        if time.monotonic()-self.start>3600:raise TimeoutError('execution_deadline')
        self.seq+=1
        row=dict(sequence=self.seq,stage=stage,utc=datetime.now(timezone.utc).isoformat(),
            elapsed_seconds=time.monotonic()-self.start,**fields)
        write_json(self.out/'status.json',row)
        with (self.out/'events.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
        print(json.dumps(row),flush=True)


class Quotes:
    def __init__(self,root):self.root=Path(root)
    @lru_cache(maxsize=64)
    def hour(self,at):
        if not START<=at<END or at%HOUR:raise ValueError('closed_price_scope')
        rows=list(REC.iter_unpack((self.root/f'{at}.ticks').read_bytes()))
        return rows,[r[0] for r in rows]
    def endpoint(self,target):
        rows,times=self.hour(target//HOUR*HOUR);i=bisect_left(times,target)
        return rows[i] if i<len(rows) and rows[i][0]-target<=60000 else None
    def interval(self,start,end):
        for hour in range(start//HOUR*HOUR,end//HOUR*HOUR+1,HOUR):
            rows,times=self.hour(hour)
            for index in range(bisect_left(times,start),bisect_right(times,end)):
                yield rows[index],index


def admit_sources(cfg,out,event):
    source=json.loads(Path(cfg['tick_source']).read_bytes())
    if digest(cfg['tick_source'])!=cfg['tick_source_sha256']:raise ValueError('source_manifest_changed')
    minutes,_=source_views(cfg['cache'],cfg['source_correction'],end_msc=END)
    target=out/'ticks';target.mkdir()
    expected=defaultdict(set)
    for stamp in minutes:
        if START<=stamp<END:expected[stamp//HOUR*HOUR].add(stamp)
    proof=[];bad=[];counts=Counter()
    for index,r in enumerate(source['hours'],1):
        at=r['at']
        if not START<=at<END or at%HOUR:raise ValueError('non_development_tick_source')
        if digest(r['rawPath'])!=r['sha256']:raise ValueError('raw_tick_changed')
        ticks=decode(json.loads(Path(r['rawPath']).read_bytes()),start_msc=at,end_msc=at+HOUR)
        if len(ticks)!=r['records']:raise ValueError('raw_tick_census')
        observed=minute_ohlc(ticks)
        absent=sorted(expected[at]-observed.keys())
        counts['admitted_M1_minutes_in_requested_hours']+=len(expected[at])
        counts['admitted_M1_minutes_without_ticks']+=len(absent)
        for stamp,pair in observed.items():
            actual=[pair['bid'][k] for k in ('open','high','low','close')]
            if stamp in minutes:
                counts['M1_compared']+=1
                if actual!=minutes[stamp]:bad.append(dict(at=stamp,source=minutes[stamp],observed=actual,raw=r))
            else:counts['tick_minutes_absent_in_M1']+=1
        with (target/f'{at}.ticks').open('xb') as f:
            for row in zip(ticks.timestamps,ticks.bid_units,ticks.ask_units):f.write(REC.pack(*row))
        counts['ticks']+=len(ticks);counts['hours']+=1
        if not ticks.timestamps:counts['empty_hours']+=1
        proof.append(dict(at=at,raw_sha256=r['sha256'],binary_sha256=digest(target/f'{at}.ticks'),
            records=len(ticks),minutes=len(observed),admitted_M1_minutes_without_ticks=absent))
        if index%100==0:event('source_review',hours=index,total=len(source['hours']))
    review=dict(counts=dict(counts),mismatches=bad,hours=proof)
    write_json(out/'source-review.json',review)
    if bad:raise ValueError('execution_source_OHLC_mismatch_before_outcomes')
    return review


def path_for(row,quotes,hard_tp):
    at,bid,ask=row['entry_quote'];side=row['side'];sign=1 if side=='BUY' else -1
    price=ask if side=='BUY' else bid;stop=row['stop_units'];distance=sign*(price-stop)
    if distance<=0 or (bid<=stop if side=='BUY' else ask>=stop):raise ValueError('invalid_natural_stop')
    ounces=150000//distance
    if not 1<=ounces<=5000:raise ValueError('size_outside_declared_lot_spec')
    end=deadline(at);tp=price+sign*2*distance if hard_tp else None
    previous=at;largest_gap=0;gap_count=0;records=0;close=None
    mae=0;mfe=0
    entry_index=None;exit_index=None
    for quote,index in quotes.interval(at,end+60000):
        if entry_index is None:entry_index=index
        stamp=quote[0]
        if stamp>previous:
            largest_gap=max(largest_gap,stamp-previous)
            if stamp-previous>15*60000:gap_count+=1
        previous=stamp;records+=1
        move=sign*(quote_exit(side,quote)-price)
        mae=min(mae,move);mfe=max(mfe,move)
        # Quotes arriving at/after deadline have time-close priority; no new TP.
        if stamp>=end:
            close=('FRIDAY_CLOSE' if end<at+48*HOUR else 'TIME_48H',quote_exit(side,quote),stamp)
            exit_index=index
            break
        reason,fill=trigger(side,quote,stop,tp)
        if reason:
            close=(reason,fill,stamp);exit_index=index;break
    result=dict(signal_id=signal_id(row),recipe=row['recipe'],side=side,day=row['day'],
        entry_msc=at,entry_quote=row['entry_quote'],entry_price_units=price,stop_units=stop,
        entry_quote_index=entry_index,exit_quote_index=exit_index,
        natural_sl_usd_per_oz=distance/1000,ounces=ounces,lot=ounces/100,
        tp_units=tp,deadline_msc=end,exit_policy='TP2R' if hard_tp else 'NO_TP',
        records=records,max_observed_quote_gap_ms=largest_gap,gaps_gt15m=gap_count,
        MAE_usd_per_oz=mae/1000,MFE_usd_per_oz=mfe/1000,
        path_complete_not_proven=True)
    if close:
        reason,fill,stamp=close
        result.update(reason=reason,exit_price_units=fill,exit_msc=stamp,
            endpoint_wait_ms=max(0,stamp-end),costs={})
        result['costs']={cell:economics(result,cell) for cell in CELLS}
    else:result.update(reason='UNRESOLVED_ENDPOINT',exit_msc=None,costs=None)
    return result


class Stat:
    """Merge exact ordered segment extrema/DD under a constant equity offset."""
    def __init__(self):
        self.peak=0.;self.dd=0.;self.daily=0.;self.daily_equity=0.;self.minimum=0.
        self.cash=0.;self.anchor=0.;self.equity_anchor=0.;self.dd_witness=None;self.daily_witness=None
    def add(self,low,high,internal_dd,last,at):
        dd=max(self.peak-low,internal_dd)
        if dd>self.dd:self.dd=dd;self.dd_witness=at
        self.peak=max(self.peak,high);self.minimum=min(self.minimum,low)
        loss=self.anchor-low
        if loss>self.daily:self.daily=loss;self.daily_witness=at
        self.daily_equity=max(self.daily_equity,self.equity_anchor-low)
    def dump(self):
        return dict(max_equity_R_drawdown=self.dd/RISK,max_equity_drawdown_usd=self.dd,
            worst_daily_loss_pct=self.daily/50000*100,worst_daily_loss_usd=self.daily,
            equity_start_daily_loss_pct=self.daily_equity/50000*100,
            max_loss_from_initial_pct=-self.minimum/50000*100,
            dd_segment_witness=self.dd_witness,daily_segment_witness=self.daily_witness,
            realized_net_usd=self.cash)


def reset_times(year):
    day=datetime(year,1,1).date();end=datetime(year+1,1,1).date();result=[]
    while day<=end:
        stamp=int(datetime(day.year,day.month,day.day,tzinfo=PRAGUE).timestamp()*1000)
        if START<=stamp<END:result.append(stamp)
        day+=timedelta(days=1)
    return result


def price_summary(rows,qbuy,qsell):
    low=high=peak=last=None;dd=0
    for _,bid,ask in rows:
        value=(qbuy*bid-qsell*ask)/1000
        if low is None:low=high=peak=value
        low=min(low,value);high=max(high,value);peak=max(peak,value);dd=max(dd,peak-value);last=value
    return None if low is None else (low,high,dd,last)


def book(trades,quotes,year):
    """Shared ordered quote segments, four cost cash ledgers, no summed MAEs."""
    if any(t['exit_msc'] is None for t in trades):
        resolved=[t for t in trades if t['exit_msc'] is not None]
        return dict(status='UNRESOLVED_PATH_BOOK_NOT_MEASURED',
            excluded_signal_ids=[t['signal_id'] for t in trades if t['exit_msc'] is None],
            resolved_subcohort_only=book(resolved,quotes,year) if resolved else None)
    actions=defaultdict(list);stats={c:Stat() for c in CELLS}
    for i,t in enumerate(trades):
        _,et=quotes.hour(t['entry_msc']//HOUR*HOUR)
        _,xt=quotes.hour(t['exit_msc']//HOUR*HOUR)
        actions[(t['entry_msc'],t.get('entry_quote_index',bisect_left(et,t['entry_msc'])))].append(('entry',i,1))
        actions[(t['exit_msc'],t.get('exit_quote_index',bisect_left(xt,t['exit_msc'])))].append(('exit',i,1))
        for e in funding_events(t['entry_msc'],t['exit_msc']):actions[(e['at'],-1)].append(('swap',i,e['multiplier']))
    for at in reset_times(year):actions[(at,-1)].append(('reset',None,1))
    active={};accrued={c:{} for c in CELLS};qbuy=qsell=0;basis=0.;last_quote=None;max_concurrency=0;max_gross_oz=0
    stale_resets=0;event_marks=0
    if not trades:return dict(status='EMPTY')
    start=min(t['entry_msc'] for t in trades);end=max(t['exit_msc'] for t in trades)
    action_times=sorted(key for key in actions if start<=key[0]<=end)
    ai=0
    def apply(key,quote=None):
        nonlocal qbuy,qsell,basis,max_concurrency,max_gross_oz,stale_resets,event_marks,last_quote
        at=key[0]
        if any(a[0]=='reset' for a in actions[key]):
            if active and (last_quote is None or at-last_quote[0]>60000):stale_resets+=1
            for cell,s in stats.items():
                # Entry slip is temporarily represented as an equity expense;
                # in MT5 it stays in open price PnL until the position closes.
                s.anchor=s.cash+round_fee((qbuy+qsell)*.20)-sum(accrued[cell].values())
                s.equity_anchor=s.cash+((qbuy*last_quote[1]-qsell*last_quote[2])/1000-basis if active else 0)
        if quote is not None:
            last_quote=quote
            if active:
                value=(qbuy*quote[1]-qsell*quote[2])/1000-basis
                for s in stats.values():s.add(s.cash+value,s.cash+value,0,s.cash+value,at)
        for kind,i,mult in sorted(actions[key],key=lambda x: {'reset':0,'swap':1,'exit':2,'entry':3}[x[0]]):
            if kind=='reset':continue
            t=trades[i];q=t['ounces'];sign=1 if t['side']=='BUY' else -1
            if kind=='entry':
                active[i]=t;basis+=sign*q*t['entry_price_units']/1000
                if sign==1:qbuy+=q
                else:qsell+=q
                for cell,s in stats.items():
                    accrued[cell][i]=0.
                    s.cash-=commission(t['entry_price_units'],q)+round_fee(q*.20)
            elif kind=='swap':
                for cell,s in stats.items():
                    charge=round_fee(q*swap_per_oz(t['side'],cell)*mult)
                    s.cash+=charge;accrued[cell][i]+=charge
            else:
                del active[i];basis-=sign*q*t['entry_price_units']/1000
                if sign==1:qbuy-=q
                else:qsell-=q
                for cell,s in stats.items():
                    accrued[cell].pop(i)
                    s.cash+=t['costs'][cell]['gross_usd']-commission(t['exit_price_units'],q)-round_fee(q*exit_slip(t['reason'],cell))
            max_concurrency=max(max_concurrency,len(active));max_gross_oz=max(max_gross_oz,qbuy+qsell)
            if last_quote:
                value=(qbuy*last_quote[1]-qsell*last_quote[2])/1000-basis if active else 0
                for s in stats.values():s.add(s.cash+value,s.cash+value,0,s.cash+value,at)
                event_marks+=1
    for hour in range(start//HOUR*HOUR,end//HOUR*HOUR+1,HOUR):
        # Hours outside the requested source census have no open positions.
        path=quotes.root/f'{hour}.ticks'
        if not path.exists():
            if active:raise ValueError('missing_requested_path_hour')
            while ai<len(action_times) and action_times[ai][0]<hour+HOUR:
                apply(action_times[ai]);ai+=1
            continue
        rows,times=quotes.hour(hour);cursor=bisect_left(times,start)
        while ai<len(action_times) and action_times[ai][0]<hour+HOUR:
            key=action_times[ai];at,index=key
            cut=bisect_left(times,at) if index<0 else index
            if index>=0 and (cut>=len(rows) or rows[cut][0]!=at):raise ValueError('event_quote_ordinal')
            segment=rows[cursor:cut]
            if segment:
                if active:
                    low,high,dd,last=price_summary(segment,qbuy,qsell)
                    for s in stats.values():s.add(s.cash+low-basis,s.cash+high-basis,dd,s.cash+last-basis,segment[-1][0])
                last_quote=segment[-1]
            # At a quote timestamp positions act on that quote, before later ticks.
            quote=rows[cut] if index>=0 else None
            apply(key,quote);ai+=1;cursor=cut
        segment=rows[cursor:bisect_right(times,end)]
        if segment:
            if active:
                low,high,dd,last=price_summary(segment,qbuy,qsell)
                for s in stats.values():s.add(s.cash+low-basis,s.cash+high-basis,dd,s.cash+last-basis,segment[-1][0])
            last_quote=segment[-1]
    if active:raise ValueError('unclosed_book')
    for cell,s in stats.items():
        expected=sum(t['costs'][cell]['net_usd'] for t in trades)
        if abs(s.cash-expected)>1e-6:raise ValueError('book_cash_bridge')
    return dict(status='OBSERVED_TICK_BOOK_CONDITIONAL',costs={c:s.dump() for c,s in stats.items()},
        max_concurrent_positions=max_concurrency,max_gross_ounces=max_gross_oz,
        stale_equity_start_resets=stale_resets,event_marks=event_marks,
        daily_anchor='PRAGUE_MIDNIGHT_BALANCE',unobserved_quotes_not_bounded=True)


def execute(config_path):
    cfg=json.loads(Path(config_path).read_bytes());out=Path(cfg['output']);out.mkdir(exist_ok=False)
    event=Events(out)
    try:
        for name,sha in cfg['pins'].items():
            if digest(Path(cfg['workspace'])/name)!=sha:raise ValueError('frozen_code_changed:'+name)
        if digest(cfg['measurements'])!=cfg['measurements_sha256']:raise ValueError('parent_changed')
        if digest(cfg['source_correction'])!=cfg['source_correction_sha256']:raise ValueError('source_correction_changed')
        if digest(Path(cfg['cache'])/'manifest.json')!=cfg['cache_manifest_sha256']:raise ValueError('cache_manifest_changed')
        parent_rows=json.loads(Path(cfg['measurements']).read_bytes())
        if len(parent_rows)!=608 or any(not START<=r['decision_msc']<END for r in parent_rows):
            raise ValueError('parent_cohort_or_closed_window')
        if sum(r['recipe'] in ('H1A_ASIA','H1C_MOMENTUM') for r in parent_rows)!=356:
            raise ValueError('path_cohort_changed')
        census=json.loads(Path(cfg['census']).read_bytes())
        if digest(cfg['census'])!=cfg['census_sha256']:raise ValueError('census_changed')
        source_packet=json.loads(Path(cfg['tick_source']).read_bytes())
        if sorted(r['at'] for r in source_packet['hours'])!=census['hours']:
            raise ValueError('source_does_not_match_registered_census')
        source=admit_sources(cfg,out,event);quotes=Quotes(out/'ticks')
        rows=parent_rows;coverage=[];paths=[]
        for i,row in enumerate(rows):
            end=deadline(row['entry_quote'][0]);quote=quotes.endpoint(end)
            old=next(m for m in row['markouts'] if m['hours']==48)
            coverage.append(dict(signal_id=signal_id(row),recipe=row['recipe'],side=row['side'],day=row['day'],
                old_missing=old['exit_quote'] is None,target_msc=end,quote=quote,
                clamped=end<row['entry_quote'][0]+48*HOUR))
            if row['recipe'] in ('H1A_ASIA','H1C_MOMENTUM'):
                if quotes.endpoint(row['decision_msc'])!=tuple(row['entry_quote']):
                    raise ValueError('parent_entry_quote_not_reproduced')
                paths.extend(path_for(row,quotes,tp) for tp in (False,True))
            if i%50==0:event('path_measurement',signals=i,total=len(rows))
        write_json(out/'coverage.json',coverage);write_json(out/'trades.json',paths)
        summaries=[]
        for recipe,view in [('H1A_ASIA','BOTH'),('H1A_ASIA','BUY'),('H1A_ASIA','SELL'),('H1C_MOMENTUM','BOTH')]:
            for policy in ('NO_TP','TP2R'):
                for year in (2022,2023):
                    subset=[t for t in paths if t['recipe']==recipe and t['exit_policy']==policy
                        and t['day'].startswith(str(year)) and (view=='BOTH' or t['side']==view)]
                    event('synchronized_book',recipe=recipe,view=view,policy=policy,year=year)
                    b=book(subset,quotes,year)
                    cells={}
                    resolved=[t for t in subset if t['costs'] is not None]
                    for c in CELLS:
                        net=sum(t['costs'][c]['net_R'] for t in resolved)
                        cells[c]=dict(annual_net_R=net,mean_net_R=net/len(resolved) if resolved else None,
                            net_usd=sum(t['costs'][c]['net_usd'] for t in resolved),
                            **{k:sum(t['costs'][c][k] for t in resolved) for k in ('gross_usd','commission_usd','slippage_usd','swap_usd')})
                    summaries.append(dict(recipe=recipe,view=view,policy=policy,year=year,signals=len(subset),
                        resolved=len(resolved),exit_counts=dict(Counter(t['reason'] for t in subset)),costs=cells,book=b,
                        paths_with_gap_gt15m=sum(t['gaps_gt15m']>0 for t in subset),
                        max_quote_gap_minutes=max((t['max_observed_quote_gap_ms']/60000 for t in subset),default=0)))
        result=dict(schema='XAU-H1-execution-result-v1',summaries=summaries,
            coverage=dict(total=len(coverage),available=sum(r['quote'] is not None for r in coverage),
                old_missing=sum(r['old_missing'] for r in coverage),restored=sum(r['old_missing'] and r['quote'] is not None for r in coverage),
                missing=[r for r in coverage if r['quote'] is None]),
            source_counts=source['counts'],config_sha256=digest(config_path),
            trades_sha256=digest(out/'trades.json'),coverage_sha256=digest(out/'coverage.json'),
            source_review_sha256=digest(out/'source-review.json'),prices2024_2026_read=False,
            prop_qualified=False,broker_calls=0,wall_seconds=time.monotonic()-event.start)
        write_json(out/'result.json',result);event('completed',result_sha256=digest(out/'result.json'))
        return result
    except BaseException as exc:
        import traceback
        write_json(out/'failure.json',dict(type=type(exc).__name__,message=str(exc),
            locations=[dict(file=f.filename,line=f.lineno) for f in traceback.extract_tb(exc.__traceback__)]))
        raise


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);a=p.parse_args();execute(a.config)

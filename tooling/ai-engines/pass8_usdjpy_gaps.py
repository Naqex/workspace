"""Classify the frozen Pass 7B day exclusions and replay only observed QDM quotes."""

import argparse
from collections import Counter, defaultdict
from math import isclose
from pathlib import Path

import numpy as np

import pass5_usdjpy_tokyo as base
import pass7b_usdjpy_equity as equity
from pass7b_usdjpy_research import accounts, load_m1, profile
from pass6_breakout_execution import weekdays

PROTOCOL='18de257068e8fa9c297e77031029d3c213935f00'
PARENT='0517738'
STRESS='M1_Real_Stress_05'
A='sparse_zero_tick_minutes_compatible'
B='real_data_gap_or_unresolved'
C='holiday_or_early_close'
PRICE_JUMP_LIMIT=.001


def shape(day, offsets, prices, flat):
    missing=np.setdiff1d(np.arange(flat+1),offsets,assume_unique=True)
    positions=offsets.searchsorted(missing)
    bounded=(positions>0)&(positions<len(offsets))
    adjacent=positions[bounded]
    jumps=np.abs(prices[adjacent-1][:,[3,7]]-prices[adjacent][:,[0,4]])
    consecutive=bool(np.any(np.diff(missing)==1))
    boundaries=bool(np.isin([0,180,600,flat],offsets).all())
    max_jump=float(jumps.max()) if jumps.size else None
    return missing,dict(day=base.date(day).date().isoformat(),year=base.date(day).year,
        missing_minutes=len(missing),max_gap_minutes=int(max(np.diff(np.r_[-1,offsets,flat+1]))-1),
        isolated=not consecutive,boundary_quotes=boundaries,has_missing_tail=bool(missing.size and missing[-1]==flat),
        missing_box=int((missing<180).sum()),missing_oco=int(((missing>=180)&(missing<600)).sum()),
        missing_after_oco=int((missing>=600).sum()),quote_jump_max_pips=max_jump/base.PIP if max_jump is not None else None,
        compatible=bool(0<len(missing)<=5 and not consecutive and bounded.all() and boundaries
                        and max_jump is not None and max_jump<=PRICE_JUMP_LIMIT+1e-9))


def touches_between(past, following, edge):
    return min(past,following)<=edge+1e-10 and max(past,following)>=edge-1e-10


def replayable(missing, offsets, quote, trade):
    top,bottom=equity.box_edges(quote[offsets<180])
    entry_offset=offsets[trade.entry] if trade is not None else None
    exit_offset=offsets[trade.execution.index] if trade is not None else None
    for m in missing:
        if trade is not None and (abs(m-entry_offset)<=1 or abs(m-exit_offset)<=1):
            return False
        i=offsets.searchsorted(m)
        q0,q1=quote[i-1],quote[i]
        if 180<=m<600 and (entry_offset is None or m<entry_offset):
            if touches_between(q0[7],q1[4],top) or touches_between(q0[3],q1[0],bottom):
                return False
        if trade is not None and entry_offset<m<exit_offset:
            bid=trade.side==1
            if touches_between(q0[3 if bid else 7],q1[0 if bid else 4],trade.edge):
                return False
    return True


def cluster_name(year):
    return 'A' if year<=2020 else 'B'


def audit(jobs, destination):
    lock_path=base.ROOT/'planning/research/NATIVE_FTMO_HOLDOUT_LOCK.json'
    if base.sha(lock_path)!=base.LOCK_SHA:
        raise ValueError('Native holdout lock changed')
    lock=base.read(lock_path)
    if base.sha(base.AUDIT)!=lock['audit_sha256']:
        raise ValueError('FTMO audit drift')
    parent=jobs/'pass7b-usdjpy-qdm-equity-20261120'
    report_path=base.ROOT/'planning/research/PASS7B-USDJPY-FULL-M1-FLOATING-EQUITY-20261120.json'
    old=base.read(report_path)
    folder=parent/'development-m1'
    mp=folder/'manifest.json'
    if base.sha(mp)!=old['source_manifest_sha256']:
        raise ValueError('Pass 7B Development seal drift')
    m=base.read(mp)
    if m['holdout_exclusive_ms']!=base.STOP*1000:
        raise ValueError('Wrong Development cutoff')
    gpath=parent/'verified/m1-coverage-gaps.json'
    expected=base.read(parent/'manifest.json')['files']['verified/m1-coverage-gaps.json']['sha256']
    if base.sha(gpath)!=expected:
        raise ValueError('Prior gap cohort drift')
    frozen={r['day']:r for r in base.read(gpath)['native_h1_missing_m1_days']}
    if len(frozen)!=481:
        raise ValueError('Wrong excluded-day count')
    books,_=accounts(jobs,base.read(base.AUDIT))
    baseline=[]
    restored=[]
    existing_days=[]
    accepted_days=[]
    gaps=[]
    for year in base.YEAR:
        times,values=load_m1(folder,m['years'][str(year)],year)
        for day in weekdays():
            if base.date(day).year!=year:
                continue
            day_name=base.date(day).date().isoformat()
            end=(base.hard_flat(base.date(day))-day)//60
            lo,hi=times.searchsorted([day,day+(end+1)*60])
            day_end=times.searchsorted(day+base.DAY)
            offsets=(times[lo:hi]-day)//60
            quote=values[lo:hi,:8]
            if len(offsets)==end+1:
                if np.any(offsets!=np.arange(end+1)) or day_name in frozen:
                    raise ValueError('Previously classified M1 clock changed')
                existing_days.append(day//base.DAY)
                trade,_=equity.select(day,quote)
                if trade is not None:
                    baseline.append(trade)
                continue
            if day_name not in frozen:
                continue
            missing,data=shape(day,offsets,quote,end)
            if any(data[k]!=frozen[day_name][k] for k in ('missing_minutes','max_gap_minutes')):
                raise ValueError('Previously observed gap count changed')
            data['observed_after_flat_same_utc_day']=bool(day_end>hi)
            data['admitted']=data['trade']=False
            data['group']=A if data['compatible'] else B
            if data['compatible']:
                trade,_=equity.select(day,quote,offsets=offsets)
                data['admitted']=replayable(missing,offsets,quote,trade)
                if data['admitted']:
                    accepted_days.append(day//base.DAY)
                    if trade is not None:
                        restored.append(trade)
                        data['trade']=True
            gaps.append(data)
    if len(gaps)!=len(frozen) or len(existing_days)!=1334:
        raise ValueError('Pass 7B coverage census mismatch')
    if any(x['has_missing_tail'] and not x['observed_after_flat_same_utc_day'] for x in gaps):
        raise ValueError('Early close metadata needs review before classification')
    clusters=defaultdict(Counter)
    years=defaultdict(Counter)
    for row in gaps:
        for vessel in (years[str(row['year'])],clusters[cluster_name(row['year'])]):
            vessel[row['group']]+=1
            for k in ('missing_minutes','missing_box','missing_oco','missing_after_oco','admitted','trade'):
                vessel[k]+=int(row[k])
            vessel['max_gap_over_15']+=int(row['max_gap_minutes']>15)
            vessel['single_minute_days']+=int(row['missing_minutes']==1)
            vessel['missing_tail']+=int(row['has_missing_tail'])
    addon=equity.PROFILE[STRESS]
    previous_rows,previous_curve,control=profile(baseline,addon)
    old_metrics=old['profiles'][STRESS]
    if control['n']!=old_metrics['n'] or not isclose(control['net_R'],old_metrics['net_R'],abs_tol=1e-9):
        raise ValueError('Pass 7B Stress_05 baseline changed')
    combined=sorted(baseline+restored,key=lambda trade:trade.day)
    rows,marks,sensitivity=profile(combined,addon)
    clocks=[None if tr.offsets is None else tr.day+60*tr.offsets[tr.entry:tr.execution.index+1]
            for tr in combined]
    sizes=[]
    for book in books:
        prev,_=equity.account_replay(book,.003,previous_rows,previous_curve,existing_days)
        old_book=next(x for x in old['account_equity'][STRESS]
                      if x['account']==book.label and x['risk_pct']==.3)
        for field in ('net_usd','peak_floating_dd_pct','worst_daily_loss_pct','static_loss_pct'):
            if not isclose(prev[field],old_book[field],abs_tol=1e-8):
                raise ValueError(f'Baseline equity drift: {book.label} {field}')
        updated,_=equity.account_replay(book,.003,rows,marks,sorted(existing_days+accepted_days),
                                            observed_times=clocks)
        sizes.append(dict(baseline=prev,sensitivity=updated))
    result=dict(schema='pass8-usdjpy-m1-gap-audit-v1',protocol_commit=PROTOCOL,parent=PARENT,
        holdout_market_prices_read=False,order_send_count=0,
        holdout_lock_sha256=base.LOCK_SHA,source_manifest_sha256=base.sha(mp),
        total={k:sum(c[k] for c in years.values()) for k in (A,B,C,'admitted','trade','missing_minutes',
              'missing_box','missing_oco','missing_after_oco','max_gap_over_15','single_minute_days','missing_tail')},
        years=dict(years),clusters=dict(clusters),
        coverage=dict(baseline=len(existing_days),sensitivity=len(existing_days)+len(accepted_days)),
        base_R=control,sensitivity_R=sensitivity,books=sizes)
    destination.mkdir(exist_ok=False)
    base.write(destination/'gap-days.json',gaps)
    base.write(destination/'gap-summary.json',result)
    base.write(destination/'stress05-sensitivity-trades.json',rows)
    print(result['total'],result['coverage'],sensitivity['net_R_annual'],flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jobs',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    audit(args.jobs,args.output)

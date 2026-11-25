"""Run the registered Pass 7B solo USDJPY M1 audit from QDM quarantine exports."""

import argparse
from collections import Counter, defaultdict
from math import isclose
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

import pass5_usdjpy_tokyo as base
import pass7b_qdm_m1 as source
import pass7b_usdjpy_equity as equity
from pass6_breakout_execution import bound_usdjpy_packets, explicit_packet, weekdays

SWING_REPORT='SWING-10K-AUDIT-MULTIWEEK-AND-WIN-TAXONOMY-20261120.json'
PARQUET_CURVE=['ts_utc','open_usd_per_lot','high_usd_per_lot','low_usd_per_lot','close_usd_per_lot']


def accounts(jobs, audit):
    directory=jobs/'swing-10k-20261120/native-margin'
    report=base.read(base.ROOT/'planning/research'/SWING_REPORT)
    files=['TARGET_ACCOUNT_SPEC_SNAPSHOT.json','NATIVE_MARGIN_MATRIX.json']
    paths=[directory/f for f in files]
    bindings={f:base.sha(p) for f,p in zip(files,paths)}
    if any(report['inputs'][f]!=bindings[f] for f in files):
        raise ValueError('Swing account evidence hash drift')
    snap,margin=(base.read(p) for p in paths)
    if snap['account']['leverage']!=30 or snap['account']['currency']!='USD':
        raise ValueError('Swing book identity drift')
    swing=snap['specs']['USDJPY']
    standard=audit['symbols']['USDJPY']
    if standard['commission_usd_per_lot_roundtrip']!=equity.COMMISSION:
        raise ValueError('USDJPY commission drift')
    m=max(x['margin_100_usd'] for x in margin['USDJPY']['sides'].values())
    std_margin=max(standard['spec']['margin_estimates_usd']['1.0'])
    if not isclose(m,100000/30,abs_tol=.01) or std_margin!=1000:
        raise ValueError('Margin differs from registered leverage')
    books=[]
    for label,initial,margin_per_lot,spec in (
            ('Swing 10k',10000,m,swing),('Swing 25k',25000,m,swing),
            ('Standard 50k',50000,std_margin,standard['spec'])):
        if (spec['trade_contract_size'],spec['currency_margin'],spec['volume_min'],spec['volume_step'])!=(
                equity.CONTRACT,'USD',.01,.01):
            raise ValueError('USDJPY contract changed')
        books.append(equity.Account(label,initial,margin_per_lot,spec['volume_min'],
                                    spec['volume_step'],spec['volume_max']))
    return books,bindings


def load_m1(folder, meta, year):
    name=f'USDJPY-M1-BIDASK-{year}.parquet'
    path=folder/name
    if meta['parquet']!=name or base.sha(path)!=meta['parquet_sha256']:
        raise ValueError('USDJPY M1 Parquet SHA mismatch')
    low,high=(stamp//source.MINUTE_MS for stamp in source.year_limits(year))
    bt=pq.read_table(path,columns=['minute'])['minute'].to_numpy()
    if (not len(bt) or len(bt)!=meta['minutes'] or bt[0]<low or bt[-1]>=high
            or np.any(np.diff(bt)<=0)):
        raise ValueError('USDJPY M1 UTC fence/ordering failed')
    cols=source.COLUMNS[2:]
    prices=pq.read_table(path,columns=cols)
    return bt*60,np.column_stack([prices[k].to_numpy() for k in cols])/1000.


def paired_reference(jobs):
    p=jobs/'pass5-usdjpy-tokyo-box-20261120'
    p6=jobs/'pass6-breakout-execution-20261120'
    paths=[p/'verified/sl_active_ledger.json',p6/'verified/usdjpy_m1_ledger.json']
    for parent,path in zip((p,p6),paths):
        record=base.read(parent/'manifest.json')['files'][path.relative_to(parent).as_posix()]
        if base.sha(path)!=record['sha256']:
            raise ValueError('Parent USDJPY ledger binding drift')
    h1,m1=(base.read(p) for p in paths)
    h1days={r['day'] for r in h1}
    paired={r['day']:r for r in m1 if r['day'] in h1days}
    if len(paired)!=339:
        raise ValueError('Pass 6 matched cohort changed')
    packets=bound_usdjpy_packets(jobs/'challenge-discovery4-20261108/execution-v1')
    return h1,paired,packets


def parity_day(day, times, prices, flat, packet, state):
    """Only reads the previously bound R084/R085 dates for the Pass 6 parity oracle."""
    two=[explicit_packet(*packet[side],day) for side in ('BID','ASK')]
    states=range(day,flat+60,60)
    for at in states:
        if any(at not in stream for stream in two):
            continue
        state['target_minutes']+=1
        pos=times.searchsorted(at)
        if pos<len(times) and times[pos]==at:
            q=prices[pos]
            prev=[two[0][at].o,two[1][at].o,two[0][at].c,two[1][at].c]
            pairs=(q[0],q[4],q[3],q[7])
            state['clock_matched_minutes']+=1
            state['bid_ask_reversed_at_open']+=int(q[4]<q[0])
            state['exact_both_open']+=int(np.allclose(pairs[:2],prev[:2],rtol=0,atol=1e-9))
            state['exact_both_close']+=int(np.allclose(pairs[2:],prev[2:],rtol=0,atol=1e-9))
            state['exact_all_eight_OHLC']+=int(np.allclose(q[:8],[
                item for s in two for item in (s[at].o,s[at].h,s[at].l,s[at].c)],rtol=0,atol=1e-9))
            for i in range(2):
                k='bid' if i==0 else 'ask'
                state[f'abs_open_error_{k}_milli']+=int(round(abs(pairs[i]-prev[i])*1000))
        # Clock correlation: compare prices with proposed one-hour displacements on the same scope.
        for offset in (-3600,0,3600):
            point=at+offset
            index=times.searchsorted(point)
            if index<len(times) and times[index]==point:
                state[f'alignment_n_{offset}']+=1
                state[f'alignment_abs_bid_milli_{offset}']+=int(round(abs(prices[index,0]-two[0][at].o)*1000))


def configure_and_select(folder, manifest, hourly, p6, packets):
    coverage=defaultdict(Counter)
    full_months=set()
    trading_days=[]
    trades=[]
    parity=Counter()
    gap_days=[]
    missing_h1_days=[]
    for year in base.YEAR:
        times,prices=load_m1(folder,manifest['years'][str(year)],year)
        dated=base.date(times[0]).year
        if dated!=year or np.any(prices[:,4]<prices[:,0]) or np.any(prices[:,7]<prices[:,3]):
            raise ValueError('Paired quote integrity failure')
        c=coverage[str(year)]
        j=0
        for day in weekdays():
            d=base.date(day)
            if d.year!=year:
                continue
            key=d.date().isoformat()
            c['weekdays']+=1
            flat=base.hard_flat(d)
            lo,hi=times.searchsorted([day,day+base.DAY])
            trade_end=int(times.searchsorted(flat+60))
            c['weekdays_with_any_tick_minutes']+=int(hi>lo)
            native=all(t in hourly for t in range(day,day+10*base.HOUR,base.HOUR))
            c['native_h1_box_and_window_days']+=int(native)
            if key in p6:
                parity['pass6_reference_days']+=1
                parity_day(day,times[lo:hi],prices[lo:hi],flat,packets[day],parity)
            path=times[lo:trade_end]
            expected=(flat-day)//60+1
            missing=expected-len(path)
            if missing:
                c['weekday_missing_at_least_one_minute']+=1
                if native:
                    c['native_h1_days_with_incomplete_m1']+=1
                    gap_days.append(dict(day=key,missing_minutes=missing,
                        max_gap_minutes=int(max(np.diff(np.r_[day-60,path,flat+60]))//60-1)))
                    if len(path)==0:
                        missing_h1_days.append(key)
                continue
            if path[0]!=day or path[-1]!=flat or np.any(np.diff(path)!=60):
                raise ValueError('Path contains invalid M1 clock increments')
            c['complete_path']+=1
            c['complete_paths_with_native_h1']+=int(native)
            full_months.add((d.year,d.month))
            trading_days.append(day//base.DAY)
            quote=prices[lo:trade_end]
            midpoint_delta=np.maximum(abs((quote[:,1]+quote[:,5])/2-quote[:,9]/2),
                                      abs((quote[:,2]+quote[:,6])/2-quote[:,10]/2))
            c['proxy_mid_extrema_differ_minutes']+=int(np.count_nonzero(midpoint_delta>1e-9))
            c['paired_minutes_in_complete_paths']+=len(path)
            trade, dual_minutes=equity.select(day,quote[:,:8])
            c['any_dual_touch_minutes_in_OCO']+=dual_minutes
            if key in p6:
                parity['complete_qdm_days_on_pass6_reference']+=1
            if trade is None:
                c['no_touch']+=1
                continue
            c['fills']+=1
            trades.append(trade)
            j+=1
        print(year,'complete days',c['complete_path'],'trades',j,flush=True)
    return coverage,sorted(full_months),trading_days,trades,parity,gap_days,missing_h1_days


def profile(trades, addon):
    rows=[]
    marks=[]
    peak=dd=total=0.
    for trade in trades:
        curve=equity.path(trade,addon)
        row=equity.record(trade,addon)
        if not isclose(curve[-1,3],row['net_usd_per_lot'],abs_tol=1e-9):
            raise ValueError('M1 curve and realized close do not reconcile')
        z=total+equity.drawdown_points(curve)/row['initial_risk_usd']
        peaks=np.maximum.accumulate(np.r_[peak,z])
        dd=max(dd,float((peaks[1:]-z).max()))
        peak=float(peaks[-1])
        total+=row['net_R']
        rows.append(row)
        marks.append(curve)
    return rows,marks,equity.trade_summary(rows,dd)


def verdict(grid, all_months, stress):
    if len(all_months)!=84 or stress['n']==0:
        return 'INCONCLUSIVE_M1_COVERAGE'
    if min(stress['clusters'].values())<=0:
        return 'FAILED_FULL_M1_TRUTH_CHECK'
    for book in grid:
        if (min(book['cluster_net_usd'].values())>0 and book['positive_years']>=5
                and book['worst_daily_loss_pct']<=3. and book['peak_floating_dd_pct']<=8.
                and book['annual_pct']['all']>=8. and not book['hard_daily_breached']
                and not book['hard_static_breached']):
            return 'SOLO_VIABLE_FOR_PASS8_CHALLENGE_SIM'
    return 'ENGINE_1_NEEDS_PARTNER'


def run(job, jobs, source_root, out):
    lock_path=base.ROOT/'planning/research/NATIVE_FTMO_HOLDOUT_LOCK.json'
    if base.sha(lock_path)!=base.LOCK_SHA:
        raise ValueError('Holdout lock drift')
    lock=base.read(lock_path)
    if base.sha(base.AUDIT)!=lock['audit_sha256']:
        raise ValueError('FTMO cost audit drift')
    audit=base.read(base.AUDIT)
    books,account_bindings=accounts(jobs,audit)
    if not (source_root/'manifest.json').is_file():
        source.build(job,source_root)
    manifest=base.read(source_root/'manifest.json')
    if (manifest['protocol_commit'],manifest['holdout_exclusive_ms'],manifest['export_receipt_sha256']) != (
            source.PROTOCOL,base.STOP*1000,base.sha(job/'QDM_EXPORT_RECEIPT.json')):
        raise ValueError('QDM M1 manifest not bound to this export')
    h1,parent,packets=paired_reference(jobs)
    hourly=base.load_sealed(jobs/'bottleneck2-monfri-20261119/development','H1',lock['series']['USDJPY']['H1'])
    c,months,days,trades,parity,gaps,missing_days=configure_and_select(source_root,manifest,hourly,parent,packets)
    out.mkdir(exist_ok=False)
    result=dict(schema='pass7b-qdm-usdjpy-full-m1-equity-v1',protocol_commit=source.PROTOCOL,
                holdout_lock_sha256=base.LOCK_SHA,holdout_price_rows_analysed=0,order_send_count=0,
                source=manifest,source_manifest_sha256=base.sha(source_root/'manifest.json'),
                ftmo_spec_bindings=account_bindings | {'standard_audit':lock['audit_sha256']},
                coverage=c,months_with_complete_paths=len(months),gap_days=len(gaps),
                native_active_days_without_any_path_minute=len(missing_days),
                h1=equity.trade_summary([r|dict(dual_entry=False,entry_bar_forced_stop=False) for r in h1],None),
                profiles={}, account_equity={})
    for name,addon in equity.PROFILE.items():
        rows,curves,r=profile(trades,addon)
        result['profiles'][name]=r
        base.write(out/f'{name}-trades.json',rows)
        if name=='M1_Real_Base':
            shared=[x for x in rows if x['day'] in parent]
            paired=[parent[x['day']] for x in shared]
            parity['matched_trades']=len(shared)
            parity['same_side']=sum(u['side']==v['side'] for u,v in zip(shared,paired))
            parity['same_entry_minute']=sum(u['entry']==v['entry'] for u,v in zip(shared,paired))
            result['pass6_paired']=dict(counts=dict(parity),qdm_net_R=sum(x['net_R'] for x in shared),
                                       pass6_net_R=sum(x['net_R'] for x in paired))
        times=np.concatenate([x['entry']+np.arange(len(y))*60 for x,y in zip(rows,curves,strict=True)])
        curve=np.concatenate(curves)
        pq.write_table(pa.table({PARQUET_CURVE[0]:times}|{
            k:curve[:,i] for i,k in enumerate(PARQUET_CURVE[1:])}),
                       out/f'{name}-minute-per-lot.parquet',compression='zstd')
        results=[]
        amounts={}
        for spec in books:
            for risk in equity.RISKS:
                b,a=equity.account_replay(spec,risk,rows,curves,days)
                results.append(b)
                amounts[f'{spec.label}/{risk:.4f}']=a
        result['account_equity'][name]=results
        base.write(out/f'{name}-account-lots.json',amounts)
        print(name,'R/yr',r['net_R_annual']['all'],'floating DD',r['floating_drawdown_R'],flush=True)
    stress='M1_Real_Stress_05'
    result['verdict']=verdict(result['account_equity'][stress],months,result['profiles'][stress])
    base.write(out/'m1-coverage-gaps.json',dict(native_h1_missing_m1_days=gaps,native_h1_no_path=missing_days))
    base.write(out/'result.json',result)
    print(result['verdict'],flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job',type=Path,required=True)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    run(args.job,args.job.parent,args.source,args.output)

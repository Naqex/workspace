"""Pass 9 offline audit of MQL5 Round 2, keeping source units and risk evidence separate."""

import argparse
from collections import Counter, defaultdict
from dataclasses import replace
from datetime import timedelta
from hashlib import sha256
from math import fsum
from pathlib import Path
import re
from statistics import correlation
from zoneinfo import ZoneInfo

from bot_breakout_forensic import (assume_utc, concurrency, cumulative_stats, distribution,
                                  exit_evidence, source_time)
from bot_live_auditor import INBOX, ROOT, audit, behavior, metrics, outcomes
from pass8_mql5_public import FIELD, clean
from quant_core.ftmo_track_replay import (STOP, LogOnlyMarket, bar_path_scope, calendar_warnings,
                                         check_lock, position, profiles, rollovers, utc_time)
from quant_core.live_trade_log import MQL5_PENDING_TYPES, normalize, table
from native_ftmo_monfri_seal import read, write

PROTOCOL='011d1633dcf4b8a0e93ab0106e0686a88ddf4f97'
ZONES=('UTC','Europe/Helsinki')
OLD='bot-lab-mql5-pass3-20261120'
REFERENCE='2283078'
SIZES={'Swing':(10000,25000),'Standard':(50000,)}
EXTRA_FOREX={'AUDCAD','AUDNZD','NZDCAD','GBPAUD','EURCAD','GBPCAD','CADCHF'}
FUTURES_ROOTS={'NQ','GC','NG','HG','SI','6J','6E','YM','RTY','ES'}


def digest(data):
    return sha256(data).hexdigest()


class SnapshotConversion(LogOnlyMarket):
    """Pinned FX quote references for log repricing, with no market history binding."""
    def __init__(self, specs):
        super().__init__()
        self.specs=specs

    def bid(self, symbol, at):
        spec=self.specs.get(symbol)
        return (spec['bid']+spec['ask'])/2 if spec is not None else None


def out_of_scope(symbol):
    root=symbol.split('_')[0]
    if symbol in EXTRA_FOREX:
        return 'CFD_FX_LISTED_SPEC_NOT_IN_SEALED_13'
    if root in FUTURES_ROOTS and '_' in symbol:
        return 'ROOT_LISTED_UNDER_SEPARATE_FTMO_FUTURES_PRODUCT_CONTRACT_NOT_BOUND'
    if root=='ZC' and '_' in symbol:
        return 'CORN_CFD_UNDERLYING_AVAILABLE_SOURCE_FUTURES_CONTRACT_NOT_VERIFIED'
    return 'SUPPORT_UNVERIFIED'


def settle_proxy(t):
    return t.profit+(t.commission or 0.)+(t.swap or 0.)+(t.fee or 0.)


def stop_distance(t):
    return (t.open_price-t.sl)*(1 if t.direction=='BUY' else -1) if t.sl else None


def stop_risk(t, specs, market):
    distance=stop_distance(t)
    if distance is None or distance<=0 or t.symbol not in specs:
        return None
    s=specs[t.symbol]
    rate=market.usd(s['currency_profit'],0,t.symbol,t.open_price)
    return distance*t.lots*s['trade_contract_size']*rate if rate is not None else None


def sizing_audit(trades, canonical, specs):
    gross_view=[replace(t,net_profit=t.profit) for t in trades]
    gross=behavior(gross_view,outcomes(gross_view),LogOnlyMarket(),specs)['HIDDEN_MARTINGALE_LOT_ESCALATION']
    lookup={t.row:t for t in trades}
    market=SnapshotConversion(specs)
    def annotate(data):
        rows=[]
        for e in data['evidence']:
            t,p=(lookup[e[k]] for k in ('row','previous'))
            a,b=(stop_risk(x,specs,market) for x in (t,p))
            rows.append(e|dict(symbol=t.symbol,display_risk_ratio=a/b if a is not None and b is not None else None))
        ratios=[x['display_risk_ratio'] for x in rows if x['display_risk_ratio'] is not None]
        return dict(assessed=data['assessed'],events=len(rows),max_lot_ratio=max(
                    (x['lot_multiple'] for x in rows),default=None),
                    risk_pairs=len(ratios),risk_at_least_1_5=sum(x>=1.5 for x in ratios),
                    risk_ratio_distribution=distribution(ratios),evidence=rows)
    return dict(net_complete=annotate(canonical),gross_only=annotate(gross))


def peak_margin(valued):
    stamps=defaultdict(list)
    for t,c in valued:
        margin=c['margin_usd']
        if margin is not None:
            stamps[t.open_time].append(margin)
            stamps[t.close_time].append(-margin)
    peak=active=0.
    for tt in sorted(stamps):
        active+=fsum(stamps[tt])
        peak=max(peak,active)
    return peak


def costs(trades, specs, name):
    valued=[]
    unsupported=Counter()
    market=SnapshotConversion(specs)
    for t in trades:
        s=specs.get(t.symbol)
        if s is None:
            unsupported['OUT_OF_FTMO_13_UNIVERSE']+=1
            continue
        p=position(t,s,market)
        if p is None:
            unsupported['UNPRICED_SUPPORTED_ROW']+=1
            continue
        rate=market.usd(s['currency_profit'],t.close_time,t.symbol,t.close_price)
        slip_px=.20 if t.symbol=='XAUUSD' else .25 if t.symbol=='US500.cash' else .002 if t.symbol.endswith('JPY') else .00002
        slip=2*slip_px*s['trade_contract_size']*rate*t.lots
        fee=(p['open_commission']+p['close_commission'])*t.lots
        seen=list(rollovers(t.open_time,t.close_time,s['swap_rollover3days']))
        valued.append((t,dict(gross=p['gross']*t.lots,commission=fee,swap=p['swap']*t.lots,
            net_base=p['net']*t.lots,stress_slippage=slip,net_stress=p['net']*t.lots-slip,
            margin_usd=p['margin']*t.lots if p['margin'] is not None else None,
            rollovers=len(seen),triple_rollovers=sum(v==3 for _,v in seen))))
    totals=Counter()
    by=defaultdict(Counter)
    for t,c in valued:
        values={k:v for k,v in c.items() if k!='margin_usd'}
        totals.update(values)
        by[t.symbol].update(values|{'n':1})
    cal=calendar_warnings(trades,None,specs)
    margin=peak_margin(valued) if valued else None
    return dict(n=len(valued),missing=dict(unsupported),totals=dict(totals) if valued else None,
                by_symbol={k:dict(v) for k,v in by.items()},
                risk=metrics([(t,r['net_stress']) for t,r in valued]),
                weekend_supported_proxy=len(cal['weekend_proxy_rows']),
                estimated_concurrent_margin_usd=margin,margin_pct_nominal={
                    str(b):100*margin/b for b in SIZES[name]} if margin is not None else None)


def crosses_saturday(a,b):
    saturday=(a+timedelta(days=(5-a.weekday())%7)).replace(hour=0,minute=0,second=0,microsecond=0)
    if a.weekday()==6:
        saturday=a.replace(hour=0,minute=0,second=0,microsecond=0)-timedelta(days=1)
    return a < saturday+timedelta(days=1) and b > saturday


def clock_summary(trades):
    stamps=[source_time(t.open_wall_ms) for t in trades]
    exits=[source_time(t.close_wall_ms) for t in trades]
    zones={}
    for z in ZONES:
        zone=ZoneInfo(z)
        clock=[(utc_time(assume_utc(t.open_wall_ms,zone)),utc_time(assume_utc(t.close_wall_ms,zone))) for t in trades]
        zones[z]=dict(saturday_entries=sum(a.weekday()==5 for a,_ in clock),sunday_entries=sum(a.weekday()==6 for a,_ in clock),
            earliest_monday_open=min((a.strftime('%H:%M') for a,_ in clock if a.weekday()==0),default=None),
            latest_friday_close=max((b.strftime('%H:%M') for _,b in clock if b.weekday()==4),default=None),
            holds_saturday=sum(crosses_saturday(a,b) for a,b in clock),
            ny_17_rollover_trades=sum(next(rollovers(int(a.timestamp()*1000),
                                        int(b.timestamp()*1000),3),None) is not None for a,b in clock))
    return dict(first=min(stamps).isoformat(),last=max(exits).isoformat(),
          pre_2025_source_wall=sum(t.close_wall_ms<STOP for t in trades),
          holdout_or_straddle_source_wall=sum(t.close_wall_ms>=STOP for t in trades),
          hourly_source_wall=Counter(a.hour for a in stamps).most_common(),
          minute_source_wall=Counter(a.minute for a in stamps).most_common(),
          at_hour=sum(a.minute==a.second==0 for a in stamps),
          on_hour_minute=sum(a.minute==0 for a in stamps),
          at_h4_wall=sum(a.minute==a.second==0 and a.hour%4==0 for a in stamps),
          at_d1_wall=sum(a.hour==0 and a.minute==a.second==0 for a in stamps),
          holding_hours=distribution([(t.close_wall_ms-t.open_wall_ms)/3600000 for t in trades]),
          source_midnight_crossings=sum(a.date()!=b.date() for a,b in zip(stamps,exits)),
          timezone_assumptions=zones,timezone_status='SOURCE_WALL_CLOCK_UNVERIFIED')


def private_rows(raw, trades, specs):
    header, rows, *_=table(raw,'.csv')
    by_header={k.lower():i for i,k in enumerate(header)}
    comments=by_header.get('comment')
    kinds=Counter()
    pending_hour=Counter()
    canceled_hour=Counter()
    for cells in rows:
        kind=cells[by_header['type']].strip().casefold()
        if kind in MQL5_PENDING_TYPES:
            kinds[kind]+=1
            t=cells[0].strip()
            if len(t)>=16:
                pending_hour[t[11:16]]+=1
                if comments is not None and 'cancel' in cells[comments].casefold():
                    canceled_hour[t[11:16]]+=1
    exits=Counter()
    for t in trades:
        comment=rows[t.row-1][comments].casefold() if comments is not None else ''
        if not t.sl and not t.tp and '[sl]' not in comment and '[tp]' not in comment:
            exits['UNKNOWN_EXIT_NO_STOP_TARGET_EVIDENCE']+=1
            continue
        if t.symbol not in specs:
            exits['UNKNOWN_EXIT_NO_BOUND_TICK_SIZE']+=1
            continue
        exits[exit_evidence(t,comment,specs[t.symbol]['trade_tick_size'])['label']]+=1
    return dict(pending=dict(kinds),pending_source_clock=pending_hour.most_common(6),
          canceled_pending_count=sum(canceled_hour.values()),canceled_pending_source_clock=canceled_hour.most_common(6),
          exit_labels=dict(exits))


def pnl_summary(trades, specs):
    ordered=sorted(trades,key=lambda t:(t.close_wall_ms,t.row))
    months=Counter()
    quarters=Counter()
    at=defaultdict(list)
    p_r=defaultdict(list)
    stops=defaultdict(list)
    targets=defaultdict(list)
    streak=longest=0
    market=SnapshotConversion(specs)
    for t in ordered:
        cash=settle_proxy(t)
        close=source_time(t.close_wall_ms)
        months[close.strftime('%Y-%m')]+=cash
        quarters[f'{close.year}-Q{(close.month-1)//3+1}']+=cash
        at[t.close_wall_ms].append(cash)
        risk=stop_risk(t,specs,market)
        rate=market.usd(t.profit_currency,0,t.symbol,t.close_price)
        if risk and rate is not None:
            p_r[t.close_wall_ms].append(cash*rate/risk)
        if (distance:=stop_distance(t)) is not None:
            stops[t.symbol].append(distance)
        if t.tp:
            targets[t.symbol].append(abs(t.tp-t.open_price))
        streak=streak+1 if cash<0 else 0
        longest=max(longest,streak)
    top=sorted((v for v in months.values() if v>0),reverse=True)[:2]
    monetary=metrics([(t,settle_proxy(t)) for t in ordered])
    return dict(profit_currency=ordered[0].profit_currency,gross=metrics([(t,t.profit) for t in ordered]),
          complete_net=metrics([(t,t.net_profit) for t in ordered if t.net_profit is not None]),
          cash_proxy_blank_fee_zero=monetary,fee_coverage={k:sum(getattr(t,k) is not None for t in ordered)
             for k in ('commission','swap','net_profit')},observed_months=dict(months),observed_quarters=dict(quarters),
          profitable_months=sum(v>0 for v in months.values()),profitable_quarters=sum(v>0 for v in quarters.values()),
          ex_top2_months=monetary['sum']-fsum(top),
          top2_months_positive_share=fsum(top)/fsum(v for v in months.values() if v>0) if top else None,
          longest_losing_streak_cash_proxy=longest,
          closed_dd_cash_proxy=cumulative_stats([fsum(v) for v in at.values()]),
          display_sl_R_count=sum(map(len,p_r.values())),display_sl_R_dd_proxy=cumulative_stats(
            [fsum(v) for v in p_r.values()]) if p_r else None,
          true_initial_R_dd=None,lot_histogram={str(k):v for k,v in Counter(t.lots for t in ordered).items()},
          price_to_display_sl_distance_by_symbol={k:dict(protective=distribution([v for v in vs if v>0]),
                    n_protective=sum(v>0 for v in vs),n_nonprotective=sum(v<=0 for v in vs),unit='source_price')
                    for k,vs in stops.items()},
          price_to_display_tp_distance_by_symbol={k:dict(n=len(vs),unit='source_price',distance=distribution(vs))
                    for k,vs in targets.items()},
          display_R_basis='source_cash_proxy_converted_at_sealed_FX_reference_over_display_stop_USD',
          display_stop_risk_usd=distribution([r for t in trades if (r:=stop_risk(t,specs,market)) is not None]))


def paired_returns(a,b, start, end, *, weekly=False):
    a,b=({k:v for k,v in d.items() if start<=k<=end} for d in (a,b))
    if weekly:
        def sum_weeks(data):
            out=Counter()
            for d,v in data.items():
                out[d-timedelta(days=d.weekday())]+=v
            return out
        a,b=map(sum_weeks,(a,b))
    def coef(days):
        points=[(a.get(d,0.),b.get(d,0.)) for d in sorted(days)]
        x,y=zip(*points) if points else ([],[])
        return dict(n=len(points),pearson=correlation(x,y) if min(len(set(x)),len(set(y)))>1 else None)
    return dict(both_active=coef(a.keys()&b.keys()),union_active=coef(a.keys()|b.keys()),
                reference_loss_periods=coef({k for k,v in b.items() if v<0}))


def correlate_with_reference(trades,reference):
    out={}
    for z in ZONES:
        zone=ZoneInfo(z)
        def dates(ts):
            result=Counter()
            for t in ts:
                utc=assume_utc(t.close_wall_ms,zone)
                if utc>=STOP:
                    result[utc_time(utc).date()]+=settle_proxy(t)
            return result
        a=dates(trades)
        for nm, cohort in [('all_breakout_legs',reference),('breakout_usdjpy_only',[t for t in reference if t.symbol=='USDJPY'])]:
            b=dates(cohort)
            if not a or not b:
                continue
            start,end=max(min(a),min(b)),min(max(a),max(b))
            out[z+'/'+nm]=dict(common_from=start.isoformat(),common_to=end.isoformat(),
                         day=paired_returns(a,b,start,end),week=paired_returns(a,b,start,end,weekly=True))
    return out


def load_profiles(jobs):
    folder=jobs/'pass8-engine2-and-m1-gaps-20261120'
    m=read(folder/'manifest.json')['files']
    public=folder/'public-scan.json'
    if digest(public.read_bytes())!=m[public.name]['sha256']:
        raise ValueError('Pass 8 public evidence drift')
    result={}
    for x in read(public)['passed']:
        rel=f"public/detail-{x['signal_id']}.html"
        raw=(folder/rel).read_bytes()
        if digest(raw)!=m[rel]['sha256']:
            raise ValueError('Public snapshot SHA drift')
        f={clean(k).rstrip(':'):clean(v) for k,v in FIELD.findall(raw.decode('utf-8'))}
        suffix=re.search(r'\b[A-Z]{3}$',f.get('Profit',''))
        result[x['signal_id']]=dict(name=x['name'],url=x['url'],currency=suffix[0] if suffix else None,
                                   sha256=m[rel]['sha256'],public_trades=x['detail_trades'])
    return result


def audit_batch(jobs, destination, inbox=INBOX):
    check_lock()
    priors=jobs/OLD
    aggregate=priors/'AUDIT_AGGREGATES.json'
    if digest(aggregate.read_bytes())!=read(priors/'manifest.json')['files'][aggregate.name]['sha256']:
        raise ValueError('Pass 3 evidence drift')
    old=read(aggregate)['records']
    old_hash={x['sha256'] for x in old}
    old_id={x['signal_id'] for x in old}
    old_ref=next(x for x in old if x['signal_id']==REFERENCE)
    ref_data=(inbox/old_ref['file']).read_bytes()
    if digest(ref_data)!=old_ref['sha256']:
        raise ValueError('Breakout reference CSV changed')
    reference,_=normalize(ref_data,'.csv',currency='USD')
    public=load_profiles(jobs)
    ftmo,bindings=profiles()
    files=sorted({*inbox.glob('*.csv'),*(inbox/'engine2_round2').glob('*.csv')})
    result=[]
    exclusions=[]
    seen=set()
    private={}
    for file in files:
        raw=file.read_bytes()
        ident=file.name.split('.')[0]
        sha=digest(raw)
        if sha in old_hash or ident in old_id or sha in seen:
            exclusions.append(file.name)
            continue
        seen.add(sha)
        pub=public.get(ident,dict(name=file.stem,url=None,currency=None))
        trades,meta=normalize(raw,'.csv',currency=pub['currency'])
        if not trades or any(t.open_wall_ms is None or t.close_wall_ms is None or not t.open_price
            or not t.close_price or not t.lots or t.profit is None for t in trades):
            raise ValueError(f'Missing minimum structure: {file.name}')
        direct=audit(raw,'.csv',currency=pub['currency'],market=LogOnlyMarket())
        assert direct['normalization']==meta
        tox=direct['behavioral_toxicity']
        g=tox['HIDDEN_GRID_AVERAGING_DOWN']
        stop=tox['NO_HARD_SL_OR_WIDE_STOP_GAMBLING']
        size=sizing_audit(trades,tox['HIDDEN_MARTINGALE_LOT_ESCALATION'],ftmo['Swing'])
        out=direct['out_of_ftmo_13_universe']
        by_time={}
        for z in ZONES:
            values,_=normalize(raw,'.csv',timezone_name=z,currency=pub['currency'])
            by_time[z]={n:costs(values,s,n) for n,s in ftmo.items()}
        cash=pnl_summary(trades,ftmo['Swing'])
        if g['evidence'] or size['net_complete']['risk_at_least_1_5'] or size['gross_only']['risk_at_least_1_5']:
            status='REJECTED_HIDDEN_GRID_OR_MARTINGALE'
        elif size['gross_only']['events'] and size['gross_only']['risk_pairs']<size['gross_only']['events']:
            status='INSUFFICIENT_DATA_UNKNOWN'
        elif len(trades)==sum(out.values()):
            status='CLEAN_BUT_OUT_OF_FTMO13'
        elif not all((by_time[z]['Swing']['totals'] or {}).get('net_stress',0)>0 for z in ZONES):
            status='REJECTED_COST_OR_EDGE'
        else:
            status='CLEAN_ENGINE2_CANDIDATE'
        record=dict(signal_id=ident,profile=pub,file=file.name,sha256=sha,normalization=meta,
            symbols=direct['observed']['assets'],direction=direct['observed']['direction'],
            path_scope=dict(Counter(bar_path_scope(t) for t in trades)),status=status,
            out_of_universe={k:dict(n=v,support=out_of_scope(k)) for k,v in out.items()},
            grid=dict(adverse_entries=len({x['row'] for x in g['evidence']}),pairs=len(g['evidence']),
                      max_adverse_open=g['max_adverse_priors_at_entry'],overlap_checks=g['log_only_overlap_checks']),
            lot_scaling={k:{kk:vv for kk,vv in v.items() if kk!='evidence'} for k,v in size.items()},
            stops=stop,initial_sl_verified=sum(t.initial_sl is not None for t in trades),
            costs=by_time,cash=cash,clock=clock_summary(trades),execution=private_rows(raw,trades,ftmo['Swing']),
            concurrency=concurrency([{'trade':t} for t in trades]))
        # Keep the unresolved ALocalLevels-style profile in the triage dossier without promoting it.
        if not g['evidence']:
            record['reference_correlation']=correlate_with_reference(trades,reference)
        result.append(record)
        private[ident]=dict(grid_pairs=g['evidence'],lot_sequences=size)
        print(ident,status,len(trades),record['grid']['adverse_entries'],flush=True)
    totals=Counter(x['status'] for x in result)
    receipt=dict(schema='pass9-engine2-round2-v1',protocol_commit=PROTOCOL,parent='955633b',
                 order_send_count=0,holdout_price_files_opened=0,development_price_files_opened=0,
                 target_profile_bindings=bindings,legacy_exclusions=exclusions,records=result,
                 counts=dict(files=len(result),closed=sum(x['normalization']['accepted'] for x in result),
                     grid_flagged=sum(x['grid']['adverse_entries']>0 for x in result),
                     anti_grid_no_flag=sum(x['grid']['adverse_entries']==0 for x in result),
                     candidate_promoted=totals['CLEAN_ENGINE2_CANDIDATE'],statuses=totals))
    destination.mkdir(exist_ok=False)
    write(destination/'audit.json',receipt)
    write(destination/'toxicity-evidence.json',private)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--jobs',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    audit_batch(args.jobs,args.output)

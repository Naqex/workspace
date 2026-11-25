"""Log-only forensic receipt for a two-symbol closed-trade export."""

import argparse
from bisect import bisect_left
from collections import Counter, defaultdict
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from itertools import accumulate, groupby
import json
from pathlib import Path
from math import fsum
from statistics import correlation
from zoneinfo import ZoneInfo

import numpy as np

from bot_live_auditor import LIMIT, metrics
from quant_core.ftmo_track_replay import LogOnlyMarket, PRAGUE, STOP, bar_path_scope, position, profiles, rollovers, utc_time
from quant_core.live_trade_log import normalize, numeric, table
from quant_core.native_paths import read_bounded

ASSETS = ('USDJPY', 'XAUUSD')
ZONES = ('UTC', 'Europe/Helsinki')
CUTOFF = {'USDJPY': (18, 0), 'XAUUSD': (18, 55)}
SLIPPAGE = {'USDJPY': .004, 'XAUUSD': .40}
UNITS = {'USDJPY': .01, 'XAUUSD': 1.}
PERCENTILES = (.10, .25, .50, .75, .90, 1.)


def distribution(values):
    if not values:
        return None
    return dict(zip(('p10', 'p25', 'median', 'p75', 'p90', 'max'),
                    map(float, np.quantile(values, PERCENTILES))))


def source_time(ms):
    return utc_time(ms).replace(tzinfo=None)


def assume_utc(ms, zone):
    return int(source_time(ms).replace(tzinfo=zone).timestamp() * 1000)


def read_source(raw):
    trades, meta = normalize(raw, '.csv')
    header, rows, _, _, _ = table(raw, '.csv')
    if meta['layout'] != 'MQL5_SIGNALS_HISTORY' or header[-1] != 'Comment':
        raise ValueError('EXPECTED_MQL5_HISTORY_WITH_COMMENT')
    if not trades or {t.symbol for t in trades} - set(ASSETS):
        raise ValueError('WRONG_SYMBOL_COHORT')
    if any(t.open_wall_ms is None or t.close_wall_ms is None or t.open_wall_ms >= t.close_wall_ms
           or any(v is None for v in (t.direction, t.lots, t.open_price, t.close_price, t.profit)) for t in trades):
        raise ValueError('INCOMPLETE_LOG_GEOMETRY')
    funding, pending = [], []
    for values in rows:
        side = values[1].strip().casefold()
        if side not in {'balance', 'buy stop', 'sell stop'}:
            continue
        at = datetime.fromisoformat(values[0].replace('.', '-', 2))
        if side == 'balance':
            amount = numeric(values[11], '.', grouped=True)
            if amount is None:
                raise ValueError('INCOMPLETE_FUNDING')
            funding.append((at, amount))
        elif not values[11].strip() and 'cancel' in values[12].casefold():
            end = datetime.fromisoformat(values[7].replace('.', '-', 2))
            pending.append((values[3], side, at, end))
    comments = {t.row: rows[t.row-1][-1].casefold() for t in trades}
    return trades, meta, funding, pending, comments


def exit_evidence(trade, comment, tick):
    direction = 1 if trade.direction == 'BUY' else -1
    stop, target = trade.sl, trade.tp
    sl_gap = abs(trade.close_price-stop) if stop else None
    tp_gap = abs(trade.close_price-target) if target else None
    sl_near = sl_gap is not None and sl_gap <= tick + 1e-9
    tp_near = tp_gap is not None and tp_gap <= tick + 1e-9
    sl_tag, tp_tag = '[sl]' in comment, '[tp]' in comment
    favorable_stop = stop and direction*(stop-trade.open_price) >= -1e-9
    if (sl_tag or sl_near) and not tp_tag:
        mechanism = 'SL'
        label = ('BREAKEVEN_OR_TRAILING_STOP' if favorable_stop else
                 'HIT_EXACT_SL' if sl_near else 'SL_TAG_OUTSIDE_ONE_TICK')
    elif tp_tag or tp_near:
        mechanism = 'TP'
        label = 'HIT_EXACT_TP' if tp_near else 'TP_TAG_OUTSIDE_ONE_TICK'
    else:
        mechanism = 'TIME_OR_SIGNAL'
        label = 'TIME_OR_SIGNAL_EXIT'
    return dict(label=label, mechanism=mechanism, sl_tag=sl_tag, tp_tag=tp_tag,
                favorable_display_sl=bool(favorable_stop), sl_gap=sl_gap, tp_gap=tp_gap)


def in_cutoff(at, symbol):
    h, m = CUTOFF[symbol]
    return at.hour == h and at.minute == m and at.second <= 5


def clock_fingerprint(trades, pending):
    entries = [source_time(t.open_wall_ms) for t in trades]
    exits = [source_time(t.close_wall_ms) for t in trades]
    panes = {}
    for name in ZONES:
        zone = ZoneInfo(name)
        converted = [a.replace(tzinfo=zone).astimezone(timezone.utc) for a in entries]
        closed = [a.replace(tzinfo=zone).astimezone(timezone.utc) for a in exits]
        friday = [a for a in closed if a.weekday() == 4]
        monday = [a for a in converted if a.weekday() == 0]
        saturday_cross = 0
        for a,b in zip(converted,closed):
            start = (a + timedelta(days=(5-a.weekday())%7)).replace(hour=0, minute=0, second=0)
            saturday_cross += a < start + timedelta(days=1) and b > start
        nights = [sum(1 for _ in rollovers(int(a.timestamp()*1000), int(b.timestamp()*1000), 3))
                  for a,b in zip(converted,closed)]
        panes[name] = dict(entry_hour_utc=dict(sorted(Counter(a.hour for a in converted).items())),
                           sunday_utc_entries=sum(a.weekday() == 6 for a in converted),
                           earliest_monday_open_utc=min((a.time().isoformat() for a in monday),default=None),
                           latest_friday_close_utc=max((a.time().isoformat() for a in friday),default=None),
                           positions_crossing_saturday_utc=saturday_cross,
                           ny_17_rollover_nights_buckets=dict(Counter(str(min(v,2)) for v in nights)))
    transitions = []
    pending_stamps = [a for _,_,a,_ in pending]
    pending_sides = defaultdict(set)
    for _,side,at,_ in pending:
        pending_sides[at.date()].add(side)
    for zone_name in ('Europe/Helsinki','America/New_York'):
        tz=ZoneInfo(zone_name)
        now=min(entries).date()
        last=max(exits).date()
        while now <= last:
            at=datetime.combine(now,datetime.min.time()).replace(hour=12,tzinfo=tz)
            if at.utcoffset() != (at-timedelta(days=1)).utcoffset():
                epoch=at.replace(tzinfo=None,hour=0)
                def neighborhood(stamps, left, right):
                    values = [x for x in stamps if left <= x < right]
                    modes = Counter(a.time().isoformat(timespec='minutes') for a in values)
                    return dict(n=len(values), modes=modes.most_common(3))
                transitions.append(dict(model=zone_name,day=now.isoformat(),
                    pending_before=neighborhood(pending_stamps,epoch-timedelta(days=14),epoch),
                    pending_after=neighborhood(pending_stamps,epoch,epoch+timedelta(days=14)),
                    exit_before=neighborhood(exits,epoch-timedelta(days=14),epoch),
                    exit_after=neighborhood(exits,epoch,epoch+timedelta(days=14))))
            now+=timedelta(days=1)
    sunday=[a for a in entries if a.weekday()==6]
    monday=[a for a in entries if a.weekday()==0]
    friday=[a for a in exits if a.weekday()==4]
    pending_monday=[a for a in pending_stamps if a.weekday()==0]
    return dict(entry_minute=dict(sorted(Counter(a.minute for a in entries).items())),
                entry_hour_source=dict(sorted(Counter(a.hour for a in entries).items())),
                entry_weekday_source=dict(sorted(Counter(a.weekday() for a in entries).items())),
                entry_minute_grid={str(n):sum(a.minute%n==0 for a in entries) for n in (5,15,30,60)},
                entry_exact_second_grid={str(n):sum(a.minute%n==0 and a.second==0 for a in entries)
                                        for n in (5,15,30,60)},
                pending_count=len(pending),pending_open_clock=dict(Counter(a.time().isoformat(timespec='minutes') for a in pending_stamps)),
                pending_days=len(pending_sides), pending_days_with_both_stop_sides=sum(len(v)==2 for v in pending_sides.values()),
                pending_expiry_at_asset_cutoff=sum(in_cutoff(b,t) for t,_,_,b in pending),
                earliest_monday_fill=min((a.time().isoformat() for a in monday),default=None),
                earliest_monday_pending=min((a.time().isoformat() for a in pending_monday),default=None),
                latest_friday_close=max((a.time().isoformat() for a in friday),default=None),sunday_entries=len(sunday),
                calendar_midnight_nights_buckets=dict(Counter(str(min((b.date()-a.date()).days,2)) for a,b in zip(entries,exits))),
                holding_hours=distribution([(b-a)/timedelta(hours=1) for a,b in zip(entries,exits)]),
                utc_assumption_sensitivity=panes,dst_14_day_window_checks=transitions)


def protective_stop_risk(t, spec):
    if not t.sl:
        return None
    direction = 1 if t.direction == 'BUY' else -1
    distance = direction * (t.open_price-t.sl)
    usd = 1/t.open_price if t.symbol == 'USDJPY' else 1.
    return distance*spec['trade_contract_size']*usd*t.lots if distance > 0 else None


def cost_projection(t, spec, zone, market):
    bound = replace(t, open_time=assume_utc(t.open_wall_ms,zone),close_time=assume_utc(t.close_wall_ms,zone))
    p = position(bound,spec,market)
    if p is None:
        return None
    price_unit_usd = 1/t.close_price if t.symbol == 'USDJPY' else 1.
    slip = SLIPPAGE[t.symbol]*spec['trade_contract_size']*price_unit_usd
    return dict(base=p['net']*t.lots,stress=(p['net']-slip)*t.lots,swap=p['swap']*t.lots)


def summarize_money(items):
    ts = [item['trade'] for item in items]
    gross = metrics([(t,t.profit) for t in ts])
    net = [(t,t.net_profit) for t in ts if t.net_profit is not None]
    costs = {}
    for key in (k for k in items[0]['costs']) if items else ():
        priced = [it['costs'][key] for it in items if it['costs'][key] is not None]
        costs[key] = dict(n=len(priced),**{k:fsum(row[k] for row in priced) if priced else None
                                          for k in ('base','stress','swap')})
    return dict(gross=gross,source_net_coverage=len(net),source_net_metrics=metrics(net),
                modeled_costs=costs)


def cumulative_stats(values):
    running=high=drawdown=low=0.
    for step in values:
        running+=step
        high=max(high,running)
        low=min(low,running)
        drawdown=max(drawdown,high-running)
    return dict(peak_to_valley=drawdown,static_below_initial=-low)


def drawdown(items):
    sorted_items=sorted(items,key=lambda it:(it['trade'].close_wall_ms,it['trade'].row))
    vals=[it['trade'].profit for it in sorted_items]
    series=[]
    r_coverage=0
    for it in sorted_items:
        risk=it['display_risk_usd']
        if risk:
            r_coverage+=1
            series.append((it['trade'].close_wall_ms,it['trade'].profit/risk))
    def cash_at_same_time(rows):
        return [fsum(b for _,b in cohort) for _,cohort in groupby(rows,key=lambda r:r[0])]
    streak=longest=0
    for v in vals:
        streak=streak+1 if v<0 else 0
        longest=max(longest,streak)
    r_stats=cumulative_stats(cash_at_same_time(series)) if r_coverage else None
    by_zone={}
    if r_coverage==len(items) and series:
        for z in ZONES:
            zone=ZoneInfo(z)
            dates=defaultdict(list)
            for i,v in series:
                day=utc_time(assume_utc(i,zone)).astimezone(PRAGUE).date()
                dates[day].append((i,v))
            daily_r=max(cumulative_stats(cash_at_same_time(r))['static_below_initial'] for r in dates.values())
            by_zone[z]={str(fraction):dict(closed_daily_pct=daily_r*fraction,
                        closed_static_pct=r_stats['static_below_initial']*fraction,
                        closed_peak_to_valley_pct=r_stats['peak_to_valley']*fraction) for fraction in (.50,.75)}
    return dict(gross_cash=cumulative_stats(cash_at_same_time([(it['trade'].close_wall_ms,it['trade'].profit)
                                                              for it in sorted_items])),
                longest_gross_losing_streak=longest,display_risk_r_rows=r_coverage,closed_R_proxy=r_stats,
                closed_only_rule_scale_sensitivity=by_zone,true_initial_R_drawdown=None)


def concurrency(items):
    ordered=sorted((it['trade'] for it in items),key=lambda t:(t.open_wall_ms,t.row))
    starts=[t.open_wall_ms for t in ordered]
    events=[(t.open_wall_ms,1,t.symbol,t.direction) for t in ordered]
    events.extend((t.close_wall_ms,-1,t.symbol,t.direction) for t in ordered)
    active=Counter()
    peak=side_peak=0
    marks=[]
    for at,group in groupby(sorted(events),key=lambda event:event[0]):
        for _,delta,symbol,side in group:
            active[symbol,side]+=delta
        total=sum(active.values())
        peak=max(peak,total)
        side_peak=max(side_peak,max(active.values()))
        marks.append((at,total))
    overlap_ms=sum(b-a for (a,n),(b,_) in zip(marks,marks[1:]) if n>1)
    by_symbol=defaultdict(list)
    for t in ordered:
        by_symbol[t.symbol].append(t)
    close_to_next=[(b.open_wall_ms-a.close_wall_ms)/1000
                   for rows in by_symbol.values() for a,b in zip(rows,rows[1:])]
    return dict(peak=peak, peak_same_symbol_and_side=side_peak, overlap_ms=overlap_ms,
                minimum_inter_entry_seconds=min(((b-a)/1000 for a,b in zip(starts,starts[1:])),default=None),
                minimum_same_symbol_prior_close_to_next_entry_seconds=min(close_to_next,default=None))


def risk_distribution(items):
    pairs=[(it['gross_balance_at_open_usd'],it['display_risk_usd']) for it in items
           if it['display_risk_usd'] is not None and it['gross_balance_at_open_usd']>0]
    rtn=[a for a,_ in pairs]
    notionals=[b for _,b in pairs]
    corr=correlation(rtn,notionals) if len(set(rtn))>1 and len(set(notionals))>1 else None
    return dict(rows=len(pairs),source_balance_is_fee_incomplete=True,
                dollar_stop_risk=distribution(notionals),
                percentage_of_reconstructed_balance=distribution([100*b/a for a,b in pairs]),
                correlation_balance_to_stop_risk=corr)


def period_table(items, quarter=False):
    buckets=defaultdict(list)
    for it in items:
        close=source_time(it['trade'].close_wall_ms)
        bucket=f'{close.year}-Q{(close.month-1)//3+1}' if quarter else close.strftime('%Y-%m')
        buckets[bucket].append(it)
    return {k:summarize_money(rows) for k,rows in sorted(buckets.items())}


def cross_asset_correlation(items):
    start=max(min(it['trade'].close_date for it in items if it['trade'].symbol==s) for s in ASSETS)
    end=min(max(it['trade'].close_date for it in items if it['trade'].symbol==s) for s in ASSETS)
    result={}
    for period in ('day','week'):
        buckets=defaultdict(Counter)
        for it in items:
            t=it['trade']
            if start <= t.close_date <= end:
                day=source_time(t.close_wall_ms).date()
                if period=='week':
                    day-=timedelta(days=day.weekday())
                buckets[day][t.symbol]+=t.profit
        cohorts={'union_active':list(buckets.values()),
                 'both_active':[b for b in buckets.values() if all(s in b for s in ASSETS)]}
        result[period]={name:dict(n=len(rows),pearson=correlation(*( [b[s] for b in rows] for s in ASSETS))
                     if len(rows)>1 and all(len({b[s] for b in rows})>1 for s in ASSETS) else None)
                        for name,rows in cohorts.items()}
    return dict(common_start=start,common_end=end,**result)


def summarize_asset(items, pending, asset):
    trades=[it['trade'] for it in items]
    exits=Counter(it['exit']['label'] for it in items)
    winners=Counter(it['exit']['label'] for it in items if it['trade'].profit>0)
    cutoff=[it for it in items if it['exit']['mechanism']=='TIME_OR_SIGNAL'
            and in_cutoff(source_time(it['trade'].close_wall_ms),asset)]
    risk_r=[it['trade'].profit/it['display_risk_usd'] for it in items if it['display_risk_usd']]
    distances=[abs(t.open_price-t.sl)/UNITS[asset] for t in trades if t.sl]
    tp=[abs(t.tp-t.open_price)/UNITS[asset] for t in trades if t.tp]
    tp_over_sl=[abs(t.tp-t.open_price)/abs(t.open_price-t.sl) for t in trades if t.tp and t.sl and t.open_price!=t.sl]
    return dict(trades=len(trades), first_open=min(t.open_date for t in trades),last_close=max(t.close_date for t in trades),
        clock=clock_fingerprint(trades,pending), total=summarize_money(items),
        directions={side:summarize_money([it for it in items if it['trade'].direction==side]) for side in ('BUY','SELL')},
        exit=dict(labels=dict(exits), mechanisms=dict(Counter(it['exit']['mechanism'] for it in items)),
                  positive_gross_by_label=dict(winners),source_swap_known=sum(t.swap is not None for t in trades),
                  cutoff_proximity_5s=len(cutoff), cutoff_gross_winners=sum(it['trade'].profit>0 for it in cutoff),
                  cutoff_gross_usd=fsum(it['trade'].profit for it in cutoff),
                  time_or_signal_gross_usd=fsum(it['trade'].profit for it in items if it['exit']['mechanism']=='TIME_OR_SIGNAL'),
                  tagged_stop_distance_ticks=distribution([it['sl_gap_ticks'] for it in items
                                                           if it['exit']['sl_tag'] and it['sl_gap_ticks'] is not None]),
                  other_time_or_signal_clock=dict(Counter(source_time(it['trade'].close_wall_ms).strftime('%H:%M')
                     for it in items if it['exit']['mechanism']=='TIME_OR_SIGNAL' and it not in cutoff))),
        stop_distance=distribution(distances),stop_unit='pip' if asset=='USDJPY' else 'USD/oz',
        target_distance=distribution(tp),target_over_stop=distribution(tp_over_sl),target_rows=len(tp),
        display_r_multiple=distribution(risk_r),display_r_total=fsum(risk_r) if risk_r else None,
        actual_initial_r_multiple=None,risk=risk_distribution(items),concurrency=concurrency(items),drawdown=drawdown(items),
        monthly=period_table(items),quarterly=period_table(items,quarter=True))


def analyze(raw):
    trades,meta,funding,pending,comments=read_source(raw)
    rates,bindings=profiles()
    market=LogOnlyMarket()
    items=[]
    cashflows=funding+[(source_time(t.close_wall_ms),t.profit) for t in trades]
    ordered=sorted(cashflows)
    clock=[at for at,_ in ordered]
    balances=[0.,*accumulate(v for _,v in ordered)]
    for t in trades:
        spec=rates['Swing'][t.symbol]
        tick=spec['trade_tick_size']
        finding=exit_evidence(t,comments[t.row],tick)
        items.append(dict(trade=t,exit=finding,sl_gap_ticks=finding['sl_gap']/tick if finding['sl_gap'] is not None else None,
             display_risk_usd=protective_stop_risk(t,spec),
             gross_balance_at_open_usd=balances[bisect_left(clock,source_time(t.open_wall_ms))],
             costs={f'{p}/{z}':cost_projection(t,sp[t.symbol],ZoneInfo(z),market)
                    for p,sp in rates.items() for z in ZONES}))
    items.sort(key=lambda it:(it['trade'].open_wall_ms,it['trade'].row))
    cohorts={s:[it for it in items if it['trade'].symbol==s] for s in ASSETS}
    symbols={s:summarize_asset(v,[q for q in pending if q[0]==s],s) for s,v in cohorts.items() if v}
    cohort_windows=[]
    f=sorted(funding)
    for i,(a,cash) in enumerate(f):
        end=f[i+1][0] if i+1<len(f) else datetime.max
        cohort_windows.append(dict(from_source_clock=a.isoformat(),flow_usd=cash,
            assets={s:risk_distribution([it for it in v if a<=source_time(it['trade'].open_wall_ms)<end]) for s,v in cohorts.items()}))
    dates=Counter('pre_2025' if t.close_wall_ms<STOP else 'post_2025' if t.open_wall_ms>=STOP else 'straddles_2025'
                  for t in trades)
    payload=dict(schema='bot-lab-breakout-forensic-dna-v1',input_sha256=sha256(raw).hexdigest(),normalization=meta,
        scope=dict(first_open_source_clock=source_time(min(t.open_wall_ms for t in trades)).isoformat(),
                   last_close_source_clock=source_time(max(t.close_wall_ms for t in trades)).isoformat(),
                   time_cohorts={k:dates[k] for k in ('pre_2025','post_2025','straddles_2025')},bar_path_scope=dict(Counter(bar_path_scope(t) for t in trades)),
                   timezone_status='SOURCE_WALL_CLOCK_OFFSET_UNRESOLVED',initial_stop_verified=0,
                   market_store_opened=False,backtests_run=0,order_send_count=0),
        price_spec_bindings=bindings, assets=symbols, aggregate=summarize_money(items),monthly=period_table(items),
        quarterly=period_table(items,quarter=True),cash_flows_and_risk_periods=cohort_windows,concurrency=concurrency(items),
        drawdown=drawdown(items),cross_asset_correlation=cross_asset_correlation(items) if len(symbols)==2 else None,
        selective_win_diagnosis=dict(path_labeled=0,unknown_winners=sum(t.profit>0 for t in trades),
           winner_basis='REPORTED_GROSS_SIGN_ONLY',swap_share=None),prop_status='PROP_UNMEASURED')
    row_evidence=[dict(source_row=it['trade'].row,symbol=it['trade'].symbol,label=it['exit']['label'],
                       mechanism=it['exit']['mechanism'],tagged_sl=it['exit']['sl_tag'],tagged_tp=it['exit']['tp_tag'],
                       cutoff_5s=in_cutoff(source_time(it['trade'].close_wall_ms),it['trade'].symbol)
                       if it['exit']['mechanism']=='TIME_OR_SIGNAL' else False,
                       bar_path=bar_path_scope(it['trade'])) for it in items]
    return payload,row_evidence


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path)
    parser.add_argument('output_directory',type=Path,help='New private directory for aggregate and row evidence')
    args=parser.parse_args()
    report,evidence=analyze(read_bounded(args.source,LIMIT))
    args.output_directory.mkdir(parents=True,exist_ok=False)
    for name,payload in (('aggregate.json',report),('exit_evidence.json',evidence)):
        (args.output_directory/name).write_text(json.dumps(payload,indent=2,allow_nan=False)+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__':
    main()

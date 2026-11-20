"""Preregistered USDJPY Tokyo-box first-touch screen on sealed native H1."""

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from math import fsum, isfinite
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pyarrow.parquet as pq

from native_ftmo_asym_pivot import wall_to_utc
from native_ftmo_monfri_screen import wilder
from native_ftmo_monfri_seal import AUDIT, CLOCK, ROOT, START, STOP, read, sha, write
from selective_win_diagnosis import LABELS, UNKNOWN, classify

YEAR = tuple(range(2018, 2025))
CLUSTERS = {'A': YEAR[:3], 'B': YEAR[3:]}
HOUR = 3600
DAY = 24 * HOUR
PIP = .01
HORIZONS = ('4h', '8h', 'hard_flat')
HELSINKI = ZoneInfo('Europe/Helsinki')
NEW_YORK = ZoneInfo('America/New_York')
LONDON = ZoneInfo('Europe/London')
LOCK_SHA = 'f0a6b43cb205535b0a959456455dc1d857a0936c06c2e51b8614fd7d772a8486'
PROTOCOL_COMMIT = 'f2f02e821fd28baa11f082cff32e907fd68f571e'


@dataclass(frozen=True)
class Bar:
    o: float
    h: float
    l: float
    c: float


@dataclass(frozen=True)
class Costs:
    spread_pips: float
    commission_usd: float
    contract: float
    slip_pips_per_side: float = .20

    @property
    def spread(self):
        return self.spread_pips * PIP


def date(at):
    return datetime.fromtimestamp(int(at), timezone.utc)


def hard_flat(day):
    wall = datetime(day.year, day.month, day.day, 18, tzinfo=HELSINKI)
    return int(wall.timestamp())


def load_sealed(folder, frame, binding, *, asset='USDJPY'):
    path = folder / binding['development_file']
    if (asset not in ('USDJPY','EURJPY','EURUSD','GBPUSD')
            or path.name != f'{asset}-{frame}.parquet'
            or sha(path) != binding['development_sha256']):
        raise ValueError(f'Development SHA mismatch: {frame}')
    clocks = pq.read_table(path, columns=[CLOCK])[CLOCK].to_numpy()
    if (len(clocks) != binding['development_rows'] or not len(clocks) or clocks[-1] >= STOP
            or (np.diff(clocks) <= 0).any()):
        raise ValueError(f'Invalid sealed clock: {frame}')
    values = pq.read_table(path, columns=[CLOCK, 'open', 'high', 'low', 'close'],
                           filters=[(CLOCK, '>=', START), (CLOCK, '<', STOP)])
    columns = (values[k].to_numpy() for k in (CLOCK, 'open', 'high', 'low', 'close'))
    out = {}
    for wall, op, hi, lo, cl in zip(*columns):
        utc = int(wall_to_utc(int(wall)).timestamp())
        if utc < START:
            continue
        if (utc >= STOP or utc % HOUR or utc in out or (out and utc <= next(reversed(out)))
                or not all(isfinite(v) for v in (op, hi, lo, cl))
                or not 0 < lo <= min(op, cl) <= max(op, cl) <= hi):
            raise ValueError(f'Invalid bound OHLC or UTC clock: {frame}')
        out[utc] = Bar(float(op), float(hi), float(lo), float(cl))
    return out


def atr_checkpoints(daily):
    times = list(daily)
    rows = list(daily.values())
    close = np.array([r.c for r in rows])
    high = np.array([r.h for r in rows])
    low = np.array([r.l for r in rows])
    prev = np.r_[close[0], close[:-1]]
    tr = np.maximum(high-low, np.maximum(abs(high-prev), abs(low-prev)))
    atr = wilder(tr)
    return np.minimum(np.array(times)+DAY, np.r_[times[1:],times[-1]+DAY]), atr


def touch(bar, top, bottom, spread):
    return bar.h+spread >= top-1e-10, bar.l <= bottom+1e-10


def first_touch(path, top, bottom, costs):
    for stamp, bar in path:
        buy, sell = touch(bar, top, bottom, costs.spread)
        if buy and sell:
            return 'ambiguous_first_touch', None
        if buy:
            return 'event', (stamp, 1, max(top, bar.o+costs.spread)-costs.spread/2)
        if sell:
            return 'event', (stamp, -1, min(bottom, bar.o)+costs.spread/2)
    return 'no_touch', None


def pnl(entry_mid, exit_mid, side, costs):
    gross_pips = side*(exit_mid-entry_mid)/PIP
    usd_per_pip = costs.contract*PIP/exit_mid
    spread = costs.spread_pips*usd_per_pip
    slip = 2*costs.slip_pips_per_side*usd_per_pip
    gross = gross_pips*usd_per_pip
    total = spread+slip+costs.commission_usd
    return dict(gross=gross, spread=spread, commission=costs.commission_usd,
                slippage=slip, swap=0., cost=total, cost_pips=total/usd_per_pip, net=gross-total,
                gross_pips=gross_pips, net_pips=gross_pips-total/usd_per_pip)


def valid_exit(entry, exit_, day):
    return entry <= exit_ < (day+DAY) and date(exit_).astimezone(NEW_YORK).hour < 17


def run_day(day, hourly, daily_clock, daily_atr, costs, *, pip=PIP, value_at=None):
    stamps = list(range(day, day+10*HOUR, HOUR))
    if any(t not in hourly for t in stamps[:3]):
        return 'missing_box', None, None
    if any(t not in hourly for t in stamps[3:]):
        return 'missing_activation', None, None
    box = [hourly[t] for t in stamps[:3]]
    top = max(bar.h for bar in box)+costs.spread/2
    bottom = min(bar.l for bar in box)+costs.spread/2
    path = [(t,hourly[t]) for t in stamps[3:]]
    dual = any(all(touch(bar, top, bottom, costs.spread)) for _,bar in path)
    verdict, first = first_touch(path, top, bottom, costs)
    if first is None:
        return verdict, dual, None
    stamp, side, mid = first
    entry = stamp+HOUR
    endpoints = (entry+4*HOUR, entry+8*HOUR, hard_flat(date(day)))
    if not all(valid_exit(entry, t, day) for t in endpoints):
        raise ValueError('Horizon crossed a holding limit')
    if any(t not in hourly for t in range(day,max(endpoints)+HOUR,HOUR)):
        return 'missing_markout_path', dual, None
    j = np.searchsorted(daily_clock,day+3*HOUR,side='right')-1
    atr = float(daily_atr[j]) if j >= 0 and np.isfinite(daily_atr[j]) and daily_atr[j]>0 else None
    width = top-bottom
    ratio = width/atr if atr else None
    natural_stop = mid+side*costs.spread/2
    natural_stop = abs(natural_stop - (bottom if side==1 else top))
    value = value_at if value_at is not None else lambda _, start, end, side: pnl(start,end,side,costs)
    marks = {}
    try:
        for name, t in zip(HORIZONS,endpoints):
            exit_mid = hourly[t].o+costs.spread/2
            marks[name] = dict(exit_at=date(t).isoformat(),
                               Breakout=value(t,mid,exit_mid,side), Fade=value(t,mid,exit_mid,-side))
    except KeyError:
        return 'missing_conversion_quote', dual, None
    return 'valued', dual, dict(day=date(day).date().isoformat(), year=date(day).year, side=side,
        trigger_bar_open=date(stamp).isoformat(), entry_proxy_utc=date(entry).isoformat(),
        entry_proxy_london=date(entry).astimezone(LONDON).isoformat(),
        entry_proxy_new_york=date(entry).astimezone(NEW_YORK).isoformat(),
        width_pips=width/pip, atr_d1_pips=atr/pip if atr else None, width_over_atr=ratio,
        natural_stop_pips=natural_stop/pip, entry_mid_proxy=mid,
        stop_opposite_edge=bottom if side==1 else top, markouts=marks)


def stats(cohort):
    n = len(cohort)
    cash = {k:fsum(x[k] for x in cohort) for k in (
        'gross','spread','commission','slippage','swap','cost','net','gross_pips','net_pips')}
    positive = sorted((x['net'] for x in cohort if x['net']>0),reverse=True)
    top10 = fsum(positive[:10])
    return dict(n=n,**cash, mean_net=cash['net']/n if n else None,
                cost_pct_positive_gross=100*cash['cost']/cash['gross'] if cash['gross']>0 else None,
                top10_positive_share=top10/fsum(positive) if positive else None,
                without_top10=cash['net']-top10 if n else None)


def metrics(rows, horizon):
    result = {}
    for style, direction in (('Breakout',1), ('Fade',-1)):
        outcomes = [(r['side']*direction,r['markouts'][horizon][style]) for r in rows]
        result[style] = {'both':stats([x for _,x in outcomes]),
                         'buy':stats([x for side,x in outcomes if side>0]),
                         'sell':stats([x for side,x in outcomes if side<0])}
    return result


def width_band(v):
    if v is None:
        return 'unknown'
    return '<0.25' if v < .25 else '0.25–<0.50' if v < .50 else '>=0.50'


def evaluate(rows, horizon):
    by_year = {y:metrics([r for r in rows if r['year']==y],horizon) for y in YEAR}
    clusters = {k:metrics([r for r in rows if r['year'] in years],horizon) for k,years in CLUSTERS.items()}
    total = metrics(rows,horizon)
    breaks = [q['Breakout']['both'] for q in clusters.values()]
    yearly = [q['Breakout']['both']['net'] for q in by_year.values()]
    ranked = sorted(yearly,reverse=True)
    tests = dict(gross_positive_in_both_clusters=all(q['gross']>0 for q in breaks),
        net_stress_positive_in_both_clusters=all(q['net']>0 for q in breaks),
        beats_fade_in_both_clusters=all(q['Breakout']['both']['net']>q['Fade']['both']['net'] for q in clusters.values()),
        positive_without_best_two_years=fsum(ranked[2:])>0)
    fees = [r['markouts'][horizon]['Breakout']['cost_pips'] for r in rows]
    stops = [r['natural_stop_pips'] for r in rows]
    scale = dict(median_cost_pips=float(np.median(fees)), median_stop_pips=float(np.median(stops)),
                 median_cost_over_median_stop_pct=100*float(np.median(fees))/float(np.median(stops)),
                 pass_share_at_12pct=sum(f/s<=.12 for f,s in zip(fees,stops))/len(rows)) if rows else None
    return dict(years=by_year,clusters=clusters,total=total, gate=tests, pass_stage0=all(tests.values()),
                friction_scale=scale,
                breakout_positive_years=sum(v>0 for v in yearly),
                fade_positive_years=sum(q['Fade']['both']['net']>0 for q in by_year.values()),
                breakout_net_without_best_two_years=fsum(ranked[2:]),
                width_over_atr_groups={k:metrics([r for r in rows if width_band(r['width_over_atr'])==k],horizon)
                    for k in ('<0.25','0.25–<0.50','>=0.50','unknown')})


def stop_mid(bar, side, edge, spread):
    if side == 1 and bar.l <= edge+1e-10:
        return min(edge,bar.o)+spread/2
    if side == -1 and bar.h+spread >= edge-1e-10:
        return max(edge,bar.o+spread)-spread/2
    return None


def sl_trade(event, hourly, costs, *, stop_risk_usd=None, value_at=None):
    side = event['side']
    entry = int(datetime.fromisoformat(event['entry_proxy_utc']).timestamp())
    flat = int(datetime.fromisoformat(event['markouts']['hard_flat']['exit_at']).timestamp())
    mid = event['entry_mid_proxy']
    edge = event['stop_opposite_edge']
    risk = (event['natural_stop_pips']*PIP*costs.contract/mid if stop_risk_usd is None
            else stop_risk_usd(entry,event))
    value = value_at if value_at is not None else lambda _, start, end, side: pnl(start,end,side,costs)
    if risk <= 0.:
        raise ValueError('Non-positive structural risk')
    marks_R = [value(entry,mid,mid,side)['net']/risk]
    reason = 'HARD_FLAT'
    for at in range(entry,flat,HOUR):
        bar = hourly[at]
        out = stop_mid(bar,side,edge,costs.spread)
        if out is not None:
            # A stop inside the hour has no verified ordering against the favorable extreme.
            reason = 'SL_GAP_OR_TOUCH'
            # Use exact start for open-gaps and enclosing end for interior hit timestamps.
            open_mid = bar.o+costs.spread/2
            when = at if abs(out-open_mid) <= 1e-10 else at+HOUR
            break
        marks_R.extend(value(at,mid,q+costs.spread/2,side)['net']/risk for q in (bar.h,bar.l))
    else:
        out = hourly[flat].o+costs.spread/2
        at = when = flat
    repriced = value(at,mid,out,side)
    net = repriced['net']/risk
    marks_R.append(net)
    post = dict(net_R=net,swap_R=0.,mfe_R=max(0.,max(marks_R)),mae_R=max(0.,-min(marks_R)),
                holding_hours=(when-entry)/HOUR,calendar_exit=reason=='HARD_FLAT',paired_net_R=None)
    return dict(day=event['day'],year=event['year'],side=side,reason=reason,exit_proxy=date(when).isoformat(),
                initial_risk_usd=risk,gross_R=repriced['gross']/risk,friction_R=repriced['cost']/risk,
                **post,winner_label=classify(post),
                conditional_geometry_label=classify(post|{'calendar_exit':False}))


def sl_summary(ledger):
    acc = peak = dd = 0.
    streak = longest = 0
    for row in ledger:
        n = row['net_R']
        acc += n
        peak = max(peak,acc)
        dd = max(dd,peak-acc)
        streak = streak+1 if n<0 else 0
        longest = max(longest,streak)
    return dict(n=len(ledger), net_R=fsum(r['net_R'] for r in ledger),max_closed_R_drawdown=dd,
        max_losing_streak=longest,gross_R=fsum(r['gross_R'] for r in ledger),
        cost_R=fsum(r['friction_R'] for r in ledger),
        reasons=dict(Counter(r['reason'] for r in ledger)),
        winner_labels={k:sum(r['winner_label']==k for r in ledger) for k in (*LABELS,UNKNOWN)},
        conditional_geometry_labels={k:sum(r['conditional_geometry_label']==k for r in ledger)
                                     for k in (*LABELS,UNKNOWN)})


def sl_active(events, hourly, costs):
    rows = [sl_trade(event,hourly,costs) for event in events]
    yearly = {y:sl_summary([r for r in rows if r['year']==y]) for y in YEAR}
    total = sl_summary(rows)
    clusters = {k:sl_summary([r for r in rows if r['year'] in years]) for k,years in CLUSTERS.items()}
    for k, years in CLUSTERS.items():
        clusters[k]['net_R_per_year']=clusters[k]['net_R']/len(years)
    total['net_R_per_year'] = total['net_R']/len(YEAR)
    return dict(total=total,years=yearly,clusters=clusters,
                basis='OPPOSITE_EDGE_ONE_SL_HARD_FLAT; CLOSED_R_DD; H1_ENVELOPE',
                winner_taxonomy_note='Scheduled cutoff winners lack paired continuation. Conditional geometry omits that gate.'),rows


def run(folder, out):
    lock_file = ROOT/'planning/research/NATIVE_FTMO_HOLDOUT_LOCK.json'
    if sha(lock_file)!=LOCK_SHA:
        raise ValueError('Holdout lock SHA mismatch')
    lock = read(lock_file)
    audit_sha=sha(AUDIT)
    if audit_sha!=lock['audit_sha256']:
        raise ValueError('Target FTMO cost snapshot SHA drift')
    standard = read(AUDIT)
    native = standard['symbols']['USDJPY']
    costs = Costs(native['spread']['median'],native['commission_usd_per_lot_roundtrip'],
                  native['spec']['trade_contract_size'])
    if costs != Costs(.30,5.,100000.):
        raise ValueError('Target cost inputs drifted from registration')
    binding = lock['series']['USDJPY']
    hourly = load_sealed(folder,'H1',binding['H1'])
    daily = load_sealed(folder,'D1',binding['D1'])
    ac, av = atr_checkpoints(daily)
    counts = defaultdict(Counter)
    records = []
    for day in range(START,STOP,DAY):
        d = date(day)
        if d.weekday()>=5:
            continue
        c = counts[d.year]
        c['weekdays']+=1
        status, dual, event = run_day(day,hourly,ac,av,costs)
        c[status]+=1
        if dual is not None:
            c['complete_box_and_activation']+=1
            c['any_same_bar_dual_touch_days']+=int(dual)
        if event:
            records.append(event)
    results = {h:evaluate(records,h) for h in HORIZONS}
    advanced = [h for h,res in results.items() if res['pass_stage0']]
    report = dict(schema='usdjpy-tokyo-box-stage0-v1',protocol_commit=PROTOCOL_COMMIT,
        development_start=date(START).isoformat(), development_stop_exclusive=date(STOP).isoformat(),holdout_lock_sha256=LOCK_SHA,
        source={f:dict(file=binding[f]['development_file'],sha256=binding[f]['development_sha256'],
                       utc_rows=len(v), first_utc=date(next(iter(v))).isoformat(),
                       last_utc=date(next(reversed(v))).isoformat())
                for f,v in (('H1',hourly),('D1',daily))},
        resolution='H1_BID_CONSTANT_SPREAD_PROXY', costs=costs.__dict__, target_cost_snapshot_sha256=audit_sha,
        order_send_count=0, holdout_price_files_read=0, cohorts=counts,
        valued_events=len(records), horizons=results, zero_overnight_and_weekend_by_construction=True,
        advanced_horizons=advanced, decision='ADVANCE_SL_ACTIVE' if advanced else 'REJECTED_AT_STAGE0',
        sl_active_status='RUN_ON_ADVANCED_GATE' if advanced else 'NOT_RUN_GATE_FAILED')
    sl_rows = None
    if advanced:
        report['sl_active'],sl_rows = sl_active(records,hourly,costs)
    out.mkdir(parents=True,exist_ok=False)
    write(out/'stage0.json',report)
    write(out/'paired_events.json',records)
    if sl_rows is not None:
        write(out/'sl_active_ledger.json',sl_rows)
    print(report['decision'],report['valued_events'],advanced)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('development',type=Path)
    parser.add_argument('private_output',type=Path)
    args = parser.parse_args()
    run(args.development,args.private_output)


if __name__ == '__main__':
    main()

"""Offline, fixed six-asset FTMO Development screen. Input is the sealed Development copy."""
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from math import floor
from pathlib import Path
from zoneinfo import ZoneInfo
import sys

import numpy as np
import pyarrow.parquet as pq

from native_ftmo_monfri_seal import AUDIT, ASSETS, CLOCK, FRAMES, PROTOCOL, START, STOP, label, read, sha, write

HOUR = 3600
DAY = 86400
YEAR = tuple(range(2018, 2025))
FAMILIES = ('BREAKOUT', 'PULLBACK', 'SWEEP')
SCENARIOS = ('Base-Real', 'Stress-Real')
POLICIES = ('Mon-Fri', '20:30-UTC')
BOOKS = (10000, 50000)
PARTS = ('gross', 'spread', 'commission', 'slippage', 'swap', 'net')
NEW_YORK = ZoneInfo('America/New_York')


def date(t):
    return datetime.fromtimestamp(int(t), timezone.utc)


def wilder(values, n=14):
    out = np.full(len(values), np.nan)
    start = int(np.flatnonzero(np.isfinite(values))[0])
    first = start + n - 1
    if first < len(values):
        out[first] = np.mean(values[start:first + 1])
        for i in range(first + 1, len(values)):
            out[i] = (out[i - 1] * (n - 1) + values[i]) / n
    return out


def ema(values, n):
    out = np.full(len(values), np.nan)
    out[n - 1] = np.mean(values[:n])
    for i in range(n, len(values)):
        out[i] = out[i - 1] + 2 / (n + 1) * (values[i] - out[i - 1])
    return out


def bars(path, width):
    data = pq.read_table(path)
    t, o, h, l, c = (data[n].to_numpy() for n in (CLOCK, 'open', 'high', 'low', 'close'))
    if not (len(t) and t[-1] < STOP and (np.diff(t) > 0).all() and np.isfinite(o + h + l + c).all()
            and (l > 0).all() and (l <= np.minimum(o, c)).all() and (h >= np.maximum(o, c)).all()):
        raise ValueError(f'invalid sealed OHLC: {path.name}')
    complete = t + width
    if width == DAY:
        complete = np.minimum(complete, np.r_[t[1:], t[-1] + DAY])
    prev = np.r_[c[0], c[:-1]]
    tr = np.maximum(h - l, np.maximum(abs(h - prev), abs(l - prev)))
    return dict(t=t, o=o, h=h, l=l, c=c, complete=complete, atr=wilder(tr), tr=tr)


def adx(b):
    up, down = np.r_[0., np.diff(b['h'])], np.r_[0., -np.diff(b['l'])]
    pos = wilder(np.where((up > down) & (up > 0), up, 0))
    neg = wilder(np.where((down > up) & (down > 0), down, 0))
    dx = np.divide(100 * abs(pos - neg), pos + neg, out=np.zeros(len(pos)), where=(pos + neg) > 0)
    dx[:13] = np.nan
    return wilder(dx)


@dataclass(frozen=True)
class Intent:
    asset: str
    family: str
    frame: str
    at: int
    side: int
    distance: float
    fixed_stop: float | None = None
    target: float | None = None


def candidates(asset, source):
    h, d = source['H4'], source['D1']
    signals = []
    mids = {}
    for frame, lookback in (('H4', 20), ('D1', 10)):
        if frame == 'D1' and asset == 'XAUUSD':
            continue
        f = source[frame]
        mids[frame] = []
        for i in range(max(34, lookback), len(f['t'])):
            when = int(f['complete'][i])
            if not START <= when < STOP:
                continue
            top, bottom = max(f['h'][i-lookback:i]), min(f['l'][i-lookback:i])
            mids[frame].append((when, float(f['c'][i]), float((top + bottom) / 2)))
            if f['atr'][i-1] >= np.median(f['atr'][i-21:i-1]):
                continue
            side = int(f['c'][i] > top) - int(f['c'][i] < bottom)
            if side:
                signals.append(Intent(asset, 'BREAKOUT', frame, when, side, float(f['atr'][i])))

    fast, slow, h_ma = ema(d['c'], 50), ema(d['c'], 200), ema(h['c'], 20)
    strength = adx(d)
    for i, when in enumerate(h['complete']):
        if not START <= when < STOP or i < 20:
            continue
        j = int(np.searchsorted(d['complete'], when, side='right') - 1)
        if j < 4:
            continue
        up = d['c'][j] > fast[j] > slow[j] and h['l'][i-1] <= h_ma[i-1] and h['c'][i-1] <= h_ma[i-1]
        down = d['c'][j] < fast[j] < slow[j] and h['h'][i-1] >= h_ma[i-1] and h['c'][i-1] >= h_ma[i-1]
        side = int(up and h['c'][i] > max(h_ma[i], h['h'][i-1])) - int(down and h['c'][i] < min(h_ma[i], h['l'][i-1]))
        distance = float(h['atr'][i])
        if side:
            signals.append(Intent(asset, 'PULLBACK', 'H4', int(when), side, distance))
        top, bottom = max(d['h'][j-4:j+1]), min(d['l'][j-4:j+1])
        if not (strength[j] < 25 and bottom < h['c'][i] < top):
            continue
        side = int(h['l'][i] < bottom) - int(h['h'][i] > top)
        if side:
            stop = h['l'][i] - .1*distance if side > 0 else h['h'][i] + .1*distance
            signals.append(Intent(asset, 'SWEEP', 'H4', int(when), side, distance, float(stop), float((top+bottom)/2)))
    return signals, mids


def friday_limit(t):
    day = date(t)
    return int((day.replace(hour=23, minute=0, second=0) + timedelta(days=4-day.weekday())).timestamp())


def daily_limit(t):
    day = date(t).replace(hour=20, minute=0, second=0)
    offset = day.astimezone(NEW_YORK).utcoffset() + timedelta(hours=7)
    return int((day + offset).timestamp())


class Market:
    def __init__(self, asset, feed, meta, yen):
        self.asset, self.feed, self.yen = asset, feed, yen
        self.spec = meta['spec']
        self.spread = meta['spread']['median'] * (.01 if asset.endswith('JPY') else 1 if asset in ('XAUUSD','US500.cash') else .0001)
        self.slip = .2 if asset == 'XAUUSD' else .75 if asset == 'US500.cash' else .002 if asset.endswith('JPY') else .00002
        self.contract = self.spec['trade_contract_size']
        self.margin_floor = max(self.spec['margin_estimates_usd']['1.0'])

    def usd_unit(self, t, price, *, closed=False):
        if not self.asset.endswith('JPY'):
            return self.contract
        if self.asset == 'USDJPY':
            return self.contract / price
        i = int(np.searchsorted(self.yen['t'], t, side='left') - 1)
        if not closed:
            j = i + 1
            if j < len(self.yen['t']) and self.yen['t'][j] == t:
                return self.contract / float(self.yen['o'][j])
        if i < 0:
            raise ValueError('USDJPY conversion missing')
        return self.contract / float(self.yen['c'][i])

    def margin(self, t, bid):
        if self.asset in ('US500.cash','XAUUSD'):
            estimate = self.contract * bid / 50
        elif self.asset == 'USDJPY':
            estimate = self.contract / 100
        else:
            estimate = self.usd_unit(t, bid) * bid / 100
        return max(self.margin_floor, estimate)

    def commission(self, fill):
        if self.asset == 'XAUUSD':
            return fill * self.contract * .000007
        return 0 if self.asset == 'US500.cash' else 2.50

    def roundtrip(self, ent, t, bid, out_slip, funding, *, closed=False):
        entry, side, slip = ent
        unit = self.usd_unit(t, bid, closed=closed)
        gross = side*(bid-entry)*unit
        spread = self.spread*unit
        commission = self.commission(entry+(self.spread if side==1 else 0)+side*slip) + self.commission(bid+(self.spread if side==-1 else 0)-side*out_slip)
        slippage = (slip+out_slip)*unit
        return dict(gross=gross, spread=spread, commission=commission, slippage=slippage, swap=funding,
                    net=gross-spread-commission-slippage+funding)

    def swap(self, day_start, bid, side):
        previous = date(day_start-DAY)
        if previous.weekday() >= 4:
            return 0.
        times = 3 if (previous.weekday()+1)%7 == self.spec['swap_rollover3days'] else 1
        term = self.spec['swap_long' if side > 0 else 'swap_short']
        return term*self.spec['point']*self.usd_unit(day_start,bid)*times


def crossing(side, bid_open, low, high, stop, target, spread):
    shift = spread if side < 0 else 0
    open_quote, low_quote, high_quote = bid_open+shift, low+shift, high+shift
    signed = side*(open_quote-stop)
    if signed <= 0:
        return 'SL_GAP', bid_open, True
    hit = low_quote <= stop if side > 0 else high_quote >= stop
    if hit:
        return 'SL', stop-shift, False
    if target is not None:
        hit = high_quote >= target if side > 0 else low_quote <= target
        if hit:
            return 'TP_LIMIT', target-shift, False
    return None


def simulate(market, intent, mids, scenario, policy, *, markout=False):
    feed = market.feed
    ts = feed['t']
    i = int(np.searchsorted(ts,intent.at))
    if i >= len(ts) or ts[i]-intent.at > HOUR or date(ts[i]).weekday() > 4:
        return None, 'NO_CAUSAL_ENTRY'
    start = int(ts[i])
    limit = friday_limit(start)
    if date(start).isocalendar()[:2] != date(intent.at).isocalendar()[:2]:
        return None, 'NO_CAUSAL_ENTRY'
    if markout:
        limit = min(limit,start+DAY)
    elif policy == '20:30-UTC':
        limit = min(limit,daily_limit(start))
    if start >= limit or limit >= STOP:
        return None, 'OUTSIDE_DEADLINE'
    bid = float(feed['o'][i])
    slip = market.slip if scenario == 'Stress-Real' else 0.
    side = intent.side
    ent = bid, side, slip
    stop = intent.fixed_stop if intent.fixed_stop is not None else bid + market.spread/2 - side*intent.distance
    target = intent.target
    stop_bid = stop - (market.spread if side < 0 else 0)
    crossed = side*(bid-stop_bid) <= 0
    if not markout and (crossed or (target is not None and side*(target-bid) <= 0)):
        return None, 'STRUCTURE_ALREADY_CROSSED'
    # Stage-0 must still score the directional move for a fill past the intended SL.
    if crossed:
        stop_bid = bid - side*intent.distance
    risk = -market.roundtrip(ent,start,stop_bid,slip,0)['net']
    if risk <= 0:
        return None, 'INVALID_RISK'
    structural = None
    if not markout and intent.family == 'BREAKOUT':
        levels = mids[intent.frame]
        known = mids[intent.frame+'_times']
        j = int(np.searchsorted(known,start,side='right'))
        for when, px, middle in levels[j:]:
            if when >= limit:
                break
            if side*(px-middle) <= 0:
                structural = when
                break
        if structural is not None:
            j = int(np.searchsorted(ts,structural))
            if j < len(ts) and ts[j]-structural <= HOUR and ts[j] < limit:
                limit = int(ts[j])
    path = []
    funding, last = 0., start
    for j in range(i,len(ts)):
        t = int(ts[j])
        if t-last > 2*HOUR or t > limit:
            return None, ('MISSING_CUTOFF' if t > limit and t-last <= 2*HOUR else 'LONG_PATH_GAP')
        spot = float(feed['o'][j])
        if t//DAY > last//DAY:
            funding += market.swap(t//DAY*DAY,spot,side)
        last = t
        if t == limit:
            reaction = ('MARKOUT' if markout else 'STRUCTURE' if structural is not None and t < friday_limit(start) and
                         (policy != '20:30-UTC' or t != daily_limit(start)) else 'CUTOFF',spot,True)
        elif markout:
            continue
        else:
            reaction = crossing(side,spot,float(feed['l'][j]),float(feed['h'][j]),stop,target,market.spread)
        if reaction:
            reason, fill_bid, at_open = reaction
            exit_time = t if at_open else min(t+HOUR,limit)
            parts = market.roundtrip(ent,exit_time,fill_bid,0 if reason=='TP_LIMIT' else slip,funding,closed=not at_open)
            path.append((exit_time,parts['net']))
            standalone_friction = market.roundtrip(ent,start,bid,slip,0)
            return dict(asset=intent.asset,family=intent.family,frame=intent.frame,decision=intent.at,
                        entry=start,exit=exit_time,side=side,year=date(start).year,reason=reason,
                        stop_distance=abs(bid-stop_bid),initial_risk=risk,margin=market.margin(start,bid),
                        natural_risk_usd_per_lot=abs(bid-stop_bid)*market.usd_unit(start,bid),
                        natural_stop_crossed_at_entry=crossed,
                        friction_at_entry=sum(standalone_friction[k] for k in ('spread','commission','slippage')),
                        path=path,**parts), None
        close = float(feed['c'][j])
        mark = market.roundtrip(ent,t+HOUR,close,slip,funding,closed=True)['net']
        path.append((t+HOUR,mark))
    return None, 'DEVELOPMENT_END'


def select(rows, budget, *, raw=False):
    model, skips = [], Counter()
    active = {}
    for r in sorted(rows,key=lambda x:(x['entry'],ASSETS.index(x['asset']),x['frame']!='D1',x['decision'])):
        if raw:
            lots = budget*.005/r['initial_risk']
        else:
            active = {a:v for a,v in active.items() if v[0] > r['entry']}
            bound = budget - sum(it[1] for it in active.values())
            if r['asset'] in active:
                skips['ONE_POSITION_PER_ASSET'] += 1
                continue
            lots = floor(100*min(budget*.005/r['initial_risk'],max(0.,bound)/r['margin']))/100
            if lots <= 0:
                skips['LOT_FLOOR_OR_MARGIN'] += 1
                continue
            active[r['asset']] = r['exit'],r['margin']*lots
        model.append(r | {'lots':lots})
    return model, dict(skips)


def metrics(rows, equity, budget, years):
    count = len(rows)
    exposure = len(years)
    scale = budget*.005
    parts = {k:sum(r[k]*r['lots']/scale for r in rows) for k in PARTS}
    ordered = sorted((r['net']*r['lots']/scale for r in rows if r['net']>0),reverse=True)
    pos = sum(ordered)
    rr = np.r_[0.,np.cumsum(equity,dtype=float)] if equity else np.array([0.])
    dd = float(max(np.maximum.accumulate(rr)-rr))
    return dict(trades=count,trades_per_year=count/exposure,winrate=sum(r['net']>0 for r in rows)/count if count else None,
                mean_net_R=parts['net']/count if count else None,net_R_per_year=parts['net']/exposure,
                usd_per_year=parts['net']*scale/exposure,attribution_R=parts,max_drawdown_R=dd,
                net_over_dd=parts['net']/dd if dd else None,
                top5_gross_winner_share=sum(ordered[:5])/pos if pos else None,
                top10_gross_winner_share=sum(ordered[:10])/pos if pos else None,
                net_R_without_top5=parts['net']-sum(ordered[:5]),net_R_without_top10=parts['net']-sum(ordered[:10]))


def curve(rows, budget):
    timeline = defaultdict(lambda: defaultdict(float))
    for r in rows:
        previous = 0.
        for t,value in r['path']:
            timeline[t][r['asset']] += (value-previous)*r['lots']/(budget*.005)
            previous = value
        if abs(previous-r['net']) > 1e-7:
            raise ValueError('P&L does not tie to equity path')
    return timeline


def results(rows,budget,assets):
    timeline = curve(rows,budget)
    if abs(sum(sum(x.values()) for x in timeline.values()) - sum(r['net']*r['lots']/(budget*.005) for r in rows)) > 1e-7:
        raise ValueError('equity cash tie-out')
    subsets = {'A':YEAR[:3], 'B':YEAR[3:], 'ALL':YEAR}
    subsets.update({str(y):(y,) for y in YEAR})
    report = {}
    for key, years in subsets.items():
        # Assign entire trades and their floating paths to the entry-year cohort.
        subrows = [r for r in rows if r['year'] in years]
        view = timeline if key == 'ALL' else curve(subrows,budget)
        report[key] = metrics(subrows,[sum(view[t].values()) for t in sorted(view)],budget,years)
    calendar = range(START//DAY,STOP//DAY)
    days = {a:defaultdict(float) for a in assets}
    for t,parts in timeline.items():
        for a,value in parts.items():
            days[a][min(t,STOP-1)//DAY] += value
    grid = np.asarray([[days[a].get(t,0.) for t in calendar] for a in assets])
    corr = {a:{} for a in assets}
    for i,a in enumerate(assets):
        for j,b in enumerate(assets):
            corr[a][b] = float(np.corrcoef(grid[i],grid[j])[0,1]) if np.std(grid[i])>0 and np.std(grid[j])>0 else None
    return dict(metrics=report, daily_asset_corr=corr)


def stage0(rows, assets):
    selected,_ = select(rows,10000,raw=True)
    report = results(selected,10000,assets)['metrics']
    natural = [r for r in selected if not r['natural_stop_crossed_at_entry']]
    ratios = [r['friction_at_entry']/r['natural_risk_usd_per_lot'] for r in natural]
    med = (float(np.median([r['friction_at_entry'] for r in natural])) /
           float(np.median([r['natural_risk_usd_per_lot'] for r in natural]))) if natural else None
    retained = float(np.count_nonzero(np.asarray(ratios) <= .12)/len(selected)) if selected else None
    yearly = {}
    for y in YEAR:
        r = report[str(y)]
        p = r['attribution_R']
        yearly[str(y)] = dict(count=r['trades'],mean_net_R=r['mean_net_R'],totals_R=p)
    complete = all(y['count'] and y['totals_R']['net'] >
                   y['totals_R']['spread']+y['totals_R']['commission']+y['totals_R']['slippage']
                   for y in yearly.values())
    return dict(by_year=yearly,overall_R=report['ALL']['attribution_R'],sample=len(rows),
                stop_already_crossed_in_raw_markout=len(selected)-len(natural),
                median_friction_over_median_stop_risk=med,retained_at_12pct=retained,
                gate=bool(complete and med is not None and med <= .12 and retained >= .5))


def key(r):
    return r['asset'],r['frame'],r['decision'],r['side']


def delta(old,new,budget):
    a,b={key(r):r for r in old},{key(r):r for r in new}
    common=a.keys() & b.keys()
    change = lambda p: sum(b[i][p]*b[i]['lots']-a[i][p]*a[i]['lots'] for i in common)/(budget*.005)
    return dict(common_intents=len(common),monfri_only=len(b.keys()-a.keys()),daily_only=len(a.keys()-b.keys()),
                paired_delta_R={p:change(p) for p in PARTS},
                all_delta_R=(sum(r['net']*r['lots'] for r in new)-sum(r['net']*r['lots'] for r in old))/(budget*.005))


def run(root):
    lockfile = root/'NATIVE_FTMO_HOLDOUT_LOCK.json'
    lock = read(lockfile)
    pin = sha(lockfile)
    if (root/'NATIVE_FTMO_HOLDOUT_LOCK.sha256').read_text().split()[0] != pin or lock['protocol_sha256'] != sha(PROTOCOL) or lock['audit_sha256'] != sha(AUDIT):
        raise ValueError('protocol/data seal drift')
    if lock['cutoff_server'] != '2025-01-01' or lock['status'] != 'LOCKED_HOLDOUT':
        raise ValueError('incorrect holdout fence')
    pinned = {}
    for asset in ASSETS:
        pinned[asset] = {}
        for frame,width in FRAMES.items():
            declared = lock['series'][asset][frame]
            p = root/'development'/f'{asset}-{frame}.parquet'
            if declared['development_file'] != p.name or sha(p)!=declared['development_sha256']:
                raise ValueError('Development price partition drift')
            feed = bars(p,width)
            if len(feed['t']) != declared['development_rows']:
                raise ValueError('Development row count mismatch')
            pinned[asset][frame] = feed
    audit = read(AUDIT)['symbols']
    metrics_out = {}
    trade_archive = []
    for family in FAMILIES:
        output = {}
        metrics_out[family] = output
        for scenario in SCENARIOS:
            s0 = defaultdict(list)
            by_policy = {p:defaultdict(list) for p in POLICIES}
            raw_counts, rejects, by_year = Counter(), defaultdict(Counter), defaultdict(Counter)
            for asset in ASSETS:
                signals,mids = candidates(asset,pinned[asset])
                mids |= {f+'_times':np.asarray([x[0] for x in rows],dtype='int64') for f,rows in list(mids.items())}
                market = Market(asset,pinned[asset]['H1'],audit[asset],pinned['USDJPY']['H1'])
                for intent in (v for v in signals if v.family==family):
                    raw_counts[asset]+=1
                    year = str(date(intent.at).year)
                    by_year[f'{year}/{asset}']['RAW'] += 1
                    context = (market,intent,mids,scenario)
                    for policy in ('Stage-0', *POLICIES):
                        row, why = simulate(*context,policy,markout=policy=='Stage-0')
                        if why:
                            rejects[f'{policy}/{asset}'][why]+=1
                            by_year[f'{year}/{asset}'][f'{policy}/{why}'] += 1
                        elif policy=='Stage-0':
                            s0[asset].append(row)
                        else:
                            by_policy[policy][asset].append(row)
            result = dict(raw_signals=dict(raw_counts),path_or_entry_rejects={k:dict(v) for k,v in rejects.items()},
                          annual_raw_and_reject_counts={k:dict(v) for k,v in by_year.items()},stage0={},books={})
            output[scenario] = result
            views = {'PORTFOLIO':ASSETS,**{a:(a,) for a in ASSETS}}
            for name,assets in views.items():
                result['stage0'][name] = stage0([r for a in assets for r in s0[a]],assets)
            for budget in BOOKS:
                book = {}
                result['books'][str(budget)]=book
                for name,assets in views.items():
                    chosen,summary={},{}
                    for p in POLICIES:
                        selected,skips=select([r for a in assets for r in by_policy[p][a]],budget)
                        chosen[p]=selected
                        summary[p]=results(selected,budget,assets) | {'sizing_or_overlap_rejects':skips}
                        if name=='PORTFOLIO':
                            for r in selected:
                                trade_archive.append({k:v for k,v in r.items() if k!='path'} | {'policy':p,'book':budget,'scenario':scenario})
                    summary['hold_overnight_delta']=delta(chosen[POLICIES[1]],chosen[POLICIES[0]],budget)
                    book[name]=summary
        stress = output['Stress-Real']
        inspected = stress['books']['10000']['PORTFOLIO']['Mon-Fri']['metrics']
        whole = inspected['ALL']
        tests = dict(stage0=stress['stage0']['PORTFOLIO']['gate'], dual_cluster=min(inspected[k]['net_R_per_year'] for k in ('A','B'))>0,
                     velocity=whole['net_R_per_year']>=15, drawdown=whole['max_drawdown_R']<=20, ex_top10=whole['net_R_without_top10']>0)
        output['gates'] = tests
        output['verdict'] = 'PROMISING_FOR_NEXT_STAGE' if all(tests.values()) else 'REJECTED_AT_DEV'
        print(family,output['verdict'],tests,{k:round(inspected[k]['net_R_per_year'],2) for k in ('A','B','ALL')},flush=True)
    write(root/'RESULTS.json',dict(schema='ftmo-monfri-dev-v1',holdout_lock_sha256=pin,protocol_sha256=sha(PROTOCOL),
                                  screen_code_sha256=sha(Path(__file__)),families=metrics_out,holdout_price_files_read=0))
    pq.write_table(__import__('pyarrow').Table.from_pylist(trade_archive),root/'PORTFOLIO_TRADES.parquet',compression='zstd')


if __name__=='__main__':
    run(Path(sys.argv[1]))

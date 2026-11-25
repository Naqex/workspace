"""Fixed Development screen for three preregistered FTMO Swing sleeves."""
from bisect import bisect_left
from collections import Counter, defaultdict
from dataclasses import dataclass
from math import floor, isfinite
from pathlib import Path
import sys

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from ftmo_spread_sessions import ASSETS
from native_ftmo_asym_forensics import LOCK_PIN
from native_ftmo_asym_pivot import index_signals, sma, wall_to_utc
from native_ftmo_monfri_screen import DAY, Market, bars, date
from native_ftmo_monfri_seal import AUDIT, FRAMES, ROOT, START, STOP, read, sha, write

TREND, CARRY, INDEX = 'SWING_TREND_D1', 'SWING_CARRY_TREND_D1', 'SWING_INDEX_DIP_D1'
PORTFOLIO = 'EQUAL_RISK'
FAMILIES = (TREND, CARRY, INDEX)
POLICIES = ('SWING', 'FRIDAY_OPEN')
BOOKS = (10000, 25000)
PARTS = ('gross','spread','commission','slippage','swap','net')
CLUSTERS = {'A':range(2018,2021), 'B':range(2021,2025), 'ALL':range(2018,2025)}
PROTOCOL = ROOT / 'planning/research/SWING-10K-MULTIWEEK-PROTOCOL-20261120.md'
WIN_STANDARD = ROOT / '.agents/skills/strategy-qualification/references/selective-win-diagnosis.md'
FX_RATES = {'EUR':('EURUSD', False), 'GBP':('GBPUSD', False), 'AUD':('AUDUSD', False),
            'NZD':('NZDUSD', False), 'JPY':('USDJPY', True), 'CHF':('USDCHF', True), 'CAD':('USDCAD', True)}


@dataclass(frozen=True)
class Signal:
    family: str
    asset: str
    decision: int
    bar: int
    side: int
    atr: float
    features: dict

    @property
    def key(self):
        return f'{self.family}|{self.asset}|{self.decision}|{self.side}'


def native_book(job):
    lock_path = ROOT / 'planning/research/NATIVE_FTMO_HOLDOUT_LOCK.json'
    partition = read(job / 'DEVELOPMENT_MANIFEST.json')
    if partition['holdout_lock_sha256'] != LOCK_PIN or sha(lock_path) != LOCK_PIN:
        raise ValueError('holdout lock drift')
    lock = read(lock_path)
    if partition['source_archive_manifest_sha256'] != lock['archive_manifest_sha256'] or sha(AUDIT) != lock['audit_sha256']:
        raise ValueError('audit binding drift')
    native = job / 'native-margin'
    snap, measured = (read(native / name) for name in ('TARGET_ACCOUNT_SPEC_SNAPSHOT.json','NATIVE_MARGIN_MATRIX.json'))
    a = snap['account']
    if (a['currency'],a['leverage'],a['trade_mode'],snap['balance'],snap['scope'],
            snap['actual_broker_orders'],snap['terminal_algo_trading_enabled']) != ('USD',30,0,10000.,'READ_ONLY',0,False):
        raise ValueError('unverified Swing snapshot')
    feed = {}
    for asset in ASSETS:
        name = f'{asset}-D1.parquet'
        p = job / 'development' / name
        bound = lock['series'][asset]['D1']
        m = partition['files'][name]
        if m['sha256'] != sha(p) or m['source_sha256'] != bound['source_sha256'] or m['rows'] != bound['locked_interval_indices'][0]:
            raise ValueError(f'partition drift: {asset}')
        feed[asset] = bars(p, FRAMES['D1'])
    standard = read(AUDIT)['symbols']
    markets = {asset: SwingMarket(asset, feed, snap['specs'][asset],
                                  standard[asset]['spread'], measured)
               for asset in ASSETS}
    return feed, markets, {p.name:sha(p) for p in (native/'TARGET_ACCOUNT_SPEC_SNAPSHOT.json',
        native/'NATIVE_MARGIN_MATRIX.json',job/'DEVELOPMENT_MANIFEST.json',AUDIT,PROTOCOL,WIN_STANDARD)}


class SwingMarket(Market):
    def __init__(self, asset, feeds, spec, spread, native_matrix):
        self.feeds = feeds
        measured = native_matrix[asset]
        native = [measured['sides'][side]['margin_100_usd'] for side in ('BUY','SELL')]
        if any(n is None or not isfinite(n) or n<=0 for n in native) or spec['swap_mode'] != 1:
            raise ValueError(f'native Swing margin or swap mode missing: {asset}')
        super().__init__(asset, feeds[asset], {'spec':spec | {'margin_estimates_usd':{'1.0':native}}, 'spread':spread}, None)
        cc = spec['currency_margin']
        mid = (measured['ask']+measured['bid'])/2
        if asset in ('US500.cash','XAUUSD'):
            denominator = self.contract * mid
        elif cc == 'USD':
            denominator = self.contract
        else:
            base, invert = FX_RATES[cc]
            quote = native_matrix[base]
            live = (quote['bid'] + quote['ask']) / 2
            if invert:
                live = 1 / live
            denominator = self.contract * live
        self.margin_fraction = max(native)/denominator

    def rate(self, currency, when, closed=False):
        if currency == 'USD':
            return 1.
        asset, invert = FX_RATES[currency]
        b = self.feeds[asset]
        i = int(np.searchsorted(b['t'],when,side='right')-1)
        if i < 0:
            raise ValueError(f'FX conversion unavailable: {currency}')
        value = float(b['c'][i] if closed or b['t'][i] != when else b['o'][i])
        return 1/value if invert else value

    def usd_unit(self, t, price, *, closed=False):
        currency = self.spec['currency_profit']
        if self.asset in ('USDJPY','USDCAD','USDCHF') and currency != 'USD':
            return self.contract / price
        return self.contract * self.rate(currency,t,closed)

    def margin(self, t, bid, closed=False):
        notion = bid if self.asset in ('US500.cash','XAUUSD') else self.rate(self.spec['currency_margin'],t,closed)
        return self.margin_fraction * self.contract * notion

    def funding(self, previous, now, bid, side):
        term = self.spec['swap_long' if side==1 else 'swap_short']
        triple = self.spec['swap_rollover3days']
        return term * self.spec['point'] * self.usd_unit(now,bid) * rollover_units(previous,now,triple)


def rollover_units(previous, now, triple):
    """Count the quote's charged weekdays once, including a Friday-to-Monday gap."""
    units = 0
    for day in range(previous//DAY, now//DAY):
        weekday = date(day * DAY).weekday()
        if weekday < 5:
            units += 3 if (weekday + 1) % 7 == triple else 1
    return units


def signal_features(f, fast, slow, i, distance, carry_proxy):
    return {
        'trend': 'UP' if fast[i] > slow[i] else 'DOWN' if fast[i] < slow[i] else 'FLAT',
        'volatility': 'LT_1PCT' if f['atr'][i]/f['c'][i]<.01 else '1_TO_2PCT' if f['atr'][i]/f['c'][i]<.02 else 'GE_2PCT',
        'distance': 'LT_HALF_ATR' if distance<.5 else 'HALF_TO_1_ATR' if distance<1 else 'GE_1_ATR',
        'session': 'BROKER_D1_OPEN',
        'carry_historical': 'UNKNOWN',
        'carry_snapshot_proxy': 'POS' if carry_proxy>0 else 'NEG' if carry_proxy<0 else 'ZERO',
    }


def signals(asset, feed, market):
    fast, slow = sma(feed['c'],50), sma(feed['c'],200)
    mean20 = sma(feed['c'],20)
    index, exit_ma = index_signals(asset,feed) if asset == 'US500.cash' else ([], None)
    dip = {i.at for i in index}
    swap = (market.spec['swap_long'], market.spec['swap_short'])
    carry = int(swap[0]>swap[1]) - int(swap[1]>swap[0])
    out = []
    for i in range(199,len(feed['t'])-1):
        when = int(feed['complete'][i])
        if not START <= when < STOP or not isfinite(feed['atr'][i]):
            continue
        price = float(feed['c'][i])
        top, bottom = max(feed['h'][i-20:i]), min(feed['l'][i-20:i])
        trend = int(price>slow[i] and price>top) - int(price<slow[i] and price<bottom)
        direction = int(fast[i]>slow[i]) - int(fast[i]<slow[i])
        pull = carry and direction==carry and carry*(price-mean20[i])>0>=carry*(feed['c'][i-1]-mean20[i-1])
        for family, side, anchor in ((TREND, trend, top if trend>0 else bottom),
                                    (CARRY, carry if pull and asset not in ('US500.cash','XAUUSD') else 0, mean20[i]),
                                    (INDEX, int(when in dip), slow[i])):
            if side:
                d = float(feed['atr'][i])
                if d <= 0:
                    continue
                features = signal_features(feed, fast, slow, i, abs(price-anchor)/d, swap[0 if side>0 else 1])
                out.append(Signal(family,asset,when,i,side,d,features))
    return out, exit_ma


def next_entry(market, s, policy):
    f = market.feed
    i = s.bar + 1
    t = int(f['t'][i])
    day = date(t).weekday()
    if not s.decision <= t < STOP or day >= 5 or t-s.decision > 4*DAY:
        return None, 'UNRESOLVED_ENTRY'
    if s.family == INDEX and (day == 4 or t != s.decision):
        return None, 'INDEX_ENTRY_SCHEDULE'
    if policy == 'FRIDAY_OPEN' and day == 4:
        return None, 'FRIDAY_ENTRY_VETO'
    return i, None


def setup(market, s, i):
    bid = float(market.feed['o'][i])
    t = int(market.feed['t'][i])
    side = s.side
    stop = bid - side*s.atr + (market.spread if side==-1 else 0.)
    if s.family == INDEX:
        stop += market.spread / 2
    stop_bid = stop - (market.spread if side==-1 else 0.)
    ent = (bid,side,market.slip)
    unit_risk = -market.roundtrip(ent,t,stop_bid,market.slip,0.)['net']
    natural = s.atr*market.usd_unit(t,bid)
    if unit_risk <= 0 or natural <= 0:
        raise ValueError('invalid initial stop risk')
    return ent, stop, unit_risk, natural


def d1_stop(market, stop, side, bid, low, high):
    """Trigger with Bid for BUY and Ask for SELL, gap priced at the open."""
    shift = market.spread if side==-1 else 0.
    if side*(bid+shift-stop) <= 0:
        return 'SL_GAP', bid
    extreme = low if side==1 else high
    if side*(extreme+shift-stop) <= 0:
        return 'SL', stop-shift
    return None, None


def path(market, s, exit_ma, policy, raw=False):
    f = market.feed
    index = s.family == INDEX
    i, reject = next_entry(market,s,policy)
    if reject:
        return None,reject
    ent, stop, unit_risk, natural = setup(market,s,i)
    start = int(f['t'][i])
    side = s.side
    funding, last, gaps = 0., start, 0
    path_values = []
    marks = []
    result = None
    for j in range(i,len(f['t'])):
        t = int(f['t'][j])
        if t >= STOP:
            raise ValueError('price outside Development')
        if j>i and policy=='FRIDAY_OPEN' and date(t).isocalendar()[:2] != date(start).isocalendar()[:2]:
            _, end, pnl = result
            result = ('FRIDAY_UNPRICED',end,pnl)
            break
        bid = float(f['o'][j])
        if j > i:
            funding += market.funding(last,t,bid,side)
            gaps += int(t-last > (3*DAY if date(last).weekday()==4 else DAY))
        last = t
        open_pnl = market.roundtrip(ent,t,bid,market.slip,funding)
        path_values.append((t,open_pnl['net'],market.margin(t,bid)))
        marks.append((t,open_pnl['net']))
        deadline = policy=='FRIDAY_OPEN' and date(t).weekday()==4
        age = j-i
        if raw:
            if age >= (1 if index else 5):
                result = ('MARKOUT',t,open_pnl)
                break
            continue
        if deadline:
            result = ('FRIDAY_CUTOFF',t,open_pnl)
            break
        if index and age>0 and (age>=3 or f['c'][j-1]>exit_ma[j-1]):
            result = ('INDEX_TIME' if age>=3 else 'INDEX_REBOUND',t,open_pnl)
            break
        if not index and age>0:
            previous = j-1
            proposal = float(f['c'][previous]-side*3*f['atr'][previous])
            if isfinite(proposal) and side*proposal>side*stop:
                stop=proposal
        reason,fill = d1_stop(market,stop,side,bid,float(f['l'][j]),float(f['h'][j]))
        close_time = int(min(f['complete'][j],STOP)-1)
        if reason=='SL_GAP':
            result = (reason,t,open_pnl)
            break
        if reason:
            pnl = market.roundtrip(ent,t,fill,market.slip,funding,closed=True)
            path_values.append((close_time,pnl['net'],market.margin(t,fill,True)))
            marks.append((close_time,pnl['net']))
            result = (reason,close_time,pnl)
            break
        close = float(f['c'][j])
        pnl = market.roundtrip(ent,t,close,market.slip,funding,closed=True)
        path_values.append((close_time,pnl['net'],market.margin(t,close,True)))
        marks.append((close_time,pnl['net']))
        result = ('OPEN_AT_DEV_END',close_time,pnl)
    if result is None or not START<=s.decision<=start<=result[1]<STOP:
        if raw and result is None:
            return None,'NO_MARKOUT_BEFORE_LOCK'
        raise ValueError('unresolved causal timeline')
    reason,end,pnl = result
    peak = max((0.,start), *((net,-t) for t,net in marks))
    mfe = max(0.,peak[0])/unit_risk
    mae = max(0.,-min(net for _,net in marks))/unit_risk
    peak_hours = (-peak[1]-start)/3600 if mfe>0 else None
    cost = market.roundtrip(ent,start,ent[0],market.slip,0.)
    return {'key':s.key,'family':s.family,'asset':s.asset,'side':side,'decision':s.decision,
            'entry':start,'exit':end,'year':date(start).year, 'reason':reason,'closed':reason not in ('OPEN_AT_DEV_END','FRIDAY_UNPRICED'),
            'features':s.features|{'weekday':date(start).strftime('%a'),'known_at':s.decision},
            'risk_per_lot':unit_risk,'natural_risk_per_lot':natural,'margin_per_lot':path_values[0][2],
            'friction_per_lot':sum(cost[x] for x in ('spread','commission','slippage')),
            'mfe_R_actual_risk':mfe,'mae_R_actual_risk':mae,'time_to_peak_hours':peak_hours,
            'held_bar_open_gap_flags':gaps,'path':path_values,**pnl},None

def sized_lots(trade, budget, spec):
    step = spec['volume_step']
    lot = min(spec['volume_max'], floor(budget*.005/trade['risk_per_lot']/step+1e-10)*step)
    return round(lot,8) if lot>=spec['volume_min'] else 0.


def select(rows, budget, markets):
    active = {}
    booked = []
    settled = 0.
    skips = Counter()
    ordered = sorted(rows,key=lambda r:(r['entry'],FAMILIES.index(r['family']),ASSETS.index(r['asset'])))
    for t in ordered:
        asset = t['asset']
        when = t['entry']
        for name,p in tuple(active.items()):
            if p['exit'] <= when:
                settled += p['net']*p['lots'] if p['closed'] else 0.
                del active[name]
        if asset in active:
            skips['ONE_POSITION_PER_ASSET']+=1
            continue
        lots = sized_lots(t,budget,markets[asset].spec)
        if not lots:
            skips['BELOW_MIN_LOT']+=1
            continue
        floating, margin = 0.,0.
        for p in active.values():
            i = bisect_left(p['path'],(when,float('inf'))) - 1
            pmark, pmargin = p['path'][i][1:]
            floating += pmark*p['lots']
            margin += pmargin*p['lots']
        equity = budget + settled + floating
        initial_margin = t['margin_per_lot']*lots
        if equity<=0 or margin+initial_margin>.5*equity:
            skips['MARGIN_CAP']+=1
            continue
        accepted = t | {'lots':lots,'initial_margin_usd':initial_margin,
                        'portfolio_used_margin_pct_on_entry':100*(margin+initial_margin)/equity}
        active[asset]=accepted
        booked.append(accepted)
    return booked,dict(skips)


def equity(rows, budget):
    moves = defaultdict(lambda:np.zeros(3))
    daily = defaultdict(lambda:defaultdict(float))
    for trade in rows:
        lot = trade['lots']
        before_pnl, before_margin, before_count = 0.,0.,0
        for i,(when,pnl,margin) in enumerate(trade['path']):
            # A close releases margin at its recorded fill. An open terminal
            # position remains marked for the ending-equity bridge.
            count = int(i!=len(trade['path'])-1 or not trade['closed'])
            margin = margin*count
            delta = (pnl-before_pnl)*lot
            # Keep the path but release the residual on an unpriced Standard break.
            if i==len(trade['path'])-1 and trade['reason']=='FRIDAY_UNPRICED':
                delta -= pnl*lot
                margin,count=0.,0
            moves[when] += (delta,(margin-before_margin)*lot,count-before_count)
            day = when//DAY
            daily[trade['asset']][day]+=delta
            daily[trade['family']][day]+=delta
            before_pnl,before_margin,before_count = pnl,margin,count
    if not moves:
        return dict(max_drawdown_R=0.,peak_margin_usd=0.,peak_margin_pct=0.,
                    peak_simultaneous_positions=0,ending_equity_usd=float(budget)),daily
    timeline = np.cumsum(np.array([moves[t] for t in sorted(moves)]),axis=0)
    net, margin, count = timeline.T
    dd = np.maximum.accumulate(np.r_[0.,net])[1:]-net
    with np.errstate(divide='ignore',invalid='ignore'):
        margin_pct = np.divide(100*margin,budget+net,out=np.full_like(margin,np.nan),where=budget+net>0)
    return dict(max_drawdown_R=float(max(dd))/(budget*.005),peak_margin_usd=float(max(0.,max(margin))),
                peak_margin_pct=float(max(0.,np.nanmax(margin_pct))) if not np.isnan(margin_pct).all() else None,
                peak_simultaneous_positions=int(round(max(count))),
                ending_equity_usd=float(budget+net[-1])),daily


def period_stats(rows, budget, years):
    years = tuple(years)
    scoped = [t for t in rows if t['year'] in years]
    closed = [t for t in scoped if t['closed']]
    nominal = budget*.005
    parts = {k:sum(t[k]*t['lots']/nominal for t in closed) for k in PARTS}
    marked,daily = equity(scoped,budget)
    winners = sorted((t['net']*t['lots']/nominal for t in closed if t['net']>0),reverse=True)
    pool = sum(winners)
    result = dict(trades=len(closed),entries=len(scoped),cadence_per_year=len(closed)/len(years),
                  unresolved_cutoff=sum(t['reason']=='FRIDAY_UNPRICED' for t in scoped),
                  terminal_open=sum(t['reason']=='OPEN_AT_DEV_END' for t in scoped),
                  terminal_open_mark_R=sum(t['net']*t['lots']/nominal for t in scoped if t['reason']=='OPEN_AT_DEV_END'),
                  winrate=len(winners)/len(closed) if closed else None,
                  pnl_R=parts, net_R_per_year=parts['net']/len(years),
                  usd_per_year=parts['net']*nominal/len(years), **marked)
    expected=result['pnl_R']['net']+result['terminal_open_mark_R']
    if abs((result['ending_equity_usd']-budget)/nominal-expected)>1e-7:
        raise ValueError('equity reconciliation failed')
    result['net_over_dd']=parts['net']/marked['max_drawdown_R'] if marked['max_drawdown_R'] else None
    for n in (2,5,10):
        remainder=sum(winners[:n])
        result[f'top{n}_share']=remainder/pool if pool else None
        result[f'ex_top{n}_net_R']=parts['net']-remainder
    return result,daily


def correlation(daily):
    days = range(START//DAY,STOP//DAY)
    values = {label:np.asarray([returns.get(d,0.) for d in days]) for label,returns in daily.items()}
    return {a:{b:float(np.corrcoef(x,y)[0,1]) if np.std(x)>0 and np.std(y)>0 else None
               for b,y in values.items()} for a,x in values.items()}


def stage0(rows, expected):
    by_year={}
    for y in CLUSTERS['ALL']:
        subset=[t for t in rows if t['year']==y]
        vals={k:sum(t[k]/t['risk_per_lot'] for t in subset) for k in PARTS}
        friction=sum(vals[k] for k in ('spread','commission','slippage'))
        by_year[str(y)]={'n':len(subset),'pnl_R':vals,'execution_R':friction,
                         'pass':bool(subset and vals['net']>friction)}
    med=(float(np.median([t['friction_per_lot'] for t in rows])) /
         float(np.median([t['natural_risk_per_lot'] for t in rows]))) if rows else None
    retain=sum(t['friction_per_lot']/t['natural_risk_per_lot']<=.12 for t in rows)/len(rows) if rows else None
    return dict(count=len(rows),expected=expected,median_cost_stop_ratio=med,retained_ratio=retain,by_year=by_year,
                pass_gate=bool(med is not None and med<=.12 and retain>=.5 and all(t['pass'] for t in by_year.values())))


def paired(rows, budget, markets):
    s, f = ({t['key']:t for t in rows[p]} for p in POLICIES)
    values={}
    for k in s.keys() & f.keys():
        swing,friday=s[k],f[k]
        if not swing['closed'] or not friday['closed']:
            continue
        if any(swing[v]!=friday[v] for v in ('entry','asset','side','risk_per_lot')):
            raise ValueError('paired entry drift')
        lot=sized_lots(swing,budget,markets[swing['asset']].spec)
        # Prices and costs are held fixed apart from exits and their paths.
        if lot:
            scale=lot/(budget*.005)
            values[k]={'swing_net_per_lot':swing['net'],'friday_net_per_lot':friday['net'],
                       'delta_R':{x:(swing[x]-friday[x])*scale for x in PARTS},'year':swing['year']}
    return values


def pair_stats(pairs):
    return {c:{'n':sum(v['year'] in years for v in pairs.values()),
               'delta_R':{x:sum(v['delta_R'][x] for v in pairs.values() if v['year'] in years) for x in PARTS}}
            for c,years in CLUSTERS.items()}


def gates(stats, raw, minimum, group):
    a,b,w=(stats[str(x)] for x in ('A','B','ALL'))
    return dict(stage0=raw['pass_gate'],net_both=a['net_R_per_year']>0 and b['net_R_per_year']>0,velocity=w['net_R_per_year']>=minimum,
                drawdown=w['max_drawdown_R']<=20,concentration=w['ex_top2_net_R']>0 and (w['top2_share'] or 0)<=.5,
                margin=w['peak_margin_pct'] is not None and w['peak_margin_pct']<=50,
                historical_carry_input=group not in (CARRY,PORTFOLIO))


def run(job):
    feed,markets,pins=native_book(job)
    paths={p:[] for p in POLICIES}
    raws=[]; counts=Counter(); unresolved=defaultdict(Counter)
    for asset,m in markets.items():
        intents,exit_ma=signals(asset,feed[asset],m)
        for sig in intents:
            group=(sig.family,asset)
            counts[group]+=1
            raw,why=path(m,sig,exit_ma,'SWING',raw=True)
            if raw:
                raws.append(raw)
            else:
                unresolved['RAW'][(*group,why)]+=1
            for policy in POLICIES:
                row,why=path(m,sig,exit_ma,policy)
                if row:
                    paths[policy].append(row)
                else:
                    unresolved[policy][(*group,why)]+=1
        print(f'{asset}: {len(intents)} fixed intents',flush=True)
    selectors={family:lambda t,k=family:t['family']==k for family in FAMILIES}
    selectors[PORTFOLIO]=lambda t:True
    for fam,asset in sorted(counts):
        selectors[f'{fam}:{asset}']=lambda t,k=fam,a=asset:t['family']==k and t['asset']==a
    views={}
    ledger=[]
    for name,where in selectors.items():
        name_out=views[name]={'raw':stage0([r for r in raws if where(r)],sum(v for (k,a),v in counts.items()
                                                         if where({'family':k,'asset':a}))), 'books':{}}
        sliced={p:[t for t in paths[p] if where(t)] for p in POLICIES}
        for budget in BOOKS:
            pairs=paired(sliced,budget,markets)
            book=name_out['books'][str(budget)]={'paired':pair_stats(pairs)}
            for policy in POLICIES:
                admitted,skips=select(sliced[policy],budget,markets)
                cohorts={k:period_stats(admitted,budget,y) for k,y in CLUSTERS.items()}
                stats={k:p[0] for k,p in cohorts.items()}
                book[policy]={'metrics':stats,'admission_skips':skips,
                              'daily_correlation':{k:correlation(p[1]) for k,p in cohorts.items()}}
                if policy=='SWING':
                    book[policy]['gates']=gates(stats,name_out['raw'],15 if name==PORTFOLIO else 5,name.split(':')[0])
                # The same portfolio fill may appear as an individual sleeve/proxy.
                # Keep those views separate when describing winner pools.
                if name in (*FAMILIES,PORTFOLIO):
                    for t in admitted:
                        pair=pairs.get(t['key'])
                        delta=(pair['swing_net_per_lot']-t['net'])*t['lots']/(budget*.005) if pair else None
                        recorded={k:v for k,v in t.items() if k!='path'}
                        ledger.append(recorded | {'view':name,'policy':policy,'budget':budget,'paired_extra_net_R':delta})
        name_out['candidate']=all(all(b['SWING']['gates'].values()) for b in name_out['books'].values())
    pq.write_table(pa.Table.from_pylist(ledger),job/'SWING_TRADE_LEDGER.parquet',compression='zstd')
    write(job/'SWING_SCREEN.json',dict(schema='ftmo-swing-dev-v1',holdout_lock_sha256=LOCK_PIN,holdout_prices_opened=False,
        input_sha256=pins|{'runner':sha(Path(__file__))},views=views,signal_counts={'|'.join(k):v for k,v in counts.items()},
        signal_rejects={p:{'|'.join(k):v for k,v in c.items()} for p,c in unresolved.items()},
        candidates=[k for k,v in views.items() if v['candidate']]))
    print(f'Swing Development complete: {len(views)} views, {len(ledger)} ledger rows',flush=True)


if __name__ == '__main__':
    run(Path(sys.argv[1]))

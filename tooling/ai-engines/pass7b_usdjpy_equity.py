"""Frozen Tokyo-box M1 execution and per-account FTMO equity replay."""

from collections import Counter
from dataclasses import dataclass
from math import floor, fsum
from zoneinfo import ZoneInfo

import numpy as np

import pass5_usdjpy_tokyo as base
from pass6_breakout_execution import MINUTE, SL, entries, jpy_mark, stop_price
from selective_win_diagnosis import classify

COMMISSION = 5.
CONTRACT = 100_000.
PIP = .01
BASE_SIDE_SLIPPAGE = .002
PROFILE = {'M1_Real_Base':0., 'M1_Real_Stress_05':.005, 'M1_Real_Stress_10':.01}
RISKS = (.002,.0025,.003,.004)
PRAGUE = ZoneInfo('Europe/Prague')


@dataclass(frozen=True)
class Exit:
    index: int
    price: float
    at_open: bool
    reason: str


@dataclass
class Trade:
    day: int
    entry: int
    side: int
    entry_price: float
    entry_half: float
    edge: float
    structural_risk: float
    execution: Exit
    grid: np.ndarray
    dual_entry: bool
    offsets: np.ndarray | None = None

    def second_at(self, index):
        minute = index if self.offsets is None else int(self.offsets[index])
        return self.day+minute*MINUTE

    @property
    def entry_second(self):
        return self.second_at(self.entry)


def box_edges(quotes):
    # The box uses mean(Bid/Ask extrema), matching Pass 6's M1 convention.
    return float(((quotes[:,1]+quotes[:,5])/2).max()),float(((quotes[:,2]+quotes[:,6])/2).min())


def select(day, quotes, *, offsets=None):
    if offsets is not None and (len(offsets)!=len(quotes) or offsets[0]!=0
            or np.any(np.diff(offsets)<=0)):
        raise ValueError('Invalid observed M1 offsets')
    box_end, window_end = (180,600) if offsets is None else np.searchsorted(offsets,[180,600])
    top,bottom=box_edges(quotes[:box_end])
    up=quotes[box_end:window_end,5]>=top-1e-10
    down=quotes[box_end:window_end,2]<=bottom+1e-10
    hits=np.flatnonzero(up|down)
    if not len(hits):
        return None,int(np.count_nonzero(up&down))
    at=int(box_end)+int(hits[0])
    choices=list(entries(base.Bar(*quotes[at,:4]),base.Bar(*quotes[at,4:]),top,bottom))
    out=[]
    for side,price,edge in choices:
        liquid=quotes[:,0:4] if side==1 else quotes[:,4:8]
        initial_hit=stop_price(base.Bar(*quotes[at,:4]),base.Bar(*quotes[at,4:]),
                               side,edge,entry_bar=True)
        tail=liquid[at+1:-1,2 if side==1 else 1]
        flags=np.flatnonzero(tail<=edge+1e-10 if side==1 else tail>=edge-1e-10)
        if initial_hit is not None:
            close=Exit(at,edge,False,SL)
        elif len(flags):
            i=at+1+int(flags[0])
            op=float(liquid[i,0])
            fill=min(op,edge) if side==1 else max(op,edge)
            close=Exit(i,float(fill),fill==op,SL)
        else:
            close=Exit(len(quotes)-1,float(liquid[-1,0]),True,'HARD_FLAT')
        half=float((quotes[at,4]-quotes[at,0])/2)
        risk=abs(price-edge)*CONTRACT/(price-side*half)
        if risk<=0:
            raise ValueError('Zero structural risk')
        out.append(Trade(day,at,side,price,half,edge,risk,close,
                         quotes[at:close.index+1],len(choices)>1,offsets))
    return min(out,key=lambda r:closed(r,0.)['net']/r.structural_risk),int(np.count_nonzero(up&down))


def closed(trade, addon):
    side=trade.side
    last=trade.grid[-1]
    final_half=float((last[4]-last[0])/2)
    return jpy_mark(side,trade.entry_price-side*trade.entry_half,
                    trade.execution.price+side*final_half,trade.entry_half,final_half,addon)


def path(trade, addon):
    side=trade.side
    quote=trade.grid
    liq=quote[:,:4] if side==1 else quote[:,4:]
    mids=(quote[:,0]+quote[:,4])/2
    half=(quote[:,4]-quote[:,0])/2
    now=trade.entry_price+side*(BASE_SIDE_SLIPPAGE+addon)
    def open_value(price,rate):
        return side*(price-now)*CONTRACT/rate-COMMISSION/2
    current=open_value(liq[:,0],mids)
    high=open_value(liq[:,1 if side==1 else 2],liq[:,1 if side==1 else 2]+side*half)
    low=open_value(liq[:,2 if side==1 else 1],liq[:,2 if side==1 else 1]+side*half)
    last=open_value(liq[:,3],(quote[:,3]+quote[:,7])/2)

    # First-minute highs may predate entry. Keep the after-fill opening estimate and close.
    current[0]=open_value(trade.entry_price-2*side*trade.entry_half,
                          trade.entry_price-side*trade.entry_half)
    high[0]=max(current[0],last[0])
    low[0]=min(current[0],low[0],last[0])
    terminal=closed(trade,addon)['net']
    if trade.execution.index==trade.entry or trade.execution.at_open:
        current[-1]=high[-1]=low[-1]=last[-1]=terminal
    else:
        high[-1]=max(current[-1],terminal)
        low[-1]=min(current[-1],terminal)
        last[-1]=terminal
    return np.column_stack((current,high,low,last))


def record(trade, addon):
    cash=closed(trade,addon)
    side=trade.side
    risk=trade.structural_risk
    stop_net = jpy_mark(side,trade.entry_price-side*trade.entry_half,
                       trade.edge+side*trade.entry_half,trade.entry_half,trade.entry_half,addon)['net']
    end=trade.execution
    # Match Pass 6's conditional taxonomy on the same evidence window.
    first_mid=trade.entry_price-side*trade.entry_half
    start=jpy_mark(side,first_mid,first_mid,trade.entry_half,trade.entry_half,addon)['net']
    paired=trade.grid[1:-1]
    liquidation=paired[:,:4] if side==1 else paired[:,4:]
    half=(paired[:,4]-paired[:,0])/2
    prices=liquidation[:,1:3]
    rate=prices+side*half[:,None]
    past=(side*(prices-trade.entry_price)-(.004+addon))*CONTRACT/rate-COMMISSION
    extrema=np.r_[start,cash['net'],past.ravel()]
    exit_second=trade.second_at(end.index)+int(not end.at_open)*MINUTE
    post=dict(net_R=cash['net']/risk, swap_R=0., paired_net_R=None,
              mfe_R=max(0.,float(extrema.max())/risk),mae_R=max(0.,-float(extrema.min())/risk),
              holding_hours=max(0.,(exit_second-trade.entry_second-MINUTE)/base.HOUR),
              calendar_exit=end.reason=='HARD_FLAT')
    return dict(day=base.date(trade.day).date().isoformat(),year=base.date(trade.day).year,
        entry=trade.entry_second,exit=exit_second,
        side=side,reason=end.reason,entry_bar_forced_stop=end.index==trade.entry,
        dual_entry=trade.dual_entry,entry_price=trade.entry_price,stop=trade.edge,
        initial_risk_usd=risk,stop_risk_with_cost_usd=-stop_net,
        gross_R=cash['gross']/risk,friction_R=cash['cost']/risk,net_usd_per_lot=cash['net'],
        **post,winner_label=classify(post),conditional_geometry_label=classify(post|{'calendar_exit':False}))


def drawdown_points(marks):
    # The high-then-low envelope is adverse for peak-to-valley risk.
    return marks.ravel()


def years_and_clusters(closed, key):
    yearly={str(y):fsum(r[key] for r in closed if r['year']==y) for y in base.YEAR}
    groups={k:fsum(yearly[str(y)] for y in v) for k,v in base.CLUSTERS.items()}
    annual={k:groups[k]/len(v) for k,v in base.CLUSTERS.items()}
    annual['all']=fsum(yearly.values())/len(base.YEAR)
    return yearly,groups,annual


def trade_summary(rows, dd):
    result=base.sl_summary(rows)
    y,g,a=years_and_clusters(rows,'net_R')
    wins=sorted((r['net_R'] for r in rows if r['net_R']>0),reverse=True)
    top=fsum(wins[:10])
    return result|dict(years=y,clusters=g,net_R_annual=a,positive_years=sum(v>0 for v in y.values()),
        floating_drawdown_R=dd,top10_share_positive=top/fsum(wins) if wins else None,
        year_detail={str(i):base.sl_summary([r for r in rows if r['year']==i]) for i in base.YEAR},
        cluster_detail={k:base.sl_summary([r for r in rows if r['year'] in v])
                        for k,v in base.CLUSTERS.items()},
        net_R_without_top10=result['net_R']-top,
        direction={k:base.sl_summary([r for r in rows if r['side']==i])
                   for k,i in [('BUY',1),('SELL',-1)]},
        dual_entry_days=sum(r['dual_entry'] for r in rows),
        entry_and_sl_same_minute=sum(r['entry_bar_forced_stop'] for r in rows),
        ambiguous_first_minutes=sum(r['dual_entry'] or r['entry_bar_forced_stop'] for r in rows))


@dataclass(frozen=True)
class Account:
    label: str
    initial: int
    margin_per_lot: float
    minimum: float
    step: float
    maximum: float


def floor_lot(risk_usd, stop_usd, spec):
    if stop_usd<=0:
        raise ValueError('Nonpositive stop cost')
    steps = floor(min(risk_usd/stop_usd,spec.maximum)/spec.step+1e-10)
    return round(steps*spec.step,8)


def prague_day(ts):
    return base.date(ts).astimezone(PRAGUE).date()


class EquityMetrics:
    def __init__(self, initial, start, days):
        self.peak=initial
        self.peak_at=start
        self.dd=0.
        self.dd_pct_of_peak=0.
        self.daily=0.
        self.max_age=(0,0)
        self.days=np.asarray(days,dtype=np.int64)
        self.minimum=np.inf

    def add(self, times, values, daily_balance):
        previous_peak=self.peak
        peaks=np.maximum.accumulate(np.r_[previous_peak,values])[1:]
        self.dd=max(self.dd,float(np.max(peaks-values)))
        self.dd_pct_of_peak=max(self.dd_pct_of_peak,float(np.max((peaks-values)/peaks)*100))
        self.minimum=min(self.minimum,float(np.min(values)))
        self.daily=max(self.daily,float(daily_balance-np.min(values)))
        hits=np.flatnonzero(values>=peaks)
        if len(hits):
            starts=np.r_[self.peak_at,times[hits[:-1]]]
            ends=times[hits]
            # Adjacent marks at the same peak add at most the elapsed sample interval.
            active = np.r_[True, np.diff(hits)>1]
            if hits[0]==0 and values[0]>=previous_peak:
                active[0]=False
            if active.any():
                self.update_age(starts[active],ends[active])
            self.peak_at=int(times[hits[-1]])
        self.peak=float(peaks[-1])
        if values[-1]<self.peak:
            self.update_age(np.array([self.peak_at]),np.array([times[-1]]))

    def update_age(self, starts, ends):
        calendar=ends-starts
        max_seconds=int(calendar.max())
        if max_seconds>=self.max_age[0]:
            counts=np.searchsorted(self.days,ends//base.DAY,side='right')-np.searchsorted(
                self.days,starts//base.DAY,side='right')
            self.max_age=max(self.max_age,(max_seconds,int(counts[calendar==max_seconds].max())))


def account_replay(spec, risk, rows, marks, trading_days, *, observed_times=None):
    initial=spec.initial
    balance=float(initial)
    budget=initial*risk
    metrics=EquityMetrics(balance,base.START,trading_days)
    equity_points=EquityMetrics(balance,base.START,trading_days)
    ledger=[]
    skip=Counter()
    day=None
    day_balance=float(initial)
    max_margin=max_margin_equity=0.
    min_free=initial
    uneven=0
    round_changed=0
    last_ts=base.START
    clocks=observed_times if observed_times is not None else [None]*len(rows)
    for row, curve, clock in zip(rows,marks,clocks,strict=True):
        entry=row['entry']
        current_day=prague_day(entry)
        if prague_day(row['exit'])!=current_day:
            raise ValueError('Flat rule crossed Prague reset')
        if current_day!=day:
            day=current_day
            day_balance=balance
        lot=floor_lot(budget,row['stop_risk_with_cost_usd'],spec)
        if lot+1e-10<spec.minimum:
            skip['min_lot']+=1
            continue
        margin=lot*spec.margin_per_lot
        if margin+lot*COMMISSION/2>balance:
            skip['initial_margin']+=1
            continue
        net=row['net_usd_per_lot']*lot
        realized_risk=row['stop_risk_with_cost_usd']*lot
        round_changed+=int(realized_risk<budget-1e-7)
        uneven+=int(realized_risk < budget*.9-1e-7)
        eq=balance+lot*curve
        intra_time=entry+np.arange(len(curve))*MINUTE if clock is None else clock
        if (len(intra_time)!=len(curve) or intra_time[0]!=entry or intra_time[-1]>row['exit']
                or np.any(np.diff(intra_time)<=0)):
            raise ValueError('Equity curve timestamps do not match observed path')
        stamps=np.repeat(intra_time,4)
        # Insert the pre-entry equity snapshot to measure flat intervals between trades.
        times=np.r_[entry,stamps,row['exit']]
        envelope=np.r_[balance,drawdown_points(eq),balance+net]
        observed=np.r_[balance,eq[:,(0,3)].ravel(),balance+net]
        observed_time=np.r_[entry,np.repeat(intra_time,2),row['exit']]
        metrics.add(times,envelope,day_balance)
        equity_points.add(observed_time,observed,day_balance)
        ledger.append(dict(day=row['day'],year=row['year'],lots=lot,balance_before=balance,
                           net_usd=net,balance_after=balance+net,usable_risk_usd=realized_risk,
                           margin_usd=margin))
        balance+=net
        low=float(eq.min())
        min_free=min(min_free,low-margin)
        max_margin=max(max_margin,margin)
        max_margin_equity=max(max_margin_equity,100*margin/low if low>0 else float('inf'))
        last_ts=row['exit']
    # If the last equity is below an observed peak, right-censor at the end of Development.
    for meter in (metrics,equity_points):
        if balance<meter.peak and last_ts<base.STOP:
            meter.update_age(np.array([meter.peak_at]),np.array([base.STOP]))
    year,groups,annual=years_and_clusters(ledger,'net_usd')
    static=100*max(0.,initial-min(initial,metrics.minimum))/initial
    daily=100*metrics.daily/initial
    peak=100*metrics.dd/initial
    age=metrics.max_age
    return dict(account=spec.label,initial=initial,risk_pct=100*risk,executed=len(ledger),attempted=len(rows),
                skip=dict(skip),rounded_trade_count=round_changed,under_90pct_budget_count=uneven,
                net_usd=balance-initial,years_net_usd=year,cluster_net_usd=groups,
                annual_usd=annual,annual_pct={k:100*v/initial for k,v in annual.items()},
                positive_years=sum(p>0 for p in year.values()),worst_daily_loss_pct=daily,
                peak_floating_dd_pct=peak,open_close_dd_pct=100*equity_points.dd/initial,
                peak_floating_dd_pct_of_peak=metrics.dd_pct_of_peak,
                static_loss_pct=static,max_underwater_calendar_days=age[0]/base.DAY,
                max_underwater_trading_days=age[1],max_underwater_months=age[0]/base.DAY/(365.2425/12),
                margin_peak_usd=max_margin,margin_peak_pct_initial=100*max_margin/initial,
                margin_peak_pct_equity=max_margin_equity if np.isfinite(max_margin_equity) else None,
                minimum_free_margin_usd=min_free,hard_daily_breached=daily>5,hard_static_breached=static>10,
                daily_buffer_2_5=daily<=2.5,peak_buffer_7_5=peak<=7.5,peak_buffer_8=peak<=8),ledger

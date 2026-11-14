"""Shared-account tick replay, fixed registered sizing and reconciled rewards."""
from collections import Counter,defaultdict
from datetime import date,datetime,timedelta,timezone
from zoneinfo import ZoneInfo
import numpy as np

from prop_campaign_source import START,END,FINAL,HOUR,DAY,stamp
from prop_campaign_exits import costs,quantity,funding_rate
from xau_h1_execution import commission,cents
from xau_h1_stage0_scan import funding_events

PRAGUE=ZoneInfo('Europe/Prague')
CAPITAL=50000000  # milli-USD; mark precision is retained, cash fees are cents.


def utc(at):
    return datetime.fromtimestamp(at/1000,timezone.utc)


def stats(values):
    peaks=np.maximum.accumulate(values)
    return dict(low=int(values.min()),high=int(values.max()),
        dd=int((peaks-values).max()),last=int(values[-1]))


class Account:
    def __init__(self,start,end,cell,rolling=False,fixed_risk=150):
        self.start=start;self.end=end;self.cell=cell;self.rolling=rolling;self.fixed_risk=fixed_risk
        self.balance=self.anchor=self.peak=CAPITAL
        self.active={};self.accrued={};self.phase=1;self.gate=start-1
        self.dd=self.daily=self.static=0;self.phase_dd=self.phase_daily=0
        self.phase_days=set();self.passes=[];self.breach=None;self.rejected=Counter()
        self.accepted=[];self.closed=[];self.funded_first=None;self.last_payout=None
        self.payouts=[];self.max_concurrency=0;self.throttled=0;self.float=0
        self.daily_marks=[];self.stale_resets=[];self.bridges=[]
        self.last_quote=None

    def risk(self,equity):
        if not self.rolling:return self.fixed_risk
        risk={1:250,2:175,3:125}[self.phase]
        if self.balance-self.anchor<-900000 or equity<47750000:
            return min(risk,125)
        return risk

    def floating(self,trades,quote):
        if not self.active:return 0
        if quote is None:raise ValueError('missing_open_mark')
        value=0
        for i,(q,risk) in self.active.items():
            t=trades[i];sign=1 if t['side']=='BUY' else -1
            p=quote[1] if sign==1 else quote[2]
            # Match Anchor0: pending market-exit slippage in floating; both legs
            # and cent-rounded fees settle in closed cash. Full slip in reserve.
            value+=sign*q*(p-t['entry_price_units'])-200*q+self.accrued[i]
        return value

    def metrics(self,low,high,dd=0):
        self.dd=max(self.dd,self.peak-low,dd)
        self.phase_dd=max(self.phase_dd,self.peak-low,dd)
        self.peak=max(self.peak,high)
        self.daily=max(self.daily,self.anchor-low)
        self.phase_daily=max(self.phase_daily,self.anchor-low)
        self.static=max(self.static,CAPITAL-low)

    def check(self,at,floating):
        self.float=floating
        equity=self.balance+floating
        self.metrics(equity,equity)
        if not self.rolling or self.breach:return
        if equity<max(self.anchor-2500000,45000000):
            self.breach=dict(at=at,phase=self.phase,equity_usd=equity/1000,
                daily=equity<self.anchor-2500000,overall=equity<45000000)
            return
        if self.phase<3 and not self.active and self.balance>=CAPITAL+(5000000 if self.phase==1 else 2500000) and len(self.phase_days)>=4:
            self.passes.append(dict(phase=self.phase,at=at,days=len(self.phase_days),
                balance_usd=self.balance/1000,phase_dd_pct=self.phase_dd/500000,
                phase_daily_loss_pct=self.phase_daily/500000))
            self.phase+=1;self.balance=self.anchor=self.peak=CAPITAL
            self.phase_dd=self.phase_daily=0;self.phase_days=set();self.gate=at

    def reward(self,at):
        if self.phase!=3 or self.active or self.funded_first is None:return
        since=self.last_payout if self.last_payout is not None else self.funded_first
        profit=self.balance-CAPITAL
        if at-since<30*DAY or profit<20000:return
        # Debit the whole account profit. Trader/firm split must sum to debit.
        trader=(profit*80//100)//10*10
        self.payouts.append(dict(at=at,gross_removed_usd=profit/1000,
            trader_usd=trader/1000,firm_usd=(profit-trader)/1000,
            before_usd=self.balance/1000,after_usd=50000))
        self.balance-=profit;self.anchor=self.peak=CAPITAL
        self.last_payout=at;self.phase_dd=self.phase_daily=0
        self.gate=at

    def reserve_floor(self,trades,new_id,q,entry_fee):
        """Worst declared initial/protected stop plus remaining negative costs."""
        v=self.balance-entry_fee
        positions=dict(self.active);positions[new_id]=(q,0)
        for i,(size,_) in positions.items():
            t=trades[i];sign=1 if t['side']=='BUY' else -1
            # Initial stop is conservative even if a protection arms later.
            stop=t['stop_units'];gross=sign*size*(stop-t['entry_price_units'])
            end=t.get('deadline_msc')
            if type(end) is not int or end<t['entry_msc']:
                raise ValueError('missing_or_invalid_prelocked_funding_horizon')
            # The stop exit is unknown pretrade. Reserve through the holding
            # deadline even for positions whose replay later stops out early.
            future=sum(min(0,funding_rate(t['side'],self.cell)*e['multiplier'])*size*1000
                for e in funding_events(t['entry_msc'],end))
            v+=gross-size*400+int(round(future))-cents(commission(stop,size))*10
        return v

    def action(self,kind,at,i,trades,quote,mult=0):
        if at<self.start or at>=self.end or self.breach:return
        self.last_quote=quote
        if kind=='reset':
            equity=self.balance+self.floating(trades,quote)
            self.daily_marks.append([at,equity])
            if self.active:
                self.stale_resets.append(dict(at=at,age_ms=at-quote[0],active=len(self.active)))
            self.anchor=self.balance
            if self.rolling:self.reward(at)
        elif kind=='entry':
            t=trades[i]
            if t['decision_msc']<self.start or t['decision_msc']<=self.gate:
                self.rejected['PRESTART_OR_PHASE_GATE']+=1;return
            if any(trades[k]['decision_msc']==t['decision_msc'] and trades[k].get('asset','XAUUSD')==t.get('asset','XAUUSD') for k in self.active):
                self.rejected['ASSET_DECISION_COLLISION']+=1;return
            risk=self.risk(self.balance+self.floating(trades,quote));q=quantity(t,risk)
            entry_fee=cents(commission(t['entry_price_units'],q))*10
            if self.rolling and self.reserve_floor(trades,i,q,entry_fee)<max(self.anchor-2500000,45000000):
                self.rejected['SHARED_STOP_RESERVE']+=1;return
            if self.rolling and risk==125 and self.phase<3:self.throttled+=1
            self.active[i]=(q,risk);self.accrued[i]=0;self.balance-=entry_fee
            self.accepted.append(dict(trade=i,at=at,phase=self.phase,risk_usd=risk,ounces=q))
            self.phase_days.add(utc(at).astimezone(PRAGUE).date().isoformat())
            self.max_concurrency=max(self.max_concurrency,len(self.active))
            if self.phase==3 and self.funded_first is None:self.funded_first=at
        elif kind=='swap':
            if i in self.active:
                self.accrued[i]+=int(round(self.active[i][0]*funding_rate(trades[i]['side'],self.cell)*mult*1000))
        elif kind=='exit':
            if i not in self.active:return
            q,risk=self.active.pop(i);self.accrued.pop(i)
            t=trades[i];c=costs(t,self.cell,risk);net=cents(c['net_usd'])*10
            self.balance+=net+cents(commission(t['entry_price_units'],q))*10
            self.closed.append(dict(trade=i,at=at,phase=self.phase,risk_usd=risk,
                net_usd=net/1000,net_R=net/(risk*1000),costs=c))
        self.check(at,self.floating(trades,quote))
        if kind=='exit' and self.rolling and not self.breach:self.reward(at)

    def segment(self,rows,trades,cache):
        if not self.active or self.breach:return
        key=tuple(sorted((i,q) for i,(q,_) in self.active.items()))
        if key not in cache:
            values=np.zeros(len(rows),dtype='int64')
            for i,q in key:
                t=trades[i];sign=1 if t['side']=='BUY' else -1
                p=rows['b'].astype('int64') if sign==1 else rows['a'].astype('int64')
                values+=sign*q*(p-t['entry_price_units'])
            cache[key]=(stats(values),values)
        s,values=cache[key];offset=self.balance+sum(self.accrued.values())-sum(q*200 for q,_ in self.active.values())
        if self.rolling and offset+s['low']<max(self.anchor-2500000,45000000):
            ix=int(np.flatnonzero(offset+values<max(self.anchor-2500000,45000000))[0])
            sub=stats(values[:ix+1]);self.metrics(offset+sub['low'],offset+sub['high'],sub['dd'])
            self.check(int(rows['t'][ix]),offset+int(values[ix])-self.balance)
            return
        self.metrics(offset+s['low'],offset+s['high'],s['dd'])
        self.float=offset+s['last']-self.balance

    def dump(self):
        net=sum(r['net_usd'] for r in self.closed)
        expected=CAPITAL+int(round(net*1000))
        phase_profit=sum(int(round((p['balance_usd']-50000)*1000)) for p in self.passes)
        removed=sum(int(round(p['gross_removed_usd']*1000)) for p in self.payouts)
        unpaid=sum(cents(commission(self._trades[i]['entry_price_units'],q))*10 for i,(q,_) in self.active.items()) if self.active else 0
        if self.balance!=expected-phase_profit-removed-unpaid:
            raise ValueError('account_cash_bridge')
        return dict(start_msc=self.start,end_msc=self.end,cell=self.cell,rolling=self.rolling,
            phase=self.phase,phase_passes=self.passes,first_breach=self.breach,
            entries=len(self.accepted),closed_trades=len(self.closed),rejections=dict(self.rejected),
            accepted=self.accepted,closed=self.closed,balance_usd=self.balance/1000,
            net_usd=net,net_R=sum(r['net_R'] for r in self.closed),
            mean_net_R=np.mean([r['net_R'] for r in self.closed]).item() if self.closed else None,
            net_ex_top3_R=sum(sorted((r['net_R'] for r in self.closed),reverse=True)[3:]),
            max_equity_R_DD=self.dd/(self.fixed_risk*1000) if not self.rolling else None,
            peak_dd_pct=self.dd/500000,static_loss_pct=self.static/500000,worst_daily_loss_pct=self.daily/500000,
            max_concurrency=self.max_concurrency,throttled_entries=self.throttled,payouts=self.payouts,
            trader_payout_usd=sum(p['trader_usd'] for p in self.payouts),
            cash_bridge_verified=True,stale_midnight_marks=self.stale_resets,
            daily_equity_marks=self.daily_marks,prop_qualified=False,
            status='FAILED_MODEL_BREACH' if self.breach else 'FUNDED_CENSORED' if self.phase==3 else 'RIGHT_CENSORED')


def replay(trades,prices,accounts,end=FINAL):
    """One source traversal; exact weighted tick summaries reused across starts."""
    if not trades:return [c.dump() for c in accounts]
    actions=defaultdict(list)
    for i,t in enumerate(trades):
        actions[(t['entry_msc'],t['entry_quote_index'])].append(('entry',i,0))
        actions[(t['exit_msc'],t['exit_quote_index'])].append(('exit',i,0))
        for e in funding_events(t['entry_msc'],t['exit_msc']):
            actions[(e['at'],-1)].append(('swap',i,e['multiplier']))
    d=date(2022,1,1)
    while d<utc(end).date():
        at=int(datetime(d.year,d.month,d.day,tzinfo=PRAGUE).timestamp()*1000)
        if START<=at<end:actions[(at,-1)].append(('reset',None,0))
        d+=timedelta(days=1)
    keys=sorted(actions);cursor=0;last=None;active=set();tick_count=0
    first=min(t['entry_msc'] for t in trades)//HOUR*HOUR
    final=end-HOUR
    for c in accounts:c._trades=trades
    priority={'reset':0,'swap':1,'exit':2,'entry':3}
    def consume_segment(rows):
        nonlocal last,tick_count
        if not len(rows):return
        cache={}
        for c in accounts:
            if c.start<=int(rows['t'][0]) and int(rows['t'][-1])<c.end:
                c.segment(rows,trades,cache)
        last=[int(rows['t'][-1]),int(rows['b'][-1]),int(rows['a'][-1])]
        if active:tick_count+=len(rows)
    for hour in range(first,final+HOUR,HOUR):
        # No position can need a quote in an unrequested inactive hour.
        if hour in prices.files:
            a=prices.hour(hour)
        else:
            if active:raise ValueError('held_path_hour_unadmitted')
            a=np.empty(0,dtype=[('t','<i8'),('b','<i4'),('a','<i4')])
        j=0
        while cursor<len(keys) and keys[cursor][0]<hour+HOUR:
            key=keys[cursor];at,index=key
            cut=int(a['t'].searchsorted(at)) if index<0 else index
            consume_segment(a[j:cut])
            if index>=0:
                if cut>=len(a) or a['t'][cut]!=at:raise ValueError('tick_ordinal')
                last=[int(a['t'][cut]),int(a['b'][cut]),int(a['a'][cut])]
                for c in accounts:
                    if c.start<=at<c.end and not c.breach:
                        c.check(at,c.floating(trades,last))
            for kind,i,mult in sorted(actions[key],key=lambda r:(priority[r[0]],
                    trades[r[1]].get('recipe','') if r[1] is not None else '')):
                for c in accounts:c.action(kind,at,i,trades,last,mult)
                if kind=='entry':active.add(i)
                elif kind=='exit':active.remove(i)
            j=cut;cursor+=1
        consume_segment(a[j:])
        if hour% (1000*HOUR)==0:print('replay hour',utc(hour).isoformat(),flush=True)
    if active:raise ValueError('replay_not_flat')
    return [dict(c.dump(),source_tick_marks=tick_count) for c in accounts]


def annual(trades,prices,cell,years=(2022,2023)):
    accounts=[Account(stamp(f'{y}-01-01'),stamp(f'{y+1}-01-01'),cell) for y in years]
    rows=replay(trades,prices,accounts,end=stamp(f'{max(years)+1}-01-01'))
    for y,r in zip(years,rows):r['year']=y
    return rows

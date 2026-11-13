"""Lossless sampled-M1 sufficient statistics, causal episode selection and prop replay.

No broker or fresh holdout. Integer price units=.001, money=cents; floating
rounding matches the frozen native decimal cost model. Missing ticks stay unknown.
"""
from array import array
from bisect import bisect_left, bisect_right
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal as D
import json
from pathlib import Path
import time
from zoneinfo import ZoneInfo

from gold_continuous_b1 import (
    START, END, SEED, RAW_SHA, UTC, utc, digest, write_json, GoldPrefix, Minute,
    Candle, H4Builder, ResearchH4Candidate, METAL_SMA, size_for_market_stop,
    _stop_at_fill, native_context, lifecycle_probe, calendar_oracle,
    MoneyOracleInput, money_oracle,
    QualityPath,
)

CUTOFF = int(datetime(2025, 1, 1, tzinfo=UTC).timestamp())
PRAGUE = ZoneInfo('Europe/Prague')


def rounded10(value):
    return (1 if value >= 0 else -1) * ((abs(value) + 5) // 10)


def money(cents):
    return str((D(cents)/100).quantize(D('.01')))


def price_units(value):
    whole, dot, fraction = value.partition('.')
    if not whole.isdigit() or dot and not fraction.isdigit():
        raise ValueError('invalid price grammar')
    if len(fraction) > 3 and any(c != '0' for c in fraction[3:]):
        raise ValueError('price off .001 grid')
    result = int(whole)*1000 + int((fraction+'000')[:3])
    if not 0 < result < 2147483648:
        raise ValueError('invalid price range')
    return result


def floating(side, q, entry, bid):
    delta = bid-entry if side == 'BUY' else entry-bid-1000
    return rounded10((delta-450)*q)


@dataclass
class StreamSummary:
    minimum: int | None = None
    maximum: int | None = None
    peak_dd: int = 0
    first: int | None = None
    last: int | None = None
    count: int = 0
    last_at: int | None = None
    # Each new prefix minimum stores enough prefix state to stop at its first
    # threshold crossing without including later price extrema in failed DD.
    lows: list = field(default_factory=list)

    def add(self, value, at):
        self.count += 1
        self.first = value if self.first is None else self.first
        self.last = value
        self.last_at = at
        self.maximum = value if self.maximum is None else max(self.maximum, value)
        self.peak_dd = max(self.peak_dd, self.maximum-value)
        if self.minimum is None or value < self.minimum:
            self.minimum = value
            self.lows.append([value, at, self.maximum, self.peak_dd])

    def dump(self):
        return dict(min=self.minimum, max=self.maximum, dd=self.peak_dd, first=self.first,
            last=self.last, count=self.count, last_at=self.last_at, lows=self.lows)


class Source:
    def __init__(self):
        self.times = array('q')
        self.o, self.h, self.l, self.c = (array('i') for _ in range(4))
        self.hours = []

    def add(self, at, values):
        self.times.append(at)
        for target, value in zip((self.o,self.h,self.l,self.c),values):
            target.append(value)
        bucket = at//3600*3600
        o,h,l,c = values
        if not self.hours or bucket != self.hours[-1][0]:
            self.hours.append([bucket,o,h,l,c])
        else:
            row = self.hours[-1]
            row[2],row[3],row[4] = max(row[2],h),min(row[3],l),c

    def minute(self, i):
        return Minute(self.times[i], *(D(v)/1000 for v in (self.o[i],self.h[i],self.l[i],self.c[i])))


def read_source(path, *, progress=None):
    import csv
    if digest(path) != RAW_SHA:
        raise ValueError('unadmitted source hash')
    data, previous, day_text, day_base = Source(), None, None, None
    with Path(path).open(encoding='utf-8-sig',newline='') as stream:
        reader=csv.reader(stream)
        if next(reader) != ['Date','Time','Open','High','Low','Close','Volume']:
            raise ValueError('source schema')
        for n,row in enumerate(reader,1):
            if len(row) != 7 or not '2009.11.01' <= row[0] <= '2024.12.31':
                raise ValueError('source scope/columns')
            if row[0] != day_text:
                day_text=row[0]
                day_base=int(datetime.strptime(day_text,'%Y.%m.%d').replace(tzinfo=UTC).timestamp())
            clock=row[1]
            if (len(clock)!=8 or clock[2]!=':' or clock[5:]!=':00'
                    or not clock[:2].isdigit() or not clock[3:5].isdigit()
                    or int(clock[:2])>=24 or int(clock[3:5])>=60):
                raise ValueError('invalid minute clock')
            at=day_base+int(clock[:2])*3600+int(clock[3:5])*60
            o,h,l,c=(price_units(v) for v in row[2:6])
            volume=D(row[6])
            if (previous is not None and at<=previous or not SEED<=at<CUTOFF
                    or not l<=min(o,c)<=max(o,c)<=h or not volume.is_finite() or volume<0):
                raise ValueError('source order/OHLC/volume')
            data.add(at,(o,h,l,c));previous=at
            if progress and n%200000==0:progress('parse',n)
    if len(data.times)!=5399878:
        raise ValueError('frozen source row count changed')
    return data


def canonical_frames(data):
    builder,strategy=H4Builder(),ResearchH4Candidate(METAL_SMA)
    frames=[]
    for row in data.hours:
        bar=builder.add(Candle(row[0],*(D(v)/1000+D('.5') for v in row[1:])))
        if bar is None:continue
        signal,distance=strategy.observe(bar)
        if strategy.previous_difference is not None:
            frames.append(dict(at=bar.timestamp+14400,bar_start=bar.timestamp,
                difference=str(strategy.previous_difference),distance=str(distance),signal=signal))
    return frames


def boundaries(start=START,end=CUTOFF):
    result=[]
    day=utc(start).astimezone(PRAGUE).date()
    while True:
        local=datetime(day.year,day.month,day.day,tzinfo=PRAGUE)
        at=int(local.timestamp())
        if at>=end:break
        if at>start:result.append((at*1000,'reset',1))
        day+=timedelta(days=1)
    day=utc(start).replace(hour=22,minute=0,second=0)
    if day.timestamp()<start:day+=timedelta(days=1)
    while day.timestamp()<end:
        if day.weekday()<5:result.append((int(day.timestamp())*1000,'funding',3 if day.weekday()==2 else 1))
        day+=timedelta(days=1)
    for year in range(2010,2025):
        for month in (1,4,7,10):
            at=int(datetime(year,month,1,tzinfo=UTC).timestamp())
            if start<at<end:result.append((at*1000,'cut',1))
    return sorted(result,key=lambda x:(x[0],x[1]!='reset'))


def advance_cash_reset(session,attempt,phase,at,balance,*,positions,pending=0,resume=None,fresh_quote=False):
    """Adapter bridge: cash clock advances; stale floating never becomes a quote.

    Native approximate snapshot behavior is intentionally unchanged. This scoped
    balance-anchor adapter first validates the event using the native reducer.
    """
    spec=session.profile.phases[phase.phase_index-1]
    if spec.daily_anchor_basis!='balance' or spec.reset_order!='reset_then_fees' or spec.overall_drawdown.kind!='static':
        raise ValueError('cash reset bridge requires declared static balance-anchor profile')
    cal=calendar_oracle(spec,virtual_start_utc=attempt.virtual_start_utc,
        previous_virtual_utc=phase.virtual_time_utc,current_virtual_utc=utc(at/1000))
    if len(cal['reset_boundaries'])!=1 or cal['reset_boundaries'][0]['boundary_utc']!=utc(at/1000):
        raise ValueError('must advance each exact reset boundary')
    r=lifecycle_probe(session,attempt,phase,at/1000,balance=balance,positions=positions,pending=pending,
        quality='approximate',resume=resume,kind='calendar_boundary')
    stale=phase.floating_pl
    r['phase']=r['phase'].model_copy(update=dict(balance=D(balance),daily_anchor=D(balance),
        equity=D(balance)+stale,high_water_mark=max(phase.high_water_mark,D(balance)+stale),
        virtual_time_utc=utc(at/1000),last_event_sequence=phase.last_event_sequence+1,
        open_positions=positions,pending_orders=pending,evaluation_quality='approximate'))
    life=r['resume_state'].setdefault('prop_lifecycle',{})
    life['reset_quote_state']='M1_OPEN_AT_RESET' if fresh_quote else 'NO_FRESH_QUOTE_AT_RESET'
    life['price_coverage_uncertain']=life.get('price_coverage_uncertain',False) or positions>0 and not fresh_quote
    life['last_cash_reset_utc']=utc(at/1000).isoformat()
    r['objectives'].update(calendar=json.loads(json.dumps(cal,default=str)),cash_anchor_updated=True)
    return r


def build_episode(data,frames,index,risk,bounds):
    frame=frames[index];side=frame['signal'];entry_i=bisect_left(data.times,frame['at'])
    if entry_i==len(data.times):return None
    engine=GoldPrefix(str(risk))
    qty=size_for_market_stop(D(frame['distance']),instrument=engine.instrument,model=engine.model,budget=D(risk))
    q=int(qty*100) if qty else 0
    entry=data.o[entry_i]+(1000 if side=='BUY' else 0)
    if not q or D(entry)/1000*qty*100/10>50000:
        return dict(decision=frame['at']*1000,status='rejected',side=side,risk=risk)
    stop=int(_stop_at_fill(side,D(entry)/1000,D(frame['distance']),D('.001'))*1000)
    exit_at=None
    for nxt in frames[index+1:]:
        diff=D(nxt['difference'])
        if side=='BUY' and diff<=0 or side=='SELL' and diff>=0:
            exit_at=nxt['at'];break
    planned_exit=bisect_left(data.times,exit_at) if exit_at is not None else len(data.times)
    events=[];points,envelope=StreamSummary(),StreamSummary()
    segment_start=data.times[entry_i]*1000
    bound_index=bisect_right([v[0] for v in bounds],segment_start)
    gap_count=stop_unknown=0
    last=data.times[entry_i]
    def flush(end):
        nonlocal points,envelope,segment_start
        if points.count:
            events.append(dict(kind='segment',start=segment_start,end=end,p=points.dump(),e=envelope.dump()))
        points,envelope=StreamSummary(),StreamSummary();segment_start=end
    def scheduled(through):
        nonlocal bound_index
        while bound_index<len(bounds) and bounds[bound_index][0]<=through:
            at,kind,mult=bounds[bound_index];flush(at)
            raw_i=bisect_left(data.times,at//1000)
            fresh=raw_i<len(data.times) and data.times[raw_i]*1000==at
            events.append(dict(kind=kind,at=at,multiplier=mult,q=q,side=side,
                missing_reset_quote=not fresh,
                floating_at_reset=floating(side,q,entry,data.o[raw_i]) if fresh else None))
            bound_index+=1
    def point(v,at):
        points.add(v,at);envelope.add(v,at)
    entry_at=data.times[entry_i]*1000
    events.append(dict(kind='entry',at=entry_at,net=floating(side,q,entry,data.o[entry_i])))
    closed=False;close_at=None;reason=None
    for i in range(entry_i,len(data.times)):
        at=data.times[i]*1000
        scheduled(at)
        if i>entry_i and data.times[i]>last+60:
            gap_count+=1
            flush(at)
            events.append(dict(kind='gap',at=at,start=(last+60)*1000))
        bid=data.o[i];opening=bid+(1000 if side=='SELL' else 0)
        point(floating(side,q,entry,bid),at)
        gap=opening<=stop if side=='BUY' else opening>=stop
        if gap or i==planned_exit:
            close_bid=bid;close_at=at;reason='stop_loss_gap' if gap else 'strategy_exit';closed=True
        else:
            touched=data.l[i]<=stop if side=='BUY' else data.h[i]+1000>=stop
            if touched:
                close_bid=stop-(1000 if side=='SELL' else 0);close_at=at+59999
                reason='stop_loss';closed=True;stop_unknown+=1
            else:
                favorable,adverse=(data.h[i],data.l[i]) if side=='BUY' else (data.l[i],data.h[i])
                envelope.add(floating(side,q,entry,favorable),at)
                envelope.add(floating(side,q,entry,adverse),at)
                point(floating(side,q,entry,data.c[i]),at+59999)
        if closed:
            net=floating(side,q,entry,close_bid)
            point(net,close_at);flush(close_at)
            events.append(dict(kind='close',at=close_at,net=net,reason=reason))
            break
        last=data.times[i]
    if not closed:
        flush((data.times[-1]+60)*1000-1)
        scheduled(CUTOFF*1000-1)
    return dict(decision=frame['at']*1000,entry=entry_at,exit=close_at,side=side,q=q,risk=risk,
        distance=frame['distance'],entry_fill_units=entry,stop_units=stop,events=events,
        status='closed' if closed else 'open',gap_count=gap_count,unordered_stop_minutes=stop_unknown,
        last_mark=(data.times[i]+60)*1000-1 if not closed else close_at,
        last_floating=floating(side,q,entry,data.c[i]) if not closed else 0)


def phase_a(data,*,progress=None):
    frames=canonical_frames(data);bounds=boundaries();result={125:[],200:[]}
    for index,frame in enumerate(frames):
        if frame['signal'] not in ('BUY','SELL') or frame['at']<START:continue
        for risk in result:
            episode=build_episode(data,frames,index,risk,bounds)
            if episode is not None:result[risk].append(episode)
        if progress:progress('episodes',sum(len(v) for v in result.values()))
    return dict(frames=frames,episodes=result,boundaries=bounds)


class Metrics:
    def __init__(self):
        self.peak=5000000;self.dd=self.daily=self.static=0
    def apply(self,s,cash,anchor):
        if s['count']==0:return
        self.dd=max(self.dd,self.peak-cash-s['min'],s['dd'])
        self.daily=max(self.daily,anchor-cash-s['min'])
        self.static=max(self.static,5000000-cash-s['min'])
        self.peak=max(self.peak,cash+s['max'])
    def point(self,value,cash,anchor,at):
        s=StreamSummary();s.add(value,at);self.apply(s.dump(),cash,anchor)
    def dump(self):
        return dict(peak=money(self.peak),peak_dd=money(self.dd),daily_loss=money(self.daily),static_loss=money(self.static))


class LedgerAccount:
    def __init__(self,start,end,*,challenge=True,on_reset=None):
        self.start,self.end=start*1000,end*1000
        self.cash=self.anchor=5000000;self.p=Metrics();self.e=Metrics()
        self.s,self.a,self.phase=native_context(start,end);self.resume={}
        oracle=money_oracle(self.s.profile.phases[0],MoneyOracleInput(initial_capital=50000,
            daily_anchor=50000,balance_before_separate_costs=50000,high_water_mark=50000))
        self.daily_allowance=int((oracle['daily_loss']['reference']-oracle['daily_loss']['floor'])*100)
        self.overall_floor=int(oracle['overall_drawdown']['floor']*100)
        self.resets=[at for at,kind,_ in boundaries(start,end) if kind=='reset'];self.reset_cursor=0
        self.entries=self.closed=self.funding=0;self.last_float=0
        self.challenge=challenge;self.phase_passes=[];self.breach=None;self.unknown_counts=dict(gaps=0,missing_resets=0,stop_minutes=0)
        self.trades=[];self.decisions=[];self.days=set();self.exposure=[];self.phases_metrics=[]
        self.on_reset=on_reset

    def reset(self,at,held,*,fresh=False):
        r=advance_cash_reset(self.s,self.a,self.phase,at,D(self.cash)/100,
            positions=int(held),resume=self.resume,fresh_quote=fresh)
        self.a,self.phase,self.resume=r['attempt'],r['phase'],r['resume_state']
        self.anchor=self.cash
        if self.on_reset:
            self.on_reset(dict(at=at,phase=self.phase.phase_index,held=held,
                daily_reference_balance=money(self.anchor),current_cash_balance=money(self.cash),
                reset_quote_state=self.resume['prop_lifecycle']['reset_quote_state'],
                clock_utc=self.phase.virtual_time_utc.isoformat(),sequence=self.phase.last_event_sequence))
        if held and not fresh:self.unknown_counts['missing_resets']+=1
        self.reset_cursor+=1

    def roll(self,through,held=False,exact_reset=None):
        while self.reset_cursor<len(self.resets) and self.resets[self.reset_cursor]<=through:
            at=self.resets[self.reset_cursor]
            self.reset(at,held,fresh=exact_reset==at)

    def mark(self,at,value,*,positions,qualifying=False,pending=0):
        r=lifecycle_probe(self.s,self.a,self.phase,at/1000,balance=D(self.cash)/100,floating=D(value)/100,
            quality='full_for_declared_model',qualifying=qualifying,positions=positions,pending=pending,resume=self.resume)
        self.a,self.phase,self.resume=r['attempt'],r['phase'],r['resume_state']
        return r['objectives'].get('terminal_action')

    def consume(self,episode,costs):
        if episode['status']=='rejected':return None
        self.roll(episode['entry'])
        self.entries+=1;self.days.add(utc(episode['entry']/1000).astimezone(PRAGUE).date().isoformat())
        self.decisions.append(dict(at=episode['decision'],side=episode['side'],q=episode['q']))
        self.exposure.append([episode['entry'],episode['exit'] or self.end])
        for event in episode['events']:
            kind=event['kind']
            at=event.get('at',event.get('end'))
            if kind=='segment':
                if event['start']>=self.end:break
                if event['end']>self.end:raise ValueError('ledger requires exact cutoff segment')
                at=event['p']['last_at']
            elif at>=self.end:break
            if kind=='reset':
                self.roll(at,held=True,exact_reset=at if not event['missing_reset_quote'] else None)
            elif kind=='funding':
                self.roll(at,held=True)
                rate=costs[0] if event['side']=='BUY' else costs[1]
                fee=rate*event['q']*event['multiplier'];self.cash-=fee;self.funding+=fee
            elif kind=='entry':
                self.p.point(event['net'],self.cash,self.anchor,at);self.e.point(event['net'],self.cash,self.anchor,at)
                self.last_float=event['net']
                if self.challenge and self.mark(at,event['net'],positions=1,qualifying=True)=='breach':
                    self.breach=dict(at=at,phase=self.phase.phase_index,label='M1_entry_point',
                        equity=money(self.cash+event['net']),daily_anchor=money(self.anchor))
                    return 'breach'
            elif kind=='segment':
                # Every segment lies between cash/reset changes. Its prefix
                # minima retain first-crossing order at arbitrary cash floors.
                self.roll(event['start'],held=True)
                floor=max(self.anchor-self.daily_allowance,self.overall_floor)-self.cash
                hit=next((low for low in event['e']['lows'] if low[0]<floor),None)
                if hit and self.challenge:
                    value,when,peak,dd=hit
                    truncated=dict(count=1,min=value,max=peak,dd=dd)
                    self.e.apply(truncated,self.cash,self.anchor)
                    self.breach=dict(at=when,phase=self.phase.phase_index,label='conditional_M1_extrema_or_point',
                        equity=money(self.cash+value),daily_anchor=money(self.anchor))
                    # This is a declared sampled-M1 model breach, not a quote
                    # proving the exact tick-time or a broker submission.
                    self.mark(when,value,positions=1)
                    return 'breach'
                self.p.apply(event['p'],self.cash,self.anchor);self.e.apply(event['e'],self.cash,self.anchor)
                self.last_float=event['p']['last']
                # All intermediate floors were checked against the ordered
                # segment minima above. Native lifecycle is needed at entries,
                # exits, cash resets and a witnessed breach, not every mark.
            elif kind=='close':
                if event['reason']=='stop_loss':self.unknown_counts['stop_minutes']+=1
                self.cash+=event['net'];self.closed+=1;self.last_float=0
                self.trades.append(dict(side=episode['side'],q=episode['q'],entry=episode['entry'],exit=at,price_net=event['net']))
                self.p.point(0,self.cash,self.anchor,at);self.e.point(0,self.cash,self.anchor,at)
                if self.challenge:
                    action=self.mark(at,0,positions=0)
                    if action in ('phase_pass','complete_pass'):
                        self.phase_passes.append(dict(phase=self.phase.phase_index,at=at,net_cash=money(self.cash-5000000),entry_days=len(self.days)))
                        self.phases_metrics.append(dict(phase=self.phase.phase_index,p=self.p.dump(),e=self.e.dump()))
                        return action
            elif kind=='gap':self.unknown_counts['gaps']+=1
        self.roll(min(self.end-1,episode['exit'] or self.end-1),held=episode['exit'] is None or episode['exit']>=self.end)
        return None

    def next_phase(self):
        from trading_workspace_v2.prop_session import TransitionIntent,apply_prop_lifecycle_command
        r=apply_prop_lifecycle_command(self.s,self.a,self.phase,TransitionIntent(workspace_id=self.a.workspace_id,
            session_id=self.a.session_id,attempt_id=self.a.attempt_id,profile_hash=self.a.profile_hash,
            intent_id='phase2',expected_revision=self.a.revision,event_sequence=self.phase.last_event_sequence,
            action='next_phase'),resume_state=self.resume)
        self.a,self.phase,self.resume=r['attempt'],r['phase'],r['resume_state']
        r=apply_prop_lifecycle_command(self.s,self.a,self.phase,TransitionIntent(workspace_id=self.a.workspace_id,
            session_id=self.a.session_id,attempt_id=self.a.attempt_id,profile_hash=self.a.profile_hash,
            intent_id='start-phase2',expected_revision=self.a.revision,event_sequence=self.phase.last_event_sequence,
            action='start'),resume_state=self.resume)
        self.a,self.phase,self.resume=r['attempt'],r['phase'],r['resume_state']
        self.cash=self.anchor=5000000;self.p,self.e=Metrics(),Metrics();self.days=set()
        self.last_float=0

    def result(self):
        status='failed_model_breach' if self.breach else 'completed_model_two_step' if len(self.phase_passes)==2 else 'right_censored'
        terminal_float=int(self.phase.floating_pl*100) if self.breach else self.last_float
        return dict(status=status,initial_balance_usd='50000',cash_net_usd=money(self.cash-5000000),
            floating_usd=money(terminal_float),marked_net_usd=money(self.cash-5000000+terminal_float),
            entries=self.entries,closed=self.closed,financing_debit_usd=money(self.funding),
            point_metrics=self.p.dump(),conditional_envelope=self.e.dump(),phase_passes=self.phase_passes,
            completed_phase_metrics=self.phases_metrics,first_model_breach=self.breach,unknown_counts=self.unknown_counts,
            full_path_prop_qualified=False,full_path_survival='unknown_M1_and_missing_prices',
            trades=self.trades,decisions=self.decisions)


def evaluate(ledger,start,end,risk,*,variant='Original',costs=(40,40),challenge=True,on_reset=None):
    account=LedgerAccount(start,end,challenge=challenge,on_reset=on_reset)
    consumed=start*1000
    for episode in ledger['episodes'][risk]:
        # Start flat/no inherited pending. A cross already consumed as an EXIT
        # cannot be re-used to enter the opposite side in a reset account.
        if episode['decision']<=consumed or episode['decision']>=end*1000:continue
        if variant!='Original' and episode['side']=='SELL':continue
        if episode['status']=='rejected':continue
        if episode['entry']>=end*1000:continue
        action=account.consume(episode,costs)
        consumed=episode['exit'] or end*1000
        if action=='phase_pass':account.next_phase()
        elif action in ('breach','complete_pass'):break
        if episode['status']=='open' or consumed>=end*1000:break
    if account.breach is None and len(account.phase_passes)<2:account.roll(end*1000-1,held=False)
    return account.result()


class PointAwareQualityPath(QualityPath):
    def mark(self,at,balance,floating,*,conditional=False,label='M1_point'):
        super().mark(at,balance,floating,conditional=conditional,label=label)
        if not conditional:
            # A prior within-minute peak can exceed every open/close peak.
            # Later point losses must still be measured against that peak.
            self.envelope['peak_dd']=max(self.envelope['peak_dd'],self.envelope['peak']-balance-floating)


class DirectGold(GoldPrefix):
    def __init__(self,risk,*,start,end,variant='Original'):
        super().__init__(str(risk),start=start,end=end);self.variant=variant
        self.path=PointAwareQualityPath(start,end)
    def finalize_hour(self):
        super().finalize_hour()
        if self.variant!='Original' and self.pending and self.pending['signal']=='SELL':
            self.pending['status']='blocked_short';self.pending=None


def direct(data,start,end,risk,variant='Original',progress=None):
    engine=DirectGold(risk,start=start,end=end,variant=variant);began=time.perf_counter()
    upper=bisect_left(data.times,end)
    for i in range(upper):
        if i%200000==0:
            if progress:progress('direct',i)
            if time.perf_counter()-began>900:raise TimeoutError('direct900s')
        engine.step(data.minute(i))
    engine.finish();r=engine.result();r['wall_seconds']=time.perf_counter()-began
    return r

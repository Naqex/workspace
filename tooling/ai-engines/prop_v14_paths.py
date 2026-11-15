"""Explicit M1 ordering paths and causal, source-bound stop crossings for V14."""
from functools import lru_cache
from math import ceil
import numpy as np
from prop_v14_source import JOB,FIRST,END,SEED,read,sha,save
from quant_core.market_data_store import BAR,QUOTE
from quant_core.gap_aware_execution import GapAwarePathIndex,replay_gap_aware
from quant_core.ftmo_execution_and_calendar import execution_schedule
from quant_core.vectorized_stage0_scanner import HOUR,DAY
from quant_core.vectorized_sl_active_kernel import money


class M1ScenarioQuotes:
    """Four registered OHLC observations plus interpolated stop/TP crossings."""
    def __init__(self,bars,order,first,end):
        if order not in ("OPEN_LOW_HIGH_CLOSE","OPEN_HIGH_LOW_CLOSE"):
            raise ValueError("M1_order")
        self.bars=bars;self.order=order;self.first=first;self.cutoff=end
        codes=bars["t"]//HOUR*HOUR
        starts=np.r_[0,np.flatnonzero(np.diff(codes))+1];ends=np.r_[starts[1:],len(bars)]
        self.files={int(codes[i]):(int(i),int(j)) for i,j in zip(starts,ends)}
        self.injected={}

    def points(self,first,end):
        bars=self.bars
        lo,hi=bars["t"].searchsorted([first,end],side="left")
        # End is inclusive for an endpoint open, not for its later extrema.
        if hi<len(bars) and bars["t"][hi]==end:hi+=1
        a=bars[lo:hi]
        names="olhc" if self.order=="OPEN_LOW_HIGH_CLOSE" else "ohlc"
        q=np.empty(len(a)*4,dtype=QUOTE)
        q["t"]=(a["t"][:,None]+np.array([0,20000,40000,59999])).ravel()
        for side in ("b","a"):q[side]=np.column_stack([a[side+n] for n in names]).ravel()
        return q[q["t"]<=end]

    @lru_cache(maxsize=96)
    def hour(self,at):
        if not self.first//HOUR*HOUR<=at<self.cutoff:raise ValueError("scenario_price_fence")
        q=self.points(at,min(at+HOUR-1,self.cutoff-1)) if at in self.files else np.empty(0,dtype=QUOTE)
        extra=self.injected.get(at,[])
        if extra:
            q=np.concatenate([q,np.array(extra,dtype=QUOTE)])
            q=q[np.argsort(q["t"],kind="stable")]
        return q

    def add(self,at,bid,ask):
        if not self.first<=at<self.cutoff:raise ValueError("injected_quote_outside_sample")
        self.injected.setdefault(at//HOUR*HOUR,[]).append((int(at),int(bid),int(ask)))
        self.files.setdefault(at//HOUR*HOUR,(0,0))
        self.hour.cache_clear()


def crossing(q,index,level,side,*,limit=False):
    """Continuous within a declared bar; a new minute open can jump the stop."""
    point=q[index];at=int(point["t"]);field="b" if side==1 else "a"
    opening=at%60000==0
    if index==0 or opening:
        px=int(point[field])
        fill=level if limit else (min(px,level) if side==1 else max(px,level))
        return at,fill
    before=q[index-1];old=int(before[field]);current=int(point[field])
    if old==current:return at,int(level)
    if not min(old,current)<=level<=max(old,current):
        raise ValueError("crossing_not_bracketed")
    dt=int(point["t"])-int(before["t"])
    when=int(before["t"])+max(1,ceil(abs(level-old)*dt/abs(current-old)))
    return min(when,at),int(level)


def realize(m,result,i,reader,index,identity,mode):
    entry=int(m["entry_at"][i]);end=int(result["effective_deadline"][i])
    if entry>=reader.cutoff:return None
    # Preserve exposure at a true sample end rather than fill a nonexistent endpoint.
    scheduled=int(result["scheduled_deadline"][i])
    censored=scheduled>=reader.cutoff
    endpoint=min(end,reader.cutoff-1)
    q=reader.points(entry,endpoint)
    if not len(q) or int(q["t"][0])!=entry:return None
    side=int(m["side"][i]);field="b" if side==1 else "a"
    p0=int(m["entry_price"][i]);stop=int(m["stop"][i])
    activation=int(result["activation_index"][i])
    activate=int(index.bars["t"][activation])+60000 if activation>=0 else reader.cutoff
    protect=int(result["protection_price"][i])
    levels=np.where((q["t"]>=activate)&(mode=="P1"),protect,stop)
    px=q[field].astype("int64")
    adverse=np.flatnonzero(px<=levels if side==1 else px>=levels)
    target=p0+side*3*abs(p0-stop)
    favorable=np.flatnonzero(side*(px-target)>=0) if mode=="P2" else []
    a=int(adverse[0]) if len(adverse) else len(q)
    b=int(favorable[0]) if len(favorable) else len(q)
    reason="HORIZON";exit_at=end;fill=int(q[field][-1])
    if a<len(q) and a<=b:
        exit_at,fill=crossing(q,a,int(levels[a]),side)
        reason="PROTECT" if mode=="P1" and int(q["t"][a])>=activate else "SL"
    elif b<len(q):
        exit_at,fill=crossing(q,b,target,side,limit=True);reason="TP"
    elif censored:
        exit_at=reader.cutoff;reason="RIGHT_CENSORED"
    else:
        at=int(q["t"].searchsorted(end))
        if at>=len(q) or int(q["t"][at])!=end:return None
        fill=int(q[field][at])
    last=min(int(index.bars["t"].searchsorted(min(exit_at,reader.cutoff-1),side="right"))-1,len(index.bars)-1)
    start=int(index.bars["t"].searchsorted(entry))
    uncertain=not bool(index.source_complete(np.array([start]),np.array([last]))[0])
    spread=int(q["a"][0])-int(q["b"][0])
    if reason!="RIGHT_CENSORED":
        bid=fill if side==1 else fill-spread
        reader.add(exit_at,bid,bid+spread)
    asset=m["asset"];scale=1000 if asset=="XAUUSD" else 100000
    t=dict(id=identity,asset=asset,role="CORE",side="BUY" if side==1 else "SELL",
        decision_msc=int(m["at"][i]),entry_msc=entry,entry_price_units=p0,stop_units=stop,
        deadline_msc=scheduled,exit_msc=exit_at,exit_price_units=fill,reason=reason,
        mode=mode,regime_weight=1,d1_gate=True,natural=float(m["natural"][i]),
        source_uncertain=uncertain,order=reader.order,scale=scale,censored=reason=="RIGHT_CENSORED",
        activation_time=activate if activation>=0 else None,protection_price=protect,
        source_event=i,source_model="CONDITIONAL_M1_OHLC_ORDER_AND_ASK_PROXY")
    t["reference"]={}
    if not t["censored"]:
        for model in ("SYM","ASYM"):
            values=money(asset,model,np.array([side]),np.array([p0]),np.array([fill]),
                np.array([entry]),np.array([exit_at]),np.array([reason]))
            t["reference"][model]=dict(net_R=float(values["net"][0]/t["natural"]),
                **{k:float(v[0]) for k,v in values.items()})
    return t


def build(measurements,order,bars_by_asset):
    readers={a:M1ScenarioQuotes(b,order,FIRST,END) for a,b in bars_by_asset.items()}
    out=[];missing=[]
    for identity,m in measurements.items():
        asset=m["asset"];index=m["_index"];mode=identity.rsplit("|",1)[-1]
        result=replay_gap_aware(index,m,mode)
        for i in np.flatnonzero(m["admitted"]):
            decision,entry=int(m["at"][i]),int(m["entry_at"][i])
            from datetime import datetime,timezone
            day=datetime.fromtimestamp(entry/1000,timezone.utc)
            flat=index.schedule.events.get(day.date().isoformat(),{})
            clock=flat.get("flat_utc")
            if (not FIRST<=decision<END or not 0<=entry-decision<=60000
                    or m["deadline"][i]<entry or day.weekday()>=5
                    or day.weekday()==4 and entry%DAY>=int(20.5*HOUR)
                    or flat.get("kind")=="CLOSED"
                    or clock and day.strftime("%H:%M")>=clock):
                missing.append(dict(id=identity,event=int(i),reason="CAUSAL_ENTRY_GUARD"))
                continue
            t=realize(m,result,int(i),readers[asset],index,identity,mode)
            if t is None:missing.append(dict(id=identity,event=int(i)))
            else:out.append(t)
    out.sort(key=lambda t:(t["entry_msc"],t["asset"],t["id"]))
    # Ordinals are bound after all interpolated crossings are inserted.
    for t in out:
        reader=readers[t["asset"]]
        for which in ("entry","exit"):
            at=t[which+"_msc"]
            if which=="exit" and t["censored"]:t["exit_quote_index"]=-1;continue
            q=reader.hour(at//HOUR*HOUR)
            side="a" if which=="entry" and t["side"]=="BUY" or which=="exit" and t["side"]=="SELL" else "b"
            matches=np.flatnonzero((q["t"]==at)&(q[side]==t[which+"_price_units"]))
            if not len(matches):raise ValueError("V14_event_quote_binding")
            t[which+"_quote_index"]=int(matches[0])
    return out,readers,missing

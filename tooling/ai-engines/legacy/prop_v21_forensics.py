"""Dev-first attribution over frozen V19 trades and admitted M1 scenarios."""
from collections import defaultdict
from copy import deepcopy
import subprocess
import numpy as np
from prop_v21_common import *
from prop_v15_evidence import bars_for
from prop_v14_paths import M1ScenarioQuotes,crossing
from prop_v16_paths import CausalFlatSchedule
from quant_core.ftmo_execution_and_calendar import gold_calendar
from quant_core.gap_aware_execution import GapAwarePathIndex
from quant_core.behavioral_signals import closed_atr
from quant_core.trade_forensics_classifier import classify,excursions,summarize,concentration
from prop_v10_signals import frames,align
from prop_v15_accounts import exact_quantity
from prop_v14_accounts import trade_money,VALUE

DAY,HOUR=86400000,3600000


class Context:
    def __init__(self,dev):
        self.end=DEV_END if dev else END
        self.schedule=CausalFlatSchedule(gold_calendar(FIRST,self.end).events.values())
        self.bars={a:bars_for(a,dev) for a in ("XAUUSD","EURUSD")}
        self.indices={a:GapAwarePathIndex(b,asset=a,schedule=self.schedule) for a,b in self.bars.items()}
        self.daily={}
        self._readers={}
        for a,b in self.bars.items():
            _,_,d=frames(b);d["atr"]=closed_atr(d);self.daily[a]=d

    def day_ratio(self,t):
        b=self.bars[t["asset"]];at=t["decision_msc"];lo,hi=b["t"].searchsorted([at//DAY*DAY,at])
        d=self.daily[t["asset"]];j=d["t"].searchsorted(at,side="right")-1
        if j<0 or hi<=lo or not np.isfinite(d["atr"][j]) or d["atr"][j]<=0:return None
        return float((b["bh"][lo:hi].max()-b["bl"][lo:hi].min())/d["atr"][j])

    def complete(self,asset,entry,end):
        b=self.bars[asset];i,j=b["t"].searchsorted([entry,end],side="right")-1
        if i<0 or j<i or j>=len(b) or int(b["t"][j])!=end//60000*60000:return False
        return bool(self.indices[asset].source_complete(np.array([i]),np.array([j]))[0])

    def reader(self,asset,tag):
        key=asset,tag
        if key not in self._readers:
            self._readers[key]=M1ScenarioQuotes(self.bars[asset],"OPEN_LOW_HIGH_CLOSE" if tag=="OLHC" else "OPEN_HIGH_LOW_CLOSE",FIRST,self.end)
        return self._readers[key]


def features(t,context,tag):
    cutoff=min(context.schedule.cutoff(t["entry_msc"],t["asset"]),context.end-1)
    cutoff=max(cutoff,t["exit_msc"])
    q=context.reader(t["asset"],tag).points(t["entry_msc"],cutoff)
    side=1 if t["side"]=="BUY" else -1
    f=excursions(q["t"],q["b" if side==1 else "a"],entry=t["entry_msc"],exit_at=t["exit_msc"],
        entry_price=t["entry_price_units"],natural_units=abs(t["entry_price_units"]-t["stop_units"]),side=side,
        exit_price=t["exit_price_units"],cutoff=cutoff,stop_reason=t["reason"])
    qn=exact_quantity(t,150);net=trade_money(t,qn,"SYM_FLAT",150)["net_usd"]/150
    r=dict(trade_key=f"{t['id']}@{t['entry_msc']}",id=t["id"],family=t["id"].split("|")[1][:2],
        asset=t["asset"],side=t["side"],mode=t["mode"],reason=t["reason"],entry_msc=t["entry_msc"],
        exit_msc=t["exit_msc"],year=int(np.datetime64(t["entry_msc"],"ms").astype("datetime64[Y]").astype(int)+1970),
        net_R=net,unit_net_R=t["reference"]["SYM"]["net_R"],day_range_ATR=context.day_ratio(t),
        open_path_unknown=t["source_uncertain"] or not context.complete(t["asset"],t["entry_msc"],t["exit_msc"]),
        post_path_unknown=not context.complete(t["asset"],t["exit_msc"],cutoff),post_cutoff_msc=cutoff,**f)
    r["post_1R_before_original_deadline"]=r["post_1R_at"] is not None and r["post_1R_at"]<=t["deadline_msc"]
    return dict(r,**classify(r))


def taxonomy(trades,context,tag):
    rows=[features(t,context,tag) for t in trades]
    for i in range(100,len(rows)+100,100):event("forensics_rows",order=tag,done=min(i,len(rows)))
    result=dict(total=summarize(rows),concentration=concentration(rows),
        sleeves={identity:summarize([r for r in rows if r["id"]==identity]) for identity in sorted({r["id"] for r in rows})},
        periods={label:summarize([r for r in rows if (r["year"]<=2023)==dev]) for label,dev in (("2018-2023",True),("2024-2026YTD",False))})
    return rows,result


def marked_metrics(trades,context,tag):
    changes=[]
    for t in trades:
        q=context.reader(t["asset"],tag).points(t["entry_msc"],t["exit_msc"])
        times=np.r_[q["t"],t["exit_msc"]];prices=np.r_[q["b" if t["side"]=="BUY" else "a"],t["exit_price_units"]]
        quantity=exact_quantity(t,150)
        # Scalar accounting is reused for final cents; floating marks need only
        # two endpoint cost evaluations because these books are intraday.
        final=trade_money(t,quantity,"SYM_FLAT",150)["net_usd"]/150
        sign=1 if t["side"]=="BUY" else -1
        raw=sign*(prices-t["entry_price_units"])*quantity*VALUE[t["asset"]]
        gross=np.sign(raw)*((abs(raw)+5)//10*10)/1000
        if t["asset"]=="XAUUSD":
            entry_fee=np.floor(t["entry_price_units"]*quantity*.0000007+.5+1e-9)/100
            exit_fee=np.floor(prices*quantity*.0000007+.5+1e-9)/100
            slips=quantity*.4
        else:
            entry_fee=exit_fee=np.floor(quantity*.035*100+.5+1e-9)/100
            slips=quantity*.02
        values=(gross-entry_fee-exit_fee-slips)/150;values[-1]=final
        deltas=np.diff(np.r_[0.,values]);changes.extend(zip(times.tolist(),deltas.tolist()))
    changes.sort(key=lambda p:p[0])
    at=np.array([p[0] for p in changes]);delta=np.array([p[1] for p in changes])
    uniq,ix=np.unique(at,return_index=True);eq=np.cumsum(np.add.reduceat(delta,ix))
    peaks=np.maximum.accumulate(np.r_[0.,eq])[1:]
    dd=float(np.max(peaks-eq)) if len(eq) else 0.
    daily=0.
    for d in np.unique(uniq//DAY):
        use=np.flatnonzero(uniq//DAY==d);anchor=eq[use[0]-1] if use[0] else 0.
        daily=max(daily,float(anchor-eq[use].min()))
    net=sum(trade_money(t,exact_quantity(t,150),"SYM_FLAT",150)["net_usd"]/150 for t in trades)
    if len(eq) and abs(eq[-1]-net)>1e-7:raise ValueError("V21_marked_cash_conservation")
    years=6 if context.end==DEV_END else (context.end-FIRST)/(365.2425*DAY)
    return dict(net_R=net,equity_R_DD=dd,worst_daily_R=daily,worst_daily_pct=daily*.3,
        Calmar=(net/years/dd if dd else None),annualization_years=years,fixed150_not_account_lifecycle=True)


def refine(trades,context,tag,choice):
    from quant_core.vectorized_sl_active_kernel import net_level
    out=[]
    for old in trades:
        t=deepcopy(old)
        if choice=="B1_EXHAUSTION90":
            ratio=context.day_ratio(t)
            if t["asset"]=="XAUUSD" and ratio is not None and ratio>.9:continue
        elif t["mode"]=="P0":
            side=1 if t["side"]=="BUY" else -1;p0=t["entry_price_units"]
            threshold=int(net_level(t["asset"],np.array([side]),np.array([p0]),np.array([t["natural"]]),
                np.array([t["entry_msc"]]),np.array([t["entry_msc"]]),1.)[0])
            q=context.reader(t["asset"],tag).points(t["entry_msc"],t["exit_msc"])
            px=q["b" if side==1 else "a"]
            hits=np.flatnonzero(side*(px-threshold)>=0)
            if len(hits):
                active=int(q["t"][hits[0]])//60000*60000+60000
                level=int(net_level(t["asset"],np.array([side]),np.array([p0]),np.array([t["natural"]]),
                    np.array([t["entry_msc"]]),np.array([active]),0.)[0])
                stops=np.flatnonzero((q["t"]>=active)&(side*(px-level)<=0))
                if len(stops):
                    j=int(stops[0]);at,fill=crossing(q,j,level,side)
                    if at<t["exit_msc"]:
                        t.update(exit_msc=max(active,at),exit_price_units=fill,reason="PROTECT",activation_time=active,protection_price=level)
        if t["exit_msc"]!=old["exit_msc"]:
            from quant_core.vectorized_sl_active_kernel import money
            m=money(t["asset"],"SYM",np.array([1 if t["side"]=="BUY" else -1]),np.array([t["entry_price_units"]]),
                np.array([t["exit_price_units"]]),np.array([t["entry_msc"]]),np.array([t["exit_msc"]]),np.array([t["reason"]]))
            t["reference"]["SYM"]=dict(net_R=float(m["net"][0]/t["natural"]))
        out.append(t)
    return out


def run(dev):
    if not dev and not (JOB/"Development-decision.json").exists():raise ValueError("Dev_selection_must_be_locked_first")
    context=Context(dev);scope="Dev" if dev else "Full";summaries={}
    for tag in ("OLHC","OHLC"):
        trades=read(V19/f"{scope}-{tag}-PRIMARY-trades.json")
        rows,summary=taxonomy(trades,context,tag);summary["metrics"]=marked_metrics(trades,context,tag)
        compressed(f"{scope}-{tag}-forensics",rows);summaries[tag]=summary
    save(scope+"-forensics-summary.json",summaries)
    event("taxonomy_complete",scope=scope,trades=summaries["OLHC"]["total"]["trades"])


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("--full",action="store_true");a=p.parse_args();run(not a.full)

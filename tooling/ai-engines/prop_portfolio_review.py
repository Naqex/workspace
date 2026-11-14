"""Alternate cash-posted-funding and aggregate-exposure oracle for V3."""
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from fractions import Fraction as F
import numpy as np

from prop_campaign_source import Prices
from prop_campaign_accounts import PRAGUE
from xau_h1_execution_review import funding
from prop_portfolio_common import (
    JOB, MODELS, START, END, FINAL, HOUR, DAY, read, write_json, digest, event, ROOT,
)
from prop_portfolio_accounts import ASSETS, joint_hour

CAP = 50000000


def cent_milli(value):
    return (1 if value >= 0 else -1) * int(abs(value) * 100 + F(1, 2)) * 10


def parts(trade, quantity, model):
    gold = trade["asset"] == "XAUUSD"
    scale, units = (1000, 1) if gold else (100000, 1000)
    p0, p1 = F(trade["entry_price_units"], scale), F(trade["exit_price_units"], scale)
    side = 1 if trade["side"] == "BUY" else -1
    fee0 = cent_milli(p0 * quantity * F(7, 1000000)) if gold else cent_milli(F(quantity, 40))
    fee1 = cent_milli(p1 * quantity * F(7, 1000000)) if gold else cent_milli(F(quantity, 40))
    gross = cent_milli(side * (p1 - p0) * quantity * units)
    slip = quantity * (200 if gold else 20)
    rate = (-400 if model.startswith("SYM") else
            -450 if trade["side"] == "BUY" else -50) if gold else -400
    swaps = {at: rate * quantity * multiplier for at, multiplier
             in funding(trade["entry_msc"], trade["exit_msc"])}
    return dict(gross=gross, fee0=fee0, fee1=fee1, slip=slip,
                swaps=swaps, net=gross-fee0-fee1-2*slip+sum(swaps.values()))


def checked_joint_hour(readers, hour, previous):
    rows, maps = joint_hour(readers, hour, previous)
    if not len(rows):
        return rows, maps
    for asset, names, positions in zip(ASSETS, (("b0","a0"),("b1","a1")), maps):
        native = readers[asset].hour(hour) if hour in readers[asset].files else []
        if not len(native):
            for name in names:
                expected = previous[name] if previous is not None else 0
                if np.any(rows[name] != expected):
                    raise ValueError("joint_quote_without_prior_source")
            continue
        # Gold precedes EUR at tied milliseconds. Searchsorted reconstructs
        # the other asset's past quote independently of forward-fill indices.
        side = "right" if asset == "XAUUSD" else "left"
        indices = np.searchsorted(native["t"], rows["t"], side=side) - 1
        indices[positions] = np.arange(len(native))
        for name, field in zip(names, ("b","a")):
            expected = np.full(len(rows), previous[name] if previous is not None else 0,
                               dtype="int32")
            valid = indices >= 0
            expected[valid] = native[field][indices[valid]]
            if not np.array_equal(rows[name], expected):
                raise ValueError("joint_source_sequence_or_same_ms_order")
    return rows, maps


class CashOracle:
    def __init__(self, expected, trades, model, *, cocore=False, reward_days=30):
        self.expected = expected
        self.trades = trades
        self.model = model
        self.cocore = cocore
        self.reward_days = reward_days
        self.accepted = {a["trade"]:a for a in expected["accepted"]}
        self.closed = {a["trade"]:a for a in expected["closed"]}
        self.cash = self.anchor = self.peak = CAP
        self.dd = self.daily = self.static = 0
        self.phase = 1
        self.open = {}
        self.charges = {}
        self.components = {}
        self.coeff = [0,0,0,0]
        self.basis = 0
        self.days = set()
        self.gate = expected["start_msc"]-1
        self.halt = False
        self.breach = None
        self.first_funded = None
        self.last_reward = None
        self.entry_checks = self.rejected_checks = self.money_checks = 0
        self.phase_checks = self.reward_checks = 0
        self.max_stop = 0

    def realized_balance(self):
        return self.cash + sum(self.components[i]["slip"]-self.charges[i] for i in self.open)

    def gross_point(self, quote):
        if quote is None and self.open:
            raise ValueError("oracle_open_quote_missing")
        if not self.open:
            return 0
        return sum(c*int(quote[n]) for c,n in zip(
            self.coeff,("b0","a0","b1","a1"))) - self.basis

    def measure(self, values, times):
        if not len(values) or self.breach:
            return
        equities = values + self.cash - self.basis
        bad = np.flatnonzero(equities < max(self.anchor-2500000,45000000))
        if len(bad):
            j=int(bad[0]);equities=equities[:j+1]
            self.breach=dict(at=int(times[j]),equity=int(equities[-1]))
        running = np.maximum.accumulate(np.r_[self.peak,equities])
        self.dd=max(self.dd,int(np.max(running[1:]-equities)))
        self.daily=max(self.daily,self.anchor-int(equities.min()))
        self.static=max(self.static,CAP-int(equities.min()))
        self.peak=int(running[-1])

    def point(self, at, quote):
        if not self.open:
            value = self.basis
        else:
            value = self.gross_point(quote) + self.basis
        self.measure(np.array([value],dtype="int64"),np.array([at],dtype="int64"))

    def segment(self, rows, cache):
        if not self.open or self.breach or not len(rows):
            return
        key=tuple(self.coeff)
        if key not in cache:
            values=np.zeros(len(rows),dtype="int64")
            for coefficient,name in zip(key,("b0","a0","b1","a1")):
                if coefficient:
                    values += coefficient*rows[name].astype("int64")
            cache[key]=values
        self.measure(cache[key],rows["t"])

    def entry(self, i, at, quote):
        t=self.trades[i]
        accepted=self.accepted.get(i)
        balance=self.realized_balance()
        equity=self.cash+self.gross_point(quote)
        if balance-self.anchor<=-1000000:
            self.halt=True
        reason=None
        if t["role"]=="SATELLITE" and not self.expected["include_satellite"]:
            reason="ROLE"
        elif t["decision_msc"]<self.expected["start_msc"] or t["decision_msc"]<=self.gate:
            reason="PHASE_GATE"
        elif any(self.trades[k]["asset"]==t["asset"] and
                 self.trades[k]["decision_msc"]==t["decision_msc"] for k in self.open):
            reason="COLLISION"
        elif self.halt:
            reason="DAILY_HALT"
        base=((200,175,125) if self.cocore or t["role"]=="CORE" else (100,100,75))[self.phase-1]
        risk=min(base,90) if equity<=47000000 else min(base,150) if equity<=48000000 else base
        multiplier=1 if t["asset"]=="XAUUSD" else 10
        proposed_quantity=int(risk*1000)//(multiplier*abs(t["entry_price_units"]-t["stop_units"]))
        if not 1<=proposed_quantity<=(5000 if t["asset"]=="XAUUSD" else 100000):
            reason=reason or "LOT"
        old_risk=sum(q*(1 if self.trades[k]["asset"]=="XAUUSD" else 10)*
                     abs(self.trades[k]["entry_price_units"]-self.trades[k]["stop_units"])
                     for k,q in self.open.items())
        new_risk=proposed_quantity*multiplier*abs(t["entry_price_units"]-t["stop_units"])
        if old_risk+new_risk>(800000 if self.cocore else 500000):
            reason=reason or "OPEN_CAP"
        if proposed_quantity:
            money=parts(t,proposed_quantity,self.model)
            projected=balance-money["fee0"]
            for k,q in list(self.open.items())+[(i,proposed_quantity)]:
                old=self.trades[k];gold=old["asset"]=="XAUUSD"
                s=1 if old["side"]=="BUY" else -1
                projected += s*q*(1 if gold else 10)*(
                    old["stop_units"]-old["entry_price_units"])
                stop_fee=(cent_milli(F(old["stop_units"],1000)*q*F(7,1000000))
                          if gold else cent_milli(F(q,40)))
                projected -= stop_fee+q*(400 if gold else 40)
                rate=(-400 if self.model.startswith("SYM") else
                      -450 if old["side"]=="BUY" else -50) if gold else -400
                projected += min(0,rate)*q*sum(
                    m for _,m in funding(old["entry_msc"],old["deadline_msc"]))
            if projected<=(46000000 if self.cocore else 46500000) or projected<max(self.anchor-2500000,45000000):
                reason=reason or "RESERVE"
        if bool(accepted) != (reason is None):
            raise ValueError(f"oracle_admission_decision:{i}:{reason}:{self.expected['start_msc']}")
        if accepted is None:
            self.rejected_checks+=1
            return
        state=accepted["risk_state"]
        for name,value in (
            ("balance_milli_usd",balance),("equity_milli_usd",equity),
            ("daily_anchor_milli_usd",self.anchor),
            ("projected_stop_milli_usd",projected),
            ("prior_stop_risk_milli_usd",old_risk),("new_stop_risk_milli_usd",new_risk),
        ):
            if state[name]!=value:
                raise ValueError("oracle_pretrade_state:"+name)
        if accepted["phase"]!=self.phase or accepted["risk_usd"]!=risk or accepted["ounces"]!=proposed_quantity:
            raise ValueError("oracle_risk_or_grid")
        q=proposed_quantity
        self.components[i]=money
        self.open[i]=q;self.charges[i]=0
        a=0 if t["asset"]=="XAUUSD" else 2
        buy=t["side"]=="BUY"
        self.coeff[a if buy else a+1]+=(1 if buy else -1)*q*multiplier
        self.basis+=(1 if buy else -1)*q*multiplier*t["entry_price_units"]
        self.cash-=money["fee0"]+money["slip"]
        self.days.add(datetime.fromtimestamp(at/1000,timezone.utc).astimezone(PRAGUE).date())
        if self.phase==3 and self.first_funded is None:
            self.first_funded=at
        self.max_stop=max(self.max_stop,old_risk+new_risk)
        self.entry_checks+=1

    def action(self, kind, i, at, quote, extra=None):
        if not self.expected["start_msc"]<=at<self.expected["end_msc"] or self.breach:
            return
        if kind=="reset":
            self.anchor=self.realized_balance();self.halt=False
        elif kind=="entry":
            self.entry(i,at,quote)
        elif kind=="swap" and i in self.open:
            charge=self.components[i]["swaps"][at]
            self.cash+=charge;self.charges[i]+=charge
        elif kind=="exit" and i in self.open:
            t=self.trades[i];q=self.open.pop(i);p=self.components[i]
            self.charges.pop(i)
            multiplier=1 if t["asset"]=="XAUUSD" else 10
            a=0 if t["asset"]=="XAUUSD" else 2;buy=t["side"]=="BUY"
            self.coeff[a if buy else a+1]-=(1 if buy else -1)*q*multiplier
            self.basis-=(1 if buy else -1)*q*multiplier*t["entry_price_units"]
            self.cash+=p["gross"]-p["fee1"]-p["slip"]
            if abs(self.closed[i]["net_usd"]*1000-p["net"])>1e-7:
                raise ValueError("oracle_fraction_cost_bridge")
            self.money_checks+=1
            if (self.phase<3 and not self.open and
                    self.cash>=CAP+(5000000 if self.phase==1 else 2500000) and len(self.days)>=4):
                if not any(p["at"]==at and p["phase"]==self.phase for p in self.expected["phase_passes"]):
                    raise ValueError("oracle_missing_phase_pass")
        elif kind=="pass":
            if (self.open or len(self.days)<4 or
                    self.cash<CAP+(5000000 if self.phase==1 else 2500000)
                    or extra["days"]!=len(self.days)
                    or abs(extra["balance_usd"]*1000-self.cash)>1e-7):
                raise ValueError("oracle_invalid_phase_pass")
            self.phase+=1;self.cash=self.anchor=self.peak=CAP
            self.days=set();self.gate=at;self.phase_checks+=1
        elif kind=="reward":
            since=self.last_reward if self.last_reward is not None else self.first_funded
            amount=int(round(extra["gross_removed_usd"]*1000))
            if (self.phase!=3 or self.open or since is None or at-since<self.reward_days*DAY
                    or self.cash-CAP!=amount or amount<20000):
                raise ValueError("oracle_invalid_reward")
            trader=(amount*80//100)//10*10
            if (abs(extra["trader_usd"]*1000-trader)>1e-7 or
                    abs((extra["trader_usd"]+extra["firm_usd"])*1000-amount)>1e-7):
                raise ValueError("oracle_reward_cash_debit")
            self.cash-=amount;self.anchor=self.peak=CAP
            self.last_reward=at;self.gate=at;self.reward_checks+=1
        self.point(at,quote)
        if self.realized_balance()-self.anchor<=-1000000:
            self.halt=True

    def finish(self):
        expected=self.expected
        for value,name in ((self.dd,"peak_dd_pct"),(self.daily,"worst_daily_loss_pct"),
                           (self.static,"static_loss_pct")):
            if abs(value-expected[name]*500000)>1e-6:
                raise ValueError("oracle_equity_metric:"+name)
        if (self.open or self.phase!=expected["phase"] or
                abs(self.cash-expected["balance_usd"]*1000)>1e-7 or
                bool(self.breach)!=bool(expected["first_breach"])):
            raise ValueError("oracle_terminal_cash_phase")
        return dict(start=expected["start_msc"],model=self.model,
                    portfolio=expected["include_satellite"],cash_milli_usd=self.cash,
                    phase=self.phase,dd_milli_usd=self.dd,daily_milli_usd=self.daily,
                    static_milli_usd=self.static,accepted_checked=self.entry_checks,
                    rejected_checked=self.rejected_checks,costs_checked=self.money_checks,
                    phase_passes_checked=self.phase_checks,rewards_checked=self.reward_checks,
                    max_open_stop_milli_usd=self.max_stop)


def lifecycle():
    from prop_campaign_source import PARENT
    trades=read(JOB/"system-trades.json")
    readers=dict(
        XAUUSD=Prices(read(PARENT/"attempt-2/binary-manifest.json"),FINAL),
        EURUSD=Prices(read(JOB/"system-eur-manifest.json"),FINAL),
    )
    cases=[]
    for model in MODELS:
        for system in ("SINGLE","PORTFOLIO"):
            for case in read(JOB/f"lifecycle-{model}-{system}.json"):
                cases.append(CashOracle(case,trades,model))
    actions=defaultdict(list)
    for i,t in enumerate(trades):
        a=ASSETS.index(t["asset"])
        actions[(t["entry_msc"],a,t["entry_quote_index"])].append(("entry",i,None,None))
        actions[(t["exit_msc"],a,t["exit_quote_index"])].append(("exit",i,None,None))
        for at,_ in funding(t["entry_msc"],t["exit_msc"]):
            actions[(at,-1,-1)].append(("swap",i,None,None))
    for j,case in enumerate(cases):
        for p in case.expected["phase_passes"]:
            closed=next(r for r in case.expected["closed"] if r["at"]==p["at"])
            t=trades[closed["trade"]]
            actions[(p["at"],ASSETS.index(t["asset"]),t["exit_quote_index"])].append(("pass",None,j,p))
        for p in case.expected["payouts"]:
            closed=next((r for r in case.expected["closed"] if r["at"]==p["at"]),None)
            t=trades[closed["trade"]] if closed else None
            key=(p["at"],ASSETS.index(t["asset"]),t["exit_quote_index"]) if t else (p["at"],-1,-1)
            actions[key].append(("reward",None,j,p))
    day=date(2022,1,1)
    while day<date(2025,1,1):
        at=int(datetime(day.year,day.month,day.day,tzinfo=PRAGUE).timestamp()*1000)
        if START<=at<FINAL:actions[(at,-1,-1)].append(("reset",None,None,None))
        day+=timedelta(days=1)
    priority={"reset":0,"swap":1,"exit":2,"pass":3,"reward":4,"entry":5}
    keys=sorted(actions);cursor=0;last=None;checked_quotes=0
    first=min(t["entry_msc"] for t in trades)//HOUR*HOUR

    def consume(rows):
        nonlocal last
        if not len(rows):return
        cache={}
        for case in cases:
            if case.expected["start_msc"]<=int(rows["t"][0]) and int(rows["t"][-1])<FINAL:
                case.segment(rows,cache)
        last=rows[-1]

    for hour in range(first,FINAL,HOUR):
        rows,maps=checked_joint_hour(readers,hour,last)
        checked_quotes+=len(rows);start=0
        while cursor<len(keys) and keys[cursor][0]<hour+HOUR:
            key=keys[cursor];at,asset,ordinal=key
            stop=int(rows["t"].searchsorted(at)) if asset<0 else int(maps[asset][ordinal])
            consume(rows[start:stop])
            if asset>=0:
                last=rows[stop]
                for case in cases:
                    if case.expected["start_msc"]<=at<FINAL:case.point(at,last)
            for kind,i,j,p in sorted(actions[key],key=lambda r:priority[r[0]]):
                targets=cases if j is None else [cases[j]]
                for case in targets:case.action(kind,i,at,last,p)
            start=stop;cursor+=1
        consume(rows[start:])
        if hour%(1000*HOUR)==0:
            event("V3_joint_cash_oracle",hour=datetime.fromtimestamp(hour/1000,timezone.utc).isoformat(),
                  accounts=len(cases),source_quote_updates=checked_quotes)
    records=[case.finish() for case in cases]
    result=dict(status="PASS",accounts=len(records),records=records,
                source_quote_updates_independently_checked=checked_quotes,
                accepted_decisions=sum(r["accepted_checked"] for r in records),
                rejected_decisions=sum(r["rejected_checked"] for r in records),
                cost_bridges=sum(r["costs_checked"] for r in records),
                phase_passes=sum(r["phase_passes_checked"] for r in records),
                reviewer_sha256=digest(__file__),
                independent_implementation_same_operator=True)
    write_json(JOB/"lifecycle-parity.json",result)
    event("V3_joint_cash_oracle_passed",accounts=len(records),
          accepted=result["accepted_decisions"],rejected=result["rejected_decisions"])


if __name__=="__main__":
    lifecycle()

"""Alternate V5 cash-posted funding, admissions and dynamic-fill accounting."""
from collections import defaultdict
from datetime import date, datetime, timedelta
from fractions import Fraction as F
import numpy as np
from prop_portfolio_review import CashOracle, parts, cent_milli, checked_joint_hour
from prop_campaign_accounts import PRAGUE
from xau_h1_execution_review import funding
from prop_v5_common import *


class Oracle(CashOracle):
    def __init__(self, expected, trades):
        local=[dict(t) for t in trades]
        for closed in expected["closed"]:
            local[closed["trade"]].update(closed.get("execution_override",{}))
        super().__init__(expected,local,expected["cell"],cocore=True,reward_days=14)
        self.protected=False
        self.frozen=False

    def measure(self, values, times):
        if len(values) and not self.breach and self.phase==1:
            equities=values+self.cash-self.basis
            running=np.maximum.accumulate(np.r_[self.peak,equities])[1:]
            self.protected|=bool(np.any((running>=53500000)&(equities<=52500000)))
        super().measure(values,times)

    def entry(self,i,at,quote):
        t=self.trades[i];accepted=self.accepted.get(i)
        balance=self.realized_balance();equity=self.cash+self.gross_point(quote)
        if balance-self.anchor<=-1000000:self.halt=True
        reason=None
        if self.phase==3 and self.first_funded is not None:
            since=self.last_reward if self.last_reward is not None else self.first_funded
            self.frozen|=(balance>=51000000 or balance>=50500000 and at>=since+12*DAY)
        if self.frozen:reason="HARVEST"
        if t["decision_msc"]<self.expected["start_msc"] or t["decision_msc"]<=self.gate:
            reason=reason or "PHASE_GATE"
        if any(self.trades[k]["asset"]==t["asset"] and self.trades[k]["decision_msc"]==t["decision_msc"]
               for k in self.open):reason=reason or "COLLISION"
        if self.halt:reason=reason or "DAILY_HALT"
        risk=(200,175,125)[self.phase-1]
        if equity<=47000000:risk=min(risk,90)
        elif equity<=48000000:risk=min(risk,150)
        if self.phase==1 and self.peak>=53500000:risk=min(risk,90 if self.protected else 125)
        if self.phase==2 and self.peak>=51750000:risk=min(risk,100)
        unit=1 if t["asset"]=="XAUUSD" else 10
        q=int(risk*1000)//(unit*abs(t["entry_price_units"]-t["stop_units"]))
        if not 1<=q<=(5000 if t["asset"]=="XAUUSD" else 100000):reason=reason or "LOT"
        oldrisk=sum(size*(1 if self.trades[k]["asset"]=="XAUUSD" else 10)*
                    abs(self.trades[k]["entry_price_units"]-self.trades[k]["stop_units"])
                    for k,size in self.open.items())
        newrisk=q*unit*abs(t["entry_price_units"]-t["stop_units"])
        if oldrisk+newrisk>800000:reason=reason or "CAP"
        money=parts(t,q,self.model)
        projected=balance-money["fee0"]
        for k,size in list(self.open.items())+[(i,q)]:
            old=self.trades[k];gold=old["asset"]=="XAUUSD";s=1 if old["side"]=="BUY" else -1
            projected+=s*size*(1 if gold else 10)*(old["stop_units"]-old["entry_price_units"])
            fee=cent_milli(F(old["stop_units"],1000)*size*F(7,1000000)) if gold else cent_milli(F(size,40))
            projected-=fee+size*(400 if gold else 40)
            rate=(-400 if self.model.startswith("SYM") else -450 if old["side"]=="BUY" else -50) if gold else -400
            projected+=min(0,rate)*size*sum(m for _,m in funding(old["entry_msc"],old["deadline_msc"]))
        if self.phase==1 and self.protected and projected<=52500000:reason=reason or "PROTECTED_FLOOR"
        if projected<=46000000 or projected<max(self.anchor-2500000,45000000):reason=reason or "RESERVE"
        if bool(accepted)!=(reason is None):
            raise ValueError(f"V5_oracle_admission:{i}:{at}:{reason}:{self.expected['start_msc']}")
        if accepted is None:self.rejected_checks+=1;return
        if accepted["risk_usd"]!=risk or accepted["ounces"]!=q or accepted["phase"]!=self.phase:
            raise ValueError("V5_oracle_risk_or_quantity")
        self.components[i]=money;self.open[i]=q;self.charges[i]=0
        asset=0 if t["asset"]=="XAUUSD" else 2;buy=t["side"]=="BUY"
        self.coeff[asset if buy else asset+1]+=(1 if buy else -1)*q*unit
        self.basis+=(1 if buy else -1)*q*unit*t["entry_price_units"]
        self.cash-=money["fee0"]+money["slip"]
        self.days.add(datetime.fromtimestamp(at/1000,timezone.utc).astimezone(PRAGUE).date())
        if self.phase==3 and self.first_funded is None:self.first_funded=at
        self.max_stop=max(self.max_stop,oldrisk+newrisk);self.entry_checks+=1

    def action(self,kind,i,at,quote,extra=None):
        old=self.phase
        if kind=="session_flat" and self.phase==3 and self.first_funded is not None:
            balance=self.realized_balance()
            since=self.last_reward if self.last_reward is not None else self.first_funded
            self.frozen|=(balance>=51000000 or balance>=50500000 and at>=since+12*DAY)
            return
        super().action(kind,i,at,quote,extra)
        if old!=self.phase:self.protected=self.frozen=False
        if kind=="reward":self.frozen=False
        if self.phase==3 and self.first_funded is not None:
            balance=self.realized_balance()
            since=self.last_reward if self.last_reward is not None else self.first_funded
            self.frozen|=(balance>=51000000 or balance>=50500000 and at>=since+12*DAY)


def review():
    from prop_v5_campaign import inputs
    trades,readers,end=inputs(True)
    expected=read(JOB/"validation-accounts.json")
    if read(DECISION)["mechanism"]!="PARENT":
        raise ValueError("oracle_requires_separate_D1_D2_admission_extension")
    cases=[Oracle(c,trades) for c in expected]
    actions=defaultdict(list)
    for i,t in enumerate(trades):
        actions[(t["entry_msc"],0 if t["asset"]=="XAUUSD" else 1,t["entry_quote_index"])].append(("entry",i,None,None))
    dynamic=0
    for j,case in enumerate(cases):
        for i,a in case.accepted.items():
            t=case.trades[i];asset=0 if t["asset"]=="XAUUSD" else 1
            actions[(t["exit_msc"],asset,t["exit_quote_index"])].append(("exit",i,j,None))
            for at,_ in funding(t["entry_msc"],t["exit_msc"]):
                actions[(at,-1,-1)].append(("swap",i,j,None))
        for c in case.expected["closed"]:
            if "execution_override" in c:
                dynamic+=1;t=case.trades[c["trade"]]
                tick=readers[t["asset"]].hour(t["exit_msc"]//HOUR*HOUR)[t["exit_quote_index"]]
                field="b" if t["side"]=="BUY" else "a"
                if int(tick["t"])!=t["exit_msc"] or int(tick[field])!=t["exit_price_units"]:
                    raise ValueError("dynamic_close_not_actual_native_quote")
        for kind,field in (("pass","phase_passes"),("reward","payouts")):
            for p in case.expected[field]:
                c=next((r for r in case.expected["closed"] if r["at"]==p["at"]),None)
                t=case.trades[c["trade"]] if c else None
                key=(p["at"],0 if t["asset"]=="XAUUSD" else 1,t["exit_quote_index"]) if t else (p["at"],-1,-1)
                actions[key].append((kind,None,j,p))
    day=date(2022,1,1)
    while day<date(2025,1,1):
        at=int(datetime(day.year,day.month,day.day,tzinfo=PRAGUE).timestamp()*1000)
        if START<=at<end:actions[(at,-1,-1)].append(("reset",None,None,None))
        # Sessions follow the already frozen holiday calendar.
        from prop_campaign_source import Calendar,CALENDAR
        r=Calendar(CALENDAR).events.get(day.isoformat(),{})
        clock=None if r.get("kind")=="CLOSED" else (r.get("flat_utc") or "20:30")
        if clock and day.weekday()<5:
            utc0=int(datetime(day.year,day.month,day.day,tzinfo=timezone.utc).timestamp()*1000)
            actions[(utc0+(int(clock[:2])*60+int(clock[3:]))*60000,-1,-1)].append(("session_flat",None,None,None))
        day+=timedelta(days=1)
    priority=dict(reset=0,swap=1,session_flat=2,exit=3,**{"pass":4},reward=5,entry=6)
    keys=sorted(actions);cursor=0;last=None;quotes=0
    def consume(rows):
        nonlocal last
        if not len(rows):return
        cache={}
        for c in cases:
            if c.expected["start_msc"]<=int(rows["t"][0]):c.segment(rows,cache)
        last=rows[-1]
    first=min(t["entry_msc"] for t in trades)//HOUR*HOUR
    for hour in range(first,end,HOUR):
        rows,maps=checked_joint_hour(readers,hour,last);quotes+=len(rows);start=0
        while cursor<len(keys) and keys[cursor][0]<hour+HOUR:
            at,asset,index=keys[cursor]
            stop=int(rows["t"].searchsorted(at)) if asset<0 else int(maps[asset][index])
            consume(rows[start:stop])
            if asset>=0:
                last=rows[stop]
                for c in cases:
                    if c.expected["start_msc"]<=at<end:c.point(at,last)
            for kind,i,j,p in sorted(actions[keys[cursor]],key=lambda x:priority[x[0]]):
                for c in (cases if j is None else [cases[j]]):
                    c.action(kind,i,at,last,p)
            start=stop;cursor+=1
        consume(rows[start:])
        if hour%(1000*HOUR)==0:event("V5_alternate_cash_oracle",accounts=len(cases),hour=hour)
    records=[c.finish() for c in cases]
    write_json(JOB/"accounting-parity.json",dict(
        status="PASS",accounts=len(records),records=records,joint_quotes=quotes,
        accepted=sum(r["accepted_checked"] for r in records),
        rejected=sum(r["rejected_checked"] for r in records),
        money_bridges=sum(r["costs_checked"] for r in records),
        dynamic_native_fills=dynamic,same_implementer_alternate_arithmetic=True))
    event("V5_accounting_oracle_passed",accounts=len(cases),dynamic_fills=dynamic)


if __name__=="__main__":review()

"""V14 cost adapter over the existing CoCore/Harvest state machine."""
from contextlib import ExitStack,contextmanager
from decimal import Decimal,ROUND_HALF_UP
from datetime import datetime,timezone
import numpy as np
from prop_v6_account import HarvestAccount
from prop_portfolio_accounts import VALUE
from prop_campaign_accounts import CAPITAL
from quant_core.prop_lifecycle_and_parity import bindings,simulate
from xau_h1_stage0_scan import funding_events

D=Decimal
SLIP={"XAUUSD":200,"EURUSD":10}


def cent_milli(value):
    return int(D(str(value)).quantize(D(".01"),rounding=ROUND_HALF_UP)*1000)


def commission_milli(trade,price,q):
    if trade["asset"]=="XAUUSD":
        return cent_milli(D(price)/1000*q*D(".000007"))
    return cent_milli(D(q)*D(".035"))


def entry_charge(trade,price,q):
    # Legacy entry/close bridge adds this exact charge back before settling total net.
    return commission_milli(trade,price,q)+q*SLIP[trade["asset"]]


def funding_step(trade,model):
    if trade["asset"]=="EURUSD":return -400
    return -400 if model.startswith("SYM") else -450 if trade["side"]=="BUY" else -50


def trade_money(trade,q,model,risk):
    sign=1 if trade["side"]=="BUY" else -1
    gross=cent_milli(D(sign*q*VALUE[trade["asset"]]*(trade["exit_price_units"]-trade["entry_price_units"]))/1000)
    fees=sum(commission_milli(trade,px,q) for px in (trade["entry_price_units"],trade["exit_price_units"]))
    exit_slip=0 if model.startswith("ASYM") and trade["reason"]=="TP" else q*SLIP[trade["asset"]]
    slippage=q*SLIP[trade["asset"]]+exit_slip
    swap=q*funding_step(trade,model)*sum(e["multiplier"] for e in funding_events(trade["entry_msc"],trade["exit_msc"]))
    net=gross-fees-slippage+swap
    return dict(gross_usd=gross/1000,commission_usd=fees/1000,slippage_usd=slippage/1000,
                swap_usd=swap/1000,net_usd=net/1000,net_R=net/(risk*1000))


class V14Account(HarvestAccount):
    """Only contract adapters; inherited V4 phase risks and V6 Funded harvesting."""
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.resets_with_open=[]

    def reserve_floor(self,trades,new_id,q,charge):
        result=self.balance-charge
        positions=dict(self.active);positions[new_id]=(q,0)
        for i,(quantity,_) in positions.items():
            t=trades[i];sign=1 if t["side"]=="BUY" else -1
            if t["deadline_msc"]<t["entry_msc"]:raise ValueError("prelocked_reserve_deadline")
            result+=sign*quantity*VALUE[t["asset"]]*(t["stop_units"]-t["entry_price_units"])
            result-=commission_milli(t,t["stop_units"],quantity)+quantity*SLIP[t["asset"]]
            result+=min(0,funding_step(t,self.cell))*quantity*sum(
                e["multiplier"] for e in funding_events(t["entry_msc"],t["deadline_msc"]))
        return result

    def check(self,at,floating):
        super().check(at,floating)
        # Equality touches the stated limit too; old frozen engines keep their historical '<'.
        if self.rolling and not self.breach:
            equity=self.balance+floating
            if equity<=max(self.anchor-2500000,45000000):
                self.breach=dict(at=int(at),phase=self.phase,equity_usd=equity/1000,
                    daily=equity<=self.anchor-2500000,overall=equity<=45000000)

    def action(self,kind,at,i,trades,quote,mult=0):
        if kind=="entry" and not self.rolling and self.start<=at<self.end:
            from prop_portfolio_accounts import quantity_steps
            try:quantity_steps(trades[i],self.fixed_risk)
            except ValueError:
                # A natural stop can exceed the reference risk at minimum lot.
                # The lifecycle branch already rejects this; never round up.
                self.rejected["LOT_GRID_MIN_MAX"]+=1
                return
        if kind=="reset" and self.start<=at<self.end and self.active:
            self.resets_with_open.append(dict(at=int(at),mark_age_ms=int(at-quote["t"]),
                active=len(self.active),scope="carried last scenario quote, not observed midnight tick"))
        super().action(kind,at,i,trades,quote,mult)

    def segment(self,rows,trades,cache):
        # The inherited vector branch tests '<'; preserve equality-touch semantics.
        if self.rolling and self.active and not self.breach and len(rows):
            values=np.full(len(rows),self.balance+sum(self.accrued.values()),dtype="int64")
            for i,(q,_) in self.active.items():
                t=trades[i];gold=t["asset"]=="XAUUSD"
                field=("b0" if gold else "b1") if t["side"]=="BUY" else ("a0" if gold else "a1")
                values+=(1 if t["side"]=="BUY" else -1)*q*VALUE[t["asset"]]*(
                    rows[field].astype("int64")-t["entry_price_units"])-q*SLIP[t["asset"]]
            threshold=max(self.anchor-2500000,45000000)
            hit=np.flatnonzero(values<=threshold)
            if len(hit) and values[hit[0]]==threshold:
                j=int(hit[0])
                super().segment(rows[:j+1],trades,{})
                if not self.breach:self.check(int(rows["t"][j]),self.floating(trades,rows[j]))
                if not self.breach:super().segment(rows[j+1:],trades,{})
                return
        super().segment(rows,trades,cache)

    def dump(self):
        row=super().dump()
        row.update(policy="V14_V4_Harvest_equal_risk",cost_contract="V13_UNIT_COSTS_AT_ACTUAL_QUANTITY",
            entry_slip_charged_at_entry=True,midnight_carried_marks=self.resets_with_open,
            account_source="conditional M1 scenario, Ask proxy, missing-path model",
            prop_qualified=False)
        return row


@contextmanager
def cost_bindings():
    import prop_portfolio_accounts as portfolio
    import prop_v5_account as v5
    import prop_v6_account as v6
    import prop_v6_replay as replay
    with ExitStack() as stack:
        stack.enter_context(bindings(replay,event=lambda stage,**kw:print(
            dict(stage="V14_"+stage,**kw),flush=True)))
        for module in (portfolio,v5,v6):
            values={}
            for name,value in (("entry_exit_fee",entry_charge),("trade_money",trade_money),
                               ("SLIP",SLIP),("funding_step",funding_step)):
                if hasattr(module,name):values[name]=value
            stack.enter_context(bindings(module,**values))
        yield


def monthly_starts(first,end):
    out=[]
    for y in range(2018,2027):
        for m in range(1,13):
            at=int(datetime(y,m,1,tzinfo=timezone.utc).timestamp()*1000)
            if first<=at<end and (y,m)<=(2026,9):out.append(at)
    return out


def replay_accounts(trades,readers,calendar,first,end):
    accounts=[];metadata=[]
    for model in ("SYM_FLAT","ASYM_FLAT"):
        for at in monthly_starts(first,end):
            accounts.append(V14Account(at,end,model,rolling=True))
            metadata.append(dict(kind="CHALLENGE",year=datetime.fromtimestamp(at/1000,timezone.utc).year))
        accounts.append(V14Account(first,end,model,rolling=True,standalone=True))
        metadata.append(dict(kind="STANDALONE_FULL",year=2018))
        for year in range(2018,2027):
            at=int(datetime(year,1,1,tzinfo=timezone.utc).timestamp()*1000)
            stop=min(end,int(datetime(year+1,1,1,tzinfo=timezone.utc).timestamp()*1000))
            accounts.append(V14Account(at,stop,model,rolling=False,fixed_risk=150))
            metadata.append(dict(kind="ANNUAL_REFERENCE",year=year))
    with cost_bindings():
        rows=simulate(trades,readers,accounts,first,end,calendar)
    return [dict(r,**meta) for r,meta in zip(rows,metadata)]

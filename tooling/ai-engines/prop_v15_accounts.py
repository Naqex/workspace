"""V15 risk aperture over the existing V4/V6 lifecycle, costs and harvester."""
from prop_v14_accounts import V14Account,cost_bindings,monthly_starts
from decimal import Decimal
from contextlib import ExitStack,contextmanager
from prop_portfolio_accounts import VALUE
from prop_v15_common import *
from quant_core.prop_lifecycle_and_parity import simulate


class V15Account(V14Account):
    open_cap_milli=1000000
    internal_floor_milli=45800000
    cap_rejection="V15_OPEN_STOP_RISK_2PCT_CAP"
    floor_rejection="V15_INTERNAL_STATIC_8P4PCT_RESERVE"

    def __init__(self,*args,factor=1.,cushion=False,**kwargs):
        super().__init__(*args,**kwargs)
        if factor not in FACTORS:raise ValueError("unregistered_V15_factor")
        self.factor=factor;self.cushion=cushion;self.cushion_armed=False
        self.cushion_phase=self.phase

    def observe_policy(self,at,equity):
        if self.cushion_phase!=self.phase:
            self.cushion_armed=False;self.cushion_phase=self.phase
        if self.cushion and self.phase==1:
            if self.balance<=50000000:self.cushion_armed=False
            elif self.balance>=51500000:self.cushion_armed=True
        super().observe_policy(at,equity)

    def risk_request(self,equity,role,weight):
        if not self.rolling:return self.fixed_risk
        if role!="CORE" or weight!=1:raise ValueError("V15_only_frozen_equal_core")
        risk=int(Decimal((200,175,125)[self.phase-1])*Decimal(str(self.factor))*1000)
        if self.cushion and self.phase==1 and self.cushion_armed and equity>50000000:
            risk+=min((self.balance-50000000)//5,250000)
        if equity<=46500000:risk=min(risk,75000)
        elif equity<=47500000:risk=min(risk,150000)
        return risk/1000

    def dump(self):
        return dict(super().dump(),policy="V15_DD_CUSHION" if self.cushion else "V15_DD",
            V15_factor=self.factor,cushion=self.cushion,cushion_armed=self.cushion_armed,
            requested_phase_risks_usd=[v*self.factor for v in (200,175,125)],
            open_risk_cap_pct=2.,internal_reserve_pct=8.4)


class SleeveBook(V14Account):
    def __init__(self,*args,sleeve_id,**kwargs):
        super().__init__(*args,rolling=False,fixed_risk=150,**kwargs)
        self.sleeve_id=sleeve_id

    def action(self,kind,at,i,trades,quote,mult=0):
        if kind=="entry" and trades[i]["id"]!=self.sleeve_id:return
        super().action(kind,at,i,trades,quote,mult)

    def dump(self):return dict(super().dump(),sleeve_id=self.sleeve_id)


def exact_quantity(trade,risk):
    amount=int(Decimal(str(risk))*1000)
    q=amount//(VALUE[trade["asset"]]*abs(trade["entry_price_units"]-trade["stop_units"]))
    if not 1<=q<=(5000 if trade["asset"]=="XAUUSD" else 100000):raise ValueError("position_grid")
    return q


@contextmanager
def execution_bindings():
    import prop_portfolio_accounts as portfolio
    import prop_v5_account as v5
    from quant_core.prop_lifecycle_and_parity import bindings
    with ExitStack() as stack:
        stack.enter_context(cost_bindings())
        for module in (portfolio,v5):stack.enter_context(bindings(module,quantity_steps=exact_quantity))
        yield


def replay_profiles(trades,readers,calendar,profiles,dev):
    end=DEV_END if dev else END;accounts=[];labels=[]
    for profile in profiles:
        for model in ("SYM_FLAT","ASYM_FLAT"):
            starts=[(at,False) for at in monthly_starts(FIRST,end)]+[(FIRST,True)]
            for at,standalone in starts:
                klass=V14Account if profile["name"]=="V14" else V15Account
                kwargs={} if klass is V14Account else dict(factor=profile["factor"],cushion=profile.get("cushion",False))
                accounts.append(klass(at,end,model,rolling=True,standalone=standalone,**kwargs))
                labels.append(dict(profile=profile["name"],kind="STANDALONE_FULL" if standalone else "CHALLENGE"))
    import prop_v6_replay as replay
    from quant_core.prop_lifecycle_and_parity import bindings
    with execution_bindings(),bindings(replay,event=lambda stage,**kw:event("V15_"+stage,**kw)):
        out=simulate(trades,readers,accounts,FIRST,end,calendar)
    return [dict(r,**label) for r,label in zip(out,labels)]


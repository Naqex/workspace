"""One two-tier policy with reserved swing/intraday capacity and daily reserve."""
from decimal import Decimal,ROUND_FLOOR
from prop_v15_accounts import V15Account,execution_bindings
from prop_portfolio_accounts import VALUE

DAY=86400000
TOTAL=1000000
SWING=400000
INTRADAY=600000
DAILY=1200000


def bucket(trade):
    return "INTRADAY" if trade["deadline_msc"]//DAY==trade["entry_msc"]//DAY else "SWING"


def bucket_cap(trades,active,target):
    if bucket(trades[target])=="INTRADAY":return TOTAL
    intraday=sum(q*VALUE[trades[i]["asset"]]*abs(trades[i]["entry_price_units"]-trades[i]["stop_units"])
        for i,(q,_) in active.items() if bucket(trades[i])=="INTRADAY")
    return min(TOTAL,intraday+SWING)


class V17Account(V15Account):
    cap_rejection="V17_BUCKET_OR_TOTAL_STOP_CAP"
    floor_rejection="V17_STATIC_OR_DAILY_RESERVE"

    def __init__(self,*args,tiers,**kwargs):
        if not tiers or any(w not in (1.,.6) for w in tiers.values()):raise ValueError("V17_registered_tiers_only")
        self.tiers=dict(tiers);self._request=None;self._tape=None
        super().__init__(*args,factor=1.5,cushion=True,**kwargs)

    @property
    def open_cap_milli(self):
        return TOTAL if self._request is None else bucket_cap(self._tape,self.active,self._request)

    @property
    def internal_floor_milli(self):
        return max(45800000,self.anchor-DAILY)

    def risk_request(self,equity,role,weight):
        if self._request is None:raise ValueError("V17_risk_needs_current_trade")
        identity=self._tape[self._request]["id"]
        if identity not in self.tiers:raise ValueError("V17_unregistered_sleeve")
        base=super().risk_request(equity,role,weight)
        milli=(Decimal(str(base))*Decimal(str(self.tiers[identity]))*1000).to_integral_value(rounding=ROUND_FLOOR)
        return float(milli/1000)

    def action(self,kind,at,i,trades,quote,mult=0):
        if kind=="entry":self._request=i;self._tape=trades
        try:return super().action(kind,at,i,trades,quote,mult)
        finally:
            if kind=="entry":self._request=None

    def dump(self):
        return dict(super().dump(),policy="V17_TIER_BUCKET_DAILY_RESERVE",tiers=self.tiers,
            total_stop_cap_usd=1000,swing_stop_cap_usd=400,intraday_reserved_stop_usd=600,
            intraday_borrows_unused_swing=True,daily_reserved_loss_usd=1200,
            carry_enabled=False,entry_guard_not_gap_fill_guarantee=True)

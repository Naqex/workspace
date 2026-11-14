"""One fixed safer policy: phase risk, early throttle and shared 7% reserve."""
from collections import Counter
from prop_campaign_accounts import Account
from prop_campaign_exits import quantity
from xau_h1_execution import commission,cents


class RiskV2(Account):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.risk_buckets=Counter();self.internal_rejections=[]

    def risk(self,equity):
        if not self.rolling:return self.fixed_risk
        risk=125 if self.phase==3 else 200
        if equity<47750000:risk=min(risk,90)
        elif equity<48750000:risk=min(risk,150)
        if self.balance-self.anchor<-900000:risk=min(risk,125)
        return risk

    def action(self,kind,at,i,trades,quote,mult=0):
        count=len(self.accepted);state=None
        if (kind=='entry' and self.rolling and self.start<=at<self.end and
                not self.breach and trades[i]['decision_msc']>self.gate):
            risk=self.risk(self.balance+self.floating(trades,quote))
            q=quantity(trades[i],risk)
            fee=cents(commission(trades[i]['entry_price_units'],q))*10
            projected=self.reserve_floor(trades,i,q,fee)
            state=dict(balance_milli_usd=self.balance,
                equity_milli_usd=self.balance+self.floating(trades,quote),
                daily_anchor_milli_usd=self.anchor,projected_stop_milli_usd=projected)
            if projected<=46500000:
                self.rejected['INTERNAL_STATIC_7PCT_RESERVE']+=1
                self.internal_rejections.append(dict(trade=i,at=at,phase=self.phase,
                    risk_usd=risk,projected_stop_equity_usd=projected/1000))
                return
        super().action(kind,at,i,trades,quote,mult)
        if len(self.accepted)>count:
            self.risk_buckets[str(self.accepted[-1]['risk_usd'])]+=1
            self.accepted[-1]['risk_state']=state

    def dump(self):
        r=super().dump()
        r.update(risk_buckets=dict(self.risk_buckets),
            internal_reserve_rejections=self.internal_rejections,
            policy='V2_phase200_200_125_throttle150_90_internal7',
            internal_static_target_met=self.static<3500000)
        return r

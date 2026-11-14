"""Joint block-bootstrap stress surrogate; explicitly not an exact tick replay."""
from datetime import datetime, timezone, timedelta
from pathlib import Path
import numpy as np
from prop_v5_common import *
from prop_v5_account import V5Account
from prop_portfolio_accounts import VALUE, SLIP, FIELDS
from prop_campaign_accounts import PRAGUE


class LedgerBook(V5Account):
    """Ordered daily extrema from native ticks; source contains no prop gates."""
    def __init__(self,*args,**kw):
        super().__init__(*args,controller=False,**kw)
        self.ledger=[];self.day=None;self.daystart=None
        self.open_eq=self.open_cash=None
        self.low=self.high=None;self.low_at=self.high_at=None

    def point(self,at,equity):
        if self.day is None:
            self.day=datetime.fromtimestamp(at/1000,timezone.utc).astimezone(PRAGUE).date().isoformat()
            self.daystart=at;self.open_eq=equity;self.open_cash=self.balance
        if self.low is None or equity<self.low:self.low=equity;self.low_at=at
        if self.high is None or equity>self.high:self.high=equity;self.high_at=at

    def finish_day(self,at,quote):
        if self.day is None:return
        eq=self.balance+self.floating(self._trades,quote)
        self.ledger.append(dict(
            day=self.day,open_eq=self.open_eq/1000,open_cash=self.open_cash/1000,
            close_eq=eq/1000,close_cash=self.balance/1000,
            low=self.low/1000,high=self.high/1000,
            low_at=self.low_at,high_at=self.high_at,
            closed_cash_delta=(self.balance-self.open_cash)/1000,
            equity_delta=(eq-self.open_eq)/1000,reference_risk_usd=self.fixed_risk))
        self.day=None;self.low=self.high=None

    def action(self,kind,at,i,trades,quote,mult=0):
        if not self.start<=at<self.end:return
        if kind=="reset":
            self.finish_day(at,quote)
        super().action(kind,at,i,trades,quote,mult)
        self.point(at,self.balance+self.floating(trades,quote))

    def segment(self,rows,trades,cache):
        if not len(rows):return
        values=np.full(len(rows),self.balance+sum(self.accrued.values()),dtype="int64")
        for i,(q,_) in self.active.items():
            t=trades[i];field=FIELDS[t["asset"]][0 if t["side"]=="BUY" else 1]
            values+=((1 if t["side"]=="BUY" else -1)*q*VALUE[t["asset"]]
                     *(rows[field].astype("int64")-t["entry_price_units"])-q*SLIP[t["asset"]])
        lo=int(values.argmin());hi=int(values.argmax())
        self.point(int(rows["t"][lo]),int(values[lo]))
        self.point(int(rows["t"][hi]),int(values[hi]))
        super().segment(rows,trades,cache)


def block_indices(length,paths=10000,days=252,block=20,seed=20261115):
    if length<block or min(paths,days,block)<=0:raise ValueError("bootstrap_block_or_length")
    rng=np.random.default_rng(seed)
    starts=rng.integers(0,length-block+1,size=(paths,(days+block-1)//block))
    return (starts[:,:,None]+np.arange(block)).reshape(paths,-1)[:,:days]


def simulate(ledger,indices,funded=False):
    """Daily extrema proxy with V5 ratchet/harvest states and full cash debit.

    Daily equity increments settle as flat cash at day end. Source multi-day
    positions, per-order caps/reserves and next-quote force fills cannot be
    reconstructed from daily extrema. These outputs are stress sensitivities,
    never probabilities from the exact V5 executable policy.
    """
    n,days=indices.shape
    close=np.array([d["equity_delta"]/150 for d in ledger])
    low=np.array([(d["low"]-d["open_eq"])/150 for d in ledger])
    high=np.array([(d["high"]-d["open_eq"])/150 for d in ledger])
    high_first=np.array([d["high_at"]<d["low_at"] for d in ledger])
    cash=np.full(n,50000.);phase=np.full(n,3 if funded else 1,dtype="i1")
    peak=cash.copy();static=np.zeros(n);peakdd=np.zeros(n)
    daily=np.zeros(n);dead=np.zeros(n,dtype=bool);p1=np.zeros(n,dtype=bool);both=p1.copy()
    armed=p1.copy();parked=p1.copy();frozen=p1.copy()
    phase_days=np.zeros(n,dtype=int);funded_days=np.zeros(n,dtype=int)
    payout=np.zeros(n);count=np.zeros(n,dtype=int)
    for day in range(days):
        k=indices[:,day];alive=~dead
        risk=np.select([phase==1,phase==2],[200.,175.],125.)
        risk=np.where(cash<=47000,np.minimum(risk,90),np.where(cash<=48000,np.minimum(risk,150),risk))
        risk=np.where(armed&(phase==1),np.minimum(risk,125),risk)
        risk=np.where(armed&(phase==2),np.minimum(risk,100),risk)
        risk=np.where(parked|frozen|dead,0.,risk)
        start=cash.copy()
        level=cash.copy()
        # Preserve observed order of daily max/min, not an invented favorable order.
        values=[np.where(high_first[k],high[k],low[k]),
                np.where(high_first[k],low[k],high[k]),close[k]]
        for step,delta in enumerate(values):
            mark=start+risk*delta
            mark=np.where(parked|dead,level,mark)
            static=np.maximum(static,np.maximum(0,50000-mark))
            peakdd=np.maximum(peakdd,peak-mark);peak=np.maximum(peak,mark)
            daily=np.maximum(daily,start-mark)
            violation=(mark<45000)|(mark<start-2500)
            level=np.where(violation&~dead,mark,level)
            dead|=violation
            threshold=np.where(phase==1,53500,51750)
            armed|=(phase<3)&(mark>=threshold)
            floor=(phase==1)&armed&(mark<=52500)&alive&~parked
            parked|=floor
            level=np.where(floor,mark,level)
            cash=np.where(parked|dead,level,mark)
        phase_days+=((risk>0)&~dead)
        passed1=(phase==1)&~dead&(cash>=55000)&(phase_days>=4)
        passed2=(phase==2)&~dead&(cash>=52500)&(phase_days>=4)
        p1|=passed1;both|=passed2
        phase=np.where(passed1,2,np.where(passed2,3,phase))
        reset=passed1|passed2
        cash=np.where(reset,50000,cash);peak=np.where(reset,50000,peak)
        armed&=~reset;parked&=~reset;phase_days=np.where(reset,0,phase_days)
        funded_days+=((phase==3)&~dead)
        due=funded_days>=10  # business-day approximation to14 calendar days.
        frozen|=(phase==3)&((cash>=51000)|((cash>=50500)&(funded_days>=8)))
        reward=(phase==3)&~dead&due&(cash>=50020)
        profit=np.where(reward,cash-50000,0)
        payout+=profit*.8;count+=reward
        cash-=profit;peak=np.where(reward,50000,peak);funded_days=np.where(reward,0,funded_days)
        frozen&=~reward
    return dict(
        step1_rate=float(p1.mean()),both_12month_rate=float(both.mean()),
        breach_rate=float(dead.mean()),max_static_percentiles_pct=[
            float(v/500) for v in np.percentile(static,[50,75,95])],
        max_peak_dd_percentiles_pct=[float(v/500) for v in np.percentile(peakdd,[50,75,95])],
        mean_trader_payout_usd=float(payout.mean()),mean_payout_count=float(count.mean()),
        mean_terminal_balance_usd=float(cash.mean()),
        pathwise=dict(p1=p1.tolist(),both=both.tolist(),breach=dead.tolist(),
                      static_usd=static.tolist(),payout_usd=payout.tolist()))


def run():
    from prop_v5_campaign import inputs
    from prop_v5_replay import replay
    trades,readers,end=inputs(True)
    mechanism=read(DECISION)["mechanism"]
    books=[LedgerBook(START,end,m,fixed_risk=150,mechanism=mechanism) for m in MODELS]
    replay(trades,readers,books,end)
    output={}
    for book in books:
        book.finish_day(end,book.last_quote)
        rows=[r for r in book.ledger if datetime.fromisoformat(r["day"]).weekday()<5]
        write_json(JOB/f"reference-daily-extrema-{book.cell}.json",rows)
        key=book.cell;output[key]={}
        for block in (20,5):
            ix=block_indices(len(rows),block=block)
            result=simulate(rows,ix)
            funded=simulate(rows,ix,True)
            # Keep individual path outcomes privately, not in tracked summaries.
            write_json(JOB/f"bootstrap-paths-{key}-{block}.json",dict(
                challenge=result.pop("pathwise"),funded=funded.pop("pathwise")))
            output[key][str(block)]=dict(
                paths=10000,block_business_days=block,challenge=result,
                funded_start=funded,ledger_days=len(rows))
            event("V5_block_bootstrap",model=key,block=block,paths=10000)
    write_json(JOB/"bootstrap-results.json",dict(
        seed=20261115,results=output,exact_V5_tick_engine=False,
        interpretation="daily-flat equity-extrema stress surrogate; not calibrated future probability",
        limitations=["Daily PnL realized at close; source multi-day positions not recreated",
                     "No per-order risk cap/reserve/lot or quote-gap executions in surrogate",
                     "Ratchet reacts to daily ordered extrema, not all tick threshold crossings",
                     "14calendar-day cycle approximated10business days; holidays omitted",
                     "Cross-block seam changes regimes and exposures; selfcorrelation retained only inside blocks",
                     "Only3historicalyears, selection exposed, no cleanOOS evidence"]))


if __name__=="__main__":run()

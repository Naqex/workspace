"""Scalar arithmetic bridge for the explicitly approximate bootstrap model."""
import numpy as np
from prop_v5_common import *
from prop_v5_bootstrap import block_indices,simulate


def scalar(ledger,indices,funded=False):
    cash=peak=50000.;phase=3 if funded else 1
    low=0.;dead=armed=parked=frozen=p1=both=False
    phase_days=funded_days=0;payout=0.;level=cash
    for i in indices:
        d=ledger[int(i)]
        risk=(200,175,125)[phase-1]
        if cash<=47000:risk=min(risk,90)
        elif cash<=48000:risk=min(risk,150)
        if armed and phase<3:risk=min(risk,125 if phase==1 else 100)
        if dead or parked or frozen:risk=0
        opening=cash;level=cash;alive=not dead
        points=[d["high"]-d["open_eq"],d["low"]-d["open_eq"]]
        if d["high_at"]>=d["low_at"]:points.reverse()
        points.append(d["equity_delta"])
        for delta in points:
            mark=level if parked or dead else opening+risk*delta/150
            low=max(low,50000-mark)
            peak=max(peak,mark)
            violation=mark<45000 or mark<opening-2500
            if violation and not dead:level=mark
            dead=dead or violation
            if phase<3 and mark>=(53500 if phase==1 else 51750):armed=True
            if phase==1 and armed and mark<=52500 and alive and not parked:
                parked=True;level=mark
            cash=level if parked or dead else mark
        if risk>0 and not dead:phase_days+=1
        if not dead and phase_days>=4 and (phase==1 and cash>=55000 or phase==2 and cash>=52500):
            if phase==1:p1=True
            else:both=True
            phase+=1;cash=peak=50000.;armed=parked=False;phase_days=0
        if phase==3 and not dead:funded_days+=1
        if phase==3 and (cash>=51000 or cash>=50500 and funded_days>=8):frozen=True
        if phase==3 and not dead and funded_days>=10 and cash>=50020:
            payout+=(cash-50000)*.8;cash=peak=50000.;funded_days=0;frozen=False
    return dict(p1=p1,both=both,breach=dead,static_usd=max(0,low),payout_usd=payout)


def review():
    comparisons=0
    for model in MODELS:
        ledger=read(JOB/f"reference-daily-extrema-{model}.json")
        for block in (20,5):
            ix=block_indices(len(ledger),paths=64,block=block)
            for funded in (False,True):
                vector=simulate(ledger,ix,funded)["pathwise"]
                for row,path in enumerate(ix):
                    expected=scalar(ledger,path,funded)
                    for key,value in expected.items():
                        if abs(float(vector[key][row])-float(value))>1e-6:
                            raise ValueError("bootstrap_scalar_bridge:"+key)
                    comparisons+=1
    # Deterministic chronological source order exposes approximation drift.
    historical={}
    exact=read(JOB/"validation-accounts.json")
    for model in MODELS:
        ledger=read(JOB/f"reference-daily-extrema-{model}.json")
        ix=np.arange(len(ledger))[None,:]
        proxy=simulate(ledger,ix)
        actual=next(c for c in exact if c["cell"]==model and c["start_msc"]==START)
        historical[model]=dict(
            daily_proxy={k:v for k,v in proxy.items() if k!="pathwise"},
            exact_jan2022=dict(phase=actual["phase"],balance_usd=actual["balance_usd"],
                              payout_usd=actual["trader_payout_usd"],
                              static_loss_pct=actual["static_loss_pct"],
                              peak_dd_pct=actual["peak_dd_pct"]))
    write_json(JOB/"bootstrap-parity.json",dict(
        status="PASS_FOR_SURROGATE_ARITHMETIC_ONLY",scalar_paths_checked=comparisons,
        historical_comparison=historical,exact_tick_model_equivalence=False))
    event("bootstrap_scalar_parity",paths=comparisons)


if __name__=="__main__":review()

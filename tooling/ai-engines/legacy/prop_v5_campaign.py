"""V5 Development selection and commit-frozen Historical Validation."""
from datetime import datetime, timezone
from pathlib import Path
from decimal import Decimal
import hashlib
import json
import subprocess
from collections import defaultdict
import numpy as np
from prop_campaign_source import PARENT
from xau_h1_stage0_source import signal_features
from prop_portfolio_accounts import quantity_steps, trade_money, SLIP, VALUE, FIELDS
from prop_v5_common import *
from prop_v5_account import V5Account
from prop_v5_replay import replay


def annotate(trades, validation=False):
    cfg=read(ROOT/"eurusd-b0-20261113/config-attempt-1.json")
    h=[]
    for first in ("20211101","20220101","20230101")+(("20240101",) if validation else ()):
        folder=ROOT/"eurusd-b0-20261113/prepared-v1"/first
        seal=read(folder/"seal.json")
        proof=next(p for p in seal["files"] if p["name"]=="bars.json")
        if digest(folder/"bars.json")!=proof["sha256"]:
            raise ValueError("EUR_features_source_changed")
        h.extend(read(folder/"bars.json")["h1"])
    hm={b[0]:b for b in h if b[5]==60}
    features={f["at"]:f for f in signal_features(h)}
    out=[]
    for original in trades:
        t=dict(original,d1_gate=True)
        if t["asset"]=="EURUSD":
            f=features[t["decision_msc"]]; day=t["decision_msc"]//DAY*DAY
            asia=[hm[day+i*HOUR] for i in range(6)]
            ratio=Decimal(max(b[2] for b in asia)-min(b[3] for b in asia))/f["atr_before"]
            t.update(d1_gate=ratio<=2,asia_atr_ratio=float(ratio),h4_bias=f["bias"])
        out.append(t)
    return out


def inputs(validation=False):
    if validation:
        release=read(JOB/"validation-release.json")
        blob=subprocess.check_output(["git","show",release["commit"]+":"+DECISION.as_posix()])
        d=read(DECISION)
        if json.loads(blob)!=d or hashlib.sha256(blob).hexdigest()!=release["git_blob_sha256"]:
            raise ValueError("V5_committed_decision_changed")
        for pin in d["pins"]:
            if digest(pin["path"])!=pin["sha256"]:
                raise ValueError("V5_frozen_input_or_code_changed:"+pin["path"])
        trades=read(V3/"system-trades.json")
        gold=read(PARENT/"attempt-2/binary-manifest.json")
        eur=read(V3/"system-eur-manifest.json")
        end=FINAL
    else:
        trades=[dict(t,asset="XAUUSD",role="CORE",regime_weight=1)
                for t in read(V1/"paths-SYM_FLAT-A0.json")]
        trades+=read(V3/"eur-satellite-dev-trades.json")
        gold=read(V1/"gold-dev-manifest-v2.json")
        eur=read(V3/"eur-native-dev-v1/manifest.json")
        end=END
    trades=annotate(trades,validation)
    trades.sort(key=lambda t:(t["entry_msc"],t["role"]=="SATELLITE"))
    if any(not START<=t["entry_msc"]<=t["exit_msc"]<end for t in trades):
        raise ValueError("V5_admitted_price_scope")
    return trades,dict(XAUUSD=Prices(gold,end),EURUSD=Prices(eur,end)),end


def diagnose():
    trades,readers,_=inputs()
    eur=[t for t in trades if t["asset"]=="EURUSD"]
    cash=peak=50000000; peak_at=START; worst=0; worst_tuple=None
    samples=[]; ledger=[]
    for t in eur:
        q=quantity_steps(t,150);money=trade_money(t,q,"SYM_FLAT",150)
        from prop_portfolio_accounts import entry_exit_fee
        cash-=entry_exit_fee(t,t["entry_price_units"],q)
        ticks,_=readers["EURUSD"].path(t["entry_msc"],t["exit_msc"])
        px=ticks["b"] if t["side"]=="BUY" else ticks["a"]
        eq=cash+(1 if t["side"]=="BUY" else -1)*q*10*(px.astype("int64")-t["entry_price_units"])-q*20
        running=np.maximum.accumulate(np.r_[peak,eq])
        dd=running[1:]-eq
        index=int(dd.argmax())
        if int(dd[index])>worst:
            prior=int(eq[:index+1].argmax())
            local_peak=int(eq[prior])
            top_at=int(ticks["t"][prior]) if local_peak>=peak else peak_at
            worst=int(dd[index]); worst_tuple=(top_at,int(ticks["t"][index]),int(running[index+1]),int(eq[index]))
        if int(eq.max())>peak:
            peak=int(eq.max());peak_at=int(ticks["t"][int(eq.argmax())])
        cash+=int(round(money["net_usd"]*1000))+entry_exit_fee(t,t["entry_price_units"],q)
        if cash>peak:peak=cash;peak_at=t["exit_msc"]
        samples.append(dict(at=t["entry_msc"],entry=True,value=int(eq[0])))
        samples.append(dict(at=t["exit_msc"],entry=False,value=cash))
        # Ordered extrema timestamps; extrema alone do not certify joint account path.
        minutes=ticks["t"]//60000
        starts=np.r_[0,np.flatnonzero(np.diff(minutes))+1];ends=np.r_[starts[1:],len(ticks)]
        bars=[]
        for lo,hi in zip(starts,ends):
            values=px[lo:hi];imin=lo+int(values.argmin());imax=lo+int(values.argmax())
            bars.append([int(minutes[lo]*60000),int(ticks["t"][imin]),int(px[imin]),
                         int(ticks["t"][imax]),int(px[imax]),int(px[lo]),int(px[hi-1])])
        ledger.append(dict(day=t["day"],side=t["side"],entry_msc=t["entry_msc"],
                           exit_msc=t["exit_msc"],net_R=money["net_R"],
                           asia_atr_ratio=t["asia_atr_ratio"],h4_bias=t["h4_bias"],
                           bars=bars))
    start,bottom,pv,tv=worst_tuple
    recovery=next((s["at"] for s in samples if s["at"]>bottom and s["value"]>=pv),None)
    cohort=[r for r in ledger if r["entry_msc"]>=start and r["entry_msc"]<=bottom]
    breakdown={}
    for side in ("BUY","SELL"):
        rs=[r for r in cohort if r["side"]==side]
        breakdown[side]=dict(trades=len(rs),canonical_closed_net_R=sum(r["net_R"] for r in rs))
    write_json(JOB/"eur-dd-diagnosis.json",dict(
        max_DD_R=worst/150000,start=start,trough=bottom,reference_peak_usd=pv/1000,
        reference_trough_usd=tv/1000,flat_sample_recovery=recovery,
        recovery_scope="entry/closed samples only; no recovery if final value below peak",
        side_breakdown=breakdown,cohort_trades=len(cohort),
        high_asia_ratio=dict(count=sum(r["asia_atr_ratio"]>2 for r in cohort),
                             net_R=sum(r["net_R"] for r in cohort if r["asia_atr_ratio"]>2)),
        against_h4=dict(count=sum(r["h4_bias"] not in ("NEUTRAL",r["side"]) for r in cohort),
                        net_R=sum(r["net_R"] for r in cohort if r["h4_bias"] not in ("NEUTRAL",r["side"]))),
        caution="Closed cohort contains boundary floating and exit timing; decomposition is not causal attribution",
        final_net_R=(cash-50000000)/150000))
    write_json(JOB/"eur-minute-extrema-ledger.json",dict(schema="V5-EUR-minute-extrema-v1",trades=ledger,
        layout=["minute","low_time","low_px","high_time","high_px","open_px","close_px"],
        price_scope="2022-2023 only",paired_native_ticks=True))
    event("EUR_drawdown_diagnosed",drawdown_R=worst/150000,start=start,trough=bottom)


def development():
    trades,readers,end=inputs()
    accounts=[]
    for m in MODELS:
        for mechanism in ("PARENT","D1","D2"):
            for year in (2022,2023):
                a=V5Account(stamp(f"{year}-01-01"),stamp(f"{year+1}-01-01"),m,
                            fixed_risk=150,mechanism=mechanism,controller=False)
                accounts.append(a)
            accounts.append(V5Account(START,end,m,fixed_risk=150,mechanism=mechanism,controller=False))
    combined=replay(trades,readers,accounts,end)
    write_json(JOB/"mechanism-portfolio-books.json",combined)
    eur=[t for t in trades if t["asset"]=="EURUSD"]
    a=[V5Account(stamp(f"{year}-01-01"),stamp(f"{year+1}-01-01"),"SYM_FLAT",
                 fixed_risk=150,mechanism=m,controller=False)
       for m in ("PARENT","D1","D2") for year in (2022,2023)]
    a += [V5Account(START,end,"SYM_FLAT",fixed_risk=150,mechanism=m,controller=False)
          for m in ("PARENT","D1","D2")]
    er=replay(eur,readers,a,end)
    write_json(JOB/"mechanism-eur-books.json",er)
    def book(rows,m,cell="SYM_FLAT",start=START,finish=END):
        return next(r for r in rows if r["mechanism"]==m and r["cell"]==cell
                    and r["start_msc"]==start and r["end_msc"]==finish)
    parent=book(er,"PARENT");trials=[]
    for mechanism in ("D1","D2"):
        e=book(er,mechanism);reasons=[]
        if e["max_equity_R_DD"]>=parent["max_equity_R_DD"]:reasons.append("EUR_DD_NOT_LOWER")
        for year in (2022,2023):
            a0=book(er,"PARENT",start=stamp(f"{year}-01-01"),finish=stamp(f"{year+1}-01-01"))
            a1=book(er,mechanism,start=stamp(f"{year}-01-01"),finish=stamp(f"{year+1}-01-01"))
            if a1["net_R"]<.8*a0["net_R"]:reasons.append(f"{year}:EUR_VELOCITY_LT80PCT")
        gains=[]
        for m in MODELS:
            p=book(combined,"PARENT",m);c=book(combined,mechanism,m)
            if c["max_equity_R_DD"]>=p["max_equity_R_DD"]:reasons.append(m+":PORTFOLIO_DD_NOT_LOWER")
            if c["net_R"]<.8*p["net_R"]:reasons.append(m+":PORTFOLIO_NET_LT80PCT")
            gains.append(p["max_equity_R_DD"]-c["max_equity_R_DD"])
        trials.append(dict(mechanism=mechanism,reasons=reasons,
                           min_portfolio_DD_reduction_R=min(gains),eur_DD_R=e["max_equity_R_DD"]))
    eligible=sorted([t for t in trials if not t["reasons"]],
                    key=lambda t:(-t["min_portfolio_DD_reduction_R"],t["eur_DD_R"],t["mechanism"]))
    selected=eligible[0]["mechanism"] if eligible else "PARENT"
    write_json(JOB/"mechanism-decision.json",dict(selected=selected,trials=trials,
                                                selection_years=[2022,2023],trial_count=2))
    ac=[V5Account(stamp(f"{y}-{month:02d}-01"),end,m,rolling=True,mechanism=selected)
        for m in MODELS for y in (2022,2023) for month in range(1,13)]
    rows=replay(trades,readers,ac,end)
    write_json(JOB/"development-accounts.json",rows)
    event("V5_Development_complete",selected=selected,accounts=len(rows))


def freeze():
    selection=read(JOB/"mechanism-decision.json")
    files=list(Path("tooling/ai-engines").glob("prop_v5_*.py"))+[PROTOCOL,
        Path("tooling/ai-engines/prop_campaign_accounts.py"),
        Path("tooling/ai-engines/prop_portfolio_accounts.py"),
        Path("tooling/ai-engines/prop_cocore_v4.py"),
        Path("planning/research/XAUUSD-A-SESSION-CALENDAR-20261114.json")]
    pins=[dict(path=str(p),sha256=digest(p)) for p in files]
    pins.extend(dict(path=str(p),sha256=digest(p)) for p in (
        V3/"system-trades.json",V3/"system-eur-manifest.json",PARENT/"attempt-2/binary-manifest.json"))
    out=dict(schema="PROP-OVERNIGHT-V5-DECISION-v1",utc=datetime.now(timezone.utc).isoformat(),
             mechanism=selection["selected"],selection=selection,third_sleeve=[],
             controller="ratchet7/5,3.5;harvest1/2pct;14days",core_risk_usd=[200,175,125],
             source_recovery_sha256=digest(JOB/"source-recovery.json"),
             pins=pins,dev_accounts_sha256=digest(JOB/"development-accounts.json"),
             selection2022_2023_only=True,validation2024_already_exposed=True,
             holdout2025_2026="timestamps only; no signals/PnL",
             bootstrap=dict(seed=20261115,paths_per_model=10000,primary_block_days=20,
                            sensitivity_block_days=5,year_business_days=252))
    write_json(DECISION,out);write_json(JOB/"composition-freeze.json",out)
    event("V5_frozen_needs_commit")


def release():
    head=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()
    blob=subprocess.check_output(["git","show",head+":"+DECISION.as_posix()])
    if json.loads(blob)!=read(DECISION):raise ValueError("V5_freeze_not_committed")
    write_json(JOB/"validation-release.json",dict(
        commit=head,git_blob_sha256=hashlib.sha256(blob).hexdigest(),
        utc=datetime.now(timezone.utc).isoformat()))
    event("V5_validation_released",commit=head)


def validation():
    trades,readers,end=inputs(True);mechanism=read(DECISION)["mechanism"]
    write_json(JOB/"validation-trades.json",trades)
    accounts=[V5Account(stamp(f"{y}-{month:02d}-01"),end,m,rolling=True,mechanism=mechanism)
              for m in MODELS for y in (2022,2023,2024) for month in range(1,13)]
    rows=replay(trades,readers,accounts,end)
    write_json(JOB/"validation-accounts.json",rows)
    event("V5_validation_complete",accounts=len(rows))


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("stage",choices=("diagnose","development","freeze","release","validation"))
    globals()[p.parse_args().stage]()

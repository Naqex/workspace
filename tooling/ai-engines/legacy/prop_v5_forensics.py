"""Bounded Dev diagnostics, without changing the registered selection."""
from collections import defaultdict
from datetime import datetime, timezone
import numpy as np
from prop_v5_common import *
from prop_portfolio_accounts import quantity_steps,trade_money,entry_exit_fee,SLIP
from prop_v5_campaign import inputs


def diagnose():
    trades,readers,_=inputs()
    eur=[t for t in trades if t["asset"]=="EURUSD"]
    dd=read(JOB/"eur-dd-diagnosis.json")
    totals={}
    for label,at,expected in (("peak",dd["start"],dd["reference_peak_usd"]),
                              ("trough",dd["trough"],dd["reference_trough_usd"])):
        side=dict(BUY=0,SELL=0)
        active=[]
        for t in eur:
            q=quantity_steps(t,150)
            if t["exit_msc"]<=at:
                side[t["side"]]+=int(round(trade_money(t,q,"SYM_FLAT",150)["net_usd"]*1000))
            elif t["entry_msc"]<=at:
                active.append((t,q))
        residual=int(round((expected-50000)*1000))-sum(side.values())
        if len(active)>1:raise ValueError("EUR_DD_single_position_expected")
        if active:
            t,q=active[0];sign=1 if t["side"]=="BUY" else -1
            fee=entry_exit_fee(t,t["entry_price_units"],q)
            px=t["entry_price_units"]+(residual+fee+q*20)/(sign*q*10)
            raw=readers["EURUSD"].hour(at//HOUR*HOUR)
            chosen=raw[raw["t"]==at];field="b" if sign==1 else "a"
            if not len(chosen) or not any(abs(int(v)-px)<1e-8 for v in chosen[field]):
                raise ValueError("DD_snapshot_quote_not_observed")
            side[t["side"]]+=residual
        if sum(side.values())!=int(round((expected-50000)*1000)):
            raise ValueError("DD_side_snapshot_bridge")
        totals[label]={s:v/150000 for s,v in side.items()}
    delta={s:totals["peak"][s]-totals["trough"][s] for s in ("BUY","SELL")}
    if abs(sum(delta.values())-dd["max_DD_R"])>1e-7:
        raise ValueError("DD_side_delta_bridge")
    london=[]
    for t in eur:
        day=t["entry_msc"]//DAY*DAY;mark=day+12*HOUR
        if t["entry_msc"]>=mark or t["exit_msc"]<=mark:continue
        p=readers["EURUSD"].endpoint(mark)
        if p is None:raise ValueError("London_diagnostic_quote_unknown")
        earlier=dict(t,exit_msc=p[0],exit_price_units=p[1 if t["side"]=="BUY" else 2])
        q=quantity_steps(t,150)
        net0=trade_money(earlier,q,"SYM_FLAT",150)["net_R"]
        net1=trade_money(t,q,"SYM_FLAT",150)["net_R"]
        london.append(dict(day=t["day"],side=t["side"],net_at12_R=net0,
                           actual_net_R=net1,change_after12_R=net1-net0))
    years={}
    for y in (2022,2023):
        rows=[r for r in london if r["day"].startswith(str(y))]
        years[str(y)]=dict(held_at12=len(rows),net_at12_R=sum(r["net_at12_R"] for r in rows),
                          actual_net_R=sum(r["actual_net_R"] for r in rows),
                          change_after12_R=sum(r["change_after12_R"] for r in rows))
    cash=50000000;recovery=None
    for t in eur:
        q=quantity_steps(t,150);fee=entry_exit_fee(t,t["entry_price_units"],q)
        cash-=fee
        if t["exit_msc"]>dd["trough"]:
            ticks,_=readers["EURUSD"].path(t["entry_msc"],t["exit_msc"])
            px=ticks["b"] if t["side"]=="BUY" else ticks["a"]
            equity=cash+(1 if t["side"]=="BUY" else -1)*q*10*(px.astype("int64")-t["entry_price_units"])-q*20
            hit=np.flatnonzero((ticks["t"]>dd["trough"])&(equity>=int(round(dd["reference_peak_usd"]*1000))))
            if len(hit) and recovery is None:recovery=int(ticks["t"][int(hit[0])])
        cash+=int(round(trade_money(t,q,"SYM_FLAT",150)["net_usd"]*1000))+fee
        if t["exit_msc"]>dd["trough"] and cash>=int(round(dd["reference_peak_usd"]*1000)) and recovery is None:
            recovery=t["exit_msc"]
    write_json(JOB/"eur-dd-boundary-and-london-diagnostic.json",dict(
        snapshots=totals,drawdown_contribution_R=delta,
        london_by_year=years,observations=london,
        registered_exit_changed=False,extra_variant_trials=0,
        selection_not_changed=True,prices2024_2026_used=False,
        exact_tick_recovery_time=recovery,recovery_checked_until=END,
        caution="Mark at12 applies only to original positions still open then; not a full early-exit strategy or causal proof"))
    books=read(JOB/"mechanism-eur-books.json")
    continuous=[b for b in books if b["start_msc"]==START and b["end_msc"]==END]
    years={}
    for book in continuous:
        annual={}
        for year in (2022,2023):
            annual[str(year)]=sum(
                c["net_usd"]/150 for c in book["closed"]
                if stamp(f"{year}-01-01")<=c["at"]<stamp(f"{year+1}-01-01"))
        if abs(sum(annual.values())-book["net_R"])>1e-7:
            raise ValueError("continuous_annual_cash_bridge")
        years[book["mechanism"]]=annual
    # Annual standalone diagnostic books initialize a fresh sleeve state. The
    # continuous cuts are the registered interpretation for a carried D2 state.
    failed={m:[y for y in ("2022","2023") if years[m][y]<.8*years["PARENT"][y]]
            for m in ("D1","D2")}
    if not all(failed.values()):
        raise ValueError("continuous_year_cut_requires_selection_reaudit")
    write_json(JOB/"continuous-selection-recheck.json",dict(
        annual_reference_net_R=years,failed_year_velocity_gates=failed,
        selected_unchanged="PARENT",uses2024=False,
        deviation="Standalone annual producer diagnostics initialize cold state; continuous cuts independently recheck registered year-carry interpretation. Both trials still fail, no policy or trial change."))


if __name__=="__main__":diagnose()

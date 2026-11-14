"""Byte-level CSV and separate arithmetic review of V3 source/selection."""
from collections import Counter
from datetime import datetime, timezone
from fractions import Fraction as F
from pathlib import Path

from prop_campaign_source import Prices
from prop_campaign_review import oracle
from xau_h1_execution_review import funding
from prop_portfolio_common import (
    ROOT, JOB, V1, MODELS, END, FINAL, HOUR, DAY,
    read, write_json, digest, event,
)


def raw_ticks():
    manifest=read(JOB/"eur-native-dev-v1/manifest.json")
    manifest.update(read(JOB/"eur-native-validation-v1/manifest.json"))
    prices=Prices(manifest,FINAL)
    config=read(ROOT/"eurusd-b0-20261113/config-attempt-1.json")
    checked=0;visited=set();sources=[]
    for source in config["sources"]:
        if source["first_day"] not in ("20220101","20230101","20240101"):continue
        if digest(source["path"])!=source["sha256"]:
            raise ValueError("raw_EUR_source_changed")
        wanted={
            datetime.fromtimestamp(at/1000,timezone.utc).strftime("%Y%m%d %H").encode():at
            for at in prices.files if source["first_day"][:4]==
            datetime.fromtimestamp(at/1000,timezone.utc).strftime("%Y")
        }
        current=None;expected=None;cursor=0;count=0
        with Path(source["path"]).open("rb") as stream:
            stream.readline()
            for line in stream:
                prefix=line[:11];at=wanted.get(prefix)
                if at is None:continue
                if at!=current:
                    if expected is not None and cursor!=len(expected):
                        raise ValueError("raw_tick_hour_missing_rows")
                    current=at;expected=prices.hour(at);cursor=0;visited.add(at)
                columns=line.rstrip().split(b",")
                stamp=columns[0]
                actual=(at+int(stamp[12:14])*60000+
                        int(stamp[15:17])*1000+int(stamp[18:21]))
                bid=int(columns[1].replace(b".",b""))
                ask=int(columns[2].replace(b".",b""))
                if (cursor>=len(expected) or int(expected[cursor]["t"])!=actual
                        or int(expected[cursor]["b"])!=bid or int(expected[cursor]["a"])!=ask):
                    raise ValueError("raw_tick_byte_bridge")
                cursor+=1;checked+=1;count+=1
                if checked%2000000==0:
                    event("EUR_raw_tick_oracle",checked=checked)
        if expected is not None and cursor!=len(expected):
            raise ValueError("raw_tick_last_hour_count")
        sources.append(dict(year=source["first_day"][:4],ticks=count,
                            raw_sha256=source["sha256"]))
    for at in set(prices.files)-visited:
        if len(prices.hour(at)):
            raise ValueError("unobserved_hour_contains_invented_ticks")
    result=dict(status="PASS",ticks=checked,hours=len(prices.files),
                sources=sources,method="stdlib byte slices against every stored paired tick",
                same_ms_order_verified=True,prices2025_2026_read=False)
    write_json(JOB/"source-parity.json",result)
    event("EUR_raw_tick_oracle_passed",ticks=checked,hours=len(prices.files))


def stage1():
    atlas=read(JOB/"natural-atlas.json")
    bridges=0
    for cell in atlas["cells"]:
        packet=read(JOB/f"natural-{cell['cell']['id']}.json")
        totals={m:0. for m in MODELS}
        for t in packet["records"]:
            if t["status"]!="FILLED":continue
            asset=t["asset"];q=t["quantity"];unit=t["unit"]
            scale=1000 if asset in ("XAUUSD","US500") else 100000
            p0=F(t["entry_price_units"],scale);px=F(t["exit_price_units"],scale)
            gross=(1 if t["side"]=="BUY" else -1)*(px-p0)*q*unit
            weight=sum(m for _,m in funding(t["entry_msc"],t["exit_msc"]))
            for model in MODELS:
                if asset=="XAUUSD":
                    fee=(p0+px)*q*F(7,1000000);slip=F(2,5)*q
                    rate=F(-2,5) if model.startswith("SYM") else (
                        F(-9,20) if t["side"]=="BUY" else F(-1,20))
                    carry=rate*q*weight
                elif asset=="US500":
                    fee=F(q);slip=F(3,2)*q
                    carry=-2*q*(t["exit_msc"]//DAY-t["entry_msc"]//DAY)
                else:
                    fee=F(5,100000)*q*unit;slip=F(4,100000)*q*unit
                    carry=F(-4,10000)*q*unit*weight
                value=float((gross-fee-slip+carry)/150)
                if abs(value-t["net_R"][model])>1e-8:
                    raise ValueError("M1_conditional_cost_fraction")
                totals[model]+=value;bridges+=1
        for model,total in totals.items():
            if abs(total-cell["models"][model]["total_net_R"])>1e-7:
                raise ValueError("cell_curve_total_bridge")
    decision=read(JOB/"final-satellite-decision.json")
    if decision["selected"]!=["EURUSD.SWEEP.ASIA.LONDON.DAY"] or decision["reasons"]:
        raise ValueError("frozen_satellite_verdict")
    for model,book in decision["comparison"].items():
        a,b=book["sleeve"]["net_R"].values()
        if not (a>=0 and b>=0 and a+b>=8 and book["correlation"]<.25):
            raise ValueError("satellite_gate_arithmetic")
        p=book["portfolio_half_budget"];c=book["core"]
        if p["total_net_R"]/p["max_R_DD"]<=c["total_net_R"]/c["max_R_DD"]:
            raise ValueError("marginal_gate_arithmetic")
    write_json(JOB/"stage1-parity.json",dict(
        status="PASS",cells=len(atlas["cells"]),cost_bridges=bridges,
        source_conditional_not_promoted=True,satellite_gate_rechecked=True))
    event("natural_atlas_fraction_passed",cells=112,cost_bridges=bridges)


def regime():
    days=read(JOB/"d1-dev-source.json")["days"]
    checked=0;costs_checked=0
    for model in MODELS:
        trades=read(JOB/f"regime-{model}-dev-trades.json")
        for t in trades:
            past=[d for d in days if d["minutes"]>=1200 and d["day"]+DAY<=t["decision_msc"]]
            last=past[-1];now=sum(d["close"] for d in past[-50:])/50
            before=sum(d["close"] for d in past[-55:-5])/50
            direction="BUY" if last["close"]>now>before else "SELL" if last["close"]<now<before else "NEUTRAL"
            expected=1 if direction in ("NEUTRAL",t["side"]) else .5
            if expected!=t["regime_weight"] or t["regime_known_at"]>t["decision_msc"]:
                raise ValueError("D1_causal_prefix_oracle")
            checked+=1
        reader=Prices(read(V1/"gold-dev-manifest-v2.json"))
        for book in read(JOB/"regime-comparison.json")[model]:
            value=oracle(trades,book["accepted"],[],[],reader,
                         book["start_msc"],book["end_msc"],model)
            for name,field in (("dd","peak_dd_pct"),("daily","worst_daily_loss_pct"),
                               ("static","static_loss_pct")):
                if abs(value[name]-book[field]*500000)>1e-6:
                    raise ValueError("regime_path_parity:"+field)
            if abs(value["cash"]/1000-book["balance_usd"])>1e-7:
                raise ValueError("regime_cash_parity")
            costs_checked+=len(book["closed"])
    write_json(JOB/"regime-parity.json",dict(
        status="PASS",causal_decisions=checked,books=12,closed_positions=costs_checked))
    event("D1_regime_oracle_passed",books=12,decisions=checked)


if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("stage",choices=("raw_ticks","stage1","regime"))
    globals()[parser.parse_args().stage]()

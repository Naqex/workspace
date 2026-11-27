"""One causal daily-flat rule over the unchanged A entry/SL tape."""
from collections import Counter
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
import numpy as np
from prop_v16_common import *
from prop_v15_evidence import bars_for
from prop_v15_paths import insert_excursions,patch_plan
from prop_v14_paths import build
from quant_core.gap_aware_execution import GapAwarePathIndex
from quant_core.ftmo_execution_and_calendar import SessionSchedule,gold_calendar
from quant_core.prop_lifecycle_and_parity import bindings
from prop_v14_paths import M1ScenarioQuotes
from prop_v15_paths import bind_quotes

DAY=86400000
HOUR=3600000


class CausalFlatSchedule(SessionSchedule):
    version="V16_EX_ANTE_DAILY_2030_AND_REGISTERED_EARLY_GUARDS"

    def cutoff(self,entry,asset):
        day=entry//DAY*DAY;flat=day+73800000
        date=datetime.fromtimestamp(entry/1000,timezone.utc)
        row=self.events.get(date.date().isoformat(),{})
        if row.get("flat_utc"):
            h,m=map(int,row["flat_utc"].split(":"));flat=min(flat,day+(h*60+m)*60000)
        if asset=="US500":
            local=date.astimezone(self.ny).replace(hour=16,minute=0,second=0,microsecond=0)
            flat=min(flat,int(local.timestamp()*1000))
        return flat

    def target(self,entry,deadline,asset):
        return min(int(deadline),self.cutoff(int(entry),asset))

    def off_kind(self,at,asset):
        if asset=="US500":
            local=datetime.fromtimestamp(at/1000,timezone.utc).astimezone(self.ny)
            minute=local.hour*60+local.minute
            if local.weekday()==5 or local.weekday()==4 and minute>=975 or local.weekday()==6 and minute<1080:
                return "WEEKEND"
            if 975<=minute<1080:return "DAILY_BREAK"
        return super().off_kind(at,asset)


def core_inputs(dev):
    end=DEV_END if dev else END
    cfg=read(V14/"candidate-freeze.json")
    original=[t for t in read(V14/"OLHC-strategy-trades.json") if
        t["id"] in cfg["candidate_A"] and t["decision_msc"]<end]
    bars={a:bars_for(a,dev) for a in ("XAUUSD","EURUSD")}
    schedule=CausalFlatSchedule(gold_calendar(FIRST,end).events.values())
    measurements={};lookup={};skipped=[]
    for identity in cfg["candidate_A"]:
        selected=[]
        for t in original:
            if t["id"]!=identity:continue
            if t["entry_msc"]>=schedule.cutoff(t["entry_msc"],t["asset"]):
                skipped.append(dict(id=t["id"],event=t["source_event"],reason="KNOWN_DAILY_CUTOFF",entry=t["entry_msc"]))
            else:selected.append(t)
        selected.sort(key=lambda t:t["decision_msc"]);lookup[identity]=selected
        asset=identity.split("|")[0]
        m={name:np.array([t[field] for t in selected],dtype="int64") for name,field in (
            ("at","decision_msc"),("entry_at","entry_msc"),("entry_price","entry_price_units"),
            ("stop","stop_units"),("deadline","deadline_msc"))}
        m["deadline"]=np.array([schedule.target(int(e),int(d),asset) for e,d in zip(
            m["entry_at"],m["deadline"])],dtype="int64")
        m.update(side=np.array([1 if t["side"]=="BUY" else -1 for t in selected],dtype="int8"),
            natural=np.array([t["natural"] for t in selected]),admitted=np.ones(len(selected),dtype=bool),
            asset=asset,_index=GapAwarePathIndex(bars[asset],asset=asset,schedule=schedule))
        measurements[identity]=m
    return original,bars,schedule,measurements,lookup,skipped


def make(tag,dev,strict=False):
    stage="Dev" if dev else "Full";mode="STRICT" if strict else "PRIMARY"
    end=DEV_END if dev else END
    original,bars,schedule,ms,lookup,skipped=core_inputs(dev)
    order="OPEN_LOW_HIGH_CLOSE" if tag=="OLHC" else "OPEN_HIGH_LOW_CLOSE"
    plan=[]
    if strict:
        primary=read(JOB/f"{stage}-{tag}-PRIMARY-trades.json")
        for asset,index in ((a,GapAwarePathIndex(b,asset=a,schedule=schedule)) for a,b in bars.items()):
            for t in primary:
                if t["asset"]!=asset:continue
                for g in index.gaps:
                    if not g["source_uncertain"] or not (g["after"]>t["entry_msc"] and g["before"]<t["exit_msc"]):
                        continue
                    at=next(v for v in range(g["before"]+60000,g["after"],60000)
                        if schedule.off_kind(v,asset) is None)
                    level=t["protection_price"] if t["activation_time"] is not None and t["activation_time"]<=at else t["stop_units"]
                    plan.append(dict(asset=asset,id=t["id"],entry=t["entry_msc"],exit=t["exit_msc"],
                        side=1 if t["side"]=="BUY" else -1,level=level,before=g["before"],after=g["after"],
                        source_uncertain=True,first_unknown=at,screen=dict(status="AMBIGUOUS")))
        plan=patch_plan(plan,"ALL_UNCERTIFIED")
        bars={a:insert_excursions(b,plan,a,end)[0] for a,b in bars.items()}
        for m in ms.values():m["_index"]=GapAwarePathIndex(bars[m["asset"]],asset=m["asset"],schedule=schedule)
    import prop_v14_paths as parent
    with bindings(parent,END=end):trades,readers,missing=build(ms,order,bars)
    if missing:raise ValueError("V16_A_entry_or_path_unresolved:"+str(missing[:3]))
    primary={(t["id"],t["source_event"]):t for t in read(JOB/f"{stage}-{tag}-PRIMARY-trades.json")} if strict else {}
    for t in trades:
        old=lookup[t["id"]][t["source_event"]]
        scenario=t["source_uncertain"]
        before=primary[t["id"],t["source_event"]]["source_uncertain"] if strict else scenario
        t.update(parent_source_event=old["source_event"],parent_deadline=old["deadline_msc"],
            V15_source_uncertain=old["source_uncertain"],original_source_uncertain=before,
            scenario_remaining_source_gaps=scenario,source_uncertain=before or scenario,
            ex_ante_cutoff=schedule.cutoff(t["entry_msc"],t["asset"]),
            synthetic_bridge_stress=strict,broker_certified=False)
    save(f"{stage}-{tag}-{mode}-trades.json",trades)
    save(f"{stage}-{tag}-{mode}-path-receipt.json",dict(signals=len(trades),parent_signals=len(original),
        skipped=skipped,entry_exits_overnight=sum(t["exit_msc"]//DAY!=t["entry_msc"]//DAY for t in trades),
        source_uncertain=sum(t["source_uncertain"] for t in trades),synthetic_patches=plan,
        exits=dict(Counter(t["reason"] for t in trades)),source_coverage_certificate=False,
        policy=schedule.version,known_calendar_only=True,last_quote_before_unknown_outage_used=False))
    event("V16_A_paths",scope=stage,order=tag,mode=mode,signals=len(trades),
        unknown=sum(t["source_uncertain"] for t in trades),patches=len(plan))
    return trades,readers,bars


def load(tag,dev,strict=False):
    stage="Dev" if dev else "Full";mode="STRICT" if strict else "PRIMARY"
    end=DEV_END if dev else END
    trades=read(JOB/f"{stage}-{tag}-{mode}-trades.json")
    receipt=read(JOB/f"{stage}-{tag}-{mode}-path-receipt.json")
    bars={a:bars_for(a,dev) for a in ("XAUUSD","EURUSD")}
    if strict:
        bars={a:insert_excursions(b,receipt["synthetic_patches"],a,end)[0] for a,b in bars.items()}
    order="OPEN_LOW_HIGH_CLOSE" if tag=="OLHC" else "OPEN_HIGH_LOW_CLOSE"
    readers={a:M1ScenarioQuotes(b,order,FIRST,end) for a,b in bars.items()}
    ids=read(V14/"candidate-freeze.json")["candidate_A"]
    # build() inserts crossings in mechanism/event order before sorting trades.
    for t in sorted(trades,key=lambda t:(ids.index(t["id"]),t["source_event"])):
        if t["censored"]:continue
        spread=338 if t["asset"]=="XAUUSD" else 10
        bid=t["exit_price_units"] if t["side"]=="BUY" else t["exit_price_units"]-spread
        readers[t["asset"]].add(t["exit_msc"],bid,bid+spread)
    original=[(t["entry_quote_index"],t["exit_quote_index"]) for t in trades]
    bind_quotes(trades,readers)
    if original!=[(t["entry_quote_index"],t["exit_quote_index"]) for t in trades]:
        raise ValueError("V16_saved_quote_ordinal_drift")
    return trades,readers,bars


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("tag",choices=("OLHC","OHLC"))
    p.add_argument("--full",action="store_true");p.add_argument("--strict",action="store_true")
    a=p.parse_args();make(a.tag,not a.full,a.strict)

"""Frozen signal continuation, M1 scenario ledgers, reused FTMO lifecycle."""
from collections import Counter
from pathlib import Path
import json
import time
import numpy as np
from prop_v14_source import JOB,V13,FIRST,DEV_END,END,SEED,read,save,sha
from prop_v14_campaign import DECISION
from prop_v14_paths import build
from prop_v14_accounts import replay_accounts
from quant_core.market_data_store import BAR
from quant_core.ftmo_execution_and_calendar import execution_schedule,gold_calendar
from quant_core.gap_aware_execution import GapAwarePathIndex
from quant_core.prop_lifecycle_and_parity import bindings
from quant_core.vectorized_stage0_scanner import measure


def inputs():
    cfg=read(DECISION)
    release=read(JOB/"longitudinal-release.json")
    import subprocess
    if json.loads(subprocess.check_output(["git","show",release["commit"]+":"+DECISION.as_posix()]))!=cfg:
        raise ValueError("V14_composition_drift")
    for p,digest in cfg["pins"].items():
        if sha(p)!=digest:raise ValueError("V14_code_drift:"+p)
    sources=read(JOB/"full-source-admission.json")["assets"]
    chosen=list(dict.fromkeys(cfg["candidate_A"]+cfg["candidate_B"]))
    calendar=gold_calendar(FIRST,END)
    measurements={};bars_by_asset={}
    import prop_v10_signals as s
    from prop_v12_signals import rejection_recipes
    old_rows={r["id"]:r for r in read(V13/"discovery.json")["rows"]}
    for asset,proof in sources.items():
        if sha(proof["path"])!=proof["sha256"]:raise ValueError("V14_full_source_drift")
        bars=np.memmap(proof["path"],mode="r",dtype=BAR);bars_by_asset[asset]=bars
        index=GapAwarePathIndex(bars,asset=asset,schedule=execution_schedule(FIRST,END))
        wanted=[identity.split("|")[1] for identity in chosen if identity.startswith(asset+"|")]
        catalog=[c for c in s.catalog(asset) if c["id"] in wanted]
        # Same generator/features; compute only registered F1–F4 recipe configs.
        with bindings(s,catalog=lambda _:catalog):
            raw=s.recipes(bars,asset,DEV_END,END,calendar)
        if any(r.startswith("F5") for r in wanted):
            raw += [r for r in rejection_recipes(bars,asset,DEV_END,END,calendar) if r["id"] in wanted]
        old=np.load(JOB/f"{asset}-Dev-paths.npz")
        for identity in chosen:
            if not identity.startswith(asset+"|"):continue
            recipe,horizon,mode=identity.split("|")[1:]
            row=old_rows[identity];j=row["source_cell"]
            new_recipe=next(r for r in raw if r["id"]==recipe)
            new=next(m for m in measure(asset,new_recipe,bars,calendar,DEV_END,END) if m["horizon"]==horizon)
            fields=("at","entry_at","side","entry_price","stop","natural","friction","ratio","years","deadline","admitted")
            m={}
            for field in fields:
                value=new[field]
                # Path completeness is separate from pre-entry cost admission.
                if field=="admitted":value=new["ratio"]<=.15
                m[field]=np.concatenate([old[f"{j}:{field}"],value])
            m.update(asset=asset,recipe=recipe,horizon=horizon,family=row["family"],_index=index)
            measurements[identity]=m
    return cfg,measurements,bars_by_asset,calendar


def run(order):
    started=time.perf_counter()
    cfg,measurements,bars,calendar=inputs()
    trades,readers,missing=build(measurements,order,bars)
    tag="OLHC" if order=="OPEN_LOW_HIGH_CLOSE" else "OHLC"
    save(f"{tag}-strategy-trades.json",trades)
    save(f"{tag}-path-coverage.json",dict(missing=missing,trades=len(trades),
        source_uncertain=sum(t["source_uncertain"] for t in trades),
        right_censored=sum(t["censored"] for t in trades),order=order))
    summaries=[]
    for candidate,ids in (("A",cfg["candidate_A"]),("B",cfg["candidate_B"])):
        for view in ("NEXT_QUOTE","CLEAN_COHORT"):
            selected=[t for t in trades if t["id"] in ids and
                      (view=="NEXT_QUOTE" or not t["source_uncertain"])]
            # Readers already contain matching source ordinals for the superset;
            # omitted signal events do not remove price observations.
            print(dict(stage="V14_lifecycle_begin",order=tag,candidate=candidate,view=view,
                       signals=len(selected),ex_post_filter=view=="CLEAN_COHORT"),flush=True)
            rows=replay_accounts(selected,readers,calendar,FIRST,END)
            save(f"{tag}-{candidate}-{view}-accounts.json",rows)
            for t in selected:
                y=int(np.datetime64(t["decision_msc"],"ms").astype("datetime64[Y]").astype(int)+1970)
                for model in ("SYM","ASYM"):
                    summaries.append(dict(order=tag,candidate=candidate,view=view,year=y,id=t["id"],
                        side=t["side"],censored=t["censored"],source_uncertain=t["source_uncertain"],
                        net_R=t["reference"].get(model,{}).get("net_R"),model=model))
            print(dict(stage="V14_lifecycle_complete",order=tag,candidate=candidate,view=view,
                accounts=len(rows),passes=sum(len(r["phase_passes"])==2 for r in rows if r["kind"]=="CHALLENGE"),
                payouts=sum(len(r["payouts"]) for r in rows)),flush=True)
    save(f"{tag}-reference-annual-events.json",summaries)
    save(f"{tag}-timings.json",dict(seconds=time.perf_counter()-started,order=order))


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--order",choices=("OPEN_LOW_HIGH_CLOSE","OPEN_HIGH_LOW_CLOSE"),required=True)
    run(p.parse_args().order)

"""Resume only missing V14 account batches under a committed technical erratum."""
import json
import subprocess
import numpy as np
from prop_v14_source import JOB,FIRST,END,read,save,sha
from prop_v14_paths import M1ScenarioQuotes
from prop_v14_accounts import replay_accounts
from quant_core.market_data_store import BAR
from quant_core.ftmo_execution_and_calendar import gold_calendar

ERRATUM="planning/research/EVIDENCE-AND-LIFECYCLE-V14-ERRATUM-01-20261115.json"


def run(tag):
    correction=read(ERRATUM)
    committed=json.loads(subprocess.check_output(["git","show","HEAD:"+ERRATUM]))
    if correction!=committed:raise ValueError("V14_erratum_not_committed")
    cfg=read(JOB/"candidate-freeze.json")
    release=read(JOB/"longitudinal-release.json")
    original=json.loads(subprocess.check_output(["git","show",release["commit"]+
        ":planning/research/EVIDENCE-AND-LIFECYCLE-V14-FREEZE-20261115.json"]))
    if cfg!=original:raise ValueError("V14_original_freeze_changed")
    for p,digest in dict(cfg["pins"],**correction["technical_pins"]).items():
        if sha(p)!=digest:raise ValueError("V14_resume_code_drift:"+p)
    for name,digest in correction["completed_before_fix"].items():
        if sha(JOB/name)!=digest:raise ValueError("V14_completed_result_drift")
    order="OPEN_LOW_HIGH_CLOSE" if tag=="OLHC" else "OPEN_HIGH_LOW_CLOSE"
    proofs=read(JOB/"full-source-admission.json")["assets"]
    readers={}
    for asset,p in proofs.items():
        if sha(p["path"])!=p["sha256"]:raise ValueError("V14_resume_source_drift")
        readers[asset]=M1ScenarioQuotes(np.memmap(p["path"],mode="r",dtype=BAR),order,FIRST,END)
    trades=read(JOB/f"{tag}-strategy-trades.json")
    for t in trades:
        if t["censored"]:continue
        spread=338 if t["asset"]=="XAUUSD" else 10
        bid=t["exit_price_units"] if t["side"]=="BUY" else t["exit_price_units"]-spread
        readers[t["asset"]].add(t["exit_msc"],bid,bid+spread)
    calendar=gold_calendar(FIRST,END);completed=[]
    for candidate in ("A","B"):
        for view in ("NEXT_QUOTE","CLEAN_COHORT"):
            name=f"{tag}-{candidate}-{view}-accounts.json"
            if (JOB/name).exists():continue
            selected=[t for t in trades if t["id"] in cfg["candidate_"+candidate] and
                (view=="NEXT_QUOTE" or not t["source_uncertain"])]
            print(dict(stage="V14_resume_begin",name=name,signals=len(selected)),flush=True)
            rows=replay_accounts(selected,readers,calendar,FIRST,END)
            save(name,rows);completed.append(name)
            print(dict(stage="V14_resume_complete",name=name),flush=True)
    save(f"{tag}-resume-receipt.json",dict(erratum=ERRATUM,erratum_sha256=sha(ERRATUM),
        completed=completed,unchanged_prior_outputs=True,missing_batches_only=True))


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("tag",choices=("OLHC","OHLC"))
    run(p.parse_args().tag)

"""Read frozen full/later cohorts only after ISO qualification; no selection changes."""
from pathlib import Path
import numpy as np
import prop_v26_common as common
from prop_v26_common import *
from prop_v26_iso import verify
from prop_v15_evidence import bars_for
from prop_v14_paths import M1ScenarioQuotes
from quant_core.job_workspace import JobWorkspace
import prop_v24_pareto as marked

LAB=JobWorkspace(ROOT/"batch-exact-iso-v26-20261118"/"comparison",Path(__file__).resolve().parents[2])


def run():
    frozen=verify()
    save("registration.json",dict(source_sha256=sha(__file__),ISO_freeze_sha256=sha(FREEZE),
        cutoff=END,later_already_exposed=True,no_parameters_changed=True))
    bars={a:bars_for(a,False) for a in ("XAUUSD","EURUSD")}
    rows=[]
    for tag,order in (("OLHC","OPEN_LOW_HIGH_CLOSE"),("OHLC","OPEN_HIGH_LOW_CLOSE")):
        all_trades=read(V19/f"Full-{tag}-PRIMARY-trades.json")
        assert all(FIRST<=t["entry_msc"]<=t["exit_msc"]<END for t in all_trades)
        readers={a:M1ScenarioQuotes(b,order,FIRST,END) for a,b in bars.items()}
        for label,selected in (("FULL",all_trades),("LATER",[t for t in all_trades if t["entry_msc"]>=DEV_END])):
            points=marked.prepare(selected,readers)
            values={}
            for name,weights in (("BASE_GUARD",{}),("P80_ISO_EXACT",frozen["weights"])):
                value=marked.measure(selected,points,weights)
                value.pop("development_years",None)
                value["scope"]=label
                value["reference_risk_USD"]=150
                value["source_uncertain_trades"]=sum(t.get("source_uncertain",False) for t in selected)
                values[name]=value
            rows.append(dict(order=tag,cohort=label,models=values))
            event("unit_book_comparison",order=tag,cohort=label,trades=len(selected))
    compressed("unit-book-comparison",rows)
    save("unit-book-summary.json",dict(rows=rows,no_new_strategy_selection=True,cutoff=END))
    print(read(LAB.root/"unit-book-summary.json"),flush=True)


if __name__=="__main__":
    with bindings(common,JOB=LAB.root,RUNTIME=LAB):
        activate_runtime()
        run()

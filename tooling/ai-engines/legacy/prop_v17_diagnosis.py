"""Development-only admissions, reference sleeve books and a fixed two-tier rule."""
from collections import Counter
from datetime import datetime,timezone
import hashlib
import subprocess
import numpy as np
import prop_v14_review as review
import independent_ledger_auditor as oracle
from prop_v17_common import *
from prop_v16_paths import load
from prop_v15_accounts import SleeveBook,execution_bindings
from quant_core.prop_lifecycle_and_parity import simulate,bindings
from quant_core.ftmo_execution_and_calendar import gold_calendar

DAY=86400000


def parent_bindings():
    cfg=read("planning/research/GAP-IMMUNE-MULTIASSET-V16-FREEZE-20261116.json")
    rows=[]
    for path,expected in cfg["code_pins"].items():
        blob=subprocess.check_output(["git","show","0c919a5:"+Path(path).as_posix()])
        current=Path(path).read_bytes()
        canon=blob.replace(b"\r\n",b"\n")
        now=current.replace(b"\r\n",b"\n")
        extension=(path.replace("\\","/")=="tooling/ai-engines/independent_ledger_auditor.py" and now.startswith(canon))
        if canon!=now and not extension:raise ValueError("V17_parent_semantic_drift:"+path)
        forms=(blob,canon,canon.replace(b"\n",b"\r\n"))
        if expected not in {hashlib.sha256(v).hexdigest() for v in forms}:
            raise ValueError("V17_parent_pin_not_explained_by_newlines:"+path)
        rows.append(dict(path=path,original_frozen_sha256=expected,current_sha256=sha(path),
            status="APPEND_ONLY_V17_ORACLE_EXTENSION" if extension and now!=canon else
                "RAW_MATCH" if sha(path)==expected else "CHECKOUT_LINE_ENDINGS_ONLY"))
    save("V16-parent-code-binding.json",dict(passed=True,rows=rows,original_freeze_unchanged=True))
    event("V17_parent_source_binding_PASS",files=len(rows))


def admissions():
    summaries=[];details=[]
    for tag in ("OLHC","OHLC"):
        for mode in ("PRIMARY","STRICT"):
            tape=read(V16/f"Dev-{tag}-{mode}-trades.json")
            rows=read(V16/f"Dev-{tag}-{mode}-accounts.json")
            if any(t["entry_msc"]//DAY!=t["exit_msc"]//DAY for t in tape):
                raise ValueError("V17_V16_not_intraday")
            for cost in ("SYM","ASYM"):
                selected=[r for r in rows if r["cell"].startswith(cost)]
                rejected=[];shrunk_cap=0
                for book in selected:
                    closed={r["trade"]:r for r in book["closed"]}
                    for e in book["entry_audit"]:
                        if e["accepted"] or "CAP" not in e["reason"]:continue
                        t=tape[e["trade"]]
                        active=[a for a in book["accepted"] if a["at"]<e["at"] and
                            (a["trade"] not in closed or closed[a["trade"]]["at"]>e["at"])]
                        # All relevant V16 cap blockers predate this entry; retain tie ambiguity.
                        same_time=[a["trade"] for a in book["accepted"] if a["at"]==e["at"]]
                        rejected.append(dict(start=book["start_msc"],standalone=book["standalone_funded"],
                            trade=e["trade"],id=t["id"],entry=e["at"],reason=e["reason"],
                            active=[dict(trade=a["trade"],id=tape[a["trade"]]["id"],
                                entry=a["at"],deadline=tape[a["trade"]]["deadline_msc"]) for a in active],
                            same_timestamp_accepted_ids=same_time,
                            overnight_blockers=sum(tape[a["trade"]]["deadline_msc"]//DAY>
                                tape[a["trade"]]["entry_msc"]//DAY for a in active)))
                counts=Counter();[counts.update(r["rejections"]) for r in selected]
                summaries.append(dict(order=tag,mode=mode,cost=cost,accounts=len(selected),
                    cap_occurrences=len(rejected),unique_cap_signals=len({(e["id"],e["entry"]) for e in rejected}),
                    overnight_cap_blockers=sum(e["overnight_blockers"] for e in rejected),
                    partial_lot_shrink_due_to_cap=shrunk_cap,rejections=dict(counts),
                    quality_of_rejected_signals="NOT_INFERRED_FROM_SUBSEQUENT_PNL"))
                details+= [dict(order=tag,mode=mode,cost=cost,**e) for e in rejected]
    save("V16-Dev-admission-diagnosis.json",dict(summaries=summaries,cap_events=details,
        no_48h_V16_positions=True,cap_rejects_instead_of_partial_resizing=True,
        overlapping_accounts_not_independent=True))
    event("V17_admission_diagnosis_complete",summaries=summaries)


def books(tag):
    trades,readers,_=load(tag,True)
    ids=read(V14/"candidate-freeze.json")["candidate_A"]
    accounts=[SleeveBook(FIRST,DEV_END,model,sleeve_id=identity)
        for identity in ids for model in ("SYM_FLAT","ASYM_FLAT")]
    calendar=gold_calendar(FIRST,DEV_END)
    import prop_v6_replay as replay
    with execution_bindings(),bindings(replay,event=event):
        rows=simulate(trades,readers,accounts,FIRST,DEV_END,calendar)
    save(f"Dev-{tag}-sleeve-books.json",rows)
    with bindings(review,V14LedgerOracle=oracle.V15LedgerOracle):
        checked=review.audit_accounts(rows,trades,readers,calendar,FIRST,DEV_END)
    save(f"Dev-{tag}-sleeve-books-audit.json",dict(passed=True,accounts=len(checked),records=checked,
        reference_risk_usd=150,same_implementer_and_feed=True))
    event("V17_sleeve_books_audited",tag=tag,books=len(rows))


def tiers():
    ids=read(V14/"candidate-freeze.json")["candidate_A"];scores=[]
    for identity in ids:
        cases=[]
        for tag in ("OLHC","OHLC"):
            if not read(JOB/f"Dev-{tag}-sleeve-books-audit.json")["passed"]:raise ValueError("V17_book_audit_missing")
            for r in read(JOB/f"Dev-{tag}-sleeve-books.json"):
                if r["sleeve_id"]!=identity:continue
                dd=r["max_equity_R_DD"];annual=r["net_usd"]/150/6
                cases.append(dict(order=tag,cost=r["cell"][:4],trades=r["closed_trades"],
                    annual_reference_R=annual,floating_R_DD=dd,
                    annual_R_over_DD=annual/dd if dd and dd>0 else None,
                    rejections=r["rejections"]))
        values=[c["annual_R_over_DD"] for c in cases]
        scores.append(dict(id=identity,cases=cases,worst_score=min(values) if all(v is not None for v in values) else None))
    ranked=sorted([r for r in scores if r["worst_score"] is not None and r["worst_score"]>0],
        key=lambda r:(-r["worst_score"],r["id"]))
    core=ranked[0]["id"] if ranked else sorted(ids)[0]
    weights={i:1. if i==core else .6 for i in ids}
    save("tier-selection.json",dict(tiers=weights,core=core,scores=scores,
        rank_inconclusive=not bool(ranked),selection_uses_only_2018_2023=True,
        annual_R_over_DD_not_CAGR=True,variants=1,no_equal_weight_outcome_selection=True))
    event("V17_tiers_frozen_pending_selection",core=core,tiers=weights)


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("stage",choices=("parent_bindings","admissions","books","tiers"))
    p.add_argument("--tag",choices=("OLHC","OHLC"),default="OLHC")
    a=p.parse_args();books(a.tag) if a.stage=="books" else globals()[a.stage]()

"""Resume frozen common draws in disjoint owned chunks; retain original partial journals."""
from concurrent.futures import ThreadPoolExecutor,as_completed
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import numpy as np
import prop_v26_common as common
from prop_v26_common import *
from prop_v26_campaign import Tape
from prop_v26_iso import verify
from prop_v19_accounts import V19Account
from prop_v19_stress import FastV19Oracle,summarize
from prop_v18_bootstrap import draw_plan,sequence_for,MC_END,YEAR
from prop_v18_costs import cost_bindings
from quant_core.job_workspace import JobWorkspace
from quant_core.native_paths import io_path
import prop_v18_audit as auditor

CARD=PROTOCOL.with_name("V26-REPLAY-CHUNKS-20261118.json")
BASE=ROOT/"batch-exact-iso-v26-20261118"
WORKSPACE=Path(__file__).resolve().parents[2]
CONTROL=JobWorkspace(BASE/"replay-control",WORKSPACE)


def prefix(root,tag):
    path=root/f"MC-{tag}-paths.jsonl"
    rows=[]
    for i,line in enumerate(path.read_text(encoding="utf-8").splitlines()):
        try:row=json.loads(line)
        except json.JSONDecodeError:
            raise ValueError("PARTIAL_JOURNAL_TAIL_REQUIRES_RECONCILIATION") from None
        if row["path"]!=i:raise ValueError("PARTIAL_JOURNAL_INDEX")
        rows.append(row)
    return path,rows


def register():
    original={"OLHC":common.JOB,
              "OHLC":JobWorkspace(BASE/"monte-OHLC",WORKSPACE).root}
    roots={};ranges=[]
    for tag,root in original.items():
        path,rows=prefix(root,tag)
        roots[tag]=dict(root=str(root),journal_sha256=sha(path),completed_prefix=len(rows),
                        first_native_hashes=rows[0]["native_ledger_sha256"])
        for start in range(len(rows),5000,400):
            ranges.append(dict(tag=tag,first=start,end=min(5000,start+400)))
    value=dict(schema="V26-replay-chunks-v1",sources={str(p):sha(p) for p in
        (Path(__file__),Path("tooling/ai-engines/prop_v19_stress.py"),
         Path("tooling/ai-engines/prop_v19_accounts.py"))},
        ISO_freeze_sha256=sha(FREEZE),original=roots,ranges=ranges,workers=4,
        draw_count=5000,ordering_count=2,same_draw_indices=True,
        strategy_or_native_account_semantics_changed=False,
        reason="reuse existing scalar oracle after full-ledger parity; isolated remaining ranges")
    with CARD.open("x",encoding="utf-8") as out:json.dump(value,out,indent=2)
    print(dict(prefixes={k:v["completed_prefix"] for k,v in roots.items()},chunks=len(ranges)))


def verify_card():
    verify()
    card=read(CARD)
    if card!=json.loads(subprocess.check_output(["git","show","HEAD:"+CARD.as_posix()])):
        raise ValueError("CHUNK_CARD_MUST_BE_COMMITTED")
    for p,digest in card["sources"].items():
        if sha(p)!=digest:raise ValueError("CHUNK_SOURCE_CHANGED")
    if sha(FREEZE)!=card["ISO_freeze_sha256"]:raise ValueError("ISO_FREEZE_CHANGED")
    return card


def replay(tape,draws,index):
    sequence=sequence_for(tape,draws[index])
    books=[V19Account(FIRST,MC_END,"SYM_FLAT",rolling=True,standalone=f,profile=tape.profile,
                     friction_pct=100) for f in (False,True)]
    for slot,(block,shift) in enumerate(sequence):tape.walk(block,shift,slot,books)
    native=[book.dump() for book in books]
    with bindings(auditor,FrictionOracle=FastV19Oracle):
        checks=[auditor.audit_path(tape,sequence,row) for row in native]
    c,f=native;passes={p["phase"]:p["at"] for p in c["phase_passes"]}
    return dict(path=index,phase1=passes.get(1,-1),both=passes.get(2,-1),breach=c["first_breach"],
        funded_breach=f["first_breach"],daily=c["worst_daily_loss_pct"],static=c["static_loss_pct"],
        funded_payout_years=[sum(p["trader_usd"] for p in f["payouts"] if FIRST+y*YEAR<=p["at"]<FIRST+(y+1)*YEAR)
                            for y in range(3)],post_challenge_payout_USD=c["trader_payout_usd"],
        independent_full_ledger_checks=checks,
        native_ledger_sha256=[hashlib.sha256(json.dumps(n,sort_keys=True).encode()).hexdigest() for n in native])


def worker(tag,first,end):
    card=verify_card()
    if dict(tag=tag,first=first,end=end) not in card["ranges"]:raise ValueError("UNREGISTERED_CHUNK")
    runtime=JobWorkspace(BASE/f"chunk-{tag}-{first:04}-{end:04}",WORKSPACE)
    with bindings(common,JOB=runtime.root,RUNTIME=runtime):
        activate_runtime()
        tape=Tape(tag,"PRIMARY");draws=draw_plan(tape)
        from prop_v18_common import JOB as V18
        if not np.array_equal(draws,np.load(V18/"bootstrap-common-draws.npy")):
            raise ValueError("COMMON_DRAWS_CHANGED")
        with cost_bindings(100):
            control=replay(tape,draws,0)
            if control["native_ledger_sha256"]!=card["original"][tag]["first_native_hashes"]:
                raise ValueError("NATIVE_LEDGER_DIFFERS_FROM_ORIGINAL_PREFIX")
            path=runtime.root/"paths.jsonl"
            rows=[json.loads(s) for s in path.read_text().splitlines()] if path.exists() else []
            if [r["path"] for r in rows]!=list(range(first,first+len(rows))):
                raise ValueError("CHUNK_RESUME_INDEX")
            started=time.perf_counter()
            with io_path(path).open("a",encoding="utf-8") as out:
                for index in range(first+len(rows),end):
                    row=replay(tape,draws,index)
                    out.write(json.dumps(row)+"\n");out.flush();rows.append(row)
                    if (index-first+1)%100==0:event("chunk_progress",tag=tag,first=first,done=len(rows),total=end-first)
        compressed("paths",rows)
        save("complete.json",dict(first=first,end=end,tag=tag,paths=len(rows),seconds=time.perf_counter()-started,
            journal_sha256=sha(path),native_prefix_control_equal=True,full_ledger_audit=True))


def dispatch():
    card=verify_card()
    with bindings(common,JOB=CONTROL.root,RUNTIME=CONTROL):
        activate_runtime()
        python=Path(sys.executable)
        def run(row):
            output=CONTROL.root/f"{row['tag']}-{row['first']}-{row['end']}.stdout"
            args=[str(python),str(Path(__file__).resolve()),"--worker",row["tag"],str(row["first"]),str(row["end"])]
            with output.open("x",encoding="utf-8") as stream:
                result=subprocess.run(args,stdout=stream,stderr=subprocess.STDOUT,timeout=3600,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name=="nt" else 0)
            if result.returncode:raise ValueError("CHUNK_FAILED:"+output.name)
            return row
        with ThreadPoolExecutor(max_workers=card["workers"]) as pool:
            pending=[pool.submit(run,row) for row in card["ranges"]]
            for done,future in enumerate(as_completed(pending),1):
                event("chunk_completed",done=done,total=len(pending),**future.result())
        save("dispatch-complete.json",dict(chunks=len(pending),workers=card["workers"]))


def aggregate():
    card=verify_card()
    for tag,value in card["original"].items():
        root=Path(value["root"]);path,rows=prefix(root,tag)
        assert sha(path)==value["journal_sha256"] and len(rows)==value["completed_prefix"]
        for chunk in (r for r in card["ranges"] if r["tag"]==tag):
            folder=JobWorkspace(BASE/f"chunk-{tag}-{chunk['first']:04}-{chunk['end']:04}",WORKSPACE).root
            proof=read(folder/"complete.json")
            assert proof["paths"]==chunk["end"]-chunk["first"]
            rows+=unpack("paths",folder)
        rows.sort(key=lambda r:r["path"])
        assert [r["path"] for r in rows]==list(range(5000))
        runtime=common.RUNTIME if tag=="OLHC" else JobWorkspace(BASE/"monte-OHLC",WORKSPACE)
        with bindings(common,JOB=root,RUNTIME=runtime):
            activate_runtime()
            compressed(f"MC-{tag}-paths",rows)
            save(f"MC-{tag}-summary.json",dict(**summarize(rows),order=tag,mode="PRIMARY",friction=100,
                accounts_fully_audited=10000,worst_daily=max(r["daily"] for r in rows),
                worst_static=max(r["static"] for r in rows),
                mean_post_challenge_payout_USD_per_elapsed_year=float(np.mean([r["post_challenge_payout_USD"] for r in rows]))/3,
                chunk_card_sha256=sha(CARD),original_prefix_preserved=True))
            runtime.close()


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--register",action="store_true")
    p.add_argument("--worker",nargs=3)
    p.add_argument("--aggregate",action="store_true")
    args=p.parse_args()
    if args.register:register()
    elif args.worker:worker(args.worker[0],int(args.worker[1]),int(args.worker[2]))
    elif args.aggregate:aggregate()
    else:dispatch()

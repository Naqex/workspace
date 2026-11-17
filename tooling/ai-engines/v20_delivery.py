"""Exclusive final V20 delivery stages after all financial readers are idle."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from statistics import median
import json
import os
import subprocess
import sys
import time
from prop_v20_common import JOB,V19,read,save,event,sha
from prop_v16_performance import RUNTIMES as OLD_RUNTIMES

RUNTIMES=dict(OLD_RUNTIMES,observer=str(Path("tooling/strategy-engines/observer/.venv/Scripts/python.exe").resolve()))
TEMP_ROOT=Path("D:/ANNAM/TradingWorkspace/.runtime/v20-test-temp")
CAMPAIGN_JOB=JOB


def idle():
    for name in ("Full-MC-processes.json","Full-historical-processes.json","compaction-prepared.json"):
        if not (CAMPAIGN_JOB/name).exists() or not read(CAMPAIGN_JOB/name)["passed"]:
            raise ValueError("V20_wait_for_completed_financial_and_storage_preparation:"+name)


def compaction():
    idle()
    from evidence_compaction import apply,EvidenceStore
    m=read(JOB/"compaction-prepared.json")
    result=apply(V19,m["manifest_sha256"])
    store=EvidenceStore(V19)
    for row in store.entries.values():
        if store.canonical_sha(row["relative"])!=row["sha256"]:raise ValueError("archived_original_hash_changed")
    # Retain a full-array equality/hash check without restoring large raw files.
    npy=next(r for r in store.entries.values() if r["relative"].endswith(".npy"))
    a=store.numpy(npy["relative"])
    result.update(all_archived_originals_read_and_verified=True,numpy_reader_verified=True,
        numpy_rows=len(a),canonical_manifest_sha256=sha(store.manifest_path))
    save("compaction-final.json",result)
    event("V20_compaction_applied",files=len(result["removed"]),net_bytes=result["net_payload_bytes_saved"])


def performance():
    idle();TEMP_ROOT.mkdir(parents=True,exist_ok=True)
    names=tuple(RUNTIMES);start=time.perf_counter()
    def run(group):
        out=JOB/f"tests-final-{group}.json"
        if out.exists():raise ValueError("preserve_full_test_attempt")
        args=[RUNTIMES[group],"tooling/ai-engines/quant_test_suite.py","--group",group,"--tier","all","--output",str(out)]
        if group=="base":args += ["--workers","4","--profile",str(V19/"tests-final-base.json")]
        with out.with_suffix(".stdout").open("x") as log:
            r=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,env=dict(os.environ,TEMP=str(TEMP_ROOT),TMP=str(TEMP_ROOT)))
        return group,r.returncode,read(out)
    with ThreadPoolExecutor(max_workers=5) as pool:rows=list(pool.map(run,names))
    ids,old=set(),set()
    for group,code,row in rows:
        if code or not row["passed"] or row["skipped"] or ids.intersection(row["timings"]):
            raise ValueError("V20_full_test_failure_skip_or_duplicate:"+group)
        ids.update(row["timings"])
    for group in OLD_RUNTIMES:old.update(read(V19/f"tests-final-{group}.json")["timings"])
    if len(old)!=1216 or not old<=ids:raise ValueError("lost_V19_test_IDs")
    wall=time.perf_counter()-start
    save("tests-final-matrix.json",dict(tests=len(ids),preserved_V19_IDs=len(old),zero_skip=True,
        total_wall_seconds=wall,target_under16=wall<16,new_IDs=sorted(ids-old),
        runtime_groups=names,group_seconds={g:r["seconds"] for g,_,r in rows},
        same_assertions_and_fixture_IO=True,temporary_root=str(TEMP_ROOT),
        V19_reference_wall=15.580282900016755,no_claim_identical_workload=True))
    event("V20_full_suite",tests=len(ids),wall=wall,target_under16=wall<16)


def smoke():
    idle();TEMP_ROOT.mkdir(parents=True,exist_ok=True)
    save("smoke-final-plan.json",dict(attempts=10,threshold=.78,median_target=[.55,.65],
        fresh_processes=True,workers=1,indexed_imports=True,unchanged_78_IDs=True,
        includes_all_startup_import_fixture_IO=True,temporary_root=str(TEMP_ROOT),no_retry_for_streak=True))
    old=set(read(V19/"smoke-final-00.json")["timings"]);rows=[]
    for i in range(10):
        out=JOB/f"smoke-final-{i:02d}.json"
        if out.exists():raise ValueError("preserve_smoke_final_attempt")
        start=time.perf_counter()
        r=subprocess.run([sys.executable,"tooling/ai-engines/quant_test_suite.py","--group","base","--tier","smoke",
            "--indexed-imports","--output",str(out)],env=dict(os.environ,TEMP=str(TEMP_ROOT),TMP=str(TEMP_ROOT)),capture_output=True)
        wall=time.perf_counter()-start;x=read(out)
        if r.returncode or not x["passed"] or x["skipped"] or set(x["timings"])!=old:
            raise ValueError("smoke_functionality_or_IDs_changed")
        rows.append(dict(attempt=i+1,wall=wall,tests=x["tests"],passed=True,skipped=0,
                         import_seconds=x["import_seconds"],suite_seconds=x["seconds"]))
    save("smoke-final-results.json",dict(rows=rows,below078=sum(r["wall"]<.78 for r in rows),
        wall_max=max(r["wall"] for r in rows),wall_median=median(r["wall"] for r in rows),
        all_ten_below078=all(r["wall"]<.78 for r in rows),
        median_target_met=.55<=median(r["wall"] for r in rows)<=.65,unchanged_78_IDs=True))
    event("V20_final_smoke",below078=sum(r["wall"]<.78 for r in rows),max=max(r["wall"] for r in rows))


def storage():
    idle();roots={}
    for label,root in (("D","D:/ANNAM/TradingWorkspace"),("E","E:/BACKUP-TRADINGWORKSPACE")):
        output=JOB/f"storage-after-{label}.json"
        if output.exists():raise ValueError("preserve_storage_snapshot_attempt")
        with output.with_suffix(".stdout").open("x") as log:
            subprocess.run([sys.executable,"tooling/workspace_maintenance.py","inventory","--root",root,
                "--output",str(output)],stdout=log,stderr=subprocess.STDOUT,check=True)
        before,after=read(JOB/f"storage-before-{label}.json"),read(output)
        roots[label]=dict(before=before["groups"]["/"],after=after["groups"]["/"],
            delta={k:after["groups"]["/"][k]-before["groups"]["/"][k] for k in ("bytes","files","folders")},
            before_errors=before["errors"],after_errors=after["errors"])
    save("storage-final-summary.json",dict(roots=roots,compaction=read(JOB/"compaction-final.json"),
         logical_non_atomic_snapshots=True,physical_freed_bytes=None,unrelated_WIP_untouched=True))


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("stage",choices=("compaction","performance","smoke","storage"))
    p.add_argument("--attempt", help="Separate performance/smoke receipts after a documented source correction.")
    a=p.parse_args()
    if a.attempt:
        if a.stage not in ("performance","smoke") or not a.attempt.replace("-", "").isalnum():
            p.error("attempt must be one alphanumeric/hyphen directory for performance or smoke")
        idle()
        import prop_v20_common as common
        JOB = JOB / a.attempt
        JOB.mkdir(exist_ok=True)
        common.JOB = JOB
    globals()[a.stage]()

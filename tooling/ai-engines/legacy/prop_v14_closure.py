"""Nonfinancial V14 receipts: broad reference follow-up and fixed smoke batch."""
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from statistics import median
from prop_v14_source import JOB,V13,ROOTS,read,save,sha


def storage_followup():
    """Include ignored/untracked code and environments; never repeat deletion."""
    from prop_v14_storage import TEXT
    m=read(JOB/"DEDUP_MANIFEST.json")
    targets=[r["target"] for r in m["admitted"]+m["holds"]]
    needles={}
    for t in targets:
        key=t.replace("\\","/").lower()
        for n in (key,key.split("e:/backup-tradingworkspace/",1)[-1]):
            needles.setdefault(n,[]).append(t)
    pattern=re.compile("|".join(re.escape(n) for n in needles))
    pattern_file=JOB/"dedup-reference-literals.txt"
    if not pattern_file.exists():
        pattern_file.write_text("\n".join(n for key in needles for n in (key,key.replace("/","\\")))+"\n",encoding="utf-8")
    command=["rg","--files-with-matches","--text","--hidden","--no-ignore","--ignore-case",
        "--fixed-strings","--file",str(pattern_file),"-g","!**/.git/**"]
    for suffix in sorted(TEXT):command+=["-g","*"+suffix]
    command+=["."]
    found=subprocess.run(command,cwd=ROOTS[0],capture_output=True,text=True,encoding="utf-8",errors="replace")
    paths=found.stdout.splitlines();matches={t:[] for t in targets}
    failures=[];count=total=0
    for name in paths:
        p=ROOTS[0]/name
        if p.suffix.lower() not in TEXT:continue
        try:
            with p.open("r",encoding="utf-8",errors="replace") as f:
                for line in f:
                    total+=len(line)
                    for match in pattern.finditer(line.replace("\\","/").replace("//","/").lower()):
                        for t in needles[match.group()]:
                            if name not in matches[t]:matches[t].append(name)
            count+=1
        except OSError as exc:failures.append(dict(path=str(p),error=type(exc).__name__))
    removed=read(JOB/"dedup-receipt.json")["removed"]
    bad={r["target"]:matches[r["target"]] for r in removed if matches[r["target"]]}
    save("dedup-broad-reference-followup.json",dict(files_with_literal_matches=len(paths),
        matched_text_files_read=count,matched_characters_read=total,matches=matches,errors=failures,
        rg_status=found.returncode,rg_errors=found.stderr.splitlines(),
        ignored_and_untracked_included=True,mutations=0,removed_targets_with_reference=bad,
        scope="literal path/relative path scan, plus original import/package/process safeguards; not proof of arbitrary dynamic code absence"))
    print(dict(stage="V14_broad_reference_followup",files=count,errors=len(failures),
        removed_targets_with_reference=bad),flush=True)
    if bad:raise ValueError("V14_removed_copy_reference_requires_restore")


def smoke():
    registration=JOB/"smoke-ten-registration.json"
    if registration.exists():raise ValueError("preserve_registered_smoke_batch")
    save(registration.name,dict(runs=10,consecutive_fresh_processes=True,threshold_seconds=.85,
        timing="both suite internal and subprocess wall; no warm-up/exclusion/retry",
        time_utc=__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()))
    rows=[];ids=None
    for i in range(10):
        out=JOB/f"smoke-fixed-{i+1:02}.json"
        start=time.perf_counter()
        result=subprocess.run([sys.executable,"tooling/ai-engines/quant_test_suite.py",
            "--tier","smoke","--group","base","--output",str(out)],capture_output=True,text=True)
        wall=time.perf_counter()-start
        row=read(out)
        run_ids=set(row["timings"])
        if ids is None:ids=run_ids
        if run_ids!=ids:raise ValueError("smoke_case_IDs_changed")
        rows.append(dict(run=i+1,seconds=row["seconds"],wall_seconds=wall,tests=row["tests"],
            passed=result.returncode==0 and row["passed"],skipped=row["skipped"],sha256=sha(out)))
    modules=set(read(JOB/"smoke-fixed-01.json")["modules"])
    old={n for n in read(V13/"tests-base.json")["timings"] if n.split(".")[0] in modules}
    if ids!=old:raise ValueError("historical_smoke_IDs_changed")
    save("smoke-ten-results.json",dict(rows=rows,tests=len(ids),median_seconds=median(r["seconds"] for r in rows),
        max_seconds=max(r["seconds"] for r in rows),median_wall=median(r["wall_seconds"] for r in rows),
        max_wall=max(r["wall_seconds"] for r in rows),all_suite_under_085=all(r["seconds"]<.85 for r in rows),
        all_wall_under_085=all(r["wall_seconds"]<.85 for r in rows),
        no_failures_or_skips=all(r["passed"] and not r["skipped"] for r in rows),
        retries=0,historical_smoke_IDs_preserved=len(ids&old)))
    print(read(JOB/"smoke-ten-results.json"),flush=True)


def tests():
    groups=("base","native","statistics","worker")
    rows={g:read(JOB/f"tests-{g}.json") for g in groups}
    old=set();new=set()
    for g,r in rows.items():
        prior=read(V13/f"tests-{g}.json")
        if new&set(r["timings"]):raise ValueError("duplicate_test_ID")
        old.update(prior["timings"]);new.update(r["timings"])
        if not r["passed"] or r["skipped"]:raise ValueError("failed_or_skipped_tests")
    if old-new:raise ValueError("lost_historical_test_IDs")
    save("tests-final-matrix.json",dict(passed=True,tests=len(new),old=len(old),preserved=len(old&new),
        added=sorted(new-old),missing=sorted(old-new),skipped=0,groups={
            g:{k:r.get(k) for k in ("tests","seconds","passed","skipped","python")} for g,r in rows.items()}))
    print(read(JOB/"tests-final-matrix.json"),flush=True)


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("stage",choices=("storage_followup","smoke","tests"))
    globals()[p.parse_args().stage]()

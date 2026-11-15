"""Full-tree evidence for every V12 duplicate candidate; no guessed deletions."""
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
import json
import subprocess
import time
from prop_v13_campaign import JOB, V12, read, save
from deep_storage import merkle_tree, disjoint_partitions
from workspace_maintenance import inventory

ROOTS = [Path("D:/ANNAM/TradingWorkspace"),Path("E:/BACKUP-TRADINGWORKSPACE")]


def ownership_reason(path):
    text=str(path).replace("\\","/").lower()
    if any(x in text for x in ("/site-packages/","/uv/archive-v0/","/research-python/")):
        return "INSTALLED_DEPENDENCY_OR_PACKAGE_CACHE_NOT_REDUNDANT_BY_BYTES"
    if "/planning/trader/research/" in text or "/workspace/.tmp/" in text:
        return "HISTORICAL_FIXTURE_OR_BACKUP_RETIREMENT_NOT_PROVEN"
    if "/projects/" in text or "/tooling/" in text:
        return "PROJECT_SOURCE_OR_VENDOR_CONSUMER"
    return "CANONICAL_OWNER_AND_CONSUMER_ABSENCE_NOT_PROVEN"


def run():
    start=time.perf_counter()
    manifest=JOB/"merkle-trees"
    manifest.mkdir(exist_ok=False)
    before={}
    for label,root in zip(("D","E"),ROOTS):
        print(dict(stage="V13_census_before",root=str(root)),flush=True)
        before[label]=inventory(root)
        save(f"storage-{label}-before.json",before[label])
    candidates=read(V12/"duplicate-directory-candidates.json")["directory_candidates"]
    file_pairs=read(V12/"duplicate-files-crosspath.json")["verified_identical_file_pairs"]
    # No top-N or file-extension sampling: every parent in the 1,998-pair evidence is covered.
    paths=sorted({r[k] for r in candidates for k in ("D","E")})
    assert {str(Path(r[k]).parent) for r in file_pairs for k in ("D","E")} <= set(paths)
    processes=subprocess.run(
        ["powershell","-NoProfile","-Command",
         "Get-CimInstance Win32_Process | Select-Object ProcessId,ExecutablePath | ConvertTo-Json -Compress"],
        capture_output=True,text=True,check=True)
    process_rows=json.loads(processes.stdout)
    tracked=subprocess.check_output(["git","ls-files"],text=True).splitlines()
    texts=[]
    for name in tracked:
        p=ROOTS[0]/name
        if p.suffix.lower() in {".py",".ps1",".md",".json",".toml",".yml",".yaml",".cmd",".bat",".mjs",".ts"}:
            try:
                if p.is_file() and p.stat().st_size<=1_048_576:
                    texts.append((name,p.read_text(encoding="utf-8",errors="replace").replace("\\","/").lower()))
            except OSError:
                pass
    cache,trees={},{}
    for number,name in enumerate(paths):
        try:
            tree=merkle_tree(name,hash_cache=cache)
            destination=manifest/f"{number:04d}.json"
            destination.write_text(json.dumps(tree,indent=2),encoding="utf-8")
            normalized=name.replace("\\","/").lower()
            needles=[normalized]
            for root in ROOTS:
                try: needles.append(Path(name).relative_to(root).as_posix().lower())
                except ValueError: pass
            references=[p for p,text in texts if any(n in text for n in needles)]
            active=[p["ProcessId"] for p in process_rows if p.get("ExecutablePath") and
                    str(p["ExecutablePath"]).replace("\\","/").lower().startswith(normalized+"/")]
            trees[name]={k:v for k,v in tree.items() if k!="entries"}
            trees[name].update(manifest=str(destination),code_test_CI_references=references,
                               active_executable_pids=active,ownership_reason=ownership_reason(name))
        except (OSError,ValueError) as exc:
            trees[name]=dict(path=name,error=type(exc).__name__,message=str(exc))
        if number%40==0:
            print(dict(stage="V13_Merkle_progress",trees=number+1,total=len(paths)),flush=True)
    pairs=[]
    for row in candidates:
        left,right=trees[row["D"]],trees[row["E"]]
        equal="merkle_sha256" in left and "merkle_sha256" in right and left["merkle_sha256"]==right["merkle_sha256"]
        pairs.append(dict(**row,full_tree_identical=equal,
            D_merkle=left.get("merkle_sha256"),E_merkle=right.get("merkle_sha256"),
            D_files=left.get("files"),E_files=right.get("files"),
            byte_identical_copy_size=left.get("bytes") if equal else None,
            deletion_admitted=False,reason=left.get("ownership_reason","TREE_NOT_VERIFIED")))
    save("directory-dedup.json",dict(input_file_pairs=len(file_pairs),input_directory_pairs=len(candidates),
        whole_trees=len(paths),trees=list(trees.values()),pairs=pairs,
        equal_tree_pairs=sum(r["full_tree_identical"] for r in pairs),
        errors=sum("error" in r for r in trees.values()),
        unique_content_hash_work_bytes=sum(r.get("bytes_hashed",0) for r in trees.values()),
        hardlink_metadata_preserved=True,referenced_text_files=len(texts),
        process_scope="ExecutablePath only; interpreter command-line imports are not disproven",
        deleted=False,logical_bytes_removed=dict(D=0,E=0),physical_bytes_freed=None,
        disclosure="content equality is proven where stated; canonical redundancy/consumer absence is not"))
    after={}
    for label,root in zip(("D","E"),ROOTS):
        print(dict(stage="V13_census_after",root=str(root)),flush=True)
        after[label]=inventory(root);save(f"storage-{label}-after.json",after[label])
    v10=read(Path("planning/research/ENTERPRISE-ALPHA-V10-RESULTS-20261115.json"))["storage"]
    v12=read(V12/"storage-D-final.json")
    total=lambda x:x["groups"]["/"]
    history=dict(V10=v10["D_after"],V12=total(v12),V13_before=total(before["D"]),V13_after=total(after["D"]))
    changes=[]
    old_parts=disjoint_partitions(v12);new_parts=disjoint_partitions(before["D"])
    for key in old_parts.keys()|new_parts.keys():
        delta=new_parts.get(key,{}).get("bytes",0)-old_parts.get(key,{}).get("bytes",0)
        if delta:changes.append(dict(group=key,delta_bytes=delta))
    summary=dict(D_history=history,V10_to_V12_bytes=history["V12"]["bytes"]-history["V10"]["bytes"],
        D_units={k:dict(decimal_GB=v["bytes"]/1e9,GiB=v["bytes"]/1024**3) for k,v in history.items()},
        V12_to_V13_largest_changes=sorted(changes,key=lambda x:-abs(x["delta_bytes"]))[:20],
        observed_scope_delta={label:{k:total(after[label])[k]-total(before[label])[k] for k in ("bytes","files","folders")}
                              for label in ("D","E")},
        exact_removed={label:dict(bytes=0,files=0,folders=0) for label in ("D","E")},
        before_errors={k:v["errors"] for k,v in before.items()},
        after_errors={k:v["errors"] for k,v in after.items()},
        duplicate_pairs=len(candidates),whole_tree_equal_pairs=sum(r["full_tree_identical"] for r in pairs),
        ownership_holds=dict(Counter(r["reason"] for r in pairs)),
        all_1998_input_pairs_covered=True,seconds=time.perf_counter()-start,
        observed_utc=datetime.now(timezone.utc).isoformat(),logical_bytes_only=True)
    save("storage-summary.json",summary)
    print(dict(stage="V13_storage_complete",summary=summary),flush=True)


def reconcile_baseline():
    """Receipt-only correction: the final V12 census is the comparable endpoint."""
    summary=read(JOB/"storage-summary.json")
    v12=read(V12/"storage-D-final.json")
    current=read(JOB/"storage-D-before.json")
    summary["D_history"]["V12"]=v12["groups"]["/"]
    summary["V10_to_V12_bytes"]=summary["D_history"]["V12"]["bytes"]-summary["D_history"]["V10"]["bytes"]
    summary["D_units"]={k:dict(decimal_GB=v["bytes"]/1e9,GiB=v["bytes"]/1024**3)
                        for k,v in summary["D_history"].items()}
    previous,now=disjoint_partitions(v12),disjoint_partitions(current)
    changes=[dict(group=k,delta_bytes=now.get(k,{}).get("bytes",0)-previous.get(k,{}).get("bytes",0))
             for k in previous.keys()|now.keys()]
    summary["V12_to_V13_largest_changes"]=sorted(
        [r for r in changes if r["delta_bytes"]],key=lambda r:-abs(r["delta_bytes"]))[:20]
    summary["baseline_correction"]=dict(
        reason="use final V12 census instead of its initial census; no rescan or mutation",
        original_preserved=str(JOB/"storage-summary.json"),source=str(V12/"storage-D-final.json"))
    save("storage-summary-final.json",summary)
    print(dict(V10_to_V12_bytes=summary["V10_to_V12_bytes"],rescan=False))


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--reconcile-baseline",action="store_true")
    args=p.parse_args()
    reconcile_baseline() if args.reconcile_baseline else run()

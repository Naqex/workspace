"""Close the 47 V14 dispositions without corrupting partial package installs."""
from collections import Counter,defaultdict
from pathlib import Path
import csv
import json
import os
import shutil
import subprocess
import zipfile
from prop_v15_common import *
from deep_storage import merkle_tree,disjoint_partitions
from workspace_maintenance import inventory,linked

BACKUP=Path("E:/BACKUP-TRADINGWORKSPACE")
WORKSPACE=Path("D:/ANNAM/TradingWorkspace")


def package_records(target):
    normalized=target.as_posix()
    marker="/Lib/site-packages/"
    if marker in normalized:
        root=Path(normalized.split(marker)[0]+marker[:-1])
        group="INSTALLED_ENVIRONMENT_SUBTREE"
    else:
        root=next(p for p in target.parents if p.parent.name=="archive-v0")
        group="UV_PACKAGE_ARCHIVE_SUBTREE"
    proofs=[]
    relative=target.relative_to(root).as_posix()
    for record in root.glob("*.dist-info/RECORD"):
        with record.open(encoding="utf-8",newline="") as f:
            matches=[r[0] for r in csv.reader(f) if r and
                (r[0]==relative or r[0].startswith(relative+"/"))]
        if matches:proofs.append(dict(path=str(record),sha256=sha(record),entries=len(matches)))
    return group,dict(package_root=str(root),distribution_RECORDs=proofs,
        RECORD_consumer_proven=bool(proofs),
        reason="Partial subtree belongs to distribution/cache; byte equality is not retirement of that package.")


def archive_copy(target,canonical,tree,index):
    archive=JOB/f"dedup-{index:02d}.zip";restore=JOB/f"dedup-{index:02d}-restore-proof"
    if archive.exists() or restore.exists():raise ValueError("preserve_V15_archive_attempt")
    with zipfile.ZipFile(archive,"x",compression=zipfile.ZIP_DEFLATED) as z:
        for e in tree["entries"]:
            name=e["relative"]
            if e["kind"]=="D":z.writestr(name+"/",b"")
            else:z.write(target/name,name)
    restore.mkdir()
    with zipfile.ZipFile(archive) as z:
        for info in z.infolist():
            output=restore/info.filename
            if not output.resolve().is_relative_to(restore.resolve()):raise ValueError("archive_restore_scope")
            z.extract(info,restore)
    if merkle_tree(restore)["merkle_sha256"]!=tree["merkle_sha256"]:
        raise ValueError("archive_restore_hash")
    resolved=target.resolve(strict=True);resolved_root=BACKUP.resolve(strict=True)
    if not resolved.is_relative_to(resolved_root) or resolved==resolved_root:
        raise ValueError("V15_delete_scope")
    if merkle_tree(target)["merkle_sha256"]!=tree["merkle_sha256"] or \
            merkle_tree(canonical)["merkle_sha256"]!=tree["merkle_sha256"]:
        raise ValueError("V15_archive_copy_drift")
    journal=dict(target=str(target),canonical=str(canonical),archive=str(archive),
        archive_sha256=sha(archive),merkle_sha256=tree["merkle_sha256"],
        bytes=tree["bytes"],files=tree["files"],restore_proof=True)
    save(f"dedup-{index:02d}-intent.json",journal)
    shutil.rmtree(resolved)
    restored=restore.resolve(strict=True)
    if not restored.is_relative_to(JOB.resolve()) or restored==JOB.resolve():raise ValueError("restore_cleanup_scope")
    shutil.rmtree(restored)
    if target.exists() or merkle_tree(canonical)["merkle_sha256"]!=tree["merkle_sha256"]:
        raise ValueError("V15_archive_postcondition")
    return dict(journal,disposition="ARCHIVED_AND_REDUNDANT_COPY_REMOVED",archive_bytes=archive.stat().st_size)


def run():
    old=read(V14/"DEDUP_MANIFEST.json")
    held=old["holds"]
    if len(held)!=47:raise ValueError("V15_duplicate_input_not_47")
    original_scan=read(V14/"dedup-reference-scan.json")
    # Current process matching is retained as PIDs only, never arbitrary command lines.
    processes=json.loads(subprocess.check_output(["powershell","-NoProfile","-Command",
        "Get-CimInstance Win32_Process | Select-Object ProcessId,ExecutablePath,CommandLine | ConvertTo-Json -Compress"],
        text=True))
    cache={};rows=[];package_groups=Counter()
    maximal={Path(r["target"]) for r in held}
    maximal={p for p in maximal if not any(a in maximal for a in p.parents)}
    for i,r in enumerate(held):
        target,canonical=Path(r["target"]),Path(r["canonical"])
        a,b=merkle_tree(target,hash_cache=cache),merkle_tree(canonical,hash_cache=cache)
        same=a["merkle_sha256"]==b["merkle_sha256"]
        lower=target.as_posix().lower()
        pids=[p["ProcessId"] for p in processes if lower in
            (str(p.get("ExecutablePath",""))+" "+str(p.get("CommandLine",""))).replace("\\","/").lower()]
        refs=[]
        for name in original_scan["references"].get(str(target),[]):
            p=WORKSPACE/name
            if p.is_file():
                refs.append(dict(path=str(p),sha256=sha(p),
                    kind="HISTORICAL_EVIDENCE_LOCATOR" if name.startswith("planning/research/") else "CODE_OR_CI"))
        base=dict(index=i,target=str(target),canonical=str(canonical),bytes=a["bytes"],
            files=a["files"],folders=a["folders"],merkle_sha256=a["merkle_sha256"],
            currently_identical=same,active_pids=pids,references=refs,
            counted_in_disjoint_total=target in maximal)
        save(f"dedup-tree-{i:02d}.json",a)
        if "/site-packages/" in lower or "/archive-v0/" in lower:
            group,proof=package_records(target)
            base.update(group=group,disposition="KEEP_PACKAGE_INTEGRITY",package=proof)
            package_groups[group]+=1
        else:
            embedded=any((p/".git").exists() or linked(p) for p in (target,*target.parents)
                if p.is_relative_to(BACKUP))
            safe=(same and not embedded and not pids and
                all(x["kind"]=="HISTORICAL_EVIDENCE_LOCATOR" for x in refs) and
                target.is_relative_to(BACKUP/"workspace/.tmp") and target.name=="bundles")
            if safe:
                base.update(group="HISTORICAL_CHART_LIBRARY_COPY",
                    **archive_copy(target,canonical,a,i))
            else:
                base.update(group="HISTORICAL_CHART_LIBRARY_COPY",disposition="KEEP_REFERENCED_OR_UNPROVEN",
                    reason=dict(identical=same,embedded_or_linked=embedded,active=pids,refs=refs))
        rows.append(base)
        event("V15_duplicate_disposition",index=i,disposition=base["disposition"],bytes=base["bytes"])
    disjoint=[r for r in rows if r["counted_in_disjoint_total"]]
    groups={}
    for group in sorted({r["group"] for r in rows}):
        selected=[r for r in rows if r["group"]==group]
        unique=[r for r in disjoint if r["group"]==group]
        groups[group]=dict(targets=len(selected),disjoint_trees=len(unique),
            disjoint_bytes=sum(r["bytes"] for r in unique),disjoint_files=sum(r["files"] for r in unique))
    archived=[r for r in rows if r["disposition"]=="ARCHIVED_AND_REDUNDANT_COPY_REMOVED"]
    save("dedup-dispositions.json",dict(input_pairs=106,V14_removed_trees=4,V15_targets=47,rows=rows,
        groups=groups,all_dispositions_recorded=len(rows)==47,raw_overlapping_bytes=sum(r["bytes"] for r in rows),
        disjoint_bytes=sum(r["bytes"] for r in disjoint),disjoint_files=sum(r["files"] for r in disjoint),
        logical_removed_bytes=sum(r["bytes"] for r in archived),
        archive_bytes=sum(r["archive_bytes"] for r in archived),
        package_subtrees_kept=sum(r["disposition"]=="KEEP_PACKAGE_INTEGRITY" for r in rows),
        physical_bytes_freed=None,cross_volume_hardlinks_possible=False,
        no_live_environment_removed=True,old_four_tree_purge_repeated=False))


def space_map():
    out={}
    for label,root in (("D",WORKSPACE),("E",BACKUP)):
        current=inventory(root);save(f"storage-{label}-current.json",current)
        parts=disjoint_partitions(current)
        out[label]=dict(root=str(root),total=current["groups"]["/"],errors=current["errors"],
            largest_disjoint=sorted([dict(group=k,**v) for k,v in parts.items()],key=lambda r:-r["bytes"])[:25],
            logical_bytes_only=True)
    save("storage-map.json",out);event("V15_storage_map_complete",totals={k:v["total"] for k,v in out.items()})


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("stage",choices=("dispositions","space"))
    a=p.parse_args()
    run() if a.stage=="dispositions" else space_map()

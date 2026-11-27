"""Owner-authorized zero-reference duplicate copies; rehash, manifest and journal."""
from pathlib import Path
import json
import os
import shutil
import subprocess
import time
from prop_v14_source import JOB,V13,ROOTS,read,save,sha
from deep_storage import merkle_tree
from workspace_maintenance import linked

TEXT={".py",".pyi",".ps1",".cmd",".bat",".sh",".rs",".ts",".tsx",".js",".mjs",
      ".cjs",".toml",".json",".yaml",".yml",".ini",".cfg",".md",".txt"}


def reference_scan(targets):
    paths=subprocess.check_output(["git","ls-files","--recurse-submodules","-z"],cwd=ROOTS[0]).decode().split("\0")
    refs={str(t):[] for t in targets};errors=[];read_files=0
    needles={str(t):[str(t).replace("\\","/").lower(),
                    str(t.relative_to(ROOTS[1])).replace("\\","/").lower()] for t in targets}
    for name in paths:
        if not name:continue
        p=ROOTS[0]/name
        if p.suffix.lower() not in TEXT:continue
        try:
            if not p.is_file():continue
            # Stream all text; no size threshold silently omits a code/CI consumer.
            with p.open("r",encoding="utf-8",errors="replace") as f:
                for line in f:
                    line=line.replace("\\","/").replace("//","/").lower()
                    for target,values in needles.items():
                        if any(n in line for n in values):
                            if name not in refs[target]:refs[target].append(name)
            read_files+=1
        except OSError as exc:errors.append(dict(path=str(p),error=type(exc).__name__))
    processes=json.loads(subprocess.check_output(
        ["powershell","-NoProfile","-Command",
         "Get-CimInstance Win32_Process | Select-Object ProcessId,ExecutablePath,CommandLine | ConvertTo-Json -Compress"],
        text=True))
    active={}
    # Persist matches/PIDs, never arbitrary command lines which may contain credentials.
    for target,values in needles.items():
        active[target]=[p["ProcessId"] for p in processes if any(
            n in str(p.get("ExecutablePath","")).replace("\\","/").lower() or
            n in str(p.get("CommandLine","")).replace("\\","/").lower() for n in values)]
    return dict(references=refs,active_pids=active,errors=errors,tracked_files_considered=len(paths),
                text_files_scanned=read_files,submodules_included=True)


def purge():
    started=time.perf_counter()
    pairs=[p for p in read(V13/"directory-dedup.json")["pairs"] if p["full_tree_identical"]]
    assert len(pairs)==106
    by_target={}
    for row in pairs:
        by_target.setdefault(row["E"],[]).append(row["D"])
    scan=reference_scan([Path(p) for p in by_target])
    save("dedup-reference-scan.json",scan)
    holds=[];admitted=[];cache={}
    for target_text,canonical_list in sorted(by_target.items()):
        target=Path(target_text).absolute();canonical=Path(sorted(canonical_list)[0]).absolute()
        reasons=[]
        if not target.is_relative_to(ROOTS[1]) or not canonical.is_relative_to(ROOTS[0]):
            reasons.append("ROOT_SCOPE")
        if "vi-dubber" in str(target).lower() or "vi-dubber" in str(canonical).lower():
            reasons.append("VI_PROTECTED")
        lower=str(target).replace("\\","/").lower()
        if "/site-packages/" in lower or "/archive-v0/" in lower:
            reasons.append("PARTIAL_INSTALLED_OR_UV_CACHE_TREE_RETAINS_PACKAGE_METADATA_CONSUMER")
        # Preserve an external Git checkout and all initialized worktrees.
        if any((p/".git").exists() for p in (target,*target.parents) if p.is_relative_to(ROOTS[1])):
            reasons.append("GIT_CHECKOUT_OR_BACKUP")
        if scan["references"][target_text]:reasons.append("CODE_TEST_CI_REFERENCE")
        if scan["active_pids"][target_text]:reasons.append("ACTIVE_PROCESS_REFERENCE")
        if scan["errors"]:reasons.append("REFERENCE_SCAN_INCOMPLETE")
        try:
            a,b=merkle_tree(canonical,hash_cache=cache),merkle_tree(target,hash_cache=cache)
            if a["merkle_sha256"]!=b["merkle_sha256"]:reasons.append("CONTENT_DRIFT_SINCE_V13")
        except (OSError,ValueError) as exc:
            a=b={};reasons.append("TREE_PREFLIGHT:"+type(exc).__name__)
        if reasons:
            holds.append(dict(target=target_text,canonical=str(canonical),reasons=reasons,
                              references=scan["references"][target_text]))
            continue
        admitted.append(dict(target=str(target),canonical=str(canonical),merkle=a["merkle_sha256"],
            entries=b["entries"],bytes=b["bytes"],files=b["files"],folders=b["folders"]+1,
            hardlinked_files=b["hardlinked_files"],
            restoration="copy canonical tree to this exact target; verify relative-path SHA256 manifest"))
    # Keep only maximal nonoverlapping copies; a copy can be canonical for no deletion target.
    targets={Path(r["target"]) for r in admitted}
    admitted=[r for r in admitted if not any(p in targets for p in Path(r["target"]).parents)]
    manifest=dict(schema="V14-owner-authorized-dedup-v1",input_pairs=106,unique_targets=len(by_target),
        admitted=admitted,holds=holds,D_canonical_preserved=True,reference_scan_sha256=sha(JOB/"dedup-reference-scan.json"))
    save("DEDUP_MANIFEST.json",manifest)
    journal=JOB/"dedup-journal.jsonl"
    if journal.exists():raise ValueError("preserve_dedup_attempt")
    done=[]
    # All admitted trees were preflighted before the first mutation.
    for row in admitted:
        target=Path(row["target"]).resolve(strict=True)
        canonical=Path(row["canonical"]).resolve(strict=True)
        if not target.is_relative_to(ROOTS[1].resolve()) or target==ROOTS[1].resolve():
            raise ValueError("resolved_delete_scope")
        if merkle_tree(target)["merkle_sha256"]!=row["merkle"] or merkle_tree(canonical)["merkle_sha256"]!=row["merkle"]:
            raise ValueError("dedup_changed_before_delete")
        with journal.open("a") as f:f.write(json.dumps(dict(event="REMOVE_INTENT",target=str(target)))+"\n")
        shutil.rmtree(target)
        if target.exists() or merkle_tree(canonical)["merkle_sha256"]!=row["merkle"]:
            raise ValueError("dedup_postcondition")
        done.append({k:row[k] for k in ("target","canonical","bytes","files","folders","hardlinked_files")})
        with journal.open("a") as f:f.write(json.dumps(dict(event="REMOVED_CANONICAL_VERIFIED",**done[-1]))+"\n")
    save("dedup-receipt.json",dict(passed=True,removed=done,held=holds,logical_bytes=sum(r["bytes"] for r in done),
        files=sum(r["files"] for r in done),folders=sum(r["folders"] for r in done),
        physical_bytes_freed=None,manifest_sha256=sha(JOB/"DEDUP_MANIFEST.json"),
        D_removed_bytes=0,E_removed_bytes=sum(r["bytes"] for r in done),seconds=time.perf_counter()-started))
    print(dict(stage="V14_duplicate_cleanup",targets=len(done),bytes=sum(r["bytes"] for r in done),
               held_targets=len(holds)),flush=True)


if __name__=="__main__":
    purge()

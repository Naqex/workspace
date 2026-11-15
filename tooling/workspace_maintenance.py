"""Read-only inventory and explicit, containment-checked cache maintenance."""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import tarfile
import re

CACHES = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
BUILD_CACHES = {"target","cargo-target","rust-target","api-target","release-target"}
PROTECTED = {".git", "node_modules", ".venv", "venv", "source-cache"}
REPARSE = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 1024)


def linked(path):
    s = path.lstat()
    return path.is_symlink() or bool(getattr(s, "st_file_attributes", 0) & REPARSE)


def inventory(root):
    root = Path(root).resolve(strict=True)
    groups = defaultdict(lambda: dict(bytes=0, files=0, folders=0))
    groups["/"]  # Empty roots still have a valid zero-count health summary.
    candidates, build_candidates, skipped, errors = [], [], [], []
    stack = [root]
    while stack:
        folder = stack.pop()
        try:
            scan_path = "\\\\?\\" + str(folder) if os.name == "nt" else folder
            with os.scandir(scan_path) as entries:
                for e in entries:
                    p = folder / e.name
                    s = e.stat(follow_symlinks=False)
                    if e.is_symlink() or getattr(s, "st_file_attributes", 0) & REPARSE:
                        skipped.append(str(p))
                        continue
                    rel = p.relative_to(root).parts
                    keys = ["/", rel[0]]
                    if len(rel) >= 2:
                        keys.append("/".join(rel[:2]))
                    isdir = e.is_dir(follow_symlinks=False)
                    for key in keys:
                        groups[key]["folders" if isdir else "files"] += 1
                        if not isdir:
                            groups[key]["bytes"] += s.st_size
                    if isdir:
                        stack.append(p)
                        if p.name in CACHES and "vi-dubber" not in rel and ".git" not in rel:
                            candidates.append(str(p))
                        if p.name in BUILD_CACHES and "vi-dubber" not in rel and ".git" not in rel:
                            build_candidates.append(str(p))
        except OSError as exc:
            errors.append(dict(path=str(folder), type=type(exc).__name__))
    return dict(root=str(root), groups=dict(sorted(groups.items())),
                cache_candidates=candidates, build_cache_candidates=build_candidates,
                skipped_links=skipped, errors=errors)


def verified_tree(root, target):
    root, target = Path(root).resolve(strict=True), Path(target).absolute()
    if not target.is_relative_to(root) or target == root:
        raise ValueError("target_outside_root")
    rel = target.relative_to(root)
    if "vi-dubber" in rel.parts or ".git" in rel.parts:
        raise ValueError("protected_owner")
    for p in [target, *list(target.parents)[:len(rel.parts)]]:
        if linked(p):
            raise ValueError("reparse_target")
    if target.resolve(strict=True) != target:
        raise ValueError("target_resolution_changed")
    files = []
    for folder, dirs, names in os.walk(target, followlinks=False):
        for name in dirs + names:
            p = Path(folder) / name
            if linked(p):
                raise ValueError("reparse_descendant")
        files.extend(Path(folder) / name for name in names)
    return files


def purge(root, candidates):
    """Only explicitly listed generated caches; no venv/node/raw/evidence purge."""
    unique = sorted({Path(p).absolute() for p in candidates}, key=lambda p: len(p.parts))
    selected, selected_set, receipts = [], set(), []
    for p in unique:
        if any(parent in selected_set for parent in p.parents):
            continue
        if p.name not in CACHES:
            raise ValueError("not_disposable_cache")
        files = verified_tree(root, p)
        receipts.append(dict(path=str(p), files=len(files),
                             bytes=sum(f.stat().st_size for f in files)))
        selected.append(p)
        selected_set.add(p)
    # Preflight every target before making the first mutation.
    for p in selected:
        shutil.rmtree(p)
    return dict(purged=receipts, bytes=sum(r["bytes"] for r in receipts),
                files=sum(r["files"] for r in receipts))


def archive(root, target, destination):
    """Lossless archive of an explicitly approved cold directory; retains source."""
    files = verified_tree(root, target)
    target, destination = Path(target).absolute(), Path(destination).absolute()
    if destination.exists() or destination.is_relative_to(target):
        raise ValueError("archive_destination")
    manifest = {}
    for p in sorted(files):
        with p.open("rb") as f:
            manifest[p.relative_to(target).as_posix()] = hashlib.file_digest(f, "sha256").hexdigest()
    with tarfile.open(destination, "w:gz") as tar:
        tar.add(target, arcname=target.name, recursive=True)
    with tarfile.open(destination, "r:gz") as tar:
        for name, sha in manifest.items():
            with tar.extractfile(target.name + "/" + name) as f:
                if hashlib.file_digest(f, "sha256").hexdigest() != sha:
                    raise ValueError("archive_roundtrip")
    with destination.open("rb") as f:
        sha = hashlib.file_digest(f, "sha256").hexdigest()
    receipt = dict(source=str(target), archive=str(destination), files=manifest,
                   source_preserved=True, sha256=sha)
    destination.with_suffix(destination.suffix + ".MANIFEST.json").write_text(json.dumps(receipt, indent=2))
    return receipt


def compact_environment(root, target, destination):
    """Explicit cold generated environment only; roundtrip archive before removal."""
    target = Path(target).absolute()
    if target.name not in {".venv", "node_modules"} or ".artifacts" not in target.parts:
        raise ValueError("not_cold_artifact_environment")
    files = verified_tree(root, target)
    if any(".git" in p.relative_to(target).parts for p in files):
        raise ValueError("embedded_repository")
    receipt = archive(root, target, destination)
    # Revalidate containment and every file after packing, before removal.
    current = verified_tree(root, target)
    if len(current) != len(files):
        raise ValueError("archive_source_changed")
    for p in current:
        with p.open("rb") as f:
            if hashlib.file_digest(f, "sha256").hexdigest() != receipt["files"][p.relative_to(target).as_posix()]:
                raise ValueError("archive_source_changed")
    shutil.rmtree(target)
    receipt["source_preserved"] = False
    receipt["restoration"] = "extract archive into the original parent directory; verify MANIFEST hashes"
    Path(destination).with_suffix(Path(destination).suffix + ".MANIFEST.json").write_text(json.dumps(receipt, indent=2))
    return receipt


def purge_incremental(root, target):
    target = Path(target).absolute()
    if target.name != "incremental" or target.parent.name not in {"debug", "release"} or target.parent.parent.name != "target":
        raise ValueError("not_rust_incremental")
    files = verified_tree(root, target)
    receipt = dict(path=str(target), files=len(files), bytes=sum(p.stat().st_size for p in files))
    shutil.rmtree(target)
    return receipt


def snapshot_view(records, destination):
    """Copy exact sealed bytes into one view; absolute inputs never form outputs."""
    destination = Path(destination).resolve()
    prepared = []
    for r in records:
        source = Path(r["path"])
        raw = source.read_bytes()
        candidates = {raw}
        if source.suffix in {".py", ".md", ".json"}:
            lf = raw.replace(b"\r\n", b"\n")
            candidates.update((lf, lf.replace(b"\n", b"\r\n")))
        matches = [b for b in candidates if hashlib.sha256(b).hexdigest() == r["sha256"]]
        if len(matches) != 1:
            raise ValueError("snapshot_content_changed")
        name = hashlib.sha256(str(source).encode()).hexdigest()[:16] + "-" + source.name
        target = destination / name
        if not target.resolve().is_relative_to(destination) or target.resolve() == source.resolve():
            raise ValueError("snapshot_output_overrides_source")
        prepared.append((source, target, matches[0], r["sha256"]))
    destination.mkdir(parents=True, exist_ok=True)
    output = []
    for source, target, raw, sha in prepared:
        if target.exists() and target.read_bytes() != raw:
            raise ValueError("existing_snapshot_changed")
        target.write_bytes(raw)
        output.append(dict(source=str(source), snapshot=str(target), sha256=sha))
    return output


def backup_plan(root, destination):
    source, destination = Path(root).resolve(strict=True), Path(destination).absolute()
    if destination == source or destination.is_relative_to(source) or source.is_relative_to(destination):
        raise ValueError("backup_roots_overlap")
    return dict(source=str(source), destination=str(destination), read_only=True,
                command=["robocopy", str(source), str(destination), "/E", "/L", "/XJ",
                         "/R:0", "/W:0", "/XD", *sorted(CACHES),
                         "node_modules", ".venv", "target", "/XF", "*.pyc"],
                note="Dry-run only. Never /MIR or /PURGE; preserve existing E research evidence.")


def maintain(root, *, destination=None, apply_caches=False):
    before = inventory(root)
    # Validate the backup destination before any optional cleanup.
    plan = backup_plan(root, destination) if destination else None
    deleted = purge(root, before["cache_candidates"]) if apply_caches else None
    after = inventory(root) if apply_caches else before
    return dict(before=before, after=after, cache_purge=deleted, backup=plan,
                caches_applied=apply_caches, backup_copied=False)


def market_inventory(roots):
    """Filename/size metadata only; never decode validation quotes or follow links."""
    skip = {".git","node_modules",".venv","venv","__pycache__",".pytest_cache",
            "$recycle.bin","system volume information","program files","program files (x86)",
            "programdata","windows","steamlibrary","riot games","googledrivecache",
            "target","cargo-target","rust-target","api-target","release-target"}
    symbols = re.compile(r"XAUUSD|XAGUSD|EURUSD|GBPUSD|USDJPY|AUDUSD|USDCHF|USDCAD|NZDUSD|"
                         r"GBPJPY|EURJPY|AUDJPY|BTCUSDT?|ETHUSDT?|US500|SPX500|USA500|"
                         r"USAIDXUSD|NAS100|US100|USATECHIDXUSD|US30|WTI|BRENT",re.I)
    data_ext = {".csv",".parquet",".arrow",".feather",".bi5",".hcc",".hc",".hst",
                ".fxt",".bin",".ticks",".h5",".hdf5",".db",".sqlite",".sqlite3"}
    files, skipped, errors = [], [], []
    resolved = sorted({Path(p).resolve(strict=True) for p in roots},key=lambda p:len(p.parts))
    admitted = []
    for root in resolved:
        if not any(root.is_relative_to(parent) for parent in admitted):
            admitted.append(root)
    for root in admitted:
        stack=[root]
        while stack:
            folder=stack.pop()
            try:
                scan="\\\\?\\"+str(folder) if os.name=="nt" else folder
                with os.scandir(scan) as entries:
                    for entry in entries:
                        path=folder/entry.name
                        s=entry.stat(follow_symlinks=False)
                        if entry.is_symlink() or getattr(s,"st_file_attributes",0)&REPARSE:
                            skipped.append(dict(path=str(path),reason="link"));continue
                        if entry.is_dir(follow_symlinks=False):
                            if entry.name.lower() in skip:
                                skipped.append(dict(path=str(path),reason="non_market_dependency_or_system"))
                            else:
                                stack.append(path)
                            continue
                        text=str(path)
                        tokens=sorted(set(m.group().upper() for m in symbols.finditer(text)))
                        likely=bool(tokens) or any(t in text.lower() for t in
                            ("ai-engine-jobs","dukascopy","/qdm","\\qdm","market-data","forex-data","source-cache"))
                        metadata=path.suffix.lower()==".json" and any(
                            t in entry.name.lower() for t in ("manifest","source-proof","source-admission",
                                "source-metadata","source-observation-proof","sealed-books"))
                        if likely and (path.suffix.lower() in data_ext or metadata):
                            files.append(dict(path=str(path),bytes=s.st_size,mtime_ns=s.st_mtime_ns,
                                symbols=tokens,kind="manifest_metadata" if metadata else "potential_market_source"))
            except OSError as exc:
                errors.append(dict(path=str(folder),error=type(exc).__name__))
    return dict(roots=list(map(str,admitted)),files=files,skipped=skipped,errors=errors,
                read_only=True,quote_values_decoded=False,names_are_not_admission=True)


def cross_drive_audit(roots, cache_targets=(), *, cache_budget_bytes=120_000_000_000):
    """Explicit disk health snapshot; alert on cache growth without automatic deletion."""
    snapshots=[inventory(root) for root in roots]
    cache=[]
    targets={Path(p).absolute() for p in cache_targets}
    targets.update(Path(p).absolute() for census in snapshots for p in census["build_cache_candidates"])
    selected=[]
    for path in sorted(targets,key=lambda p:(len(p.parts),str(p))):
        if not any(path.is_relative_to(parent) for parent in selected):
            selected.append(path)
    for target in selected:
        path=Path(target)
        if not path.exists():
            cache.append(dict(path=str(path),exists=False,bytes=0));continue
        if linked(path):
            cache.append(dict(path=str(path),exists=True,unknown=True,reason="link"));continue
        census=inventory(path)
        cache.append(dict(path=str(path),exists=True,**census["groups"]["/"],errors=census["errors"]))
    known=sum(r.get("bytes",0) for r in cache)
    unknown=any(r.get("unknown") or r.get("errors") for r in cache) or any(r["errors"] for r in snapshots)
    return dict(read_only=True,roots=snapshots,caches=cache,cache_known_bytes=known,
                cache_budget_bytes=cache_budget_bytes,cache_budget_exceeded=known>=cache_budget_bytes,
                cache_unknown=unknown,no_future_growth_guarantee=True,automatic_deletion=False,
                discovered_build_candidates=True,names_are_not_delete_authority=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("inventory", "purge", "backup-plan", "maintain","cross-drive-audit","market-inventory"))
    p.add_argument("--root", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--approved-inventory")
    p.add_argument("--destination")
    p.add_argument("--apply-caches", action="store_true")
    p.add_argument("--other-root",action="append",default=[])
    p.add_argument("--cache-manifest")
    a = p.parse_args()
    if a.action == "backup-plan" and not a.destination:
        p.error("backup-plan requires --destination")
    if a.action == "purge" and not a.approved_inventory:
        p.error("purge requires --approved-inventory")
    if a.action=="cross-drive-audit":
        targets=[]
        if a.cache_manifest:
            targets=[r["path"] for r in json.loads(Path(a.cache_manifest).read_bytes())["candidates"]]
        result=cross_drive_audit([a.root,*a.other_root],targets)
    elif a.action=="market-inventory":
        result=market_inventory([a.root,*a.other_root])
    elif a.action == "inventory":
        result = inventory(a.root)
    elif a.action == "purge":
        prior = json.loads(Path(a.approved_inventory).read_text())
        if Path(prior["root"]).resolve() != Path(a.root).resolve():
            raise ValueError("inventory_root_mismatch")
        result = purge(a.root, prior["cache_candidates"])
    elif a.action == "backup-plan":
        result = backup_plan(a.root, a.destination)
    else:
        result = maintain(a.root, destination=a.destination, apply_caches=a.apply_caches)
    Path(a.output).write_text(json.dumps(result, indent=2), encoding="utf-8")
    if a.action in ("cross-drive-audit","market-inventory"):
        print(json.dumps({k:v for k,v in result.items() if k not in
                          ("roots","files","skipped","errors","caches")}))
        if a.action=="market-inventory":
            print(dict(files=len(result["files"]),errors=len(result["errors"])))
        return
    if a.action == "maintain":
        print(json.dumps(dict(root=result["before"]["root"],
                              before=result["before"]["groups"]["/"],
                              after=result["after"]["groups"]["/"],
                              caches_applied=result["caches_applied"], backup_copied=False)))
        return
    print(json.dumps(dict(root=result.get("root"), total=result.get("groups", {}).get("/"),
                          errors=len(result.get("errors", [])),
                          files_purged=result.get("files"), bytes_purged=result.get("bytes"))))


if __name__ == "__main__":
    main()

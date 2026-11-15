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

CACHES = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
PROTECTED = {".git", "node_modules", ".venv", "venv", "source-cache"}
REPARSE = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 1024)


def linked(path):
    s = path.lstat()
    return path.is_symlink() or bool(getattr(s, "st_file_attributes", 0) & REPARSE)


def inventory(root):
    root = Path(root).resolve(strict=True)
    groups = defaultdict(lambda: dict(bytes=0, files=0, folders=0))
    candidates, skipped, errors = [], [], []
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
        except OSError as exc:
            errors.append(dict(path=str(folder), type=type(exc).__name__))
    return dict(root=str(root), groups=dict(sorted(groups.items())),
                cache_candidates=candidates, skipped_links=skipped, errors=errors)


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


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("inventory", "purge", "backup-plan", "maintain"))
    p.add_argument("--root", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--approved-inventory")
    p.add_argument("--destination")
    p.add_argument("--apply-caches", action="store_true")
    a = p.parse_args()
    if a.action == "backup-plan" and not a.destination:
        p.error("backup-plan requires --destination")
    if a.action == "purge" and not a.approved_inventory:
        p.error("purge requires --approved-inventory")
    if a.action == "inventory":
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

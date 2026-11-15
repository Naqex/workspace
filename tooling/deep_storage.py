"""Disjoint byte accounting, lossless cold bundles and non-destructive backup plans."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import shutil
import zipfile

from workspace_maintenance import inventory, verified_tree, linked


def disjoint_partitions(census):
    groups = census["groups"]
    result = {}
    for key, value in groups.items():
        if key == "/" or "/" in key:
            continue
        children = {k: v for k, v in groups.items() if k.startswith(key + "/")}
        result.update(children)
        residual = {field: value[field] - sum(v[field] for v in children.values())
                    for field in ("bytes", "files", "folders")}
        if any(v < 0 for v in residual.values()):
            raise ValueError("overlapping_inventory_groups")
        if any(residual.values()):
            result[key + "/@direct"] = residual
    if {f: sum(v[f] for v in result.values()) for f in ("bytes", "files", "folders")} != groups["/"]:
        raise ValueError("inventory_does_not_reconcile")
    return result


def backup_plan(census, output):
    """Metadata-only purge/archive candidates; no recursive delete or copying E."""
    root = Path(census["root"]).resolve(strict=True)
    protected = {"ai-engine-jobs", "workspace", "solo-system-20261115-04e2"}
    allowed = {"cargo-target", "rust-target", "api-target"}
    candidates = []
    for key, value in census["groups"].items():
        parts = key.split("/")
        if len(parts) != 2 or parts[0] in protected or parts[-1] not in allowed:
            continue
        target = root.joinpath(*parts)
        if linked(target) or not target.resolve().is_relative_to(root):
            continue
        files = verified_tree(root, target)
        manifest = [dict(relative=str(p.relative_to(target)), bytes=p.stat().st_size,
                         mtime_ns=p.stat().st_mtime_ns) for p in sorted(files)]
        digest = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
        candidates.append(dict(path=str(target), inventory=value, files=manifest,
            metadata_manifest_sha256=digest, action="DRY_RUN_ONLY_REBUILDABLE_BUILD_CACHE",
            content_hashes_verified=False, source_owner=parts[0],
            before_apply="Reconcile processes/worktrees; archive or prove rebuildability; revalidate metadata; never touch raw/research/VI/.git."))
    plan = dict(root=str(root), dry_run=True, candidates=candidates,
        potential_bytes=sum(r["inventory"]["bytes"] for r in candidates),
        potential_files=sum(r["inventory"]["files"] for r in candidates),
        exact_duplicates_not_proven=True, protected=sorted(protected),
        directory_names_are_not_delete_authority=True, executed=False)
    Path(output).write_text(json.dumps(plan, indent=2), encoding="utf-8")
    return {k: v for k, v in plan.items() if k != "candidates"}


def cold_zip(root, target, destination, *, remove=False):
    """Explicit cold derivative directory: SHA256 roundtrip; no raw or embedded Git."""
    root, target, destination = Path(root).resolve(strict=True), Path(target).absolute(), Path(destination).absolute()
    files = verified_tree(root, target)
    relative = target.relative_to(root).parts
    if not (".artifacts" in relative or relative[:3] == ("tooling", "ui-qa", "artifacts")):
        raise ValueError("cold_scope_not_admitted")
    if destination.exists() or destination.is_relative_to(target):
        raise ValueError("cold_archive_destination")
    if any(p.name == ".git" or ".git" in p.relative_to(target).parts for p in files):
        raise ValueError("cold_embedded_repository")
    manifest = {}
    for p in sorted(files):
        with p.open("rb") as f:
            manifest[p.relative_to(target).as_posix()] = dict(
                sha256=hashlib.file_digest(f, "sha256").hexdigest(), bytes=p.stat().st_size)
    payload = dict(source=str(target), files=manifest, format="ZIP_DEFLATED",
                   restoration_parent=str(target.parent), recursive_links_allowed=False)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for p in files:
            archive.write(p, arcname=target.name + "/" + p.relative_to(target).as_posix())
        archive.writestr("MANIFEST.json", json.dumps(payload, indent=2))
    with zipfile.ZipFile(destination) as archive:
        for name, row in manifest.items():
            with archive.open(target.name + "/" + name) as f:
                if hashlib.file_digest(f, "sha256").hexdigest() != row["sha256"]:
                    raise ValueError("cold_zip_roundtrip")
    current = verified_tree(root, target)
    if {p.relative_to(target).as_posix() for p in current} != set(manifest):
        raise ValueError("cold_tree_changed")
    for p in current:
        with p.open("rb") as f:
            if hashlib.file_digest(f, "sha256").hexdigest() != manifest[p.relative_to(target).as_posix()]["sha256"]:
                raise ValueError("cold_file_changed")
    if remove:
        shutil.rmtree(target)
    payload.update(archive=str(destination), archive_bytes=destination.stat().st_size,
        original_bytes=sum(r["bytes"] for r in manifest.values()), source_removed=remove)
    with destination.open("rb") as f:
        payload["archive_sha256"] = hashlib.file_digest(f, "sha256").hexdigest()
    destination.with_suffix(".MANIFEST.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def generated_dependencies(root, target):
    """Remove old UI QA node_modules without traversing package-manager links."""
    root, target = Path(root).resolve(strict=True), Path(target).absolute()
    if (not target.is_relative_to(root) or target.name != "node_modules" or
            target.relative_to(root).parts[:3] != ("tooling", "ui-qa", "artifacts")):
        raise ValueError("dependency_cleanup_scope")
    if linked(target):
        raise ValueError("dependency_root_reparse")
    for parent in target.parents:
        if parent == root:
            break
        if linked(parent):
            raise ValueError("dependency_ancestor_reparse")
    files, links, byte_count = 0, 0, 0
    for folder, dirs, names in os.walk(target, followlinks=False):
        for name in list(dirs):
            p = Path(folder) / name
            if linked(p):
                links += 1
                dirs.remove(name)
            elif name == ".git":
                raise ValueError("dependency_contains_repository")
        for name in names:
            p = Path(folder) / name
            if linked(p):
                links += 1
            else:
                files += 1
                byte_count += p.stat().st_size
    # Python >=3.8 rmtree removes junctions, without deleting their target contents.
    shutil.rmtree(target)
    return dict(path=str(target), files=files, bytes=byte_count, links_removed=links,
                external_link_targets_followed=False, generated_dependencies_only=True)


def apply_backup_plan(manifest, expected_sha256, backup_root, receipt, *, active_references=()):
    """Apply only a hash-bound, unchanged cache manifest explicitly approved by owner."""
    manifest, receipt = Path(manifest), Path(receipt)
    if receipt.exists() or receipt.with_suffix(".journal.jsonl").exists():
        raise ValueError("preserve_cleanup_attempt")
    raw = manifest.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError("cleanup_manifest_binding")
    plan = json.loads(raw)
    root = Path(backup_root).resolve(strict=True)
    if Path(plan["root"]).resolve(strict=True) != root or not plan["dry_run"]:
        raise ValueError("cleanup_root_binding")
    admitted = []
    protected_data = {".csv", ".parquet", ".bi5", ".qdm", ".npz", ".feather",
                      ".hcc", ".hc", ".hst", ".fxt", ".arrow"}
    for row in plan["candidates"]:
        target = Path(row["path"]).absolute()
        if (not target.is_relative_to(root) or len(target.relative_to(root).parts) != 2
                or target.name not in {"cargo-target", "rust-target", "api-target"}
                or target.relative_to(root).parts[0] in plan["protected"]):
            raise ValueError("cleanup_scope")
        if any(str(target).replace("/", "\\").lower() in str(ref).replace("/", "\\").lower()
               for ref in active_references):
            raise ValueError("cleanup_active_reference:" + str(target))
        files = verified_tree(root, target)
        actual = [dict(relative=str(p.relative_to(target)), bytes=p.stat().st_size,
                       mtime_ns=p.stat().st_mtime_ns) for p in sorted(files)]
        digest = hashlib.sha256(json.dumps(actual, sort_keys=True).encode()).hexdigest()
        if actual != row["files"] or digest != row["metadata_manifest_sha256"]:
            raise ValueError("cleanup_manifest_drift:" + str(target))
        if any(p.suffix.lower() in protected_data or ".git" in p.relative_to(target).parts
               or p.name in {"times.bin", "quotes.bin", "ticks.bin", "bars.bin"} for p in files):
            raise ValueError("cleanup_protected_data:" + str(target))
        folders = 1
        for _, dirs, _ in os.walk(target, followlinks=False):
            if ".git" in dirs:
                raise ValueError("cleanup_embedded_repository")
            folders += len(dirs)
        total = dict(bytes=sum(r["bytes"] for r in actual), files=len(actual), folders=folders)
        if total != row["inventory"]:
            raise ValueError("cleanup_inventory_drift:" + str(target))
        admitted.append(dict(path=str(target), **total))
    if len({r["path"].lower() for r in admitted}) != len(admitted):
        raise ValueError("cleanup_duplicate_target")
    journal = receipt.with_suffix(".journal.jsonl")
    result = dict(manifest=str(manifest), manifest_sha256=expected_sha256,
                  root=str(root), all_targets_preflighted=True, completed=[], executed=True)
    def event(value):
        with journal.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(value) + "\n")
    for row in admitted:
        event(dict(event="REMOVE_INTENT", **row))
        try:
            # Scope, resolved containment, links and exact manifest were checked above.
            shutil.rmtree(row["path"])
        except OSError as exc:
            result.update(passed=False, failure=dict(path=row["path"], error=type(exc).__name__),
                          partial_deletion_possible=True)
            receipt.write_text(json.dumps(result, indent=2), encoding="utf-8")
            raise
        result["completed"].append(row)
        event(dict(event="REMOVED", **row))
    result.update(passed=True, **{k:sum(r[k] for r in admitted) for k in ("bytes","files","folders")})
    receipt.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result

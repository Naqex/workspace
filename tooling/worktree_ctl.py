"""Isolated .worktrees/<name> manager for parallel subagents.

Safety invariants:
  - Strictly scoped to <repo_root>/.worktrees/<name> (blocks path traversal).
  - Verifies .gitattributes LF protection before creation and checks critical LF files after creation.
  - NEVER removes or prunes external worktrees (e.g. ~/.codex/worktrees/* or other drive checkouts).
  - Never executes git push.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKTREES_DIRNAME = ".worktrees"
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")

REQUIRED_LF_RULES: tuple[str, ...] = (
    "*.py text eol=lf",
    "*.mq5 text eol=lf",
    "*.csv text eol=lf",
    "*.json text eol=lf",
    "*.md text eol=lf",
)

CRITICAL_LF_FILES: tuple[str, ...] = (
    "tooling/ai-engines/exports/Naqex_Master_Prop7E.mq5",
    "tooling/ai-engines/exports/Files/naqex_red_news_utc.csv",
)


@dataclass(frozen=True)
class WorktreeRecord:
    path: str
    head: str
    branch: str
    scope: str  # "primary" | "managed" | "external"
    exists: bool
    prunable: bool
    locked: bool


def _norm(path: Path) -> Path:
    return path.resolve(strict=False)


def is_managed_worktree(path: Path, root: Path = ROOT) -> bool:
    """Return True iff `path` is strictly inside `<root>/.worktrees/`."""
    wt_root = _norm(root / WORKTREES_DIRNAME)
    target = _norm(path)
    return target != wt_root and target.is_relative_to(wt_root)


def validate_worktree_name(name: str) -> str:
    cleaned = name.strip()
    if not cleaned or cleaned in (".", "..") or not NAME_RE.fullmatch(cleaned):
        raise ValueError(
            f"Invalid worktree name {name!r}: must match ^[A-Za-z0-9][A-Za-z0-9._-]{{0,63}}$ with no path separators."
        )
    return cleaned


def verify_gitattributes_lf_guard(root: Path = ROOT) -> list[str]:
    """Return list of missing required LF protection rules in root .gitattributes."""
    attr_path = root / ".gitattributes"
    if not attr_path.is_file():
        return [f"Missing {attr_path}"]
    lines = {line.strip() for line in attr_path.read_text(encoding="utf-8", errors="replace").splitlines()}
    return [f"Missing LF rule in .gitattributes: {rule}" for rule in REQUIRED_LF_RULES if rule not in lines]


def verify_worktree_lf_integrity(worktree_path: Path) -> list[str]:
    """Verify critical LF-protected files inside a worktree contain zero CRLF bytes."""
    issues: list[str] = []
    for rel in CRITICAL_LF_FILES:
        candidate = worktree_path / rel
        if candidate.is_file():
            data = candidate.read_bytes()
            if b"\r\n" in data:
                issues.append(f"CRLF detected in LF-protected file: {rel}")
    return issues


def _run_git(args: list[str], *, root: Path = ROOT, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=check,
    )


def parse_worktree_porcelain(porcelain: str, root: Path = ROOT) -> list[WorktreeRecord]:
    """Parse `git worktree list --porcelain` into classified WorktreeRecord objects."""
    root_norm = _norm(root)
    records: list[WorktreeRecord] = []
    blocks = [b.strip() for b in porcelain.strip().split("\n\n") if b.strip()]
    for block in blocks:
        wt_path = ""
        head = ""
        branch = "(detached)"
        prunable = False
        locked = False
        for line in block.splitlines():
            if line.startswith("worktree "):
                wt_path = line[len("worktree ") :].strip()
            elif line.startswith("HEAD "):
                head = line[len("HEAD ") :].strip()
            elif line.startswith("branch "):
                branch = line[len("branch ") :].strip().removeprefix("refs/heads/")
            elif line.startswith("prunable"):
                prunable = True
            elif line.startswith("locked"):
                locked = True
        if not wt_path:
            continue
        p = Path(wt_path)
        p_norm = _norm(p)
        if p_norm == root_norm:
            scope = "primary"
        elif is_managed_worktree(p, root):
            scope = "managed"
        else:
            scope = "external"
        records.append(
            WorktreeRecord(
                path=wt_path.replace("\\", "/"),
                head=head,
                branch=branch,
                scope=scope,
                exists=p.exists(),
                prunable=prunable,
                locked=locked,
            )
        )
    return records


def list_worktrees(root: Path = ROOT) -> list[WorktreeRecord]:
    proc = _run_git(["worktree", "list", "--porcelain"], root=root)
    return parse_worktree_porcelain(proc.stdout, root=root)


def create_worktree(
    name: str,
    *,
    root: Path = ROOT,
    ref: str = "HEAD",
    branch: str | None = None,
    detach: bool = False,
) -> dict[str, object]:
    safe_name = validate_worktree_name(name)
    lf_errors = verify_gitattributes_lf_guard(root)
    if lf_errors:
        raise RuntimeError("LF guard failed before worktree creation: " + "; ".join(lf_errors))

    wt_root = root / WORKTREES_DIRNAME
    wt_root.mkdir(parents=True, exist_ok=True)
    target = wt_root / safe_name
    if not is_managed_worktree(target, root):
        raise ValueError(f"Refusing to create worktree outside {WORKTREES_DIRNAME}/: {target}")
    if target.exists():
        raise FileExistsError(f"Managed worktree path already exists: {target}")

    cmd = ["worktree", "add"]
    if detach:
        cmd.append("--detach")
    elif branch:
        cmd.extend(["-b", branch])
    else:
        cmd.append("--detach")
    cmd.extend([str(target), ref])

    proc = _run_git(cmd, root=root, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"git worktree add failed (rc={proc.returncode}): {(proc.stderr or proc.stdout).strip()}")

    crlf_issues = verify_worktree_lf_integrity(target)
    if crlf_issues:
        raise RuntimeError("LF integrity check failed inside newly created worktree: " + "; ".join(crlf_issues))

    return {
        "action": "create",
        "name": safe_name,
        "path": str(target.resolve()).replace("\\", "/"),
        "ref": ref,
        "branch": branch or "(detached)",
        "lf_guard_ok": True,
    }


def remove_worktree(name: str, *, root: Path = ROOT, force: bool = False) -> dict[str, object]:
    safe_name = validate_worktree_name(name)
    target = root / WORKTREES_DIRNAME / safe_name
    if not is_managed_worktree(target, root):
        raise ValueError(f"Refusing to remove non-managed worktree path: {target}")

    records = list_worktrees(root)
    target_norm = _norm(target)
    matched = [r for r in records if _norm(Path(r.path)) == target_norm]
    if not matched:
        raise FileNotFoundError(f"No registered managed worktree found at {target}")
    if matched[0].scope != "managed":
        raise PermissionError(f"Refusing to remove non-managed worktree ({matched[0].scope}): {target}")

    cmd = ["worktree", "remove"]
    if force:
        cmd.append("--force")
    cmd.append(str(target))
    proc = _run_git(cmd, root=root, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"git worktree remove failed (rc={proc.returncode}): {(proc.stderr or proc.stdout).strip()}")
    return {
        "action": "remove",
        "name": safe_name,
        "path": str(target_norm).replace("\\", "/"),
        "forced": force,
    }


def prune_managed_worktrees(*, root: Path = ROOT, dry_run: bool = False) -> dict[str, object]:
    """Prune ONLY stale git administrative entries whose target lives inside `<root>/.worktrees/`.

    External worktrees (outside `.worktrees/`) are strictly preserved and NEVER touched,
    even if their drive/directory is currently unmounted.
    """
    records = list_worktrees(root)
    external_protected = [r.path for r in records if r.scope == "external"]
    stale_managed = [r for r in records if r.scope == "managed" and (r.prunable or not r.exists)]

    git_dir_proc = _run_git(["rev-parse", "--git-common-dir"], root=root)
    git_common = Path(git_dir_proc.stdout.strip())
    if not git_common.is_absolute():
        git_common = (root / git_common).resolve()
    admin_root = git_common / "worktrees"

    pruned_admin: list[str] = []
    locked_skipped: list[str] = []
    skipped_external: list[str] = []
    if admin_root.is_dir():
        for entry in sorted(admin_root.iterdir()):
            if not entry.is_dir():
                continue
            gitdir_file = entry / "gitdir"
            if not gitdir_file.is_file():
                continue
            raw_target = gitdir_file.read_text(encoding="utf-8", errors="replace").strip()
            raw_path = Path(raw_target)
            if not raw_path.is_absolute():
                raw_path = (entry / raw_path).resolve(strict=False)
            wt_path = raw_path.parent if raw_path.name == ".git" else raw_path
            if not is_managed_worktree(wt_path, root):
                skipped_external.append(str(wt_path).replace("\\", "/"))
                continue
            if (entry / "locked").exists():
                locked_skipped.append(entry.name)
                continue
            if not wt_path.exists():
                pruned_admin.append(entry.name)
                if not dry_run:
                    shutil.rmtree(entry)

    return {
        "action": "prune",
        "dry_run": dry_run,
        "stale_managed_reported": [r.path for r in stale_managed],
        "pruned_managed_entries": pruned_admin,
        "locked_managed_skipped": locked_skipped,
        "external_worktrees_protected": sorted(set(external_protected) | set(skipped_external)),
    }


def main(argv: list[str] | None = None) -> int:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--root", type=Path, default=argparse.SUPPRESS, help="Repository root (default: workspace root)"
    )
    common.add_argument(
        "--json", action="store_true", dest="as_json", default=argparse.SUPPRESS, help="Emit JSON output"
    )

    parser = argparse.ArgumentParser(
        description="Manage isolated .worktrees/<name> checkouts while protecting LF and external worktrees."
    )
    parser.add_argument("--root", type=Path, default=ROOT, help="Repository root (default: workspace root)")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Emit JSON output")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", parents=[common], help="List all worktrees classified as primary, managed, or external")

    p_create = sub.add_parser("create", parents=[common], help="Create a new managed worktree under .worktrees/<name>")
    p_create.add_argument("name", help="Worktree directory name under .worktrees/")
    p_create.add_argument("--ref", default="HEAD", help="Git ref/commit to check out (default: HEAD)")
    p_create.add_argument("--branch", default=None, help="Create and checkout a new branch name")
    p_create.add_argument("--detach", action="store_true", help="Check out detached HEAD")

    p_remove = sub.add_parser("remove", parents=[common], help="Remove a managed worktree under .worktrees/<name>")
    p_remove.add_argument("name", help="Managed worktree name")
    p_remove.add_argument("--force", action="store_true", help="Force removal even if dirty")

    p_prune = sub.add_parser(
        "prune", parents=[common], help="Prune stale managed .worktrees/* entries (never external worktrees)"
    )
    p_prune.add_argument("--dry-run", action="store_true", help="Report what would be pruned without deleting")

    args = parser.parse_args(argv)
    root = args.root.resolve()

    try:
        if args.cmd == "list":
            recs = list_worktrees(root)
            payload: object = {"root": str(root).replace("\\", "/"), "worktrees": [asdict(r) for r in recs]}
            if args.as_json:
                print(json.dumps(payload, indent=2))
            else:
                for r in recs:
                    status = "ok" if r.exists else "missing"
                    if r.prunable:
                        status = "prunable"
                    print(f"[{r.scope:<8}] {r.branch:<34} {r.head[:8]} ({status}) {r.path}")
            return 0

        if args.cmd == "create":
            res = create_worktree(args.name, root=root, ref=args.ref, branch=args.branch, detach=args.detach)
        elif args.cmd == "remove":
            res = remove_worktree(args.name, root=root, force=args.force)
        elif args.cmd == "prune":
            res = prune_managed_worktrees(root=root, dry_run=args.dry_run)
        else:
            parser.error(f"Unknown command: {args.cmd}")
            return 2

        if args.as_json:
            print(json.dumps(res, indent=2))
        else:
            print(json.dumps(res, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

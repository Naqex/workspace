"""Non-destructive Git `post-commit` hook installer for Naqex Automation (OrderSend = 0).

Uses `git rev-parse --git-path hooks` so it works cleanly in BOTH main repositories
and Git worktrees, appending commit metadata to `.runtime/automation/event_queue.jsonl`
WITHOUT clobbering `.pre-commit-config.yaml` or any existing hook logic.

Supports:
  - `--status`    Read-only inspection of current hook state
  - `--dry-run`   Preview planned non-destructive changes without modifying disk
  - `--install`   Install/update idempotent managed block in `post-commit`
  - `--uninstall` Remove ONLY the managed block while preserving existing hook lines
"""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ORDER_SEND_CAPABLE: bool = False
ORDER_SEND_COUNT: int = 0
SCHEMA_VERSION: str = "naqex-git-hooks-v1"
MARKER_START: str = "# >>> NAQEX_AUTOMATION_POST_COMMIT_START >>>"
MARKER_END: str = "# <<< NAQEX_AUTOMATION_POST_COMMIT_END <<<"

ROOT = Path(__file__).resolve().parents[2]
_WIN_USER_RE = re.compile(
    r"(?i)(?:[A-Z]:|/mnt/[a-z])[\\/]Users[\\/](?!<|YOUR_|user\b|username\b|example\b|public\b|default\b)[A-Za-z0-9._-]+"
)


def _utc_now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_path_display(path: Path, repo_root: Path) -> str:
    """Display workspace-relative path when inside repo_root, scrubbing any local user home."""
    try:
        rel = path.resolve().relative_to(repo_root.resolve()).as_posix()
        return _WIN_USER_RE.sub("<USER_HOME>", rel)
    except Exception:
        return _WIN_USER_RE.sub("<USER_HOME>", path.as_posix())


def resolve_hooks_dir(repo_root: Path) -> Path:
    """Resolve the active Git hooks directory using `git rev-parse --git-path hooks`."""
    proc = subprocess.run(
        ["git", "rev-parse", "--git-path", "hooks"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=5.0,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if proc.returncode != 0:
        err = _WIN_USER_RE.sub("<USER_HOME>", (proc.stderr or "").strip())
        raise RuntimeError(f"git rev-parse --git-path hooks failed (rc={proc.returncode}): {err}")
    raw = (proc.stdout or "").strip()
    if not raw:
        raise RuntimeError("git rev-parse --git-path hooks returned an empty path")
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = (repo_root / candidate).resolve()
    return candidate


def build_post_commit_block() -> str:
    """Build lightweight, fail-open, secret-scrubbed POSIX sh post-commit block."""
    lines = [
        MARKER_START,
        "# Lightweight non-destructive Naqex event queue logger (OrderSend=0; never blocks git commit).",
        "(",
        '  NAQEX_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd -W 2>/dev/null || pwd)"',
        "  export NAQEX_ROOT",
        '  NAQEX_PY="$NAQEX_ROOT/.runtime/quant-audit-v24/Scripts/python.exe"',
        '  if [ ! -f "$NAQEX_PY" ]; then',
        '    NAQEX_PY="$(command -v python3 2>/dev/null || command -v python 2>/dev/null || true)"',
        "  fi",
        '  if [ -n "$NAQEX_PY" ]; then',
        '    "$NAQEX_PY" -X utf8 - "$NAQEX_ROOT" >/dev/null 2>&1 <<\'__NAQEX_POST_COMMIT_PY__\' || true',
        "import datetime, json, os, pathlib, re, subprocess, sys",
        "root = pathlib.Path(sys.argv[1]).resolve()",
        "sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()",
        "br = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], cwd=root, text=True).strip()",
        "subj = subprocess.check_output(['git', 'log', '-1', '--format=%s'], cwd=root, text=True).strip()[:160]",
        "def _scrub(s):",
        "    s = re.sub(r'https?://[^\\s\\x27\"<>]+', '<REDACTED_URL>', s)",
        "    s = re.sub(r'(?:bot)?\\b\\d{6,}:[A-Za-z0-9_-]{10,}\\b', '<REDACTED_TOKEN>', s)",
        "    s = re.sub(",
        "        r'(?i)([?&]|\\b)((?:token|api[_-]?key|secret|password)=)[^\\s&\\x27\"<>]+',",
        "        r'\\1\\2<REDACTED>', s)",
        "    gh_rx = r'\\b(?:' + 'ghp' + r'_[A-Za-z0-9]{20,}|' + 'github_pat' + r'_[A-Za-z0-9_]{20,})\\b'",
        "    s = re.sub(gh_rx, '<REDACTED>', s)",
        "    s = re.sub(r'\\b(?:192' + r'\\.168|10\\.\\d{1,3})\\.\\d{1,3}\\.\\d{1,3}\\b', '<LAN_IP>', s)",
        "    ts_rx = r'\\b100' + r'\\.(?:6[4-9]|[7-9]\\d|1[01]\\d|12[0-7])\\.\\d{1,3}\\.\\d{1,3}\\b'",
        "    s = re.sub(ts_rx, '<TAILSCALE_IP>', s)",
        "    usr_rx = (",
        "        r'(?i)(?:[A-Z]:|/mnt/[a-z])[\\\\/]Users[\\\\/]'",
        "        r'(?!<|YOUR_|user\\b|username\\b|example\\b|public\\b|default\\b)[A-Za-z0-9._-]+'",
        "    )",
        "    s = re.sub(usr_rx, '<USER_HOME>', s)",
        "    return s",
        "subj = _scrub(subj)",
        "br = _scrub(br)",
        "ts = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')",
        "details = {'repo': root.name, 'branch': br, 'commit_sha': sha, 'short_sha': sha[:12], 'subject': subj}",
        "summary = f'{root.name}@{br} {sha[:12]}: {subj}'",
        "q = root / '.runtime' / 'automation' / 'event_queue.jsonl'",
        "queued = False",
        "try:",
        "    if str(root) not in sys.path:",
        "        sys.path.insert(0, str(root))",
        "    from tooling.automation.event_queue import EventQueue",
        "    EventQueue(path=q).append(",
        "        'git_post_commit', source='git_post_commit_hook', severity='info',",
        "        status='recorded', summary=summary, details=details, ts_utc=ts,",
        "    )",
        "    queued = True",
        "except Exception:",
        "    queued = False",
        "if not queued:",
        "    ev = {'schema_version': 'naqex-automation-event-v1', 'event_type': 'git_post_commit',",
        "          'source': 'git_post_commit_hook', 'severity': 'info', 'status': 'recorded',",
        "          'summary': summary, 'details': details, 'ts_utc': ts, 'order_send_count': 0}",
        "    q.parent.mkdir(parents=True, exist_ok=True)",
        "    line = (json.dumps(ev, ensure_ascii=False, sort_keys=True, allow_nan=False) + '\\n').encode('utf-8')",
        "    fd = os.open(str(q), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)",
        "    try:",
        "        os.write(fd, line)",
        "        os.fsync(fd)",
        "    finally:",
        "        os.close(fd)",
        "__NAQEX_POST_COMMIT_PY__",
        "  fi",
        ") || true",
        MARKER_END,
    ]
    return "\n".join(lines)


def merge_hook_content(existing: str | None, block: str) -> tuple[str, str]:
    """Non-destructively insert or update the managed block without clobbering existing content."""
    clean_block = block.replace("\r\n", "\n").strip("\n")
    if existing is None or not existing.strip():
        return f"#!/bin/sh\n\n{clean_block}\n", "CREATE_NEW"

    norm = existing.replace("\r\n", "\n")
    start_idx = norm.find(MARKER_START)
    end_idx = norm.find(MARKER_END)
    if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
        end_after = end_idx + len(MARKER_END)
        merged = norm[:start_idx] + clean_block + norm[end_after:]
        if not merged.endswith("\n"):
            merged += "\n"
        return merged, "UPDATE_MANAGED_BLOCK"

    base = norm.rstrip("\n")
    merged = f"{base}\n\n{clean_block}\n"
    return merged, "APPEND_NON_DESTRUCTIVE"


def remove_hook_block(existing: str) -> tuple[str | None, str]:
    """Remove ONLY the managed block while preserving any user/pre-existing hook lines."""
    norm = existing.replace("\r\n", "\n")
    start_idx = norm.find(MARKER_START)
    end_idx = norm.find(MARKER_END)
    if start_idx == -1 or end_idx == -1 or start_idx >= end_idx:
        return norm, "NOT_INSTALLED"

    end_after = end_idx + len(MARKER_END)
    before = norm[:start_idx].rstrip("\n")
    after = norm[end_after:].lstrip("\n")
    if before and after:
        remaining = f"{before}\n\n{after}"
    else:
        remaining = before or after
    remaining = remaining.strip()
    if not remaining or remaining in {"#!/bin/sh", "#!/usr/bin/env sh", "#!/bin/bash"}:
        return None, "REMOVE_EMPTY_HOOK_FILE"
    return remaining + "\n", "STRIP_MANAGED_BLOCK_ONLY"


def _has_external_content(existing: str | None) -> bool:
    if not existing:
        return False
    cleaned, _ = remove_hook_block(existing)
    if cleaned is None:
        return False
    meaningful = [line.strip() for line in cleaned.splitlines() if line.strip() and not line.strip().startswith("#!")]
    return len(meaningful) > 0


def _atomic_write_text_executable(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
            tmp = Path(fh.name)
        try:
            mode = tmp.stat().st_mode
            os.chmod(tmp, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        except OSError:
            pass
        os.replace(tmp, path)
        tmp = None
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)


def inspect_hook_status(repo_root: Path) -> dict[str, Any]:
    """Read-only status inspection of Git hooks and `.pre-commit-config.yaml`."""
    hooks_dir = resolve_hooks_dir(repo_root)
    post_commit = hooks_dir / "post-commit"
    pre_commit_hook = hooks_dir / "pre-commit"
    pre_commit_cfg = repo_root / ".pre-commit-config.yaml"

    existing: str | None = None
    if post_commit.is_file():
        existing = post_commit.read_text(encoding="utf-8", errors="replace")

    installed = bool(existing and MARKER_START in existing and MARKER_END in existing)
    return {
        "schema": SCHEMA_VERSION,
        "checked_utc": _utc_now_iso(),
        "order_send_count": ORDER_SEND_COUNT,
        "repo_name": repo_root.resolve().name,
        "hooks_dir": _safe_path_display(hooks_dir, repo_root),
        "post_commit_path": _safe_path_display(post_commit, repo_root),
        "post_commit_exists": post_commit.is_file(),
        "installed": installed,
        "existing_custom_content": _has_external_content(existing),
        "pre_commit_config_present": pre_commit_cfg.is_file(),
        "pre_commit_hook_present": pre_commit_hook.is_file(),
        "pre_commit_untouched": True,
    }


def install_post_commit_hook(repo_root: Path, *, dry_run: bool = False) -> dict[str, Any]:
    """Install or update the managed `post-commit` hook block non-destructively."""
    status = inspect_hook_status(repo_root)
    hooks_dir = resolve_hooks_dir(repo_root)
    post_commit = hooks_dir / "post-commit"
    existing = post_commit.read_text(encoding="utf-8", errors="replace") if post_commit.is_file() else None

    block = build_post_commit_block()
    merged, action = merge_hook_content(existing, block)

    if not dry_run:
        _atomic_write_text_executable(post_commit, merged)

    status.update(
        {
            "mode": "DRY_RUN" if dry_run else "INSTALL",
            "dry_run": dry_run,
            "action": f"DRYRUN_{action}" if dry_run else action,
            "written": not dry_run,
            "installed": status["installed"] if dry_run else True,
            "hook_bytes": len(merged.encode("utf-8")),
        }
    )
    return status


def uninstall_post_commit_hook(repo_root: Path, *, dry_run: bool = False) -> dict[str, Any]:
    """Remove ONLY the managed `post-commit` block, preserving any other hook logic."""
    status = inspect_hook_status(repo_root)
    hooks_dir = resolve_hooks_dir(repo_root)
    post_commit = hooks_dir / "post-commit"
    if not post_commit.is_file():
        status.update({"mode": "UNINSTALL", "dry_run": dry_run, "action": "NOT_INSTALLED", "written": False})
        return status

    existing = post_commit.read_text(encoding="utf-8", errors="replace")
    cleaned, action = remove_hook_block(existing)
    if not dry_run and action != "NOT_INSTALLED":
        if cleaned is None:
            post_commit.unlink(missing_ok=True)
        else:
            _atomic_write_text_executable(post_commit, cleaned)

    status.update(
        {
            "mode": "DRY_RUN_UNINSTALL" if dry_run else "UNINSTALL",
            "dry_run": dry_run,
            "action": f"DRYRUN_{action}" if dry_run else action,
            "written": (not dry_run) and (action != "NOT_INSTALLED"),
            "installed": status["installed"] if dry_run else False,
        }
    )
    return status


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Non-destructive Git post-commit hook installer (worktree-safe, OrderSend = 0)."
    )
    ap.add_argument("--root", "--repo", dest="repo_root", type=Path, default=ROOT, help="Target Git repository root")
    ap.add_argument("--status", action="store_true", help="Inspect current hook installation status (read-only)")
    ap.add_argument("--install", action="store_true", help="Install/update managed post-commit hook block")
    ap.add_argument("--uninstall", action="store_true", help="Remove ONLY the managed post-commit hook block")
    ap.add_argument("--dry-run", action="store_true", help="Preview action without writing to disk")
    ap.add_argument("--offline", action="store_true", help="Accepted no-op flag (always 100%% offline)")
    ap.add_argument("--json", action="store_true", dest="as_json", help="Emit JSON output (default)")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo_root = args.repo_root.resolve()

    if args.uninstall:
        result = uninstall_post_commit_hook(repo_root, dry_run=bool(args.dry_run))
    elif args.status:
        result = inspect_hook_status(repo_root)
        result["mode"] = "STATUS"
        result["dry_run"] = bool(args.dry_run)
        result["written"] = False
    elif args.install or args.dry_run:
        # When `--dry-run` is passed (alone or with `--install`), preview safely with zero disk writes.
        result = install_post_commit_hook(repo_root, dry_run=bool(args.dry_run) or not bool(args.install))
    else:
        result = inspect_hook_status(repo_root)
        result["mode"] = "STATUS"
        result["dry_run"] = False
        result["written"] = False

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

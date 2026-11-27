"""Concurrent read-only GitHub Actions self-healing CI scanner (OrderSend = 0).

Scans GitHub Actions workflow runs across the 4 Naqex repositories concurrently
within a strict <= 3.0s budget, classifies failures with deterministic heuristics,
enforces a strict Circuit Breaker (max 3 attempts; 4th consecutive failure trips
HARD to CIRCUIT_OPEN_ESCALATE_OWNER), and appends sanitized events to
`.runtime/automation/event_queue.jsonl`.

Safety invariants:
  - ORDER_SEND_CAPABLE = False / ORDER_SEND_COUNT = 0
  - Supports `--offline` and `--dry-run` for 100% CI safety
  - Zero bare `assert` guards (safe under `python -O`)
  - Zero raw IPs, usernames, tokens, or unredacted URLs in logs/JSON/stdout
"""

from __future__ import annotations

import argparse
import inspect
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import wait as futures_wait
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ORDER_SEND_CAPABLE: bool = False
ORDER_SEND_COUNT: int = 0
SCHEMA_VERSION: str = "naqex-self-healing-ci-v1"
DEFAULT_REPOS: tuple[str, ...] = (
    "Naqex/workspace",
    "Naqex/trader",
    "Naqex/quant-trading",
    "Naqex/vi-dubber",
)
DEFAULT_MAX_ATTEMPTS: int = 3
DEFAULT_BUDGET_SEC: float = 3.0
FAILING_CONCLUSIONS: frozenset[str] = frozenset({"failure", "timed_out", "startup_failure", "action_required"})

ROOT = Path(__file__).resolve().parents[2]
_AI_ENGINES_DIR = ROOT / "tooling/ai-engines"
if str(_AI_ENGINES_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_ENGINES_DIR))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from ops_cloud.heroku_deadman.app import _scrub_secret_text as _base_scrub_secret_text
except Exception:  # pragma: no cover - fallback when run standalone outside workspace
    _base_scrub_secret_text = None

_SAFE_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_URL_RE = re.compile(r"https?://[^\s'\"<>]+")
_TG_TOKEN_RE = re.compile(r"(?:bot)?\b\d{6,}:[A-Za-z0-9_-]{10,}\b")
_KV_SECRET_RE = re.compile(r"(?i)([?&]|\b)((?:token|api[_-]?key|secret)=)[^\s&'\"<>]+")
_BEARER_RE = re.compile(r"(?i)(Bearer\s+)[^\s'\"<>]+")
_GH_TOKEN_RE = re.compile(r"\b(?:" + "ghp_" + r"[A-Za-z0-9]{20,}|" + "github_pat_" + r"[A-Za-z0-9_]{20,})\b")
_LAN_IP_RE = re.compile(r"\b(?:192" + r"\.168|10\.\d{1,3})\.\d{1,3}\.\d{1,3}\b")
_CGNAT_IP_RE = re.compile(r"\b100" + r"\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d{1,3}\.\d{1,3}\b")
_HEROKU_APP_RE = re.compile(r"(?i)\b" + "naqex-" + "deadman-" + r"[a-z0-9-]+\b")
_TG_HANDLE_RE = re.compile(r"(?i)@?" + "naqex_" + "guard_" + r"bot\b")
_WIN_USER_RE = re.compile(
    r"(?i)(?:[A-Z]:|/mnt/[a-z])[\\/]Users[\\/](?!<|YOUR_|user\b|username\b|example\b|public\b|default\b)[A-Za-z0-9._-]+"
)


def sanitize_text(raw: Any, *, secrets: tuple[str, ...] = ()) -> str:
    """Scrub secrets, raw URLs, private IPs, app names, and local user paths."""
    text = str(raw or "")
    if _base_scrub_secret_text is not None:
        text = _base_scrub_secret_text(text, secrets=secrets)
    else:
        for sec in sorted({str(s or "").strip() for s in secrets if str(s or "").strip()}, key=len, reverse=True):
            text = text.replace(sec, "<REDACTED>")
        text = _URL_RE.sub("<REDACTED_URL>", text)
        text = _TG_TOKEN_RE.sub("<REDACTED_TOKEN>", text)
        text = _KV_SECRET_RE.sub(r"\1\2<REDACTED>", text)
        text = _BEARER_RE.sub(r"\1<REDACTED>", text)
    text = _GH_TOKEN_RE.sub("<REDACTED_GH_TOKEN>", text)
    text = _LAN_IP_RE.sub("<LAN_IP>", text)
    text = _CGNAT_IP_RE.sub("<TAILSCALE_IP>", text)
    text = _HEROKU_APP_RE.sub("<HEROKU_DEADMAN_APP>", text)
    text = _TG_HANDLE_RE.sub("<TELEGRAM_GUARD_BOT>", text)
    text = _WIN_USER_RE.sub(r"<USER_HOME>", text)
    return text


def sanitize_obj(obj: Any, *, secrets: tuple[str, ...] = ()) -> Any:
    """Recursively scrub every string in a JSON-serializable object."""
    if isinstance(obj, str):
        return sanitize_text(obj, secrets=secrets)
    if isinstance(obj, dict):
        return {str(k): sanitize_obj(v, secrets=secrets) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize_obj(v, secrets=secrets) for v in obj]
    if isinstance(obj, tuple):
        return [sanitize_obj(v, secrets=secrets) for v in obj]
    return obj


def _utc_now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
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
        os.replace(tmp, path)
        tmp = None
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)


def _safe_read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def classify_ci_failure(
    workflow_name: str,
    *,
    title: str = "",
    conclusion: str = "failure",
    details: str = "",
) -> dict[str, Any]:
    """Deterministically classify a failing CI run into an actionable category."""
    wf_clean = sanitize_text(workflow_name).strip() or "unknown-workflow"
    haystack = " ".join(
        part.lower() for part in (wf_clean, sanitize_text(title), str(conclusion or ""), sanitize_text(details)) if part
    )

    rules: tuple[tuple[str, str, bool, str, tuple[str, ...]], ...] = (
        (
            "OPSEC_OR_ARCHITECTURE_GATE",
            "CRITICAL",
            False,
            "ESCALATE_OWNER_SECURITY_OR_ARCH_GATE",
            ("opsec", "gitleaks", "secret", "holdout", "check_architecture", "arch-"),
        ),
        (
            "LINT_OR_FORMAT",
            "MEDIUM",
            True,
            "RUN_OFFLINE_RUFF_CHECK_AND_FORMAT_DIAGNOSTIC",
            ("ruff", "lint", "format", "flake8", "black", "pre-commit", "crlf"),
        ),
        (
            "TYPE_CHECK",
            "MEDIUM",
            True,
            "INSPECT_TY_OR_MYPY_DIAGNOSTICS",
            ("ty check", "mypy", "pyright", "typecheck", "type-check", "typing"),
        ),
        (
            "UNIT_TEST_FAILURE",
            "HIGH",
            True,
            "REPRODUCE_FAILING_TESTS_IN_OFFLINE_MODE",
            ("pytest", "unittest", "test", "suite", "regression", "spec"),
        ),
        (
            "DEPENDENCY_OR_BUILD",
            "HIGH",
            False,
            "AUDIT_LOCKFILE_AND_BUILD_ENVIRONMENT",
            ("lockfile", "dependency", "requirements", "pyproject", "pip", "wheel", "compile", "build", "uv "),
        ),
        (
            "INFRA_TIMEOUT_OR_RUNNER",
            "LOW",
            True,
            "RECHECK_GITHUB_RUNNER_TRANSIENT_FAILURE",
            ("timed_out", "timeout", "runner", "rate limit", "network", "502", "503", "transient"),
        ),
    )

    for category, severity, auto_healable, action, keywords in rules:
        if any(kw in haystack for kw in keywords):
            sig = f"{category}:{wf_clean.lower()}"
            return {
                "category": category,
                "severity": severity,
                "auto_healable": auto_healable,
                "suggested_action": action,
                "signature": sig,
            }

    return {
        "category": "UNKNOWN_CI_FAILURE",
        "severity": "HIGH",
        "auto_healable": False,
        "suggested_action": "MANUAL_TRIAGE_REQUIRED",
        "signature": f"UNKNOWN_CI_FAILURE:{wf_clean.lower()}",
    }


def evaluate_circuit_breaker(
    state: dict[str, Any],
    key: str,
    *,
    failed: bool,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    now_utc: str | None = None,
) -> dict[str, Any]:
    """Enforce strict Circuit Breaker (max_attempts=3; attempt #4 trips HARD)."""
    if isinstance(max_attempts, bool) or not isinstance(max_attempts, int) or max_attempts < 1:
        raise ValueError(f"max_attempts must be a positive int, got {max_attempts!r}")
    ts = now_utc or _utc_now_iso()
    breakers = state.setdefault("circuit_breakers", {})
    if not isinstance(breakers, dict):
        breakers = {}
        state["circuit_breakers"] = breakers

    rec = breakers.get(key)
    if not isinstance(rec, dict):
        rec = {"attempts": 0, "state": "CLOSED", "last_updated_utc": ts}

    if not failed:
        updated = {
            "attempts": 0,
            "max_attempts": max_attempts,
            "state": "CLOSED",
            "allow_attempt": True,
            "escalate_owner": False,
            "last_updated_utc": ts,
        }
        breakers[key] = updated
        return dict(updated)

    attempts = int(rec.get("attempts", 0)) + 1
    tripped = attempts > max_attempts
    updated = {
        "attempts": attempts,
        "max_attempts": max_attempts,
        "state": "CIRCUIT_OPEN_ESCALATE_OWNER" if tripped else "CLOSED",
        "allow_attempt": not tripped,
        "escalate_owner": tripped,
        "last_updated_utc": ts,
    }
    breakers[key] = updated
    return dict(updated)


def append_queue_event(
    queue_path: Path,
    event: dict[str, Any],
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Append a scrubbed event to `.runtime/automation/event_queue.jsonl` (reusing event_queue.py if available)."""
    clean_event = sanitize_obj(event)
    if not isinstance(clean_event, dict):
        raise ValueError("Event payload must be a mapping")
    clean_event["order_send_count"] = ORDER_SEND_COUNT
    clean_event.setdefault("ts_utc", _utc_now_iso())

    if dry_run:
        return {
            "queued": False,
            "dry_run": True,
            "backend": "DRY_RUN",
            "event": clean_event,
        }

    # Try H1's shared `tooling.automation.event_queue.EventQueue` interface first if available.
    try:
        from tooling.automation import event_queue as eq_mod  # type: ignore[import-not-found]

        eq_cls = getattr(eq_mod, "EventQueue", None)
        if callable(eq_cls):
            sev_map = {
                "CRITICAL": "critical",
                "HIGH": "error",
                "MEDIUM": "warning",
                "LOW": "info",
            }
            raw_sev = str(clean_event.get("severity") or "info").upper()
            norm_sev = sev_map.get(raw_sev, raw_sev.lower())
            if norm_sev not in {"debug", "info", "warning", "error", "critical"}:
                norm_sev = "info"
            queue = eq_cls(path=queue_path)
            recorded = queue.append(
                str(clean_event.get("event_type") or "ci_event"),
                source=str(clean_event.get("source") or "self_healing_ci"),
                severity=norm_sev,
                status=str(clean_event.get("circuit_state") or clean_event.get("status") or "recorded"),
                summary=str(
                    clean_event.get("summary")
                    or f"{clean_event.get('repo', 'unknown')}:{clean_event.get('category', 'event')}"
                ),
                details=clean_event,
                ts_utc=str(clean_event.get("ts_utc") or _utc_now_iso()),
            )
            return {
                "queued": True,
                "dry_run": False,
                "backend": "event_queue.EventQueue",
                "event": recorded,
            }

        append_fn = getattr(eq_mod, "append_event", None)
        if callable(append_fn):
            sig = inspect.signature(append_fn)
            params = list(sig.parameters.keys())
            if "queue_path" in params:
                append_fn(clean_event, queue_path=queue_path)
            elif "path" in params:
                append_fn(clean_event, path=queue_path)
            elif len(params) >= 2:
                append_fn(queue_path, clean_event)
            else:
                append_fn(clean_event)
            return {"queued": True, "dry_run": False, "backend": "event_queue.append_event", "event": clean_event}
    except Exception:
        pass

    queue_path.parent.mkdir(parents=True, exist_ok=True)
    line = (json.dumps(clean_event, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    fd = os.open(str(queue_path), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        os.write(fd, line)
        os.fsync(fd)
    finally:
        os.close(fd)
    return {"queued": True, "dry_run": False, "backend": "atomic_jsonl_fallback", "event": clean_event}


def _fetch_runs_via_gh(repo: str, timeout_sec: float) -> list[dict[str, Any]]:
    gh_bin = shutil.which("gh")
    if not gh_bin:
        raise FileNotFoundError("gh CLI not found on PATH")
    proc = subprocess.run(
        [
            gh_bin,
            "run",
            "list",
            "--repo",
            repo,
            "--limit",
            "5",
            "--json",
            "databaseId,workflowName,status,conclusion,headBranch,createdAt,displayTitle",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=max(0.5, min(timeout_sec, 2.5)),
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if proc.returncode != 0:
        raise RuntimeError(f"gh_rc={proc.returncode}:{sanitize_text(proc.stderr.strip())[:160]}")
    raw = json.loads(proc.stdout.strip() or "[]")
    if not isinstance(raw, list):
        raise ValueError("Unexpected gh run list payload")
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        out.append(
            {
                "run_id": item.get("databaseId"),
                "workflow": sanitize_text(item.get("workflowName") or ""),
                "status": str(item.get("status") or ""),
                "conclusion": str(item.get("conclusion") or ""),
                "branch": sanitize_text(item.get("headBranch") or ""),
                "created_utc": str(item.get("createdAt") or ""),
                "title": sanitize_text(item.get("displayTitle") or "")[:120],
            }
        )
    return out


def _fetch_runs_via_rest(repo: str, timeout_sec: float) -> list[dict[str, Any]]:
    token = (os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or "").strip()
    url = f"https://api.github.com/repos/{repo}/actions/runs?per_page=5"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "Naqex-SelfHealing-CI/1.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=max(0.5, min(timeout_sec, 2.5))) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        raise RuntimeError(sanitize_text(str(exc), secrets=(token, url))[:180]) from exc

    raw_runs = data.get("workflow_runs") if isinstance(data, dict) else []
    if not isinstance(raw_runs, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw_runs:
        if not isinstance(item, dict):
            continue
        out.append(
            {
                "run_id": item.get("id"),
                "workflow": sanitize_text(item.get("name") or ""),
                "status": str(item.get("status") or ""),
                "conclusion": str(item.get("conclusion") or ""),
                "branch": sanitize_text(item.get("head_branch") or ""),
                "created_utc": str(item.get("created_at") or ""),
                "title": sanitize_text(item.get("display_title") or "")[:120],
            }
        )
    return out


def _validate_repo_slug(repo: str) -> str:
    """Validate GitHub `owner/repo` slug and reject path-traversal or dot segments."""
    slug = str(repo or "").strip()
    if not _SAFE_REPO_RE.fullmatch(slug):
        raise ValueError(f"Invalid GitHub repository slug: {repo!r}")
    owner, name = slug.split("/", 1)
    for seg in (owner, name):
        if seg in {".", ".."} or ".." in seg or seg.startswith(".") or seg.endswith("."):
            raise ValueError(f"Unsafe GitHub repository slug segment: {repo!r}")
    return slug


def _validate_positive_finite(val: float, *, name: str) -> float:
    if isinstance(val, bool) or not isinstance(val, (int, float)) or not math.isfinite(val) or val <= 0:
        raise ValueError(f"{name} must be a finite number > 0, got {val!r}")
    return float(val)


def scan_single_repo(
    repo: str,
    *,
    offline: bool = False,
    timeout_sec: float = 2.4,
    fetcher: Callable[[str, float], list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Scan GitHub Actions status for one repository (read-only, scrubbed)."""
    repo_clean = _validate_repo_slug(repo)
    budget = _validate_positive_finite(timeout_sec, name="timeout_sec")

    t0 = time.perf_counter()
    deadline = t0 + budget
    if offline:
        return {
            "repo": repo_clean,
            "status": "OFFLINE_SKIPPED",
            "source": "OFFLINE",
            "runs_checked": 0,
            "failing_runs": [],
            "error": None,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 1),
        }

    runs: list[dict[str, Any]] = []
    source = "CUSTOM"
    err_msg: str | None = None
    try:
        if fetcher is not None:
            runs = fetcher(repo_clean, budget)
        else:
            try:
                source = "GH_CLI"
                runs = _fetch_runs_via_gh(repo_clean, budget)
            except Exception as gh_exc:
                remaining = deadline - time.perf_counter()
                if remaining < 0.2:
                    err_msg = sanitize_text(f"gh:{gh_exc}; rest:skipped_low_budget({remaining:.2f}s)")[:200]
                else:
                    source = "GITHUB_REST"
                    try:
                        runs = _fetch_runs_via_rest(repo_clean, remaining)
                    except Exception as rest_exc:
                        err_msg = sanitize_text(f"gh:{gh_exc}; rest:{rest_exc}")[:200]
    except Exception as exc:
        err_msg = sanitize_text(str(exc))[:200]

    if err_msg is not None:
        return {
            "repo": repo_clean,
            "status": "UNREACHABLE",
            "source": source,
            "runs_checked": 0,
            "failing_runs": [],
            "error": err_msg,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 1),
        }

    failing: list[dict[str, Any]] = []
    for run in runs:
        conc = str(run.get("conclusion") or "").lower()
        if conc in FAILING_CONCLUSIONS:
            cls = classify_ci_failure(
                str(run.get("workflow") or ""),
                title=str(run.get("title") or ""),
                conclusion=conc,
            )
            failing.append(
                {
                    "run_id": run.get("run_id"),
                    "workflow": sanitize_text(run.get("workflow") or ""),
                    "branch": sanitize_text(run.get("branch") or ""),
                    "conclusion": conc,
                    "created_utc": str(run.get("created_utc") or ""),
                    "classification": cls,
                }
            )

    status = "FAILING" if failing else "HEALTHY"
    return {
        "repo": repo_clean,
        "status": status,
        "source": source,
        "runs_checked": len(runs),
        "failing_runs": failing,
        "error": None,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 1),
    }


def scan_all_repos(
    *,
    root: Path = ROOT,
    repos: tuple[str, ...] | list[str] = DEFAULT_REPOS,
    offline: bool = False,
    dry_run: bool = False,
    budget_sec: float = DEFAULT_BUDGET_SEC,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    queue_path: Path | None = None,
    state_path: Path | None = None,
    fetcher: Callable[[str, float], list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Scan all Naqex repositories concurrently within budget_sec (<= 3.0s)."""
    budget_val = _validate_positive_finite(budget_sec, name="budget_sec")
    if isinstance(max_attempts, bool) or not isinstance(max_attempts, int) or max_attempts < 1:
        raise ValueError(f"max_attempts must be a positive int, got {max_attempts!r}")

    effective_budget = min(budget_val, DEFAULT_BUDGET_SEC)
    repo_list = [_validate_repo_slug(r) for r in repos if str(r).strip()]
    if not repo_list:
        raise ValueError("At least one repository must be provided")

    resolved_queue = queue_path or (root / ".runtime/automation/event_queue.jsonl")
    resolved_state = state_path or (root / ".runtime/automation/self_healing_ci_state.json")
    now_iso = _utc_now_iso()
    t0 = time.perf_counter()
    deadline = t0 + effective_budget

    per_repo_timeout = max(0.2, effective_budget - 0.15)
    repo_results: list[dict[str, Any]] = []
    pool = ThreadPoolExecutor(max_workers=min(4, len(repo_list)))
    timed_out = False
    try:
        future_map = {
            pool.submit(
                scan_single_repo,
                repo,
                offline=offline,
                timeout_sec=per_repo_timeout,
                fetcher=fetcher,
            ): repo
            for repo in repo_list
        }
        wait_sec = max(0.01, deadline - time.perf_counter())
        done, not_done = futures_wait(future_map.keys(), timeout=wait_sec)
        timed_out = len(not_done) > 0
        for fut, repo in future_map.items():
            if fut in not_done:
                fut.cancel()
                res = {
                    "repo": repo,
                    "status": "BUDGET_TIMEOUT",
                    "source": "TIMEOUT",
                    "runs_checked": 0,
                    "failing_runs": [],
                    "error": f"exceeded_budget_{effective_budget:.1f}s",
                    "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 1),
                }
            else:
                try:
                    res = fut.result(timeout=0)
                except Exception as exc:
                    res = {
                        "repo": repo,
                        "status": "ERROR",
                        "source": "ERROR",
                        "runs_checked": 0,
                        "failing_runs": [],
                        "error": sanitize_text(str(exc))[:180],
                        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 1),
                    }
            repo_results.append(res)
    finally:
        pool.shutdown(wait=not timed_out, cancel_futures=True)

    state = _safe_read_json(resolved_state)
    events_queued: list[dict[str, Any]] = []
    open_circuits: list[str] = []

    for res in repo_results:
        repo_name = res["repo"]
        failing_runs = res.get("failing_runs") or []
        if res["status"] == "HEALTHY":
            # Reset existing circuit breakers for this repo on clean scan
            breakers = state.get("circuit_breakers")
            if isinstance(breakers, dict):
                for bkey in list(breakers.keys()):
                    if bkey.startswith(f"{repo_name}::"):
                        evaluate_circuit_breaker(state, bkey, failed=False, max_attempts=max_attempts, now_utc=now_iso)
            continue

        for frun in failing_runs:
            cls = frun["classification"]
            cb_key = f"{repo_name}::{cls['signature']}"
            cb = evaluate_circuit_breaker(state, cb_key, failed=True, max_attempts=max_attempts, now_utc=now_iso)
            frun["circuit_breaker"] = cb
            if cb["state"] == "CIRCUIT_OPEN_ESCALATE_OWNER":
                open_circuits.append(cb_key)
            ev = {
                "schema": "naqex-automation-event-v1",
                "event_type": "ci_failure_detected",
                "source": "self_healing_ci",
                "ts_utc": now_iso,
                "repo": repo_name,
                "run_id": frun.get("run_id"),
                "workflow": frun.get("workflow"),
                "branch": frun.get("branch"),
                "conclusion": frun.get("conclusion"),
                "category": cls["category"],
                "severity": cls["severity"],
                "auto_healable": bool(cls["auto_healable"]) and bool(cb["allow_attempt"]),
                "suggested_action": (
                    "ESCALATE_OWNER_CIRCUIT_OPEN" if cb["escalate_owner"] else cls["suggested_action"]
                ),
                "circuit_state": cb["state"],
                "attempt": cb["attempts"],
                "max_attempts": max_attempts,
                "order_send_count": ORDER_SEND_COUNT,
            }
            qres = append_queue_event(resolved_queue, ev, dry_run=dry_run)
            events_queued.append(qres)

    total_ms = round((time.perf_counter() - t0) * 1000.0, 1)
    if offline:
        overall = "OFFLINE"
    elif open_circuits:
        overall = "CIRCUIT_OPEN_ESCALATE_OWNER"
    elif any(r["status"] == "FAILING" for r in repo_results):
        overall = "FAILING_DETECTED"
    elif any(r["status"] in {"UNREACHABLE", "BUDGET_TIMEOUT", "ERROR"} for r in repo_results):
        overall = "DEGRADED"
    else:
        overall = "HEALTHY"

    state["schema"] = SCHEMA_VERSION
    state["updated_utc"] = now_iso
    state["order_send_count"] = ORDER_SEND_COUNT
    state["last_overall_status"] = overall
    if not dry_run:
        _atomic_write_json(resolved_state, sanitize_obj(state))

    report = sanitize_obj(
        {
            "schema": SCHEMA_VERSION,
            "checked_utc": now_iso,
            "order_send_count": ORDER_SEND_COUNT,
            "offline": offline,
            "dry_run": dry_run,
            "budget_sec": effective_budget,
            "elapsed_ms": total_ms,
            "max_attempts": max_attempts,
            "overall_status": overall,
            "repos_scanned": len(repo_results),
            "repos": repo_results,
            "open_circuits": open_circuits,
            "events_count": len(events_queued),
            "events": events_queued,
        }
    )
    return report


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Concurrent read-only Naqex GitHub Actions self-healing scanner.")
    ap.add_argument("--root", type=Path, default=ROOT, help="Workspace root directory")
    ap.add_argument("--repos", default=",".join(DEFAULT_REPOS), help="Comma-separated owner/repo list")
    ap.add_argument("--offline", action="store_true", help="Skip all live GitHub CLI/API calls (100%% CI-safe)")
    ap.add_argument("--dry-run", action="store_true", help="Do not write event_queue.jsonl or state files")
    ap.add_argument("--json", action="store_true", dest="as_json", help="Emit structured JSON output (default)")
    ap.add_argument(
        "--budget-sec",
        type=float,
        default=DEFAULT_BUDGET_SEC,
        help="Concurrency wall-clock budget (<= 3s)",
    )
    ap.add_argument("--max-attempts", type=int, default=DEFAULT_MAX_ATTEMPTS, help="Circuit breaker max attempts")
    ap.add_argument("--queue-path", type=Path, default=None, help="Override event_queue.jsonl path")
    ap.add_argument("--state-path", type=Path, default=None, help="Override circuit-breaker state JSON path")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repos = tuple(r.strip() for r in str(args.repos).split(",") if r.strip())
    report = scan_all_repos(
        root=args.root,
        repos=repos,
        offline=bool(args.offline),
        dry_run=bool(args.dry_run),
        budget_sec=float(args.budget_sec),
        max_attempts=int(args.max_attempts),
        queue_path=args.queue_path,
        state_path=args.state_path,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

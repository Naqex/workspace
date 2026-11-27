"""Cross-Product Read-Only QA Sweep (`OrderSend = 0`, `MT5_PROCS = 0`, `Holdout = 0`).

Reads `tooling/automation/configs/feature_map.json` (with built-in graceful fallback when
absent) and executes registered read-only QA checks across:
  - `TradingWorkspace` (architecture & Holdout lock verification)
  - `Cockpit` (in-process `127.0.0.1:0` ephemeral HTTP smoke test — zero fixed port conflicts!)
  - `education/check_setup.py`
  - Read-only repository & AST checks for `projects/trader` & `projects/quant-trading`

Hard Safety Invariants:
  - ORDER_SEND_CAPABLE = False, ORDER_SEND_COUNT = 0, MT5_PROCS_LAUNCHED = 0
  - HOLDOUT_ROWS_ANALYSED = 0, SPEND_VND = 0
  - Mode-A safe: NEVER runs `pytest -n auto`, NEVER runs `uv run` in root TradingWorkspace
  - Zero `shell=True`, zero bare `assert` statements (`python -O` safe), zero OPSEC leaks
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ORDER_SEND_CAPABLE: bool = False
ORDER_SEND_COUNT: int = 0
MT5_PROCS_LAUNCHED: int = 0
HOLDOUT_ROWS_ANALYSED: int = 0
SPEND_VND: int = 0

SCHEMA_VERSION: str = "naqex-product-qa-sweep-v1"
VN_TZ = timezone(timedelta(hours=7))

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FEATURE_MAP_PATH = ROOT / "tooling/automation/configs/feature_map.json"
DEFAULT_OUT_PATH = ROOT / ".runtime/automation/product_qa_latest.json"
EXPECTED_HOLDOUT_LOCK_SHA256 = "f0a6b43cb205535b0a959456455dc1d857a0936c06c2e51b8614fd7d772a8486"

BELOW_NORMAL_PRIORITY_CLASS: int = 0x00004000
CREATE_NO_WINDOW_FLAG: int = int(getattr(subprocess, "CREATE_NO_WINDOW", 0))

_FORBIDDEN_CMD_TOKENS: tuple[str, ...] = (
    "terminal64.exe",
    "metatester64.exe",
    "git push",
    "git commit",
)
_LAN_IP_RE = re.compile(r"\b(?:192" + r"\.168|10\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}\b")
_CGNAT_IP_RE = re.compile(r"\b100" + r"\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d{1,3}\.\d{1,3}\b")
_WIN_USER_RE = re.compile(
    r"(?i)(?:[A-Z]:|/mnt/[a-z])[\\/]" + "Users" + r"[\\/](?!<|YOUR_|user\b|username\b)[A-Za-z0-9._-]+"
)
_TG_TOKEN_RE = re.compile(r"(?:bot)?\b\d{6,}:[A-Za-z0-9_-]{10,}\b")
_URL_RE = re.compile(r"https?://(?!127\.0\.0\.1|localhost)[^\s'\"<>]+")


def scrub_text(raw: Any, *, max_len: int = 600) -> str:
    """Scrub secrets, external URLs, private IPs, and Windows user profile paths."""
    out = str(raw or "")
    out = _URL_RE.sub("<REDACTED_URL>", out)
    out = _TG_TOKEN_RE.sub("<REDACTED_TOKEN>", out)
    out = _LAN_IP_RE.sub("<REDACTED_IP>", out)
    out = _CGNAT_IP_RE.sub("<REDACTED_IP>", out)
    out = _WIN_USER_RE.sub("<USER_HOME>", out)
    if len(out) > max_len:
        return out[: max_len - 3] + "..."
    return out


def sanitize_value(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): sanitize_value(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize_value(v) for v in obj]
    if isinstance(obj, tuple):
        return [sanitize_value(v) for v in obj]
    if isinstance(obj, str):
        return scrub_text(obj, max_len=1200)
    return obj


def _replace_with_retry(src: Path, dst: Path, *, retries: int = 12) -> None:
    for attempt in range(retries):
        try:
            os.replace(src, dst)
            return
        except PermissionError:
            if attempt + 1 >= retries:
                raise
            time.sleep(0.01 * (attempt + 1))


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(sanitize_value(payload), indent=2, ensure_ascii=False) + "\n"
    tmp_path: Path | None = None
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
            tmp_path = Path(fh.name)
        _replace_with_retry(tmp_path, path)
        tmp_path = None
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)


def resolve_python(root: Path = ROOT) -> str:
    bundled = root / ".runtime/quant-audit-v24/Scripts/python.exe"
    if bundled.is_file():
        return str(bundled)
    return sys.executable


def build_subproc_env(root: Path = ROOT) -> dict[str, str]:
    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    parts = [
        str(root),
        str(root / "tooling/ai-engines"),
        str(root / "tooling/ai-engines/legacy"),
        str(root / "projects/trader/foundation_v2"),
        str(root / "projects/quant-trading/src"),
    ]
    if existing:
        parts.append(existing)
    env["PYTHONPATH"] = os.pathsep.join(parts)
    env["PYTHONUTF8"] = "1"
    return env


def _fallback_feature_specs() -> list[dict[str, Any]]:
    """Canonical fallback QA feature registry used if feature_map.json is absent."""
    return [
        {
            "id": "workspace_architecture_gate",
            "product": "TradingWorkspace",
            "description": "Harness Engineering architecture gate (--strict) + sealed Holdout SHA check",
            "kind": "workspace_builtin",
            "offline_safe": True,
            "order_send_count": 0,
        },
        {
            "id": "cockpit_http_smoke",
            "product": "Cockpit",
            "description": "In-process 127.0.0.1:0 Cockpit HTTP smoke (/api/health, /api/summary, offline routes)",
            "kind": "cockpit_http_smoke",
            "offline_safe": True,
            "order_send_count": 0,
        },
        {
            "id": "education_setup",
            "product": "Education",
            "description": "Validate bilingual trading course integrity via education/check_setup.py",
            "kind": "command",
            "command": ["{python}", "-X", "utf8", "education/check_setup.py"],
            "offline_safe": True,
            "order_send_count": 0,
        },
        {
            "id": "trader_readonly_check",
            "product": "projects/trader",
            "description": "Read-only structure & AST syntax audit of projects/trader/foundation_v2",
            "kind": "repo_readonly",
            "repo_path": "projects/trader",
            "ast_subpath": "foundation_v2",
            "required_paths": ["README.md", "AGENTS.md", "foundation_v2"],
            "offline_safe": True,
            "order_send_count": 0,
        },
        {
            "id": "quant_trading_readonly_check",
            "product": "projects/quant-trading",
            "description": "Read-only structure & AST syntax audit of projects/quant-trading/src",
            "kind": "repo_readonly",
            "repo_path": "projects/quant-trading",
            "ast_subpath": "src",
            "required_paths": ["README.md", "pyproject.toml", "src"],
            "offline_safe": True,
            "order_send_count": 0,
        },
    ]


def _normalize_feature_entry(raw_id: str | None, item: dict[str, Any]) -> dict[str, Any] | None:
    fid = str(item.get("id") or item.get("feature_id") or raw_id or "").strip()
    if not fid:
        return None
    product = str(
        item.get("product") or item.get("domain") or item.get("repo") or item.get("owner") or "TradingWorkspace"
    ).strip()
    desc = str(item.get("description") or item.get("title") or item.get("name") or fid).strip()
    offline_safe = bool(item.get("offline_safe", True))

    kind = str(item.get("kind") or item.get("check_type") or "").strip().lower()
    cmd = item.get("command") or item.get("verify_command") or item.get("cmd")
    if not cmd and isinstance(item.get("commands"), list) and item["commands"]:
        cmd = item["commands"][0]

    low_id = fid.lower()
    if not kind:
        if cmd is not None:
            kind = "command"
        elif "cockpit" in low_id:
            kind = "cockpit_http_smoke"
        elif "trader" in low_id or "trader" in product.lower():
            kind = "repo_readonly"
        elif "quant-trading" in low_id or "quant_trading" in low_id or "quant-trading" in product.lower():
            kind = "repo_readonly"
        else:
            kind = "workspace_builtin"

    normalized: dict[str, Any] = {
        "id": fid,
        "product": product,
        "description": desc,
        "kind": kind,
        "offline_safe": offline_safe,
        "order_send_count": 0,
    }
    if cmd is not None:
        normalized["command"] = cmd
    if item.get("fallback_command") is not None:
        normalized["fallback_command"] = item["fallback_command"]
    if isinstance(item.get("secondary_commands"), list):
        normalized["secondary_commands"] = item["secondary_commands"]
    if item.get("timeout_sec") is not None:
        try:
            normalized["timeout_sec"] = max(5, int(item["timeout_sec"]))
        except (TypeError, ValueError):
            pass
    if item.get("cwd"):
        normalized["cwd"] = str(item["cwd"])
    if item.get("repo_path"):
        normalized["repo_path"] = str(item["repo_path"])
    if item.get("ast_subpath"):
        normalized["ast_subpath"] = str(item["ast_subpath"])
    if isinstance(item.get("required_paths"), list):
        normalized["required_paths"] = [str(p) for p in item["required_paths"]]
    return normalized


def load_feature_registry(feature_map_path: Path) -> tuple[str, list[dict[str, Any]]]:
    """Load feature registry from feature_map.json with graceful fallback and core QA coverage."""
    fallback = _fallback_feature_specs()
    if not feature_map_path.is_file():
        return "fallback_missing_file", fallback

    try:
        raw = json.loads(feature_map_path.read_text(encoding="utf-8"))
    except Exception:
        return "fallback_invalid_json", fallback

    entries_raw: list[tuple[str | None, dict[str, Any]]] = []
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict):
                entries_raw.append((None, item))
    elif isinstance(raw, dict):
        container = raw.get("features") if "features" in raw else raw.get("entries")
        if isinstance(container, list):
            for item in container:
                if isinstance(item, dict):
                    entries_raw.append((None, item))
        elif isinstance(container, dict):
            for k, v in container.items():
                if isinstance(v, dict):
                    entries_raw.append((str(k), v))

    loaded: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for raw_id, item in entries_raw:
        norm = _normalize_feature_entry(raw_id, item)
        if norm is not None and norm["id"] not in seen_ids:
            seen_ids.add(norm["id"])
            loaded.append(norm)

    if not loaded:
        return "fallback_empty_map", fallback

    # Always include in-process 127.0.0.1:0 Cockpit HTTP smoke check so `--only cockpit_http_smoke`
    # and full sweeps verify live HTTP routes without fixed port collisions.
    if "cockpit_http_smoke" not in seen_ids:
        cockpit_spec = next(f for f in fallback if f["id"] == "cockpit_http_smoke")
        loaded.append(cockpit_spec)

    return "feature_map_json", loaded


def _sanitize_command_argv(raw_cmd: Any, *, root: Path, py: str) -> tuple[list[str] | None, str | None]:
    """Convert raw command into a safe argv list enforcing Mode-A & zero-uv-in-root guards."""
    if isinstance(raw_cmd, list):
        argv = [str(tok) for tok in raw_cmd if str(tok).strip()]
    elif isinstance(raw_cmd, str):
        argv = shlex.split(raw_cmd, posix=False)
    else:
        return None, "unsupported_command_type"

    if not argv:
        return None, "empty_command"

    joined_low = " ".join(argv).lower()
    for forbidden in _FORBIDDEN_CMD_TOKENS:
        if forbidden in joined_low:
            return None, f"forbidden_command_token:{forbidden}"

    # Hard Mode-A guard: NEVER run `uv run` in root TradingWorkspace
    if argv[0].lower() in ("uv", "uv.exe") and len(argv) >= 2 and argv[1].lower() == "run":
        return None, "forbidden_root_uv_run_in_mode_a"

    resolved: list[str] = []
    idx = 0
    while idx < len(argv):
        tok = argv[idx]
        if idx == 0:
            if tok.lower() in ("{python}", "python", "python3", "python.exe"):
                resolved.append(py)
                idx += 1
                continue
            cand = root / tok
            if cand.is_file():
                resolved.append(str(cand.resolve()))
                idx += 1
                continue
            if tok.replace("\\", "/") == ".runtime/quant-audit-v24/Scripts/python.exe":
                resolved.append(py)
                idx += 1
                continue
        if tok == "{root}":
            resolved.append(str(root))
            idx += 1
            continue
        # Mode-A guard: clamp `-n auto` down to `-n 2`
        if tok == "-n" and idx + 1 < len(argv) and argv[idx + 1].lower() == "auto":
            resolved.extend(["-n", "2"])
            idx += 2
            continue
        if tok.lower() == "-nauto":
            resolved.extend(["-n", "2"])
            idx += 1
            continue
        resolved.append(tok.replace("{python}", py).replace("{root}", str(root)))
        idx += 1

    return resolved, None


def run_cockpit_http_smoke(root: Path = ROOT, *, timeout_sec: float = 5.0) -> dict[str, Any]:
    """Spin up Naqex Cockpit in-process on ephemeral 127.0.0.1:0, smoke-test routes, and close cleanly."""
    t0 = time.perf_counter()
    ai_engines = root / "tooling/ai-engines"
    if str(ai_engines) not in sys.path:
        sys.path.insert(0, str(ai_engines))
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    try:
        routes_mod = importlib.import_module("cockpit.modules.routes")
        create_server = routes_mod.create_server
    except Exception as exc:
        return {
            "status": "FAIL",
            "ok": False,
            "seconds": round(time.perf_counter() - t0, 3),
            "detail": f"Cannot import cockpit.modules.routes.create_server: {scrub_text(exc, max_len=240)}",
        }

    srv = create_server(host="127.0.0.1", port=0, root=root)
    port = int(srv.server_address[1])
    thread = threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    thread.start()

    required_routes: tuple[tuple[str, str], ...] = (
        ("/api/health", "json"),
        ("/api/summary", "json"),
        ("/api/node1-summary?offline=1", "json"),
        ("/api/prop-metrix?offline=1", "json"),
        ("/", "html"),
    )
    optional_routes: tuple[str, ...] = ("/api/automation/status",)

    route_results: list[dict[str, Any]] = []
    failures: list[str] = []
    try:
        for route, expected_kind in required_routes:
            url = f"http://127.0.0.1:{port}{route}"
            try:
                with urllib.request.urlopen(url, timeout=timeout_sec) as resp:
                    code = int(resp.status)
                    body = resp.read()
                if code != 200:
                    failures.append(f"{route}:http_{code}")
                    route_results.append({"route": route, "http_status": code, "ok": False})
                    continue
                if expected_kind == "json":
                    data = json.loads(body.decode("utf-8"))
                    if not isinstance(data, dict):
                        failures.append(f"{route}:non_dict_json")
                        route_results.append({"route": route, "http_status": code, "ok": False})
                        continue
                    if route == "/api/health":
                        if data.get("ok") is not True or int(data.get("order_send_count", -1)) != 0:
                            failures.append("/api/health:invalid_invariants")
                            route_results.append({"route": route, "http_status": code, "ok": False})
                            continue
                    route_results.append({"route": route, "http_status": code, "ok": True, "bytes": len(body)})
                else:
                    ok_html = b"<html" in body.lower() or b"<!doctype html" in body.lower()
                    if not ok_html:
                        failures.append(f"{route}:invalid_html")
                    route_results.append({"route": route, "http_status": code, "ok": ok_html, "bytes": len(body)})
            except Exception as exc:
                failures.append(f"{route}:{type(exc).__name__}")
                route_results.append({"route": route, "ok": False, "error": scrub_text(exc, max_len=160)})

        for opt_route in optional_routes:
            url = f"http://127.0.0.1:{port}{opt_route}"
            try:
                with urllib.request.urlopen(url, timeout=timeout_sec) as resp:
                    code = int(resp.status)
                    data = json.loads(resp.read().decode("utf-8"))
                ok_opt = code == 200 and isinstance(data, dict) and int(data.get("order_send_count", 0)) == 0
                if not ok_opt:
                    failures.append(f"{opt_route}:invariant_mismatch")
                route_results.append({"route": opt_route, "http_status": code, "ok": ok_opt, "optional": True})
            except urllib.error.HTTPError as exc:
                if int(exc.code) == 404:
                    route_results.append(
                        {"route": opt_route, "http_status": 404, "ok": True, "optional": True, "note": "pending_h4"}
                    )
                else:
                    failures.append(f"{opt_route}:http_{exc.code}")
                    route_results.append(
                        {"route": opt_route, "http_status": int(exc.code), "ok": False, "optional": True}
                    )
            except Exception as exc:
                failures.append(f"{opt_route}:{type(exc).__name__}")
                route_results.append(
                    {"route": opt_route, "ok": False, "optional": True, "error": scrub_text(exc, max_len=120)}
                )
    finally:
        srv.shutdown()
        srv.server_close()
        thread.join(timeout=2.0)

    ok = len(failures) == 0
    return {
        "status": "PASS" if ok else "FAIL",
        "ok": ok,
        "bind": f"127.0.0.1:{port}",
        "routes": route_results,
        "seconds": round(time.perf_counter() - t0, 3),
        "detail": (
            f"In-process 127.0.0.1:{port} smoke PASS ({len(route_results)} routes verified, OrderSend=0)"
            if ok
            else f"Cockpit smoke FAIL: {', '.join(failures)}"
        ),
    }


def run_workspace_builtin_check(root: Path, *, py: str, timeout_sec: int) -> dict[str, Any]:
    """Read-only workspace architecture gate + Holdout lock SHA-256 verification."""
    t0 = time.perf_counter()
    lock_path = root / "planning/research/NATIVE_FTMO_HOLDOUT_LOCK.json"
    errors: list[str] = []
    if not lock_path.is_file():
        errors.append("missing_holdout_lock")
    else:
        sha = hashlib.sha256(lock_path.read_bytes()).hexdigest()
        if sha != EXPECTED_HOLDOUT_LOCK_SHA256:
            errors.append(f"holdout_lock_sha_mismatch:{sha[:12]}")

    arch_script = root / "tooling/check_architecture.py"
    arch_ok = True
    if arch_script.is_file():
        creationflags = (BELOW_NORMAL_PRIORITY_CLASS | CREATE_NO_WINDOW_FLAG) if os.name == "nt" else 0
        proc = subprocess.run(
            [py, "-X", "utf8", str(arch_script), "--strict", "--json"],
            cwd=str(root),
            env=build_subproc_env(root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=max(10, int(timeout_sec)),
            creationflags=creationflags,
            check=False,
        )
        arch_ok = proc.returncode == 0
        if not arch_ok:
            errors.append(f"check_architecture_strict_rc={proc.returncode}")

    ok = len(errors) == 0 and arch_ok
    return {
        "status": "PASS" if ok else "FAIL",
        "ok": ok,
        "seconds": round(time.perf_counter() - t0, 3),
        "detail": "Holdout lock SHA exact match + check_architecture --strict PASS" if ok else "; ".join(errors),
    }


def run_repo_readonly_check(root: Path, spec: dict[str, Any]) -> dict[str, Any]:
    """100% read-only structure & Python AST syntax check for sibling repos (0 edits, 0 builds)."""
    t0 = time.perf_counter()
    rel_repo = str(spec.get("repo_path") or "").strip()
    if not rel_repo:
        prod = str(spec.get("product") or "")
        if "trader" in prod.lower() or "trader" in str(spec.get("id", "")).lower():
            rel_repo = "projects/trader"
        elif "quant" in prod.lower() or "quant" in str(spec.get("id", "")).lower():
            rel_repo = "projects/quant-trading"

    repo_dir = root / rel_repo
    if not repo_dir.is_dir():
        return {
            "status": "SKIPPED_REPO_ABSENT",
            "ok": True,
            "repo_path": rel_repo,
            "seconds": round(time.perf_counter() - t0, 3),
            "detail": f"Repository path not present ({rel_repo}) — skipped gracefully in CI/offline",
        }

    required_paths = spec.get("required_paths") or ["README.md"]
    missing = [p for p in required_paths if not (repo_dir / p).exists()]

    ast_subpath = str(spec.get("ast_subpath") or "").strip()
    ast_dir = (repo_dir / ast_subpath) if ast_subpath else repo_dir
    py_checked = 0
    syntax_errors: list[str] = []
    if ast_dir.is_dir():
        skip_parts = {".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache", "node_modules", "target"}
        for py_file in sorted(ast_dir.rglob("*.py")):
            if any(part in skip_parts for part in py_file.parts):
                continue
            py_checked += 1
            try:
                ast.parse(py_file.read_text(encoding="utf-8", errors="replace"), filename=str(py_file))
            except SyntaxError as exc:
                rel_bad = py_file.relative_to(repo_dir).as_posix()
                syntax_errors.append(f"{rel_bad}:{exc.lineno}")
            if py_checked >= 250:
                break

    git_head: str | None = None
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_dir), "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
            creationflags=CREATE_NO_WINDOW_FLAG if os.name == "nt" else 0,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            git_head = proc.stdout.strip()
    except Exception:
        git_head = None

    ok = len(missing) == 0 and len(syntax_errors) == 0
    detail_parts = [f"py_ast_ok={py_checked}"]
    if git_head:
        detail_parts.append(f"head={git_head}")
    if missing:
        detail_parts.append(f"missing={','.join(missing)}")
    if syntax_errors:
        detail_parts.append(f"syntax_errors={','.join(syntax_errors[:5])}")

    return {
        "status": "PASS" if ok else "FAIL",
        "ok": ok,
        "repo_path": rel_repo,
        "git_head": git_head,
        "py_files_ast_checked": py_checked,
        "missing_paths": missing,
        "syntax_errors": syntax_errors[:10],
        "seconds": round(time.perf_counter() - t0, 3),
        "detail": " · ".join(detail_parts),
    }


def _run_single_argv(
    argv: list[str],
    *,
    root: Path,
    cwd: Path,
    timeout_sec: int,
) -> tuple[bool, int, str]:
    creationflags = (BELOW_NORMAL_PRIORITY_CLASS | CREATE_NO_WINDOW_FLAG) if os.name == "nt" else 0
    try:
        proc = subprocess.run(
            argv,
            cwd=str(cwd),
            env=build_subproc_env(root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=max(5, int(timeout_sec)),
            creationflags=creationflags,
            check=False,
        )
        ok = proc.returncode == 0
        tail = (proc.stdout or proc.stderr or "").strip().splitlines()
        summary = tail[-1] if tail else f"rc={proc.returncode}"
        return ok, int(proc.returncode), scrub_text(summary, max_len=240)
    except subprocess.TimeoutExpired:
        return False, 124, f"Timeout after {timeout_sec}s"
    except OSError as exc:
        return False, 127, f"OS error: {scrub_text(exc, max_len=200)}"


def _execute_command_feature(
    *,
    root: Path,
    py: str,
    spec: dict[str, Any],
    timeout_sec: int,
) -> dict[str, Any]:
    t0 = time.perf_counter()
    eff_timeout = int(spec.get("timeout_sec") or timeout_sec)
    argv, reject_reason = _sanitize_command_argv(spec.get("command"), root=root, py=py)
    cwd = root / str(spec["cwd"]) if spec.get("cwd") else root

    # If primary executable path is missing (e.g. submodule .venv absent in CI), try fallback_command
    if argv is not None and ("/" in argv[0] or "\\" in argv[0]) and not Path(argv[0]).is_file():
        fb = spec.get("fallback_command")
        if fb is not None:
            argv, reject_reason = _sanitize_command_argv(fb, root=root, py=py)
            cwd = root

    if argv is None:
        return {
            "status": "FAIL",
            "ok": False,
            "seconds": round(time.perf_counter() - t0, 3),
            "detail": f"Command rejected by safety guard: {reject_reason}",
        }

    if not cwd.is_dir():
        return {
            "status": "SKIPPED_CWD_ABSENT",
            "ok": True,
            "seconds": round(time.perf_counter() - t0, 3),
            "detail": f"Working directory absent ({spec.get('cwd')}) — skipped gracefully",
        }

    ok, rc, summary = _run_single_argv(argv, root=root, cwd=cwd, timeout_sec=eff_timeout)
    summaries = [summary]
    commands_run = 1
    if not ok:
        return {
            "status": "FAIL",
            "ok": False,
            "returncode": rc,
            "commands_run": commands_run,
            "seconds": round(time.perf_counter() - t0, 3),
            "detail": summary,
        }

    # Execute all registered secondary_commands fail-closed
    raw_secondary = spec.get("secondary_commands")
    secondary_list: list[Any] = raw_secondary if isinstance(raw_secondary, list) else []
    for idx, sec_raw in enumerate(secondary_list, start=1):
        sec_argv, sec_reject = _sanitize_command_argv(sec_raw, root=root, py=py)
        if sec_argv is None:
            return {
                "status": "FAIL",
                "ok": False,
                "returncode": 1,
                "commands_run": commands_run,
                "seconds": round(time.perf_counter() - t0, 3),
                "detail": f"Secondary command #{idx} rejected by safety guard: {sec_reject}",
            }
        sec_ok, sec_rc, sec_summary = _run_single_argv(sec_argv, root=root, cwd=cwd, timeout_sec=eff_timeout)
        commands_run += 1
        summaries.append(f"sec#{idx}: {sec_summary}")
        if not sec_ok:
            return {
                "status": "FAIL",
                "ok": False,
                "returncode": sec_rc,
                "commands_run": commands_run,
                "seconds": round(time.perf_counter() - t0, 3),
                "detail": scrub_text(" | ".join(summaries), max_len=280),
            }

    return {
        "status": "PASS",
        "ok": True,
        "returncode": 0,
        "commands_run": commands_run,
        "seconds": round(time.perf_counter() - t0, 3),
        "detail": scrub_text(" | ".join(summaries), max_len=280),
    }


def run_product_qa_sweep(
    *,
    root: Path = ROOT,
    feature_map_path: Path | None = None,
    out_path: Path | None = DEFAULT_OUT_PATH,
    only_ids: list[str] | None = None,
    offline: bool = False,
    dry_run: bool = False,
    timeout_sec: int = 120,
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    """Run registered cross-product QA sweep and write sanitized JSON receipt."""
    t0 = time.perf_counter()
    now = now_utc or datetime.now(UTC)
    now_ict = now.astimezone(VN_TZ)
    py = resolve_python(root)
    fmap_path = (
        feature_map_path if feature_map_path is not None else (root / "tooling/automation/configs/feature_map.json")
    )
    source_tag, features = load_feature_registry(fmap_path)

    requested_ids: list[str] = []
    for raw in only_ids or []:
        for tok in str(raw).split(","):
            clean = tok.strip()
            if clean:
                requested_ids.append(clean)

    available_ids = [f["id"] for f in features]
    unknown_ids = [fid for fid in requested_ids if fid not in available_ids]
    if unknown_ids:
        payload = {
            "schema": SCHEMA_VERSION,
            "generated_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "generated_ict": now_ict.strftime("%Y-%m-%d %H:%M:%S ICT"),
            "order_send_capable": ORDER_SEND_CAPABLE,
            "order_send_count": ORDER_SEND_COUNT,
            "mt5_procs_launched": MT5_PROCS_LAUNCHED,
            "holdout_rows_analysed": HOLDOUT_ROWS_ANALYSED,
            "spend_vnd": SPEND_VND,
            "offline": bool(offline),
            "dry_run": bool(dry_run),
            "feature_map_source": source_tag,
            "overall_status": "FAIL",
            "error": f"Unknown --only feature_id(s): {', '.join(unknown_ids)}",
            "available_feature_ids": available_ids,
            "counts": {"pass": 0, "fail": 1, "skipped": 0, "dry_run": 0},
            "results": [],
            "elapsed_sec": round(time.perf_counter() - t0, 3),
        }
        if out_path is not None:
            atomic_write_json(out_path, payload)
        return payload

    selected = [f for f in features if not requested_ids or f["id"] in requested_ids]
    results: list[dict[str, Any]] = []

    for spec in selected:
        base: dict[str, Any] = {
            "id": spec["id"],
            "product": spec["product"],
            "kind": spec["kind"],
            "description": spec["description"],
            "offline_safe": bool(spec.get("offline_safe", True)),
            "order_send_count": 0,
        }
        if offline and not base["offline_safe"]:
            base.update(
                {
                    "status": "SKIPPED_OFFLINE",
                    "ok": True,
                    "seconds": 0.0,
                    "detail": "Skipped under --offline (feature requires network/remote host)",
                }
            )
            results.append(base)
            continue

        if dry_run:
            base.update(
                {
                    "status": "DRY_RUN",
                    "ok": True,
                    "seconds": 0.0,
                    "detail": f"Dry-run: {spec['kind']} check planned for {spec['product']}",
                }
            )
            results.append(base)
            continue

        kind = spec["kind"]
        if kind == "cockpit_http_smoke":
            outcome = run_cockpit_http_smoke(root)
        elif kind == "workspace_builtin":
            outcome = run_workspace_builtin_check(root, py=py, timeout_sec=timeout_sec)
        elif kind == "repo_readonly":
            outcome = run_repo_readonly_check(root, spec)
        elif kind == "command":
            outcome = _execute_command_feature(root=root, py=py, spec=spec, timeout_sec=timeout_sec)
        else:
            outcome = {
                "status": "SKIPPED_UNKNOWN_KIND",
                "ok": True,
                "seconds": 0.0,
                "detail": f"Unsupported check kind '{kind}' — skipped gracefully",
            }
        base.update(outcome)
        results.append(base)

    counts = {
        "pass": sum(1 for r in results if r.get("status") == "PASS"),
        "fail": sum(1 for r in results if r.get("status") == "FAIL"),
        "skipped": sum(1 for r in results if str(r.get("status", "")).startswith("SKIPPED")),
        "dry_run": sum(1 for r in results if r.get("status") == "DRY_RUN"),
    }

    if dry_run:
        overall_status = "DRY_RUN"
    elif counts["fail"] > 0:
        overall_status = "FAIL"
    else:
        overall_status = "PASS"

    payload = {
        "schema": SCHEMA_VERSION,
        "generated_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generated_ict": now_ict.strftime("%Y-%m-%d %H:%M:%S ICT"),
        "order_send_capable": ORDER_SEND_CAPABLE,
        "order_send_count": ORDER_SEND_COUNT,
        "mt5_procs_launched": MT5_PROCS_LAUNCHED,
        "holdout_rows_analysed": HOLDOUT_ROWS_ANALYSED,
        "spend_vnd": SPEND_VND,
        "offline": bool(offline),
        "dry_run": bool(dry_run),
        "feature_map_source": source_tag,
        "only_filter": requested_ids,
        "available_feature_ids": available_ids,
        "overall_status": overall_status,
        "counts": counts,
        "results": results,
        "elapsed_sec": round(time.perf_counter() - t0, 3),
    }

    if out_path is not None:
        atomic_write_json(out_path, payload)
    return payload


def make_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Naqex Cross-Product Read-Only QA Sweep (OrderSend=0).",
    )
    ap.add_argument("--root", type=Path, default=ROOT, help="Workspace root override")
    ap.add_argument("--feature-map", type=Path, default=None, help="Path to feature_map.json")
    ap.add_argument("--out", type=Path, default=None, help="JSON receipt output path")
    ap.add_argument(
        "--only",
        action="append",
        default=[],
        help="Run only specified feature_id (repeatable or comma-separated)",
    )
    ap.add_argument("--offline", action="store_true", help="Run only offline-safe QA checks")
    ap.add_argument(
        "--dry-run", action="store_true", help="Plan QA sweep without executing subprocesses or HTTP server"
    )
    ap.add_argument("--timeout-sec", type=int, default=120, help="Per-feature timeout in seconds")
    ap.add_argument("--json", action="store_true", dest="as_json", help="Emit full JSON payload to stdout")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = make_parser().parse_args(argv)
    out_path = args.out if args.out is not None else (args.root / ".runtime/automation/product_qa_latest.json")
    payload = run_product_qa_sweep(
        root=args.root,
        feature_map_path=args.feature_map,
        out_path=out_path,
        only_ids=args.only,
        offline=args.offline,
        dry_run=args.dry_run,
        timeout_sec=args.timeout_sec,
    )
    if args.as_json:
        print(json.dumps(sanitize_value(payload), indent=2, ensure_ascii=False))
    else:
        c = payload["counts"]
        print(
            f"[product_qa_sweep] status={payload['overall_status']} source={payload['feature_map_source']} "
            f"pass={c['pass']} fail={c['fail']} skip={c['skipped']} dry_run={c['dry_run']} "
            f"OrderSend={ORDER_SEND_COUNT}"
        )
    return 1 if payload["overall_status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())

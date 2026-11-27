"""Nightly Quant & Workspace Hygiene Runner (01:30 ICT | OrderSend = 0, MT5_PROCS = 0).

Orchestrates strictly read-only nightly checks across Naqex TradingWorkspace:
  1. `system_doctor.py --mode fast --json`
  2. `check_architecture.py --strict --json`
  3. Knowledge Brain read-only health (`brain.sqlite3` RO query + `brain_cli.py audit-data`)
  4. Optional automation radar hooks (`auto_research_radar`, `prop_terms_radar`,
     `strategy_intel_bridge`) when present on disk — graceful skip when absent
  5. `<X13_WORKER>` read-only status (`--offline` / `--dry-run` skips SSH completely)

Hard Safety Invariants:
  - ORDER_SEND_CAPABLE = False, ORDER_SEND_COUNT = 0, MT5_PROCS_LAUNCHED = 0
  - HOLDOUT_ROWS_ANALYSED = 0 (Holdout 2025+ SEALED), SPEND_VND = 0
  - Mode-A / Mode-B aware: enforces Windows BELOW_NORMAL priority in MODE_A_OWNER_ACTIVE
  - Zero bare `assert` statements (100% safe under `python -O`)
  - Zero hardcoded IPs, usernames, tokens, or secrets (OPSEC-scrubbed)
"""

from __future__ import annotations

import argparse
import ctypes
import importlib.util
import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ORDER_SEND_CAPABLE: bool = False
ORDER_SEND_COUNT: int = 0
MT5_PROCS_LAUNCHED: int = 0
HOLDOUT_ROWS_ANALYSED: int = 0
SPEND_VND: int = 0

SCHEMA_VERSION: str = "naqex-nightly-quant-ops-v1"
VN_TZ = timezone(timedelta(hours=7))

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_PATH = ROOT / ".runtime/automation/nightly_latest.json"

BELOW_NORMAL_PRIORITY_CLASS: int = 0x00004000
NORMAL_PRIORITY_CLASS: int = 0x00000020
CREATE_NO_WINDOW_FLAG: int = int(getattr(subprocess, "CREATE_NO_WINDOW", 0))

OPTIONAL_RADAR_HOOKS: tuple[dict[str, str], ...] = (
    {
        "id": "auto_research_radar",
        "script": "tooling/automation/auto_research_radar.py",
        "output": ".runtime/automation/research_radar_latest.json",
    },
    {
        "id": "prop_terms_radar",
        "script": "tooling/automation/prop_terms_radar.py",
        "output": ".runtime/automation/prop_terms_radar_latest.json",
    },
    {
        "id": "strategy_intel_bridge",
        "script": "tooling/automation/strategy_intel_bridge.py",
        "output": ".runtime/automation/strategy_intel_handoff_latest.json",
    },
)

_LAN_IP_RE = re.compile(r"\b(?:192" + r"\.168|10\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}\b")
_CGNAT_IP_RE = re.compile(r"\b100" + r"\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d{1,3}\.\d{1,3}\b")
_WIN_USER_RE = re.compile(
    r"(?i)(?:[A-Z]:|/mnt/[a-z])[\\/]" + "Users" + r"[\\/](?!<|YOUR_|user\b|username\b)[A-Za-z0-9._-]+"
)
_TG_TOKEN_RE = re.compile(r"(?:bot)?\b\d{6,}:[A-Za-z0-9_-]{10,}\b")
_URL_RE = re.compile(r"https?://[^\s'\"<>]+")
_KV_SECRET_RE = re.compile(r"(?i)([?&]|\b)((?:token|api[_-]?key|secret)=)[^\s&'\"<>]+")
_BEARER_RE = re.compile(r"(?i)(Bearer\s+)[^\s'\"<>]+")


def _load_module_from_path(module_name: str, file_path: Path) -> Any | None:
    if not file_path.is_file():
        return None
    resolved = str(file_path.resolve())
    existing = sys.modules.get(module_name)
    if existing is not None:
        existing_file = getattr(existing, "__file__", None)
        if existing_file and str(Path(existing_file).resolve()) == resolved:
            return existing
    try:
        spec = importlib.util.spec_from_file_location(module_name, resolved)
        if spec is None or spec.loader is None:
            return None
        mod = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = mod
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        sys.modules.pop(module_name, None)
        return None


def scrub_text(raw: Any, *, max_len: int = 800) -> str:
    """Scrub secrets, URLs, private IPs, and Windows user paths from persisted diagnostics."""
    out = str(raw or "")
    out = _URL_RE.sub("<REDACTED_URL>", out)
    out = _TG_TOKEN_RE.sub("<REDACTED_TOKEN>", out)
    out = _KV_SECRET_RE.sub(r"\1\2<REDACTED>", out)
    out = _BEARER_RE.sub(r"\1<REDACTED>", out)
    out = _LAN_IP_RE.sub("<REDACTED_IP>", out)
    out = _CGNAT_IP_RE.sub("<REDACTED_IP>", out)
    out = _WIN_USER_RE.sub("<USER_HOME>", out)
    if len(out) > max_len:
        return out[: max_len - 3] + "..."
    return out


def sanitize_value(obj: Any) -> Any:
    """Recursively sanitize nested dicts/lists for safe persistence."""
    if isinstance(obj, dict):
        return {str(k): sanitize_value(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize_value(v) for v in obj]
    if isinstance(obj, tuple):
        return [sanitize_value(v) for v in obj]
    if isinstance(obj, str):
        return scrub_text(obj, max_len=1600)
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
    """Atomically persist LF-only UTF-8 JSON with fsync and Windows rename retry."""
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
    """Resolve canonical bundled workspace Python (never `uv run` in root)."""
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


def _read_idle_sec_windows() -> float | None:
    if os.name != "nt":
        return None
    try:

        class _LastInputInfo(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint32), ("dwTime", ctypes.c_uint32)]

        lii = _LastInputInfo()
        lii.cbSize = ctypes.sizeof(_LastInputInfo)
        if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
            return None
        tick64 = ctypes.windll.kernel32.GetTickCount64()
        elapsed_ms = (int(tick64) - int(lii.dwTime)) & 0xFFFFFFFF
        return round(elapsed_ms / 1000.0, 1)
    except Exception:
        return None


def _read_free_ram_gb_windows() -> float | None:
    if os.name != "nt":
        return None
    try:

        class _MemoryStatusEx(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_uint32),
                ("dwMemoryLoad", ctypes.c_uint32),
                ("ullTotalPhys", ctypes.c_uint64),
                ("ullAvailPhys", ctypes.c_uint64),
                ("ullTotalPageFile", ctypes.c_uint64),
                ("ullAvailPageFile", ctypes.c_uint64),
                ("ullTotalVirtual", ctypes.c_uint64),
                ("ullAvailVirtual", ctypes.c_uint64),
                ("ullAvailExtendedVirtual", ctypes.c_uint64),
            ]

        ms = _MemoryStatusEx()
        ms.dwLength = ctypes.sizeof(_MemoryStatusEx)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(ms)):
            return None
        return round(float(ms.ullAvailPhys) / float(1024**3), 2)
    except Exception:
        return None


def detect_dev_pc_mode(
    *,
    root: Path = ROOT,
    offline: bool = False,
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    """Detect MODE_A_OWNER_ACTIVE vs MODE_B_IDLE_OVERNIGHT safely (fail-closed to Mode A)."""
    now = now_utc or datetime.now(UTC)
    now_ict = now.astimezone(VN_TZ)
    in_overnight = 0 <= now_ict.hour < 7

    if not offline:
        router = _load_module_from_path(
            "_naqex_compute_router",
            root / "tooling/ai-engines/ops_cloud/compute_router.py",
        )
        if router is not None and hasattr(router, "probe_dev_pc"):
            try:
                info = router.probe_dev_pc(now_utc=now)
                if isinstance(info, dict) and info.get("mode"):
                    mode = str(info["mode"])
                    return {
                        "mode": mode,
                        "priority": "NORMAL" if mode == "MODE_B_IDLE_OVERNIGHT" else "BELOW_NORMAL",
                        "source": "compute_router.probe_dev_pc",
                        "in_overnight_window_ict": bool(info.get("in_overnight_window_ict", in_overnight)),
                        "idle_sec": info.get("idle_sec"),
                        "cpu_util_pct": info.get("cpu_util_pct"),
                        "gpu_util_pct": info.get("gpu_util_pct"),
                        "free_ram_gb": info.get("free_ram_gb"),
                        "ntp_ok": info.get("ntp_ok"),
                    }
            except Exception:
                pass

    idle_sec = _read_idle_sec_windows()
    free_ram_gb = _read_free_ram_gb_windows()
    mode = "MODE_A_OWNER_ACTIVE"
    if idle_sec is not None and free_ram_gb is not None:
        idle_ready = (idle_sec >= 900.0) or (in_overnight and idle_sec >= 300.0)
        if idle_ready and free_ram_gb >= 6.0 and in_overnight:
            mode = "MODE_B_IDLE_OVERNIGHT"

    return {
        "mode": mode,
        "priority": "NORMAL" if mode == "MODE_B_IDLE_OVERNIGHT" else "BELOW_NORMAL",
        "source": "local_offline_sensor" if offline else "local_fallback_sensor",
        "in_overnight_window_ict": in_overnight,
        "idle_sec": idle_sec,
        "free_ram_gb": free_ram_gb,
    }


def _subproc_creationflags(priority: str) -> int:
    if os.name != "nt":
        return 0
    prio_flag = NORMAL_PRIORITY_CLASS if priority == "NORMAL" else BELOW_NORMAL_PRIORITY_CLASS
    return prio_flag | CREATE_NO_WINDOW_FLAG


def _run_cmd(
    cmd: list[str],
    *,
    root: Path,
    priority: str,
    timeout_sec: int,
) -> tuple[int, str, str, float]:
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(root),
            env=build_subproc_env(root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=max(5, int(timeout_sec)),
            creationflags=_subproc_creationflags(priority),
            check=False,
        )
        return int(proc.returncode), proc.stdout or "", proc.stderr or "", round(time.perf_counter() - t0, 3)
    except subprocess.TimeoutExpired as exc:
        return 124, "", f"timeout_after_{timeout_sec}s:{exc}", round(time.perf_counter() - t0, 3)
    except OSError as exc:
        return 127, "", f"os_error:{exc}", round(time.perf_counter() - t0, 3)


def _extract_json_object(stdout: str) -> dict[str, Any] | None:
    text = stdout.strip()
    if not text:
        return None
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                parsed = json.loads(text[start : end + 1])
                return parsed if isinstance(parsed, dict) else None
            except json.JSONDecodeError:
                return None
        return None


def _run_system_doctor_fast(
    *,
    root: Path,
    py: str,
    priority: str,
    dry_run: bool,
    timeout_sec: int,
) -> dict[str, Any]:
    script = root / "tooling/ai-engines/system_doctor.py"
    cmd = [py, "-X", "utf8", str(script), "--mode", "fast", "--json"]
    if not script.is_file():
        return {
            "id": "system_doctor_fast",
            "status": "SKIPPED",
            "ok": True,
            "detail": "system_doctor.py not found",
            "seconds": 0.0,
        }
    if dry_run:
        return {
            "id": "system_doctor_fast",
            "status": "DRY_RUN",
            "ok": True,
            "planned_cmd": [
                Path(py).name,
                "-X",
                "utf8",
                "tooling/ai-engines/system_doctor.py",
                "--mode",
                "fast",
                "--json",
            ],
            "priority": priority,
            "detail": "Dry-run: system_doctor --mode fast planned (not executed)",
            "seconds": 0.0,
        }

    rc, out, err, sec = _run_cmd(cmd, root=root, priority=priority, timeout_sec=timeout_sec)
    parsed = _extract_json_object(out)
    if parsed is not None:
        all_ok = bool(parsed.get("all_ok", False)) and rc == 0
        raw_checks = parsed.get("checks")
        checks: list[Any] = raw_checks if isinstance(raw_checks, list) else []
        passed_cnt = sum(1 for c in checks if isinstance(c, dict) and c.get("ok"))
        failed_names = [str(c.get("name")) for c in checks if isinstance(c, dict) and not c.get("ok")]
        return {
            "id": "system_doctor_fast",
            "status": "PASS" if all_ok else "FAIL",
            "ok": all_ok,
            "returncode": rc,
            "seconds": sec,
            "checks_passed": passed_cnt,
            "checks_total": len(checks),
            "failed_checks": failed_names,
            "detail": f"{passed_cnt}/{len(checks)} checks PASS" if all_ok else f"FAIL: {', '.join(failed_names) or rc}",
        }
    return {
        "id": "system_doctor_fast",
        "status": "FAIL",
        "ok": False,
        "returncode": rc,
        "seconds": sec,
        "detail": scrub_text(err or out or f"system_doctor exited rc={rc}", max_len=300),
    }


def _run_check_architecture_strict(
    *,
    root: Path,
    py: str,
    priority: str,
    dry_run: bool,
    timeout_sec: int,
) -> dict[str, Any]:
    script = root / "tooling/check_architecture.py"
    cmd = [py, "-X", "utf8", str(script), "--strict", "--json"]
    if not script.is_file():
        return {
            "id": "check_architecture_strict",
            "status": "SKIPPED",
            "ok": True,
            "detail": "check_architecture.py not found",
            "seconds": 0.0,
        }
    if dry_run:
        return {
            "id": "check_architecture_strict",
            "status": "DRY_RUN",
            "ok": True,
            "planned_cmd": [Path(py).name, "-X", "utf8", "tooling/check_architecture.py", "--strict", "--json"],
            "priority": priority,
            "detail": "Dry-run: check_architecture --strict planned (not executed)",
            "seconds": 0.0,
        }

    rc, out, err, sec = _run_cmd(cmd, root=root, priority=priority, timeout_sec=timeout_sec)
    parsed = _extract_json_object(out)
    if parsed is not None:
        passed = bool(parsed.get("passed", False)) and rc == 0
        err_cnt = int(parsed.get("error_count", 0) or 0)
        warn_cnt = int(parsed.get("warning_count", 0) or 0)
        return {
            "id": "check_architecture_strict",
            "status": "PASS" if passed else "FAIL",
            "ok": passed,
            "returncode": rc,
            "seconds": sec,
            "error_count": err_cnt,
            "warning_count": warn_cnt,
            "by_rule": parsed.get("by_rule", {}),
            "detail": f"STRICT {'PASS' if passed else 'FAIL'} ({err_cnt} errors, {warn_cnt} warnings)",
        }
    return {
        "id": "check_architecture_strict",
        "status": "FAIL",
        "ok": False,
        "returncode": rc,
        "seconds": sec,
        "detail": scrub_text(err or out or f"check_architecture exited rc={rc}", max_len=300),
    }


def _check_brain_index_health(
    *,
    root: Path,
    py: str,
    priority: str,
    dry_run: bool,
    refresh_brain: bool,
    timeout_sec: int,
) -> dict[str, Any]:
    """Strictly read-only Knowledge Brain health audit (unless --refresh-brain is requested)."""
    t0 = time.perf_counter()
    db_path = root / ".runtime/knowledge/brain.sqlite3"
    vec_path = root / ".runtime/knowledge/brain_vec.npz"
    brain_cli = root / "tooling/knowledge/brain_cli.py"

    if dry_run:
        return {
            "id": "brain_index_health",
            "status": "DRY_RUN",
            "ok": True,
            "db_present": db_path.is_file(),
            "vec_present": vec_path.is_file(),
            "planned_cmd": [
                Path(py).name,
                "-X",
                "utf8",
                "tooling/knowledge/brain_cli.py",
                "index" if refresh_brain else "audit-data",
            ],
            "detail": (
                f"Dry-run: brain_cli {'index' if refresh_brain else 'audit-data'} planned "
                f"(db_present={db_path.is_file()}, vec_present={vec_path.is_file()})"
            ),
            "seconds": round(time.perf_counter() - t0, 3),
        }

    files_cnt: int | None = None
    chunks_cnt: int | None = None
    sqlite_err: str | None = None
    if db_path.is_file():
        con: sqlite3.Connection | None = None
        try:
            uri = f"file:{db_path.resolve().as_posix()}?mode=ro"
            con = sqlite3.connect(uri, uri=True, timeout=5.0)
            row_f = con.execute("SELECT COUNT(*) FROM files").fetchone()
            row_c = con.execute("SELECT COUNT(*) FROM chunks").fetchone()
            files_cnt = int(row_f[0]) if row_f else 0
            chunks_cnt = int(row_c[0]) if row_c else 0
        except Exception as exc:
            sqlite_err = f"{type(exc).__name__}:{exc}"
        finally:
            if con is not None:
                con.close()

    audit_payload: dict[str, Any] | None = None
    rc = 0
    if brain_cli.is_file():
        subcmd = "index" if refresh_brain else "audit-data"
        rc, out, err, _ = _run_cmd(
            [py, "-X", "utf8", str(brain_cli), subcmd],
            root=root,
            priority=priority,
            timeout_sec=min(timeout_sec, 90),
        )
        audit_payload = _extract_json_object(out)
        if rc != 0 and sqlite_err is None:
            sqlite_err = scrub_text(err or out or f"brain_cli rc={rc}", max_len=240)

    if sqlite_err:
        return {
            "id": "brain_index_health",
            "status": "FAIL",
            "ok": False,
            "returncode": rc,
            "seconds": round(time.perf_counter() - t0, 3),
            "detail": scrub_text(sqlite_err, max_len=260),
        }

    if not db_path.is_file() or not vec_path.is_file():
        return {
            "id": "brain_index_health",
            "status": "WARN",
            "ok": True,
            "db_present": db_path.is_file(),
            "vec_present": vec_path.is_file(),
            "seconds": round(time.perf_counter() - t0, 3),
            "detail": "COLD index (run brain_cli.py index to populate .runtime/knowledge)",
        }

    broken = int((audit_payload or {}).get("broken_knowledge_links_count", 0) or 0)
    near_dups = int((audit_payload or {}).get("near_duplicate_topic_headings_count", 0) or 0)
    ready = bool((files_cnt or 0) > 0 and (chunks_cnt or 0) > 0)
    status = "PASS" if (ready and broken == 0) else ("WARN" if ready else "FAIL")
    return {
        "id": "brain_index_health",
        "status": status,
        "ok": status != "FAIL",
        "files_indexed": files_cnt,
        "chunks_indexed": chunks_cnt,
        "broken_knowledge_links": broken,
        "near_duplicate_headings": near_dups,
        "seconds": round(time.perf_counter() - t0, 3),
        "detail": (
            f"READY ({files_cnt} files, {chunks_cnt} chunks, broken_links={broken}, near_dups={near_dups})"
            if ready
            else "EMPTY brain index"
        ),
    }


def _run_optional_radar_hooks(
    *,
    root: Path,
    py: str,
    priority: str,
    offline: bool,
    dry_run: bool,
    timeout_sec: int,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for spec in OPTIONAL_RADAR_HOOKS:
        hook_id = spec["id"]
        script_path = root / spec["script"]
        output_path = root / spec["output"]
        if not script_path.is_file():
            results.append(
                {
                    "id": hook_id,
                    "script": spec["script"],
                    "present": False,
                    "status": "SKIPPED_NOT_PRESENT",
                    "ok": True,
                    "output_present": output_path.is_file(),
                    "detail": f"Optional hook not present on disk ({spec['script']}) — skipped gracefully",
                    "seconds": 0.0,
                }
            )
            continue

        args = [py, "-X", "utf8", str(script_path)]
        if offline:
            args.append("--offline")
        if dry_run:
            args.append("--dry-run")
            results.append(
                {
                    "id": hook_id,
                    "script": spec["script"],
                    "present": True,
                    "status": "DRY_RUN",
                    "ok": True,
                    "output_present": output_path.is_file(),
                    "planned_cmd": [Path(py).name, "-X", "utf8", spec["script"], *args[4:]],
                    "detail": f"Dry-run: optional hook {hook_id} detected and planned",
                    "seconds": 0.0,
                }
            )
            continue

        rc, out, err, sec = _run_cmd(args, root=root, priority=priority, timeout_sec=min(timeout_sec, 90))
        ok = rc == 0
        results.append(
            {
                "id": hook_id,
                "script": spec["script"],
                "present": True,
                "status": "PASS" if ok else "WARN",
                "ok": True,  # Optional radar degradation should warn, not fail-crash core hygiene
                "returncode": rc,
                "output_present": output_path.is_file(),
                "seconds": sec,
                "detail": (
                    f"{hook_id} completed rc=0 ({sec:.2f}s)"
                    if ok
                    else f"{hook_id} non-zero rc={rc}: {scrub_text(err or out, max_len=200)}"
                ),
            }
        )
    return results


def _check_x13_readonly_status(
    *,
    root: Path,
    offline: bool,
    dry_run: bool,
) -> dict[str, Any]:
    if offline:
        return {
            "id": "x13_worker_status",
            "status": "SKIPPED_OFFLINE",
            "ok": True,
            "ssh_attempted": False,
            "detail": "Offline mode: skipped <X13_WORKER> SSH probe",
        }
    if dry_run:
        return {
            "id": "x13_worker_status",
            "status": "DRY_RUN",
            "ok": True,
            "ssh_attempted": False,
            "detail": "Dry-run: <X13_WORKER> read-only SSH probe planned (not executed)",
        }

    router = _load_module_from_path(
        "_naqex_compute_router_x13",
        root / "tooling/ai-engines/ops_cloud/compute_router.py",
    )
    if router is None or not hasattr(router, "probe_x13_worker"):
        return {
            "id": "x13_worker_status",
            "status": "SKIPPED_NOT_PRESENT",
            "ok": True,
            "ssh_attempted": False,
            "detail": "compute_router.py not available for <X13_WORKER> probe",
        }

    try:
        probe = router.probe_x13_worker()
        if not isinstance(probe, dict):
            return {
                "id": "x13_worker_status",
                "status": "WARN",
                "ok": True,
                "ssh_attempted": True,
                "detail": "Unexpected <X13_WORKER> probe response shape",
            }
        reachable = bool(probe.get("reachable", False))
        eligible = bool(probe.get("eligible", False))
        reasons = list(probe.get("ineligible_reasons") or [])
        return {
            "id": "x13_worker_status",
            "status": "PASS" if (reachable and eligible) else "WARN",
            "ok": True,
            "ssh_attempted": True,
            "reachable": reachable,
            "eligible": eligible,
            "transport": probe.get("transport"),
            "ac_online": probe.get("ac_online"),
            "cpu_util_pct": probe.get("cpu_util_pct"),
            "free_ram_gb": probe.get("free_ram_gb"),
            "disk_free_gb": probe.get("disk_free_gb"),
            "ntp_offset_ms": probe.get("ntp_offset_ms"),
            "forbidden_files": probe.get("forbidden_files"),
            "ineligible_reasons": [scrub_text(r, max_len=120) for r in reasons],
            "detail": (
                f"ELIGIBLE ({probe.get('transport')}, RAM={probe.get('free_ram_gb')}GB)"
                if (reachable and eligible)
                else f"UNAVAILABLE/INELIGIBLE: {', '.join(str(r) for r in reasons) or 'unreachable'}"
            ),
        }
    except Exception as exc:
        return {
            "id": "x13_worker_status",
            "status": "WARN",
            "ok": True,
            "ssh_attempted": True,
            "detail": f"<X13_WORKER> probe exception: {scrub_text(exc, max_len=200)}",
        }


def run_nightly_quant_ops(
    *,
    root: Path = ROOT,
    out_path: Path | None = DEFAULT_OUT_PATH,
    offline: bool = False,
    dry_run: bool = False,
    refresh_brain: bool = False,
    timeout_sec: int = 180,
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    """Execute nightly read-only quant & hygiene checks and persist sanitized JSON receipt."""
    t0 = time.perf_counter()
    now = now_utc or datetime.now(UTC)
    now_ict = now.astimezone(VN_TZ)
    py = resolve_python(root)
    dev_mode_info = detect_dev_pc_mode(root=root, offline=offline, now_utc=now)
    priority = str(dev_mode_info["priority"])

    checks = [
        _run_system_doctor_fast(root=root, py=py, priority=priority, dry_run=dry_run, timeout_sec=timeout_sec),
        _run_check_architecture_strict(root=root, py=py, priority=priority, dry_run=dry_run, timeout_sec=timeout_sec),
        _check_brain_index_health(
            root=root,
            py=py,
            priority=priority,
            dry_run=dry_run,
            refresh_brain=refresh_brain,
            timeout_sec=timeout_sec,
        ),
    ]
    optional_radars = _run_optional_radar_hooks(
        root=root,
        py=py,
        priority=priority,
        offline=offline,
        dry_run=dry_run,
        timeout_sec=timeout_sec,
    )
    x13_status = _check_x13_readonly_status(root=root, offline=offline, dry_run=dry_run)

    all_items = [*checks, *optional_radars, x13_status]
    counts = {
        "pass": sum(1 for x in all_items if x.get("status") == "PASS"),
        "warn": sum(1 for x in all_items if x.get("status") == "WARN"),
        "fail": sum(1 for x in all_items if x.get("status") == "FAIL"),
        "skipped": sum(1 for x in all_items if str(x.get("status", "")).startswith("SKIPPED")),
        "dry_run": sum(1 for x in all_items if x.get("status") == "DRY_RUN"),
    }

    if dry_run:
        overall_status = "DRY_RUN"
    elif counts["fail"] > 0:
        overall_status = "FAIL"
    elif counts["warn"] > 0:
        overall_status = "WARN"
    else:
        overall_status = "PASS"

    payload: dict[str, Any] = {
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
        "dev_pc_mode": dev_mode_info["mode"],
        "process_priority": priority,
        "dev_pc": dev_mode_info,
        "overall_status": overall_status,
        "counts": counts,
        "checks": checks,
        "optional_radars": optional_radars,
        "x13_status": x13_status,
        "elapsed_sec": round(time.perf_counter() - t0, 3),
    }

    if out_path is not None:
        atomic_write_json(out_path, payload)

    return payload


def make_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Naqex 01:30 Nightly Quant & Hygiene Runner (Read-Only | OrderSend=0).",
    )
    ap.add_argument("--root", type=Path, default=ROOT, help="Workspace root override")
    ap.add_argument("--out", type=Path, default=None, help="JSON receipt output path")
    ap.add_argument("--offline", action="store_true", help="Skip SSH and external network calls")
    ap.add_argument("--dry-run", action="store_true", help="Plan checks without executing heavy subprocesses")
    ap.add_argument("--refresh-brain", action="store_true", help="Run brain_cli.py index instead of read-only audit")
    ap.add_argument("--timeout-sec", type=int, default=180, help="Per-check subprocess timeout in seconds")
    ap.add_argument("--json", action="store_true", dest="as_json", help="Emit full JSON payload to stdout")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = make_parser().parse_args(argv)
    out_path = args.out if args.out is not None else (args.root / ".runtime/automation/nightly_latest.json")
    payload = run_nightly_quant_ops(
        root=args.root,
        out_path=out_path,
        offline=args.offline,
        dry_run=args.dry_run,
        refresh_brain=args.refresh_brain,
        timeout_sec=args.timeout_sec,
    )
    if args.as_json:
        print(json.dumps(sanitize_value(payload), indent=2, ensure_ascii=False))
    else:
        c = payload["counts"]
        print(
            f"[nightly_quant_ops] status={payload['overall_status']} mode={payload['dev_pc_mode']} "
            f"prio={payload['process_priority']} pass={c['pass']} warn={c['warn']} fail={c['fail']} "
            f"skip={c['skipped']} dry_run={c['dry_run']} OrderSend={ORDER_SEND_COUNT}"
        )
    return 1 if payload["overall_status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())

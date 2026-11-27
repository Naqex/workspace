"""Zero-Token 15-Minute Local Watchdog + Active Push Alerts (OrderSend = 0).

Checks:
  1. PC Dev local NTP offset (< 1000ms)
  2. Disk free space (D: or workspace anchor)
  3. <X13_WORKER> read-only health (optional; skipped on --skip-ssh / --offline)
  4. Heroku Deadman `/health` & `/api/status` via `.runtime/ops-cloud/heroku_connection_local.json`
     or `NAQEX_DEADMAN_URL` (read-only, strictly scrubbed)
  5. Stale `.lock` files under `.runtime/` and `.tmp/`

Active Alert Wiring (reuses `ops_cloud/heroku_deadman/app.py` directly):
  - Imports `dispatch_alert_message` & `_scrub_secret_text` from `ops_cloud.heroku_deadman.app`
  - Reads `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `ALERT_WEBHOOK_URL` from environment
  - Degrades gracefully (`configured: false`, exit 0) when unset on PC Dev
  - Enforces alert cooldown (`900s` default) to prevent alert storms
  - NEVER dispatches live alerts during `--offline` or `--dry-run`

Atomically persists sanitized state (0 raw IPs/tokens/URLs/usernames) to:
  - `.runtime/automation/watchdog_latest.json`
  - `.runtime/ops-cloud/node1_watchdog_state.json`
  - `.runtime/ops-cloud/telegram_alert_state.json`
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

ORDER_SEND_CAPABLE: bool = False
ORDER_SEND_COUNT: int = 0
SCHEMA_WATCHDOG: str = "naqex-watchdog-15m-v1"
SCHEMA_NODE1_STATE: str = "naqex-node1-watchdog-state-v1"
SCHEMA_ALERT_STATE: str = "naqex-telegram-alert-state-v1"

DEFAULT_COOLDOWN_SEC: int = 900
DEFAULT_NTP_MAX_MS: float = 1000.0
DEFAULT_DISK_WARN_GB: float = 15.0
DEFAULT_DISK_CRIT_GB: float = 5.0
DEFAULT_STALE_LOCK_SEC: int = 3600
_BELOW_NORMAL_PRIORITY_CLASS: int = 0x00004000
_PROCESS_QUERY_LIMITED_INFORMATION: int = 0x1000

ROOT = Path(__file__).resolve().parents[2]
_AI_ENGINES_DIR = ROOT / "tooling/ai-engines"
if str(_AI_ENGINES_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_ENGINES_DIR))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ops_cloud.heroku_deadman.app import _scrub_secret_text, dispatch_alert_message  # noqa: E402

_NTP_OFFSET_RE = re.compile(r"([+-]\d+(?:\.\d+)?)s\b")
_LAN_IP_RE = re.compile(r"\b(?:192" + r"\.168|10\.\d{1,3})\.\d{1,3}\.\d{1,3}\b")
_CGNAT_IP_RE = re.compile(r"\b100" + r"\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d{1,3}\.\d{1,3}\b")
_HEROKU_APP_RE = re.compile(r"(?i)\b" + "naqex-" + "deadman-" + r"[a-z0-9-]+\b")
_TG_HANDLE_RE = re.compile(r"(?i)@?" + "naqex_" + "guard_" + r"bot\b")
_WIN_USER_RE = re.compile(
    r"(?i)(?:[A-Z]:|/mnt/[a-z])[\\/]Users[\\/](?!<|YOUR_|user\b|username\b|example\b|public\b|default\b)[A-Za-z0-9._-]+"
)
_GH_TOKEN_RE = re.compile(r"\b(?:" + "ghp_" + r"[A-Za-z0-9]{20,}|" + "github_pat_" + r"[A-Za-z0-9_]{20,})\b")


def sanitize_opsec_text(raw: Any, *, secrets: tuple[str, ...] = ()) -> str:
    """Scrub secrets, URLs, private IPs, Heroku app names, bot handles, and local user paths."""
    out = _scrub_secret_text(str(raw or ""), secrets=secrets)
    out = _GH_TOKEN_RE.sub("<REDACTED_GH_TOKEN>", out)
    out = _LAN_IP_RE.sub("<LAN_IP>", out)
    out = _CGNAT_IP_RE.sub("<TAILSCALE_IP>", out)
    out = _HEROKU_APP_RE.sub("<HEROKU_DEADMAN_APP>", out)
    out = _TG_HANDLE_RE.sub("<TELEGRAM_GUARD_BOT>", out)
    out = _WIN_USER_RE.sub("<USER_HOME>", out)
    return out


def sanitize_payload(obj: Any, *, secrets: tuple[str, ...] = ()) -> Any:
    """Recursively scrub all string values inside a JSON payload."""
    if isinstance(obj, str):
        return sanitize_opsec_text(obj, secrets=secrets)
    if isinstance(obj, dict):
        return {str(k): sanitize_payload(v, secrets=secrets) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize_payload(v, secrets=secrets) for v in obj]
    if isinstance(obj, tuple):
        return [sanitize_payload(v, secrets=secrets) for v in obj]
    return obj


def _utc_now_iso(now_ts: float | None = None) -> str:
    dt = datetime.fromtimestamp(now_ts, tz=UTC) if now_ts is not None else datetime.now(UTC)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


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


def set_below_normal_priority() -> bool:
    """Best-effort BELOW_NORMAL process priority on Windows for Mode-A owner friendliness."""
    if os.name != "nt":
        return False
    try:
        k32 = ctypes.windll.kernel32
        handle = k32.GetCurrentProcess()
        return bool(k32.SetPriorityClass(handle, _BELOW_NORMAL_PRIORITY_CLASS))
    except Exception:
        return False


def check_local_ntp(
    *,
    offline: bool = False,
    max_offset_ms: float = DEFAULT_NTP_MAX_MS,
) -> dict[str, Any]:
    """Check PC Dev NTP clock drift against `< 1000ms` threshold."""
    if max_offset_ms <= 0:
        raise ValueError(f"max_offset_ms must be > 0, got {max_offset_ms!r}")
    if offline:
        return {
            "status": "SKIPPED_OFFLINE",
            "ok": True,
            "offset_ms": None,
            "threshold_ms": max_offset_ms,
            "reason": None,
        }
    if os.name != "nt":
        return {
            "status": "UNSUPPORTED_OS",
            "ok": True,
            "offset_ms": None,
            "threshold_ms": max_offset_ms,
            "reason": None,
        }

    for srv in ("time.cloudflare.com", "time.google.com"):
        try:
            proc = subprocess.run(
                ["w32tm", "/stripchart", f"/computer:{srv}", "/samples:1", "/dataonly"],
                capture_output=True,
                text=True,
                timeout=1.6,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            match = _NTP_OFFSET_RE.search(proc.stdout or "")
            if match:
                offset_ms = round(float(match.group(1)) * 1000.0, 1)
                passed = abs(offset_ms) < max_offset_ms
                return {
                    "status": "OK" if passed else "CRITICAL",
                    "ok": passed,
                    "offset_ms": offset_ms,
                    "threshold_ms": max_offset_ms,
                    "reason": None if passed else f"DEV_PC_NTP_DRIFT_{offset_ms:+.1f}ms",
                }
        except Exception:
            continue

    return {
        "status": "WARN",
        "ok": False,
        "offset_ms": None,
        "threshold_ms": max_offset_ms,
        "reason": "DEV_PC_NTP_UNAVAILABLE",
    }


def check_disk_space(
    root: Path,
    *,
    drive: str | None = None,
    warn_gb: float = DEFAULT_DISK_WARN_GB,
    crit_gb: float = DEFAULT_DISK_CRIT_GB,
) -> dict[str, Any]:
    """Check free disk space on D: (or workspace drive anchor)."""
    if drive:
        anchor = Path(drive)
    elif os.name == "nt" and Path("D:\\").exists():
        anchor = Path("D:\\")
    else:
        anchor = Path(root.anchor or str(root))

    if not anchor.exists():
        anchor = Path(root.anchor or str(root))

    usage = shutil.disk_usage(anchor)
    gib = float(1024**3)
    free_gb = round(usage.free / gib, 2)
    total_gb = round(usage.total / gib, 2)
    used_pct = round(((usage.total - usage.free) / usage.total) * 100.0, 1) if usage.total > 0 else 0.0

    drive_label = anchor.drive or str(anchor.anchor or "/")
    if free_gb < crit_gb:
        status = "CRITICAL"
        ok = False
        reason: str | None = f"DISK_CRITICAL_{drive_label}_{free_gb:.1f}GB"
    elif free_gb < warn_gb:
        status = "WARN"
        ok = False
        reason = f"DISK_LOW_{drive_label}_{free_gb:.1f}GB"
    else:
        status = "OK"
        ok = True
        reason = None

    return {
        "status": status,
        "ok": ok,
        "drive": sanitize_opsec_text(drive_label),
        "free_gb": free_gb,
        "total_gb": total_gb,
        "used_pct": used_pct,
        "warn_gb": warn_gb,
        "crit_gb": crit_gb,
        "reason": reason,
    }


def check_x13_health(
    *,
    offline: bool = False,
    skip_ssh: bool = False,
) -> dict[str, Any]:
    """Read-only `<X13_WORKER>` health check (reusing ops_cloud.compute_router)."""
    if offline:
        return {
            "worker": "<X13_WORKER>",
            "status": "SKIPPED_OFFLINE",
            "ok": True,
            "reachable": None,
            "eligible": None,
            "reason": None,
        }
    if skip_ssh:
        return {
            "worker": "<X13_WORKER>",
            "status": "SKIPPED_SSH",
            "ok": True,
            "reachable": None,
            "eligible": None,
            "reason": None,
        }

    try:
        from ops_cloud.compute_router import probe_x13_worker

        raw = probe_x13_worker(connect_timeout=2, timeout=3.5)
    except Exception as exc:
        return {
            "worker": "<X13_WORKER>",
            "status": "DEGRADED_OPTIONAL",
            "ok": True,
            "reachable": False,
            "eligible": False,
            "reason": None,
            "error": f"X13_PROBE_ERR:{sanitize_opsec_text(str(exc))[:120]}",
        }

    reachable = bool(raw.get("reachable", False))
    forbidden = int(raw.get("forbidden_files") or 0)
    if forbidden > 0:
        status = "CRITICAL"
        ok = False
        reason: str | None = f"X13_FORBIDDEN_FILES={forbidden}"
    elif not reachable:
        status = "OFFLINE_OPTIONAL"
        ok = True
        reason = None
    else:
        status = "OK" if raw.get("eligible") else "BUSY_OR_INELIGIBLE"
        ok = True
        reason = None

    return sanitize_payload(
        {
            "worker": "<X13_WORKER>",
            "status": status,
            "ok": ok,
            "reachable": reachable,
            "ssh_alias": raw.get("ssh_alias"),
            "transport": raw.get("transport"),
            "eligible": raw.get("eligible"),
            "ac_online": raw.get("ac_online"),
            "cpu_util_pct": raw.get("cpu_util_pct"),
            "free_ram_gb": raw.get("free_ram_gb"),
            "disk_free_gb": raw.get("disk_free_gb"),
            "ntp_offset_ms": raw.get("ntp_offset_ms"),
            "forbidden_files": forbidden,
            "ineligible_reasons": list(raw.get("ineligible_reasons") or []),
            "reason": reason,
        }
    )


def _normalize_deadman_origin(raw_url: str) -> str:
    """Normalize any Deadman URL (incl. `/api/heartbeat`, `/api/status`, `/health`) to its base origin."""
    parsed = urlparse(str(raw_url or "").strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    path = (parsed.path or "").rstrip("/")
    for suffix in ("/api/heartbeat", "/api/status", "/health"):
        if path.lower().endswith(suffix):
            path = path[: -len(suffix)].rstrip("/")
    return f"{parsed.scheme}://{parsed.netloc}{path}"


def _load_heroku_connection(root: Path) -> tuple[str, str, str, tuple[str, ...]]:
    """Safely load Heroku Deadman origin & view_token without ever persisting secrets."""
    env_url = os.environ.get("NAQEX_DEADMAN_URL", "").strip()
    env_token = os.environ.get("NAQEX_VIEW_TOKEN", "").strip()
    cfg_path = root / ".runtime/ops-cloud/heroku_connection_local.json"
    cfg = _safe_read_json(cfg_path) if cfg_path.is_file() else {}

    cfg_web_url = str(cfg.get("web_url") or "").strip()
    cfg_hb_url = str(cfg.get("heartbeat_endpoint") or "").strip()
    dash_url = str(cfg.get("mobile_dashboard_url") or "").strip()
    app_name = str(cfg.get("app_name") or "").strip()
    raw_web_url = env_url or cfg_web_url or cfg_hb_url or dash_url
    view_token = env_token or str(cfg.get("view_token") or "").strip()

    if not view_token and dash_url:
        view_token = (parse_qs(urlparse(dash_url).query).get("token") or [""])[0].strip()
    if not view_token and raw_web_url:
        view_token = (parse_qs(urlparse(raw_web_url).query).get("token") or [""])[0].strip()

    web_base = _normalize_deadman_origin(raw_web_url)
    parsed = urlparse(web_base)
    if env_url and web_base:
        source = "ENV"
    elif web_base:
        source = "LOCAL_CONFIG"
    else:
        source = "UNCONFIGURED"

    secrets = tuple(
        s
        for s in (
            env_url,
            env_token,
            cfg_web_url,
            cfg_hb_url,
            raw_web_url,
            dash_url,
            app_name,
            web_base,
            view_token,
            parsed.netloc,
        )
        if s
    )
    return web_base, view_token, source, secrets


def check_heroku_deadman(
    root: Path,
    *,
    offline: bool = False,
    timeout_sec: float = 2.5,
) -> dict[str, Any]:
    """Read-only probe of Heroku Deadman `/health` and `/api/status` (zero leaked URLs/tokens)."""
    web_base, view_token, source, secrets = _load_heroku_connection(root)
    if not web_base:
        return {
            "configured": False,
            "source": "UNCONFIGURED",
            "status": "UNCONFIGURED",
            "ok": True,
            "health_ok": None,
            "status_ok": None,
            "node1": None,
            "reason": None,
            "error": None,
        }

    if offline:
        return {
            "configured": True,
            "source": source,
            "status": "SKIPPED_OFFLINE",
            "ok": True,
            "health_ok": None,
            "status_ok": None,
            "node1": None,
            "reason": None,
            "error": None,
        }

    health_ok = False
    status_ok = False
    node1: dict[str, Any] | None = None
    errors: list[str] = []

    try:
        req_h = urllib.request.Request(
            f"{web_base}/health",
            headers={"User-Agent": "Naqex-Watchdog/1.0"},
            method="GET",
        )
        with urllib.request.urlopen(req_h, timeout=timeout_sec) as resp:
            health_ok = 200 <= int(resp.status) < 300
    except Exception as exc:
        errors.append("health:" + sanitize_opsec_text(str(exc), secrets=secrets)[:140])

    try:
        headers = {"User-Agent": "Naqex-Watchdog/1.0"}
        if view_token:
            headers["X-Naqex-View-Token"] = view_token
        req_s = urllib.request.Request(f"{web_base}/api/status", headers=headers, method="GET")
        with urllib.request.urlopen(req_s, timeout=timeout_sec) as resp:
            if 200 <= int(resp.status) < 300:
                status_ok = True
                data = json.loads(resp.read().decode("utf-8"))
                nodes = data.get("nodes") if isinstance(data, dict) else []
                if isinstance(nodes, list):
                    preferred = next(
                        (n for n in nodes if isinstance(n, dict) and n.get("account_label") == "NAQEX_NODE1"),
                        None,
                    ) or (nodes[0] if nodes and isinstance(nodes[0], dict) else None)
                    if isinstance(preferred, dict):
                        node1 = {
                            "account_label": str(preferred.get("account_label") or "NAQEX_NODE1"),
                            "status": str(preferred.get("status") or "UNKNOWN"),
                            "age_sec": preferred.get("age_sec"),
                            "mt5_running": preferred.get("mt5_running"),
                            "balance": preferred.get("balance"),
                            "equity": preferred.get("equity"),
                            "daily_dd_pct": preferred.get("daily_dd_pct"),
                            "static_dd_pct": preferred.get("static_dd_pct"),
                            "open_positions": preferred.get("open_positions"),
                            "orphan_no_sl": preferred.get("orphan_no_sl"),
                            "regime": preferred.get("regime"),
                            "kill_switch": preferred.get("kill_switch"),
                            "last_seen_utc": preferred.get("last_seen_utc"),
                        }
    except Exception as exc:
        errors.append("api_status:" + sanitize_opsec_text(str(exc), secrets=secrets)[:140])

    reasons: list[str] = []
    if not health_ok:
        reasons.append("HEROKU_DEADMAN_HEALTH_FAIL")
    if not status_ok:
        reasons.append("HEROKU_DEADMAN_STATUS_FAIL")
    if isinstance(node1, dict):
        if str(node1.get("status") or "").upper() == "CRITICAL":
            reasons.append("NODE1_STATUS_CRITICAL")
        if node1.get("mt5_running") is False:
            reasons.append("NODE1_MT5_DOWN")
        if bool(node1.get("kill_switch", False)):
            reasons.append("NODE1_KILL_SWITCH_ACTIVE")
        if int(node1.get("orphan_no_sl") or 0) > 0:
            reasons.append(f"NODE1_ORPHAN_NO_SL={int(node1['orphan_no_sl'])}")
        age_val = node1.get("age_sec")
        if isinstance(age_val, (int, float)) and not isinstance(age_val, bool) and float(age_val) > 180.0:
            reasons.append(f"NODE1_HEARTBEAT_STALE={int(age_val)}s")

    overall_ok = len(reasons) == 0
    return sanitize_payload(
        {
            "configured": True,
            "source": source,
            "status": "OK" if overall_ok else "CRITICAL",
            "ok": overall_ok,
            "health_ok": health_ok,
            "status_ok": status_ok,
            "node1": node1,
            "reason": "; ".join(reasons) if reasons else None,
            "error": "; ".join(errors) if errors else None,
        },
        secrets=secrets,
    )


def _is_pid_alive(pid: int) -> bool:
    if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0:
        return False
    if os.name == "nt":
        try:
            k32 = ctypes.windll.kernel32
            handle = k32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if not handle:
                return False
            try:
                exit_code = ctypes.c_ulong(0)
                if k32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                    return int(exit_code.value) == 259  # STILL_ACTIVE
                return True
            finally:
                k32.CloseHandle(handle)
        except Exception:
            return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def check_stale_locks(
    root: Path,
    *,
    stale_after_sec: int = DEFAULT_STALE_LOCK_SEC,
    now_ts: float | None = None,
) -> dict[str, Any]:
    """Scan bounded runtime/tmp directories for stale `.lock` files."""
    if stale_after_sec < 1:
        raise ValueError(f"stale_after_sec must be >= 1, got {stale_after_sec!r}")
    now = float(now_ts if now_ts is not None else time.time())
    scan_dirs = (
        root / ".runtime/automation",
        root / ".runtime/ops-cloud",
        root / ".runtime/locks",
        root / ".tmp",
    )

    locks_found = 0
    stale_locks: list[dict[str, Any]] = []
    for base in scan_dirs:
        if not base.is_dir():
            continue
        try:
            entries = list(base.iterdir())
        except OSError:
            continue
        for entry in entries:
            if not entry.is_file() or entry.suffix.lower() != ".lock":
                continue
            locks_found += 1
            try:
                age_sec = max(0.0, now - entry.stat().st_mtime)
            except OSError:
                continue
            rel = entry.relative_to(root).as_posix()
            pid_dead = False
            parsed = _safe_read_json(entry)
            pid = parsed.get("pid")
            if isinstance(pid, int) and not isinstance(pid, bool) and pid > 0:
                pid_dead = not _is_pid_alive(pid)
            if pid_dead or age_sec > float(stale_after_sec):
                stale_locks.append(
                    {
                        "path": sanitize_opsec_text(rel),
                        "age_sec": round(age_sec, 1),
                        "reason": "DEAD_PID" if pid_dead else "AGE_EXCEEDED",
                    }
                )

    ok = len(stale_locks) == 0
    return {
        "status": "OK" if ok else "WARN",
        "ok": ok,
        "locks_found": locks_found,
        "stale_count": len(stale_locks),
        "stale_locks": stale_locks[:20],
        "stale_after_sec": stale_after_sec,
        "reason": f"STALE_LOCKS={len(stale_locks)}" if stale_locks else None,
    }


def evaluate_and_dispatch_alerts(
    *,
    overall_status: str,
    reasons: list[str],
    prev_alert_state: dict[str, Any],
    now_ts: float,
    cooldown_sec: int = DEFAULT_COOLDOWN_SEC,
    offline: bool = False,
    dry_run: bool = False,
    force_test_alert: bool = False,
    dispatcher: Callable[..., dict[str, Any]] = dispatch_alert_message,
) -> dict[str, Any]:
    """Evaluate alert cooldown & dispatch via `ops_cloud.heroku_deadman.app.dispatch_alert_message`."""
    if cooldown_sec < 0:
        raise ValueError(f"cooldown_sec must be >= 0, got {cooldown_sec!r}")

    tg_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    tg_chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    webhook_url = os.environ.get("ALERT_WEBHOOK_URL", "").strip()
    secrets = tuple(s for s in (tg_token, tg_chat_id, webhook_url) if s)

    tg_configured = bool(tg_token and tg_chat_id)
    webhook_configured = bool(webhook_url)
    configured = tg_configured or webhook_configured

    prev_map_raw = prev_alert_state.get("last_alert_ts_by_key")
    last_by_key: dict[str, float] = {}
    if isinstance(prev_map_raw, dict):
        for k, v in prev_map_raw.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                last_by_key[str(k)] = float(v)

    clean_reasons = sorted({sanitize_opsec_text(r, secrets=secrets) for r in reasons if str(r).strip()})
    if force_test_alert and not clean_reasons:
        clean_reasons = ["MANUAL_WATCHDOG_TEST_ALERT"]

    fingerprint = hashlib.sha256("|".join(clean_reasons).encode("utf-8")).hexdigest()[:16] if clean_reasons else "NONE"
    now_iso = _utc_now_iso(now_ts)

    state_out: dict[str, Any] = {
        "schema": SCHEMA_ALERT_STATE,
        "updated_utc": now_iso,
        "order_send_count": ORDER_SEND_COUNT,
        "configured": configured,
        "telegram_configured": tg_configured,
        "webhook_configured": webhook_configured,
        "cooldown_sec": cooldown_sec,
        "overall_status": overall_status,
        "alert_fingerprint": fingerprint,
        "reasons": clean_reasons,
        "action": "NO_ALERT_NEEDED",
        "sent": [],
        "errors": [],
        "cooldown_remaining_sec": 0,
        "last_sent_utc": prev_alert_state.get("last_sent_utc"),
        "last_alert_ts_by_key": last_by_key,
    }

    if not clean_reasons:
        return state_out

    if dry_run:
        state_out["action"] = "SUPPRESSED_DRY_RUN"
        return state_out
    if offline:
        state_out["action"] = "SUPPRESSED_OFFLINE"
        return state_out
    if not configured:
        state_out["action"] = "DEGRADED_UNCONFIGURED"
        return state_out

    prev_ts = last_by_key.get(fingerprint)
    if prev_ts is not None and (now_ts - prev_ts) < float(cooldown_sec):
        rem = int(round(float(cooldown_sec) - (now_ts - prev_ts)))
        state_out["action"] = "SUPPRESSED_COOLDOWN"
        state_out["cooldown_remaining_sec"] = max(1, rem)
        return state_out

    plain_lines = [
        f"[Naqex Watchdog 15m] {overall_status} ({now_iso})",
        *[f"- {r}" for r in clean_reasons[:8]],
        "OrderSend=0 (read-only alert)",
    ]
    plain_text = "\n".join(plain_lines)
    html_lines = [
        f"<b>[Naqex Watchdog 15m] {html.escape(overall_status)}</b> ({html.escape(now_iso)})",
        *[f"• {html.escape(r)}" for r in clean_reasons[:8]],
        "<i>OrderSend=0 (read-only alert)</i>",
    ]
    html_text = "\n".join(html_lines)

    res = dispatcher(
        plain_text,
        html_text=html_text,
        telegram_bot_token=tg_token,
        telegram_chat_id=tg_chat_id,
        webhook_url=webhook_url,
        timeout_sec=8.0,
    )
    sent = [str(x) for x in (res.get("sent") or [])]
    errs = [sanitize_opsec_text(e, secrets=secrets) for e in (res.get("errors") or [])]
    state_out["sent"] = sent
    state_out["errors"] = errs
    if sent:
        last_by_key[fingerprint] = float(now_ts)
        # Keep bounded cooldown map
        if len(last_by_key) > 64:
            for old_k, _ in sorted(last_by_key.items(), key=lambda kv: kv[1])[:-64]:
                last_by_key.pop(old_k, None)
        state_out["action"] = "SENT"
        state_out["last_sent_utc"] = now_iso
    else:
        state_out["action"] = "DISPATCH_FAILED"
    return sanitize_payload(state_out, secrets=secrets)


def run_watchdog(
    *,
    root: Path = ROOT,
    offline: bool = False,
    dry_run: bool = False,
    skip_ssh: bool = False,
    cooldown_sec: int = DEFAULT_COOLDOWN_SEC,
    ntp_max_ms: float = DEFAULT_NTP_MAX_MS,
    stale_lock_sec: int = DEFAULT_STALE_LOCK_SEC,
    disk_drive: str | None = None,
    force_test_alert: bool = False,
    now_ts: float | None = None,
    dispatcher: Callable[..., dict[str, Any]] = dispatch_alert_message,
) -> dict[str, Any]:
    """Run all 15-minute watchdog checks, evaluate alerts, and persist 3 sanitized state files."""
    t0 = time.perf_counter()
    ts_now = float(now_ts if now_ts is not None else time.time())
    now_iso = _utc_now_iso(ts_now)

    ntp_res = check_local_ntp(offline=offline, max_offset_ms=ntp_max_ms)
    disk_res = check_disk_space(root, drive=disk_drive)
    x13_res = check_x13_health(offline=offline, skip_ssh=skip_ssh)
    heroku_res = check_heroku_deadman(root, offline=offline)
    locks_res = check_stale_locks(root, stale_after_sec=stale_lock_sec, now_ts=ts_now)

    checks = {
        "dev_pc_ntp": ntp_res,
        "disk_space": disk_res,
        "x13_worker": x13_res,
        "heroku_deadman": heroku_res,
        "stale_locks": locks_res,
    }

    reasons: list[str] = []
    has_critical = False
    has_warn = False
    for chk in checks.values():
        st = str(chk.get("status") or "").upper()
        if st == "CRITICAL":
            has_critical = True
        elif st == "WARN":
            has_warn = True
        if chk.get("reason") and (st in {"CRITICAL", "WARN"} or not bool(chk.get("ok", True))):
            reasons.append(str(chk["reason"]))

    if has_critical:
        overall_status = "CRITICAL"
    elif has_warn:
        overall_status = "WARN"
    elif offline:
        overall_status = "OFFLINE_OK"
    else:
        overall_status = "HEALTHY"

    watchdog_path = root / ".runtime/automation/watchdog_latest.json"
    node1_path = root / ".runtime/ops-cloud/node1_watchdog_state.json"
    alert_path = root / ".runtime/ops-cloud/telegram_alert_state.json"

    prev_alert_state = _safe_read_json(alert_path)
    alert_state = evaluate_and_dispatch_alerts(
        overall_status=overall_status,
        reasons=reasons,
        prev_alert_state=prev_alert_state,
        now_ts=ts_now,
        cooldown_sec=cooldown_sec,
        offline=offline,
        dry_run=dry_run,
        force_test_alert=force_test_alert,
        dispatcher=dispatcher,
    )

    node1_state = sanitize_payload(
        {
            "schema": SCHEMA_NODE1_STATE,
            "checked_utc": now_iso,
            "order_send_count": ORDER_SEND_COUNT,
            "offline": offline,
            "configured": heroku_res["configured"],
            "source": heroku_res["source"],
            "status": heroku_res["status"],
            "health_ok": heroku_res["health_ok"],
            "status_ok": heroku_res["status_ok"],
            "node1": heroku_res["node1"],
            "reason": heroku_res["reason"],
            "error": heroku_res["error"],
        }
    )

    watchdog_state = sanitize_payload(
        {
            "schema": SCHEMA_WATCHDOG,
            "checked_utc": now_iso,
            "order_send_count": ORDER_SEND_COUNT,
            "offline": offline,
            "dry_run": dry_run,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 1),
            "overall_status": overall_status,
            "reasons": reasons,
            "checks": checks,
            "alert_summary": {
                "configured": alert_state["configured"],
                "action": alert_state["action"],
                "sent": alert_state["sent"],
                "errors": alert_state["errors"],
                "cooldown_sec": alert_state["cooldown_sec"],
            },
            "state_files": {
                "watchdog_latest": ".runtime/automation/watchdog_latest.json",
                "node1_watchdog_state": ".runtime/ops-cloud/node1_watchdog_state.json",
                "telegram_alert_state": ".runtime/ops-cloud/telegram_alert_state.json",
                "persisted": not dry_run,
            },
        }
    )

    if not dry_run:
        _atomic_write_json(watchdog_path, watchdog_state)
        _atomic_write_json(node1_path, node1_state)
        _atomic_write_json(alert_path, alert_state)

    return {
        "watchdog": watchdog_state,
        "node1_watchdog_state": node1_state,
        "telegram_alert_state": alert_state,
    }


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Naqex Zero-Token 15m Watchdog + Active Push Alerts (OrderSend = 0).")
    ap.add_argument("--root", type=Path, default=ROOT, help="Workspace root override")
    ap.add_argument("--offline", action="store_true", help="Skip NTP/SSH/Heroku/Telegram network calls")
    ap.add_argument("--dry-run", action="store_true", help="Do not persist state files or send live alerts")
    ap.add_argument("--skip-ssh", action="store_true", help="Skip optional <X13_WORKER> SSH probe")
    ap.add_argument("--json", action="store_true", dest="as_json", help="Emit JSON output (default)")
    ap.add_argument(
        "--cooldown-sec",
        type=int,
        default=DEFAULT_COOLDOWN_SEC,
        help="Alert cooldown seconds (default 900)",
    )
    ap.add_argument("--ntp-max-ms", type=float, default=DEFAULT_NTP_MAX_MS, help="Max allowed NTP drift in ms")
    ap.add_argument("--stale-lock-sec", type=int, default=DEFAULT_STALE_LOCK_SEC, help="Stale lock age threshold")
    ap.add_argument("--disk-drive", default=None, help="Explicit drive/path to check disk space (default D:)")
    ap.add_argument("--below-normal", action="store_true", help="Lower process priority to BELOW_NORMAL on Windows")
    ap.add_argument(
        "--test-alert",
        action="store_true",
        help="Trigger a manual test alert (blocked by --dry-run/--offline)",
    )
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.below_normal:
        set_below_normal_priority()
    result = run_watchdog(
        root=args.root,
        offline=bool(args.offline),
        dry_run=bool(args.dry_run),
        skip_ssh=bool(args.skip_ssh),
        cooldown_sec=int(args.cooldown_sec),
        ntp_max_ms=float(args.ntp_max_ms),
        stale_lock_sec=int(args.stale_lock_sec),
        disk_drive=args.disk_drive,
        force_test_alert=bool(args.test_alert),
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

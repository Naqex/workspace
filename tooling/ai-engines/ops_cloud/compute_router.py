"""3-Node Compute Orchestrator (`<DEV_PC>` Control Plane + `<X13_WORKER>` Dev Worker; `naqex-node1` isolated).

Implements the locked `/grill-me Q1` Star-Topology policy (`OrderSend = 0`, `Holdout 2025+` air-gapped on `<DEV_PC>`):
  - Local `<DEV_PC>` OS sensors (`GetLastInputInfo` + `GetTickCount64`, `nvidia-smi`,
    `SHQueryUserNotificationState`, `GetSystemTimes` + `GlobalMemoryStatusEx`, `w32tm`).
  - `MODE_A_OWNER_ACTIVE` (`2` cores gaming/GPU>25% or `3` cores active, `BELOW_NORMAL`, `0%` GPU)
    vs `MODE_B_IDLE_OVERNIGHT` (`5/6` cores `NORMAL` + `60/40` `10` micro-shards when shardable).
  - Single-handshake `<2s` SSH probe to `<X13_WORKER>` (`naqex-x13` LAN -> `naqex-x13-ts` Tailscale)
    requiring AC power (`ACLineStatus == 1` & `BatteryStatus != 1`), NTP `< 1000ms`, `forbidden_files == 0`.
  - Immutable Dev-only bundle dispatch + `results/<job_id>/` pull with strict `manifest.sha256.json`
    verification + silent automatic fallback to `<DEV_PC>` logging `fallback_reason`.
  - ZERO hardcoded LAN/TS IPs or local usernames (SSH aliases only); ZERO `naqex-node1` compute paths.
"""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import math
import os
import random
import re
import subprocess
import sys
import tarfile
import tempfile
import time
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Any

ORDER_SEND_CAPABLE: bool = False
ORDER_SEND_COUNT: int = 0

ROOT = Path(__file__).resolve().parents[3]
AI_ENGINES_DIR = ROOT / "tooling/ai-engines"
X13_HOSTS: tuple[str, ...] = ("naqex-x13", "naqex-x13-ts")
X13_BASE_DIR = r"C:\NaqexResearch"
X13_REMOTE_PYTHON = r"C:\NaqexResearch\.venv\Scripts\python.exe"
X13_REMOTE_PROBE = r"C:\NaqexResearch\x13_probe.py"
_X13_AC_UNPLUGGED_RC: int = 77
_X13_LOCK_BUSY_RC: int = 78

_FORBIDDEN_SHELL_META: frozenset[str] = frozenset('&|;><^%$()`"\'!\r\n\t')
_SAFE_HOST_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_SAFE_JOB_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_SAFE_EXTRA_ARG_RE = re.compile(r"^[A-Za-z0-9._:=\\/@,-]+$")
_SAFE_FLAG_RE = re.compile(r"^--[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
_NTP_OFFSET_RE = re.compile(r"([+-]\d+(?:\.\d+)?)s\b")
_DEV_CALENDAR_ALLOWLIST: tuple[str, ...] = (
    "red_news_official_2018_2024_6ccy.json",
    "red_news_official_2018_2024.json",
)
_FORBIDDEN_DEV_TOKENS: tuple[str, ...] = (
    "holdout",
    "2025",
    "2026",
    "native_ftmo_holdout_lock",
    "accounts.dat",
    ".ssh",
    "id_ed25519",
    "private_vault",
)

# Win32 constants: QUNS_BUSY(2), QUNS_RUNNING_D3D_FULL_SCREEN(3), QUNS_PRESENTATION_MODE(4)
_QUNS_BUSY_STATES: frozenset[int] = frozenset({2, 3, 4})
_BELOW_NORMAL_PRIORITY_CLASS = 0x00004000
_NORMAL_PRIORITY_CLASS = 0x00000020


class _LastInputInfo(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint32), ("dwTime", ctypes.c_uint32)]


class _FileTime(ctypes.Structure):
    _fields_ = [("dwLowDateTime", ctypes.c_uint32), ("dwHighDateTime", ctypes.c_uint32)]


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


def _sha256_file(path: Path) -> str:
    with path.open("rb") as fh:
        return hashlib.file_digest(fh, "sha256").hexdigest()


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


def _validate_host(host: str) -> str:
    h = str(host or "").strip()
    if not h or not _SAFE_HOST_RE.fullmatch(h) or "node1" in h.lower():
        raise ValueError(f"Invalid or forbidden compute SSH host alias: {host!r}")
    return h


def _validate_job_id(job_id: str) -> str:
    jid = str(job_id or "").strip()
    if not jid or not _SAFE_JOB_ID_RE.fullmatch(jid):
        raise ValueError(f"Invalid job_id (alphanumeric/._- only): {job_id!r}")
    low = jid.lower()
    if any(tok in low for tok in _FORBIDDEN_DEV_TOKENS):
        raise ValueError(f"Job ID contains forbidden air-gap token: {job_id!r}")
    return jid


def _validate_extra_args(extra_args: list[str] | None) -> list[str]:
    if not extra_args:
        return []
    out: list[str] = []
    for raw in extra_args:
        arg = str(raw)
        if not arg or any(ch in _FORBIDDEN_SHELL_META for ch in arg) or not _SAFE_EXTRA_ARG_RE.fullmatch(arg):
            raise ValueError(f"Unsafe argument rejected: {arg!r}")
        out.append(arg)
    return out


def assert_dev_only_path(path_like: str | Path) -> None:
    """Fail-closed guard ensuring no Holdout / 2025+ / secrets path can ever be bundled for <X13_WORKER>."""
    norm = str(path_like).replace("\\", "/").lower()
    for tok in _FORBIDDEN_DEV_TOKENS:
        if tok in norm:
            raise ValueError(f"HOLDOUT_OR_SECRET_AIRGAP_VIOLATION: forbidden token {tok!r} in {path_like!r}")


# ==============================================================================
# 1. LOCAL <DEV_PC> READ-ONLY OS SENSORS
# ==============================================================================

def _read_idle_sec() -> float:
    if os.name != "nt":
        return 0.0
    lii = _LastInputInfo()
    lii.cbSize = ctypes.sizeof(_LastInputInfo)
    if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
        return 0.0
    tick64 = ctypes.windll.kernel32.GetTickCount64()
    # Compare 32-bit dwTime cleanly modulo 2^32 against GetTickCount64 low 32 bits
    elapsed_ms = (int(tick64) - int(lii.dwTime)) & 0xFFFFFFFF
    return round(elapsed_ms / 1000.0, 1)


def _read_gpu_util_pct() -> int:
    try:
        proc = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=1.5,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if proc.returncode == 0 and proc.stdout.strip():
            first_line = proc.stdout.strip().splitlines()[0]
            return int(float(first_line.split(",")[0].strip()))
    except Exception:
        pass
    return 0


def _read_fullscreen_busy() -> bool:
    if os.name != "nt":
        return False
    try:
        state = ctypes.c_int(0)
        hr = ctypes.windll.shell32.SHQueryUserNotificationState(ctypes.byref(state))
        if hr == 0:
            return int(state.value) in _QUNS_BUSY_STATES
    except Exception:
        pass
    return False


def _read_cpu_util_pct(sample_sec: float = 0.20) -> float:
    if os.name != "nt":
        return 0.0
    k32 = ctypes.windll.kernel32
    i1, k1, u1 = _FileTime(), _FileTime(), _FileTime()
    i2, k2, u2 = _FileTime(), _FileTime(), _FileTime()
    if not k32.GetSystemTimes(ctypes.byref(i1), ctypes.byref(k1), ctypes.byref(u1)):
        return 0.0
    time.sleep(sample_sec)
    if not k32.GetSystemTimes(ctypes.byref(i2), ctypes.byref(k2), ctypes.byref(u2)):
        return 0.0

    def _i(ft: _FileTime) -> int:
        return (int(ft.dwHighDateTime) << 32) | int(ft.dwLowDateTime)

    di = _i(i2) - _i(i1)
    tot = (_i(k2) - _i(k1)) + (_i(u2) - _i(u1))
    if tot <= 0:
        return 0.0
    return round(min(100.0, max(0.0, float(tot - di) / float(tot)) * 100.0), 1)


def _read_free_ram_gb() -> float:
    if os.name != "nt":
        return 16.0
    ms = _MemoryStatusEx()
    ms.dwLength = ctypes.sizeof(_MemoryStatusEx)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(ms)):
        return 0.0
    return round(float(ms.ullAvailPhys) / float(1024 ** 3), 2)


def _read_ntp_offset_ms() -> float | None:
    if os.name != "nt":
        return None
    for srv in ("time.cloudflare.com", "time.google.com"):
        try:
            proc = subprocess.run(
                ["w32tm", "/stripchart", f"/computer:{srv}", "/samples:1", "/dataonly"],
                capture_output=True,
                text=True,
                timeout=1.6,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            m = _NTP_OFFSET_RE.search(proc.stdout or "")
            if m:
                return round(float(m.group(1)) * 1000.0, 1)
        except Exception:
            continue
    return None


def _finite_float(val: Any) -> float | None:
    """Return finite float, or None on None/bool/NaN/Inf/unparseable."""
    if val is None or isinstance(val, bool):
        return None
    try:
        f = float(val)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _strict_int(val: Any) -> int | None:
    """Return strict non-bool int, or None."""
    if isinstance(val, bool) or not isinstance(val, int):
        return None
    return val


def _strict_ntp_passed(dev_pc: dict[str, Any], x13: dict[str, Any]) -> bool:
    """Require finite <1000ms NTP offset on BOTH <DEV_PC> and <X13_WORKER> (fail-closed on None/NaN)."""
    dev_ntp = _finite_float(dev_pc.get("ntp_offset_ms"))
    x13_ntp = _finite_float(x13.get("ntp_offset_ms"))
    return (
        dev_ntp is not None
        and abs(dev_ntp) < 1000.0
        and x13_ntp is not None
        and abs(x13_ntp) < 1000.0
    )


def classify_dev_pc_mode(dev_pc: dict[str, Any]) -> str:
    """Classify `<DEV_PC>` into `MODE_A_OWNER_ACTIVE` or `MODE_B_IDLE_OVERNIGHT` per locked Q1 policy."""
    idle_sec = _finite_float(dev_pc.get("idle_sec"))
    overnight = bool(dev_pc.get("in_overnight_window_ict", False))
    gpu_pct = _finite_float(dev_pc.get("gpu_util_pct"))
    fullscreen = bool(dev_pc.get("fullscreen_busy", False))
    cpu_pct = _finite_float(dev_pc.get("cpu_util_pct"))
    free_ram_gb = _finite_float(dev_pc.get("free_ram_gb"))

    if idle_sec is None or gpu_pct is None or cpu_pct is None or free_ram_gb is None:
        return "MODE_A_OWNER_ACTIVE"

    idle_ready = (idle_sec >= 900.0) or (overnight and idle_sec >= 300.0)
    busy_now = (gpu_pct > 25.0) or fullscreen or (cpu_pct >= 30.0) or (free_ram_gb < 6.0)
    if idle_ready and not busy_now:
        return "MODE_B_IDLE_OVERNIGHT"
    return "MODE_A_OWNER_ACTIVE"


def probe_dev_pc(*, now_utc: datetime | None = None) -> dict[str, Any]:
    """Read local `<DEV_PC>` OS sensors with sequential CPU sampling before subprocess probes (100% read-only)."""
    now = now_utc or datetime.now(UTC)
    now_ict = now.astimezone(timezone(timedelta(hours=7)))
    in_overnight = 0 <= now_ict.hour < 7

    # Sample CPU utilization sequentially BEFORE spawning nvidia-smi / w32tm
    # subprocesses so probe child processes do not self-inflate idle CPU %.
    cpu_pct = _read_cpu_util_pct(0.20)
    idle_sec = _read_idle_sec()
    fullscreen = _read_fullscreen_busy()
    free_ram = _read_free_ram_gb()

    with ThreadPoolExecutor(max_workers=2) as pool:
        f_gpu = pool.submit(_read_gpu_util_pct)
        f_ntp = pool.submit(_read_ntp_offset_ms)
        gpu_pct = f_gpu.result()
        ntp_ms = f_ntp.result()

    info: dict[str, Any] = {
        "idle_sec": idle_sec,
        "in_overnight_window_ict": in_overnight,
        "gpu_util_pct": gpu_pct,
        "fullscreen_busy": fullscreen,
        "cpu_util_pct": cpu_pct,
        "free_ram_gb": free_ram,
        "ntp_offset_ms": ntp_ms,
        "ntp_ok": (ntp_ms is not None and abs(ntp_ms) < 1000.0),
    }
    info["mode"] = classify_dev_pc_mode(info)
    return info


# ==============================================================================
# 2. REMOTE <X13_WORKER> FAIL-CLOSED PROBE & ELIGIBILITY GATES
# ==============================================================================

def evaluate_x13_eligibility(
    x13: dict[str, Any],
    *,
    min_ram_gb: float = 4.0,
    strict_ntp: bool = False,
    allow_ntp_drift: bool = False,
) -> tuple[bool, list[str]]:
    """Apply all 4 mandatory fail-closed gates to an `<X13_WORKER>` probe payload."""
    reasons: list[str] = []
    if x13.get("reachable") is not True:
        existing = list(x13.get("ineligible_reasons") or [])
        return False, existing or ["x13_unreachable"]

    min_ram = _finite_float(min_ram_gb)
    if min_ram is None or min_ram < 0.0:
        reasons.append(f"invalid_min_ram_gb({min_ram_gb!r})")
        req_ram = 4.0
    else:
        req_ram = max(4.0, min_ram)

    ac_line_raw = x13.get("ac_line_status")
    ac_line = _strict_int(ac_line_raw)
    bat_code = x13.get("battery_status_code")
    if bat_code == 1 or isinstance(bat_code, bool):
        reasons.append("x13_battery_discharging(BatteryStatus=1)")
    if x13.get("ac_online") is not True or ac_line != 1:
        reasons.append(f"x13_ac_offline(ac_online={x13.get('ac_online')},ac_line_status={ac_line_raw})")

    cpu_pct = _finite_float(x13.get("cpu_util_pct"))
    if cpu_pct is None or cpu_pct < 0.0:
        reasons.append(f"x13_cpu_invalid({x13.get('cpu_util_pct')!r})")
    elif cpu_pct >= 40.0:
        reasons.append(f"x13_cpu_busy({cpu_pct:.1f}%>=40%)")

    free_ram = _finite_float(x13.get("free_ram_gb"))
    if free_ram is None or free_ram < 0.0:
        reasons.append(f"x13_ram_invalid({x13.get('free_ram_gb')!r})")
    elif free_ram < req_ram:
        reasons.append(f"x13_low_ram({free_ram:.2f}GB<{req_ram:.2f}GB)")

    disk_free = _finite_float(x13.get("disk_free_gb"))
    if disk_free is None or disk_free < 0.0:
        reasons.append(f"x13_disk_invalid({x13.get('disk_free_gb')!r})")
    elif disk_free < 15.0:
        reasons.append(f"x13_low_disk({disk_free:.2f}GB<15.0GB)")

    if x13.get("active_job_lock") is not None:
        reasons.append("x13_busy_active_job_lock")

    if x13.get("venv_ok") is not True:
        reasons.append(f"x13_missing_venv({x13.get('venv_ok')!r})")

    forbidden_raw = x13.get("forbidden_files")
    forbidden = _strict_int(forbidden_raw)
    if forbidden is None or forbidden < 0:
        reasons.append(f"x13_forbidden_files_invalid({forbidden_raw!r})")
    elif forbidden > 0:
        reasons.append(f"x13_forbidden_files({forbidden})")

    ntp_raw = x13.get("ntp_offset_ms")
    if not allow_ntp_drift:
        if ntp_raw is None:
            if strict_ntp:
                reasons.append("x13_ntp_unavailable")
        else:
            ntp_ms = _finite_float(ntp_raw)
            if ntp_ms is None:
                reasons.append(f"x13_ntp_invalid({ntp_raw!r})")
            elif abs(ntp_ms) >= 1000.0:
                reasons.append(f"x13_ntp_drift_ge_1000ms({ntp_ms:+.1f}ms)")

    return len(reasons) == 0, reasons


def probe_x13_worker(
    *,
    hosts: tuple[str, ...] = X13_HOSTS,
    lan_only: bool = False,
    connect_timeout: int = 2,
    timeout: float = 4.0,
    strict_ntp: bool = False,
    allow_ntp_drift: bool = False,
) -> dict[str, Any]:
    """Probe `<X13_WORKER>` via single SSH handshake (`naqex-x13` -> `naqex-x13-ts` fallback on rc=255)."""
    candidates = (_validate_host(hosts[0]),) if lan_only else tuple(_validate_host(h) for h in hosts)
    remote_cmd = f'"{X13_REMOTE_PYTHON}" "{X13_REMOTE_PROBE}"'
    last_reason = "x13_unreachable"

    for idx, alias in enumerate(candidates):
        has_next = idx + 1 < len(candidates)
        t0 = time.perf_counter()
        try:
            proc = subprocess.run(
                ["ssh", "-o", f"ConnectTimeout={int(connect_timeout)}", "-o", "BatchMode=yes", alias, remote_cmd],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
            )
        except (subprocess.SubprocessError, OSError) as exc:
            last_reason = f"x13_ssh_timeout_or_error({alias}:{type(exc).__name__})"
            if has_next:
                continue
            break

        probe_ms = round((time.perf_counter() - t0) * 1000.0, 1)
        if proc.returncode == 255:
            last_reason = f"x13_ssh_unreachable({alias})"
            if has_next:
                continue
            break

        if proc.returncode != 0:
            last_reason = f"x13_probe_failed(rc={proc.returncode})"
            break

        try:
            raw = json.loads(proc.stdout.strip())
            if not isinstance(raw, dict):
                raise ValueError("probe JSON root is not an object")
        except Exception:
            last_reason = "x13_probe_invalid_json"
            break

        payload = {
            "ssh_alias": alias,
            "transport": "TAILSCALE" if alias.endswith("-ts") else "LAN",
            "probe_ms": probe_ms,
            "reachable": True,
            "ac_online": raw.get("ac_online") is True,
            "ac_line_status": _strict_int(raw.get("ac_line_status")),
            "battery_status_code": _strict_int(raw.get("battery_status_code")),
            "battery_pct": _strict_int(raw.get("battery_pct")),
            "cpu_util_pct": _finite_float(raw.get("cpu_util_pct")),
            "free_ram_gb": _finite_float(raw.get("free_ram_gb")),
            "disk_free_gb": _finite_float(raw.get("disk_free_gb")),
            "venv_ok": raw.get("venv_ok") is True,
            "active_job_lock": raw.get("active_job_lock"),
            "ntp_offset_ms": _finite_float(raw.get("ntp_offset_ms")),
            "forbidden_files": _strict_int(raw.get("forbidden_files")),
        }
        eligible, reasons = evaluate_x13_eligibility(
            payload, strict_ntp=strict_ntp, allow_ntp_drift=allow_ntp_drift
        )
        payload["eligible"] = eligible
        payload["ineligible_reasons"] = reasons
        return payload

    return {
        "ssh_alias": candidates[0],
        "transport": "NONE",
        "probe_ms": None,
        "reachable": False,
        "ac_online": False,
        "ac_line_status": None,
        "battery_status_code": None,
        "battery_pct": None,
        "cpu_util_pct": None,
        "free_ram_gb": None,
        "disk_free_gb": None,
        "venv_ok": False,
        "active_job_lock": None,
        "ntp_offset_ms": None,
        "forbidden_files": 0,
        "eligible": False,
        "ineligible_reasons": [last_reason],
    }


def _is_only_active_lock_busy(reasons: list[str]) -> bool:
    """Return True iff X13 failed eligibility solely because another job holds `active_job.lock`."""
    return len(reasons) == 1 and reasons[0] == "x13_busy_active_job_lock"


def wait_for_x13_lease(
    *,
    probe_fn: Callable[[], dict[str, Any]] | None = None,
    lan_only: bool = False,
    strict_ntp: bool = False,
    allow_ntp_drift: bool = False,
    min_ram_gb: float = 4.0,
    max_wait_sec: float = 120.0,
    base_backoff_sec: float = 2.0,
    max_backoff_sec: float = 15.0,
    jitter_frac: float = 0.25,
    max_attempts: int | None = None,
    sleep_fn: Callable[[float], None] = time.sleep,
    rng: random.Random | None = None,
) -> dict[str, Any]:
    """Safe Lease Queue wrapper around `<X13_WORKER>` `active_job.lock` with jittered exponential backoff.

    Retries ONLY when X13 is healthy on every gate except `x13_busy_active_job_lock`.
    Fails fast immediately on unreachable, battery discharging, NTP drift, low RAM/disk,
    or forbidden-file violations so silent `<DEV_PC>` fallback executes without delay.
    """
    max_w = _finite_float(max_wait_sec)
    base_b = _finite_float(base_backoff_sec)
    max_b = _finite_float(max_backoff_sec)
    j_frac = _finite_float(jitter_frac)
    if max_w is None or max_w < 0.0:
        raise ValueError(f"Invalid max_wait_sec (must be finite >= 0): {max_wait_sec!r}")
    if base_b is None or base_b < 0.0:
        raise ValueError(f"Invalid base_backoff_sec (must be finite >= 0): {base_backoff_sec!r}")
    if max_b is None or max_b < 0.0:
        raise ValueError(f"Invalid max_backoff_sec (must be finite >= 0): {max_backoff_sec!r}")
    if j_frac is None or not (0.0 <= j_frac <= 1.0):
        raise ValueError(f"Invalid jitter_frac (must be in [0, 1]): {jitter_frac!r}")
    if max_attempts is not None and (isinstance(max_attempts, bool) or max_attempts < 1):
        raise ValueError(f"Invalid max_attempts (must be >= 1): {max_attempts!r}")

    prober = probe_fn or (
        lambda: probe_x13_worker(
            lan_only=lan_only,
            strict_ntp=strict_ntp,
            allow_ntp_drift=allow_ntp_drift,
        )
    )
    rand = rng or random.Random()
    waited = 0.0
    attempt = 0
    sleeps: list[float] = []

    while True:
        attempt += 1
        x13 = prober()
        eligible, reasons = evaluate_x13_eligibility(
            x13,
            min_ram_gb=min_ram_gb,
            strict_ntp=strict_ntp,
            allow_ntp_drift=allow_ntp_drift,
        )
        if eligible:
            return {
                "acquired": True,
                "status": "LEASE_ACQUIRED",
                "attempts": attempt,
                "waited_sec": round(waited, 4),
                "sleep_history_sec": sleeps,
                "x13_worker": x13,
                "reasons": [],
            }
        if not _is_only_active_lock_busy(reasons):
            return {
                "acquired": False,
                "status": "X13_INELIGIBLE",
                "attempts": attempt,
                "waited_sec": round(waited, 4),
                "sleep_history_sec": sleeps,
                "x13_worker": x13,
                "reasons": reasons,
            }
        remaining = max_w - waited
        if (max_attempts is not None and attempt >= max_attempts) or remaining <= 0.0:
            return {
                "acquired": False,
                "status": "LEASE_TIMEOUT",
                "attempts": attempt,
                "waited_sec": round(waited, 4),
                "sleep_history_sec": sleeps,
                "x13_worker": x13,
                "reasons": reasons,
            }

        raw_delay = min(max_b, base_b * (2.0 ** (attempt - 1)))
        factor = 1.0 + rand.uniform(-j_frac, j_frac) if j_frac > 0.0 else 1.0
        delay = min(remaining, max(0.0, raw_delay * factor))
        if delay <= 0.0:
            if max_attempts is None:
                return {
                    "acquired": False,
                    "status": "LEASE_TIMEOUT",
                    "attempts": attempt,
                    "waited_sec": round(waited, 4),
                    "sleep_history_sec": sleeps,
                    "x13_worker": x13,
                    "reasons": reasons,
                }
        else:
            sleep_fn(delay)
        sleeps.append(round(delay, 4))
        waited += delay


# ==============================================================================
# 3. DETERMINISTIC ROUTING POLICY (MODE A / MODE B / 60-40 / 20-80 / FALLBACK)
# ==============================================================================

def decide_route(
    dev_pc: dict[str, Any],
    x13_worker: dict[str, Any],
    *,
    est_minutes: float = 10.0,
    ram_gb: float = 4.0,
    shardable: bool = False,
    shards: int = 10,
    touches_holdout: bool = False,
    touches_vps: bool = False,
    requires_admin: bool = False,
    needs_gpu: bool = False,
    strict_ntp: bool = False,
    allow_ntp_drift: bool = False,
    force_x13: bool = False,
    allow_mode_a_assist: bool = False,
    force_mode_b: bool = False,
    owner_approved_long_run: bool = False,
) -> dict[str, Any]:
    """Apply locked `/grill-me Q1` routing table deterministically with silent fallback on X13 failure."""
    est_m = _finite_float(est_minutes)
    if est_m is None or est_m < 0.0:
        raise ValueError(f"Invalid est_minutes (must be finite >= 0): {est_minutes!r}")
    ram_req = _finite_float(ram_gb)
    if ram_req is None or ram_req < 0.0:
        raise ValueError(f"Invalid ram_gb (must be finite >= 0): {ram_gb!r}")
    est_minutes = est_m
    ram_gb = ram_req

    reasons: list[str] = []
    if force_mode_b:
        mode = "MODE_B_IDLE_OVERNIGHT"
        reasons.append("Owner authorized --force-mode-b: overriding local Mode A sensor to MODE_B_IDLE_OVERNIGHT")
    else:
        mode = dev_pc.get("mode") or classify_dev_pc_mode(dev_pc)
    gpu_val = _finite_float(dev_pc.get("gpu_util_pct"))
    gaming_or_gpu = (gpu_val is None or gpu_val > 25.0) or bool(dev_pc.get("fullscreen_busy", False))
    mode_a_cores = 2 if gaming_or_gpu else 3
    x13_ok, x13_reasons = evaluate_x13_eligibility(
        x13_worker, min_ram_gb=ram_gb, strict_ntp=strict_ntp, allow_ntp_drift=allow_ntp_drift
    )

    # Tier 3 fail-closed approval gates
    if touches_vps:
        return _build_decision(
            target="BLOCKED_NEEDS_APPROVAL",
            tier="TIER_3_ASK_OWNER",
            ask_owner=True,
            dev_cores=0,
            dev_priority="BELOW_NORMAL",
            dev_gpu=False,
            x13_threads=0,
            split={"dev_pc": 0, "x13_worker": 0},
            reasons=["naqex-node1 mutations/compute are forbidden without explicit owner Tier-3 approval"],
        )
    if requires_admin:
        return _build_decision(
            target="BLOCKED_NEEDS_APPROVAL",
            tier="TIER_3_ASK_OWNER",
            ask_owner=True,
            dev_cores=0,
            dev_priority="BELOW_NORMAL",
            dev_gpu=False,
            x13_threads=0,
            split={"dev_pc": 0, "x13_worker": 0},
            reasons=["Windows Admin (UAC) action requires explicit owner Tier-3 approval"],
        )
    if est_minutes > 60.0 and not owner_approved_long_run:
        return _build_decision(
            target="BLOCKED_NEEDS_APPROVAL",
            tier="TIER_3_ASK_OWNER",
            ask_owner=True,
            dev_cores=0,
            dev_priority="BELOW_NORMAL",
            dev_gpu=False,
            x13_threads=0,
            split={"dev_pc": 0, "x13_worker": 0},
            reasons=[f"Estimated duration {est_minutes:.1f}m > 60m requires explicit owner Tier-3 approval"],
        )
    if est_minutes > 60.0 and owner_approved_long_run:
        reasons.append(f"Owner authorized --owner-approved-long-run: overriding 60m cap ({est_minutes:.1f}m)")
    if needs_gpu and mode == "MODE_A_OWNER_ACTIVE":
        return _build_decision(
            target="BLOCKED_NEEDS_APPROVAL",
            tier="TIER_3_ASK_OWNER",
            ask_owner=True,
            dev_cores=0,
            dev_priority="BELOW_NORMAL",
            dev_gpu=False,
            x13_threads=0,
            split={"dev_pc": 0, "x13_worker": 0},
            reasons=["Heavy GPU workload while owner active on <DEV_PC> (Mode A) requires Tier-3 approval"],
        )

    dev_cores_local = mode_a_cores if mode == "MODE_A_OWNER_ACTIVE" else 5
    dev_prio_local = "BELOW_NORMAL" if mode == "MODE_A_OWNER_ACTIVE" else "NORMAL"
    dev_gpu_local = False if mode == "MODE_A_OWNER_ACTIVE" else bool(needs_gpu)
    tier = "TIER_1_SILENT" if est_minutes < 15.0 else "TIER_2_NOTIFY_1LINE"

    # Air-gapped local-only workloads (Holdout 2025+ or GPU)
    if touches_holdout or needs_gpu:
        if touches_holdout:
            reasons.append("Holdout 2025+ air-gap enforced: strictly pinned to <DEV_PC>")
        if needs_gpu:
            reasons.append("GPU workload pinned to <DEV_PC> (Mode B idle)")
        return _build_decision(
            target="DEV_PC_ONLY",
            tier="TIER_3_ASK_OWNER" if touches_holdout else tier,
            ask_owner=bool(touches_holdout),
            dev_cores=dev_cores_local,
            dev_priority=dev_prio_local,
            dev_gpu=dev_gpu_local,
            x13_threads=0,
            split={"dev_pc": 100, "x13_worker": 0},
            reasons=reasons,
        )

    # Explicit smoke/offload preference (still respects fail-closed X13 gates + silent fallback!)
    if force_x13:
        if x13_ok:
            reasons.append("Explicit Dev-only X13 target requested and X13 passed all 4/4 gates")
            return _build_decision(
                target="X13_ONLY",
                tier=tier,
                ask_owner=False,
                dev_cores=0,
                dev_priority=dev_prio_local,
                dev_gpu=False,
                x13_threads=7,
                split={"dev_pc": 0, "x13_worker": 100},
                reasons=reasons,
            )
        fb = "; ".join(x13_reasons)
        reasons.append(f"X13 ineligible ({fb}) -> silent automatic fallback to <DEV_PC>")
        return _build_decision(
            target="DEV_PC_ONLY",
            tier=tier,
            ask_owner=False,
            dev_cores=dev_cores_local,
            dev_priority=dev_prio_local,
            dev_gpu=False,
            x13_threads=0,
            split={"dev_pc": 100, "x13_worker": 0},
            fallback_used=True,
            fallback_reason=fb,
            reasons=reasons,
        )

    # Short jobs (< 10 min): run locally to avoid bundle/transfer overhead
    if est_minutes < 10.0:
        reasons.append(f"Short Dev job ({est_minutes:.1f}m < 10m) runs locally on <DEV_PC> ({mode})")
        return _build_decision(
            target="DEV_PC_ONLY",
            tier=tier,
            ask_owner=False,
            dev_cores=dev_cores_local,
            dev_priority=dev_prio_local,
            dev_gpu=False,
            x13_threads=0,
            split={"dev_pc": 100, "x13_worker": 0},
            reasons=reasons,
        )

    # Mode A (owner active) + heavy Dev job >= 10m -> default offload 100% to X13,
    # or optional gentle 20/80 assist when `allow_mode_a_assist=True` and shardable.
    if mode == "MODE_A_OWNER_ACTIVE":
        if x13_ok:
            if allow_mode_a_assist and shardable:
                n_total = max(2, int(shards))
                n_dev = max(1, int(round(n_total * 0.20)))
                if n_dev >= n_total:
                    n_dev = n_total - 1
                n_x13 = n_total - n_dev
                assist_cores = min(2, mode_a_cores)
                reasons.append(
                    f"PC Dev in Mode A (gpu={dev_pc.get('gpu_util_pct')}%, fullscreen={dev_pc.get('fullscreen_busy')}) "
                    f"with gentle Mode-A assist (cap={assist_cores} cores BELOW_NORMAL, 0% GPU) + X13 ready -> "
                    f"20/80 split ({n_dev}/{n_x13} micro-shards)"
                )
                return _build_decision(
                    target="PARALLEL_20_80_MODE_A",
                    tier=tier,
                    ask_owner=False,
                    dev_cores=assist_cores,
                    dev_priority="BELOW_NORMAL",
                    dev_gpu=False,
                    x13_threads=7,
                    split={"dev_pc": 20, "x13_worker": 80},
                    micro_shards={"total": n_total, "dev_pc": n_dev, "x13_worker": n_x13},
                    reasons=reasons,
                )
            reasons.append(
                f"PC Dev in Mode A (gpu={dev_pc.get('gpu_util_pct')}%, fullscreen={dev_pc.get('fullscreen_busy')})"
            )
            reasons.append(f"Dev job {est_minutes:.1f}m >= 10m offloaded 100% to <X13_WORKER> (4/4 gates passed)")
            return _build_decision(
                target="X13_ONLY",
                tier=tier,
                ask_owner=False,
                dev_cores=0,
                dev_priority="BELOW_NORMAL",
                dev_gpu=False,
                x13_threads=7,
                split={"dev_pc": 0, "x13_worker": 100},
                reasons=reasons,
            )
        fb = "; ".join(x13_reasons)
        reasons.append(
            f"PC Dev in Mode A (cap={mode_a_cores} cores, BELOW_NORMAL, 0% GPU); "
            f"X13 ineligible ({fb}) -> silent fallback"
        )
        return _build_decision(
            target="DEV_PC_ONLY",
            tier=tier,
            ask_owner=False,
            dev_cores=mode_a_cores,
            dev_priority="BELOW_NORMAL",
            dev_gpu=False,
            x13_threads=0,
            split={"dev_pc": 100, "x13_worker": 0},
            fallback_used=True,
            fallback_reason=fb,
            reasons=reasons,
        )

    # Mode B (idle/overnight): 5/6 cores + 60/40 10 micro-shards if >= 15m & shardable & X13 ready
    if est_minutes >= 15.0 and shardable:
        if x13_ok:
            n_total = max(2, int(shards))
            n_dev = int(round(n_total * 0.60))
            n_x13 = n_total - n_dev
            reasons.append(
                f"PC Dev in Mode B (idle/overnight, 5/6 cores NORMAL) + X13 ready -> "
                f"60/40 split ({n_dev}/{n_x13} micro-shards)"
            )
            return _build_decision(
                target="PARALLEL_60_40",
                tier=tier,
                ask_owner=False,
                dev_cores=5,
                dev_priority="NORMAL",
                dev_gpu=False,
                x13_threads=7,
                split={"dev_pc": 60, "x13_worker": 40},
                micro_shards={"total": n_total, "dev_pc": n_dev, "x13_worker": n_x13},
                reasons=reasons,
            )
        fb = "; ".join(x13_reasons)
        reasons.append(f"PC Dev in Mode B (5/6 cores NORMAL); X13 ineligible ({fb}) -> silent fallback to <DEV_PC>")
        return _build_decision(
            target="DEV_PC_ONLY",
            tier=tier,
            ask_owner=False,
            dev_cores=5,
            dev_priority="NORMAL",
            dev_gpu=False,
            x13_threads=0,
            split={"dev_pc": 100, "x13_worker": 0},
            fallback_used=True,
            fallback_reason=fb,
            reasons=reasons,
        )

    reasons.append("PC Dev in Mode B (5/6 cores NORMAL) handling non-shardable or <15m Dev job locally")
    return _build_decision(
        target="DEV_PC_ONLY",
        tier=tier,
        ask_owner=False,
        dev_cores=5,
        dev_priority="NORMAL",
        dev_gpu=False,
        x13_threads=0,
        split={"dev_pc": 100, "x13_worker": 0},
        reasons=reasons,
    )


def _build_decision(
    *,
    target: str,
    tier: str,
    ask_owner: bool,
    dev_cores: int,
    dev_priority: str,
    dev_gpu: bool,
    x13_threads: int,
    split: dict[str, int],
    reasons: list[str],
    fallback_used: bool = False,
    fallback_reason: str | None = None,
    micro_shards: dict[str, int] | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "target": target,
        "autonomy_tier": tier,
        "ask_owner_required": ask_owner,
        "fallback_used": fallback_used,
        "fallback_reason": fallback_reason,
        "dev_pc_cores": dev_cores,
        "dev_pc_priority": dev_priority,
        "dev_pc_gpu_allowed": dev_gpu,
        "x13_threads": x13_threads,
        "shard_split_pct": split,
        "reasons": reasons,
    }
    if micro_shards is not None:
        out["micro_shards"] = micro_shards
    return out


# ==============================================================================
# 4. IMMUTABLE BUNDLES, MANIFEST SHA-256 VERIFICATION & JOB DISPATCH
# ==============================================================================

def _current_git_sha() -> str:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--short=12", "HEAD"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if proc.returncode == 0:
            return proc.stdout.strip()
    except Exception:
        pass
    return "unknown"


def build_job_bundle(
    job_id: str,
    entry_script: Path,
    out_dir: Path,
    *,
    extra_files: tuple[Path, ...] = (),
    shard_batch_arc: str | None = None,
    shard_arg_flag: str | None = None,
) -> dict[str, Any]:
    """Package an immutable Dev-only tar.gz bundle + SHA-256 manifest (rejects Holdout/secrets fail-closed)."""
    jid = _validate_job_id(job_id)
    entry = entry_script.resolve()
    if not entry.is_file():
        raise FileNotFoundError(f"Entry script not found: {entry}")
    if shard_arg_flag is not None and not _SAFE_FLAG_RE.fullmatch(shard_arg_flag):
        raise ValueError(f"Unsafe shard_arg_flag rejected: {shard_arg_flag!r}")

    files_to_pack: list[tuple[str, Path]] = []
    seen_arc: set[str] = set()
    for p in (entry, *(ef.resolve() for ef in extra_files)):
        assert_dev_only_path(p)
        try:
            arc = p.relative_to(ROOT).as_posix()
        except ValueError:
            arc = p.name
        assert_dev_only_path(arc)
        if arc not in seen_arc:
            seen_arc.add(arc)
            files_to_pack.append((arc, p))

    if shard_batch_arc is not None:
        assert_dev_only_path(shard_batch_arc)
        if shard_batch_arc not in seen_arc:
            raise ValueError(f"shard_batch_arc not present in bundled files: {shard_batch_arc!r}")

    out_dir.mkdir(parents=True, exist_ok=True)
    tar_path = out_dir / "bundle.tar.gz"
    file_hashes: dict[str, str] = {}
    with tarfile.open(tar_path, "w:gz") as tf:
        for arc, p in sorted(files_to_pack):
            assert_dev_only_path(arc)
            tf.add(str(p), arcname=arc)
            file_hashes[arc] = _sha256_file(p)

    bundle_sha = _sha256_file(tar_path)
    manifest: dict[str, Any] = {
        "schema": "naqex-job-bundle-v1",
        "job_id": jid,
        "git_sha": _current_git_sha(),
        "created_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "entry_arc": files_to_pack[0][0],
        "bundle_tar_sha256": bundle_sha,
        "files": file_hashes,
    }
    if shard_batch_arc is not None:
        manifest["shard_batch_arc"] = shard_batch_arc
    if shard_arg_flag is not None:
        manifest["shard_arg_flag"] = shard_arg_flag
    manifest_path = out_dir / "bundle_manifest.sha256.json"
    _atomic_write_json(manifest_path, manifest)
    return {
        "tar_path": tar_path,
        "manifest_path": manifest_path,
        "manifest": manifest,
    }


def write_result_manifest(result_dir: Path, *, job_id: str, host_label: str) -> Path:
    """Compute SHA-256 of every file in `result_dir` and atomically write `manifest.sha256.json` LAST."""
    entries: dict[str, dict[str, Any]] = {}
    for p in sorted(result_dir.rglob("*")):
        if not p.is_file() or p.name == "manifest.sha256.json" or p.name.endswith(".tmp"):
            continue
        rel = p.relative_to(result_dir).as_posix()
        entries[rel] = {"sha256": _sha256_file(p), "bytes": p.stat().st_size}
    manifest = {
        "schema": "naqex-job-result-manifest-v1",
        "job_id": job_id,
        "host": host_label,
        "completed_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "order_send_count": ORDER_SEND_COUNT,
        "files": entries,
    }
    mpath = result_dir / "manifest.sha256.json"
    _atomic_write_json(mpath, manifest)
    return mpath


def verify_result_manifest(result_dir: Path) -> dict[str, Any]:
    """Fail-closed SHA-256 verifier for pulled or local job results (`manifest.sha256.json`)."""
    mpath = result_dir / "manifest.sha256.json"
    if not mpath.is_file():
        return {
            "ok": False,
            "status": "FAILED_INTEGRITY",
            "errors": ["missing manifest.sha256.json"],
            "files_verified": 0,
        }
    try:
        manifest = json.loads(mpath.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "ok": False,
            "status": "FAILED_INTEGRITY",
            "errors": [f"invalid manifest json: {exc}"],
            "files_verified": 0,
        }

    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        return {
            "ok": False,
            "status": "FAILED_INTEGRITY",
            "errors": ["empty or malformed manifest files map"],
            "files_verified": 0,
        }

    root_res = result_dir.resolve()
    errors: list[str] = []
    verified = 0
    for rel, meta in sorted(files.items()):
        pp = PurePosixPath(str(rel))
        if pp.is_absolute() or ".." in pp.parts or "\\" in str(rel):
            errors.append(f"unsafe relative path in manifest: {rel!r}")
            continue
        target = (root_res / Path(*pp.parts)).resolve(strict=False)
        try:
            target.relative_to(root_res)
        except ValueError:
            errors.append(f"path escapes result_dir: {rel!r}")
            continue
        if not target.is_file():
            errors.append(f"missing file: {rel}")
            continue
        exp_sha = meta.get("sha256") if isinstance(meta, dict) else str(meta)
        got_sha = _sha256_file(target)
        if got_sha != exp_sha:
            errors.append(f"sha256 mismatch for {rel}: expected={exp_sha} got={got_sha}")
            continue
        verified += 1

    ok = len(errors) == 0 and verified == len(files)
    return {
        "ok": ok,
        "status": "VERIFIED_PASS" if ok else "FAILED_INTEGRITY",
        "job_id": manifest.get("job_id"),
        "host": manifest.get("host"),
        "files_verified": verified,
        "errors": errors,
    }


_REMOTE_RUNNER_PY = r'''"""Immutable remote job runner on <X13_WORKER> with AC-power guard, atomic lock & manifest."""
from __future__ import annotations
import ctypes, hashlib, json, os, pathlib, re, subprocess, sys, tarfile, tempfile, time
from datetime import datetime, timezone

_SAFE_FLAG_RE = re.compile(r"^--[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")

def _ac_online() -> bool:
    if os.name != "nt":
        return True
    class _SPS(ctypes.Structure):
        _fields_ = [("AC", ctypes.c_ubyte), ("BF", ctypes.c_ubyte), ("BP", ctypes.c_ubyte),
                    ("SF", ctypes.c_ubyte), ("BLT", ctypes.c_ulong), ("BFLT", ctypes.c_ulong)]
    s = _SPS()
    return bool(ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(s))) and int(s.AC) == 1

def _inspect_pid_created_at(pid: int) -> tuple[bool, str]:
    if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
        return True, ""
    if os.name != "nt":
        try:
            os.kill(pid, 0)
            return True, str(pid)
        except ProcessLookupError:
            return True, ""
        except PermissionError:
            return True, str(pid)
        except Exception:
            return False, ""
    try:
        ps = (
            f"$p=Get-CimInstance Win32_Process -Filter 'ProcessId = {int(pid)}'; "
            "if ($p) { $p.CreationDate.ToUniversalTime().ToString('o') }"
        )
        r = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps],
            capture_output=True, text=True, timeout=3,
        )
        if r.returncode != 0:
            return False, ""
        return True, r.stdout.strip()
    except Exception:
        return False, ""

def _proc_created_at(pid: int) -> str:
    ok, val = _inspect_pid_created_at(pid)
    if ok and val:
        return val
    return datetime.now(timezone.utc).isoformat()

def _is_lock_stale(lock_path: pathlib.Path) -> bool:
    try:
        saved = json.loads(lock_path.read_text(encoding="utf-8"))
    except Exception:
        return False
    pid = saved.get("pid")
    if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
        return False
    ok, cur_created = _inspect_pid_created_at(pid)
    if not ok:
        return False
    if not cur_created:
        return True
    saved_created = saved.get("created_at") or saved.get("createdAt")
    if not saved_created:
        return False
    return str(cur_created) != str(saved_created)

def _acquire_active_lock(lock_path: pathlib.Path, lock_meta: dict) -> bool:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(lock_meta, indent=2, sort_keys=True) + "\n").encode("utf-8")
    for _ in range(2):
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            if _is_lock_stale(lock_path):
                try:
                    lock_path.unlink(missing_ok=True)
                except OSError:
                    return False
                continue
            return False
        try:
            os.write(fd, payload)
            os.fsync(fd)
        finally:
            os.close(fd)
        return True
    return False

def _sha(p: pathlib.Path) -> str:
    with p.open("rb") as fh:
        return hashlib.file_digest(fh, "sha256").hexdigest()

def _atomic_json(p: pathlib.Path, obj: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    txt = json.dumps(obj, indent=2, sort_keys=True) + "\n"
    kw = {"encoding": "utf-8", "newline": "\n", "dir": p.parent, "suffix": ".tmp", "delete": False}
    with tempfile.NamedTemporaryFile("w", **kw) as fh:
        fh.write(txt); fh.flush(); os.fsync(fh.fileno()); tmp = pathlib.Path(fh.name)
    os.replace(tmp, p)

def main() -> int:
    job_id, threads_s = sys.argv[1], sys.argv[2]
    extra_args = sys.argv[3:]
    base = pathlib.Path(r"C:\NaqexResearch")
    job_dir = base / "jobs" / job_id
    src_dir = job_dir / "src"
    res_dir = base / "results" / job_id
    lock_path = base / "locks" / "active_job.lock"
    res_dir.mkdir(parents=True, exist_ok=True)
    if not _ac_online():
        return 77
    lock_meta = {
        "job_id": job_id, "pid": os.getpid(),
        "created_at": _proc_created_at(os.getpid()), "executable": sys.executable,
    }
    if not _acquire_active_lock(lock_path, lock_meta):
        return 78
    t0 = time.perf_counter()
    try:
        bm = json.loads((job_dir / "bundle_manifest.sha256.json").read_text(encoding="utf-8"))
        tar_p = job_dir / "bundle.tar.gz"
        if _sha(tar_p) != bm["bundle_tar_sha256"]:
            raise RuntimeError("Bundle tar SHA-256 mismatch")
        src_dir.mkdir(parents=True, exist_ok=True)
        with tarfile.open(tar_p, "r:gz") as tf:
            for m in tf.getmembers():
                dest = (src_dir / m.name).resolve()
                dest.relative_to(src_dir.resolve())
            if sys.version_info >= (3, 12):
                tf.extractall(src_dir, filter="data")
            else:
                tf.extractall(src_dir)
        for rel, exp_sha in bm["files"].items():
            if _sha(src_dir / rel) != exp_sha:
                raise RuntimeError(f"Extracted file SHA mismatch: {rel}")
        entry = src_dir / bm["entry_arc"]
        env = os.environ.copy()
        env["NUMBA_NUM_THREADS"] = threads_s
        env["OMP_NUM_THREADS"] = threads_s
        env["NAQEX_RESULT_DIR"] = str(res_dir)
        env["NAQEX_JOB_ID"] = job_id
        env["NAQEX_WORKER_ROLE"] = "X13_WORKER"
        env["NAQEX_WORKSPACE_ROOT"] = str(base)
        env["PYTHONUTF8"] = "1"
        ai_engines_dir = base / "tooling" / "ai-engines"
        py_parts = [str(ai_engines_dir), str(src_dir)]
        if env.get("PYTHONPATH"):
            py_parts.append(env["PYTHONPATH"])
        env["PYTHONPATH"] = os.pathsep.join(py_parts)
        child_args = list(extra_args)
        sb_arc = bm.get("shard_batch_arc")
        if isinstance(sb_arc, str) and sb_arc:
            sb_path = (src_dir / sb_arc).resolve()
            sb_path.relative_to(src_dir.resolve())
            env["NAQEX_SHARD_BATCH_FILE"] = str(sb_path)
            try:
                sb_obj = json.loads(sb_path.read_text(encoding="utf-8"))
                idxs = sb_obj.get("shard_indices")
                if isinstance(idxs, list):
                    env["NAQEX_SHARD_INDICES"] = ",".join(str(int(i)) for i in idxs)
                    env["NAQEX_SHARD_COUNT"] = str(len(idxs))
                if isinstance(sb_obj.get("total_shards"), int):
                    env["NAQEX_TOTAL_SHARDS"] = str(int(sb_obj["total_shards"]))
            except Exception:
                pass
            sb_flag = bm.get("shard_arg_flag")
            if isinstance(sb_flag, str) and _SAFE_FLAG_RE.fullmatch(sb_flag):
                child_args.extend([sb_flag, str(sb_path)])
        stdout_p = res_dir / "stdout.log"
        stderr_p = res_dir / "stderr.log"
        with (
            stdout_p.open("w", encoding="utf-8", newline="\n") as out_fh,
            stderr_p.open("w", encoding="utf-8", newline="\n") as err_fh,
        ):
            proc = subprocess.Popen(
                [sys.executable, str(entry), *child_args],
                cwd=str(src_dir), env=env, stdout=out_fh, stderr=err_fh,
            )
            off_ac_since = None
            while proc.poll() is None:
                if not _ac_online():
                    off_ac_since = off_ac_since or time.monotonic()
                    if time.monotonic() - off_ac_since >= 60.0:
                        proc.terminate()
                        proc.wait(timeout=5)
                        return 77
                else:
                    off_ac_since = None
                time.sleep(0.25)
            rc = proc.wait()
        _atomic_json(res_dir / "host_meta.json", {
            "job_id": job_id, "host": "X13_WORKER", "returncode": rc,
            "threads": int(threads_s), "elapsed_sec": round(time.perf_counter() - t0, 3),
            "completed_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "order_send_count": 0,
        })
        if rc != 0:
            return rc
        files = {}
        for p in sorted(res_dir.rglob("*")):
            if p.is_file() and p.name != "manifest.sha256.json" and not p.name.endswith(".tmp"):
                files[p.relative_to(res_dir).as_posix()] = {"sha256": _sha(p), "bytes": p.stat().st_size}
        _atomic_json(res_dir / "manifest.sha256.json", {
            "schema": "naqex-job-result-manifest-v1", "job_id": job_id, "host": "X13_WORKER",
            "completed_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "order_send_count": 0, "files": files,
        })
        return 0
    finally:
        lock_path.unlink(missing_ok=True)

if __name__ == "__main__":
    raise SystemExit(main())
'''


def _run_local_dev_job(
    job_id: str,
    entry_script: Path,
    dest_dir: Path,
    *,
    cores: int,
    priority: str,
    extra_args: list[str] | None = None,
    extra_env: dict[str, str] | None = None,
    timeout: int = 3600,
) -> dict[str, Any]:
    dest_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["NUMBA_NUM_THREADS"] = str(max(1, cores))
    env["OMP_NUM_THREADS"] = str(max(1, cores))
    env["NAQEX_RESULT_DIR"] = str(dest_dir)
    env["NAQEX_JOB_ID"] = job_id
    env["NAQEX_WORKER_ROLE"] = "DEV_PC"
    env["NAQEX_WORKSPACE_ROOT"] = str(ROOT)
    env["PYTHONUTF8"] = "1"
    py_parts = [str(AI_ENGINES_DIR)]
    if env.get("PYTHONPATH"):
        py_parts.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(py_parts)
    if extra_env:
        env.update(extra_env)
    flags = 0
    if os.name == "nt":
        flags = _BELOW_NORMAL_PRIORITY_CLASS if priority == "BELOW_NORMAL" else _NORMAL_PRIORITY_CLASS
    t0 = time.perf_counter()
    proc = subprocess.run(
        [sys.executable, str(entry_script), *(extra_args or [])],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        creationflags=flags,
    )
    (dest_dir / "stdout.log").write_text(proc.stdout or "", encoding="utf-8", newline="\n")
    (dest_dir / "stderr.log").write_text(proc.stderr or "", encoding="utf-8", newline="\n")
    _atomic_write_json(
        dest_dir / "host_meta.json",
        {
            "job_id": job_id,
            "host": "DEV_PC",
            "returncode": proc.returncode,
            "cores": cores,
            "priority": priority,
            "elapsed_sec": round(time.perf_counter() - t0, 3),
            "completed_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "order_send_count": ORDER_SEND_COUNT,
        },
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Local job {job_id} failed (rc={proc.returncode}): {(proc.stderr or '').strip()[:300]}")
    write_result_manifest(dest_dir, job_id=job_id, host_label="DEV_PC")
    verify = verify_result_manifest(dest_dir)
    return {
        "executed_on": "DEV_PC",
        "returncode": proc.returncode,
        "cores": cores,
        "priority": priority,
        "verify": verify,
    }


def pull_results(
    job_id: str,
    dest_dir: Path,
    *,
    host: str = X13_HOSTS[0],
    cleanup_remote: bool = False,
) -> dict[str, Any]:
    """Pull `C:\\NaqexResearch\\results\\<job_id>\\` from `<X13_WORKER>` and strictly verify SHA-256 manifest."""
    jid = _validate_job_id(job_id)
    alias = _validate_host(host)
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Atomic readiness check: refuse pull unless manifest.sha256.json exists on remote
    chk = subprocess.run(
        ["ssh", "-o", "ConnectTimeout=4", "-o", "BatchMode=yes", alias,
         f'if exist "{X13_BASE_DIR}\\results\\{jid}\\manifest.sha256.json" (echo READY) else (echo NOT_READY)'],
        capture_output=True, text=True, timeout=10,
    )
    if chk.returncode != 0 or "READY" not in (chk.stdout or ""):
        return {
            "ok": False,
            "status": "NOT_READY_MISSING_MANIFEST",
            "job_id": jid,
            "ssh_alias": alias,
            "dest_dir": str(dest_dir),
        }

    # Pull contents into a staging sibling and copy files cleanly into dest_dir
    with tempfile.TemporaryDirectory(prefix=f"x13_pull_{jid}_") as td:
        stage = Path(td)
        scp = subprocess.run(
            ["scp", "-r", "-o", "ConnectTimeout=6", "-o", "BatchMode=yes",
             f"{alias}:C:/NaqexResearch/results/{jid}", str(stage)],
            capture_output=True, text=True, timeout=120,
        )
        if scp.returncode != 0:
            return {"ok": False, "status": "SCP_PULL_FAILED", "stderr": scp.stderr.strip(), "job_id": jid}
        pulled_root = stage / jid
        if not pulled_root.is_dir():
            return {"ok": False, "status": "SCP_EMPTY_DIR", "job_id": jid}
        verify = verify_result_manifest(pulled_root)
        if not verify["ok"]:
            return {"ok": False, "status": "FAILED_INTEGRITY", "job_id": jid, "verify": verify}
        for src_file in sorted(pulled_root.rglob("*")):
            if src_file.is_file():
                rel = src_file.relative_to(pulled_root)
                out_f = dest_dir / rel
                out_f.parent.mkdir(parents=True, exist_ok=True)
                out_f.write_bytes(src_file.read_bytes())

    final_verify = verify_result_manifest(dest_dir)
    if cleanup_remote and final_verify["ok"]:
        subprocess.run(
            ["ssh", "-o", "ConnectTimeout=4", "-o", "BatchMode=yes", alias,
             f'rmdir /s /q "{X13_BASE_DIR}\\jobs\\{jid}" "{X13_BASE_DIR}\\results\\{jid}"'],
            capture_output=True, text=True, timeout=15,
        )
    return {
        "ok": final_verify["ok"],
        "status": final_verify["status"],
        "job_id": jid,
        "ssh_alias": alias,
        "dest_dir": str(dest_dir),
        "verify": final_verify,
    }


def _fallback_dev_policy(dev_pc: dict[str, Any], *, force_mode_b: bool = False) -> tuple[int, str]:
    """Compute fail-closed local `<DEV_PC>` core cap & OS priority matching Mode A / Mode B."""
    if force_mode_b:
        return 5, "NORMAL"
    mode = dev_pc.get("mode") or classify_dev_pc_mode(dev_pc)
    gpu_val = _finite_float(dev_pc.get("gpu_util_pct"))
    gaming = (gpu_val is None or gpu_val > 25.0) or bool(dev_pc.get("fullscreen_busy", False))
    if mode == "MODE_A_OWNER_ACTIVE":
        return (2 if gaming else 3), "BELOW_NORMAL"
    return 5, "NORMAL"


def _execute_x13_bundle(
    job_id: str,
    entry: Path,
    out_dir: Path,
    *,
    alias: str,
    x13_threads: int,
    safe_args: list[str],
    extra_files: tuple[Path, ...] = (),
    shard_batch_arc: str | None = None,
    shard_arg_flag: str | None = None,
    timeout: int = 3600,
    lease_max_wait_sec: float = 0.0,
    lease_base_backoff_sec: float = 2.0,
    lease_max_backoff_sec: float = 15.0,
    lease_sleep_fn: Callable[[float], None] = time.sleep,
    lan_only: bool = False,
    strict_ntp: bool = False,
    allow_ntp_drift: bool = False,
    ram_gb: float = 4.0,
) -> dict[str, Any]:
    """Upload immutable Dev-only bundle and execute 1 atomic job on `<X13_WORKER>` with rc=78 lock retry."""
    jid = _validate_job_id(job_id)
    safe_alias = _validate_host(alias)
    with tempfile.TemporaryDirectory(prefix=f"bundle_{jid}_") as td:
        bdir = Path(td)
        bundle = build_job_bundle(
            jid,
            entry,
            bdir,
            extra_files=extra_files,
            shard_batch_arc=shard_batch_arc,
            shard_arg_flag=shard_arg_flag,
        )
        runner_local = bdir / "run_job.py"
        runner_local.write_text(_REMOTE_RUNNER_PY, encoding="utf-8", newline="\n")

        mk = subprocess.run(
            [
                "ssh",
                "-o",
                "ConnectTimeout=4",
                "-o",
                "BatchMode=yes",
                safe_alias,
                f'if not exist "{X13_BASE_DIR}\\jobs\\{jid}" mkdir "{X13_BASE_DIR}\\jobs\\{jid}" '
                f'& if not exist "{X13_BASE_DIR}\\locks" mkdir "{X13_BASE_DIR}\\locks" '
                f'& if not exist "{X13_BASE_DIR}\\results\\{jid}" mkdir "{X13_BASE_DIR}\\results\\{jid}"',
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if mk.returncode != 0:
            raise RuntimeError(f"x13_mkdir_failed(rc={mk.returncode})")

        for local_p in (bundle["tar_path"], bundle["manifest_path"], runner_local):
            cp = subprocess.run(
                [
                    "scp",
                    "-o",
                    "ConnectTimeout=6",
                    "-o",
                    "BatchMode=yes",
                    str(local_p),
                    f"{safe_alias}:C:/NaqexResearch/jobs/{jid}/{local_p.name}",
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if cp.returncode != 0:
                raise RuntimeError(f"x13_scp_upload_failed({local_p.name},rc={cp.returncode})")

        quoted_extra = " ".join(f'"{a}"' for a in safe_args)
        run_cmd = (
            f'"{X13_REMOTE_PYTHON}" "{X13_BASE_DIR}\\jobs\\{jid}\\run_job.py" '
            f'"{jid}" "{int(x13_threads)}" {quoted_extra}'
        ).strip()

        lock_retries = 0
        remaining_lease = max(0.0, float(lease_max_wait_sec))
        while True:
            run_p = subprocess.run(
                ["ssh", "-o", "ConnectTimeout=6", "-o", "BatchMode=yes", safe_alias, run_cmd],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            if run_p.returncode == _X13_LOCK_BUSY_RC:
                if remaining_lease > 0.0 and lock_retries < 5:
                    lock_retries += 1
                    lease = wait_for_x13_lease(
                        lan_only=lan_only,
                        strict_ntp=strict_ntp,
                        allow_ntp_drift=allow_ntp_drift,
                        min_ram_gb=ram_gb,
                        max_wait_sec=remaining_lease,
                        base_backoff_sec=lease_base_backoff_sec,
                        max_backoff_sec=lease_max_backoff_sec,
                        sleep_fn=lease_sleep_fn,
                    )
                    remaining_lease = max(0.0, remaining_lease - float(lease["waited_sec"]))
                    if lease["acquired"]:
                        continue
                    raise RuntimeError(f"x13_busy_active_job_lock_timeout({','.join(lease['reasons'])})")
                raise RuntimeError("x13_busy_active_job_lock")
            if run_p.returncode == _X13_AC_UNPLUGGED_RC:
                raise RuntimeError("x13_ac_unplugged_during_run")
            if run_p.returncode != 0:
                raise RuntimeError(f"x13_remote_exec_failed(rc={run_p.returncode}): {run_p.stderr.strip()[:200]}")
            break

        pulled = pull_results(jid, out_dir, host=safe_alias, cleanup_remote=False)
        if not pulled["ok"]:
            raise RuntimeError(f"x13_pull_or_sha_failed({pulled['status']})")
        return {
            "executed_on": "X13_WORKER",
            "ssh_alias": safe_alias,
            "x13_threads": int(x13_threads),
            "lock_retries": lock_retries,
            "pull": pulled,
            "verify": pulled["verify"],
        }


def dispatch_job(
    job_id: str,
    entry_script: Path,
    *,
    est_minutes: float = 15.0,
    ram_gb: float = 4.0,
    shardable: bool = False,
    shards: int = 10,
    touches_holdout: bool = False,
    touches_vps: bool = False,
    requires_admin: bool = False,
    needs_gpu: bool = False,
    strict_ntp: bool = False,
    allow_ntp_drift: bool = False,
    force_x13: bool = False,
    allow_mode_a_assist: bool = False,
    force_mode_b: bool = False,
    owner_approved_long_run: bool = False,
    lan_only: bool = False,
    dry_run: bool = False,
    dest_dir: Path | None = None,
    extra_args: list[str] | None = None,
    lease_max_wait_sec: float = 0.0,
    lease_base_backoff_sec: float = 2.0,
    lease_max_backoff_sec: float = 15.0,
    lease_sleep_fn: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """Probe, route, and execute a Dev-only job with immutable bundle + SHA-256 verification + silent fallback."""
    jid = _validate_job_id(job_id)
    safe_args = _validate_extra_args(extra_args)
    entry = entry_script.resolve()
    if not touches_holdout:
        assert_dev_only_path(entry)

    dev_pc = probe_dev_pc()
    lease_info: dict[str, Any] | None = None
    if (
        not dry_run
        and lease_max_wait_sec > 0.0
        and not touches_holdout
        and not touches_vps
        and not requires_admin
        and not needs_gpu
    ):
        lease_info = wait_for_x13_lease(
            lan_only=lan_only,
            strict_ntp=strict_ntp,
            allow_ntp_drift=allow_ntp_drift,
            min_ram_gb=ram_gb,
            max_wait_sec=lease_max_wait_sec,
            base_backoff_sec=lease_base_backoff_sec,
            max_backoff_sec=lease_max_backoff_sec,
            sleep_fn=lease_sleep_fn,
        )
        x13 = lease_info["x13_worker"]
    else:
        x13 = probe_x13_worker(lan_only=lan_only, strict_ntp=strict_ntp, allow_ntp_drift=allow_ntp_drift)

    decision = decide_route(
        dev_pc,
        x13,
        est_minutes=est_minutes,
        ram_gb=ram_gb,
        shardable=shardable,
        shards=shards,
        touches_holdout=touches_holdout,
        touches_vps=touches_vps,
        requires_admin=requires_admin,
        needs_gpu=needs_gpu,
        strict_ntp=strict_ntp,
        allow_ntp_drift=allow_ntp_drift,
        force_x13=force_x13,
        allow_mode_a_assist=allow_mode_a_assist,
        force_mode_b=force_mode_b,
        owner_approved_long_run=owner_approved_long_run,
    )
    out_dir = dest_dir or (ROOT / ".tmp" / "compute_results" / jid)
    receipt: dict[str, Any] = {
        "schema": "naqex-compute-dispatch-v1",
        "job_id": jid,
        "checked_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "order_send_count": ORDER_SEND_COUNT,
        "dry_run": dry_run,
        "dev_pc": dev_pc,
        "x13_worker": x13,
        "decision": decision,
        "dest_dir": str(out_dir),
    }
    if lease_info is not None:
        receipt["lease"] = {
            "acquired": lease_info["acquired"],
            "status": lease_info["status"],
            "attempts": lease_info["attempts"],
            "waited_sec": lease_info["waited_sec"],
        }

    blocked = (
        decision["target"] == "BLOCKED_NEEDS_APPROVAL"
        or bool(decision.get("ask_owner_required"))
    )
    if dry_run or blocked:
        receipt["ok"] = not blocked
        if blocked:
            receipt["blocked_reason"] = "TIER_3_ASK_OWNER_APPROVAL_REQUIRED"
        return receipt

    if decision["target"] == "X13_ONLY":
        alias = str(x13["ssh_alias"])
        try:
            x13_exec = _execute_x13_bundle(
                jid,
                entry,
                out_dir,
                alias=alias,
                x13_threads=int(decision["x13_threads"]),
                safe_args=safe_args,
                lease_max_wait_sec=lease_max_wait_sec,
                lease_base_backoff_sec=lease_base_backoff_sec,
                lease_max_backoff_sec=lease_max_backoff_sec,
                lease_sleep_fn=lease_sleep_fn,
                lan_only=lan_only,
                strict_ntp=strict_ntp,
                allow_ntp_drift=allow_ntp_drift,
                ram_gb=ram_gb,
            )
            receipt["ok"] = True
            receipt["execution"] = x13_exec
            return receipt
        except Exception as exc:
            # Silent automatic fallback to <DEV_PC> if X13 drops or loses AC power mid-flight
            fb_reason = f"x13_runtime_fallback: {exc}"
            decision["fallback_used"] = True
            decision["fallback_reason"] = fb_reason
            cores, prio = _fallback_dev_policy(dev_pc, force_mode_b=force_mode_b)
            local_res = _run_local_dev_job(jid, entry, out_dir, cores=cores, priority=prio, extra_args=safe_args)
            receipt["ok"] = bool(local_res["verify"]["ok"])
            receipt["execution"] = local_res
            return receipt

    local_res = _run_local_dev_job(
        jid,
        entry,
        out_dir,
        cores=max(1, int(decision["dev_pc_cores"])),
        priority=str(decision["dev_pc_priority"]),
        extra_args=safe_args,
    )
    receipt["ok"] = bool(local_res["verify"]["ok"])
    receipt["execution"] = local_res
    return receipt


def _normalize_shard_specs(shard_specs: Sequence[Any] | int) -> list[Any]:
    if isinstance(shard_specs, bool):
        raise ValueError("shard_specs must be a positive int or non-empty sequence, not bool")
    if isinstance(shard_specs, int):
        if shard_specs < 1:
            raise ValueError(f"shard_specs count must be >= 1, got {shard_specs}")
        return [{"shard_id": i, "index": i} for i in range(shard_specs)]
    items = list(shard_specs)
    if not items:
        raise ValueError("shard_specs sequence must be non-empty")
    return items


def _default_merge_shard_payloads(worker_records: list[dict[str, Any]]) -> dict[str, Any]:
    merged_shards: list[Any] = []
    worker_summaries: list[dict[str, Any]] = []
    for rec in worker_records:
        payload = rec["payload"]
        worker_summaries.append(
            {
                "worker": rec["worker"],
                "executed_on": rec["executed_on"],
                "shard_indices": rec["shard_indices"],
            }
        )
        if isinstance(payload, dict) and isinstance(payload.get("shards"), list):
            merged_shards.extend(payload["shards"])
        elif isinstance(payload, dict) and isinstance(payload.get("results"), list):
            merged_shards.extend(payload["results"])
        elif isinstance(payload, list):
            merged_shards.extend(payload)
        else:
            merged_shards.append(payload)

    if merged_shards and all(
        isinstance(item, dict) and ("shard_id" in item or "index" in item) for item in merged_shards
    ):
        merged_shards.sort(key=lambda item: (item.get("index", item.get("shard_id", 0)), str(item.get("shard_id", ""))))

    return {
        "schema": "naqex-merged-shard-results-v1",
        "total_merged_items": len(merged_shards),
        "workers": worker_summaries,
        "shards": merged_shards,
    }


def dispatch_parallel_shards(
    job_id: str,
    entry_script: Path,
    shard_specs: Sequence[Any] | int,
    *,
    est_minutes: float = 20.0,
    ram_gb: float = 4.0,
    touches_holdout: bool = False,
    touches_vps: bool = False,
    requires_admin: bool = False,
    needs_gpu: bool = False,
    strict_ntp: bool = False,
    allow_ntp_drift: bool = False,
    allow_mode_a_assist: bool = False,
    force_mode_b: bool = False,
    owner_approved_long_run: bool = False,
    lan_only: bool = False,
    dry_run: bool = False,
    dest_dir: Path | None = None,
    extra_files: tuple[Path, ...] = (),
    extra_args: list[str] | None = None,
    shard_arg_flag: str | None = None,
    lease_max_wait_sec: float = 60.0,
    lease_base_backoff_sec: float = 2.0,
    lease_max_backoff_sec: float = 15.0,
    lease_sleep_fn: Callable[[float], None] = time.sleep,
    result_filename: str = "shard_results.json",
    merge_fn: Callable[[list[dict[str, Any]]], dict[str, Any]] | None = None,
    timeout: int = 3600,
) -> dict[str, Any]:
    """Mode-aware parallel shard dispatcher (`PARALLEL_60_40`, `PARALLEL_20_80_MODE_A`, `X13_ONLY`, fallback).

    Runs `<X13_WORKER>`'s assigned shard slice as ONE atomic batched job (respecting the single
    `active_job.lock` via the Safe Lease Queue) concurrently with `<DEV_PC>`'s local slice,
    verifies every worker's `manifest.sha256.json`, merges results deterministically, and
    silently falls back to `<DEV_PC>` (strictly obeying Mode A/B core caps & priority) if X13
    is unreachable, ineligible, or drops mid-flight.
    """
    jid = _validate_job_id(job_id)
    safe_args = _validate_extra_args(extra_args)
    if shard_arg_flag is not None and not _SAFE_FLAG_RE.fullmatch(shard_arg_flag):
        raise ValueError(f"Unsafe shard_arg_flag rejected: {shard_arg_flag!r}")
    shards_list = _normalize_shard_specs(shard_specs)
    n_total = len(shards_list)

    entry = entry_script.resolve()
    if not touches_holdout:
        assert_dev_only_path(entry)
        for ef in extra_files:
            assert_dev_only_path(ef.resolve())

    dev_pc = probe_dev_pc()
    may_use_x13 = (
        not touches_holdout
        and not touches_vps
        and not requires_admin
        and not needs_gpu
        and est_minutes >= 10.0
        and (owner_approved_long_run or est_minutes <= 60.0)
    )
    lease_info: dict[str, Any] | None = None
    if not dry_run and may_use_x13 and lease_max_wait_sec > 0.0:
        lease_info = wait_for_x13_lease(
            lan_only=lan_only,
            strict_ntp=strict_ntp,
            allow_ntp_drift=allow_ntp_drift,
            min_ram_gb=ram_gb,
            max_wait_sec=lease_max_wait_sec,
            base_backoff_sec=lease_base_backoff_sec,
            max_backoff_sec=lease_max_backoff_sec,
            sleep_fn=lease_sleep_fn,
        )
        x13 = lease_info["x13_worker"]
    else:
        x13 = probe_x13_worker(lan_only=lan_only, strict_ntp=strict_ntp, allow_ntp_drift=allow_ntp_drift)

    decision = decide_route(
        dev_pc,
        x13,
        est_minutes=est_minutes,
        ram_gb=ram_gb,
        shardable=True,
        shards=max(2, n_total),
        touches_holdout=touches_holdout,
        touches_vps=touches_vps,
        requires_admin=requires_admin,
        needs_gpu=needs_gpu,
        strict_ntp=strict_ntp,
        allow_ntp_drift=allow_ntp_drift,
        allow_mode_a_assist=allow_mode_a_assist,
        force_mode_b=force_mode_b,
        owner_approved_long_run=owner_approved_long_run,
    )

    target = str(decision["target"])
    eff_mode = "MODE_B_IDLE_OVERNIGHT" if force_mode_b else dev_pc.get("mode")
    dev_indices: list[int] = []
    x13_indices: list[int] = []
    if target in ("PARALLEL_60_40", "PARALLEL_20_80_MODE_A"):
        if n_total == 1:
            if eff_mode == "MODE_A_OWNER_ACTIVE" and not allow_mode_a_assist:
                x13_indices = [0]
            else:
                dev_indices = [0]
        else:
            n_dev = int(decision["micro_shards"]["dev_pc"])
            n_dev = max(1, min(n_total - 1, n_dev))
            dev_indices = list(range(0, n_dev))
            x13_indices = list(range(n_dev, n_total))
    elif target == "X13_ONLY":
        x13_indices = list(range(0, n_total))
    elif target == "DEV_PC_ONLY":
        dev_indices = list(range(0, n_total))

    out_dir = dest_dir or (ROOT / ".tmp" / "compute_results" / jid)
    shard_plan: dict[str, Any] = {
        "total_shards": n_total,
        "dev_pc_indices": dev_indices,
        "x13_worker_indices": x13_indices,
        "x13_atomic_batch": bool(x13_indices),
    }
    receipt: dict[str, Any] = {
        "schema": "naqex-parallel-dispatch-v1",
        "job_id": jid,
        "checked_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "order_send_count": ORDER_SEND_COUNT,
        "dry_run": dry_run,
        "dev_pc": dev_pc,
        "x13_worker": x13,
        "decision": decision,
        "shard_plan": shard_plan,
        "dest_dir": str(out_dir),
    }
    if lease_info is not None:
        receipt["lease"] = {
            "acquired": lease_info["acquired"],
            "status": lease_info["status"],
            "attempts": lease_info["attempts"],
            "waited_sec": lease_info["waited_sec"],
            "sleep_history_sec": lease_info["sleep_history_sec"],
        }

    blocked = target == "BLOCKED_NEEDS_APPROVAL" or bool(decision.get("ask_owner_required"))
    if dry_run or blocked:
        receipt["ok"] = not blocked
        if blocked:
            receipt["blocked_reason"] = "TIER_3_ASK_OWNER_APPROVAL_REQUIRED"
        return receipt

    out_dir.mkdir(parents=True, exist_ok=True)
    workers_root = out_dir / "workers"
    workers_root.mkdir(parents=True, exist_ok=True)

    def _write_batch_file(path: Path, worker_role: str, batch_job_id: str, idxs: list[int]) -> Path:
        payload = {
            "schema": "naqex-shard-batch-v1",
            "job_id": jid,
            "batch_job_id": batch_job_id,
            "worker": worker_role,
            "total_shards": n_total,
            "shard_indices": idxs,
            "shards": [shards_list[i] for i in idxs],
        }
        _atomic_write_json(path, payload)
        return path

    def _run_dev_slice(slice_name: str, idxs: list[int], cores: int, prio: str) -> dict[str, Any]:
        sub_jid = f"{jid}_{slice_name}"[:64]
        sub_dir = workers_root / slice_name
        sub_dir.mkdir(parents=True, exist_ok=True)
        batch_path = _write_batch_file(sub_dir / "shard_batch.json", "DEV_PC", sub_jid, idxs)
        local_args = list(safe_args)
        if shard_arg_flag is not None:
            local_args.extend([shard_arg_flag, str(batch_path)])
        local_env = {
            "NAQEX_SHARD_BATCH_FILE": str(batch_path),
            "NAQEX_SHARD_INDICES": ",".join(str(i) for i in idxs),
            "NAQEX_SHARD_COUNT": str(len(idxs)),
            "NAQEX_TOTAL_SHARDS": str(n_total),
        }
        res = _run_local_dev_job(
            sub_jid,
            entry,
            sub_dir,
            cores=cores,
            priority=prio,
            extra_args=local_args,
            extra_env=local_env,
            timeout=timeout,
        )
        return {
            "worker": slice_name,
            "executed_on": "DEV_PC",
            "shard_indices": idxs,
            "result_dir": sub_dir,
            "execution": res,
            "verify": res["verify"],
        }

    def _run_x13_slice(idxs: list[int]) -> dict[str, Any]:
        sub_jid = f"{jid}_x13"[:64]
        sub_dir = workers_root / "x13_worker"
        sub_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=f"x13_batch_{sub_jid}_") as td:
            batch_path = _write_batch_file(Path(td) / "shard_batch.json", "X13_WORKER", sub_jid, idxs)
            res = _execute_x13_bundle(
                sub_jid,
                entry,
                sub_dir,
                alias=str(x13["ssh_alias"]),
                x13_threads=int(decision["x13_threads"]),
                safe_args=safe_args,
                extra_files=(*extra_files, batch_path),
                shard_batch_arc="shard_batch.json",
                shard_arg_flag=shard_arg_flag,
                timeout=timeout,
                lease_max_wait_sec=lease_max_wait_sec,
                lease_base_backoff_sec=lease_base_backoff_sec,
                lease_max_backoff_sec=lease_max_backoff_sec,
                lease_sleep_fn=lease_sleep_fn,
                lan_only=lan_only,
                strict_ntp=strict_ntp,
                allow_ntp_drift=allow_ntp_drift,
                ram_gb=ram_gb,
            )
        return {
            "worker": "x13_worker",
            "executed_on": "X13_WORKER",
            "shard_indices": idxs,
            "result_dir": sub_dir,
            "execution": res,
            "verify": res["verify"],
        }

    completed_workers: list[dict[str, Any]] = []
    x13_error: Exception | None = None
    dev_cores = max(1, int(decision["dev_pc_cores"])) if dev_indices else 0
    dev_prio = str(decision["dev_pc_priority"])

    if dev_indices and x13_indices:
        # Execute PC Dev local slice and X13 1 atomic batched job concurrently.
        with ThreadPoolExecutor(max_workers=2) as pool:
            f_dev = pool.submit(_run_dev_slice, "dev_pc", dev_indices, dev_cores, dev_prio)
            f_x13 = pool.submit(_run_x13_slice, x13_indices)
            # Always await PC Dev slice first so any X13 fallback never oversubscribes local cores.
            dev_worker = f_dev.result()
            completed_workers.append(dev_worker)
            try:
                x13_worker_res = f_x13.result()
                completed_workers.append(x13_worker_res)
            except Exception as exc:
                x13_error = exc
    elif x13_indices:
        try:
            completed_workers.append(_run_x13_slice(x13_indices))
        except Exception as exc:
            x13_error = exc
    elif dev_indices:
        completed_workers.append(_run_dev_slice("dev_pc", dev_indices, dev_cores, dev_prio))

    if x13_error is not None:
        # Silent automatic fallback to <DEV_PC> strictly obeying Mode A/B core caps & priority.
        fb_reason = f"x13_runtime_fallback: {x13_error}"
        decision["fallback_used"] = True
        decision["fallback_reason"] = fb_reason
        fb_cores, fb_prio = _fallback_dev_policy(dev_pc, force_mode_b=force_mode_b)
        completed_workers.append(_run_dev_slice("x13_fallback_dev_pc", x13_indices, fb_cores, fb_prio))

    # Fail-closed SHA-256 verification of EVERY worker manifest before merging
    worker_payloads: list[dict[str, Any]] = []
    worker_receipts: list[dict[str, Any]] = []
    all_workers_ok = True
    for w in completed_workers:
        v = verify_result_manifest(w["result_dir"])
        if not v["ok"]:
            all_workers_ok = False
        worker_receipts.append(
            {
                "worker": w["worker"],
                "executed_on": w["executed_on"],
                "shard_indices": w["shard_indices"],
                "result_dir": str(w["result_dir"]),
                "verify": v,
            }
        )
        res_file = w["result_dir"] / result_filename
        if v["ok"] and res_file.is_file():
            worker_payloads.append(
                {
                    "worker": w["worker"],
                    "executed_on": w["executed_on"],
                    "shard_indices": w["shard_indices"],
                    "payload": json.loads(res_file.read_text(encoding="utf-8")),
                }
            )

    if not all_workers_ok:
        receipt["ok"] = False
        receipt["status"] = "FAILED_INTEGRITY"
        receipt["workers"] = worker_receipts
        return receipt

    merged_payload: dict[str, Any] | None = None
    if worker_payloads:
        merged_payload = (
            merge_fn(worker_payloads)
            if merge_fn is not None
            else _default_merge_shard_payloads(worker_payloads)
        )
        _atomic_write_json(out_dir / "merged_results.json", merged_payload)

    hosts_used = sorted({w["executed_on"] for w in completed_workers})
    host_label = "+".join(hosts_used) if hosts_used else "DEV_PC"
    summary_doc: dict[str, Any] = {
        "schema": "naqex-parallel-summary-v1",
        "job_id": jid,
        "target": target,
        "dev_pc_mode": dev_pc.get("mode"),
        "fallback_used": bool(decision.get("fallback_used")),
        "fallback_reason": decision.get("fallback_reason"),
        "hosts_executed": hosts_used,
        "shard_plan": shard_plan,
        "workers": worker_receipts,
        "merged_results_present": merged_payload is not None,
        "order_send_count": ORDER_SEND_COUNT,
        "completed_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    _atomic_write_json(out_dir / "parallel_summary.json", summary_doc)
    write_result_manifest(out_dir, job_id=jid, host_label=host_label)
    merged_verify = verify_result_manifest(out_dir)

    receipt["ok"] = bool(merged_verify["ok"])
    receipt["status"] = merged_verify["status"]
    receipt["hosts_executed"] = hosts_used
    receipt["workers"] = worker_receipts
    receipt["merged_verify"] = merged_verify
    if merged_payload is not None:
        receipt["merged_results_path"] = str(out_dir / "merged_results.json")
    return receipt


# ==============================================================================
# 4B. ATOMIC DEV-ONLY CACHE SYNC (P0-2)
# ==============================================================================

_REMOTE_CACHE_UNPACK_PY = r'''"""Atomic fail-closed Dev-only cache unpacker on <X13_WORKER> (0 Holdout/secrets)."""
from __future__ import annotations
import hashlib, json, os, pathlib, shutil, sys, tarfile

_FORBIDDEN_TOKENS = (
    "holdout",
    "2025",
    "2026",
    "native_ftmo_holdout_lock",
    "accounts.dat",
    ".ssh",
    "id_ed25519",
    "private_vault",
)

def _sha(p: pathlib.Path) -> str:
    with p.open("rb") as fh:
        return hashlib.file_digest(fh, "sha256").hexdigest()

def main() -> int:
    base = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(r"C:\NaqexResearch")
    staging = base / "cache_staging"
    tar_p = staging / "dev_cache_bundle.tar.gz"
    man_p = staging / "dev_cache_manifest.sha256.json"
    manifest = json.loads(man_p.read_text(encoding="utf-8"))
    if _sha(tar_p) != manifest["archive_sha256"]:
        raise RuntimeError("dev_cache_bundle.tar.gz SHA-256 mismatch")

    extract_dir = staging / "extract"
    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    extract_dir.mkdir(parents=True, exist_ok=True)

    with tarfile.open(tar_p, "r:gz") as tf:
        members = tf.getmembers()
        for m in members:
            norm = m.name.replace("\\", "/")
            if norm.startswith("/") or ".." in pathlib.PurePosixPath(norm).parts or "\\" in m.name:
                raise RuntimeError(f"Unsafe tar member path: {m.name!r}")
            if not (m.isfile() or m.isdir()):
                raise RuntimeError(f"Unsupported non-regular tar member: {m.name!r}")
            low = norm.lower()
            for tok in _FORBIDDEN_TOKENS:
                if tok in low:
                    raise RuntimeError(f"HOLDOUT_OR_SECRET_AIRGAP_VIOLATION in tar member: {m.name!r}")
            dest = (extract_dir / norm).resolve()
            dest.relative_to(extract_dir.resolve())
        if sys.version_info >= (3, 12):
            tf.extractall(extract_dir, filter="data")
        else:
            tf.extractall(extract_dir)

    expected_files = manifest["files"]
    verified = 0
    for rel, meta in sorted(expected_files.items()):
        src = (extract_dir / rel).resolve()
        src.relative_to(extract_dir.resolve())
        if not src.is_file():
            raise RuntimeError(f"Missing extracted cache file: {rel}")
        if _sha(src) != meta["sha256"]:
            raise RuntimeError(f"SHA-256 mismatch on extracted cache file: {rel}")
        dst = (base / rel).resolve()
        dst.relative_to(base.resolve())
        dst.parent.mkdir(parents=True, exist_ok=True)
        os.replace(src, dst)
        verified += 1

    tapes_v2_verified = False
    v2_json_rel = ".runtime/hot-m1-cache/_derived/frozen_9e_tapes_v2.json"
    v2_npz_rel = ".runtime/hot-m1-cache/_derived/frozen_9e_tapes_v2.npz"
    if v2_json_rel in expected_files and v2_npz_rel in expected_files:
        j_ok = _sha(base / v2_json_rel) == expected_files[v2_json_rel]["sha256"]
        n_ok = _sha(base / v2_npz_rel) == expected_files[v2_npz_rel]["sha256"]
        if not (j_ok and n_ok):
            raise RuntimeError("frozen_9e_tapes_v2 post-install SHA-256 verification failed")
        tapes_v2_verified = True

    shutil.rmtree(extract_dir, ignore_errors=True)
    tar_p.unlink(missing_ok=True)
    print(json.dumps({
        "ok": True,
        "files_verified": verified,
        "forbidden_members": 0,
        "frozen_9e_tapes_v2_verified": tapes_v2_verified,
    }))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
'''


def verify_frozen_9e_tapes_v2(derived_dir: Path) -> dict[str, Any]:
    """Fail-closed integrity & pre-2025 air-gap verifier for `frozen_9e_tapes_v2.{json,npz}`."""
    json_path = derived_dir / "frozen_9e_tapes_v2.json"
    npz_path = derived_dir / "frozen_9e_tapes_v2.npz"
    if not json_path.is_file() and not npz_path.is_file():
        return {"present": False, "verified": False, "errors": ["frozen_9e_tapes_v2_not_found"]}

    errors: list[str] = []
    if not json_path.is_file():
        errors.append("missing frozen_9e_tapes_v2.json")
    if not npz_path.is_file():
        errors.append("missing frozen_9e_tapes_v2.npz")
    if errors:
        return {"present": True, "verified": False, "errors": errors}

    try:
        meta = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"present": True, "verified": False, "errors": [f"invalid_json: {exc}"]}

    if not isinstance(meta, dict):
        return {"present": True, "verified": False, "errors": ["json_root_not_object"]}

    schema = meta.get("schema")
    if schema != "naqex-frozen-tapes-v2":
        errors.append(f"unexpected_schema({schema!r})")

    npz_sha = _sha256_file(npz_path)
    expected_npz_sha = meta.get("npz_sha256")
    if (
        not isinstance(expected_npz_sha, str)
        or len(expected_npz_sha) != 64
        or any(ch not in "0123456789abcdefABCDEF" for ch in expected_npz_sha)
    ):
        errors.append(f"missing_or_invalid_npz_sha256({expected_npz_sha!r})")
    elif expected_npz_sha.lower() != npz_sha.lower():
        errors.append(f"npz_sha256_mismatch(expected={expected_npz_sha},got={npz_sha})")

    ext_days = meta.get("ext_days")
    if not isinstance(ext_days, list) or not ext_days:
        errors.append("missing_or_empty_ext_days")
    else:
        bad_ext = [str(d) for d in ext_days if not isinstance(d, str) or not d.strip() or d >= "2025-01-01"]
        if bad_ext:
            errors.append(f"holdout_date_leak_in_ext_days({bad_ext[0]!r})")

    strict_days = meta.get("strict_cluster_a_days")
    if strict_days is not None:
        if not isinstance(strict_days, list):
            errors.append("invalid_strict_cluster_a_days")
        else:
            bad_ca = [str(d) for d in strict_days if not isinstance(d, str) or not d.strip() or d >= "2025-01-01"]
            if bad_ca:
                errors.append(f"holdout_date_leak_in_strict_cluster_a_days({bad_ca[0]!r})")

    return {
        "present": True,
        "verified": len(errors) == 0,
        "schema": schema,
        "json_sha256": _sha256_file(json_path),
        "npz_sha256": npz_sha,
        "ext_days_count": len(meta.get("ext_days") or []) if isinstance(meta.get("ext_days"), list) else 0,
        "errors": errors,
    }


def collect_dev_cache_files(
    *,
    root: Path = ROOT,
    include_tapes: bool = True,
) -> dict[str, Any]:
    """Collect the strict Dev-only allowlist for `<X13_WORKER>` (`40/41` quant_core excl. holdout_guard, etc.)."""
    ai_dir = root / "tooling/ai-engines"
    selected: dict[str, Path] = {}
    counts: dict[str, int] = {
        "quant_core": 0,
        "quant_factory_root": 0,
        "capital_optimizer": 0,
        "offensive3_code": 0,
        "ssot_configs": 0,
        "offensive3_configs": 0,
        "calendars": 0,
        "frozen_tapes": 0,
    }

    def _add(p: Path, bucket: str) -> None:
        rel = p.relative_to(root).as_posix()
        assert_dev_only_path(rel)
        assert_dev_only_path(p.name)
        if rel not in selected:
            selected[rel] = p
            counts[bucket] += 1

    # 1. quant_core/*.py — strictly EXCLUDING holdout_guard.py (40/41 files on PC Dev)
    qc_dir = ai_dir / "quant_core"
    if qc_dir.is_dir():
        for p in sorted(qc_dir.glob("*.py")):
            low_name = p.name.lower()
            if low_name == "holdout_guard.py" or any(tok in low_name for tok in _FORBIDDEN_DEV_TOKENS):
                continue
            _add(p, "quant_core")

    # 2. quant_factory/*.py (excluding holdout/2025/2026) + capital_optimizer/ + offensive3/
    qf_dir = ai_dir / "quant_factory"
    if qf_dir.is_dir():
        for p in sorted(qf_dir.glob("*.py")):
            if any(tok in p.name.lower() for tok in _FORBIDDEN_DEV_TOKENS):
                continue
            _add(p, "quant_factory_root")
        cap_dir = qf_dir / "capital_optimizer"
        if cap_dir.is_dir():
            for p in sorted(cap_dir.rglob("*")):
                if not p.is_file() or "__pycache__" in p.parts:
                    continue
                if p.suffix.lower() not in (".py", ".json"):
                    continue
                if any(tok in p.relative_to(root).as_posix().lower() for tok in _FORBIDDEN_DEV_TOKENS):
                    continue
                _add(p, "capital_optimizer")
        off3_code_dir = qf_dir / "offensive3"
        if off3_code_dir.is_dir():
            for p in sorted(off3_code_dir.rglob("*.py")):
                if not p.is_file() or "__pycache__" in p.parts:
                    continue
                if any(tok in p.relative_to(root).as_posix().lower() for tok in _FORBIDDEN_DEV_TOKENS):
                    continue
                _add(p, "offensive3_code")

    # 3. configs/ssot/ + configs/offensive3/
    ssot_dir = ai_dir / "configs/ssot"
    if ssot_dir.is_dir():
        for p in sorted(ssot_dir.rglob("*")):
            if not p.is_file() or p.suffix.lower() != ".json":
                continue
            if any(tok in p.relative_to(root).as_posix().lower() for tok in _FORBIDDEN_DEV_TOKENS):
                continue
            _add(p, "ssot_configs")

    off3_cfg_dir = ai_dir / "configs/offensive3"
    if off3_cfg_dir.is_dir():
        for p in sorted(off3_cfg_dir.rglob("*.json")):
            if not p.is_file():
                continue
            if any(tok in p.relative_to(root).as_posix().lower() for tok in _FORBIDDEN_DEV_TOKENS):
                continue
            _add(p, "offensive3_configs")

    # 4. configs/calendars/ — explicit pre-2025 allowlist (includes red_news_official_2018_2024_6ccy.json)
    cal_dir = ai_dir / "configs/calendars"
    if cal_dir.is_dir():
        for fname in _DEV_CALENDAR_ALLOWLIST:
            cand = cal_dir / fname
            if cand.is_file():
                _add(cand, "calendars")

    # 5. .runtime/hot-m1-cache/_derived/frozen_9e_tapes_v2.{json,npz} (with strict integrity verification)
    derived_dir = root / ".runtime/hot-m1-cache/_derived"
    tapes_v2_check = (
        verify_frozen_9e_tapes_v2(derived_dir)
        if include_tapes
        else {"present": False, "verified": False, "errors": []}
    )
    if include_tapes:
        if tapes_v2_check["present"]:
            if not tapes_v2_check["verified"]:
                raise ValueError(f"frozen_9e_tapes_v2 verification failed: {tapes_v2_check['errors']}")
            for ext in (".json", ".npz"):
                _add(derived_dir / f"frozen_9e_tapes_v2{ext}", "frozen_tapes")
        else:
            for ext in (".json", ".npz"):
                cand = derived_dir / f"frozen_9e_tapes_v1{ext}"
                if cand.is_file():
                    _add(cand, "frozen_tapes")

    # Final fail-closed audit across every collected archive path
    for rel in selected:
        assert_dev_only_path(rel)
        if "holdout_guard" in rel.lower():
            raise ValueError(f"HOLDOUT_OR_SECRET_AIRGAP_VIOLATION: holdout_guard leaked into cache list: {rel}")

    ordered = [(rel, selected[rel]) for rel in sorted(selected)]
    return {
        "entries": ordered,
        "counts": counts,
        "frozen_9e_tapes_v2": tapes_v2_check,
        "holdout_guard_excluded": not any("holdout_guard" in rel.lower() for rel, _ in ordered),
    }


def build_dev_cache_archive(
    out_dir: Path,
    *,
    root: Path = ROOT,
    include_tapes: bool = True,
) -> dict[str, Any]:
    """Pack 1 atomic `dev_cache_bundle.tar.gz` + `dev_cache_manifest.sha256.json` passing every member via air-gap."""
    collected = collect_dev_cache_files(root=root, include_tapes=include_tapes)
    entries: list[tuple[str, Path]] = collected["entries"]
    out_dir.mkdir(parents=True, exist_ok=True)
    tar_path = out_dir / "dev_cache_bundle.tar.gz"
    file_entries: dict[str, dict[str, Any]] = {}

    tmp_tar: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=out_dir,
            prefix=".dev_cache_bundle.",
            suffix=".tar.gz.tmp",
            delete=False,
        ) as raw_fh:
            tmp_tar = Path(raw_fh.name)
        with tarfile.open(tmp_tar, "w:gz", compresslevel=1) as tf:
            for arc, src in entries:
                assert_dev_only_path(arc)
                assert_dev_only_path(src.name)
                tf.add(str(src), arcname=arc)
                file_entries[arc] = {"sha256": _sha256_file(src), "bytes": src.stat().st_size}
        os.replace(tmp_tar, tar_path)
        tmp_tar = None
    finally:
        if tmp_tar is not None:
            tmp_tar.unlink(missing_ok=True)

    archive_sha = _sha256_file(tar_path)
    manifest: dict[str, Any] = {
        "schema": "naqex-dev-cache-bundle-v2",
        "created_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "git_sha": _current_git_sha(),
        "archive_name": tar_path.name,
        "archive_sha256": archive_sha,
        "archive_bytes": tar_path.stat().st_size,
        "file_count": len(file_entries),
        "total_bytes": sum(m["bytes"] for m in file_entries.values()),
        "counts": collected["counts"],
        "holdout_airgap_enforced": True,
        "holdout_guard_excluded": True,
        "forbidden_files_count": 0,
        "frozen_9e_tapes_v2_verified": bool(collected["frozen_9e_tapes_v2"]["verified"]),
        "files": file_entries,
    }
    manifest_path = out_dir / "dev_cache_manifest.sha256.json"
    _atomic_write_json(manifest_path, manifest)
    return {
        "tar_path": tar_path,
        "manifest_path": manifest_path,
        "manifest": manifest,
        "frozen_9e_tapes_v2": collected["frozen_9e_tapes_v2"],
    }


def sync_dev_cache(
    *,
    lan_only: bool = False,
    dry_run: bool = False,
    verify_only: bool = False,
    host: str | None = None,
    root: Path = ROOT,
    include_tapes: bool = True,
) -> dict[str, Any]:
    """One-way atomic `tar.gz` allowlist sync of Dev-only (<= 2024) assets to `<X13_WORKER>` (0 Holdout)."""
    x13 = probe_x13_worker(hosts=(host,) if host else X13_HOSTS, lan_only=lan_only)
    if not x13["reachable"]:
        return {"ok": False, "status": "X13_UNREACHABLE", "x13_worker": x13}

    collected = collect_dev_cache_files(root=root, include_tapes=include_tapes)
    entries: list[tuple[str, Path]] = collected["entries"]
    summary: dict[str, Any] = {
        "schema": "naqex-sync-dev-cache-v2",
        "ok": True,
        "ssh_alias": x13["ssh_alias"],
        "dry_run": dry_run,
        "verify_only": verify_only,
        "archive_format": "tar.gz",
        "atomic_single_archive": True,
        "file_count": len(entries),
        "total_bytes": sum(p.stat().st_size for _, p in entries),
        "counts": collected["counts"],
        "frozen_9e_tapes_v2_verified": bool(collected["frozen_9e_tapes_v2"]["verified"]),
        "frozen_9e_tapes_v2": collected["frozen_9e_tapes_v2"],
        "holdout_airgap_enforced": True,
        "holdout_guard_excluded": bool(collected["holdout_guard_excluded"]),
        "forbidden_files": 0,
    }
    if dry_run or verify_only:
        summary["files"] = [arc for arc, _ in entries]
        return summary

    alias = _validate_host(str(x13["ssh_alias"]))
    with tempfile.TemporaryDirectory(prefix="x13_dev_cache_") as td:
        stage_dir = Path(td)
        packed = build_dev_cache_archive(stage_dir, root=root, include_tapes=include_tapes)
        unpack_local = stage_dir / "unpack_cache.py"
        unpack_local.write_text(_REMOTE_CACHE_UNPACK_PY, encoding="utf-8", newline="\n")

        subprocess.run(
            [
                "ssh",
                "-o",
                "ConnectTimeout=4",
                "-o",
                "BatchMode=yes",
                alias,
                f'if not exist "{X13_BASE_DIR}\\cache_staging" mkdir "{X13_BASE_DIR}\\cache_staging"',
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
        )
        for local_p in (packed["tar_path"], packed["manifest_path"], unpack_local):
            subprocess.run(
                [
                    "scp",
                    "-o",
                    "ConnectTimeout=6",
                    "-o",
                    "BatchMode=yes",
                    str(local_p),
                    f"{alias}:C:/NaqexResearch/cache_staging/{local_p.name}",
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=300,
            )

        unpack_cmd = f'"{X13_REMOTE_PYTHON}" "{X13_BASE_DIR}\\cache_staging\\unpack_cache.py" "{X13_BASE_DIR}"'
        proc = subprocess.run(
            ["ssh", "-o", "ConnectTimeout=6", "-o", "BatchMode=yes", alias, unpack_cmd],
            check=True,
            capture_output=True,
            text=True,
            timeout=300,
        )
        remote_receipt = json.loads((proc.stdout or "{}").strip())
        summary["archive_sha256"] = packed["manifest"]["archive_sha256"]
        summary["archive_bytes"] = packed["manifest"]["archive_bytes"]
        summary["remote_verify"] = remote_receipt
    return summary


_REMOTE_M1_SHA_INVENTORY_PY = r'''"""Read-only SHA-256 inventory of Dev M1 Parquets + manifest.json on <X13_WORKER>."""
from __future__ import annotations
import hashlib, json, pathlib, sys

def _sha(p: pathlib.Path) -> str:
    with p.open("rb") as fh:
        return hashlib.file_digest(fh, "sha256").hexdigest()

def main() -> int:
    base = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(r"C:\NaqexResearch")
    cache_root = base / ".runtime" / "hot-m1-cache"
    hashes: dict[str, str] = {}
    if cache_root.is_dir():
        mpath = cache_root / "manifest.json"
        if mpath.is_file():
            hashes[".runtime/hot-m1-cache/manifest.json"] = _sha(mpath)
        for p in sorted(cache_root.rglob("*.parquet")):
            if p.is_file():
                rel = p.relative_to(base).as_posix()
                hashes[rel] = _sha(p)
    print(json.dumps({"ok": True, "hashes": hashes}))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
'''


def collect_m1_parquet_sync_plan(
    *,
    root: Path = ROOT,
    cache_dir: Path | None = None,
    assets: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Collect fail-closed Dev-only M1 Parquet + manifest.json sync entries with verified local SHA-256."""
    m1_cache = Path(cache_dir) if cache_dir is not None else (root / ".runtime/hot-m1-cache")
    manifest_path = m1_cache / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Hot M1 cache manifest missing: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    if not isinstance(manifest, dict) or not isinstance(manifest.get("assets"), dict):
        raise ValueError(f"Invalid hot M1 cache manifest: {manifest_path}")
    if isinstance(manifest.get("holdout_rows"), bool) or manifest.get("holdout_rows") != 0:
        raise ValueError(
            f"HOLDOUT_OR_SECRET_AIRGAP_VIOLATION: manifest holdout_rows={manifest.get('holdout_rows')!r} != 0"
        )

    all_assets_map: dict[str, Any] = manifest["assets"]
    target_assets = (
        [str(a).strip().upper() for a in assets] if assets is not None else sorted(all_assets_map.keys())
    )
    entries: list[dict[str, Any]] = []
    seen_rels: set[str] = set()

    for asset_u in target_assets:
        assert_dev_only_path(asset_u)
        if asset_u not in all_assets_map:
            raise KeyError(f"Asset {asset_u!r} not found in hot M1 cache manifest")
        am = all_assets_map[asset_u]
        rel_dir = str(am.get("dir", "")).strip()
        assert_dev_only_path(rel_dir)
        asset_folder = (m1_cache / rel_dir).resolve()
        try:
            asset_folder.relative_to(m1_cache.resolve())
        except ValueError as exc:
            raise ValueError(f"Unsafe asset dir escapes cache root: {rel_dir!r}") from exc

        # Scan asset folder for any stray 2025/2026/holdout files fail-closed
        if asset_folder.is_dir():
            for stray in sorted(asset_folder.rglob("*")):
                if stray.is_file():
                    assert_dev_only_path(stray.relative_to(m1_cache).as_posix())

        years_map = am.get("years")
        if not isinstance(years_map, dict) or not years_map:
            raise ValueError(f"Missing years map for asset {asset_u}")

        for yk, ym in sorted(years_map.items()):
            assert_dev_only_path(yk)
            if int(yk) >= 2025 or int(yk) < 2018:
                raise ValueError(
                    f"HOLDOUT_OR_SECRET_AIRGAP_VIOLATION: forbidden year {yk!r} for asset {asset_u}"
                )
            fname = str(ym.get("parquet", "")).strip()
            assert_dev_only_path(fname)
            pfile = (asset_folder / fname).resolve()
            try:
                pfile.relative_to(asset_folder)
            except ValueError as exc:
                raise ValueError(f"Parquet escapes asset folder: {fname!r}") from exc
            if not pfile.is_file():
                raise FileNotFoundError(f"Missing sealed parquet for {asset_u} {yk}: {pfile}")
            rel_posix = f".runtime/hot-m1-cache/{rel_dir}/{fname}"
            assert_dev_only_path(rel_posix)
            actual_sha = _sha256_file(pfile)
            exp_sha = ym.get("parquet_sha256")
            if isinstance(exp_sha, str) and exp_sha and actual_sha != exp_sha:
                raise ValueError(
                    f"Local M1 parquet SHA-256 mismatch for {asset_u} {yk}: expected={exp_sha} got={actual_sha}"
                )
            if rel_posix not in seen_rels:
                seen_rels.add(rel_posix)
                entries.append(
                    {
                        "rel_path": rel_posix,
                        "local_path": pfile,
                        "sha256": actual_sha,
                        "bytes": int(pfile.stat().st_size),
                        "asset": asset_u,
                    }
                )

    # Always append manifest.json LAST so remote manifest never references missing parquets
    man_rel = ".runtime/hot-m1-cache/manifest.json"
    assert_dev_only_path(man_rel)
    entries.append(
        {
            "rel_path": man_rel,
            "local_path": manifest_path,
            "sha256": _sha256_file(manifest_path),
            "bytes": int(manifest_path.stat().st_size),
            "asset": "__MANIFEST__",
        }
    )

    return {
        "cache_dir": m1_cache,
        "assets": target_assets,
        "entries": entries,
        "total_files": len(entries),
        "total_bytes": sum(int(e["bytes"]) for e in entries),
    }


def _query_x13_m1_hashes(alias: str) -> dict[str, str]:
    safe_alias = _validate_host(alias)
    with tempfile.TemporaryDirectory(prefix="x13_m1_inv_") as td:
        inv_local = Path(td) / "m1_sha_inventory.py"
        inv_local.write_text(_REMOTE_M1_SHA_INVENTORY_PY, encoding="utf-8", newline="\n")
        subprocess.run(
            [
                "ssh",
                "-o",
                "ConnectTimeout=4",
                "-o",
                "BatchMode=yes",
                safe_alias,
                f'if not exist "{X13_BASE_DIR}\\cache_staging" mkdir "{X13_BASE_DIR}\\cache_staging"',
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
        )
        subprocess.run(
            [
                "scp",
                "-o",
                "ConnectTimeout=6",
                "-o",
                "BatchMode=yes",
                str(inv_local),
                f"{safe_alias}:C:/NaqexResearch/cache_staging/m1_sha_inventory.py",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        cmd = f'"{X13_REMOTE_PYTHON}" "{X13_BASE_DIR}\\cache_staging\\m1_sha_inventory.py" "{X13_BASE_DIR}"'
        proc = subprocess.run(
            ["ssh", "-o", "ConnectTimeout=6", "-o", "BatchMode=yes", safe_alias, cmd],
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
        payload = json.loads((proc.stdout or "{}").strip())
        hashes = payload.get("hashes")
        if not isinstance(hashes, dict):
            raise RuntimeError(f"Malformed remote M1 inventory JSON: {payload!r}")
        return {str(k): str(v) for k, v in hashes.items()}


def _scp_upload_m1_file(alias: str, local_path: Path, rel_posix: str) -> None:
    safe_alias = _validate_host(alias)
    assert_dev_only_path(rel_posix)
    remote_rel_win = rel_posix.replace("/", "\\")
    remote_parent_win = str(Path(remote_rel_win).parent)
    subprocess.run(
        [
            "ssh",
            "-o",
            "ConnectTimeout=4",
            "-o",
            "BatchMode=yes",
            safe_alias,
            f'if not exist "{X13_BASE_DIR}\\{remote_parent_win}" mkdir "{X13_BASE_DIR}\\{remote_parent_win}"',
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    subprocess.run(
        [
            "scp",
            "-o",
            "ConnectTimeout=6",
            "-o",
            "BatchMode=yes",
            str(local_path),
            f"{safe_alias}:C:/NaqexResearch/{rel_posix}",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=300,
    )


def sync_m1_parquets_incremental(
    *,
    lan_only: bool = False,
    dry_run: bool = False,
    host: str | None = None,
    root: Path = ROOT,
    cache_dir: Path | None = None,
    assets: Sequence[str] | None = None,
    query_remote_hashes_fn: Callable[[str], dict[str, str]] | None = None,
    upload_fn: Callable[[str, Path, str], None] | None = None,
) -> dict[str, Any]:
    """Incrementally sync Dev-only M1 Parquets + manifest.json to `<X13_WORKER>` by per-file SHA-256.

    - Fails closed immediately on any local `2025`/`2026`/`holdout` token or SHA mismatch.
    - Skips files whose remote SHA-256 already matches local SHA-256 (0 redundant transfer).
    - Supports Silent Automatic Fallback (`fallback_used=True`) if `<X13_WORKER>` is unreachable
      or drops mid-transfer so callers can continue cleanly on `<DEV_PC>`.
    """
    # Step 1: Fail-closed local air-gap & SHA audit BEFORE probing X13
    plan = collect_m1_parquet_sync_plan(root=root, cache_dir=cache_dir, assets=assets)
    entries: list[dict[str, Any]] = plan["entries"]

    x13 = probe_x13_worker(hosts=(host,) if host else X13_HOSTS, lan_only=lan_only)
    if not x13["reachable"]:
        fb_reason = "; ".join(x13.get("ineligible_reasons") or ["x13_unreachable"])
        return {
            "schema": "naqex-sync-m1-parquets-v1",
            "ok": True,
            "status": "FALLBACK_DEV_PC_LOCAL",
            "fallback_used": True,
            "fallback_reason": fb_reason,
            "dry_run": dry_run,
            "assets_requested": plan["assets"],
            "total_files": plan["total_files"],
            "uploaded_files": [],
            "skipped_files": [],
            "bytes_uploaded": 0,
            "bytes_skipped": 0,
            "holdout_airgap_enforced": True,
            "forbidden_files": 0,
            "order_send_count": ORDER_SEND_COUNT,
            "x13_worker": x13,
        }

    if _strict_int(x13.get("forbidden_files")) not in (None, 0):
        return {
            "schema": "naqex-sync-m1-parquets-v1",
            "ok": False,
            "status": "X13_FORBIDDEN_FILES_ABORT",
            "fallback_used": False,
            "fallback_reason": None,
            "dry_run": dry_run,
            "holdout_airgap_enforced": True,
            "forbidden_files": x13.get("forbidden_files"),
            "order_send_count": ORDER_SEND_COUNT,
            "x13_worker": x13,
        }

    alias = _validate_host(str(x13["ssh_alias"]))
    querier = query_remote_hashes_fn or _query_x13_m1_hashes
    uploader = upload_fn or _scp_upload_m1_file

    try:
        remote_hashes = querier(alias)
    except Exception as exc:
        return {
            "schema": "naqex-sync-m1-parquets-v1",
            "ok": True,
            "status": "FALLBACK_DEV_PC_LOCAL",
            "fallback_used": True,
            "fallback_reason": f"x13_inventory_fallback: {exc}",
            "dry_run": dry_run,
            "ssh_alias": alias,
            "assets_requested": plan["assets"],
            "total_files": plan["total_files"],
            "uploaded_files": [],
            "skipped_files": [],
            "bytes_uploaded": 0,
            "bytes_skipped": 0,
            "holdout_airgap_enforced": True,
            "forbidden_files": 0,
            "order_send_count": ORDER_SEND_COUNT,
            "x13_worker": x13,
        }

    to_upload: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for entry in entries:
        rel = entry["rel_path"]
        assert_dev_only_path(rel)
        if remote_hashes.get(rel) == entry["sha256"]:
            skipped.append(entry)
        else:
            to_upload.append(entry)

    if dry_run:
        return {
            "schema": "naqex-sync-m1-parquets-v1",
            "ok": True,
            "status": "DRY_RUN_READY",
            "fallback_used": False,
            "fallback_reason": None,
            "dry_run": True,
            "ssh_alias": alias,
            "assets_requested": plan["assets"],
            "total_files": plan["total_files"],
            "planned_upload_files": [e["rel_path"] for e in to_upload],
            "uploaded_files": [],
            "skipped_files": [e["rel_path"] for e in skipped],
            "bytes_to_upload": sum(int(e["bytes"]) for e in to_upload),
            "bytes_uploaded": 0,
            "bytes_skipped": sum(int(e["bytes"]) for e in skipped),
            "holdout_airgap_enforced": True,
            "forbidden_files": 0,
            "order_send_count": ORDER_SEND_COUNT,
        }

    uploaded_rels: list[str] = []
    bytes_uploaded = 0
    try:
        for entry in to_upload:
            rel = entry["rel_path"]
            assert_dev_only_path(rel)
            uploader(alias, entry["local_path"], rel)
            uploaded_rels.append(rel)
            bytes_uploaded += int(entry["bytes"])

        # Post-upload remote SHA-256 verification when any file was transferred
        verified_remote = True
        if to_upload:
            post_hashes = querier(alias)
            for entry in to_upload:
                rel = entry["rel_path"]
                if post_hashes.get(rel) != entry["sha256"]:
                    raise RuntimeError(
                        f"Remote SHA-256 verification failed after upload for {rel}: "
                        f"expected={entry['sha256']} got={post_hashes.get(rel)!r}"
                    )
    except Exception as exc:
        return {
            "schema": "naqex-sync-m1-parquets-v1",
            "ok": True,
            "status": "FALLBACK_DEV_PC_LOCAL",
            "fallback_used": True,
            "fallback_reason": f"x13_upload_fallback: {exc}",
            "dry_run": False,
            "ssh_alias": alias,
            "assets_requested": plan["assets"],
            "total_files": plan["total_files"],
            "uploaded_files": uploaded_rels,
            "skipped_files": [e["rel_path"] for e in skipped],
            "bytes_uploaded": bytes_uploaded,
            "bytes_skipped": sum(int(e["bytes"]) for e in skipped),
            "holdout_airgap_enforced": True,
            "forbidden_files": 0,
            "order_send_count": ORDER_SEND_COUNT,
        }

    return {
        "schema": "naqex-sync-m1-parquets-v1",
        "ok": True,
        "status": "SYNCED_VERIFIED" if to_upload else "ALREADY_UP_TO_DATE",
        "fallback_used": False,
        "fallback_reason": None,
        "dry_run": False,
        "ssh_alias": alias,
        "assets_requested": plan["assets"],
        "total_files": plan["total_files"],
        "uploaded_files": uploaded_rels,
        "skipped_files": [e["rel_path"] for e in skipped],
        "bytes_uploaded": bytes_uploaded,
        "bytes_skipped": sum(int(e["bytes"]) for e in skipped),
        "remote_sha_verified": verified_remote,
        "holdout_airgap_enforced": True,
        "forbidden_files": 0,
        "order_send_count": ORDER_SEND_COUNT,
    }


# ==============================================================================
# 5. CLI ENTRYPOINT (probe | route | dispatch | sync-dev-cache | sync-m1-parquets | pull-results)
# ==============================================================================

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Naqex 3-Node Compute Orchestrator (<DEV_PC> + <X13_WORKER>).")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_probe = sub.add_parser("probe")
    p_probe.add_argument("--lan-only", action="store_true")
    p_probe.add_argument("--strict-ntp", action="store_true")

    p_route = sub.add_parser("route")
    p_route.add_argument("--est-minutes", type=float, default=15.0)
    p_route.add_argument("--ram-gb", type=float, default=4.0)
    p_route.add_argument("--shardable", action="store_true")
    p_route.add_argument("--shards", type=int, default=10)
    p_route.add_argument("--touches-holdout", action="store_true")
    p_route.add_argument("--touches-vps", action="store_true")
    p_route.add_argument("--requires-admin", action="store_true")
    p_route.add_argument("--needs-gpu", action="store_true")
    p_route.add_argument("--strict-ntp", action="store_true")
    p_route.add_argument("--lan-only", action="store_true")
    p_route.add_argument("--allow-mode-a-assist", action="store_true")
    p_route.add_argument("--force-mode-b", action="store_true")
    p_route.add_argument("--owner-approved-long-run", action="store_true")

    p_disp = sub.add_parser("dispatch")
    p_disp.add_argument("--job-id", required=True)
    p_disp.add_argument("--entry", type=Path, required=True)
    p_disp.add_argument("--est-minutes", type=float, default=15.0)
    p_disp.add_argument("--ram-gb", type=float, default=4.0)
    p_disp.add_argument("--shardable", action="store_true")
    p_disp.add_argument("--shards", type=int, default=10)
    p_disp.add_argument("--touches-holdout", action="store_true")
    p_disp.add_argument("--touches-vps", action="store_true")
    p_disp.add_argument("--requires-admin", action="store_true")
    p_disp.add_argument("--needs-gpu", action="store_true")
    p_disp.add_argument("--strict-ntp", action="store_true")
    p_disp.add_argument("--allow-ntp-drift", action="store_true")
    p_disp.add_argument("--force-x13", action="store_true")
    p_disp.add_argument("--allow-mode-a-assist", action="store_true")
    p_disp.add_argument("--force-mode-b", action="store_true")
    p_disp.add_argument("--owner-approved-long-run", action="store_true")
    p_disp.add_argument("--lease-wait-sec", type=float, default=0.0)
    p_disp.add_argument("--lan-only", action="store_true")
    p_disp.add_argument("--dry-run", action="store_true")
    p_disp.add_argument("--dest", type=Path, default=None)

    p_sync = sub.add_parser("sync-dev-cache")
    p_sync.add_argument("--lan-only", action="store_true")
    p_sync.add_argument("--dry-run", action="store_true")
    p_sync.add_argument("--verify-only", action="store_true")
    p_sync.add_argument("--host", default=None)

    p_sync_m1 = sub.add_parser("sync-m1-parquets")
    p_sync_m1.add_argument("--lan-only", action="store_true")
    p_sync_m1.add_argument("--dry-run", action="store_true")
    p_sync_m1.add_argument("--host", default=None)
    p_sync_m1.add_argument("--assets", nargs="*", default=None)

    p_pull = sub.add_parser("pull-results")
    p_pull.add_argument("--job-id", required=True)
    p_pull.add_argument("--dest", type=Path, required=True)
    p_pull.add_argument("--host", default=X13_HOSTS[0])
    p_pull.add_argument("--cleanup-remote", action="store_true")

    args = ap.parse_args(argv)
    if args.cmd == "probe":
        dev_pc = probe_dev_pc()
        x13 = probe_x13_worker(lan_only=args.lan_only, strict_ntp=args.strict_ntp)
        strict_ok = _strict_ntp_passed(dev_pc, x13)
        out = {
            "schema": "naqex-compute-router-v1",
            "owner_policy_ref": "grill_me_q1_locked",
            "checked_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "order_send_count": ORDER_SEND_COUNT,
            "dev_pc": dev_pc,
            "x13_worker": x13,
            "guardrails": {
                "holdout_airgap_enforced": True,
                "vps_compute_forbidden": True,
                "strict_ntp_passed": strict_ok,
            },
        }
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0

    if args.cmd == "route":
        dev_pc = probe_dev_pc()
        x13 = probe_x13_worker(lan_only=args.lan_only, strict_ntp=args.strict_ntp)
        dec = decide_route(
            dev_pc,
            x13,
            est_minutes=args.est_minutes,
            ram_gb=args.ram_gb,
            shardable=args.shardable,
            shards=args.shards,
            touches_holdout=args.touches_holdout,
            touches_vps=args.touches_vps,
            requires_admin=args.requires_admin,
            needs_gpu=args.needs_gpu,
            strict_ntp=args.strict_ntp,
            allow_mode_a_assist=args.allow_mode_a_assist,
            force_mode_b=args.force_mode_b,
            owner_approved_long_run=args.owner_approved_long_run,
        )
        out = {
            "schema": "naqex-compute-router-v1",
            "owner_policy_ref": "grill_me_q1_locked",
            "checked_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "order_send_count": ORDER_SEND_COUNT,
            "dev_pc": dev_pc,
            "x13_worker": x13,
            "decision": dec,
            "guardrails": {
                "holdout_airgap_enforced": True,
                "vps_compute_forbidden": True,
                "strict_ntp_passed": _strict_ntp_passed(dev_pc, x13),
            },
        }
        print(json.dumps(out, indent=2, ensure_ascii=False))
        blocked = dec["target"] == "BLOCKED_NEEDS_APPROVAL" or bool(dec.get("ask_owner_required"))
        return 2 if blocked else 0

    if args.cmd == "dispatch":
        res = dispatch_job(
            args.job_id,
            args.entry,
            est_minutes=args.est_minutes,
            ram_gb=args.ram_gb,
            shardable=args.shardable,
            shards=args.shards,
            touches_holdout=args.touches_holdout,
            touches_vps=args.touches_vps,
            requires_admin=args.requires_admin,
            needs_gpu=args.needs_gpu,
            strict_ntp=args.strict_ntp,
            allow_ntp_drift=args.allow_ntp_drift,
            force_x13=args.force_x13,
            allow_mode_a_assist=args.allow_mode_a_assist,
            force_mode_b=args.force_mode_b,
            owner_approved_long_run=args.owner_approved_long_run,
            lan_only=args.lan_only,
            dry_run=args.dry_run,
            dest_dir=args.dest,
            lease_max_wait_sec=args.lease_wait_sec,
        )
        print(json.dumps(res, indent=2, ensure_ascii=False))
        dec = res["decision"]
        if dec["target"] == "BLOCKED_NEEDS_APPROVAL" or bool(dec.get("ask_owner_required")):
            return 2
        return 0 if res.get("ok") else 1

    if args.cmd == "sync-dev-cache":
        res = sync_dev_cache(lan_only=args.lan_only, dry_run=args.dry_run, verify_only=args.verify_only, host=args.host)
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0 if res.get("ok") else 1

    if args.cmd == "sync-m1-parquets":
        res = sync_m1_parquets_incremental(
            lan_only=args.lan_only,
            dry_run=args.dry_run,
            host=args.host,
            assets=args.assets,
        )
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0 if res.get("ok") else 1

    if args.cmd == "pull-results":
        res = pull_results(args.job_id, args.dest, host=args.host, cleanup_remote=args.cleanup_remote)
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0 if res.get("ok") else 1

    return 1


if __name__ == "__main__":
    raise SystemExit(main())

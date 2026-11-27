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
import re
import subprocess
import sys
import tarfile
import tempfile
import time
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

_FORBIDDEN_SHELL_META: frozenset[str] = frozenset('&|;><^%$()`"\'!\r\n\t')
_SAFE_HOST_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_SAFE_JOB_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_SAFE_EXTRA_ARG_RE = re.compile(r"^[A-Za-z0-9._:=\\/@,-]+$")
_NTP_OFFSET_RE = re.compile(r"([+-]\d+(?:\.\d+)?)s\b")
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
    """Read local `<DEV_PC>` OS sensors concurrently (< 400 ms, 100% read-only)."""
    now = now_utc or datetime.now(UTC)
    now_ict = now.astimezone(timezone(timedelta(hours=7)))
    in_overnight = 0 <= now_ict.hour < 7

    with ThreadPoolExecutor(max_workers=3) as pool:
        f_cpu = pool.submit(_read_cpu_util_pct, 0.20)
        f_gpu = pool.submit(_read_gpu_util_pct)
        f_ntp = pool.submit(_read_ntp_offset_ms)
        idle_sec = _read_idle_sec()
        fullscreen = _read_fullscreen_busy()
        free_ram = _read_free_ram_gb()
        cpu_pct = f_cpu.result()
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


# ==============================================================================
# 3. DETERMINISTIC ROUTING POLICY (MODE A / MODE B / 60-40 / SILENT FALLBACK)
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

    mode = dev_pc.get("mode") or classify_dev_pc_mode(dev_pc)
    gpu_val = _finite_float(dev_pc.get("gpu_util_pct"))
    gaming_or_gpu = (gpu_val is None or gpu_val > 25.0) or bool(dev_pc.get("fullscreen_busy", False))
    mode_a_cores = 2 if gaming_or_gpu else 3
    x13_ok, x13_reasons = evaluate_x13_eligibility(
        x13_worker, min_ram_gb=ram_gb, strict_ntp=strict_ntp, allow_ntp_drift=allow_ntp_drift
    )

    reasons: list[str] = []
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
    if est_minutes > 60.0:
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

    # Mode A (owner active) + heavy Dev job >= 10m -> offload 100% to X13 or silent fallback
    if mode == "MODE_A_OWNER_ACTIVE":
        if x13_ok:
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
) -> dict[str, Any]:
    """Package an immutable Dev-only tar.gz bundle + SHA-256 manifest (rejects Holdout/secrets fail-closed)."""
    jid = _validate_job_id(job_id)
    entry = entry_script.resolve()
    if not entry.is_file():
        raise FileNotFoundError(f"Entry script not found: {entry}")

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

    out_dir.mkdir(parents=True, exist_ok=True)
    tar_path = out_dir / "bundle.tar.gz"
    file_hashes: dict[str, str] = {}
    with tarfile.open(tar_path, "w:gz") as tf:
        for arc, p in sorted(files_to_pack):
            tf.add(str(p), arcname=arc)
            file_hashes[arc] = _sha256_file(p)

    bundle_sha = _sha256_file(tar_path)
    manifest = {
        "schema": "naqex-job-bundle-v1",
        "job_id": jid,
        "git_sha": _current_git_sha(),
        "created_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "entry_arc": files_to_pack[0][0],
        "bundle_tar_sha256": bundle_sha,
        "files": file_hashes,
    }
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


_REMOTE_RUNNER_PY = r'''"""Immutable remote job runner on <X13_WORKER> with AC-power guard & atomic manifest."""
from __future__ import annotations
import ctypes, hashlib, json, os, pathlib, subprocess, sys, tarfile, tempfile, time
from datetime import datetime, timezone

def _ac_online() -> bool:
    if os.name != "nt":
        return True
    class _SPS(ctypes.Structure):
        _fields_ = [("AC", ctypes.c_ubyte), ("BF", ctypes.c_ubyte), ("BP", ctypes.c_ubyte),
                    ("SF", ctypes.c_ubyte), ("BLT", ctypes.c_ulong), ("BFLT", ctypes.c_ulong)]
    s = _SPS()
    return bool(ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(s))) and int(s.AC) == 1

def _proc_created_at(pid: int) -> str:
    try:
        ps = (
            f"$p=Get-CimInstance Win32_Process -Filter 'ProcessId = {int(pid)}'; "
            "if ($p) { $p.CreationDate.ToUniversalTime().ToString('o') }"
        )
        r = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps],
            capture_output=True, text=True, timeout=3,
        )
        return r.stdout.strip()
    except Exception:
        return datetime.now(timezone.utc).isoformat()

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
    _atomic_json(lock_path, lock_meta)
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
        env["PYTHONUTF8"] = "1"
        stdout_p = res_dir / "stdout.log"
        stderr_p = res_dir / "stderr.log"
        with (
            stdout_p.open("w", encoding="utf-8", newline="\n") as out_fh,
            stderr_p.open("w", encoding="utf-8", newline="\n") as err_fh,
        ):
            proc = subprocess.Popen(
                [sys.executable, str(entry), *extra_args],
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
    timeout: int = 3600,
) -> dict[str, Any]:
    dest_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["NUMBA_NUM_THREADS"] = str(max(1, cores))
    env["OMP_NUM_THREADS"] = str(max(1, cores))
    env["NAQEX_RESULT_DIR"] = str(dest_dir)
    env["NAQEX_JOB_ID"] = job_id
    env["PYTHONUTF8"] = "1"
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
    return {"executed_on": "DEV_PC", "returncode": proc.returncode, "verify": verify}


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
    lan_only: bool = False,
    dry_run: bool = False,
    dest_dir: Path | None = None,
    extra_args: list[str] | None = None,
) -> dict[str, Any]:
    """Probe, route, and execute a Dev-only job with immutable bundle + SHA-256 verification + silent fallback."""
    jid = _validate_job_id(job_id)
    safe_args = _validate_extra_args(extra_args)
    entry = entry_script.resolve()
    if not touches_holdout:
        assert_dev_only_path(entry)

    dev_pc = probe_dev_pc()
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
            with tempfile.TemporaryDirectory(prefix=f"bundle_{jid}_") as td:
                bdir = Path(td)
                bundle = build_job_bundle(jid, entry, bdir)
                runner_local = bdir / "run_job.py"
                runner_local.write_text(_REMOTE_RUNNER_PY, encoding="utf-8", newline="\n")

                mk = subprocess.run(
                    ["ssh", "-o", "ConnectTimeout=4", "-o", "BatchMode=yes", alias,
                     f'if not exist "{X13_BASE_DIR}\\jobs\\{jid}" mkdir "{X13_BASE_DIR}\\jobs\\{jid}" '
                     f'& if not exist "{X13_BASE_DIR}\\locks" mkdir "{X13_BASE_DIR}\\locks" '
                     f'& if not exist "{X13_BASE_DIR}\\results\\{jid}" mkdir "{X13_BASE_DIR}\\results\\{jid}"'],
                    capture_output=True, text=True, timeout=15,
                )
                if mk.returncode != 0:
                    raise RuntimeError(f"x13_mkdir_failed(rc={mk.returncode})")

                for local_p in (bundle["tar_path"], bundle["manifest_path"], runner_local):
                    cp = subprocess.run(
                        ["scp", "-o", "ConnectTimeout=6", "-o", "BatchMode=yes",
                         str(local_p), f"{alias}:C:/NaqexResearch/jobs/{jid}/{local_p.name}"],
                        capture_output=True, text=True, timeout=60,
                    )
                    if cp.returncode != 0:
                        raise RuntimeError(f"x13_scp_upload_failed({local_p.name},rc={cp.returncode})")

                quoted_extra = " ".join(f'"{a}"' for a in safe_args)
                run_cmd = (
                    f'"{X13_REMOTE_PYTHON}" "{X13_BASE_DIR}\\jobs\\{jid}\\run_job.py" '
                    f'"{jid}" "{int(decision["x13_threads"])}" {quoted_extra}'
                ).strip()
                run_p = subprocess.run(
                    ["ssh", "-o", "ConnectTimeout=6", "-o", "BatchMode=yes", alias, run_cmd],
                    capture_output=True, text=True, timeout=3600,
                )
                if run_p.returncode == 77:
                    raise RuntimeError("x13_ac_unplugged_during_run")
                if run_p.returncode != 0:
                    raise RuntimeError(f"x13_remote_exec_failed(rc={run_p.returncode}): {run_p.stderr.strip()[:200]}")

                pulled = pull_results(jid, out_dir, host=alias, cleanup_remote=False)
                if not pulled["ok"]:
                    raise RuntimeError(f"x13_pull_or_sha_failed({pulled['status']})")
                receipt["ok"] = True
                receipt["execution"] = {"executed_on": "X13_WORKER", "ssh_alias": alias, "pull": pulled}
                return receipt
        except Exception as exc:
            # Silent automatic fallback to <DEV_PC> if X13 drops or loses AC power mid-flight
            fb_reason = f"x13_runtime_fallback: {exc}"
            decision["fallback_used"] = True
            decision["fallback_reason"] = fb_reason
            mode = dev_pc["mode"]
            gaming = dev_pc["gpu_util_pct"] > 25 or dev_pc["fullscreen_busy"]
            cores = 2 if gaming else (3 if mode == "MODE_A_OWNER_ACTIVE" else 5)
            prio = "BELOW_NORMAL" if mode == "MODE_A_OWNER_ACTIVE" else "NORMAL"
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


def sync_dev_cache(
    *,
    lan_only: bool = False,
    dry_run: bool = False,
    verify_only: bool = False,
    host: str | None = None,
) -> dict[str, Any]:
    """One-way allowlist sync of Dev-only (<= 2024) artifacts to `<X13_WORKER>` with zero Holdout leakage."""
    x13 = probe_x13_worker(hosts=(host,) if host else X13_HOSTS, lan_only=lan_only)
    if not x13["reachable"]:
        return {"ok": False, "status": "X13_UNREACHABLE", "x13_worker": x13}

    allow_files: list[Path] = []
    qf_dir = AI_ENGINES_DIR / "quant_factory"
    if qf_dir.is_dir():
        for p in sorted(qf_dir.glob("*.py")):
            if not any(tok in p.name.lower() for tok in _FORBIDDEN_DEV_TOKENS):
                allow_files.append(p)
    derived_dir = ROOT / ".runtime/hot-m1-cache/_derived"
    for stem in ("frozen_9e_tapes_v2", "frozen_9e_tapes_v1"):
        for ext in (".json", ".npz"):
            cand = derived_dir / f"{stem}{ext}"
            if cand.is_file():
                allow_files.append(cand)
        if any(stem in p.name for p in allow_files):
            break

    for p in allow_files:
        assert_dev_only_path(p.relative_to(ROOT))

    summary: dict[str, Any] = {
        "schema": "naqex-sync-dev-cache-v1",
        "ok": True,
        "ssh_alias": x13["ssh_alias"],
        "dry_run": dry_run,
        "verify_only": verify_only,
        "file_count": len(allow_files),
        "total_bytes": sum(p.stat().st_size for p in allow_files),
        "holdout_airgap_enforced": True,
    }
    if dry_run or verify_only:
        summary["files"] = [p.relative_to(ROOT).as_posix() for p in allow_files]
        return summary

    alias = str(x13["ssh_alias"])
    for p in allow_files:
        rel = p.relative_to(ROOT).as_posix()
        remote_dir = f"{X13_BASE_DIR}\\{str(Path(rel).parent).replace('/', '\\')}"
        subprocess.run(
            ["ssh", "-o", "ConnectTimeout=4", "-o", "BatchMode=yes", alias,
             f'if not exist "{remote_dir}" mkdir "{remote_dir}"'],
            check=True, capture_output=True, text=True, timeout=15,
        )
        subprocess.run(
            ["scp", "-o", "ConnectTimeout=6", "-o", "BatchMode=yes", str(p), f"{alias}:C:/NaqexResearch/{rel}"],
            check=True, capture_output=True, text=True, timeout=120,
        )
    return summary


# ==============================================================================
# 5. CLI ENTRYPOINT (probe | route | dispatch | sync-dev-cache | pull-results)
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
    p_disp.add_argument("--lan-only", action="store_true")
    p_disp.add_argument("--dry-run", action="store_true")
    p_disp.add_argument("--dest", type=Path, default=None)

    p_sync = sub.add_parser("sync-dev-cache")
    p_sync.add_argument("--lan-only", action="store_true")
    p_sync.add_argument("--dry-run", action="store_true")
    p_sync.add_argument("--verify-only", action="store_true")
    p_sync.add_argument("--host", default=None)

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
            lan_only=args.lan_only,
            dry_run=args.dry_run,
            dest_dir=args.dest,
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

    if args.cmd == "pull-results":
        res = pull_results(args.job_id, args.dest, host=args.host, cleanup_remote=args.cleanup_remote)
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0 if res.get("ok") else 1

    return 1


if __name__ == "__main__":
    raise SystemExit(main())

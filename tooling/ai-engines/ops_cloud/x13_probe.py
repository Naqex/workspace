"""Standalone lightweight read-only health & AC-power probe for <X13_WORKER> (OrderSend = 0).

Deployed to `C:\\NaqexResearch\\x13_probe.py` on <X13_WORKER> and invoked over SSH in < 1.5s.
Checks AC power (`GetSystemPowerStatus().ACLineStatus == 1` & `Win32_Battery.BatteryStatus != 1`),
CPU%, free RAM GB, C: free GB, NTP offset ms, PID+CreationDate anti-PID-reuse active lock,
and `forbidden_files == 0` (zero Holdout/2025+/accounts.dat).
"""
from __future__ import annotations

import argparse
import ctypes
import json
import os
import re
import shutil
import subprocess
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ORDER_SEND_CAPABLE: bool = False
ORDER_SEND_COUNT: int = 0

DEFAULT_BASE_DIR = Path(r"C:\NaqexResearch")
_FORBIDDEN_TOKENS: tuple[str, ...] = (
    "holdout",
    "2025",
    "2026",
    "accounts.dat",
    "native_ftmo_holdout_lock",
    "id_ed25519",
    "private_vault",
    ".ssh",
)
_SKIP_DIRS: frozenset[str] = frozenset({".venv", "__pycache__", ".git"})
_NTP_OFFSET_RE = re.compile(r"([+-]\d+(?:\.\d+)?)s\b")


class _SystemPowerStatus(ctypes.Structure):
    _fields_ = [
        ("ACLineStatus", ctypes.c_ubyte),
        ("BatteryFlag", ctypes.c_ubyte),
        ("BatteryLifePercent", ctypes.c_ubyte),
        ("SystemStatusFlag", ctypes.c_ubyte),
        ("BatteryLifeTime", ctypes.c_ulong),
        ("BatteryFullLifeTime", ctypes.c_ulong),
    ]


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


def _ft_to_int(ft: _FileTime) -> int:
    return (int(ft.dwHighDateTime) << 32) | int(ft.dwLowDateTime)


def read_power_status() -> dict[str, Any]:
    if os.name != "nt":
        return {"ac_line_status": 0, "battery_pct": None}
    st = _SystemPowerStatus()
    if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(st)):
        return {"ac_line_status": 255, "battery_pct": None}
    pct = None if int(st.BatteryLifePercent) == 255 else int(st.BatteryLifePercent)
    return {"ac_line_status": int(st.ACLineStatus), "battery_pct": pct}


def read_battery_status_code() -> int | None:
    """Query Win32_Battery.BatteryStatus (1 = Discharging -> must reject; 2/6..9 = AC/Charging)."""
    if os.name != "nt":
        return None
    try:
        proc = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                "$b=Get-CimInstance Win32_Battery | Select-Object -First 1; if ($b) { [int]$b.BatteryStatus }",
            ],
            capture_output=True,
            text=True,
            timeout=1.8,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        raw = proc.stdout.strip()
        return int(raw) if raw.isdigit() else None
    except Exception:
        return None


def read_cpu_util_pct(sample_sec: float = 0.15) -> float:
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
    di = _ft_to_int(i2) - _ft_to_int(i1)
    dk = _ft_to_int(k2) - _ft_to_int(k1)
    du = _ft_to_int(u2) - _ft_to_int(u1)
    tot = dk + du
    if tot <= 0:
        return 0.0
    busy = max(0.0, float(tot - di) / float(tot))
    return round(min(100.0, busy * 100.0), 1)


def read_free_ram_gb() -> float:
    if os.name != "nt":
        return 0.0
    ms = _MemoryStatusEx()
    ms.dwLength = ctypes.sizeof(_MemoryStatusEx)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(ms)):
        return 0.0
    return round(float(ms.ullAvailPhys) / float(1024 ** 3), 2)


def read_ntp_offset_ms(servers: tuple[str, ...] = ("time.cloudflare.com", "time.google.com")) -> float | None:
    if os.name != "nt":
        return None
    for srv in servers:
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


def read_windows_process(pid: int) -> dict[str, Any] | None:
    """Inspect a live Windows process by numeric PID (PID + CreationDate anti-PID-reuse check)."""
    if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
        return None
    if os.name != "nt":
        return None
    ps = (
        "$ErrorActionPreference='Stop'; "
        f"$p=Get-CimInstance Win32_Process -Filter 'ProcessId = {int(pid)}'; "
        "if ($p) { [pscustomobject]@{"
        "pid=[int]$p.ProcessId; name=$p.Name; executable=$p.ExecutablePath; "
        "createdAt=$p.CreationDate.ToUniversalTime().ToString('o')"
        "} | ConvertTo-Json -Compress }"
    )
    proc = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps],
        capture_output=True,
        text=True,
        timeout=3.0,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    raw = (proc.stdout or "").strip()
    return json.loads(raw) if raw else None


def inspect_active_lock(
    lock_path: Path,
    *,
    process_inspector: Callable[[int], dict[str, Any] | None] = read_windows_process,
) -> dict[str, Any] | None:
    """Return active lock metadata if a verified live owner holds `lock_path`, else None (stale/absent)."""
    if not lock_path.is_file():
        return None
    try:
        saved = json.loads(lock_path.read_text(encoding="utf-8"))
    except Exception:
        return {"status": "CORRUPT_LOCK_FAIL_CLOSED", "path": str(lock_path)}

    pid = saved.get("pid")
    if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
        return {"status": "INVALID_PID_FAIL_CLOSED", "saved": saved}

    try:
        current = process_inspector(pid)
    except Exception:
        # Fail-closed if process verification cannot complete
        return {"status": "INSPECT_ERROR_FAIL_CLOSED", "pid": pid, "job_id": saved.get("job_id")}

    if not current:
        return None  # Stale lock: process no longer running

    saved_created = saved.get("created_at") or saved.get("createdAt")
    if not saved_created:
        # Legacy lock without CreationDate: fail-closed while PID is alive
        return {"status": "LEGACY_LOCK_ACTIVE", "pid": pid, "job_id": saved.get("job_id")}

    if str(current.get("createdAt") or "") != str(saved_created):
        return None  # OS reused the PID after original job exited -> stale lock

    saved_exec = saved.get("executable")
    cur_exec = current.get("executable")
    if saved_exec and cur_exec:
        if os.path.normcase(os.path.normpath(str(saved_exec))) != os.path.normcase(os.path.normpath(str(cur_exec))):
            return None  # Executable mismatch -> stale lock

    return {
        "job_id": saved.get("job_id"),
        "pid": pid,
        "created_at": saved_created,
        "executable": cur_exec or saved_exec,
    }


def count_forbidden_files(base_dir: Path) -> tuple[int, list[str]]:
    """Fast scan of `base_dir` (excluding `.venv`/`__pycache__`) for Holdout/2025+/secrets leaks."""
    if not base_dir.is_dir():
        return 0, []
    found: list[str] = []
    stack = [str(base_dir)]
    base_resolved = str(base_dir)
    while stack:
        cur = stack.pop()
        try:
            with os.scandir(cur) as it:
                for entry in it:
                    name = entry.name
                    low_name = name.lower()
                    if entry.is_dir(follow_symlinks=False):
                        if name in _SKIP_DIRS:
                            continue
                        if any(tok in low_name for tok in _FORBIDDEN_TOKENS):
                            found.append(os.path.relpath(entry.path, base_resolved))
                        else:
                            stack.append(entry.path)
                    elif entry.is_file(follow_symlinks=False):
                        if any(tok in low_name for tok in _FORBIDDEN_TOKENS):
                            found.append(os.path.relpath(entry.path, base_resolved))
        except OSError:
            continue
    return len(found), found[:20]


def collect_probe(base_dir: Path = DEFAULT_BASE_DIR) -> dict[str, Any]:
    t0 = time.perf_counter()
    # Sample CPU utilization sequentially BEFORE spawning powershell.exe / w32tm
    # subprocesses so probe child processes do not self-inflate idle CPU %.
    cpu_pct = read_cpu_util_pct(0.15)
    pwr = read_power_status()
    with ThreadPoolExecutor(max_workers=2) as pool:
        f_bat = pool.submit(read_battery_status_code)
        f_ntp = pool.submit(read_ntp_offset_ms)
        bat_code = f_bat.result()
        ntp_ms = f_ntp.result()

    free_ram_gb = read_free_ram_gb()
    drive_anchor = base_dir if base_dir.exists() else Path(base_dir.anchor or "C:\\")
    disk_free_gb = round(shutil.disk_usage(drive_anchor).free / float(1024 ** 3), 2)
    venv_ok = (base_dir / ".venv" / "Scripts" / "python.exe").is_file()
    active_lock = inspect_active_lock(base_dir / "locks" / "active_job.lock")
    forbidden_cnt, forbidden_sample = count_forbidden_files(base_dir)

    ac_line = int(pwr["ac_line_status"])
    ac_online = (ac_line == 1) and (bat_code != 1)

    reasons: list[str] = []
    if ac_line != 1:
        reasons.append(f"ac_offline(ACLineStatus={ac_line})")
    if bat_code == 1:
        reasons.append("battery_discharging(BatteryStatus=1)")
    if cpu_pct >= 40.0:
        reasons.append(f"cpu_busy({cpu_pct:.1f}%>=40%)")
    if free_ram_gb < 4.0:
        reasons.append(f"low_ram({free_ram_gb:.2f}GB<4.0GB)")
    if disk_free_gb < 15.0:
        reasons.append(f"low_disk({disk_free_gb:.2f}GB<15.0GB)")
    if active_lock is not None:
        reasons.append(f"active_job_lock({active_lock.get('job_id') or active_lock.get('status')})")
    if not venv_ok:
        reasons.append("missing_venv_python")
    if forbidden_cnt > 0:
        reasons.append(f"forbidden_files({forbidden_cnt})")
    if ntp_ms is not None and abs(ntp_ms) >= 1000.0:
        reasons.append(f"ntp_drift_ge_1000ms({ntp_ms:+.1f}ms)")

    return {
        "schema": "naqex-x13-probe-v1",
        "checked_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "order_send_count": ORDER_SEND_COUNT,
        "probe_local_ms": round((time.perf_counter() - t0) * 1000.0, 1),
        "ac_online": ac_online,
        "ac_line_status": ac_line,
        "battery_status_code": bat_code,
        "battery_pct": pwr["battery_pct"],
        "cpu_util_pct": cpu_pct,
        "free_ram_gb": free_ram_gb,
        "disk_free_gb": disk_free_gb,
        "venv_ok": venv_ok,
        "active_job_lock": active_lock,
        "ntp_offset_ms": ntp_ms,
        "forbidden_files": forbidden_cnt,
        "forbidden_sample": forbidden_sample,
        "eligible": len(reasons) == 0,
        "ineligible_reasons": reasons,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Read-only AC-power & resource probe for <X13_WORKER>.")
    ap.add_argument("--base-dir", type=Path, default=DEFAULT_BASE_DIR)
    args = ap.parse_args(argv)
    print(json.dumps(collect_probe(args.base_dir), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

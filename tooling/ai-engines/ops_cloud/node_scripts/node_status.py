"""Naqex Home-VPS read-only single-command health probe (`OrderSend = 0`)."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import pathlib
import re
import shutil
import subprocess
import time

MT5_ROOT = pathlib.Path(r"C:\Naqex\mt5")
HEROKU_LOG = pathlib.Path(r"C:\Naqex\logs\heroku_heartbeat_last.log")


def _run(cmd: list[str], timeout: int = 8) -> tuple[int, str, str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except Exception as exc:
        return -1, "", str(exc)


def _decode_mt5_log(path: pathlib.Path) -> str:
    raw = path.read_bytes()
    return raw.decode("utf-16-le", errors="ignore") if b"\x00" in raw[:200] else raw.decode("utf-8", errors="ignore")


def collect_status() -> dict:
    out: dict = {"checked_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "order_send_count": 0}

    _, s, _ = _run(
        [
            "powershell", "-NoProfile", "-Command",
            "@(Get-Process -Name terminal64 -EA 0 | ForEach-Object { @{pid=$_.Id; session=$_.SessionId; start=$_.StartTime.ToString('s')} }) | ConvertTo-Json -Compress",
        ]
    )
    try:
        mt5 = json.loads(s) if s else []
        if isinstance(mt5, dict):
            mt5 = [mt5]
    except Exception:
        mt5 = []
    out["mt5_procs"] = mt5

    hb_p = MT5_ROOT / "MQL5" / "Files" / "naqex_heartbeat.json"
    if hb_p.exists():
        try:
            hb = json.loads(hb_p.read_text(encoding="utf-8", errors="ignore"))
            hb["age_sec"] = int(time.time()) - int(hb.get("utc_ts", 0))
            out["heartbeat"] = hb
        except Exception as exc:
            out["heartbeat_err"] = str(exc)

    today = datetime.now().strftime("%Y%m%d")
    log_p = MT5_ROOT / "MQL5" / "Logs" / f"{today}.log"
    pg_ok: list[str] = []
    pg_warn: list[str] = []
    if log_p.exists():
        txt = _decode_mt5_log(log_p)
        start_hhmm = mt5[0]["start"][11:16] if mt5 else "00:00"
        for ln in txt.splitlines():
            parts = ln.split("\t")
            if len(parts) >= 5 and parts[2][:5] >= start_hhmm:
                if "PROPGUARD-OK" in ln:
                    pg_ok.append(parts[3])
                elif any(k in ln for k in ("PROPGUARD-WARN", "PROPGUARD-ERR", "CRITICAL")):
                    pg_warn.append(ln[-160:])
    out["propguard_ok_count"] = len(pg_ok)
    out["propguard_warn_count"] = len(pg_warn)
    if pg_warn:
        out["propguard_warns_sample"] = pg_warn[-5:]

    if HEROKU_LOG.exists():
        try:
            out["heroku_last"] = json.loads(HEROKU_LOG.read_text(encoding="utf-8-sig", errors="ignore"))
        except Exception:
            out["heroku_last_raw"] = HEROKU_LOG.read_text(encoding="utf-8-sig", errors="ignore")[:200]

    _, s, _ = _run(["w32tm", "/stripchart", "/computer:time.cloudflare.com", "/samples:1", "/dataonly"], timeout=6)
    m = re.search(r"([+-]\d+\.\d+s)", s)
    out["ntp_offset"] = m.group(1) if m else (s.splitlines()[-1] if s else "unknown")

    disks: dict = {}
    for drv in ("C", "D"):
        try:
            u = shutil.disk_usage(f"{drv}:\\")
            disks[drv] = {"free_gb": round(u.free / (1024**3), 1), "total_gb": round(u.total / (1024**3), 1)}
        except Exception:
            pass
    out["disks"] = disks

    _, s, _ = _run(
        [
            "powershell", "-NoProfile", "-Command",
            """
$os=Get-CimInstance Win32_OperatingSystem
$au=gp 'HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsUpdate\\AU' -EA 0
$al=gp 'HKLM:\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Winlogon' -EA 0
$tasks=@(Get-ScheduledTask 'Naqex_*' -EA 0|%{$i=Get-ScheduledTaskInfo -TaskName $_.TaskName -TaskPath $_.TaskPath -EA 0;@{name=$_.TaskName;state="$($_.State)";res=$i.LastTaskResult}})
@{
  uptime_hr=[math]::Round(((Get-Date)-$os.LastBootUpTime).TotalHours,2)
  free_ram_gb=[math]::Round($os.FreePhysicalMemory/1MB,1)
  wu_reboot=(Test-Path 'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\WindowsUpdate\\Auto Update\\RebootRequired')
  cbs_reboot=(Test-Path 'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Component Based Servicing\\RebootPending')
  no_auto_update=$au.NoAutoUpdate
  auto_logon=$al.AutoAdminLogon
  tasks=$tasks
}|ConvertTo-Json -Depth 3 -Compress
""",
        ]
    )
    try:
        out["system"] = json.loads(s)
    except Exception:
        out["system_raw"] = s[:200]
    return out


if __name__ == "__main__":
    print(json.dumps(collect_status(), ensure_ascii=True))

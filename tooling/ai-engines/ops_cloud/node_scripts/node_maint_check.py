"""Naqex Home-VPS Windows 10 IoT LTSC deep maintenance & 24/5 lock check (`OrderSend = 0`)."""
from __future__ import annotations

import json
import os
import subprocess
from datetime import UTC, datetime

_NO_WINDOW_FLAGS: int = int(getattr(subprocess, "CREATE_NO_WINDOW", 0)) if os.name == "nt" else 0


def run_maint_check() -> dict:
    ps = r"""
$au = gp 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU' -EA 0
$wu = gp 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate' -EA 0
$al = gp 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon' -EA 0
$hb = gp 'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Power' -EA 0
$pf = @(Get-CimInstance Win32_PageFileSetting -EA 0 | ForEach-Object { $_.Name })
$diskIdle = (
  powercfg /query SCHEME_CURRENT SUB_DISK DISKIDLE 2>$null |
  Select-String 'Current AC Power Setting Index' |
  ForEach-Object { $_.Line.Trim() }
) -join '; '
$uo = @(
  Get-ScheduledTask -TaskPath '\Microsoft\Windows\UpdateOrchestrator\' -EA 0 |
  Where-Object { $_.TaskName -match 'Reboot' } |
  ForEach-Object {
    $i = Get-ScheduledTaskInfo -TaskName $_.TaskName -TaskPath $_.TaskPath -EA 0
    @{name=$_.TaskName; state="$($_.State)"; next="$($i.NextRunTime)"}
  }
)
$hf = @(
  Get-HotFix | Sort-Object InstalledOn -Descending | Select-Object -First 5 |
  ForEach-Object { @{id=$_.HotFixID; date="$($_.InstalledOn)"} }
)
$bakDir = 'D:\NaqexBackup\daily'
$latestBak = if (Test-Path $bakDir) {
  (Get-ChildItem $bakDir -Directory -EA 0 | Sort-Object Name -Descending | Select-Object -First 1).Name
} else { $null }
$pwshOk = Test-Path 'C:\Naqex\tools\pwsh\pwsh.exe'
$alBin = Test-Path 'C:\Naqex\tools\Sysinternals\Autologon64.exe'
$wuReb = 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired'
$cbsReb = 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\RebootPending'
@{
  wu_reboot_required = (Test-Path $wuReb)
  cbs_reboot_pending = (Test-Path $cbsReb)
  au_policy = @{
    NoAutoUpdate=$au.NoAutoUpdate
    AUOptions=$au.AUOptions
    NoAutoReboot=$au.NoAutoRebootWithLoggedOnUsers
    AlwaysAutoReboot=$au.AlwaysAutoRebootAtScheduledTime
  }
  wu_policy = @{
    SetActiveHours=$wu.SetActiveHours
    Start=$wu.ActiveHoursStart
    End=$wu.ActiveHoursEnd
    NoDeadlineReboot=$wu.ConfigureDeadlineNoAutoReboot
    ExcludeDrivers=$wu.ExcludeWUDriversInQualityUpdate
  }
  hiberboot_enabled = $hb.HiberbootEnabled
  disk_idle_ac = $diskIdle
  pagefiles = $pf
  auto_admin_logon = $al.AutoAdminLogon
  update_orchestrator_reboot = $uo
  recent_hotfixes = $hf
  latest_daily_backup = $latestBak
  pwsh7_installed = $pwshOk
  autologon64_present = $alBin
} | ConvertTo-Json -Depth 4 -Compress
"""
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps],
        capture_output=True,
        text=True,
        timeout=15,
        creationflags=_NO_WINDOW_FLAGS,
    )
    data = json.loads(r.stdout.strip()) if r.stdout.strip() else {"error": r.stderr.strip()[:300]}
    au = data.get("au_policy") or {}
    uo = data.get("update_orchestrator_reboot") or []
    armed_reboot = any(str(t.get("state", "")).lower() == "ready" for t in uo)
    data["checked_utc"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    data["order_send_count"] = 0
    data["ok"] = (
        not data.get("wu_reboot_required")
        and not data.get("cbs_reboot_pending")
        and au.get("NoAutoUpdate") == 1
        and au.get("NoAutoReboot") == 1
        and str(data.get("auto_admin_logon")) == "1"
        and not armed_reboot
        and "0x00000000" in str(data.get("disk_idle_ac", "")).lower()
    )
    return data


if __name__ == "__main__":
    print(json.dumps(run_maint_check(), ensure_ascii=True))

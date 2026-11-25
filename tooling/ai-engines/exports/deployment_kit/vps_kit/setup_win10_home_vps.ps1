<#
.SYNOPSIS
    Naqex Windows 10 Home-VPS Bootstrap Script (i3-7100 / Win10 IoT LTSC or Win10 Pro).

.DESCRIPTION
    Prepares a dedicated Windows 10 secondary PC for 24/5 MT5 + AI-Agent SSH remote operations:
      1. Power policy: Never sleep, never hibernate, display off 5m, disable Fast Startup
      2. Stability policy: Disable forced Windows Update auto-reboot while logged on
      3. Remote AI-Agent access: Install & enable built-in Windows OpenSSH Server (`sshd`)
      4. Prerequisite check: Git, Python/uv, Tailscale, LAN adapter status (zero Microsoft Store/winget required)
      5. Optional Scheduled Task registration for `pc_heartbeat_sender.py` (every 1 min -> Heroku Dead-Man's-Switch)

    Fail-closed invariants:
      - NEVER stores broker passwords, Heroku API keys, or ingest tokens in files/Git.
      - Safe `-DryRun` mode audits current PC readiness without making admin changes.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\setup_win10_home_vps.ps1 -DryRun
#>
[CmdletBinding()]
param(
    [string]$HeartbeatJsonPath = "",
    [string]$AccountLabel = "FTMO_HOME_PC",
    [switch]$RegisterHerokuHeartbeatTask,
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$IsAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
$Actions = New-Object System.Collections.Generic.List[string]
$Warnings = New-Object System.Collections.Generic.List[string]

if (-not $DryRun -and -not $IsAdmin) {
    throw "ADMIN_REQUIRED: Run PowerShell as Administrator to apply power/WindowsUpdate/OpenSSH settings (or pass -DryRun to inspect)."
}

# 1. Check key tools (works on Win10 IoT LTSC without winget/Store)
$Tools = [ordered]@{
    git       = [bool](Get-Command git -ErrorAction SilentlyContinue)
    python    = [bool](Get-Command python -ErrorAction SilentlyContinue)
    uv        = [bool](Get-Command uv -ErrorAction SilentlyContinue)
    tailscale = [bool](Get-Command tailscale -ErrorAction SilentlyContinue)
    sshd_svc  = [bool](Get-Service -Name sshd -ErrorAction SilentlyContinue)
}

if (-not $Tools.tailscale) { $Warnings.Add("Install Tailscale from https://tailscale.com/download/windows for secure remote SSH/RDP.") }
if (-not $Tools.git)       { $Warnings.Add("Install Git for Windows from https://git-scm.com/download/win") }
if (-not $Tools.python)    { $Warnings.Add("Install Python 3.12+ (or uv from https://docs.astral.sh/uv/)") }

# 2. Power plan: Never sleep, never hibernate, monitor off 5m
if ($DryRun) {
    $Actions.Add("DRYRUN_POWERCFG: standby-timeout-ac=0, hibernate-timeout-ac=0, monitor-timeout-ac=5, HiberbootEnabled=0")
} else {
    powercfg /change standby-timeout-ac 0 | Out-Null
    powercfg /change hibernate-timeout-ac 0 | Out-Null
    powercfg /change monitor-timeout-ac 5 | Out-Null
    powercfg /h off | Out-Null
    $pwrReg = "HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Power"
    if (Test-Path $pwrReg) { Set-ItemProperty -Path $pwrReg -Name "HiberbootEnabled" -Type DWord -Value 0 }
    $Actions.Add("APPLIED_POWERCFG_NEVER_SLEEP")
}

# 3. Disable forced Windows Update auto-reboot with logged-on user
if ($DryRun) {
    $Actions.Add("DRYRUN_WU_POLICY: NoAutoRebootWithLoggedOnUsers=1")
} else {
    $wuKey = "HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU"
    New-Item -Path $wuKey -Force | Out-Null
    Set-ItemProperty -Path $wuKey -Name "NoAutoRebootWithLoggedOnUsers" -Type DWord -Value 1
    Set-ItemProperty -Path $wuKey -Name "AUOptions" -Type DWord -Value 3
    $Actions.Add("APPLIED_NO_AUTO_REBOOT_POLICY")
}

# 4. Enable built-in Windows OpenSSH Server for AI-Agent remote SSH automation
if ($DryRun) {
    $Actions.Add("DRYRUN_OPENSSH: ensure OpenSSH.Server capability + sshd Automatic + Firewall TCP 22")
} else {
    if (-not $Tools.sshd_svc) {
        Add-WindowsCapability -Online -Name "OpenSSH.Server~~~~0.0.1.0" | Out-Null
    }
    Set-Service -Name sshd -StartupType Automatic
    Start-Service sshd
    if (-not (Get-NetFirewallRule -Name "Naqex-OpenSSH-Server" -ErrorAction SilentlyContinue)) {
        New-NetFirewallRule -Name "Naqex-OpenSSH-Server" -DisplayName "Naqex OpenSSH Server (TCP 22)" -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22 | Out-Null
    }
    $Actions.Add("ENABLED_OPENSSH_SERVER")
}

# 5. Optional 1-minute Scheduled Task pushing heartbeat -> Heroku Dead-Man's-Switch
$KitRoot = Split-Path -Parent $PSScriptRoot
$AiEngines = Split-Path -Parent (Split-Path -Parent $KitRoot)
$SenderPy = Join-Path $AiEngines "ops_cloud\heroku_deadman\pc_heartbeat_sender.py"
$TaskName = "Naqex_Heroku_Heartbeat_$AccountLabel"

if ($RegisterHerokuHeartbeatTask) {
    if ([string]::IsNullOrWhiteSpace($HeartbeatJsonPath)) {
        throw "MISSING_HEARTBEAT_PATH: pass -HeartbeatJsonPath pointing to MQL5\Files\naqex_heartbeat.json"
    }
    $pyExe = (Get-Command python -ErrorAction SilentlyContinue).Source
    if ([string]::IsNullOrWhiteSpace($pyExe)) { $pyExe = "python.exe" }
    $cmd = "`"$pyExe`" -X utf8 `"$SenderPy`" --heartbeat-path `"$HeartbeatJsonPath`" --account-label `"$AccountLabel`" --once"
    if ($DryRun) {
        $Actions.Add("DRYRUN_REGISTER_SCHTASK:$TaskName => $cmd")
    } else {
        schtasks /Create /TN $TaskName /SC MINUTE /MO 1 /TR $cmd /F | Out-Null
        $Actions.Add("REGISTERED_SCHTASK:$TaskName")
    }
}

$Out = [ordered]@{
    schema       = "naqex-win10-home-vps-bootstrap-v1"
    utc          = [DateTimeOffset]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
    dry_run      = [bool]$DryRun
    is_admin     = [bool]$IsAdmin
    order_send   = 0
    tools_found  = $Tools
    actions      = @($Actions)
    warnings     = @($Warnings)
}
Write-Output ($Out | ConvertTo-Json -Depth 5)
exit 0

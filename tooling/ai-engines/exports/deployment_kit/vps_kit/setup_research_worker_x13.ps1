<#
.SYNOPSIS
    Bootstrap a Secondary Windows Laptop as a LAN Research Worker (OpenSSH Key Auth + AC Never-Sleep).

.DESCRIPTION
    One-time setup script for a secondary Windows research laptop (e.g., ThinkPad X13) so the main Dev PC
    can dispatch heavy offline backtests / MT5 Strategy Tester jobs over LAN SSH without passwords:
      1. Installs/enables built-in Windows OpenSSH Server (`sshd`, Automatic start) + Firewall TCP 22 (Private/LAN)
      2. Authorizes the provided Ed25519 PUBLIC key into `administrators_authorized_keys` (strict Windows ACLs)
      3. Configures AC power plan: never sleep while plugged in (`standby-timeout-ac = 0`, display off 5m)
         while keeping battery power settings untouched for portability
      4. Creates `C:\NaqexResearch\` working directory and prints LAN IPv4 + username for Dev PC `~/.ssh/config`

    Safety invariants:
      - NEVER stores passwords, private keys, or broker credentials.
      - Safe `-DryRun` mode audits readiness without modifying system settings.

.EXAMPLE
    # Run in PowerShell as Administrator on the secondary laptop:
    powershell -ExecutionPolicy Bypass -File .\setup_research_worker_x13.ps1 -PublicKey "ssh-ed25519 AAAA... devpc"
#>
[CmdletBinding()]
param(
    [string]$PublicKey = "",
    [string]$WorkRoot = "C:\NaqexResearch",
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$IsAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $DryRun -and -not $IsAdmin) {
    throw "ADMIN_REQUIRED: Run PowerShell as Administrator on the secondary laptop (or pass -DryRun)."
}

$Actions = New-Object System.Collections.Generic.List[string]

# 1. OpenSSH Server + Firewall (LAN/Private)
Write-Host "[1/4] Checking Windows OpenSSH Server (first-time download from Windows Update can take 1-4 min)..."
if ($DryRun) {
    $Actions.Add("DRYRUN_OPENSSH: Install/enable sshd Automatic + Firewall Private TCP 22")
} else {
    if (-not (Get-Service -Name sshd -ErrorAction SilentlyContinue)) {
        Write-Host "      Installing OpenSSH.Server capability via Windows Update (please wait)..."
        Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0 | Out-Null
    } else {
        Write-Host "      OpenSSH Server already installed (skipping download)."
    }
    Set-Service -Name sshd -StartupType Automatic
    Start-Service sshd
    if (-not (Get-NetFirewallRule -Name "Naqex-Research-SSH-LAN" -ErrorAction SilentlyContinue)) {
        New-NetFirewallRule -Name "Naqex-Research-SSH-LAN" -DisplayName "Naqex Research Worker SSH (LAN)" `
            -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22 -Profile Private | Out-Null
    }
    $Actions.Add("ENABLED_OPENSSH_SERVER_LAN")
}

# 2. Authorize Dev PC Ed25519 PUBLIC key (zero password login for automation)
Write-Host "[2/4] Configuring Ed25519 SSH key (passwordless LAN access)..."
if ($PublicKey -and $PublicKey.Trim().StartsWith("ssh-")) {
    if ($DryRun) {
        $Actions.Add("DRYRUN_AUTHKEY: Add public key to administrators_authorized_keys + user authorized_keys")
    } else {
        $pubTrim = $PublicKey.Trim()
        # Admin key path (required by Windows OpenSSH when user is in Administrators group)
        $adminKeyFile = "C:\ProgramData\ssh\administrators_authorized_keys"
        $existing = if (Test-Path $adminKeyFile) { Get-Content $adminKeyFile -ErrorAction SilentlyContinue } else { @() }
        if ($existing -notcontains $pubTrim) {
            [System.IO.File]::AppendAllText($adminKeyFile, "$pubTrim`n", (New-Object System.Text.UTF8Encoding($false)))
        }
        icacls $adminKeyFile /inheritance:r /grant "*S-1-5-32-544:F" /grant "*S-1-5-18:F" | Out-Null

        # Also add to user ~/.ssh/authorized_keys for non-admin accounts
        $userSshDir = Join-Path $env:USERPROFILE ".ssh"
        New-Item -ItemType Directory -Path $userSshDir -Force | Out-Null
        $userKeyFile = Join-Path $userSshDir "authorized_keys"
        $uExist = if (Test-Path $userKeyFile) { Get-Content $userKeyFile -ErrorAction SilentlyContinue } else { @() }
        if ($uExist -notcontains $pubTrim) {
            [System.IO.File]::AppendAllText($userKeyFile, "$pubTrim`n", (New-Object System.Text.UTF8Encoding($false)))
        }
        $Actions.Add("INSTALLED_PUBLIC_KEY_NO_PASSWORD_SSH")
    }
}

# 3. Laptop AC Power Policy (close lid = Do Nothing on AC, never sleep/hibernate/disk-idle on AC; battery untouched!)
Write-Host "[3/4] Applying Laptop AC Power Plan (Lid Close = Do Nothing on AC, Never Sleep on AC, Display off 5m)..."
if ($DryRun) {
    $Actions.Add("DRYRUN_POWERCFG: AC lid-close=0 (Do Nothing), standby-ac=0, hibernate-ac=0, disk-ac=0, monitor-ac=5, HiberbootEnabled=0 (DC battery behavior unchanged)")
} else {
    powercfg /change standby-timeout-ac 0 | Out-Null
    powercfg /change hibernate-timeout-ac 0 | Out-Null
    powercfg /change disk-timeout-ac 0 | Out-Null
    powercfg /change monitor-timeout-ac 5 | Out-Null
    # Close lid while plugged into AC = 0 (Do Nothing), so laptop keeps running closed!
    powercfg /setacvalueindex SCHEME_CURRENT SUB_BUTTONS LIDACTION 0 | Out-Null
    powercfg /setactive SCHEME_CURRENT | Out-Null
    $pwrReg = "HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Power"
    if (Test-Path $pwrReg) { Set-ItemProperty -Path $pwrReg -Name "HiberbootEnabled" -Type DWord -Value 0 }
    $Actions.Add("APPLIED_LAPTOP_AC_LID_OPEN_RUNNING_NEVER_SLEEP")
}

# 4. Working directory & Tool audit
Write-Host "[4/4] Auditing tools & LAN IP..."
if (-not $DryRun) {
    New-Item -ItemType Directory -Path $WorkRoot -Force | Out-Null
}
$LanIps = @(Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object { $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254.*" -and $_.PrefixOrigin -ne "WellKnown" } |
    Select-Object -ExpandProperty IPAddress)

[ordered]@{
    schema     = "naqex.research_worker_bootstrap.v1"
    dry_run    = [bool]$DryRun
    hostname   = $env:COMPUTERNAME
    username   = $env:USERNAME
    lan_ips    = $LanIps
    work_root  = $WorkRoot
    tools      = [ordered]@{
        git       = [bool](Get-Command git -ErrorAction SilentlyContinue)
        python    = [bool](Get-Command python -ErrorAction SilentlyContinue)
        uv        = [bool](Get-Command uv -ErrorAction SilentlyContinue)
        tailscale = [bool](Get-Command tailscale -ErrorAction SilentlyContinue)
        sshd      = [bool](Get-Service -Name sshd -ErrorAction SilentlyContinue)
    }
    actions    = $Actions
    next_tip   = "In Lenovo Vantage, enable Battery Charge Threshold (60-80%) before long plugged-in runs."
} | ConvertTo-Json -Depth 4

<#
.SYNOPSIS
    PowerShell 5.1-safe installer for Naqex Watchdog (15m), Morning Briefing (07:30), and NTP check.

.DESCRIPTION
    Registers non-admin (user-scope) Windows Scheduled Tasks running at BELOW_NORMAL priority
    with OrderSend=0:
      - Naqex-Watchdog-15m     (every 15 minutes; 3650-day repetition duration - PS 5.1 safe!)
      - Naqex-Morning-Briefing (daily at 07:30 local time)

    Safety & Compatibility Invariants:
      - 100% Windows PowerShell 5.1 safe (uses bounded 3650-day repetition, zero PS 7-only syntax)
      - Supports -DryRun (validates task trigger/settings objects in memory without registering)
      - Supports -UserScopeOnly (non-admin Interactive Limited principal)
      - Zero secrets, zero raw IPs, zero hardcoded user profile paths, OrderSend=0

.EXAMPLE
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tooling\automation\install_ntp_and_watchdog_tasks.ps1 -DryRun -UserScopeOnly
#>
[CmdletBinding()]
param(
    [string]$WorkspaceRoot = "",
    [switch]$DryRun,
    [switch]$UserScopeOnly,
    [switch]$Offline,
    [switch]$ConfigureNtp,
    [ValidateRange(1, 1440)]
    [int]$WatchdogIntervalMinutes = 15,
    [string]$MorningBriefingTime = "07:30"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$OrderSendCount = 0
[uint32]$TaskSchedulerBelowNormalPriority = 7

if ([string]::IsNullOrWhiteSpace($WorkspaceRoot)) {
    $ToolingDir = Split-Path -Parent $PSScriptRoot
    $ResolvedRoot = Split-Path -Parent $ToolingDir
} else {
    $ResolvedRoot = (Resolve-Path -LiteralPath $WorkspaceRoot).Path
}

if (-not ($MorningBriefingTime -match '^(?:[01]\d|2[0-3]):[0-5]\d$')) {
    throw "INVALID_BRIEFING_TIME: Expected HH:mm (24h), got '$MorningBriefingTime'"
}

$RuntimeDir = Join-Path $ResolvedRoot ".runtime"
$VenvDir = Join-Path $RuntimeDir "quant-audit-v24"
$VenvScripts = Join-Path $VenvDir "Scripts"
$BundledPython = Join-Path $VenvScripts "python.exe"
$PythonExe = if (Test-Path -LiteralPath $BundledPython) { $BundledPython } else { "python.exe" }
$PythonBundledExists = [bool](Test-Path -LiteralPath $BundledPython)

$AutomationDir = Join-Path (Join-Path $ResolvedRoot "tooling") "automation"
$WatchdogScript = Join-Path $AutomationDir "watchdog_15m.py"
$BriefingScript = Join-Path $AutomationDir "morning_briefing.py"

# Check elevation safely (no hardcoded usernames)
$CurrentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
$CurrentPrincipal = New-Object Security.Principal.WindowsPrincipal($CurrentIdentity)
$IsAdmin = [bool]$CurrentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
$EffectiveUserScope = [bool]($UserScopeOnly -or (-not $IsAdmin))

# PowerShell 5.1-safe bounded repetition duration: 3650 days (10 years).
$RepetitionInterval = New-TimeSpan -Minutes $WatchdogIntervalMinutes
$RepetitionDuration = New-TimeSpan -Days 3650

$WatchdogTrigger = New-ScheduledTaskTrigger -Once -At (Get-Date).Date `
    -RepetitionInterval $RepetitionInterval `
    -RepetitionDuration $RepetitionDuration
$WatchdogArgs = "-X utf8 `"$WatchdogScript`" --below-normal"
$WatchdogAction = New-ScheduledTaskAction -Execute $PythonExe -Argument $WatchdogArgs -WorkingDirectory $ResolvedRoot
$WatchdogSettings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 5)
$WatchdogSettings.Priority = $TaskSchedulerBelowNormalPriority

$BriefingTrigger = New-ScheduledTaskTrigger -Daily -At $MorningBriefingTime
$BriefingArgs = "-X utf8 `"$BriefingScript`" --notify"
$BriefingAction = New-ScheduledTaskAction -Execute $PythonExe -Argument $BriefingArgs -WorkingDirectory $ResolvedRoot
$BriefingSettings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 10)
$BriefingSettings.Priority = $TaskSchedulerBelowNormalPriority

$TaskPrincipal = if ($EffectiveUserScope) {
    New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
} else {
    New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest
}

$Actions = New-Object System.Collections.Generic.List[string]
$TaskSpecs = @(
    [ordered]@{
        name               = "Naqex-Watchdog-15m"
        schedule           = "Every $WatchdogIntervalMinutes minutes (RepetitionDuration=P3650D)"
        script             = "tooling/automation/watchdog_15m.py"
        script_exists      = [bool](Test-Path -LiteralPath $WatchdogScript)
        process_priority   = "BELOW_NORMAL"
        scheduler_priority = $TaskSchedulerBelowNormalPriority
        order_send_count   = $OrderSendCount
        trigger_interval   = [string]$WatchdogTrigger.Repetition.Interval
        trigger_duration   = [string]$WatchdogTrigger.Repetition.Duration
        action_obj         = $WatchdogAction
        trigger_obj        = $WatchdogTrigger
        settings_obj       = $WatchdogSettings
    },
    [ordered]@{
        name               = "Naqex-Morning-Briefing"
        schedule           = "Daily at $MorningBriefingTime local time"
        script             = "tooling/automation/morning_briefing.py"
        script_exists      = [bool](Test-Path -LiteralPath $BriefingScript)
        process_priority   = "BELOW_NORMAL"
        scheduler_priority = $TaskSchedulerBelowNormalPriority
        order_send_count   = $OrderSendCount
        trigger_interval   = "DAILY"
        trigger_duration   = "INDEFINITE_DAILY"
        action_obj         = $BriefingAction
        trigger_obj        = $BriefingTrigger
        settings_obj       = $BriefingSettings
    }
)

$TaskSummaries = New-Object System.Collections.Generic.List[object]
foreach ($spec in $TaskSpecs) {
    $TaskName = $spec.name
    if ($DryRun) {
        $Actions.Add("DRYRUN_VALIDATED_TASK:$TaskName")
        $TaskStatus = "DRYRUN_READY"
    } else {
        $TaskDef = New-ScheduledTask `
            -Action $spec.action_obj `
            -Trigger $spec.trigger_obj `
            -Settings $spec.settings_obj `
            -Principal $TaskPrincipal `
            -Description "Naqex zero-token automation task ($TaskName, BELOW_NORMAL, OrderSend=0)"
        Register-ScheduledTask -TaskName $TaskName -InputObject $TaskDef -Force | Out-Null
        $Actions.Add("REGISTERED_TASK:$TaskName")
        $TaskStatus = "REGISTERED"
    }

    $TaskSummaries.Add([ordered]@{
        name               = $TaskName
        status             = $TaskStatus
        schedule           = $spec.schedule
        script             = $spec.script
        script_exists      = $spec.script_exists
        process_priority   = $spec.process_priority
        scheduler_priority = $spec.scheduler_priority
        trigger_interval   = $spec.trigger_interval
        trigger_duration   = $spec.trigger_duration
        order_send_count   = $OrderSendCount
    })
}

# Read-only NTP check (configuration requires Admin and explicit -ConfigureNtp without -UserScopeOnly)
$NtpStatus = "SKIPPED_OFFLINE"
if (-not $Offline) {
    if ($ConfigureNtp -and (-not $EffectiveUserScope) -and $IsAdmin -and (-not $DryRun)) {
        & w32tm /config /manualpeerlist:"time.cloudflare.com,0x9 time.google.com,0x9" /syncfromflags:manual /reliable:YES /update | Out-Null
        & w32tm /resync /nowait | Out-Null
        $NtpStatus = "CONFIGURED_AND_RESYNCED"
        $Actions.Add("CONFIGURED_W32TM_NTP")
    } elseif ($ConfigureNtp -and ($EffectiveUserScope -or (-not $IsAdmin))) {
        $NtpStatus = "SKIPPED_USER_SCOPE_REQUIRES_ADMIN"
        $Actions.Add("SKIPPED_NTP_CONFIG_NON_ADMIN")
    } else {
        try {
            $null = & w32tm /query /status 2>&1
            $NtpStatus = if ($LASTEXITCODE -eq 0) { "W32TM_STATUS_OK" } else { "W32TM_QUERY_NONZERO" }
        } catch {
            $NtpStatus = "W32TM_UNAVAILABLE"
        }
        if ($DryRun) {
            $Actions.Add("DRYRUN_CHECKED_NTP_STATUS:$NtpStatus")
        }
    }
} else {
    $Actions.Add("OFFLINE_SKIPPED_NTP_QUERY")
}

$Summary = [ordered]@{
    schema                = "naqex-ntp-watchdog-tasks-v1"
    checked_utc           = [DateTimeOffset]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
    powershell_version    = $PSVersionTable.PSVersion.ToString()
    ps51_safe_duration    = "New-TimeSpan -Days 3650"
    dry_run               = [bool]$DryRun
    user_scope_only       = [bool]$UserScopeOnly
    effective_scope       = if ($EffectiveUserScope) { "USER_LIMITED_NON_ADMIN" } else { "ELEVATED_INTERACTIVE" }
    is_admin              = $IsAdmin
    offline               = [bool]$Offline
    order_send_count      = $OrderSendCount
    process_priority      = "BELOW_NORMAL"
    scheduler_priority    = $TaskSchedulerBelowNormalPriority
    bundled_python_exists = $PythonBundledExists
    ntp_status            = $NtpStatus
    tasks                 = $TaskSummaries.ToArray()
    actions               = $Actions.ToArray()
}

Write-Output ($Summary | ConvertTo-Json -Depth 6)
exit 0

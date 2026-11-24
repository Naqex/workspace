<#
.SYNOPSIS
    Naqex Lean Local + Windows VPS MT5 Watchdog (M1.5).

.DESCRIPTION
    Monitors an MT5 terminal running the Naqex 8-EA + AccountOrchestrator suite on either
    the owner's local Windows PC (Free Trial) or a future Windows VPS (Challenge/Funded):
      1. MT5 process health (`terminal64` running check, optional path match)
      2. `naqex_heartbeat.json` freshness (`StaleAfterSec`, default 180s), kill-switch,
         AMBER/RED risk regime, and orphan no-SL position detection
      3. Safe log rotation for watchdog logs & optional MT5 audit logs (> MaxLogBytes)
      4. Pluggable alert sink: defaults to a local JSONL alert file (zero secrets, zero network).
         Optional webhook dispatch ONLY when `-EnableWebhook` is passed AND env var
         `NAQEX_ALERT_WEBHOOK_URL` is configured by the operator.

    Fail-closed: NEVER places orders, NEVER logs into MT5, NEVER stores credentials.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\naqex_mt5_watchdog.ps1 -DryRun -HeartbeatPath .\sample_hb.json -StateDir .\out
#>
[CmdletBinding()]
param(
    [string]$HeartbeatPath = "",
    [string]$ProcessName = "terminal64",
    [string]$StateDir = "",
    [string]$AlertFile = "",
    [string]$WatchdogLogFile = "",
    [int]$StaleAfterSec = 180,
    [int]$MaxLogBytes = 5242880,
    [int]$KeepRotatedLogs = 5,
    [string]$AccountLabel = "NAQEX_MT5_LOCAL",
    [switch]$DryRun,
    [switch]$SkipProcessCheck,
    [switch]$EnableWebhook,
    [long]$NowUtcOverride = 0
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Resolve-DefaultStateDir {
    param([string]$InputDir)
    if (-not [string]::IsNullOrWhiteSpace($InputDir)) {
        return $InputDir
    }
    return (Join-Path $PSScriptRoot "watchdog_state")
}

function Rotate-LogFileIfNeeded {
    param(
        [string]$Path,
        [int]$ThresholdBytes,
        [int]$KeepCount,
        [bool]$IsDryRun
    )
    $result = [ordered]@{
        path        = $Path
        rotated     = $false
        size_bytes  = 0
        archive     = $null
        dry_run     = $IsDryRun
    }
    if (-not (Test-Path -LiteralPath $Path)) {
        return $result
    }
    $fi = Get-Item -LiteralPath $Path
    $result.size_bytes = [long]$fi.Length
    if ($fi.Length -lt $ThresholdBytes) {
        return $result
    }
    $stamp = [DateTimeOffset]::UtcNow.ToString("yyyyMMddTHHmmssZ")
    $archivePath = "$Path.$stamp.bak"
    $result.archive = $archivePath
    if (-not $IsDryRun) {
        Move-Item -LiteralPath $Path -Destination $archivePath -Force
        $dir = Split-Path -Parent $Path
        $leaf = Split-Path -Leaf $Path
        $oldArchives = Get-ChildItem -LiteralPath $dir -Filter "$leaf.*.bak" -File -ErrorAction SilentlyContinue |
            Sort-Object LastWriteTimeUtc -Descending |
            Select-Object -Skip $KeepCount
        foreach ($old in $oldArchives) {
            Remove-Item -LiteralPath $old.FullName -Force -ErrorAction SilentlyContinue
        }
    }
    $result.rotated = $true
    return $result
}

function Invoke-AlertSink {
    param(
        [hashtable]$Payload,
        [string]$SinkFile,
        [bool]$IsDryRun,
        [bool]$AllowWebhook
    )
    $sinkResult = [ordered]@{
        local_alert_written = $false
        local_alert_file    = $SinkFile
        webhook_sent        = $false
        webhook_skipped     = $true
        webhook_reason      = "disabled_by_default"
    }

    $jsonLine = ($Payload | ConvertTo-Json -Compress -Depth 6)
    $parentDir = Split-Path -Parent $SinkFile
    if (-not (Test-Path -LiteralPath $parentDir)) {
        New-Item -ItemType Directory -Force -Path $parentDir | Out-Null
    }
    Add-Content -LiteralPath $SinkFile -Value $jsonLine -Encoding UTF8
    $sinkResult.local_alert_written = $true

    if ($AllowWebhook) {
        $webhookUrl = $env:NAQEX_ALERT_WEBHOOK_URL
        if ($IsDryRun) {
            $sinkResult.webhook_reason = "dry_run_mode"
        } elseif ([string]::IsNullOrWhiteSpace($webhookUrl)) {
            $sinkResult.webhook_reason = "env_NAQEX_ALERT_WEBHOOK_URL_empty"
        } else {
            try {
                $body = @{
                    text    = "[$($Payload.status)] $($Payload.account_label): $($Payload.alerts -join ' | ')"
                    content = "[$($Payload.status)] $($Payload.account_label): $($Payload.alerts -join ' | ')"
                } | ConvertTo-Json -Compress
                Invoke-RestMethod -Uri $webhookUrl -Method Post -Body $body -ContentType "application/json" -TimeoutSec 10 | Out-Null
                $sinkResult.webhook_sent = $true
                $sinkResult.webhook_skipped = $false
                $sinkResult.webhook_reason = "sent"
            } catch {
                $sinkResult.webhook_reason = "error:$($_.Exception.Message)"
            }
        }
    }
    return $sinkResult
}

$resolvedStateDir = Resolve-DefaultStateDir -InputDir $StateDir
if (-not (Test-Path -LiteralPath $resolvedStateDir)) {
    New-Item -ItemType Directory -Force -Path $resolvedStateDir | Out-Null
}
$resolvedAlertFile = if ([string]::IsNullOrWhiteSpace($AlertFile)) {
    Join-Path $resolvedStateDir "naqex_watchdog_alerts.jsonl"
} else {
    $AlertFile
}
$resolvedLogFile = if ([string]::IsNullOrWhiteSpace($WatchdogLogFile)) {
    Join-Path $resolvedStateDir "naqex_watchdog.log"
} else {
    $WatchdogLogFile
}

$nowUtcTs = if ($NowUtcOverride -gt 0) { $NowUtcOverride } else { [DateTimeOffset]::UtcNow.ToUnixTimeSeconds() }
$nowUtcIso = [DateTimeOffset]::FromUnixTimeSeconds($nowUtcTs).UtcDateTime.ToString("yyyy-MM-ddTHH:mm:ssZ")

$status = "OK"
$alerts = New-Object System.Collections.Generic.List[string]

# 1. Log rotation check (both watchdog log and alert log)
$rotations = @()
$rotations += Rotate-LogFileIfNeeded -Path $resolvedLogFile -ThresholdBytes $MaxLogBytes -KeepCount $KeepRotatedLogs -IsDryRun:$DryRun
$rotations += Rotate-LogFileIfNeeded -Path $resolvedAlertFile -ThresholdBytes $MaxLogBytes -KeepCount $KeepRotatedLogs -IsDryRun:$DryRun

# 2. MT5 terminal process check
$procRunning = $false
$procCount = 0
if ($SkipProcessCheck) {
    $procRunning = $true
    $procCount = -1
} else {
    $procs = @(Get-Process -Name $ProcessName -ErrorAction SilentlyContinue)
    $procCount = $procs.Count
    $procRunning = ($procCount -gt 0)
    if (-not $procRunning) {
        if ($DryRun) {
            if ($status -eq "OK") { $status = "WARNING" }
            $alerts.Add("MT5_PROCESS_NOT_RUNNING(dry_run): process '$ProcessName' count=0")
        } else {
            $status = "CRITICAL"
            $alerts.Add("MT5_PROCESS_NOT_RUNNING: process '$ProcessName' count=0")
        }
    }
}

# 3. Heartbeat JSON inspection
$hbData = $null
$hbAgeSec = $null
if ([string]::IsNullOrWhiteSpace($HeartbeatPath)) {
    if ($status -eq "OK") { $status = "WARNING" }
    $alerts.Add("HEARTBEAT_PATH_UNSET: pass -HeartbeatPath pointing to MQL5\\Files\\naqex_heartbeat.json")
} elseif (-not (Test-Path -LiteralPath $HeartbeatPath)) {
    $status = "CRITICAL"
    $alerts.Add("HEARTBEAT_MISSING: file not found at '$HeartbeatPath'")
} else {
    try {
        $rawHb = Get-Content -LiteralPath $HeartbeatPath -Raw -Encoding UTF8
        $hbData = $rawHb | ConvertFrom-Json
        $hbTs = [long]$hbData.utc_ts
        $rawAgeSec = $nowUtcTs - $hbTs
        $hbAgeSec = $rawAgeSec
        if ($rawAgeSec -lt -60) {
            $status = "CRITICAL"
            $alerts.Add("HEARTBEAT_FUTURE_TIMESTAMP: age=${rawAgeSec}s (clock skew > 60s)")
        } elseif ($rawAgeSec -gt $StaleAfterSec) {
            $status = "CRITICAL"
            $alerts.Add("HEARTBEAT_STALE: age=${rawAgeSec}s > ${StaleAfterSec}s")
        }
        $hbProps = $hbData.PSObject.Properties.Name
        if (($hbProps -contains "terminal_connected") -and (-not [bool]$hbData.terminal_connected)) {
            $status = "CRITICAL"
            $alerts.Add("BROKER_DISCONNECTED: terminal_connected=false")
        }
        if ($hbProps -contains "quote_ts") {
            $qTs = [long]$hbData.quote_ts
            $nowDt = [DateTimeOffset]::FromUnixTimeSeconds($nowUtcTs).UtcDateTime
            $isActiveMarket = ($nowDt.DayOfWeek -ge [System.DayOfWeek]::Monday -and $nowDt.DayOfWeek -le [System.DayOfWeek]::Friday -and $nowDt.Hour -ge 1 -and $nowDt.Hour -lt 20)
            if ($isActiveMarket -and $qTs -gt 0 -and ($nowUtcTs - $qTs) -gt ($StaleAfterSec * 2)) {
                if ($status -eq "OK") { $status = "WARNING" }
                $alerts.Add("QUOTE_FEED_STALE: quote_age=$($nowUtcTs - $qTs)s > $($StaleAfterSec * 2)s")
            }
        }
        if ([bool]$hbData.kill_switch) {
            $status = "CRITICAL"
            $alerts.Add("GLOBAL_KILLSWITCH_ACTIVE: daily_dd=$($hbData.daily_dd_pct)% static_dd=$($hbData.static_dd_pct)%")
        }
        if ([int]$hbData.orphan_no_sl -gt 0) {
            $status = "CRITICAL"
            $alerts.Add("ORPHAN_NO_SL_POSITIONS: count=$($hbData.orphan_no_sl)")
        }
        $regime = [string]$hbData.regime
        if ($regime -in @("AMBER_BRAKE", "RED_BRAKE")) {
            if ($status -eq "OK") { $status = "WARNING" }
            $alerts.Add("RISK_REGIME=${regime}: risk_mult=$($hbData.risk_mult)x static_dd=$($hbData.static_dd_pct)%")
        }
    } catch {
        $status = "CRITICAL"
        $alerts.Add("HEARTBEAT_PARSE_ERROR: $($_.Exception.Message)")
    }
}

$report = [ordered]@{
    schema          = "naqex-mt5-watchdog-v1"
    checked_utc     = $nowUtcIso
    checked_utc_ts  = $nowUtcTs
    account_label   = $AccountLabel
    dry_run         = [bool]$DryRun
    status          = $status
    process_name    = $ProcessName
    process_running = $procRunning
    process_count   = $procCount
    heartbeat_path  = $HeartbeatPath
    heartbeat_age_s = $hbAgeSec
    heartbeat       = $hbData
    alerts          = @($alerts)
    log_rotations   = $rotations
}

# 4. Write watchdog log line and emit alert sink when status != OK or in DryRun
$logLine = "$nowUtcIso [$status] acct=$AccountLabel proc=$procCount hb_age=$hbAgeSec alerts=$($alerts.Count)"
Add-Content -LiteralPath $resolvedLogFile -Value $logLine -Encoding UTF8

$sinkInfo = $null
if ($status -ne "OK" -or $DryRun) {
    $sinkInfo = Invoke-AlertSink -Payload $report -SinkFile $resolvedAlertFile -IsDryRun:$DryRun -AllowWebhook:$EnableWebhook
}
$report["alert_sink"] = $sinkInfo

$jsonOut = $report | ConvertTo-Json -Depth 6
Write-Output $jsonOut

if ($DryRun) {
    exit 0
}
if ($status -eq "CRITICAL") {
    exit 2
}
if ($status -eq "WARNING") {
    exit 1
}
exit 0

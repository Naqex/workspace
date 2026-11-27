<#
.SYNOPSIS
    1-Touch Emergency Kill-Switch Guard with mandatory manual_halt_ack <= 10s check (B8, OrderSend = 0).

.DESCRIPTION
    Fail-closed emergency halt orchestrator for Naqex MT5 EAs (`Naqex_Master_Prop7E_v103.ex5` /
    `Naqex_Master_Prop7E.ex5` / `Naqex_AccountOrchestrator.ex5`):
      1. Pre-checks preset (`.set`) and heartbeat JSON to verify `InpAllowManualHaltFile=true` capability.
         If explicitly disabled (`false`), IMMEDIATELY escalates RED (exit 2) instead of silently failing.
      2. Atomically writes `naqex_manual_halt.flag` (`FLATTEN_ALL` or `HALT_NEW_ENTRIES`; skipped in `-DryRun`/`-WhatIf`).
      3. Polls `naqex_master_v103_heartbeat.json` (primary) / `naqex_heartbeat.json` (fallback) for
         `manual_halt_ack == true` within <= 10 seconds (hard-capped at 10s).
      4. If `manual_halt_ack != true` within <= 10s (EA frozen, MT5 crashed, disconnected, or legacy
         `InpAllowManualHaltFile=false`), immediately returns exit code 2 + CRITICAL RED ESCALATION
         instructing manual flatten via MT5 Mobile / MT5 Desktop AlgoTrading OFF button.
    NEVER calls OrderSend. Complements `naqex_mt5_watchdog.ps1` and `node_ctl.py`.

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File .\emergency_killswitch_guard.ps1 -Mt5FilesDir C:\Naqex\mt5\MQL5\Files -Action FLATTEN_ALL -DryRun
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$Mt5FilesDir = "C:\Naqex\mt5\MQL5\Files",

    [ValidateSet("FLATTEN_ALL", "HALT_NEW_ENTRIES", "RESET_NORMAL")]
    [string]$Action = "FLATTEN_ALL",

    [string]$Reason = "EMERGENCY_MANUAL_HALT",
    [string]$PresetPath = "",
    [string]$HeartbeatFileName = "",
    [string]$FlagFileName = "naqex_manual_halt.flag",
    [int]$AckTimeoutSec = 10,
    [int]$PollIntervalMs = 250,
    [int]$MaxHeartbeatAgeSec = 180,
    [long]$NowUtcOverride = 0,
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$SchemaVersion = "naqex-emergency-killswitch-guard-v3"
$InvCulture = [System.Globalization.CultureInfo]::InvariantCulture
$IsDryRun = [bool]$DryRun -or [bool]$WhatIfPreference
$MaxAllowedAckTimeoutSec = 10

$ReusedOpsTools = @(
    "tooling/ai-engines/ops_cloud/node_ctl.py",
    "tooling/ai-engines/ops_cloud/node_weekly_digest.py",
    "tooling/ai-engines/exports/deployment_kit/ops_watchdog/naqex_mt5_watchdog.ps1",
    "tooling/ai-engines/cockpit/modules/telemetry.py"
)

$ImmediateManualSteps = @(
    "STEP 1 (< 60s): Open MT5 Mobile App on 4G/5G immediately -> check Trade tab -> manually close ALL open positions and delete ALL pending orders.",
    "STEP 2 (< 120s): Connect to naqex-node1 via RDP over <LAN_SUBNET> or Tailscale (<TAILSCALE_IP>) and toggle MT5 'Algo Trading' button OFF (RED icon).",
    "STEP 3 (< 180s): Confirm 0 open positions in FTMO Client Area / Account MetriX before 20:50 UTC (03:50 ICT) swap=0 hard-flat cutoff.",
    "STEP 4 (Diagnostics): Run 'python tooling/ai-engines/ops_cloud/node_ctl.py status' and 'node_ctl.py logs --scope mql5 --errors-only' + 'naqex_mt5_watchdog.ps1'."
)

function Get-ObjProp {
    param($Obj, [string]$Name, $Default = $null)
    if ($null -eq $Obj) { return $Default }
    if ($Obj -is [System.Collections.IDictionary]) {
        if ($Obj.Contains($Name)) { return $Obj[$Name] }
        return $Default
    }
    $p = $Obj.PSObject.Properties[$Name]
    if ($null -ne $p) { return $p.Value }
    return $Default
}

function ConvertTo-StrictBool {
    param(
        $Value,
        [switch]$NativeBoolOnly
    )
    if ($null -eq $Value) { return $null }
    if ($Value -is [bool]) { return $Value }
    if ($NativeBoolOnly) { return $null }
    if ($Value -is [string]) {
        $s = $Value.Trim().ToLowerInvariant()
        if ($s -eq "true" -or $s -eq "1") { return $true }
        if ($s -eq "false" -or $s -eq "0" -or $s -eq "no") { return $false }
        return $null
    }
    if ($Value -is [int] -or $Value -is [long] -or $Value -is [int16] -or $Value -is [byte]) {
        if ($Value -eq 1) { return $true }
        if ($Value -eq 0) { return $false }
        return $null
    }
    return $null
}

function ConvertTo-StrictInt {
    param($Value)
    if ($null -eq $Value -or $Value -is [bool]) { return $null }
    if ($Value -is [int] -or $Value -is [long] -or $Value -is [int16] -or $Value -is [byte]) {
        return [long]$Value
    }
    if ($Value -is [double] -or $Value -is [decimal]) {
        $dbl = [double]$Value
        if ([double]::IsNaN($dbl) -or [double]::IsInfinity($dbl)) { return $null }
        $trunc = [math]::Truncate($dbl)
        if ($trunc -eq $dbl) { return [long]$trunc }
        return $null
    }
    return $null
}

function ConvertTo-SanitizedText {
    param([string]$Text)
    if ($null -eq $Text) { return "" }
    $out = $Text
    $out = [regex]::Replace($out, '(?i)https?://[^\s"''<>]+', '[REDACTED_URL]')
    $out = [regex]::Replace($out, '(?i)\b(password|passwd|token|api[_-]?key|secret|webhook)\s*[:=]\s*\S+', '$1=[REDACTED]')
    $out = [regex]::Replace($out, '\b(?!100\.64\.0\.0/10\b)(?:\d{1,3}\.){3}\d{1,3}\b', '[REDACTED_IP]')
    $out = [regex]::Replace($out, '(?i)[A-Z]:\\Users\\[^\\/\s"'']+', 'C:\Users\<USER>')
    $out = $out.Replace('$', 'USD ')
    return $out
}

function Read-TextSharedAutoEncoding {
    param([string]$Path)
    $fs = [System.IO.File]::Open($Path, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
    try {
        $ms = New-Object System.IO.MemoryStream
        try {
            $fs.CopyTo($ms)
            $raw = $ms.ToArray()
        } finally {
            $ms.Dispose()
        }
    } finally {
        $fs.Dispose()
    }
    if ($raw.Length -eq 0) { return "" }
    if ($raw.Length -ge 2 -and $raw[0] -eq 0xFF -and $raw[1] -eq 0xFE) {
        return [System.Text.Encoding]::Unicode.GetString($raw, 2, $raw.Length - 2)
    }
    $scanLen = [math]::Min(200, $raw.Length)
    $hasNull = $false
    for ($i = 0; $i -lt $scanLen; $i++) {
        if ($raw[$i] -eq 0) { $hasNull = $true; break }
    }
    if ($hasNull) {
        return [System.Text.Encoding]::Unicode.GetString($raw)
    }
    return [System.Text.Encoding]::UTF8.GetString($raw)
}

function Parse-PresetManualHaltCapability {
    param([string]$Path)
    $res = [ordered]@{
        preset_checked        = $false
        preset_exists         = $false
        allow_manual_halt_raw = $null
        allow_manual_halt     = $null
        manual_halt_file      = $null
    }
    if ([string]::IsNullOrWhiteSpace($Path)) { return $res }
    $res.preset_checked = $true
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        return $res
    }
    $res.preset_exists = $true
    $txt = Read-TextSharedAutoEncoding -Path $Path
    foreach ($line in ($txt -split "`r?`n")) {
        $s = $line.Trim()
        if ($s -match '(?i)^InpAllowManualHaltFile\s*=\s*([^|;\r\n]+)') {
            $rawVal = $Matches[1].Trim()
            $res.allow_manual_halt_raw = $rawVal
            if ($rawVal -ieq "true" -or $rawVal -eq "1") {
                $res.allow_manual_halt = $true
            } elseif ($rawVal -ieq "false" -or $rawVal -eq "0") {
                $res.allow_manual_halt = $false
            }
        }
        if ($s -match '(?i)^InpManualHaltFile\s*=\s*([^|;\r\n]+)') {
            $res.manual_halt_file = $Matches[1].Trim()
        }
    }
    return $res
}

function Resolve-HeartbeatCandidates {
    param([string]$FilesDir, [string]$ExplicitName)
    if (-not [string]::IsNullOrWhiteSpace($ExplicitName)) {
        return @((Join-Path $FilesDir $ExplicitName))
    }
    return @(
        (Join-Path $FilesDir "naqex_master_v103_heartbeat.json"),
        (Join-Path $FilesDir "naqex_heartbeat.json")
    )
}

function Read-ActiveHeartbeat {
    param([string[]]$CandidatePaths, [long]$NowTs, [int]$MaxAgeSec)
    $selectedPath = ""
    foreach ($cand in $CandidatePaths) {
        if (Test-Path -LiteralPath $cand -PathType Leaf) {
            $selectedPath = $cand
            break
        }
    }
    if ([string]::IsNullOrWhiteSpace($selectedPath)) {
        return [ordered]@{
            found                      = $false
            file_name                  = ""
            parse_ok                   = $false
            fresh                      = $false
            utc_ts                     = $null
            age_sec                    = $null
            terminal_connected         = $null
            terminal_connected_invalid = $false
            manual_halt                = $null
            manual_halt_ack            = $null
            allow_manual_halt          = $null
            open_positions             = $null
            regime                     = $null
            error                      = "HEARTBEAT_FILE_NOT_FOUND"
        }
    }
    try {
        $raw = Read-TextSharedAutoEncoding -Path $selectedPath
        $hb = $raw | ConvertFrom-Json
        $hbTsRaw = Get-ObjProp -Obj $hb -Name "utc_ts" -Default $null
        $hbTs = ConvertTo-StrictInt -Value $hbTsRaw
        $age = if ($null -ne $hbTs -and $hbTs -gt 0) { $NowTs - $hbTs } else { $null }
        $isFresh = ($null -ne $age) -and ($age -ge -60) -and ($age -le $MaxAgeSec)
        $termRaw = Get-ObjProp -Obj $hb -Name "terminal_connected" -Default $null
        $termConn = ConvertTo-StrictBool -Value $termRaw
        $termInvalid = ($null -ne $termRaw) -and ($null -eq $termConn)
        $mhRaw = Get-ObjProp -Obj $hb -Name "manual_halt" -Default $null
        $ackRaw = Get-ObjProp -Obj $hb -Name "manual_halt_ack" -Default $null
        $capRaw = Get-ObjProp -Obj $hb -Name "allow_manual_halt_file" -Default $null
        $openRaw = Get-ObjProp -Obj $hb -Name "open_positions" -Default $null
        $openPos = ConvertTo-StrictInt -Value $openRaw
        $regRaw = Get-ObjProp -Obj $hb -Name "regime" -Default $null
        return [ordered]@{
            found                      = $true
            file_name                  = (Split-Path -Leaf $selectedPath)
            parse_ok                   = $true
            fresh                      = $isFresh
            utc_ts                     = $hbTs
            age_sec                    = $age
            terminal_connected         = $termConn
            terminal_connected_invalid = $termInvalid
            manual_halt                = ConvertTo-StrictBool -Value $mhRaw
            manual_halt_ack            = ConvertTo-StrictBool -Value $ackRaw -NativeBoolOnly
            allow_manual_halt          = ConvertTo-StrictBool -Value $capRaw
            open_positions             = $openPos
            regime                     = if ($null -ne $regRaw) { [string]$regRaw } else { $null }
            error                      = ""
        }
    } catch {
        return [ordered]@{
            found                      = $true
            file_name                  = (Split-Path -Leaf $selectedPath)
            parse_ok                   = $false
            fresh                      = $false
            utc_ts                     = $null
            age_sec                    = $null
            terminal_connected         = $null
            terminal_connected_invalid = $false
            manual_halt                = $null
            manual_halt_ack            = $null
            allow_manual_halt          = $null
            open_positions             = $null
            regime                     = $null
            error                      = ("HEARTBEAT_PARSE_ERROR:" + $_.Exception.Message)
        }
    }
}

function Write-FlagAtomic {
    param([string]$TargetPath, [string]$Content)
    $dir = Split-Path -Parent $TargetPath
    if (-not (Test-Path -LiteralPath $dir -PathType Container)) {
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
    }
    $stamp = [DateTimeOffset]::UtcNow.Ticks
    $tmpPath = "$TargetPath.tmp.$PID.$stamp"
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($tmpPath, $Content, $utf8NoBom)
    Move-Item -LiteralPath $tmpPath -Destination $TargetPath -Force
}

function Emit-EscalationAndExit {
    param(
        [string]$ReasonCode,
        [string]$Message,
        [hashtable]$Details
    )
    $payload = [ordered]@{
        schema                 = $SchemaVersion
        checked_utc            = [DateTimeOffset]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ", $InvCulture)
        dry_run                = $IsDryRun
        order_send_count       = 0
        action                 = $Action
        verdict                = "CRITICAL_RED_ESCALATION"
        escalation_required    = $true
        reason_code            = $ReasonCode
        message                = $Message
        immediate_manual_steps = $ImmediateManualSteps
        reused_ops_tools       = $ReusedOpsTools
    }
    foreach ($k in $Details.Keys) {
        $payload[$k] = $Details[$k]
    }
    Write-Output (ConvertTo-SanitizedText -Text ($payload | ConvertTo-Json -Depth 6))
    exit 2
}

# Hard-cap ACK timeout strictly to <= 10s (B8 invariant)
$AckTimeoutClamped = $false
$EffectiveAckTimeoutSec = $AckTimeoutSec
if ($EffectiveAckTimeoutSec -gt $MaxAllowedAckTimeoutSec) {
    $EffectiveAckTimeoutSec = $MaxAllowedAckTimeoutSec
    $AckTimeoutClamped = $true
} elseif ($EffectiveAckTimeoutSec -lt 1) {
    $EffectiveAckTimeoutSec = 1
    $AckTimeoutClamped = $true
}
$EffectivePollMs = [math]::Max(50, [math]::Min(1000, $PollIntervalMs))

$NowUtcTs = if ($NowUtcOverride -gt 0) { $NowUtcOverride } else { [DateTimeOffset]::UtcNow.ToUnixTimeSeconds() }
$NowUtcIso = [DateTimeOffset]::FromUnixTimeSeconds($NowUtcTs).UtcDateTime.ToString("yyyy-MM-ddTHH:mm:ssZ", $InvCulture)

# STEP 1: Check preset & initial heartbeat capability (InpAllowManualHaltFile=true)
$PresetCap = Parse-PresetManualHaltCapability -Path $PresetPath
$EffectiveFlagName = if (-not [string]::IsNullOrWhiteSpace([string]$PresetCap.manual_halt_file)) {
    [string]$PresetCap.manual_halt_file
} else {
    $FlagFileName
}
$FlagPath = Join-Path $Mt5FilesDir $EffectiveFlagName
$HbCandidates = Resolve-HeartbeatCandidates -FilesDir $Mt5FilesDir -ExplicitName $HeartbeatFileName
$InitialHb = Read-ActiveHeartbeat -CandidatePaths $HbCandidates -NowTs $NowUtcTs -MaxAgeSec $MaxHeartbeatAgeSec

$CapabilityStatus = "UNCONFIRMED_PENDING_HEARTBEAT_ACK"
if ($PresetCap.preset_checked -and (-not $PresetCap.preset_exists)) {
    Emit-EscalationAndExit -ReasonCode "PRESET_FILE_NOT_FOUND" -Message "Preset path specified for InpAllowManualHaltFile verification was not found; cannot verify kill-switch capability." -Details @{
        ack_timeout_sec        = $EffectiveAckTimeoutSec
        ack_timeout_clamped    = $AckTimeoutClamped
        manual_halt_ack        = $false
        flag_written           = $false
        capability_status      = "PRESET_MISSING"
        preset_capability      = $PresetCap
        heartbeat              = $InitialHb
        elapsed_sec            = 0.0
    }
}
if ($PresetCap.allow_manual_halt -eq $false) {
    Emit-EscalationAndExit -ReasonCode "CAPABILITY_DISABLED_IN_PRESET" -Message "Preset has InpAllowManualHaltFile=false: EA will IGNORE naqex_manual_halt.flag! Flatten manually via MT5 Mobile / AlgoTrading OFF immediately." -Details @{
        ack_timeout_sec        = $EffectiveAckTimeoutSec
        ack_timeout_clamped    = $AckTimeoutClamped
        manual_halt_ack        = $false
        flag_written           = $false
        capability_status      = "DISABLED_IN_PRESET"
        preset_capability      = $PresetCap
        heartbeat              = $InitialHb
        elapsed_sec            = 0.0
    }
}
if ($InitialHb.allow_manual_halt -eq $false) {
    Emit-EscalationAndExit -ReasonCode "CAPABILITY_DISABLED_IN_HEARTBEAT" -Message "Heartbeat reports allow_manual_halt_file=false: EA will IGNORE naqex_manual_halt.flag! Flatten manually via MT5 Mobile / AlgoTrading OFF immediately." -Details @{
        ack_timeout_sec        = $EffectiveAckTimeoutSec
        ack_timeout_clamped    = $AckTimeoutClamped
        manual_halt_ack        = $false
        flag_written           = $false
        capability_status      = "DISABLED_IN_HEARTBEAT"
        preset_capability      = $PresetCap
        heartbeat              = $InitialHb
        elapsed_sec            = 0.0
    }
}
if ($PresetCap.allow_manual_halt -eq $true -or $InitialHb.allow_manual_halt -eq $true) {
    $CapabilityStatus = "CONFIRMED_TRUE"
}

# STEP 2: Atomic write (or remove on RESET_NORMAL) of naqex_manual_halt.flag
$CleanReason = ($Reason -replace '[\r\n|]', '_').Trim()
if ([string]::IsNullOrWhiteSpace($CleanReason)) { $CleanReason = "EMERGENCY_MANUAL_HALT" }
$FlagPayload = "$Action|$NowUtcIso|$CleanReason`n"
$FlagWritten = $false
$FlagWriteUtcTs = $null

if (-not $IsDryRun) {
    $FlagWriteUtcTs = if ($NowUtcOverride -gt 0) {
        $NowUtcOverride
    } else {
        [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
    }
    if ($Action -eq "RESET_NORMAL") {
        if (Test-Path -LiteralPath $FlagPath -PathType Leaf) {
            Remove-Item -LiteralPath $FlagPath -Force
        }
        $FlagWritten = $true
    } else {
        Write-FlagAtomic -TargetPath $FlagPath -Content $FlagPayload
        $FlagWritten = $true
    }
}

# STEP 3: Mandatory heartbeat poll for fresh post-write manual_halt_ack within <= 10 seconds
$ExpectedAck = ($Action -ne "RESET_NORMAL")
$Stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
$AckConfirmed = $false
$PollCount = 0
$LatestHb = $InitialHb
$FailReasonCode = "ACK_TIMEOUT_EA_FROZEN_OR_DISABLED"
$FailMessage = "manual_halt_ack did not become $ExpectedAck within ${EffectiveAckTimeoutSec}s (EA frozen, MT5 crashed, or InpAllowManualHaltFile=false). Flatten manually via MT5 Mobile / AlgoTrading OFF immediately!"

while ($true) {
    $PollCount++
    $PollNowTs = if ($NowUtcOverride -gt 0) {
        $NowUtcOverride + [long][math]::Floor($Stopwatch.Elapsed.TotalSeconds)
    } else {
        [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
    }
    $LatestHb = Read-ActiveHeartbeat -CandidatePaths $HbCandidates -NowTs $PollNowTs -MaxAgeSec $MaxHeartbeatAgeSec

    if (-not $LatestHb.found) {
        $FailReasonCode = "HEARTBEAT_MISSING_MT5_DOWN"
        $FailMessage = "Heartbeat JSON not found (MT5 crashed or not running). Flatten manually via MT5 Mobile immediately!"
    } elseif (-not $LatestHb.parse_ok) {
        $FailReasonCode = "HEARTBEAT_CORRUPT_OR_LOCKED"
        $FailMessage = "Heartbeat JSON unreadable. Flatten manually via MT5 Mobile / AlgoTrading OFF immediately!"
    } elseif (-not $LatestHb.fresh) {
        $FailReasonCode = "HEARTBEAT_STALE_EA_FROZEN"
        $FailMessage = "Heartbeat is stale (age=$($LatestHb.age_sec)s > ${MaxHeartbeatAgeSec}s): EA/MT5 likely frozen. Flatten manually via MT5 Mobile immediately!"
    } elseif ($Action -eq "FLATTEN_ALL" -and ($LatestHb.terminal_connected -eq $false -or $LatestHb.terminal_connected_invalid)) {
        $FailReasonCode = "BROKER_DISCONNECTED_CANNOT_FLATTEN"
        $FailMessage = "MT5 terminal_connected=false or invalid during FLATTEN_ALL: EA cannot close broker positions! Close ALL positions manually via MT5 Mobile on 4G/5G immediately!"
    } elseif (($null -ne $FlagWriteUtcTs) -and (($null -eq $LatestHb.utc_ts) -or ($LatestHb.utc_ts -lt $FlagWriteUtcTs))) {
        $FailReasonCode = "ACK_STALE_PRE_WRITE_HEARTBEAT"
        $FailMessage = "Heartbeat utc_ts=$($LatestHb.utc_ts) predates flag_write_utc_ts=${FlagWriteUtcTs}: EA has NOT published a post-write heartbeat (frozen or unresponsive). Flatten manually via MT5 Mobile / AlgoTrading OFF immediately!"
    } elseif ($LatestHb.manual_halt_ack -ne $ExpectedAck) {
        $FailReasonCode = "ACK_TIMEOUT_MANUAL_HALT_UNCONFIRMED"
        $FailMessage = "manual_halt_ack remained $($LatestHb.manual_halt_ack) after ${EffectiveAckTimeoutSec}s (EA frozen, MT5 crashed, invalid non-boolean ACK, or legacy InpAllowManualHaltFile=false). Flatten manually via MT5 Mobile / AlgoTrading OFF immediately!"
    } elseif ($Action -eq "FLATTEN_ALL" -and (($null -eq $LatestHb.open_positions) -or ($LatestHb.open_positions -ne 0))) {
        $FailReasonCode = "FLATTEN_INCOMPLETE_POSITIONS_REMAIN"
        $FailMessage = "Action=FLATTEN_ALL requires open_positions=0, but heartbeat reports open_positions=$($LatestHb.open_positions) after ${EffectiveAckTimeoutSec}s. Close ALL open positions manually via MT5 Mobile immediately!"
    } else {
        $AckConfirmed = $true
        break
    }

    if ($Stopwatch.Elapsed.TotalSeconds -ge [double]$EffectiveAckTimeoutSec) {
        break
    }
    $remainingMs = [int](([double]$EffectiveAckTimeoutSec - $Stopwatch.Elapsed.TotalSeconds) * 1000.0)
    if ($remainingMs -le 0) { break }
    $sleepMs = [math]::Min($EffectivePollMs, $remainingMs)
    Start-Sleep -Milliseconds $sleepMs
}

$Stopwatch.Stop()
$ElapsedSec = [math]::Round($Stopwatch.Elapsed.TotalSeconds, 3)

if (-not $AckConfirmed) {
    Emit-EscalationAndExit -ReasonCode $FailReasonCode -Message $FailMessage -Details @{
        ack_timeout_sec        = $EffectiveAckTimeoutSec
        ack_timeout_clamped    = $AckTimeoutClamped
        poll_count             = $PollCount
        elapsed_sec            = $ElapsedSec
        flag_file_name         = $EffectiveFlagName
        flag_written           = $FlagWritten
        flag_write_utc_ts      = $FlagWriteUtcTs
        planned_flag_payload   = $FlagPayload.Trim()
        capability_status      = $CapabilityStatus
        preset_capability      = $PresetCap
        manual_halt_ack        = $false
        heartbeat              = $LatestHb
    }
}

$OkVerdict = if ($IsDryRun) { "DRYRUN_ACK_CONFIRMED" } else { "GREEN_HALT_ACK_CONFIRMED" }
$OkPayload = [ordered]@{
    schema                 = $SchemaVersion
    checked_utc            = [DateTimeOffset]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ", $InvCulture)
    dry_run                = $IsDryRun
    order_send_count       = 0
    action                 = $Action
    verdict                = $OkVerdict
    escalation_required    = $false
    ack_timeout_sec        = $EffectiveAckTimeoutSec
    ack_timeout_clamped    = $AckTimeoutClamped
    poll_count             = $PollCount
    elapsed_sec            = $ElapsedSec
    flag_file_name         = $EffectiveFlagName
    flag_written           = $FlagWritten
    flag_write_utc_ts      = $FlagWriteUtcTs
    planned_flag_payload   = $FlagPayload.Trim()
    capability_status      = $CapabilityStatus
    preset_capability      = $PresetCap
    manual_halt_ack        = [bool]$LatestHb.manual_halt_ack
    heartbeat              = $LatestHb
    reused_ops_tools       = $ReusedOpsTools
}

Write-Output (ConvertTo-SanitizedText -Text ($OkPayload | ConvertTo-Json -Depth 6))
exit 0

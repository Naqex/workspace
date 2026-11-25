<#
.SYNOPSIS
    Fail-Closed Flat-Only .ex5 & Red-News CSV Updater (never overwrites EAs or news CSV while positions are open!).

.DESCRIPTION
    Checks `MQL5\Files\naqex_heartbeat.json` inside a target MT5 sandbox/VPS directory.
    REFUSES (exit code 2) to copy updated `.ex5` binaries or `naqex_red_news_utc.csv`
    if `open_positions > 0`. Verifies SHA-256 checksums for all 9 `.ex5` binaries and the
    4-currency `naqex_red_news_utc.csv` calendar after copy. Safe to run with `-DryRun` at any time.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\sync_updated_ex5_when_flat.ps1 -TargetMt5Root D:\ANNAM\TradingWorkspace\.runtime\ftmo-demo-portable-1515343166 -DryRun
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$TargetMt5Root,

    [string]$Ex5SourceDir = "",
    [string]$RedNewsCsvPath = "",
    [string]$ManifestFilePath = "",
    [long]$ExpectedLogin = 0,
    [string]$ExpectedServer = "",
    [int]$MaxHeartbeatAgeSec = 180,
    [long]$NowUtcOverride = 0,
    [switch]$IncludeMasterEx5,
    [switch]$RequireManualHaltAck,
    [switch]$RequireManifest,
    [switch]$DryRun,
    [switch]$ForceWhenHeartbeatMissing
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RequiredEx5Names = @(
    "Naqex_AccountOrchestrator.ex5",
    "Naqex_WB_EXP080_USDJPY.ex5",
    "Naqex_WB_EXP080_VOLHIGH_GBPUSD.ex5",
    "Naqex_WB_FX_USD_BASKET_12U_Z35.ex5",
    "Naqex_WB_IDX_RS_US100_LEAD_1130.ex5",
    "Naqex_WB_NY_RISK_FLOW_10ET_USDJPY.ex5",
    "Naqex_WB_SESS_CONT_BRK40_US100.ex5",
    "Naqex_WB_TOKYO_BOX_USDJPY.ex5",
    "Naqex_WB_VOLCOMP_EXP75_EURJPY.ex5"
)
if ($IncludeMasterEx5) {
    $RequiredEx5Names += "Naqex_Master_Prop7E.ex5"
}

function Get-AncestorPath {
    param([string]$StartPath, [int]$Levels)
    $cur = $StartPath
    for ($i = 0; $i -lt $Levels; $i++) {
        if ([string]::IsNullOrWhiteSpace($cur)) { return "" }
        $next = Split-Path -Parent $cur
        if ([string]::IsNullOrWhiteSpace($next) -or $next -eq $cur) { return "" }
        $cur = $next
    }
    return $cur
}

$KitRoot = Get-AncestorPath -StartPath $PSScriptRoot -Levels 1
$ExportsDir = Get-AncestorPath -StartPath $PSScriptRoot -Levels 2
$RepoRoot = Get-AncestorPath -StartPath $PSScriptRoot -Levels 5
$ManifestPath = if (-not [string]::IsNullOrWhiteSpace($ManifestFilePath)) {
    $ManifestFilePath
} elseif ($KitRoot) {
    Join-Path $KitRoot "manifest.sha256.json"
} else {
    ""
}
$DefaultCompiledDir = if ($RepoRoot) { Join-Path $RepoRoot ".runtime\mt5-compiled-ex5" } else { "" }
$ResolvedEx5Dir = if (-not [string]::IsNullOrWhiteSpace($Ex5SourceDir)) {
    $Ex5SourceDir
} elseif ($DefaultCompiledDir -and (Test-Path -LiteralPath $DefaultCompiledDir)) {
    $DefaultCompiledDir
} else {
    $ExportsDir
}
$ResolvedCsvPath = if (-not [string]::IsNullOrWhiteSpace($RedNewsCsvPath)) {
    $RedNewsCsvPath
} elseif ($ExportsDir) {
    Join-Path $ExportsDir "Files\naqex_red_news_utc.csv"
} else {
    ""
}
$HbPath = Join-Path $TargetMt5Root "MQL5\Files\naqex_heartbeat.json"
$NowUtcTs = if ($NowUtcOverride -gt 0) { $NowUtcOverride } else { [DateTimeOffset]::UtcNow.ToUnixTimeSeconds() }

function Emit-BlockedAndExit {
    param([string]$StatusCode, [string]$Message, [hashtable]$Extra = @{}, [bool]$IsDryRun = $false)
    $obj = [ordered]@{
        schema     = "naqex-ex5-flat-sync-v2"
        status     = $StatusCode
        dry_run    = $IsDryRun
        order_send = 0
        message    = $Message
    }
    foreach ($k in $Extra.Keys) { $obj[$k] = $Extra[$k] }
    Write-Output ($obj | ConvertTo-Json -Depth 4)
    exit 2
}

function Assert-FlatAndFreshHeartbeat {
    param(
        [string]$Path, [long]$NowTs, [int]$MaxAgeSec,
        [bool]$AllowMissing, [bool]$IsDryRun,
        [long]$ExpLogin, [string]$ExpServer, [bool]$NeedHaltAck
    )
    if (-not (Test-Path -LiteralPath $Path)) {
        if ($AllowMissing) { return @{ open_positions = 0; utc_ts = 0; account_login = 0 } }
        throw "HEARTBEAT_MISSING_FAIL_CLOSED: $Path not found. Pass -ForceWhenHeartbeatMissing only if terminal is verified offline."
    }
    $hb = Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
    $hbProps = $hb.PSObject.Properties.Name

    # R2-03 CRITICAL: NEVER allow sync when broker is disconnected or positions_state is UNKNOWN!
    if (-not ($hbProps -contains "terminal_connected") -or (-not [bool]$hb.terminal_connected)) {
        Emit-BlockedAndExit -StatusCode "BLOCKED_BROKER_DISCONNECTED" -Message "Refused fail-closed: terminal_connected is false or missing (broker positions unknown while offline)." -Extra @{ heartbeat_path = $Path } -IsDryRun:$IsDryRun
    }
    if ($hbProps -contains "positions_state") {
        $ps = ([string]$hb.positions_state).ToUpperInvariant()
        if ($ps -ne "CONFIRMED") {
            Emit-BlockedAndExit -StatusCode "BLOCKED_POSITIONS_UNKNOWN" -Message "Refused fail-closed: positions_state='$ps' != CONFIRMED." -Extra @{ heartbeat_path = $Path; positions_state = $ps } -IsDryRun:$IsDryRun
        }
    }
    if ($ExpLogin -gt 0) {
        $gotLogin = if ($hbProps -contains "account_login") { [long]$hb.account_login } else { 0 }
        if ($gotLogin -ne $ExpLogin) {
            Emit-BlockedAndExit -StatusCode "BLOCKED_ACCOUNT_MISMATCH" -Message "Refused fail-closed: account_login=$gotLogin != expected $ExpLogin." -Extra @{ account_login = $gotLogin; expected_login = $ExpLogin } -IsDryRun:$IsDryRun
        }
    }
    if (-not [string]::IsNullOrWhiteSpace($ExpServer)) {
        $gotSrv = if ($hbProps -contains "account_server") { [string]$hb.account_server } else { "" }
        if ($gotSrv -ne $ExpServer) {
            Emit-BlockedAndExit -StatusCode "BLOCKED_SERVER_MISMATCH" -Message "Refused fail-closed: account_server='$gotSrv' != expected '$ExpServer'." -Extra @{ account_server = $gotSrv; expected_server = $ExpServer } -IsDryRun:$IsDryRun
        }
    }
    if ($NeedHaltAck) {
        $ack = ($hbProps -contains "manual_halt_ack" -and [bool]$hb.manual_halt_ack) -or ($hbProps -contains "manual_halt" -and [bool]$hb.manual_halt)
        if (-not $ack) {
            Emit-BlockedAndExit -StatusCode "BLOCKED_MANUAL_HALT_UNCONFIRMED" -Message "Refused fail-closed: manual_halt_ack is false (lock new entries before release sync)." -Extra @{ heartbeat_path = $Path } -IsDryRun:$IsDryRun
        }
    }

    $openPos = [int]$hb.open_positions
    $totalAcctPos = if ($hbProps -contains "total_account_positions") { [int]$hb.total_account_positions } else { $openPos }
    $pendingOrd = if ($hbProps -contains "pending_orders") { [int]$hb.pending_orders } else { 0 }
    $inFlightOrd = if ($hbProps -contains "in_flight_orders") { [int]$hb.in_flight_orders } else { 0 }

    if ($openPos -lt 0 -or $totalAcctPos -lt 0 -or $pendingOrd -lt 0 -or $inFlightOrd -lt 0) {
        Emit-BlockedAndExit -StatusCode "BLOCKED_POSITIONS_UNKNOWN" -Message "Refused fail-closed: negative position/order count signals unknown broker state." -Extra @{ open_positions = $openPos; total_account_positions = $totalAcctPos; pending_orders = $pendingOrd } -IsDryRun:$IsDryRun
    }
    if ($openPos -gt 0 -or $totalAcctPos -gt 0 -or $pendingOrd -gt 0 -or $inFlightOrd -gt 0) {
        Emit-BlockedAndExit -StatusCode "BLOCKED_OPEN_POSITIONS" -Message "Refused fail-closed: account not flat (open=$openPos total=$totalAcctPos pending=$pendingOrd in_flight=$inFlightOrd)." -Extra @{ open_positions = $openPos; total_account_positions = $totalAcctPos; pending_orders = $pendingOrd; in_flight_orders = $inFlightOrd; heartbeat_path = $Path } -IsDryRun:$IsDryRun
    }
    if (-not $AllowMissing) {
        if (-not ($hbProps -contains "utc_ts") -or [long]$hb.utc_ts -le 0) {
            Emit-BlockedAndExit -StatusCode "BLOCKED_STALE_HEARTBEAT" -Message "Refused fail-closed: heartbeat missing valid utc_ts." -Extra @{ heartbeat_path = $Path } -IsDryRun:$IsDryRun
        }
        $ageSec = $NowTs - [long]$hb.utc_ts
        if ($ageSec -gt $MaxAgeSec -or $ageSec -lt -60) {
            Emit-BlockedAndExit -StatusCode "BLOCKED_STALE_HEARTBEAT" -Message "Refused fail-closed: heartbeat age=${ageSec}s outside [-60, ${MaxAgeSec}]s." -Extra @{ heartbeat_age_s = $ageSec; max_age_s = $MaxAgeSec; heartbeat_path = $Path } -IsDryRun:$IsDryRun
        }
    }
    return @{
        open_positions = $openPos
        utc_ts         = if ($hbProps -contains "utc_ts") { [long]$hb.utc_ts } else { 0 }
        account_login  = if ($hbProps -contains "account_login") { [long]$hb.account_login } else { 0 }
    }
}

$HbSnap1 = Assert-FlatAndFreshHeartbeat -Path $HbPath -NowTs $NowUtcTs -MaxAgeSec $MaxHeartbeatAgeSec -AllowMissing:$ForceWhenHeartbeatMissing -IsDryRun:$DryRun -ExpLogin $ExpectedLogin -ExpServer $ExpectedServer -NeedHaltAck:$RequireManualHaltAck
$OpenPos = [int]$HbSnap1.open_positions

$Ex5Files = @()
foreach ($reqName in $RequiredEx5Names) {
    $fp = Join-Path $ResolvedEx5Dir $reqName
    if (-not (Test-Path -LiteralPath $fp)) {
        throw "MISSING_REQUIRED_EX5: $reqName not found in $ResolvedEx5Dir"
    }
    $Ex5Files += Get-Item -LiteralPath $fp
}

# R2-03: Always cross-verify source .ex5 AND red-news CSV hashes against manifest whenever manifest is available (or required!)
$ManifestHashes = @{}
$ManifestCsvHash = ""
if (-not [string]::IsNullOrWhiteSpace($ManifestPath) -and (Test-Path -LiteralPath $ManifestPath)) {
    $mObj = Get-Content -LiteralPath $ManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($mObj.compiled_ex5_files) {
        foreach ($prop in $mObj.compiled_ex5_files.PSObject.Properties) {
            $leaf = Split-Path -Leaf $prop.Name
            $ManifestHashes[$leaf] = ([string]$prop.Value.sha256).ToLowerInvariant()
        }
    }
    if ($mObj.external_dependencies) {
        foreach ($prop in $mObj.external_dependencies.PSObject.Properties) {
            if ($prop.Name -like "*naqex_red_news_utc.csv" -and $prop.Value.snapshot_sha256) {
                $ManifestCsvHash = ([string]$prop.Value.snapshot_sha256).ToLowerInvariant()
            }
        }
    }
} elseif ($RequireManifest) {
    throw "MANIFEST_REQUIRED_MISSING: manifest not found at '$ManifestPath'"
}

if (-not (Test-Path -LiteralPath $ResolvedCsvPath)) {
    throw "RED_NEWS_CSV_MISSING: $ResolvedCsvPath not found."
}
$CsvLines = @(Get-Content -LiteralPath $ResolvedCsvPath -Encoding UTF8 | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
if ($CsvLines.Count -lt 201 -or ($CsvLines[0].Trim() -notlike "utc_ts,ccy,event*")) {
    throw "RED_NEWS_CSV_INVALID: expected header 'utc_ts,ccy,event' and >= 200 rows in $ResolvedCsvPath (found $($CsvLines.Count) lines)."
}
$CsvRowCount = $CsvLines.Count - 1
$SrcCsvSha = (Get-FileHash -LiteralPath $ResolvedCsvPath -Algorithm SHA256).Hash.ToLowerInvariant()
if (-not [string]::IsNullOrWhiteSpace($ManifestCsvHash) -and $SrcCsvSha -ne $ManifestCsvHash) {
    throw "MANIFEST_CSV_SHA256_MISMATCH: naqex_red_news_utc.csv disk=$SrcCsvSha != manifest=$ManifestCsvHash"
}

# Detect whether target places Naqex EAs under MQL5\Experts\Naqex or directly under MQL5\Experts
$SubDir = Join-Path $TargetMt5Root "MQL5\Experts\Naqex"
$DestDir = if (Test-Path -LiteralPath $SubDir) { $SubDir } else { Join-Path $TargetMt5Root "MQL5\Experts" }
$DestFilesDir = Join-Path $TargetMt5Root "MQL5\Files"
$DestCsvPath = Join-Path $DestFilesDir "naqex_red_news_utc.csv"

# Pre-validate source hashes against manifest before touching destination
$Ex5Hashes = [ordered]@{}
$Updated = New-Object System.Collections.Generic.List[string]
foreach ($f in $Ex5Files) {
    $srcHash = (Get-FileHash -LiteralPath $f.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($ManifestHashes.ContainsKey($f.Name) -and $ManifestHashes[$f.Name] -ne $srcHash) {
        throw "MANIFEST_SHA256_MISMATCH: $($f.Name) disk=$srcHash != manifest=$($ManifestHashes[$f.Name])"
    }
    $Ex5Hashes[$f.Name] = $srcHash
    $Updated.Add($f.Name)
}

if (-not $DryRun) {
    # Re-check flat + connected + fresh right before writing (reduces TOCTOU window)
    $NowCheckTs = if ($NowUtcOverride -gt 0) { $NowUtcOverride } else { [DateTimeOffset]::UtcNow.ToUnixTimeSeconds() }
    $null = Assert-FlatAndFreshHeartbeat -Path $HbPath -NowTs $NowCheckTs -MaxAgeSec $MaxHeartbeatAgeSec -AllowMissing:$ForceWhenHeartbeatMissing -IsDryRun:$false -ExpLogin $ExpectedLogin -ExpServer $ExpectedServer -NeedHaltAck:$RequireManualHaltAck

    New-Item -ItemType Directory -Force -Path $DestDir | Out-Null
    New-Item -ItemType Directory -Force -Path $DestFilesDir | Out-Null
    $Stamp = [DateTimeOffset]::UtcNow.ToString("yyyyMMddTHHmmssZ")
    $RollbackDir = Join-Path $TargetMt5Root ".naqex_sync_rollback_$Stamp"
    $BackedUp = @()
    $NewlyCreated = @()
    try {
        foreach ($f in $Ex5Files) {
            $dst = Join-Path $DestDir $f.Name
            if (Test-Path -LiteralPath $dst) {
                New-Item -ItemType Directory -Force -Path $RollbackDir | Out-Null
                $bak = Join-Path $RollbackDir $f.Name
                $origHash = (Get-FileHash -LiteralPath $dst -Algorithm SHA256).Hash.ToLowerInvariant()
                Copy-Item -LiteralPath $dst -Destination $bak -Force
                $BackedUp += @{ Src = $bak; Dst = $dst; OrigHash = $origHash }
            } else {
                $NewlyCreated += $dst
            }
            Copy-Item -LiteralPath $f.FullName -Destination $dst -Force
            $dstHash = (Get-FileHash -LiteralPath $dst -Algorithm SHA256).Hash.ToLowerInvariant()
            if ($dstHash -ne $Ex5Hashes[$f.Name]) {
                throw "SHA256_MISMATCH_AFTER_COPY: $($f.Name) src=$($Ex5Hashes[$f.Name]) dst=$dstHash"
            }
        }
        if (Test-Path -LiteralPath $DestCsvPath) {
            New-Item -ItemType Directory -Force -Path $RollbackDir | Out-Null
            $bakCsv = Join-Path $RollbackDir "naqex_red_news_utc.csv"
            $origCsvHash = (Get-FileHash -LiteralPath $DestCsvPath -Algorithm SHA256).Hash.ToLowerInvariant()
            Copy-Item -LiteralPath $DestCsvPath -Destination $bakCsv -Force
            $BackedUp += @{ Src = $bakCsv; Dst = $DestCsvPath; OrigHash = $origCsvHash }
        } else {
            $NewlyCreated += $DestCsvPath
        }
        Copy-Item -LiteralPath $ResolvedCsvPath -Destination $DestCsvPath -Force
        $dstCsvSha = (Get-FileHash -LiteralPath $DestCsvPath -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($dstCsvSha -ne $SrcCsvSha) {
            throw "SHA256_MISMATCH_AFTER_COPY: naqex_red_news_utc.csv src=$SrcCsvSha dst=$dstCsvSha"
        }
        if (Test-Path -LiteralPath $RollbackDir) {
            Remove-Item -Recurse -Force -LiteralPath $RollbackDir -ErrorAction SilentlyContinue
        }
    } catch {
        $syncErr = $_
        $rbErrors = @()
        # R2-03: Strict rollback restores ALL overwritten files with SHA verification AND removes newly introduced files!
        foreach ($item in $BackedUp) {
            try {
                Copy-Item -LiteralPath $item.Src -Destination $item.Dst -Force
                $restoredHash = (Get-FileHash -LiteralPath $item.Dst -Algorithm SHA256).Hash.ToLowerInvariant()
                if ($restoredHash -ne $item.OrigHash) {
                    $rbErrors += "Restore SHA mismatch on $($item.Dst)"
                }
            } catch {
                $rbErrors += "Restore failed on $($item.Dst): $($_.Exception.Message)"
            }
        }
        foreach ($newDst in $NewlyCreated) {
            if (Test-Path -LiteralPath $newDst) {
                try { Remove-Item -Force -LiteralPath $newDst } catch { $rbErrors += "Failed removing new file ${newDst}: $($_.Exception.Message)" }
            }
        }
        if ($rbErrors.Count -gt 0) {
            throw "SYNC_AND_ROLLBACK_ERROR: $($syncErr.Exception.Message) | RollbackErrors: $($rbErrors -join '; ')"
        }
        throw $syncErr
    }
}

$res = [ordered]@{
    schema           = "naqex-ex5-flat-sync-v2"
    status           = if ($DryRun) { "DRYRUN_READY_FLAT" } else { "SYNCED_CLEAN_FLAT" }
    open_positions   = $OpenPos
    dest_dir         = $DestDir
    files_count      = $Updated.Count
    files            = @($Updated)
    ex5_sha256       = $Ex5Hashes
    manifest_checked = ($ManifestHashes.Count -gt 0)
    red_news_csv     = [ordered]@{
        source          = $ResolvedCsvPath
        dest            = $DestCsvPath
        rows            = $CsvRowCount
        sha256          = $SrcCsvSha
        synced          = (-not [bool]$DryRun)
        sha256_verified = $true
    }
    sha256_verified  = $true
    order_send       = 0
}
Write-Output ($res | ConvertTo-Json -Depth 5)
exit 0

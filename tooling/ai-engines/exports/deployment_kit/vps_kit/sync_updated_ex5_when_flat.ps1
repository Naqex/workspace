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
    [int]$MaxHeartbeatAgeSec = 180,
    [long]$NowUtcOverride = 0,
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
$ManifestPath = if ($KitRoot) { Join-Path $KitRoot "manifest.sha256.json" } else { "" }
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

function Assert-FlatAndFreshHeartbeat {
    param([string]$Path, [long]$NowTs, [int]$MaxAgeSec, [bool]$AllowMissing, [bool]$IsDryRun)
    if (-not (Test-Path -LiteralPath $Path)) {
        if ($AllowMissing) { return 0 }
        throw "HEARTBEAT_MISSING_FAIL_CLOSED: $Path not found. Pass -ForceWhenHeartbeatMissing only if terminal is verified offline."
    }
    $hb = Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
    $hbProps = $hb.PSObject.Properties.Name
    $openPos = [int]$hb.open_positions
    if ($openPos -gt 0) {
        $blocked = [ordered]@{
            schema         = "naqex-ex5-flat-sync-v1"
            status         = "BLOCKED_OPEN_POSITIONS"
            open_positions = $openPos
            heartbeat_path = $Path
            dry_run        = $IsDryRun
            order_send     = 0
            message        = "Refused fail-closed: terminal currently has $openPos open position(s). Retry once flat (open_positions == 0)."
        }
        Write-Output ($blocked | ConvertTo-Json -Depth 4)
        exit 2
    }
    if (-not $AllowMissing) {
        if (-not ($hbProps -contains "utc_ts") -or [long]$hb.utc_ts -le 0) {
            $blocked = [ordered]@{
                schema         = "naqex-ex5-flat-sync-v1"
                status         = "BLOCKED_STALE_HEARTBEAT"
                heartbeat_path = $Path
                dry_run        = $IsDryRun
                order_send     = 0
                message        = "Refused fail-closed: heartbeat missing valid utc_ts."
            }
            Write-Output ($blocked | ConvertTo-Json -Depth 4)
            exit 2
        }
        $ageSec = $NowTs - [long]$hb.utc_ts
        if ($ageSec -gt $MaxAgeSec -or $ageSec -lt -60) {
            $blocked = [ordered]@{
                schema          = "naqex-ex5-flat-sync-v1"
                status          = "BLOCKED_STALE_HEARTBEAT"
                heartbeat_age_s = $ageSec
                max_age_s       = $MaxAgeSec
                heartbeat_path  = $Path
                dry_run         = $IsDryRun
                order_send      = 0
                message         = "Refused fail-closed: heartbeat age=${ageSec}s outside [-60, ${MaxAgeSec}]s."
            }
            Write-Output ($blocked | ConvertTo-Json -Depth 4)
            exit 2
        }
    }
    return $openPos
}

$OpenPos = Assert-FlatAndFreshHeartbeat -Path $HbPath -NowTs $NowUtcTs -MaxAgeSec $MaxHeartbeatAgeSec -AllowMissing:$ForceWhenHeartbeatMissing -IsDryRun:$DryRun

$Ex5Files = @()
foreach ($reqName in $RequiredEx5Names) {
    $fp = Join-Path $ResolvedEx5Dir $reqName
    if (-not (Test-Path -LiteralPath $fp)) {
        throw "MISSING_REQUIRED_EX5: $reqName not found in $ResolvedEx5Dir"
    }
    $Ex5Files += Get-Item -LiteralPath $fp
}

# Cross-verify source .ex5 hashes against kit manifest when using default compiled dir
$ManifestHashes = @{}
if ([string]::IsNullOrWhiteSpace($Ex5SourceDir) -and -not [string]::IsNullOrWhiteSpace($ManifestPath) -and (Test-Path -LiteralPath $ManifestPath)) {
    $mObj = Get-Content -LiteralPath $ManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($mObj.compiled_ex5_files) {
        foreach ($prop in $mObj.compiled_ex5_files.PSObject.Properties) {
            $leaf = Split-Path -Leaf $prop.Name
            $ManifestHashes[$leaf] = ([string]$prop.Value.sha256).ToLowerInvariant()
        }
    }
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
    # Re-check flat + fresh right before writing (reduces TOCTOU window)
    $NowCheckTs = if ($NowUtcOverride -gt 0) { $NowUtcOverride } else { [DateTimeOffset]::UtcNow.ToUnixTimeSeconds() }
    $null = Assert-FlatAndFreshHeartbeat -Path $HbPath -NowTs $NowCheckTs -MaxAgeSec $MaxHeartbeatAgeSec -AllowMissing:$ForceWhenHeartbeatMissing -IsDryRun:$false

    New-Item -ItemType Directory -Force -Path $DestDir | Out-Null
    New-Item -ItemType Directory -Force -Path $DestFilesDir | Out-Null
    $Stamp = [DateTimeOffset]::UtcNow.ToString("yyyyMMddTHHmmssZ")
    $RollbackDir = Join-Path $TargetMt5Root ".naqex_sync_rollback_$Stamp"
    $BackedUp = @()
    try {
        foreach ($f in $Ex5Files) {
            $dst = Join-Path $DestDir $f.Name
            if (Test-Path -LiteralPath $dst) {
                New-Item -ItemType Directory -Force -Path $RollbackDir | Out-Null
                $bak = Join-Path $RollbackDir $f.Name
                Copy-Item -LiteralPath $dst -Destination $bak -Force
                $BackedUp += @{ Src = $bak; Dst = $dst }
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
            Copy-Item -LiteralPath $DestCsvPath -Destination $bakCsv -Force
            $BackedUp += @{ Src = $bakCsv; Dst = $DestCsvPath }
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
        foreach ($item in $BackedUp) {
            if (Test-Path -LiteralPath $item.Src) {
                Copy-Item -LiteralPath $item.Src -Destination $item.Dst -Force -ErrorAction SilentlyContinue
            }
        }
        throw
    }
}

$res = [ordered]@{
    schema          = "naqex-ex5-flat-sync-v1"
    status          = if ($DryRun) { "DRYRUN_READY_FLAT" } else { "SYNCED_CLEAN_FLAT" }
    open_positions  = $OpenPos
    dest_dir        = $DestDir
    files_count     = $Updated.Count
    files           = @($Updated)
    ex5_sha256      = $Ex5Hashes
    manifest_checked = ($ManifestHashes.Count -gt 0)
    red_news_csv    = [ordered]@{
        source          = $ResolvedCsvPath
        dest            = $DestCsvPath
        rows            = $CsvRowCount
        sha256          = $SrcCsvSha
        synced          = (-not [bool]$DryRun)
        sha256_verified = $true
    }
    sha256_verified = $true
    order_send      = 0
}
Write-Output ($res | ConvertTo-Json -Depth 5)
exit 0

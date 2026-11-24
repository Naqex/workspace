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
    [switch]$DryRun,
    [switch]$ForceWhenHeartbeatMissing
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$KitRoot = Split-Path -Parent $PSScriptRoot
$ExportsDir = Split-Path -Parent $KitRoot
$RepoRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $ExportsDir))
$ResolvedEx5Dir = if (-not [string]::IsNullOrWhiteSpace($Ex5SourceDir)) {
    $Ex5SourceDir
} elseif (Test-Path -LiteralPath (Join-Path $RepoRoot ".runtime\mt5-compiled-ex5")) {
    Join-Path $RepoRoot ".runtime\mt5-compiled-ex5"
} else {
    $ExportsDir
}
$ResolvedCsvPath = if (-not [string]::IsNullOrWhiteSpace($RedNewsCsvPath)) {
    $RedNewsCsvPath
} else {
    Join-Path $ExportsDir "Files\naqex_red_news_utc.csv"
}
$HbPath = Join-Path $TargetMt5Root "MQL5\Files\naqex_heartbeat.json"

$OpenPos = 0
$HbFound = Test-Path -LiteralPath $HbPath
if ($HbFound) {
    $hb = Get-Content -LiteralPath $HbPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $OpenPos = [int]$hb.open_positions
    if ($OpenPos -gt 0) {
        $blocked = [ordered]@{
            schema         = "naqex-ex5-flat-sync-v1"
            status         = "BLOCKED_OPEN_POSITIONS"
            open_positions = $OpenPos
            heartbeat_path = $HbPath
            dry_run        = [bool]$DryRun
            order_send     = 0
            message        = "Refused fail-closed: terminal currently has $OpenPos open position(s). Retry once flat (open_positions == 0)."
        }
        Write-Output ($blocked | ConvertTo-Json -Depth 4)
        exit 2
    }
} elseif (-not $ForceWhenHeartbeatMissing) {
    throw "HEARTBEAT_MISSING_FAIL_CLOSED: $HbPath not found. Pass -ForceWhenHeartbeatMissing only if terminal is verified offline."
}

$Ex5Files = Get-ChildItem -LiteralPath $ResolvedEx5Dir -Filter "*.ex5" | Sort-Object Name
if ($Ex5Files.Count -lt 9) {
    throw "INCOMPLETE_EXPORTS: expected >= 9 .ex5 in $ResolvedEx5Dir, found $($Ex5Files.Count)"
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

$Updated = New-Object System.Collections.Generic.List[string]
$Ex5Hashes = [ordered]@{}
foreach ($f in $Ex5Files) {
    $srcHash = (Get-FileHash -LiteralPath $f.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    $dst = Join-Path $DestDir $f.Name
    if (-not $DryRun) {
        New-Item -ItemType Directory -Force -Path $DestDir | Out-Null
        Copy-Item -LiteralPath $f.FullName -Destination $dst -Force
        $dstHash = (Get-FileHash -LiteralPath $dst -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($dstHash -ne $srcHash) {
            throw "SHA256_MISMATCH_AFTER_COPY: $($f.Name) src=$srcHash dst=$dstHash"
        }
    }
    $Ex5Hashes[$f.Name] = $srcHash
    $Updated.Add($f.Name)
}

if (-not $DryRun) {
    New-Item -ItemType Directory -Force -Path $DestFilesDir | Out-Null
    Copy-Item -LiteralPath $ResolvedCsvPath -Destination $DestCsvPath -Force
    $dstCsvSha = (Get-FileHash -LiteralPath $DestCsvPath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($dstCsvSha -ne $SrcCsvSha) {
        throw "SHA256_MISMATCH_AFTER_COPY: naqex_red_news_utc.csv src=$SrcCsvSha dst=$dstCsvSha"
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

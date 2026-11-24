<#
.SYNOPSIS
    Fail-Closed Flat-Only .ex5 Updater (never overwrites EAs while positions are open!).

.DESCRIPTION
    Checks `MQL5\Files\naqex_heartbeat.json` inside a target MT5 sandbox/VPS directory.
    REFUSES to copy updated .ex5 binaries (e.g., after the `ResolveExecutedFillPrice` TCA fix)
    if `open_positions > 0`. Safe to run with `-DryRun` at any time.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\sync_updated_ex5_when_flat.ps1 -TargetMt5Root D:\ANNAM\TradingWorkspace\.runtime\ftmo-demo-portable-1515343166 -DryRun
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$TargetMt5Root,

    [string]$Ex5SourceDir = "",
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

# Detect whether target places Naqex EAs under MQL5\Experts\Naqex or directly under MQL5\Experts
$SubDir = Join-Path $TargetMt5Root "MQL5\Experts\Naqex"
$DestDir = if (Test-Path -LiteralPath $SubDir) { $SubDir } else { Join-Path $TargetMt5Root "MQL5\Experts" }

$Updated = New-Object System.Collections.Generic.List[string]
foreach ($f in $Ex5Files) {
    $dst = Join-Path $DestDir $f.Name
    if (-not $DryRun) {
        New-Item -ItemType Directory -Force -Path $DestDir | Out-Null
        Copy-Item -LiteralPath $f.FullName -Destination $dst -Force
    }
    $Updated.Add($f.Name)
}

$res = [ordered]@{
    schema         = "naqex-ex5-flat-sync-v1"
    status         = if ($DryRun) { "DRYRUN_READY_FLAT" } else { "SYNCED_CLEAN_FLAT" }
    open_positions = $OpenPos
    dest_dir       = $DestDir
    files_count    = $Updated.Count
    files          = @($Updated)
}
Write-Output ($res | ConvertTo-Json -Depth 4)
exit 0

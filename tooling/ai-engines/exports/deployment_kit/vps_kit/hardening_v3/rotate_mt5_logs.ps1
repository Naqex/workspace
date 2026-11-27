<#
.SYNOPSIS
    Safe MT5 & MQL5 log rotation script for naqex-node1 (Hardening v3, OrderSend = 0).

.DESCRIPTION
    Rotates historical `*.log` files under `C:\Naqex\mt5\Logs\` and `C:\Naqex\mt5\MQL5\Logs\`:
      - Compresses logs strictly older than 7 days into `D:\NaqexBackup\mt5-logs-archive\<scope>\`
      - Verifies zip archive readability and uncompressed length before deleting source `.log`
      - Deletes archives older than 90 days
      - NEVER touches today's active log file (checked against BOTH UTC and Local dates + 24h mtime guard)
      - Enforces C: SSD free-space guard (> 20 GB) and forbids broken-latch drive E:
      - Full `-DryRun` and `-WhatIf` support with zero disk mutations.
    Complements `naqex_mt5_watchdog.ps1` (watchdog log rotation) and `node_ctl.py logs`.

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File .\rotate_mt5_logs.ps1 -DryRun
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$Mt5Root = "C:\Naqex\mt5",
    [string]$ArchiveRoot = "D:\NaqexBackup\mt5-logs-archive",
    [int]$CompressOlderThanDays = 7,
    [int]$RetainArchiveDays = 90,
    [double]$MinSystemDriveFreeGb = 20.0,
    [double]$SimulatedSystemDriveFreeGb = -1.0,
    [string]$NowUtcIsoOverride = "",
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

$SchemaVersion = "naqex-rotate-mt5-logs-v3"
$InvCulture = [System.Globalization.CultureInfo]::InvariantCulture
$IsDryRun = [bool]$DryRun -or [bool]$WhatIfPreference

$ReusedOpsTools = @(
    "tooling/ai-engines/ops_cloud/node_ctl.py",
    "tooling/ai-engines/ops_cloud/node_scripts/node_logs.py",
    "tooling/ai-engines/ops_cloud/node_weekly_digest.py",
    "tooling/ai-engines/exports/deployment_kit/ops_watchdog/naqex_mt5_watchdog.ps1"
)

function ConvertTo-SanitizedText {
    param([string]$Text)
    if ($null -eq $Text) { return "" }
    $out = $Text
    $out = [regex]::Replace($out, '(?i)[A-Z]:\\Users\\[^\\/\s"'']+', 'C:\Users\<USER>')
    $out = [regex]::Replace($out, '\b(?!100\.64\.0\.0/10\b)(?:\d{1,3}\.){3}\d{1,3}\b', '[REDACTED_IP]')
    $out = $out.Replace('$', 'USD ')
    return $out
}

function Test-ForbiddenDriveE {
    param([string]$PathValue)
    if ([string]::IsNullOrWhiteSpace($PathValue)) { return $false }
    $norm = $PathValue.Trim().Replace('/', '\')
    return ($norm -match '(?i)^E:(\\|$)')
}

function Emit-JsonAndExit {
    param($Payload, [int]$ExitCode)
    $txt = ConvertTo-SanitizedText -Text ($Payload | ConvertTo-Json -Depth 6)
    Write-Output $txt
    exit $ExitCode
}

if ((Test-ForbiddenDriveE -PathValue $Mt5Root) -or (Test-ForbiddenDriveE -PathValue $ArchiveRoot)) {
    $errPayload = [ordered]@{
        schema           = $SchemaVersion
        status           = "BLOCKED_FORBIDDEN_DRIVE_E"
        dry_run          = $IsDryRun
        order_send_count = 0
        message          = "Drive E: is strictly forbidden under 3-drive broken-latch storage contract."
        reused_ops_tools = $ReusedOpsTools
    }
    Emit-JsonAndExit -ExitCode 2 -Payload $errPayload
}

if ($CompressOlderThanDays -lt 1 -or $RetainArchiveDays -lt $CompressOlderThanDays) {
    $errPayload = [ordered]@{
        schema           = $SchemaVersion
        status           = "BLOCKED_INVALID_RETENTION_POLICY"
        dry_run          = $IsDryRun
        order_send_count = 0
        message          = "CompressOlderThanDays must be >= 1 and RetainArchiveDays >= CompressOlderThanDays."
    }
    Emit-JsonAndExit -ExitCode 2 -Payload $errPayload
}

$NowUtc = if (-not [string]::IsNullOrWhiteSpace($NowUtcIsoOverride)) {
    [DateTimeOffset]::Parse($NowUtcIsoOverride, $InvCulture, [System.Globalization.DateTimeStyles]::AssumeUniversal).ToUniversalTime()
} else {
    [DateTimeOffset]::UtcNow
}
$NowLocal = $NowUtc.ToLocalTime()
$TodayUtcKey = $NowUtc.ToString("yyyyMMdd", $InvCulture)
$TodayLocalKey = $NowLocal.ToString("yyyyMMdd", $InvCulture)
$ProtectedDateKeys = @($TodayUtcKey, $TodayLocalKey) | Select-Object -Unique

function Get-DriveFreeGb {
    param([string]$TargetPath, [double]$SimulatedGb)
    if ($SimulatedGb -ge 0.0) {
        return [math]::Round($SimulatedGb, 2)
    }
    try {
        $root = [System.IO.Path]::GetPathRoot($TargetPath)
        if ([string]::IsNullOrWhiteSpace($root)) { $root = "C:\" }
        $di = New-Object System.IO.DriveInfo($root)
        return [math]::Round(($di.AvailableFreeSpace / 1GB), 2)
    } catch {
        return -1.0
    }
}

function Get-EffectiveFileDateUtc {
    param([System.IO.FileInfo]$FileObj)
    $mtimeUtc = $FileObj.LastWriteTimeUtc
    $m = [regex]::Match($FileObj.BaseName, '(20\d{2})(\d{2})(\d{2})')
    if ($m.Success) {
        try {
            $parsed = New-Object System.DateTime([int]$m.Groups[1].Value, [int]$m.Groups[2].Value, [int]$m.Groups[3].Value, 23, 59, 59, [System.DateTimeKind]::Utc)
            # Take the MORE RECENT timestamp so recently modified logs are NEVER rotated prematurely
            if ($parsed -gt $mtimeUtc) { return $parsed }
        } catch {}
    }
    return $mtimeUtc
}

function Test-IsTodayProtectedLog {
    param([System.IO.FileInfo]$FileObj, [string[]]$TodayKeys, [DateTimeOffset]$RefNowUtc)
    foreach ($k in $TodayKeys) {
        if ($FileObj.BaseName -eq $k -or $FileObj.Name -like "$k*.log") {
            return $true
        }
    }
    $ageHours = ($RefNowUtc.UtcDateTime - $FileObj.LastWriteTimeUtc).TotalHours
    if ($ageHours -lt 24.0) {
        return $true
    }
    return $false
}

function Test-ZipArchiveReadable {
    param([string]$ZipPath, [long]$ExpectedUncompressedBytes)
    if (-not (Test-Path -LiteralPath $ZipPath -PathType Leaf)) { return $false }
    $za = $null
    try {
        $za = [System.IO.Compression.ZipFile]::OpenRead($ZipPath)
        if ($za.Entries.Count -ne 1) { return $false }
        $entry = $za.Entries[0]
        if ([long]$entry.Length -ne $ExpectedUncompressedBytes) { return $false }
        return $true
    } catch {
        return $false
    } finally {
        if ($null -ne $za) { $za.Dispose() }
    }
}

$DiskBeforeGb = Get-DriveFreeGb -TargetPath $Mt5Root -SimulatedGb $SimulatedSystemDriveFreeGb

$LogScopes = @(
    [ordered]@{ scope = "terminal"; path = (Join-Path $Mt5Root "Logs") },
    [ordered]@{ scope = "mql5";     path = (Join-Path $Mt5Root "MQL5\Logs") }
)

$ProtectedActiveFiles = New-Object System.Collections.Generic.List[string]
$KeptRecentFiles = New-Object System.Collections.Generic.List[string]
$PlannedCompressFiles = New-Object System.Collections.Generic.List[string]
$CompressedFiles = New-Object System.Collections.Generic.List[object]
$Errors = New-Object System.Collections.Generic.List[string]
[long]$ProjectedReclaimedBytes = 0
[long]$ActualReclaimedBytes = 0

foreach ($sc in $LogScopes) {
    $scopeName = [string]$sc.scope
    $dirPath = [string]$sc.path
    if (-not (Test-Path -LiteralPath $dirPath -PathType Container)) {
        continue
    }
    $logFiles = @(Get-ChildItem -LiteralPath $dirPath -Filter "*.log" -File -ErrorAction SilentlyContinue | Sort-Object Name)
    foreach ($lf in $logFiles) {
        if (Test-IsTodayProtectedLog -FileObj $lf -TodayKeys $ProtectedDateKeys -RefNowUtc $NowUtc) {
            $ProtectedActiveFiles.Add("${scopeName}/$($lf.Name)")
            continue
        }
        $effDate = Get-EffectiveFileDateUtc -FileObj $lf
        $ageDays = ($NowUtc.UtcDateTime - $effDate).TotalDays
        if ($ageDays -le [double]$CompressOlderThanDays) {
            $KeptRecentFiles.Add("${scopeName}/$($lf.Name)")
            continue
        }

        $archiveSubDir = Join-Path $ArchiveRoot $scopeName
        $zipName = "$($lf.BaseName)_${scopeName}.zip"
        $zipPath = Join-Path $archiveSubDir $zipName
        $ProjectedReclaimedBytes += [long]$lf.Length
        $PlannedCompressFiles.Add("${scopeName}/$($lf.Name) -> ${scopeName}/${zipName}")

        if (-not $IsDryRun) {
            try {
                if (-not (Test-Path -LiteralPath $archiveSubDir -PathType Container)) {
                    New-Item -ItemType Directory -Force -Path $archiveSubDir | Out-Null
                }
                $srcSha = (Get-FileHash -LiteralPath $lf.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
                $srcLen = [long]$lf.Length
                $tmpZip = "$zipPath.tmp.$PID"
                if (Test-Path -LiteralPath $tmpZip) {
                    Remove-Item -LiteralPath $tmpZip -Force
                }
                $za = [System.IO.Compression.ZipFile]::Open($tmpZip, [System.IO.Compression.ZipArchiveMode]::Create)
                try {
                    $null = [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
                        $za,
                        $lf.FullName,
                        $lf.Name,
                        [System.IO.Compression.CompressionLevel]::Optimal
                    )
                } finally {
                    $za.Dispose()
                }
                if (-not (Test-ZipArchiveReadable -ZipPath $tmpZip -ExpectedUncompressedBytes $srcLen)) {
                    Remove-Item -LiteralPath $tmpZip -Force -ErrorAction SilentlyContinue
                    throw "ZIP_VERIFY_FAILED:$($lf.Name)"
                }
                Move-Item -LiteralPath $tmpZip -Destination $zipPath -Force
                # Preserve original log timestamp on archive for accurate 90-day retention tracking
                (Get-Item -LiteralPath $zipPath).LastWriteTimeUtc = $lf.LastWriteTimeUtc
                Remove-Item -LiteralPath $lf.FullName -Force
                $ActualReclaimedBytes += $srcLen
                $CompressedFiles.Add([ordered]@{
                    scope          = $scopeName
                    source_name    = $lf.Name
                    archive_name   = $zipName
                    source_bytes   = $srcLen
                    source_sha256  = $srcSha
                    archive_bytes  = [long](Get-Item -LiteralPath $zipPath).Length
                })
            } catch {
                $Errors.Add("COMPRESS_ERROR:${scopeName}/$($lf.Name):$($_.Exception.Message)")
            }
        }
    }
}

# Prune archives strictly older than RetainArchiveDays (default 90 days)
$PlannedPruneArchives = New-Object System.Collections.Generic.List[string]
$PrunedArchives = New-Object System.Collections.Generic.List[string]
$KeptArchivesCount = 0

if (Test-Path -LiteralPath $ArchiveRoot -PathType Container) {
    $archives = @(Get-ChildItem -LiteralPath $ArchiveRoot -Filter "*.zip" -File -Recurse -ErrorAction SilentlyContinue | Sort-Object FullName)
    foreach ($arc in $archives) {
        $arcEffDate = Get-EffectiveFileDateUtc -FileObj $arc
        $arcAgeDays = ($NowUtc.UtcDateTime - $arcEffDate).TotalDays
        if ($arcAgeDays -le [double]$RetainArchiveDays) {
            $KeptArchivesCount++
            continue
        }
        $relLabel = $arc.Name
        $PlannedPruneArchives.Add($relLabel)
        if (-not $IsDryRun) {
            try {
                Remove-Item -LiteralPath $arc.FullName -Force
                $PrunedArchives.Add($relLabel)
            } catch {
                $Errors.Add("PRUNE_ERROR:${relLabel}:$($_.Exception.Message)")
            }
        }
    }
}

$DiskAfterGb = Get-DriveFreeGb -TargetPath $Mt5Root -SimulatedGb $SimulatedSystemDriveFreeGb
$DiskGuardPassed = ($DiskAfterGb -gt $MinSystemDriveFreeGb)

$Status = if ($Errors.Count -gt 0) {
    "ERROR_ROTATION_PARTIAL"
} elseif (-not $DiskGuardPassed) {
    if ($IsDryRun) { "DRYRUN_LOW_DISK_ALERT" } else { "RED_LOW_DISK_AFTER_ROTATE" }
} else {
    if ($IsDryRun) { "DRYRUN_READY" } else { "ROTATED_CLEAN" }
}

$ExitCode = 0
if ($Errors.Count -gt 0) {
    $ExitCode = 1
} elseif (-not $DiskGuardPassed -and (-not $IsDryRun)) {
    $ExitCode = 2
}

$FinalPayload = [ordered]@{
    schema                    = $SchemaVersion
    checked_utc               = $NowUtc.ToString("yyyy-MM-ddTHH:mm:ssZ", $InvCulture)
    dry_run                   = $IsDryRun
    order_send_count          = 0
    status                    = $Status
    compress_older_than_days  = $CompressOlderThanDays
    retain_archive_days       = $RetainArchiveDays
    min_system_drive_free_gb  = $MinSystemDriveFreeGb
    disk_free_gb_before       = $DiskBeforeGb
    disk_free_gb_after        = $DiskAfterGb
    disk_guard_passed         = $DiskGuardPassed
    today_protected_keys      = @($ProtectedDateKeys)
    protected_active_files    = @($ProtectedActiveFiles.ToArray())
    kept_recent_files_count   = $KeptRecentFiles.Count
    planned_compress_files    = @($PlannedCompressFiles.ToArray())
    compressed_files          = @($CompressedFiles.ToArray())
    planned_prune_archives    = @($PlannedPruneArchives.ToArray())
    pruned_archives           = @($PrunedArchives.ToArray())
    kept_archives_count       = $KeptArchivesCount
    projected_bytes_reclaimed = $ProjectedReclaimedBytes
    actual_bytes_reclaimed    = $ActualReclaimedBytes
    errors                    = @($Errors.ToArray())
    reused_ops_tools          = $ReusedOpsTools
}
Emit-JsonAndExit -ExitCode $ExitCode -Payload $FinalPayload

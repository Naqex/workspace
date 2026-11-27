<#
.SYNOPSIS
    1-Way Read-Only Live-Vault Pull from naqex-node1 -> PC Dev .runtime/live-vault/ (Hardening v3, OrderSend = 0).

.DESCRIPTION
    Pulls read-only telemetry and forensic artifacts from `naqex-node1` to isolated PC Dev
    `.runtime/live-vault/snapshots/<UTC_STAMP>/` with two-sided SHA-256 verification:
      - `naqex_exec_audit*.csv`
      - `naqex_decision_blackbox_*.jsonl`
      - Broker M1 quote tapes (`*quote*.csv`, `*quote*.jsonl`, `*m1*tape*.*`, `nfp_cpi_*.*`)
      - Heartbeat snapshots (`naqex_heartbeat*.json`, `naqex_master*_heartbeat.json`)
    HARD INVARIANTS:
      - ZERO writes back to `naqex-node1` (`remote_writes = 0`, 1-way pull only)
      - ZERO Holdout (`2025+`) or Dev backtest cache mixing (forbids holdout/dev_cache/E: paths)
      - ZERO credential/config files copied (`accounts.dat`, `terminal.lic`, `*.ini`, `*.key`, `*token*`)
      - Full `-DryRun`, `-WhatIf`, and `-OfflineSourceDir` support for offline CI testing.
    Reuses `node_ctl.py` SSH LAN -> Tailscale (`-ts`) alias convention and complements `node_weekly_digest.py`.

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File .\sync_live_vault_readonly.ps1 -DryRun
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$SshAlias = "naqex-node1",
    [string]$FallbackSshAlias = "naqex-node1-ts",
    [string]$RemoteMt5FilesDir = "C:\Naqex\mt5\MQL5\Files",
    [string]$RemoteQuoteTapeDir = "C:\Naqex\logs\quote_tapes",
    [string]$RemotePython = "C:\Naqex\tools\python\cpython-3.12-windows-x86_64-none\python.exe",
    [string]$LocalVaultRoot = "",
    [string]$OfflineSourceDir = "",
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$SchemaVersion = "naqex-live-vault-readonly-pull-v3"
$InvCulture = [System.Globalization.CultureInfo]::InvariantCulture
$IsDryRun = [bool]$DryRun -or [bool]$WhatIfPreference

$ReusedOpsTools = @(
    "tooling/ai-engines/ops_cloud/node_ctl.py",
    "tooling/ai-engines/ops_cloud/node_scripts/node_exec_audit.py",
    "tooling/ai-engines/ops_cloud/node_weekly_digest.py",
    "tooling/ai-engines/ops_cloud/nfp_cpi_quote_collector.py"
)

$AllowPatterns = @(
    '(?i)^naqex_exec_audit.*\.csv$',
    '(?i)^naqex_decision_blackbox_.*\.jsonl$',
    '(?i)^naqex_master.*heartbeat\.json$',
    '(?i)^naqex_heartbeat.*\.json$',
    '(?i)^nfp_cpi_.*\.(csv|jsonl)$',
    '(?i)^.*quote.*\.(csv|jsonl|parquet|npz)$',
    '(?i)^.*m1.*tape.*\.(csv|jsonl|parquet|npz)$'
)

$ForbiddenPatterns = @(
    '(?i)^accounts\.dat$',
    '(?i)^terminal\.lic$',
    '(?i)\.ini$',
    '(?i)\.key$',
    '(?i)\.pem$',
    '(?i)\.pfx$',
    '(?i)\.ex5$',
    '(?i)secret',
    '(?i)token',
    '(?i)password',
    '(?i)passwd',
    '(?i)heroku_connection_local\.json$'
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

function Emit-ResultAndExit {
    param([string]$Status, [int]$ExitCode, [hashtable]$Extra)
    $obj = [ordered]@{
        schema            = $SchemaVersion
        checked_utc       = [DateTimeOffset]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ", $InvCulture)
        status            = $Status
        direction         = "ONE_WAY_PULL_READONLY"
        dry_run           = $IsDryRun
        order_send_count  = 0
        remote_writes     = 0
        holdout_mixed     = $false
        dev_cache_mixed   = $false
        reused_ops_tools  = $ReusedOpsTools
    }
    foreach ($k in $Extra.Keys) { $obj[$k] = $Extra[$k] }
    Write-Output (ConvertTo-SanitizedText -Text ($obj | ConvertTo-Json -Depth 6))
    exit $ExitCode
}

function Test-SafeSshAlias {
    param([string]$Alias)
    if ([string]::IsNullOrWhiteSpace($Alias)) { return $false }
    return ($Alias -match '^[A-Za-z0-9][A-Za-z0-9._-]*$')
}

function Test-AllowlistedArtifactName {
    param([string]$FileName)
    foreach ($forb in $ForbiddenPatterns) {
        if ($FileName -match $forb) { return $false }
    }
    foreach ($allow in $AllowPatterns) {
        if ($FileName -match $allow) { return $true }
    }
    return $false
}

function Test-SafeLocalVaultRoot {
    param([string]$VaultPath)
    if ([string]::IsNullOrWhiteSpace($VaultPath)) {
        return @{ ok = $false; reason = "LocalVaultRoot is empty." }
    }
    $norm = $VaultPath.Trim().Replace('/', '\')
    if ($norm -match '(?i)^E:(\\|$)') {
        return @{ ok = $false; reason = "Drive E: is forbidden." }
    }
    if ($norm -match '(^|\\)\.\.?(\\|$)') {
        return @{ ok = $false; reason = "Dot traversal segments are forbidden." }
    }
    if ($norm -match '(?i)(holdout|native_ftmo_holdout|dev_cache|mt5-m1-cache|mt5-compiled-ex5|private_vault|\\mql5\\|\\exports\\)') {
        return @{ ok = $false; reason = "Vault path MUST NOT overlap Holdout, Dev cache, exports, MQL5, or private_vault." }
    }
    if ($norm -notmatch '(?i)\\live-vault(\\|$)' -and $norm -notmatch '(?i)\\live-vault$') {
        return @{ ok = $false; reason = "LocalVaultRoot must target an isolated 'live-vault' directory." }
    }
    return @{ ok = $true; reason = "Isolated live-vault target verified." }
}

function Invoke-ProcessWithStdin {
    param(
        [string]$FileName,
        [string[]]$Arguments,
        [string]$StdinText = "",
        [int]$TimeoutMs = 25000
    )
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $FileName
    $escapedArgs = @()
    foreach ($a in $Arguments) {
        if ($a -match '[\s"]') {
            $escapedArgs += ('"' + ($a -replace '"', '\"') + '"')
        } else {
            $escapedArgs += $a
        }
    }
    $psi.Arguments = ($escapedArgs -join " ")
    $psi.UseShellExecute = $false
    $psi.RedirectStandardInput = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.CreateNoWindow = $true
    $psi.StandardOutputEncoding = [System.Text.Encoding]::UTF8
    $psi.StandardErrorEncoding = [System.Text.Encoding]::UTF8

    $proc = New-Object System.Diagnostics.Process
    $proc.StartInfo = $psi
    $null = $proc.Start()
    $stdoutTask = $proc.StandardOutput.ReadToEndAsync()
    $stderrTask = $proc.StandardError.ReadToEndAsync()
    if (-not [string]::IsNullOrEmpty($StdinText)) {
        $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
        $bytes = $utf8NoBom.GetBytes($StdinText)
        $proc.StandardInput.BaseStream.Write($bytes, 0, $bytes.Length)
        $proc.StandardInput.BaseStream.Flush()
    }
    $proc.StandardInput.Close()
    if (-not $proc.WaitForExit($TimeoutMs)) {
        try { $proc.Kill() } catch {}
        return @{ returncode = 124; stdout = ""; stderr = "Process timed out after ${TimeoutMs}ms." }
    }
    $proc.WaitForExit()
    $rc = $proc.ExitCode
    $stdoutStr = $stdoutTask.GetAwaiter().GetResult()
    $stderrStr = $stderrTask.GetAwaiter().GetResult()
    $proc.Dispose()
    return @{ returncode = $rc; stdout = $stdoutStr; stderr = $stderrStr }
}

function Invoke-RemoteReadOnlyListing {
    param([string[]]$RemoteDirs)
    $pyDirsJson = ($RemoteDirs | ConvertTo-Json -Compress)
    if ($RemoteDirs.Count -eq 1) { $pyDirsJson = "[$pyDirsJson]" }
    $pyScript = @"
import hashlib, json, pathlib, re
dirs = json.loads(r'''$pyDirsJson''')
allow_re = [
    re.compile(r'^naqex_exec_audit.*\.csv$', re.I),
    re.compile(r'^naqex_decision_blackbox_.*\.jsonl$', re.I),
    re.compile(r'^naqex_master.*heartbeat\.json$', re.I),
    re.compile(r'^naqex_heartbeat.*\.json$', re.I),
    re.compile(r'^nfp_cpi_.*\.(csv|jsonl)$', re.I),
    re.compile(r'^.*quote.*\.(csv|jsonl|parquet|npz)$', re.I),
    re.compile(r'^.*m1.*tape.*\.(csv|jsonl|parquet|npz)$', re.I),
]
forb_re = [
    re.compile(r'^(accounts\.dat|terminal\.lic|heroku_connection_local\.json)$', re.I),
    re.compile(r'\.(ini|key|pem|pfx|ex5)$', re.I),
    re.compile(r'(secret|token|password|passwd)', re.I),
]
items = []
for d in dirs:
    p = pathlib.Path(d)
    if not p.is_dir():
        continue
    for f in sorted(p.iterdir()):
        if not f.is_file():
            continue
        nm = f.name
        if any(r.search(nm) for r in forb_re):
            continue
        if not any(r.search(nm) for r in allow_re):
            continue
        h = hashlib.sha256()
        with f.open('rb') as fp:
            for chunk in iter(lambda: fp.read(65536), b''):
                h.update(chunk)
        items.append({'name': nm, 'remote_path': str(f), 'bytes': f.stat().st_size, 'sha256': h.hexdigest().lower()})
print(json.dumps({'ok': True, 'files': items}, ensure_ascii=True))
"@

    $candidates = @($SshAlias)
    if (-not [string]::IsNullOrWhiteSpace($FallbackSshAlias) -and $FallbackSshAlias -ne $SshAlias) {
        $candidates += $FallbackSshAlias
    }
    $lastErr = ""
    for ($i = 0; $i -lt $candidates.Count; $i++) {
        $hostAlias = $candidates[$i]
        $hasNext = ($i + 1) -lt $candidates.Count
        $remoteCmd = ('"{0}" -' -f $RemotePython)
        $res = Invoke-ProcessWithStdin -FileName "ssh" -Arguments @("-o", "ConnectTimeout=6", "-o", "BatchMode=yes", $hostAlias, $remoteCmd) -StdinText $pyScript -TimeoutMs 25000
        if ($res.returncode -eq 255 -and $hasNext) {
            $lastErr = $res.stderr
            continue
        }
        if ($res.returncode -ne 0 -or [string]::IsNullOrWhiteSpace($res.stdout)) {
            return @{ ok = $false; error = ("Remote read-only listing failed (rc={0}): {1}" -f $res.returncode, $res.stderr.Trim()) }
        }
        $parsed = $res.stdout.Trim() | ConvertFrom-Json
        return @{ ok = $true; host_alias = $hostAlias; files = @($parsed.files) }
    }
    return @{ ok = $false; error = ("SSH unreachable: {0}" -f $lastErr) }
}

# === MAIN EXECUTION ===
if (-not (Test-SafeSshAlias -Alias $SshAlias)) {
    Emit-ResultAndExit -Status "BLOCKED_INVALID_SSH_ALIAS" -ExitCode 2 -Extra @{ message = "Invalid SshAlias parameter." }
}
if (-not [string]::IsNullOrWhiteSpace($FallbackSshAlias) -and (-not (Test-SafeSshAlias -Alias $FallbackSshAlias))) {
    Emit-ResultAndExit -Status "BLOCKED_INVALID_SSH_ALIAS" -ExitCode 2 -Extra @{ message = "Invalid FallbackSshAlias parameter." }
}

$RepoRoot = Get-AncestorPath -StartPath $PSScriptRoot -Levels 6
$ResolvedVaultRoot = if (-not [string]::IsNullOrWhiteSpace($LocalVaultRoot)) {
    $LocalVaultRoot
} elseif (-not [string]::IsNullOrWhiteSpace($RepoRoot)) {
    Join-Path $RepoRoot ".runtime\live-vault"
} else {
    ""
}

$VaultCheck = Test-SafeLocalVaultRoot -VaultPath $ResolvedVaultRoot
if (-not $VaultCheck.ok) {
    Emit-ResultAndExit -Status "BLOCKED_FORBIDDEN_VAULT_TARGET" -ExitCode 2 -Extra @{
        message = $VaultCheck.reason
    }
}

$IsOffline = -not [string]::IsNullOrWhiteSpace($OfflineSourceDir)
$SourceFiles = @()
$SkippedForbidden = @()
$SelectedHost = "offline_source"

if ($IsOffline) {
    if (-not (Test-Path -LiteralPath $OfflineSourceDir -PathType Container)) {
        Emit-ResultAndExit -Status "BLOCKED_OFFLINE_SOURCE_MISSING" -ExitCode 2 -Extra @{
            message = "OfflineSourceDir does not exist."
        }
    }
    foreach ($f in @(Get-ChildItem -LiteralPath $OfflineSourceDir -File -Recurse -ErrorAction SilentlyContinue | Sort-Object FullName)) {
        $isForbidden = $false
        foreach ($forb in $ForbiddenPatterns) {
            if ($f.Name -match $forb) { $isForbidden = $true; break }
        }
        if ($isForbidden) {
            $SkippedForbidden += $f.Name
            continue
        }
        if (-not (Test-AllowlistedArtifactName -FileName $f.Name)) { continue }
        $sha = (Get-FileHash -LiteralPath $f.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        $SourceFiles += [ordered]@{
            name        = $f.Name
            source_path = $f.FullName
            bytes       = [long]$f.Length
            sha256      = $sha
        }
    }
} else {
    $listing = Invoke-RemoteReadOnlyListing -RemoteDirs @($RemoteMt5FilesDir, $RemoteQuoteTapeDir)
    if (-not $listing.ok) {
        Emit-ResultAndExit -Status "BLOCKED_REMOTE_LISTING_FAILED" -ExitCode 2 -Extra @{
            message = $listing.error
        }
    }
    $SelectedHost = $listing.host_alias
    foreach ($rf in @($listing.files)) {
        if (-not (Test-AllowlistedArtifactName -FileName ([string]$rf.name))) { continue }
        $SourceFiles += [ordered]@{
            name        = [string]$rf.name
            source_path = [string]$rf.remote_path
            bytes       = [long]$rf.bytes
            sha256      = ([string]$rf.sha256).ToLowerInvariant()
        }
    }
}

$PlannedNames = @($SourceFiles | ForEach-Object { $_.name })
$SourceShaMap = [ordered]@{}
foreach ($sf in $SourceFiles) { $SourceShaMap[$sf.name] = $sf.sha256 }

if ($IsDryRun) {
    Emit-ResultAndExit -Status "DRYRUN_PULL_PLAN_READY" -ExitCode 0 -Extra @{
        mode                     = if ($IsOffline) { "offline_source" } else { "live_ssh_readonly" }
        planned_count            = $SourceFiles.Count
        planned_files            = $PlannedNames
        skipped_forbidden_files  = @($SkippedForbidden)
        local_files_written      = 0
        sha256_verified          = $false
        source_sha256            = $SourceShaMap
        message                  = "DryRun complete: 0 remote writes, 0 local writes."
    }
}

$SnapStamp = [DateTimeOffset]::UtcNow.ToString("yyyyMMddTHHmmssZ", $InvCulture)
$SnapshotDir = Join-Path (Join-Path $ResolvedVaultRoot "snapshots") $SnapStamp
New-Item -ItemType Directory -Force -Path $SnapshotDir | Out-Null

$PulledFiles = @()
$LocalShaMap = [ordered]@{}
$Mismatches = @()

foreach ($sf in $SourceFiles) {
    $dstPath = Join-Path $SnapshotDir $sf.name
    if ($IsOffline) {
        Copy-Item -LiteralPath $sf.source_path -Destination $dstPath -Force
    } else {
        $remoteSpec = ("{0}:{1}" -f $SelectedHost, ($sf.source_path -replace '\\', '/'))
        $scpRes = Invoke-ProcessWithStdin -FileName "scp" -Arguments @("-o", "ConnectTimeout=6", "-o", "BatchMode=yes", $remoteSpec, $dstPath) -TimeoutMs 30000
        if ($scpRes.returncode -ne 0) {
            if (Test-Path -LiteralPath $dstPath) { Remove-Item -LiteralPath $dstPath -Force -ErrorAction SilentlyContinue }
            Emit-ResultAndExit -Status "PULL_TRANSFER_FAILED" -ExitCode 1 -Extra @{
                mode                = "live_ssh_readonly"
                failed_file         = $sf.name
                local_files_written = $PulledFiles.Count
                sha256_verified     = $false
                message             = ("SCP read-only pull failed for {0}: {1}" -f $sf.name, $scpRes.stderr.Trim())
            }
        }
    }
    $localSha = (Get-FileHash -LiteralPath $dstPath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($localSha -ne $sf.sha256) {
        Remove-Item -LiteralPath $dstPath -Force -ErrorAction SilentlyContinue
        $Mismatches += $sf.name
    } else {
        $LocalShaMap[$sf.name] = $localSha
        $PulledFiles += $sf.name
    }
}

if ($Mismatches.Count -gt 0) {
    Emit-ResultAndExit -Status "SHA256_MISMATCH_PULL_ABORTED" -ExitCode 1 -Extra @{
        mode                = if ($IsOffline) { "offline_source" } else { "live_ssh_readonly" }
        pulled_files        = $PulledFiles
        sha256_mismatches   = $Mismatches
        sha256_verified     = $false
        local_files_written = $PulledFiles.Count
        message             = "SHA-256 verification failed on pulled artifacts; corrupt copies removed."
    }
}

$ManifestObj = [ordered]@{
    schema          = "naqex-live-vault-snapshot-manifest-v3"
    snapshot_utc    = $SnapStamp
    plane           = "LIVE_VAULT_ISOLATED_READONLY"
    direction       = "ONE_WAY_PULL_READONLY"
    order_send      = 0
    remote_writes   = 0
    holdout_mixed   = $false
    dev_cache_mixed = $false
    files_count     = $PulledFiles.Count
    sha256          = $LocalShaMap
}
$ManifestJson = ConvertTo-SanitizedText -Text ($ManifestObj | ConvertTo-Json -Depth 5)
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText((Join-Path $SnapshotDir "manifest.sha256.json"), $ManifestJson + "`n", $utf8NoBom)

Emit-ResultAndExit -Status "PULLED_CLEAN_VERIFIED" -ExitCode 0 -Extra @{
    mode                    = if ($IsOffline) { "offline_source" } else { "live_ssh_readonly" }
    snapshot_id             = $SnapStamp
    pulled_count            = $PulledFiles.Count
    pulled_files            = $PulledFiles
    skipped_forbidden_files = @($SkippedForbidden)
    local_files_written     = $PulledFiles.Count
    sha256_verified         = $true
    sha256_mismatches       = @()
    source_sha256           = $SourceShaMap
    local_sha256            = $LocalShaMap
    message                 = "1-way read-only pull completed and SHA-256 verified."
}

<#
.SYNOPSIS
    Fail-Closed Flat-Only Staging Guard for Total Offensive #2 on naqex-node1 (OrderSend = 0).

.DESCRIPTION
    Verifies mandatory flat-only and infrastructure safety preconditions before staging
    Total Offensive #2 artifacts into isolated `C:\Naqex\staging\total-offensive-2\` on `naqex-node1`.
    NEVER overwrites live MT5 `MQL5\Experts\`, `MQL5\Files\`, `MQL5\Presets\`, or `E:\` paths.
    NEVER touches AutoTrading or broker credentials.
    Supports `-DryRun`, `-OfflineFixtureDir <dir>` (100% deterministic offline tests), and live SSH alias.

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File .\stage_total_offensive_2_when_flat.ps1 -DryRun
#>
[CmdletBinding()]
param(
    [string]$SshAlias = "naqex-node1",
    [string]$FallbackSshAlias = "naqex-node1-ts",
    [string]$RemoteStagingDir = "C:\Naqex\staging\total-offensive-2",
    [string]$RemotePython = "C:\Naqex\tools\python\cpython-3.12-windows-x86_64-none\python.exe",
    [string]$RemoteNodeScriptsDir = "C:\Naqex\scripts",
    [string]$SourceBundleDir = "",
    [string]$OfflineFixtureDir = "",
    [string]$LocalVerifyPython = "",
    [double]$MinDiskFreeGb = 20.0,
    [double]$MaxAbsNtpOffsetMs = 1000.0,
    [int]$MaxHeartbeatAgeSec = 180,
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$SchemaVersion = "naqex-node1-staging-guard-v1"
$InvCulture = [System.Globalization.CultureInfo]::InvariantCulture

$ForbiddenOutputKeys = @(
    "_ssh_host", "account_login", "login", "ip", "wan_ip", "public_ip", "router_ip",
    "hop_ips", "raw_hops", "isp", "org", "asn", "token", "view_token", "ingest_token",
    "password", "passwd", "secret", "webhook", "api_key", "url", "web_url",
    "mobile_dashboard_url", "username", "user"
)

$ForbiddenSourcePatterns = @(
    "(?i)^accounts\.dat$",
    "(?i)^terminal\.lic$",
    "(?i)\.ini$",
    "(?i)\.key$",
    "(?i)\.pem$",
    "(?i)\.pfx$",
    "(?i)secret",
    "(?i)token",
    "(?i)password",
    "(?i)passwd",
    "(?i)heroku_connection_local\.json$"
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

function Get-ObjProp {
    param($Obj, [string]$Name, $Default = $null)
    if ($null -eq $Obj) { return $Default }
    if ($Obj -is [System.Collections.IDictionary]) {
        if ($Obj.Contains($Name)) { return $Obj[$Name] }
        return $Default
    }
    $props = $Obj.PSObject.Properties
    if ($null -ne $props) {
        $p = $props[$Name]
        if ($null -ne $p) { return $p.Value }
    }
    return $Default
}

function Try-ToInt {
    param($Value)
    if ($null -eq $Value -or $Value -is [bool]) { return $null }
    if ($Value -is [int] -or $Value -is [long]) { return [long]$Value }
    if ($Value -is [double] -or $Value -is [decimal]) {
        $d = [double]$Value
        if ([double]::IsNaN($d) -or [double]::IsInfinity($d)) { return $null }
        if ([math]::Floor($d) -ne $d) { return $null }
        return [long]$d
    }
    $s = ([string]$Value).Trim()
    if ([string]::IsNullOrWhiteSpace($s)) { return $null }
    $out = [long]0
    if ([long]::TryParse($s, [System.Globalization.NumberStyles]::Integer, $InvCulture, [ref]$out)) {
        return $out
    }
    return $null
}

function Try-ToDouble {
    param($Value)
    if ($null -eq $Value -or $Value -is [bool]) { return $null }
    if ($Value -is [int] -or $Value -is [long] -or $Value -is [double] -or $Value -is [float] -or $Value -is [decimal]) {
        $d = [double]$Value
        if ([double]::IsNaN($d) -or [double]::IsInfinity($d)) { return $null }
        return $d
    }
    $s = ([string]$Value).Trim()
    if ([string]::IsNullOrWhiteSpace($s)) { return $null }
    $out = [double]0.0
    if ([double]::TryParse($s, [System.Globalization.NumberStyles]::Float, $InvCulture, [ref]$out)) {
        if ([double]::IsNaN($out) -or [double]::IsInfinity($out)) { return $null }
        return $out
    }
    return $null
}

function ConvertTo-SanitizedText {
    param([string]$Text)
    if ($null -eq $Text) { return "" }
    $out = $Text
    $out = [regex]::Replace($out, '(?i)https?://[^\s"''<>]+', '[REDACTED_URL]')
    $out = [regex]::Replace($out, '(?i)\b(password|passwd|token|api[_-]?key|secret|webhook|authorization|bearer)\s*[:=]\s*\S+', '$1=[REDACTED]')
    $out = [regex]::Replace($out, '(?i)\bBearer\s+[A-Za-z0-9._\-+/=]{6,}', 'Bearer [REDACTED]')
    $out = [regex]::Replace($out, '(?i)(?:\b(?:[0-9a-f]{1,4}:){3,7}[0-9a-f]{1,4}\b|(?:[0-9a-f]{1,4}:){1,6}:[0-9a-f:]{1,20}|::[0-9a-f:]{1,20})', '[REDACTED_IPV6]')
    $out = [regex]::Replace($out, '\b(?:\d{1,3}\.){3}\d{1,3}\b', '[REDACTED_IP]')
    $out = [regex]::Replace($out, '(?i)[A-Z]:\\Users\\[^\\/\s"'']+', '<USER_PROFILE>')
    $out = [regex]::Replace($out, '(?i)/Users/[^/\s"'']+', '<USER_PROFILE>')
    $out = [regex]::Replace($out, '(?i)/home/[^/\s"'']+', '<USER_PROFILE>')
    $out = [regex]::Replace($out, '(?i)\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\b', '[REDACTED_USER]')
    $out = $out.Replace('$', 'USD ')
    return $out
}

function ConvertTo-SanitizedObject {
    param($Obj)
    if ($null -eq $Obj) { return $null }
    if ($Obj -is [string]) {
        return (ConvertTo-SanitizedText -Text $Obj)
    }
    if ($Obj -is [bool] -or $Obj -is [int] -or $Obj -is [long] -or $Obj -is [double] -or $Obj -is [float] -or $Obj -is [decimal]) {
        return $Obj
    }
    if ($Obj -is [System.Collections.IDictionary]) {
        $clean = [ordered]@{}
        foreach ($k in $Obj.Keys) {
            $ks = [string]$k
            if ($ForbiddenOutputKeys -contains $ks.ToLowerInvariant()) { continue }
            $clean[$ks] = ConvertTo-SanitizedObject -Obj $Obj[$k]
        }
        return $clean
    }
    if ($Obj -is [System.Collections.IEnumerable]) {
        $list = New-Object System.Collections.ArrayList
        foreach ($item in $Obj) {
            $null = $list.Add((ConvertTo-SanitizedObject -Obj $item))
        }
        return ,$list.ToArray()
    }
    if ($Obj -is [PSCustomObject]) {
        $clean = [ordered]@{}
        foreach ($prop in $Obj.PSObject.Properties) {
            $ks = [string]$prop.Name
            if ($ForbiddenOutputKeys -contains $ks.ToLowerInvariant()) { continue }
            $clean[$ks] = ConvertTo-SanitizedObject -Obj $prop.Value
        }
        return $clean
    }
    return (ConvertTo-SanitizedText -Text ([string]$Obj))
}

function Emit-ResultAndExit {
    param(
        [string]$Status,
        [int]$ExitCode,
        [hashtable]$Payload
    )
    $out = [ordered]@{
        schema              = $SchemaVersion
        checked_utc         = [DateTimeOffset]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ", $InvCulture)
        status              = $Status
        dry_run             = [bool]$DryRun
        mode                = if ([string]::IsNullOrWhiteSpace($OfflineFixtureDir)) { "live_ssh" } else { "offline_fixture" }
        order_send_count    = 0
        live_ex5_overwrites = 0
        autotrading_touched = $false
    }
    foreach ($k in $Payload.Keys) {
        $out[$k] = $Payload[$k]
    }
    $sanitized = ConvertTo-SanitizedObject -Obj $out
    $json = $sanitized | ConvertTo-Json -Depth 6
    $json = ConvertTo-SanitizedText -Text $json
    Write-Output $json
    exit $ExitCode
}

function Test-SafeSshAlias {
    param([string]$Alias)
    if ([string]::IsNullOrWhiteSpace($Alias)) { return $false }
    return ($Alias -match '^[A-Za-z0-9][A-Za-z0-9._-]*$')
}

function Test-SafeStagingTargetPath {
    param([string]$TargetPath)
    if ([string]::IsNullOrWhiteSpace($TargetPath)) {
        return @{ ok = $false; reason = "Target staging path is empty." }
    }
    $norm = $TargetPath.Trim().Replace('/', '\')
    if ($norm -match '\\\\') {
        return @{ ok = $false; reason = "Repeated path separators are forbidden." }
    }
    if ($norm -match '(^|\\)\.\.?(\\|$)') {
        return @{ ok = $false; reason = "Dot path segments '.' or '..' are forbidden." }
    }
    if ($norm -match '(?i)^E:') {
        return @{ ok = $false; reason = "Drive E: is forbidden (broken SATA latch policy)." }
    }
    if ($norm -match '(?i)\\mql5\\(experts|files|presets|include|indicators|scripts)(\\|$)') {
        return @{ ok = $false; reason = "Live MT5 MQL5 folder is strictly forbidden for staging." }
    }
    if ($norm -match '(?i)\\naqex\\mt5(\\|$)') {
        return @{ ok = $false; reason = "Live MT5 root C:\Naqex\mt5 is strictly forbidden for staging." }
    }
    $trimmed = $norm.TrimEnd('\')
    if ($trimmed -notmatch '(?i)^C:\\Naqex\\staging\\total-offensive-2(\\[A-Za-z0-9][A-Za-z0-9._-]*)*$') {
        return @{ ok = $false; reason = "Staging path must stay isolated inside C:\Naqex\staging\total-offensive-2." }
    }
    $segments = $trimmed.Split('\')
    for ($i = 4; $i -lt $segments.Count; $i++) {
        $seg = $segments[$i]
        if ($seg -eq "." -or $seg -eq ".." -or $seg.StartsWith(".") -or $seg.EndsWith(".")) {
            return @{ ok = $false; reason = "Invalid dot-prefixed or dot-terminated staging subdirectory segment." }
        }
    }
    return @{ ok = $true; reason = "Isolated staging path verified." }
}

function ConvertTo-NtpOffsetMs {
    param($StatusObj)
    $rawMs = Get-ObjProp -Obj $StatusObj -Name "ntp_offset_ms" -Default $null
    if ($null -ne $rawMs) {
        $parsedMs = Try-ToDouble -Value $rawMs
        if ($null -ne $parsedMs) { return $parsedMs }
        return $null
    }
    $rawStr = Get-ObjProp -Obj $StatusObj -Name "ntp_offset" -Default $null
    if ($null -eq $rawStr) { return $null }
    $txt = ([string]$rawStr).Trim()
    if ([string]::IsNullOrWhiteSpace($txt)) { return $null }
    $mMs = [regex]::Match($txt, '(?i)^([+-]?\d+(?:\.\d+)?)\s*ms$')
    if ($mMs.Success) {
        return (Try-ToDouble -Value $mMs.Groups[1].Value)
    }
    $mSec = [regex]::Match($txt, '(?i)^([+-]?\d+(?:\.\d+)?)\s*s$')
    if ($mSec.Success) {
        $sec = Try-ToDouble -Value $mSec.Groups[1].Value
        if ($null -ne $sec) { return [math]::Round($sec * 1000.0, 3) }
    }
    return $null
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

    $exited = $proc.WaitForExit($TimeoutMs)
    if (-not $exited) {
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

function Invoke-RemoteSshCommand {
    param(
        [string]$RemoteCommand,
        [string]$StdinText = "",
        [int]$TimeoutMs = 25000
    )
    $candidates = @($SshAlias)
    if (-not [string]::IsNullOrWhiteSpace($FallbackSshAlias) -and $FallbackSshAlias -ne $SshAlias) {
        $candidates += $FallbackSshAlias
    }
    $lastErr = ""
    for ($i = 0; $i -lt $candidates.Count; $i++) {
        $hostAlias = $candidates[$i]
        $hasNext = ($i + 1) -lt $candidates.Count
        $sshArgs = @("-o", "ConnectTimeout=6", "-o", "BatchMode=yes", $hostAlias, $RemoteCommand)
        $res = Invoke-ProcessWithStdin -FileName "ssh" -Arguments $sshArgs -StdinText $StdinText -TimeoutMs $TimeoutMs
        if ($res.returncode -eq 255 -and $hasNext) {
            $lastErr = $res.stderr
            continue
        }
        return @{
            host_index = $i
            host_alias = $hostAlias
            returncode = $res.returncode
            stdout     = $res.stdout
            stderr     = $res.stderr
        }
    }
    return @{ host_index = -1; host_alias = ""; returncode = 255; stdout = ""; stderr = $lastErr }
}

function Read-RemoteNodeProbes {
    $statusCmd = ('"{0}" "{1}\node_status.py"' -f $RemotePython, $RemoteNodeScriptsDir)
    $rStatus = Invoke-RemoteSshCommand -RemoteCommand $statusCmd -TimeoutMs 25000
    if ($rStatus.returncode -ne 0 -or [string]::IsNullOrWhiteSpace($rStatus.stdout)) {
        return @{ ok = $false; error = ("Remote node_status.py failed (rc={0}): {1}" -f $rStatus.returncode, $rStatus.stderr.Trim()) }
    }
    $integrityCmd = ('"{0}" "{1}\node_integrity.py"' -f $RemotePython, $RemoteNodeScriptsDir)
    $rInt = Invoke-RemoteSshCommand -RemoteCommand $integrityCmd -TimeoutMs 25000
    if ($rInt.returncode -ne 0 -or [string]::IsNullOrWhiteSpace($rInt.stdout)) {
        return @{ ok = $false; error = ("Remote node_integrity.py failed (rc={0}): {1}" -f $rInt.returncode, $rInt.stderr.Trim()) }
    }
    try {
        $statusObj = $rStatus.stdout.Trim() | ConvertFrom-Json
        $intObj = $rInt.stdout.Trim() | ConvertFrom-Json
    } catch {
        return @{ ok = $false; error = ("Failed parsing remote probe JSON: {0}" -f $_.Exception.Message) }
    }
    return @{
        ok            = $true
        selected_host = $rStatus.host_alias
        status        = $statusObj
        integrity     = $intObj
    }
}

function Test-StagingPreconditions {
    param(
        $StatusObj,
        $IntegrityObj,
        [string]$TargetDir
    )
    $gates = New-Object System.Collections.ArrayList
    $failedGates = New-Object System.Collections.ArrayList
    $primaryCode = "READY"

    $pathCheck = Test-SafeStagingTargetPath -TargetPath $TargetDir
    $null = $gates.Add([ordered]@{
        id     = "isolated_staging_target"
        status = if ($pathCheck.ok) { "PASS" } else { "BLOCK" }
        detail = $pathCheck.reason
    })
    if (-not $pathCheck.ok) {
        $null = $failedGates.Add("isolated_staging_target")
        $primaryCode = "BLOCKED_FORBIDDEN_TARGET_PATH"
    }

    $hb = Get-ObjProp -Obj $StatusObj -Name "heartbeat" -Default $null
    $openPos = Try-ToInt -Value (Get-ObjProp -Obj $hb -Name "open_positions" -Default $null)
    $totalPosRaw = Get-ObjProp -Obj $hb -Name "total_account_positions" -Default $null
    $totalPos = if ($null -ne $totalPosRaw) { Try-ToInt -Value $totalPosRaw } else { $openPos }
    $pendingRaw = Get-ObjProp -Obj $hb -Name "pending_orders" -Default 0
    $pendingOrd = Try-ToInt -Value $pendingRaw
    $orphanRaw = Get-ObjProp -Obj $hb -Name "orphan_no_sl" -Default 0
    $orphanNoSl = Try-ToInt -Value $orphanRaw

    $flatOk = (
        ($null -ne $openPos) -and ($openPos -eq 0) -and
        ($null -ne $totalPos) -and ($totalPos -eq 0) -and
        ($null -ne $pendingOrd) -and ($pendingOrd -eq 0) -and
        ($null -ne $orphanNoSl) -and ($orphanNoSl -eq 0)
    )
    $null = $gates.Add([ordered]@{
        id     = "flat_positions_zero"
        status = if ($flatOk) { "PASS" } else { "BLOCK" }
        detail = ("open_positions={0}, total_account_positions={1}, pending_orders={2}, orphan_no_sl={3}" -f $openPos, $totalPos, $pendingOrd, $orphanNoSl)
    })
    if (-not $flatOk) {
        $null = $failedGates.Add("flat_positions_zero")
        if ($primaryCode -eq "READY") { $primaryCode = "BLOCKED_OPEN_POSITIONS" }
    }

    $termConnRaw = Get-ObjProp -Obj $hb -Name "terminal_connected" -Default $null
    $termConn = ($termConnRaw -is [bool] -and $termConnRaw -eq $true)
    $posStateRaw = Get-ObjProp -Obj $hb -Name "positions_state" -Default "UNKNOWN"
    $posState = ([string]$posStateRaw).Trim().ToUpperInvariant()
    $ageSec = Try-ToDouble -Value (Get-ObjProp -Obj $hb -Name "age_sec" -Default $null)
    $ageOk = ($null -ne $ageSec) -and ($ageSec -ge -60.0) -and ($ageSec -le [double]$MaxHeartbeatAgeSec)
    $connFreshOk = $termConn -and ($posState -eq "CONFIRMED") -and $ageOk
    $null = $gates.Add([ordered]@{
        id     = "broker_connected_and_fresh"
        status = if ($connFreshOk) { "PASS" } else { "BLOCK" }
        detail = ("terminal_connected={0}, positions_state={1}, age_sec={2} (max {3}s)" -f $termConn, $posState, $ageSec, $MaxHeartbeatAgeSec)
    })
    if (-not $connFreshOk) {
        $null = $failedGates.Add("broker_connected_and_fresh")
        if ($primaryCode -eq "READY") {
            if (-not $termConn -or $posState -ne "CONFIRMED") {
                $primaryCode = "BLOCKED_BROKER_DISCONNECTED"
            } else {
                $primaryCode = "BLOCKED_STALE_HEARTBEAT"
            }
        }
    }

    $commonIni = Get-ObjProp -Obj $IntegrityObj -Name "common_ini" -Default $null
    $connIni = Get-ObjProp -Obj $IntegrityObj -Name "connector_ini" -Default $null
    $kpVal = Get-ObjProp -Obj $commonIni -Name "keep_private" -Default $null
    $connLoginOverride = [bool](Get-ObjProp -Obj $connIni -Name "has_login_override" -Default $false)
    $kpOk = (([string]$kpVal).Trim() -eq "1") -and (-not $connLoginOverride)
    $null = $gates.Add([ordered]@{
        id     = "keep_private_enabled"
        status = if ($kpOk) { "PASS" } else { "BLOCK" }
        detail = ("KeepPrivate={0}, connector_login_override={1}" -f $kpVal, $connLoginOverride)
    })
    if (-not $kpOk) {
        $null = $failedGates.Add("keep_private_enabled")
        if ($primaryCode -eq "READY") { $primaryCode = "BLOCKED_KEEP_PRIVATE" }
    }

    $disks = Get-ObjProp -Obj $StatusObj -Name "disks" -Default $null
    $diskC = Get-ObjProp -Obj $disks -Name "C" -Default $null
    $diskFreeGb = Try-ToDouble -Value (Get-ObjProp -Obj $diskC -Name "free_gb" -Default $null)
    $diskOk = ($null -ne $diskFreeGb) -and ($diskFreeGb -gt $MinDiskFreeGb)
    $null = $gates.Add([ordered]@{
        id     = "disk_c_free_above_min"
        status = if ($diskOk) { "PASS" } else { "BLOCK" }
        detail = ("disk_c_free_gb={0} (required > {1} GB)" -f $diskFreeGb, $MinDiskFreeGb)
    })
    if (-not $diskOk) {
        $null = $failedGates.Add("disk_c_free_above_min")
        if ($primaryCode -eq "READY") { $primaryCode = "BLOCKED_LOW_DISK" }
    }

    $ntpMs = ConvertTo-NtpOffsetMs -StatusObj $StatusObj
    $ntpOk = ($null -ne $ntpMs) -and ([math]::Abs($ntpMs) -lt $MaxAbsNtpOffsetMs)
    $null = $gates.Add([ordered]@{
        id     = "ntp_drift_within_limit"
        status = if ($ntpOk) { "PASS" } else { "BLOCK" }
        detail = ("ntp_offset_ms={0} (required abs < {1} ms)" -f $ntpMs, $MaxAbsNtpOffsetMs)
    })
    if (-not $ntpOk) {
        $null = $failedGates.Add("ntp_drift_within_limit")
        if ($primaryCode -eq "READY") { $primaryCode = "BLOCKED_NTP_DRIFT" }
    }

    return @{
        passed       = ($failedGates.Count -eq 0)
        status_code  = $primaryCode
        gates_passed = ($gates.Count - $failedGates.Count)
        gates_total  = $gates.Count
        failed_gates = @($failedGates.ToArray())
        gates        = @($gates.ToArray())
        snapshot     = [ordered]@{
            open_positions          = $openPos
            total_account_positions = $totalPos
            pending_orders          = $pendingOrd
            orphan_no_sl            = $orphanNoSl
            terminal_connected      = $termConn
            positions_state         = $posState
            heartbeat_age_sec       = $ageSec
            keep_private            = ([string]$kpVal).Trim()
            disk_c_free_gb          = $diskFreeGb
            ntp_offset_ms           = $ntpMs
        }
    }
}

function Test-ForbiddenSourceName {
    param([string]$FileName)
    foreach ($pat in $ForbiddenSourcePatterns) {
        if ($FileName -match $pat) { return $true }
    }
    return $false
}

function Resolve-SourceBundle {
    $kitRoot = Get-AncestorPath -StartPath $PSScriptRoot -Levels 1
    $exportsDir = Get-AncestorPath -StartPath $PSScriptRoot -Levels 2
    $repoRoot = Get-AncestorPath -StartPath $PSScriptRoot -Levels 5

    $items = New-Object System.Collections.ArrayList
    if (-not [string]::IsNullOrWhiteSpace($SourceBundleDir)) {
        if (-not (Test-Path -LiteralPath $SourceBundleDir -PathType Container)) {
            return @{ ok = $false; code = "BLOCKED_MISSING_SOURCE_BUNDLE"; error = "SourceBundleDir not found." }
        }
        $files = @(Get-ChildItem -LiteralPath $SourceBundleDir -File | Sort-Object Name)
        foreach ($f in $files) {
            if (Test-ForbiddenSourceName -FileName $f.Name) {
                return @{ ok = $false; code = "BLOCKED_FORBIDDEN_CREDENTIAL_FILE"; error = ("Forbidden credential/config file in source bundle: {0}" -f $f.Name) }
            }
            $null = $items.Add($f)
        }
    } elseif (-not [string]::IsNullOrWhiteSpace($OfflineFixtureDir)) {
        $fxSrc = Join-Path $OfflineFixtureDir "source"
        if (-not (Test-Path -LiteralPath $fxSrc -PathType Container)) {
            return @{ ok = $false; code = "BLOCKED_MISSING_SOURCE_BUNDLE"; error = "Offline fixture missing 'source' directory." }
        }
        $files = @(Get-ChildItem -LiteralPath $fxSrc -File | Sort-Object Name)
        foreach ($f in $files) {
            if (Test-ForbiddenSourceName -FileName $f.Name) {
                return @{ ok = $false; code = "BLOCKED_FORBIDDEN_CREDENTIAL_FILE"; error = ("Forbidden credential/config file in source bundle: {0}" -f $f.Name) }
            }
            $null = $items.Add($f)
        }
    } else {
        $masterEx5 = Join-Path $repoRoot ".runtime\mt5-compiled-ex5\Naqex_Master_Prop7E.ex5"
        $redNewsCsv = Join-Path $exportsDir "Files\naqex_red_news_utc.csv"
        $manifestJson = Join-Path $kitRoot "manifest.sha256.json"
        $presetsDir = Join-Path $kitRoot "presets"
        foreach ($req in @($masterEx5, $redNewsCsv, $manifestJson)) {
            if (-not (Test-Path -LiteralPath $req -PathType Leaf)) {
                return @{ ok = $false; code = "BLOCKED_MISSING_SOURCE_ARTIFACT"; error = ("Missing required staging artifact: {0}" -f (Split-Path -Leaf $req)) }
            }
            $null = $items.Add((Get-Item -LiteralPath $req))
        }
        if (Test-Path -LiteralPath $presetsDir -PathType Container) {
            $presetFiles = @(Get-ChildItem -LiteralPath $presetsDir -Filter "FTMO_Std10K_MasterProp7E_*.set" -File | Sort-Object Name)
            foreach ($pf in $presetFiles) {
                $null = $items.Add($pf)
            }
        }
    }

    if ($items.Count -eq 0) {
        return @{ ok = $false; code = "BLOCKED_EMPTY_SOURCE_BUNDLE"; error = "Source bundle contains zero files." }
    }
    return @{ ok = $true; files = @($items.ToArray()); repo_root = $repoRoot }
}

function Get-PythonHashScript {
    param([string]$TargetDirectory)
    $cleanDir = $TargetDirectory.Trim().Replace('/', '\').TrimEnd('\')
    $escaped = $cleanDir.Replace('\', '\\').Replace('"', '\"')
    return @"
import hashlib, json, pathlib
root = pathlib.Path("$escaped")
out = {}
if root.is_dir():
    for p in sorted(root.iterdir()):
        if p.is_file():
            h = hashlib.sha256()
            with p.open("rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    h.update(chunk)
            out[p.name] = h.hexdigest().lower()
print(json.dumps({"ok": root.is_dir(), "files": out}, ensure_ascii=True))
"@
}

function ConvertFrom-VerifierJson {
    param([string]$RawStdout)
    if ([string]::IsNullOrWhiteSpace($RawStdout)) {
        return @{ ok = $false; error = "SHA-256 verifier emitted empty stdout." }
    }
    $parsed = $null
    try {
        $parsed = $RawStdout.Trim() | ConvertFrom-Json
    } catch {
        return @{ ok = $false; error = ("SHA-256 verifier emitted non-JSON output: {0}" -f $_.Exception.Message) }
    }
    $okFlag = Get-ObjProp -Obj $parsed -Name "ok" -Default $null
    if (-not ($okFlag -is [bool] -and $okFlag -eq $true)) {
        return @{ ok = $false; error = ("SHA-256 verifier reported ok={0} (expected true)." -f $okFlag) }
    }
    $filesObj = Get-ObjProp -Obj $parsed -Name "files" -Default $null
    if ($null -eq $filesObj) {
        return @{ ok = $false; error = "SHA-256 verifier JSON missing required 'files' map." }
    }
    return @{ ok = $true; files = $filesObj }
}

function Resolve-LocalPythonExe {
    param([string]$RepoRoot)
    if (-not [string]::IsNullOrWhiteSpace($LocalVerifyPython) -and (Test-Path -LiteralPath $LocalVerifyPython -PathType Leaf)) {
        return $LocalVerifyPython
    }
    if (-not [string]::IsNullOrWhiteSpace($RepoRoot)) {
        $cand = Join-Path $RepoRoot ".runtime\quant-audit-v24\Scripts\python.exe"
        if (Test-Path -LiteralPath $cand -PathType Leaf) { return $cand }
    }
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($null -ne $cmd) { return $cmd.Source }
    return ""
}

# === MAIN EXECUTION ===

if (-not (Test-SafeSshAlias -Alias $SshAlias)) {
    Emit-ResultAndExit -Status "BLOCKED_INVALID_SSH_ALIAS" -ExitCode 2 -Payload @{
        message      = "Rejected invalid SSH alias parameter."
        failed_gates = @("ssh_alias_valid")
    }
}
if (-not [string]::IsNullOrWhiteSpace($FallbackSshAlias) -and (-not (Test-SafeSshAlias -Alias $FallbackSshAlias))) {
    Emit-ResultAndExit -Status "BLOCKED_INVALID_SSH_ALIAS" -ExitCode 2 -Payload @{
        message      = "Rejected invalid fallback SSH alias parameter."
        failed_gates = @("ssh_alias_valid")
    }
}

$IsOffline = -not [string]::IsNullOrWhiteSpace($OfflineFixtureDir)
$StatusObj = $null
$IntegrityObj = $null
$SelectedSshHost = ""

if ($IsOffline) {
    if (-not (Test-Path -LiteralPath $OfflineFixtureDir -PathType Container)) {
        Emit-ResultAndExit -Status "BLOCKED_MISSING_FIXTURE" -ExitCode 2 -Payload @{
            message      = "OfflineFixtureDir does not exist."
            failed_gates = @("offline_fixture_present")
        }
    }
    $statusPath = Join-Path $OfflineFixtureDir "status.json"
    $intPath = Join-Path $OfflineFixtureDir "integrity.json"
    if (-not (Test-Path -LiteralPath $statusPath -PathType Leaf) -or -not (Test-Path -LiteralPath $intPath -PathType Leaf)) {
        Emit-ResultAndExit -Status "BLOCKED_MISSING_FIXTURE" -ExitCode 2 -Payload @{
            message      = "OfflineFixtureDir must contain status.json and integrity.json."
            failed_gates = @("offline_fixture_present")
        }
    }
    try {
        $StatusObj = (Get-Content -LiteralPath $statusPath -Raw -Encoding UTF8) | ConvertFrom-Json
        $IntegrityObj = (Get-Content -LiteralPath $intPath -Raw -Encoding UTF8) | ConvertFrom-Json
    } catch {
        Emit-ResultAndExit -Status "BLOCKED_INVALID_FIXTURE_JSON" -ExitCode 2 -Payload @{
            message      = ("Invalid JSON in offline fixture: {0}" -f $_.Exception.Message)
            failed_gates = @("offline_fixture_valid")
        }
    }
} else {
    $probe = Read-RemoteNodeProbes
    if (-not $probe.ok) {
        Emit-ResultAndExit -Status "BLOCKED_NODE_UNREACHABLE" -ExitCode 2 -Payload @{
            message      = $probe.error
            failed_gates = @("remote_probe_reachable")
        }
    }
    $StatusObj = $probe.status
    $IntegrityObj = $probe.integrity
    $SelectedSshHost = $probe.selected_host
}

$GateEval = Test-StagingPreconditions -StatusObj $StatusObj -IntegrityObj $IntegrityObj -TargetDir $RemoteStagingDir
if (-not $GateEval.passed) {
    Emit-ResultAndExit -Status $GateEval.status_code -ExitCode 2 -Payload @{
        target_staging_dir = $RemoteStagingDir
        gates_passed       = $GateEval.gates_passed
        gates_total        = $GateEval.gates_total
        failed_gates       = $GateEval.failed_gates
        gates              = $GateEval.gates
        node_snapshot      = $GateEval.snapshot
        staged_count       = 0
        sha256_verified    = $false
        message            = ("Fail-closed staging guard blocked: {0}" -f ($GateEval.failed_gates -join ", "))
    }
}

$Bundle = Resolve-SourceBundle
if (-not $Bundle.ok) {
    Emit-ResultAndExit -Status $Bundle.code -ExitCode 2 -Payload @{
        target_staging_dir = $RemoteStagingDir
        gates_passed       = $GateEval.gates_passed
        gates_total        = $GateEval.gates_total
        failed_gates       = @($Bundle.code.ToLowerInvariant())
        gates              = $GateEval.gates
        node_snapshot      = $GateEval.snapshot
        staged_count       = 0
        sha256_verified    = $false
        message            = $Bundle.error
    }
}

$LocalShaMap = [ordered]@{}
$FileNames = New-Object System.Collections.ArrayList
foreach ($f in $Bundle.files) {
    $h = (Get-FileHash -LiteralPath $f.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    $LocalShaMap[$f.Name] = $h
    $null = $FileNames.Add($f.Name)
}

if ($DryRun) {
    Emit-ResultAndExit -Status "DRYRUN_READY_FLAT" -ExitCode 0 -Payload @{
        target_staging_dir = $RemoteStagingDir
        gates_passed       = $GateEval.gates_passed
        gates_total        = $GateEval.gates_total
        failed_gates       = @()
        gates              = $GateEval.gates
        node_snapshot      = $GateEval.snapshot
        staged_count       = 0
        planned_count      = $FileNames.Count
        planned_files      = @($FileNames.ToArray())
        local_sha256       = $LocalShaMap
        remote_sha256      = [ordered]@{}
        sha256_verified    = $false
        sha256_mismatches  = @()
        message            = "DryRun complete: all preconditions passed; zero remote/staging writes performed."
    }
}

# === NON-DRYRUN ISOLATED STAGING WITH TWO-SIDED SHA-256 VERIFICATION ===

$RemoteShaMap = [ordered]@{}
$Mismatches = New-Object System.Collections.ArrayList
$VerifierEngine = ""

if ($IsOffline) {
    $offlineDestDir = Join-Path $OfflineFixtureDir "staging\total-offensive-2"
    New-Item -ItemType Directory -Force -Path $offlineDestDir | Out-Null
    foreach ($f in $Bundle.files) {
        $dstPath = Join-Path $offlineDestDir $f.Name
        Copy-Item -LiteralPath $f.FullName -Destination $dstPath -Force
    }
    $pyExe = Resolve-LocalPythonExe -RepoRoot $Bundle.repo_root
    if ([string]::IsNullOrWhiteSpace($pyExe)) {
        Emit-ResultAndExit -Status "SHA256_VERIFIER_UNAVAILABLE" -ExitCode 1 -Payload @{
            target_staging_dir = $RemoteStagingDir
            staged_count       = $FileNames.Count
            sha256_verified    = $false
            message            = "Python interpreter unavailable for two-sided SHA-256 verification."
        }
    }
    $VerifierEngine = "python_hashlib_offline"
    $pyScript = Get-PythonHashScript -TargetDirectory $offlineDestDir
    $pyRes = Invoke-ProcessWithStdin -FileName $pyExe -Arguments @("-") -StdinText $pyScript -TimeoutMs 25000
    if ($pyRes.returncode -ne 0 -or [string]::IsNullOrWhiteSpace($pyRes.stdout)) {
        Emit-ResultAndExit -Status "SHA256_VERIFICATION_FAILED" -ExitCode 1 -Payload @{
            target_staging_dir = $RemoteStagingDir
            staged_count       = $FileNames.Count
            sha256_verified    = $false
            message            = ("Python SHA-256 verifier failed: {0}" -f $pyRes.stderr.Trim())
        }
    }
    $parsedCheck = ConvertFrom-VerifierJson -RawStdout $pyRes.stdout
    if (-not $parsedCheck.ok) {
        Emit-ResultAndExit -Status "SHA256_VERIFICATION_FAILED" -ExitCode 1 -Payload @{
            target_staging_dir = $RemoteStagingDir
            verifier_engine    = $VerifierEngine
            staged_count       = $FileNames.Count
            sha256_verified    = $false
            message            = $parsedCheck.error
        }
    }
    $remFilesObj = $parsedCheck.files
    foreach ($name in $FileNames) {
        $rHash = Get-ObjProp -Obj $remFilesObj -Name $name -Default $null
        if ($null -eq $rHash) {
            $RemoteShaMap[$name] = "MISSING"
            $null = $Mismatches.Add($name)
        } else {
            $rHashNorm = ([string]$rHash).ToLowerInvariant()
            $RemoteShaMap[$name] = $rHashNorm
            if ($rHashNorm -ne $LocalShaMap[$name]) {
                $null = $Mismatches.Add($name)
            }
        }
    }
} else {
    # Live Wave 2A: re-check flat state immediately before write (reduces TOCTOU window)
    $recheck = Read-RemoteNodeProbes
    if (-not $recheck.ok) {
        Emit-ResultAndExit -Status "BLOCKED_NODE_UNREACHABLE" -ExitCode 2 -Payload @{
            target_staging_dir = $RemoteStagingDir
            message            = ("Pre-copy recheck failed: {0}" -f $recheck.error)
            failed_gates       = @("remote_probe_recheck")
        }
    }
    if (-not [string]::IsNullOrWhiteSpace($recheck.selected_host)) {
        $SelectedSshHost = $recheck.selected_host
    }
    $reGate = Test-StagingPreconditions -StatusObj $recheck.status -IntegrityObj $recheck.integrity -TargetDir $RemoteStagingDir
    if (-not $reGate.passed) {
        Emit-ResultAndExit -Status $reGate.status_code -ExitCode 2 -Payload @{
            target_staging_dir = $RemoteStagingDir
            gates_passed       = $reGate.gates_passed
            gates_total        = $reGate.gates_total
            failed_gates       = $reGate.failed_gates
            gates              = $reGate.gates
            node_snapshot      = $reGate.snapshot
            staged_count       = 0
            sha256_verified    = $false
            message            = ("Pre-copy TOCTOU recheck blocked: {0}" -f ($reGate.failed_gates -join ", "))
        }
    }

    $cleanRemDir = $RemoteStagingDir.Trim().Replace('/', '\').TrimEnd('\')
    $escapedRemDir = $cleanRemDir.Replace('\', '\\').Replace('"', '\"')
    $mkPy = ('import os; os.makedirs("{0}", exist_ok=True); print("OK")' -f $escapedRemDir)
    $mkCmd = ('"{0}" -' -f $RemotePython)
    $mkRes = Invoke-RemoteSshCommand -RemoteCommand $mkCmd -StdinText $mkPy -TimeoutMs 20000
    if ($mkRes.returncode -ne 0) {
        Emit-ResultAndExit -Status "STAGING_MKDIR_FAILED" -ExitCode 1 -Payload @{
            target_staging_dir = $RemoteStagingDir
            staged_count       = 0
            sha256_verified    = $false
            message            = ("Remote isolated staging mkdir failed: {0}" -f $mkRes.stderr.Trim())
        }
    }
    if (-not [string]::IsNullOrWhiteSpace($mkRes.host_alias)) {
        $SelectedSshHost = $mkRes.host_alias
    }

    $scpDir = $RemoteStagingDir.Trim().Replace('\', '/').TrimEnd('/')
    foreach ($f in $Bundle.files) {
        $scpHosts = @($SelectedSshHost)
        if (-not [string]::IsNullOrWhiteSpace($FallbackSshAlias) -and $FallbackSshAlias -ne $SelectedSshHost) {
            $scpHosts += $FallbackSshAlias
        }
        $scpOk = $false
        $lastScpErr = ""
        foreach ($hAlias in $scpHosts) {
            $remoteTarget = ("{0}:{1}/{2}" -f $hAlias, $scpDir, $f.Name)
            $scpArgs = @("-o", "ConnectTimeout=6", "-o", "BatchMode=yes", $f.FullName, $remoteTarget)
            $scpRes = Invoke-ProcessWithStdin -FileName "scp" -Arguments $scpArgs -TimeoutMs 30000
            if ($scpRes.returncode -eq 0) {
                $SelectedSshHost = $hAlias
                $scpOk = $true
                break
            }
            $lastScpErr = $scpRes.stderr.Trim()
        }
        if (-not $scpOk) {
            Emit-ResultAndExit -Status "STAGING_TRANSFER_FAILED" -ExitCode 1 -Payload @{
                target_staging_dir = $RemoteStagingDir
                staged_count       = 0
                sha256_verified    = $false
                message            = ("SCP transfer failed for {0}: {1}" -f $f.Name, $lastScpErr)
            }
        }
    }

    $VerifierEngine = "remote_python_hashlib_ssh"
    $verifyScript = Get-PythonHashScript -TargetDirectory $cleanRemDir
    $verifyCmd = ('"{0}" -' -f $RemotePython)
    $vRes = Invoke-RemoteSshCommand -RemoteCommand $verifyCmd -StdinText $verifyScript -TimeoutMs 25000
    if ($vRes.returncode -ne 0 -or [string]::IsNullOrWhiteSpace($vRes.stdout)) {
        Emit-ResultAndExit -Status "SHA256_VERIFICATION_FAILED" -ExitCode 1 -Payload @{
            target_staging_dir = $RemoteStagingDir
            verifier_engine    = $VerifierEngine
            staged_count       = $FileNames.Count
            sha256_verified    = $false
            message            = ("Remote Python SHA-256 verification failed: {0}" -f $vRes.stderr.Trim())
        }
    }
    $parsedCheck = ConvertFrom-VerifierJson -RawStdout $vRes.stdout
    if (-not $parsedCheck.ok) {
        Emit-ResultAndExit -Status "SHA256_VERIFICATION_FAILED" -ExitCode 1 -Payload @{
            target_staging_dir = $RemoteStagingDir
            verifier_engine    = $VerifierEngine
            staged_count       = $FileNames.Count
            sha256_verified    = $false
            message            = $parsedCheck.error
        }
    }
    $remFilesObj = $parsedCheck.files
    foreach ($name in $FileNames) {
        $rHash = Get-ObjProp -Obj $remFilesObj -Name $name -Default $null
        if ($null -eq $rHash) {
            $RemoteShaMap[$name] = "MISSING"
            $null = $Mismatches.Add($name)
        } else {
            $rHashNorm = ([string]$rHash).ToLowerInvariant()
            $RemoteShaMap[$name] = $rHashNorm
            if ($rHashNorm -ne $LocalShaMap[$name]) {
                $null = $Mismatches.Add($name)
            }
        }
    }
}

if ($Mismatches.Count -gt 0) {
    Emit-ResultAndExit -Status "SHA256_VERIFICATION_FAILED" -ExitCode 1 -Payload @{
        target_staging_dir = $RemoteStagingDir
        gates_passed       = $GateEval.gates_passed
        gates_total        = $GateEval.gates_total
        failed_gates       = @("two_sided_sha256_match")
        gates              = $GateEval.gates
        node_snapshot      = $GateEval.snapshot
        verifier_engine    = $VerifierEngine
        staged_count       = $FileNames.Count
        staged_files       = @($FileNames.ToArray())
        local_sha256       = $LocalShaMap
        remote_sha256      = $RemoteShaMap
        sha256_verified    = $false
        sha256_mismatches  = @($Mismatches.ToArray())
        message            = ("Two-sided SHA-256 mismatch on: {0}" -f ($Mismatches -join ", "))
    }
}

Emit-ResultAndExit -Status "STAGED_CLEAN_FLAT" -ExitCode 0 -Payload @{
    target_staging_dir = $RemoteStagingDir
    gates_passed       = $GateEval.gates_passed
    gates_total        = $GateEval.gates_total
    failed_gates       = @()
    gates              = $GateEval.gates
    node_snapshot      = $GateEval.snapshot
    verifier_engine    = $VerifierEngine
    staged_count       = $FileNames.Count
    staged_files       = @($FileNames.ToArray())
    local_sha256       = $LocalShaMap
    remote_sha256      = $RemoteShaMap
    sha256_verified    = $true
    sha256_mismatches  = @()
    message            = "Staged cleanly into isolated staging directory with 100% two-sided SHA-256 match (0 live overwrites)."
}

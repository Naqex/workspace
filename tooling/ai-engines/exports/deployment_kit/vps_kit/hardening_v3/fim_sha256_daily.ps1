<#
.SYNOPSIS
    Daily File Integrity Monitoring (FIM) SHA-256 auditor for naqex-node1 (Hardening v3, OrderSend = 0).

.DESCRIPTION
    Compares live SHA-256 hashes of `.ex5` binaries, `.set` presets, `naqex_red_news_utc.csv`,
    and `Config\common.ini` (plus mandatory `KeepPrivate=1` and zero `Login=` override checks)
    against a pinned SHA-256 manifest JSON and emits a `GREEN` or `RED` JSON receipt.
    100% read-only against MT5 files; `-DryRun` / `-WhatIf` skips writing optional `-ReceiptOutPath`.
    Reuses and aligns with `node_integrity.py`, `node_cutover_dryrun.py`, and `manifest.sha256.json`.

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File .\fim_sha256_daily.ps1 -Mt5Root C:\Naqex\mt5 -ManifestPath C:\Naqex\ops\fim_manifest_sha256.json -DryRun
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$Mt5Root = "C:\Naqex\mt5",
    [string]$ManifestPath = "C:\Naqex\ops\fim_manifest_sha256.json",
    [string]$PresetDir = "",
    [string]$ReceiptOutPath = "",
    [int]$MinRedNewsRows = 492,
    [switch]$AllowExtraEx5,
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$SchemaVersion = "naqex-fim-sha256-daily-v3"
$InvCulture = [System.Globalization.CultureInfo]::InvariantCulture
$IsDryRun = [bool]$DryRun -or [bool]$WhatIfPreference

$ReusedOpsTools = @(
    "tooling/ai-engines/ops_cloud/node_ctl.py",
    "tooling/ai-engines/ops_cloud/node_scripts/node_integrity.py",
    "tooling/ai-engines/ops_cloud/node_cutover_dryrun.py",
    "tooling/ai-engines/exports/deployment_kit/vps_kit/sync_updated_ex5_when_flat.ps1"
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

function Read-TextAutoEncoding {
    param([string]$Path)
    $raw = [System.IO.File]::ReadAllBytes($Path)
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

function Get-Sha256Lower {
    param([string]$Path)
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Inspect-Mt5Ini {
    param([string]$IniPath)
    if (-not (Test-Path -LiteralPath $IniPath -PathType Leaf)) {
        return [ordered]@{
            exists             = $false
            keep_private       = $null
            has_login_override = $false
            sha256             = $null
        }
    }
    $txt = Read-TextAutoEncoding -Path $IniPath
    $kp = $null
    $hasLogin = $false
    foreach ($line in ($txt -split "`r?`n")) {
        $s = $line.Trim()
        if ($s -match '(?i)^keepprivate\s*=\s*(.+)$') {
            $kp = $Matches[1].Trim()
        }
        if ($s -match '(?i)^login\s*=') {
            $hasLogin = $true
        }
    }
    return [ordered]@{
        exists             = $true
        keep_private       = $kp
        has_login_override = $hasLogin
        sha256             = (Get-Sha256Lower -Path $IniPath)
    }
}

function Extract-ManifestPins {
    param($ManifestObj)
    $ex5Pins = [ordered]@{}
    $setPins = [ordered]@{}
    $csvPin = ""
    $commonIniPin = ""

    # Format A: Dedicated FIM v3 manifest (`ex5`, `presets`, `red_news_csv_sha256`, `common_ini_sha256`)
    $ex5Node = Get-ObjProp -Obj $ManifestObj -Name "ex5" -Default $null
    if ($null -ne $ex5Node) {
        foreach ($prop in $ex5Node.PSObject.Properties) {
            $val = if ($prop.Value -is [string]) { $prop.Value } else { [string](Get-ObjProp -Obj $prop.Value -Name "sha256" -Default "") }
            if (-not [string]::IsNullOrWhiteSpace($val)) {
                $ex5Pins[(Split-Path -Leaf $prop.Name)] = $val.Trim().ToLowerInvariant()
            }
        }
    }
    # Format B: Deployment kit `compiled_ex5_files` / `files`
    $compEx5 = Get-ObjProp -Obj $ManifestObj -Name "compiled_ex5_files" -Default $null
    if ($null -ne $compEx5) {
        foreach ($prop in $compEx5.PSObject.Properties) {
            $leaf = Split-Path -Leaf $prop.Name
            $val = [string](Get-ObjProp -Obj $prop.Value -Name "sha256" -Default "")
            if ($leaf -like "*.ex5" -and (-not [string]::IsNullOrWhiteSpace($val))) {
                $ex5Pins[$leaf] = $val.Trim().ToLowerInvariant()
            }
        }
    }
    $filesNode = Get-ObjProp -Obj $ManifestObj -Name "files" -Default $null
    if ($null -ne $filesNode) {
        foreach ($prop in $filesNode.PSObject.Properties) {
            $leaf = Split-Path -Leaf $prop.Name
            $val = if ($prop.Value -is [string]) { $prop.Value } else { [string](Get-ObjProp -Obj $prop.Value -Name "sha256" -Default "") }
            if ([string]::IsNullOrWhiteSpace($val)) { continue }
            if ($leaf -like "*.ex5") { $ex5Pins[$leaf] = $val.Trim().ToLowerInvariant() }
            elseif ($leaf -like "*.set") { $setPins[$leaf] = $val.Trim().ToLowerInvariant() }
        }
    }
    # Format C: Flat top-level map (`Naqex_*.ex5: "<sha256>"`)
    foreach ($prop in $ManifestObj.PSObject.Properties) {
        if ($prop.Name -like "*.ex5" -and $prop.Value -is [string]) {
            $ex5Pins[(Split-Path -Leaf $prop.Name)] = $prop.Value.Trim().ToLowerInvariant()
        }
    }

    $presetNode = Get-ObjProp -Obj $ManifestObj -Name "presets" -Default $null
    if ($null -ne $presetNode) {
        foreach ($prop in $presetNode.PSObject.Properties) {
            $val = if ($prop.Value -is [string]) { $prop.Value } else { [string](Get-ObjProp -Obj $prop.Value -Name "sha256" -Default "") }
            if (-not [string]::IsNullOrWhiteSpace($val)) {
                $setPins[(Split-Path -Leaf $prop.Name)] = $val.Trim().ToLowerInvariant()
            }
        }
    }

    $rawCsv = Get-ObjProp -Obj $ManifestObj -Name "red_news_csv_sha256" -Default ""
    if (-not [string]::IsNullOrWhiteSpace([string]$rawCsv)) {
        $csvPin = ([string]$rawCsv).Trim().ToLowerInvariant()
    } else {
        $extDeps = Get-ObjProp -Obj $ManifestObj -Name "external_dependencies" -Default $null
        if ($null -ne $extDeps) {
            foreach ($prop in $extDeps.PSObject.Properties) {
                if ($prop.Name -like "*naqex_red_news_utc.csv") {
                    $s = [string](Get-ObjProp -Obj $prop.Value -Name "snapshot_sha256" -Default (Get-ObjProp -Obj $prop.Value -Name "sha256" -Default ""))
                    if (-not [string]::IsNullOrWhiteSpace($s)) { $csvPin = $s.Trim().ToLowerInvariant() }
                }
            }
        }
    }

    $rawIni = Get-ObjProp -Obj $ManifestObj -Name "common_ini_sha256" -Default ""
    if (-not [string]::IsNullOrWhiteSpace([string]$rawIni)) {
        $commonIniPin = ([string]$rawIni).Trim().ToLowerInvariant()
    }

    return [ordered]@{
        ex5               = $ex5Pins
        presets           = $setPins
        red_news_csv_sha  = $csvPin
        common_ini_sha    = $commonIniPin
    }
}

$Failures = New-Object System.Collections.Generic.List[string]
$CheckedUtc = [DateTimeOffset]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ", $InvCulture)

if (-not (Test-Path -LiteralPath $ManifestPath -PathType Leaf)) {
    $failReceipt = [ordered]@{
        schema           = $SchemaVersion
        checked_utc      = $CheckedUtc
        dry_run          = $IsDryRun
        order_send_count = 0
        verdict          = "RED"
        failures         = @("MANIFEST_MISSING")
        reused_ops_tools = $ReusedOpsTools
    }
    Write-Output (ConvertTo-SanitizedText -Text ($failReceipt | ConvertTo-Json -Depth 5))
    exit 2
}

$ManifestObj = $null
try {
    $ManifestObj = (Get-Content -LiteralPath $ManifestPath -Raw -Encoding UTF8) | ConvertFrom-Json
} catch {
    $failReceipt = [ordered]@{
        schema           = $SchemaVersion
        checked_utc      = $CheckedUtc
        dry_run          = $IsDryRun
        order_send_count = 0
        verdict          = "RED"
        failures         = @("MANIFEST_INVALID_JSON")
        reused_ops_tools = $ReusedOpsTools
    }
    Write-Output (ConvertTo-SanitizedText -Text ($failReceipt | ConvertTo-Json -Depth 5))
    exit 2
}

$Pins = Extract-ManifestPins -ManifestObj $ManifestObj
if ($Pins.ex5.Count -eq 0) {
    $Failures.Add("MANIFEST_EMPTY_EX5_PINS")
}

# 1. Verify .ex5 binaries
$Ex5SubDir = Join-Path $Mt5Root "MQL5\Experts\Naqex"
$Ex5Dir = if (Test-Path -LiteralPath $Ex5SubDir -PathType Container) { $Ex5SubDir } else { Join-Path $Mt5Root "MQL5\Experts" }
$ActualEx5Map = @{}
if (Test-Path -LiteralPath $Ex5Dir -PathType Container) {
    foreach ($f in @(Get-ChildItem -LiteralPath $Ex5Dir -Filter "*.ex5" -File -ErrorAction SilentlyContinue | Sort-Object Name)) {
        $ActualEx5Map[$f.Name] = Get-Sha256Lower -Path $f.FullName
    }
}

$Ex5Matched = 0
$Ex5Mismatches = @()
$Ex5Unexpected = @()
foreach ($name in $Pins.ex5.Keys) {
    $exp = $Pins.ex5[$name]
    if (-not $ActualEx5Map.ContainsKey($name)) {
        $Ex5Mismatches += [ordered]@{ file = $name; status = "MISSING"; expected_16 = $exp.Substring(0, [math]::Min(16, $exp.Length)); actual_16 = "MISSING" }
        $Failures.Add("EX5_MISSING:$name")
    } elseif ($ActualEx5Map[$name] -ne $exp) {
        $act = $ActualEx5Map[$name]
        $Ex5Mismatches += [ordered]@{ file = $name; status = "SHA256_MISMATCH"; expected_16 = $exp.Substring(0, [math]::Min(16, $exp.Length)); actual_16 = $act.Substring(0, [math]::Min(16, $act.Length)) }
        $Failures.Add("EX5_SHA256_MISMATCH:$name")
    } else {
        $Ex5Matched++
    }
}
if (-not $AllowExtraEx5) {
    foreach ($actualName in ($ActualEx5Map.Keys | Sort-Object)) {
        if (-not $Pins.ex5.Contains($actualName)) {
            $Ex5Unexpected += $actualName
            $Failures.Add("UNEXPECTED_EX5:$actualName")
        }
    }
}

# 2. Verify .set presets
$ResolvedPresetDir = if (-not [string]::IsNullOrWhiteSpace($PresetDir)) { $PresetDir } else { Join-Path $Mt5Root "MQL5\Presets" }
$PresetMatched = 0
$PresetMismatches = @()
foreach ($pname in $Pins.presets.Keys) {
    $exp = $Pins.presets[$pname]
    $pp = Join-Path $ResolvedPresetDir $pname
    if (-not (Test-Path -LiteralPath $pp -PathType Leaf)) {
        $PresetMismatches += [ordered]@{ file = $pname; status = "MISSING"; expected_16 = $exp.Substring(0, [math]::Min(16, $exp.Length)); actual_16 = "MISSING" }
        $Failures.Add("PRESET_MISSING:$pname")
    } else {
        $act = Get-Sha256Lower -Path $pp
        if ($act -ne $exp) {
            $PresetMismatches += [ordered]@{ file = $pname; status = "SHA256_MISMATCH"; expected_16 = $exp.Substring(0, [math]::Min(16, $exp.Length)); actual_16 = $act.Substring(0, [math]::Min(16, $act.Length)) }
            $Failures.Add("PRESET_SHA256_MISMATCH:$pname")
        } else {
            $PresetMatched++
        }
    }
}

# 3. Verify naqex_red_news_utc.csv
$CsvPath = Join-Path $Mt5Root "MQL5\Files\naqex_red_news_utc.csv"
$CsvReport = [ordered]@{
    exists      = $false
    rows        = 0
    header_ok   = $false
    sha256_16   = $null
    sha_matched = $false
}
if (-not (Test-Path -LiteralPath $CsvPath -PathType Leaf)) {
    $Failures.Add("RED_NEWS_CSV_MISSING")
} else {
    $CsvReport.exists = $true
    $csvLines = @(Get-Content -LiteralPath $CsvPath -Encoding UTF8 | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
    $CsvReport.rows = [math]::Max(0, $csvLines.Count - 1)
    $CsvReport.header_ok = ($csvLines.Count -gt 0 -and ($csvLines[0].Trim() -like "utc_ts,ccy,event*"))
    $csvSha = Get-Sha256Lower -Path $CsvPath
    $CsvReport.sha256_16 = $csvSha.Substring(0, 16)
    if (-not $CsvReport.header_ok) {
        $Failures.Add("RED_NEWS_CSV_BAD_HEADER")
    }
    if ($CsvReport.rows -lt $MinRedNewsRows) {
        $Failures.Add("RED_NEWS_CSV_ROWS_LOW:$($CsvReport.rows)<$MinRedNewsRows")
    }
    if (-not [string]::IsNullOrWhiteSpace($Pins.red_news_csv_sha)) {
        if ($csvSha -eq $Pins.red_news_csv_sha) {
            $CsvReport.sha_matched = $true
        } else {
            $CsvReport.sha_matched = $false
            $Failures.Add("RED_NEWS_CSV_SHA256_MISMATCH")
        }
    } else {
        $CsvReport.sha_matched = $false
        $Failures.Add("RED_NEWS_CSV_PIN_MISSING")
    }
}

# 4. Verify Config\common.ini (KeepPrivate=1 + optional SHA-256) and connector.ini (no Login= override)
$CommonIniPath = Join-Path $Mt5Root "Config\common.ini"
$CommonIni = Inspect-Mt5Ini -IniPath $CommonIniPath
$CommonIniShaMatched = $true
if (-not $CommonIni.exists) {
    $Failures.Add("COMMON_INI_MISSING")
} elseif (([string]$CommonIni.keep_private).Trim() -ne "1") {
    $Failures.Add("KEEP_PRIVATE_DISABLED")
}
if (-not [string]::IsNullOrWhiteSpace($Pins.common_ini_sha)) {
    if ($CommonIni.exists -and $CommonIni.sha256 -eq $Pins.common_ini_sha) {
        $CommonIniShaMatched = $true
    } else {
        $CommonIniShaMatched = $false
        $Failures.Add("COMMON_INI_SHA256_MISMATCH")
    }
}

$ConnectorIniPath = Join-Path $Mt5Root "connector.ini"
$ConnectorIni = Inspect-Mt5Ini -IniPath $ConnectorIniPath
if ($ConnectorIni.exists -and $ConnectorIni.has_login_override) {
    $Failures.Add("CONNECTOR_INI_LOGIN_OVERRIDE_FORBIDDEN")
}

$Verdict = if ($Failures.Count -eq 0) { "GREEN" } else { "RED" }
$ExitCode = if ($Verdict -eq "GREEN") { 0 } else { 2 }

$Receipt = [ordered]@{
    schema           = $SchemaVersion
    checked_utc      = $CheckedUtc
    dry_run          = $IsDryRun
    order_send_count = 0
    verdict          = $Verdict
    summary          = [ordered]@{
        ex5_pinned       = $Pins.ex5.Count
        ex5_matched      = $Ex5Matched
        ex5_mismatches   = $Ex5Mismatches.Count
        ex5_unexpected   = $Ex5Unexpected.Count
        presets_pinned   = $Pins.presets.Count
        presets_matched  = $PresetMatched
        presets_mismatch = $PresetMismatches.Count
        red_news_ok      = ($CsvReport.exists -and $CsvReport.header_ok -and $CsvReport.sha_matched -and ($CsvReport.rows -ge $MinRedNewsRows))
        keep_private_ok  = ($CommonIni.exists -and (([string]$CommonIni.keep_private).Trim() -eq "1"))
        failure_count    = $Failures.Count
    }
    ex5              = [ordered]@{
        found_count = $ActualEx5Map.Count
        matched     = $Ex5Matched
        mismatches  = $Ex5Mismatches
        unexpected  = $Ex5Unexpected
    }
    presets          = [ordered]@{
        pinned     = $Pins.presets.Count
        matched    = $PresetMatched
        mismatches = $PresetMismatches
    }
    red_news_csv     = $CsvReport
    common_ini       = [ordered]@{
        exists             = $CommonIni.exists
        keep_private       = $CommonIni.keep_private
        sha256_16          = if ($CommonIni.sha256) { $CommonIni.sha256.Substring(0, 16) } else { $null }
        sha_pin_checked    = (-not [string]::IsNullOrWhiteSpace($Pins.common_ini_sha))
        sha_matched        = $CommonIniShaMatched
    }
    connector_ini    = [ordered]@{
        exists             = $ConnectorIni.exists
        has_login_override = $ConnectorIni.has_login_override
    }
    receipt_written  = $false
    failures         = @($Failures)
    reused_ops_tools = $ReusedOpsTools
}

$JsonText = ConvertTo-SanitizedText -Text ($Receipt | ConvertTo-Json -Depth 6)

if (-not [string]::IsNullOrWhiteSpace($ReceiptOutPath) -and (-not $IsDryRun)) {
    $parent = Split-Path -Parent $ReceiptOutPath
    if (-not [string]::IsNullOrWhiteSpace($parent) -and (-not (Test-Path -LiteralPath $parent))) {
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
    }
    $Receipt.receipt_written = $true
    $JsonText = ConvertTo-SanitizedText -Text ($Receipt | ConvertTo-Json -Depth 6)
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($ReceiptOutPath, $JsonText + "`n", $utf8NoBom)
}

Write-Output $JsonText
exit $ExitCode

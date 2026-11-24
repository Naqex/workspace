<#
.SYNOPSIS
    Naqex MT5 24/5 Windows VPS 1-Click Deployment Kit (Zero Secrets, Fail-Closed).

.DESCRIPTION
    Stages the verified 9/9 compiled Naqex .ex5 suite, official 2018-2027 red-news CSV,
    and selected Prop Firm preset profile (.set) into a target portable MT5 terminal directory
    on a Windows VPS, and optionally registers a 2-minute Windows Scheduled Task running
    `naqex_mt5_watchdog.ps1` with Telegram/Discord webhook alerting (read strictly from
    `$env:NAQEX_ALERT_WEBHOOK_URL` — never stored on disk).

    Fail-closed invariants:
      - NEVER logs into MT5, NEVER places orders, NEVER writes passwords/API keys.
      - Verifies all 9 .ex5 binaries exist and prints SHA-256 manifest before staging.
      - Refuses to overwrite a live terminal if `naqex_heartbeat.json` shows `open_positions > 0`.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\install_vps_24x5.ps1 -TargetMt5Root C:\NaqexMT5 -PresetProfile The5ers_HighStakes_P1_Balanced -DryRun
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$TargetMt5Root,

    [ValidateSet(
        "FTMO_FreeTrial_DryRun",
        "FTMO_FreeTrial_Demo",
        "FTMO_P1_Balanced_3to6m",
        "FTMO_P1_Sprint_1to3m",
        "FTMO_P2_Verify",
        "FTMO_Funded_Swing_Safe",
        "FTMO_Funded_Std_RedNews",
        "The5ers_HighStakes_P1_Balanced",
        "The5ers_HighStakes_P1_Sprint",
        "The5ers_HighStakes_Funded"
    )]
    [string]$PresetProfile = "The5ers_HighStakes_P1_Balanced",

    [string]$AccountLabel = "NAQEX_VPS_MT5",
    [string]$Ex5SourceDir = "",
    [switch]$RegisterWatchdogTask,
    [switch]$EnableWebhook,
    [switch]$DryRun
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
$PresetDir = Join-Path (Join-Path $KitRoot "presets") $PresetProfile
$WatchdogScript = Join-Path (Join-Path $KitRoot "ops_watchdog") "naqex_mt5_watchdog.ps1"
$RedNewsCsv = Join-Path (Join-Path $ExportsDir "Files") "naqex_red_news_utc.csv"

$RequiredEx5 = @(
    "Naqex_AccountOrchestrator.ex5",
    "Naqex_WB_TOKYO_BOX_USDJPY.ex5",
    "Naqex_WB_EXP080_USDJPY.ex5",
    "Naqex_WB_EXP080_VOLHIGH_GBPUSD.ex5",
    "Naqex_WB_SESS_CONT_BRK40_US100.ex5",
    "Naqex_WB_IDX_RS_US100_LEAD_1130.ex5",
    "Naqex_WB_VOLCOMP_EXP75_EURJPY.ex5",
    "Naqex_WB_NY_RISK_FLOW_10ET_USDJPY.ex5",
    "Naqex_WB_FX_USD_BASKET_12U_Z35.ex5"
)

# 1. Verify all 9 compiled .ex5 + red-news CSV + preset directory exist
$Hashes = [ordered]@{}
foreach ($name in $RequiredEx5) {
    $src = Join-Path $ResolvedEx5Dir $name
    if (-not (Test-Path -LiteralPath $src)) {
        throw "MISSING_COMPILED_EX5: $src (compile all 9 .mq5 into .runtime\mt5-compiled-ex5 first!)"
    }
    $Hashes[$name] = (Get-FileHash -LiteralPath $src -Algorithm SHA256).Hash.ToLowerInvariant()
}
if (-not (Test-Path -LiteralPath $RedNewsCsv)) {
    throw "MISSING_RED_NEWS_CSV: $RedNewsCsv"
}
if (-not (Test-Path -LiteralPath $PresetDir)) {
    throw "MISSING_PRESET_PROFILE: $PresetDir"
}

# 2. Fail-closed guard: refuse overwrite if target terminal currently holds open positions!
$TargetMql5 = Join-Path $TargetMt5Root "MQL5"
$TargetExperts = Join-Path (Join-Path $TargetMql5 "Experts") "Naqex"
$TargetPresets = Join-Path $TargetMql5 "Presets"
$TargetFiles = Join-Path $TargetMql5 "Files"
$TargetHb = Join-Path $TargetFiles "naqex_heartbeat.json"

if (Test-Path -LiteralPath $TargetHb) {
    $hb = Get-Content -LiteralPath $TargetHb -Raw -Encoding UTF8 | ConvertFrom-Json
    if ([int]$hb.open_positions -gt 0) {
        throw "REFUSED_OPEN_POSITIONS: $TargetHb reports open_positions=$($hb.open_positions). Wait until flat before deploying!"
    }
}

$Actions = New-Object System.Collections.Generic.List[string]
if (-not $DryRun) {
    New-Item -ItemType Directory -Force -Path $TargetExperts, $TargetPresets, $TargetFiles | Out-Null
    foreach ($name in $RequiredEx5) {
        Copy-Item -LiteralPath (Join-Path $ResolvedEx5Dir $name) -Destination (Join-Path $TargetExperts $name) -Force
    }
    Copy-Item -LiteralPath $RedNewsCsv -Destination (Join-Path $TargetFiles "naqex_red_news_utc.csv") -Force
    Get-ChildItem -LiteralPath $PresetDir -Filter "*.set" | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $TargetPresets $_.Name) -Force
    }
    $Actions.Add("STAGED_9_EX5_AND_PRESETS:$PresetProfile")
} else {
    $Actions.Add("DRYRUN_VERIFIED_9_EX5_AND_PRESETS:$PresetProfile")
}

# 3. Optional Windows Scheduled Task registration (2-minute watchdog heartbeat & webhook alert)
$TaskName = "Naqex_MT5_Watchdog_$AccountLabel"
$WebhookFlag = if ($EnableWebhook) { " -EnableWebhook" } else { "" }
$WatchdogCmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$WatchdogScript`" -HeartbeatPath `"$TargetHb`" -AccountLabel `"$AccountLabel`"$WebhookFlag"

if ($RegisterWatchdogTask) {
    if ($DryRun) {
        $Actions.Add("DRYRUN_WOULD_REGISTER_SCHTASK:$TaskName")
    } else {
        schtasks /Create /TN $TaskName /SC MINUTE /MO 2 /TR $WatchdogCmd /F | Out-Null
        $Actions.Add("REGISTERED_SCHTASK:$TaskName")
    }
}

$Summary = [ordered]@{
    schema          = "naqex-vps-24x5-install-v1"
    utc             = [DateTimeOffset]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
    dry_run         = [bool]$DryRun
    order_send      = 0
    preset_profile  = $PresetProfile
    target_mt5_root = $TargetMt5Root
    account_label   = $AccountLabel
    ex5_count       = $RequiredEx5.Count
    ex5_sha256      = $Hashes
    watchdog_cmd    = $WatchdogCmd
    actions         = @($Actions)
}

Write-Output ($Summary | ConvertTo-Json -Depth 6)
exit 0

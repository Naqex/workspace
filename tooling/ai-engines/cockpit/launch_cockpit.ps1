<#
.SYNOPSIS
  Launch Naqex Quant Pod Local Interactive Web Control Room (127.0.0.1:8787, OrderSend=0).
.DESCRIPTION
  Uses workspace Quant Python runtime (.runtime\quant-audit-v24\Scripts\python.exe),
  binds strictly to 127.0.0.1, requires zero external packages or CDNs.
#>
param(
    [int]$Port = 8787,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$PyExe = Join-Path $RepoRoot ".runtime\quant-audit-v24\Scripts\python.exe"
$ServerPy = Join-Path $PSScriptRoot "server.py"

if (-not (Test-Path -LiteralPath $PyExe)) {
    throw "Quant Python runtime not found at $PyExe"
}
if (-not (Test-Path -LiteralPath $ServerPy)) {
    throw "Cockpit server script not found at $ServerPy"
}

$Url = "http://127.0.0.1:$Port"
Write-Host "=== Naqex Quant Pod Web Control Room ===" -ForegroundColor Cyan
Write-Host "URL: $Url | Localhost Only | OrderSend = 0 | Holdout 2025+ SEALED" -ForegroundColor Green

if (-not $NoBrowser) {
    Start-Job -ScriptBlock {
        param($u)
        Start-Sleep -Milliseconds 900
        Start-Process $u
    } -ArgumentList $Url | Out-Null
}

& $PyExe -X utf8 $ServerPy --host 127.0.0.1 --port $Port

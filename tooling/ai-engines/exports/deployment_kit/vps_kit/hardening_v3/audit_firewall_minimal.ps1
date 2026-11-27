<#
.SYNOPSIS
    Read-only Windows Firewall posture auditor for naqex-node1 (Hardening v3, OrderSend = 0).

.DESCRIPTION
    Audits Windows Defender Firewall profile state, minimal outbound allowlist readiness
    (MT5 broker TCP 443, NTP UDP 123, Heroku Dead-Man HTTPS TCP 443, Tailscale UDP 41641),
    and unauthorized non-loopback inbound listening ports or overly broad inbound rules.
    100% read-only: NEVER modifies firewall rules, NEVER touches MT5, NEVER emits raw IPv4/IPv6.
    Reuses and complements `node_ctl.py`, `ftmo_pre_checkout_guard.py`, and `naqex_mt5_watchdog.ps1`.

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File .\audit_firewall_minimal.ps1 -DryRun
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [int[]]$AllowedInboundTcpPorts = @(22),
    [int[]]$AllowedInboundUdpPorts = @(41641),
    [string]$OfflineFixturePath = "",
    [string]$OutputJsonPath = "",
    [switch]$StrictExit,
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$SchemaVersion = "naqex-firewall-minimal-audit-v3"
$InvCulture = [System.Globalization.CultureInfo]::InvariantCulture
$IsDryRun = [bool]$DryRun -or [bool]$WhatIfPreference

$RequiredOutboundFlows = @(
    [ordered]@{ id = "broker_mt5_tls";       protocol = "TCP"; port = 443;   target = "MT5 Broker Trade/Quote TLS" },
    [ordered]@{ id = "ntp_time_sync";        protocol = "UDP"; port = 123;   target = "w32time NTP (Cloudflare/Google)" },
    [ordered]@{ id = "heroku_deadman_https"; protocol = "TCP"; port = 443;   target = "<HEROKU_DEADMAN_APP> HTTPS" },
    [ordered]@{ id = "tailscale_wireguard";  protocol = "UDP"; port = 41641; target = "Tailscale Mesh (100.64.0.0/10)" }
)

$ReusedOpsTools = @(
    "tooling/ai-engines/ops_cloud/node_ctl.py",
    "tooling/ai-engines/ops_cloud/ftmo_pre_checkout_guard.py",
    "tooling/ai-engines/ops_cloud/node_weekly_digest.py",
    "tooling/ai-engines/exports/deployment_kit/ops_watchdog/naqex_mt5_watchdog.ps1"
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
    $out = [regex]::Replace($out, '(?i)\b(password|passwd|token|api[_-]?key|secret|webhook|bearer)\s*[:=]\s*\S+', '$1=[REDACTED]')
    $out = [regex]::Replace($out, '(?i)(?:\b(?:[0-9a-f]{1,4}:){3,7}[0-9a-f]{1,4}\b|(?:[0-9a-f]{1,4}:){1,6}:[0-9a-f:]{1,20}|::[0-9a-f:]{1,20})', '[REDACTED_IPV6]')
    $out = [regex]::Replace($out, '\b(?!100\.64\.0\.0/10\b)(?:\d{1,3}\.){3}\d{1,3}\b', '[REDACTED_IP]')
    $out = [regex]::Replace($out, '(?i)[A-Z]:\\Users\\[^\\/\s"'']+', 'C:\Users\<USER>')
    $out = $out.Replace('$', 'USD ')
    return $out
}

function Classify-AddressScope {
    param([string]$RawAddress)
    if ([string]::IsNullOrWhiteSpace($RawAddress)) { return "UNKNOWN" }
    $s = $RawAddress.Trim()
    $knownScopes = @("ANY_ADDR", "LAN_SUBNET", "LAN_PRIVATE", "TAILSCALE_CGNAT", "LOOPBACK", "LINK_LOCAL", "PUBLIC_IP_REDACTED", "IPV6_REDACTED", "SCOPED_CUSTOM", "UNKNOWN")
    if ($knownScopes -contains $s.ToUpperInvariant()) {
        return $s.ToUpperInvariant()
    }
    if ($s -eq "Any" -or $s -eq "*" -or $s -eq "0.0.0.0" -or $s -eq "::" -or $s -eq "0.0.0.0/0") {
        return "ANY_ADDR"
    }
    if ($s -eq "LocalSubnet") { return "LAN_SUBNET" }
    if ($s -eq "100.64.0.0/10" -or $s -eq "<TAILSCALE_IP>") { return "TAILSCALE_CGNAT" }
    if ($s -eq "<LAN_SUBNET>" -or $s -eq "<LAN_IP>") { return "LAN_PRIVATE" }
    if ($s -eq "127.0.0.1" -or $s -eq "::1" -or $s -eq "localhost") { return "LOOPBACK" }

    $ipPart = $s.Split('/')[0]
    $ipObj = $null
    if ([System.Net.IPAddress]::TryParse($ipPart, [ref]$ipObj)) {
        if ([System.Net.IPAddress]::IsLoopback($ipObj)) { return "LOOPBACK" }
        if ($ipObj.AddressFamily -eq [System.Net.Sockets.AddressFamily]::InterNetwork) {
            $b = $ipObj.GetAddressBytes()
            if ($b[0] -eq 0 -and $b[1] -eq 0 -and $b[2] -eq 0 -and $b[3] -eq 0) { return "ANY_ADDR" }
            if ($b[0] -eq 100 -and $b[1] -ge 64 -and $b[1] -le 127) { return "TAILSCALE_CGNAT" }
            if ($b[0] -eq 10) { return "LAN_PRIVATE" }
            if ($b[0] -eq 172 -and $b[1] -ge 16 -and $b[1] -le 31) { return "LAN_PRIVATE" }
            if ($b[0] -eq 192 -and $b[1] -eq 168) { return "LAN_PRIVATE" }
            if ($b[0] -eq 169 -and $b[1] -eq 254) { return "LINK_LOCAL" }
            return "PUBLIC_IP_REDACTED"
        }
        if ($ipObj.AddressFamily -eq [System.Net.Sockets.AddressFamily]::InterNetworkV6) {
            if ($ipObj.IsIPv6LinkLocal) { return "LINK_LOCAL" }
            if ($ipObj.Equals([System.Net.IPAddress]::IPv6Any)) { return "ANY_ADDR" }
            return "IPV6_REDACTED"
        }
    }
    return "SCOPED_CUSTOM"
}

function Test-PortMatchesSpec {
    param([string]$Spec, [int]$TargetPort)
    if ([string]::IsNullOrWhiteSpace($Spec)) { return $false }
    $trim = $Spec.Trim()
    if ($trim -ieq "Any" -or $trim -eq "*") { return $true }
    foreach ($tok in ($trim -split ',')) {
        $t = $tok.Trim()
        if ($t -match '^\d+$') {
            if ([int]$t -eq $TargetPort) { return $true }
        } elseif ($t -match '^(\d+)-(\d+)$') {
            $lo = [int]$Matches[1]
            $hi = [int]$Matches[2]
            if ($TargetPort -ge $lo -and $TargetPort -le $hi) { return $true }
        }
    }
    return $false
}

function Test-ProtocolMatches {
    param([string]$RuleProto, [string]$FlowProto)
    if ([string]::IsNullOrWhiteSpace($RuleProto)) { return $true }
    $rp = $RuleProto.Trim().ToUpperInvariant()
    $fp = $FlowProto.Trim().ToUpperInvariant()
    if ($rp -eq "ANY" -or $rp -eq $fp) { return $true }
    if ($rp -eq "6" -and $fp -eq "TCP") { return $true }
    if ($rp -eq "17" -and $fp -eq "UDP") { return $true }
    return $false
}

function Collect-LiveFirewallSnapshot {
    $profiles = @()
    try {
        foreach ($p in @(Get-NetFirewallProfile -ErrorAction Stop)) {
            $profiles += [ordered]@{
                name                    = [string]$p.Name
                enabled                 = [bool]$p.Enabled
                default_inbound_action  = [string]$p.DefaultInboundAction
                default_outbound_action = [string]$p.DefaultOutboundAction
            }
        }
    } catch {
        $profiles += [ordered]@{
            name                    = "UNAVAILABLE"
            enabled                 = $false
            default_inbound_action  = "UNKNOWN"
            default_outbound_action = "UNKNOWN"
            error                   = "Get-NetFirewallProfile unavailable"
        }
    }

    $tcpListeners = @()
    try {
        foreach ($c in @(Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue)) {
            $scope = Classify-AddressScope -RawAddress ([string]$c.LocalAddress)
            if ($scope -eq "LOOPBACK") { continue }
            $procName = "PID_" + [string]$c.OwningProcess
            try {
                $pr = Get-Process -Id $c.OwningProcess -ErrorAction SilentlyContinue
                if ($null -ne $pr -and -not [string]::IsNullOrWhiteSpace($pr.ProcessName)) {
                    $procName = [string]$pr.ProcessName
                }
            } catch {}
            $tcpListeners += [ordered]@{
                protocol      = "TCP"
                port          = [int]$c.LocalPort
                address_scope = $scope
                process       = $procName
            }
        }
    } catch {}

    $udpListeners = @()
    try {
        foreach ($u in @(Get-NetUDPEndpoint -ErrorAction SilentlyContinue)) {
            $scope = Classify-AddressScope -RawAddress ([string]$u.LocalAddress)
            if ($scope -eq "LOOPBACK") { continue }
            $procName = "PID_" + [string]$u.OwningProcess
            try {
                $pr = Get-Process -Id $u.OwningProcess -ErrorAction SilentlyContinue
                if ($null -ne $pr -and -not [string]::IsNullOrWhiteSpace($pr.ProcessName)) {
                    $procName = [string]$pr.ProcessName
                }
            } catch {}
            $udpListeners += [ordered]@{
                protocol      = "UDP"
                port          = [int]$u.LocalPort
                address_scope = $scope
                process       = $procName
            }
        }
    } catch {}

    $rules = @()
    try {
        $allEnabled = @(Get-NetFirewallRule -Enabled True -ErrorAction SilentlyContinue)
        $portFilters = @{}
        foreach ($pf in @(Get-NetFirewallPortFilter -ErrorAction SilentlyContinue)) {
            $portFilters[[string]$pf.InstanceID] = $pf
        }
        $addrFilters = @{}
        foreach ($af in @(Get-NetFirewallAddressFilter -ErrorAction SilentlyContinue)) {
            $addrFilters[[string]$af.InstanceID] = $af
        }
        foreach ($r in $allEnabled) {
            $id = [string]$r.Name
            $pf = if ($portFilters.ContainsKey($id)) { $portFilters[$id] } else { $null }
            $af = if ($addrFilters.ContainsKey($id)) { $addrFilters[$id] } else { $null }
            $remRaw = if ($null -ne $af) { @($af.RemoteAddress) -join "," } else { "Any" }
            $remScopes = @()
            foreach ($tok in ($remRaw -split ',')) {
                $remScopes += Classify-AddressScope -RawAddress $tok
            }
            $rules += [ordered]@{
                name          = [string]$r.DisplayName
                direction     = [string]$r.Direction
                action        = [string]$r.Action
                protocol      = if ($null -ne $pf) { [string]$pf.Protocol } else { "Any" }
                local_port    = if ($null -ne $pf) { (@($pf.LocalPort) -join ",") } else { "Any" }
                remote_port   = if ($null -ne $pf) { (@($pf.RemotePort) -join ",") } else { "Any" }
                remote_scopes = @($remScopes | Select-Object -Unique)
            }
        }
    } catch {}

    return [ordered]@{
        source        = "live_windows_firewall_readonly"
        profiles      = $profiles
        tcp_listeners = $tcpListeners
        udp_listeners = $udpListeners
        rules         = $rules
    }
}

$Snapshot = $null
if (-not [string]::IsNullOrWhiteSpace($OfflineFixturePath)) {
    if (-not (Test-Path -LiteralPath $OfflineFixturePath -PathType Leaf)) {
        $errObj = [ordered]@{
            schema           = $SchemaVersion
            checked_utc      = [DateTimeOffset]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ", $InvCulture)
            dry_run          = $IsDryRun
            order_send_count = 0
            firewall_mutated = $false
            verdict          = "RED"
            error            = "OFFLINE_FIXTURE_NOT_FOUND"
        }
        Write-Output ($errObj | ConvertTo-Json -Depth 5)
        exit 2
    }
    $fx = (Get-Content -LiteralPath $OfflineFixturePath -Raw -Encoding UTF8) | ConvertFrom-Json
    $normTcp = @()
    foreach ($item in @(Get-ObjProp -Obj $fx -Name "tcp_listeners" -Default @())) {
        $normTcp += [ordered]@{
            protocol      = "TCP"
            port          = [int](Get-ObjProp -Obj $item -Name "port" -Default 0)
            address_scope = Classify-AddressScope -RawAddress ([string](Get-ObjProp -Obj $item -Name "address_scope" -Default (Get-ObjProp -Obj $item -Name "local_address" -Default "ANY_ADDR")))
            process       = ConvertTo-SanitizedText -Text ([string](Get-ObjProp -Obj $item -Name "process" -Default "unknown"))
        }
    }
    $normUdp = @()
    foreach ($item in @(Get-ObjProp -Obj $fx -Name "udp_listeners" -Default @())) {
        $normUdp += [ordered]@{
            protocol      = "UDP"
            port          = [int](Get-ObjProp -Obj $item -Name "port" -Default 0)
            address_scope = Classify-AddressScope -RawAddress ([string](Get-ObjProp -Obj $item -Name "address_scope" -Default (Get-ObjProp -Obj $item -Name "local_address" -Default "ANY_ADDR")))
            process       = ConvertTo-SanitizedText -Text ([string](Get-ObjProp -Obj $item -Name "process" -Default "unknown"))
        }
    }
    $normRules = @()
    foreach ($r in @(Get-ObjProp -Obj $fx -Name "rules" -Default @())) {
        $rawScopes = @(Get-ObjProp -Obj $r -Name "remote_scopes" -Default @())
        if ($rawScopes.Count -eq 0) {
            $rawAddr = [string](Get-ObjProp -Obj $r -Name "remote_address" -Default "Any")
            $rawScopes = @((Classify-AddressScope -RawAddress $rawAddr))
        } else {
            $rawScopes = @($rawScopes | ForEach-Object { Classify-AddressScope -RawAddress ([string]$_) })
        }
        $normRules += [ordered]@{
            name          = ConvertTo-SanitizedText -Text ([string](Get-ObjProp -Obj $r -Name "name" -Default "unnamed"))
            direction     = [string](Get-ObjProp -Obj $r -Name "direction" -Default "Inbound")
            action        = [string](Get-ObjProp -Obj $r -Name "action" -Default "Allow")
            protocol      = [string](Get-ObjProp -Obj $r -Name "protocol" -Default "Any")
            local_port    = [string](Get-ObjProp -Obj $r -Name "local_port" -Default "Any")
            remote_port   = [string](Get-ObjProp -Obj $r -Name "remote_port" -Default "Any")
            remote_scopes = @($rawScopes | Select-Object -Unique)
        }
    }
    $Snapshot = [ordered]@{
        source        = "offline_fixture"
        profiles      = @(Get-ObjProp -Obj $fx -Name "profiles" -Default @())
        tcp_listeners = $normTcp
        udp_listeners = $normUdp
        rules         = $normRules
    }
} else {
    $Snapshot = Collect-LiveFirewallSnapshot
}

$RedFindings = New-Object System.Collections.Generic.List[string]
$AmberFindings = New-Object System.Collections.Generic.List[string]

# 1. Profile checks
$ProfileReport = @()
$AllOutboundDefaultBlock = $true
$AnyProfileChecked = $false
foreach ($prof in @($Snapshot.profiles)) {
    $AnyProfileChecked = $true
    $pName = [string](Get-ObjProp -Obj $prof -Name "name" -Default "UNKNOWN")
    $pEnabled = [bool](Get-ObjProp -Obj $prof -Name "enabled" -Default $false)
    $pIn = [string](Get-ObjProp -Obj $prof -Name "default_inbound_action" -Default "UNKNOWN")
    $pOut = [string](Get-ObjProp -Obj $prof -Name "default_outbound_action" -Default "UNKNOWN")
    if (-not $pEnabled) {
        $RedFindings.Add("FIREWALL_PROFILE_DISABLED:$pName")
    }
    if ($pIn -ine "Block" -and $pIn -ine "NotConfigured") {
        $RedFindings.Add("INBOUND_DEFAULT_NOT_BLOCK:${pName}:$pIn")
    }
    if ($pOut -ine "Block") {
        $AllOutboundDefaultBlock = $false
    }
    $ProfileReport += [ordered]@{
        name                    = $pName
        enabled                 = $pEnabled
        default_inbound_action  = $pIn
        default_outbound_action = $pOut
    }
}
if (-not $AnyProfileChecked) {
    $RedFindings.Add("NO_FIREWALL_PROFILES_FOUND")
}
if (-not $AllOutboundDefaultBlock) {
    $AmberFindings.Add("OUTBOUND_DEFAULT_ALLOW_RECOMMEND_MINIMAL_ALLOWLIST")
}

# 2. Minimal outbound allowlist checks (MT5 443, NTP UDP 123, Heroku 443, Tailscale UDP 41641)
$OutboundChecks = @()
$OutboundRules = @($Snapshot.rules | Where-Object { ([string]$_.direction) -ieq "Outbound" })
foreach ($flow in $RequiredOutboundFlows) {
    $explicitAllow = $false
    $explicitBlock = $false
    foreach ($r in $OutboundRules) {
        $protoMatch = Test-ProtocolMatches -RuleProto ([string]$r.protocol) -FlowProto ([string]$flow.protocol)
        $portMatch = Test-PortMatchesSpec -Spec ([string]$r.remote_port) -TargetPort ([int]$flow.port)
        if ($protoMatch -and $portMatch) {
            if (([string]$r.action) -ieq "Block") { $explicitBlock = $true }
            if (([string]$r.action) -ieq "Allow") { $explicitAllow = $true }
        }
    }
    $permitted = (-not $explicitBlock) -and ($explicitAllow -or (-not $AllOutboundDefaultBlock))
    if (-not $permitted) {
        $RedFindings.Add("REQUIRED_OUTBOUND_BLOCKED:$($flow.id):$($flow.protocol)/$($flow.port)")
    }
    $OutboundChecks += [ordered]@{
        id             = $flow.id
        protocol       = $flow.protocol
        port           = $flow.port
        target         = $flow.target
        explicit_allow = $explicitAllow
        explicit_block = $explicitBlock
        permitted      = $permitted
    }
}

# 3. Unauthorized non-loopback inbound listening ports
$UnauthorizedListeners = @()
$AllowedListeners = @()
$SeenListenerKeys = @{}
foreach ($l in @($Snapshot.tcp_listeners) + @($Snapshot.udp_listeners)) {
    $proto = [string]$l.protocol
    $port = [int]$l.port
    $scope = [string]$l.address_scope
    $proc = [string]$l.process
    if ($scope -eq "LOOPBACK") { continue }
    $dedupKey = "$proto|$port|$scope|$proc"
    if ($SeenListenerKeys.ContainsKey($dedupKey)) { continue }
    $SeenListenerKeys[$dedupKey] = $true

    $isAllowed = if ($proto -eq "TCP") {
        $AllowedInboundTcpPorts -contains $port
    } else {
        $AllowedInboundUdpPorts -contains $port
    }
    $entry = [ordered]@{
        protocol      = $proto
        port          = $port
        address_scope = $scope
        process       = $proc
    }
    if ($isAllowed) {
        $AllowedListeners += $entry
    } else {
        $UnauthorizedListeners += $entry
    }
}
if ($UnauthorizedListeners.Count -gt 0) {
    $RedFindings.Add("UNAUTHORIZED_INBOUND_LISTENERS:count=$($UnauthorizedListeners.Count)")
}

# 4. Overly broad inbound Allow rules (Any remote scope on SSH/RDP/SMB/unauthorized ports)
$InboundAllowRules = @($Snapshot.rules | Where-Object { ([string]$_.direction) -ieq "Inbound" -and ([string]$_.action) -ieq "Allow" })
$BroadInboundRules = @()
foreach ($r in $InboundAllowRules) {
    $scopes = @($r.remote_scopes)
    $isAnyRemote = ($scopes -contains "ANY_ADDR")
    $lport = [string]$r.local_port
    $isHighRiskPort = (
        (Test-PortMatchesSpec -Spec $lport -TargetPort 22) -or
        (Test-PortMatchesSpec -Spec $lport -TargetPort 3389) -or
        (Test-PortMatchesSpec -Spec $lport -TargetPort 445) -or
        (Test-PortMatchesSpec -Spec $lport -TargetPort 135) -or
        (Test-PortMatchesSpec -Spec $lport -TargetPort 139)
    )
    if ($isAnyRemote -and $isHighRiskPort) {
        $BroadInboundRules += [ordered]@{
            name          = [string]$r.name
            protocol      = [string]$r.protocol
            local_port    = $lport
            remote_scopes = $scopes
            recommendation = "Restrict remote scope strictly to <LAN_SUBNET> and 100.64.0.0/10"
        }
    }
}
if ($BroadInboundRules.Count -gt 0) {
    $RedFindings.Add("OVERLY_BROAD_INBOUND_ALLOW_RULES:count=$($BroadInboundRules.Count)")
}

$Verdict = "GREEN"
$StrictCode = 0
if ($RedFindings.Count -gt 0) {
    $Verdict = "RED"
    $StrictCode = 2
} elseif ($AmberFindings.Count -gt 0) {
    $Verdict = "AMBER"
    $StrictCode = 1
}

$Report = [ordered]@{
    schema                       = $SchemaVersion
    checked_utc                  = [DateTimeOffset]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ", $InvCulture)
    source                       = $Snapshot.source
    dry_run                      = $IsDryRun
    order_send_count             = 0
    firewall_mutated             = $false
    verdict                      = $Verdict
    strict_exit_code             = $StrictCode
    outbound_posture_mode        = if ($AllOutboundDefaultBlock) { "STRICT_ALLOWLIST" } else { "DEFAULT_ALLOW_BASELINE" }
    allowed_inbound_tcp_ports    = @($AllowedInboundTcpPorts)
    allowed_inbound_udp_ports    = @($AllowedInboundUdpPorts)
    allowed_remote_admin_scope   = "<LAN_SUBNET>, 100.64.0.0/10"
    profiles                     = $ProfileReport
    required_outbound_allowlist  = $OutboundChecks
    allowed_inbound_listeners    = $AllowedListeners
    unauthorized_inbound_count   = $UnauthorizedListeners.Count
    unauthorized_inbound_sample  = @($UnauthorizedListeners | Select-Object -First 25)
    overly_broad_inbound_rules   = @($BroadInboundRules | Select-Object -First 15)
    red_findings                 = @($RedFindings)
    amber_findings               = @($AmberFindings)
    reused_ops_tools             = $ReusedOpsTools
}

$JsonText = ConvertTo-SanitizedText -Text ($Report | ConvertTo-Json -Depth 6)

if (-not [string]::IsNullOrWhiteSpace($OutputJsonPath) -and (-not $IsDryRun)) {
    $parent = Split-Path -Parent $OutputJsonPath
    if (-not [string]::IsNullOrWhiteSpace($parent) -and (-not (Test-Path -LiteralPath $parent))) {
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
    }
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($OutputJsonPath, $JsonText + "`n", $utf8NoBom)
}

Write-Output $JsonText

if ($IsDryRun -and (-not $StrictExit)) {
    exit 0
}
exit $StrictCode

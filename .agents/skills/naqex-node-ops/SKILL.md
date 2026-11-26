---
name: naqex-node-ops
description: Operate and maintain the Windows 10 IoT LTSC Home-VPS over SSH, cloud dead-man's-switch monitor, alert bot, and read-only crypto shadow collectors. Use for node health/NTP/storage/update checks and fail-closed flat-only .ex5/red-news sync; do not use for strategy R&D, UI, lessons, or Holdout.
---

# Naqex Home-VPS & Cloud Dead-Man's-Switch Operations

Keep the dedicated Windows 10 Home-VPS (`naqex-node1`), cloud dead-man's-switch monitor (`<HEROKU_DEADMAN_APP>`), and alert bot (`<TELEGRAM_GUARD_BOT>`) reliable, synchronized, secret-free, and fail-closed.

> **2-Layer OPSEC Rule:** This public Layer-1 skill uses generic placeholders only (`<LAN_IP>`, `<TAILSCALE_IP>`, `<SSH_USER>`, `<HEROKU_DEADMAN_APP>`, `<TELEGRAM_GUARD_BOT>`). Read live parameters strictly from gitignored `private_vault/ops/naqex-node1-topology.md` — never commit real IPs, handles, or broker logins into Layer 1.

## Hard Safety Boundaries (Fail-Closed)

1. **`OrderSend = 0` & Manual Broker Auth:** All ops scripts, heartbeats, watchdogs, and cloud monitors are strictly read-only (`OrderSend = 0`). Broker login happens manually inside MT5 Portable GUI — never store broker passwords in scripts, env files, chat, or Git.
2. **Flat-Only Mutation & `KeepPrivate=1` Gate:** Never overwrite `.ex5` binaries, swap active presets, stop/restart `terminal64.exe`, or reboot `naqex-node1` while `naqex_heartbeat.json` shows `open_positions > 0` or `terminal_connected != true`. Before any MT5 restart, confirm `Config\common.ini` and `connector.ini` set `KeepPrivate=1` with NO blank `Login=` override.
3. **3-Node Plane Isolation:** `naqex-node1` is strictly the 24/5 Execution Plane (`C:\Naqex\{mt5,ops,logs,tools}`, pagefile locked to `C:\pagefile.sys`, NEVER place MT5/DB/pagefile on broken-latch `E:`). Never install AI CLIs, Node.js, Docker, Chrome, or MT5 MCP on `naqex-node1`; never run backtests/Monte Carlo there; never connect `<X13_WORKER>` directly to `naqex-node1`.
4. **Zero-Secret & LTSC Supply-Chain Guard:** Never pass tokens (`HEROKU_API_KEY`, `NAQEX_*_TOKEN`, `TELEGRAM_BOT_TOKEN`) via CLI arguments or tracked files. Install/upgrade tools only from official Microsoft/GitHub/Astral archives and `--only-binary=:all:` wheels (never `curl | bash` or `irm | iex`).
5. **Holdout & Scope Isolation:** Never touch sealed `2025+` Holdout (`NATIVE_FTMO_HOLDOUT_LOCK.json`), global `AGENTS.md`, or unrelated submodules.

## Quick Operational Workflow

1. **Single-Command Health Audit (`< 0.5s`, `0%` background CPU):** Run [node_ctl.py](../../../tooling/ai-engines/ops_cloud/node_ctl.py) (`status | logs | integrity | maint | audit`; single-handshake LAN `naqex-node1` -> Tailscale `naqex-node1-ts` on `rc=255`). Never call `MetaTrader5.initialize()` from SSH Session `0`.
2. **Verify Core Invariants:** Clock drift `< 2s` (`< 1s` before live quote captures), `C:` free `> 20 GB`, daily backup on `D:\NaqexBackup\daily\`, Win10 IoT LTSC anti-auto-reboot + `DISKIDLE=0` + `AutoAdminLogon=1`, Heroku `/health` (`12 USD/mo <= 13 USD/mo` student cap) + `/api/status` (`X-Naqex-View-Token`, heartbeat `< 120s`).
3. **Flat-Only `.ex5` / Red-News Sync:** Compile locally into `.runtime/mt5-compiled-ex5/`, verify `open_positions == 0` via [sync_updated_ex5_when_flat.ps1](../../../tooling/ai-engines/exports/deployment_kit/vps_kit/sync_updated_ex5_when_flat.ps1), verify SHA-256 match bit-for-bit, restart via Scheduled Task, and confirm `[PROPGUARD-OK]` in `MQL5\Logs\YYYYMMDD.log`.
4. **Detailed Runbook (Load On Demand):** Read [references/win10-vps-runbook.md](references/win10-vps-runbook.md) for SSH key ACLs, 3-drive storage contract, Scheduled Tasks, `KeepPrivate=1` recovery, weekend reboot checks, and Heroku deploy steps.

## Workflow Handoffs

- **Pre-deploy audit:** Run [adversarial-self-audit](../adversarial-self-audit/SKILL.md) on every new ops script, collector, or sync change before touching `naqex-node1`.
- **Peer & downstream skills:** [quant-factory-ops](../quant-factory-ops/SKILL.md) for local builds/doctor, [strategy-qualification](../strategy-qualification/SKILL.md) for gate eligibility, [evidence-continuity](../evidence-continuity/SKILL.md) for ops receipts, and [github-issue-workflow](../github-issue-workflow/SKILL.md) for clean repo commits/PRs (Layer-1 sanitized only).

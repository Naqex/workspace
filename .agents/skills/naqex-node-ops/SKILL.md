---
name: naqex-node-ops
description: Operate and maintain the Windows 10 IoT LTSC Home-VPS over SSH, cloud dead-man's-switch monitor, alert bot, and read-only crypto shadow collectors. Use for node health/NTP/storage/update checks and fail-closed flat-only .ex5/red-news sync; do not use for strategy R&D, UI, lessons, or Holdout.
---

# Naqex Home-VPS & Cloud Dead-Man's-Switch Operations

Keep the dedicated Windows 10 Home-VPS (`naqex-node1`), cloud dead-man's-switch monitor (`<HEROKU_DEADMAN_APP>`), alert bot (`<TELEGRAM_GUARD_BOT>`), and read-only shadow collectors reliable, synchronized, secret-free, and fail-closed.

> **2-Layer OPSEC Rule:** This public Layer-1 skill uses generic placeholders only. Read live node parameters (real LAN/Tailscale IPs, SSH user, cloud app name, alert handle, account login, and local backup paths) from local gitignored `private_vault/ops/naqex-node1-topology.md` when present — never commit real IPs, handles, or broker logins into Layer 1.

## Topology & Fixed Storage Contract

- **SSH Aliases (main dev PC -> `naqex-node1`, exact values in `private_vault/ops/naqex-node1-topology.md`):**
  - LAN primary (`<1ms`, router DHCP pin): `ssh naqex-node1` (`<SSH_USER>@<LAN_IP>`)
  - Tailscale remote fallback: `ssh naqex-node1-ts` (`<SSH_USER>@<TAILSCALE_IP>`)
  - Windows OpenSSH Admin key path on node: `C:\ProgramData\ssh\administrators_authorized_keys` (ASCII/UTF-8 no BOM, `icacls /inheritance:r /grant '*S-1-5-32-544:F' /grant '*S-1-5-18:F'`).
- **3-Drive Allocation on `naqex-node1`:**
  - `C:` (`119 GB` healthy Samsung SSD): Windows 10 IoT Enterprise LTSC, Pagefile locked strictly to `C:\pagefile.sys` (`AutomaticManagedPagefile = False`), `C:\Naqex\{mt5, ops, logs, tools, crypto-shadow}`.
  - `D:` (`465 GB` healthy Seagate HDD): `D:\NaqexBackup\daily\YYYYMMDD\` (30-day rolling log/audit/heartbeat backup at `05:30`).
  - `E:` (`111 GB` secondary SSD with broken SATA latch): `E:\Scratch\` non-critical scratch ONLY. **Never place MT5, live bots, databases, or pagefile on `E:`.**
- **Cloud Monitor & Alerts:**
  - Cloud app `<HEROKU_DEADMAN_APP>`: `1 × Basic` (`7 USD/mo`, 24/7 no sleep) + `heroku-postgresql:essential-0` (`5 USD/mo`, auto-pruned `10,000` rows) = `12 USD/mo <= 13 USD/mo` student credit cap (`312 USD` credit, `2026-10-01 -> 2028-09-30`; review/cancel gate `2028-09-25` before card billing).
  - Local gitignored connection pointer on main PC: `.runtime/ops-cloud/heroku_connection_local.json`.
  - Alert bot: `<TELEGRAM_GUARD_BOT>` (`TELEGRAM_BOT_TOKEN` & `TELEGRAM_CHAT_ID` stored strictly in cloud Config Vars).

## Hard Safety Boundaries (Fail-Closed)

1. **`OrderSend = 0` & Manual Broker Auth:** All ops scripts, heartbeats, watchdogs, cloud monitor, and crypto shadow collectors are strictly read-only (`OrderSend = 0`). Broker login happens manually inside MT5 Portable GUI — never store broker passwords in scripts, env files, chat logs, or Git (neither Layer 1 nor Layer 2).
2. **Flat-Only Mutation Rule:** Never overwrite `.ex5` binaries, swap active presets, stop/restart `terminal64.exe`, or reboot `naqex-node1` while `MQL5\Files\naqex_heartbeat.json` shows `open_positions > 0`. Always wait for flat (`open_positions == 0`) or weekend close (`Fri 22:00 UTC -> Sun 21:00 UTC`).
2b. **Pre-Restart Auto-Login Persistence Gate:** Before stopping or restarting `terminal64.exe` (even when flat), inspect `C:\Naqex\mt5\Config\common.ini` (and `C:\Naqex\mt5\connector.ini`) to confirm `KeepPrivate=1` with NO blank-password `Login=` override. If `KeepPrivate=0` is found, change it to `KeepPrivate=1` and warn the owner BEFORE restarting — restarting while `KeepPrivate=0` drops the live broker session and requires one-time manual GUI login (MT5 encrypts `accounts.dat` per machine and zero broker passwords are stored in scripts/Git).
3. **Zero-Secret Handling:** Never print, log, or pass tokens (`HEROKU_API_KEY`, `NAQEX_INGEST_TOKEN`, `NAQEX_VIEW_TOKEN`, `TELEGRAM_BOT_TOKEN`) via CLI arguments or tracked files. Inject remote node tokens strictly over encrypted SSH stdin into Windows Machine Environment Variables; `SYSTEM` Scheduled Tasks must load Machine env live from Registry (via `C:\Naqex\ops\run_heroku_heartbeat.ps1`) so Task Scheduler never reads stale pre-boot env caches.
4. **Windows 10 IoT LTSC Supply-Chain Guard:** LTSC has no Microsoft Store/`winget`. Install or upgrade runtime tools only from official GitHub/Astral release archives (`uv`, `MinGit`) and binary Python wheels (`uv pip install --only-binary=:all:`). Never run blind `curl | bash` or `irm | iex` pipelines.
5. **Holdout & Scope Isolation:** Never touch sealed `2025+` Holdout (`NATIVE_FTMO_HOLDOUT_LOCK.json`), global `AGENTS.md`, or unrelated submodules (`projects/vi-dubber`, `projects/trader`).

## Operational Workflows

### 1. Health Check (Daily / Post-Reboot / Post-Move)

Run over `ssh naqex-node1` (fallback `ssh naqex-node1-ts`):

- **Clock Drift (`< 2s` vs UTC):** Verify `w32time` is `Running` (`Automatic`) and synced to `time.cloudflare.com` / `time.google.com`. Clock drift breaks red-news UTC windows and triggers false cloud `STALE` alerts.
- **Storage & Pagefile:** Confirm `C:` free space `> 20 GB`, `D:\NaqexBackup\daily\` has today's snapshot, and `Win32_PageFileSetting` lists ONLY `C:\pagefile.sys`.
- **Power & Anti-Auto-Reboot Policy (Win10 IoT LTSC 24/5 Lock):** Confirm `HiberbootEnabled = 0`, Sleep/Hibernate/Disk timeouts = `0` (`powercfg /query SCHEME_CURRENT SUB_DISK DISKIDLE` -> `0x00000000`, never default `0x00000384` = `900s`), `AU` keys (`NoAutoUpdate = 1`, `AUOptions = 2`, `NoAutoRebootWithLoggedOnUsers = 1`, `AlwaysAutoRebootAtScheduledTime = 0`, `AUPowerManagement = 0`), root `WindowsUpdate` policy (`SetActiveHours = 1`, `ConfigureDeadlineNoAutoRebootForQualityUpdates = 1`, `ExcludeWUDriversInQualityUpdate = 1`), and `\Microsoft\Windows\UpdateOrchestrator\Reboot_AC` / `Reboot_Battery` not armed mid-week during active market sessions.
- **Scheduled Tasks (`SYSTEM`):** Check `LastTaskResult == 0` for `Naqex_Heroku_Heartbeat_NODE1` (1m), `Naqex_Daily_Backup_D` (05:30), `Naqex_Crypto_Shadow_5m` (5m), and `Naqex_Crypto_Maker_Probe_5m` (5m); verify `Naqex_MT5_Watchdog_NODE1` (2m) reports `0` when MT5 is live (exit `2` is expected only when MT5 is intentionally closed).
- **Cloud Readiness:** Query `GET /health` (`ok=true`, `persistence="postgres"`, `order_send_count=0`) and `GET /api/status` with header `X-Naqex-View-Token` (`Authorization: Bearer` is strictly for `POST /api/heartbeat` ingest) on `<HEROKU_DEADMAN_APP>`, confirming `NAQEX_NODE1` heartbeat age `< 120s`.

### 2. Fail-Closed `.ex5`, Preset & Red-News Updates

1. Compile all `9/9 .ex5` locally on dev PC into `.runtime/mt5-compiled-ex5/` (`0` `.ex5` binaries inside tracked `tooling/ai-engines/exports/`) and run `verify_deployment_kit.py --build --require-ex5`.
2. Check remote `C:\Naqex\mt5\MQL5\Files\naqex_heartbeat.json` — abort immediately if `open_positions > 0` (also enforced by [sync_updated_ex5_when_flat.ps1](../../../tooling/ai-engines/exports/deployment_kit/vps_kit/sync_updated_ex5_when_flat.ps1)); verify `Config\common.ini` / `connector.ini` preserve `KeepPrivate=1` with zero blank `Login=` override before stopping `terminal64.exe`.
3. Transfer updated `.ex5` / `naqex_red_news_utc.csv` / `.set` profiles over LAN `scp` and verify `9/9` SHA-256 bit-for-bit match against `C:\Naqex\ops\ex5_expected_sha256.json`.
4. Never copy `accounts.dat`, `terminal.lic`, or broker credentials between machines.
5. **Post-Restart Proof:** After restarting MT5 (`Start-ScheduledTask -TaskName 'Naqex_MT5_Portable_AutoStart'`), inspect `MQL5\Logs\YYYYMMDD.log` (not just `Logs\YYYYMMDD.log`) to confirm all `9` charts logged `[PROPGUARD-OK] Loaded ... red-news events`, `[ORCH-INIT]`, and `0` `[PROPGUARD-WARN]` file-lock warnings, and confirm `naqex_heartbeat.json` shows `"terminal_connected": true` with expected `dry_run`.

**Windows SSH & Session Pitfalls (`naqex-node1`):**
- Never call `MetaTrader5.initialize()` from an SSH (Session `0`) process against an interactive Session `1` `terminal64.exe` — cross-session IPC hangs until timeout; inspect `naqex_heartbeat.json`, `Logs\YYYYMMDD.log`, and `MQL5\Logs\YYYYMMDD.log` instead.
- Default OpenSSH shell is `cmd.exe` and long PowerShell `-EncodedCommand` strings hit cmdline limits; for multi-step remote ops, pipe Python to `C:\Naqex\ops\.venv\Scripts\python.exe -` or `scp` a temporary `.ps1` file, run `powershell -NoProfile -ExecutionPolicy Bypass -File ...`, and remove it afterward.

### 3. Windows & Crypto Shadow Maintenance

- **Weekend Maintenance Window:** Apply Windows security patches or reboot `naqex-node1` only during weekend market close (`open_positions == 0`) or a verified flat controlled window if an unscheduled `UpdateOrchestrator\Reboot_AC` is already armed. After reboot, verify BIOS AC power-restore, desktop logon (`Naqex_MT5_Portable_AutoStart`), `sshd`, Tailscale, NTP sync, and all `SYSTEM` tasks automatically resume.
- **Read-Only Crypto Shadow Collectors:** Keep `crypto_shadow_runner.py` and `crypto_maker_shadow_probe.py` running in `--once` 5-minute Scheduled Tasks under `C:\Naqex\crypto-shadow\` (never inside dev IDE background jobs), and pull JSONL logs over LAN `scp` to main PC `.runtime/live-overnight/` whenever running TCA audits.

### 4. Cloud Dead-Man's-Switch & Alert Bot Operations

- **Budget Lock:** Never scale beyond `1 × Basic` + `Postgres Essential-0` (`12 USD/mo <= 13 USD/mo`) without explicit owner approval.
- **Deploy Source Update:** Package `tooling/ai-engines/ops_cloud/heroku_deadman/` via Heroku Sources/Builds API (pass explicit empty header `Content-Type: ""` on S3 presigned PUT to avoid `403`), wait for build `succeeded`, then verify `GET /health` and unauthenticated `GET /` returning `401`.
- **Alert Bot:** Store `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` strictly in cloud Config Vars; verify delivery with one test message after initial setup or token rotation.

## Canonical Scripts & References

- Home-VPS bootstrap & checklist: [setup_win10_home_vps.ps1](../../../tooling/ai-engines/exports/deployment_kit/vps_kit/setup_win10_home_vps.ps1), [WIN10-HOME-VPS-CHECKLIST.md](../../../tooling/ai-engines/exports/deployment_kit/vps_kit/WIN10-HOME-VPS-CHECKLIST.md)
- 24/5 MT5 kit & flat-only sync: [install_vps_24x5.ps1](../../../tooling/ai-engines/exports/deployment_kit/vps_kit/install_vps_24x5.ps1), [sync_updated_ex5_when_flat.ps1](../../../tooling/ai-engines/exports/deployment_kit/vps_kit/sync_updated_ex5_when_flat.ps1), [VPS-24X5-RUNBOOK.md](../../../tooling/ai-engines/exports/deployment_kit/vps_kit/VPS-24X5-RUNBOOK.md)
- Cloud Dead-Man's-Switch & PC sender: [app.py](../../../tooling/ai-engines/ops_cloud/heroku_deadman/app.py), [pc_heartbeat_sender.py](../../../tooling/ai-engines/ops_cloud/heroku_deadman/pc_heartbeat_sender.py)
- Local Quant Factory & `system_doctor.py`: [quant-factory-ops](../quant-factory-ops/SKILL.md)

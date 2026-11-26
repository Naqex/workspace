# Windows 10 IoT LTSC Home-VPS & Cloud Dead-Man's-Switch Runbook

Detailed operational procedures split out of [naqex-node-ops/SKILL.md](../SKILL.md) to keep the hot skill entrypoint lean.

> **2-Layer OPSEC Rule:** Keep all real LAN/Tailscale IPs, SSH users, cloud app names, alert handles, and account logins strictly in local gitignored `private_vault/ops/naqex-node1-topology.md`. Never commit real host identifiers or credentials into Layer 1.

## 1. Topology & Fixed Storage Contract

- **SSH Aliases (main dev PC -> `naqex-node1`):**
  - LAN primary (`< 1ms`, router DHCP pin): `ssh naqex-node1` (`<SSH_USER>@<LAN_IP>`)
  - Tailscale remote fallback: `ssh naqex-node1-ts` (`<SSH_USER>@<TAILSCALE_IP>`)
  - Windows OpenSSH Admin key path on node: `C:\ProgramData\ssh\administrators_authorized_keys` (ASCII/UTF-8 no BOM, `icacls /inheritance:r /grant '*S-1-5-32-544:F' /grant '*S-1-5-18:F'`).
- **3-Drive Allocation on `naqex-node1`:**
  - `C:` (`119 GB` Samsung SSD): Windows 10 IoT Enterprise LTSC, Pagefile locked strictly to `C:\pagefile.sys` (`AutomaticManagedPagefile = False`), `C:\Naqex\{mt5, ops, logs, tools, crypto-shadow}`.
  - `D:` (`465 GB` Seagate HDD): `D:\NaqexBackup\daily\YYYYMMDD\` (30-day rolling log/audit/heartbeat backup at `05:30`).
  - `E:` (`111 GB` secondary SSD with broken SATA latch): `E:\Scratch\` non-critical scratch ONLY. **Never place MT5, live bots, databases, or pagefile on `E:`.**
- **Cloud Monitor & Alerts:**
  - Cloud app `<HEROKU_DEADMAN_APP>`: `1 x Basic` (`7 USD/mo`, 24/7 no sleep) + `heroku-postgresql:essential-0` (`5 USD/mo`, auto-pruned `10,000` rows) = `12 USD/mo <= 13 USD/mo` student credit cap (`2026-10-01 -> 2028-09-30`; review/cancel gate `2028-09-25` before card billing).
  - Local gitignored connection pointer on main PC: `.runtime/ops-cloud/heroku_connection_local.json`.
  - Alert bot: `<TELEGRAM_GUARD_BOT>` (`TELEGRAM_BOT_TOKEN` & `TELEGRAM_CHAT_ID` stored strictly in cloud Config Vars).
- **3-Node Plane Isolation (Star Topology):** `naqex-node1` is strictly the 24/5 Execution Plane (`OrderSend = 0` ops scripts + MT5 Portable) and is completely isolated from `<X13_WORKER>` (Dev-only CPU Research Plane, LAN `ssh naqex-x13` / Tailscale `ssh naqex-x13-ts`, parameters in Layer-2 `private_vault/ops/naqex-x13-worker.md`). Never dispatch backtests/Monte Carlo to `naqex-node1` and never connect `<X13_WORKER>` directly to `naqex-node1` ([THREE-NODE-COMPUTE-ORCHESTRATION-AND-SYNC-BLUEPRINT-20261127.md](../../../../planning/research/THREE-NODE-COMPUTE-ORCHESTRATION-AND-SYNC-BLUEPRINT-20261127.md)).

## 2. Health Check & Pre-Built Single-Command Toolkit (`C:\Naqex\scripts\*.py`)

Prefer the pre-built 1-command JSON scripts on `naqex-node1` via Dev wrapper [node_ctl.py](../../../../tooling/ai-engines/ops_cloud/node_ctl.py) (`status | logs | integrity | maint | audit`, single-handshake LAN -> Tailscale on `rc=255`, `0%` background CPU, `< 0.5s`):

- **Clock Drift (`< 2s` vs UTC; `< 1s` before live quote captures):** Verify `w32time` is `Running` (`Automatic`) and synced to `time.cloudflare.com` / `time.google.com`. Clock drift breaks red-news UTC windows and triggers false cloud `STALE` alerts.
- **Storage & Pagefile:** Confirm `C:` free space `> 20 GB`, `D:\NaqexBackup\daily\` has today's snapshot, and `Win32_PageFileSetting` lists ONLY `C:\pagefile.sys`.
- **Power, Anti-Auto-Reboot & Unattended Power-Restore Policy (Win10 IoT LTSC 24/5 Lock):** Confirm `HiberbootEnabled = 0`, Sleep/Hibernate/Disk timeouts = `0` (`powercfg /query SCHEME_CURRENT SUB_DISK DISKIDLE` -> `0x00000000`, never default `0x00000384` = `900s`), `AU` keys (`NoAutoUpdate = 1`, `AUOptions = 2`, `NoAutoRebootWithLoggedOnUsers = 1`, `AlwaysAutoRebootAtScheduledTime = 0`, `AUPowerManagement = 0`), root `WindowsUpdate` policy (`SetActiveHours = 1`, `ConfigureDeadlineNoAutoRebootForQualityUpdates = 1`, `ExcludeWUDriversInQualityUpdate = 1`), `\Microsoft\Windows\UpdateOrchestrator\Reboot_AC` / `Reboot_Battery` not armed mid-week, and **`AutoAdminLogon = 1`** configured manually via official `C:\Naqex\tools\Sysinternals\Autologon64.exe` (Windows LSA Secret encrypted; never store Windows passwords in scripts, chat, or Git) so an unattended power outage automatically restores the desktop session and MT5.
- **Scheduled Tasks (`SYSTEM`):** Check `LastTaskResult == 0` for `Naqex_Heroku_Heartbeat_NODE1` (1m) and `Naqex_Daily_Backup_D` (05:30); verify `Naqex_MT5_Watchdog_NODE1` (2m) reports `0` when MT5 is live (exit `2` is expected only when MT5 is intentionally closed). Note: Crypto Shadow/Maker tasks are intentionally disabled under Round-3 own-book pause (`< 10k USD`).
- **Cloud Readiness:** Query `GET /health` (`ok=true`, `persistence="postgres"`, `order_send_count=0`) and `GET /api/status` with header `X-Naqex-View-Token` (`Authorization: Bearer` is strictly for `POST /api/heartbeat` ingest) on `<HEROKU_DEADMAN_APP>`, confirming `NAQEX_NODE1` heartbeat age `< 120s`.

## 3. Fail-Closed `.ex5`, Preset & Red-News Updates

1. Compile binaries locally on dev PC into `.runtime/mt5-compiled-ex5/` (`0` `.ex5` binaries inside tracked `tooling/ai-engines/exports/`) and run `verify_deployment_kit.py --build --require-ex5`.
2. Check remote `C:\Naqex\mt5\MQL5\Files\naqex_heartbeat.json` — abort immediately if `open_positions > 0` or `terminal_connected != true` (also enforced by [sync_updated_ex5_when_flat.ps1](../../../../tooling/ai-engines/exports/deployment_kit/vps_kit/sync_updated_ex5_when_flat.ps1)).
3. Verify `C:\Naqex\mt5\Config\common.ini` and `connector.ini` preserve `KeepPrivate=1` with NO blank-password `Login=` override before stopping `terminal64.exe` (restarting while `KeepPrivate=0` drops the live broker session and requires manual GUI re-login).
4. Transfer updated `.ex5` / `naqex_red_news_utc.csv` (`492` events) / `.set` profiles over LAN `scp` and verify bit-for-bit SHA-256 match against `C:\Naqex\ops\ex5_expected_sha256.json`. Never copy `accounts.dat`, `terminal.lic`, or broker credentials between machines.
5. **Post-Restart Proof:** After restarting MT5 (`Start-ScheduledTask -TaskName 'Naqex_MT5_Portable_AutoStart'`), inspect `MQL5\Logs\YYYYMMDD.log` (not just `Logs\YYYYMMDD.log`) to confirm `[PROPGUARD-OK] Loaded ... red-news events`, `[ORCH-INIT]` / Master init, and `0` `[PROPGUARD-WARN]` file-lock warnings, and confirm `naqex_heartbeat.json` reports `"terminal_connected": true` with expected `dry_run`.

## 4. Windows SSH Pitfalls, Weekend Maintenance & Cloud Deploys

- **Windows SSH Session 0 Pitfall:** Never call `MetaTrader5.initialize()` from an SSH (Session `0`) process against an interactive Session `1` `terminal64.exe` — cross-session IPC hangs until timeout; inspect `naqex_heartbeat.json`, `Logs\YYYYMMDD.log`, and `MQL5\Logs\YYYYMMDD.log` instead.
- **Shell Hygiene:** Default OpenSSH shell is `cmd.exe` and PowerShell 5.1 emits `CLIXML` noise while long `-EncodedCommand` strings hit cmdline limits; prefer `node_ctl.py` (or `C:\Naqex\tools\pwsh\pwsh.exe` 7 for ad-hoc queries), and for multi-step scripts `scp` a temp file, execute it, and delete it afterward.
- **Weekend Maintenance Window:** Apply Windows security patches or reboot `naqex-node1` only during weekend market close (`open_positions == 0`) or a verified flat controlled window. After reboot, verify BIOS AC power-restore, desktop logon (`Naqex_MT5_Portable_AutoStart`), `sshd`, Tailscale, NTP sync, and all `SYSTEM` tasks automatically resume.
- **Cloud Dead-Man's-Switch Deploy:** Never scale beyond `1 x Basic` + `Postgres Essential-0` (`12 USD/mo <= 13 USD/mo`) without explicit owner approval. Package `tooling/ai-engines/ops_cloud/heroku_deadman/` via Heroku Sources/Builds API (pass explicit empty header `Content-Type: ""` on S3 presigned PUT to avoid `403`), wait for build `succeeded`, then verify `GET /health` and unauthenticated `GET /` returning `401`.
- **Zero-Secret Rule:** Inject remote node tokens strictly over encrypted SSH stdin into Windows Machine Environment Variables (`SYSTEM` Scheduled Tasks load Machine env live via `C:\Naqex\ops\run_heroku_heartbeat.ps1`). Never pass tokens via CLI arguments or tracked files.

## 5. Canonical Scripts & Kit Docs

- Home-VPS bootstrap & checklist: [setup_win10_home_vps.ps1](../../../../tooling/ai-engines/exports/deployment_kit/vps_kit/setup_win10_home_vps.ps1), [WIN10-HOME-VPS-CHECKLIST.md](../../../../tooling/ai-engines/exports/deployment_kit/vps_kit/WIN10-HOME-VPS-CHECKLIST.md)
- 24/5 MT5 kit & flat-only sync: [install_vps_24x5.ps1](../../../../tooling/ai-engines/exports/deployment_kit/vps_kit/install_vps_24x5.ps1), [sync_updated_ex5_when_flat.ps1](../../../../tooling/ai-engines/exports/deployment_kit/vps_kit/sync_updated_ex5_when_flat.ps1), [VPS-24X5-RUNBOOK.md](../../../../tooling/ai-engines/exports/deployment_kit/vps_kit/VPS-24X5-RUNBOOK.md)
- Cloud Dead-Man's-Switch & PC sender: [app.py](../../../../tooling/ai-engines/ops_cloud/heroku_deadman/app.py), [pc_heartbeat_sender.py](../../../../tooling/ai-engines/ops_cloud/heroku_deadman/pc_heartbeat_sender.py)

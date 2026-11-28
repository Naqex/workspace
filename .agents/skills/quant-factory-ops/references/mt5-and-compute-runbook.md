# MT5 Real-Tick, Long-Horizon Sizing & 3-Node Compute Runbook

Detailed operational procedures split out of [quant-factory-ops/SKILL.md](../SKILL.md) to keep the hot skill entrypoint lean.

## 1. Throughput-Calibrated Long-Horizon / Overnight Factory Sizing

When the owner authorizes a long autonomous window (e.g., `6-12h` overnight) with multi-lane `swarm` execution, NEVER size the plan as a small static `20-30` milestone list (measured 4-lane throughput is `~25-35` milestones/hour -> a static list finishes in `< 2h`):

1. **Calibrate to measured velocity:** Budget `~20-30` concrete work units per active parallel hour, split into **Core Production Waves + Continuous Fresh-Data R&D Cycles + Scheduled Live-Execution Feedback Loops** (`schedule` checkpoints every `2h` to inspect live demo/shadow TCA logs, fix runtime issues, and launch the next orthogonal wave).
2. **Expand ONLY across genuinely new value axes (Anti-Overfit & Anti-Busywork):** Never re-mine an already-exhausted dataset or invent cosmetic refactors to fill hours. Extra overnight cycles MUST use:
   - **Fresh datasets / asset classes / timeframes** (new commodities/indices/FX pairs, `15m/1H` crypto, multi-day swing with live-measured broker swaps, macro ETFs, CME futures), each with its own strict `m_total` budget cap through `research_council.py`;
   - **Real-world execution compute** (MT5 Real-Tick Strategy Tester latency/spread sweeps, live demo/shadow microstructure capture & TCA reconciliation);
   - **Measured system/portfolio optimization** (pytest/Numba speedups, NCO/Ledoit-Wolf/Meta-Labeling, interactive ops cockpit, multi-prop & own-book execution kits).
3. **Clean halt still applies when ALL high-value cycles & scheduled live-capture checkpoints finish:** Never degrade passing tests or fabricate fake work after the final scheduled checkpoint.

## 2. Event-Driven Time Compression & Parallel Execution Discipline

Minimize wall-clock waste without weakening hard safety or statistical boundaries (`Holdout 2025+ SEALED`, `OrderSend = 0` default, zero mid-run parameter edits on live v1 EAs):

1. **Event/Sample Gates over Arbitrary Calendar Waits:** Prefer minimum-sufficient event criteria (e.g., `>= 10-15` clean closed fills spanning Asia/London/NY sessions, rollover, and red-news with `0` technical defects) over rigid calendar padding (`14d / 30d / months`). When a bounded-loss micro-canary (e.g., a small ticket after written firm clearance) produces higher-fidelity real-world evidence faster than prolonged demo waiting, present **both** the fast-path and conservative-path trade-off explicitly.
2. **Parallelize Independent Lanes instead of Serializing:** Never pause an active owner behind a passive telemetry wait. Keep dependent capital-scaling gates fail-closed while immediately executing technically independent lanes in parallel (Dev v2 R&D, VPS/Control Room ops, independent Own-Book sleeves, product apps).
3. **Local-First Fast Falsification:** Default to local SSD caches (`.runtime/hot-m1-cache`, `.npz` derived tapes, Numba JIT) with zero dependency on external drives, run compute jobs asynchronously alongside disjoint code/ops edits, and run cheap kill-tests (`robustness_gate`, Walk-Forward vs Fixed baseline) first to kill weak ideas in seconds instead of days.

## 3. MT5 Dev Portable & Multi-Symbol Real-Tick Discipline

1. **Single Canonical English Dev MT5:** Keep ONLY `.runtime/ftmo-demo-portable-<DEMO_ID>` (English) on the dev PC and prune stale `.runtime` MT5 clones after use — never switch Dev MT5/MetaEditor to Vietnamese (breaks HTML report & compile-log regex parsers; Vietnamese on `naqex-node1` live terminal is safe).
2. **Headless Strategy Tester Auth & Isolation:** Every `tester.ini` MUST enforce `KeepPrivate=1` and `[Experts] Enabled=0 / AllowLiveTrading=0 / AllowDllImport=0` (prevents wiping `accounts.dat` and prevents live chart orders). `MetaTrader5.initialize()` alone does not persist credentials for `/config:tester.ini` — pass transient `[Common]` Demo credentials only from gitignored local `.env` deleted in `finally:` (never log/commit). Never launch two `terminal64.exe` processes concurrently on the same host, verify `Config/servers.dat` before connecting to a new firm, and stop heavy multi-symbol Tester runs immediately when the owner reports high CPU load.
3. **Multi-Asset MQL5 Invariants:** Never apply a single FX spread cap (`35 pts`) to indices (`US100.cash ~195 pts`) — use per-asset-class caps (`MaxSpreadCapForSymbol`). Always declare `#property tester_file "naqex_red_news_utc.csv"` so Tester sandboxes receive the red-news CSV. Cache immutable closed-bar (`shift=1`) D1 ATR/range filters once per D1 bar, add a `>= 60s` holiday-retry cooldown on M1 window reconstructions, and use `EventSetTimer(MQLInfoInteger(MQL_TESTER) ? 60 : 1)` + 1s Tester `OnTick` throttle so `Model=4` avoids tens of millions of redundant callbacks.
4. **Live-Money Parity, Slippage Deviation & CI Guardrails:**
   - Always assert MQL5-vs-Python parity on drawdown brakes (`AMBER`/`RED` must scale relatively `base * mult` + intraday headroom taper rather than absolute clamping on P1 multipliers) and pass real per-engine `magic` + `tk`/`pos` into `LogExecAuditFor()` so TCA reconciliation and overnight-hold checks stay accurate.
   - Calibrate `CTrade::SetDeviationInPoints()` per asset class from real live-probe tail slippage (e.g., `35` pts FX vs `>= 450` pts `US100.cash`, never rely on MT5's `10`-pt default).
   - Holdout/research scripts must NEVER overwrite production `exports/Files/naqex_red_news_utc.csv` and must enforce programmatic `HoldoutLockError` (`max_date < "2025-01-01"`) inside `data_store`/`prop_engine`/`mt5_realtick_runner`.
   - Keep pure-offline function-based `pytest` suites + `test_layer1_opsec_guard.py` explicitly wired into `.github/workflows/workspace.yml`.
5. **MT5 Tester Blind Spots, Profile Binding & Event-Ordered Parity:**
   - **Never treat `MQL_TESTER` green runs as restart or rejection-log proof:** `HydrateTradedDaysFromHistory()` (R1), `RestoreOrInitDayAnchorM()`/`PersistAutoKillStateM()` (R2), and `LogMasterShadowRow()` early-return under `MQL_TESTER`, while `OnTick()` skips sub-second ticks after the first tick per second. Mark Tester-skipped restart branches `SKIPPED_IN_TESTER` (never `PASS` from `hydrated=true`), verify with fixed offline fixtures (explicitly labeling Python-replica checks as *Python logic verified; MQL branch unexecuted*), log rejected signals explicitly on contention fixtures, and record raw tick-stream vs EA-observed timestamps for sub-second spikes.
   - **Prove profile switches in receipts:** Functions like `margin_per_lot_usd()` may match strict strings (`profile_mode == "Standard"`), silently falling back to `"Swing"` on contract IDs. Always emit `contract_id`, resolved `profile_mode`, and 1-lot margin for the same signal before/after switching, and save a profile-only ablation before bundling sizing (`balance * 0.95`, `volStep`, `85%` margin) or intraday-brake fixes.
   - **Event-ordered parity & tick-intersection honesty:** Verify `signal -> accept/reject -> lot -> intraday regime change -> exit/kill -> equity -> phase transition` (including mid-day floating-DD brake and simultaneous margin contention). Use the verified `.tkc` real-tick intersection across ALL required symbols (`<= 2024-12-31`), list missing/synthetic months verbatim, and note MetaQuotes simulated delay applies to EA requests rather than server-side SL triggers.
6. **Live Multi-EA & VPS Runtime Invariants:** All concurrent `FileOpen` calls (`LoadRedNewsCsv`, `LogExecAuditFor`) must pass `FILE_SHARE_READ | FILE_SHARE_WRITE` with bounded retry; `Naqex_AccountOrchestrator` must gate DD/kill-switch on `IsAccountSynced(bal, eq)` (`TERMINAL_CONNECTED != 0 && bal > 0 && eq > 0`) so disconnected startup never latches sticky kill-switch; VPS PowerShell scripts must use bounded `Get-AncestorPath` instead of deep repo-relative `Split-Path -Parent` chains.

## 4. 3-Node Compute Routing, Star Sync & NTP Discipline

Follow the owner-locked 3-node architecture ([THREE-NODE-COMPUTE-ORCHESTRATION-AND-SYNC-BLUEPRINT-20261127.md](../../../../planning/research/THREE-NODE-COMPUTE-ORCHESTRATION-AND-SYNC-BLUEPRINT-20261127.md); real LAN/Tailscale IPs live strictly in Layer-2 `private_vault/ops/`):

1. **Star Topology Centered on `<DEV_PC>` (Zero Bidirectional Sync):**
   - `<DEV_PC>` is the ONLY Git commit/authoring host and the ONLY machine allowed to hold `Holdout 2025+`. Never run OneDrive/Syncthing/Google Drive sync over `.git`, `.runtime`, or `private_vault`.
   - `<X13_WORKER>` receives immutable Dev-only (`<= 2024`) cache + Git-SHA job bundles via [compute_router.py](../../../../tooling/ai-engines/ops_cloud/compute_router.py) and writes immutable `results/<job_id>/` + trailing `manifest.sha256.json` pulled back by `<DEV_PC>`.
   - `naqex-node1` remains strictly isolated as the 24/5 MT5 Execution Plane — never run backtests/Monte Carlo there and never connect `<X13_WORKER>` directly to `naqex-node1`.
2. **Auto-Detect & Dynamic Dispatch (`<= 60m` Offline Dev Jobs — No Owner Prompt Needed):**
   - **PC Dev Activity Sensing (local OS metrics only):** In `Mode A` (owner active/gaming/GPU `> 25%`), cap local background work to **`2-3` CPU cores**, `BELOW_NORMAL` priority, and **`0%` GPU**, offloading `>= 10m` Dev CPU batches to `<X13_WORKER>`. In `Mode B` (idle `>= 15m` or `00:00-07:00 ICT`), open up to **`5/6` cores** (`NORMAL`) with `30s` live preemption and split shardable `>= 15m` batches **`60% <DEV_PC> / 40% <X13_WORKER>`** (`10` micro-shards).
   - **X13 `1.5s` AC-Only Pre-Flight & Silent Fallback:** Probe `ssh naqex-x13` (fallback `naqex-x13-ts`) requiring `ACLineStatus == 1` & `BatteryStatus != 1` (never burn battery; save & stop if unplugged `> 60s`), `free RAM >= 4 GB`, `C: >= 15 GB`, `|NTP| < 1000 ms`, `venv_ok == True`, and `forbidden_files == 0`. If offline/on battery/busy, silently fall back to `<DEV_PC>` under the active mode cap and log `fallback_reason`.
3. **3-Tier Autonomy & NTP Gate:**
   - **Auto-run without asking:** Offline Dev research/tests/Numba/Monte Carlo `<= 60m` (`0 VND`, `OrderSend = 0`).
   - **Ask owner first:** Any mutation/restart on `naqex-node1`, Windows Admin actions (`w32tm /resync`), heavy GPU jobs during gaming, batches `> 60m`, any Holdout protocol, or any monetary spend.
   - **NTP `< 1,000 ms` Pre-Capture Gate:** Always verify `|NTP| < 1000 ms` on the capturing node before live `QUOTE_ONLY` windows (e.g., NFP/CPI).

## 5. Safe Local Capability Upgrades (Supply-Chain Guard)

Only install a local Python speedup/testing package when a profiled bottleneck warrants it:

1. Verify official package name, license (ban AGPL-3.0 / GPLv3 / Commons-Clause in core packages — enforced by `ARCH-07`), and binary wheel availability (never run `curl | bash` or untrusted install scripts).
2. Install strictly into the project quant venv with binary wheels only:
   `uv pip install --python .runtime/quant-audit-v24/Scripts/python.exe --only-binary=:all: <package>`
3. Smoke-test parity + measured speedup immediately and run `system_doctor.py --mode full`.
4. Ask the owner first before any paid tool, OAuth/secret, global config change, or persistent daemon.

## 6. Local Services Map, Data Priority, Zero-Popup Windows & CI Hygiene

1. **Inspect Existing Workspace Services & Data Tools Before Advising External Alternatives:**
   - **Trader `CLIProxyAPI` vs External Windows Instance ([LOCAL-SERVICES.md](../../../../projects/trader/foundation_v2/docs/LOCAL-SERVICES.md)):** Workspace-owned Trader `CLIProxyAPI` runs on loopback **`127.0.0.1:17852`** (resolve runtime `home`/`configPath`/`executable` dynamically via `.runtime/paperclip/gateway-owner.json` instead of hardcoding a static path; block external third-party routes via a sanitized temp config without mutating `managed.yaml`; `OPERATIONS.md` policy `request-retry: 0`, degrade cleanly to `NEUTRAL / SKIP_OFFLINE` on `429` or offline). Treat OAuth-backed `CLIProxyAPI` (`17852`) strictly as **`DEV_RESEARCH_ONLY`** (OAuth providers can return `403`/`503` quota errors); production/VPS macro advisory MUST use an **Official API `<= 5 USD/mo`** (e.g., top Radar model `qwen/qwen3.7-flash`) with local Ollama degraded fallback. Windows port **`8317`** is an external host instance — NEVER modify its config, auth, keys, or lifecycle.
   - **Data Source Priority When Dukascopy HTTP Hits AWS WAF (`403`/`202`):** NEVER bypass WAF or CAPTCHA. Inspect existing **`QDM CLI 125.2692`** ([quantdatamanager.md](../../../../projects/trader/docs/quantdatamanager.md), `TW_V2_QDM_HOME`, export cache `<= 2024-12-31`) and local **`FTMO-Demo` portable M1** (`<= 2024-12-31`, `holdout_rows = 0`) BEFORE adding any new downloader.
2. **Zero-Popup Windows Background Automation:**
   - All Windows Scheduled Tasks running background Python scripts MUST execute **`.runtime\quant-audit-v24\Scripts\pythonw.exe`** with `Hidden = $true` (never console `python.exe`).
   - EVERY `subprocess.run` / `subprocess.Popen` call inside scheduled or router modules (`watchdog_15m.py`, `morning_briefing.py`, `compute_router.py` — including `ssh`, `scp`, `git`, `w32tm`, `nvidia-smi`) MUST pass `creationflags = int(getattr(subprocess, "CREATE_NO_WINDOW", 0)) if os.name == "nt" else 0`; otherwise Windows spawns a visible black `cmd`/`conhost` window for every child console command launched from windowless `pythonw.exe`. Enforce coverage via an **AST scan** across `tooling/automation/`, `tooling/ai-engines/ops_cloud/`, and `tooling/ai-engines/quant_factory/wave4/` (`0` calls missing `creationflags`), not manual grep alone.
3. **MT5 Same-Feed vs Cross-Feed Parity & Live `OnnxRun()` Verification:**
   - Separate **cross-feed broker drift** (`FTMO 00:00 EET` D1 vs `Dukascopy 00:00 UTC` D1 + production CSV lacking 2018–2024 non-USD events + 1s post-news re-entry) from EA logic bugs: certify `>= 98%` formula parity on **same-feed FTMO M1 + identical calendar** before Demo Burn-In, and note `MQL_TESTER` skips `LogExecAuditFor`/`LogMasterShadowRowV103` unless explicitly enabled via a tester flag.
   - When exporting ML models to MT5 ONNX (`OnnxRun`), force pure `float32` tensors (`zipmap = False`) and verify numerical parity **`Python == onnxruntime == MT5 Strategy Tester OnnxRun() <= 1e-5`** (retain a pure-MQL5 `.mqh` fallback if the MT5 ONNX runtime rejects an operator). Beyond precomputed vector parity, require an **end-to-end feature-extraction parity test** between Python training features and live MQL5 `BuildCausalMLFeatures*()` (same `ATR` smoothing and day boundary) plus `MarkEngineTraded()` on ML rejections before Holdout/live promotion.
4. **CI `@pytest.mark.local_cache` Marker, Portability & Clean Multi-Repo Git Hygiene:**
   - Mark any pytest reading gitignored `private_vault/` or `.runtime/` caches with `@pytest.mark.local_cache` while keeping pure synthetic offline assertions active in GitHub Actions CI.
   - Normalize `\r\n -> \n` before hashing tracked text files in cross-platform CI assertions, lazy-import optional cross-submodule helpers so CI stays green on pinned submodules, and pass `write_output_path=None` / `tmp_path` in tests so production `.runtime/` SSOT SHA-256 hashes never mutate during pytest.
   - Never run `git add -A` in the superproject: stage explicit paths only, assert `0` unintended `:160000` gitlinks, `0` `.ex5` in `private_vault/` or tracked `exports/`, and preserve untouched owner WIP in `projects/vi-dubber`.

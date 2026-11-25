---
name: quant-factory-ops
description: Audit, accelerate, prune bloat, verify regression, and maintain the Naqex 4-layer Quant Factory (JSON configs, NPZ cache, Numba JIT, MQL5 PropGuard, MT5 real-tick tester, system_doctor). Use for quant infra health, speedups, or maintenance; not lessons, UI, strategy picks, or Holdout.
---

# Quant Factory Operations & Autonomous Maintenance

Keep the Naqex quant research factory fast, modular, zero-hardcoding, bloat-free, and regression-safe across long-term passes without breaking locked evidence or safety boundaries.

## Hard boundaries (fail-closed)

- **Holdout lock (`>= 2025-01-01`):** Never unlock, read, or mutate `NATIVE_FTMO_HOLDOUT_LOCK.json` (`holdout_rows = 0` until explicit owner unlock protocol).
- **Zero live execution:** Never disable `InpDryRunLogOnly = true` / `InpGuardDryRunLogOnly = true` or run `OrderSend` (`OrderSend = 0`).
- **Scope & global config:** Never modify global `AGENTS.md`, global hooks/MCP config, or unrelated submodules (e.g., `projects/vi-dubber`, `projects/trader`).
- **Caller-verified pruning:** Never delete or compact a tracked file, JSON receipt, or helper without checking callers with `rg` first and preserving byte-exact archives on `E:\BACKUP-TRADINGWORKSPACE\ai-engine-jobs\` whenever historical receipts are compacted.

## 4-Layer Flexible Architecture (zero hardcoding)

All new studies (`Pass 29+`) reuse these 4 layers instead of duplicating loops in monolithic `passN_*.py` files:

1. **Declarative JSON configs** (`tooling/ai-engines/configs/`):
   - `firms/*.json`: prop/broker rules (FTMO Swing/Standard, The5ers High Stakes/Hyper Growth, Exness). Add a new firm by adding 1 JSON file.
   - `profiles/*.json`: phase multipliers, AMBER/RED DD brakes, causal weighting (`cluster_a_invdd`), volatility targeting (`window=20`), per-symbol concurrent risk cap.
   - `calendars/*.json`: official UTC red-news schedules (`red_news_official_2018_2024.json`).
   - Single machine-readable strategy ledger: [PORTFOLIO-REGISTRY.json](../../../planning/research/PORTFOLIO-REGISTRY.json).
2. **Data & Derived Cache** ([data_store.py](../../../tooling/ai-engines/quant_factory/data_store.py)):
   - Sealed M1 Bid/Ask Parquet cache stays on D: SSD (`.runtime/hot-m1-cache/`).
   - Precomputed minute-by-minute frozen engine tapes persist as zero-pickle `.npz` + SHA-verified `.json` in `.runtime/hot-m1-cache/_derived/` (`< 0.35s` warm load).
3. **Numba-JIT Statistical & Prop Engine** ([eval_pipeline.py](../../../tooling/ai-engines/quant_factory/eval_pipeline.py), [prop_engine.py](../../../tooling/ai-engines/quant_factory/prop_engine.py)):
   - `@njit(cache=True)` sign-flip permutation, BH-FDR, Bailey–Lopez de Prado DSR/PSR, worst-5% tail correlation, 6-core `ProcessPoolExecutor` sweeps.
   - Config-driven exact M1 Prague-reset `replay_portfolio_m1` (with `max_symbol_concurrent_risk` cap + `±5m` red-news flatten) and `@njit(cache=True)` lifecycle simulator (`< 50 ms` per 2,000 paths).
4. **Verified Reporting & MQL5 Guard** ([report_gen.py](../../../tooling/ai-engines/quant_factory/report_gen.py), [Naqex_PropGuard.mqh](../../../tooling/ai-engines/exports/Include/Naqex_PropGuard.mqh)):
   - Auto-generated Markdown tables and immutable `.json` + `.sha256` receipts.
   - Shared MQL5 production guard (auto `ORDER_FILLING_*`, `SYMBOL_TRADE_TICK_VALUE_LOSS`, per-symbol concurrent risk cap, Strategy-Tester UTC offset, `SymbolInfoSessionTrade` holiday early-close flatten, `GlobalVariable` VPS-restart persistence, CSV red-news guard).
   - Live multi-EA & VPS runtime invariants: all concurrent `FileOpen` calls (`LoadRedNewsCsv`, `LogExecAuditFor`) must pass `FILE_SHARE_READ | FILE_SHARE_WRITE` with bounded retry; `Naqex_AccountOrchestrator` must gate DD/kill-switch on `IsAccountSynced(bal, eq)` (`TERMINAL_CONNECTED != 0 && bal > 0 && eq > 0`) so disconnected startup never latches sticky kill-switch; VPS PowerShell scripts must use bounded `Get-AncestorPath` instead of deep repo-relative `Split-Path -Parent` chains.

## Autonomous Maintenance Runbook

### 1. Health & Regression Gate (`system_doctor.py`)

Run fast mode during active edits (`< 10s`), and full mode before every commit/milestone (`~25s` via 6-core `pytest -n 6`):

```powershell
$py = 'D:\ANNAM\TradingWorkspace\.runtime\quant-audit-v24\Scripts\python.exe'
& $py -X utf8 tooling/ai-engines/system_doctor.py --mode fast
& $py -X utf8 tooling/ai-engines/system_doctor.py --mode full
```

### 2. Anti-Bloat & Index Hygiene

Trigger compaction proactively before hitting Git/anti-bloat limits:
- `planning/research/README.md > 150` lines → archive older passes verbatim into `planning/research/ARCHIVE-INDEX-YYYYMM.md` keeping 100% of links intact.
- `planning/CURRENT-CONTEXT.md > 12 KB` → keep only active context, locked invariants, and exact links to owner ledgers.
- Any branch-touched file in `planning/research/ > 900 KB` → copy byte-exact raw artifact + SHA-256 to `E:\BACKUP-TRADINGWORKSPACE\ai-engine-jobs\archive-raw-json-YYYYMMDD\`, write compact structured summary + archive pointer in repo, update verified callers (`rg`), and re-run `system_doctor.py --mode full`.

### 3. Safe Local Capability Upgrades (Supply-Chain Guard)

Only install a local Python speedup/testing package when a profiled bottleneck warrants it:
1. Verify official package name, license, and binary wheel availability (never run `curl | bash` or untrusted install scripts).
2. Install strictly into the project quant venv with binary wheels only:
   `uv pip install --python .runtime/quant-audit-v24/Scripts/python.exe --only-binary=:all: <package>`
3. Smoke-test parity + measured speedup immediately and run `system_doctor.py --mode full`.
4. Ask the owner first before any paid tool, OAuth/secret, global config change, or persistent daemon.

### 4. Throughput-Calibrated Long-Horizon / Overnight Factory Sizing

When the owner authorizes a long autonomous window (e.g., `6–12h` overnight) with multi-lane `swarm` execution, NEVER size the plan as a small static `20–30` milestone list (measured 4-lane XHigh throughput is `~25–35` milestones/hour -> a static list finishes in `< 2h`):

1. **Calibrate to measured velocity:** Budget `~20–30` concrete work units per active parallel hour, split into **Core Production Waves + Continuous Fresh-Data R&D Cycles + Scheduled Live-Execution Feedback Loops** (`schedule` checkpoints every `2h` to inspect live demo/shadow TCA logs, fix runtime issues, and launch the next orthogonal wave).
2. **Expand ONLY across genuinely new value axes (Anti-Overfit & Anti-Busywork):** Never re-mine an already-exhausted dataset or invent cosmetic refactors to fill hours. Extra overnight cycles MUST use:
   - **Fresh datasets / asset classes / timeframes** (e.g., new commodities/indices/FX pairs, `15m/1H` crypto, multi-day swing with live-measured broker swaps, macro ETFs, CME futures), each with its own strict `m_total` budget cap through `research_council.py`;
   - **Real-world execution compute** (MT5 Real-Tick Strategy Tester latency/spread sweeps, live demo/shadow microstructure capture & TCA reconciliation);
   - **Measured system/portfolio optimization** (pytest/Numba speedups, NCO/Ledoit-Wolf/Meta-Labeling, interactive ops cockpit, multi-prop & own-book execution kits).
3. **Clean halt still applies when ALL high-value cycles & scheduled live-capture checkpoints finish:** Never degrade passing tests or fabricate fake work after the final scheduled checkpoint.

### 5. Event-Driven Time Compression & Parallel Execution Discipline

Minimize wall-clock waste without weakening hard safety or statistical boundaries (`Holdout 2025+ SEALED`, `OrderSend = 0` default, zero mid-run parameter edits on live v1 EAs):

1. **Event/Sample Gates over Arbitrary Calendar Waits:** Prefer minimum-sufficient event criteria (e.g., `>= 10–15` clean closed fills spanning Asia/London/NY sessions, rollover, and red-news with `0` technical defects) over rigid calendar padding (`14d / 30d / months`). When a bounded-loss micro-canary (e.g., a small `39 USD` ticket after written firm clearance) produces higher-fidelity real-world evidence faster than prolonged demo waiting, present **both** the fast-path and conservative-path trade-off explicitly.
2. **Parallelize Independent Lanes instead of Serializing:** Never pause an active owner behind a passive telemetry wait. Keep dependent capital-scaling gates fail-closed while immediately executing technically independent lanes in parallel (Dev v2 R&D, VPS/Control Room ops, independent Own-Book sleeves, product apps).
3. **Local-First Fast Falsification:** Default to local SSD caches (`.runtime/hot-m1-cache`, `.npz` derived tapes, Numba JIT) with zero dependency on external drives, run compute jobs asynchronously alongside disjoint code/ops edits, and run cheap kill-tests (`robustness_gate`, Walk-Forward vs Fixed baseline) first to kill weak ideas in seconds instead of days.

### 6. MT5 Dev Portable & Multi-Symbol Real-Tick Discipline

1. **Single Canonical English Dev MT5:** Keep ONLY `.runtime/ftmo-demo-portable-1515343166` (English) on the dev PC and prune stale `.runtime` MT5 clones after use — never switch Dev MT5/MetaEditor to Vietnamese (breaks HTML report & compile-log regex parsers; Vietnamese on `naqex-node1` live terminal is safe).
2. **Headless Strategy Tester Auth & Isolation:** Every `tester.ini` MUST enforce `KeepPrivate=1` and `[Experts] Enabled=0 / AllowLiveTrading=0 / AllowDllImport=0` (prevents wiping `accounts.dat` and prevents live chart orders). Note `MetaTrader5.initialize()` alone does not persist credentials for `/config:tester.ini` — pass transient `[Common]` Demo credentials only from gitignored local `.env` deleted in `finally:` (never log/commit). Never launch two `terminal64.exe` processes concurrently on the same host, verify `Config/servers.dat` before connecting to a new firm, and stop heavy multi-symbol Tester runs immediately when the owner reports high CPU load.
3. **Multi-Asset MQL5 Invariants:** Never apply a single FX spread cap (`35 pts`) to indices (`US100.cash ~195 pts`) — use per-asset-class caps (`MaxSpreadCapForSymbol`). Always declare `#property tester_file "naqex_red_news_utc.csv"` so Tester sandboxes receive the red-news CSV. Cache immutable closed-bar (`shift=1`) D1 ATR/range filters once per D1 bar, add a `>= 60s` holiday-retry cooldown on M1 window reconstructions, and use `EventSetTimer(MQLInfoInteger(MQL_TESTER) ? 60 : 1)` + 1s Tester `OnTick` throttle so `Model=4` avoids tens of millions of redundant callbacks.

## Negative triggers

- Do not use for strategy hypothesis design (use [strategy-research](../strategy-research/SKILL.md)), white-box discovery (use [whitebox-prop-discovery](../whitebox-prop-discovery/SKILL.md)), or strategy qualification verdicts (use [strategy-qualification](../strategy-qualification/SKILL.md)).
- Do not use for trading tutoring, UI platform changes, or unlocking Holdout/live broker execution.

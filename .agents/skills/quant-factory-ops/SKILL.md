---
name: quant-factory-ops
description: Autonomously audit, accelerate, prune bloat, verify regression, and maintain the Naqex 4-layer Quant Factory (declarative JSON configs, zero-pickle NPZ derived cache, Numba JIT evaluation, MQL5 PropGuard, and system_doctor health checks). Use for quant infrastructure health checks, performance upgrades, anti-bloat archiving, or safe local package/workflow maintenance; do not use for trading education, UI design, strategy selection, or opening the sealed 2025+ Holdout.
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

## Negative triggers

- Do not use for strategy hypothesis design (use [strategy-research](../strategy-research/SKILL.md)), white-box discovery (use [whitebox-prop-discovery](../whitebox-prop-discovery/SKILL.md)), or strategy qualification verdicts (use [strategy-qualification](../strategy-qualification/SKILL.md)).
- Do not use for trading tutoring, UI platform changes, or unlocking Holdout/live broker execution.

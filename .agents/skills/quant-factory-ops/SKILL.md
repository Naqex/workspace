---
name: quant-factory-ops
description: Audit, accelerate, prune bloat, verify regression, and maintain the Naqex 4-layer Quant Factory (JSON configs, NPZ cache, Numba JIT, MQL5 PropGuard, MT5 real-tick tester, system_doctor). Use for quant infra health, speedups, or maintenance; not lessons, UI, strategy picks, or Holdout.
---

# Quant Factory Operations & Autonomous Maintenance

Keep the Naqex quant research factory fast, modular, zero-hardcoding, bloat-free, and regression-safe across long-term passes without breaking locked evidence or safety boundaries.

## Hard Boundaries (Fail-Closed)

- **Holdout lock (`>= 2025-01-01`):** Never unlock, read, or mutate `NATIVE_FTMO_HOLDOUT_LOCK.json` (`holdout_rows = 0` until explicit owner unlock protocol). Enforce programmatic `HoldoutLockError` (never Python `assert`, stripped by `python -O`).
- **Zero live execution:** Never disable `InpDryRunLogOnly = true` / `InpGuardDryRunLogOnly = true` or run `OrderSend` (`OrderSend = 0`).
- **Scope & global config:** Never modify global `AGENTS.md`, global hooks/MCP config, or unrelated submodules (`projects/vi-dubber`, `projects/trader`).
- **Caller-verified pruning:** Never delete or compact a tracked file, JSON receipt, or helper without checking callers with `rg` first and preserving byte-exact archives on cold backup whenever raw artifacts are compacted.

## 4-Layer Flexible Architecture (Zero Hardcoding)

All new studies reuse these 4 layers instead of duplicating loops in monolithic scripts:

1. **Declarative JSON & SSOT Configs** (`tooling/ai-engines/configs/ssot/`, `configs/firms/`, `configs/profiles/`, `configs/calendars/`):
   - Pydantic v2 SSOT models in [schemas.py](../../../tooling/ai-engines/quant_core/schemas.py) enforce unit suffixes (`_frac`, `_pct`, `_usd`), IANA timezones, and non-future `verified_utc`.
   - Single machine-readable portfolio ledger: [PORTFOLIO-REGISTRY.json](../../../planning/research/PORTFOLIO-REGISTRY.json).
2. **Data & Derived Cache** ([data_store.py](../../../tooling/ai-engines/quant_factory/data_store.py)):
   - Sealed M1 Bid/Ask Parquet cache on local SSD (`.runtime/hot-m1-cache/`).
   - Precomputed minute-by-minute frozen engine tapes persist as zero-pickle `.npz` + builder/manifest SHA-verified `.json` in `.runtime/hot-m1-cache/_derived/` (`< 0.30s` warm load, zero top-level `scipy`/`pyarrow`).
3. **Numba-JIT Statistical & Prop Engine** ([eval_pipeline.py](../../../tooling/ai-engines/quant_factory/eval_pipeline.py), [prop_engine.py](../../../tooling/ai-engines/quant_factory/prop_engine.py), `quant_core/`):
   - Sign-flip permutation, BH-FDR, Bailey-Lopez de Prado DSR/PSR, CSCV PBO, CPCV, Hansen SPA, worst-5% tail correlation, and Prague-reset M1 lifecycle simulation verified against stdlib `Decimal` oracle.
4. **Verified Reporting & MQL5 Guard** ([report_gen.py](../../../tooling/ai-engines/quant_factory/report_gen.py), [Naqex_PropGuard.mqh](../../../tooling/ai-engines/exports/Include/Naqex_PropGuard.mqh)):
   - Atomic temp+fsync+replace JSON/Markdown reports (`quant_core/io_utils.py`) with SHA-256 receipts and single-master EA (`Naqex_Master_Prop7E.mq5`).

## Core Maintenance Gates

### 1. Health, Architecture & Regression Gate (`system_doctor.py` + `check_architecture.py`)

Run fast mode during active edits (`< 4.0s`) and full mode before milestones:

```powershell
$py = 'D:\ANNAM\TradingWorkspace\.runtime\quant-audit-v24\Scripts\python.exe'
& $py -X utf8 tooling/ai-engines/system_doctor.py --mode fast
& $py -X utf8 tooling/check_architecture.py --strict
& $py -X utf8 tooling/ai-engines/system_doctor.py --mode full
```

### 2. Anti-Bloat & Index Hygiene (`ARCH-03..05`)

- Keep `planning/research/README.md <= 15,000 B` (target `< 10,000 B` / `<= 100` lines); archive historical passes into `planning/research/archive/` + `planning/research/ARCHIVE-INDEX-YYYYMM.md`.
- Keep `planning/CURRENT-CONTEXT.md <= 12,000 B` and never add new loose `.py` files to `tooling/ai-engines/` root (place experiments in `experiments/`, core modules in `quant_core/` or `quant_factory/`).
- Compact any branch-touched research JSON `> 900 KB` with cold-backup SHA-256 pointer.

### 3. Detailed Runbooks (Load On Demand)

Read [references/mt5-and-compute-runbook.md](references/mt5-and-compute-runbook.md) for:
- Long-horizon / overnight swarm sizing and event-driven time compression.
- Canonical English Dev MT5 Portable, headless `tester.ini` auth/isolation, multi-asset MQL5 invariants, and `MQL_TESTER` blind-spot rules.
- 3-node Star Topology compute routing (`compute_router.py`, `<DEV_PC>` Mode A/B, `<X13_WORKER>` `1.5s` AC-only probe, NTP `< 1,000 ms` gate).
- Binary-wheel-only supply-chain upgrade rules (`uv pip --only-binary=:all:`).

## Workflow Handoffs

- **Pre-handoff falsification:** Run [adversarial-self-audit](../adversarial-self-audit/SKILL.md) before closing major quant/parity/compute/optimizer edits.
- **Downstream / peer skills:** [strategy-qualification](../strategy-qualification/SKILL.md) for gate verdicts, [evidence-continuity](../evidence-continuity/SKILL.md) for durable receipts, and [naqex-node-ops](../naqex-node-ops/SKILL.md) for Home-VPS deployment.

## Negative Triggers

- Do not use for strategy hypothesis design (use [strategy-research](../strategy-research/SKILL.md)), white-box discovery (use [whitebox-prop-discovery](../whitebox-prop-discovery/SKILL.md)), or strategy qualification verdicts (use [strategy-qualification](../strategy-qualification/SKILL.md)).
- Do not use for trading tutoring, UI platform changes, or unlocking Holdout/live broker execution.

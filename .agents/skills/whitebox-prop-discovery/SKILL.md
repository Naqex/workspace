---
name: whitebox-prop-discovery
description: Discover, intake-audit, and validate prop-first white-box trading strategies (FTMO Swing/Standard, swap=0, zero-grid/martingale) on sealed M1 Bid/Ask caches using strict Cluster A discovery and blind Cluster B validation, then export auditable .mq5 templates for verified candidates. Use for systematic prop strategy discovery or auditing open-source .mq5 leads; never use to crack, run, or black-box-clone closed-source commercial .ex4/.ex5 binaries.
---

# White-Box Prop-First Strategy Discovery

Discover and qualify FTMO-compatible white-box strategies without black-box `.ex4`/`.ex5` execution, grid/martingale traps, or in-sample data mining.

## Hard boundaries

- **No closed-source binary cloning:** Never execute, crack, or black-box-clone unauthorized commercial `.ex4`/`.ex5`/`.dll` binaries. Accept only open-source `.mq5`/`.py`/`.pine` specifications, verified public trade-log CSV DNA audits, or clean-room mathematical rules.
- **Holdout lock (`>= 2025-01-01`):** Always read from sealed Development caches (`holdout_rows = 0`, `NATIVE_FTMO_HOLDOUT_LOCK.json`). Never touch holdout during discovery or screening.
- **Prop-first constraints:** Prefer intraday `swap = 0` (or verified positive-swap), hard SL on every order, max 1 position per engine/symbol, zero grid/martingale, and Prague-reset daily loss safety.
- **Fail-closed execution:** Generated `.mq5` templates MUST keep `InpDryRunLogOnly = true` by default (`OrderSend = 0`). Qualification gates belong to [validation-gates.md](../strategy-qualification/references/validation-gates.md).

## Workflow

1. **Pre-register search budget before running:** Freeze the candidate grammar space, asset list, `m_total` hypothesis count, cost model, and stop rules in `planning/research/` before inspecting Cluster B outcomes.
2. **Multi-source inbox & open-source `.mq5` intake triage:** When the owner drops new external leads into `D:\ANNAM\strategy-intel\inbox\` (`01-open-source-code/`, `02-trade-logs-csv/`, `03-papers-and-notes/`, `04-quarantine-setfiles/`), run [inbox_intake_scanner.py](../../../tooling/ai-engines/inbox_intake_scanner.py) (`--defender`) for read-only quarantine of binaries (`.ex4/.ex5/.exe/.dll/.rar`) and automatic FTMO red-flag triage via `audit_open_source_mq5` in [mq5_whitebox_exporter.py](../../../tooling/ai-engines/mq5_whitebox_exporter.py).
3. **Run strict-split white-box discovery:** Execute [whitebox_discovery.py](../../../tooling/ai-engines/whitebox_discovery.py) on the D: SSD Hot M1 Parquet Cache:
   - **Discovery split (Cluster A ONLY, `2018–2020`):** Screen grammar candidates strictly on Cluster A (`n_A >= 60`, `FTMO Stress > 0`, `PF_A > 1.05`).
   - **Blind OOS split (Cluster B, `2021–2024`):** Evaluate Cluster A survivors blind on Cluster B, applying **Benjamini–Hochberg FDR over the entire search space `m_total`**, paired sign-flip + random-entry MC Null (`N = 1,000`), Fade superiority, and daily correlation `r(USDJPY)` against the frozen core.
   - **3-Tier output:** Classify every candidate into `TIER_1_FTMO_READY`, `TIER_2_PERSONAL_VAULT` (with `PROVISIONAL_XAU` whenever native Ask is absent), or `TIER_3_DEAD_NO_EDGE`.
4. **Forensic gate before `.mq5` export:** Any `TIER_1` candidate MUST pass 3 cost tiers (`Base`, `Stress +0.5`, `Stress +1.0`), 12-cell 2D parameter plateau, 4-axis decomposition, and Prague-reset M1 floating-equity portfolio audit before exporting an `.mq5` template via `export_exp_daily_open_mq5`.

## Commands

```powershell
$py = 'D:\ANNAM\TradingWorkspace\.runtime\quant-audit-v24\Scripts\python.exe'
$env:PYTHONPATH = 'D:\ANNAM\TradingWorkspace\tooling\ai-engines;D:\ANNAM\TradingWorkspace\projects\trader\foundation_v2\src'
& $py tooling/ai-engines/whitebox_discovery.py --output 'E:\BACKUP-TRADINGWORKSPACE\ai-engine-jobs\whitebox-discovery-run'
```

## Negative triggers

- Do not trigger for simple status checks, trading education lessons, UI changes, or ordinary codebase edits.
- Do not trigger to download, run, decompile, or imitate proprietary `.ex4`/`.ex5` binaries from warez/redistribution sites.

---
name: whitebox-prop-discovery
description: Discover, intake-audit, and validate prop-first white-box strategies (FTMO Swing/Standard, swap=0, zero-grid/martingale) on sealed M1 Bid/Ask caches via Cluster A -> blind Cluster B, then export auditable .mq5 templates. Use for prop strategy R&D or open-source .mq5 audits; do not use to crack/clone .ex4/.ex5.
---

# White-Box Prop-First Strategy Discovery

Discover and qualify FTMO-compatible white-box strategies without black-box `.ex4`/`.ex5` execution, grid/martingale traps, or in-sample data mining.

## Hard boundaries

- **No closed-source binary cloning:** Never execute, crack, or black-box-clone unauthorized commercial `.ex4`/`.ex5`/`.dll` binaries. Accept only open-source `.mq5`/`.py`/`.pine` specifications, verified public trade-log CSV DNA audits, or clean-room mathematical rules.
- **Holdout lock (`>= 2025-01-01`):** Always read from sealed Development caches (`holdout_rows = 0`, `NATIVE_FTMO_HOLDOUT_LOCK.json`). Never touch holdout during discovery or screening.
- **Prop-first constraints:** Prefer intraday `swap = 0` (or verified positive-swap), hard SL on every order, max 1 position per engine/symbol, zero grid/martingale, and Prague-reset daily loss safety.
- **Fail-closed execution:** Generated `.mq5` templates MUST keep `InpDryRunLogOnly = true` by default (`OrderSend = 0`). Qualification gates belong to [validation-gates.md](../strategy-qualification/references/validation-gates.md).
- **2-Layer Output Boundary (Public Framework vs Private Alpha Vault):** Keep public `tooling/ai-engines/exports/` strictly for open framework code (`Naqex_PropGuard.mqh`, baseline v1 templates, and dry-run/demo kits). Store new proprietary v2/v3 strategy candidates in `private_vault/strategies/`, live/paid challenge `.set` presets in `private_vault/presets/`, and real broker/prop statements in `private_vault/statements/` (gitignored by Layer 1, synced only to the private personal vault). Never commit proprietary v2/v3 alphas, live paid presets, or real broker statements into Public Layer 1.

## Workflow

1. **Pre-register search budget before running:** Freeze the candidate grammar space, asset list, `m_total` hypothesis count, cost model, and stop rules in `planning/research/` before inspecting Cluster B outcomes.
2. **Multi-source inbox & open-source `.mq5` intake triage:** When the owner drops new external leads into `D:\ANNAM\strategy-intel\inbox\` (`01-open-source-code/`, `02-trade-logs-csv/`, `03-papers-and-notes/`, `04-quarantine-setfiles/`), run [inbox_intake_scanner.py](../../../tooling/ai-engines/inbox_intake_scanner.py) (`--defender`) for read-only quarantine of binaries (`.ex4/.ex5/.exe/.dll/.rar`) and automatic FTMO red-flag triage via `audit_open_source_mq5` in [mq5_whitebox_exporter.py](../../../tooling/ai-engines/mq5_whitebox_exporter.py).
3. **Run strict-split white-box discovery:** Execute [whitebox_discovery.py](../../../tooling/ai-engines/whitebox_discovery.py) on the D: SSD Hot M1 Parquet Cache:
   - **Discovery split (Cluster A ONLY, `2018–2020`):** Screen grammar candidates strictly on Cluster A (`n_A >= 60`, `FTMO Stress > 0`, `PF_A > 1.05`).
   - **Blind OOS split (Cluster B, `2021–2024`):** Evaluate Cluster A survivors blind on Cluster B, applying **Benjamini–Hochberg FDR over the entire search space `m_total`**, paired sign-flip + random-entry MC Null (`N = 1,000`), Fade superiority, and daily correlation `r(USDJPY)` against the frozen core.
   - **3-Tier output:** Classify every candidate into `TIER_1_FTMO_READY`, `TIER_2_PERSONAL_VAULT` (with `PROVISIONAL_XAU` whenever native Ask is absent), or `TIER_3_DEAD_NO_EDGE`.
   - **Data sealing (CausalDataStore + `HoldoutLockError`):** Both **`dukascopy-node`** and **`QDM CLI`** are permitted under `CausalDataStore` + programmatic `HoldoutLockError` (`< 2025-01-01T00:00:00Z`, `holdout_rows = 0`). Use `dukascopy-node` for fast SHA-sealed M1 Bid+Ask Dev batches ([fetch_gbpjpy_m1_seal.mjs](../../../tooling/ai-engines/fetch_gbpjpy_m1_seal.mjs) + [seal_gbpjpy_m1.py](../../../tooling/ai-engines/seal_gbpjpy_m1.py), ~2–3 min per 7-year symbol / ~40–50 MB Parquet), and `QDM CLI` for supplemental or raw tick-archive exports (see [STRATEGY-WORKFLOW.md](../../../tooling/ai-engines/STRATEGY-WORKFLOW.md)).
4. **Forensic gate before `.mq5` export:** Any `TIER_1` candidate MUST pass:
   - 3 cost tiers (`Base`, `Stress +0.5`, `Stress +1.0`),
   - **Dual 2D parameter surfaces** (`trigger × SL` AND `trigger × secondary filter`, reporting boundary sensitivity transparently),
   - **Outlier & Crisis Stress** (`-Top3`, `-Top5`, excluding major shock months such as Mar-2020 COVID and Sep–Oct 2022 UK Gilt),
   - 4-axis decomposition & Prague-reset M1 floating-equity portfolio audit before exporting an `.mq5` template via `export_exp_daily_open_mq5` (`audit_open_source_mq5` strips `//` and `/* */` comments before scanning so doc headers do not trigger false positives).
5. **Quant Factory Reuse & Pre-Qualification Audit (Pass 29+):** For portfolio replays, firm/profile sweeps, DSR/PBO/CPCV/Hansen SPA, or MQL5 guard logic, reuse [quant_factory/](../../../tooling/ai-engines/quant_factory/__init__.py), declarative SSOT configs in `tooling/ai-engines/configs/`, [Naqex_PropGuard.mqh](../../../tooling/ai-engines/exports/Include/Naqex_PropGuard.mqh), and [system_doctor.py](../../../tooling/ai-engines/system_doctor.py) instead of duplicating loops in new monolithic scripts. See [quant-factory-ops](../quant-factory-ops/SKILL.md). Before handing any survivor to [strategy-qualification](../strategy-qualification/SKILL.md), run [adversarial-self-audit](../adversarial-self-audit/SKILL.md) to verify zero lookahead and fail-closed invariants.

## Runtime & Commands

- **Required Python runtime:** Always use `D:\ANNAM\TradingWorkspace\.runtime\quant-audit-v24\Scripts\python.exe` (includes `pyarrow`, `numpy`, `numba`, `pytest`, `pytest-xdist`; system Python and product venvs lack them).
- **Node MCP note (troubleshooting):** Local `Node v24.19.0` requires `rea-agents` pinned to `6.7.0 --mcp` (do not bump to `6.10.x` until Node >= `24.22.1`); if `naqex_search` reports stale index, rebuild via `uv run --no-project --python 3.12 tooling/search/xerj.py index`.

```powershell
$py = 'D:\ANNAM\TradingWorkspace\.runtime\quant-audit-v24\Scripts\python.exe'
$env:PYTHONPATH = 'D:\ANNAM\TradingWorkspace\tooling\ai-engines;D:\ANNAM\TradingWorkspace\projects\trader\foundation_v2\src'
& $py tooling/ai-engines/whitebox_discovery.py --output 'E:\BACKUP-TRADINGWORKSPACE\ai-engine-jobs\whitebox-discovery-run'
& $py tooling/ai-engines/inbox_intake_scanner.py --defender
```

## Negative triggers

- Do not trigger for simple status checks, trading education lessons, UI changes, or ordinary codebase edits.
- Do not trigger to download, run, decompile, or imitate proprietary `.ex4`/`.ex5` binaries from warez/redistribution sites.

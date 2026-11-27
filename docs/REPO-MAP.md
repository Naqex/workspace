# Naqex Workspace — Agent-First Repository Map

Single concise navigation map for AI agents and solo operators (`OrderSend = 0` by default; `Holdout 2025+ SEALED`). For authority and governance rules, read [AGENTS.md](../AGENTS.md) and [CURRENT-CONTEXT.md](../planning/CURRENT-CONTEXT.md).

## Top-Level Layout

```text
TradingWorkspace/
├── AGENTS.md                         # Workspace-wide agent rules & scope gates (always-loaded)
├── pyproject.toml                    # Unified Ruff, ty, pytest (xdist/worksteal), pythonpath config
├── .github/workflows/workspace.yml   # CI: workspace checks, architecture gate, offline pytest, OPSEC
├── .agents/
│   ├── rules/trading-workspace.md    # Always-on reporting, scorecard & anti-idle rules
│   └── skills/                       # 18 repo skills wired as a closed 9-stage workflow graph
├── docs/
│   ├── REPO-MAP.md                   # This Agent-First workspace map
│   ├── licensing.md                  # Source-available license & third-party boundaries
│   └── development/                  # Dev guide (README.md) & SKILL-MAINTENANCE.md
├── planning/
│   ├── CURRENT-CONTEXT.md            # Active state & next actions (<= 12 KB budget)
│   ├── TOP1-SOLO-QUANT-MASTER-PLAN.md# Single Roadmap SSOT (locked V3 / Step-8 reality)
│   ├── CONTEXT-LIFECYCLE.md          # Compaction, handoff & archive lifecycle rules
│   ├── archive/                      # Frozen historical plans & snapshots (incl. 2026-09/)
│   ├── checkpoints/                  # Dated milestone receipts
│   ├── trader/                       # Naqex Trader product completion & UI plans
│   └── research/                     # Active research reports, README.md (<= 10 KB), PORTFOLIO-REGISTRY.json
│       └── archive/                  # Historical Pass 1-22, V1-V26, US500/INDEX/PROP-V* reports
├── knowledge/                        # Public evergreen playbooks, topics & Layer-1 owner stub
├── education/                        # Bilingual EN-VI trading course, rubrics & check_setup.py
├── UI-Systems/ & UI/                 # Global design-system tokens & trading-domain UI contracts
├── projects/                         # Independent Git submodules (own venvs, tests, CI)
│   ├── trader/                       # Naqex Trader (foundation_v2 Rust + React + Python)
│   ├── quant-trading/                # Crypto Spot daily/4H quant research lab (uv)
│   ├── vi-dubber/                    # AI video translation/dubbing tool (uv)
│   └── integrations/                 # Upstream forks: paperclip, rd-agent, TradingAgents, hermes-agent
├── tooling/                          # Shared governance, quant factory, search & knowledge CLIs
│   ├── check_workspace.py            # Guide links & submodule pin verifier
│   ├── check_skill_links.py          # Skill link & negative-trigger verifier
│   ├── check_architecture.py         # Harness gates [ARCH-01..07] (scipy, assert, bloat, orphans, licenses)
│   ├── naqex_cli.py                  # Unified developer CLI wrapper
│   ├── worktree_ctl.py               # Managed .worktrees/ lifecycle controller
│   ├── run_registry/                 # SQLite hash-chained experiment & event registry (store.py)
│   ├── knowledge/                    # Personal Knowledge Vault CLI (brain_cli.py, research_cli.py)
│   ├── search/                       # Local concept search indexer (xerj.py)
│   ├── github-workflow/              # Lightweight branch/PR/submodule workflow docs & checks
│   ├── integrations/                 # Integration catalog.json & doctor.mjs
│   └── ai-engines/                   # 2-Tier Naqex Quant Factory & MQL5/Ops tooling (below)
└── private_vault/                    # Gitignored Layer-2 private vault (strategies, presets, ops topology)
```

## Inside `tooling/ai-engines/` (2-Tier Clean Layout)

| Folder / Entrypoint | Role & Ownership |
|---|---|
| `quant_core/` | Pure typed SSOT core (`schemas.py`, `metrics.py`, `prop_sim.py`, `decimal_oracle.py`, `red_news.py`, `tca.py`, `holdout_guard.py`, `causality.py`, `io_utils.py`, `mql_contract_drift.py`). Zero top-level `scipy`, zero `assert` on Holdout. |
| `quant_factory/` | Production 4-layer quant pipeline (`data_store.py`, `eval_pipeline.py`, `prop_engine.py`, `report_gen.py`, `research_council.py`, `robustness_gate.py`, `red_team_auditor.py`, `tca_reconcile.py`, `daily_statement_reconciler.py`, `experiment_ledger.py`, `capital_optimizer/`). |
| `experiments/` | One-off research studies (`lab7..12`, `pass29..32`, `round3_frame_benchmark`, `portfolio_v1_vs_v2_study`, `top1_unified_trajectory_study`), with thin backward-compatible shims in `quant_factory/` for callers. |
| `legacy/` | Archived historical `prop_v5..v26`, `v17..v20`, and 0-caller loose scripts (auto-resolved by `quant_test_suite.py` and `tests/conftest.py`). |
| `ops_cloud/` | 3-node compute router (`compute_router.py`, `x13_probe.py`), Home-VPS SSH wrapper (`node_ctl.py`), and Heroku dead-man's-switch monitor (`heroku_deadman/`). |
| `cockpit/` | Local Control Room (`server.py` + `modules/`, `127.0.0.1:8787`) & Prop MetriX telemetry UI. |
| `exports/` | Open framework MQL5 code (`Include/Naqex_PropGuard.mqh`, `Naqex_Master_Prop7E.mq5`), red-news CSV (`Files/naqex_red_news_utc.csv`, 492 events), calibration probe (`calibration_probe/`), and VPS deployment kit. |
| `configs/` | Declarative JSON configs: `ssot/` (Pydantic-validated), `firms/`, `profiles/`, `calendars/`. |
| `tests/` | Full offline pytest + legacy unittest suites (`conftest.py` pins BLAS threads, worksteal & `legacy/` path). |
| Root active core & closure (`233` `.py`) | Active CLIs (`system_doctor.py`, `quant_test_suite.py`, `research_inventory.py`, `strategy_evidence.py`, `inbox_intake_scanner.py`, `mq5_whitebox_exporter.py`, `engine_worker.py`, etc.) + core engines imported by `quant_factory/` & `quant_core/` (`hot_m1_cache.py`, `whitebox_discovery.py`, `pass5..28`). |

## Closed 9-Stage Skill Workflow

```text
research-and-memory-ops -> strategy-research -> whitebox-prop-discovery -> quant-factory-ops
   -> adversarial-self-audit -> strategy-qualification -> naqex-node-ops -> evidence-continuity
   -> engineering-retrospective (-> github-issue-workflow / parallel-agent-workflow)
```

## Essential Verification Commands

```powershell
$py = '.\.runtime\quant-audit-v24\Scripts\python.exe'
& $py tooling/check_workspace.py
& $py tooling/check_skill_links.py --skills-dir .agents/skills --review-triggers
& $py tooling/check_architecture.py --strict
& $py -X utf8 tooling/ai-engines/system_doctor.py --mode fast
& $py -m pytest -o cache_dir=.tmp/pytest-dev -n 4 --dist worksteal -q tooling/ai-engines/tests/test_layer1_opsec_guard.py tooling/ai-engines/tests/test_quant_factory_suite.py
```

## Local Ignored Directories (Never Commit)

- `.runtime/` — Python venv (`quant-audit-v24`), hot M1 Parquet cache, derived `.npz` tapes, local DuckDB/SQLite indexes.
- `.tmp/` — Ephemeral pytest caches (`.tmp/pytest-<lane>`) and swarm handoff dropbox receipts (`.tmp/swarm_dropbox/`).
- `.worktrees/` — Isolated parallel agent Git worktrees managed by `tooling/worktree_ctl.py`.
- `private_vault/` — Layer-2 private personal vault (alpha candidates, paid presets, statements, real host IPs).

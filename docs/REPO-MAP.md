# Naqex Workspace — Agent-First Repository Map

Single concise navigation map for AI agents and solo operators (`OrderSend = 0` by default; `Holdout 2025+ SEALED`). For authority and governance rules, read [AGENTS.md](../AGENTS.md) and [CURRENT-CONTEXT.md](../planning/CURRENT-CONTEXT.md).

## Top-Level Layout

```text
TradingWorkspace/
├── AGENTS.md                         # Workspace-wide agent rules & scope gates (immutable 10,901 B)
├── pyproject.toml                    # Unified Ruff, ty, pytest (xdist/worksteal), pythonpath config
├── .github/workflows/workspace.yml   # CI: workspace checks, architecture gate, offline pytest, OPSEC
├── .agents/
│   ├── rules/trading-workspace.md    # Always-on reporting, scorecard & anti-idle rules
│   └── skills/                       # 19 repo skills wired as a closed graph (incl. poteto-autonomous-verify)
├── docs/
│   ├── REPO-MAP.md                   # This Agent-First workspace map (<= 100 lines)
│   ├── licensing.md                  # Source-available license & third-party boundaries
│   └── development/                  # Dev guide (README.md) & SKILL-MAINTENANCE.md
├── planning/
│   ├── CURRENT-CONTEXT.md            # Active state & next actions (< 8 KB target, ARCH-05 12 KB)
│   ├── TOP1-SOLO-QUANT-MASTER-PLAN.md# Single Roadmap SSOT (locked V3 / Step-8 reality)
│   ├── CONTEXT-LIFECYCLE.md          # Compaction, handoff & archive lifecycle rules
│   ├── archive/ & checkpoints/       # Frozen historical plans, snapshots & dated milestone receipts
│   ├── trader/                       # Naqex Trader product completion & UI plans
│   └── research/                     # Active reports, README.md (< 14.5 KB, <= 150L), PORTFOLIO-REGISTRY.json
│       └── archive/                  # Historical Pass 1-22, V1-V26, US500/INDEX/PROP-V* reports
├── knowledge/                        # Public evergreen playbooks, topics & Layer-1 owner stub
├── education/                        # Bilingual EN-VI trading course, rubrics & check_setup.py
├── UI-Systems/ & UI/                 # Global design-system tokens & trading-domain UI contracts
├── projects/                         # Independent Git submodules (own venvs, tests, CI)
│   ├── trader/                       # Naqex Trader (foundation_v2 Rust + React + Python)
│   ├── quant-trading/                # Crypto Spot daily/4H quant research lab (uv, numpy+pandas)
│   ├── vi-dubber/                    # AI video translation/dubbing tool (uv)
│   └── integrations/                 # Upstream forks: paperclip, rd-agent, TradingAgents, hermes-agent
├── tooling/                          # Shared governance, automation, workflows, quant factory & CLIs
│   ├── check_workspace.py            # Guide links & submodule pin verifier
│   ├── check_skill_links.py          # Skill link & negative-trigger verifier
│   ├── check_architecture.py         # Harness gates [ARCH-01..10] (scipy, assert, bloat, orphans, licenses, automation)
│   ├── naqex_cli.py                  # Unified developer CLI wrapper (incl. `auto <9 subcommands>`)
│   ├── worktree_ctl.py               # Managed .worktrees/ lifecycle controller
│   ├── automation/                   # Self-healing 24/7 runner, watchdog, briefing, radars & 1-way intel bridge
│   │   └── configs/                  # feature_map.json, research_watchlist.json, frontier_alpha_candidates.json, sidecars/
│   ├── workflows/                    # Reusable Antigravity run_workflow scripts (audit_19_gates.py, pareto_strategy_sweep.py)
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
| `quant_core/` | Pure typed SSOT core (`41` modules: `schemas`, `metrics`, `prop_sim`, `decimal_oracle`, `red_news`, `tca`, `holdout_guard`, `causality`, `io_utils`, `mql_contract_drift`). `0` ruff/format/ty/CRLF. |
| `quant_factory/` | Production 4-layer quant pipeline (`data_store`, `eval_pipeline`, `prop_engine`, `report_gen`, `research_council`, `robustness_gate`, `red_team_auditor`, `tca_reconcile`, `daily_statement_reconciler`, `experiment_ledger`, `preregister_holdout_v2`, `capital_optimizer/`). |
| `experiments/` | Research studies (`lab7..12`, `pass29..32`, `flashcrash_pareto_study`, `portfolio_7e_plus_alpha2_study`, `three_sleeve_top1_roadmap_study`), with backward-compatible shims in `quant_factory/`. |
| `legacy/` | Archived historical `prop_v5..v26`, `v17..v20`, and 0-caller loose scripts (auto-resolved by `quant_test_suite.py` and `tests/conftest.py`). |
| `ops_cloud/` | 3-node compute router (`compute_router.py`, `x13_probe.py`), Home-VPS SSH wrapper (`node_ctl.py`), quote collector, and Heroku dead-man's-switch monitor (`heroku_deadman/`). |
| `cockpit/` | Local Control Room (`server.py` + `modules/`, `127.0.0.1:8787`, stateless `/api/automation/*`) & Prop MetriX telemetry UI. |
| `exports/` | Open framework MQL5 code (`Include/Naqex_PropGuard.mqh`, `Naqex_Master_Prop7E.mq5`, candidate `v103`), red-news CSV (`Files/naqex_red_news_utc.csv`, 492 events), calibration probe, and VPS deployment kit. |
| `configs/` | Declarative JSON configs: `ssot/` (Pydantic-validated), `firms/`, `profiles/`, `calendars/`. |
| `tests/` | Full offline pytest + legacy unittest suites (`conftest.py` pins BLAS threads, worksteal & `legacy/` path). |
| Root active core (`233` `.py`) | Active CLIs (`system_doctor.py`, `quant_test_suite.py`, `research_inventory.py`, `strategy_evidence.py`, `inbox_intake_scanner.py`, `mq5_whitebox_exporter.py`, `engine_worker.py`) + core engines (`hot_m1_cache.py`, `whitebox_discovery.py`, `pass5..28`). |

## Cleanroom 1-Way Bridge & Skill Workflow

- **1-Way Cleanroom Intake (`D:\ANNAM\strategy-intel` -> `TradingWorkspace`):** Air-gapped external repo (`4/4` cleanroom guards: `repo_hygiene_check`, `verify_verbatim`, `holdout_sanitizer`, `test_guards`). `tooling/automation/strategy_intel_bridge.py` reads `handoff/sanitized_{master,auto}_leads.json` in-memory (`untrusted_external_data: true`, `0` bytes written back to `strategy-intel`, `0` `2025/2026` leakage) into `.runtime/automation/strategy_intel_handoff_latest.json`.
- **Closed Skill Graph:** `research-and-memory-ops -> strategy-research -> whitebox-prop-discovery -> quant-factory-ops -> adversarial-self-audit -> poteto-autonomous-verify -> strategy-qualification -> naqex-node-ops -> evidence-continuity -> engineering-retrospective`.

## Essential Verification Commands (PC Dev Mode-A Safe)

```powershell
.\.runtime\quant-audit-v24\Scripts\python.exe tooling/check_workspace.py
.\.runtime\quant-audit-v24\Scripts\python.exe tooling/check_skill_links.py --skills-dir .agents/skills --review-triggers
.\.runtime\quant-audit-v24\Scripts\python.exe tooling/check_architecture.py --strict
.\.runtime\quant-audit-v24\Scripts\python.exe -X utf8 tooling/ai-engines/system_doctor.py --mode fast
.\.runtime\quant-audit-v24\Scripts\python.exe -X utf8 tooling/naqex_cli.py auto status --offline --json
.\.runtime\quant-audit-v24\Scripts\pytest.exe -o cache_dir=.tmp/pytest-dev -n 2 --dist worksteal -m "not local_cache" -q tooling/ai-engines/tests/test_layer1_opsec_guard.py tooling/ai-engines/tests/test_quant_factory_suite.py
```

## Local Ignored Directories (Never Commit)

- `.runtime/` — Python venv (`quant-audit-v24`), hot M1 Parquet cache, derived `.npz` tapes, local DuckDB/SQLite indexes, `.runtime/automation/` receipts.
- `.tmp/` — Ephemeral pytest caches (`.tmp/pytest-<lane>`) and swarm handoff receipts (`.tmp/swarm_dropbox/`).
- `.worktrees/` — Isolated parallel agent Git worktrees managed by `tooling/worktree_ctl.py`.
- `private_vault/` — Layer-2 private personal vault (alpha candidates, paid presets, statements, real host IPs).

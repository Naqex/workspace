# Coding-agent tools — 2026-11-02

Scope: install useful research candidates, minimally verify benefit on this
workspace, retain existing product/runtime ownership. No broker/provider calls,
product changes, global instruction changes, new accounts or keys.

## Decision

| Tool | Result | Routing |
|---|---|---|
| `rg` | Keep as the first tool for exact names/text | Fast baseline, no index |
| Xerj | Keep existing installation; refresh and smoke-test | Passage/symbol lookup |
| CodeGraph 1.6.2 | Installed locally, CLI only | Named callers/callees/impact |
| Context7 | Add optional project HTTP MCP; live HTTP smoke passed | Public library documentation |
| Graphify, Obsidian, QMD, Serena | Not installed | No distinct benefit demonstrated for the current task |

Runtime still exposes neither new Context7 tools nor the configured Xerj tools
in this session. A new session/reconnect and trusted project config are needed;
saving configuration and testing HTTP do not establish agent-tool availability.

## Installation and data flow

- CodeGraph: official `@colbymchenry/codegraph@1.6.2`, MIT; package and platform
  bundle pinned by committed npm lockfile. `npm install --ignore-scripts` ran
  locally. `npm audit signatures` verified registry signatures and attestations
  for both installed packages. This does not prove absence of vulnerabilities.
- Executable/dependencies: `.runtime/tools/codegraph/1.6.2/`, 266.3 MB.
- Wrapper reuses Xerj's Git-tracked allowlist, with a separate snapshot under
  `.runtime/search/codegraph/`, 49.0 MB including source snapshot and 42.7 MB DB.
  No whole-workspace/runtime/credential/dataset/holdout scan. It disables
  telemetry, download fallback, update checks and daemon behavior per process.
- The native `init` installer was avoided: its DB API initializes only the
  local index. No upstream config/instruction rewrites. Index is explicit;
  queries compare current source hashes and refuse missing, stale or incomplete
  manifests. Source remains authoritative. No concurrent index/query on one corpus.
- Context7 uses `https://mcp.context7.com/mcp` directly. Only
  `resolve-library-id` and `query-docs` are enabled, with bounded timeouts and
  `required=false`. Only public React documentation queries were sent. No local
  proxy/npm dependency or background service was added. Anonymous access worked
  in this run; quotas/authentication requirements can change.
- The initial trial graph was moved out of Xerj's corpus into local benchmark
  artifacts (42.7 MB). Only generated evidence/runtime files exist there.

## Minimal benchmark

Windows x64, Python 3.12, local source snapshot. Both tools searched the same
snapshot, restricted to JS/JSX for the `rg` baseline. CodeGraph queries include
Python wrapper startup and freshness checks. Single observation per query;
timings are diagnostic, not a statistically stable throughput benchmark.

| Symbol | `rg` ms | Graph ms | `rg` output bytes | Graph output bytes |
|---|---:|---:|---:|---:|
| `shiftCalendarMonth` | 41.9 | 1323.7 | 583 | 321 |
| `civilMonthWeeks` | 57.6 | 1329.6 | 715 | 439 |
| `buildAnalyticsModel` | 39.0 | 1398.5 | 3367 | 1411 |

Commands: `rg -n -w -g '*.js' -g '*.jsx' <symbol> .` in the snapshot;
`python -X utf8 tooling/search/codegraph.py callers <symbol>` at workspace root.
`rg` returns occurrences; Graph returns definition/caller identities and import
relationships. These are different representations, not equivalent full-source
outputs. Smaller output does not establish token savings or faster end-to-end
engineering. Prefer `rg` for exact lookup; keep Graph for structural navigation.

Correctness checked against original source:

- `shiftCalendarMonth`: definition `calendarViewModel.js:1`, caller `step` in
  `CalendarView.jsx:9` found correctly.
- `civilMonthWeeks`: definition `calendarViewModel.js:7`, caller `calendarWeeks`
  in `liveWorkspaceModel.js:42` found correctly. Graph **misses** the call in
  `CalendarMonth`'s default parameter (`CalendarView.jsx:25`); it does return that
  file's import. Therefore graph output is not a complete call-site inventory.
- `buildAnalyticsModel`: graph identifies seven named calling functions across
  six files, separating them from six import references; source was read back.
- `impact shiftCalendarMonth --json` references `CalendarView.jsx` as expected.
- Initial native graph build: 12.670 s on 517 source/docs files. After tooling
  additions, both snapshots have 518 files; graph covers supported code files
  only. Xerj's later refresh indexed 389 code files, 6782 records, 14.6 s.
- Context7 server reported 4.4.3. React library resolution selected
  `/reactjs/react.dev` (~1.75 s); `query-docs` returned cleanup/event-listener and
  Strict Mode documentation with official source paths in 1.667 s, 6784 bytes.
  No claim that this beats web search or improves overall coding success rate.

Raw results, measured commands and smoke artifacts are local under
`.runtime/search/benchmark/` (`run.py`, `results.json`, `context7-react.sse`,
caller JSON and `impact.json`). They are intentionally not committed with source.

## Verification and maintenance

- Real CLI index/query/callers/callees/status/impact smoke checks passed.
- Isolated manifests: missing/stale/incomplete indexes refused; matching
  manifest accepted. Tests did not modify product source or the real manifest.
- Both real indexes passed freshness checks after the final wrapper change.
- Project TOML parsed with `tomllib`; exact Context7 allowlist verified.
- AI environment audit: **0 errors, 0 warnings**. Global 12279 B, project
  9099/65536 B, project reserve 56437 B, combined 21378 B; no instruction growth.
- Diff whitespace check passed. Existing Trader plan, VI Dubber WIP and evidence
  were outside this change. No product build/full suite was needed for local
  optional retrieval/configuration changes.

Usage, reinstall and rollback: [search README](../../../../tooling/search/README.md).
No automatic upgrades. Re-evaluate a pin when a real parser/platform issue or
security update justifies it; do not schedule services or add MCPs just for coverage.

Primary sources:
[CodeGraph](https://github.com/colbymchenry/codegraph),
[Context7 tool/connection docs](https://context7.com/docs/resources/all-clients),
[Codex MCP configuration](https://learn.chatgpt.com/docs/extend/mcp).

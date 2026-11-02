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

## RTK explicit trial — không promote

Owner duyệt thử riêng, không bật tự động. Tải official RTK OSS 1.1.0 cho Windows,
Apache-2.0; release archive digest khớp. Bản OSS được chọn tường minh vì default
edition có BUSL engine. Không chạy init/install hooks, không sửa global config
hoặc PATH. Telemetry/recall/tee tắt; tracking DB ở runtime thử riêng.

Archive SHA256:
`9b076379be9d86011ca3f3a0264d0be4851da5535453a47f67fa46b4e893fbb2`.
Exe SHA256 lúc thử:
`431abf30cf72213ad85bcc4526b67c55ca519336efbbf3c1630e388a1f3f4b0f`.
Source: [official OSS release](https://github.com/rtk-ai/rtk/releases/tag/v1.1.0).

| Command | Raw bytes / median ms | RTK bytes / median ms | Native compact bytes / median ms |
|---|---:|---:|---:|
| git status | 723 / 421 | 219 / 1033 | 220 / 388 |
| git log -n 20 | 5909 / 59 | 3546 / 279 | 3563 / 53 |

3 samples/command, same checkout. RTK includes reviewed Python wrapper startup;
native compact Git uses the useful field set, not byte-identical output.
These short diagnostic samples do not establish universal RTK latency or an
end-to-end coding-agent improvement. No token savings measured.

Focused engine suite: all 16 tests passed raw and RTK, output 2577 → 126 bytes.
Deliberately failing unittest preserved exit 1 but RTK dropped traceback and
`EXPECTED_BOUNDARY_FAILURE` assertion marker; raw output retained both.
Sampled source search compressed only 663 → 659 bytes. Decision: native
`git status --short --branch` and
`git log -n 20 --format='%h %s (%ar) <%an>%n%b'` meet this need with fewer layers.
Do not filter test/debug output automatically.

Executable RTK and tracked trial wrapper/lock candidate removed after review;
only ignored archive/evidence remain. Local artifacts:
`.runtime/tools/rtk/benchmark/{results.json,*-raw.txt,*-rtk.txt,reviewed-wrapper.py,reviewed-pin.json}`;
benchmark scripts in `.runtime/tools/rtk/`. No hook/service/global change.
Ponytail review/audit principles were applied through caller/data-flow and
failure controls in RD pilot; no duplicate broad plugin/skill installed and no
Ponytail performance claim. Research/result details:
[coding addons](../../../research/CODING-AGENT-ADDONS-20261102.md).

Hermes research was refreshed against official MCP plugin and app-server docs;
no installation/configuration performed. Existing manager ownership/navigation
was clarified in the development guide, without another registry/daemon.

Final focused verification: AI environment audit **0 errors, 0 warnings**;
global 12279 B, project 9099/65536 B, reserve 56437 B, combined 21378 B.
Workspace contracts passed: 9 guides, 7 pinned submodules. Changed local Markdown
links resolve, pilot Python AST parses with the recorded source hash unchanged,
and RTK executable is absent. Diff whitespace check passed. Existing product
plan/VI Dubber/evidence WIP left outside these commits. No unchanged provider
call, engine test suite or full product build repeated just for documentation.

## Context discovery sau đối chiếu harness — 02/11

Owner giao thực hiện đề xuất ở [research bổ trợ](../../../research/CODING-AGENT-ADDONS-20261102.md).
Lát này sửa cách tìm nguồn, không đổi global instructions, hooks, skills,
MCP/config, model, engines hoặc quyền runtime. Không dựng thêm knowledge manager.

### Thay đổi và data/state flow

- `docs/development/README.md` có bảng dẫn tới QDM, AI plan/receipt, engine
  contracts, job lifecycle và Trader ownership/runtime. Bảng chỉ route tới owner
  đã có, không copy trạng thái job thành registry mới.
- Brief autonomy ghi rõ các đề xuất31/10 là lịch sử; đầu brief dẫn scope tới
  AI plan, kết quả tới receipt và setup tới integration guide. Hai ghi chú
  “chưa cài/tích hợp RD-Agent” được đặt lại đúng thời điểm thay vì xóa lịch sử.
- CURRENT-CONTEXT dẫn trực tiếp tới AI plan/receipt và QDM. AI plan sửa dòng
  “chưa dữ liệu Forex” thành đã có export M1, vẫn thiếu tick Bid/Ask/cost cho
  runner. Không ghi backtest/Prop pass hoặc mở quyền từ việc đã export.
- Tái dùng CLI runner bằng `tasks/context-routing.json`: một task read-only,
  allowed_files rỗng,11file inputs công khai trong repo. Snapshot giữ policy và
  hash riêng. README giải thích prepare không gọi model hoặc tự nghiệm thu.
  Task có acceptance hiển thị; đây là regression smoke có hướng dẫn, không là
  blind benchmark/holdout hoặc bằng chứng tổng quát hóa của model.

### Kiểm tra trước/sau và giới hạn

Hai packet chính ở `tooling/agent-workflow/runs/` (ignored):
`20261102-130804-context-routing-02bc44` trước sửa và
`20261102-131022-context-routing-851db2` sau sửa. Một packet trung gian giữ nguyên
để truy vết, không dùng so sánh. Cùng task/input paths/policy, khác nội dung đúng
4tài liệu được sửa. Tất cả vẫn `prepared`,0attempts; không worker/model call.

Diagnostic offline bắt đầu tại developer guide, tìm đường qua Markdown links
trong cùng11file được stage. Alias Trader AGENTS trong packet được map về source
path khi tính liên kết. Chỉ đếm file hops; không mô phỏng `rg`, đọc theo section,
độ hiểu semantic, thời gian LLM hoặc toàn bộ repo ngoài packet.

| Câu hỏi / nguồn đích | Trước: linked hops | Sau: linked hops |
|---|---:|---:|
| QDM đã có và độ phân giải dữ liệu | 4 | 1 |
| Kết quả AI mới nhất trong receipt | 2 | 1 |
| Ownership/quyền source Trader | Không có đường trong packet | 1 |
| Contract quyền research | 1 | 1 |
| Run bị ngắt/receipt còn running | 1 | 1 |

Đã đọc nguồn đích để đối chiếu5câu: QDM/M1 không thành tick Bid/Ask; PLAN và
receipt có ownership riêng; source không là runtime; research/review không cấp
broker/holdout/promotion authority; hard-killed `running` là interrupted/unknown.
Đây là review thủ công của agent đang làm, không phải5cold-context model trials.
Không diễn giải “không có linked path” thành agent không tìm được bằng search.

Script, input hashes, routes và kết quả diagnostic local:
`.runtime/context-routing-20261102/{evaluate.py,navigation-results.json}`.
Hash packet khớp sau kiểm tra, allowed_files rỗng; không source/DB/runtime ghi bởi
worker. Không rerun engine/financial suites không đổi chỉ để kiểm tài liệu.

Kiểm liên kết4tài liệu context đã sửa đạt; workspace checker đạt9guides/8pins.
Audit trước sửa:0errors/0warnings, global12.279B, project9.099/65.536B,
reserve56.437B, combined21.378B,16skills. Đây là instruction audit, không phải
tổng prompt hoặc phép đo tốc độ agent. AI environment definitions không thay.
Audit sau sửa cũng0errors/0warnings, các byte/reserve giữ nguyên; diff check đạt.

Bước đo bằng model khi được giao: cùng config/source, fresh sessions/workspaces,
2–3lượt mỗi nhóm để sàng lọc, kiểm đúng hành vi/boundary và sửa chữa owner cần
làm; chỉ mở rộng ca còn bất định. Chưa có A/B model efficacy hoặc whole-harness
acceptance. Lát Forex quay về contract/QDM/receipt hiện có, không dispatch lại
workflow crypto hoặc thêm downloader trước khi xác minh nguồn tick bounded.

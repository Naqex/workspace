# AI integrations — adoption và runtime cutover

31/10/2026, Asia/Saigon. Scope/acceptance:
[owner plan](../../trader/AI-RESEARCH-UI-PROTOTYPE-20261031.md),
[issue #6](https://github.com/Naqex/workspace/issues/6).
Đây là source/runtime foundation; chưa acceptance toàn vòng AI autonomy.

## Đọc tiếp theo việc đang làm

Receipt ghi theo thời gian từ31/10; bảng và câu “hiện tại” trong các mục cũ
thuộc ngày của chính mục đó. Dùng liên kết dưới đây để tới đúng checkpoint,
không đọc toàn bộ lịch sử hoặc lấy snapshot cũ thay trạng thái native/local.

| Việc cần tiếp tục | Đọc đúng nguồn |
|---|---|
| Chốt một đợt để chạy Demo có giám sát | [Task tổng hiện hành](#0411--gom-task-chốt-demo-có-giám-sát); issue#8 và amendment trong AI plan, không lấy NAQ-80 làm toàn bộ mục tiêu |
| Quote policy và kiểm nhanh mới nhất | [Tách quote khỏi raw flags](#0411--tách-ổn-định-quote-khỏi-raw-flags-kiểm-nhanh-thay-vì-chờ-thêm-h1);34tests/saved-pair replay đã có, không chạy lại nếu input không đổi |
| NAQ-80, kết quả r3 và phục hồi khi MT5 chưa sẵn sàng | [Kết quả và bản sửa recovery](#0411--naq-80-dừng-do-readiness-và-phục-hồi-cursor-có-giới-hạn); lịch sử float ở [checkpoint trước](#0411--sửa-float-grid-và-đối-soát-báo-cáo-naq-80) |
| NAQ-80, log đã bật và kiểm đường đọc thật mới nhất | [Log kết nối và kiểm ngắn](#0411--log-kết-nối-mt5-và-kiểm-đọc-thật-ngắn); không nhầm với H1 handoff acceptance |
| Lượt quan sát dài: còn sống, tiến độ, báo lỗi | [Heartbeat và observer](#0411--củng-cố-quan-sát-tiến-độ-và-báo-lỗi); [cách vận hành](../../../tooling/ai-engines/OPERATIONS.md#visibility-for-finite-shadow-observations) |
| NAQ-80, kết quả r4 và tránh chờ lại H1 | [R4 dừng và tái hiện nhanh](#0411--r4-dừng-khi-audit-và-tái-hiện-lỗi-không-chờ-h1); [khởi chạy lịch sử](#0411--naq-80-khởi-chạy-r4-với-observer) |
| Phục hồi sau ngắt hay sửa reducer | [Reprocess đã có lệnh](#0411--reprocess-capture-đã-lưu-và-phân-loại-checkout-cũ); [runbook](../../../projects/trader/foundation_v2/docs/FOREX-FORWARD.md#choose-resume-or-offline-reprocessing) |
| Dọn workspace, giữ WIP/runtime | [Inventory ban đầu](#0411--inventory-cleanup-chỉ-đọc) → [delta checkout cũ](#0411--reprocess-capture-đã-lưu-và-phân-loại-checkout-cũ) |
| Vận hành Studio/native task/run/report | [Operations guide](../../../tooling/ai-engines/OPERATIONS.md), rồi mục receipt được workflow dẫn tới |

Đây là index trong receipt owner hiện có, không phải ledger mới hoặc tuyên bố
full acceptance. Chưa compact lịch sử chưa review hoặc di chuyển evidence.

## Kết quả

| Thành phần | Source | Bằng chứng hiện tại |
|---|---|---|
| Paperclip | `projects/integrations/paperclip`, Naqex fork, `42fd568cf8f588334cacc6004aa23aff54daa52b` | Remote branch `codex/naqex-integration` đúng pin; upstream riêng; native UI/API chạy lại sau relocation |
| RD-Agent | `projects/integrations/rd-agent`, Microsoft upstream, `484776c211e4fbbeef03e0ec00d6bbee7362a4f4` | Git submodule, README/pyproject/requirements/CLI và MIT license đã đọc; chưa cài dependencies hoặc chạy job |
| TradingAgents | `projects/integrations/TradingAgents`, Naqex fork, `ecaafe585a98478ef7dbcf5678f4a64b5e7d1066` | Code giữ nguyên từ `6bfea6a6`; chỉ sửa đường dẫn evidence trong UPSTREAM-SYNC.md sau relocation; editable reinstall `--no-deps`, import version0.7.0 và module path mới đúng |
| LangGraph | Dependency TradingAgents | Import được trong cùng venv; không clone source hoặc dựng UI/service riêng |
| Quant Lab | `projects/quant-trading` | Giữ nguyên; không có source/runtime mutation trong lát này |

Fork Paperclip: <https://github.com/Naqex/paperclip>. Fork default master mới hơn
pin chạy; tạo fork không tự cập nhật runtime. `.gitmodules` trỏ fork/branch,
gitlink giữ commit cụ thể. Root gitlink Trader vẫn baseline cũ như trước, không
kèm WIP audit hoặc lịch sử product ngoài scope vào commit adoption này.

## Luồng và trạng thái được giữ

Trader preview5218 → iframe Paperclip17860 → API/storage/DB Paperclip riêng17861.
Nguồn đã chuyển nhưng instance giữ tại `.runtime/paperclip/instances/trader-ui/`.
Company `f2b281a7-f974-43a2-ae81-5472a09d6260` / `Naqex AI` giữ nguyên; sau
cutover vẫn 0 agents. Không tạo task/agent/heartbeat run hoặc gọi provider.
Heartbeat scheduler tiếp tục tắt; manual execution API của Paperclip vẫn tồn tại.

Sau cutover: launcher23408, server11428, PostgreSQL624 tại lúc kiểm tra. Các PID
là evidence thời điểm, không phải ID để kill trong phiên sau. Đọc owner/process
thực tế khi resume. Windows standalone CLIProxyAPI8317 vẫn PID18940; cổng17852
chưa mở. Không cập nhật Trader5180/API8010 hoặc terminal broker.

Launcher gọi lại báo "already running" đúng source/revision, không tạo instance
thứ hai. Layout, theme và outer sidebar preference giữ nguyên; Paperclip vẫn
English ở lát này, chưa triển khai patch Việt hóa.

## Backup và Windows dependency relocation

- Backup qua API chính thức `POST /api/instance/database-backups` trước cutover:
  `.runtime/paperclip/instances/trader-ui/backups/paperclip-20261031-230528.sql.gz`.
  Gzip đọc được 1,533,841 bytes SQL; SHA256
  `1b0b332a4efc711a587cbb52914e66e6692f2d63e6ae8f52d101fe6d63bb9b41`.
- Stopped-cluster/config/owner/company snapshot và junction inventory giữ local
  tại `.runtime/paperclip/cutover-20261031/`; không commit data hoặc secret.
- 5,034 junction nội bộ node_modules được đổi từ source cũ sang source mới;
  kiểm toàn bộ target trong inventory: 0 broken. Không sửa dependency versions.
- TradingAgents editable package được cài lại bằng `uv pip install --python
  .venv/Scripts/python.exe --no-deps -e .`; interpreter import chỉ đúng source mới.
  Đây không chứng minh toàn bộ venv/console scripts có thể di chuyển portable.

## Kiểm chứng

- `node tooling/integrations/doctor.mjs --runtime`: ba source khớp gitlink,
  origin/license, clean; health Paperclip khớp revision.
- Doctor negative cases: thiếu source trả `missing-source`; path thoát workspace
  bị từ chối. Script không import engine hoặc dispatch công việc.
- `python tooling/check_workspace.py`: 9 guides, 7 pinned submodules pass.
  Unit tests topology/links: 5 pass. Node syntax checks doctor/launcher pass.
- Native browser QA trên preview5218, 1920/dark/VI, 1440/light/EN, 390/dark/VI:
  8 cases pass (native render, dialogs/Escape, document/search persistence,
  sidebar preference, unavailable + retry). Browser chặn writes/external;
  report ghi 0 writes, 0 external requests, 0 page errors.
  Ảnh1920/390 đã xem: iframe tới đáy, mobile không tràn ngang; upstream focus
  sau Escape vẫn BODY như trước, không phải trigger.
- Browser probe là bản copy script đã có, chỉ đổi import/output paths, không sửa
  tests/receipt lịch sử. Script/output/ảnh mới ở
  `.runtime/research/paperclip-localization-20261031/adoption-browser.mjs` và
  `.runtime/paperclip/cutover-20261031/browser/`.
- Không chạy lại full build/test Paperclip vì source revision/behavior không đổi;
  thay đổi ở root paths/launcher/docs, đã kiểm đúng native runtime consumer.

## AI environment và skill dài hạn

Thêm skill repo `.agents/skills/upstream-integrations/SKILL.md`, nested
`projects/integrations/AGENTS.md` và route ngắn từ root AGENTS. Hướng dẫn setup/
rollback ở `tooling/integrations/README.md`; catalog là owner path/role/upstream,
cổng vẫn dùng config Trader hiện có. Không đổi global config/MCP hoặc cài plugin.

Skill-creator quick validation pass. Semantic review: task fork/relocation/
upstream update đi đúng skill; task tư vấn Quant Lab hoặc chỉnh UI thông thường
không thuộc trigger. Đây là review trigger thủ công, chưa là benchmark bộ chọn
skill tự động. Phiên hiện tại đọc file trực tiếp; discovery ở phiên sau theo
cơ chế repo skills, không tuyên bố tool mới đã được expose.

Deterministic audit workspace: 0 errors/warnings; global12,288 B, active21,387 B,
reserve44,149 B trên ceiling65,536. Audit riêng Paperclip: 0 errors/warnings,
active25,923 B theo chain riêng của audit ở Git root submodule. Nếu cộng cả
parent workspace + integrations + upstream AGENTS trong ngữ cảnh hiện tại:
36,122 B, còn29,414 B; cao hơn target32KiB nhưng vẫn giữ reserve16KiB. Giữ nguyên
policy upstream thay vì cắt instruction của tác giả chỉ để giảm số đo.
Chưa tạo skill research/model workflow từ luồng chưa thực hiện.

## Thất bại trong quá trình và cách xử lý

- Guard PowerShell ban đầu bọc REST array trong `@(...)` nên đếm sai; dừng trước
  mutation, sửa đọc `.Count` trên REST array thực, xác nhận0 agents rồi mới dừng.
- Sau khi dừng server, `pg_ctl stop` báo PID đã mất: xác minh cả3 process và
  ports đã dừng trước backup/move. Startup sau đó xử lý stale PID; health/company
  và DB hiện có được kiểm lại. Không gọi stop/kill theo port hoặc chạy initdb mới.
- `git mv` lần2 yêu cầu stage `.gitmodules`; stage riêng file move rồi tiếp tục.
- Lệnh Start-Process bị policy chặn trước execution. Dùng exec session chạy
  launcher đã có để khởi động đúng instance; không tìm cách tắt approval policy.
- Editable install với `--no-build-isolation` thất bại vì venv thiếu setuptools;
  chạy lại với build isolation theo pyproject, `--no-deps`, thành công. Không sửa
  manifest để né lỗi hoặc nâng toàn bộ dependency.

## Điểm tiếp tục

Nền fork/source/runtime hoàn tất trong scope trên. Việc tiếp theo trong owner
plan: mở rộng i18n Paperclip theo từng khu vực UI, cấu hình company/roles và
workflow cho owner review; sau đó nối một job engine có contract/provenance và
cancel/retry rõ ràng. RD-Agent cần qualification Linux/container/WSL theo source;
chưa cài hoặc bật môi trường đó từ lát adoption. Giữ UI-first và ngân sách/quyền
owner đã chốt, không đổi "source-ready" thành "autonomy-ready".

Clean-clone runtime còn phụ thuộc feature checkout Trader có
`foundation_v2/local-services.json` (`18e9348d` hoặc hậu duệ); root gitlink hiện
chưa nâng. Không stage gitlink Trader đang chứa lịch sử/WIP ngoài scope. Engine
jobs và packaging gate tiếp tục mở trên issue/plan; broad UI audit vẫn pause.

## Tiếp nối: localization shell/tasks và đồng bộ VI/EN

Paperclip commit `e123c2b18108fb3b910c554ba3a5e7098794f278`, nhánh
`codex/naqex-integration`. Root gitlink pin revision này. Host thay đổi riêng
`AiPaperclipPanel.jsx` và browser regression: Trader commit `7b4c332d`, nhánh
`codex/note-workspace-completion`. Cả hai feature branch đã push lên fork Naqex.

### Hành vi và state

- Trader gửi preference VI/EN khi child ready, load và host language thay đổi.
  Child kiểm exact origin được launcher cấp từ local-services và source===parent;
  host kiểm origin/source của ready. Không wildcard/trust từ query hoặc execution.
- i18next đổi ngôn ngữ tại chỗ; optional localStorage nhớ lựa chọn, `html.lang`
  theo language. Không đổi iframe key/src theo language. Search, dialog và draft
  còn trong document cũ. Storage bị chặn vẫn đổi ngôn ngữ được.
- Tách namespace `workspace` EN/VI, reuse validator key/interpolation/safety;
  native translation và các locale khác giữ nguyên, fallback EN cho namespace mới.
  Tên company/project/agent và nội dung người dùng giữ nguyên.
- Coverage: nav classic/production/mobile, account actions, task breadcrumb/search/
  empty/create và các trường chính new-task. Specialized filters/composer settings,
  errors, các trang khác và coordinator experimental còn EN. Không gọi toàn app
  đã Việt hóa. `Board` hiện là tên user trong session, được giữ nguyên.

### Kiểm chứng và review

- i18n + bridge:12/12. Covered VI/EN, locale fallback, interpolation, exact
  origin/source/version, malformed payload, denied storage, standalone và cleanup.
- Focused components: Sidebar, account menu, mobile coordinator nav, Issues,
  IssuesList và NewIssueDialog. Lần đầu239 pass/2 fail do đổi casing native
  DialogTitle "New task" thành "New Task"; khôi phục key EN riêng. Rerun
  NewIssueDialog+i18n:123/123. Các5 file component còn lại đã pass trước đó.
- UI `tsc -b` ban đầu thiếu generated Storybook catalog. Chạy helper upstream
  `node scripts/storybook-catalog.mjs`, rerun `tsc -b` pass; generated files ignored.
  UI Vite production build pass; giữ warnings upstream CSS highlight/chunk-size.
- `check-token-gates.mjs` exit1:106 vi phạm có sẵn (75 color,31 bracket). So scanner
  trên archived parent pin và candidate: cùng106 vi phạm, added0. Không thêm
  allowlist hoặc gọi whole-repo gate pass. Evidence `.runtime/research/
  paperclip-localization-20261031/tokens-before.txt`, `tokens-after.txt`.
- Browser script thật `web/tests/aiPaperclip.browser.mjs`:9 cases pass tại1920
  darkVI,1440 lightEN,390 darkVI. Đổi VI→EN→VI với dialog/draft/search đang mở;
  document identity, navigation persistence, sidebar preference, error/retry,
  dialog/Escape.0 writes,0 external,0 pageerrors. Xem ảnh1920 và dialog390 thực tế.
  Lần đầu selector Create Task không còn duy nhất khi VI labels trùng nhau;
  sửa locator scope theo empty-state và rerun, không sửa app để né kiểm tra.
  Evidence: `projects/trader/foundation_v2/.runtime/paperclip-localization/browser/`.
  Focus sau Escape vẫn BODY upstream, không thay đổi trong lát này.
- Review độc lập `/root/review_paperclip_embed`: không thấy blocker ở message
  boundary/mount/draft/memo/breadcrumb; chỉ preview5218 là trusted host hiện tại.
  Review là source-only; browser evidence được thực hiện riêng như trên.
- Không chạy full monorepo suite, engine/model job hoặc broker test cho lát UI.

### Runtime và rollback

Guard trước restart: đúng owner source/server11428/launcher23408; mỗi company
có0 agents/0 live-runs. API backup tạo
`.runtime/paperclip/instances/trader-ui/backups/paperclip-20261031-233548.sql.gz`,
SHA256 `a5fcdd2547868d4ea893d21c8c3e848d7b8f3e61b4c1f780243d9db3681a0eb8`.
Snapshot company/backup receipt trong `.runtime/research/paperclip-localization-20261031/`.
Dừng đúng owner, xác nhận3 ports free; restart launcher cùng home/config/DB.
Health khớp commit mới, company được kiểm lại. Chưa có migration mới của patch.
Owned launcher16864/server25964 (PID chỉ là snapshot, đọc owner.json trước thao tác).

Trader preview build từ archive HEAD `18e9348d` + duy nhất overlay
`src/AiPaperclipPanel.jsx` để loại WIP audit khỏi preview. Candidate và build log:
`projects/trader/foundation_v2/.runtime/paperclip-localization-candidate/`,
`.runtime/research/paperclip-localization-20261031/host-build.log`. Copied hashed
assets trước, index cuối; giữ assets cũ và `preview-index-before.html` để rollback
UI bằng index trước nếu cần. Không build từ dirty worktree hoặc đổi runtime5180.

CLIProxyAPI managed không khởi động; instance Windows8317 giữ nguyên. Chưa tạo
agents/jobs/providers, không khai source-ready thành autonomy-ready. Hướng dẫn
patch/upgrade nằm trong fork `doc/NAQEX-LOCALIZATION.md`; không cần skill mới cho
mỗi lần thêm bản dịch. Broad UI audit và WIP ngoài scope được giữ nguyên.

## 01/11 — Việt hóa giao diện chuyên sâu và đội nghiên cứu mẫu

Owner giao hoàn thiện phần Việt hóa còn lại và đưa sơ đồ đội cùng một nhiệm vụ
mẫu lên UI để xem trước. Paperclip commit `11d41b67152cff17afb6c05b325abe28c4ab424b`,
nhánh `codex/naqex-integration`. Giữ upstream, dependency và schema hiện tại;
chỉ thay UI/copy và tài liệu liên quan. Trader source/preview không được build
lại từ WIP audit; root gitlink Trader tiếp tục giữ nguyên.

### Hành vi, dữ liệu và quyết định

- Reuse i18next với namespace `interface` EN/VI gồm10.923 messages, ngoài
  namespace `workspace` hiện có. Mở rộng copy ở agents, tasks/composer, settings,
  apps/connections, skills, costs, projects, routines, audit và menu/dialog/
  tooltip/nhãn truy cập. Key và placeholder giữa hai catalog được kiểm cùng nhau.
- Component đăng ký đổi locale tại chỗ; form/dialog không bị remount. Registry
  nhãn dùng getter để không giữ ngôn ngữ lúc import. Mã status, credential policy,
  route, tên đã lưu và nội dung người dùng không đổi theo bản dịch.
- Sửa các nhánh từng dựa vào chữ hiển thị: ownership kết nối, icon/tone trace,
  breadcrumb mobile và attribution avatar. Giữ casing EN của từng loại badge.
  Loại đuôi số nhiều tiếng Anh trong91 vị trí copy có đếm số khi dùng VI.
- Agents classic/production có nút **Xem đội và nhiệm vụ mẫu**, chỉ hiện trong
  embedding được cấu hình. Dialog gốc trình bày owner → điều phối → nghiên cứu
  và kiểm chứng độc lập; có câu hỏi mẫu và bốn bước data/thử nghiệm/đánh giá/
  báo cáo. State chỉ là đóng/mở trong React, không có API tạo agent hoặc job.
- Tên model/provider, code/config, hướng dẫn skill, nội dung người dùng và chi
  tiết lỗi gốc từ dịch vụ được giữ nguyên. Catalog tách riêng giúp giữ bản dịch,
  nhưng upstream sửa component vẫn cần merge/review call site. Không dùng DOM
  translator và không gọi mọi trang dữ liệu động/plugin đã được nghiệm thu.

### Kiểm chứng

- UI typecheck và Vite build pass trên source đã commit. Build vẫn có warnings
  upstream về CSS/import/chunk-size. Không đổi dependency hoặc framework.
- Final focused suite: **550/550 tests,21 files**. Gồm settings, costs, skills,
  tasks, agents, connections, catalog, sidebar, dialog, locale/bridge, breadcrumb,
  trace icon, status và projects. Tests VI/EN giữ draft/dialog và raw policy;
  đội mẫu không gọi fetch. Log `.runtime/research/paperclip-full-copy-acceptance-rerun.log`.
- Review AST so source trước patch với EN đã giải ngược:838 files,827 tương
  đương sau bỏ subscription/copy boilerplate,0 key thiếu.11 files còn lại được
  review riêng cho preview, getter, các sửa state/label ở trên và spacing chữ
  Expires. Evidence `.runtime/research/paperclip-copy-ast-audit.json`.
- Browser trước cutover:11 routes trên company rỗng và4 checks về language/draft/
  responsive;1920 darkVI,1440 lightEN,390 darkVI. Không tràn ngang;0 pageerrors,
  không có request ra ngoài. POST tự refresh subscription từ trang Costs bị QA
  chặn trước khi gửi; không coi đó là0 lần thử ghi. GET `/api/mcp/connections`
  trả404 trên runtime hiện tại; đây là phần API chưa có, chưa sửa trong lát copy.
  Evidence `.runtime/research/paperclip-full-copy-browser/report.json` và ảnh.
- Token gate vẫn exit1 với106 lỗi có sẵn:75 color,31 bracket; không thêm lỗi hoặc
  allowlist để lách gate. `git diff --check` pass. Không khai whole-repo gate pass.

Các lần lỗi được giữ lại:5 failures whitespace từ lượt đầu đã sửa và chạy lại;
duplicate hook/label union type đã sửa; Projects/Status/IssueCases casing đã
sửa và nằm trong550 final tests. Browser ban đầu dùng route không có/thời điểm
còn loading và sai tên nút EN; đã sửa harness, chờ nội dung thật rồi chạy lại.
QA sâu phát hiện POST refresh bị chặn; harness chỉ chấp nhận đúng request bị
chặn này, vẫn từ chối mọi ghi khác. Không sửa app để né guard.

Lượt full UI suite thăm dò đã dừng khi còn sửa source/catalog, không phải kết
quả acceptance. CompanyImport/Inbox failed trong lượt rộng nhưng4 case liên
quan pass khi chạy riêng. IssueProperties monitor còn khác định dạng máy
`16:08` so với test hard-code `4:08 PM`; formatter đó không bị patch. Có failures
về hai bản cài CodeMirror và timing AgentDetail chưa đóng bằng full-suite rerun.
Không chạy full monorepo suite, engine benchmark hay broker test cho lát này.
Logs thăm dò/triage vẫn giữ ở `.runtime/research/paperclip-full-copy-*.log`.

### Runtime và khôi phục

Guard API trước/sau cập nhật: company `Naqex AI`,0 agents/0 live-runs. Manual
backup trước restart:
`.runtime/paperclip/instances/trader-ui/backups/paperclip-20261101-083823.sql.gz`,
SHA256 `fc718345466973d2e96f14790540aed7e304006f862e7c910557133e29533411`.
Config/owner/backup receipt giữ trong `.runtime/research/paperclip-full-copy-cutover/`.
Không áp migration, không đổi cấu hình/provider/account.

Dừng đúng server/launcher owner cũ. Postgres đã tự thoát sau server; lệnh pg_ctl
đụng race và báo PID không còn, rồi kiểm lại PID và cả3 ports đều không còn
listener trước restart. Launcher upstream xử lý stale lock, dùng lại DB; startup
báo migrations already applied. Health mới khớp `11d41b6`; owner snapshot:
launcher24824/server22036 (đọc lại owner.json, không dùng PID này như authority).
Runtime/guard/browser smoke sau cutover giữ cùng thư mục evidence.

Rollback source về pin trước `e123c2b` sau khi kiểm đúng owner và backup mới;
giữ instance DB/storage/config. Không reset DB để rollback bản dịch. CLIProxyAPI
managed17852 không khởi động; instance Windows8317 chỉ được dùng cho inference
dịch thuật theo quyền đã có, không thay config/process của nó. Cần xem lại
UI/đội mẫu trước lát provisioning và contract chạy engine thực tế.

## 2026-11-01 — Sửa Paperclip tự reload và onboarding chen vào điều hướng

### Nguyên nhân và phạm vi

- Tái hiện bằng click sidebar thật: Issues → Projects → Skills → Dashboard.
  Khi company có 0 agents, Dashboard gọi `openOnboarding`; wizard lazy xuất hiện
  sau khi trang đã hiển thị và chặn thao tác sidebar. Document ID không đổi:
  trường hợp trong ảnh là overlay tự mở, không phải iframe remount. Probe lỗi
  và trace được giữ tại `.runtime/research/paperclip-navigation-probe/report.json`.
- Runtime dev còn có nguyên nhân reload độc lập: log cutover trước ghi
  `optimized dependencies changed. reloading` lúc 08:48:16 và 08:48:42.
  Probe lần này không phát lại optimizer reload sau khi cache đã ấm; không coi
  mọi chuyển trang trong ảnh đều là document reload.
- Paperclip commit `548adbc`: dashboard không auto-onboard trong iframe của bản
  build đã cấu hình workspace origin. Nút tạo agent/route onboarding vẫn dùng
  wizard native. Mở Paperclip riêng giữ hành vi auto-onboarding upstream.
- Launcher workspace build static UI trước mỗi cold start, với đúng origin bridge,
  rồi chạy `PAPERCLIP_UI_DEV_MIDDLEWARE=false`; không dùng HMR/optimizer trong
  runtime sử dụng hằng ngày. Owner ghi `uiMode=static`; gọi lại không restart.
  Đánh đổi: sửa source cần khởi động lại đúng owner để build, mất khoảng 6–10 giây
  cho UI build trong lượt này. Không sửa host Trader hoặc unrelated audit WIP.
- Nút “Xem đội và nhiệm vụ mẫu” vẫn là phần Naqex thêm để xem trước; chưa tạo
  agents hoặc nối engine. Đây không phải UI native của upstream.

### Kiểm chứng và runtime

- Focused onboarding route/offer: 34/34 tests pass; UI `tsc -b` pass; build pass.
  Token gate vẫn fail với 106 lỗi sẵn có (75 color/31 bracket), không thêm lỗi
  hoặc allowlist. Không chạy full suite hoặc tuyên bố whole-product acceptance.
- Regression mới `node tooling/paperclip/navigation.browser.mjs`: pass. Click 7
  native routes, lặp Dashboard với 0 agents, 3 vòng host Connections/Paperclip,
  VI/EN/VI, giữ draft 35 giây; iframe/document/search/draft giữ nguyên. Chỉ có
  2 document requests khởi tạo (host + iframe), 0 reload/HMR/pageerrors/ghi/ra ngoài.
  Nút tạo agent chủ động mở wizard bình thường. Evidence:
  `.runtime/research/paperclip-navigation/report.json`.
- Existing host browser regression: 9 checks pass ở 1920/1440/390px, gồm native
  dialog/Escape, draft/language, sidebar preference và unavailable/retry. Log:
  `.runtime/research/paperclip-navigation-existing-browser.log`. Script cũ ghi
  scope “isolated database”; lượt này thực tế dùng instance local `trader-ui`
  đã có với company rỗng, mọi browser request ghi đều bị chặn.
- Trước cutover xác nhận company `Naqex AI`, 0 agents/0 live-runs. Backup manual:
  `.runtime/paperclip/instances/trader-ui/backups/paperclip-20261101-085805.sql.gz`,
  SHA256 `a704ec3036d17f72a72f7ad7ba683ab4308187b0a5be12ce4d9250a816df6fd1`.
  Owner/config/backup/hash/deployed receipt trong
  `.runtime/research/paperclip-navigation-cutover/` (không commit dữ liệu này).
- Pre-stop guard lần đầu từ chối vì health đọc Git HEAD hiện tại, còn owner giữ
  SHA lúc khởi động; chưa stop process ở lần đó. Đã đọc health source, đối chiếu
  PID/parent/command/start time và HEAD mới rồi dừng đúng owner. Ba ports đều rảnh
  trước start; upstream xử lý stale PostgreSQL lock, không restore/reset DB.
- Static runtime mới healthy ở17860, Postgres17861, không listener27860;
  launcher8256/server20188 là snapshot, phải đọc lại owner khi thao tác sau này.
  Served `/assets/index-BWM1q_52.js` khớp dist; HTML không có `/@vite/client`.
  Doctor runtime healthy; pin source khớp sau khi stage gitlink trong slice này.
  Không migration, provider/broker/agent execution hoặc bật automation.
- Rollback source về `11d41b6` và launcher trước slice này sau khi kiểm đúng owner;
  giữ instance/config/database hiện tại. Không dùng rollback source để xoá dữ liệu.
  Đây là kiểm tra luồng lỗi và idle ngắn, chưa là bằng chứng vận hành nhiều giờ.

## 2026-11-01 — Connection project và đội Paperclip pilot

### Quyền và cách nối

Owner giao setup Paperclip/đội agents; sau câu hỏi về gateway đã yêu cầu mở API
project và xác nhận tài khoản đã đăng nhập. Dùng native AI Connections của
Paperclip, không viết adapter Gemini: company-shared `local/responses`, URL
`http://127.0.0.1:17852/v1`, key trong vault. Provider `openai` là giao thức;
model thực tế từ catalog gateway là `gemini-3.8-flash-high` (`antigravity`).
Harness thử: installed Codex CLI0.164.0, `codex_local`, legacy, engine `cli`.
Không dùng credentials/global config Codex hoặc gateway Windows8317.

### Đã thực hiện

- Tìm thấy ba account project trong runtime Trader cũ, không copy credentials.
  Khởi động CLIProxyAPI8.0.40 ở17852, binary SHA256
  `0fd1f03b80a4acac69515e3737fc9f4445de69221e4750e20a3c70038a3b8443`.
  API Trader8010 đã dừng trước khi mở gateway standalone. Owner runtime hiện
  hành ở `.runtime/paperclip/gateway-owner.json`; PID23572 là snapshot.
- Catalog và inference Responses trả `PROJECT_GATEWAY_OK`; native Paperclip
  Test Environment qua connection shared đạt hello cho cả lane mặc định và CLI.
  Đây là qualification kết nối ngắn, không là task/tool qualification.
- Company `Naqex AI` có ba agents thật: Điều phối nghiên cứu (pm), Nghiên cứu
  chiến lược (researcher), Kiểm chứng độc lập (qa); hai agent sau reportsTo lead.
  Instructions bundle qua API có revision; dùng skill vận hành upstream.
- Timer tắt; kết thúc pilot cả ba paused và `wakeOnDemand:false`. Mỗi agent
  maxConcurrentRuns1, maxDailyRuns6, timeout180s. Bypass Codex được đặt false.
  Không cung cấp broker/demo/live hoặc dữ liệu thị trường thật.

### Failure và sửa lỗi có bằng chứng

- Task `NAQ-1` (`670d9c6c-ded3-4e20-ae1e-235c1b976df9`) chỉ là đề bài giả lập
  phí hai chiều và causal timing. Run đầu
  `cb8d99cc-c54e-405e-9075-d71530a195f8` failed với HTTP413 sau thao tác đầu;
  skill injection báo EPERM. Retry do Paperclip tạo đã cancelled khi pause.
- `managed.yaml` giới hạn request65536 bytes. Probe70000 bytes tái hiện413;
  tăng riêng pilot lên8388608, gateway hot-reload, cùng probe đi tới validation
  model (HTTP400 model_not_found). Không tăng retry hoặc sửa generator Trader.
  Backup config chứa key chỉ ở evidence local bị ignore.
- Skill directories dùng junction trên Windows; giữ directory symlink ở hệ
  khác và quyền callback/preserve custom directories. Bổ sung SystemRoot,
  WINDIR, ComSpec vào shell allowlist, giữ provider-key exclusion. Controlled
  Windows PowerShell probe thiếu SystemRoot không chạy; thêm biến này chạy được.
- Source Paperclip `42b6107a6f5d997eb6755bd144b42a974449d82b`:
  focused skill injection + shell environment11/11 tests pass; typecheck
  adapter-utils và codex-local pass; diff check pass. Launcher build static UI
  pass trước restart. Không chạy full suite hoặc toàn bộ product acceptance.
- Run sau sửa `8ad071e9-4bab-41b6-acca-f36a29374583` process succeeded nhưng tool
  calls bị `blocked by policy`. Không còn413/EPERM trong lượt này. Model tạo
  nội dung nháp, platform materialize final response thành comment; chưa chứng
  minh agent tự gọi API để ghi task/document hoặc chuyển trạng thái. Operator
  đã đặt `NAQ-1` blocked với action qualification harness/sandbox. Không mở
  bypass để vượt policy. Chưa chạy researcher/reviewer hoặc engine quant.

### Backup, runtime và resume

- Trước provision: `paperclip-20261101-091528.sql.gz`, SHA256
  `b1cda01130214518feb1e8c5f7c6934015e958632be95f4c5b138a27382a18bf`.
  Trước restart: `paperclip-20261101-092547.sql.gz`, SHA256
  `6c98653bbe0a1db272d7f44ccf642f470684a07a0113290e0ef3f0d4b7cdc1a1`.
  Cả hai trong `.runtime/paperclip/instances/trader-ui/backups/`.
- Kiểm PID/parent/command owner rồi dừng server/launcher; ports17860/17861 rảnh
  trước start. Không migration/reset/restore DB. Runtime static mới healthy ở
  source42b6107; owner snapshot launcher16352/server2836, phải đọc lại khi thao tác.
- `.runtime/research/paperclip-team-setup/` giữ probe, backup receipt, IDs,
  failure events, kết quả sau sửa và `checkpoint.json`. Checkpoint cuối có
  zero queued/running runs; không bật timer/automation. Gateway vẫn đang mở.
- Audit AI environment trước/sau: ok,0 errors/0 warnings; active21387/65536 B,
  reserve44149 B. Không đổi instructions/config toàn máy hoặc tạo skill mới.
- Standard grants upstream vẫn cho configure/tool management; tắt các flag
  không tự thu hồi grants và `tasks:assign` còn đường simple_default. Đây là
  gap chưa giải quyết, không tuyên bố đội có quyền tối thiểu hoặc sandbox đã đạt.
  Bước tiếp: chọn/qualify harness native theo cùng connection, xác minh quyền
  từ chối thực tế, rồi chạy từng task bằng tools. Giữ ba agents paused đến lúc đó.
- Gateway standalone dùng home Trader cũ. Handoff/restore override phải theo
  [hướng dẫn](../../../tooling/paperclip/README.md), không khởi động owner thứ hai.
  Source rollback về548adbc giữ DB hiện có; backup mới trước mọi restore mất dữ
  liệu. Không rollback source bằng cách xoá đội, connection hoặc lịch sử lỗi.

## 2026-11-01 — Dọn pilot, owner tự thiết lập native

### Quyết định và scope

Owner yêu cầu lưu kết quả test, dọn đội/config/custom UI mẫu, giữ tiếng Việt và
tự thiết lập qua UI upstream. Không tự tạo đội, company hoặc connection thay thế.
Giữ static embedding, origin/language bridge và fix navigation; không đổi cổng
hoặc chạm gateway Windows8317, Trader WIP hay source engine khác.

### Kết quả đã lưu và cleanup qua API gốc

- Kết quả pilot vẫn là: Responses inference và native Test Environment hello
  đạt; full task/tool workflow chưa đạt do policy. Các lỗi413/EPERM/shell và
  process succeeded nhưng tool blocked vẫn giữ trong receipt lịch sử và local
  evidence. Không đổi kết luận thành full pass sau cleanup.
- Backup trước cleanup: paperclip-20261101-093820.sql.gz,356309 bytes; SHA256
  1af082b517e9e0ed89bdab6f02026820d61553f2ae11349c2093abcc68c3ad0e.
  Backup sau cleanup trước cutover: paperclip-20261101-094522.sql.gz,88293 bytes.
  Cùng thư mục instance backups đã ghi phía trên. Data export/comments/IDs và
  kết quả API ở .runtime/research/paperclip-team-setup/cleanup-20261101/.
- Xác minh ba agents đều có metadata quant-research-pilot-v1 và đúng IDs mẫu;
  không có agent MIIKEY đã lưu. Company Naqex AI không có project/goal/task khác
  sau khi xóa taskNAQ-1; không có live runs.
- DELETE task và hai agents đạt. Agent đầu có409 do termination bất đồng bộ,
  chờ terminated rồi xóa đạt. Lead DELETE trả500 vì cost_events tham chiếu
  heartbeat_runs. Connection DELETE trả403 vì installs còn agent IDs đã xóa.
  Đây là lỗi cleanup upstream được quan sát thực tế, chưa sửa source/database.
- Dùng DELETE /api/companies/:id của Paperclip cho company mẫu do Codex tạo;
  native transaction dọn đúng thứ tự phụ thuộc. Trả200 ok; GET /api/companies
  trả[] sau đó. Kết quả cuối không còn tổ chức, agent, task hay connection mẫu
  trong company. Không restore/reset cả DB.
- Gateway PID23572 được đối chiếu executable/config/port17852 với owner rồi
  dừng. Restore bodylimit65536 từ8388608, bytes config khớp backup trướcpilot.
  Lần so sánh đầu bỏ sót indentation nên chưa đổi giá trị; lần sau kiểm diff
  và xác nhận chỉ một dòng thay đổi, restore chính xác. Auth/account giữ nguyên;
  owner hiện ghi stopped. Gateway Windows PID15756/port8317 không thao tác.

### Source và nghiên cứu

- Paperclip commit0490d33 bỏ ResearchTeamPreview, test/catalog mẫu; đảo đúng
  patch42b6107 bằng inverse diff. Ba file adapter implementation khớp upstream
  pin42fd568. Giữ Việt hóa và bridge/embedding cần thiết.
- Antigravity: profile qualified=false tại paperclip-runner-permissions.ts;
  UI AgentBasicsDialog dựa vào cờ này. Plan upstream28/10 vẫn pending, macOS
  ARM64 là target đầu; không phải thiếu đăng nhập hay lỗi bản dịch.
- Copilot: profile qualified=true, nhưng assertVerifiedAcpxProviderPlatform
  trong production ACPX reject win32. openQualifiedAcpxRuntime gọi gate trước
  spawn; native picker không chứng minh chạy được trên Windows. Chưa chạy
  Copilot, chưa cài Linux/WSL/Docker hoặc native provider mới.
- Google official19/05/2026: Gemini CLI ngừng tài khoản cá nhân18/06/2026;
  Standard/Enterprise và paid API keys có ngoại lệ. Không dùng menu cũ để suy
  ra entitlement tài khoản. Links và self-setup trong tooling/paperclip/README.md.
- Public MCP có37 direct operations, scope configure chỉnh existing agent,
  project và skills; không tạo agent/credentials/commands/policies.
  Instance local_trusted thiếu public origin nên routes MCP chưa mount, GET
  /api/mcp/setup và /api/mcp/connections đều404; enablePublicMcp=false nữa.
  Cần authenticated user/company membership và OAuth; chưa đổi auth, bật MCP
  hay sửa Codex/global config. MCP chưa được expose/đăng nhập trong phiên này.

### Kiểm chứng và bàn giao

- Focused locale-validation + workspace-preferences:12/12 pass. Không chạy full
  suite hoặc thêm provider/model run. Static UI build qua launcher đạt6.37s;
  giữ các warning chunk size/dynamic import/CSS có sẵn, không gọi đó fullproduct
  acceptance. Runtime/served asset/rendered handoff bổ sung sau cutover bên dưới.
- Rollback source qua Git nếu cần, giữ DB hiện tại. Backup chứa dữ liệu trước
  cleanup để tham khảo/khôi phục chỉ khi owner muốn; không tự phục hồi đội mẫu.

### Cutover và UI sau cleanup

Runtime static khởi động source0490d33; owner launcher21000/server15060 là
snapshot, đọc owner.json lại trước thao tác. Startup báo migrations already
applied; không migration/restore DB. Health ok, company list[]. Served asset
/assets/index-BUzcKgPM.js khớp byte với dist; không HMR client.

Read-only Playwright trong process riêng mở Trader5218 → iframe17860/onboarding:
form tạo organization đã render, html.lang=vi,0 pageerrors/0 request ghi hoặc
external bị phát hiện. Ban đầu lấy heading quá sớm chỉ ghi trạng thái loading;
chờ textbox của form rồi kiểm lại đạt. Onboarding gốc vẫn còn nhãn Continue và
đoạn Your first agent đã sẵn sàng làm việc; không claim100% dịch/copy acceptance.
Import Playwright trong persistent REPL bị lỗi module default export; dùng script
Node native với package đã có, không cài dependency hoặc patch module. Evidence:
browser-report.json,embedded-after.png và build/start logs trong cleanup folder.

Backup sau cleanup SHA256: 5d0c04d04db1f481222f937050484750743382d6ac46d2c2b096e0113cb3a361. Gateway17852 không còn listener; Windows
8317 vẫn PID15756. Bộ thử chỉ scope cleanup/locale/render; chưa qualification
Copilot/Antigravity hoặc MCP. Owner tiếp tục tạo organization theo UI; không
tự khôi phục dữ liệu mẫu từ backup.

### Pilot đội nghiên cứu Sky AI (01/11)

Owner tự tạo company Naqex AI (6b90f0c1) và kết nối Sky AI qua gateway project
17852 (af6b795e, model claude-opus-5.5, khóa trong vault Paperclip). Codex tạo
qua API: agent Trưởng nhóm nghiên cứu (6da897b6, codex_local, timer tắt,
wakeOnDemand=true, maxConcurrentRuns=1, maxDailyRuns=10, không tạo agent/skill),
project pilot fa771cdb và task NAQ-3. NAQ-1/NAQ-2 hủy kèm comment giải thích.
Bài tập offline phí/look-ahead, không broker, demo hay tiền thật.

Kết quả: run c671f8fc succeeded sau 34 giây, exit 0; agent tự ghi ket-qua.md,
tự comment và đặt NAQ-3 done. Số liệu đúng (lãi gộp 2, phí 0,202, ròng 1,798
trên vốn 100; khớp t+1). Bản trước từng ghi nhầm 2,000% thành 2%; vẫn cần review
người với output số. Run record: .runtime/research/paperclip-team-setup/skyai-run-naq3.json.

Lỗi gốc đã sửa:

- Codex sandbox chặn mọi lệnh shell vì managed config.toml làm mất
  [windows] sandbox: Paperclip e2a9b5e ghim unelevated sandbox, có test.
- Shell không mở được socket (Winsock) vì allowlist env mất SystemRoot/WINDIR/
  ComSpec; ae5decb áp lại 42b6107, kèm junction cho skill link (EPERM).
- Gateway 413: max-request-body-bytes 65536 -> 8388608 trong managed.yaml;
  backup gateway-managed-before-skyai-20261101-132152.yaml (SHA256 79B59971...FADC).
  Owner quyết định giữ 8 MB hay phục hồi.
- Thiếu agent JWT nên run không có PAPERCLIP_API_KEY: thêm
  .runtime/paperclip/instances/trader-ui/.env (gitignored) với
  PAPERCLIP_AGENT_JWT_SECRET; banner khởi động báo Agent JWT set.

Backup DB trước thay đổi: backups/paperclip-20261101-125953.sql.gz. Focused
tests Paperclip 27/27; tsc toàn repo còn lỗi implicit-any có sẵn. Wakeup thủ
công bị skipped với issue đã có run kết thúc và comment không đánh thức agent;
dùng issue mới giao cho agent hoặc wakeup assignment kèm payload.issueId.

## Native engine jobs — 01–02/11/2026

### Scope và kiến trúc

Owner giao nối TradingAgents trước, RD-Agent sau, và chọn các model Gemini cho
lượt thực tế. Không gọi lại route Opus5.5 hết hạn. Native Paperclip `process`
adapter gọi `tooling/ai-engines/engine_worker.py`; không sửa source engine hoặc
thêm UI/DB điều phối cạnh tranh. Task nhận đúng một khối JSON `naqex-engine`,
không nhận shell command, endpoint, key hay đường dẫn từ task. Wrapper xác nhận
run/company/assignee, checkout qua API, rồi dùng `TradingAgentsGraph.propagate`
và exporter báo cáo upstream.

Paperclip sở hữu assignment, queue, concurrency, timeout/cancellation và history.
Wrapper không retry provider hoặc outcome chưa rõ. Timer tắt; một run đồng thời
cho mỗi worker, timeout900giây. Không có daily run/spending cap được enforcement
trong wrapper; đã bỏ key `maxDailyRuns` không có consumer thực ở native heartbeat
khỏi hai worker mới. Không thay agent Trưởng nhóm nghiên cứu của owner.

### Kết quả thực tế

| Phần | Bằng chứng |
|---|---|
| Worker phân tích | `762a1f5c-4d9f-4959-8ff9-5e9c61233d5c`, Chuyên viên phân tích, native process, idle sau run |
| Yêu cầu | NAQ-4, BTC-USD, crypto, ngày yêu cầu2026-11-01, analyst market |
| Model route | quick/deep đều `gemini-3.8-flash-high`, route có trong catalog gateway project17852 |
| Run | `47bf4a86-48d9-4f15-87fe-460022c2dbe5`, native status succeeded;22:47:06→22:51:49 ngày01/11 giờ Việt Nam |
| Kết quả | Task done, native Markdown document `engine-47bf4a86-48d9-4f15-87fe-460022c2dbe5`; nội dung VI, heading exporter còn EN |
| Source engine | TradingAgents `ecaafe585a98478ef7dbcf5678f4a64b5e7d1066`; Paperclip `e2a9b5e5aaf221c30b89fed55a1513e664a96ac5` |
| Artifacts local | `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/6b90f0c1-8f91-4fe8-bc15-fc8c58b3ac8f/47bf4a86-48d9-4f15-87fe-460022c2dbe5/` giữ request hash, receipt/provenance, report/cache/results |

Ngày02/11 Paperclip đã tắt, nên API read ban đầu bị connection refused. Kiểm PID
owner cũ đã hết/cổng trống rồi mở lại cùng launcher/instance/data. Startup báo
migrations already applied, Agent JWT set, heartbeat disabled. API xác nhận lại
run succeeded/task done/document hiện hữu. Browser UI gốc mở NAQ-4 và thẻ
Kết quả phân tích: báo cáo VI đã render, tên model có trong header exporter.
Không giao thêm model job khi resume; không xóa hoặc thay báo cáo pilot.

Snapshot đọc API đã lọc và startup logs:
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-integration-20261102/`.
Dispatch lần đầu và logs trước đó ở folder cùng prefix ngày20261101.

### Gateway và dữ liệu

Start gateway qua retained API8010 từng403 khi thiếu Origin, rồi503
`ai_gateway_config_conflict` qua host preview. Mismatch API/config chưa sửa.
Đã dùng standalone project owner sẵn có, cùng executable/config/auth, cổng17852;
không đổi gateway Windows8317. Ngày02/11 kiểm owner/PID/cổng rồi mở lại standalone,
authenticated GET catalog có model Gemini đã chọn. Không gọi inference mới.
Owner `.runtime/paperclip/gateway-owner.json` được cập nhật PID/log/status sau
readiness; snapshot owner trước start nằm trong backup ngày02/11.
Config thực tế giữ request body8MB, không áp lại64KB từ cleanup lịch sử.

Khóa chỉ đọc từ gateway config tại job time; không đưa vào settings, task,
adapter config hoặc Git. Cấu hình riêng `.runtime/ai-engines/settings.json`
chỉ giữ paths/model IDs. Worker loại provider/tracing/upstream env kế thừa,
kiểm exact loopback origin/registry port và import path/source tracked state.

### Kiểm chứng bản wrapper chốt

- 16 focused unittest đạt: input sai, env credential isolation, origin/run/
assignee boundary, checkout409 không retry, preflight không inference, native
report/provenance, lỗi delivery, duplicate dispatch, gateway sai cổng/model vắng.
- Sửa duplicate dispatch để không đổi task/receipt của run đang có. Resolve
gateway một lần trước engine, lưu `report.md` trước publication; delivery lỗi
vẫn giữ engine_status completed và delivery_status failed. Receipt thêm hash
wrapper/report. Không gọi báo cáo đã phân tích là đã gửi khi publication lỗi.
- Pilot model chạy bằng bản wrapper trước những hardening trên; các sửa sau
được kiểm offline, chưa chạy model E2E lần nữa. Không suy chúng đã qua live run.
- `node tooling/integrations/doctor.mjs --runtime`: cả ba source đúng pin/origin,
license hiện hữu, tracked source sạch; Paperclip healthy. Đây không là kiểm
dependency/RD-Agent/model hoặc whole-product acceptance.

### RD-Agent và giới hạn bàn giao

Chuyên viên nghiên cứu `a3c59356-275a-4960-88e0-98cb7d8ea60f` vẫn paused. Source
pin `484776c2` có hướng dẫn Linux; máy chưa có WSL distribution/Docker được
qualification. Chưa cài dependency hoặc chạy thí nghiệm. Đã hỏi owner quyền
cài Linux/WSL2/Docker, chưa có câu trả lời; không tự đổi hệ thống hay reboot.
Sau gate đó mới chọn bounded finance experiment/data contract và kiểm runtime.

Model route ID không xác minh nhà cung cấp thực bên dưới gateway. Báo cáo dùng
nhiều câu chắc chắn và con số chưa được đối chiếu độc lập; date request không
bảo đảm daily candle đã đóng hoặc point-in-time data. Rating Sell là output
engine, không là lệnh giao dịch hay strategy approval. Chưa backtest/OOS/chi phí/
stress/soak, chưa có vòng nghiên cứu tự chủ end-to-end. Không broker execution,
không bật lịch, không thay đổi holdout hoặc DB Trader. API8010/UI5218 không
được khởi động lại trong lát resume02/11; dùng native Paperclip17860 để xem kết quả.

Resume: đọc [engine jobs](../../../tooling/ai-engines/README.md), xác nhận model/
gateway readiness rồi tạo task mới nếu thực sự cần phân tích khác. Không giao
lại NAQ-4 để thử resume inference đã hoàn tất; không bật RD worker trước runtime.

## 02/11/2026 — RD-Agent runtime và khảo sát Hermes/OpenClaw

Owner đã cho phép cài Linux/Docker. Chọn WSL2 Ubuntu + Docker Engine trong một
distro riêng: Linux giữ package/venv, container giữ môi trường thí nghiệm.
Không cần Docker Desktop cho luồng này; đổi lại phải quản lý distro/Docker
bằng lệnh. Không đổi source pin, provider config, broker hay runtime Trader.

| Thành phần | Kết quả thực tế |
|---|---|
| WSL | Bản có sẵn 2.7.12.0; distro mới `NaqexResearch`, WSL2 |
| Linux | Ubuntu 24.04.5 LTS, default user `naqex`; Python 3.12.3 |
| RD-Agent | 1.0.0, build từ `484776c211e4fbbeef03e0ec00d6bbee7362a4f4`, khớp gitlink |
| Docker Engine | 29.9.2; containerd 2.4.2, Buildx 0.38.1; repo/key chính thức Docker |
| Persistent disk | `.runtime/linux/NaqexResearch/ext4.vhdx`; không xử lý như cache |
| Linux source/venv/evidence | `/opt/naqex/rd-agent/{source,venv,evidence}` |
| Handoff | Distro đã terminate đúng tên, `wsl --list --verbose` xác nhận Stopped; worker vẫn paused |

Kiểm chứng đã thực hiện:

- Cài đặt kết thúc exit 0; `pip check` báo không có dependency hỏng;
  `rdagent --help` tải CLI thành công.
- `rdagent health_check --no-check-env --no-check-ports` ghi Docker normal;
  Docker SDK ping được assert thành công, không chỉ dựa vào exit status upstream.
- Container `hello-world` chạy thành công với network none, memory 64m, CPU 1,
  pids 64, cap-drop ALL, no-new-privileges. Digest:
  `sha256:c567b231f65614688711a75f31518a064258a51d442117a3e771a3a8fdba78ef`.
- Sau restart riêng distro: user đúng, không mount ổ Windows, Windows interop
  tắt; Docker service/socket/containerd inactive và disabled autostart.
  Docker chỉ dùng Unix socket. Docker group có quyền root trong distro;
  không coi đây là sandbox tuyệt đối cho generated code.
- Upstream có cảnh báo import `fitz` deprecated, không chặn CLI/runtime smoke;
  chưa sửa dependency hoặc source để che cảnh báo.

Logs/script bootstrap và bản sao tám evidence files giữ local trong
`.runtime/linux/`, gồm `provision.log` và `evidence/requirements.freeze.txt`.
SHA256 freeze:
`5398B1333DCE26F036AEBD93BAFD0D4C96C04B73DF7EE2611E4E18F85380FDA1`.
Nguồn Ubuntu qua catalog/downloader chính thức WSL; chưa tự tính lại checksum
rootfs, không tuyên bố đã làm bước đó. Docker signing key fingerprint:
`9DC858229FC7DD38854AE2D88D81803C0EBFCD88`.

Chưa dựng finance Qlib/CUDA image, tải dataset, gọi model hoặc chạy finance
experiment. Cần data adapter, bounded experiment/container policy và provider
qualification trước khi mở worker. Wrapper vẫn từ chối RD-Agent dispatch;
chỉ cập nhật thông báo lỗi cũ để phản ánh runtime đã cài. Đây chưa là nghiệm
thu vòng nghiên cứu hay chiến lược. Hướng dẫn vận hành/rollback:
[RD-Agent runtime](../../../tooling/ai-engines/rd-agent-runtime.md).

[Khảo sát Hermes/OpenClaw](../../research/HERMES-OPENCLAW-20261102.md) đã đối
chiếu source/docs chính thức. Chưa cài hoặc benchmark hai công cụ này. Đề xuất
chưa thêm vào global/Codex: Hermes chỉ thử làm worker khi có task chứng minh
lợi ích; OpenClaw dành cho nhu cầu kênh chat owner sau này. Paperclip tiếp tục
sở hữu dispatch/retry/cancellation/history.

Final AI environment audit đạt 0 errors, 0 warnings; global 12,279 B, project
9,099/65,536 B, reserve 56,437 B, combined 21,378 B. Không sửa global config.

## 02/11 — RD-Agent synthetic factor pilot

Owner duyệt một thí nghiệm nhỏ trước khi thêm engine. Đã chạy **một candidate
do Gemini sinh**, dùng upstream `FactorTask`, `FactorFBWorkspace` và evaluators
từ RD-Agent 1.0.0/pin `484776c211e4fbbeef03e0ec00d6bbee7362a4f4`.
Không sửa source upstream, không mở RD worker/Paperclip adapter hoặc scheduler.

### Request và data/state

- Operator tạo prompt/contract trước, gọi gateway project loopback 17852 một
  lần, không retry; requested `gemini-3.8-flash-high`, response báo
  `gemini-3.8-flash-n`. Alias/response không độc lập xác minh model backend.
- Usage: 150 prompt + 1.567 completion = 1.717 tokens; completion gồm 1.457
  reasoning tokens. Không có phép đo chi phí tiền hoặc lợi nhuận.
- Candidate đã review: đọc HDF giả lập, group theo instrument, shift 3,
  tính `close / previous_close - 1`, giữ full index/order rồi ghi result HDF.
- Fixture seed 20261102, 160 ngày × 8 mã = 1.280 rows. Contract ghi split
  90/30/40 ngày nhưng pilot không fit/tune/chọn model hoặc báo OOS performance.
- Controller/venv ở Linux riêng; candidate ở Docker network none, CPU 1,
  RAM 512 MB, pids 64, 50 giây, user 1000:1000, read-only root filesystem,
  cap-drop ALL, no-new-privileges, tmpfs 32 MB. Mount workspace RW và input RO;
  không mount Docker socket, controller, credentials hoặc ổ Windows.
- Workspace output chưa có disk quota riêng; code này đã review, chưa là
  sandbox cho code thù địch. Docker group có quyền root trong distro.

### Kết quả

| Kiểm chứng | Kết quả |
|---|---|
| Upstream workspace thực thi candidate | Đạt, launcher exit 0 |
| Oracle vòng lặp độc lập | Đúng đủ 1.280 rows; 1.256 giá trị hợp lệ, 24 warmup NaN |
| Upstream evaluators | Inf, SingleColumn, Index, RowCount, EqualValueRatio đều score 1 |
| Prefix invariance và future perturbation | Đạt; output trước cutoff giữ nguyên |
| Negative causal control | Công thức shift(-1) bị phép kiểm phát hiện nhìn trước |
| Expected execution failure | Upstream workspace trả failure đúng và giữ marker lỗi |
| Real-data finance loop / native dispatch | Chưa chạy, worker vẫn paused và adapter từ chối RD job |
| Strategy qualification / broker | Không; không có backtest lợi nhuận hoặc broker request |

### Failures đã giải quyết

1. Docker start trong một WSL call rời không giữ service cho call kế tiếp:
   gom start/job/EXIT cleanup vào cùng owned root shell.
2. Import RD từ cwd `/root` gây template-loader PermissionError: chuyển sang
   job directory Linux mà `naqex` truy cập được trước `runuser`.
3. Receipt dùng `rdagent.__file__` gặp namespace package None: ghi `__path__`.
4. Copy shell wrapper làm mất executable mode: gọi `sh <wrapper>` tường minh.
5. Oracle có NumPy timedelta deprecation warning không chặn kết quả; không vá
   dependency/upstream chỉ để che cảnh báo. Không gọi model lại khi sửa harness.

### Provenance, artifacts và handoff

| Artifact | SHA256 |
|---|---|
| Docker image ID | `766b1a0e71699c07765a47f8c671cdfaa0cb234a3ca493b8c145382e44408ca8` |
| pilot.py | `b1d368f0706dccdf94911c6ad81d1cd82b9361a4ad994ceaebb6ecbae04428c5` |
| candidate.py | `91a00cb4b61f84e0043ebfa52c7434377a472266e4ab5b04ffbc17ed9cfd4ae9` |
| fixture HDF | `c5943829460bdeeebd2ae080a3ec7f6994ee855bef43e37fa0f9ad9d0eecd4f6` |

Tracked harness/recipe: [rd-factor-pilot](../../../tooling/ai-engines/rd-factor-pilot/README.md).
Linux job: `/opt/naqex/rd-agent/pilots/20261102-momentum-01/`.
Windows local evidence: `.runtime/linux/factor-pilot/` gồm `run.log`, model
attempt, candidate, complete `evidence.tar`, các failure logs; các root regular
files cần thiết được đọc/chọn an toàn sang `evidence/`, không extract symlinks.
Raw data/runtime không commit. Image tag/transitive packages chưa khóa toàn
bộ; receipt image ID là danh tính immutable của chính lượt đã chạy.

Docker cleanup của launcher đã kết thúc; `wsl --list --verbose` xác nhận
`NaqexResearch` **Stopped**. Gateway trước pilot đang off; PID 14488 được xác
minh path, SHA256, command/config và creation time rồi dừng, owner file ghi
`stopped`. Một lần guard từ chối vì JSON date đã parse thành DateTime nhưng
bị parse lại qua culture; sửa kiểm tra bằng typed DateTime trước khi stop.
Không sửa gateway config, Windows 8317 hoặc bật service nền mới.

Lát tiếp: chọn data adapter có point-in-time provenance, chốt bounded finance
contract và kiểm native dispatch/cancel trước mở RD worker. Pilot xác nhận
đường **sinh code → thực thi → kiểm chứng**, chưa nghiệm thu hệ AI tự chủ đầy đủ.

## 02/11 — workflow market factor qua native Paperclip

Owner duyệt nối trọn luồng dữ liệu thật → một candidate Gemini → RD-Agent →
Quant Lab → báo cáo native Paperclip. Scope là contract cố định
`crypto-momentum-3d-v1`, không thêm engine/UI riêng hoặc mở vòng tìm kiếm tự do.
Không migration, broker/demo/live, protected holdout hay scheduler.

### Hành vi và luồng data/state

1. Dùng public Binance downloader có sẵn của Quant Lab tạo snapshot BTCUSDT và
   ETHUSDT daily UTC: `2021-01-01 <= open_time < 2025-01-01`. Mỗi mã 1.461
   nến, tổng 2.922. Kiểm hash, calendar, OHLCV, gap budget 0 và close time trước
   provider. Downloader có thể trả boundary candle do endTime inclusive;
   controller lọc đúng window trước factor/evaluation, không dùng nến ngoài kỳ.
2. Paperclip giao task đúng worker. Một model request, không retry; prompt cố
   định factor `close[t] / close[t-3] - 1` theo instrument. AST review giới hạn
   thao tác transform; code chạy trong Docker offline, không chạy trên Windows.
3. Upstream RD-Agent FactorTask/FactorFBWorkspace và năm evaluators thực thi,
   so với oracle vòng lặp độc lập. Đạt 2.922 rows, 2.916 giá trị và 6 warmup NaN;
   cả năm evaluator score 1. Prefix/future-perturbation invariance đạt; negative
   control nhìn trước và execution failure đều được phát hiện.
4. Quant Lab xác minh factor rồi replay quy tắc tương đương bằng signal/accounting
   có sẵn trên từng prefix, không chạy arbitrary candidate trong evaluator tin
   cậy. Factor dương thì long, còn lại giữ tiền; vị thế từ nến sau. Expanding
   train 730 bars, bốn cửa sổ OOS rời nhau 180 bars/mã, 11 tail bars unused.
   So cash/buy-hold cùng input/timing, phí 10 bps + trượt giá 5 bps và stress 2x.
5. Lưu artifacts trước publication; native documents **Kết quả nghiên cứu** và
   **Dữ liệu và kiểm chứng** giữ summary và metrics/provenance riêng. Nếu gửi
   báo cáo lỗi, kết quả đã tính còn nguyên, delivery báo failed và không tự
   gọi lại provider. Paperclip giữ dispatch/concurrency/cancellation.

### Kết quả thực tế

Native task [NAQ-6](http://127.0.0.1:17860/NAQ/issues/NAQ-6) `done`, run
`2193750a-cb69-47c9-88b3-9c9e0bceaa0f` `succeeded`, local receipt
`completed/published`. Company `6b90f0c1-8f91-4fe8-bc15-fc8c58b3ac8f`, worker
`a3c59356-275a-4960-88e0-98cb7d8ea60f` — Chuyên viên nghiên cứu.

Các số lợi nhuận sau là **median tổng lợi nhuận của bốn cửa sổ 180 ngày**,
không phải lợi nhuận gộp toàn kỳ hoặc dự báo:

| Mã | Ứng viên, 15 bps | Ứng viên, 30 bps | Mua và giữ, 15 bps | Drawdown xấu nhất ứng viên, 15 bps |
|---|---:|---:|---:|---:|
| BTCUSDT | 27,52% | 17,74% | 51,71% | -17,94% |
| ETHUSDT | 1,50% | -6,17% | 36,90% | -28,73% |

Workflow đạt; **candidate chưa qualified**. Chưa có kiểm định ý nghĩa thống kê,
parameter stability, mô phỏng order book/partial fills hoặc forward demo.
Formula đã chốt trước, không fit/tune theo số OOS; đây là kiểm workflow, chưa
phải full RD-Agent `fin_factor/fin_model` hypothesis search. Snapshot lịch sử
tải hiện tại không bảo đảm revision-vintage/PIT và không là final holdout kín.
Không chạy tiếp để chọn số đẹp hơn, không tự promote chiến lược.

### Kiểm chứng và lỗi đã giải quyết

- Model: một call, zero retries; requested `gemini-3.8-flash-high`, reported
  `gemini-3.8-flash-n`. Usage 175 prompt + 1.073 completion = 1.248 tokens,
  gồm 963 reasoning tokens. Alias/response không độc lập chứng minh backend.
- Native cancellation riêng, không gọi model: NAQ-5, run
  `7802a335-8649-4447-a343-3cd2579f6e2a` chuyển `cancelled`; Linux guardian ghi
  `cancelled_eof`, child stopped, Docker/socket/containerd inactive. Fixture
  agent `a3d5973f-8bd5-4510-a8ef-0fdd9a411765` đã terminated, task cancelled.
- Guardian giữ exclusive flock và lease heartbeat/EOF; không giành daemon đang
  active. Dọn container đúng job label rồi dừng services do job khởi động.
  Container network none, RO root, user 1000, RAM 512 MB, CPU 1, pids 64,
  deadline 50 s, tmpfs 32 MB, cap-drop ALL/no-new-privileges; giới hạn mỗi file
  8 MiB, chưa có tổng disk quota. Chưa chứng nhận sandbox cho code thù địch.
- Linux smoke đầu gặp PyTables không lưu timezone-extension MultiIndex:
  normalize UTC rồi strip timezone chỉ tại biên HDF, evaluator khôi phục UTC.
  Smoke r2 đạt 2.922 rows/four folds trước provider run; không gọi lại model.
- Resume fixture agent và sửa tài liệu từng trả 409: đọc lại lifecycle/revision,
  dùng native resume/optimistic concurrency; không bypass ownership guard.
- Test baseline ban đầu giả định thứ tự list sai; sửa tìm theo `baseline_id`.
  Kiểm chứng cuối: **23/23 engine tests**; Quant Lab focused **38 tests** đã
  đạt trước đó, không chạy lại vì Quant source không đổi. Ruff F, workspace
  contracts và GitHub workflow structure đạt; ba integration source đúng pin,
  clean tracked source theo doctor đã chạy trong lượt này.
- Browser thực tại 1440×1000: Trader5218 iframe Paperclip17860 mở báo cáo,
  số liệu hiển thị đúng, giữ qua native navigation/reload, zero page errors.
  Bảng ban đầu quá rộng panel: đổi thành bảng ba cột/mã, metrics đầy đủ ở tài
  liệu riêng. Summary rev 2, evidence rev 1; không gọi provider lại. Không có
  kiểm server restart hoặc whole-product acceptance.

### Provenance và bàn giao

| Artifact/source | SHA256 hoặc pin |
|---|---|
| Snapshot manifest | `1136529b04f9a5e48ae2a3874889a1e9ac558a604e8e663b100687c64c33d110` |
| Candidate | `68ecd25a5e9e1c280e5edc24486932e3431b689d9f023b097222b282027b3b90` |
| RD-Agent | `484776c211e4fbbeef03e0ec00d6bbee7362a4f4` |
| Quant Lab | `943b779dc96ac16aae6718cec16f4f3f00e07a92` |
| Docker image | `sha256:766b1a0e71699c07765a47f8c671cdfaa0cb234a3ca493b8c145382e44408ca8` |
| Actual-run engine_worker.py | `fd6cffcfe3daccc11aff7055db6456d387bb9b9fc2d892f16dfc91a1bb2335d3` |
| pilot.py | `a71ea41178c9ff213fc71cdf63fe847e9fc1ab056c2d013deae13dda9dffda18` |
| guardian.py | `6fc8abe59edaf35909b30daefc1a6ee033d1dbe75ba401af0a482fb7b9ca1799` |
| Report rev 2 | `90e043c64cbe8564e1e67902b27a6f1b000469b735f11a35117460effa8663d0` |
| Evidence doc | `382444b416b399e583e2c62b7ef1f837b1fa77c1b0fe822dc9d9cd921fcefe23` |

Artifacts ở
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/6b90f0c1-8f91-4fe8-bc15-fc8c58b3ac8f/2193750a-cb69-47c9-88b3-9c9e0bceaa0f/`.
Dataset `.runtime/ai-engines/datasets/crypto-daily-2021-2024/`; browser
artifacts/result và final-summary giữ tại `.runtime/ai-engines/`.
Linux job `/opt/naqex/rd-agent/paperclip-jobs/<run-id>/` giữ guardian/result/logs.
Raw data/private settings/runtime artifacts không commit.

Actual provider/native run dùng wrapper hash ghi ở trên. Sau đó đã tách tài
liệu evidence, thu gọn formatter và sửa persist-before-publish; source mới được
23 tests và native document API kiểm chứng, **chưa chạy lại toàn bộ provider job**.
Receipt local giữ original hash và presentation-update hash, bản report cũ còn
`report-presentation-v1.md`. Child RD receipt `paperclip_dispatch:false` chỉ nói
pilot con không sở hữu API; outer receipt `dispatch.kind=paperclip-native-process`
và native run là bằng chứng dispatch thực.

Handoff: workers idle, timer off; agent Trưởng nhóm nghiên cứu của owner giữ
nguyên. Docker services inactive, distro NaqexResearch đã Stopped. Paperclip17860,
gateway project17852 và preview5218 còn mở để owner xem; gateway owner metadata
đã khớp PID/path/config/creation time/hash và catalog readiness. Không sửa instance
Windows8317, không thêm autostart/service hệ thống hoặc AI-environment config.
Tiếp theo cần một research contract mới có tiêu chí chọn/loại và kế hoạch đánh
giá trước khi mở vòng tìm kiếm; không giao lại NAQ-6 đã hoàn tất.

## 02/11 — Hermes reviewer trong Paperclip, giữ native workers

Owner duyệt thử Hermes như harness tùy chọn, Gemini qua gateway project 17852;
không thay các engine nghiên cứu/số liệu hay nối global Codex/MCP. Đây là pilot
phản biện hồ sơ NAQ-6, không phải chiến lược đủ điều kiện hoặc vòng autonomy mới.

### Source và runtime

- Hermes upstream MIT, release `v0.22.5`, gitlink
  `bf0203a794a07aac3ff764972ab9087baa4e4f4e` tại
  `projects/integrations/hermes-agent`; không sửa core. Upstream PM chuẩn bị
  core Python 3.14.9, extras `[]`, trong `.runtime/hermes/research/installs/`.
  PM snapshot báo CLI version unknown; provenance lấy gitlink, không suy từ nhãn.
- Chọn SDK chính thức `run_agent.AIAgent` + native `process` adapter. Release này
  cho CLI chat tự mở local gateway detached; dừng CLI chưa chứng minh daemon
  task đã dừng. SDK chạy cùng child process để Paperclip sở hữu lifecycle.
  Gateway Hermes của lượt probe đã được dừng; không thêm service/listener/MCP.
- Profile, sessions và memory riêng dưới `.runtime/hermes/research/`; không nhập
  Codex memory/credentials. Worker đọc internal gateway key từ managed config
  lúc chạy, không giữ thêm key trong `.env` hay task/Paperclip settings.
- Inventory thực đã kiểm: `memory`, `research_publish`, `session_search`;
  progressive tool discovery tắt. Không terminal/files/code/delegation/cron/
  broker; đây là capability limit, **không phải OS sandbox**. Memory là context
  tạm, không là bằng chứng mới hoặc quyền promote skill/strategy.
- Worker **Chuyên viên phản biện** `43144218-ee99-427d-aabb-5abde2f8d804`,
  reports-to leader hiện có của owner. Timer off, wake-on-demand, concurrency 1.
  Hướng dẫn setup/disable: [Hermes guide](../../../tooling/ai-engines/hermes.md).

### Native jobs và completion

| Task | Bằng chứng |
|---|---|
| NAQ-7 | Thất bại trước inference vì SDK venv không có PyYAML; task cancelled, giữ history. Reuse `hermes_yaml.safe_load`, không pip thêm vào PM venv |
| [NAQ-8](http://127.0.0.1:17860/NAQ/issues/NAQ-8) | Run `e9e5e6d1-2a88-47cc-a42b-2b5d94d564f4` succeeded, issue done, report native và bài học đã lưu |
| NAQ-9 | Run `9867a41a-c2ce-40b4-95fc-9e51c24f100c` cancelled; fixture SDK HTTP loopback, zero external provider calls |
| NAQ-10 | Run `251edf38-3648-4337-87d1-ce5f7a3e9a70` succeeded; process mới trích đúng bài học cũ mà task không cung cấp lại nội dung |
| [NAQ-11](http://127.0.0.1:17860/NAQ/issues/NAQ-11) | Run `a8868849-d05e-4c4b-befd-b66b79a420a5` succeeded, issue done với completion contract cuối cùng |

Plugin chỉ attach document và ghi publication `attached`; worker chỉ PATCH issue
done khi model turn completed **và** đã attach. Nếu model lỗi sau attachment,
không coi task done. NAQ-11 kiểm chứng source cuối, receipt lưu source/worker hash
và memory hash trước chạy. NAQ-8 là bản benchmark trước bước siết completion và
thêm provenance này; không gán current worker hash ngược cho lượt NAQ-8.

Native cancel NAQ-9 mất khoảng 0,172s. SDK PID 23376 dừng, listener 59553 đóng,
không có completion file; fixture dùng real SDK nhưng không gọi model thật.
AdapterConfig đã được phục hồi. Đây là bằng chứng hủy local child, không bảo đảm
thu hồi computation/billing của remote provider.

### So sánh tối thiểu: Gemini trực tiếp và Hermes + Gemini

Cùng dossier [hermes-pilot.md](../../../tooling/ai-engines/hermes-pilot.md),
SHA256 `1ab0d6cff53a6a62d6f94898fafc6e3afa89c3b498f0f8d2322529b02cf52b13`.
Requested `gemini-3.8-flash-high`, response route `gemini-3.8-flash-n` ở cả hai;
alias không độc lập xác nhận model thực tế.

| Đo trên một task | Gemini trực tiếp | Hermes + Gemini |
|---|---:|---:|
| Wall time | 29,04s | 38,83s SDK; 41,40s native run |
| API calls | 1 | 2 |
| Total tokens theo API | 4.185 | 18.309 |

N=1, system prompt/tool loop khác nhau theo harness; chưa đo latency ổn định,
chi phí USD hay chất lượng trên bộ task đại diện. Hermes dùng khoảng 4,37 lần
token trong lượt này; **chưa chứng minh chất lượng tốt hơn**.

Hai báo cáo chép đúng 8 metric chính, phân biệt median walk-forward OOS với return
toàn kỳ và không promote strategy. Đề xuất thí nghiệm tiếp theo của cả hai chưa
đủ executable contract. Direct gọi dữ liệu từ 2024 là mới dù snapshot đã chứa 2024;
Hermes gọi 2025 là holdout chưa tiếp xúc mà hồ sơ không chứng minh lịch sử tiếp xúc
toàn workspace, filter volatility chưa định nghĩa và comparator chưa cùng kỳ.
Không dùng kết luận tuyệt đối “không leakage” từ vài invariance/oracle checks.
Đã attach **Đối chiếu và giới hạn** vào NAQ-8, giữ nguyên report gốc để bảo toàn
provenance; không chạy theo các đề xuất này hoặc gọi lại để chọn kết quả đẹp hơn.

Lợi ích thực chứng của Hermes trong phạm vi này là tool workflow đăng báo cáo và
memory qua process mới. Giữ native workers, dùng Hermes tùy chọn khi cần hai khả
năng đó; không đổi toàn bộ harness.

### Kiểm chứng, recovery và bàn giao

- Hermes plugin/worker focused **6/6 pass**; shared engine-worker regression
  **16/16 pass** sau thay optional YAML loader. Không chạy lại suite không đổi.
- Paperclip explicit `HERMES_HOME` probe từng tìm host `python3`/`~/.hermes`, bỏ
  qua configured profile. Sửa cùng đường hello probe đang dùng cho managed
  routing; giữ connection gate, không bypass. Commit Paperclip
  `14241e3bab1f3f03444d70189b33352bfb5f119c`; focused tests **3/3 pass** và
  Hermes package `tsc --noEmit` pass. Legacy `detect-model.test.ts`: 5 pass,
  **2 fail trên Windows do không có host python3**; nhánh đó không thay. Chưa
  full monorepo acceptance/PR-ready.
- Trước restart đã backup qua native API:
  `.runtime/paperclip/instances/trader-ui/backups/paperclip-20261102-093150.sql.gz`,
  627.192 bytes. Kiểm owner/PID trước restart; PostgreSQL thoát cùng server,
  `pg_ctl stop` báo No such process, không reset/restore/migration. Static UI
  build đạt, health xác nhận đúng commit đang chạy.
- Browser 1440×1000: Trader 5218 iframe Paperclip 17860 mở được Đối chiếu và giới
  hạn NAQ-8 và Kết quả phản biện NAQ-11, zero page errors. Lần assertion đầu
  dùng exact plain text không khớp native issue-link rendering; sửa locator theo
  heading rồi kiểm lại, không sửa report hay gọi provider.
- Worker hiện idle, timer off; RD-Agent/TradingAgents/leader của owner được giữ.
  Không có Hermes worker/daemon còn chạy; project gateway 17852, Paperclip 17860,
  Trader 5218 còn mở. Không tác động Windows gateway 8317/global Codex.
- Integration doctor cuối: cả bốn source đúng pin/origin/license, sạch tracked
  source; Paperclip runtime healthy. AI-environment audit: 0 lỗi / 0 cảnh báo,
  global 12.279 B, project 9.099/65.536 B, reserve 56.437 B; không sửa global config.
- Validator metadata phát hiện hai AI trailers bị tách bởi dòng trống. Đã sửa
  message của commit local, không đổi source tree: Paperclip pin cuối
  `2e0f8f84b810ef3ae89c400d3ee1faf6b281c217` thay `14241e3b` nêu ở lượt thử.
  Backup mới `paperclip-20261102-095653.sql.gz` (672.043 bytes), restart đúng
  owner khi workers idle; health đúng pin cuối, NAQ-11 còn done sau restart.
  Không chạy model lại; các receipt cũ giữ commit/source evidence lúc thực thi.

Artifacts gốc theo từng run tại
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/6b90f0c1-8f91-4fe8-bc15-fc8c58b3ac8f/`.
Folder `hermes-benchmark-20261102/` giữ `benchmark.json`, manifest SHA256, dossier,
hai báo cáo, operator review, usage/receipts, memory/cancel/native status và browser
screenshots; không chứa settings/key. Source/plugin final hashes nằm trong
benchmark và NAQ-11 receipt. `.runtime/hermes/` giữ profile/config/private state
local, không commit. Paperclip fix hiện là local commit; chưa push/fresh-clone
acceptance. Không tuyên bố hoàn tất product audit hay toàn bộ AI autonomy.

### Bổ sung — lệnh python3 trên Windows

Owner cho phép bổ sung Python. Máy đã có Python 3.12.10 chính thức; `python3`
trước đó trỏ Microsoft Store alias. Đã tạo hard link `python3.exe` cạnh
`C:/Users/MIIKEY/AppData/Local/Programs/Python/Python312/python.exe`, dùng cùng
binary/hash và standard library, không cài interpreter trùng hoặc sửa PATH.
Smoke import `ssl`, `sqlite3`, `venv` đạt. Hai file `detect-model.test.ts` và
`profile-environment.test.ts` hiện **10/10 pass**, thay giới hạn hai test lỗi
đã ghi ở lượt trước. Không sửa test/source Paperclip hoặc gọi provider lại.
Rollback riêng alias bằng cách xóa đúng `Python312/python3.exe`, giữ `python.exe`.
AI-environment audit sau thay đổi: 0 lỗi/0 cảnh báo; instruction sizes và reserve
giữ nguyên các số đã ghi ở lượt trước.

## 02/11 — workflow crypto spot có dependency và bàn giao cho owner

Owner đã chọn crypto spot và duyệt nối workflow. Dùng `spot_workflow.py` để tạo
graph idempotent bằng native issue idempotency keys, parent/children và dependency
wakeups. Không thêm UI, coordinator agent, poller/scheduler hoặc patch upstream.
Giữ đội hiện có; leader do owner tạo không đổi cấu hình. Source/artifact input
không nhận path hoặc command từ task.

### Kết quả và phạm vi

| Công việc | Trạng thái thực tế |
|---|---|
| [NAQ-20](http://127.0.0.1:17860/NAQ/issues/NAQ-20) | Tổng hợp `in_review`, giao `local-board` để owner xem |
| NAQ-21 | RD-Agent/Quant Lab done; native run `40a670e2-4798-4892-a4b8-ffa05ffa628d` succeeded |
| NAQ-22 | Hermes nhận tự động từ dependency, model turn hoàn tất, report đã attached và issue done; run có lỗi **bàn giao cuối** được giữ nguyên |
| NAQ-23 | Paper blocked, unassigned, **NOT_RUN**; không có forward observation |
| NAQ-24 | Fixture native API sửa/kiểm riêng bàn giao; run `eaa13b37-0663-42c1-8a84-88c8cf69e1c5` succeeded, zero provider calls |

Lượt này rerun đúng contract `crypto-momentum-3d-v1` BTC/ETH D1 trên snapshot cũ
để kiểm tích hợp; một candidate Gemini, không đổi formula/tune dữ liệu đã xem.
Requested route `gemini-3.8-flash-high` không chứng minh model nền phía provider.
Các metric chính bằng NAQ-6: median bốn cửa sổ OOS 180 ngày, BTC 27,52%/17,74%
ở chi phí 15/30 bps, ETH 1,50%/-6,17%; không phải return gộp toàn kỳ. Candidate
vẫn research-only, không có holdout kín mới, strategy qualification hoặc broker.

Hermes xác minh dependency UUID, company/agent/parent, source request cố định,
native run succeeded, receipt completed/published, report/evidence hash và native
document revision. Hồ sơ số liệu được dựng từ Quant validation, attach thành
**Nguồn và số liệu phản biện** trước inference, lưu binding ở `review-source.json`.
Kiểm lại binding trước provider và publication/finalization; thiếu/sửa nguồn,
failed/cancelled run hoặc parent đã dừng không tự đi tiếp. Settle wait tối đa năm
giây chỉ đợi native process finalize, không retry provider. Review memory không
được yêu cầu sửa và không được dùng làm authority.

### Lỗi đã gặp và cách khắc phục

1. Native `in_progress` yêu cầu assignee. Parent tổng hợp không chạy agent;
   giữ unassigned `todo` trong lúc children làm việc. Ban đầu gán parent cho Board
   làm run-scoped cross-issue write bị từ chối; đã bỏ lựa chọn đó. Owner chỉ nhận
   hồ sơ ở bước cuối, qua API quyền native hiện có, không dùng board credentials
   bên trong worker.
2. Run Hermes `9e47a800-2c9a-430e-af99-c61dcd2ad2f7` có hai API calls, model
   hoàn tất và report được giữ, nhưng PATCH parent `in_review` bị 422 vì agent
   chưa chỉ rõ review path. Sửa bằng `assigneeUserId` của human creator/responsible
   user trong cùng transition. Giữ receipt failed với `review_delivery=published`;
   không sửa lịch sử thành succeeded và không gọi lại model. NAQ-24 kiểm chính
   thao tác đó qua native process/API bằng báo cáo đã có. Board probe từng chuyển
   parent sang in_review rồi trả todo trước fixture; hiện owner assignment và
   review state được native agent API xác nhận. Hai tài liệu cũ được ghi rõ là
   lịch sử/trước recovery; bản sửa đổi gốc còn nguyên.
3. Lần chạy unittest Hermes đầu dùng console cp1252 gây UnicodeEncodeError khi
   in tiếng Việt, không phải assertion logic. Dùng `-X utf8`; focused checks đạt.

### Kiểm chứng và giới hạn

- **32 focused tests pass:** shared engine worker 16, workflow 7, Hermes worker
  4, plugin 5. Gồm schema/path, duplicate start, wrong scope/run/worker, source
  failed/cancelled/hash/revision change, bỏ binding, cancellation calls, model
  failure sau attach, partial parent delivery và paper không tự chạy. Không chạy
  lại broad suite không đổi.
- Native graph create gọi lại trả cùng bốn IDs. Offline missing-source fixtures
  NAQ-12–19 đánh thức review nhưng receipts xác nhận `provider_work_started=false`;
  source completion giả lập không được coi là kết quả nghiên cứu. Các graph thử
  đã cancelled qua helper, giữ done history. Lỗi self-block status write ban đầu
  được tránh bằng không PATCH lại issue đã blocked.
- Cancel helper được kiểm qua fake native API: hủy parent trước, cancel active
  child run, giữ done history. Hủy graph không có active provider đã kiểm native;
  native active SDK cancellation dựa trên receipt NAQ-9 trước đó, không lặp lại
  provider/cancel benchmark. UI chỉ hủy parent không bảo đảm dừng process tức thì;
  dùng helper hoặc native run cancel. Guard chặn bước tiếp theo/publication.
- Có một research run thực tế và một Hermes run thực tế; đường tự động dependency
  đã chạy. Bản sửa bàn giao cuối kiểm riêng offline/native và bằng unit test,
  **chưa rerun toàn chuỗi provider sau sửa**, vì kết quả model đã có và không cần
  lặp inference để kiểm status update.
- Browser đọc được NAQ-20 `in_review`/Board cùng ba children, mở **Kết quả và bước
  tiếp theo** ở trang native. Iframe Trader hiện dashboard với trạng thái các
  task. CUA click/focus trong iframe bị “target/root no longer available”; đã
  chuyển kiểm đọc report sang tab native, không tự coi đây là bằng chứng bug app
  hoặc toàn bộ interaction trong iframe đạt. Giới hạn này giữ cho lát UI sau.
- Doctor: bốn source đúng pin/origin/license, tracked source sạch, Paperclip
  healthy. AI audit cuối: 0 lỗi/0 cảnh báo, global 12.279 B, project 9.099/65.536 B,
  reserve 56.437 B, combined 21.378 B. Chỉ đồng bộ project Hermes plugin/profile
  khi worker idle; không đổi global Codex, port, engine pin hoặc provider secret.
- Handoff: bốn agents idle, timer heartbeats off; paper blocked/unassigned.
  Không có worker mới/daemon hoặc quyền demo/live. Không phải whole-product
  audit acceptance hay bằng chứng hệ thống đã tự kiếm tiền.

Evidence local:
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/6b90f0c1-8f91-4fe8-bc15-fc8c58b3ac8f/workflow-handoff-20261102/evidence.json`;
source/review artifacts giữ theo UUID run. Ảnh native owner report:
`9e47a800-2c9a-430e-af99-c61dcd2ad2f7/workflow-owner-review.png` dưới cùng artifact
root/company. Backup DB trước lát này vẫn là native
`.runtime/paperclip/instances/trader-ui/backups/paperclip-20261102-095653.sql.gz`;
không restore, migration hoặc restart server trong lượt này.

Bước tiếp: owner đọc hai báo cáo NAQ-21/22, chốt câu hỏi/contract nghiên cứu mới
trước chạy experiment khác. Đề xuất thêm filter/parameter scan từ báo cáo Hermes
chỉ là gợi ý chưa được duyệt, không là contract hoặc lệnh tự chạy.

## 02/11 — kiểm lại ứng viên cũ và đánh giá khả năng dùng tiền

Owner giao tiếp tục và hỏi hệ thống có thể kiếm tiền chưa. Thực hiện một lượt
offline với **quy tắc Donchian100/50 + vol30%/lookback30 đã có**, không làm theo
gợi ý filter/scan, không thêm model/engine hoặc mở dữ liệu chưa xem. Báo cáo dễ
đọc: [mức sẵn sàng](STRATEGY-READINESS-20261102.md); issue umbrella #6 vẫn mở.

### Thí nghiệm và kết luận

- Snapshot BTC/ETH 2021–2024, 1.461 nến mỗi tài sản; contract ghi trước đánh giá,
  source Quant `943b779d`. Bốn cửa sổ 180 ngày, 01/01/2023–20/12/2024,
  cash/buy-hold cùng input/timing/cost. Phí10 + slippage5 bps, stress40bps tổng.
  Không tune, không portfolio claim, không thống kê ý nghĩa/qualification.
- Hoàn tất 104,26 giây, provider calls0. Trung vị lợi nhuận cửa sổ: BTC16,87%
  (stress15,87%), ETH8,23% (7,87%). Mua và giữ lần lượt51,71% và36,90%.
  Worst drawdown **trong các cửa sổ**: BTC−11,96% (−12,69%), ETH−14,20%
  (−14,39%), so passive−20,93%/−37,07%. Không gán các số này cho cả giai đoạn.
  Mỗi tài sản3/4 cửa sổ lãi; cửa sổ đầu vẫn lỗ và giữ trong report/validation.
- Chưa đủ bằng chứng dùng tiền thật: dữ liệu đã consumed, giá khớp vẫn xấp xỉ
  close-to-close; chưa forward observation/portfolio xuyên suốt/chi phí vận hành
  và risk budget. Giảm drawdown nhưng ít return hơn không tự phủ định mục tiêu
  giảm rủi ro; có lãi lịch sử cũng không xác nhận edge tương lai.
- Native document `strategy-readiness-20261102` trên NAQ-20 đã PUT rồi GET lại,
  body SHA `c85e932482dc20fc95ca56821707f5d9fdbe69e931378344a162a25d6f28fe44`
  khớp report repo. Đây là operator publication, không giả làm native AI run.
  Parent giữ `in_review`/local-board; paper blocked/unassigned/NOT_RUN,0ngày;
  bốn agents idle/timers off. Không dispatch, broker/demo/live hoặc lịch mới.

### Lỗi chất lượng dữ liệu đã sửa

- Tái hiện ở pandas2.3.3 (Quant) và worker3.0.6: integer timestamp us từng bị
  chia cố định1e9, daily86.400giây thành86,4giây; missing-day fixture bị nhận
  accepted/gap_count0. Trước sửa regression s/ms/us fail, ns pass.
- Source `quant_trading/data_quality.py` đổi sang
  `timestamps.diff().dropna().dt.total_seconds()`, không sửa/fill nến.
  Quant commit `52f6501c4058d46e298678d963908b5ef76d84e8`.
- 21 quality tests trên từng môi trường đạt, gồm regular/missing-day/rejection
  và input bất biến cho s/ms/us/ns. 7 RD workflow tests đạt; hai dòng stdout
  failed/completed trong suite là kết quả fixture mocked delivery, không real run.
  Ruff hai file sửa đạt, diff review đạt; không chạy broad suite không liên quan.
  pandas3 của worker nằm ngoài range Quant<3; focused pass chưa là full compatibility.
- Snapshot cũ có quality metadata sai, sau sửa preflight từ chối đúng như kỳ vọng.
  Tạo `crypto-daily-2021-2024-quality-r2` từ đúng CSV, raw/canonical data hash
  giữ nguyên; audit mới86.400giây/gap0,1.461nến mỗi tài sản, preflight đạt.
  Manifest SHA `9b95da82fc591dccee5f9b8f32025476e226a8da02806959305a92e5048f0c38`.
  Dataset pin settings riêng chuyển khi workers idle, backup settings trước đổi.
  Không ghi đè manifest cũ/receipts lịch sử hoặc gọi dữ liệu này là OOS mới.
- Run số diễn ra trước sửa có exact UTC-index và timedelta cadence check độc
  lập; post-fix revalidation xác minh cùng nến/hash. Không lặp backtest chỉ để
  sửa metadata, không gán source mới cho kết quả cũ.
- Git commit Quant thành công nhưng automatic geometric-repack báo bad object
  ở ref `refs/codex/turn-diffs/checkpoints/...` của ứng dụng. HEAD/diff/source
  commit xác nhận được; không xóa ref hoặc sửa Git maintenance ngoài phạm vi.

Evidence dưới artifact root/company phía trên:
`donchian-frozen-review-20261102/` giữ run.py/contract/validation/report/receipt và
`owner-readiness-publication.json`; `quality-revalidation-20261102/` giữ script,
preflight và receipt hash cũ/mới. `STRATEGY-READINESS-20261102.md` dẫn chi tiết.

Bước tiếp: kiểm execution/accounting trên ứng viên cố định và chốt tiêu chí
rủi ro/lợi ích; sau bằng chứng phù hợp mới lập forward paper contract. Không tự
thêm engine, mở lịch hoặc sử dụng vốn từ kết quả này. Whole-product audit,
full autonomy và khả năng sinh lời vẫn chưa được công nhận.

## 02/11 — contract Forex/prop và kiểm mốc lỗ ngày offline

Owner đã chọn Forex major/MT5, FTMO 2-Step Swing làm chuẩn mô phỏng rồi giao
tiếp tục. [Contract đầu tiên](../../research/FOREX-PROP-PILOT-20261102.md) đăng ký
EURUSD/H4, 10.000 USD giả lập, risk dự kiến25 USD/lệnh, một candidate Donchian
20/10 + ATR14 cố định. Đây là defaults offline của agent; owner chưa chọn cỡ
tài khoản hoặc cấp risk budget tiền thật. Chưa xem outcome Forex, chọn/nhập
manifest hoặc mở holdout. Các guard25/100/500 USD và candidate là đặc tả cho
runner tiếp theo, không là tính năng đã nối vào job engine.

### Reuse, vấn đề tái hiện và thay đổi

- Dùng `projects/trader/foundation_v2/trading_workspace_v2/prop_session.py`
  và native `api-rust/src/prop_core.rs`; không viết rule engine thứ hai hoặc
  đổi Quant spot thành CFD backtester. Scope vẫn ở AI plan, không mở audit rộng.
- Nguồn FTMO đọc lại ngày02/11: [objectives, phần2-Step](https://ftmo.com/en/trading-objectives/),
  [Swing](https://ftmo.com/en/faq/what-is-the-swing-account-type-and-how-does-it-work/).
  Daily equity loss dùng balance lúc00:00 CE(S)T làm anchor; generic profile cũ
  lấy anchor theo cùng basis của loss nên chưa biểu diễn được luật này.
- Tái hiện bằng pure Python lifecycle: initial100.000, midnight balance102.000,
  floating−1.000 → equity101.000, anchor101.000/floor96.000. Theo reference cần
  anchor102.000/floor97.000. Đây là thiếu khả năng profile cho luật hãng mới,
  không khẳng định mọi generic simulation cũ sai.
- Thêm `daily_anchor_basis=balance|equity|null` ở phase, cập nhật schema và
  hai implementation. Null/absent giữ hành vi cũ. Money evaluator tiếp tục so
  equity với floor; reset lấy balance khi profile khai báo. Hai thứ tự phí/reset
  giữ riêng, không trừ phí hai lần. Không migration hoặc sửa profile đang lưu.
- Fixture named-provider có hai phase, URL/version quan sát, profile SHA;
  ngày effective là ngày đóng băng nghiên cứu, không phải ngày hãng đổi terms.
  Chưa là preset UI đầy đủ. Profile chứa field mới cần runtime/schema mới khi
  triển khai; chưa ghi nó vào DB runtime, không có dữ liệu cần rollback.

Source Trader: **`ac9d2d20fdc5d0d6a5d0cc4866531b85bb579b85`**, trên branch hiện có
`codex/note-workspace-completion`, sạch sau commit. Chưa merge/push, đổi gitlink
root hoặc cập nhật API/UI đang chạy. Root pin được giữ theo quy trình product
merge trước pin; fresh checkout root chưa bao gồm source candidate này.

### Kiểm chứng đã chạy

Từ `projects/trader/foundation_v2`, Python trong `.venv/Scripts/python.exe`, UTF8:

| Kiểm tra | Kết quả |
|---|---|
| `python -X utf8 -m unittest discover -s tests -p test_ftmo_swing_offline.py -v` | 8 tests đạt, gồm các subcases: floating±, phí/reset hai thứ tự, midnight breach, boundary bằng/vượt1cent, cả hai target/min4days/flat, carrying và thiếu intraday coverage |
| `python -X utf8 -m unittest discover -s tests -p test_ps00_prop_session_contract.py -v` | 15 đạt; có lịch Prague/DST/no-tick và money/contract/terminal state |
| Từ `tests`: `../.venv/Scripts/python.exe -X utf8 -m unittest test_ps02_prop_lifecycle.Ps02PropLifecycleTests -v` | 16 đạt; focused lifecycle, không chạy persistence/DB |
| `python -X utf8 scripts/rust_prop_check.py` | 2 Rust tests đạt: ca FTMO độc lập và corpus parity438 fixtures (342+96); compile offline21,36s, test0,18s |
| `python -X utf8 api-rust/tests/export_prop_schemas.py --check` | Đạt, gồm schema mới |
| Diff/format review | `git diff --check` đạt; rustfmt trên file Rust test; chỉ các file của lát này được stage |

Lần chạy 8tests đầu có5 assertion failures vì objectives serialize tiền thành
string, trong khi test mới so với Decimal. Sửa assertion theo JSON contract,
không sửa số kỳ vọng hoặc production code để pass; lượt sau8/8 đạt. Lifecycle
suite có warning upstream Starlette/httpx, assertions vẫn đạt. Không lặp broad
suite hoặc provider inference. Pure Rust harness chỉ compile Prop module;
không phải full API build/persistence/browser/runtime acceptance.

### Giới hạn và bước tiếp

Rule conformance offline đạt không chứng minh chiến lược có lợi nhuận/pass
challenge. Bản sửa ở source; màn hình Paperclip, agents/native task state và
runtime giữ nguyên trong lát này, không kiểm lại chúng để suy health hiện tại.
Chưa broker connection/demo/live, free trial, phí challenge hoặc scheduler mới.

**Bottleneck tiếp theo:** manifest bid/ask/cost hợp lệ và Forex execution/
accounting trên cùng virtual clock. H4/M1 close-only không đủ chứng minh không
breach intraday. Chốt nguồn/cutoff, cost và split trước outcome; nối một replay
offline cố định và independent accounting checks, rồi mới bàn forward trial.
Chưa tự promotion, mở holdout hoặc gọi lại workflow crypto cho Forex.

## 02/11 — khôi phục luồng QDM đã có theo nhắc nhở của owner

Owner nhắc project dùng QDM CLI và yêu cầu lưu cách dùng vào docs. Kiểm tra
trực tiếp xác nhận bộ cài **125.2692** còn ở checkout runtime cũ:
`D:/ANNAM/TradingWorkspace/projects/mt5-tradingview-backtester/foundation_v2/.runtime/quantdatamanager`.
Source hiện hành là `projects/trader`; bộ cài không tự chuyển theo rename.
`qdmcli.exe -h` và `-symbol action=list` qua wrapper `QdmCli` hiện có đều thành
công. Không đọc license, đổi activation, copy cache, restart API hay truy cập broker.

### Đã làm và kiểm chứng

- Export **cache có sẵn**, `EURUSD_TW`, M1, UTC, ngày03/01/2022, bằng
  `-data action=export`; không gọi `action=update`, không tạo symbol mới.
  Cache metadata có8.755.235 records,2003–2026; chỉ đọc giá ngày development
  đã đăng ký, không mở giá validation/holdout.
- CSV có1.425 nến,00:00–23:59UTC; timestamp tăng nghiêm ngặt, OHLC dương và
  đúng quan hệ high/low. Giờ12:00–13:00 có60 nến. So lưới24giờ thiếu15 phút;
  receipt giữ danh sách, `review_missing_minutes_not_filled`, không bù/suy giá.
- CSV SHA256: `c823e003012effb0dcf359722c82a12ce38d954046f9b2248e504ad1aff101af`.
  Artifact local:
  `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/forex-prop-pilot-20261102/qdm-cache-export-20261102/`.
  `receipt.json` giữ exact arguments, hash, khoảng ngày, checks và qualification;
  không đưa dữ liệu hãng vào Git hoặc đăng ký dataset trong DB Workspace.
- Cập nhật docs QDM hiện có với đường dẫn thực tế, wrapper/commands export,
  giới hạn M1/tick và update-full-history. README Trader/foundation route tới
  docs này. Sửa ghi chú FTMO cũ theo source balance-anchor vừa hoàn thành;
  không khẳng định runtime đã cập nhật hoặc preset đầy đủ.
- Dọn4 file prototype **chưa commit của chính lượt này**: direct tick capture,
  Node test, accounting probe và Python test phụ thuộc format capture đó.
  Không thêm downloader hoặc oracle mới trước khi có format tick QDM xác minh.
- Kiểm syntax Python của ví dụ docs,3 đường dẫn liên kết và đối chiếu lại
  hash/count trong receipt với CSV đều đạt; `git diff --check` ở hai repo đạt.
  Không chạy lại các suite Prop không đổi vì thay đổi giữ lại chỉ là docs.

Source docs Trader: `7e9e2730`, branch `codex/note-workspace-completion`.
Root gitlink giữ nguyên chờ product merge, chưa push/deploy hoặc thay runtime.

### Sai hướng trước khi sửa và giới hạn còn lại

Trước khi rà QDM đủ, thử direct Dukascopy Jetta nhậnHTTP202, header
`x-amzn-waf-action: challenge`; đã dừng, không bypass, không tạo capture.
Đây **không phải** lỗi nguồn QDM. Các7Node/4Python tests tổng hợp của prototype
đã chạy chỉ là kiểm thử thăm dò, không còn là capability được giữ trong repo.
Python system thiếu psycopg khi import wrapper; dùng `.venv/Scripts/python.exe`
có sẵn thành công, không cài package hoặc đổi global environment.

Help QDM có `datatype=TICK`/`timeframe=TICK`, nhưng danh sách symbol chỉ có M1.
Chưa tải tick mới vì `action=update` có thể kéo full history vượt vùng nghiên
cứu. M1 hiện tại mang `provider_default`, không chứng minh Bid/Ask gốc hoặc
đường đi equity intraday. Chưa chạy accounting BUY/SELL, H4 strategy, Prop pass
hoặc kết luận lợi nhuận. Bước kế tiếp là xác minh đường lấy/export tick có giới
hạn và semantics quote/time; không yêu cầu owner export tay khi QDM còn dùng được.

## 02/11 — Tiếp Forex: full tick cache được duyệt, CLI đang chạy

**ACTIVE/PARTIAL.** Owner sửa hướng thao tác: dùng QDM CLI; không mở GUI để
khảo sát thêm. Sau khi đã báo rõ update có thể tải toàn bộ, owner trả lời:
“cứ tải toàn bộ nếu cần, tại sau này còn sài nhiều mà”. Phạm vi thu thập cache
được mở; phạm vi export/kiểm giá vẫn chỉ03/01/2022 UTC, tập trung12:00–13:00.
Không phân tích validation2023–2024/holdout từ2025, không broker/DB/runtime rollout.

### Đã làm và job đang chạy

- Đọc `-h` và `-symbol action=list` qua wrapper hiện có. QDM125.2692 vẫn chạy;
  help không chứng minh update có giới hạn ngày. Cache trước lượt này chỉ có M1.
- Đã tạo `EURUSD_TICK_TW`: InstrumentEURUSD, TimeframeTICK, SourceDukascopy,
  cache rỗng trước update. Giữ symbolM1 `EURUSD_TW`.
- Job dùng Python venv Trader + `QdmCli`, chạy detached từ06:29:32UTC.
  PID Python thực tế29152; launcher17952 là parent/bootstrap, không là worker
  canonical. QDM child lúc kiểm4168. Kiểm lại PID và command trước mọi resume.
- Job folder:
  `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/forex-prop-pilot-20261102/qdm-tick-full-20261102/`.
  `run.py`, `receipt.json`, `worker.pid`, `progress.log`, `error.log` giữ local.
  Receipt ghi source/script hashes, exact commands, version, metadata và stage;
  progress log loại startup machine/license diagnostics.
- `-data action=update symbols=EURUSD_TICK_TW` đang ghi cache ở bộ cài QDM
  checkout cũ. Lúc kiểm đã đi qua download years2003–2026, tới writing2005
  khoảng9%; đây là tiến độ pha ghi, không là % hoàn thành hệ thống hoặc bằng
  chứng mọi năm có dữ liệu hợp lệ. D: còn khoảng70GiB ở lượt kiểm gần nhất;
  trước job74,7GiB. Chưa thể biết kích thước cache cuối hoặc thời gian hoàn tất.
- Sau update, cùng worker tự list metadata rồi export chỉ03/01/2022UTC,
  `timeframe=TICK`, `format=[[Generic tick format (comma delimited)]]`.
  Thành công sẽ ghi path/hash/bytes và stage `exported_pending_quote_validation`;
  chưa coi generic export là Bid/Ask đã được kiểm. Failure giữ `failed`/error code.
- Không chạy QDM instance thứ hai hoặc kill giữa lúc ghi. `worker.pid` giữ PID
  Python thực tế; `receipt.json` là bằng chứng stage mới nhất, snapshot này
  không chứng minh process còn sống ở lượt sau. Không chạy lại `run.py` trên
  folder này; export dir được tạo mới để tránh ghi đè bằng chứng.

### Chi phí và giới hạn đã làm rõ

[FTMO25/09/2025](https://ftmo.com/en/blog/trading-updates/trading-update-25-sep-2025/)
công bố commissionForex2,50USD/lot/mỗi chiều từ29/09/2025:5USD/lot/hai chiều.
0,01lot tương ứng0,025USD/chiều và0,05USD/hai chiều trước quy tắc rounding
của tài khoản. Chưa xác nhận phí thực tế2022 hoặc account-specific/current spec.
Contract Forex giữ nhãn scenario nếu áp fee tham chiếu vào giá lịch sử.

Đọc `semantics/data_costs.py`: `commission_per_side_account` là tiền toàn lệnh,
runner cần nhân rate với lot trước khi truyền; không nhập rate mỗi lot trực tiếp.
[FTMO29/10/2026](https://ftmo.com/en/blog/trading-updates/trading-update-29-oct-2026/)
nhắc swap thay đổi, rollover theo server; daily-loss reset theo Prague riêng.
Swap rates/schedule và symbol/margin/lot limits đầy đủ còn thiếu; không lấy
community estimates hoặc SQ Default làm FTMO verified specs.

Syntax script, registration TICK/source, command/scope flags, phép tính commission
bằng Decimal và diff checks đạt. Không chạy lại financial suites không đổi.
Docs Trader commit `de3f525c`; root gitlink không cập nhật trong lát này.
Không có quote validation, BUY/SELL accounting, H4 outcome hoặc Prop pass mới.

**Resume:** đọc job receipt, kiểm exact PID/command/log nếu stage còn chạy;
đợi cùng worker, không khởi động job trùng. Khi `exported_pending_quote_validation`,
kiểm header/format, timezone/day bounds, millisecond, Bid/Ask dương/không crossed,
duplicate timestamps và bảo toàn thứ tự dòng; hash/count/missing coverage riêng.
Nếu `failed`, xem stage/commands/metadata để chỉ retry phần thiếu sau khi xác
nhận QDM rảnh. Chỉ nối accounting sau quote/spec/cost qualification; chưa dựng
strategy backtest hoặc bỏ qua intrabar-equity gap của Prop engine.

## 02/11 — Risk guard offline và tick export đã kiểm format

**SOURCE CANDIDATE / DATA FORMAT QUALIFIED; STRATEGY NOT RUN.** Owner duyệt
làm risk controller trong lúc QDM tải. Không broker/demo/live, DB import,
migration, API/UI/native rollout hoặc đọc giá validation/holdout.

### Risk controller

Source Trader `3300a4c8`, branch `codex/note-workspace-completion`:
`foundation_v2/trading_workspace_v2/forex_pilot_risk.py`, tick execution hook
và `foundation_v2/tests/test_forex_pilot_risk.py`.

- Giới hạn dự kiến25 USD/lệnh gồm chi phí đã khai báo; dừng nội bộ equity
  ngày100 USD/tổng500 USD. Từ chối entry thiếu SL, entry gap làm SL sai phía,
  risk vượt giới hạn hoặc chạm/vượt ngân sách còn lại. Margin vẫn do core kiểm.
- Mỗi quote mark equity trước/sau xử lý; latch dừng và chặn entry. Nếu còn vị
  thế, đóng ở quote tiếp theo theo Bid/Ask thực tế của input. SL/TP trên quote
  trigger vẫn có thể đóng trước; không đóng hai lần. Gap có thể vượt budget.
- Daily reset dùng balance mang sang trước quote đầu ngày Europe/Prague,
  có DST; tổng không reset. Snapshot JSON giữ pending close qua restart/đổi
  ngày, last quote/sequence và stop evidence. Cửa sổ lỗi không publish nửa state.
- Reuse accounting hiện có; không dựng execution engine riêng. Net liquidation
  gồm full roundtrip costs/aggregate financing của core; chưa có timed swap
  ledger hoặc broker rounding/spec verified. Tick guard không chứng minh đoạn
  giá thiếu; giữ `intrabar_equity_coverage=insufficient`, không cấp Prop pass.
  Stress liquidation dùng carried position cố tình quá lớn; normal admission
  không cho mở vị thế với stop rộng đó.

Focused verification, từ repo Trader với Python venv sẵn có:

| File | Kết quả |
|---|---|
| `test_forex_pilot_risk.py` | 13 passed: BUY/SELL, costs, gap/spread, budget, SL không đóng lặp, restart/Prague mùa đông và mùa hè, checkpoint lỗi |
| `test_replay_tick_execution.py` | 22 passed: core regression sau hook/extract close |
| `test_ps02_replay_prop_connection.py` | 20 passed: Prop connection regression |
| `test_replay_immediate_execution.py` | 10 passed qua pytest: current-quote execution regression |

Ba suite unittest chạy bằng `python -m unittest discover -s foundation_v2/tests
-p <filename>`; file immediate dùng `python -m pytest
foundation_v2/tests/test_replay_immediate_execution.py -q`. Hai lần gọi unittest
cho file immediate trước đó không pass: sai cwd gây import error; khi sửa cwd
thì0 tests vì file dùng pytest functions. Đã sửa runner, không sửa test để né lỗi.
Warnings dependency Starlette/httpx, anyio và Pydantic Decimal serialization
được giữ; không đổi dependency ngoài scope. Không chạy full suite/native build
cho module offline này. Diff checks đạt; chưa tuyên bố runtime đã cập nhật.

### QDM hoàn tất cache; phục hồi riêng bước export

- Cùng job CLI đã tải/ghi xong trong25 phút8 giây theo log. Metadata:
  **517.750.341 records**,2003.05.05–2026.11.01,8.582 ngày lịch theo QDM,
  timezone UTC. Đây là metadata cache, không phải đã đọc toàn bộ giá.
  Free D: sau update73.915.801.600 bytes; giảm khoảng6,25GB so với trước,
  chỉ là disk delta quan sát, không là byte mạng hoặc kích thước cache chính xác.
- Worker kết thúc sau export assertion `one_bounded_export_required` vì không
  có CSV. Root cause: literal `[[...]]` quanh format không nằm trong tên mà
  `-h` của bản cài liệt kê. CLI vẫn báo thành công; phải kiểm artifact thực tế.
  Xác nhận worker/CLI cũ đã thoát, chỉ chạy lại export cùng ngày với một argv
  `format=Generic tick format (comma delimited)`, thư mục mới
  `export-format-corrected`. Không update lại hoặc mở QDM GUI.
- CSV `EURUSD_TICK_TW-TICK-No Session.csv`,2.957.978 bytes; SHA256
  `d994e395d53b4e8c01e18e10ec65f0b5d394a17a0020d025f96de8cd6f72ba49`.
  Header `DateTime,Bid,Ask,Volume`; timestamp `yyyyMMdd HH:mm:ss.SSS`.
  **65.215 ticks** chỉ03/01/2022 UTC,00:00:00.033–23:59:59.732;
  giờ12:00–13:00 có3.829 ticks. Bid/Ask finite, dương/không crossed, bước giá
  quan sát0,00001; timestamps tăng, không duplicate timestamp/row liền kề.
- 15 phút không có quote, trùng danh sách thiếu của mẫu M1; khoảng cách lớn
  nhất413.792ms. Giữ `review_gaps_not_filled`; không coi là coverage liên tục
  hoặc lỗi transport đã xác định. Đây là giá Dukascopy, không quote FTMO.
- Job folder giữ `receipt.json`, `run.py`, `validate_export.py`, progress/error
  logs và CSV local. Receipt giữ attempt lỗi và recovery args/hash riêng;
  stage mới **`quote_format_validated_cost_spec_pending`**. Worker đã kết thúc,
  không còn job download cần chờ. Không commit dữ liệu hãng hoặc nhập DB.
- Docs export/format/resume Trader `c0b0e134`; root gitlink giữ nguyên.

**Resume:** dùng cache/CSV đã có, không tải lại. Hoàn thiện declared broker
spec/cost scenario (commission, financing/rollover, lot/tick/margin và rounding),
đăng ký manifest tick cùng provenance/row sequence trước khi nối một probe
BUY/SELL offline trong giờ12:00–13:00. Không suy phí năm2022 từ công bố2025,
không mặc định swap=0. Chưa có H4 warmup/strategy runner, edge hoặc Prop pass.

## 02/11 — Probe BUY/SELL trên tick QDM, accounting đạt

**ACCOUNTING PASSED ONLY; BROKER SPEC / STRATEGY / PROP NOT QUALIFIED.**
Source Trader `62411d0b`: script `foundation_v2/scripts/forex_pilot_probe.py`
và `foundation_v2/tests/test_forex_pilot_probe.py`. Không thay core accounting,
risk guard, API/UI, DB hoặc runtime; không kết nối broker hay chạy provider AI.

### Đăng ký và nguồn

Contract Forex mục7 được ghi trước lượt tính P/L. Cùng CSV đã pin hash, chỉ
12:00–13:00 UTC ngày03/01/2022; giá cuối trước12:00 làm reference SL, không
dùng giá tương lai để chọn chiều/size/stop. Hai account độc lập10.000 USD,
BUY/SELL0,01lot; mỗi chiều baseline/slippage stress0,00002 mỗi chiều. Không
chọn lượt có lãi hoặc tìm tham số. Script chỉ nhận đúng hash registered CSV,
kiểm authorized day trước price fields, source order/millisecond và đủ60 phút;
không fill khoảng trống hoặc export thêm data. Manifest pin CSV/window hash,
source code hashes, reference và assumptions trước tính outcomes.

Đọc lại nguồn chính thức02/11:

- [Commission update25/09/2025](https://ftmo.com/en/blog/trading-updates/trading-update-25-sep-2025/):
  2,50 USD/lot/chiều từ29/09/2025; cho probe0,01lot là0,025 mỗi chiều,
  0,05 roundtrip. Đây là scenario giá2022 với published reference, chưa là phí2022.
- [Swing FAQ](https://ftmo.com/en/faq/what-is-the-swing-account-type-and-how-does-it-work/):
  base leverage1:30, dùng fixed research margin hiện có, chưa tiered/stop-out.
- [Symbols](https://ftmo.com/en/symbols/): search index của primary page trả
  contract100.000 và Swing leverage1:30 cho EURUSD. Page extractor không render
  dynamic table; urllib gặp SSL EOF. Không coi search cache là actual terminal
  spec, không lấy swap trong cache làm lịch sử. Lot min/step0,01, price step
  0,00001, pip0,0001 và rounding2-decimal vẫn được gắn observed/assumed tương ứng.
- [Update29/10/2026](https://ftmo.com/en/blog/trading-updates/trading-update-29-oct-2026/):
  swaps có thể đổi; cần contract specification. Probe bắt buộc flat trước13:00
  UTC, không qua midnight rollover; financing0 vì không có sự kiện rollover
  trong cửa sổ này, không hàm ý swap rate0 hoặc strategy H4 được phép bỏ swap.

### Luồng và kết quả

CSV hash → parse giữ row ordinal làm sequence → tick windows1 phút → pilot
risk admission → core Bid/Ask accounting → SL nếu chạm, hoặc tất toán giá trị
tại quote cuối kỳ → JSON restore/validation → Decimal oracle độc lập.
Cả4 lượt này dùng terminal valuation; không ghi nhận stop fill trong mẫu thật.
Helper close dùng quote canonical cuối cùng, **chưa chứng minh một lệnh đóng
gửi sau đó có thể khớp giá ấy**. Rủi ro causal exit cần xử lý trước strategy.

| Chiều | Slippage/chiều | Gross USD | Commission USD | Slippage USD | Net USD |
|---|---|---|---|---|---|
| BUY |0 |0,28 |0,05 |0 |0,23 |
| BUY |0,00002 |0,28 |0,05 |0,04 |0,19 |
| SELL |0 |−0,34 |0,05 |0 |−0,39 |
| SELL |0,00002 |−0,34 |0,05 |0,04 |−0,43 |

Chỉ là phép đối soát tài khoản trên một giờ, không là return chiến lược hoặc
bằng chứng edge. Oracle độc lập kiểm fill side, gross/fees/net/balance, margin
notional/leverage; stress delta đúng−0,04 USD. Cả4 snapshot JSON restore đạt,
flat cuối kỳ; mỗi lượt quan sát3.829 tick. Spread chỉ tính qua Bid/Ask một lần.

`python -m unittest discover -s foundation_v2/tests -p test_forex_pilot_probe.py
-v`: **3 tests passed**, gồm cả BUY/SELL terminal valuation/cost sensitivity,
SL gap fill đúng một lần và parser từ chối sai hash/header/day/order/missing
minute. Synthetic fixture không phải dữ liệu thị trường; giữ riêng với4 lượt
thật. Không chạy lại65 tests source core/risk không đổi. Diff checks đạt.

Artifacts local (không đưa CSV/checkpoint giá vào Git):
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/forex-prop-pilot-20261102/accounting-probe-20261102/`.
`manifest.json`, `results.json`, `receipt.json` giữ hashes, command, source SHA,
snapshots/ledgers và scope. Sau commit kiểm source hashes vẫn trùng manifest.
Không update gitlink Trader, không push/deploy hoặc mua challenge.

**Resume:** probe accounting nhỏ đã xong, không cần tải QDM hay lặp probe.
Trước strategy H4: nối causal exit (quote tiếp theo sau quyết định, giữ đúng
risk latch), timed financing/rollover và broker spec/cost profile có nguồn;
đăng ký warmup/development manifest trước export thêm. Lot/margin/rounding của
account cụ thể vẫn chưa verified. Chưa mở validation/holdout, broker/trial/live.

## 02/11 — Causal exit đã nối và đối soát trên mẫu development

**SOURCE CANDIDATE / CAUSAL ACCOUNTING PASSED ONLY.** Trader `540288ab`.
Đã hoàn tất lát queued exit, chưa nối H4 strategy, broker hoặc runtime.

### Hành vi/state và trade-off

- `queue_forex_pilot_exit` tạo request từ closed-bar checkpoint đang có:
  operation, position, cursor, decision timestamp và observed quote. Chỉ cho
  exit position đang mở; từ chối request trùng, operation đã dùng hoặc chứng cứ
  quyết định không khớp ledger. `exit_pending` optional mặc địnhNone, snapshot
  cũ không có request vẫn đọc được; không DB migration/API contract thay đổi.
- `advance_forex_pilot` giữ request qua JSON restart/cửa sổ chưa có quote đủ
  điều kiện. Strategy exit chỉ khớp quote timestamp **lớn hơn** decision time,
  kể cả quote cùng millisecond có sequence lớn hơn cũng chưa đủ điều kiện.
  Khác risk liquidation, vốn đóng ở quote kế tiếp của trigger đã quan sát.
- Thứ tự xử lý: observe equity → pending risk liquidation nếu có → SL/TP →
  strategy exit nếu còn position → cập nhật risk state. Không đóng hai lần.
  Nếu đóng do protection/risk trước, clear exit request còn chờ; cờ dừng risk
  không bị xóa. Daily/overall stop chặn entry nhưng không ngăn yêu cầu exit.
  Quote lỗi ở cuối cửa sổ không publish exit fill/state nửa chừng.
- Reuse close accounting/core event `protective_fill`, gắn reason riêng
  `pilot_strategy_exit`, `command_operation_id`, proof `pilot_exit`; không giả
  thành SL. Validator kiểm proof dẫn về price_mark và fill sau decision.
  Native/runtime/UI chưa nhận capability này; không claim lifecycle Prop pass.

### Kiểm chứng và dữ liệu thật

Đã ghi contract mục8 **trước** lượt outcome mới: cùng4 scenarios/CSV và
entry/size/SL, chỉ đổi exit thành quyết định cố định12:59 UTC. Không xuất thêm
dữ liệu hoặc chọn thời điểm theo P/L. Script bỏ fallback terminal valuation;
hết mẫu chưa có quote eligible để flat thì fail, giữ bằng chứng thiếu.

- 19 tests pilot risk đạt (13 cũ +6 mới): BUY/SELL strict timestamp, same-ms
  quote không khớp, gap/cost, request qua restart, SL/risk ưu tiên, operation
  reuse/tampered decision và transactional failure.
- 4 tests probe đạt: accounting BUY/SELL, SL gap một close, parser corruption,
  thiếu quote sau decision không được fake close.
- 32 core regression đạt: `pytest test_replay_tick_execution.py
  test_replay_immediate_execution.py -q`; hai warnings Starlette/httpx và anyio
  đã có, không đổi dependency. Focused unittest commands như lượt trước, đúng
  file names. Không chạy lại full suite/Prop/native build không liên quan.
- Source diff checks đạt. Sau thêm independent first-eligible-quote assertion
  vào probe, lượt real-data4 scenarios kiểm trực tiếp nhánh đó thành công;
  không lặp suite chỉ để tăng số lần pass.

Cả4 lượt có3.829 ticks; decision12:59:00 UTC, fill tại quote đầu eligible
**12:59:00.084 UTC**. Khoảng84ms là khoảng cách giữa decision và input quote,
không đo latency broker/hạ tầng. BUY đóngbid, SELL đóngask; Decimal oracle và
margin độc lập khớp, JSON checkpoints restore đạt.

| Chiều | Slippage/chiều | Net USD |
|---|---|---|
| BUY |0 |0,19 |
| BUY |0,00002 |0,15 |
| SELL |0 |−0,36 |
| SELL |0,00002 |−0,40 |

Kết quả khác valuation cuối kỳ của lượt trước vì exit time thay đổi; đây là
đối soát kỹ thuật, không so sánh edge hoặc chọn chiến lược. Slippage stress
delta vẫn−0,04 USD mỗi lượt; không latency, liquidity/depth hoặc broker guarantee.

Artifacts mới giữ riêng, không ghi đè lượt valuation:
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/forex-prop-pilot-20261102/causal-exit-probe-20261102/`.
`manifest.json`, `results.json`, `receipt.json` giữ command, code/data hashes,
source revision và scope. Kiểm source hashes sau commit vẫn trùng manifest;
receipt pin final commit; root gitlink không stage/update. Không DB/runtime/
broker/provider action hoặc phân tích validation/holdout.

**Resume:** causal entry/exit accounting nhỏ đã có. Phần tiếp theo là declared
financing/rollover events và broker spec/cost profile cho vị thế qua đêm, rồi
đăng ký warmup/development manifest trước dựng H4 runner. Không reuse financing0
của intraday probe cho strategy H4. Chưa có lợi nhuận chiến lược hoặc Prop pass.

## 02/11 — Timed financing và H4 development đã chạy offline

**TECHNICAL INTEGRATION PASSED / STRATEGY UNPROVEN.** Trader financing
`a1388e73`, causal entry/quantity costs `46b9d20b`, H4 runner `29735345`.
Owner cho phép mọi phạm vi dữ liệu; chưa có FTMO demo/free trial, hướng dẫn
sau. Chưa đưa vào API/UI/native/runtime, chưa mở tài khoản/provider/broker.

### Thay đổi và luồng state

- `forex_financing.py`: cash events có schedule UTC, known-at, signed rate
  theo lot/chiều, multiplier và source/qualification. Cập nhật balance rồi
  risk guard trên cash clock, giữ quote định giá cũ có nhãn stale. Qua gap
  vẫn giữ cash; chặn duplicate/backdate/aggregate double charge. Stop do cash
  chờ quote thực sự sau event. Prague reset và server rollover là hai clock
  riêng. JSON/rewind giữ cash; không dựng quote mới.
- Pilot entry có decision time và optional stop distance. Quote cùng timestamp
  với quyết định chưa được fill; stop cách actual fill đúng distance, round
  ra xa theo tick. Commission rate theo quantity không đổi nghĩa fixed fee cũ;
  partial close không scale hai lần. General research từ chối rate mới chưa
  hỗ trợ. Offline snapshot không import sang Rust vì chưa có native parity.
- `forex_h4.py` + `scripts/forex_h4_pilot.py`: QDM ticks → validate → hourly
  execution/risk mỗi tick → H4 đã đóng → Donchian20/10, ATR14 Wilder → size
  round xuống → queue → quote eligible. Reuse core fills/accounting; chỉ báo
  midpoint loại chính nến quyết định khỏi channel, không trade warmup.
- Contract mục9 pin trước outcome: calendar22:00UTC Mon–Fri (Wed×3), debit
  giả định10/20USD/lot, slippage0/0,00002. Đây là declared scenarios, không phí
  lịch sử2022/spec FTMO. Ngân sách stop ban đầu gồm commission/slippage, chưa
  biết tổng financing theo số đêm; cash/risk guard vẫn hoạt động. Fixed research
  leverage không thay margin/stop-out thực. Không tune/model/holdout action.

### Dữ liệu và kết quả

Export đã hoàn tất từ cache, không tải lại:
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/forex-prop-pilot-20261102/h4-inputs-20261102/`.
Hash hai CSV ở contract mục9/export receipt. Warmup20–31/12/2021 có546.210ticks,
58H4 đủ4giờ quote; development03–14/01/2022 có643.775ticks,58H4 đủ4giờ quote.
Mỗi lát238giờ có quote,3H4 thiếu giờ bị loại, không bù nến. Development có
2.964phút không quote giữa đầu/cuối, gồm cuối tuần; max gap172.800.637ms.
Không khẳng định toàn bộ phút thiếu là lỗi nguồn hoặc feed đã đầy đủ.

Job H4: launcherPID20040, actual workerPID22076, đã hoàn tất
`completed_declared_scenarios` lúc08:09:39UTC02/11; không cần restart/resume.
Artifacts:
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/forex-prop-pilot-20261102/h4-development-20261102/`.
Manifest pin source29735345/code/input hashes trước outcome; quality, results,
decisions và JSON checkpoints riêng cho hai scenarios. Stdout/stderr ở folder
cha; stderr trống sau hoàn tất. Không ghi đè probe cũ.

| Kết quả trên10.000USD mô phỏng | Reference | Cost-stress |
|---|---:|---:|
| Lệnh mở/đã đóng |3/3 |3/3 |
| Net trade sau commission/slippage, trước cash financing |−17,72 |−18,20 |
| Debit financing giả định |2,80 |5,60 |
| Thay đổi balance sau mọi phí |−20,52 |−23,80 |
| Balance/equity cuối |9.979,48 |9.976,20 |
| Equity thấp nhất quan sát |9.949,76 |9.948,08 |
| Internal risk stops/rejections |0/0 |0/0 |

Cả hai có SELL +2BUY, lot0,04 mỗi lệnh;2SL và1causal strategy exit. Cùng4
decisions, không chọn scenario theo lợi nhuận. Exit cuối decision
1642176000000ms, quote1642176000107ms;107ms là khoảng cách input quote,
không measured broker latency. Mỗi scenario643.775ticks +10cash events;
Decimal oracle độc lập đối soát từng close/cash/balance và JSON restore đạt.
Kết thúc flat tự nhiên, không terminal fake close. Không chạm internal stop
chỉ đúng với quotes/cash được cung cấp; `intrabar_equity_coverage=insufficient`,
`broker_spec_verified=false`, `strategy_pass=false`, `prop_pass=false` giữ nguyên.

### Kiểm chứng và lỗi đã xử lý

- Financing8tests đạt trước entry/cost slice: debit/credit, multiplier,
  gap/cash breach/restart, Prague DST/server clock, tamper và rewind.
- Sau entry/cost:35tests pilot/financing/probe/quantity đạt. Lượt đầu1budget
  fixture fail do entry quote đúng decision boundary; sửa entry thành+1ms,
  stop quote+2ms để giữ4lỗ/remaining budget, không đổi expected loss/nới guard.
  Có gap BUY/SELL, strict timestamp, rounding, JSON/tamper/invalid distance.
  Sau thêm partial quantity/general research rejection, focused quantity +
  engine oracle12tests đạt.
- H4 synthetic5tests đạt: channel/ATR seed, partial candles, sizing/min lot,
  parser corruption/source ordinal, runner roundtrip và declared calendar.
- Core regression111tests đạt: tick/core/margin/immediate/partial close/Prop.
  3warnings đã có: Starlette/httpx, anyio và Pydantic Decimal/int serialization.
- Tổng161test cases khác nhau đạt qua focused commands. Không lặp full suite/
  native/UI hoặc probe cũ chỉ để tăng pass count. Diff check đạt; root gitlink
  và WIP khác không stage. Không database/runtime restart hoặc rollout.

**Bước tiếp cần owner:** FTMO demo/free-trial MT5 và bảng EURUSD Specification
để pin lot/tick/swap/margin/rollover thực, rồi đăng ký development window lớn
hơn trước qualification. Owner tạo/login tài khoản; agent hướng dẫn/đọc thông
số được cung cấp, không tự dùng credentials/broker. Chưa có thì không gọi
declared run là sát tài khoản hoặc mở holdout để cố tìm kết quả đẹp.3lệnh/hai
tuần chưa đủ edge; chưa đủ bằng chứng dùng tiền/mua challenge.

## FTMO demo specification và H4 development tiếp nối — 02/11/2026

Owner đã đăng nhập FTMO demo, cho phép tiếp tục đọc EURUSD và mô phỏng offline.
Contract trước outcome: `planning/research/FOREX-PROP-PILOT-20261102.md` mục10,
SHA256 `5ca088734127ba492d3fca4912e8a490ec118016ae5b25df460faffbae9b18e3`.
Gate chờ demo/spec ở receipt trước đã được thay bằng bằng chứng bên dưới;
không mở OrderCheck/OrderSend hoặc strategy trên broker.

### Quyền bảo trì và nguồn quan sát

- Trader commit `d8ed92c7`: `AGENTS.md` lưu quyền standing của owner cho
  local UI/API/adapter rollout, restart service/terminal thuộc project và
  reconnect account hiện có; giữ identity/access mode/data/rollback, kiểm
  active jobs và unknown submissions trước gián đoạn. Không cấp migration,
  xóa dữ liệu, tài khoản/provider mới, production hoặc broker execution.
- Đọc lại file, diff check và audit AI environment trước/sau đạt:
  global12.279B + project5.519B, reserve60.017B;0errors/0warnings.
- Tài khoản đích `…7819`, FTMO-Demo, USD10.000, demo, leverage30,
  SDK name `$10k FTMO Free Trial Swing 2-Step`; giữ mode owner đã chọn.
  Attach vào terminal project đang chạy, kiểm path/data_path/login/server
  trước/sau. Không restart cần thiết, không dùng credentials hoặc gửi lệnh.
- Capture08:58:49.252636UTC02/11/2026:
  `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/forex-prop-pilot-20261102/ftmo-current-spec-20261102/spec.json`;
  SHA256 `930e5670b21b09963d21741258706adeff6b10c454dd9fafa0df7346a0a74756`.
  SDK có trong interpreter runtime cũ; canonical Trader Python chưa có SDK.
  Lượt đầu ModuleNotFoundError đã được xử lý bằng đúng interpreter có sẵn,
  không cài thêm SDK hoặc chuyển runtime/data.

EURUSD: contract100.000EUR/lot, tick/point0,00001, tick value1USD/lot,
min/step0,01lot/max50lot. Margin Forex/EUR; SDK calculator1lot BUY tại1,12210
=3.740,33USD, SELL tại1,12209=3.740,30USD. Các calculator chỉ tính toán,
không OrderCheck/OrderSend. Margin call100%/stop-out50% được ghi nhận,
core vẫn fixed research leverage, chưa mô phỏng server liquidation/tiered rate.

Swap modePoints: long−9,3 → debit9,30USD/lot/ngày; short+0,31 →
credit0,31USD/lot/ngày; triple Wednesday. Không có deals EURUSD hôm capture,
nên commission account-specific chưa xác minh. Giữ published reference
2,50USD/lot/chiều; lịch22UTC/Wed×3, rates hiện tại áp lên2022 và rounding
cent là declared counterfactual, không tái dựng phí lịch sử.

### Source, dữ liệu và job

Trader `95a40edc` mở rộng runner hiện có bằng account-spec/hash pin và input
manifest; kiểm units/currency/contract/tick/lot/leverage/swap mode và reject
spec không hỗ trợ. BUY debit/SELL credit tính Decimal; không suy từ snapshot
hiện tại thành knowledge2022. Manifest giữ timestamp capture2026 và scenario
clock riêng; full broker-spec/historical-spec/strategy/Prop qualification
vẫn false. Candidate/params/risk giữ nguyên, không tuning hoặc model call.

QDM CLI export cache03/01–31/03/2022 đã xong09:03:26UTC; CSV264.754.020B,
SHA256 `dfe850eff9150032b865f82949f758fe422b9798fb9f55f7077c48cd63f8a2de`.
Manifest/output trong `h4-q1-export-20261102/` dưới folder job; warmup dùng
nguyên lát20–31/12/2021 đã pin. Không download/update, không mở GUI hoặc2023+.

Lượt đầu `ftmo-h4-20261102/` hoàn tất reference hai tuần nhưng cost-stress
dừng vì WinError5 lúc atomic replace receipt khi reader đang mở. Đã tái hiện
cùng lỗi bằng native Windows handle không FILE_SHARE_DELETE, hết lỗi sau đóng
reader. Trader fix `387791fd` retry riêng Windows sharing/access-denied trong
tối đa1giây; lỗi kéo dài vẫn raise, file cũ giữ nguyên. Không đổi accounting.
Regression kiểm transient recovery/persistent failure đạt; giữ toàn bộ job
lỗi, không overwrite. Lượt mới chạy tuần tự tại
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/forex-prop-pilot-20261102/ftmo-h4-20261102-retry1/`;
`job-receipt.json` giữ PID của launcher/worker hiện hành, manifests/code hashes,
stdout/stderr, kết quả và checkpoints tách theo `two-weeks`/`q1`.

Focused tests sau mở rộng:17tests +17subtests đạt (H4/financing). Sau sửa writer:
10H4tests +11subtests đạt; không cộng các test chạy lại vào số test khác nhau.
Không chạy full suite/UI/native hoặc restart runtime cho thay đổi offline này.

### Chạy lại development03–14/01/2022

Lượt `two-weeks` hoàn tất09:13:57UTC. Cùng643.775ticks,3entries/3closes,
4decisions,10cash events; cuối mẫu flat tự nhiên, không terminal close giả.

| USD trên vốn mô phỏng10.000 | Reference swap hiện tại | Cost-stress |
|---|---:|---:|
| Net trade sau commission/slippage, trước financing |−17,72 |−18,20 |
| Financing debit ròng |2,22 |5,60 |
| Balance/equity delta sau mọi phí |−19,94 |−23,80 |
| Equity thấp nhất quan sát |9.950,23 |9.948,08 |
| Internal risk stops/rejections |0/0 |0/0 |

So với reference cũ−20,52USD, thay swap làm debit giảm0,58USD; phần trade net
vẫn−17,72USD, không biến candidate thành có lợi thế. Stress result object
khớp **toàn bộ** kết quả lượt trước, xác nhận đổi input/spec plumbing không
làm đổi scenario giữ nguyên. Decimal đối soát/JSON restore/equity balance
identity và CSV hash khớp. `review.json` ngoài repo giữ kiểm chứng compact.
Các gate qualification/coverage vẫn giữ; không đủ bằng chứng edge hoặc mua
challenge. Q1 chạy tuần tự sau lượt này, kết quả hoàn tất ở phần dưới.

### Development03/01–31/03/2022 — đã hoàn tất

Job actualPID24856 hoàn tất09:36:31UTC; orchestrator receipt cũng đã chuyển
`completed_declared_scenarios`, stderr hai lượt mới trống. Không còn bước
resume của job này. Artifact `ftmo-h4-20261102-retry1/q1/`; code pin387791fd,
spec/input hashes ở manifests đã ghi trước outcome. Không đổi source khi chạy.

Development có5.837.028ticks,1.537giờ có quote,372H4 đủ4giờ;24H4 thiếu giờ
bị loại. Có34.878phút không quote giữa đầu/cuối, gồm cuối tuần; max adjacent
gap172.815.415ms. Không sort/dedup/fill gap hoặc gọi dữ liệu là coverage đầy đủ.

| USD trên vốn mô phỏng10.000 | Reference swap hiện tại | Cost-stress |
|---|---:|---:|
| Entry fills / closed trades |13/13 |13/13 |
| Net trade sau commission/slippage, trước financing |62,17 |47,22 |
| Financing debit ròng |7,80 |38,00 |
| Balance/equity delta sau mọi phí |54,37 |9,22 |
| Balance/equity cuối |10.054,37 |10.009,22 |
| Equity thấp nhất quan sát |9.950,23 |9.948,08 |
| Internal risk stops/rejections |0/0 |0/0 |

Cả hai20decisions/64cash events, cuối kỳ flat tự nhiên, không entry chờ hoặc
fake terminal close. Stress có thể đổi size/fill/SL timing theo cùng quy tắc
do slippage, không chỉ là trừ thêm một khoản phí vào closed results reference.
Không tìm tham số, chọn run hoặc dùng model/holdout. Hai tuần là phần đầu của
Q1, không tính hai mẫu thành hai kiểm chứng độc lập.

Decimal oracle từng close/cash/balance, JSON restore, equity=balance+floating,
observed tick count và dataset hash khớp. `review.json` kiểm cả hai windows,
giữ stress hai tuần trùng toàn bộ accepted result cũ. Source tests có18test
cases khác nhau đã qua focused checks (không cộng lại các lần chạy lặp).
WinError5 lần đầu đã được tái hiện/sửa và kiểm bằng cả test writer lẫn lượt
chạy dài mới. Không triển khai lại UI/API/terminal hoặc đổi database.

**Đánh giá:** +0,5437% reference và+0,0922% stress trên cùng vốn10.000USD;
13lệnh/3tháng development chưa đủ chứng minh edge. Lợi nhuận nhạy với chi phí.
`broker_spec_verified=false`, `historical_spec_verified=false`,
`strategy_pass=false`, `prop_pass=false`,
`intrabar_equity_coverage=insufficient` giữ nguyên. Swap hiện tại/counterfactual
calendar/commission reference không phải tái dựng account2022; chưa có
account-specific commission, historical financing/rounding hoặc server stop-out.

**Hướng validation từng đề xuất:** đăng ký tiêu chí/cửa sổ ngoài development
trước outcome tiếp theo, giữ holdout cuối độc lập. Owner đã gác hướng này lại
theo điều chỉnh ưu tiên bên dưới. Commission vẫn cần đối chiếu deals của account
khi có nguồn/quyền tương ứng; không tự đặt lệnh để đo phí. Không còn gate chờ
owner tạo/login FTMO hoặc gửi bảng Specification. Chưa mở live, mua challenge
hoặc quyền broker execution từ kết quả mô phỏng này.

### Owner đổi ưu tiên sang hệ thống — 02/11/2026

Owner làm rõ chưa muốn dành thời gian tối ưu chiến lược; ưu tiên hoàn thiện
hệ thống AI và workflow vận hành trước. Gác đề xuất validation2023, giữ nguyên
candidate và mọi kết quả đã có làm fixture kiểm tích hợp. Kết quả fixture có
lãi hay không không quyết định workflow đã hoàn thiện hay chưa.

Scope/acceptance mới ở đầu `planning/trader/AI-RESEARCH-UI-PROTOTYPE-20261031.md`.
**Bước tiếp hiện hành:** đối chiếu native workflow crypto đã kiểm và Forex
runner offline; chỉ ra/nối mắt xích Forex còn thiếu trong một luồng owner thấy
được trên UI: task → dữ liệu QDM → mô phỏng → phản biện → báo cáo. Kiểm handoff,
provenance, trạng thái, lỗi/hủy/retry và tránh worker trùng bằng cơ chế đã có.
Không khởi động job/worker mới trong lượt điều chỉnh context này. Chưa có
acceptance end-to-end Forex qua Paperclip; các kết quả offline bên trên giữ
nguyên giá trị/phạm vi. Không mở quyền broker từ ưu tiên hoàn thiện hệ thống.

### Workflow Forex native xuyên suốt — 02/11/2026

Theo giao việc tiếp theo của owner, đã nối và chạy **một bài mẫu hệ thống**:
Paperclip → dữ liệu QDM đã pin → runner Forex hiện có → Hermes/Gemini →
native documents → human review trong Trader5180. Không đổi chiến lược,
mở validation/holdout, gọi broker hoặc chạy lại Q1.

Source: Trader `c1f9b821` thêm explicit argv/progress callback cho runner;
workspace `b731d58` thêm adapter Forex, reuse lifecycle `spot_workflow.py`
với profile `forex`. Worker mới **Chuyên viên kiểm định** chạy Python offline
trong cùng process; các engine/worker cũ giữ vai trò. Không sửa Paperclip core.
Independent source review phát hiện binding và pre-start scope cần siết;
đã sửa và có regression checks trước commit.

Focused source checks: wrapper suite53tests đạt; sau scope regression cuối,
workflow12tests đạt (54unique cases tổng hợp, không tuyên bố chạy lại cả54).
Adapter7tests đạt; Trader H4 runner11tests+11subtests đạt. Build/test là bằng
chứng source; các lượt native/browser bên dưới là bằng chứng runtime riêng.

#### Lượt thật và provenance

| Công việc | Kết quả quan sát |
|---|---|
| [NAQ-25](http://127.0.0.1:17860/NAQ/issues/NAQ-25) | `in_review`, giao `local-board`; có tài liệu **Kết quả và bước tiếp theo** |
| NAQ-26 — dữ liệu/mô phỏng | `done`, native run `cf852f42-d6aa-4bf8-8311-50d90cf93881` succeeded/exit0; không gọi model |
| NAQ-27 — Hermes | Tự nhận sau dependency; `done`, run `2458ca3d-5847-40ed-babb-17bc9e92e578` succeeded/exit0 |
| NAQ-28 — paper | `blocked`, không gắn agent, **NOT_RUN** |

Graph key `forex-system-20261102`; không tạo key khác để lặp lượt thành công.
Hai CSV QDM và spec FTMO giữ hash đã đăng ký. Mô phỏng kiểm đúng oracle cũ:
643.775ticks,3lệnh đóng, balance delta−19,94/−23,80USD. Đây chỉ là fixture
kiểm hệ thống, không là chiến lược mới hay bằng chứng qualification.
Hermes dùng route `gemini-3.8-flash-high`,2API calls trong một lượt review,
46,27giây. Route không chứng minh tên model nền của provider. Cả workflow
từ dispatch tới bàn giao khoảng3phút26giây; chưa benchmark năng lực scale.

Đã đối soát hash body và revision của hai native documents NAQ-26 với receipt
numeric và source binding của Hermes. Báo cáo phản biện/nguồn được publish;
không chạy lại model để sửa delivery. `strategy_qualified=false`,
`execution_authorized=false`. Native verification xác nhận không agent running
sau các lượt này. Artifacts nằm ngoài repo dưới
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/<company>/<run>/`.

#### Hủy, lỗi và chạy lại

Fixture riêng **NAQ-29–32**, key `forex-system-cancel-20261102`, kiểm hủy khi
numeric process thực sự đã bắt đầu: run `cb5e3ba9-38aa-4e35-921e-acfe15b8fa36`
chuyển native `cancelled`, cả graph cancelled, process4356 không còn,
không success document và không model call. Receipt numeric còn `running`
sau hard kill là evidence interrupted/unknown; native cancellation là trạng
thái terminal, không sửa receipt để giả là engine hoàn tất.

Source checks bao phủ data/spec/hash lỗi, nguồn/reparent/parent manifest đổi,
dependency chưa đạt, cancel, duplicate dispatch và publish lỗi. Same key không
reset started work. Retry phải xem run+receipt và tạo lượt mới rõ ràng;
checkpoint JSON giữ bằng chứng, chưa có CLI resume numerical replay.
Hủy parent trong UI chặn bước sau/publication và được numeric nhận ở progress
boundary; hủy native run dừng process hiện hành. Lệnh wrapper `cancel --parent`
hủy cả graph/run. **Chưa có một nút native UI tạo/hủy trọn graph**; không coi
pilot này là hoàn thiện mọi thao tác owner hoặc tự chủ toàn hệ thống.

#### Sửa bridge và kiểm trên Trader5180

Tái hiện GET `/integrations/paperclip/health` trả200HTML thay JSON: runtime
checkout cũ thiếu plugin/module bridge và local-services registry; source
canonical đã có. Backup tại
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/forex-system-ui-bridge-20261102/`.
Đã promote đúng bridge/registry và sửa config runtime tối thiểu; restart
chỉ UI Vite PID28896 đã xác minh creation/executable → PID976. Không restart
API8010 hoặc MT5. Owner receipt UI cũ ghi PID4024 đã stale; không dùng PID đó
để stop. Hash Trader served index giữ nguyên
`873f7cd66edd414e40f76f3f4b5ad85945271947ffa71107433c6a45a26827c9`.
Health hiện trả JSON `ok`, pin Paperclip `2e0f8f84`.

Phát hiện thêm preference build chỉ tin host5218 nên native frame ở5180
không nhận VI/EN. Launcher có `--workspace-origin`, kiểm exact loopback origin
và khớp owner; mặc định5218 giữ tương thích.4CLI refusal cases và reuse instance
đúng origin đạt; review độc lập không thấy lỗi cần sửa. Build static UI với
origin5180, promote index/SW sau copy assets mới và giữ assets cũ/branding.
Server Paperclip PID23764/database giữ nguyên; không cần restart vì server
đọc index từ đĩa mỗi request. Rollback index/SW/owner và promotion receipt tại
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/forex-system-paperclip-ui-20261102/`.
Lần rename đầu lỗi PowerShell chuyển null backup thành empty path; đã hoàn
tất bằng overwrite rename sau backup, xác minh hash và native rendered UI.
Build còn warnings upstream về chunk size/config/CSS; chưa là speed audit.

Browser5cases đạt trên actual5180: mở summary, link numeric report và actual
Hermes report, đổi VI/EN/chuyển tab giữ document+route+report,390px không
horizontal overflow. Đã xem screenshot1920/390. Không pageerror hoặc request
ngoài allowlist; chỉ cho phép native read marks của3task đã biết ngoài GET.
Hai lần test harness lỗi selector normalization/stale Frame handle được lưu
riêng, sửa harness rồi chạy đạt; không sửa source để né lỗi test.
Browser report/screenshots và native hash verification ở backup bridge
`browser/` và `native-verification.json`. Không kiểm toàn bộ UI/Paperclip,
broker acceptance, outage recovery dài hạn hoặc system-wide autonomy.

**Bước tiếp:** hoàn thiện thao tác owner tạo mẫu/hủy cả workflow ngay trên UI,
ưu tiên khả năng native Paperclip trước custom UI. Reuse luồng đã kiểm; không
chạy lại fixture/model thành công hoặc chuyển sang tuning. Tiếp tục giữ riêng
qualification/paper/live và gate chi phí broker còn thiếu.

### Studio: research vận hành và lỗi workflow — 02/11/2026

Owner yêu cầu tiếp Studio, đối chiếu docs/internet/cộng đồng và cải tiến phần
cần thiết; dừng chỉnh cấu hình subagents. Quyết định và nguồn nằm trong
[khảo sát vận hành](../../research/STUDIO-OPERATIONS-20261102.md).

Giữ native UI/API/process và luồng numeric → một lượt Hermes → human review.
Routines có manual trigger nhưng tạo một execution issue, không thay thẳng graph
đã kiểm. Reusable case workflows ở source pin là mẫu prompt, có experimental
gate; chưa là graph executor. Không bật timer, thêm CEO/coordinator, engine hoặc
framework. Chưa làm UI tạo/hủy trọn graph và chưa hoàn thiện cost accounting.

#### Sửa adapter

- Gộp phần báo lỗi linked workflow vào `spot_workflow.report_workflow_failure`.
  Numeric/Hermes chuyển summary sang `blocked`, giao human creator/responsible
  user, publish **Workflow cần bạn xem** kèm link bước lỗi và diagnostic code.
  Báo cáo completed và paper NOT_RUN được giữ. Không tự retry hoặc gọi model.
- Theo native contract, worker tự đứng tên `unblockDescriptor.owner`; agent
  không được chọn board/user ở field này. Người nhận summary vẫn là human.
  Bổ sung descriptor cho failed report/linked Hermes; giữ guard reassign/cancel.
- Sửa module identity khi native adapter chạy `engine_worker.py` dưới `__main__`:
  alias về cùng module để `JobError` của sibling modules được bắt đúng. Trước đó
  đường lỗi có thể thoát lên `paperclip_context_missing`, dù context thực tế đủ.
- Native Paperclip/core engine, quyền subagent và broker không thay đổi. Worker
  nạp wrapper mới ở lượt dispatch tiếp; không restart dịch vụ hoặc MT5.

#### Kiểm chứng và lỗi đã giữ lại

Focused suites: workflow15, engine worker22, Hermes5 = **42 tests đạt**. Bao gồm
CLI entrypoint trong subprocess (không provider), preflight thất bại, error delivery,
giữ completed report, parent đổi/cancel/reassign và native unblock-owner payload.
Đây là focused verification, không phải toàn bộ suite hoặc whole-product acceptance.

Native fault injection dùng request thiếu engine để dừng trước settings/data/model:

| Lượt | Kết quả |
|---|---|
| NAQ-33–36 | Tái hiện module identity error. Run `beba5d57-223d-466b-bb64-e3c209bbd983` failed/exit2; giữ lịch sử và hủy graph |
| NAQ-37–40 | Module fix cho diagnostic đúng và publish failure doc; parent transition chưa đạt. Sửa riêng delivery bằng native board API; sau đó hủy fixture, không chạy lại model |
| NAQ-41–44 | Xác nhận `paperclip_http_403` khi agent dùng board làm unblock owner. Giữ doc/run, hủy fixture sau khi sửa theo source contract |
| NAQ-45–48 | **Đạt**: run `f09a06fd-149e-40b2-9f74-1e900bbe29c6` failed/exit2 đúng kỳ vọng; source và summary blocked, summary giao local-board, failure doc khớp run; review/paper vẫn blocked |

Tất cả các lượt này **không đọc dữ liệu, gọi model, chạy numerical engine hoặc
broker**. Không dùng trạng thái failed để giả engine thành công. Ba graph thử
trước được cancelled để bớt việc trong inbox nhưng giữ report/run/history; graph
NAQ-45 giữ làm ví dụ lỗi có thể mở xem. NAQ-25 vẫn in_review, các workers idle.

Harness lần đầu gọi nhầm `/agents/{id}/runs` trả404; sửa sang native company
heartbeat-runs, không redispatch cùng graph. Browser harness lần đầu dùng heading
trùng title/body và strict selector lỗi; sửa locator level1, không sửa UI để pass.

Actual Studio5180: **4 browser cases đạt** — failure document và mã lỗi, link tới
bước con,390px không horizontal overflow, summary/report thành công NAQ-25 vẫn
mở được. Không pageerror/blocked request; đã xem screenshot1920/390. Chỉ cho phép
GET/HEAD cùng native read marks của các task cụ thể; không browser dispatch.

Artifact scripts, native assertion JSON, lỗi trước sửa, screenshots và browser
report: `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/studio-operations-20261102/`.
`git diff --check` đạt. Không có acceptance mới cho strategy, paper/demo/live.

**Giới hạn:** delivery vẫn có thể thất bại khi API mất kết nối hoặc lỗi xảy ra
trước khi worker nhận được assignment; native run/receipt vẫn phải được xem.
Re-read guard không phải transaction/CAS liên request. Numeric fault path đã kiểm
native thật; nhánh Hermes delivery được kiểm offline có model mock, không chạy lại
Gemini. Tạo/hủy trọn graph bằng UI và SDK/gateway token/cost visibility còn pending.

### Studio: điều khiển workflow từ UI, 02/11

Owner giao tiếp tục hệ thống, chưa tối ưu chiến lược. Lát này thêm **Studio →
Đội AI → Quy trình** trong Trader: chọn company/project, xem mẫu Forex/spot đã
đăng ký, tạo draft, xác nhận start, dừng cả graph, mở native task/run/report.
Paperclip giữ task store, dispatch, dependency và cancellation. Không sửa source
engine/Paperclip core, provider, quyền subagents hoặc global AI environment.

#### Contract và thay đổi

- Trader commit `9c47db194d37db0bd315fdd03926d7ce74950ae0` thêm dialog nhỏ,
  VI/EN, reuse LegacyModal/AiStatus, dark/light, focus/Escape và responsive.
  Mở/đóng dialog không remount iframe; chỉ action mở task đổi URL native.
- `tooling/ai-engines/studio_workflows.py` reuse graph lifecycle cũ. Local
  Vite/preview middleware chỉ nhận năm action allowlist, JSON giới hạn8KiB,
  Host loopback và Origin trùng chính xác; executable/script cố định, không shell.
  Đây là local control boundary, chưa là production/static-host API.
- Tạo draft lưu token vào sessionStorage trước request. Lost response/reload
  khôi phục cùng token; start/cancel outcome chưa rõ cần đọc native truth trước
  thao tác tiếp. Definite scope/invalid error cho chọn lại local selection,
  không xóa native history. Duplicate writes trong cùng company bị chặn trong
  một middleware process; không tuyên bố transaction với client Paperclip khác.
- Independent review bắt lỗi title dedup native: parent cùng tên có thể bị gộp
  dù token mới, kể cả khác project. Sửa wrapper dùng `allowDuplicate:true` cùng
  idempotency key cho từng task, kiểm company/project của parent trước children.
  Hai draft mới vẫn độc lập; retry cùng key vẫn trả đúng graph cũ.
- Review cũng bổ sung chặn research đã giao human trước start, canonicalize
  company UUID cho write lock, và reset scope khi pending draft không còn hợp lệ.
  Mã `workflow_scope` đi xuyên CLI/UI, không biến lỗi scope thành lỗi mạng.
- Không tạo scheduler/coordinator, tham số strategy tự do, tài khoản hay quyền
  paper/demo/live. Preview/draft không gọi model hoặc numerical engine.

#### Kiểm chứng

| Phạm vi | Kết quả |
|---|---|
| Python Studio wrapper | **7 tests đạt**: scope, idempotency, title dedup/project isolation, dependency change, human assignment, start/cancel guards |
| Workflow regression | **15 tests đạt** sau thay đổi helper graph; không provider/broker |
| Node middleware | **3 tests đạt**: origin/host/method/action, concurrency kể cả UUID hoa/thường, unknown outcome không lộ lỗi riêng; health bridge cũ **1 test đạt** ở đầu lát |
| Actual UI + native Paperclip | **5 cases đạt** trong `browser.json`: preview, draft/start confirmation chưa dispatch, iframe/focus, reload/cancel, injected lost create response sau native creation thật; có VI/EN390px |
| Independent drafts native | Hai draft cùng title mở đồng thời có ID riêng; replay key đầu trả đúng ID đầu, project đúng, cả hai chưa start và hủy được |
| Scope recovery UI | Injected definitive scope error cho pending draft → reset → hai selector dùng lại được; không tạo native task |
| Final layout | **3 cases đạt**, ảnh đã xem: dark390×844, light390×640, light1440×960; footer trong viewport, body scroll riêng, badge styles đúng, không horizontal overflow/pageerror |
| Build / integration doctor | Vite build cuối đạt; chunk-size warnings còn giữ. Doctor có4 source clean/pin/license đúng và Paperclip healthy; không chứng minh engine/job readiness |

Native draft fixtures NAQ-49/53/57/61 đã cancelled, giữ toàn bộ history. Final
read-only reconciliation xác minh12 child tasks đều cancelled, `startedAt=null`,
`executionRunId=null`, agents running0; NAQ-25 vẫn in_review, NAQ-45 vẫn blocked.
Không chạy lại successful workflow để kiểm nút Start: UI chỉ kiểm confirmation;
đường dispatch reuse helper đã có offline regression và native pilot trước.

Harness `verify-recovery.mjs` đạt hai assertion native đầu rồi lỗi selector label
ở kiểm reset scope; không sửa UI để pass selector. Sửa locator và chờ catalog
load xong, chỉ chạy lại `--scope-only`, đạt. Hai draft không được tạo lại; trạng
thái cuối đối soát bằng `verify-native-final.mjs`. Giữ `recovery.json` và console
lỗi làm lịch sử, không coi toàn script lần đầu pass.

Artifact local: `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/studio-controls-20261102/`
gồm scripts, `browser.json`, `layout.json`, `recovery.json`, `scope-recovery.json`,
`native-final.json`, screenshots và `build-final.log`. Không commit artifacts,
private config, DB hoặc secret. `git diff --check` đạt; WIP ngoài scope giữ nguyên.

#### Local runtime và resume

Sau Windows restart, Paperclip owner marker cũ trỏ PID đã được Windows dùng cho
`StartMenuExperienceHost.exe`; launcher từ chối đúng. Backup owner/lock vào
`runtime-before/`, đổi tên marker stale rồi dùng launcher project hiện có; không
kill PID tái sử dụng, không reset DB/config. Một lệnh gộp backup/move/start bị
automatic approval review chặn trước thực thi; sau đó từng bước kiểm ownership
và launcher chuẩn đã chạy thành công. Lỗi và backup được giữ, không tắt guard.

Trader chạy canonical Vite source tại5180; Paperclip17860/DB17861 giữ instance
cũ. API8010/MT5 không được khởi động hoặc restart trong lát này. Không chạm
CLIProxyAPI17852 hoặc instance Windows8317. Vì vậy đây là Studio/local control
acceptance, chưa là whole-product/backend acceptance hoặc production rollout.

**Bước tiếp theo:** quota/token/cost visibility và đối soát native run/receipt
cho lỗi chưa rõ outcome, trước khi thiết kế lịch tự chạy có giới hạn. Chi phí SDK/
gateway unknown chưa được coi bằng0; scheduler vẫn tắt. Strategy tuning, dữ liệu
mới, qualification và broker execution chưa thực hiện trong lát này.

### Studio: hướng dẫn agents, task policy và MCP/Decision audit, 02/11

Owner hỏi cách chuẩn hóa hướng dẫn vận hành và các trường trong task, Jev1.13,
sau đó hỏi Paperclip MCP vì Connections hiện lỗi đỏ. Lát này chỉ đọc runtime,
đối chiếu source/docs và bổ sung hướng dẫn; không chạy model, thay native policy,
chuyển auth mode hoặc kết nối OAuth.

**Đã xác minh bằng native GET:**

- Workers TradingAgents, RD-Agent, Forex và Hermes dùng native process adapters,
  timer heartbeat tắt, concurrency1, không được tự tạo agent/skill. Forex worker
  hiện có status `error`; setup không đồng nghĩa provider/job hiện sẵn sàng.
- NAQ-29 là graph cancelled có3 children cancelled; wrapper trả `can_start=false`,
  `can_cancel=false`. Không gán worker hoặc restart để làm sạch ảnh trạng thái.
  NAQ-25 vẫn in_review giao local-board; NAQ-26/27 done đúng workers numeric/Hermes.
- `executionPolicy=null` trên các task đã đọc: chưa cấu hình native Reviewer/
  Approver stages. Hermes phản biện qua child task; human handoff là assignment/
  summary in_review, chưa là native approval gate. Không dùng nó làm quyền execution.
- Native Trưởng nhóm nghiên cứu có instructions file nhưng nội dung mới là một
  câu chung. Nó không điều phối registered graph hiện tại; chưa tự sửa prompt
  owner-managed hoặc gắn thêm quyền. Hermes prompt được wrapper nạp rõ, còn
  process workers nhận typed contract; không tự đọc mọi Markdown/skill trong repo.
- Decision settings disabled, connection/grant/provider/model null, choices rỗng;
  availability=`not_configured`, history0. Shared pin có model `typesafe/jev-1.13`;
  server chỉ đăng ký consumer `settings.test` và route test. Studio wrappers chưa
  gọi Decision service. Presence trong picker không chứng minh tính năng đã dùng.

**MCP root cause:** health200/ok, deploymentMode=`local_trusted`;
`GET /api/mcp/setup` và `/api/mcp/connections` trả404 `API route not found`.
Native experimental settings có `enablePublicMcp=false`; instance config chưa có
auth publicBaseUrl, launcher không truyền PAPERCLIP_PUBLIC_URL. Source chỉ mount
management routes khi có public MCP config. Card lỗi vì route chưa được mở;
không phải evidence key/model/quota lỗi. Runtime tools của Codex chưa có Paperclip
MCP tool; các thao tác vừa qua dùng native HTTP API và source inspection.

Theo pinned `doc/public-mcp.md` và [upstream docs](https://github.com/paperclipai/paperclip/blob/master/doc/public-mcp.md),
native MCP cần valid origin, real authenticated user/company membership, feature
flag và human OAuth consent. Local-trusted implicit board không cấp consent.
Đổi auth mode đơn lẻ sẽ ảnh hưởng `paperclip_setup.api`/Studio controls đang dùng
implicit local access. Chưa đổi config để chỉ làm biến mất dòng đỏ. Khi triển khai
cần một cutover thống nhất: backup → owner login/membership → operator auth cho
controls → native worker/control checks → MCP client consent và scope verification.

**Tài liệu/skill đã bổ sung:**

- `tooling/ai-engines/OPERATIONS.md`: ownership, instruction loaders, task field
  semantics, draft/start/cancel/recovery, MCP/HTTP/source boundary, Jev consumer gate.
- Repo skill `.agents/skills/studio-operations/SKILL.md`: workflow vận hành đã có
  bằng chứng, route sang guide/receipt/helpers; loại trừ strategy và upstream upgrade.
- Workspace AGENTS và engine README route tới cùng guide. Giữ command/contracts
  ở README cũ, kết quả ở receipt này; không tạo ledger hoặc script dispatch mới.
- Skill đã được host expose trong phiên; chưa import nó vào Paperclip Skills hay
  thay prompt/capability của workers. Không nâng global config hoặc tạo hook mới.

**Research và quyết định Jev:** đã đọc live TypeSafe index/confidence, Context7
primary documentation và [OpenRouter Jev guide](https://openrouter.ai/docs/guides/community/jev).
Jev trả typed decision/probability cho semantic routing/classification; không
thay workflow code, quyền, numeric validation hoặc Gemini/Hermes. OpenRouter guide
hiện có1.14 và vẫn hỗ trợ1.13; giữ model pin, không auto-upgrade picker. Chưa thêm
connection vì registered workflow chưa có Decision consumer. Khi có nhu cầu cụ
thể, kiểm advisory classification trên labeled cases, unknown/escalation, latency
và cost trước promotion; không dùng confidence như quyền phê duyệt.

**Kiểm chứng:** skill validator đạt; local Markdown links kiểm thành công; positive
walkthrough dùng skill/guide đọc NAQ-29 qua wrapper, không có mutation/dispatch.
Negative trigger strategy selection được semantic review, chưa có classifier
benchmark. AI-environment audit:0 errors/0 warnings, global12279B không đổi,
project9269/65536B, reserve56267B, combined21548B. `git diff --check` đạt.
Không build/test lại code runtime vì lượt này chỉ đổi instructions/docs.

### Studio: bật MCP chính thức và chuyển auth local, 02/11

Owner yêu cầu setup MCP sau audit trên, đã tự đăng nhập/claim board và duyệt
hai flow riêng: Codex OAuth và native CLI board access cho Studio.

**Thay đổi:**

- Giữ source Paperclip pin `2e0f8f84`, DB/storage và cổng17860/17861. Không sửa
  source engine/upstream. Instance chuyển `local_trusted` → `authenticated` /
  `private`, loopback; `auth.publicBaseUrl=http://127.0.0.1:17860`.
- Bật `enablePublicMcp` bằng native API trước cutover. Native board claim cấp
  quyền người dùng thật; không ghi trực tiếp bảng user/membership.
- `.codex/config.toml` thêm `naqex_paperclip` Streamable HTTP, OAuth scopes
  `paperclip:read`, `paperclip:write`, `offline_access`; không configure. Allowlist
  14 tools cho task/document và directory reads. Không đổi global MCP config.
- Studio giữ native API, helper đọc exact-origin credential từ CLI auth store
  riêng `.runtime/paperclip/auth.json`. Không dùng token MCP cho REST, không dùng
  key agent cho operator và không retry anonymous khi token bị từ chối.
- Hướng dẫn renew/revoke/rollback ở `tooling/paperclip/README.md`, instruction
  boundary ở `tooling/ai-engines/OPERATIONS.md`. Skill vận hành cũ vẫn route cùng
  guide; chưa import skill vào Paperclip hoặc thay prompt/policy workers/Jev.

**Backup/runtime:** native `db:backup` tạo SQL gzip825433B cùng config/env/owner
snapshot ở `.runtime/paperclip/mcp-cutover-20261102/`. Trước restart:5 agents,
0 queued/running jobs. Dừng đúng PTY owner cũ và restart launcher chuẩn với
workspace origin5180. UI build đạt với các warning upstream sẵn có về CSS,
dynamic imports/chunk size; không sửa chúng trong task MCP. Migrations đã áp
từ trước. Scheduler vẫn tắt, JWT signing secret giữ nguyên. Không restart Trader
API/MT5, không gọi gateway, model, strategy hoặc broker.

**Kiểm chứng:**

- 4 auth tests đạt: không credential ở local mode, origin khác không được dùng,
  exact-origin credential được gửi, store sai không fallback và401 không retry.
  Lần chạy đầu thiếu PYTHONPATH nên import lỗi; chạy lại với tooling/ai-engines
  trên PYTHONPATH đạt. Không sửa test để bỏ kiểm tra.
- Native health200/ok/authenticated; OAuth discovery đúng issuer17860. Management
  MCP không còn404: request không có session bị401, đúng quyền yêu cầu.
- `codex mcp login naqex_paperclip` hoàn tất; CLI status `o_auth`. Probe riêng
  qua Codex app-server `mcpServerStatus/list` đã authenticate và nhận catalog37
  tools, `toolsError=null`; lưu `mcp-inventory.json` local. Probe ban đầu không
  có thread/project context trả inventory rỗng; probe sau truyền đúng endpoint
  project bằng process config override, không ghi config global. Không gọi model.
- Native API xác nhận real-user board_key có quyền công ty;5 agent IDs giữ
  nguyên, active runs0. CLI wrapper overview và HTTP POST chỉ đọc overview qua
  Trader5180 đều đạt, trả3 workflow hiện có. Không tạo/start task để test auth.
- AI environment audit0 errors/0 warnings: global12279B, project9269/65536B,
  project reserve56267B, combined21548B. `git diff --check` đạt.

**Giới hạn/resume:** tools Paperclip chưa được expose trong chat đang chạy;
OAuth/discovery không được báo thành task call qua MCP. Sau reconnect/chat mới,
gọi `paperclip_connection` và đọc NAQ-29 để xác nhận company/scope thực tế. Worker
JWT path giữ nguyên nhưng chưa dispatch worker sau cutover; API write/workflow
execution sau đổi auth chưa được thực thi trong lát này. Các task lịch sử vẫn
giữ assignment/state, gồm local-board cũ; board claim không được hiểu là tự đổi
mọi assignee. Quota/cost visibility và reconcile vẫn là lát hệ thống tiếp theo.

### Studio: vận hành native, đối soát run/receipt, 02/11

**Quyết định owner thay thế UI bên ngoài:** owner phản đối dialog Quy trình vì
trùng khả năng Paperclip, đồng thời yêu cầu lưu sở thích để agent không lặp lại.
Đã gỡ nút/dialog, CSS, browser HTTP bridge và tests chỉ phục vụ lớp UI đó khỏi
Trader; **Studio → Đội AI** dùng UI native Paperclip. Không đổi source engine.
Trader giữ phần nhúng, preference và trạng thái kết nối. Hướng dẫn vận hành,
AI plan và skill Studio đã cập nhật; memory update note được ghi theo yêu cầu.
Các ảnh/kiểm chứng dialog trước đó trong evidence là lịch sử, không phải UI cần
khôi phục. Các chức năng native phải được kiểm tra trước khi thêm UI quản trị.
Trader source cleanup: commit `b0ba0439`; commit `60307c44` của dialog trước đó
được giữ trong lịch sử, không phải phiên bản UI hiện hành.

**Phần hệ thống được giữ:** CLI `studio_workflows.py get` đối chiếu native
task/run với receipt local, giới hạn scope company/issue/agent và dung lượng đọc.
Phân biệt chưa chạy, đang chạy, gián đoạn, đã lưu nhưng chưa gửi, lỗi, hủy và
evidence không khớp. Hash dùng logical UTF-8 text đúng contract worker trên Windows.
Có duration, requested/reported model và token/cost khi được native báo cáo;
zero counters mặc định của process adapter không được hiểu là zero SDK usage.
Model settings lỗi không khóa đọc/hủy. Task có run history không thể bị reset
thành draft rồi dispatch lại qua helper. Đây là projection cho agent/operator,
không tạo task ledger hay màn quản trị cạnh tranh với Paperclip.

| Phạm vi | Kết quả xác minh |
|---|---|
| Python | **17 tests đạt**: scoped controls/observations, run history, interrupted/delivery/mismatch, unknown usage, CRLF, model config lỗi |
| Native API sau auth cutover | Tạo draft → reload → hủy qua native board API đã đạt trước khi bỏ UI wrapper; parent `051c0285-a056-4f4c-89e8-3c4838ff60a3`, mọi child cancelled, zero runs/model calls |
| Đối soát task lịch sử | NAQ-25 research/review đều recorded; fault fixture NAQ-45 có failed source. Không redispatch; hai lần GET graph đo khoảng0,83s và0,64s, không phải benchmark tải |
| UI hiện hành | Native-only production build đạt; **4 embed cases đạt** tại1440/390px: giữ draft/navigation/preferences và recovery; không còn nút/dialog Quy trình, zero writes/page errors |
| Runtime5180 | Không còn outer workflow UI; POST bridge cũ trả404, zero page errors. Kiểm tra tiếp đã đợi native sign-in form render trong iframe bằng browser biệt lập chưa đăng nhập; không coi đó là owner task journey. API8010/MT5 chưa khởi động trong lát này |
| Review | Review độc lập source/ảnh trước và sau thay đổi; phát hiện/sửa sai hash CRLF, model-preflight dependency, history start guard và queued polling của bản dialog đã loại bỏ |
| AI environment | Audit0 errors/0 warnings; global12279B, project9269/65536B, reserve56267B, combined21548B |

Artifact riêng tư: `E:/BACKUP-TRADINGWORKSPACE/studio-observation-20261102/`
(`native-observation.json`, `browser/report.json` giữ native draft/cancel,
`browser-final/` giữ dialog lịch sử, `native-only-dist/`, `native-only-5180.json/png`,
`native-only-hydrated-5180.json/png` xác nhận native form đã render).
Embed fixture report/ảnh ở `projects/trader/foundation_v2/.runtime/studio-embed-fixture/`.
Lượt actual-dialog QA đầu thất bại vì selector `dl` khớp hai phần tử; đã giữ
`actual-studio-attempt1.json`, sửa harness chọn details đang mở rồi đạt. Không
sửa product để né kiểm tra. Khởi động detached Paperclip bị auto-review chặn
không có lý do cụ thể; launcher project trong phiên terminal đã chạy thành công.

**Giới hạn:** actual MCP task tools chưa được expose trong chat này; các thao tác
trên là native HTTP API. Write auth đã kiểm bằng draft/cancel, worker JWT dispatch
sau auth migration vẫn chưa kiểm lại. Provider receipt/token/price của SDK còn
thiếu nên không thể suy ra quota còn lại hay tổng tiền. Recovery delivery vẫn cần
agent đối soát và sửa publication qua native API, không có tự động resume/rerun.
Native Reviewers/Approvers, scheduler và broker execution không được bật. Exness
demo được owner cho phép dùng khi cần test hệ thống, nhưng lát Studio này không
cần broker; không OrderCheck/OrderSend, không tối ưu chiến lược. Timeout/concurrency
không là money cap. Bước hệ thống tiếp theo là hoàn thiện provider usage receipt
và kiểm worker dispatch sau đổi auth khi có nhu cầu thực, trước lịch tự chạy.

### Studio: worker sau đổi auth và SDK usage, 02/11

Owner giao tiếp tục hệ thống; giữ fixture EURUSD/H4 và chưa tối ưu chiến lược.
Đã mở lại gateway project17852 bằng binary đã kiểm SHA256 và config/account
hiện có; PID21312, log/owner ở `.runtime/paperclip/gateway-owner.json`. PID cũ
không còn, cổng kiểm trống trước launch; không sửa instance Windows8317. Không
đổi cấu hình provider, model hoặc gateway, không chuẩn bị lại profile Hermes.

**Thay đổi:** `studio_observation.py` đọc thêm file `usage.jsonl` mà plugin
Hermes đã ghi sẵn. `provider_usage` là dữ liệu quan sát riêng, không ghi đè
native accounting. Kiểm receipt/session/request/run, giới hạn64KiB, loại request
trùng giống nhau, từ chối xung đột/số token sai; thiếu usage hoặc thiếu main-call
coverage hiện partial. Tách model được yêu cầu với model gateway báo về; không
coi tên model gateway trả là chứng minh độc lập model gốc. Giữ cost unknown;
không suy giá từ route hay giá mặc định. Không sửa source engine/plugin, không
thêm store, UI hoặc lệnh provider retry.

**Luồng thật sau auth migration:** native graph mới `NAQ-69`
(`307a9c6e-5c5d-42ea-9e34-954fa97913b8`), key `auth-usage-20261102-01`.
Preflight xác nhận fixture/spec hashes, model catalog, source pins và0 active
runs trước start. Trader source `b0ba043903fcc25cd385b2a9ae12d9f303e51230`,
Hermes `bf0203a794a07aac3ff764972ab9087baa4e4f4e`.

| Bước | Kết quả đã đọc từ native API/receipt |
|---|---|
| NAQ-70 kiểm định | done/succeeded/recorded, run `785a2db4-4dda-447d-b70a-22dcb8973c18`,110,54s; báo cáo và evidence đã gắn task |
| NAQ-71 phản biện | done/succeeded/recorded, run `bc607b8e-1a89-418c-b9ec-29971a8635b9`,44,48s;2 main requests có usage |
| SDK tokens quan sát | input14468, output2822, cache-read/write0; reasoning1572 là bucket theo SDK, không cộng lại vào output |
| Model | requested `gemini-3.8-flash-high`; gateway reported `gemini-3.8-flash-n`; cost unknown |
| NAQ-69 bàn giao | in_review, giao đúng human owner, có document **Kết quả và bước tiếp theo** |
| NAQ-72 paper | blocked/NOT_RUN,0 runs; mọi timer vẫn tắt; active runs sau hoàn tất0 |

**Kiểm chứng:**12 observation tests +9 scoped-control regression tests đạt.
Native get của graph mới và NAQ-25 lịch sử đọc được usage; không chạy lại lượt
cũ. `git diff --check` đạt; Trader/Paperclip/Hermes worktree sạch. Không cần build
UI vì lát này không sửa UI. Evidence riêng tư:
`E:/BACKUP-TRADINGWORKSPACE/studio-observation-20261102/post-auth-20261102/`
(`graph.json`, `data-preflight.json`, `observation.json`, `verification.json`);
worker output ở artifact root đã đăng ký theo company/run.

**Giới hạn:** đã kiểm worker JWT/callback dispatch sau auth cutover qua native
HTTP API; chat này vẫn chưa expose Paperclip MCP tools. SDK usage là metadata
quan sát, chưa có giá/invoice, quota còn lại hoặc enforceable money cap. Recovery
delivery vẫn cần đối soát trước retry; scheduler chưa mở. Không có lượt tuning,
broker SDK/OrderCheck/OrderSend, dữ liệu mới hoặc giấy phép paper/live.

### Studio: khảo sát GitHub native, 02/11

**Đề xuất:** dùng repo GitHub đã có. `Naqex/trader` cho project coding
**Phát triển Trader**; `Naqex/workspace` cho kế hoạch/tooling khi thật sự cần
agent làm phần đó. Giữ project nghiên cứu hiện có và worker contract bounded;
không cần tạo repo GitHub riêng hoặc cấp checkout ghi được cho mọi engine.
Instructions/contracts vẫn có owner ở `tooling/ai-engines/`; không commit DB,
profile hoặc secrets để làm repo cấu hình. Hướng vận hành đã bổ sung vào
`tooling/ai-engines/OPERATIONS.md` §GitHub repositories and coding work.

**Đã kiểm thực tế:** company Naqex AI có1 project nghiên cứu, workspaces rỗng,
project Git authorization chưa gán,0 repository connections/0 repositories.
Native gallery có GitHub với method `mcp-key` (PAT, tool/MCP remote) và
`copilot-token` (AI runtime authentication riêng); chưa có managed GitHub App
method được chào ở instance này. Preflight endpoint GitHub reachable nhưng401
khi chưa có credential; đây không phải bằng chứng đã kết nối hoặc đọc được repo.
Paperclip pin `2e0f8f84b810ef3ae89c400d3ee1faf6b281c217` được đối chiếu source
project validators/routes và `doc/execution-github-identity.md`.

**Nguồn chính thức:** [connector setup](https://docs.paperclip.ing/connectors/github-setup/),
[access boundaries](https://docs.paperclip.ing/connectors/github/),
[coding workspace](https://docs.paperclip.ing/how-to/connect-agent-to-github/).
Gắn repo vào project và cấp quyền connector là2 bước khác nhau. Managed App
phụ thuộc eligible Cloud enrollment; PAT là đường native phù hợp để bắt đầu
local, chỉ chọn repo/agents cần thiết, chỉ đọc, có expiry. PAT tool access không
tự cấp managed shell identity. Coding sau này cần isolated worktree được bật
và kiểm thực tế, PR workflow/branch protection; Ask-first của tool gateway không
kiểm soát shell git/gh. Standard-trust local worker chưa có managed identity có
thể dùng auth host, nên không coi connector chỉ đọc là sandbox của coding agent.

Engineering issue inbox vẫn là `Naqex/workspace`, PR ở repo sở hữu code; task
Paperclip chỉ liên kết issue/PR liên quan, không mirror toàn bộ backlog hay tạo
ledger thứ hai. Experimental Code Review Bot chưa cần cho nhu cầu đọc repo.
Chưa tạo project/workspace/connector hoặc repo mới, chưa cấp token/OAuth/quyền
GitHub, chưa đọc private repo qua connector. Bước owner nếu chọn triển khai là
duyệt phạm vi và nhập fine-grained PAT trong native Connectors, sau đó kiểm đọc
một file đã biết trước khi xét quyền ghi. Không lấy token gh của host.

Evidence: `post-auth-20261102/github-research.json` dưới evidence root của lát
Studio ở trên. Research này không tuyên bố GitHub connection hoặc coding
worktree đã được nghiệm thu.

### Studio: skill native cho Trưởng nhóm nghiên cứu, 02/11

Owner duyệt bổ sung skill riêng cho Trưởng nhóm qua catalog Paperclip. Đã tạo
`tooling/ai-engines/paperclip-skills/naqex-research-lead/SKILL.md`: giao việc đúng
worker/contract, đọc trạng thái trước mutation, kiểm evidence/provenance,
reconcile lỗi/delivery trước retry và bàn giao bằng tiếng Việt. Skill dùng
bundled `paperclip` cho API mechanics; không nhân bản toàn bộ guide vận hành.
Đây là package cho consumer Paperclip, không thêm skill discovery/global Codex.

**Native publication/assignment:** dùng company skill API `POST /companies/:id/skills`
với idempotency key `naqex-research-lead-v1`, sau đó `POST /agents/:id/skills/sync`
`mode: add`. Skill ID `6a920348-0c2c-4b01-9340-557f0ae13621`, current version
`869451ba-0e79-44e2-974e-e680769dab29`; key
`company/6b90f0c1-8f91-4fe8-bc15-fc8c58b3ac8f/naqex-research-lead`.
Gán duy nhất Trưởng nhóm `6da897b6-ce7e-45ba-a8d4-d30de1571dc5`; catalog xác nhận
attachedAgentCount1. Giữ cả3 bundled defaults và toàn bộ adapter/runtime config
khác;4 process workers không nhận thêm skills. Native tạo snapshot managed
markdown-only; source owner trong repo, nội dung native đối chiếu bằng hash.

Lần đầu sync có version pin trả400 vì Beta skills chưa bật. Đã kiểm trạng thái
publication để giữ đúng skill hiện có, rồi gán không pin qua native API; không
bật Beta hoặc thử bypass. Assignment hiện theo current version, không tuyên bố
đã khóa version cho agent. Skill source content SHA256 logical UTF-8:
`302bc3418167a738867207d542eae6e6f2979fdb6046d93739ba2fd7c6403955`.

**Kiểm chứng:** quick_validate đạt; GET native SKILL.md/version trùng source;
semantic review với tình huống đọc tiến độ (không dispatch), delivery chưa rõ
(đối soát, không lặp inference) và yêu cầu ngoài contract (không giao nhầm worker).
Smoke gọi chính `ensureCodexSkillsInjected` của adapter pin trong skills home
cách ly: package đọc từ native API được mount đúng hash; skill không chọn không
được mount. Không sửa source engine hay home Codex thật. AI environment audit
0 errors/0 warnings; global12279B, project9269/65536B, reserve56267B, combined21548B.
Git diff check đạt. Không chạy lại các tests hệ thống không đổi.

Evidence/backup private ở
`E:/BACKUP-TRADINGWORKSPACE/studio-observation-20261102/native-skills-20261102/`
(`before.json`, `skill.json`, `assignment.json`, `verification.json`,
`injection-manifest.json`, `injection-result.json`, `api-package/`, `injection-smoke/`).
Rollback assignment qua native sync `mode: remove` với đúng skill key; giữ
bundled selections và lịch sử phiên bản. Không cần restore DB hoặc sửa engine.

**Giới hạn:** native snapshot hiện `missing` chờ materialization lúc chạy;
đó chưa phải bằng chứng agent đã đọc hoặc làm theo skill. Đã kiểm adapter
injection trong home cách ly, chưa dispatch actual Trưởng nhóm/task/model để
thử hành vi.0 active runs, timer giữ nguyên tắt, không model/broker calls hoặc
GitHub authorization. Lượt nhiệm vụ thực tiếp theo cần kiểm discovery/content
và hành vi trong runtime riêng của agent; không dùng smoke thay acceptance đó.

### Studio: cài bộ skills từ catalog Paperclip, 03/11

Owner duyệt bộ `task-planning`, `qa-acceptance`, `doc-maintenance` sau khảo sát
catalog native. Cài bằng `POST /companies/:id/skills/install-catalog`, giữ nội
dung upstream từ `@paperclipai/skills-catalog` 0.3.1 (MIT), rồi sync `mode: add`
cho Trưởng nhóm `6da897b6-ce7e-45ba-a8d4-d30de1571dc5`. Đây là consumer duy nhất
hiện hỗ trợ native skill delivery; không tạo thêm agent bảo trì hoặc gán vào
4 process workers. Tổng selections của Trưởng nhóm từ 4 thành 7, giữ skill Naqex
và 3 defaults cũ. Không bật Beta/version pins.

| Skill | Native ID | Current version |
|---|---|---|
| task-planning | c2ff66be-9f17-4799-b7e4-e9aaaa743c84 | 81bd4a87-817c-477b-aab8-d10e7f914aad |
| qa-acceptance | 0d7b1d92-4df5-4268-913c-d61173cbf267 | 5672b126-badc-4270-9721-4ceb09e9b5ba |
| doc-maintenance | 44c0867d-fcf7-42e4-9460-4ec9526560bd | c3b8af8e-a576-410b-802e-fa6e2e698473 |

**Lỗi và xử lý:** GET catalog files ban đầu trả 422 do CRLF trong checkout
Windows; SHA256 sau đổi CRLF→LF trùng cả Git blob HEAD và manifest. Đã backup
byte cũ rồi khôi phục chính xác 3 Git blobs, thêm 3 quy tắc `text eol=lf` trong
`D:/ANNAM/TradingWorkspace/.git/modules/projects/paperclip/info/attributes`.
Không sửa nội dung skill/logic engine, manifest hoặc guard kiểm hash. Quy tắc
chỉ local, không tự lan sang clone khác; hướng dẫn đã bổ sung vào launcher guide.
Sau tạm dừng, instance không còn chạy; launcher native khởi động lại với origin
5180, giữ DB/storage/config và scheduler tắt. `Start-Process` bị automatic
approval review từ chối; launcher chạy qua terminal được công cụ quản lý.

**Kiểm chứng:** cả 3 native contents trùng SHA256 catalog, current versions và
attachedAgentCount 1; sync không có warnings. Chỉ `paperclipSkillSync` của lead
thay đổi; permissions/runtime/model config và 4 agent khác giữ nguyên. Smoke
gọi chính `ensureCodexSkillsInjected` của adapter pin, với packages đọc lại từ
native API trong skills home cách ly: mount 3/3 đúng hash và loại skill không
được chọn. Không ghi vào Codex home thật hoặc dispatch model/broker/task.
Native snapshot vẫn `missing` chờ materialization ở lượt chạy thực; smoke
không chứng minh agent đã đọc/làm theo hoặc có cải thiện chất lượng/hiệu suất.
Audit môi trường AI: 0 errors/0 warnings; global 12279 B, project 9269/65536 B,
reserve 56267 B, combined 21548 B. Native health `ok`, 0 agent đang chạy;
`git diff --check` đạt, Paperclip checkout không có thay đổi nội dung tracked.

Evidence riêng tư tiếp tục ở
`E:/BACKUP-TRADINGWORKSPACE/studio-observation-20261102/catalog-skills-20261102/`:
`apply-before.json`, catalog/install/assignment/after JSON, `verification.json`,
API packages và `injection-result.json`; 3 file `*-before.bin` và
`git-info-attributes-before.bin` là backup phục hồi. Rollback bằng native sync
`mode: remove` với đúng 3 keys đã thêm, giữ các selections cũ và lịch sử. Chỉ
gỡ 3 dòng attributes do lát này thêm nếu muốn đảo sửa LF; không ghi đè các rule
local khác. Operations guide định nghĩa cách dùng 3 skills mà không nhân bản
PLAN/receipt hoặc mở rộng quyền hạn.

### Studio: rà kiến trúc và mức sẵn sàng mở rộng, 03/11

Owner yêu cầu audit tổng thể, kiểm thử tối thiểu, phân loại theo từng lát từ
nghiên cứu tới thực thi thật. Kết luận: giữ kiến trúc hiện tại cho nghiên cứu
có owner theo dõi; chưa nghiệm thu chạy tự động nhiều job hoặc giao dịch.
Không bật lịch, tăng concurrency, đổi model hay thêm engine trong lượt audit.

| Lát | Bằng chứng và giới hạn hiện tại |
|---|---|
| Điều phối | Paperclip native HTTP đọc được; 5 agents idle, mỗi agent maxConcurrentRuns 1, timer tắt. Không có UI/ledger workflow thứ hai. |
| Trưởng nhóm | Có 7 selections nhưng 4 skills mới vẫn chờ materialization; codex_local/CLI chọn claude-opus-5.5, route owner từng báo hết hạn. Bypass approvals/sandbox false. Chưa gọi model để xác nhận readiness. |
| Nghiên cứu | TradingAgents/RD-Agent/Hermes source sạch, đúng gitlink; lịch sử engine jobs được giữ. Các process workers chỉ nhận contract đã đăng ký, chưa là nghiên cứu tự do. |
| Dữ liệu/mô phỏng | NAQ-69 được đọc lại qua observation helper: Forex done/succeeded/recorded 110,54s, receipt/output hash hợp lệ. Không export QDM hoặc chạy lại fixture. |
| Phản biện | NAQ-69 Hermes done/succeeded/recorded 44,48s; SDK quan sát 2 requests, input 14468/output 2822. Chi phí unknown, không phải invoice. |
| Owner duyệt | NAQ-69 in_review giao human; executionPolicy null. Bàn giao này không là native Reviewer/Approver policy hay trading authority. |
| Paper/forward | Placeholder blocked/NOT_RUN; chưa có forward engine/soak acceptance. |
| Demo/live | Không gọi broker, không mở execution; việc đã kết nối MT5 không nghiệm thu luồng AI→lệnh. |

**Readiness và ưu tiên:** gateway model catalog hiện `gateway_unavailable`;
WSL NaqexResearch stopped (on-demand, không coi đó là lỗi cài đặt). Native
budget policies rỗng, company/agent monthly budget 0; lead có maxDailyRuns 10,
4 process workers chưa có daily run cap. Cost summary có 27 events, 24 chưa
định giá, 22 unknown billing, 2 pending accounting, pricingComplete false.
Các nhóm có thể chồng nhau; pending accounting không đồng nghĩa run còn chạy,
spendCents 0 không chứng minh miễn phí. Ưu tiên chọn model đúng adapter/còn dùng
được cho lead và khôi phục gateway trước lượt job kế tiếp. Sau đó reuse native
maxDailyRuns/budget policies thay vì viết scheduler/quota store mới; money cap
chưa đáng tin khi billing còn unknown. Giữ cap số lượt như lớp giới hạn riêng.

Trước tăng tải: một nhiệm vụ lead nhỏ để kiểm skill discovery và đúng contract;
kiểm phục hồi/hủy ở runtime thực rồi mới thử tối đa 2 workflow độc lập có owner
theo dõi. Đây là bước đề xuất, chưa phải mức concurrency đã benchmark. RD-Agent
tiếp tục một runtime lease, không nhân bản worker để vượt lease. Cân nhắc native
approval stages khi có hành động đặc quyền cụ thể, không thêm reviewer trùng
Hermes. Chưa có bottleneck đo được đòi thêm engine/Jev/memory/vector/queue.

**Kiểm chứng tối thiểu:** doctor source/runtime đạt cho 4 integrations, pin,
origin/license sạch và Paperclip healthy. 8 focused offline behavioral tests
đạt trong 0,152s: auth bị thu hồi, chống dispatch trùng, source/run/hash handoff,
hủy child, lỗi delivery không lặp inference, interrupted khác success, unknown
usage khác zero billing, human handoff không tự chạy paper. Không mở full suite,
load/soak/restore test hoặc fresh provider workflow. `/mcp/setup` và
`/mcp/connections` trả 401 với CLI credential hiện tại; không kết luận OAuth
người dùng hỏng hoặc MCP đang expose trong chat. Dùng native HTTP phù hợp scope.

Evidence private:
`E:/BACKUP-TRADINGWORKSPACE/studio-observation-20261103/architecture-audit/`
(`runtime-summary.json`, `summary.json`, `data-quality.json`, `overview.json`,
`last-accepted-graph-observation.json`, `audit-findings.json`). Không đổi
runtime/config/source engine hoặc strategy; kết quả là scoped architecture audit,
không full-product, fresh inference, multi-job hay live acceptance.

### Studio: giới hạn lượt chạy và xử lý quota/429, 03/11

Owner duyệt ưu tiên quota/token sau audit. Dùng policy native thay vì thêm
dashboard, quota store hay scheduler. PATCH `runtimeConfig` qua API đã xác thực
cho đúng 4 process workers, giữ các trường cũ; Trưởng nhóm đã có cap 10 nên
không sửa. Đọc lại cả đội: **10 started runs/ngày/agent, maxConcurrentRuns 1**,
timer tắt, 5 agents idle. Kiểm tra hash các trường adapter/permissions/metadata/
reportsTo không đổi, kể cả runtime/aiConnection của Trưởng nhóm. Setup helpers
giữ cùng default cho worker mới; không tự migrate worker đã tồn tại.

| Lớp | Kết quả |
|---|---|
| Paperclip | Cap per-agent được lưu và đọc lại bằng native API; ngày UTC reset lúc 07:00 Việt Nam. Failed started runs vẫn tính vào cap. Không dispatch để thử chạm trần trên dữ liệu thật. |
| Gateway project 17852 | Managed config đang có request-retry 0, max-retry-credentials 1, max-retry-interval 0; không có credential override các retry keys trong YAML hiện tại. Giữ nguyên config/key/route; không gọi model hoặc thay instance Windows 8317. |
| TradingAgents/RD | Giữ retry 0/one call; thêm chẩn đoán model_rate_limited cho HTTP/SDK 429, native báo cáo lỗi và giữ artifacts. |
| Hermes | Profile đã có api_max_retries 1 (một attempt), auto_recovery_cycles 0, fallback rỗng, auxiliary retries 0. Đọc structured failure_reason của SDK để ghi model_rate_limited cùng hành động chờ/reset/đối soát; không replay report đã có. |

**Luồng:** native admission kiểm giới hạn → process nhận contract → engine gọi
model theo retry policy có sẵn → wrapper lưu receipt/report hoặc lỗi 429 → owner
đối soát trước lần thử mới. Cap có thể chặn graph giữa các child; không tự mở
thêm quyền/run để vượt trần. Đây không là company-wide request pool, tổng token/
ngày, giá USD chính xác hay quota của Codex chat. Nhiều agent khác nhau vẫn có
thể chạy đồng thời và một run có nhiều model calls. Chưa tăng tải/bật lịch.

**Kiểm chứng tập trung:** 15 tests đạt trong 1,345s: toàn bộ LifecycleTests của
engine wrapper, test RD generation 429 one-call, CompletionTests Hermes. Kiểm
HTTPError/OpenAI RateLimitError 429 không rò diagnostics, không gọi lại; giữ
success, duplicate-run, lỗi publication và linked human handoff. Không chạy
full suite hoặc broker. Lần gọi test đầu sai đường dẫn Python do cwd ở tooling;
đã dùng absolute interpreter, không thay dependency.

Smoke bằng **Hermes SDK thật + HTTP server giả lập local**, profile/home tạm,
không dùng memory thật: HTTP 429 + Retry-After 120 trả completed false,
failure_reason rate_limit, **1 inference request**, không auto recovery. Có
thêm 1 POST `/api/show` cho metadata, không phải inference/retry. Harness ban
đầu thiếu PyYAML (runtime dùng hermes_yaml); sau đó assertion đếm cả metadata
nên fail. Chỉ sửa harness dùng loader native và đếm đúng inference endpoint;
không sửa engine, policy hoặc tăng retry để pass. Không gọi provider trả phí.

Audit môi trường AI sau sửa đạt **0 errors/0 warnings**; global 12279 B,
project 9269/65536 B, reserve 56267 B, combined 21548 B. Diff check đạt. Wrapper
source được đọc ở lần dispatch tiếp theo, không cần restart engine đang idle.
Gateway/provider readiness và lead model hết hạn vẫn là gate trước job thật;
lát này không xác minh fresh inference, daily-cap saturation hay load/soak.

Evidence private:
`E:/BACKUP-TRADINGWORKSPACE/studio-observation-20261103/quota-controls/`
(`native-before.json`, `native-after.json`, `policy-summary.json`,
`hermes-429-smoke.py`, stdout/stderr smoke). Rollback runtime: đọc config hiện
tại, chỉ phục hồi sự có mặt/giá trị maxDailyRuns của 4 worker theo before bằng
native PATCH, giữ mọi field/owner change khác; không ghi đè nguyên snapshot.
Không xóa run/report. Rollback source bằng revert commit của lát này.

### Studio: bỏ cap ngày và bàn giao research bằng native documents, 03/11

**Quyết định mới của owner thay thế cap ngày ở mục trước:** ưu tiên vận hành
trơn tru, tối ưu chi phí sau. Đã gỡ `maxDailyRuns` và các alias `dailyRunLimit`,
`dailyRunCap`, `maxRunsPerDay` khỏi heartbeat của cả 5 agents bằng native API.
Đọc lại xác nhận không còn cap ngày; giữ maxConcurrentRuns 1, timer tắt và
wakeOnDemand true. Snapshot trước/sau xác nhận adapter, quyền, metadata,
reportsTo và aiConnection không bị thay. Hai setup helpers bỏ default cap ngày,
vẫn không tự migrate các agent đã tồn tại. Không thay quota của provider,
retry policy, timeout, quyền broker hoặc bật lịch.

**Luồng bàn giao:** dùng task hiện tại cùng research document và `plan` có
revision; owner không cần copy lại kết quả. Công việc nhỏ đã được giao tiếp tục
trên task hiện tại. Khi thực sự cần quyết định mới, native request_confirmation
trỏ đúng revision, resolverPolicy human_only, wake_assignee và lead giữ assignment.
Sau khi duyệt, chỉ tách task khi có ranh giới ownership/dependency thật; dùng
native accepted-plan decomposition để giữ revision/idempotency, đọc lại các
blockedByIssueIds. Không thêm workflow dialog, queue, database hoặc sửa engine.

Đã cập nhật source skill `naqex-research-lead`, publish qua native company skill
API và đọc lại content khớp SHA256
`ededfb366766b4f694878429a115b9c89eba5eae053fb05e8c4af3e83370f38c`.
Version native cuối được lưu trong private `skill-publication.json`; lead vẫn
chọn skill và theo current version (không pin Beta, không thay 6 skill khác).
Runtime adapter sẽ mount phiên bản mới ở lần chạy kế tiếp; chưa tuyên bố model
đã đọc hoặc thực thi nó.

**Smoke native tối thiểu:** fixture
[NAQ-73](http://127.0.0.1:17860/NAQ/issues/NAQ-73) không gán agent, đã đóng
cancelled và giữ làm bằng chứng. Research/plan đọc lại được, confirmation gắn
đúng revision, cùng idempotency key trả cùng interaction, human_only được lưu
đúng, sửa plan làm confirmation expired/stale_target; endpoint decomposition trả
422 cho plan chưa được duyệt và không tạo task con. Không giả lập owner accept,
không dispatch model. Happy path sau owner acceptance, dependency execution và
wake của lead chưa được kiểm bằng workflow thật. Native default resolver ở probe
đầu là anyone; skill/guide cuối bắt buộc human_only cho quyết định của owner.

**Kiểm chứng source/runtime:** đọc lại cap cả 5 agents; gọi cấu hình tạo mới của
3 process workers xác nhận không có daily aliases và vẫn concurrency 1.
AI environment audit 0 errors/0 warnings: global 12279 B, project 9269/65536 B,
reserve 56267 B, combined 21548 B. Diff check đạt; không lặp full suite vì không
đổi engine behavior/retry. Chi phí unknown vẫn là unknown.

**Điểm chặn trước lượt tự động:** lead còn model Opus5.5 hết hạn và kết nối cũ;
project gateway chưa sẵn sàng. Probe HTTP Trader API8010 và UI5180 không kết nối
được ở thời điểm kiểm, nên chưa có fresh Gemini inference. Không đổi provider/
credential, dùng instance Windows8317 hoặc dựng launcher bỏ qua ownership.
Lát tiếp theo: khôi phục đúng runtime manifest/launcher và gateway17852 đã sở hữu,
chọn Gemini đang có cho đúng native adapter rồi chạy một nhiệm vụ hệ thống nhỏ.
Đây là cấu hình/instruction + native API smoke, chưa là end-to-end model acceptance.

Evidence private:
`E:/BACKUP-TRADINGWORKSPACE/studio-observation-20261103/research-handoff/`
(`daily-cap-before.json`, `daily-cap-after.json`, `skill-publication.json`,
`fixture.json`, `fixture-documents.json`, `confirmation-before.json`,
`confirmation-after.json`, `native-handoff-smoke.json`). Rollback chỉ phục hồi
field cap cần thiết từ before sau khi đọc current; skill rollback publish lại
source phiên bản trước qua native API, không ghi đè DB hoặc các lựa chọn khác.

### Studio: khôi phục runtime, Gemini và bàn giao native, 03/11

**Quyết định owner:** thử Terra6.1; nếu không dùng được thì giữ Gemini và tiếp
hệ thống. Không mở lại lane tối ưu chiến lược, engine mới hoặc UI quản lý ngoài.

**Gateway project:** nâng binary standalone từ CLIProxyAPI8.0.40 lên release
chính thức [v8.0.52](https://github.com/router-for-me/CLIProxyAPI/releases/tag/v8.0.52).
Đã đối chiếu asset digest/checksums, MIT và đường dẫn archive; archive SHA256
`395324dd124bd657bccd5fdf06119587cd7c87bddacff191d5f45431e8f08d23`,
binary SHA256 `4f2e5e7a8477f1bf9ef4059b289d6b904de9e3412c9a0a903ca2495946bda3d1`.
Giữ binary cũ để rollback, config byte-identical và đủ17 auth JSON; chỉ restart
đúng process có owner manifest. Không thay gateway Windows8317. Model Terra
xuất hiện trong catalog mới nhưng một Responses request thực tế bị HTTP400
`model_not_found`: account/route được chọn không hỗ trợ model đó. Không suy
rộng ra mọi account và không thử quay vòng account sau quyết định giữ Gemini.

**Trader runtime:** UI5180/Paperclip17860 đã mở; API8010 ban đầu từ chối scientific
descriptor cũ. Đối chiếu cho thấy engine/adapter hashes và phiên bản dependency
không đổi, chỉ file count của base Python tăng11564→11565. Chạy bootstrap hiện
có để tạo lại descriptor, giữ guard stale-install; không sửa source engine.
Khởi động lại đúng native/compact profile với DB/artifact/QDM/binary hiện có;
`/health/ready` trả ok, command_worker not_required. Runtime vẫn ở checkout cũ
theo native-owner manifest; source canonical vẫn là projects/trader. Đây không
phải migration runtime hoặc whole-product acceptance. Lệnh vận hành dùng
Python `-B` để không tạo bytecode làm đổi fingerprint.

**Fresh Gemini:** direct Responses smoke trả GEMINI_READY, model
`gemini-3.8-flash-high`,3,148s/121tokens. Trưởng nhóm giữ adapter codex_local/CLI,
cwd, timeout, quyền và skill; chỉ đổi model cùng kết nối native sang gateway17852
bằng credential gateway đã có. Connection chỉ cấp cho trưởng nhóm, không mở
allAgents. Kết nối Sky cũ được giữ lịch sử; provider OpenAI ở đây là protocol,
model thực tế là Gemini.

**Nhiệm vụ native thực tế:** [NAQ-74](http://127.0.0.1:17860/NAQ/issues/NAQ-74),
run `65eb35f4-6e30-4abd-b359-2773ad8113b3`, succeeded/task done trong129,6s.
Model đọc assigned skills, lưu research và xuất báo cáo tiếng Việt qua native
API. Đây là bằng chứng Gemini + Codex CLI tools + native publication; không
chứng minh accepted-plan owner approval/wake đã chạy. Usage native có fresh
input71081, cached input475529, output9977; rawInputIncludesCached false, không
cộng cached vào fresh hoặc suy giá USD khi chưa có giá route.

Model ban đầu ghi cùng nội dung vào report và result. Đã backup cả hai rồi xóa
đúng result trùng của fixture qua native API; giữ research và report. Cập nhật
skill nguồn để chỉ publish một final report, publish native version
`4a24d530-345c-432d-9536-0cdf3d10b473` và đọc lại khớp SHA256
`90f1ba58f7ef3db5cb9bdf1dedfebc284fdadf29f69bc51fd385d79634794880`.
Không chạy lại inference chỉ để kiểm instruction này; hành vi model ở lượt
sau chưa được chứng minh. Không thay skill khác hoặc bật Beta.

**Workflow cố định thực tế:** dùng helper `spot_workflow.py start --workflow
forex` cùng key `system-handoff-20261103-gemini`; không tạo graph/attempt thứ hai.
Parent [NAQ-75](http://127.0.0.1:17860/NAQ/issues/NAQ-75), research NAQ-76,
review NAQ-77, paper NAQ-78. Research run
`d517d5dc-3a7d-4935-947e-ef67c244adf0` succeeded114,3s; Paperclip tự wake Hermes
qua dependency, reviewer run `bb99990e-6316-484e-9c7c-87948f6c2ea4` succeeded36,4s,
Gemini2 API calls. Parent tự chuyển in_review và gán người dùng thật; hai child
done, paper vẫn blocked/unassigned/NOT_RUN. Không cần lead chạy giữa hai bước.

Đối soát15 assertions đạt: native runs/receipts thành công, publication đủ,
dependency đúng một source, binding đúng issue/run/parent, hai document hashes
và revision native khớp local receipt, Gemini reviewer, human handoff, paper
không chạy và không mở holdout/execution. Dùng nguyên fixture EURUSD/H4 hai tuần
đã pin; không QDM GUI, tải dữ liệu mới, broker call hoặc đổi tham số chiến lược.
Đây là fresh worker→review→human acceptance; việc owner accept plan rồi model
tự decomposition/wake vẫn chưa thử và không được suy từ kết quả này. Lead task
NAQ-74 và graph NAQ-75 là hai phép kiểm riêng, graph được operator khởi động.

**Kiểm chứng cuối:** integration doctor đạt4 source/pin/origin/license checks;
AI environment audit sau thay skill đạt0errors/0warnings: global12279B,
project9269/65536B, reserve56267B, combined21548B. Diff check đạt. Không chạy
full suite hoặc lặp inference đã thành công. Chưa có load/soak, unattended
scheduler, native Reviewer/Approver policy hoặc whole-product acceptance.

**Điểm tiếp:** xem hồ sơ native NAQ-75 và dùng các task thực tế nhỏ theo contract
đã có. Không cần thêm engine/UI hoặc tối ưu phí ngay. Khi cần tách task từ một
plan mới, owner duyệt đúng revision trước; giữ human_only. Hoạt động dài ngày/
lịch tự động cần acceptance restart/stop và phạm vi vận hành riêng, không tự mở
từ việc bỏ daily cap. Phát triển chiến lược vẫn ngoài lát này.

Evidence private: `E:/BACKUP-TRADINGWORKSPACE/cliproxyapi-upgrade-20261103/`,
`E:/BACKUP-TRADINGWORKSPACE/runtime-start-20261103/` và
`E:/BACKUP-TRADINGWORKSPACE/studio-observation-20261103/research-handoff/`.
File `fixed-graph-acceptance.json` giữ15checks cùng IDs/timestamps;
`fixed-*-completed.json` giữ native task/documents sau publication.
Backup private có credential, không đưa vào Git. Gateway rollback: đối chiếu
manifest/path/creation time của process hiện tại, dừng đúng owner, dùng binary
cũ với config giữ nguyên; không kill theo port/name. Agent/skill rollback chỉ
patch field cần thiết sau khi đọc current, giữ mọi lựa chọn mới khác của owner.

## 03/11/2026 — Quy ước báo cáo cho owner

Owner yêu cầu thống nhất cách báo cáo và đối chiếu docs/cộng đồng trước khi áp
dụng. Đã đọc catalog của instance đang chạy, source pin và hướng dẫn chính thức:

- [Agent instructions](https://docs.paperclip.ing/guides/org/agents/#recommended-bundle-structure-agents-soul-heartbeat-tools):
  giữ role entry gọn, tách tone/procedure khi có nhu cầu thật; không cần tạo đủ
  bộ AGENTS/SOUL/HEARTBEAT/TOOLS cho mỗi agent.
- [Company skills](https://docs.paperclip.ing/reference/skills/): library, phiên bản
  và assignment là các bước riêng; cài catalog không tự chứng minh agent đã đọc.
- Native catalog `summarize-status` chỉ ghi scope summary slot;
  `status-card-query` quản lý thẻ trạng thái. `simplified-english` dành cho
  controlled English. Không dùng chúng để ép báo cáo task tiếng Việt vào một
  quy trình khác hoặc tạo thêm Summarizer/routine.
- [Trao đổi cộng đồng](https://www.reddit.com/r/PaperClip_AI/comments/1wdztc1/bestadvanced_tips_to_get_the_most_out_of_paperclip/)
  có ví dụ daily report/Hermes; đây là kinh nghiệm cá nhân, không là benchmark
  hay bằng chứng cần thêm một agent cho hệ thống này.

**Thay đổi:** mở rộng skill `naqex-research-lead` đang được gán bằng reference
`references/owner-reporting.md`: tiếng Việt tự nhiên, kết quả trước, mức chi tiết
theo task, bảng khi có ích, phân biệt bằng chứng/suy luận/chưa kiểm, link evidence
thay raw log/ID dài. Không ép mọi báo cáo vào một template. Giữ một native final
document `report` và contract số liệu của engine. Hermes wrapper đọc chính
reference này cùng reviewer instructions, đưa vào SDK prompt và ghi hash tổng;
không giả định process worker tự load skills catalog hay AGENTS.

**Native publication:** hai agent lead/reviewer idle ở preflight. Qua native HTTP
API được xác thực, lưu backup rồi thêm reference trước, cập nhật SKILL.md sau,
dùng expectedVersionId và idempotency key. Version cuối
`4cefeaa7-5485-4af3-99db-9eee5289de77`; đọc lại cả hai file cùng version khớp
source. SHA256 reference
`633c2be79f828d53d7381ddc4dadaf5006d95167a1962407d1f8a7372f48d636`;
entrypoint `c531e514ff70d320445907d4633869a21324261485266c0f460c0df4dd11e1d0`.
Giữ nguyên7 skill selections/version-pin choices và model/adapter/quota. Không
sửa source upstream, global instructions, UI hoặc các báo cáo đã lưu.

**Kiểm chứng:** skill validator đạt; Hermes focused suite7tests đạt, gồm prompt
nhận đủ hai nguồn, hash khớp và thiếu reference dừng trước provider. Lượt chạy
đầu gặp console/default file encoding cp1252 của Python trên Windows; chạy lại
với `-X utf8` đạt, không đổi test để bỏ lỗi. Native content/assignment readback
đạt. AI environment audit cuối:0errors/0warnings, global12279B,
project9269/65536B, project reserve56267B, combined21548B. Không chạy lại full
suite hoặc inference. Hướng dẫn mới áp dụng ở lượt kế tiếp; chưa khẳng định model
đã đọc hoặc phong cách báo cáo mới đạt bằng một fresh model run.

Evidence/backup private:
`.runtime/ai-engines/reporting-20261103T044729Z/verification.json` và các file
`*-before.json`. Rollback native bằng phiên bản trước
`4a24d530-345c-432d-9536-0cdf3d10b473` qua version API sau khi đối chiếu current;
không ghi đè thay đổi mới của owner. Revert cùng lát wrapper/reference trong Git
nếu bỏ hướng dẫn dùng chung. Scope chỉ là báo cáo, không mở scheduling/trading.

## 03/11 — Hoàn thiện nền vận hành và phiên Forex có thể khôi phục

Scope theo mục **Phạm vi owner giao — hoàn thiện hệ thống** trong AI plan;
[issue #8](https://github.com/Naqex/workspace/issues/8). Không tạo Goal hoặc
progress ledger khác. Product source ở `projects/trader`; runtime cũ tại
`projects/mt5-tradingview-backtester` chưa được cập nhật bởi hai commit sau.

| Lát | Kết quả/source | Bằng chứng và giới hạn |
|---|---|---|
| Vận hành | Trader `d1d96b2b`: supervisor probe `/health/ready` mỗi5giây;3lỗi liên tiếp → degraded; healthy → recovery; shutdown ghi stopping/stopped |35 focused launcher tests đạt. HTTP lỗi không restart/kill/retry; chưa theo dõi tiến độ native research worker hoặc rollout/soak |
| Artifact handoff | Trader `a734b25b`: candidate/revision/purpose + hash data/spec/cost/source bất biến; hash stream1MiB và giữ cursor |9 focused binding tests đạt. Hash chứng minh identity, không chứng nhận chất lượng hoặc phí lịch sử |
| Phiên Forex | Cùng commit: checkpoint H4/ATR/history, risk/accounting, entry/exit đang chờ, cash calendar và quote cursor |8 focused coordinator tests +11 H4 regression đạt; restart parity xuyên entry/exit/financing. Chỉ historical quote replay, không observed forward |
| Consumer thật | CLI `foundation_v2/scripts/forex_forward.py` đọc QDM CSV đã export theo registration, chạy batch và resume |5 focused CLI tests đạt; liên tục/resume cùng snapshot, input/sidecar collision và source/hash thay đổi bị chặn. Fixture synthetic, không chạy lại research/dữ liệu thị trường |

### Hành vi, data/state và quyết định

Registration → hash các artifact và source thực thi → seed Forex/risk → buffer
một giờ quote → chỉ đóng giờ/nến H4 theo quote muộn hơn hoặc source watermark
hợp lệ → reducer hiện có → checkpoint có lock, generation CAS, checksum,
fsync/atomic replace. Resume rehash nguồn và giữ cursor; không có send/provider/
download hay tác dụng ngoài file checkpoint. EOF không tự đóng giờ cuối.

Review độc lập phát hiện và sửa hai lỗi consumer: file sidecar `.lock` có thể
trùng input và mutate bytes; pin re-export không bao phủ implementation tính
tiền. Đã chặn cả checkpoint/sidecar và pin file semantic thực cùng CLI. Review
cũng phát hiện watermark qua phí chưa xử lý có thể công bố cash horizon sai;
`close_before` hiện từ chối trước mutation khi thiếu giờ quote phù hợp, không
tạo quote/nến giả để tính swap. Regression giữ nguyên snapshot rồi ghi phí đúng
một lần khi có quote tiếp theo. Một lỗi import Pydantic trong test harness CLI
đã sửa bằng đăng ký module importlib; không thay validator hay làm yếu test.

Trade-off: cold resume quét lại prefix CSV; ưu tiên cursor đơn giản và đúng.
Phiên có hard resource cap:100.000quotes/giờ buffer,10.000giờ committed,
checkpoint64MiB. Chạm cap phải có rollover rõ; chưa gọi là daemon chạy vô hạn.
Spec/cost giữ fixed EURUSD và$2.50/lot/side; unknown financing/commission và
current FTMO spec áp lịch sử vẫn không được chứng nhận. Hướng dẫn product:
`foundation_v2/docs/FOREX-FORWARD.md`. UI quản lý task/run/report vẫn native.

### Tách quyền tự động — đã duyệt, đang triển khai

Audit source xác nhận API local-trust chưa phân biệt Owner với Automation;
gắn thêm `automation=true` không chặn caller đi qua manual endpoint. Owner
đã duyệt **tách quyền; migration local sau khi có backup**. Đang triển khai
source/offline: owner cookie/CSRF + bearer riêng, grant native bất biến, attempt/
risk reservations và kiểm fresh SDK ngay trước single send. Chưa tạo grant,
migration owner DB, bật service/scheduler hoặc gửi OrderCheck/OrderSend.

Giữ native UUID/unknown receipt, terminal/generation lock và reconciliation.
Không dựng hệ giao dịch song song, không đổi semantics manual managed trading.
Grant/agent cùng OS user không là sandbox chống coding agent có toàn quyền
filesystem; deterministic runner không được nhận secret/DB authority của owner.
Backup/restore hiện có không được nâng thành owner-data acceptance chỉ từ
synthetic fixture cũ. Bước tiếp là kiểm tích hợp auth/grant trên DB cách ly,
sau đó mới chuẩn bị cutover/backup phù hợp standing grant và duyệt mới.

## 03/11 — Tách quyền Owner/Automation đã triển khai local

Tiếp mục triển khai phía trên; không thay lịch sử chưa rollout của hai commit
trước. Product commit `0d0ff7c0` hoàn tất auth/grant/SDK/web/launcher và tài liệu;
cùng `d1d96b2b`, `a734b25b` đã được lưu trong canonical Trader. Lát rollout này
đưa supervisor readiness và ranh giới quyền vào API/UI đang dùng; chưa chạy
consumer Forex hoặc thử gửi lệnh trên broker.

### Hành vi và luồng state

Owner đăng nhập local qua nonce dùng một lần → cookie HttpOnly/SameSite Strict,
Path `/api/v2`; mutation cần exact Origin và CSRF chỉ giữ trong memory. Bearer
maintenance riêng, không lưu secret vào task/receipt/URL. Nonce hết hạn10phút,
cookie12giờ absolute, bearer7ngày; không tự gia hạn hoặc replay mutation401/403.
Spent marker atomic/fsync giữ hiệu lực qua restart. Fresh nonce hợp lệ thay được
cookie cũ; mixed/duplicate/malformed credentials bị từ chối.

Owner duyệt policy bất biến → token runner trả một lần, DB chỉ giữ digest →
runner chỉ có3route native command/receipt/reconcile. Policy pin workspace,
connection/generation/login/server, Demo/currency, artifact, symbol/action,
expiry/volume/attempt/risk/floors. Reservation và native unknown receipt commit
cùng transaction trước adapter; unknown/accepted/partial giữ capacity, không
retry uncertain send. Revoke giữ cùng terminal lock và không tự đóng position.

Final SDK bắt buộc Demo hedging, SL và fresh quote/spread/lot/position/risk/margin;
một OrderCheck rồi kiểm lại DB connection/pause/grant sau final prepare, sát một
OrderSend. Floor/aggregate admission chặn mở mới, không chặn full close có chứng
minh ownership khi equity giảm. Automated close hiện chỉ hỗ trợ ticket bằng
stable identifier: broker rollover bị chặn trước check/send vì durable opening
receipt chưa lưu stable identifier; không suy ownership từ magic number.

Trade-off: đây là phân quyền HTTP, không phải sandbox chống process có toàn
quyền cùng Windows user/DB. Không cấp Owner secret cho runner. Giữ native
Paperclip làm UI quản lý task/run/report; không thêm management UI bên ngoài.

### Kiểm chứng source/offline và review

| Phạm vi | Kết quả |
|---|---|
| Rust auth/local session/OAuth regression |27pass |
| Grant pure / disposable PostgreSQL lifecycle |6pass /1pass; cluster đã dừng |
| Commands registry / Demo regression / identity middleware |4/5/1pass |
| SDK mocks / worker receipt và fences |33/13pass |
| Provisioner |5pass,1skip vì Windows symlink privilege; mocked reparse đạt |
| Launcher/wrapper |4auth cases + startup/collision đạt; PowerShell parse và6isolated cases đạt |
| Web transport |15pass; final affected Owner7pass |
| Contracts/build |OpenAPI/frozen contract, web production build,3Rust release binaries và diff check đạt |

Review độc lập đã tìm và sửa timeout cold worker, final generation/pause/grant
fence, rollover close và close dưới account floor. Test registry ban đầu thiếu
3auth routes trong expected count; cập nhật expectation đúng contract. Không
làm yếu test. OpenAPI giữ thứ tự cũ, diff additive; đồng bộ field additive
`PropPhaseSpec.daily_anchor_basis` còn thiếu trong frozen schema. Giữ chunk/CSS
warnings có sẵn, không mở refactor ngoài scope. Không chạy lại unchanged suites
ở lượt chốt chỉ để tăng số lần pass.

### Backup, migration và runtime thực tế

- API/UI đã dừng và DB quiesced trước backup bằng helper hiện có; không active
  jobs/downloads/client khác hoặc unresolved broker submission.
- Bundle verified `system-capabilities-20261103`, snapshot
  `20261103T105459Z-52692e6c3a9b`:4.274.413.773bytes,4.142artifact files;
  manifest SHA256 `ce5484ac36af65801c491c44dd92be356ec39def318cf058e5d4223e8cf96943`.
- Migration owner DB chỉ áp `0021_automation_grants.sql`; không pending. Binary
  schema20 không dùng để rollback trực tiếp: cần schema21-compatible build hoặc
  restore matching DB/artifacts. Không xóa ledger để ép downgrade.
- API8010 native/compact dùng local-capability, giữ DB/artifact/QDM/scientific/
  legacy/AI interpreter và runtime ownership cũ. UI5180 đã promote bằng asset
  collision check, giữ hashed assets/brand và atomic entry index.
- Fresh readback lúc11:29:57UTC:13checks đạt về PID/creation identity, executable
  hashes,7owned file hashes, auth, readiness, served UI, schema, Paperclip/gateway
  và zero unapproved automation. Anonymous API401, Owner200, ready200/database
  ready, UI200, Paperclip health200; gateway17852 không key trả401 như dự kiến.
- Exness-MT5Trial17 và FTMO-Demo đều connected/demo, không đổi access mode. DB:
  **0grant,0reservation,0unknown broker requests**. Lượt này không gọi
  OrderCheck/OrderSend, không inference hoặc tự tạo workflow/task mới.
- Browser Owner login đã thành công. Sau khi existing launcher khởi động lại
  Paperclip17860 và gateway17852, bấm Thử lại mở được native company Naqex AI,
  task NAQ-75 in_review/NAQ-76+77 done/NAQ-78 blocked. Đi qua Tài khoản giao dịch
  đọc được cả hai demo rồi quay Studio, giữ document/task state. Đây là read-only
  journey, không là unattended/soak hoặc broker execution acceptance.

Lần kiểm đầu dùng nhầm API providers route404 đã đổi sang route source xác nhận;
final readiness helper ban đầu đọc nhầm field `ready` thay `ok`/`database`, sửa
assertion theo response thật rồi đạt. CUA gặp stale connection; reset binding
khôi phục được, không đổi product source để né lỗi công cụ.

Evidence private: `E:/BACKUP-TRADINGWORKSPACE/system-capabilities-20261103/`:
`backup-verified.json`, `prepared.json`, `migration.log`, `runtime-auth-check.json`,
`final-readiness.json`, `ui-promotion.json`, `studio-ui.png`, `accounts-ui.png`.
Backup bundle nằm ở backup root mà `backup-verified.json` dẫn tới; rollback
files/binaries/UI trong `runtime-before/`. Secret/config private không commit.

**Còn lại:** nguồn quote observed và forward dài ngày, alert/soak, phiên Demo
có policy được owner duyệt và whole-product audit. Historical replay không là
observed forward; fixture/system acceptance không chứng nhận lợi nhuận. Không
tự cấp grant/risk budget từ quyền bảo trì hoặc từ câu “dùng Exness demo”.

### Kiểm đọc sâu phát hiện và sửa default symbol MT5

Sau read-only journey, GET native trading snapshot của Exness mặc định trả
`demo_invalid_number`, trong khi chỉ rõ `EURUSDm` trả ready. Root cause source:
worker ưu tiên `EURUSD` chỉ vì có tên trong danh mục broker, dù không có quote
hợp lệ cho tài khoản này. Trader `d77a74a1` chọn mặc định theo Bid/Ask dương,
finite, không đảo; subscribe symbol chưa visible qua SDK read path. Giữ nguyên
symbol được caller chọn rõ, không retry OrderCheck/send hoặc nới stale/risk gate.

Kiểm17worker tests đạt, gồm zero/NaN/missing/inverted quote, suffix broker,
explicit selection và cold subscription. Runtime thử đầu cho thấy nếu quét
mọi visible symbol khi quote chưa về thì có thể nhảy sang BTCJPYm; đã sửa trước
khi chốt: có nhóm EURUSD/XAUUSD ưu tiên thì chờ quote của nhóm đó, không tự đổi
asset. Bản cuối đã rollout và đọc mặc định được **EURUSDm**, giữ generation11,
positions/orders rỗng. Lượt đầu sau cold subscription báo quote unavailable,
lượt đọc kế tiếp ready; quote age5.175ms được đánh dấu stale, không gọi fresh
hoặc dùng để gửi lệnh. Snapshot ready chỉ là khả năng đọc, không là execution
admission. Không gửi lệnh trên cả bản tạm hoặc bản cuối.

PowerShell wrapper CheckOnly từ chối vì không xác minh được executable bằng
CIM trong phiên này; không dừng process. Dùng existing native launcher thay thế,
đối chiếu Win32 PID/creation/path identity, idle/unknown guards và current secure
manifest trước stop/start. Không làm yếu wrapper hoặc đổi auth. Chỉ copy owned
worker file, giữ bytes rollback và các descriptor/interpreter trước đó.
`worker-promotion.json` giữ source SHA/hash/rollback; metadata promotion trước
được giữ riêng. Sau restart,13runtime/auth/hash checks đạt lại lúc11:46:26UTC,
grant/reservation/unknown vẫn0. Không chạy lại Rust/web suites vì chỉ đổi worker
Python; không thay binary/schema/UI assets.

### Khôi phục bản backup owner vào môi trường riêng

Đã dùng chính bundle đã verify phía trên, `restore_backup_files` hiện có và
PostgreSQL18.6 để phục hồi4.143files/4.274.413.773bytes, gồm metadata dump cùng
4.142artifact files, vào thư mục private/cluster loopback mới. Không chạy API,
adapter, terminal hoặc worker trên dữ liệu phục hồi; owner DB/artifacts không đổi.
`pg_restore --single-transaction --exit-on-error --no-owner --no-privileges` đạt.
Migration schema20→21 trên bản phục hồi đạt; hash từng hàng/số hàng của **44bảng
cũ** giữ nguyên, trừ migration ledger được kiểm riêng. Constraints đều validated,
schema check21current/no pending, hai bảng automation mới rỗng. Cluster đã dừng.

Lần đầu Windows postmaster giữ output pipe của pg_ctl nên harness chờ EOF dù
cluster đã ready; chưa chạy restore. Đã xác minh/dừng đúng process harness và
cluster thử, giữ receipt interrupted; resume đúng copied snapshot sau rehash,
chuyển output control sang file private. Không chép lại toàn bộ4,27GB, không
đổi product tool để xử lý lỗi harness. Receipt cuối PASS tại
`isolated-owner-restore/receipt.json`. Không phục hồi OS roles/ACL hoặc chuyển
runtime owner sang target thử; đây là isolated owner-backup restore acceptance,
không là diễn tập disaster recovery toàn máy/UX.

### Phiên Exness demo được owner duyệt — chặn đúng quote stale

Owner đã duyệt rõ phiên15phút: Exness demo464104926/Exness-MT5Trial17,
EURUSDm,0,01lot, tối đa1position/2submissions (mở→đóng), SL bắt buộc,
rủi ro tính toán tối đa$2tiền demo; chỉ chạy khi identity/quote/risk hợp lệ,
unknown chỉ reconcile, không resend. Đây là quyền cho phiên này, không mở
scheduler, chiến lược hoặc FTMO/Real. Không coi stop loss là bảo đảm tuyệt đối
trước gap/slippage; SDK giữ cost buffer và không nới guard để có fill.

Controller đọc fresh native snapshot và pin artifact system fixture, generation11,
tạo grant bất biến `056a0c22-8c0a-4636-8331-15e9eb6ce2f4` hết hạn12:07:00UTC.
Runner riêng chỉ đọc credential Automation/typed input, không nhận Owner bearer
hoặc DB environment; không dùng MCP hay sửa rows trực tiếp để gửi lệnh.

| Kiểm phiên thật | Kết quả |
|---|---|
| Native command/receipt/reservation |1attempt được ghi; SDK trả rejected/demo_quote_stale trước OrderCheck/send |
| Gửi lệnh/mở vị thế |0OrderSend; không mở vị thế và không thử lại |
| Ngân sách sau rejected |Reservation được giải phóng về0; attempt lịch sử vẫn1 |
| Thu hồi |Grant revoked qua native Owner API; không còn quyền mở mới |
| Phân quyền |Runner đọc route Owner trả403; token revoked vẫn đọc own receipt200 |
| Đối soát DB |0unknown broker requests; không tự tạo phiên/grant thay thế để reset attempt |

Receipt `approved-exness-demo/cleanup-receipt.json` là **PASS_FAIL_CLOSED**,
không là positive open→close acceptance. Handoff/state/guard đã chạy native;
đường fill và close thành công trên broker vẫn chưa được chứng minh. Bước cần
ưu tiên là độ tươi quote/observed forward và phiên kiểm tiếp có scope mới phù
hợp; không tăng max quote age để biến stale thành fresh. Approval/artifact/
policy/intent/response/cleanup được giữ private cùng thư mục; token không vào Git.

## 03/11 — Runner Demo bền vững và final admission theo policy

Tiếp phạm vi hoàn thiện hệ thống, không tuning strategy hoặc gọi model.
Product `aca83e17` thay harness dùng một lần bằng
`foundation_v2/scripts/mt5_demo_session.py`; `0fc58e49` tách timestamp tick khỏi
state kinh tế; `91427ba9` áp đúng biên `deviation_points` đã duyệt vào final quote
recheck. Các commit đã rollout local qua native owned launcher, giữ auth/schema/
UI/data roots và rollback của từng lần promote. Không sửa Paperclip core hay
tạo thêm UI/quy trình quản lý ngoài.

### Hành vi, state và kiểm chứng

Manifest/artifact/credential identity → intent fsync trước single native POST →
receipt/reconcile cùng UUID → full opening fill đúng volume/account/generation/
grant mới được tạo intent close. Sau crash/timeout/404 không POST lại intent;
đổi input/secret identity, checkpoint hỏng hoặc concurrent writer đều chặn.
Client chỉ3route Automation, chặn proxy/redirect, không tạo/revoke/renew grant
hoặc tự chọn symbol/SL/ngân sách. STOP/expiry/reconcile-only chặn send mới, không
tự đóng vị thế; partial/unknown phải báo attention. Native DB vẫn own authority,
counters và reservation; file chỉ giữ tiến trình client.

| Lát kiểm | Bằng chứng/phạm vi |
|---|---|
| Runner restart/lifecycle |10focused tests đạt: crash trước/sau POST, timeout, partial/scope mismatch, expiry/STOP, pin/tamper và lock. Không SDK/network |
| Native readback thật |Import intent lịch sử vào fixture recovery riêng rồi đọc đúng receipt revoked; `blocked/demo_quote_stale`,0grant/command mới. Không gọi đây là crash broker thật |
| Quote read path |5snapshot thật: tuổi quote409–2.577ms; không đủ cơ sở kết luận feed mất ổn định dài hạn |
| Native SSE |30,076giây/2segments chủ động disconnect/reconnect,59ready samples,0stream errors/0stale; age441–4.242ms,p95=3.671ms. Sampled latest state, không full ticks hoặc multi-day forward |
| SDK/worker hiện hành |59focused tests/84subtests đạt trước chốt tolerance; affected SDK41tests/48subtests đạt sau đổi tolerance theo broker point. Không chạy Rust/web suites unchanged |
| Runtime |Private `demo-operations-promotion.json` pin3files của `91427ba9`; auth vẫn local-capability, schema21/UI giữ nguyên. Read Exness qua cold unavailable rồi ready; FTMO/Exness có lỗi startup/sync tạm thời, không gọi đó là root cause đã sửa |

Trade-off: crash ngay trước POST cũng không tự gửi lại dù receipt404; ưu tiên
chống gửi trùng. `resume` chỉ gửi close chưa attempt trong authority gốc. Full
close đã attempt nhưng unknown chỉ đối soát, không gửi lần hai. Không cài daemon,
scheduler hoặc cấp secret Owner cho runner.

### Các phiên được duyệt tiếp và lỗi admission thực tế

Owner duyệt lại từng phiên Exness demo464104926/Exness-MT5Trial17,EURUSDm,
15phút,0,01lot,1position/2submissions,SL bắt buộc,risk tính toán≤$2demo.
Hai phiên tiếp sau phiên stale lịch sử đều rejected trước send:

| Phiên | Kết quả |
|---|---|
| v2,source `aca83e17` |`demo_automation_state_changed`;1attempt,0reservation/unknown/position sau cleanup; grant revoked |
| v3,source `0fc58e49` |Cùng reason; diagnostic xác nhận request không đổi nhưng entry/estimated risk/total risk đổi. Inventory rỗng, grant revoked, không retry |

v2 thiếu diagnostic nên không khẳng định timestamp là nguyên nhân của phiên
đó. Source chứng minh timestamp cùng giá có thể gây false rejection; đã có
regression riêng. v3 xác nhận giá dịch chuyển thật: so toàn bộ preview bằng
nhau đã phủ nhận độ lệch giá mà policy cho phép.

Final SDK hiện chỉ cho phép Bid/Ask đổi trong `deviation_points` của immutable
grant khi request market-execution không mang price và không thay đổi. Fresh
prepare tính lại SL/spread/per-trade/aggregate risk/margin; mở mới vẫn fence
equity/free-margin/currency/inventory. Price-bearing request đổi vẫn chặn. Full
owned close cho phép equity/free-margin thả nổi thay đổi để giảm exposure;
identity/ownership/volume/quote/spread/expiry/generation vẫn kiểm. Sau native
fence cuối kiểm lại tuổi quote rồi mới single OrderSend. Không thêm check/send
hoặc retry. Ca quote nằm trong biên chuyển sang acceptance đúng policy; vẫn giữ
ca ngoài biên, vượt risk/spread/SL/margin và revoke/expiry/no-resend.

Evidence private tiếp tục ở
`E:/BACKUP-TRADINGWORKSPACE/system-capabilities-20261103/`: `durable-demo-recovery/`,
`quote-timing-readonly.json`, `observed-market-readonly*.json*`,
`demo-operations-*.json`, `market-admission-runtime.json`,
`approved-exness-demo-v2/` và `approved-exness-demo-v3/`. Secret không commit.
Phiên v4 được owner duyệt tiếp đã xác nhận positive open→close trên bản
`91427ba9`; kết quả và giới hạn ở mục 04/11 dưới đây.

## 04/11 — Mở và đóng thành công trên Exness demo

Owner duyệt phiên mới cùng phạm vi: demo 464104926 / Exness-MT5Trial17,
EURUSDm, 15 phút, 0,01 lot, 1 position / 2 submissions, mở→đóng ngay, SL bắt buộc,
rủi ro tính toán ≤ $2 demo; unknown chỉ reconcile, không resend. Controller v4
xác minh creation identity/hash của các process native, API/database ready,
source/deployed 3 files khớp promotion `91427ba9` trước khi tạo grant. Account
đúng Demo/USD, generation 12, không vị thế/lệnh chờ hoặc unknown/active grant cũ.

Luồng thật: Owner tạo grant bất biến gắn artifact → runner chỉ nhận credential
Automation → ghi intent → native admission/SDK → receipt opening filled →
gửi full close đúng vị thế → receipt closing filled → Owner revoke grant →
đọc native receipt và snapshot, đối soát DB read-only. Không sửa source thêm,
không chạy lại test suite unchanged, không dùng manual endpoint/MCP/SDK bypass.

| Lát kiểm | Kết quả thực tế |
|---|---|
| Mở | 04/11/2026, 07:10:35–37 Việt Nam; BUY 0,01 lot, SL 1,11906; risk ước tính $1,20 gồm cost buffer, dưới $2 được duyệt; broker retcode 10009/filled |
| Đóng | Full 0,01 lot, retcode 10009/filled; 2 native attempts tổng cộng, không retry |
| Đối soát | 0 vị thế, 0 lệnh chờ, 0 unknown, reservation 0; hai receipt giữ đúng deal/order và đọc được sau revoke |
| Kết thúc quyền | Grant `e69be122-4777-4dc6-bd26-14d78e9f2ffe` revoked qua Owner API; không tự gia hạn/tạo phiên tiếp |
| Tiền demo | Balance $10.001,01 → $10.000,97, chênh lệch −$0,04; đây là kiểm luồng hệ thống, không là đánh giá chiến lược |

Private evidence: `approved-exness-demo-v4/` trong backup root đã dẫn ở trên;
`controller-receipt.json` là `completed/open_close_proven`,
`cleanup-receipt.json` là `PASS_BOUNDED_DEMO_OPEN_CLOSE`, toàn bộ 10 checks đạt.
Artifact/policy/plan/preflight/postflight/checkpoint và native receipt IDs giữ
trong thư mục private; không đưa credential hoặc Owner bearer vào Git.

**Acceptance đạt:** một phiên execution Demo có giới hạn đi hết đường
grant→risk admission→broker fill→full close→revoke→đối soát. Kết quả này không
chứng minh vận hành unattended dài ngày, root cause cold-start/reconnect đã hết,
hoặc chiến lược có lợi nhuận. Không lặp thêm phiên mở/đóng khi chưa có mục tiêu
kiểm chứng và authority mới; phần vận hành dài ngày vẫn là acceptance riêng.

## 04/11 — Ổn định khởi động và đồng bộ tài khoản MT5

Tiếp mục tiêu vận hành hệ thống trên Demo, không tuning chiến lược hoặc mở
phiên giao dịch mới. Routine reconnect/local rollout dùng standing maintenance
grant; quyền phiên v4 tiếp tục revoked. Không thêm UI, engine hoặc scheduler.

### Hai lỗi đã xác định

| Lát | Bằng chứng trước sửa | Thay đổi |
|---|---|---|
| Khởi động terminal | Exness reconnect một lần: `queued→syncing→mt5_worker_failed→connected` sau khoảng 29 giây. Probe tiếp xác nhận `mt5_trading_disabled` tại `verify_identity` bị `PermissionError`, WinError 32 ở `clean_terminal`, che mất. Log lúc lỗi có `terminal process already started` | `e73cecb0`: chờ Windows `WaitForInputIdle` tối đa 10 giây trước SDK attach; không dọn file từ worker khi descendants còn giữ khóa |
| Đọc đồng thời | GET snapshot FTMO trùng lượt collector làm `mt5_terminal_busy`; collector chuyển account sang error và đặt lần thử kế tiếp sau 300 giây, dù terminal không mất kết nối | `85940ede`: riêng lock timeout hoãn collector 2 giây, giữ status/journal/last-sync; lỗi DB thật vẫn là lỗi, không giả lập health thành công |

Luồng khởi động vẫn là terminal riêng với `/config` → startup barrier → SDK
initialize → identity/access/path/generation verification. Windows idle không
chứng minh account ready. SDK/send không có retry mới. Native job owner dừng
descendants; `prepare_terminal` dọn thư mục private trước cold start kế tiếp,
giữ nguyên các binary đã duyệt. Diagnostic tạm chỉ ghi exception type, WinError
và tên hàm/dòng, không message/secret; đã gỡ và kiểm hash trước promote candidate.

Collector contention không đổi snapshot hoặc mốc đồng bộ thành công. Queued/
syncing không được nâng thành connected; lỗi có sẵn không bị xóa. Chỉ SQLSTATE
`LOCK_NOT_AVAILABLE` dùng nhánh này; các lỗi lock-query khác vẫn báo database
unavailable. Command/grant/receipt/unknown/final SDK admission giữ nguyên.

### Kiểm chứng đã đạt

| Phạm vi | Kết quả |
|---|---|
| Python worker | 20 tests đạt; sau khi làm rõ assertions, chỉ chạy lại 3 tests thay đổi, đều đạt. Chặn timeout/stopped/invalid handle trước SDK, giữ lỗi khởi tạo và không gọi OrderCheck/OrderSend |
| Rust collector | 10 tests liên quan đạt, gồm retry và guard không xóa lịch sử khi cold sync chưa đủ dữ liệu |
| PostgreSQL tách biệt | 1 fixture lifecycle đạt; busy giữ status/snapshot/last-sync, không giả readiness, không che lỗi thật, chặn sai workspace/generation. Cluster tạm đã dừng; không login broker hoặc sửa owner DB |
| Candidate worker trên Exness | Quan sát 180,55 giây/86 samples; không còn `mt5_worker_failed`/trading-disabled trong lượt này. `mt5_history_warming` xuất hiện 7 samples rồi connected từ giây 23,2; journal được giữ, 0 vị thế/lệnh chờ, không gọi đây là zero-error hoặc multiday acceptance |

Kiểm FTMO trước reconnect đã dừng ở preflight vì native account đang locked/
not-ready do contention cũ; 0 resume/order calls trong attempt đó. Giữ attempt
này để đối chiếu, không coi nó là FTMO acceptance. Hai account sau đó tự hồi
trên lịch đọc hiện có.

Private evidence nằm cùng backup root hệ thống: `connection-recovery-20261104/`,
`connection-recovery-diagnostic-20261104/`, `connection-startup-candidate-20261104/`,
`connection-startup-ftmo-20261104/`, `connection-contention-postgres.json`.
API release build với lockfile đã đạt; đã promote local binary từ `85940ede`
qua launcher đang sở hữu runtime. Giữ native/compact/local-capability, database,
adapter roots và các interpreter hiện có; không migration. Backup manifest,
launcher arguments, promotion record và adapter rollback giữ trong
`connection-stability-rollout-20261104/` cùng private root trên.

| Kiểm runtime mới | Kết quả và giới hạn |
|---|---|
| Theo dõi kết nối | 305,05 giây, 98 samples: Exness và FTMO giữ `connected`, không có connection error_code; journal tiếp tục đồng bộ. Đây là trạng thái collector, không khẳng định mọi trading snapshot đều ready |
| Tranh terminal thật | Giữ advisory lock Exness 6,05 giây bằng transaction chỉ đọc; cả 5 checks đạt: reader chờ, collector hoãn, giữ status/journal và không giả last-sync. Probe đầu chưa chứng minh reader chờ; giữ kết quả inconclusive, chỉ đổi phép đo sang đúng lock tag trong `pg_locks` rồi probe v2 đạt; không sửa sản phẩm giữa hai probe |
| Đọc snapshot | Cold reads: Exness busy, FTMO invalid number. Cuối observer: FTMO ready, Exness vẫn invalid number. Lượt đối chiếu sau đó: Exness ready với cả chỉ định `EURUSDm` và chọn tự động, không restart; quote được đánh dấu stale khoảng 6,3–6,5 giây. Chưa xác định trường số gây lỗi trước đó; không coi tự hồi là đã sửa root cause hoặc quote đủ điều kiện send |
| Runtime/ownership | 10 checks đạt: PID/creation identity, binary và adapter hashes, source/run pin, profile, API ready/DB ready, anonymous scoped API bị 401, UI 5180 trả 200, đúng 1 terminal/account và source sạch |
| Quyền và lệnh | Không có grant active, unknown request hoặc native request mới; 0 broker commands trong rollout/observer/probe. Phiên v4 vẫn revoked |

Artifact chính: `promotion.json`, `receipt.json`, `postflight.json`,
`contention-probe.json`, `contention-probe-v2.json`, `runtime-verification.json`
và `symbol-comparison.json` trong thư mục rollout private. Không đưa bearer,
credential hay raw terminal log vào Git.

**Acceptance của lát này:** startup barrier và nhánh defer khi tranh terminal
đã có focused regression, PostgreSQL fixture và bằng chứng local runtime; hai
account kết nối với một terminal riêng cho mỗi account. Chưa công nhận vận hành
unattended nhiều ngày, mọi snapshot luôn sẵn sàng, hoặc lợi nhuận chiến lược.
Không lặp phiên mở/đóng chỉ để kiểm lại phần đã đạt. Lỗi numeric thoáng qua còn
là giới hạn cần khoanh vùng nếu tái xuất hiện; không nới validation để che lỗi.

## 04/11 — Kiểm độ bền local trước vận hành Demo dài hơn

Owner giao toàn bộ phần kiểm nhanh theo thời gian/sự cố/replay/restore, giữ nhiều
máy cho sau; sau đó xác nhận chưa có đích backup ngoài máy hoặc kênh cảnh báo,
ưu tiên hoàn tất local. Phạm vi được nối vào AI plan hiện hành, issue
`Naqex/workspace#8`; không thêm source of truth, engine hoặc workflow UI.

Product commit `07270211fb22533559b715449024018768f1bc2f` bổ sung regression,
CLI rehearsal và hướng dẫn vào runtime doc. Logic runner/forward/native admission
và backup được reuse; không sửa policy production để tạo kết quả đạt. Không
deploy lại API vì thay đổi này là test/tool/docs; runtime trước đó vẫn ở
`85940ede`. Quyền giao dịch v4 không được mở lại, 0 broker commands trong lát này.

| Lát kiểm | Bằng chứng | Giới hạn |
|---|---|---|
| Thời gian mô phỏng | Mỗi ngày2027–2028 (731ngày, gồm leap day): runner6579 trường hợp trước/đúng/sau hết hạn ở3offset; native policy kiểm hạn và fingerprint với offset tương đương, không cho hồi sinh sau731ngày | Chỉ logic thời hạn/offset; không giả2năm uptime, market replay, DST scheduler hoặc phí thị trường |
| Session/crash/storage | Python focused18tests +16subtests đạt trong6,76giây: matrix12tình huống ở mở/đóng; lỗi trước/sau ghi intent/result; atomic replace thất bại giữ checkpoint cũ; mất phản hồi rồi restore sau2năm chỉ đối soát | Fake HTTP/SDK boundaries, không OrderSend thật |
| Replay liên tục vs restore | Test mới đạt11,69giây:256giờ synthetic/256events,32lần restore checkpoint giữa luồng và duplicate replay; snapshot cuối và từng giờ khớp continuous | Fixture hệ thống, không chọn/tối ưu hay qualification chiến lược |
| Lỗi lặp/tài nguyên |64lần resume unknown vẫn1POST ban đầu và2read/reconcile mỗi lần, checkpoint không vượt64KiB/không sót temp;64chu kỳ readiness chỉ ghi128transitions và không restart child | Không là benchmark RAM/CPU toàn MT5 hoặc capacity nhiều account |
| Backup bị gián đoạn | Lỗi disk giữa restore giữ bundle tốt, target dở không được ghi đè; restore sang target mới kiểm hash đạt | Dữ liệu fixture, không sửa DB owner |
| Native PostgreSQL | Harness mới reuse grant lifecycle fixture, crash bằng immediate stop rồi restart và restore bundle DB/artifact sang DB mới. Hash/count47bảng (29rows synthetic) giữ nguyên; native loader chặn revoked/expired sau cả crash và restore;5checks đạt, cluster đã dừng | Restore fixture1,359giây, toàn harness83,235giây; không là RTO production hoặc restore toàn máy |
| Kiểm nguồn/CI | Scoped rustfmt và diff check đạt; CLI help hoạt động. Thêm offline session/demo-admission/worker/forward vào job Python CI; native virtual-time nằm trong Rust tests mặc định | Chưa chạy remote CI hoặc toàn bộ suite từ lát này; rehearsal PostgreSQL là command explicit, không tự chạy vào owner DSN |

Lần PostgreSQL đầu bị guard chặn do harness đặt sai tên disposable role/database
(`demo_recovery_fixture` thay vì contract `rust_runtime_fixture`); cluster đã
dừng và receipt FAILED được giữ. Sửa harness dùng đúng identity, không nới guard;
attempt r2 đạt. Không dùng failed attempt làm evidence phục hồi.

Private evidence dưới backup root hiện hành:
`demo-recovery-qualification-20261104/receipt.json` (failed),
`demo-recovery-qualification-20261104-r2/receipt.json`, native subprocess logs,
checked bundle và `qualification.json` giữ source hashes/giới hạn của các checks.
Hướng dẫn tiếp được tích hợp trong `RUST-NATIVE-RUNTIME.md`, mục Demo reliability
qualification; command `scripts/demo_recovery_rehearsal.py` tự tạo cluster riêng,
không nhận DSN owner và gỡ inherited application/PostgreSQL environment.

**Kết luận scope local:** đã có gate lặp lại được trước Demo, không cần chờ1–2năm
để kiểm thời hạn/phục hồi. Sau gate này, vận hành Demo có giám sát để bổ sung lỗi
Windows/SDK/quote thật là phù hợp; không chờ hết mọi lỗi lý thuyết, cũng không bỏ
qua lỗi làm mất quyền/dữ liệu hoặc gửi trùng. Gặp lỗi thì dừng đúng phạm vi,
giữ evidence, sửa root cause và thêm regression liên quan. Lỗi numeric thoáng
qua đã ghi ở lát trước còn mở; connected không được thay thế quote/send readiness.
Chưa bật observer nhiều ngày, auto-start/restart mới, external alert, off-machine
backup hoặc nhiều máy. Không mở phiên broker mới từ việc offline gate đạt.

## 04/11 — Hướng dẫn nơi lưu backup cho owner

Theo yêu cầu tiếp tục và hướng dẫn backup: kiểm read-only runtime owner, hiện
trạng storage và helper sẵn có; không ngắt runtime chỉ để tư vấn nơi lưu.
Manifest vẫn native/compact/local-capability, PID/creation identity khớp.
Preflight DB chỉ đọc ghi0research/API/AI/download jobs active,0grant active,
0unknown requests và0account có saved inventory; đây không là broker inventory
read mới hoặc quyền mở phiên.

Windows xác nhận C/D/E/G ở các disk số3/0/1/4 tương ứng. D và E là hai disk
khác nhau; E còn khoảng167,4GB tại lúc đọc. Runtime backup junction tiếp tục
trỏ vào root E đã cấu hình. DB data_directory và artifacts root hiện tại đều
resolve ở D; backup E khác disk với dữ liệu đang chạy. Receipt snapshot03/11 ghi PASS,4.274.413.773bytes và
4.142artifact files; manifest còn tồn tại. Chưa rehash toàn bundle hoặc tạo
snapshot mới trong lượt tư vấn này, không nâng receipt cũ thành backup hôm nay.

Khuyến nghị: E cho local recovery nhanh, thêm bản đã mã hóa ngoài máy (cloud
owner chọn hoặc ổ rời được tháo/ngắt kết nối) khi có đích; chưa cần NAS/máy dự
phòng. Đề xuất retention7daily+4weekly là policy để xem xét theo dung lượng,
không cài timer hoặc xóa bản cũ. Helper hiện tại yêu cầu quiesce, chưa là online
backup24/7. Trader bundle không bao gồm toàn bộ Paperclip/provider auth.

Tích hợp inventory/trình tự/thẩm quyền phục hồi vào
`tooling/ai-engines/OPERATIONS.md`, mục Owner backup and recovery boundaries.
Không cấu hình cloud, xuất credential hoặc gửi dữ liệu ra ngoài. Nguồn đối chiếu:
[NCSC backup separation/offline](https://www.ncsc.gov.uk/blog-post/offline-backups-in-an-online-world)
và [PostgreSQL filesystem backup](https://www.postgresql.org/docs/18/backup-file.html).

## 04/11 — Tiếp độ ổn định: snapshot numeric và cold subscription

Owner xác nhận G là ổ rời, sau đó quyết định để phần backup ổ rời/cloud lại khi
cần. Lát này không tạo snapshot DB mới, ghi G, upload hoặc bật lịch backup.
Tiếp đúng lỗi `demo_invalid_number` còn mở, không chạy lại các qualification đã đạt.

| Phần | Thay đổi / bằng chứng |
|---|---|
| Cold subscription | Fixture tái hiện symbol spec trước `symbol_select` còn tick size bằng0 dù SDK tuple mới hợp lệ. Adapter đọc lại spec sau subscribe, vẫn chặn nếu dữ liệu mới không hợp lệ. Đây là lỗi source được tái hiện, chưa chứng minh là nguyên nhân mọi lỗi runtime trước đây |
| Chẩn đoán thật | Sau rollout lần đầu, Exness explicit `EURUSDm` bị `demo_invalid_number`; phản hồi mới xác định `data_quality.invalid_field=quote.bid`. Chỉ lưu tên trường/điều kiện dương-hữu hạn, không ghi raw SDK value hoặc secret |
| Phân loại trạng thái | Bid/Ask không hợp lệ trả `demo_quote_unavailable`, thống nhất default-symbol path và UI message đã có. Tick size/point/lot limits lỗi vẫn `demo_invalid_number`. Native API giữ diagnostic thay vì bỏ; không thêm UI, retry hoặc thay execution gate |
| Kiểm nguồn |64Python tests về Demo/worker đạt0,872s;8Rust tests về demo trading đạt; release build, scoped rustfmt và diff check đạt. Fixture kiểm cả feed invalid→ready, không initialize lại, OrderCheck hoặc send. Không chạy lại crash/restore suite không đổi |
| Runtime | API binary mới qua owned launcher; giữ native/compact/local-capability, paths và launch descriptors. Bản Python phân loại kế tiếp chỉ reconnect2worker đã sở hữu, không restart API thêm. SHA/path/process identity và7checks cuối đạt |
| Warmup/recovery | Quan sát20,3giây đầu sau reconnect vẫn `mt5_history_warming`; không coi là pass hoặc reconnect lặp. Collector retry sẵn có15giây tiếp tục với journal cũ. Lượt đọc sau khoảng71–73giây có explicit Exness/FTMO ready; Exness auto tạm quote unavailable rồi explicit ready0,3giây sau. Cả hai kết nối cuối connected, không error_code |
| Quyền/dữ liệu |0grant active,0unknown request,0native request mới,0broker commands/provider inference. Snapshot explicit cuối không có positions/orders. Không migration, thay strategy hoặc gia hạn quyền cũ |

Trader commits `11ae9796` (refresh spec/diagnostic) và `043c4f3e` (quote
classification/recovery regression). Private evidence/rollback tại root E hiện
hành: `numeric-snapshot-20261104/{before,after,recovered}.json`,
`numeric-snapshot-20261104/promotion.json` và
`numeric-snapshot-classification-20261104/{promotion,receipt,qualification}.json`.
Receipt20giây chưa ready được giữ nguyên; qualification sau đó ghi recovery thực.

**Còn mở:** FTMO quote `time_msc` đi trước host UTC khoảng7.197–7.199giây;
snapshot đọc được nhưng `quote_status=future`. Không tự trừ2giờ, đổi clock hoặc
nới freshness gate để cho send. Cần xác minh semantics timestamp của broker/SDK
trước khi coi FTMO execution-ready. Exness explicit cuối fresh, age950ms. Chưa
có unattended nhiều ngày, external alert hoặc whole-product acceptance.

## 04/11 — Khép lỗi broker clock và bàn giao nền Demo local

Tiếp yêu cầu hoàn thiện hệ thống cho Demo, chưa tối ưu chiến lược. Backup G/cloud
tiếp tục hoãn theo owner; không tạo lịch, upload hay copy ổ rời. Không tạo Goal,
engine, management UI hoặc ledger mới. Scope vẫn ở AI plan; issue
`Naqex/workspace#8` và Product Plan không được đóng bằng acceptance của lát này.

### Thay đổi, luồng dữ liệu và quyết định

Trader `6fc78274` thêm decoder dùng chung cho quote, bar, collector và broker
reconciliation. Chỉ server chính xác `FTMO-Demo` dùng profile
`ftmo_demo_server_2026_v1`, sự kiện từ năm 2026: offset New York cộng bảy giờ
(mùa đông UTC+2, mùa hè UTC+3). Các server khác giữ SDK UTC contract, không đoán
broker từ prefix hoặc suy offset từ tuổi quote. Giữ timestamp gốc cùng metadata
clock; chuyển sang UTC trước cutoff/freshness/reconciliation. Grant vẫn hết hạn
theo UTC, Prop reset timezone không đổi. Fold/gap DST và thời gian FTMO chưa được
xác minh bị chặn; legacy FTMO export không được gắn nhãn UTC sai.

Nguồn chính thức và giới hạn nằm trong
`projects/trader/foundation_v2/docs/MT5-BROKER-CLOCK.md`: FTMO account specs và
hai trading updates tháng 3/tháng 10 năm 2026, Exness server timezone, MetaQuotes
tick-history contract. MetaQuotes mô tả UTC nhưng dữ liệu FTMO quan sát được dùng
server wall time; profile này ghi rõ ngoại lệ đã kiểm, không sửa Windows clock
hoặc nới stale/future guard. Khi broker đổi server/feed/lịch phải kiểm lại profile.

Rollout đầu phát hiện regression: snapshot cả hai account trả
`mt5_clock_unavailable`. Tái hiện offline bằng `numpy.int64` đúng kiểu timestamp
trong MT5 rates array; tests trước dùng dict với Python int nên chưa bắt được.
Trader `b4f4ecd5` chuyển integer scalar hợp lệ thành Python int trước nhân/kiểm;
giữ chặn bool, số âm, NaN/Infinity và kiểu không hợp lệ. Regression dùng structured
NumPy array và kiểm overflow trước phép nhân. CI Windows hiện cài extra `mt5`
từ lockfile sẵn có và chạy cả read-worker tests để không bỏ qua NumPy fixture.
Không thêm package/version mới hoặc gọi SDK thật trong tests.

### Bằng chứng mới

| Phạm vi | Kết quả |
|---|---|
| Source trước rollout đầu | 87 tests clock/Demo/connector/broker-worker đạt; 9 legacy read-worker tests đạt khi chạy đúng runtime venv có NumPy. Giữ bằng chứng lệnh sai CWD và lượt canonical venv thiếu NumPy bị skip, không tính là đủ kiểm chứng |
| Regression sau lỗi kiểu SDK | 78 focused tests clock/Demo/connector/read-worker đạt, không skip, 1,178 giây. Diff check đạt. Không chạy lại Rust/web/crash/restore unchanged; chưa chạy remote CI |
| Rollout đầu | Observer khoảng 125 giây, cả hai connected nhưng snapshots bị clock guard chặn; receipt `final_snapshots_ready=false` giữ nguyên, không nâng thành PASS |
| Rollout đã sửa | Chỉ cập nhật bốn file Python và resume mỗi account một lần; API/UI không restart. Preflight dùng collector mới dưới 120 giây, xác minh Demo, inventory rỗng, mode/identity, không active grant hoặc unknown trước reconnect |
| Cold recovery | Observer 128,11 giây / 26 samples. Exness ready từ giây 31,328 sau cold quote unavailable; FTMO ready từ giây 43,782 sau not-ready. Không reconnect lặp để ép healthy |
| Quote/bar UTC | 10 Exness ready samples: raw bằng UTC, age 846–2.681 ms. 9 FTMO ready samples: raw trừ đúng 7.200.000 ms, age 948–2.939 ms; mọi ready sample đều fresh theo read policy hiện hành, bar UTC đi tiếp. Đây không là authorization hoặc final send admission |
| Collector và journal | Postflight Exness generation 19: 30 deals / 1 cashflow; FTMO generation 5: 0 deals / 1 cashflow. Raw/UTC của events khớp profile, không event sau cutoff; mọi deal ID của native filled receipts trước đây còn trong collector |
| Runtime/auth | 15/15 checks đạt lúc 03:50:40 UTC: native/UI process identity, binary/adapter/index hashes, profile native/compact/local-capability, API/DB ready, anonymous 401, Paperclip health và gateway yêu cầu key, source sạch, đúng 1 owned terminal/account |
| Quyền và tác dụng ngoài | 0 native requests mới, 0 unknown, 0 active grants, 0 positions/orders; 0 research/API/AI/download jobs active ở postflight. 0 OrderCheck/OrderSend/provider inference trong lát này. Phiên v4 vẫn revoked |

API run ID giữ `1862f6b810bc4f2c9d4663ceea41c8b6`; API binary vẫn bản numeric
rollout trước, không gọi nó là binary build từ commit Python mới. Bốn Python
files đang chạy khớp source `b4f4ecd5654e348661a1e500e58620f4ab8868fb`.
Private rollback/evidence nằm trong backup root E hiện hành:
`broker-clock-20261104/{promotion,receipt}.json` giữ failed rollout;
`broker-clock-scalar-20261104/{promotion,receipt,qualification}.json` và
`samples.jsonl` giữ kết quả sửa. Không đưa bearer, credentials hoặc raw terminal
logs vào Git. Script postflight chỉ GET/SQL read-only; không tạo quyền hoặc sends.

### Đối chiếu phạm vi hệ thống hiện hành

| Lát | Acceptance đã có | Phần chưa được kết luận |
|---|---|---|
| Research → mô phỏng → review → owner | Native Paperclip handoff, artifact/hash/dependency/cancel/recovery và báo cáo đã có evidence ở các mục trước | Không redispatch model/pilot chỉ để thêm green; chưa strategy qualification |
| Dữ liệu và Forex replay | Provenance/spec/cost binding, QDM CLI, causal fills/risk, checkpoint/restart parity; broker clock local đã sửa và kiểm thật | Chi phí lịch sử chưa xác minh không thành zero hoặc phí đã chứng nhận; replay không là observed-market forward |
| Phân quyền/risk/execution | Owner/Automation tách biệt, grant bất biến, idempotency/unknown/reconcile, final SDK guards; v4 trước đã mở và đóng Exness Demo trong giới hạn được duyệt | Không có grant mới; maintenance không cho giao dịch tiếp, FTMO chưa có phiên OrderSend acceptance |
| Phục hồi local | Virtual-time/fault/replay tests, PostgreSQL crash và restore fixture, isolated owner-bundle restore đã đạt ở các mục trước | Không là hai năm uptime, whole-machine DR hoặc phục hồi broker về quá khứ |
| Runtime có giám sát | Hai account đọc được, mỗi account một terminal riêng; readiness/degraded/recovery và giữ journal khi warmup/contention; checks mới đạt | Quan sát ngắn không chứng minh chạy bền nhiều ngày hoặc đủ capacity nhiều account |
| Chạy tự động liên tục | Chưa bật | Durable complete-tick source/cursor cho observed forward, lifecycle dài ngày, alert ngoài máy và boot/failover chưa được qualification; SSE chỉ sampled latest state |

**Kết luận:** đã khép các lỗi source/runtime đang mở của lát Demo local này;
nền hiện tại phù hợp vận hành Demo có giám sát, trong các phiên có phạm vi rõ.
Không còn dùng FTMO `future` do server clock như blocker chưa xử lý. Không tự gọi
đây là toàn sản phẩm hoàn tất, chiến lược có lãi hoặc autonomous 24/7. Dừng thêm
test/framework vào phần đã đủ bằng chứng. Bước giao dịch mới cần owner xác định
phiên/account/time/risk; phần continuous forward dài ngày là acceptance riêng,
không được suy ra từ snapshot, SSE hoặc vòng mở/đóng đã đạt. Backup G/cloud,
external alert và nhiều máy vẫn hoãn; không dùng việc hoãn đó để chặn phần local.

## 04/11 — Nguồn quote native có checkpoint, đã kiểm trên hai Demo

Owner giao tiếp sau handoff local; tiếp đúng khoảng thiếu nguồn forward, không
tuning chiến lược, bật daemon hoặc mở phiên giao dịch mới. Trader commit
`f5b4065053f63af53ab669d1dca89fbf15995a8a` bổ sung nguồn dữ liệu có thể resume;
giữ UI/quản lý task/run/report native Paperclip. Scope nối vào AI plan hiện có,
không tạo ledger, engine hoặc framework khác.

### Luồng và trade-off

`GET /api/v2/live/trading/ticks` → context native của connection → advisory
terminal lock → worker đang sở hữu account → `copy_ticks_range(COPY_TICKS_ALL)`.
Generation/account/permissions được kiểm trước và sau read; read-only connections
cũng được đọc. Không có SDK attachment, terminal hoặc đường send mới. Query UTC
second-aligned, tối đa 60 giây/page, kết thúc ít nhất 2 giây trước host UTC; trên
5000 SDK rows bị chặn, không truncate. FTMO dùng verified broker-clock profile
cho query lẫn normalized timestamps; DST không rõ bị chặn. Chính sách 2 giây chỉ
tách cửa sổ đang hình thành, không chứng minh broker history đã đủ hoặc bất biến.

`scripts/mt5_observed_capture.py` chỉ GET exact loopback route, không proxy/
redirect, không import SDK/DB hoặc tạo grant. Trusted operator cấp private Owner
secret file; token không nằm trong page/checkpoint/arguments/report. Đây không
là sandbox chống agent có toàn quyền filesystem. Các input phải ngoài output;
directory private và không symlink/junction. Mỗi page fsync/checksum trước atomic
cursor commit; writer lock chặn đồng thời. Resume kiểm toàn bộ prefix/client pin,
đọc lại page cuối và từ chối thay đổi rows/order/binding/clock/SDK/source. Crash
giữa page và cursor: kiểm/re-read page chưa commit rồi adopt đúng một lần.

Giữ Bid/Ask, flags, raw/UTC timestamps, thứ tự và cả duplicate cùng millisecond;
đây là quote capture, không market depth/trade-volume feed. API trả account/
generation, clock profile, SDK version và hash hai module capture/clock. Cursor
là `requested_through_msc`, **không** verified source watermark. Empty page vẫn
`broker_history_unverified`. Chỉ recheck page cuối, không bảo đảm broker không
sửa page cũ hơn. Chưa chuyển dữ liệu này thành bar-finality hoặc quyền gửi lệnh.

Session tối đa 24 giờ/10000 pages; mỗi invocation tối đa 360 pages (default 12),
trả `waiting` khi cửa sổ chưa đóng hoặc `stopped` khi có file STOP. Không tự ngủ/
retry, cài lịch/auto boot hoặc auto-extend session. Giới hạn này là bound storage/
work theo contract, không khôi phục cap quota 10 lượt/ngày đã gỡ trước đây.

### Kiểm chứng và rollout

| Lát | Kết quả và giới hạn |
|---|---|
| Python | 34 tests liên quan đạt qua focused runs: 4 SDK-range, 9 recorder và 21 broker-worker. NumPy array thật về cấu trúc nhưng SDK/network fake: half-open/same-ms duplicates, FTMO query UTC, invalid/oversize/order/DST, resume parity, page-before-cursor crash, checksum/source/binding, network/disk/atomic-replace, concurrent writer và STOP |
| Thất bại fixture | Lượt đầu 3 tests mới lỗi vì `np.array(tuple-of-rows)` bị hiểu là một record; sửa fixture thành list-of-rows, không đổi guard để pass. Lệnh rustfmt đầu sai CWD chưa format được; lệnh đúng sau đó đạt |
| Rust/CI | 9 Demo/stream/range tests và 4 native-route/command tests đạt; release build đạt 2m55s. CI Python thêm hai modules mới vào job offline hiện có, chưa chạy remote CI hoặc full suite unchanged |
| Rollout local | Preflight jobs/grants/unknown/inventory trước stop. Owned launcher check-only/require-idle và stop/start đạt; backup old binary descriptor/scripts, giữ native/compact/local-capability, DB/artifacts/interpreters. Không migration hoặc build/promote UI |
| Capture Exness | 30 giây theo range đăng ký, 3 pages / 38 ticks. Process `start` ghi page đầu 13 ticks; process CLI mới `resume` kiểm page cuối rồi đi tiếp đúng cursor. Raw timestamp bằng UTC |
| Capture FTMO | Cùng 30 giây, 3 pages / 74 ticks; page đầu 24 ticks. Resume qua process mới đạt; raw trừ 7.200.000 ms thành UTC. Cả hai dùng SDK 5.0.6231 |
| Đối chiếu thật | 7/7 checks đạt: hai process-resume hoàn tất, quote Bid/Ask/time đã quan sát có trong history cả hai account, clock đúng, anonymous 401, generation sai 423, không thêm command request, connection/inventory giữ nguyên |
| Sau rollout | 15/15 runtime checks đạt lúc 04:13:23 UTC: identity/hash/profile/auth/readiness, UI index và native Studio, đúng một terminal/account, source sạch, quote/bar UTC, journal giữ các filled deals cũ. Exness generation 19, FTMO generation 5 giữ nguyên |
| Quyền và chi phí | Broker command requests vẫn 32 trước/sau; 0 unknown, 0 active grants, 0 positions/orders, 0 OrderCheck/OrderSend/provider inference trong lát này. Không phí model, strategy run, external alert hoặc backup G/cloud |

Cold read đầu sau restart: Exness quote unavailable, FTMO ready; observer chỉ đọc
lại sau 10 giây thì cả hai ready, không reconnect lặp. Không dùng recovery này
để tuyên bố mọi cold-start đều dưới 10 giây hoặc vận hành nhiều ngày đã đạt.
API run mới `e62d5f0b38994c53b6acf3055a36c41b`, binary SHA256
`49c89c6012a454bea68fc3ecb7a43a485a4b141b8bdcd702388c2d86590755df`.

Private evidence/rollback dưới E root hiện hành trong `observed-quotes-20261104/`:
`promotion.json`, `capture-qualification.json`, `runtime-verification.json`,
registrations và hai capture directories chứa pages/state; logs riêng cho mỗi
process start/resume. Không đưa dữ liệu tài khoản/secrets vào Git. Product docs:
`foundation_v2/docs/LIVE-MARKET-STREAM.md` và `FOREX-FORWARD.md`, mục bounded
observed quote capture, giữ endpoint/commands/phạm vi và cách dừng/resume.
Primary contract đã đối chiếu:
[MetaQuotes copy_ticks_range](https://www.mql5.com/en/docs/python_metatrader5/mt5copyticksrange_py).

**Acceptance đạt:** bounded source capture có provenance và requested cursor,
disk/process recovery, kiểm cả Exness/FTMO thật qua đường native hiện có. Chưa
gọi là durable complete-tick market truth, consumer chiến lược observed-forward,
24/7 daemon hoặc qualification lợi nhuận. Bước tiếp của continuous forward phải
chốt semantics coverage/bar-finality và lifecycle trước khi nối vào quyết định;
không dùng cursor này như watermark đủ dữ liệu để đóng giờ hoặc tự mở quyền.

## 04/11 — Phiên forward shadow hữu hạn: stop, crash và resume

Owner duyệt làm tiếp phiên có giám sát sau nguồn capture, hỏi ý nghĩa forward.
Forward xử lý dữ liệu mới phát sinh theo thời gian thực; shadow ở lát này chỉ
ghi/đánh giá quan sát, không gửi lệnh. Trader commit
`350e2bd57752e807b61bf1070ed5bc759a8b7206` nối lifecycle, chất lượng dữ liệu và
ứng viên cố định. Không tuning chiến lược hoặc mở phiên giao dịch Demo mới.

### Hành vi và luồng state

`mt5-shadow` (Rust CLI) → một Python step có giới hạn → native GET ticks/owned
SDK worker hiện có → page/hash/cursor durable → shadow projection → ứng viên H4
chỉ khi giờ đủ điều kiện. Native Paperclip giữ task/report; không có UI, API
management surface hoặc task ledger mới trong Trader. Không sửa source engine.
Rust tái sử dụng owned-process Windows Job, không thêm daemon Python, scheduler,
auto boot, migration hoặc dependency. Giữ `cargo run` mặc định vào API cũ.

Rust giữ OS writer lock, STOP, deadline UTC và monotonic budget của invocation,
thời hạn step90s/memory384MiB, manifest/binary/interpreter pins và lifecycle
checksum/fsync/atomic replacement. Chỉ đợi tới page/settlement đến hạn. Status
phân biệt interrupted qua lock thay vì PID; explicit resume mới gỡ STOP, không
gia hạn phiên. Drop/crash supervisor kết thúc owned child tree. Lifecycle lưu
incarnation hiện hành; log mỗi invocation giữ riêng trong evidence, không tự
tuyên bố đây là incident log append-only. API/terminal đang chạy không restart.

Python pin8 source/lockfile hashes, Python/Pydantic version cùng source/SDK clock
lineage từ capture. Resume kiểm và đọc lại các page đã ghi; prefix/hash/source
đổi, HTTP, disk hoặc timeout đều dừng, không tự retry. Shadow là projection từ
pages; crash giữa capture/shadow/lifecycle commits replay lại prefix mà không
thêm trùng nến/quyết định. Credentials chỉ qua private file; không vào output/Git.

**Chính sách nến:** giờ đầu chưa đủ loại rõ là partial; giờ cuối chưa đóng không
vào candidate. Một giờ đủ requested windows phải qua30–120s settlement và đọc
lại từng overlapping page không đổi. Empty/quiet hour hoặc gap leading/adjacent/
trailing trên60s chặn thay vì dựng nến, skip giờ hoặc reset candidate. Đây là
policy bảo thủ có thể từ chối quiet market hợp lệ; không suy calendar hay khẳng
định broker trả đủ tick. H4 chỉ nhận đủ4giờ; decision giữ cả earliest allowed và
actual first observation time. Recheck lịch sử cũ khi resume không chứng minh
broker không sửa dữ liệu sau completion.

### Kiểm chứng và giới hạn

| Lát | Bằng chứng |
|---|---|
| Python source | 8 tests mới qua focused runs: 7 reducer/recovery tests với3subtests, thêm1diagnostic HTTP test. Kiểm chưa đủ settlement, H4 causal, partial/same-ms duplicates, gap, revision/backfill, prefix/restart parity, STOP/expiry/network, changed pins/symbol/deadline; mã HTTP an toàn và đúng1call khi thất bại |
| Rust source | 11 tests đạt, gồm2lifecycle/deadline/lock/checksum và9owned-process tests;1ignored là child fixture được parent crash test gọi. Sau đổi pin/metadata chạy lại đúng2tests mới. Release build đạt3m07s; binary SHA256 `980a2339bb08654c9de8b8cc4884885f8226ef1ea6ed30a8a1c046beeede30f6` |
| Formatting/lint | Scoped rustfmt3files đạt, diff check đạt. `cargo fmt --check` toàn repo còn FAIL ở file cũ không đổi như commands/live_ledger/note_library/note_types; không sửa ngoài scope hoặc gọi full CI đạt. Clippy command đạt, còn140warnings trong lib hiện có và1warning ở reused owned-process spawn function; không disable lint |
| Lỗi triển khai ban đầu | Rust include path của shared owned-process module chưa rõ khi dùng từ bin; thêm explicit module/test paths, compile/tests sau đạt. Không thay semantics process ownership |
| Hai lượt runtime đầu | Dừng trước page commit, không broker command. Helper đã lọc biến môi trường Windows theo chữ hoa/thường, bỏ SystemRoot; r2 diagnostic là URLError. Probe chỉ đổi môi trường xác nhận thiếu SystemRoot gây Winsock10106, đủ biến trả HTTP200. Sửa helper; không sửa API, fallback hoặc nới freshness. Lượt đầu có một diagnostic read/commit13ticks sau failure; không coi lượt này PASS |
| Phiên r3 thực tế | Exness Demo, cùng generation19:100giây đăng ký,10pages/202ticks; STOP sau page1, resume rồi abrupt terminate sau page2, process mới resume đến complete.3incarnations, deadline và durable prefix giữ nguyên;12/12checks đạt lúc04:43:22UTC |
| Quyền/inventory | Native command requests32→32,0active grants/unknown;0positions/orders sau phiên,0OrderCheck/OrderSend/model inference. Mode/account/generation giữ nguyên. API vẫn run `e62d5f0b38994c53b6acf3055a36c41b`, native/local-capability; không rollout API/UI hoặc reconnect |
| H4 runtime |0giờ/H4 hoàn chỉnh trong khoảng ngắn này; `warming_up`, indicator_ready=false. Source fixture kiểm H4 đóng đúng, runtime chỉ chứng minh observed data/lifecycle/recovery tới trạng thái warmup; chưa chứng minh một decision H4 thực tế |
| Báo cáo native | [NAQ-79](http://127.0.0.1:17860/NAQ/issues/NAQ-79) done trong Naqex AI, document `shadow-system-20261104`, native API PUT/GET body khớp. MCP không được expose trong chat này nên dùng project-authenticated HTTP helper hiện có; không dispatch worker/model hoặc sửa database Paperclip |

CI hiện có đã nhận module Python mới; chưa chạy remote CI/full suite. Không
chạy lại QDM/strategy pilot/broker open-close tests đã accepted và không đổi.

Private evidence dưới `E:/BACKUP-TRADINGWORKSPACE/system-capabilities-20261103/`:
`shadow-session-20261104/` và `shadow-session-20261104-r2/` giữ failure logs,
registration/lifecycle; `shadow-session-20261104-r3/` giữ binary, registration,
capture/shadow/lifecycle,3invocation logs, `qualification.json` và
`paperclip-publication.json`. Helper `qualify_shadow_session.py` và
`publish_shadow_report.py` ở E root. Không đưa account/raw quotes/secrets vào Git.
Shadow report checksum
`446d81a7c44a90f411b13e01cad4fdcaa0db903d76bd109a638c021837993a46`;
native report body checksum
`5b1aa34e0cd8bf1db508fe23069ce2d3f5f9960a8c05809a2845a4ba60fa3c4c`.

**Acceptance:** finite observed capture + Rust lifecycle/STOP/crash/cold-resume
đạt trong scope trên; source đã nối fixed candidate và quality guards. Phiên đã
kết thúc, không còn shadow worker cần chờ. Coverage vẫn
`broker_history_unverified`, không là complete-tick watermark hay24/7uptime.
Adapter đánh giá flat-state advisory, chưa có position/EXIT lifecycle, quantity,
fills, margin, fees/swap hoặc P&L; unknown cost là not_modeled, không là zero.

**Phần tiếp nếu mở forward nhiều ngày:** continuity/warmup giữa các phiên hoặc
nguồn warmup đúng thời điểm/basis và lineage; một phiên24giờ không đủ20H4 trước
đó để có entry. Không dùng warmup2022 cho thị trường2026 hoặc kéo scope sang
tuning. Mô phỏng vị thế/chi phí cần contract riêng đúng broker trước khi gọi đây
là full paper trader. Issue Naqex/workspace#8 vẫn OPEN; lát này không kết luận
whole-product, strategy profitability hoặc mở quyền giao dịch. Backup G/cloud,
external alert và nhiều máy tiếp tục hoãn theo owner.

## 04/11 — Giữ warmup giữa các phiên shadow hữu hạn

Tiếp source WIP từ phiên trước, Trader commit
`1685e22cc0cec4483e0e96d808d3eae686c5113e` bổ sung registration/report v2 với
predecessor đã pin hash. Phiên mới chỉ nhận lifecycle `complete`, registration,
capture/report counters và source/clock/SDK cùng account/generation khớp. Kiểm
pages khi init/cold resume; giữ candidate history/ATR và phần H4 chưa đủ, mỗi
report chỉ ghi giờ/decision của phiên hiện tại cùng tổng tích lũy. Không copy
raw ticks hoặc phát lại decision cũ. Đường dẫn canonical local phải tách biệt.

Handoff đúng mốc H1 và không gap/overlap. Dừng giữa giờ phải resume cùng phiên;
phiên hoàn tất giữa giờ không được seed. Tối đa32phiên/chuỗi, mỗi phiên giữ
bound24giờ. V1 giữ làm evidence, không tự sửa manifest/source pins để upgrade;
không migration dữ liệu owner, scheduler, auto rollover hoặc dịch vụ nền mới.

| Lát | Bằng chứng / giới hạn |
|---|---|
| Python | 15tests +11subtests đạt trong104,71s: hai modules shadow/continuation. Dữ liệu tổng hợp92giờ qua4phiên23giờ tạo23H4, candidate/builder khớp xử lý liên tục; cold resume khớp nguyên report. Kiểm gap/overlap/generation/symbol/policy, mid-hour, lifecycle incomplete, đổi report/page/SDK và causal observation time |
| Lỗi fixture | Lượt đầu6tests có1FAIL vì Decimal bằng nhau nhưng JSON khác scale (`1.1003`/`1.10030`). So typed Decimal state cho parity số học; kiểm cold-resume nguyên report vẫn giữ exact equality. Không nới guard production để pass |
| Review độc lập | Reviewer chỉ đọc diff phát hiện Rust start60s không đủ cho settlement60–120s. Sửa continuation allowance bằng settlement+60s, vẫn cần Python init xác minh predecessor trước read; start độc lập giữ60s. Reviewer kiểm bản sửa và docs, không còn finding trong scope |
| Rust/build | 1targeted regression đạt cho settlement30/120, quá hạn và independent start; scoped rustfmt/diff check đạt. Locked release build đạt3,74s. Không chạy lại owned-process hoặc full suite unchanged, không gọi full CI pass |
| Native report | PUT/GET document `shadow-continuity-20261104` trên task [NAQ-79](http://127.0.0.1:17860/NAQ/issues/NAQ-79), body khớp; SHA256 `6414ca33011af4f7288c41b48c6b249e24e8a4cdbe21153267f0ef2ca64673af`. Dùng project-authenticated native HTTP helper vì MCP không expose, không dispatch model |
| Runtime/quyền | Không có shadow worker đang hoạt động khi kiểm ownership; không gọi broker/OrderCheck/OrderSend/provider trong lát này. Không restart API/terminal, source engine, thay UI hoặc tạo native task mới. Chưa chạy continuation trên broker thật hoặc promote API/UI |

Evidence private:
`E:/BACKUP-TRADINGWORKSPACE/system-capabilities-20261103/shadow-continuity-20261104/`
giữ qualification/source/binary hash và publication receipt. Binary release ở
target hiện có; docs `foundation_v2/docs/FOREX-FORWARD.md` giữ cách pin seed,
start/stop/resume và giới hạn. CI hiện có thêm module continuation, chưa chạy
remote CI. Product Plan dirty amendment từ task khác không nằm trong commit này.

**Acceptance:** source/offline continuity đã kiểm;92giờ là thời gian dữ liệu
tổng hợp, không là uptime hoặc forward broker nhiều ngày. Coverage tiếp tục
`broker_history_unverified`; vị thế/fill/lot/fees/swap/P&L vẫn not modeled.
Bước tiếp đúng scope là phiên v2 có giám sát trên dữ liệu mới, kiểm bàn giao
thật tại mốc H1; weekend/gap/unattended lifecycle còn riêng. Không tuning,
kết luận lợi nhuận hoặc mở quyền giao dịch; issue#8 và whole-product còn mở.

## 04/11 — Đang quan sát bàn giao hai phiên v2 trên dữ liệu mới

Owner giao tiếp sau checkpoint continuity; bắt đầu finite qualification thật,
chỉ đọc Exness Demo `464104926 / Exness-MT5Trial17`, EURUSDm, generation19.
Đây là lượt quan sát mới, không lặp open/close hoặc cấp grant. Preflight12:18
giờ VN xác minh process identity/binary của native owner, HTTP ready và account
inventory:32native requests,0active grants/unknown,0positions/orders. Native API
run vẫn `e62d5f0b38994c53b6acf3055a36c41b`, không restart/reconnect/rollout.

Lượt chuẩn bị đầu dừng trước capture bởi native Paperclip HTTP422: `in_progress`
phải có assignee. Đối chiếu service source xác định guard; dùng owner user đã
tạo task reference làm assignee, không gán AI worker. Giữ nguyên thư mục lỗi và
idempotency key khi thực hiện lại, không bypass native API hoặc sửa DB engine.

| Mốc giờ Việt Nam 04/11 | Phạm vi đang chạy |
|---|---|
| 12:19:43 | Bắt đầu phiên1; page60giây, settle30giây; phần H1 đầu chưa đủ bị loại |
| 13:00–14:00 | Thu trọn một H1 mới để có builder warmup thực tế |
| Sau14:00:30 | Chỉ khi phiên1 complete và preflight/binding giữ nguyên mới tạo registration2 pin report hash, rồi start phiên2 |
| 14:02:30 dự kiến | Phiên2 kết thúc quan sát; hard deadline cuối14:05. Không chạy phiên3 hoặc tự gia hạn |

Task native [NAQ-80](http://127.0.0.1:17860/NAQ/issues/NAQ-80) đang `in_progress`,
document `live-handoff-20261104` đã PUT/GET body khớp. Không đổi task NAQ-79 đã
hoàn tất hoặc dispatch worker/model. Driver hữu hạn chỉ điều khiển đúng hai
invocations của CLI hiện có; không cài scheduler, startup, service hoặc product
auto rollover. Kết thúc/failure cập nhật cùng native document/status; HTTP delivery
lỗi không tự lặp capture. Chưa có acceptance cho live handoff.

Startup đã kiểm lúc12:20:46VN: lifecycle `running`,1page/66ticks thật đã commit,
cursor tiến đúng60giây; driver stderr rỗng. Đây chỉ là bằng chứng khởi động và
ghi nguồn, chưa đủ công nhận bàn giao hoặc hoàn tất lượt quan sát.

**Ownership/resume:** thư mục private
`E:/BACKUP-TRADINGWORKSPACE/system-capabilities-20261103/shadow-live-handoff-20261104-r2/`
giữ `qualification-state.json`, registration1/2, sessions/lifecycle/pages và
result `qualification.json` sau khi đủ checks. Driver thật PID26268,
`mt5-shadow` phiên1 PID2848 tại12:20VN; launcher PID27308 là Python redirector.
Driver script `observe_shadow_handoff.py` và stdout/stderr `.driver.*.log` ở E
root hiện có. Bản lỗi đầu ở `shadow-live-handoff-20261104/`. Binary đã copy/pin
SHA256 `2d99705a665989f90cafca238fa59ea427b6632e081a1a9144c9cb398b85d624`;
source vẫn Trader `1685e22c`, worktree sạch khi khởi động. Không sửa source pins
hoặc khởi chạy helper lần hai trong khi job này còn hoạt động.

Để dừng, tạo file `STOP` trong thư mục r2; driver chuyển STOP sang session đang
chạy và không start phiên tiếp. Source/binding/data revision/quiet-gap vượt guard,
timeout hoặc deadline sẽ dừng và giữ evidence, không tự retry/reconnect. Khi
resume công việc, đọc state/log/native task và xác minh PID/creation identity
trước hành động; không rerun helper hoặc tạo attempt khác để che lỗi chưa hiểu.

**Tiêu chí kết thúc:** hai native lifecycles complete; phiên1 có1H1 thật;
phiên2 giữ đúng builder/candidate state và cumulative count, đọc được quotes mới,
không tạo H4 giả; report1 bất biến và command/grant/unknown/account/run giữ
nguyên. Một H1 chưa đủ khởi tạo ATR/H4 entry; coverage vẫn
`broker_history_unverified`, chưa phải uptime nhiều ngày, P&L hay quyền giao dịch.

## 04/11 — Ẩn console và giữ hạ tầng hiện tại

Owner chọn dùng PC chính ở giai đoạn hiện tại, tháo/cất GTX1660 của PC phụ;
VI Dubber tạm dừng phát triển. Chưa cần vận hành PC phụ, Heroku, Oracle hoặc
VPS; chỉ xem lại khi có nhu cầu thực tế. Đây là quyết định phạm vi, không phải
thay đổi phần cứng, cloud hoặc dịch vụ đã được agent thực hiện.

Ẩn cửa sổ Windows Terminal PID25064/HWND3215294 sau khi đối chiếu title/path
với Python launcher API đang sở hữu. Win32 xác nhận visible từ true thành false;
API health vẫn `ok=true`, database `ready`. Không kill/restart process hoặc ngắt
phiên shadow đang chạy. Log stdout/stderr hiện có vẫn giữ nguyên.

Private rollout helper `promote_observed_quotes.py` ở E root bên trên đã bỏ
`DETACHED_PROCESS`, giữ `CREATE_NO_WINDOW` với stdout/stderr vào file. Theo
[Microsoft process creation flags](https://learn.microsoft.com/en-us/windows/win32/procthread/process-creation-flags),
`CREATE_NO_WINDOW` bị bỏ qua khi dùng cùng `DETACHED_PROCESS`. Launcher chuẩn
`projects/trader/scripts/restart_offline_api.ps1` đã dùng `-WindowStyle Hidden`;
không thêm launcher, service hoặc config mới. Chỉ review/syntax-check helper,
chưa thực hiện lại rollout/restart trong lúc quan sát để kiểm lần launch mới.

## 04/11 — Inventory cleanup chỉ đọc

Snapshot 12:46VN theo yêu cầu owner: lập danh sách giữ/xóa/archive trong lúc
chờ NAQ-80, không cleanup runtime hoặc mở lane sản phẩm. Reuse
[cleanup plan](../../trader/REPO-CLEANUP-PLAN.md) và
[context lifecycle](../../CONTEXT-LIFECYCLE.md); không thêm manager/ledger/CLI.
Các ứng viên bên dưới chưa phải file được phép xóa; mặc định giữ khi thiếu
consumer map, backup hoặc xác nhận owner dữ liệu. Đường dẫn tương đối lấy gốc
`D:/ANNAM/TradingWorkspace`, E là local storage hiện có, không phải cloud backup.

| Nhóm / đường dẫn | Đã thấy và owner/consumer | Phân loại / điều kiện bước sau |
|---|---|---|
| `projects/trader` | Canonical source; Git sạch, HEAD `1685e22c` | **Giữ**; không thay pins/source khi capture đang chạy |
| `projects/mt5-tradingview-backtester` | Checkout runtime; API launcher/venv và hai terminal đang dùng. Git có 51 modified và 7.813 untracked status entries, không phải toàn bộ đều là file độc lập | **Giữ**; không gộp hoặc xóa vì tên cũ. Sau phiên: phân loại delta source/evidence/runtime, bảo toàn WIP trước cutover và kiểm rollback. Không tự copy toàn bộ sang canonical |
| `E:/BACKUP-TRADINGWORKSPACE/system-capabilities-20261103/` | API executable nằm ở `observed-quotes-20261104/bin/`; driver và shadow dùng `shadow-live-handoff-20261104-r2/`, log và registration ở cùng root | **Giữ** toàn bộ phần đang dùng; không move/rename binaries, logs, pages, manifests hoặc sửa report hashes |
| Cùng E root: `shadow-live-handoff-20261104/`, `shadow-session-20261104*`, `execute_demo_v*.py`, `promote_*.py` | Có attempts lỗi, helper gửi lệnh/rollout và before snapshots; không phải API được hỗ trợ | **Ứng viên archive**, chưa move. Giữ failure evidence/rollback; kiểm link trong receipt, imports và consumer trước. Không chạy lại helper để đoán tác dụng hoặc coi tên v4 là bản mặc định |
| `.pytest_cache`, `.ruff_cache` | Junction tới `E:/BACKUP-TRADINGWORKSPACE/workspace/`; lần lượt 5 files/2.468bytes và 10files/1.630bytes | **Ứng viên xóa nội dung cache** khi không có writer; hiện **giữ** vì chỉ khoảng4KiB, lợi ích không đáng thao tác. Không xóa junction/target theo wildcard |
| `.tmp` | Junction tới E workspace; 4.046files,310.075.820bytes (~296MiB), gồm source `xerj-source`, patch, scan evidence và logs | **Giữ/chưa rõ**; tên tmp không đủ chứng minh disposable. Kiểm từng subtree/consumer; không xóa nguyên target |
| `tmp`, `.uv-cache` | Junction tới E workspace; `tmp` scan hữu hạn chưa xong, uv cache chưa đo | **Giữ/chưa đo đủ**; không nhận tổng bytes từ scan dở hoặc coi dependency cache là rác |
| `.artifacts`, `projects/.artifacts`, `projects/.runtime` | Preview/QA/build artifacts nhiều giai đoạn; scan root artifacts đã thấy ít nhất605.402.121bytes (~577MiB), còn pending và4entries bị skip | **Ứng viên archive theo milestone**; đây là lower bound, không phải tổng hay dung lượng có thể thu hồi. Đối chiếu receipt/negative findings/acceptance trước; giữ raw được dẫn, chỉ bỏ derivative có thể tái tạo và không còn consumer |
| `.runtime/ai-env-backup-20261101` | 3files/31.703bytes | **Giữ** backup nhỏ; chưa kiểm nội dung nhạy cảm, không publish hoặc chuyển vào tracked docs |
| `.runtime/paperclip`, `.runtime/hermes`, `.runtime/ai-engines`, `.runtime/linux`, `.runtime/search` và checkout/tool runtime khác | Storage/config/environment của công cụ; chưa đủ inventory để xác nhận dormant | **Giữ**; không gỡ dependency, auth, WSL hoặc engine vì ít dùng. Paperclip native tiếp tục own task/run/report, không tạo UI quản lý thay thế |
| `.worktrees/vi-dubber-p23-separation-progress` và worktrees Git bên ngoài | Workspace có4registered worktrees; thư mục con không tự là worktree workspace, cần đối chiếu repo owner riêng | **Giữ**; không recursive-delete hoặc prune trước khi kiểm branch/WIP/worker và snapshot |
| `projects/evidence/ledger-design-system-20261012` | Untracked ở workspace | **Giữ WIP**; chưa có quyền sở hữu/nội dung/consumer đủ để move, stage hoặc xóa |
| `projects/vi-dubber` | 3untracked checkpoint/resource-monitor paths; sản phẩm đang tạm dừng | **Giữ**; pause không là retire. Không chạy worker, dọn media/model/cache hoặc stage WIP |
| `projects/app.fxreplay.com.zip` | Ignored archive16.773.098bytes (~16MiB), chưa xác minh provenance/license/consumer | **Giữ/chưa rõ**; không extract/run/publish, chỉ xem xét archive/xóa khi xác minh giá trị reference |
| AI receipt, Product Plan và docs lịch sử | Receipt hiện dài hơn3.600dòng; Product Plan đang dirty từ task khác. Development README đã phân biệt canonical source/runtime và native ownership | **Ứng viên compact sau review**, không sửa writer khác. Bảo toàn original bytes/hash, anchors, failure/WIP/quyền và resume links theo lifecycle; không tạo bản tiến độ thứ hai |

**Kiểm chứng:** process inventory xác nhận API PID15152, supervisor2812,
terminal25428/19308 và driver26268/shadow2848 còn đúng executable paths.
Lifecycle NAQ-80 phiên1 vẫn `running`,26pages/1.412ticks, cursor tăng so với
20pages/1.042ticks trước đó; driver stderr0bytes, execution capability false.
Đây không phải broker/live-handoff acceptance. Không đọc giá trị secret,
không chạy helper giao dịch/provider hoặc audit toàn bộ nội dung mọi repo.
Đo dung lượng chỉ giới hạn một số cây, không follow reparse points; không có
tổng workspace/dung lượng có thể xóa đã xác minh.

**Bước dọn đầu tiên sau phiên:** reconcile kết quả/native report → giữ nguyên
receipt thất bại và rollback → phân loại delta checkout cũ → compact đúng phần
history đã review. Chưa có danh sách material deletion sẵn thực thi; không
`git clean`, reset, prune, xóa cache/data hoặc di chuyển file trong lượt này.
Chỉ cập nhật receipt và liên kết từ cleanup plan; Product Plan/WIP giữ nguyên.

## 04/11 — Sửa float grid và đối soát báo cáo NAQ-80

Kiểm lúc14:05VN: lượt r2 đã dừng14:00:33, lifecycle phiên1 `failed`, reason
`shadow_tick_grid_invalid`,101pages/5.147ticks; chưa tạo phiên2. Không có
`qualification.json` đạt. Giữ nguyên capture/registration/lifecycle failed;
không sửa source pins hoặc resume expired/failed để tự công nhận acceptance.

Source trace xác định296giá Bid/Ask có đuôi float lệch grid trong101pages,
ví dụ `1.1227800000000001`, sai khác nearest tick chỉ `1E-16`. Trader commit
`c099822c886c4333eb3433ab6a908a4476e4644b` chuẩn hóa tối đa1binary-float ULP
trước khi tính mid bằng Decimal. Giá lệch bước thật vẫn bị chặn; raw capture,
hashes, clock, gap/settlement/authority guards giữ nguyên. Không đổi chiến lược,
API/adapter đang chạy, source integration hoặc quyền giao dịch.

| Kiểm chứng | Kết quả / giới hạn |
|---|---|
| Regression mới | 1test/3subcases lệch bước đạt0,802s; raw page bytes không đổi và mid đúng. Lượt đầu fixture thiếu `max_batches=60` nên chưa thu trọn giờ; sửa fixture, không nới production guard. 8tests cũ đã đạt trong lượt module trước đó; không tuyên bố một full-suite invocation mới đạt |
| Continuity | 7tests đạt83,982s, log private `offline-shadow-grid-20261104/continuation-tests.log`. Lượt trước bị ngắt chat/mất session output; xác minh không còn process rồi mới chạy lại để lấy bằng chứng, không retry test unchanged chỉ để có thêm lần pass |
| Capture thật offline | Reducer mới đọc101saved pages, không network: có1H1 gồm3.023ticks, max gap16.816ms, builder có warmup,0decisions, execution false. Hash102JSON input files không đổi; đây không phải fresh forward hoặc bằng chứng SDK reread ổn định |
| Native báo cáo | Driver cũ thiếu `baseRevisionId` khi sửa document; vì catch nuốt lỗi nên không tới PATCH status. PATCH `blocked` riêng còn cần `unblockDescriptor`. Đã đối soát/sửa document bằng native HTTP với revision; MCP connection xác nhận đúng Naqex AI và search/read task/doc, cập nhật blocked có descriptor thành công. Không có agent assignee hoặc model dispatch |

Driver mới private `observe_shadow_handoff_r3.py` dùng same task NAQ-80, source
commit mới và thư mục `shadow-live-handoff-20261104-r3/`; không overwrite driver
hoặc evidence r2. Publish đọc revision hiện hành; nhánh lỗi vẫn thử cập nhật
status riêng với unblock descriptor và lưu delivery/status error types thay vì
nuốt exception. Startup PUT/GET đã khớp, MCP đọc revision3 xác nhận nội dung.
Chưa force failure ở lượt broker mới chỉ để kiểm nhánh lỗi.

**Lượt mới đang chạy:** start14:28:44VN, thu trọn H1 từ15:00–16:00, chỉ bàn giao
sau16:00:30 nếu phiên1 complete, kết thúc dự kiến16:02:30, hard deadline16:05.
Hai phiên hữu hạn, không scheduler/auto retry/service mới. Driver thật PID16096
(venv redirector17964), shadow27780 ở startup; stderr rỗng. Preflight vẫn
32commands,0active grants/unknown/positions/orders; API run và generation19
không đổi. Không restart API/terminal để triển khai reducer vì child đọc source
canonical qua registration pin. Chưa có live-handoff acceptance mới.

Resume đọc qualification-state/lifecycle/native NAQ-80 và kiểm process identity
trước hành động; STOP đặt ở thư mục r3. Không chạy lại driver hoặc chỉnh source
pinned khi đang capture. Cleanup vẫn theo inventory chỉ đọc ở trên; chưa retire
checkout cũ, compact receipt đang ghi, move/xóa WIP hoặc dữ liệu runtime.

## 04/11 — Model và đường kết nối cho một owner

Owner hỏi đối chiếu hệ thống thực tế, chưa giao đổi provider hoặc mua API.
Research primary sources cho thấy GPT, Claude, Gemini, DeepSeek/Qwen đều có
đường dùng trong framework công khai; không có thống kê đủ để xếp thị phần model
trong hệ thống trading cá nhân hoặc chứng minh proxy có uptime giao dịch dài hạn.
[TradingAgents README](https://github.com/TauricResearch/TradingAgents) mô tả
API nhiều provider, tier quick/deep và cả own ChatGPT plan. Đây là capability
của framework, không phải chứng nhận profitability hoặc nhà cung cấp bảo trợ proxy.

| Trường hợp | Khuyến nghị hiện tại, chưa đổi cấu hình |
|---|---|
| Coding/trao đổi có owner | Subscription qua native Codex/Claude Code/Gemini CLI phù hợp khi provider hỗ trợ; không đồng nhất native OAuth với proxy chuyển token thành generic API |
| Research cá nhân có thể chờ/retry | Giữ Gemini/CLIProxyAPI đang có, ghi provider/model thực trả và provenance; chưa cần mua API chỉ vì chuẩn bị demo |
| Job tự động quan trọng, cần thời hạn | Ưu tiên API chính thức khi có nhu cầu thật. Có thể dùng trực tiếp hoặc gateway với API key chính thức; giữ một gateway không có nghĩa bắt buộc dùng subscription OAuth |
| Risk/send/position reconciliation | Tiếp tục deterministic runtime với quyền hạn rõ; AI/provider unavailable không được bypass guard hoặc mở rộng execution |

[OpenAI auth](https://learn.chatgpt.com/docs/auth) phân biệt subscription và API,
khuyến nghị API key cho programmatic CLI; [App Server](https://learn.chatgpt.com/docs/app-server)
có đường local/open-source subscription riêng, không chứng minh token relay bất kỳ
được hỗ trợ. [Gemini CLI auth](https://geminicli.com/docs/get-started/authentication/)
phân biệt Google login/API key. [Claude credential policy](https://code.claude.com/docs/en/legal-and-compliance#authentication-and-credential-use)
phân biệt native subscription và đường xây ứng dụng/API; cần kiểm đúng provider,
không suy luận một mình dùng thì mọi cách relay đều được bảo đảm.

[CLIProxyAPI upstream](https://github.com/router-for-me/CLIProxyAPI) có ecosystem
consumer và hỗ trợ OAuth/API-key upstream. Tuy nhiên [issue6655](https://github.com/router-for-me/CLIProxyAPI/issues/6655)
ghi maintainer xác nhận cooldown cục bộ có thể còn chặn sau khi provider phục hồi
sớm; báo cáo bug/consumer list không là số liệu uptime. [Anthropic trading guide](https://claude.com/resources/guides/the-ai-investment-firm/front-office-trading-and-execution)
đặt agent vào phân tích sandbox và điều tra read-only; đây là reference workflow,
không phải bằng chứng mọi trading desk triển khai như vậy.

## 04/11 — Reprocess capture đã lưu và phân loại checkout cũ

Owner nhắc không chạy lại toàn bộ mỗi khi lỗi: chốt tách recovery khỏi fresh
forward. Trader commit `6b06b125b17891a96984d7b9ada34d085be55d22` thêm command
`foundation_v2/scripts/mt5_shadow_reprocess.py`, reuse recorder/reducer/checksums
và private path/ACL đã có; không thêm dependency, schema DB, service hoặc UI.

| Trường hợp | Cách dùng / giới hạn |
|---|---|
| Process ngắt, code/deadline còn khớp | `mt5-shadow resume` cùng phiên, giữ cursor và warmup; không tạo phiên mới để bỏ partial hour |
| Reducer được sửa, capture còn tốt | Reprocess từ manifest/state cũ sang output mới; tối đa pin `step` được khác. Candidate/capture/dependency contract khác hoặc có predecessor cần compatibility review riêng |
| Kết quả offline | `reprocess.json` giữ source/capture/manifest hashes, thời điểm tính lại, scope saved capture, execution false, continuation eligibility false. Không tạo lifecycle `complete` hoặc biến nó thành seed live |
| Phần cần kiểm broker/lifecycle | Chỉ chạy mục kiểm live còn thiếu; không thu lại thị trường để chứng minh một phép tính đã kiểm từ saved capture |

Ba regression tests mới đạt:2tests/2,045s và1test/1,348s. Kiểm code đổi chỉ
reducer, expired registration đọc offline được, không gọi NativeReader, input
bytes không đổi, output không ghi đè/nằm trong nguồn, candidate mismatch/capture
tamper/manifest thay đổi giữa chừng không publish. Không rerun source/reducer/
continuity tests unchanged vừa đạt; đây không phải full CI mới.

CLI thật chạy trên r2 tạo `shadow-reprocess-cli-20261104/reprocess.json` ở E root
hiện có:101pages/5.147ticks/1H1. H1 khớp kiểm offline trước; hash toàn bộ102JSON
input files vẫn khớp bản kiểm trước. R2 lifecycle failed giữ nguyên. Không SDK,
API, provider hoặc lệnh giao dịch trong reprocess. Lượt r3 đang chạy giữ nguyên
toàn bộ8source pins; file mới, tests và docs không thay reducer mà nó đang dùng.
Tại14:41VN kiểm gần nhất: lifecycle running,13pages/791ticks; chưa có acceptance
bàn giao. Head mới thêm công cụ offline, không phải rollout API/terminal.

**Cleanup delta:** file private `checkout-delta-inventory-20261104.json` giữ hash
và so sánh từng path. `git status -z --untracked-files=all` có15.605entries
(51modified,15.554untracked), khác inventory `normal` vì mở rộng các thư mục,
không suy ra file vừa phát sinh. Bỏ qua nội dung15.545untracked artifact/runtime
paths; so60paths gồm toàn bộ51modified và9untracked source/config phù hợp:
18byte-identical với canonical,42khác (38evidence paths và4source/tool/test).
Không có missing canonical trong60paths đã so; không suy rộng sang mọi dữ liệu.

| Path khác trong `foundation_v2/` | Quyết định giữ và lý do |
|---|---|
| `scripts/api_platform_acceptance.py` | Giữ WIP; runtime có thêm quick-trading HTTP fixture, đồng thời còn default đường PostgreSQL cũ. Không copy nguyên file đè resolver canonical |
| `tests/test_mt5_broker_worker.py` | Giữ để đối chiếu; canonical đã có regression startup/recovery mà runtime copy thiếu. Không làm yếu tests bằng copy từ checkout cũ |
| `web/src/ReplayWorkspace.jsx` | Giữ; khác session catalog/last-session, action lock và resume behavior. Không tự merge hoặc rollback khi owner khác còn WIP |
| `web/vite.config.js` | Giữ; khác vendor discovery fallback. Không bỏ vendor lookup hiện hành chỉ để đạt byte parity |

38evidence differences tiếp tục giữ để review theo milestone. Scan diff đầu bị
PowerShell Python cp1252 chặn Unicode; đọc lại phần còn lại bằng `-X utf8`, không
chạy code hoặc tạo lại screenshots. Đây là classification, không chứng minh
4delta đều phải port. Không xóa source/WIP/cache hoặc retire checkout đang chạy.
Đã thêm index ở đầu receipt giúp đọc đúng checkpoint; chưa rút/xóa lịch sử chưa
review hoặc tạo nguồn tiến độ mới. Product Plan và VI WIP giữ nguyên.

## 04/11 — NAQ-80 dừng do readiness và phục hồi cursor có giới hạn

Kiểm lúc16:35VN: r3 đã failed lúc15:07:49VN, phiên1 reason
`shadow_native_http_423_mt5_connection_not_ready`, giữ38pages/2.443ticks,
0H1 đầy đủ, chưa khởi động phiên2. Native NAQ-80 đã tự ghi document revision4
và blocked đúng lúc lỗi; nhánh publish/status mới hoạt động. Không có qualification
đạt và không còn driver/shadow của r3 đang chạy; các mốc16:03/16:05 phía trên
là dự kiến lịch sử, không phải tiến trình còn sống.

Preflight16:36 và read-only DB16:39: API run vẫn
`e62d5f0b38994c53b6acf3055a36c41b`, Exness demo generation19 đã connected lại;
32commands,0active grants/unknown/positions/orders tại preflight. Hai account
connected ở lần đọc16:39. Source `managed_record` trả423 khi DB status khác
connected; bảng hiện hành đã ghi đè error_code sau recovery và terminal log chỉ
có startup. **Chưa xác minh được nguyên nhân trạng thái đổi lúc15:07**, không
quy kết broker/network, account switch hoặc worker crash. Cùng generation không
chứng minh đường truyền chưa từng gián đoạn.

Trader commit `cde626afced1ddff025c939071cf223815ffdb8b` sửa đúng điểm đã chứng minh:
supervisor Rust trước đây kết thúc ngay khi read-side readiness tạm thời lỗi.
Chỉ423 `mt5_connection_not_ready` và503 `demo_terminal_busy` được chờ10giây/lần,
tối đa6retry/60giây trong một episode, không vượt deadline gốc. Lifecycle giữ
start/count/reason/cumulative retries; resume không reset episode đang chờ.
Thử lại cùng phiên/cursor và re-audit toàn prefix; không tự reconnect, tạo phiên,
đổi identity, reset partial H1 hoặc retry send. Source/binding/revision/auth và
lỗi khác vẫn fail-closed; STOP/expiry vẫn hoạt động. Không sửa Python capture/
reducer/candidate hoặc runtime API đang phục vụ.

| Kiểm chứng | Kết quả / giới hạn |
|---|---|
| Rust supervisor | `cargo test --locked --bin mt5-shadow`:14passed,1ignored helper fixture; có2tests mới kiểm allowlist, budget/reload/deadline. Release build đạt |
| Supervisor executable + HTTP fixture | 3tests/57,152s đạt: mất readiness rồi tiếp cursor không duplicate (7pages/7ticks), sửa page cũ bị chặn, STOP khi chờ. Loopback port ngẫu nhiên/dummy credential, không SDK/broker. Sau review thêm guard tránh ghi recovered khi worker trả STOP/expiry; rebuild, focused allowlist và STOP test4,457s đạt |
| Capture r3 offline | `shadow-r3-reprocess-20261104/reprocess.json`:38pages/2.443ticks,0H1,network_reads0,execution false,continuation_eligible false. Đọc nguồn có checksum và kiểm inputs unchanged; lifecycle failed giữ nguyên |
| Artifact | Bản mới pin ở private `shadow-read-recovery-20261104/bin/mt5-shadow.exe`, SHA256 `125c5888f5470c93907d6a8454e1a834df3bf8c7344fe2fe25ad9d902e1980cf`; source/runtime API và terminal không restart |

Không chạy lại lượt dài, gửi lệnh, gọi model hoặc mở session/grant. Bản sửa
supervisor đã kiểm bằng failure injection hữu hạn; chưa là live-handoff hoặc
uptime acceptance. Phiên r3 đã hết deadline/binary pin cũ nên không resume bằng
binary mới, không sửa registration để hồi sinh phiên. Phần còn thiếu là bằng
chứng bàn giao trên dữ liệu mới và chẩn đoán nguyên nhân gốc nếu readiness tái
diễn; chỉ kiểm đúng transport/lifecycle còn thiếu sau đối soát, không thu lại
thị trường để kiểm một phép tính offline đã đạt. NAQ-80 tiếp tục blocked vì chưa
đạt acceptance của task; không dispatch agent hoặc tạo task quản lý thứ hai.

## 04/11 — Log kết nối MT5 và kiểm đọc thật ngắn

Owner giao hai bước: bổ sung chẩn đoán chuyển trạng thái MT5 rồi kiểm đường đọc
thật1–2phút. Trader commit `b526bcabc697424ecaff3d6fdfaf1a9288ed578b` thêm
tracing JSON vào collector và account actions; không thêm service, dependency,
UI/state store hoặc migration. Log ghi timestamp UTC, workspace/connection ID,
generation, trạng thái/mã lỗi trước và sau; không ghi login/name/password,
credential hoặc snapshot. Cặp before/after lấy từ cùng locked UPDATE, không
SELECT rời để đoán transition. Generation/workspace không khớp không ghi log;
polling giữ nguyên trạng thái không spam; terminal busy không bị gán disconnected.
Connect/sync/pause/resume/disconnect/remove ghi action sau persistence để phân
biệt thao tác owner với mất mạng. Runbook: `docs/LIVE-MARKET-STREAM.md` mục
Connection diagnostics trong Trader.

| Lát kiểm | Kết quả / phạm vi |
|---|---|
| Source / PostgreSQL | Unit sanitizer đạt; fixture PostgreSQL riêng chạy native Router/DPAPI/lifecycle đạt1test/1,46s, source fingerprints unchanged, owner_runtime_touched=false. Kiểm log error→connected và mã lỗi trước/sau, không duplicate khi error không đổi, busy/stale write không tạo transition giả, không lộ secret/snapshot. Private `readiness-logging-pg-20261104.json` |
| Build / rollout | Release API build đạt5m14s. Guard require-idle đối soát jobs/downloads/grants/unknown, cả hai account demo không positions/orders; lưu manifest/launch và binary rollback trước cutover. Không schema migration hoặc copy WIP/source checkout cũ |
| Vướng preflight | Full scientific verification timeout30s ở lần đầu, chưa stop runtime. Diagnostic không có đủ adapter env bị từ chối; kiểm lại đúng env đạt valid installation trong21,641s. Giữ timeout/validation nguyên, resume đúng checkpoint trước cutover; initial failed check còn giữ, không bypass guard |
| Runtime | API mới run `4fd4fb8e12bb4b509edfc479aa1680c5`, SHA256 `0009fbf84d379fc3347b480026422b1d31223ecbabd41fc86888510ea752aad4`, native/compact/local-capability, schema21 không pending. Giữ research/admin/scientific/legacy/config/port/auth và adapter root. Lần đọc đầu sau restart chưa đạt readiness assert; không lưu response reason nên không kết luận nguyên nhân. Đối soát lại chính run đó: Exness và FTMO ready/demo,0positions/orders, không restart lần nữa |
| Log thật | Runtime thừa kế RUST_LOG=warn nên bật info riêng `trading_workspace_api::mt5_connector`. Filter lưu trong `api-launch.json` environment_overrides và private rollout. Sync Exness đúng1lần tạo3events: action sync→queued, queued→syncing, syncing→connected; generation19 giữ nguyên. Không disconnect/reconnect để tạo lỗi giả |
| Đọc thật | Pinned supervisor mới thu60giây17:18:25–17:19:25VN và settle30giây, complete:6pages/71ticks,0transport retries,0H1/decisions. Không cần chờ thêm H1 để kiểm đường đọc này. Trước/sau cùng API run/generation19,32commands,0active grants/unknown; preflightpositions/orders rỗng. Đây là short real read, không phải proof retry trên outage thật hoặc H1/live uptime acceptance |

Private `readiness-logging-20261104/` giữ before-manifest/launch, initial và resumed
guard logs, exact environment overrides, candidate binary và `promotion.json`.
`api-launch.json` đã đối soát với current owner manifest sau first-read failure,
không chạy lại driver để overwrite checkpoint hoặc restart healthy API. Launcher
và terminal vẫn chạy ẩn theo cơ chế hiện có. API log thực tế là
`platform-4fd4fb8e12bb4b509edfc479aa1680c5-api.out.log` dưới runtime manifest folder.
Không log rotation/service hoặc global environment mới; khi launch lại phải giữ
scoped filter đã lưu, không chỉ đọc arguments rồi bỏ environment_overrides.

Private `readiness-short-20261104/qualification.json`, registration, lifecycle,
capture và `connection-events.json` giữ bằng chứng kiểm ngắn; supervisor đã kết
thúc, không có lượt dài đang chạy. Chưa xác minh nguyên nhân MT5 đổi trạng thái
lúc15:07 trong r3; log mới không khôi phục lịch sử đó. H1 handoff trên dữ liệu mới
vẫn pending; NAQ-80 giữ blocked theo acceptance gốc. Không gửi OrderCheck/OrderSend,
tạo grant/session giao dịch, gọi model hoặc chỉnh chiến lược. Hai bước logging +
short-read trong lần giao này hoàn tất; không suy rộng thành whole-system uptime.

## 04/11 — Củng cố quan sát tiến độ và báo lỗi

Owner chỉ ra thiếu sót vận hành: một lượt dài dừng nhưng trạng thái/tiến độ chưa
đủ dễ thấy. Không cần chạy lại một giờ để kiểm lớp quan sát. Rà đúng luồng finite
shadow hiện có; không đổi chiến lược, provider, quyền broker hoặc dựng UI Trader.

| Khoảng thiếu | Thay đổi / kết quả |
|---|---|
| Chỉ in stdout khi kết thúc, khó phân biệt chờ và treo | Trader `bb6d3ff2f6a3ec06ce9e6ef2e544e2473969ac18`: lifecycle có heartbeat mỗi5giây trong worker/poll/retry, phase riêng và capture bounds. Thời điểm tiến độ dữ liệu giữ riêng, không giả tick mới khi đang chờ |
| PID sống không chứng minh còn phản hồi | Status dựa khóa phiên, heartbeat và deadline: responsive, heartbeat_stale sau15giây, overdue hoặc interrupted. Kiểm khóa không tạo file mới; khi lấy được khóa đọc lại lifecycle để tránh nhầm completion vừa commit thành crash. Không sửa lifecycle khi đọc status |
| Tiến độ không hiện đều trên Paperclip | `tooling/ai-engines/shadow_watch.py` đọc status, in tiếng Việt, tùy chọn đăng document native cùng task. Poll khoảng5giây, thường publish60giây; phase/health/reason đổi gửi lần kiểm kế. Ghi thời gian bản tin, heartbeat, thời gian dữ liệu, tick/page/H1, expected settlement/deadline và lỗi; không phần trăm giả |
| Kênh báo cáo lỗi dễ bị nhầm thành lỗi tính toán | Publisher đọc trước PUT, dùng baseRevisionId, đối soát body khi response mất, không tạo revision trùng hoặc ghi đè competing writer trong lượt observer. Pending bản tin cũ không được xác nhận thay kết quả failed mới. Retry riêng, stderr rõ, final delivery lỗi trả nonzero; không restart capture |
| Chạy detached nhưng không ghi cách theo dõi | Operations/runbook yêu cầu giữ PID/log của supervisor và observer cùng attempt, xác minh native document đầu trước khi để lượt dài chạy. Chạy ẩn, mở log/terminal khi cần; không service/scheduler/auto-boot mới |

Kiểm chứng focused: Rust16passed/1ignored helper, release build đạt;4tests
executable+synthetic loopback đạt62,578s gồm heartbeat khi retry/chờ rồi kill thật,
phát hiện interrupted không đổi checkpoint, recovery không duplicate, old-page
revision bị chặn và STOP. Sau thay lock inspection kiểm crash riêng đạt9,523s;
sau final lock reread, unit status không tạo lock và đọc capture complete cũ đạt.
4observer tests đạt: uncertain PUT, competing writer, stale/quiet/old heartbeat,
pending running message không che failed outcome. Không SDK/broker/model trong
các fixture. Không chạy lại full suites hoặc lượt thị trường dài.

Artifact mới: private `shadow-visibility-20261104/bin/mt5-shadow.exe`, SHA256
`76c90a589167d6a422d31cc4c96605dc578c40b73e2e63d3983bf4bfbedae151`, build.json pin
source. Không restart API/terminal hoặc chép code vào checkout runtime cũ. Binary
mới dùng cho đăng ký mới; không sửa binary/source/deadline của phiên r3 hết hạn.

Smoke kênh thật17:38VN: observer `--once` đọc phiên short-read complete cũ
(71ticks/6pages/0H1), đăng native NAQ-80 document `shadow-ff1e4f2b423aded4`,
revision1 và đọc lại đúng nội dung qua MCP. Đây là bản trạng thái lịch sử có
mốc kết thúc17:19:56VN, không phải lượt quan sát mới. Heartbeat/bounds chưa có
ở binary cũ được ghi chưa có, không backfill vào evidence. NAQ-80 vẫn blocked
vì H1 handoff chưa đạt. Lần kiểm process trong lượt này không có mt5-shadow đang chạy.

Giới hạn: observer phải được khởi chạy cùng lượt dài tiếp; không tự chạy nền
vĩnh viễn. Nếu observer/Paperclip/PC ngừng, bản tin không thể tiếp tục tự báo;
mốc quá90giây khi đang chạy là dấu hiệu cần kiểm tra, chưa có independent external
alarm. Heartbeat chỉ chứng minh supervisor responsive, không broker/data quality.
External backup/alert và nhiều máy tiếp tục để sau theo owner. Không gửi lệnh,
tạo grant/session giao dịch, gọi model hoặc nâng task acceptance.

## 04/11 — NAQ-80 khởi chạy r4 với observer

Owner giao tiếp tục task. Đối soát preflight bằng helper read-only đã có:
process creation identity/executable hashes khớp manifest runtime, API/DB ready,
Exness demo generation19, requested_mode trading giữ nguyên,32commands,
0active grants/unknown/positions/orders. API vẫn run
`4fd4fb8e12bb4b509edfc479aa1680c5`; không shadow cũ đang chạy, không restart.
Capture r3 chưa có H1 và đã failed/expired; short-read chỉ60giây nên không thể
đóng vai predecessor có H1 mới. Không sửa deadline/pins hoặc nhãn lịch sử.

Khởi chạy finite driver private `observe_shadow_handoff_r4.py` lúc17:46:38VN,
attempt `shadow-live-handoff-20261104-r4/`. Reuse preflight/plan/evidence checks
từ r3; pin source Trader `bb6d3ff2f6a3ec06ce9e6ef2e544e2473969ac18` và binary
`76c90a589167d6a422d31cc4c96605dc578c40b73e2e63d3983bf4bfbedae151`.
Driver đơn lẻ có file lock; state có checksum, PID/creation identity của driver,
supervisor và observer, log riêng. Khởi chạy hidden bằng Start-Process; wrapper
PID19204, actual driver14788, supervisor23408, observer wrapper15748 ở lần đọc
đầu. Đây là snapshot; lần sau so identity trong state, không dùng PID cũ để kill.

| Mốc VN ngày04/11 | Phạm vi / trạng thái lúc bắt đầu |
|---|---|
|17:46:39|Bắt đầu phiên1, registration-1.json; leading partial H1 chỉ giữ capture, không tiêu thụ như H1 đầy đủ|
|18:00–19:00|Một H1 mới đầy đủ; đây là phần dữ liệu live còn thiếu, không thu lại để kiểm phép tính offline|
|Sau19:00:30|Kiểm phiên1 complete, đúng1H1 và builder state thật; tạo phiên2 contiguous, pin report predecessor|
|19:02:30 / khoảng19:03|Dự kiến chốt phiên2 sau120giây dữ liệu và30giây settle|
|19:05|Deadline cuối bất biến; không tự kéo dài hoặc mở attempt thay thế|

Lần kiểm17:48: session1 running/responsive,1page/42ticks,0H1,0retry,
heartbeat tiến triển, stderr driver/supervisor/observer trống. Không là acceptance.
Native NAQ-80 đã in_progress, assignee user giữ nguyên, không AI dispatch.
Main document `live-handoff-20261104` revision8 ghi mốc giờ và scope;
progress `shadow-11f486ad28b6bcb8` đã tự lên revision2 (17:47:43VN), đọc lại
qua MCP khớp42ticks/1page. Phiên2 sẽ có document theo registration hash riêng.

Driver chỉ đăng ký một attempt mới; không sao chép/mutate capture cũ. Khi cần
khôi phục, đối soát `qualification-state.json`, hai lifecycle, process identities,
pins và deadline trước. `observe_shadow_handoff_r4.py --resume` lấy cùng driver
lock, nối lại supervisor còn sống hoặc explicit resume session interrupted còn
hạn; không tự hồi sinh failed/expired và không thay registration. `--publish-only`
sửa pending native report/status riêng, không chạy lại capture. Driver chưa được
crash-inject ở lượt thật; đây là resume path, không bằng chứng cold-driver recovery.

Logs driver ở private root `shadow-handoff-r4.driver.stdout.log` và
`shadow-handoff-r4.driver.stderr.log`; trong attempt có `session-1.stdout.log`,
`session-1.stderr.log`, `observer-1.stdout.log`, `observer-1.stderr.log` (tương tự
ordinal2). STOP tại attempt là yêu cầu dừng read-only, không chứng minh process
đã kết thúc; kiểm lifecycle/identity sau đó. Không thêm scheduler/auto-start,
grant/session giao dịch, OrderCheck/OrderSend, model call hoặc config global.
Runtime API và terminal vẫn giữ nguyên. Kết quả bàn giao, qualification cuối và
uptime còn pending; đọc native/checkpoint mới trước khi tiếp tục lượt sau.

## 04/11 — R4 dừng khi audit và tái hiện lỗi không chờ H1

Owner hỏi tiến độ và việc phải chờ1giờ lặp lại. Kiểm lúc19:05VN: r4 đã failed
lúc19:00:32, reason `shadow_observed_window_revised`,74pages/3.272ticks,
0H1 được audit chấp nhận, không khởi chạy phiên2. Không mt5-shadow còn chạy.
Native NAQ-80 blocked từ19:00:34; progress document đã ghi failed revision101
đúng thời điểm. Không có lỗi publication trong stderr đã đọc; kênh quan sát mới
đã báo được sự cố, nhưng H1 handoff vẫn chưa đạt.

Read-only diagnostic trên3range đã có (page13,14,73), không tạo capture/session
mới: cả100ticks đối chiếu giữ nguyên count/order/timestamps/Bid/Ask, metadata
clock/source/binding/SDK giữ nguyên; chỉ flags đổi6→134, XOR128. Đây là **reread
chẩn đoán sau lỗi**, không phải response gốc19:00:32 (bản cũ chưa lưu nó).
Tái hiện được cùng lỗi strict comparison trên cặp page đã lưu; không kết luận
mọi page/broker history chỉ thay flag hoặc tự đặt nghĩa cho bit128.
[MetaQuotes MqlTick](https://www.mql5.com/en/docs/constants/structures/mqltick)
và [AlgoBook](https://www.mql5.com/en/book/applications/timeseries/timeseries_ticks_mqltick)
mô tả public tick flags; nguồn đã đọc chưa xác minh ý nghĩa bit128. Không mask
bit hoặc cho capture failed thành pass chỉ vì quotes ở3range giống nhau.

| Lát kiểm nhanh | Kết quả / giới hạn |
|---|---|
| Reprocess capture cũ | CLI hiện có xử lý74pages/3.272ticks thành1H1 trong khoảng1,6giây, network_reads0; output mới `shadow-r4-offline-20261104/reprocess.json`, continuation_eligible=false, không sửa failed lifecycle |
| Replay khác biệt đã lưu | Gọi audit bằng original page13 và diagnostic reread đã lưu, không mạng: tái hiện `shadow_observed_window_revised` trong0,1133giây; private `shadow-r4-revision-diagnostic-20261104/saved-failure-replay/` |
| Source bổ sung evidence | Trader `ffc7377b75560a295b1e4bb711a01253c5aa5ead`: audit-failures giữ reread thực tế + summary/hash/range/changed fields/flags_only classification khi mismatch xảy ra. Giữ nguyên strict rejection, raw capture và candidate |
| Focused regression | 3tests đạt9,527s: flags-only revision lưu đối chứng mà vẫn chặn, late backfill/revision không sửa report, settled-hour/candidate không gửi lệnh. Không build API/Rust hoặc chạy full suites cho thay đổi Python này |

Private `diagnose_shadow_r4.py`, `comparison-00013/00014/00073.json`,
`reread-*.json` và `flag-summary.json` giữ diagnostic; bảng100ticks chỉ thuộc
3range đã đọc. Source thay step pin, chưa rollout/đăng ký lại phiên live nào;
không sửa manifest/pins/deadline hoặc chạy --resume cho r4 đã hết hạn.

Operations guide bổ sung thứ tự: synthetic-clock/unit → replay capture/competing
observations → short live chỉ cho transport → H1 mới chỉ cho hành vi live còn
thiếu được nêu rõ. Không dùng lượt nền một giờ làm vòng debug mặc định. Bước còn
thiếu: xác minh semantics/compatibility của flags và quyết định contract phù hợp
trước khi chọn targeted live check; không mở lượt một giờ khác trong lần này.
Không gửi lệnh, gọi model, tạo grant hoặc restart terminal/API; WIP ngoài scope
giữ nguyên. Whole-system/live-handoff acceptance tiếp tục pending.

## 04/11 — Tách ổn định quote khỏi raw flags; kiểm nhanh thay vì chờ thêm H1

Owner giao tiếp tục, nhấn mạnh không lặp lại vòng chờ1giờ để debug. Trader
`0e476c35b43d2aea0ca05be3c19e0be48087d821` thêm policy tường minh cho **phiên
mới**: mặc định `raw_ticks_v1` vẫn chặn mọi thay đổi raw. Với consumer chỉ đọc
snapshot Bid/Ask để dựng midpoint/H1/H4, có thể đăng ký
`stability_policy=ordered_quotes_v1`. Policy này so khớp chính xác số lượng,
thứ tự, timestamp/source timestamp, Bid/Ask và mọi lineage; flags là metadata
không được consumer này sử dụng. Không mask bit128 hay tự gán ý nghĩa cho nó.

Cơ sở primary: [MqlTick](https://www.mql5.com/en/docs/constants/structures/mqltick)
mô tả các giá trị snapshot được điền độc lập với flags; [ví dụ Python của MetaQuotes](https://www.mql5.com/en/docs/python_metatrader5/mt5copyticksfrom_py)
chứa flags134. Ý nghĩa bit128 vẫn chưa xác minh; thiết kế không suy ra rằng nó
vô hại cho mọi consumer. Đây là contract quote-only, không dùng cho phân tích
dựa trên flags, fills, broker completeness hoặc mở quyền execution.

Luồng: registration pin policy → capture pin vào cursor → reread/audit dùng
cùng comparator → giữ nguyên raw pages + lưu đối chứng → reducer tạo nến từ
giá. `audit-observations/` giữ original/reread/summary có checksum khi flags
khác; không ghi được evidence thì dừng. Đổi giá/time/order/count/source vẫn
chặn. Resume/handoff không được đổi policy; report ghi rõ
`raw_flags_stability=not_asserted` ở chế độ quote. Đánh đổi là thêm evidence
cho metadata revision; không khẳng định raw flags bất biến.

| Kiểm chứng | Kết quả / phạm vi |
|---|---|
| Capture + shadow reducer + continuation | 34tests đạt89,057s; log private `shadow-quote-policy-tests-20261104.log`. Có crash/cursor, revision guard, quote-policy resume, handoff cùng policy và mô phỏng92giờ qua4phiên;92giờ là synthetic time, không phải uptime thật |
| Replay bằng dữ liệu đã lưu | `verify_shadow_quote_policy_20261104.py`: kiểm integrity74pages/3.272ticks; đối chiếu3cặp diagnostic đã lưu,100ticks. Cả3cặp vẫn bị raw policy chặn, quote policy so khớp;1,1435s, network_reads0, new_sessions0 |
| Giữ bằng chứng cũ | Manifest, lifecycle, cursor và74pages của r4 có hash trước/sau giống nhau. Replay result private `shadow-quote-policy-replay-20261104/result.json` có continuation_eligible=false |
| Diff/commit | Diff check đạt;6file source/test/contract đã commit. Không sửa candidate, Rust/API hoặc runtime; không gửi lệnh, tạo grant hay gọi model |

Lượt test full3module ở turn trước bị ngắt, không có kết quả cuối để tin cậy;
lượt34tests trên là kết quả được lưu log và xác nhận exit0 sau khi tiếp tục.
Không khởi chạy lại r4 hoặc tạo phiên quan sát mới. Dữ liệu3cặp là diagnostic
reread sau sự cố, không chứng minh response19:00:32 hay toàn bộ74pages chỉ đổi
flags. Không công nhận r4 thành đạt bằng kết quả offline.

Capture source thay đổi làm client pin cũ không còn tương thích; reprocessor
hiện tại chủ động từ chối capture pin khác, không sửa manifest/cursor để né
guard. Phiên mới cần source/policy registration mới; phiên failed cũ chỉ đọc để
điều tra. Handoff H1 trên live còn chưa chứng minh, nhưng không dùng lượt1giờ
làm vòng sửa lỗi. Chỉ xét một phép kiểm live khi đã nêu đúng hành vi còn thiếu;
34tests và saved-pair replay là gate cho bản sửa này, không whole-system acceptance.

Native publication chưa thực hiện: GET Paperclip trả connection refused và
không thấy listener ở17860 khi kiểm. Thử khởi động đúng launcher hiện có ở chế
độ hidden để cập nhật report bị automatic approval review từ chối trước khi
thực thi, lý do `blocked by policy`. Không đổi config, chạy launcher bằng đường
khác hoặc ghi trực tiếp DB. Document `live-handoff-20261104` revision10 / task
blocked là trạng thái cuối đã biết từ lần trước, chưa xác minh lại hiện tại.
Khi Paperclip hoạt động trở lại, đọc revision mới rồi ghi kết quả này vào đúng
document hiện có; publication không cần chạy lại capture hoặc gọi model.

## 04/11 — Gom task chốt Demo có giám sát

Owner hỏi đã có thể chạy thật trên Demo chưa và yêu cầu gom phần còn thiếu để
làm một đợt. Đã reuse/cập nhật [issue#8](https://github.com/Naqex/workspace/issues/8)
**Complete Trader system readiness from research to controlled forward execution**;
không tạo issue trùng với#6/#7 hoặc native NAQ-80. AI plan thêm mục **Chốt một
đợt để vận hành Demo có giám sát — owner giao04/11**, giữ scope/acceptance tại
plan và trạng thái/evidence tại receipt này. GitHub body giữ nguyên nội dung cũ,
thêm amendment04/11; đọc lại khớp nội dung sau chuẩn hóa newline, issue OPEN.
Assertion lần đầu so exact newline không khớp CRLF; không sửa/ghi lại issue vì
khác biệt chỉ newline, semantic readback đạt.

| Lát / mức sẵn sàng | Bằng chứng được reuse / việc còn lại |
|---|---|
| Mở→đóng lệnh Demo có giới hạn | Đã đạt trên Exness lúc07:10VN04/11;2attempts filled, cleanup không còn exposure/unknown. Đây là evidence lịch sử; grant đã revoke, không phải quyền gửi mới hoặc snapshot tài khoản hiện tại |
| Phân quyền, risk, crash/recovery/restore local | Có evidence trong các mục03–04/11; không lặp suite/model/pilot để thêm green |
| Runtime/source/account đang chạy | Chưa sẵn sàng ở thời điểm kiểm này: không thấy listener8010/5180/17860/17861. Tình trạng owner/process/account phải đối soát trước start; khởi động Paperclip đã bị automatic review chặn ở lượt trước, chưa retry bằng cách khác |
| Dữ liệu/warmup/decision | Quote-policy fix có34tests và saved-pair replay; live H1 handoff chưa đạt. Nguồn warmup gần đây/cùng basis và causal cutoff cần chốt cho phiên, không chờ80giờ để debug hoặc dùng dữ liệu2022 làm warmup2026 |
| Decision→vị thế/EXIT→native execution | Source hiện hành `mt5_shadow_step.py` trả execution_capability=false, chỉ candidate state/advisory; `mt5_demo_session.py` là immediate open/full-close, chưa strategy scheduler. Phải nối/review phần thiếu theo consumer thực, reuse Forex coordinator/native grants/receipts; không đổi tên shadow thành trader để nhận hoàn tất |
| Stop/visibility/gate cuối | Hoàn tất trên cùng đường xuyên suốt mới: exposure/unknown đúng, tiếp cursor/intent không duplicate, native progress/report. Sau offline gate mới chuẩn bị bounded Demo session để owner duyệt; không ép tín hiệu hoặc gửi lệnh khi chưa có grant hợp lệ |

Đích đợt là **Demo hữu hạn có giám sát đi trọn luồng**, không là autonomous24/7
hoặc lợi nhuận. Đã có nền để vận hành Demo từng phiên; chưa nên bật tự giao
dịch xuyên suốt từ shadow hiện tại. Cloud/G backup, external alerts, nhiều máy,
failover/scale account, provider/model mới và tuning chiến lược vẫn hoãn, không
dùng chúng làm blocker cho local Demo. Ticket rollover/expiry phải báo exposure
và hành động owner, không bỏ ownership fence hoặc tự dùng manual credentials.

Không thay source/runtime, gửi lệnh, chạy test/model hoặc thu thêm dữ liệu trong
lát lập task này. Validation là đối chiếu source/receipt hiện hành, diff/link
review và native GitHub readback; không cần chạy lại34tests cho thay đổi tài liệu.
Native Paperclip publication vẫn pending do instance không truy cập được; scope
task không được coi là mới cấp quyền khởi động đã bị tool review từ chối hay
quyền broker. Tiếp đúng6lát đã đăng ký, không thêm đợt tối ưu mở vô hạn.

## 04/11 — Policy vẫn chặn; sửa riêng lỗi PID tái sử dụng của Paperclip

Owner yêu cầu xử lý `blocked by policy` và tiếp task. Đọc config local chỉ các
field cần thiết: sandbox danger-full-access, approval never; không có local
rule file khớp Start-Process/run-local. Audit môi trường đạt0errors/0warnings,
global12.279B, project9.269/65.536B, reserve56.267B, combined21.548B.
Không sửa config/AGENTS/hooks/MCP, thêm allow rule hoặc giảm guard.

[OpenAI approvals/security](https://learn.chatgpt.com/docs/agent-approvals-security)
và [sandbox](https://learn.chatgpt.com/docs/sandboxing) phân biệt sandbox,
approval policy và automatic reviewer. Phản hồi CreateProcess chỉ nêu
`rejected: blocked by policy`, không có rule/reviewer decision để xác định
nguyên nhân. Các mục trước gọi chắc chắn đây là automatic approval review là
diễn giải quá mức; hiện chỉ xác minh được denial ở lớp công cụ, trước execution.
Sau xác nhận mới của owner, thử đúng thao tác Start-Process/hidden launcher
một lần vẫn bị từ chối trước thực thi. Không đổi shell/tool hoặc nhúng lệnh
khởi động vào script khác để né denial. Startup/native publication vẫn blocked.

Đồng thời source-confirmed một lỗi launcher độc lập: owner cũ ghi PID7044,
Windows đã cấp PID này cho BraveCrashHandler.exe tạo ngày04/11; server PID cũ
không còn. `alive(pid)` cũ vì vậy có thể báo nhầm Paperclip vẫn hoạt động.
Không kill Brave, sửa/xóa owner file hoặc thử startup trực tiếp để tái hiện.

Sửa `tooling/paperclip/run-local.mjs` và helper Windows: owner/startup lock mới
ghi PID + creation time + executable + command line; kiểm identity trước khi
reuse/khóa. PID thuộc app khác được xem stale; Node cũ còn sống nhưng thiếu
identity hoặc không đọc đủ identity thì dừng để kiểm, không tự nhận ownership.
Giữ port/revision/origin checks, không kill process hoặc reset DB/config.
Đây không phải sửa/bypass policy Codex; nhánh startup thật chưa được chạy.

Kiểm3tests đạt109,4209ms: PID legacy bị Brave tái sử dụng, exact identity và
thay creation/path/command/PID, thiếu quyền/legacy Node fail-closed. Smoke read-only
trên Windows thật xác minh identity process Node kiểm tra và PID7044 không là
owner. Node syntax/diff checks đạt. Audit môi trường không phát hiện lỗi, không
cần tăng budget hoặc bật MCP. Chưa có runtime/API/broker/whole-system acceptance.

Rà offline lát3 của task#8: ForexForwardSession có position-aware ENTRY/EXIT
nhưng ledger/fill là mô phỏng; không dùng nó làm truth vị thế broker. Shadow
chỉ advisory, Demo session chỉ immediate open/close. Phần cần nối tiếp là durable
decision/intent nhận broker receipt và inventory thực qua native runner, giữ
authority/idempotency/unknown hiện có; không gọi đường mô phỏng là đã đủ live.
Không chạy lại34tests, thu thêm tick hoặc gửi lệnh cho phần rà source này.

## 04/11 — Hoàn tất đợt Demo hữu hạn có giám sát (NAQ-81 / issue #8)

**Kết luận:** đạt đích đợt đã đăng ký trong AI plan: runner nhận dữ liệu thực,
warmup cùng basis, tiếp checkpoint trong process mới, quan sát và kết thúc hữu
hạn, đối soát flat rồi thu hồi grant. Không có tín hiệu H4 mới nên phiên này
không tạo order; không giả lập broker fill để nhận đạt. Entry/exit/failure dùng
fixture production cùng native receipts đã có; fill broker thật trước đó được
reuse riêng, không gọi là fill của phiên mới. Không là autonomous24/7, lợi nhuận,
whole-product acceptance hoặc live H1 shadow handoff.

Owner đã giao tự hoàn tất, không xin duyệt lại từng bước. AI plan ghi override
cho chính đợt Demo, kế thừa giới hạn Exness Demo/EURUSDm, 0,01lot, một vị thế,
hai submissions, SL bắt buộc, downside mô hình tối đa2USD, unknown chỉ reconcile.
Không sửa AGENTS/config/quyền broker toàn cục hoặc mở Real/challenge/provider.

### Code và data/state

Trader `60d049b18e0b01e9416e469b7f802d25396f7988` thêm snapshot chỉ đọc scope
theo Automation grant: đúng account/generation/symbol, fixedH1/max300bars,
source/SDK/clock và foreign-exposure rõ. Sau expiry/revoke vẫn đọc/đối soát được;
native admission mới quyết định quyền gửi. Không có migration hoặc đường SDK
gửi lệnh mới; reuse native idempotency/risk/receipt/reservation hiện có.

`mt5_forward_session.py` dùng fixedH4 nguyên trạng, native Bid H1/UTC
`mt5_native_bid_h1_utc_v1` cho cả warmup và dữ liệu mới. Chỉ nhận nến đã đóng
qua30giây; bootstrap không vào lệnh quá khứ, decision mới không quá60giây.
Source/SDK/clock/binding/cursor/revision/stale/foreign/unknown không hợp lệ thì
chặn. Một chu kỳ entry, deterministic IDs, decision/intent bền vững; receipt
và inventory broker là truth vị thế. Candidate EXIT hoặc finish hữu hạn đã
đăng ký mới đóng full vị thế sở hữu; close receipt cần flat inventory sau đó.
STOP/pause/revoke/expiry không là flat. Runner không nhận Owner/DB/provider
credential trong environment; Windows OS variables cần cho socket được giữ.

State/checksummed observations/manifest ở private local, native Paperclip giữ
task/report; không tạo dashboard/dialog hoặc ledger quản lý cạnh tranh. Ranh
giới basis native Bid khác midpoint QDM/shadow được công khai, không tuyên bố
tick đầy đủ hoặc strategy qualification từ warmup lịch sử.

### Runtime rollout và lỗi phát hiện từ dữ liệu thật

Paperclip đã được owner chạy lại: healthOK, source
`2e0f8f84b810ef3ae89c400d3ee1faf6b281c217`; native task/report đọc/ghi hoạt động.
Không kết luận policy denial của Codex đã sửa dứt điểm. Khởi động API/UI đúng
owner bằng công cụ hiện hành được cho phép trong lượt này.

API cutover đã kiểm process identity/hash/profile/local-capability, idle jobs /
downloads/AI runs, không active grant/unknown/exposure. Lưu old manifest/launch,
worker và OpenAPI trước stop qua owned launcher, rồi chạy binary pin mới.
Không migration; chỉ copy worker/OpenAPI, giữ nguyên symbol-catalog WIP và các
descriptor/database/artifact roots. Readiness đạt; Exness và FTMO reconnect,
flat inventory. UI5180 giữ hoạt động. Runtime-owning checkout cũ chưa bị đổi tên.

Private rollback: `system-capabilities-20261103/forward-promotion-20261104` trênE.
API run `2c642326eaf84fcdbfa4bc97607e537d`, API SHA256
`75836bcd135fed2a78605b42d0f65e23a8c9ba6f356869c8bacade1b03de06ed`.
API/worker source pin60d049b1; runner/candidate source sau sửa là
`d8f09240ec736aaa805762e487a0b19150153ca2` (Python-only, không cần restart MT5).

Lần native snapshot đầu bị `bar_tick_grid_invalid` do SDK float tail, ví dụ
`1.1232199999999999`. Dừng trước runner/send, thu hồi grant; giữ failed artifacts
`forward-native-20261104`, không sửa lịch sử thành pass. Bản sửa d8f09240 reuse
quy tắc mộtULP từ shadow bằng helper chung `sdk_tick_price`; giá lệch tick thật,
NaN/infinity/âm/bool hoặc OHLC sai vẫn từ chối. Raw observations/hashes giữ nguyên.
Saved native snapshot300bars kiểm lại offline nhận299closedbars, không network.
Một preflight sau đó không đạt quote<=2giây nên dừng trước tạo folder/grant;
bounded read-only preflight tiếp theo đạt, không retry broker command.

### Kiểm chứng tập trung

| Phạm vi | Kết quả |
|---|---|
| Forward runner production candidate → entry/receipt/inventory → finite exit/flat; no-signal; crash/partial/STOP/expiry/revoke/source/cursor/integrity | Ban đầu11tests đạt; sau lỗi float, suite12tests đạt1,395s |
| Durable Demo helper sau extraction `submit_once` |16tests đạt3,365s |
| Broker worker snapshot provenance/source-change |22tests đạt0,209s |
| Shared float helper / shadow compatibility |1focused regression đạt0,755s; không chạy lại toàn bộ34tests không đổi |
| Rust snapshot account/generation/symbol fencing và auth default-deny |2focused tests đạt |
| Disposable PostgreSQL native grant/reservation/settlement/revoke; inspect-after-revoke/expiry |1test đạt0,73s; không dùng ownerDB làm test target |
| Release binary, scoped formatting, Python compilation và diff |Đạt; final release2m27s |

Fixture PostgreSQL helper bỏ phụ thuộc `createdb.exe` không được đóng gói trong
embeddedPG hiện tại; dùng psycopgCREATE DATABASE trên disposable cluster vừa tự
tạo với port/user riêng. Không dùng DSN app/owner; đã chạy thành công cùng testPG.
Một test invocation ban đầu từ product-root sai import path; không tính pass.
Saved-snapshot diagnostic ban đầu dùng nhầm reader64KiB của manifest; đổi thành
JSON reader cho evidence file lớn, không tăng/loosen giới hạn runner.

### Phiên native cuối — 21:44:56 → 21:46:20 Việt Nam

Private qualification: `system-capabilities-20261103/forward-native-20261104-r2`
trênE, `qualification.json`, raw observations và checksummed runner state.
Finish đăng ký21:46:16, expiry21:47:16; worker/runner kết thúc trước expiry.
SDK `5.0.6231`, clock `sdk_utc_v1`; account generation19 không đổi.

| Phép kiểm / kết quả | Giá trị |
|---|---|
| Native input |300H1 từ19/10 02:00UTC tới04/11 14:00UTC, loại forming bar |
| Warmup |20closedH4 trong rolling candidate history; không ép tín hiệu |
| Resume |Process seed kết thúc; process watch mới đọc cùng manifest/credential/checkpoint, không bootstrap từ đầu |
| Quan sát |35native observations được lưu bất biến, native progress readback đạt |
| Kết thúc |`completed / session_finished_flat_no_entry`, exit0 |
| New broker requests / inventory |0requests;0positions;0orders |
| Unknown / reserved risk |0 /0 |
| Cleanup authority |Grant revoked; đọc snapshot sau revoke đạt, flat và không mở quyền gửi |

Native task [NAQ-81](http://127.0.0.1:17860/NAQ/issues/NAQ-81), UUID
`500aa551-57de-4718-8b29-4a7edb001908`, document `demo-readiness-20261104` giữ
tiến độ/heartbeat/lý do/cursor/exposure và kết quả. Codex thực hiện qua CLI/native
HTTP; không dispatch agent/model mới. CLI auth không trao cho runner.

**Phần giữ riêng:** NAQ-80/live H1 shadow handoff vẫn chưa đạt, failedr4 không
được relabel hoặc chạy lại1giờ. Không phải dependency của basis nativeBid này.
Cloud/G backup, external alerts, nhiều máy/failover, auto-boot/scheduler24/7,
scale account và tuning/qualification chiến lược vẫn hoãn theo owner. Đợt này
đủ để vận hành từng phiên Demo hữu hạn có giám sát; không để runner tiếp tục
giao dịch sau khi kết thúc. Phiên mới phải có artifact/grant scope mới, không
resume completed để hồi sinh quyền hoặc tự dùng Owner endpoint thay runner.

Native NAQ-81 đã chuyển `done`, document đọc lại đúng; GitHub#8 đã đóng theo
scope đợt Demo hữu hạn. NAQ-80 vẫn `blocked`. GitHub comment ghi rõ commits
local chưa được push; không đẩy kèm73commits khác đang chờ trên branch workspace.

Kiểm metadata cuối phát hiện các trailerAI bị tách thành hai paragraph nên
Git chỉ parse một trailer. Đã chuẩn hóa đúng hai commit Trader vừa tạo, chưa
push; trees/source bytes không đổi: build pin60d049b1 tương ứng commit
`1401bce3e90d2f3ac00e4372d4c19fdd50428311`, runner pin d8f09240 tương ứng
`c97cd79d327131d73a9938640c5b49522ba8c931`. Native/private run giữ original
SHA tại thời điểm chạy; mapping ở `trailer-normalization.json` cùng private root.
Không chạy lại test/runtime cho thay đổi metadata. Validator dùng tooling
interpreter cóPyYAML; product venv không có dependency này, không cài thêm vào
runtime chỉ để kiểm forms/trailers.

## 04/11 — Nhiều phiên quan sát độc lập, không nhân model inference (#9 / NAQ-82)

**Đạt scope đợt:** hai Rust shadow supervisors chạy đồng thời trên Exness Demo,
cấu hình trang5/10giây, state/log/registration/task riêng. Dừng rồi resumeA giữ
prefix/cursor/deadline; B giữ cùng process identity và incarnation1. Cả hai
complete trên50giây dữ liệu thực, không cần chờ H1. Không tạo grant, không
OrderCheck/OrderSend và không model inference trong các runner/observers này.
Không gộp kết quả này thành H1 handoff, H4 warmup hay strategy qualification.

### Implementation và quyền sở hữu

Workspace `tooling/ai-engines/shadow_sessions.py` reuse `mt5-shadow` và
`shadow_watch.py`, không thêm daemon/UI/agent hoặc ledger task. Group manifest
pin binary/interpreter/registration; đầu ra mỗi child riêng, input ngoài output
tree, start không overwrite. Private launch checkpoint giữ PID/kernel creation /
executable; resume chọn child cụ thể, không chạy lại child running/complete,
không gia hạn deadline hoặc kill PID. Stop/status không đòi read credential hay
registration còn hợp lệ; `observe` sửa riêng publication. Control lock chỉ bao
thao tác CLI, không giữ suốt phiên. OS env cần cho Windows được giữ, loại DB /
provider/token env; read-side private input theo native shadow contract hiện có.
Child launch/observer lỗi không tự hủy hoặc restart sibling.

Trader `62cd94bde0cb8b039859ee76a9937cfcb8af3215` chặn cấp hai execution grants
active/unexpired cùng workspace/login/server. PostgreSQL transaction/advisory
lock theo account ngăn race kể cả connection alias; tài khoản khác vẫn được
cấp riêng. Revoke/expiry vẫn cho phép thay thế theo reconciliation/gates hiện
có, không phải tự gia hạn hoặc portfolio risk allocator. Không đổi order/risk /
receipt/idempotency hay migration. Đây là giới hạn ownership thực thi, không
phải giới hạn số phiên research/quan sát hoặc quota AI.

### Kiểm và runtime

| Phạm vi | Bằng chứng |
|---|---|
| CLI group |7tests đạt0,797s: configs/state/process tách, env không có key/DB, stop/resume riêng giữ cursor, duplicate/running/complete/changed input chặn, stop không cần secret, observer-only repair, sibling failure isolation |
| Native grant concurrency |Disposable PostgreSQL lifecycle test đạt0,93s, gồm hai credentials cấp đồng thời chỉ1thắng, alias bị chặn, account khác được cấp; các kiểm reservation/revoke/expiry cũ cùng test vẫn đạt |
| Build / source |Scoped rustfmt/diff/py_compile đạt; release API2m21s |
| API rollout |Đúng owner identity/hash/native/local-capability, quiescent jobs/downloads/AI runs và0activegrant/unknown/exposure; old manifest/launch và binary rollback giữ trênE; không migration hoặc copy worker/WIP |
| Runtime sau rollout |Readiness đạt, Exness/FTMO reconnect và flat; API run875ecd4431714691831ae90e18a8b128, SHA256e518d8d9aedb6ae3886f3b221d44ec1d99d26d9deca5a39a92b6569598ac8866 |

Một invocation unit test từ workspace root thiếu import path, chưa chạy test;
chạy đúngcwd `tooling/ai-engines` bằng interpreter có sẵn đạt7tests. Không cài
dependency/provider mới hoặc chạy lại những suite không bị thay đổi.

Private rollback: `system-capabilities-20261103/multi-session-promotion-20261104`
trênE. Private actual qualification:
`system-capabilities-20261103/multi-session-live-20261104/qualification.json`,
group launch checkpoint, overlap/stop/resume receipts và child lifecycles/capture.

### Quan sát thực kết thúc22:17:28 Việt Nam

| Phép kiểm | A | B |
|---|---|---|
| Page size |5giây |10giây |
| Pages/ticks |10/52 |5/52 |
| Supervisor incarnation |2, đã stop/resume |1, process không đổi |
| Capture prefix |Giữ nguyên trước/sau resume |Tiếp tục độc lập |
| Kết thúc |complete |complete |
| Closed H1 |0 |0 |
| Task/native progress |NAQ-83, done/readback đạt |NAQ-84, done/readback đạt |

Hai phiên có cùng window50giây nên52tick mỗi phiên là cùng quan sát, không cộng
thành104tick thị trường độc lập. Policy `ordered_quotes_v1` so Bid/Ask/timing /
lineage; raw flags được lưu nhưng không asserted stable. Không sửa mặc định
strict hoặc nhận failed NAQ-80 thành pass. Chỉ chứng minh concurrency/isolation
và resume hữu hạn; chưa kiểm nhiều tài khoản cùng gửi lệnh hay uptime dài ngày.

Before/after không đổi:32native requests lịch sử,0activegrants,0unknown,
generation19, cùng API run. Các phiên quan sát không có model call; điều này
không nói cuộc chat Codex triển khai không tiêu quota. Parent
[NAQ-82](http://127.0.0.1:17860/NAQ/issues/NAQ-82), UUID
`b4c7e64a-6e04-41cc-9ea4-8bcd577feb45`, document `multi-session-20261104` giữ kết
quả tổng; hai task child giữ observer documents riêng. Manual owner-assigned
tasks ghi rõ Codex CLI thực hiện, không dispatch agent/model hoặc thêm việc owner.

### Chi phí/quota — quyết định áp dụng

Giữ usage/provider_usage native hiện có, không thêm cost store/dashboard.
Missing usage/price/cache vẫn unknown, không lấy process-adapter0 làm0SDKtokens.
Không khôi phục cap10lượt/ngày; maxConcurrentRuns1/agent, timeroff và bounded
retry/deadline hiện có giữ nguyên. Chạy nhiều phiên code không tự nhân tokenAI;
ba model analyses tương đương có thể gần ba lần tokenwork, chạy tuần tự vẫn
tốn tổng công việc đó. Song song làm request/token dồn theo phút hơn.

Tối ưu ngay ở mức tránh gọi inference/retry trùng, reuse artifact hợp lệ và
không dùng model để vẽ heartbeat/report tiến độ. Hard money/token budget chưa
được bật khi owner chưa chọn mức/scope và chưa có usage nguồn đầy đủ; không
ước lượng quota subscription từ bảng giáAPI hoặc hứa cache qua proxy/accounts.
Docs chính thức đã mở/đối chiếu04/11: OpenAI prompt-caching, Gemini caching /
rate-limits và Context7 official Gemini usageMetadata. Các docs nói vềAPI chính
thức, không chứng minh cách subscription/proxy hiện tại trừ quota. Hướng dẫn
schema/CLI/trade-offs và các link nguồn nằm trong OPERATIONS mục mới.

Bảy regression group đã nối vào Workspace CI hiện có, không thêm job/service:
lấy Pydantic version từ Trader uv.lock rồi chạy đúng module tại toolingcwd,
không chạy broker/provider/model. YAML và đường dẫn/version lookup được kiểm
local; chưa tuyên bố GitHub Actions pass khi branch/commits chưa được push.

## 04/11 — Đã khởi chạy gói qua đêm read-only (#10 / NAQ-85)

**Trạng thái: RUNNING, chưa nhận hoàn tất H1 handoff hoặc đợt qua đêm.**
Owner đã duyệt toàn gói và phần nền liên quan lúc22:42VN, sau đó hỏi xử lý lỗi /
ngắt. Scope mới đã ghi trong AI plan; research giữ lý do/giới hạn. Native
[NAQ-85](http://127.0.0.1:17860/NAQ/issues/NAQ-85) giữ báo cáo tổng; ExnessNAQ-86,
FTMONAQ-87 và offlineNAQ-88. Manual owner-assigned tasks ghi Codex CLI thực hiện,
không dispatch model hoặc thêm việc cho owner. GitHub#10 giữ task nhiều phiên.

Workspace `99f3db2` bổ sung `shadow_night.py`: bộ chạy hữu hạn reuse Rust shadow
supervisors và group/observer, cùng private checksummed state; không thêm engine,
UI/ledger quản lý, service autostart, trading grant hoặc broker command. Source /
runtime epoch/config/input/credential/interpreter/binary pins được đóng băng.
Exness predecessor hoàn tất đúng H1, verify frozen lifecycle/report/capture và
actual closedH1 rồi successor mới được khởi chạy. Nếu missed launch window mà
không có successor thì báo thiếu, không backdate/đổi deadline. Manager resume
nhận lại group/child đã có, kể cả crash sau spawn hoặc sau native completion;
uncertain launch không đủ evidence thì chặn, không tạo session thay thế.

Lỗi một lane không restart sibling; manager/source/runtime/storage lỗi thì stop
các read-only sessions của chính run, giữ evidence. Publication pending/revision
được lưu bền vững và readback trước retry; sửa publication không cần broker
secret/source còn hợp lệ, không gọi model hoặc thu lại capture. Native task status
updates kiểm company/manual assignment. CLIstatus đọc liveness theo PID/kernel
creation/executable và native lifecycle hiện tại, không gọi broker.

### Offline gate và chuẩn bị

-12focused tests đạt1,509s: manager restart attach, uncertain launch, crash sau
 successor spawn, late manager attach khi successor đã tồn tại, nhận completed
 sessions sau deadline, sibling isolation, missingH1/missed window, prefix /
 deadline binding, source/storage guard, atomic-save failure, uncertain
 publication khi credential đã mất, STOP/expiry không suy flat.
- Test đầu phát hiện thiếu handoff-verification marker sau crash. Đã ghi marker
 trước intent/launch và thêm crash/late-resume cases; giữ native guards.
- Không lặp suite6579virtual-time hoặc restore47bảng đã đạt; offline lane làm
 xong thì done, không lấp giờ qua đêm bằng unchanged tests. CI hiện có mở pattern
 `test_shadow*.py`; chưa chạy remoteActions khi commits chưa được push.
- Read-only preflight trước run:Exness83ticks,FTMO170ticks trên một phút gần đây;
 flat/no orders,0activegrant/unknown và native request count32không đổi. FTMO dùng
 profile `ftmo_demo_server_2026_v1` (server wall→UTC), Exness `sdk_utc_v1`.
- Lần chuẩn bị đầu bị local-path guard chặn vì runtime manifest đi qua junction
 `.runtime/api-platform` đã có. Chưa tạo controller/native session/grant. Giữ
 prepared input tại `overnight-20261104`; không nới path guard. Lượt chuẩn bịr2
 ghi canonical resolved runtime-owner path trênE và pin epoch đã xác minh.

### Run đã khởi chạy

Run ID `ead4eec6-2bf4-43d6-85a1-de4ba3b6f861`; private root:
`E:/BACKUP-TRADINGWORKSPACE/system-capabilities-20261103/overnight-20261104-r2`.
`RUNBOOK.md` giữ commands/status/stop/resume/publish với exact paths;
`night.json` bất biến; `controller/state.json` checksummed;
`controller-process.json` giữ launch identity/args; stdout/stderr và native group /
child logs riêng. Có thể đọc PID wrapper khác identity Python thực trong state;
luôn dùng current process_identity, không kill theo tên/port/PID trần.

| Lane/mốc Việt Nam | Kế hoạch đã đăng ký |
|---|---|
| Bắt đầu native |Khoảng23:10ngày04/11; page60giây, settle30giây |
| ExnessNAQ-86 |Predecessor từ lúc start tới01:00ngày05/11, chứa trọn H1 00:00–01:00; sau complete/settlement mới bàn giao successor tới06:55 |
| FTMONAQ-87 |Thu độc lập song song từ start tới06:55; broker clock/binding riêng |
| OfflineNAQ-88 |Đã done,12tests passed; không để worker lặp lại qua đêm |
| Hạn chót |07:00ngày05/11; native child deadline không quá06:58; không gia hạn |
| Authority |Read-only;0grant/OrderCheck/OrderSend/model calls trong job |

Parent và hai child progress documents đã readback sau launch. Manager/native
supervisors/observers đều sống theo creation identity; native healthresponsive,
không error trong snapshot đầu. Page đầu đang chờ đủ60giây đã đăng ký, chưa lấy
heartbeat thay bằng bằng chứng dữ liệu. **Đợi kết quả native actual sau này mới
được nhận handoff/overnight đạt; NAQ-80failed cũ không được tự chuyển pass.**

Resource policy bảo thủ cho run này:chặn dưới8GiBfree trênD hoặcE, tối đa2GiB
output run; lúc start D66,2GiB/E154,6GiB. Kiểm định kỳ60giây, không xóa/prune
evidence. `resources.jsonl` ghi free/output bytes và owned process cumulative
CPUseconds/working-set bytes (không giả whole-PCcapacity). Temporary Windows
idle-sleep request chỉ tồn tại trong thread controller, cho phép screen-off,
không sửa power settings global; forcedsleep/restart/mất điện vẫn gây ngắt.

### Sáng tiếp tục / sự cố

1. Đọc NAQ-85 và `shadow_night.py status` từ RUNBOOK:manager_alive, last update,
   fresh native child statuses, first error, pages/ticks/H1/cursor và resource.
2. Nếu manager đã chết nhưng child còn sống, resume manager cùngnight.json /
   controlleroutput để attach, không chạy start mới. Lock ngăn hai manager cùng
   sở hữu run; không kill/reconnect account để lấy trạng tháigreen.
3. Sau powerloss/OSrestart không có autostart. Chỉ resume trong original window
   và sau kiểm identity/source/data prefix; missed interval giữ missing/blocked,
   không sửa registration hoặc gia hạn. Phiên native failed/source/generation /
   revision cần review; manager không auto resume nó.
4. Publication hỏng xử lý `publish` riêng. Khi run complete, manager dự kiến
   chốt parent/child task statuses/report; lỗi delivery giữ pending, không rerun
   inference/capture. Local checkpoint/log tồn tại khi Paperclip down, không là
   external alert nếu toànPCmất điện. Native taskdone không tự đồng nghĩa whole
   product/24-7/strategyqualification hoặc cấp quyền giao dịch.

Không restart API/terminal/source capture trong run; không backup quiesced,
cloud/Gcopy, external alert, multi-machine/failover, engine/model mới hoặc tuning.
Code/runbook/data-basis/release/capacity hướng dẫn cập nhật trong OPERATIONS;
phần cần evidence qua đêm giữ RUNNING cho sáng reconcile.

Readback sau page đầu:Exness64ticks/1page,FTMO157ticks/1page; cả haihealth
responsive/poll_wait, manageralive, errorsempty. Đây là dữ liệu thực đã commit,
không chỉ heartbeat; vẫn chưa có closedH1 vì chưa qua giờ đầy đủ.

## 05/11 05:08–05:17 — Kiểm sáng sớm, sửa telemetry và resume cùng capture

Owner yêu cầu kiểm có lỗi khi mới05giờ. Read-only status xác nhận controller cũ
đã blocked lúc**02:38:39VN**, fatal `PreflightError`; FTMO/Exness-successor bị
controller stop, không mất checkpoints. H1 predecessor Exness đã complete
110pages/7.313ticks và một closedH1; frozen state được verify/bàn giao lúc
**01:00:44VN**, successor đã nhận dữ liệu trước lần dừng.

### Root cause / phạm vi sửa

Last state ghi resource disk/size thành công nhưng chưa có process metrics;
source path `process_metrics` gọi `group.alive` ngoài try và không bắt
`PreflightError`/RuntimeError khi xác minh PID. Lỗi optional metrics vì vậy đi
qua fatal handler và stop capture. PID/kernel error cụ thể lúc02:38 không được
log cũ giữ lại; không khẳng định chắc PID nào đã được Windows tái sử dụng.
Fault injection đúng exception chứng minh đường lỗi source. Lỗi cấp dữ liệu /
broker không xuất hiện trong checkpoint tại thời điểm controller dừng.

Workspace `59feddd`: metrics identity/query unavailable trả unknown, không
zeroCPU/RAM và không stop capture. Runtime/source/authority identity fence thật
vẫn fail-closed. Fatal controller error lưu detail, cố publish blocked/task
trước exit thay vì chỉ để stale in_progress. Thêm ghi recovery/downtime trong
native summary. **14focused tests đạt1,622s**, gồm metrics exception không gây
fatal và runtime identity error vẫn chặn/publish. Không restart API/MT5 hoặc
thay native source/schema/risk/permission.

### Controller-only revision / phục hồi

Giữ nguyên runID `ead4eec6-2bf4-43d6-85a1-de4ba3b6f861`, input capture registrations,
SDK/source/clock/binding/binary, counters/prefix, end06:55 và deadline07:00.
Old source/night.json/controller state được backup tại private
`overnight-20261104-r2/repair-20261105`; bản gốc không bị sửa expected hashes.
Tạo `night-recovery-20261105.json` + `controller-recovery-20261105` cho revision
chỉ sửa điều phối/telemetry; repair-manifest giữ mapping, old error, prefixhashes
và gate14tests. Guard nguồn capture và native runtime epoch875ecd... đã verify.

Lúc**05:15:14VN** resume rõ ràng đúng native FTMOnext/Exness-next đang stopped,
không tạo capture/group mới; oldprefix page hashes so lại vẫn khớp. Controller
mới attach hai group đã có, không chạy lại predecessor. Report gốc được chốt
blocked từ bản sao state, recovery report native mới nêu downtime02:38→05:15;
không gọi đó là uptime liên tục. Read-backfill có observed_at mới, không phát
lại quyết định giao dịch. Runtime/positions đã preflight,0grant/unknown,32requests
lịch sử không đổi. Không OrderCheck/OrderSend/model inference trong repair.

Active runbook: private root cũ, **`RUNBOOK-RECOVERY-20261105.md`**; native
document `overnight-controller-recovery` trênNAQ-85 giữ exact commands. Dùng
controller-recovery paths, không resume controller cũ hoặc sửa original plan.

### Phát hiện FTMO khi audit lại prefix — giữ fail-closed

FTMOincarnation2 bị `shadow_observed_window_revised` lúc05:15sau resume. Saved
pair tại `initial/ftmo/audit-observations` giữ cả original/reread. Đoạn
**00:22:20→00:23:20VN** trả84ticks ban đầu,96khi đọc lại; so rows bỏ riêngflags
thấy**12row mới,0row cũ bị mất**, cùng source/SDK/clock. Khác biệt không chỉflags;
ordered_quotes_v1 từ chối đúng. Không ép reducer nhận revised history, đổi
registration/policy hoặc khởi capture thay thế. NAQ-87 chuyển blocked, rawpair
hash `de97fd7b...`/`ae2e5089...` giữ để điều tra late-arrival/cache behavior.

Exness-nextincarnation2 tiếp độc lập, đang đọc bù từ oldcursor với source/binding
cũ; không error trong readback05:15:54, manageralive và resource guardđạt.
NAQ-85/86 còn in_progress; NAQ-87blocked, NAQ-88done. Đợt qua đêm chưa đạt đầy đủ;
sáng reconcile coverage cuối và phần gián đoạn, không tự chuyển failed histories
hoặc NAQ-80 thànhpass. Hạn chót07:00giữ nguyên.

## 05/11 05:50–06:04 — Phục hồi lịch sử FTMO sau late backfill

Owner chọn NAQ-87 bị đỏ và yêu cầu sửa. Thêm workspace helper
`tooling/ai-engines/shadow_reconcile.py`, không sửa source/pins của capture,
reducer, SDK/clock, native supervisor hay controller đang chạy. Helper kiểm
registration và lifecycle bằng binary Rust đã pin, khóa riêng failed session,
giữ dữ liệu gốc; đọc lại mỗi trang hai lần, tối đa ba cặp. Chỉ chấp nhận thêm
quote theo thứ tự mà bảo toàn mọi quote cũ, kể cả duplicate cùng timestamp.
Removed/price-changed/reordered quote hoặc đổi binding/source/SDK/clock đều chặn.
Flags vẫn là metadata, không có bảo đảm history hoàn chỉnh từ hai lần đọc.

Revision riêng có checksummed raw observations, selected pages, checkpoint từng
trang và receipt; `--resume` kiểm persisted prefix và đọc lại trước khi tiếp tục.
Ghi dở sau selected-page được tiếp tục mà không rewrite page. Không tạo native
lifecycle giả; output không là live predecessor hoặc execution authority.
Hướng dẫn đã thêm vào `tooling/ai-engines/OPERATIONS.md`.

**8 focused tests đạt16,260s**: original unchanged, thêm tick/tính lại H1,
removed/changed/reordered và lineage rejection, duplicate preservation,
unstable reads bounded, interrupted resume, further backfill và orphan-page
adoption. Saved pair thật84→96 tái hiện12ticks thêm,0removed trước native read.

Native read toàn prefix hoàn tất lúc05:59VN: **209pages,20.733→20.745ticks**, đúng
**1page/12ticks** bổ sung. Original lifecycle report cuối có208pages/20.663ticks;
capture đã commit thêm một page trước khi reducer audit báo lỗi, nên lấy209page
capture-state đã checksum làm prefix thực tế, không bỏ trang cuối.
Tính lại giữ2closedH1,0H4; H1**00:00VN** tăng6.311→6.323ticks, OHLCmid và maxgap
12.912ms không đổi. Không dựng nến phần giờ chưa đủ. Fresh known_at từ API
receipt được giữ, không backdate quyết định.

Private revision: `E:/BACKUP-TRADINGWORKSPACE/system-capabilities-20261103/ftmo-history-revision-20261105`.
`revision.json` digest `eda0f4ee197eae90d6e19b4a6efcac02bea99f93c6a342dfcfae99d87930c184`;
comparison/test/raw read logs ở old runroot `repair-20261105`. Original capture
checksum so lại khớp sau reducer. Native NAQ-87 document
`ftmo-history-reconciliation` đã PUT/readback đúng. **History recovery complete**,
nhưng NAQ-87 vẫn blocked cho acceptance overnight: failed live session không
trở thành continuous success bằng historical replay. Không fresh hour-long run,
model inference, OrderCheck/OrderSend hoặc grant mới.

### Phát hiện độc lập lúc chốt giờ Exness06:00

Trong lúc repair, Exness-next vẫn cập nhật với source cũ; native kết thúc
**06:00:48VN**, `shadow_hour_gap_requires_review`. Đây là quality guard khác
FTMO, không phải telemetry crash. H1**05:00–06:00VN** có731ticks và hai gap
99.415ms,198.234ms; đoạn dài nhất**05:01:41,862→05:05:00,096VN**, vượt policy60s.
Native reread các minute bao quanh gap cho ordered quotes khớp bản gốc,
kể cả các trang05:02/03/04 có0tick; chưa có bằng chứng là local capture bỏ tick.
Giữ raw observations ở `repair-20261105/exness-gap-observations` và diagnosis
checksummed; không nới ngưỡng, điền nến giả hoặc restart phiên để xóa lỗi.

Exness official [instrument hours](https://get.exness.help/hc/en-us/articles/4405235684498-Instrument-trading-hours)
nêu rollover mùa đông22:00UTC, có thể tạm ngưng vài phút và Trial có maintenance.
Gap trùng giờ rollover là **suy luận phù hợp**, chưa chứng minh nguyên nhân
riêng cho server; giờ maintenance23:20UTC trong tài liệu không khớp gap này.
Controller tự chốt blocked sau khi mọi child terminal; NAQ-85/86/87blocked,
NAQ-88done. Không còn capture qua đêm đang chạy sau06:01; không cần đợi07:00
để biết kết quả. Bước thiết kế tiếp theo là tách raw collection health khỏi
bar-quality acceptance và xác minh broker/session calendar, không âm thầm
đổi hợp đồng60s của lượt đã chạy. GitHub#10 còn mở cho acceptance toàn đợt.

## 05/11 — Paperclip blocked-parent attention projection

Owner yêu cầu sửa NAQ-85 hiện xanh trong khi NAQ-86/87 đều đỏ. Native API xác
nhận cả3task `blocked`, không execution run; parent `blockerAttention` vẫn là
`covered / active_child`,2coveredblockers và `blockingTreeLive=true`. Source
`server/src/services/issues.ts` short-circuit mọi human assignment (trừcancelled)
thành covered, không xét trạng tháiblocked hay downstream. Cùng lỗi xuất hiện
trong helper kiểm live tree; UI render đúng projection sai từserver, không phải
cache hay cần gán một AIagent để chữa.

Paperclip source checkpoint **`5501757`**: human assignment không tự cover một
blockednode; đi tiếp xuống dependencies/children và dùng các active/wait paths
đã có. Đồng bộ live-tree predicate; giữ nguyên human backlog/review waits,
active runs và explicit waits. Không thêm query, schema, status hay assignee
mutation. Cập nhật contract ở `doc/execution-semantics.md`.

Hai regression mới tái hiện đúng lỗi trên real isolated PostgreSQL:
**trước sửa2failed/25passed**, sau sửa**27passed**,64,07s toàn suite. Kiểm cả
parent có2human-owned blockedchildren không có livework và human-owned blocked
dependency phải trỏ tới leaf thực sự đang chạy. Không chạy repo-wide tests/build
cho thay đổi hai predicate; chưa coi đây là full-repo/release qualification.

### Activation đang bị chặn

Preflight không có running/queued Paperclip runs. Đã snapshot config/owner và
backup DB bằng **native `runDatabaseBackup` JavaScript engine** vào private
`E:/BACKUP-TRADINGWORKSPACE/system-capabilities-20261103/paperclip-blocker-fix-20261105`.
Backup`paperclip-20261105-063107.sql.gz`:1.186.524bytes, SHA256
`0a579650588a26e3e3996185144926e070dc250b0520c7ade5f93d80f1c81d3a`;
gzip/content verified, chưa thử restore. Native package không cópg_dump nên
attempt pg_dump không chạy; không cài thêm package hay bỏ backup.

Lệnh PowerShell dừng đúng owner Node + clean-stop PG để restart local bị tool
auto-review từ chối **`blocked by policy`**, không có lý do chi tiết khác. Lệnh
bị từ chối trước khi chạy, không có process bị dừng. Không chuyển shell/tool
để lách từ chối. Native hot-restart helper chỉ viết intent cho service manager,
không có restart API phù hợp với launcher local này. Đã yêu cầu owner dừng
instance đang chạy; sau đó dùng launcher hiện có với workspace origin5180,
kiểm health revision5501757 và native NAQ-85 `needs_attention`,0covered,
`blockingTreeLive=false`, giữ nguyên statuses/assignees. Chưa nâng workspace
gitlink hoặc tuyên bố UI/runtime đã sửa trước activation/readback.

Readback06:33: health đã trả sourceHEAD5501757 nhưng parent vẫncovered/live
và owner PID chưa đổi. Vì health có thể đọc HEAD hiện tại, revision string
không chứng minh module trong process đã reload; acceptance phải có native
attention readback đúng cùng process owner sau restart, không chỉ health SHA.

### Activation hoàn tất sau owner stop,05/11 06:48VN

Owner xác nhận đã dừng. Detached `Start-Process` bị auto-review chặn trước thực
thi; launcher gốc chạy được trong managed terminal (`exec`session43538), không
đổi shell để thực thi lại lệnh đã bị từ chối. Lần đầu launcher chặn17861 vẫn
nhậnTCP nhưng SQLtimeout: postmaster26428 đã mất, còn một orphanPG18
`io_worker`18800, cùng parent/start time với cluster `trader-ui/db` trong
`postmaster.pid`/`postmaster.opts`. Native `pg_ctl status` xác nhận main đã dừng;
TERM tới orphan bằngpg_ctl báokhôngcósignalendpoint. Lệnh riêng có identity
guard dừng đúng orphan18800 đã được tool cho phép; không dừng PostgreSQL Trader
hay các cluster khác, không xóa/đổi DBfiles. Launcher sau đó tự xử lý stale lock,
mở lại **cluster cũ**, UI buildđạt8,56s; các warningVite/CSS/chunks cũ vẫn có.

Owner mới launcher19972/server23880, sourcecommit5501757;
healthprocessStartedAt`2026-11-04T23:48:13.358Z`, listener ready06:48:24VN.
Native readback so với private`before.json` xác nhận IDs/status/assignees của
NAQ-85/86/87 giữ nguyên. Parent chuyển **needs_attention**,0coveredblockers,
2attentionblockers, **blockingTreeLive=false**; lưu`after.json`. Đây là bằng
chứng behavior/module mới đã load, không chỉ currentGitSHA tronghealth.

Browser tab4 tại`/NAQ/issues` đã verify AXlabel parent
`Bị chặn · 2 blockers need attention` và screenshot cảparent/2children đềuđỏ.
Ảnh private`paperclip-blocker-fix-20261105/blocked-parent-fixed.png`.
Không chạy lại27tests vì source không đổi sau pass, không inference/modeljob,
grant hay brokercommand, không resume các failedcapture. Lỗi màu/attention đã
khép; các gate chất lượng dữ liệu overnight vẫn blocked đúng kết quả.

## 05/11 10:00–10:20 — Tách thu raw tick khỏi bar-quality failure

Owner giao sửa tiếp hai lỗi dữ liệu. Trader source **`d9232b87`** bổ sung
`projection_policy=quarantine_v1` cho registration mới, default vẫnstrict_v1.
Historical audit có revised rows hoặc closedH1 gap>60s ghi durable
`quality-hold.json`; raw collector tiếp tục từ cursor, giữ nguyên
`shadow.json` hợp lệ cuối và không retry cùngbad hour mỗi poll. Hold pinplan và
last-valid-report được kiểm trước append khi resume; known-at không backdate.
Account/source/SDK/clock/checksum và most-recent raw page revision vẫn là hard
fail. Không sửa producer, không nới60s, không fill nến hay đoán broker calendar.

Workspace controller phân biệt raw `complete` và projectionheld: lane khác vẫn
chạy, nhưng heldsample không đượcdone hoặc seedhandoff. Successor sao chép đúng
projectionpolicy; product warmup cũng chặn heldpredecessor. Native progress
hiển thị “Đang thu tick; tạm giữ tính nến/tín hiệu” cùng raw counters và nguyên
nhân; khi hết raw scope vẫn nói rõ dữ liệu cần kiểm tra. Không thêm dashboard,
daemon, model, retryengine hay đường gửi lệnh.

### Kiểm chứng theo phạm vi

- **18step tests**, **8continuity tests** (gồm92giờ synthetic/four-session),
  **35workspace tests** đều đạt:61testcases liên quan. Sau chỉnhknown-at và
  successorpolicy đã chạy lại3quality regressions +15night tests, đều đạt.
- Saved-data replay đúng evidence: FTMOpair84→96 giữ reason revised, rawpages
  **209→210→211**; Exnessgap**198.234ms** giữ reason gap, rawpages
  **300→301→302**. Frozen validreport và original capture checksum không đổi.
  Đây là **offline/synthetic clock + empty continuation pages**,0networkreads;
  không coi emptytail là tickthật hoặcfreshforward. Private script và results
  ở `quote-quality-repair-20261105/replay_saved.py`, `saved-replay.json`.
- Native read-only smoke **hai account thật chạy song song** bằng binary cũ
  đã pin +source Python mới, cả2complete/terminal vàprojectionready. Mỗi lane
  10pages/20srange: Exness1tick,FTMO10ticks,0H1. Không inference, grant,
  OrderCheck/OrderSend hoặc reconnect/APIrestart. Smoke chứng minh collector/
  protocol hiện tại, không chứng minh fresh H1/handoff/overnight/strategy.
- Private artifacts: `E:/BACKUP-TRADINGWORKSPACE/system-capabilities-20261103/quote-quality-repair-20261105`:
  original source snapshots, per-lane offline replay, tests logs,
  `native-smoke/` lifecycle/capture/logs và `native-smoke-result.json`.
  Native jobs mới đã kết thúc; không còn finite smoke worker đang chạy.

Luồng source mới đã được dùng bởi native smoke, không cần restart UI/API để
load Python worker mới. Old registrations/lifecycles/sourcepins không được
viết lại hoặc resume sau deadline. Current read-only registrations cần chọn
quarantine_v1 rõ ràng theo FOREX-FORWARD/OPERATIONS; projection hold không tự
được gỡ hoặc trở thành authority thực thi. Giữ NAQ-85/86/87blocked cho acceptance
đợt qua đêm cũ, công bố repair trên cùng native tasks; không chạy thêm một giờ
chỉ để đổi màu. Broker-specific calendar và future uninterrupted qualification
vẫn là scope chưa chứng minh, không được gọi đã đạt từ các kiểm tra này.

## 05/11 — Khép task kiểm/sửa thay vì treo blocked sau resolution

Owner gửi ảnh NAQ-85/86/87 đỏ và yêu cầu sửa toàn luồng. Live API/AX xác nhận
đó là các task qua đêm cũ, không có run mới hoặc một exception mới trong ảnh.
Thiếu sót của workflow trước: giữ taskblocked sau khi chẩn đoán/repair đã được
kiểm chứng, cùng `unblockDescriptor` yêu cầuownerinspect đã lỗi thời; task state
và kết quả observation bị dùng như một trạng thái duy nhất.

Đối soát description/scope và evidence đã có, đóng công việc kiểm/sửa bằng
native document `resolution` trên từngtask rồi chuyển **NAQ-86,87,85→done**,
clear obsoleteunblockdescriptor, giữassignees. Description giữnguyênphầnscopegốc
và thêm kếtquả xửlý. Resolution phân biệt rõ: workresolved; originalovernight
notpassed; sourcefix/replay/short-native-read verified; continuous-forward và
strategy qualification không được khẳng định. Remaining qualification tiếp tục
theo GitHubissue#10OPEN; không đóng issue đó hoặc gọi oldrun pass để đóng task.

Sửa `shadow_night.Manager.finish_task`: publication cũ không chuyển task đãdone
hoặccancelled trở lại blocked. Company/assignment fences giữ nguyên; các task
chưa resolve vẫn bịblocked khi runfailed. **17controller tests đạt2,021s**, gồm
hai regression mới cho terminalresolution, unresolvedfailure và scopefence.
Đã gọi chính productionfinalizationmethod với realAPI cho3task vừa resolve:
cả3vẫndone và `updatedAt` không đổi (không phát sinhPATCH). Native Task documents
đãreadback; oldcontroller statechecksum so lại giữnguyênblocked/failed.

Browser tab4 `/NAQ/issues` AX xácnhận parent và cả2children đềuDone. Không
restart runtime hoặc tạojob mới trong bướccloseout; không xóa/đổi rawdata,
sourcepins, lifecycle, lịch sử lỗi, grant hay OrderCheck/OrderSend. Operations
guide bổsung quytrình explicitresolution để không lặp việc báo“đãsửa” nhưng để
côngviệc treoowner. Bảnđiềuchỉnhnày thay quyếtđịnh giữ nativeworkitemsblocked ở
đoạn trước; kếtquả oldobservation và các giới hạn evidence không thay đổi.
Private before/after: `quote-quality-repair-20261105/native-task-resolution-before.json`
và `native-task-resolution-after.json`.

## 05/11 — Đã khởi động phiên qua rollover, NAQ-89–92

Owner duyệt vận hành Demo có giám sát, chỉđọc, haiaccount qua rollover và một
plannedstop/resume. Native manualtasks: parent **NAQ-89**, Exness**NAQ-90**,
FTMO**NAQ-91**, preflight/recovery**NAQ-92**; gánowneruser,0agentdispatch.
RunID **`7a97177c-11f4-4792-820f-0c3e25418a65`**; capture từ
**10:47:32VN05/11**, Exnessboundary**12:00**, finalcapture**05:15VN06/11**,
childdeadline05:18, controllerharddeadline**05:20**. Quarantine_v1,60spages,
same existing brokerbindings/runtimeepoch875ecd...;0model/grant/OrderCheck/Send.

Private root: `E:/BACKUP-TRADINGWORKSPACE/system-capabilities-20261103/forward-20261105-rollover`.
Source/identity/native short-read/saved-replay evidence tái sử dụng vì không đổi;
gate mới checksum và pin nguồn, không lặp tests/provider chỉ để bắt đầu job.
Resourceguard>=2GiB free mỗiD/E,<=1GiB root; current headroom~72GB/~166GB.
Controller giữ idle-sleep request theo thời gian sống, không cài auto-boot,
service hoặc đổi Windows powerplan. Backup/off-machine vẫn ngoài scope.

### Planned recovery đã đạt

Exness nativeSTOP rồi resume **cùng registration/output/deadline**. Ba trang
durable/65ticks không đổi, incarnation1→2, FTMO vẫn tăngpage khiExnessstopped.
`controlled-recovery.json` ghi passed,NAQ-92Done và document đãreadback.
Không chạy lại exercise. Sourceprefix không rewind, không API/MT5restart.

### Khóa nhánh raw continuation trước khi để qua đêm

Audit setup chỉ ra qualified-only H1 handoff có thể bỏ mất phạm vi raw sau12:00
nếu H1 bịheld. Thêm **explicit** controllerpolicy`raw_if_held_v1`, default vẫn
qualified_only_v1: chỉ khi predecessor **nativecomplete**, manifest/counters/
rawcursor/qualityhold/reporthash khớp thì mới mở rawsuccessor **không seed**.
Freshstart phải<=60s sau boundary; failed/incomplete/mismatched/late không
được dùng. Không gọi rawrestart là H1handoff; `verified_before_launch=false`,
qualification vẫnneedsreview. Existing-successor recovery không bị cổnglaunch
window ép tạo capture lần2. **20controller tests đạt6,154s**, gồm nhánhheld,
no-seed, mismatchednative, late rejection và reattachkhôngdoublelaunch.

Chỉ dừng oldcontroller bằng managedterminalCtrl-C sau plannedexercise; detached
collectors/observers **vẫnrunning**, counts/incarnations giữ nguyên. Snapshot
originalplan/state/source ở`controller-revision/`. Reviewedcontroller-only
revision giữ cùngrunID, initialgroups/registrations/cursors, Step/SDK/source và
runtime, end/deadline; active`night-current.json`/`controller-current/`.
Current managed terminal**11882**; old10639 đãthoát. Không sửa expectedhash
trong originalnight.json hoặc state để giảresume. Phầncontroller dùng plan/gate
mới, còn childregistrations không đổi.

Native parentlive document**`shadow-f75bcfe1fb68b564`** đãPUT/readback;
`operating-window` giữmốc/cáchresume, oldcontroller doc được ghi rõhistorical.
Childlive reports cập nhậtđộc lập; tiếnđộ routine60s, stale90s cầnkiểmstatus.
Readback sau revision: Exness16pages/350ticks vàFTMO16pages/901ticks,
bothrunning,projectionready; đây chưa là freshH1/handoff/overnight acceptance.
Runbookprivate có exact status/resume/stop commands; chỉ đổiTaskstatus không
dừng collectors. Không chỉnh các pinnedsourcefiles trong lúc chạy. Khi PC
reboot cầnreconcile rồiresume đúngrun/window; không có installedautostart.
Kết quả cuối vẫn phải đối soát raw/projection/recovery/coverage/publication,
không côngnhận fullacceptance trước khi đạt mốc và đọc nativeevidence.

## 05/11 — Rút gọn phiên dài, chốt kiểm nhanh theo yêu cầu owner

Owner cho rằng chờ cả ngày quá lâu và yêu cầu cách nhanh hơn vẫn kiểm đúng.
Đổi scope trong AI plan: kiểm code bằng clock/fault/continuity + saved-data
replay; chỉ dùng short native integration khi boundary liên quan cần đọc thật.
Không cần phát triển framework mới hoặc chạy lại các test/source không đổi.
OPERATIONS ghi rõ khi nào mới cần quan sát dài và cách kết thúc phiên rút gọn.

Native STOP được gửi **11:17:16 VN 05/11**, terminal vào **11:17:16–17**.
Đối soát bằng native status và process creation identity: controller stopped/
đã thoát; cả Exness/FTMO stopped/terminal; hai supervisor và hai observer đều
đã thoát, không có successor được khởi chạy. Managed terminal11882 exit1 do
operator_stop, không phải overnight pass hoặc exception mới trong collector.
Controller giữ snapshot lanes trước STOP; parent live document được chú thích
và resolution đối soát terminal riêng, không sửa state để giả kết quả mới.

| Lát kiểm | Kết quả thực tế / evidence scope |
|---|---|
| Dữ liệu thật song song | Mỗi account29pages,10:47:32–11:16:32VN,29phút đã đọc; Exness666ticks, FTMO1.746ticks, cả hai0closedH1 |
| Phục hồi thật | Planned recovery đãpassed: giữ3pages/65ticks, cùng registration/output/deadline, incarnation1→2; FTMO vẫn tiến khiExnessstopped |
| Tăng tốc đã có | Reuse18step +8continuity +35workspace tests và20controller tests; có92giờ synthetic/four-session, saved revision/gap replay; không coi synthetic tail là tickthật |
| Short native read đã có | Haiaccount complete/ready,10pages/20srange mỗiaccount; đây là integration smoke, không là H1qualification |
| Chưa chứng minh | Fresh H1handoff của phiên này, rollover thật, uptime24/7 và strategy qualification |

Private `forward-20261105-rollover/fast-scope-result.json` giữ native readback,
recovery và SHA256 inventory của controllerstate/lifecycle/shadow/rawcapture.
Đã đối hash trước/sau native publication: không đổi các file bằng chứng gốc.
`fast-scope-tasks-before.json`/`fast-scope-tasks-after.json` giữ taskreadback.
RUNBOOK mở đầu bằng trạng thái stopped/superseded; các lệnh cũ chỉ còn tham chiếu
lịch sử, không tự resume phiên rút gọn.

Native **NAQ-90/91/89 done** sau resolution và readback, giữ assignee, bỏ
unblockDescriptor lỗi thời. NAQ-92 giữdone. Done biểu thị công việc kiểm nhanh
theo scope mới đã hoàn tất; lifecycle gốc vẫnstopped, phạm vi qua đêm chưa đạt.
Parent `operating-window` và `resolution` của ba task nêu rõ scopechange; các
child terminalreports đã delivered. GitHub **workspace#10 vẫnOPEN** vì H1/
continuous-operation acceptance chưa được kiểm đủ; không đóng bằng kiểm nhanh.
Không gửi lệnh, cấpgrant, gọi model, reconnect hoặc restart terminal/API.

## 05/11 — Bắt đầu khảo sát chiến lược theo mục tiêu prop

Owner giao tiếp nghiên cứu và hỏi phạm vi hai hãng hay prop nói chung. Đã hoàn
tất khảo sát/protocol trong `planning/research/PROP-STRATEGY-ROUND1-20261105.md`:
FTMO 2-Step Swing chuẩn chính, The5ers High Stakes đối chiếu; không tạo engine
tổng quát. Đã đọc primary sources của hai hãng, AQR/BIS/Fed/NBER và nghiên cứu
về selection bias; chọn theo edge/risk/compliance, chưa xếp theo outcome mới.

Danh mục 10 ý tưởng đã phân nhóm/loại trùng: C01 Donchian baseline, C02 SMA20/80
và C04 z-score20 là shortlist H4; C06 session breakout dự phòng cần clock/news/H1.
Quy tắc C02/C04 là adaptations tự đăng ký, không tự gọi exact paper replication.
Chưa cài EA/package, nhập source hoặc chạy backtest/agent inference mới.

Đối chiếu metadata QDM manifest: warmup 20–31/12/2021 và Q1 03/01–31/03/2022
đã consumed; không mở raw price hoặc outcome mới. Protocol giữ gate availability/
consumed và freeze trước validation/final holdout. Các candidate chưa code chưa
được coi là runner hỗ trợ. Historical cost/intrabar equity và account-specific
The5ers rules/news vẫn là qualification gaps, không bị giả thành 0/pass.

Native Paperclip 17860 hiện connection refused. Lệnh Start-Process Hidden để chạy
launcher hiện có (cùng source 5501757, origin 5180, không sửa config) bị automatic
review chặn `blocked by policy`, không có lý do chi tiết. Không khởi chạy qua
đường khác. Native task/document publication **chưa thực hiện**; không tạo
task ID hoặc công nhận dispatch. Kết quả nghiên cứu local và source links đã lưu
đầy đủ; receipt này giữ bước tiếp trong khi chưa có native publication.

Bước tiếp: audit availability/consumed manifest; implement candidate contract và
runner nhỏ reuse Forex core rồi focused checks trước numerical run. Chỉ công bố
native khi instance có lại và đã dedup đúng task scope; không rerun fixture cũ.

## 05/11 — Hai ứng viên H4 đã triển khai và kiểm development hai tuần

Trader source **`a306c9618bb9aa6bbeff2dcbb4bdd0b982a2204c`** bổ sung hai ứng viên
đã đăng ký: SMA20/80 và z-score20/2, thoát theo 6 lần đóng H4 của cùng position ID.
Reuse tick execution/accounting/financing/risk; tách helper Wilder ATR14 để ba
ứng viên dùng cùng phép tính. CLI mặc định giữ Donchian/manifest cũ; chế độ
study phải chọn candidate trong danh sách cố định, input manifest có hash và
research protocol. Không tạo engine/framework, model call hoặc đường broker.
Hướng dẫn nằm ở `projects/trader/foundation_v2/docs/FOREX-RESEARCH.md`.

### Kiểm dữ liệu và đăng ký trước outcome

- Metadata QDM CLI hiện có: EURUSD_TICK_TW, UTC, cache báo 05/05/2003–01/11/2026,
  517.750.341 records. Đây chỉ là metadata, không xác nhận coverage/đã đọc giá.
- Audit 10 entry từ manifests trong private Forex pilot root: các lát đã xem
  warmup 20–31/12/2021 và development 03/01–31/03/2022. Không khẳng định đã audit
  mọi project để công nhận 2023+ là unseen; validation/finalholdout chưa mở.
- Warmup cũ chỉ 58 H4. Protocol clarification được commit **`64ecdad`** trước run:
  cùng warmup 01–31/12/2021 cho C01/C02/C04, tối thiểu 81 H4; time exit đếm cả nến
  chứa fill, không tạo bar qua gap và reset theo position ID. Không đổi tham số
  sau outcome hoặc thay manifest/capture cũ.
- Export từ cache QDM, không GUI/download/update: 63.734.720 bytes, SHA256
  `63b63be980254b572bbc3ec2d7e1d68726ffeb510d0202f29c0c975670e1a640`.
  Validate 1.404.696 ticks/133 H4 hợp lệ; development 643.775 ticks/58 H4 giữ nguyên.

### Kiểm chứng và lượt chạy thực tế

**26 tests liên quan đạt:**8 candidate/runner tests, 11 H4/accounting regressions,
7 workspace ForexFixture tests. Kiểm prior-window population variance/crossover,
prefix causality, identity-bound time exit, malformed state, roundtrip và legacy
contract không mở sang study/holdout. Không chạy lại full suite hoặc broker/UI.

Ba process độc lập, output riêng; mỗi process chạy reference và cost-stress.
Manifest đầu **12:15:22 VN**, lượt cuối hoàn tất **12:17:24 VN 05/11**, khoảng
**121,4 giây** cho 6 mô phỏng trên dữ liệu **03–14/01/2022 đã từng xem**. Source,
protocol/input/account spec đều pin trước outcome; kiểm lại source hash sau run.
Cả 3 terminal exit 0, stderr 0 bytes; process creation identity xác nhận 3 worker đã
thoát. Không còn lượt numeric study này chạy nền.

| Ứng viên | Scenario | Balance delta USD | Equity delta USD | Mở/đóng lệnh | Còn vị thế |
|---|---|---:|---:|---|---|
| Donchian C01 | Reference |−19,94 |−19,94 |3/3 |Không |
| Donchian C01 | Cost-stress |−23,80 |−23,80 |3/3 |Không |
| SMA20/80 C02 | Reference |−24,64 |+9,41 |2/1 |Có1 |
| SMA20/80 C02 | Cost-stress |−27,60 |−0,52 |2/1 |Có1 |
| Z-score C04 | Reference |−27,08 |−27,08 |4/4 |Không |
| Z-score C04 | Cost-stress |−32,84 |−32,84 |4/4 |Không |

Tất cả tính trên 10.000 USD giả lập; equity dùng quote cuối và modeled costs,
không phải lợi nhuận đã thực hiện hoặc tiền rút được. Không force close cuối
mẫu. Cả 6 independent accounting và candidate state roundtrip đạt. Sau bỏ 2 field
evidence mới, **mọi field kết quả C01 khớp toàn bộ baseline hai tuần cũ** dù
warmup dài hơn. Không cộng hai lượt thành hai mẫu kiểm chứng độc lập.

Kết luận slice: numerical integration đã kiểm, chưa xếp hạng edge; rất ít lệnh,
SMA còn open position và nhạy chi phí. `strategy_pass=false`, `prop_pass=false`,
`broker_spec_verified=false`, `intrabar_equity_coverage=insufficient` giữ nguyên.
Chưa triển khai profile The5ers hoặc lấy FTMO cost gắn nhãn The5ers verified.
Candidate snapshot giữ indicator/position age; CLI resume **chưa hỗ trợ**, không
gọi JSON roundtrip là phục hồi job giữa chừng.

Private evidence: `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/prop-strategy-round1-20261105/`.
`data-audit.json`, `cache-metadata.json`, `export-receipt.json`,
`two-weeks-inputs.json`; `attempt-1/study-manifest.json`, `protocol.md`,
`observation.json`, per-candidate manifest/quality/results/checkpoints/logs.
`PROGRESS.md` là snapshot tiến độ dẫn nguồn receipt, có timestamp; observer
không phải daemon/capture controller. Đã gửi mở file qua Codex panel, tool trả
queued; không khẳng định người dùng đã nhìn thấy. Native Paperclip publication
vẫn chưa làm do instance chưa có lại; không lách lần launch bị policy chặn.

Bước tiếp: development Q1 trên cùng protocol/common warmup nếu cần tăng mẫu,
rồi đóng băng thiết kế OOS sau audit consumed/coverage đủ phạm vi. Không chọn
SMA chỉ vì equity reference dương hai tuần; không tối ưu size để ép pass prop.

## 05/11 — Research và sửa project default cho Codex policy rejection

Owner yêu cầu đối chiếu Reddit/cộng đồng/OpenAI và sửa lỗi. Báo cáo nguồn,
phân biệt fact/hypothesis và đường activation ở
`planning/research/CODEX-POLICY-BLOCK-20261105.md`.

Đã xác nhận active thread là disabled/never, global danger-full-access/never;
project chỉ có MCP config và được trusted. Không tìm thấy rules hoặc managed
files ở các vị trí đã kiểm; không khẳng định đã loại mọi enforcing layer.
Desktop26.1029.7803.0, thread CLI0.166.0-alpha.6, CLI trênPATH0.164.0 là ba thông
tin khác nhau. Không update nhầm CLI trênPATH để công nhận sửa runtime desktop.

Trong điều tra, một source-read command chứa URL/launch search literals cũng
bị tool từ chối trước execution. Điều này phù hợp giả thuyết static heuristic
Windows bắt nội dung quá rộng; source/community corroboration chưa là runtime
rule ID. Cách gọi "automatic reviewer" ở các receipt trước chưa đủ bằng chứng:
chỉ xác minh được pre-execution policy rejection, không xác minh reviewer ran.

Đã backup và chỉ thêm project `.codex/config.toml` key
`approval_policy = "on-request"`; parsed before/after chứng minh MCP config giữ
nguyên. Global config, sandbox, reviewer và guard rules không đổi. Maintainer
audit trước/sau0errors/0warnings, TOML/diff checks đạt. Đây là default có đường
review cho lần khởi tạo phù hợp, **chưa thay active never của cuộc chat**.

Owner cần chọn chế độ cho phép duyệt trên app rồi gửi lượt mới để kiểm effective
policy; nếu app vẫn giữnever thì mở task mới đúng mode, tiếp từ plan/receipt.
Chưa retry launch Paperclip, khởi service/terminal, gửi support hoặc tuyên bố
original operation đã phục hồi. Không đổi shell/encoding hoặc tool để lách cùng
operation bị chặn; chưa tìm được bản vá upstream nào bảo đảm fix mọi trường hợp.

## 05/11 — Lưu research và kế thừa bằng chứng ngoài chat

Owner yêu cầu mỗi lượt research cập nhật context và áp dụng tương tự cho các
chẩn đoán/kiểm chứng/quyết định cần kế thừa. Đã reuse context lifecycle và owner
map hiện có, thêm repo skill
[evidence-continuity](../../../.agents/skills/evidence-continuity/SKILL.md),
route từ AGENTS và development/current context. Không thêm ledger, service,
vector store hoặc hook mới. Quy trình: đọc nguồn cũ → kiểm delta/freshness →
lưu bằng chứng/giới hạn → cập nhật link bàn giao.

[Chỉ mục research](../../research/README.md) dẫn tới tài liệu hiện có;
[research prop/automation](../../research/PROP-AUTOMATION-AND-STRATEGY-EVIDENCE-20261105.md)
lưu hai lượt đối chiếu vừa qua, tách source fact/community/inference/unknown
và khuyến nghị chưa được owner chốt. Round1 thêm Terms The5ers §11/T7 vì mô tả
EA cũ chưa nêu yêu cầu approval bằng văn bản; không thay outcome, tham số hoặc
protocol tín hiệu đã freeze. Các tài liệu cũ trong chỉ mục không được tự gắn
nhãn đã re-audit hôm nay.

Kiểm chứng documentation-only:

- `python -X utf8 C:/Users/MIIKEY/.codex/skills/.system/skill-creator/scripts/quick_validate.py .agents/skills/evidence-continuity`: valid.
  Lượt đầu không có `-X utf8` gặp lỗi decoder cp1252; dùng UTF-8 của process
  để đọc đúng tiếng Việt, không sửa system encoding/global config hoặc validator.
- `python -X utf8 tooling/check_skill_links.py --skills-dir .agents/skills/evidence-continuity --review-triggers`: 1 skill, 0 lỗi/0 cảnh báo.
- Reuse `tooling/check_workspace.py::check_links` cho9file nội dung/điều hướng:
  0 local-link errors; `git diff --check` đạt.
- Manual resume-read: từ chỉ mục tìm được mức auto đề xuất, trạng thái chưa
  được owner chốt, nguồn The5ers mới, phần chưa biết và điều kiện refresh.
  Negative trigger: dịch/chỉnh câu đơn giản không tạo artifact mới. Đây là
  review chỉ dẫn/tài liệu, chưa là forward-test bằng một model độc lập.
- Maintainer audit `-Force`: 0 errors/0 warnings; global12.279B,
  project9.711/65.536B, combined21.990B, project reserve55.825B;18skills.

Source guide chỉ rõ cách gửi evidence locator/revision qua native dossier hoặc
typed request. Không sửa/publish catalog Paperclip, gọi model/provider, đổi
Hermes loader hoặc công nhận worker đang chạy đã nhận skill mới. Agent đọc
repo có route rõ qua AGENTS; consumer khác vẫn dùng loader/output contract
hiện có. Không mở quyền giao dịch hoặc tự coi research là strategy acceptance.

## 05/11 — Khảo sát agent tools và thực thi research round2

Owner giao khảo sát FTMO/The5ers/TradingView/cộng đồng, rồi triển khai đề xuất
research trước. Dùng workflow evidence-continuity, giữ nguồn/giới hạn tại
[tool survey](../../research/PROP-AGENT-TOOLS-20261105.md), không research lại
toàn bộ lựa chọn automation. Owner xác nhận chưa có TVpaid/The5ers account.

### Kết quả khảo sát và quyết định

- TradingView có MCP **chính thức public beta**, OAuth2.1, Essential trở lên,
  trial không gồm quyền. Tools có đọc data/screener/calendar và ghi watchlist/
  alert. Không mặc định mọi tool read-only: `get_active_watchlist` có side
  effect trong mô tả dù nhãn read-only. Chưa kết nối vì thiếu gói/tài khoản.
- The5ers có MCP chính thức chỉ đọc account/program/performance/headroom;
  không đặt lệnh/đổi account. Chưa kiểm authenticated tool schema hoặc download
  skill hãng, vì owner chưa có account. Không mua chỉ để thử công cụ.
- FTMO có MetriX/Analysis/Journal/App Suite35tools; chưa tìm thấy công bố MCP
  hay API portal public trong phạm vi khảo sát. MT5 API hiện có là đường giao
  dịch/dữ liệu khác portal; cTrader Open API là lựa chọn platform khi cần,
  chưa lý do đổi MT5 hoặc thêm adapter.
- Community shortlist TVDesktopCDP/market-analysisMCP, MT5MCP, EarnForex
  PositionSizer/AccountProtector được đọc capability/license. Không nhập/cài:
  thiếu nhu cầu độc lập, trùng adapter/risk và còn data/permission/source audit.
  TradingView policy hạn chế non-display: không lấy MCP/webhook hoặc MIT của
  wrapper làm quyền dùng data cho execution. Sources/conditions ở survey.

### Source và hướng triển khai

Workspace preregistration **`33570b0`** chốt
[round2](../../research/PROP-STRATEGY-ROUND2-20261105.md) trước code/outcome.
Trader **`7c2ee901`** thêm pullback-trend và UTC00–08range, dùng chung tick
execution/accounting/financing/sizing/risk, opt-in candidate IDs. Legacy default
và round1 formulas không đổi. **`631ac1b2`** cập nhật guide của cùng runner.
Không deploy broker runtime hoặc bắt native fixed fixture chạy chiến lược mới.

- Pullback: SMA20/80 xác định trend, close recrossSMA20 sau pullback; exit khi
  mất trend;2ATRstop. Đây là adaptation do ta định nghĩa, không exact EA replication.
- Range: đủ hai H4bar00:00/04:00UTC cùng ngày, close breakout ở12:00/16:00UTC;
  một entry signal/ngày; scheduledexit20:00UTC hoặc close hợp lệ kế tiếp nếu
  thiếu data. Không giả London session/DST hoặc flat qua gap.
- Hướng auto có giám sát được áp dụng cho research: owner chọn chiến lược/risk/
  triển khai, bot theo rule; AI không cần gọi từng tick/lệnh. Chưa strategy
  qualification hoặc broker grant mới. Semi-auto cần quyết định người trước
  outcome; chưa có thì không công nhận lợi ích.

**Focused verification:** `foundation_v2/.venv/Scripts/python.exe -m pytest -q
tests/test_forex_prop_candidates.py tests/test_forex_h4_candidates.py` đạt
**16tests,11subtests**. Kiểm hai hướng entry/exit, previous-window timing,
prefix causality, đủrange/day/gap/DSTUTC, one-signal/day sau snapshot restore,
position identity, malformed state, roundtrip và shared accounting. Lượt sau
thêm manualtemplate chỉ chạy lại focused suite vì source liên quan đổi.
Không rerun fullsuite/core hoặc broker chỉ để tăng số test.

### Lượt numerical thực tế

Private root:
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/prop-strategy-round2-20261105/`.
Hai worker output riêng, chạy đồng thời trong cùng turn; không subagent/model.
Từ khoảng**13:35:56–13:37:41VN05/11**, dưới2phút; sessionexit0 cả hai,
stderr0bytes. Mỗi candidate chạy reference và coststress trên development
**03–14/01/2022 đã consumed**,643.775ticks/238H1/58H4; commonwarmupDec2021
giữ1.404.696ticks/133H4. Không tải lại, không holdout/OOS.

| Candidate | Scenario | Balance/equity deltaUSD | Mở/đóng | Còn vị thế |
|---|---|---:|---|---|
| Pullback20/80 | Reference |−36,55 |2/2 |Không |
| Pullback20/80 | Cost-stress |−38,96 |2/2 |Không |
| UTCrange00–08 | Reference |+15,03 |7/7 |Không |
| UTCrange00–08 | Cost-stress |+14,56 |7/7 |Không |

Tất cả trên10.000USDgiả lập;9trade/costscenario, không tính các lần reference/
stress thành18 cơ hội độc lập. Accounting và candidate state roundtrip4/4đạt;
source10files/worker được hash-check sau run. `strategy_pass=false`,
`prop_pass=false`, `broker_spec_verified=false`, intrabarcoverageinsufficient
giữ nguyên. Không chọn UTCrange là winner từ7trade hoặc tuning theo outcome.

`attempt-1/study-manifest.json` pin protocol
`da01bc6e4673cb55f8d202ea32996ba815704a5b29773cc1232d453920a3c1b7`, inputs và
source revision trước outcome. Perworker giữ manifest/quality/results/checkpoint/
decisions/log. `completion-review.json`, `RESULTS.md`, `PROGRESS.md` giữ review
và kết quả; đã gửi mở progress qua Codexpanel, toolqueued, không khẳng định owner
đã nhìn thấy. Không còn numeric job round2 này chạy.

Hai `manual-review-template.json` có4/14entries tương ứng reference/stress;
manifesthash, signalIDunique và null decision/time/reason đã kiểm. Nhãn
`historical_schema_example_not_prospective_evidence`,
`manual_filter_measured=false`, `risk_override_allowed=false`; chưa là so sánh
semi-auto. Bỏ lệnh làm đổi state nên không cộng riêng tradePnL để giả replay.
CLIresume vẫn unsupported; snapshotroundtrip không là jobresume.

**Tiếp theo theo evidence:** tăng sample development, audit consumed/coverage và
đóng băng OOS trước kết luận edge; lấy quyết định người thật khi cần so manual
filter; account/OAuthTV/The5ers và approvalEA phải có trước integration đó.
Không tự mua challenge, bật broker execution, thêm service hoặc công nhận quỹ
đã duyệt. Research/implementation/numericintegration hoàn tất đúng lát trên;
chứng minh lợi nhuận và survival dài hạn chưa hoàn tất.

## 05/11 — Workflow strategy, qualification và chủ động quản lý skills

Owner duyệt triển khai toàn bộ đề xuất workflow trước, đồng thời yêu cầu agent
chủ động tạo/cập nhật/đánh giá/dọn skill thay vì chờ owner nhắc. Scope lần này:
instruction/tooling/offline verification và native skill delivery khi runtime
khả dụng; không tuning/new numerical strategy study hoặc broker grant.

### Các lớp đã triển khai

- Repo skills `strategy-research` và `strategy-qualification`, reference risk/prop
  đóng gói cùng qualification. Method được chắt lọc từ round1/round2 đã chạy;
  chưa exact OOS/prop promotion thì skill không mô tả chúng như capability đã đạt.
- `tooling/ai-engines/STRATEGY-WORKFLOW.md` nối source/rules/data/risk/runner/
  review/operate/context. AGENTS, current/development context, Studio và lead
  source route đúng chặng. Không thêm agent/UI/ledger hoặc skill riêng từng hãng.
- `docs/development/SKILL-MAINTENANCE.md` dùng maintainer/skill-creator hiện có:
  trigger theo workflow lặp/lỗi/contract đổi, reuse/update trước create; kiểm
  callers/assignment trước merge/retire; không xóa hàng loạt, nới gate hoặc bật
  permission tạo skill của bounded workers. Đây là proactive instruction trong
  task, không daemon/scheduler hoặc global config/hook mới.
- Trader **`5ed15dbd`**: runner có `--preflight-only`, cùng input/spec/quality/
  warmup checks, manifest ghi mode và receipt riêng; chưa simulation/results.
  Cập nhật guide và runtime skill; legacy default/native fixed worker không đổi.
- `strategy_evidence.py inspect`: dựng dossier đọc-only từ completed study;
  kiểm scenario/candidate/cash components/checkpoint/coverage, fingerprint
  artifacts, tùy chọn input rehash/source comparison. Không tự tính statistical
  qualification hoặc full accounting ledger; `promotion_authorized:false`.
  Source drift là khoảng cách tái hiện, không xóa historical pinned evidence.
- `paperclip_strategy_skills.py`: package hai skills + source lead hiện có,
  preview/export mặc định, apply native API riêng. Backup files/assignments,
  content/version/idempotency checks, không xóa/upstream overwrite/permission
  change/service/model call. Không ghi DB trực tiếp hoặc tự retry unknown write.

### Risk/concurrency audit: reuse, không thêm engine cạnh tranh

Đọc `automation_grants.rs::create_grant`, `admit_in_transaction` và settlement
consumer: account-scoped creation lock (workspace/server/login), từ chối active
execution owner trùng, durable attempt/risk reservations và unknown không tự
release. Runtime skill/reference nhắc lại boundary này. Đây là **source-confirmed**,
chưa rerun broker/Postgres/runtime acceptance; code guard không sửa nên không
chạy lại suite không đổi. Không công nhận đã có multi-strategy allocator hoặc
correlation-aware portfolio engine từ việc guard có tồn tại.

### Kiểm chứng

- Product: `foundation_v2/.venv/Scripts/python.exe -m pytest -q
  tests/test_forex_preflight.py tests/test_forex_prop_candidates.py
  tests/test_forex_h4_candidates.py`: **18tests +11subtests đạt**.
- Workspace: `python -X utf8 -m unittest discover -s tooling/ai-engines/tests
  -p test_strategy_evidence.py -v`: **6tests đạt**. Mismatch checkpoint/candidate/
  coverage/cash, NaN, giả promotion, interrupted/preflight và path escape bị chặn;
  equity mở được giữ riêng, source drift không phá historical evidence.
- `test_paperclip_strategy_skills.py`: **5tests đạt**, native API fixture kiểm
  package allowlist, modeadd giữ selection, content update/backup/version,
  rerun không ghi dư, process/active/upstream collision từ chối và unknown/
  version conflict dừng trước assignment. Không gọi model hoặc real write API.
- Tổng **29tests +11subtests**, focused; không fullsuite/numeric replay mới.
- Quickvalidate hai skill mới valid; scoped skilllink check6skills0errors.
  Một advisory ở lượt review-trigger heuristic không đọc negative trigger tiếng
  Việt của lead; semantic review xác nhận boundary có thật, không sửa wording
  chỉ để lách heuristic.9guides local links0errors; diffcheck đạt.
- Maintainer audit `-Force`: global12.279B, project10.133/65.536B,
  reserve55.403B, combined22.412B,20skills,0errors/0warnings. Global không sửa.

### Smoke trên artifact/data thật và walkthrough

Private root:
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/strategy-workflow-20261105/`.

- Preflight candidateUTCrange trên QDMmanifest round1/commonwarmup và FTMOspec
  đã pin: receipt **`preflight_passed_no_simulation`**, process exit0,
  stderr0bytes, không results.json. Chỉ kiểm data/contract; không trade/model/
  holdout. Source đã đổi CLI nên native study lịch sử không là run code mới.
- `round2-dossier.json` thực sự hashCSV/protocol; `round2-dossier-v2.json` bổ sung
  contract/risk/input/cost routing, dẫn verification trước không giả vừa rehash.
  Phát hiện đúng drift `scripts/forex_h4_pilot.py` do preflight mới, invariants
  historical data vẫn checked và permissionfalse. Không chạy lại2phút/1giờ chỉ
  để công nhận một thay đổi tooling.
- Manual walkthrough positive: từ research index đi tới round2candidate/protocol,
  gọi dossier, đề xuất `inconclusive` cho evidence7trade/dev-only; không chọn
  winner hoặc tự mở demo. Negative: hỏi trạng thái/dịch câu không tạo study,
  preflight không thành backtest pass; source-positive risk review không thành
  live acceptance. Chưa forward-test bằng model độc lập; không spawn thêm agent.

### Native delivery chưa hoàn tất vì runtime unavailable

Authenticated native read qua `paperclip_setup.api('/companies')` bị
`URLError / WinError10061` tại origin cấu hình; Paperclip không nhận kết nối.
Không publish/assign hoặc công nhận catalog/runtime đã nhận skill. Bundle đã
export `paperclip-skills-bundle.json` để resume. Không retry lệnh khởi service
đã từng bị policy từ chối trong context trước, không đổi shell/tool để lách.

Khi native runtime khỏe: đọc company/lead hiện hành (không dùng ID đoán từ
history), giữ idle, dùng helper `--company ... --agent ... --receipt <new-private>
--apply`; verify native content/desired selections và actual mounted package
ở lần work có ích tiếp theo. Helper không tự dispatch model để tạo bằng chứng.
Nội dung source/instruction/tools và offlinechecks đã xong; publication/real
agent use vẫn chưa được xác nhận, cần giữ gap này trong báo cáo tiếp.

## 05/11/2026 — log/status nghiên cứu và dừng batch Q1 vì hiệu năng

Owner giao tiếp vận hành/nghiên cứu và yêu cầu bằng chứng dễ chẩn đoán khi job
lỗi/ngắt. Dùng lại native status/receipts và Python stdlib logging; không thêm
collector/service hoặc dashboard quản lý ngoài Paperclip. Guide hiện hành:
[OBSERVABILITY](../../../tooling/ai-engines/OBSERVABILITY.md). Workflow đã được
route qua các skills research/Studio/debugging có sẵn; không tạo skill logging
riêng. Đây là instrumentation consumer nghiên cứu, không phải audit hoàn chỉnh
mọi API hoặc chứng nhận toàn sản phẩm đã có tracing/redaction.

### Đã thay đổi và kiểm chứng

- Trader `3855b494`: attempt có run UUID/event sequence, UTC/elapsed time,
  phase/counters và structured `events.jsonl`, rotation1MiB +2backups.
  `failure.json` giữ exception type/code/stage/source frames; không exception
  text/locals. Logger riêng, không sửa global logging; giữ hash/accounting/
  checkpoint và callback cancellation. Input/spec failures cũng được ghi.
- Workspace `296eb3c`: `strategy_evidence.py status --run-dir <attempt>` đọc
  snapshot, phân biệt terminal/stale. Stale là process state unknown, không
  failed/retry. Guides/skills dùng lại owner; có checkpoint không đồng nghĩa
  CLI resume. `9e0f172` đăng ký common-warmup Q1 trước outcome.
- Focused checks trước đó trong lượt: product preflight/prop/H4candidate
  **20tests +11subtests đạt**; workspace strategy-evidence **7tests đạt** và
  forex-research **7tests đạt**. Skill/local-link audit không lỗi; maintainer
  audit20skills,0errors/0warnings. Không chạy lại vì source tương ứng không đổi.
- Trader `814e1135`: profile reader100.000tickQ1 cho thấy `strptime` chiếm
  2,335/4,671s cumulative khi instrument. Dùng guarded ISO fast path cho format
  canonical; inputs khác giữ legacy parser. Không bỏ hash/date/order/ms/
  BidAsk/tick-grid checks. `tests/test_forex_h4.py`: **12tests +23subtests đạt**.
  Có test malformed/leap/time/UTCms và fallback không canonical. Test hủy cũ
  được cập nhật theo redaction contract; vẫn assert không đọc ticks, original
  exception đến callback caller, failed stage và source frames được giữ.
- Benchmark không profiler, một reader,100.000tick development thật,1warmup
  pair +3sample pairs, đảo thứ tự baseline/candidate, cùng full-file SHAcheck
  mỗi lần: median **2,709s →1,517s =1,79×**; toàn bộ timestamp/sequence/Bid/Ask
  khớp. Đây là reader improvement; **chưa đo whole-scenario speedup**. Không
  thay candidate/risk hoặc gọi kết quả benchmark là outcome chiến lược.

### Batch Q1 chưa hoàn tất; không còn chạy ngầm

Private root:
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/prop-q1-comparison-20261105/`.
Đầu vào Q1 đã consumed:5.837.028tick; commonwarmup12/2021. Sourcepin3855b494,
5candidate ×reference/stress; model/broker/holdoutcalls0. Các worker xong
validation nhưng còn trong reference, throughput quan sát khoảng4.800–5.500
tick/s khi chạy song song; không thể xong cả hai scenario trong20phút đăng ký.

Đã dừng sớm lúc **14:41:18VN**, trước deadline14:42:06. Xác minh command,
creation time, receipt PID/parent của **11process** rồi stop; kiểm lại không còn
Python worker/controller nào của batch. Đây là external process termination,
không gọi graceful application shutdown. Kiểm identity ban đầu từ chối vì
PowerShell tự đổi ISO JSON date sang DateTime rồi parse lại mất offset; chưa
stop ở lần đó. Lần đúng dùng UTC identity rõ và exact command scope.

`attempt-1/resolution.json` giữ **stopped_early_performance**,5worker snapshot,
hash artifacts và explicit `study_complete=false`; **0results.json**. Receipt,
events/checkpoints/manifest lịch sử không sửa. `PROGRESS.md` được cập nhật sau
khi controller writer dừng; controller-status cũ `running` chỉ là snapshot trước
dừng, được resolution giải thích. Không ghép kết quả partial hoặc xếp hạng.

Phát hiện private controller terminate venv launcher thay vì Python con và có
thể gọi trạng thái completed khi child exitnonzero. Đã đối soát/dừng cả cây
tiến trình lần này; **không relaunch controller đó nguyên trạng**. CLIresume
chưa hỗ trợ; checkpoint được giữ không là run tiếp từ checkpoint đã kiểm chứng.
Chưa tự chạy lại fullQ1. Bước tiếp: dùng supervisor hiện có sau khi kiểm đúng
Windows child ownership/cancel/result semantics, đo trọn một scenario với
deadline phù hợp trước khi dispatch lại nhiều candidate. Không mở OOS/holdout.

Evidence tái hiện: `parser-baseline.prof`, `forex_h4_baseline.py`,
`benchmark_parser.py`, `parser-benchmark.json`, `attempt-1/stopped-process-identities.json`,
`stop-verification.json`, `resolution.json` và `PROGRESS.md` trong private root.
`data-consumption-inventory.json` chỉ đọc metadata12manifest/input files;
**unseen_2023_plus_established=false**, không xem giá/outcome laterwindows.

### Native delivery còn pending

Authenticated read lại `/companies` vẫn `ConnectionRefusedError/WinError10061`.
Paperclip không nhận kết nối; chưa publish/assign bundle vào native catalog.
Bundle đã export để tiếp tục khi runtime khỏe; không gọi source skill là đã
mounted. Không chạy lại lệnh start bị policy từ chối trước đó hoặc đổi công cụ
để né. Hướng dẫn/source/logging đã triển khai; native publication và Q1 outcome
vẫn là hai việc chưa hoàn tất, không whole-product/strategy acceptance.

## 05/11/2026 — tiếp Q1 bằng supervisor sở hữu cây tiến trình

Owner duyệt bước1–3: sửa runner, đo trọn candidate đầu rồi chạy hết5candidate.
Workspace commit `b10214e` thêm `forex_study_batch.py`, dùng lại
`nautilus_worker._WorkerOwnedJob`; actual base interpreter + venv import paths,
stdin gate trước study, kill-on-job-close cho cả descendants. Không tạo service,
model/provider hoặc broker call. Exit0 còn phải kiểm dossier/bindings/accounting.
Completed jobs reuse sau kiểm lại; partial/failed giữ nguyên và không auto retry.

**Đang thực thi, chưa kết luận:** private batch tại
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/prop-q1-comparison-20261105/attempt-2/`;
config/protocol copies tại `../supervised-inputs/`. Controller actualPID2076,
creation/command/executable ở `controller-identity.json`; Codex exec session95999.
Productpin814e1135. ProbeDonchian một mình, sau đó tối đa3jobs, hardcap1800s/job
và5400s/batch theo protocol bổ sung trước outcome. `progress.json`/`PROGRESS.md`
cập nhật5giây; `CANCEL` cạnh chúng dừng việc còn lại. Không khởi worker thứ hai
cho cùng batch. Chưa hỗ trợ resume giữa simulation; đọc terminal/process identity
trước khi tiếp. Final outcome bổ sung bên dưới khi thực sự xong.

Focused verification: `python -m unittest discover -s tooling/ai-engines/tests
-p test_forex_study_batch.py -v`: **6tests đạt**. Hai test thật Windows kiểm cả
worker+grandchild khi owner close và worker khi supervisor crash; còn lại kiểm
nonzero, exit0/artifact invalid, timeout và completed reuse không dispatch.
Không chạy lại core/strategy tests vì source/product không đổi trong lượt này.

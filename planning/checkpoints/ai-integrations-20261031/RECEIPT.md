# AI integrations — adoption và runtime cutover

31/10/2026, Asia/Saigon. Scope/acceptance:
[owner plan](../../trader/AI-RESEARCH-UI-PROTOTYPE-20261031.md),
[issue #6](https://github.com/Naqex/workspace/issues/6).
Đây là source/runtime foundation; chưa acceptance toàn vòng AI autonomy.

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

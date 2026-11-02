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

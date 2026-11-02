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

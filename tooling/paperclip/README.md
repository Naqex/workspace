# Paperclip trong Trader

Source nằm ở `projects/integrations/paperclip`, dưới dạng Git submodule từ
[fork Naqex](https://github.com/Naqex/paperclip), giữ upstream/layout và MIT license.
Pin đầu tiên: `42fd568cf8f588334cacc6004aa23aff54daa52b`
(version trong source: `0.3.1`). Không tự cập nhật theo nhánh master mỗi lần chạy.

Trader nhúng toàn bộ UI gốc qua iframe origin `http://127.0.0.1:17860`, mục
**AI → Paperclip**. Paperclip giữ điều hướng và dialog của nó; Trader giữ menu
cấp sản phẩm. Menu ngoài giữ lựa chọn của người dùng trên desktop, mở bằng nút
menu trên mobile.
Document của iframe được giữ khi chuyển sang công cụ khác trong cùng tab.

Host Trader cần cả `web/paperclipBridge.mjs`, plugin `localPaperclip()` trong
Vite config và `foundation_v2/local-services.json` cùng bản UI. Khi cập nhật
checkout runtime cũ, chỉ chép `dist` là chưa đủ cho route health. GET
`http://127.0.0.1:5180/integrations/paperclip/health` phải trả JSON với
`status: "ok"`; HTTP200 chứa HTML của SPA vẫn là bridge chưa được cài.
Sửa middleware chỉ cần restart UI Vite đúng owner, không cần restart API/MT5.

## Cài và chạy local

Cần Node.js >=24.11 và Git. Từ workspace root:

Lát tích hợp hiện tại cần source Trader có `foundation_v2/local-services.json`
(commit `18e9348d` hoặc hậu duệ; đồng bộ VI/EN cần `7b4c332d` hoặc hậu duệ).
Root gitlink Trader chưa nâng từ baseline cũ;
clone mới cần khôi phục đúng checkout feature trước khi dùng launcher/UI này.
Không tự reset checkout đang có WIP. Plan
`planning/trader/AI-RESEARCH-UI-PROTOTYPE-20261031.md` giữ handoff source.

```powershell
git submodule update --init -- projects/integrations/paperclip
```

Từ `projects/integrations/paperclip`:

```powershell
npm exec --yes --package=pnpm@9.15.4 -- pnpm install --frozen-lockfile --ignore-scripts
node scripts/ensure-plugin-build-deps.mjs
```

Lệnh thứ hai build shared/plugin SDK theo helper upstream đã kiểm tra. Không
chạy toàn bộ lifecycle scripts hoặc sửa package manager global. pnpm11 có sẵn
không đọc patch config như pnpm9 và đã từ chối frozen install ở pin này; dùng
đúng bản9.15.4 được `packageManager` của upstream chỉ định.

Trở lại workspace root:

```powershell
node tooling/paperclip/run-local.mjs
```

Launcher build UI với origin của Trader trước khi khởi động rồi phục vụ static
assets. Bản dùng hằng ngày không có Vite HMR hoặc dependency optimizer tự reload
khi chuyển trang. Build lỗi thì dừng trước khi khởi động server. Khi sửa source,
cần dừng đúng owner rồi chạy lại launcher để build bản mới; không dùng dist cũ.
Trong bản nhúng, dashboard không tự bật wizard khi company chưa có agent; nút
tạo agent và route onboarding chủ động vẫn hoạt động như Paperclip gốc.

Đây là process local chạy trong terminal, không cài Windows service hay tự khởi
động cùng máy. Launcher kiểm owner/PID, revision và cổng trước khi chạy; gọi lại
khi instance đã khỏe sẽ dùng instance hiện có. Instance đang khởi động/lỗi hoặc
cổng do process khác giữ sẽ bị từ chối thay vì tự kill/restart.

| Thành phần | Vị trí |
|---|---|
| Paperclip UI/API | `127.0.0.1:17860` |
| PostgreSQL riêng | loopback, port17861 |
| Vite HMR | port27860 được dành riêng; bản static không mở listener |
| Config/DB/storage/secrets | `.runtime/paperclip/instances/trader-ui/` |
| PID/identity | `owner.json` trong thư mục instance |
| UI Trader preview | `127.0.0.1:5218` |

Cổng được đọc từ `projects/trader/foundation_v2/local-services.json`.
[Bảng cổng và quy tắc cấp cổng](../../projects/trader/foundation_v2/docs/LOCAL-SERVICES.md)
giữ contract hiện hành cho cả CLIProxyAPI. Launcher kiểm cả ba cổng Paperclip;
không tự tăng cổng hoặc dùng listener lạ. Config instance cũ lệch JSON sẽ bị từ chối.
Khi đổi cổng: backup database/config, dừng đúng owner, sửa `server.port` và
`database.embeddedPostgresPort` trong config riêng rồi chạy lại launcher; giữ
nguyên DB/storage/home. Build lại Trader để URL iframe khớp JSON.

Launcher truyền một danh sách biến môi trường tối thiểu, không kế thừa
`DATABASE_URL` hoặc provider keys của Trader. First run tạo database mới và áp
migrations upstream trong database đó; không sửa DB Trader. Config được tạo một
lần, không ghi đè khi chạy lại. Telemetry và kiểm tra cập nhật tắt trong config;
heartbeat scheduler và announcements tắt trong môi trường process.

Tổ chức và đội pilot ban đầu đã được dọn qua API gốc ngày01/11 theo yêu
cầu owner. Sau đó owner tự tạo Naqex AI; theo yêu cầu nối engine mới, đã thêm hai
worker qua API gốc, giữ nguyên agent Trưởng nhóm nghiên cứu của owner.
Backup và kết quả thử được giữ trong
[receipt tích hợp](../../planning/checkpoints/ai-integrations-20261031/RECEIPT.md).
Owner tự tạo organization, agent, connection và công việc trong UI upstream.
Tắt scheduler không khóa API chạy agent thủ công. TradingAgents đã có lượt
Gemini → báo cáo NAQ-4 qua [native process adapter](../ai-engines/README.md);
RD-Agent vẫn paused. Chưa nối broker, dữ liệu Trader hoặc ánh xạ company Paperclip với workspace Trader.
Ẩn iframe không dừng công việc mà owner có thể cấu hình về sau.

VI/EN của Trader được đồng bộ tới Paperclip qua message chỉ dành cho preference;
kiểm exact origin + parent window, không đổi iframe URL hay tải lại bản nháp.
Launcher cấp `VITE_NAQEX_WORKSPACE_ORIGIN` từ cổng AI preview trong registry.
Mặc định chỉ origin preview đó được tin cậy. Khi dùng Trader chính ở5180, chờ
native runs kết thúc, dừng đúng instance owner rồi chạy:

```powershell
node tooling/paperclip/run-local.mjs --workspace-origin http://127.0.0.1:5180
```

Launcher kiểm exact loopback origin, build lại UI và ghi `workspaceOrigin` vào
owner receipt. Gọi lại phải dùng cùng origin; không tự restart instance đang
chạy để đổi cấu hình. Chỉ một origin host được tin cậy mỗi lần build; không dùng
wildcard hoặc nới kiểm `event.source`. Mở riêng dùng ngôn ngữ đã lưu hoặc EN.

Bản dịch đã mở rộng sang cấu hình, agents, công việc, kết nối, kỹ năng, chi phí,
dự án và các menu/dialog chuyên sâu. Nội dung người dùng, hướng dẫn skill, mã
cấu hình và chi tiết lỗi gốc từ dịch vụ giữ nguyên. Native i18next giữ namespace
`translation`; fork dùng `workspace` và `interface` để không làm lệch contract
các locale upstream khác. Cập nhật upstream vẫn cần đối chiếu call site và bản
dịch mới; không tự bảo đảm mọi màn hình động đã được nghiệm thu. Hướng dẫn
mở rộng/upgrade: `projects/integrations/paperclip/doc/NAQEX-LOCALIZATION.md`.
Theme vẫn do Paperclip quản lý; host chỉ gợi ý color scheme.

## Catalog skills trên Windows

Nếu native catalog trả 422 `Pinned catalog file hash mismatch`, kiểm tra byte
của file với SHA256 trong catalog trước khi cài. `core.autocrlf=true` có thể
chuyển LF của Git blob thành CRLF trong checkout. Chỉ khi bản LF khớp chính xác
cả Git blob của pin hiện tại và manifest mới khôi phục byte LF; không tái tạo
manifest hoặc nới kiểm hash để chấp nhận nội dung chưa xác minh.

Lát cài 03/11 đã khôi phục đúng 3 `SKILL.md` của `task-planning`, `qa-acceptance`,
`doc-maintenance` và thêm `text eol=lf` cho từng đường dẫn đó vào Git
`info/attributes` riêng của checkout (tìm bằng `git rev-parse --git-path info/attributes`).
Không đổi Git config global hoặc logic engine. Quy tắc local không đi theo clone;
checkout mới cần kiểm lại nếu gặp lỗi. Receipt giữ backup, hash và rollback.

## Owner tự thiết lập

Bản fork chỉ giữ Việt hóa và các thay đổi cần cho nhúng/điều hướng. Đã bỏ
ResearchTeamPreview, catalog mẫu và bản vá Windows Codex của lần pilot. Không
provision lại đội từ catalog mẫu hoặc thêm UI quản trị cạnh tranh với Paperclip.
Hai worker engine mới thuộc scope owner giao sau cleanup; xem hướng dẫn engine
jobs ở trên. Setup helper tạo worker paused; chỉ bật worker phân tích khi gateway
và model đã sẵn sàng. Giữ worker RD-Agent paused trước khi runtime đạt.

Thứ tự thao tác:

1. Tạo organization bằng UI Paperclip; tên do owner chọn.
2. Tạo một project nghiên cứu; chưa trỏ agent vào toàn bộ workspace.
3. Tạo một agent **Trưởng nhóm nghiên cứu** bằng wizard gốc. Chọn bộ chạy và kết nối
   tài khoản trong wizard; không bắt buộc tạo Local endpoint/CLIProxyAPI trước.
4. Chỉ sau khi Test Environment đạt mới giao một task offline nhỏ. Chưa bật
   lịch tự động; chưa tạo cả đội trước khi agent đầu chạy được.

Tên agent dùng chức danh doanh nghiệp tiếng Việt; không dùng nickname. Bộ tên
đề xuất và nguồn khảo sát nằm trong
[nghiên cứu đội agents](../../planning/research/PAPERCLIP-QUANT-TEAM-RESEARCH-20261031.md#tên-chức-danh-tiếng-việt--khảo-sát01112026).

### Native và giới hạn bản pin

- GitHub Copilot: profile upstream qualified=true, nhưng production ACPX của
  bản pin chặn win32 tại assertVerifiedAcpxProviderPlatform. Nút chọn không là
  bằng chứng Windows chạy được. Cần qualification trong môi trường Linux phù
  hợp trước khi dùng native này; chưa cài WSL/Docker hoặc đổi runtime trong lát này.
- Google Antigravity: profile qualified=false; UI hiện Chưa khả dụng đúng với
  upstream. Plan28/10 nhắm macOS ARM64 trước; Product E2E/Stop/tools còn pending.
  Không ép bật candidate hoặc cập nhật upstream chỉ để bỏ nhãn này.
- Gemini CLI: Google thông báo ngừng phục vụ tài khoản cá nhân/free/AI Pro/Ultra
  từ18/06/2026. Standard/Enterprise và paid API-key có ngoại lệ. Không hướng dẫn
  owner đăng nhập tài khoản cá nhân vào Gemini CLI chỉ vì picker còn mục đó.
- Native bỏ một tầng proxy, nhưng vẫn cần runtime, quyền tài khoản/model và
  kiểm chứng tool/task. Chưa có native Copilot/Antigravity run trong instance này.

Nguồn: [Google chuyển sang Antigravity](https://developers.googleblog.com/an-important-update-transitioning-gemini-cli-to-antigravity-cli/),
[GitHub Copilot authentication](https://docs.github.com/en/copilot/how-tos/copilot-cli/set-up-copilot-cli/authenticate-copilot-cli),
[source profile](../../projects/integrations/paperclip/packages/adapter-utils/src/paperclip-runner-permissions.ts),
[platform gate](../../projects/integrations/paperclip/packages/paperclip-runner/src/drivers/acpx/installation-integrity.ts),
[Antigravity plan](../../projects/integrations/paperclip/doc/plans/2026-10-28-antigravity-integration.md).

### MCP để trợ lý thao tác Paperclip

Paperclip có public Assistant Connections MCP; dùng làm control interface qua
API/authorization upstream thay vì thêm màn hình hoặc ghi DB. Direct MCP cho
phép đọc/giao việc, chỉnh existing agent/instructions/project/skills trong scope
được duyệt. Tạo agent, credentials, execution commands và policies nằm ngoài
surface đó; MCP không cấp model hoặc thay bộ chạy.

Ngày02/11 đã chuyển instance sang `authenticated` + `private`, chỉ bind loopback,
giữ DB/storage và cổng17860/17861. `auth.publicBaseUrl` là origin17860;
`enablePublicMcp=true` được bật qua API gốc. Owner đã đăng nhập và nhận quyền
quản trị qua board claim gốc. Lỗi404 cũ do thiếu auth/public origin đã được xử lý;
request chưa đăng nhập nay bị từ chối401 thay vì route không tồn tại.

Codex dùng Streamable HTTP trực tiếp tại `http://127.0.0.1:17860/mcp/paperclip`.
Định nghĩa nằm trong `.codex/config.toml` của workspace, tên `naqex_paperclip`.
OAuth đã được owner duyệt cho Naqex AI: `paperclip:read`, `paperclip:write`,
`offline_access`; không xin `paperclip:configure`. Allowlist chỉ bật công cụ
task/document và đọc agents/projects/approvals. Token OAuth do Codex quản lý;
không sao chép token vào TOML, repo hoặc worker settings.

Kết nối mới có thể cần nạp lại MCP/mở chat mới trong workspace. Khi công cụ đã
expose, gọi `paperclip_connection` rồi đọc một task để xác minh đúng company và
scope. Đã kiểm OAuth và discovery bằng Codex CLI/app-server riêng, không gọi model;
điều này không tự thêm tools vào chat đang chạy hoặc chứng minh một workflow mới
đã thực thi.

Studio giữ API riêng. Helper đọc board credential do native CLI lưu tại
`.runtime/paperclip/auth.json`, chỉ cho exact origin của project; không đọc token
MCP hoặc auth của instance ngoài. Đăng nhập/renew từ checkout Paperclip:

```powershell
$env:PAPERCLIP_HOME='D:\ANNAM\TradingWorkspace\.runtime\paperclip'
$env:PAPERCLIP_INSTANCE_ID='trader-ui'
node cli/node_modules/tsx/dist/cli.mjs cli/src/index.ts auth login --api-base http://127.0.0.1:17860 --company-id 6b90f0c1-8f91-4fe8-bc15-fc8c58b3ac8f --no-browser
```

Owner duyệt URL CLI hiện ra. Không xin instance admin cho credential Studio.
MCP renew từ workspace bằng `codex mcp login naqex_paperclip`; owner duyệt OAuth
riêng. Thu hồi từng kết nối qua UI native/CLI logout tương ứng. Không tự login,
auto-consent hoặc dùng key của worker thay cho quyền người dùng.

Backup trước chuyển đổi ở `.runtime/paperclip/mcp-cutover-20261102/`, gồm native
SQL dump và config/env/owner. Khi phục hồi, dừng đúng instance owner, giữ database
hiện tại; khôi phục cấu hình đã sao lưu và toggle MCP qua quyền quản trị hợp lệ,
rồi restart. Không restore DB chỉ để đổi auth mode. Snapshot config cũ dùng
`local_trusted`, nên rollback làm instance trở lại quyền local không cần login;
chỉ dùng khi owner chủ động chọn chế độ đó. Không đổi mode khi worker đang chạy.

[Tài liệu MCP upstream](https://github.com/paperclipai/paperclip/blob/master/doc/public-mcp.md)
và [bản pin](../../projects/integrations/paperclip/doc/public-mcp.md) giữ contract.

### Gateway project sau pilot

Hiện hành02/11: standalone gateway project đã mở lại bằng config/account sẵn có,
phục vụ worker TradingAgents qua cổng trong registry. Owner/PID và log hiện hành
ở `.runtime/paperclip/gateway-owner.json`; không đổi gateway Windows8317.
Config thực tế giữ giới hạn8MB từ pilot sau, không phải64KB của snapshot cleanup.
API Trader cũ từng trả `ai_gateway_config_conflict` khi start; chưa sửa mismatch
đó. Giữ standalone owner và không start gateway thứ hai từ API.

Lịch sử trước lát engine:

Pilot Sky AI 01/11 chạy lại gateway 17852 và nâng max-request-body-bytes lên 8388608 vì prompt agent vượt 64 KB (chi tiết, backup trong RECEIPT ai-integrations-20261031). Trước pilot:
Sau cleanup, gateway standalone17852 được dừng và giới hạn request phục hồi đúng
backup65536 bytes. Owner có thể yêu cầu khởi động lại bằng config/auth hiện có;
`.runtime/paperclip/gateway-owner.json` giữ PID/identity/log và trạng thái phiên.
Kiểm process/port lại khi dùng, không tự start để setup native và không giao
gateway cho API Trader khi standalone owner vẫn chạy. Giữ auth/account project,
binary và registry port; không sửa gateway Windows8317.
Không xóa các tích hợp source RD-Agent/TradingAgents hoặc Trader WIP.

Kiểm tra lỗi điều hướng nhúng sau khi Paperclip và Trader preview đã chạy:

```powershell
node tooling/paperclip/navigation.browser.mjs
```

Script dùng Playwright đã cài trong Trader, chặn request ghi/ra ngoài; kiểm tra
document không reload, wizard không tự mở, giữ bản nháp khi chuyển công cụ/VI-EN
và chờ 35 giây. Chỉ mở wizard bằng nút tạo agent, không gửi form hoặc tạo agent.
Evidence local nằm ở `.runtime/research/paperclip-navigation/report.json`.

## Trader preview và dev

Vite dev/preview có route cố định `/integrations/paperclip/health` chỉ GET tới
health của Paperclip; không proxy API ghi hoặc trả chi tiết đường dẫn database.
Production host khác cần mount route tương đương trước khi dùng panel này.

Từ `projects/trader/foundation_v2/web`:

```powershell
npm run build -- --outDir ../.runtime/ai-workspace-preview
node serveAiPreview.mjs 5218
```

Server preview phục vụ UI Trader và bridge health cố định cho Paperclip và
CLIProxyAPI. Panel CLIProxyAPI nhận diện phản hồi preview rồi kiểm trang quản trị
ở cổng registry17852; không cần bật API Trader hoặc đưa khóa vào bridge. Rời panel
trong preview không gọi refresh API Trader. API Trader khác không được nối;
writes bị từ chối. Các iframe gọi UI/API integration thật trên origin riêng.
Không coi preview này là bản Trader/API đầy đủ trên5180.

Rollback UI: chạy lại static preview cũ đã giữ trong
`projects/trader/foundation_v2/.runtime/ai-research-ui-20261031/serve.mjs` sau khi
xác minh và dừng đúng process preview mới. Giữ database Paperclip; không xóa dữ
liệu để rollback giao diện. Upstream upgrade là một candidate pin mới, có kiểm
tra migration/backup và UI riêng, không `submodule update --remote` tự động.

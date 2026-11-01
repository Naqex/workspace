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

Instance ban đầu có một organization rỗng `Naqex AI`, chưa có agent/job/provider
được cấu hình. Tắt scheduler không khóa API chạy agent thủ công; đây là instance
Paperclip thật, không phải sandbox chặn mọi execution. Chưa nối trading engines,
broker, dữ liệu Trader hoặc tự ánh xạ company Paperclip với workspace Trader.
Ẩn iframe không dừng các công việc mà owner có thể cấu hình về sau.

VI/EN của Trader được đồng bộ tới Paperclip qua message chỉ dành cho preference;
kiểm exact origin + parent window, không đổi iframe URL hay tải lại bản nháp.
Launcher cấp `VITE_NAQEX_WORKSPACE_ORIGIN` từ cổng AI preview trong registry.
Hiện chỉ origin preview đó được tin cậy; host ở cổng khác cần cấu hình lại và
kiểm chứng trước khi coi ngôn ngữ đã đồng bộ. Mở riêng dùng ngôn ngữ đã lưu hoặc EN.

Bản dịch đã mở rộng sang cấu hình, agents, công việc, kết nối, kỹ năng, chi phí,
dự án và các menu/dialog chuyên sâu. Nội dung người dùng, hướng dẫn skill, mã
cấu hình và chi tiết lỗi gốc từ dịch vụ giữ nguyên. Native i18next giữ namespace
`translation`; fork dùng `workspace` và `interface` để không làm lệch contract
các locale upstream khác. Cập nhật upstream vẫn cần đối chiếu call site và bản
dịch mới; không tự bảo đảm mọi màn hình động đã được nghiệm thu. Hướng dẫn
mở rộng/upgrade: `projects/integrations/paperclip/doc/NAQEX-LOCALIZATION.md`.
Theme vẫn do Paperclip quản lý; host chỉ gợi ý color scheme.

Trang Agents có nút **Xem đội và nhiệm vụ mẫu**: ba vai trò nghiên cứu và một
nhiệm vụ để owner xem trước. Đây là UI đề xuất, chưa tạo agents, jobs hoặc lịch
chạy. Bật kết nối model/engine và thực thi là một lát tích hợp riêng.

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

Server preview chỉ phục vụ UI Trader và bridge health. API Trader khác không
được nối; writes bị từ chối. Iframe vẫn gọi API Paperclip thật trên origin riêng.
Không coi preview này là bản Trader/API đầy đủ trên5180.

Rollback UI: chạy lại static preview cũ đã giữ trong
`projects/trader/foundation_v2/.runtime/ai-research-ui-20261031/serve.mjs` sau khi
xác minh và dừng đúng process preview mới. Giữ database Paperclip; không xóa dữ
liệu để rollback giao diện. Upstream upgrade là một candidate pin mới, có kiểm
tra migration/backup và UI riêng, không `submodule update --remote` tự động.

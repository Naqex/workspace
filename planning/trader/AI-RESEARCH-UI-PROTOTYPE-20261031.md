# AI workspace — native Paperclip UI và prototype lịch sử

## Lát setup được owner giao — 01/11

Owner giao cấu hình Paperclip và mở CLIProxyAPI project bằng các tài khoản đã
đăng nhập. Đã lưu native connection Responses API và tạo ba agents thật theo
đề xuất research. Connection/model probe đạt; pilot `NAQ-1` chưa đạt toàn luồng:
công cụ shell bị policy từ chối. Cả đội đã pause, timer/wake tắt, không có run
đang chạy. API gateway vẫn mở cho project; không thay bản Windows.

Source sửa Windows của Paperclip: `42b6107`; receipt giữ failure trước/sau,
owner/backup và việc cần tiếp tục. Bước tiếp là qualification harness/sandbox và
thu hẹp quyền thực tế, rồi mới chạy researcher/reviewer; chưa bật automation,
RD-Agent, TradingAgents hoặc broker. Không nối runtime chỉ dựa vào flag permission.
Hướng dẫn vận hành: [Paperclip](../../tooling/paperclip/README.md).
UI audit rộng tiếp tục pause; các mục dưới đây là lịch sử theo từng lát.

## Lịch sử mở rộng UI — 01/11

Đã mở rộng bản dịch VI/EN sang các trang/menu/dialog chuyên sâu của fork bằng
catalog i18next riêng. Trang Agents có **Xem đội và nhiệm vụ mẫu**: sơ đồ ba
vai trò và một nhiệm vụ nghiên cứu để owner duyệt, chưa provision agent/job.
Source Paperclip `11d41b6`; runtime local đã cập nhật cùng revision, giữ DB.
Phạm vi kiểm chứng và giới hạn nằm trong mục ngày01/11 của
[receipt tích hợp](../checkpoints/ai-integrations-20261031/RECEIPT.md).

Tại thời điểm lát UI này, còn cần review trước khi cấu hình agents, provider và
contract chạy job engine. Các mục31/10 dưới đây
giữ lịch sử, không thay coverage và trạng thái mới trong receipt.

## Lát localization tiếp nối — 31/10

Đã nối VI/EN từ Trader preview tới native Paperclip bằng preference message
kiểm origin/source; đổi ngôn ngữ giữ document, bản nháp và search. Fork dùng
i18next namespace `workspace` riêng, giữ locale upstream và tên/nội dung do
người dùng nhập. Phạm vi hiện tại: navigation desktop/mobile, account actions,
task breadcrumb/search/empty/create và trường chính của new-task dialog.
Đây là bản dịch từng phần; filters/composer settings và các trang khác còn EN.

Browser preview5218: 9 cases trên1920/1440/390px; source review độc lập;
focused unit/component, UI typecheck và build đã kiểm. Token gate toàn fork
còn106 lỗi upstream, không thêm lỗi so với pin cũ. Receipt chi tiết nối vào
`planning/checkpoints/ai-integrations-20261031/RECEIPT.md`.
Chưa cấu hình agents/provider hoặc chạy engine job. UI audit rộng vẫn pause;
tiếp theo hoàn thiện các luồng UI cần dùng và cấu hình company/roles cho owner
review trước khi nối job. Root gitlink Trader vẫn giữ baseline để tránh đưa WIP
audit vào lát integration; host feature checkout được ghi ở receipt.

## Lát adoption được owner giao — fork, source và AI environment

Issue: [Naqex/workspace#6](https://github.com/Naqex/workspace/issues/6).
Owner chọn fork Paperclip gốc, RD-Agent, TradingAgents và LangGraph; giao thực
hiện fork/tích hợp và rà skill dài hạn. Thứ tự UI trước engine vẫn áp dụng.

Acceptance lát nền source/runtime:

- Paperclip có fork Naqex và upstream remote riêng; giữ revision đã kiểm chứng,
  không tự nhảy lên master mới nhất khi tạo fork.
- Source ngoài dưới `projects/integrations/`, giữ submodule/layout/license; RD-Agent
  được pin source. LangGraph giữ là dependency TradingAgents, Quant Lab giữ nguyên.
- Paperclip đang nhúng vẫn hoạt động sau chuyển đường dẫn; giữ nguyên company,
  dữ liệu, cổng và preference sidebar. Backup và rollback được ghi trước cutover.
- Hướng dẫn gần source, một skill repo cho workflow upstream đã được thực hiện;
  không tạo skill nghiên cứu AI từ luồng chưa chạy hoặc thay global config.
- Kiểm topology/đường dẫn, dependency/import và native browser phù hợp với thay đổi.

Lát này không chứng minh RD-Agent/TradingAgents đã chạy job model hay toàn vòng
autonomy. Các lát nối engine sau phải có contract job thực tế, authority cho
dispatch/retry và evidence riêng; không khai agent chạy được chỉ vì đã clone source.
Checkpoint của lát này: `planning/checkpoints/ai-integrations-20261031/RECEIPT.md`.

## Lát được giao tiếp theo — native Paperclip

Owner xác nhận nối UI gốc và lưu source trong `projects/`. Đã tích hợp submodule
upstream `projects/paperclip` tại pin `42fd568cf8f588334cacc6004aa23aff54daa52b`,
giữ source nguyên bản. Trader mở AI→Paperclip bằng iframe toàn vùng nội dung;
rail bên ngoài giữ lựa chọn của owner, bên trong dùng điều hướng và dialogs gốc. Dữ liệu
Paperclip có instance riêng; chưa nối engine nghiên cứu/giao dịch.

[Setup/runtime boundaries](../../tooling/paperclip/README.md).
Evidence/source/runtime và các giới hạn được giữ trong receipt
`projects/trader/foundation_v2/evidence/paperclip-ui-20261031/RECEIPT.md`.
Implementation ban đầu ở Trader `98a0871b`, điều chỉnh port/sidebar ở `18e9348d`; gitlink Trader của root
chưa nâng vì HEAD hiện tại còn chứa lịch sử ngoài phạm vi tích hợp này.
Owner yêu cầu tách cổng khỏi app Windows: Paperclip hiện dùng API17860/DB17861/
HMR27860; CLIProxyAPI managed giữ17852, không chạm instance Windows8317.
`foundation_v2/local-services.json` trong Trader giữ cấu hình dùng chung;
`docs/LOCAL-SERVICES.md` và receipt `PORTS-SIDEBAR.md` giữ hướng dẫn/bằng chứng.
Preview owner tại
`http://127.0.0.1:5218/?workspace=tenant-a&view=ai&area=ai&section=paperclip&lang=vi`.
Các đoạn phía dưới giữ lịch sử quyết định/prototype, không thay trạng thái mới.

## Điều chỉnh hướng sau owner review, 31/10

Owner yêu cầu thiết kế UI từ tổng thể vào chi tiết: khung workspace → điều
hướng → UI upstream → các hành trình trading riêng. Ưu tiên nhúng UI gốc
Paperclip như cách Trader nhúng CLIProxyAPI; không tiếp tục dựng các màn quản
lý công việc/agents riêng để thay thế Paperclip.

Prototype `5aafd680` bên dưới giữ làm bản khám phá workflow, chưa được owner
chấp nhận làm giao diện đích. Build/browser receipt của prototype không chứng
minh Paperclip đã tích hợp. UI audit rộng vẫn pause.

Lát tiếp theo đề xuất: Trader giữ điều hướng cấp sản phẩm; khu AI dành vùng
nội dung cho Paperclip với điều hướng nội bộ của chính nó. Khi ở khu này, thu
gọn điều hướng Trader để tránh hai sidebar đầy đủ cạnh nhau. Chốt khung và
chuyển qua lại trước khi làm màn nghiên cứu riêng hoặc nối engine.

Nguồn kiểm tra: [repo upstream](https://github.com/paperclipai/paperclip),
[server](https://github.com/paperclipai/paperclip/blob/master/server/src/app.ts),
[API client](https://github.com/paperclipai/paperclip/blob/master/ui/src/api/client.ts)
và [MIT license](https://github.com/paperclipai/paperclip/blob/master/LICENSE).
UI gọi `/api` trên origin của Paperclip, nên hướng thử đầu là iframe nguyên
ứng dụng tại origin local riêng; không copy riêng bundle vào origin Trader.
Đây là đánh giá từ source, chưa xác nhận iframe/auth bằng runtime. Cần pin
revision và kiểm framing headers, login/cookies, điều hướng, sự kiện và layout
trên đúng bản chạy trước khi kết luận tương thích.

UI gốc cần API/storage của Paperclip để hoạt động; chạy instance local phục vụ
review UI là một lát riêng với dữ liệu riêng và không tự giao việc cho agent.
Chưa cài/chạy instance hoặc nối trading engine từ lần điều chỉnh này. Không
đặt tối ưu hiệu năng giả định thành điều kiện chặn; mount khi mở lần đầu và
giữ state nếu phù hợp, đo bottleneck thật sau. Ẩn UI không có nghĩa dừng agents.

## Scope prototype lịch sử

Owner giao ngày31/10: làm UI trong Trader trước để review workflow; backend và
services chỉ tiếp sau feedback. Owner cho phép thử CLIProxyAPI/Gemini, nhưng lát
UI này không cần gọi model. Brief kiến trúc: [autonomy](../research/AUTONOMOUS-TRADING-SYSTEM-BRIEF.md).

## Phạm vi

- Khu AI có mục Nghiên cứu, dùng shell và design system hiện có.
- Danh sách có tìm kiếm/lọc; chi tiết có quy trình, thử nghiệm và nhật ký.
- Dialog tạo bản nháp với mục tiêu, data/baseline mẫu và giới hạn số lần thử.
- Trạng thái mẫu: đang chạy, hoàn tất/chờ review, thiếu bằng chứng, lỗi và dừng.
- Quyết định demo chỉ là preview; không tạo run, gọi broker hoặc ghi DB.
- State lưu local theo workspace, có báo lỗi lưu và khôi phục mẫu có xác nhận.

UI phải ghi rõ dữ liệu minh họa; không dùng metric giả như bằng chứng nghiên cứu.
Reuse LegacyModal, FxSelect, SearchInput, AppIcon, palette và compact controls.
Giữ VI–EN, dark/light, keyboard/focus và layout desktop/mobile. Không resume
owner-system audit đang pause hoặc stage WIP của nó.

## Kiểm chứng và bàn giao

Build ở output riêng; browser journey trên UI hiện hành với API fixture/deny
cho writes và external traffic. Kiểm create→reload, search/filter, tabs,
stop/decision preview, empty/error, Escape/focus và mobile/light. Review ảnh
thực tế. Receipt source/build/fixture tách khỏi backend/provider acceptance.

Trạng thái/evidence và hướng mở preview giữ trong receipt tại
`projects/trader/foundation_v2/evidence/ai-research-ui-20261031/`.
Source checkpoint trong repo Trader: `5aafd680`.
[Preview UI riêng](http://127.0.0.1:5218/?workspace=tenant-a&view=ai&area=ai&section=research&lang=vi).
Owner xem prototype trước khi giao lát backend/services. Plan này chỉ own scope,
không đóng Product Plan/U/Y/W hoặc cấp quyền live.

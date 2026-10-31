# AI Research — UI prototype

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

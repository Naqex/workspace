# Paperclip — khảo sát bản dịch, cấu hình và vị trí engine

Ngày: **31/10/2026**. Research/proposal; chưa là quyết định adoption hoặc kế hoạch di chuyển.
Scope: tiếp nối [brief kiến trúc](AUTONOMOUS-TRADING-SYSTEM-BRIEF.md), theo yêu cầu
khảo sát của owner. Không thay trạng thái acceptance của prototype/engine.

## Kết quả bản dịch

Chưa tìm thấy bản tiếng Việt hoàn chỉnh đủ bằng chứng để dùng ngay.

| Nguồn đã kiểm tra | Kết quả | Khuyến nghị |
|---|---|---|
| Paperclip pin `42fd568cf8f588334cacc6004aa23aff54daa52b` | Có i18next/react-i18next; `vi.json` chỉ có ba chuỗi onboarding; khởi tạo mặc định English | Mở rộng nền i18n hiện có nếu owner giao Việt hóa |
| [hinet/paperclip-lang](https://github.com/hinet/paperclip-lang), pin `6eb40ef1ac9f4610298616af1bd0180f7ef226e7` | Plugin dịch DOM, sáu ngôn ngữ, chưa có VI; đổi ngôn ngữ reload trang | Không cài nguyên trạng; chỉ tham khảo sau kiểm tra license |
| [moxi-2534/paperclip-zh-CN](https://github.com/moxi-2534/paperclip-zh-CN), pin `7f031df9f49bdb77b2e9611085d893d3ebe6cec8` | Fork tiếng Trung; 299 key top-level trong mỗi catalog EN/ZH; dùng i18next và language detector | Tham khảo cách tách chuỗi; không thay checkout đang chạy bằng fork cũ |

Native catalog: [vi.json tại pin đang dùng](https://github.com/paperclipai/paperclip/blob/42fd568cf8f588334cacc6004aa23aff54daa52b/ui/src/i18n/locales/vi.json).
Plugin hinet khai MIT trong package.json nhưng chưa thấy LICENSE độc lập;
package version 1.0.5 khác manifest 1.0.2, SDK devDependency `^2026.416.0`.
Chưa xác minh tương thích plugin end-to-end với Paperclip pin hiện hành.
Paperclip ghi [plugin API còn alpha](https://docs.paperclip.ing/administration/plugins/).

### Kiểm chứng giới hạn của plugin DOM

Đọc source/build scripts, không install dependency hoặc chạy plugin worker.
Chạy nguyên hàm DOM translator đã bỏ type TypeScript trên trang HTML giả định
bằng Playwright headless. Sáu assertion xác nhận:

- Nhãn button khớp dictionary được dịch.
- Nội dung `contenteditable` và `pre` cũng bị thay chữ khi khớp dictionary.
- `placeholder` và `aria-label` không được dịch.
- Sửa `.data` của text node hiện hữu không kích hoạt bản dịch.

Đây là lỗi/phạm vi hiển thị trên fixture; không chứng minh dữ liệu lưu bị sửa.
Không cài plugin hoặc kiểm thử nó trong instance đang dùng. Clone/source probe
và JSON kết quả ở `.runtime/research/paperclip-localization-20261031/` (local,
ignored); script `probe.mjs`, kết quả `dom-translator-fixture-result.json`.

Hướng đề xuất: catalog EN/VI + gọi key ở component bằng i18n hiện có, giữ patch
riêng nhỏ trong fork có upstream remote. Pin version; cập nhật qua candidate,
kiểm key thiếu và các luồng chính trước promotion. Patch không tự mất khi merge
đúng cách, nhưng vẫn có thể conflict hoặc phát sinh chuỗi chưa dịch sau update.
Không hứa plugin/overlay loại bỏ được công bảo trì này.

## Ai cấu hình Paperclip?

Đề xuất Codex chuẩn bị phần kỹ thuật có thể tái lập: cấu hình instance, vai trò,
adapter, workflow mẫu, đường dẫn/cổng, backup và chính sách duyệt theo scope.
Paperclip có API cấu hình và [export/import công ty](https://docs.paperclip.ing/guides/power/export-import/);
source tại pin hiện hành có route export/import preview/apply. Không giả định
export công ty bao gồm toàn bộ instance, secret hoặc database backup.

Owner quyết định mục tiêu, ngân sách, tài khoản/model và quyền tự chủ. Đăng nhập
và secret xử lý local; không đưa credential vào Git. Chưa tạo agents, nối
provider hoặc bật job trong lượt khảo sát. Bước cấu hình phải có scope riêng.

## Nhúng UI khác với nối engine

| Thành phần | Cách dùng đề xuất |
|---|---|
| Paperclip | Nhúng UI quản lý công việc/agents; đã có native embed, chưa nối engine |
| [RD-Agent](https://github.com/microsoft/RD-Agent) | Worker nghiên cứu chạy job giới hạn qua adapter; trả trạng thái/artifact; chưa chọn/cài |
| [TradingAgents](https://github.com/TauricResearch/TradingAgents) | Engine phân tích/phản biện; đưa báo cáo vào UI chung; chưa có bằng chứng tích hợp Paperclip |
| [LangGraph](https://docs.langchain.com/oss/python/langgraph/overview) | Thư viện workflow bên trong worker; TradingAgents local đã khai dependency; không cần clone UI/repo riêng |

Mapping là đề xuất phân trách nhiệm, không buộc mỗi job đi qua cả bốn thành phần.
Paperclip quản lý việc cấp cao; engine giữ vòng chạy nội bộ của job. Khi triển
khai phải chọn rõ một owner cho dispatch/retry/cancel/approval để không chạy đôi
với AI lifecycle Trader hiện có. Engine không tự nhận quyền broker từ task.

## Bố trí source — đề xuất, chưa di chuyển

Giữ sản phẩm tự phát triển ở `projects/trader`, `projects/quant-trading`,
`projects/vi-dubber`. Có thể gom ứng dụng/engine ngoài đã adoption dưới
`projects/integrations/` (Paperclip, TradingAgents, RD-Agent nếu được chọn).
Phân theo vai trò bảo trì; việc là fork không đủ để phân loại một sản phẩm.
Giữ mỗi repo/submodule độc lập và nguyên layout/license upstream.

Thư viện như LangGraph nằm trong dependency/lockfile của consumer. Source chỉ
khảo sát ở `.runtime/research/`; launcher/adapter dùng chung ở `tooling/`.
Không đặt database/secret cùng checkout để tiện gom thư mục.

Chưa tạo cây thư mục mới: di chuyển repo đang chạy cần một lát riêng cập nhật
gitlink, launcher, config, docs và runtime paths; giữ data, xác minh restart và
rollback. Runtime local, root gitlink chưa đồng bộ feature Trader và các WIP
audit hiện hành được mô tả trong `tooling/paperclip/README.md`; khảo sát này
không xử lý hoặc công nhận các gate đó.

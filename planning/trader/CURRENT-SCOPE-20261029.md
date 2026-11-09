# Naqex Trader current execution scope — 29/10/2026

## Quyết định phạm vi

Đây là scope điều hành hiện tại cho Naqex Trader. Nó áp dụng cho code và
evidence mới ở `projects/trader/foundation_v2`, nơi các AI agents đã hoàn thiện
UI theo hướng tham chiếu FX Replay và các contract/runtime hiện hành.

Các plan/checkpoint cũ vẫn giữ để truy vết lịch sử, nhưng không dùng các yêu cầu
đã lỗi thời làm điều kiện chặn cho slice hiện tại.

## Tạm hoãn khỏi đợt này

| Hạng mục cũ | Cách xử lý hiện tại |
|---|---|
| Figma Make round-trip / Y26 / U1d | Deferred. Không mở Figma, không upload context, không yêu cầu Make artifact. |
| Miro board / Y12 | Deferred. Không cập nhật board hoặc coi board là acceptance source. |
| Điều kiện Figma/Miro trong U9 | Bỏ khỏi critical path hiện tại; U9 chỉ xét integrated code, QA, cleanup, rollback và evidence thực tế. |

Việc tạm hoãn này không đánh dấu Y12/Y26 là đạt; chỉ loại chúng khỏi phạm vi
đang thực thi. Có thể mở lại bằng một quyết định phạm vi mới.

## Gate đang dùng

| Nhóm | Phạm vi hiện tại | Trạng thái từ audit mới |
|---|---|---|
| UI | FX-aligned shell, design system, chart, live/practice/analytics và các hành trình hiện có | U1/U3/U4: partial; U9: chưa đóng |
| Data | QDM/Dukascopy isolated import, contracts, catalog, scope guard | U2: partial |
| Research | Engine, deterministic reconciliation, OOS/stress software slices | U5: partial |
| Analytics/Prop | Read model, metrics và live presentation | U6: partial |
| AI | Offline/provider-neutral boundary, context hash, no-broker guard | U7: partial |
| Demo/live | Demo lifecycle receipt theo account đã được cấp quyền; live tách riêng | U8 demo slice: pass có giới hạn; U8 live: mở |

Một slice chỉ được ghi `scoped accepted` khi receipt nêu đúng source/build,
phạm vi và giới hạn. Không chuyển slice thành full product acceptance.

## Các phần giữ lại — ví dụ ngay trong Trader

Owner đồng ý tiếp tục các phần dưới đây. Dùng code đang chạy và kiểm chứng
hành vi tương ứng để quyết định đạt; mỗi ví dụ là một việc người dùng thực sự làm.

| Phần giữ | Tình huống trong Trader | Cần kiểm chứng để khép phần tương ứng |
|---|---|---|
| UI và design system | Mở Live > Giao dịch, lọc Buy, sang Lịch rồi quay lại; dùng trên màn hình nhỏ. | Trang không lỗi, bộ lọc đúng, bảng/biểu đồ không chồng chữ; trạng thái lỗi có đường thử lại. |
| Dữ liệu thị trường | Nhập EURUSD M1 từ QDM/Dukascopy để luyện tập một đoạn lịch sử. | Nến đúng thời gian, OHLC và khoảng dữ liệu; phát hiện thiếu/trùng nến trước khi dùng kết quả. |
| Luyện tập / replay | Tua EURUSD đến 10:00, đặt Buy rồi chạy tiếp tới SL/TP. | Không lộ nến tương lai; lệnh, giá khớp, phí và số dư khớp với các bước đã chạy. |
| Research | Thử quy tắc breakout trên một giai đoạn, rồi kiểm trên giai đoạn khác chưa dùng để chỉnh quy tắc. | Chạy lại cho cùng kết quả; tính phí; tách dữ liệu xây quy tắc và dữ liệu kiểm tra. |
| Phân tích và Prop | Account MT5 có 14 giao dịch đã đóng: bảng, lịch và panel phân tích phải dùng đúng phạm vi. | Không đếm 28 deal vào/ra thành 28 trade; phí, hòa vốn, múi giờ và hạn mức Prop được tính đúng. |
| Nhãn dùng chung | Tạo nhóm Setup, nhãn Breakout màu xanh trong Settings; gắn cho một lệnh Practice và một lệnh Live. | Cùng tên/màu; đổi tên cập nhật cách hiển thị; lưu trữ không xóa dấu vết trên lệnh cũ. |
| AI hỗ trợ | Hỏi AI nhận xét nhóm lệnh có nhãn Breakout trong dữ liệu đã chọn. | Biết dữ liệu/phạm vi đang đọc, không tự bịa số liệu hoặc tự gửi lệnh; quyền provider tách riêng. |
| Kết nối MT5 demo/live | Đồng bộ account demo đã liên kết rồi mở các lệnh trong Live. | Đúng account, số liệu, trạng thái mới/cũ; kiểm chứng demo không tự cấp quyền giao dịch tài khoản thật. |
| Kiểm tra tích hợp và dọn repo | Khởi động lại app, mở các trang chính, tiếp tục phiên đã lưu. | Chạy đúng entrypoint, giữ dữ liệu và có rollback; receipt chỉ rõ phần nào thực sự đã kiểm. |

## Nguyên tắc tiếp tục

1. Ưu tiên sửa và kiểm chứng code/evidence hiện hành trong `foundation_v2`.
2. Dùng browser/runtime QA theo các hành trình thực tế của Naqex Trader; không
   quay lại preview legacy để quyết định UI.
3. Không tự mở provider trả phí, holdout, broker/live, deploy hoặc packaging.
4. Khi muốn đưa Figma/Miro trở lại, tạo một scope amendment mới thay vì sửa
   receipt lịch sử.

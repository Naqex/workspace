# US500: chuẩn bị kiểm xu hướng 12 tháng, không tìm lại tham số của RSI

Đây là hướng R009 đã có trong catalogue, trước đây bị hoãn vì thiếu lịch sử
dài. Đăng ký hướng tiếp theo trong khi hai lượt RSI đang hoàn tất; **chưa chạy
số liệu mới**. Không đổi tiêu chí hoặc kết quả của các ứng viên đã thử.

Nguồn vừa đọc lại 08/11/2026: [AQR — Time Series Momentum, original paper data](https://www.aqr.com/Insights/Datasets/Time-Series-Momentum-Original-Paper-Data).
Nghiên cứu dùng tín hiệu excess return 12 tháng, giữ một tháng trên nhiều hợp
đồng futures/forwards. Dữ liệu CFD giá thuần, hard SL và mức risk của project
khác nghiên cứu gốc: đây là **adaptation**, không phải replication hoặc bằng
chứng rằng kết quả công bố sẽ chuyển sang US500/FTMO.

## Quy tắc trước kết quả

| Phần | Quyết định |
|---|---|
| Hai phiên bản | Tín hiệu long/short theo dấu thay đổi giá 12 tháng; benchmark luôn long khi có cùng lịch sử hợp lệ |
| Mốc dữ liệu | 2013 chỉ warmup; đánh giá liên tục 2014–2024, không reset tài khoản mỗi năm; không đọc 2025+ |
| Tín hiệu | Close Bid của phiên cash cuối tháng vừa kết thúc so với close cuối tháng cách đó 12 tháng; cần đủ 13 mốc liên tiếp, không điền close thiếu |
| Quyết định và khớp | Đầu phiên cash đầu tiên của tháng mới; quyết định tại open, khớp open M1 sau đó một phút; thiếu phút khớp thì hết hạn, không khớp bù |
| Stop | 1,5 lần trung bình 14 true ranges của 14 phiên cash hoàn chỉnh trước đó; giữ nguyên SL cho vị thế đang có |
| Quản lý lệnh | Một vị thế; đổi dấu thì đóng và đảo chiều; cùng dấu giữ lệnh, không thêm lot/reset SL; sau SL chờ lịch tháng sau; dữ liệu tín hiệu/ATR không hợp lệ thì đề nghị thoát |
| Vốn và chi phí | 10.000 USD, planned risk 25 USD/lệnh; geometry/lot/margin/commission/slippage/funding giữ shared book đã kiểm; hai kịch bản phí cũ, không nâng risk |
| Cuối mẫu | Giữ open position, floating và funding đến hết 2024; không tạo lệnh đóng giả để làm đẹp |

Cash daily và month endpoints phải tự tổng hợp từ canonical unfiltered M1
Bid/Ask và lịch NYSE đã pin. Không dùng provider D1/H1 range đang bị quarantine.
Chỉ cập nhật lịch sử ngày hiện tại **sau** quyết định ở open; future gap/giá
cuối ngày không được sửa quyết định đã xảy ra. Calendar biết trước không đồng
nghĩa giá tương lai đã biết. Không dùng volume CFD làm exchange volume.

## Điều kiện chạy và review

Trước chạy: hoàn tất writer hiện hành; kiểm source/input/protocol pins, causal
fixtures (13 tháng, dấu return, missing month, ATR quá khứ, future-prefix),
shared book, null control và bộ đối soát đã vá. Hai phiên bản cùng input/cost/
risk, nhưng là hai trials có quan hệ, không phải hai bằng chứng độc lập.

Giới hạn máy: kiểm RAM thực tế trước load toàn kỳ; một numerical writer,
deadline/cancel/status/log, output mới. Tái dùng dữ liệu đã seal, không tải lại
lịch sử hoặc mở provider/account mới. Chuẩn bị/indexing và compute/review có
timer riêng; không thêm GPU/framework chỉ vì có thể.

Sau chạy báo net chuẩn/stress, trades/funding/open mark, các năm có giá trị
mark-to-market và ba block 2014–2017 / 2018–2020 / 2021–2024, cùng benchmark.
Annual net là chênh lệch equity của **cùng account liên tục**, không cộng các
annual books reset. Đủ ưu tiên kiểm sâu nếu stress tổng dương, ít nhất 7/11
năm stress dương và cả ba block stress dương; đây là heuristic đăng ký trước,
không là p-value, đủ edge hoặc kết luận loại cả họ xu hướng. Chênh lệch so
benchmark phải được trình bày để thấy phần lợi nhuận có thể chỉ do thị trường
tăng; chưa có native path/DD thì chưa tuyên bố vượt benchmark về risk.

Data exposure/trial history, gaps, stale quotes, declared financing/dividends
và target broker contract vẫn phải được review. Lượt này chỉ là retrospective
screening; không clean OOS, prop compliance, OrderCheck/OrderSend hoặc quyền
mua challenge. C1/C2 chưa hoàn tất. Chỉ thực thi sau các điều kiện trên, không
ghi kết quả hoặc tự nâng trạng thái catalogue trước khi đã chạy.

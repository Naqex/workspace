# R026: cần tín hiệu cổ phiếu tương đối trước khi viết bot

Delta sau preflight: [fixture/provenance results](INDEX-EXPLICIT-SOURCE-RESULTS-20261108.md)
đã lấy và kiểm EZU/SPY/EURUSD03/01/2023. Transport dùng được nhưng metadata
M1 không chứng minh long history, và decoder padding cần source-only view.
LSEG overview đã xác minh16:00 London; calculation PDF vẫn timeout. Chưa có
numeric strategy protocol hoặc PnL R026; các gap bên dưới còn áp dụng.

**Không biến ý tưởng này thành “cuối tháng cứ mua/bán EURUSD”.** Sau khi
[R025 component](US500-TURN-OF-MONTH-COMPONENT-RESULTS-20261108.md) không đạt,
đọc phương pháp của một cơ chế khác trong catalogue. Chưa đăng ký hoặc chạy
PnL mới; R026 vẫn chưa có strategy. Ngày kiểm nguồn:08/11/2026.

## Nguồn thực sự nói gì?

| Nguồn primary | Phần đã đọc | Hệ quả cho project |
|---|---|---|
|[Melvin/Prins, bản tác giả tại ECB,2013](https://www.ecb.europa.eu/events/pdf/conferences/131216/Third_FX_Workshop_MELVIN_PRINS_Equity%20hedging%20and%20exchange%20rates%20Nov%202013.pdf); [bản công bố2015](https://www.sciencedirect.com/science/article/pii/S1386418114000779)|Abstract, giới thiệu và §§2/3/5.1; kết quả hồi quy, chưa đọc toàn appendix|Hedge cuối tháng liên hệ với mức tăng cổ phiếu **tương đối**, đã biết trước phiên cuối tháng. Cần dữ liệu nhiều thị trường, không chỉ US500 hoặc lịch ngày.|
|[Bank of Canada2021-48](https://www.bankofcanada.ca/wp-content/uploads/2021/10/swp2021-48.pdf)|§V.C và §V.E, pp32–35/printed; clock notes|Hiệu ứng fixing hằng ngày khác kênh hedge cuối tháng. Full quoted spreads làm nhiều kết quả âm; không được giảm spread theo kết quả để lấy lại lời.|
|[LSEG WMR methodology v31,11/2026](https://www.lseg.com/content/dam/ftse-russell/en_us/documents/ground-rules/wmr-fx-methodology.pdf)|Version và introduction; đọc tiếp calculation section bị timeout|Không tuyên bố đã rà đủ method hiện hành/lịch sử; giữ gap về calendar/window. Một nến16:00 không tự là WMR benchmark.|
|[BIS,13/02/2015](https://www.bis.org/speeches/20150213-fx-benchmarks)|Đoạn mở rộng cửa sổ fixing|Cửa sổ chuyển một phút sang năm phút từ15/02/2015; không áp nguyên mô tả2013 cho toàn bộ lịch sử.|

Bản2013 dùng mười vùng tiền tệ, chỉ số cổ phiếu toàn thị trường và sample
2004–2012; hồi quy panel lấy chênh lệch với trung bình cross-section. Hướng
hedge dựa trên return tới ngày áp chót, tránh dùng close cuối tháng chưa biết.
Đây là nghiên cứu tác động giá, chưa là bot có SL, spread/commission/latency,
portfolio risk hoặc bằng chứng prop-fit. Bản draft dùng wording GMT; không
đồng nhất với16:00 London có DST khi thiết kế adaptation hiện tại.

## Chưa đủ gì để chạy?

| Phần | Trạng thái hiện tại | Bước nhỏ nhất |
|---|---|---|
|Signal inputs|Chưa có protocol pin chỉ số so sánh của vùng EUR và US, adjusted-return convention/calendar/publication lag|Rà metadata nguồn có sẵn; nếu dùng proxy CFD/ETF phải ghi rõ approximation trước đọc outcome. Không gọi S&P500 là total-market replication.|
|Direction/model|Chưa có mapping bilateral EURUSD từ tín hiệu relative-equity được đóng băng|Chọn adaptation có lý do và baseline; không lấy một coefficient panel làm position size.|
|Event calendar|NYSE calendar không là lịch last WMR fixing; clock source2013 và hiện hành khác phạm vi|Pin lịch công bố WMR/ngày nghỉ/early close và rules từng thời kỳ trước tính outcome.|
|Fills/costs|H1 cache không quan sát đúng window fixing5phút; giá benchmark không là quote gửi lệnh|Dùng observed Bid/Ask có timestamp, delay/fill sau decision và phí của target; không giả được khớp benchmark.|
|Trials/OOS|Các FX versions và2010–2024 đã có exposure ở campaign|Trial mới có version/protocol/consumption riêng; không gọi là clean OOS hoặc mở2025+.|

**Quyết định:** tiếp tục metadata/clock feasibility, chưa code một bot R026
hay tải hàng loạt mười markets. Nếu không có nguồn phù hợp, giữ `deferred`
với lý do, chọn cơ chế khác; không thay bằng lịch mua/bán vô điều kiện rồi
gắn tên paper. Research này không sửa bot, risk, costs, global skills hoặc
quyền broker. C1/C2 vẫn đang mở.

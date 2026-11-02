# Ưu tiên thị trường cho hệ thống AI

Khảo sát ngày 02/11/2026. **Khuyến nghị để owner xem xét, chưa là quyết định chọn
thị trường hoặc quyền giao dịch.** Liên quan [brief kiến trúc](AUTONOMOUS-TRADING-SYSTEM-BRIEF.md).
Không cài tool, chạy provider, tải thêm dataset hoặc thay runtime trong khảo sát này.

## Kết luận

Ưu tiên **BTC/ETH spot, long/cash, khung ngày** cho workflow nghiên cứu đầu tiên.
Forex là nhánh mở rộng hợp lý, đặc biệt khi mục tiêu chuyển sang broker demo/MT5
hoặc có giả thuyết về tiền tệ được kiểm chứng. Đây là lựa chọn theo khả năng xây,
kiểm tra và vận hành trong workspace hiện tại; chưa chứng minh crypto có lợi
nhuận cao hơn hoặc LLM có edge tốt hơn ở thị trường này.

Spot ở đây là mua tài sản bằng vốn có, không vay, không short, không perpetual.
Forex trong so sánh là cặp tiền chính qua retail broker; vàng XAUUSD/CFD là một
nhánh sản phẩm riêng, có contract/chi phí riêng. Kết luận không đại diện cho
currency futures, mọi loại crypto hoặc mọi broker/sàn.

## Bằng chứng và đánh giá

| Tiêu chí | BTC/ETH spot | Forex retail |
|---|---|---|
| Data nghiên cứu | Binance công khai OHLCV/trades dạng daily/monthly và checksum; volume là giao dịch của venue đó, không là toàn thị trường [1] | Có nguồn bid/ask/mid như OANDA; volume nến tại OANDA là số cập nhật giá, không là tổng khối lượng Forex [2] |
| Tự động hóa | API exchange hỗ trợ dữ liệu và lệnh; cần kiểm semantics và khả năng truy cập từng venue [3] | API broker hỗ trợ automation; OANDA có practice và live riêng, nên Forex không thiếu đường triển khai AI [4] |
| Mô phỏng ban đầu | Long/cash không margin có ít trạng thái accounting hơn sản phẩm margin; là đánh giá engineering | Cần mô hình đúng bid/ask, phí, financing/swap và margin theo broker; financing có thể là khoản thu hoặc chi [2][5] |
| Vận hành | Thị trường 24/7 tạo cả nhu cầu giám sát cuối tuần | Thường có phiên nghỉ cuối tuần; vẫn có gap và lịch nghỉ theo broker [6] |
| Rủi ro riêng | Giá, thanh khoản, exchange/custody, quote asset và API; không leverage vẫn có thể mất phần lớn vốn | Giá, broker/counterparty, margin và execution; OTC retail không là giao dịch trên một sở tập trung [7] |
| Tài sản workspace | Quant Lab đã có accounting long/cash, dữ liệu lịch sử và pilot NAQ-6; Hermes đã phản biện dossier | Trader có nền MT5; contract research/chi phí/validation tương đương cho workflow này chưa được chứng minh qua pilot vừa rồi |

Nhận định ưu tiên crypto là suy luận từ những yếu tố trên và source hiện tại,
không phải kết quả benchmark hai thị trường trên cùng risk budget. Không lấy
việc project đã có crypto làm bằng chứng thị trường đó tốt hơn về đầu tư.

## AI có vai trò gì?

Hai thị trường đều có thể dùng AI nghiên cứu giả thuyết, viết candidate, tổng hợp
thông tin và phản biện. Khối tính P&L, kiểm timing, risk và đối soát cần contract
và code kiểm chứng được. Việc thêm nhiều LLM agents không tự tạo lợi thế giao dịch.
Khảo sát này chưa tìm được bằng chứng so sánh đáng tin để kết luận LLM có lợi
nhuận bền vững cao hơn ở một trong hai thị trường.

Khung ngày là đề xuất cho bài toán hiện tại: tần suất quyết định thấp hơn làm
giảm áp lực latency, chi phí inference và vận hành. Đổi lại số quan sát giao dịch
mới tích lũy chậm; một đợt paper ngắn không đủ chứng minh edge. H4 có thể khảo sát
sau nếu giả thuyết yêu cầu; không mặc định thêm tần suất để kiếm thêm lợi nhuận.

## Cách quyết định dài hạn

1. Hoàn tất một workflow trên BTC/ETH spot với dữ liệu có provenance, quy tắc và
   tiêu chí chọn/loại được chốt trước khi xem kết quả mới.
2. So với cash và buy-and-hold cùng timing/cost, có OOS/walk-forward và cost stress.
   Pilot NAQ-6 đã hoàn thành workflow nhưng candidate chưa qualified; không dùng
   dossier cũ để tune rồi coi nó là holdout mới.
3. Quan sát paper bằng dữ liệu thị trường thật và simulated fills, phân biệt với
   test API. Ví dụ Coinbase Advanced Trade sandbox trả static mocked responses;
   kết nối sandbox thành công không chứng minh chiến lược có lợi nhuận [8].
4. Khi mở Forex, giữ cùng quy trình đánh giá, nhưng data adapter, cost model,
   margin/accounting và execution contract phải đúng sản phẩm. So chiến lược ở
   mức rủi ro tương đương sau mọi chi phí, độ ổn định và công sức vận hành.
5. Có thể ưu tiên Forex sớm hơn nếu owner chốt mục tiêu MT5/broker demo hoặc prop
   firm và quy định nơi đó thực sự cho phép workflow dự định. Không nghiên cứu
   song song hai stack đầy đủ chỉ để có đủ lựa chọn.

Lựa chọn sàn/broker để dùng tiền thật là quyết định riêng. Với người cư trú Việt
Nam, cần kiểm tư cách venue, sản phẩm, API và nghĩa vụ hiện hành trước deployment.
Giải đáp trên Cổng TTĐT Chính phủ, đối chiếu ngày 02/11/2026, dẫn quy tắc sáu tháng kể từ giấy phép tổ
chức dịch vụ tài sản mã hóa đầu tiên theo Nghị quyết 05/2025/NQ-CP [9]. Khảo sát
này chưa xác minh ngày giấy phép đầu tiên hoặc kết luận một venue cụ thể được
phép cho owner sử dụng; nguồn dữ liệu public không tự là đề xuất mở tài khoản.

## Nguồn chính thức đã đối chiếu

1. [Binance public data](https://github.com/binance/binance-public-data): format,
   lịch xuất bản, checksum và lịch sử thay thế archive. Checksum chứng minh bytes,
   không tự bảo đảm point-in-time vintage hoặc không có lỗi dữ liệu.
2. [OANDA candlestick definitions](https://developer.oanda.com/rest-live-v20/instrument-df/).
3. [Coinbase Exchange API](https://www.coinbase.com/developer-platform/products/exchange-api).
4. [OANDA practice/live endpoints](https://developer.oanda.com/rest-live-v20/development-guide/).
5. [OANDA financing](https://www.oanda.com/us-en/trading/financing-fees/): điều khoản
   của OANDA US, là ví dụ cần mô phỏng financing, không áp nguyên tỷ lệ cho broker khác.
6. [OANDA operating hours](https://www.oanda.com/us-en/trading/hours-of-operation/):
   minh họa lịch Forex và crypto, có maintenance/holiday exceptions.
7. [CFTC: OTC Forex](https://www.cftc.gov/LearnAndProtect/AdvisoriesAndArticles/CustomerAdvisory_MustKnowForex.html):
   cấu trúc retail dealer và margin; không suy rộng thống kê thua lỗ sang AI hoặc crypto.
8. [Coinbase Advanced Trade sandbox](https://docs.cdp.coinbase.com/coinbase-app/advanced-trade-apis/sandbox).
9. [Giải đáp chính sách của Chính phủ](https://chinhsachonline.chinhphu.vn/giao-dich-tai-san-ma-hoa-khong-qua-to-chuc-duoc-cap-phep-co-the-bi-xu-ly-92252.htm).

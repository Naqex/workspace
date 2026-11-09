# Khảo sát bot trả phí cho mục tiêu prop — 09/11/2026

## Kết luận và phạm vi

Nên khảo sát bot thương mại để học cơ chế, tiêu chuẩn sản phẩm và tìm ứng viên
để kiểm tiếp. Chưa có cơ sở mua một bot trong danh sách này để chạy challenge.
Giá bán là giá phần mềm/hỗ trợ, không là bằng chứng có edge. Bot miễn phí vẫn
cần kiểm như bot trả phí; giá không đủ để phân biệt chất lượng.

Đây là desk research theo yêu cầu riêng của owner trong khi Goal đang paused.
Không mua, đăng ký, tải/chạy EA, mở dữ liệu holdout của project hoặc gọi broker.
Không thêm các sản phẩm được khảo sát vào catalogue 81 hồ sơ như trial đã chạy.
Nguồn kiểm ngày 09/11/2026; giá hiển thị có thể khác checkout/thuế/khuyến mãi.
Danh sách là mẫu khảo sát, không là bảng xếp hạng doanh số hoặc lợi nhuận.

## Gate luật quỹ trước giá và lợi nhuận

| Quỹ | Nguồn chính thức hiện hành | Ý nghĩa với lựa chọn |
|---|---|---|
| FTMO CFD | Cho phép EA trong giới hạn giao dịch hợp lệ; cảnh báo EA bên thứ ba có thể trùng chiến lược với người khác, liên quan maximum capital allocation | Không cấm mọi EA mua ngoài; cũng không tự động chấp nhận vì vendor ghi “FTMO” |
| The5ers CFD | Trang prohibited practices, cập nhật 03/11/2026, liệt kê EA không sở hữu source code và EA bên thứ ba mở giao dịch giống trader khác | License chạy phần mềm chưa chứng minh quyền sở hữu source. Phải giải quyết gate này trước dùng bot đóng mã |

Nguồn: [FTMO strategies FAQ](https://ftmo.com/faq/which-instruments-can-i-trade-and-what-strategies-am-i-allowed-to-use/),
[The5ers prohibited practices](https://the5ers.com/faqs/prohibited-trading-practices/).
The5ers còn cấm khai thác feed lúc rollover; không suy ra mọi giao dịch ban đêm
đều bị cấm. Đổi lot/magic number không chứng minh chiến lược độc lập hoặc hợp lệ.
Đây là phạm vi CFD, không gộp luật Futures.

## Sản phẩm và chi phí

| Bot | Giá USD hiển thị | Cách hoạt động / nền tảng theo vendor | Nhận định cho project |
|---|---|---|---|
| [Forex Fury](https://www.forexfury.com/shop/) | Gold 249,99; Diamond 459,99, lifetime | Nhiều preset, có scalping; MT4/MT5. Gold 1 / Diamond 2 live licenses | Giá vào thấp hơn các bundle; chưa xác minh edge của bản Core hiện tại. Cần đo spread/slippage và tail loss |
| [Forex Flex EA](https://forexflexea.com/) | 349,47 cho 1 MT5 hoặc MT4; 499,95 gói 2 MT4+MT5 | Nhiều strategy/set file; có grid/progressive; dùng virtual trades để tìm entry | Không thể đánh giá mọi preset như một strategy. Ưu tiên xem lot progression, basket loss và stop thực tế |
| [WallStreet Forex Robot 3.0](https://www.wallstreet-forex.com/) | Starter 197; Pro 357; Premium 437, one-time | 3.0 dùng M15; FAQ xác nhận MT4; gói lớn kèm các EA khác | Chưa xác nhận MT5, không khớp trực tiếp stack hiện tại. Không gán cơ chế Recovery PRO cho bản 3.0 |
| [Waka Waka](https://www.valerytrading.com/products/waka-waka) | Thuộc portfolio bên dưới | Grid, 3 cặp FX, M15; MT4/MT5 | Tham khảo risk của basket; chưa là ứng viên challenge |
| [Perceptrader AI](https://www.valerytrading.com/products/perceptrader-ai) | Thuộc portfolio bên dưới | Grid có AI, 6 cặp FX, M5; MT4/MT5 | Nhãn AI không chứng minh lợi thế; không tính như cơ hội độc lập chỉ vì tên khác Waka |
| [Night Hunter Pro](https://www.valerytrading.com/products/night-hunter) | Thuộc portfolio bên dưới | Night scalper, 12 cặp, M5; MT4/MT5; vendor ghi không grid và nhạy slippage | Đáng đọc cơ chế hơn cho nhánh không grid; chưa đủ bằng chứng mua/chạy quỹ |

[ValeryTrading pricing hiện tại](https://www.valerytrading.com/pricing):
6 EA giá 1.497 USD/năm hoặc 4.997 USD một lần. Vendor công bố trial demo
14 ngày không thẻ và hoàn tiền 30 ngày; chưa kiểm thực tế điều kiện checkout/
refund. “Own” là tên gói truy cập vĩnh viễn, chưa chứng minh sở hữu mã nguồn.
Shop cũ có giá riêng từng EA và dữ liệu cũ; không dùng lẫn với portfolio hiện tại.

Fury [trang chính thức](https://www.forexfury.com/) công bố preset scalping,
MT4/MT5 và số license ở trên; trang chủ truy cập không ổn định trong lượt kiểm,
shop chính thức đọc được. Không kết luận bản hiện tại có cùng hành vi các bản cũ.

## Hiệu suất: đã kiểm đến đâu?

Vendor Valery hiển thị max DD Waka 23,84%, Perceptrader 21,96%, Night Hunter
13,92%. Đây là số do vendor trình bày, **chưa đối soát tracker**; không dùng để
tính xác suất pass. Ba link Myfxbook chính thức đều trả 403 trong lượt này:

- [Waka #12286158](https://www.myfxbook.com/members/MischenkoValeria/waka-waka-original/12286158).
- [Perceptrader #10168303](https://www.myfxbook.com/members/MischenkoValeria/pai-unique-mode-no-limits/10168303).
- [Night Hunter #8562210](https://www.myfxbook.com/members/MischenkoValeria/night-hunter-pro-all-pairs/8562210).

Không đổi sang tài khoản khác mà giữ số thống kê của tài khoản cũ. Bài review
và trang affiliate có số DD khác rất lớn; chưa thống nhất account/version/risk/
balance-vs-equity nên không nhập các con số đó thành “DD thật” của mọi bản bot.

Theo [Myfxbook verification](https://www.myfxbook.com/help/knowledge-base/verification/),
track record xác nhận lịch sử hiển thị khớp lịch sử broker; trading privileges
xác nhận người kết nối có quyền/master password. Suy luận giới hạn: hai badge
không kiểm toán code, không chứng minh mọi preset đang bán, luật quỹ hay lợi
nhuận tương lai. Cần xem cả lỗ đang mở, lot, deposit/withdrawal, ngày cập nhật
cuối và phiên bản/preset gắn với account.

Ngay cả nếu các DD vendor nêu được xác nhận, cần đánh giá lại dưới sizing và
luật đúng chương trình challenge. Không thể lấy DD vốn riêng rồi suy ra hợp
quỹ; giảm lot có thể đổi thời gian đạt target và vẫn cần kiểm lại đường equity.

## Cộng đồng nói gì?

Đây là tự thuật/chẩn đoán để tìm câu hỏi cần kiểm, không là thống kê đại diện.

| Nguồn / thời gian | Điều đáng học | Giới hạn |
|---|---|---|
| [Reddit Forex Fury, 2022–2024](https://www.reddit.com/r/Forex/comments/vo4trt/) | Có người báo có lời, có người lỗ; phản hồi đề cập RR xấu, SL lớn và tác động settings. Có người khen Flex khi dùng risk thấp | Bản cũ, lời kể chưa audit; không áp nguyên verdict cho Core 2026 hoặc chấp nhận khuyến cáo “không trade thứ Sáu” làm rule chung |
| [Reddit MT5 EAs, 2026](https://www.reddit.com/r/Forex/comments/1th5mn9/looking_for_real_longterm_experiences_with_mt5_eas/) | Người dùng Perceptrader nói có lời và DD từng khoảng 22%; sau đó cho biết account đã dùng EA khác trước 2025 | PnL toàn account không thể gán hết cho một bot; link account không truy cập được trong lượt này; số liệu chỉ là tự thuật |
| [Reddit Waka, 12/2025](https://www.reddit.com/r/Forex/comments/1pchbar/1_months_profit_from_a_400_deposit/) | Người đăng báo một tháng lời lớn sau gần năm chỉnh settings | Một tháng và nhiều tuning không chứng minh bền vững; kết quả đẹp có thể đã qua nhiều lựa chọn |
| [Brainyforex tự chạy WallStreet 2.0, 2017](https://www.brainyforex.com/brainyforex-tested-wallstreet-forex-robot-20.html) | Tác giả báo demo 100 ngày: 102 lệnh, 73 thắng, tổng vẫn lỗ; nêu vấn đề VPS/execution | Bản 2.0, rất cũ, chưa audit; chỉ minh họa winrate cao không đảm bảo lời, không phán bản 3.0 |

Các review SEO/affiliate của The Robotic Trader, AlgoTradingSpace và các bảng
“best EA” có thể giúp tìm link gốc. Không dùng chúng làm bằng chứng mua/ranking.
Một số review tự nói không mua/chạy sản phẩm; testimonial trên website vendor
cũng là nội dung vendor chọn. Không suy ra bot nào cũng lừa đảo từ Reddit,
hoặc bot bán ra chắc chắn không có edge.

## Cách tham khảo có ích cho mình

1. Giữ survey này như nguồn ý tưởng, chưa mua bot. Nếu chọn khảo sát sâu:
   Night Hunter cho cơ chế không grid, Fury cho preset scalp giá thấp hơn;
   **đây là ưu tiên audit, không xếp hạng hiệu suất**. Flex chỉ đáng đi tiếp khi
   xác định được preset và quyền kiểm độc lập; không mua bundle chỉ vì nhiều bot.
2. Với The5ers, ưu tiên chiến lược/code mình sở hữu hợp pháp; nếu thuê viết,
   hợp đồng phải rõ source/ownership. Sở hữu code chỉ giải quyết một gate,
   không bảo đảm tuân thủ toàn bộ luật hoặc edge. Chưa gửi hỏi vendor/quỹ.
3. Trước trả tiền: chốt version/preset; đầy đủ entry/exit/sizing hoặc quyền
   kiểm đủ; SL/basket cap/lot progression; exact tracker và open equity;
   broker/cost/DST/news; giấy phép/source; trial/refund và xác nhận phù hợp
   từ chính quỹ khi còn điểm chưa rõ. Vendor ghi “prop set” không thay quỹ.
4. Nếu qua các gate, đưa **một preset cố định** vào protocol có phí và luật
   quỹ; giữ cả kết quả fail. Sau backtest/kiểm chéo mới demo forward theo
   quyền được cấp; không cần mua nhiều bot để thử cùng lúc từ đầu.

[MQL5 Market rules](https://www.mql5.com/en/market/rules) phân biệt demo tester
với chạy chart online: demo EA Market chỉ test trong Strategy Tester, khác
trial demo online do vendor tự cấp. Mua Market không chuyển quyền sở hữu sản
phẩm, không cho decompile; MetaQuotes không bảo đảm lợi nhuận. Không tải crack,
leaked source hoặc coi file .ex5 là source sở hữu. Chưa kiểm code/quyền network/
DLL của bất kỳ bot nào trong survey.

## Bước tiếp và điều kiện cập nhật

Khuyến nghị hiện tại: chưa chi tiền; dùng khảo sát để chọn cơ chế minh bạch và
quyền sở hữu phù hợp. Nếu owner chọn một sản phẩm, audit sâu đúng version và
exact account trước quyết định trial/mua. Refresh giá, terms, firm/program và
tracker trước hành động; nếu tracker còn bị chặn, giữ performance unknown.
Chiến dịch tìm edge hiện hữu vẫn paused; survey này không thay verdict của
81 hồ sơ nghiên cứu hoặc chứng nhận challenge-ready.

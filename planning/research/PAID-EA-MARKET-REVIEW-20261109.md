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

**Cập nhật khảo sát sâu cùng ngày:** xem [Night Hunter / Fury](#khảo-sát-sâu-night-hunter-pro-và-forex-fury--09112026).
Fury CORE có grid tùy chọn; Night Hunter có kênh mua riêng MQL5 và thống kê
signal MQL5 đọc được. Những bổ sung này thay phần shortlist/giới hạn tương ứng
bên dưới; việc Myfxbook trả 403 vẫn giữ nguyên, chưa kiểm raw ledger hoặc EA.

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
| [Forex Fury](https://www.forexfury.com/shop/) | Gold 249,99; Diamond 459,99, lifetime | MT4/MT5, nhiều preset; CORE 2026 thêm grid bật/tắt được. Gold 1 / Diamond 2 live licenses | Giá vào thấp hơn bundle; phải chốt preset/grid/SL trước đánh giá. Chưa xác minh edge CORE |
| [Forex Flex EA](https://forexflexea.com/) | 349,47 cho 1 MT5 hoặc MT4; 499,95 gói 2 MT4+MT5 | Nhiều strategy/set file; có grid/progressive; dùng virtual trades để tìm entry | Không thể đánh giá mọi preset như một strategy. Ưu tiên xem lot progression, basket loss và stop thực tế |
| [WallStreet Forex Robot 3.0](https://www.wallstreet-forex.com/) | Starter 197; Pro 357; Premium 437, one-time | 3.0 dùng M15; FAQ xác nhận MT4; gói lớn kèm các EA khác | Chưa xác nhận MT5, không khớp trực tiếp stack hiện tại. Không gán cơ chế Recovery PRO cho bản 3.0 |
| [Waka Waka](https://www.valerytrading.com/products/waka-waka) | Thuộc portfolio bên dưới | Grid, 3 cặp FX, M15; MT4/MT5 | Tham khảo risk của basket; chưa là ứng viên challenge |
| [Perceptrader AI](https://www.valerytrading.com/products/perceptrader-ai) | Thuộc portfolio bên dưới | Grid có AI, 6 cặp FX, M5; MT4/MT5 | Nhãn AI không chứng minh lợi thế; không tính như cơ hội độc lập chỉ vì tên khác Waka |
| [Night Hunter Pro](https://www.valerytrading.com/products/night-hunter) | Website: portfolio; [MQL5 MT5](https://www.mql5.com/en/market/product/68327): 2.800 riêng EA | Night scalper M5, MT4/MT5; website 12 cặp, marketplace/record 9; vendor ghi không grid | Có thống kê MQL5 để audit tiếp; chưa đủ bằng chứng mua/chạy quỹ |

[ValeryTrading pricing hiện tại](https://www.valerytrading.com/pricing):
6 EA giá 1.497 USD/năm hoặc 4.997 USD một lần. Vendor công bố trial demo
14 ngày không thẻ và hoàn tiền 30 ngày; chưa kiểm thực tế điều kiện checkout/
refund. “Own” là tên gói truy cập vĩnh viễn, chưa chứng minh sở hữu mã nguồn.
Kênh MQL5 hiện vẫn có giá riêng Night Hunter; điều kiện license/trial/refund
khác website, không áp điều kiện portfolio sang marketplace.

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
   Night Hunter cho cơ chế vendor mô tả không grid; Fury cần hạ ưu tiên cho
   tới khi xác định preset CORE và trạng thái grid/SL (xem khảo sát sâu);
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
quyền sở hữu phù hợp. Đã research sâu public evidence NHP/Fury ở dưới; nếu đi
tiếp, cần exact build/preset và quyền kiểm hợp pháp trước trial/mua. Refresh
giá, terms, firm/program và tracker trước hành động; tracker còn bị chặn thì
giữ số hiện hành của đúng account đó unknown.
Chiến dịch tìm edge hiện hữu vẫn paused; survey này không thay verdict của
81 hồ sơ nghiên cứu hoặc chứng nhận challenge-ready.

## Khảo sát sâu Night Hunter Pro và Forex Fury — 09/11/2026

Owner giao research sâu hai sản phẩm, chưa cần tự tìm thêm. Đây là cập nhật
public evidence, không numerical trial mới; không resume Goal. Đã đọc một
file cấu hình công khai dưới dạng text trong bộ nhớ; không lưu/chạy EA,
đăng ký trial, mua hàng hoặc gửi hỏi vendor/quỹ.

### So sánh để quyết định

| Mục | Night Hunter Pro | Forex Fury CORE |
|---|---|---|
| Cơ chế công khai | Vendor: scalp lúc yên, pending orders, không grid/martingale, SL từng lệnh | Release CORE 12/02/2026: thêm grid bật/tắt được; không suy mọi preset đều bật |
| Điểm kiểm được | MQL5 signal lâu năm và preset public | Release/giá/refund; hai tracker CORE tìm được nhưng đều 403 |
| Điểm còn hở | Executable/preset hiện bán có tái hiện record MT4 không; equity path đầy đủ | Exact build/preset/grid/lot progression/SL và kết quả hiện hành chưa audit |
| Kết luận | Ưu tiên nghiên cứu hơn Fury vì bằng chứng dễ kiểm hơn, không là xếp hạng lợi nhuận | Hạ ưu tiên so với shortlist ban đầu; chưa nên mua chỉ vì giá thấp |
| Cả FTMO và The5ers | Chưa qua gate quyền sở hữu source/luật, chưa challenge-ready | Cùng vướng gate source; chưa challenge-ready |

### Night Hunter: record khác với quảng cáo thế nào?

[Signal 856907](https://www.mql5.com/en/signals/856907) hiển thị MT4,
ICMarketsSC-Live24, bắt đầu 27/10/2020, 2.185 lệnh: thắng 67,55%, PF 1,22;
lệnh thắng trung bình 0,64 AUD, thua −1,10 AUD, payoff +0,08 AUD. Khoảng
10 lệnh/tuần, giữ trung bình 11 giờ: tên scalp không có nghĩa mọi lệnh đóng
trong vài giây. Trang cảnh báo 80% growth tập trung trong 35 ngày.

Các nhãn DD trên chính trang khác nhau: `Drawdown by balance / Maximal`
59,70 AUD (22,13%); `Relative / By Balance` 13,91% (59,70 AUD);
`Relative / By Equity` 11,86% (12,51 AUD). Không gộp thành một “DD thật”,
không so trực tiếp với ngưỡng daily/static của quỹ.

Đây là aggregate platform hiển thị, chưa audit raw ledger, phí đầy đủ hoặc
mapping version/preset. MT4 record không chứng minh MT5 6.74 chạy giống;
không ngoại suy growth thành xác suất pass. Myfxbook #8562210 vẫn chưa đọc
được; chưa xác minh hai tracker chính xác là cùng account.

[MQL5 MT5 listing](https://www.mql5.com/en/market/product/68327) ghi v6.74,
08/02/2026, 2.800 USD/10 activations; yêu cầu hedging account, có Hide SL,
lọc news/rollover và WebRequest phục vụ giờ/tin. Đây là mô tả vendor, chưa
kiểm runtime/network của binary. “Tested for FTMO” chưa là xác nhận của FTMO.
[Website](https://www.valerytrading.com/products/night-hunter) ghi 12 cặp,
nhưng listing và signal ghi 9; chưa coi lịch sử 9 cặp là bằng chứng cho 12.

### Preset công khai: đọc được gì, chưa được gì?

Signal dẫn [NHP_AllPairs_MPR20.set](https://c.mql5.com/31/689/NHP_AllPairs_MPR20.set).
Web reader không hỗ trợ content-type; đọc trực tiếp HTTPS dưới dạng text,
không thực thi: 1.362 byte, SHA256
`0f9307191d4b0602e1d62294b21756b38cdaaa205c298317fe6d65115cd87193`.
Đây là file tại thời điểm kiểm, không chứng minh preset giữ nguyên suốt record.

| Trường đã đọc | Diễn giải có giới hạn |
|---|---|
| `LotSizingMethod=0`, fixed 0.01, risk field 5.0 | Chưa xác minh enum của build tạo file. Không kết luận account thực sự risk 5% vì field có thể không active |
| `MaximumSymbols=5`, `MaximumCurrencies=2` | Có giới hạn danh nghĩa; chưa chứng minh tổng exposure/risk của lệnh đang mở |
| `MaximumDrawdown=100.0`, money 0.0 | Không thấy cấu hình giới hạn daily loss/reset theo quỹ; chưa xác nhận semantics 0 và action enum |
| `Stop_Loss=0.0`, `HideSL=false` | Không suy SL bị tắt: guide mô tả SL mặc định riêng từng cặp. Cần order history và build để xác nhận |
| `MinimumPriceRange=20`, SmartTime/rollover/news true | Xác nhận các input trong file, chưa chứng minh bộ lọc hoạt động hoặc nguồn ngoài luôn có sẵn |

[Guide của tác giả](https://www.mql5.com/ru/blogs/post/745616), đăng 2021,
có thể đã được sửa: lot modes chỉ dùng field tương ứng; floating-DD guard
có phạm vi account/strategy, không tự là daily-loss guard tính cả realized
và reset đúng giờ quỹ. Guide nói pending fill ít phụ thuộc VPS; suy luận
kỹ thuật: hủy/sửa/thoát và hidden SL vẫn cần terminal/kết nối, nên không coi
pending order là thay thế cho vận hành an toàn. Chưa dùng guide cũ để xác
nhận default hiện tại; không tải ZIP không liên quan được đính kèm ở đó.

### Fury: thay đổi quan trọng và những gì chưa xác minh

[CORE announcement](https://www.forexfury.com/forex-fury-core-2026/) xác nhận
grid là tùy chọn và có preset mới cho S&P500/FX. Không đủ để gọi Fury một
chiến lược duy nhất không grid. Preset tắt grid cũng cần kiểm độc lập.

[Shop](https://www.forexfury.com/shop/) vẫn hiển thị Gold 249,99 / Diamond
459,99 USD. [Refund policy](https://www.forexfury.com/return-policy/): trong
14 ngày, cần email đơn hàng/lý do và ảnh setup/sử dụng; additional licenses
không hoàn tiền. Không coi unlimited demo licenses sau mua là free trial.

[ATI review](https://algotradingindex.com/algorithms/forex-fury-review/)
chỉ dùng để tìm hai link tracker:
[CORE low risk #12008967](https://www.myfxbook.com/members/forexfuryreal/fury-core-low-risk/12008967),
[CORE low risk 2 #12008966](https://www.myfxbook.com/members/forexfuryreal/fury-core-low-risk-2/12008966).
Cả hai trả 403 ngày kiểm; chưa lấy số review tháng 9 làm số hiện hành.
Không gán tài khoản GOLD/TradeWithPAT hoặc bản V4/V6 cho CORE đang bán.
FAQ/terms có lúc timeout; chưa kiểm được toàn bộ điều kiện bằng mua thực tế.

### Cộng đồng: dùng làm câu hỏi kiểm, không làm verdict

| Nguồn | Phản hồi đọc được | Giới hạn |
|---|---|---|
| [NHP MQL5 MT4 reviews](https://www.mql5.com/en/market/product/66358), Emmanuel Martinez, 14/04/2025 | Nói kết quả phụ thuộc broker/settings; một lỗ có thể xóa thành quả tháng, tự thay cặp | Tự thuật, chưa ledger. Không nhận tuning hoặc câu “EA sống 6 tháng” của reviewer làm quy luật |
| [Fury Trustpilot](https://www.trustpilot.com/review/forexfury.com), Jay V, 21/07/2026 | Nói CORE demo tăng 49% hơn một tháng | Tự thuật ngắn hạn, không audited; Verified review không xác minh PnL |
| Cùng trang, Christopher Bever, 22/10/2026 | Nói một lỗ xóa nhiều lãi nhỏ | Không nêu exact build/preset; không gán chắc cho CORE hoặc mọi user |

Reddit cũ trong survey vẫn hữu ích để hỏi về tail loss/settings; chưa tìm
được evidence đủ mạnh để kết luận cộng đồng đồng thuận về CORE 2026.
Không dùng rating/affiliate ranking thay executable/preset/account audit.

### Quyết định và phần owner có thể giúp sau này

Chưa mua hai bot. [The5ers](https://the5ers.com/faqs/prohibited-trading-practices/)
hiện liệt kê EA không sở hữu source, trade trùng bên thứ ba và khai thác feed
rollover trong prohibited practices. Không suy mọi night scalper bị cấm.
[FTMO](https://ftmo.com/faq/which-instruments-can-i-trade-and-what-strategies-am-i-allowed-to-use/)
cho EA có điều kiện, cảnh báo trùng strategy/capital allocation. Chưa có xác
nhận riêng cho hai preset; sửa magic/lot không giải quyết quyền hoặc hành vi.

Nếu đi tiếp, hỏi vendor đúng build/preset, lịch sử đầy đủ và nguồn quyền dùng;
hỏi quỹ exact setup còn mơ hồ, rồi mới quyết định trial. Chưa gửi các câu hỏi.
Website Night Hunter quảng bá trial 14 ngày; terms link `/terms` không truy
cập được nên chưa xác nhận đầy đủ điều kiện. [MQL5 rules](https://www.mql5.com/en/market/rules)
chỉ cho demo Market chạy tester; không chuyển source ownership khi mua.

Owner chưa cần tự research sâu. Chỉ khi có quyền hợp pháp, manual/preset/
trade export và trả lời vendor/quỹ mới bổ sung phần public research không
thấy; không cần đưa password/key. Với mục tiêu cả hai quỹ, tiếp tục ưu tiên
code sở hữu hợp pháp; có thể học cơ chế công khai rồi tự thiết kế và kiểm
định, không sao chép/decompile logic đóng mã hoặc coi đó là đã chứng minh edge.

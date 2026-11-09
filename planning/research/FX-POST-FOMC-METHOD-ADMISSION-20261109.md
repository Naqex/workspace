# EURUSD sau FOMC: đọc phương pháp trước khi thử quy tắc

09/11/2026, sau [R087](JAPAN-US-CASH-REACTION-RESULTS-20261109.md).
**Chưa chạy PnL mới.** Ưu tiên kiểm giả thuyết có đầu vào quan sát được và
chi phí tái hiện; không dùng surprise dataset2024 làm tín hiệu sẵn có2019.

## Gold/account-spec: kiểm local đã xong, chưa định giá lại

Đối chiếu receipt cũ với file private FTMO `ftmo-current-spec-20261102/spec.json`:
SHA `930e5670b21b09963d21741258706adeff6b10c454dd9fafa0df7346a0a74756`
vẫn khớp, chỉ EURUSD. Không có XAU/US500 spec trong file này. Process query
`terminal64.exe` không trả terminal đang chạy lúc kiểm; native owner manifest
standardpath cũng không có. Không đoán account/path/port, initializeSDK,
restart/reconnect, OrderCheck/OrderSend hoặc mở account để lấy thêm.

[Gold cost gap](GOLD-TARGET-COST-ADMISSION-20261109.md) giữ nguyên: chưa đủ
point/mode/multiplier đúng symbol/account để chuyển publicswappoints thành
cashfee. Không gọi snapshot EURUSD là hợp đồng vàng hoặc dùng Exness thay
FTMO. Đây là kiểm cachedspec, không xác minh lại connection/rate hiện tại.

## Nguồn phương pháp và phiên bản

| Nguồn đã đọc | Scope / phần giúp quyết định |
|---|---|
|[Wang thesis2018, chapter1](https://www.olsendata.com/data_products/client_papers/papers/201808-MinhoWang-EssaysOnCurrencyMarkets.pdf)|Đọc PDFpages13–50, đặc biệt20–22/25/31: dữ liệu15min midpoint, nhiều currency, excessreturn có lãi suất; window12h. Không tradableCFDnet hoặc proof riêng EURUSD saufee |
|[Xu discussant11/03/2022](https://www.nancyxu.net/_files/ugd/efd0b7_99257144559d4b61b592862dc067edfe.pdf)|Đọc slides về12–24h và critique phân biệt jump/trend; đây là discussion, không current paper/code |
|[Lee/Wang SSRN4386170](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4386170)|Primary search-served abstract; direct403. Chưa fullcurrentmethod, không lấy abstract điền parameters |
|[Rosa2011 publisher](https://www.sciencedirect.com/science/article/pii/S0378426610003407)|Primary abstract nói price absorption30–40min; đó không chứng minh continuation strategy sau30min |

Hai bản Wang2018 và discussion2022 có cách mô tả positive/negative jump khác
nhau. **Không trộn thành predictor.** Phần chung12–24h chỉ là motivation;
nhánh jump/factor/interest-rate replication chưa admitted. Paperportfolio
và EURUSD đơn lẻ khác nhau. Source Olsenmid cũng khác observed Dukascopy
BidAsk; không import headlineperformance hoặc excessreturn làm cashPnL.

Thesis dùng mốc14:15 cho mẫu cũ; không sao chép sang2019/2022. Accepted
[R062 calendar](FOMC-NASDAQ-COMPONENT-PROTOCOL-20261108.md) đã đối chiếu
16scheduled events14NY với datedFedpublications. Ownadaptation phải dựa
đúng timestamp đó. Không exclude exceptionalevents theo outcome hoặc chọn
policy-direction từ thông tin chưa biết lúc quyết định.

## Hướng được chọn và giới hạn

Ưu tiên **calendar-conditioned SELL EURUSD12–24h sau FOMC**, chưa jumpfilter:
sourceinputs rõ, window nằm trong ngày FX nên declaredrollover17NY không
nằm trongholding. Đây là một sleeve tần suất8events/năm; tự nó chưa giải
quyết time-fit3/6/12months. Liên quan FOMC/event và preECB/sessionflow R021,
không cơ hội độc lập mới chỉ vì thêm eventmask hoặc đổi thị trường.

Ownrecipe là câu hỏi bác bỏ được, không paperreplication. Nếu đi tiếp, freeze
entry/exit/control/cost/sourcegap/gate trước quotes/PnL. Không dùng initial
reaction sign khi currentjumpmethod chưa rõ. Không dùng shortswapcredit,
swapfree hoặc giảmfunding để cứu mẫu cũ; không SL/accountpolicy từ component.

## PDF/provenance và lỗi công cụ

Private `execution-v1/fx-post-fomc-method-v1/` trong campaign rootE: giữ
hai PDF personalreference, receipt, text và renderedpage21thesis/page5discussion.
Visual đã kiểm hướng tỷ giá USD/foreign, midpoint/excessreturn và window;
không redistribute PDF/images trong repo. HaiGET tải thành công15,780s tổng
theo perrequest (receiptwall riêng), không marketdataset hoặc2025holdout.

- Thesis200pages,12.846.815B,SHA`39662026c101d39062d804ec3f7219f4904ddb94c44404ab7f367fccd401ea06`.
- Discussion17pages,737.848B,SHA`7e7debbddac0465d3fcbae12d0123e98574cb7d1cf0a49ee7a611a6b15642629`.

Pypdf extraction có Type1/fontTools warnings; không suy formula từ text lỗi.
Poppler`pdftoppm` render thành công; `pdftotext` không có trênPATH hoặc bundle
được kiểm, không cài package chỉ cho đủ. SSRN403/guessedpublisherURLfailure
giữ là failedaccess, không fullpaperread hoặc bypass. Research nguồn này có
paper2025 nhưng không tải ownmarket2025+ hoặc dùng outcomes đó làm holdout.

Bước tiếp: [R088 registration](EURUSD-POST-FOMC-PROTOCOL-20261109.md), source
pilot trước economics. Catalogue87/58 giữ nguyên tới khi có implementation/
outcomes mới. Goalactive, C1/C2 chưa đạt, không broker/runtime mutation.

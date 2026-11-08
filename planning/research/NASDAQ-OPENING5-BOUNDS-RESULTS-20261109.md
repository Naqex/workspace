# R065: gác phiên bản hiện tại sau kiểm khoảng kết quả

**Chưa có ứng viên challenge. Gác exact R065 để chuyển cơ chế khác.**
Năm 2022 dương nhưng năm 2019 vẫn âm ở cả đầu biên có lợi của sensitivity
model vừa đăng ký. Không cần tiếp tục tìm archive chỉ để cứu phiên bản này.
Đây không bác bỏ mọi opening-range strategy hoặc mọi khả năng có edge.

[Protocol](NASDAQ-OPENING5-BOUNDS-PROTOCOL-20261109.md) commit `6bca04e`,
implementation `ad9f35b`; parent financial strategy vẫn `d5aad5b`.
Không đổi entry/SL/TP/risk/cost; bổ sung cách biểu diễn uncertainty riêng.

## Kết quả trên vốn mô phỏng 10.000 USD mỗi năm

| Năm | Phí chuẩn: khoảng net USD | Phí cao: khoảng net USD | Số lệnh chuẩn/cao | Lệnh có bất định mỗi mức phí |
|---|---:|---:|---:|---:|
| 2019 | −351,20 đến −339,70 | −925,72 đến −914,80 | 239 / 246 | 2 |
| 2022 | +714,71 | +568,12 | 243 / 243 | 0 |

Đây là **outer bounds có điều kiện**: giá chưa thấy được giả định nằm trong
H1 cùng side và protective execution tuân theo parent model. Không phải
khôi phục quote thiếu hoặc xác nhận PnL thực. H1 tương lai chỉ dùng phân tích
bất định, không được đưa vào tín hiệu/sizing. Khoảng 2019 hẹp không chứng minh
không có outlier, broker outage hoặc rejection ngoài giả định.

Năm 2019 có số lệnh khác giữa hai costs vì slippage tham gia sizing và kiểm
min/max quantity/margin; không giả đây là cùng trades chỉ trừ thêm phí. Hai
scenarios và hai năm đã exposed không là independent trials/clean OOS.

Theo tiêu chí khóa trước, stress upper bound 2019 < 0 nên không ưu tiên
exact recipe thêm. **Original R065 gate vẫn inconclusive vì 2019 unknown**;
không sửa annual N/A thành net của conditional model hoặc claim original
gate đã bị chứng minh fail. Quyết định gác là ưu tiên nghiên cứu từ model
sensitivity, không tự động rejection của cả family hoặc quyền giao dịch.

## Kiểm gì để tin đúng phạm vi?

- 8 unit tests cho mô hình mới đạt; 12 parent regressions đạt. Một test cash
  eligibility ban đầu không kích hoạt được nhánh cần kiểm; sửa fixture tăng
  margin ngày kế rồi kiểm lại. Không đổi production logic để test pass.
- Trước numeric: 12 synthetic Fraction cases BUY/SELL × hai costs ×
  exact/missing/dual-hit khớp producer. Không dựa vào tổng PnL để chọn mô hình.
- Full reviewer riêng dùng Fraction, tự tính opening/side/stop/TP, quantity,
  margin, nhánh uncertainty, giá thoát, rounding và cash cho đủ 8 books.
  6 mutations sai count/exit bound/net/side/quantity/authority đều bị phát hiện.
- Toàn bộ 243 trades/cost năm 2022 có cùng entry/side/quantity/stop/TP/cost/net
  với reviewed parent v2. 16 closed trades/cost trước first gap 2019 exact.
  4 null books vẫn không có lệnh/PnL. Không lấy parity thay bằng chứng edge.
- Đây là cùng agent/provider với code path và số học khác; chưa independent
  human/model review, target-broker fidelity, prop equity/DD hoặc OOS.

## Nguồn, failure và phục hồi

[BI5 protocol](NASDAQ-BI5-SOURCE-PROTOCOL-20261109.md): một GET timeout trước
HTTP response, `URLError/WinError 10060`, 21,608s; không có binary payload.
Giữ failed source attempt; không kết luận archive không có file hoặc quote.

[H1 source fixture](NASDAQ-H1-GAP-ENVELOPE-PROTOCOL-20261109.md): hai side chứa
16.624 ticks và 59 M1; 472 M1 price fields khớp envelope, không có tick phút
14:49. H1 Ask 6733,140–6763,341 loại trừ TP6563,560 nhưng không loại SL6755,070.
Producer Decimal và reviewer Fraction khớp; 5 mutations bị phát hiện.
Một locator M1 ban đầu dẫn failed v1 được sửa bằng amendment `b0aec98`
trước trích giá; source thực là reviewed v2, không sửa failed v1 thành complete.

Bounds attempt v1 dừng ở event serialization Decimal sau khi đã lưu
`2019-reference.json`. Attempt v2 chỉ sửa serializer/locator, giữ v1 scripts,
manifest và failure; reuse book đầu nguyên bytes rồi full Fraction review.
Actual progress/events roundtrip Decimal đạt trước chạy v2. Không rerun book
đã tính chỉ vì logging lỗi; 7 books còn lại được chạy rồi review.

Private base: `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`.
Mọi locator dưới đây tương đối với `execution-v1/`:

| Artifact | Locator / seal |
|---|---|
| BI5 failure | `nasdaq-bi5-source-fixture-v1/failure.json` |
| H1 source fixture | `nasdaq-h1-gap-envelope-v1/result.json`; SHA `0ec6c186de798761345619e56af5fd37f0749fcefffdcdf467b8bb636310245e` |
| Bounds failure giữ lại | `nasdaq-opening5-bounds-v1/failure.json` |
| Bounds 8 books + pins/progress/events | `nasdaq-opening5-bounds-v2/result.json`; SHA `589ffa3493013a5b1f2ac43d7a14cc1a45e787ac5e536289cb68d4152f1eea3e` |
| Full Fraction review | `nasdaq-opening5-bounds-v2/review.json`; reviewer SHA `1782dd47784ff58d67d11c3c4ab7ed0a6d31924fc796b8a95444a3c427a3acac` |
| Reused first book | SHA `040478514e38fb43cb346d8486026ff288ce0cfe97f1109410bc797c94e53b55` ở cả v1/v2 |

## Hậu kiểm kỹ thuật và dữ liệu

| Lát | Wall time đo được | Kết luận / hành động |
|---|---:|---|
| Archive GET failed | 21,608s | Giữ lỗi transport, không retry không đổi |
| H1 fixture + Fraction review | 2,662s | Reuse nguồn cũ, không download |
| Bounds v1 trước lỗi log | 6,571s | Lỗi serializer đã sửa và smoke-test trên actual writer |
| Bounds v2: 7 books + reuse 1 | 24,335s | Đủ nhanh cho research hiện tại; không GPU/Rust rewrite |
| Full Fraction review | 7,652s | Tách correctness khỏi performance và economics |

Các dòng có scope khác nhau, không suy speedup so với batch cũ hoặc cộng
thành end-to-end research time. Thời gian authoring/research chưa instrument,
ghi unknown; CPU không là token/quota. Đây không là benchmark lặp nhiều lần.

Data flow tiếp tục: immutable raw → source-only view có seal → protocol và
config/code pins → exact/conditional outputs tách riêng → review → catalogue.
Giữ history/negatives/failures; không migration/raw rewrite hoặc xóa evidence.
[Data/retrieval review](AGENT-DATA-RETRIEVAL-20261108.md) vẫn là owner của thiết
kế lưu/tra cứu; numerical JSON là nguồn số liệu, RAG không tính thay PnL.
Reuse existing research/qualification/retrospective skills; chưa có lý do tạo
skill quản lý mới cho một conditional model. Không thêm framework/DB/UI.

**Tiếp:** method admission cho NASDAQ noise14, một asset-transfer hypothesis
khác opening5; giữ parent R048 US500 negatives và trial history. Đăng ký recipe,
source/clock/cost/risk và phương pháp kiểm trước outcomes mới; không điều chỉnh
R065 hoặc tăng risk để ép target. Catalogue vẫn 65 records/45 policy versions/
25 native rules cho tới khi hypothesis mới có đăng ký riêng. Goal C1/C2 active.
Không worker còn chạy khi đóng lượt này; không broker/holdout/runtime mutation.

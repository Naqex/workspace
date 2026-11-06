# Hai ứng viên sau annual — review bằng chứng đã có, 06/11/2026

## Kết luận và quyết định bước tiếp

**Cả Z-score và UTC range vẫn `inconclusive`: giữ để nghiên cứu, chưa chọn
winner, chưa đủ cơ sở chạy challenge hoặc promote strategy lên broker.**
Phép tính/accounting đã có kiểm chứng trong declared scope; lợi thế bền vững
và tốc độ đạt vốn quỹ vẫn chưa được chứng minh. Study annual hoàn tất; không
còn chờ numerical worker của lượt đó.

Lượt review này chỉ đọc artifacts đã dùng: không replay giá, mở window mới,
đổi parameter hoặc gửi broker. Owner giao review/chọn bước tiếp; đề xuất
experiment bên dưới **chưa là executable registration hoặc quyết định đã duyệt**.

## Kết quả theo giai đoạn

USD trên tài khoản mô phỏng ban đầu10.000USD, planned risk25USD/lệnh,
daily/overall nội bộ100/500USD, một vị thế. Giữ nguyên entry, initialSL2ATR và
exit của từng candidate. Bảng dùng **chi phí cao**, tính thay đổi equity gồm
lãi/lỗ đang mở và các phí đã booking theo mô hình.

| Giai đoạn | Z-score | UTC range |
|---|---:|---:|
| Q1/2022 |−139,30|+26,67|
| Q1/2023 |+61,08|+28,48|
| Q2/2023 |+86,68|+12,54|
| Q3/2023 |+101,37|−43,99|
| Q4/2023 |−69,36|+189,93|

Đây là5khối quý không trùng lịch, **không phải5mẫu độc lập thống kê** hoặc
một account chạy liên tục15tháng. Q1/2022 chạy engine revision cũ; giữ cùng
candidate IDs/risk/cost terms, nhưng chưa chứng minh numerical equivalence
giữa hai engine versions. Không cộng các window pilot/Q1/annual/horizons
chồng nhau thành thêm evidence độc lập.

| Chỉ tiêu2023 | Z-score | UTC range | Ý nghĩa |
|---|---:|---:|---|
| Net phí chuẩn / cao, USD |275,74 /179,77|223,74 /186,96|Chênh lệch gồm cả sizing giữa scenarios |
| Tick equity DD, phí cao, USD |106,43|143,79|Không thay full firm compliance |
| Lệnh đóng |102|199|Tần suất quan sát, chưa là mục tiêu chung |
| Giữ lệnh trung bình |29,59giờ|6,15giờ|Z-score phơi nhiễm phí qua đêm nhiều hơn |
| Net năm trừ contribution quý tốt nhất, USD |+78,40|−2,97|Diagnostic tập trung lợi nhuận, không là replay bỏ quý |
| Net giảm khi tăng phí |34,80%|16,44%|Stress scenario khai báo, chưa phải broker costs lịch sử |

**UTC range:** Q4đóng góp189,93USD trong tổng186,96USD cả năm; ba quý còn
lại cộng lại−2,97USD. Dương4/5khối quý nhưng chưa đủ để chọn nó thắng.
**Z-score:** lợi nhuận2023ít phụ thuộc riêng quý tốt nhất, nhưng thua ở
Q1/2022vàQ4/2023. Chưa biết nguyên nhân thuộc market regime nào; không thêm
filter dựa trên hindsight hoặc bắt mọi quý đều có lãi.

## Phí và sizing có giải thích được kết quả không?

Đối chiếu từng closed trade bằng Decimal và cộng về net ledger2023:

| Khoản tiền2023, USD | Z chuẩn | Z cao | UTC chuẩn | UTC cao |
|---|---:|---:|---:|---:|
| Price PnL đã chứa Bid/Ask spread, trước các phí bên dưới |315,12|310,98|262,54|256,35|
| Commission |19,55|19,45|38,80|38,55|
| Slippage cash cost |0|15,56|0|30,84|
| Financing debit |19,83|96,20|0|0|
| Net |275,74|179,77|223,74|186,96|

Commission2,50USD/lot/side; chuẩn slippage0, financing buy9,3/sell−0,31;
cao slippage0,00002/side, financing buy/sell20. Financing22:00UTC ngày thường,
Wednesday×3; candle/quoteUTC, daily risk resetEurope/Prague. Đây là declared
counterfactual costs, chưa là historical broker statement.

Modeled initial stop-risk trung bình ở phí cao là22,13USD/lệnh cho Z-score
và21,97USD cho UTC, khoảng88,54%/87,89% ngân sách25USD. Không có bằng chứng
sizing chỉ sử dụng một phần rất nhỏ risk budget. Initial stop-risk không
bao gồm financing phát sinh/gap/latency và không bảo đảm maximum loss:
closed trade tệ nhất2023tương ứng−27,80/−25,00USD. Z-scoreQ1/2022đã có price
PnL âm trước các phí bổ sung, nên không thể quy toàn bộ kết quả xấu cho swap.

## Đã kiểm gì và còn thiếu gì?

| Lát | Bằng chứng hiện có | Giới hạn |
|---|---|---|
| Correctness | Annual12sealed rows đối soát, financial/trade traces parity với annual cũ; review reconcile trade costs và monthly sums;23input artifact hashes khớp | Scoped kiểm chứng, không audit toàn engine/broker |
| Edge | Các contribution/cost diagnostics bên trên | Q1/2022và2023đã consumed; không clean OOS, chưa có uncertainty/selection-aware inference |
| Prop fit | Native tick-risk/lifecycle trên2023, không breach declared profile; mọi cutoff vẫnphase1/chưa target | Không full firm/news/inactivity/payout/spec certification; không suy thời gian pass từ annual mean |
| Operations | Numerical batch hoàn tất; review dùng lại artifacts | Chưa là forward/reconciliation hai chiến lược trên broker |
| Authority | Review offline | Không cấp quyền data window mới, broker hoặc mua challenge |

Phương pháp monthly/quarterly dùng equity mark cuối cùng trong ledger trước
boundary, gồm floating và scheduled cash events; không lấy thêm quote để tạo
giá biên. Kiểm khớp12horizons3/6/12tháng và tổng12monthly contributions bằng
annual net. Không dùng closed-PnL theo tháng thoát để giả thành equity returns.

## Một experiment đề xuất — kiểm thêm giai đoạn trước khi chỉnh risk/TP

**Câu hỏi:** hai bộ quy tắc không đổi có còn tạo net dương sau chi phí ở đoạn
lịch sử tiếp theo của2022, hay kết quả hiện tại phụ thuộc hẹp vào thời kỳ?

| Thành phần | Thiết kế đề xuất, chưa được chạy |
|---|---|
| Candidate | Cả hai frozen versions hiện tại, EURUSD/H4 |
| Window |01/04–30/09/2022; warmup01/02–31/03/2022; chưa mở giá mới |
| Cách chọn | Tiếp theoQ1/2022theo lịch, chưa dựa vào outcome window mới; tránhQ4/2022vìNov–Decđã dùng warmup2023 |
| Giữ cố định | Initial10k, planned25USD/trade, internal100/500, entry/2ATRSL/original exits, hai costs và declared prop profile |
| Primary | Net6tháng ở reference/stress, tickDD, first-breach/native phase status và counts/exposure |
| Diagnostics | ContributionQ2/Q3, costs/holding/sizing; không đòi mỗi quý đều thắng |
| Correctness stop | Lỗi material/timing/data/accounting làm evidence bị quarantine; sửa đúng lỗi trước numerical acceptance |
| Interpretation | Breach: không đạt profile/config đó. Net không dương: chưa đủ để promote trong test này, không loại cả họ chiến lược. Net dương: chỉ thêm robustness evidence, chưa tự pass edge/prop |

Trước thực thi phải audit availability/consumed metadata mà không đọc outcome,
xác định gate dữ liệu và freeze registration/source/input hashes/cost/decision.
Prior exposure chưa rõ nên **không gọi window này clean OOS**. Contract runner
hiện dùng3/6/12tháng; study6tháng cần registration/consumer/preflight đúng scope,
không sửa JSON annual đã freeze hoặc tạo input hash giả. Warmup không tính PnL;
account reset đầu window, không nối giả state từ engineQ1cũ.

Đề xuất này **ưu tiên trước risk12,50/25 và TP2R** vì bất định chính hiện là
robustness theo thời kỳ, không phải thiếu dùng risk budget. Giữ các task risk/
exit đã giao trong backlog; không bỏ chúng và không auto-dispatch test mới.
Đây là thay đổi thứ tự do review evidence, không sửa verdict/criteria lịch sử.

## Provenance, tái lập và nguồn phương pháp

- Annual root: `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/prop-survivors-20261106/execution-v1/`;
  [protocol](PROP-PATH-SURVIVORS-20261106.md), pinned numerical source`0883e9ee`,
  implementation`5c6d82ff`; test-only`7b2c536d`không đổi numerical bytes.
- LegacyQ1: `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/prop-q1-comparison-20261105/attempt-3/`;
  source`814e11358636b0b3d35bc7241f64925418996f4a`.
- Review root: `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/prop-survivors-20261106/review-v1/`;
  recipe`review_saved.py`, output`saved-evidence-review.json`, log`review.log`.
  Output SHA256`d6ddeca3ae850d98d4d76d00503ec8409b70cdc9d7bd499d914ff4ba51710fbf`;
  JSON giữ23input artifact hashes và source/data/candidate/cost bindings.
  Recipe tạo output bằng exclusive write; tái lập dùng output directory mới,
  không overwrite evidence gốc. Không coi checkpoint-input fingerprint là raw
  data hash; dùng manifest development SHA256.
- Framework hiện có: [validation audit](STRATEGY-VALIDATION-FRAMEWORK-20261105.md).
  Đối chiếu lại phương pháp06/11với
  [A Backtesting Protocol — Arnott/Harvey/Markowitz](https://people.duke.edu/~charvey/Research/Published_Papers/P138_A_backtesting_protocol.pdf)
  và [QuantConnect Research Guide](https://www.quantconnect.com/docs/v2/cloud-platform/backtesting/research-guide):
  giữ giả thuyết/quy tắc, tính chi phí, giữ failures và bảo vệ OOS; không dùng
  test lặp trên cùng dữ liệu để biến net dương thành chứng minh edge.

## Chuẩn bị song song khi chờ period batch — đề xuất sau câu hỏi owner 06/11

Owner hỏi có nên kiểm lại các bản chưa qua screening hoặc ý tưởng chưa được
triển khai. Khuyến nghị: tiếp tục hai numerical workers đang chạy; song song
review artifacts đã consumed và chuẩn bị hypothesis/protocol, chưa dispatch
thêm batch hoặc sửa source đang được numerical workers dùng.

| Nhóm | Việc chuẩn bị | Điều kiện để cân nhắc numerical test mới |
|---|---|---|
| Donchian hiện tại: annual stress −488,47 USD | Giữ fail của version/config này, xem nguồn lỗ từ saved price-PnL/costs/exposure | Cơ chế hoặc gap cụ thể đủ lý do; không tăng lot hoặc sweep để cứu kết quả |
| SMA: stress −25,49 USD, 15 lệnh đóng/năm | Ưu tiên phân biệt ít mẫu, cost sensitivity và lỗi implementation nếu có | Protocol giải quyết bất định sample/coverage, giữ rules; không tự gọi đã có edge |
| Pullback: stress −132,51 USD; reference +1,40 gồm vị thế mở | Phân tích net/floating/financing/holding và nguyên nhân price-PnL so với phí | Có hypothesis sửa một yếu tố, thành version/trial mới; không chọn exit sau khi thấy outcome |
| Ý tưởng chưa triển khai ở danh mục round1 | Đọc cơ chế, yêu cầu history/universe/session/cost và khả năng tái lập | Đủ dữ liệu/contract và một giả thuyết rõ mới đăng ký; chưa test không phải đã fail |

Quy trình cho bài tiếp: phân loại fail/insufficient/correctness → nêu một câu
hỏi và tiêu chí bác bỏ → reuse diagnostics trên consumed artifacts → freeze
rules/data/cost/risk/decision trước outcome mới → chạy phần cần thiết → giữ mọi
trial kể cả âm. Thay risk đơn thuần không chứng minh đã sửa lợi thế sau phí.
Protocol round1/round2 là hai đợt bổ sung candidate, không phải hai chứng nhận
qualification. G0–G6 vẫn phân biệt correctness, edge, prop và execution authority.

Đề xuất này chưa là phân công chạy lại ba ứng viên, chọn winner, mở data window
mới hoặc thay current period registration. Primary source phương pháp vẫn là
Arnott/Harvey/Markowitz đã dẫn trên; tránh sửa đi sửa lại theo cùng kết quả.

### Chuẩn bị đã thực hiện: đọc lại ba bản tạm gác, 06/11

Đã tính lại từ saved annual report của source `bbc7c60e`, không đọc giá hoặc
chạy numerical simulation mới. Đối soát từng closed trade: price PnL sau spread
trừ commission/slippage/model-financing/timed-financing bằng net; cộng về cash,
thêm floating đúng account equity. Sáu candidate/cost rows khớp.

| Phí cao, USD | Lệnh đóng | Closed price PnL sau spread | Commission + slippage đóng | Financing của lệnh đóng | Net equity cuối năm |
|---|---:|---:|---:|---:|---:|
| Donchian |43|−328,23|14,04|146,20|−488,47|
| SMA |15|+89,19|4,68|110,00|−25,49|
| Pullback |20|+22,78|6,93|158,20|−132,51|

Pullback net closed là−142,35USD; cộng floating20,24 và trừ financing vị thế
đang mở10,40 mới ra equity−132,51. Không gọi closed-price column là tổng PnL
account trước mọi phí. SMA/Pullback giữ lệnh đóng trung bình248,35/275,60giờ,
khoảng10,35/11,48ngày, nên financing model là một bất định vận hành đáng kiểm.
Đây là attribution số học, không chứng minh cơ chế thị trường hoặc edge; phí
stress là giả định, không phải phí hãng thực thu. Không giả swap0 để cứu bản.

SMA giữ closed price PnL89,19ở cả hai costs, mẫu chỉ15lệnh; đáng chuẩn bị câu
hỏi coverage/cost realism trước khi sửa exit. Pullback có price PnL dương mỏng
và net closed âm ngay reference (−14,17USD); chưa đủ lý do ưu tiên biến thể TP.
Donchian đã âm ở price PnL sau spread trong cả hai costs, financing không giải
thích hết lỗ. Không cộng/pool các scenarios thành mẫu độc lập; Donchian có số
fills khác nhau giữa scenarios, không phải chỉ lấy cùng trades trừ phí khác.

Artifact:
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/prop-period-robustness-20261106/post-batch-preparation-v1/deferred-candidates-diagnostic.json`.
Input saved report SHA256
`2d1ff9d885f79c7a566955e4c509c16784f4d6f7fa0e173fcca188e78d26a118`.
Giữ historical-engine/report scope; đây không là independent full raw replay.
Scope/acceptance việc sau batch và gap forward nằm ở
[AI plan hiện hành](../trader/AI-RESEARCH-UI-PROTOTYPE-20261031.md#sau-period-batch-chuẩn-bị-tiến-tới-vốn-prop-và-payout--06112026).

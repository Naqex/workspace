# Vì sao US500 ít lệnh? Đã kiểm riêng tần suất

11/11/2026. [Protocol khóa trước số đếm](US500-FREQUENCY-AUDIT-PROTOCOL-20261111.md),
commit `0f929a3`. Đây là 15 phép đếm năm/probe, **không phải backtest lời/lỗ mới**.
Giữ nguyên [162 financial books trước](US500-MULTIFRAME-RESULTS-20261111.md).

## Kết quả dễ đọc

Cùng US500, M15, MA20/80, ATR14, đệm0,10ATR, BUY/SELL và một setup/ngày.
Số dưới là **tín hiệu đã xác nhận và có đủ giá ở phút khớp dự kiến**. Chưa qua
native order/risk/SL/exit nên không gọi là executed trades hoặc lợi nhuận.

| Phép đo | Thay đổi so với bản nền | 2022 | 2023 | 2024 | Tổng |
|---|---|---:|---:|---:|---:|
| FP00 | Giữ đúng bản nền |9|6|4|19|
| FP01 | Warmup chỉ dùng MA cần thiết, bỏ phụ thuộc H1 ở A |9|6|4|19|
| FP02 | Như FP01, tìm setup đến14:00, xác nhận đến15:00 NY |35|27|31|93|
| FP03 | Như FP01, chấp nhận râu nến chạm/xuyên MA |22|15|17|54|
| FP04 | Kết hợp khung giờ rộng và râu nến chạm MA |55|50|53|158|

FP04 tăng từ19 lên158 tín hiệu, khoảng8,3lần **về số tín hiệu trong mẫu**, không
phải tốc độ chạy hoặc lợi nhuận tăng8,3lần. Khoảng1tín hiệu/tuần, vẫn thấp hơn
mục tiêu thiết kế2–5lệnh/tuần đã đề xuất. Các probe là biến thể cùng họ; không
cộng tín hiệu của chúng thành mẫu độc lập lớn hơn.

**Kết luận:** giới hạn giờ và định nghĩa pullback/confirmation làm cơ hội thưa.
Warmup common161+H1 của bài so sánh cũ có loại thêm bar, nhưng bỏ phụ thuộc đó
không tăng số confirm trong bản đầu phiên này. Không có bằng chứng engine
đánh rơi lệnh chỉ vì warmup hoặc reporter.

## Từng tầng đã lọc thế nào?

Ba năm có753phiên theo lịch:747phiên thường,6phiên ngắn. Không nói753phiên đều
đủ điều kiện; readiness và dữ liệu thiếu vẫn chặn theo lịch sử đã biết.

| Cùng đơn vị nến tại giờ được phép arm | FP00 | FP04 |
|---|---:|---:|
| Tổng giờ/nến cần xét |3.012|12.777|
| Phiên ngắn |24|78|
| Bị chặn vì gap đã xuất hiện |27|223|
| Chưa đủ warmup |574|1.105|
| Đã dùng lượt setup của ngày |158|4.451|
| Hướng MA chưa ổn định |24|137|
| Close trước không nằm đúng phía MA |824|2.055|
| Chưa xuất hiện pullback theo định nghĩa |1.280|4.255|
| **Setup được ghi nhận** |**101**|**473**|

Các dòng trong mỗi cột cộng đúng tổng số nến. Một ngày có thể xuất hiện nhiều
reason ở các giờ khác nhau; không cộng unique-day counts chéo thành số ngày
bị loại. Vì giờ xét khác nhau, raw reject counts hai cột không là tỷ lệ tác
động nhân quả hoặc lý do xóa filter theo PnL.

| Sau khi đã ghi setup | FP00 | FP04 |
|---|---:|---:|
| Confirm đúng thời hạn |19|158|
| Hết hạn trước khi confirm |81|304|
| Hủy vì mất hướng |1|10|
| Hủy vì gap sau arm |0|1|
| **Tổng setup** |**101**|**473**|

Ở FP04, khoảng64,3%setup hết hạn và33,4%confirm. Yêu cầu nến sau đóng vượt
đỉnh/đáy armbar là tầng còn chặt. Con số này **không chứng minh** các setup hết
hạn sẽ có lời nếu vào sớm; chưa đo đường giá sau entry hoặc PnL của chúng.
Mỗi ngày chỉ nhận setup đầu tiên, nên nới điều kiện arm không bảo đảm số confirm
tăng theo mọi phép so sánh. Không tự bật rearm để ép tăng số lệnh.

## Đối chiếu và giới hạn

- FP00 khớp từng timestamp/side arm và confirm với saved R098 cả ba năm và
  replay parent Policy. R120 cũng khớp savedtrace:87arm/15confirm. Không chỉ so
  tổng count. Không rerun financial engine để kiểm metadata tín hiệu.
- 10tests đạt: hai chiều, close-cross so với wick, own warmup không bỏ MA80,
  giờ muộn/expiry, strict equality, gap/shortday, oneattempt, exactopen và
  prefix không đổi khi sửa dữ liệu tương lai.
- Reuse accepted full four-quarter source proofs; pin source/protocol/tests/
  calendars/input hashes và snapshots. 2022–24 exposed,2025+không đọc.
- Mỗi confirm có exact-open minute và preceding causal minute trong cặp giá;
  chưa chứng minh có thể đặt lệnh, đủ margin, đủ minlot hoặc đủ chất lượng
  thực thi trên broker đích. Không xét news/closures hoặc target FTMO feed.

## Quyết định đã khóa và bước tiếp

Mốc50–100 screening,200–500 kiểm sâu là planning heuristic, không chuẩn quỹ,
statistical certificate hoặc lý do ép entry. FP04 là thiết kế chính đã chọn
**trước phép đếm**; không chọn lại giữa5probes sau khi thấy kết quả.

Protocol đợt này đặt research-priority floor>=200signal tổng và>=50/năm trước
khi xem xét đăng ký financial screen riêng. FP04 đạt annualfloor55/50/53 nhưng
chỉ158tổng: **chưa qua floor của đợt này**, không chạy batch tài chính mới.
Đây là quyết định phân bổ công sức, không bác bỏ edge hay nói158lệnh không
bao giờ đủ cho screening. Không sửa floor sau outcome để cho FP04 qua.

**Đề xuất tiếp:** nếu tiếp tục họ pullback, cần một giả thuyết mới có lý do
kinh tế cho confirmation, chẳng hạn giá hồi phục lại MA theo hướng ban đầu,
thay vì mặc định phải vượt toàn bộ armbar. Đây là thay chiến lược, cần spec/
registration/kiểm số tín hiệu mới; không gọi là sửa bug hoặc nới tự động.
Không triển khai hay chạy giả thuyết này trong lượt audit hiện tại.

FP01–FP04 được giữ trong catalogue dưới `frequency_only_studies`. Catalogue
account policies vẫn122records/87versions; cộng thêm4related frequency-only
designs đã xem, không che trials hoặc đếm chúng thành4edge độc lập.

## Hậu kiểm kỹ thuật

| Lát công việc | Đo được | Quyết định |
|---|---:|---|
| Đọc/kiểm source và chuẩn bị indicators3năm |21,61s|Load một lần/năm dùng chung5probes|
| Toàn audit |22,06s|Không financial replay; không claim speedup so workload5phút44|
| Frequency replay và parent trace parity |0,45s|Census theo từng tầng, giữ attempts/expires|
| Engineering/research/Git |Chưa đo riêng|Không gộp vào22,06s|

Chưa có lỗi material mới hoặc nhu cầu thêm engine/GPU/Rust. Lát cải tiến có
ích là bước admission tần suất ở workflow hiện có; chưa cần skill mới. Existing
strategy-research/qualification vẫn giữ thiết kế trước outcome và gate riêng.

Evidence private dưới campaign `execution-v1/us500-frequency-audit-v1/`:
`manifest.json`, `source-snapshot/`, `input-YEAR.json`, `YEAR-FPxx.json`,
`YEAR-R120-audit.json`, `result.json`, `events.jsonl`, `progress.json`.
Mỗi attempt/event nằm trong annual artifact; không còn writer/job đang chạy.

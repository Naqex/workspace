# US500: đã đếm cơ hội, ưu tiên kiểm tiếp phá kênh20

Owner sau đó yêu cầu [kiểm cùng FP07 trên2013–2021](US500-CHANNEL-HISTORY-RESULTS-20261112.md):
đã hoàn tất frequency-only, giữ data-gap caveats; không đổi các số2022–24dưới đây.

12/11/2026. **Phá kênh20 có nhịp đáng nghiên cứu tiếp; chưa biết có lời.**
Đã hoàn tất 12ca = baseline+3frequency probes×3năm trong22,77giây.
Không có financial simulation, broker/model calls hoặc dữ liệu2025+ mới.
[Protocol](US500-OPPORTUNITY-SCREEN-PROTOCOL-20261112.md) và source/tests đã
commit `0df2da5` trước số đếm; giữ nguyên các kết quả và floor lịch sử.

## Đọc kết quả đơn giản

| Bộ luật tín hiệu | Cơ hội đầu ngày2022 /2023 /2024 | Tổng3năm | Mỗi5phiên lịch | Tuần không có cơ hội | Tháng ít nhất /trung vị /nhiều nhất |
|---|---:|---:|---:|---:|---:|
| R123/FP05: pullback cũ, thử setup đầu ngày |58 /50 /57|165|1,10|47/157|1 /4 /10|
| FP06: cho tìm setup khác sau lần đầu không xác nhận |65 /54 /62|181|1,20|40/157|1 /5 /10|
| **FP07: phá kênh20 nến trước đó** |195 /174 /171|**540**|**3,59**|**1/157**|**10 /15 /21**|
| FP08: hai đường MA20/80 cắt nhau |72 /62 /62|196|1,30|36/157|2 /6 /9|

Đơn vị là **signal đầu tiên trong ngày có đủ quote ở clock dự kiến**, không
phải orders/fills hoặc trades đã qua risk/position/cost. Mẫu số giữ753phiên
lịch, kể cả warmup/gap/shortsession;157tuần có tuần biên/nghỉ lễ. Không gọi
tuần/phiên bị data blocks là thị trường không có setup.

Chọn signal đầu ngày **trước** kiểm quote; không chọn signal sau vì signal
đầu thiếu quote. Trong mẫu này tất cả confirmation clocks đều đủ cặp quote;
availability không chứng minh đủ margin/minlot, fill hoặc tuân thủ targetbroker.

## US500 ít cơ hội hay luật quá kén?

**Trong mẫu và luật đã đăng ký, sự khan hiếm chủ yếu nằm ở cách định nghĩa
setup/confirmation đang chọn; không có cơ sở gọi US500 tự nó ít cơ hội.**
FP07 thấy540ngày có trigger trong cùng753phiên. Đây là rule khác, không thí
nghiệm cô lập duy nhất mỗi tham số; không quy mọi khác biệt cho một filter.

Phép đối chiếu kiểm soát riêng cap là FP06 so exactR123:

- Cùng setup/MA/ATR/clock/expiry; chỉ cho rearm ở bar sau expire/cancel,
  vẫn dừng sau confirmation đầu ngày.
- Tăng165→181, thêm16ngày, khoảng**9,7%**. Giữ mọi ngày baseline từng confirm.
  Cách retry này không làm nhịp tăng mạnh; không khẳng định mọi cách rearm
  khác sẽ có cùng tác động, không dùng kết quả để tự đổi bot.
- Baseline396arms:165confirm,222expire,8canceltrend,1cancelgap. Nhiều setup
  đã có nhưng chưa đạt xác nhận trước expiry. Chưa biết vào sớm có lợi hay lỗ;
  số đếm không là lý do bỏ confirmation để cứu PnL.
- FP06424arms:181confirm,233expire,9canceltrend,1cancelgap. Chưa tính PnL của
  các ngày thêm; không lấy net cũ cộng16lệnh giả định hoặc promote bản mới.

## FP07 đơn giản là gì, có đều không?

Tại một M15 vừa đóng: nếu close cao hơn đỉnh20nến **trước nó** cộng0,10ATR thì
ghi cơ hội BUY; dưới đáy20nến trừ đệm thì SELL. Không đưa nến đang xét vào
kênh; không dùng nến chưa đóng. Đợt giá liên tục còn ngoài kênh chỉ đếm một
lần, phải trở vào/đổi phía mới có đợt khác. Chỉ xét10–15NY, session/gap rules
đã khóa. Đây là giả thuyết trigger, chưa có exit/SL/sizing hay account policy.

FP07 có992trigger events (538BUY/454SELL), nhưng chỉ**540ngày** sau khi giữ
trigger đầu ngày. Không gọi992là992trade độc lập; những đợt sau có thể xảy ra
khi một vị thế trước vẫn còn mở. Không cấp quyền trade nhiều lần/ngày từ rawcount.

- 131/157tuần có≥3cơ hội đầu ngày;1tuần không có. Longest no-signal run6phiên
  lịch, gồm warmup/data filtering, không chứng nhận outage-free.
- Tháng10–21, trungvị15. Theo quý39–52. Annualfirstcounts195→174→171 tương
  đương3,88→3,48→3,39mỗi5phiên; không giả nhịp luôn cố định qua các năm.
- [ORB R094 đã có](US500-FREQUENCY-LANDSCAPE-20261111.md) khoảng4,50entry/5phiên
  nhưng economics chưa đạt/held gaps còn. Không chạy lại ORB hoặc coi dải
  cadence tốt là bằng chứng có thể qua quỹ.

## Quyết định và bước tiếp

**Ưu tiên FP07 cho việc thiết kế economic screen đăng ký riêng**: nhịp trong
dải3–5đề xuất, luật rõ, không phải vì đã thấy lợi nhuận (chưa tính). Đây là
relatedR001/Donchian, không edge độc lập hoặc replication của paper/indicator.
[LEAN Donchian](https://www.quantconnect.com/docs/v2/writing-algorithms/indicators/supported-indicators/donchian-channel)
chỉ hỗ trợ định nghĩa high/low channel; cách dùng priorbars, đệm và giờ thuộc
protocol của project. Không claim20bars/0,10ATR là tham số tối ưu.

FP06/FP08 giữ evidence và hạ ưu tiên cadence của vòng này; không gọi chúng
không có edge vì ít mẫu. ExactR123 và R094 negative verdicts giữ nguyên.
Không quét tiếp periods/threshold/giờ để tăng số đếm.

Chặng kế tiếp cần freeze đầy đủ entry→fill, exits/SL, risk/lot, costs/stress,
gap/end-state và decision rule trước PnL. Sau đó mới biết bao nhiêu signal
thành trade, có lời sau fees không; còn prop news/closures/spec, intraminute
equity, OOS và forward là gate riêng. Chưa dispatch financial run trong lượt này.

## Cách đã kiểm, luồng dữ liệu và giới hạn

PairedM1+calendar đã admitted → shared M15/native indicator preparation →
closed-bar triggers → episode/firstday selection → quote-availability census →
weekly/monthly/quarterly report. Reuse nativeNautilus1.231.0 indicators và source
loader; không gọi đây là native financial replay vì không có orders/accounting.

- 9focused tests đạt: BUY/SELL, currentbar excluded/equality, episode dedup,
  gap reset/overnight history, MA two closed values/same session, rearm bar
  sau/cap sau confirm, quote missing không đổi first-selection, futureprefix.
- Baseline cả3năm arm/confirm timestamps+side khớp saved FP05. FP06 giữ mọi
  baseline-confirm day. Terminal arm census và period totals đối soát.
- Finalsavedreview12cases: current source/baseline/manifest hashes, signal
  ordering/calendar clocks, firstday sums và daily/monthly/quarterly census.
  Đây là same-agent/separate-arithmetic/synthetic-regression evidence, không
  independent human/feed audit hay reconstruction mọi trigger từ feed thứ hai.
- Chỉ dữ liệu2022–2024 đã exposed. Các count không forecast live cadence,
  effective independent sample size, winrate, PnL hoặc pass probability.

Evidence private dưới campaign `execution-v1/us500-opportunities-v1/`:
manifest/source-snapshot, input-year hashes,12annual outputs, result/events/
progress/timers và`final-census-review.json`. Không còn controller lock/job.

## Hậu kiểm gọn

| Lát | Số đo / quyết định |
|---|---|
|Source validation+shared preparation3năm|20,884giây;load1lần/năm dùng chung4cases|
|Signal counts/parity/write|0,894giây;không financial engine hoặc worker farm|
|Toàn run|22,774giây;chưa đo riêng code/research/docs/Git|
|Reliability|Một writer,PID/progress/CANCEL/deadline,source pins;không lỗi/retry trong run|
|Cải tiến giữ lại|Đếm raw vs first/day và cap diagnostic trước PnL;không cần GPU/engine/skill mới|

Catalogue account counts giữ**123records/88policy-modelversions/53native**,
thêm3relatedfrequency-onlydesignsFP06–08, không xóa negatives hoặc giấu trials.

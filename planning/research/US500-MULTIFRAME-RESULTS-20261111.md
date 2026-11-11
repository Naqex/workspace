# US500 pullback A/B/C: backtest xong, chưa đủ bằng chứng để challenge

11/11/2026. [Protocol](US500-MULTIFRAME-PROTOCOL-20261111.md),
[hậu kiểm sửa quality flag](US500-MULTIFRAME-REVIEW-AMENDMENT-20261111.md),
[bảng đủ 27 cấu hình và BUY/SELL](US500-MULTIFRAME-FULL-TABLE-20261111.md).
27 related configurations, 162 native financial books +9 null controls đã xong.
Không đổi MA/k/risk/giờ/SL sau outcome; không broker hoặc2025+.

## Kết quả dễ đọc

Mỗi sổ năm bắt đầu10.000USD, plannedrisk≤25USD/lệnh. Bảng dưới cộng mô tả
ba sổ2022/2023/2024 riêng biệt, không phải một account chạy liên tục/CAGR.
Chuẩn/cao là slippage0,25/0,75point mỗi chiều; commission0, spread trong
paired Bid/Ask. Đây là declared proxy scenarios, chưa measured FTMO fills.

| Thiết kế | MA | Đệm ATR | Lệnh/3năm | Tổng net chuẩn | Tổng net chi phí cao |
|---|---|---:|---:|---:|---:|
| A: M15 |20/80|0,10|19|−0,37USD|−24,04USD|
| B: thêm H1 |20/80|0,10|19|−0,37USD|−24,04USD|
| C: thêm H1, xác nhận M5 |20/80|0,10|23|−18,36USD|−46,71USD|
| A: MA nhạy hơn |10/40|0,10|29|+31,28USD|−0,93USD|
| C: MA nhạy hơn |10/40|0,10|32|+68,91USD|−24,41USD|
| A: MA chậm hơn — R120 |40/160|0,10|15|+65,27USD|+48,87USD|

**Chưa có chiến lược đủ bằng chứng để challenge.** 11/27 cấu hình dương khi
cộng chuẩn,5/27 khi cộng chi phí cao. Chỉ R120 dương từng năm ở cả hai costs,
nhưng mỗi năm chỉ9/2/4lệnh. Nhãn này mô tả kết quả sau search, không preregistered
pass threshold, hiệu chỉnh multiple trials hoặc xác suất có edge.

| R120 |2022|2023|2024|
|---|---:|---:|---:|
| Số lệnh |9|2|4|
| Net chuẩn |+10,30USD|+14,91USD|+40,06USD|
| Net chi phí cao |+2,81USD|+11,99USD|+34,07USD|

R120 có9/15lệnh thắng;60% chỉ là mô tả mẫu rất nhỏ. Không suy độ chính xác
60% cho tương lai, không chuyển SELL-only thành trial mới vì thấy BUY yếu.
Không gọi15lệnh là đủ chỉ vì có ba năm lịch. Hướng hiện tại có tín hiệu quá
thưa để chứng minh phù hợp mục tiêu quan sát thường xuyên/nguồn thu chính.

Tần suất thấp có dấu vết rõ: R120 có87arm attempts,15confirm,71expiry,
1trend-cancel trên753scheduledsessions. Luật chỉ nhận pullback trong4M15
đầu phiên, rồi đợi vượt armbar trong≤60phút; không phải mọi biến động củaUS500
đều thành tín hiệu. Đây là thuộc tính của exactrules, không bằng chứng cả
US500/trend-following không có cơ hội. Chưa tự nới luật sau khi thấy ít lệnh.

Ở MA20/80, A/B có cùng trades/outcomes ở cả7buffers trong mẫu này: H1 chưa
thêm thông tin cho các admissions đã có, không7lần xác nhận độc lập. C có
thêm/đổi entry nhưng chưa cải thiện net đủ rõ; M5 không tự tốt hơn M15.

## Phạm vi tính đúng đã kiểm

- Native NautilusTrader1.231.0 thật dispatch quotes/events, market/stop orders,
  matching, positions và cash. Native Cfd INDEX multiplier1, không giả thành
  Forex. Custom strategy/data adapter và FillModel giữ declared semantics.
- Native SMA/ATR đối chiếu Decimal; closed M15/M5/H1/as-of/carry, equality,
  same-event ordering, expiry, both sides, next-minute entry và no-reversal
  có fixtures. Full session history, common161M15+20H1 readiness, cold annual
  starts; gap reset causal, không dùng coverage tương lai xóa trades trước đó.
- Separate Fraction/Decimal reviewer đối soát entryside/time, quantity/SL/
  plannedrisk/margin, first stop/gap/scheduled exit, nativeclosed events/cash,
  fees, open endstate và quality flags. Đây là **same-agent, separate code path**,
  không độc lập reviewer/feed hoặc chứng minh toàn hệ thống không thể sai.
- 23focused tests +1 CLI recovery integration test đạt. Recovery cố ý fail ở
  book3: giữ2sealedbooks, chỉ chạy55book còn lại; tampered savedbook bị chặn.
  6synthetic old→fixed native comparisons giữ toàn bộ financial fields.
- 171savedbooks được hậu kiểm lại. 9nullcontrols khônglệnh/khôngPnL.
  Tất cả closedtrades trong đợt này có complete observed M1 held coverage;
  0unresolved/0openposition cuối book sau correction. Vẫn không exact tick path.

M1 lowBid/highAsk chỉ là stop-touch envelope, không observed synchronous quote
hoặc crossingtime. Không TP/competing intraminute barrier trong study này;
gapstop dùng open±slip, touchstop level±slip. Full intraminute equityDD và
FTMOdaily/overall/news/closures/targetcontract/targetfeed/OOS **chưa được kiểm**.
Endpoint equityDD không được dùng thay chúng. Không có quyền chạy broker.

## Hai lỗi integration đã sửa, lịch sử giữ nguyên

1. V1 dừng ở0books sau≈13s: NETTING cache không chứa mỗi roundtrip như position
   riêng. Đổi collector sang nativePositionClosed events;3roundtrip regression
   và per-position/cash reconciliation đạt. Native orders/rules không đổi.
2. V2 completed nhưng hậu kiểm thấy scheduledexit bị gắn unresolved sai:
   same-open callback cập nhật lastminute rồi FillModel tưởng làgap. Sửa guard
   chấp nhận current/previousminute; reviewer nay kiểm cả false-positive lẫn
   false-negative. 1.002qualityflags qua related/cost books được sửa trong
   **output mới**. All financialfields/fills/cash fingerprints giữ nguyên,
   không chạy lại162financialbooks. Không count1.002 thành independenttrades.

V2/V2-summary giữ để audit; **dùng v3-review và v3-summary** để đọc quality/net.
Source financial run commit`551f2f4`; correction/review commit`8639011`.
Original protocol/source snapshots và failure receipts giữ nguyên.

## Hiệu năng và hậu kiểm kỹ thuật

| Phần | Thời gian đo | Ý nghĩa |
|---|---:|---|
| Native batch3cohorts song song |≈344,35s —5phút44giây| elapsed của workload đã chạy, không thời gian toàn chat |
| Source/aggregate/quotes preparation |30,13s cộng3cohorts| thời gian cộng; không cộng tiếp vào elapsed song song |
|171native simulations |988,02s cộng workers| không phải chờ988s;3processes chạy đồng thời |
| Per-book review/write |8,37s cộng workers| trước postreview quality correction |
| Savedbook postreview, gồm source validation và6synthetic parity |29,77s|0native financial resimulations |
| Research/coding/debug/Git/viết báo cáo |Chưa đo riêng| không nhận cả task chỉ mất5phút44 |

| Phát hiện | Đã làm | Điều còn lại |
|---|---|---|
| NETTING history bị đếm sai | Dùng PositionClosed, regression3trades | Không dùng position cache làm trade journal |
| Quality flag false-positive | Strict coverage reviewer +sameopen regression | Giữ old artifacts và new corrected view |
| Rework có nguy cơ chạy lại cả batch | Sealed completed-book reuse đã kiểm CLI | Chưa intra-book state resume |
| Progress total hard-coded253 | Lấy sessioncount thật trong source mới | Existingv2logs giữ lịch sử, không sửa log cũ |
| Full event replay chiếm phần lớn compute | Reuse source/indicator/quote data mỗi năm;3isolatedcohorts | Chưa profilefunction; không claim Rust/GPU speedup hoặc thêm framework |

Existing research/qualification/retrospective skills đủ; bài học thuộc code,
tests và receipt. Không tạo thêm skill chỉ để lặp lại instruction đã có.

## Quyết định tiếp theo

Catalogue122records/87policy-modelversions, trong đó52native;27bản mới liên
quan cùng họ, không27edge. **R120 chỉ đáng soi kỹ trace/mẫu nhỏ**, chưa promote
hay mởholdout. Các bản còn lại giữ outcomes và costsensitivity, không loại cả
family hoặc tự quét thêm MA/k để cứu. Không ép số lệnh hoặc tăngrisk để pass.

Bước hữu ích tiếp là đọc15R120trades và87arm→confirm paths để xác minh lý do
tín hiệu thưa, mức tập trung lợi nhuận và giới hạn nguồn; giải thích cho owner
trước khi đăng ký câu hỏi mới. Nếu phải đổi giờ/confirmation/MA/SL thì trial
mới có lý do rõ, giữ negatives hiện tại. Chưa chạy việc đó trong backtest này.

## Evidence

Privatebase `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/execution-v1/`:

- `us500-multiframe-native-v1`: original failure0books.
- `us500-multiframe-native-v2-{2022,2023,2024}`: native manifests/snapshots,
  raw books/reviews/seals/events/progress/timers; qualityflags superseded.
- `us500-multiframe-native-v3-review-{year}`: corrected books, independent
  execution reviews/seals; sourceinput identity and financial invariants checked.
- `us500-multiframe-quality-review-v3.json`: sixnativeparity fixtures,
  correctioncensus/timers/sourcepins;0financialresimulations.
- `us500-multiframe-summary-v3/{summary.json,TABLE.md}`: authoritative aggregation.

Replay commands và pinned runtime ở [native guide](../../tooling/strategy-engines/README.md).
Không còn job chạy hoặc chờ. Broker/model/network calls0;2025+reserved.

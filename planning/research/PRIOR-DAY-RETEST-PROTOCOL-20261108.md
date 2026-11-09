# R019: phá mức ngày trước rồi kiểm lại — đăng ký trước outcome

Thuộc [campaign C1/C2](CHALLENGE-CANDIDATE-CAMPAIGN-V2-20261108.md).
Thay quyết định deferred của [admission cũ](LOCAL-SESSION-ADMISSION-20261108.md)
bằng một recipe thực thi được. Không sửa/ghi đè parent R015 hoặc kết quả cũ.

## Giả thuyết và thay đổi có chủ đích

[NYFed125](https://www.newyorkfed.org/research/staff_reports/sr125.html) và
[NYFed150](https://www.newyorkfed.org/research/staff_reports/sr150.html), official
summaries đọc lại08/11/2026, hỗ trợ cơ chế orders quanh levels và continuation
khi phá level. Chúng **không chứng minh** prior-day extrema, retest, H1 hay
ba giờ chờ của project. Không claim exact replication hoặc paper đã chứng
minh recipe có lợi thế. Không dùng dữ liệu/code paper.

Giả thuyết mới: chờ một nến sau breakout chạm lại level nhưng đóng cửa giữ
phía breakout có thể tránh một phần false breaks. Trade-off: ít lệnh hơn,
vào muộn và bỏ lỡ các trend không quay lại. Đây là trial mới có selection
exposure, không bug fix để cứu R015 đã thất bại.

## Exact recipe

ID `eurusd-h1-prior-day-retest3-atr14x1p5-close20-r025-v1`, catalogue R019.
Reuse native `IntradayH1Candidate`, range/ATR/cost/sizing/execution owner.

- H1 mid từ actual observed quote aggregates, chỉ biết OHLC sau đóng nến.
  Prior range như R015: ngàyUTC trước có≥18 observed hours, không quá4calendar
  days; Sunday thiếu giờ không thay range. Không padding hoặc sửa giá gốc.
- Khi flat, tại H1 decision **08–15UTC**, nếu close>prior high thì arm BUY,
  close<prior low thì arm SELL. Không entry tại bar breakout. Một **arm attempt**
  mỗi ngàyUTC, kể cả sau hủy, khác parent chỉ latch khi emitted entry.
- Chỉ xem **ba nến H1 liên tiếp sau bar arm**, tối đa3 giờ wall-clock. Không
  dùng intrabar order hoặc retest trong bar breakout. Gap giờ, ngày đổi hoặc
  range không còn hợp lệ thì hủy; không chờ đủ3observations qua gap.
- BUY: nến sau có low≤level và close>level thì entry signal; close≤level hủy
  trước, không chờ reclaim. SELL đối xứng: high≥level và close<level; close≥level
  hủy. Nến thứ3 được phép xác nhận; hết nến thứ3 mà chưa xác nhận thì hủy.
- Entry confirmation chỉ tại decision08–16UTC. Hết giờ thì hủy pending arm.
  Không đổi hướng/rearm sau hủy cùng ngày. Một emitted entry mỗi ngày, dù
  sizing/margin từ chối; không same-event reversal.
- SL1,5×WilderATR14 cập nhật tại confirmation decision. Planned25USD trên
  initial10k, floor lot/step0,01 như parent, không fixed TP. Exit decision20UTC
  hoặc ngày đổi, SL/gap theo core. Quote sau decision mới fill; thiếu quote
  giữ pending đến quan sát sau và ghi actual delay, không giả fill đúng giờ.
- State có armed side/level/time và arm-attempt day; export/restore đủ state.
  Pending chỉ thuộc R019; sai level/time/day hoặc state của candidate khác
  phải bị reject. Old candidate defaults vẫn nhận legacy states.

## Kiểm trước PnL và so sánh

Source/test/schema và protocol được commit/pin trước outcomes. Fixture receipt
phải có trước run: BUY/SELL, không same-bar entry, confirm bar1/bar3, expiry,
invalidation/one-arm latch, gap/day/clock, missing data, stale range, state
roundtrip/mutations và rejected position identity. Có native coarse fixture
kiểm next-quote entry/exit/SL/cash, không chỉ test tín hiệu rời rạc.

Giữ old16H1+3metal candidates: dùng predecessor code snapshot để kiểm legacy
signal/stop-distance/state fields trong prefix có vị thế và restore; defaults
mới chỉ None. Không lấy test pass làm C1/C2. Đây là offline opt-in candidate,
không dispatch tự động hoặc broker authority.

## Stage1: paired development2019/2022

- Hai năm đã consumed, không cleanOOS. Native bound H1 caches của
  `eurusd-observed-history-v2`; warmup≥100H1, dùng toàn bộ observed Nov–Dec
  năm trước như parent (không chỉ lấy100nến cuối),
  scope. Rehash raw/cache, kiểm schema/runtime/order trước load. Không download,
  export lại, đọc source đang ghi hoặc sửa binding để ép cache pass.
- R019 và parent R015 ×2costs ×2years =8books. Rerun bounded parent để kiểm
  behavior sau extension state và so cùng numerical source; không rerun624cases.
- Annual initial10k/risk25USD, một position, no force-close; không ghép hai
  năm thành account liên tục/CAGR. BidAsk embedded, commission2,50USD/lot/side,
  slip0/0,00002; fundingBUY9,30/SELL−0,31reference,20/20stress,22UTC/Wed×3.
  Costs khai báo, chưa target broker historical verification.
- H1 stop level/gap là approximation, không first-crossing tick hoặc prop
  equity/internal brakes. Ghi no-position periods, pending/end-open và gaps;
  không nhận H1 retention là edge hoặc permission.
- Metrics từng book: net equity gồm floating, cash, funding, trades/sides,
  signals/rejections, open/pending, mean/tails/concentration và monthly entries.
- **Frozen priority:** R019 net>0 ở cả4year-cost cases, ít nhất30closed
  trades mỗi year/cost. Không cần beat một metric parent được chọn sau outcome.
  So parent chỉ để hiểu trade-off. Heuristic không statistical significance.
  Fail thì không tự mở full batch/tune3hours hoặc SL; giữ exact negative.
  Near-zero/stop-sensitive không đủ hard-reject family; chỉ đăng ký tick
  diagnostic có lý do nếu uncertainty có thể đổi quyết định.

Nếu đạt stage1, đăng ký stage2 full2010–2022 và selection/stop/tick review trước
compute. Không tự mở2025+ hoặc chuyển protocol này thành quyền holdout.

## Artifacts/review/retrospective

Private campaign root `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`.
Output mới `execution-v1/prior-day-retest-v1`, driver/reviewer snapshot cùng
protocol/code/input/test receipt hashes trước PnL. Một writer, deadline300s,
progress/PID/events/CANCEL/failure; no automatic retry/overwrite.

Separate reviewer kiểm state transitions/ranking of times bằng implementation
khác, mọi financial trade/cash/funding/openmark, summaries và retention. Reuse
native source loader cho admission, không gọi nó independent source feed.
Fraction money oracle không import cost function; synthetic mutations phải
reject bad decision/fill/fees/source/scope. Cùng agent/provider không human/
model independent audit. Giữ cả review failures, không sửa frozen run outputs.

Sau batch ghi phasewall/CPU, lỗi/gap và next action. Chỉ tối ưu bottleneck đo
được; không tạo engine/framework/RAG mới. Goal vẫn active cho đến C1/C2 thực
sự; code/tests/coarse screens chỉ là các bước nghiên cứu.

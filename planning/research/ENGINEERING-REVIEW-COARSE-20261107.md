# Hậu kiểm và tối ưu sau pilot sàng lọc — 07/11/2026

**Đã giảm thời gian chuẩn bị dữ liệu mà giữ nguyên kết quả.** Đồng thời cập
nhật skill `engineering-retrospective` và nối nó vào bước đóng batch nghiên
cứu. Không tạo skill trùng, daemon tự sửa source hoặc tracker mới.

Scope: hậu kiểm [pilot H1](COARSE-SCREEN-REVIEW-20261107.md), chỉ dữ liệu đã
consumed. Không thay chiến lược, sizing, execution, chi phí, luật quỹ hoặc
holdout. Không chạy lại annual/tick study; chỉ tạo H1 cache theo binding mới
và kiểm sự tương đương của tầng xấp xỉ. Code Trader: `579ff52f`.

## Xếp ưu tiên và việc đã làm

| Ưu tiên | Phát hiện | Quyết định / kết quả |
|---|---|---|
| 1. Độ đúng | Coarse stop vẫn thiên về lạc quan; margin/risk/DD chưa đầy đủ | Giữ bắt buộc tick review, không tự reject/promote. Đây là giới hạn mô hình, không dùng tối ưu hiệu suất để sửa hoặc giấu nó |
| 2. Chuẩn bị dữ liệu | Profile thấy vòng gom nến tạo tuple/kwargs và gọi min/max hàng triệu lần | Đã dùng các mảng OHLC của từng giờ để cập nhật trực tiếp; A/B giảm median wall 16,0% |
| 3. Quy trình lặp | Skill có rồi nhưng chưa nói rõ hậu kiểm khi đóng screening/validation batch | Đã thêm trigger, reference theo domain và link từ strategy-research/workflow; chỉ hậu kiểm evidence mới |
| 4. Phần chậm tiếp | Parse/validate raw chiếm phần lớn profile sau sửa | Giữ nguyên bộ đọc và mọi guard; chưa đủ lý do rewrite decoder/Rust/GPU hoặc thêm dependency |
| 5. Compute/report | Cached screen cả nhóm vẫn dưới 2 giây | Giữ nguyên, không tối ưu tiếp đoạn nhỏ chỉ vì có thể làm |

## Hành vi thay đổi và luồng dữ liệu

Raw ticks vẫn qua đúng native reader: hash, grammar/date, thứ tự, Bid/Ask và
tick grid. Vòng gom H1 giữ các list OHLC trong một giờ, chỉ cập nhật extrema
khi có giá cao/thấp hơn; không tạo cấu trúc tạm cho từng quote như trước.
Extrema của mid vẫn tính từ mid thực quan sát, không lấy trung bình của Bid
high và Ask high vốn có thể xuất hiện ở hai thời điểm khác nhau.

Hour metadata, counts/sequence, spread, gaps, Decimal values và builder H4 giữ
nguyên. Không bỏ kiểm source/hash để reuse: source mới tạo binding mới, old
cache/attempt và source snapshot vẫn nguyên vẹn. Cache hiện hành của lần này
nằm tại `current-hours/` trong private root bên dưới; không sửa pin cache cũ.

Đánh đổi code nhỏ: thay vòng lặp gọn bằng sáu phép so sánh trực tiếp trong
hot path, giảm allocation/call overhead. Không thêm abstraction hay một
decoder thứ hai; không thay công thức số học hoặc điều kiện chấp nhận input.

## Số đo

Máy i5-9400F, Python3.12.10, một process. Benchmark prefix là 326.373 observed
ticks từ03–07/01/2022 đã dùng, ABBAAB xen kẽ, ba mẫu mỗi bản. Mỗi mẫu tạo cache
H1 mới, OS file cache đã ấm. Profiling tách khỏi các mẫu timing. Ba mẫu không
là capacity/p95 ổn định hoặc bằng chứng tốc độ của một năm dữ liệu.

| Phần | Trước | Sau | Cách hiểu |
|---|---:|---:|---|
| Median chuẩn bị cùng prefix |2,8754s|2,4152s|A/B cùng semantics; giảm16,0%, speedup1,19×|
| Chuẩn bị warmup+Q1 |73,3796s|55,0252s|Hai quan sát khác thời điểm; không nhận tỷ lệ giảm này là controlled full-quarter A/B|
| Cached8rules×2costs |1,8526s|1,7605s|Tham khảo một lượt mỗi bản; không quy cải thiện compute cho patch chuẩn bị|
| Tests liên quan |8tests trước pilot|9tests/2subtests,0,39s|Thêm regression extrema riêng, spread và boundary/gap|

Cold ở đây nói về cache chuyển đổi H1 chưa tồn tại, không khẳng định dữ liệu
chưa có trong OS disk cache. Không chia thời gian annual/native tick engine
cho1,19 hoặc lấy ratio423× của mô hình xấp xỉ cũ làm tăng tốc engine.

Profile trước:5.549.536calls, sau:2.939.446calls. Dưới profiler, reader sau
chiếm3,125/3,784giây cumulative, gồm parse/validation. Những thời gian này chỉ
để quy trách nhiệm, không trộn với timing A/B không profiler. RAM peak và thời
gian active research/code/review chưa đo đầy đủ; giữ unknown.

## Bằng chứng không làm đổi kết quả

- Focused `test_forex_coarse_screen.py`:9passed,2subtests. Case mới kiểm side
  extrema khác thời điểm, observed mid high/low, maximum spread, count/sequence,
  last timestamp và reset ở giờ mới sau gap. Các case cũ tiếp tục kiểm financing,
  pending, Friday, causality và tamper.
- So toàn bộ550warmupH1/1.537evalH1 từ7.241.724ticks với cache source cũ:
  **từng field JSON khớp**, không chỉ OHLC hay hash đầu/cuối.
- 133/372H4 và excluded timestamps khớp. **16/16coarse scenarios khớp mọi field
  trừ wall/CPU timing**, gồm decisions/trades/costs/cash/floating/open/pending.
- 78sealed artifacts của pilot gốc vẫn khớp hash. Không cần replay tick cả quý
  hoặc kiểm lại native core không đổi. Kết quả economic và qualification cũ
  giữ nguyên; parity kỹ thuật không biến Q1consumed thành cleanOOS.

## Skill dùng lại và kiểm chứng môi trường

Đã mở rộng [engineering-retrospective](../../.agents/skills/engineering-retrospective/SKILL.md),
thêm [reference cho lượt nghiên cứu](../../.agents/skills/engineering-retrospective/references/research-runs.md),
nối từ strategy-research và STRATEGY-WORKFLOW. Mỗi batch có evidence mới sẽ
được hậu kiểm gọn: tìm lỗi/nút thắt → chọn sửa nhỏ → parity/A-B → lưu delta và
next trigger. Không full-audit sau mỗi command, không ép có thay đổi mỗi lần.

Positive case đã áp dụng thật ở lượt này: nhận diện preparation hotspot, sửa,
đối chiếu và benchmark. Negative case walkthrough: chỉ hỏi tiến độ hoặc mở
lại report không đổi thì không gọi vòng profile/replay. Đây là walkthrough
và thực thi bởi agent hiện tại, chưa là thử routing bằng model độc lập.

Hai skill qua `quick_validate.py`, link audit2skills:0errors/0warnings.
Maintainer audit trước/sau:0errors/0warnings,21skills; global12.279B,
project10.133/65.536B, reserve55.403B, combined22.412B. Không sửa global config,
hook hoặc cài dependency. `quick_validate` thiếu PyYAML trong product venv;
đã dùng Python bundled có sẵn, không thêm dependency vào ứng dụng.
Repo workflow đã cập nhật; chưa publish package cho native Paperclip/Hermes.

## Evidence và điều kiện mở lại tối ưu

Private root:
`E:\BACKUP-TRADINGWORKSPACE\ai-engine-jobs\coarse-retrospective-20261107\execution-v1`.
`protocol.json` khóa câu hỏi/invariants/limits trước sửa; `input.json` giữ
prefix/raw pins. `prefix-benchmark.json` giữ6samples; `before.prof/after.prof`
và profile text giữ attribution; `parity-review.json` giữ full-field comparison;
`preparation/`, `coarse/`, logs/progress và source snapshots giữ output mới.
`evidence-seal.json` giữ hashes; không ghi đè attempt cũ. Không còn job nền.

Đã đủ để kết thúc lát tối ưu này. Chỉ mở lại parser/performance khi dữ liệu
mới hoặc quy mô thực làm preparation thành chờ đợi đáng kể; cần oracle/parity
cho decoder trước khi đổi. Bước nghiên cứu tiếp vẫn là chọn/freeze nhóm rules
nhỏ từ catalogue, không mở annual/holdout hoặc cứu version âm bằng tuning.

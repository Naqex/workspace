# Tick review: tối ưu giữ semantics trước full-history intake

Không new strategy/PnL. [Closing pilot](INDEX-CLOSING-TICK-CALIBRATION-RESULTS-20261109.md)
đã source-admitted8hours; dùng lại toàn bộ raw/export/review, không fetch lại.
Baseline result SHA `b8439892eb87566ac8ae6bd0c05c052a1bff92378732899c2dc14131b7eebf64`,
review SHA `ba9e105ee5af756ba4877b2daf0db607d14310115fcac25715f13c8a0abf7b69`.
Old Fraction reviewer giữ nguyên bytes/pins làm oracle, không sửa để candidate pass.

## Bằng chứng đã có trước candidate

Bounded cProfile2hours (8.672+30.861ticks) chỉ ra Fraction constructors chiếm
khoảng71% cumulative inspect time; regex/instance/gcd overhead, không là mẫu
speedup hoặc full-history ETA. Native offline decode/format toàn8hours khớp
objects/export hashes. Một full pin pass đọc312.832.166bytes, khoảng745ms;
old collector rehash cả canonical inputs trước/sau mỗi hour dù không dùng chúng
trong network/decode loop. Native decode riêng chỉ khoảng3–24ms/hour ở pass này.
Timers instrumented/one-pass chỉ là attribution. Records ở private
`execution-v1/index-tick-review-performance-v1/{baseline-profile,native-profile}.json`.

NumPy không có trong product venv. Thử stdlib integer-grid/compact columns trước,
không thêm dependency, GPU/Rust hoặc framework nếu chưa cần.

## Hai thay đổi được thử và tiêu chí

1. Tick inspection: giữ timestamp/price delta arithmetic dưới dạng integer units
   với grid0,001 đã khóa, volume theo đúng native millions normalization. Trả
   compact columns để aggregate/query quote mà không tạo Fraction/dict mỗi tick.
   Base-price normalization chỉ chịu existing1e-7 unit binary noise; observed
   export prices vẫn exact-grid, không nới tolerance theo outcome. Bool/string/
   NaN/negative volume/crossed/grid/order/schema/census/overflow/scope phải reject.
   Empty source giữ empty, equal timestamps giữ ordinal; không sort/dedup/pad.
2. Source collector pin guard cho future controller: full inputs kiểm trước lần
   dùng đầu và trước completed; code/protocol/config/package pins kiểm trong
   loop, raw response/output seals giữ kiểm từng hour. Canonical M1 inputs không
   được đọc giữa loop; consumer đọc lại phải full-hash trước dùng. Không mtime-only
   cache, sửa hashes/proof cũ hoặc dùng guard này cho live/trading authority.
   Default old controllers giữ nguyên; standalone helper có explicit active pins.

Correctness gate trước timing: toàn115.502ticks×5fields,960M1sidebars OHLC,
64quote locators/ordinal/wait/age khớp frozen Fraction oracle. Kiểm boundary,
duplicates/missing/flat/invalid values và mutations trên synthetic+actual.
Integer representation khác Fraction phải được đổi đơn vị chính xác khi so;
không chỉ so net hoặc checksum of count. Không benchmark trading conclusions.

Source guard: missing/changed code phải fail khi active check, changed input
trước initial/final phải fail; malformed/no active pins reject. Metadata guarantee
là before-use/commit binding, không claim bắt mọi transient rewrite của input
không đọc trong loop. Test semantic roles, không che lỗi bằng hash cache.

Benchmark A/B alternate3pairs trên cùng8hours cached inputs, warmup tách khỏi
timing, không profiling/tracemalloc trong timed candidates. Báo raw samples,
median/CPU/memory pass riêng; nhỏ không ổn định p95. Inspect gate ≥2×median
speedup và output parity; guard gate full-source bytes không tăng theo số hour,
vẫn đầy đủ before-use/final checks. Whole cached source+review measured riêng
nếu implementation có consumer thật; phase speed không suy nguyên batch.

Nếu candidate không đạt đủ correctness/value thì giữ baseline, ghi failed attempt.
Output mới trong performance owner hiện có, PID/status/timing/pins/failures,
deadline180s mỗi benchmark, no network/holdout/OrderSend/global config/raw rewrite.
Sau khi chọn implementation mới freeze long source và economic method riêng.

## Method fidelity vẫn tách khỏi speed

Parent Open15:59 exit khác cash close16:00. Scheduled exit đổi là recipe/model
revision, không optimization cùng semantics. Tick pilot hiện chưa có quotes sau
16:00; cần source admission bổ sung trước model dùng close. Không auto chọn
clock/delay bởi PnL hoặc gọi integer review pass là edge/prop qualification.

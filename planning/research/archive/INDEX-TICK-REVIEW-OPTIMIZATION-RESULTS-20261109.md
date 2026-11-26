# Kiểm tick nhanh hơn, giữ nguyên bằng chứng nguồn

Theo [protocol đã đăng ký](INDEX-TICK-REVIEW-OPTIMIZATION-PROTOCOL-20261109.md)
ở `3982c9e`. Chọn hai helpers mới cho consumer có scope phù hợp; không sửa
old collectors, frozen Fraction reviewer, raw hoặc kết quả chiến lược.
Không có PnL mới hay ứng viên challenge mới từ phép đo này.

## Kết quả đo

Workload: cùng 8 giờ cached development của closing pilot, 115.502 ticks,
Node v24.19.0, Python venv Trader hiện có. Warmup riêng; 3 cặp A/B đổi thứ tự,
timing không gắn profiler/tracemalloc. Không chạy hai benchmark đồng thời.

| Lát được đo | Baseline median | Candidate median | Kết luận trong scope |
|---|---:|---:|---|
| Python inspect, input đã load | 2,8907 s | 0,7256 s | Nhanh 3,98 lần, giảm 74,9% thời gian |
| Node cached replay: pin checks + raw read/decode/format/serialize/seal | 12,7991 s | 1,8189 s | Nhanh 7,04 lần; không HTTP/cooldown/output writes |
| Pin bytes mỗi replay | 5.318.345.365 | 636.545.370 | Full checks 17 → 2; 16 active checks vẫn giữ |
| Peak Python allocations riêng, giờ NASDAQ 30.861 ticks | 19.185.300 B | 1.288.788 B | Giảm 93,3%; không là RSS hoặc RAM toàn app |

Raw samples Python: Fraction 2,8806 / 2,8907 / 2,9163 s; integer 0,7256 /
0,7145 / 0,7340 s. Node legacy 12,7802 / 12,8223 / 12,7991 s; scoped 1,8495 /
1,8101 / 1,8189 s. Ba mẫu không đủ đánh giá p95 ổn định. Windows CPU thô được
giữ trong artifacts; không suy microbenchmark thành ETA toàn history/research.
Producer cũ 19,158 s và reviewer cũ 8,820 s gồm scope khác, không dùng làm
baseline A/B của helpers mới.

## Vì sao kết quả vẫn được giữ đúng?

`index_tick_review.py` dùng cột timestamp/giá nguyên (grid 0,001), giữ thứ tự
khi bằng timestamp, missing minute và cửa sổ nửa mở. Volume giữ native millions
normalization; observed native prices phải exact-grid. Raw base chỉ dùng
existing normalization trong sai số floating đã khóa, không nới theo PnL.
Output là derived compact columns trong RAM, chưa format cache/DB mới.

Trước timing đã so với frozen Fraction oracle: **577.510 fields / 960 M1 side
OHLC / 64 quote locators, ordinal, wait và quote age exact**. Baseline M1 đã
khớp canonical source ở pilot cũ; không tải lại nguồn. Cả 32 actual mutations
(price/clock/order/volume × 8 giờ) bị reject. 6 Python tests kiểm schema/type,
bool/NaN/overflow/grid/spread/order/census/empty/boundary/holdout; 5 Node tests
kiểm admission/final/missing/tamper/phase/caller mutation; 8 existing candle
provenance tests đạt. Không gọi số test là chứng minh edge.

`source_pin_guard.cjs` kiểm toàn inputs trước dùng và trước completed;
code/protocol/config/package active pins kiểm giữa loop. Không đọc canonical
M1 inputs trong loop, raw hash và output seals vẫn mỗi giờ. Guard latches
failure: khôi phục file sau phát hiện lỗi cũng không cho hoàn tất attempt đó.
Không dùng mtime-only/hash cache. Không claim phát hiện transient rewrite của
input không được đọc giữa loop. Consumer phải full-hash lại trước dùng input.
Node A/B dùng cùng pins, raw/decode/format và 8 serialized export hashes exact.

## Lệnh, artifacts và quyết định

Private base giữ nguyên:
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`.
Output `execution-v1/index-tick-review-performance-v1/`:
`{baseline-profile,native-profile,python-benchmark,node-benchmark}.json`,
progress/events theo PID, full pins, memory và raw samples.
Saved scripts `benchmark-index-tick-review-v1.py` và
`benchmark-index-source-pins-v1.cjs` tại private base; mỗi benchmark deadline
180 s và no-overwrite guard. Lượt này terminal 0, không network/PnL/broker.

Commands từ workspace:

```powershell
projects/trader/foundation_v2/.venv/Scripts/python.exe -X utf8 -m unittest discover -s tooling/ai-engines/tests -p test_index_tick_review.py -v
node --test tooling/ai-engines/tests/source_pin_guard.test.cjs
projects/trader/foundation_v2/.venv/Scripts/python.exe -X utf8 -m unittest discover -s tooling/ai-engines/tests -p test_candle_source_provenance.py -v
```

**Giữ hai helpers, không thêm NumPy/GPU/Rust/dependency.** Phạm vi index tick
grid và giờ development đóng, không generic tick parser hoặc trading authority.
Rollback: future consumers quay lại frozen reviewer/full checks; raw, pins và
old controllers chưa đổi. Skill workflow hiện có đã yêu cầu parity/phase/pins;
không cần skill mới chỉ cho hai helpers.

Hậu kiểm: correctness đạt trong pilot, performance đạt gate, reliability có
failure latch. Nút thắt lớn nhất đã gỡ là repeated hashing, không phải decoder.
Ngừng tối ưu lát này; bước tiếp là source admission quanh **16:00–17:00** trên
cùng dates/assets đã chọn trước, rồi đăng ký economic recipe riêng cho paper
cash-close window. Parent exit 15:59 vẫn là bản khác, giữ kết quả âm và lineage.
Không biến source availability thành broker latency hoặc edge.

# Pilot nguồn tick quanh cuối phiên, chưa tính lợi nhuận mới

## Vì sao và giới hạn câu hỏi

[Rest-of-day review](INDEX-REST-OF-DAY-RESULTS-20261109.md) không đạt gate;
giữ verdict/pins. Các books dùng next-M1Open, tức proxy một phút sau decision,
không actual measured broker latency. Trước thêm nhiều filters, kiểm xem dữ
liệu hiện có có hỗ trợ một future **timestamp-based execution scenario** rõ
hơn không. Không gọi đây là speedup, source repair, edge hoặc latency thật.

Không chọn ngày từ PnL: lấy first regular cashday tháng1 và tháng7 ở cả hai
development years, giữ dù source mismatch/empty. Hai instruments đang dùng
cùng provider Dukascopy: `usa500idxusd`, `usatechidxusd`.

| Ngày | Giờ UTC cần lấy | Giờ New York |
|---|---|---|
| 02/01/2019 | 20:00–21:00 | 15:00–16:00 |
| 01/07/2019 | 19:00–20:00 | 15:00–16:00 |
| 03/01/2022 | 20:00–21:00 | 15:00–16:00 |
| 01/07/2022 | 19:00–20:00 | 15:00–16:00 |

4 dates×2 assets =8 hours, các dates thuộc consumed development; không own
2025+. Source admission thu joint Bid/Ask ticks/volumes, không chỉ một side,
giữ ordinal cho equal timestamps. Tick clocks là archived event timestamps,
không actual delivery/processing time. Volume quote không exchange volume.

## Intake và phép kiểm khóa trước

- Reuse pinned `dukascopy-node` 1.51.1 local runtime, existing bounded fetch/
  raw cache/decoder và Fraction reviewer như các source pilots trước; đọc lại
  current installed hashes trước execution. Không cài/upgrade, account/OAuth,
  provider mới, trả phí hoặc broker. Một writer, deadline180s/CANCEL/progress/
  events/seals; không worker thứ hai lên cùng output.
- Một request mỗi instrument-hour; cache hit dùng lại, không bắt source fetch.
  Network qua existing public archive, batch1/300ms, retry0/WAFoff/token cacheoff;
  không bypass 403/429 hoặc fallback provider. Giữ partial seals/failure;
  existing recovery helper chỉ bounded transient network, không infinite retry.
- Output mới `execution-v1/index-closing-tick-calibration-v1`, source snapshots,
  protocol/package/runtime hashes, raw path/hash/config/request/rowcount/price
  grid/order/volume/BidAsk checks. Reuse source-hour-cache đã có nếu đúng identity.
- Reviewer dựng raw quotes bằng Fraction, so every observed tick price/clock/
  volume với decoder output. So full common-minute OHLC từng side với source-only
  M1 đã review, giữ missing/unpaired phút. Không sinh mid extrema, fake bars hoặc
  đổi multiplier/tolerance để ép match; conflict thì admission inconclusive.
- Kiểm riêng late signal 15:29 BidClose/known-at upper bound từ quotes; không
  đưa quote sau 15:30 vào signal. Previous close/09:59 không nằm trong pilot,
  tiếp tục là inherited source evidence, không claim all-feature tick proof.
- Chỉ thống kê quote availability/delay/count từ các target timestamps:
  decision15:30 và15:58 cộng200ms/1s/2s, next-M1Open baseline15:31/15:59.
  Tìm first quote theo timestamp/ordinal, báo wait/last observed age; không
  forward-fill/no quote thành giá bất biến hoặc chọn latency bằng PnL.

Không tính trade returns, net PnL, account/SL hoặc promote candidate trong pilot.
Một ngày source match không chứng minh mọi ngày/market/broker match. Nếu source
đủ dùng, freeze economic latency comparison riêng trước new outcomes, giữ same
signal/decision/costs và những assumptions đổi. Không lấy tốt hơn trên pilot
làm lý do rerun annual batch không đăng ký hoặc coi original exact results sai.
Nếu source không đủ, ghi đúng gap và chọn next bounded action, không archive chase
vô hạn hoặc bỏ goal chỉ vì một pilot inconclusive.

Consensus first-half/rest-of-day trong primary paper là hypothesis khác có thể
đăng ký sau, nhưng chưa chạy group PnL hoặc chọn filter từ parent trade outcomes.
Ưu tiên calibration trước để tránh thêm variants trên một execution proxy chưa
được đo. Đây là quyết định sequencing, không kết luận filter có hoặc không edge.

# R066 NASDAQ noise14: một tín hiệu đầu tiên mỗi phiên

Đăng ký trước implementation và outcomes. Theo [method admission](NASDAQ-NOISE14-METHOD-20261109.md),
transfer cơ chế bands của R048 sang NASDAQ; không đổi R065 để cứu negative.
Đây là adaptation mới: Bid chart, chỉ một entry attempt mỗi ngày, hard stop
và exit ở opposite band hoặc cuối phiên. Không replication paper SPY/VWAP/
volatility-target sizing, không mở param grid. Parent R048 negatives giữ nguyên.

## Exact recipe

- Candidate `nasdaq-noise14-first-break-opposite-stop-r025-m1-v1`, parent R048.
  Cash NY calendar/halfday đã freeze. Dev2019 và2022 đã exposed; warmup từ
  Nov–Dec2018/2021 chỉ tạo history, không entries/PnL. Không own2025+.
- Bid Open phút09:30 và Bid Close theo slot của mỗi phiên. Với đúng14 phiên
  lịch liền trước, mean absolute return cùng slot từ open; thiếu bất kỳ
  open/slot nào thì band unavailable, không tìm lùi phiên cũ để đủ14.
  Upper=max(todayOpen,previousCashClose)*(1+mean); lower=min(...)*(1-mean).
  PreviousCashClose là close phút cuối phiên trước, kể cả halfday.
  Reuse `index_noise_study.bands`; không dùng quote volume/VWAP.
- Quyết định sau close mỗi30 phút:10:00,10:30,…,15:30; halfday đến12:30.
  BidClose>upper BUY, <lower SELL, equality/no band không signal. Known-at
  minute close; fill đúng Open sau thêm một phút:10:01,…,15:31.
  Chỉ first nonzero signal trong ngày được thử vào. Thiếu/crossed fill hoặc
  không đủ quantity/margin thì bỏ ngày; không thử lại ở signal thuận lợi sau.
- Stop cố định ở opposite band của entry decision, floor0,001 cho BUY,
  ceil0,001 cho SELL. Dùng actual Ask/Bid entry để tính distance/quantity.
  Không TP/trailing. Sau entry, first opposite nonzero band signal quyết định
  market exit cùng độ trễ. Neutral hoặc cùng side không thoát/re-enter.
  Cuối phiên exit Open phút15:59 hoặc12:59. Không mở lại trong cùng ngày.
- Native open-gap SL trước market exit; sau đó native intrabar SL. BUY dùng
  Bid, SELL dùng Ask. Missing decision khi flat ghi unavailable; missing
  held minute làm exact model unknown và block future entries/năm.
  Scheduled/opposite exit chỉ có hiệu lực khi đúng source minute tồn tại.
- Mỗi năm10.000USD, fixed25USD plannedrisk, không compounding. NASDAQ contract1,
  step/min0,01/max50/leverage10; source Bid/Ask embedded; commission0 và
  slip0,25/0,75 mỗi side, funding0 vì intraday theo declared model. Reuse
  `nasdaq_h4_study.market`, native sizing/protection/cost. Đây chưa target
  broker specs/history/actual fill. Risk budget không bảo đảm loss<=25 khi gap.

## Exact và sensitivity tách verdict

Chạy hai exact books/cost/year cùng null controls. Đồng thời đăng ký
sensitivity H1-envelope theo [R065 bounds](NASDAQ-OPENING5-BOUNDS-PROTOCOL-20261109.md):
giá chưa thấy nằm trong H1 cùng side, parent-style protective execution
không rejection; missing held minute thêm possible SL interval BUY[H1low,SL]
hoặc SELL[SL,H1high], giữ nhánh sống tới known SL/opposite/final exit.
Không TP nên không có TP branch. Missing terminal minute hoặc H1 thiếu/
excludes observed M1 → inconclusive. Entry eligibility phải giống nhau trên
toàn cash interval; khác thì inconclusive. H1 retrospective không dùng entry.
Conditional cash không làm original unknown biến mất hoặc cấp broker authority.

Giữ exact positive/negative/unknown và conditional intervals, đủ16books:
2years ×2costs ×2models ×2null. Null không tạo trades, equity0.
Nếu exact stress cả2years knownflat/net>0 và>=100trades/year: đủ ưu tiên
research stage tiếp, chưa edge/OOS/prop/forward. Exact unknown thì chỉ xem
conditional lower>0 ở cả2years là ưu tiên giải uncertainty. Conditional
upper<=0 ở bất kỳ stressyear: gác exact recipe. Bounds cắt0 giữ inconclusive.
Không đổi gate/clock/risk/SL/exit sau outcome; model variant không tăng policy count.

## Kiểm và artifacts

Fixtures trước numeric: prior14 chỉ dùng quá khứ, missing required slot không
backfill, halfday/DST, equality, entry/exit latency, one attempt/day, side SL,
rounding/risk/margin, open-gap ordering, unknown freeze và conditional cash.
Reviewer Fraction riêng cho band/first signal/entry/exit/sizing/cost/state;
đối chiếu exact/conditional khi không gặp uncertainty, null và source seals.

Private output `challenge-discovery4-20261108/execution-v1/nasdaq-noise14-v1`:
config/manifest/source pins, plans/books, progress/events/timing, result/review.
One writer, CANCEL, deadline180s. No network/model/broker/holdout calls.
Reuse data từ reviewed `nasdaq-m1-history-v2` (warmup+2019), mixed2022 từ
`nasdaq-tick-derived-hour-v1`, H1 từ `nasdaq-history-v1`; hash-bind parent
results/reviews và every used book/session trước outcomes. Không raw rewrite.

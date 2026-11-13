# XAUUSD H1 — Stage-0 Raw Markout Discovery

Owner mở **chiến dịch mới**, không mở lại EURUSD B1/XAUUSD B1 đã hủy.
Scope: Development2022–2023, seed từ01/11/2021; không đọc giá2024–2026.
Chỉ 3 recipe cố định × BUY/BOTH, không parameter sweep, chưa bot SL/TP,
account replay, sizing/risk search hoặc challenge. Giữ lịch sử thử cũ.

## Quy tắc đóng trước outcomes

Giá tín hiệu: admitted BidM1 → H1 đủ60phút; H4 đủ4H1 liên tiếp, UTC buckets.
Không padding bar thiếu. SMA20 và WilderATR14 liên tục, dùng bar đã đóng;
MA/ATR để xác định vùng và buffer lấy **trước bar tín hiệu**. Không volume filter.
Entry decision H1close lúc08:00–15:00UTC (baropen07–14), weekday; firsttick
>=decision, wait≤60s. Không giả đây là calendar London/NewYork theo DST.

Bias chung H4: last completed close>SMA20 và SMA20>SMA20 của3completedbars
trước → BUY; SELL đối xứng. H4age>8h hoặc chưa đủ indicator → không có bias.
Đây là lựa chọn H4 trong phạm vi D1/H4 owner nêu, không chạy thêm D1 variant.

| ID | Cơ chế cố định | Natural stop geometry, chỉ đo khoảng cách | Horizon chính |
|---|---|---|---|
| H1A_ASIA | Có đủ6H1 00–06UTC; H1close vượt AsianHigh, previousclose≤AsianHigh và H4BUY. SELL đối xứng với AsianLow/H4SELL. Chỉ tín hiệu đầu tiên/ngày cho recipe, khóa trên BOTH trước khi lấy viewBUY. | BUY=AsianLow−0,10ATR14H1; SELL=AsianHigh+0,10ATR. Thesis phá toàn vùng bị vô hiệu khi qua phía đối diện; không nới sau khi xem phí. | +8h |
| H1B_RECLAIM | H4BUY, previousH1close≤lockedSMA20H1, currentclose>lockedSMA20 và currentclose>open. SELL đối xứng. Cần previousbar liền trước. | Low của2H1 hiện tại/trước−0,10ATR choBUY; high+buffer choSELL. | +24h |
| H1C_MOMENTUM | H4BUY; currentclose−previousclose≥1,0ATR14H1, thân nến tăng, lows3H1 liên tiếp tăng dần. SELL: giảm≥1ATR, thân giảm, highs giảm dần. | Low thấp nhất3H1−0,10ATR BUY; high cao nhất3H1+buffer SELL. | +8h |

BUY là subset của BOTH, không cộng thành6 alpha độc lập; báo SELL để giải
thích BOTH, không promote thêm SELL-only. Các recipe/horizon cũng có thể overlap.
NaturalSL không là order/exit đã chạy; chưa TP, trailing, partial hoặc filter phí.

## Markout, costs và coverage

- Cả4mốc **+4/+8/+24/+48giờ lịch** từ observedentry, không đổi thành số nến
  giao dịch hoặc dời mốc cuối tuần sang thứHai. +48h ở cuối2023 chạm2024 →
  censored, không mở năm mới. Missingquotes giữ nguyên và báo mỗi cohort/horizon.
- BUYAskentry/Bidliquidation, SELLBidentry/Askliquidation; freshquotewait≤60s.
  Tick nativeDukascopy hiện có, reuse raw hashes, chỉ bổ sung giờ cần thiết.
  Chưa cần đọc toàn đường giữ để đo DD/SLTP: chỉ fixed-horizon markout.
- Commission proxy owner đã dùng:0,000007×(entryprice+exitprice) USD/oz.
  Reference slip0; stress slip0,40USD/oz/cảvòng. ObservedBidAsk đã chứa spread.
  Benchmark friction execution=(entryspread+exitspread)/2+commission+slip.
  Admission scale dùng entryspread+2×entryprice×rate+slip, biết tại entry.
- **Funding proxy khóa trước:** reference−20USD/lot/rollover, stress−40USD/lot
  (=−0,20/−0,40USD/oz), cảBUY/SELL; weekdays22UTC, Wednesday×3. Count các
  events `entry<rollover≤exit`. Đây là giả định bảo thủ kế thừa, chưa swap
  FTMO thực tế/asymmetric/date-specific; không gán swap0 cho24/48h.
- Net markout phải trừ financing; báo riêng gross/spread/commission/slip/swap.
  Scenario là counterfactual cost model, không thực thi broker hay giá target.
  Thiếu targetspec/news/calendar vẫn chưa prop qualified.

## Stage-0 và output đã khóa

Theo [gate](../../.agents/skills/strategy-qualification/references/validation-gates.md#stage-0-unconditional-markout--scale-screen):
raw mean netstress horizonchính dương từngnăm và ≥mean executionfriction cùng
cohort/đơnvị. Median ex-anteF/median naturalSL ≤12% (15% chỉ diagnostic;
không đổi cap sau outcome); từng tín hiệu F/SL≤12% phải giữ≥50%, báo cả15%.
Số lượng theo từng năm:40 là sàn suitability,80 là mục tiêu, không ép quota.
Không lọc tín hiệu trước markout để làm đẹp; SLinvalid/data rejection tách riêng.

Không chọn horizon phụ lời nhất rồi gọi primarypass. Báo cả ma trận4horizons
và kết quả primary từng recipe. Missing endpoints làm số liệu conditional;
không gọi là pass đầy đủ trên rawcohort. Phân biệt positive-in-observed-model,
economic-fail, cadence/scale-fail, data/calendar unknown; không lấy partialmean
làm bằng chứng kiếm payout. BUY/BOTH/horizons không độc lập; bootstrap theo
cụm ngày2.000lần,seed20261113,95%percentiles; chưa multiple-trial adjusted.

Freeze protocol/code/cost/data/census trước markouts; count-only không PnL
được phép trước quote fetch. Fixtures causalH4/H1/clock/ATR/geometry/BUYsubset,
fees/Wedtriplerollover/weekendmissing/holdout trước run. Independent arithmetic
self-audit sau run, không gửi ASTRA. Một writer, deadline/retry/cancel/logs,
raw/failedattempts giữ nguyên. Kết quả/counters/timers → JSON + báo cáo,
commit/push/một PR, chưa tự merge hoặc đóng gói bot từ kết quả đẹp.

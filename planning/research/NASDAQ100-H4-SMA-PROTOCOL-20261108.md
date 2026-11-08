# R061: NASDAQ H4 SMA20/80, frozen development pilot

Đăng ký trước outcome sau [source/history admission](NASDAQ100-HISTORY-RESULTS-20261108.md).
Một recipe,2years ×2declaredcosts; không search/grid. Parent R002, khác asset/
Bidchart/source basis, không independent edge hoặc exact AQR replication.
Hypothesis: trend-following H4 có thể giữ net economics trên NASDAQ CFD trong
cả2019 và2022, thay vì chỉ thắng một hướng thị trường. Có thể bị bác bỏ.

## Rule và causal ordering

`nasdaq100-h4-bid-sma20-80-atr14x2-r025-h1proxy-v1`, workspace tooling-only.
Reuse `advance_atr14`, Candle, protective exit, USD sizing/financial primitives;
không mượn US500/XAU instrument hoặc gọi prototype là native tick integration.
Source `usatechidxusd`/`USATECH.IDX/USD`, UTC/ms, sourcegrid0.001.

- H4 UTC00/04/08/12/16/20, chỉ khi có đủ4BidH1 chính xác. O/H/L/C tổng hợp
  cùng Bid side; không mean side extrema. Incomplete group không observe,
  không impute; SMA đếm80completed observations, không80wallhours. True range
  dùng previous completed close qua gap; Wilder ATR14 seed mean14TR.
- Warmup Nov–Dec trước mỗi developmentyear, no positions/actions/PnL. State
  history giữ qua Jan1, account reset10k mỗi year. Không reset theo tháng.
- Sau barclose, diff=SMA20−SMA80. Flat: cross<=0→>0 BUY, >=0→<0 SELL. Holding:
  BUY thoát nếu diff<=0, SELL thoát nếu diff>=0. Không reverse cùng decision.
  Stop cố định2ATR14 tại entry decision; không TP/trailing/reentry khi chỉ còn
  cùng dấu diff. Không thay rule sau khi xem outcomes.
- Signal known tại H4end, fill đúng sourceH1Open ở **decision+1hour**. Open là
  intervalproxy, không actualtick tại timestamp đó. Pending thiếu exact fill
  hour bị cancel+log; không fill lại ở quote tiếp theo. Chưa có hourly quote
  thì không biết chắc SL đã kích hoạt; holding qua gap phải đánh unresolved.
- Mỗi H1: calendar funding tới start → gap flag → opening-gapSL → pending
  action nếu đúng giờ/khôngpositionconflict → intrabarSL bằng Bid BUY/Ask SELL
  → H4close decision. SL intrabar có interval, không fabricated exacttime.
  BUYentryAsk/exitBid, SELLentryBid/exitAsk. Dùng observed side OHLC/spreads,
  gapstop ở opening worse-than-stop, adverse slippage do costmodel đúng1lần.
- Một position, planned stop budget25USD gồm2slips+rounding reserve+commission;
  adverse gap/funding có thể vượt25, không gọi hard maxloss. Không internal
  daily/overallkill hoặc prop compliance claim từ H1. Cuối mẫu giữ vị thế và
  pending, mark final observed Close; không forceclose. Báo mark timestamp.

## Declared economic contract, không target broker specification

USD account10k; one research unit worth1USD/priceunit, step/min0.01unit,
max50units, sourcegrid0.001, leverage10. Đây là scenario geometry, không quỹ
lot/point/tickvalue. Sizing/margin phải gồm contract multiplier và stop rounding.

| Scenario | Spread | Slip/side priceunits | Commission | Calendar funding debit |
|---|---|---:|---:|---|
| Reference | Observed separate Bid/Ask | 0.25 | 0 | Notional at entry ×8%/365/day |
| Stress | Same observed sides | 0.75 | 0 | Entry notional ×16%/365/day |

Funding debit cả BUY/SELL, cent HALF_UP mỗi event22UTC mỗi calendar day kể cả
weekend, position đã tồn tại trước boundary mới charge. Không tripleweekday,
credit hoặc giả FTMO swaps. Missing hours vẫn calendaraccrual đến endexclusive;
nếu stop time unresolved thì funding cũng modeldependent. Public FTMO index
commission0 đã kiểm ở source admission; không historicalterms claim. Dividend
adjustment/target contract chưa biết; coarse outcome không đủ promotion.

## Input, execution, review và retention

Reuse immutable source books của `execution-v1/nasdaq-history-v1` tại private
campaign root. Pin exact resultSHA858a86b14c739a91a1751fa9b5aff388453e5cbc347beae91cce7232f72ff9c0,
reviewSHAc110b26d059694e9aa7d774e51c6aadadd553da867b19c45999a86ff67b54400,
8book hashes và source config. No network, no2025+, historicaldevelopment,
cleanOOS=false. Raw/normalization không đổi. Hash/identity/roles/OHLC/grid,
crossed Open/Close phải guard trước simulation; không đọc search snippets làm
numeric source. Source H1review đã xong, không tải/parse ticks lại.

`tooling/ai-engines/nasdaq_h4_study.py` + focused fixtures phải xong **trước**
4numericbooks. Causal prefix/future mutation, H4missing, crossings/warmup,
stopgap/SELLside, exactpendingexpiry, funding22UTC/weekend, sizing/risk/margin,
cash/float và finalopen phải có kiểm. Mọi materialbug giữattempt/rerunaffected.
Driver/reviewer tại campaignroot, output mới `execution-v1/nasdaq-h4-sma-v1`;
onewriter/PID/progress/events/failure/CANCEL/deadline120s; source snapshot/hash
trước PnL. Reviewer khác arithmetic (Fraction), tự dựng H4/cross/ATR/state
và mọi trade/cost/funding/summaries, mutation wrongprice/time/missingdecision/
funding/authority reject. Cùng agent không là independent human/model review.

Chỉ **retain for further research** nếu cả2stressyears netequity>0 và mỗiyear
>=20closedtrades, verified arithmetic/source. Thiếu íttrades hoặc unresolved
path nghĩa evidence limited; âm đáng tin theo declaredmodel gác exactrecipe,
không reject cả family. Dù retained vẫn phải tick/gap/targetcost/selection-aware
OOS/prop3–6–12month/forward/handover trước challenge. Không tune side/SL/cost
để cứu kết quả. Ghi negative và timing; optimize chỉ khi evidence bottleneck.

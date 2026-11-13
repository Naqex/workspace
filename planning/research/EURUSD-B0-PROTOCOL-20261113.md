# EURUSD B0 — đăng ký triển khai đã được owner duyệt

Task STRATEGY-E2E; parent [card đã duyệt](PROP-DESIGN-FROM-CONSTRAINTS-PROPOSAL-20261113.md).
PR70 merged `0a8542ba`; source thiết kế `ee616c8`. Chỉ **B0**, không B1,
không XAUUSD, sizing sweep hoặc broker. Freeze protocol/config/source snapshot
trước khi đọc outcome mới; corrections phải giữ attempt cũ và lý do.

## Scope và clock

- Indicator seed 01/11/2021 UTC; warmup chỉ indicator. Development2022–2023;
  historical validation2024 **đã exposed**. User yêu cầu cả ba năm, nên vẫn
  đo2024 nếu Development thất bại; không dùng2024 sửa B0.
- Giá2025–2026 đóng hoàn toàn. Loader chỉ nhận bốn partitions2021–2024 và
  kiểm upper timestamp <01/01/2025. Không network fallback/data download.
- CSV QDM / lossless native prepared ticks, observed Bid/Ask, source order
  (kể cả same-ms). Giá nguyên đơn vị0,00001; source UTC, session Europe/London,
  daily accounting Europe/Prague. Không volume filter/padded candles.
- M15/H1 từ Bid tick; chỉ admit bar có quotes ở đủ15/60phút. Gaps không được
  forward-fill. WilderATR14: seed mean14TR, rồi(13ATR+TR)/14, qua observations
  admitted; TR đầu=high-low. SMA20H1 có slope so3completedH1 trước. Indicators
  liên tục xuyên năm, không reseed/reset. Không diễn giải observational gaps
  thành outage xác minh hoặc full-feed certificate.

## B0 state machine (không tối ưu)

1. Zone từ bốnM15 07:00–08:00London; thiếu một bar→ngày không có zone.
2. H1bias theo card, xét tại breakout và mỗi bar đợi retest. Breakout bar
   mở từ08:00, **đóng trước11:00**, BidClose vượt zone0,10ATR trướcbar.
   Khóa ATR buffer. Không lấy H1 đang chạy hoặc ATR của breakout.
3. Bốn bar kế tiếp: firsttouch khi range giao edge±buffer. BUY cầnclose>
   edge+buffer vàclose>open; SELL đối xứng. Bias đổi/firsttouchfail/expiry/
   11:00→cancel. Gap mộtM15 khi pending→cancel_unknown; barcancel không được
   dùng lại tạo setup ngay cùng event. Không mở vị thế từbarđóng11:00.
4. First observed quote **timestamp >= barclose** (bar gồm ticks <close);
   đây là event mới, không tick cuối bar. Quote trễ>60s→execution unknown,
   không lấy quote xa thuận lợi. BUYAsk, SELLBid; naturalSL từretestextreme
   ±buffer round ra ngoài grid. TP2×distance từentryquote; SL cố định tuyệt
   đối, không dời theofill nhằm qua cap. Entrygap làmSLkhônghợplệ→skip.
5. Một setup/position; tối đa2fills/Londonday. Sau exit, barclose mới phải
   **lớn hơn exittimestamp**; không reuseevent. Costskip cũng consume trigger.
6. First-crossing observed tick: SL fill tại liquidation-side quote (gồmgap);
   TP fill tại limit level, không priceimprovement; timeexit firsttick>=12:00.
   Native protective priority trước timedexit trên cùngquote. Tickorder giải
   SL/TP, không giả thứ tự M1. Missing cutoffquote/activegap>60s giữ data flag;
   không biến lastquote thành syntheticclose. Ngoài observedcoverage, DDunknown.

## Economics cố định

- 50.000USD đầu **mỗi sổ năm**, R0=150USD (0,30%), khôngcompounding. Indicator
  state vẫn liên tục. Báo annualreset và pooledsum, không CAGR.
- Dùng nativeInstrumentSpec/CostModel/sizing/accounting từ D:Trader checkout;
  tick0,00001,100k/lot,min/step0,01,max50lots, leverage30; đây là declared
  historical geometry dựa capture02/11/2026, không historicalbroker certificate.
- Common quantity cho hai fee scenarios: floor theo **stress** stoprisk+
  roundtripfees+native1gridreserve; margin <= currentcash−150USD. Commonstress
  sizing/admission giúp cô lập costdelta, không hai alpha versions.
- Reference commission2,50USD/lot/side,slip0; stress cùngcommission+0,00002price/
  side, tổng9USD/lot/roundtrip. Slippage là debit riêng theo nativecostcontract;
  không cộng vàofill rồi trừlầnnữa. Entry/exit observedspread đã ởgross.
- Admission dùng **entryspread** làm ex-ante reserve cả vòng của midbenchmark:
  F_plan=lot×(entryspread×100k+9); F_plan/R0<=12%. Không biết spreadexit trước.
  Realizedspread=0,5×(entryspread+exitspread)×lot×100k. Báo realizedtails/vượtcap;
  không trừ spread một lần nữa khỏi grossBidAsk. R_price=lot×distance×100k.
- Nativeaccounting round cents; báo cả exactdecimalreconciliation trướcround.
  GrossUSD/lot=sum(gross_after_spread)/sum(lots), không mean ratios/tradewins.
  NetR0=netUSD/150; annual gồm tháng0/losses. Nativecost là declaredmodel,
  không chứng nhận biểu phí tài khoảnFTMO cụ thể.

## Hai data gates còn thiếu: không âm thầm bỏ filter

Chưa có full lịch **known-at/historical** restrictedEUR/USD events2022–24,
hoặc datedtargetsymbolsession/rollovercalendar. CalendarFOMC hiện có không đủ
chứng minh cả CPI/NFP/GDP/ECB. Không tự gọi noevents hoặc targetswap0.

- Strict funded-compatible B0: **BLOCKED_BY_CALENDAR** khi hai inputs chưaadmit;
  runner không phát strictacceptedorders/propqualification.
- Lượt này vẫn đo **conditional B0 economic diagnostic** theo yêu cầu owner:
  nguyên signal/SL/TP/admission/card, execution sessionLondon và declared
  rollover21:00UTC (cutoff20:45UTC, muộn hơn12London), có trường
  `news_checked=false`, `target_calendar_verified=false` cho **mọi** intent/trade.
  Đây là counterfactual trước news/targetcalendar admission, không variantB1,
  không giả fullB0/Standardfunded evidence. Net được gọi `conditional_net_usd`;
  financing0 chỉ theo declaredrollovermodel và khi thực sự cóobservedflatquote.
  Strictcadence/net giữN/A; không đưa conditionaltrades qua G4/gatechallenge.
- Nếu một vị thế không xác nhậnflat/cópathgap: tách metricbound/uncertainty,
  không cộng vào exactqualifiednet. Không promote dùconditionalPnLdương.

Officialrefs kiểm13/11/2026: [news](https://ftmo.com/faq/can-i-trade-news/),
[symbols](https://ftmo.com/en/symbols/). FAQ có exceptionChallenge/Verification/
Swing; localcard chủ động nhắm fundedStandard, không dùngexception để xóa
newsfilter. Publicschedule không là dated2022–24accountcalendar.

## Counters / output / integrity

Validzones→biasbreakouts→firsttouchconfirmations (pre-cost)→costrejects→other
rejects→conditionalfills. StrictfillableN/A táchriêng. Mỗi intent giữ parentzone,
breakout/retestknownat, naturalSL, price/cost/quantity, skipreason. Thống kê SL
pips trướcadmission vàfills, BUY/SELL/year, F/R0median/p90/max vàtails,
grossUSD/lot vs9USD và Catalogue13historical0,69–8,19; mean/annualnetR0.

Dailyanchor=balance lúc00:00Prague; strategyflatgiữangày nên dailybalance /
equityanchor trùng. WorstDailyLoss=max(anchor−observednetliquidationequity,0).
Mark ởmọitickkhipositionopen, entryfee/slip tạientry, exitfee/slip khi exit;
peakDD trênnetobservedequity; báo thêm liquidationcostreservebound/staticloss.
Nămreset không xóa globaldrawdown: pooledRpath có nămflat tại boundary;
daily metrics vẫn yearlocal. Đây không FTMOlifecycle/time-to-pass replay.

Privateoutput dưới `execution-v1/eurusd-b0-20261113/`; source/config/protocol
hash, events/status, prepseals, tickcounts/coverage, decision/tradeJSON,
reconciliation, fixtures vàtiming. Một writer, boundeddeadline/cancel marker.
Reuseraw/prep chỉ khi bindings/hash đúng; failedattempts giữnguyên. Xuấtphễu
trước bảng economics từcùngfrozenreplay; không replaylầnnữa chỉđểđếm, không
sửa rules saucount. B1/A chỉ ownerduyệt riêng.

Gate trướcfinancialrun: causal/H1/ATR/retest/SL/grid/costcap/sizing/DST/
sameevent/SLTPorder/costaccounting/sourceholdout/tamper tests và nativeparity.
Kết quả xấu không cho phép chỉnhthreshold/exit hoặc mở giá2025+.

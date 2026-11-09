# Tuần đáo hạn: phép thử lịch riêng, không mặc định có lợi thế

10/11/2026, sau ECB archive không được admit intraday. Goal C1/C2 chưa đạt.
Rà catalogue92/58 trước: R025 đã có turn-of-month, chưa có exact monthly
options-week component. Đây là lịch/option-inventory hypothesis liên quan
R025 và equity flow; chưa independent edge hoặc account policy.

## Đối chiếu primary trước chọn phép thử

| Hướng | Bằng chứng đọc mới | Quyết định |
|---|---|---|
| Pre-holiday large-cap | [Ko/Yang](https://cfr.ivo-welch.info/published/papers/ko2021pre.pdf), §§1–2/Tables1–2: extension1983–2019 yếu đi ở large caps, gồm S&P500; không suy headline1963–82 thành current opportunity | Hạ ưu tiên phép thử chỉ dùng lịch nghỉ trên US500; không thêm own market trial |
| Even-week FOMC cycle | [Knox/Vissing-Jorgensen, FEDS2026-023](https://www.federalreserve.gov/econres/feds/files/2026023pap.pdf), §6/figure5/table5: opposite cycle2017–21; average good news không tự là permanent risk premium | Không thêm unconditional even-week long hoặc đảo chiều để cứu sau khi đọc kết quả |
| Monthly options week | [Stivers/Sun2013 publisher](https://www.sciencedirect.com/science/article/abs/pii/S0378426613003051), abstract/highlights; [QC implementation](https://www.quantconnect.com/research/15295/option-expiration-week-effect/) method/embeddedcode đọc | Một own transfer probe trên US500, chi phí đầy đủ; không paper replication hoặc dùng hiệu suất QC làm evidence của mình |

Đọc full Ko/Yang và §6 Fed; không gọi full Stivers/Sun method đã đọc khi chỉ
có abstract. QC là primary implementation, không original empirical paper.
QC dùng OEF/S&P100, schedule Monday10:00 và liquidate trong OnData của expiry
date, **không explicit expiry closing auction**; behavior holiday/fills không
tự suy từ mô tả. Own rule dưới đây khóa timing riêng, không copy/chạy code QC.
Native1.51.1 inventory không thấy OEF; USA500CFD không cùng instrument/universe.

Một [Auburn dissertation](https://auetd.auburn.edu/bitstream/handle/10415/9299/Matt%20Flynn%20Dissertation.pdf?isAllowed=y&sequence=2)
có search preview nói hedge relation đổi theo retail activity; web và direct
fetch timeout, chưa đọc fullmethod hoặc verify numerical evidence. Giữ cảnh
báo bất định, không chọn long/short theo snippet hoặc coi full audit đã xong.
Market volume/delta/open-interest không có; calendar không là observed dealer hedge.

## G0: recipe và quyết định trước market source/outcomes

Candidate `us500-monthly-options-week-calendar-price-component-v1`, dự kiến
R093 khi financial trial thực sự chạy; catalogue92/58 giữ trước đó. Own-code,
fixedunit1USD/quoted-index-point, không vốn tài khoản hoặc risk0,25%/SL.

- Discovery hai năm **2019 và2022** đã consumed; không clean OOS/own2025+.
  Mỗi tháng lấy tuần Monday→thirdFriday; endpoint cuối là last cash day trong
  tuần ấy (Thursday khi GoodFriday). Vào first cash day của tuần, kể cả Tuesday
  nếu Monday nghỉ. Đây là own transfer, khác QC scheduling đã nêu.
- Causal calendar từ `nasdaq_cash_calendar.calendar_for`/cash_sessions hiện
  có; thirdFriday là anchor lịch, không endpoint settlement AM của SPX. Entry
  decision tại cashopen, target sau60s; exit decision2phút trước cashclose của
  ngày cuối, target sau60s. NYhistoricalDST/earlyclose giữ; không fixedUTC−5.
- Control duy nhất: BUY cùng rule trong tuần liền trước, đã khóa trước giá;
  không thêm post-expiry short, khác week/entry/holding/side grid. 12months ×
  2roles × 2years = **48windows,96endpoint hours**. Không đếm controls thành
  independent strategy, matched windows không cùng path/holding/macro events.
- Tick source nativeDukascopy1.51.1, `usa500idxusd`, 0,001grid, full joint
  Bid/Ask và same-ms order. Lấy first quote tại/sau target, wait≤60s, exit phải
  trước cashclose. Quote volume không là exchange volume/executable liquidity.
- Reuse exact raw cache trước GET; tối đa96logicalhour requests,1worker,
  300ms pacing sau miss, retry0, timeout/deadline180s, CANCEL/PID/progress/seals/
  source snapshots. Giữ partial failure, không auto restart hoặc padding.
- Review tất cả sourcefields bằng native/integer decoder và Fraction decoder
  riêng, manual UTC calendar oracle, source/authority/clock/price/count mutations.
  **Cả96locators đủ mới mở economic computation**; thiếu giữ unknown và dừng
  source admission, không đổi thời gian/loại tháng để cứu.
- Core accounting hiện có, zero-commission scenario giữ như R086: source
  Bid/Ask spread embedded; slippage0,25/0,75 mỗi chiều; funding8%/16% annual
  notional vào entryAsk, cents từng debit tại22UTC mỗi calendar day trong
  actual entry→exit. Đây là declaredscenario, không exactFTMO/The5ers historical
  cost/spec. Không zero-swap hoặc broker/account calls.
- Tách midpointbenchmark → embeddedspread → commission/slip → funding →
  rounding → net; không trừ spread lần hai. Nullnoexposure0 chỉ là accounting
  control, unknown quote không thành null. Không intrapath/SL/margin/account/
  dailyDD/brokerfill hoặc actual challenge simulation ở component này.
- Frozen triage: **mỗi năm** primary strict stressnet>0 **và** lớn hơn control
  strict stressnet. Hai năm cùng đạt mới đăng ký temporal robustness trước
  risk wrapper; đây là chọn việc tiếp, không statistical edge/prop certificate.
  Không tune cost/calendar/holding sau outcome, không flip sign. Báo sample,
  concentration và annualgross/net; không lấy12events làm đủ statistical sample.

## Source evidence và review

Private `execution-v1/options-calendar-method-sources-v1/` giữ 4downloadedfiles
và dissertationtimeout:KoPDF SHA`039d0939df6c5096a9b4aa4918fea95db0230f21cde1f9eabab772e430637b1b`,
FedPDF`0fa80a4af119ceb69876ca01549261174bd6034964282b0d726222f2a5465d92`,
CBOEPDF`6f3b1e751d0c0cf14b52d685095234a717d5f8e43ed9f96136ba1a4bae59b3b8`,
QCHTML`1bf53930d7eb49c3c9f504310dabe6c90014ec5be61482a665356768aec1463f`.
5GETattempts/retry0,32,404s tổng; lưu redirects/text/receipt, không redistribute.
KoURL redirect `.org/forthcoming` khác publisher2024final; claim scope theo bản
đã đọc, không tự gọi bytes là final journal copy. Fed cover2026/draft25Aug2025.

[OCC equity specs](https://www.theocc.com/clearance-and-settlement/clearing/equity-options-product-specifications)
thirdFriday; [CBOE2022calendar](https://cdn.cboe.com/resources/options/Cboe2022OPTIONSCalendar.pdf)
đã render/view:21Jan expiry/17Jan holiday;14Apr expiry/15Apr holiday, phân biệt
red expiry và orange prior AM-index lasttrade. Calendar retrospective evidence
không xác minh mọi revision đã biết trước từng event hoặc targetCFD hours.

Implementation/tests freeze cùng protocol trước source. Source/economic
artifacts mới có config/hash/manifest/status/log/timing; reviewer không gọi
producer để tự xác nhận output. Giữ cả negatives và method limits; goalactive.

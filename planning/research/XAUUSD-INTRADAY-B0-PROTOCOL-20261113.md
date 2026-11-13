# XAUUSD Intraday B0/A0 — protocol thực thi được owner duyệt

PR72 merge `7ee9ace`; EURUSD B1 **CANCELLED_BY_OWNER**, không tiêu lượt và không
chuyển quota sang Gold. Chỉ A0/B0 này, không A1/B1 hoặc tối ưu parameters.
Parent [card](XAUUSD-INTRADAY-B0-PROPOSAL-20261113.md); yêu cầu mới nhất cho phép
chạy cả Development2022–23 và historical validation2024, kể cả dev yếu.
2025–2026 CLOSED tuyệt đối. Nov–Dec2021 chỉ seed indicators, không trades.

## Freeze trước outcomes mới

- Dùng các bar Bid đã admit, UTC; H1SMA20/slope3completedH1, WilderATR14M15
  continuous từ01/11/2021. M15SMA20 trước bar hiện tại; cần đủ15/60phút/bar,
  không padding/volume filter. Previous M15 phải liền trước theo clock.
- Khóa zone=SMA20±0,20ATR trước bar. BUY previousclose>upper, bar hiện tại
  chạm band vàclose>upper; SELL đối xứng. Không yêu cầu màu nến.
- Bar mở từ09UTC, barclose/entry phải<16UTC; earliestclose09:15, last15:45.
  Mọi rawsignal được đếm kể cả account đang giữ lệnh/đã2fills, không biến các
  counters khác đơn vị thành phễu ngày trừ số nến.
- NaturalSL=setupLow−0,10ATR BUY, High+0,10ATR SELL, round outward. Sourcegrid
  0,001USD/oz, contract100oz/lot, lotmin/step0,01/max50 và leverage10 là
  **declared research geometry**, chưa xác minh target account hiện hành.
- Entry first observed Bid/Ask tick>=barclose, wait≤60s và<16UTC. Chuẩn bị
  đúng các tick-hours của rawsignals và2giờ tiếp theo; không fullhistory replay
  hoặc source sau2024. Reuse native Dukascopy provider/cache/decoder, giữ
  same-ms order/raw hash. Kiểm signalbars chứa observedticks trước financialrun;
  mismatch material→source defect, không âm thầm coi sources là interchangeable.
- Một position, max2fills/ngàyUTC, sauexit chờ barclose mới. Costadmission ở
  các rawsignals bị accountblock vẫn chỉ diagnostic, không order. Thứ tự counters:
  quote/geometry→stresscostcap→dailycap→position/waitbar→lot/margin→fill.

## Costs, size và exits

- Mỗi sổ50k reset theo năm; indicators không reset. FixedR0=150USD/lệnh.
  Cùng stressreservedquantity cho reference/stress, không compound/sizing sweep.
- Commission **mỗi leg**=0,000007×100×lots×executionquoteprice, centroundHALF_UP.
  Reference slip0; stress0,20USD/oz/side=20USD/lot/side. Commission theo notional
  counterfactual đã duyệt, không giả đó là phí lịch sử/account đã capture.
- Native sizing helper với per-lotcommission bound tại max(entry,SL,TP),1grid
  reserve và0,02USD/trade centroundreserve; stressrisk≤150. Margin theo mincash
  hai scenario, declared leverage10. Không kéo SL; Fplan = entryspread×100×lots
  +commissionreserve+stressslip+roundreserve, Fplan/R0≤12%.
- SL fill observedliquidationside firstcrossing (gồm gap); TP limit2Rprice,
  không priceimprovement. Từng tick mở position được markequity với entryfees;
  exitfees đúng exitquote. Net bridge dùng cents và oracle Decimal riêng.
- Exit priority same tick: SL/TP trước timedexit. Deadline=min(entry+120min,
 18UTC, datedsession/rollover−15min, restrictednews−5min nếu inputs admit).
  Tie120min/18UTC ghi TIME_STOP_2H. Vì entry<16UTC,18UTC thường không binding;
  vẫn xuất SESSION_CLOSE_1800 với0 nếu không có event loại này.

## Calendar và quality còn thiếu

Owner cho phép ghi rõ spread/Ask/calendar assumptions. Ưu tiên observedAsk/tick,
không lấy Bid+1USD hoặc spread0 khi chưa đăng ký scenario riêng. Full known-at
news/datesession lịch sử chưa có: **strict funded B0 BLOCKED_BY_CALENDAR**.
Lượt này đo conditional declared-regular-session economics; news không được
gán checked/0events. Tất cả trades giữ news_checked=false/target_calendar_verified=false.
Không dùng observedlastbar của ngày để chọn giờ thoát nhìn trước.

Swap0 chỉ khi conditional model xác nhận flat trước declaredrollover; không
quote deadline/heldgap hoặc SLTPunknown giữ qualityflags, không chứng nhận
fullpath. Sourcehour unavailable không tự là không có giá. Nếu không xác nhận
được exit: dừng/censor account từ đó, giữ missingpath và partialsum riêng,
không reset qua ngày hoặc forceclose đẹp. Max2×0,30%=0,60% là nominalplannedrisk,
không hardbound DailyLoss khi gaps/fills/costs vượt reserve.

## Output và review

1. Funnel theo năm: weekday/sourcevaliddays, uniqueH1hours/M15directionalbars,
   rawsignals,costrejects,medianSLrejected/accepted USD/oz,dailycapblocks,
   otherblocks,actualfills. Giữ units/counts/reasons và zero-months.
2. Exit reason TP_2R/SL/TIME_STOP_2H/SESSION_CLOSE_1800 (+news nếu có), count,
   winrate net>0/mean/totalNetR mỗi cost và năm/pooled. Exit table không chứng
   minh “timeexit cứu/cắt winner” nếu chưa có approvedcounterfactual; không
   đọc postexitprices để chạy holdingdiagnostic mới.
3. Side BUY/SELL: counts,grossafterspread,commission,slip,netUSD/netR.
4. Envelope: cadence,mean/annualNetR,observedtickequitypeakDD/R0,dailyLoss
   Europe/Prague,staticloss,coverage/gaps,censoring. Không CashDD→floatingproof.

Pin config/protocol/native/source/runtime/raw cache/producer hashes trước
financialrun; immutable attempts, one writer, logs/status/deadline/CANCEL,
partial failures giữ nguyên. Fixtures causalMA/ATR/bias/SL/TP/gap/fees/rounding/
costcap/dailycap/timeout/clock/holdout trước fullrun; second arithmetic/path
audit sau chạy. B0 technicalpass không edge/prop qualification hoặc liveauthority.

## Amendment dữ liệu trước mọi financial outcome

Tick-view-v1 đã chặn dispatch: 135.278/135.281 phút BidOHLC khớp CSV/QDM,
3 phút năm2024 lệch (15/02 13:30,13/12 14:33,23/12 15:14 UTC),237ticks ngoài
rangeM1cũ. Native `processData` xác nhận toàn bộ58.483quotes của3hours liên
quan; đây là archived-candle/source revision, chưa xác minh độc lập provider.
Giữ nguyên originalCSV/cache, failedview và snapshotv1; correctionmanifest
`source-corrections-v1.json` bind original/correctedOHLC/rawhash. Loader kiểm
original exact và corrected bằng decoder đã parity trước khi dựng lại H1/M15.
`signal-source-v3` dừng do adapter dict/listshape, giữfailure; v4 là bản sửa.
Không PnL trước các sửa này, không chọn source dựa trên kết quả tài chính.
Rules/split/risk/cost không đổi; native ticks vẫn là fill/path source. Đây là
data-version change, không A1. Freeze snapshot/config mới trước financialrun.
`tick-view-v2` phải khớp tất cả selectedminuteOHLC sau correction mới được seal.
Audit chỉ chứng minh selectedhours, không toàn bộ khoM1 hay feedđộc lập.

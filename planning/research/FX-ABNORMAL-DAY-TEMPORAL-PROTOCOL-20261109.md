# R089: kiểm độ bền 2010–2024, không đổi chiến lược

Theo [kết quả hai năm](FX-ABNORMAL-DAY-RESULTS-20261109.md) đã reviewed:
2019 stress+493USD/11cơ hội,2022+962USD/16; cùng100.000EURnotional nghiên cứu,
không account return. Giữ nguyên component `eurusd-prior-abnormal-20h-day-reversal-utc-v2`:
20weekday calibration, mean/samplevariance, strict2sigma/sign, dayproxy00–20UTC,
Tue–Fri reversal01–08UTC, source lag≤60s, commission5USD và stress extra4USD/unit.
Không SL/sizing/clock/side/fees grid, không thay minimum theo kết quả mới.

## Phạm vi khóa trước outcome mới

- Evaluation2010–2024:3.913weekdayrows;2019/2022 là discovery đã biết, giữ
  nguyên521rows/27cơ hội và12books.13năm còn lại là temporalextension, không
  cleanOOS: dữ liệu đã consumed trong campaign và phần lớn thuộc mẫu paper.
- Fullcalendar cần14.126targetslots2009–2024:2009 cần42warmupslots nhưng không
  có registeredraw, giữ **explicit unavailable**, không fetch hoặc tạo giá.
  Jan2010 có thể unavailablehistory/known-at skip; không bỏ các ngày này.
-2010–2022 dùng exactsealedraw/cache metadata của `pre-ecb-long-price-v1`;
 2023/2024 dùng exactraw/config/result/review-v2 của `pre-ecb-recent-price-v1`.
  Hai năm sau **raw-only mode đã đăng ký**, không ép nhận H1 cache legacy.
-Reuse source1.954slots của discoveryfullsource đã sealed; chỉ source roles
  mới cần decode/review.2019/2022 có thêm2tailroles/năm cho calibration của
  năm sau, không financial rerun của baseline. RawSHA vẫn kiểm khi reuse.
  Nguồn hoàn toàn có sẵn; không network, own2025+, broker hoặc account mới.

| Source year | Targetslots |
|---|---:|
|2009,unavailablewarmup|42|
|2010|940|
|2011|936|
|2012|938|
|2013|940|
|2014|940|
|2015|940|
|2016|940|
|2017|936|
|2018|938|
|2019|940|
|2020|944|
|2021|940|
|2022|936|
|2023|936|
|2024|940|

## Source và resume

Giữ registeredsourceview hiện có: currentnative decoder từ raw, Fraction
decoder/selector khác, predecessor và referencecacheoriginalbinding khi có.
2023/24 dùng hai rawreaders, không tạo cache mới. Unknown giữ actualreason;
native/cache/oracle phải đồng ý availability và mọi field của resolvedslot.
Sourceadmitted không đồng nghĩa mọi slot đều available hoặc executable.

Sourcejob có checkpoint niêm phong riêng từngyear, source/config/target/code/
runtimepins, OS lock một writer, progress/PID/events/timers/CANCEL/deadline.
Resume chỉ dùng year đãsealđúnghash/binding; không đanglive thì mởwriterkhác,
không đổi pin cũ để reuse hoặc restart vì observationtimeout. Nếu kiểm
controlledcheckpoint/resume, phải báo đúng scope, không tự claim crash-resume
trong rawyear hoặc account-simulation equivalence.

Một sourceattempt tối đa1.200s activewall, khôngauto retry; completeyears giữ
cho resume. Sourcechecker giữ14.126census, discovery1954bridge và mutations
price/time/sequence/missingtarget/authority. Full financialphase chỉ sau source
admission và preflight. Writer/sourcecode frozen trước đọc outcomes mới.

## Frozen priority cho risk review

Chỉ dùng **13extensionyears**, không lấy hai discoveryyears cứu gate. Mỗi
cost/rule có sổ riêng;90books/23.478financialcases không là23.478trades.

1. Mọi selectedentry/exit được resolve; còn unknown thì strictnetN/A,
   khôngdropyear hoặc cộngknownsubset thành completePnL.
2. Mỗi extensionyear có≥80%eligibleTue–Fri với featureavailable (`normal+shock`),
   denominator giữ cả unavailablehistory/zerovariance. Đây là qualitytriage,
   không statisticalpower; không loại ngày thiếu để tính lại tỷ lệ.
3. Có≥100resolvedselectedopportunities trong13extensionyears.
4. Primary extensionstressnet>0 và≥9/13extensionyears cóstressnet>0.
5. Cả5extensionblocks đều stresspositive:2010–12,2013–15,2016–18,2020–21,
   2023–24. Báo combined/discovery riêng, không nhập vào những blocks này.

Đây là tiêu chí ưu tiên công việc đã đăng ký, không chứng minh edge hoặc
probabilitypass. Per-year≥8discoveryheuristic cũ chỉ diagnostics, không thay
temporal gate. Thiếucoverage/sample →inconclusive; đủ nguồn/mẫu nhưng không
economicretention →gác exactversion. Không retune sau kết quả để tự đạt.

## Kiểm uncertainty, mô tả trước khi nhìn kết quả

Trên13strictannualnets: bootstrap annualblocks cóhoànlại10.000draws, seed8901;
95%percentile interval cho meanannualnetUSD/unit, nearest-rank, khôngROI/
passprobability hoặc selection-adjustedtest.13yearblocks ít và exchangeability
qua regimes chưa chứng minh; interval không phải bảo đảm tương lai. Thiếu
bất kỳ annualstrictnet →N/A, không bỏ năm đó. Tính thêm leave-one-year-out
sumrange, top5positive-trade share và winner/loser counts trên extension.
Các diagnostics **không** thêm gate mới hoặc tự cấp C1/C2; không dùng chúng
để chọn subgroup/giờ/stop sau outcome.

## Kiểm chứng và bước sau

- API mở rộng year scope phải giữ default2019/2022 và chặn2025+. Kiểm parity
  actualdiscoveryrows/summary với frozenbaseline vì code đổi scope; pipeline
  extension vẫn reuse originalfinancialbytes, không tính discovery thành trial mới.
- Review độc lập codepath/mean-variance identity/clock/known-at/financials/
  costs/census/gates/uncertainty; cùngagent khôngindependenthuman/feed.
  Giữ syntheticunknown/flat/zero/boundary, invalidscope và guardmutations.
- Nếu retained: đo pathrisk/SL mechanism/exante sizing rồi nativeaccount/
  prop/time-fit3/6/12m, targetfees, selection/OOS/prospective và ownerhandover.
  Chưađếnđó khôngmua/chạychallenge. Goalactive/C1C2chưađạt.

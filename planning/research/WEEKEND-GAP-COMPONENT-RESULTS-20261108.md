# R024: component không đạt ưu tiên; giữ kết quả và không viết bot từ mẫu này

**Phép thử đã hoàn tất, chưa có ứng viên challenge.** Fadegap12giờ sau phí
dương2019 nhưng âm2022, không đạt tiêu chí đã khóa. Không sửa factor3, giờ
vào/ra hoặc chọn chỉ năm đẹp để tạo survivor. Đây là negative/inconclusive
evidence cho đúng probe này, không bác bỏ mọi weekendgapstrategy.

[Protocol trước outcome](WEEKEND-GAP-COMPONENT-PROBE-20261108.md), commit
`163add6`; numericalimplementation/tests`e1ae85a`, telemetryfixsauđó`8277f92`.
Reuse[103weekends/206endpoints](WEEKEND-GAP-DATA-RESULTS-20261108.md)
EURUSD2019/2022 đã consumed, không download hoặc mở dữ liệu2025+.

## Kết quả dễ đọc

Đơn vị **pip giá sau spread/commission/slippage**, không% hoặc lãi/lỗ tài
khoản10k/50k. Component chưa có sizing/SL/risk/propengine, nên không được suy
thời gian pass, accountdrawdown hoặc xác suất challenge từ bảng này.

| Phép thử / năm | Sự kiện | Tổng pip phí chuẩn | Tổng pip phí cao | Bình quân pip, phí cao |
|---|---:|---:|---:|---:|
|Primaryfade,2019|9|+28,8|+25,2|+2,80|
|Primaryfade,2022|12|−61,0|−65,8|−5,48|
|Followgapcontrol,2019|9|−52,3|−55,9|−6,21|
|Followgapcontrol,2022|12|+9,6|+4,8|+0,40|
|Secondaryungatedfade,2019|49|−164,8|−184,4|−3,76|
|Secondaryungatedfade,2022|47|−133,3|−152,1|−3,24|

Primarysum hai năm:−32,2pip chuẩn/−40,6pip cao trên21events; không dùng tổng
để che2022âm. Followcontrol chỉ dương2022, không thay primary bằng control.
Ungatedfade là diagnostic đã đăng ký, không chiến lược mới để chọn hậu nghiệm.
Flatcashbaseline0, không có lệnh/phí và không phải strategy có thể passquỹ.

Primarywins/coststress:5/9 và5/12;3positiveevents lớn nhất đóng góp87,53% và
82,16% tổng positivepips. Event yếu nhất−31,8/−90,3pip; tốt nhất+35,6/+67,7pip.
Mẫu nhỏ, outcomes cùng thị trường và thresholds đã exposed qua research;
không gắn confidence/p-value/edgeproof hoặc gọi hai năm là cleanOOS.

## Sample không bị lọc theo lợi nhuận

| Năm | Allweekends | Qualitymissing/late trước entry | Đủ quote/nonzero direction | Costfiltered | Primaryeligible/resolved |
|---|---:|---:|---:|---:|---:|
|2019|52|3|49|40|9/9|
|2022|51|4|47|35|12/12|

Không drop7qualityfailures khỏi denominator103.2019:22/03Friday→24/03Sunday
có firstquote muộn hơn5phút;24/05→26/05firstquote muộn gần3giờ nên thiếu
entrywindow;20/09→22/09 không có quote đủ entrydeadline.2022:weekends bắt đầu
07/10,28/10,09/12,23/12 thiếu entrywindow;weekendcuối còn thiếuexitwindow.
Không autođợi lâu hơn60giây hoặc carrygiá, không suy thiếuquote=marketclosed.

Filter dùng gap/entryspread và declaredcosts biết lúc entry; exitquote không
tham gia eligibility. Các events đã primaryeligible đều có exit đúngdeadline
trong actualsample; code/fixture giữ eligible nhưng unresolved nếu futureexit
thiếu, không lặng lẽ xóa event đó hoặc tính thành0profit.

## C2 và luồng dữ liệu

`sealedraw/admission → exact4quoteevents → exantefilter → sharedcostprimitive
→ summaries → independentreview`. Chỉ sourceobservation không trở thành
brokerfill; không tạo engine/sổrisk thứhai hoặc sửa productruntime.

- Rawhash và66.133.073linecounts khớp seals; clock/order/grid kiểm theo existing
  packet và selectedBrokerReplayTick. Exactfirstat/after entry/exit, inclusive
  deadline60s, Friday/Sundayage5min, NY DST và sourceordinal giữ trong artifacts.
-7focusedtests trước actualoutcomes: BUY/SELL tính tay80USDgross→75USDnet/
  71USDstress cho1standardlot, thresholdinclusive, zero/missing, futureexit
  isolation, rawselection/hash/latequote, spring/fallDST và undefinedmeans.
  Standardlot chỉ unitconversion, không có nghĩa risk25USD mỗi event.
- PrivateFractionreviewer không import component/costhelper:384direction×cost
  arithmeticchecks khớp; counts/sum/mean/signs, gap/threshold/eligibility và
  eventclocks khớp. Pip/USD exact; bpsratio chỉ cho arithmeticrounding<1e−20,
  không tolerance cho giá/clock/cash hoặc nới model để pass.
- Rawreviewscan riêng kiểm412eventrecords trên nguồn, gồm quote bị từ chối
  vì đến muộn. Entry/exit phải là firstsourcequote tại/sau clock: so trực tiếp
  predecessor timestamp, không chỉ xem selectedquote nằm trong một phút.
  Sourcehash được kiểm lại; không dùng H1extrema làm tickordering.
-3actualinmemorytampercases bị chặn: đổieligibility, sửanetcash, sửaresolvedcount.
  Sameagent/separatecodepaths, không independentfeed/human/modelsign-off.
- Commission2,50USD/lot/side, stress0,00002slippage/side, observedentry/exitspread
  giữ nguyên. Funding0 chỉ cho declaredsingletradingday Sun17:10→Mon05:10NY,
  không đi qua next17NYrollover; chưa historicalFTMOcontract/holidayproof.

Chưa SL/equitypath/sizing/intrabarDD/targetbroker/OOS/forward nên C1 không đạt.
C2 được củng cố trong đúng scopequote/arithmetic/causality đã kiểm, không tự
chứng nhận toàn bộ hệ thống hoặc mọi strategy.

## Hậu kiểm kỹ thuật và thời gian

| Lát đo | Actual | Kết luận |
|---|---:|---|
|Focusedtests trước numeric /sau telemetryfix|7tests/0,199s →8tests/0,216s|Chỉ suite bị ảnh hưởng, không fullproduct|
|Numericcomponent gồm rawscan/hash/quote selection/report|39,861s|Không fulltickriskengine; CPU/peakRAM chưa đo riêng|
|Independentarithmetic +actualrawreview|34,760s|Không rerun component để review|

Phần lớn wall là đọc/hash raw; chỉ parse selectedquotes và kiểm rawtime/order,
không tính indicator hoặc risk trên mỗi tick. Không gọi tốc độ này là native
backtestspeedup và không thêm GPU/Rust/framework khi chưa có bottleneck đáng
đầu tư. Timings không bao gồm agentcoding/researchtime chưa đo hoặc tokenquota.

**Đã tái hiện và sửa một lỗi telemetry:** khi CANCEL/deadline đã tới, helper
`progress('failed')` cũng kiểm lại điều kiện dừng và ném lỗi lần nữa, làm mất
terminalprogress và che originalexception. IsolatedCLIregression trướcfix
thực sự ERROR vớiRuntimeErrorcancelled thayValueErrorfixture; saufix8testsđạt,
failure.json giữ originaltype và progress.json hiệnfailed. Không bỏ cancellation
hoặc deadline ở workphases; chỉ cho terminalfailure được ghi. Không ảnh hưởng
financialoutcomes của completedjob, nên không rerun numerical.

Originalsource/testse1ae đã copy vào private`source-snapshot/` **trước sửa**,
hash khớp numericalmanifest.10toplevelnumerical/parserfunctions và toànmain
trừnestedprogress có ASTexact trước/saufix; receipt`telemetry-fix-review.json`
giữ before/afterSHA và scope. Originalnumericalreview đã xong trước codechange;
manifest không được sửa pin để gán currentcode mới cho oldrun. Futurehistorical
inspection phải dùng sourceversion/snapshot đó; currentfiledrift là expected.

Không có numericalproducerbug material mới trong actualscope; không nới test
hoặc sửa outcomes. Reuse quoteartifacts theo bindings nếu reviewer cần đọc lại;
không chạy lặp cùng sample để kiếm thêm confidence hoặc làm đẹp benchmark.

## Quyết định và bước tiếp

R024 từ endpointmetadatareviewed sang **componentnotretained, nostrategy**.
Giữ exactcode/protocol/raw/source/negatives, không tăng sốpolicyversions từ
component. Không mở gridtime/gapfilter/risk để cứu; chỉ revisithypothesis khi
có câu hỏi mới có cơ sở và protocol/trialhistory riêng trước outcomes.

Chọn R019break→retest trong catalogue để specification/data-readiness tiếp:
reuse prior-daylevel/ATR/clock và financialcore củaR015, nhưng retest phải ở
bar sau breakout và causalstate phải checkpoint/prefixrestore. Đây là local
hypothesis, chưa có edge. Trước numerical phải kiểm source/cachecontinuity
của currentD:code với oldH1cache; không sửaoldpins để forcecurrentreader hoặc
rebuildmọidataset theo phản xạ. Freezeexactrecipe/risk/cost/decision trước PnL.
R026 vẫn thiếu relative-equity/currency/corporate-action/fixingcalendar,
không thay nó bằng calendarbuy/sell hoặc tải hàng loạt để épwinner.

Private`execution-v1/weekend-gap-component-v1`:manifest/progress/events,
quotes2019/2022,fullresult,`review.py`/reviewprogress/result,sourcepins,
originalsource-snapshot vàtelemetryfixreceipts.
Fixtures ở`weekend-gap-component-fixtures-v1/result.json`. Numericalsession78026
và reviewsession5971 đã terminalexit0, khôngjobnền. No broker/model/marketdata
networkcalls hoặc2025+; C1/C2Goal vẫn active, không mở quyềnchallenge/execution.

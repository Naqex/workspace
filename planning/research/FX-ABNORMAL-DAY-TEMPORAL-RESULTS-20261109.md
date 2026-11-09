# R089 không qua kiểm độ bền; gác exact reversal recipe

Thực hiện [temporal protocol](FX-ABNORMAL-DAY-TEMPORAL-PROTOCOL-20261109.md),
freeze `7822726` trước nguồn/outcomes mới. Kế thừa [discovery](FX-ABNORMAL-DAY-RESULTS-20261109.md),
không sửa hai năm dương cũ hoặc lấy chúng cứu gate. **Đủ nguồn/mẫu cho phép
kiểm đã đăng ký, nhưng không retained về kinh tế:**8/13extensionyears dương,
hai trong nămblocks âm. Chưa có ứng viên challenge hoặc bằng chứng edge bền.

## Kết quả theo năm

USD trên100.000EURnotional nghiên cứu, không lợi nhuận account10k/risk25USD.
Giữ00–20UTCdayproxy/20priorweekdays/k2/Tue–Fri01–08reversal và fees. Không
SL/account/margin/prop simulation hoặc independent/OOS chứng nhận.

| Năm | Cơ hội | Net chuẩn USD | Net cao USD | Vai trò |
|---|---:|---:|---:|---|
|2010|16|−828|−892|Extension|
|2011|15|−3.978|−4.038|Extension|
|2012|9|+577|+541|Extension|
|2013|13|−456|−508|Extension|
|2014|10|+317|+277|Extension|
|2015|13|+2.156|+2.104|Extension|
|2016|13|+108|+56|Extension|
|2017|11|+436|+392|Extension|
|2018|10|−713|−753|Extension|
|2019|11|+537|+493|Discovery, reuse|
|2020|15|+1.841|+1.781|Extension|
|2021|8|−211|−243|Extension|
|2022|16|+1.026|+962|Discovery, reuse|
|2023|19|+920|+844|Extension|
|2024|12|+1.036|+988|Extension|

13extensionyears có164opportunities, reference+1.205USD/stress+549USD;
toàn15years gồm191opportunities/stress+2.004USD. Không cộng hai costs thành
portfolio hoặc23.478financialcases thành từng ấy trades. Baseline521rows/
3.126cases được reuse, chỉ3.392weekdayrows/20.352cases mới. 90books giữ riêng.

## Vì sao không giữ để viết risk wrapper?

| Frozen criterion | Kết quả |
|---|---|
|Selected endpoints đầy đủ|164/164extension, không selectedunknown|
|Feature availability≥80%eligible mỗi extensionyear|Đạt tất cả; không bỏ unavailable khỏi denominator|
|≥100resolvedextensionopportunities|Đạt164|
|Extension stressnet>0|Đạt+549USD/unit|
|≥9/13extensionyears stresspositive|**Không đạt:8/13**|
|Cả5extensionblocks stresspositive|**Không đạt:2010–12 và2016–18 âm**|

Đây không chỉ vì hụt một năm ở heuristic9/13. Kết quả không đồng đều theo
thời kỳ, tổng mỏng và mức bất định lớn. Không tự bắt đầu mẫu ở2020, bỏ2011,
đổiside/clock/fees/stop hoặc gọi những năm gần đây là cleanOOS. Gate này là
ưu tiên nghiên cứu, không chứng minh mọi dailyshockreversal đều vô dụng.

## Giá, phí và thang biến động là ba chuyện khác nhau

| Extensionblock | Midpricebenchmark USD | Tổng costdebits USD | Stressnet USD |
|---|---:|---:|---:|
|2010–12|−3.642,50|746,50|−4.389|
|2013–15|+2.318,50|445,50|+1.873|
|2016–18|+90,50|395,50|−305|
|2020–21|+1.827|289|+1.538|
|2023–24|+2.197|365|+1.832|
|**13extensionyears**|**+2.790,50**|**2.241,50**|**+549**|

Costpool gồm spread765,50/commission820/slip656/funding0USD, không double
countspread trongBidAsk.2010–12 giá đã bất lợi trước phí;2016–18 giá hơi dương
nhưng phí ăn hết. Vì thế không coi mọi yếu điểm là phí hoặc hạspread để cứu.
Fees vẫn declaredscenario, chưa current/historicalcontract của quỹ đích.

[Vol-scale diagnostic](FX-ABNORMAL-DAY-VOL-SCALE-DIAGNOSTIC-20261109.md) được
đăng ký **sau** temporaloutcomes để kiểm hữu hạn một nghi vấn: fixednotional
có che một kết quả tốt khi chuẩn hóa bằng biến động biết trước không? Giữ
mọi trade/fees, không account sizing. Cảhai block âm vẫn âm; chỉ7/13năm có
điểm chuẩn hóa dương. Không có basis dùng riêng volatilityscaling để chuyển
parent sang riskwrapper. Frozenverdict giữnot_retained; đây không policy mới.

## Mức bất định và concentration

Theo diagnostics đã đăng ký trên13extensionyears, không lấy discovery vào:

- Meanannualstressnet≈42,23USD/unit. Annual-blockbootstrap10.000draws/seed8901
  cho95%percentileinterval của mean≈**−810,92 đến+769,77USD/unit**.13blocks ít,
  exchangeability qua regimes chưa chứng minh, không selection-adjustedtest
  hoặc xác suất pass quỹ; interval không được hiểu là bảo đảm tương lai.
- Leave-one-year-out tổng12năm còn lại từ−1.555 đến+4.587USD/unit. Kết luận
  tổng lời nhạy với năm được xem, không có lý do loại năm gây bất lợi.
-83netwins/81netlosses,0flat; positivepool20.310USD, negativepool19.761USD,
  top5positive trades chiếm≈28,26%positivepool. Winrate≈50,61% không tự chứng
  minh lời đủ lớn/rủi ro phù hợp, không chọn lại những trades này làm filter.

## Nguồn, checkpoint và correctness

-14.126targets/16partitions2009–2024;14.034validwithin60s.2009không có raw
  nên42warmupslots explicitunavailable;50late/missing còn lại giữsourceproof,
  không ffill hoặc đổi thànhmarketPnL0. Featuremissing là known-at skip.
  Khác financialselectedunknown: actualselected191/191 đều cóendpoints.
-Reuse1.954discoverysource slots; còn source roles mới mới decode/review.
 2019/2022 thêm2tailroles/năm cho calibration của năm sau, không replayfinancial
  baseline. Warmup không PnL; chưa đọc own2025+ hoặc lấy data từ provider mới.
-Native quote decoder và Fraction/rawselector khác, first-after/predecessor/
  price/grid/sequence/availability khớp; registeredreference cache khi có.
 2023/24 raw-only mode, không ép dùng legacycache. Mỗi reader đi qua373.428.864
  new-prefixrows; fullrawSHA giữ, không gọi từng ấy rows là financialsamples
  hoặc fullSL/path/brokerfill audit. Source4guardmutations bịreject.
-Controlledhandoff sau2010 đã kiểm: resume reuseexactyearseal/rows, không
  đọc/parse lại rawyear đó ngoài hashcheck.2009/2010checkpoint reused, source
  OS lock thực tế chặn writer thứhai khi PID4968 đanglive. **Không** claim
  in-yearcrash/accountresume hoặc uninterruptedsimulation equivalence.
-13focusedtests đạt khi mở year scope, trong đó4temporaltests. Đã sửa riêng
  samplefixture để selected/exposed/resolvedcounts nhất quán,4affectedtests
  đạt lại; production rules không đổi. Finance/statpreflightv1 giữ, v2 được
  snapshot/review trước numeric;0PnL ởv1, không rerun market vì testfixture.
-Actualdefaultparity521discoveryrows/summary khớp bản cũ sau codeyearscope
  đổi,0,390s/no rawreads. Extensionpipeline sau đó reuse originalfinancialrows
  và kiểm exactobjectbridge, không gọi oldyears là trial mới.
-Full23.478cases/90books reviewed bằng rational variance identity/clock/
  known-at/cost/rounding/financials khác codepath.9actualmutations net/commission/
  side/clock/calendar/authority/annualgate/temporalgate/sourceauthority bịreject.
  Bootstrap có integer-cent oracle trên drawtable cố định; constant/zero/
  unknown và falseCI fixtures. Cùngagent, không independenthuman/feed review.

## Thời gian và hậu kiểm

| Lát | Actual wall | Scope |
|---|---:|---|
|Source từmanifestđầu đếnclosure|701,006s≈11phút41s|Cócontrolledhandoff;0GET|
|Source hai process invocations|≈674,816s|Phần gọi worker, không cộng thêm vào dòng trên|
|Baselineparity|0,390s|Do APIyearscope đổi, không trial mới|
|Temporal/statpreflightv2|≈1,045s|Chạy trong lúc source đangđọc, không cộng vào end-to-end|
|Numeric13newyears|2,205s|Nằm trong economicphase bên dưới|
|Economicphase/fullreview/mutations/statistics|12,357s|23.478cases gồmbaseline reuse|
|Volnormalizeddiagnosis+exactboundsreview|0,385s|191scores,0rawreads/simulation mới|

SourceCPU hai invocations≈549,547s; chưa đo peakRAM hoặc toàn giờ authoring/
research. Không claim speedup so với2yearworkload trước. Phần tốn thời gian
là source validation, không tiền/signal loop. Giữ yearseals và14.126quote packet
để reuse; chưa có lý do GPU/Rust/indexservice hoặc chạy lại wholehistory.
Nếu consumer mới cần nhiều giờ khác, ưu tiên canonicalsource admission/cache
contract trước repeatedrawscan; chưa viết index mới khi chưa chốt nextrecipe.

## Artifact và resume

Privatebase `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`:

- `execution-v1/fx-abnormal-day-temporal-source-v1/`:OSlockfile,peryearseals/
  rows,manifest/sourcecalendar,raw/native/reference proofs,controlledcheckpoint,
  events/progress/result. All processes terminal; writerlock đã release.
- `execution-v1/fx-abnormal-day-temporal-preflight-v1/`:baselineparity và OSlock/
  checkpoint observation. `fx-abnormal-day-temporal-v1/` giữ firststatpreflight;
  `fx-abnormal-day-temporal-v2/` là activefullfinance/result/review/uncertainty/
  bootstrapdraws/decomposition/inputpins/source-snapshots. Không overwritev1.
- `execution-v1/fx-abnormal-day-vol-scale-v1/`:separatepost-outcome diagnosis,
  không sửa financialledger. Savedcontrollers/helpers tại privatebase giữ pins.

| Artifact | SHA256 |
|---|---|
|Temporal source result|`655a5dda9b226cdbbefe96f3a49f3f662560024cf0be4e2d4642b03a5fbc3141`|
|Economic result|`c3550451752bd463ac4afa8cdc906c7818b20700afb790ae2e66fa0e41869164`|
|Economic review|`54411482670c8c44666eae42fc07cb6dbc61f899f9d094c61ff3cfd129a465c9`|
|Temporal gate|`36fef3e6923c8cabbb8ae3b0e94785c1976e27991fd82986a37f328dfbc6c117`|
|Uncertainty|`9e71a29c1de186f5e4003be6efd714944f5d05959cf63068fd1a112c02cb73a3`|

R089 và negatives giữ nguyên, catalogue89/58accountversions; không newpolicy,
broker/runtime/globalenvironment/skill mutation. Goalactive/C1C2chưađạt.
Tiếp admission **same-day causal abnormal-return continuation** từ primarypaper
đã đọc: firstthreshold crossing phải biết lúc xảy ra, không nhận diện ngày bằng
Close tương lai rồi giả đã vào trước. Khác nextdayreversal và related với
R007/R089, không independentedge đã chứng minh. Method/sourcefixture trước
recipe/outcome, reuse dataset đãadmitted, khôngn/k/side/feegrid cứuR089.

**Bước tiếp đã thực hiện:** [R090results](FX-INTRADAY-SHOCK-RESULTS-20261109.md)
không retained trên2019/2022. Không resume lại gợi ý same-day ở checkpoint này;
giữ exact R089 negative và chuyển theo entrypoint hiện hành của campaign.

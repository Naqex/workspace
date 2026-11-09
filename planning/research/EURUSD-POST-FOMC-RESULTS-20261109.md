# R088: sau phí còn dương, chưa chứng minh phần lợi thế riêng của FOMC

[Protocol](EURUSD-POST-FOMC-PROTOCOL-20261109.md) freeze `4cb1b36` trước
quotes/outcomes mới. Đã hoàn tất **32 windows /24 books /192 financialcases**,
đối soát nguồn và số học. **Không đạt frozen event-priority gate** vì2022
không tốt hơn tuần đối chứng. Chưa SL/accountpolicy hoặc challengecandidate.

## Kết quả

Đơn vị **USD trên100.000EUR notional nghiên cứu**, không return/account10k
hoặc permissiontrade1lot. Hai năm exposed/development;16events không192
independenttrades. Không nhầm USD ở đây với JPY/unit của R087.

| Cohort |Reference net|Stress net|Stress minus matchedweek|
|---|---:|---:|---:|
|2019,8postFOMC windows|+1.045|+1.013|+295|
|2022,8postFOMC windows|+577|+545|−1.896|
|2019,8matchedweek windows|+750|+718|N/A|
|2022,8matchedweek windows|+2.473|+2.441|N/A|

Full registered endpoints32/32 đủ; mỗiwindow719/719pairedlistedM1minutes
trongsourcepath. Endpointpricecomponent vẫn không simultaneous executable
ticks hoặc equity/SLpathproof. Khôngunknown bịdrop/ffill, không chọnside/giờ.

## Tiền đi đâu trên cohort chính?

| KhoảnUSD/notional nghiên cứu |2019|2022|
|---|---:|---:|
|Midpointpricebenchmark PnL|+1.108,50|+649,50|
|Spreadembedded|−23,50|−32,50|
|Commission5USD×8windows|−40|−40|
|Extraslippagestress4USD×8|−32|−32|
|Fundingdeclared|0|0|
|**Netstress**|**+1.013**|**+545**|

Funding0 được khóa trước do02:01–13:59NY không crossingdeclared17NYrollover;
không giảswapfree, không copy0 sang overnightstrategy. Entry/exitderived
từactual14NYcalendar, không dùng14:15thesis cho2019/22. Chi phí chưa exact
targetbrokerfees/historicalspec; sourcequotesDukascopy khác FTMOexecution.
CoregrossBidAsk đã chứa spread; benchmarkmid chỉ kế toán, khôngfillprice.

**Đúc kết:** R088 khác R086/R087 ở chỗ phần dương chưa bị costs xóa hết.
Nhưng cảevent vàmatchedweek cùngdương, riêng2022matchedweek lớn hơn nhiều;
không đủ chứng minh FOMCselection tạo thêm edge. Positivecashsum không
chứng minh stableexpectedreturn hoặc phù hợpchallenge/lowrisk/timefit.

## Kiểm chứng trước và sau PnL

-4focusedtests mới đạt: NY/UTC/DST/calendarpublication/no-rollover; SELL/BUY
  costs/null/units; missing/crossed/offgrid/interiorgap scope; futureexit
  khôngđổischedule và fullcensus/gate. Reuse `fixing_clock_probe.price_return`
  cùng nativecostcore, không viết thêm frameworkkhớplệnh.
-Pilot4day-sidefiles,2dates đủ719minutes/window;28.740rawfields và4price/
  timestamp/missing/crossedmutations đãreview trướcfullsource. Khôngpilot→
  fullcohort ngầm. [Methodadmission](FX-POST-FOMC-METHOD-ADMISSION-20261109.md)
  giữ thesis/discussionversiondifferent và cachedFTMOEURUSDonly gap.
-Fullsource64day-sides:60GETmới+4pilot reuse,0transienterrors. **459.780OHLCV
  fields** đối soát native/explicitDecimal/Fractionrawdelta; padding vàvolume0
  khôngbịnhầm. Raw/grid/day/side/endpointknown-at/pins/snapshots giữ trướcuse.
-Sourcecalendar16events từ acceptedR062JSON, oracle dựng nextday02:01/13:59
  riêng; originalpublication trướcentry. Khôngsurprisecontents/futurelabels.
-Preflight192syntheticcostcases+6mutations; actual192cases+6mutations net/
  commission/clock/unknown/authority/gate đều bịreject. Không case bịnới đểpass.
  Sameagent/phươngpháp sốhọc khác, khôngindependentfeed/model/human.

## Thời gian và artifact

| Phase |Wall|Phạm vi|
|---|---:|---|
|Pilotfetch/review|0,973+0,612≈1,585s|2dates/sourceonly|
|Fullfetch60new+4reuse|12,401s|Không lấy lại pilot/rawUS history|
|Fullsource review+prepared+preflight|6,095s|459.780fields/192syntheticcases|
|Economics+actualFractionreview/mutations|0,166s|192actualcases; riêngproducer0,117s|
|**Successfulfullworkerphases**|**18,662s**|Không gồm research/code/visualPDF/methodadmission/pilot|

Không benchmarkA/B soR087 hoặc toànpipeline. Không mớiCPU/GPU/Rust tối ưu
có evidence đáng làm; nguồn full nhỏ nên reuse giúp tránh batchđắt. Không
jobnền, không CLIresumeclaim khi chưa testinterruptionequivalence.

Privatebase `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`:
`execution-v1/eurusd-postfomc-source-pilot-v1/`, `eurusd-postfomc-calendar-v1/`,
`eurusd-postfomc-source-v1/`, `eurusd-postfomc-component-v1/`. Giữsource/raw/
native/seals/manifest/snapshots/prepared/rows/summary/result/review/progress.
Savedcontroller`run-review-eurusd-postfomc-v1.py`; producer/reviewer math khác
trong cùng savedfile, không gọi thành independentprocessreview.

- SourceReviewSHA `f2e956a0e9daef41de3e97157db56c74fed8e4c8d37d1698d9ec5d781dcc8872`.
- ResultSHA `d8e149f34147912c42ef90b7b37578df9dc9aface186ee182d2759d5c9cbdfc0`.
- ReviewSHA `77030325ac27fff9c6c895ee0e88436a0499616b5aeab927b86d55ab227ab90b`.

## Quyết định và bước tiếp

Khôngpromote **FOMCmask** theo frozenrule. Đồng thời không gắn nhãn “mọi
SELL02–14NY vôlợi” vì cảevent/control còn dương. Liên quan R021/sessionUSD
flow đã có, khôngedge độc lập hoặc mộtwinner được khám pháblind.

Bước kế hữu hạn là đối chiếu risk-wrapper attribution/time-fit của family
đã có với bằng chứng dương này: signal có yếu sau costs, hay SL/position
weights làm mất phần dương? Reuse [preECBresults](PRE-ECB-RECENT-PRICE-RESULTS-20261108.md)
và wrapperresults hiện có; **không** gộp PnL hai clockkhác, dùng FOMCcontrols
làm strategy mới, hoặc điều chỉnhstop/lot từoutcomes. Chỉ khi có một giả
thuyết risk/implementation có cơ sở mới registertrial riêng. Không FOMC
jump/side/date/feegrid đểcứu; không costđãthấp nên tănglot cho nhanh.

Đối chiếu đã thực hiện sau run: [wrapper attribution](PRE-ECB-WRAPPER-ATTRIBUTION-RESULTS-20261108.md)
cho thấy trên commonmask2019/2022, weights giúp nhưng parentexit/SL làm giảm
kết quả. [Path risk](PRE-ECB-PATH-RISK-RESULTS-20261108.md) lại cho thấy giữ
nguyên lot mà bỏ SL có lỗ giữa đường tới5,48R trong scope đã đo; không phải
giải pháp đủ an toàn. [R056](PRE-ECB-SESSION-RISK-RESULTS-20261108.md) đã thử
stop theo volatility cả phiên với risk25USD: net13năm dương nhưng2/4stressblocks
âm. Các clock02NY→14Berlin khác02:01→13:59NY ở đây; không gộp hoặc chuyển
PnL/stop giữa hai bài. Không có lý do mở thêm stop/lotgrid từ các bảng này.
R088 không bị loại vì phí; phần event-selection chưa đạt và risk/time-fit vẫn
chưa chứng minh. [Cost diagnosis](COST-HEADROOM-DIAGNOSTIC-20261109.md#cách-dùng-kết-quả-để-chọn-đúng-việc-cần-tối-ưu)
giữ thứ tự hành động; chỉ mở lại exact recipe khi có bằng chứng mới phù hợp.

Catalogue88records/58accountpolicyversions, chưachallenge. C1/C2 giữ nguyên;
không own2025+, broker, provider/account trả phí mới, runtime hoặc muaEA/quỹ.

# R089 giữ để kiểm độ bền, chưa ứng viên challenge

Thực hiện [protocol và amendments](FX-ABNORMAL-DAY-PROTOCOL-20261109.md),
[fullsource registration](FX-ABNORMAL-DAY-FULL-SOURCE-PROTOCOL-20261109.md)
freeze `c2696f9` trước fullsource/realfeatures/PnL. Component
`eurusd-prior-abnormal-20h-day-reversal-utc-v2` **qua frozen priority gate**
trong hai năm đã thử. Đủ lý do kiểm thêm độ bền, chưa chứng minh edge hoặc
đủ điều kiện mua/chạy challenge FTMO/The5ers.

## Quy tắc và kết quả dễ đọc

Đo EURUSD00→20UTC của ngày trước; so với20weekdays trước ngày đó. Nếu biến
động vượt mean±2sample-std và cùng dấu actualreturn, ngày sau xét giao dịch
ngược hướng01→08UTC, chỉ Tue–Fri. Dùng dữ liệu biết trước quyết định; không
chọn ngày theo giá thoát hoặc chỉ báo sau trade. [Method](FX-ABNORMAL-DAY-METHOD-ADMISSION-20261109.md)
giữ nguồn và khác biệt với paper; v123hproxy không khả dụng đã được thay trước
outcome, không copy giờ server không rõ của paper thành UTC.

Đơn vị tiền **USD trên100.000EURnotional nghiên cứu**, không USD/account10k,
không sizingrisk25USD và chưa SL/account path. Mỗi cost là phương án thay thế,
không cộng chuẩn+cao thành một portfolio hoặc coi3.126cases là3.126trades.

| Năm | Cơ hội được chọn | BUY/SELL | Net phí chuẩn | Net phí cao | Selected unresolved |
|---|---:|---:|---:|---:|---:|
|2019|11|6/5|+537|+493|0|
|2022|16|7/9|+1.026|+962|0|

Oppositecontrol cùngmask:2019−702/−746USD,2022−1.310/−1.374USD ởchuẩn/cao;
null0. Không chọn primary từ oppositeoutcomes. Mỗi năm≥8selected và strict
stressnet>0, tất cả selectedendpoints resolved nên frozenpriority đạt. Đó là
heuristic công việc, không statisticalpower hoặc xác suất pass quỹ.

## Phí ăn bao nhiêu trên đúng cùng path?

| Khoản USD/notional nghiên cứu, primary |2019|2022|
|---|---:|---:|
|Midpoint price benchmark|+619,50|+1.168|
|Spread embedded|−27,50|−62|
|Commission|−55|−80|
|Extra slippage stress|−44|−64|
|Funding trong window|0|0|
|**Net stress**|**+493**|**+962**|

Bid/Ask gross đã chứa spread; bảng chuyển về midpoint benchmark rồi tách,
không trừ lần hai. Funding0 chỉ vì01–08UTC không qua declared17NYrollover,
không swapfreepolicy. Commission5USD/roundtrip/unit; stress0,4pip extra slip
khứ hồi; còn targetaccountfees/specs/fills chưa verified. Tín hiệu giữ phần
dương sau declaredcosts trong hai cohort, chưa là expectededge bền vững.

## Census, missing và kiểm đúng phạm vi

- Toàn521weekdayrows:2019 có261,2022 có260. CalendarMonday skips52/năm;
  eligibleTue–Fri209/208. Feature2019:21unavailablehistory/177normal/11shock;
  2022:0unavailablehistory/192normal/16shock. Missingcalibration biết trước
  entry nên0exposure, không bỏ row. Đây là policy với sourceavailability này,
  không khẳng định lịch sử broker đầy đủ hoặc ngày nguồn thiếu không có cơ hội.
-4sourcepartitions2018/2019/2021/2022 đúng warmup+evaluation,1.954targets;
 1.947validwithin60s,7late/missing giữ explicit. Nguồn đã có,0GET. Warmup
  khôngPnL. Registeredcache reference giữ originalruntime; currentnative
  selectedquote decoder và Fractionrawprefixselector khác đồng ý về target/
  price/time/sequence/availability.88pilotslots bridge không đổi. Mỗi reader
  qua108.803.327prefixrows; không108triệu financialsamples hoặc fullpathaudit.
-5causalfeaturetests trước đó giữ;4financialcomponenttests mới đạt.60synthetic
  BUY/SELL/normal/zero-variance/missing/late/null/weekday cases +8mutations đã
  reviewed trước actualnumeric. Unknownselected không bị đổi thành0; empty
  calendar/history không tạo falsepass. Nativecostcore được reuse.
-521actualrows×3rules×2costs=3.126financialcases/12books. Reviewer không import
  producer feature/costhelper chooracle: rational pairwise-variance identity
  khác, clocks/known-at/calibration/signals/costs/rounding/ledger sums/gates
  đều khớp.8actualmutations feature/side/net/commission/clock/calendar/authority/
  gate bịreject; unknownbranch đã kiểm ở synthetic vì actualselectedunknown0.
-Source4mutations price/time/sequence/missingtarget bịreject; sourcefalseauthority
  mutation được kiểm thêm trước economics. Sameagent/differentcodepaths/math,
  không độc lậphuman/feed/process. Không gọi financialresult`pending_review`
  là chưa chạy: `review.json` bind exactresult, progress`completed_reviewed`.

## Giữ để làm gì, chưa được suy điều gì?

Giữ **một exactversion** cho temporalrobustness trước đầu tưriskwrapper.
Chỉ27opportunities trong hai năm exposed; không đủ kết luận expectededge,
không cleanOOS hoặc selection-adjusted evidence sau toàncampaign. Entrymask
hiếm có thể quá chậm cho3/6/12months; chưa có evidence account-return/timefit.
Không tăng lot, đổi n/k/clock, loại subgroup thua hoặc mở2025+ để cứu.

ComponentkhôngSL: chưa biết pathadverseexcursion/stop truncation, gaps/margin,
account-wide equity/dailyreset/firstbreach, program rules hoặc khả năng payout.
Tổng fixednotional dương không cho kết luận trade1lot an toàn hoặc bỏSL. C1/C2
chưa đạt. Bước tiếp: đăng ký mở rộng lịch sử đã consumed, giữ nguyên rules/
costs, reuse exact2019/2022results và quotes đãverified; chỉ source/years mới
cần review thêm. Sau độ bền mới chốt risk mechanism và nativeprop/time-fit.

## Timing và hậu kiểm

| Lát | Actual wall | CPU / scope |
|---|---:|---|
|Fullsource4partitions +raw/native/cache/oracle/bridge|175,771s|159,422sCPU;0GET|
|Synthetic preflight|0,192s|60wirecases/8mutations, khôngalpharesults|
|Numeric component|0,364s|Nằm trong economicphase bên dưới|
|Economicphase gồm fullreview/mutations|2,125s|2,047sCPU,3.126cases|
|**Successfulworkerphases không đếm lặp numeric**|**178,088s≈2phút58s**|Không research/code/tests/oldpilot|
|4focusedcomponenttests|0,052s unittest body|Không end-to-end commandwall|

Không số đo peakRAM hoặc end-to-end authoringtime, ghi unknown. Source scan
chi phối; chưa cần GPU/Rust hoặc sửa loop tiền đã dưới1s. **Tối ưu dùng lại
ngay:** sealed1.954targetpacket/27selectedcases và baseline2019/2022, không
chạy lại source hoặc numeric unchanged khi mở study kế. Runtime đổi là
consumeradmission mới, không sửa originalcache/runtimebinding cho nhanh.
Các kỹ thuật rawindex/chunking chỉ xét khi phải lặp scan cùngraw cho nhiều
consumers mới; chưa thêm framework/indexservice vì một lượt fullscan3phút.

Khôngfailure/retry trong fullsource/preflight/economicphase này. V1runtime và
v2Fridayfixturefailures vẫn ở [priorreceipt](FX-ABNORMAL-DAY-SOURCE-FIXTURE-RESULTS-20261109.md).
Khôngjobnền khi đóng lượt;0model/broker/network/own2025+ ở numeric/source.
Không product/runtime/globalenvironment/skill mutation.

## Artifact để tiếp tục

Privatebase `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`:
`execution-v1/fx-abnormal-day-full-source-v1/` giữcalendar1954targets/manifest/
source-receipts/current-native/cachedreference/Fractionoracle/progress/events;
`execution-v1/fx-abnormal-day-component-v1/` giữpreflight/normalizedinputs/
source-snapshots/inputmanifest/rows/summary/decomposition/result/review/progress.
Savedcontrollers `run-fx-abnormal-full-source-v1.py` và
`run-review-fx-abnormal-component-v1.py` tại privatebase, không overwriteoldroot.

| Artifact | SHA256 |
|---|---|
|Fullsource result|`bc3794d9f64972a5dc4cacc57d98c5788b3f33c6dffb4accecd16324e382f0dc`|
|Economic result|`43454a8483249a1af0a10b306875a0385cb9876f8fa99acbac8883b05c1b30c9`|
|Economic review|`8cde4ffd64e3d74a6fa0172dc90a200d11f77a54d45c794f0f6a96be330b9561`|
|Summary|`e5d025081274432210c072dbc034ff6bc0c84450326475f74a7448e1f5ea899a`|
|Decomposition|`78975f945a0562ed2885fc78fdd6be8100da9e2aa91850db7639fbe9c6b1b34c`|

Catalogue89researchrecords/58accountpolicyversions; không đếm source/price
component thành executablebot/nativeaccountpolicy. Goalactive/chưachallenge.

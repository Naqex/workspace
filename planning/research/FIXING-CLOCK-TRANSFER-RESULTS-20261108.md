# Đợt discovery mới: thêm15phút không cải thiện kết quả — 08/11/2026

Đã thực hiện [protocol58d2ae9](FIXING-CLOCK-TRANSFER-PROBE-20261108.md),8tests
trước numerical, rawquotes/currenttypedcostcore. Đây là completion của **đợt
nghiên cứu hữu hạn** owner vừa giao, không hoàn thành mục tiêu dài hạn tìm
ứng viên challenge. Không rerun624cases hoặc source/tickbacktest cũ.

## Các quyết định được lưu

-24exactFXversions trên19cataloguerecords đã **gác sau frozen costscreen**:
  [624outcomes](EURUSD-CATALOGUE13-RESULTS-20261108.md) và
  [version decisions](STRATEGY-CATALOGUE-20261107.json). Tất cả stress total
  âm, không chỉ fail9/13yearheuristic. Reopen chỉ khi có lỗi material cần
  correction hoặc câu hỏi mới có registration; không dispatch lại không đổi.
-GoldSMA50k vẫn researchsurvivor/deprioritized theo
  [review](GOLD-SMA50K-REVIEW-20261108.md), không bị gác theo FXdecision.
  ML/index/controls và16ideas chưacode giữ đúng trạng thái/evidence riêng.
-Catalogue vẫn53records/41policyversions; probe endpoint này chưa strategy
  implementation mới. Một lỗi cập nhật cộtMarkdown được sửa8c3a75b trước
  kết luận:53rows/6columns/versionsnumeric khớp, không đổi JSONcounts/outcomes.

## Câu hỏi và kết quả

Giữ cùng SELLentry02NY, so exit14:00Berlin(parentclock) với14:15Berlin.
Loại ảnh hưởng SL/sizing để hỏi riêng **15phút đó có bị bỏ lỡ không**.
Đây là exposed component EURUSD đơn lẻ, không paperportfolio replication.

Đơn vị bảng là **tổng pip sau spread/commission/slippage trên những ngày đủ
quote**; không accountPnL, risk25USD, annualreturn hoặc xác suất pass.

| Năm | Calendar weekdays /entryeligible /pairedresolved | Exit14:00 chuẩn/cao | Exit14:15 chuẩn/cao | Paireddelta14:15−14:00 |
|---|---:|---:|---:|---:|
|2019|261 /260 /259|+405,5 /+301,9|+286,5 /+182,9|−119,0pip|
|2022|260 /260 /260|+326,2 /+222,2|+165,0 /+61,0|−161,2pip|

Cùng entry/unit/cost nên paireddelta bằng nhau ở hai costs, không phải2
independentfindings. Primarymean stress0,706/0,235pip perresolvedevent;
min/maxstress2019−57,6/+86,7pip,2022−103,2/+151,2pip. Trung bình nhỏ với
tails lớn không tự là edge hoặc phù hợp challenge. Top3positives chiếm
10,15%/8,46% positivepips, không là robustnesscertificate.

BUYoppositecontrol primaryexit stress−798,0pip2019/−755,5pip2022; không
đổi hướng vì control hoặc chọn đẹp theo outcome. Flat0 không strategy.

**Kết luận cho câu hỏi đã khóa:** trên pairedresolvedevents, dữ liệu không
ủng hộ việc giữ thêm15phút để cải thiện phiên bản cũ. Không sửa exit của
parent sang14:15, không tuyên bố lỗi hệ thống do “lệch15phút”.
`priority_for_wrapper_review=false`; machine status giữ`inconclusive_quote_coverage` do
missingfuture dưới đây. Bằng chứng pairednegative và gapcoverage là hai trục
riêng: không dùng gap để giấu negativecontrast hoặc ngầm tính đầy đủ cảnăm.

## Quality và exposure không bị che

-2019Jan1 thiếu entry trong60s, entryineligible; vẫn trong denominator261.
-2019Dec25 có entry nhưng cảhai exit thiếu trong60s; giữ **1unresolved**.
  Quote đầu sau deadline tới26Dec. Không carry/interpolate/auto-close ởgiá
  bịa hoặc tính missingPnL=0. Không có sourcecalendar để gọi đó chắc chắn là
  marketclosed hay feedloss.2022không có late/missing trong targets của probe.
-Raw66.133.073rows2019/2022 được hash/count/order đúngparentseals. Không
  download, không đọc2025+.2019overlap paperperiod,2022đãexposedresearch;
  cảhai development, không cleanOOS.519resolveddailycomparisons không519
  independentalphas; costs/directions là dependentviews trên cùngquotes.

## Vì sao có component dương mà parent vẫn gác?

Đọc lại exactparentpreECB coarsebooks đã có, không numericalrerun:

| Năm | ParentSL/sizing netUSD chuẩn/cao | Entryfills | Funding / cuối mẫu |
|---|---:|---:|---|
|2019|−177,54 /−364,88|260|0 /flat|
|2022|+3,18 /−134,86|260|0 /flat|

Không so trực tiếp USD trên10k/planned25USD với pip/constant1lot để quy cả
delta choSL. Parent có stop/weights và2019có260fills trongkhi noSLcomponent
chỉ259resolvedpaths. **Câu hỏi kế tiếp có ích** nếu tiếp tục cơ chế này:
giữclock14:00, đối soát từng entry và tách tác động stop/weights/coverage trên
commonmask trước thay rule. Cần protocol riêng; chưa có causalmeasurement của
SL hoặc một chiến lược bỏSL đã được duyệt. Không tăngrisk hoặc bỏSL trongbot.

Như vậy đợt này loại được một giải thích cụ thể và định vị câu hỏi tiếp bằng
evidence, không mở thêm indicatorgrid hoặc batch13years để hy vọng ra winner.

## Correctness, logs và thời gian

| Lát | Bằng chứng | Thời gian |
|---|---|---:|
|Tests trướcoutcome|8focusedtests:BUY/SELL,NY/EUDST,60sinclusive,futureexit/eligibility,commonmask,sourcefirstquote/hash/count,CLI2syntheticyears vànooverwrite/badfixtures|0,836s|
|Numericalcomponent|521events/12annual-cost-viewrows, quotes/previoussourceordinals,pins/snapshots/logs.2rawscans, khôngposition/sizing/backtestengine |47,438s;CPU42,938s|
|IndependentCSV/Fractionoracle|3119selected/predecessorrawrows khớp;3114financialchecks;calendar/status/sum/mean/min/max/signcounts/pairedsum khớp|37,301s|
|Event→source linkage|1563eventquote links;3119requiredrawrows bằngoraclecount;8actualin-memorymutations(price/ordinal/missing/duplicate) bịreject|Chưa timer riêng|

Oracle dùng implementation riêng không importsimulator/probe/costhelper;
vẫn cùngagent, không independenthuman/modelsign-off. Không fullfeedquality/
currentbroker/historicalfills/propDD/SLproof hoặc calibratedstatisticaledge.
Hash/sourcebindings không thay những gates đó.

Private root:
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/execution-v1/fixing-clock-transfer-v1`.
`manifest.json`,source-snapshot,events/proofs2019/2022,`result.json`,
`progress.json`,events.jsonl,`review.py`/`review-result.json`,
`review_linkage.py`/`linkage-review.json` giữfullreceipt.
NumericalresultSHA`98414710bdf3d73e39033c2b5b12ec8866d7a13d315302d13661022c4243be34`.
Source58d2ae9 pin trướcnumeric; documentation8c3a75b sửa cataloguecolumn/routing,
không đổi financialsource/protocol. Numericalsession75010 vàreview74953 đã
terminalexit0;không còn worker. Không broker/model/marketdownloadcalls.

Sau review không có materialfinancialbug mới cần sửa; không rerun numeric
chỉ để bổ sung linkagepacket hoặc viết báo cáo. Bottleneck chính là đọc/hash
raw cho provenance, workload<1phút; chưa cầnGPU/Rust/newframework. Goal của
đợt có đủ design→test→numeric→review→decision; C1/C2dài hạn vẫn chưa đạt,
không mởholdout/broker/paidaccount/challenge/production.

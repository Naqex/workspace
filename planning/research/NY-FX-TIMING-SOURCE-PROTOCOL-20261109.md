# NYFX: fixture M1 cho câu hỏi độ trễ, chưa thêm chiến lược

Đăng ký trước sourceM1fetch và inspection; không PnL/selectiontrades. Parent
[R070/R071results](NY-FX-REVERSAL-RESULTS-20261109.md) là negatives của onehour
H1adaptation, giữ nguyên pins/outcomes. Không gọi originalpaper đã bị bác bỏ.

## Vì sao đây là câu hỏi đáng kiểm?

Paper có15minlagcheck, parent dùng1hour vì H1Openproxy. Chênh lệch này lớn so
horizon đảochiều; không biết nó giải thích negative hay không. Muốn đo cần
paired **cùng M1source/engine/rules**, chỉ đổi lag60→15minutes. Không được so
M1newPnL với oldH1PnL rồi quy toàn bộ delta cho latency: intrabarSL/sourcebar
semantics cũng đổi. Đây là hypothesis/source/model revision riêng, không bugfix
đã được chứng minh và không quyền đổithreshold/risk/MA4/SL/cost để cứu outcome.

## Source fixture cố định

- ExistingDukascopy/pinned1.51.1 EURUSD Bid/Ask M1; exactUTCdates
  **2019-01-06/07/08 và2019-03-10/11/12**,12dailyURLs. Targetweekdays Jan7/8 và
  Mar11/12 chọn theo winter/US-DST/weekend transition trước source, không theo
  PnL/news. Sundays là pastwarmup,không trade. Own2025+đóng; no otheryears.
- Source-onlyview từ immutable nativeexpanded exports/raw; reuse getCachedM1,
  Fraction/Decimaldecoder/candleprovenance. Explicitvolume0giữ; decoderpadding
  khôngobservations. UnitsUSDperEUR/tick0,00001/nativevolume millions, UTCms/
  minutestart, Closeknownafter+1min. H1features sẽ là aggregation observedM1,
  không tựfill60minutes hoặc assumeH1providerfile giống toàn bộM1.
- Report perday/side schema/order/grid/OHLC/rawcensus/hash; prior15hours cho
 10/11/12/13NYfeature readiness; exact4actionminutes(:15 và next:00) và15NYexit,
  fullheldsessionminute presence vàunpaired/crossedOpenClose. Missing/crossed
  được giữ; chưapricefillability hoặc jointticks. Đối chiếu H1source cũ trong
  samehours theo trường/coverage; discrepancy phảiphânloại trước economics,
  không sửa raw hoặc hạsourceguard để thành parity.
- Output `execution-v1/ny-fx-timing-source-fixture-v1`:12nativeexports/seals/
  rawproofs/snapshots/manifest/census/progress/events/result/review, protocol/
  package/helper/lockfile pinned. Existingcache reuse, không globalinstall.
- Retry0,cumulativefailurecap1,WAF/token-cacheoff,onewriter/CANCEL/deadline180s.
  Fetch sequentially12URLs; schema/403/auth/rateblock khôngbypass. Giữ partial
  books/failure, không restart vì observertimeout. Không newprovider/OAuth/key/
  paidservice/broker/modelcalls, khôngstrategy/outcome/prop/holdoutqualification.

## Acceptance và bước sau

Fullraw→native/canonical fields, source timestamps và volume semantics được
kiểm bằng implementationkhác; mutations sai price/time/count/hash/authority
bịreject. Statussource-only, dù mọiminuteđủ không thêmcataloguestrategycount.
Fixture thiếu thì chốt gap/nextsmallstep, không substitute ngày khác để pass.

Chỉ khi fixture đủ semantics mới đăng ký pairedM1history2019/2022 và exact
SL/entry/exit/lifecycle/sizing/quality/gate, trước neweconomicoutcomes. Candidate
MA4/day/risk/cost giữ nguyên; closeat15NY, quyếtđịnh10–13NY. Latency15/60 chỉ là
factor đã nêu,khôngparametergrid. Muốn tách timing thật phải cùng signalbar/
fillsource/pathresolution; fullpairedaccountstate có thể diverge, không cộng
PnL riêng từnglệnh thành portfolio. Không rerun oldH1 hoặc gọi4days là đủedge.
Lưu phasewall/CPU/cache/negative/gaps vào existingresearchowner; không thêmUI,
DB/RAG/skill/framework hoặc migration/xóa dữ liệu. GoalC1/C2tiếp tục active.

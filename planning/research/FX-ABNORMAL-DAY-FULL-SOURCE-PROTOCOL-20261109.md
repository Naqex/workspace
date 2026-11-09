# R089 v2: census nguồn toàn2019/2022 trước economics

Theo [economic protocol cùng amendments](FX-ABNORMAL-DAY-PROTOCOL-20261109.md)
và [fixture88/88](FX-ABNORMAL-DAY-SOURCE-FIXTURE-RESULTS-20261109.md).
Giữ active20hproxy00→20UTC/calibration20weekdays/k2/nextdayreversal01→08UTC,
minimum8selected/năm chỉtriage. Chưa realfeatures/selectedcounts/PnL ở lúc
đăng ký; calendar census dưới đây không đọc giá.

| Partition | Source targetslots khóa trước quotes | Vai trò |
|---|---:|---|
|2018|42|Calibrationwarmup cho đầu2019|
|2019|938|Dayproxy00/20 +entry01/exit08, dedup theo timestamp|
|2021|40|Calibrationwarmup cho đầu2022|
|2022|934|Dayproxy00/20 +entry01/exit08, dedup theo timestamp|
|**Tổng**|**1.954**|Không phải1.954trades hoặc market samples độc lập|

Entrycensus:2019 có261weekdays/209calendar-eligible Tue–Fri;2022 có260/208.
Mỗi eligible entry yêu cầu20weekdays trước shockday +shockday, fixedslots00/20;
dayproxy/quote targets deduplicate nhưng không xóa observations/weekdayrows.
Warmup không financialPnL. Không2018/2021economicoutcomes, khôngown2025+.

## Source-only admission

Reuse sealed parent config/result/review `pre-ecb-long-price-v1` cho cả4years,
và sourcefixturev3 resultSHA
`c7d8727bed0ebe200fccb045749e0156ed46ff7456c36cb21dc5eca74b8b5432`.
Không refetch/rebuild, sửa nativecachekey/runtimebinding hay oldreceipts.
Giữ currentconsumer/oldproducer runtime riêng như registeredfixturev3.

- Primary currentnative quote decoder lấy first-aftertarget từ raw; Fraction
  decoder/selector khác đọc rawprefix và predecessor. Readonly H1 reference
  giữ originalSHA/payloadchecksum/binding/sourcehash/count/sequence, current
  modelvalidation được ghi riêng; không gọi native runtimecache đãaccepted.
- Kiểm tất cả1.954slots, field giá/grid/actualtime/sequence/lag≤60s; bridge đủ
 88pilotslots không đổi. RawfullSHA kiểm trước dùng; 4years gần như fullraw
  prefixes vì có targetcuối năm, không gọi đây là SL/path/execution audit.
- **Missing/late là output hợp lệ của source census**, không falsequote hoặc
  financial0. Cache/native/oracle phải đồng ý về availability; resolvedslots
  phải khớp mọi field. Sourceviewadmitted nghĩa transforms/provenance/census
  đúng, không1.954available. Khác fixturepilot yêu cầu88/88available, đây là
  census fullcohort chấp nhận unknown đã khai báo để không selectionbias.
- Normalized feature observations chỉ nhận quote tronglag đãreview, còn lại
  None kèm source reason gốc. Feature unavailable là known-at skip; selected
  entry/exitmissing giữ unresolved tài chính. Không dùng futuremissingexit để
  thay signals, xóa ngày hoặc chọn sample.
- Fullcalendar dựng lại bằng cách khác; mutation sourceprice/time/sequence/
  missingtarget và falseauthority phải bịreject. Không coi sourcegate làedge.

Một writer/output `execution-v1/fx-abnormal-day-full-source-v1`, deadline300s,
progress/PID/events theo year/counter, nooverwrite/CANCEL/failure/snapshot/pins.
Không auto retry do observationtimeout hoặc rerun đãsealed để đẹp report.
Source-stage không gọi feature/finance; financial stage chỉ sau source admit
và synthetic financial review, native costcore/declaredfees giữ nguyên.

## Economics sau source/preflight

521weekdayrows×3rules(primary/opposite/null)×2costs =3.126financialcases,
12books. Số trade thực là selectedshocks được báo riêng, không3.126samples.
Known-at calendar/history/normal skips có0exposure, không giảunknownselected
thành0. Financial strictnet N/A nếu còn selectedunresolved; report knownsubset
riêng, denominator và unavailablehistorydays rõ. Review riêng mean/variance/
signals với rational variance identity khác, costs/rounding/net với Fraction;
không import producerfeature/costhelper cho phần oracle.

Kiểm toàn rows/12books, primary/opposite/costs/null và gate≥8/coverage/strictnet;
mutation feature/side/net/commission/calendar/unknown/authority/gate phải fail.
Giữ code/input/protocol/runtime SHA trước numeric, output mới, timings/source
và numerical scope tách riêng. Cùngagent/codepath khác, không độc lậphuman/feed.
Chưaaccount/SL/equity/targetfees/prop/timefit/OOS/prospective/ownerhandover.

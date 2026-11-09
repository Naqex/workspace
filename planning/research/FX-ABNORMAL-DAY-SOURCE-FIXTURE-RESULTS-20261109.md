# R089: source fixture đạt, chưa real features hoặc PnL

Tiếp [method](FX-ABNORMAL-DAY-METHOD-ADMISSION-20261109.md),
[economic protocol và amendments](FX-ABNORMAL-DAY-PROTOCOL-20261109.md),
[source fixture protocol](FX-ABNORMAL-DAY-SOURCE-FIXTURE-PROTOCOL-20261109.md).
Active component dự kiến `eurusd-prior-abnormal-20h-day-reversal-utc-v2`.
**88/88slots resolved/đối soát**,4mutations reject,5featuretests đạt.
Chưa tính real-data features, số shock, financial outcomes hoặc account PnL.
Catalogue vẫn88records/58accountversions, ID R089 chưa tính như policy đã chạy.

## Đã kiểm và sửa gì?

| Lát | Kết quả thực tế | Quyết định / giới hạn |
|---|---|---|
| Primary method | FX paper đầy đủ §§3–4/Tables1–5; sample2008–2018, không transaction costs | Lấy cơ chế làm hypothesis, không copy headline PnL hoặc tiêu chí winrate≥50%; own n/UTCproxy khác paper |
| Calendar alternatives | Preholiday large-cap premium suy yếu; FOMC cycle có đổi chiều sau mẫu ban đầu | Không mở hai batch chỉ vì literature cũ từng có kết quả đẹp; không bác bỏ mọi phiên bản |
| Runtime reuse v1 | Python3.12.14/Pydantic2.14.2 khác producer3.12.10/2.13.5; native cachekey mới không tồn tại | Giữ failure, không sửa pin/loader; registered source view riêng giữ original runtime và ghi current consumer |
| Dayproxy v1 |80/88slots tronglag;8slot không hợp lệ đềuFriday23UTC, firstafterSunday | Dayproxy23h không khả dụng cho20weekdays liên tiếp; không dùng Sundayclose giả hoặc xóaFriday |
| Dayproxy v2 |End20UTC cho **mọi** weekday, source fixture mới88/88slots đủ | Sửa trước realfeatures/PnL, không rescue theo outcome;20hproxy vẫn không dailyclose đúng paper |
| Causality |5tests: calibration tách shockday, futureoutcomes không ảnh hưởng, strict2sigma boundary, missing khôngbackfill, Fridaypreclose regression | Chỉ feature contract; chưa statistical edge/account/prop/fullsource |

Minimum8selected/năm là heuristic ưu tiên đã sửa trước realfeatures/PnL từ
minimum20banđầu, sau đọc tần suất thấp ở paper. Lịch sử/ngưỡng cũ/lý do giữ
trong protocol; không chọn theo counts của ownstudy. Giữ sourceunknown,
strictnet và C1/C2;8events không đủ tự chứng minh edge.

## Source view và đối soát

05/02/2019 và01/02/2022 là Tuesday đầu tháng2, chọn bằng lịch trước đọc giá.
Mỗi date21weekdayobservations×2slots00/20UTC +entry01/exit08UTC=44targets.
Nguồn EURUSD QDM jointtick đã consumed, không sourceM1 separate-side hoặc
giá bịa từ OHLC Close. Native quote decoder đọc selectedfirstafter từ raw;
Fractiondecoder riêng đọc rawprefix khác codepath và kiểm predecessor.
Cả hai so với H1 firstquote của cache reference đã niêm phong, actualtime/
sequence/Bid/Ask/lag≤60s khớp.4mutations price/time/sequence/missingtarget bị
reject bằng comparator đang dùng. Hai reader đều qua5.205.206prefixrows;
đây là cùng feed/agent, không hai market samples hoặc human review.

Registered readonly reference kiểm rawSHA/cacheSHA/originalpayloadchecksum/
binding/date/sourcecodepins/counts/sequence và model validation. Current
consumer runtime ghi riêng, không thay originalproducerbinding hoặc gọi native
runtime cacheloader đã nhận cache cũ. Full rawSHA được kiểm; rawdecoder oracle
chỉ prefix tới targetcuối, không independent audit toànyear/path/SL/feed.
Source/root/trader code và oldcache không sửa. Model/engine/broker calls0.

## Thời gian, failure và provenance

| Lát | Actual wall | Phạm vi |
|---|---:|---|
|3public PDF captures +selectedtext|16,340s|Không market data; không tổng research/code time|
|V1 runtime failure|11,953s|0realfeature/financialcase; originalfailure giữ|
|V2 source review|25,595s|88targets,80resolved, source gatefalse|
|V3 source review|14,723s|88/88resolved,4mutations reject; CPU14,375s|
|5focused featuretests hiện hành|0,017s unittest body|Không end-to-end wall hoặc performance benchmark|

V2/V3 cùng sourceyears nhưng differenttargetsemantics và cache/IOconditions,
không gọi25,595→14,723làspeedup cùngworkload. Chưa có bottleneck cần GPU/
Rust/dependency mới hoặc rerun numerical batch. Đã bắt lỗi trước financial
run; đúng thứ tự preflight, không coi failedfixture là strategy thua.

Privatebase `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`:

- `execution-v1/frontier-method-admission-v1/`:3PDFs/selectedtext/receipt và
  renderedFXpage4 đã xem trực quan; koPDF11pages/Fed29/FX12. Không redistribute.
- `execution-v1/fx-abnormal-day-source-fixture-v1/`:failure/manifest/snapshots;
  `v2/`:80/88reviewed; `v3/`:active88/88source-onlyresult. Tên đầy đủ giữ prefix
  `fx-abnormal-day-source-fixture-` cho từng sibling, không sửa bytesattempt cũ.
- Saved `fetch-frontier-method-sources-v1.py`,
  `run-fx-abnormal-source-fixture-v1.py`/`v2.py`/`v3.py` tại privatebase.
  Mỗi attempt có PID/events/status/timers/pins/source-snapshot; đều terminal.

| Artifact | SHA256 |
|---|---|
|V3 result|`c7d8727bed0ebe200fccb045749e0156ed46ff7456c36cb21dc5eca74b8b5432`|
|V3 source receipts|`d8db2ff289636784a841c539c5dd96e93f157d9c4955fbd54cdff30777691b3b`|
|V3 native targets và reference targets|`e782f49f82ceab395a9757f314acc93b18f989dadb2fc72d0e42d1d006918479`|
|V3 Fraction oracle targets|`b286693a309d7db04d63926b2f3a5f94306970e6bec7900069cdf1362956f1b3`|
|FX primary PDF|`340080644276413e9d04d5289ea2ed77dcc5ab4877140dcff1e6c8da92d7de47`|
|FEDS2026-023 PDF|`0fa80a4af119ceb69876ca01549261174bd6034964282b0d726222f2a5465d92`|
|Holiday replication PDF|`039d0939df6c5096a9b4aa4918fea95db0230f21cde1f9eabab772e430637b1b`|

Feature code: `tooling/ai-engines/abnormal_day_feature.py`, stdlib exactFraction
cho squared2sigma comparison; không roundedsqrt làm đổi signalbranch.
Protocol freeze trước source lần lượt `9f19696`/`7f5022d`/`1231752`. Những
amendments công khai lý do/old→new trướcaffectedsource/outcome, không ghi
đè history. Historical studies của oldruntime không tự biến thành accepted
current-runtime simulations hoặc bị xóa; consumer mới cần đúng admission.

## Resume

Khôngcònjob của lượt này, C1/C2 chưa đạt, Goalactive. Bước tiếp **fullsource
census** của2019/2022 với calibrationwarmup2018/2021 đã consumed, theo20hproxy
v2. Đăng ký partitions/targets/old→newconsumer trước đọc; reuse sealedreference
và raw, không refetch/rebuild hoặc copy88pilot thành fullcoverage. Mọi weekday
và unavailable phải córow; selectedunknown không thành0. Sau source/preflight
costs mới được chạy financial component và separate reviewer. Chưa native
account/prop/OOS/prospective/ownerhandover, không tănglot hoặc mua challenge.

Không cần skill mới: existing source-transformations/research/qualification/
retrospective đã yêu cầu các bước này. Vấn đề ở contract/runtime cụ thể,
không bằng chứng cần thêm manager/framework hoặc sửa global environment.

# R067: nguồn đủ, quan hệ cố định chưa đạt bộ lọc

**Method follow-up 09/11:** đã đọc full methods/results/conclusion của CESifo
12559 tại [method delta](GOLD-SILVER-METHOD-DELTA-20261109.md). Không dùng điểm
gãy chọn sau toàn mẫu tới 2025 để bật bot ngược từ 2018; không rerun R067
hoặc thêm record. Fixed formation verdict và p-values bên dưới giữ nguyên.

Theo [protocol](GOLD-SILVER-FORMATION-PROTOCOL-20261109.md) `470442c` và
implementation `a9a2b48`, history/source/sample/statistics đã hoàn tất và được
review riêng. **Gác exact XAU/XAG fixed formations này trước economic design.**
Không có bot/returns/PnL mới hoặc ứng viên challenge; Goal C1/C2 vẫn active.

Vàng và bạc có thể cùng chuyển động mà chênh lệch giữa chúng vẫn trôi lâu.
Lượt này hỏi liệu một quan hệ tuyến tính cố định đã đủ căn cứ để nghiên cứu
bot quay về cân bằng; chưa hỏi bot có kiếm được tiền sau phí không.

| Formation | Ngày đủ/định trước | OLS beta | Cointegration p | Bộ lọc p<=0,05 | Kết luận scope |
|---|---:|---:|---:|---|---|
|2018|251/251|0,581701|0,743909|Không đạt|Không ưu tiên exact fixed formation|
|2021|252/252|0,174709|0,093324|Không đạt|Không ưu tiên exact fixed formation|

Orientation y=ln(XAU BidClose),x=ln(XAG BidClose), fixed Engle–Granger constant/
maxlag1/autolagNone. Năm2021 còn không đạt leg-level nonrejection condition;
không suy các pretests chứng minh I(1). Nonrejection của no-cointegration không
chứng minh không có quan hệ hoặc mọi pair strategy vô dụng. Không đổi năm,
giờ, orientation, lag hoặc threshold để tìm p nhỏ. Chưa pairPnL2019/2022.

## Source/data/role đã kiểm

-96rawmonth sources,8side/year exports XAU/XAG2018/2021:47.252H1bars,
  236.260price/volume fields khớp canonical và Fraction integer-delta paths.
  Giữ source-listed rows, kể cả zero volume nếu có;22.360native padding rows
  bị loại khỏi source-only views, không rewrite raw/native export lịch sử.
-Mỗi asset/year có paired source-hour presence; không crossed Open/Close hoặc
  unpaired hours trong4asset-year groups. Đây là separate side H1 bars,
  không chứng nhận actual jointtick hoặc executable fill.
-Sample16UTC H1Close/known17UTC, dates theo frozen US cash calendar chỉ là
  thiết kế mẫu, không metals opening-hours.503/503dates đủ,1.006BidClose
  observations kiểm nguồn; không drop/asof/fill ngày thiếu/crossed.
-Three focused tests trước outcomes: source/time/side roles, missing/crossed
  census chặn statistics, scope/grid/order/closedholdout. Synthetic metals
  role mapping +4Decimal80 checks đạt trước actual formation diagnostics.
-Full reviewer dựng lại date census/giá và dùng immutable R035 Decimal80
  log/OLS/residualADF oracle qua alias keys tường minh.8coefficient/SD/tstat
  checks khớp;6mutations price/date/count/authority/stat/hash bị bắt. Stored
  samples/legs vẫn ghi XAU/XAG, không giả đã dùng GBP/AUD data.
-P-value/critical curves và legADF vẫn cùng pinned statistical library;
  chưa independent inference/human/model sign-off. Không lấy pvalue như tem edge.

## Engineering retrospective

| Phase đo được | Wall /CPU | Quyết định |
|---|---|---|
|History8exports/96months|45,071s /1,438s|Cache4hits/92misses/0unknown; bốn Nov2018raw từ pilot được reuse|
|Full source review|3,180s /CPU chưa đo|Reuse reviewed views sau này; không decode lại fullraw không đổi|
|Sample+statistics driver|2,205s /CPU theo result|Nguồn đã admit trước stats; không training hoặc PnL|
|Independent sample/Decimal review|1,762s /CPU chưa đo|Giữ inference limitations rõ, không bỏ audit để chạy nhanh|

Đây không phải native replay benchmark hoặc end-to-end researchtime. Source
job chủ yếu chờ cache/network; không có căn cứ dùng GPU/Rust rewrite. Cache
response instrumentation chỉ pass-through trong process riêng và được restore
ởfinally; không sửa installed library/global configuration. Không dependency
install/update. Source/stat workers và reviewers đều terminal0, không job chờ.

Private base `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`,
locators dưới `execution-v1/`:

| Artifact | Binding |
|---|---|
|`gold-silver-history-v1/result.json`|SHA `cfa8e19b9d93ad615153e4a83ddb2997727a43ce21b6d25dfa9a9ac316907e20`|
|`gold-silver-history-v1/review.json`|96rawhashes/fullsource/quality/mutations|
|`gold-silver-formation-v1/result.json`|SHA `682cf61d972c6c47fa1f9229bf2082324f29cbdab532ee63c201c9b4d41edbc2`|
|`gold-silver-formation-v1/review.json`|SHA `29d130eab98a39398f80d17f7e3e441c4628cc7d0017d6b7d09b01d7c7ad395e`|

History PID26976/stat PID24868 đã terminal. Config/pins/source snapshots/
rawproofs/sample/census/diagnostics/events/timing giữ nguyên để tái hiện.
Catalogue67records/46researchpolicies/25native trước admission hypothesis mới;
statistical probe không tăng count strategies đã code. Chưa runtime/broker/
own2025+holdout/skills/global config/data deletion trong lượt này.

**Tiếp:** [ML labels khớp SL/cost](GOLD-ML-LABEL-ALIGNMENT-METHOD-20261109.md).
Giữ negatives của R038/R039, không nói label mismatch là nguyên nhân đã xác
minh khiến oldML thất bại. Kiểm source/label/clock/split/control trước recipe
và outcomes mới; không ưu tiên một model chỉ vì là ML.

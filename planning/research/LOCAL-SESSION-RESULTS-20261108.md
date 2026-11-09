# Phiên Mỹ chưa đủ ổn để ưu tiên bot — 08/11/2026

Thực hiện [admission/protocol](LOCAL-SESSION-ADMISSION-20261108.md), khóa trong
commita84a2fa trước numeric. Hai giả thuyết đã so: R019retest defer vì exact
recipe chưa đủ cơ sở ưu tiên; R023local session được nhận để kiểm price/cost
component. Không thêm policy/bot hoặc sửa các bản cũ đã gác.

## Câu hỏi và câu trả lời

**Câu hỏi:** mua EURUSD08:00–16:00NewYork, gần method của SNB hơn bản
post-London cũ, có còn lời sau chi phí trên dữ liệu đã có không?

Pip trong bảng là tổng các cơ hội **1standardlot**, chưa có SL/sizing/account.
Không phải return trên10k, lợi nhuận bot hoặc khả năng pass quỹ.

| Cửa sổ đã khóa | Năm | Phí chuẩn | Phí cao | Số ngày đủ endpoints |
|---|---|---:|---:|---:|
| **Primary: BUY08–16NY** |2019|−242,2pip|−345,8pip|259/261|
| **Primary: BUY08–16NY** |2022|+145,1pip|+41,1pip|260/260|
| Context: SELL07Dublin→08NY |2019|+384,2pip|+280,6pip|259/261|
| Context: SELL07Dublin→08NY |2022|+347,7pip|+243,7pip|260/260|
| Opposite control: SELL08–16NY |2019|−152,9pip|−256,5pip|259/261|
| Opposite control: SELL08–16NY |2022|−605,2pip|−709,2pip|260/260|

**Quyết định:** primary không đạt tiêu chí stress dương cả hai năm nên không
ưu tiên risk-wrapper ở đợt này. Không lấy context dương thay primary sau
outcome. Context không độc lập với PreECB; các giờ khác quanh DST và endpoint
khác làm nó không byte-identical với bản cũ. Không tăng samplecount/edgecount
vì chạy hai costs hoặc hai views. Cả hai hướng BUY/SELL phiên Mỹ cùng có thể
âm do spread/phí; đảo dấu một bot thua không tự thành bot lời.

Primary stress theo nửa năm2019:−230,5/−115,3pip;2022:−279,3/+320,4pip.
Phần dương2022 không trải đều qua hai nửa năm; không chọn riêng nửa cuối để
cứu, không gọi halfyear độc lập. Các phân hoạch đã đăng ký trước outcome.

Hai ngày2019 chưa đủ:01/01thiếuentry cả hai legs;25/12primarythiếuentry,
EUcontext cóentry nhưngthiếuexit. Giữ unavailable/status/quotes trên đủ521
weekdays, không fill0 hoặc sửa cửa sổ. Endpoint đầy đủ không chứng minh feed
không gap giữa giờ, native SL fills hoặc prop-equity path.

## Đã kiểm những gì?

| Lát | Bằng chứng | Giới hạn |
|---|---|---|
| Thiết kế | Protocol/source/tests đã commit trước numeric; primary/context/control và retention không đổi sau outcomes |2019/2022đãexposed, không cleanOOS; nguồn EBS cũ khác quote feed/cost của project |
| Inputs/clock | Reuse raw-bound H1, loader kiểm raw/cache hashes/schema/runtime/producer/order; Dublin/NY riêngDST | Không tự đổi oldpins hoặc rebuild; thiếu dữ liệu giữ nguyên |
| Fixture |8tests tính tay BUY/SELL/phí/spread, DST mismatch, weekend, late/missing, sequence/grid/hour, denominator và không cho context cứu primary | Lượt fixture đầu thất bại2assert chỉ do format85.0≠85.00; sửa soDecimal đúng giá trị trước numeric, không đổi core/cost để pass |
| Số học | Separate Fraction implementation kiểm3.114event-cost cases và12summaryrows, counts/missing/halves/concentration/priority | Cùngagent, không independent model/engine audit; mean/share dùng tolerance1e−25 vì Decimal28digits |
| Raw oracle | Hash66.133.073rows;24source endpoint/predecessor links trên8dates sớm nhất khớp,4mutations reject | Chỉ selectedquotes, không whole-year fill oracle hoặc source giá độc lập |
| Vận hành job | Numeric/review terminalexit0, log/status/source snapshots/finite deadline/CANCEL | Không kiểm runtime MT5 hoặc khả năng broker trading |

Private root:
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/execution-v1/`.
`local-session-component-v1` giữmanifest/result/2019-events/2022-events,
events/status/source snapshots,review.py/review-result/review-progress;
sibling `local-session-fixtures-v1` giữtest receipt/log/numeric.log.
ResultSHA `2c68fdc174b022c14f33e0eff181ac7c4c9046d0795f9a5d857776b17722538b`.

## Hậu kiểm kỹ thuật và bước tiếp

- Numeric7,372s CPU7,328s, independent implementation review32,763s. Không
  simulation/broker/modelcalls. Đây là timing lát mới, không claim speedup
  so53phút cũ hoặc công sức end-to-end. Không có numerical retry.
- Giữ cache reuse và raw check; không có measured bottleneck đáng viết Rust,
  GPU hoặc framework mới. Không cập nhật skills chỉ vì batch phải có update:
  research/qualification/hậu kiểm hiện có đã bao phủ workflow này.
- Không sửa/hồi sinh parent, nớiSL/risk hoặc thêm calendar/parameter grid.
  Source literature có ích để chọn câu hỏi, không làm economics tự đạt.
- Đối soát catalogue giữ53records/41policyversions; R023 chỉ thêm component
  evidence. Tính lại `by_readiness` còn sửa aggregate cũ chưa phản ánh R024
  đã mang `component_probe_not_retained`; đây là metadata bookkeeping,
  không numerical result mới hoặc thêm/xóa một chiến lược.
- Đợt haihypotheses đã có kết quả admission và numerical/review; C1chưađạt.
  Goal cònactive vì chưa có review đủ rõ để kết luận không còn phép thử giá
  trị trongscope. Lát tiếp là review cơ hội còn lại theo catalogue/data/cost/
  novelty và giá trị quyết định, trước khi đăng ký đợt khác hay kết thúc B.
  Không tự mở holdout2025+, broker, account/provider hoặc chi phí mới.

Phương pháp nguồn đã lưu trongadmission: [SNB2011-04](https://www.snb.ch/public/asset/en/www-snb-ch/publications/research/working-papers/2011/working_paper_2011_04/publications0_en/working_paper_2011_04.n.pdf),
Table1/2,§2.2. Kết quả ở đây do project tính, không số hiệu quả SNB hiện tại
hoặc exact replication của publishedsample.

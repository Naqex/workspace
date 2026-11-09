# R066 noise14: không ưu tiên tiếp exact recipe

Đã thực hiện [protocol](NASDAQ-NOISE14-PROTOCOL-20261109.md) `f09366f` và
implementation `6ec3d35`, full16 books được kiểm lại bằng Fraction. **Gác
phiên bản này; chưa có ứng viên challenge.** Không đổi risk/cost/exit sau outcome.

| Năm / mô hình | Phí chuẩn net USD | Phí cao net USD | Closed trades/cost | Giới hạn |
|---|---:|---:|---:|---|
|2019 exact|N/A|N/A|104|Unknown khi giữ lệnh02/10; không annual net|
|2019 conditional H1|−214,67|−250,47|135|Một held minute thiếu; kết quả có điều kiện|
|2022 exact|+217,58|+198,44|165|Modeled flat; chưa tick/target/prop/OOS|
|2022 conditional H1|+217,58|+198,44|165|Không uncertainty; trades khớp exact|

Vốn10.000USD/năm, fixed25USD planned risk/lệnh, không compounding. Tám null
books có0trades/0PnL. Một policy mới, không đếm16books thành16strategies hoặc
independent trials. Catalogue66records/46policyversions/25native.

2019 exact dừng ở timestamp1570035480000, vị thế SELL0,19, SL7702,393.
Conditional H1 Ask range7510,14–7548,93 loại trừ SL trong giờ thiếu dưới
giả định envelope. Khoảng PnL collapse thành một giá trị vẫn **có điều kiện**;
không khôi phục quote, xác nhận broker fill hoặc sửa original unknown.
Năm2019 stress upper<0 nên không đạt tiêu chí đã đăng ký; không cần archive
chase/TP/SL/clock tuning hoặc mở holdout để cứu phiên bản này.

## Correctness và nguồn

- 16 focused tests: causal prior14, missing slot không backfill, equality,
  halfday/DST, một delayed attempt/ngày, opposite exit không reverse,
  rounding/quantity/margin, Bid/Ask stop, missing held/terminal và null.
- Fixture ban đầu kế thừa previous close1005 làm expected band sai; sửa
  synthetic warmup close về1000 trước numeric, giữ production gap formula.
  Không sửa giá thật hoặc rule để test pass.
- 12 synthetic Fraction cases trước outcomes khớp: two costs × exact/
  conditional × complete/missing/opposite. Actual logger/progress smoke dùng
  Decimal lồng nhau đạt trước chạy; reuse native rotating logger/atomic JSON.
- Full reviewer tự tính rational bands/first signal, delayed entry/opposite
  exit, stop rounding, quantity/margin, held path, conditional branches và
  cash cho16books;6mutations net/time/stop/quantity/count/authority bị bắt.
  Decimal band representation tolerance<1e−20; signal/stop ticks/quantity/
  prices/money/state yêu cầu đúng, không dùng tolerance để bỏ khác biệt lệnh.
- Source-only exports, warmup/calendar, mixed2022 và parent reviews có hash;
  không tải lại data hoặc giả partial H1 là joint ticks. Đây là cùng agent/
  provider với code path khác, chưa independent human/model sign-off.

Private `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`:
`execution-v1/nasdaq-noise14-v1` giữ plans/books/pins/source snapshots/progress/
events/timings/result/review. ResultSHA
`8c75b9f1f292ef7d30687b95d3a07f8c42f6e4d606a70bb7f372291fb50a5cbd`;
reviewSHA `91e4daa30bee6539a614bda1c94e3a8a8948e4bf4dc90ea426e1f1c7cdacae8c`.
Worker PID20532 và reviewer đã terminal0; không có numerical job để chờ.

## Hậu kiểm gọn

| Lát | Wall time | Quyết định |
|---|---:|---|
|Load+source validation2019 /2022|4,867 /5,192s|Mỗi năm một lần, dùng chung cho8books|
|Prepare causal plans2019 /2022|0,495 /0,529s|Dùng chung exact/cost/null, không tính lại bands|
|Producer toàn lượt|25,324s, CPU24,688s|Đủ nhanh; chưa cần GPU/Rust hoặc parallel rewrite|
|Fraction review toàn lượt|19,927s|Giữ review; không đổi độ đúng để giảm thời gian|

Đây là workload mới, không claim speedup so với R065; authoring/researchtime
chưa được đo end-to-end. Không có logger failure mới. Không cần xóa data,
tạo RAG/service/skill mới hoặc refactor unrelated code trong lượt này.
Giữ existing research/qualification/retrospective skills và ownership native.

Lát tiếp: admission một cơ chế relative-value vàng/bạc với source pilot
nhỏ trước formation/PnL; chung kim loại không chứng minh cointegration.
Kiểm primary method và source/units/time trước, không tiếp tục grid NASDAQ.
Goal C1/C2 active; không broker/holdout/runtime/global configuration changes.

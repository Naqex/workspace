# NASDAQ cash RSI3 + IBS: không đạt sàng lọc đã đăng ký

[Protocol](NASDAQ-CASH-RSI-COMPONENT-PROTOCOL-20261108.md) khóa trước outcomes,
source [M1 history đã đạt](NASDAQ-M1-HISTORY-RESULTS-20261108.md).
8cost/controlcases đã terminal, separate event/Fraction reviewer khớp.
Đây là kết quả một hypothetical unit, **không** lãi/lỗ tài khoản10k hoặc lot.

| Giai đoạn | Phí chuẩn, USD/unit | Phí cao, USD/unit | Lệnh đóng |
|---|---:|---:|---:|
|2019|+37,40|−2,97|9|
|2022|−295,50|−486,42|21|

Không giữ exactrecipe: cả hai stressyears không dương, 2019 cũng thiếu
ngưỡng10closedtrades. Không thêm stop/filter/clock hoặc giảm phí để cứu nó.
4nullcontrols net0; không pending/open hoặc missingfill cuối mẫu. Mọi trade
có observed-path gaps, không gọi là continuous executable path. Source cash
không đầy đủ vẫn safetyEXIT/noentry theo rule trước outcome, không impute.

Đã kiểm:1.728decisionrows qua8cases,60trade-costrecords,162fundingevents,
120entry/exitpricebindings; quantities đều1hypotheticalunit. Source/admission/
case hashes giữ version, independent Fraction signal và event-driven cash
math đối soát;4mutations quote/time/funding/authority reject. Sameagent/feed,
không independenthuman/modelsignoff hoặc bằng chứng noSL account/prop/OOS.
10unit tests đạt trước historyrun,9wire/transitionfixturecases reviewed.

Private`execution-v1/nasdaq-cash-rsi-component-v1` tại campaignroot giữ kết quả,
review/pins/snapshots/status. ProducerPID24620 vàreviewer terminal0.
ResultSHA`fa36f7547fd0d67274ceec7ec7c66ec472f7a92e7c8c63c548fe4d6062f0fc4d`.
Original componentSHA`43912e65810513ea64217e659daa4f868c0ce2d2ee88976c2d69ae14eb65720b`;
source snapshot giữ bytes gốc khi code sau này tối ưu. Không sửa oldpins.

## Hậu kiểm performance: thay đổi trước đo mới

Producer63,872s, CPU63,547s; reviewer18,629s. Replayloop mỗi case khoảng0,1s,
nhưng fullinputvalidation lặp ở8cost/controlcases khiến tổng simulationwall
khoảng46,6s. Chuẩn bị mỗi năm4,6–4,9s; không phải LLMquota bottleneck.

Tối ưu nhỏ: `simulate_batch` kiểm input một lần mỗi năm rồi dùng cùng immutable-
by-convention/read-only view cho4fixedcases. Public `simulate` vẫn kiểm đầy đủ;
không public skip-validation flag hoặc cache tin dựa vào tên file.12tests đạt,
gồm validator1call, exact financial/state parity, input unchanged và crossed
input chặn trước bất kỳ replay nào.

Đăng ký benchmark mới **trước đo**: reuse exact two-year input và oldsealed8
results, ghi source/snapshot hashes mới tại
`execution-v1/nasdaq-cash-rsi-batch-parity-v1`. Chỉ bỏ timing fields khi so
mọi decisions/trades/funding/gaps/rejections/open/pending/totals/authority.
Không thay rules/data/costs/retention; mismatch dừng, không claim speedup.
So old sum8casewall với new sum2batchwall có cùng8cases; totalworkflowtiming
ghi riêng, không so việc tải nguồn12phút với compute vài giây.

Goal C1/C2 active, chưa challenge candidate. Data và component negative được
tái sử dụng; bước tiếp chọn mechanism/method admission khác có lý do,
không mở rộng history hoặc retune exactR063 chỉ vì muốn winner.

### Benchmark đã hoàn tất

8/8case có toàn bộ financial/state outputs exact, chỉ bỏ2timingfields. Tổng
8case từ46,617s xuống12,364s cho2batch, giảm73,5%/nhanh3,77lần trong scope
compute đã đo. Toàn command mới23,534s gồmload/prepare/hash/parity, không
so12,364s với source download719,816s. Single diagnostic sample, baseline là
sealed run trước; không alternating repeats/p95 hoặc wholeproductspeedup.
Mỗi năm chỉ validate1lần,5,741/5,869s; không cần Rust/GPU cho replayloop0,1s.
BenchmarkPID24636 terminal0;12focusedtests đạt. Giữ `simulate_batch` cho lượt
sau; current private v1driver giữ frozen code cũ, không sửa lại để pretend đã
dùng optimization. Artifact mới `nasdaq-cash-rsi-batch-parity-v1/result.json`.
Rules/data/fees/retention/verdict không đổi; không rerun negatives để tìm winner.

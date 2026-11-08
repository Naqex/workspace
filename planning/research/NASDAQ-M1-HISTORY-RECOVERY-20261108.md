# NASDAQ M1: sửa output contract và tiếp tục từ raw cache

V1 của [source protocol](NASDAQ-M1-HISTORY-PROTOCOL-20261108.md) dừng sau
23,303 giây tại kiểm `source_time_order`, 0 book sealed. Giữ nguyên failed
attempt, raw bytes, driver và snapshots; không sửa lịch sử hoặc gọi là data gap.

## Chẩn đoán trước sửa

Cache-only diagnostic `nasdaq-m1-format-diagnostic-v1`: đủ 61 raw BID ngày
warmup2019, 54.977 explicit bars. Request không có `format`; native validated
default `array`. Driver đọc `row.timestamp` trên tuple nên nhận `undefined`.
JSON mapping giữ exact cả 6 trường trên mọi row; timestamp đều integer,
minute-aligned, trong interval và tăng nghiêm ngặt. Không network, không sort,
drop, đổi giá, calendar hoặc threshold; đây là lỗi producer contract.

## Recovery đăng ký trước chạy

Attempt mới `execution-v1/nasdaq-m1-history-v2`, driver/reviewer `*-v2` dưới
private campaign root hiện có. Chỉ thêm `format:'json'`, preflight kiểm output
shape native bằng fixture trước fetch; source-only helper từ chối thiếu format
trước source access. Giữ 8books/1.704rawdays/windows/fees/không economics và
các admission gates của protocol. Deadline1.800s và retry budget6 giữ nguyên.

Pin diagnostic/failure/parent manifest và rehash 61 raw đã có trước chạy;
copy calendar/source captures/admission/sessions exact bytes từ v1 và kiểm
bindings, không fetch calendar lại. Reuse4pilot raw hashes. Cache reuse không
là resume đầy đủ simulation; chưa book nào sealed để resume. Reviewer mới
trỏ v2, giữ nguyên independent Fraction arithmetic và fullsource checks.
Lưu source snapshots trước fetch; newattempt không sửa old helper snapshot.

Thêm regression cho request thiếu/sai format và tuple↔JSON giữ cả6fields,
kể cả explicit volume0. Không thay default native view hoặc upstream package.
Đây là sửa correctness/rework; chưa có speedup benchmark hoặc edge evidence.
Skills research/source transformations/debugging/retrospective hiện có đã
bao phủ workflow; sửa code guard thay vì thêm skill lặp.

Private evidence: `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`.
Sau source/review mới quyết định có đủ đăng ký exact economic recipe không.
Goal C1/C2 active; chưa challenge candidate, chưa holdout/broker/authority.

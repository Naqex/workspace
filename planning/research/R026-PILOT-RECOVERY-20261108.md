# R026 pilot: tiếp tục sau lỗi transport, không đổi câu hỏi

Delta kỹ thuật trước attempt v2; parent
[protocol](RESEARCH-DATA-ADMISSION-20261108.md). Attempt v1 dừng sau1/28
requests,10,999s; raw/native EZU Bid03/01/2022 còn nguyên, chưa PnL. Failure
chỉ giữ generic Error/frames, thiếu status/cause; chưa được gọi chắc chắn
HTTP500 hay timeout. Không đổi ngày/proxy/recipe để vượt lỗi.

V2 giữ cùng28 requests/schema/scope. Pin/copy raw prefix còn có vào cache mới,
kiểm native-seal trước reuse; không ghi thêm hoặc sửa cache/exports v1. Native
retry vẫn0; reuse helper đã có để retry tối đa2lần chỉ timeout/500/502/503/504,
backoff10/20s, cumulative transient cap4, deadline300s. Auth/WAF/403/429/schema
không retry. Giữ logs/status/source snapshots/CANCEL; lỗi thì dừng hữu hạn,
không auto đổi provider hoặc tăng cap. Ghi safe error classification/status/
cause code/frames thay vì chỉ Error hoặc full exception text.

Đây là attempt mới của cùng pilot, không trial strategy mới hoặc mở rộng
quyền. Source/data admission và PnL vẫn tách biệt. Successful cache hit không
là request network mới; kết quả partial không bị xóa.

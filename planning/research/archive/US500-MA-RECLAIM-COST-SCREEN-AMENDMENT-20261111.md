# Tách sàng lọc chi phí sơ bộ khỏi bước kiểm sâu — trước PnL mới

11/11/2026. Original [protocol](US500-MA-RECLAIM-PROTOCOL-20261111.md) và
attempt `us500-ma-reclaim-v1` giữ nguyên:165signals(58/50/57), chưa đạt
priorityfloor200,0financialbooks. Không sửa số đếm hoặc ghi attempt đó là pass.

Phát hiện về thiết kế quy trình: áp floor200 để chặn mọi financialscreen đã
trộn hai bước khác nhau. Đề xuất có trước phép đo là50–100trades cho screening,
200–500 cho review sâu. Chưa đủ mẫu cho review không tự ngăn một phép kiểm
cost/execution sơ bộ có phạm vi nhỏ. Đây là điều chỉnh phân bổ công sức,
không sửa strategy/floor để tuyên bố có edge. Ghi rõ adaptation sau khi đã biết
frequency; không gọi là preregistered từ trước phép đo165signals.

## Đăng ký mới, trước bất kỳ PnL của R123

[Registration máy đọc](US500-MA-RECLAIM-COST-SCREEN-REGISTRATION-20261111.json)
bind exact originalmanifest/result hashes, R123config,165knownsignals và
2022–24. Một G2 exploratorycost/execution screen:6nativefinancialbooks và
3nullcontrols. Không candidate/MA/k/clock/SL/sizegrid. R123 đã chọn trước
frequency, chưa có return outcomes để chọn. Không sửa FP04 hoặc negatives.

Mọi luật setup/confirmation/risk/fills/costs/15:31flat của originalprotocol giữ.
Newoutput/source pins/code/tests và receipts riêng, originalattempt bất biến.
Recomputedfrequency phải khớp58/50/57. `frequency_eligible` vẫn false và
deepreviewfloor200 giữ nguyên; `edge_qualified=false` bất kể kết quả tiền.
Không xin/rộng quyền broker,holdout,provider hoặc deploy.

Kết luận tối đa: implementation/cost sensitivity dưới declaredM1model,
net/annual stability/side/concentration diagnostics. Không confidence95%,
DSR/OOS/prop-fit hoặc challenge approval. Lời/lỗ yếu thì gác exactrecipe hoặc
giữ inconclusive theo coverage; không retune tiếp trong cùng screen.

Không thêm một cờ bỏ mọi gate: CLI phải nhận exact registrationhash, exact
parentattempt hashes và schema/config/date/count/scope checks. Không có
registration thì giữ nguyên frequency-first stop rule. Kiểm tamper/2025+/
qualificationfield và legacyfloor trước chạy. Đây là case cho workflow:
**tách G2 cheapscreen khỏi G3 evidence review; samplefloor là phạm vi đã khóa,
không universal law hay tem chứng nhận.**

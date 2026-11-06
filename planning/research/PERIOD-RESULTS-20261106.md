# Q2–Q3/2022 — kết quả, hậu kiểm và quyết định bước tiếp

## Kết quả đã xác nhận

Batch của [protocol](PERIOD-ROBUSTNESS-20261106.md) hoàn tất **18:21:30 VN
ngày 06/11/2026**, khởi động17:36:40. Pipeline khoảng44phút50giây; numerical
batch2684,94s,2/2jobs completed_verified,4scenarios và8horizon rows. Không
model/broker calls, không final holdout, không còn numerical worker của lượt.

Vốn mô phỏng10.000USD; fixed planned25USD/lệnh, luật gốc, hai declared costs:

| Candidate | Net6tháng phí chuẩn | Net6tháng phí cao | TickDD chuẩn/cao | Lệnh đóng | Quyết định trong bài |
|---|---:|---:|---:|---:|---|
| Z-score |−81,21USD|−117,10USD|153,99/169,52USD|61|Không tiếp tục cấu hình này ở nhánh ưu tiên: không đạt cost screen |
| UTC range |+48,56USD|+39,81USD|128,13/132,85USD|99|Giữ để review validation tiếp; vẫn inconclusive về edge/prop |

Cả hai cuối mẫu flat, không pending, không breach declared profile; mọi cutoff
vẫnphase1/chưa đạt target. Lifecycle `running` nghĩa chưa đạt tại cutoff,
không phải numerical job còn chạy. Không coi PnL dương hoặc zero breach là pass
challenge, đủ broker authority hoặc bảo đảm payout.

## Coverage, costs và độ tập trung

Contributions equity phí cao, USD, gồm floating/phí đã booking tại các mốc:

| Khối quý không trùng lịch | Z-score | UTC range |
|---|---:|---:|
| Q1/2022 — historical engine cũ |−139,30|+26,67|
| Q2/2022 — study mới |+20,03|+105,55|
| Q3/2022 — study mới |−137,13|−65,74|
| Q1/2023 |+61,08|+28,48|
| Q2/2023 |+86,68|+12,54|
| Q3/2023 |+101,37|−43,99|
| Q4/2023 |−69,36|+189,93|

Q3/2022là equity ở cutoff6tháng trừ cutoff3tháng trên cùng account; không
replay quý độc lập hoặc dùng closed-PnL của tháng thoát để thay equity return.
Z-scoreQ2còn một vị thế mở, đã tính floating đúng scope. Source Q1/2022khác
2023/current; chưa chứng minh cross-version numerical equivalence. Đây là7khối
quý không trùng lịch, không phải7mẫu độc lập, không liên tục21tháng và không
được nối ba tài khoản reset thành một equity curve/compound return giả.

UTC range có cả hai giai đoạn dài đã kiểm (Apr–Sep2022vàannual2023) dương sau
stress, nhưng contribution không ổn định: study mới lãiQ2rồi lỗQ3; năm2023
gần như phụ thuộcQ4. Hai quýIIIâm chưa chứng minh seasonality hoặc lý do thêm
summer filter. Sáu tháng mới chỉ+0,3981%initial ở stress; chưa có evidence
time-to-capital phù hợp mục tiêu owner. Không nhân lot hoặc ngoại suy tốc độ
pass từ số trung bình. Z-score giữ negative result và family hypothesis trong
history; không xóa cả họ mean reversion hoặc sửa nó ngay trên outcome mới.

## Hậu kiểm đã thực hiện

Private root:
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/prop-period-robustness-20261106/execution-v1/`.
Report SHA256
`b59aabd4119f82372ad018865b6ada508b740ea35f398bf472b3f0cd7b3423f6`.
`audit_completed.py` đã kiểm2dossiers với actual input hashes/source bindings,
seals và8snapshot rows; report so với snapshot khớp, từng closed-trade price/
commission/slippage/financing cộng về cash/equity. Kết quả ở
`completed-evidence-audit.json`; không numerical replay hoặc mở window mới.

Native consumer cũng kiểm calendar/Prague qualifying days/tick-count/min-equity/
DD so ledger/phase archives. End quote age10.801.797ms, khoảng3giờ trước cutoff
UTC: giữ valuation gốc và tuổi quote, không tạo giá nửa đêm. Không có vị thế
mở cuối mẫu, nên không có floating cuối mẫu dựa vào quote đó.

Pipeline, batch, reporter và worker stderr trống; projection errors0. Tổng
CPU hai workers5048,30s, không là wall time/toàn máy hay quota AI. So annual
2h43với bài6tháng44m50không là controlled speedup: tick count, thời kỳ,
trade path, foreground và workload khác nhau. Không cần GPU/Rust optimization
mới để đóng kết luận này. Partial CLI resume vẫn chưa hỗ trợ; completed reuse
và restartable offline stream là hai capability khác nhau.

## Quyết định và bài tiếp theo

1. **Tạm gác Z-score version hiện tại ở nhánh ưu tiên**, giữ outcomes/code/trials.
   Bản này không đạt screen bài mới và đã có các quý khác âm; chưa có lý do
   mở risk/TP variants để cứu kết quả.
2. **Ưu tiên UTC range cho review validation**, giữ nguyên UTC session, ATR/SL,
   exits, risk và costs. Verdict vẫn `inconclusive`, chưa đủ promotion lên broker.
   Không cần test lại sáu tháng hoặc annual chỉ để đổi report.
3. **Chuẩn bị bàn giao offline dùng lại runner/state hiện có.** Kiểm UTC range
   nhận quote theo luồng, checkpoint/restart và batch parity trên consumed/
   synthetic input. Đây là software validation, không thêm mẫu economic edge
   hoặc thay cửa G3/G4 trước strategy-forward trên broker.
4. **Bài kinh tế tiếp theo nên kiểm nguyên bản đã khóa trên dữ liệu dùng đúng
   vai trò**, trước risk/TP tuning. Hồ sơ cần exact split/exposure/window,
   source/spec/cost/risk, primary net/risk/coverage, quyết định/stop và trial
   history trước outcome. Chưa có executable registration cho2024/2025+,
   không gọi chúng clean OOS hoặc tự mở final holdout. Prior exposure không
   xác minh được thì historical validation phải giữ nhãn đó; prospective shadow
   về sau mới tạo evidence thực sự sau freeze, theo phạm vi riêng.

SMA/Pullback/các ý tưởng dự phòng giữ ở [review](SURVIVOR-REVIEW-20261106.md).
Chúng chưa được promote hoặc chạy lại từ kết quả UTC. Roadmap/scope tiếp ở
[AI plan](../trader/AI-RESEARCH-UI-PROTOTYPE-20261031.md); receipt giữ actual
implementation/test/binding và bước tiếp, không báo toàn bộ mục tiêu đã hoàn tất.

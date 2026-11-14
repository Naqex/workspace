# Chiến dịch độc lập: hệ thống trading tự động cho một owner

Owner giao thực thi và mở rộng phạm vi ngày 15/11/2026. Mục tiêu là có ứng
viên đủ điều kiện Challenge và hệ thống vận hành riêng, tiến tới funded/payout.
Không đạt mục tiêu chỉ bằng code, CI, báo cáo hoặc số backtest tăng lên.

## Quyền và nơi làm việc

- Workspace riêng: `C:/Users/MIIKEY/.codex/worktrees/solo-prop-system/TradingWorkspace`,
  branch `codex/solo-prop-system`, baseline `5864d8b` (PR81 đã merge).
- Trader riêng: `C:/Users/MIIKEY/.codex/worktrees/04e2/trader`, branch
  `codex/solo-system-research`, baseline source `e9ac368`, research note `b944c570`.
- Output riêng: `E:/BACKUP-TRADINGWORKSPACE/solo-system-20261115-04e2/`;
  scoped tests/receipts trong `.artifacts/solo-system-20261115/` của Trader.
- Read-only input: sealed source/evidence đã có. Không chạy entrypoint cũ nếu
  JOB/output còn trỏ về campaign khác. Không sửa checkout, WIP, runtime, DB,
  terminal hoặc campaign V4 của thread gốc. Không chờ kết quả thread đó.
- Dev 2022–2023; 2024 đã exposed, chỉ historical validation sau freeze đúng
  study. 2025–2026 giữ đóng cho tới protocol/quyền mở cụ thể. Warmup từ quá khứ
  được đăng ký riêng. Không mua Challenge, gửi lệnh hoặc đổi tài khoản/provider
  trả phí chỉ vì đã giao research/system execution.

Owner cho phép mở rộng phương pháp, tài sản và nghiên cứu trong phạm vi mục
tiêu; không dùng các giới hạn do agent tự đặt của báo cáo trước để chặn.
Mỗi thay đổi kinh tế vẫn phải đăng ký trước outcome, giữ trial history;
chỉ tiêu không được hạ để gọi winner là đạt.

## Trạng thái và điều kiện hoàn tất từng lát

| ID | Công việc | Trạng thái hiện tại | Bằng chứng để đóng |
|---|---|---|---|
| S0 | Cô lập checkout/output/state | Git riêng đã kiểm; workspace mới tại baseline đã merge | Root đúng, clean/index riêng, không ghi campaign/runtime khác |
| S1 | Map luồng tự động và ownership | Đang đối chiếu source | Nêu rõ engine/research khác runtime advisory/execution; không có sổ tài khoản cạnh tranh |
| S2 | Chặn kế thừa cấu hình runtime trong worktree | Đang sửa launcher + tests | Reproduce fail trước sửa; từ chối trước DB/build; positive isolated profile; primary regression |
| S3 | Skills và AI environment | Sửa bounded runtime skill đang review | Audit cấu trúc/budget, routing đúng standalone, không global mutation |
| S4 | Recovery/reconciliation | 171 scoped offline tests đạt, native process/recovery còn chờ build | Unknown không resend; STOP khác flat; DST/funding/resume; native synthetic rehearsal và restore |
| Q0 | Kế thừa và chọn thí nghiệm | Audit metadata V3 đang thực hiện | Exact candidate, cơ chế, nguồn và gaps, frozen budget trước numerical run |
| Q1 | Source/path confirmation | Chưa chạy outcome mới | Bounded source provenance/clock/BidAsk và full held path; missing vẫn unknown |
| Q2 | Alpha, portfolio, time-fit | Chưa chạy | Phí stress, cadence, trial/dependence, equity lifecycle, đối soát độc lập đúng revision |
| Q3 | Robustness/validation | Chưa chạy | Freeze trước validation; exposed khác clean OOS; stress và unseen/prospective gap minh bạch |
| S5 | Bind chiến lược với engine/runtime | Chưa đủ candidate qualified | Same decision semantics, units/account/risk, no duplicate, exact artifact/code lineage |
| D0 | Bàn giao vận hành cho owner | Chưa đủ | Runnable own setup, stop/recover/rollback, runbook và cách hiểu risk/results; quyền broker riêng |

Goal vẫn active khi còn thiếu ứng viên đủ điều kiện. Kết quả âm/inconclusive
là kết quả nghiên cứu, không phải lý do tự tuyên bố mục tiêu lợi nhuận hoàn tất.
Sau từng đợt finite, cập nhật bằng chứng và quyết định tiếp dựa trên thông tin
mới; không quét hoặc sửa tham số vô hạn chỉ để có PnL dương.

## Nền đã có và giới hạn

V3 có A gốc + EURUSD satellite, 15/36 mốc qua P1, chỉ 2/36 qua cả hai vòng
ở ASYM và chung một funded path, payout0. Đây là baseline đã exposed, không
qualification mới của chiến dịch này. GBP sweep có H1 screen đáng xác minh
nhưng chưa đủ M1/tick; số screen không được gọi là execution-realistic profit.

Trader shadow hiện là advisory EURUSD H4, không tự hỗ trợ A+EUR portfolio.
Historical forex_forward, offline account replay và durable Demo client là
các consumer khác nhau. Phải bind semantic/risk contract trước khi gọi là
một đường end-to-end. Không dùng smoke/fixture để hợp thức hóa dữ liệu hoặc edge.

## Verification và tích hợp

Focused fixtures/saved replay trước; chỉ thêm long/live observations khi
còn câu hỏi thực tế cần chúng. Process, DB và artifact rehearsal dùng tài nguyên
disposable riêng, thu hồi đúng PID/owner. Không dùng test có CREATE/DROP/TRUNCATE
trên DSN inherited. Native binary phải được build cho source đúng checkout.

Mỗi repo một branch coherent; review + tests trước commit/push/PR. Không tự
merge hoặc promote vào lane gốc. Bằng chứng kỹ thuật, kinh tế, prop-fit,
vận hành và quyền execution được kết luận riêng.

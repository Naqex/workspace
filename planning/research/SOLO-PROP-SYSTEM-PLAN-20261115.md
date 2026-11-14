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
| S1 | Map luồng tự động và ownership | Đã đối chiếu, lưu trong Trader execution report | Nêu rõ engine/research khác runtime advisory/execution; chưa có bot A+EUR/GBP broker end-to-end |
| S2 | Chặn kế thừa cấu hình runtime trong worktree | Trader `7241a8b0`: 56 Python tests/53 subtests, 26 Rust AI tests, review độc lập đạt | Từ chối trước DB/build; positive isolated profile; primary regression; chưa rollout |
| S3 | Skills và AI environment | Existing skill/reference đã cập nhật; audit 0 lỗi/0 cảnh báo | 4 links, 7 routing cases; không global mutation |
| S4 | Recovery/reconciliation | 175 recovery tests; restore16/16 và Demo5/5 trên cụm riêng đạt | 47 bảng đối soát; hai grant race winners kiểm riêng; các cụm đã dừng; không broker acceptance |
| Q0 | Kế thừa và chọn thí nghiệm | S01 GBP đã khóa trước source/numeric mới | Một inherited SL recipe, giữ raw markout âm và 112-trial history; chưa mở trial phụ |
| Q1 | Source/path confirmation | Downloader riêng đang chạy, chưa admission cuối | 300 raw/3.576 giờ, reuse292; tải3.284; check20giờ đầu khớp81.345ticks/H1, không thay full gate |
| Q2 | Alpha, portfolio, time-fit | Chưa chạy; adapter synthetic đang review | Sửa ordinal entry/exit cùng-ms ở đường M1; baseline A+EUR cần cùng semantics trước marginal gate |
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

Trader [PR32](https://github.com/Naqex/trader/pull/32), head `621f0e0b`, chứa
isolation/storage fixes và báo cáo kỹ thuật. Git merge-tree không conflict với
main `930fa768`; chưa merge/deploy. Worktree và PR không attach được vào app do
giới hạn100attachments; đường dẫn/URL vẫn dùng được, không tạo checkout thay thế.

## Hàng đợi theo bằng chứng, chưa mở trial mới

Audit riêng chỉ đọc Dev V1–V3: GBP S01 có ưu tiên cao nhất để phân biệt screen
H1 với executable tick path. Không thêm family/exit/risk grid trong lúc chờ
nguồn. Các lựa chọn khác chưa gần qualification hơn: Gold previous-day sweep
chỉ23/22lệnh và retention45,1%/39,3%; Gold TWOBAR −2,21/+6,07R,27/26lệnh.
Đây là kết quả đã exposed, không phải numeric mới của chiến dịch này.

Dự phòng có câu hỏi thực: US500 previous-day NY48H có screen +12,34/+8,16R,
nhưng2023 retention32,97%, friction/SL19,10% và carry/dividend chưa xác minh.
Audit primary FTMO ngày15/11 cho thấy
[index CFDs hiện commission0](https://ftmo.com/en/blog/zero-commissions-on-indices/),
khác legacy$1/contract/vòng. Chưa có đủ dated spec để áp hồi tố2022–2023;
contract/lot/margin, feed parity và swap/dividend vẫn unknown.
[Thông báo swap2023](https://ftmo.com/en/blog/trading-updates/trading-update-16-feb-2023/)
nêu lãi suất/cổ tức làm rates thay đổi; không chứng nhận fixed−$2/ngàyUTC.

Nếu cần bước tiếp sauS01, đăng ký một geometry-only comparison commission1vs0,
giữ observed spread, stressslip1,5point/vòng, naturalSL và gates. Không chạy
PnL hoặc nói phí0 đã cứu retention. Swap không thuộc cost geometry gate nên
thay swap không giải quyết cửa này. Không giảm stress thiếu bằng chứng; mọi
numeric mới cần registration riêng trước outcome.

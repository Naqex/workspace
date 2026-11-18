# Chiến dịch độc lập: hệ thống trading tự động cho một owner

Owner giao thực thi và mở rộng phạm vi ngày 15/11/2026. Mục tiêu là có ứng
viên đủ điều kiện Challenge và hệ thống vận hành riêng, tiến tới funded/payout.
Không đạt mục tiêu chỉ bằng code, CI, báo cáo hoặc số backtest tăng lên.

Ngày 17/11/2026 owner xác nhận lại: **tiếp tục độc lập, phạm vi rộng**.
Goal cũ đã xóa; goal mới bao gồm alpha, portfolio, kiểm định, kiến trúc,
engines, môi trường AI và vận hành cho một người. Có thể mở rộng phương pháp
và tối ưu tiếp khi có bằng chứng cần thiết; các quyền broker, chi phí ngoài,
holdout và bảo vệ nhánh gốc bên dưới vẫn riêng biệt. Không phụ thuộc việc
thread gốc có tiếp tục hay không.

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
| Q1 | Source/path confirmation | Correction v2 `SOURCE_RECONCILED`; giữ original admission `SOURCE_REVIEW_REQUIRED` | 25.537.048 ticks/3.576 giờ; không H1 mismatch/held gap sau correction hai giờ; cùng vendor, chưa FTMO parity |
| Q2 | Alpha, portfolio, time-fit | S01 economics-v2/oracle v3 PASS; S02 shared replay PASS correctness nhưng `INCONCLUSIVE_PATH` | 108 accounts, 733 trades; candidate Net/DD tốt hơn baseline, DD tuyệt đối tăng; XAUUSD gaps; chưa Challenge |
| Q3 | Robustness/validation | S03 đã release nguồn2024; GBPraw138/1.632heldhours, đangsourceadmission | Conditional validation giữ unknownpath,104reported/108sentinels, exactDevprefix; chưafinancialS03/cleanOOS |
| S5 | Bind chiến lược với engine/runtime | Chưa đủ candidate qualified | Same decision semantics, units/account/risk, no duplicate, exact artifact/code lineage |
| D0 | Bàn giao vận hành cho owner | Chưa đủ | Runnable own setup, stop/recover/rollback, runbook và cách hiểu risk/results; quyền broker riêng |

Goal hiện active theo xác nhận của owner ngày 17/11. Kết quả âm/inconclusive
là kết quả nghiên cứu, không phải lý do tự tuyên bố mục tiêu lợi nhuận hoàn tất.
Sau từng đợt finite, cập nhật bằng chứng và quyết định tiếp dựa trên thông tin
mới; không quét hoặc sửa tham số vô hạn chỉ để có PnL dương.

## Nền đã có và giới hạn

V3 có A gốc + EURUSD satellite, 15/36 mốc qua P1, chỉ 2/36 qua cả hai vòng
ở ASYM và chung một funded path, payout0. Đây là baseline đã exposed, không
qualification mới của chiến dịch này. Khoảng trống nguồn GBP của checkpoint V3
đã được S01 xử lý: source-v2 và economics-v2 có đối soát độc lập trên tick;
S02 đã ghép ba tài sản vào cùng account. Cả hai vẫn dùng nguồn cùng vendor,
không chứng minh execution FTMO hay edge ngoài mẫu.

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

Checkpoint delivery ngày 15/11: Trader
[PR32](https://github.com/Naqex/trader/pull/32), head `621f0e0b`, có review độc
lập và 5/5 CI đạt; chưa có bằng chứng merge/deploy trong chiến dịch này.
Workspace [PR84](https://github.com/Naqex/workspace/pull/84) là draft; direct
branch `7f9dd4c` có 3/3 CI đạt, run `43634922641`. Hội nhập main còn conflict
CI/index ở checkpoint đó; phải refresh trước tích hợp, không gọi trạng thái
GitHub lịch sử là hiện hành. Ngày 17/11 hai checkout vẫn sạch trước khi tiếp.
Không đổi producer giữa run. Attachment từng chạm giới hạn 100 identities;
giữ checkout và đường dẫn hiện có, không tạo checkout thay thế.

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

## Source checkpoint và seam tiếp theo

Original S01 proof giữ nguyên failed H1 reconciliation; hai backend cùngvendor
candle/tick khác nhau tại18/10/2022 12:00 và15:00UTC. Independent integer decode
tái hiện đúng mỗi nguồn. Source-only generator comparison với2H1hours lấy từ
tick giữ nguyên300events và naturalSL. Bốn GET kiểm lại đềuHTTP202bodyrỗng,
khôngadmit/retry. Xem [discrepancy protocol](SOLO-GBP-SOURCE-DISCREPANCY-20261115.md).
V2 chỉ được tạo sau correctionproducer/protocol/tests/review; oldproof không
sửa thànhPASS, không hạ tolerance hoặc bỏ4mismatches khỏioriginalbook.

Seam shared-account đã triển khai tại `6f6c2f8`: reuse `PortfolioAccount`, giữ
hai-asset defaults, thêm assets/risk tường minh và timestamp/age từng asset.
Ba stream merge theo `(timestamp,asset_rank,source_ordinal)`, nên EUR ở giữa
Gold→EUR→GBP vẫn giữ đúng ordering. Fixtures kiểm two-asset parity, tied ticks,
missing/stale quotes, cap/reserve/halt, DST/funding, phase/reward và cash bridges.
S02 independent oracle kiểm108accounts,1.219.429fieldchecks và46.082coveragechecks.
Đây là correctness của mô hình đã khai báo; margin/news/broker feed vẫn thiếu.

Ngày17/11, independent economics oracle bắt false reject đúng15% tại
BUY19/06/2023. [Repair](SOLO-GBP-COST-GATE-CORRECTION-20261117.md) đã chạy
v2 và review độc lập PASS đúng300raw/287fills/13rejects, tiền150/75 và sáu
GBPcurves. Lệnh thêm là−1,0834R, kết quảv2 giảm đúng, v1 giữ nguyên.
[Báo cáo S01](SOLO-GBP-CONFIRMATION-RESULTS-20261117.md) ghi giới hạn và
concentration; chưa thể gọi M1 additive là account PnL.
[S02 results](SOLO-THREE-ASSET-REPLAY-RESULTS-20261118.md) ghi runner
`INCONCLUSIVE_PATH` sau independent oracle PASS đúng scope: candidate có
Net/DD tốt hơn baseline ở hai cost models nhưng XAUUSD có khoảng thiếu báo giá,
DD tuyệt đối tăng và không monthly account nào hoàn tất cả hai phase. Giữ
2024 đóng cho tới calendar/path protocol mới; không gắn verdict này với
Challenge readiness.

Audit lịch nguồn18/11 đã kiểm148 khoảng duy nhất: median toàn gap60,0326 phút,
phần unknown sau15 phút là45,0326 phút; tất cả khớp17:00–18:00 New York theo DST.
Chưa có lịch Dukascopy lịch sử đủ để miễn trừ; không suy từ mẫu giờ thành proof.
Continuous candidate unknown1,924739%, baseline2,178177%. Bằng chứng và đường
đọc tiếp ở [S02 results](SOLO-THREE-ASSET-REPLAY-RESULTS-20261118.md).

Nguồn công khai18/11 xác nhận lịch Dukascopy hiện tại trùng17–18NY; chưa có
hiệu lực2022–2023 nên giữ unknown. Lifecycle audit cho thấy tất cảP1candidate
trong10/2023; P2còn68–88ngày, bestending+644/+854USD và7windows mỗi model âm.
Không chỉ thiếu dữ liệu; độ đều/tốc độ lãi còn yếu dù354–374lệnh/năm.
Lát tiếp [S03 conditional Historical Validation2024](SOLO-THREE-ASSET-VALIDATION-PROTOCOL-20261118.md)
đã khóa thiết kế, giữ nguyên composition/risk, tiếp lifecycle2022–2023, kiểm
prefix và internalstateparity; không mở giá trước protocol/code/reviewfreeze.
Runtime seam chỉ khảo sát offline: consumer
hiện tại chưa hỗ trợ portfolio tick/Prop, không gắn nhãn đã có bot từ S02.

Checkpoint18/11: S03 implementation `5ccdc6d`, independentpre-release41file;
source13/harness27/downloader20syntheticsPASS, engine28 và oracle34 riêng.
Sourcerelease2024 vàGBPregistration đã tạo saucommit/review; chi tiết trong
[S03 results](SOLO-THREE-ASSET-VALIDATION-RESULTS-20261118.md). Codepolicy và
thứ tự nguồn→proof→financial giữ nguyên. CI head`bc79b9a`3/3PASS sau xử lý
đúng1secret-scanfalsepositive; chưamergePR84 hoặcrolloutTrader.

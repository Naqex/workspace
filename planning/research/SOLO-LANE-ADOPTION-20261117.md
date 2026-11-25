# Tiếp nhận cải tiến từ xingchiapi-astra

Ngày chốt đối chiếu: 18/11/2026 (tiếp nhận đợt V24 ngày 17/11). **Đã sửa cổng phí chính xác và tuổi báo giá trong
nhánh V24. Chưa nhận chiến lược GBPUSD hoặc thay engine tài khoản.**
Đây là cải tiến correctness cho công cụ hiện tại, không phải một trial tìm alpha.

## Nguồn và quyết định tích hợp

Chat nguồn: `01a1daf7-cb89-7b83-ad62-cb0be1b35cdc`.
Trader nguồn: `~/.codex/worktrees/04e2/trader`,
`codex/solo-system-research`, SHA `621f0e0bbf7dcfde00ff546b343acd4189eb95dd`.
Workspace nguồn: `~/.codex/worktrees/solo-prop-system/TradingWorkspace`,
`codex/solo-prop-system`, SHA `6f6c2f850f55d3a8ad802e3b27459a4aa27a3688`.
SHA Workspace này còn local, cao hơn head PR84 `b1ba9a8` một commit.

Đích: `D:/ANNAM/TradingWorkspace`, nhánh `codex/pareto-mt5-and-bot-lab-v24`,
baseline `0704f885ad77365792998c0940e386e36c2a70ac`, [PR103](https://github.com/Naqex/workspace/pull/103).
Trader gitlink vẫn là `930fa76882e741702620f626986bb38755368635`.
Không merge toàn nhánh nguồn vì base cũ có cả thay đổi không liên quan và
formatting Rust; không sửa worktree, DB, port, job hoặc PR của lane nguồn.

| Thành phần ở nguồn | Đánh giá tại đích | Hành động |
|---|---|---|
| Exact cost gate, commit `9ca78a6fafa1e52ee2b6f4f243349c80cb910f01` | Đích vẫn chia float tại cổng 12%/15%, tái hiện được false reject | Tiếp nhận cách so sánh chính xác, điều chỉnh cho mô hình phí native hiện có |
| Quote timestamp từng tài sản, commit `6f6c2f8` | Shadow đã có stale guard, nhưng tuổi vị thế khác dùng giờ nhận giá | Chuyển guard sang `source_msc`; không chép toàn engine ba tài sản |
| API worktree isolation, commit `7241a8b0` | Launcher đích chưa có root/DB/port/manifest admission này | Giữ đường tích hợp product qua [Trader PR32](https://github.com/Naqex/trader/pull/32); chưa port/deploy trong patch workspace |
| Windows long paths + ChangeTime/USN, commit `a60db1e5` | Đích đã có ChangeTime nhưng chưa có đầy đủ USN/read-sharing/long-path changes | Cũng thuộc PR32, cần kiểm tại lớp artifact/product; chưa đổi scanner hoặc xóa scan gaps lịch sử |
| GBPUSD S01 source correction + independent oracle | Có hồ sơ tốt, sửa đúng hai H1 và giữ nguyên 300 tín hiệu | Giữ evidence tham khảo; chưa thêm candidate vào BASE_GUARD |
| Shared-account replay S02, commit `6f6c2f8` | Đã chạy xong nhưng verdict `INCONCLUSIVE_PATH`; khác baseline/risk của V24 | Chưa thay engine hoặc dùng kết quả để promote |

PR32 vẫn OPEN, 5/5 CI xanh tại `621f0e0b`; PR84 vẫn DRAFT/OPEN.
Đây là trạng thái đã kiểm ngày trên, không là quyền merge hay runtime acceptance.
Terminal isolation của connector V24 khác API/DB worktree isolation của PR32.

## Hai hành vi đã sửa và luồng dữ liệu

**Cổng phí:** `quant_core/cost_gates.py` so sánh `100 × cost > percent × stop`
bằng phân số chính xác. Với Gate1, dùng giá trị thập phân đã khai báo, thay phép
chia float; đúng 12% và 25% được xử lý theo ranh giới cũ, không thêm epsilon.
Với ShadowPaper, Bid/Ask integer → spread + commission từng chân + stress market
slippage → phí theo quote units → so với khoảng SL integer tại ngưỡng 15%.
Commission Gold vẫn làm tròn 0,0001 USD/oz mỗi chân; FX vẫn 9 USD/lot/vòng
ngoài paired spread. Đây là round-trip tức thời ở entry, không có funding.

Ca cụ thể: EURUSD BUY bid `1,28175`, ask `1,28184`, SL `1,28064`:
SL 12 pip, phí 1,8 pip = đúng 15%; nay được nhận. SL ngắn hơn một quote unit
vẫn bị loại. Không dùng một khoảng dung sai để cho lệnh vượt cap đi qua.

**Tuổi báo giá:** khi giữ XAUUSD rồi xét lệnh EURUSD, tuổi giá XAUUSD được tính
từ thời điểm giá phát sinh, không từ lúc nhận lại. Đúng 120.000 ms vẫn theo
ngưỡng hiện có; 120.001 ms bị chặn kể cả arrival clock còn chưa quá hạn.
Luồng còn lại dùng known-at clock để khớp paper, không backdate execution.

Không đổi tín hiệu/SL/TP/risk/weights, model phí hay accounting kernel lịch sử.
Cổng nhận lệnh có thể đổi membership ở đúng ranh giới; chưa chạy lại backtest
và không sửa kết quả cũ để ngầm áp correction này. Nếu consumer sau dùng code
mới, phải bind cả `cost_gates.py` vào producer pins của run mới.

## Điều đáng học từ nghiên cứu bên kia

S01 GBPUSD đã đối soát 25.537.048 tick / 3.576 giờ và 300 raw signals;
exact gate nhận 287 lệnh, loại 13. Ở risk 150 USD/lệnh, 2022 đạt +5,1173R,
2023 +24,3873R. Nhưng bỏ ba lệnh tốt nhất năm 2022 thì còn −11,5454R;
raw DAY markout vẫn âm cả hai năm. Đây là inherited-recipe exception,
không phải ứng viên mới qua Stage-0 hay OOS sạch.
Nguồn chi tiết: `planning/research/SOLO-GBP-CONFIRMATION-RESULTS-20261117.md`
trong workspace nguồn; oracle v3 đã PASS trong phạm vi S01, thay kết luận
oracle cũ chưa chạy được. Không mở rộng PASS sang Gold/EUR/shared account.

S02 attempt-1 **đã hoàn tất phép tính**, không còn ở trạng thái chờ chạy:
733 inherited trades / 108 sổ, Development 2022–2023. Dưới SYM_FLAT,
A+EUR thu +3.100,95 USD / equity DD 3.683,59 USD; thêm GBP thu +5.322,60 USD
/ DD 4.225,99 USD. Mức rủi ro cố định lần lượt Gold/EUR/GBP = 150/75/75 USD;
thêm tài sản cũng thêm risk budget, không coi lợi nhuận tăng là cải thiện miễn phí.
11/24 monthly starts qua P1, 0 qua P2; các start chồng lấn, không phải xác suất.
Result vẫn `INCONCLUSIVE_PATH`, `DATA_PATH_INCOMPLETE`, `prop_qualified=false`,
independent result review PENDING. Vì vậy chưa lấy số đẹp để thay BASE_GUARD.

Đọc result/report từ
`E:/BACKUP-TRADINGWORKSPACE/solo-system-20261115-04e2/research/S02-three-asset-replay/attempt-1/`.
Không chạy lại job, đọc raw quote hoặc mở dữ liệu 2024–2026 trong lượt tiếp nhận.

## Kiểm chứng và giới hạn

Ba regression mới được chạy trước sửa: cả ba FAIL đúng nguyên nhân dự kiến
(12% equality, 15% equality, source age). Sau sửa, focused suite **49 PASS/0 skip**,
gồm oracle Decimal cho commission, BUY/SELL Gold và stop sát hai phía ngưỡng.
Full suite **1.340 PASS/0 skip**, giữ đủ 1.335 test IDs cũ và thêm 5 IDs.
Wall time 18,635 giây / 6 workers là correctness run, không chứng minh speedup;
mục tiêu tốc độ V24 vẫn chưa đạt, không retry để chọn lần nhanh.

Commands, source hashes và receipts ở private job
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/execution-v1/cross-lane-adoption-20261117/`.
So sánh với `pareto-mt5-bot-lab-v24-20261117/tests-release-verified.json`:
không thiếu test ID. Có source/test review tại lane hiện tại; không gọi đó là
independent review. Không cần skill/framework/config AI mới cho hai sửa lỗi này.

Patch tiếp tục trên PR103, chưa merge. Hai worktree nguồn sạch, VI Dubber WIP
được giữ, không đổi gitlink, không broker call hoặc restart runtime.
Ưu tiên reuse tiếp theo là tích hợp product PR32 trong phạm vi Trader;
GBP/S02 chỉ tiến tiếp sau khi giải quyết path gaps và kiểm định độc lập tương ứng.

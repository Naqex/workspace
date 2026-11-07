# UTC range nguyên bản — kiểm độ bền lịch sử 2024

Owner giao07/11 thực hiện liên tiếp các task nghiên cứu/kiểm định đã đề xuất.
Lát này giữ nguyên ứng viên UTC còn inconclusive sau [period study](PERIOD-RESULTS-20261106.md),
không chọn hoặc sửa nó theo kết quả discovery đợt3đang chạy. Chỉ nghiên cứu
offline;2024có prior exposure unverified theo owner, nên **historical robustness,
không clean OOS/final holdout**.2025+giữ đóng. Không OrderCheck/OrderSend/model.

## Thiết kế khóa trước giá/outcome mới

| Phần | Cấu hình |
|---|---|
| Hypothesis | Bộ quy tắc UTC range nguyên gốc có tiếp tục tạo net dương sau chi phí ở năm lịch tiếp theo, hay outcome cũ phụ thuộc hẹp vào thời kỳ? |
| Candidate | `eurusd-h4-utc-range00-08-atr14-r025-v1` giữ nguyên entry/range/day latch, initial2ATR14SL, exit20UTC/next valid, không TP/filter mới |
| Warmup |01/11–31/12/2023, causal, ít nhất81H4hợp lệ, không PnL |
| Evaluation |01/01–31/12/2024, end exclusive01/01/2025; snapshot3/6/12tháng lồng nhau |
| Selection / holdout | Dữ liệu2022/2023đã dùng lựa chọn;2024là bài historical validation mới trong project, external exposure unknown;2025+không mở. Không gọi chữ validation là chứng nhận OOS |
| Account / risk | Initial10kUSD, planned25USD/lệnh,1position, internal daily100/overall500; account reset đầu sample |
| Reference / stress | Giữ2,50USD/lot/side; chuẩnslip0/financebuy9,3,sell−0,31; caoslippage0,00002/side,buy/sell20;22UTCweekday,Wed×3 |
| Prop model | Reuse exact declared FTMO2-Step Swing10k snapshot06/11, counterfactual áp2024; không refresh hoặc giả account contract/historical fees đã verified |
| Clock / fills |UTCnến đóng; next observed Bid/Ask quote; dailyEurope/Prague/DST, native declared lifecycle/reset; gaps giữ nguyên, không force-close cuối mẫu |
| Primary | Net12tháng reference/stress cùng firstbreach/native phase/coverage; profits các phase reset lưu riêng, không cộng thành payout |
| Secondary |3/6tháng, quarterly contribution nếu cùng account, costs/holding/lot/count/DD/tail/open/pending/quote age |
| Limits |1numerical worker,6hceiling,8hbatch; preparation30phút riêng; không auto retry, chỉ reuse completed seals đúng binding |

Điều kiện dừng: material correctness/timing/data failure quarantine evidence
liên quan; firstbreach không đủ profile/config; no trades/coverage thiếu là
inconclusive. Net không dương ở một cost không promote bản trong bài; dương
cả hai và khôngbreach chỉ cho review thêm, chưa edge/firm certification. Chưa
target phải báo not-reached/censored, không tăng lot hoặc kéo dài sample tùy
kết quả. Không chọn lại chỉ các quý có lời hoặc tuning risk/TP sau outcome.

## Trước thực thi

Audit consumption metadata/availability không đọc giá trước freeze; pin protocol
bytes trước QDM export. Dùng cache hiện có, không download/update; hash/quality/
H4/tick-cache preparation một lần. Exact input/source/runtime/profile/decision
registration khóa sau export, trước numerical; whitelist digest tại owner hiện
có, không sửa old registration hoặc nới guard. Đợi discovery numerical writers
kết thúc trước thay shared registration reader; old evidence giữ source snapshot.

Preflight đúng pinned inputs/protocol/spec/profile/cost phải đạt, rồi finite
supervisor ghi progress/log/seals và tự report. Nếu reader/report lỗi thì giữ
numerical artifacts đã verified; không tự replay cả năm. Report/dossier không
tự cấp authority hoặc thêm data window. Live/broker strategy handoff vẫn là
scope/gate riêng sau G3/G4review, không thuộc phép kiểm này.

Exposure audit không tìm record không chứng minh unseen. Thực thi hoàn tất cũng
không là kết thúc pipeline nghiên cứu; giữ mọi trial và chuyển qualification
theo khungG0–G6. Đây là bài tách khỏi discovery3, không so parameter variants
trên2024và không dùng2024để chọn bản trong discovery rồi gọi nó validation sạch.

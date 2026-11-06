# Annual 2023 — kết quả và quyết định sau batch

Kiểm ngày06/11/2026. Mục tiêu: chọn bước nghiên cứu tiếp cho Forex tự động,
FTMO 2-Step Swing là chuẩn chính; chưa chọn cấu hình gửi lệnh hoặc mua challenge.
Scope/tiêu chí đã freeze ở [recovery registration](TIME-FIT-RECOVERY-20261106.json).
Đây là historical robustness, prior exposure chưa xác minh;2023 nay consumed.

## Kết quả đã xác nhận

Private evidence root:
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/prop-time-fit-20261106/execution-v2/`.
`pipeline.json` completed11:32:25VN; `batch-1/batch-terminal.json`
completed_verified5/5job lúc11:31:45VN.10scenario,30horizon rows;0model/broker
calls, holdout_read=false, không automatic retry. Cả ba stderr pipeline/batch/report
trống. Run source Trader `bbc7c60e`; không đánh đồng source mới sau run với source này.

Vốn mô phỏng10.000USD, research budget25USD/lệnh theo initial balance,
1vị thế, internal daily100/overall500USD. Equity gồm floating và phí; không ép
đóng tại cutoff. Mỗi ô **phí chuẩn / phí cao**, USD:

| Phiên bản | 3 tháng | 6 tháng | 12 tháng | Quyết định trong bài này |
|---|---:|---:|---:|---|
| Donchian | −139,05 / −166,95 | −258,67 / −328,03 | −306,11 / −488,47 | Không tiếp tục cấu hình này: fail annual cost-screen |
| SMA | −95,78 / −110,76 | −7,57 / −48,68 | +64,15 / −25,49 | Tạm gác: stress âm; chỉ15lệnh đóng/năm |
| Z-score | +80,08 / +61,08 | +191,59 / +147,76 | +275,74 / +179,77 | Inconclusive; giữ để nghiên cứu tiếp |
| Pullback | −27,85 / −51,09 | −48,97 / −105,39 | +1,40 / −132,51 | Tạm gác: stress âm; chuẩn còn floating20,40USD |
| UTC range | +41,61 / +28,48 | +63,31 / +41,02 | +223,74 / +186,96 | Inconclusive; giữ để nghiên cứu tiếp |

Quyết định theo annual screen đã đăng ký, không áp ngược điều kiện phải xanh
mọi quý. Ba horizon cùng start, không là ba sample độc lập. Không loại cả họ
strategy từ một version/risk/window; không đo được false-negative rate thật.
Số Q1có điều chỉnh cash-tail đã khai báo; raw/seal giữ nguyên. Annual10/10rows
không có delta cash-tail. Xem `horizon-report.json` và `.md` để phân biệt raw/derived.

| Chẩn đoán cả năm, phí cao | Z-score | UTC range |
|---|---:|---:|
| Net equity / initial | +1,7977% | +1,8696% |
| Lệnh đóng |102|199|
| Lệnh/tháng, trung bình mô tả |8,5|16,6|
| Win rate, toàn bộ lệnh đóng |53,9%|51,3%|
| Lãi/lỗ trung bình mỗi lệnh, sau phí |+1,76USD|+0,94USD|
| Profit factor |1,295|1,217|
| Realized average win / average loss |1,107|1,158|
| Chuỗi thua dài nhất |7|5|
| MaxDD **chỉ tại ledger events** |95,81USD|137,32USD|
| Top3lệnh / tổng lợi nhuận dương |15,0%|15,0%|
| Vị thế mở cuối mẫu |0|0|

Không có minimum win rate chung; realized win/loss không là planned TP/SL.
Risk25USD là budget dự kiến, không phải mỗi fill đều chịu đúng25USD thực tế.
Lợi nhuận mỏng ở assumptions này; chưa có cơ sở nhân lot hoặc ngoại suy thời
gian pass. Internal risk không trigger không chứng nhận full FTMO drawdown.

## Đã làm hậu kiểm và sửa gì

`audit_completed.py` → `post-batch-audit.json`: chạy41,49s, kiểm5dossier,
10scenario seals, tính lại30rows và đối chiếu Markdown/JSON. Report SHA256:
`2d1ff9d885f79c7a566955e4c509c16784f4d6f7fa0e173fcca188e78d26a118`.
13source files của run được copy và kiểm SHA vào `sealed-source-v2/` trước sửa;
đây là evidence snapshot, không là runtime checkout mới.

Chọn **lệnh đóng đầu tiên theo thời gian** của hai ứng viên × hai costs, không
chọn theo lời/lỗ. Đọc76.355raw prefix quotes, gom H1/H4 độc lập; tính lại ATR,
prior20z-score hoặc UTC range, decision, lot rounding, next quote, initial SL,
exit quote và net cash/financing.4/4trace đạt:

| Case | Signal/quantity | Net độc lập |
|---|---|---:|
| Z-score chuẩn | SELL0,04lot; z=2,16656 |+6,53USD|
| Z-score phí cao | SELL0,04lot |+5,56USD|
| UTC range chuẩn | SELL0,04lot; close1,06605 < range low1,06640 |−0,32USD|
| UTC range phí cao | SELL0,04lot |−0,48USD|

Warmup dùng candle cache đã inspect và hash-bound, không độc lập đọc lại toàn
bộ warmup. Signal/ATR/sizing/cash dùng công thức riêng; không gọi helper bị kiểm.
Trace này kiểm entry-rule và exit quote/order; **chưa độc lập replay đủ exit-rule**
hay toàn bộ trades. BUY/gap controls đã có ở `screening-proof.json` của cùng root.
Audit ban đầu giả slippage thay đổi fill, nên fail ở stress; source/ledger xác nhận
model ghi Bid/Askfill và tách slippage thành cash cost. Đã sửa đúng oracle,
giữ raw run nguyên vẹn. Đây là giới hạn realism cần đối chiếu broker về sau.

Raw runner đã sửa **calendar cash completeness** cho lượt tương lai: post phí
trước cutoff trong quote-free gap và cuối dataset; event đúng cutoff thuộc khoảng
kế tiếp. Không thêm quote/fill/candle/cursor hoặc ép đóng. Test tái hiện trước fix:
thiếu phí Friday4/5event và gồm nhầm event đúng cutoff. Sau fix:127tests Forex
đạt,7report tests đạt; có risk-halt giữ close_pending khi hết quote, no-anchor
fail-closed và giữ pending order. Test suite đầu chạy sai import root bị1import
error; command đúng từ product root đạt, không sửa test để né lỗi.

Source fix commit `977d9055`; commands/evidence ở `calendar-fix-validation.json`.
Đã kiểm lại5/5legacy dossiers đọc bằng `sealed-source-v2/` sau source change.
New runner yêu cầu historical registration mới có
`calendar_accounting=exclusive_event_clock_v1`; pin cả numerical CLI. Không sửa
registration đã freeze hoặc coi source mới đã annual-verified. Legacy artifacts
vẫn đọc được bằng source đã seal; không chạy lại annual chỉ để đổi report.

## Gói chứng cứ: đã chứng minh đến đâu?

| Cửa | Trạng thái/bằng chứng hiện có | Còn thiếu trước kết luận lớn hơn |
|---|---|---|
| G0 Thiết kế | Registration/source/data/cost/cutoffs frozen, giữ cả failed attempt | Không chứng minh prereg bằng hash riêng;2023không clean OOS |
| G1 Timing/code | Prefix parity10/10;4raw→signal→cash samples; BUY/SELL/gap fixtures; boundary regressions | Chưa audit độc lập mọi decision/exit và toàn engine |
| G2 Accounting/model |30rows recomputed;net closed/open financing khớp; raw/derived tách rõ | Historical broker cost/fill/spec chưa verified; slippage là cash model |
| G3 Edge | Hai bản dương annual ở cả hai costs; trial âm giữ nguyên | Một năm/một pair, sample/dependence/selection và fresh validation thiếu |
| G4 Prop fit | Có budgets nội bộ; candleUTC, risk resetPrague | Full tick DD, phase1→reset→phase2, breach/time-to-target và exception coverage chưa nối |
| G5 Vận hành strategy | Đã có system operations evidence riêng | Chưa forward hai strategy frozen hoặc đối soát actual broker fills |
| G6 Authority | Chỉ research offline | Không cấp quyền order/challenge từ report |

### Điều kiện cần về mục tiêu balance, không cần replay tick

`audit_balance_target.py` → `balance-target-diagnostic.json`: kiểm lại30sealed
observations,5synthetic controls (below, equal rồi hồi lại, above rồi hồi lại,
no-trade, nonfinite refusal). Giả định dùng mốc phase1**10% balance**
đã khai báo trong [terms snapshot](PROP-TERMS-SNAPSHOT-20261106.md), không refresh
hoặc chứng nhận contract tài khoản. Trên initial10.000USD, target là11.000USD.

| Phiên bản | Peak balance cả năm, chuẩn / cao, USD | Có chạm11.000 trên path này? |
|---|---:|---|
| Donchian |10.000,01 /10.000,00|Không|
| SMA |10.083,74 /10.000,00|Không|
| Z-score |10.340,31 /10.259,73|Không|
| Pullback |10.024,52 /10.000,00|Không|
| UTC range |10.223,74 /10.186,96|Không|

Đã xét mọi cash event trong ledger, gồm thời điểm trước debit/credit và derived
cash-tail; không chỉ nhìn ending balance.30/30horizons chưa chạm mục tiêu.
Đây là diagnostic **post-hoc trên đúng frozen internal-risk account path**:
chưa cần full phase2để biết path này không chạm target10%, nhưng không suy
full FTMO first-breach/phase compliance hoặc kết quả nếu thay risk/rules/fills.
Balance chạm target về sau cũng chỉ là điều kiện cần, chưa đủ pass. Giữ primary
cost-screen cũ; diagnostic không biến thành tiêu chí đã prereg hoặc power estimate.

## Thứ tự việc tiếp theo

Thực thi tiếp sau review: [study hai survivors](PROP-PATH-SURVIVORS-20261106.md)
đã bổ sung tick-risk/native lifecycle/exit controls và completed16:09VN sau
dispatch13:26VN.12sealed rows đối soát đạt, financial outputs/trade traces khớp
annual cũ cho hai survivors. Measured annual tickDD chuẩn/cao: Z-score90,80/
106,43USD;UTC range129,71/143,79USD. Không breach declared loss profile, nhưng
chưa đạt targetphase1ởmọicutoff. Không gọi lifecycle`running` là worker còn chạy.
Các mục dưới giữ lý do/thứ tự đã chọn; actual state theo receipt AI.
Risk/TP variants và fresh validation vẫn chưa chạy; chưa coi đây là OOS/edge proof.

1. **Nối phép đo account/prop trước batch đắt tiếp theo.** Reuse `prop_session.py`;
   nhận risk observations ở từng quote/cash event, đúng resetPrague/DST, equity
   gồm floating/cost. Giữ peak/trough/first breach/qualifying days và coverage.
   Oracle hữu hạn phải kiểm equity hồi lại trước bar close, phí/giờ reset trùng,
   gap/no quote, pending/flat, pass→reset→phase2 với capital/risk/financing mới.
   Không dựng phase2 bằng trừ target hoặc replay lại ledger với state đã sai.
2. **Risk sensitivity, một trục:** hai survivors,0,125% và0,25% của initial10k
   (12,50/25USD), giữ entry/SL/exit/costs/internal account limits. Đây là thiết kế
   tiếp theo, **chưa executable registration hoặc outcome mới**. Reuse consumed
   2023và cache hợp lệ; không mở2024/2025+. Baseline25USD ở source mới chỉ chạy
   lại phần cần chứng minh changed accounting; không reuse numerical cross-source
   bằng bỏ drift guard. So lot/min-lot, actual stop-risk, denied fills, full risk
   path và time-fit; không linear-scale PnL cũ, không chọn chỉ theo return cao nhất.
3. **Exit comparison sau risk review**, giữ một risk đã khóa; mỗi candidate
   original exit so với TP2R **overlay**: đặt TP tại fill±2×initial stop distance
   đã làm tròn tick; giữ SL và exit rule cũ, điều kiện hợp lệ đến trước thắng.
   R là gross fill→rounded initialSL price distance, khác netR sau phí. TP cần
   next-quote/gap/protective-order semantics; đổi holding thì replay cả account
   path. Candidate ID/version mới, không search risk×TP×SL×indicator/pair cùng lúc.
4. **Fresh validation/forward** chỉ sau freeze và consumption/gate review. Không
   gọi window unseen từ việc metadata trống; không tự mở holdout hoặc broker.

Đây là scope/acceptance cho lát tiếp, chưa claim đã làm xong risk/exit/prop batch.
Không mở thêm tối ưu GPU/Rust hoặc full-batch benchmark khi chưa chặn bước này.
Độ đúng/account path và kiểm robustness hiện có giá trị hơn thêm tốc độ đơn lẻ.

## Hậu kiểm kỹ thuật

| Lát | Đã đo | Quyết định |
|---|---|---|
| Chuẩn bị dùng chung |536,547s; source-bound reuse | Giữ; chưa có lý do đổi storage/cache |
| Numerical5worker |130,2–200,2phút/worker;47035,19CPU-seconds tổng | Nguồn chậm nằm ở numerical scenarios; không gọi quota AI |
| Toàn pipeline |Khoảng3giờ30phút, kể cả prep/report;5worker/6core | Có terminal/deadline; không gọi mức này là SLA |
| Reuse | Read-only audit41,49s; không replay27,5triệutick | Dùng sealed results cho report/decision; giữ source snapshot |
| ETA | Estimate09:51kết thúc10:40–11:15; actual11:32 | ETA cần tính validation/tail và worker chậm nhất; ticks%khác wall% |
| Correctness | Legacy golden cũng bỏ sót cash-tail | Thêm calendar oracle/regression, không dùng parity làm chứng nhận duy nhất |
| Recovery | Partial CLIresume vẫn chưa có | Scenario/job seal reuse có kiểm; không gọi numerical rerun là resume |

Không có baseline annual hoàn tất cùng workload trước fix nên **chưa đo annual
speedup**; không so53phút của một quý với cả năm như cùng bài. CPU-times là
từ worker receipts, không phải đo toàn máy hoặc RAM/GPU/foreground latency.

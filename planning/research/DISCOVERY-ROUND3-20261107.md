# Mở rộng nghiên cứu đợt 3 — protocol trước outcome, 07/11/2026

Owner giao triển khai liên tiếp screening, mở rộng hypothesis và vá lỗi có
bằng chứng. Scope này offline: dùng development đã consumed, không mở holdout,
không broker/model/paid provider. Kết quả/commands ở receipt AI hiện có.

## Danh mục và quyết định trước outcome mới

| Bộ luật / nhóm | Tình trạng | Lý do / dependency |
|---|---|---|
| Donchian20/10, trend | Đã thử, tạm gác version | Giữ kết quả âm, không nhân biến thể để cứu |
| SMA20/80, trend | Đã thử, tạm gác | Ít mẫu, financing nhạy; không đủ edge |
| Pullback20/80, trend | Đã thử, tạm gác | Price-PnL mỏng, financing; chưa tuning exit |
| Z-score20, reversion | Đã thử, tạm gác version | Fail period cost screen |
| UTC range breakout, session | Đã thử, còn inconclusive | Nhánh validation giữ nguyên, không winner |
| Failed20 breakout, level reversion | Chọn triển khai mới | Kiểm giả thuyết false break/rejection; không có order-book data |
| Compression6/24 breakout, volatility expansion | Chọn triển khai mới | So diễn biến sau range hẹp, vẫn cùng họ breakout/trend |
| UTC range fade, session reversion | Chọn triển khai mới | Kiểm rejection thay continuation, cùng clock/data với UTC breakout |
| Time-series momentum D1/monthly | Giữ research backlog | Cần long history/horizon/cost và contract D1; không biến12tháng thành12nếnH4 |
| Cross-sectional currency momentum | Giữ research backlog | Cần nhiều currency/universe/correlation/cost, EURUSD không đủ |

Tổng8bộ luật có thể chạy sau implementation,2research directions deferred;
không gọi10chiến lược implemented hoặc8nguồn edge độc lập. Ba bản mới là
quy tắc tự định nghĩa trước outcome, không paper replication hoặc khuyến nghị
gửi lệnh. Không mở pair/timeframe hoặc parameter grid cùng lúc.

Nguồn primary kiểm07/11:
[NY Fed Osler SR125](https://www.newyorkfed.org/research/staff_reports/sr125.html)
về clustering take-profit/stop-loss và reversal/continuation quanh levels;
[SR150](https://www.newyorkfed.org/research/staff_reports/sr150.html) về stop-loss
cascades. Chúng chỉ là cơ chế gợi ý: rolling extremes không phải levels/order
flow trong paper, không chứng minh ba công thức EURUSD/H4. Compression là
hypothesis riêng, chưa có primary evidence cho threshold6/24. [QuantConnect](https://www.quantconnect.com/docs/v2/cloud-platform/backtesting/research-guide)
hỗ trợ đặt hypothesis trước outcome/giữ OOS, không xác nhận strategy này.

## Quy tắc frozen trước khi đọc outcome mới

Tất cả EURUSD/H4UTC, nến đóng/mid từ observed BidAsk; initialSL2×WilderATR14,
không fixedTP; entry next quote, một vị thế, không reverse cùng event; 25USD
planned risk trên10k, internal daily100/overall500, cùng commission/slip/financing
reference/stress trước. Cần81warmupH4hợp lệ. Quy tắc đều đối xứngBUY/SELL.

| Candidate ID | Entry khi flat | Exit khi có position |
|---|---|---|
| `eurusd-h4-failed20-atr14-time6-r025-v1` | Dùng20nến trước; BUY nếu low nến mới < minimumlow trước và close mới > minimumlow; SELL nếu high mới > maximumhigh trước và close < maximumhigh. Nếu sweep cả hai biên cùng nến thì không entry | BUY thoát khi close >= midpoint của high/low20nến trước; SELL ngược lại; hoặc6nếnH4đã quan sát cùng positionID |
| `eurusd-h4-compression6-24-atr14-time6-r025-v1` | Dùng24nến trước; range6nến cuối <= một nửa range24 và range24>0; BUY close mới > high6, SELL close mới < low6 | BUY close < midpoint range6nến trước; SELL close > midpoint; hoặc6nếnH4cùng positionID |
| `eurusd-h4-utc-range-fade-atr14-r025-v1` | Phải đủH4bar00/04UTCngàyhiện tại; tại bar08/12UTC: BUY khi low mới < rangelow và close > rangelow; SELL khi high mới > rangehigh và close < rangehigh. Sweep cả hai biên bỏ qua; một emitted entry/ngày kể cả risk từ chối | H4close20UTC hoặc close hợp lệ đầu ngày kế khi thiếu bar; không bịa scheduled fill |

Strict inequalities đúng như bảng, equality không là crossing/rejection.
Held-bars gồm bar chứa fill; missing bars không đếm, position mới reset tuổi.
Prior levels không chứa signal bar; history/ATR/position/day latch roundtrip.

## Sàng lọc nhanh v1: feasibility trước, tick economics sau

Không viết simulatorOHLC thứ hai để giả fill/intrabarDD. Reuse quality/H4cache
đã hash-bound; chạy từng rule theo nến ở trạng thái **flat probe** để đo causal
entry opportunities, BUY/SELL, tick-grid/lot/stop-budget feasibility với costs
đăng ký. Đây không là actual executed signals, trade count/winrate/PnL/equity/
prop pass. Không ghép các hypothetical signals thành portfolio. State có day
latch riêng vẫn tiến đúng quy tắc; exit/position-path không được mô phỏng ở đây.

Reason hữu hạn: data/contract error→fail evidence; no entry→insufficient trong
window; no sizeable entry→needs lot/cost review; otherwise→eligible tick review.
Không loại cả họ từ probe, không coi probe winner. Ba bản mới và UTC comparator
đều được deep-check ở batch đầu **bất kể probe reason** để tránh chỉ kiểm survivors.
Đối chứng same-candle probes với causal H4 rebuilt từ consumed raw prefix, prefix
future mutation và BUY/SELL/equality/missing bar/ambiguous synthetic fixtures.
Đo source-bound cache read/probe vs full tick separately; không hứa speedup.

## Batch đầu hữu hạn

Warmup01–31/12/2021; evaluation03/01–31/03/2022, reuse exact existing raw hashes;
đã consumed/selection development, không OOS. Hai costs cũ; ngàyUTC/phanhPrague.
Không horizon profile nếu chưa đăng ký riêng; internal budget không là luật quỹ.
Chạy ba bản mới và UTC comparator bằng native batch,4workers tối đa,45phút/worker,
2giờ/batch ceilings, không ETA. Shared preparation một lần,30phút trần riêng;
source/pins/manifest mới, không overwrite accepted artifacts; không auto retry.

Correctness/timing/accounting lỗi→quarantine phần ảnh hưởng. Positive net cả hai
costs và đủ coverage chỉ cho review thêm; âm→không promote version trong bài;
zero trades/lot infeasible→inconclusive. Không yêu cầu xanh mọi quý hoặc minimum
winrate chung; không điều chỉnh criteria theo outcomes. Comparator không có
cross-source equivalence thì lưu drift và kiểm phần thay đổi, không bỏ guard.

Sau batch đọc tất cả4candidates×2costs, giữ trials/failures, cost/holding/sizing/
open/floating/DDcoverage. Lát sau chọn theo bất định/cơ chế, không auto thêm
threshold/TP/risk hoặc mở finalholdout. UTC validation tách riêng: cần audit
exposure/availability rồi exact protocol trước new-window outcome; chưa cấp
broker authority từ task nghiên cứu. Current source docs/tests có checkpoint
coherent; hạn chế source mutation khi numerical writer chạy.

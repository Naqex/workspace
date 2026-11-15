# V12 — đăng ký đường giá có SL và ensemble trước outcome

Task `eb7bd823-db6d-4304-90c6-64970b529ccc`. PR #90 merge `2175685`;
branch `codex/sl-active-ensemble-v12`, một PR mới dự kiến #91, không tự merge.
Giữ raw, frozen V1–V11, Trader pin và WIP VI Dubber. Không broker/provider trả
phí/Astra/runtime promotion. Không delegation trong lượt này.

## Câu hỏi và exposure

V11 là endpoint screen, không phải implementation lỗi vì thiếu SL. V12 được
owner cấp ngân sách mới để đo tác động của stop/exit. SL có thể cắt lỗ và cũng
có thể cắt các trade sau đó hồi phục; không đăng ký kết luận trước phép đo.
2024–2026 chưa đo F1–F4 trong V10/V11 nhưng đã có exposure các chiến dịch
trước, nên chỉ là reused historical validation. Cấm đọc giá 2024–2026 trước
gate Dev và commit danh sách/config; cutoff nếu được mở là 13/10/2026.

## Nguồn và tập thử cố định

Development 2018–2023, seed từ 01/11/2017; reuse matrices V10 reviewed và
V11 clock-corrected, source admissions/hash/proof tương ứng. Gold/EUR M1,
US500 M1, GBP/AUD native paired H1. Không tạo M1 từ H1. Track storage chỉ đọc
metadata archive/filename ngoài Dev; nguồn M1 mới chỉ nhận sau admission
schema/paired quotes/timeframe/full Dev/proof và đăng ký addendum trước numeric.
Không tải nguồn mới. Ask/cost/calendar proxy và gaps vẫn giữ nhãn conditional.

- Giữ nguyên 1.264 cells F1–F4, đo đúng P0 và P1: 2.528 path cells.
- F5: 5 tài sản × H1/H4 × N=3/5/10 ngày × 4 horizons = 120 cells.
  Đo P0/P1/P2: 360 path cells; tổng budget 2.888 path cells.
- P2 dùng duy nhất TP=3R, không thử 2,5R rồi chọn bản đẹp hơn.
- BOTH, không side search; không đổi stops/lookbacks/horizons cũ.
- Không chạy thêm subset/ordering/weights sau kết quả đầu.

F5 dùng N nến D1 hoàn thành gần nhất làm biên trên/dưới, biết tại thời điểm
quyết định H1/H4. Nến tín hiệu chọc ra ngoài một biên rồi đóng trở lại bên
trong; đóng nửa dưới/nửa trên của chính nến cho SELL/BUY tương ứng.
ADX Wilder14 trên chính timeframe tín hiệu, gồm nến vừa đóng, phải ≤25;
không thiếu giá trị warmup. SL tại râu nến quét cộng 0,1×ATR14 đã biết trước
nến tín hiệu. Hai chiều đồng thời thì bỏ, tối đa một event/ngày/recipe,
giữ calendar entry guard V11. Entry quote đầu tiên từ decision, trễ ≤60s.
Không thêm zone/bias/filter khác. F5 là hypothesis mới sau V11, không clean
discovery hoặc đảm bảo kiếm tiền trong năm đi ngang.

## Contract của kernel

Giá integer units, long đóng theo Bid, short đóng theo Ask. Natural stop giữ
nguyên; P0 không hard TP. Khớp SL tại open xấu hơn nếu gap qua SL, rồi cộng
market slippage stress riêng; không giả mọi lỗ bị khóa đúng −1R. TP là limit:
khớp đúng giá target, không negative exit slippage trong ASYM; SYM giữ full
stress làm đối chứng. Entry slippage là chi phí tách biệt, không đổi signals.
Commission/swap tính theo exit thực, không thời điểm horizon cũ.

P1: kích hoạt sau khi giá thuận chiều đủ để net liquidation, gồm spread,
commission, market slippage và swap đã tích lũy, đạt +1,5R. Mức bảo vệ là
giá cho net +0,15R tại lúc kích hoạt, có bù phí/swap khi đó; không cam kết
net +0,15R sau swap hoặc gap/slippage khác trong tương lai.
Trigger/protect dùng phí SYM bảo thủ cho cả hai cost views, không chọn
thời điểm bảo vệ theo scenario nào có lợi nhuận đẹp hơn.
Stop cũ được xét trước favorable excursion. Dời stop có hiệu lực từ bar kế
tiếp, không dùng thứ tự high/low chưa biết để giả fill trong chính bar kích
hoạt. Bar đồng thời chạm stop và TP luôn xét stop trước. Với H1 không biết
đường đi trong giờ: báo conservative bar model, không intrahour certification.

Horizon giữ DAY/24H/48H/FRIDAY và holiday clamp V11; US500 giữ correction
16:15–18:00 New York →16:00 cùng ngày. Hạn thiếu quote ≤60s là unknown,
không next-open/interpolate; stop xảy ra trước hạn có thể là exit đã biết.
Không dùng extrema của bar ở horizon (bar đó chưa hình thành tại hạn).

Đường giá thiếu trong giờ hoạt động trước exit làm path unknown, không suy
ra SL chưa chạm. Lịch đóng định kỳ đã biết được tách khỏi unexpected gaps;
ghi số phút/giờ thiếu và coverage, không ép mọi khoảng trống là đóng cửa.
Unknown không được tính như lệnh 0R hoặc vào ensemble; source-complete gate
không được cứu bằng bỏ các trade chưa biết.

Preflight timestamp trước numeric ghi source schedule theo New York:
FX nghỉ Fri 17:00–Sun 17:00; Gold Fri 17:00–Sun 18:00, ngày thường
17:00–18:00; US500 Fri 16:15–Sun 18:00, ngày thường 16:15–18:00. Đây là
source-calendar proxy, không live FTMO hours. Các phút hụt ngoài khung đó
vẫn unknown, kể cả thiếu một phút sát giờ nghỉ; không suy từ mức PnL.

## Phí, profile ngày và ghép tổ hợp

Reuse Gold/EUR stress V11; GBP/AUD EUR-like 9 USD/lot/vòng và −40 USD/lot
rollover với thứ Tư ×3; US500 Atlas 1 USD commission +1,5 point slippage/vòng,
funding −2 USD/lot/ngày lịch. SYM/ASYM FX/US500 vẫn proxy tương ứng, không
target-native specs. Không giảm phí để cứu kết quả. Chi phí/1R và admission
15% giữ entry natural scale cũ; ≥50% mỗi cụm, pooled scale ≤15%.

Component: raw và admitted net dương mỗi cụm, mean admitted ≥0,04R,
path/endpoint coverage đầy đủ cho claims tương ứng; không cadence gate riêng.
PnL ngày dùng thay đổi mark-to-market của từng trade, không gom tổng R vào
ngày entry. Phí ghi đúng lúc entry/exit/rollover. Daily correlation vẫn là
model estimate, không là chứng nhận độc lập thống kê.

Composer giữ graph/medoid V11, đổi threshold correlation cố định 0,25;
cùng asset/family nối khi corr≥0,25 hoặc overlap decisions≥50%. P0/P1/P2
cùng recipe là biến thể cùng cơ chế, không nhiều bets độc lập. Sort
asset/family/ID, cross-representative corr<0,25, tối đa 8; không profit sort.
Equal risk 1R/trade. Cần K=4–8, có ít nhất hai tài sản hoặc có cả F1–F4 và
F5; không ép chọn F5 nếu nó không qua cổng.

Shared composer thêm tham số threshold, default 0,30 giữ semantics V11;
V12 gọi explicit 0,25. Exact V11 source từ Git `2175685` được lưu/hash
trong private job, giữ registration lịch sử; không sửa frozen pins V11.

Ensemble: ≥60 admitted/year trung bình ở từng cụm; 120 là mục tiêu không
trần. ≥5/6 năm dương, net ex-best-year >0 cả SYM/ASYM, raw/admitted hai cụm
dương. Báo actual cash R-DD và MTM riêng. Account-wide replay chỉ sau gate
alpha: reference risk 150 USD/trade trên 50k, shared open-stop budget 800 USD,
lot grid/cost rounding; không risk/phase grid.

Nếu Dev fail: giữ đầy đủ so sánh V11/P0/P1, registry 42 nhánh, V11 6 nhánh
và top theo từng asset; cancel validation/lifecycle, không thêm biến thể cứu.
Nếu pass: commit config/source/calendar/cost/risk trước validation, chạy
2024–13/10/2026 và lifecycle adapter đã có; thiếu full source/path thì báo
DATA_PATH_INCOMPLETE, không fabricate 9-year performance.

## Auditor, storage và bàn giao

`independent_ledger_auditor.py` không import Quant Core/PnL/DD helper. Chỉ
nhận ledger, original-source quotes, cost/rule/calendar specs đã hash; tự tính
fill/stop witness, fees/swap, daily Prague balance anchor và static floor tới
cent. Ledger tối thiểu 8 fields không đủ tự suy phí/lot contract/phase:
spec/exit reason/protection decisions phải explicit, không lấy producer PnL
làm oracle. Kiểm fixtures độc lập + ledger Dev được chọn; account results chỉ
claim khi có actual continuous account. Cùng implementer vẫn không là
reviewer/contributor/feed độc lập.

Storage inventory D/E logical readable bytes; permission errors unknown.
Archive chỉ list member metadata trước gate, không đọc validation OHLC.
Duplicate candidates theo path/size chưa là redundant data; chỉ hash bytes
khi cần và báo bounded coverage. Không xóa raw/research, không nén WIP hoặc
archive có source pin đang dùng. Có thể chỉ lập danh sách, không mutation.

Correctness fixtures trước numeric; scalar independent audit sau run.
Benchmark cùng workload, cold/warm và IO/prep/kernel tách riêng; không hứa
vài giây nếu chưa đo. Giữ 1.048 old test IDs + tests mới, 0 skip; smoke <1s
là mục tiêu quan sát, không bỏ test để ép. Một PR, 3 CI đúng final HEAD,
private receipts và báo cáo 4 phần. Không tự merge PR #91.

# Đăng ký kiểm định Swing 10k/25k · 20/11/2026

Ba cơ chế được đăng ký trước khi xem PnL. Development A 2018–2020 và
B 2021–2024. D1 FTMO native 13 mã, H4 chỉ dùng tham chiếu ATR khi đo ký quỹ.
US500.cash chỉ D1 trong cả hai phép đo. Khóa từ 01/01/2025 giữ nguyên SHA
`f0a6b43cb205535b0a959456455dc1d857a0936c06c2e51b8614fd7d772a8486`.
Dùng lịch sử trước 2018 để warm-up. Dữ liệu 2025 trở đi vẫn bị khóa với mọi
tín hiệu, nhãn và replay. Báo giá live hiện tại dùng riêng cho audit spec.

| Nhánh | Tín hiệu khi D1 đã đóng | Stop và thoát |
|---|---|---|
| SWING_TREND_D1 | BUY/SELL khi close vượt high/low 20 D1 trước và nằm đúng phía SMA200 | 1 ATR(14) tại entry. Dời stop theo close ± 3 ATR(14) cuối đã đóng, chỉ siết một chiều. |
| SWING_CARRY_TREND_D1 | 11 FX. Chọn chiều có swap lớn hơn trên snapshot, gồm trường hợp cả hai âm. SMA50/SMA200 đồng hướng và close cắt SMA20 cùng chiều. Bỏ tie swap. | 1 ATR(14) tại entry. Dời stop theo close ± 3 ATR(14) cuối đã đóng, chỉ siết một chiều. |
| SWING_INDEX_DIP_D1 | US500.cash BUY, close trên SMA200, RSI(2) Wilder cắt xuống 10. Giữ điều kiện không mở lệnh thứ Sáu và phải có open kế tiếp đúng mốc của ASYM_A. | Stop 1 ATR(14). Thoát tại D1 open sau rebound qua SMA5 hoặc sau ba bar giữ. Bỏ riêng cutoff thứ Sáu ở Swing. |

So ghép cặp cùng intent, entry, lot và chi phí Swing. Cột Standard mô phỏng
riêng cutoff tại **D1 open thứ Sáu** cho đủ 13 mã. Mốc này giữ đối chiếu
ASYM_A và tránh dùng extrema của một bar chạy qua cutoff. Số đo chỉ áp
cho quy ước Friday open. Lệnh vào đúng mốc cutoff bị veto trong sổ
Standard và tách khỏi cặp định lượng price/swap delta. Không dùng margin
1:100 trong phép cô lập exit. Snapshot Standard giữ vai trò audit riêng.

Nến D1 được biết vào cuối bar trước khi dùng open mới. FX/trend vào ở
open kế tiếp, cho phép chuyển cuối tuần và gắn cờ khoảng cách entry bất
thường trên bốn ngày. Sổ dipped index giữ đúng yêu cầu open kế tiếp của
ASYM_A. Với path qua tuần, stop kiểm gap tại open trước khi thử extrema,
fill bất lợi tại open hoặc stop cộng stress. Bar D1 không có thứ tự
intrabar đáng tin. Đo MAE/MFE từ open, close và fill quan sát được trên mô
hình, bỏ high/low chưa biết thứ tự so với stop. Cuối 2024 đánh dấu vị thế
đang mở, định giá cuối 2024 và tách khỏi thống kê lệnh đóng.

Trước mỗi lệnh, nominal risk 0,50% vốn đầu, floor theo min/step/max; dùng stop
1 ATR cộng spread, commission, stress slippage để tính lot. Sổ portfolio
equal-risk dùng cùng risk cho từng cơ hội, một vị thế/mã. Nếu đụng mốc ưu
tiên Trend, Carry, Index và thứ tự mã cố định. Dùng tối đa 50% equity tại
lúc admit. Báo cả peak và ngưỡng 40%. Margin lịch sử quy đổi từ tỷ suất
ký quỹ native vừa đo, FX theo tiền ký quỹ, kim loại/chỉ số theo giá.
Book 25k là quy đổi cùng spec, không phải đo tài khoản 25k. Giá chuyển đổi
dùng FX D1 cùng mốc hợp lệ. Phí từ 36f1535: spread median London đã đo,
5 USD/lot FX round trip, 0,0007% notional mỗi phía vàng, US500 zero commission.
Stress mỗi phía 0,20 pip FX, 0,20 USD/oz vàng, 0,75 điểm US500. Hạch toán
swap điểm theo chiều và 3× theo snapshot Swing, qua các rollover thứ
Hai–Sáu trong thời gian giữ, gồm qua cuối tuần. Dùng snapshot hiện tại
làm proxy cho 2018–2024, chưa có lịch phí lịch sử.

Stage‑0 thô trước SL: +5 bar giao dịch cho Trend/Carry, D1 open sau entry
cho Index. Báo gross/ma sát/swap và net từng năm ở fixed risk lot liên tục.
Áp gate hiện hành net thô > phí vào–ra từng năm, median ma sát/stop ≤12%,
ít nhất 50% qua 12%. Sổ SL-active được owner yêu cầu là phép chẩn đoán
cố định, kể cả với Stage‑0 âm. Chọn nhánh khi net dương cả A/B dưới stress,
Stage‑0 qua, ≥5 R/năm, DD ≤20R, R bỏ top 2 dương và top 2 ≤50% pool thắng,
margin khả thi ở cả hai quy mô. Sổ ghép ba nhánh chẩn đoán dùng ≥15 R/năm
và cùng các gate. Chỉ nhận candidate để review bước kế. Không grid,
thử ngưỡng phụ, Monte Carlo hay lifecycle. Các ngưỡng nhãn lệnh thắng
được khóa độc lập trong [reference](../../.agents/skills/strategy-qualification/references/selective-win-diagnosis.md).

# Đăng ký ba cơ chế bất đối xứng sau `2df5b25`

Giữ mốc 2025-01-01 nguyên byte. Development A 2018–2020, B 2021–2024.
Chỉ đọc Parquet Development đã niêm phong, tape ledger trước và BASE_GUARD
tape Dev. Kết quả giải phẫu được phép dùng để chọn hướng trước khi đo.

| Cơ chế | Định nghĩa cố định | Markout thô chính | Thoát thực nghiệm |
|---|---|---|---|
| ASYM_A | US500.cash D1 duy nhất. BUY khi close trên SMA200, RSI(2) Wilder <10, chỉ tại lần cắt xuống 10. | D1 open kế sau entry, chặn Friday open. | SL 1 ATR(14) D1. Thoát ở D1 open sau close vượt SMA5, chậm nhất sau 3 bar giữ hoặc Friday open. |
| ASYM_B | USDJPY, EURJPY, EURUSD, GBPUSD. Trend từ SMA50/SMA200 của D1 cuối đã xong. Donchian20 H4 hoặc Donchian10 D1 theo chiều trend. ATR trước ở dưới median 20 ATR trước đó. | 24 giờ broker, chặn Friday 23:00 broker. | SL 1 ATR của khung tín hiệu. Thoát trên close xuyên đường giữa Donchian, hoặc Friday 23:00 broker. |
| ASYM_C | EURUSD, USDJPY, EURJPY, GBPUSD, XAUUSD. Breakout H4 qua 5 bar trước, true range ≥1,5× ATR H4 trước, close trong 20% ngoài theo chiều phá và cùng dấu EMA50 dốc theo D1. Chỉ intent đầu mỗi mã/ngày. | Exact H1 open tại 20:00 UTC cùng ngày, không SL/TP. | SL 1 ATR H4, hard-flat 20:00 UTC. Chỉ vào 08:00–15:00 UTC. Không bù giờ thiếu. |

Ở B, so đúng một đối chứng cùng luật bỏ filter swap. B chính chỉ giữ chiều
có phí swap 3× ≤5% ATR D1 theo giá, cho qua credit. Dùng snapshot `36f1535`
cho cả tỷ lệ và hạch toán. FX vào đúng hoặc tối đa một giờ sau quyết định.
Ưu tiên D1 trên H4 lúc cùng entry. C hướng tới 40–100 lệnh/năm chỉ là mốc
cadence, không chỉnh tham số để đuổi theo số lệnh. B/C dùng H1 cho SL path.

A chỉ dùng nến D1, kể cả entry/exit/SL/DD. Entry theo D1 open kế tiếp trên
ngày liền sau nến tín hiệu, không mở thứ Sáu. Nếu thiếu D1 open và phải xử
lý qua ngày chưa xác nhận, đánh dấu unresolved. Đóng Friday open để không
giả có giá H1 trước phiên đóng. Có thể biết sớm lịch lễ trong vận hành thật;
lát offline này không chứng nhận lịch ngoại lệ.

Chi phí theo contract trước: median London, 5 USD FX RT, US500 0, vàng
0,0007% mỗi phía; stress +0,20 pip/phía FX, +0,75 điểm US500, +0,20 USD/oz
vàng. Giữ cả Base-Real và Stress-Real. Mô hình swap 00:00 broker cho đêm
thứ Hai–Năm, hệ số 3 theo mã. C chuyển đổi 20:00 UTC với giả định giờ
server New York+7 giờ và ghi nhận swap đúng bằng 0. H1 có gap >2 giờ làm
path unresolved. Giá mở qua SL dùng mức mở cộng trượt; dùng Bid/Ask mô
phỏng. Giữ giả định 0,5% per-trade, lot floor 0,01, margin như `2df5b25`.

Stress là cổng quyết định. Một nhánh mã cần ≥5R/năm, tổ hợp cần ≥15R/năm.
Cả hai phải gross raw dương trên từng cụm, net SL-active dương hai cụm,
DD ≤20R, net bỏ top 2 dương, hai lệnh thắng nhất ≤50% tổng R dương. Áp
thêm Stage-0 hiện hành với net raw vượt ma sát từng năm, median phí/stop
≤12% và giữ ≥50%. Nếu hết nhánh hoặc tổng đóng góp nhánh qua cổng <10R/năm,
kích hoạt `KILL_SWITCH_TRIGGERED` và `OHLC_STANDARD_SEARCH_EXHAUSTED` trong
phạm vi cuộc tìm kiếm đã đăng ký. B không carry là đối chứng, không là một
họ thứ tư hoặc ứng viên thay thế. Không mở holdout theo kết quả của lượt.

Đo tương quan theo net R thực hiện ngày thoát UTC, điền 0 ngày làm việc
không có deal. Dùng giao 2018–2023 do V19 tape Dev dừng trước 2024.
Đối chiếu tape OLHC/PRIMARY/SYM risk 150 USD của các sleeve BASE_GUARD.
Proxy theo sổ tape, khác sổ lifecycle sau admission và mark-to-market.
Không chạy lại lifecycle để lấy chuỗi đối chứng. Báo hệ số theo cả ba họ
và mã riêng lẻ, cùng cỡ mẫu và ngày cùng có lệnh.

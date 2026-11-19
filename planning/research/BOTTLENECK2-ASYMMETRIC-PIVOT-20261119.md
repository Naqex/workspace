# Bottleneck 2 · Giải phẫu Mon–Fri và chốt hướng OHLC Standard

**KILL_SWITCH_TRIGGERED · OHLC_STANDARD_SEARCH_EXHAUSTED.** Cả ba cơ chế
đăng ký đều rớt cổng danh mục. Tách từng mã vẫn có **0 nhánh đủ chuẩn**
và tổng đóng góp đủ chuẩn là **0 R/năm**. USDJPY trong ASYM_B dương hai cụm
khi có stop và thoát cấu trúc, nhưng markout thô sau phí chỉ dương 3/7 năm
nên rớt Stage‑0. Quyết định dừng áp dụng cho cuộc tìm kiếm OHLC Standard
đã đăng ký. Hướng bàn giao cho owner là xét giả thuyết có dữ liệu đầu vào
liên thị trường, vĩ mô hoặc order-flow ở vòng nghiên cứu riêng.

Development A là 2018–2020, B là 2021–2024. Holdout từ 01/01/2025
giữ nguyên niêm phong. Nhánh mới của US500.cash dùng D1 duy nhất.
Kết quả chạy offline theo [protocol khóa trước](BOTTLENECK2-ASYMMETRIC-PIVOT-PROTOCOL-20261119.md)
(commit 4c06f76) và [audit phí FTMO Demo 10k](FTMO-DEMO-10K-STANDARD-FULL13-AND-EXECUTION-20261119.md)
(commit 36f1535).

## 1. Sổ cũ · phần lãi đến từ đâu?

Bảng dùng lệnh đã được nhận vào danh mục 10k Stress‑Real của commit 2df5b25.
Mỗi ô là **số lệnh · gross / phí vào–ra / swap có dấu / net**, theo R
(50 USD). Phí vào–ra gồm spread, commission và slippage. Ledger cũ lưu
key `20:30-UTC` cho chính sách thoát ở giá H1 **20:00 UTC**.
Hai chính sách làm thời gian chiếm vị thế khác nhau, nên cột Δ là **gross
Mon–Fri trừ gross đóng ngày trên cùng intent ghép cặp**. JSON có cả
đối soát theo cụm, swap và net ghép cặp cho từng dòng.

| Họ | Mã | Chiều | 20:00 UTC · n và R | Mon–Fri · n và R | Δ gross ghép cặp R |
| --- | --- | --- | ---: | ---: | ---: |
| BREAKOUT | US500.cash | BUY | 273 · +16,19 / +21,21 / 0,00 / −5,02 | 161 · +3,74 / +13,86 / −5,26 / −15,39 | +12,11 |
| BREAKOUT | US500.cash | SELL | 104 · −20,01 / +8,14 / 0,00 / −28,15 | 86 · −26,12 / +7,05 / −1,74 / −34,92 | −10,86 |
| BREAKOUT | EURUSD | BUY | 266 · −9,88 / +7,58 / 0,00 / −17,46 | 182 · −28,15 / +5,67 / −7,34 / −41,16 | −27,63 |
| BREAKOUT | EURUSD | SELL | 295 · −16,05 / +8,32 / 0,00 / −24,36 | 200 · −7,11 / +6,09 / +0,31 / −12,89 | −2,79 |
| BREAKOUT | USDJPY | BUY | 417 · +42,59 / +13,39 / 0,00 / +29,20 | 240 · +63,57 / +9,06 / +3,71 / +58,22 | +31,52 |
| BREAKOUT | USDJPY | SELL | 179 · +6,77 / +6,20 / 0,00 / +0,58 | 134 · +19,29 / +4,81 / −10,09 / +4,40 | +22,38 |
| BREAKOUT | EURJPY | BUY | 362 · +25,57 / +13,65 / 0,00 / +11,92 | 221 · +22,13 / +9,46 / +1,90 / +14,57 | −0,38 |
| BREAKOUT | EURJPY | SELL | 218 · −7,69 / +8,43 / 0,00 / −16,13 | 162 · −24,34 / +6,70 / −4,94 / −35,98 | −23,55 |
| BREAKOUT | GBPUSD | BUY | 324 · +12,51 / +11,03 / 0,00 / +1,47 | 211 · −27,50 / +7,93 / −3,57 / −39,00 | −21,82 |
| BREAKOUT | GBPUSD | SELL | 299 · −28,89 / +10,30 / 0,00 / −39,19 | 211 · −42,93 / +7,69 / −3,26 / −53,88 | −23,58 |
| BREAKOUT | XAUUSD | BUY | 179 · −15,90 / +13,03 / 0,00 / −28,92 | 143 · −16,00 / +10,47 / −10,81 / −37,28 | −1,86 |
| BREAKOUT | XAUUSD | SELL | 132 · −0,10 / +9,88 / 0,00 / −9,98 | 102 · −16,22 / +7,61 / −0,58 / −24,42 | −10,93 |
| PULLBACK | US500.cash | BUY | 135 · −4,77 / +14,73 / 0,00 / −19,51 | 130 · +3,30 / +14,16 / −3,27 / −14,13 | +8,96 |
| PULLBACK | US500.cash | SELL | 29 · +6,59 / +1,72 / 0,00 / +4,87 | 26 · +6,65 / +1,49 / −0,48 / +4,68 | +3,91 |
| PULLBACK | EURUSD | BUY | 119 · −3,86 / +3,96 / 0,00 / −7,82 | 109 · −21,54 / +3,65 / −3,83 / −29,02 | −15,87 |
| PULLBACK | EURUSD | SELL | 185 · −4,59 / +6,08 / 0,00 / −10,66 | 170 · −7,93 / +5,61 / +0,24 / −13,29 | −10,91 |
| PULLBACK | USDJPY | BUY | 175 · −17,59 / +7,30 / 0,00 / −24,90 | 163 · −14,41 / +6,72 / +1,98 / −19,16 | +2,27 |
| PULLBACK | USDJPY | SELL | 116 · −9,70 / +4,87 / 0,00 / −14,57 | 103 · −22,25 / +4,27 / −10,11 / −36,63 | −14,94 |
| PULLBACK | EURJPY | BUY | 176 · −5,23 / +8,19 / 0,00 / −13,42 | 157 · −6,71 / +7,25 / +1,27 / −12,69 | +0,67 |
| PULLBACK | EURJPY | SELL | 77 · −14,82 / +3,23 / 0,00 / −18,05 | 71 · −13,61 / +2,99 / −2,71 / −19,31 | +1,84 |
| PULLBACK | GBPUSD | BUY | 148 · −15,52 / +6,28 / 0,00 / −21,79 | 136 · −23,34 / +5,80 / −2,03 / −31,18 | −9,13 |
| PULLBACK | GBPUSD | SELL | 146 · −20,19 / +5,39 / 0,00 / −25,58 | 119 · −16,93 / +4,31 / −2,08 / −23,32 | −0,24 |
| PULLBACK | XAUUSD | BUY | 204 · −8,54 / +13,73 / 0,00 / −22,27 | 172 · −18,83 / +11,57 / −13,28 / −43,68 | −9,38 |
| PULLBACK | XAUUSD | SELL | 52 · +1,73 / +4,57 / 0,00 / −2,83 | 50 · −4,20 / +4,43 / −0,35 / −8,97 | −5,97 |
| SWEEP | US500.cash | BUY | 101 · −9,07 / +10,32 / 0,00 / −19,39 | 99 · −15,89 / +9,80 / −1,32 / −27,02 | −6,92 |
| SWEEP | US500.cash | SELL | 147 · −1,12 / +29,83 / 0,00 / −30,95 | 144 · −19,29 / +28,46 / −3,95 / −51,70 | −17,13 |
| SWEEP | EURUSD | BUY | 290 · +17,06 / +14,24 / 0,00 / +2,82 | 285 · +2,32 / +13,46 / −8,16 / −19,30 | −11,71 |
| SWEEP | EURUSD | SELL | 215 · +19,50 / +10,29 / 0,00 / +9,21 | 207 · +28,88 / +9,65 / +0,19 / +19,42 | +12,43 |
| SWEEP | USDJPY | BUY | 121 · +6,23 / +6,59 / 0,00 / −0,35 | 120 · −12,77 / +6,50 / +1,09 / −18,18 | −19,03 |
| SWEEP | USDJPY | SELL | 235 · −29,78 / +16,75 / 0,00 / −46,53 | 234 · −29,99 / +16,49 / −13,56 / −60,04 | −0,03 |
| SWEEP | EURJPY | BUY | 172 · +16,07 / +10,82 / 0,00 / +5,25 | 165 · +32,81 / +10,24 / +0,81 / +23,38 | +10,67 |
| SWEEP | EURJPY | SELL | 280 · −19,41 / +21,22 / 0,00 / −40,64 | 268 · −27,03 / +19,91 / −7,71 / −54,65 | −1,67 |
| SWEEP | GBPUSD | BUY | 215 · +15,82 / +12,93 / 0,00 / +2,89 | 210 · +20,03 / +12,36 / −2,07 / +5,60 | +2,63 |
| SWEEP | GBPUSD | SELL | 209 · −11,18 / +13,16 / 0,00 / −24,33 | 203 · −33,05 / +12,53 / −2,03 / −47,62 | −14,66 |
| SWEEP | XAUUSD | BUY | 163 · −22,91 / +14,83 / 0,00 / −37,74 | 162 · −21,57 / +13,82 / −8,79 / −44,18 | +1,67 |
| SWEEP | XAUUSD | SELL | 189 · +17,68 / +17,57 / 0,00 / +0,11 | 185 · +10,05 / +16,60 / −0,83 / −7,39 | −7,81 |

**USDJPY BREAKOUT.** BUY đem về **+58,22R** trong Mon–Fri, khoảng
93% tổng net của hai chiều. SELL chỉ còn **+4,40R** sau khi mất **10,09R**
swap. BUY Mon–Fri đổi từ −15,01R ở A sang +73,24R ở B. Đóng lúc 20:00 UTC,
BUY còn +29,20R và dương ở cả hai cụm trong sổ danh mục. SELL còn +0,58R
toàn kỳ, âm ở A. Sổ **standalone** USDJPY BREAKOUT Mon–Fri đem về
+8,95R/năm, với −0,07 ở A và +15,71 ở B. Khi đóng ngày, standalone này là
cặp mã × họ **duy nhất** dương cả hai cụm (+1,28 / +6,49 R/năm, toàn kỳ
+4,25 R/năm, swap bằng 0).

Giữ Mon–Fri trên cùng intent USDJPY BREAKOUT tạo chênh lệch sau đây.

| Chiều | Intent ghép | Δ gross R | Δ swap R | Δ net R |
| --- | ---: | ---: | ---: | ---: |
| BUY | 239 | +31,52 | +3,71 | +35,23 |
| SELL | 133 | +22,38 | −10,09 | +12,30 |
| Tổng | 372 | +53,91 | −6,38 | +47,52 |

Cả ba họ đều mất gross sau khi giữ lâu hơn. Các nhóm âm lớn nhất
được xếp theo chênh lệch trên cùng intent.

| Họ | Δ gross R | Δ swap R | Bốn nhóm kéo gross xuống nhiều nhất |
| --- | ---: | ---: | --- |
| BREAKOUT | −57,40 | −41,24 | EURUSD BUY −27,63R, GBPUSD SELL −23,58R, EURJPY SELL −23,55R, GBPUSD BUY −21,82R |
| PULLBACK | −48,78 | −34,38 | EURUSD BUY −15,87R, USDJPY SELL −14,94R, EURUSD SELL −10,91R, XAUUSD BUY −9,38R |
| SWEEP | −51,57 | −45,72 | USDJPY BUY −19,03R, US500.cash SELL −17,13R, GBPUSD SELL −14,66R, EURUSD BUY −11,71R |

## 2. Ba cơ chế đã đăng ký

- **ASYM_A.** US500.cash BUY khi trên SMA200 và RSI(2) cắt xuống 10.
  Vào ở open D1 kế tiếp, stop 1 ATR. Thoát khi có hồi qua SMA5, sau
  ba bar giữ hoặc tại open thứ Sáu, tùy mốc đến trước.
- **ASYM_B.** Breakout H4/D1 bám xu hướng D1 trên bốn cặp FX, có lọc
  nén biến động. Lọc chiều mà swap 3× vượt 5% ATR D1. Thoát theo stop,
  khi close xuyên trung điểm Donchian hoặc theo cutoff thứ Sáu. Chạy đúng
  một đối chứng bỏ lọc carry với các phần khác giữ nguyên.
- **ASYM_C.** Breakout H4 có nến mở rộng biên độ và đồng hướng độ dốc
  EMA50 D1. Vào trong 08:00–15:00 UTC, stop 1 ATR H4 và thoát 20:00 UTC
  trong ngày. Tối đa một intent/mã/ngày. Swap đo được bằng 0.

**Markout thô** đo biến động giá có hướng đến một mốc thời gian, trước
SL và thoát cấu trúc. A dùng D1 open sau entry, B dùng 24 giờ broker
có clamp thứ Sáu, C dùng 20:00 UTC. Các tổng dưới đây tính theo 10k
Stress‑Real và cùng convention R. Ở Stage‑0 dùng lot liên tục để đo
tín hiệu. Sổ SL-active làm tròn xuống 0,01 lot, dùng mức rủi ro danh
nghĩa 0,50%, xét margin và giới hạn một vị thế mỗi mã. Sổ 50k áp chính
quy tắc lot/margin trên vốn 50k, với 250 USD/R. Top 10 là tỷ trọng
trong tổng R dương của các lệnh thắng sau phí.

| Cơ chế | Gross thô R | Phí thô R | Swap thô R | Net thô R | Gross có SL R | Phí có SL R | Swap có SL R |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ASYM_A | +4,10 | +1,54 | −0,64 | +1,92 | +5,50 | +1,51 | −0,83 |
| ASYM_B | +28,79 | +64,47 | −9,41 | −45,10 | −7,50 | +29,13 | −4,52 |
| ASYM_B_NO_CARRY | +30,64 | +67,96 | −16,75 | −54,07 | −9,70 | +31,19 | −8,63 |
| ASYM_C | −23,23 | +31,24 | 0,00 | −54,47 | −22,56 | +30,03 | 0,00 |

| Cơ chế | Lệnh | Lệnh/năm | Winrate | R/lệnh | A R/năm | B R/năm | Dev R/năm | Max DD R | USD/năm 10k | USD/năm 50k | Top 10 | R bỏ Top 10 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ASYM_A | 34 | 4,9 | 58,8% | +0,093 | −0,06 | +0,83 | +0,45 | 2,78 | +22,56 | +114,12 | 81,8% | −8,08 |
| ASYM_B | 791 | 113,0 | 29,3% | −0,052 | −13,14 | −0,43 | −5,88 | 91,60 | −293,99 | −1 567,85 | 19,2% | −126,39 |
| ASYM_B_NO_CARRY | 836 | 119,4 | 29,2% | −0,059 | −15,12 | −1,04 | −7,08 | 101,83 | −353,75 | −1 878,95 | 18,3% | −134,76 |
| ASYM_C | 692 | 98,9 | 41,3% | −0,076 | +5,11 | −16,98 | −7,51 | 80,95 | −375,61 | −1 977,47 | 14,2% | −88,18 |

Carry giúp ASYM_B giảm khoản lỗ từ −7,08 xuống −5,88 R/năm. Phần swap
âm trên sổ SL-active giảm từ −8,63R xuống −4,52R và DD giảm khoảng 10,23R,
nhưng rổ FX vẫn âm ở cả hai cụm. ASYM_A có commission bằng 0 và DD nhỏ,
song toàn kỳ chỉ +0,45 R/năm trên 34 lệnh. ASYM_C đạt 98,9 lệnh/năm và
zero swap, nhưng thua ngay từ gross; cụm B kéo kết quả xuống −16,98 R/năm.

### Kết quả từng mã

| Cơ chế · mã | Lệnh | Gross thô R | Phí thô R | Swap thô R | Net thô R | Gross có SL R | Phí có SL R | Swap có SL R | A / B / Dev R/năm | DD R | Cổng rớt |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| ASYM_A · US500.cash | 34 | +4,10 | +1,54 | −0,64 | +1,92 | +5,50 | +1,51 | −0,83 | −0,06 / +0,83 / +0,45 | 2,78 | Net hai cụm, Stage‑0, R/năm, Top 2 |
| ASYM_B · EURUSD | 193 | −10,54 | +11,32 | −5,49 | −27,35 | −20,68 | +5,86 | −2,67 | −4,16 / −4,19 / −4,17 | 36,30 | Gross hai cụm, Net hai cụm, Stage‑0, R/năm, DD, Top 2 |
| ASYM_B · USDJPY | 166 | +81,06 | +15,95 | +3,44 | +68,55 | +64,92 | +6,21 | +2,12 | +1,07 / +14,40 / +8,69 | 15,51 | Stage‑0 |
| ASYM_B · EURJPY | 198 | +9,88 | +18,85 | −0,49 | −9,45 | −10,49 | +8,29 | −0,14 | −2,67 / −2,73 / −2,70 | 27,60 | Net hai cụm, Stage‑0, R/năm, DD, Top 2 |
| ASYM_B · GBPUSD | 234 | −51,61 | +18,35 | −6,89 | −76,85 | −41,25 | +8,77 | −3,83 | −7,39 / −7,92 / −7,69 | 71,21 | Gross hai cụm, Net hai cụm, Stage‑0, R/năm, DD, Top 2 |
| ASYM_B_NO_CARRY · EURUSD | 194 | −11,38 | +11,34 | −5,50 | −28,22 | −21,66 | +5,88 | −2,69 | −4,16 / −4,44 / −4,32 | 37,31 | Gross hai cụm, Net hai cụm, Stage‑0, R/năm, DD, Top 2 |
| ASYM_B_NO_CARRY · USDJPY | 205 | +82,82 | +19,10 | −3,66 | +60,06 | +63,86 | +7,97 | −1,84 | −0,71 / +14,05 / +7,72 | 22,74 | Net hai cụm, Stage‑0, DD |
| ASYM_B_NO_CARRY · EURJPY | 203 | +10,81 | +19,17 | −0,70 | −9,06 | −10,65 | +8,57 | −0,28 | −2,86 / −2,73 / −2,78 | 28,17 | Net hai cụm, Stage‑0, R/năm, DD, Top 2 |
| ASYM_B_NO_CARRY · GBPUSD | 234 | −51,61 | +18,35 | −6,89 | −76,85 | −41,25 | +8,77 | −3,83 | −7,39 / −7,92 / −7,69 | 71,21 | Gross hai cụm, Net hai cụm, Stage‑0, R/năm, DD, Top 2 |
| ASYM_C · EURUSD | 172 | −17,00 | +6,08 | 0,00 | −23,08 | −15,68 | +5,90 | 0,00 | −1,23 / −4,47 / −3,08 | 26,06 | Gross hai cụm, Net hai cụm, Stage‑0, R/năm, DD, Top 2 |
| ASYM_C · USDJPY | 122 | +6,33 | +4,99 | 0,00 | +1,34 | +13,83 | +4,89 | 0,00 | +3,93 / −0,71 / +1,28 | 11,29 | Gross hai cụm, Net hai cụm, Stage‑0, R/năm, Top 2 |
| ASYM_C · EURJPY | 133 | −13,75 | +6,43 | 0,00 | −20,18 | −11,54 | +6,24 | 0,00 | −1,54 / −3,29 / −2,54 | 21,19 | Gross hai cụm, Net hai cụm, Stage‑0, R/năm, DD, Top 2 |
| ASYM_C · GBPUSD | 189 | +9,51 | +7,69 | 0,00 | +1,82 | +5,86 | +7,53 | 0,00 | +3,94 / −3,38 / −0,24 | 19,54 | Gross hai cụm, Net hai cụm, Stage‑0, R/năm, Top 2 |
| ASYM_C · XAUUSD | 76 | −8,32 | +6,05 | 0,00 | −14,37 | −15,02 | +5,47 | 0,00 | 0,00 / −5,12 / −2,93 | 23,57 | Gross hai cụm, Net hai cụm, Stage‑0, R/năm, DD, Top 2 |

- **USDJPY trong ASYM_B** có 166 lệnh (+1,07 / +14,40 R/năm theo
  cụm, +8,69 R/năm toàn kỳ). Hai lệnh tốt nhất chiếm 15,0% tổng R dương.
  Bỏ hai lệnh này còn +38,21R, qua cổng tập trung đã khóa. Bỏ đến Top 10
  còn −10,48R, một tín hiệu phụ thuộc đuôi đáng theo dõi. Stage‑0 rớt vì
  markout sau phí chỉ dương 3/7 năm, trong đó 2019 không có mẫu markout
  được định giá. Nhánh USDJPY này vẫn ở trạng thái `REJECTED_AT_DEV`.
- **XAUUSD trong ASYM_C** có dữ liệu H4 cả hai cụm. Trong cụm A, 84 bar
  phiên qua ngưỡng xung lực nhưng 0 bar đồng thời phá mức 5 bar và có
  close ở 20% ngoài theo chiều phá. Do đó 0 lệnh ở cụm A nghĩa là thiếu
  mẫu theo luật đã khóa. 76 lệnh đủ điều kiện đều thuộc cụm B.

### Tương quan với BASE_GUARD

| Cơ chế | Pearson r | Ngày làm việc | Ngày cơ chế có PnL | Ngày hai bên cùng có PnL |
| --- | ---: | ---: | ---: | ---: |
| ASYM_A | −0,016 | 1565 | 27 | 8 |
| ASYM_B | −0,033 | 1565 | 447 | 113 |
| ASYM_B_NO_CARRY | −0,027 | 1565 | 469 | 115 |
| ASYM_C | +0,023 | 1565 | 420 | 89 |

Dùng ngày UTC ghi nhận PnL lệnh đã thoát, giai đoạn chung 2018–2023.
Ngày làm việc không có deal nhận 0. Tape BASE_GUARD OLHC/PRIMARY/SYM
có 340 lệnh fixed-risk, 322 ngày có PnL. Các hệ số gần 0 mô tả tape
này. Độ tin cậy cho kết hợp còn thấp do ít ngày trùng lệnh và do proxy
khác chuỗi floating equity sau admission trên tài khoản.

## 3. Phán quyết, giới hạn và đối soát

Cổng khóa yêu cầu gross thô và net có SL cùng dương ở hai cụm, Stage‑0
yêu cầu net thô cao hơn phí vào–ra ở từng năm, median ma sát/stop ≤12%
và giữ ≥50% tín hiệu,
DD ≤20R, net bỏ Top 2 dương và tỷ trọng Top 2 ≤50%. Mức đóng góp là
≥5R/năm cho nhánh đơn hoặc ≥15R/năm cho tổ hợp. Kết quả đưa vào vòng
kết hợp là **0 nhánh**. Ở phạm vi đã đăng ký, dừng thêm biến thể OHLC
và giữ quyết định hiện hành của BASE_GUARD.

DD trong báo cáo dựa trên các mốc equity được dựng từ bar D1 (A)
hoặc H1 (B/C). Bid/ask và trượt giá dùng mô hình dựa trên mẫu Demo,
còn swap dùng snapshot hiện tại áp về lịch sử. Giá khớp tick, trượt
quanh tin, lịch đóng sớm và phí lịch sử theo từng ngày vẫn bất định.
Đóng 20:00 UTC kiểm được swap bằng 0 trong C. Việc tuân thủ mọi kỳ
nghỉ >2 giờ và giới hạn giao dịch tin cần có lịch instrument và bằng
chứng giao dịch phù hợp. Quy tắc nghỉ >2 giờ áp dụng tài khoản funded
Standard, có ngoại lệ Challenge, Verification và Swing. [FTMO FAQ](https://ftmo.com/en/faq/can-i-hold-positions-overnight-or-over-the-weekend/).

Khi đối soát, phép tính bỏ Top 2 được sửa để chỉ trừ hai lệnh thắng
lớn nhất. Chạy lại cùng bộ luật đã đăng ký cho Parquet giống từng byte.
Ngoài chỉ số Top 2 và cổng tập trung liên quan, kết quả và phán quyết
giữ nguyên. Test hồi quy khóa phép tính. Kiểm tra trực tiếp 9.412 dòng
Parquet với 16 tổ hợp cơ chế × chế độ phí × sổ vốn: mốc quyết định/entry/exit,
khóa thời gian, khóa US500 D1, swap bằng 0 cho C, khóa lệnh duy nhất và
đẳng thức gross − phí + swap = net. Tổng lệnh và PnL khớp JSON theo
năm, cụm và toàn kỳ. Track 1 khớp lại attribution và delta ghép cặp ở sổ cha.

[JSON đối soát](BOTTLENECK2-ASYMMETRIC-PIVOT-20261119.json) · [SHA256 báo cáo và JSON](BOTTLENECK2-ASYMMETRIC-PIVOT-20261119.sha256) · [Niêm phong](NATIVE_FTMO_HOLDOUT_LOCK.json).
Private manifest nằm tại `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/bottleneck2-asymmetric-pivot-20261119/manifest.json`.
SHA256 manifest `be77daf84d9d73671e8423804e711f30d348917740b041c7968acc1d508ebf52`. Manifest giữ hash của FORENSICS.json, SCREEN.json và PIVOT_TRADES.parquet.
Tệp SHA256 dùng byte LF chuẩn trong Git cho báo cáo và JSON.

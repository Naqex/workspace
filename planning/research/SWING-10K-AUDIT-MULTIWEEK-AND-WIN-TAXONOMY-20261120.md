# FTMO Swing 10k/25k · audit ký quỹ, giữ xuyên tuần và chẩn đoán lệnh thắng

**0/3 nhánh Swing và 0 nhánh theo mã đủ chuẩn.** Rổ 10k mất **25,02 R/năm** khi giữ xuyên tuần và **10,07 R/năm** khi đóng ở D1 open thứ Sáu. Nhánh Standard đã đóng vẫn chỉ là đối chứng. Đề xuất chuyển việc kế tiếp sang **Bot Lab** để đọc log/đường vốn và phân biệt lỗi thực thi với tín hiệu yếu trước khi cấp ngân sách biến thể mới.

## 1. Audit MT5 chỉ đọc

Đã xác minh FTMO-Demo, USD, balance 10.000, leverage 1:30, account DEMO. Terminal MT5 cô lập tắt giao dịch tự động, chỉ gọi API thông tin, báo giá, tính margin và tính PnL giả định. OrderSend = 0. Cấu hình Swing nằm riêng trong thư mục ignored với ACL chỉ owner và SYSTEM như file Standard. Đã đối soát và dọn hai tiến trình con/cập nhật sinh lại sau lượt margin. Lượt export lịch sau cùng đã kết thúc sạch.

Bảng lấy margin 0,01 lot lớn hơn giữa BUY/SELL. Spread là trung vị, FX tính pip, kim loại/chỉ số theo đơn vị giá. Mẫu Swing 468 quote native trong 30 giây và mẫu Standard London tại 36f1535 thu ở cửa sổ khác. Sai lệch spread phản ánh hai mẫu quan sát. Commission dựa trên sổ deal Standard 36f1535 trong phép mô phỏng.

| Mã | Contract / min / step / stops ở Swing | Swap L/S (Standard → Swing) | 3× | Margin 0,01 lot STD → SW (USD) | Spread p50 STD → SW (n Swing) | Phiên T6 Swing, giờ server |
| --- | --- | --- | --- | --- | --- | --- |
| EURUSD | 100 000 / 0,01 / 0,01 / 0 | −8,47 / 0,29 → −9,21 / 0,28 | 3 → 3 | 11,01 → 36,57 | 0,10 → 0,10 (30) | 00:05–23:55 |
| GBPUSD | 100 000 / 0,01 / 0,01 / 0 | −4,58 / −5,33 → −4,52 / −5,42 | 3 → 3 | 13,17 → 43,66 | 0,70 → 0,75 (24) | 00:05–23:55 |
| AUDUSD | 100 000 / 0,01 / 0,01 / 0 | −2,45 / −7,05 → −2,20 / −7,08 | 3 → 3 | 6,71 → 22,16 | 0,40 → 0,50 (25) | 00:05–23:55 |
| USDJPY | 100 000 / 0,01 / 0,01 / 0 | 2,64 / −19,33 → 2,61 / −17,60 | 3 → 3 | 10,00 → 33,33 | 0,30 → 0,30 (35) | 00:05–23:55 |
| USDCHF | 100 000 / 0,01 / 0,01 / 0 | 1,95 / −13,52 → 1,91 / −13,33 | 3 → 3 | 10,00 → 33,33 | 0,50 → 0,40 (16) | 00:05–23:55 |
| USDCAD | 100 000 / 0,01 / 0,01 / 0 | 0,71 / −10,82 → 0,77 / −11,02 | 3 → 3 | 10,00 → 33,33 | 0,40 → 0,40 (21) | 00:05–23:55 |
| NZDUSD | 100 000 / 0,01 / 0,01 / 0 | −4,80 / 0,00 → −4,68 / −0,13 | 3 → 3 | 5,53 → 18,28 | 0,60 → 0,50 (27) | 00:05–23:55 |
| EURGBP | 100 000 / 0,01 / 0,01 / 0 | −6,80 / 0,15 → −7,43 / 0,19 | 3 → 3 | 11,01 → 36,57 | 0,50 → 0,60 (16) | 00:05–23:55 |
| EURJPY | 100 000 / 0,01 / 0,01 / 0 | 2,11 / −11,15 → 1,24 / −10,11 | 3 → 3 | 11,01 → 36,57 | 0,90 → 1,00 (36) | 00:05–23:55 |
| GBPJPY | 100 000 / 0,01 / 0,01 / 0 | 5,87 / −25,15 → 3,50 / −25,07 | 3 → 3 | 13,17 → 43,66 | 2,40 → 2,50 (50) | 00:05–23:55 |
| AUDJPY | 100 000 / 0,01 / 0,01 / 0 | 3,77 / −15,25 → 2,81 / −13,92 | 3 → 3 | 6,71 → 22,16 | 1,00 → 1,20 (46) | 00:05–23:55 |
| XAUUSD | 100 / 0,01 / 0,01 / 0 | −56,56 / −4,20 → −56,28 / −4,20 | 3 → 3 | 74,71 → 235,05 | 0,35 → 0,44 (93) | 01:05–23:50 |
| US500.cash | 1 / 0,01 / 0,01 / 0 | −87,25 / −88,78 → −138,03 / −36,37 | 5 → 5 | 1,48 → 4,77 | 0,60 → 0,60 (49) | 01:05–23:50 |

Contract size, min/step lot, stops level, tick size và swap mode trùng ở 13/13 mã. Ngày swap 3× cũng trùng, thứ Tư (3) ở FX/vàng và thứ Sáu (5) ở US500.cash. Swap points hai chiều thay đổi giữa hai snapshot.
MT5 export quote/trade sessions đủ 13 mã. Audit Standard 36f1535 thiếu export weekly theo tài khoản nên parity phiên ở trạng thái **chưa xác minh**. Lịch Swing quan sát là lịch thường kỳ, chưa có lịch đóng sớm lịch sử. [FTMO Symbols](https://ftmo.com/en/symbols/).

FTMO Swing 1:30 dành cho 2-Step và cho phép giữ qua cuối tuần cũng như giao dịch tin theo điều khoản sản phẩm. Mốc Friday open bên dưới là đối chứng chính sách, sớm hơn giờ đóng phiên của funded Standard. [FTMO Swing](https://ftmo.com/en/faq/what-is-the-swing-account-type-and-how-does-it-work/) · [FTMO 2-Step](https://ftmo.com/en/2-step-challenge/).

### Lot và sức chứa tại 40%–50% equity

Dùng median ATR(14) Development, stop 1 ATR cộng ma sát stress, floor theo lot thật. Các cặp số lot/margin dưới đây lấy trường hợp BUY/SELL cần margin lớn hơn. 25k dùng cùng spec quan sát để quy đổi vốn. US500.cash không dùng H4.

| Mã | 10k D1 lot / USD | 10k H4 lot / USD | 25k D1 lot / USD | 25k H4 lot / USD |
| --- | --- | --- | --- | --- |
| EURUSD | 0,06 / 219,45 | 0,17 / 621,76 | 0,16 / 585,19 | 0,43 / 1 572,70 |
| GBPUSD | 0,04 / 174,62 | 0,13 / 567,52 | 0,12 / 523,87 | 0,32 / 1 396,98 |
| AUDUSD | 0,07 / 155,14 | 0,19 / 421,10 | 0,19 / 421,10 | 0,47 / 1 041,68 |
| USDJPY | 0,10 / 333,33 | 0,25 / 833,33 | 0,26 / 866,67 | 0,63 / 2 100,00 |
| USDCHF | 0,06 / 200,00 | 0,16 / 533,33 | 0,17 / 566,67 | 0,42 / 1 400,00 |
| USDCAD | 0,08 / 266,67 | 0,21 / 700,00 | 0,21 / 700,00 | 0,54 / 1 800,00 |
| NZDUSD | 0,08 / 146,26 | 0,19 / 347,36 | 0,20 / 365,65 | 0,49 / 895,83 |
| EURGBP | 0,07 / 256,02 | 0,18 / 658,34 | 0,17 / 621,76 | 0,45 / 1 645,85 |
| EURJPY | 0,07 / 256,02 | 0,18 / 658,34 | 0,18 / 658,34 | 0,47 / 1 718,99 |
| GBPJPY | 0,05 / 218,28 | 0,14 / 611,18 | 0,14 / 611,18 | 0,35 / 1 527,95 |
| AUDJPY | 0,09 / 199,47 | 0,23 / 509,76 | 0,23 / 509,76 | 0,58 / 1 285,47 |
| XAUUSD | 0,02 / 470,10 | 0,05 / 1 175,24 | 0,05 / 1 175,24 | 0,12 / 2 820,58 |
| US500.cash | 0,93 / 443,29 | — | 2,33 / 1 110,61 | — |

Số vị thế dưới đây giả sử mỗi mã có tối đa một vị thế ở cỡ đại diện. “Chọn mã nhẹ” là tối đa nếu ưu tiên các mã ít margin. “Bất kỳ mã” dùng tổng nhóm margin nặng nhất để cho giới hạn bảo thủ tại cùng snapshot. Đây là sức chứa theo ký quỹ. 13 vị thế × 0,50% vẫn có tới 6,50% rủi ro stop danh nghĩa trước gap và tương quan. Lot thực tế và equity thay đổi theo thời điểm.

| Sổ | ATR | Trần margin | Tối đa chọn mã nhẹ | Số mã bất kỳ |
| --- | --- | --- | --- | --- |
| 10000 | D1 | 40,0% | 13/13 | 13/13 |
| 10000 | D1 | 50,0% | 13/13 | 13/13 |
| 10000 | H4 | 40,0% | 7/12 | 4/12 |
| 10000 | H4 | 50,0% | 9/12 | 6/12 |
| 25000 | D1 | 40,0% | 13/13 | 13/13 |
| 25000 | D1 | 50,0% | 13/13 | 13/13 |
| 25000 | H4 | 40,0% | 7/12 | 4/12 |
| 25000 | H4 | 50,0% | 9/12 | 6/12 |

## 2. Sàng lọc Swing Development

[Protocol đã khóa](SWING-10K-MULTIWEEK-PROTOCOL-20261120.md) ghi đúng ba cơ chế. Cụm A 2018–2020 và B 2021–2024. Mỗi dòng dùng lệnh đóng, số liệu DD gồm đường equity nội mô hình. R sổ 10k = 50 USD và 25k = 125 USD. Vị thế còn mở giữ mark riêng. Range bar D1 không đủ thứ tự intrabar để xác nhận stop/tick DD hay tuân thủ Daily Loss. Giờ đầu D1 là nhãn broker, còn fill dùng giá open ghi trong bar. Phiên thực tế bắt đầu sau nhãn đó ở nhiều mã.

| Nhánh | Sổ | Cụm | Lệnh/năm | Gross R | Phí R | Swap R | Net R/năm | DD R | Net/DD | USD/năm | Peak margin USD / % | Peak vị thế |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SWING_TREND_D1 | 10000 | A | 102,7 | 10,41 | 6,80 | −65,55 | −20,65 | 90,77 | −0,68 | −1 032,38 | 2 789,05 / 36,3% | 13 |
| SWING_TREND_D1 | 10000 | B | 95,0 | −56,86 | 7,22 | −40,77 | −26,21 | 114,46 | −0,92 | −1 310,63 | 2 533,64 / 30,7% | 13 |
| SWING_TREND_D1 | 10000 | ALL | 98,3 | −46,45 | 14,02 | −106,32 | −23,83 | 180,00 | −0,93 | −1 191,38 | 2 789,05 / 53,1% | 13 |
| SWING_TREND_D1 | 25000 | A | 102,7 | 10,75 | 7,15 | −68,86 | −21,76 | 93,74 | −0,70 | −2 719,43 | 7 356,13 / 38,6% | 13 |
| SWING_TREND_D1 | 25000 | B | 85,0 | −63,45 | 6,78 | −37,27 | −26,87 | 119,78 | −0,90 | −3 359,34 | 5 669,80 / 28,6% | 13 |
| SWING_TREND_D1 | 25000 | ALL | 92,6 | −52,70 | 13,93 | −106,13 | −24,68 | 189,40 | −0,91 | −3 085,09 | 7 356,13 / 53,3% | 13 |
| SWING_CARRY_TREND_D1 | 10000 | A | 54,3 | −53,00 | 2,84 | 1,86 | −18,00 | 75,25 | −0,72 | −899,76 | 1 537,77 / 19,1% | 7 |
| SWING_CARRY_TREND_D1 | 10000 | B | 67,5 | 16,90 | 5,15 | 4,23 | 4,00 | 29,36 | 0,54 | 199,78 | 2 358,02 / 22,1% | 10 |
| SWING_CARRY_TREND_D1 | 10000 | ALL | 61,9 | −36,10 | 7,99 | 6,09 | −5,43 | 78,53 | −0,48 | −271,45 | 2 358,02 / 31,4% | 10 |
| SWING_CARRY_TREND_D1 | 25000 | A | 54,3 | −56,97 | 3,01 | 1,90 | −19,36 | 80,70 | −0,72 | −2 419,67 | 3 978,84 / 20,0% | 7 |
| SWING_CARRY_TREND_D1 | 25000 | B | 67,5 | 16,94 | 5,37 | 4,44 | 4,00 | 31,04 | 0,52 | 500,22 | 6 060,04 / 22,9% | 10 |
| SWING_CARRY_TREND_D1 | 25000 | ALL | 61,9 | −40,03 | 8,38 | 6,35 | −6,01 | 83,78 | −0,50 | −751,16 | 6 060,04 / 33,6% | 10 |
| SWING_INDEX_DIP_D1 | 10000 | A | 4,0 | −0,29 | 0,64 | −1,02 | −0,65 | 3,18 | −0,61 | −32,41 | 417,35 / 4,2% | 1 |
| SWING_INDEX_DIP_D1 | 10000 | B | 5,5 | 1,31 | 0,88 | −1,46 | −0,26 | 4,48 | −0,23 | −12,89 | 368,37 / 3,7% | 1 |
| SWING_INDEX_DIP_D1 | 10000 | ALL | 4,9 | 1,01 | 1,51 | −2,47 | −0,43 | 4,96 | −0,60 | −21,26 | 417,35 / 4,2% | 1 |
| SWING_INDEX_DIP_D1 | 25000 | A | 4,0 | −0,29 | 0,64 | −1,02 | −0,65 | 3,19 | −0,61 | −81,02 | 1 042,34 / 4,2% | 1 |
| SWING_INDEX_DIP_D1 | 25000 | B | 5,5 | 1,34 | 0,88 | −1,46 | −0,25 | 4,49 | −0,22 | −31,34 | 922,74 / 3,7% | 1 |
| SWING_INDEX_DIP_D1 | 25000 | ALL | 4,9 | 1,05 | 1,52 | −2,48 | −0,42 | 4,95 | −0,59 | −52,63 | 1 042,34 / 4,2% | 1 |
| EQUAL_RISK | 10000 | A | 134,3 | −8,03 | 8,68 | −64,23 | −26,98 | 123,68 | −0,65 | −1 349,04 | 3 233,45 / 49,7% | 13 |
| EQUAL_RISK | 10000 | B | 109,0 | −54,76 | 8,24 | −31,20 | −23,55 | 107,26 | −0,88 | −1 177,54 | 2 927,45 / 27,7% | 13 |
| EQUAL_RISK | 10000 | ALL | 119,9 | −62,79 | 16,92 | −95,43 | −25,02 | 189,86 | −0,92 | −1 251,04 | 3 233,45 / 57,4% | 13 |
| EQUAL_RISK | 25000 | A | 134,3 | −12,23 | 9,12 | −67,63 | −29,66 | 133,28 | −0,67 | −3 707,29 | 8 571,43 / 49,8% | 13 |
| EQUAL_RISK | 25000 | B | 102,2 | −43,95 | 8,07 | −31,50 | −20,88 | 94,89 | −0,88 | −2 609,93 | 6 902,07 / 26,5% | 13 |
| EQUAL_RISK | 25000 | ALL | 116,0 | −56,17 | 17,19 | −99,13 | −24,64 | 186,23 | −0,93 | −3 080,22 | 8 571,43 / 56,4% | 13 |

Chi tiết theo **mã × nhánh**, D1/10k Swing. JSON giữ cả các cohort 25k, sổ Friday và các funnel.

| Nhánh · Mã | Lệnh/năm | Gross / phí / swap toàn Dev (R) | A / B / Dev (R/năm) | DD R | Stage‑0 |
| --- | --- | --- | --- | --- | --- |
| SWING_CARRY_TREND_D1 · AUDJPY | 4,0 | 1,32/0,58/1,89 | 1,83 / −0,71 / 0,38 | 10,19 | Rớt |
| SWING_CARRY_TREND_D1 · AUDUSD | 3,6 | −11,52/0,44/−1,13 | −0,76 / −2,70 / −1,87 | 18,49 | Rớt |
| SWING_CARRY_TREND_D1 · EURGBP | 7,9 | −32,07/1,44/0,28 | −2,98 / −6,07 / −4,75 | 38,19 | Rớt |
| SWING_CARRY_TREND_D1 · EURJPY | 6,3 | −4,11/0,67/0,83 | −4,05 / 2,05 / −0,56 | 14,69 | Rớt |
| SWING_CARRY_TREND_D1 · EURUSD | 6,3 | −2,87/0,56/0,34 | −1,91 / 0,66 / −0,44 | 11,72 | Rớt |
| SWING_CARRY_TREND_D1 · GBPJPY | 7,1 | 1,28/1,00/1,84 | −2,14 / 2,13 / 0,30 | 14,32 | Rớt |
| SWING_CARRY_TREND_D1 · GBPUSD | 6,3 | −12,28/0,65/−2,63 | −2,88 / −1,73 / −2,22 | 19,31 | Rớt |
| SWING_CARRY_TREND_D1 · NZDUSD | 5,7 | −1,53/0,92/−0,12 | −2,09 / 0,93 / −0,37 | 16,69 | Rớt |
| SWING_CARRY_TREND_D1 · USDCAD | 5,9 | −2,72/0,66/0,83 | −1,58 / 0,55 / −0,36 | 12,36 | Rớt |
| SWING_CARRY_TREND_D1 · USDCHF | 3,9 | 0,64/0,54/1,76 | −0,49 / 0,83 / 0,26 | 6,28 | Rớt |
| SWING_CARRY_TREND_D1 · USDJPY | 5,0 | 27,76/0,54/2,20 | −0,94 / 8,06 / 4,20 | 9,71 | Rớt |
| SWING_INDEX_DIP_D1 · US500.cash | 4,9 | 1,01/1,51/−2,47 | −0,65 / −0,26 / −0,43 | 4,96 | Rớt |
| SWING_TREND_D1 · AUDJPY | 7,3 | 2,26/1,17/−4,47 | 1,47 / −1,95 / −0,48 | 13,72 | Rớt |
| SWING_TREND_D1 · AUDUSD | 8,1 | −17,34/1,11/−8,45 | 0,76 / −7,29 / −3,84 | 32,84 | Rớt |
| SWING_TREND_D1 · EURGBP | 7,6 | −19,61/1,25/−5,07 | −2,59 / −4,54 / −3,70 | 26,84 | Rớt |
| SWING_TREND_D1 · EURJPY | 9,1 | −23,24/1,13/−2,68 | −4,88 / −3,10 / −3,86 | 29,41 | Rớt |
| SWING_TREND_D1 · EURUSD | 7,7 | −16,93/0,72/−5,63 | −0,53 / −5,42 / −3,32 | 27,40 | Rớt |
| SWING_TREND_D1 · GBPJPY | 7,7 | −0,31/1,08/−4,46 | −2,93 / 0,73 / −0,84 | 11,79 | Rớt |
| SWING_TREND_D1 · GBPUSD | 8,6 | −7,25/0,83/−4,54 | −1,95 / −1,70 / −1,80 | 24,33 | Rớt |
| SWING_TREND_D1 · NZDUSD | 8,4 | −8,94/1,34/−3,67 | 0,71 / −4,02 / −1,99 | 19,48 | Rớt |
| SWING_TREND_D1 · US500.cash | 6,7 | 12,91/1,71/−27,72 | −4,17 / −1,00 / −2,36 | 30,24 | Rớt |
| SWING_TREND_D1 · USDCAD | 9,0 | −20,06/1,10/−5,26 | −2,18 / −4,98 / −3,78 | 29,88 | Rớt |
| SWING_TREND_D1 · USDCHF | 9,0 | −14,93/1,26/−9,99 | −3,24 / −4,11 / −3,74 | 32,52 | Rớt |
| SWING_TREND_D1 · USDJPY | 7,7 | 14,13/0,83/−7,16 | −5,31 / 5,52 / 0,88 | 25,37 | Rớt |
| SWING_TREND_D1 · XAUUSD | 6,9 | 30,15/1,41/−19,73 | 4,18 / −0,88 / 1,29 | 15,87 | Rớt |

**XAUUSD D1 standalone** (10000: 48 entry, 0 lượt bị loại do min lot · 25000: 48 entry, 0 lượt bị loại do min lot). Sức chứa ở snapshot và min lot lịch sử được đo riêng.

### Cùng tín hiệu, đo riêng ảnh hưởng của đóng thứ Sáu

Mỗi cặp có cùng intent, entry, risk và lot. Delta = Swing trừ Friday open. Bảng cộng delta theo intent giải quyết được, gồm những intent có thể chồng lấn. Chênh lệch giữa các sổ thực tế còn chịu các slot bị chiếm bởi lệnh giữ lâu và các lệnh bị veto đầu thứ Sáu. Đối chứng cùng phí và margin Swing để cô lập lịch thoát.

| Nhánh | Sổ | Cụm | Net Swing / Friday R/năm | Cặp | Δ gross R | Δ swap R | Δ net R |
| --- | --- | --- | --- | --- | --- | --- | --- |
| SWING_TREND_D1 | 10000 | A | −20,65 / −6,95 | 759 | −105,79 | −146,84 | −252,63 |
| SWING_TREND_D1 | 10000 | B | −26,21 / −8,42 | 1159 | −332,73 | −89,73 | −422,45 |
| SWING_TREND_D1 | 10000 | ALL | −23,83 / −7,79 | 1918 | −438,52 | −236,57 | −675,08 |
| SWING_TREND_D1 | 25000 | A | −21,76 / −7,29 | 759 | −104,36 | −154,20 | −258,57 |
| SWING_TREND_D1 | 25000 | B | −26,87 / −9,45 | 1159 | −358,46 | −93,92 | −452,38 |
| SWING_TREND_D1 | 25000 | ALL | −24,68 / −8,53 | 1918 | −462,83 | −248,13 | −710,95 |
| SWING_CARRY_TREND_D1 | 10000 | A | −18,00 / −3,00 | 187 | −62,54 | 0,80 | −61,74 |
| SWING_CARRY_TREND_D1 | 10000 | B | 4,00 / −1,66 | 359 | −18,25 | 4,55 | −13,69 |
| SWING_CARRY_TREND_D1 | 10000 | ALL | −5,43 / −2,23 | 546 | −80,79 | 5,36 | −75,43 |
| SWING_CARRY_TREND_D1 | 25000 | A | −19,36 / −3,09 | 187 | −64,92 | 0,71 | −64,22 |
| SWING_CARRY_TREND_D1 | 25000 | B | 4,00 / −1,83 | 359 | −20,46 | 4,78 | −15,68 |
| SWING_CARRY_TREND_D1 | 25000 | ALL | −6,01 / −2,37 | 546 | −85,38 | 5,48 | −79,89 |
| SWING_INDEX_DIP_D1 | 10000 | A | −0,65 / −0,12 | 12 | −1,10 | −0,48 | −1,58 |
| SWING_INDEX_DIP_D1 | 10000 | B | −0,26 / 0,76 | 23 | −3,39 | −0,69 | −4,08 |
| SWING_INDEX_DIP_D1 | 10000 | ALL | −0,43 / 0,38 | 35 | −4,49 | −1,17 | −5,65 |
| SWING_INDEX_DIP_D1 | 25000 | A | −0,65 / −0,12 | 12 | −1,10 | −0,48 | −1,58 |
| SWING_INDEX_DIP_D1 | 25000 | B | −0,25 / 0,77 | 23 | −3,40 | −0,69 | −4,08 |
| SWING_INDEX_DIP_D1 | 25000 | ALL | −0,42 / 0,39 | 35 | −4,50 | −1,17 | −5,66 |
| EQUAL_RISK | 10000 | A | −26,98 / −10,42 | 958 | −169,43 | −146,52 | −315,95 |
| EQUAL_RISK | 10000 | B | −23,55 / −9,81 | 1541 | −354,37 | −85,86 | −440,21 |
| EQUAL_RISK | 10000 | ALL | −25,02 / −10,07 | 2499 | −523,79 | −232,38 | −756,16 |
| EQUAL_RISK | 25000 | A | −29,66 / −10,83 | 958 | −170,39 | −153,98 | −324,37 |
| EQUAL_RISK | 25000 | B | −20,88 / −11,09 | 1541 | −382,32 | −89,84 | −472,14 |
| EQUAL_RISK | 25000 | ALL | −24,64 / −10,98 | 2499 | −552,70 | −243,81 | −796,50 |

Riêng dip US500, sổ Friday mới đạt +0,38R/năm tại 10k và dùng spec Swing mới. Mốc +0,45R/năm của ASYM_A thuộc audit Standard cũ. Trong cặp cùng spec mới, bỏ cutoff làm mất 5,65R tổng qua 35 intent (−4,49R giá và −1,17R swap). Tổng swing carry có swap dương trên cặp 10k nhưng giảm gross nhiều hơn. Tín hiệu carry dùng snapshot hiện thời để hồi chiếu và được đánh dấu thiếu dấu carry point-in-time.

### Sàng lọc thô và tương quan

| Nhánh | Markout thô có giá / intent | Gross thô R | Phí thô R | Swap thô R | Net thô R | Số năm qua cửa phí | Tỷ lệ giữ qua 12% |
| --- | --- | --- | --- | --- | --- | --- | --- |
| SWING_TREND_D1 | 2469/2472 | −12,66 | 59,07 | −147,97 | −219,70 | 0/7 | 100,0% |
| SWING_CARRY_TREND_D1 | 688/689 | −39,95 | 14,10 | 3,22 | −50,82 | 2/7 | 100,0% |
| SWING_INDEX_DIP_D1 | 35/54 | 4,10 | 1,54 | −1,01 | 1,54 | 3/7 | 100,0% |
| EQUAL_RISK | 3192/3215 | −48,51 | 74,71 | −145,76 | −268,97 | 1/7 | 100,0% |

Tương quan Pearson trên thay đổi equity ngày broker, điền 0 khi không có mark. Bảng theo nhánh thuộc rổ ghép 10k. Ma trận mã và nhánh theo cả cụm và 25k có trong JSON.

| Nhánh | SWING_TREND_D1 | SWING_CARRY_TREND_D1 | SWING_INDEX_DIP_D1 |
| --- | --- | --- | --- |
| SWING_TREND_D1 | 1,000 | 0,224 | −0,016 |
| SWING_CARRY_TREND_D1 | 0,224 | 1,000 | 0,002 |
| SWING_INDEX_DIP_D1 | −0,016 | 0,002 | 1,000 |

## 3. Phân loại lệnh thắng

[Selective Win Diagnosis](../../.agents/skills/strategy-qualification/references/selective-win-diagnosis.md) khóa thứ tự ưu tiên và điều kiện biết tại entry. Nhãn đường đi giá để chẩn đoán exit. BASE_GUARD dùng tape SYM và quote pack OLHC Development 2018–2023 có hash. Đường USDJPY de62a92 dựng lại từ input H1 đã khóa và khớp entry/exit/net/swap với ledger. 56/62 winner USDJPY thoát theo cutoff nhưng thiếu cặp giữ tiếp tương thích, nên taxonomy để unknown. BASE_GUARD giữ unknown cho nguồn path bất định, MAE/MFE ở phần còn lại dùng M1 scenario và cost proxy theo trade.

Các ô taxonomy là **số winner · tỷ trọng pool R dương**. MAE/MFE dùng R theo risk gốc của nguồn, capture dùng realized net/MFE. So sánh chỉ dùng mô tả do độ phân giải D1, H1 và M1 scenario khác nhau.

| Cohort | Winners | Clean | Tail | Carry | Cutoff | Lucky | Unknown | MAE / MFE trung vị R | Capture trung vị | Top 2 / 5 / 10 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SWING_TREND_D1 · 10000 · SWING | 153 | 0 · 0,0% | 56 · 71,4% | 1 · 0,0% | 0 · 0,0% | 96 · 28,6% | 0 · 0,0% | 0,05 / 4,76 | 33,8% | 7,6% / 15,0% / 24,8% |
| SWING_TREND_D1 · 10000 · FRIDAY_OPEN | 573 | 141 · 44,1% | 12 · 9,7% | 0 · 0,0% | 93 · 17,3% | 317 · 27,4% | 10 · 1,5% | 0,02 / 0,81 | 94,6% | 2,1% / 4,8% / 8,8% |
| SWING_CARRY_TREND_D1 · 10000 · SWING | 104 | 0 · 0,0% | 51 · 79,3% | 2 · 0,4% | 0 · 0,0% | 51 · 20,4% | 0 · 0,0% | 0,03 / 4,82 | 43,1% | 10,4% / 18,1% / 29,3% |
| SWING_CARRY_TREND_D1 · 10000 · FRIDAY_OPEN | 243 | 60 · 47,5% | 1 · 1,9% | 0 · 0,0% | 61 · 21,7% | 118 · 28,1% | 3 · 0,7% | 0,02 / 0,70 | 96,1% | 3,2% / 6,9% / 12,6% |
| SWING_INDEX_DIP_D1 · 10000 · SWING | 16 | 7 · 72,1% | 0 · 0,0% | 0 · 0,0% | 0 · 0,0% | 9 · 27,9% | 0 · 0,0% | 0,05 / 1,04 | 85,7% | 28,5% / 59,5% / 89,9% |
| SWING_INDEX_DIP_D1 · 10000 · FRIDAY_OPEN | 20 | 4 · 45,9% | 0 · 0,0% | 0 · 0,0% | 2 · 11,2% | 14 · 42,9% | 0 · 0,0% | 0,05 / 0,68 | 90,7% | 27,5% / 53,7% / 82,4% |
| EQUAL_RISK · 10000 · SWING | 193 | 6 · 2,3% | 71 · 70,6% | 2 · 0,2% | 0 · 0,0% | 114 · 26,9% | 0 · 0,0% | 0,05 / 4,72 | 37,5% | 6,7% / 13,2% / 20,8% |
| EQUAL_RISK · 10000 · FRIDAY_OPEN | 818 | 202 · 45,3% | 13 · 7,5% | 0 · 0,0% | 155 · 18,5% | 435 · 27,3% | 13 · 1,3% | 0,02 / 0,80 | 94,6% | 1,5% / 3,5% / 6,4% |
| USDJPY_de62a92 | 62 | 0 · 0,0% | 0 · 0,0% | 0 · 0,0% | 0 · 0,0% | 6 · 4,4% | 56 · 95,6% | 0,09 / 2,55 | 77,7% | 15,0% / 31,2% / 47,3% |
| BASE_GUARD_DEV_2018_2023 | 148 | 46 · 64,6% | 0 · 0,0% | 0 · 0,0% | 0 · 0,0% | 90 · 26,9% | 12 · 8,5% | 0,23 / 0,85 | 65,8% | 9,9% / 19,6% / 32,2% |

Trong rổ Friday 10k, 802/815 winner đóng vì lịch có cặp giữ tiếp. 155 lệnh có phần lời tăng đủ ngưỡng, tổng +397,47R (62,9% pool lời đối chứng trên nhóm winner clamp ghép cặp). Đây là phần lời tăng trên winner được chọn hồi tố. Bảng ghép toàn mẫu phía trên bao gồm cả lệnh thua.

JSON lưu phân rã theo cụm và 25k, base rates theo trend/volatility/weekday/distance trên cả thắng, thua và hòa, median time-to-peak và swap share theo nhãn, Top‑2/5/10 và phần net sau khi bỏ các winner lớn nhất. Dấu carry lịch sử được để unknown. Cột carry snapshot là proxy riêng.

## 4. Kiểm chứng và giới hạn

Đã đối soát 11.321 dòng sổ và 11.767 dòng nhãn: ranh giới Development, dấu PnL và 16 sổ policy × vốn × view, tổng gross − phí + swap = net, cap tại entry, khóa mẫu và label membership. 19 unit test PASS, 0 skip. Audit skill 0 lỗi, 0 warning. Niêm phong từ 01/01/2025 giữ nguyên. Giữ 20% Standard làm đối chứng, không đưa các signal cũ vào một vòng tối ưu mới.

Giới hạn chính gồm spread một cửa sổ, swap/margin snapshot chiếu ngược, FX conversion D1, khoảng trống lịch lễ, không có giá khớp tick xuyên tuần và lịch phiên Standard chưa có export cùng tài khoản. 50% là cap admit. Tỷ lệ margin có thể tăng sau khi equity giảm, như peak 57,4% ở rổ 10k. Kết quả chỉ ở tầng sàng lọc Development. Hoàn tất audit ký quỹ và phân rã winner vẫn chưa giải quyết được thiếu lợi thế sau phí của các tín hiệu đã đăng ký.

[JSON đối soát](SWING-10K-AUDIT-MULTIWEEK-AND-WIN-TAXONOMY-20261120.json) · [SHA256](SWING-10K-AUDIT-MULTIWEEK-AND-WIN-TAXONOMY-20261120.sha256) · [Holdout lock](NATIVE_FTMO_HOLDOUT_LOCK.json).

Private manifest: swing-10k-20261120/manifest.json. SHA256: 0d9d87ef808613b6b8f35b0412ef4dde428ed7379cad532f881884c28fc41e41. Hash báo cáo và JSON dùng byte LF chuẩn trong Git.

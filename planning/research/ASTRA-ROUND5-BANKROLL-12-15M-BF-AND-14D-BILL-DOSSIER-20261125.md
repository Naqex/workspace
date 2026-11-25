# Hồ Sơ Tái Thẩm Định Astra Vòng 5 — Bài Toán Vốn `12–15 triệu VND`, Lịch Sale FTMO Thật & 2 Kịch Bản `30/11` vs Giữ Bill `14 Ngày`

- **Ngày lập:** `25/11/2026 23:22 ICT` · **Tình trạng:** `READY_FOR_ASTRA_ROUND5_RECHECK`
- **Cập nhật 4 dữ kiện mới so với Vòng 4:**
  1. **Điều kiện pháp lý tuổi tác:** Chủ sở hữu xác nhận **đủ điều kiện `>= 18` tuổi** (cổng hợp lệ tham gia FTMO đã thông qua).
  2. **Khung vốn rủi ro thực tế tại Việt Nam:** **`12–15 triệu VND`** (`~462–577 USD` @ `26.000 VND/USD`). Khoản chênh lệch **`9–29 USD`** (`~235k–755k VND`) hay chênh tiền ứng trước **`~1,56 triệu VND`** (`98,70 EUR` vs `155 EUR`) đều có ý nghĩa thực tế — cần đặt rõ trên cùng bàn cân theo VND.
  3. **Đã hoàn thành 100% phép kiểm Astra Vòng 4 chỉ định (`v1.01`, Dev `<= 2024-12-31`, `Holdout 2025+` NIÊM PHONG, `OrderSend = 0`):**
     - Mô phỏng **1 vé không retry (`N = 10.000 × 36 tháng`)** + mở rộng thành **bộ 4 bảng theo vốn `12–15 triệu VND`** (`1 vé` / `2 vé` / `3 vé` / `Chờ đợt sale`), gắn **vé #1 = Black Friday** và **vé #2/#3 chạy đúng lịch khuyến mãi thật của FTMO** (không còn giả định lỗi mọi vé mua lại đều là giá Black Friday như vòng 4!).
     - Kiểm thử **MT5 `Naqex_Master_Prop7E.ex5 v1.01`** tại đúng độ trễ đo được **`500 ms` (P50)** và **`655 ms` (P90)** trên `20,02 triệu` tick thực Q4/2024, cộng thêm **Full-2024 `Model=1` ở `500 ms`** (`Funded 1x` & `P1 4x`).
  4. **Hai kịch bản thời hạn thực tế song song (thay vì cực đoan chỉ có hạn `30/11`):**
     - **Case 1 (`PAY_BY_NOV30`):** Thanh toán trực tiếp trước `16:00 ICT Thứ Hai 30/11/2026` (gồm cả biến thể **Case 1B**: trả trước `30/11`, giữ tài khoản `0` lệnh trong `10–12 ngày` theo quyền hủy hợp đồng `14 ngày` của FTMO GTC nếu chưa mở lệnh).
     - **Case 2 (`HOLD_UNPAID_BILL_14D`):** Tạo đơn `Đang chờ / Chưa thanh toán` trên `trader.ftmo.com/billing` vào sáng `30/11` (**`0 VND`** bỏ ra ngày `30/11`), tận dụng thời hạn giữ hóa đơn ~14 ngày (tới `~13–14/12/2026`) để gom thêm `10–12` phiên đo đuôi SL `US100.cash` xuyên **NFP `04/12` + CPI `10/12`** trước khi quyết định bấm trả tiền.

---

## 1. Research Lịch Khuyến Mãi FTMO & Cơ Chế Giữ Bill `14 Ngày` (Tách Bạch Nguồn Chính Thức vs Cộng Đồng)

### A. Lịch khuyến mãi thực tế trong năm của FTMO
- **Nguyên tắc chung (nguồn chính thức `ftmo.com` & cộng đồng Reddit `r/PropFirmTester`, `r/Forex`):** FTMO **KHÔNG phát mã giảm giá ngẫu nhiên** (các trang coupon bên ngoài đa số giả). Ưu đãi thật chỉ áp tự động toàn trang vào vài khung lớn hoặc đổi **FTMO Points** (`1 Point = 1 EUR`, chỉ có sau khi rút thưởng/hoàn phí).
- **Lịch sale theo mùa đã kiểm chứng:**
  1. **Black Friday / Cyber Monday (23/11 – 30/11 `16:00 ICT`):** Đợt giảm sâu và chắc chắn nhất năm (**`-20%` đến `-30%`** cho `FTMO Standard` CFD; năm 2026 trên `trader.ftmo.com/billing` VN ghi nhận 2 mức bill thực tế tùy cấu hình: **`98,70 EUR` ≈ `105,12 USD` ≈ `2,73 tr VND`** hoặc **`62,30 EUR` ≈ `66,35 USD` ≈ `1,73 tr VND`** ứng với giá gốc `89 EUR` `-30%`).
  2. **Giáng Sinh / Năm Mới (`~20/12 – 07/01`):** Khá thường xuyên lặp lại ưu đãi **`~10%–20%`** (không cam kết cứng hàng năm; mô phỏng dưới chạy cả nhánh có `-20% = 124 EUR` lẫn nhánh bảo thủ không có sale Giáng Sinh).
  3. **Kỷ niệm / Cột mốc (`Tháng 9`):** Thỉnh thoảng có đợt `10%–20%` ngắn ngày, không đều hàng năm.
  4. **Các tháng còn lại (`Tháng 2–8, 10` — chiếm ~85% số ngày trong năm):** Gần như **không có khuyến mãi** — mua lại phải trả giá gốc **`155 EUR` (`165,08 USD ≈ 4,29 tr VND`)** (hoặc `89 EUR = 94,79 USD ≈ 2,46 tr VND` nếu FTMO giữ giá nền vùng 10K).

### B. Đối chiếu 2 kịch bản thời hạn: `30/11` vs Giữ Bill `14 Ngày`
| Kịch bản | Tiền bỏ ra ngày `30/11` | Bằng chứng nguồn | Ưu điểm | Rủi ro thực tế cần nhìn thẳng |
|---|---:|---|---|---|
| **Case 1A: Thanh toán trước `30/11 16:00 ICT` & chạy từ `01/12`** | `2,73 tr` *(hoặc `1,73 tr`)* VND | Chính thức `ftmo.com` | Chắc chắn `100%` khóa giá Black Friday | Chỉ có dữ liệu sống `1` phiên (`28/28` RT, `2` lệnh SL `US100.cash`); khóa vốn ngay |
| **Case 1B: Thanh toán trước `30/11`, giữ `0` lệnh trong `10–12 ngày` (xuyên NFP `04/12` + CPI `10/12`)** | `2,73 tr` *(hoặc `1,73 tr`)* VND | **FTMO General Terms & Conditions** (chính thức: quyền rút khỏi hợp đồng hoàn `100%` trong `14` ngày nếu **chưa đặt bất kỳ lệnh demo nào**; ngủ đông `30` ngày) | Khóa `100%` giá Black Friday + có thêm `10–12` ngày đo đuôi SL Demo trước khi đặt lệnh #1; nếu Demo vỡ chuẩn thì yêu cầu hoàn phí | Cần đọc kỹ điều khoản checkout VN xem có ngoại lệ cho đơn promo Black Friday không; nếu hoàn về thẻ VN vẫn có thể mất `~2–3%` phí chuyển đổi ngoại tệ (`~60k–80k VND`) |
| **Case 2: Tạo đơn `Đang chờ / Chưa thanh toán` sáng `30/11` (Giữ bill ~14 ngày -> `~13–14/12`)** | **`0 VND`** | **Kinh nghiệm cộng đồng VN** (ảnh chụp thật `trader.ftmo.com/billing`: trạng thái `Đang chờ`, số tiền khóa `98,70 EUR` / `62,30 EUR`, tự hủy sau ~14 ngày) + bài `hocvientrader.com` | **Quyền chọn mua miễn phí (`0 VND` rủi ro ngày `30/11`)**: vừa giữ cửa hưởng giá Black Friday, vừa có `10–12` ngày đo đa phiên sống trên `naqex-node1` xuyên NFP `04/12` + CPI `10/12` trước khi chi đồng nào | **FTMO không cam kết bằng hợp đồng** giữ giá khuyến mãi cho hóa đơn chưa trả sau `30/11 10:00 CET` — hệ thống tự động có thể hủy hoặc đổi về giá gốc sớm hơn 14 ngày (khi đó thiệt hại tiền mặt = `0 VND`, chỉ mất suất sale và quay về giá thường / chờ sale Giáng Sinh) |

---

## 2. Bộ Bảng Kinh Tế Trên Vốn Thực `12–15 Triệu VND` (`N = 10.000 × 36 Tháng`, `v1.01 REL+HEADROOM`, `GUARD_ALL_ON`, `P1 Sprint 4x`)

Biên nhận Layer-2: `private_vault/strategies/wave2-overnight-rd-20261125/single_ticket_v101_audit/bankroll_12_15m_bf_summary.json` (`26.000 VND/USD`, `1,065 USD/EUR`, `Holdout 2025+` NIÊM PHONG, `holdout_rows_analysed = 0`).
**Cơ chế giá trung thực (đã sửa lỗ hổng vòng 4):** Vé #1 = giá thực ngày vào (`98,70 EUR = 105,12 USD = 2,73 tr` hoặc `155 EUR = 165,08 USD = 4,29 tr`); vé mua lại #2/#3 tính đúng giá lịch ngày lịch thực tế (`155 EUR` ngoài mùa sale, `-20% = 124 EUR` nếu rơi `20/12–07/01`, `-30% = 98,70 EUR` nếu rơi `23–30/11`), và FTMO chỉ hoàn đúng phí của **vé đậu**.

### Bảng A — So sánh 4 cấu trúc vốn (`1 vé` / `2 vé` / `2 vé chờ sale` / `3 vé`) khi **VÉ #1 = BLACK FRIDAY (`98,70 EUR = 2,73 tr VND`)** vs **BỎ BLACK FRIDAY (`155 EUR = 4,29 tr VND`)**

#### A1. Tại ma sát `0,66×` (đúng trung bình 28/28 lệnh đo sống) & `1,00×` (chuẩn Dev)

| Ma sát | Kế hoạch (trần vốn `<= 12–15 tr VND`) | `P(Pay1)` 12m / 24m / 36m | Chờ Pay1 P50 (24m) | **Lãi ròng 24m Mean (USD / tr VND)** | **Lãi ròng 24m Med (USD / tr VND)** | `P(Lỗ<=0)` 24m | Vốn ứng TB / P95 / Trần (tr VND) | `EV / Mean OOP` | Cháy sạch vé (`Ruin`) |
|---|---|---:|---:|---:|---:|---:|---|---:|---:|
| **`0,66×`** | **`BF98 · 1 vé duy nhất` (0 retry)** | `59,9 / 84,7 / 88,6%` | `273d` | `+834,8` (`+21,71 tr`) | `+815,9` (`+21,21 tr`) | `15,3%` | `2,73 / 2,73 / 2,73 tr` | **`+7,94×`** | `10,2%` |
| `0,66×` | `Bỏ BF (155 EUR) · 1 vé duy nhất` | `59,9 / 84,7 / 88,6%` | `273d` | `+825,7` (`+21,47 tr`) | `+815,9` (`+21,21 tr`) | `15,3%` | `4,29 / 4,29 / 4,29 tr` | `+5,00×` | `10,2%` |
| **`0,66×`** | **`BF98 · Trần 2 vé` (lịch thật)** | `62,3 / 91,9 / 97,3%` | `284d` | **`+883,3` (`+22,97 tr`)** | **`+856,6` (`+22,27 tr`)** | **`8,4%`** | **`3,17 / 7,02 / 7,02 tr`** | **`+7,25×`** | **`1,2%`** |
| `0,66×` | `Bỏ BF (155 EUR) · Trần 2 vé` | `62,3 / 91,9 / 97,3%` | `284d` | `+874,2` (`+22,73 tr`) | `+851,8` (`+22,15 tr`) | `8,8%` | `4,73 / 8,58 / 8,58 tr` | `+4,81×` | `1,2%` |
| **`0,66×`** | **`BF98 · Trần 3 vé` (lịch thật)** | `62,4 / 92,5 / 98,2%` | `286d` | `+886,5` (`+23,05 tr`) | `+858,2` (`+22,31 tr`) | `8,0%` | `3,22 / 7,02 / 11,32 tr` | `+7,17×` | `0,1%` |
| **`1,00×`** | **`BF98 · 1 vé duy nhất` (0 retry)** | `46,6 / 73,0 / 79,2%` | `300d` | `+551,7` (`+14,34 tr`) | `+490,5` (`+12,75 tr`) | `27,0%` | `2,73 / 2,73 / 2,73 tr` | **`+5,25×`** | `18,1%` |
| `1,00×` | `Bỏ BF (155 EUR) · 1 vé duy nhất` | `46,6 / 73,0 / 79,2%` | `300d` | `+535,5` (`+13,92 tr`) | `+490,5` (`+12,75 tr`) | `27,0%` | `4,29 / 4,29 / 4,29 tr` | `+3,24×` | `18,1%` |
| **`1,00×`** | **`BF98 · Trần 2 vé` (lịch thật)** | `49,5 / 83,0 / 92,5%` | `319d` | **`+598,4` (`+15,56 tr`)** | **`+555,2` (`+14,44 tr`)** | **`17,7%`** | **`3,50 / 7,02 / 7,02 tr`** | **`+4,45×`** | **`3,1%`** |
| `1,00×` | `BF98 · Trần 2 vé (chờ đợt sale)` | `46,8 / 80,0 / 91,4%` | `320,5d` | `+569,1` (`+14,80 tr`) | `+513,0` (`+13,34 tr`) | `20,8%` | `3,26 / 5,47 / 6,17 tr` | `+4,54×` | `2,9%` |
| `1,00×` | `Bỏ BF (155 EUR) · Trần 2 vé` | `49,5 / 83,0 / 92,5%` | `319d` | `+582,3` (`+15,14 tr`) | `+545,9` (`+14,19 tr`) | `18,4%` | `5,06 / 8,58 / 8,58 tr` | `+2,99×` | `3,1%` |
| **`1,00×`** | **`BF98 · Trần 3 vé` (lịch thật)** | `49,5 / 84,2 / 94,6%` | `322d` | `+601,6` (`+15,64 tr`) | `+558,5` (`+14,52 tr`) | `16,9%` | `3,63 / 7,02 / 11,32 tr` | `+4,31×` | `0,5%` |
| `1,00×` | `Bỏ BF (155 EUR) · Trần 3 vé` | `49,5 / 84,2 / 94,6%` | `322d` | `+585,5` (`+15,22 tr`) | `+548,4` (`+14,26 tr`) | `17,7%` | `5,19 / 8,58 / 12,88 tr` | `+2,93×` | `0,5%` |

#### A2. Tại vùng stress `1,25×`, `1,50×` (mức Astra yêu cầu chấm) & `1,75×`

| Ma sát | Kế hoạch (trần vốn `<= 12–15 tr VND`) | `P(Pay1)` 12m / 24m / 36m | Chờ Pay1 P50 (24m) | **Lãi ròng 24m Mean (USD / tr VND)** | **Lãi ròng 24m Med (USD / tr VND)** | `P(Lỗ<=0)` 24m | Vốn ứng TB / P95 / Trần (tr VND) | `EV / Mean OOP` | Cháy sạch vé (`Ruin`) |
|---|---|---:|---:|---:|---:|---:|---|---:|---:|
| **`1,25×`** | **`BF98 · 1 vé duy nhất`** | `37,8 / 62,6 / 69,8%` | `316d` | `+386,2` (`+10,04 tr`) | `+266,9` (`+6,94 tr`) | `37,4%` | `2,73 / 2,73 / 2,73 tr` | `+3,67×` | `26,3%` |
| **`1,25×`** | **`BF98 · Trần 2 vé` (lịch thật)** | `40,7 / 74,2 / 86,1%` | `340d` | **`+423,0` (`+11,00 tr`)** | **`+359,5` (`+9,35 tr`)** | **`27,0%`** | **`3,84 / 7,02 / 7,02 tr`** | **`+2,86×`** | **`6,2%`** |
| `1,25×` | `Bỏ BF (155 EUR) · Trần 2 vé` | `40,7 / 74,2 / 86,1%` | `340d` | `+400,6` (`+10,42 tr`) | `+347,2` (`+9,03 tr`) | `28,1%` | `5,40 / 8,58 / 8,58 tr` | `+1,93×` | `6,2%` |
| **`1,25×`** | **`BF98 · Trần 3 vé` (lịch thật)** | `40,8 / 75,8 / 89,4%` | `346d` | `+423,7` (`+11,02 tr`) | `+362,9` (`+9,44 tr`) | `26,1%` | `4,10 / 11,32 / 11,32 tr` | `+2,69×` | `1,2%` |
| **`1,50×`** | **`BF98 · 1 vé duy nhất`** | `29,3 / 51,2 / 58,3%` | `329d` | `+245,5` (`+6,38 tr`) | `+62,4` (`+1,62 tr`) | `48,8%` | `2,73 / 2,73 / 2,73 tr` | **`+2,34×`** | `35,8%` |
| `1,50×` | `Bỏ BF (155 EUR) · 1 vé duy nhất` | `29,3 / 51,2 / 58,3%` | `329d` | `+216,3` (`+5,62 tr`) | `+62,4` (`+1,62 tr`) | `48,8%` | `4,29 / 4,29 / 4,29 tr` | `+1,31×` | `35,8%` |
| **`1,50×`** | **`BF98 · Trần 2 vé` (lịch thật)** | `31,9 / 63,2 / 76,4%` | `362d` | **`+262,7` (`+6,83 tr`)** | **`+185,0` (`+4,81 tr`)** | **`38,2%`** | **`4,24 / 7,02 / 7,02 tr`** | **`+1,61×`** | **`11,5%`** |
| `1,50×` | `BF98 · Trần 2 vé (chờ đợt sale)` | `29,4 / 59,1 / 74,0%` | `367d` | `+244,2` (`+6,35 tr`) | `+131,2` (`+3,41 tr`) | `42,3%` | `3,76 / 5,47 / 6,17 tr` | `+1,69×` | `10,8%` |
| `1,50×` | `Bỏ BF (155 EUR) · Trần 2 vé` | `31,9 / 63,2 / 76,4%` | `362d` | `+233,4` (`+6,07 tr`) | `+173,2` (`+4,50 tr`) | `39,6%` | `5,80 / 8,58 / 8,58 tr` | `+1,05×` | `11,5%` |
| **`1,50×`** | **`BF98 · Trần 3 vé` (lịch thật)** | `32,0 / 65,3 / 81,1%` | `370d` | `+258,9` (`+6,73 tr`) | `+194,5` (`+5,06 tr`) | `37,1%` | `4,72 / 11,32 / 11,32 tr` | `+1,43×` | `3,1%` |
| `1,50×` | `Bỏ BF (155 EUR) · Trần 3 vé` | `32,0 / 65,3 / 81,1%` | `370d` | `+229,6` (`+5,97 tr`) | `+179,4` (`+4,66 tr`) | `38,7%` | `6,28 / 12,88 / 12,88 tr` | `+0,95×` | `3,1%` |
| **`1,75×`** | **`BF98 · 1 vé / Trần 2 vé / Trần 3 vé`** | `40,1 / 51,4 / 54,0%` *(24m)* | `339–386d` | `+138 / +129 / +118` | `-105 / -16,5 / +30` | `60 / 50 / 49%` | `2,73 / 7,02 / 11,32 tr` | `+1,31 / +0,72 / +0,56×` | `46 / 19 / 6,7%` |

*(Ghi chú kiểm tra độ nhạy `No-Xmas`: tắt hoàn toàn sale Giáng Sinh chỉ làm lệch Mean 24m `< 0,5 USD` vì rất ít đường rơi đúng 18 ngày cuối tháng 12. Kịch bản **`Hold14D`** lùi khởi chạy sang `14/12/2026` cho kết quả 24m trùng khít tới `0,1 USD` — không mất lợi nhuận nào nhưng lời thêm `10–12` ngày đo đuôi Demo!)*

### Bảng B — Độ nhạy nếu trang checkout VN hiện **`62,30 EUR` (`66,35 USD = 1,73 tr VND`, gốc `89 EUR = 2,46 tr`)** (đã thấy trên ảnh bill VN `trader.ftmo.com/billing`)

| Ma sát | Kế hoạch (`BF62 -> gốc 89 EUR`) | `P(Pay1)` 24m / 36m | Chờ Pay1 P50 | Lãi ròng 24m Mean (USD / tr VND) | Lãi ròng 24m Med (USD / tr VND) | `P(Lỗ<=0)` | Vốn ứng TB / Trần (tr VND) | `EV / Mean OOP` |
|---|---|---:|---:|---:|---:|---:|---|---:|
| `0,66×` | `BF62 · 1 vé / 2 vé / 3 vé` | `84,7 / 91,9 / 92,5%` | `273–286d` | `+841 / +891 / +895` (`+21,9–23,3 tr`) | `+816 / +859 / +861` | `15,3 / 8,3 / 7,8%` | `1,73 / 4,19 / 6,65 tr` | `+12,7 / +11,7 / +11,6×` |
| `1,00×` | `BF62 · 1 vé / 2 vé / 3 vé` | `73,0 / 83,0 / 84,2%` | `300–322d` | `+562 / +614 / +618` (`+14,6–16,1 tr`) | `+491 / +558 / +562` | `27,0 / 17,3 / 16,3%` | `1,73 / 4,19 / 6,65 tr` | `+8,5 / +7,4 / +7,2×` |
| `1,50×` | `BF62 · 1 vé / 2 vé / 3 vé` | `51,2 / 63,2 / 65,3%` | `329–370d` | `+264 / +296 / +297` (`+6,9–7,7 tr`) | `+62 / +195 / +206` | `48,8 / 37,3 / 35,8%` | `1,73 / 4,19 / 6,65 tr` | `+4,0 / +3,0 / +2,7×` |

---

## 3. Bằng Chứng Kỹ Thuật Mới Đóng Góp Vào Vòng 5 (`v1.01`, `Holdout 2025+` NIÊM PHONG)

1. **Đóng điểm mù độ trễ `50 ms` vs `493 / 655 ms` thực đo (`Model=4` `20,02 triệu` tick thực Q4/2024, `v1.01`, `1:100`, `492` tin đỏ, `swap = 0,00 USD`, `clean = True`):**
   - `50 ms`: `+736,06 USD` (`PF 1,23`, `Sh 1,98`, `EqDD 6,27%`, `155` lệnh)
   - **`500 ms` (P50 đo sống):** **`+790,52 USD`** (`PF 1,25`, `Sh 2,13`, `EqDD 6,24%`, `155` lệnh)
   - **`655 ms` (P90 đo sống):** **`+799,56 USD`** (`PF 1,25`, `Sh 2,15`, `EqDD 6,17%`, `155` lệnh)
   - *Trung thực:* Không có suy giảm cấu trúc khi tăng trễ gấp `10–13×` trên lịch sử tick thực (chênh `+54..+63 USD` là nhiễu mở nến, không tính là lợi thế; MT5 `ExecutionMode` chưa thay thế được độ sâu sổ lệnh khi tin sốc).
2. **Đóng điểm mù "Full-2024 mới chạy v1.00" (`Model=1` cả năm 2024 ở `500 ms` trên `v1.01`):**
   - `Funded 1x @ 500 ms`: **`+613,64 USD`**, `4/4` quý dương, `minBal 9.960,39`, `EqDD 4,06%`, `worstDay -148,12 USD`.
   - `P1 4x @ 500 ms`: **`+1.418,65 USD`**, `4/4` quý dương, `minBal 9.595,79`, vượt qua cú sụp Yen `05/08/2024` (`-314,00 USD = -3,14% < -5%`), **đạt `+10%` đúng ngày `2024-05-15` (`134` ngày lịch)**.
3. **Điểm mù duy nhất còn mở (nhưng Case 2 giải được với chi phí `0 VND`!):** Mới đo `1` phiên sống (`28/28` RT, Core-4 P50 `0,615×` / P90 `0,897×`, Bootstrap 95% CI `[0,618×..0,704×]`) và `2` lần chạm SL thật trên `US100.cash`.

---

## 4. Nhận Định Toán Học Rút Ra Trước Khi Chấm Vòng 5

- **`BF98 · Trần 2 vé` (tối đa `7,02 tr VND`, giữ lại `5–8 tr` tiền mặt) áp đảo cả `1 vé` lẫn `3 vé`:** Ở `1,50×`, nâng `P(Pay1 24m)` từ `51,2% -> 63,2%`, cắt `Ruin` từ `35,8% -> 11,5%`, nâng trung vị lãi gấp `3×` (`+1,62 -> +4,81 tr VND`), trong khi thêm vé #3 (`11,32 tr VND`) làm **giảm nhẹ** Mean (`+262,7 -> +258,9 USD`).
- **Ngồi chờ đợt sale cho vé #2 (`WAIT_PROMO`) bị phản tác dụng:** tiết kiệm ~`0,85 tr` trần OOP nhưng mất thời gian chạy Funded nên giảm trung vị ròng từ `+4,81 -> +3,41 tr VND`.
- **Chiến lược tối ưu thời điểm (`Case 2` vs `Case 1B`):** Thay vì ép quyết định sống còn trước `30/11` khi mới đo 1 phiên, **tạo đơn giữ bill `Đang chờ` sáng `30/11` (`0 VND` rủi ro)** — kết hợp chạy thêm `10–12` phiên Demo sống xuyên NFP `04/12` + CPI `10/12` — biến hạn chót cực đoan `30/11` thành quyền chọn miễn phí; hoặc dùng **Case 1B** (trả `30/11` nhưng giữ `0` lệnh 10–12 ngày để bảo toàn quyền hoàn `100%` trong 14 ngày của FTMO GTC nếu checkout không có ngoại lệ).

---

## 5. Prompt Sẵn Dán Gửi GPT-6.2 Astra (Vòng 5 — Tái Thẩm Định Sau Khi Vá Đủ 4 Điểm Mù)

> *Chủ sở hữu sao chép nguyên khối sau dán trực tiếp cho Astra.*

```text
Xin Astra chấm lại Vòng 5 (GO / HOLD-14D-BILL / UNPAID-OPTION) cho Naqex_Master_Prop7E v1.01 với đầy đủ dữ kiện mới vừa bổ sung để giải quyết đúng 4 điểm Vòng 4 đã chỉ ra (tất cả dùng Dev <= 2024-12-31, Holdout 2025+ NIÊM PHONG, OrderSend=0):

1) CẬP NHẬT CHỦ SỞ HỮU & PHÁP LÝ:
- Chủ sở hữu xác nhận ĐỦ 18+ TUỔI (VN, hoàn toàn hợp lệ tham gia FTMO).
- Tổng vốn rủi ro hiện có: 12–15 triệu VND (~462–577 USD @ 26.000 VND/USD). Không ép phải dừng cứng ở 1 vé nếu 2 vé tối ưu hơn trong khung vốn; và khoản tiết kiệm 1,56 triệu VND tiền mặt ứng trước (98,70 EUR vs 155 EUR) hay 240k–760k VND EV đều có ý nghĩa thực tế với chủ sở hữu.
- Lưu ý: Trên trader.ftmo.com/billing tại VN ghi nhận 2 mức giá Black Friday (-30%): mức bảo thủ 98,70 EUR (~105,12 USD ~ 2,73 tr VND, gốc 155 EUR = 4,29 tr VND) và mức ưu đãi vùng 62,30 EUR (~66,35 USD ~ 1,73 tr VND, gốc 89 EUR = 2,46 tr VND).

2) KẾT QUẢ KIỂM THỬ MT5 v1.01 Ở ĐÚNG ĐỘ TRỄ THỰC ĐO (500 ms P50 / 655 ms P90) & FULL-2024:
- Q4/2024 Model=4 Real-Tick (20,02M tick thực, P1 4x + PROFIT_LOCK, 1:100, 492 tin đỏ, swap=0,00, 155 lệnh):
  * 50 ms (cũ): +736,06 USD | PF 1,23 | Sh 1,98 | BalDD 4,92% | EqDD 6,27%
  * 500 ms (P50 đo sống): +790,52 USD | PF 1,25 | Sh 2,13 | BalDD 4,90% | EqDD 6,24%
  * 655 ms (P90 đo sống): +799,56 USD | PF 1,25 | Sh 2,15 | BalDD 4,83% | EqDD 6,17%
  (Không suy giảm cấu trúc ở 500–655 ms; chênh +54..+63 USD coi là nhiễu mở nến, không tính là lợi thế.)
- Full-2024 Model=1 @ 500 ms trên v1.01 (swap=0,00, clean=True):
  * Funded 1x: +613,64 USD | PF 1,15 | Sh 1,21 | EqDD 4,06% | 4/4 quý dương (minBal 9.960,39)
  * P1 4x: +1.418,65 USD | PF 1,15 | Sh 1,26 | EqDD 8,75% | 4/4 quý dương | minBal 9.595,79 | ngày sụp Yên 05/08/2024 -3,14% (< -5%) | đạt +10% ngày 2024-05-15 (134 ngày).

3) BẢNG KINH TẾ VỐN 12–15 TR VND (N=10.000 x 36 tháng, v1.01 REL+HEADROOM, GUARD_ALL_ON, P1 Sprint 4x, VÉ #1 = BLACK FRIDAY, VÉ #2/#3 TÍNH ĐÚNG LỊCH KHUYẾN MÃI THẬT FTMO: 155 EUR ngoài mùa, -20% Giáng Sinh, -30% BF năm sau):
- Ma sát 0,66x (đúng TB 28/28 lệnh sống):
  * BF98 1 vé (0 retry, Max 2,73tr): Pay1(12/24/36m) 59,9/84,7/88,6% | Chờ P50 273d | Net24 Mean +834,8 (+21,7tr) / Med +815,9 (+21,2tr) | P<=0 15,3% | Ruin 10,2% | EV/OOP +7,94x
  * BF98 Trần 2 vé (Max 7,02tr): Pay1 62,3/91,9/97,3% | Chờ P50 284d | Net24 Mean +883,3 (+23,0tr) / Med +856,6 (+22,3tr) | P<=0 8,4% | MeanOOP 3,17tr | Ruin 1,2% | EV/OOP +7,25x
  * Bỏ BF (155 EUR) Trần 2 vé (Max 8,58tr): Net24 Mean +874,2 / Med +851,8 | MeanOOP 4,73tr | EV/OOP +4,81x
- Ma sát 1,00x (chuẩn Dev):
  * BF98 1 vé (Max 2,73tr): Pay1 46,6/73,0/79,2% | Chờ P50 300d | Net24 Mean +551,7 (+14,3tr) / Med +490,5 (+12,8tr) | P<=0 27,0% | Ruin 18,1% | EV/OOP +5,25x
  * BF98 Trần 2 vé (Max 7,02tr): Pay1 49,5/83,0/92,5% | Chờ P50 319d | Net24 Mean +598,4 (+15,6tr) / Med +555,2 (+14,4tr) | P<=0 17,7% | MeanOOP 3,50tr | Ruin 3,1% | EV/OOP +4,45x
  * BF98 Trần 2 vé (chờ đợt sale mua vé 2, Max 6,17tr): Pay1 46,8/80,0/91,4% | Net24 Mean +569,1 / Med +513,0 (kém hơn mua ngay)
  * Bỏ BF (155 EUR) Trần 2 vé (Max 8,58tr): Net24 Mean +582,3 / Med +545,9 | MeanOOP 5,06tr | EV/OOP +2,99x
- Ma sát 1,25x:
  * BF98 1 vé: Pay1 37,8/62,6/69,8% | Chờ 316d | Net24 Mean +386,2 / Med +266,9 | P<=0 37,4% | Ruin 26,3%
  * BF98 Trần 2 vé: Pay1 40,7/74,2/86,1% | Chờ 340d | Net24 Mean +423,0 (+11,0tr) / Med +359,5 (+9,35tr) | P<=0 27,0% | Ruin 6,2% | EV/OOP +2,86x
- Ma sát 1,50x (stress Astra):
  * BF98 1 vé (Max 2,73tr): Pay1 29,3/51,2/58,3% | Chờ P50 329d | Net24 Mean +245,5 (+6,38tr) / Med +62,4 (+1,62tr) | P<=0 48,8% | Ruin 35,8% | EV/OOP +2,34x
  * BF98 Trần 2 vé (Max 7,02tr): Pay1 31,9/63,2/76,4% | Chờ P50 362d | Net24 Mean +262,7 (+6,83tr) / Med +185,0 (+4,81tr) | P<=0 38,2% | MeanOOP 4,24tr | Ruin 11,5% | EV/OOP +1,61x
  * BF98 Trần 3 vé (Max 11,32tr): Pay1 32,0/65,3/81,1% | Chờ P50 370d | Net24 Mean +258,9 / Med +194,5 | Ruin 3,1% (Mean giảm nhẹ so với 2 vé!)
  * Bỏ BF (155 EUR) Trần 2 vé (Max 8,58tr): Net24 Mean +233,4 / Med +173,2 | MeanOOP 5,80tr | EV/OOP +1,05x
  * Nếu checkout VN hiện 62,30 EUR (1,73tr, gốc 89 EUR = 2,46tr): BF62 Trần 2 vé (Max 4,19tr) ở 1,50x đạt Mean +296,3 (+7,70tr) / Med +195,1 (+5,07tr) | EV/OOP +2,97x.
- Ma sát 1,75x: BF98 Trần 2 vé Mean +128,8 / Med -16,5 / P<=0 50,3% / Ruin 19,4%.

4) HAI KỊCH BẢN THỜI HẠN SONG SONG (THAY VÌ CỰC ĐOAN CHỈ CÓ 30/11):
- Case 1 (Trả trước 30/11 16:00 ICT): Khóa chắc 100% giá BF. Biến thể Case 1B: trả trước 30/11 nhưng giữ 0 lệnh trong 10–12 ngày (xuyên NFP 04/12 + CPI 10/12) để đo thêm đuôi SL US100.cash trên Demo; theo FTMO GTC chính thức có quyền hủy hoàn 100% trong 14 ngày nếu chưa đặt lệnh nào (kiểm trước điều khoản checkout & phí ngoại tệ thẻ ~2–3%).
- Case 2 (Tạo đơn giữ bill Đang chờ sáng 30/11 — 0 VND bỏ ra ngày 30/11): Cộng đồng VN trên trader.ftmo.com/billing giữ bill chưa thanh toán được ~14 ngày (đến ~13–14/12/2026), vừa có thêm 10–12 phiên đo đuôi SL thật (NFP 04/12 + CPI 10/12) trước khi trả tiền; rủi ro duy nhất là FTMO không cam kết bằng hợp đồng nên có thể tự hủy bill sớm (thiệt hại tiền mặt = 0 VND).

CÂU HỎI CHỐT VÒNG 5 CHO ASTRA (TRẢ LỜI NGẮN GỌN, THẲNG THẮN):
1. Với đầy đủ dữ kiện mới (đủ 18+, vốn 12–15tr VND, v1.01 qua 500/655ms & Full-2024, bảng 1/2/3 vé theo lịch sale thật), Astra chọn phương án nào trong 4 phương án:
   (a) CASE 2 — Tạo bill giữ giá 14 ngày sáng 30/11 (0 VND), đo thêm đuôi SL US100.cash qua NFP 04/12 + CPI 10/12 rồi quyết định thanh toán trước ngày 13/12?
   (b) CASE 1B — Thanh toán 1 vé BF trước 30/11 (khóa chắc giá 98,70 hoặc 62,30 EUR) nhưng giữ 0 lệnh 10–12 ngày đo Demo rồi kích hoạt (hoặc rút theo luật 14 ngày GTC nếu đo xấu)?
   (c) CASE 1A — Thanh toán & chạy ngay từ 01/12 với trần kỷ luật 2 vé (tối đa 7,02 tr VND)?
   (d) Vẫn giữ UNPAID-OPTION 0 USD bỏ qua hoàn toàn (kể cả không tạo bill giữ giá)?
2. Nếu vào tiền (sau khi vượt cổng đo đuôi SL hoặc ngay 30/11), cấu hình kỷ luật nào hợp lý nhất cho vốn 12–15tr VND: Trần 1 vé hay Trần 2 vé, và nếu checkout VN hiện 62,30 EUR vs 98,70 EUR thì phán quyết có đổi không?
3. Điểm mù lớn nhất còn lại (nếu có) trước khi đặt lệnh thật đầu tiên là gì?
```

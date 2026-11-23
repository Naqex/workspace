# Pass 18 Protocol · Săn Động Cơ #3 Ngoài `USDJPY` Từ Nguồn Mở Học Thuật & MQL5 CodeBase

- **Trạng thái:** `PRE_REGISTERED_BEFORE_EXECUTION` (đóng băng luật trước khi chạy số liệu)
- **Ngày khóa:** `2026-11-23`
- **Bối cảnh kế thừa:** Pass 17 (`1062475`) xác nhận bộ đôi 2 động cơ `USDJPY` (`PORT_INV_DD_075`: Tokyo-box + `EXP_DAILY_OPEN_080`) giảm Peak DD 40% (`9,08% -> 5,45%`), giảm Underwater 50% (`41,2 -> 20,6` tháng), Calmar tăng gấp đôi (`0,32 -> 0,64`), nhưng tốc độ `+3,51% – +3,70%/năm` vẫn dưới ngưỡng FTMO Challenge `8–12%/năm` và dồn 100% rủi ro vào `USDJPY`. Đồng thời `EXP_DAILY_OPEN` thất bại trên `US500` và chỉ đạt mức nhẹ trên `GBPUSD` (`1,20 ATR`).
- **Mục tiêu Pass 18 (Hướng 1 — nguồn mở hợp pháp):** Kiểm định 14 giả thuyết **100% trong ngày (`swap = 0`), 100% ngoài `USDJPY`** (`US500`, `EURUSD`, `GBPUSD`, `XAUUSD`) trích từ tài liệu học thuật bình duyệt (*JFE*, *Journal of Finance*, *JFM*) và chuẩn mã nguồn mở kinh điển (Quantpedia, MQL5 CodeBase `.mq5` NR4) nhằm tìm ứng viên Động cơ #3 có tương quan thấp với lõi `USDJPY`.
- **Ranh giới bất biến:**
  - Chỉ đọc vùng Development UTC `2018-01-01` đến `2024-12-31` từ D: SSD Hot M1 Parquet Cache (SHA-verified); **`holdout_rows = 0`**, giữ nguyên khóa [NATIVE_FTMO_HOLDOUT_LOCK.json](NATIVE_FTMO_HOLDOUT_LOCK.json) (`SHA f0a6b43cb205535b0a959456455dc1d857a0936c06c2e51b8614fd7d772a8486`).
  - `OrderSend = 0`, `network_calls = 0`, không thực thi file `.ex5`/`.exe`/`.dll` bên ngoài.
  - Mọi đồng hồ phiên dùng múi giờ DST chính xác (`America/New_York` cho `US500`, `Europe/London` cho WMR Fix / LBMA Fix, `UTC` cho đóng ngày).
  - `US500`, `EURUSD`, `GBPUSD` chạy **Native M1 Bid/Ask**; `XAUUSD` dùng M1 Bid + Stress spread proxy (`$0,50`) và luôn gắn nhãn `PROVISIONAL_XAU` (chưa cấp Tier 1 chính thức nếu chưa có Native Ask).

---

## 1. Danh sách 14 giả thuyết khóa trước (`BH FDR m = 14`, `swap = 0`)

Mọi chiến lược dùng `ATR14_D` tính hoàn toàn nhân quả trên nến D1 đã đóng trước đó (`idx - 1`), SL bảo vệ `0,75 × ATR14_D` (kiểm tra SL-trước bảo thủ trên cùng phút M1), đóng cưỡng bức cuối phiên trong ngày (`swap = 0`):

| # | Mã chiến lược | Tài sản | Nguồn sơ cấp (học thuật / mã nguồn mở) | Luật vào lệnh nhân quả | Đóng lệnh (`swap = 0`) |
| ---: | --- | --- | --- | --- | --- |
| 1 | `US500_GHLZ_LAST30` | `US500` | Gao, Han, Li & Zhou (2018), *JFE* — *Market Intraday Momentum* | `r1 = (Bid_10:00ET - Close_prev16:00ET) / ATR14_D`; nếu `abs(r1) >= 0,25` vào lúc `15:30 ET` theo `sign(r1)` | SL `0,75 ATR`, flat `15:55 ET` |
| 2 | `US500_GHLZ_AFTERNOON` | `US500` | Gao, Han, Li & Zhou (2018), *JFE* (tách lệnh cuối ngày) | `r1h = (Bid_10:30ET - Open_09:30ET) / ATR14_D`; nếu `abs(r1h) >= 0,35` vào lúc `13:30 ET` theo `sign(r1h)` | SL `0,75 ATR`, flat `15:55 ET` |
| 3 | `US500_GAP_FADE_NY` | `US500` | Lou, Polk & Skouras (2019), *JFE* — *Overnight vs Intraday* | Gap đêm `g = (Open_09:30ET - Close_prev16:00ET) / ATR14_D`; nếu `abs(g) >= 0,35` **đánh ngược gap** lúc `09:35 ET` | SL `0,75 ATR`, TP `0,60 × abs(gap)`, flat `15:55 ET` |
| 4 | `US500_IBS_INTRADAY` | `US500` | Quantpedia / Connors — *Internal Bar Strength* | Ngày trước `IBS = (C-L)/(H-L)`: `IBS <= 0,20` → BUY, `IBS >= 0,80` → SELL lúc `09:35 ET` | SL `0,75 ATR`, flat `15:55 ET` |
| 5 | `FX_WMR_PRE_FIX` | `EURUSD` | Krohn, Mueller & Whelan (2024), *Journal of Finance* | Trượt giá USD trước Fix 16:00 London: SELL lúc `13:00 Europe/London` | SL `0,75 ATR`, flat `15:55 London` |
| 6 | `FX_WMR_PRE_FIX` | `GBPUSD` | Krohn, Mueller & Whelan (2024), *Journal of Finance* | Trượt giá USD trước Fix 16:00 London: SELL lúc `13:00 Europe/London` | SL `0,75 ATR`, flat `15:55 London` |
| 7 | `FX_WMR_POST_FIX` | `EURUSD` | Krohn, Mueller & Whelan (2024), *Journal of Finance* | Đảo chiều giải tỏa tồn kho sau Fix 16:00 London: BUY lúc `16:05 Europe/London` | SL `0,75 ATR`, flat `20:55 London` |
| 8 | `FX_WMR_POST_FIX` | `GBPUSD` | Krohn, Mueller & Whelan (2024), *Journal of Finance* | Đảo chiều giải tỏa tồn kho sau Fix 16:00 London: BUY lúc `16:05 Europe/London` | SL `0,75 ATR`, flat `20:55 London` |
| 9 | `FX_WMR_MORNING_FADE` | `EURUSD` | Krohn, Mueller & Whelan (2024), *JoF* (có điều kiện) | Nếu biên `07:00 → 15:55 London` `>= 0,50 ATR`, đánh ngược chiều lúc `16:05 Europe/London` | SL `0,75 ATR`, flat `20:55 London` |
| 10 | `FX_WMR_MORNING_FADE` | `GBPUSD` | Krohn, Mueller & Whelan (2024), *JoF* (có điều kiện) | Nếu biên `07:00 → 15:55 London` `>= 0,50 ATR`, đánh ngược chiều lúc `16:05 Europe/London` | SL `0,75 ATR`, flat `20:55 London` |
| 11 | `XAU_NR4_EXPANSION` | `XAUUSD` | Toby Crabel (1990) / MQL5 CodeBase `.mq5` NR4 | Ngày trước là `NR4` (biên độ nhỏ hơn 3 ngày liền trước): breakout `Open ± 0,65 ATR` trong `07:00–17:00 UTC` | SL `0,75 ATR`, flat `20:55 UTC` |
| 12 | `XAU_LBMA_PM_DRIFT` | `XAUUSD` | Caminschi & Heaney (2014), *JFM* — *LBMA Gold Fix* | Biên phiên London sáng `07:00 → 13:00 London` `>= 0,40 ATR`: thuận chiều lúc `13:05 London` vào COMEX/PM Fix | SL `0,75 ATR`, flat `20:55 UTC` |
| 13 | `EURUSD_NR4_EXPANSION` | `EURUSD` | Toby Crabel (1990) / MQL5 CodeBase `.mq5` NR4 | Ngày trước là `NR4`: breakout `Open ± 0,65 ATR` trong `07:00–17:00 UTC` | SL `0,75 ATR`, flat `20:55 UTC` |
| 14 | `GBPUSD_NR4_EXPANSION` | `GBPUSD` | Toby Crabel (1990) / MQL5 CodeBase `.mq5` NR4 | Ngày trước là `NR4`: breakout `Open ± 0,65 ATR` trong `07:00–17:00 UTC` | SL `0,75 ATR`, flat `20:55 UTC` |

---

## 2. Phí thực thi, kiểm định thống kê & tiêu chí phân tầng

1. **Phí thực thi:**
   - **FTMO Stress (chính):** FX `native Bid/Ask + $7/lot + 0,9 pip RT`; `US500` `native Bid/Ask + 0,75 pt/chiều` (báo cáo kèm `Mid 0,50` và `Base 0,25`); `XAUUSD` `$0,50 spread + $0,50 slip RT + comm` (`PROVISIONAL_XAU`).
   - **Exness Personal (tham chiếu không ràng buộc):** theo `EXNESS-CONTRACT-SPECS-SNAPSHOT-20261123.json`.
2. **Chống ảo giác & đánh giá trực giao:**
   - Đối xứng ngược chiều (`Fade`) trên cùng điểm vào & SL.
   - Kiểm định `Random-Entry Monte Carlo Null` (`N = 1.000`, `seed = 20261123`) trên đúng tập ngày giao dịch.
   - Hiệu chỉnh đa giả thuyết **Benjamini–Hochberg FDR (`m = 14`)**.
   - Tách Cụm A (`2018–2020`) vs Cụm B (`2021–2024`), tách chiều `BUY` vs `SELL`, và đo **hệ số tương quan Pearson theo ngày (`corr_usdjpy_core`)** so với lõi 2 động cơ `USDJPY` (`PORT_INV_DD_075`) từ Pass 17.
3. **Chuẩn 3 tầng:**
   - `TIER_1_FTMO_READY`: Native Bid/Ask, `n >= 150`, FTMO Stress `> 0` cả Cụm A & B, `>= 5/7` năm dương, `MC p < 0,05`, `BH FDR q <= 0,10`, thắng Fade, `|corr_usdjpy_core| < 0,35` để vào vòng pháp y ghép danh mục Pass 19.
   - `TIER_2_PERSONAL_VAULT`: Có edge thực sau phí hoặc chỉ dương ở Exness/không đủ tốc độ FTMO Challenge (hoặc `XAUUSD` thiếu Native Ask gắn nhãn `PROVISIONAL_XAU`).
   - `TIER_3_DEAD_NO_EDGE`: Lỗ hoặc không vượt kiểm định ngẫu nhiên / chỉ sống nhờ 1 giai đoạn.

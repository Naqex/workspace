# Pass 15 · Protocol Engine #2 đo ni đóng giày cho FTMO (`XAUUSD` Intraday `swap = 0` & FX Carry-Aligned Swing)

Baseline `460c77f` (nhánh `codex/prop-research-roadmap`).
Phạm vi dữ liệu **Development UTC `2018-01-01` → `< 2025-01-01`** (`1514764800`..`1735689600`), đọc từ **Hot M1 Parquet Cache SSD** (`.runtime/hot-m1-cache/`, đã đối soát SHA-256 với ổ E).
Khóa cứng Holdout `>= 2025-01-01` (`NATIVE_FTMO_HOLDOUT_LOCK.json`, `holdout_rows = 0`).
`network_calls = 0`, `OrderSend = 0`, không MT5, không đọc `.env`.
Thông số phí/swap/margin bám SHA `36f1535` (FTMO Standard) và `8fd77ef` (FTMO Swing); phân loại 3 tầng theo `validation-gates.md`.

## Động lực thiết kế (rút trực tiếp từ bằng chứng Pass 10–14)

1. **Khắc phục triệt để bẫy Swap Vàng (`-56,28 USD/đêm`, thứ Tư `3×`):** Nhánh A chỉ đánh biến động phiên London–Mỹ của `XAUUSD` và **đóng phẳng toàn bộ lúc `20:55 UTC` (`swap = 0` tuyệt đối)**, tận dụng tỷ lệ `cost/ATR` thấp nhất toàn sàn mà không mất `15–40R` phí qua đêm như các chiến lược H4/D1 ở Pass 14.
2. **Tận dụng chính chiều Swap dương của FTMO:** Trên FTMO Swing, **`USDJPY` Long có `swap_long = +2,61`** và **`EURUSD` Short có `swap_short = +0,28`** — sàn trả ngược tiền giữ lệnh cho hệ thống thay vì ăn mòn lợi nhuận.
3. **Giữ tập thử gọn (`7` giả thuyết trực giao):** Tránh làm loãng lực kiểm định FDR như khi quét 52+ cặp ngẫu nhiên.

---

## Nhánh A · `XAUUSD` Intraday Volatility & Momentum (`swap = 0`, 2 chiều, `2018–2024`)

- **Dữ liệu & ghi chú trung thực:** `XAUUSD` M1 Bid + FTMO proxy spread (`Base $0,35` + `$0,10/chiều` slip; **`Stress_Mid $0,50` + `$0,25/chiều` slip (primary)**; `Stress_High $0,75` + `$0,50/chiều` slip) + commission FTMO `price * 100 * 0,000007` mỗi chiều. Vì `native_Ask = false`, mọi ứng viên vượt cửa trên `XAUUSD` được gắn nhãn tối đa `TIER_1_FTMO_READY_PROVISIONAL_XAU` (cần xác nhận lại trên Tick Bid/Ask thật trước bước shadow/demo).
- **4 cơ chế đăng ký trước (tối đa 1 lệnh/ngày, đóng phẳng `20:55 UTC`, `swap = 0`, SL-first khi trùng phút):**
  1. **`XAU_DAILY_OPEN_ATR` (đồng thời khớp khái niệm `BRK019`):** Mở ngày UTC `00:00` đặt mốc `open_0`. Trong `07:00–16:59 UTC`, OCO mua khi Ask chạm `open_0 + 0,50 * ATR14_D1` (SL = `open_0 - 0,25 * ATR14_D1`, tổng rủi ro `0,75 * ATR14_D1`) hoặc bán khi Bid chạm `open_0 - 0,50 * ATR14_D1` (SL = `open_0 + 0,25 * ATR14_D1`), giữ tới `20:55 UTC`.
  2. **`XAU_LONDON_NY_MOMENTUM`:** Đo xung lực phiên London `07:00–12:59 UTC` (đã đóng hoàn toàn). Nếu `|C_1259 - O_0700| >= 0,45 * ATR14_D1` và nến London đóng trong vùng `30%` cực trị theo hướng xung lực → vào theo xu hướng tại `13:00 UTC`, `SL = 0,60 * ATR14_D1`, giữ tới `20:55 UTC`.
  3. **`XAU_H1_DONCHIAN_INTRADAY`:** Trong `07:00–16:59 UTC`, vào theo nến H1 đầu tiên đóng phá `Donchian(20)` (cao hơn `max` 20 giờ trước → BUY; thấp hơn `min` 20 giờ trước → SELL), `SL = 1,5 * ATR14_H1`, giữ tới `20:55 UTC`.
  4. **`XAU_ASIA_SQUEEZE_BREAK`:** Đo biên độ phiên Á `00:00–06:59 UTC`. Chỉ giao dịch những ngày biên Á nén chặt (`asia_range < 0,35 * ATR14_D1` và `asia_range >= 0,10 * ATR14_D1` để tránh ngày nghỉ lễ phẳng). Đặt OCO phá đỉnh/đáy phiên Á trong `07:00–16:59 UTC`, SL ở biên đối diện phiên Á, giữ tới `20:55 UTC`.

---

## Nhánh B · FX Positive-Carry Trend-Following (Native Tick M1 Bid/Ask, `2018–2024`)

- **Dữ liệu & chi phí (`native_Ask = true`):** `USDJPY` (`pass7b`) và `EURUSD` (`pass13`) Native Tick-derived M1 Bid/Ask; commission FTMO `5 USD/lot` RT, slippage **`M1_Real_Stress_05` (`+0,50 pip` RT + `0,20 pip/chiều` gốc = `0,90 pip` RT, primary)** và **`FTMO Swing Swap` có dấu + thứ Tư `3×`** (`USDJPY swap_long = +2,61`, `EURUSD swap_short = +0,28`).
- **3 cơ chế đăng ký trước (không chồng vị thế, SL-first trên đường đi M1):**
  5. **`CARRY_USDJPY_LONG_DONCHIAN20`:** Khi D1 đóng vượt đỉnh `20` ngày (`C > max(H[d-20:d])`) và `C > EMA50_D1` → mua mở phiên ngày kế tiếp (`00:00 UTC`), `SL = entry - 2,0 * ATR14_D1`, thoát khi SL chạm trên M1 hoặc D1 đóng thủng đáy `10` ngày (`Donchian 10` trailing) hoặc tối đa `20` ngày giao dịch.
  6. **`CARRY_USDJPY_LONG_PULLBACK_H4`:** Khi nền D1 tăng (`C > EMA50_D1`), mua khi H4 hồi chạm `<= EMA20_H4` rồi đóng tăng `> EMA20_H4` (`C > O`), `SL = min(H4_low, EMA20 - 1,5 * ATR14_H4)`, `TP = entry + 2,5 * risk`, tối đa `10` ngày.
  7. **`CARRY_EURUSD_SHORT_DONCHIAN20`:** Khi D1 đóng thủng đáy `20` ngày (`C < min(L[d-20:d])`) và `C < EMA50_D1` → bán mở phiên ngày kế tiếp (`00:00 UTC`), `SL = entry + 2,0 * ATR14_D1`, thoát khi SL chạm trên M1 hoặc D1 đóng vượt đỉnh `10` ngày hoặc tối đa `20` ngày giao dịch.

---

## Đối chứng, Kiểm định & Ghép danh mục tự động

- **Monte Carlo Random-Entry Null Test (`N = 1.000`, `seed = 20261123`)** cho cả 7 giả thuyết + **Benjamini–Hochberg FDR (`m = 7`)**.
- **Đối chứng `Fade` (đảo chiều cùng thời điểm)** cho cả 4 cơ chế 2 chiều ở Nhánh A.
- **Phân loại 3 tầng (`validation-gates.md`):**
  - `TIER_1_FTMO_READY` (hoặc `_PROVISIONAL_XAU` nếu `native_Ask=false`): `n >= 30`, `FTMO_Stress net_R > 0`, dương cả Cụm A (`2018–2020`) & Cụm B (`2021–2024`), `>= 5/7` năm dương, `net_R > top10_R`, `MC Null p_f < 0,05`, `closed_dd_R <= 25R`.
  - `TIER_2_PERSONAL_VAULT`: Trượt Tier 1 do tốc độ/tần suất/Swap FTMO nhưng có edge thật (`MC Null p_g < 0,05`, dương cả Cụm A & B trên Exness Ref, `>= 5/7` năm dương).
  - `TIER_3_DEAD_NO_EDGE`: Còn lại.
- **Hậu kiểm tự động cho MỌI ứng viên Tier 1 / Tier 2:** Chạy **lưới độ bền tham số `±30%`** (bắt buộc toàn bộ/đa số ô lân cận giữ dương cả 2 cụm) và chạy **ghép danh mục M1 với Engine #1 `USDJPY` Pass 7B/8** (khi ứng viên thuộc Nhánh A hoặc intraday `swap = 0` tương thích Prague daily reset, hoặc đánh giá đóng/nổi trên sổ Swing 10k/25k & Standard 50k).

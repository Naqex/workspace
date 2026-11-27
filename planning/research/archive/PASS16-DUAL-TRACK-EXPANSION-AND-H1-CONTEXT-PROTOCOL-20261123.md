# Pass 16 · Protocol 2 nhánh song song: Động lượng mở rộng tần suất thấp (`swap = 0`) & 8 mã `H1` còn lại của `strategy-intel`

Baseline `fbd3a1c` (nhánh `codex/prop-research-roadmap`).
Phạm vi dữ liệu **Development UTC `2018-01-01` → `< 2025-01-01`** trên **Hot M1 Parquet Cache SSD** (`.runtime/hot-m1-cache/`, SHA-verified).
Khóa cứng Holdout `>= 2025-01-01` (`holdout_rows = 0`), `network_calls = 0`, `OrderSend = 0`, Air-Gap 100% với `strategy-intel`.
Thông số phí FTMO bám SHA `36f1535`/`8fd77ef`; tham chiếu Exness bám [EXNESS-CONTRACT-SPECS-SNAPSHOT-20261123.json](EXNESS-CONTRACT-SPECS-SNAPSHOT-20261123.json) (`EXNESS_WEBSITE_SNAPSHOT_UNMEASURED_DEMO`).

---

## Nhánh 1 · Khai thác tín hiệu động lượng `p = 0,004` ở Pass 15 (Ngưỡng mở rộng biên độ lớn, tần suất thấp, `swap = 0`)

- **Động lực:** Ở Pass 15, `XAU_DAILY_OPEN_ATR` (`open_0 ± 0,50*ATR`) tạo lãi gộp `+$29.484` (`MC p = 0,004`, `FDR q = 0,028`, thắng Fade `+144,5R`) nhưng thua ròng vì vào quá dày (`1.235` lệnh → phí thực thi `-$64.803`).
- **4 cấu hình giảm tần suất / mở rộng biên độ (2 chiều, tối đa 1 lệnh/ngày, đóng phẳng `20:55 UTC`, `swap = 0`, SL-first):**
  1. `EXP_DAILY_OPEN_080`: Kích hoạt OCO tại `open_0 ± 0,80 * ATR14_D1` trong `07:00–16:59 UTC`, `SL = 0,75 * ATR14_D1`.
  2. `EXP_DAILY_OPEN_100`: Kích hoạt OCO tại `open_0 ± 1,00 * ATR14_D1` trong `07:00–16:59 UTC`, `SL = 0,75 * ATR14_D1`.
  3. `EXP_DAILY_OPEN_120`: Kích hoạt OCO tại `open_0 ± 1,20 * ATR14_D1` trong `07:00–16:59 UTC`, `SL = 0,75 * ATR14_D1`.
  4. `EXP_DAILY_OPEN_080_TREND`: Như `0,80 * ATR` nhưng chỉ nhận chiều thuận `EMA50_D1` đã đóng hôm trước.
- **Tài sản kiểm định (`4 × 3 = 12` cặp):** `XAUUSD` (M1 Bid + proxy spread `Stress_Mid $0,50` + `$0,25/chiều` slip, gắn nhãn `PROVISIONAL` nếu sống sót), `USDJPY` (Native Tick M1 Bid/Ask, `M1_Real_Stress_05`), `EURUSD` (Native Tick M1 Bid/Ask, `M1_Real_Stress_05`).
- Kèm đối chứng **`Fade`**, **Monte Carlo Null (`N=1.000`, `seed=20261123`)**, **BH FDR (`m=12`)**, kiểm **±30% tham số** và **ghép danh mục M1 với Engine #1 `USDJPY`** cho mọi ứng viên lọt Tier 1 / Tier 2.

---

## Nhánh 2 · Đóng sổ nhóm `39 TÌNH HUỐNG` của `strategy-intel` — 8 chiến lược `H1` nội phiên (`swap = 0`)

*(Mã thứ 9 là `BRK019` đã kiểm ở Pass 15.)* Mọi tín hiệu chỉ đọc nến đã đóng, vào tại `open` phút M1 kế tiếp, tối đa 1 lệnh/ngày, đóng phẳng `20:55 UTC` (`swap = 0`), chạy trên **3 tài sản** (`XAUUSD` gốc + `EURUSD`, `USDJPY` native M1 Bid/Ask → **`8 × 3 = 24` cặp**, BH FDR riêng `m = 24`):

1. **`BRK011` (Camarilla R4/S4 breakout):** Từ nến D1 hôm qua: `R4 = C + (H-L)*0,55`, `S4 = C - (H-L)*0,55`. Trong `07:00–16:59 UTC`, phá `R4` → BUY (`SL = C + (H-L)*0,275`, tức `R3`), phá `S4` → SELL (`SL = S3`).
2. **`BRK037` (Momentum 2 nến H1 liên tiếp phá biên):** Hai nến H1 đóng liên tiếp vượt trên `Donchian(20)` → BUY (`SL = 1,5*ATR14_H1`); 2 nến đóng liên tiếp dưới `Donchian(20)` → SELL.
3. **`IND017` (CCI ±100 breakout):** H1 `CCI(20)` cắt lên `+100` → BUY, cắt xuống `-100` → SELL (`SL = 1,5*ATR14_H1`).
4. **`IND027` (EMA 9/21 cross H1):** Trong `07:00–16:59 UTC`, H1 `EMA(9)` cắt lên `EMA(21)` → BUY, cắt xuống → SELL (`SL = 1,5*ATR14_H1`).
5. **`MTF005` (Weekly High/Low + H1 từ chối):** Tính `prev_week_H`, `prev_week_L` của tuần lịch hoàn chỉnh trước đó (100% nhân quả). Nếu nến H1 quét lên `>= prev_week_H` rồi đóng lại `< prev_week_H` và giảm → SELL (`SL = H1_high + buffer`); đối xứng cho đáy tuần → BUY.
6. **`NEN024` (Đáy nhọn V-bottom H1 Long):** Nến H1 trước giảm mạnh `<= -2,0*ATR14_H1`, ngay sau đó nến H1 hiện tại tăng mạnh `>= +2,0*ATR14_H1` → BUY (`SL = min(low_2bars) - buffer`).
7. **`NEN029` (Gap sáng thứ Hai H1):** Nếu `|open_Mon - close_Fri| >= 1,0*ATR14_H1` → vào theo hướng gap tại `01:00 UTC` thứ Hai (`SL = 1,5*ATR14_H1`), đóng `20:55 UTC`.
8. **`VIR024` (3 Line Strike Bull H1 Long):** Ba nến H1 giảm liên tiếp (`C < O` với đáy thấp dần), tiếp theo là 1 nến H1 tăng đóng vượt trên giá mở cửa của nến giảm đầu tiên → BUY (`SL = min(low_4bars) - buffer`).

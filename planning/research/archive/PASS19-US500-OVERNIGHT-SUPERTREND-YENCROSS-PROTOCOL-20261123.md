# Pass 19 Protocol · `US500` Overnight/Swing M1 · Clean-Room `SuperTrend` · Stage-0 Cặp Chéo Yên & Positive-Carry

- **Trạng thái:** `PRE_REGISTERED_BEFORE_EXECUTION` (khóa luật trước thực nghiệm)
- **Ngày khóa:** `2026-11-23`
- **Bối cảnh kế thừa:** Pass 17 (`1062475`) xác nhận lõi 2 động cơ `USDJPY` (`PORT_INV_DD_075`: `+3,51–3,70%/năm`, Peak DD `5,45%`, Calmar `0,64`). Pass 18 (`935a526`) bác bỏ 14 giả thuyết học thuật/mở trong ngày (`swap = 0`) trên `US500`, `EURUSD`, `GBPUSD`, `XAUUSD` vì biên lãi ngắn hạn quá mỏng bị spread CFD nuốt hoặc bị cắt khỏi phần giữ qua đêm (như `IBS`).
- **Mục tiêu Pass 19 (100% zero-network trên dữ liệu đã niêm phong `2018–2024`):**
  1. **Nhánh 1 (Native M1 Bid/Ask `US500`, `m = 6`):** Kiểm định 6 chiến lược học thuật qua đêm / swing ngắn (1–3 ngày) trên `US500` với **đúng biểu phí FTMO Swing đã đo** (`hoa hồng $0/lot`, `swap_long = -138,03 pt`, `swap_short = -36,37 pt`, `triple-swap Thứ Sáu`, trượt giá Stress `0,75 pt/chiều` + đối chứng `Base 0,25 pt/chiều` và `Exness Swap-Free`).
  2. **Nhánh 2 (Clean-Room `SuperTrend(10, 3.0)` Retracement + Step-Trailing trên 5 tài sản M1, `swap = 0`, `m = 5`):** Tự viết sạch khái niệm công khai `SuperTrend(10, 3.0)` hồi về + trailing từng bước (trích từ tên tham số công khai của `.set`, không dịch ngược hay chạy `.ex5`) để kiểm định thật trên `USDJPY`, `EURUSD`, `GBPUSD`, `US500` (Native M1 Bid/Ask) và `XAUUSD` (`PROVISIONAL_XAU`).
  3. **Nhánh 3 (Stage-0 H4/D1 Scout không tải mạng trên 5 cặp FX Swap dương đã niêm phong trong `swing-10k-20261120/development/`, `m = 10` + đối chứng `USDJPY`):** Sàng lọc sơ bộ `EURJPY`, `GBPJPY`, `AUDJPY`, `USDCAD`, `USDCHF` cho (3A) công thức đột phá `EXP_DAILY_OPEN_080` (`swap = 0`) và (3B) Trend Following Donchian thuận chiều **Swap dương FTMO** (nhận `+0,77` đến `+3,50 pt/lot/đêm` + `3×` Thứ Tư). Mọi ứng viên qua Nhánh 3 chỉ gắn nhãn `STAGE0_H4_D1_PRE_M1_SCOUT` — **tuyệt đối không xếp Tier 1 khi chưa kiểm M1 Bid/Ask ở Pass 20**.
- **Ranh giới bất biến:** Development UTC `2018-01-01` đến `2024-12-31`, **`holdout_rows = 0`**, khóa [NATIVE_FTMO_HOLDOUT_LOCK.json](NATIVE_FTMO_HOLDOUT_LOCK.json), `OrderSend = 0`, `network_calls = 0`.

---

## 1. Nhánh 1 · 6 giả thuyết `US500` Overnight / Short-Swing (Native M1 Bid/Ask, BH FDR `m = 6`)

| # | Mã chiến lược | Nguồn gốc | Quy tắc nhân quả (`America/New_York`, đo tại `15:50 ET`) | SL / Đóng lệnh & Swap FTMO |
| ---: | --- | --- | --- | --- |
| 1 | `US500_IBS_OVERNIGHT_LONG` | Quantpedia / Connors | `IBS = (C-L)/(H-L) <= 0,20` tại `15:50 ET` → BUY | SL `1,25 ATR14_D`, thoát `15:50 ET` ngày kế tiếp (tính đủ Swap + 3× T6) |
| 2 | `US500_IBS_NEXT_OPEN_LONG` | Quantpedia (thuần qua đêm) | `IBS <= 0,20` tại `15:50 ET` → BUY | SL `1,00 ATR14_D`, thoát `09:35 ET` sáng hôm sau (tính đủ Swap + 3× T6) |
| 3 | `US500_IBS_TWO_SIDED` | Quantpedia đối xứng | `IBS <= 0,20` BUY / `IBS >= 0,80` SELL tại `15:50 ET` | SL `1,25 ATR14_D`, thoát `15:50 ET` ngày kế tiếp (tách BUY vs SELL) |
| 4 | `US500_RSI2_PULLBACK_LONG` | Larry Connors RSI(2) | `Close > SMA200_D` và `RSI(2) <= 15` tại `15:50 ET` → BUY | SL `1,50 ATR14_D`, thoát khi `Close_15:50 > High_{d-1}` hoặc tối đa 3 ngày |
| 5 | `US500_OVERNIGHT_DRIFT_MON_THU` | Lou–Polk–Skouras (2019 *JFE*) | Thứ Hai–Thứ Năm `15:50 ET` (bỏ Thứ Sáu để né Swap 3×!) → BUY | SL `1,00 ATR14_D`, thoát `09:35 ET` sáng hôm sau |
| 6 | `US500_DOWN_DAY_OVERNIGHT_LONG` | Lou–Polk–Skouras có điều kiện | Ngày giảm mạnh `(C - O) <= -0,50 ATR14_D` tại `15:50 ET` → BUY | SL `1,00 ATR14_D`, thoát `09:35 ET` sáng hôm sau |

*Kiểm định bắt buộc:* Exact FTMO Swing swap (`swapL=-138,03`, `swapS=-36,37`, `3day=5`), Fade đối xứng, Paired Sign-Flip + Random-Day MC Null (`N = 1.000`), BH FDR (`m = 6`), tách Cụm A (`2018–2020`) vs Cụm B (`2021–2024`), tương quan ngày `r(USDJPY)` với lõi Pass 17.

---

## 2. Nhánh 2 · Clean-Room `SuperTrend(10, 3.0)` Retracement + Step-Trailing (`swap = 0`, `m = 5`)

- **Tài sản:** `USDJPY`, `EURUSD`, `GBPUSD`, `US500` (Native M1 Bid/Ask), `XAUUSD` (`PROVISIONAL_XAU`).
- **Quy tắc nhân quả (tính trên nến H1 đã đóng):**
  - Tính `SuperTrend(ATR_period=10, mult=3.0)` trên chuỗi H1 đã đóng (tối thiểu warmup 30 nến).
  - Trong khung thanh khoản (`07:00–17:00 UTC` với FX/XAU; `10:00–14:30 ET` với `US500`), khi `ST_dir == +1` và nến H1 đóng ngay trước đó hồi về gần dải ST (`Low_H1 <= ST_band + 0,50 × ATR_H1` hoặc `Close_H1 < EMA20_H1` nhưng vẫn đóng trên `ST_band`), đặt lệnh dừng BUY phá `High_H1` trước đó trong 60 phút kế tiếp (đối xứng cho SELL khi `ST_dir == -1`).
  - `SL = max(1,00 × ATR_H1, 0,35 × ATR14_D)`. Kích hoạt step-trailing khi lãi nổi đạt `+1,0R` (kéo SL theo từng nấc `0,5R`, khoảng cách `0,5R`), đóng cưỡng bức cuối ngày (`20:55 UTC` / `15:55 ET`, `swap = 0`).

---

## 3. Nhánh 3 · Stage-0 H4/D1 Scout cho 5 cặp FX Swap Dương (`EURJPY`, `GBPJPY`, `AUDJPY`, `USDCAD`, `USDCHF` + đối chứng `USDJPY`)

- **Nguồn dữ liệu:** `E:\BACKUP-TRADINGWORKSPACE\ai-engine-jobs\swing-10k-20261120\development\*-H4.parquet` & `*-D1.parquet`, lọc cứng `2018-01-01 <= ts < 2025-01-01` (warmup từ dữ liệu `< 2018`, `holdout_rows = 0`).
- **3A (`EXP_DAILY_OPEN_080_H4_SCOUT`, `swap = 0`):** Kiểm tra sơ bộ xem công thức `Open ± 0,80 ATR14_D`, `SL 0,75 ATR14_D`, flat cuối ngày có dương cả Cụm A & B trên các cặp chéo Yên / USD khác hay không (phí bảo thủ `1,5 pip RT` + hoa hồng FTMO; hiệu chuẩn đối chiếu trực tiếp với `USDJPY`).
- **3B (`POS_SWAP_DONCHIAN20_D1_SCOUT`, chỉ chiều Swap dương FTMO):** Mua (`BUY`) trên 5 cặp có `swap_long > 0` (`EURJPY +1,24`, `GBPJPY +3,50`, `AUDJPY +2,81`, `USDCAD +0,77`, `USDCHF +1,91`) khi `Close > EMA50_D` và phá đỉnh `20` ngày, `SL = 2,0 ATR14_D`, thoát khi phá đáy `10` ngày (tính đúng Swap dương + `3×` Thứ Tư), đối chiếu với Random-Entry Null để loại bỏ ảo giác xu hướng đơn chiều.
- **Cổng chuyển tầng:** Bất kỳ cặp nào vượt Nhánh 3 chỉ được đề xuất **tải M1 Bid/Ask kiểm định chính thức ở Pass 20**, không cấp `TIER_1_FTMO_READY` từ nến H4/D1.

# Pass 18 · Sàng lọc 14 chiến lược mã nguồn mở & học thuật ngoài `USDJPY` (`swap = 0`)

- **Protocol khóa trước thực nghiệm:** [PASS18-OPENSOURCE-NON-USDJPY-ENGINE3-PROTOCOL-20261123.md](PASS18-OPENSOURCE-NON-USDJPY-ENGINE3-PROTOCOL-20261123.md) (commit `467a028`)
- **An toàn & kiểm thử:** Development UTC `2018–2024`, **`holdout_rows = 0`**, `network_calls = 0`, `OrderSend = 0`, `quant_test_suite` **`1524/1524 PASS (0 skip, 19.43s)`**, thời gian chạy màn hình: `10.45s`.
- **Phán quyết tổng hợp:** **`ALL_14_OPENSOURCE_INTRADAY_NON_USDJPY_REJECTED_BY_CFD_SPREAD_OR_NO_EDGE`** · Phân tầng: **`TIER_1 = 0/14`**, **`TIER_2 = 0/14`**, **`TIER_3 = 14/14`**.

---

## 1. Bảng kết quả toàn bộ 14 giả thuyết (`BH FDR m = 14`, `swap = 0`)

| Chiến lược | Tài sản | `n` | FTMO Stress R (Base R) | Cụm A / B · Năm+ | BUY / SELL R | Fade R | MC `p_f` · FDR `q_f` | `r(USDJPY)` | Phân tầng |
| --- | --- | ---: | --- | --- | --- | ---: | --- | ---: | --- |
| **`US500_GHLZ_LAST30`** | `US500` | `1009` | `-55.24R` (`-26.22R`) | `-28.5 / -26.7` · `0/7` | `-36.1 / -19.1` | `-58.7R` | `0.416` · `q=0.831` | `-0.0266` | `TIER_3_DEAD_NO_EDGE` |
| **`US500_GHLZ_AFTERNOON`** | `US500` | `355` | `-14.22R` (`-3.39R`) | `-6.1 / -8.1` · `3/7` | `-10.6 / -3.7` | `-23.3R` | `0.167` · `q=0.685` | `0.0258` | `TIER_3_DEAD_NO_EDGE` |
| **`US500_GAP_FADE_NY`** | `US500` | `691` | `-76.55R` (`-57.43R`) | `-32.6 / -44.0` · `0/7` | `-36.2 / -40.4` | `-23.2R` | `0.997` · `q=0.997` | `-0.026` | `TIER_3_DEAD_NO_EDGE` |
| **`US500_IBS_INTRADAY`** | `US500` | `829` | `-49.74R` (`-27.04R`) | `-16.6 / -33.2` · `2/7` | `-14.7 / -35.0` | `-50.7R` | `0.525` · `q=0.852` | `-0.0194` | `TIER_3_DEAD_NO_EDGE` |
| **`FX_WMR_PRE_FIX`** | `EURUSD` | `1817` | `-46.01R` (`-29.60R`) | `-24.9 / -21.1` · `1/7` | `+0.0 / -46.0` | `-59.4R` | `0.378` · `q=0.831` | `0.0142` | `TIER_3_DEAD_NO_EDGE` |
| **`FX_WMR_POST_FIX`** | `EURUSD` | `1817` | `-49.72R` (`-33.34R`) | `-25.0 / -24.7` · `0/7` | `-49.7 / +0.0` | `-66.7R` | `0.226` · `q=0.685` | `0.0241` | `TIER_3_DEAD_NO_EDGE` |
| **`FX_WMR_MORNING_FADE`** | `EURUSD` | `585` | `-25.54R` (`-20.38R`) | `-10.1 / -15.5` · `2/7` | `-8.0 / -17.6` | `-9.8R` | `0.720` · `q=0.917` | `-0.0153` | `TIER_3_DEAD_NO_EDGE` |
| **`EURUSD_NR4_EXPANSION`** | `EURUSD` | `237` | `-9.67R` (`-7.52R`) | `-5.2 / -4.4` · `2/7` | `-9.2 / -0.5` | `-27.0R` | `0.859` · `q=0.997` | `0.0472` | `TIER_3_DEAD_NO_EDGE` |
| **`FX_WMR_PRE_FIX`** | `GBPUSD` | `1817` | `-59.30R` (`-47.74R`) | `-37.1 / -22.3` · `0/7` | `+0.0 / -59.3` | `-45.8R` | `0.658` · `q=0.917` | `0.0273` | `TIER_3_DEAD_NO_EDGE` |
| **`FX_WMR_POST_FIX`** | `GBPUSD` | `1817` | `-48.22R` (`-36.59R`) | `-28.7 / -19.5` · `1/7` | `-48.2 / +0.0` | `-64.7R` | `0.245` · `q=0.685` | `0.0144` | `TIER_3_DEAD_NO_EDGE` |
| **`FX_WMR_MORNING_FADE`** | `GBPUSD` | `588` | `-23.22R` (`-19.48R`) | `-13.6 / -9.7` · `2/7` | `-14.3 / -8.9` | `-17.8R` | `0.547` · `q=0.852` | `-0.0217` | `TIER_3_DEAD_NO_EDGE` |
| **`GBPUSD_NR4_EXPANSION`** | `GBPUSD` | `221` | `-16.49R` (`-15.12R`) | `-6.7 / -9.8` · `1/7` | `-6.5 / -10.0` | `-12.4R` | `0.929` · `q=0.997` | `0.0132` | `TIER_3_DEAD_NO_EDGE` |
| **`XAU_NR4_EXPANSION`** | `XAUUSD` | `244` | `-19.18R` (`-16.37R`) | `-4.1 / -15.1` · `2/7` | `-10.7 / -8.5` | `-28.4R` | `0.236` · `q=0.685` | `0.129` | `TIER_3_DEAD_NO_EDGE` |
| **`XAU_LBMA_PM_DRIFT`** | `XAUUSD` | `269` | `-3.50R` (`-0.01R`) | `-2.1 / -1.4` · `2/7` | `-7.3 / +3.8` | `-21.4R` | `0.155` · `q=0.685` | `0.0621` | `TIER_3_DEAD_NO_EDGE` |

---

## 2. Chẩn đoán cơ chế — Vì sao cả 14 mô hình học thuật/mở này đều không qua phí CFD FTMO?

1. **Hiệu ứng tần suất cao học thuật bị ăn mòn bởi chênh lệch Bid/Ask CFD & suy giảm hậu công bố:**
   - **`FX_WMR_POST_FIX` (Krohn–Mueller–Whelan 2024, *Journal of Finance*):** Có lợi thế thô so với đánh ngược chiều (`+17,0R` trên `EURUSD` và `+16,5R` trên `GBPUSD` qua 1.817 ngày), nhưng biên lãi mỗi lệnh quá mỏng (~0,5–1,0 bps) nên phí sàn FTMO (`$5–$7/lot` + spread thực) kéo xuống `-48R` đến `-50R` (Base vẫn `-33R` đến `-37R`).
   - **`US500_GHLZ_LAST30` (Gao–Han–Li–Zhou 2018, *JFE*):** Suy giảm hoàn toàn giai đoạn 2018–2024 (`-55,24R` Stress, `-26,22R` Base, `0/7` năm dương).
   - **`US500_GAP_FADE_NY` (Lou–Polk–Skouras 2019):** Đánh ngược gap đêm trên `US500` thua nặng (`-76,55R`, `0/7` năm dương; đánh thuận gap hơn `+53R` nhưng vẫn âm `-23,2R` sau phí Stress).
   - **`US500_IBS_INTRADAY` (Quantpedia IBS):** Phần lớn lợi thế lịch sử của IBS nằm ở giữ **qua đêm**, khi cắt chỉ giữ trong phiên `09:35–15:55 ET` bị lỗ `-49,74R` (`Base -27,04R`).
2. **Đột phá nén biên độ `NR4` (MQL5 CodeBase / Crabel) không còn edge trên M1 Bid/Ask:** Thua trên cả `EURUSD` (`-9,67R`), `GBPUSD` (`-16,49R`) và `XAUUSD` (`-19,18R`).
3. **Điểm sáng chẩn đoán nhỏ nhất:** `XAU_LBMA_PM_DRIFT` (Caminschi–Heaney London sáng → COMEX/PM Fix) hòa vốn ở mức Base (`-0,01R`) và hơn Fade `+17,9R`, nhưng vẫn âm `-3,50R` ở FTMO Stress (`2/7` năm, `p = 0,155`).
4. **Kết luận chiến lược (giữ nguyên lõi 2 động cơ Pass 17):** Sau 18 Pass (>130 giả thuyết), chỉ những chiến lược **biên độ trung/rộng (`SL ~ 0,75–1,00 ATR`, chi phí `< 5%` SL) + `swap = 0` + cấu trúc xu hướng rõ** như bộ đôi `USDJPY` (`Tokyo-box` + `EXP_DAILY_OPEN_080`) mới sống sót qua M1 Bid/Ask + FTMO Stress. Hướng triển vọng nhất tiếp theo cho Pass 19: (a) mở rộng dữ liệu M1 Bid/Ask sang **cặp chéo Yên biên độ lớn (`EURJPY`, `GBPJPY`, `AUDJPY`)** và/hoặc **`US100.cash` (`NAS100`)** nơi phí/ATR cực nhỏ; hoặc (b) thử chiến lược giữ **nhiều ngày chỉ theo chiều Swap dương / hoa hồng `$0/lot`** (như `US500` swing/overnight dài hơn hoặc FX positive-carry khung D1/W1 có kiểm soát DD).

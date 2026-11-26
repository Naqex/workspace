# Pass 19 · `US500` Overnight M1 (FTMO Swap) · Clean-Room `SuperTrend(10,3)` · Stage-0 Cặp Chéo Yên & Positive-Carry

- **Protocol khóa trước thực nghiệm:** [PASS19-US500-OVERNIGHT-SUPERTREND-YENCROSS-PROTOCOL-20261123.md](PASS19-US500-OVERNIGHT-SUPERTREND-YENCROSS-PROTOCOL-20261123.md) (commit `87c5a3f`)
- **An toàn & kiểm thử:** Development UTC `2018–2024`, **`holdout_rows = 0`**, `network_calls = 0`, `OrderSend = 0`, `quant_test_suite` **`1528/1528 PASS (0 skip, 17.38s)`**.
- **Phán quyết tổng hợp:** **`US500_FTMO_SWAP_HEADWIND_CONFIRMED_SUPERTREND_REJECTED_STAGE0_GBPJPY_AND_POS_SWAP_USDCAD_PROMISING`**.

---

## 1. Nhánh 1 · `US500` Overnight & Short-Swing (Native M1 Bid/Ask, đúng Swap FTMO Swing `swapL=-138,03`, `3×` Thứ Sáu)

| Chiến lược (`US500`) | `n` | FTMO Stress R (Base R) | Exness Swap-Free R | Cụm A / B · Năm+ · DD | Swap FTMO (USD) | Fade R | `p_sf` · `q_f` · `p_tm` | `r(USDJPY)` | Phân tầng |
| --- | ---: | --- | ---: | --- | ---: | ---: | --- | ---: | --- |
| **`US500_IBS_OVERNIGHT_LONG`** | `316` | `-6.42R` (`-1.25R`) | **`+9.40R`** | `-11.5 / +5.1` · `3/7` · `18.5R` | `-609` | `-36.2R` | `0.045` · `q=0.162` · `0.151` | `-0.0557` | `TIER_3_DEAD_NO_EDGE` |
| **`US500_IBS_NEXT_OPEN_LONG`** | `316` | `-19.28R` (`-13.06R`) | **`+0.22R`** | `-14.7 / -4.6` · `2/7` · `24.5R` | `-609` | `-28.5R` | `0.256` · `q=0.357` · `0.454` | `-0.0408` | `TIER_3_DEAD_NO_EDGE` |
| **`US500_IBS_TWO_SIDED`** | `826` | `-44.64R` (`-30.86R`) | **`-14.99R`** | `-26.4 / -18.3` · `2/7` · `46.2R` | `-893` | `-55.3R` | `0.298` · `q=0.357` · `n/a` | `-0.0052` | `TIER_3_DEAD_NO_EDGE` |
| **`US500_RSI2_PULLBACK_LONG`** | `248` | `-13.10R` (`-9.36R`) | **`+5.83R`** | `-9.0 / -4.1` · `1/7` · `26.7R` | `-958` | `-26.1R` | `0.222` · `q=0.357` · `n/a` | `-0.0236` | `TIER_3_DEAD_NO_EDGE` |
| **`US500_OVERNIGHT_DRIFT_MON_THU`** | `1381` | `-67.79R` (`-38.05R`) | **`+8.02R`** | `-43.1 / -24.7` · `1/7` · `76.1R` | `-2003` | `-121.7R` | `0.054` · `q=0.162` · `0.002` | `-0.0292` | `TIER_3_DEAD_NO_EDGE` |
| **`US500_DOWN_DAY_OVERNIGHT_LONG`** | `293` | `-32.44R` (`-26.77R`) | **`-13.22R`** | `-20.7 / -11.7` · `0/7` · `32.4R` | `-596` | `-11.7R` | `0.787` · `q=0.787` · `0.877` | `-0.0417` | `TIER_3_DEAD_NO_EDGE` |

> **Kết luận Nhánh 1:** Phí qua đêm FTMO Swing trên `US500.cash` (`-1,38 USD/đêm`, `-4,14 USD` cuối tuần) hút mất `-596` đến `-2.003 USD` trên 1 hợp đồng, kéo toàn bộ `6/6` chiến lược qua đêm trên FTMO về âm (`TIER_3`). Ngược lại, trên tham chiếu **Exness Swap-Free (`swap = 0`)**, `US500_IBS_OVERNIGHT_LONG` đảo chiều sang **`+9,40R`**, `US500_OVERNIGHT_DRIFT_MON_THU` **`+8,02R`** và `US500_RSI2_PULLBACK_LONG` **`+5,83R`** (chứng minh rõ rào cản nằm ở phí Swap qua đêm FTMO chứ không phải không có hiệu ứng).

---

## 2. Nhánh 2 · Clean-Room `SuperTrend(10, 3.0)` Retracement + Step-Trailing (`swap = 0`, 5 tài sản M1)

| Tài sản (`CLEAN_SUPERTREND_10_3`) | `n` | FTMO Stress R (Base R) | Cụm A / B · Năm+ | Fade R | `p_sf` · `q_f` | `r(USDJPY)` | Phân tầng |
| --- | ---: | --- | --- | ---: | --- | ---: | --- |
| **`USDJPY`** | `973` | `-41.11R` (`-25.15R`) | `-37.2 / -3.9` · `2/7` | `-91.0R` | `0.081` · `q=0.132` | `-0.0581` | `TIER_3_DEAD_NO_EDGE` |
| **`EURUSD`** | `1062` | `-62.01R` (`-42.45R`) | `-20.9 / -41.1` · `2/7` | `-129.3R` | `0.132` · `q=0.132` | `0.057` | `TIER_3_DEAD_NO_EDGE` |
| **`GBPUSD`** | `1043` | `-61.29R` (`-47.84R`) | `-12.3 / -49.0` · `3/7` | `-125.2R` | `0.106` · `q=0.132` | `0.0084` | `TIER_3_DEAD_NO_EDGE` |
| **`US500`** | `715` | `-62.98R` (`-21.89R`) | `-55.6 / -7.4` · `2/7` | `-140.5R` | `0.076` · `q=0.132` | `0.0152` | `TIER_3_DEAD_NO_EDGE` |
| **`XAUUSD`** | `1046` | `-76.65R` (`-50.89R`) | `-46.9 / -29.8` · `1/7` | `-250.8R` | `0.005` · `q=0.025` | `0.0266` | `TIER_3_DEAD_NO_EDGE` |

> **Kết luận Nhánh 2:** Thất bại hoàn toàn (`0/5`, lỗ `-41,1R` đến `-76,7R` Stress và `-21,9R` đến `-50,9R` ngay cả ở Base) do tần suất vào lệnh cao (`715–1.062` lệnh/7 năm) gặp nhiễu M1 Bid/Ask.

---

## 3. Nhánh 3 · Stage-0 H4/D1 Scout (5 cặp FX Swap Dương + đối chứng `USDJPY`, chỉ đề xuất tải M1 cho Pass 20)

### 3A. `EXP_DAILY_OPEN_080` trên H4 (`swap = 0`, hiệu chuẩn trực tiếp trên `CONTROL_USDJPY`)

| Cặp tiền | `n` | Net R (H4 Stress) | Cụm A / B · Năm+ · DD | BUY / SELL R | Fade R | `p_sf` | `r(USDJPY)` | Trạng thái Stage-0 |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- |
| **`EURJPY`** | `647` | `-4.65R` | `-4.1 / -0.5` · `1/7` · `13.2R` | `+7.9 / -12.6` | `-16.2R` | `0.604` | `0.2274` | `STAGE0_H4_D1_PRE_M1_SCOUT` |
| **`GBPJPY`** | `622` | `+9.28R` | `+0.1 / +9.2` · `5/7` · `9.2R` | `+19.8 / -10.5` | `-19.2R` | `0.407` | `0.2295` | `STAGE0_H4_D1_PRE_M1_SCOUT` |
| **`AUDJPY`** | `623` | `-5.88R` | `-7.2 / +1.4` · `2/7` · `12.4R` | `-7.8 / +2.0` | `-28.4R` | `0.246` | `0.2105` | `STAGE0_H4_D1_PRE_M1_SCOUT` |
| **`USDCAD`** | `594` | `-5.08R` | `-10.0 / +4.9` · `2/7` · `15.9R` | `-9.6 / +4.5` | `-20.2R` | `0.332` | `-0.0382` | `STAGE0_H4_D1_PRE_M1_SCOUT` |
| **`USDCHF`** | `618` | `+0.42R` | `-10.3 / +10.7` · `3/7` · `11.2R` | `-3.9 / +4.3` | `-34.3R` | `0.202` | `0.1696` | `STAGE0_H4_D1_PRE_M1_SCOUT` |
| **`USDJPY`** | `611` | `+24.85R` | `+9.4 / +15.4` · `5/7` · `8.6R` | `+36.4 / -11.5` | `-42.0R` | `0.048` | `0.5125` | `CONTROL_USDJPY` |

### 3B. `POS_SWAP_DONCHIAN20_D1` (Chỉ mua chiều Swap dương FTMO, nhận thưởng Swap qua đêm + `3×` Thứ Tư)

| Cặp tiền (`BUY` Swap dương) | `n` | Net R (kèm +Swap) | Cụm A / B · Năm+ · DD | Swap FTMO nhận (USD) | `p_gross` · `p_net` | `r(USDJPY)` | Trạng thái Stage-0 |
| --- | ---: | ---: | --- | ---: | --- | ---: | --- |
| **`EURJPY`** | `32` | `-0.53R` | `-5.4 / +4.9` · `4/7` · `7.3R` | **`+912`** | `0.554` · `0.401` | `-0.0117` | `STAGE0_H4_D1_PRE_M1_SCOUT` |
| **`GBPJPY`** | `29` | `+5.58R` | `-2.2 / +7.8` · `4/7` · `3.6R` | **`+3002`** | `0.301` · `0.161` | `0.0125` | `STAGE0_H4_D1_PRE_M1_SCOUT` |
| **`AUDJPY`** | `32` | `-3.90R` | `-0.5 / -3.4` · `2/7` · `7.9R` | **`+2183`** | `0.554` · `0.381` | `-0.0248` | `STAGE0_H4_D1_PRE_M1_SCOUT` |
| **`USDCAD`** | `30` | `+8.07R` | `+3.4 / +4.7` · `6/7` · `3.4R` | **`+590`** | `0.303` · `0.188` | `-0.003` | `STAGE0_H4_D1_PRE_M1_SCOUT` |
| **`USDCHF`** | `25` | `+3.27R` | `-1.3 / +4.6` · `4/7` · `5.8R` | **`+1670`** | `0.378` · `0.182` | `0.0359` | `STAGE0_H4_D1_PRE_M1_SCOUT` |
| **`USDJPY`** | `29` | `+16.21R` | `-5.9 / +22.1` · `4/7` · `6.8R` | **`+2078`** | `0.029` · `0.006` | `-0.0002` | `CONTROL_USDJPY` |

### Kết luận & Đề xuất Pass 20
1. **Lọc sạch 4/5 cặp không cần tải dữ liệu M1 lãng phí (`EURJPY`, `AUDJPY`, `USDCAD`, `USDCHF` rớt `EXP080_H4`)** — chỉ duy nhất **`GBPJPY`** qua Stage-0 `EXP080_H4` (`+9,28R`, Cụm A `+0,1` / B `+9,2`, `5/7` năm, thắng Fade `+28,5R`, tương quan `rJPY = 0,23`).
2. **Phát hiện nhánh Positive-Swap Carry-Trend (`DON20_POS`):** **`USDCAD`** đạt **`+8,07R` (`6/7` năm dương, A `+3,4` / B `+4,7`, DD chỉ `3,4R`, nhận `+$590` Swap dương, `rJPY = -0,003` — hoàn toàn trực giao với lõi `USDJPY`!)**; cả rổ 6 cặp Swap dương (`USDCAD`, `GBPJPY`, `USDCHF`, `USDJPY`, `EURJPY`, `AUDJPY`) đạt **`+28,7R` trên `177` lệnh và thu về `+$10.435` Swap dương FTMO** với tương quan ngày `~0,00` so với lõi trong ngày.
3. **Pass 20 ưu tiên:** Kiểm chứng chuyên sâu (M1/H1 + Floating Equity + Prague reset + độ bền tham số + kiểm tra trùng vị thế) cho **(a) Rổ Positive-Swap Carry-Trend (`USDCAD` + đa cặp Swap dương)** và **(b) tải M1 Bid/Ask cho `GBPJPY` để kiểm thật `EXP_DAILY_OPEN_080 GBPJPY`**.

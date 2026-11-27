# Pass 13 · Kiểm chứng 3 nhánh song song tìm Engine #2 (FX Liquidity Sweep · Clean-Room Intel · US500 Explicit M1)

- **Protocol khóa trước thực nghiệm:** [PASS13-TRIPLE-TRACK-ENGINE2-PROTOCOL-20261123.md](PASS13-TRIPLE-TRACK-ENGINE2-PROTOCOL-20261123.md) (commit `62ef313`)
- **Phạm vi dữ liệu:** Development UTC `2018-01-01` → `< 2025-01-01` · **Holdout `>= 2025-01-01` LOCKED (`holdout_rows = 0`)**
- **An toàn vận hành:** `network_calls = 0`, `OrderSend = 0`, không MT5, không đọc `.env`, `quant_test_suite` **`1514/1514 PASS (0 skip, 16.11s)`**
- **Kết luận tổng hợp:** **`ALL_THREE_TRACKS_REJECTED_ENGINE1_STILL_NEEDS_PARTNER`** · **`ORB_ENGINE2_SEARCH_EXHAUSTED`** (giữ Engine #1 `USDJPY` Pass 7B/8; không ứng viên nào đủ điều kiện ghép danh mục).

---

## Tóm tắt phán quyết 3 nhánh

| Nhánh / Ứng viên | Nguồn dữ liệu (UTC 2018–2024) | Kết quả Primary Stress | Monte Carlo Null (`N=1000`) | Phán quyết |
| --- | --- | --- | --- | --- |
| **Nhánh 1 · `GBPUSD` Liquidity Sweep** | Native Tick M1 Bid/Ask (`526,5M` ticks) | Stage-0 `-$37.302` · SL Flat `-275,5R` (`strict`) / `-335,1R` (`ext`) | `p = 0,705` (`strict`) / `0,778` (`ext`) | `GBPUSD_SWEEP_FAILED_M1_CHECK` |
| **Nhánh 1 · `EURUSD` Liquidity Sweep** | Native Tick M1 Bid/Ask (`190,0M` ticks) | Stage-0 `-$15.751` · SL Flat `-275,4R` (`strict`) / `-352,1R` (`ext`) | `p = 0,418` (`strict`) / `0,442` (`ext`) | `EURUSD_SWEEP_FAILED_M1_CHECK` |
| **Nhánh 2A · `NEN022` Fakey H4 (`EURUSD`)** | Native Tick M1 Bid/Ask | `Swing RR2 Stress_Mid`: `-25,61R` (`A -40,0 / B +14,4`) | 24h `p = 0,519` | `NEN022_EURUSD_FAILED_M1_CHECK` |
| **Nhánh 2A · `NEN022` Fakey H4 (`GBPUSD`)** | Native Tick M1 Bid/Ask | `Swing RR2 Stress_Mid`: `-42,29R` (`A -22,9 / B -19,4`) | 24h `p = 0,792` | `NEN022_GBPUSD_FAILED_M1_CHECK` |
| **Nhánh 2A · `NEN022` Fakey H4 (`XAUUSD`)** | QDM M1 Bid + Proxy Spread (`native_Ask=false`) | `Swing RR2 Stress_Mid`: `-74,91R` (`A -19,1 / B -55,9`) | 24h `p = 0,531` | `NEN022_XAUUSD_FAILED_M1_CHECK` |
| **Nhánh 2B · `SEA003` XAUUSD Turn-of-Month** | QDM M1 Bid + Proxy Spread + FTMO Swap 3× | Gross `+$42.023` → Swap `-$25.270` (`60,1%`) → Net `+$8.248` (`B -$69`) | Gross `p = 0,291` · Net `p = 0,279` | `SEA003_FAILED_RANDOM_ENTRY_NULL_DRIFT_ILLUSION` |
| **Nhánh 3 · `US500 NY ORB`** | Sealed Direct-Dukascopy Explicit M1 Bid/Ask | `M1_Stress_High`: Stage-0 `-1.186 pts` · SL `-46,66R` (`strict`) / `-58,89R` (`ext`) | `p = 0,072` (`strict`) / `0,069` (`ext`) | `US500_FAILED_EXPLICIT_M1_CHECK` |

---

## 1. Nhánh 1 · `GBPUSD` & `EURUSD` Intraday Liquidity Sweep & Reversal

- **Dữ liệu cục bộ (`network_calls = 0`):** `GBPUSD` đọc trực tiếp parquets Pass 11 (`1.310` ngày `strict` / `1.572` ngày `extended`); `EURUSD` xuất cục bộ từ `EURUSD_TICK_TW` (`190.030.407` ticks `2018–2024` → `2.607.359` nến M1 Bid/Ask, `1.198` `strict` / `1.550` `extended`).
- **Kết quả Stage-0 (`M1_Real_Stress_05`, `hard_flat 17:00` London, `swap = 0`):**
  - `GBPUSD`: `strict` (`n=1.213`) net `-$37.302` (`A -$33.640`, `B -$3.662`), `Fade` cũng âm `-$18.270`; `extended` (`n=1.449`) net `-$48.325`, `Fade -$17.638`.
  - `EURUSD`: `strict` (`n=1.072`) net `-$15.751` (`A -$4.869`, `B -$10.882`), `Fade -$20.659`; `extended` (`n=1.387`) net `-$21.421`, `Fade -$25.406`.
- **Kết quả SL cấu trúc (`sweep_extreme ± 2 pip`) & lưới ổn định tham số:**
  - `GBPUSD` (`Stress_05`): `Sweep_SL_Flat` `-275,50R` (`strict`, WR `10,3%`) / `-335,05R` (`extended`); `Sweep_SL_OppEdge` `-441,76R` / `-511,27R`. Toàn bộ 6/6 tổ hợp lưới ổn định (`box 00–07/00–08` × `buffer 1/2/3 pip`) âm nặng từ `-242,6R` đến `-538,9R`.
  - `EURUSD` (`Stress_05`): `Sweep_SL_Flat` `-275,36R` (`strict`, WR `12,0%`) / `-352,13R` (`extended`); `Sweep_SL_OppEdge` `-213,45R` / `-327,09R`. Toàn bộ 6/6 tổ hợp lưới ổn định âm từ `-320,2R` đến `-508,1R`.
- **Chẩn đoán cấu trúc:** Đóng nến M1 quay lại hộp Á/tiền London xảy ra trên `~90%` ngày giao dịch do nhiễu vi mô quanh biên tĩnh; cả breakout (Pass 11) lẫn sweep-reclaim M1 (Pass 13) đều thất bại vì không có lợi thế dịch chuyển/vĩ mô đủ bù chi phí ma sát và quét SL ngắn.

---

## 2. Nhánh 2 · Tái dựng Clean-Room Air-Gap từ `strategy-intel` (`NEN022` & `SEA003`)

### 2A. `NEN022` — Fakey H4 (2 chiều, kiểm đường đi M1 + FTMO Swap 3×)

| Tài sản | Nguồn | Raw Sigs | Stage-0 24h (`Stress_Mid`) | MC Null 24h | `Swing RR2.0 Stress_Mid` (`n`, WR, Net R, Cụm A/B) | `Standard FriFlat RR2.0 Stress_Mid` |
| --- | --- | ---: | ---: | ---: | --- | ---: |
| `EURUSD` | Native Tick M1 Bid/Ask | `407` | `-$12.828` (swap `-$2.503`) | `p = 0,519` | `n=384` · `34,9%` · **`-25,61R`** (`-40,00 / +14,39`) | **`-23,17R`** (`-31,76 / +8,59`) |
| `GBPUSD` | Native Tick M1 Bid/Ask | `436` | `-$30.373` (swap `-$2.993`) | `p = 0,792` | `n=407` · `32,4%` · **`-42,29R`** (`-22,86 / -19,44`) | **`-48,84R`** (`-21,10 / -27,73`) |
| `XAUUSD` | M1 Bid + Proxy Spread | `453` | `-$66.098` (swap `-$19.088`) | `p = 0,531` | `n=408` · `31,1%` · **`-74,91R`** (`-19,05 / -55,87`) | **`-73,64R`** (`-18,12 / -55,52`) |

- Cả 3 mức mục tiêu `RR ∈ {1,5; 2,0; 3,0}` và ngay cả mức phí `Base` đều âm nặng trên cả 3 tài sản (`EURUSD Base -11,80R`, `GBPUSD Base -32,24R`, `XAUUSD Base -37,42R`). Nhãn `"CHẤT"` từ blog công khai không sống sót khi tái dựng nhân quả trên M1.

### 2B. `SEA003` — `XAUUSD` Turn-of-Month (Pre-Mortem Swap 3× FTMO + Monte Carlo Null)

- **83 chu kỳ tháng (`2018-01` → `2024-11`, loại `2024-12` để khóa cứng Holdout `2025-01`):**
  - **Gross price change (`Bid-to-Bid`):** **`+$42.023 / lot`** (trông rất hấp dẫn nếu bỏ qua phí qua đêm và xu hướng nền của vàng).
  - **FTMO Swap thật (`swap_long = -$56,56/lot/đêm`, gồm `53` đêm thứ Tư `3×`):** **`-$25.270 / lot`** — ăn mất **`60,1%`** toàn bộ lợi nhuận gộp (`-$304,5 / lot / lệnh`).
  - **Phí thực thi (`Stress_Mid`: spread `$0,50` + slip `$0,25/chiều` + comm FTMO):** **`-$8.505 / lot`** (`$14.730` ở `Stress_High`).
  - **Net sau phí (`Unhedged_NoSL Stress_Mid`):** còn **`+$8.248 / lot`**, nhưng **Cụm B (`2021–2024`) đã âm (`-$69`)**, chỉ `4/7` năm dương, lỗ tệ nhất trong một lệnh **`-5,39%`**, closed DD **`$20.448 / lot`** (`2,5×` tổng lãi 7 năm). Biến thể `ATR14_SL2x` (`Stress_Mid`) cũng chỉ `4/7` năm dương với DD `$16.963 / lot` (`Stress_High` Cụm A âm `-$360`).
  - **Monte Carlo Random-Entry Null (`N = 1.000`, chọn ngẫu nhiên 1 ngày/tháng giữ đúng 5 phiên):** Vàng tăng thế kỷ `2018–2024` khiến vào ngẫu nhiên cũng lãi gộp trung bình `+$26.730 / lot` (`p95 = +$76.910`), nên **`gross p_value = 0,291`** và **`net p_value = 0,279` (`>> 0,05`)**. **Bác bỏ dứt khoát như ảo giác drift + bị Swap 3× bào mòn.**

---

## 3. Nhánh 3 · `US500 NY ORB` trên Explicit M1 Bid/Ask đã niêm phong (`2018–2024`)

- **Nguồn dữ liệu:** 28 file quý `q1..q4-{bid,ask}.json` đã xác thực SHA-256 (`us500-long-explicit-source-v1/2018..2021` + `us500-explicit-source-v1/2022..2024`), `1.378` ngày `strict` (`1.316` lệnh) / `1.418` ngày `extended` (`1.351` lệnh). Observed spread giờ mở cửa NYSE: `mean = 0,436 pt`, `p50 = 0,463 pt`, `p90 = 0,532 pt`, `p95 = 0,709 pt`.

| Bậc phí (`US500 NY ORB`, `extended` `n=1.351`) | Stage-0 Net (`hard_flat`) | Stage-0 Fade | SL Net R (Cụm A / B) | Floating DD R · Underwater | Swing 10k `0,30%` (Net · Peak DD) |
| --- | ---: | ---: | ---: | ---: | ---: |
| `M1_Base` (`0,25 pt/chiều`) | `+105,3 pts` | `-2.670,8 pts` | `+10,70R` (`-10,90 / +21,61`) | `48,1R` · `80,0 tháng` | `+$345` · `13,75%` |
| `M1_Stress_Mid` (`0,50 pt/chiều`) | `-570,2 pts` | `-3.346,3 pts` | **`-24,09R`** (`-24,75 / +0,66`) | `64,9R` · `80,0 tháng` | `-$612` · `17,83%` |
| **`M1_Stress_High` (`0,75 pt/chiều`, primary)** | **`-1.245,7 pts`** | `-4.021,8 pts` | **`-58,89R`** (`-38,60 / -20,29`) | `82,1R` · `80,8 tháng` | **`-$1.519` · `21,83%`** |
| Đối chứng `Fade` + SL (`M1_Stress_High`) | — | — | **`-247,12R`** (`-68,77 / -178,34`) | `252,3R` · `83,2 tháng` | — |

- Ở `strict` (`M1_Stress_High`), chỉ có **1/7 năm dương** (`2022: +589,2 pts`; 6 năm còn lại đều âm), SL đạt `-46,66R` (`A -23,39R / B -23,28R`), Monte Carlo Null `p = 0,072` (`strict`) / `0,069` (`extended`).
- **Phán quyết khép vòng ORB:** Kết hợp với Pass 11 (`GBPUSD` London ORB trượt), dòng Opening Range Breakout cho Engine #2 chính thức khép lại: **`ORB_ENGINE2_SEARCH_EXHAUSTED`**.

---

## 4. Hướng đi Pass 14 (Thoát hoàn toàn khỏi bẫy ORB / pattern nến đơn lẻ / swap âm dài ngày)

Ba bài học cốt lõi đã chứng minh trên M1 thực:
1. **Không lặp lại static-box ORB hay sweep M1 đơn thuần trên `EURUSD`/`GBPUSD`/`US500`** và **không giữ Long `XAUUSD` nhiều đêm** (swap `-$56,56/đêm`, thứ Tư `3×` phá hủy hầu hết alpha yếu).
2. **Engine #1 (`USDJPY` Tokyo-box)** có điểm yếu giải phẫu rõ (Pass 12): rơi vào DD `41 tháng` trong giai đoạn `2019–2021` (low-volatility / range compression, chiều `SELL` lỗ nặng trong khi `BUY` chịu đựng tốt hơn).
3. **3 hướng Engine #2 thực sự khác cơ chế (orthogonal) nên mở ở Pass 14:**
   - **Ứng viên A — Volatility-Breakout / Session Trend-Follow trên `XAUUSD` Intraday (`swap = 0`):** Vàng có biến động phiên London–NY cực lớn (tỷ lệ `cost/ATR` thấp nhất toàn sàn) và đóng lệnh trong ngày tránh hoàn toàn `-$56,56` swap qua đêm; tập trung kiểm định đột phá cấu trúc biến động (`Donchian / ATR Expansion / London–NY Trend Continuation`, 2 chiều, `hard_flat` trước `17:00 NY`).
   - **Ứng viên B — Cross-Pair FX Carry-Aligned Swing (`EURUSD` Short / `USDJPY` Long hoặc Relative-Strength Multi-Day):** Tận dụng **chính chiều swap dương hoặc trung tính** của FTMO (`EURUSD swap_short = +0,28`, `USDJPY swap_long > 0`, `GBPJPY/AUDJPY swap_long > 0`) để tài trợ phí giữ lệnh thay vì bị swap âm ăn mòn như `SEA003`.
   - **Ứng viên C — Intraday Mean-Reversion có điều kiện cực trị (Volatility-Normalized Z-Score / VWAP-Session Deviation) trên `US500` hoặc `EURUSD`/`GBPUSD`:** Chỉ vào lệnh khi giá lệch quá `>= 2,0–2,5σ` trong phiên (tần suất thấp `30–60` lệnh/năm, `cost/stop < 8%`) thay vì đánh 90% số ngày như sweep biên tĩnh.

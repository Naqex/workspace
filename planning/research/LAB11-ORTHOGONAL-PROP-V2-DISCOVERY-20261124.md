---
title: "Lab #11: Khám Phá Chiến Lược Prop v2 Không Trùng Kiểu Phá Vỡ & Tài Sản Mới (Dev 2018–2024)"
date: "2026-11-24"
lane: "Lane C (quant-rnd)"
cycle: "Wave-3 Cycle 1"
status: "COMPLETE — ZERO_APPROVED_KEEP_A1_V1_LIVE8 (0/20 Đạt Đủ 6 Cổng Phản Biện)"
holdout_rows_analysed: 0
order_send_count: 0
---

# Lab #11 — Khám Phá Chiến Lược Prop v2 Không Trùng Kiểu Phá Vỡ & Tài Sản Mới (`2018–2024`)

> **Kết luận trung thực (`ZERO_APPROVED_KEEP_A1_V1_LIVE8`):** Quét có đăng ký trước toàn bộ `m_total = 20` giả thuyết hộp trắng (`swap = 0`, cắt lỗ cứng, không lưới/gấp thếp) thuộc `4` họ chiến lược hoàn toàn khác kiểu phá vỡ trên dữ liệu M1 Bid/Ask thật giai đoạn phát triển **`2018-01-02..2024-12-31`** (`Holdout 2025+` khóa kín tuyệt đối, `holdout_rows_analysed = 0`, `Holdout Lock SHA-256 = f0a6b43cb205535b...`, đã áp dụng bộ lọc tin đỏ `±5 phút` 2018–2024). **Kết quả thực tế: `0/20` ứng viên vượt qua đủ `6` cổng phản biện đỏ (`APPROVE_FOR_INCUBATION`).** Toàn bộ `20/20` đều đạt độ độc lập cực cao (`|r| <= 0,063` với đội hình gốc `A1_V1_LIVE8`), nhưng hầu hết mất lợi thế sau khi trừ chênh giá mua/bán thực và trượt giá; chỉ có `2` ứng viên tiệm cận (`L11_C2_GER40_CASH_OR30_FADE` và `L11_A3_USDCAD_NY_VWAP_FADE`) nhưng đều trượt cổng ổn định năm hoặc số lệnh tối thiểu và không vượt kiểm định đa giả thuyết (`BH q = 0,32–0,70`). **Quyết định: Giữ nguyên đội hình gốc `A1_V1_LIVE8` (không gượng ép sửa tham số để lách cổng!).**

---

## 1. Thiết Kế Khám Phá & Hàng Rào Chống Ảo Giác

- **Mục tiêu chiến lược ([TOP1-SOLO-QUANT-MASTER-PLAN.md](../TOP1-SOLO-QUANT-MASTER-PLAN.md)):** Bộ `8` bot đang chạy (`A1_V1_LIVE8`: `E1..E7 + S6`) đều đi theo cơ chế **phá vỡ / thuận xu hướng trong ngày** trên `USDJPY, GBPUSD, EURJPY, US100, USD-Basket`. Lab #11 tìm các động cơ **đảo chiều trong ngày / tài sản mới** có tương quan ngày **`|r| < 0,25`** với `A1_V1_LIVE8` để kiểm tra xem có thể rút ngắn thời gian đậu quỹ từ `~5–6 tháng` xuống `2–3 tháng` hay không.
- **Dữ liệu & Kỷ luật chống nhìn trộm tương lai:**
  - Nguồn dữ liệu duy nhất: `.runtime/hot-m1-cache/` (12 mã M1 Bid/Ask thật 7 năm, xác minh mọi mốc thời gian `< 2025-01-01T00:00:00Z`).
  - Phân tách mẫu khóa cứng: **Cluster A (`2018–2020`, `3` năm)** -> **Blind Cluster B (`2021–2024`, `4` năm)**, theo dõi đủ `m_total = 20` bằng `Sign-Flip Null`, `Bonferroni`, `BH-FDR` và `Deflated Sharpe Ratio (DSR)`.
  - Mọi chỉ báo khung ngày (`ATR14`, giá đóng/mở hôm trước) đều dịch trễ cứng `shift = 1` (chỉ dùng ngày đã đóng `<= t-1`); mọi tín hiệu trong ngày chỉ đọc nến đã đóng trước thời điểm vào lệnh; xử lý chạm đồng thời SL & TP trên cùng 1 nến M1 theo chiều **bảo thủ SL khớp trước TP**; đóng lệnh bắt buộc trước `20:50 UTC` để đảm bảo **`swap = 0`**; và áp dụng lọc tin đỏ chính thức `2018–2024` (`±300s` `FLATTEN_5M`) cho cả `20` ứng viên.
- **6 cổng phản biện đỏ bắt buộc (trượt 1 cổng -> loại thẳng):**
  1. **Cổng 1 (`G1_CLB_PF_OR_N`):** Blind Cluster B (`2021–2024`) phải đạt `PF >= 1,15`, lãi ròng dương và `>= 60` lệnh (`>= 15` lệnh/năm) ở mức phí `1,0×`.
  2. **Cổng 2 (`G2_STRESS_15X`):** Sống khỏe có lãi trên Blind Cluster B dưới áp lực trượt giá & phí **`1,5×`** (`Ann_ClB_15x > 0`).
  3. **Cổng 3 (`G3_ORTHOGONALITY`):** Tương quan ngày **`|r| < 0,25`** so với tổng `A1_V1_LIVE8` và **`< 0,35`** so với từng bot lẻ mạnh nhất trong bộ 8 bot.
  4. **Cổng 4 (`G4_YEAR_STABILITY`):** Có ít nhất **`5/7` năm dương** (`2018–2024`) và không có 1 năm đơn lẻ nào gánh quá **`60%`** tổng lợi nhuận.
  5. **Cổng 5 (Kiểm thử ghép danh mục Prop `10.000` kịch bản):** Chạy Block-Bootstrap Monte Carlo (`seed = 20261124`) trên `FTMO Swing 10K` và `The5ers High Stakes 5K` với **`P1_Balanced` đã siết trần 1 mã `SYMCAP = 1,75%`** và **`Dyn_ProfitLock`**.
  6. **Cổng 6 (Trung thực tuyệt đối):** Không chỉnh sửa tham số sau khi thấy số liệu Blind Cluster B; giữ nguyên toàn bộ kết quả âm/thất bại để tích lũy tri thức thật.

---

## 2. Bảng Kết Quả Đầy Đủ `m_total = 20` Ứng Viên (Khớp 100% Với JSON Receipt)

Mã nguồn: [lab11_orthogonal_prop_v2_discovery.py](../../tooling/ai-engines/quant_factory/lab11_orthogonal_prop_v2_discovery.py) · Kiểm thử: [test_lab11_orthogonal_prop_v2.py](../../tooling/ai-engines/tests/test_lab11_orthogonal_prop_v2.py) · Biên nhận JSON: [LAB11-ORTHOGONAL-PROP-V2-DISCOVERY-20261124.json](LAB11-ORTHOGONAL-PROP-V2-DISCOVERY-20261124.json).

| Mã Ứng Viên | Tài Sản | Cl.A n | Cl.A PF | Cl.B n | Cl.B PF | Cl.B R (1x) | Cl.B aR (1.5x) | Năm Dương | Max Năm % | r(LIVE8) | Max r Bot | pSF Cl.B | Bonf p | BH q | DSR | Phán Quyết | Cổng Trượt |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| `L11_A1_EURUSD_LDN_STRETCH_FADE` | EURUSD | 43 | 0.51 | 47 | 0.75 | -3.51 | -1.03 | 1/7 | 100.0% | -0.050 | -0.249 | 0.6933 | 1.0000 | 1.0000 | 0.004 | `REJECT_KILLED` | G1_CLB_PF_OR_N, G2_STRESS_15X, G4_YEAR_STABILITY |
| `L11_A2_AUDUSD_ASIA_LDN_FADE` | AUDUSD | 71 | 0.67 | 81 | 0.86 | -3.42 | -1.17 | 1/7 | 100.0% | -0.059 | -0.060 | 0.4086 | 1.0000 | 1.0000 | 0.005 | `REJECT_KILLED` | G1_CLB_PF_OR_N, G2_STRESS_15X, G4_YEAR_STABILITY |
| `L11_A3_USDCAD_NY_VWAP_FADE` | USDCAD | 51 | 1.12 | 59 | 1.27 | +4.47 | +0.88 | 5/7 | 43.6% | -0.023 | -0.092 | 0.0789 | 1.0000 | 0.7043 | 0.107 | `REJECT_KILLED` | G1_CLB_PF_OR_N |
| `L11_A4_US500_OPEN_STRETCH_FADE` | US500 | 41 | 0.49 | 61 | 0.70 | -7.19 | -2.07 | 1/7 | 100.0% | -0.005 | -0.127 | 0.7822 | 1.0000 | 1.0000 | 0.002 | `REJECT_KILLED` | G1_CLB_PF_OR_N, G2_STRESS_15X, G4_YEAR_STABILITY |
| `L11_A5_GER40_MIDDAY_VWAP_FADE` | GER40 | 20 | 0.68 | 17 | 0.51 | -3.71 | -0.98 | 0/7 | 100.0% | +0.010 | +0.031 | 0.8342 | 1.0000 | 1.0000 | 0.001 | `REJECT_KILLED` | G1_CLB_PF_OR_N, G2_STRESS_15X, G4_YEAR_STABILITY |
| `L11_B1_XAU_ASIA_SWEEP_LDN_REV` | XAUUSD | 39 | 0.87 | 35 | 0.65 | -2.84 | -0.82 | 1/7 | 100.0% | -0.023 | -0.061 | 0.6054 | 1.0000 | 1.0000 | 0.000 | `REJECT_KILLED` | G1_CLB_PF_OR_N, G2_STRESS_15X, G4_YEAR_STABILITY |
| `L11_B2_XAU_LDN_AM_FIX_DRIFT` | XAUUSD | 159 | 0.63 | 171 | 0.82 | -6.61 | -2.22 | 1/7 | 100.0% | +0.032 | +0.075 | 0.5375 | 1.0000 | 1.0000 | 0.003 | `REJECT_KILLED` | G1_CLB_PF_OR_N, G2_STRESS_15X, G4_YEAR_STABILITY |
| `L11_B3_XAU_COMEX_OPEN_MR` | XAUUSD | 43 | 0.47 | 90 | 0.66 | -11.00 | -3.06 | 0/7 | 100.0% | -0.046 | -0.045 | 0.8491 | 1.0000 | 1.0000 | 0.000 | `REJECT_KILLED` | G1_CLB_PF_OR_N, G2_STRESS_15X, G4_YEAR_STABILITY |
| `L11_B4_XAU_COMEX_CLOSE_MOM` | XAUUSD | 106 | 0.64 | 201 | 0.73 | -10.59 | -3.35 | 1/7 | 100.0% | +0.054 | +0.073 | 0.6224 | 1.0000 | 1.0000 | 0.000 | `REJECT_KILLED` | G1_CLB_PF_OR_N, G2_STRESS_15X, G4_YEAR_STABILITY |
| `L11_B5_XAU_PM_FIX_REVERT` | XAUUSD | 128 | 0.60 | 221 | 0.69 | -18.77 | -5.49 | 1/7 | 100.0% | -0.063 | -0.085 | 0.8062 | 1.0000 | 1.0000 | 0.000 | `REJECT_KILLED` | G1_CLB_PF_OR_N, G2_STRESS_15X, G4_YEAR_STABILITY |
| `L11_C1_GER40_CASH_OR30_MOM` | GER40 | 159 | 1.06 | 254 | 0.69 | -24.96 | -7.00 | 1/7 | 100.0% | -0.040 | -0.067 | 0.8971 | 1.0000 | 1.0000 | 0.000 | `REJECT_KILLED` | G1_CLB_PF_OR_N, G2_STRESS_15X, G4_YEAR_STABILITY |
| `L11_C2_GER40_CASH_OR30_FADE` | GER40 | 49 | 0.71 | 74 | 1.55 | +9.07 | +1.94 | 5/7 | 131.6% | +0.038 | +0.073 | 0.0160 | 0.3197 | 0.3197 | 0.354 | `NEAR_MISS_REJECTED` | G4_YEAR_STABILITY |
| `L11_C3_GER40_VS_US500_REL_MR` | GER40 | 34 | 0.86 | 63 | 0.63 | -4.26 | -1.31 | 2/7 | 100.0% | -0.041 | -0.036 | 0.7423 | 1.0000 | 1.0000 | 0.000 | `REJECT_KILLED` | G1_CLB_PF_OR_N, G2_STRESS_15X, G4_YEAR_STABILITY |
| `L11_C4_GER40_VS_US500_LEADLAG` | GER40 | 84 | 0.77 | 67 | 0.31 | -18.02 | -4.67 | 1/7 | 100.0% | +0.056 | +0.141 | 0.9970 | 1.0000 | 1.0000 | 0.000 | `REJECT_KILLED` | G1_CLB_PF_OR_N, G2_STRESS_15X, G4_YEAR_STABILITY |
| `L11_C5_GER40_PRE_US_DRIFT` | GER40 | 205 | 0.89 | 285 | 0.99 | -0.39 | -1.08 | 3/7 | 100.0% | +0.003 | +0.077 | 0.1149 | 1.0000 | 0.7043 | 0.023 | `REJECT_KILLED` | G1_CLB_PF_OR_N, G2_STRESS_15X, G4_YEAR_STABILITY |
| `L11_D1_BTC_WEEKEND_MR_FADE` | BTCUSD | 12 | 0.54 | 12 | 1.86 | +2.93 | +0.65 | 2/7 | 738.6% | +0.000 | +0.000 | 0.1409 | 1.0000 | 0.7043 | 0.153 | `REJECT_KILLED` | G1_CLB_PF_OR_N, G4_YEAR_STABILITY |
| `L11_D2_BTC_US_OPEN_MOM` | BTCUSD | 33 | 0.22 | 65 | 0.67 | -6.50 | -2.00 | 1/7 | 100.0% | +0.019 | +0.064 | 0.5045 | 1.0000 | 1.0000 | 0.001 | `REJECT_KILLED` | G1_CLB_PF_OR_N, G2_STRESS_15X, G4_YEAR_STABILITY |
| `L11_D3_BTC_ASIA_STRETCH_FADE` | BTCUSD | 57 | 0.28 | 83 | 0.45 | -22.54 | -5.96 | 1/7 | 100.0% | +0.016 | +0.050 | 0.9770 | 1.0000 | 1.0000 | 0.000 | `REJECT_KILLED` | G1_CLB_PF_OR_N, G2_STRESS_15X, G4_YEAR_STABILITY |
| `L11_D4_GBPJPY_LDN_OVEREXT_FADE` | GBPJPY | 10 | 4.73 | 9 | 1.55 | +1.69 | +0.40 | 5/7 | 27.6% | -0.009 | -0.108 | 1.0000 | 1.0000 | 1.0000 | 0.087 | `REJECT_KILLED` | G1_CLB_PF_OR_N |
| `L11_D5_GBPJPY_PRIOR_DAY_REV` | GBPJPY | 48 | 2.11 | 58 | 0.48 | -13.12 | -3.36 | 4/7 | 100.0% | +0.051 | +0.058 | 0.9530 | 1.0000 | 1.0000 | 0.000 | `REJECT_KILLED` | G1_CLB_PF_OR_N, G2_STRESS_15X, G4_YEAR_STABILITY |

---

## 3. Kiểm Thử Ghép Danh Mục Prop (`10.000` Kịch Bản Block Bootstrap, `SYMCAP = 1,75%`)

Vì `0/20` ứng viên đạt chuẩn `APPROVE_FOR_INCUBATION`, bảng dưới đây đo chính xác hiệu năng của đội hình gốc **`A1_V1_LIVE8_BASE`** (trên toàn bộ lịch Mon–Fri chuẩn `2018–2024`, có lọc tin đỏ `±5 phút`, trần `SYMCAP 1,00%` khi Funded và trần siết **`SYMCAP 1,75%`** ở Vòng 1 theo Bản vá #3), kèm `2` kịch bản **chẩn đoán giả định (CHỈ ĐỂ ĐO TÁC ĐỘNG, KHÔNG THĂNG HẠNG)** khi ghép thêm 1 hoặc 2 ứng viên tiệm cận tốt nhất (`L11_C2_GER40_CASH_OR30_FADE` và `L11_A3_USDCAD_NY_VWAP_FADE`).

### 3.1. Hiệu Năng Danh Mục M1 Gốc (`Funded_Safe 1,0×`, `SYMCAP 1,00%`)

| Danh Mục | Số Bot | Lãi Năm 1x | Sharpe 1x | Sụt Sâu Nhất | Calmar 1x | Calmar 1.5x | Lần Chạm Trần P1 (1.75%) |
|---|---:|---:|---:|---:|---:|---:|---:|
| `A1_V1_LIVE8_BASE` | 8 | 8.63% | 1.33 | 9.52% | 0.91 | 0.47 | 1851 |
| `DIAG_COUNTERFACTUAL_TOP1_UNAPPROVED` | 9 | 8.85% | 1.32 | 9.21% | 0.96 | 0.48 | 1974 |
| `DIAG_COUNTERFACTUAL_TOP2_UNAPPROVED` | 10 | 9.22% | 1.37 | 8.32% | 1.11 | 0.55 | 2084 |

### 3.2. Kết Quả Mô Phỏng Vòng Thi Quỹ (`10.000` Đường, `seed = 20261124`)

| Danh Mục | Gói Quỹ | Chế Độ Vòng 1 | Đậu 3m / 6m / 12m | Trung Vị Đậu | Rớt Bất Kỳ | Cháy 5 Vé | Lãi Ròng 24m (EV) | Hiệu Quả / Phí Vé |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `A1_V1_LIVE8_BASE` | FTMO_SWING_10K | `P1_Balanced_SymCap175` | 11.7% / 33.5% / 53.6% | 137d | 0.6% | 0.00% | +646.5 USD | 3.85x |
| `A1_V1_LIVE8_BASE` | FTMO_SWING_10K | `Dyn_ProfitLock_SymCap175` | 12.7% / 33.8% / 51.9% | 130d | 1.0% | 0.00% | +626.4 USD | 3.73x |
| `A1_V1_LIVE8_BASE` | THE5ERS_HS_5K | `P1_Balanced_SymCap175` | 11.6% / 33.3% / 53.5% | 137d | 0.6% | 0.00% | +328.7 USD | 8.43x |
| `A1_V1_LIVE8_BASE` | THE5ERS_HS_5K | `Dyn_ProfitLock_SymCap175` | 12.2% / 33.5% / 51.8% | 131d | 1.0% | 0.00% | +319.9 USD | 8.20x |
| `DIAG_COUNTERFACTUAL_TOP1_UNAPPROVED` | FTMO_SWING_10K | `P1_Balanced_SymCap175` | 12.6% / 33.1% / 51.6% | 136d | 0.8% | 0.00% | +641.3 USD | 3.82x |
| `DIAG_COUNTERFACTUAL_TOP1_UNAPPROVED` | FTMO_SWING_10K | `Dyn_ProfitLock_SymCap175` | 13.7% / 34.2% / 50.9% | 128d | 1.1% | 0.00% | +635.2 USD | 3.78x |
| `DIAG_COUNTERFACTUAL_TOP1_UNAPPROVED` | THE5ERS_HS_5K | `P1_Balanced_SymCap175` | 12.4% / 33.0% / 51.5% | 137d | 0.8% | 0.00% | +327.0 USD | 8.38x |
| `DIAG_COUNTERFACTUAL_TOP1_UNAPPROVED` | THE5ERS_HS_5K | `Dyn_ProfitLock_SymCap175` | 13.4% / 34.1% / 50.9% | 129d | 1.1% | 0.00% | +324.6 USD | 8.32x |
| `DIAG_COUNTERFACTUAL_TOP2_UNAPPROVED` | FTMO_SWING_10K | `P1_Balanced_SymCap175` | 13.5% / 33.0% / 51.6% | 137d | 0.9% | 0.00% | +669.7 USD | 3.99x |
| `DIAG_COUNTERFACTUAL_TOP2_UNAPPROVED` | FTMO_SWING_10K | `Dyn_ProfitLock_SymCap175` | 14.3% / 34.6% / 51.4% | 127d | 1.1% | 0.00% | +669.0 USD | 3.98x |
| `DIAG_COUNTERFACTUAL_TOP2_UNAPPROVED` | THE5ERS_HS_5K | `P1_Balanced_SymCap175` | 13.3% / 32.9% / 51.5% | 138d | 0.9% | 0.00% | +341.2 USD | 8.75x |
| `DIAG_COUNTERFACTUAL_TOP2_UNAPPROVED` | THE5ERS_HS_5K | `Dyn_ProfitLock_SymCap175` | 14.0% / 34.4% / 51.3% | 127d | 1.1% | 0.00% | +341.2 USD | 8.75x |

---

## 4. 5 Bài Học Thực Chiến Rút Ra Từ Dữ Liệu Thật (Tránh Lặp Lại Vết Xe Đổ)

1. **Vàng (`XAUUSD`) trong ngày (`0/5` sống sót):** Cả `2` hướng thuận xu hướng quanh phiên London AM Fix / COMEX (`L11_B2`, `L11_B4`: Cl.B `PF = 0,73–0,82`) lẫn `3` hướng đánh đảo chiều (`L11_B1`, `L11_B3`, `L11_B5`: Cl.B `PF = 0,65–0,69`) đều thua lỗ đều đặn qua `6/7` năm. Chẩn đoán lệnh đối xứng (`fade_R`) cho thấy biên lợi nhuận thuần của Vàng quanh các mốc giờ cố định gần như bằng `0`, nên toàn bộ `170–220` lệnh trong Blind Cl.B bị bào mòn trực tiếp bởi chênh giá + trượt giá (`~3,2%` khoảng SL mỗi lệnh).
2. **`BTCUSD` CFD trong ngày trên sàn quỹ (`0/3` sống sót — Bỏ hẳn):** Dù giao dịch cả cuối tuần (`r = 0,000` với FX!), dữ liệu M1 thật cho thấy tổng chi phí chênh giá (`4,91%` SL) + trượt giá stress (`7,09%` SL) lên tới **`12,0%` khoảng cắt lỗ cho mỗi lệnh** — giết sạch mọi chiến lược đóng trong ngày (`L11_D2 PF = 0,67`, `L11_D3 PF = 0,45` lỗ `-22,54R`). Lợi thế Crypto chỉ thực sự tồn tại trên sàn giao ngay/perpetual (`S2`, `S3A` khung `4H–D1`), không phù hợp để đánh CFD trong ngày trên tài khoản quỹ.
3. **`GER40` (DAX) cho tín hiệu đảo chiều mở cửa sáng giá nhất nhưng chưa đủ ổn định (`NEAR_MISS_REJECTED`):** Trong khi đánh thuận theo mở cửa Xetra (`L11_C1 PF = 0,69`, `-24,96R`) và đánh đuổi theo nhịp Mỹ đêm qua (`L11_C4 PF = 0,31`, `-18,02R`) đều gãy nặng (vì thị trường châu Âu mở cửa đã phản ánh xong tin Mỹ!), chiến lược ngược lại **`L11_C2_GER40_CASH_OR30_FADE`** (bán/mua đảo chiều khi 30 phút mở cửa Xetra giật `>= 0,40 ATR`) đạt **`PF = 1,55`**, **`+9,07R`**, sống tốt ở `1,5×` (`+1,94R/năm`), `p_signflip = 0,0160`, `r(LIVE8) = +0,038`. Tuy nhiên nó thua ở `2018–2020` (`PF = 0,71`) khiến 1 năm gánh `131,6%` tổng lãi ròng 7 năm và `BH q = 0,3197` chưa qua ngưỡng `0,10` -> giữ trong sổ theo dõi nghiên cứu, **không duyệt chạy thật**.
4. **Cẩn trọng với bẫy "suýt đậu" ở `L11_A3_USDCAD_NY_VWAP_FADE`:** Đây là ứng viên hiếm hoi dương cả Cl.A (`PF = 1,12`) lẫn Cl.B (`PF = 1,27`, `1,5× = +0,88R/năm`, `5/7` năm dương, `max_yr_share = 43,6%`, `r = -0,023`), chỉ thiếu đúng **`1` lệnh (`59 < 60`)** ở Cổng 1. Theo kỷ luật khoa học, ta **tuyệt đối không hạ ngưỡng `0,45 -> 0,44`** để cố ép đủ `60` lệnh vì kiểm định đa giả thuyết (`BH q = 0,7043`, `DSR = 0,107`) cho thấy cạnh tranh thống kê vẫn quá mỏng.
5. **Tác động cực quan trọng của trần `SYMCAP = 1,75%` lên tốc độ đậu quỹ:** Khi siết trần rủi ro đồng thời 1 mã xuống `1,75%` ở Vòng 1 (chạm trần `1.851` lần trong 7 năm trên `A1_V1_LIVE8`), tỷ lệ rớt vé giảm mạnh từ `~22%` xuống chỉ còn **`0,6%–1,0%`** (`0,00%` cháy 5 vé, hiệu quả đồng phí đạt **`8,43×` trên The5ers 5K** và **`3,85×` trên FTMO 10K**!), nhưng đổi lại thời gian đậu trung vị kéo dài thành `130–137` phiên (~6,2–6,5 tháng). Thậm chí kể cả khi ghép giả định cả 2 ứng viên tiệm cận tốt nhất (`DIAG_COUNTERFACTUAL_TOP2`), tốc độ đậu cũng chỉ nhanh hơn `3–4` phiên (`130d -> 127d`), trong khi Calmar tăng khá rõ (`0,91 -> 1,11`, sụt giảm sâu nhất hạ từ `9,52% -> 8,32%`).

---

## 5. Khuyến Nghị Hành Động Tiếp Theo Cho Chu Kỳ 2

1. **Giữ nguyên `A1_V1_LIVE8` làm đội hình chính trên tài khoản quỹ** (không pha loãng bằng các chiến lược đảo chiều yếu hoặc chưa qua đa kiểm định).
2. **Đường thực tế nhất để tiến tới mốc đậu `2–3` tháng & Sharpe `2,0–3,0` (như [TOP1-SOLO-QUANT-MASTER-PLAN.md](../TOP1-SOLO-QUANT-MASTER-PLAN.md)):**
   - **Trên Prop:** Kết hợp chạy song song lệch pha `DUAL_2FIRM_STAGGER_42D` (`The5ers 5K` -> `FTMO Swing 25K/50K`), rà soát lại biên tối ưu `SYMCAP` giữa `1,75%` (rớt `0,6%`, chậm) và `2,00%–2,25%` (giữ rớt vùng vàng `15%–25%` nhưng nhanh hơn rõ rệt), và tiếp tục săn chiến lược v2 ở các cơ chế có tần suất cao hơn (`>= 50–100` lệnh/năm, ví dụ cấu trúc biến động nén phiên Âu/Á hoặc tương đối đa cặp tiền tệ thay vì đón đầu giật nến đơn lẻ).
   - **Trên Sổ Vốn Riêng (Own-Book):** Đẩy nhanh nguồn tiền hoàn toàn độc lập ngoài FX intraday (`S2 Crypto Spot`, `S3A Funding BTC+ETH`, `S3B/S4 ETF IBKR`), nơi khung giữ lệnh `4H–D1` không bị chi phí chênh giá trong ngày bào mòn.

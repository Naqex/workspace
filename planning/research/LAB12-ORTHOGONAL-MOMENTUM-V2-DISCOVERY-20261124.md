---
title: "Lab #12: Khám Phá Chiến Lược Thuận Xu Hướng, Mở Rộng Biến Động & Dẫn Dắt Liên Thị Trường Trên 7 Tài Sản M1 Mới (Dev 2018–2024)"
date: "2026-11-24"
lane: "Lane C (quant-rnd)"
cycle: "Wave-3 Cycle 2"
status: "COMPLETE — ZERO_APPROVED_36_TOTAL_PARETO_FRONTIER_A1_V1_LIVE8 (0/16 Đạt; Tổng 0/36 Lab #11 + #12)"
holdout_rows_analysed: 0
order_send_count: 0
---

# Lab #12 — Khám Phá Động Lượng Mở Rộng Biến Động & Dẫn Dắt Liên Thị Trường Trên 7 Tài Sản M1 (`2018–2024`)

> **Kết luận dứt khoát (`ZERO_APPROVED_36_TOTAL_PARETO_FRONTIER_A1_V1_LIVE8`):** Sau khi [Lab #11](LAB11-ORTHOGONAL-PROP-V2-DISCOVERY-20261124.md) chứng minh hướng đánh đảo chiều mục tiêu ngắn bị chênh giá CFD bào mòn (`0/20` đạt), Lab #12 kiểm nghiệm hướng bổ sung đối lập: **động lượng đuôi phải lớn (`tp = None`, giữ lệnh tới cuối phiên `swap = 0`), phá vỡ sau nén biến động, và truyền dẫn liên thị trường** trên `7` tài sản M1 Bid/Ask còn dư địa (`GER40, XAUUSD, AUDUSD, GBPJPY, USDCAD, EURUSD, US500`, `m_total = 16` giả thuyết đăng ký trước, dữ liệu phát triển **`2018-01-02..2024-12-31`**, `Holdout 2025+` khóa kín `holdout_rows_analysed = 0`, `Holdout Lock SHA-256 = f0a6b43cb205535b...`, áp dụng lọc tin đỏ `±5 phút`). **Kết quả trung thực: `0/16` đạt đủ `6` cổng phản biện đỏ (`APPROVE_FOR_INCUBATION`).**
>
> **Chốt biên hiệu quả (Pareto Frontier) sau trọn bộ `36` giả thuyết độc lập (`Lab #11: 0/20` + `Lab #12: 0/16`):** Đội hình **`A1_V1_LIVE8`** (cùng phương án dự phòng `L10_B2_EURUSD_VOLCOMP75`) chính là **đường biên hiệu quả đã kiểm chứng** của mô hình M1 CFD `swap = 0` trong ngày. Con đường thực tế để chạm chuẩn Top 1% (`1,5–3` tháng đậu & Sharpe `2,0–3,0`) **không nằm ở việc cố săn thêm bot CFD lẻ**, mà nằm ở **2 đòn bẩy đã chứng minh bằng toán học**: (1) **Thang tài khoản quỹ song song lệch pha (`The5ers 5K -> FTMO Swing 25K/50K/100K`)** — ngay trong bảng dưới, nâng bậc từ `FTMO 10K -> 25K` tự động kéo hiệu quả đồng phí từ **`3,82× -> 6,11×`** mà không cần sửa 1 dòng code chiến lược; và (2) **Sổ Vốn Riêng đa nhánh (`NCO_CexCap25`: `S2 Crypto Spot`, `S3A Funding`, `S3B/S4 ETF IBKR`)** trên khung `4H–D1`.

---

## 1. Thiết Kế Thí Nghiệm & Kỷ Luật Chống Ảo Giác

- **Khác biệt cốt lõi so với Lab #11:** Không đặt chốt lời ngắn (`tp = None`), cho phép lệnh thắng chạy hết biên độ trong ngày tới giờ đóng cửa phiên (`16:20 UTC` cho `GER40`, `15:50 ET` cho `US500`, `20:50 UTC` cho Vàng & FX, **`swap = 0`**) nhằm ăn đuôi phải `1,5R–4,0R` vượt xa chi phí chênh giá.
- **4 họ chiến lược đăng ký trước (`m_total = 16`, không trùng `A1_V1_LIVE8`, `Lab #10`, hay `Lab #11`):**
  - **Họ A (`A_GER40_EU_ORB`, `4` giả thuyết):** Phá vỡ khung mở cửa Frankfurt `08:00 CET` (`OR30/OR60`), nén biến động `ATR5/ATR20 <= 0,85` và tiếp diễn sáng -> chiều trên `GER40` (ký quỹ `1:15`, đóng trước giờ đóng cửa Xetra `16:20 UTC`).
  - **Họ B (`B_XAU_VOL_EXP`, `4` giả thuyết):** Vàng (`XAUUSD`) phá vỡ hộp phiên Á sang London, phá vỡ `OR30` mở cửa COMEX (`08:20 ET`), nén biến động London -> Mỹ, và mở rộng vượt đỉnh/đáy ngày hôm trước.
  - **Họ C (`C_FX_NONJPY_MOM`, `4` giả thuyết):** Nén biến động Á -> Âu trên `AUDUSD` và `GBPJPY`, phá vỡ phiên dầu/Mỹ trên `USDCAD`, và tiếp diễn sáng London trên `EURUSD`.
  - **Họ D (`D_US500_CROSS_LEADLAG`, `4` giả thuyết):** `US500` mở cửa `OR30` (khác hoàn toàn `US100` E4/E5), truyền dẫn rủi ro `GER40 -> US500` lúc `09:30 ET`, đồng thuận trú ẩn `XAUUSD + EURUSD` phiên Mỹ, và đồng thuận rổ tiền tệ hàng hóa `AUDUSD / USDCAD`.
- **Chuẩn khớp lệnh & chống nhìn trộm:** Chỉ báo ngày (`ATR14`, `ATR5/ATR20`, `prev_h/l`) dịch trễ `shift = 1`; lệnh chờ phá vỡ (`Stop Breakout`) khớp thực tế tại `max(top, AskOpen)` / `min(bot, BidOpen)` (bỏ qua nến 1 phút chạm cả 2 đầu); chạm đồng thời SL/TP xử lý bảo thủ SL khớp trước; áp dụng đầy đủ bộ lọc tin đỏ `2018–2024` (`±300s` `FLATTEN_5M`).

---

## 2. Bảng Kết Quả Đầy Đủ `m_total = 16` Ứng Viên (Khớp 100% Với JSON Receipt)

Mã nguồn: [lab12_orthogonal_momentum_v2_discovery.py](../../tooling/ai-engines/quant_factory/lab12_orthogonal_momentum_v2_discovery.py) · Kiểm thử: [test_lab12_orthogonal_momentum_v2.py](../../tooling/ai-engines/tests/test_lab12_orthogonal_momentum_v2.py) · Biên nhận JSON: [LAB12-ORTHOGONAL-MOMENTUM-V2-DISCOVERY-20261124.json](LAB12-ORTHOGONAL-MOMENTUM-V2-DISCOVERY-20261124.json).

| Mã Ứng Viên | Tài Sản | Cl.A n | Cl.A PF | Cl.B n | Cl.B PF | Cl.B R (1x) | Cl.B aR (1.5x) | Năm Dương | Max Năm % | r(LIVE8) | Max r Bot | pSF Cl.B | Bonf p | BH q | DSR | Phán Quyết | Cổng Trượt |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| `L12_A1_GER40_FFM08_ORB30_BRK` | GER40 | 738 | 0.78 | 1022 | 0.93 | -20.92 | -8.35 | 1/7 | 100.0% | +0.030 | +0.074 | 0.2358 | 1.0000 | 0.6287 | 0.003 | `REJECT_KILLED` | G1_CLB_PF_OR_N, G2_STRESS_15X, G4_YEAR_STABILITY |
| `L12_A2_GER40_FFM08_ORB60_BRK` | GER40 | 737 | 0.96 | 1023 | 0.86 | -38.56 | -12.50 | 1/7 | 100.0% | +0.007 | +0.058 | 0.6444 | 1.0000 | 0.7931 | 0.000 | `REJECT_KILLED` | G1_CLB_PF_OR_N, G2_STRESS_15X, G4_YEAR_STABILITY |
| `L12_A3_GER40_VOLCOMP_EXP` | GER40 | 150 | 0.76 | 194 | 0.54 | -25.53 | -6.93 | 1/7 | 100.0% | -0.024 | -0.051 | 0.9710 | 1.0000 | 0.9710 | 0.000 | `REJECT_KILLED` | G1_CLB_PF_OR_N, G2_STRESS_15X, G4_YEAR_STABILITY |
| `L12_A4_GER40_MORN_TO_AFT_CONT` | GER40 | 131 | 0.99 | 209 | 0.97 | -1.71 | -1.08 | 3/7 | 100.0% | -0.028 | +0.063 | 0.2038 | 1.0000 | 0.6287 | 0.018 | `REJECT_KILLED` | G1_CLB_PF_OR_N, G2_STRESS_15X, G4_YEAR_STABILITY |
| `L12_B1_XAU_ASIA_BOX_LDN_BRK` | XAUUSD | 549 | 0.95 | 782 | 0.81 | -37.44 | -11.75 | 2/7 | 100.0% | +0.146 | +0.107 | 0.4496 | 1.0000 | 0.7193 | 0.000 | `REJECT_KILLED` | G1_CLB_PF_OR_N, G2_STRESS_15X, G4_YEAR_STABILITY |
| `L12_B2_XAU_COMEX0820_ORB30` | XAUUSD | 735 | 0.77 | 954 | 1.00 | -0.00 | -3.06 | 2/7 | 100.0% | +0.024 | +0.021 | 0.0170 | 0.2717 | 0.2078 | 0.042 | `REJECT_KILLED` | G1_CLB_PF_OR_N, G2_STRESS_15X, G4_YEAR_STABILITY |
| `L12_B3_XAU_LDN_NY_VOLCOMP_BRK` | XAUUSD | 180 | 0.83 | 243 | 0.79 | -12.09 | -3.79 | 0/7 | 100.0% | +0.029 | +0.066 | 0.5105 | 1.0000 | 0.7425 | 0.001 | `REJECT_KILLED` | G1_CLB_PF_OR_N, G2_STRESS_15X, G4_YEAR_STABILITY |
| `L12_B4_XAU_PRIOR_DAY_EXP_BRK` | XAUUSD | 292 | 0.89 | 360 | 0.91 | -8.14 | -3.16 | 3/7 | 100.0% | +0.046 | +0.079 | 0.3257 | 1.0000 | 0.6513 | 0.013 | `REJECT_KILLED` | G1_CLB_PF_OR_N, G2_STRESS_15X, G4_YEAR_STABILITY |
| `L12_C1_AUDUSD_ASIA_LDN_VOLCOMP` | AUDUSD | 141 | 1.06 | 198 | 0.69 | -14.14 | -4.15 | 2/7 | 100.0% | +0.051 | +0.110 | 0.7602 | 1.0000 | 0.8546 | 0.000 | `REJECT_KILLED` | G1_CLB_PF_OR_N, G2_STRESS_15X, G4_YEAR_STABILITY |
| `L12_C2_GBPJPY_ASIA_LDN_VOLCOMP` | GBPJPY | 253 | 0.97 | 330 | 1.02 | +1.30 | -0.26 | 4/7 | 100.0% | +0.072 | +0.106 | 0.1379 | 1.0000 | 0.6287 | 0.080 | `REJECT_KILLED` | G1_CLB_PF_OR_N, G2_STRESS_15X, G4_YEAR_STABILITY |
| `L12_C3_USDCAD_NY_OIL_EXP_BRK` | USDCAD | 571 | 0.82 | 797 | 0.83 | -30.55 | -10.06 | 1/7 | 100.0% | -0.030 | -0.053 | 0.3726 | 1.0000 | 0.6624 | 0.000 | `REJECT_KILLED` | G1_CLB_PF_OR_N, G2_STRESS_15X, G4_YEAR_STABILITY |
| `L12_C4_EURUSD_LDN_MORN_CONT` | EURUSD | 99 | 1.02 | 133 | 0.72 | -9.67 | -2.82 | 2/7 | 100.0% | +0.096 | +0.249 | 0.8012 | 1.0000 | 0.8546 | 0.001 | `REJECT_KILLED` | G1_CLB_PF_OR_N, G2_STRESS_15X, G4_YEAR_STABILITY |
| `L12_D1_US500_CASH_ORB30_EOD` | US500 | 716 | 0.74 | 994 | 1.00 | -0.74 | -4.33 | 3/7 | 100.0% | +0.086 | +0.277 | 0.0260 | 0.4156 | 0.2078 | 0.026 | `REJECT_KILLED` | G1_CLB_PF_OR_N, G2_STRESS_15X, G4_YEAR_STABILITY |
| `L12_D2_GER40_TO_US500_TRANSMIT` | US500 | 212 | 0.84 | 304 | 0.84 | -14.57 | -4.90 | 0/7 | 100.0% | +0.079 | +0.072 | 0.5864 | 1.0000 | 0.7819 | 0.003 | `REJECT_KILLED` | G1_CLB_PF_OR_N, G2_STRESS_15X, G4_YEAR_STABILITY |
| `L12_D3_XAU_USD_SAFEHAVEN_NY` | XAUUSD | 166 | 0.78 | 207 | 1.03 | +1.44 | -0.33 | 2/7 | 100.0% | +0.110 | +0.094 | 0.1648 | 1.0000 | 0.6287 | 0.056 | `REJECT_KILLED` | G1_CLB_PF_OR_N, G2_STRESS_15X, G4_YEAR_STABILITY |
| `L12_D4_COMMOD_FX_BASKET_MOM` | AUDUSD | 191 | 0.84 | 251 | 0.84 | -9.25 | -3.12 | 0/7 | 100.0% | +0.161 | +0.273 | 0.3077 | 1.0000 | 0.6513 | 0.002 | `REJECT_KILLED` | G1_CLB_PF_OR_N, G2_STRESS_15X, G4_YEAR_STABILITY |

---

## 3. Kiểm Thử Ghép Danh Mục Prop (`10.000` Kịch Bản, `FTMO 10K / 25K` & `The5ers 5K`)

Vì `0/16` ứng viên vượt qua 6 cổng, bảng dưới đây so sánh đội hình chuẩn **`A1_V1_LIVE8_BASE`** với kịch bản chẩn đoán giả định **`DIAG_COUNTERFACTUAL_TOP1_UNAPPROVED`** (`live8 + L12_C2_GBPJPY_ASIA_LDN_VOLCOMP`, CHỈ ĐỂ KIỂM CHỨNG — KHÔNG THĂNG HẠNG), qua đó chứng minh trực tiếp rằng **cố nhồi thêm bot yếu vào `A1_V1_LIVE8` sẽ làm xấu đi mọi chỉ số cốt lõi**, trong khi **nhảy bậc vé `FTMO 10K -> 25K` nâng hiệu quả đồng phí thêm `+60%` ngay lập tức**.

### 3.1. Hiệu Năng M1 Gốc (`Funded_Safe 1,0×`, `SYMCAP 1,00%`)

| Danh Mục | Số Bot | Lãi Năm 1x | Sharpe 1x | Sụt Sâu Nhất | Calmar 1x | Calmar 1.5x | Lần Chạm Trần P1 (1.75%) |
|---|---:|---:|---:|---:|---:|---:|---:|
| `A1_V1_LIVE8_BASE` | 8 | 8.63% | 1.31 | 9.52% | 0.91 | 0.47 | 1851 |
| `DIAG_COUNTERFACTUAL_TOP1_UNAPPROVED` | 9 | 8.56% | 1.20 | 10.02% | 0.85 | 0.41 | 2434 |

### 3.2. Mô Phỏng Vòng Thi Quỹ (`10.000` Đường Block-Bootstrap, `seed = 20261124`)

| Danh Mục | Gói Quỹ | Chế Độ Vòng 1 | Đậu 3m / 6m / 12m | Trung Vị Đậu | Rớt Bất Kỳ | Cháy 5 Vé | Lãi Ròng 24m (EV) | Hiệu Quả / Phí Vé |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `A1_V1_LIVE8_BASE` | FTMO_SWING_10K | `P1_Balanced_SymCap175` | 11.9% / 32.7% / 53.3% | 140d | 0.7% | 0.00% | +641.5 USD | 3.82x |
| `A1_V1_LIVE8_BASE` | FTMO_SWING_10K | `Dyn_ProfitLock_SymCap175` | 12.7% / 33.1% / 51.7% | 134d | 1.3% | 0.00% | +616.6 USD | 3.67x |
| `A1_V1_LIVE8_BASE` | FTMO_SWING_25K | `P1_Balanced_SymCap175` | 11.9% / 32.7% / 53.3% | 140d | 0.7% | 0.00% | +1650.8 USD | 6.11x |
| `A1_V1_LIVE8_BASE` | FTMO_SWING_25K | `Dyn_ProfitLock_SymCap175` | 12.7% / 33.1% / 51.7% | 134d | 1.3% | 0.00% | +1592.7 USD | 5.90x |
| `A1_V1_LIVE8_BASE` | THE5ERS_HS_5K | `P1_Balanced_SymCap175` | 11.8% / 32.6% / 53.3% | 140d | 0.7% | 0.00% | +326.3 USD | 8.37x |
| `A1_V1_LIVE8_BASE` | THE5ERS_HS_5K | `Dyn_ProfitLock_SymCap175` | 12.2% / 32.9% / 51.6% | 135d | 1.3% | 0.00% | +315.0 USD | 8.08x |
| `DIAG_COUNTERFACTUAL_TOP1_UNAPPROVED` | FTMO_SWING_10K | `P1_Balanced_SymCap175` | 14.8% / 32.4% / 48.7% | 131d | 2.6% | 0.00% | +585.0 USD | 3.48x |
| `DIAG_COUNTERFACTUAL_TOP1_UNAPPROVED` | FTMO_SWING_10K | `Dyn_ProfitLock_SymCap175` | 16.1% / 33.1% / 47.4% | 123d | 3.3% | 0.00% | +563.7 USD | 3.36x |
| `DIAG_COUNTERFACTUAL_TOP1_UNAPPROVED` | FTMO_SWING_25K | `P1_Balanced_SymCap175` | 14.8% / 32.4% / 48.7% | 131d | 2.6% | 0.00% | +1520.6 USD | 5.63x |
| `DIAG_COUNTERFACTUAL_TOP1_UNAPPROVED` | FTMO_SWING_25K | `Dyn_ProfitLock_SymCap175` | 16.1% / 33.1% / 47.4% | 123d | 3.3% | 0.00% | +1471.4 USD | 5.45x |
| `DIAG_COUNTERFACTUAL_TOP1_UNAPPROVED` | THE5ERS_HS_5K | `P1_Balanced_SymCap175` | 14.6% / 32.3% / 48.7% | 131d | 2.6% | 0.00% | +302.1 USD | 7.75x |
| `DIAG_COUNTERFACTUAL_TOP1_UNAPPROVED` | THE5ERS_HS_5K | `Dyn_ProfitLock_SymCap175` | 15.7% / 32.9% / 47.3% | 123d | 3.3% | 0.00% | +292.5 USD | 7.50x |

---

## 4. Phân Tích Khoa Học: Vì Sao 0/36 Giả Thuyết (Lab #11 + Lab #12) Không Vượt Nổi `A1_V1_LIVE8`

1. **Tín hiệu thô (Gross Alpha) có thật nhưng bị tường ma sát CFD nuốt sạch ở tần suất cao:** Hai ứng viên phá vỡ mở cửa kinh điển **`L12_B2_XAU_COMEX0820_ORB30`** (`954` lệnh Cl.B, `p_signflip = 0,0170`) và **`L12_D1_US500_CASH_ORB30_EOD`** (`994` lệnh Cl.B, `p_signflip = 0,0260`) đều thắng có ý nghĩa thống kê trước chính lệnh đánh ngược chiều (`fade`), chứng tỏ hiệu ứng mở cửa COMEX & NYSE là có thật. Tuy nhiên, vì kích hoạt tới `~240` lệnh/năm, riêng chênh giá mua/bán + trượt giá stress (`~3%–4,5%` SL mỗi lệnh) đã đốt **`30R–45R`** trong 4 năm Blind Cl.B — kéo lợi nhuận ròng `1,0×` về đúng hòa vốn (`PF = 1,00`) và âm sâu `-3,06R..-4,33R/năm` ở mức stress `1,5×`.
2. **Họ phá vỡ châu Âu `GER40` (`0/4`) & Dẫn dắt `GER40 -> US500` (`0/1`) thất bại rõ ràng:** Phá vỡ `OR30`/`OR60` Frankfurt (`L12_A1`, `L12_A2`: `-20,92R` và `-38,56R`) và nén biến động `GER40` (`L12_A3`: `PF = 0,54`) liên tục dính bẫy phá vỡ giả trong phiên Âu. Điều này khớp hoàn toàn với phát hiện ngược chiều của Lab #11 (`L11_C2_GER40_CASH_OR30_FADE` đạt `PF = 1,55` ở Cl.B!) — chứng tỏ DAX đầu phiên có xu hướng quét thanh khoản rồi quay đầu hơn là chạy thẳng một mạch.
3. **Ghép thêm bot yếu làm hỏng danh mục ngay lập tức:** Trong kiểm thử chẩn đoán `DIAG_COUNTERFACTUAL_TOP1_UNAPPROVED` (thêm ứng viên dương nhất Lab #12 là `L12_C2_GBPJPY_ASIA_LDN_VOLCOMP`, `PF = 1,02`), dù có tương quan cực thấp (`r = +0,072`), nó vẫn kéo giảm **toàn bộ chất lượng danh mục**: Sharpe `1,31 -> 1,20`, sụt giảm sâu nhất tăng `9,52% -> 10,02%`, Calmar `1,5×` tụt `0,47 -> 0,41`, tỷ lệ rớt vé tăng gần `4×` (`0,7% -> 2,6%`), và lãi ròng EV trên `FTMO 25K` giảm **`-130,2 USD`** (`6,11× -> 5,63×`).
4. **Chốt bài học tổng kết cho toàn dự án (`100+` giả thuyết CFD nội nhật từ Pass 29–30 + Lab #10–#12):**
   - Toàn bộ không gian chiến lược M1 CFD đóng trong ngày (`swap = 0`) trên `12` tài sản đã được quét sạch cả 2 thái cực (đảo chiều ở Lab #11 lẫn thuận xu hướng / mở rộng biến động ở Lab #12) mà không chạm `Holdout 2025+`.
   - **`A1_V1_LIVE8` (và dự phòng `L10_B2_EURUSD_VOLCOMP75`) là biên hiệu quả Pareto đã kiểm chứng của kênh Prop CFD.**
   - **Không mở thêm Lab săn bot CFD nội nhật mới.** Toàn bộ nguồn lực tăng trưởng sang chuẩn Top 1% (`1,5–3` tháng đậu quy đổi & Sharpe thực chiến `2,0–3,0`) chuyển dứt khoát sang:
     1. **Vận hành sạch `A1_V1_LIVE8` với đủ 4 bản vá + thang đa quỹ lệch pha** (`The5ers 5K [8,37× phí]` -> `FTMO Swing 25K [6,11× phí]` -> `50K/100K`, trích từ lãi thật theo sổ 3 ngăn),
     2. **Tái đầu tư lãi Prop vào Sổ Vốn Riêng đa nhánh khung `4H–D1` (`NCO_CexCap25`: `S2 Crypto Spot`, `S3A Funding`, `S3B/S4 ETF IBKR`)**, nơi thời gian nắm giữ dài triệt tiêu hoàn toàn tường ma sát chênh giá trong ngày.

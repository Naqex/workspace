---
title: "Wave 2 Lab #7 & Live Maker Probe: Overnight-vs-Intraday Tug-of-War, 4-Quadrant Macro & Moreira-Muir RD-Agent-Q Loop (2005-2026)"
date: 2026-11-24
lane: quant-rnd (Lane C)
milestone: Wave 2 Cycle 4A — Live Maker Shadow Probe + Lab #7
status: COMPLETE_5_COUNCIL_APPROVED_0_REDUNDANT_SLEEVE6
holdout_rows_analysed: 0
order_send_count: 0
primary_scripts:
  - tooling/ai-engines/quant_factory/crypto_maker_shadow_probe.py
  - tooling/ai-engines/quant_factory/lab7_overnight_macro_rd_loop.py
---

# Wave 2 Cycle 4A: Live Crypto Maker Shadow Probe & Lab #7 RD-Agent-Q (21-Năm 40-ETF)

## 1. Tóm tắt điều hành (Executive Summary)

Chu kỳ 4A triển khai song song hai nhánh nghiên cứu định lượng thực chiến (`OrderSend = 0`, `0` API keys, FX Holdout `2025+` đóng băng hoàn toàn với `holdout_rows_analysed = 0`):

1. **Nhánh 1 — Live Passive-Limit Shadow Probe cho `M2B_BLEND_50_FUND_50_MOM`** ([crypto_maker_shadow_probe.py](../../tooling/ai-engines/quant_factory/crypto_maker_shadow_probe.py)):
   - Thu thập trực tiếp sổ lệnh công khai Binance USD-M Futures (`bookTicker`, `premiumIndex`, `fundingRate`, `4h` & `1m` klines trên `20` hợp đồng perp thanh khoản nhất, chạy trong `1.84s`, hỗ trợ `--once` và `--daemon --interval-sec 300`, ghi telemetry vào `.runtime/live-overnight/crypto_maker_shadow.jsonl` và `crypto_maker_shadow_latest.json`).
   - Kết quả smoke-test trực tiếp (`2026-11-23T18:22Z`, `13` chân rổ `M2B_BLEND`, trung vị spread `1.401 bps`, `net_exposure = 0.0`):
     - Khung **5 phút** (`n = 52` thử nghiệm touch-through chặt `low < bid` / `high > ask`): tỷ lệ khớp **`94.23%`**, adverse selection 5m **`+3.634 bps`**, chi phí hiệu dụng **`5.886 bps <= 6.150 bps`** (`PASS` ngưỡng M2!).
     - Khung **15 phút** (`n = 39`): tỷ lệ khớp **`100.0%`**, adverse selection 5m **`+1.561 bps`**, chi phí hiệu dụng **`3.561 bps <= 6.150 bps`** (`PASS` mạnh ngưỡng M2!).
     - Khung **60 phút** (`n = 13`): tỷ lệ khớp **`100.0%`**, nhưng adverse selection 5m cục bộ ở nhịp 1 giờ gần nhất tăng lên **`+5.316 bps`** khiến chi phí hiệu dụng là **`7.316 bps > 6.150 bps`** (`FAIL` cục bộ — rổ đối chứng All-20 vẫn đạt **`4.175 bps <= 6.150 bps`**). Điều này khẳng định cần chạy `--daemon` xuyên đêm 30 ngày để thu thập phân phối fill/adverse-selection đủ mẫu trước khi nâng `M2B_BLEND_50_FUND_50_MOM` từ `CONDITIONAL_RETEST` lên incubation.

2. **Nhánh 2 — Lab #7 Chạy thực tế `auto_research_loop.run_research_batch()` trên 21 năm OHLC 40-ETF** ([lab7_overnight_macro_rd_loop.py](../../tooling/ai-engines/quant_factory/lab7_overnight_macro_rd_loop.py)):
   - Kiểm thử **`M = 10 <= 20`** giả thuyết white-box hoàn toàn mới trên lịch NYSE sạch (`.runtime/etf40-cache/`, `Cluster A = 2006-01-03..2018-12-31` `n = 3,271` ngày -> `Blind Cluster B = 2019-01-01..2026-11-20` `n = 1,984` ngày; khớp 1-1 theo ngày NYSE với `S1 PORT_7E` Dev `<= 2024-12-31` `n = 1,510` ngày).
   - **Kết quả Research Council (`auto_research_loop` ledger SHA `7194825a1b15639c`):** **`5 / 10` đạt `APPROVE_FOR_INCUBATION`** (tự động xuất `5` bộ template Python + MQL5 `InpDryRunLogOnly = true` trong `.runtime/auto-research-out/lab7/templates/`), **`5 / 10` bị `REJECT_KILLED`**.
   - **Khám phá phủ định (Family A — Overnight-vs-Intraday Tug-of-War `0 / 4`):** Giao dịch mua đóng/bán mở hàng ngày (`L7_A1_OV_DAILY_MOC_MOO`, turnover `300.6x/năm`) bị chi phí đấu giá `5 bps / 10 bps` phá hủy hoàn toàn (`-9.52%` Cl.B 1x, `-22.16%` Cl.B 2x). Ngay cả lọc dip `-1 sigma` (`L7_A2`, `-5.26%`) hay chiến lược nắm giữ tháng Lou-Polk-Skouras (`L7_A3` `-0.26%`, `L7_A4` `+2.25%`) đều không vượt nổi `BH-FDR q <= 0.10`.
   - **Khám phá dương tính mạnh (Family B Macro 4-Quadrant & Family C Moreira-Muir Variance Scaling — `5 / 6` PASS Council):**
     - `L7_B1_MACRO_QUAD_REGIME` đạt Blind Cl.B **`+12.74%` CAGR (`2x +11.88%`), Sharpe `1.062`, `BH-q = 0.00767`, `DSR_b = 0.9168`, `GFC -0.91%`, `COVID +5.21%`**.
     - `L7_C3_MM17_VAR_MACRO_CORE` (Moreira-Muir *JF 2017* co giãn theo phương sai trễ `20d`, đòn bẩy `<= 1.0x`) đạt Blind Cl.B **`+5.11%` CAGR (`2x +4.81%`), Sharpe `1.008`, MaxDD chỉ `7.34%`, Calmar `0.696`, turnover chỉ `5.69x/năm` (`BE 15.64x`), `DSR_full = 0.9951`**, và **cả 3 khủng hoảng đều dương hoặc đi ngang (`GFC +6.64%`, `COVID +2.27%`, `2022 -0.62%`)!**
   - **Quyết định Kỷ luật về Sleeve #6 (`0` JSON trùng lặp được xuất):** Dù 5 chiến lược vượt sạch 6 cổng Research Council và có `|r(S1)| <= 0.07`, tất cả đều chia sẻ rủi ro vĩ mô ETF với `S4_ETF40_MULTIFACTOR` ensemble (`r = 0.4599` tới `0.7870 > 0.45`; ngay ứng viên độc lập nhất là `L7_C2_MM17_VAR_XSEC_TOP6` đạt `r(S4_primary) = +0.2001` và `r(S3B) = +0.3704` nhưng có `r(S4_ensemble) = +0.4599`, vượt trần `0.45` đúng `0.0099`). Giữ nguyên chuẩn fail-closed (**không nới trần sau khi nhìn số!**): **không xuất `sleeve6_overnight_macro_etf.json`**, thay vào đó xếp `L7_C3_MM17_VAR_MACRO_CORE` và `L7_B1_MACRO_QUAD_REGIME` làm ứng viên nâng cấp trực tiếp cho Own-Book IBKR `S3B v2 / S4 v2`!

---

## 2. Kết quả chi tiết Live Passive-Limit Shadow Probe (`M2B_BLEND_50_FUND_50_MOM`)

Trích xuất nguyên văn từ `.runtime/live-overnight/crypto_maker_shadow_latest.json` (`cycle_num = 1`, `2026-11-23T18:22:32Z`, `order_send_count = 0`, `api_keys_used = 0`):

| Nhóm đo | Khung thời gian | Số thử nghiệm | Số lần khớp | Tỷ lệ khớp (Touch-Through) | Adv. Selection 5m (bps) | Adv. Selection 15m (bps) | Chi phí hiệu dụng (bps) | Ngưỡng M2 (bps) | Đạt M2? |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Rổ active `M2B_BLEND` (13 chân) | 5m | 52 | 49 | 94.23% | +3.634 | -7.417 | 5.886 | 6.150 | `PASS` |
| Rổ active `M2B_BLEND` (13 chân) | 15m | 39 | 39 | 100.00% | +1.561 | -12.786 | 3.561 | 6.150 | `PASS` |
| Rổ active `M2B_BLEND` (13 chân) | 60m | 13 | 13 | 100.00% | +5.316 | -7.131 | 7.316 | 6.150 | `FAIL` |
| Đối chứng All-20 Perps | 5m | 160 | 148 | 92.50% | +1.036 | +0.720 | 3.558 | 6.150 | `PASS` |
| Đối chứng All-20 Perps | 15m | 120 | 120 | 100.00% | -0.444 | -1.708 | 2.000 | 6.150 | `PASS` |
| Đối chứng All-20 Perps | 60m | 40 | 40 | 100.00% | +2.175 | -4.815 | 4.175 | 6.150 | `PASS` |

Ghi chú kỹ thuật: mô hình áp sàn bảo thủ `max(0, adv_sel_5m)` khi tính chi phí hiệu dụng để không bao giờ ghi khống chi phí âm từ biến động ngắn hạn có lợi. Lệnh chạy nền xuyên đêm cho Coordinator:
`D:\ANNAM\TradingWorkspace\.runtime\quant-audit-v24\Scripts\python.exe tooling/ai-engines/quant_factory/crypto_maker_shadow_probe.py --daemon --interval-sec 300`

---

## 3. Bảng kết quả đầy đủ Lab #7 (`M = 10`, Qua `auto_research_loop.run_research_batch()`)

Mọi số liệu trích nguyên văn từ `.runtime/etf40-cache/lab7_overnight_macro_summary.json` (thời gian chạy `3.22s`, `Cl.A = 3,271` ngày NYSE `2006-2018`, `Blind Cl.B = 1,984` ngày NYSE `2019-2026`, phí `1x = 5 bps` / `2x = 10 bps` + `50 bps/năm` phí mượn short).

| Mã giả thuyết | Họ | Cl.A 1x CAGR | Cl.A Shp | Cl.B 1x CAGR | Cl.B 2x CAGR | Cl.B Shp | Cl.B MaxDD | BH-q | DSR_b | BE Mult | r(S1) | r(S4 Pri) | r(S4 Ens) | Council Verdict | S6 Qual |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| `L7_A1_OV_DAILY_MOC_MOO` | A (OV) | -10.98% | -2.090 | -9.52% | -22.16% | -1.536 | 54.75% | 0.99999 | 0.0000 | -0.73x | -0.0271 | +0.2319 | +0.4459 | `REJECT_KILLED` | `No` |
| `L7_A2_OV_DIP_SELECTIVE` | A (OV) | -2.69% | -0.646 | -5.26% | -12.40% | -1.002 | 36.15% | 0.99999 | 0.0000 | -0.15x | -0.0261 | +0.0962 | +0.2602 | `REJECT_KILLED` | `No` |
| `L7_A3_LPS_TUGOFWAR_LS` | A (LPS) | +0.83% | 0.175 | -0.26% | -0.61% | -0.010 | 19.32% | 0.64016 | 0.0544 | 0.22x | -0.0532 | -0.0294 | +0.0934 | `REJECT_KILLED` | `No` |
| `L7_A4_LPS_OVERNIGHT_DOM_LO` | A (LPS) | +4.08% | 0.506 | +2.25% | +1.89% | 0.297 | 20.15% | 0.34580 | 0.2305 | 6.88x | -0.0732 | +0.2993 | +0.5656 | `REJECT_KILLED` | `No` |
| `L7_B1_MACRO_QUAD_REGIME` | B (Macro) | +6.16% | 0.622 | +12.74% | +11.88% | 1.062 | 19.81% | 0.00767 | 0.9168 | 11.44x | -0.0697 | +0.6054 | +0.6682 | `APPROVE_FOR_INCUBATION` | `No` |
| `L7_B2_YC_CREDIT_DEFENSIVE` | B (Macro) | +4.97% | 0.626 | +8.96% | +7.91% | 0.978 | 19.62% | 0.00767 | 0.8762 | 7.69x | -0.0442 | +0.7050 | +0.6721 | `APPROVE_FOR_INCUBATION` | `No` |
| `L7_B3_MACRO_REGIME_LS` | B (Macro) | -2.41% | -0.191 | +1.24% | +0.14% | 0.183 | 17.17% | 0.41247 | 0.1436 | 2.13x | -0.0016 | +0.1088 | -0.0278 | `REJECT_KILLED` | `No` |
| `L7_C1_MM17_VAR_TSMOM_38` | C (MM17) | +4.09% | 0.713 | +4.85% | +4.22% | 0.901 | 8.30% | 0.00978 | 0.8236 | 7.72x | -0.0400 | +0.4268 | +0.7870 | `APPROVE_FOR_INCUBATION` | `No` |
| `L7_C2_MM17_VAR_XSEC_TOP6` | C (MM17) | +5.07% | 0.805 | +2.97% | +2.24% | 0.642 | 9.71% | 0.08294 | 0.5866 | 4.80x | -0.0155 | +0.2001 | +0.4599 | `APPROVE_FOR_INCUBATION` | `No` |
| `L7_C3_MM17_VAR_MACRO_CORE` | C (MM17) | +3.92% | 0.859 | +5.11% | +4.81% | 1.008 | 7.34% | 0.00767 | 0.8904 | 15.64x | -0.0513 | +0.4523 | +0.5001 | `APPROVE_FOR_INCUBATION` | `No` |

---

## 4. So sánh Khủng hoảng (GFC / COVID / 2022) & Tương quan với `S3B` / `S4`

So sánh 5 ứng viên vượt Research Council với `S4_ETF40_MULTIFACTOR` ([LAB4-40ETF-MULTIFACTOR-VRP-20261124.md](./LAB4-40ETF-MULTIFACTOR-VRP-20261124.md)):

| Ứng viên Approved | GFC (`2008-01-02..2009-03-09`) | COVID (`2020-02-19..2020-03-23`) | Lạm phát 2022 (`2022-01-03..2022-10-14`) | r vs `S3B` | r vs `S4` Pri | r vs `S4` Ens | Vai trò đề xuất |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `L7_B1_MACRO_QUAD_REGIME` | -0.91% | +5.21% | -8.92% | +0.6678 | +0.6054 | +0.6682 | Ứng viên nâng cấp `S4 v2` (CAGR cao nhất `+12.74%`) |
| `L7_B2_YC_CREDIT_DEFENSIVE` | -1.91% | +6.05% | -16.86% | +0.6295 | +0.7050 | +0.6721 | Trùng yếu tố Credit với `E40_CREDIT_HYG_IEF` |
| `L7_C1_MM17_VAR_TSMOM_38` | -0.67% | -4.85% | -1.30% | +0.6341 | +0.4268 | +0.7870 | Giảm mạnh DD 2022 (`-1.30%` vs `S4 -13.59%`) |
| `L7_C2_MM17_VAR_XSEC_TOP6` | +2.12% | -4.08% | -0.08% | +0.3704 | +0.2001 | +0.4599 | Độc lập nhất (`r_Pri = 0.20`), sát ngưỡng `0.45` với Ens |
| `L7_C3_MM17_VAR_MACRO_CORE` | +6.64% | +2.27% | -0.62% | +0.7586 | +0.4523 | +0.5001 | Ứng viên nâng cấp `S3B v2` (MaxDD `7.34%`, `BE 15.64x`) |
| *Đối chứng: `S4_APPROVED_EQW`* | *-2.81%* | *-3.22%* | *-13.59%* | *—* | *—* | *1.0000* | *Incumbent Own-Book hiện tại* |

**Bài học kiến trúc:** Co giãn theo phương sai trễ `20d` của Moreira & Muir (*JF 2017*) trong `L7_C3_MM17_VAR_MACRO_CORE` cắt lỗ khủng hoảng lạm phát 2022 từ `-13.59%` xuống chỉ **`-0.62%`**, đồng thời giữ nguyên lợi nhuận dương trong cả GFC (`+6.64%`) và COVID (`+2.27%`) với MaxDD toàn giai đoạn 21 năm chỉ **`7.97%`**.

---

## 5. Quản trị & Khả năng tái lập (Provenance)

- **Lệnh tái lập Lab #7:** `D:\ANNAM\TradingWorkspace\.runtime\quant-audit-v24\Scripts\python.exe tooling/ai-engines/quant_factory/lab7_overnight_macro_rd_loop.py`
- **Ledger RD-Agent-Q đã băm SHA-256:** `.runtime/auto-research-out/lab7/LAB7_OVERNIGHT_MACRO_RD_V1_ledger.json` (`sha256: 7194825a1b15639c`) và `LAB7_OVERNIGHT_MACRO_RD_V1_ledger.md` cùng 5 bộ template white-box (`InpDryRunLogOnly = true`, `OrderSend = 0`).
- **Kiểm thử tự động:** [test_wave2_lab7_and_maker_probe.py](../../tooling/ai-engines/tests/test_wave2_lab7_and_maker_probe.py).
- **Trạng thái xuất Sleeve #6:** **`NONE`** (không xuất thêm JSON trùng lặp `S4` để bảo toàn cấu trúc 6-sleeve sạch cho `NCO_CexCap25`).

---
doc_type: research_receipt
date: 2026-11-24
lane: risk-auditor
milestone: Wave2-Cycle4G-OwnBook-ETF-SuperSleeve
holdout_rows_analysed: 0
order_send_count: 0
---

# Own-Book ETF Super-Sleeve (9 Động Cơ Lab #4 + Lab #7) & Kiểm Định Lô Nguyên IBKR (`5k–200k USD`)

- **Generated UTC:** `2026-11-23T18:46:59.208947+00:00` (runtime `10.689s`)
- **Safety Seal:** Holdout `2025+` của `S1 PORT_7E` giữ **100% SEALED** (`lock=f0a6b43cb205535b...`, `holdout_rows_analysed = 0`, `OrderSend = 0`). Không ghi đè `sleeve3b_macro_etf.json` hay `sleeve4_etf40_multifactor.json`.
- **Lưới NYSE 40-ETF (`0` peeking):** `2005-01-03..2026-11-20 (5507 NYSE days; Cl.A=3020d <= 2017-12-31, Cl.B=2235d >= 2018-01-01)`. Trọng số `SUPER_ETF_9ENG_CLA_NCO` huấn luyện **100% trên Cluster A `<= 2017-12-31`**.

## 1. Đối Đầu 5 Ứng Viên Own-Book ETF Trên Blind Cluster B (`2018–2026`) & 3 Cú Sập Lịch Sử

| ETF Sleeve Candidate | Cl.A Sh | Cl.B 1x CAGR% | Cl.B DD% | Cl.B 1x Sh/Cal | Cl.B 2x Sh/Cal | Turn/yr | r(S1) | GFC 08% | COVID 20% | 2022% |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| INCUMBENT_S3B_MACRO_ETF | 0.65 | +6.66% | 7.77% | 0.97 / 0.86 | 0.93 / 0.80 | ~6.0x | -0.042 | -0.0% | -4.5% | -2.7% |
| INCUMBENT_S4_LAB4_EQW | 0.93 | +6.42% | 15.57% | 0.81 / 0.41 | 0.63 / 0.27 | 29.8x | -0.028 | -2.8% | -3.2% | -13.6% |
| L7_TOP2_MACRO_VAR_EQW | 0.82 | +7.91% | 12.25% | 1.03 / 0.65 | 0.96 / 0.59 | 10.2x | -0.064 | +3.1% | +3.8% | -4.6% |
| SUPER_ETF_6ENG_EQW | 0.99 | +6.98% | 12.35% | 0.96 / 0.57 | 0.80 / 0.43 | 22.8x | -0.042 | -0.8% | -0.9% | -10.6% |
| SUPER_ETF_9ENG_CLA_NCO | 1.08 | +4.31% | 7.31% | 0.90 / 0.59 | 0.63 / 0.35 | 26.2x | -0.049 | +0.2% | -0.9% | -6.0% |

- **Trọng số `SUPER_ETF_9ENG_CLA_NCO` (khớp thuần Cluster A `<= 2017-12-31`):** `E40_RSI2_CONNORS: 30.0%`, `E40_CREDIT_HYG_IEF_REGIME: 0.0%`, `E40_XSEC_SECTOR_MOM_TOP4: 0.0%`, `E40_VRP_VOL_CARRY: 24.6%`, `L7_B1_MACRO_QUAD_REGIME: 0.0%`, `L7_B2_YC_CREDIT_DEFENSIVE: 0.0%`, `L7_C1_MM17_VAR_TSMOM_38: 10.4%`, `L7_C2_MM17_VAR_XSEC_TOP6: 0.0%`, `L7_C3_MM17_VAR_MACRO_CORE: 35.0%`.

## 2. Kiểm Định Khớp Lệnh Thực Tế IBKR: Cổ Phiếu Nguyên (`Integer Shares`) vs Lô Lẻ (`Fractional`) Trên `SUPER_ETF_6ENG_EQW`

Mô phỏng trực tiếp trên giá ETF thực tế (`SPY ~690 USD`, `QQQ ~608`, `GLD ~323`, `TLT ~81`) suốt Blind Cluster B (`2018–2026`), tính đúng biểu phí IBKR US Tiered (`0.0035 USD/cp`, tối thiểu `0.35 USD/lệnh`, trần `1%`) + `2.5 bps` spread một chiều:

| Capital Tier | Mode | Orders/yr | IBKR Comm (bps/yr) | Spread (bps/yr) | Tracking Err (bps/yr) | Idle Cash% | Net CAGR% | Net Sh / DD% | Clean Int? |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| 5,000 USD | Integer OFF | 705 | 451.00 | 52.51 | 202.4 | 15.87% | +1.39% | 0.27 / 14.36% | NEEDS_FRAC |
| 5,000 USD | Fractional ON | 764 | 474.28 | 57.06 | 47.8 | 0.00% | +2.56% | 0.38 / 17.25% | — |
| 25,000 USD | Integer OFF | 1243 | 127.61 | 58.54 | 34.5 | 2.66% | +5.88% | 0.84 / 12.37% | NEEDS_FRAC |
| 25,000 USD | Fractional ON | 1197 | 123.02 | 58.77 | 12.7 | 0.00% | +6.26% | 0.86 / 12.87% | — |
| 50,000 USD | Integer OFF | 1612 | 80.39 | 59.20 | 18.1 | 1.29% | +6.56% | 0.92 / 12.24% | PASS |
| 50,000 USD | Fractional ON | 1666 | 84.03 | 59.27 | 8.6 | 0.00% | +6.67% | 0.92 / 12.55% | — |
| 200,000 USD | Integer OFF | 2626 | 37.46 | 59.74 | 7.4 | 0.31% | +7.12% | 0.98 / 12.10% | PASS |
| 200,000 USD | Fractional ON | 2890 | 41.12 | 59.80 | 6.2 | 0.00% | +7.12% | 0.97 / 12.19% | — |

- **Ngưỡng vốn tối thiểu chạy sạch cổ phiếu nguyên (`TE <= 50 bps/yr` & `Idle Cash <= 2.0%`):** **`50,000 USD`** (ở `5k–25k USD` phải bật Fractional Shares; đồng thời phát hiện **bẫy phí tối thiểu `0.35 USD/lệnh` của IBKR** ở `5k USD` lên tới `451–474 bps/năm` khi chạy `700+` lệnh/năm -> dưới `25k USD` bắt buộc dùng dead-band lọc lệnh nhỏ hoặc chọn nhánh turnover thấp như `L7_TOP2_MACRO_VAR_EQW` `10.2x/năm` / `S3B` `~6x/năm`).

## 3. Kiểm Định Tác Động Thay Thế `S4` -> `SUPER_ETF_6ENG_EQW` Trong Quant Pod v2 (`NCO_CexCap25`)

- **Phán quyết trung thực (`2020–2022` -> Blind OOS `2023–2024`):** **`KEEP_S4_V1`**

| Pod v2 Allocator | Config | S4 Weight% | OOS CAGR% | OOS MaxDD% | OOS Sharpe | OOS Calmar | 2022 Crisis Ret / DD% |
|---|---|---:|---:|---:|---:|---:|---:|
| NCO_CexCap25 | Baseline (S4 v1) | 4.0% | +4.95% | 2.23% | 1.89 | 2.21 | +2.69% / 1.09% |
| NCO_CexCap25 | Upgrade (SUPER_ETF_6ENG) | 1.8% | +4.79% | 2.29% | 1.82 | 2.10 | +3.35% / 1.02% |
| ERC_LW_CexCap25 | Baseline (S4 v1) | 11.1% | +5.56% | 2.24% | 2.07 | 2.48 | +0.95% / 1.31% |
| ERC_LW_CexCap25 | Upgrade (SUPER_ETF_6ENG) | 11.1% | +5.29% | 2.31% | 1.98 | 2.29 | +1.88% / 1.29% |

## 4. Kết Luận Điều Hành Own-Book IBKR

1. **Nổi bật nhất trên Blind Cluster B (`2018–2026`):** **`L7_TOP2_MACRO_VAR_EQW`** dẫn đầu toàn bảng với **`CAGR +7.91%`, `1x Sh 1.03`, `2x Sh 0.96`, `Turn 10.2x/yr`**, dương cả `GFC (+3.1%)` lẫn `COVID (+3.8%)` và chỉ `-4.6%` năm `2022`. **`SUPER_ETF_6ENG_EQW`** đạt **Sharpe `0.96`** (`2x 0.80`), **MaxDD `12.35%`** (vượt `S4_LAB4_EQW` Sharpe `0.81` / DD `15.57%`). Bản `SUPER_ETF_9ENG_CLA_NCO` có DD thấp nhất (`7.31%`, Sharpe `0.90`).
2. **Thực chiến IBKR theo quy mô vốn:** `SUPER_ETF_6ENG_EQW` chạy sạch cổ phiếu nguyên (không cần lô lẻ, `TE = 18.1 bps/yr`, không hao Sharpe) từ mốc **`50,000 USD`** (rẻ gấp đôi ngưỡng `100k USD` của CME Micro Futures ở Lab #8!). Dưới `25k USD`, tuyệt đối tránh khớp `700+` lệnh nhỏ/năm (bị phí tối thiểu `0.35 USD/lệnh` ăn `127–474 bps/năm`) — hãy ưu tiên `L7_TOP2_MACRO_VAR_EQW` + `S3B` (turnover thấp) kèm Fractional Shares.
3. **Quyết định tích hợp Pod v2 (`KEEP_S4_V1`):** Thay `S4 v1 -> SUPER_ETF_6ENG_EQW` cải thiện phòng thủ khủng hoảng `2022` (`NCO +2.69% -> +3.35%`, DD `1.09% -> 1.02%`) nhưng giảm nhẹ OOS Sharpe `2023–2024` (`1.89 -> 1.82`), nên giữ nguyên `sleeve4_etf40_multifactor.json` làm baseline `NCO_CexCap25` và coi `L7_TOP2` / `SUPER_ETF_6ENG` là ứng viên nâng cấp Own-Book chuyên biệt khi vốn IBKR đạt `>= 25k–50k USD`.

---
doc_type: research_receipt
date: 2026-11-24
lane: risk-auditor
milestone: Wave2-Cycle4B-PodV2-CexCap-Rebalance
holdout_rows_analysed: 0
order_send_count: 0
---

# Quant Pod v2 — Trần Nhóm CEX `<= 25%`, Tối Ưu Chu Kỳ Tái Cân Bằng & Overlay Biến Động Nhân Quả (6 Sleeves)

- **Generated UTC:** `2026-11-23T18:27:12.841506+00:00` (runtime `9.172s`)
- **Safety Seal:** Holdout `2025+` SEALED (`lock=f0a6b43cb205535b...`, `holdout_rows_analysed = 0`, `OrderSend = 0`).
- **6 Finalized Sleeves (`2020-01-01..2024-12-31 (1305 biz days)`):** `S1_PROP_FX_IDX, S2_CRYPTO_SPOT, S3A_FUND_CARRY, S3B_MACRO_ETF, S4_ETF40_MULTIFACTOR, S5_CME_FUTURES_PROP` (huấn luyện trọng số nhân quả trên `2020-01-01..2022-12-31`, kiểm định Blind OOS trên `2023-01-02..2024-12-31`).

## 1. So Sánh Phân Bổ 6 Sleeves & Kiểm Định Sốc Sập Sàn CEX `-50%` (`NCO_CexCap25` / `ERC_LW_CexCap25`)

Hàm chiếu simplex `apply_group_weight_cap()` khóa đồng thời `w_i <= 35%` cho từng sleeve VÀ `w(S2_CRYPTO_SPOT) + w(S3A_FUND_CARRY) <= 25%` cho tổng phơi nhiễm sàn CEX:

| Allocator | S1_PROP_FX_IDX | S2_CRYPTO_SPOT | S3A_FUND_CARRY | S3B_MACRO_ETF | S4_ETF40_MULTIFACTOR | S5_CME_FUTURES_PROP | Total CEX% |
|---|---:|---:|---:|---:|---:|---:|---:|
| Equal_Weight | 16.7% | 16.7% | 16.7% | 16.7% | 16.7% | 16.7% | 33.3% |
| ERC_Capped35 | 16.3% | 9.3% | 35.0% | 11.7% | 8.1% | 19.6% | 44.3% |
| ERC_LW_Capped35 | 16.1% | 9.5% | 35.0% | 11.7% | 8.2% | 19.4% | 44.5% |
| NCO_Capped35 | 17.3% | 6.5% | 35.0% | 10.1% | 3.0% | 28.1% | 41.5% |
| ERC_LW_CexCap25 | 21.8% | 4.9% | 20.1% | 15.9% | 11.1% | 26.2% | 25.0% |
| NCO_CexCap25 | 22.8% | 2.0% | 23.0% | 13.3% | 4.0% | 35.0% | 25.0% |
| HRP | 5.2% | 1.7% | 81.3% | 2.2% | 1.1% | 8.5% | 83.0% |

| Allocator | CEX -50% Hit% | CEX -50%+P99d% | Corr0.85 P99 DD% | Worst-Case DD% | 10k USD (USD / tr VND) | 50k USD (USD / tr VND) | 200k USD (USD / tr VND) |
|---|---:|---:|---:|---:|---|---|---|
| Equal_Weight | -16.67% | -17.07% | -18.83% | -18.83% (Corr0.85_Crunch_P99) | -1,883 / -48.0 tr | -9,415 / -240.1 tr | -37,660 / -960 tr |
| ERC_Capped35 | -22.16% | -22.46% | -13.00% | -22.46% (CEX_-50%_Haircut) | -2,246 / -57.3 tr | -11,230 / -286.4 tr | -44,920 / -1146 tr |
| ERC_LW_Capped35 | -22.27% | -22.57% | -13.18% | -22.57% (CEX_-50%_Haircut) | -2,257 / -57.6 tr | -11,285 / -287.8 tr | -45,140 / -1151 tr |
| NCO_Capped35 | -20.75% | -21.05% | -10.64% | -21.05% (CEX_-50%_Haircut) | -2,105 / -53.7 tr | -10,525 / -268.4 tr | -42,100 / -1074 tr |
| ERC_LW_CexCap25 | -12.50% | -12.91% | -11.53% | -12.91% (CEX_-50%_Haircut) | -1,291 / -32.9 tr | -6,455 / -164.6 tr | -25,820 / -658 tr |
| NCO_CexCap25 | -12.50% | -12.89% | -8.81% | -12.89% (CEX_-50%_Haircut) | -1,289 / -32.9 tr | -6,445 / -164.3 tr | -25,780 / -657 tr |
| HRP | -41.49% | -41.58% | -7.40% | -41.58% (CEX_-50%_Haircut) | -4,158 / -106.0 tr | -20,790 / -530.1 tr | -83,160 / -2121 tr |

## 2. Kiểm Định Chu Kỳ Tái Cân Bằng & Drift-Band Own-Book (`S1=0`, `S2=15`, `S3A=10`, `S3B/S4/S5=5 bps`)

| Allocator / Schedule | Rebals | Turnover/yr | Cost (bps/yr) | TE (bps) | OOS CAGR% | OOS MaxDD% | OOS Sharpe | OOS Calmar |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| NCO_CexCap25 / Daily | 1304 | 18.8% | 1.93 | 0.10 | +4.93% | 2.24% | 1.88 | 2.20 |
| NCO_CexCap25 / Weekly_Mon | 261 | 9.4% | 0.96 | 0.96 | +4.93% | 2.24% | 1.89 | 2.21 |
| NCO_CexCap25 / Monthly_1st | 59 | 4.3% | 0.45 | 1.84 | +4.93% | 2.23% | 1.89 | 2.21 |
| NCO_CexCap25 / Quarterly | 19 | 2.8% | 0.27 | 4.00 | +4.93% | 2.23% | 1.89 | 2.21 |
| NCO_CexCap25 / DriftBand_3pct | 1 | 0.8% | 0.09 | 9.28 | +4.89% | 2.23% | 1.88 | 2.19 |
| NCO_CexCap25 / DriftBand_5pct | 0 | 0.0% | 0.00 | 13.33 | +4.92% | 2.21% | 1.93 | 2.23 |
| ERC_LW_CexCap25 / Daily | 1304 | 23.0% | 2.52 | 0.11 | +5.53% | 2.24% | 2.06 | 2.47 |
| ERC_LW_CexCap25 / Weekly_Mon | 261 | 11.2% | 1.23 | 1.24 | +5.54% | 2.24% | 2.07 | 2.47 |
| ERC_LW_CexCap25 / Monthly_1st | 59 | 5.3% | 0.60 | 2.58 | +5.55% | 2.23% | 2.07 | 2.48 |
| ERC_LW_CexCap25 / Quarterly | 19 | 3.3% | 0.36 | 5.85 | +5.55% | 2.23% | 2.07 | 2.48 |
| ERC_LW_CexCap25 / DriftBand_3pct | 1 | 1.0% | 0.13 | 14.25 | +5.54% | 2.24% | 2.07 | 2.47 |
| ERC_LW_CexCap25 / DriftBand_5pct | 0 | 0.0% | 0.00 | 19.00 | +5.58% | 2.22% | 2.11 | 2.51 |

## 3. Kiểm Định Overlay Biến Động Vĩ Mô & Phanh DD Nhân Quả (`<= t-1`, 0 Magic-Number)

- **Quy tắc nhân quả (`<= t-1`):** Nếu `vol20[t-1] > P90 mở rộng` HOẶC `DD[t-1] > 5%`, cắt `50%` tỷ trọng nhánh beta cao (`S2_CRYPTO_SPOT`, `S4_ETF40_MULTIFACTOR`) sang T-Bill `0%` Cash (hoặc `50%` Cash + `50%` `S3B_MACRO_ETF`).
- **Phán quyết trung thực trên Blind OOS `2023–2024`:** **`KEEP_STATIC_CEXCAP25_DEFAULT`**

| Allocator / Variant | Risk-Off % | Avg Cash% | Switches | Cost bps/yr | OOS CAGR% | OOS MaxDD% | OOS Sharpe (Δ) | OOS Calmar (Δ) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| NCO_CexCap25 / Static_Monthly | 0.0% | 0.0% | 0 | 0.45 | +4.93% | 2.23% | 1.89 (+0.00) | 2.21 (+0.00) |
| NCO_CexCap25 / Causal_VolDD_TBILL_CASH_0PCT | 6.2% | 0.2% | 18 | 1.35 | +4.84% | 2.23% | 1.85 (-0.04) | 2.17 (-0.04) |
| NCO_CexCap25 / Causal_VolDD_TBILL50_S3B50 | 6.2% | 0.1% | 18 | 1.59 | +4.82% | 2.24% | 1.85 (-0.04) | 2.16 (-0.05) |
| ERC_LW_CexCap25 / Static_Monthly | 0.0% | 0.0% | 0 | 0.60 | +5.55% | 2.23% | 2.07 (+0.00) | 2.48 (+0.00) |
| ERC_LW_CexCap25 / Causal_VolDD_TBILL_CASH_0PCT | 4.3% | 0.3% | 34 | 4.83 | +5.36% | 2.33% | 2.00 (-0.07) | 2.30 (-0.18) |
| ERC_LW_CexCap25 / Causal_VolDD_TBILL50_S3B50 | 4.3% | 0.2% | 34 | 6.12 | +5.43% | 2.31% | 2.03 (-0.04) | 2.35 (-0.13) |

## 4. Quyết Định Sản Xuất Cho Quant Pod v2 (6 Sleeves)

1. **Trần nhóm CEX `<= 25%` hoàn thành mục tiêu sống còn:** Cắt sốc mất trắng `-50%` sàn CEX từ `-21.05%` (`NCO_Capped35`) xuống **`-12.89%`** (`NCO_CexCap25`, chỉ riêng CEX instant hit = `-12.50%`). Toàn bộ biên sập Black-Swan worst-case trên mốc `50k USD` giảm từ `-268.4 tr VND` xuống **`-164.3 tr VND`** (`NCO_CexCap25`) và **`-164.6 tr VND`** (`ERC_LW_CexCap25`) — bước vào vùng kiểm soát `CAUTION_AMBER` thay vì `BREACH_RED` ngay cả dưới kịch bản sập sàn `-50%`.
2. **Lịch tái cân bằng tối ưu cho Owner Solo:** **`Monthly_1st`** (`59` lần / 5 năm, phí `0.45 bps/yr`, OOS Sharpe `1.89`) hoặc **`DriftBand_3pct`** (`1` lần / 5 năm, phí `0.09 bps/yr`, OOS Sharpe `1.88`) tiết kiệm chi phí vượt trội so với `Daily` (`1.93 bps/yr`, `1304` lần) với sai số bám sát (`TE`) gần bằng 0.
3. **Overlay vĩ mô nhân quả (`KEEP_STATIC_CEXCAP25_DEFAULT`):** Toàn bộ kết quả kiểm định OOS được báo cáo nguyên trạng không tối ưu ngược; chọn cấu hình mặc định đơn giản nhất thắng thực tế trên OOS để tránh overfitting và giữ vận hành 1 người gọn nhẹ.

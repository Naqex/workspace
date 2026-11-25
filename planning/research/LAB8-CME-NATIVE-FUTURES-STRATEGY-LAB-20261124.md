---
doc_type: research_receipt
date: 2026-11-24
lane: risk-auditor
milestone: Wave2-Cycle4D-Lab8-CME-Native-Futures
holdout_rows_analysed: 0
order_send_count: 0
---

# Lab #8 — Phòng Thí Nghiệm CME-Native Futures Không Swap (`MES / MNQ / MGC / MCL / ZN / 6E`, `2015–2026`)

- **Generated UTC:** `2026-11-23T18:37:55.969759+00:00` (runtime `10.75s`)
- **Safety Seal:** Holdout `2025+` của `S1 PORT_7E` giữ **100% SEALED** (`lock=f0a6b43cb205535b...`, `holdout_rows_analysed = 0`, `OrderSend = 0`).
- **Dữ liệu CME liên tục (`0` skipped):** `ES=F, NQ=F, GC=F, CL=F, ZN=F, 6E=F` (`2015-01-02..2026-11-20 (2991 bars, Cl.A=1383d, Cl.B=1482d)`). Xử lý nhân quả cú sập âm `-37.63 USD` của `CL=F` ngày `2020-04-20` qua bộ lọc roll-safe (không rò rỉ tương lai, không NaN/Inf).
- **Mô hình phí CME Micro thực tế (`ZERO` retail CFD overnight swap):** Hoa hồng sàn+NFA `1.24–1.64 USD/RT` + `1–2` ticks trượt giá (sàn tối thiểu `1.5–2.5 bps` một chiều) + `3 bps/quý` (`12 bps/năm`) chi phí roll hợp đồng quý (`Mar/Jun/Sep/Dec`), stress ở cả `1x` và `2x`.
- **Kết quả Hội đồng Nghiên cứu (`m_total = 9`):** **`0/9` `APPROVE_FOR_INCUBATION`** | Ứng viên chính chọn hoàn toàn trên Cluster A: **`L8_A3_TSMOM_BLEND_LONG_BIAS`** | Export `sleeve7_cme_native_futures.json`: **`False`** (`None`).

## 1. Bảng Kiểm Định 9 Chiến Lược CME Futures (`Cluster A 2015–2020 -> Blind Cluster B 2021–2026`)

| Strategy ID | Verdict | Cl.A Sh | Cl.B 1x/2x CAGR% | Cl.B Sh | Cl.B DD% | BH-q | DSR | BE Mult | Cost bps/yr | r(S1)/r(S4) | COVID / 2022% |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| L8_A1_TSMOM_60D_6ASSET | KILL | 0.42 | +6.47% / +5.15% | 0.60 | 11.35% | 0.2109 | 0.472 | 6.6x | 124.4 | -0.02 / +0.06 | +6.8% / +21.2% |
| L8_A2_TSMOM_BLEND_20_60_120 | KILL | 0.54 | +3.23% / +2.25% | 0.43 | 8.72% | 0.2599 | 0.316 | 4.7x | 99.9 | -0.02 / +0.13 | +3.0% / +17.3% |
| L8_A3_TSMOM_BLEND_LONG_BIAS | KILL | 0.70 | +2.94% / +2.19% | 0.46 | 7.28% | 0.2599 | 0.340 | 5.3x | 79.4 | -0.04 / +0.28 | +1.2% / +7.8% |
| L8_B1_DONCHIAN_20_10_6ASSET | KILL | -0.07 | +0.79% / +0.03% | 0.14 | 12.50% | 0.3755 | 0.119 | 2.5x | 81.3 | +0.04 / +0.14 | +3.6% / +8.9% |
| L8_B2_DONCHIAN_55_20_6ASSET | KILL | 0.42 | +2.55% / +2.11% | 0.39 | 11.48% | 0.2599 | 0.286 | 7.5x | 45.3 | +0.01 / +0.17 | +1.9% / +3.7% |
| L8_B3_DONCHIAN_BLEND_20_55 | KILL | 0.17 | +1.72% / +1.11% | 0.28 | 8.71% | 0.3029 | 0.203 | 4.3x | 62.8 | +0.03 / +0.17 | +2.8% / +6.3% |
| L8_C1_RISKPARITY_TREND_GUARD | KILL | 0.70 | +5.71% / +5.18% | 0.67 | 9.91% | 0.2109 | 0.538 | 12.8x | 54.2 | -0.07 / +0.49 | -4.5% / -3.4% |
| L8_C2_COMM_EQ_BOND_XSEC_MOM | KILL | 0.05 | +1.20% / -0.19% | 0.17 | 12.68% | 0.3755 | 0.135 | 2.2x | 140.4 | -0.05 / +0.07 | +7.9% / +5.7% |
| L8_C3_SKEW_CRASH_RISKPARITY | KILL | 0.65 | +7.34% / +6.20% | 0.78 | 10.06% | 0.2109 | 0.650 | 8.1x | 109.9 | -0.06 / +0.33 | +1.6% / +8.9% |

- **Chẩn đoán trung thực (`0/9` duyệt trên 5.88 năm Blind Cluster B):** Không chiến lược nào vượt đồng thời toàn bộ 6 cổng — nổi bật nhất là `L8_C3_SKEW_CRASH_RISKPARITY` (`Cl.B CAGR +7.34%`, `2x +6.20%`, `Sharpe 0.78`, `DSR 0.650 >= 0.50`, `BE 8.1x`, `r(S1)=-0.06`, `2022 +8.9%`), đạt 5/6 cổng nhưng dừng tại **`G1_bh_fdr` (`q = 0.2109 > 0.10` trên `m = 9`)**. Về mặt thống kê, với `5.88` năm dữ liệu và `m = 9` thử nghiệm, vượt BH-FDR `q <= 0.10` đòi hỏi `Sharpe OOS >= ~0.95` trong khi CTA Futures cổ điển có kỳ vọng lịch sử `0.55–0.80` nhưng mạnh vượt trội về **Crisis Alpha** (như `L8_A1_TSMOM_60D_6ASSET` đạt **`+21.2%`** trong cú sập lãi suất `2022` với `r(S4) = +0.06`). Cổng fail-closed giữ `sleeve7_cme_native_futures.json` **không export**.

## 2. Triển Khai IBKR Own-Book Futures: Ký Quỹ Micro & Tác Động Vào Quant Pod v2 (`NCO_CexCap25`)

- **Tương quan `2020–2024` của `L8_A3_TSMOM_BLEND_LONG_BIAS` với các nhánh hiện có:** `S1_PROP_FX_IDX: -0.027`, `S2_CRYPTO_SPOT: +0.155`, `S3A_FUND_CARRY: +0.054`, `S3B_MACRO_ETF: +0.536`, `S4_ETF40_MULTIFACTOR: +0.329`, `S5_CME_FUTURES_PROP: -0.031`.

| IBKR Account Tier | Avg Init Margin (USD) | Avg Margin % | Peak Margin % | Micro Fit | Verdict |
|---|---:|---:|---:|---:|---|
| 25,000 USD | 809 USD | 3.2% | 8.6% | 0/6 | TOO_SMALL_USE_ETF |
| 50,000 USD | 1,618 USD | 3.2% | 8.6% | 2/6 | TOO_SMALL_USE_ETF |
| 100,000 USD | 3,235 USD | 3.2% | 8.6% | 3/6 | PARTIAL_HIGH_MIN_NOTIONAL |

| Pod v2 Allocator (Blind OOS 2023–2024) | Before (No S7) CAGR/DD/Sh/Cal | After (+S7) CAGR/DD/Sh/Cal | S7 Weight % |
|---|---|---|---:|
| NCO_CexCap25 | +4.95% / 2.23% / 1.89 / 2.21 | +4.88% / 2.13% / 1.93 / 2.29 | 5.8% |
| ERC_LW_CexCap25 | +5.56% / 2.24% / 2.07 / 2.48 | +5.08% / 2.15% / 1.91 / 2.36 | 10.7% |

## 3. Đối Chiếu Luật Thực Tế: Topstep 50K Prop vs IBKR Own-Book Futures

1. **Cảnh báo luật cứng Topstep (`topstep_standard_overnight_allowed = False`):** Topstep Combine & XFA **bắt buộc đóng toàn bộ vị thế trước `15:10 CT` mỗi ngày (CẤM giữ qua đêm)**. Do đó, toàn bộ chiến lược D1 Swing (`TSMOM`, `Donchian`, `Risk-Parity`) của Lab #8 **KHÔNG hợp lệ** trên Topstep Intraday chuẩn! Nếu giả định quỹ futures cho phép giữ qua đêm (`3,000` paths MC), EV ước tính chỉ đạt `-0.49x` (`CF24 -528 USD`, Pass `39.9%`).
2. **Định vị đúng sân chơi — IBKR Own-Book Futures (chỉ từ mốc vốn `>= 100,000 USD`):** Trên IBKR Own-Book, giữ lệnh qua đêm hoàn toàn hợp lệ và **KHÔNG mất retail CFD swap** — tổng phí thực đo ở Bảng 1 chỉ `45.3–140.4 bps/năm` (gồm `12 bps/năm` roll quý + phí/trượt giá tái cân bằng hàng ngày, rẻ hơn gấp `10–40` lần so với `-860..-3,014 bps/năm` swap CFD của Lab #3B!). Tuy nhiên, **rào cản thực tế là quy mô danh nghĩa tối thiểu mỗi 1 hợp đồng CME Micro** (`MES ~30k`, `MNQ ~43k`, `MGC ~27k`, `ZN ~112k USD`): ở mốc `25k–50k USD`, chỉ `0–2/6` hợp đồng vừa tỷ trọng mục tiêu mà không vượt đòn bẩy -> **ưu tiên dùng ETF (`S3B + S4`) cho mốc vốn `< 100k USD`**, chỉ nâng cấp sang CME Futures trực tiếp trên IBKR từ `100k–200k+ USD`.

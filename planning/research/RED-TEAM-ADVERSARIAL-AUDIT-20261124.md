# Institutional Red-Team Adversarial Audit — PORT_7E & PORT_9E (Dev 2018–2024)

- **Generated UTC:** `2026-11-23T16:41:41.026558+00:00`
- **Data Scope:** Sealed Development `2018-01-02..2024-12-31 (1564 days)` ONLY (`holdout_rows_analysed = 0`, `OrderSend = 0`)
- **Holdout Lock SHA-256:** `f0a6b43cb205535b...` (SEALED, untouched)
- **Seed / Runtime:** `seed = 20261124`, `31.708s`
- **Baseline 1.0x:** `PORT_7E` Ann `+7.73%`, DD `6.36%`, Calmar `1.22` | `PORT_9E` Ann `+8.83%`, DD `6.37%`, Calmar `1.39`
- **Overall Red-Team Verdict:** **`PASS_WITH_RED_TEAM_WARNINGS`**

## 1. Cost Stress Curve (`1.0x -> 3.0x` Spread/Slippage & Exact Breakeven Multiple)

| Cost Mult | PORT_7E Net (USD) | PORT_7E Ann% | PORT_7E DD% | PORT_7E Calmar | PORT_9E Net (USD) | PORT_9E Ann% | PORT_9E DD% | PORT_9E Calmar |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1.0x | +5413.4 | +7.73% | 6.36% | 1.22 | +6182.5 | +8.83% | 6.37% | 1.39 |
| 1.5x | +3258.6 | +4.66% | 8.44% | 0.55 | +3659.9 | +5.23% | 9.75% | 0.54 |
| 2.0x | +1103.8 | +1.58% | 12.30% | 0.13 | +1137.2 | +1.62% | 13.97% | 0.12 |
| 2.5x | -1051.1 | -1.50% | 19.43% | -0.08 | -1385.4 | -1.98% | 20.10% | -0.10 |
| 3.0x | -3205.9 | -4.58% | 36.50% | -0.13 | -3908.1 | -5.58% | 42.72% | -0.13 |

- **Exact Portfolio Breakeven Cost Multiple:** `PORT_7E = 2.26x` (verify PnL tại breakeven = `+0.00 USD`), `PORT_9E = 2.23x` (verify PnL tại breakeven = `-0.00 USD`).

### Chi tiết Breakeven từng Engine (9/9)

| Engine | Trades | Net 1.0x (USD) | Net 2.0x (USD) | Net 3.0x (USD) | Cost 1x (USD) | Breakeven Mult |
|---|---:|---:|---:|---:|---:|---:|
| E1_USDJPY_TOKYO | 1437 | +1021.3 | -440.6 | -1902.5 | 1461.9 | 1.70x |
| E2_USDJPY_EXP80 | 569 | +1450.3 | +548.1 | -354.1 | 902.2 | 2.61x |
| E3_GBPUSD_VH | 198 | +1096.5 | +706.0 | +315.4 | 390.6 | 3.81x |
| E4_US100_SESS40 | 414 | +629.2 | -153.7 | -936.5 | 782.9 | 1.80x |
| E5_US100_RS1130 | 261 | +630.8 | +203.4 | -223.9 | 427.4 | 2.48x |
| E6_EURJPY_VOLCOMP | 138 | +393.8 | +218.5 | +43.2 | 175.3 | 3.25x |
| E7_USDJPY_NY10ET | 105 | +191.6 | +22.1 | -147.4 | 169.5 | 2.13x |
| S6_FX_USD_BSK | 195 | +360.8 | +93.6 | -173.7 | 267.2 | 2.35x |
| S7_XAU_EXP120 | 204 | +408.3 | -60.1 | -528.5 | 468.4 | 1.87x |

## 2. Execution Latency & Adverse Fill Stress (`+1m` Delay & Worst-of-M1 Entry Bar)

| Stress Mode | PORT_7E Ann% | PORT_7E DD% | PORT_7E Calmar | PORT_7E Retained% | PORT_9E Ann% | PORT_9E DD% | PORT_9E Calmar | PORT_9E Retained% |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| +1m Fill Delay (Symmetric) | +4.80% | 7.86% | 0.61 | 62.1% | +5.87% | 8.05% | 0.73 | 66.4% |
| +1m Fill Delay (Adverse-Only Quote Fade) | +2.84% | 9.76% | 0.29 | 36.7% | +3.57% | 9.89% | 0.36 | 40.4% |
| Worst-of-M1 Entry Bar Fill | +3.35% | 9.10% | 0.37 | 43.3% | +4.08% | 9.36% | 0.44 | 46.2% |

## 3. Parameter Neighborhood Stability & Fragility Perturbation (`±10%, ±20%`)

### 3A. Dịch chuyển khoảng cách Stop-Loss (`-20% .. +20%`) trực tiếp trên M1 MAE path

| SL Mult | PORT_7E Ann% | PORT_7E DD% | PORT_7E Calmar | PORT_9E Ann% | PORT_9E DD% | PORT_9E Calmar |
|---|---:|---:|---:|---:|---:|---:|
| 0.80x | +7.47% | 8.31% | 0.90 | +8.64% | 8.84% | 0.98 |
| 0.90x | +8.16% | 7.43% | 1.10 | +9.11% | 8.64% | 1.05 |
| 1.00x | +7.73% | 6.36% | 1.22 | +8.83% | 6.37% | 1.39 |
| 1.10x | +6.81% | 5.76% | 1.18 | +7.77% | 5.67% | 1.37 |
| 1.20x | +6.47% | 5.12% | 1.26 | +7.36% | 5.16% | 1.43 |

### 3B. Monte Carlo Risk-Weight & Threshold-Dropout Jitter (200 draws)

| Portfolio | Jitter Band | Weight Ann (p05/med/p95) | Weight Calmar (p05/med) | Threshold Dropout Ann (p05/med) | Threshold Calmar (p05/med) | P(Ann > 0) |
|---|---|---:|---:|---:|---:|---:|
| PORT_7E | ±10% | +7.59% / +7.74% / +7.88% | 1.14 / 1.18 | +5.83% / +6.99% | 0.75 / 1.12 | 100.0% |
| PORT_7E | ±20% | +7.43% / +7.71% / +8.03% | 1.10 / 1.17 | +4.67% / +6.20% | 0.62 / 0.98 | 100.0% |
| PORT_9E | ±10% | +8.69% / +8.82% / +8.99% | 1.31 / 1.36 | +6.88% / +7.95% | 0.88 / 1.18 | 100.0% |
| PORT_9E | ±20% | +8.53% / +8.82% / +9.14% | 1.26 / 1.35 | +5.78% / +7.04% | 0.73 / 1.03 | 100.0% |

## 4. Top-K Lucky Trade Removal (Bỏ Top `1%, 3%, 5%` Lệnh Thắng Lớn Nhất)

| Drop Top % | PORT_7E Dropped | PORT_7E Ann% | PORT_7E Calmar | PORT_7E Retained% | PORT_9E Dropped | PORT_9E Ann% | PORT_9E Calmar | PORT_9E Retained% |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Top 1% | 30/2908 | +2.25% | 0.29 | 29.1% | 33/3245 | +2.83% | 0.38 | 32.0% |
| Top 3% | 88/2908 | -3.68% | -0.12 | -47.6% | 98/3245 | -3.91% | -0.13 | -44.3% |
| Top 5% | 146/2908 | -8.03% | -0.14 | -103.8% | 163/3245 | -8.80% | -0.14 | -99.7% |

## 5. Phân Rã Theo Năm (`2018..2024`), Volatility Regime & Cú Sốc Khủng Hoảng

| Year | PORT_7E Ret% | PORT_7E DD% | PORT_7E Sharpe | PORT_9E Ret% | PORT_9E DD% | PORT_9E Sharpe | Engines > 0 (of 9) |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2018 | +11.42% | 3.50% | 1.97 | +11.81% | 3.24% | 1.96 | 8/9 |
| 2019 | -0.23% | 4.79% | -0.05 | -0.32% | 4.93% | -0.06 | 5/9 |
| 2020 | +13.53% | 4.73% | 2.10 | +18.45% | 4.85% | 2.34 | 6/9 |
| 2021 | +1.94% | 4.11% | 0.50 | +2.40% | 4.91% | 0.60 | 5/9 |
| 2022 | +18.41% | 2.88% | 2.48 | +19.58% | 2.87% | 2.42 | 9/9 |
| 2023 | +2.07% | 6.26% | 0.31 | +3.30% | 6.25% | 0.45 | 6/9 |
| 2024 | +7.00% | 5.37% | 1.14 | +6.60% | 5.23% | 1.04 | 8/9 |

### Causal Volatility-Regime Terciles (20d Lagged Realized Vol)

| Vol Regime | Days | PORT_7E Ann% | PORT_7E Sharpe | PORT_9E Ann% | PORT_9E Sharpe | PORT_9E Max Daily DD% |
|---|---:|---:|---:|---:|---:|---:|
| LOW_VOL_BOTTOM_33PCT | 515 | +7.20% | 1.30 | +6.42% | 1.11 | 1.25% |
| MID_VOL_MIDDLE_33PCT | 514 | +5.02% | 0.85 | +6.67% | 1.04 | 2.24% |
| HIGH_VOL_TOP_33PCT | 515 | +11.59% | 1.82 | +14.08% | 1.95 | 2.23% |

### Named Macro Crisis Windows (2018–2024)

| Crisis Window | Period | Days | PORT_7E Ret% | PORT_7E DD% | PORT_9E Ret% | PORT_9E DD% | PORT_9E Max Daily DD% |
|---|---|---:|---:|---:|---:|---:|---:|
| 2018_Q4_Fed_QT | 2018-10-01..2018-12-31 | 62 | +7.07% | 1.65% | +7.33% | 1.86% | 0.99% |
| 2020_COVID_Crash | 2020-02-20..2020-04-30 | 50 | +5.98% | 2.57% | +10.20% | 2.33% | 1.26% |
| 2022_RateHike_Shock | 2022-01-01..2022-10-31 | 204 | +15.25% | 2.48% | +15.84% | 2.60% | 2.24% |
| 2023_SVB_Bank_Stress | 2023-03-08..2023-03-31 | 17 | -0.41% | 0.89% | +0.16% | 1.26% | 0.78% |
| 2024_Aug_Yen_Unwind | 2024-07-15..2024-08-31 | 35 | +1.99% | 2.10% | +1.73% | 2.71% | 2.23% |

## 6. Tail-Correlation & Simultaneous-Loss Shock vs FTMO `5.0%` Daily DD Limit

- **PORT_7E Pairwise Correlation:** All days mean `0.0411` (max `0.314`, `E4_US100_SESS40 x E5_US100_RS1130`) vs Worst-5% tail mean `-0.1144` (max `0.2247`, `E4_US100_SESS40 x E5_US100_RS1130`).
- **PORT_9E Pairwise Correlation:** All days mean `0.041` (max `0.3302`, `E3_GBPUSD_VH x S6_FX_USD_BSK`) vs Worst-5% tail mean `-0.0774` (max `0.2542`, `E4_US100_SESS40 x E5_US100_RS1130`).

### Top 5 Worst Historical Intraday DD Days (`PORT_9E`, Dev 2018–2024)

| Date | Losing Engines | Day Net 1x | M1 Daily DD 1x | Scaled 2.5x | Scaled 4.0x | Scaled 4.75x |
|---|---|---:|---:|---:|---:|---:|
| 2022-09-22 | 5 (E1, E2, E3, E6, S6) | -2.10% | 2.24% | 5.61% | 8.97% | 10.65% |
| 2024-08-05 | 6 (E2, E3, E4, E5, S6, S7) | -2.17% | 2.23% | 5.57% | 8.90% | 10.57% |
| 2020-12-07 | 5 (E1, E3, E5, S6, S7) | -1.26% | 1.54% | 3.84% | 6.14% | 7.29% |
| 2023-09-29 | 3 (E1, E2, E3) | -1.48% | 1.53% | 3.81% | 6.10% | 7.25% |
| 2022-02-14 | 4 (E1, E2, E3, E5) | -1.15% | 1.39% | 3.46% | 5.54% | 6.58% |

### Adversarial Flash-Crash Simultaneous `-1R` Shock Matrix (`corr -> 1.0`)

| Profile | Worst 3 Eng | Worst 5 Eng | All Uncapped | All + SYMCAP | Guarded (+KillSwitch) | < 5.0% FTMO Limit? |
|---|---:|---:|---:|---:|---:|---|
| Funded_Safe (1.00x, PORT_7E) | 1.84% | 2.84% | 3.50% | 3.25% | 2.75% | SAFE |
| P2_Verify (2.50x, PORT_7E) | 4.60% | 7.10% | 8.75% | 5.75% | 3.75% | SAFE |
| P1_Balanced (4.00x, PORT_9E) | 7.36% | 11.36% | 18.00% | 12.00% | 4.45% | SAFE |
| P1_Sprint (4.75x, PORT_9E) | 8.74% | 13.49% | 21.38% | 13.50% | 4.55% | SAFE |

## 7. DST / UTC-Offset Sensitivity Check

| DST Calendar Regime | Days | PORT_7E Ann% | PORT_7E Sharpe | PORT_9E Ann% | PORT_9E Sharpe | PORT_9E Win-Day% |
|---|---:|---:|---:|---:|---:|---:|
| US_EU_SUMMER_SYNC | 937 | +4.66% | 0.82 | +4.64% | 0.77 | 45.8% |
| US_EU_WINTER_SYNC | 520 | +11.32% | 1.92 | +13.03% | 2.00 | 44.8% |
| US_EU_DST_MISMATCH | 107 | +17.24% | 2.11 | +25.13% | 2.65 | 47.5% |

### Mô phỏng Lỗi Lệch Đồng Hồ Broker `±60 phút`

| Clock-Offset Bug Mode | PORT_7E Ann% | PORT_7E Calmar | PORT_7E Retained% | PORT_9E Ann% | PORT_9E Calmar | PORT_9E Retained% |
|---|---:|---:|---:|---:|---:|---:|
| +60m Late Entry (lệch +1h UTC) | +0.94% | 0.10 | 12.1% | +1.35% | 0.13 | 15.3% |
| -60m Early Flat (đóng sớm 1h) | +7.39% | 1.02 | 95.5% | +8.30% | 1.02 | 93.9% |

## 8. Bảng Kiểm Phản Biện & Khuyến Nghị Red-Team Cho Deployment

- `[WARN]` `cost_breakeven_port9e_gt_2_5x`
- `[PASS]` `latency_worst_m1_bar_positive`
- `[PASS]` `sl_pm20_all_positive`
- `[WARN]` `top5pct_lucky_removed_positive`
- `[PASS]` `funded_safe_simultaneous_shock_under_5pct`
- `[PASS]` `dst_mismatch_positive`
- **Cảnh báo biên chi phí (`breakeven < 2.0x`):** `E1_USDJPY_TOKYO, E4_US100_SESS40, S7_XAU_EXP120` — bắt buộc giám sát TCA thực tế trong 14 ngày Free Trial (`tca_reconcile.py`) và giữ `InpGuardMaxSpreadPoints` nghiêm ngặt.
- **Tính lồi của Trend-Following Intraday (Top-K Test):** `PORT_9E` vẫn dương `+2.83%/năm` khi bỏ Top 1% lệnh thắng (`33/3245` lệnh), nhưng chuyển âm khi bỏ Top 3%–5% lệnh thắng lớn nhất (mà giữ nguyên toàn bộ lệnh thua). Đây là đặc tính cấu trúc chuẩn của chiến lược breakout thuận xu hướng (tỷ lệ thắng `~45%`, lỗ chặn `-1R`, lãi chạy mở lên `+2R..+5R`) — đồng nghĩa **không được để VPS downtime hoặc tự ý đóng non lệnh đang lãi**, vì mất chỉ `3%` ngày breakout tốt nhất sẽ xóa biên lợi nhuận.
- **Bài học bắt buộc từ Shock Matrix:** Nếu bỏ `SYMCAP` và `Naqex_AccountOrchestrator` Global Kill-Switch, kịch bản flash-crash đồng thời ở mức P1 (`4.0x–4.75x`) sẽ vượt xa ngưỡng `5.0%` Daily DD của FTMO. Bắt buộc kích hoạt song song `InpGuardMaxSymbolRiskPct` + `InpKillDailyDdPct` trước khi mở tài khoản live.

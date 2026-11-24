# Lab #10 (Thế Hệ v2): Săn Alpha 7 Cổng `PASS_ROBUST`, Walk-Forward SL/TP (12m->4m) & Dynamic Prop Pacing

- **Phạm vi dữ liệu:** Dev niêm phong `2018–2024` (`Cluster A: 2018–2020`, `Blind Cluster B: 2021–2024`, `holdout_rows_analysed = 0`, `order_send_count = 0`, chạy cục bộ `hot_m1_cache` trong `16.78s`).

## 1A. Săn Động Cơ Trực Giao Qua Đủ 7 Cổng (`G0..G6`, `m_total = 16`)

- **Đỗ 7/7 cổng (`APPROVE_FOR_INCUBATION`):** **0/16** (`NONE`)
- **Đạt mức kiểm thử lại (`CONDITIONAL_RETEST`):** **1/16** (`L10_B2_EURUSD_VOLCOMP75`)

| Spec ID | Asset | N (A/B) | Cl.A R | Cl.B R | 2xCost R | BH-q | r(7E) | MC Same | B&S | Trim5W | WY-P10 | G6 | Council Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| L10_A1_GER40_FFM_BRK60 | GER40 | 204 (82/122) | +5.7 | -7.8 | -5.0 | 0.505 | -0.01 | 56% | NO | -10.7 | -5.1 | FAIL_FRAGILE | REJECT_KILLED |
| L10_A2_GER40_FFM_BRK80_TP2 | GER40 | 147 (64/83) | -1.1 | -7.2 | -10.3 | 0.637 | +0.03 | 22% | NO | -14.9 | -8.0 | FAIL_FRAGILE | REJECT_KILLED |
| L10_B1_GBPJPY_VOLCOMP75 | GBPJPY | 144 (57/87) | -3.1 | -0.5 | -4.3 | 0.505 | +0.08 | 40% | NO | -10.4 | -4.5 | FAIL_FRAGILE | REJECT_KILLED |
| L10_B2_EURUSD_VOLCOMP75 | EURUSD | 117 (44/73) | +5.2 | +4.8 | +8.7 | 0.032 | +0.02 | 98% | OK | +3.6 | -3.4 | PASS_ROBUST | CONDITIONAL_RETEST |
| L10_B3_AUDUSD_VOLCOMP75 | AUDUSD | 115 (50/65) | +1.5 | -4.3 | -4.1 | 0.505 | +0.04 | 41% | NO | -6.9 | -6.9 | FAIL_FRAGILE | REJECT_KILLED |
| L10_B4_USDCAD_VOLCOMP75 | USDCAD | 112 (48/64) | +1.8 | -2.1 | -1.3 | 0.505 | +0.01 | 59% | NO | -5.8 | -3.5 | FAIL_FRAGILE | REJECT_KILLED |
| L10_C1_XAU_LDN_FADE_TP12 | XAUUSD | 38 (17/21) | -3.1 | -7.4 | -11.5 | 0.991 | +0.02 | 0% | NO | -12.1 | -4.5 | FAIL_FRAGILE | REJECT_KILLED |
| L10_C2_US500_NOON_FADE_TP10 | US500 | 95 (41/54) | -7.4 | -11.5 | -21.4 | 0.991 | -0.10 | 0% | NO | -21.5 | -6.1 | FAIL_FRAGILE | REJECT_KILLED |
| L10_C3_GER40_MID_FADE_TP10 | GER40 | 50 (26/24) | -3.7 | +0.7 | -3.6 | 0.650 | -0.01 | 29% | NO | -5.6 | -3.8 | FAIL_FRAGILE | REJECT_KILLED |
| L10_C4_EURUSD_NY_FADE_TP10 | EURUSD | 56 (21/35) | -0.8 | -0.5 | -1.8 | 0.650 | -0.15 | 46% | NO | -3.0 | -2.6 | FAIL_FRAGILE | REJECT_KILLED |
| L10_D1_EURUSD_NY10ET_CONT | EURUSD | 144 (65/79) | -3.3 | -0.6 | -5.2 | 0.650 | -0.02 | 38% | NO | -8.8 | -4.4 | FAIL_FRAGILE | REJECT_KILLED |
| L10_D2_GBPJPY_NY10ET_CONT | GBPJPY | 115 (48/67) | -7.3 | +3.9 | -4.0 | 0.650 | +0.04 | 32% | NO | -7.7 | -3.9 | FAIL_FRAGILE | REJECT_KILLED |
| L10_D3_XAUUSD_NY10ET_CONT | XAUUSD | 137 (40/97) | -0.2 | -1.5 | -5.8 | 0.607 | +0.01 | 70% | NO | -8.8 | -6.7 | FAIL_FRAGILE | REJECT_KILLED |
| L10_D4_AUDUSD_NY10ET_CONT | AUDUSD | 88 (32/56) | -5.8 | +1.3 | -5.4 | 0.650 | -0.04 | 24% | NO | -7.3 | -4.0 | FAIL_FRAGILE | REJECT_KILLED |
| L10_D5_EURUSD_WMR16_REV | EURUSD | 216 (86/130) | -4.4 | -8.3 | -14.9 | 0.917 | +0.01 | 11% | NO | -19.6 | -6.9 | FAIL_FRAGILE | REJECT_KILLED |
| L10_D6_USDCAD_WMR16_REV | USDCAD | 272 (104/168) | -2.2 | -21.0 | -25.7 | 0.950 | +0.06 | 1% | NO | -31.7 | -9.2 | FAIL_FRAGILE | REJECT_KILLED |

## 1B. Walk-Forward SL/TP Trượt (`12` Tháng Học -> `4` Tháng Chạy OOS, `2019–2024`)

- **Tổng hợp `PORT_7E` (`2678` lệnh OOS):** Fixed Baseline PF = **`1.149`** (`+126.2R`) · Walk-Forward 12m->4m PF = **`1.09`** (`+80.5R`) · In-Sample Oracle PF = **`1.162`** -> Khoảng cách ảo giác Overfit (`Oracle - WF`) = **`+0.072`** · Khuyến nghị: **`KEEP_FIXED_HOLD_TO_FLAT`**.

| Engine | Core | N OOS | Fixed PF (R) | WF 12m->4m PF (R) | Oracle PF (Combo) | WF-Base ΔPF | Overfit Gap |
|---|---|---|---|---|---|---|---|
| E1_USDJPY_TOKYO | 7E | 1216 | 1.086 (+48.0R) | 1.023 (+13.0R) | 1.088 (1.25x/3.0R) | -0.063 | +0.065 |
| E2_USDJPY_EXP80 | 7E | 487 | 1.276 (+29.0R) | 1.239 (+27.3R) | 1.291 (1.25x/3.0R) | -0.037 | +0.052 |
| E3_GBPUSD_VH | 7E | 173 | 1.423 (+15.2R) | 1.328 (+13.1R) | 1.449 (1.25x/3.0R) | -0.095 | +0.121 |
| E4_US100_SESS40 | 7E | 368 | 1.106 (+7.7R) | 1.051 (+4.1R) | 1.106 (1.00x/FLAT) | -0.055 | +0.055 |
| E5_US100_RS1130 | 7E | 224 | 1.181 (+7.6R) | 1.142 (+7.3R) | 1.181 (1.00x/FLAT) | -0.039 | +0.039 |
| E6_EURJPY_VOLCOMP | 7E | 123 | 1.656 (+12.7R) | 1.256 (+6.4R) | 1.702 (1.00x/3.0R) | -0.400 | +0.446 |
| E7_USDJPY_NY10ET | 7E | 87 | 1.435 (+6.0R) | 1.546 (+9.3R) | 1.546 (0.75x/FLAT) | +0.111 | +0.000 |
| S6_FX_USD_BSK | Sat | 163 | 1.315 (+9.7R) | 1.190 (+6.5R) | 1.364 (1.00x/2.0R) | -0.125 | +0.174 |
| S7_XAU_EXP120 | Sat | 176 | 1.283 (+10.6R) | 1.294 (+14.2R) | 1.314 (1.00x/3.0R) | +0.011 | +0.020 |

## 1C. Dynamic Prop Pacing (`N = 5,000` Đường MC, `PORT_7E + 1 CONDITIONAL_PASS_ROBUST_V2 (L10_B2_EURUSD_VOLCOMP75)`)

| Prop Firm | Policy | Pass 24m% | Med Days Pass | Med Days Pay1 | Breach% | Wipeout% | OOP95 USD | EV 24m USD | EV/Fee |
|---|---|---|---|---|---|---|---|---|---|
| THE5ERS_HS_5K | P1_Balanced_Static | 63.5% | 126 | 154 | 3.7% | 0.00% | 39.0 | +280.5 | +7.19x |
| THE5ERS_HS_5K | P1_Sprint_Static | 57.6% | 113 | 145 | 5.5% | 0.00% | 78.0 | +253.3 | +6.50x |
| THE5ERS_HS_5K | Dyn_ProfitLock_45x | 62.9% | 121 | 152 | 4.2% | 0.00% | 39.0 | +276.6 | +7.09x |
| THE5ERS_HS_5K | Dyn_FastStart_SafeLock50 | 75.0% | 148 | 175 | 17.2% | 0.00% | 78.0 | +334.0 | +8.56x |
| THE5ERS_HS_5K | Breadth_V2_DynProfitLock | 59.6% | 124 | 151 | 4.5% | 0.00% | 39.0 | +259.1 | +6.64x |
| FTMO_SWING_10K | P1_Balanced_Static | 63.6% | 126 | 154 | 3.7% | 0.00% | 168.0 | +538.1 | +3.20x |
| FTMO_SWING_10K | P1_Sprint_Static | 57.7% | 111 | 145 | 5.5% | 0.00% | 336.0 | +478.4 | +2.85x |
| FTMO_SWING_10K | Dyn_ProfitLock_45x | 63.0% | 120 | 151 | 4.2% | 0.00% | 168.0 | +530.7 | +3.16x |
| FTMO_SWING_10K | Dyn_FastStart_SafeLock50 | 75.0% | 146 | 174 | 17.2% | 0.00% | 336.0 | +646.4 | +3.85x |
| FTMO_SWING_10K | Breadth_V2_DynProfitLock | 59.7% | 122 | 150 | 4.5% | 0.00% | 168.0 | +491.6 | +2.93x |


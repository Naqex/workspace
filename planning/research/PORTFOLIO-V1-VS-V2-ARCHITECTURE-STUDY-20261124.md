# Nghiên Cứu Chốt Kiến Trúc Danh Mục: `Portfolio v1` vs `Portfolio v2` (Dev `2018–2024`, Holdout `2025+` Niêm Phong)

- **Phạm vi dữ liệu:** `2018-01-02..2024-12-31` (`holdout_rows_analysed = 0`, `order_send_count = 0`, `m_total = 6` cấu trúc đăng ký trước, thời gian chạy `21.84s`).
- **Chuẩn thực thi M1 giống nhau 100%:** Floating-equity Prague-reset, `max_symbol_concurrent_risk = 1.0%`, chặn tin đỏ chính thức `±5m`, cùng `seed = 20261124` (`N = 5000` đường MC).

## 1. Bảng So Sánh Hiệu Suất & Kháng Chi Phí (`1.0×` / `1.5×` / `2.0×` Friction)

| Kiến trúc | EAs | Trd/Yr | Ann 1x% | Cl.A / Cl.B% | Peak DD% | Calmar 1x | Calmar 1.5x | Calmar 2.0x | Năm tệ nhất | +Yrs | Kết luận |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A0_V1_CORE7_INCUMBENT | 7 | 414 | +7.85% | +9.4/+6.7 | 8.19% | 0.96 | 0.54 | 0.21 | 2019 (+1.22%) | 7/7 | INCUMBENT_BASELINE |
| A1_V1_LIVE8_INCUMBENT | 8 | 438 | +8.28% | +10.5/+6.6 | 9.12% | 0.91 | 0.48 | 0.19 | 2023 (+0.82%) | 7/7 | INCUMBENT_BASELINE |
| A2_V2_ROBUST_TIER_8E | 8 | 436 | +7.55% | +9.8/+5.8 | 8.96% | 0.84 | 0.52 | 0.23 | 2023 (+1.10%) | 7/7 | MIXED_TRADEOFF_KEEP_V1_DEFAULT |
| A3_V2_PRUNE_FRAGILE_6E | 6 | 179 | +6.73% | +9.7/+4.5 | 9.58% | 0.70 | 0.47 | 0.26 | 2023 (+1.47%) | 7/7 | REJECT_INFERIOR_TO_V1 |
| A4_V2_PURE_PASS_4E | 4 | 88 | +6.18% | +7.0/+5.6 | 7.86% | 0.79 | 0.50 | 0.26 | 2023 (+1.69%) | 7/7 | MIXED_TRADEOFF_KEEP_V1_DEFAULT |
| A5_V2_ROBUST_TIER_9E_EUR | 9 | 451 | +7.05% | +9.7/+5.1 | 7.54% | 0.94 | 0.57 | 0.27 | 2024 (+0.87%) | 7/7 | MIXED_TRADEOFF_KEEP_V1_DEFAULT |

## 2. Mô Phỏng Vòng Đời Prop Firm (`N = 5,000` Đường MC — `1.0×` & Stress `1.5×` Chi Phí)

| Kiến trúc | Quỹ / Policy | Pass 24m% (1x / 1.5x) | Med Days Pass | Breach% | Wipeout% | OOP95 USD | EV/Fee (1x / 1.5x) |
|---|---|---|---|---|---|---|---|
| A0_V1_CORE7_INCUMBENT | FTMO_SWING_10K · P1_Balanced_Static | 66.0% / 45.9% | 126d / 132d | 1.9% | 0.00% | 168 | +3.43x / +1.24x |
| A0_V1_CORE7_INCUMBENT | FTMO_SWING_10K · Dyn_ProfitLock_45x | 64.9% / 44.6% | 115d / 114d | 2.5% | 0.00% | 168 | +3.43x / +1.23x |
| A0_V1_CORE7_INCUMBENT | THE5ERS_HS_5K · P1_Balanced_Static | 66.1% / 45.8% | 127d / 133d | 1.9% | 0.00% | 39 | +7.61x / +3.24x |
| A0_V1_CORE7_INCUMBENT | THE5ERS_HS_5K · Dyn_ProfitLock_45x | 64.9% / 44.6% | 115d / 114d | 2.5% | 0.00% | 39 | +7.64x / +3.26x |
| A1_V1_LIVE8_INCUMBENT | FTMO_SWING_10K · P1_Balanced_Static | 66.7% / 45.7% | 127d / 132d | 2.8% | 0.00% | 168 | +3.63x / +1.28x |
| A1_V1_LIVE8_INCUMBENT | FTMO_SWING_10K · Dyn_ProfitLock_45x | 65.1% / 46.1% | 113d / 115d | 3.2% | 0.00% | 168 | +3.61x / +1.34x |
| A1_V1_LIVE8_INCUMBENT | THE5ERS_HS_5K · P1_Balanced_Static | 66.6% / 45.6% | 127d / 132d | 2.8% | 0.00% | 39 | +8.06x / +3.33x |
| A1_V1_LIVE8_INCUMBENT | THE5ERS_HS_5K · Dyn_ProfitLock_45x | 65.0% / 46.2% | 113d / 116d | 3.2% | 0.00% | 39 | +8.04x / +3.48x |
| A2_V2_ROBUST_TIER_8E | FTMO_SWING_10K · P1_Balanced_Static | 69.0% / 49.7% | 135d / 141d | 1.8% | 0.00% | 168 | +3.44x / +1.36x |
| A2_V2_ROBUST_TIER_8E | FTMO_SWING_10K · Dyn_ProfitLock_45x | 66.8% / 48.0% | 127d / 130d | 2.5% | 0.00% | 168 | +3.31x / +1.32x |
| A2_V2_ROBUST_TIER_8E | THE5ERS_HS_5K · P1_Balanced_Static | 68.9% / 49.7% | 135d / 141d | 1.8% | 0.00% | 39 | +7.59x / +3.44x |
| A2_V2_ROBUST_TIER_8E | THE5ERS_HS_5K · Dyn_ProfitLock_45x | 66.7% / 48.0% | 128d / 130d | 2.5% | 0.00% | 39 | +7.34x / +3.38x |
| A3_V2_PRUNE_FRAGILE_6E | FTMO_SWING_10K · P1_Balanced_Static | 62.1% / 46.6% | 138d / 147d | 3.1% | 0.00% | 168 | +2.65x / +1.14x |
| A3_V2_PRUNE_FRAGILE_6E | FTMO_SWING_10K · Dyn_ProfitLock_45x | 61.3% / 45.4% | 127d / 134d | 4.2% | 0.00% | 168 | +2.65x / +1.11x |
| A3_V2_PRUNE_FRAGILE_6E | THE5ERS_HS_5K · P1_Balanced_Static | 62.0% / 46.5% | 139d / 147d | 3.1% | 0.00% | 39 | +6.01x / +3.01x |
| A3_V2_PRUNE_FRAGILE_6E | THE5ERS_HS_5K · Dyn_ProfitLock_45x | 61.3% / 45.3% | 129d / 134d | 4.2% | 0.00% | 39 | +6.03x / +3.00x |
| A4_V2_PURE_PASS_4E | FTMO_SWING_10K · P1_Balanced_Static | 59.5% / 43.0% | 156d / 159d | 1.2% | 0.00% | 168 | +2.17x / +0.83x |
| A4_V2_PURE_PASS_4E | FTMO_SWING_10K · Dyn_ProfitLock_45x | 57.0% / 42.2% | 142d / 145d | 1.9% | 0.00% | 168 | +2.10x / +0.82x |
| A4_V2_PURE_PASS_4E | THE5ERS_HS_5K · P1_Balanced_Static | 59.4% / 43.0% | 156d / 158d | 1.2% | 0.00% | 39 | +5.01x / +2.37x |
| A4_V2_PURE_PASS_4E | THE5ERS_HS_5K · Dyn_ProfitLock_45x | 56.9% / 42.1% | 144d / 146d | 1.9% | 0.00% | 39 | +4.87x / +2.36x |
| A5_V2_ROBUST_TIER_9E_EUR | FTMO_SWING_10K · P1_Balanced_Static | 70.4% / 50.6% | 142d / 150d | 1.1% | 0.00% | 168 | +3.23x / +1.28x |
| A5_V2_ROBUST_TIER_9E_EUR | FTMO_SWING_10K · Dyn_ProfitLock_45x | 70.2% / 51.5% | 130d / 138d | 1.4% | 0.00% | 168 | +3.31x / +1.38x |
| A5_V2_ROBUST_TIER_9E_EUR | THE5ERS_HS_5K · P1_Balanced_Static | 70.3% / 50.6% | 142d / 149d | 1.1% | 0.00% | 39 | +7.12x / +3.23x |
| A5_V2_ROBUST_TIER_9E_EUR | THE5ERS_HS_5K · Dyn_ProfitLock_45x | 70.2% / 51.5% | 131d / 139d | 1.4% | 0.00% | 39 | +7.29x / +3.43x |

## 3. Phân Tích Theo Từng Năm Dương Lịch (`2018–2024`, M1 `1.0×`)

| Kiến trúc | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 |
|---|---|---|---|---|---|---|---|
| A0_V1_CORE7_INCUMBENT | +13.79% | +1.22% | +13.21% | +3.87% | +16.35% | +1.50% | +5.05% |
| A1_V1_LIVE8_INCUMBENT | +13.12% | +2.58% | +15.77% | +5.30% | +16.16% | +0.82% | +4.21% |
| A2_V2_ROBUST_TIER_8E | +10.14% | +5.24% | +14.08% | +4.71% | +14.03% | +1.10% | +3.56% |
| A3_V2_PRUNE_FRAGILE_6E | +6.33% | +8.32% | +14.51% | +4.35% | +10.53% | +1.47% | +1.61% |
| A4_V2_PURE_PASS_4E | +4.54% | +7.73% | +8.59% | +2.85% | +13.07% | +1.69% | +4.75% |
| A5_V2_ROBUST_TIER_9E_EUR | +8.62% | +7.00% | +13.33% | +4.67% | +12.26% | +2.60% | +0.87% |

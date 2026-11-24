# Kiểm Toán Cổng Robustness 4 Trụ Cột Trên 9 Động Cơ Dev (`2018–2024`, `holdout_rows = 0`)

- **Phạm vi dữ liệu:** `2018-01-02..2024-12-31` (niêm phong tuyệt đối `Holdout 2025+`, `holdout_rows_analysed = 0`, `order_send_count = 0`).
- **Mô phỏng Random-Entry MC trên nến M5 thật (`hot_m1_cache`):** `1000` lần/động cơ, thời gian chạy `8.33s`.
- **Tổng hợp nhanh:** `MC 50/50 >= 90%`: **9/9** · `MC Same-Side >= 90%`: **9/9** · `Cả BUY & SELL dương`: **5/9** · `Cắt Top-5% vẫn dương`: **6/9**.
- **Phân loại:** `PASS_ROBUST = 4/9` · `WARN_ASYMMETRY_OR_YEAR = 2/9` · `FAIL_FRAGILE = 3/9`.

## Bảng Kết Quả Chi Tiết 9 Động Cơ (Dev `2018–2024`)

| Engine | Core | N | Raw R | MC 50/50 | MC Same-Side | BUY R (MC) | SELL R (MC) | Trim-5% Win (PF) | Trim-5% All | Worst Yr | WY-P10 | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| E1_USDJPY_TOKYO | 7E | 1437 | +76.5R | 100.0% | 100.0% | +77.7R (100%) | -1.2R (97%) | -86.9R (0.87) | -198.2R | 2019 -24.0R | -21.0R | FAIL_FRAGILE |
| E2_USDJPY_EXP80 | 7E | 569 | +34.8R | 100.0% | 100.0% | +37.3R (100%) | -2.5R (85%) | +1.2R (1.01) | -15.4R | 2024 +0.6R | -2.9R | WARN_ASYMMETRY_OR_YEAR |
| E3_GBPUSD_VH | 7E | 198 | +14.2R | 99.9% | 99.8% | +4.7R (95%) | +9.5R (99%) | +2.8R (1.07) | -5.0R | 2018 -1.0R | -3.3R | PASS_ROBUST |
| E4_US100_SESS40 | 7E | 414 | +14.1R | 100.0% | 99.7% | +4.2R (92%) | +9.9R (100%) | -2.6R (0.97) | -11.5R | 2019 -1.3R | -4.4R | FAIL_FRAGILE |
| E5_US100_RS1130 | 7E | 261 | +12.2R | 99.7% | 99.7% | +5.9R (94%) | +6.4R (98%) | +1.8R (1.04) | -5.5R | 2023 -3.5R | -3.9R | PASS_ROBUST |
| E6_EURJPY_VOLCOMP | 7E | 138 | +13.1R | 99.4% | 99.0% | +8.2R (98%) | +4.9R (93%) | +4.8R (1.21) | +1.1R | 2021 -2.0R | -2.4R | PASS_ROBUST |
| E7_USDJPY_NY10ET | 7E | 105 | +7.3R | 97.9% | 96.6% | +5.9R (95%) | +1.4R (82%) | +1.1R (1.08) | -0.7R | 2020 -1.3R | -1.3R | PASS_ROBUST |
| S6_FX_USD_BSK | Sat | 195 | +10.0R | 99.2% | 99.1% | -0.9R (68%) | +10.9R (100%) | +1.0R (1.03) | -3.8R | 2024 -1.9R | -2.4R | WARN_ASYMMETRY_OR_YEAR |
| S7_XAU_EXP120 | Sat | 204 | +12.0R | 100.0% | 99.9% | -1.4R (79%) | +13.3R (100%) | -3.2R (0.93) | -10.3R | 2019 -3.4R | -3.5R | FAIL_FRAGILE |

## Bảng Xếp Hạng Theo Điểm Năm Tệ Nhất (`mc_worst_year_p10_r`)

| Hạng | Động cơ | Nhóm | WY-P10 Score | Năm tệ nhất | Tổng R | Kết luận |
|---|---|---|---|---|---|---|
| 1 | E7_USDJPY_NY10ET | PORT_7E | -1.3R | -1.3R | +7.3R | PASS_ROBUST |
| 2 | S6_FX_USD_BSK | Satellite | -2.4R | -1.9R | +10.0R | WARN_ASYMMETRY_OR_YEAR |
| 3 | E6_EURJPY_VOLCOMP | PORT_7E | -2.4R | -2.0R | +13.1R | PASS_ROBUST |
| 4 | E2_USDJPY_EXP80 | PORT_7E | -2.9R | +0.6R | +34.8R | WARN_ASYMMETRY_OR_YEAR |
| 5 | E3_GBPUSD_VH | PORT_7E | -3.3R | -1.0R | +14.2R | PASS_ROBUST |
| 6 | S7_XAU_EXP120 | Satellite | -3.5R | -3.4R | +12.0R | FAIL_FRAGILE |
| 7 | E5_US100_RS1130 | PORT_7E | -3.9R | -3.5R | +12.2R | PASS_ROBUST |
| 8 | E4_US100_SESS40 | PORT_7E | -4.4R | -1.3R | +14.1R | FAIL_FRAGILE |
| 9 | E1_USDJPY_TOKYO | PORT_7E | -21.0R | -24.0R | +76.5R | FAIL_FRAGILE |


---
doc_type: research_receipt
date: 2026-11-24
lane: risk-auditor
milestone: Wave2-Lab6-MetaLabeling
holdout_rows_analysed: 0
order_send_count: 0
---

# Lab #6 — Kiểm Định Purged Embargo Walk-Forward Meta-Labeling (AFML Ch. 3, 7 & 10)

- **Generated UTC:** `2026-11-23T17:56:39.833926+00:00` (runtime `1.071s`)
- **Safety Seal:** Holdout `2025–2026` của `PORT_7E` giữ **100% SEALED** (`lock=f0a6b43cb205535b...`, `holdout_rows_analysed = 0`, `OrderSend = 0`).
- **Giao thức chống rò rỉ (AFML Ch. 7):** Expanding Walk-Forward mỗi `90` ngày, **Purge `5` ngày + Embargo `10` ngày** giữa tập huấn luyện và tập kiểm định; chuẩn hóa đặc trưng và ngưỡng kích thước lệnh khớp 100% trong tập huấn luyện.
- **Tín hiệu gốc giữ nguyên tuyệt đối:** Không thay đổi điểm vào/hướng lệnh của `PORT_7E` và `Crypto F4_4H_EMA`; Meta-Labeler chỉ điều chỉnh kích thước vị thế (`[0.50x..1.25x]`) hoặc lọc bỏ nhóm đuôi 20% xác suất thấp nhất (`Toxic Filter`).

## 1. Đối Đầu Trực Tiếp Trên `PORT_7E` Intraday Prop (Blind Cluster B `2022–2024`, Dev Only)

- **Mẫu quan sát:** `2912` tổng mẫu (`1349` trên Blind Cluster B từ `2022-01-01`)
- **6 Đặc trưng nhân quả (`<= t-1`):** `port_vol_20d, vol_ratio_5_20, port_ret_20d, port_dd_60d, signal_density_5d, eng_trailing_wr20`
- **Phán quyết trung thực:** **`REJECT_KEEP_RAW_WHITEBOX`** (ứng viên tốt nhất: `LOGISTIC_TOXIC_FILTER`)

| Policy | Avg Size | Kept % | Brier (Skill) | ROC-AUC | Cl.B CAGR% | Cl.B MaxDD% | Cl.B Sharpe | Cl.B Calmar | ΔSharpe / ΔCalmar |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| RAW_WHITEBOX_1X | 1.00x | 100.0% | baseline | — | +10.65% | 5.83% | 1.36 | 1.83 | +0.00 / +0.00 |
| LOGISTIC_SCALE_050_125 | 0.90x | 100.0% | 0.2509 (-0.004) | 0.501 | +10.20% | 6.81% | 1.36 | 1.50 | +0.00 / -0.33 |
| LOGISTIC_TOXIC_FILTER | 0.84x | 83.9% | 0.2509 (-0.004) | 0.501 | +11.09% | 5.83% | 1.51 | 1.90 | +0.15 / +0.07 |
| SHALLOW_TREE_SCALE_050_125 | 0.87x | 100.0% | 0.2510 (-0.004) | 0.468 | +6.65% | 6.81% | 0.97 | 0.98 | -0.39 / -0.85 |
| SHALLOW_TREE_TOXIC_FILTER | 0.92x | 91.8% | 0.2510 (-0.004) | 0.468 | +8.42% | 5.83% | 1.14 | 1.44 | -0.22 / -0.39 |

## 2. Đối Đầu Trực Tiếp Trên `Crypto F4_4H_EMA_24_120_BTC` (Blind Cluster B `2024–2026`)

- **Mẫu quan sát:** `1564` tổng mẫu (`570` trên Blind Cluster B từ `2024-01-01`)
- **6 Đặc trưng nhân quả (`<= t-1`):** `btc_vol_20d, btc_vol_ratio_5_20, btc_ret_20d, btc_dd_60d, f4_ret_20d, f4_dd_60d`
- **Phán quyết trung thực:** **`REJECT_KEEP_RAW_WHITEBOX`** (ứng viên tốt nhất: `SHALLOW_TREE_SCALE_050_125`)

| Policy | Avg Size | Kept % | Brier (Skill) | ROC-AUC | Cl.B CAGR% | Cl.B MaxDD% | Cl.B Sharpe | Cl.B Calmar | ΔSharpe / ΔCalmar |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| RAW_WHITEBOX_1X | 1.00x | 100.0% | baseline | — | +5.69% | 9.72% | 0.78 | 0.59 | +0.00 / +0.00 |
| LOGISTIC_SCALE_050_125 | 0.70x | 100.0% | 0.2510 (-0.004) | 0.508 | +6.24% | 7.56% | 1.00 | 0.83 | +0.22 / +0.24 |
| LOGISTIC_TOXIC_FILTER | 0.60x | 60.4% | 0.2510 (-0.004) | 0.508 | +5.29% | 7.80% | 0.82 | 0.68 | +0.04 / +0.09 |
| SHALLOW_TREE_SCALE_050_125 | 0.72x | 100.0% | 0.2513 (-0.005) | 0.503 | +7.52% | 7.72% | 1.15 | 0.97 | +0.37 / +0.38 |
| SHALLOW_TREE_TOXIC_FILTER | 0.76x | 76.3% | 0.2513 (-0.005) | 0.503 | +6.38% | 8.08% | 0.90 | 0.79 | +0.12 / +0.20 |

## 3. Phân Tích Định Lượng & Khuyến Nghị Điều Hành

1. **Tại sao Meta-Labeling cần tiêu chuẩn khắt khe (`ΔSharpe > +0.05`, `ΔCalmar > +0.05` VÀ `Brier Skill > 0`):** Mô hình phân loại nhị phân trên chuỗi lợi suất tài chính có tỷ lệ tín hiệu/nhiễu rất thấp. Nếu `Brier Skill <= 0` hoặc `ROC-AUC ≈ 0.50`, mô hình không có khả năng phân biệt lệnh thắng/thua ngoài mẫu tốt hơn tung đồng xu. Điểm đáng chú ý trên `Crypto F4_4H_EMA` là `SHALLOW_TREE_SCALE_050_125` đẩy Sharpe từ `0.78 -> 1.15` dù `ROC-AUC = 0.503` và `Brier Skill = -0.005`: hiệu ứng này đến từ **implicit volatility/drawdown damping** (`avg_size = 0.72x` giảm phơi nhiễm khi biến động tăng) chứ không phải năng lực phân loại thắng/thua thực sự, nên gate `Brier Skill > 0` bác bỏ một cách kỷ luật để tránh chọn nhầm lớp ML cồng kềnh thay cho rule quản trị vốn white-box đơn giản.
2. **Cảnh báo rủi ro với chiến lược Trend-Following lồi (`PORT_7E` & `F4_4H_EMA`):** Như đã chứng minh ở `RED-TEAM-ADVERSARIAL-AUDIT-20261124.md` (Test 4 Top-K), phần lớn lợi nhuận của hệ thống breakout nằm ở đuôi phải `+2R..+5R`. Bất kỳ bộ lọc `Toxic Filter` nào vô tình bỏ sót chỉ `2–3%` ngày breakout lớn sẽ làm suy giảm mạnh tỷ suất sinh lời ngoài mẫu.
3. **Quyết định thực thi:** Giữ nguyên tín hiệu white-box thuần (`RAW_WHITEBOX_1X`) cho cả `PORT_7E` (FTMO Free Trial/Funded) và `Crypto F4_4H_EMA` nếu Meta-Labeler không vượt chuẩn ở cả 3 tiêu chí; chỉ coi `meta_labeler.py` là công cụ nghiên cứu chuẩn AFML sẵn sàng tái kiểm định khi có thêm dữ liệu forward thực tế.

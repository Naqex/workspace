---
doc_type: research_receipt
date: 2026-11-24
lane: risk-auditor
milestone: Wave2-Cycle3B-MultiProp-And-BlackSwan
holdout_rows_analysed: 0
order_send_count: 0
---

# Tối Ưu Scaling Đa Tài Khoản Prop & Stress-Test Black-Swan Đa Sleeve (Wave 2 Cycle 3B)

- **Generated UTC:** `2026-11-23T18:16:37.407743+00:00` (Prop Sim `21.574s` | Crisis Replay `5.131s`)
- **Safety Seal:** Holdout `2025+` SEALED (`lock=f0a6b43cb205535b...`, `holdout_rows_analysed = 0`, `OrderSend = 0`).
- **Tỷ giá quy đổi `PROFILE.md`:** `1 USD = 25,500 VND`. Pod Own-Book sử dụng `6` sleeves thực tế (`S1_PROP_FX_IDX, S2_CRYPTO_SPOT, S3A_FUND_CARRY, S3B_MACRO_ETF, S4_ETF40_MULTIFACTOR, S5_CME_FUTURES_PROP`).

## 1. Tối Ưu Scaling Đa Tài Khoản Prop (5,000 Paths, 60 Tháng, Block = 5d)

Mô phỏng đồng thời nhiều tài khoản trên **cùng một băng thị trường bootstrap (`idx_matrix[b, d]`)** để bắt trọn **tương quan drawdown 100%** khi các tài khoản cùng chạy `PORT_7E`/`PORT_9E`, kèm luật **3-Bucket Treasury** (`30%` Reserve tới trần `5x` vé -> `100%` overflow đổ vào Own-Book; `50%` Own-Book tự gộp lãi hàng ngày theo Pod `ERC_LW_Capped35`; `20%` Ops/Thuế).

### 1A. Ngân Sách Phí Khởi Điểm `500 USD` (`12.8 triệu VND`)

| Architecture | Profile | Wipeout % | Sustain % | Dbl-Fail % | P95 CorrDD% | Fees 24m | Wealth 24m (Med) | EV/Fee | OB 60m (USD / tr VND) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| SINGLE_FTMO_SWING | Balanced | 5.4% | 94.5% | 0.0% | 10.00% | 206 USD | +766 USD | +3.69x | 1,698 USD (43 tr) |
| SINGLE_FTMO_SWING | Sprint | 7.4% | 92.6% | 0.0% | 10.00% | 212 USD | +798 USD | +3.67x | 1,719 USD (44 tr) |
| SINGLE_THE5ERS_HS | Balanced | 0.0% | 99.7% | 0.0% | 10.00% | 48 USD | +346 USD | +7.36x | 1,045 USD (27 tr) |
| SINGLE_THE5ERS_HS | Sprint | 0.0% | 99.9% | 0.0% | 10.00% | 51 USD | +361 USD | +7.34x | 1,068 USD (27 tr) |
| DUAL_2FIRM_SYNC | Balanced | 1.1% | 98.8% | 19.8% | 10.00% | 209 USD | +1046 USD | +5.15x | 2,566 USD (65 tr) |
| DUAL_2FIRM_SYNC | Sprint | 1.8% | 98.2% | 24.1% | 10.00% | 219 USD | +1096 USD | +5.11x | 2,609 USD (66 tr) |
| DUAL_2FIRM_STAGGER_42D | Balanced | 0.4% | 99.5% | 3.0% | 10.00% | 209 USD | +969 USD | +4.74x | 2,477 USD (63 tr) |
| DUAL_2FIRM_STAGGER_42D | Sprint | 0.7% | 99.3% | 3.4% | 10.00% | 220 USD | +1017 USD | +4.73x | 2,526 USD (64 tr) |
| LADDER_STAGGER_SCALE | Balanced | 0.6% | 99.4% | 6.5% | 10.00% | 256 USD | +1436 USD | +6.43x | 6,088 USD (155 tr) |
| LADDER_STAGGER_SCALE | Sprint | 1.1% | 98.9% | 7.0% | 10.00% | 269 USD | +1543 USD | +6.50x | 6,242 USD (159 tr) |

### 1B. Ngân Sách Phí Khởi Điểm `1,500 USD` (`38.2 triệu VND`)

| Architecture | Profile | Wipeout % | Sustain % | Dbl-Fail % | P95 CorrDD% | Fees 24m | Wealth 24m (Med) | EV/Fee | OB 60m (USD / tr VND) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| SINGLE_FTMO_SWING | Balanced | 0.0% | 99.9% | 0.0% | 10.00% | 217 USD | +795 USD | +3.70x | 2,419 USD (62 tr) |
| SINGLE_FTMO_SWING | Sprint | 0.0% | 99.9% | 0.0% | 10.00% | 229 USD | +835 USD | +3.68x | 2,473 USD (63 tr) |
| SINGLE_THE5ERS_HS | Balanced | 0.0% | 99.7% | 0.0% | 10.00% | 48 USD | +346 USD | +7.36x | 1,045 USD (27 tr) |
| SINGLE_THE5ERS_HS | Sprint | 0.0% | 99.9% | 0.0% | 10.00% | 51 USD | +361 USD | +7.34x | 1,068 USD (27 tr) |
| DUAL_2FIRM_SYNC | Balanced | 0.0% | 99.9% | 19.8% | 10.00% | 211 USD | +1071 USD | +5.24x | 3,248 USD (83 tr) |
| DUAL_2FIRM_SYNC | Sprint | 0.0% | 100.0% | 24.1% | 10.00% | 224 USD | +1126 USD | +5.19x | 3,307 USD (84 tr) |
| DUAL_2FIRM_STAGGER_42D | Balanced | 0.0% | 99.9% | 3.1% | 10.00% | 211 USD | +992 USD | +4.82x | 3,160 USD (81 tr) |
| DUAL_2FIRM_STAGGER_42D | Sprint | 0.0% | 100.0% | 3.5% | 10.00% | 223 USD | +1041 USD | +4.80x | 3,245 USD (83 tr) |
| LADDER_STAGGER_SCALE | Balanced | 0.1% | 99.9% | 9.4% | 9.96% | 745 USD | +5150 USD | +8.00x | 25,430 USD (648 tr) |
| LADDER_STAGGER_SCALE | Sprint | 0.2% | 99.8% | 10.9% | 10.00% | 784 USD | +5557 USD | +8.11x | 25,930 USD (661 tr) |

### 1C. Ngân Sách Phí Khởi Điểm `3,000 USD` (`76.5 triệu VND`)

| Architecture | Profile | Wipeout % | Sustain % | Dbl-Fail % | P95 CorrDD% | Fees 24m | Wealth 24m (Med) | EV/Fee | OB 60m (USD / tr VND) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| SINGLE_FTMO_SWING | Balanced | 0.0% | 99.9% | 0.0% | 10.00% | 217 USD | +795 USD | +3.70x | 2,419 USD (62 tr) |
| SINGLE_FTMO_SWING | Sprint | 0.0% | 99.9% | 0.0% | 10.00% | 229 USD | +835 USD | +3.68x | 2,474 USD (63 tr) |
| SINGLE_THE5ERS_HS | Balanced | 0.0% | 99.7% | 0.0% | 10.00% | 48 USD | +346 USD | +7.36x | 1,045 USD (27 tr) |
| SINGLE_THE5ERS_HS | Sprint | 0.0% | 99.9% | 0.0% | 10.00% | 51 USD | +361 USD | +7.34x | 1,068 USD (27 tr) |
| DUAL_2FIRM_SYNC | Balanced | 0.0% | 99.9% | 19.8% | 10.00% | 211 USD | +1071 USD | +5.24x | 3,248 USD (83 tr) |
| DUAL_2FIRM_SYNC | Sprint | 0.0% | 100.0% | 24.1% | 10.00% | 224 USD | +1126 USD | +5.19x | 3,308 USD (84 tr) |
| DUAL_2FIRM_STAGGER_42D | Balanced | 0.0% | 99.9% | 3.1% | 10.00% | 211 USD | +992 USD | +4.82x | 3,160 USD (81 tr) |
| DUAL_2FIRM_STAGGER_42D | Sprint | 0.0% | 100.0% | 3.5% | 10.00% | 223 USD | +1041 USD | +4.80x | 3,246 USD (83 tr) |
| LADDER_STAGGER_SCALE | Balanced | 0.1% | 99.9% | 9.9% | 9.91% | 1078 USD | +10086 USD | +10.71x | 45,211 USD (1153 tr) |
| LADDER_STAGGER_SCALE | Sprint | 0.2% | 99.8% | 11.9% | 10.00% | 1141 USD | +10890 USD | +10.80x | 46,606 USD (1188 tr) |

### 1D. Lộ Trình Vượt Ngưỡng Own-Book `50,000 USD` (`1.275 tỷ VND`) & `100,000 USD` (`2.55 tỷ VND`)

| Kịch Bản Vốn + Prop Ladder | Profile | Wipeout % | Peak Funded (Med) | OB 24m (Med) | OB 60m (Med) | P(>=50k 60m) | Med Tháng -> 50k | P(>=100k 60m) | Med Tháng -> 100k |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Pure Prop Ladder (Budget 1.5k + OB 0k) | Balanced | 0.1% | 205,000 USD | 4,217 USD | 25,430 USD | 7.7% | 55.4m | 0.0% | > 60m |
| Pure Prop Ladder (Budget 1.5k + OB 0k) | Sprint | 0.2% | 207,500 USD | 4,537 USD | 25,930 USD | 8.5% | 55.2m | 0.0% | > 60m |
| Pure Prop Max Ladder (Budget 3k + OB 0k) | Balanced | 0.1% | 350,000 USD | 8,952 USD | 45,211 USD | 42.5% | 49.6m | 3.8% | 56.5m |
| Pure Prop Max Ladder (Budget 3k + OB 0k) | Sprint | 0.2% | 350,000 USD | 9,626 USD | 46,606 USD | 44.5% | 49.3m | 4.0% | 56.1m |
| Hybrid Seed 10k (Budget 1.5k + OB 10k) | Balanced | 0.1% | 205,000 USD | 15,869 USD | 40,003 USD | 26.9% | 52.7m | 0.1% | 57.7m |
| Hybrid Seed 10k (Budget 1.5k + OB 10k) | Sprint | 0.2% | 207,500 USD | 16,134 USD | 40,575 USD | 28.2% | 52.5m | 0.2% | 57.9m |
| Hybrid Seed 25k (Budget 3k + OB 25k) | Balanced | 0.1% | 350,000 USD | 37,988 USD | 81,734 USD | 93.2% | 35.2m | 26.4% | 53.0m |
| Hybrid Seed 25k (Budget 3k + OB 25k) | Sprint | 0.2% | 350,000 USD | 38,740 USD | 83,055 USD | 93.6% | 34.4m | 27.6% | 52.9m |
| Hybrid Seed 40k (Budget 3k + OB 40k) | Balanced | 0.1% | 350,000 USD | 55,493 USD | 103,656 USD | 100.0% | 18.1m | 55.5% | 49.4m |
| Hybrid Seed 40k (Budget 3k + OB 40k) | Sprint | 0.2% | 350,000 USD | 56,177 USD | 104,934 USD | 100.0% | 17.4m | 58.1% | 49.1m |

## 2. Stress-Test 6 Kịch Bản Black-Swan & Contagion Trên `6` Sleeves (`2020-01-01..2024-12-31 (1305 biz days)`)

Trọng số phân bổ huấn luyện nhân quả `2020–2022` (chưa bao gồm `2023–2024` OOS):

| Allocator | S1_PROP_FX_IDX | S2_CRYPTO_SPOT | S3A_FUND_CARRY | S3B_MACRO_ETF | S4_ETF40_MULTIFACTOR | S5_CME_FUTURES_PROP |
|---|---:|---:|---:|---:|---:|---:|
| Equal_Weight | 16.7% | 16.7% | 16.7% | 16.7% | 16.7% | 16.7% |
| ERC_Capped35 | 16.3% | 9.3% | 35.0% | 11.7% | 8.1% | 19.6% |
| ERC_LW_Capped35 | 16.1% | 9.5% | 35.0% | 11.7% | 8.2% | 19.4% |
| NCO_Capped35 | 17.3% | 6.5% | 35.0% | 10.1% | 3.0% | 28.1% |
| HRP | 5.2% | 1.7% | 81.3% | 2.2% | 1.1% | 8.5% |

### 2A. Tổng Hợp 5 Kịch Bản Khủng Hoảng (S1..S5)

| Allocator | S1 Hist 20d/60d DD% | S2 2022+FTX DD% | S3 CEX Wt% | S3 -30%/-50% Hit% | S4 Corr0.85 P95/P99 DD% | S4 Worst 1d P99% | S5 3x Slip CAGR% (Ret%) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Equal_Weight | 2.24% / 2.30% | 6.60% | 33.3% | 10.0% / 16.7% | 9.92% / 18.83% | 6.09% | +4.63% (65%) |
| ERC_Capped35 | 1.63% / 1.72% | 6.69% | 44.3% | 13.3% / 22.2% | 6.76% / 13.00% | 3.84% | +4.43% (66%) |
| ERC_LW_Capped35 | 1.63% / 1.71% | 6.74% | 44.5% | 13.4% / 22.3% | 6.86% / 13.18% | 3.90% | +4.47% (66%) |
| NCO_Capped35 | 1.56% / 1.78% | 5.94% | 41.5% | 12.4% / 20.8% | 5.71% / 10.64% | 2.98% | +3.85% (61%) |
| HRP | 0.75% / 0.75% | 10.35% | 83.0% | 24.9% / 41.5% | 3.02% / 7.40% | 1.83% | +6.13% (89%) |

### 2B. Kịch Bản 6 — Ma Trận Thiệt Hại Tuyệt Đối Bằng `%`, `USD` & `VND` (`25,500 VND/USD`, Chuẩn `PROFILE.md`)

| Allocator | Worst-Case DD% | Dominant Shock | 10k USD Tier (USD / tr VND / Status) | 50k USD Tier (USD / tr VND / Status) | 200k USD Tier (USD / tr VND / Status) |
|---|---:|---|---|---|---|
| Equal_Weight | 18.83% | Corr0.85_Crunch_P99 | -1,883 USD / -48.0 tr (CAUTION_AMBER) | -9,415 USD / -240.1 tr (BREACH_RED) | -37,660 USD / -960 tr (BREACH_RED) |
| ERC_Capped35 | 22.46% | CEX_-50%_Haircut | -2,246 USD / -57.3 tr (BREACH_RED) | -11,230 USD / -286.4 tr (BREACH_RED) | -44,920 USD / -1146 tr (BREACH_RED) |
| ERC_LW_Capped35 | 22.57% | CEX_-50%_Haircut | -2,257 USD / -57.6 tr (BREACH_RED) | -11,285 USD / -287.8 tr (BREACH_RED) | -45,140 USD / -1151 tr (BREACH_RED) |
| NCO_Capped35 | 21.05% | CEX_-50%_Haircut | -2,105 USD / -53.7 tr (BREACH_RED) | -10,525 USD / -268.4 tr (BREACH_RED) | -42,100 USD / -1074 tr (BREACH_RED) |
| HRP | 41.58% | CEX_-50%_Haircut | -4,158 USD / -106.0 tr (BREACH_RED) | -20,790 USD / -530.1 tr (BREACH_RED) | -83,160 USD / -2121 tr (BREACH_RED) |

## 3. Khuyến Nghị Điều Hành Trực Diện Cho Owner

1. **Chống phá sản quỹ phí (`500 USD` ngân sách nhỏ):** Mở đồng bộ 2 quỹ ngay ngày `t=0` với `P1_Sprint` đẩy rủi ro cháy quỹ phí lên `1.8%` và rủi ro double-fail đồng thời lên `24.1%`; chuyển sang **2-Firm Staggered (`+42` ngày) + `P1_Balanced`** hạ mạnh rủi ro cháy quỹ xuống `0.4%` (so với `1.1%` chạy đồng bộ) và giảm double-fail từ `19.8% -> 3.0%`.
2. **Sự thật toán học về mốc `50k / 100k USD` Own-Book:** Chỉ chạy 1 tài khoản `10k USD` đơn lẻ không thể vượt `50k USD` Own-Book trong 5 năm; chỉ khi kết hợp **thang nhân danh nghĩa đa quỹ (`LADDER_STAGGER_SCALE` lên `100k–200k` nominal) + luật 3-Bucket đổ tràn 100% vào Own-Book Pod + vốn mồi tự có (`10k–25k USD`)**, đường cong vượt `50k USD` (`1.275 tỷ VND`) mới khả thi trong khung `2–5` năm.
3. **Bài học sống còn về rủi ro sập sàn CEX (`S3`):** `HRP` không trần bị sập **`-41.58%`** (mất `-2121 triệu VND` trên mốc `200k USD`!) vì dồn `83.0%` vào CEX. Ngược lại, **`NCO_Capped35`** hạ tổng phơi nhiễm CEX xuống `41.5%` (`35% S3A + 6.5% S2`), cắt gần một nửa cú sốc xuống **`-21.05%`** (`-268.4 triệu VND` ở mốc `50k USD`). Phát hiện quan trọng: trần `35%` theo *từng sleeve* vẫn cho phép 2 sleeve CEX (`S3A + S2`) cộng dồn lên `41.5%–44.5%`; do đó, ở mốc vốn `50k–200k USD` cần áp thêm **trần nhóm sàn CEX tổng hợp `<= 25%` (`S2 + S3A`)** (kết hợp tách vốn lưu ký T-Bill/IBKR) để giữ thiệt hại Black-Swan tuyệt đối đúng vùng `COMFORT_GREEN` của `PROFILE.md`.

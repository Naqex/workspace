---
doc_type: quant-research-trajectory
generated_utc: 2026-11-24T19:48:16.023573+00:00
dev_window: 2020-01-03..2024-12-31
mc_paths: 5000
mc_horizon_months: 60
mc_seed: 20261124
holdout_rows_analysed: 0
order_send_count: 0
receipt_sha256: da665a9c9f6dc0b6e93268f97fd80981941694368449f0d05027523d88d089ae
---

# Mô Phỏng Hợp Nhất 60 Tháng: Lộ Trình Top-1% Quỹ Cấp Vốn -> Vốn Riêng & Tự Nuôi Hạ Tầng (Dev 2020-01-03..2024-12-31)

> **Niêm phong dữ liệu & Trung thực toán học:** Chạy 100% trên giao điểm ngày thật của dữ liệu Phát triển niêm phong `2020-01-03..2024-12-31` (`holdout_rows_analysed = 0`, khóa Holdout `2025+` nguyên vẹn SHA `f0a6b43cb205535b...`), `OrderSend = 0`, **5.000 kịch bản Monte Carlo ghép đồng bộ 60 tháng** (`1.260` phiên, `Circular Block-Bootstrap`, độ dài khối `5` ngày, `seed = 20261124`). Tỷ giá quy đổi `1 USD = 25.500 VND`. Sổ Vốn Riêng chạy đúng cấu hình **`NCO_CexCap25`** tái cân bằng `Monthly_1st` (tổng sàn CEX khóa cứng **`25.0%` <= 25%**; tỷ trọng: `S2_CRYPTO_SPOT=1.3%, S3A_FUND_CARRY=23.7%, S3B_MACRO_ETF=37.5%, S4_ETF40_MULTIFACTOR=37.5%`) và trừ thẳng phí kéo IBKR thực tế theo cỡ tài khoản (`-1,20%` dưới `5k`, `-0,65%` dưới `25k`, `-0,30%` dưới `50k`, `-0,10%` từ `50k+`).

## 1. Kết Luận Trọng Tâm Dễ Hiểu (Không Tô Hồng)

1. **Thang Leo Thông Minh (`Smart-Tier`: `5K -> 25K -> 20K -> 50K -> 50K 4%/8% -> 100K x2`, trần `350k USD`, Gate-42 có đệm `2x` phí) áp đảo hoàn toàn cách mua lặp lại vé `10K` cũ:**
   - Cùng một mức ngân sách vé khởi điểm **`1.500 USD` (`38,2 tr VND`, Vốn Riêng mồi `0 USD`)** ở chi phí chuẩn `1,0x`: sau `60` tháng, trung vị Sổ Vốn Riêng của thang mới đạt **`49,113 USD`** so với **`9,597 USD`** của thang `10K` cũ (**gấp `5.12x`**!), đồng thời tỷ lệ cháy sạch quỹ phí giữ ở mức **`0.78%`** (so với `0.02%` của thang cũ).
   - Ngay cả khi trượt giá thực tế tăng nặng **`1,5x`**, trung vị Vốn Riêng sau 60 tháng vẫn tăng mạnh từ `1,761 USD` (cũ) lên **`13,346 USD`** (mới).
2. **Hạ tầng chuyên nghiệp tự nuôi 100% từ tiền lãi (không bao giờ bỏ tiền túi):**
   - Ở cấu hình thực chiến `Budget 1.500 USD + OB 0 USD` (`1,0x`), **Mốc A — Tự nuôi VPS sát sàn LD4/NY4 (`35 USD/tháng`)** mở khóa ở trung vị **tháng thứ `16`**, và **Mốc B — Tự nuôi Dữ liệu sạch Top-1% (`100 USD/tháng`, tổng vốn hoạt động >= `50k USD`)** mở khóa ở trung vị **tháng thứ `26`**.
3. **Sự thật toán học về các mốc Vốn Riêng `50k / 100k / 200k USD` và Điểm Giao Cắt (`Crossover`):**
   - Đi tay trắng (`OB Seed = 0 USD`), xác suất tự tích lũy Vốn Riêng vượt **`50.000 USD` (`1,275 tỷ VND`)** trong `60` tháng đạt **`49.4%`** (`Budget 1.500 USD`) và **`66.3%`** (`Budget 3.000 USD`).
   - Khi kết hợp **vốn mồi Vốn Riêng `25.000 USD` + `Budget 3.000 USD`**, xác suất vượt **`100.000 USD` (`2,55 tỷ VND`)** đạt **`45.0%`** trong `60` tháng, và xác suất chạm **Điểm Giao Cắt Thật (`Crossover` — sau khi Prop đã Funded >= `25k USD`, lãi ròng tháng Vốn Riêng `1,0x` >= lãi ròng tháng Prop)** trong `60` tháng là **`4.4%`**.
   - *Ngưỡng Giao Cắt Giải Tích (minh bạch):* Vì Sổ Vốn Riêng thuần 4 nhánh `NCO_CexCap25` (`1,0x`, `MaxDD 9.28%`) sinh lãi kỳ vọng `0.46%/tháng` còn Prop Funded `1,0x` (`7E`) sau chia `80%` sinh `0.56%/tháng` trên vốn danh nghĩa, để Vốn Riêng `1,0x` vượt `100k` Prop cần khoảng **`121,470 USD`** (và vượt `350k` Prop cần **`437,292 USD`**); nếu nâng Own-Book lên `2,0x` vol, ngưỡng vượt `100k` Prop hạ xuống **`60,735 USD`**!
4. **Giá trị kinh tế cực lớn của việc kiểm soát trượt giá (`1,0x` vs `1,5x`) bằng VPS sát sàn tự nuôi:** So sánh bảng `1,0x` (`49,113 USD`) với `1,5x` (`13,346 USD`) cho thấy để trượt giá phình lên `1,5x` làm bay hơn `35,767 USD` tích lũy 5 năm — chứng minh việc trích `35 USD/tháng` từ lãi để chuyển MT5 sang VPS LD4/NY4 ngay khi chạm Mốc A là khoản đầu tư có ROI cao nhất toàn hệ thống.

## 2. Phần 1 — So Sánh Thang `10K` Cũ vs Thang `Smart-Tier` Mới (`5.000` Kịch Bản × `60` Tháng)

Toàn bộ tài khoản Prop mở song song trên **cùng ngày thị trường M1** để đo trọn rủi ro trùng lỗ; cơ chế 3 Ngăn tự động đổ tràn `100%` phần dự phòng vượt trần `5x` vé mục tiêu vào Sổ Vốn Riêng `NCO_CexCap25`.

### 2.1. Chi Phí Chuẩn (`1,0x` M1 Bid/Ask + Khóa Tin Đỏ `±5p`)

| Kịch Bản (Ngân sách vé B, Vốn mồi OB) | Cháy Quỹ Vé | Rớt Đôi | Vốn Prop Đỉnh (TV) | EV/Phí 24T | Vốn Riêng 24T (TV) | Vốn Riêng 60T (TV / VND) | Hạ tầng tự trả 60T |
|---|---|---|---|---|---|---|---|
| Old Repeated-10K (SYMCAP 3.0%) (B=500, OB=0) | 0.12% | 36.5% | 50,000 USD | 1.20x | 405 USD | **3,328 USD** (85 tr) | 770 USD |
| Old Repeated-10K (SYMCAP 3.0%) (B=1,500, OB=0) | 0.02% | 44.0% | 85,000 USD | 0.92x | 861 USD | **9,597 USD** (245 tr) | 1,820 USD |
| Old Repeated-10K (SYMCAP 3.0%) (B=3,000, OB=0) | 0.04% | 43.5% | 90,000 USD | 0.82x | 1,424 USD | **12,066 USD** (308 tr) | 2,160 USD |
| Smart-Tier (Matched Cap 100k) (B=1,500, OB=0) | 0.58% | 27.8% | 100,000 USD | 4.75x | 2,937 USD | **19,397 USD** (495 tr) | 4,162 USD |
| Smart-Tier Ladder (OB Seed 0) (B=500, OB=0) | 0.74% | 10.5% | 350,000 USD | 1.70x | 719 USD | **13,489 USD** (344 tr) | 2,220 USD |
| Smart-Tier Ladder (OB Seed 0) (B=1,500, OB=0) | 0.78% | 32.2% | 350,000 USD | 3.23x | 2,957 USD | **49,113 USD** (1252 tr) | 4,765 USD |
| Smart-Tier Ladder (OB Seed 0) (B=3,000, OB=0) | 0.44% | 38.8% | 350,000 USD | 4.11x | 6,405 USD | **63,634 USD** (1623 tr) | 5,415 USD |
| Smart-Tier + Hybrid OB 10k (B=1,500, OB=10,000) | 0.78% | 32.2% | 350,000 USD | 3.23x | 13,906 USD | **61,582 USD** (1570 tr) | 4,765 USD |
| Smart-Tier + Hybrid OB 10k (B=3,000, OB=10,000) | 0.44% | 38.8% | 350,000 USD | 4.11x | 17,264 USD | **76,030 USD** (1939 tr) | 5,415 USD |
| Smart-Tier + Hybrid OB 25k (B=1,500, OB=25,000) | 0.78% | 32.2% | 350,000 USD | 3.23x | 30,678 USD | **80,781 USD** (2060 tr) | 4,765 USD |
| Smart-Tier + Hybrid OB 25k (B=3,000, OB=25,000) | 0.44% | 38.8% | 350,000 USD | 4.11x | 33,910 USD | **95,332 USD** (2431 tr) | 5,415 USD |

### 2.2. Kịch Bản Stress Trượt Giá Trung Bình (`1,25x` Chi Phí M1)

| Kịch Bản (Ngân sách vé B, Vốn mồi OB) | Cháy Quỹ Vé | Rớt Đôi | Vốn Prop Đỉnh (TV) | EV/Phí 24T | Vốn Riêng 24T (TV) | Vốn Riêng 60T (TV / VND) | Hạ tầng tự trả 60T |
|---|---|---|---|---|---|---|---|
| Old Repeated-10K (SYMCAP 3.0%) (B=500, OB=0) | 0.22% | 33.8% | 30,000 USD | 0.83x | 229 USD | **1,738 USD** (44 tr) | 245 USD |
| Old Repeated-10K (SYMCAP 3.0%) (B=1,500, OB=0) | 0.08% | 44.8% | 70,000 USD | 0.51x | 416 USD | **4,847 USD** (124 tr) | 945 USD |
| Old Repeated-10K (SYMCAP 3.0%) (B=3,000, OB=0) | 0.04% | 44.9% | 80,000 USD | 0.42x | 664 USD | **7,411 USD** (189 tr) | 1,208 USD |
| Smart-Tier (Matched Cap 100k) (B=1,500, OB=0) | 1.36% | 35.2% | 100,000 USD | 3.28x | 1,993 USD | **14,691 USD** (375 tr) | 3,345 USD |
| Smart-Tier Ladder (OB Seed 0) (B=500, OB=0) | 1.66% | 11.4% | 150,000 USD | 1.27x | 487 USD | **5,321 USD** (136 tr) | 1,190 USD |
| Smart-Tier Ladder (OB Seed 0) (B=1,500, OB=0) | 1.74% | 40.1% | 350,000 USD | 2.24x | 1,966 USD | **31,636 USD** (807 tr) | 3,990 USD |
| Smart-Tier Ladder (OB Seed 0) (B=3,000, OB=0) | 0.96% | 48.6% | 350,000 USD | 2.78x | 3,531 USD | **47,690 USD** (1216 tr) | 4,935 USD |
| Smart-Tier + Hybrid OB 10k (B=1,500, OB=10,000) | 1.74% | 40.1% | 350,000 USD | 2.24x | 12,942 USD | **44,142 USD** (1126 tr) | 3,990 USD |
| Smart-Tier + Hybrid OB 10k (B=3,000, OB=10,000) | 0.96% | 48.6% | 350,000 USD | 2.78x | 14,473 USD | **60,226 USD** (1536 tr) | 4,935 USD |
| Smart-Tier + Hybrid OB 25k (B=1,500, OB=25,000) | 1.74% | 40.1% | 350,000 USD | 2.24x | 29,730 USD | **63,306 USD** (1614 tr) | 3,990 USD |
| Smart-Tier + Hybrid OB 25k (B=3,000, OB=25,000) | 0.96% | 48.6% | 350,000 USD | 2.78x | 31,305 USD | **79,149 USD** (2018 tr) | 4,935 USD |

### 2.3. Kịch Bản Stress Trượt Giá Nặng (`1,5x` Chi Phí M1)

| Kịch Bản (Ngân sách vé B, Vốn mồi OB) | Cháy Quỹ Vé | Rớt Đôi | Vốn Prop Đỉnh (TV) | EV/Phí 24T | Vốn Riêng 24T (TV) | Vốn Riêng 60T (TV / VND) | Hạ tầng tự trả 60T |
|---|---|---|---|---|---|---|---|
| Old Repeated-10K (SYMCAP 3.0%) (B=500, OB=0) | 0.72% | 31.4% | 20,000 USD | 0.42x | 94 USD | **826 USD** (21 tr) | 0 USD |
| Old Repeated-10K (SYMCAP 3.0%) (B=1,500, OB=0) | 0.32% | 47.3% | 40,000 USD | 0.12x | 169 USD | **1,761 USD** (45 tr) | 280 USD |
| Old Repeated-10K (SYMCAP 3.0%) (B=3,000, OB=0) | 0.12% | 47.5% | 60,000 USD | 0.03x | 283 USD | **3,469 USD** (88 tr) | 490 USD |
| Smart-Tier (Matched Cap 100k) (B=1,500, OB=0) | 3.06% | 44.1% | 100,000 USD | 2.01x | 1,183 USD | **9,316 USD** (238 tr) | 2,310 USD |
| Smart-Tier Ladder (OB Seed 0) (B=500, OB=0) | 3.58% | 11.3% | 50,000 USD | 0.81x | 235 USD | **2,560 USD** (65 tr) | 630 USD |
| Smart-Tier Ladder (OB Seed 0) (B=1,500, OB=0) | 3.74% | 48.7% | 300,000 USD | 1.37x | 1,166 USD | **13,346 USD** (340 tr) | 2,680 USD |
| Smart-Tier Ladder (OB Seed 0) (B=3,000, OB=0) | 2.22% | 59.7% | 350,000 USD | 1.67x | 1,835 USD | **29,962 USD** (764 tr) | 4,095 USD |
| Smart-Tier + Hybrid OB 10k (B=1,500, OB=10,000) | 3.74% | 48.7% | 300,000 USD | 1.37x | 12,166 USD | **25,541 USD** (651 tr) | 2,680 USD |
| Smart-Tier + Hybrid OB 10k (B=3,000, OB=10,000) | 2.22% | 59.7% | 350,000 USD | 1.67x | 12,809 USD | **42,234 USD** (1077 tr) | 4,095 USD |
| Smart-Tier + Hybrid OB 25k (B=1,500, OB=25,000) | 3.74% | 48.7% | 300,000 USD | 1.37x | 28,962 USD | **44,613 USD** (1138 tr) | 2,680 USD |
| Smart-Tier + Hybrid OB 25k (B=3,000, OB=25,000) | 2.22% | 59.7% | 350,000 USD | 1.67x | 29,774 USD | **61,279 USD** (1563 tr) | 4,095 USD |

## 3. Phần 2 — Xác Suất & Trung Vị Tháng Đạt Các Mốc Hạ Tầng, Vốn Riêng & Giao Cắt (Thang `Smart-Tier`)

Cột **Mốc A (VPS `35 USD/tháng`)** và **Mốc B (Dữ liệu `100 USD/tháng`)** ghi theo định dạng **`P(24T) / P(36T) / P(60T) (TV = tháng trung vị)`**. Các cột **Mốc C & D** ghi **`P(60T) (tháng trung vị)`**.

### 3.1. Chi Phí Chuẩn (`1,0x`)

| Cấu Hình Vốn | Mốc A: Tự nuôi VPS | Mốc B: Tự nuôi Data (>=50k) | C1: OB 25k | C2: OB 50k | C3: OB 100k | C4: OB 200k | Mốc D: Crossover |
|---|---|---|---|---|---|---|---|
| B=500 + OB=0 | 38% / 70% / 93% (TV 27T) | 4% / 25% / 69% (TV 41T) | 36.6% (50T) | 14.8% (54T) | 0.5% (58T) | 0.0% (>60T) | 0.1% (60T) |
| B=1,500 + OB=0 | 78% / 92% / 98% (TV 16T) | 42% / 72% / 92% (TV 26T) | 75.4% (40T) | 49.4% (48T) | 7.0% (55T) | 0.0% (>60T) | 0.6% (55T) |
| B=3,000 + OB=0 | 81% / 94% / 99% (TV 16T) | 61% / 85% / 96% (TV 21T) | 87.3% (35T) | 66.3% (46T) | 13.3% (55T) | 0.0% (>60T) | 0.8% (53T) |
| B=1,500 + OB=10,000 | 78% / 92% / 98% (TV 16T) | 42% / 72% / 92% (TV 26T) | 84.5% (35T) | 63.0% (45T) | 13.7% (55T) | 0.0% (>60T) | 1.0% (55T) |
| B=3,000 + OB=10,000 | 81% / 94% / 99% (TV 16T) | 61% / 85% / 96% (TV 21T) | 92.7% (29T) | 78.6% (41T) | 23.8% (54T) | 0.0% (>60T) | 1.5% (52T) |
| B=1,500 + OB=25,000 | 78% / 92% / 98% (TV 16T) | 42% / 72% / 92% (TV 26T) | 100.0% (1T) | 80.4% (39T) | 29.6% (53T) | 0.0% (>60T) | 4.3% (48T) |
| B=3,000 + OB=25,000 | 81% / 94% / 99% (TV 16T) | 61% / 85% / 96% (TV 21T) | 100.0% (1T) | 90.7% (33T) | 45.0% (51T) | 0.1% (58T) | 4.4% (50T) |

### 3.2. Kịch Bản Stress Trượt Giá `1,5x`

| Cấu Hình Vốn | Mốc A: Tự nuôi VPS | Mốc B: Tự nuôi Data (>=50k) | C1: OB 25k | C2: OB 50k | C3: OB 100k | C4: OB 200k | Mốc D: Crossover |
|---|---|---|---|---|---|---|---|
| B=500 + OB=0 | 18% / 40% / 70% (TV 34T) | 1% / 7% / 30% (TV 46T) | 7.6% (52T) | 1.6% (56T) | 0.0% (>60T) | 0.0% (>60T) | 0.1% (59T) |
| B=1,500 + OB=0 | 56% / 76% / 89% (TV 20T) | 19% / 40% / 66% (TV 32T) | 36.5% (46T) | 13.9% (52T) | 0.5% (56T) | 0.0% (>60T) | 0.9% (55T) |
| B=3,000 + OB=0 | 61% / 82% / 92% (TV 20T) | 36% / 62% / 80% (TV 26T) | 56.3% (41T) | 27.0% (50T) | 1.5% (56T) | 0.0% (>60T) | 2.0% (53T) |
| B=1,500 + OB=10,000 | 56% / 76% / 89% (TV 20T) | 19% / 40% / 66% (TV 32T) | 51.2% (42T) | 23.6% (50T) | 1.5% (56T) | 0.0% (>60T) | 1.8% (53T) |
| B=3,000 + OB=10,000 | 61% / 82% / 92% (TV 20T) | 36% / 62% / 80% (TV 26T) | 70.4% (35T) | 41.2% (47T) | 3.8% (55T) | 0.0% (>60T) | 3.7% (52T) |
| B=1,500 + OB=25,000 | 56% / 76% / 89% (TV 20T) | 19% / 40% / 66% (TV 32T) | 100.0% (1T) | 43.8% (45T) | 5.1% (54T) | 0.0% (>60T) | 79.0% (12T) |
| B=3,000 + OB=25,000 | 61% / 82% / 92% (TV 20T) | 36% / 62% / 80% (TV 26T) | 100.0% (1T) | 64.1% (40T) | 11.7% (53T) | 0.0% (>60T) | 77.4% (12T) |

## 4. Phần 3 — Bảng Chấm Điểm Top-1% Độc Lập & Ma Trận Nỗi Đau VND Tuyệt Đối (`25.500 VND/USD`)

### 4.1. So Sánh Tổng Hợp Trước & Sau Nâng Cấp (Baseline Cũ vs Smart-Tier + `NCO_CexCap25`)

| Kiến Trúc Danh Mục | Prop Funded 1x/năm | OB CAGR 1x | OB Sharpe | OB Calmar | Sốc CEX -50% | Cháy Quỹ Vé | EV/Phí 24T | OB 60T (TV) | Sharpe Hợp Nhất |
|---|---|---|---|---|---|---|---|---|---|
| Baseline Cũ (Repeated 10K · SYMCAP 3.0% · Budget 1.5k, OB 0k) | +7.31% | +5.62% | 1.18 | 0.61 | -41.58% | 0.02% | 0.92x | 9,597 USD | 0.83 |
| Nâng Cấp Smart-Tier (SYMCAP 1.75% + DynPL + 4/8 Safe · Budget 1.5k, OB 0k) | +7.31% | +5.62% | 1.18 | 0.61 | -12.89% | 0.78% | 3.23x | 49,113 USD | 1.11 |
| Top-1% Hybrid Full Pod (Smart-Tier + NCO_CexCap25 · Budget 3k, OB 25k) | +7.31% | +5.62% | 1.18 | 0.61 | -12.89% | 0.44% | 4.11x | 95,332 USD | 1.74 |

- *Ghi chú minh bạch về lợi suất Sổ Vốn Riêng (`NCO_CexCap25`, `1,0x` không đòn bẩy, **chỉ gồm 4 nhánh Vốn Riêng thuần đầu tư `S2+S3A+S3B+S4` — đã loại bỏ `S1/S5` Prop để không tính trùng**):* Trên tập `2020–2024` khớp ngày trực tiếp (không quay vòng ngày tương lai, tính đủ phí tái cân bằng 2 chiều `sum(|Δw|*c)`), Vốn Riêng thuần 4 nhánh đạt `CAGR +5.62%`, `MaxDD 9.28%`, `Sharpe 1.18`, `Calmar 0.61` (OOS `2023–2024`: `Sharpe 1.47`, `MaxDD 3.27%`; tham chiếu Pod gộp đủ 6 nhánh gồm Prop đạt `Sharpe 2.27`). Toàn bộ bảng trên giữ nguyên `1,0x` không đòn bẩy để phản ánh đường đáy an toàn nhất.

### 4.2. Ma Trận Nỗi Đau Tuyệt Đối Theo Mốc Vốn Riêng (`NCO_CexCap25`, `25.500 VND/USD`)

| Cỡ Sổ Vốn Riêng (USD / tr VND) | Phí kéo IBKR | Lãi Ròng Năm (Sau IBKR) | Sụt Giảm Lịch Sử | Khủng Hoảng Tương Quan (0.85) | Sốc Sập Sàn CEX -50% (Có Trần 25%) | So Với HRP Cũ Không Trần |
|---|---|---|---|---|---|---|
| 10,000 USD (255 tr) | -0.65%/năm | +4.97% (+497 USD / +12.7 tr) | -9.28% (-23.7 tr) | -8.81% (-22.5 tr) | -12.89% (-32.9 tr) | -106 tr (BỎ) |
| 50,000 USD (1,275 tr) | -0.10%/năm | +5.52% (+2,760 USD / +70.4 tr) | -9.28% (-118.3 tr) | -8.81% (-112.3 tr) | -12.89% (-164.3 tr) | -530 tr (BỎ) |
| 100,000 USD (2,550 tr) | -0.10%/năm | +5.52% (+5,520 USD / +140.8 tr) | -9.28% (-236.6 tr) | -8.81% (-224.7 tr) | -12.89% (-328.7 tr) | -1060 tr (BỎ) |
| 200,000 USD (5,100 tr) | -0.10%/năm | +5.52% (+11,040 USD / +281.5 tr) | -9.28% (-473.3 tr) | -8.81% (-449.3 tr) | -12.89% (-657.4 tr) | -2121 tr (BỎ) |

## 5. Khuyến Nghị Hành Động Gọn Cho Chủ Quỹ

1. **Chốt lộ trình vé Smart-Tier (`5K -> 25K -> 20K -> 50K -> 50K 4%/8% -> 100K`, chỉ mở vé 2 khi đã có payout hoặc đệm >= `2x` phí):** Không đốt tiền mua lặp lại nhiều vé `10K` phí đắt — dùng `The5ers 5K` (`39 USD`) làm bàn đạp rồi nhảy bậc `FTMO Swing 25K/50K/100K` từ tiền lãi.
2. **Khóa cứng nguyên tắc hạ tầng tự nuôi:** Giữ `naqex-node1` (`0 USD/tháng`) tới khi vượt Mốc A (`Ops >= 300 USD/tháng` bền vững hoặc dự phòng Ops `>= 1.200 USD`) mới trích `35 USD/tháng` thuê VPS LD4/NY4; chỉ mua gói dữ liệu sạch `100 USD/tháng` khi tổng vốn quản lý vượt `50.000 USD` và quỹ Ops đủ dày.
3. **Giữ cứng trần sàn CEX `<= 25%` (`NCO_CexCap25`):** Nhìn vào bảng nỗi đau VND — ở mốc `100.000 USD` (`2,55 tỷ VND`), ngay cả kịch bản cực đoan sàn Crypto sập mất trắng `50%`, tổng thiệt hại bị khóa tối đa ở `-328,7 triệu VND` (`-12,89%`) thay vì mất trắng `-1.060 triệu VND` (`-41,58%`) như danh mục không trần.

*Thời gian tính toán toàn bộ kiểm toán M1 + 5.000 Monte Carlo × 60 tháng: `46.49s` · JSON kiểm chứng: `TOP1-UNIFIED-PROP-TO-OWNBOOK-TRAJECTORY-20261124.json` · SHA-256: `da665a9c9f6dc0b6e93268f97fd80981941694368449f0d05027523d88d089ae`.*

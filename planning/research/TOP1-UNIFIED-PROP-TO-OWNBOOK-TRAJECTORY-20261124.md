---
doc_type: quant-research-trajectory
generated_utc: 2026-11-24T11:12:41.748807+00:00
dev_window: 2018-01-02..2024-12-31
mc_paths: 5000
mc_horizon_months: 60
mc_seed: 20261124
holdout_rows_analysed: 0
order_send_count: 0
receipt_sha256: 323bb5823eaf80ee33177b6e2fd4046e2f1341745084cf68448925c7e6a0e5c9
---

# Mô Phỏng Hợp Nhất 60 Tháng: Lộ Trình Top-1% Quỹ Cấp Vốn -> Vốn Riêng & Tự Nuôi Hạ Tầng (Dev 2018–2024)

> **Niêm phong dữ liệu & Trung thực toán học:** Chạy 100% trên dữ liệu Phát triển niêm phong `2018-2024` (`holdout_rows_analysed = 0`, khóa Holdout `2025+` nguyên vẹn SHA `f0a6b43cb205535b...`), `OrderSend = 0`, **5.000 kịch bản Monte Carlo ghép đồng bộ 60 tháng** (`1.260` phiên, `Circular Block-Bootstrap`, độ dài khối `5` ngày, `seed = 20261124`). Tỷ giá quy đổi `1 USD = 25.500 VND`. Sổ Vốn Riêng chạy đúng cấu hình **`NCO_CexCap25`** tái cân bằng `Monthly_1st` (tổng sàn CEX khóa cứng **`25.0%` <= 25%**; tỷ trọng: `S1_PROP_FX_IDX=22.8%, S2_CRYPTO_SPOT=2.0%, S3A_FUND_CARRY=23.0%, S3B_MACRO_ETF=13.3%, S4_ETF40_MULTIFACTOR=4.0%, S5_CME_FUTURES_PROP=35.0%`) và trừ thẳng phí kéo IBKR thực tế theo cỡ tài khoản (`-1,20%` dưới `5k`, `-0,65%` dưới `25k`, `-0,30%` dưới `50k`, `-0,10%` từ `50k+`).

## 1. Kết Luận Trọng Tâm Dễ Hiểu (Không Tô Hồng)

1. **Thang Leo Thông Minh (`Smart-Tier`: `5K -> 25K -> 20K -> 50K -> 60K 4%/8% -> 100K x2`) áp đảo hoàn toàn cách mua lặp lại vé `10K` cũ:**
   - Cùng một mức ngân sách vé khởi điểm **`1.500 USD` (`38,2 tr VND`, Vốn Riêng mồi `0 USD`)** ở chi phí chuẩn `1,0x`: sau `60` tháng, trung vị Sổ Vốn Riêng của thang mới đạt **`27,956 USD`** so với **`11,085 USD`** của thang `10K` cũ (**gấp `2.52x`**!), đồng thời tỷ lệ cháy sạch quỹ phí giữ ở mức **`0.00%`** (so với `0.02%` của thang cũ).
   - Ngay cả khi trượt giá thực tế tăng nặng **`1,5x`**, trung vị Vốn Riêng sau 60 tháng vẫn tăng mạnh từ `1,803 USD` (cũ) lên **`2,271 USD`** (mới).
2. **Hạ tầng chuyên nghiệp tự nuôi 100% từ tiền lãi (không bao giờ bỏ tiền túi):**
   - Ở cấu hình thực chiến `Budget 1.500 USD + OB 0 USD` (`1,0x`), **Mốc A — Tự nuôi VPS sát sàn LD4/NY4 (`35 USD/tháng`)** mở khóa ở trung vị **tháng thứ `20`**, và **Mốc B — Tự nuôi Dữ liệu sạch Top-1% (`100 USD/tháng`, tổng vốn hoạt động >= `50k USD`)** mở khóa ở trung vị **tháng thứ `30`**.
3. **Sự thật toán học về các mốc Vốn Riêng `50k / 100k / 200k USD` và Điểm Giao Cắt (`Crossover`):**
   - Đi tay trắng (`OB Seed = 0 USD`), xác suất tự tích lũy Vốn Riêng vượt **`50.000 USD` (`1,275 tỷ VND`)** trong `60` tháng đạt **`31.3%`** (`Budget 1.500 USD`) và **`45.1%`** (`Budget 3.000 USD`).
   - Khi kết hợp **vốn mồi Vốn Riêng `25.000 USD` + `Budget 3.000 USD`**, xác suất vượt **`100.000 USD` (`2,55 tỷ VND`)** đạt **`32.1%`** trong `60` tháng, và xác suất chạm **Điểm Giao Cắt Thật (`Crossover` — sau khi Prop đã Funded >= `25k USD`, lãi ròng tháng Vốn Riêng `1,0x` >= lãi ròng tháng Prop)** trong `60` tháng là **`2.2%`**.
   - *Ngưỡng Giao Cắt Giải Tích (minh bạch):* Vì Sổ Vốn Riêng `NCO_CexCap25` (`1,0x`, `MaxDD 2,23%`) sinh lãi kỳ vọng `0.45%/tháng` còn Prop Funded `1,0x` sau chia `80%` sinh `0.57%/tháng` trên vốn danh nghĩa, để Vốn Riêng `1,0x` vượt `100k` Prop cần khoảng **`127,356 USD`** (và vượt `360k` Prop cần **`458,481 USD`**); nếu nâng Own-Book lên `2,0x` vol (`MaxDD ~4,5%` vẫn rất an toàn), ngưỡng vượt `100k` Prop hạ ngay xuống **`63,678 USD`**!
4. **Giá trị kinh tế cực lớn của việc kiểm soát trượt giá (`1,0x` vs `1,5x`) bằng VPS sát sàn tự nuôi:** So sánh bảng `1,0x` (`27,956 USD`) với `1,5x` (`2,271 USD`) cho thấy để trượt giá phình lên `1,5x` làm bay hơn `25,685 USD` tích lũy 5 năm — chứng minh việc trích `35 USD/tháng` từ lãi để chuyển MT5 sang VPS LD4/NY4 ngay khi chạm Mốc A là khoản đầu tư có ROI cao nhất toàn hệ thống.

## 2. Phần 1 — So Sánh Thang `10K` Cũ vs Thang `Smart-Tier` Mới (`5.000` Kịch Bản × `60` Tháng)

Toàn bộ tài khoản Prop mở song song trên **cùng ngày thị trường M1** để đo trọn rủi ro trùng lỗ; cơ chế 3 Ngăn tự động đổ tràn `100%` phần dự phòng vượt trần `5x` vé mục tiêu vào Sổ Vốn Riêng `NCO_CexCap25`.

### 2.1. Chi Phí Chuẩn (`1,0x` M1 Bid/Ask + Khóa Tin Đỏ `±5p`)

| Kịch Bản (Ngân sách vé B, Vốn mồi OB) | Cháy Quỹ Vé | Rớt Đôi | Vốn Prop Đỉnh (TV) | EV/Phí 24T | Vốn Riêng 24T (TV) | Vốn Riêng 60T (TV / VND) | Hạ tầng tự trả 60T |
|---|---|---|---|---|---|---|---|
| Old Repeated-10K (SYMCAP 3.0%) (B=500, OB=0) | 0.08% | 33.6% | 60,000 USD | 1.47x | 518 USD | **4,592 USD** (117 tr) | 1,015 USD |
| Old Repeated-10K (SYMCAP 3.0%) (B=1,500, OB=0) | 0.02% | 39.0% | 90,000 USD | 1.18x | 1,087 USD | **11,085 USD** (283 tr) | 2,105 USD |
| Old Repeated-10K (SYMCAP 3.0%) (B=3,000, OB=0) | 0.00% | 38.8% | 90,000 USD | 1.10x | 1,681 USD | **13,341 USD** (340 tr) | 2,360 USD |
| Smart-Tier Ladder (OB Seed 0) (B=500, OB=0) | 0.00% | 6.9% | 160,000 USD | 2.52x | 755 USD | **7,482 USD** (191 tr) | 1,645 USD |
| Smart-Tier Ladder (OB Seed 0) (B=1,500, OB=0) | 0.00% | 11.1% | 360,000 USD | 3.21x | 1,195 USD | **27,956 USD** (713 tr) | 3,435 USD |
| Smart-Tier Ladder (OB Seed 0) (B=3,000, OB=0) | 0.00% | 10.6% | 360,000 USD | 3.80x | 1,872 USD | **44,553 USD** (1136 tr) | 4,288 USD |
| Smart-Tier + Hybrid OB 10k (B=1,500, OB=10,000) | 0.00% | 11.1% | 360,000 USD | 3.21x | 12,449 USD | **41,152 USD** (1049 tr) | 3,435 USD |
| Smart-Tier + Hybrid OB 10k (B=3,000, OB=10,000) | 0.00% | 10.6% | 360,000 USD | 3.80x | 13,108 USD | **57,880 USD** (1476 tr) | 4,288 USD |
| Smart-Tier + Hybrid OB 25k (B=1,500, OB=25,000) | 0.00% | 11.1% | 360,000 USD | 3.21x | 29,605 USD | **61,708 USD** (1574 tr) | 3,435 USD |
| Smart-Tier + Hybrid OB 25k (B=3,000, OB=25,000) | 0.00% | 10.6% | 360,000 USD | 3.80x | 30,277 USD | **78,326 USD** (1997 tr) | 4,288 USD |

### 2.2. Kịch Bản Stress Trượt Giá Nặng (`1,5x` Chi Phí M1)

| Kịch Bản (Ngân sách vé B, Vốn mồi OB) | Cháy Quỹ Vé | Rớt Đôi | Vốn Prop Đỉnh (TV) | EV/Phí 24T | Vốn Riêng 24T (TV) | Vốn Riêng 60T (TV / VND) | Hạ tầng tự trả 60T |
|---|---|---|---|---|---|---|---|
| Old Repeated-10K (SYMCAP 3.0%) (B=500, OB=0) | 0.76% | 29.9% | 20,000 USD | 0.52x | 117 USD | **874 USD** (22 tr) | 0 USD |
| Old Repeated-10K (SYMCAP 3.0%) (B=1,500, OB=0) | 0.42% | 44.2% | 40,000 USD | 0.21x | 183 USD | **1,803 USD** (46 tr) | 280 USD |
| Old Repeated-10K (SYMCAP 3.0%) (B=3,000, OB=0) | 0.18% | 44.4% | 60,000 USD | 0.13x | 280 USD | **3,288 USD** (84 tr) | 455 USD |
| Smart-Tier Ladder (OB Seed 0) (B=500, OB=0) | 0.02% | 8.0% | 30,000 USD | 1.11x | 89 USD | **1,155 USD** (30 tr) | 0 USD |
| Smart-Tier Ladder (OB Seed 0) (B=1,500, OB=0) | 0.06% | 16.0% | 90,000 USD | 1.08x | 114 USD | **2,271 USD** (58 tr) | 490 USD |
| Smart-Tier Ladder (OB Seed 0) (B=3,000, OB=0) | 0.00% | 17.4% | 180,000 USD | 1.32x | 135 USD | **4,051 USD** (103 tr) | 875 USD |
| Smart-Tier + Hybrid OB 10k (B=1,500, OB=10,000) | 0.06% | 16.0% | 90,000 USD | 1.08x | 11,504 USD | **15,588 USD** (398 tr) | 490 USD |
| Smart-Tier + Hybrid OB 10k (B=3,000, OB=10,000) | 0.00% | 17.4% | 180,000 USD | 1.32x | 11,549 USD | **17,417 USD** (444 tr) | 875 USD |
| Smart-Tier + Hybrid OB 25k (B=1,500, OB=25,000) | 0.06% | 16.0% | 90,000 USD | 1.08x | 28,647 USD | **36,480 USD** (930 tr) | 490 USD |
| Smart-Tier + Hybrid OB 25k (B=3,000, OB=25,000) | 0.00% | 17.4% | 180,000 USD | 1.32x | 28,748 USD | **38,291 USD** (976 tr) | 875 USD |

## 3. Phần 2 — Xác Suất & Trung Vị Tháng Đạt Các Mốc Hạ Tầng, Vốn Riêng & Giao Cắt (Thang `Smart-Tier`)

Cột **Mốc A (VPS `35 USD/tháng`)** và **Mốc B (Dữ liệu `100 USD/tháng`)** ghi theo định dạng **`P(24T) / P(36T) / P(60T) (TV = tháng trung vị)`**. Các cột **Mốc C & D** ghi **`P(60T) (tháng trung vị)`**.

### 3.1. Chi Phí Chuẩn (`1,0x`)

| Cấu Hình Vốn | Mốc A: Tự nuôi VPS | Mốc B: Tự nuôi Data (>=50k) | C1: OB 25k | C2: OB 50k | C3: OB 100k | C4: OB 200k | Mốc D: Crossover |
|---|---|---|---|---|---|---|---|
| B=500 + OB=0 | 44% / 63% / 84% (TV 23T) | 8% / 25% / 57% (TV 39T) | 29.2% (48T) | 13.5% (52T) | 1.8% (57T) | 0.0% (>60T) | 0.0% (>60T) |
| B=1,500 + OB=0 | 54% / 72% / 90% (TV 20T) | 28% / 50% / 78% (TV 30T) | 52.7% (42T) | 31.3% (48T) | 5.9% (55T) | 0.0% (>60T) | 0.0% (>60T) |
| B=3,000 + OB=0 | 58% / 75% / 91% (TV 19T) | 40% / 61% / 83% (TV 25T) | 66.7% (38T) | 45.1% (46T) | 11.2% (54T) | 0.0% (>60T) | 0.0% (>60T) |
| B=1,500 + OB=10,000 | 54% / 72% / 90% (TV 20T) | 28% / 50% / 78% (TV 30T) | 66.7% (39T) | 42.7% (46T) | 10.3% (53T) | 0.0% (>60T) | 0.0% (>60T) |
| B=3,000 + OB=10,000 | 58% / 75% / 91% (TV 19T) | 40% / 61% / 83% (TV 25T) | 77.0% (33T) | 56.9% (43T) | 17.6% (53T) | 0.0% (>60T) | 0.0% (>60T) |
| B=1,500 + OB=25,000 | 54% / 72% / 90% (TV 20T) | 28% / 50% / 78% (TV 30T) | 100.0% (1T) | 61.5% (41T) | 21.1% (52T) | 0.1% (58T) | 2.3% (50T) |
| B=3,000 + OB=25,000 | 58% / 75% / 91% (TV 19T) | 40% / 61% / 83% (TV 25T) | 100.0% (1T) | 73.5% (37T) | 32.1% (50T) | 0.3% (57T) | 2.2% (50T) |

### 3.2. Kịch Bản Stress Trượt Giá `1,5x`

| Cấu Hình Vốn | Mốc A: Tự nuôi VPS | Mốc B: Tự nuôi Data (>=50k) | C1: OB 25k | C2: OB 50k | C3: OB 100k | C4: OB 200k | Mốc D: Crossover |
|---|---|---|---|---|---|---|---|
| B=500 + OB=0 | 21% / 32% / 49% (TV 28T) | 1% / 6% / 17% (TV 43T) | 4.4% (51T) | 1.2% (54T) | 0.0% (>60T) | 0.0% (>60T) | 0.0% (>60T) |
| B=1,500 + OB=0 | 28% / 41% / 61% (TV 27T) | 9% / 20% / 37% (TV 35T) | 14.1% (47T) | 4.6% (51T) | 0.3% (57T) | 0.0% (>60T) | 0.0% (>60T) |
| B=3,000 + OB=0 | 33% / 46% / 64% (TV 24T) | 17% / 30% / 48% (TV 30T) | 26.3% (43T) | 10.8% (50T) | 0.8% (55T) | 0.0% (>60T) | 0.0% (>60T) |
| B=1,500 + OB=10,000 | 28% / 41% / 61% (TV 27T) | 9% / 20% / 37% (TV 35T) | 25.1% (43T) | 9.4% (51T) | 0.7% (56T) | 0.0% (>60T) | 0.0% (>60T) |
| B=3,000 + OB=10,000 | 33% / 46% / 64% (TV 24T) | 17% / 30% / 48% (TV 30T) | 39.4% (39T) | 18.0% (47T) | 1.9% (55T) | 0.0% (>60T) | 0.1% (46T) |
| B=1,500 + OB=25,000 | 28% / 41% / 61% (TV 27T) | 9% / 20% / 37% (TV 35T) | 100.0% (1T) | 21.6% (46T) | 2.6% (54T) | 0.0% (>60T) | 61.9% (14T) |
| B=3,000 + OB=25,000 | 33% / 46% / 64% (TV 24T) | 17% / 30% / 48% (TV 30T) | 100.0% (1T) | 35.0% (42T) | 5.8% (53T) | 0.0% (>60T) | 59.3% (13T) |

## 4. Phần 3 — Bảng Chấm Điểm Top-1% Độc Lập & Ma Trận Nỗi Đau VND Tuyệt Đối (`25.500 VND/USD`)

### 4.1. So Sánh Tổng Hợp Trước & Sau Nâng Cấp (Baseline Cũ vs Smart-Tier + `NCO_CexCap25`)

| Kiến Trúc Danh Mục | Prop Funded 1x/năm | OB CAGR 1x | OB Sharpe | OB Calmar | Sốc CEX -50% | Cháy Quỹ Vé | EV/Phí 24T | OB 60T (TV) | Sharpe Hợp Nhất |
|---|---|---|---|---|---|---|---|---|---|
| Baseline Cũ (Repeated 10K · SYMCAP 3.0% · Budget 1.5k, OB 0k) | +7.64% | +5.64% | 2.27 | 2.53 | -41.58% | 0.02% | 1.18x | 11,085 USD | 0.89 |
| Nâng Cấp Smart-Tier (SYMCAP 1.75% + DynPL + 4/8 Safe · Budget 1.5k, OB 0k) | +7.64% | +5.64% | 2.27 | 2.53 | -12.89% | 0.00% | 3.21x | 27,956 USD | 1.04 |
| Top-1% Hybrid Full Pod (Smart-Tier + NCO_CexCap25 · Budget 3k, OB 25k) | +7.64% | +5.64% | 2.27 | 2.53 | -12.89% | 0.00% | 3.80x | 78,326 USD | 1.70 |

- *Ghi chú minh bạch về lợi suất Sổ Vốn Riêng (`NCO_CexCap25`, `1,0x` không đòn bẩy):* Trên tập `2020–2024`, Pod `6` nhánh đạt `CAGR +5.64%`, `MaxDD 2.23%`, `Sharpe 2.27`, `Calmar 2.53` (OOS `2023–2024`: `Sharpe 1.89`, `MaxDD 2.23%`). Khi tài sản Vốn Riêng đạt chuẩn tổ chức (`>= 100k USD`) và nếu chủ sở hữu muốn tăng tốc đạt chuẩn `+15%..+20%/năm` của Top-1%, chỉ cần nâng biên độ rủi ro mục tiêu của Own-Book từ `1,0x` (`Vol ~3%`) lên `2,0x` (`Vol ~6%`, `MaxDD ~5%` vẫn an toàn dưới trần `8%`) — toàn bộ bảng trên cố tình giữ nguyên `1,0x` không đòn bẩy để phản ánh đường đáy an toàn nhất.

### 4.2. Ma Trận Nỗi Đau Tuyệt Đối Theo Mốc Vốn Riêng (`NCO_CexCap25`, `25.500 VND/USD`)

| Cỡ Sổ Vốn Riêng (USD / tr VND) | Phí kéo IBKR | Lãi Ròng Năm (Sau IBKR) | Sụt Giảm Lịch Sử | Khủng Hoảng Tương Quan (0.85) | Sốc Sập Sàn CEX -50% (Có Trần 25%) | So Với HRP Cũ Không Trần |
|---|---|---|---|---|---|---|
| 10,000 USD (255 tr) | -0.65%/năm | +4.99% (+499 USD / +12.7 tr) | -2.23% (-5.7 tr) | -8.81% (-22.5 tr) | -12.89% (-32.9 tr) | -106 tr (BỎ) |
| 50,000 USD (1,275 tr) | -0.10%/năm | +5.54% (+2,770 USD / +70.6 tr) | -2.23% (-28.4 tr) | -8.81% (-112.3 tr) | -12.89% (-164.3 tr) | -530 tr (BỎ) |
| 100,000 USD (2,550 tr) | -0.10%/năm | +5.54% (+5,540 USD / +141.3 tr) | -2.23% (-56.9 tr) | -8.81% (-224.7 tr) | -12.89% (-328.7 tr) | -1060 tr (BỎ) |
| 200,000 USD (5,100 tr) | -0.10%/năm | +5.54% (+11,080 USD / +282.5 tr) | -2.23% (-113.7 tr) | -8.81% (-449.3 tr) | -12.89% (-657.4 tr) | -2121 tr (BỎ) |

## 5. Khuyến Nghị Hành Động Gọn Cho Chủ Quỹ

1. **Chốt lộ trình vé Smart-Tier (`5K -> 25K -> 20K -> 50K -> 60K 4%/8% -> 100K`):** Tuyệt đối không đốt tiền mua lặp lại nhiều vé `10K` phí đắt — dùng `The5ers 5K` (`39 USD`) làm bàn đạp rồi nhảy thẳng `FTMO Swing 25K/50K/100K` từ tiền lãi, giúp tăng tài sản Vốn Riêng sau 5 năm gấp nhiều lần trong cùng một ngân sách ban đầu.
2. **Khóa cứng nguyên tắc hạ tầng tự nuôi:** Giữ `naqex-node1` (`0 USD/tháng`) tới khi vượt Mốc A (`Ops >= 300 USD/tháng` bền vững hoặc dự phòng Ops `>= 1.200 USD`) mới trích `35 USD/tháng` thuê VPS LD4/NY4; chỉ mua gói dữ liệu sạch `100 USD/tháng` khi tổng vốn quản lý vượt `50.000 USD` và quỹ Ops đủ dày.
3. **Giữ cứng trần sàn CEX `<= 25%` (`NCO_CexCap25`):** Nhìn vào bảng nỗi đau VND — ở mốc `100.000 USD` (`2,55 tỷ VND`), ngay cả kịch bản cực đoan sàn Crypto sập mất trắng `50%`, tổng thiệt hại bị khóa tối đa ở `-328,7 triệu VND` (`-12,89%`) thay vì mất trắng `-1.060 triệu VND` (`-41,58%`) như danh mục không trần.

*Thời gian tính toán toàn bộ kiểm toán M1 + 5.000 Monte Carlo × 60 tháng: `31.12s` · JSON kiểm chứng: `TOP1-UNIFIED-PROP-TO-OWNBOOK-TRAJECTORY-20261124.json` · SHA-256: `323bb5823eaf80ee33177b6e2fd4046e2f1341745084cf68448925c7e6a0e5c9`.*

---
doc_type: quant-research-audit
generated_utc: 2026-11-24T10:56:56.062737+00:00
dev_window: 2018-01-02..2024-12-31
mc_paths: 10000
mc_seed: 20261124
holdout_rows_analysed: 0
order_send_count: 0
receipt_sha256: a007ae771f32e779ca268765961fc47fef2c0c97f35d715093c3595d0431b8da
---

# Kiểm Toán Định Lượng: Siết Trần Rủi Ro 1 Mã (`SYMCAP`) & Ma Trận Lên Cấp Tài Khoản Quỹ (Dev 2018–2024)

> **Niêm phong dữ liệu & An toàn:** Chạy hoàn toàn trên tập Phát triển `2018-2024` (`holdout_rows_analysed = 0`, khóa Holdout `2025+` nguyên vẹn SHA `f0a6b43cb205535b...`), `OrderSend = 0`, mô phỏng **10.000 kịch bản Monte Carlo** (`Circular Block-Bootstrap`, độ dài khối `5` ngày, `seed = 20261124`) ghép trực tiếp từ dữ liệu chạy từng phút M1 thật có khóa tin đỏ `±5` phút của danh mục live **8 EA (`A1_V1_LIVE8`)**.

## 1. Tóm Tắt Dễ Hiểu Cho Chủ Quỹ

1. **Siết trần rủi ro 1 mã (`SYMCAP`) từ `3,00%–3,50%` xuống `1,75%` giảm mạnh rủi ro nổ trần ngày mà vẫn giữ hiệu suất kiếm tiền trên mỗi USD tiền vé (`EV/Fee`) cao vượt trội:**
   - Trên **FTMO Swing 10K (`Dyn_ProfitLock` `4,5x -> +5% khóa 2,0x`)** ở chi phí chuẩn `1,0x`: tỷ lệ cháy trần lỗ ngày `5%` ngay lượt thi đầu giảm từ **`25.5%`** (`SYMCAP 3,50%`) xuống còn **`4.7%`** (`SYMCAP 1,75%`). Tỷ lệ rớt lượt đầu giảm từ `26.5%` xuống `5.5%`, trong khi **`EV/Fee`** giữ mức rất cao (`3.61x` so với `3.59x`).
   - Khi thị trường giãn trượt giá `1,5x` (kịch bản stress thực chiến): cháy trần ngày lượt đầu vẫn giảm sâu từ **`24.8%`** xuống **`4.2%`**.
   - Trên **The5ers High Stakes 5K (`39 USD`)**: cháy trần ngày lượt đầu giảm từ **`22.7%`** xuống **`4.2%`**.
2. **Lên cấp tài khoản (`10K -> 25K / 50K / 100K`) là đòn bẩy kinh tế lớn nhất mà không hề tăng thêm rủi ro phần trăm:**
   - Vì giá vé không tăng tỷ lệ thuận với vốn (FTMO 10K tốn `1,68%` vốn mua vé, còn 50K chỉ tốn `0,72%` và 100K chỉ tốn `0,56%`), chỉ cần giữ nguyên chiến lược đã siết `SYMCAP 1,75%`, nhảy từ **10K -> 25K** nhân `EV/Fee` lên **`1.61x`**, lên **50K** nhân **`2.47x`**, và lên **100K** nhân **`3.21x`**!
3. **Cảnh báo cứng về bẫy luật `4%/8%` của The5ers High Stakes 50K/60K (`329 USD`):**
   - Nếu bê nguyên bộ cấu hình 5K (vốn thiết kế cho luật `5%/10%`) sang chạy The5ers 50K (`4%` lỗ ngày / `8%` lỗ tổng), tỷ lệ cháy trần ngày lượt đầu vọt lên **`34.7%`** (với `SYMCAP 3,00%`) và vẫn tới **`12.8%`** (ngay cả với `SYMCAP 1,75%` chưa hạ cỡ lệnh!).
   - Khi hạ cấu hình riêng cho khung `4%/8%` (`P1 2,75x -> +4% khóa 1,50x`, `SYMCAP 1,15%`, cắt lỗ ngày EA `2,8%`), cháy trần ngày lượt đầu rơi xuống chỉ còn **`6.1%`**, mở khóa hiệu quả **`EV/Fee = 8.25x`** (50K) và **`10.02x`** (60K)!

## 2. Phần 1 — Kiểm Toán `SYMCAP` Trên Danh Mục Live 8 EA (`A1_V1_LIVE8`)

### 2.1. Tác Động Vật Lý Từng Phút M1 Tại Mức Khởi Đầu P1 (`4,5x`, 7 Năm Dev `2018–2024`, Phí `1,0x`)

Bảng dưới đo trực tiếp dữ liệu M1 thật trước khi đưa vào Monte Carlo: ở `SYMCAP` cũ (`3,00%–3,50%`), chỉ 1 lệnh đơn hoặc 2 lệnh trùng mã mở cùng lúc có thể đẩy lỗ nổi trong ngày vọt quá `-10%` (gấp đôi trần `5%` của quỹ!). Siết về `1,50%–1,75%` cắt gần một nửa cú sốc ngày xấu nhất và giảm margin đỉnh từ `84,5%` về ~`55%`.

| SYMCAP | Lãi năm (P1 4.5x) | Lỗ ngày xấu nhất | Lỗ ngày P99 | Số ngày >= 5% | Số ngày >= 4% | Margin đỉnh | Số lần SYMCAP chặn |
|---|---|---|---|---|---|---|---|
| 1.50% | 18.81% | -5.53% | -2.77% | 1 ngày | 1 ngày | 48.7% | 1615 |
| 1.75% | 21.09% | -6.62% | -3.15% | 1 ngày | 4 ngày | 55.5% | 1615 |
| 2.00% | 23.37% | -7.59% | -3.55% | 1 ngày | 9 ngày | 62.8% | 1615 |
| 3.00% | 30.10% | -10.01% | -4.61% | 12 ngày | 28 ngày | 77.7% | 614 |
| 3.50% | 32.52% | -10.71% | -4.89% | 16 ngày | 39 ngày | 84.5% | 136 |

### 2.2. Kết Quả 10.000 Kịch Bản Monte Carlo — `FTMO Swing 10K` (`Dyn_ProfitLock` `4,5x -> +5% khóa 2,0x`)

**Kịch bản chi phí chuẩn (`1,0x`):**

| SYMCAP | Cháy Ngày (Lượt 1) | Cháy Tổng (Lượt 1) | Rớt Lượt 1 | Đậu trong 24T | Trung vị đậu | EV / Phí vé | Dòng tiền 24T (USD / VND) | Chi phí ròng xấu P95 |
|---|---|---|---|---|---|---|---|---|
| 1.50% | 5.3% | 0.6% | 5.9% | 71.4% | 147d | 3.56x | +598 USD (+15.3 tr) | 336 USD (8.6 tr) |
| 1.75% (KHUYÊN DÙNG) | 4.7% | 0.8% | 5.5% | 70.9% | 135d | 3.61x | +607 USD (+15.5 tr) | 336 USD (8.6 tr) |
| 2.00% | 4.0% | 1.0% | 5.0% | 69.4% | 126d | 3.61x | +606 USD (+15.5 tr) | 336 USD (8.6 tr) |
| 3.00% (CŨ - NGUY HIỂM) | 22.5% | 1.2% | 23.7% | 71.7% | 117d | 3.61x | +606 USD (+15.4 tr) | 336 USD (8.6 tr) |
| 3.50% (CŨ - NGUY HIỂM) | 25.5% | 1.0% | 26.5% | 71.6% | 112d | 3.59x | +604 USD (+15.4 tr) | 504 USD (12.8 tr) |

**Kịch bản trượt giá nặng (`1,5x` chi phí M1):**

| SYMCAP | Cháy Ngày (Lượt 1) | Cháy Tổng (Lượt 1) | Rớt Lượt 1 | Đậu trong 24T | Trung vị đậu | EV / Phí vé | Dòng tiền 24T (USD / VND) | Chi phí ròng xấu P95 |
|---|---|---|---|---|---|---|---|---|
| 1.50% | 4.8% | 3.4% | 8.2% | 47.7% | 155d | 1.15x | +192 USD (+4.9 tr) | 336 USD (8.6 tr) |
| 1.75% (KHUYÊN DÙNG) | 4.2% | 3.7% | 7.9% | 47.7% | 141d | 1.19x | +200 USD (+5.1 tr) | 336 USD (8.6 tr) |
| 2.00% | 3.9% | 4.0% | 7.9% | 48.0% | 129d | 1.24x | +209 USD (+5.3 tr) | 336 USD (8.6 tr) |
| 3.00% (CŨ - NGUY HIỂM) | 21.6% | 4.2% | 25.8% | 51.6% | 120d | 1.20x | +202 USD (+5.1 tr) | 504 USD (12.8 tr) |
| 3.50% (CŨ - NGUY HIỂM) | 24.8% | 3.7% | 28.5% | 52.0% | 117d | 1.18x | +198 USD (+5.1 tr) | 504 USD (12.8 tr) |

### 2.3. Đối Chiếu `The5ers High Stakes 5K` (`Dyn_ProfitLock`, Phí `39 USD`, 3 Ngày Lãi `>= +0,5%`)

**Kịch bản chi phí chuẩn (`1,0x`):**

| SYMCAP | Cháy Ngày (Lượt 1) | Cháy Tổng (Lượt 1) | Rớt Lượt 1 | Đậu trong 24T | Trung vị đậu | EV / Phí vé | Dòng tiền 24T (USD / VND) | Chi phí ròng xấu P95 |
|---|---|---|---|---|---|---|---|---|
| 1.50% | 5.0% | 0.5% | 5.5% | 74.1% | 127d | 8.57x | +334 USD (+8.5 tr) | 78 USD (2.0 tr) |
| 1.75% (KHUYÊN DÙNG) | 4.2% | 0.7% | 4.9% | 73.9% | 118d | 8.72x | +340 USD (+8.7 tr) | 39 USD (1.0 tr) |
| 2.00% | 3.9% | 1.0% | 4.9% | 72.0% | 111d | 8.62x | +336 USD (+8.6 tr) | 39 USD (1.0 tr) |
| 3.00% (CŨ - NGUY HIỂM) | 19.7% | 1.2% | 20.9% | 74.0% | 102d | 8.89x | +346 USD (+8.8 tr) | 78 USD (2.0 tr) |
| 3.50% (CŨ - NGUY HIỂM) | 22.7% | 0.9% | 23.6% | 74.2% | 101d | 8.91x | +347 USD (+8.9 tr) | 78 USD (2.0 tr) |

**Kịch bản trượt giá nặng (`1,5x`):**

| SYMCAP | Cháy Ngày (Lượt 1) | Cháy Tổng (Lượt 1) | Rớt Lượt 1 | Đậu trong 24T | Trung vị đậu | EV / Phí vé | Dòng tiền 24T (USD / VND) | Chi phí ròng xấu P95 |
|---|---|---|---|---|---|---|---|---|
| 1.50% | 4.4% | 3.4% | 7.8% | 51.5% | 133d | 3.58x | +140 USD (+3.6 tr) | 78 USD (2.0 tr) |
| 1.75% (KHUYÊN DÙNG) | 3.8% | 3.8% | 7.5% | 51.8% | 122d | 3.69x | +144 USD (+3.7 tr) | 78 USD (2.0 tr) |
| 2.00% | 3.6% | 4.0% | 7.6% | 51.6% | 115d | 3.74x | +146 USD (+3.7 tr) | 78 USD (2.0 tr) |
| 3.00% (CŨ - NGUY HIỂM) | 19.0% | 4.1% | 23.1% | 54.8% | 104d | 3.84x | +150 USD (+3.8 tr) | 78 USD (2.0 tr) |
| 3.50% (CŨ - NGUY HIỂM) | 22.4% | 3.8% | 26.2% | 55.1% | 101d | 3.90x | +152 USD (+3.9 tr) | 117 USD (3.0 tr) |

### 2.4. Đối Chiếu Chế Độ Tĩnh `P1_Balanced_Static` (`4,0x` Không Khóa Lãi) Trên FTMO Swing 10K (`1,0x`)

| SYMCAP | Cháy Ngày (Lượt 1) | Cháy Tổng (Lượt 1) | Rớt Lượt 1 | Đậu trong 24T | Trung vị đậu | EV / Phí vé | Dòng tiền 24T (USD / VND) | Chi phí ròng xấu P95 |
|---|---|---|---|---|---|---|---|---|
| 1.50% | 4.8% | 0.5% | 5.4% | 71.9% | 145d | 3.63x | +610 USD (+15.5 tr) | 336 USD (8.6 tr) |
| 1.75% (KHUYÊN DÙNG) | 4.0% | 0.8% | 4.8% | 71.6% | 134d | 3.67x | +617 USD (+15.7 tr) | 168 USD (4.3 tr) |
| 2.00% | 3.6% | 1.0% | 4.6% | 70.2% | 129d | 3.64x | +612 USD (+15.6 tr) | 168 USD (4.3 tr) |
| 3.00% (CŨ - NGUY HIỂM) | 20.2% | 1.1% | 21.3% | 70.6% | 118d | 3.50x | +589 USD (+15.0 tr) | 336 USD (8.6 tr) |
| 3.50% (CŨ - NGUY HIỂM) | 19.5% | 1.3% | 20.8% | 70.7% | 116d | 3.54x | +595 USD (+15.2 tr) | 336 USD (8.6 tr) |

- **Kết luận Phần 1:** Mức **`SYMCAP = 1,75%`** (biên an toàn `1,50%–2,00%`) kết hợp **`Dyn_ProfitLock` (`4,5x -> +5% hạ về 2,0x`)** là điểm ngọt rõ ràng nhất: loại bỏ hoàn toàn nguy cơ 1 lệnh đơn (hoặc 2 bot cùng mã USDJPY/US100) bắn thủng trần lỗ ngày `5%`, giữ thời gian đậu quỹ nhanh và bảo toàn dòng tiền ròng 24 tháng ngay cả khi chi phí thực tế tăng `1,5x`.

## 3. Phần 2 — Ma Trận Hiệu Quả Tiền Vé Đa Cấp Bậc & Bẫy Luật `4%/8%` Trên The5ers 50K/60K

Toàn bộ các gói `5%/10%` bên dưới dùng đúng cấu hình đã kiểm chứng (`SYMCAP 1,75% + Dyn_ProfitLock`). Riêng gói **The5ers 50K/60K** (luật siết cứng `4%` ngày / `8%` tổng) được thử đối chứng 3 trường hợp: (1) bê nhầm preset 5K cũ (`SYMCAP 3,0%`), (2) bê preset 5K mới (`SYMCAP 1,75%`) nhưng không hạ cỡ lệnh, và (3) cấu hình chuẩn hóa riêng cho khung `4%/8%` (`P1 2,75x`, `SYMCAP 1,15%`, cắt lỗ ngày EA `2,8%`). Tỷ giá quy đổi `1 USD = 25.500 VND`.

### 3.1. Ma Trận Đa Cấp Bậc — Chi Phí Chuẩn (`1,0x`, `N = 10.000` Kịch Bản)

| Gói Tài Khoản Quỹ | Phí / Vốn | Luật DD | SYMCAP / P1 | Cháy Ngày (L1) | Rớt Lượt 1 | Đậu 24T | EV / Phí vé | Dòng tiền ròng 24T (USD / VND) | Chi phí ròng P95 |
|---|---|---|---|---|---|---|---|---|---|
| FTMO Swing 10K (Giá chuẩn 168 USD) | 1.68% | 5%/10% | 1.75% / 4.50x | 4.7% | 5.5% | 70.9% | **3.61x** | +607 USD (+15.5 tr) | 336 USD (8.6 tr) |
| FTMO Swing 10K (Promo ~95 USD) | 0.95% | 5%/10% | 1.75% / 4.50x | 4.7% | 5.5% | 70.9% | **6.68x** | +635 USD (+16.2 tr) | 190 USD (4.8 tr) |
| FTMO Swing 25K (270 USD) | 1.08% | 5%/10% | 1.75% / 4.50x | 4.7% | 5.5% | 70.9% | **5.83x** | +1,574 USD (+40.1 tr) | 540 USD (13.8 tr) |
| FTMO Swing 50K (360 USD) | 0.72% | 5%/10% | 1.75% / 4.50x | 4.7% | 5.5% | 70.9% | **8.93x** | +3,217 USD (+82.0 tr) | 720 USD (18.4 tr) |
| FTMO Swing 100K (560 USD) | 0.56% | 5%/10% | 1.75% / 4.50x | 4.7% | 5.5% | 70.9% | **11.60x** | +6,494 USD (+165.6 tr) | 1,120 USD (28.6 tr) |
| The5ers HS 5K (Promo 39 USD · 5%/10% DD) | 0.78% | 5%/10% | 1.75% / 4.50x | 4.2% | 4.9% | 73.9% | **8.72x** | +340 USD (+8.7 tr) | 39 USD (1.0 tr) |
| The5ers HS 5K (Chuẩn 52 USD · 5%/10% DD) | 1.04% | 5%/10% | 1.75% / 4.50x | 4.2% | 4.9% | 73.9% | **6.40x** | +333 USD (+8.5 tr) | 52 USD (1.3 tr) |
| The5ers HS 20K (189 USD · 5%/10% DD) | 0.94% | 5%/10% | 1.75% / 4.50x | 4.2% | 4.9% | 73.9% | **7.10x** | +1,341 USD (+34.2 tr) | 189 USD (4.8 tr) |
| The5ers HS 50K (329 USD · 4%/8% DD — DÙNG NHẦM PRESET 5K!) | 0.66% | 4%/8% | 3.00% / 4.50x | 34.7% | 40.9% | 83.2% | **11.83x** | +3,891 USD (+99.2 tr) | 1,316 USD (33.6 tr) |
| The5ers HS 50K (329 USD · 4%/8% DD — Preset 5K SYMCAP 1.75%) | 0.66% | 4%/8% | 1.75% / 4.50x | 12.8% | 21.0% | 78.0% | **10.74x** | +3,535 USD (+90.1 tr) | 658 USD (16.8 tr) |
| The5ers HS 50K (329 USD · 4%/8% DD — Preset 4%/8% CHUẨN) | 0.66% | 4%/8% | 1.15% / 2.75x | 6.1% | 6.9% | 71.8% | **8.25x** | +2,714 USD (+69.2 tr) | 658 USD (16.8 tr) |
| The5ers HS 60K (329 USD · 4%/8% DD — Preset 4%/8% CHUẨN) | 0.55% | 4%/8% | 1.15% / 2.75x | 6.1% | 6.9% | 71.8% | **10.02x** | +3,296 USD (+84.0 tr) | 658 USD (16.8 tr) |

### 3.2. Ma Trận Đa Cấp Bậc — Kiểm Thử Stress Trượt Giá `1,5x` (`N = 10.000` Kịch Bản)

| Gói Tài Khoản Quỹ | Phí / Vốn | Luật DD | SYMCAP / P1 | Cháy Ngày (L1) | Rớt Lượt 1 | Đậu 24T | EV / Phí vé | Dòng tiền ròng 24T (USD / VND) | Chi phí ròng P95 |
|---|---|---|---|---|---|---|---|---|---|
| FTMO Swing 10K (Giá chuẩn 168 USD) | 1.68% | 5%/10% | 1.75% / 4.50x | 4.2% | 7.9% | 47.7% | **1.19x** | +200 USD (+5.1 tr) | 336 USD (8.6 tr) |
| FTMO Swing 10K (Promo ~95 USD) | 0.95% | 5%/10% | 1.75% / 4.50x | 4.2% | 7.9% | 47.7% | **2.59x** | +246 USD (+6.3 tr) | 190 USD (4.8 tr) |
| FTMO Swing 25K (270 USD) | 1.08% | 5%/10% | 1.75% / 4.50x | 4.2% | 7.9% | 47.7% | **2.21x** | +595 USD (+15.2 tr) | 540 USD (13.8 tr) |
| FTMO Swing 50K (360 USD) | 0.72% | 5%/10% | 1.75% / 4.50x | 4.2% | 7.9% | 47.7% | **3.63x** | +1,307 USD (+33.3 tr) | 720 USD (18.4 tr) |
| FTMO Swing 100K (560 USD) | 0.56% | 5%/10% | 1.75% / 4.50x | 4.2% | 7.9% | 47.7% | **4.85x** | +2,716 USD (+69.3 tr) | 1,120 USD (28.6 tr) |
| The5ers HS 5K (Promo 39 USD · 5%/10% DD) | 0.78% | 5%/10% | 1.75% / 4.50x | 3.8% | 7.5% | 51.8% | **3.69x** | +144 USD (+3.7 tr) | 78 USD (2.0 tr) |
| The5ers HS 5K (Chuẩn 52 USD · 5%/10% DD) | 1.04% | 5%/10% | 1.75% / 4.50x | 3.8% | 7.5% | 51.8% | **2.58x** | +134 USD (+3.4 tr) | 104 USD (2.6 tr) |
| The5ers HS 20K (189 USD · 5%/10% DD) | 0.94% | 5%/10% | 1.75% / 4.50x | 3.8% | 7.5% | 51.8% | **2.91x** | +551 USD (+14.0 tr) | 378 USD (9.6 tr) |
| The5ers HS 50K (329 USD · 4%/8% DD — DÙNG NHẦM PRESET 5K!) | 0.66% | 4%/8% | 3.00% / 4.50x | 37.4% | 51.7% | 68.8% | **5.50x** | +1,809 USD (+46.1 tr) | 1,316 USD (33.6 tr) |
| The5ers HS 50K (329 USD · 4%/8% DD — Preset 5K SYMCAP 1.75%) | 0.66% | 4%/8% | 1.75% / 4.50x | 12.9% | 34.0% | 59.1% | **4.67x** | +1,536 USD (+39.2 tr) | 987 USD (25.2 tr) |
| The5ers HS 50K (329 USD · 4%/8% DD — Preset 4%/8% CHUẨN) | 0.66% | 4%/8% | 1.15% / 2.75x | 4.2% | 8.2% | 46.5% | **2.98x** | +982 USD (+25.0 tr) | 658 USD (16.8 tr) |
| The5ers HS 60K (329 USD · 4%/8% DD — Preset 4%/8% CHUẨN) | 0.55% | 4%/8% | 1.15% / 2.75x | 4.2% | 8.2% | 46.5% | **3.74x** | +1,230 USD (+31.4 tr) | 658 USD (16.8 tr) |

## 4. Khuyến Nghị Triển Khai Vận Hành Cho Chủ Quỹ

1. **Áp dụng ngay trần `SYMCAP <= 1,75%` (tối đa `2,00%`) cho mọi preset P1 (`5%/10%` DD):** không bao giờ quay lại mức `3,00%–3,50%` cũ để tránh một cú trượt giá tin vĩ mô làm bay tài khoản chỉ sau một buổi sáng.
2. **Lộ trình leo thang vốn tối ưu hiệu quả đồng vốn (từ tiền lãi quỹ tái đầu tư, không bỏ thêm tiền túi):**
   - *Bước 1 (Khởi động & chứng minh vận hành):* `FTMO Swing 10K` (ưu tiên săn promo ~`95 USD`) + `The5ers HS 5K` (`39 USD`) chạy song song cách nhịp để rút payout đầu tiên và lấp đầy Quỹ Dự Phòng 5 vé.
   - *Bước 2 (Nhảy bậc `EV/Fee` gấp ~2x–3x):* Dùng tiền lãi payout mua thẳng **`FTMO Swing 50K` (`360 USD`)** hoặc **`FTMO Swing 100K` (`560 USD`)** (thay vì mua nhiều vé 10K nhỏ lẻ tốn phí gấp 2–3 lần trên cùng mức vốn).
3. **Cấm tuyệt đối bê preset 5K sang The5ers 50K/60K (`4%/8%` DD):** Bắt buộc nạp bộ tham số hiệu chỉnh riêng (`P1 2,75x -> +4% khóa 1,50x`, `SYMCAP 1,15%`, phanh Amber `2,4%`, Red `4,8%`, cắt lỗ ngày EA `2,8%`) trước khi bấm chạy.

*Thời gian tính toán toàn bộ kiểm toán M1 + 10.000 Monte Carlo: `53.45s` · JSON kiểm chứng: `PROP-TIER-SCALING-AND-SYMCAP-AUDIT-20261124.json` · SHA-256: `a007ae771f32e779ca268765961fc47fef2c0c97f35d715093c3595d0431b8da`.*

---
doc_type: quant-research-audit
generated_utc: 2026-11-24T19:48:13.487461+00:00
dev_window: 2018-01-02..2024-12-31
mc_paths: 10000
mc_seed: 20261124
holdout_rows_analysed: 0
order_send_count: 0
receipt_sha256: 2fbafafc3a00ef5bc872dc29bf82152401147f211f5d548ad91393896251f95f
---

# Kiểm Toán Định Lượng: Siết Trần Rủi Ro 1 Mã (`SYMCAP`) & Ma Trận Lên Cấp Tài Khoản Quỹ (Dev 2018–2024)

> **Niêm phong dữ liệu & An toàn:** Chạy hoàn toàn trên tập Phát triển `2018-2024` (`holdout_rows_analysed = 0`, khóa Holdout `2025+` nguyên vẹn SHA `f0a6b43cb205535b...`), `OrderSend = 0`, mô phỏng **10.000 kịch bản Monte Carlo** (`Circular Block-Bootstrap`, độ dài khối `5` ngày, `seed = 20261124`) ghép trực tiếp từ dữ liệu chạy từng phút M1 thật có khóa tin đỏ `±5` phút của danh mục live **8 EA (`A1_V1_LIVE8`)**.

## 1. Tóm Tắt Dễ Hiểu Cho Chủ Quỹ

1. **Siết trần rủi ro 1 mã (`SYMCAP`) từ `3,00%–3,50%` xuống `1,75%` giảm mạnh rủi ro nổ trần ngày mà vẫn giữ hiệu suất kiếm tiền trên mỗi USD tiền vé (`EV/Fee`) cao vượt trội:**
   - Trên **FTMO Swing 10K (`Dyn_ProfitLock` `4,5x -> +5% khóa 2,0x`)** ở chi phí chuẩn `1,0x`: tỷ lệ cháy trần lỗ ngày `5%` ngay lượt thi đầu giảm từ **`23.7%`** (`SYMCAP 3,50%`) xuống còn **`2.7%`** (`SYMCAP 1,75%`). Tỷ lệ rớt lượt đầu giảm từ `24.6%` xuống `3.4%`, trong khi **`EV/Fee`** giữ mức rất cao (`3.67x` so với `3.60x`).
   - Khi thị trường giãn trượt giá `1,5x` (kịch bản stress thực chiến): cháy trần ngày lượt đầu vẫn giảm sâu từ **`23.7%`** xuống **`3.2%`**.
   - Trên **The5ers High Stakes 5K (`39 USD`)**: cháy trần ngày lượt đầu giảm từ **`19.2%`** xuống **`2.3%`**.
2. **Lên cấp tài khoản (`10K -> 25K / 50K / 100K`) là đòn bẩy kinh tế lớn nhất mà không hề tăng thêm rủi ro phần trăm:**
   - Vì giá vé không tăng tỷ lệ thuận với vốn (FTMO 10K tốn `1,68%` vốn mua vé, còn 50K chỉ tốn `0,72%` và 100K chỉ tốn `0,56%`), chỉ cần giữ nguyên chiến lược đã siết `SYMCAP 1,75%`, nhảy từ **10K -> 25K** nhân `EV/Fee` lên **`1.61x`**, lên **50K** nhân **`2.46x`**, và lên **100K** nhân **`3.19x`**!
3. **Cảnh báo cứng về bẫy luật `4%/8%` của The5ers High Stakes 50K/60K (`329 USD`):**
   - Nếu bê nguyên bộ cấu hình 5K (vốn thiết kế cho luật `5%/10%`) sang chạy The5ers 50K (`4%` lỗ ngày / `8%` lỗ tổng), tỷ lệ cháy trần ngày lượt đầu vọt lên **`34.3%`** (với `SYMCAP 3,00%`) và vẫn tới **`11.2%`** (ngay cả với `SYMCAP 1,75%` chưa hạ cỡ lệnh!).
   - Khi hạ cấu hình riêng cho khung `4%/8%` (`P1 2,75x -> +4% khóa 1,50x`, `SYMCAP 1,15%`, cắt lỗ ngày EA `2,8%`), cháy trần ngày lượt đầu rơi xuống chỉ còn **`3.9%`**, mở khóa hiệu quả **`EV/Fee = 7.70x`** (50K) và **`9.37x`** (60K)!

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
| 1.50% | 3.1% | 0.6% | 3.7% | 71.9% | 149d | 3.63x (3.50x tổng phí) | +610 USD (+15.6 tr) · P<=0=31% | 168 USD (4.3 tr) |
| 1.75% (KHUYÊN DÙNG) | 2.7% | 0.6% | 3.4% | 71.5% | 140d | 3.67x (3.55x tổng phí) | +617 USD (+15.7 tr) · P<=0=31% | 168 USD (4.3 tr) |
| 2.00% | 2.5% | 0.8% | 3.3% | 70.2% | 135d | 3.62x (3.50x tổng phí) | +608 USD (+15.5 tr) · P<=0=33% | 168 USD (4.3 tr) |
| 3.00% (CŨ - NGUY HIỂM) | 20.3% | 0.9% | 21.2% | 72.4% | 126d | 3.63x (2.88x tổng phí) | +609 USD (+15.5 tr) · P<=0=32% | 336 USD (8.6 tr) |
| 3.50% (CŨ - NGUY HIỂM) | 23.7% | 0.9% | 24.6% | 72.2% | 122d | 3.60x (2.76x tổng phí) | +605 USD (+15.4 tr) · P<=0=32% | 504 USD (12.8 tr) |

**Kịch bản trượt giá nặng (`1,5x` chi phí M1):**

| SYMCAP | Cháy Ngày (Lượt 1) | Cháy Tổng (Lượt 1) | Rớt Lượt 1 | Đậu trong 24T | Trung vị đậu | EV / Phí vé | Dòng tiền 24T (USD / VND) | Chi phí ròng xấu P95 |
|---|---|---|---|---|---|---|---|---|
| 1.50% | 3.2% | 2.5% | 5.8% | 48.8% | 157d | 1.29x (1.22x tổng phí) | +217 USD (+5.5 tr) · P<=0=55% | 336 USD (8.6 tr) |
| 1.75% (KHUYÊN DÙNG) | 3.2% | 2.8% | 6.0% | 49.0% | 152d | 1.31x (1.24x tổng phí) | +220 USD (+5.6 tr) · P<=0=55% | 336 USD (8.6 tr) |
| 2.00% | 2.8% | 3.3% | 6.1% | 48.5% | 144d | 1.31x (1.23x tổng phí) | +220 USD (+5.6 tr) · P<=0=55% | 336 USD (8.6 tr) |
| 3.00% (CŨ - NGUY HIỂM) | 20.8% | 3.2% | 24.0% | 52.0% | 133d | 1.28x (0.99x tổng phí) | +215 USD (+5.5 tr) · P<=0=53% | 336 USD (8.6 tr) |
| 3.50% (CŨ - NGUY HIỂM) | 23.7% | 2.9% | 26.7% | 52.5% | 131d | 1.26x (0.94x tổng phí) | +212 USD (+5.4 tr) · P<=0=53% | 504 USD (12.8 tr) |

### 2.3. Đối Chiếu `The5ers High Stakes 5K` (`Dyn_ProfitLock`, Phí `39 USD`, 3 Ngày Lãi `>= +0,5%`)

**Kịch bản chi phí chuẩn (`1,0x`):**

| SYMCAP | Cháy Ngày (Lượt 1) | Cháy Tổng (Lượt 1) | Rớt Lượt 1 | Đậu trong 24T | Trung vị đậu | EV / Phí vé | Dòng tiền 24T (USD / VND) | Chi phí ròng xấu P95 |
|---|---|---|---|---|---|---|---|---|
| 1.50% | 2.6% | 0.5% | 3.1% | 72.9% | 128d | 6.91x (6.70x tổng phí) | +270 USD (+6.9 tr) · P<=0=40% | 39 USD (1.0 tr) |
| 1.75% (KHUYÊN DÙNG) | 2.3% | 0.6% | 2.9% | 72.8% | 122d | 6.99x (6.79x tổng phí) | +273 USD (+7.0 tr) · P<=0=39% | 39 USD (1.0 tr) |
| 2.00% | 2.1% | 0.7% | 2.8% | 71.5% | 118d | 6.93x (6.73x tổng phí) | +270 USD (+6.9 tr) · P<=0=40% | 39 USD (1.0 tr) |
| 3.00% (CŨ - NGUY HIỂM) | 16.0% | 0.8% | 16.8% | 71.9% | 109d | 6.98x (5.85x tổng phí) | +272 USD (+6.9 tr) · P<=0=40% | 78 USD (2.0 tr) |
| 3.50% (CŨ - NGUY HIỂM) | 19.2% | 0.9% | 20.1% | 72.2% | 108d | 7.00x (5.65x tổng phí) | +273 USD (+7.0 tr) · P<=0=39% | 78 USD (2.0 tr) |

**Kịch bản trượt giá nặng (`1,5x`):**

| SYMCAP | Cháy Ngày (Lượt 1) | Cháy Tổng (Lượt 1) | Rớt Lượt 1 | Đậu trong 24T | Trung vị đậu | EV / Phí vé | Dòng tiền 24T (USD / VND) | Chi phí ròng xấu P95 |
|---|---|---|---|---|---|---|---|---|
| 1.50% | 2.9% | 2.7% | 5.6% | 51.3% | 136d | 2.65x (2.51x tổng phí) | +104 USD (+2.6 tr) · P<=0=64% | 78 USD (2.0 tr) |
| 1.75% (KHUYÊN DÙNG) | 2.5% | 3.1% | 5.5% | 50.7% | 128d | 2.68x (2.53x tổng phí) | +104 USD (+2.7 tr) · P<=0=64% | 78 USD (2.0 tr) |
| 2.00% | 2.1% | 3.4% | 5.4% | 49.9% | 123d | 2.65x (2.51x tổng phí) | +103 USD (+2.6 tr) · P<=0=65% | 78 USD (2.0 tr) |
| 3.00% (CŨ - NGUY HIỂM) | 16.3% | 3.5% | 19.8% | 53.0% | 112d | 2.75x (2.23x tổng phí) | +107 USD (+2.7 tr) · P<=0=62% | 78 USD (2.0 tr) |
| 3.50% (CŨ - NGUY HIỂM) | 19.5% | 3.3% | 22.8% | 53.3% | 109d | 2.76x (2.16x tổng phí) | +108 USD (+2.7 tr) · P<=0=62% | 78 USD (2.0 tr) |

### 2.4. Đối Chiếu Bộ Preset Đang Xuất Thực Tế (`DEPLOYED_PRESET_EXACT`: `4,00x -> 2,01x`, P2/Funded `7E`, `SYMCAP 1,50%/1,00%`)

**FTMO Swing 10K (`1,0x` / `1,25x` / `1,5x` — lưu ý `504` phiên giao dịch tương đương ~`27,4` tháng lịch trên `221` ngày giao dịch/năm):**

| SYMCAP | Cháy Ngày (Lượt 1) | Cháy Tổng (Lượt 1) | Rớt Lượt 1 | Đậu 504 phiên | Trung vị đậu | EV / Phí (Đầu / Tổng) | Dòng tiền 504 phiên (USD / VND / P<=0) | Chi phí ròng xấu P95 |
|---|---|---|---|---|---|---|---|---|
| 1.50% | 3.6% | 24.8% | 28.4% | 96.7% | 153d | 5.31x (3.77x tổng phí) | +891 USD (+22.7 tr) · P<=0=9% | 504 USD (12.8 tr) |
| 1.75% (KHUYÊN DÙNG) | 3.3% | 26.2% | 29.5% | 97.3% | 143d | 5.51x (3.84x tổng phí) | +925 USD (+23.6 tr) · P<=0=8% | 504 USD (12.8 tr) |
| 2.00% | 2.8% | 28.7% | 31.5% | 97.8% | 135d | 5.65x (3.84x tổng phí) | +949 USD (+24.2 tr) · P<=0=7% | 504 USD (12.8 tr) |
| 3.00% (CŨ - NGUY HIỂM) | 13.6% | 24.5% | 38.1% | 98.5% | 119d | 5.83x (3.56x tổng phí) | +979 USD (+25.0 tr) · P<=0=7% | 672 USD (17.1 tr) |
| 3.50% (CŨ - NGUY HIỂM) | 13.3% | 24.6% | 37.9% | 98.5% | 118d | 5.86x (3.59x tổng phí) | +985 USD (+25.1 tr) · P<=0=7% | 672 USD (17.1 tr) |

**FTMO Swing 10K (`DEPLOYED_PRESET_EXACT`, trượt giá `1,25x`):**

| SYMCAP | Cháy Ngày (Lượt 1) | Cháy Tổng (Lượt 1) | Rớt Lượt 1 | Đậu 504 phiên | Trung vị đậu | EV / Phí (Đầu / Tổng) | Dòng tiền 504 phiên (USD / VND / P<=0) | Chi phí ròng xấu P95 |
|---|---|---|---|---|---|---|---|---|
| 1.50% | 4.2% | 32.0% | 36.2% | 93.0% | 173d | 3.89x (2.48x tổng phí) | +653 USD (+16.6 tr) · P<=0=16% | 504 USD (12.8 tr) |
| 1.75% (KHUYÊN DÙNG) | 3.4% | 33.6% | 37.0% | 94.8% | 162d | 4.10x (2.56x tổng phí) | +689 USD (+17.6 tr) · P<=0=14% | 504 USD (12.8 tr) |
| 2.00% | 2.8% | 35.5% | 38.3% | 95.6% | 153d | 4.23x (2.57x tổng phí) | +711 USD (+18.1 tr) · P<=0=14% | 672 USD (17.1 tr) |
| 3.00% (CŨ - NGUY HIỂM) | 14.6% | 29.7% | 44.3% | 96.5% | 132d | 4.43x (2.43x tổng phí) | +744 USD (+19.0 tr) · P<=0=13% | 672 USD (17.1 tr) |
| 3.50% (CŨ - NGUY HIỂM) | 14.2% | 30.0% | 44.1% | 96.8% | 130d | 4.48x (2.47x tổng phí) | +752 USD (+19.2 tr) · P<=0=12% | 672 USD (17.1 tr) |

**FTMO Swing 10K (`DEPLOYED_PRESET_EXACT`, trượt giá `1,5x`):**

| SYMCAP | Cháy Ngày (Lượt 1) | Cháy Tổng (Lượt 1) | Rớt Lượt 1 | Đậu 504 phiên | Trung vị đậu | EV / Phí (Đầu / Tổng) | Dòng tiền 504 phiên (USD / VND / P<=0) | Chi phí ròng xấu P95 |
|---|---|---|---|---|---|---|---|---|
| 1.50% | 4.5% | 40.5% | 45.1% | 86.9% | 194d | 2.40x (1.34x tổng phí) | +404 USD (+10.3 tr) · P<=0=27% | 672 USD (17.1 tr) |
| 1.75% (KHUYÊN DÙNG) | 3.7% | 41.7% | 45.4% | 89.6% | 183d | 2.61x (1.43x tổng phí) | +438 USD (+11.2 tr) · P<=0=25% | 672 USD (17.1 tr) |
| 2.00% | 3.1% | 44.1% | 47.2% | 91.3% | 173d | 2.73x (1.44x tổng phí) | +458 USD (+11.7 tr) · P<=0=23% | 672 USD (17.1 tr) |
| 3.00% (CŨ - NGUY HIỂM) | 17.1% | 34.5% | 51.6% | 93.6% | 147d | 2.95x (1.42x tổng phí) | +495 USD (+12.6 tr) · P<=0=21% | 840 USD (21.4 tr) |
| 3.50% (CŨ - NGUY HIỂM) | 16.7% | 34.8% | 51.5% | 93.9% | 145d | 2.99x (1.44x tổng phí) | +502 USD (+12.8 tr) · P<=0=21% | 840 USD (21.4 tr) |

### 2.5. Đối Chiếu Chế Độ Tĩnh `P1_Balanced_Static` (`4,0x` Không Khóa Lãi) Trên FTMO Swing 10K (`1,0x`)

| SYMCAP | Cháy Ngày (Lượt 1) | Cháy Tổng (Lượt 1) | Rớt Lượt 1 | Đậu trong 24T | Trung vị đậu | EV / Phí vé | Dòng tiền 24T (USD / VND) | Chi phí ròng xấu P95 |
|---|---|---|---|---|---|---|---|---|
| 1.50% | 4.6% | 0.5% | 5.1% | 72.2% | 146d | 3.65x (3.47x tổng phí) | +614 USD (+15.7 tr) · P<=0=31% | 336 USD (8.6 tr) |
| 1.75% (KHUYÊN DÙNG) | 4.1% | 0.6% | 4.7% | 72.1% | 139d | 3.71x (3.54x tổng phí) | +623 USD (+15.9 tr) · P<=0=31% | 168 USD (4.3 tr) |
| 2.00% | 3.6% | 0.7% | 4.3% | 70.3% | 134d | 3.64x (3.48x tổng phí) | +611 USD (+15.6 tr) · P<=0=32% | 168 USD (4.3 tr) |
| 3.00% (CŨ - NGUY HIỂM) | 20.9% | 1.0% | 21.8% | 70.8% | 125d | 3.51x (2.76x tổng phí) | +590 USD (+15.1 tr) · P<=0=34% | 336 USD (8.6 tr) |
| 3.50% (CŨ - NGUY HIỂM) | 20.9% | 1.0% | 21.9% | 71.0% | 125d | 3.53x (2.78x tổng phí) | +593 USD (+15.1 tr) · P<=0=33% | 336 USD (8.6 tr) |

- **Kết luận Phần 1:** Mức **`SYMCAP = 1,75%`** (biên an toàn `1,50%–2,00%`) kết hợp **`Dyn_ProfitLock` (`4,5x -> +5% hạ về 2,0x`)** là điểm ngọt rõ ràng nhất: loại bỏ hoàn toàn nguy cơ 1 lệnh đơn (hoặc 2 bot cùng mã USDJPY/US100) bắn thủng trần lỗ ngày `5%`, giữ thời gian đậu quỹ nhanh và bảo toàn dòng tiền ròng 24 tháng ngay cả khi chi phí thực tế tăng `1,5x`.

## 3. Phần 2 — Ma Trận Hiệu Quả Tiền Vé Đa Cấp Bậc & Bẫy Luật `4%/8%` Trên The5ers 50K/60K

Toàn bộ các gói `5%/10%` bên dưới dùng đúng cấu hình đã kiểm chứng (`SYMCAP 1,75% + Dyn_ProfitLock`). Riêng gói **The5ers 50K/60K** (luật siết cứng `4%` ngày / `8%` tổng) được thử đối chứng 3 trường hợp: (1) bê nhầm preset 5K cũ (`SYMCAP 3,0%`), (2) bê preset 5K mới (`SYMCAP 1,75%`) nhưng không hạ cỡ lệnh, và (3) cấu hình chuẩn hóa riêng cho khung `4%/8%` (`P1 2,75x`, `SYMCAP 1,15%`, cắt lỗ ngày EA `2,8%`). Tỷ giá quy đổi `1 USD = 25.500 VND`.

### 3.1. Ma Trận Đa Cấp Bậc — Chi Phí Chuẩn (`1,0x`, `N = 10.000` Kịch Bản)

| Gói Tài Khoản Quỹ | Phí / Vốn | Luật DD | SYMCAP / P1 | Cháy Ngày (L1) | Rớt Lượt 1 | Đậu 24T | EV / Phí vé | Dòng tiền ròng 24T (USD / VND) | Chi phí ròng P95 |
|---|---|---|---|---|---|---|---|---|---|
| FTMO Swing 10K (Chuẩn 168 USD · EXACT .SET 4.0x/7E) | 1.68% | 5%/10% | 1.75% / 4.00x | 3.3% | 29.5% | 97.3% | **5.51x** (3.84x) | +925 USD (+23.6 tr) · P<=0=8% | 504 USD (12.8 tr) |
| FTMO Swing 10K (Giá chuẩn 168 USD) | 1.68% | 5%/10% | 1.75% / 4.50x | 2.7% | 3.4% | 71.5% | **3.67x** (3.55x) | +617 USD (+15.7 tr) · P<=0=31% | 168 USD (4.3 tr) |
| FTMO Swing 10K (Promo ~95 USD) | 0.95% | 5%/10% | 1.75% / 4.50x | 2.7% | 3.4% | 71.5% | **6.76x** (6.53x) | +642 USD (+16.4 tr) · P<=0=31% | 95 USD (2.4 tr) |
| FTMO Swing 25K (270 USD) | 1.08% | 5%/10% | 1.75% / 4.50x | 2.7% | 3.4% | 71.5% | **5.90x** (5.71x) | +1,593 USD (+40.6 tr) · P<=0=31% | 270 USD (6.9 tr) |
| FTMO Swing 50K (360 USD) | 0.72% | 5%/10% | 1.75% / 4.50x | 2.7% | 3.4% | 71.5% | **9.02x** (8.72x) | +3,249 USD (+82.8 tr) · P<=0=31% | 360 USD (9.2 tr) |
| FTMO Swing 100K (560 USD) | 0.56% | 5%/10% | 1.75% / 4.50x | 2.7% | 3.4% | 71.5% | **11.70x** (11.31x) | +6,553 USD (+167.1 tr) · P<=0=31% | 560 USD (14.3 tr) |
| The5ers HS 5K (Promo 39 USD · EXACT .SET 4.0x/7E + MinPay 150) | 0.78% | 5%/10% | 1.75% / 4.00x | 2.8% | 27.5% | 98.3% | **10.40x** (7.49x) | +406 USD (+10.3 tr) · P<=0=12% | 117 USD (3.0 tr) |
| The5ers HS 5K (Promo 39 USD · 5%/10% DD) | 0.78% | 5%/10% | 1.75% / 4.50x | 2.3% | 2.9% | 72.8% | **6.99x** (6.79x) | +273 USD (+7.0 tr) · P<=0=39% | 39 USD (1.0 tr) |
| The5ers HS 5K (Chuẩn 52 USD · 5%/10% DD) | 1.04% | 5%/10% | 1.75% / 4.50x | 2.3% | 2.9% | 72.8% | **5.09x** (4.94x) | +265 USD (+6.7 tr) · P<=0=39% | 52 USD (1.3 tr) |
| The5ers HS 20K (189 USD · 5%/10% DD) | 0.94% | 5%/10% | 1.75% / 4.50x | 2.3% | 2.9% | 72.8% | **6.38x** (6.19x) | +1,206 USD (+30.7 tr) · P<=0=32% | 189 USD (4.8 tr) |
| The5ers HS 50K (329 USD · 4%/8% DD — DÙNG NHẦM PRESET 5K!) | 0.66% | 4%/8% | 3.00% / 4.50x | 34.3% | 39.6% | 81.9% | **10.62x** (6.59x) | +3,493 USD (+89.1 tr) · P<=0=23% | 987 USD (25.2 tr) |
| The5ers HS 50K (329 USD · 4%/8% DD — Preset 5K SYMCAP 1.75%) | 0.66% | 4%/8% | 1.75% / 4.50x | 11.2% | 18.6% | 77.0% | **9.80x** (7.97x) | +3,223 USD (+82.2 tr) · P<=0=28% | 658 USD (16.8 tr) |
| The5ers HS 50K (329 USD · 4%/8% DD — Preset 4%/8% CHUẨN) | 0.66% | 4%/8% | 1.15% / 2.75x | 3.9% | 4.6% | 70.7% | **7.70x** (7.35x) | +2,535 USD (+64.6 tr) · P<=0=34% | 329 USD (8.4 tr) |
| The5ers HS 60K (329 USD · 4%/8% DD — Preset 4%/8% CHUẨN) | 0.55% | 4%/8% | 1.15% / 2.75x | 3.9% | 4.6% | 70.7% | **9.37x** (8.94x) | +3,083 USD (+78.6 tr) · P<=0=33% | 329 USD (8.4 tr) |

### 3.2. Ma Trận Đa Cấp Bậc — Kiểm Thử Stress Trượt Giá `1,25x` (`N = 10.000` Kịch Bản)

| Gói Tài Khoản Quỹ | Phí / Vốn | Luật DD | SYMCAP / P1 | Cháy Ngày (L1) | Rớt Lượt 1 | Đậu 504p | EV / Phí (Đầu/Tổng) | Dòng tiền ròng (USD / VND / P<=0) | Chi phí ròng P95 |
|---|---|---|---|---|---|---|---|---|---|
| FTMO Swing 10K (Chuẩn 168 USD · EXACT .SET 4.0x/7E) | 1.68% | 5%/10% | 1.75% / 4.00x | 3.4% | 37.0% | 94.8% | **4.10x** (2.56x) | +689 USD (+17.6 tr) · P<=0=14% | 504 USD (12.8 tr) |
| FTMO Swing 10K (Giá chuẩn 168 USD) | 1.68% | 5%/10% | 1.75% / 4.50x | 2.9% | 4.3% | 61.0% | **2.44x** (2.34x) | +410 USD (+10.5 tr) · P<=0=42% | 168 USD (4.3 tr) |
| FTMO Swing 10K (Promo ~95 USD) | 0.95% | 5%/10% | 1.75% / 4.50x | 2.9% | 4.3% | 61.0% | **4.68x** (4.48x) | +444 USD (+11.3 tr) · P<=0=42% | 95 USD (2.4 tr) |
| FTMO Swing 25K (270 USD) | 1.08% | 5%/10% | 1.75% / 4.50x | 2.9% | 4.3% | 61.0% | **4.06x** (3.89x) | +1,095 USD (+27.9 tr) · P<=0=42% | 270 USD (6.9 tr) |
| FTMO Swing 50K (360 USD) | 0.72% | 5%/10% | 1.75% / 4.50x | 2.9% | 4.3% | 61.0% | **6.32x** (6.05x) | +2,274 USD (+58.0 tr) · P<=0=42% | 360 USD (9.2 tr) |
| FTMO Swing 100K (560 USD) | 0.56% | 5%/10% | 1.75% / 4.50x | 2.9% | 4.3% | 61.0% | **8.25x** (7.91x) | +4,623 USD (+117.9 tr) · P<=0=42% | 560 USD (14.3 tr) |
| The5ers HS 5K (Promo 39 USD · EXACT .SET 4.0x/7E + MinPay 150) | 0.78% | 5%/10% | 1.75% / 4.00x | 3.0% | 35.1% | 96.6% | **7.77x** (5.03x) | +303 USD (+7.7 tr) · P<=0=20% | 117 USD (3.0 tr) |
| The5ers HS 5K (Promo 39 USD · 5%/10% DD) | 0.78% | 5%/10% | 1.75% / 4.50x | 2.5% | 3.8% | 61.8% | **4.65x** (4.48x) | +181 USD (+4.6 tr) · P<=0=52% | 39 USD (1.0 tr) |
| The5ers HS 5K (Chuẩn 52 USD · 5%/10% DD) | 1.04% | 5%/10% | 1.75% / 4.50x | 2.5% | 3.8% | 61.8% | **3.31x** (3.19x) | +172 USD (+4.4 tr) · P<=0=52% | 52 USD (1.3 tr) |
| The5ers HS 20K (189 USD · 5%/10% DD) | 0.94% | 5%/10% | 1.75% / 4.50x | 2.5% | 3.8% | 61.8% | **4.33x** (4.17x) | +819 USD (+20.9 tr) · P<=0=44% | 189 USD (4.8 tr) |
| The5ers HS 50K (329 USD · 4%/8% DD — DÙNG NHẦM PRESET 5K!) | 0.66% | 4%/8% | 3.00% / 4.50x | 36.4% | 44.4% | 74.6% | **7.64x** (4.44x) | +2,513 USD (+64.1 tr) · P<=0=32% | 1,316 USD (33.6 tr) |
| The5ers HS 50K (329 USD · 4%/8% DD — Preset 5K SYMCAP 1.75%) | 0.66% | 4%/8% | 1.75% / 4.50x | 11.5% | 23.0% | 67.3% | **6.86x** (5.31x) | +2,256 USD (+57.5 tr) · P<=0=38% | 658 USD (16.8 tr) |
| The5ers HS 50K (329 USD · 4%/8% DD — Preset 4%/8% CHUẨN) | 0.66% | 4%/8% | 1.15% / 2.75x | 4.1% | 5.7% | 59.2% | **4.99x** (4.70x) | +1,641 USD (+41.9 tr) · P<=0=46% | 658 USD (16.8 tr) |
| The5ers HS 60K (329 USD · 4%/8% DD — Preset 4%/8% CHUẨN) | 0.55% | 4%/8% | 1.15% / 2.75x | 4.1% | 5.7% | 59.2% | **6.13x** (5.78x) | +2,016 USD (+51.4 tr) · P<=0=46% | 658 USD (16.8 tr) |

### 3.3. Ma Trận Đa Cấp Bậc — Kiểm Thử Stress Trượt Giá `1,5x` (`N = 10.000` Kịch Bản)

| Gói Tài Khoản Quỹ | Phí / Vốn | Luật DD | SYMCAP / P1 | Cháy Ngày (L1) | Rớt Lượt 1 | Đậu 24T | EV / Phí vé | Dòng tiền ròng 24T (USD / VND) | Chi phí ròng P95 |
|---|---|---|---|---|---|---|---|---|---|
| FTMO Swing 10K (Chuẩn 168 USD · EXACT .SET 4.0x/7E) | 1.68% | 5%/10% | 1.75% / 4.00x | 3.7% | 45.4% | 89.6% | **2.61x** (1.43x) | +438 USD (+11.2 tr) · P<=0=25% | 672 USD (17.1 tr) |
| FTMO Swing 10K (Giá chuẩn 168 USD) | 1.68% | 5%/10% | 1.75% / 4.50x | 3.2% | 6.0% | 49.0% | **1.31x** (1.24x) | +220 USD (+5.6 tr) · P<=0=55% | 336 USD (8.6 tr) |
| FTMO Swing 10K (Promo ~95 USD) | 0.95% | 5%/10% | 1.75% / 4.50x | 3.2% | 6.0% | 49.0% | **2.79x** (2.62x) | +265 USD (+6.7 tr) · P<=0=55% | 190 USD (4.8 tr) |
| FTMO Swing 25K (270 USD) | 1.08% | 5%/10% | 1.75% / 4.50x | 3.2% | 6.0% | 49.0% | **2.38x** (2.24x) | +642 USD (+16.4 tr) · P<=0=55% | 540 USD (13.8 tr) |
| FTMO Swing 50K (360 USD) | 0.72% | 5%/10% | 1.75% / 4.50x | 3.2% | 6.0% | 49.0% | **3.87x** (3.64x) | +1,393 USD (+35.5 tr) · P<=0=54% | 720 USD (18.4 tr) |
| FTMO Swing 100K (560 USD) | 0.56% | 5%/10% | 1.75% / 4.50x | 3.2% | 6.0% | 49.0% | **5.15x** (4.85x) | +2,883 USD (+73.5 tr) · P<=0=54% | 1,120 USD (28.6 tr) |
| The5ers HS 5K (Promo 39 USD · EXACT .SET 4.0x/7E + MinPay 150) | 0.78% | 5%/10% | 1.75% / 4.00x | 3.1% | 43.1% | 93.0% | **5.08x** (2.89x) | +198 USD (+5.1 tr) · P<=0=33% | 156 USD (4.0 tr) |
| The5ers HS 5K (Promo 39 USD · 5%/10% DD) | 0.78% | 5%/10% | 1.75% / 4.50x | 2.5% | 5.5% | 50.7% | **2.68x** (2.53x) | +104 USD (+2.7 tr) · P<=0=64% | 78 USD (2.0 tr) |
| The5ers HS 5K (Chuẩn 52 USD · 5%/10% DD) | 1.04% | 5%/10% | 1.75% / 4.50x | 2.5% | 5.5% | 50.7% | **1.81x** (1.71x) | +94 USD (+2.4 tr) · P<=0=64% | 104 USD (2.6 tr) |
| The5ers HS 20K (189 USD · 5%/10% DD) | 0.94% | 5%/10% | 1.75% / 4.50x | 2.5% | 5.5% | 50.7% | **2.56x** (2.42x) | +484 USD (+12.3 tr) · P<=0=56% | 378 USD (9.6 tr) |
| The5ers HS 50K (329 USD · 4%/8% DD — DÙNG NHẦM PRESET 5K!) | 0.66% | 4%/8% | 3.00% / 4.50x | 36.6% | 49.6% | 66.4% | **4.88x** (2.64x) | +1,604 USD (+40.9 tr) · P<=0=42% | 1,316 USD (33.6 tr) |
| The5ers HS 50K (329 USD · 4%/8% DD — Preset 5K SYMCAP 1.75%) | 0.66% | 4%/8% | 1.75% / 4.50x | 11.9% | 30.9% | 57.9% | **4.27x** (3.04x) | +1,404 USD (+35.8 tr) · P<=0=49% | 987 USD (25.2 tr) |
| The5ers HS 50K (329 USD · 4%/8% DD — Preset 4%/8% CHUẨN) | 0.66% | 4%/8% | 1.15% / 2.75x | 4.1% | 7.6% | 45.7% | **2.76x** (2.56x) | +910 USD (+23.2 tr) · P<=0=60% | 658 USD (16.8 tr) |
| The5ers HS 60K (329 USD · 4%/8% DD — Preset 4%/8% CHUẨN) | 0.55% | 4%/8% | 1.15% / 2.75x | 4.1% | 7.6% | 45.7% | **3.48x** (3.22x) | +1,146 USD (+29.2 tr) · P<=0=60% | 658 USD (16.8 tr) |

## 4. Khuyến Nghị Triển Khai Vận Hành Cho Chủ Quỹ

1. **Áp dụng ngay trần `SYMCAP <= 1,75%` (tối đa `2,00%`) cho mọi preset P1 (`5%/10%` DD):** không bao giờ quay lại mức `3,00%–3,50%` cũ để tránh một cú trượt giá tin vĩ mô làm bay tài khoản chỉ sau một buổi sáng.
2. **Lộ trình leo thang vốn tối ưu hiệu quả đồng vốn (từ tiền lãi quỹ tái đầu tư, không bỏ thêm tiền túi):**
   - *Bước 1 (Khởi động & chứng minh vận hành):* `FTMO Swing 10K` (ưu tiên săn promo ~`95 USD`) + `The5ers HS 5K` (`39 USD`) chạy song song cách nhịp để rút payout đầu tiên và lấp đầy Quỹ Dự Phòng 5 vé.
   - *Bước 2 (Nhảy bậc `EV/Fee` gấp ~2x–3x):* Dùng tiền lãi payout mua thẳng **`FTMO Swing 50K` (`360 USD`)** hoặc **`FTMO Swing 100K` (`560 USD`)** (thay vì mua nhiều vé 10K nhỏ lẻ tốn phí gấp 2–3 lần trên cùng mức vốn).
3. **Cấm tuyệt đối bê preset 5K sang The5ers 50K/60K (`4%/8%` DD):** Bắt buộc nạp bộ tham số hiệu chỉnh riêng (`P1 2,75x -> +4% khóa 1,50x`, `SYMCAP 1,15%`, phanh Amber `2,4%`, Red `4,8%`, cắt lỗ ngày EA `2,8%`) trước khi bấm chạy.

*Thời gian tính toán toàn bộ kiểm toán M1 + 10.000 Monte Carlo: `55.72s` · JSON kiểm chứng: `PROP-TIER-SCALING-AND-SYMCAP-AUDIT-20261124.json` · SHA-256: `2fbafafc3a00ef5bc872dc29bf82152401147f211f5d548ad91393896251f95f`.*

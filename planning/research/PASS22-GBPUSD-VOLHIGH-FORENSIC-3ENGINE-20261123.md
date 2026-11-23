# Pass 22 · Pháp y M1 `WB_EXP_80_VOL_HIGH GBPUSD` & Đột Phá Danh Mục 3 Động Cơ (Prague Reset)

- **Protocol khóa trước thực nghiệm:** [PASS22-GBPUSD-VOLHIGH-FORENSIC-3ENGINE-PROTOCOL-20261123.md](PASS22-GBPUSD-VOLHIGH-FORENSIC-3ENGINE-PROTOCOL-20261123.md) (commit `d9b70d6`)
- **An toàn & kiểm thử:** Development UTC `2018–2024`, **`holdout_rows = 0`**, `network_calls = 0`, `OrderSend = 0`, `quant_test_suite` **`1537/1537 PASS (0 skip, 17.12s)`**.
- **Phán quyết tổng hợp:** **`GBPUSD_VOLHIGH_PROMOTED_AS_ORTHOGONAL_ENGINE3`** · Cấu hình 3 động cơ vượt toàn bộ rào kiểm định trên cả 3 cỡ sổ (`10k`, `25k`, `50k`): `PORT3E_075_GBP025, PORT3E_075_GBP050, PORT3E_075_GBP075, PORT3E_INVDD_125`.
- **Mẫu `.mq5` trắng đã xuất (`InpDryRunLogOnly = true`, `0` cờ đỏ):** `tooling/ai-engines/exports/Naqex_WB_EXP080_VOLHIGH_GBPUSD.mq5`.

---

## 1. Nhánh 1A · Kiểm chứng 3 bậc phí thực chiến (`Base` · `Stress +0,50 pip` · `Stress +1,00 pip`)

| Bậc phí (`WB_EXP_80_VOL_HIGH GBPUSD`, `swap = 0`) | `strict` (n · Net R · DD R) | `extended` (n · Net R · DD R · UW) | `all_dev` (n · Net R · Năm+ · DD R · UW) |
| --- | --- | --- | --- |
| **`M1_Real_Base`** | `158` · `+17.84R` · `4.5R` | `171` · `+16.64R` · `4.7R` · `17.4m` | `198` · **`+15.54R`** · `5/7` · `6.3R` · `26.8m` |
| **`M1_Real_Stress_05`** | `158` · `+16.74R` · `4.5R` | `171` · `+15.47R` · `4.8R` · `17.4m` | `198` · **`+14.19R`** · `5/7` · `6.4R` · `26.9m` |
| **`M1_Real_Stress_10`** | `158` · `+15.65R` · `4.6R` | `171` · `+14.30R` · `4.9R` · `26.0m` | `198` · **`+12.86R`** · `4/7` · `6.6R` · `26.9m` |

## 2. Nhánh 1B & 1C · Mặt phẳng độ bền tham số (`21` ô) · Phân tách chiều & Sát hạch sự kiện cực đoan

- **Mặt phẳng `trig × sl_atr` (`vol_mult = 1,10`):** **`8 / 9` ô** dương đồng thời ở cả Cụm A (`2018–2020`) và Cụm B (`2021–2024`).
- **Mặt phẳng `trig × vol_mult` (`sl_atr = 0,75`):** **`3 / 12` ô** dương đồng thời ở cả Cụm A & B *(ghi nhận trung thực: ngưỡng lọc chế độ biến động `vol_mult` nhạy hơn `sl_atr` — cần giữ đúng cửa chế độ biến động mở rộng)*.
- **Cân bằng 2 chiều (`all_dev`, Stress `+0,50 pip`):** **`BUY` (`n=95`, WR `52.6%`): `+4.72R` (DD `3.90R`)** · **`SELL` (`n=103`, WR `47.6%`): `+9.47R` (DD `5.75R`)** · `p_sf = 0.0070` · **`r(USDJPY) = 0.0174` (tương quan gần bằng 0)**.
- **Sát hạch loại bỏ sự kiện cực đoan (`Outlier Stress`):** Tổng `+14.19R` → Bỏ Top-3 lệnh: **`+6.24R`** · Bỏ Top-5 lệnh: **`+2.82R`** · Loại tháng 03/2020 (COVID): **`+6.81R`** · Loại tháng 09–10/2022 (khủng hoảng Gilt Anh): **`+12.05R`** · **Loại đồng thời CẢ HAI khủng hoảng (`n=182`): vẫn dương `+4.66R`**.

---

## 3. Nhánh 2 · Lỗ Nổi M1 Từng Phút + Reset Ngày Giờ Prague cho Danh Mục 3 Động Cơ (`extended`, Stress `+0,50 pip`)

| Sổ | Cấu hình | Annual Net % (A / B / Chung) | Peak DD % | Daily Loss % | Underwater | Calmar | Peak Margin % · Fail |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| `Swing_10000` | **`BASE_2E_USDJPY_075`** | `+4.12% / +3.05% / +3.51%` | `5.45%` | `0.74%` | `20.6m` | **`0.64`** | `11.7%` · `0` |
| `Swing_10000` | **`SOLO_GBP_VH_075`** | `+2.16% / +1.12% / +1.57%` | `3.38%` | `0.82%` | `26.0m` | **`0.46`** | `6.5%` · `0` |
| `Swing_10000` | **`PORT3E_075_GBP050`** | `+5.46% / +3.78% / +4.50%` | `5.82%` | `1.26%` | `20.1m` | **`0.77`** | `13.4%` · `0` |
| `Swing_10000` | **`PORT3E_075_GBP075`** | `+6.27% / +4.18% / +5.07%` | `6.09%` | `1.53%` | `19.9m` | **`0.83`** | `15.1%` · `0` |
| `Swing_10000` | **`PORT3E_075_GBP100`** | `+7.00% / +4.53% / +5.59%` | `6.89%` | `1.79%` | `19.9m` | **`0.81`** | `17.2%` · `0` |
| `Swing_10000` | **`PORT3E_INVDD_100`** | `+3.78% / +2.68% / +3.15%` | `3.90%` | `0.92%` | `19.9m` | **`0.81`** | `10.1%` · `0` |
| `Swing_10000` | **`PORT3E_INVDD_125`** | `+5.09% / +3.58% / +4.23%` | `5.18%` | `1.21%` | `19.9m` | **`0.82`** | `12.6%` · `0` |
| `Swing_25000` | **`BASE_2E_USDJPY_075`** | `+4.22% / +3.24% / +3.66%` | `5.62%` | `0.75%` | `19.9m` | **`0.65`** | `12.0%` · `0` |
| `Swing_25000` | **`SOLO_GBP_VH_075`** | `+2.24% / +1.19% / +1.64%` | `3.44%` | `0.85%` | `26.0m` | **`0.48`** | `6.5%` · `0` |
| `Swing_25000` | **`PORT3E_075_GBP050`** | `+5.65% / +4.01% / +4.71%` | `5.94%` | `1.26%` | `19.9m` | **`0.79`** | `13.5%` · `0` |
| `Swing_25000` | **`PORT3E_075_GBP075`** | `+6.45% / +4.43% / +5.30%` | `6.30%` | `1.52%` | `19.6m` | **`0.84`** | `15.5%` · `0` |
| `Swing_25000` | **`PORT3E_075_GBP100`** | `+7.18% / +4.79% / +5.81%` | `7.10%` | `1.79%` | `19.6m` | **`0.82`** | `17.4%` · `0` |
| `Swing_25000` | **`PORT3E_INVDD_100`** | `+4.21% / +2.91% / +3.47%` | `4.21%` | `1.00%` | `19.6m` | **`0.82`** | `10.2%` · `0` |
| `Swing_25000` | **`PORT3E_INVDD_125`** | `+5.39% / +3.62% / +4.38%` | `5.38%` | `1.25%` | `19.9m` | **`0.82`** | `12.9%` · `0` |
| `Standard_50000` | **`BASE_2E_USDJPY_075`** | `+4.24% / +3.29% / +3.70%` | `5.66%` | `0.75%` | `19.9m` | **`0.65`** | `3.6%` · `0` |
| `Standard_50000` | **`SOLO_GBP_VH_075`** | `+2.23% / +1.18% / +1.63%` | `3.49%` | `0.85%` | `26.0m` | **`0.47`** | `2.0%` · `0` |
| `Standard_50000` | **`PORT3E_075_GBP050`** | `+5.72% / +4.07% / +4.78%` | `6.00%` | `1.27%` | `19.9m` | **`0.80`** | `4.1%` · `0` |
| `Standard_50000` | **`PORT3E_075_GBP075`** | `+6.47% / +4.47% / +5.33%` | `6.46%` | `1.53%` | `19.9m` | **`0.82`** | `4.7%` · `0` |
| `Standard_50000` | **`PORT3E_075_GBP100`** | `+7.22% / +4.87% / +5.88%` | `7.27%` | `1.80%` | `19.6m` | **`0.81`** | `5.2%` · `0` |
| `Standard_50000` | **`PORT3E_INVDD_100`** | `+4.30% / +2.99% / +3.55%` | `4.27%` | `1.02%` | `19.9m` | **`0.83`** | `3.1%` · `0` |
| `Standard_50000` | **`PORT3E_INVDD_125`** | `+5.41% / +3.74% / +4.46%` | `5.41%` | `1.27%` | `19.9m` | **`0.82`** | `3.9%` · `0` |

---

## 4. Ý nghĩa cột mốc & Lộ trình tiếp theo

1. **Cột mốc lịch sử của dự án (Pass 7B → Pass 17 → Pass 22 trên `Swing_10000`):**
   - Pass 7B (1 động cơ `USDJPY` Tokyo-box): `+2,93%/năm` · Peak DD `9,08%` · Underwater `41,2m` · **`Calmar = 0,32`**.
   - Pass 17 (2 động cơ `USDJPY`): `+3,51%/năm` · Peak DD `5,45%` · Underwater `20,6m` · **`Calmar = 0,64`**.
   - **Pass 22 (3 động cơ: thêm `GBPUSD WB_EXP_80_VOL_HIGH` ngoài đồng Yên):**
     - **`PORT3E_INVDD_125`** *(trọng số chỉ tính trên Cụm A)*: **`+4,23%/năm` (`4,46%` Standard 50k)** · **Peak DD giảm sâu thêm xuống `5,18%`** · Daily `1,21%` · **`Calmar = 0,82`** (`2,56×` bản gốc!).
     - **`PORT3E_075_GBP075`**: **`+5,07%/năm` (`5,33%` Standard 50k)** · **Peak DD chỉ `6,09%` (`6,46%` Standard 50k)** · Daily `1,53%` · Underwater `19,9m` · **`Calmar = 0,83–0,84`** · `0` lỗi margin!
2. **Khoảng cách còn lại tới FTMO Challenge (`8–12%/năm` ở Peak DD `<= 7%`):** Chúng ta đã đi được hơn nửa chặng đường (`Calmar 0,32 → 0,64 → 0,84`, lãi `2,93% → 3,51% → 5,33%/năm` trong khi giữ DD `< 6,5%`). Để chạm hẳn vùng `8–10%/năm` mà giữ an toàn `DD <= 7%`, chỉ cần thêm **1–2 động cơ trực giao nữa** (từ nguồn inbox bạn sưu tầm + mở rộng hệ thống `whitebox_discovery.py` sang `US100.cash` / `GER40` hoặc thêm họ chiến lược mới trên `EURUSD`/`XAUUSD`).

# Pass 21 · Song Song: `GBPJPY` M1 Bid/Ask (`2,61M` nến) & Hệ Thống White-Box Prop-First Discovery

- **Protocol khóa trước thực nghiệm:** [PASS21-GBPJPY-M1-AND-WHITEBOX-PROP-DISCOVERY-PROTOCOL-20261123.md](PASS21-GBPJPY-M1-AND-WHITEBOX-PROP-DISCOVERY-PROTOCOL-20261123.md) (commit `9bbf69c`)
- **An toàn & kiểm thử:** Development UTC `2018–2024`, **`holdout_rows = 0`**, `OrderSend = 0`, `quant_test_suite` **`1534/1534 PASS (0 skip, 15.43s)`**, `audit-ai-environment.ps1` `errors=0; warnings=0`, `check_skill_links.py` `14 skills; 0 errors`.
- **Phán quyết tổng hợp:** **`GBPJPY_M1_REJECTED_WHITEBOX_DISCOVERY_DEPLOYED_AND_FOUND_ORTHOGONAL_GBPUSD_VOL_HIGH_CANDIDATE`**.

---

## 1. Nhánh A · Niêm phong & Pháp y Native M1 Bid/Ask `GBPJPY` (`2.609.946` nến `2018–2024`, `43,1 MB` trên D: SSD Hot Cache)

| Chiến lược (`GBPJPY`, `swap = 0`) | `n` | Base R | Stress +0,50 R | Stress +1,00 R | Cụm A / B · Năm+ · DD | BUY / SELL R | Fade R | `p` · `q_fdr` | Phân tầng |
| --- | ---: | ---: | ---: | ---: | --- | --- | ---: | --- | --- |
| **`EXP_DAILY_OPEN_080`** | `605` | `-6.55R` | `-9.52R` | `-12.46R` | `-5.0 / -4.5` · `3/7` · `16.1R` | `+10.0 / -19.6` | `-88.3R` | `0.012` · `q=0.048` | `TIER_3_DEAD_NO_EDGE` |
| **`EXP_DAILY_OPEN_100`** | `372` | `-15.61R` | `-17.37R` | `-19.12R` | `-7.3 / -10.1` · `1/7` · `20.3R` | `-1.9 / -15.5` | `-49.4R` | `0.258` · `q=0.344` | `TIER_3_DEAD_NO_EDGE` |
| **`EXP_DAILY_OPEN_120`** | `214` | `-8.18R` | `-9.22R` | `-10.25R` | `-8.5 / -0.7` · `3/7` · `15.1R` | `-2.0 / -7.2` | `-30.6R` | `0.397` · `q=0.397` | `TIER_3_DEAD_NO_EDGE` |
| **`EXP_DAILY_OPEN_080_TREND`** | `295` | `-3.54R` | `-5.03R` | `-6.51R` | `-6.3 / +1.3` · `3/7` · `8.8R` | `+4.9 / -9.9` | `-38.8R` | `0.142` · `q=0.284` | `TIER_3_DEAD_NO_EDGE` |

- **Mặt phẳng tham số 2 chiều `GBPJPY` (12 ô ở Stress +0,50 pip):** **`0 / 12`** ô dương cả 2 cụm A & B.
- **Lỗ nổi Prague Reset (`Swing_10000`):** Lõi 2 động cơ `USDJPY` (`BASE_2E_USDJPY_075`) **`+3,51%/năm` · Peak DD `5,45%` · Calmar `0,64`**; chạy lẻ `GBPJPY` (`0,50%`) lỗ **`-0.86%/năm` (DD `8.90%`)**; ghép thêm `GBPJPY` (`PORT3E_075_GBP025..050`) kéo lãi giảm còn `+2.65%–+3.07%/năm`, Peak DD tăng lên `6.66%–8.58%`, Calmar tụt còn `0.31–0.46`.
- **Nguyên nhân lộ rõ trên M1 Bid/Ask:** Spread thực của `GBPJPY` (`1,4–2,4 pip` median) + nhiễu quét SL trong phút M1 xóa sạch lãi ảo `+9,28R` từng thấy trên nến H4 Pass 19 → **loại dứt điểm `GBPJPY` cho họ `EXP_DAILY_OPEN` & Session Box (`0/30` spec qua Cụm B)**.

---

## 2. Nhánh B · Hệ Thống White-Box Prop-First Discovery (AI Env + Engine + `.mq5` Exporter) & Phát Hiện Mới

- **Thành phần hạ tầng mới đã xây dựng & kiểm toán:**
  - Engine khám phá 4 họ trắng (`swap = 0`, tách cứng Cụm A `2018–2020` → kiểm mù Cụm B `2021–2024`, BH FDR toàn không gian): `tooling/ai-engines/whitebox_discovery.py`.
  - Bộ sinh `.mq5` sạch (`InpDryRunLogOnly = true`, hard SL, `swap = 0`, ngắt lỗ ngày) & bộ kiểm toán tĩnh `.mq5` mã nguồn mở: `tooling/ai-engines/mq5_whitebox_exporter.py`.
  - Mẫu `.mq5` trắng đầu tiên xuất cho Engine #2 đã kiểm chứng: `tooling/ai-engines/exports/Naqex_WB_EXP080_USDJPY.mq5` (`0` cờ đỏ).
  - Repo skill quản trị quy trình dài hạn: `.agents/skills/whitebox-prop-discovery/SKILL.md` (`0` lỗi audit).

### Kết quả chạy khám phá lần đầu (`m_total = 174` cấu hình trên 6 tài sản M1 — Cụm A tìm → Cụm B kiểm mù)

| Ứng viên qua cổng Cụm A (Top 10) | Tài sản | `n` | Cụm A (Tìm) → Cụm B (Mù) | Tổng Stress R (Base R) | Năm+ · DD | `p` · `q_all` | `r(USDJPY)` | Phân tầng |
| --- | --- | ---: | --- | --- | --- | --- | ---: | --- |
| **`WB_EXP_80_NONE`** | `USDJPY` | `569` | `+22.2R` → **`+12.9R`** | `+35.08R` (`+40.39R`) | `7/7` · `6.4R` | `0.001` · `q=0.048` | `0.6697` | `TIER_1_FTMO_READY` |
| **`WB_EXP_65_NONE`** | `USDJPY` | `849` | `+13.7R` → **`+14.2R`** | `+27.89R` (`+35.51R`) | `6/7` · `8.9R` | `0.001` · `q=0.048` | `0.5903` | `TIER_1_FTMO_READY` |
| **`WB_EXP_80_EMA50_TREND`** | `USDJPY` | `276` | `+8.7R` → **`+15.9R`** | `+24.65R` (`+27.27R`) | `6/7` · `6.8R` | `0.001` · `q=0.048` | `0.5007` | `TIER_1_FTMO_READY` |
| **`WB_EXP_100_NONE`** | `USDJPY` | `344` | `+15.6R` → **`+6.1R`** | `+21.61R` (`+24.86R`) | `6/7` · `5.6R` | `0.007` · `q=0.091` | `0.4656` | `TIER_2_PERSONAL_VAULT` |
| **`WB_EXP_100_EMA50_TREND`** | `USDJPY` | `164` | `+7.8R` → **`+8.7R`** | `+16.52R` (`+18.14R`) | `6/7` · `3.9R` | `0.020` · `q=0.240` | `0.4135` | `TIER_2_PERSONAL_VAULT` |
| **`WB_EXP_65_EMA50_TREND`** | `USDJPY` | `406` | `+3.8R` → **`+11.8R`** | `+15.60R` (`+19.25R`) | `6/7` · `10.5R` | `0.003` · `q=0.072` | `0.4694` | `TIER_2_PERSONAL_VAULT` |
| **`WB_EXP_80_VOL_HIGH`** | `GBPUSD` | `198` | `+5.7R` → **`+8.6R`** | `+14.33R` (`+15.68R`) | `5/7` · `5.4R` | `0.006` · `q=0.091` | `0.0168` | `TIER_2_PERSONAL_VAULT` |
| **`WB_EXP_65_VOL_LOW`** | `USDJPY` | `273` | `+4.0R` → **`+9.2R`** | `+13.11R` (`+15.62R`) | `6/7` · `5.9R` | `0.002` · `q=0.072` | `0.4215` | `TIER_2_PERSONAL_VAULT` |
| **`WB_EXP_80_VOL_HIGH`** | `USDJPY` | `201` | `+9.2R` → **`+2.5R`** | `+11.69R` (`+13.52R`) | `5/7` · `5.1R` | `0.005` · `q=0.091` | `0.3687` | `TIER_2_PERSONAL_VAULT` |
| **`WB_EXP_80_VOL_LOW`** | `USDJPY` | `189` | `+3.4R` → **`+3.0R`** | `+6.42R` (`+8.12R`) | `4/7` · `6.5R` | `0.007` · `q=0.091` | `0.4614` | `TIER_2_PERSONAL_VAULT` |

### Đột phá ngoài đồng Yên phát hiện tự động từ hệ thống White-Box: **`WB_EXP_80_VOL_HIGH` trên `GBPUSD` (Native Tick M1 Bid/Ask, `swap = 0`)**
- **Quy tắc trắng siêu gọn (chỉ 2 điều kiện nhân quả):** Ngày hôm trước có biên độ mở rộng (`High - Low >= 1,10 × ATR14_D1`) → hôm sau đột phá từ giá mở cửa ngày `± 0,80 × ATR14_D1` trong khung `07:00–17:00 UTC`, SL cứng `0,75 × ATR14_D1`, đóng cưỡng bức `20:55 UTC` (`swap = 0`).
- **Bằng chứng kiểm mù rất sạch:** Cụm A `2018–2020`: **`+5,72R`** (`n=89`, `PF 1,255`) → **Cụm B kiểm mù `2021–2024`: `+8,61R` (`n=109`, `PF 1,421`, dương cả `4/4` năm mù `2021–2024`, DD chỉ `3,53R`!)**.
- **Cân bằng cả 2 chiều & trực giao tuyệt đối với `USDJPY`:** `BUY` `95` lệnh **`+5,03R`** và `SELL` `103` lệnh **`+9,30R`** (khắc phục điểm lệch BUY của `USDJPY`!); tổng **`+14,33R`** Stress (`Base +15,68R`), thắng Fade `-38,45R` tới `+52,78R`, `p = 0,006`, `BH FDR toàn 144 cấu hình q = 0,0915 <= 0,10`, **tương quan ngày với lõi `USDJPY` = `0,0168` (gần như bằng 0!)**.
- **Lưu ý trung thực (lý do tạm xếp `TIER_2` chờ Pass 22 pháp y):** `top10_R = 19,18R > 14,33R` (nhiều lệnh thắng lớn rơi vào các ngày biến động mạnh 2020 & 2022) và 2018–2019 hơi âm nhẹ (`-1,12R`, `-0,40R`).
- **Khuyến nghị Pass 22:** Chạy pháp y M1 floating equity + mặt phẳng 2 chiều 12 ô + ghép thử **Danh mục 3 động cơ (`USDJPY` Tokyo-box + `USDJPY` `EXP080` + `GBPUSD` `WB_EXP_80_VOL_HIGH`)** với Prague reset trên `Swing 10k / 25k / Standard 50k` (chạy 100% cục bộ trong ~20 giây, không cần tải dữ liệu mới!).

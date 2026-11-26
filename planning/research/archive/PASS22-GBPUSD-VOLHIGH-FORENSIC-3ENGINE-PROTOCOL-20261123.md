# Pass 22 Protocol · Pháp y M1 Floating Equity `WB_EXP_80_VOL_HIGH GBPUSD` & Ghép Danh Mục 3 Động Cơ (Prague Reset)

- **Trạng thái:** `PRE_REGISTERED_BEFORE_EXECUTION` (khóa luật trước thực nghiệm)
- **Ngày khóa:** `2026-11-23`
- **Bối cảnh kế thừa:**
  - Pass 17 (`1062475`): Lõi 2 động cơ `USDJPY` (`PORT_INV_DD_075`: Tokyo-box + `EXP_DAILY_OPEN_080`) đạt `+3,51%/năm` (Swing 10k) / `+3,70%/năm` (Standard 50k), Peak DD `5,45%–5,66%`, Daily Loss `0,74%`, Underwater `19,9–20,6` tháng, Calmar `0,64–0,65`.
  - Pass 21 (`d95b94f`): Hệ thống `whitebox_discovery.py` (tách cứng Cụm A `2018–2020` tìm → Cụm B `2021–2024` kiểm mù trên `174` cấu hình / 6 tài sản) phát hiện ứng viên ngoài đồng Yên đầu tiên vượt kiểm mù: **`WB_EXP_80_VOL_HIGH GBPUSD`** (Native Tick M1 Bid/Ask, `swap = 0`, `n = 198`, Cụm A `+5,72R` → Cụm B mù `+8,61R`, `4/4` năm mù dương, `BUY +5,03R` & `SELL +9,30R`, DD đóng `5,43R`, Fade `-38,45R`, `p = 0,006`, `BH FDR q_all = 0,0915`, `r(USDJPY) = 0,0168`). Tạm giữ ở `TIER_2` do `top10_R = 19,18R > 14,33R` — cần pháp y đầy đủ trước khi quyết định ghép làm Động cơ #3.
- **Ranh giới bất biến:** Development UTC `2018-01-01` đến `2024-12-31`, **`holdout_rows = 0`**, khóa [NATIVE_FTMO_HOLDOUT_LOCK.json](NATIVE_FTMO_HOLDOUT_LOCK.json), `OrderSend = 0`, `network_calls = 0`.

---

## 1. Nhánh 1 · Pháp y đa tầng `WB_EXP_80_VOL_HIGH GBPUSD` (Native Tick M1 Bid/Ask, `swap = 0`)

1. **Nhánh 1A — Ma trận 3 bậc phí thực chiến (`strict`, `extended`, `all_dev`):**
   - `M1_Real_Base` (`+0,0 pip` phụ phí trên spread thực + `0,2 pip/chiều` trượt cơ sở + `$5/lot` comm).
   - `M1_Real_Stress_05` (`+0,50 pip` phụ phí Stress tiêu chuẩn — chuẩn chấm điểm chính).
   - `M1_Real_Stress_10` (`+1,00 pip` phụ phí Stress cực đoan).
2. **Nhánh 1B — Hai mặt phẳng độ bền tham số (`21` ô tổng cộng ở Stress `+0,50 pip`):**
   - **Mặt phẳng 1 (`12` ô `trig_atr × vol_mult`):** `trig_atr ∈ {0.65, 0.80, 0.95, 1.10}` × `vol_mult ∈ {0.95, 1.10, 1.25}` (giữ `sl_atr = 0.75`). Kiểm xem lọc biến động `vol_mult` có tạo cao nguyên thật hay chỉ là điểm nhọn ăn may.
   - **Mặt phẳng 2 (`9` ô `trig_atr × sl_atr`):** `trig_atr ∈ {0.70, 0.80, 0.90}` × `sl_atr ∈ {0.55, 0.75, 0.95}` (giữ `vol_mult = 1.10`).
3. **Nhánh 1C — Phân tách 4 trục & Sát hạch tập trung lợi nhuận (`Outlier Stress`):**
   - Tách theo chiều (`BUY` vs `SELL`), khung giờ (`07:00–11:59 London` vs `12:00–16:59 NY`), bậc `cost/stop %`, từng năm `2018–2024`.
   - Kiểm tra độ lệ thuộc vào sự kiện cực đoan: kết quả khi **bỏ Top-3 / Top-5 lệnh thắng lớn nhất**, khi **loại toàn bộ tháng 03/2020 (COVID)**, và khi **loại toàn bộ tháng 09–10/2022 (khủng hoảng Gilt Anh)**.

---

## 2. Nhánh 2 · Mô phỏng Lỗ Nổi M1 Từng Phút + Reset Ngày Giờ Prague cho Danh Mục 3 Động Cơ

- **3 động cơ ghép chung (100% Native Tick M1 Bid/Ask, `swap = 0`, Stress `+0,50 pip`):**
  1. Engine #1: `USDJPY` Tokyo-box OCO (Pass 7B/8).
  2. Engine #2: `USDJPY` `EXP_DAILY_OPEN_080` (Pass 16/17).
  3. Engine #3 ứng viên: `GBPUSD` `WB_EXP_80_VOL_HIGH` (Pass 21).
- **Sổ kiểm định:** `Swing_10000` (`1:30`), `Swing_25000` (`1:30`), `Standard_50000` (`1:100`) trên tập `extended` khớp chuẩn Pass 17.
- **Các cấu hình rủi ro khóa trước:**
  - `BASE_2E_USDJPY_075` (đối chứng chính xác Pass 17).
  - `SOLO_GBP_VH_050`, `SOLO_GBP_VH_075`, `SOLO_GBP_VH_100`.
  - `PORT3E_075_GBP025`, `PORT3E_075_GBP050`, `PORT3E_075_GBP075`, `PORT3E_075_GBP100`.
  - `PORT3E_INVDD_075`, `PORT3E_INVDD_100`, `PORT3E_INVDD_125` (trọng số nghịch đảo DD tính **chỉ trên Cụm A `2018–2020`** cho cả 3 động cơ — không nhìn Cụm B!).
- **Tiêu chí nâng lên Engine #3 chính thức:**
  1. Vượt cả 3 bậc phí (`Base`, `Stress +0,50`, `Stress +1,00`).
  2. Mặt phẳng tham số có `>= 9/12` ô (`trig × vol_mult`) hoặc `>= 7/9` ô (`trig × sl`) dương đồng thời cả Cụm A & B.
  3. Khi ghép danh mục 3 động cơ trên cả 3 cỡ sổ (`10k`, `25k`, `50k`), phải **tăng đồng thời Lãi/năm và Calmar so với `BASE_2E_USDJPY_075` (`0,64`)**, giữ `Peak DD <= 7,0%`, `Daily Loss <= 2,5%`, `Margin Fail = 0`, và dương cả Cụm A lẫn Cụm B.

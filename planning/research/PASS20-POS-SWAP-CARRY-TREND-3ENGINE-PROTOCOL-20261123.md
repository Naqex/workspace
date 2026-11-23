# Pass 20 Protocol · Pháp y H4/M1 Nhánh Positive-Swap Carry-Trend (8 cặp) & Ghép Danh Mục 3 Động Cơ

- **Trạng thái:** `PRE_REGISTERED_BEFORE_EXECUTION` (khóa luật trước thực nghiệm)
- **Ngày khóa:** `2026-11-23`
- **Bối cảnh kế thừa:**
  - Pass 17 (`1062475`): Lõi 2 động cơ `USDJPY` (`PORT_INV_DD_075`: Tokyo-box + `EXP_DAILY_OPEN_080`) đạt `+3,51%/năm` (Swing 10k) / `+3,70%/năm` (Standard 50k), Peak DD `5,45%–5,66%`, Daily Loss `0,74%`, Underwater `19,9–20,6` tháng, Calmar `0,64` — êm cho tài khoản riêng nhưng thiếu tốc độ & phụ thuộc `USDJPY`.
  - Pass 19 (`db31557`): Stage-0 D1 phát hiện nhánh **Positive-Swap Donchian-20 (`DON20_POS`)** với `USDCAD` đạt `+8,07R` (`6/7` năm dương, Cụm A `+3,4` / B `+4,7`, DD `3,4R`, `rJPY = -0,003`) và rổ 6 cặp Swap dương thu `+$10.435` Swap dương FTMO / `+28,7R` với tương quan `~0,00` so với lõi trong ngày.
- **Mục tiêu Pass 20 (100% zero-network trên dữ liệu đã niêm phong `2018–2024`):**
  1. **Nhánh 1 (Pháp y 8 cặp Swap dương trên nến H4 + kiểm chéo Native M1 trên `USDJPY` & `EURUSD`):** Mở rộng đủ toàn bộ **8 cặp FX có Swap dương trên FTMO Swing**:
     - **6 cặp BUY Swap dương:** `GBPJPY (+3,50)`, `AUDJPY (+2,81)`, `USDJPY (+2,61)`, `USDCHF (+1,91)`, `EURJPY (+1,24)`, `USDCAD (+0,77)`.
     - **2 cặp SELL Swap dương:** `EURUSD (+0,28)`, `EURGBP (+0,19)`.
     - Kiểm tra đầy đủ từng nến H4 (`~11.000` nến/cặp) ở 2 bậc phí (`Stress_1x`: `1,8 pip` JPY / `1,5 pip` non-JPY + hoa hồng; `Stress_2x`: `3,0 pip` RT), đồng thời **tách minh bạch lợi nhuận từ Giá thuần (`Zero-Swap`) vs lợi nhuận kèm Swap FTMO** (vì lãi suất & Swap sàn có thể thay đổi theo chu kỳ ngân hàng trung ương), kèm đối chứng **H4 vs Native M1 Bid/Ask** trên `USDJPY` & `EURUSD` và kiểm định **Random-Entry Matched-Hold Null (`N = 1.000`)**.
  2. **Nhánh 2 (Mặt phẳng độ bền tham số 2 chiều `12` ô):** Quét `entry_don ∈ {15, 20, 30, 40}` × `(exit_don, sl_atr) ∈ {(10, 1.5), (10, 2.0), (15, 2.5)}` trên cả 2 cấu trúc rổ:
     - `SLEEVE_NON_JPY_4`: Chỉ 4 cặp **KHÔNG có đồng Yên** (`USDCAD` Long, `USDCHF` Long, `EURUSD` Short, `EURGBP` Short) — loại bỏ hoàn toàn rủi ro trùng đồng Yên với Engine #1 & #2.
     - `SLEEVE_ALL_8_JPYCAP1`: Đủ 8 cặp nhưng khóa trần **tối đa 1 vị thế Yên mở cùng lúc** (chống nhân rủi ro trùng khi đồng Yên đảo chiều đột ngột).
  3. **Nhánh 3 (Mô phỏng Lỗ Nổi Ghép Danh Mục 3 Động Cơ + Reset Ngày Giờ Prague trên `Swing_10000`, `Swing_25000`, `Standard_50000`):**
     - Ghép trực tiếp đường equity từng phút thật của **Engine #1 (`USDJPY` Tokyo-box) + Engine #2 (`USDJPY` `EXP_DAILY_OPEN_080`, Stress `+0,50 pip`)** từ Pass 17 với đường equity nổi từng nến H4 của **Engine #3 (`SLEEVE_NON_JPY_4` và `SLEEVE_ALL_8_JPYCAP1`)** ở các mức phân bổ rủi ro khóa trước (`0,25%`, `0,40%`, `0,50%` mỗi lệnh carry, có trần tổng rủi ro mở đồng thời).
     - Kiểm tra nghiêm ngặt: `Annual Net %` (Cụm A / Cụm B / Chung), `Peak Floating DD %`, `Max Prague Daily Loss %`, `Underwater months`, `Max Margin %`, `Margin Fail = 0`, `Calmar`.
- **Ranh giới bất biến:** Development UTC `2018-01-01` đến `2024-12-31`, **`holdout_rows = 0`**, khóa [NATIVE_FTMO_HOLDOUT_LOCK.json](NATIVE_FTMO_HOLDOUT_LOCK.json), `OrderSend = 0`, `network_calls = 0`.
- **Điều kiện nâng tầng trung thực:** Mọi cặp ngoài `USDJPY`/`EURUSD` chạy trên H4/D1 trong Pass 20 vẫn mang nhãn `H4_FORENSIC_PENDING_M1_CONFIRMATION` (chưa cấp `TIER_1_FTMO_READY` chính thức nếu chưa xác nhận M1 Bid/Ask đối với cặp ngoài bộ 4 cặp đã có M1, trừ khi chênh lệch H4 vs M1 trên `USDJPY` & `EURUSD` cho thấy độ sai lệch nhỏ hơn `0,15R/năm`).

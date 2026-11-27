# Pass 17 · Protocol pháp y M1 Floating Equity cho `EXP_DAILY_OPEN_080 USDJPY` & kiểm chéo `GBPUSD` / `US500`

Baseline `8aa1726` (nhánh `codex/prop-research-roadmap`).
Phạm vi dữ liệu **Development UTC `2018-01-01` → `< 2025-01-01`** trên **Hot M1 Parquet Cache SSD** (`.runtime/hot-m1-cache/`, SHA-verified).
Khóa cứng Holdout `>= 2025-01-01` (`NATIVE_FTMO_HOLDOUT_LOCK.json`, `holdout_rows = 0`).
`network_calls = 0`, `OrderSend = 0`, không MT5, không đọc `.env`.
Thông số phí/margin/lot bám SHA `36f1535` (FTMO Standard) và `8fd77ef` (FTMO Swing); phân loại 3 tầng theo `validation-gates.md`.

---

## Nhánh 1 · Pháp y toàn diện ứng viên `TIER_1_FTMO_READY`: `EXP_DAILY_OPEN_080 USDJPY` (`swap = 0`)

- **Cơ chế gốc khóa từ Pass 16:** Trên Native Tick-derived M1 Bid/Ask `USDJPY` (`2018–2024`), đặt mốc `open_0 = bid_open(00:00 UTC)`, dùng Wilder `ATR14_D1` đã đóng hôm trước (`100%` nhân quả). OCO trong `07:00–16:59 UTC` tại `open_0 ± 0,80 * ATR14_D1`, `SL = 0,75 * ATR14_D1` tính từ giá vào, tối đa 1 lệnh/ngày, đóng phẳng `20:55 UTC` (`swap = 0`).
- **4 bài sát hạch bắt buộc trước khi xem xét bước Qualification / Holdout:**
  1. **Khớp mẫu `strict` (`1.334` ngày) vs `extended` (`1.564` ngày) vs toàn kỳ (`all_dev`):** Đối soát với đúng lịch ngày đủ điều kiện của Engine #1 Pass 7B/8 để loại trừ sai lệch phủ dữ liệu; đo trên cả **3 bậc stress (`M1_Real_Base +0,0 pip`, `M1_Real_Stress_05 +0,50 pip` primary, `M1_Real_Stress_10 +1,00 pip` cực đoan)**.
  2. **Mặt phẳng độ bền tham số 2 chiều (`12` ô):** `trig_atr ∈ {0,65; 0,80; 0,95; 1,10}` × `sl_atr ∈ {0,55; 0,75; 0,95}` ở `M1_Real_Stress_05` — kiểm tra cao nguyên lợi nhuận (tránh gai đơn lẻ).
  3. **Giải phẫu 4 trục Known-at-Entry:** Theo từng năm (`2018–2024`), chiều (`BUY`/`SELL`), khung vào (`07:00–11:59` London vs `12:00–16:59` NY) và tỷ lệ `cost / stop (%)`.
  4. **Đo lỗ nổi từng phút thật (`M1 Floating Equity` + Reset ngày giờ Prague qua `pass11_portfolio.replay()`):**
     - **Chạy độc lập (`SOLO_EXP080`)** trên 3 sổ `Swing 10k`, `Swing 25k`, `Standard 50k` tại các mức rủi ro `0,30% / 0,40% / 0,50% / 0,75% / 1,00%` — đo `annual_pct (A/B/All)`, `peak_dd_pct`, `daily_loss_pct`, `static_loss_pct`, `underwater_months`, `peak_margin_pct`, `margin_failures`.
     - **Ghép cặp với Engine #1 `USDJPY` Tokyo-box (Pass 7B/8)** trên ngày trùng nhau (`strict` & `extended`): đo cả chế độ **Song song (`PORT_EQUAL 0,15+0,15`, `0,20+0,20`, `0,25+0,25`, `PORT_INV_DD 0,40`, `0,50`)** lẫn kiểm `double_sl_days` & `simultaneous_margin_pct`, để kiểm chứng có vượt rào nội bộ (`daily_loss <= 2,5%`, `peak_dd <= 6,5–8,0%`, tốc độ `>= 8%/năm`) hay không.

---

## Nhánh 2 · Kiểm chéo `EXP_DAILY_OPEN` sang tài sản độc lập (`GBPUSD` & `US500`, Native Bid/Ask M1, `swap = 0`)

- **`GBPUSD` (Native Tick M1 Bid/Ask, `M1_Real_Stress_05`):** 4 cấu hình (`0,80 / 1,00 / 1,20 ATR` + `0,80_TREND`), OCO `07:00–16:59 UTC`, flat `20:55 UTC` (`swap = 0`).
- **`US500` (Sealed Explicit M1 Bid/Ask, NYSE full cash sessions `390` phút, `$0/lot` comm, `M1_Stress_High = 0,75 pt/chiều` primary + `Mid 0,50` + `Base 0,25`):** Mốc `open_0 = bid_open(09:30 NY)`, Wilder `ATR14_D1` đã đóng phiên trước, OCO `10:00–14:30 NY` tại `open_0 ± {0,80; 1,00; 1,20} * ATR14_D1` (+ `0,80_TREND` với `EMA50_D1`), `SL = 0,75 * ATR14_D1`, flat `15:55 NY` (`swap = 0`).
- Đối chứng `Fade`, **Monte Carlo Random-Entry Null (`N = 1.000`, `seed = 20261123`)**, **BH FDR (`m = 8`)**, và phân loại 3 tầng (`TIER_1` / `TIER_2` / `TIER_3`).
- Nếu `GBPUSD` hoặc `US500` đạt `TIER_1_FTMO_READY`, lập tức chạy ghép danh mục M1 đa tài sản cùng `EXP_DAILY_OPEN_080 USDJPY` và Engine #1 `USDJPY`.

# Pass 21 Protocol · Song Song: `GBPJPY` M1 Bid/Ask (`EXP_DAILY_OPEN`) & Hệ Thống White-Box Prop-First Discovery

- **Trạng thái:** `PRE_REGISTERED_BEFORE_EXECUTION` (khóa luật trước thực nghiệm)
- **Ngày khóa:** `2026-11-23`
- **Ủy quyền owner:** Owner xác nhận chạy song song 2 nhánh: (A) tải & niêm phong `GBPJPY` M1 Bid/Ask `2018–2024` kiểm thật ứng viên Stage-0 Pass 19, và (B) xây dựng hệ thống **White-Box Discovery ưu tiên quỹ (FTMO-First)** gồm công cụ tái sử dụng, repo skill `.agents/skills/whitebox-prop-discovery/`, bộ kiểm định phân tầng 3 lớp, bộ xuất `.mq5` trắng sạch, và lượt chạy khám phá thực nghiệm đầu tiên trên toàn bộ D: SSD Hot M1 Cache.
- **Ranh giới bất biến:**
  - Tuyệt đối khóa vùng Holdout **`>= 2025-01-01`** (`NATIVE_FTMO_HOLDOUT_LOCK.json`, **`holdout_rows = 0`**). Mọi truy vấn Dukascopy cho `GBPJPY` bị ép cứng biên trên `to = 2025-01-01T00:00:00Z` (exclusive) và xác minh `last_ms < 1735689600000` trước khi ghi Parquet.
  - `OrderSend = 0`, không đọc `.env`, không chạy file `.ex5`/`.exe`/`.dll` đóng kín.
  - Ưu tiên tuyệt đối cho **FTMO Swing (`10k/25k`, `1:30`, 80%) & FTMO Standard (`50k`, `1:100`, 20%)**: `swap = 0` trong ngày (hoặc kiểm soát Swap dương), hard SL trên mọi lệnh, zero grid/martingale, reset ngày theo giờ `Europe/Prague`.

---

## 1. Nhánh A · Pháp y M1 Bid/Ask `GBPJPY` (`2018–2024`) & Ghép Danh Mục 3 Động Cơ

1. **Niêm phong dữ liệu `GBPJPY` M1 Bid/Ask (`2018–2024`):**
   - Tải song song `priceType='bid'` và `priceType='ask'` từ `dukascopy-node` đã ghim (`.runtime/research-data/node_modules/dukascopy-node`), đối khớp từng phút (loại nến đóng cửa weekend/flat, đảm bảo `ask >= bid`), đóng gói 7 file Parquet Zstd SHA-verified vào `E:\BACKUP-TRADINGWORKSPACE\ai-engine-jobs\pass21-gbpjpy-m1-20261123\development-m1\` và nạp vào D: SSD Hot M1 Cache (`hot_m1_cache.py`).
2. **Kiểm định pháp y `EXP_DAILY_OPEN` trên `GBPJPY` (`swap = 0`, Native M1 Bid/Ask):**
   - Kiểm tra đủ 3 bậc phí (`M1_Real_Base`, `M1_Real_Stress_05` `+0,50 pip`, `M1_Real_Stress_10` `+1,00 pip`) cho `0,80 / 1,00 / 1,20 ATR` và `0,80_TREND` (`BH FDR m = 4`).
   - Nếu vượt Stress `+0,50 pip` và dương cả 2 cụm A (`2018–2020`) & B (`2021–2024`), chạy ngay:
     - Mặt phẳng độ bền tham số 2 chiều **`12` ô** (`trig ∈ {0.65, 0.80, 0.95, 1.10}` × `sl ∈ {0.55, 0.75, 0.95}`).
     - Phân tách 4 trục (`BUY` vs `SELL`, khung giờ `London` vs `NY`, bậc chi phí).
     - Mô phỏng **Lỗ nổi M1 từng phút + Reset ngày giờ Prague** trên `Swing_10000`, `Swing_25000`, `Standard_50000` (chạy lẻ `GBPJPY` và ghép 3 động cơ cùng lõi Pass 17 `USDJPY` Tokyo-box + `EXP_DAILY_OPEN_080 USDJPY`).

---

## 2. Nhánh B · Hệ Thống White-Box Prop-First Discovery (AI Env + Engine + `.mq5` Exporter)

1. **Nguyên tắc chống Overfitting bắt buộc (Strict Split):**
   - **Tập tìm kiếm (Discovery ONLY):** Chỉ dùng **Cụm A (`2018-01-01` đến `2020-12-31`)** để chọn lọc cấu trúc ứng viên đạt ngưỡng tối thiểu (`n_A >= 60`, `Net_A > 0`, `PF_A > 1,05`, `Stress FTMO`, `swap = 0`).
   - **Tập kiểm định mù (Blind OOS Validation):** Mọi ứng viên qua Cụm A được chấm điểm **MÙ trên Cụm B (`2021-01-01` đến `2024-12-31`)**, đồng thời tính **BH FDR trên TOÀN BỘ không gian tìm kiếm `m_total`** (tránh gian lận chọn trước!), kiểm **Fade đối xứng**, **Paired Sign-Flip & Random-Entry MC Null (`N = 1.000`)**, **vùng lân cận tham số ±25%**, và **tương quan ngày `r(USDJPY)`** với lõi Pass 17.
   - **Tập Holdout (`>= 2025-01-01`):** Tuyệt đối không mở (`holdout_rows = 0`).
2. **Không gian ngữ pháp White-Box ưu tiên quỹ (4 họ trực giao, `swap = 0`, 0% grid/martingale, tối đa 2–3 điều kiện dễ đọc):**
   - **Họ 1 (`WB_SESSION_BOX`):** Đột phá biên hộp phiên thanh khoản (`00:00–06:59`, `02:00–07:59`, `07:00–10:59 UTC`) có lọc biên độ hộp/ATR, SL cạnh hộp hoặc `0,75 ATR`, flat `20:55 UTC`.
   - **Họ 2 (`WB_OPEN_EXPANSION`):** Mở rộng từ giá mở cửa ngày/phiên (`±k ATR`, `k ∈ {0.65, 0.80, 1.00, 1.20}`) kèm bộ lọc chế độ nhân quả (`NONE`, `EMA50_TREND`, `PREV_DAY_VOL_HIGH`, `PREV_DAY_VOL_LOW`), SL `0,75 ATR`, flat cuối ngày.
   - **Họ 3 (`WB_OVEREXT_FADE`):** Đảo chiều quá đà có SL cứng (`fade` sau khi giá chạy `>= k ATR` trong phiên sáng/Âu sang phiên Mỹ, `k ∈ {0.80, 1.00, 1.20}`, SL `0,75 ATR`, flat cuối ngày — kiểm chứng trực diện giả thuyết hồi quy trên `EURUSD`, `GBPUSD`, `US500`, `XAUUSD`).
   - **Họ 4 (`WB_IMPULSE_PULLBACK`):** Xung lực đầu phiên (`07:00–10:00 UTC` hoặc `09:30–10:30 ET` chạy `>= 0,40 ATR`) → chờ hồi lại `30%–50%` xung lực rồi vào thuận chiều, SL `0,75 ATR`, flat cuối ngày.
3. **Thành phần AI Env & Công cụ bàn giao:**
   - Engine tái sử dụng: `tooling/ai-engines/whitebox_discovery.py` (chạy trên toàn bộ tài sản trong D: SSD Hot M1 Cache, xuất bảng xếp hạng 3 tầng `TIER_1 / TIER_2 / TIER_3`).
   - Bộ sinh `.mq5` trắng & đọc `.mq5` mở: `tooling/ai-engines/mq5_whitebox_exporter.py` (sinh mã `.mq5` sạch, zero-grid, hard-SL, đóng cưỡng bức cuối ngày cho ứng viên đã kiểm chứng + parser đọc `input` từ file `.mq5` mã nguồn mở MQL5 CodeBase).
   - Repo Skill chuẩn hóa: `.agents/skills/whitebox-prop-discovery/SKILL.md` (tuân thủ `ai-environment-maintainer`, kiểm bằng `audit-ai-environment.ps1` và `check_skill_links.py`).

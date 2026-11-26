# Pass 13 · Protocol 3 nhánh song song tìm Engine #2 (FX Liquidity Sweep · Clean-Room Intel · US500 Explicit M1)

Baseline `21557e2` (nhánh `codex/prop-research-roadmap`).
Phạm vi dữ liệu **Development UTC `2018-01-01` → `< 2025-01-01`** (`1514764800`..`1735689600`).
Khóa cứng Holdout `>= 2025-01-01` theo `NATIVE_FTMO_HOLDOUT_LOCK.json` (`sha256: f0a6b43cb205535b0a959456455dc1d857a0936c06c2e51b8614fd7d772a8486`, bắt buộc `holdout_rows = 0`).
Không mạng (`network_calls = 0`), không MT5, `OrderSend = 0`, không đọc `.env`, không mô phỏng Challenge trước khi vượt cổng M1 + SL + Portfolio.
Thông số phí/margin/swap bám cứng SHA của `36f1535` (FTMO Standard) và `8fd77ef` (FTMO Swing) qua `quant_core.ftmo_track_replay.profiles()`.
Mọi kết quả sử dụng dữ liệu cục bộ Dukascopy/QDM là proxy execution, chưa phải broker fill trực tiếp.

## Quy ước chung cho cả 3 nhánh

- **Phân cụm thời gian:** 7 năm (`2018`–`2024`), Cụm A (`2018–2020`), Cụm B (`2021–2024`).
- **Mốc ghép danh mục (Portfolio Reference):** Tái dựng chính xác Engine #1 `USDJPY` Tokyo-box Pass 7B/8 ở `M1_Real_Stress_05` (`1.228` strict / `1.437` extended) qua `pass11_portfolio.frozen_usdjpy()`. Khi một ứng viên vượt cổng sống sót SL, chạy ghép danh mục trên ngày trùng nhau (`Swing 10k`, `Swing 25k`, `Standard 50k`): `USDJPY 0,30%` solo vs `Equal 0,15%+0,15%` vs `Inverse-DD Cụm A` (tổng `0,30%`), reset Prague, envelope M1.
- **Đối chứng chống ảo giác bắt buộc (`validation-gates.md`):**
  1. **Fade control:** Đảo chiều ngay tại cùng timestamp/báo giá (trên quote khả thi đối diện).
  2. **Monte Carlo Random-Entry Null Test:** `N = 1.000` lần rút ngẫu nhiên cố định (`seed = 20261123`), giữ nguyên tần suất, chiều và độ dài nắm giữ để tính phân vị 95 (`p95`) và `p_value = P(null >= observed)`. Chiến lược chỉ đạt kiểm định thời điểm khi `p_value < 0,05`.
  3. **Xử lý chạm SL/TP cùng phút:** Luôn giải quyết theo kịch bản xấu nhất (giả định chạm SL trước).

---

## Nhánh 1 · `GBPUSD` & `EURUSD` Intraday Liquidity Sweep & Reversal

- **Động lực:** Khai thác trực tiếp hiện tượng 172 ngày quét hai biên từng đánh gục breakout London ORB ở Pass 11 trên dữ liệu Tick Bid/Ask cục bộ (`swap = 0`).
- **Nguồn dữ liệu cục bộ (Native Tick-derived M1 Bid/Ask, `network_calls = 0`):**
  - `GBPUSD`: Đọc trực tiếp parquets đã niêm phong từ `pass11-gbpusd-m1-20261120/development-m1/GBPUSD-M1-BIDASK-2018..2024.parquet` (kiểm SHA manifest Pass 11).
  - `EURUSD`: Export từ cache cục bộ QDM `EURUSD_TICK_TW` (`517,75M` ticks) chỉ trong `datefrom=YYYY.01.01`, `dateto=YYYY.12.31` (`2018`–`2024`, timezone `UTC`), kiểm clock admission + gộp thành `EURUSD-M1-BIDASK-2018..2024.parquet` kèm manifest SHA-256 trước khi chạy chiến lược.
- **Luật cơ học 100% nhân quả (theo đồng hồ địa phương London `Europe/London`, DST tự động, tối đa 1 lệnh/ngày):**
  - **Vùng thanh khoản tham chiếu (`Box`):** `00:00–07:59` London (`480` phút): `box_high = max(ask_high)`, `box_low = min(bid_low)`. Bỏ ngày `box_high <= box_low`.
  - **Cửa sổ quét & đảo chiều (`08:00–12:59` London, 300 phút):**
    - Theo dõi **lần quét biên đầu tiên** sau `08:00`:
      - **Quét đỉnh → SELL:** Một phút có `ask_high >= box_high` (và chưa từng chạm `box_low`) và tại phút đó hoặc phút kế tiếp trong `[08:00, 13:00)` nến M1 đóng hẳn vào trong hộp (`bid_close < box_high`). Vào lệnh **SELL** tại `bid_open` của phút kế tiếp (`t + 1`). `sweep_extreme = max(ask_high)` từ `08:00` đến phút reclaim. `SL = sweep_extreme + 2,0 pip` (`0,0002`), khớp tại `ask_high >= SL` (hoặc `ask_open` nếu gap).
      - **Quét đáy → BUY:** Đối xứng — `bid_low <= box_low` (chưa chạm `box_high`), đóng `ask_close > box_low`. Vào **BUY** tại `ask_open` của phút `t + 1`. `sweep_extreme = min(bid_low)`. `SL = sweep_extreme - 2,0 pip`, khớp tại `bid_low <= SL` (hoặc `bid_open` nếu gap).
      - **Quét cả 2 đầu trước khi reclaim:** Bỏ ngày (`dual_sweep_skip`).
  - **Hard Flat:** `17:00` London (trước `17:00 NY` → **`swap = 0`**).
  - **Phân loại gap:** Giữ chuẩn `strict` (đủ mọi phút `00:00..17:00` London) và `extended` (`strict + A_admitted`, tối đa 5 phút thiếu rời rạc, lệch giá `<= 0,2 pip`, không rơi sát điểm sweep/reclaim/entry/exit).
  - **Phí & Stress:** Observed M1 Bid/Ask spread + commission FTMO `\$5/lot` round-trip + slippage gốc `0,2 pip/chiều`, đánh giá 3 bậc `M1_Real_Base (+0,0 pip)`, **`M1_Real_Stress_05 (+0,5 pip)` (primary)**, `M1_Real_Stress_10 (+1,0 pip)`.
  - **Các chế độ thoát lệnh đăng ký trước (trên cùng tập điểm vào):**
    1. **Stage-0 Raw Horizon:** `2h`, `4h`, `hard_flat (17:00)` + đối chứng `Fade` + `Random-Entry Null (N=1000)`.
    2. **`Sweep_SL_Flat`:** SL cấu trúc tại `sweep_extreme ± 2 pip`, giữ tới `17:00` London.
    3. **`Sweep_SL_OppEdge`:** SL cấu trúc tại `sweep_extreme ± 2 pip`, TP tại biên đối diện của hộp (`box_low` / `box_high`), hard flat `17:00` London.
  - **Kiểm ổn định lân cận (nếu vượt cổng sống sót):** Thử `buffer ∈ {1,0; 2,0; 3,0} pip` và `box_end ∈ {07:00, 08:00}` London để xác nhận không sụp vách đá.
  - **Cổng sống sót:** Dương cả Cụm A & Cụm B ở `M1_Real_Stress_05` trên cả `strict` và `extended`, `>= 5/7` năm dương, vẫn dương khi bỏ top 10 lệnh, thắng `Fade` và `Random-Entry Null (p < 0,05)`.

---

## Nhánh 2 · Tái dựng Clean-Room Air-Gap từ `strategy-intel` (`NEN022` & `SEA003`)

- **Tuân thủ Air-Gap:** Chỉ đọc đặc tả văn bản đã khử nhiễu (`NEN022`, `SEA003`) từ `strategy-intel/handoff/sanitized_master_leads.json` (`SOURCE_CLAIM_ONLY`); cài đặt độc lập 100% trong `Naqex/workspace`, không import file/code chéo repo.
- **Nguồn dữ liệu cục bộ:**
  - `EURUSD` & `GBPUSD`: Native Tick-derived M1 Bid/Ask (`2018–2024`).
  - `XAUUSD`: Export cục bộ từ QDM `XAUUSD_TW` (`M1` Bid, `2018–2024`, `network_calls = 0`, kiểm clock `< 2025-01-01`). **Gắn nhãn rõ `M1_BID_PROXY_SPREAD` (`native_Ask = false`)**: dùng spread proxy đo từ FTMO Demo (`0,35` base / `0,50` stress mid / `0,75` stress high USD/oz), commission FTMO `price * 100 * 0,000007` mỗi chiều, và **FTMO Swap chính xác (`swap_long = -56,56`, `swap_short = -4,20`, thứ Tư `3×`)**. Nếu trượt trên proxy spread + swap thật → **REJECT dứt khoát**; nếu sống sót → chỉ gắn nhãn `PROVISIONAL_NEEDS_NATIVE_TICK_BIDASK`, chưa đủ điều kiện qualify.
- **Ứng viên 2A — `NEN022` (Fakey H4, 2 chiều, trên `EURUSD`, `GBPUSD`, `XAUUSD`):**
  - Tổng hợp nhân quả nến `H4` theo đồng hồ UTC (`00, 04, 08, 12, 16, 20 UTC`) từ M1.
  - Chuỗi 3 nến `H4` đã đóng hoàn toàn `[mother (t-2), inside (t-1), fakey (t)]`:
    - `inside.high <= mother.high` và `inside.low >= mother.low`.
    - **BUY Fakey:** `fakey.low < inside.low`, `fakey.high <= mother.high`, `fakey.close > inside.low` và `fakey.close > fakey.open`. Vào `BUY` tại phút M1 đầu tiên sau khi `fakey` đóng (`ask_open`). `SL = fakey.low - buffer` (`2 pip` FX / `\$0,50` XAUUSD), `TP = entry + 2,0 * risk`.
    - **SELL Fakey:** Đối xứng (`fakey.high > inside.high`, `fakey.low >= mother.low`, `fakey.close < inside.high`, `fakey.close < fakey.open`). Vào `SELL` tại `bid_open`. `SL = fakey.high + buffer`, `TP = entry - 2,0 * risk`.
  - Chạy đường đi M1 đầy đủ (SL-first khi cùng phút), giới hạn giữ tối đa `5` ngày giao dịch (báo cáo cả hai chế độ: đóng trước cuối tuần thứ Sáu `20:55 UTC` cho Standard và giữ qua tuần cho Swing), tính đúng `rollovers(start, end, triple=3)` theo giờ `17:00 NY`.
  - Báo cáo Stage-0 (`12h / 24h / 48h` + Fade), kết quả SL/TP `2R` (thêm lân cận `1,5R / 3,0R` nếu sống sót), và `Random-Entry Null (N=1000)`.
- **Ứng viên 2B — `SEA003` (`XAUUSD` Turn-of-Month, Long-Only, Pre-Mortem Swap 3× + Null Test):**
  - Quy tắc nguyên văn: *"Mua 2 phiên cuối tháng, đóng phiên 3 tháng mới"* (dùng lịch ngày giao dịch UTC Mon–Fri có nến M1 trong `2018–2024`, ~84 chu kỳ tháng).
  - **Vào lệnh:** `01:00 UTC` ngày giao dịch áp chót (thứ 2 tính từ cuối tháng `M`); kiểm độ nhạy giờ vào `00:05 UTC` và `08:00 UTC`.
  - **Thoát lệnh:** `20:55 UTC` ngày giao dịch thứ 3 của tháng `M+1` (hoặc sớm hơn nếu chạm SL).
  - **2 biến thể:** (1) `Unhedged_NoSL` (đo nguyên bản mùa vụ + tổng chi phí Swap 3× FTMO + Max Floating DD thực trên M1); (2) `ATR14_SL_2x` (Wilder ATR(14) D1 đóng trước giờ vào, `SL = entry - 2,0 * ATR14`, chạy replay Swing 10k `0,30%` risk).
  - **Kiểm định sát hạch bắt buộc:** Phân tách `Gross Price PnL` vs `Spread+Comm+Slip` vs `FTMO Swap (kèm 3× thứ Tư)` và chạy **`Random-Entry Null (N=1000)`** (chọn ngẫu nhiên 1 ngày giao dịch trong mỗi tháng với cùng thời gian giữ 5 phiên) để kiểm tra xem Turn-of-Month có thực sự thắng xu hướng tăng dài hạn của vàng `2018–2024` sau khi trừ phí qua đêm hay không.

---

## Nhánh 3 · `US500 NY ORB` trên Explicit M1 Bid/Ask đã niêm phong (`2018–2024`)

- **Giải quyết dứt điểm điểm nghẽn QDM 429 của Pass 12 bằng nguồn riêng hợp lệ:**
  - Không thay đổi biên nhận `US500_M1_DATA_UNAVAILABLE` của Pass 12; Pass 13 mở nguồn **Paired Explicit M1 Bid/Ask** (direct-Dukascopy đã qua `explicit_m1_view.py` & `sealed_m1_review.py`, `holdoutRead = false`, `networkCalls = 0`):
    - `2018–2021`: `challenge-discovery4-20261108/execution-v1/us500-long-explicit-source-v1/<year>/q{1..4}-{bid,ask}.json`
    - `2022–2024`: `challenge-discovery4-20261108/execution-v1/us500-explicit-source-v1/<year>/q{1..4}-{bid,ask}.json`
  - Kiểm SHA-256 từng file `q{1..4}-{bid,ask}.json` đối chiếu với `q{1..4}-{bid,ask}-seal.json` và kiểm mọi timestamp nằm gọn trong `[1514764800000, 1735689600000)` (`holdout_rows = 0`).
- **Tái sử dụng 100% động cơ đã kiểm toán `pass12_us500_ny_orb.py`:**
  - NYSE full days 390 phút (DST New York), hộp `09:30–10:30`, OCO `10:30–14:00`, hard flat `15:55` (`swap = 0`).
  - Observed explicit Bid/Ask spread, `$0/lot` commission FTMO `US500.cash`, 3 bậc slippage `M1_Base (0,25 pt/chiều)`, `M1_Stress_Mid (0,50 pt/chiều)`, **`M1_Stress_High (0,75 pt/chiều)` (primary)**.
  - Chạy đủ Stage-0 (`2h / 4h / hard_flat` + Fade) + **Monte Carlo Random-Entry Null (`N=1000`)** + opposite-edge SL (`strict` vs `extended`), và nếu vượt cổng sống sót thì chạy ghép danh mục **USDJPY + US500.cash** qua `pass12_us500_ny_orb.combine()`.
  - Bổ sung kiểm tra đối chứng **US500 NY ORB Fade** (nếu Breakout âm và Fade dương vượt cả 2 cụm ở `M1_Stress_High`, ghi nhận riêng làm báo cáo chẩn đoán — không tự đổi luật thắng sau khi nhìn số).

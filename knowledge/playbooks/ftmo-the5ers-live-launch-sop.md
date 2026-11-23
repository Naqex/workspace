---
doc_type: evergreen
domain: knowledge
topic: ftmo-the5ers-live-launch-sop
updated_utc: 2026-11-24
order_send_count: 0
holdout_rows_analysed: 0
sources:
  - "tooling/ai-engines/exports/deployment_kit/ACTIVATION-CARD-LOCAL-MT5.md"
  - "tooling/ai-engines/exports/deployment_kit/the5ers_kit/THE5ERS-LAUNCH-AND-TERMS11-EMAIL.md"
  - "tooling/ai-engines/exports/deployment_kit/ops_watchdog/naqex_mt5_watchdog.ps1"
  - "tooling/ai-engines/quant_factory/prop_challenge_tracker.py"
  - "tooling/ai-engines/quant_factory/daily_ops_briefing.py"
  - "knowledge/topics/mt5-live-execution-gaps-and-tca.md"
  - "knowledge/playbooks/naqex-master-roadmap-2026-2027.md"
  - "planning/research/MULTI-PROP-SCALING-AND-BLACKSWAN-STRESS-20261124.md"
---

# Quy Trình Khai Trương Thực Chiến FTMO & The5ers (`Pre-Flight → Day-1 → Day-14` & Emergency Runbook)

> **Mục tiêu SOP:** Biến việc triển khai từ **`FTMO-Demo 1515343166` (14 ngày Free Trial)** sang **tài khoản trả phí `FTMO Standard BF-25%` + `The5ers High Stakes`** thành một quy trình cơ học, kiểm chứng được bằng số liệu và không phụ thuộc cảm xúc. Mọi bước đều giữ nguyên tắc **fail-closed**: chưa qua đủ 5 quy tắc trong [prop_challenge_tracker.py](../../tooling/ai-engines/quant_factory/prop_challenge_tracker.py) thì tuyệt đối **KHÔNG** nâng sang tài khoản trả phí.

---

## 1. Danh Mục Kiểm Tra Trước Chuyến Bay (`Pre-Flight Checklist` — Trước Giờ G)

1. **Xác minh Sandbox MT5 Portable (`FTMO-Demo 1515343166`):**
   - Dùng đúng thư mục portable độc lập `.runtime/ftmo-demo-portable-1515343166` (tuyệt đối không mở chung terminal cá nhân khác), tuân theo [ACTIVATION-CARD-LOCAL-MT5.md](../../tooling/ai-engines/exports/deployment_kit/ACTIVATION-CARD-LOCAL-MT5.md).
   - Kiểm tra `9` biểu đồ trong profile `Naqex_FreeTrial`: `7` EA lõi (`E1..E7` magic `20261122..20261129`, trừ `20261127`), `1` EA vệ tinh `S6` (`20261127`), và `1` `Naqex_AccountOrchestrator` giám sát chung (`20261120..20261199`).
   - Đảm bảo `KeepPrivate = 0`, `Leverage = 1:30`, `AutoTrading` bật **CHỈ** khi chủ sở hữu sẵn sàng mở Free Trial (mặc định triển khai mới bắt đầu bằng `InpDryRunLogOnly = true` trong 24h đầu để kiểm tra tín hiệu mà không gửi lệnh!).
2. **Kiểm tra Hạ tầng VPS & Watchdog Uptime:**
   - Chọn VPS độ trễ thấp (`<= 15 ms` tới máy chủ `FTMO-Demo` / `The5ers` London/Frankfurt, RAM `>= 4 GB`, tắt Windows Update tự khởi động lại trong giờ phiên Á–Âu–Mỹ từ `23:00 UTC` Chủ nhật đến `21:55 UTC` Thứ Sáu).
   - Cài tác vụ định kỳ mỗi `5` phút cho [naqex_mt5_watchdog.ps1](../../tooling/ai-engines/exports/deployment_kit/ops_watchdog/naqex_mt5_watchdog.ps1) để tự giám sát `terminal64.exe`, đọc `naqex_heartbeat.json`, và báo động ngay nếu nhịp tim cũ quá `180` giây (`-StaleAfterSec 180`) hoặc `orphan_no_sl > 0`.
3. **Đồng bộ & Làm mới Lịch Tin Đỏ Hằng Quý (`naqex_red_news_utc.csv`):**
   - Kiểm tra tệp [naqex_red_news_utc.csv](../../tooling/ai-engines/exports/Files/naqex_red_news_utc.csv) đã chép đúng vào `MQL5\Files\` của terminal và có đủ các sự kiện NFP, CPI, FOMC, BoE, ECB, BoJ trong quý hiện tại (`InpGuardEnableRedNews = true`, `InpGuardNewsPadSec = 300`).
   - **Lịch làm mới bắt buộc:** Ngày `25` của tháng cuối mỗi quý (`Tháng 3, 6, 9, 12`), cập nhật lịch quý tới, chạy đối soát kiểm thử, và chép đè đồng loạt lên mọi VPS đang hoạt động.
4. **Cổng Tiền Khai Trương `The5ers Terms §11`:**
   - Gửi email xác nhận quyền vận hành EA độc quyền trước khi mua vé `39 USD` theo mẫu chuẩn trong [THE5ERS-LAUNCH-AND-TERMS11-EMAIL.md](../../tooling/ai-engines/exports/deployment_kit/the5ers_kit/THE5ERS-LAUNCH-AND-TERMS11-EMAIL.md) (cam kết sở hữu mã nguồn white-box riêng, không dùng chung tín hiệu bên thứ ba, giữ đệm tin đỏ `±5` phút chặt hơn mức `±2` phút của hãng). Lưu email phản hồi chấp thuận vào hồ sơ lưu trữ cá nhân.

---

## 2. Lịch Trình Giám Sát 14 Ngày Free Trial (`Day-1 → Day-14`)

- **Ngày 1 (24 giờ Dry-Run kiểm tra khớp nối):**
  - Chạy toàn bộ `9` biểu đồ ở chế độ `DryRun` hoặc tài khoản Free Trial `1515343166`, xác nhận `naqex_heartbeat.json` cập nhật mỗi `<= 60` giây, `kill_switch = false`, `orphan_no_sl = 0`, và không có lỗi `4756 / 10018 / 10019` trong tab `Experts`.
- **Ngày 2 → Ngày 13 (Kiểm tra 5 phút/ngày — Cấm nhìn bảng giá theo phút):**
  - Mỗi tối sau `21:55 UTC` (khi mọi vị thế intraday đã đóng sạch trước giờ rollover `21:55–22:15 UTC`), chạy đúng **2 lệnh kiểm toán cục bộ**:
    1. [daily_ops_briefing.py](../../tooling/ai-engines/quant_factory/daily_ops_briefing.py) để chấm điểm sức khỏe vận hành (`0–100`).
    2. [prop_challenge_tracker.py](../../tooling/ai-engines/quant_factory/prop_challenge_tracker.py) với `--profile ftmo_swing_10k` để đọc `naqex_exec_audit.csv`, kiểm tra `swap == 0`, khóa tin đỏ `±300s`, và trượt giá trung bình từng động cơ.
  - Nếu gặp sai lệch khớp lệnh, tra ngay bảng phân tách *lỗi sàn vs lỗi bot* trong [mt5-live-execution-gaps-and-tca.md](../topics/mt5-live-execution-gaps-and-tca.md). **Tuyệt đối không đóng lệnh tay giữa phiên** (trừ tình huống khẩn cấp ở Mục 4).
- **Ngày 14 (Phán quyết Chuyển đổi Sang Trả Phí — `PASS_TO_PAID` vs `EXTEND_SHADOW` vs `HALT_AND_FIX`):**
  - Chỉ được nâng cấp sang tài khoản trả phí khi `prop_challenge_tracker.py` trả về **`PASS_TO_PAID`** đồng thời thỏa:
    - `>= 4` ngày giao dịch hợp lệ (FTMO) và `0` vi phạm Daily Loss (`< 3,5%` Amber brake) / Max Loss (`< 7,0%` Red brake).
    - `nonzero_swap_count == 0`, `overnight_hold_count == 0`, `rollover_blackout_count == 0`, `red_news_guard_violations == 0`.
    - `0` động cơ (`E1..E7, S6`) có trượt giá trung bình 14 ngày vượt `1,5×` ngân sách M1 backtest.

---

## 3. Quy Trình Nâng Cấp Lên Trả Phí (`DUAL_2FIRM_STAGGER_42D + P1_Balanced`)

Tuân thủ chính xác kiến trúc tối ưu đã chứng minh trên 5.000 đường mô phỏng tại [MULTI-PROP-SCALING-AND-BLACKSWAN-STRESS-20261124.md](../../planning/research/MULTI-PROP-SCALING-AND-BLACKSWAN-STRESS-20261124.md) và lộ trình [naqex-master-roadmap-2026-2027.md](naqex-master-roadmap-2026-2027.md):

1. **Ngày `T = 0` — Khai Trương Tài Khoản #1 (`The5ers High Stakes 5K`, phí `39 USD`):**
   - Áp hồ sơ **`P1_Balanced`** (`4,0×` ở Step 1, `2,5×` ở Step 2, hạ cứng về `1,0×` ngay khi lên Funded; `SYMCAP_100 = 1,0%`, khóa tin đỏ `±300s`).
   - Theo dõi bằng `--profile the5ers_hs_5k`: nhớ quy tắc đặc thù của The5ers là cần tối thiểu **`3` ngày lãi riêng biệt, mỗi ngày `>= +0,50%` số dư đầu (`>= +25,0 USD` trên tài khoản `5k USD`)**.
2. **Ngày `T + 42` Phiên Giao Dịch (~2 Tháng Sau) — Khai Trương Tài Khoản #2 (`FTMO Standard 10K BF-25%` hoặc `FTMO Swing 10K`):**
   - **Tại sao bắt buộc giữ độ trễ `+42` phiên?** Mở cùng ngày với `P1_Sprint` đẩy xác suất cháy kép đồng thời (`Double-Fail`) lên **`24,1%`** (nguy cơ cháy quỹ phí `1,8%` ở ngân sách `500 USD`); giữ độ trễ **`+42` ngày + `P1_Balanced`** cắt **Double-Fail xuống chỉ còn `3,0%`** và nguy cơ cháy quỹ phí xuống **`0,4%`** (`0,0%` ở ngân sách `1.500 USD`).
   - Ngay khi tài khoản #1 lên Funded và rút payout đầu tiên, chuyển dòng tiền vào sổ kế toán 3-Bucket ([treasury_ledger.py](../../tooling/ai-engines/quant_factory/treasury_ledger.py)): `30%` quỹ dự phòng phí (trần `5×` vé -> tràn `100%` sang Own-Book), `50%` Sổ Vốn Riêng, `20%` VPS & dự phòng thuế.

---

## 4. Sổ Tay Ứng Cứu Khẩn Cấp (`Emergency Runbook` — Fail-Closed)

Chỉ được phép can thiệp tay khi xảy ra **1 trong 4 sự cố kỹ thuật cấp độ ĐỎ** sau đây:

| Sự cố Khẩn cấp | Dấu hiệu Nhận diện | Thao tác Ứng cứu Tức thì (Đúng Thứ tự) | Điều kiện Mở lại Hệ thống |
| :--- | :--- | :--- | :--- |
| **1. Vị thế Mồ côi Không SL (`orphan_no_sl > 0`)** | Báo động `[ORCH-ALERT]` / `daily_ops_briefing` `FAIL` (`score <= 40`) | (1) Tắt nút `Algo Trading` trên MT5; (2) Kiểm tra vé lệnh mồ côi trên tab `Trade`; (3) Gắn ngay SL bằng `0,75 ATR` (hoặc đóng thị trường nếu đã vượt lỗ `1,0R`); (4) Lưu log `Experts` & `Journal`. | Tìm ra nguyên nhân gốc (lỗi kết nối/giới hạn `STOPLEVEL`), sửa và test lại trên Demo trước khi bật lại. |
| **2. Mất Kết nối Sàn / Treo VPS (`HbAge > 180s`)** | Watchdog gửi cảnh báo mất nhịp tim (`-StaleAfterSec 180`) hoặc `terminal_connected = false` | (1) Đăng nhập MT5 Mobile (chỉ dùng xem & đóng khẩn cấp, không vào lệnh tay); (2) Kiểm tra xem có vị thế mở sắp chạm rollover `21:55 UTC` không; (3) Nếu sát rollover mà VPS chưa hồi phục, đóng phẳng vị thế mở qua Mobile để bảo toàn `swap = 0`. | Khởi động lại VPS/terminal, xác nhận `naqex_heartbeat.json` nhảy nhịp đều và `GlobalVariable` `DAYEQ` khôi phục đúng. |
| **3. Kích hoạt Global Kill-Switch (`kill_switch = true`)** | Lỗ ngày chạm giới hạn nội bộ (`2,5%–3,5%`) hoặc lỗ tổng chạm phanh Đỏ (`7,0%`) | **KHÔNG ĐƯỢC tắt Kill-Switch để đánh gỡ!** Kiểm tra `prop_challenge_tracker.py` xác nhận toàn bộ vị thế đã đóng phẳng; dừng giao dịch phần còn lại của ngày (hoặc cả tuần nếu chạm phanh Đỏ `7,0%`). | Chờ sang ngày giao dịch mới sau khi hoàn tất rà soát nhật ký lỗi; tuyệt đối không nâng lot để gỡ lỗ. |
| **4. Vi phạm Swap != 0 hoặc Trượt Giá `> 1,5×` M1** | `prop_challenge_tracker.py` trả về **`HALT_AND_FIX`** (Rule 4 hoặc Rule 5) | (1) Tắt riêng EA bị gắn cờ (không cần tắt các EA xanh còn lại nếu lỗi cục bộ); (2) Đối chiếu giờ đóng lệnh với múi giờ DST máy chủ sàn (`UTC+2` vs `UTC+3`); (3) So sánh spread log tại thời điểm khớp. | Vá lệch múi giờ / bộ lọc spread tối đa (`InpGuardMaxSpreadPts`), xác minh `0` vi phạm trên Demo rồi mới kích hoạt lại. |

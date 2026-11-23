# Current context — Naqex Workspace

`23/11/2026` · `WORK: ACTIVE/PARTIAL | REVIEW: REVIEWED-PARTIAL | DOC: COMPACTED-RESUMABLE`

`RESEARCH: ENGINE_1_NEEDS_PARTNER · BASELINE: USDJPY PASS 7B/8 · HOLDOUT >= 01/01/2025 LOCKED · PROP: NOT_QUALIFIED`

## 1. Mục tiêu chính & Khung vận hành

- **North Star:** Xây dựng hệ thống giao dịch tự động đa động cơ (white-box, zero-grid/martingale, kiểm chứng trên dữ liệu Bid/Ask M1/Tick với phí thực tế) đủ bằng chứng vượt **FTMO 2-Step** và tạo dòng tiền Reward bền vững cho một người vận hành ([Lộ trình prop](research/PROP-SYSTEM-ROADMAP.md)).
- **Tỷ trọng mục tiêu hiện hành:** **80% FTMO Swing (`10k/25k`, đòn bẩy `1:30`, giữ qua đêm/cuối tuần/tin mạnh)** và **20% đối chứng FTMO Standard (`50k`, `1:100`)**, bám đúng biểu phí đã đo từ Demo (`36f1535` Standard, `8fd77ef` Swing: FX `$5/lot`, `US500.cash` `$0/lot`, swap có dấu + triple-swap đúng ngày).
- **Ràng buộc an toàn bất biến:** Khóa cứng Holdout từ `01/01/2025` (`NATIVE_FTMO_HOLDOUT_LOCK.json`), `OrderSend = 0`, không mở MT5/đọc `.env`, không tự sửa global config, không đụng pin `projects/trader` hay WIP `projects/vi-dubber`.
- **Điều phối thống nhất:** Antigravity tiếp quản cả vai trò điều phối lẫn thực thi trên `Naqex/workspace` (thay thế quy trình copy-paste giữa Gemini Web / Codex / chat Astra cũ). Kho săn ý tưởng bên ngoài `D:\ANNAM\strategy-intel` giữ **Air-Gap tuyệt đối** (chỉ chuyển giao đặc tả toán học thuần túy, không import file hay trộn số liệu `>= 2025`).

## 2. Trạng thái nghiên cứu hiện hành (Pass 5 → Pass 20)

- **Pass 20 (23/11/2026) — Pháp y H4/M1 Positive-Swap Carry-Trend (8 cặp) & Ghép 3 Động Cơ (`1531/1531` tests PASS):** Xác nhận độ khớp H4 vs M1 (`USDJPY +14,68R` vs `+15,18R`; `EURUSD -1,58R` vs `-0,06R`), nhưng **bác bỏ dứt điểm nhánh Donchian Carry-Trend** (`0/12` ô `NON_JPY_4` và `0/12` ô `ALL_8_JPYCAP1` dương cả A&B; trượt timing null `p = 0,14–0,97`; ghép Prague-reset vào lõi Pass 17 không cải thiện được Calmar `0.65`). Giữ lõi 2 động cơ `USDJPY` Pass 17; ứng viên Stage-0 còn lại cần tải M1 Bid/Ask để kiểm thật là **`GBPJPY` (`EXP_DAILY_OPEN_080`)** hoặc mở dữ liệu **`US100.cash` / `GER40`**. [Báo cáo Pass 20](research/PASS20-POS-SWAP-CARRY-TREND-3ENGINE-20261123.md) · [Protocol `54cb069`](research/PASS20-POS-SWAP-CARRY-TREND-3ENGINE-PROTOCOL-20261123.md).
- **Pass 19 (23/11/2026) — `US500` Overnight (FTMO Swap) · Clean-Room `SuperTrend(10,3)` · Stage-0 Cặp Chéo Yên & Positive-Carry (`1528/1528` tests PASS):** `US500` qua đêm (`0/6` FTMO vì phí Swap `-1,38 USD/đêm` hút `-596..-2.003 USD`, dù `IBS` đạt `+9,40R` ở Exness Swap-Free); Clean-Room `SuperTrend(10,3)` rớt sạch `0/5` (`-41R..-77R`); Stage-0 H4/D1 (hiệu chuẩn khớp `CONTROL_USDJPY` `+24,85R`) chỉ ra 2 ứng viên đáng đẩy lên Pass 20: **`GBPJPY` (`EXP080_H4 +9,28R`, `5/7` năm, `rJPY=0,23`)** và nhánh **Positive-Swap Carry-Trend `DON20_POS`** dẫn đầu bởi **`USDCAD` (`+8,07R`, `6/7` năm dương, A `+3,4`/B `+4,7`, DD `3,4R`, `rJPY=-0,003`)** cùng rổ 6 cặp thu `+$10.435` Swap dương / `+28,7R`. [Báo cáo Pass 19](research/PASS19-US500-OVERNIGHT-SUPERTREND-YENCROSS-20261123.md) · [Protocol `87c5a3f`](research/PASS19-US500-OVERNIGHT-SUPERTREND-YENCROSS-PROTOCOL-20261123.md).
- **Pass 18 (23/11/2026) — Sàng lọc 14 chiến lược học thuật & mã nguồn mở ngoài `USDJPY` (`swap = 0`, BH FDR `m = 14`):** `0/14` Tier 1, `0/14` Tier 2, `14/14 TIER_3_DEAD_NO_EDGE` (`1.524/1.524` tests PASS). Các hiệu ứng học thuật ngắn hạn (`JFE` GHLZ `-55,2R`, Gap Fade `-76,6R`, IBS trong ngày `-49,7R`, `JoF 2024` WMR Fix `EURUSD/GBPUSD` `-46R..-59R` dù hơn Fade `+17R`) và `MQL5 CodeBase NR4` (`-9,7R..-19,2R`) đều bị spread/phí CFD nuốt hoặc suy giảm giai đoạn `2018–2024`; `XAU_LBMA_PM_DRIFT` chỉ hòa vốn Base (`-0,01R`, Stress `-3,50R`). Giữ lõi 2 động cơ `USDJPY` Pass 17. [Báo cáo Pass 18](research/PASS18-OPENSOURCE-NON-USDJPY-ENGINE3-20261123.md) · [Protocol `467a028`](research/PASS18-OPENSOURCE-NON-USDJPY-ENGINE3-PROTOCOL-20261123.md).
- **Pass 17 (23/11/2026) — Pháp y M1 Floating Equity `EXP_DAILY_OPEN_080 USDJPY` & kiểm chéo `GBPUSD`/`US500`:**
  - **`EXP_DAILY_OPEN_080 USDJPY` xác nhận là Engine #2 thật (Native Tick M1 Bid/Ask, `swap = 0`):** Sống qua cả 3 bậc phí kể cả Stress `+1,00 pip` (`+29,54R`, DD nổi `7,7R`), **`12/12` ô 2D tham số dương cả Cụm A & B**. Ghép cùng Engine #1 Tokyo-box (`PORT_INV_DD_075`, Prague reset) trên Swing 10k/25k & Standard 50k: **`+3,51–3,70%/năm`**, **Peak DD giảm `9,08% → 5,45%` (`-40%`), underwater giảm một nửa `41,2 → 19,9–20,6` tháng, Daily Loss `0,74%`, Calmar tăng gấp đôi `0,32 → 0,64`** (`0` lỗi margin).
  - **Giới hạn trung thực cần xử lý tiếp:** (a) Lãi tập trung mạnh ở `BUY` (`+37,28R`) vs `SELL` (`-2,53R`); (b) Tốc độ `3,5–3,7%/năm` đạt chuẩn `TIER_2_PERSONAL_VAULT` nhưng chưa đủ ngưỡng `8–12%/năm` của FTMO Challenge → cần Engine #3 trên tài sản **ngoài `USDJPY`**.
  - **Kiểm chéo `GBPUSD` & `US500`:** `US500` trượt cả 4 mức (`-10R..-18R`, `TIER_3`); `GBPUSD` chỉ có `1,20 ATR` đạt `TIER_2` (`+4,95R`, `5/7` năm). [Báo cáo Pass 17](research/PASS17-USDJPY-EXPANSION-FORENSIC-AND-CROSS-ASSET-20261123.md) · [Protocol `92808a4`](research/PASS17-USDJPY-EXPANSION-FORENSIC-AND-CROSS-ASSET-PROTOCOL-20261123.md).
- **Pass 16 (23/11/2026) — Phát hiện `EXP_DAILY_OPEN_080 USDJPY` & đóng sổ Source 1 `strategy-intel`:** `23/24` cặp H1 vào `TIER_3`, `VIR024 USDJPY` vào `TIER_2`; lưu [EXNESS-CONTRACT-SPECS-SNAPSHOT-20261123.json](research/EXNESS-CONTRACT-SPECS-SNAPSHOT-20261123.json). [Báo cáo Pass 16](research/PASS16-DUAL-TRACK-EXPANSION-AND-H1-CONTEXT-20261123.md).
- **Pass 15 (23/11/2026) — FTMO-Native Screen:** `0/7` Tier 1/2, nhưng phát hiện tín hiệu gốc `XAU_DAILY_OPEN_ATR` (`p=0,004`, `q=0,028`) dẫn thẳng tới đột phá Pass 16. [Báo cáo Pass 15](research/PASS15-FTMO-NATIVE-ENGINE2-20261123.md).
- **Pass 14 (23/11/2026) — Sàng lọc đồng loạt 13 chiến lược `"CHẤT"` còn lại từ `strategy-intel` (Hoàn tất 15/15 Top Leads · Phân loại 3 tầng):**
  - Chạy toàn bộ **52 cặp** (`13` chiến lược × `XAUUSD`/`EURUSD`/`GBPUSD`/`USDJPY`, ~10,3 triệu nến M1, `52.000` lượt MC Null + FDR) trong **`35,47s`** trên Hot M1 Cache SSD (`249,3 MB`).
  - **`TIER_1_FTMO_READY`: `0 / 52`** (chưa có ứng viên Top 15 nào đủ chuẩn ghép thi FTMO ngay).
  - **`TIER_2_PERSONAL_VAULT_PROVISIONAL_XAU`: `2 / 52`** (cất kho tài khoản riêng/Exness, cần xác nhận Tick Bid/Ask thật và lưu ý `FDR q = 0,416`):
    - `NEN006 XAUUSD` *(Inside bar + EMA200 D1, n=161)*: FTMO `+14,89R` (`A +4,5 / B +10,4`, `5/7` năm, DD `9,8R`) → Exness Swap-Free **`+30,30R`**; `p_g=0,016`, `4/4` ô ±30% dương cả A&B.
    - `IND026 XAUUSD` *(Ichimoku Chikou D1 Long, n=43)*: FTMO `+10,49R` (`A +5,8 / B +4,7`, `5/7` năm, DD `3,3R`) → Exness Swap-Free **`+19,70R`**; `p_g=0,014`, `3/3` ô ±30% dương cả A&B.
  - **`TIER_3_DEAD_NO_EDGE`: `50 / 52`** (cộng `NEN022`, `SEA003` từ Pass 13). [Báo cáo Pass 14](research/PASS14-STRATEGY-INTEL-TOP15-BATCH-20261123.md) · [Protocol `079ea0a`](research/PASS14-STRATEGY-INTEL-TOP15-BATCH-PROTOCOL-20261123.md).
- **Pass 13 (23/11/2026) — 3 nhánh song song (`ALL_THREE_TRACKS_REJECTED` · `ORB_ENGINE2_SEARCH_EXHAUSTED`):** `GBPUSD`/`EURUSD` M1 Sweep (`-275R..-511R`), `NEN022` Fakey H4 (`-25R..-75R`), `SEA003` XAUUSD TOM (Swap 3× ăn `60,1%`, `MC p=0,279` drift illusion), `US500 NY ORB` Explicit M1 (`-46,7R / -58,9R`, 1/7 năm dương → đóng dứt điểm họ ORB). [Báo cáo Pass 13](research/PASS13-TRIPLE-TRACK-ENGINE2-20261123.md).
- **Pass 12 (23/11/2026) — Pháp y `USDJPY`:** Loại lọc `Cost/Box <= 12%` (`USDJPY_COST_HYGIENE_NOT_RETAINED`); đoạn underwater `41,12` tháng (`2018–2022`) dồn ở `cost 6–12%`, `SELL`, khung `03:00–06:59 UTC`. [Báo cáo Pass 12](research/PASS12-US500-M1-ORB-AND-USDJPY-FORENSIC-20261120.md).
- **Engine #1 hiện có (`USDJPY` Tokyo-box OCO, Pass 5→8):** Edge thật trên 7 năm M1 Bid/Ask (`+10,92R/năm` Stress `+0,50 pip` mẫu mở rộng; `+11,74R/năm` mẫu chặt; đã đủ chuẩn `TIER_2_PERSONAL_VAULT` chạy solo, đang ở `ENGINE_1_NEEDS_PARTNER` để lên `TIER_1_FTMO_READY`). [Pass 8](research/PASS8-ANTIGRID-ENGINE2-SOURCING-AND-M1-GAP-AUDIT-20261120.md) · [Pass 7B](research/PASS7B-USDJPY-FULL-M1-FLOATING-EQUITY-20261120.md).
- **Nhánh đã đóng dứt điểm (không lặp lại):** Toàn bộ họ ORB (`GBPUSD` Pass 11, `EURUSD`/`US500 TOM` Pass 10, `US500 NY ORB` Pass 13), `GBPUSD`/`EURUSD` M1 static-box sweep (Pass 13), `13/15` mã `"CHẤT"` của `strategy-intel` vào `TIER_3_DEAD_NO_EDGE` (Pass 13–14), `EURJPY/EURUSD/GBPUSD` Tokyo-box (Pass 7), `XAUUSD` Asia breakout (Pass 6), MQL5 Round 1–2 (Pass 9), kho 1.029 EA cũ (V24–V26), OHLC Standard campaign (`OHLC_STANDARD_SEARCH_EXHAUSTED`).

## 3. Tài nguyên dữ liệu & Hạ tầng SSD/HDD (Zero-Network)

- **D: SSD Hot M1 Parquet Cache (`.runtime/hot-m1-cache/`, `249,3 MB`, đọc 12,56M nến trong `2,47s`, ổ D trống `151,4 GB`):** `USDJPY`, `GBPUSD`, `EURUSD`, `US500` (Native Bid/Ask `2018–2024`, SHA-verified) và `XAUUSD` (M1 Bid `2018–2024`, `native_Ask = false`). Đã dời `8,36 GB` CSV QDM cũ sang `E:\BACKUP-TRADINGWORKSPACE\qdm-legacy-exports\`.
- **E: HDD Cold Archive (`510 GB` trống):** Toàn bộ tick CSV gốc, log, kết quả cũ và D1 warm-up `2000–2017` (`swing-10k-20261120/development/`).

## 4. Hạ tầng, Phân loại 3 tầng & Hướng mở Pass 15

- **Chuẩn kiểm định mới (`validation-gates.md`):** Mọi lượt sàng lọc tự động gắn 3 tầng (`TIER_1_FTMO_READY` · `TIER_2_PERSONAL_VAULT` · `TIER_3_DEAD_NO_EDGE`) kèm MC Null + FDR + ±30% stability. Nợ CI duy nhất trước khi merge lên `main`: file lịch sử `SWING-10K-...20261120.json` (`8fd77ef`, `1,28 MiB > 1 MiB` trần `check_anti_bloat.py`).
- **Đề xuất Pass 15 (tận dụng băng chuyền 35 giây trên Hot Cache SSD):**
  1. **Quét tiếp kho `strategy-intel`:** Lọc và chạy đồng loạt nhóm **`27` EA có luật rõ ràng (`REPLICABLE_RULE_SET`)** trong `ea-directory-2026` (35/45 EA là Trend-Following) + các mã **`M15/H1` đánh trong ngày (`swap = 0`)** trong 39 mã `"TÌNH HUỐNG"` của Source 1.
  2. **Thiết kế Engine #2 tối ưu riêng cho cấu trúc phí FTMO:** `XAUUSD` đánh sóng London–NY **đóng trong ngày (`swap = 0`)** và/hoặc FX **thuận chiều Swap dương FTMO** (`USDJPY` Long `swap_long = +2,61` / `EURUSD` Short `swap_short = +0,28`).

## 5. Đường đọc theo phạm vi & Quyền hạn

| Phạm vi | Nguồn quyền hạn (Owner) |
|---|---|
| Chiến dịch nghiên cứu prop | [PROP-SYSTEM-ROADMAP](research/PROP-SYSTEM-ROADMAP.md) · [Chỉ mục research](research/README.md) · [Workflow](../tooling/ai-engines/STRATEGY-WORKFLOW.md) · [Validation gates](../.agents/skills/strategy-qualification/references/validation-gates.md) |
| Naqex Trader (code & UI) | [Product Plan](trader/PRODUCT-COMPLETION-PLAN.md) → [Entrypoint](trader/EXECUTION-ENTRYPOINT.md) → ledger run hiện hành |
| Vận hành Paperclip / Studio | [OPERATIONS](../tooling/ai-engines/OPERATIONS.md) · [AI Engines README](../tooling/ai-engines/README.md) |
| Context, skills & bảo trì | [CONTEXT-LIFECYCLE](CONTEXT-LIFECYCLE.md) · [SKILL-MAINTENANCE](../docs/development/SKILL-MAINTENANCE.md) · [WORKSPACE-MAINTENANCE](../tooling/WORKSPACE-MAINTENANCE.md) |
| Sản phẩm khác (`projects/`) | `AGENTS.md` / `README.md` của từng repo (`vi-dubber` WIP giữ nguyên, không chạm pin `trader`) |

## 6. Lịch sử & Khôi phục

- [Snapshot 23/11/2026 trước compact (V1–V26 + Pass 1–11, 88 KiB)](archive/2026-11-23-pass12-takeover/CURRENT-CONTEXT.before.md) · [MANIFEST](archive/2026-11-23-pass12-takeover/MANIFEST.json) (byte-exact gốc tại `CURRENT-CONTEXT.original.txt.gz`).
- [Snapshot 12/11/2026](archive/2026-11-12-strategy-e2e/CURRENT-CONTEXT.before.md) · [MANIFEST](archive/2026-11-12-strategy-e2e/MANIFEST.json).

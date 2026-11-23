# Current context — Naqex Workspace

`23/11/2026` · `WORK: ACTIVE/PARTIAL | REVIEW: REVIEWED-PARTIAL | DOC: COMPACTED-RESUMABLE`

`RESEARCH: ENGINE_1_NEEDS_PARTNER · BASELINE: USDJPY PASS 7B/8 · HOLDOUT >= 01/01/2025 LOCKED · PROP: NOT_QUALIFIED`

## 1. Mục tiêu chính & Khung vận hành

- **North Star:** Xây dựng hệ thống giao dịch tự động đa động cơ (white-box, zero-grid/martingale, kiểm chứng trên dữ liệu Bid/Ask M1/Tick với phí thực tế) đủ bằng chứng vượt **FTMO 2-Step** và tạo dòng tiền Reward bền vững cho một người vận hành ([Lộ trình prop](research/PROP-SYSTEM-ROADMAP.md)).
- **Tỷ trọng mục tiêu hiện hành:** **80% FTMO Swing (`10k/25k`, đòn bẩy `1:30`, giữ qua đêm/cuối tuần/tin mạnh)** và **20% đối chứng FTMO Standard (`50k`, `1:100`)**, bám đúng biểu phí đã đo từ Demo (`36f1535` Standard, `8fd77ef` Swing: FX `$5/lot`, `US500.cash` `$0/lot`, swap có dấu + triple-swap đúng ngày).
- **Ràng buộc an toàn bất biến:** Khóa cứng Holdout từ `01/01/2025` (`NATIVE_FTMO_HOLDOUT_LOCK.json`), `OrderSend = 0`, không mở MT5/đọc `.env`, không tự sửa global config, không đụng pin `projects/trader` hay WIP `projects/vi-dubber`.
- **Điều phối thống nhất:** Antigravity tiếp quản cả vai trò điều phối lẫn thực thi trên `Naqex/workspace` (thay thế quy trình copy-paste giữa Gemini Web / Codex / chat Astra cũ). Kho săn ý tưởng bên ngoài `D:\ANNAM\strategy-intel` giữ **Air-Gap tuyệt đối** (chỉ chuyển giao đặc tả toán học thuần túy, không import file hay trộn số liệu `>= 2025`).

## 2. Trạng thái nghiên cứu hiện hành (Pass 5 → Pass 13)

- **Pass 13 (23/11/2026) — 3 nhánh song song tìm Engine #2 (`ALL_THREE_TRACKS_REJECTED` · `ORB_ENGINE2_SEARCH_EXHAUSTED`):**
  - **Nhánh 1 (`GBPUSD` & `EURUSD` Intraday Liquidity Sweep & Reversal, M1 Bid/Ask cục bộ, `swap = 0`):** Cả 2 cặp rớt toàn diện ở `M1_Real_Stress_05` (`GBPUSD`: Stage-0 `-$37.302`, SL Flat `-275,5R / -335,1R`, `MC p = 0,705–0,778`; `EURUSD`: Stage-0 `-$15.751`, SL Flat `-275,4R / -352,1R`, `MC p = 0,418–0,442`; 6/6 ô lưới ổn định đều âm `-242R..-539R`).
  - **Nhánh 2 (Clean-Room Air-Gap từ `strategy-intel`):**
    - `NEN022` (Fakey H4 2 chiều): Rớt cả 3 tài sản ở mọi `RR ∈ {1,5; 2,0; 3,0}` và cả phí Base (`EURUSD -25,61R`, `GBPUSD -42,29R`, `XAUUSD -74,91R` ở `Swing RR2 Stress_Mid`, `MC p = 0,52–0,79`).
    - `SEA003` (`XAUUSD` Turn-of-Month, 83 chu kỳ `2018-01..2024-11`): Gross `+$42.023/lot` nhưng **FTMO Swap 3× thứ Tư (`53` đêm) ăn `-$25.270` (`60,1%`)**, cộng phí thực thi còn `+$8.248` (`Cụm B 2021–2024` âm `-$69`, MAE `-5,39%`, DD `$20.448`), và **Monte Carlo Null (`N=1000`) cho `gross p = 0,291 / net p = 0,279`** → bác bỏ (`SEA003_FAILED_RANDOM_ENTRY_NULL_DRIFT_ILLUSION`).
  - **Nhánh 3 (`US500 NY ORB` trên Sealed Explicit M1 Bid/Ask `2018–2024`, `1.316/1.351` lệnh):** Rớt dứt điểm ở `M1_Stress_High` (`-1.186/-1.246 pts`, SL `-46,66R / -58,89R`, chỉ 1/7 năm dương, `MC p = 0,072`, Fade `-238,6R`) → khép toàn bộ họ ORB (`ORB_ENGINE2_SEARCH_EXHAUSTED`).
  - [Báo cáo Pass 13](research/PASS13-TRIPLE-TRACK-ENGINE2-20261123.md) · [Protocol `62ef313`](research/PASS13-TRIPLE-TRACK-ENGINE2-PROTOCOL-20261123.md).
- **Pass 12 (23/11/2026) — Pháp y `USDJPY` & QDM `US500`:** QDM `USA500IDXUSD` bị HTTP 429 (`US500_M1_DATA_UNAVAILABLE`); `USDJPY` tái dựng đủ `1.228/1.437` lệnh, loại lọc `Cost/Box <= 12%` (`USDJPY_COST_HYGIENE_NOT_RETAINED`), xác định đoạn underwater `41,12` tháng (`2018–2022`) tập trung ở `cost 6–12%`, `SELL` và khung `03:00–06:59 UTC`. [Báo cáo Pass 12](research/PASS12-US500-M1-ORB-AND-USDJPY-FORENSIC-20261120.md).
- **Engine #1 hiện có (`USDJPY` Tokyo-box OCO, Pass 5→8):** Edge thật trên 7 năm M1 Bid/Ask (`+10,92R/năm` Stress `+0,50 pip` mẫu mở rộng; `+11,74R/năm` mẫu chặt), chạy đơn lẻ chậm (`~3,0%/năm` tại 0,30% risk, DD `9,08%`, underwater `21–41 tháng`). **Giữ làm baseline `ENGINE_1_NEEDS_PARTNER`.** [Pass 8](research/PASS8-ANTIGRID-ENGINE2-SOURCING-AND-M1-GAP-AUDIT-20261120.md) · [Pass 7B](research/PASS7B-USDJPY-FULL-M1-FLOATING-EQUITY-20261120.md).
- **Nhánh đã đóng dứt điểm (không lặp lại):** Toàn bộ họ ORB (`GBPUSD` Pass 11, `EURUSD`/`US500 TOM` Pass 10, `US500 NY ORB` Pass 13), `GBPUSD`/`EURUSD` M1 static-box sweep (Pass 13), `NEN022` Fakey H4 & `SEA003` XAUUSD TOM (Pass 13), `EURJPY/EURUSD/GBPUSD` Tokyo-box (Pass 7), `XAUUSD` Asia breakout (Pass 6), MQL5 Round 1–2 (Pass 9), kho 1.029 EA cũ (V24–V26), OHLC Standard campaign (`OHLC_STANDARD_SEARCH_EXHAUSTED`).

## 3. Tài nguyên dữ liệu M1 đã niêm phong sẵn trên ổ E (Zero-Network cho Pass 14)

- **Native Tick-derived M1 Bid/Ask (`2018–2024`, SHA-verified, `holdout_rows = 0`):** `USDJPY` (`pass7b`), `GBPUSD` (`pass11`), **`EURUSD` (`pass13`, 190M ticks → 2,61M nến M1)**, **`US500` Explicit M1 (`challenge-discovery4`, 2013–2024)**.
- **QDM M1 Bid (`2018–2024`, proxy spread, `native_Ask = false`):** **`XAUUSD` (`pass13`, 2,48M nến M1)**; kèm FTMO Demo H1/H4/D1 đủ 13 mã (`swing-10k-20261120`).

## 4. Hạ tầng, Hiệu năng & Hướng mở Pass 14

- **Hiệu năng & AI Env (23/11/2026):** `quant_test_suite.py` chạy **`1.514/1.514 PASS (0 skip)` trong `16,11s`** (`--workers 4`, lệch shard `1,07×`). Luật M1/Swap-3×/Null-Test/Air-Gap đã mã hóa vào `validation-gates.md` và chứng minh hiệu quả ngay tại Pass 13. Nợ CI duy nhất trước khi merge lên `main`: file lịch sử `SWING-10K-...20261120.json` (`8fd77ef`, `1,28 MiB > 1 MiB` trần `check_anti_bloat.py`).
- **Đề xuất Pass 14 (3 cơ chế thực sự trực giao với ORB & tránh bẫy Swap âm):**
  1. **`XAUUSD` Intraday Volatility-Breakout / London–NY Trend Continuation (`swap = 0`):** Tận dụng biên độ vàng lớn nhất sàn (tỷ lệ `cost/ATR` thấp) mà triệt tiêu 100% swap `-$56,56/đêm`.
  2. **FX Carry-Aligned Swing (`EURUSD` Short / `USDJPY`–`GBPJPY`–`AUDJPY` Long):** Dùng chính chiều **swap dương/trung tính** trên FTMO để tài trợ lệnh đa ngày thay vì bị swap ăn mòn.
  3. **Intraday Extreme-Deviation Mean-Reversion (`Z-score >= 2,0–2,5σ` / VWAP-Session) trên `US500` hoặc `EURUSD`/`GBPUSD`:** Tần suất thấp (`30–60` lệnh/năm, `cost/stop < 8%`) thay cho sweep nhiễu 90% số ngày.

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

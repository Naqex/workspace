# Current context — Naqex Workspace

`23/11/2026` · `WORK: ACTIVE/PARTIAL | REVIEW: REVIEWED-PARTIAL | DOC: COMPACTED-RESUMABLE`

`RESEARCH: ENGINE_1_NEEDS_PARTNER · BASELINE: USDJPY PASS 7B/8 · HOLDOUT >= 01/01/2025 LOCKED · PROP: NOT_QUALIFIED`

## 1. Mục tiêu chính & Khung vận hành

- **North Star:** Xây dựng hệ thống giao dịch tự động đa động cơ (white-box, zero-grid/martingale, kiểm chứng trên dữ liệu Bid/Ask M1/Tick với phí thực tế) đủ bằng chứng vượt **FTMO 2-Step** và tạo dòng tiền Reward bền vững cho một người vận hành ([Lộ trình prop](research/PROP-SYSTEM-ROADMAP.md)).
- **Tỷ trọng mục tiêu hiện hành:** **80% FTMO Swing (`10k/25k`, đòn bẩy `1:30`, giữ qua đêm/cuối tuần/tin mạnh)** và **20% đối chứng FTMO Standard (`50k`, `1:100`)**, bám đúng biểu phí đã đo từ Demo (`36f1535` Standard, `8fd77ef` Swing: FX `$5/lot`, `US500.cash` `$0/lot`, swap có dấu + triple-swap đúng ngày).
- **Ràng buộc an toàn bất biến:** Khóa cứng Holdout từ `01/01/2025` (`NATIVE_FTMO_HOLDOUT_LOCK.json`), `OrderSend = 0`, không mở MT5/đọc `.env`, không tự sửa global config, không đụng pin `projects/trader` hay WIP `projects/vi-dubber`.
- **Điều phối thống nhất:** Antigravity tiếp quản cả vai trò điều phối lẫn thực thi trên `Naqex/workspace` (thay thế quy trình copy-paste giữa Gemini Web / Codex / chat Astra cũ). Kho săn ý tưởng bên ngoài `D:\ANNAM\strategy-intel` giữ **Air-Gap tuyệt đối** (chỉ chuyển giao đặc tả toán học thuần túy, không import file hay trộn số liệu `>= 2025`).

## 2. Trạng thái nghiên cứu hiện hành (Pass 5 → Pass 12)

- **Pass 12 (23/11/2026) — US500 NY ORB M1 & Pháp y USDJPY:**
  - **Track 1 (`US500 NY ORB` qua QDM):** `US500_M1_DATA_UNAVAILABLE`. QDM CLI `125.2692` (`USA500IDXUSD_PASS12_QUARANTINE`) gặp `HTTP 429` lặp lại ngay ở `2011.09–2011.10` qua 3 lượt thử (20/11 & 23/11) vì `action=update` không nhận `datefrom`; 0 bản ghi 2018–2024 vào QDM, chưa ra phán quyết kinh tế (không tự thay bằng cache Dukascopy cũ ngoài protocol).
  - **Track 2 (`USDJPY` Tokyo-box M1, 1.437 lệnh Stress +0,50 pip):** `USDJPY_COST_HYGIENE_NOT_RETAINED`. Tái dựng khớp tuyệt đối Pass 7B/8 (`1.228` lệnh / `1.334` ngày mẫu chặt; `1.437` lệnh / `1.564` ngày mẫu mở rộng). Cổng `Cost/Box <= 12%` tăng net mẫu chặt (`+11,74 → +13,03R/năm`) nhưng làm giảm Cụm A mẫu mở rộng (`+6,50 → +1,47R/năm`, cả kỳ `+10,92 → +9,51R/năm`) và tăng DD Swing 10k 0,30% (`9,08% → 9,22%`). Giải phẫu 4 trục chỉ ra mẫu mở rộng có đoạn underwater dài nhất **41,12–41,16 tháng** (`20/12/2018 → 25/05/2022`), đỉnh DD rơi vào `20/12/2018 → 30/01/2020`, chủ yếu từ nhóm phí `6–12%` (`−23,10R`) và khung vào sớm `03:00–06:59 UTC` (`81,54R / 102,98R` lỗ gộp). **Giữ USDJPY gốc làm Engine #1 baseline, gác variant 12%.**
  - [Báo cáo Pass 12](research/PASS12-US500-M1-ORB-AND-USDJPY-FORENSIC-20261120.md) · [Protocol `fdef13d`](research/PASS12-US500-M1-ORB-AND-USDJPY-FORENSIC-PROTOCOL-20261120.md).
- **Engine #1 hiện có (`USDJPY` Tokyo-box OCO, Pass 5→8):** Edge thật trên 7 năm M1 Bid/Ask (`+10,92R/năm` Stress `+0,50 pip` trên mẫu mở rộng; `+11,74R/năm` mẫu chặt), nhưng chạy đơn lẻ quá chậm (`~3,0%/năm` tại 0,30% risk, peak DD `9,08–9,34%`, underwater `21–41 tháng`). **Cần Engine #2 khác bản chất để bù chuỗi thua.**
  [Pass 8](research/PASS8-ANTIGRID-ENGINE2-SOURCING-AND-M1-GAP-AUDIT-20261120.md) · [Pass 7B](research/PASS7B-USDJPY-FULL-M1-FLOATING-EQUITY-20261120.md).
- **Nhánh đã loại / đóng dứt điểm (không lặp lại):**
  - `GBPUSD London ORB` (`GBPUSD_FAILED_M1_CHECK` ở [Pass 11](research/PASS11-GBPUSD-M1-TRUTH-AND-TWO-ENGINE-PORTFOLIO-20261120.md)): H1 `+181,24R` sập về `−7,45R` trên M1 Bid/Ask do 172 ngày hai cạnh (`−158,17R`) → khóa luật **Straight-to-M1** cho mọi pending stop trong ngày.
  - `EURUSD London ORB`, `US500 TOM` (swap 3× ăn `−$545` trên lãi gộp `+$521`, [Pass 10](research/PASS10-ENGINE2-INSTITUTIONAL-FLOW-STAGE0-20261120.md)); `EURJPY/EURUSD/GBPUSD Tokyo-box` ([Pass 7](research/PASS7-USDJPY-FULL-M1-EQUITY-AND-FX-SCOUT-20261120.md)); `XAUUSD` Asia breakout ([Pass 6](research/PASS6-USDJPY-HIRES-AND-XAUUSD-PORTFOLIO-20261120.md)).
  - MQL5 public signals Round 1 & 2 (`12/14` hồ sơ giấu Grid/Martingale, 0/6 Round 2 đạt chuẩn Clean-Room, [Pass 9](research/PASS9-ENGINE2-ROUND2-AUDIT-AND-DNA-20261120.md)); toàn bộ kho 1.029 EA cũ (V24–V26); OHLC Standard campaign (`OHLC_STANDARD_SEARCH_EXHAUSTED`, [Bottleneck 2](research/BOTTLENECK2-ASYMMETRIC-PIVOT-20261119.md)); `BASE_GUARD` giữ làm đối chứng `NOT_QUALIFIED`.

## 3. Tài nguyên dữ liệu sẵn trên đĩa (Zero-Network cho Pass 13)

- **QDM Tick Bid/Ask cục bộ (2003–2026, chỉ được xuất UTC `2018–2024`):** `USDJPY_PASS7B_QUARANTINE` (517M ticks), `GBPUSD_PASS11_QUARANTINE` (526M ticks), `EURUSD_TICK_TW` (518M ticks).
- **QDM M1 cục bộ:** `XAUUSD_TW` (7,97M M1), `EURUSD_TW` (8,76M M1).
- **Dukascopy Explicit M1 Bid/Ask đã niêm phong (kênh cũ, cần protocol riêng nếu tái dùng):** `us500-long-explicit-source-v1` (2013–2024 trên ổ E).

## 4. Hạ tầng, Hiệu năng & Việc kế tiếp (Pass 13)

- **Hiệu năng & AI Env (23/11/2026):** `quant_test_suite.py` tối ưu LPT sharding + `--indexed-imports` (1.509→1.511 tests/0 skip, `--workers 4`: `30,50s → 17,01s`, nhanh gấp `1,79×`). Cập nhật luật thực thi M1/Swap/Null-Test/Air-Gap vào `validation-gates.md` và `strategy-research`. Lưu ý nợ CI trước khi merge nhánh lên `main`: `SWING-10K-...20261120.json` (`8fd77ef`) nặng 1,28 MiB vượt trần 1 MiB của `check_anti_bloat.py` (không sửa file đã niêm phong SHA; cần quyết định grandfathering hoặc chuyển raw summary mới `< 500 KB`).
- **Đề xuất bước kế tiếp (Pass 13 — chờ owner chốt):** Dừng săn biến thể Session Breakout FX; chuyển thẳng sang họ **bù pha cho USDJPY** trên dữ liệu Bid/Ask đã có sẵn cục bộ:
  1. **GBPUSD / EURUSD Intraday Liquidity Sweep & Reversal** (khai thác trực tiếp hiện tượng 172 ngày whipsaw hai biên của Pass 11 trên 526M/518M QDM ticks cục bộ, `swap = 0`, 2 chiều + đối chứng `Fade`).
  2. **Clean-Room White-Box Reproduction từ `strategy-intel` (Air-Gap):** `NEN022` (Fakey H4 đảo chiều phá vỡ giả 2 chiều) và/hoặc đối chứng trung thực `SEA003` (XAUUSD Turn-of-Month có đủ Swap 3× FTMO + Monte Carlo Random-Entry Null Test).
  3. *(Tùy chọn)* Chốt dứt điểm `US500 NY ORB` bằng protocol riêng dùng `us500-long-explicit-source-v1` đã có sẵn trên đĩa thay cho QDM 429.

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

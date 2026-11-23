# Bản tin Điều hành Sống — Naqex One-Person Quant Pod (2026-11-24)

> **Trạng thái:** `IN_PROGRESS (Checkpoint #1 — Tầng 1, Tầng 6 & M7.1 đã kiểm chứng & push; Tầng 2–5 đang chạy song song)` · **Cập nhật lúc:** `2026-11-23 23:44 (+07)`
> **An toàn Fail-Closed:** `OrderSend = 0` · `Holdout 2025+ SEALED` · `0` file ổ đĩa bị xóa · `projects/quant-trading` & `projects/vi-dubber` nguyên vẹn.

---

## 1. Bảng điểm 8 Tầng · 26 Mốc (Cập nhật Sống)

| Tầng | Mốc | Trạng thái | Tóm tắt Kết quả Đã Kiểm chứng |
|---|---|---|---|
| **Tầng 1** | **M1.1 – M1.5** (`mql5-builder`) | **DONE (`@verifier #17`)** | Biên dịch thật **`9/9` `.ex5`** bằng MetaEditor64 build 6230 (**`0 errors, 0 warnings`**); `10/10` audit `0` cờ đỏ; `8/8` parity MQL5↔Python PASS; **`10` cấu hình / `90` file `.set`** đồng bộ hệ số M2.2 (`P1_Balanced 4.00x`, `P1_Sprint 4.75x`, `P2 2.50x`, `Funded_Safe 1.00x`) + Watchdog gọn local/VPS (`21/21` pytest PASS). |
| **Tầng 2** | **M2.1 – M2.3** (`risk-auditor`) | *Đang chạy & chờ QA* | M2.1 Red-Team 7 đòn đánh, M2.2 Dual-P1 EV Frontier 10k nhánh (`#7`), M2.3 Postmortem/Council đã hoàn thiện code — đang hoàn tất Tầng 5 trước khi `@verifier` duyệt. |
| **Tầng 3** | **M3.1 – M3.4** (`quant-rnd`) | *Xong dữ liệu, đang tổng hợp* | 50-coin Crypto Spot nhân quả sạch survivorship bias (`F4_4H_EMA_24_120_BTC`: Cl.A `+16,30% Sh 1,82`, Cl.B mù `+5,69% Sh 0,78`) + Funding Carry (`CARRY_BTC_ETH_CONS_2XBUF`: `0` thanh lý, Cl.B `+2,99% DD 0,29%`) đã xuất sang `.runtime/quant-pod-returns/` (`#8`). |
| **Tầng 4** | **M4.1 – M4.3** (`quant-rnd`) | *Đang chạy Pass 29–30* | M4.3 Macro ETF 18 năm (`2008–2026`) đã xong (`M5_VOL_PARITY_TREND_GUARD` Cl.B `+7,58% Sh 1,06 DD 7,77%`, `MACRO_50TSMOM_LS_50ALLWEATHER_TG` dương cả 3 khủng hoảng GFC/COVID/2022 — `#10`); đang chạy Pass 29–30 (chỉ kho Dev `< 2025-01-01`). |
| **Tầng 5** | **M5.1 – M5.3** (`risk-auditor`) | *Đang chạy* | M5.3 lịch tin đỏ mở rộng hết `2027` (`343` dòng UTC, `#14`) đã xong; đang chạy M5.1 Bộ phân bổ vốn 4 nhánh HRP/ERC & M5.2 Pod Dashboard. |
| **Tầng 6** | **M6.1 – M6.5** (`domain-research`) | **DONE (`@verifier #16`)** | Hoàn thành đủ **`6` cẩm nang Super-Indie tiếng Việt** trong `knowledge/topics/` + `alpha-hypothesis-ledger.md` + nâng cấp `brain_cli.py` (`0` broken links, `0` duplicate headings, `8/8` pytest PASS, `675` file / `4.334` đoạn). |
| **Tầng 7** | **M7.1** (`domain-research`) | **DONE (`@verifier #16`)** | Kiểm toán 100% chỉ đọc tại `planning/research/STORAGE-HYGIENE-AUDIT-20261124.md`: **`16,64 GB`** có thể dời an toàn sang `E:\BACKUP-TRADINGWORKSPACE\` bằng lệnh `robocopy` 1 dòng (`0` file bị xóa đêm nay). |
| **Tầng 7** | **M7.2 – M7.3** (`coordinator`) | *Chờ hoàn tất Tầng 2–5* | Chạy `system_doctor --mode full` + `projects/quant-trading` tests + chốt Bản tin cuối. |
| **Tầng 8** | **M8.1 – M8.2** (`quant-rnd` + `risk-auditor`) | *Sẵn sàng mở ngay sau Tầng 1–7* | Pass 31–32 săn động cơ Intraday trực giao trên kho Dev dưới giám sát Red-Team (`m_total_cap <= 40`, Holdout khóa cứng). |

---

## 2. Đường dẫn Triển khai MT5 Free Trial (Đã sẵn sàng ngay từ Checkpoint #1)

- **9 file `.ex5` đã biên dịch sạch (`0 errors, 0 warnings`):** `D:\ANNAM\TradingWorkspace\.runtime\mt5-compiled-ex5\`
- **Bộ `90` file `.set` (`10` cấu hình) + Watchdog + Hướng dẫn 5 bước:** [ACTIVATION-CARD-LOCAL-MT5.md](research/MT5-COMPILE-PARITY-AND-DEPLOYMENT-KIT-20261124.md) và `tooling/ai-engines/exports/deployment_kit/ACTIVATION-CARD-LOCAL-MT5.md`
- **Báo cáo Kiểm toán Ổ đĩa Chỉ đọc (`16,64 GB`):** [STORAGE-HYGIENE-AUDIT-20261124.md](research/STORAGE-HYGIENE-AUDIT-20261124.md)
- **6 Cẩm nang Super-Indie mới:** [mt5-live-execution-gaps-and-tca.md](../knowledge/topics/mt5-live-execution-gaps-and-tca.md), [capital-scaling-prop-to-own-book.md](../knowledge/topics/capital-scaling-prop-to-own-book.md), [market-microstructure-and-economic-edge-handbook.md](../knowledge/topics/market-microstructure-and-economic-edge-handbook.md), [trading-psychology-and-profit-giveback-playbook.md](../knowledge/topics/trading-psychology-and-profit-giveback-playbook.md), [ai-quant-engineering-frontier-2026.md](../knowledge/topics/ai-quant-engineering-frontier-2026.md), [alpha-hypothesis-ledger.md](../knowledge/topics/alpha-hypothesis-ledger.md).

*(Bản tin này sẽ tự động được cập nhật tiếp sau Checkpoint #2 khi Tầng 2–5 hoàn tất và Checkpoint #3 sau Tầng 8.)*

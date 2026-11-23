# Bản tin Điều hành Sống — Naqex One-Person Quant Pod (2026-11-24)

> **Trạng thái:** `IN_PROGRESS (Checkpoint #2 — TOÀN BỘ Tầng 1–7 đã kiểm chứng 100% & push lên Git; đang chạy Tầng 8 Pass 31–32)` · **Cập nhật lúc:** `2026-11-23 23:55 (+07)`
> **An toàn Fail-Closed:** `OrderSend = 0` · `Holdout 2025+ SEALED` (`holdout_rows_analysed = 0`) · `0` file ổ đĩa bị xóa · `projects/quant-trading` (`261 passed`, sạch Git) & `projects/vi-dubber` nguyên vẹn.

---

## 1. Bảng điểm 8 Tầng · 26 Mốc (Cập nhật Sống)

| Tầng | Mốc | Trạng thái | Commit SHA | Kết quả Chính Đã Kiểm chứng Độc lập (`@verifier`) |
|---|---|---|---|---|
| **Tầng 1** | **M1.1 – M1.5** (`mql5-builder`) | **DONE (`#17`)** | `e63036f` | Biên dịch thật **`9/9` `.ex5`** bằng MetaEditor64 build 6230 (**`0 errors, 0 warnings`**); `10/10` audit `0` cờ đỏ; `8/8` parity MQL5↔Python PASS; **`10` cấu hình / `90` `.set`** đồng bộ hệ số M2.2 + Watchdog gọn local/VPS (`21/21` pytest PASS). |
| **Tầng 2** | **M2.1 – M2.3** (`risk-auditor`) | **DONE (`#25`)** | *CP #2B* | Red-Team 7 đòn đánh: điểm gãy chi phí hòa vốn **`PORT_7E = 2,26×`**, **`PORT_9E = 2,23×`**, **`5/5`** khủng hoảng lịch sử đều dương; Đường biên EV `10.000` nhánh (`seed=20261124`) cho **`P1_Balanced_3to6m`** & **`P1_Sprint_1to3m`** qua FTMO & The5ers; Postmortem Engine + 6-Gate Research Council (`21/21` pytest PASS). |
| **Tầng 3** | **M3.1 – M3.4** (`quant-rnd`) | **DONE (`#22`)** | `07a3211` | **Crypto Spot sạch survivorship bias** (`50` coin Binance `1d`/`4h` 2019–2026 gồm cả coin delist `EOS/MKR/WAVES`): tách đúng `-6,6..-11,2 pp/năm` thiên lệch của rổ 5 coin cũ; ứng viên nhân quả `F4_4H_EMA_24_120_BTC` Cl.B mù `+5,69%` Sh `0,776` DD `9,72%` (`BM -38,99%`), full `DSR = 0,991`. **Funding Carry** `CARRY_BTC_ETH_CONS_2XBUF` (`2x` buffer, `0` thanh lý qua FTX 2022) Cl.A `+7,69%` DD `0,95%` / Cl.B `+2,99%` DD `0,29%`. Submodule `projects/quant-trading` khỏe (`261 passed`). |
| **Tầng 4** | **M4.1 – M4.3** (`quant-rnd`) | **DONE (`#22`)** | `07a3211` | **Macro ETF 18 năm (`2008–2026`)**: `M5_VOL_PARITY_TREND_GUARD` Cl.B mù `+7,58%` Sh `1,063` DD `7,77%` `BH q = 0,0062` `DSR = 0,958`; `MACRO_50TSMOM_LS_50ALLWEATHER_TG` dương cả 3 khủng hoảng (`+7,98%` GFC, `+0,13%` COVID, `+4,67%` 2022). **Pass 29 Gold/Index (`0/24`)** & **Pass 30 FX Mở rộng (`0/24`)**: ghi nhận trung thực 100% kết quả âm, giữ nguyên `PORT_7E` không pha loãng. |
| **Tầng 5** | **M5.1 – M5.3** (`risk-auditor`) | **DONE (`#25`)** | `e63036f` + *CP #2B* | **Bộ phân bổ vốn 4 nhánh (`ERC_Capped35` trần 35% CEX)** OOS `2023–2024`: **CAGR `+5,95%`, Sharpe `2,25`, MaxDD `2,45%`, Calmar `2,43`**; **Pod Dashboard** (`.runtime/pod_dashboard.html`, tạo trong `0,17s`); **Lịch tin đỏ `2018–2027`** (`343` dòng UTC chính thức từ Fed/BLS/ECB/BoE/BoJ). |
| **Tầng 6** | **M6.1 – M6.5** (`domain-research`) | **DONE (`#16`)** | `e63036f` | Đủ **`6` cẩm nang Super-Indie tiếng Việt** trong `knowledge/topics/` + `alpha-hypothesis-ledger.md` + nâng cấp `brain_cli.py` (`0` broken links, `0` near-duplicate headings, `8/8` pytest PASS). |
| **Tầng 7** | **M7.1** (`domain-research`) | **DONE (`#16`)** | `e63036f` | Kiểm toán 100% chỉ đọc [STORAGE-HYGIENE-AUDIT-20261124.md](research/STORAGE-HYGIENE-AUDIT-20261124.md): **`16,64 GB`** có thể dời sang ổ `E:` bằng lệnh `robocopy` 1 dòng (`0` file bị xóa đêm nay). |
| **Tầng 8** | **M8.1 – M8.2** (`quant-rnd` + `risk-auditor`) | *Đang chạy* | — | **Pass 31** (Cross-Session Vol Compression, Conditioned Liquidity Sweep, NY Cross-Asset Spillover, trần `m_total <= 20`) & **Pass 32** (LOO Fragility + Causal Allocation Audit trên kho Dev `< 2025-01-01`). |

---

## 2. Kết quả Nổi bật (Tóm tắt Nhanh)

### A. So sánh 2 Hồ sơ Thi Quỹ Phase 1 (`10.000` nhánh, `seed=20261124`, Dev `2018–2024`)
- **`P1_Balanced_3to6m`** (hệ số hiệu dụng `4,00×` = `EA 1,50×` × `Orch 2,67×` → P2 `2,50×` → Funded `1,00×`): tỷ lệ trượt 1 lần `22,6%–23,8%`, trung vị P1 `2,0–2,7` tháng (cả 2 vòng `5,6–6,1` tháng), **EV ròng trên 1 USD phí thi:** **`+3,25×`** FTMO Swing, **`+4,08×`** FTMO Standard Sale `-25%`, **`+7,17×`** The5ers High Stakes (`8%+5%`).
- **`P1_Sprint_1to3m`** (hệ số hiệu dụng `4,75×` = `EA 1,50×` × `Orch 3,17×` → P2 `2,75×` → Funded `1,00×`): tỷ lệ trượt 1 lần `30,0%–33,4%`, trung vị P1 `1,6–2,0` tháng (cả 2 vòng `4,6–5,1` tháng), dòng tiền ròng 24 tháng cao nhất (`+738 USD` Swing / `+368 USD` The5ers HS).
- Chi tiết: [PROP-EV-FRONTIER-BALANCED-VS-SPRINT-20261124.md](research/PROP-EV-FRONTIER-BALANCED-VS-SPRINT-20261124.md) · [RED-TEAM-ADVERSARIAL-AUDIT-20261124.md](research/RED-TEAM-ADVERSARIAL-AUDIT-20261124.md).

### B. One-Person Quant Pod 4 Nhánh Trực giao (`ERC_Capped35`, OOS `2023–2024`)
- **4 nhánh độc lập:** FX Prop `PORT_7E` + Crypto Spot nhân quả `F4_4H_EMA` + Crypto Funding Carry `2×` buffer (trần `<= 35%` CEX) + Macro ETF 18 năm `M5_VOL_PARITY_TREND_GUARD`.
- **Hiệu suất tổng hợp OOS (`2023–2024`):** **CAGR `+5,95%`, Sharpe `2,25`, MaxDD `2,45%`, Calmar `2,43`**.
- **Dashboard tĩnh HTML sẵn sàng mở bằng trình duyệt:** `D:\ANNAM\TradingWorkspace\.runtime\pod_dashboard.html` · Chi tiết: [QUANT-POD-4SLEEVE-ALLOCATION-20261124.md](research/QUANT-POD-4SLEEVE-ALLOCATION-20261124.md).

### C. Đường dẫn Triển khai MT5 Free Trial (Sẵn sàng kéo thả trưa mai)
- **9 file `.ex5` (`0 errors, 0 warnings`):** `D:\ANNAM\TradingWorkspace\.runtime\mt5-compiled-ex5\`
- **Bộ `90` file `.set` (`10` cấu hình) + Watchdog + Hướng dẫn 5 bước:** `tooling/ai-engines/exports/deployment_kit/ACTIVATION-CARD-LOCAL-MT5.md` · [MT5-COMPILE-PARITY-AND-DEPLOYMENT-KIT-20261124.md](research/MT5-COMPILE-PARITY-AND-DEPLOYMENT-KIT-20261124.md)

*(Bản tin sẽ được chốt lần cuối sau khi Tầng 8 Pass 31–32 hoàn tất và `system_doctor --mode full` đạt 100% PASS.)*

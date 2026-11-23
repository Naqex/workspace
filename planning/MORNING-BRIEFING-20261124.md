# Bản tin Điều hành Sáng — Naqex One-Person Quant Pod (2026-11-24)

> **Trạng thái:** **`COMPLETE — 8/8 TẦNG · 26/26 MỐC HOÀN THÀNH & ĐÃ KIỂM CHỨNG ĐỘC LẬP`** · **Hoàn tất lúc:** `2026-11-24 00:08 (+07)`
> **An toàn Fail-Closed (100% nguyên vẹn):** `OrderSend = 0` · `Holdout 2025+ SEALED` (`holdout_rows_analysed = 0`) · `0` file ổ đĩa bị xóa · `projects/quant-trading` (`261 passed`, Git sạch `2035522`) & `projects/vi-dubber` nguyên vẹn · `AGENTS.md` toàn cục không đổi.

---

## 1. Bảng Điểm Toàn Bộ 8 Tầng · 26 Mốc

| Tầng | Mốc | Lane | Trạng thái & QA | Commit SHA | Thành quả Cốt lõi Đã Kiểm chứng |
|---|---|---|---|---|---|
| **Tầng 1** | **M1.1–M1.5** | `mql5-builder` | **DONE (`@verifier #17`)** | `e63036f` | Biên dịch thật **`9/9` `.ex5`** bằng MetaEditor64 build 6230 (**`0 errors, 0 warnings`**); `10/10` audit `0` cờ đỏ; `8/8` parity MQL5↔Python PASS; **`10` cấu hình / `90` `.set`** đồng bộ hệ số M2.2 + Watchdog gọn local/VPS (`21/21` pytest PASS). |
| **Tầng 2** | **M2.1–M2.3** | `risk-auditor` | **DONE (`@verifier #25`)** | `5932a6b` | Red-Team 7 đòn đánh: điểm gãy chi phí hòa vốn **`PORT_7E = 2,26×`**, **`PORT_9E = 2,23×`**, **`5/5`** khủng hoảng lịch sử đều dương; Đường biên Dual-P1 EV `10.000` nhánh (`seed=20261124`); Blameless Postmortem + 6-Gate Research Council. |
| **Tầng 3** | **M3.1–M3.4** | `quant-rnd` | **DONE (`@verifier #22`)** | `07a3211` | **Crypto Spot sạch survivorship bias** (`50` coin Binance `1d`/`4h`, gồm coin delist `EOS/MKR/WAVES`): tách rõ `-6,61..-11,21 pp/năm` thiên lệch cũ; `F4_4H_EMA` Cl.B mù `+5,69%` Sh `0,78` DD `9,72%` (`BM -38,99%`). **Funding Carry** `CARRY_BTC_ETH_2XBUF` (`0` thanh lý FTX `-0,07%`) Cl.B `+2,99%` DD `0,29%`. `projects/quant-trading` sạch (`261 passed`) + Promotion Spec. |
| **Tầng 4** | **M4.1–M4.3** | `quant-rnd` | **DONE (`@verifier #22`)** | `07a3211` | **Macro ETF 18 năm (`2008–2026`)**: `M5_VOL_PARITY_TG` Cl.B mù `+7,58%` Sh `1,063` DD `7,77%` (`BH q=0,0062`, `DSR 0,958`); `M1_AHL_TSMOM_LS` dương cả 3 khủng hoảng (`+15,9%` GFC, `+4,75%` COVID, `+12,2%` 2022). **Pass 29 (`0/24`)** & **Pass 30 (`0/24`)** ghi nhận trung thực 100% kết quả âm. |
| **Tầng 5** | **M5.1–M5.3** | `risk-auditor` | **DONE (`@verifier #25`)** | `e63036f` + `5932a6b` | **Phân bổ vốn 4 nhánh (`ERC_Capped35` trần 35% CEX)** OOS `2023–2024`: **CAGR `+5,95%`, Sharpe `2,25`, MaxDD `2,45%`, Calmar `2,43`**; **Pod Dashboard HTML** (`.runtime/pod_dashboard.html`, tạo `0,17s`); **Lịch tin đỏ `2018–2027`** (`343` dòng UTC chính thức Fed/BLS/ECB/BoE/BoJ). |
| **Tầng 6** | **M6.1–M6.5** | `domain-research` | **DONE (`@verifier #16`)** | `e63036f` + *CP #3* | Đủ **`6` cẩm nang Super-Indie tiếng Việt** trong `knowledge/topics/` + **`alpha-hypothesis-ledger.md` (`0` dòng `PENDING`, đủ Pass 1–32 & 4 nhánh)** + nâng cấp `brain_cli.py` (`0` broken links, `0` duplicate headings). |
| **Tầng 7** | **M7.1–M7.3** | `domain-research` + `coordinator` | **DONE (`@verifier #16` + Full Doctor)** | `e63036f` + *CP #3* | Kiểm toán chỉ đọc **`16,64 GB`** có thể dời sang ổ `E:` bằng `robocopy` 1 dòng (`0` file bị xóa); `system_doctor --mode full` **10/10 PASS**; bản tin điều hành hoàn chỉnh. |
| **Tầng 8** | **M8.1–M8.2** | `quant-rnd` + `risk-auditor` | **DONE (`@verifier #28` & `@risk-auditor #30`)** | *CP #3* | **Pass 31 (`0/18 REJECT_KILLED`)** qua `research_council.py` (tổng **`0/66`** false positives Pass 29–31!); **Pass 32** bóc trần **bẫy cắt tỉa LOO** (`V09` rơi `2,045 → 0,387`), xác nhận giữ nguyên **`PORT_7E`** số 1 sản xuất và ghi nhận **`V08_PORT9E_CAUSAL_ERC`** (`Cl.B Cal 1,596`) làm ứng viên v2 (kèm lưu ý trần `<= 0,75%` mã thưa lệnh). |

---

## 2. Những Con Số Quan Trọng Nhất Để Bạn Ra Quyết Định Lúc 12:00 Trưa

### A. Kết quả Kiểm toán Đối kháng (Red-Team 7 Đòn đánh trên `PORT_7E` & `PORT_9E`)
- **Độ dày biên an toàn chi phí:** `PORT_7E` chịu được gấp **`2,26×`** chi phí/trượt giá trước khi hòa vốn (`PORT_9E = 2,23×`; mạnh nhất `E3 GBPUSD 3,81×`, `E6 EURJPY 3,25×`; 3 động cơ cần để ý TCA sát khi chạy Demo là `E1 1,70×`, `E4 1,80×`, `S7 1,87×`).
- **Khớp lệnh xấu & Rung lắc tham số:** Sống dương qua trễ khớp `+1` phút bất lợi (`+3,57%/năm`), giá xấu nhất nến M1 (`+4,08%/năm`), `100%` dương dưới rung lắc `±20%` SL/ngưỡng, và **dương cả `5/5` khủng hoảng lớn** (`2018 Q4 +7,33%`, `COVID +10,20%`, `2022 +15,84%`, `SVB +0,16%`, `Yen Unwind 08/2024 +1,73%`).
- Chi tiết: [RED-TEAM-ADVERSARIAL-AUDIT-20261124.md](research/RED-TEAM-ADVERSARIAL-AUDIT-20261124.md).

### B. Đường biên 2 Cấu hình Thi Quỹ Phase 1 (`10.000` nhánh, `seed=20261124`)

| Cấu hình P1 → P2 → Funded | Hệ số hiệu dụng (`EA × Orch`) | Tỷ lệ trượt 1 lần | Trung vị P1 / Cả 2 vòng | EV / 1 USD phí thi (FTMO Swing / BF-25% / The5ers HS) | Dòng tiền ròng 24 tháng (Swing / The5ers HS) |
|---|---|---|---|---|---|
| **`P1_Balanced_3to6m`** | `4,00×` (`1,50 × 2,67`) → `2,50×` → `1,00×` | `22,6%–23,8%` | `2,0–2,7m` / `5,6–6,1m` | **`+3,25×` / `+4,08×` / `+7,17×`** | `+631 USD` / `+321 USD` |
| **`P1_Sprint_1to3m`** | `4,75×` (`1,50 × 3,17`) → `2,75×` → `1,00×` | `30,0%–33,4%` | `1,6–2,0m` / `4,6–5,1m` | `+3,05×` / `+3,88×` / `+6,82×` | **`+738 USD` / `+368 USD`** |

- **Điểm sáng cực lớn:** **The5ers High Stakes (`8% + 5%`, phí rẻ)** cho **EV trên mỗi 1 USD phí thi cao nhất (`+7,17×`)**, trong khi **FTMO Standard có sale `-25%` (`+4,08×`)** vượt rõ FTMO Swing giá gốc (`+3,25×`) nhờ bộ lọc tin đỏ `±5m` đã được kiểm chứng giữ `>90%` lợi nhuận! Chi tiết: [PROP-EV-FRONTIER-BALANCED-VS-SPRINT-20261124.md](research/PROP-EV-FRONTIER-BALANCED-VS-SPRINT-20261124.md).

### C. One-Person Quant Pod 4 Nhánh Trực giao (Vốn Tự Có & Đa Nhánh)
- Tương quan giữa 4 nhánh chỉ nằm trong **`r = -0,035` đến `+0,149`**.
- **Bẫy HRP không ràng buộc đã được chặn kịp:** HRP thuần đổ `93%` vốn vào Funding Carry chỉ vì độ biến động thấp (`0,29%` DD) — rất nguy hiểm về rủi ro sập sàn CEX. Bản sản xuất **`ERC_Capped35` (trần `<= 35%` CEX)** đạt OOS `2023–2024` **CAGR `+5,95%`, Sharpe `2,25`, MaxDD `2,45%`, Calmar `2,43`**.
- Mở thẳng **Dashboard tĩnh HTML** trên trình duyệt: `D:\ANNAM\TradingWorkspace\.runtime\pod_dashboard.html` · Chi tiết: [QUANT-POD-4SLEEVE-ALLOCATION-20261124.md](research/QUANT-POD-4SLEEVE-ALLOCATION-20261124.md).

### D. Bài học Chống Overfit Đắt giá từ Pass 29–32 (Dev `< 2025-01-01`)
- Tổng `66` giả thuyết Intraday mới (`Pass 29: 24`, `Pass 30: 24`, `Pass 31: 18`) đều bị chặn sạch (`0/66` đạt) — chứng minh bộ cổng `research_council.py` + `Matched-Hold Null` không bịa alpha.
- **Pass 32 (Bẫy LOO Pruning):** Cắt bỏ 3 động cơ yếu nhất Cụm A (`E1, E6, S7`) đẩy Calmar Cụm A lên `2,045` nhưng làm **Calmar Cụm B mù sập về `0,387`** vì chính 3 động cơ đó lại kéo danh mục ở Cụm B! **Kết luận:** Giữ nguyên **`PORT_7E`** cho thực chiến; lưu `V08_PORT9E_CAUSAL_ERC` làm ứng viên v2 chờ sau `90` ngày Demo/Live.

---

## 3. Đường dẫn Nhanh & 3 Quyết định Cho Bạn Lúc 12:00 Trưa

- **9 file `.ex5` đã biên dịch sạch (`0 errors, 0 warnings`):** `D:\ANNAM\TradingWorkspace\.runtime\mt5-compiled-ex5\`
- **Bộ `90` file `.set` (`10` cấu hình) + Hướng dẫn 5 bước + Watchdog:** `tooling/ai-engines/exports/deployment_kit/ACTIVATION-CARD-LOCAL-MT5.md`
- **6 Cẩm nang Super-Indie mới trong `knowledge/topics/`:** [MT5 Execution & TCA](../knowledge/topics/mt5-live-execution-gaps-and-tca.md) · [Capital Scaling 24m](../knowledge/topics/capital-scaling-prop-to-own-book.md) · [Market Microstructure Handbook](../knowledge/topics/market-microstructure-and-economic-edge-handbook.md) · [Profit Giveback Playbook](../knowledge/topics/trading-psychology-and-profit-giveback-playbook.md) · [AI-Quant Frontier 2026](../knowledge/topics/ai-quant-engineering-frontier-2026.md) · [Alpha Hypothesis Ledger](../knowledge/topics/alpha-hypothesis-ledger.md).

**3 quyết định bạn có thể chốt ngay khi thức dậy:**
1. **Khởi động FTMO Free Trial `14` ngày (`0 USD`) trên máy Windows hiện tại:** Làm theo 5 bước trong `ACTIVATION-CARD-LOCAL-MT5.md` (Ngày 1 chạy preset `FTMO_FreeTrial_DryRun` kiểm log sạch, từ Ngày 2 chuyển `FTMO_FreeTrial_Demo` thu dữ liệu TCA thật rồi chạy `postmortem_gen.py`).
2. **Dọn `16,64 GB` ổ D: sang ổ E: (tùy chọn):** Xem bảng phân rã và chạy đúng 1–4 lệnh `robocopy` đã kiểm thử PS 5.1 trong [STORAGE-HYGIENE-AUDIT-20261124.md](research/STORAGE-HYGIENE-AUDIT-20261124.md) (`0` file đã bị xóa đêm nay).
3. **Thăng hạng Nhánh #2 Crypto Spot vào `projects/quant-trading`:** Nếu bạn đồng ý kết quả `F4_4H_EMA_24_120_BTC` (`CRYPTO-SLEEVE2-SURVIVORSHIP-FREE-20261124.md`), chốt để triển khai theo đặc tả [CRYPTO-PROMOTION-SPEC-20261124.md](research/CRYPTO-PROMOTION-SPEC-20261124.md).

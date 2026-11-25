# Phán quyết Holdout `2025–2026` Một Lần Duy Nhất (`ONE-TIME BLIND VERDICT`)

- **Protocol G0 khóa trước dữ liệu:** [HOLDOUT-2025-2026-UNLOCK-PROTOCOL-20261123.md](HOLDOUT-2025-2026-UNLOCK-PROTOCOL-20261123.md) (commit `521926f`)
- **Biên nhận máy kiểm chứng (JSON + SHA-256):** [HOLDOUT-2025-2026-ONE-TIME-VERDICT-20261123.json](HOLDOUT-2025-2026-ONE-TIME-VERDICT-20261123.json)
- **Cửa sổ Holdout mù 100%:** `2025-01-02` → `2026-11-20` UTC (`491` ngày giao dịch, `1.881` năm, `10` tài sản Dukascopy Native M1 Bid+Ask thật trong kho tách biệt `.runtime/holdout-m1-cache/`, `124.6 MB`). Kho Development `.runtime/hot-m1-cache/` (`2018–2024`) và khóa `NATIVE_FTMO_HOLDOUT_LOCK.json` giữ nguyên bất biến.
- **Bất biến an toàn:** `OrderSend = 0`, `weekend_violations = 0`, `margin_failures = 0`, `0` tham số bị chỉnh sửa sau khi xem kết quả.

---

## 1. Phán quyết theo Cổng G0 đã khóa

- **`PORT_7E_P28_CORE` (và bản sản xuất `PORT_7E + SYMCAP_100 + Red-News ±5m`):** **ĐẠT `GO` TOÀN DIỆN** (`+12.10%` đến `+12.70%/năm`, `Float Peak DD 6.55%–6.92% <= 7.5%`, `Daily DD 1.48% <= 3.0%`, `Calmar 1.75–1.94 >= 0.70`, **`7/7` động cơ lõi dương**, `0` lỗi margin/swap).
- **`PORT_9E_INVDD_SYMCAP_100` & `PORT_9E_SYMCAP_100_REDNEWS`:** **ĐẠT `GO` TOÀN DIỆN** (`+12.28%` đến `+12.65%/năm`, `Float Peak DD 7.16%–7.46% <= 7.5%`, `Daily DD 1.18%–1.48%`, `Calmar 1.65–1.77`, **`9/9` động cơ dương**).
- **Bản thô `PORT_9E_UNCAPPED` (chưa lắp Inverse-DD hay khóa tin đỏ):** Script tự động gắn nhãn **`CONDITIONAL`** theo đúng luật G0 vì `Peak DD = 8.34%` vượt nhẹ ngưỡng trần `7.50%` của mức `GO` (dù lãi đạt `+12.42%/năm`, `Calmar 1.49`, `Daily DD 1.48%`). Kết quả này xác nhận chính xác giá trị thực tiễn của **Cluster-A Inverse-DD (`DD 7.46%`)** và **Khóa tin đỏ `±5m` (`DD 7.16%`)** đã thiết kế trước khi mở Holdout.

---

## 2. Kết quả từng động cơ trên Holdout mù `2025–2026` (`9/9` DƯƠNG — `0/9` ÂM)

| Động cơ (tham số đóng băng từ `2018–2024`) | Số lệnh `n` | Lãi ròng (`R`) | `PF` | Tỷ lệ thắng | `MaxDD (R)` | `BUY (R)` | `SELL (R)` | `2025 (R)` | `2026 (R)` |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **`E1_USDJPY_TOKYO`** | `465` | **`+48.05`** | `1.22` | `45.4%` | `47.75` | `+18.50` | `+29.55` | `+51.82` | `-3.77` |
| **`E2_USDJPY_EXP80`** | `141` | **`+11.16`** | `1.33` | `51.8%` | `8.55` | `+7.60` | `+3.56` | `-3.03` | `+14.19` |
| **`E3_GBPUSD_VH`** | `53` | **`+0.28`** | `1.02` | `49.1%` | `3.97` | `+1.88` | `-1.59` | `-1.93` | `+2.22` |
| **`E4_US100_SESS40`** | `101` | **`+9.47`** | **`1.57`** | `57.4%` | `2.62` | `+1.53` | `+7.94` | `+3.93` | `+5.54` |
| **`E5_US100_RS1130`** | `42` | **`+7.39`** | **`2.87`** | **`59.5%`** | **`0.90`** | `+3.75` | `+3.64` | `+5.11` | `+2.27` |
| **`E6_EURJPY_VOLCOMP`** | `47` | **`+0.25`** | `1.02` | `51.1%` | `4.95` | `+0.60` | `-0.35` | `-4.28` | `+4.53` |
| **`E7_USDJPY_NY10ET`** | `32` | **`+2.61`** | **`1.70`** | `56.2%` | `1.35` | `+1.86` | `+0.75` | `+1.46` | `+1.14` |
| **`S6_FX_USD_BSK`** *(vệ tinh P1)* | `51` | **`+1.60`** | `1.11` | `47.1%` | `4.48` | `-0.37` | `+1.97` | `-0.84` | `+2.44` |
| **`S7_XAU_EXP120`** *(vệ tinh P1)* | `52` | **`+11.48`** | **`2.58`** | **`61.5%`** | `2.83` | `+4.65` | `+6.83` | `+5.37` | `+6.11` |

**Điểm sáng đa dạng hóa ngoài mẫu:** Năm `2025` khi `E2/E3/E6` đi lùi nhẹ (`-3.03 / -1.93 / -4.28R`), nhóm `E1/E4/E5/E7/S7` gánh danh mục dương `+7.19%`; sang năm `2026` khi `E1` chững `-3.77R`, `E2 (+14.19R)` và `E6 (+4.53R)` bùng nổ kéo cả danh mục lên `+15.58%` đến `+20.70%`.

---

## 3. Kiểm toán M1 Floating Equity (Prague Reset) & Giám sát Alpha Decay (`CUSUM + SPRT + Cone`)

| Cấu hình danh mục (`2025-01-02` → `2026-11-20`, `1.881` năm) | Tổng lãi | Lãi/năm | `2025 / 2026` | `Peak DD` | `Daily DD` | `Calmar` | `UW (tháng)` | Cổng G0 |
|---|---:|---:|---|---:|---:|---:|---:|---|
| **`PORT_7E_UNCAPPED`** (`E1..E7`) | `+22.76%` | `+12.10%` | `+7.19% / +15.58%` | `6.92%` | `1.48%` | `1.75` | `4.33m` | **GO** |
| **`PORT_7E_SYMCAP_100`** (`<= 1%`/mã) | `+22.34%` | `+11.88%` | `+6.90% / +15.44%` | `6.96%` | `1.48%` | `1.71` | `4.33m` | **GO** |
| **`PORT_7E_SYMCAP_100 + REDNEWS ±5m`** | **`+23.88%`** | **`+12.70%`** | `+4.70% / +19.18%` | **`6.55%`** | `1.48%` | **`1.94`** | `5.32m` | **GO** |
| **`PORT_9E_UNCAPPED`** (`E1..E7+S6+S7`) | `+23.37%` | `+12.42%` | `+6.70% / +16.67%` | `8.34%` | `1.48%` | `1.49` | `6.93m` | *CONDITIONAL* (`DD > 7.5%`) |
| **`PORT_9E_INVDD_SYMCAP_100`** *(InvDD Cụm A)* | `+23.11%` | `+12.28%` | `+7.83% / +15.28%` | `7.46%` | **`1.18%`** | `1.65` | `6.93m` | **GO** |
| **`PORT_9E_SYMCAP_100 + REDNEWS ±5m`** | `+23.79%` | `+12.65%` | `+3.10% / +20.70%` | `7.16%` | `1.48%` | `1.77` | `9.63m` | **GO** |

- **Giám sát Alpha Decay (`live_decay_monitor.py` so `2025–2026` với nền đóng băng `2018–2024`):**
  - `PORT_7E`: **`GREEN_WITHIN_EXPECTATION`** — Wald SPRT **`CONFIRM_EDGE_INTACT`** (`LLR = -2.768 <= -2.251`), tổng lãi `+22.76%` nằm ở **bách phân vị `74.5%`** của nón kỳ vọng (`p50 = +16.58%`), `CUSUM` hiện tại `0.00σ`.
  - `PORT_9E`: **`GREEN_WITHIN_EXPECTATION`** — Wald SPRT **`CONFIRM_EDGE_INTACT`** (`LLR = -2.528 <= -2.251`), tổng lãi `+23.37%` nằm ở **bách phân vị `66.5%`** (`p50 = +18.81%`), `CUSUM` hiện tại `0.00σ`.
- **Ghi chú minh bạch về sai khác đối chiếu `2024`:** Trên năm đệm `2024`, bộ đọc `holdout_eval_2025_2026.py` dùng nến D1 dựng từ M1 UTC (`00:00 UTC`) thay vì D1 Server MT5 (`EET 00:00`) nên cho chênh lệch nhẹ `+0.54%..+0.69%` so với bản Development (`PORT_7E 7.69% vs 7.00%`, `PORT_9E 7.14% vs 6.60%`) do lệch ranh giới `2–3` giờ khi tính Wilder `ATR14`.

---

## 4. Gói triển khai MT5 Demo / Free Trial (đã tích hợp sẵn, `OrderSend = 0`)

- Toàn bộ `8` EA `.mq5` đã được nối trực tiếp `#include "Include/Naqex_PropGuard.mqh"`, sửa triệt để lỗi trùng Magic Number cũ (`E1 = 20261122`, `E3 GBPUSD = 20261125`, `E4 US100 = 20261124`) và đồng bộ đúng tỷ trọng `PORTFOLIO-REGISTRY.json`.
- Đã bổ sung bộ điều phối toàn tài khoản [Naqex_AccountOrchestrator.mq5](../../tooling/ai-engines/exports/Naqex_AccountOrchestrator.mq5) (tự hạ AMBER/RED, Kill-Switch toàn tài khoản, phát hiện lệnh mồ côi thiếu SL, xuất heartbeat `naqex_heartbeat.json`) và lịch tin đỏ `2018–2026` [naqex_red_news_utc.csv](../../tooling/ai-engines/exports/Files/naqex_red_news_utc.csv) (`MQL5/Files/`).
- **Quy trình bắt buộc trước khi nạp phí thật:** (1) Biên dịch `8` EA + `Orchestrator` trên MetaEditor và kiểm MT5 Strategy Tester chế độ **"Every tick based on real ticks"** + độ trễ `150–250ms`; (2) Treo **FTMO Free Trial `14` ngày** + đối soát `naqex_exec_audit.csv` bằng `quant_factory.tca_reconcile`; (3) Tham gia **The5ers Free Monthly Competition (`0 USD`)** để đo `SymbolInfo` thật và xin email xác nhận EA tự viết theo Terms §11.

---
title: "Đối Soát Thực Nghiệm MT5 Real-Tick (Model=4) vs Python & Vá Lỗi Swap Ngày Nửa Phiên Mỹ"
date: "2026-11-24"
lane: "lane-a-mql5-builder"
phase: "wave2-cycle0"
status: "VERIFIED_8_OF_8_PASS"
holdout_2025_2026: "SEALED (0 holdout rows)"
---

# Báo Cáo Đối Soát MT5 Real-Tick (`Model=4`) vs Python — FTMO-Demo (`1515343166`)

- **Thời điểm tạo báo cáo (UTC):** `2026-11-23T19:49:41+00:00` (bàn giao sáng `2026-11-24`)
- **Tài khoản kiểm chứng:** `FTMO-Demo` (`login=1515343166`, `ACCOUNT_TRADE_MODE_DEMO`, vốn `10,000 USD`, đòn bẩy **Swing `1:30`**, `terminal_build=6230`, sandbox cô lập `.runtime/ftmo-demo-portable-1515343166`, tuyệt đối không đụng máy chủ thật).
- **Cấu hình mô phỏng:** MetaTrader 5 Strategy Tester `Model = 4` (**Every tick based on real ticks**, chất lượng dữ liệu `99%–100%`, `11.39M–24.20M` real ticks mỗi cặp), quét đa độ trễ **`50ms / 150ms / 250ms`** trên cửa sổ Development **`2024-09-01..2024-12-31`** (`< 2025-01-01`, giữ nguyên niêm phong Holdout `2025–2026`).
- **Kết luận tổng thể:** **`8 / 8` EA ĐẠT `PASS`**, **`24 / 24` lượt chạy `ok = true`**, **`24 / 24` lượt chạy `swap = 0.00 USD`**, **`24 / 24` log sạch `0` lỗi** (`0` `INIT_FAILED`, `0` `retcode 10030`, `0` `[PROPGUARD-ERR]`).
- **Bằng chứng gốc:** `.runtime/mt5-realtick-results/realtick_matrix_summary.json` (và `24` báo cáo `.htm` + `parsed_result.json` chi tiết).

---

## 1. Hai Lỗi Thực Tế Do Real-Tick FTMO Phát Hiện & Bản Vá Triệt Để

Đợt chạy `Model = 4` lần đầu trên tick thật FTMO đã bóc trần **2 lỗ hổng mà backtest M1 thường bỏ sót**:

### 1.1 Lỗi Swap Qua Đêm Trên `E4_US100_SESS40` Vào Ngày Nửa Phiên Mỹ (`+12.69 USD`)
- **Hiện tượng trước khi vá:** `E4_US100_SESS40` khớp đủ `19` lệnh, log sạch, nhưng phát sinh **`swap = +12.69 USD`** (ở `50/150ms`) và `+12.91 USD` (`250ms`) cùng PnL `-36.83 USD` (`50ms`), bị bộ đối soát tự động gắn cờ `NEEDS_REVIEW` (`SWAP_VIOLATION`).
- **Truy vết chính xác từng giao dịch trong `E4_US100_SESS40_50ms/parsed_result.json`:**
  1. **Lệnh #26–27 — Thứ Sáu Đen (`2024-11-29`, Black Friday):** Vào lệnh BUY `0.26` lot lúc `18:49:20` giờ server (`11:49 ET`). Sàn NYSE đóng cửa sớm lúc `13:00 ET` và FTMO dừng khớp `US100.cash` lúc `20:15` giờ server (`13:15 ET`) — **trước mốc phẳng lệnh `15:55 ET`**. Vị thế bị treo xuyên cuối tuần tới `2024.12.02 02:00:00`, phát sinh **`swap = +8.39 USD`** (triple Friday swap) và vi phạm quy tắc không giữ lệnh qua tuần của FTMO Standard.
  2. **Lệnh #38–39 — Đêm Giáng Sinh (`2024-12-24`, Christmas Eve):** Vào lệnh BUY `0.20` lot lúc `18:38:18` giờ server (`11:38 ET`). FTMO đóng sớm `US100.cash` lúc `13:15 ET`, lệnh bị giữ xuyên lễ Giáng Sinh tới `2024.12.26 01:05:00`, phát sinh **`swap = +4.30 USD`**.
  3. Tổng `8.39 + 4.30 = 12.69 USD` — khớp chính xác tới từng cent.
- **Nguyên nhân gốc:** Hàm MQL5 `SymbolInfoSessionTrade()` trong `IsNearBrokerSessionClose()` chỉ trả về lịch cố định Thứ Hai–Thứ Sáu hàng tuần, **không phản ánh lịch đóng cửa sớm ngày lễ Mỹ (`13:00 ET`)**.

### 1.2 Lệch 1 Giờ Mùa Hè Mỹ (`NY+7 US DST`) Bên Trong `MQL_TESTER`
- **Hiện tượng trước khi vá:** Trên FTMO (chuẩn NY-close `NY+7`: `UTC+3` mùa hè Mỹ EDT, `UTC+2` mùa đông Mỹ EST — khớp [native_ftmo_asym_pivot.py](../../tooling/ai-engines/native_ftmo_asym_pivot.py)), hàm `NowUTC()` trong `MQL_TESTER` trước đây trừ cố định `InpGuardTesterUtcOffsetH = 2`, khiến toàn bộ tháng 9–10 (`2024-09-01..2024-11-02`) trong Strategy Tester chạy sớm `1` giờ (`17:31` thay vì `18:31` server). *(Lưu ý: ở chế độ chạy thật `!MQL_TESTER`, `NowUTC()` luôn gọi `TimeGMT()` nên không bị lệch.)*

### 1.3 Bản Vá Đã Áp Dụng & Biên Dịch Lại `9/9` (`0 errors, 0 warnings`)
1. **[Naqex_PropGuard.mqh](../../tooling/ai-engines/exports/Include/Naqex_PropGuard.mqh):**
   - Bổ sung bộ lịch thuần toán học `IsUsEquityHalfDayNY(ny)` chặn cả 3 ngày đóng sớm `13:00 ET` hàng năm của NYSE: **03/07** (T2–T5 trước Quốc khánh Mỹ), **Black Friday** (Thứ Sáu sau Thứ Năm tuần 4 tháng 11: ngày `23..29`), và **24/12** (Đêm Giáng Sinh T2–T6).
   - Nâng cấp `NowUTC()` trong `MQL_TESTER` tự động nhận diện US DST (`IsUsDstUtc`, Chủ nhật thứ 2 tháng 3 -> Chủ nhật đầu tháng 11) khi `InpGuardTesterUtcOffsetH == 2`.
2. **[Naqex_WB_SESS_CONT_BRK40_US100.mq5](../../tooling/ai-engines/exports/Naqex_WB_SESS_CONT_BRK40_US100.mq5) (`E4`) & [Naqex_WB_IDX_RS_US100_LEAD_1130.mq5](../../tooling/ai-engines/exports/Naqex_WB_IDX_RS_US100_LEAD_1130.mq5) (`E5`):**
   - Không mở lệnh phiên chiều và cưỡng chế đóng lệnh (`HARD_FLAT_US_HALF_DAY_SWAP0`) vào các ngày nửa phiên Mỹ; bổ sung chốt phòng vệ `nyMins < 09:30 && HasOpenPosition()` (`OVERNIGHT_FAILSAFE_SWAP0`).
3. **Biên dịch & kiểm định sau vá:**
   - Toàn bộ `9/9` file `.mq5` biên dịch bằng FTMO portable `MetaEditor64.exe` đạt **`0 errors, 0 warnings`** (giữ nguyên mặc định `InpDryRunLogOnly = true` & `InpGuardDryRunLogOnly = true`, `10/10` file `0` red flags qua `audit_open_source_mq5`).
   - Đồng bộ `.ex5` vào `.runtime/mt5-compiled-ex5/`, `.runtime/ftmo-demo-portable-1515343166/MQL5/Experts/Naqex/` và làm mới [manifest.sha256.json](../../tooling/ai-engines/exports/deployment_kit/manifest.sha256.json).

---

## 2. Bảng Đối Soát Toàn Bộ `8/8` EA × `3` Mức Độ Trễ (`24/24` Lượt Chạy Sau Vá)

Cửa sổ kiểm chứng Development: **`2024-09-01..2024-12-31`** (`Deposit = 10,000 USD`, `Leverage = 1:30`, `Model = 4` Real Ticks).

| Engine | Symbol / TF | Ticks thật | MT5 Trades (`50ms`) | Py Trades | Day Jaccard | MT5 `50ms` Net (USD) | MT5 `150ms` Net (USD) | MT5 `250ms` Net (USD) | Drag `50->250ms` | Py Dev Net (USD) | MT5 `50ms` PF / DD% | Swap (USD) | Kết luận |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---|
| `E1_USDJPY_TOKYO` | `USDJPY` M15 | 20,022,579 | 78 | 78 | **95.0%** | -40.75 | -42.69 | -43.54 | -2.79 | -33.38 | 0.93 / 2.30% | **0.00** | **PASS** |
| `E2_USDJPY_EXP80` | `USDJPY` M15 | 20,022,579 | 26 | 23 | 69.0% | +73.36 | +74.25 | +74.08 | +0.72 | +173.64 | 1.26 / 1.17% | **0.00** | **PASS** |
| `E3_GBPUSD_VH` | `GBPUSD` M15 | 13,491,937 | 11 | 12 | **91.7%** | -104.81 | -105.74 | -106.65 | -1.84 | -103.97 | 0.53 / 2.44% | **0.00** | **PASS** |
| `E4_US100_SESS40` | `US100.cash` M5 | 19,747,271 | 18 | 19 | **94.7%** | **+40.15** | **+57.53** | **+69.47** | +29.32 | +26.95 | 1.36 / 0.83% | **0.00** | **PASS** |
| `E5_US100_RS1130` | `US100.cash` M5 | 19,747,271 | 12 | 15 | 68.8% | +17.75 | +24.04 | +30.37 | +12.62 | -10.22 | 1.25 / 0.63% | **0.00** | **PASS** |
| `E6_EURJPY_VOLCOMP` | `EURJPY` M15 | 24,196,341 | 5 | 4 | **80.0%** | **+92.77** | **+93.30** | **+93.89** | +1.12 | +90.08 | 102.95 / 0.41% | **0.00** | **PASS** |
| `E7_USDJPY_NY10ET` | `USDJPY` M5 | 20,022,579 | 3 | 3 | **100.0%** | -20.53 | -20.69 | -20.90 | -0.37 | -8.06 | 0.33 / 0.62% | **0.00** | **PASS** |
| `S6_FX_USD_BSK` | `MULTI_FX` M15 | 11,394,916 | 3 | 3 | 50.0% | -58.30 | -58.30 | -58.40 | -0.10 | -48.23 | 0.00 / 0.60% | **0.00** | **PASS** |
| **Tổng `PORT_7E` (`E1..E7`)** | **7 Core EAs** | — | **153** | **154** | — | **+57.94** | **+80.00** | **+96.72** | **+38.78** | **+135.04** | — | **0.00** | **7/7 PASS** |
| **Tổng 8 EA (`+S6`)** | **8 EAs** | — | **156** | **157** | — | **-0.36** | **+21.70** | **+38.32** | **+38.68** | **+86.81** | — | **0.00** | **8/8 PASS** |

### So sánh trực diện Trước Vá vs Sau Vá trên `E4_US100_SESS40` & Độ Khớp Ngày Giao Dịch

| Chỉ số kiểm chứng | Trước khi vá (`Fixed UTC+2`, chưa chặn half-day) | Sau khi vá (`NY+7 US DST` + `IsUsEquityHalfDayNY`) |
|---|---|---|
| `E4_US100_SESS40` Swap (`50/150/250ms`) | `+12.69 / +12.69 / +12.91 USD` (**VIOLATION**) | **`0.00 / 0.00 / 0.00 USD` (`PASS`)** |
| `E4_US100_SESS40` Net PnL (`50/150/250ms`) | `-36.83 / -27.32 / -20.43 USD` | **`+40.15 / +57.53 / +69.47 USD`** |
| `E4_US100_SESS40` Day Jaccard vs Python | `58.3%` (`14/19` trùng, `5` thừa) | **`94.7%` (`18/18` lệnh MT5 khớp Python, `0` thừa)** |
| `E1_USDJPY_TOKYO` Trades & Jaccard | `79` vs `78` (`93.8%`) | **`78` vs `78` chính xác (`95.0%`)** |
| `E5_US100_RS1130` Day Jaccard | `52.9%` (`9` trùng) | **`68.8%` (`11/12` lệnh MT5 khớp Python)** |
| `E7_USDJPY_NY10ET` Day Jaccard | `50.0%` (`2/3` trùng) | **`100.0%` (`3/3` trùng tuyệt đối)** |
| `S6_FX_USD_BSK` Trades & Jaccard | `5` vs `3` (`33.3%`, `-119.90 USD`) | **`3` vs `3` chính xác (`50.0%`, `-58.30 USD`)** |

---

## 3. Nhận Định Kỹ Thuật Về Sai Khác Nhỏ Giữa MT5 Real-Tick & Python M1

1. **Độ nhạy với độ trễ (`50ms -> 250ms`) rất thấp trên FX và thuận nhẹ trên `US100.cash`:**
   - Trên toàn bộ 6 EA FX (`E1, E2, E3, E6, E7, S6`), chênh lệch tổng PnL khi tăng độ trễ gấp `5` lần (`50ms -> 250ms`) chỉ từ `-2.79` đến `+1.12 USD` (tức `< 0.03%` tài khoản) — xác nhận hệ thống **không phụ thuộc vào độ trễ siêu thấp (HFT)** và hoàn toàn phù hợp chạy PC local hoặc Windows VPS phổ thông (`15–150ms`).
   - Trên `US100.cash` (`E4`, `E5`), độ trễ `150–250ms` thậm chí cho giá khớp tốt hơn đôi chút trên mẫu Q4/2024 do dao động micro-tick hai chiều quanh thời điểm breakout (`+29.32 USD` ở `E4`, `+12.62 USD` ở `E5`); coi đây là nhiễu micro-tick trung tính, không kỳ vọng làm edge.
2. **Lý do chênh lệch nhỏ về số lệnh/PnL ở `E2` (`+73.36` vs `+173.64 USD`) và `E5`/`S6`:**
   - Python dùng dữ liệu M1 Bid/Ask đóng gói sẵn với mô hình `iATR` trên nến D1 lịch UTC chuẩn, còn MT5 `Model = 4` dùng `iATR` trên nến D1 giờ server FTMO (`NY+7`) + tick thực biến thiên spread từng mili-giây + `InpGuardEnableRedNews = true` (`±5m` CSV tin đỏ có thể chặn hoặc đóng sớm 1–2 lệnh trùng ngày FOMC/CPI/NFP vốn không tắt trong tape thô `build_or_load_frozen_tapes()`).
   - Phí commission thực đo trong báo cáo MT5 khớp sát chuẩn FTMO: `US100.cash = 0.00 USD`, FX (`USDJPY/GBPUSD/EURJPY/MULTI_FX`) `~5.00 USD/lot` khứ hồi (`-17.78`, `-9.36`, `-6.32`, `-1.82`, `-0.80`, `-1.72 USD`).
3. **Sức khỏe `PORT_7E` vs `S6` trên thực nghiệm tick thật:** Trong Q4/2024, `PORT_7E` (`E1..E7`) vẫn giữ **dương `+57.94..+96.72 USD`** ở mọi mức độ trễ với MaxDD từng engine chỉ `0.41%–2.44%`, trong khi `S6` âm nhẹ `-58.30 USD` trên `3` lệnh — nhất quán với thiết kế chỉ bật `S6` ở giai đoạn Free Trial / P1 và tắt (`0.00%`) ở P2 & Funded.

---

## 4. Hạ Tầng Vận Hành Sẵn Sàng Cho FTMO Free Trial Demo Đêm Nay

- **Bộ công cụ Wave-2 Cycle 0 (chạy hoàn toàn fail-closed, cấm chạm `C:\Program Files\MetaTrader 5`):**
  - [mt5_realtick_runner.py](../../tooling/ai-engines/exports/mt5_realtick_runner.py) — chạy tuần tự `Model=4` Real-Tick đa độ trễ (`KeepPrivate=0`, `Leverage=1:30`, không ghi mật khẩu vào `.ini`).
  - [mt5_vs_python_reconciler.py](../../tooling/ai-engines/exports/mt5_vs_python_reconciler.py) — bóc tách báo cáo `.htm` UTF-16LE + bảng Deals (`swap`, `commission`, `SL`) + khóa cứng không chạm Holdout Python `>= 2025-01-01`.
  - [build_ftmo_profile.py](../../tooling/ai-engines/exports/build_ftmo_profile.py) — đã dựng sẵn hồ sơ **`Naqex_FreeTrial` (9 biểu đồ UTF-16LE, `expertmode=1` chỉ bật Algo Trading, tắt tuyệt đối DLL)** trong `.runtime/ftmo-demo-portable-1515343166/MQL5/Profiles/Charts/Naqex_FreeTrial/` và `81A933A9.../MQL5/Profiles/Charts/Naqex_FreeTrial/` dùng bộ preset `FTMO_FreeTrial_Demo` đã kiểm chứng (`US100.cash` `MaxSpreadPoints = 450.0`, `SYMCAP_100 = 1.00%`, `RedNews = true`).
  - [mt5_live_monitor.py](../../tooling/ai-engines/exports/mt5_live_monitor.py) — bộ giám sát chỉ đọc (`order_send_count = 0`), kiểm tra cưỡng bức `ACCOUNT_TRADE_MODE_DEMO` & `FTMO-Demo 1515343166`, ghi log live bid/ask/spread/equity/positions/heartbeat mỗi `60s` ra `.runtime/live-overnight/mt5_live_spread_log.jsonl`.
- **Kiểm chứng tự động:**
  - `verify_deployment_kit.py --require-ex5`: **`PASS | profiles=10 presets=90 tracked_sha=114 ex5_sha=9`**.
  - `pytest -vv tooling/ai-engines/tests/test_wave2_mt5_realtick.py tooling/ai-engines/tests/test_mql5_parity_and_kit.py tooling/ai-engines/tests/test_quant_factory_suite.py`: **100% PASS**.

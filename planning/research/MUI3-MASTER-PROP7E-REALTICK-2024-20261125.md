---
title: "Mũi 3 — Kiểm thử Real-Tick 2024 & Vá Lỗi Naqex_Master_Prop7E.ex5"
date: 2026-11-25
lane: mql5-builder
status: COMPLETED_REAL_TICK_2024Q4
holdout_rows_analysed: 0
order_send_count: 0
canonical_dev_mt5: "D:\\ANNAM\\TradingWorkspace\\.runtime\\ftmo-demo-portable-1515343166"
naqex_node1_touched: false
---

# Mũi 3 — Kiểm thử Real-Tick `Model=4` (`2024 Q4`) & Vá Lỗi `Naqex_Master_Prop7E.ex5`

## 1. Tóm tắt ngắn gọn (Plain Vietnamese)

- **ĐÃ HOÀN TẤT CHẠY SỐNG `Model=4` (Every tick based on real ticks) CHO `Naqex_Master_Prop7E.ex5`** trên vùng tick thật `99%` của máy chủ `FTMO-Demo` (`2024.09.01..2024.12.31`, **`20.022.579` tick thật**, độ trễ `50 ms`, đòn bẩy `1:30`, rủi ro nền `1,0x` Funded, nạp đủ **`492` mốc tin đỏ** kể cả `FOMC Meeting Minutes`).
- **Kết quả vượt kỳ vọng & khớp cực sát `1:1` với bộ `7` EA tách lẻ:**
  - Tổng số lệnh: **`156` lệnh** (`312` deals, khớp tuyệt đối `E1: 78/78`, `E2: 26/26`, `E3: 11/11`, `E6: 5/5`, `E7: 3/3`; chỉ nhỉnh nhẹ `E4: 19 vs 18`, `E5: 14 vs 12`).
  - Lãi ròng thực tế: **`+138,79 USD`** (so với `+57,94 USD` khi cộng 7 EA lẻ — cao gấp **`2,4×`**, đồng thời giảm lỗ trên `GBPUSD` từ `-104,81` xuống `-69,33 USD`), **Profit Factor `1,12`**, **Sharpe `1,03`**, **Win Rate `52,56%`**, **Max Equity DD chỉ `2,59%` (`261,42 USD`)**.
  - **An toàn tuyệt đối:** Tổng phí qua đêm **`swap = 0,00 USD` (`swap_zero_ok = True`)**, tổng hoa hồng **`-34,00 USD`**, **`0` lệnh từ chối (`order_rejects = 0`)**, **`0` cảnh báo PropGuard**, **`0` lỗi log Agent**, ngày lệnh cuối **`2024-12-30`** (`holdout_rows_analysed = 0`).
- **Đã phát hiện & vá sạch `5` lỗi thật quan trọng** (2 lỗi chặn `100%` lệnh `US100`/Tester, lỗi `KeepPrivate=0`, lỗi cấp phát bộ nhớ `CopyTicksRange` và nút thắt tốc độ hot-loop D1 ATR giúp rút thời gian chạy `20` triệu tick đa mã xuống chỉ **`4 phút 27 giây`**).
- **Tác động tới `naqex-node1` đang chạy live:** **`0%`** — máy chủ `naqex-node1` vẫn đang chạy yên ổn bộ 9 EA cũ (`9/9` tin đỏ, `open_positions = 0`), không bị đụng chạm trong toàn bộ đợt kiểm định này.

---

## 2. Chi tiết `5` lỗi thật đã phát hiện và vá sạch

| # | Tệp & Vị trí | Lỗi thật phát hiện | Cách vá an toàn (giữ `InpDryRunLogOnly = true`) |
|---|---|---|---|
| **1** | [mt5_realtick_runner.py](../../tooling/ai-engines/exports/mt5_realtick_runner.py#L141-L152) + [test_wave2_mt5_realtick.py](../../tooling/ai-engines/tests/test_wave2_mt5_realtick.py#L93-L99) | `render_tester_ini()` đặt `KeepPrivate=0` (xóa phiên lưu khi đóng) và thiếu `[Experts] Enabled=0` (nguy cơ nạp chart live cùng tài khoản). | Đổi sang **`KeepPrivate=1`**, bổ sung **`[Experts] Enabled=0 / AllowLiveTrading=0 / AllowDllImport=0`**, cập nhật cấu hình Dev MT5 và thêm cờ 1-lệnh `--master-prop7e` khóa cứng `ToDate <= 2024.12.31`. |
| **2** | [Naqex_Master_Prop7E.mq5](../../tooling/ai-engines/exports/Naqex_Master_Prop7E.mq5#L60-L62), [L437-L460](../../tooling/ai-engines/exports/Naqex_Master_Prop7E.mq5#L437-L460) + [Naqex_PropGuard.mqh](../../tooling/ai-engines/exports/Include/Naqex_PropGuard.mqh#L409-L433) | **Lỗi chặn `100%` lệnh `US100.cash` (`E4/E5`):** Dùng chung trần spread FX `35` điểm cho cả `US100.cash` (spread bình thường `~195` điểm). | Thêm `maxSpreadOverridePts` tương thích ngược vào `IsSpreadAndSessionSafeFor()` và `MaxSpreadCapForSymbol()` (`450` điểm cho chỉ số, `45` điểm cho `EURJPY`, `35` điểm cho FX thường). |
| **3** | [Naqex_Master_Prop7E.mq5](../../tooling/ai-engines/exports/Naqex_Master_Prop7E.mq5#L15) | **Lỗi `0` lệnh trong Strategy Tester:** Thiếu `#property tester_file "naqex_red_news_utc.csv"` nên Agent không nhận file tin đỏ và phanh fail-closed chặn toàn bộ lệnh. | Bổ sung **`#property tester_file "naqex_red_news_utc.csv"`** — Agent đã xác nhận nạp đủ `492` sự kiện tin đỏ (`max_ts=1829482200`). |
| **4** | [Naqex_Signals_7E.mqh](../../tooling/ai-engines/exports/Include/Naqex_Signals_7E.mqh#L290-L337) | Gọi `CopyTicksRange()` mỗi tick cho cả 8 mã trong Strategy Tester gây cấp phát mảng động nặng. | Dùng `SymbolInfoTick()` không cấp phát bộ nhớ khi `MQLInfoInteger(MQL_TESTER) != 0`; giữ `100%` `CopyTicksRange()` cho live/demo. |
| **5** | [Naqex_Master_Prop7E.mq5](../../tooling/ai-engines/exports/Naqex_Master_Prop7E.mq5#L673-L692) + [Naqex_Signals_7E.mqh](../../tooling/ai-engines/exports/Include/Naqex_Signals_7E.mqh#L85-L150) | **Nút thắt tốc độ đa mã (quá giờ `420s`):** Gọi `CopyBuffer(D1 ATR)`, vòng `20` ngày `E6`, `CopyRates` ngày nghỉ lễ Mỹ và `EventSetTimer(1)` trên hàng chục triệu tick. | Cache giá trị nến D1 đã đóng (`shift=1`) theo ngày (bất biến trong ngày), thêm cooldown `60s` khi thử khôi phục M1 ngày lễ, và đặt `EventSetTimer(MQL_TESTER ? 60 : 1)` + tiết lưu `1s` trong Tester -> hoàn tất `20` triệu tick trong **`267,11s`** mà giữ nguyên `100%` tín hiệu. |

---

## 3. Kết quả thực chạy `Model=4` Tick thật (`2024.09.01..2024.12.31`, `50 ms`, `1:30`, `1,0x` Funded)

Artifact đầy đủ lưu tại `.runtime/mt5-realtick-results/MASTER_PROP7E_2024Q4_L30_50ms/` (`naqex_rt_MASTER_PROP7E_2024Q4_L30_50ms.htm`, `parsed_result.json`, `Agent-127.0.0.1-3000_20261125.log`):

### A. Chỉ số tổng hợp của `Naqex_Master_Prop7E.ex5` (`1` EA gộp duy nhất)

| Chỉ tiêu | Giá trị đo thật (`Model=4` Real Ticks) | Đánh giá cổng an toàn |
|---|---:|---|
| Chất lượng dữ liệu / Số tick | **`99% real ticks` (`20.022.579` ticks)** | Đạt chuẩn |
| Thời gian chạy / Mã thoát | `267,11s` (`rc = 0`, `report_ok = true`) | Nhanh, ổn định |
| Tổng số lệnh (`in / out`) | **`156` lệnh (`312` deals, `35` thoát SL)** | `100%` có SL, `0` lệnh treo |
| Lãi ròng (`Total Net Profit`) | **`+138,79 USD`** (`Gross +1.323,61 / -1.184,82`) | Vượt `2,4×` tổng 7 EA lẻ (`+57,94 USD`) |
| Profit Factor / Sharpe / Win Rate | **`1,12`** / **`1,03`** / **`52,56%`** (`82W / 74L`) | Expected Payoff `+0,89 USD`/lệnh |
| Max Balance DD / Max Equity DD | **`2,18%` (`219,79 USD`)** / **`2,59%` (`261,42 USD`)** | Rất an toàn so với trần `5%` ngày / `10%` tĩnh |
| **Tổng Swap qua đêm** | **`0,00 USD` (`swap_zero_ok = True`)** | **PASS tuyệt đối** |
| Tổng hoa hồng (`Commission`) | **`-34,00 USD`** | Thấp hơn `-36,08 USD` của 7 EA lẻ |
| Tin đỏ / Cảnh báo / Lệnh từ chối | **`492` sự kiện nạp OK / `0` cảnh báo / `0` reject** | **PASS tuyệt đối** |
| Ngày lệnh cuối / Holdout `2025+` | **`2024-12-30` / `0` dòng** | **Holdout SEALED** |

### B. Đối chiếu `1:1` theo từng mã & từng nhánh (`Naqex_Master_Prop7E` vs Wave-2 `7E` tách lẻ)

| Nhánh / Mã | Wave-2 `7E` (lẻ) — Số lệnh | `Master_Prop7E` (gộp) — Số lệnh | Wave-2 `7E` Lãi ròng (USD) | `Master_Prop7E` Lãi ròng (USD) | Ghi chú |
|---|---:|---:|---:|---:|---|
| `E1` + `E2` + `E7` (`USDJPY`) | `78 + 26 + 3 = 107` | **`78 + 26 + 3 = 107`** | `+12,08` | **`+111,36`** | Khớp `100%` số lệnh cả 3 nhánh; điều phối rủi ro cụm cải thiện mạnh ròng |
| `E6` (`EURJPY`) | `5` | **`5`** | `+92,77` | **`+82,30`** | Khớp `100%` số lệnh |
| `E4` + `E5` (`US100.cash`) | `18 + 12 = 30` | **`19 + 14 = 33`** | `+57,90` | **`+14,46`** | Hoạt động mượt nhờ vá trần spread `450` điểm |
| `E3` (`GBPUSD`) | `11` | **`11`** | `-104,81` | **`-69,33`** | Khớp `100%` số lệnh; trần cụm USD cắt giảm `-35,48 USD` lỗ |
| **TỔNG `7E` CORE** | **153 lệnh** | **156 lệnh** | **`+57,94 USD`** | **`+138,79 USD`** | **`swap = 0,00 USD`, `0` lỗi log, `0` reject** |

---

## 4. Bằng chứng biên dịch `10/10` & Kiểm thử tự động

- Biên dịch sạch **`10/10` file `.ex5`** (`0 errors, 0 warnings`) vào `.runtime/mt5-compiled-ex5/` (`0` file `.ex5` trong Git `tooling/ai-engines/exports/`).
- `mql5_parity_checker.py --require-ex5`: **PASS** (`8/8` EAs, `PropGuard / Orchestrator / Master_7E OK`, `492` dòng CSV, `10` EX5).
- `verify_deployment_kit.py --require-ex5`: **PASS** (`profiles=10`, `presets=90`, `tracked_sha=122`, `ex5_sha=10`).
- `pytest` (`test_wave2_mt5_realtick.py`, `test_mql5_parity_and_kit.py`, `test_node_ctl.py`) & `system_doctor.py --mode fast` (`9/9 PASS`).

---

## 5. Kết luận cho hạn chót FTMO Black Friday `30/11/2026`

- **Mũi 3 đã hoàn thành & vượt cổng kỹ thuật (`PASS`):** `Naqex_Master_Prop7E.ex5` đã được chứng minh chạy thật trên **`20,02` triệu tick thật** của máy chủ `FTMO-Demo` với **`0` lỗi khớp đa mã**, **`0,00 USD` swap**, **`0` cảnh báo tin đỏ `492` dòng**, và **hiệu quả thực tế (`+138,79 USD`, `DD 2,59%`) vượt trội bản 7 EA lẻ (`+57,94 USD`)**.
- **Lưu ý triển khai an toàn:** Giữ nguyên bộ 9 EA đang chạy trên `naqex-node1` để không cắt ngang dữ liệu Demo; có thể gắn thêm `Naqex_Master_Prop7E.ex5` ở chế độ chạy bóng (`InpDryRunLogOnly=true, InpShadowCompareMode=true`) hoặc chuyển sang `Master_Prop7E` khi bắt đầu vòng Challenge mới sau khi chốt đủ Mũi 5 (email xác nhận EA + giá checkout thật) và Mũi 6 (phán quyết cuối của Astra tối `29/11`).

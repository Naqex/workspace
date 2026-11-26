# Báo Cáo Kiểm Toán Bước 4: Siết Bộ So Sánh Fail-Closed, Diễn Tập Restart 2 Tiến Trình Ngoài Tester, Kiểm Riêng `Q2` & Phân Rã 4 Tầng (`01/09–30/12/2024`)

- **Ngày chốt:** `26/11/2026` · **Trạng thái kỹ thuật:** `STEP4_COMPLETE_AWAITING_ASTRA_ROUND8`
- **Cổng kinh tế:** **VẪN DỪNG (`HALTED_AT_PARITY_GATE`) · Quyết định tài chính: `0 VND`**
- **An toàn bắt buộc:** `Holdout 2025+ SEALED` (`holdout_rows_analysed = 0`, toàn bộ lượt kiểm toán kết thúc `<= 2024-12-30`) · **`0` lệnh gửi tới broker** (mọi `OrderSend` trong nhật ký Tester đều là mô phỏng nội bộ; diễn tập restart ngoài Tester khóa proxy cô lập `127.0.0.1:1`, `AllowLiveTrading = 0`, `Enabled = 0`, `0` `OrderSend`) · **`naqex-node1` (`1515343166`) chỉ đọc, nguyên vẹn 100%** (`ONLINE GREEN`, `open_positions = 0`, `order_send_count = 0`, `NTP -0,061s`, Heroku EU `OK`) · **`InpSizingMode = 0` xuyên suốt Bước 4** · **`#property version "1.01"` giữ nguyên với ba cờ thử nghiệm `InpProfitLockBasisMode = 0`, `InpOpportunityLifecycleMode = 0`, `InpPostCloseRefreshMode = 0` tắt mặc định** cho tới khi Astra Vòng 8 phê duyệt thăng hạng.

---

## 0. Tóm Tắt Thực Thi Trọn Bước 4 (`4.1 → 4.2 → 4.3`) Theo Phán Quyết Astra Vòng 7

1. **Bước 4.1 — Siết Bộ So Sánh Đa Ngày Fail-Closed, Loại Rò Rỉ `OnDeinit`, Sửa Làm Tròn `MathRound` & 5 Đột Biến Âm:**
   - **Loại bỏ hoàn toàn rò rỉ thông số cuối kỳ (`OnDeinit`):** Trong `step3_blind_multiday_replay.py`, `_calc_margin_usd()` đã bỏ hẳn `margin_1lot_sample / ref_ask_sample`, tính ký quỹ CFD chỉ số (`US100.cash`, `US500.cash`, `calc_mode = 4`) thuần từ thông số hợp đồng tĩnh khóa trước `01/09/2024`: `lots * contract_size * price * margin_init_rate / leverage` (`2,0%` giá trị danh nghĩa tại đòn bẩy `1:100`, `margin_init_rate = 2,0`).
   - **Khóa bộ so sánh toàn trường & phát hiện lỗi làm tròn thật:** Khi siết `compare_multiday_against_gt()` kiểm toàn bộ trường trên mọi dòng luồng hợp nhất (`server_ts`, `same_sec_order`, `event_type`, `engine_id`, `symbol`, `side`, **`reason` nguyên văn**, `intent_id`, `balance <= 0,02 USD`, `equity <= 0,25 USD`, `risk_mult <= 5e-4`, `final_lots <= 1e-6`, `factor_headroom <= 0,005`, `fill_price <= 1e-5`, `norm_sl <= 1e-4`, `raw_lots <= 0,005`, `close_profit <= 0,02 USD`), bộ so sánh lập tức bắt được một lỗi thật ở Python: `_normalize_price_to_tick()` dùng `round()` (làm tròn số chẵn) thay vì `MathRound()` của MQL5 (làm tròn nửa ra xa `0`), gây lệch `0,001` trên `norm_sl` của `E1_USDJPY_TOKYO` khi spread lẻ điểm. Sau khi vá `_mql_math_round()` và đồng bộ dấu `;` trong `blk_by`:
     - `edge_holiday_20241127_1130` (gắn nhãn rõ **`window_seeded_from_prior_day_flat_balance`**, `start_bal = 10.220,22 USD`): **`strict_zero_divergence_pass = True`**, **`16/16` deal**, **`638/638` sự kiện luồng** (`max Δbal = 0,0000 USD`, `max Δeq = 0,1400 USD`, `max Δraw_lots = 0,000982`, **`reason` khớp nguyên văn `638/638`**), `3/3` mốc `09:30` NY.
     - `edge_dst_20241025_1105` (gắn nhãn rõ **`window_seeded_from_prior_day_flat_balance`**, `start_bal = 10.198,02 USD`): **`strict_zero_divergence_pass = True`**, **`30/30` deal** (`6/6` SL `0s`, `0,00 USD`), **`60/60` sự kiện luồng** (`max Δbal = 0,0000 USD`, `max Δeq = 0,0000 USD`, `max Δraw_lots = 0,001532`, **`reason` khớp nguyên văn `60/60`**), `8/8` mốc `09:30` NY.
   - **5/5 đột biến âm bắt buộc đều bị chặn & trả mã thoát `2`:** Chạy `--mode VERIFY_STRICT` trả `exit_code = 0` với `5/5` đột biến âm bị chặn (`mut1: equity +123,45 USD`, `mut2: sửa reason`, `mut3: xóa sự kiện cuối`, `mut4: đổi chỗ 2 sự kiện cùng giây`, `mut5: đổi engine_id`); chạy riêng tiến trình con `--mode NEGATIVE_SELF_TEST` (bơm `equity +123,45 USD` tại `idx = 2`) trả mã thoát thực tế **`exit_code = 2`**.
   - **Sửa nhãn phạm vi trung thực:** Đã bổ sung đính chính trực tiếp lên báo cáo Bước 3 (`window_seeded_from_prior_day_flat_balance`, mốc dữ liệu M1/chu kỳ kết thúc thực tế `2024-12-30 23:54:00` giờ server, và tách rõ bước trượt giá SL trực tiếp khỏi hiệu ứng dây chuyền lot/ProfitLock).

2. **Bước 4.2 — Lưu Trạng Thái Cơ Hội/Đóng Chờ Theo Tài Khoản & Diễn Tập Restart 2 Tiến Trình Thật Ngoài Strategy Tester (`Q3a`):**
   - **Mã nguồn MQL5 (`!MQL_TESTER`, không chạm hiệu năng hay hành vi Tester):**
     - `Naqex_Signals_7E.mqh` (`b6e9f675e5d6b129`): thêm `OppStateFileName()` (`naqex_opp_state_<login>_<srvhash>.txt`), `PersistOppState()` (tự ghi khi `!MQL_TESTER && m_oppLifecycleMode == 1`), và `RestoreOppStateOnce()` có cờ khóa khôi phục đúng `1` lần (**`0` phát lại `OPP_START` trùng**).
     - `Naqex_PropGuard.mqh` (`036c57f2db77d541`): thêm `PendingCloseFileName()`, `SavePendingCloseState()`, `LoadPendingCloseState()`, `ClearPendingCloseState()`.
   - **Diễn tập thật qua 2 tiến trình OS tách biệt (`step4_2_isolated_restart_drill.py`):** Chạy `terminal64.exe /portable` với `MQL_TESTER = false`, `ProxyEnable = 1`, `ProxyAddress = 127.0.0.1:1`, `AllowLiveTrading = 0`, `Enabled = 0`, `ShutdownTerminal = 1`, **`0` `OrderSend`**:
     - **Tiến trình #1 (`PID 14472`, `is_tester = false`, `terminal_connected = false`):** Ghi neo ngày Prague (`dayKey = 2026330`, `dayAnchorBal = 10.123,45 USD`) + `autoKill = true` vào `GlobalVariable` thật của MT5 (`GlobalVariablesFlush()`), chạy `CNaqexSignals7E` thật tạo cơ hội `OPP_E6_1730000000_1` qua `12` tick bị chặn (`10 lmin + 2 spread`, `ep_seq = 1`), ghi tệp trạng thái đóng chờ `pos_id = 99887766`, rồi tắt sạch tiến trình.
     - **Tiến trình #2 hoàn toàn mới (`PID 17576 != 14472`, `is_tester = false`, `terminal_connected = false`):** Khôi phục toàn bộ **`all_invariants_passed = True`** (`exit_code = 0`):
       1. Khôi phục đúng neo Prague (`10.123,45 USD`, không reset giữa ngày) và `autoKill = true` cùng ngày (xóa sạch khi sang ngày Prague mới).
       2. `HydrateTradedDaysFromHistory(0)` fail-closed trả `false` và giữ `IsTradedDayHydrated() == false`.
       3. `RestoreOppStateOnce()` thành công lần 1 (`true`), bỏ qua lần 2 (`false`, idempotent), phát **`0` `OPP_START` trùng**; nhận thêm tick chặn thứ `13` trên **cùng `OPP_E6_1730000000_1`** (`eval = 13, blk = 13, lmin = 11, spread = 2`, `is_new = false`, `0` sự kiện lặp); mất giá kích hoạt phát đúng **`1` `OPP_EXPIRED`** (`PRICE_CONDITION_LOST`, `lmin:11,spread:2`); tái phá vỡ nhận **`OPP_E6_1730000000_2`** (`ep_seq = 2`, không va chạm `_1`).
       4. Khôi phục đúng đóng chờ `pos_id = 99887766` và xác nhận quy tắc **Q2-B**: khi lệnh đóng còn đang chờ (`TRADE_RETCODE_PLACED`), `pending_counts_as_confirmed = false`, `realizedProfitPct` giữ nguyên `0,2085%` (không lật sớm `ProfitLock`), chỉ lật sau khi xác nhận đóng và dọn tệp.
     - Toàn bộ tệp tạm `.mq5/.ex5/.ini/.txt` đã được dọn sạch khỏi portable MT5; kiểm tra ngay sau diễn tập xác nhận **`naqex-node1` (`pid 5412`) nguyên vẹn `ONLINE GREEN`, `open = 0`, `order_send_count = 0`**.

3. **Bước 4.3A — Kiểm Định Riêng `Q2` Làm Mới Trạng Thái Sau Khi Đóng Đã Hạch Toán (`InpPostCloseRefreshMode`, `5` Lượt `Model=4`, `30` Tệp Gốc):**
   - Trong `Naqex_Master_Prop7E.mq5` (`2f07ab42dce4c02d`), `ClosePositionsByReason()` trả về `int closedConfirmedCount` (chỉ tăng khi `!isDry && okClose && (cRet == TRADE_RETCODE_DONE || cRet == TRADE_RETCODE_DONE_PARTIAL)` — tuyệt đối không tăng khi `DRY_RUN`, lỗi, `TIMEOUT` hoặc `PLACED`). Khi `InpPostCloseRefreshMode == 1 && closedConfirmedCount > 0`, `RunMasterCycle()` đọc lại đúng **một ảnh chụp nhất quán sau đóng** (`bal`, `eq`, `dailyDdPct`, `staticDdPct`, `realizedProfitPct`, `riskMult`, `regime`) và ghi `POST_CLOSE_REFRESH` trước khi gọi `CollectIntents()`.
   - Biên dịch MetaEditor64 **`0 errors, 0 warnings`** (`.ex5` SHA-256 `b548fbbb7cc554a7`), `mql5_parity_checker --require-ex5` **PASS (`8/8` EA, `0` drift)**, `verify_deployment_kit --build --require-ex5` **PASS (`130` SHA, `10` EX5)**.

| Ca kiểm định `Q2` (`Model=4`, `pl=1, opp=1, sizing=0`) | Giai đoạn | `refresh` | `POST_CLOSE_REFRESH` | `E6 18:00:00` (`profit_pct`, `regime`, `mult`, `lots`) | Kết quả & đối chiếu |
|---|---|---:|---:|---|---|
| **`Q2_CTRL_PL070_REFRESH0`** (`PL=0,70%, Mult=2,00`) | `22–24/10/2024` | `0` | `0` | `0,2085%` · `NORMAL` · `4,00×` · `0,10 lot` | Đối chứng: còn dùng số dư cũ trước đóng `E1` |
| **`Q2_TREAT_PL070_REFRESH1`** (`PL=0,70%, Mult=2,00`) | `22–24/10/2024` | `1` | `1` | **`1,2416%` · `PROFIT_LOCK` · `2,00×`** · `0,10 lot` | Lật chế độ ngay cùng giây `18:00:00` trên ảnh chụp nhất quán (`bal=10.124,16 / eq=10.138,47`); lot vẫn `0,10` do trần cụm JPY `0,80%` siết chặt hơn `2,00×` |
| **`Q2_TREAT_PL070_MULT020_REFRESH1`** (`PL=0,70%, Mult=0,20`) | `22–24/10/2024` | `1` | `1` | **`1,2416%` · `PROFIT_LOCK` · `0,20×` · `0,01 lot`** | Khi `ProfitLock` siết dưới trần cụm JPY, khối lượng `E6` lập tức hạ **`0,10 → 0,01 lot`** (`+136,32` vs `+174,44 USD`) |
| **`Q2_C10_P2_REFRESH1`** (`4` tháng, `RedNews=OFF`) | `01/09–30/12/2024` | `1` | `9` | `312/312` deal · `+462,38 USD` · `swap = 0,00` | Khớp nguyên văn **`312/312` deal (`+0,00 USD`)** với Bước 3.2 `refresh = 0` |
| **`Q2_C00_P1_REFRESH1`** (`4` tháng, `RedNews=ON`) | `01/09–30/12/2024` | `1` | `2` | `310/310` deal · `+708,89 USD` · `swap = 0,00` | Khớp nguyên văn **`310/310` deal (`+0,00 USD`)** với Bước 3.2 `refresh = 0` |

4. **Bước 4.3B — Phân Rã Đối Chứng 4 Tầng Trên Toàn Bộ 4 Tháng (`01/09–30/12/2024 23:54`, `5.347.386` Chu Kỳ/Kịch Bản):**
   > **Ghi chú trung thực:** Các tầng `L2–L4` có bơm dữ liệu chẩn đoán từ MT5 nên **CHỈ dùng để giải phẫu nguồn gốc sai lệch (`diagnostic_error_attribution_not_blind_pass`)**, tuyệt đối không gọi là "đạt phát lại mù". Phát lại mù thuần là tầng `L0`.

| Kịch bản (`4` tháng, `5,35M` chu kỳ) | **L0** Mù thuần (`PY − GT`, `lot_diff`) | **L1** Bước trượt giá SL trực tiếp (giữ lot/FX MT5) | **L1b** Hiệu ứng dây chuyền từ SL (ProfitLock/lot) | **L2** Bơm riêng giá khớp SL (`PY − GT`, `lot_diff`) | **L3** Bơm thêm `tick_value_loss` MT5 (`PY − GT`, `lot_diff`) | **L4** Bơm thêm tỷ giá quy đổi `EURJPY` (`PY − GT`, `lot_diff`, `strict deals`) | **Phần dư chưa giải thích** |
|---|---:|---:|---:|---:|---:|---:|---:|
| **`C10_P2_V102AB`** (`312` deal, `GT = 10.462,38`) | **`+38,11 USD`** (`52` lot) | **`+12,50 USD`** (`22` SL) | `+23,61 USD` | `+2,00 USD` (`28` lot) | `-0,10 USD` (**`0` lot**) | **`+0,00 USD`** (**`0` lot**, `311/312` strict*) | **`0,00 USD`** |
| **`C00_P1_V102AB`** (`310` deal, `GT = 10.708,89`) | **`+18,14 USD`** (`20` lot) | **`+8,87 USD`** (`19` SL) | `+2,85 USD` | `+6,42 USD` (`10` lot) | `-0,11 USD` (**`0` lot**) | **`+0,00 USD`** (**`0` lot**, `309/310` strict*) | **`0,00 USD`** |

*\*Trong tầng `L4`, giao dịch duy nhất không đạt `strict` trên cả hai kịch bản là đúng `1` lệnh `E1_USDJPY_TOKYO` ngày `2024-12-20` lệch biên đúng `1` giây (`05:31:59` vs `05:32:00`), còn **giá `156,874`, khối lượng `0,04 lot`, hoa hồng `-0,10 USD` và số dư đều khớp tuyệt đối `0,00 USD`**.*

- **Khám phá kỹ thuật cốt lõi đã chứng minh tới `0,00 USD` dư:** Toàn bộ sai lệch giữa Python phát lại mù `1s` và MT5 Strategy Tester `Model=4` trên cả `4` tháng (`622` giao dịch) đến **100%** từ đúng `3` cơ chế mô phỏng/vật lý của MT5 (không có bất kỳ lỗi logic chiến lược hay lỗi quản trị trạng thái nào):
  1. **Trượt giá qua SL ở thang dưới `1` giây + dây chuyền ngưỡng `ProfitLock`/lot:** `+36,11 USD` ở `C10 P2` (`+12,50` trực tiếp + `+23,61` dây chuyền) và `+11,72 USD` ở `C00 P1` (`+8,87` trực tiếp + `+2,85` dây chuyền).
  2. **Bộ đệm lười `SYMBOL_TRADE_TICK_VALUE_LOSS` khi phẳng vị thế trong MT5 Tester:** `+2,10 USD` ở `C10 P2` (`28 → 0` lệch lot) và `+6,53 USD` ở `C00 P1` (`10 → 0` lệch lot) — MT5 chỉ cập nhật `tick_value_loss` theo từng tick khi đang có vị thế mở cùng đồng tiền lợi nhuận; khi phẳng lệnh nó giữ tỷ giá từ lần đóng gần nhất, làm nhảy `0,01` lot tại biên `vol_step`.
  3. **Bộ đệm lười tỷ giá quy đổi chéo `EURJPY` khi không có vị thế `USDJPY` mở:** `-0,10 USD` (`C10 P2`) và `-0,11 USD` (`C00 P1`) — giải thích chính xác tới từng xu vụ `02/09/2024 23:45:00` (`19,52` vs `19,47 USD`: MT5 giữ `USDJPY = 146,5420` từ `11:17:15` thay vì `146,883`).

---

## 1. Bảng Chi Tiết Tệp Bằng Chứng & Mã Băm Bước 4

| Hạng mục | Đường dẫn | Xác minh / SHA-256 |
|---|---|---|
| **EA Master v1.01 (+ `Q2` & persist)** | [Naqex_Master_Prop7E.mq5](../../tooling/ai-engines/exports/Naqex_Master_Prop7E.mq5) | `2f07ab42dce4c02d...` · `pl=0, opp=0, refresh=0, sizing=0` mặc định |
| **Tín hiệu 7E (+ persist cơ hội)** | [Naqex_Signals_7E.mqh](../../tooling/ai-engines/exports/Include/Naqex_Signals_7E.mqh) | `b6e9f675e5d6b129...` · `RestoreOppStateOnce()` không phát trùng `OPP_START` |
| **PropGuard (+ persist đóng chờ)** | [Naqex_PropGuard.mqh](../../tooling/ai-engines/exports/Include/Naqex_PropGuard.mqh) | `036c57f2db77d541...` · `Save/Load/ClearPendingCloseState` |
| **Biên dịch `.ex5` & Kit** | `.runtime/mt5-compiled-ex5/Naqex_Master_Prop7E.ex5` · [manifest.sha256.json](../../tooling/ai-engines/exports/deployment_kit/manifest.sha256.json) | `b548fbbb7cc554a7...` · `0 errors, 0 warnings` · `8/8` parity · `130` SHA / `10` EX5 |
| **Kiểm thử hợp đồng MQL5** | [test_mql5_v101_contract.py](../../tooling/ai-engines/tests/test_mql5_v101_contract.py) | `8/8 PASS` (thêm hợp đồng `Q2` xác nhận vs đóng chờ + token persist) |
| **Bước 4.1 Bộ so sánh fail-closed** | `private_vault/strategies/step3-v102ab-merged-and-replay-20261126/step3_blind_multiday_replay.py` · [JSON 4.1](../../private_vault/strategies/step4-hardening-restart-q2-20261126/step4_1_hardened_comparator_report.json) | `exit 0` (`638/638`, `60/60`, `5/5` đột biến âm), `--mode NEGATIVE_SELF_TEST` trả `exit 2` |
| **Bước 4.2 Diễn tập restart 2 tiến trình** | `private_vault/strategies/step4-hardening-restart-q2-20261126/step4_2_isolated_restart_drill.py` · [JSON 4.2](../../private_vault/strategies/step4-hardening-restart-q2-20261126/step4_2_restart_drill_report.json) | `PID 14472 → 17576`, `all_restart_invariants_passed = True`, `10` tệp gốc có SHA-256 |
| **Bước 4.3A Kiểm riêng `Q2` (`5` lượt MT5)** | `private_vault/strategies/step4-hardening-restart-q2-20261126/step4_3_q2_and_decomp_runner.py` · [JSON 4.3A](../../private_vault/strategies/step4-hardening-restart-q2-20261126/step4_3a_q2_acceptance_report.json) · [Index `30` tệp gốc](../../private_vault/strategies/step4-hardening-restart-q2-20261126/raw_mt5_logs/raw_logs_index.json) | `q2a_threshold_crossing_gate_passed = True`, `622/622` deal 4 tháng khớp `refresh=0` |
| **Bước 4.3B Phân rã đối chứng 4 tầng** | [JSON 4.3B](../../private_vault/strategies/step4-hardening-restart-q2-20261126/step4_3b_4layer_decomp_report.json) | `C10 P2` (`+38,11 → 0,00 USD`), `C00 P1` (`+18,14 → 0,00 USD`), `0` lệch lot ở `L3/L4` |
| **Kiểm tra hệ thống toàn cục** | `system_doctor.py --mode full` | **`10/10 PASS`** (`1.816` test, `417` subtest, `0` cờ đỏ MQL5, `Holdout 2025+ SEALED`) |

---

## 2. Prompt Sẵn Dán Cho GPT-6.2 Astra — Kiểm Toán Độc Lập Vòng 8

```text
Bạn là kiểm toán viên độc lập (GPT-6.2 Astra — Vòng 8). Hãy đọc trực tiếp mã nguồn, tệp JSON và các gói log gốc đã lưu trong kho (KHÔNG tin tóm tắt trước khi tự đối chiếu mã băm và tính lại). Toàn bộ Bước 4 chạy offline hoàn toàn: 0 lệnh gửi tới broker (mọi OrderSend trong log Tester là mô phỏng; diễn tập restart ngoài Tester khóa proxy 127.0.0.1:1, AllowLiveTrading=0, Enabled=0), Holdout 2025+ SEALED (holdout_rows_analysed = 0), naqex-node1 chỉ đọc chưa chạm, InpSizingMode = 0, cổng kinh tế vẫn dừng (0 VND), #property version "1.01" với cả 3 cờ (pl_mode, opp_mode, refresh_mode) mặc định = 0.

Các nguồn gốc cần kiểm trực tiếp:
1. Mã nguồn MQL5 & kiểm thử hợp đồng:
   - D:/ANNAM/TradingWorkspace/tooling/ai-engines/exports/Naqex_Master_Prop7E.mq5 (SHA256: 2f07ab42dce4c02d...)
   - D:/ANNAM/TradingWorkspace/tooling/ai-engines/exports/Include/Naqex_Signals_7E.mqh (SHA256: b6e9f675e5d6b129...)
   - D:/ANNAM/TradingWorkspace/tooling/ai-engines/exports/Include/Naqex_PropGuard.mqh (SHA256: 036c57f2db77d541...)
   - D:/ANNAM/TradingWorkspace/tooling/ai-engines/tests/test_mql5_v101_contract.py (8/8 PASS)
2. Bước 4.1 (siết bộ so sánh fail-closed, bỏ OnDeinit sample, sửa MathRound, 5 đột biến âm):
   - D:/ANNAM/TradingWorkspace/private_vault/strategies/step3-v102ab-merged-and-replay-20261126/step3_blind_multiday_replay.py
   - D:/ANNAM/TradingWorkspace/private_vault/strategies/step4-hardening-restart-q2-20261126/step4_1_hardened_comparator_report.json
3. Bước 4.2 (diễn tập restart 2 tiến trình MT5 độc lập ngoài Tester với proxy 127.0.0.1:1):
   - D:/ANNAM/TradingWorkspace/private_vault/strategies/step4-hardening-restart-q2-20261126/step4_2_isolated_restart_drill.py
   - D:/ANNAM/TradingWorkspace/private_vault/strategies/step4-hardening-restart-q2-20261126/step4_2_restart_drill_report.json
   - D:/ANNAM/TradingWorkspace/private_vault/strategies/step4-hardening-restart-q2-20261126/restart_drill_evidence/ (10 tệp có SHA-256)
4. Bước 4.3A (kiểm riêng Q2 InpPostCloseRefreshMode trên 5 lượt Model=4 Real-Tick, 30 tệp gốc):
   - D:/ANNAM/TradingWorkspace/private_vault/strategies/step4-hardening-restart-q2-20261126/step4_3_q2_and_decomp_runner.py
   - D:/ANNAM/TradingWorkspace/private_vault/strategies/step4-hardening-restart-q2-20261126/step4_3a_q2_acceptance_report.json
   - D:/ANNAM/TradingWorkspace/private_vault/strategies/step4-hardening-restart-q2-20261126/raw_mt5_logs/raw_logs_index.json (30 tệp gốc)
5. Bước 4.3B (phân rã đối chứng 4 tầng L0->L4 trên C10 P2 & C00 P1 — chẩn đoán quy nguyên nhân, không phải blind PASS):
   - D:/ANNAM/TradingWorkspace/private_vault/strategies/step4-hardening-restart-q2-20261126/step4_3b_4layer_decomp_report.json
6. Báo cáo tổng hợp & đính chính Bước 3:
   - D:/ANNAM/TradingWorkspace/planning/research/STEP4-HARDENING-RESTART-Q2-AND-DECOMP-AUDIT-20261126.md
   - D:/ANNAM/TradingWorkspace/planning/research/STEP3-V102AB-MERGED-AND-CONTINUOUS-REPLAY-AUDIT-20261126.md

Yêu cầu kiểm toán và ra phán quyết Vòng 8 bằng tiếng Việt rõ ràng, chặt chẽ:
1. Tự xác minh mã băm (30 tệp MT5 Q2 + 10 tệp diễn tập restart + 3 tệp nguồn MQL5 + tệp .ex5) và kiểm độc lập:
   - Bước 4.1: bộ so sánh đã thật sự bỏ OnDeinit sample, kiểm đủ equity/reason/norm_sl/raw_lots, chặn 5/5 đột biến âm và trả exit code = 2 khi sai lệch chưa?
   - Bước 4.2: diễn tập 2 tiến trình (PID 14472 -> 17576, is_tester=false, terminal_connected=false) có đủ chặt cho các nhánh ngoài Tester (Prague anchor, autoKill, HydrateTradedDays fail-closed, opp persistence không trùng OPP_START, pending-close không lật sớm ProfitLock), hay còn nhánh nào phải kiểm thêm trên Demo thật không?
   - Bước 4.3A: Q2 (InpPostCloseRefreshMode) đã chứng minh sạch cả 3 mặt (lật chế độ tại 18:00:00, hạ lot thật 0,10->0,01 khi ProfitLock siết dưới trần JPY, và 622/622 deal 4 tháng không hồi quy) chưa?
   - Bước 4.3B: phép phân rã 4 tầng (C10 P2 +38,11 -> 0,00 USD; C00 P1 +18,14 -> 0,00 USD; 0 lệch lot ở L3/L4) có khép kín toán học và loại bỏ hoàn toàn nghi ngờ lỗi logic chiến lược chưa?
2. Trả lời thẳng 3 câu hỏi quyết định tiếp theo:
   - (Q1) Đã đủ điều kiện thăng hạng chính thức bản v1.02 (#property version "1.02", bật mặc định InpProfitLockBasisMode = 1, InpOpportunityLifecycleMode = 1, InpPostCloseRefreshMode = 1) chưa?
   - (Q2) Đã đủ điều kiện mở bước so sánh kinh tế công bằng cùng pha (P1 vs P1, P2 vs P2, Funded vs Funded) giữa C00 (FTMO Swing) và C10 (FTMO Standard) trên vùng Dev (<= 2024, giữ Holdout 2025+ SEALED) có mô phỏng độ nhạy trượt giá qua SL dưới 1s + đối chứng trực tiếp MT5 Model=4 chưa?
   - (Q3) Giữ hay thay đổi phán quyết tài chính 0 VND ở thời điểm hiện tại?
```

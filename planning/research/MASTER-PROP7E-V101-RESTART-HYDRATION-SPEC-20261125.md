---
title: "Kế hoạch Vá Cứng MQL5 v1.01 (7 Lỗi P0/P1 & Khôi phục Trạng thái OPS-01)"
date: 2026-11-25
lane: mql5-builder
status: READY_TO_APPLY_AFTER_WAVE1B_2205ICT
applies_to: "Naqex_Master_Prop7E.mq5 + Include/Naqex_Signals_7E.mqh + Include/Naqex_PropGuard.mqh (v1.01)"
v100_frozen_during_live_probe: true
order_send_count: 0
holdout_rows_analysed: 0
---

# Kế hoạch Vá Cứng MQL5 `v1.01` — `7` Hạng mục `P0/P1` Sẵn sàng Thi công Sau `22:05 ICT`

## 1. Phạm vi & Lý do giữ đóng băng `v1.00` trong lúc đo thực địa

- **Đóng băng an toàn trong lúc chạy Wave 1B:** Trong khi `@ops-probe` đang thu thập mẫu spread & khớp lệnh thực tế trên Dev PC đến `~22:05 ICT`, tuyệt đối không chạy `MetaEditor64.exe` / `terminal64.exe` và giữ nguyên bản `v1.00` đã kiểm chứng `5/5` kịch bản.
- **Mục tiêu bản `v1.01` (áp dụng ngay sau `22:05 ICT`, biên dịch sạch `10/10` + đối chiếu `Model=4` real ticks Q4 `4,0x`):** Xử lý dứt điểm toàn bộ **`7` điểm yếu thực địa (`P0/P1`)** gồm `6` phát hiện từ kiểm toán sâu 5 góc độ (`V101-01..V101-06`) và đột phá **`V101-07` (`REL+HEADROOM` sửa bẫy "Cát lún AMBER")** vừa chứng minh bằng `N = 5.000` kịch bản Monte Carlo (`#270`).

---

## 2. Bản thiết kế chi tiết `7` miếng vá `v1.01`

### Vá `V101-01` (`P0` — Audit Attribution): Ghi đúng `magic` từng nhánh + `tk=`/`pos=` trong `LogExecAuditFor()`
- **Vấn đề hiện tại (`v1.00`):** `Naqex_Master_Prop7E.mq5` gọi `g_guard.Init(..., InpMagicRangeMin, ...)` nên mọi dòng ghi vào `naqex_exec_audit.csv` đều mang magic cố định `20261120` thay vì magic thật của nhánh (`20261122..20261129`) và thiếu `tk=`/`pos=` khi đóng lệnh -> khiến `prop_challenge_tracker.py` bị mù phân bổ theo nhánh (`0/7`) và không nối được cặp mở-đóng để kiểm tra giữ qua đêm.
- **Cách vá chính xác:**
  1. Bổ sung tham số tùy chọn `const long magicOverride = -1` (giữ tương thích ngược cho `8` EA lẻ!) vào `CNaqexPropGuard::LogExecAuditFor(...)` trong `Include/Naqex_PropGuard.mqh`: nếu `magicOverride > 0` thì ghi `magicOverride`, ngược lại dùng `m_magic`.
  2. Tại `Naqex_Master_Prop7E.mq5::ProcessIntentAtomically()`, truyền `it.magic` vào `LogExecAuditFor(...)` và ghi kèm `pos=%I64u` (lấy `HistoryDealGetInteger(deal, DEAL_POSITION_ID)` hoặc `ResultOrder()`).
  3. Tại `CNaqexPropGuard::ClosePositionChecked()`, lấy `PositionGetInteger(POSITION_MAGIC)` và `PositionGetInteger(POSITION_IDENTIFIER)` trước khi đóng, ghi `tk=%I64u|pos=%I64u` kèm đúng magic của vị thế vào dòng `POSITION_CLOSE` trong `naqex_exec_audit.csv`.

### Vá `V101-02` (`P0` — Restart Safety `OPS-01`): Khôi phục `m_tradedDay[8]` + `g_autoKillActive` + `ANCHOR_UNRECOVERED` + Bảo vệ dựng lại `E1/E4`
- **Vấn đề hiện tại (`v1.00`):** `m_tradedDay[8]` và `g_autoKillActive` chỉ nằm trên RAM; nếu MT5 khởi động lại giữa phiên sau khi một nhánh đã đóng lệnh trong ngày (hoặc sau khi cầu dao ngày đã bật), trạng thái bị mất. Ngoài ra, nếu `HistorySelect` tạm lỗi sau restart, `g_anchorUnrecovered` bị kẹt vĩnh viễn tới ngày hôm sau; và `E1/E4` có thể dựng thiếu biên nếu khởi động lại ngay giữa khung `00–03 UTC` hoặc `09:30–11:30 ET`.
- **Cách vá chính xác:**
  1. Thêm `HydrateTradedDaysFromHistory(const datetime nowUtc)` trong `Naqex_Signals_7E.mqh` (chỉ chạy khi `!MQLInfoInteger(MQL_TESTER)`): quét `HistorySelect(srvNow - 48*3600, srvNow + 60)` lọc `DEAL_ENTRY_IN` + `DEAL_TYPE_BUY/SELL`, ánh xạ đúng `EngineIndexFromMagic(DEAL_MAGIC)` theo khóa ngày chuẩn từng nhánh (`utcDay` cho `E1/S6`, `d1Start` cho `E2/E3/E6`, `nyDay` cho `E4/E5/E7`) + quét thêm `PositionsTotal()`. Fail-closed (`g_tradedDayHydrated = false`, chặn intent mới) và thử lại mỗi `5s` nếu `HistorySelect` thất bại.
  2. Lưu `g_autoKillActive` vào GlobalVariable khóa theo tài khoản `CNaqexPropGuard::AcctAutoKillKey()` + `AcctDayKeyName()` (y hệt `Orchestrator`), đồng thời tự thử lại `RestoreOrInitDayAnchorM()` mỗi `15s` khi `g_anchorUnrecovered == true` để phục hồi ngay khi lịch sử broker đồng bộ xong.
  3. Bảo vệ `E1` (`00:00..03:00 UTC`) và `E4` (`09:30..11:30 ET`): khi khởi động lại ngay *giữa* khung tạo hộp (`!m_e1BoxReady` trong `00–03 UTC`, hoặc `!m_e4MornInit` trong `09:30–11:30 ET`), gọi ngay `ReconstructM1Window(startUtc, nowUtc)` để nối đủ đỉnh/đáy từ đầu khung thay vì thiếu dữ liệu các phút trước khi bật MT5.

### Vá `V101-03` (`P1` — Clock & Prague DST): Thay `TimeCurrent()` bằng `TimeTradeServer()` & Chuẩn hóa mốc 00:00 Chủ nhật đổi giờ EU
- **Vấn đề hiện tại (`v1.00`):** `TimeCurrent()` dừng cập nhật khi thị trường ít tick (đêm cuối tuần / chuyển phiên), làm sai lệch tính `srvMinusUtc` và làm chậm `OnTimer()` đóng phẳng. Ngoài ra, ngày Chủ nhật đổi giờ EU (`LastSundayOfMonth` tháng 3/10), `PragueUtcOffsetHoursM(utc)` lấy offset tại thời điểm hiện tại (`utc`) thay vì offset tại đúng `00:00` Prague (`01:00 UTC` mới đổi giờ), tạo sai lệch `1` giờ cho `CurrentResetStartServerTimeM()` vào sáng Chủ nhật chuyển mùa.
- **Cách vá chính xác:**
  1. Trong `CNaqexPropGuard::NowUTC()` và `CurrentResetStartServerTimeM()` / `ReconstructM1Window()`, dùng `TimeTradeServer()` (chỉ dùng `TimeCurrent()` khi `MQLInfoInteger(MQL_TESTER) != 0`).
  2. Khi tính `prgMidUtc` trong `CurrentResetStartServerTimeM()`, tính offset theo đúng ngày-giờ `00:00` của lịch Prague hôm đó (`midPrgStruct.hour = 0`), đảm bảo `HistorySelect(resetStart, ...)` khớp chuẩn phút đổi ngày của FTMO cả vào `2` ngày Chủ nhật đổi giờ mùa xuân & mùa thu.

### Vá `V101-04` (`P1` — US Holidays, Red-News Hard-Ban & Sunday Flat): Lịch nghỉ lễ Mỹ đầy đủ + Khóa đóng tay trong `±135s` + Vá Chủ nhật
- **Vấn đề hiện tại (`v1.00`):**
  - `IsUsEquityHalfDayNY()` hiện mới phủ một phần ngày nghỉ sớm Mỹ, chưa phủ trọn danh sách **Thanksgiving + Black Friday, MLK Day, Presidents' Day, Good Friday, Memorial Day, Juneteenth, July 4 (+ ngày trước lễ), Labor Day, Christmas Eve**.
  - `ClosePositionsByReason()` khi gặp `ShouldClockFlattenMagic()` hoặc `IsNearBrokerSessionCloseFor()` chưa kiểm tra chặn cứng **`IsInsideRedNewsHardBanFor(psym)` (`±InpGuardNewsHardBanSec = ±135s`)** — có rủi ro đóng lệnh ngay trong vùng cấm `±2m` của FTMO Standard Funded nếu mốc đóng trùng tin đỏ!
  - `ShouldClockFlattenMagic()` hiện trả `false` khi `day_of_week == 0 || day_of_week == 6`, nên nếu có vị thế sót từ thứ Sáu mở lại tối Chủ nhật (`22:00 UTC`), EA không tự xả ngay cho tới sáng thứ Hai!
- **Cách vá chính xác:**
  1. Nâng cấp `IsUsEquityHolidayOrHalfDayNY(ny)` trong `Naqex_PropGuard.mqh` phủ trọn lịch NYSE (`MLK`, `Presidents`, `Good Friday` bằng thuật toán Anonymous Gregorian Easter, `Memorial`, `Juneteenth`, `July 4`, `Labor`, `Thanksgiving`, `Black Friday`, `Christmas Eve / Day`, `New Year`).
  2. Thêm `IsInsideRedNewsHardBanFor(psym)` (`MathAbs(nowUtc - ev.utc_ts) <= InpGuardNewsHardBanSec`) và chặn mọi thao tác đóng không khẩn cấp (clock-flat / early-close) bên trong cửa sổ `±135s`, chỉ giữ xả trước tin trong vùng `-300s..-135s` (ngoài `±2m` của FTMO) và đóng ngay sau `+135s`! (Ngoại lệ duy nhất: `MASTER_KILL_DAILY_DD / STATIC_DD` khẩn cấp bảo vệ tài khoản.)
  3. Tại `ShouldClockFlattenMagic()`: nếu `utc.day_of_week == 0 && utc.hour >= 21` (mở cửa phiên Chủ nhật mà vẫn còn lệnh sót), trả `true` với lý do `"WEEKEND_GAP_FAILSAFE_SWAP0"` để dọn sạch ngay lập tức.

### Vá `V101-05` (`P1` — Pending Orders & In-Flight Reconciliation): Hủy lệnh chờ `OrdersTotal()` + Đánh dấu `MarkEngineTraded()` khi `TIMEOUT/PLACED` khớp
- **Vấn đề hiện tại (`v1.00`):** Khi kích cầu dao (`Kill`), vào vùng tin đỏ hoặc cắt phẳng cuối ngày, EA chỉ đóng vị thế `PositionsTotal()` mà chưa quét hủy lệnh chờ `OrdersTotal()` cùng dải magic. Khi `OrderSend` trả `TRADE_RETCODE_TIMEOUT` hoặc `TRADE_RETCODE_PLACED`, nếu lệnh thực tế khớp sau đó vài trăm ms, `ReconcileInFlightOrders()` chỉ tắt cờ `active` mà quên gọi `g_signals.MarkEngineTraded()`, và chưa chống đăng ký trùng slot `g_inFlight` theo `intent_id`/`magic`.
- **Cách vá chính xác:**
  1. Thêm hàm `CancelPendingOrdersByReason(const bool cancelAll, const string reason)` duyệt ngược `OrdersTotal() - 1 .. 0`, hủy mọi lệnh chờ thuộc dải `InpMagicRangeMin..InpMagicRangeMax` khi kích `Kill / ManualFlatten / RedNews / HardFlat`.
  2. Trong `ReconcileInFlightOrders()` (và `OnTradeTransaction()` khi `DEAL_ADD` khớp), lưu thêm `session_day_key` trong struct `NaqexInFlightOrder`; khi phát hiện vị thế/deal thực sự đã khớp từ trạng thái `unknown_state`, gọi ngay `g_signals.MarkEngineTraded(magic, session_day_key)` và ghi `ORDER_FILL_RECONCILED` vào `naqex_exec_audit.csv`.
  3. Trong `RegisterInFlight()`, kiểm tra nếu đã tồn tại slot active trùng `magic` hoặc `order_ticket` -> cập nhật tại chỗ thay vì mở slot trùng.

### Vá `V101-06` (`P1` — Execution Math & Broker Compliance): Làm tròn lô `volDigits`, `reqMargin <= 0` fail-closed, `SetDeviationInPoints`, và `Bid - SL` cho BUY `STOPS_LEVEL`
- **Vấn đề hiện tại (`v1.00`):**
  - `MathFloor((riskMoney / lossPerLot) / volStep) * volStep` không có đệm `+1e-9` và chưa qua `NormalizeDouble(lots, volDigits)` nên số thực IEEE-754 (ví dụ `0.06999999999999999`) có thể bị hạ mất 1 bước `0.01` hoặc bị broker từ chối `INVALID_VOLUME`.
  - Dòng kiểm tra ký quỹ dùng `reqMargin < 0.0` (chỉ bắt số âm, lọt qua trường hợp broker trả `reqMargin == 0.0` khi mất feed thông số ký quỹ!).
  - Chưa đặt `g_trade.SetDeviationInPoints(InpMaxSlippagePoints)` (mặc định `30` điểm FX / `150` điểm chỉ số) và kiểm tra `STOPS_LEVEL` cho lệnh BUY nên đo `MathAbs(bid - stopLoss)` (giá thanh lý thật của BUY là `Bid`, của SELL là `Ask`!).
- **Cách vá chính xác:**
  1. Tính `volDigits` từ `volStep` -> dùng `lots = NormalizeDouble(MathFloor((rawLots / volStep) + 1e-9) * volStep, volDigits)`.
  2. Siết điều kiện ký quỹ fail-closed sang `reqMargin <= 0.0` (cả trong `Naqex_Master_Prop7E.mq5` lẫn `Naqex_PropGuard.mqh`).
  3. Gọi `g_trade.SetDeviationInPoints(...)` theo nhóm mã trước `Buy/Sell` và kiểm tra `STOPS_LEVEL` theo giá thanh lý thật (`is_buy ? (bid - stopLoss) : (stopLoss - ask)`).

### Vá `V101-07` (`P0` — Sửa "Bẫy Cát Lún AMBER" `REL+HEADROOM`): Đổi phanh `AMBER/RED` sang hệ số tương đối + giảm dần theo biên DD ngày
- **Vấn đề hiện tại (`v1.00`, `Naqex_Master_Prop7E.mq5:318-354`):** Phanh `AMBER_BRAKE` (`staticDdPct >= 3,5%`) và `RED_BRAKE` (`>= 6,0%`) đang áp trần **tuyệt đối** `MathMin(mult, InpAmberMult)` (`0,65x`) và `MathMin(mult, InpRedMult)` (`0,40x`). Với gói P1 `4,00x`, cắt thẳng từ `4,00x -> 0,65x` (giảm `83,75%` kích thước lệnh) làm tài khoản bị sa lầy trong vùng AMBER/RED suốt `57%–72%` số ngày lịch, đẩy tỷ lệ kẹt mãi ở P1 tháng 24 lên **`34,6%`** và kéo trung vị lãi 24 tháng ở ma sát `1,50x` xuống âm **`-105,1 USD`** (`#270`).
- **Cách vá chính xác (`REL+HEADROOM`):**
  1. Đổi `AMBER_BRAKE` sang nhân tương đối: `mult = MathMin(mult, InpBasePhaseMult * InpAmberMult)` (`P1 4,00x -> 2,60x`; `P2 2,00x -> 1,30x`; **`Funded 1,00x -> 0,65x` giữ nguyên 100%!**).
  2. Đổi `RED_BRAKE` sang nhân tương đối: `mult = MathMin(mult, InpBasePhaseMult * InpRedMult)` (`P1 4,00x -> 1,60x`; `P2 2,00x -> 0,80x`; **`Funded 1,00x -> 0,40x` giữ nguyên 100%!**).
  3. Bật **vô điều kiện** bộ hãm theo khoảng trống DD ngày (`dailyHeadroom = MathMax(0.0, InpKillDailyDdPct - dailyDdPct)`): khi `dailyHeadroom < 2,0%`, nhân thêm `ddScale = MathMax(0.25, dailyHeadroom / 2.0)` kể cả khi `InpSizingMode == 0`, bảo đảm giữ **`0,0%` vi phạm trần lỗ ngày**.
- **Bằng chứng đối chứng (`N = 5.000` kịch bản `98,70 EUR`, `#270`):** Tại ma sát `1,50x`, `REL+HEADROOM` lật trung vị 24 tháng từ **`-105,1 USD -> +235,7 USD`** (`EV/Fee +2,92x`), nâng `Pass24` từ **`48,4% -> 78,2%`**, cắt `StuckP1` từ **`34,6% -> 6,4%`**, và giữ **`0,0%` vỡ DD ngày** (ở `1,00x` đạt trung vị `+600,0 USD` / `Pass24 91,1%`).

---

## 3. Lộ trình thi công & Nghiệm thu ngay sau `22:05 ICT` (khi `@ops-probe` dừng Dev MT5)

1. Xác nhận `0` tiến trình `terminal64`/`metatester64` đang chạy trên Dev PC (chỉ thực thi sau lệnh `GREEN_LIGHT_V101_COMPILE_AND_REALTICK`).
2. Áp dụng trọn bộ `7` miếng vá `V101-01..V101-07` vào `Naqex_PropGuard.mqh`, `Naqex_Signals_7E.mqh`, và `Naqex_Master_Prop7E.mq5` (`#property version "1.01"`, giữ `InpDryRunLogOnly = true` & `InpShadowCompareMode = true`).
3. Biên dịch sạch `10/10` `.ex5` qua `MetaEditor64.exe` (`0 errors, 0 warnings`) vào `.runtime/mt5-compiled-ex5/`.
4. Cập nhật `mql5_parity_checker.py` + `verify_deployment_kit.py --build --require-ex5` + chạy trọn `pytest` (`test_mql5_parity_and_kit.py`, `test_holdout_and_tca_guards.py`, `test_statement_reconcile_e2e.py`, `test_node_cutover_dryrun.py`).
5. Chạy kiểm chứng **`Model=4` Real Ticks Q4 `4,0x` (`MASTER_PROP7E_V101_2024Q4_P1_4X_50ms`, ~4,5 phút)** xác nhận `swap = 0,00 USD`, `492` tin đỏ OK, `0` lỗi/reject, phanh tương đối `REL+HEADROOM` vận hành đúng, và **`naqex_exec_audit.csv` ghi đúng đủ `7/7` magic nhánh + `tk=`/`pos=`**.
6. Chỉ đồng bộ lên `naqex-node1` khi `node_cutover_dryrun.py --live-readonly` báo xanh `10/10` (`READY_FOR_CUTOVER`).

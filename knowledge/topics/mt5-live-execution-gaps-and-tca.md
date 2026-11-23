---
doc_type: evergreen
domain: knowledge
topic: mt5-live-execution-gaps-and-tca
updated_utc: 2026-11-23
sources:
  - "T1: MetaQuotes MQL5 Documentation — Strategy Tester, Deal Properties, Order Filling & Trade Retcodes (mql5.com/en/docs)"
  - "T1: FTMO Official Symbol Specs & Trading Updates (ftmo.com) + The5ers Official Program Rules (the5ers.com)"
  - "T1 (Đo nội bộ): FTMO-DEMO-10K-STANDARD-FULL13-AND-EXECUTION-20261119.md & PRE-HOLDOUT-READINESS-AND-BLINDSPOT-AUDIT-20261123.md"
  - "T2: Habr RU (articles 982782, 890142, 1095592) & Quant StackExchange (Q59440, Q50759) — chi phí khớp thực & sự cố kỹ thuật algotrading"
  - "T3: Cộng đồng MQL5.com & Reddit r/algotrading — kinh nghiệm rollover 21:55-22:15 UTC, weekend gap, reconnect & orphan tickets"
---

# Khoảng cách MT5 Backtest vs Live/Free Trial & Sổ tay TCA Thực chiến

> Tài liệu sống dành riêng cho bước chuyển từ **Holdout Python (`GO`)** sang **MT5 Strategy Tester → FTMO Free Trial `14` ngày → Tài khoản quỹ nhỏ**. Mục tiêu: loại bỏ hoàn toàn tình huống *"backtest đẹp nhưng chạy thật chảy máu hoặc đoán nhầm lỗi sàn thành lỗi bot"* khi owner chưa có lịch sử giao dịch live trước đó ([Hồ sơ Owner](../owner/PROFILE.md)).

---

## 1. Phân tầng bằng chứng: Sự thật kỹ thuật vs Kinh nghiệm cộng đồng vs Quy ước Naqex

- **Sự thật đã xác minh (T1 — Tài liệu MQL5 / Spec sàn / Đo trực tiếp FTMO-Demo của Naqex):**
  - Trong MT5 Strategy Tester, `TimeGMT()` **trả về giờ máy chủ (`TimeCurrent()`) chứ không phải UTC thật**, tạo lệch `2–3` giờ nếu EA không tự bù offset theo `MQLInfoInteger(MQL_TESTER)` ([Pre-Holdout Audit §3.2](../../planning/research/PRE-HOLDOUT-READINESS-AND-BLINDSPOT-AUDIT-20261123.md)).
  - Chế độ test mặc định của MT5 không mô phỏng độ trễ mạng (`latency`), hàng đợi khớp LP (*liquidity provider*), từ chối lệnh (`retcode 10030/10018/10004`), hay ngắt kết nối VPS.
  - Đo thực tế `16` vòng trên **FTMO-Demo 10k Standard (`19/11/2026`)**: commission FX (`EURUSD`, `GBPJPY`) khớp đúng **`5,00 USD/lot` khứ hồi**, `US500.cash` = **`0 USD`**, `XAUUSD` = **`5,20 USD/lot`** (`~0,0007%` notional); độ trễ vòng lệnh từ host Việt Nam `p50 = 363–397 ms`, `max = 544 ms`; trượt SL thực đo `-0,10 pip` (`EURUSD`), `+0,02 USD/oz` (`XAUUSD`), `-0,16 điểm` (`US500.cash`), và đã từng gặp **`1` lệnh `XAUUSD` bị treo trạng thái trung gian mất `90,84` giây** trước khi đồng bộ đóng đúng ticket ([FTMO Demo Execution Audit](../../planning/research/FTMO-DEMO-10K-STANDARD-FULL13-AND-EXECUTION-20261119.md)).
- **Kinh nghiệm cộng đồng thực chiến (T2/T3 — MQL5, Habr RU, QuantSE, Reddit):**
  - Khoảng **`21:55–22:15 UTC`** (đóng cửa New York `17:00 ET`, mùa hè dịch về **`20:55–21:15 UTC`**) là vùng "chân không thanh khoản" (*rollover blackout*): spread `EURUSD`/`USDJPY`/`GBPUSD` có thể giãn **`3×–10×`** bình thường (`3–10+ pip`), đủ quét SL của lệnh đang mở dù biểu đồ Bid nhìn như chưa chạm.
  - Sự cố mất kết nối VPS/broker hoặc lỗi không đọc lại vị thế thật (`PositionsTotal()` / `PositionGetTicket()`) là nguyên nhân phổ biến nhất sinh ra **lệnh trùng (double-fill)** hoặc **lệnh mồ côi (orphan position)** không có SL — nhiều vụ cháy tài khoản algotrading ngoài đời đến từ bug quản trị trạng thái hơn là từ bản thân tín hiệu (Habr RU `890142`).
- **Quy ước vận hành Naqex (Suy luận từ T1+T2):**
  - Mọi động cơ trong `PORT_7E` và `PORT_9E` đều giữ cứng **intraday `swap = 0`**, đóng cưỡng bức trước **`20:55 UTC`** (`US100` đóng `15:55 ET`, `E1 USDJPY` đóng `18:00 Europe/Helsinki`) để **né hoàn toàn** cửa sổ rollover và weekend gap.
  - Không bao giờ đánh giá chất lượng khớp bằng mắt thường trên chart; mọi đánh giá sau `14` ngày Free Trial phải chạy qua [tca_reconcile.py](../../tooling/ai-engines/quant_factory/tca_reconcile.py) đọc trực tiếp nhật ký `naqex_exec_audit.csv`.

---

## 2. Năm nguồn sai lệch lớn nhất giữa MT5 Backtest và FTMO / The5ers Live

### 2.1. Giãn Spread giờ Rollover (`21:55–22:15 UTC` mùa đông / `20:55–21:15 UTC` mùa hè)
- **Cơ chế vi cấu trúc:** Các ngân hàng tạo lập thị trường (*Tier-1 LPs*) rút báo giá để chốt sổ ngày giao dịch lúc `17:00 New York`. Spread mở rộng đột ngột ở cả 2 phía: lệnh **BUY** đóng theo giá **Bid**, lệnh **SELL** đóng theo giá **Ask**. Do biểu đồ MT5 mặc định vẽ theo **Bid**, lệnh SELL bị quét SL vì **Ask** nhảy vọt mà mắt thường nhìn nến Bid sẽ tưởng sàn "ăn gian".
- **Bẫy DST kép (rất dễ dính):** Mỹ đổi giờ DST lệch Châu Âu `2–3` tuần mỗi năm. Lúc Mỹ đang giờ hè (`EDT = UTC-4`), mốc `17:00 ET` là **`21:00 UTC`** — tức chỉ sau giờ `flat_utc = 20:55` của Naqex đúng **`5` phút**!
- **Lớp phòng thủ bắt buộc:**
  1. `Naqex_PropGuard.mqh` kiểm tra `SymbolInfoSessionTrade()` (`IsNearBrokerSessionClose()`) để tự đóng sớm trước giờ đóng phiên sàn và các ngày lễ nửa phiên Mỹ (*US Half-Days* đóng `13:00 ET`).
  2. Bật bộ lọc **Max Spread Guard** chặn mở lệnh mới nếu `SYMBOL_SPREAD` vượt trần cho phép (ví dụ `> 2,5×–3,0×` spread chuẩn từng mã).

### 2.2. Khoảng trống cuối tuần (*Weekend Gaps*) và Ngày lễ đóng sớm
- **Thực tế sàn:** Tin địa chính trị cuối tuần có thể làm giá mở cửa Chủ Nhật (`22:00 UTC`) nhảy cách giá đóng cửa Thứ Sáu `30–150+ pip`. Lệnh Stop Loss **không bảo vệ được** trước gap — lệnh sẽ khớp ở giá mở cửa đầu tiên khả dụng (*gap slippage*), đủ kích hoạt vi phạm **Max Daily Loss `5%`** hoặc **Max Overall Loss `10%`** ngay trong giây đầu tiên của tuần mới.
- **Sai lệch Backtest:** Dữ liệu OHLC/tick bị làm mịn đôi khi nối liền Thứ Sáu sang Thứ Hai hoặc giả lập khớp đúng mức SL ngay trong khoảng trống giá.
- **Lớp phòng thủ Naqex:** `weekend_violations = 0`, `post_21utc_exits = 0` đã kiểm toán trên `100%` `2018–2024` và Holdout `2025–2026`. Tuy nhiên trên MT5 thật, vẫn phải xác minh rằng **lệnh đóng `hard flat` lúc `20:55 UTC` Thứ Sáu thực sự khớp xong** (không bị kẹt do mất mạng hoặc `TRADE_RETCODE_MARKET_CLOSED` vì ngày lễ).

### 2.3. Phân bố Trượt giá (*Slippage Distribution*) — Không phải số cố định
- **Sự thật cần hiểu:** Trượt giá thực tế có **đuôi dày bất đối xứng (asymmetric heavy tail)**:
  - **Lệnh Market / Stop-Entry / Stop-Loss:** Khi thị trường đi nhanh (đúng lúc tín hiệu Breakout của `E1..E7` kích hoạt!), thanh khoản cùng chiều mỏng đi nên trượt giá nghiêng về **bất lợi (adverse slippage)**.
  - **Lệnh Limit / Take-Profit:** Thường có xác suất khớp đúng giá hoặc trượt có lợi (*positive slippage*), nhưng dễ bị bỏ lỡ lệnh (*missed fill*) nếu giá chỉ chạm nhẹ.
- **Quy đổi thực tế cho Naqex:**
  - Trong nghiên cứu `2018–2024`, toàn bộ lõi `PORT_7E` đã sống sót dưới **`Stress +0,50 pip` mỗi chiều** và thậm chí **`+1,00 pip`** (`STRESS10`), và trên `US100.cash` spread đo thực tế FTMO-Demo (`1,95 pts`) còn **chặt hơn** dữ liệu lịch sử Dukascopy (`2,88–3,41 pts`).
  - Trong [tca_reconcile.py](../../tooling/ai-engines/quant_factory/tca_reconcile.py), ngưỡng trượt giá bất lợi trung bình so với khoảng dừng lỗ (`R0`) được khóa sẵn:
    - **`GREEN`:** trượt trung bình `< 12%` của `R0`, tỷ lệ reject `<= 5%`, `p90 latency <= 600 ms`, `swap_violations = 0`.
    - **`AMBER_WATCH`:** trượt trung bình `12%–25%` của `R0` hoặc `p90 latency > 600 ms`.
    - **`RED_SLIPPAGE_BREACH` / `RED_EXECUTION_QUALITY` / `RED_SWAP_VIOLATION`:** trượt `>= 25%` của `R0`, reject `> 5%`, hoặc phát sinh bất kỳ lệnh nào bị tính swap `!= 0`.

### 2.4. Khác biệt hạ tầng FTMO Demo/Free Trial vs Live/Funded & The5ers
- **Sự thật T1 + T3 cần phân biệt rõ:**
  - Trên **FTMO Free Trial** và **FTMO Challenge**, tài khoản chạy trên máy chủ mô phỏng nội bộ với thanh khoản tổng hợp tốt; cộng đồng (T3) thường ghi nhận **slippage trên Challenge/Live có thể cao hơn nhẹ so với Demo yên tĩnh** quanh tin đỏ hoặc khi lot lớn (`> 5–10 lot`), dù ở quy mô tài khoản `10.000–50.000 USD` (`0,10–1,50 lot` mỗi động cơ của Naqex), tác động thị trường (*market impact*) gần như bằng `0`.
  - **The5ers High Stakes** có luật cứng hơn FTMO Swing: cấm khớp (mở, đóng, dính SL/TP) trong cửa sổ **`±2 phút` quanh tin đỏ** (vi phạm sẽ bị **trừ toàn bộ lãi nhưng giữ nguyên lỗ**!). Vì vậy `Naqex_PropGuard` áp khóa bảo thủ **`±5 phút`** từ file `naqex_red_news_utc.csv`.

### 2.5. Mất kết nối, Khởi động lại VPS & Vị thế Mồ côi (*Orphan Positions*)
- **4 kịch bản lỗi hạ tầng kinh điển:**
  1. **Timeout khi gửi lệnh:** EA gọi `OrderSend()`, mạng VPS đứt `3` giây, sàn **đã khớp lệnh** nhưng EA không nhận được `TRADE_RETCODE_DONE` → EA gửi lại lệnh lần 2 (**double-fill**, nhân đôi rủi ro!).
  2. **Windows Update tự khởi động lại VPS giữa phiên:** Biến RAM (`g_dayStartEquity`, `g_lastTradedDay`) về `0` → EA quên mất hôm nay đã đánh rồi và vào thêm lệnh mới, hoặc mất mốc lỗ ngày Prague Reset.
  3. **Sửa tay trên điện thoại / lệnh thiếu SL:** Một vị thế nằm ngoài kiểm soát của `Magic Number` hoặc mất SL cứng trên server → vi phạm ngay luật bắt buộc SL của The5ers và phá trần rủi ro tài khoản.
  4. **Sai chế độ khớp `ORDER_FILLING_*`:** FTMO/The5ers/Exness dùng bit cờ `FOK`, `IOC`, `RETURN` khác nhau → dính mã lỗi `10030` (`Invalid filling mode`) khiến EA bỏ lỡ 100% lệnh.
- **Lớp chống lỗi đã có của Naqex:**
  - `Naqex_PropGuard.mqh` lưu trạng thái bền vững qua `GlobalVariableSet/Get` theo cặp `(Magic, Symbol)`, tự dò `SYMBOL_FILLING_MODE`, dùng `SYMBOL_TRADE_TICK_VALUE_LOSS`, và đối soát bằng `PositionsTotal()`.
  - `Naqex_AccountOrchestrator.mq5` giám sát chéo toàn tài khoản, phát hiện vị thế không có SL hoặc vượt trần rủi ro, xuất `naqex_heartbeat.json` cho `ops_monitor.py`.

---

## 3. Bảng Chẩn đoán 14 ngày Free Trial: Phân tách *Lỗi Sàn/Thanh khoản* vs *Bug Logic Bot*

Trong suốt `14` ngày treo **FTMO Free Trial**, bất kỳ sai khác nào giữa thực tế và Python/MT5 Tester đều phải tra theo bảng quyết định này — **tuyệt đối không sửa tham số tín hiệu khi chưa phân loại xong nguyên nhân gốc**:

| Triệu chứng quan sát trong Free Trial | Bằng chứng cần kiểm ngay (Log / Tick / CSV) | Nếu thấy dấu hiệu này → **Lỗi Sàn / Thanh khoản (Broker/Market)** | Nếu thấy dấu hiệu này → **Bug Logic / Cấu hình Bot (EA/Ops)** | Hành động khắc phục chuẩn |
|---|---|---|---|---|
| **1. Dính SL dù nến Bid trên chart chưa chạm** | Xuất raw `Ticks` (Bid & Ask) từ MT5 quanh đúng giây đóng lệnh; xem cột `DEAL_REASON_SL` | Lệnh là **SELL** và cột **Ask** thực sự vượt qua SL (đặc biệt quanh tin tức hoặc gần `21:00–22:15 UTC`) | Lệnh khớp đúng giờ `21:00+ UTC` do EA **chưa đóng `hard flat`** đúng giờ hoặc tính sai DST/UTC | Nếu do lỗi bot: sửa mốc `NowUTC()` / `flat_utc`. Nếu do spread sàn giãn bất thường trong phiên chính: lưu bằng chứng vào TCA, kiểm tra lại trần `MaxSpread`. |
| **2. Trượt giá vào/ra xấu (`>= 12%` của `R0`)** | So `signal_price` vs `fill_price` và `latency_ms` trong `naqex_exec_audit.csv`; đối chiếu lịch tin đỏ | `latency_ms < 250 ms`, spread lúc khớp giãn mạnh đúng lúc nến M1 biến động mạnh hoặc tin cấp 2 | `latency_ms > 500 ms` liên tục (chạy từ máy nhà/VPS xa server FTMO Prague/London), hoặc dùng lệnh Market đuổi giá muộn nhiều giây sau đóng nến | Thuê VPS gần server FTMO (`< 10–25 ms` ping) nếu latency cao; nếu trượt đến từ tin tức/giờ mở cửa, xem lại cửa sổ `red_news` và ngưỡng `AMBER/RED` TCA. |
| **3. Bot mở 2 lệnh trùng hoặc không mở lệnh nào** | Mở tab `Experts` + `Journal` tìm mã `retcode`; kiểm `GlobalVariables` (`F3` trên MT5) | Lệnh trả `10004 Requote`, `10018 Market closed`, `10021 No prices`, hoặc server FTMO bảo trì ngắn | Lệnh trả **`10030 Invalid filling`**, `10014 Invalid volume`, `10016 Invalid stops`, hoặc sau VPS restart EA không đọc lại `GlobalVariable` / `PositionsTotal()` | `10030/10014/10016` = **100% bug EA**, dừng ngay và viết test hồi quy. Lệnh trùng sau timeout = bổ sung khóa kiểm tra vị thế hiện có trước khi retry. |
| **4. Lệnh bị tính `Swap != 0` hoặc kẹt qua đêm** | Kiểm cột `swap_usd` trong `naqex_exec_audit.csv` và giờ đóng trên `History` | Sàn đóng phiên sớm đột xuất do **ngày lễ** mà không gửi thông báo trước hoặc lỗi thanh khoản cuối phiên | EA đóng sau `21:00 UTC` / `16:00 ET`, sai múi giờ hè/đông, hoặc không kiểm `SymbolInfoSessionTrade()` | Xếp **`RED_SWAP_VIOLATION`** ngay lập tức; kiểm lại hàm `IsNearBrokerSessionClose()` và ngày lễ Mỹ/Âu trước khi cho chạy tiếp. |
| **5. Lot vào thực tế lệch `> 5%` so với Python** | Kiểm `lots`, `sl_price`, `equity`, `SYMBOL_TRADE_TICK_VALUE_LOSS`, `SYMBOL_VOLUME_STEP` | Sàn đổi contract size / bước lot / tỷ giá quy đổi cặp chéo so với snapshot cũ | EA dùng nhầm `TICK_VALUE` thay vì `TICK_VALUE_LOSS`, quên trừ rủi ro đang mở (`SYMCAP_100`), hoặc làm tròn sai bước lot `0,01` | Chạy lại snapshot `SymbolInfo` Read-Only; sửa công thức `ComputeSafeLots()` và đối chiếu lại `mql5_parity_checker.py`. |
| **6. Khác tín hiệu vào lệnh so với Python trên cùng ngày** | Xuất nến M1 & D1 từ chính MT5 FTMO Demo so với Dukascopy M1 | Khác nhỏ (`1–3` lệnh/tháng) do giá đỉnh/đáy nến D1/M1 giữa feed FTMO và Dukascopy lệch vài `0,1` pip hoặc nến D1 EET vs UTC (`+0,5%–0,7%/năm` đã biết ở Holdout) | Lệch giờ mở cửa phiên `1–3` tiếng hàng loạt, sai thứ tự chỉ số bar (`bar 0` đang chạy vs `bar 1` đã đóng), hoặc dùng nhầm `TimeCurrent()` thay vì `NowUTC()` | Nếu lệch có hệ thống theo giờ/bar → **100% bug parity**, cấm lên tiền thật cho tới khi đạt `>= 95%` khớp tín hiệu trên MT5 Strategy Tester. |
| **7. Tổng rủi ro vượt trần `1%`/mã hoặc Daily DD gần chạm trần** | Kiểm nhật ký `Naqex_AccountOrchestrator` + `naqex_heartbeat.json` | Không có (luật rủi ro là trách nhiệm hoàn toàn của phía trader) | Trùng `Magic Number`, lỗi cộng dồn `SYMCAP_100` giữa `E4+E5` (`US100`) hoặc `E1+E2+E7` (`USDJPY`), hoặc Orchestrator chưa gắn trên chart riêng | **100% bug triển khai/cấu hình** — kích hoạt Kill-Switch, rà lại bảng Magic Number duy nhất trong [PORTFOLIO-REGISTRY.json](../../planning/research/PORTFOLIO-REGISTRY.json). |

---

## 4. Quy trình 4 cổng bắt buộc trước khi trả tiền mua Challenge đầu tiên

1. **Cổng 1 — MT5 Real-Tick Stress Parity:** Biên dịch sạch `0 errors, 0 warnings` toàn bộ `8` EA + `Naqex_AccountOrchestrator`, chạy Strategy Tester ở chế độ **`Every tick based on real ticks`** với độ trễ giả lập **`150–250 ms`**, kiểm tra không có lệch múi giờ `TimeGMT()` và tỷ lệ trùng lệnh với Python đạt chuẩn.
2. **Cổng 2 — 14 ngày FTMO Free Trial có gắn `tca_reconcile.py`:** Treo liên tục trên máy chủ/VPS ổn định (hoặc máy bàn mở 24/5 có ghi log `ops_monitor.py`), thu thập đầy đủ `naqex_exec_audit.csv`, không tắt/sửa lệnh bằng tay dù lệnh đang lãi hay lỗ.
3. **Cổng 3 — Hậu kiểm TCA (Pass/Fail nhị phân):**
   - `verdict == "GREEN"` (`mean adverse slippage < 12% R0`, `reject_rate <= 5%`, `p90 latency <= 600 ms`, `swap_violations == 0`).
   - `0` lệnh mồ côi, `0` lỗi `10030/10014/10016`, `0` vi phạm giờ đóng cửa ngày lễ/cuối tuần.
4. **Cổng 4 — Nếu bổ sung The5ers song song:** Lấy snapshot `SymbolInfo` thật ở mức **`0 USD`** qua **The5ers Free Monthly Competition** và nhận email xác nhận EA tự viết (Terms §11) trước khi mua gói `5.000 USD` (`39 USD`) ([Hồ sơ The5ers](../../planning/research/THE5ERS-PARALLEL-PROFILE-AND-SPEC-PLAN-20261123.md)).

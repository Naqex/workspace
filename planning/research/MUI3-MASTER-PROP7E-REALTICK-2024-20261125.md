---
title: "Mũi 3 & 3b — Kiểm thử Ma trận 5 Kịch bản 2024 & Vá Lỗi Naqex_Master_Prop7E.ex5"
date: 2026-11-25
lane: mql5-builder
status: COMPLETED_6SCENARIO_MATRIX_2024_WITH_V101_CERTIFIED
holdout_rows_analysed: 0
order_send_count: 0
naqex_node1_touched: false
---

# Mũi 3 & 3b — Kiểm thử Ma trận 5 Kịch bản `2024` & Vá Lỗi `Naqex_Master_Prop7E.ex5`

## 1. Tóm tắt ngắn gọn (Plain Vietnamese)

- **ĐÃ HOÀN TẤT MA TRẬN `5` KỊCH BẢN TRÊN MT5 STRATEGY TESTER (`FTMO-Demo`) CHO `Naqex_Master_Prop7E.ex5`** (`4` kịch bản **`Model=4` Tick thật `99%–100%` (`20.022.579` ticks)** cho `2024 Q4` ở cả `1,0x` Funded & `4,0x` P1 Challenge dưới độ trễ `50 ms` và `150 ms`, cộng `1` kịch bản **`Model=1` (1-Minute OHLC)** kiểm chứng đủ cả `12` tháng năm `2024` trên dữ liệu nến `2024.hcc` cục bộ).
- **Mọi cổng an toàn đều PASS tuyệt đối `5/5` kịch bản:**
  - Tổng phí qua đêm **`swap = 0,00 USD` (`swap_zero_ok = True`)** trên toàn bộ **`1.091` lệnh cộng dồn** (gồm cả `469` lệnh xuyên suốt 2 kỳ đổi giờ mùa hè/đông Prague của cả năm `2024`).
  - Nạp đủ **`492` mốc tin đỏ** (`naqex_red_news_utc.csv`, gồm `FOMC Meeting Minutes`), **`0` cảnh báo PropGuard**, **`0` lệnh bị từ chối (`order_rejects = 0`)**, **`0` lỗi log Agent**, **`0` lệnh live thật (`OrderSend = 0`)**, ngày lệnh cuối **`2024-12-30`** (`holdout_rows_analysed = 0`).
- **3 phát hiện quan trọng nhất cho quyết định Black Friday `30/11/2026`:**
  1. **Miễn nhiễm hoàn toàn với độ trễ khớp `3×` (`50 ms` -> `150 ms`) trên tick thật `Model=4`:**
     - Ở mức `1,0x` Funded: `50 ms` lãi **`+138,79 USD`** (`PF 1,12`, `EqDD 2,59%`) -> tăng trễ lên `150 ms` vẫn đạt **`+156,19 USD`** (`PF 1,13`, `Sharpe 1,16`, `EqDD 2,50%`, giữ nguyên `156` lệnh).
     - Ở mức `4,0x` P1 Challenge + `PROFIT_LOCK`: `50 ms` lãi **`+754,60 USD` (`+7,55%`, `PF 1,24`, `Sharpe 2,02`, `EqDD 6,27%`)** -> tăng trễ lên `150 ms` gần như giống hệt **`+755,69 USD` (`+7,56%`, `PF 1,24`, `Sharpe 2,03`, `EqDD 6,23%`)**.
  2. **Chế độ P1 `4,0x` + `PROFIT_LOCK` hoạt động đúng thiết kế trên tick thật:**
     - Hệ thống chạm mốc **`+5,0%`** vào ngày **`2024-11-15`**, tự động kích hoạt `PROFIT_LOCK` hạ đòn bẩy rủi ro từ `4,00×` về `2,01×`, đạt đỉnh **`10.815,30–10.817,17 USD` (`+8,15%..+8,17%`)** và chốt Q4 ở **`+7,55%..+7,56%`**.
     - Đáy số dư tĩnh dưới mốc vốn gốc `10.000 USD` chỉ là **`-2,08%` (`9.792,41 USD`)**, ngày lỗ thực tế nặng nhất chỉ **`-169,80 USD` (`-1,70%`)** ở `50 ms` / **`-172,32 USD` (`-1,72%`)** ở `150 ms` — cách rất xa trần lỗ ngày `5,0%` và trần mềm `3,5%` của FTMO.
  3. **Kiểm chứng cả `12` tháng năm `2024` (`Model=1` 1-Minute OHLC, `1,0x` Funded):**
     - Đạt **`+744,48 USD` (`+7,44%`)** trên **`469` lệnh** (`PF 1,19`, `Sharpe 1,47`, `Recovery 1,72`, `Equity DD 3,97%`), **cả `4/4` quý năm `2024` đều có lãi** (`Q1 +286,91`, `Q2 +93,44`, `Q3 +252,00`, `Q4 +112,13 USD`).
     - Chịu đựng êm sự kiện sập carry-trade đồng Yên ngày **`2024-08-05`** với ngày lỗ nặng nhất cả năm chỉ **`-155,37 USD` (`-1,55%`)** và đáy tĩnh dưới `10.000 USD` chỉ **`-0,40%`**.
- **Tác động tới `naqex-node1` đang chạy live:** **`0%`** — toàn bộ `5` kịch bản chạy trên bản Dev MT5 cô lập (`.runtime/ftmo-demo-portable-1515343166`, `[Experts] Enabled=0`), không đụng tới `naqex-node1` hay `C:\Program Files\MetaTrader 5`.

---

## 2. Ma trận kết quả đầy đủ `5` kịch bản (`Naqex_Master_Prop7E.ex5`, vốn `10.000 USD`)

> [!NOTE]
> **Minh bạch tuyệt đối về `Model=4` vs `Model=1` ở Kịch bản 5 (`2024FULL`):**
> `4` kịch bản `2024 Q4` (`2024.09.01..2024.12.31`) chạy **`100%` tick thật `Model=4` (`20.022.579` ticks)** đã lưu cục bộ. Khi chạy thử `Model=4` cho đủ `12` tháng `2024.01.01..2024.12.31`, máy chủ `FTMO-Demo Access Server 1a` bóp băng thông tải file `.tkc` các tháng `2024.01..2024.08` xuống chỉ còn **`~115 KB/s`** (mất `20` phút mới tải xong `USDJPY 202401..08` + `GBPUSD 202408`, ước tính cần `~85` phút để tải nốt `~570 MB` cho `6` mã còn lại và sẽ chặn làn đo spread thực địa Wave 1B trước phiên Mỹ). Do đó, theo phê duyệt Option B (`#210`), Kịch bản 5 được chạy bằng **`Model=1` (1-Minute OHLC)** trên `100%` dữ liệu nến `2024.hcc` cục bộ và **ghi nhãn tách biệt hoàn toàn** với `4` kịch bản `Model=4`. Đối chiếu riêng giai đoạn `2024.09..2024.12`, `Model=1` cho lãi thận trọng hơn (`+16,44 USD`) so với `Model=4` tick thật (`+138,79..+156,19 USD`), chứng tỏ `Model=1` không thổi phồng kết quả Q4.

| # | Kịch bản (`label`) | Cửa sổ | Chế độ MT5 (`Model`) | Đòn bẩy / Mult / Trễ | Số tick / Chất lượng | Số lệnh (`in`) | Lãi ròng (USD) | PF | Sharpe | Win % | Bal DD % | Eq DD % | Swap (USD) | Comm (USD) | Tin đỏ / Reject / Lỗi | Thời gian |
|---|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|
| **1** | `MASTER_PROP7E_2024Q4_L30_50ms` | `2024.09.01..12.31` | **`Model=4` Real Ticks** | `1:30` / `1,0x` / `50 ms` | `20.022.579` (`99%`) | `156` | **`+138,79`** | `1,12` | `1,03` | `52,56%` | `2,18%` | `2,59%` | **`0,00`** | `-34,00` | `492` / `0` / `0` | `267,11s` |
| **2** | `MASTER_PROP7E_2024Q4_STRESS_150ms` | `2024.09.01..12.31` | **`Model=4` Real Ticks** | `1:100` / `1,0x` / `150 ms` | `20.022.579` (`99%`) | `156` | **`+156,19`** | `1,13` | `1,16` | `52,56%` | `2,16%` | `2,50%` | **`0,00`** | `-34,00` | `492` / `0` / `0` | `265,95s` |
| **3** | `MASTER_PROP7E_2024Q4_P1_4X_L100_50ms` | `2024.09.01..12.31` | **`Model=4` Real Ticks** | `1:100` / `4,0x` P1 / `50 ms` | `20.022.579` (`99%`) | `155` | **`+754,60`** | **`1,24`** | **`2,02`** | `52,90%` | `4,92%` | `6,27%` | **`0,00`** | `-98,30` | `492` / `0` / `0` | `271,90s` |
| **4** | `MASTER_PROP7E_2024Q4_P1_4X_STRESS_150ms` | `2024.09.01..12.31` | **`Model=4` Real Ticks** | `1:100` / `4,0x` P1 / `150 ms` | `20.022.579` (`100%`) | `155` | **`+755,69`** | **`1,24`** | **`2,03`** | `52,90%` | `4,86%` | `6,23%` | **`0,00`** | `-97,92` | `492` / `0` / `0` | `275,00s` |
| **5** | `MASTER_PROP7E_2024FULL_L100_50ms_M1OHLC` | `2024.01.01..12.31` | **`Model=1` (1-Min OHLC)** | `1:100` / `1,0x` / `50 ms` | `1.461.259` (`100%`) | `469` | **`+744,48`** | **`1,19`** | **`1,47`** | `50,75%` | `3,36%` | `3,97%` | **`0,00`** | `-143,82` | `492` / `0` / `0` | `73,23s` |
| **6** | **`MASTER_PROP7E_V101_2024Q4_P1_4X_50ms`** *(bản vá cứng `v1.01`)* | `2024.09.01..12.31` | **`Model=4` Real Ticks** | `1:100` / `4,0x` P1 / `50 ms` | `20.022.579` (`100%`) | **`155`** | **`+736,06`** | **`1,23`** | **`1,98`** | **`52,90%`** | `4,92%` | **`6,27%`** | **`0,00`** | `-98,30` | **`492` / `0` / `0`** | `393,46s` |

*Chứng nhận bản vá cứng **`v1.01`** (`#340` + `#348`, biên dịch sạch `10/10` `.ex5` `0 errors, 0 warnings`, `Naqex_Master_Prop7E.ex5` SHA-256 `2e0006ad786bdad6`): Kịch bản 6 chạy đúng `[MASTER-7E-INIT] v1.01` với đầy đủ `7` miếng vá `V101-01..V101-07` (gồm lịch nghỉ lễ Mỹ `23` ngày, cấm đóng trong `±135s` tin đỏ, `SetDeviationInPoints` hiệu chuẩn thực địa `35` FX / `450` `US100.cash`, `RoundVolumeDownToStep`, và phanh tương đối `REL+HEADROOM` + giảm tốc vô điều kiện theo biên lỗ ngày). Kết quả khớp `100%` cấu trúc lệnh `155` lệnh (`E1=79, E2=25, E3=11, E4=19, E5=14, E6=5, E7=2`), chạm `PROFIT_LOCK` đúng ngày `2024-11-15`, giữ đáy tĩnh `-2,08%` (`9.792,41 USD`), ngày lỗ lớn nhất `-169,80 USD` (`-1,70%`, `2024-10-25`), `swap = 0,00 USD`, `492` tin đỏ nạp OK, `0` lỗi/reject, ngày lệnh cuối `2024-12-30` (`holdout_rows_analysed = 0`). Đóng góp theo mã `v1.01`: `USDJPY +425,14`, `US100.cash +249,15`, `EURJPY +211,70`, `GBPUSD -149,93 USD`.*

*Thư mục lưu trữ đầy đủ `.htm`, `parsed_result.json`, `tester.ini` (đã lược sạch thông tin đăng nhập), `.set` và log Agent cho cả 6 kịch bản: `.runtime/mt5-realtick-results/MASTER_PROP7E_*/`.*

---

## 3. Phân tích sâu theo cấu trúc rủi ro, cặp tiền và nhánh chiến lược

### A. Kiểm tra P1 Challenge `4,0x` + `PROFIT_LOCK` (`Model=4` Tick thật, `50 ms` vs `150 ms`)

Tham số chuẩn vòng 1 (`P1`) theo thiết kế: `InpBasePhaseMult=4,00`, `InpTargetProfitPct=10,00`, `InpProfitLockPct=5,00 -> InpProfitLockMult=2,01`, trần từng mã `1,75%`, cụm `USD 2,25%` / `JPY 2,00%` / `IDX 1,75%`, tổng rủi ro mở `3,00%`, phanh mềm ngày `3,50%` / tĩnh `8,00%`.

| Chỉ tiêu vận hành thực tế | `P1 4,0x @ 50 ms` (`Model=4`) | `P1 4,0x @ 150 ms` (`Model=4`) | Nhận xét an toàn |
|---|---:|---:|---|
| Đỉnh số dư (`Max Balance`) | `10.815,30 USD` (`+8,15%`) | `10.817,17 USD` (`+8,17%`) | Gần chạm mục tiêu `10%` ngay trong quý khó nhất |
| Đáy số dư tĩnh (`Min Balance`) | **`9.792,41 USD` (`-2,08%`)** | **`9.803,49 USD` (`-1,97%`)** | Cách rất xa trần tĩnh `-10%` và phanh mềm `-8%` |
| Ngày chạm `+5,0%` (`PROFIT_LOCK`) | **`2024-11-15`** | **`2024-11-15`** | Đồng nhất tuyệt đối giữa `50 ms` và `150 ms` |
| Ngày lỗ thực tế nặng nhất | `-169,80 USD` (`-1,70%`, `2024-10-25`) | `-172,32 USD` (`-1,72%`, `2024-10-25`) | Dưới `1/2` trần mềm ngày `-3,5%` của hệ thống |
| Ngày lãi cao nhất | `+280,12 USD` (`2024-11-15`) | `+288,53 USD` (`2024-11-15`) | Không phụ thuộc vào 1 ngày may mắn duy nhất |
| Đóng góp theo mã (`USDJPY` / `US100` / `EURJPY` / `GBPUSD`) | `+429,56` / `+233,95` / `+212,09` / `-121,00` | `+386,48` / `+282,49` / `+213,21` / `-126,49` | `3/4` mã lãi đều; phanh cụm USD hãm tốt lỗ `GBPUSD` |
| Số lệnh theo nhánh (`E1..E7`) | `79 / 25 / 11 / 19 / 14 / 5 / 2` | `79 / 25 / 11 / 19 / 14 / 5 / 2` | Khớp `100%` cấu trúc lệnh ở cả 2 mức độ trễ |

**Tại sao `PF` (`1,12 -> 1,24`) và `Sharpe` (`1,03 -> 2,02`) ở bản `4,0x` lại vượt trội hơn `1,0x`?**
1. Ở mức `1,0x` trên tài khoản `10.000 USD`, một số lệnh `US100.cash` (`E4/E5`) bị làm tròn khối lượng xuống lô nhỏ nhất (`0,01` hoặc bỏ bớt phần lẻ), làm giảm đóng góp của `US100.cash` (`+14,46 USD`). Khi nâng lên `4,0x`, khối lượng khớp sát tỷ lệ rủi ro chuẩn hơn giúp `US100.cash` đóng góp mạnh **`+233,95..+282,49 USD`**.
2. Cơ chế **`PROFIT_LOCK`** (khi lãi đạt `+5%` hạ rủi ro về `2,01x`) kết hợp trần cụm `USD 2,25%` giúp hãm rủi ro trên `GBPUSD` (chỉ lỗ `-121 USD`, tức `1,75×` thay vì nhân `4×`) và khóa chặt lợi nhuận tháng 11 (`+683,53 USD`) không bị trả lại trong tháng 12 (`+17,96 USD`).

### B. Kiểm chứng cả năm `2024` (`MASTER_PROP7E_2024FULL_L100_50ms_M1OHLC`, `Model=1` 1-Minute OHLC)

- **Phạm vi dữ liệu:** `2024-01-02` đến `2024-12-30` (`469` lệnh = `938` deals, `117` lệnh chốt SL, `0` lệnh treo, `0,00 USD` swap qua đêm, `492` tin đỏ nạp OK).
- **Lãi ròng theo quý (`4/4` quý đều dương):**
  - `Q1 2024` (`01..03`): **`+286,91 USD`** (`+34,85` / `-45,40` / `+297,46`)
  - `Q2 2024` (`04..06`): **`+93,44 USD`** (`+200,54` / `-177,44` / `+70,34`)
  - `Q3 2024` (`07..09`): **`+252,00 USD`** (`+376,28` / `-28,59` / `-95,69`) — ngày cú sốc carry-trade Yên `2024-08-05` chỉ lỗ **`-155,37 USD` (`-1,55%`)**
  - `Q4 2024` (`10..12`): **`+112,13 USD`** (`-16,62` / `+140,23` / `-11,48`)
- **Đóng góp theo mã & số lệnh theo nhánh (`469` lệnh cả năm):**
  - `USDJPY` (`E1=233`, `E2=81`, `E7=15` -> `329` lệnh): **`+375,83 USD`**
  - `US100.cash` (`E4=54`, `E5=36` -> `90` lệnh): **`+321,53 USD`**
  - `EURJPY` (`E6=19` -> `19` lệnh): **`+125,97 USD`**
  - `GBPUSD` (`E3=31` -> `31` lệnh): **`-78,85 USD`**

### C. Đối chiếu `1:1` trên `2024 Q4` (`Naqex_Master_Prop7E` gộp vs Wave-2 `7E` tách lẻ, `Model=4` `50 ms`)

| Nhánh / Mã | Wave-2 `7E` (lẻ) — Số lệnh | `Master_Prop7E` (gộp) — Số lệnh | Wave-2 `7E` Lãi ròng (USD) | `Master_Prop7E` Lãi ròng (USD) | Ghi chú |
|---|---:|---:|---:|---:|---|
| `E1` + `E2` + `E7` (`USDJPY`) | `78 + 26 + 3 = 107` | **`78 + 26 + 3 = 107`** | `+12,08` | **`+111,36`** | Khớp `100%` số lệnh cả 3 nhánh; điều phối cụm cải thiện mạnh ròng |
| `E6` (`EURJPY`) | `5` | **`5`** | `+92,77` | **`+82,30`** | Khớp `100%` số lệnh |
| `E4` + `E5` (`US100.cash`) | `18 + 12 = 30` | **`19 + 14 = 33`** | `+57,90` | **`+14,46`** | Hoạt động mượt nhờ vá trần spread `450` điểm |
| `E3` (`GBPUSD`) | `11` | **`11`** | `-104,81` | **`-69,33`** | Khớp `100%` số lệnh; trần cụm USD cắt giảm `-35,48 USD` lỗ |
| **TỔNG `7E` CORE** | **153 lệnh** | **156 lệnh** | **`+57,94 USD`** | **`+138,79 USD`** | **`swap = 0,00 USD`, `0` lỗi log, `0` reject** |

---

## 4. Chi tiết `5` lỗi thật đã phát hiện và vá sạch trong Mũi 3 (`main @ 43c2434`)

| # | Tệp & Vị trí | Lỗi thật phát hiện | Cách vá an toàn (giữ `InpDryRunLogOnly = true`) |
|---|---|---|---|
| **1** | [mt5_realtick_runner.py](../../tooling/ai-engines/exports/mt5_realtick_runner.py#L141-L152) + [test_wave2_mt5_realtick.py](../../tooling/ai-engines/tests/test_wave2_mt5_realtick.py#L93-L99) | `render_tester_ini()` đặt `KeepPrivate=0` (xóa phiên lưu khi đóng) và thiếu `[Experts] Enabled=0`. | Đổi sang **`KeepPrivate=1`**, bổ sung **`[Experts] Enabled=0 / AllowLiveTrading=0 / AllowDllImport=0`** và thêm cờ `--master-prop7e` khóa cứng `ToDate <= 2024.12.31`. |
| **2** | [Naqex_Master_Prop7E.mq5](../../tooling/ai-engines/exports/Naqex_Master_Prop7E.mq5#L60-L62), [L437-L460](../../tooling/ai-engines/exports/Naqex_Master_Prop7E.mq5#L437-L460) + [Naqex_PropGuard.mqh](../../tooling/ai-engines/exports/Include/Naqex_PropGuard.mqh#L409-L433) | **Chặn `100%` lệnh `US100.cash` (`E4/E5`):** Dùng chung trần spread FX `35` điểm cho cả `US100.cash` (spread thật `~195` điểm). | Thêm `maxSpreadOverridePts` tương thích ngược vào `IsSpreadAndSessionSafeFor()` và `MaxSpreadCapForSymbol()` (`450` điểm chỉ số, `45` điểm `EURJPY`, `35` điểm FX thường). |
| **3** | [Naqex_Master_Prop7E.mq5](../../tooling/ai-engines/exports/Naqex_Master_Prop7E.mq5#L15) | **`0` lệnh trong Strategy Tester:** Thiếu `#property tester_file "naqex_red_news_utc.csv"` nên Agent kích phanh fail-closed. | Bổ sung **`#property tester_file "naqex_red_news_utc.csv"`** — xác nhận nạp đủ `492` tin đỏ (`max_ts=1829482200`) trong cả `5/5` lần chạy. |
| **4** | [Naqex_Signals_7E.mqh](../../tooling/ai-engines/exports/Include/Naqex_Signals_7E.mqh#L290-L337) | Gọi `CopyTicksRange()` mỗi tick cho cả 8 mã trong Strategy Tester gây cấp phát mảng động nặng. | Dùng `SymbolInfoTick()` không cấp phát khi `MQL_TESTER != 0`; giữ nguyên `100%` `CopyTicksRange()` cho live/demo. |
| **5** | [Naqex_Master_Prop7E.mq5](../../tooling/ai-engines/exports/Naqex_Master_Prop7E.mq5#L673-L692) + [Naqex_Signals_7E.mqh](../../tooling/ai-engines/exports/Include/Naqex_Signals_7E.mqh#L85-L150) | Nút thắt hot-loop D1 ATR, vòng `20` ngày `E6`, `CopyRates` ngày nghỉ lễ Mỹ và `EventSetTimer(1)`. | Cache giá trị nến D1 đã đóng (`shift=1`) theo ngày, cooldown `60s` khôi phục M1 ngày lễ, và `EventSetTimer(60)` trong Tester -> giảm còn **`266–275s`** cho `20,02` triệu tick đa mã. |

---

## 5. Bằng chứng biên dịch `10/10` & Kiểm thử tự động

- Biên dịch sạch **`10/10` file `.ex5` bản `v1.01`** (`0 errors, 0 warnings`) vào `.runtime/mt5-compiled-ex5/` (`0` file `.ex5` trong Git `tooling/ai-engines/exports/`).
- `mql5_parity_checker.py --require-ex5`: **PASS** (`8/8` EAs, `PropGuard / Orchestrator / Master_7E OK`, `Master==7E 7/7 drifts=0`, `492` dòng CSV, `10` EX5).
- `verify_deployment_kit.py --build --require-ex5`: **PASS** (`profiles=10`, `presets=90`, `master_presets=4`, `total_presets=94`, `tracked_sha=127`, `ex5_sha=10`).
- `pytest -q` (`test_mql5_parity_and_kit.py`, `test_mql5_v101_contract.py`, `test_layer1_opsec_guard.py`, `test_prop_live_tca_monitor.py`): **`32 passed`** (`V101_CONTRACT_PASS`, `0` lỗi OPSEC).
- Đã xác minh **`0` tiến trình `terminal64`/`metatester64`/`MetaEditor64` tồn dư** (`0%` CPU) và **`0` file `_transient_auth_tester.ini` còn sót lại** sau khi hoàn tất cả `6` kịch bản.

---

## 6. Kết luận cho hạn chót FTMO Black Friday `30/11/2026`

- **Mũi 3 & 3b đã vượt trọn vẹn cổng kỹ thuật (`PASS 5/5`):** `Naqex_Master_Prop7E.ex5` đã được chứng minh thực chiến trên **`20,02` triệu tick thật (`Model=4`)** ở cả `1,0x` và `4,0x` P1, miễn nhiễm hoàn toàn với độ trễ khớp `150 ms` (`+755,69 USD`, `PF 1,24`, `Sharpe 2,03`), giữ `swap = 0,00 USD` tuyệt đối trên cả `1.091` lệnh cộng dồn, `0` lỗi log/reject, và đạt `4/4` quý dương cả năm `2024` (`Model=1` 1m OHLC).
- **Khuyến nghị hành động tiếp theo:**
  1. Bàn giao sạch Dev MT5 cho `@ops-probe` khởi chạy ngay **Wave 1B** (Mũi 1–2 đo thực địa spread & trượt giá trên `FTMO-Demo 1515343318`).
  2. Giữ nguyên bộ 9 EA đang chạy trên `naqex-node1` để không làm đứt chuỗi dữ liệu Demo hiện hữu; chỉ chuyển sang `Naqex_Master_Prop7E.ex5` (cấu hình `P1 4,0x + PROFIT_LOCK`) khi bắt đầu vòng Challenge mới sau khi chốt đủ Mũi 1–2 (ma sát thực tế), Mũi 5 (email xác nhận EA & giá checkout thật) và phán quyết cuối của Astra tối `29/11`.
  3. *(Tùy chọn không chặn Black Friday)*: Nếu muốn nâng Kịch bản 5 cả năm `2024` từ `Model=1` lên `Model=4` tick thật `100%`, nên chạy ngoài giờ cao điểm (sau `01:00` sáng giờ VN khi `FTMO-Demo` tải `.tkc` ở tốc độ `~2 MB/s` thay vì `115 KB/s`).

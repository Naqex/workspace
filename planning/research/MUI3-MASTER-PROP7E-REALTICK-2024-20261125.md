---
title: "Mũi 3 — Kiểm thử Real-Tick 2024 & Vá Lỗi Naqex_Master_Prop7E.ex5"
date: 2026-11-25
lane: mql5-builder
status: BLOCKED_AWAITING_DEV_DEMO_LOGIN
holdout_rows_analysed: 0
order_send_count: 0
canonical_dev_mt5: "D:\\ANNAM\\TradingWorkspace\\.runtime\\ftmo-demo-portable-1515343166"
naqex_node1_touched: false
---

# Mũi 3 — Kiểm thử Real-Tick 2024 & Vá Lỗi `Naqex_Master_Prop7E.ex5`

## 1. Tóm tắt ngắn gọn (Plain Vietnamese)

- **Đã sửa xong 4 lỗi thật quan trọng** trong quá trình kiểm tra mã nguồn và chạy thử MT5 Strategy Tester `Model=4` cho `Naqex_Master_Prop7E.ex5` — trong đó có **2 lỗi nghiêm trọng** mà nếu không sửa sẽ làm `US100.cash` (`E4/E5`) bị chặn 100% lệnh hoặc toàn bộ Strategy Tester ra 0 lệnh!
- **Biên dịch sạch 10/10 file `.ex5` (`0 errors, 0 warnings`)** bằng bản MT5 Dev duy nhất trên máy (`.runtime\ftmo-demo-portable-1515343166\MetaEditor64.exe`), đồng bộ lịch tin đỏ `492` dòng (`6` đồng tiền: `AUD, CAD, EUR, GBP, JPY, USD`), cập nhật khóa kiểm tra SHA-256 (`122` file theo dõi + `10` file `.ex5`) và vượt **100% kiểm thử tự động (`35/35` pytest PASS)**.
- **Trạng thái lượt chạy live `Model=4` năm 2024 trên máy Dev:** Hiện đang **`BLOCKED_AWAITING_DEV_DEMO_LOGIN`** vì phiên MT5 Dev gần nhất ngày `24/11/2026` từng chạy với `connector.ini` có `KeepPrivate=0`, làm MT5 xóa mật khẩu tài khoản `FTMO-Demo 1515343166` khỏi `accounts.dat` của máy Dev khi đóng. Khi chưa đăng nhập lại, MT5 Build 6230 treo ở bước đồng bộ lịch sử `USDJPY` cho mọi EA (đã kiểm chứng đối chứng trên cả `Naqex_Master_Prop7E.ex5` lẫn EA đã chạy tốt trước đó là `Naqex_WB_TOKYO_BOX_USDJPY.ex5`).
- **Tác động tới `naqex-node1` đang chạy live:** **`0%` — KHÔNG ảnh hưởng và KHÔNG cần đồng bộ hay khởi động lại `naqex-node1`.** Máy `naqex-node1` hiện đang chạy bộ 9 EA bản cũ (`Naqex_AccountOrchestrator` + 8 `Naqex_WB_*`), chưa chạy `Naqex_Master_Prop7E.ex5`. Chúng tôi tuyệt đối không chạm vào `naqex-node1`, không đụng dữ liệu Holdout `2025+` (`holdout_rows_analysed = 0`) và không vượt rào xác thực (`OrderSend = 0`).

---

## 2. Chi tiết 4 lỗi thật đã phát hiện và vá sạch

| # | Tệp & Dòng | Lỗi thật phát hiện | Cách vá an toàn (giữ `InpDryRunLogOnly = true`) |
|---|---|---|---|
| **1** | [mt5_realtick_runner.py](../../tooling/ai-engines/exports/mt5_realtick_runner.py#L141-L152) + [test_wave2_mt5_realtick.py](../../tooling/ai-engines/tests/test_wave2_mt5_realtick.py#L93-L99) | `render_tester_ini()` đặt `KeepPrivate=0` (xóa mật khẩu `FTMO-Demo` đã lưu sau khi đóng) và thiếu `[Experts] Enabled=0` (nguy cơ nạp chart live của tài khoản `1515343166` đang chạy trên `naqex-node1`). | Đổi sang **`KeepPrivate=1`**, bổ sung **`[Experts] Enabled=0 / AllowLiveTrading=0 / AllowDllImport=0`**, cập nhật `KeepPrivate=1` vào `.runtime\ftmo-demo-portable-1515343166\{connector.ini, config\common.ini}` (UTF-16LE, 0 mật khẩu), và thêm cờ 1-lệnh `--master-prop7e` có khóa cứng `ToDate <= 2024.12.31`. |
| **2** | [Naqex_Master_Prop7E.mq5](../../tooling/ai-engines/exports/Naqex_Master_Prop7E.mq5#L60-L62), [L437-L460](../../tooling/ai-engines/exports/Naqex_Master_Prop7E.mq5#L437-L460) + [Naqex_PropGuard.mqh](../../tooling/ai-engines/exports/Include/Naqex_PropGuard.mqh#L409-L433) | **Lỗi chặn 100% lệnh `US100.cash` (`E4/E5`):** Vì `Master_Prop7E` gom 7 engine vào 1 EA duy nhất nên toàn bộ dùng chung 1 biến `InpGuardMaxSpreadPoints = 35.0` (mức dành cho FX). Trong khi đó spread bình thường của `US100.cash` trên FTMO là `~195` điểm (`> 35`), khiến `E4` và `E5` bị chặn 100% (`ORDER_BLOCKED_SPREAD`). | Thêm tham số tùy chọn `maxSpreadOverridePts = -1.0` (tương thích ngược 100% với 8 EA lẻ) vào `IsSpreadAndSessionSafeFor()`, và thêm `InpMaxIndexSpreadPoints = 450.0` (cho `US100/NAS100/US500/SPX`), `InpMaxEurJpySpreadPoints = 45.0` (`EURJPY`), giữ nguyên `35.0` cho FX khác qua `MaxSpreadCapForSymbol()`. |
| **3** | [Naqex_Master_Prop7E.mq5](../../tooling/ai-engines/exports/Naqex_Master_Prop7E.mq5#L15) | **Lỗi `0` lệnh trong Strategy Tester do thiếu `#property tester_file`:** PropGuard v3.0 chặn an toàn (fail-closed) khi thiếu `naqex_red_news_utc.csv`. Trong MT5 Strategy Tester, Agent chạy trong thư mục cách ly `Tester\Agent-*\MQL5\Files\` và chỉ tự động chép CSV vào nếu file nguồn khai báo `#property tester_file`. | Bổ sung **`#property tester_file "naqex_red_news_utc.csv"`** ngay đầu `Naqex_Master_Prop7E.mq5` để MT5 tự đóng gói/chuyển đủ `492` sự kiện tin đỏ vào Agent khi chạy Strategy Tester. |
| **4** | [Naqex_Signals_7E.mqh](../../tooling/ai-engines/exports/Include/Naqex_Signals_7E.mqh#L290-L337) | Trong `Model=4` đa cặp tiền cả năm 2024 (~60–80 triệu tick), gọi `CopyTicksRange()` cho cả 8 mã ở mỗi tick tạo hàng trăm triệu lần cấp phát mảng động trong Strategy Tester. | Dùng `SymbolInfoTick()` không cấp phát bộ nhớ khi `MQLInfoInteger(MQL_TESTER) != 0`, giữ nguyên 100% `CopyTicksRange()` khi chạy live/demo. |

---

## 3. Bằng chứng biên dịch `10/10` & Kiểm thử tự động

Biên dịch bằng `D:\ANNAM\TradingWorkspace\.runtime\ftmo-demo-portable-1515343166\MetaEditor64.exe`, toàn bộ nhị phân lưu tại `.runtime\mt5-compiled-ex5\` (`0` file `.ex5` lọt vào thư mục Git `tooling/ai-engines/exports/`):

| Tên nhị phân (`.ex5`) | Kích thước (bytes) | Lỗi / Cảnh báo |
|---|---:|---|
| `Naqex_Master_Prop7E.ex5` | `106,452` | `0 errors, 0 warnings` |
| `Naqex_AccountOrchestrator.ex5` | `54,426` | `0 errors, 0 warnings` |
| `Naqex_WB_TOKYO_BOX_USDJPY.ex5` | `62,920` | `0 errors, 0 warnings` |
| `Naqex_WB_EXP080_USDJPY.ex5` | `63,238` | `0 errors, 0 warnings` |
| `Naqex_WB_EXP080_VOLHIGH_GBPUSD.ex5` | `63,492` | `0 errors, 0 warnings` |
| `Naqex_WB_SESS_CONT_BRK40_US100.ex5` | `63,016` | `0 errors, 0 warnings` |
| `Naqex_WB_IDX_RS_US100_LEAD_1130.ex5` | `63,726` | `0 errors, 0 warnings` |
| `Naqex_WB_VOLCOMP_EXP75_EURJPY.ex5` | `64,682` | `0 errors, 0 warnings` |
| `Naqex_WB_NY_RISK_FLOW_10ET_USDJPY.ex5` | `65,778` | `0 errors, 0 warnings` |
| `Naqex_WB_FX_USD_BASKET_12U_Z35.ex5` | `66,266` | `0 errors, 0 warnings` |

- `mql5_parity_checker.py --require-ex5`: **PASS** (`8/8` EAs, `PropGuard OK`, `Orchestrator OK`, `Master_7E OK`, `492` dòng CSV `['AUD', 'CAD', 'EUR', 'GBP', 'JPY', 'USD']`, `10` EX5 sạch).
- `verify_deployment_kit.py --require-ex5`: **PASS** (`profiles=10`, `presets=90`, `tracked_sha=122`, `ex5_sha=10`).
- `pytest` trên 4 bộ kiểm thử (`test_wave2_mt5_realtick.py`, `test_mql5_parity_and_kit.py`, `test_lab10_and_ops_upgrades.py`, `test_quant_factory_suite.py`): **`35 passed`**.

---

## 4. Nguyên nhân gốc khiến lượt chạy `Model=4` năm 2024 bị chặn trên máy Dev

1. **Bằng chứng log trên máy Dev (`.runtime\ftmo-demo-portable-1515343166\logs\20261124.log` & `20261125.log`):**
   - Lần cuối máy Dev đăng nhập `FTMO-Demo 1515343166` là `24/11 15:35:18` qua `connector.ini` có `KeepPrivate=0`. Trong MT5, `KeepPrivate=0` không lưu mật khẩu vào `accounts.dat`, nên sau khi tắt máy Dev, mật khẩu đã bị xóa trắng.
   - Hôm nay (`25/11`), khi chạy `terminal64.exe /portable /config:tester.ini`, MT5 đợi 48 giây rồi báo `Tester: not synchronized with trade server [0]`. Sau đó `MetaTester 5` (Build 6230) đứng yên tại dòng `Symbols USDJPY: symbol synchronized` và không tiến sang đồng bộ lịch sử cho **cả `Naqex_Master_Prop7E.ex5` lẫn EA đối chứng `Naqex_WB_TOKYO_BOX_USDJPY.ex5`** (`2024.09.02..2024.09.06`).
2. **Lưu ý kỹ thuật về vùng tick thật của máy chủ `FTMO-Demo`:**
   - Trong `.runtime\ftmo-demo-portable-1515343166\bases\FTMO-Demo\`: dữ liệu nến M1 (`2024.hcc`) đã có đủ cả 12 tháng `2024.01..2024.12` cho tất cả 8 mã; còn dữ liệu tick thật (`.tkc`) trên `FTMO-Demo` bắt đầu từ **`2024.09.02`** cho 7/8 mã (`USDJPY`, `GBPUSD`, `EURJPY`, `US100.cash`, `US500.cash`, `AUDUSD`, `USDCAD`) và từ `2024.01` cho `EURUSD`.
   - Do đó sau khi đăng nhập lại, nên chạy cả 2 cửa sổ: **`2024.01.01..2024.12.31`** (kiểm tra đủ cả năm 2024 với `Model=4`) và **`2024.09.01..2024.12.31`** (đối chiếu 1:1 trực tiếp trên vùng tick thật 100% với kết quả 7E Wave-2 bên dưới).

---

## 5. Mốc đối chiếu Real-Tick `Model=4` hiện có của 7E (`2024.09.01..2024.12.31`)

Trích từ artifact đã kiểm chứng `.runtime/mt5-realtick-results/realtick_matrix_summary.json` (`FTMO-Demo 1515343166`, độ trễ `50 ms`, `Model=4` Real Ticks, `Leverage 1:30`, rủi ro gốc `1.0x`):

| Engine | Mã | Số lệnh (`50 ms`) | Lãi ròng MT5 (USD) | PF | Equity DD (%) | Tổng Swap (USD) | Phí Comm (USD) | Khớp ngày vs Python | Kết quả |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| `E1_USDJPY_TOKYO` | `USDJPY` | 78 | -40.75 | 0.93 | 2.30% | **0.00** | -17.78 | 95.0% | PASS |
| `E2_USDJPY_EXP80` | `USDJPY` | 26 | +73.36 | 1.26 | 1.17% | **0.00** | -9.36 | 69.0% | PASS |
| `E3_GBPUSD_VH` | `GBPUSD` | 11 | -104.81 | 0.53 | 2.44% | **0.00** | -6.32 | 91.7% | PASS |
| `E4_US100_SESS40` | `US100.cash` | 18 | +40.15 | 1.36 | 0.83% | **0.00** | 0.00 | 94.7% | PASS |
| `E5_US100_RS1130` | `US100.cash` | 12 | +17.75 | 1.25 | 0.63% | **0.00** | 0.00 | 68.8% | PASS |
| `E6_EURJPY_VOLCOMP` | `EURJPY` | 5 | +92.77 | 102.95 | 0.41% | **0.00** | -1.82 | 80.0% | PASS |
| `E7_USDJPY_NY10ET` | `USDJPY` | 3 | -20.53 | 0.33 | 0.62% | **0.00** | -0.80 | 100.0% | PASS |
| **Tổng 7E Core (lẻ)** | **4 mã** | **153** | **+57.94** | — | — | **0.00** | **-36.08** | — | **7/7 PASS** |

*(Tất cả 7/7 engine lõi đạt `swap = 0.00 USD`, `0` lỗi log Agent, `0` lệnh thiếu cắt lỗ; sau khi hoàn tất đăng nhập Dev MT5, lượt chạy `Naqex_Master_Prop7E.ex5` sẽ đối chiếu trực tiếp tổng lệnh, tổng lãi/lỗ, DD gộp và trần nhóm yếu tố USD/JPY/US100 so với bảng trên.)*

---

## 6. Thao tác 10 giây của chủ sở hữu để mở khóa & lệnh chạy 1-click sau đăng nhập

### Bước 1 — Lưu lại phiên `FTMO-Demo 1515343166` đúng 1 lần trên máy Dev (10 giây)
1. Mở trực tiếp `D:\ANNAM\TradingWorkspace\.runtime\ftmo-demo-portable-1515343166\terminal64.exe /portable`.
2. **Đảm bảo nút `Algo Trading` đang TẮT (biểu tượng màu đỏ)** để máy Dev không gửi bất kỳ lệnh nào lên tài khoản Demo đang chạy trên `naqex-node1`.
3. Vào `File -> Login to Trade Account`, đăng nhập `1515343166` (`Server: FTMO-Demo`), tích chọn **`Save password`** (đã khóa sẵn `KeepPrivate=1` trong `Config\common.ini` và `connector.ini` để không bị xóa lại).
4. Đợi góc dưới phải hiện kết nối xanh, rồi đóng MT5 Dev.

### Bước 2 — Chạy 1 lệnh duy nhất để hoàn tất Real-Tick `Model=4` năm 2024 (tự khóa Holdout `<= 2024.12.31`)

```powershell
# 1) Cả năm 2024 trên cấu hình FTMO Standard 10K (1:100, 1.0x Funded, Red-News 492 dòng BẬT)
D:\ANNAM\TradingWorkspace\.runtime\quant-audit-v24\Scripts\python.exe tooling/ai-engines/exports/mt5_realtick_runner.py --master-prop7e --from-date 2024.01.01 --to-date 2024.12.31 --leverage 100 --base-mult 1.00 --latencies 50

# 2) Đối chiếu 1:1 vùng Real-Tick 100% (2024.09.01..2024.12.31, 1:30 Swing vs Wave-2 7E)
D:\ANNAM\TradingWorkspace\.runtime\quant-audit-v24\Scripts\python.exe tooling/ai-engines/exports/mt5_realtick_runner.py --master-prop7e --from-date 2024.09.01 --to-date 2024.12.31 --leverage 30 --base-mult 1.00 --latencies 50
```

Kết quả HTML, log Agent (`[PROPGUARD-OK] Loaded 492 red-news events`), tổng swap/SL và `parsed_result.json` sẽ được lưu tự động vào `.runtime/mt5-realtick-results/MASTER_PROP7E_*`.

---

## 7. Gợi ý cho mốc Black Friday `30/11/2026`

- **Không nên chuyển ngay sang `Naqex_Master_Prop7E.ex5` trên tài khoản tiền thật ngày `30/11` khi chưa chạy xong Bước 2 ở trên** (vì cần bằng chứng `Model=4` thực tế xác nhận 0 lỗi khớp lệnh đa mã, `swap = 0` và `492` tin đỏ nạp đúng trong Agent).
- **Phương án an toàn cho `30/11`:** Trong khi hoàn tất lượt chạy `Model=4` cho `Master_Prop7E` (chỉ mất 10 giây đăng nhập + ~5 phút chạy Tester), bộ **9 EA lõi bản cũ** (`Naqex_AccountOrchestrator` + 7 EA lõi đã đạt `7/7` Real-Tick `PASS` `swap=0` và đang chạy thực chiến trên `naqex-node1`) vẫn là tuyến phòng thủ sẵn sàng, không bị ảnh hưởng bởi các sửa đổi trên `Master_Prop7E`.

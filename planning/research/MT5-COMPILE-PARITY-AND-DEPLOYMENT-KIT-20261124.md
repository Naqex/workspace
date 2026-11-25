# Biên Bản Nghiệm Thu Tier 1 (M1.1–M1.5): Biên Dịch MQL5, Kiểm Tra Parity, Bộ Preset 10 Hồ Sơ & Watchdog MT5

- **Lane thực hiện:** Lane A (`mql5-builder`) — Naqex Quant Pod Overnight 8-Tier Build
- **Ngày hoàn tất (UTC):** `2026-11-23` (bàn giao sáng `2026-11-24`)
- **Ràng buộc an toàn:** `OrderSend = 0`, `InpDryRunLogOnly = true` & `InpGuardDryRunLogOnly = true` giữ nguyên mặc định trên toàn bộ `9/9` file `.mq5` và `Include/Naqex_PropGuard.mqh`; **0** đăng nhập broker; Holdout `2025–2026` giữ nguyên niêm phong (`NATIVE_FTMO_HOLDOUT_LOCK.json` untouched).
- **Trình biên dịch thực tế:** `C:\Program Files\MetaTrader 5\MetaEditor64.exe` (MetaTrader 5 x64 build `6230`, include root `...\D0E8209F77C8CF37AD8BF550E51FF075\MQL5`). *(Ghi chú môi trường: thư mục `C:\Program Files\FTMO Global Markets MT5 Terminal\` hiện chỉ còn thư mục `Config/`, không có `MetaEditor64.exe`/`terminal64.exe` nên sử dụng fallback chuẩn `C:\Program Files\MetaTrader 5\`.)*

---

## 1. M1.1 — Biên Dịch MetaEditor64 Thực Tế (`9/9` File: `0 errors, 0 warnings`) & Các Bản Vá An Toàn

Trong quá trình kiểm tra từng dòng trước biên dịch, phát hiện và vá sạch **5 lỗi tiềm ẩn vận hành** trong `Naqex_PropGuard.mqh` và các EA (vẫn giữ `0` red flags qua `audit_open_source_mq5` và tương thích 100% test hồi quy cũ):

1. **Đấu nối `InpMaxDailyLossPct` vào `CNaqexPropGuard::Init()`:** Trước đây cả 8 EA khai báo `InpMaxDailyLossPct` nhưng không truyền vào `g_guard`; nay `IsDailyLossBreached()` lấy ngưỡng nghiêm ngặt hơn `MathMin(InpGuardMaxDailyLossPct, m_eaMaxDailyLossPct)` (fail-closed).
2. **Bảo vệ đa cặp tiền cho Satellite S6 (`Naqex_WB_FX_USD_BASKET_12U_Z35.mq5`):** Bổ sung `IsInsideRedNewsWindowFor(sym)` và `IsSpreadAndSessionSafeFor(sym)` trong `Naqex_PropGuard.mqh`, kiểm tra tin đỏ và spread trên **đúng cặp tiền được chọn vào lệnh** (`GBPUSD`/`EURUSD`/`AUDUSD`/`USDCAD`) thay vì cặp biểu đồ, đồng thời cấu hình `ConfigureFillingMode` trước khi đóng lệnh.
3. **Cấu hình `ConfigureFillingMode` khi đóng khẩn cấp trong `Naqex_AccountOrchestrator.mq5`:** Gọi `CNaqexPropGuard::ConfigureFillingMode(g_orchTrade, sym)` trước `PositionClose(ticket)` để chống lỗi `retcode 10030` khi đóng đồng thời FX và `US100.cash`.
4. **Cửa sổ rollover & CSV tin đỏ chống lệch cột:** Vá `IsSpreadAndSessionSafeFor()` hỗ trợ cả khung rollover không vắt qua nửa đêm (`Start < End`), bổ sung map `GER40 -> EUR`, và xả cột thừa cuối dòng trong `LoadRedNewsCsv()` (`while(!FileIsLineEnding(fh))`) để an toàn tuyệt đối khi Lane B mở rộng cột lịch tin 2027.
5. **Bền vững khởi động lại giữa phiên cho E1 (`Naqex_WB_TOKYO_BOX_USDJPY.mq5`):** Lưu `BOXDAY`/`BOXTOP`/`BOXBOT` vào `GlobalVariable` của MT5 để không mất biên hộp Tokyo nếu khởi động lại MT5 trong khung `03:00–10:00 UTC`.

### Bảng kết quả biên dịch thực tế (`.ex5` lưu tại `.runtime/mt5-compiled-ex5/`, `0` file `.ex5` trong Git `exports/`)

| File nguồn (`.mq5`) | Binary (`.ex5`) | Kích thước (bytes) | SHA-256 (12 ký tự) | Log MetaEditor64 | Thời gian |
|---|---|---:|---|---|---:|
| `Naqex_AccountOrchestrator.mq5` | `Naqex_AccountOrchestrator.ex5` | 35242 | `710e22554f45` | 0 err / 0 warn | 721 ms |
| `Naqex_WB_EXP080_USDJPY.mq5` | `Naqex_WB_EXP080_USDJPY.ex5` | 47800 | `7ca57e2e436b` | 0 err / 0 warn | 1211 ms |
| `Naqex_WB_EXP080_VOLHIGH_GBPUSD.mq5` | `Naqex_WB_EXP080_VOLHIGH_GBPUSD.ex5` | 47992 | `d662b636219b` | 0 err / 0 warn | 1312 ms |
| `Naqex_WB_FX_USD_BASKET_12U_Z35.mq5` | `Naqex_WB_FX_USD_BASKET_12U_Z35.ex5` | 50616 | `85fc4dfe5114` | 0 err / 0 warn | 1172 ms |
| `Naqex_WB_IDX_RS_US100_LEAD_1130.mq5` | `Naqex_WB_IDX_RS_US100_LEAD_1130.ex5` | 48240 | `88ef1ae7ff78` | 0 err / 0 warn | 1199 ms |
| `Naqex_WB_NY_RISK_FLOW_10ET_USDJPY.mq5` | `Naqex_WB_NY_RISK_FLOW_10ET_USDJPY.ex5` | 50706 | `3205297820f1` | 0 err / 0 warn | 1451 ms |
| `Naqex_WB_SESS_CONT_BRK40_US100.mq5` | `Naqex_WB_SESS_CONT_BRK40_US100.ex5` | 48196 | `179ba92061d7` | 0 err / 0 warn | 1867 ms |
| `Naqex_WB_TOKYO_BOX_USDJPY.mq5` | `Naqex_WB_TOKYO_BOX_USDJPY.ex5` | 48960 | `44834074b46c` | 0 err / 0 warn | 1271 ms |
| `Naqex_WB_VOLCOMP_EXP75_EURJPY.mq5` | `Naqex_WB_VOLCOMP_EXP75_EURJPY.ex5` | 49366 | `ab0be926d011` | 0 err / 0 warn | 1310 ms |

- **Static audit (`audit_open_source_mq5`):** `10/10` file (`9 .mq5 + 1 .mqh`) đạt `CLEAN_FOR_PYTHON_REPLICATION` với `0` red flags.

---

## 2. M1.2 — Trình Kiểm Tra Parity Tự Động MQL5 <-> Python (`mql5_parity_checker.py`)

- **File:** [mql5_parity_checker.py](../../tooling/ai-engines/exports/mql5_parity_checker.py)
- **Kết quả chạy thực tế (`--require-ex5`):** **`PASS (8/8 EAs)`**, `PropGuard OK`, `Orchestrator OK`, `Red-News CSV OK` (`343` dòng `2018–2027`, tiền tệ `EUR/GBP/JPY/USD` đã đồng bộ sau M5.3 của Lane B), `Compiled EX5 OK (9 checked)`.
- **Các hạng mục kiểm chéo tự động:**
  - Đối khớp toàn bộ 8 EA với [PORTFOLIO-REGISTRY.json](PORTFOLIO-REGISTRY.json) và các hàm Python đóng băng (`pass5`, `pass17`, `pass22`, `pass26`, `pass27`, `pass28`): Magic Number duy nhất liên tiếp `20261122..20261129` nằm gọn trong dải Orchestrator `20261120..20261199`.
  - Xác nhận không có lookahead (`CopyBuffer(..., 0, 1, 1, ...)` dùng nến D1 đã đóng `shift=1`, `iClose(..., PERIOD_M1, 1)` cho cross-asset z-return).
  - Xác nhận dây nối `Naqex_PropGuard.mqh`, `SYMCAP_100` (`InpGuardMaxSymbolRiskPct = 1.00`), lịch tin đỏ `naqex_red_news_utc.csv` (`±300s`), `InpDryRunLogOnly = true` trên mọi file nguồn.

---

## 3. M1.3 — Bộ Preset 10 Hồ Sơ (90 File `.set`) & Bộ Cài Tự Kiểm Chứng (`deployment_kit/`)

- **Trình build & tự kiểm chứng:** [verify_deployment_kit.py](../../tooling/ai-engines/exports/verify_deployment_kit.py)
- **Manifest SHA-256:** [manifest.sha256.json](../../tooling/ai-engines/exports/deployment_kit/manifest.sha256.json) (`114` file tracked + `9` binary `.ex5` trong `.runtime/mt5-compiled-ex5/`).
- **Thẻ kích hoạt buổi sáng 5 bước (tiếng Việt):** [ACTIVATION-CARD-LOCAL-MT5.md](../../tooling/ai-engines/exports/deployment_kit/ACTIVATION-CARD-LOCAL-MT5.md).
- **Đồng bộ tham số M2.2 từ `@risk-auditor` (`seed=20261124`):**
  - Toàn bộ 4 hồ sơ P1 đã nạp đúng hệ số hiệu chỉnh từ [PROP-EV-FRONTIER-BALANCED-VS-SPRINT-20261124.md](PROP-EV-FRONTIER-BALANCED-VS-SPRINT-20261124.md), tách gọn qua `EA_RiskScale × Orch_InpBasePhaseMult` để tôn trọng tuyệt đối biên kẹp `[0.20, 3.50]` của `NQXG_GLOBAL_RISK_MULT`:
    - `FTMO_P1_Balanced_3to6m` & `The5ers_HighStakes_P1_Balanced`: hiệu dụng `4.00x` (`1.50x` EA × `2.67` Orch, Amber `7.5%/1.00x`, Red `9.0%/0.75x`, KillDaily `4.2%`, KillStatic `9.2%`, MaxSymRisk `3.00%`).
    - `FTMO_P1_Sprint_1to3m` & `The5ers_HighStakes_P1_Sprint`: hiệu dụng `4.75x` (`1.50x` EA × `3.17` Orch, Amber/Red `9.9%/1.00x`, KillDaily `4.3%`, KillStatic `9.5%`, MaxSymRisk `3.50%`).
    - `FTMO_P2_Verify`: hiệu dụng `2.50x` (`1.00x` EA × `2.50` Orch, `PORT_7E` core, S6 tắt `0.00%`, KillDaily `3.5%`, MaxSymRisk `2.50%`).
    - `FTMO_Funded_Swing_Safe`, `FTMO_Funded_Std_RedNews`, `The5ers_HighStakes_Funded`: hiệu dụng `1.00x`, `PORT_7E` core (S6 tắt `0.00%`), `SYMCAP_100 = 1.00%`, KillDaily `2.5%`, KillStatic `7.5%`.
- **Phát hiện thực tế cứu vận hành (`US100.cash` spread):** Theo snapshot thực đo FTMO Demo (`ftmo_indices_spec_snapshot.json`), spread thường của `US100.cash` là `195` points (`1.95` điểm chỉ số, `digits=2`) trong khi mặc định FX là `35` points. Nếu giữ `35.0`, E4 & E5 sẽ bị chặn 100% lệnh! Toàn bộ 10 bộ `.set` của E4 & E5 đã cài tường minh `InpGuardMaxSpreadPoints = 450.0` (`4.50` điểm chỉ số), E6 `EURJPY = 45.0`, các cặp FX còn lại `35.0`.
- **Chính sách khóa an toàn (`ARM-LOCKED`):** Chỉ `FTMO_FreeTrial_Demo` đặt `InpDryRunLogOnly=false` để kiểm thử khớp lệnh giấy trên Free Trial Demo; `FTMO_FreeTrial_DryRun` và **toàn bộ 8 hồ sơ Challenge/Funded trả phí đều khóa `InpDryRunLogOnly=true` + `InpGuardDryRunLogOnly=true`** đến khi chủ tài khoản tự tay mở khóa sau khi Free Trial đạt TCA `GREEN`.

---

## 4. M1.4 — Kiểm Tra MT5 Strategy Tester Offline Cô Lập (Trung Thực 100%)

- **Kiểm tra dữ liệu lịch sử local (read-only):**
  - `C:\Program Files\MetaTrader 5\Bases\Default\History\` có sẵn dữ liệu Development `2023.hcc` và `2024.hcc` (~16 MB/năm) cho `USDJPY`, `GBPUSD`, `EURUSD`, `USDCHF`.
  - `.runtime/ftmo-demo-full13-20261119/` có các file `.hcc` lịch sử từ đợt đo spec trước.
- **Kết quả chạy thử sandbox `/portable` hoàn toàn không đăng nhập broker:**
  - Tạo sandbox cô lập tại `.runtime/mt5-offline-tester/` chỉ chứa dữ liệu Dev `2023–2024` (`FromDate=2024.01.02`, `ToDate=2024.03.29`, `0` dòng Holdout `2025+`), `Login=0`, `InpDryRunLogOnly=true`.
  - MetaTrader 5 x64 build `6230` khởi chạy đọc cấu hình `tester_smoke.ini` thành công nhưng từ chối chạy Strategy Tester với mã thoát `-1000012353` và thông báo gốc trong log (`Tester/logs/20261123.log`):
    > `tester not started because the account is not specified`
- **Hành động xử lý:** Tuân thủ nghiêm nguyên tắc `OrderSend = 0` / không đăng nhập tài khoản broker tự động, không vượt rào; ghi nhận trung thực giới hạn trên của MT5 build `6230` và đã tích hợp sẵn **Checklist 1-Click GUI Strategy Tester (60 giây)** ngay trong [ACTIVATION-CARD-LOCAL-MT5.md](../../tooling/ai-engines/exports/deployment_kit/ACTIVATION-CARD-LOCAL-MT5.md) để chạy ngay sau khi bạn đăng nhập FTMO Free Trial Demo.

---

## 5. M1.5 — Watchdog Gọn Nhẹ Cho PC Local & Windows VPS (`ops_watchdog/`)

- **File:** [naqex_mt5_watchdog.ps1](../../tooling/ai-engines/exports/deployment_kit/ops_watchdog/naqex_mt5_watchdog.ps1)
- **Tính năng đã kiểm thử dry-run thực tế:**
  - Kiểm tra tiến trình `terminal64`, kiểm tra độ tươi `naqex_heartbeat.json` (`StaleAfterSec = 180s`), phát hiện `kill_switch = true`, `orphan_no_sl > 0`, chế độ phanh `AMBER_BRAKE`/`RED_BRAKE`.
  - Tự xoay vòng file log (`.bak`) khi vượt `MaxLogBytes` (mặc định `5 MB`, giữ `5` bản).
  - Sink cảnh báo dạng plugin: mặc định ghi JSONL cục bộ (`naqex_watchdog_alerts.jsonl`, **0 secret**, **0 kết nối mạng**); chỉ gửi webhook khi truyền rõ `-EnableWebhook` và thiết lập biến môi trường `NAQEX_ALERT_WEBHOOK_URL`.

---

## 6. Kết Quả Kiểm Thử Tự Động (`pytest`)

- **Lệnh kiểm chứng:**
  `D:\ANNAM\TradingWorkspace\.runtime\quant-audit-v24\Scripts\python.exe -m pytest -vv tooling/ai-engines/tests/test_mql5_parity_and_kit.py tooling/ai-engines/tests/test_quant_factory_suite.py tooling/ai-engines/tests/test_pass27_suite.py tooling/ai-engines/tests/test_pass28_suite.py`
- **Kết quả:** **`21 passed in 6.88s`** (gồm `6/6` test mới trong [test_mql5_parity_and_kit.py](../../tooling/ai-engines/tests/test_mql5_parity_and_kit.py) kiểm tra parity, tamper detection, 10 profile/90 `.set`, compile logs `9/9`, PowerShell watchdog dry-run/critical/log-rotation, activation card & Holdout lock + `15/15` test hồi quy Quant Factory / Pass 27 / Pass 28).
- **Anti-bloat:** Toàn bộ file trong `exports/` và `planning/research/MT5-COMPILE-PARITY-AND-DEPLOYMENT-KIT-20261124.md` đều `< 40 KB` (dưới ngưỡng `900 KB`), `0` binary `.ex5` trong cây Git.

# Thẻ Kích Hoạt Buổi Sáng — MT5 Local Windows PC (Naqex 8-EA + Orchestrator)

> **Phạm vi:** Hướng dẫn chạy **FTMO Free Trial (10,000 USD)** trên máy Windows local trước, sau đó chuyển nguyên bộ sang Windows VPS khi thi Challenge / Funded.  
> **Nguyên tắc an toàn (Fail-Closed):** Tất cả 9 file `.mq5` đều mặc định `InpDryRunLogOnly = true` và `InpGuardDryRunLogOnly = true` (`OrderSend = 0`). Toàn bộ 8 bộ preset thi/Funded đều ở trạng thái **ARM-LOCKED** (chỉ mở khóa thủ công khi bạn xác nhận Free Trial PASS & TCA GREEN).

---

## 5 Bước Kích Hoạt Nhanh Trong 5 Phút

### Bước 1 — Kiểm chứng toàn vẹn bộ cài trước khi mở MT5
Mở PowerShell tại `D:\ANNAM\TradingWorkspace` và chạy lệnh kiểm tra SHA-256 + parity:

```powershell
.\.runtime\quant-audit-v24\Scripts\python.exe tooling\ai-engines\exports\verify_deployment_kit.py --require-ex5
```

Xác nhận kết quả **`Deployment Kit Verify: PASS`** (`profiles=10 presets=90`, `9/9` file `.ex5` hợp lệ, `0` red flags).

### Bước 2 — Copy 9 file `.ex5` và lịch tin đỏ vào thư mục MT5 Data Folder
1. Mở **MetaTrader 5** (`C:\Program Files\MetaTrader 5\terminal64.exe` hoặc bản FTMO MT5 đã cài) -> **File -> Open Data Folder**.
2. Copy **9 file `.ex5`** từ `D:\ANNAM\TradingWorkspace\.runtime\mt5-compiled-ex5\*.ex5` vào:  
   `<MT5 Data Folder>\MQL5\Experts\Naqex\`
3. Copy file lịch tin đỏ `D:\ANNAM\TradingWorkspace\tooling\ai-engines\exports\Files\naqex_red_news_utc.csv` vào:  
   `<MT5 Data Folder>\MQL5\Files\naqex_red_news_utc.csv`
4. Copy thư mục preset cần dùng từ `tooling\ai-engines\exports\deployment_kit\presets\<PROFILE>\*.set` vào:  
   `<MT5 Data Folder>\MQL5\Presets\`
5. Trong cửa sổ **Navigator** của MT5 -> chuột phải **Expert Advisors -> Refresh**.

### Bước 3 — Đăng nhập FTMO Free Trial & bật đúng 9 biểu đồ (Chart)
1. Đăng nhập tài khoản **FTMO Free Trial Demo** (tuyệt đối KHÔNG đăng nhập tài khoản thật/trả phí ở giai đoạn này).
2. Mở **Market Watch** -> chuột phải -> **Show All** -> đảm bảo hiện đủ: `USDJPY`, `GBPUSD`, `EURUSD`, `AUDUSD`, `USDCAD`, `EURJPY`, `US100.cash`, `US500.cash`.
3. Bật nút **Algo Trading** trên thanh công cụ (chỉ bật sau khi đã chọn đúng preset!).
4. Mở đúng **9 chart** và gắn lần lượt (gắn **Orchestrator đầu tiên**):

| # | EA (`.ex5`) | Chart & Khung | Magic | MaxSpread (pts) | Ghi chú |
|---:|---|---|---:|---:|---|
| 0 | `Naqex_AccountOrchestrator.ex5` | `EURUSD` `M15` | Range `20261120..99` | 35.0 | **Gắn đầu tiên** — ghi `naqex_heartbeat.json` mỗi 15s |
| 1 | `Naqex_WB_TOKYO_BOX_USDJPY.ex5` | `USDJPY` `M15` | `20261122` | 35.0 | Core E1 — Tokyo Box OCO, flat 18:00 Helsinki |
| 2 | `Naqex_WB_EXP080_USDJPY.ex5` | `USDJPY` `M15` | `20261123` | 35.0 | Core E2 — Daily Open Exp 0.80 ATR |
| 3 | `Naqex_WB_EXP080_VOLHIGH_GBPUSD.ex5` | `GBPUSD` `M15` | `20261125` | 35.0 | Core E3 — Vol-High GBPUSD |
| 4 | `Naqex_WB_SESS_CONT_BRK40_US100.ex5` | `US100.cash` `M5` | `20261124` | **450.0** | Core E4 — Bắt buộc load `.set` (spread FTMO US100 ~195 pts) |
| 5 | `Naqex_WB_IDX_RS_US100_LEAD_1130.ex5` | `US100.cash` `M5` | `20261126` | **450.0** | Core E5 — Cần `US500.cash` trong Market Watch |
| 6 | `Naqex_WB_VOLCOMP_EXP75_EURJPY.ex5` | `EURJPY` `M15` | `20261128` | 45.0 | Core E6 — Vol-Compression EURJPY |
| 7 | `Naqex_WB_NY_RISK_FLOW_10ET_USDJPY.ex5` | `USDJPY` `M5` | `20261129` | 35.0 | Core E7 — Cần `US100.cash` + G6 USD majors |
| 8 | `Naqex_WB_FX_USD_BASKET_12U_Z35.ex5` | `EURUSD` `M15` | `20261127` | 35.0 | Satellite S6 — Bật ở FreeTrial/P1, **tắt (`0.00%`) ở P2 & Funded** |

> **Cảnh báo quan trọng về `US100.cash`:** Spread thực đo trên FTMO Demo cho `US100.cash` là `195` points (`1.95` điểm chỉ số, `digits=2`). Luôn dùng nút **Load** để nạp file `.set` (đã cài sẵn `InpGuardMaxSpreadPoints=450.0`), KHÔNG để mặc định `35.0` của FX.

### Bước 4 — Quy trình 2 giai đoạn trên FTMO Free Trial (Ngày 1–2 vs Ngày 3–14)
- **Ngày 1–2 (`FTMO_FreeTrial_DryRun`):** Load toàn bộ 9 file `.set` trong `presets\FTMO_FreeTrial_DryRun\`. Xác nhận trong tab **Experts**:
  - Không có lỗi `INIT_FAILED`, không có `retcode 10030`.
  - File `<MT5 Data Folder>\MQL5\Files\naqex_heartbeat.json` cập nhật đều mỗi 15 giây với `"kill_switch": false`, `"orphan_no_sl": 0`, `"dry_run": true`.
  - Khi có tín hiệu, log xuất `[DRYRUN-GUARD]` và ghi vào `naqex_exec_audit.csv`.
- **Ngày 3–14 (`FTMO_FreeTrial_Demo`):** Khi Ngày 1–2 sạch 100%, load bộ `presets\FTMO_FreeTrial_Demo\` (`InpDryRunLogOnly=false`, `InpGuardDryRunLogOnly=false`, rủi ro bảo thủ `1.00x`, `SYMCAP_100 = 1.00%`) để khớp lệnh Demo thật và thu thập dữ liệu TCA (`naqex_exec_audit.csv`) kiểm tra trượt giá, latency, và `swap = 0`.

### Bước 5 — Bật Watchdog giám sát trên PC Local (dùng y hệt khi chuyển lên VPS)
Chạy thử 1 lần bằng PowerShell (trỏ `-HeartbeatPath` tới đúng `<MT5 Data Folder>\MQL5\Files\naqex_heartbeat.json`):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tooling\ai-engines\exports\deployment_kit\ops_watchdog\naqex_mt5_watchdog.ps1 `
  -HeartbeatPath "<MT5_DATA_FOLDER>\MQL5\Files\naqex_heartbeat.json" `
  -AccountLabel "FTMO_FREETRIAL_LOCAL"
```

- Mặc định ghi cảnh báo ra file JSON cục bộ (`watchdog_state\naqex_watchdog_alerts.jsonl`), **0 secret**, tự xoay vòng log `> 5 MB`.
- Khi chuyển lên Windows VPS: đăng ký lệnh trên vào **Task Scheduler** chạy mỗi `1` phút (có thể truyền thêm `-EnableWebhook` và đặt biến môi trường hệ thống `NAQEX_ALERT_WEBHOOK_URL` nếu muốn bắn Telegram/Discord).

---

## Bảng Tham Chiếu 10 Hồ Sơ Preset (Đã Đồng Bộ M2.2 `seed=20261124`)

| Profile | Firm / Vốn | Eff Mult (`EA × Orch`) | Amber / Red Brake | Kill Daily / Static | MaxSymRisk | RedNews ±5m | S6 | Trạng thái Preset |
|---|---|---:|---|---|---|---|---|---|
| `FTMO_FreeTrial_DryRun` | FTMO 10,000 USD | `1.00x` (`1.00 × 1.00`) | `3.5%/0.65x`, `6.0%/0.40x` | `2.5%` / `7.5%` | `1.00%` | ON | ON | DryRun (`OrderSend=0`) |
| `FTMO_FreeTrial_Demo` | FTMO 10,000 USD | `1.00x` (`1.00 × 1.00`) | `3.5%/0.65x`, `6.0%/0.40x` | `2.5%` / `7.5%` | `1.00%` | ON | ON | Demo Paper Fills |
| `FTMO_P1_Balanced_3to6m` | FTMO 10,000 USD | `4.00x` (`1.50 × 2.67`) | `7.5%/1.00x`, `9.0%/0.75x` | `4.2%` / `9.2%` | `3.00%` | ON | ON | **ARM-LOCKED** |
| `FTMO_P1_Sprint_1to3m` | FTMO 10,000 USD | `4.75x` (`1.50 × 3.17`) | `9.9%/1.00x`, `9.9%/1.00x` | `4.3%` / `9.5%` | `3.50%` | ON | ON | **ARM-LOCKED** |
| `FTMO_P2_Verify` | FTMO 10,000 USD | `2.50x` (`1.00 × 2.50`) | `3.5%/0.65x`, `6.0%/0.40x` | `3.5%` / `7.5%` | `2.50%` | ON | OFF | **ARM-LOCKED** |
| `FTMO_Funded_Swing_Safe` | FTMO 10,000 USD | `1.00x` (`1.00 × 1.00`) | `3.5%/0.65x`, `6.0%/0.40x` | `2.5%` / `7.5%` | `1.00%` | OFF | OFF | **ARM-LOCKED** |
| `FTMO_Funded_Std_RedNews` | FTMO 10,000 USD | `1.00x` (`1.00 × 1.00`) | `3.5%/0.65x`, `6.0%/0.40x` | `2.5%` / `7.5%` | `1.00%` | ON | OFF | **ARM-LOCKED** |
| `The5ers_HighStakes_P1_Balanced` | The5ers 5,000 USD | `4.00x` (`1.50 × 2.67`) | `7.5%/1.00x`, `9.0%/0.75x` | `4.2%` / `9.2%` | `3.00%` | ON | ON | **ARM-LOCKED** (cần EA clearance) |
| `The5ers_HighStakes_P1_Sprint` | The5ers 5,000 USD | `4.75x` (`1.50 × 3.17`) | `9.9%/1.00x`, `9.9%/1.00x` | `4.3%` / `9.5%` | `3.50%` | ON | ON | **ARM-LOCKED** (cần EA clearance) |
| `The5ers_HighStakes_Funded` | The5ers 5,000 USD | `1.00x` (`1.00 × 1.00`) | `3.5%/0.65x`, `6.0%/0.40x` | `2.5%` / `7.5%` | `1.00%` | ON | OFF | **ARM-LOCKED** (cần EA clearance) |

> **Quy tắc mở khóa ARM-LOCKED:** Chỉ khi đã qua Free Trial 14 ngày với TCA `GREEN`, bạn mới tự tay mở tab **Inputs** của từng EA và đổi cả 2 dòng `InpDryRunLogOnly = false` và `InpGuardDryRunLogOnly = false` ngay trước khi bấm OK.

---

## Checklist 1-Click GUI MT5 Strategy Tester (60 Giây Sau Khi Đăng Nhập Demo)

> *Lý do:* Kiểm thử tự động hoàn toàn offline không tài khoản bằng `terminal64.exe /portable /config:...` (MT5 build 6230) bị MT5 từ chối với mã `-1000012353` (`tester not started because the account is not specified`). Vì nguyên tắc `OrderSend = 0` không tự đăng nhập broker trong phiên tự động, hãy chạy smoke test 60 giây trực tiếp trên GUI ngay sau khi đăng nhập FTMO Free Trial:

1. Nhấn **`Ctrl + R`** trong MT5 để mở **Strategy Tester** -> chọn **Single**.
2. Chọn **Expert:** `Naqex\Naqex_WB_EXP080_USDJPY.ex5`, **Symbol:** `USDJPY`, **Timeframe:** `M15`.
3. Chọn **Date:** `Custom period` từ **`2024.01.02`** đến **`2024.03.29`** (giai đoạn Development, giữ nguyên tính khách quan của năm gần nhất), **Modeling:** `1 minute OHLC` (hoặc `Every tick based on real ticks`), **Deposit:** `10000 USD`, **Leverage:** `1:30`.
4. Sang tab **Inputs** -> bấm **Load** -> chọn `presets\FTMO_FreeTrial_Demo\Naqex_WB_EXP080_USDJPY.set` (đảm bảo `InpGuardTesterUtcOffsetH = 2` cho mùa đông / `3` cho mùa hè FTMO).
5. Bấm **Start** -> kiểm tra tab **Journal** & **Backtest**:
   - Không có lỗi `INIT_FAILED`, `OrderSend error 10030`, hay `array out of range`.
   - Mọi lệnh đều có **S/L** ngay khi vào và đóng trước rollover (**Swap = 0.00**).
   - Lặp lại 1 lần tương tự với `Naqex_WB_SESS_CONT_BRK40_US100.ex5` trên `US100.cash` `M5` (kiểm tra `InpGuardMaxSpreadPoints = 450.0`).

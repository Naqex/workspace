---
doc_type: ops-audit-and-sop
domain: naqex-node1-and-deadman-ops
campaign: total-offensive-2-v2.5
lane: d4-node1-stage
wave: wave1_readonly_audit
created_utc: 2026-11-27
checked_utc: "2026-11-27T06:38:55Z..2026-11-27T06:41:08Z"
layer: layer1_public_sanitized
order_send_count: 0
holdout_rows_analysed: 0
mt5_procs_dev: 0
spend_vnd: 0
---

# Kiểm Toán Chỉ Đọc `naqex-node1` & Cloud Dead-Man's-Switch Tiền-NFP + SOP Thu Hoạch Trước `08/12/2026`

**Kết luận (Wave 1 — Chỉ đọc 100%, `0 VND`, `OrderSend = 0`, `MT5_PROCS = 0` trên máy Dev, `Holdout 2025+ SEALED`):**
- **`naqex-node1` XANH TOÀN BỘ (`10/10` cổng `node_cutover_dryrun` ĐẠT — `READY_FOR_CUTOVER`):** đang phẳng lệnh (`open_positions = 0`), kết nối `FTMO-Demo` tươi (`age_sec = 2..11s`), `KeepPrivate = 1`, `C:` trống `91,7 GB`, đồng hồ `NTP = -105,7 ms`, `10/10` tệp `.ex5` + `492` dòng lịch tin đỏ khớp SHA-256, sao lưu ngày `20261127` mới `0` ngày.
- **Heroku Cloud Dead-Man's-Switch (`<HEROKU_DEADMAN_APP>`) XANH (`HTTP 200` trên cả `/health` và `/api/status`):** Postgres bền vững, `NAQEX_NODE1` `status = OK`, nhịp tim mới `39s` (`< 120s`), `open_positions = 0`, `orphan_no_sl = 0`, `kill_switch = false`, `order_send_count = 0`.
- **Khóa thời hạn bắt buộc:** tài khoản **FTMO Free Trial hết hạn vào ngày `08/12/2026`** -> bắt buộc thu hoạch trọn bộ log sống + sao kê chi tiết MT5 **ngay sau NFP Thứ Sáu `04/12/2026` và tuyệt đối TRƯỚC `08/12/2026`**, để làm đầu vào cho cổng thanh toán hóa đơn Black Friday `14` ngày (**`~14/12/2026`**).

> **Quy tắc OPSEC 2 lớp:** Báo cáo Tầng 1 này đã lọc sạch 100% địa chỉ IPv4/IPv6, URL thật, token, tên người dùng và mã số đăng nhập tài khoản (`<FTMO_TRIAL_LOGIN>`, `<HEROKU_DEADMAN_APP>`, `<LAN_IP>`, `<TAILSCALE_IP>`). Wave 1 tuyệt đối không ghi đè `.ex5` sống, không bật AutoTrading, và không chuyển tệp lên `naqex-node1` (việc staging cô lập vào `C:\Naqex\staging\total-offensive-2\` chỉ chạy khi vào Wave 2A).

---

## 1. Kết Quả Kiểm Toán Chỉ Đọc `naqex-node1` (`27/11/2026 06:38–06:41 UTC`)

Toàn bộ `4` mũi đọc trực tiếp từ máy Dev (`node_ctl.py status`, `integrity`, `maint`, `audit`) và cổng tổng hợp (`node_cutover_dryrun.py --live-readonly`) đều trả về **`order_send_count = 0`**, không khởi chạy MT5 trên máy Dev (`MT5_PROCS = 0`).

| Nhóm kiểm tra | Kết quả đo thực tế (`27/11/2026`) | Ngưỡng an toàn bắt buộc | Trạng thái |
|---|---|---|---|
| **Kết nối MT5 & Nhịp tim (`status`)** | `terminal64.exe` đang chạy (`Session 2`, khởi động `25/11 14:25`), `FTMO-Demo` (`<FTMO_TRIAL_LOGIN>`), `terminal_connected = true`, `positions_state = CONFIRMED`, `anchor_state = SYNCED`, `age_sec = 2..11s`, `regime = NORMAL`, `kill_switch = false`, `dry_run = false` | `connected = true`, `CONFIRMED`, `age <= 180s`, `kill_switch = false` | 🟢 **ĐẠT** |
| **Trạng thái phẳng lệnh (`status`)** | `open_positions = 0`, `total_account_positions = 0`, `pending_orders = 0`, `orphan_no_sl = 0`, `balance = 9.998,88 USD`, `equity = 9.998,88 USD`, `daily_dd_pct = 0,0%`, `static_dd_pct = 0,011%` | Bắt buộc `= 0` vị thế / lệnh chờ / thiếu SL | 🟢 **ĐẠT** |
| **Đồng hồ NTP & Ổ đĩa (`status`)** | `ntp_offset = -105,7 ms` (`-00,1056509s`, lần đo thứ hai `-109,4 ms`), ổ `C:` trống **`91,7 GB / 118,6 GB`**, ổ `D:` trống **`465,6 GB / 465,8 GB`**, RAM trống `7,6 GB`, uptime `47,27 giờ` | `|NTP| < 1.000 ms`, `C: free > 20 GB` | 🟢 **ĐẠT** |
| **Toàn vẹn mã & Cấu hình (`integrity`)** | `ex5_found_count = 10/10`, `ex5_expected_matched = 10/10`, `0` lệch SHA-256; `naqex_red_news_utc.csv` đủ **`492` dòng** (`sha16 = 235722ed1821499f`, `sha_match = true`); `common.ini` giữ **`KeepPrivate = 1`**, `connector.ini` không có `Login=` ghi đè | `10/10` SHA khớp, `492` dòng CSV khớp, `KeepPrivate = 1` | 🟢 **ĐẠT** |
| **Khóa 24/5 Win10 LTSC & Sao lưu (`maint`)** | `wu_reboot = false`, `cbs_reboot = false`, `NoAutoUpdate = 1`, `NoAutoReboot = 1`, `AutoAdminLogon = 1`, `hiberboot = 0`, `DISKIDLE = 0x00000000`, `UpdateOrchestrator` `Reboot_AC/Battery = Disabled`, `pagefile` khóa chặt trên `C:\pagefile.sys` (`0` chạm `E:`), sao lưu `D:\NaqexBackup\daily\20261127` (`0` ngày tuổi) | Không cờ reboot, khóa AutoLogon + LTSC 24/5, sao lưu `<= 2` ngày | 🟢 **ĐẠT** |
| **Tác vụ nền & Nhật ký khớp (`status` + `audit`)** | `Naqex_Heroku_Heartbeat_NODE1`, `Naqex_Daily_Backup_D`, `Naqex_MT5_Watchdog_NODE1` đều `Ready (rc=0)`; `AutoStart` `Running`; tác vụ Crypto Shadow/Maker đang `Disabled` đúng kế hoạch; `naqex_exec_audit.csv` có `557` dòng `ORDER_BLOCKED_SYMCAP`, **`0` `FILL_UNRESOLVED`**, **`0` `rejects_tail`**, `propguard_warn_count = 0` | `0` `FILL_UNRESOLVED`, `0` cảnh báo PropGuard | 🟢 **ĐẠT** |
| **Tổng hợp `node_cutover_dryrun.py`** | **`READY_FOR_CUTOVER` (`10/10` cổng ĐẠT, `0` cổng chặn)** cho preset `FTMO_Std10K_MasterProp7E_P1_Sprint_4x.set` (`FTMO_STD_10K_P1_SPRINT_4X`) | `10/10` cổng ĐẠT | 🟢 **ĐẠT** |

**Hai điểm lưu ý vận hành nhỏ (không phải lỗi chặn):**
1. `propguard_ok_count = 0` trong `node_ctl.py status` ngày `27/11/2026` là **hành vi dự kiến**: `terminal64.exe` khởi động từ `25/11/2026 14:25`, nên dòng `[PROPGUARD-OK]` ghi vào tệp nhật ký `20261125.log`, còn nhật ký ngày `27/11/2026` sạch hoàn toàn (`propguard_warn_count = 0`).
2. Đối chiếu từ [CURRENT-CONTEXT.md](../CURRENT-CONTEXT.md): đồng hồ NTP của cả `3` máy hiện đều đã đạt chuẩn (`naqex-node1 -105,7 ms`, `<DEV_PC> -24,2 ms`, `<X13_WORKER> +27,7 ms`, `strict_ntp_passed = true`); vẫn cần kiểm tra lại `|NTP| < 1.000 ms` ngay trước cửa sổ `QUOTE_ONLY` ngày `04/12/2026`.

---

## 2. Kết Quả Kiểm Toán Cloud Dead-Man's-Switch (`<HEROKU_DEADMAN_APP>`)

Thực hiện gọi chỉ đọc `GET /health` và `GET /api/status` (kèm tiêu đề `X-Naqex-View-Token` đọc từ tệp cấu hình cục bộ ngoài Git, không ghi ra log/báo cáo):

| Điểm cuối (Endpoint) | Mã HTTP | Trạng thái & Chỉ số đã lọc OPSEC | Ngưỡng chuẩn | Đánh giá |
|---|---:|---|---|---|
| `GET /health` | **`200`** | `ok = true`, `service = naqex-heroku-deadman`, `persistence = postgres`, `order_send_count = 0` | `HTTP 200`, `ok = true`, `postgres` | 🟢 **ĐẠT** |
| `GET /api/status` | **`200`** | `node_count = 1`, `account_label = NAQEX_NODE1`, `status = OK`, **`age_sec = 39s`**, `mt5_running = true`, `open_positions = 0`, `orphan_no_sl = 0`, `regime = NORMAL`, `kill_switch = false`, `equity = 9.998,88 USD`, `daily_dd_pct = 0,0%`, `static_dd_pct = 0,011%`, `last_seen_utc = 2026-11-27T06:39:01Z`, `order_send_count = 0` | `HTTP 200`, `status = OK`, `age_sec < 120s`, `order_send_count = 0` | 🟢 **ĐẠT** |
| **Ghi nhận trên `naqex-node1`** | — | `heroku_heartbeat_last.log` báo `ok = true`, `status = OK`, `reasons = []`, `received_utc = 2026-11-27T06:38:01Z` | Đồng bộ hai chiều `< 120s` | 🟢 **ĐẠT** |
| **Ngân sách gói Student** | — | `1 Basic Dyno (7 USD) + Postgres Essential-0 (5 USD) = 12 USD/tháng` (`<= 13 USD/tháng` hạn mức Student đến `30/09/2028`; mốc rà soát hủy/gia hạn `25/09/2028`) | `<= 13 USD/tháng` (`0 USD` thẻ thật) | 🟢 **ĐẠT** |

**Phát hiện kỹ thuật cần ghi nhận (chỉ đọc, chưa sửa tệp ngoài phạm vi làn D4):**
- Trong tệp `.runtime/ops-cloud/heroku_connection_local.json`, trường `web_url` hiện đang chứa hậu tố đường dẫn `/api/heartbeat`. Khi một công cụ đọc `web_url` và ghép trực tiếp `/health` hoặc `/api/status` lên `parsed.path`, máy chủ sẽ trả `401/404`; khi chuẩn hóa về gốc origin (`scheme + host`), cả `/health` và `/api/status` đều trả **`HTTP 200`**. Nên ghi vào danh sách sửa nhẹ sau Wave 1 cho module đọc cấu hình Cockpit (`prop_risk.py`) để luôn cắt về gốc origin trước khi ghép đường dẫn.

---

## 3. Hợp Đồng Staging Cô Lập Wave 2A (`stage_total_offensive_2_when_flat.ps1`)

Đã xây dựng script PowerShell 5.1 fail-closed tại [stage_total_offensive_2_when_flat.ps1](../../tooling/ai-engines/exports/deployment_kit/vps_kit/stage_total_offensive_2_when_flat.ps1) kèm bộ kiểm thử ngoại tuyến 100% tại [test_node1_staging_guard.py](../../tooling/ai-engines/tests/test_node1_staging_guard.py).

| Hàng rào an toàn | Điều kiện bắt buộc | Mã chặn khi vi phạm (Exit `2`) |
|---|---|---|
| **Cô lập thư mục đích** | Chỉ cho phép trong `C:\Naqex\staging\total-offensive-2\` (chặn cứng mọi đường dẫn `MQL5\Experts`, `MQL5\Files`, `MQL5\Presets`, `C:\Naqex\mt5`, ổ `E:` và `..`) | `BLOCKED_FORBIDDEN_TARGET_PATH` |
| **Phẳng lệnh tuyệt đối** | `open_positions == 0`, `total_account_positions == 0`, `pending_orders == 0`, `orphan_no_sl == 0` (kiểm lại lần 2 ngay trước khi `scp` trong Wave 2A) | `BLOCKED_OPEN_POSITIONS` |
| **Kết nối broker & Nhịp tim tươi** | `terminal_connected == true`, `positions_state == CONFIRMED`, `age_sec <= 180s` | `BLOCKED_BROKER_DISCONNECTED` / `BLOCKED_STALE_HEARTBEAT` |
| **Khóa phiên đăng nhập MT5** | `common.ini` có `KeepPrivate == 1` và `connector.ini` không ghi đè `Login=` | `BLOCKED_KEEP_PRIVATE` |
| **Dung lượng ổ hệ thống** | Ổ `C:` trống nghiêm ngặt **`> 20,0 GB`** | `BLOCKED_LOW_DISK` |
| **Độ lệch đồng hồ NTP** | Giá trị tuyệt đối **`|ntp_offset_ms| < 1.000 ms`** (từ chối nếu `unknown` hoặc thiếu số) | `BLOCKED_NTP_DRIFT` |
| **Chặn rò bí mật nguồn & OPSEC đầu ra** | Từ chối đóng gói `accounts.dat`, `terminal.lic`, `*.ini`, `*secret*`, `*token*`, `*.key`; bộ lọc OPSEC xóa sạch IPv4/IPv6/URL/token/login/tên người dùng khỏi JSON đầu ra | `BLOCKED_FORBIDDEN_CREDENTIAL_FILE` |
| **Xác thực SHA-256 hai chiều** | Băm cục bộ bằng PowerShell + băm phía máy chủ bằng Python `hashlib.sha256` qua SSH stdin; lệch 1 bit -> dừng cứng (`exit 1`) | `SHA256_VERIFICATION_FAILED` |

**Lệnh chạy ở Wave 2A (KHÔNG chạy trong Wave 1):**
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tooling/ai-engines/exports/deployment_kit/vps_kit/stage_total_offensive_2_when_flat.ps1 -DryRun
```
*(Khi chủ sở hữu / điều phối viên mở Wave 2A và kết quả `-DryRun` trả `DRYRUN_READY_FLAT`, mới chạy lại không có `-DryRun` để nạp cô lập vào `C:\Naqex\staging\total-offensive-2\` — vẫn giữ `0` đè `.ex5` sống và `0` bật AutoTrading.)*

---

## 4. Khóa Hạn Hết Hạn FTMO Free Trial (`08/12/2026`) & Mốc Thời Gian Tới `~14/12/2026`

> **CẢNH BÁO MỐC CỨNG:** Tài khoản **FTMO Free Trial (`<FTMO_TRIAL_LOGIN>`) hết hạn cứng vào Thứ Ba `08/12/2026`**. Khi hết hạn `14` ngày, máy chủ `FTMO-Demo` có thể ngắt phiên truy cập lịch sử giao dịch trực tiếp trên MT5. Mọi log sống, tệp `naqex_exec_audit.csv`, và sao kê chi tiết MT5 **BẮT BUỘC phải thu hoạch trọn vẹn sau NFP `04/12/2026` và chậm nhất trước `23:59 ICT` Thứ Hai `07/12/2026` (tuyệt đối TRƯỚC `08/12/2026`)**.

| Mốc lịch (ICT / UTC) | Sự kiện trọng yếu | Mục tiêu & Tác động tới quyết định `~14/12/2026` |
|---|---|---|
| **Thứ Hai `30/11/2026 16:00 ICT` (`09:00 UTC`)** | Hạn chót khuyến mãi Black Friday FTMO (`2-Step Standard 10K`) | Chốt khóa giá sale (tạo hóa đơn có thời hạn thanh toán `14` ngày nếu áp dụng chiến lược trì hoãn thanh toán `0 VND` tới khi đủ dữ liệu NFP/CPI). |
| **Thứ Sáu `04/12/2026 20:30 ICT` (`13:30 UTC`)** | **US NFP** (`utc_ts = 1796391000`, tin đỏ lớn nhất đầu tháng 12) | Chạy thu thập `QUOTE_ONLY` (`20:25..20:45 ICT`, `OrderSend = 0`) trên `US100.cash, USDJPY, GBPUSD, EURJPY` và kiểm chứng lá chắn tin đỏ `±300s / ±135s`. |
| **Tối `04/12` -> Chủ Nhật `06/12/2026` (Chậm nhất `07/12 23:59 ICT`)** | **CỬA SỔ THU HOẠCH BẮT BUỘC TRƯỚC HẠN `08/12/2026`** | Tải sạch 100% log MT5/MQL5, `naqex_exec_audit.csv`, sao lưu `D:\NaqexBackup\daily\`, và xuất **MT5 Detailed Statement (HTML + CSV)** + FTMO MetriX trước khi tài khoản Trial bị đóng. |
| **Thứ Ba `08/12/2026`** | **HẾT HẠN CỨNG FTMO FREE TRIAL (`08/12/2026`)** + `AUD RBA` (`10:30 ICT`) | Mốc khóa cứng không thể lùi. Trước ngày này, toàn bộ bằng chứng Free Trial phải đã nằm an toàn trong `private_vault/` có dấu SHA-256. |
| **Thứ Tư `09/12` – Thứ Năm `10/12/2026`** | **FOMC** (`10/12 02:00 ICT`) & **US CPI** (`10/12 20:30 ICT`, `utc_ts = 1796909400`) | Thu thập `QUOTE_ONLY` lần 2 quanh **US CPI** (`20:25..20:45 ICT`) để có đủ cặp bằng chứng sốc thanh khoản NFP + CPI. |
| **`~14/12/2026` (Hạn chót `14` ngày hóa đơn Black Friday)** | **CỔNG QUYẾT ĐỊNH THANH TOÁN HÓA ĐƠN BLACK FRIDAY** | Hợp nhất: (1) Báo cáo đối soát Free Trial trọn vòng (thu trước `08/12`), (2) Dữ liệu `QUOTE_ONLY` NFP `04/12` + CPI `10/12`, (3) Thư xác nhận EA bằng văn bản từ FTMO -> quyết định **THANH TOÁN** hay **BỎ HÓA ĐƠN (`0 VND`)**. |

---

## 5. SOP 5 Bước Thu Hoạch Log Sống & Sao Kê MT5 Hậu-NFP (`04/12` -> Trước `08/12/2026`)

Thực hiện tuần tự đúng 5 bước sau (ước tính **`25–35` phút**, `OrderSend = 0`, tuyệt đối không sửa cấu hình hay đè tệp trên `naqex-node1`):

1. **Bước 1/5 — Chụp nhanh trạng thái hậu-NFP (ngay `04/12/2026 20:50 ICT`, `~3` phút):**
   Chạy từ `<DEV_PC>` các lệnh chỉ đọc để chốt bằng chứng vận hành ngay sau sự kiện NFP (`13:30 UTC`):
   ```powershell
   .runtime\quant-audit-v24\Scripts\python.exe tooling\ai-engines\ops_cloud\node_ctl.py status
   .runtime\quant-audit-v24\Scripts\python.exe tooling\ai-engines\ops_cloud\node_ctl.py integrity
   .runtime\quant-audit-v24\Scripts\python.exe tooling\ai-engines\ops_cloud\node_ctl.py audit
   .runtime\quant-audit-v24\Scripts\python.exe tooling\ai-engines\ops_cloud\node_ctl.py logs --scope mql5 --days 14 --tail 200
   .runtime\quant-audit-v24\Scripts\python.exe tooling\ai-engines\ops_cloud\node_ctl.py logs --scope terminal --days 14 --tail 200
   ```
   Xác nhận `open_positions = 0`, `orphan_no_sl = 0`, `propguard_warn_count = 0`, và có dòng chặn tin đỏ `US_NFP` đúng khung `13:25..13:35 UTC`.

2. **Bước 2/5 — Kéo trọn bộ log gốc, audit CSV và snapshot dự phòng về `private_vault/` (`05/12/2026` cuối tuần phẳng lệnh, `~8` phút):**
   Tạo thư mục lưu trữ cục bộ **ngoài Git** tại `private_vault/telemetry/ftmo-trial-harvest-202612/` trên `<DEV_PC>`, dùng `scp` chỉ đọc từ `naqex-node1` kéo toàn bộ:
   - `C:\Naqex\mt5\MQL5\Files\naqex_exec_audit*.csv` và `C:\Naqex\mt5\MQL5\Files\naqex_heartbeat.json`
   - `C:\Naqex\mt5\MQL5\Logs\*.log` (toàn bộ chu kỳ Free Trial `14` ngày)
   - `C:\Naqex\mt5\Logs\*.log` (log hệ thống terminal để đối chiếu mất kết nối / lỗi mạng)
   - Bản sao lưu ngày mới nhất từ `D:\NaqexBackup\daily\` (`20261204` – `20261206`)
   - Tệp tick chỉ đọc NFP `nfp_cpi_quote_ticks_US_NFP_20261204.csv` (tầng `QUOTE_ONLY`, không gộp với `FILL_VERIFIED`).

3. **Bước 3/5 — Xuất Sao Kê Chi Tiết MT5 & FTMO MetriX TRƯỚC `08/12/2026` (`05–06/12/2026`, `~5` phút):**
   - Mở RDP vào `naqex-node1` (khi thị trường cuối tuần đóng cửa, `open_positions = 0`): trong cửa sổ **Toolbox -> History**, bấm chuột phải chọn **`All History`**, sau đó chọn **`Report -> Open XML / HTML`** và lưu vào `C:\Naqex\logs\ftmo_trial_statement_20261206.html` rồi `scp` về `private_vault/telemetry/ftmo-trial-harvest-202612/`.
   - Đăng nhập cổng web FTMO Client Area -> mở trang **MetriX** của gói Free Trial -> xuất **Trade Journal / CSV** và lưu cùng thư mục trên (phòng trường hợp cần đối chiếu giờ máy chủ FTMO và phí hoa hồng/swap).
   - Băm SHA-256 toàn bộ thư mục thu hoạch để niêm phong bằng chứng gốc trước khi tài khoản hết hạn ngày `08/12/2026`.

4. **Bước 4/5 — Chạy Đối Soát Tự Động `daily_statement_reconciler.py` (`06/12/2026`, `~5` phút, `OrderSend = 0`):**
   Chạy trên `<DEV_PC>` (thay `<FTMO_TRIAL_LOGIN>` bằng mã số thật đọc từ `private_vault/`, không lưu vào Git):
   ```powershell
   .runtime\quant-audit-v24\Scripts\python.exe tooling\ai-engines\quant_factory\daily_statement_reconciler.py --audit-csv private_vault/telemetry/ftmo-trial-harvest-202612/naqex_exec_audit.csv --statement private_vault/telemetry/ftmo-trial-harvest-202612/ftmo_trial_statement_20261206.html --expected-login <FTMO_TRIAL_LOGIN> --out-json private_vault/telemetry/ftmo-trial-harvest-202612/reconcile_receipt_20261206.json
   ```
   Tiêu chí ĐẠT bắt buộc: `passed = true`, `order_send_count = 0`, `orphan_audit_count = 0`, `orphan_statement_count = 0`, `unresolved_fill_rows = 0`, `missing_swap_count = 0`, **`nonzero_swap_count = 0`** (`swap = 0,00 USD`).

5. **Bước 5/5 — Cổng Ra Quyết Định Hóa Đơn Black Friday (`11–13/12/2026`, trước hạn chót `~14/12/2026`, `~10` phút):**
   Gộp biên bản đối soát Free Trial (đã chốt trước `08/12`) + kết quả `QUOTE_ONLY` NFP (`04/12`) & CPI (`10/12`) + email xác nhận bằng văn bản từ FTMO vào hồ sơ quyết định cuối:
   - **CHỈ THANH TOÁN HÓA ĐƠN** nếu đồng thời đạt: (a) `daily_statement_reconciler` `PASS` (`swap = 0,00 USD`, `0` `FILL_UNRESOLVED`, `0` lệnh thiếu SL), (b) chi phí trượt giá thực địa giữ ổn định `<= 1,50x` ngân sách M1, (c) có xác nhận văn bản từ FTMO cho EA độc quyền và không vi phạm vùng cấm tin đỏ `±2p`, (d) có lệnh phê duyệt tường minh từ chủ sở hữu.
   - **HỦY / BỎ HÓA ĐƠN (`0 VND`)** nếu phát sinh bất kỳ lỗi `R3/R4` nào chưa đóng dứt điểm (trượt giá `> 1,75x`, dính swap khác `0`, lỗi tin đỏ, hoặc thiếu xác nhận pháp lý).

---

## 6. Bước Kế Tiếp (`< 2` Phút)

1. **Cho Wave 2A (khi được điều phối viên mở khóa):** Chạy `stage_total_offensive_2_when_flat.ps1 -DryRun` kiểm tra cổng phẳng lệnh trước khi thực hiện nạp cô lập vào `C:\Naqex\staging\total-offensive-2\`.
2. **Trước `04/12/2026`:** Kiểm tra lại độ lệch đồng hồ NTP (`|NTP| < 1.000 ms`, hiện cả 3 máy đã đạt `strict_ntp_passed = true`) ngay trước cửa sổ `QUOTE_ONLY` NFP, và giữ nguyên trạng thái sạch của `naqex-node1` cho tới cửa sổ thu hoạch hậu-NFP trước `08/12/2026`.

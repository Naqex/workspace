# Naqex Home-VPS Hardening v3 — 5-Scenario Chaos Drill Playbook

Sổ tay diễn tập sự cố thực tế cho nút giao dịch 24/5 `naqex-node1` (Windows 10 IoT Enterprise LTSC), áp dụng cho giai đoạn Demo, FTMO Standard 10K Evaluation và Funded.

> **Kỷ luật An toàn & OPSEC Lớp 1 (Bắt buộc):**
> - **Chiến lược `OrderSend = 0` cho toàn bộ công cụ vận hành:** Mọi script kiểm tra/sao lưu đều chỉ đọc hoặc ghi cờ `naqex_manual_halt.flag` — tuyệt đối không gọi lệnh giao dịch trực tiếp từ script.
> - **Không rò rỉ dữ liệu thật:** Chỉ dùng ký hiệu thay thế (`<LAN_SUBNET>`, `<LAN_IP>`, `<TAILSCALE_IP>`, `<SSH_USER>`, `<HEROKU_DEADMAN_APP>`, `<TELEGRAM_GUARD_BOT>`, `100.64.0.0/10`). Tra cứu thông số thật duy nhất trong `private_vault/ops/naqex-node1-topology.md`.
> - **Đơn vị tiền tệ:** Luôn ghi rõ `USD` / `VND`, không dùng ký hiệu tiền tệ trần.
> - **Không trộn Holdout/Dev:** Mọi bản kéo dữ liệu thực địa từ `naqex-node1` đi 1 chiều duy nhất vào `.runtime/live-vault/`.

---

## 0. Bộ Công Cụ Tái Sử Dụng & Kịch Bản Hardening v3

| Nhóm | Công cụ chuẩn (không viết trùng) | Vai trò |
| :--- | :--- | :--- |
| Giám sát SSH 1 lệnh | `tooling/ai-engines/ops_cloud/node_ctl.py` | Kiểm tra `status`, `logs`, `integrity`, `maint`, `audit` (tự dự phòng LAN sang Tailscale) |
| Kiểm tra tiền chuyển đổi | `tooling/ai-engines/ops_cloud/node_cutover_dryrun.py` | Chấm 10/10 cổng an toàn trước khi bật tài khoản mới |
| Kiểm tra Geo-IP & Tin đỏ | `tooling/ai-engines/ops_cloud/ftmo_pre_checkout_guard.py` | Chặn IP Mỹ, phát hiện CGNAT `100.64.0.0/10`, lịch tin đỏ 14 ngày |
| Bản tin sáng / tuần | `tooling/ai-engines/ops_cloud/node_weekly_digest.py` | Tổng hợp nhanh <= 35 dòng trạng thái MT5, đĩa `C:`, backup `D:` |
| Canh gác MT5 cục bộ | `tooling/ai-engines/exports/deployment_kit/ops_watchdog/naqex_mt5_watchdog.ps1` | Phát hiện treo `terminal64.exe`, nhịp tim quá hạn `> 180s`, lệnh thiếu SL |
| **Hardening v3 (Mũi 3)** | `hardening_v3/audit_firewall_minimal.ps1` | Kiểm toán tường lửa chỉ đọc (MT5 TCP 443, NTP UDP 123, Heroku TCP 443, Tailscale UDP 41641) |
| **Hardening v3 (Mũi 3)** | `hardening_v3/rotate_mt5_logs.ps1` | Nén log > 7 ngày sang `D:\NaqexBackup\mt5-logs-archive\`, xóa lưu trữ > 90 ngày, khóa bảo vệ log hôm nay |
| **Hardening v3 (Mũi 3)** | `hardening_v3/fim_sha256_daily.ps1` | Giám sát toàn vẹn SHA-256 hằng ngày cho `.ex5`, `.set`, `naqex_red_news_utc.csv`, `Config\common.ini` (`KeepPrivate=1`) |
| **Hardening v3 (Mũi 3)** | `hardening_v3/emergency_killswitch_guard.ps1` | **Bắt buộc (B8):** Ghi `naqex_manual_halt.flag` và kiểm chứng `manual_halt_ack == true` trong `<= 10s`; quá 10s báo ĐỎ cấp tốc |
| **Hardening v3 (Mũi 3)** | `hardening_v3/sync_live_vault_readonly.ps1` | Kéo 1 chiều chỉ đọc audit CSV, blackbox JSONL, M1 quote tape, heartbeat về `.runtime/live-vault/` có kiểm SHA-256 |

---

## Diễn Tập 1: Mất Mạng Cáp Quang / ISP Drop 15 Phút Khi Đang Mở Lệnh
*(Scenario 1: Fiber/ISP Drop 15m Mid-Position)*

- **Tín hiệu phát hiện (0–2 phút):**
  1. `<TELEGRAM_GUARD_BOT>` từ `<HEROKU_DEADMAN_APP>` báo `STALE > 120s` cho `NAQEX_NODE1`.
  2. `python tooling/ai-engines/ops_cloud/node_ctl.py status` báo `terminal_connected=false` hoặc mất kết nối SSH.
- **Hành động tức thời (phút 2–5):**
  1. Bật ngay mạng di động 4G/5G trên điện thoại, mở **MT5 Mobile** kiểm tra lệnh mở: xác nhận toàn bộ lệnh đều có **Stop Loss cứng** nằm trên máy chủ broker (SL bảo vệ chạy trên server broker ngay cả khi Home-VPS rớt mạng).
  2. Không vội mở thêm lệnh tay hay khởi động lại `naqex-node1`.
  3. Kiểm tra mốc giờ cắt swap=0 (`20:50 UTC` = `03:50 ICT`) và lịch tin đỏ sắp tới bằng `python tooling/ai-engines/ops_cloud/ftmo_pre_checkout_guard.py --live-readonly --days 14` (hoặc tra bản sao nội bộ): nếu mạng chưa hồi trước `20:45 UTC` hoặc trước tin đỏ 10 phút, đóng lệnh chủ động bằng MT5 Mobile.
- **Xác minh sau khi mạng hồi (phút 15–20):**
  1. Chạy `python tooling/ai-engines/ops_cloud/node_ctl.py status` (LAN hoặc tự chuyển sang `naqex-node1-ts`): xác nhận `terminal_connected=true`, `positions_state=CONFIRMED`, `orphan_no_sl=0`, `anchor_state != UNRECOVERED_AFTER_GAP`.
  2. Chạy `python tooling/ai-engines/ops_cloud/node_ctl.py logs --scope mql5 --days 1 --errors-only` kiểm tra không có lỗi treo lệnh.
  3. Kéo bản ghi đối chiếu về máy chính:
     ```powershell
     powershell -NoProfile -ExecutionPolicy Bypass -File .\sync_live_vault_readonly.ps1 -DryRun
     ```
- **Tiêu chuẩn Đạt:** SL máy chủ broker giữ nguyên vị thế, không phát sinh lệnh mồ côi (`orphan_no_sl == 0`), nhịp tim hồi xanh trong `< 2` phút sau khi cáp quang thông lại.

---

## Diễn Tập 2: Mất Điện Vượt Pin UPS + Cứu Hộ MT5 Mobile < 3 Phút Trước `20:50 UTC`
*(Scenario 2: Power Outage > UPS Battery + <3m MT5 Mobile Rescue Before 20:50 UTC Swap=0 Cutoff)*

- **Bối cảnh rủi ro:** Điện lưới cúp lâu hơn thời lượng pin UPS; `naqex-node1` tắt nguồn trước giờ đóng lệnh cuối ngày FTMO Standard (`20:50 UTC` = `03:50 ICT`). Nếu giữ lệnh qua `21:00 UTC` sẽ phát sinh phí swap và rủi ro giãn spread rollover.
- **Quy trình cứu hộ < 3 phút (SLA cứng <= 180 giây):**
  1. **Giây 0–45:** Nhận cảnh báo `<TELEGRAM_GUARD_BOT>` (`STALE > 120s`) hoặc thấy mất điện nhà; mở **MT5 Mobile** bằng 4G/5G (tắt Wi-Fi nhà để tránh kẹt mạng).
  2. **Giây 45–120:** Đối chiếu đúng số tài khoản/máy chủ FTMO, đóng toàn bộ vị thế đang mở (`Close Position`) và hủy toàn bộ lệnh chờ (`Delete Pending Orders`).
  3. **Giây 120–180:** Đăng nhập FTMO Client Area / Account MetriX xác nhận `Open Positions = 0` trước mốc `20:50 UTC`.
- **Quy trình hậu kiểm khi có điện lại:**
  1. Xác nhận BIOS `Restore on AC Power Loss -> Power On` tự bật máy, Windows tự đăng nhập (`AutoAdminLogon=1`), và `Naqex_MT5_Portable_AutoStart` tự khởi chạy MT5 Portable.
  2. Chạy bộ kiểm tra chỉ đọc:
     ```powershell
     python tooling/ai-engines/ops_cloud/node_ctl.py maint
     python tooling/ai-engines/ops_cloud/node_weekly_digest.py --live-readonly
     powershell -NoProfile -ExecutionPolicy Bypass -File .\fim_sha256_daily.ps1 -Mt5Root C:\Naqex\mt5 -ManifestPath C:\Naqex\ops\fim_manifest_sha256.json -DryRun
     ```
  3. Xác nhận `KeepPrivate=1`, không có `Login=` ghi đè trong `connector.ini`, đồng hồ NTP lệch `< 1s`, và `[PROPGUARD-OK]` xuất hiện trong `MQL5\Logs\YYYYMMDD.log`.
- **Tiêu chuẩn Đạt:** Thời gian từ lúc kích hoạt diễn tập đến khi tài khoản phẳng `0` lệnh trên MT5 Mobile `<= 180` giây và trước `20:50 UTC`; sau khi có điện lại, hệ thống tự phục hồi mà không cần gõ mật khẩu Windows.

---

## Diễn Tập 3: `terminal64.exe` Treo Hoặc Crash Giữa Lệnh (Kiểm Chứng Kill-Switch B8 `<= 10s`)
*(Scenario 3: terminal64.exe Hang / Crash Mid-Position + B8 Kill-Switch Escalation)*

- **Tín hiệu phát hiện:** `naqex_mt5_watchdog.ps1` phát cảnh báo `MT5_PROCESS_NOT_RUNNING` hoặc `HEARTBEAT_STALE (> 180s)`; hoặc EA không phản hồi sự kiện thị trường.
- **Bước 1 — Kích hoạt cầu dao 1 chạm có xác nhận ACK `<= 10s`:**
  ```powershell
  powershell -NoProfile -ExecutionPolicy Bypass -File .\emergency_killswitch_guard.ps1 -Mt5FilesDir C:\Naqex\mt5\MQL5\Files -Action FLATTEN_ALL -AckTimeoutSec 10
  ```
  - **Nhánh XANH (Exit Code `0`, `manual_halt_ack == true` trong `<= 10s`):** EA còn sống và đã tiếp nhận lệnh đóng phẳng; chờ xác nhận `open_positions == 0` rồi kéo log phân tích.
  - **Nhánh ĐỎ KHẨN CẤP (Exit Code `2`, `CRITICAL_RED_ESCALATION`):** Xảy ra khi EA treo, `terminal64.exe` đã crash, mất kết nối broker, hoặc preset cũ đặt `InpAllowManualHaltFile=false`. **KHÔNG CHỜ THÊM!** Chuyển ngay sang cứu hộ tay:
    1. Mở **MT5 Mobile** đóng ngay toàn bộ vị thế đang mở và hủy lệnh chờ.
    2. Kết nối RDP tới `naqex-node1` qua `<LAN_IP>` hoặc `<TAILSCALE_IP>`, tắt nút **Algo Trading** sang màu ĐỎ (hoặc chấm dứt tiến trình `terminal64.exe` bị treo nếu đã xác nhận phẳng lệnh trên MT5 Mobile).
- **Bước 2 — Khởi động lại sạch (chỉ sau khi phẳng lệnh + xác minh `KeepPrivate=1`):**
  1. Kiểm tra `fim_sha256_daily.ps1` (`KeepPrivate=1`, SHA-256 `.ex5` và `naqex_red_news_utc.csv` khớp 100%).
  2. Khởi chạy lại tác vụ `Naqex_MT5_Portable_AutoStart` (không gọi `MetaTrader5.initialize()` từ SSH Session `0`).
  3. Kéo bản ghi đen về `.runtime/live-vault/` bằng `sync_live_vault_readonly.ps1` để điều tra nguyên nhân gốc.
- **Tiêu chuẩn Đạt:** Khi giả lập `manual_halt_ack=false` hoặc tắt tiến trình MT5, script báo `CRITICAL_RED_ESCALATION` (exit `2`) đúng `<= 10` giây, không bao giờ báo XANH giả tạo.

---

## Diễn Tập 4: Cảnh Báo Đầy Ổ SSD `C:` Do Phình Log (`<= 20 GB` Trống)
*(Scenario 4: C: SSD Log Bloat Warning <= 20 GB Free)*

- **Tín hiệu phát hiện:** `node_ctl.py status` hoặc `node_weekly_digest.py` báo `disk_c_free_gb <= 20 GB`.
- **Ràng buộc an toàn lưu trữ 3 ổ đĩa:**
  - `C:` (`119 GB` SSD): Chứa Windows, `C:\pagefile.sys` và `C:\Naqex\mt5`. Luôn giữ trống `> 20 GB`.
  - `D:` (`465 GB` HDD): Chứa `D:\NaqexBackup\daily\` và `D:\NaqexBackup\mt5-logs-archive\`.
  - `E:` (`111 GB` SSD chốt SATA gãy): **CẤM TUYỆT ĐỐI** chuyển MT5, log quan trọng, cơ sở dữ liệu hay pagefile sang `E:`.
- **Quy trình xử lý an toàn:**
  1. Chạy thử chế độ chỉ đọc `-DryRun` trước để xem danh sách log cũ `> 7` ngày và kho lưu trữ `> 90` ngày sẽ xử lý:
     ```powershell
     powershell -NoProfile -ExecutionPolicy Bypass -File .\rotate_mt5_logs.ps1 -Mt5Root C:\Naqex\mt5 -ArchiveRoot D:\NaqexBackup\mt5-logs-archive -DryRun
     ```
  2. Xác nhận đầu ra JSON liệt kê log ngày hôm nay (`YYYYMMDD.log` theo cả UTC và giờ địa phương) trong `protected_active_files` — tuyệt đối không chạm vào file log đang ghi.
  3. Chạy xoay vòng thật (bỏ `-DryRun`), kiểm tra `disk_guard_passed == true` và `disk_free_gb_after > 20.0`.
  4. Kiểm tra lại `python tooling/ai-engines/ops_cloud/node_ctl.py maint` xác nhận `pagefiles` chỉ nằm trên `C:\pagefile.sys`.
- **Tiêu chuẩn Đạt:** Giải phóng dung lượng ổn định về `> 20 GB` trên ổ `C:`, 0 byte dữ liệu log ngày hiện tại bị khóa/xóa, bản nén `.zip` mở kiểm chứng thành công trên `D:\NaqexBackup\mt5-logs-archive\`.

---

## Diễn Tập 5: Broker Âm Thầm Đổi Symbol Suffix, Đòn Bẩy Hoặc Phí Swap
*(Scenario 5: Silent Broker Spec / Suffix / Leverage / Swap Change)*

- **Tín hiệu phát hiện:**
  1. `node_ctl.py logs --scope mql5 --days 1 --errors-only` hoặc `node_ctl.py audit` xuất hiện `ORDER_REJECT`, `FILL_UNRESOLVED`, `SYMBOL_NOT_FOUND`, hoặc log báo phí swap khác `0`.
  2. Chênh lệch bất thường trong báo cáo `node_weekly_digest.py` hoặc kiểm tra trước thanh toán `ftmo_pre_checkout_guard.py`.
- **Bước 1 — Khoanh vùng ngay (Chặn vào lệnh mới, giữ SL bảo vệ lệnh cũ):**
  ```powershell
  powershell -NoProfile -ExecutionPolicy Bypass -File .\emergency_killswitch_guard.ps1 -Mt5FilesDir C:\Naqex\mt5\MQL5\Files -Action HALT_NEW_ENTRIES -AckTimeoutSec 10
  ```
  *(Nếu exit code `2` do `manual_halt_ack != true` sau `10s`: tắt ngay nút Algo Trading trên MT5 Desktop và kiểm soát vị thế trên MT5 Mobile.)*
- **Bước 2 — Thu thập bằng chứng chỉ đọc & kiểm toán thông số:**
  1. Kéo ngay `naqex_exec_audit.csv`, `naqex_decision_blackbox_*.jsonl` và M1 quote tape về máy chính bằng `sync_live_vault_readonly.ps1` (1 chiều chỉ đọc, có kiểm SHA-256).
  2. Mở MT5 Market Watch kiểm tra trực tiếp Specification của 8 cặp lõi (`USDJPY`, `GBPUSD`, `EURJPY`, `US100.cash`, `US500.cash`, `EURUSD`, `AUDUSD`, `USDCAD`): hậu tố tên mã, kích cỡ hợp đồng, đòn bẩy, chế độ Swap-Free.
  3. Đối chiếu tường lửa tối thiểu `audit_firewall_minimal.ps1 -DryRun` và toàn vẹn file `fim_sha256_daily.ps1 -DryRun` để loại trừ sự cố giả mạo hoặc lỗi máy chủ broker.
- **Bước 3 — Chỉ mở lại khi đạt 10/10 cổng an toàn:**
  - Chờ tài khoản phẳng `0` lệnh, cập nhật cấu hình `.set` đã kiểm chứng (nếu đổi hậu tố), đồng bộ phẳng bằng `sync_updated_ex5_when_flat.ps1`, chạy `python tooling/ai-engines/ops_cloud/node_cutover_dryrun.py --live-readonly` đạt `READY_FOR_CUTOVER (10/10)` trước khi gỡ cờ dừng.
- **Tiêu chuẩn Đạt:** Ngăn chặn kịp thời chuỗi lệnh lỗi/sai khối lượng trong `< 5` phút, lưu đầy đủ bằng chứng SHA-256 trong `.runtime/live-vault/`, không mở lại giao dịch khi cổng `node_cutover_dryrun.py` còn báo `BLOCKED`.

---

## Thang Đánh Giá Diễn Tập Định Kỳ (Hàng Quý / Trước Đợt Challenge Mới)

- 🔴 **Xấu (Chưa đạt chuẩn chạy thật):** Còn kịch bản chưa diễn tập, `manual_halt_ack` không kiểm chứng `<= 10s`, `KeepPrivate=0`, hoặc đĩa `C: <= 20 GB`.
- 🟡 **Đủ dùng (Tối thiểu cho Demo/Trial):** Đã chạy `-DryRun` 5/5 script, biên bản FIM XANH, cứu hộ MT5 Mobile dưới 5 phút.
- 🟢 **Tốt (Chuẩn Challenge 10K):** 5/5 kịch bản diễn tập đạt thông số, cứu hộ MT5 Mobile `< 3` phút trước `20:50 UTC`, `node_cutover_dryrun.py` đạt 10/10 cổng.
- 🏆 **Top 1% thực tế (Chuẩn Funded dài hạn):** Toàn bộ 5/5 kịch bản đạt SLA định kỳ hằng quý, tường lửa outbound thu hẹp đúng 4 luồng tối thiểu, nhật ký FIM & Live-Vault 1 chiều lưu biên bản SHA-256 liên tục 0 ngày đứt quãng.

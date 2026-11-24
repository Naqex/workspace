# Hướng Dẫn Triển Khai VPS 24/5 — Naqex MT5 Suite (Không Cần Treo Máy Cá Nhân)

Tài liệu này gom quy trình chuyển toàn bộ bộ **9 `.ex5` + lịch tin đỏ `2018–2027` + bộ preset Prop Firm + watchdog cảnh báo** lên Windows VPS trong ~10 phút với kỷ luật **zero secret trong script/Git** và **fail-closed khi còn vị thế mở**.

---

## 1. Tiêu chuẩn chọn Windows VPS (Chi phí ~10–18 USD/tháng)

- **Vị trí máy chủ (ưu tiên ping thấp tới broker):** London (LD4) hoặc Frankfurt (FR2) / Amsterdam — mục tiêu ping `<= 15 ms` tới `FTMO-Server` và `The5ers-Live`.
- **Cấu hình tối thiểu:** `2 vCPU`, `4 GB RAM`, SSD `>= 40 GB`, Windows Server 2022.
- **Bảo mật bắt buộc:** bật tường lửa Windows, đổi cổng RDP mặc định hoặc dùng Tailscale/WireGuard, không lưu mật khẩu broker dạng plain-text trong file `.ini` hay script.

---

## 2. Cài đặt 1 lệnh lên VPS (`install_vps_24x5.ps1`)

1. Cài MT5 bản portable trên VPS (ví dụ `C:\NaqexMT5_The5ers`), đăng nhập tài khoản Demo hoặc Challenge **trực tiếp trong cửa sổ MT5** (tích `Save password` nội bộ của MT5), bật `Algo Trading`, **TẮT** `Allow DLL imports`.
2. Copy thư mục `tooling/ai-engines/exports/` (gồm `9/9 .ex5`, `Files/naqex_red_news_utc.csv`, `deployment_kit/`) lên VPS.
3. Kiểm tra trước bằng chế độ `-DryRun`:
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\install_vps_24x5.ps1 `
     -TargetMt5Root C:\NaqexMT5_The5ers `
     -PresetProfile The5ers_HighStakes_P1_Balanced `
     -AccountLabel THE5ERS_5K `
     -RegisterWatchdogTask -DryRun
   ```
4. Bỏ `-DryRun` để cài thật (script tự kiểm tra SHA-256 của cả `9/9 .ex5`, chép `.set` + `naqex_red_news_utc.csv`, và tạo Windows Scheduled Task chạy `naqex_mt5_watchdog.ps1` mỗi 2 phút).

---

## 3. Bật cảnh báo Telegram / Discord qua biến môi trường

Watchdog **không bao giờ lưu webhook trong code**. Trên VPS, đặt biến môi trường người dùng một lần duy nhất:

```powershell
[Environment]::SetEnvironmentVariable("NAQEX_ALERT_WEBHOOK_URL", "https://discord.com/api/webhooks/...", "User")
```

Sau đó truyền thêm cờ `-EnableWebhook` khi đăng ký Scheduled Task. Watchdog sẽ báo ngay khi:
- Tiến trình `terminal64` bị tắt/treo;
- `naqex_heartbeat.json` quá hạn `> 180` giây;
- `orphan_no_sl > 0` hoặc `kill_switch == true` hoặc chuyển sang vùng `AMBER_BRAKE` / `RED_BRAKE`.

---

## 4. Quy tắc cập nhật bản `.ex5` mới (Fail-Closed Khi Đang Có Lệnh Mở)

Không bao giờ ghi đè `.ex5` giữa lúc bot đang giữ lệnh. Luôn dùng script `sync_updated_ex5_when_flat.ps1`:

```powershell
powershell -ExecutionPolicy Bypass -File .\sync_updated_ex5_when_flat.ps1 `
  -TargetMt5Root D:\ANNAM\TradingWorkspace\.runtime\ftmo-demo-portable-1515343166
```

- Nếu `naqex_heartbeat.json` báo `open_positions > 0`, script **tự động dừng với mã lỗi `2` (`BLOCKED_OPEN_POSITIONS`)** và không động vào bất kỳ file nào.
- Khi tài khoản về `0` vị thế mở (sau 21:00 UTC hard flat hoặc sau khi chốt lệnh), chạy lại lệnh trên để đồng bộ bản `.ex5` mới có sửa lỗi `ResolveExecutedFillPrice` (ghi chính xác giá khớp thực `DEAL_PRICE` vào `naqex_exec_audit.csv`).

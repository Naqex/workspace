# Checklist 15 Phút Cài PC Phụ Windows 10 (`i3-7100 / 12GB RAM`) Cho AI Agent Quản Lý

1. **Phần cứng & BIOS (~3 phút):**
   - Tháo `GTX 1660` (cắm dây màn hình tạm vào cổng mainboard dùng Intel HD 630 tích hợp -> tiết kiệm ~`10–15W`, cả máy chỉ còn ~`20–30W`).
   - Cắm dây mạng **LAN trực tiếp** vào router (không dùng Wi-Fi).
   - Vào BIOS bật **`Restore on AC Power Loss -> Power On`** (cúp điện có lại là tự khởi động).
2. **Cài Windows 10 (~7 phút):**
   - Cài `Windows 10 IoT Enterprise LTSC 2021` (hoặc `Windows 10 Pro 22H2` từ Microsoft.com).
   - Tải 3 phần mềm nền: **Git for Windows**, **Python 3.12 (hoặc `uv`)**, và **Tailscale** (đăng nhập cùng tài khoản Tailscale với máy chính).
   - Chạy **Sysinternals Autologon** (chính chủ Microsoft) để sau khi tự bật nguồn, Windows tự đăng nhập vào Desktop khởi chạy MT5.
3. **Chạy 1 lệnh Bootstrap bằng PowerShell (Run as Administrator):**
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\setup_win10_home_vps.ps1
   ```
   *(Tự động tắt Sleep/Hibernate/Fast Startup, khóa Windows Update không tự reboot, và bật sẵn **OpenSSH Server** để AI Agent từ máy chính SSH trực tiếp sang quản lý toàn bộ!)*
4. **Thêm SSH Key & Nối Trạm Canh Heroku (~3 phút):**
   - Chép file `id_ed25519.pub` của máy chính vào `C:\ProgramData\ssh\administrators_authorized_keys` trên PC phụ -> AI Agent trên máy chính kết nối SSH không cần mật khẩu.
   - Đặt 2 biến User Env (`NAQEX_DEADMAN_URL` và `NAQEX_INGEST_TOKEN`) rồi đăng ký task gửi nhịp 1 phút/lần bằng cờ `-RegisterHerokuHeartbeatTask`.
5. **Đăng nhập MT5 Portable lần đầu (~2 phút):**
   - Chính tay bạn mở MT5 Portable, nhập tài khoản broker + tích *Save password* + bật `Algo Trading` + **TẮT** `Allow DLL imports`.
   - Rút màn hình cất đi — từ lúc này toàn bộ giám sát 24/7 đã có **Heroku EU Dead-Man's-Switch** canh chéo và AI Agent quản qua SSH.

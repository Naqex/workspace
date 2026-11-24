# Hướng Dẫn Deploy Trạm Canh Heroku Dead-Man's-Switch (`7 USD/tháng` từ Credit Student)

App thuần Python chuẩn (`0` thư viện ngoài, build mất ~15 giây, `OrderSend = 0`), chạy 24/7 trên **1 Basic Dyno** (`7 USD/tháng`, không ngủ, dùng được ~`44` tháng từ `312 USD` Platform Credits) để canh PC Windows 10 (`i3-7100`) ở nhà:
- Mất nhịp quá `3` phút (`180s` do cúp điện / rớt mạng / treo MT5) -> **hú Telegram/Discord ngay lập tức**.
- PC có điện nối lại -> tự báo `[RECOVERED]`.
- MT5 báo `orphan_no_sl > 0`, `kill_switch = true`, `AMBER/RED_BRAKE` hoặc `daily_dd >= 2,5%` -> báo ngay.
- Mở `https://<ten-app>.herokuapp.com` trên điện thoại xem trực tiếp trạng thái Equity / lệnh mở / tuổi nhịp mọi lúc.

---

## Bước 1 — Tạo Bot Telegram nhận cảnh báo (~1 phút, miễn phí)

1. Mở Telegram, nhắn `@BotFather` -> gõ `/newbot` -> đặt tên bất kỳ -> nhận chuỗi **`TELEGRAM_BOT_TOKEN`**.
2. Nhắn 1 câu `hi` vào chính con bot vừa tạo, rồi nhắn `@userinfobot` để lấy số **`TELEGRAM_CHAT_ID`** của bạn.
3. *(Tùy chọn)* Nếu thích Discord, chỉ cần tạo Webhook trong kênh Discord để lấy `ALERT_WEBHOOK_URL` (không cần Telegram).

---

## Bước 2 — Deploy lên Heroku (Không cần đụng `API Clients` hay `Authorized Applications`)

Bạn có **2 cách** (chọn cách thấy gọn hơn):

### Cách A — Dùng Heroku CLI (Đăng nhập trực tiếp bằng trình duyệt MFA, không cần copy API Key)
1. Cài Heroku CLI trên Windows (`winget install Heroku.HerokuCLI`), rồi chạy:
   ```powershell
   heroku login
   heroku create naqex-deadman-watch --region eu
   heroku ps:type web=basic -a naqex-deadman-watch
   ```
   *(Quan trọng: chọn `--region eu` và `web=basic` để dyno chạy 24/7 không tự ngủ.)*
2. Thiết lập biến bí mật trên Heroku (chỉ lưu trên server Heroku, không lưu vào Git):
   ```powershell
   heroku config:set -a naqex-deadman-watch `
     NAQEX_INGEST_TOKEN="chon-mot-chuoi-bi-mat-dai-bat-ky" `
     NAQEX_VIEW_TOKEN="mat-khau-xem-trang-web-tren-dien-thoai" `
     TELEGRAM_BOT_TOKEN="token-tu-BotFather" `
     TELEGRAM_CHAT_ID="so-chat-id-cua-ban" `
     STALE_AFTER_SEC="180"
   ```
3. Đẩy đúng thư mục `heroku_deadman` lên Heroku:
   ```powershell
   git subtree push --prefix tooling/ai-engines/ops_cloud/heroku_deadman https://git.heroku.com/naqex-deadman-watch.git main
   ```

### Cách B — Nếu muốn AI Agent tự deploy giúp trên máy bạn
- Không bao giờ dán Heroku API Key lên khung chat.
- Nếu muốn agent tự chạy lệnh `heroku` trên máy bạn, chỉ cần vào **Windows Environment Variables** (User env) thêm biến `HEROKU_API_KEY` (hoặc tự chạy `heroku login` một lần trên PowerShell).

---

## Bước 3 — Cài trên PC phụ Windows 10 (`i3-7100`, tháo `GTX 1660`)

1. Cài biến môi trường User trên PC phụ:
   ```powershell
   [Environment]::SetEnvironmentVariable("NAQEX_DEADMAN_URL", "https://naqex-deadman-watch.herokuapp.com/api/heartbeat", "User")
   [Environment]::SetEnvironmentVariable("NAQEX_INGEST_TOKEN", "dung-chuoi-bi-mat-o-buoc-2", "User")
   ```
2. Chạy thử 1 nhịp dry-run để xác nhận đọc đúng `naqex_heartbeat.json`:
   ```powershell
   python tooling\ai-engines\ops_cloud\heroku_deadman\pc_heartbeat_sender.py `
     --heartbeat-path "C:\NaqexMT5\MQL5\Files\naqex_heartbeat.json" `
     --account-label "FTMO_HOME_PC" --once --dry-run
   ```
3. Đăng ký Windows Task Scheduler chạy `--once` mỗi `1` phút (hoặc chạy daemon `--interval-sec 60` lúc Windows khởi động) — kết hợp BIOS **`Restore on AC Power Loss -> Power On`** và dây mạng LAN cắm thẳng.
4. Trên điện thoại, lưu bookmark: `https://naqex-deadman-watch.herokuapp.com/?token=<NAQEX_VIEW_TOKEN>`.

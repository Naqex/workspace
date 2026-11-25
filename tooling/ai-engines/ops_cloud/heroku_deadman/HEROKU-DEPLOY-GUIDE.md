# Hướng Dẫn Vận Hành Trạm Canh Heroku Dead-Man's-Switch (`12 USD/tháng` <= Trần `13 USD` Student)

App đã hiệu chuẩn đúng gói **GitHub Student Heroku Credits (`312 USD`, hiệu lực `2026-10-01 -> 2028-09-30`)**:
- **`1 × Basic Dyno` (`7 USD/tháng`, 24/7 không ngủ)** + **`1 × Heroku Postgres Essential-0` (`5 USD/tháng`, lưu vĩnh viễn lịch sử heartbeat & cảnh báo qua mọi đợt restart dyno 24h)** = **`12 USD/tháng <= 13 USD/tháng`** hạn mức gói Student (`~264 USD / 312 USD` cho 22 tháng còn lại -> **`0 USD` trừ thẻ** tới `30/09/2028`).
- **Nhắc lịch quan trọng:** đặt lịch ngày **`25/09/2028`** để tắt dyno/database hoặc chuyển gói trước khi credit hết hạn ngày `30/09/2028`.
- **Chức năng (`OrderSend = 0`):** mất nhịp `> 180s` (cúp điện/rớt mạng/treo MT5) -> hú Telegram/Discord ngay (`[PC_OFFLINE]`), nối lại -> báo `[RECOVERED]`, có `orphan_no_sl > 0` / `kill_switch` / `AMBER-RED` -> báo khẩn; xem trực tiếp trên điện thoại tại `GET /`.

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
   heroku create <HEROKU_DEADMAN_APP> --region eu
   heroku ps:type web=basic -a <HEROKU_DEADMAN_APP>
   ```
   *(Quan trọng: chọn `--region eu` và `web=basic` để dyno chạy 24/7 không tự ngủ.)*
2. Thiết lập biến bí mật trên Heroku (chỉ lưu trên server Heroku, không lưu vào Git):
   ```powershell
   heroku config:set -a <HEROKU_DEADMAN_APP> `
     NAQEX_INGEST_TOKEN="chon-mot-chuoi-bi-mat-dai-bat-ky" `
     NAQEX_VIEW_TOKEN="mat-khau-xem-trang-web-tren-dien-thoai" `
     TELEGRAM_BOT_TOKEN="token-tu-BotFather" `
     TELEGRAM_CHAT_ID="so-chat-id-cua-ban" `
     STALE_AFTER_SEC="180"
   ```
   *(Tùy chọn: đặt thêm `NAQEX_NODE_RDP_HINT="<TAILSCALE_IP>"` trong config Heroku nếu muốn hiển thị gợi ý RDP trong tin nhắn Telegram — không ghi cứng IP trong mã nguồn.)*
3. Đẩy đúng thư mục `heroku_deadman` lên Heroku:
   ```powershell
   git subtree push --prefix tooling/ai-engines/ops_cloud/heroku_deadman https://git.heroku.com/<HEROKU_DEADMAN_APP>.git main
   ```

### Cách B — Nếu muốn AI Agent tự deploy giúp trên máy bạn
- Không bao giờ dán Heroku API Key lên khung chat.
- Nếu muốn agent tự chạy lệnh `heroku` trên máy bạn, chỉ cần vào **Windows Environment Variables** (User env) thêm biến `HEROKU_API_KEY` (hoặc tự chạy `heroku login` một lần trên PowerShell).

---

## Bước 3 — Cài trên PC phụ Windows 10 (`i3-7100`, tháo `GTX 1660`)

1. Cài biến môi trường User trên PC phụ:
   ```powershell
   [Environment]::SetEnvironmentVariable("NAQEX_DEADMAN_URL", "https://<HEROKU_DEADMAN_APP>.herokuapp.com/api/heartbeat", "User")
   [Environment]::SetEnvironmentVariable("NAQEX_INGEST_TOKEN", "dung-chuoi-bi-mat-o-buoc-2", "User")
   ```
2. Chạy thử 1 nhịp dry-run để xác nhận đọc đúng `naqex_heartbeat.json`:
   ```powershell
   python tooling\ai-engines\ops_cloud\heroku_deadman\pc_heartbeat_sender.py `
     --heartbeat-path "C:\NaqexMT5\MQL5\Files\naqex_heartbeat.json" `
     --account-label "FTMO_HOME_PC" --once --dry-run
   ```
3. Đăng ký Windows Task Scheduler chạy `--once` mỗi `1` phút (hoặc chạy daemon `--interval-sec 60` lúc Windows khởi động) — kết hợp BIOS **`Restore on AC Power Loss -> Power On`** và dây mạng LAN cắm thẳng.
4. Kiểm tra trạng thái API qua header `X-Naqex-View-Token` (**không** truyền token trong query string trên URL để tránh lọt bí mật vào access log của router Heroku):
   ```powershell
   curl.exe -s -H "X-Naqex-View-Token: <NAQEX_VIEW_TOKEN>" "https://<HEROKU_DEADMAN_APP>.herokuapp.com/api/status"
   ```

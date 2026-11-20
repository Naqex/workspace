# Inbox nhật ký giao dịch

Đặt bản xuất CSV, HTML hoặc XML vào thư mục này. Bản xuất cá nhân được Git
bỏ qua. Từ root workspace, chạy một lệnh.

```powershell
uv run --project tooling/strategy-engines/observer --no-sync python -m tooling.ai_engines.bot_live_auditor --output .runtime/bot-lab-live.json
```

Output là scorecard theo từng file cho Swing 10k/25k và Standard 10k/50k.
Lần chạy sau dùng tên output mới. Ưu tiên bản xuất full history từ Myfxbook
hoặc MT5 có timestamps gồm múi giờ, giá mở/đóng, lot, stop lúc mở và chi phí.
MQL5 Signals, Darwinex và cTrader có thể dùng bảng một dòng mỗi giao dịch
với các cột tương đương. Xem [playbook](../../../../planning/research/BOT-REVERSE-LAB-PLAYBOOK.md#scorecard-ftmo-từ-log-thực-chiến)
để khai múi giờ và nguồn đường giá khi cần.

Log là dữ liệu để kiểm toán. Runner xử lý offline và trả `unknown` cho
trường thiếu. Không bỏ file thông tin đăng nhập hoặc package bot vào inbox.

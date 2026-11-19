# FTMO read-only / shadow — ba bước

**Chưa có lệnh broker trong runner này.** Máy chưa mở MT5 thì runner tự dùng
replay có nhãn rõ; replay không chứng minh đã kết nối FTMO hoặc đã đo slippage.

1. Mở PowerShell tại workspace và chuẩn bị runtime local đã khóa:

   ```powershell
   cd D:\ANNAM\TradingWorkspace
   uv sync --project tooling/strategy-engines/observer --locked --no-build
   ```

2. Thu specification/Bid/Ask. Nếu muốn dữ liệu thật, tự mở và đăng nhập đúng
   **FTMO DEMO/TRIAL USD** trước; không dùng tài khoản real hoặc terminal khác.

   ```powershell
   uv run --project tooling/strategy-engines/observer --no-sync python -m tooling.ai_engines.ftmo_trial_runner --mode read-only --seconds 60
   ```

3. Thử sổ paper bằng replay ngay:

   ```powershell
   uv run --project tooling/strategy-engines/observer --no-sync python -m tooling.ai_engines.ftmo_trial_runner --mode shadow-paper --replay
   ```

Mỗi lần chạy có output private mới, in đường dẫn khi xong. Xem
`TARGET_ACCOUNT_SPEC_SNAPSHOT.json`, `SPEC_PARITY_DIFF.json`, `quotes.parquet`,
`quote_capture.json`, `report.json`; shadow còn có `shadow_paper_ledger.json`
và journal phát lại. Fixture mặc định có intent giả lập để kiểm đường xử lý;
không phải một tín hiệu giao dịch thực. Replay có timestamp pacing; `--speed`
chỉ thay tốc độ phát lại, không đổi timestamps hoặc bỏ quotes.

## Chuyển sang shadow trên quote MT5 thật

Kiểm tra nhanh terminal đang mở trước khi thu dữ liệu:

```powershell
uv run --project tooling/strategy-engines/observer --no-sync python -m tooling.ai_engines.ftmo_trial_runner --check-mt5-ready
```

Kết quả ở `MT5_PREFLIGHT.json`: connected, ping gần nhất do terminal báo,
tuổi quote và symbol đọc được. Exit code `2` nghĩa chưa sẵn sàng; checker không
tự bật terminal, login hoặc phát lại fixture. Ping này không là phép đo RTT mới.
`read_only_ready=true` vẫn chưa là `shadow_ready`; sessions/news/seeds/spec parity
cần xác minh riêng. Thời gian kiểm đo được phụ thuộc IPC và trạng thái máy.

Không thể hứa cold setup hoàn tất trong 30 giây. Entry point có một lệnh,
nhưng prerequisites phải được xác minh trước. Dùng thêm `--manifest <private.json>`
và khi nhiều terminal có `--terminal <terminal64.exe>`. Runner không mở terminal,
không login, không đổi account/symbol selection và không gửi lệnh.

Để chờ chủ tài khoản mở MT5 và đăng nhập FTMO Demo/Trial USD:

```powershell
uv run --project tooling/strategy-engines/observer --no-sync python -m tooling.ai_engines.ftmo_trial_runner --watch-mt5 --watch-timeout 300 --seconds 60
```

Watcher chạy trong terminal hiện tại, mặc định kiểm mỗi 5 giây; có thể đổi bằng
`--watch-poll-seconds`. Thời gian chờ `--watch-timeout` và thời gian ghi spread
`--seconds` đều giới hạn 1–3.600 giây. Khi nhận đúng account và quote đủ mới,
công cụ bind executable/account hash/server, chụp `TARGET_ACCOUNT_SPEC_SNAPSHOT.json`,
ghi `SPEC_PARITY_DIFF.json` rồi lưu Bid/Ask/spread thành Zstd Parquet có SHA256.
Mất terminal hoặc đổi account giữa probe và capture sẽ báo lỗi; không tự phát
fixture. Nhiều terminal cần đường dẫn chỉ định; terminal ngoài FTMO hoặc account
thật không được nhận. Đây là thu thập read-only, chưa xác nhận quyền shadow,
biểu phí commission hoặc lịch giao dịch đầy đủ.

Capture `READ_ONLY` native lấy Bid/Ask mới nhất mỗi 250 ms và ghi cửa sổ quan
sát từng mã trong `report.json`. So `first_msc` và `last_msc` với thời lượng
chạy để phát hiện đoạn báo giá ngắn, kể cả khi runner trả thành công. Đây là
mẫu báo giá đã thấy. Đường đọc lịch sử theo thời điểm vẫn dùng riêng cho replay
và shadow. [Kết quả đối soát](FTMO-DEMO-10K-STANDARD-RESEARCH-20261119.md).

`WATCH_REPORT.json` giữ kết quả timeout/interrupt/failure; exit `2` là chưa thu
thành công, `130` là đã ngắt. Poll/IPC có thể kết thúc muộn hơn deadline một
probe đang chạy. Không cài daemon/service, không tự đăng nhập và không gửi lệnh.

Manifest kế thừa schema trong [runbook adapter V19](FTMO-FREE-TRIAL-ADAPTER-V19-20261116.md):
binding account hash/server, phase, capture window, exact seeded H1 từ nguồn
đã admission, specs, lịch tin và holiday có provenance/known-at/coverage.
`policy=V16` hoặc `V20`; V20 cần `v20_profile` đúng một trong ba profile đã
[freeze](VOLTARGET-SHADOW-V20-FREEZE-20261117.json). Các profile vẫn research-only.

Python SDK không tự xuất đủ lịch session. Script chỉ đọc
[`mt5_readonly_sessions.mq5`](../../tooling/ai-engines/mt5_readonly_sessions.mq5)
có thể xuất quote/trade sessions từ terminal ra MQL5/Files. Script được
source-review; chưa compile/chạy trên terminal trong V20 nếu terminal vắng.
Giữ export private vì có login phục vụ binding; không commit hoặc gửi lên chat.

Khai báo `session_export` gồm path/SHA256, source, known_at_msc, from_msc,
to_msc, coverage_complete và session_timezone đã xác minh. Không tự suy
múi giờ server hoặc holiday từ giờ Windows. Session export thường kỳ không
thay thông báo lịch đóng sớm theo ngày. Thiếu seed/news/session/spec hợp lệ
thì shadow dừng hoặc chặn entry có reason; không biến unknown thành an toàn.
Khi có export và múi giờ hợp lệ, parity diff kiểm deadline đóng của ngày UTC
hiện tại có nằm trong weekly trade session hay không, có DST. Đây không là
chứng nhận độc lập rằng lịch holiday/đóng sớm của broker đã đầy đủ.

MFE/MAE chỉ trên quotes đã quan sát; không chứng nhận từng giây không có
quote. Slippage thực cần log request/fill bên ngoài cùng account/intent;
capture spread không tự đo được slippage. Kết thúc process có thể còn vị thế
paper: journal/report giữ trạng thái, cần replay/reconciliation trước resume,
không xóa ledger để coi như đã flat. Vị thế broker không bị tác động.

## Đọc lại evidence V19 đã nén

`evidence_compaction.EvidenceStore` đọc trực tiếp archive và kiểm cả SHA256
bản nén/bản gốc. Các consumer cũ đã freeze vẫn giữ nguyên code; khi cần chạy
lại chúng, khôi phục đúng đường file và byte gốc:

```powershell
uv run --project tooling/strategy-engines/observer --no-sync python tooling/ai-engines/evidence_compaction.py restore --relative "Full-pack/OLHC-PRIMARY-quotes.npy"
```

Tên tương đối phải lấy từ `evidence-zstd-v20/MANIFEST.json` của job V19,
không đoán tên theo ví dụ. Bỏ `--relative` sẽ restore toàn bộ các file đã nén,
làm tăng lại dung lượng tương ứng. Restore không ghi đè file khác nội dung.

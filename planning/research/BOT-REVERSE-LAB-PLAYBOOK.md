# Bot Lab và tài khoản FTMO Trial

## Đưa bot vào lab

Chỉ phân tích bản bạn có quyền dùng. Copy vào
`research/bot_reverse_lab/inbox/` (Git ignore). Không chạy bot, DLL, pyc hoặc EA
lạ trong Python/MT5 để kiểm an toàn. Lab chỉ đọc dữ liệu; không gỡ khóa EX4/EX5.

```powershell
uv run --project tooling/strategy-engines/observer --no-sync python -m tooling.ai_engines.bot_reverse_engineer --inspect research/bot_reverse_lab/inbox/bot.mq5
```

Hỗ trợ source `.mq4/.mq5/.py/.cs/.pine`: chỉ báo/timeframe, bằng chứng entry,
exit/SL/TP/trailing, giờ phiên và sizing, kèm dòng nguồn và SHA256. Python dùng
AST/tokenizer; ngôn ngữ khác dùng mẫu cấu trúc, không giả là compiler đầy đủ.

Binary `.ex4/.ex5/.dll/.pyc`: ASCII/UTF16 strings; PE import names nếu có PE
header hợp lệ. Không load DLL, không deserialize pyc, không execute mẫu.
EX4/EX5 có thể không lộ strings; hồ sơ thiếu dữ liệu không có nghĩa bot sạch.

Preset `.set/.ini/.chr` dùng cùng `--inspect`: giữ current/start/step/stop/flag,
kể cả tuple MT5 và các dòng optimization riêng của MT4. Login/password/server/
license values được che. Đơn vị SL/TP vẫn unknown nếu thiếu symbol/digits;
preset không chứng minh code thực thi hoặc lợi thế của bot.

Để kiểm thêm quy mô chi phí đã xác minh, dùng cùng đơn vị giá:

```powershell
uv run --project tooling/strategy-engines/observer --no-sync python -m tooling.ai_engines.bot_reverse_engineer --inspect research/bot_reverse_lab/inbox/bot.py --friction 0.75 --natural-sl 8 --retention 0.8
```

Các số trên là ví dụ input, không là biểu phí hoặc SL của bot chưa phân tích.
Không cung cấp scale thì Gate1 giữ missing-evidence. Gate1 rớt chỉ in JSON ra
stdout, không tạo file phụ. `exit0` nghĩa inspect thành công, **không** là
strategy pass. CLI không tự chạy SL/account/Monte Carlo. Pipeline giữ Stage-0
và cần recipe nhân quả/frozen, hard SL, costs/data được review trước Gate2.

Nhân lot trong ngữ cảnh thua hoặc SL bằng0 là cờ cần chặn/review. Lọc ngày cố
định có thể là lịch lễ hợp lệ; không tự gán người viết là lừa đảo. Regex không
chứng minh đầy đủ control flow; absence of findings không là FTMO-safe.
Rủi ro SL quá5% cần equity/volume/contract thực, không thể suy từ khoảng giá.

## Phân tích trade log

Chuẩn hóa CSV/JSON/HTML table thành các cột `open_time,type,symbol,price,sl,tp,
close_time,profit,volume`. JSON có thể là list hoặc `{"trades":[...]}`. HTML
chuẩn được giữ tương thích. Native MT4 closed-trade tables và MT5 Deals/Orders
được nhận diện từ `.htm/.html/.xml`; header Symbol/Period/Inputs/Bars/Ticks/
Modelling quality được trích xuất. Chỉ closed table đầy đủ hoặc MT5 position-ID
pairing không có partial/reversal mới vào cloner; thiếu identity không đoán bằng
order ID. XML không cho phép DTD/entities. Locale hoặc số mơ hồ giữ review.

```powershell
uv run --project tooling/strategy-engines/observer --no-sync python -m tooling.ai_engines.bot_reverse_engineer --clone-log research/bot_reverse_lab/inbox/trades.csv --log-timezone UTC
```

Timestamp có offset thì ưu tiên offset. Naive timestamp bắt buộc khai timezone;
không đoán theo máy/server. Giờ DST mơ hồ hoặc không tồn tại bị loại. Phân bố
giờ dùng UTC; escalation chỉ so lệnh cùng symbol đã đóng trước entry hiện tại.
Thiếu close time/market data giữ unknown, không lấy profit tương lai suy tín hiệu.

Có thể thêm `--market-store <private-bindings.json>` với mapping:

```json
{"EURUSD":{"path":"E:/admitted-bid-store","scale":100000,"time_basis":"UTC"}}
```

Loader reuse `MarketDataStore` và checksums; chỉ dùng bars hoàn tất trước entry.
Xuất ATR H1/H4, SL/TP theo ATR, SMA/Donchian20 H1, RSI14 đơn giản, PDH/PDL và
Asian00–06UTC. Nguồn Bid này không có Ask thực và không chứng nhận execution.
Fingerprint **không khôi phục duy nhất thuật toán** hoặc tự tạo chiến lược có
thể backtest9năm. Bước tiếp là viết contract cơ chế có thể bác bỏ, đăng ký trial,
đối chiếu quyết định trước outcome, rồi chạy Stage-0/Dev đúng protocol.

V26 companion inventory quét metadata D/E với exclusions/limits được khai báo,
chỉ mở nội dung có association hoặc MT/tester context. Association theo tên/
cùng folder là gợi ý, không chứng minh cùng bot. Overlay/hash và nội dung preset/
report nằm trong private job; không sửa profiles V25 đã seal hoặc publish source.

Nguồn định dạng: [MT5 tester reports](https://www.metatrader5.com/en/terminal/help/algotrading/testing_report)
và [MT4 tester report](https://www.metatrader4.com/en/trading-platform/help/autotrading/tester/tester_report).
Actual supported layouts được khóa bằng fixtures; không coi parser là compiler
hoặc hỗ trợ mọi version/ngôn ngữ của terminal.

## Thay tài khoản Free Trial

Connector hiện có:

| Thành phần | Đường dẫn repo | Vai trò |
|---|---|---|
| Product connector | `projects/trader/foundation_v2/scripts/mt5_connector.py` | DPAPI secret, terminal portable riêng, identity/error checks |
| Product clock | `projects/trader/foundation_v2/scripts/mt5_clock.py` | Exact FTMO-Demo2026 broker-clock→UTC; không suy mọi server |
| Native API owner | `projects/trader/foundation_v2/api-rust/src/mt5_connector.rs` | Credential sealed trong `mt5_connections`; không đọc lại password cũ |
| Legacy socket | `projects/trader/archive/legacy/root/mt5_data.py` | Bridge lịch sử, không khởi động lại để làm runtime mới |
| Trial binding | `tooling/ai-engines/ftmo_connection.py` | Reuse helper product, owned process tree, env-file parser, clock proxy |
| Capture/shadow | `tooling/ai-engines/ftmo_trial_runner.py` | Snapshot/parity, quote capture, paper ledger; không broker orders |

Trader pin giữ nguyên. Không decrypt credentials cũ hay đổi tài khoản trên
terminal Trader đang hoạt động. Template bốn biến: `config/ftmo_free_trial.env.example`.

```powershell
Copy-Item config/ftmo_free_trial.env.example config/ftmo_free_trial.env
notepad config/ftmo_free_trial.env
uv run --project tooling/strategy-engines/observer --no-sync python -m tooling.ai_engines.ftmo_trial_runner --credentials-file config/ftmo_free_trial.env --check-mt5-ready
```

Điền `FTMO_MT5_LOGIN`, `FTMO_MT5_PASSWORD`, `FTMO_MT5_SERVER`, và đường dẫn cài
MT5 trong `FTMO_MT5_TERMINAL_PATH`. File filled đã ignore; không paste password
vào chat/argv. Loader parse literal, không chạy PowerShell expressions.
Muốn nạp vào process environment thay vì file, dùng parser có sẵn:

```powershell
uv run --project tooling/strategy-engines/observer --no-sync python -c "import os; from tooling.ai_engines.ftmo_connection import credentials; os.environ.update(credentials('config/ftmo_free_trial.env')); from tooling.ai_engines.ftmo_trial_runner import main; raise SystemExit(main())" --check-mt5-ready
```

Environment chỉ sống trong process này, không sửa global/user environment.
Server/identity/demo/USD được kiểm trước capture; account đổi thì dừng.
Một portable terminal riêng được tạo dưới `.runtime/ftmo-trial-readonly-v24/`,
tắt Experts/DLL và nằm trong Windows Job sở hữu toàn process tree. Hết lệnh
thì đóng tree. Không thay tài khoản/terminal product. Stale lock phải reconcile
process trước khi dọn; không tự xóa lock để chạy trùng.

Dùng `--watch-mt5 --watch-timeout 300 --seconds 60` để chờ quote đủ mới;
`--mode read-only --seconds 60` để capture. Không có credentials thì vẫn giữ
workflow attach vào terminal đã chạy của V23. Khi dùng file không được fallback
fixture. Native `--mode shadow-paper --manifest <private.json>` còn đòi seed,
lịch news/holiday/session, spec parity và clock scope hợp lệ; login thành công
không làm các gate này tự đạt. Replay fixture là tùy chọn riêng.

10giây là mục tiêu thao tác thay thông tin sau khi đã cài SDK/MT5, không là cam
kết thời gian mạng/cold install. V24 không có credential mới để chứng nhận
native login/capture/clock parity thực; mới kiểm fixtures và no-terminal path.

## Đọc kết quả nhanh

Đối chứng `controls/` chỉ chứng minh các pattern trong ba mẫu được bắt đúng;
không phải100% recall ngoài thực tế. Raw scan/fingerprint/Dev pass/account model
và quyền trade là các tầng khác nhau. Gate2 rớt giữ một decision receipt; không
sinh105 starts/5.000 bootstrap. Gate3 kiểm committed freeze, content/input/code
bindings và tính lại Dev gate. V24 P80_20 đã rớt, giữ V16/V19 BASE_GUARD.

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
và [MT4 tester results](https://www.metatrader4.com/en/trading-platform/help/overview/strategy_tester/strategy_tester_results).
Actual supported layouts được khóa bằng fixtures; không coi parser là compiler
hoặc hỗ trợ mọi version/ngôn ngữ của terminal.

## Scorecard FTMO từ log thực chiến

Dùng [inbox live_signals](../../research/bot_reverse_lab/inbox/live_signals/README.md)
và lệnh duy nhất trong hướng dẫn inbox. Có thể truyền thêm một file CSV/HTML/XML
để audit riêng. Kết quả mặc định là JSON theo file. Thêm `--include-rows`
với output private nếu cần schema chuẩn hóa từng dòng. Tệp người dùng đặt vào
inbox được Git bỏ qua. Giữ source hash và scope cùng kết quả.

- Hỗ trợ bảng CSV/HTML một dòng một lệnh với header Myfxbook, MQL5 Signals,
  Darwinex/cTrader dạng lịch sử phẳng và bảng tổng quát. MT4/MT5 History dùng
  parser đã có để nhận closed Positions hoặc ghép Deals theo position ID.
  Partial, reversal, thiếu ID hay layout không nhận diện trả warning/unknown.
  Bảng độc quyền cần xuất cột chuẩn trước khi nạp.
- Khai `--timezone` theo nguồn nếu timestamp thiếu offset. Ngày mơ hồ cần
  `--date-order dmy|mdy`. Ngày thiếu giờ giữ độ phân giải ngày. Số thập phân khác
  dấu chấm khai `--decimal-mark`. Chỉ dùng `--volume-lots` hoặc
  `--stop-is-initial` khi source bảo đảm đơn vị hoặc phiên bản của SL.
  `--profit-basis net|gross` và `--currency USD` dùng khi source xác nhận.
  Mặt bằng R tự ghi không quy đổi thành PnL USD.
- Nếu có giá đã được phép đọc, `--market-store` nhận JSON mapping theo mã
  với `path`, `scale`, `time_basis: UTC`, `bar_seconds: 60` và
  `scope: DEVELOPMENT`. Loader kiểm hash cột clock và mốc cuối trước khi
  mở OHLC. Bid M1 dùng proxy spread cho Ask, chỉ lấy cả phút đã giữ đầy đủ
  cho MAE/MFE. Risk sizing cần **SL ban đầu**, giá và timestamp đủ để tính
  PnL. Đường vốn chỉ xác nhận được tại mốc có đủ giá cho mọi vị thế đang mở.
- Với Standard funded, `--calendar` nhận JSON có `source`,
  `valid_from_utc_msc`, `valid_to_utc_msc`, và `breaks_by_symbol`
  chứa cặp mốc bắt đầu/kết thúc đã xác minh, sắp xếp theo thời gian. Khi
  thiếu lịch, nắm giữ xuyên giữa thứ Bảy chỉ là cờ kiểm lại. Swing được
  miễn quy tắc đóng qua kỳ nghỉ áp dụng cho funded Standard.
- Nhãn theo [Selective Win Diagnosis](../../.agents/skills/strategy-qualification/references/selective-win-diagnosis.md).
  Nhãn bị cắt bởi lịch cần lệnh có exit reason lịch và cặp giữ tiếp cùng entry,
  risk và target costs. `--paired-continuation` nhận JSON khóa hash input và
  profile, với `source`, `input_sha256`, `profile_sha256_lf` hai profile,
  `basis: SAME_ENTRY_INITIAL_RISK_AND_TARGET_COSTS` và `profiles` ánh xạ
  profile → số dòng → `entry_utc_msc`, `exit_utc_msc`, `risk_per_lot_usd`,
  `net_R`. Cặp cần provenance từ phép so sánh giữ nguyên cơ chế. Thiếu
  bằng chứng ưu tiên giữ unknown. MAE/MFE hậu nghiệm không dùng làm entry filter.
- Profile phí bám snapshot [Standard](FTMO-DEMO-10K-STANDARD-FULL13-AND-EXECUTION-20261119.md)
  và [Swing](SWING-10K-AUDIT-MULTIWEEK-AND-WIN-TAXONOMY-20261120.md).
  Giá khớp đã chứa spread. Auditor hạch toán commission và swap đích một lần.
  Đây là reprice trên fills quan sát, chưa dự đoán giá khớp/slippage ở broker đích.
  FTMO 2-Step kiểm equity với 5% ở mốc 00:00 CE(S)T và 10% static. Báo
  riêng margin quan sát và độ phủ. Score 80/20 thể hiện trọng tâm Swing và
  Standard, không cộng điểm cho dữ liệu thiếu hoặc cấp quyền giao dịch.
  [FTMO Trading Objectives](https://ftmo.com/en/trading-objectives/) ·
  [FTMO weekend policy](https://ftmo.com/en/faq/can-i-hold-positions-overnight-or-over-the-weekend/).

[Bằng chứng Bot Lab](BOT-LAB-LIVE-AUDITOR-AND-LEAKAGE-DIAGNOSIS-20261120.md)
đối chiếu cả lệnh thắng và thua từ sổ đã seal, rồi chạy pipeline trên
Performance CSV có sẵn. Giữ khác biệt giữa một journal tự ghi và deal history
broker. Phần trả lại từ đỉnh lời không đủ để kết luận đổi exit cứu được edge.

### Batch leaderboard và blueprint

Dùng lệnh ở [inbox](../../research/bot_reverse_lab/inbox/live_signals/README.md).
Quét CSV/HTML/HTM, bỏ qua README và template, giữ một bản theo SHA cho file
trùng byte. Leaderboard ghi rõ cờ loại và điểm thiếu theo từng file. Cổng
Swing kiểm cả 10k/25k tại 0,50% và 1,00%. Standard kiểm thêm 10k/50k,
giờ nghỉ >2 giờ và cửa tin cấm. Điểm là 80% lợi suất Swing tháng chuẩn hóa
ở risk 0,50% trên sổ yếu hơn, cộng 20% tương ứng Standard khi Standard qua.
Tháng tính theo tháng lịch tính cả đầu/cuối. Unknown và hồ sơ bị loại
không có điểm hoặc thứ hạng.

Batch dùng cùng market store Development ở trên. Có thể cung cấp lịch nghỉ
với --calendar và lịch tin --news-calendar. JSON tin có source, valid_from_utc_msc,
valid_to_utc_msc và restricted_news_by_symbol ánh xạ từng mã tới timestamp
tin FTMO hạn chế theo UTC ms. Danh sách rỗng mang nghĩa người cung cấp xác
nhận mã đó đã được phủ trong khoảng khai báo. Lịch phải kèm nguồn và đủ phủ
cả cửa ±2 phút quanh entry/exit. Hồ sơ lệnh qua mốc khoá dùng cash, lot,
holding, phiên và cờ từ file nguồn. Cash-only giữ riêng khỏi equity và
không lấp mark thiếu ở vị thế đang mở. Mã không có spec/FX conversion
được trả thiếu bằng chứng. Các PASS chỉ để shortlist nghiên cứu.

[Playbook tìm nguồn](LIVE-SIGNAL-SOURCING-PLAYBOOK.md) có preset ≥12 tháng,
≥150 lệnh, DD ≤20% và quyền export. [Báo cáo batch và dry run](BOT-LAB-BATCH-BLUEPRINT-AND-SOURCING-20261120.md).

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

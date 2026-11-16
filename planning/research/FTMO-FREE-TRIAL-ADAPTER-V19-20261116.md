# V19 — bộ thu dữ liệu và shadow cho FTMO Free Trial

**Đã có adapter và kiểm thử offline; chưa xác minh hoạt động trên terminal
FTMO thật. Không có chức năng gửi lệnh broker trong bản này.**
Đọc cùng [spec V18](FTMO-FREE-TRIAL-EXECUTION-SPEC-20261116.md), không thay
biểu phí/điều khoản của tài khoản đích bằng kết quả nghiên cứu.

## Phần đã làm

[`ftmo_free_trial_adapter.py`](../../tooling/ai-engines/ftmo_free_trial_adapter.py)
có hai chế độ:

| Chế độ | Đầu vào → đầu ra |
|---|---|
| `READ_ONLY` mặc định | File bridge hoặc terminal đang chạy được chỉ định rõ → specification, ticks Bid/Ask, phân bố spread theo giờ UTC và mốc balance đầu ngày Prague |
| `SHADOW_PAPER` | Luồng quote/nến đã đóng có thời điểm biết → generator V16 gốc, risk V16/V19 đã khóa, paper ledger và expected fills; không đổi vị thế broker |

SDK `MetaTrader5` chỉ được import khi người vận hành chọn rõ
`--attach-running-terminal`. Trước `initialize`, adapter kiểm tra đường dẫn
đó thuộc terminal đang chạy. Không gọi `login`, `symbol_select`, `OrderCheck`
hay `OrderSend`. Luôn kiểm demo-mode, server/currency và hash danh tính
account. `ALLOW_LIVE_ORDER_SEND=False`; sửa một cờ không tạo quyền execution
hoặc tự biến adapter này thành EA.

Luồng chính: **account/spec binding → quote/nến biết tại thời điểm đó → tín
hiệu từ generator cũ → guards → lot/admission của account engine cũ → paper
entry/SL/P1/exit → expected fill → đối soát với fill bên ngoài**.

Giữ cùng ba sleeve, công thức SL, P1 và sizing đã dẫn ở spec V18. V19 dùng
`selected_profile` trong
[freeze](ASYMMETRIC-RECOVERY-V19-FREEZE-20261116.json); adapter từ chối một
profile khác gắn nhãn V19. Thêm cổng dự phòng stop-equity trong ngày 2,2%
cho paper V16/V19. Đây là overlay vận hành, chưa là chứng nhận performance
sau lịch tin hiện hành.

## Các chốt chặn

- Mốc ngày là **00:00 Europe/Prague**, có DST. Balance đầu ngày được dựng từ
  balance hiện tại trừ mọi cashflow deal đã ghi nhận từ midnight. Không lấy
  floating equity làm anchor hoặc dùng giờ Windows.
- Equity hiện tại bao gồm floating; thiếu/stale account mark thì chặn entry.
  Khi chạm 2,2%, paper ngừng entry và yêu cầu đóng ở quote hợp lệ. SL/gap,
  latency và mất feed vẫn có thể làm vượt ngưỡng; không hứa bảo vệ tuyệt đối.
- Lịch tin phải có source, thời gian biết và coverage hoàn chỉnh cho phiên.
  Mặc định shadow mô phỏng quy tắc Funded Standard: chặn vùng ±2 phút và
  yêu cầu flat sớm 150 giây trước tin. Không coi lịch trống chưa rõ coverage
  là không có tin. Với phase không có restriction, phải cấu hình policy
  riêng có bằng chứng; không suy từ nhãn demo.
- Đóng theo deadline 20:30 UTC cùng ngày hoặc holiday early-close đã biết.
  Thiếu quote sau deadline được ghi là đóng muộn, không backdate. Mất feed
  >2 phút chỉ được thoát ở quote sau khi quan sát được lại.
- P1 chỉ arm sau khi phút trước đã hoàn tất; không dùng high/low tương lai.
  Mức bảo vệ không khớp tick-size broker được gắn
  `PAPER_ONLY_NONEXECUTABLE_PROTECTION_LEVEL`, không làm tròn ngầm.
- Thiếu specification, khác contract size/lot step, SL không hợp hướng/
  stop-level/tick-size, max volume, stale quote hoặc lịch phiên chưa rõ đều
  chặn entry. Guard 30 phút M1 chỉ nhìn phút đã đóng trước decision.
- Intent có ID ổn định; cùng ID nhưng khác nội dung là lỗi. Tick đã biết
  trước khi signal được cung cấp không được dùng làm giá vào hồi tố.

Đóng vì risk và restriction tin có thể xung đột khi feed bị đứt: log riêng
`RESTRICTED_NEWS_EXIT_CONFLICT`. Paper vẫn phản ánh rủi ro và giá thực sự
quan sát; không tuyên bố đã bảo đảm tuân thủ broker trong tình huống đó.

## Seed và parity

H1/H4/D1 dùng bộ tính chỉ báo cũ. Cắt lịch sử còn 1.000 H1 rồi khởi động lại
Wilder ATR/ADX không được coi là cùng state. Native shadow yêu cầu seed có
hash từ mốc 01/11/2017 UTC; file `v16-closed-hour-seed-v1` lưu `first`,
`known_at_msc` và các hàng `t,bo,bh,bl,bc`. Seed chỉ chứa nến đã đóng, thứ tự
tăng, không trùng. Overlap với nến native khác nhau phải dừng để đối chiếu,
không âm thầm trộn feed.

Đã đối chiếu sáu prefix Development từ cùng nguồn M1 gốc: generator native
hourly giữ nguyên thời điểm/chiều/SL. Điều này chưa chứng minh seed broker,
spread hiện hành, lịch tin, fill/latency hoặc toàn bộ loop trên MT5 thật.
Trong máy/runtime kiểm thử hiện tại chưa có SDK `MetaTrader5`; chưa attach
terminal hoặc đăng ký tài khoản mới.

## Lưu log và phát lại

Manifest ở thư mục private: binding chứa `account_hash`, `server`; không đưa
login/password/token vào report. File bridge dùng schema
`ftmo-readonly-bridge-v1`: account/specs, ticks hoặc events theo `known_at_msc`.
Events gồm `account_mark`, `closed_hours`, `closed_M1`, `signal`, `quote`.
`closed_hours` có source và prefix H1; `signal` dùng cho adapter đã sinh
intent hoặc kiểm thử. Khi nối generator từ nến, không thay bằng manual
signal rồi gọi đó là parity chiến lược.

Native shadow chạy hữu hạn tối đa 3.600 giây mỗi lần; mặc định 60 giây.
Nó lưu `effective-paper-plan.json` và `native-shadow-events.jsonl` trước khi
xử lý. Tick ở cùng millisecond được đọc lại tại biên, giữ duplicate có thứ
tự; thay lịch sử biên thì dừng. Account identity được kiểm lại mỗi vòng.
Phát lại journal qua file bridge để đối chiếu state. Khởi động lại có vị
thế paper cần replay/binding review; không tự xóa ledger để reset.

Đối soát fill bên ngoài cần: `intent_id`, `deal_id`, asset, **side của vị thế**,
`leg=ENTRY/EXIT`, volume, price, request/fill time, commission/swap/fee.
Nhiều partial fills được tính giá bình quân theo volume; missing/duplicate/
unexpected/excess hoặc fill trước request không được gọi là match. Slippage
bất lợi đổi dấu giữa BUY/SELL và ENTRY/EXIT. Chuẩn hóa side của deal MT5
sang side vị thế trước khi join; comment gần giống không đủ chứng minh intent.
Quote-only không đo được slippage.

## Cách chạy đã kiểm

Hai CLI `READ_ONLY` mặc định và `SHADOW_PAPER` đã chạy trên **fixture offline**,
có receipt `adapter-CLI-verification.json` trong private V19 job. Test gateway
native giả lập cũng phát lại được cùng account state/expected fills. Đây
không phải lệnh hay fill FTMO đã thực hiện.

```powershell
$env:PYTHONPATH='projects/trader/foundation_v2;tooling/ai-engines;tooling/ai-engines/tests;tooling'
python tooling/ai-engines/ftmo_free_trial_adapter.py --help
python -m unittest test_ftmo_free_trial_adapter -v
```

Để dùng tài khoản thật trong tương lai cần manifest private và SDK phù hợp
trong Python runtime, terminal đã được owner chuẩn bị và binding verified.
`--attach-running-terminal` chỉ mở quyền đọc, không quyền gửi lệnh.
Chưa có manifest/binding/seed/lịch tin của tài khoản đích nên V19 không chạy
lệnh này trên terminal của owner.

## Nguồn và giới hạn điều khoản

Ngày 16/11/2026 đã đọc được các tài liệu chính thức MQL5:
[initialize](https://www.mql5.com/en/docs/python_metatrader5/mt5initialize_py),
[ticks](https://www.mql5.com/en/docs/python_metatrader5/mt5copyticksrange_py),
[rates](https://www.mql5.com/en/docs/python_metatrader5/mt5copyratesfrompos_py),
[deals](https://www.mql5.com/en/docs/python_metatrader5/mt5historydealsget_py),
[symbol](https://www.mql5.com/en/docs/python_metatrader5/mt5symbolinfo_py) và
[account](https://www.mql5.com/en/docs/python_metatrader5/mt5accountinfo_py).
HTML/hash và receipt ở private V19 job; chưa là runtime acceptance.

Hai FAQ FTMO về tin và giữ lệnh không truy cập lại được do TLS timeout;
web tool cũng không cung cấp nội dung đối soát. Ngưỡng của engine là
**giả định nghiên cứu đã version hóa**, chưa chứng minh điều khoản FTMO hiện
hành của account. Tiếp tục phải đối chiếu Client Area/program/phase, session,
specification và các khoản phí của chính tài khoản trước vận hành.

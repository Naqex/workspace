# V25 external E1 — H1 engulfing + RSI37, trước outcome

Chọn tối đa một cơ chế từ nhóm candlestick/oscillator, không coi đổi RSI/
CCI/MFI/Stochastic trên cùng mẫu nến là bốn cơ chế độc lập. Trong Top10
structural source, ưu tiên RSI có default/expiry rõ rồi thứ tự tên; chọn
`BullishBearish Engulfing RSI.mq5` nếu có. Không đủ nguồn/không trong Top10
thì0 trials. Top10 không xếp bằng PnL. Không lấy DarkCloud/Piercing source
có orphan signal block làm bản sạch và không tự sửa source đó để cứu ý tưởng.
Source đã đọc/review SHA256:
`f31d225aa34323541e4834c4f904d9b3a9d43c695afd04c319d4f3bcfed76313`.
Hash/defaults khác thì dừng, không chỉ tin tên file.

E1: EURUSD H1 (chart context mới khai báo, source dùng `_Symbol/_Period`),
warmup2017-11 và Dev2018–2023. Hai chiều BUY/SELL, dùng completed H1, không
thêm H4 bias/session filter. Đây là independent formula port với provenance,
không native binary/MT5 parity hoặc code/license redistribution.

Giữ defaults source: AvgBody12, trend SMA5, RSI37, SL200point=20pip trên
EURUSD5digits. Tại bar1 vừa đóng / bar2 trước đó:

- BUY: bar2 giảm; body tăng bar1 >mean12body; close1>open2; open1<close2;
  midpoint thân bar2 <SMA5 tại bar2; RSI37 tại bar1<40.
- SELL đối xứng: bar2 tăng; body giảm bar1>mean12body; close1<open2;
  open1>close2; midpoint thân bar2>SMA5 tại bar2; RSI37 tại bar1>60.
- Source hard SL = entry ±max(200point, observed spread). Quy tắc này được
  mô tả trước outcome; cost gate không tự kéo SL. Original TP200point,
  duration10bars và RSI exit được giữ làm metadata; chưa code SL/TP trước
  khi Stage0 chính đạt.

Raw Stage0 chưa loại tín hiệu do đang có position: đo cả cơ hội chồng lấn,
không coi raw cadence là số lệnh tài khoản. First M1 open ở/sau quyết định
≤1phút và endpoint ≤1phút; thiếu thì unknown, không kéo last quote sang.
H1 được aggregate từ admitted M1 hoàn chỉnh60bars; data-gap/source-chart
differences vẫn là giới hạn, không khẳng định exact source-bot equivalence.

Primary+8h lịch, diagnostic+4h không dùng chọn. Clamp trước inherited known
holiday/Friday long-close; calendar là declared scenario, chưa EURUSD broker
certification. Paired spread, commission+slip9USD/lot, funding legacy−40USD/lot/
rollover/tripleWednesday nếu giữ qua22UTC. Raw markout không có SL/TP.
Cap median12% bằng exact comparator; giữ>=50% tín hiệu tự nhiên; mọi năm
mean net>0 và >=mean friction; cadence>=40/năm; endpoint gaps không pass.
Nếu primary không đạt thì0 SL-active children, không thử RSI/MA/timeframe
hoặc horizon khác. Nếu đạt, chỉ source-default SL/TP/expiry trong một card
chi tiết riêng trước khi đo; không mở later nếu thiếu path/Dev gates.

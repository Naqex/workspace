# Sửa discovery/screen — protocol trước phép đối chiếu mới

Owner giao sửa các điểm trong [diagnosis](DISCOVERY-DIAGNOSIS-20261108.md).
Đây là execution hữu hạn của yêu cầu sửa hiện tại; không tự đổi trạng thái
Goal đang paused, không mở holdout/broker hoặc hứa có ứng viên challenge.

## Câu hỏi đã khóa

1. Trong một prefix đã consumed, coarse và native tick có cùng signal,
   entries/quantities, costs và kết quả trong phạm vi nào? Nếu khác, quy từng
   lệch cho signal/stop/funding/risk, không mặc định do strategy.
2. Trong624annual FX cases đã completed, tiền mất do closeable-price movement,
   commission/slippage/funding và floating phân bố thế nào? Không lấy gross
   đã chứa spread làm frictionless alpha; không lấy reference−stress làm
   cost-only delta nếu sizing/path khác.
3. Exact recipes đã thử là replication, adaptation hay project hypothesis?
   Chọn bước nghiên cứu bằng original→project differences và availability,
   không chỉ vì indicator nổi tiếng hoặc recipe dễ code.

## Selection, input và execution đã chốt trước numeric mới

- Bốn exact IDs hiện có: `eurusd-h1-shock2-reclaim-atr14x1p5-time12-r025-v1`,
  `eurusd-h1-prior-day-break-atr14x1p5-close20-r025-v1`,
  `eurusd-h1-rsi14-reentry-atr14x1p5-time12-r025-v1`,
  `eurusd-h4-sma20-80-atr14-r025-v1`.
  Chọn dựa trên outcomes đã exposed để **kiểm sai số**, không phát hiện edge:
  shock gần0, daybreak là parent củaR019, RSI bản bị gác, SMA thử nhánhH4/carry.
- Warmup01–31/12/2021 và prefix03–07/01/2022 inclusive từ inputs/cache của
  `coarse-screen-pilot-20261107/execution-v1`. Raw evaluation vẫn là fileQ1,
  chỉ consumed prefix được replay. Rehash raw/cache/protocol/source; không
  xuất lại hoặc tạo dữ liệu thị trường mới. Không mở2025+.
- Hai costs cũ: commission2,50USD/lot/side; reference slippage0,
  financingBUY9,30/SELL−0,31; stress slippage0,00002/side,funding20/20;
  Wed×3/22UTC.10k/planned25USD/mộtposition/noTP/no forcedclose.
  Native internal brakes giữ nguyên; coarse thiếu tickrisk/prop phải nêu rõ.
- Dùng core `run_scenario` và `simulate_coarse`, không engine mới. Một writer,
  trần compute600s, preparation120s,total720s; CANCEL kiểm theo native hourly
  progress và trước mỗi case. Status/log/wall/CPU/source snapshots ở attempt
  mới `execution-v1/screen-calibration-repair-v1`; không overwrite completed.
  Fail giữ log/output, không auto retry. No-fill là inconclusive, không chọn
  thêm window đến khi xuất hiện lệnh.
- Trước run: focused tests cho costdiagnostic/decision-comparison, existing
  coarse causal/stop/gap/state fixtures. Pin code sau khi tests đạt và trước
  worker; không sửa source trong lúc compute.

## Đọc kết quả, không đổi criteria sau outcome

Signal/time/quantity/count khác nhau phải được phân loại bằng artifact;
không so tổng tiền rồi tự coi parity. Stopfill coarse có thể khác tick,
không ép equality hoặc dùng pilotbudget6,25USD làm bound mới.
Mọi signflip, riskstop/rejection, mismatch chưa giải thích đều cần review;
no-fill không chứng minh độ nhạy của filter. Có profit/sign agreement trong
tuần này không là annualerrorbound hoặc false-negative rate toàn catalogue.

Costdiagnostic chỉ đọc sealed624cases, kiểm cả cash/open/funding/net counts,
không sửa fills/rules/costs hoặc sinh chiến lược“không phí”. Đổi return/risk/
exit sau diagnostics là trial mới với consumed exposure giữ nguyên.

## Acceptance của phần sửa

- Tool có fixtures tính tay BUY/SELL, credit/open/rounding và rejects cho
  tamperedcash/count/source binding/nonfinite; actual624rows tái đối soát.
-8calibrationcases đều có terminal hoặc failure/inconclusive ghi đúng;
  signal/entries/risk/cash khác biệt có locator, không tự promotion/rejection.
- Lập source→adaptation map và research admission trong workflow owner;
  giữ empirical benchmark khác intended positive/negative software controls.
- Kết quả/limits/nextaction được lưu ngoài chat. Không đồng nhất “đã sửa quy
  trình trong scope này” với C1/C2 toàn campaign hoặc full engine audit.

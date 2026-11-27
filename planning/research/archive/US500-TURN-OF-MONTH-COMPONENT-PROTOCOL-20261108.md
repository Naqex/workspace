# R025: kiểm thành phần đầu/cuối tháng trước khi triển khai bot

Đăng ký trước outcome mới của component probe. [Campaign](CHALLENGE-CANDIDATE-CAMPAIGN-20261108.md)
vẫn giữ C1/C2; [method review](EQUITY-CALENDAR-HYPOTHESES-REVIEW-20261108.md)
chưa là một strategy đã triển khai. Không thêm policy version chỉ vì có code
phân tích giá hoặc một component dương.

## Nguồn, câu hỏi và phạm vi

Đọc 08/11/2026, McConnell/Xu2008 bản tác giả tại
[Purdue](https://business.purdue.edu/faculty/mcconnell/publications/Equity-Returns-at-the-Turn-of-the-Month.pdf),
intro và mục Aggregate Market Returns/Table1: định nghĩa là ngày giao dịch
cuối tháng và ba ngày giao dịch đầu tháng sau. Paper so daily returns của nhóm
này với các ngày còn lại; không chứng nhận CFD intraday, hardSL hoặc phí hiện
tại. Câu hỏi ở đây: thành phần giá trong phiên có còn đáng đưa sang bot, hay
hiệu ứng quan sát chủ yếu nằm ở khoảng qua đêm?

- Existing US500 canonical unfiltered Bid/Ask, 2019–2024 là evaluation;
  Q4/2018 chỉ lấy previous-session endpoint cho đầu2019. Chọn khoảng này vì
  source/calendar sẵn, tránh giai đoạn old-CFD endpoint thiếu đã biết; chưa xem
  kết quả R025. Đây là exposed retrospective research, không clean OOS.
- Calendar là frozenNYSE từng năm, America/New_York/DST/halfday. Full calendar
  chọn ngày trước khi đọc giá; không định lại last tradingday theo dữ liệu
  còn hiện diện. Dữ liệu thiếu giữ unknown, không dịch ngày hoặc điền close.
- So TOM={lastday,first3days} với REST. Giữ mọi năm, hai block không overlap
  2019–2021 và2022–2024, không thử {-2,+4}, weekdays hoặc lọc ngày theo outcome.
- Close-to-close logreturn dùng exact last Bid close của **phiên liền trước**
  và phiên hôm nay. Tách overnight (previousclose→todayopen) và cashsession
  (todayopen→todayclose), kiểm identity log CTC=overnight+cash.
- Tradable intraday component: calendar decision09:31NY, entryAsk open09:32;
  decision2min trước close, exitBid open phút cuối (15:59/12:59). Chừa open
  recovery slot nếu sau này dùng shared book. Không dùng giá tương lai trong
  quyết định calendar. Thiếu entry/exit quote thì unknown, không execution0.
- Commission0 theo publicFTMO profile, embedded Bid/Ask spread; reference
  slippage0,25/chiều, stress0,75/chiều. Tính net price change chia entryAsk,
  đơn vị bps của giá; không sizing/SL/capital/funding hoặc giả account PnL.
  Overnight/CTC chỉ decomposition chưa trừ swap, không được dùng thay carry
  simulation hoặc suy tiền rút/pass quỹ.

## Kiểm, dữ liệu và quy tắc quyết định trước outcome

Trước chạy kiểm calendar last/first3 qua năm/holiday, log identity, Bid/Ask và
slippage tính tay, missing exact predecessor/endpoint không forwardfill. Đọc
request manifests/seals, hash raw, strictschema/order/grid/BidAsk alignment;
chỉ giữ endpoints cần sau khi validate. Không đọc provider D1/H1 đang quarantine.
Snapshot source/protocol/calendar/input hashes và provenance, status/log,
deadline/cancel/singlewriter. Reuse nguồn có sẵn, không network/broker/modelcalls.

Admission: mỗi năm evaluation phải có quan sát hợp lệ trong cả TOM và REST cho
cả CTC và tradable component; năm không có data không trở thành zero. Báo counts
planned/observed/missing và coverage, không giả đã có full market history.

Chỉ ưu tiên đăng ký intraday bot nếu trong **cả hai block**, TOM mean tradable
netbps>0 và cao hơn REST ở cả reference/stress. Đây là component triage đã
chọn trước, không pvalue/edge proof hoặc loại toàn bộ calendar family. Nếu chỉ
CTC/overnight đáng xem thì để carry design ở trạng thái cần funding/clock
review; không tự chọn holding theo đường equity đẹp. Nếu không đủ thì giữ
negative/inconclusive component và chuyển mechanism khác, không grid ngày/giờ.

Không có trade/order/portfolio engine mới. Không2025+localholdout, account mới,
paidprovider hoặc production. Publication/selection history tiếp tục ghi ngoài
chat; positive component không tự đạt C1 hoặc quyền chạy demo.

# R065: khoảng kết quả có điều kiện khi thiếu một số nến

Đăng ký trước implementation và outcome mới. Parent strategy/kernel/risk/cost
giữ theo [R065](NASDAQ-OPENING5-ORB-PROTOCOL-20261108.md); old unknown và
two-year gate giữ nguyên. Đây là sensitivity model khác, không sửa lịch sử.

## Lý do, giả định và giới hạn

[H1 fixture](NASDAQ-H1-GAP-ENVELOPE-PROTOCOL-20261109.md) đã đối chiếu hai side,
16.624 ticks và 59 M1: H1 chứa mọi giá đã thấy, không có tick ở 14:49, loại
trừ TP nhưng không loại trừ SL. H1 Ask range 6733,140–6763,341, SL6755,070.
Không biết unknown execution thật; ghi một PnL chính xác sẽ sai.

Thử tính **outer bounds có điều kiện** thay vì fill một giá giả: giả định mọi
giá chưa thấy trong phút thiếu nằm trong H1 source cùng side; protective
order vẫn hoạt động theo mô hình fill/cost của parent và không có rejection.
Đây không là chứng minh không có outlier/outage tại broker. H1 chứa thời gian
trước entry, nên chỉ dùng làm biên rộng cho bất định, không làm tín hiệu hoặc
execution quote. Dùng H1 sau đóng giờ để phân tích retrospective, không đưa
thông tin tương lai vào entry/SL/TP/size.

## Recipe khóa trước outcome

- Hai năm 2019 và 2022; 2019 M1 từ `nasdaq-m1-history-v2`, 2022 từ mixed view
  `nasdaq-tick-derived-hour-v1`; calendar và parent manifests/reviews đã có.
  H1 từ `nasdaq-history-v1`. Không fetch, không mở 2025+.
- Entry/SL/10R/exit/halfday/risk25USD/cost reference+stress và null-control
  giống parent. Reset balance 10.000USD/năm; không compounding.
- M1 hợp lệ dùng đúng native open-gap → scheduled-exit → protective logic.
  M1 chạm cả SL và TP giữ cả hai khả năng, không tùy chọn có lợi.
- M1 thiếu khi đang giữ: lấy H1 đúng side. Nếu H1 thiếu hoặc không chứa mọi
  observed M1 OHLC trong giờ thì stop inconclusive; không padding.
- BUY có thể SL nếu H1 low<=SL: thêm exit-price interval [H1low,SL]; TP nếu
  H1 high>=TP: thêm [TP,H1high]. SELL đảo hướng: SL [SL,H1high], TP [H1low,TP].
  Đây là superset của các quote fills giả định; không khẳng định xảy ra.
- Giữ cả nhánh chưa thoát sau phút thiếu. Khi nhánh đó gặp exit đã biết thì
  đóng tập khả năng; nếu phút scheduled exit thiếu hoặc hết phiên còn chưa
  xác định terminal thì inconclusive. Không giả vờ đã thực sự đóng tại broker.
- Mỗi trade lấy min/max exit costs sau parent rounding. Cộng interval cash;
  chỉ mở trade kế nếu margin/risk/cash eligibility giống nhau trên toàn
  interval. Entry bị thiếu không mở, crossed source bị chặn. Nếu eligibility
  khác giữa hai đầu biên thì inconclusive, không dùng fixed10k để né state.
- Hai đầu interval bằng nhau khi không có bất định phải khớp exact parent.
  Không tính prop DD hoặc calibrated pass probability từ outer bounds.

## Kiểm trước chạy và quyết định

Focused fixtures BUY/SELL, adverse gap, same-M1 dual hit, missing H1, envelope
inconsistency, missing scheduled exit, cash-dependent eligibility và exact
parent parity; Fraction arithmetic kiểm lại các trade bounds và full totals.
Control 2022 có 243 closed trades phải khớp từng trade parent v2 và cash
714,71/568,12USD nếu không có bất định mới. Giữ mọi failure/attempt.

Nếu upper-bound stress2019<=0: exact recipe không đáng ưu tiên thêm dù
giả định có lợi. Nếu lower>0 và đủ100trades mỗi stressyear: chỉ đủ cân nhắc
nghiên cứu tiếp dưới giả định này, chưa original gate pass/OOS/prop/forward.
Nếu khoảng cắt0: chưa kết luận economics. Không đổi risk/SL/TP/cost sau outcome.
Catalogue không tăng policy count vì đổi uncertainty model.

Output private `nasdaq-opening5-bounds-v1`: config/pins, books, progress/events,
timings, result/review; mỗi trade có interval/reason/uncertain-source locator.
120s deadline, CANCEL, một writer. Không broker/model calls, authority=false.

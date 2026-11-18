# Mở rộng kiểm nguồn cho toàn bộ khoảng thiếu Development

Sau [lượt hồi quy](PROP-REPLAY-REGRESSION-RESULTS-20261118.md), dùng cùng
nhà cung cấp và cùng quy tắc cho toàn bộ **43 khoảng đã biết / 25 lệnh**
Development từ `gap-ranking`. Không thêm gap theo dấu PnL. Bao gồm 36
khoảng EURUSD và 7 khoảng XAUUSD, thuộc 19 kho tháng EST. Dùng ba kho
EURUSD đã kiểm SHA, tải tối đa 16 kho còn lại qua mẫu công khai. Ba
tác vụ tải đồng thời, mỗi kho tối đa 32 MiB nén, giữ lỗi từng kho. Chỉ
giải mã giá trong khoảng cần so. Không có giá nào từ 2024–2026.

- Đếm tick theo khoảng và theo hai phút liền kề. Đối chiếu Bid
  Open/Close ở các phút chung để mô tả chênh lệch giữa hai nguồn. Đổi
  EST cố định UTC−5 đúng đặc tả. Cùng kết quả giữa hai nguồn chưa chứng
  minh độc lập, và khác giá không chứng minh nguồn nào sai.
- Chạy phép kiểm khác nguồn với mọi lệnh P0 có đủ entry/deadline trong
  60 giây và tối đa ba phút giữa các tick khi giữ. Giữ stop tuyệt đối,
  luồng giá riêng và số lot cũ. EURUSD giữ phí/lot như lượt 3 lệnh.
  XAUUSD dùng commission 0,0007% notional mỗi phía và trượt giá 0,20
  USD/oz mỗi phía. Dùng đúng dữ liệu và precision native, kể cả khi
  giá khác lưới của M1. Bộ V19 này đóng trong ngày, trước rollover.
- P1 chỉ đo tick chạm ngưỡng stop hoặc mức bảo vệ đang hoạt động theo
  ledger V19 tại phút thiếu. Không suy trigger P1 từ đường V19 sang
  HistData rồi gọi là replay cả lệnh. Các lệnh không đủ dữ liệu giữ
  nguyên trạng thái chưa biết.
- Để lượng hóa quy mô, thay số tiền của từng P0 đo được vào **bảng
  đối chiếu cố định $150 risk** và giữ các lệnh khác theo PRIMARY hoặc
  STRICT. Đây là phép cộng tĩnh theo lệnh, không thay feed hoặc sổ
  V19, không dùng để tính pass Challenge, equity DD hoặc payout.
- Đồng thời rà hồ sơ V13/V16/V26 và hai ca đối chứng F4/VIX trước khi
  chọn việc tiếp. Nếu không có nhánh đạt cổng, giữ nguyên verdict và
  chỉ ra việc nào còn đủ khả năng đổi quyết định.

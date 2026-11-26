# EURUSD sau đấu giá Treasury — công thức Stage‑0 khóa trước đo

Mã `EUR-UST-AUCTION-BTC`. Một công thức trên Development 2018–2023.
Dùng sức cầu tại đấu giá trái phiếu Mỹ làm tín hiệu. Phép đo khác giờ
fixing, FOMC, giá dầu, phần lệch với rổ FX và nhánh DGS2 dùng biến động
lợi suất 2 năm. Cơ chế là nhu cầu Treasury của các nhóm nhà đầu tư kéo theo
điều chỉnh vị thế phòng hộ tiền tệ và tồn kho dealer. Nghiên cứu gốc thấy
cầu trái phiếu cao hơn đi cùng ngoại tệ mạnh hơn trong cửa sổ đấu giá.
Ta kiểm phần di chuyển còn lại sau khi kết quả đã công khai và luồng điều
chỉnh vị thế có thể tiếp diễn. Hướng theo bid-to-cover và độ trễ ở đây chỉ
là giả thuyết có thể bác bỏ, vì phần chính của nghiên cứu đo quanh công bố.
[Bank of Canada, mục 3.1 và 6](https://publications.gc.ca/collections/collection_2025/banque-bank-canada/FB3-5-2025-29-eng.pdf)

- Dùng Fiscal Data `auctions_query`, thông tin chính thức của nominal
  fixed-rate 2, 3, 5, 7, 10, 20, 30 năm theo `original_security_term`.
  Có thể dùng 2017 để hình thành lịch sử BTC, chỉ đọc giá từ 2018.
  Nếu có nhiều kỳ đủ loại cùng ngày, chọn kỳ dài nhất đã định danh.
  Nếu trùng cùng kỳ dài nhất thì bỏ ngày. Kỳ có BTC hoặc giờ đóng
  thiếu được ghi riêng. Giờ đóng competitive lấy theo lịch đã công bố.
  Kết quả được đọc tại competitive close +15 phút theo New York.
  Công bố nguồn chuẩn khoảng hai phút sau đóng, buffer 15 phút xử lý
  độ trễ thường gặp. Kỳ nào có bằng chứng công bố muộn hơn thì thiếu nguồn,
  không dùng tín hiệu cho ngày đó. [Treasury Fiscal Data](https://fiscaldata.treasury.gov/datasets/treasury-securities-auctions-data/) ·
  [TreasuryDirect, lịch sử công bố](https://www.savingsbond.gov/research-center/timeline/auctions/)
- So bid-to-cover công bố với trung vị bốn kỳ nominal trước cùng tenor.
  Phải đủ bốn kỳ và chúng đều diễn ra trước ngày hiện tại. Cao hơn thì BUY
  EURUSD, thấp hơn thì SELL. Bằng nhau đứng ngoài. Dùng cả các kỳ đã được
  chọn hoặc không chọn làm cơ hội để xây lịch sử so sánh.
- Đo M1 open đúng phút competitive close +15 và 16:30 New York trong ngày.
  Dùng V14 EURUSD Development đã seal, Bid lấy từ nguồn M1 và Ask proxy
  +1,0 pip như nhánh EURUSD trước. Stop tự nhiên nằm ngoài Bid Low
  hai giờ trước entry cho BUY, hoặc Ask High hai giờ cho SELL, đệm 0,1 pip.
  Phải có đủ 120 phút để tính stop. Không kích hoạt stop ở Stage‑0.
  Spread đã nằm trong giá, commission 0,7 pip/vòng và trượt 0,2 pip/vòng.
  Tổng ma sát 1,9 pip/vòng theo kịch bản stress. Swap 0 với lệnh trong phiên.
- Dừng nếu bất kỳ năm nào dưới 40 tín hiệu, dưới 99% có đủ giá hai đầu,
  median friction / median stop trên 12%, giữ dưới 50% qua cap hoặc
  markout ròng trung bình dưới 1,9 pip. Chỉ replay cùng vốn và risk với
  BASE_GUARD nếu qua đủ. Báo cả ngày thiếu, không thay ngưỡng/giờ/chiều
  sau đo, giữ đóng giá 2024–2026.

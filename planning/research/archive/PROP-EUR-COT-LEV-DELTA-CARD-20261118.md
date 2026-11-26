# EURUSD theo thay đổi vị thế hợp đồng EUR công bố hằng tuần

`EUR-COT-LEV-DELTA` là phép thử dự phòng sau khi
[US500 ETF](PROP-US500-LETF-AUM-CARD-20261118.md) hụt cổng đối chứng.
Một công thức duy nhất, Development 2018–2023. Câu hỏi là liệu thay đổi
vị thế EUR của nhóm dùng đòn bẩy có tiếp tục sau khi số liệu đã công bố,
do lệnh của tổ chức được chia nhỏ qua nhiều phiên và hedge liên thị trường.
Dữ liệu tuần mô tả vị thế tổng hợp và có độ trễ. Nghiên cứu RBNZ tìm thấy
đồng biến trong cùng kỳ rõ hơn tác dụng dự báo. Vì vậy đây là giả thuyết
cần kiểm và có thể bị bác, khác những luật lấy giá dầu, giá FX, lợi suất
hoặc đấu giá Treasury để chọn chiều.
[RBNZ AN2018/03](https://www.rbnz.govt.nz/research-and-publications/research/our-research-and-analysis/analytical-notes/2018/an2018-03)

- Nguồn CFTC TFF Futures Only, hợp đồng CME EURO FX mã 099741, ZIP
  từng năm 2018–2023. Một báo cáo mỗi tuần ISO. So net vị thế
  `Lev_Money_Positions_Long_All − Lev_Money_Positions_Short_All` của
  hai tuần liên tiếp. BUY EURUSD khi tăng, SELL khi giảm. Bằng nhau
  đứng ngoài. Không qua tuần thiếu và không lấy dữ liệu năm 2017.
  [ZIP CFTC](https://www.cftc.gov/MarketReports/CommitmentsofTraders/HistoricalCompressed/index.htm)
- Dùng báo cáo khoảng một tuần trước và đo từ 10:30 đến 16:30 New York
  vào **thứ Tư của tuần tiếp theo**. Cho đủ thời gian kể cả lịch công bố
  bị lùi một hoặc hai ngày làm việc từ thứ Sáu. Bỏ tuần báo cáo từ thứ Hai
  24/12/2018 tới hết tuần bắt đầu 04/03/2019, và từ 30/01/2023 tới hết
  tuần bắt đầu 20/03/2023, do các đợt công bố trễ đã biết. Khoảng bỏ
  áp cho tuần tạo tín hiệu, tuần so sánh trước có thể dùng sau khi khôi
  phục. Chỉ dùng ngày có phiên NYSE đầy đủ theo lịch repo, bỏ ngày chứ
  không dời lệnh. Archive cuối kỳ là proxy số đã công bố, chưa có timestamp
  hay phiên bản đầu cho mỗi báo cáo.
  [Lịch CFTC](https://www.cftc.gov/MarketReports/CommitmentsofTraders/ReleaseSchedule/index.htm) ·
  [Shutdown 2018–2019](https://www.cftc.gov/PressRoom/PressReleases/7864-19) ·
  [Các kỳ trễ 2023](https://www.cftc.gov/MarketReports/CommitmentsofTraders/HistoricalSpecialAnnouncements/index.htm)
- Đo đúng M1 Open tại hai mốc bằng Bid và Ask proxy +1 pip của gói
  EURUSD V14. Stop ngoài Bid Low hai giờ trước entry với BUY hoặc Ask
  High với SELL, thêm 0,1 pip. Cần đủ 120 phút cho stop. Chỉ đo distance,
  chưa chạy SL. Ma sát stress tổng 1,9 pip/vòng gồm spread proxy, 0,7
  pip commission và 0,2 pip slippage. Thoát trước rollover.
- Từng năm ≥40 tín hiệu, ≥99% có giá hai đầu, median ma sát / median
  stop ≤12%, giữ ≥50% qua cap 12% và mean net ≥1,9 pip. Chỉ replay
  cùng vốn và risk nếu qua đủ. Không sửa công thức theo outcome và giữ
  đóng giá 2024–2026.

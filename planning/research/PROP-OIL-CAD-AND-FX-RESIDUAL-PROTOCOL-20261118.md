# Hai đầu mối từ tài liệu gốc — dầu/CAD và hồi quy phần lệch FX

Một lượt trên Development 2018–2023, thứ tự cố định bên dưới, tối đa một
công thức mỗi cơ chế. Giữ quyết định của các công thức đã gác.
[Quyết định sau DGS2](PROP-POST-DGS2-REOPEN-DECISION-20261118.md)

1. **Dầu dẫn USD/CAD.** Ferraro–Rogoff–Rossi tách liên hệ đồng thời
   và dự báo ngày từ dầu đã quan sát. Tín hiệu có độ trễ thay đổi
   theo thời đoạn. Hướng cần thẩm định là dầu tăng thì USD/CAD giảm
   tiếp sau khi có thể khớp. Cửa nguồn yêu cầu giá dầu có thời gian
   xuất hiện, hợp đồng hoặc chuỗi roll định danh, và USD/CAD Bid/Ask
   đủ kỳ để đo stop lẫn giá thoát. Spot WTI theo ngày không xác minh
   được known-at chỉ từ nhãn ngày quan sát. Phí USD/CAD phải báo
   spread riêng, chuyển commission USD về CAD tại tỷ giá áp dụng nếu
   tính theo pip, rồi cộng stress slippage. Một lot 100.000 USD có
   trị giá 10 CAD/pip, nên phí USD không đổi thẳng sang pip của
   EURUSD. Hồ sơ WTI chỉ admit các phiên mẫu, thiếu cặp giá đủ kỳ
   tại chỗ. Dừng ở `SOURCE_BLOCKED`, 0 công thức chạy trên CAD và
   0 PnL. WoW/tuần hay giảm tần suất từ kết quả dầu không nằm trong
   lượt này. [Ferraro–Rogoff–Rossi](https://www.bankofcanada.ca/wp-content/uploads/2012/02/workshop-exchange-rates-june2011-Ferraro-Rogoff-Rossi.pdf) ·
   [Bank of Canada](https://www.bankofcanada.ca/2016/03/staff-analytical-note-2016-2/) ·
   [EIA](https://www.eia.gov/petroleum/prices/) ·
   [Hồ sơ WTI](WTI-SESSION-SOURCE-RESULTS-20261109.md)
2. **EURUSD hồi quy phần lệch với rổ FX.** Avellaneda–Lee nghiên cứu
   phần biến động riêng và hồi quy trung bình trong cổ phiếu. Đây là
   phép chuyển ý tưởng sang FX bằng rổ cố định, chưa giả định residual
   thật hay lợi thế đã chứng minh. Liên quan họ R034 đã dừng trước
   PnL. N1-EUR-PEERS hỏi EURUSD có đi tiếp theo hai cặp khác khi cả
   hai đã đi cùng chiều hay không. Công thức này hỏi biến động riêng
   của EURUSD có đảo ngược hay không, không cần hai cặp cùng chiều,
   không có fit beta và chỉ đo một lệnh một chân.
   [Avellaneda–Lee](https://math.nyu.edu/~avellane/AvellanedaLeeStatArb20090616.pdf) ·
   [R034](RESIDUAL-REVERSION-METHOD-ADMISSION-20261109.md) ·
   [Nhịp 1](PROP-N1-RESULTS-20261118.md)

## Công thức duy nhất được đo

- Mọi ngày thứ Hai–thứ Sáu 2018–2023 ngoài ngày đóng theo lịch đã
  dùng ở Nhịp 1. Chốt lúc **14:00 UTC**, sau đúng hai giờ 12:00–14:00
  của ba cặp. EURUSD dùng V14 M1 Bid và Ask proxy đã seal, GBPUSD và
  AUDUSD dùng V11 H1 paired và chỉ giữ file Development. Yêu cầu
  đúng 120 phút EURUSD và đủ cả hai giờ của mỗi cặp phụ, không ghép
  cửa sổ đến từ các giờ không liên tục.
- Tính mỗi thay đổi theo Bid Open của đầu 12:00 và Bid Close của
  bar cuối trước 14:00, chia Bid Open. Phần lệch bằng thay đổi EURUSD
  trừ bình quân đều hai cặp phụ. Phần lệch ≥10 bp thì SELL EURUSD,
  ≤−10 bp thì BUY; nếu không thì đứng ngoài. Ngưỡng tròn 10 bp là
  mức di chuyển tương đối khoảng 10–12 pip của EURUSD trong vùng giá
  lịch sử, dùng để đòi lệch thấy được trước phí, không là giả định
  về mức hồi quy. Một hướng, một quyết định/ngày.
- Entry và exit đúng M1 Open 14:00/18:00 UTC, giữ **4 giờ**. Đây là
  cửa sổ giả thuyết sau khi rổ đã hình thành, trước rollover. Nếu lịch
  đã biết buộc flat trước 18:00 thì bỏ ngày trước khi chọn tín hiệu.
  Stop đo ngoài biên Bid Low hai giờ với BUY, ngoài Ask High với SELL
  một tick lưới (0,1 pip). Vị trí cực trị là mốc cấu trúc bác ý tưởng
  bật lại sau phần lệch. Chỉ đo hình học, không kích hoạt stop ở Stage‑0.
- Spread proxy 1 pip đã nằm trong Ask/Bid. Commission stress 0,7
  pip/vòng và slippage 0,2 pip/vòng. Đo net trên tín hiệu thô đủ
  giá và báo thêm nhóm qua cap 12%. Giữ riêng thiếu dữ liệu tạo tín
  hiệu, thiếu endpoint, stop không hợp lệ, rớt phí và qua phí. Báo
  chênh lệch theo từng năm, độ phủ và bootstrap tuần nếu đủ mẫu.
- Giữ các cổng hiện hành: ≥40 tín hiệu thô/năm, ≥99% điểm định giá
  trên tín hiệu, mean net dương và ≥1,9 pip, median phí/median SL
  ≤12% và ≥50% tín hiệu qua cap. Dùng cùng ngân sách rủi ro với
  BASE_GUARD, cùng mốc và cả hai kịch bản chỉ khi qua đủ cổng.
  Dữ liệu giá 2024–2026 đóng. Không thay ngưỡng, hướng, giờ hoặc
  tạo cơ chế thứ ba sau outcome.

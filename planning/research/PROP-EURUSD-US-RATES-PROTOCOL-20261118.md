# EURUSD phiên Mỹ — tiếp diễn sau thay đổi lợi suất Mỹ hai năm

**Một công thức duy nhất trên Development 2018–2023.** Chọn EURUSD theo
[phép đo biên độ phiên Mỹ](PROP-SESSION-FEASIBILITY-RESULTS-20261118.md).
Giả thuyết là thị trường FX còn định giá lại đồng USD khi lợi suất Mỹ
hai năm đã dịch chuyển đủ rõ trước phiên. Đây là proxy một phía cho
định giá lãi suất, còn kỳ vọng lãi suất châu Âu và các yếu tố khác cũng
có thể chi phối EURUSD. Khác F5 quét biên, B0 phá vùng London và N1
đuổi theo cặp FX cùng chiều, luật này lấy hướng từ thị trường trái
phiếu. [Fed về tỷ giá và chính sách](https://www.federalreserve.gov/faqs/economy_12763.htm) ·
[Chuỗi DGS2](https://fred.stlouisfed.org/series/DGS2)

- Dùng lịch NYSE 2018–2023 đã khóa, chỉ phiên 390 phút. Tại 10:30 New
  York, dùng hai quan sát DGS2 có giá trị mới nhất mang ngày **trước**
  ngày giao dịch; cả hai cách ngày giao dịch tối đa bảy ngày lịch. Hai
  quan sát là các mức đã công bố qua phiên trước theo quy ước H.15
  16:15 giờ Mỹ. Bỏ qua ô ngày nghỉ. CSV FRED lấy trong 01/01/2018–
  31/12/2023, không dùng lợi suất trong ngày. Giới hạn là chuỗi tải
  hiện tại, chưa tái lập vintage tại mỗi ngày. [Lịch công bố H.15](https://www.federalreserve.gov/feeds/H15.html)
- Chênh lệch hai mức ≥ +2 bp thì SELL EURUSD, ≤ −2 bp thì BUY, phần
  còn lại đứng ngoài. Một ngày có một quyết định. 2 bp chọn trước kết
  quả để tránh tín hiệu trên một bước làm tròn 1 bp. Không có grid.
- V14 EURUSD M1 Development có SHA và Ask proxy 1 pip. Entry đúng
  M1 Open 10:30 New York và giá đo sau 4 giờ đúng M1 Open 14:30.
  BUY Ask→Bid, SELL Bid→Ask, không đi qua rollover. Stop tự nhiên
  dưới đáy Bid hoặc trên đỉnh Ask của 60 phút 09:30–10:29 một bước
  giá 0,1 pip. Thiếu giờ đầu vẫn giữ tín hiệu thô và endpoint nếu có.
  Thiếu endpoint giữ riêng; không lấp giá, không mô phỏng SL/PnL tài
  khoản ở Stage‑0.
- Phí stress theo V26: spread 1 pip đã nằm trong Bid/Ask, commission
  0,7 pip/vòng và slippage 0,2 pip/vòng. Tổng ma sát dùng cho cổng
  là 1,9 pip trong nguồn này. Đo kinh tế trên mọi tín hiệu có giá,
  và báo riêng nhóm qua phí theo đúng chiều luật đã chọn. Chỉ dùng
  giá sau entry cho phép đo markout, không dùng để chọn hướng hoặc stop.
- Từng năm: tối thiểu 40 tín hiệu thô, ≥99% có endpoint; net stress
  trung bình dương và ≥ ma sát trung bình; median phí / median
  stop ≤12%; ít nhất 50% tín hiệu thô qua cap 12%. Báo ngày thiếu
  nguồn lợi suất, đứng ngoài, thiếu geometry, thiếu endpoint, rớt
  chi phí và qua phí. Equity hoặc walk-forward chỉ xét nếu công thức
  qua cổng này. Hai ca đối chứng giữ nguyên theo hồ sơ F4 và US500–VIX.
- Dữ liệu giá 2024–2026 đóng. Nghiên cứu offline, rủi ro tài khoản
  và luật BASE_GUARD giữ nguyên.

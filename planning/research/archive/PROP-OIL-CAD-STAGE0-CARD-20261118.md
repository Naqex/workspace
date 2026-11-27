# WTI → USD/CAD — khóa luật và sàng lọc nguồn Development

Ứng viên duy nhất `OIL-CAD-1PCT`, tiếp nối
[protocol](PROP-OIL-CAD-AND-FX-RESIDUAL-PROTOCOL-20261118.md).
Khóa trước phép đếm và PnL. Chỉ dùng 2018–2023. Giả thuyết là cú di chuyển
dầu đủ lớn trong một đoạn thanh khoản của phiên Mỹ có thể tiếp tục tác động
lên CAD ở phiên kế. Cửa sổ ngày kế kiểm độ trễ. Đây là biến thể riêng của
[ý tưởng dầu trễ](https://www.bankofcanada.ca/wp-content/uploads/2012/02/workshop-exchange-rates-june2011-Ferraro-Rogoff-Rossi.pdf).

- Ngày tín hiệu là thứ Hai đến thứ Sáu theo UTC. Dùng Bid Open nến WTI H1
  14:00 và Bid Close nến 15:00 Dukascopy LIGHT.CMD/USD. Cần đúng hai nến
  nguồn. Cả hai giá phải dương. Return bằng Close / Open − 1. Dầu tăng ít
  nhất 1,00% thì SELL USD/CAD, dầu giảm ít nhất 1,00% thì BUY. Mức tròn 1%
  được chọn để chỉ kiểm cú dịch chuyển có độ lớn đáng kể trong hai giờ.
  Tín hiệu chỉ hình thành từ 16:00 UTC. Hai nến nằm trong cùng phiên,
  trước giờ nghỉ đổi hợp đồng theo tài liệu nguồn. Không nối return qua roll.
  [Lịch điều chỉnh CFD](https://www.dukascopy.com/swiss/cz/marketwatch/calendars/cfd-price-adjustment-calendar/)
- Vào đúng ngày thứ Hai–thứ Sáu kế tiếp, tối đa một tín hiệu/ngày. Loại
  ngày không có phiên hợp lệ theo lịch đã công bố và không dời tín hiệu
  qua thêm ngày. Chỉ tính nếu ngày tín hiệu và ngày giao dịch đều nằm trong
  Development. Dùng ngày vào lệnh để nhóm theo năm. Kiểm thử đầu tiên chỉ
  đếm **cận trên số tín hiệu có thể khớp**, trước khi trừ ngày nghỉ và
  ngày thiếu giá USD/CAD. Mọi ngày thiếu nến dầu được cộng vào cận trên
  bảo thủ như thể đều có tín hiệu. Nếu cận trên của một năm dưới 40 thì
  dừng ngay, vì lọc nguồn/phí chỉ có thể giảm số cơ hội.
- Nếu qua phép đếm, đòi đủ hai phía M1 USD/CAD 14:00–16:00 trong ngày vào,
  xác minh dữ liệu intraday bằng tick cùng nguồn Dukascopy. Entry ở tick
  đầu trong phút 16:01 UTC, exit ở tick đầu trong phút 20:00 UTC. BUY dùng
  Ask vào / Bid ra, SELL dùng Bid vào / Ask ra. Markout không kích hoạt
  stop. Stop tự nhiên là Bid Low của cửa sổ trước entry trừ 0,1 pip cho BUY,
  hoặc Ask High cộng 0,1 pip cho SELL. Ghi thiếu dữ liệu riêng và kiêng
  ghép timestamp hoặc nến từ nguồn khác để lấp.
- Commission proxy 2,50 USD/lot/side, quy đổi CAD theo mid ở mỗi đầu khớp
  rồi chia 10 CAD/pip/lot. Spread nằm trong Bid/Ask. Trượt stress 0,10
  pip/side. Dùng tổng nửa spread tại hai đầu giá cộng commission và slippage
  để đo ma sát vòng lệnh, không trừ spread lần nữa. Đóng trong ngày UTC,
  trước 17:00 New York, swap bằng 0 cho lịch giữ này. Báo rõ phí proxy.
  [FTMO Free Trial, công bố 11/09/2025](https://ftmo.com/en/blog/trading-updates/trading-update-11-sep-2025/)
- Giữ các cổng từng năm ≥40 tín hiệu, ≥99% endpoint, median ma sát stress /
  median stop ≤12%, giữ ≥50% qua cap 12%, mean markout ròng dương và ít
  nhất bằng ma sát stress đại diện của năm (trung vị). Chỉ đối chiếu vòng đời
  cùng vốn/risk với BASE_GUARD nếu qua đủ. Không đổi hướng, ngưỡng, window
  hoặc chi phí sau đo. Không mở giá 2024–2026.

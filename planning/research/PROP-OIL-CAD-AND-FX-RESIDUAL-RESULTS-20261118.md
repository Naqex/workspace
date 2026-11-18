# Dầu/CAD và hồi quy phần lệch FX — kết quả sàng lọc

**Hai đầu mối, một công thức đã đo, chưa có ứng viên để replay.** Dầu/CAD
vướng nguồn. Luật hồi quy phần lệch EURUSD trượt Stage‑0. Giữ BASE_GUARD
làm đối chứng ở `NOT_QUALIFIED` và tiếp tục mục tiêu tìm lợi thế mới.
[Protocol khóa trước đo tại `2ad08ea`](PROP-OIL-CAD-AND-FX-RESIDUAL-PROTOCOL-20261118.md)

## 1. Dầu dẫn USD/CAD — `SOURCE_BLOCKED`

Ferraro–Rogoff–Rossi phân biệt tương quan đồng thời và dầu trễ một ngày.
Kết quả dự báo với dầu trễ phụ thuộc khoảng ước lượng và thay đổi theo
thời đoạn. Bank of Canada thấy biến động hàng hóa hữu ích để giải thích
biến động CAD cùng kỳ, còn yếu tố USD chung có sức dự báo mạnh hơn.
Bằng chứng này hỗ trợ kiểm một giả thuyết ở chân trời ngày, với mốc giá
dầu đã biết và giá FX sau mốc đó. Không đủ căn cứ chuyển thẳng xuống M15.
[Ferraro–Rogoff–Rossi](https://www.bankofcanada.ca/wp-content/uploads/2012/02/workshop-exchange-rates-june2011-Ferraro-Rogoff-Rossi.pdf) ·
[Bank of Canada](https://www.bankofcanada.ca/2016/03/staff-analytical-note-2016-2/)

- **WTI.** Pilot `LIGHT.CMD/USD` là báo giá CFD, khác spot Cushing và
  settlement hợp đồng CME. Pilot cũ có 1.614/1.656 mốc Bid/Ask trong sáu
  phiên và cả ba phiên 2019 hụt sàn phủ 98%. Hồ sơ chỉ đủ để biết nguồn
  mẫu, chưa có hai chuỗi đồng bộ 2018–2023. Chuỗi spot EIA gắn ngày
  quan sát. Muốn dùng làm feature cần xác định thời điểm giá từng ngày
  được công bố hoặc dùng nguồn quote có timestamp riêng. Muốn dùng
  futures cần định danh hợp đồng và nối giá không tạo cú nhảy giả khi
  roll. [Pilot WTI](WTI-SESSION-SOURCE-RESULTS-20261109.md) ·
  [Lịch Petroleum Daily](https://www.eia.gov/petroleum/prices/)
- **USD/CAD.** Chưa có nguồn Bid/Ask đủ kỳ đã đối soát trong kho
  hiện tại. Xác nhận thông số phí theo cặp còn thiếu. Một lot 100.000
  USD có 10 CAD/pip; nếu commission ghi USD/lot thì đổi sang CAD
  ở tỷ giá ứng với lần tính phí để so bằng pip. Chi phí trên bảng
  symbol công khai không xác minh được spread/slippage lịch sử.
  Chưa gán số phí 1,9 pip của EURUSD sang USD/CAD.
  [Bảng symbol FTMO](https://ftmo.com/en/symbols/)

Không đo PnL của dầu/CAD. Có thể mở lại khi có nguồn WTI biết được
thời điểm xuất hiện, USD/CAD Bid/Ask phủ kỳ và mô hình phí có đơn
vị, nguồn và mua/bán rõ ràng. Khi đó khóa rule ngày trước khi đếm
hoặc đọc lợi nhuận. Các yêu cầu này không đòi mua dữ liệu trong lượt này.

## 2. EURUSD hồi quy phần lệch FX — `ECONOMIC_FAIL`

So thay đổi EURUSD với bình quân GBPUSD và AUDUSD từ 12:00 tới 14:00
UTC. Nếu EURUSD mạnh hơn rổ ít nhất 10 bp thì SELL, yếu hơn ít nhất
10 bp thì BUY. Giữ đúng 4 giờ. Stop tự nhiên tham chiếu cực trị hai
giờ trước entry. Ma sát stress 1,9 pip gồm Ask proxy cố định, commission
và slippage. Lợi nhuận đo dưới đây là markout đến 18:00, chưa chạy SL.

| Năm | Phiên | Raw BUY / SELL | Rớt phí | Qua phí | SL trung vị (pip) | Net TB sau phí (pip) | Net TB nhóm qua phí (pip) |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2018 | 248 | 44 / 46 | 60 | 30 (33,3%) | 11,00 | −3,00 | −0,93 |
| 2019 | 248 | 45 / 46 | 69 | 22 (24,2%) | 8,10 | +1,46 | +1,51 |
| 2020 | 250 | 61 / 64 | 72 | 53 (42,4%) | 13,60 | +1,01 | −1,59 |
| 2021 | 248 | 49 / 51 | 68 | 32 (32,0%) | 12,55 | +1,01 | +1,30 |
| 2022 | 250 | 67 / 77 | 66 | 78 (54,2%) | 17,35 | −2,64 | −3,66 |
| 2023 | 249 | 59 / 51 | 54 | 56 (50,9%) | 16,40 | +0,52 | +4,45 |

Trong 1.493 phiên có lịch đủ thời gian, 832 phiên không đủ lệch và một
phiên thiếu dữ liệu tạo tín hiệu. **660/660 tín hiệu có giá và stop**.
Nhóm qua phí có 271/660 (41,1%). Chỉ 2022–2023 đạt cả hai tiêu chí về
quy mô stop và tỷ lệ giữ mẫu, nhưng 2022 âm ngay trong nhóm qua phí.
Tất cả sáu năm hụt markout 1,9 pip. Trung bình gộp là **−0,35 pip**;
khoảng bootstrap theo tuần của từng năm đều chứa 0.

**Quyết định.** Gác đúng công thức EURUSD này. Chưa có kịch bản ghép
cùng risk để báo thêm số vòng 1, vòng 2 hay drawdown. Ưu tiên kế tiếp
là câu hỏi về nguồn dầu–CAD có mốc known-at kiểm được và đủ bộ giá
thay vì thêm biến thể vào luật EURUSD vừa loại. Giữ nguyên các kết
luận cũ, ngân sách risk và khóa giá 2024–2026.

## Kiểm chứng

30 test hiện có, sáu kiểm tra fixture và đối soát bằng số hữu tỷ
toàn bộ dấu/điểm cắt, stop, giá vào/ra, phí và số đếm của 660 tín hiệu.
Bộ đọc M1/H1 kiểm hash nguồn và chỉ cấp năm Development. Artifact tại
`execution-v1/prop-fx-residual-stage0-20261118/749687b9be70/`.
SHA256 `stage0-results.json`
`6834360be5dee0ebaaa1279b1a3791b36a6c8722cf00da72c02e836fdaeb8929`.
SHA256 `residual-session-rows-manifest.json`
`2c9ae8fe248a403bb228a1edfd88f93fc2ceb86c8d058d6edde010b2c2c9fcd8`.

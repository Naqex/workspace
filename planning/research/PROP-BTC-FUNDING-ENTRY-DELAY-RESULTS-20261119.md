# BTCUSD funding nhóm thấp · vào sau 2 phút so với sau 60 phút

**Đóng nhánh BTCUSD BUY sau funding nhóm thấp.** Trong 2021–2023,
vào sớm nâng markout thô sau phí stress từ **+50,83 lên +62,05 bp**
trên 197 tín hiệu ghép được. Sổ mô phỏng với sizing và các cổng
đã khóa lỗ **1.217,13 USD**, so với **171,97 USD** ở bản gốc.
Cả hai nhận 48 lệnh. Chênh lệch đến chủ yếu từ việc thay tám lệnh
cũ bằng tám lệnh khác khi geometry, ma sát và lịch chiếm vị thế
thay đổi theo giá vào. Không có năm đầy đủ nào đạt 1.000 USD.

## Một thay đổi đồng hồ

| Bản | Vào | Thoát |
| --- | --- | --- |
| A · parent dcdf9bf | Bitstamp BTC/USD H1 Open ở settlement +60 phút | Sau khi vào đúng 24h |
| B · phép thử khóa trước | Bitstamp BTC/USD M1 Open ở settlement +2 phút | Sau khi vào đúng 24h |

Giữ đủ 248 tín hiệu đã đăng ký, cùng rank funding, lịch thứ Hai
đến thứ Năm UTC, một vị thế, đáy ngày trước trừ 0,01 USD, cap
ma sát 12%, sizing gồm dự phòng phí ở mức 150 USD, bước lot 0,01,
ký quỹ 1:1 và các mức chi phí. Natural stop vẫn chỉ dùng để lọc và
sizing trong phép đo đến giờ thoát. Commission 0,0325% mỗi chiều,
stress thêm 15 bp spread+trượt và 15 bp phí giữ phiên trên giá vào.
Hai phí này là giả định CFD. Giá Open lấy từ sàn spot.

Dùng 423 mốc M1 khác nhau cho B và 14 mốc đúng giờ H1 lấy trước
ở mỗi quý có tín hiệu để đối chiếu A. Cả 14 Open của M1 khớp H1.
Mỗi request chỉ một nến, có start/end trong đúng phút, xác minh
timestamp, market và SHA256. 422/423 mốc B có nến volume dương.
Mốc **06/09/2023 08:02 UTC** trả nến volume 0, ghi giá vào B chưa
biết. Sự kiện còn trong mẫu số, bản A bị cap loại ở ngày này.
247/248 tín hiệu có đủ cả hai đầu để so sánh A/B.

Mốc +2 nằm sau timestamp settlement ghi nhận của tất cả tín hiệu.
Lịch sử chỉ cho biết thời điểm settlement, chưa cho biết lúc Binance
đăng rate hoặc dữ liệu đến máy vận hành. Phép đo B giả định rate đã
tới trước Open +2 và chưa có bằng chứng khớp tại giá đó trên CFD.
Chỉ dùng giá đến hết 2023.
[Quy tắc và dữ liệu parent](PROP-BTC-FUNDING-LOW-TAIL-RESULTS-20261119.md) ·
[Bitstamp OHLC API](https://www.bitstamp.net/api/).

## Vào sớm cải thiện phần nào của chuyển động giá?

Trên mỗi cặp, chênh gộp B − A bằng **giá vào A trừ giá vào B**
cộng **giá ra B trừ giá ra A**. Dùng log-ratio từng chân để
cộng chính xác theo đơn vị bp trước phí. Cột raw stress dùng lợi suất
đơn giản sau phí, cùng sự kiện có giá. Các cửa 24h thô còn chồng nhau.

| Kỳ | Tín hiệu ghép | Giá vào sớm, log bp | Giá ra sớm, log bp | Raw stress A → B, bp |
| --- | ---: | ---: | ---: | ---: |
| 2020 từ 08/03 | 50 | +5,10 | −10,24 | +279,66 → +271,77 |
| 2021 | 46 | +16,29 | +13,93 | +37,43 → +68,20 |
| 2022 | 99 | +7,99 | −3,20 | +75,03 → +79,82 |
| 2023 | 52 | +6,40 | −0,06 | +16,62 → +22,79 |
| **2021–2023** | **197** | **+9,51** | **+1,63** | **+50,83 → +62,05** |

Trong ba năm đầy đủ, giá vào sớm giúp **30,30 USD/BTC** và dời
giờ ra giúp **7,41 USD/BTC**, tính trung bình gộp trên 197 cặp.
Hiệu ứng giá dương trên mẫu thô. Kết quả 2023 của B vẫn dưới cổng
raw yêu cầu bù **36,52 bp** phí stress, và chỉ có 52/53 cặp có giá.

## Sổ sau cổng vẫn xấu hơn

| Năm | Raw A/B có giá / mẫu | B bị stop geometry / cap / overlap / mất giá | Số lệnh có giá A / B | Net reference A → B, USD | Net stress A → B, USD |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2020 từ 08/03 | 50/50 và 50/50 | 6 / 16 / 10 / 0 | 17 / 18 | +1.291,26 → +1.332,69 | +1.209,70 → +1.239,11 |
| 2021 | 46/46 và 46/46 | 10 / 12 / 11 / 0 | 14 / 13 | −96,90 → +34,88 | −147,51 → −16,00 |
| 2022 | 99/99 và 99/99 | 16 / 45 / 12 / 0 | 22 / 26 | +59,85 → −790,55 | −69,88 → −950,89 |
| 2023 | 53/53 và 52/53 | 2 / 41 / 0 / 1 | 12 / 9 | +128,25 → −191,14 | +45,42 → −250,24 |
| **2021–2023** | **198/198 và 197/198** | **28 / 98 / 23 / 1** | **48 / 48** | **+91,20 → −946,82** | **−171,97 → −1.217,13** |

A loại 29 / 96 / 25 / 0 lượt theo bốn lý do trên ở 2021–2023.
B giữ 71/198 qua geometry, phí và lot trước giới hạn overlap, so với
73/198 của A. Hai sổ đều có 16 lệnh/năm. Stress B **−405,71 USD/năm**,
A **−57,32 USD/năm**. B đã âm **724,04 USD trước phí** trên 48 lệnh
nhận, rồi trừ 87,62 USD commission, 202,73 USD spread+trượt, và
202,73 USD phí giữ qua đêm. Cả ba năm B hụt cổng tiền. Giữ riêng 2020
là kỳ từ tháng 3.

| Phân rã B − A, stress 2021–2023 | USD |
| --- | ---: |
| Đổi giá trên 40 lệnh chung, giữ lot của A | +134,85 |
| Đổi lot trên 23/40 lệnh chung | +68,82 |
| Tám lệnh chỉ có ở B | −640,50 |
| Bỏ tám lệnh chỉ có ở A | −608,32 |
| **Chênh cả sổ** | **−1.045,16** |

Nếu chỉ dời giờ trên 48 lệnh cũ và ép giữ lot của A, kết quả tăng
336,58 USD thành +164,62 USD cho cả ba năm. Đây là phép quy thuộc
giá, vì có lệnh cũ không còn đủ điều kiện vào khi chạy đúng luật B.

Top 3 đợt B bắt đầu 23/03/2020 00:00, 27/02/2022 16:00 và
03/11/2020 16:00 UTC, đóng góp lần lượt **509,44 / 498,68 / 310,52 USD**.
Bỏ ba đợt này khỏi cả hai sổ, tổng 2020 partial + 2021–2023 của **B**
từ +21,98 xuống **−1.296,66 USD**, còn **A** từ +1.037,74 xuống
**−199,00 USD**. Bỏ ba đợt tốt nhất của riêng A thì A còn −259,72 USD.
Trong 2021–2023 sau khi bỏ ba đợt B, A còn −676,31 và B −1.715,81 USD.

**Dừng ở Stage-0.** Có bằng chứng rằng một phần phản ứng giá xuất
hiện trước giờ vào cũ. Chuyển mốc vào sớm theo luật đã khóa khiến sổ
nhận lỗ nặng hơn, vẫn ít lệnh và phụ thuộc vài đợt. Cổng raw 2023,
độ phủ 2023, tỷ lệ giữ ở 2022/2023 và tiền mô phỏng đều có phần
chưa đạt. Vì thế điều kiện lấy thêm giá đối chứng ngoài tail, kiểm
SL-active và mô phỏng tài khoản chưa mở. Mẫu Development đã phơi
nhiễm theo nghiên cứu gốc, BASE_GUARD giữ NOT_QUALIFIED.

Receipt ở ai-engine-jobs/prop-btc-funding-delay-20261119 trên ổ E.
Đã kiểm SHA256 và khớp lại A theo parent, rồi đối soát bằng Fraction
độc lập 248 cửa vào/ra, 247 phân rã giá, sizing, vị thế không
chồng và tổng tiền từng năm. Kết quả nén Zstandard giữ toàn bộ
lượt quan sát và giá không xác định.

# TSLA 2022H2 — lãi lỗ trên 42 lần phá biên đã khóa

**Gác pilot TSLA có lọc RVOL.** Kết quả trên cổ phiếu cơ sở sau commission
paper chạy từ **−269,28 tới +991,97 USD** trong sáu tháng, tùy thứ tự
High/Low trong nến vào lệnh. Toàn bộ chênh lệch tiền nằm ở **một lệnh SELL
16/12**. Kịch bản khớp SL bất lợi hơn âm **2.355,15 USD**. Bằng chứng
này chưa đủ ưu tiên mở thêm mẫu hay replay tài khoản 50.000 USD.
[Phép kiểm nguồn và capacity đã khóa tại de5e776](PROP-STOCKS-IN-PLAY-AND-GOLD-PM-RESULTS-20261118.md)

## Cùng 42 lệnh và cùng risk

Giữ TSLA 07–12/2022, giờ New York, toàn bộ side, giá vào proxy, giờ phá
biên và số cổ phần của 42 tín hiệu đã khóa. Sử dụng số liệu raw với
split 3:1 đúng ngày hiệu lực, 25/08. Cửa sổ mở phiên là 09:30–09:34.
Một mã, một lần vào/ngày, SL cách giá vào 0,1 ATR14 ngày, ngân sách
tối đa 150 USD. Risk sau làm tròn của 42 lệnh là **6.271,73 USD**,
bình quân 149,33 USD. Lệnh chưa chạm SL thoát tại M1 Open 15:59.

- Hai đường trong từng nến vào là Open → High → Low → Close và Open
  → Low → High → Close. SL chỉ hoạt động sau khi entry đã kích hoạt.
  Lấy kết quả thấp/cao của cả hai đường cho mỗi lệnh để tổng hợp hai
  kịch bản. Khi giá Open phút tiếp theo đã xuyên SL thì dùng Open
  đó. Có **0** trường hợp gap qua stop tại Open trước mốc thoát phiên
  trong 42 lệnh này. Khoảng trống nhỏ hơn một phút vẫn chưa quan sát được.
- Khi chỉ biết High/Low đã chạm SL, kịch bản giá liên tục lấy mức SL.
  Kịch bản khớp bất lợi lấy Low của phút chạm cho BUY, High cho SELL.
  Phép lấy cực trị là stress để đo độ nhạy, chưa biết giá stop-market
  thực. Cả hai giữ cách đóng phiên tại Open 15:59. Các khoảng kết quả
  dưới đây chỉ áp dụng cho những giả định đã khai báo.
- Gross dùng chuyển động giá cổ phiếu. Paper trừ 0,0035 USD/share/side.
  Phí thay thế chỉ trừ 0,004% notional mỗi chiều theo kịch bản đã
  ghi trong pilot, chưa xác nhận là phí FTMO. Chưa có spread thực thi,
  tick-order hoặc giá khớp trên CFD. Phép so chi phí không cộng hai
  biểu commission lại với nhau.
  [Phương pháp paper](https://alexandria.unisg.ch/server/api/core/bitstreams/3c2989c4-688d-4d78-8a71-f02690990d51/content)

## Kết quả sáu tháng

| Kịch bản | Gross USD / mean R | Sau phí paper USD / mean R | Sau phí thay thế USD / mean R |
|---|---:|---:|---:|
| Thứ tự nến bất lợi, chạm SL theo giá liên tục | −233,05 / −0,0367 | −269,28 / −0,0425 | −329,55 / −0,0521 |
| Thứ tự nến thuận lợi, chạm SL theo giá liên tục | +1.028,20 / +0,1639 | +991,97 / +0,1581 | +931,75 / +0,1485 |
| Khớp SL tại cực trị bất lợi của phút chạm | −2.318,92 / −0,3692 | −2.355,15 / −0,3750 | −2.415,41 / −0,3846 |

`Mean R` là trung bình PnL của từng lệnh chia risk của chính lệnh đó.
Để so với mốc **500 USD/sáu tháng**, dùng 500 / 6.271,73 =
**0,07972R** trên tổng risk đã triển khai. Sau phí paper, hai đầu theo
thứ tự nến đạt **−0,04294R / +0,15817R** trên tổng risk, còn bảng
stress khớp là **−0,37552R**. Kết quả thuận lợi qua được mốc tham
chiếu khi đứng riêng. Kết quả phụ thuộc một phút quyết định và thiếu
xác nhận fill, nên chưa dùng để ngoại suy tiền cả năm. Winrate sau
commission paper là **7–8/42 (16,7%–19,0%)**. Trung vị khoảng **−1,01R**.

| Nhóm | Lệnh | USD sau phí paper, thứ tự bất lợi → thuận lợi | USD stress khớp, phí paper |
|---|---:|---:|---:|
| BUY | 22 | −998,08 → −998,08 | −2.240,54 |
| SELL | 20 | +728,81 → +1.990,05 | −114,61 |
| Tháng 7 | 1 | −148,88 → −148,88 | −236,22 |
| Tháng 8 | 4 | −596,17 → −596,17 | −880,40 |
| Tháng 9 | 10 | +77,96 → +77,96 | −511,62 |
| Tháng 10 | 9 | +24,27 → +24,27 | −344,62 |
| Tháng 11 | 4 | −601,19 → −601,19 | −726,87 |
| Tháng 12 | 14 | +974,73 → +2.235,98 | +344,59 |

**Nguồn bất định.** Có 11 nến entry vừa đi qua vùng kích hoạt vừa qua
mức SL, mỗi nến ứng với một lệnh. Thứ tự giá đổi giờ thoát ở cả 11.
Mười lệnh vẫn chạm cùng SL ở phút khác nên tiền bằng nhau trong mô
hình liên tục. Riêng SELL **09:35 ET ngày 16/12** sẽ thoát cuối ngày
**+1.110,42 USD** nếu High xuất hiện trước và SL bị đi qua trước khi
lệnh được kích hoạt. Nếu Low xuất hiện trước và kích hoạt SELL, High
sau đó chạm SL, kết quả **−150,82 USD**. Chênh **1.261,25 USD** giải
thích toàn bộ khoảng PnL của hai thứ tự. Có 7–8 lệnh đóng phiên và
34–35 lệnh đóng bởi SL trong hai trường hợp.

**Tập trung lợi nhuận.** Ở đầu thuận lợi, lệnh 22/12 đóng góp
**+1.517,26 USD**, bỏ lệnh này còn **−525,29 USD**. Ba lệnh thắng lớn
nhất đóng góp **3.694,99 USD**, bằng **60,6%** tổng tiền của các lệnh
thắng. Bỏ cả ba còn **−2.703,02 USD**. Ở đầu bất lợi, bỏ lệnh thắng
lớn nhất còn **−1.786,54 USD**, bỏ ba còn **−3.784,17 USD**. Cắt đuôi
ở đây chỉ dùng đọc độ tập trung, không thay luật hoặc loại lệnh khỏi
kết quả chính.

## Đối chứng bỏ đúng bộ lọc RVOL

Cùng lịch 111 ngày có đủ warm-up, cách đo ATR, side, phát hiện phá
biên, stop, phí và ngân sách vốn. Bỏ đúng RVOL ≥1. Sổ đối chứng
tái lập cả 42 lệnh cũ và thêm 61 lệnh RVOL<1. Bảng tính theo phí paper.

| Mẫu | Lệnh | USD theo hai thứ tự nến | Mean R theo hai thứ tự | USD / mean R khi stress khớp |
|---|---:|---:|---:|---:|
| RVOL ≥1 đã khóa | 42 | −269,28 → +991,97 | −0,0425 → +0,1581 | −2.355,15 / −0,3750 |
| RVOL <1, phần thêm | 61 | +4.223,41 → +5.241,88 | +0,4616 → +0,5736 | +2.544,59 / +0,2773 |
| Toàn bộ ORB | 103 | +3.954,14 → +6.233,85 | +0,2561 → +0,4042 | +189,44 / +0,0113 |

Trên đúng lát TSLA này, bộ lọc RVOL giảm số lệnh và nhóm nó giữ có
kỳ vọng thấp hơn nhóm bị loại trong cả ba kịch bản báo cáo. Mẫu toàn
ORB khi stress khớp còn **+23,33 USD** sau phí thay thế, trước spread
và chi phí CFD chưa đo. Đây là đối chứng mô tả, chưa chứng minh bộ
lọc hại toàn universe hay đủ cơ sở promote một chiến lược ORB mới.

## Quyết định và đối soát

**Không mở thêm slice 2023H1 hoặc replay 50k.** Kịch bản thuận lợi có
lãi, song một thứ tự nến chưa biết đổi dấu của toàn mẫu và stress
khớp không chừa biên trước chi phí thực thi. Dừng ở mức ưu tiên của
pilot một mã. Một lát M1 ngoài mẫu cũng chưa trả lời dứt điểm thứ tự
giá của lệnh quyết định, và dữ liệu lệnh FTMO cũng chưa có.
`BASE_GUARD` vẫn `NOT_QUALIFIED`, hướng Gold PM đã đóng theo
[báo cáo trước](PROP-STOCKS-IN-PLAY-AND-GOLD-PM-RESULTS-20261118.md).

Đăng ký quy ước trước outcome tại SHA256
`64268db78746824093824e1102d8761ee78fbbbc84d0870f49693062bfd2a357`.
Script khóa hash sổ 42, code gốc, ZIP và manifest. Kiểm đủ OHLCV cash
của 127 phiên. **6/6 kiểm thử** tình huống về thứ tự entry, SL, gap
và đóng phiên. Tính lại qua implementation khác cho **206 đường giá
mô hình, 103 entry và 27 tổng PnL theo nhóm/kịch bản/phí**. Hồ sơ private
lưu tại `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/prop-tsla-2022h2-cash-path-20261118/`.
File `tsla-cash-path.private.json.zst` đã xác minh round-trip, SHA256
`246b436d29f7a52fbfca78f8c32147627fabfa03f908f547b357a5f546c2e13d`.
Tất cả giá trong lượt này thuộc mẫu cash 07–12/2022. Không truy cập
broker, mua dữ liệu, đổi risk hoặc mở giá 2024–2026.

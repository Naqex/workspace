# R029 currency carry trên EURUSD, GBPUSD và AUDUSD

**Gác R029 ở quy mô risk đang dùng.** Chỉ có **5 vị thế trong sáu năm**.
Tại risk tối đa 150 USD/lệnh, phép thử cần **swap ròng 11,50%/năm**
trên phần giá trị danh nghĩa thực sự nắm giữ để góp thêm 1.000 USD/năm.
Chênh lãi suất chính sách quan sát được quy cùng cơ sở chỉ khoảng
**1,16%/năm** trước mọi phụ phí. Mô hình chênh lãi suất cho khoảng
**+189 USD/năm** sau phí mở/đóng. Giảm một điểm phần trăm cho chi phí
tài trợ thì còn **+111 USD/năm**. Không đủ để dành lượt replay 50k.
[Mốc đóng góp và danh mục đối chứng](PROP-PAYOUT-REPLAY-DECISION-20261118.md)

## Công thức và phạm vi

Catalogue và round C08 chưa có outcome riêng cho carry. R029 ở đây
xếp theo chênh **lãi suất**, còn R033 xếp theo biến động **giá**.
Nghiên cứu ECB sử dụng forward. Bài này dùng tỷ giá spot và lãi
suất công bố để tạo tín hiệu và đo quy mô. Forward premium không
được cộng lần nữa. Carry có thể kiếm tiền từ chênh lãi suất, nhưng
tỷ giá đi ngược hoặc thanh khoản xấu có thể lấn át khoản chênh này.
[Catalogue](STRATEGY-CATALOGUE-20261107.md) ·
[ECB, carry dùng forward](https://www.ecb.europa.eu/pub/pdf/scpwps/ecbwp1968.en.pdf) ·
[Brunnermeier, Nagel và Pedersen](https://www.nber.org/papers/w14473)

- **Lịch và quy tắc.** Từ 02/2018 tới 12/2023, vào ngày đầu tháng
  mà USD, EUR, GBP và AUD cùng cho phép thanh toán, lúc 14:00 UTC,
  chọn chênh tuyệt đối lớn nhất trước USD. Mua đồng có lãi suất
  cao và bán đồng thấp. Chỉ dùng mức BIS mang ngày trước ngày
  quyết định. Giá trị không có ở ngày nghỉ dùng quan sát trước
  đó, tối đa bảy ngày. Đối chiếu API nhiều mã với từng mã. Các
  dòng BoE `NaN` ngày nghỉ giữ là thiếu. Chuỗi BIS dùng Fed target
  midpoint, lãi suất tái cấp vốn chính ECB trong giai đoạn này,
  Bank Rate của BoE và cash rate target RBA. Đây là mức chính
  sách theo ngày hiệu lực được công bố, chưa có vintage theo
  từng giờ công bố. [BIS policy rate](https://data.bis.org/topics/CBPOL)
- **Kích thước và stop.** Một vị thế cùng lúc. Stop cách giá vào
  hai lần trung bình true range của 20 phiên đủ H1. Risk trước
  giao dịch bao gồm spread và phí stress vòng lệnh. Lot 100.000
  đơn vị cơ sở, lưới 0,01 lot và margin Swing 1:30 dùng làm
  giả định. Nếu xếp hạng giữ nguyên cặp và chiều, tiếp tục vị thế
  với cùng size và SL. Sau khi stop, chỉ được vào lại tại lần
  xét tháng kế tiếp. EURUSD dùng Bid M1 V14 tổng hợp H1 và Ask
  proxy 1 pip. GBPUSD/AUDUSD dùng H1 native hai chiều V11. Các
  giá mở/đóng theo lịch có exact H1 Open trong phép thử.
- **Chi phí giao dịch.** Spot PnL đi qua Bid/Ask, nên spread đã
  nằm trong PnL. Không trừ thêm spread. Commission tham chiếu
  2,50 USD/lot/side và stress slippage 0,20 pip/side. Fee theo
  công bố FTMO tháng 9/2025 dùng để đo khả thi triển khai trên
  đường giá cũ. [FTMO commission](https://ftmo.com/en/blog/trading-updates/trading-update-25-sep-2025/)

## Tiền, thời gian phơi nhiễm và ngưỡng swap

71 lần xếp hạng cho **5 vị thế mới và 66 lần giữ nguyên vị thế**.
Stop trung vị 177,61 pip, risk dự tính cao nhất 147,21 USD.
Notional cao nhất chỉ **10.722 USD**, tương đương **357 USD**
margin ở 1:30. Giới hạn ở đây là risk mỗi lệnh và biên độ stop.
Giữ tổng **2.114,83 ngày**, trung vị **86,88 ngày**, dài nhất
**1.489 ngày**. Trung bình theo thời gian là 7.849 USD notional.
Theo lịch ngày giá trị chịu swap là **7.838 USD notional-năm
trên mỗi năm lịch**. Trên mỗi 100.000 đơn vị cơ sở, tổng phơi
nhiễm là 146,63 lot-ngày trong sáu năm, hoặc 24,44 lot-ngày/năm.

Từ riêng phơi nhiễm, 1.000 USD/năm đòi **12,76%/năm** ròng trên
notional chịu swap, tương đương **40,92 USD/lot/ngày giá trị**.
Sau khi ghi nhận lợi nhuận spot, cần thêm **901,46 USD swap/năm**,
tương đương **11,50%/năm** hoặc **36,89 USD/lot/ngày giá trị**.
Để chỉ hòa vốn, sổ đã có lãi spot nên có thể chịu swap âm tới
591,22 USD trong sáu năm, tương đương −1,26%/năm trên cơ sở
phơi nhiễm này. Dư địa hòa vốn khác xa mục tiêu cộng 1.000 USD/năm.

| Năm | Vị thế mới | Notional-năm chịu swap, USD | Spot sau phí, USD | Swap theo chênh lãi suất, USD | Net với swap giả lập, USD | Swap cần để đạt 1.000 USD, %/năm |
|---|---:|---:|---:|---:|---:|---:|
| 2018 | 1 | 7.926 | +689,08 | +143,61 | +832,69 | 3,92% |
| 2019 | 0 | 8.714 | +178,57 | +188,46 | +367,03 | 9,43% |
| 2020 | 0 | 8.786 | −704,55 | +37,01 | −667,54 | 19,40% |
| 2021 | 0 | 8.714 | +593,18 | +10,89 | +604,07 | 4,67% |
| 2022 | 2 | 6.482 | +205,68 | +75,64 | +281,33 | 12,25% |
| 2023 | 2 | 6.407 | −370,74 | +87,60 | −283,14 | 21,40% |

Hàng năm đánh dấu vị thế đang mở ở ranh giới năm bằng giờ H1
đã có trước ranh giới, rồi phân bổ chi phí và PnL theo accrual.
Sáu năm cộng lại khớp sổ đóng. Spot sau spread **+595,09 USD**,
trừ commission **2,15 USD** và slippage **1,72 USD**, còn
**+591,22 USD**. Khoản swap giả lập **+543,21 USD** gồm **+0,55
USD** ở BUY và **+542,66 USD** ở SELL. Với phụ phí tài trợ 1 điểm
phần trăm theo năm áp cả hai chiều, swap còn **+72,91 USD**.
Một SELL EURUSD từ 02/2018 tới 03/2022 đóng góp **+1.282,50 USD**
cả spot lẫn policy carry. Loại nó ở bảng độ tập trung để đo
độ phụ thuộc, bốn lệnh còn lại **−148,07 USD**. Quy tắc không đổi.

| Cụm | Spot USD/năm | Net theo chênh lãi suất USD/năm | Net khi trừ phụ phí 1 điểm % USD/năm | Swap ròng cần để đạt 1.000 USD/năm |
|---|---:|---:|---:|---:|
| 2018–2020 | +54,37 | +177,39 | +92,64 | 11,16%/năm |
| 2021–2023 | +142,71 | +200,75 | +128,74 | 11,90%/năm |

### Ngày tính và kiểm mức swap có dấu

Mô hình dùng 17:00 New York từ thứ Hai tới thứ Sáu theo DST. Mỗi
lần, đếm chênh ngày giữa hai ngày thanh toán T+2 kế nhau theo lịch
cặp tiền. Dùng QuantLib 1.40 với lịch Fed, TARGET, UK Settlement
và AU Settlement. Kiểm thứ Tư thường có ba ngày. Ví dụ EURUSD
24/05/2023 tính bốn ngày do Memorial Day. 26/05 có hệ số 0. Tổng
**1.509 mốc** phân rã thành 74 ×0, 1.117 ×1, 15 ×2, 254 ×3,
43 ×4 và 6 ×5, tổng **2.111 ngày giá trị**. Không cộng swap
thứ Bảy và Chủ Nhật riêng. Ngày thanh toán T+2 và timestamp
17:00 là mô hình tham chiếu. Lịch charge FTMO lịch sử, holiday
override và mức swap của đúng server vẫn chưa có.
[OANDA giải thích T+2, ngày lễ và triple](https://www.oanda.com/us-en/trading/financing-fees/) ·
[FTMO giải thích swap và triple](https://ftmo.com/en/blog/what-is-a-swap-and-for-whom-is-it-important/) ·
[QuantLib](https://www.quantlib.org/)

Có hai bảng **OANDA TMS .pro** đúng ngày trong Development. Đây
là swap Long/Short theo phần trăm mỗi năm của broker khác. Tính
thử trên cùng USD notional × ngày giá trị / 365 để so quy mô.
Không dùng chúng thay cho sổ FTMO hoặc áp cho các ngày ngoài
hiệu lực. Lãi GBPUSD có thể âm cả hai chiều.

| Tuần hiệu lực | EURUSD Long / Short | GBPUSD Long / Short | AUDUSD Long / Short | Đối chiếu với vị thế của R029 đúng tuần |
|---|---:|---:|---:|---|
| 17–23/07/2023 | −2,58% / +0,72% | −1,02% / −0,75% | −1,96% / +0,04% | EURUSD SELL, 7 ngày giá trị. +0,92 USD theo TMS so với +1,43 USD theo BIS |
| 04–10/12/2023 | −2,15% / +0,60% | −0,90% / −0,62% | −1,74% / +0,20% | AUDUSD SELL, 7 ngày giá trị. +0,28 USD theo TMS so với +1,43 USD theo BIS |

Hai tuần này dùng kiểm tính hợp lý của dấu và độ lớn, không là
mẫu đủ để ước lượng swap cả sáu năm. Chưa tìm được chuỗi FTMO
2018–2023 có dấu, đơn vị, symbol và ngày charge xác minh. Ngay
cả phép tính không có phụ phí tài trợ cũng chỉ cho **+177 /
+201 USD/năm** ở hai cụm, cách xa mục tiêu.
[TMS 17/07/2023](https://www.tmsbrokers.com/sites/default/files/documents/18-07-2023/punkty_swapowe_tms_en_2023.07.17.pdf) ·
[TMS 04/12/2023](https://www.tmsbrokers.com/sites/default/files/documents/04-12-2023/punkty_swapowe_tms_en_2023.12.04.pdf)

## Rủi ro và khả năng ghép BASE

Cả **5/5 vị thế** chồng ít nhất một lệnh BASE ở cả sổ PRIMARY
và STRICT. Đỉnh đếm cùng lúc là **3 vị thế** kể cả carry, tức
450 USD risk nếu cùng quy mỗi vị thế về tham chiếu 150 USD.
R029 độc lập có ký quỹ nhỏ, nhưng không có vị thế nào hoàn toàn
tách khỏi BASE trong suốt vòng đời. Đây là số đếm chồng thời gian.
Chưa mô phỏng admission hoặc đóng góp khi dùng chung sổ.

Có **3 stop**, gồm hai lần giá Open đã qua SL. Khi gap qua stop,
phép đo dùng Open quan sát. Nếu chạm bên trong H1 thì mô hình
liên tục dùng SL và kiểm thêm cực trị bất lợi cùng giờ. Lệnh
spot lỗ lớn nhất **142,81 USD**, lên **147,12 USD** nếu dùng cực
trị stop hour. Kịch bản chênh lãi suất trừ 1 điểm phần trăm,
trên vốn đầu 50.000 USD, cho lỗ ngày Prague xấu nhất **143,73
USD (0,29%)**, lỗ dưới vốn đầu **65,84 USD (0,13%)** và peak-to-
valley H1 theo thứ tự cực trị bất lợi **1.226,78 USD (2,45%)**.
Mức cuối đo phần lãi nổi đã mất theo thời gian. Hai ngưỡng đệm
nghiên cứu 3% ngày và 6,5% dưới vốn đầu đều còn rộng trong mô hình.

Trong khi giữ lệnh có **21 giờ thiếu H1 trong phiên** và **148 giờ
thiếu H1 trùng ngày nghỉ thanh toán** ngoài khoảng nghỉ tuần đã
loại. Nhãn ngày nghỉ thanh toán không khẳng định FX đóng cửa.
Đường intrahour và gap broker chưa xác minh. Không thể lấy năm
lệnh và biên H1 làm bằng chứng đủ an toàn cho tài khoản. Lý do dừng
ngay là tần suất, độ tập trung và quy mô thu nhập ở cùng risk.
Gắn `CADENCE_OR_SAMPLE_SHORTFALL`, `DATA_PATH_INCOMPLETE` và
`PROP_UNMEASURED`. Giữ BASE_GUARD ở `NOT_QUALIFIED`.

## Đối soát

Luật niêm phong trước giá và PnL ở SHA256
`879809d9257da335eb47297aebf9117e3990c0ca2a26e97c8f27adef09210f42`.
Bằng chứng tại
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/prop-fx-carry-r029-20261118/`.
Comparator độc lập tính lại 1.509 ngày roll, 5 sổ lệnh, notional-năm,
ngưỡng swap và PnL bằng Fraction. Artifact Zstandard có SHA256
`5fc847eb8bb75a31e334eb6fe36839ea91ff31a7734f960956830e9df86849cd`
và kiểm tra giải nén khớp dữ liệu. Lần chuẩn bị đầu dừng vì parser
coi `NaN` BoE là số khi so hai API. Sửa admission thành thiếu dữ
liệu trước khi đọc giá. Không dùng dữ liệu giá 2024–2026, không
tạo tài khoản, đặt lệnh, mua dữ liệu hay mở biến thể.

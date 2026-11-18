# US500 Calendar 60/40 | Kết quả Development

19/11/2026 · **Gác công thức đã thử cho payout.** Sổ có stop âm
**256,78 USD/năm** ở 2018–2020 và **78,06 USD/năm** ở 2021–2023.
Benchmark cổ phiếu đơn thuần thắng 60/40 ở cụm đầu nhưng thua ở
cụm sau. Phần đóng góp từ trái phiếu chưa ổn định. `ECONOMIC_FAIL`
trên phần đo được. `DATA_PATH_INCOMPLETE` cho replay đầy đủ.
BASE_GUARD vẫn `NOT_QUALIFIED`.

## Tín hiệu và thời điểm có thể vào

Harvey, Mazzoleni và Melone mô phỏng danh mục 60% cổ phiếu, 40%
trái phiếu. Tỷ trọng cổ phiếu lên trên 60% khi cổ phiếu tăng hơn
trái phiếu, tạo nhu cầu bán để cân lại. Phép thử giữ **Calendar**
của §2.2 với nhóm năm phiên cuối tháng. Tỷ trọng reset đúng 60/40
tại close phiên cuối tháng, nên close đó phát tín hiệu bằng 0
cho phiên kế. Từ close của những phiên còn lại, mua US500 nếu
tỷ trọng dưới 60%, bán nếu trên 60%. Chỉ thử một cửa sổ thực thi
từ 09:32 New York phiên cash kế tiếp đến giá mở phút cuối phiên.

Trong nghiên cứu gốc, một độ lệch chuẩn của Calendar tương ứng
khoảng **17 bp** thay đổi lợi suất cổ phiếu ngày sau. Hệ số trên
spread cổ phiếu–trái phiếu khoảng **19,4 bp**. Đây là hai hệ số
hồi quy, với các biến kiểm soát và thang đo riêng. Trong bảng
của ta, PnL chỉ từ US500 sau 09:32, nên bỏ phần dịch chuyển từ
close hôm trước tới entry. Mẫu công bố 1997–17/03/2023 trùng
phần lớn Development. [Nghiên cứu gốc, §2.2 và §4.2](https://www.nber.org/system/files/working_papers/w33554/revisions/w33554.rev0.pdf) ·
[Công thức reset trong slide của tác giả](https://people.duke.edu/~charvey/temp/Harvey_Cornell_seminar.pdf).

Tỷ trọng dùng **IVV / IEF** thay cho hai futures Bloomberg.
Lợi suất ngày bằng `(close + phân phối tiền mặt theo ngày ex) /
close trước`. Cả hai nguồn có 1.509/1.509 phiên NYSE 2018–2023.
Kho lưu 25 phân phối IVV và 72 phân phối IEF, không có sự kiện
split trong khoảng. Các dấu phiên trong chuỗi khớp giờ NYSE mở,
còn close chỉ dùng từ phiên hôm sau. Kho hiện tại không xác
nhận mọi revision trong lịch sử. Đây là chỉ báo chênh lệch
lợi suất hai ETF, chưa đo giao dịch thực của các quỹ.
[Nguồn IVV](https://www.ishares.com/us/products/239726/ishares-core-sp-500-etf) ·
[Nguồn IEF](https://www.ishares.com/us/products/239456/ishares-710-year-treasury-bond-etf) ·
[Lịch giá IVV](https://finance.yahoo.com/quote/IVV/history/) ·
[Lịch giá IEF](https://finance.yahoo.com/quote/IEF/history/).

R025 luôn BUY một nhóm ngày quanh giao tháng. US500-LETF-AUM dùng
quy mô ETF đòn bẩy để chọn ngày đánh theo momentum cuối phiên.
Phép hiện tại cần hướng từ độ lệch 60/40 trước phiên. Đối chứng
khóa trước là (1) đảo chiều theo dấu return tháng của IVV riêng
và (2) luôn BUY theo cùng lịch. Hai đối chứng dùng cùng ngày, giờ,
khoảng stop và lot khi tính PnL. [R025 sau sửa nguồn](INDEX-EXPLICIT-SOURCE-RESULTS-20261108.md) ·
[US500-LETF-AUM](PROP-US500-LETF-AUM-AND-EUR-COT-RESULTS-20261118.md).

## Phễu, ma sát và kết quả từng năm

Giữ ngày đầu ra theo lịch cash NYSE, tính giờ đóng sớm vào lịch.
Dùng M1 Bid/Ask của US500 đã kiểm hash theo bốn quý từng năm.
Markout theo giờ giữ đến phút cuối phiên. Reference trừ thêm
0,50 point/vòng, stress trừ 2,50 point/vòng, đều ngoài spread
đã nằm sẵn trong hai giá. FTMO công bố commission chỉ số bằng
0. Sổ stress mô phỏng thêm 1,00 point commission vòng lệnh
và 1,50 point trượt. Không có vị thế qua đêm, nên không tính
swap hoặc điều chỉnh cổ tức CFD qua đêm trong cửa sổ này.
[FTMO về phí chỉ số](https://ftmo.com/en/blog/zero-commissions-on-indices/).

Phép kiểm stop dùng một lần bình quân true range 14 phiên IVV
đã đóng, đổi theo tỷ lệ giá sang US500. Rủi ro tối đa danh nghĩa
150 USD trên 50k. Lot làm tròn xuống 0,01, hệ số 1 USD/point/lot,
margin tham chiếu 1:15. Chặn ma sát ước lượng khi vào trên 12%
khoảng stop. Sổ có SL cần đủ toàn bộ phút giữa entry và deadline.
Gap xuyên SL dùng báo giá mở nến phía có thể thoát. Chạm trong
nến dùng giá SL mô phỏng. Spread của hai đầu dùng đúng Bid/Ask.
Hệ số lot/margin cần kiểm lại trên tài khoản đích.
[FTMO về leverage theo nhóm tài sản](https://ftmo.com/en/blog/a-few-answers-to-your-questions/).

| Năm | Tín hiệu / định giá hai đầu | Qua cap phí / đủ đường M1 | Markout chuẩn / stress (point/lệnh có giá) | SL / ma sát vào trung vị (point) | Net có SL stress (USD) |
|---|---:|---:|---:|---:|---:|
| 2018 | 44 / 44 | 27 / 25 | +3,53 / +1,53 | 35,88 / 2,76 | +101,50 |
| 2019 | 48 / 48 | 26 / 18 | −3,10 / −5,10 | 24,26 / 2,76 | −596,82 |
| 2020 | 48 / 46 | 46 / 43 | −1,96 / −3,96 | 51,63 / 2,95 | −275,03 |
| 2021 | 48 / 48 | 48 / 37 | −1,02 / −3,02 | 42,80 / 2,96 | −192,68 |
| 2022 | 48 / 48 | 48 / 47 | +5,95 / +3,95 | 82,15 / 2,99 | +520,14 |
| 2023 | 48 / 48 | 48 / 46 | −1,49 / −3,49 | 42,56 / 3,02 | −561,64 |

Trong 360 dòng lịch cuối tháng, có **72 reset flat**, bốn ngày
chưa có mốc gốc trong tháng 1/2018, và **284 tín hiệu**. 282
có giá hai đầu. Hai ngày thiếu giá là 28/04/2020 và 24/11/2020.
Có 39 lần trượt phí trước khi xét toàn đường giá. Trong 243 cơ
hội đã qua phí, 27 thiếu ít nhất một phút. **216** định giá được
theo SL, gồm 103 BUY và 113 SELL. Tổng có 191 thoát theo giờ,
24 chạm stop trong nến và một lần xuyên stop tại mở nến. 2018
và 2022 có markout stress dương. Chỉ 2022 vượt thêm sàn mean
ma sát cùng mẫu (3,95 so với 2,94 points).

## So hai cụm và mức tiền cần đạt

| Chỉ số | 2018–2020 | 2021–2023 |
|---|---:|---:|
| Tín hiệu / cụm tháng có tín hiệu | 140 / 35 | 144 / 36 |
| Lệnh đo SL / cụm tháng có lệnh đo | 86 / 26 | 130 / 36 |
| Định giá được bình quân mỗi năm | 28,7 lệnh | 43,3 lệnh |
| Mean stress đến giờ, trước SL | −2,60 point | −0,85 point |
| 60/40 có SL, sau stress | **−256,78 USD/năm** | **−78,06 USD/năm** |
| Mean net R/lệnh, 1R = 150 USD | −0,05972R | −0,01201R |
| Đối chứng chỉ IVV, cùng lot và stop | +14,01 USD/năm | −301,89 USD/năm |
| Đối chứng luôn BUY, cùng lot và stop | −235,78 USD/năm | −534,42 USD/năm |
| Lot trung vị / notional bình quân | 3,155 / 9.621 USD | 2,54 / 11.374 USD |
| Cần để đóng góp 1.000 USD/năm | **34,88 USD/lệnh**, 36,26 bp net | **23,08 USD/lệnh**, 20,29 bp net |
| Cash DD / DD từ đỉnh cash trước theo mark M1 | 1.265,99 / 1.296,57 USD | 841,92 / 864,88 USD |
| Lỗ tiềm ẩn trong ngày lớn nhất trên phần mô phỏng | 149,95 USD (0,300%) | 149,98 USD (0,300%) |
| Bỏ top 10 lệnh thắng, tổng theo cụm | −2.074,74 USD | −2.431,79 USD |

Số bp cần đạt lấy USD/lệnh chia cho notional bình quân
của lệnh định giá được. Đây là phép quy đổi quy mô ở risk đã
khóa. Tháng là đơn vị gom tín hiệu có cùng quá trình tích lũy
tỷ trọng. Mỗi tháng có tối đa bốn lệnh liên quan, nên 216 lệnh
không đại diện cho 216 lần quan sát độc lập.

Thêm IEF chỉ đổi hướng ở 28/284 tín hiệu và 28/216 lệnh định
giá được. Trên những lệnh đổi hướng, PnL so với chỉ IVV giảm
812,38 USD ở cụm đầu và tăng 671,49 USD ở cụm sau. Lợi ích 2022
không duy trì sang 2023. Lệnh thắng lớn nhất mỗi cụm lần lượt
+180,27 USD ngày 26/12/2018 và +340,29 USD ngày 26/08/2022.
Tổng top 10 là +1.304,39 và +2.197,61 USD.

Chồng lịch giữ lệnh với V19 BASE PRIMARY OLHC trên 18/86 và
39/130 lệnh. Các lệnh không chồng tự chúng cộng −454,27
và −630,68 USD theo cụm. Số này chưa mô phỏng cùng tài khoản.
Ba lệnh đo được trùng 16 ngày FOMC đã niêm phong trong 2019/2022.
Cả ba giữ qua mốc tin, 0 lần thoát theo mô hình nằm sát ±2 phút.
Chưa chứng minh thời điểm chạm stop trong nến hoặc đủ lịch tin
hạn chế cho Funded Standard. Ba phiên có đóng sớm đã dùng đúng
cash close. [Quy định tin FTMO](https://ftmo.com/en/faq/can-i-trade-news/) ·
[Lịch FOMC](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm).

## Quyết định và đối soát

Gác thu thêm dữ liệu hoặc chạy vòng đời tài khoản cho cấu hình
này. Phần quan sát có cả markout stress âm và sổ SL âm ở hai
cụm. Cụm đầu bình quân dưới 40 lệnh/năm. 29 tín hiệu còn thiếu
endpoint hoặc đường giá cần thiết cho sổ SL. Không quy chúng
thành lệnh hòa hoặc suy kết quả cho ES–TY, các giờ khác hay
giai đoạn ngoài mẫu. Lượt này chỉ dùng chuỗi giá 2018–2023.

Lưu khóa trước kết quả và 360 dòng riêng. Bộ tính Fraction đối
soát tỷ trọng, phí, lot, DD và đối chứng. So lại 12 đường M1
(thoát theo giờ sớm nhất và lần SL đầu tiên mỗi năm) từ kho
niêm phong, gồm cả hai phía. Kiểm chứng M1 vẫn chịu giới hạn
khớp ở mức SL mô phỏng, thanh khoản và lịch phiên tài khoản đích.

Bằng chứng tại
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/prop-us500-calendar-rebalance-20261119/`.

| File | SHA256 |
|---|---|
| `registration.md` | `184c200c19827978647a4f614a13430fdaf3ba799f014f2cac49adcfd4eb7593` |
| `series-receipt.json` | `80b6e720a87d6da655e454f64f60f2c9d3859233b25ae9a5deecafb368591604` |
| `calendar-results.json.zst` | `e766c5bda2e4e8e0c116138deddcedb1a36a1c1037d7938e55553b5d8c668a84` |
| `review.json` | `1da69681b46ef7853f31dccb218945e923c2e173678bb1e016df5391149e365f` |


## Đối chiếu qua đêm và commission trên cùng 284 tín hiệu

**Gác cả hướng kiểm tra vào sớm hơn.** Tính trọn chênh lệch
từ close hôm trước đến 09:32 vẫn chỉ cho **+18,02 / +172,28
USD/năm gross** ở hai cụm với lot tham chiếu đã khóa. Đây là
biến động định giá. Kho giá chưa chứng minh thời điểm có thể
biết đủ IVV/IEF và khớp được trong khoảng ngoài phiên. Kết quả
dưới đây giữ nguyên ba chuỗi hướng mua/bán và toàn bộ 284 ngày.

### Tách bốn phần trên cùng nguồn US500

Dùng mid Bid/Ask CFD tại năm mốc: close nến cash cuối ngày
tín hiệu, open phiên sau, open 09:32 New York, open phút thoát
đã khóa và close nến cash cuối. Mỗi ngày dùng cùng close trước
làm mẫu số bp. USD gross dùng 1 USD/point/lot và lot được tính
tại close trước bằng khoảng stop theo biến động IVV đã biết,
ngân sách 150 USD, phí dự phòng gốc, bước lot 0,01 và margin
tham chiếu 1:15. Lot ở 09:32 của sổ cũ chỉ dùng cho phép bỏ
commission bên dưới. Close là mốc định giá, còn lệnh ở mốc đó
chưa được kiểm khả năng khớp hay điều kiện quỹ.

| Phần giá — Calendar 60/40 | 2018–2020, 136 ngày | 2021–2023, 143 ngày |
|---|---:|---:|
| Close trước → cash open | −0,663 point · −1,82 bp · −108,95 USD/năm | +1,788 point · +4,31 bp · +241,71 USD/năm |
| Cash open → 09:32 | +1,015 point · +3,50 bp · +126,97 USD/năm | −0,671 point · −1,59 bp · −69,42 USD/năm |
| 09:32 → phút thoát | +0,441 point · +2,95 bp · −81,01 USD/năm | +2,080 point · +4,84 bp · +192,67 USD/năm |
| Phút thoát → cash close | +0,277 point · +1,23 bp · +10,14 USD/năm | +0,302 point · +0,79 bp · +38,53 USD/năm |
| **Close → close** | **+1,069 point · +5,86 bp · −52,85 USD/năm** | **+3,498 point · +8,34 bp · +403,48 USD/năm** |

Point và bp là trung bình trên ngày có đủ cả năm mốc.
Dấu tiền có thể khác dấu của point vì ngày có lãi/lỗ dùng lot
khác nhau. Bốn phần cộng đúng close-to-close trước khi làm tròn.
Trên đúng 279 ngày, phần 09:32 đến phút thoát sau spread và
2,50 point stress còn **−2,446 / −0,872 point/lệnh**. Bỏ đúng
1 point commission cho **−1,446 / +0,128**. Spread tại entry
và exit chỉ trừ một lần khi chuyển từ mid sang Bid/Ask thực thi.

| Gross USD/năm, cùng lot tham chiếu | Trước 09:32, 2018–2020 / 2021–2023 | Close-to-close, 2018–2020 / 2021–2023 |
|---|---:|---:|
| Calendar 60/40 | +18,02 / +172,28 | −52,85 / +403,48 |
| Chỉ IVV | −199,18 / +122,86 | +141,99 / +71,12 |
| Luôn BUY | +363,29 / +187,78 | +254,77 / +29,37 |

Khoảng ngoài phiên đổi dấu giữa hai cụm. Ngay cả tổng trước
09:32 gồm thêm hai phút đầu phiên cũng dưới mốc 1.000 USD/năm
và kém luôn BUY ở cả hai cụm. Không cần định giá tiếp giả
thuyết khớp sau giờ công bố dữ liệu, swap, cổ tức CFD hay đóng
trước kỳ nghỉ. Phép đo này giới hạn ở CFD và lịch đã khóa.
Kết quả paper dùng futures và hệ số ở tần suất ngày vẫn là
phạm vi khác. [Nghiên cứu gốc §2.2 và §4.2](https://www.nber.org/system/files/working_papers/w33554/revisions/w33554.rev0.pdf).

Có **279/284** ngày đủ cả năm mốc. Ngày vào 28/04/2020 và
24/11/2020 thiếu mốc phiên mới. Ba ngày 29/04/2020, 25/11/2020
và 27/11/2023 thiếu close trước. 282/284 có đủ đoạn 09:32
đến phút thoát, trong đó 3 ngày chưa đủ để phân rã toàn phiên.
Cả 284 vẫn ở hồ sơ tín hiệu, các mốc trống giữ là chưa đo.
Không đổi mẫu của sổ 216 lệnh có stop.

### Phần thay đổi khi commission về 0

FTMO công bố chỉ số mô phỏng miễn commission. Trên đúng 216
lệnh đã định giá, cộng **1 point × lot gốc** vào PnL mỗi lệnh,
giữ trượt stress 1,50 point/vòng cùng spread, SL, giá khớp, lot
và điều kiện chọn lệnh đã khóa. Đây là phép tính độ nhạy trên
sổ cũ. [Commission chỉ số FTMO](https://ftmo.com/en/blog/zero-commissions-on-indices/).

| Năm hoặc cụm | Lệnh | Tiền cộng lại cả kỳ (USD) | Net 60/40 mới (USD/năm) |
|---|---:|---:|---:|
| 2018 | 25 | 79,48 | +180,98 |
| 2019 | 18 | 76,69 | −520,13 |
| 2020 | 43 | 121,51 | −153,52 |
| **2018–2020** | **86** | **277,68** | **−164,22** |
| 2021 | 37 | 121,50 | −71,18 |
| 2022 | 47 | 85,38 | +605,52 |
| 2023 | 46 | 141,11 | −420,53 |
| **2021–2023** | **130** | **347,99** | **+37,94** |

Còn hụt 1.164,22 / 962,06 USD/năm so với mốc 2% trên sổ 50k.
Cùng phép tính phí, chỉ IVV đạt +106,57 / −185,89 USD/năm,
còn luôn BUY đạt −143,22 / −418,42 USD/năm. Cả ba chuỗi
được cộng lại đúng lượng commission trên mẫu so chung, nên
khoảng cách PnL giữa chúng giữ nguyên.

Bộ tính Decimal riêng kiểm lại 284 hướng giữ nguyên, 279
phép cộng đủ mốc và 216 chỉnh phí. Lưu trong thư mục bằng chứng
ở trên. `session-attribution-registration.md` SHA256
`25f692b5a1ffb63aa0a74c751a14f87b12a26600b072e11849563beb28e61911`,
`session-attribution.json.zst` SHA256
`d16f92e7420b31fd0e37097cbcfda30b5ab3648c41e3376f32d8634365a4077d`.
Giữ `BASE_GUARD` ở `NOT_QUALIFIED`. Chỉ dùng giá 2018–2023.

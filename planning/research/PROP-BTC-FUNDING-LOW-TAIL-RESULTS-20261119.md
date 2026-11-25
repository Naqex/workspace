# BTCUSD · Funding nhóm thấp và lợi nhuận sau 24 giờ

**Gác ứng viên ở Stage-0.** Trong ba năm đủ dữ liệu 2021–2023, lợi suất
thô sau stress trung bình **+50,37 bp** trên 198 tín hiệu có giá, còn
sổ sau cổng phí và giới hạn một vị thế chỉ giữ **48 lệnh**, lỗ
**171,97 USD**. Năm 2020 sau warm-up lãi **1.209,70 USD**, tập trung
vào vài đợt. Không năm nào trong ba năm đầy đủ đạt 1.000 USD. Trạng thái
**ECONOMIC_FAIL + CADENCE_OR_SAMPLE_SHORTFALL** cho ứng viên theo lịch
và cách sizing đã khóa. BASE_GUARD giữ NOT_QUALIFIED.

## Quy tắc, nguồn và khả năng chuyển sản phẩm

Ở mỗi kỳ Binance BTCUSDT perpetual, xếp funding đã thanh toán so với
các kỳ trong 180 ngày ngay trước đó. Percentile đếm mỗi mức thấp hơn
là 1 và mỗi mức bằng nhau là 0,5, chia số kỳ trước. Tín hiệu BUY khi
percentile ≤10%. Phải có đủ 180 ngày từ đầu nguồn và tối thiểu
300 quan sát, theo cách khóa lịch sử chặt hơn warm-up số mẫu của bài.
Bài báo nêu mức hồi +0,506% trên spot Binance trong 24h tính ngay từ
settlement. Mô hình này dùng mức đó để đặt giả thuyết. BUY và 24h đã
được chọn dựa trên bài đăng tháng 8/2026 có mẫu tới 2026. Đây là kiểm
tra chuyển sản phẩm và chi phí trên lịch sử đã phơi nhiễm theo cơ chế.
[Bài báo Memon và cộng sự, §3](https://www.aijmr.com/papers/2026/4/1493.pdf).

Nguồn funding có **4.721/4.721** kỳ trên lưới 8h, từ 10/09/2019 08:00
đến 31/12/2023 16:00 UTC. Đoạn 2019 đến từ REST với start/end rõ, do
ZIP 2019 trả 404. 48 ZIP tháng 2020–2023 khớp SHA256 do Binance phát
hành. Timestamp lệch tối đa 47 ms so với mốc chuẩn. Bắt đầu xếp hạng
08/03/2020 08:00 UTC, mỗi cửa sổ có 540 kỳ trước. Năm 2018 trước
nguồn instrument, 2019 chỉ dùng warm-up. Không có số PnL cho hai năm đó.
[Funding API](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Get-Funding-Rate-History) ·
[Kho Binance](https://data.binance.vision/?prefix=data/futures/um/monthly/fundingRate/BTCUSDT/).

Giá dùng 52.584 H1 đã niêm phong của Bitstamp BTC/USD. Vào H1 Open
kế tiếp sau mốc settlement, gồm chờ một giờ với settlement đúng giờ.
Khung vào thứ Hai–thứ Năm UTC. Thoát đúng +24h, tối đa một vị thế,
cho phép mở lệnh mới sau khi đóng ở cùng timestamp. H1 Open là proxy.
Lịch sử settlement chưa xác minh độ trễ khi công bố rate. Stop tự nhiên
là đáy ngày UTC vừa đóng trừ 0,01 USD. Nếu Open đã ở bằng/thấp hơn stop,
bỏ cơ hội. Stop chưa kích hoạt trong markout. Max 5 BTC, cap 12% ma sát
stress so với SL, risk 150 USD gồm phí dự phòng, ký quỹ 1:1 trên sổ
50.000 USD, lot bước 0,01 BTC. Công thức và giá kế thừa nghiên cứu BTC cũ.
[Sổ Bitstamp và sizing gốc](PROP-BTC-DAILY-MOMENTUM-AND-VIX-CURVE-RESULTS-20261118.md).

Commission tham chiếu 0,0325% giá trị ở mỗi chiều. Ngoài commission,
reference trừ 5 bp spread+trượt cả vòng và 5 bp qua đêm. Stress trừ
15 + 15 bp. Mỗi vị thế đi qua một nửa đêm Prague trong mô hình.
Biểu phí lịch sử, spread khớp, swap thực tế và phiên CFD đúng tài khoản
chưa xác minh. Funding perp chỉ tạo tín hiệu, tiền funding perp bằng 0
trong sổ BTCUSD. [Biểu phí FTMO công bố tháng 7/2025](https://ftmo.com/en/blog/trading-updates/trading-update-24-jul-2025/).

## Phễu và kết quả tiền

“Đợt” là chuỗi các kỳ funding liên tiếp nằm trong nhóm thấp. Bảng
đếm đợt chạm mỗi năm. Tín hiệu thô còn cửa nắm giữ chồng nhau, lệnh
nhận trong sổ một vị thế thì không chồng nhau về thời gian.

| Năm | Xếp hạng | Kỳ nhóm thấp / số đợt | Theo lịch vào / có giá | Funding thật sự âm trong nhóm theo lịch | Qua SL–phí–lot trước overlap | Lệnh nhận / số đợt |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2020 từ 08/03 | 896 | 86 / 28 | 50 / 50 | 50/50 | 27 | 17 / 15 |
| 2021 | 1.095 | 99 / 33 | 46 / 46 | 34/46 | 25 | 14 / 12 |
| 2022 | 1.095 | 159 / 77 | 99 / 99 | 88/99 | 34 | 22 / 21 |
| 2023 | 1.095 | 96 / 61 | 53 / 53 | 53/53 | 14 | 12 / 12 |
| **2021–2023** | **3.285** | **354 / 171** | **198 / 198** | **175/198** | **73** | **48 / 45** |

Qua cả kỳ, 440 sự kiện nhóm thấp, 389/440 thật sự âm (88,4%). Theo
lịch vào, 225/248 âm (90,7%). Trong 65 lệnh nhận, 61 âm (93,8%).
Tất cả sự kiện đủ lịch và lệnh nhận đều có giá hai đầu. Phễu đầy đủ
2021–2023 loại 29 ở geometry, 96 ở cap, 25 do trùng cửa đang giữ.
2020 tương ứng 7 / 16 / 10. Retention trước overlap ở ba năm đủ dữ
liệu lần lượt 54,3%, 34,3%, 26,4%; ngưỡng đã khóa là 50%.

| Năm | Gross thô / net thô stress, bp/lượt | Gross USD lệnh nhận | Commission | Spread + trượt stress | Swap proxy stress | Net reference / stress | Stress USD/lệnh |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2020 từ 08/03 | +316,26 / +279,66 | +1.358,99 | 26,95 | 61,17 | 61,17 | +1.291,26 / +1.209,70 | +71,16 |
| 2021 | +73,95 / +37,43 | −55,17 | 16,43 | 37,96 | 37,96 | −96,90 / −147,51 | −10,54 |
| 2022 | +111,56 / +75,03 | +166,93 | 42,22 | 97,30 | 97,30 | +59,85 / −69,88 | −3,18 |
| 2023 | +52,06 / +15,54 | +196,65 | 26,98 | 62,12 | 62,12 | +128,25 / +45,42 | +3,78 |
| **2021–2023** | **+86,90 / +50,37** | **+308,41** | **85,63** | **197,37** | **197,37** | **+91,20 / −171,97** | **−3,58** |

Ở cùng cách lấy trung bình đơn giản 2021–2023, stress còn **+50,37 bp**
từ 198 tín hiệu thô, **+10,85 bp** sau khi bỏ 29 Open đã ở dưới stop,
**−39,68 bp** trên 73 tín hiệu giữ được sau cap và lot, rồi **−19,54 bp**
trên 48 lệnh nhận sau overlap. Sau khi tính trọng số cỡ vị thế,
48 lệnh có gross **+23,44 bp** và net stress **−13,07 bp**, tương
đương **−57,32 USD/năm**. Commission-only và reference trên cùng
48 lệnh chỉ đạt **+74,26 và +30,40 USD/năm**. Năm 2023 raw net
15,54 bp cũng thấp hơn chi phí stress 36,52 bp, hụt ngưỡng raw markout.

Hòa vốn quy đổi theo giá trị vào lệnh thực có là tổng gross **23,44 bp**
cho ba năm đủ dữ liệu. Trừ commission rồi còn **16,93 bp** cho tổng
spread, trượt và phí giữ qua đêm. Mô hình stress tính 30 bp ở phần này.
Với đúng 16 lệnh/năm và cỡ vị thế đã đo, để đạt **1.000 / 5.000 USD/năm**
cần trung bình net **62,50 / 312,50 USD/lệnh**, tức cần thêm
**241 / 1.153 bp** so với mức stress đang có. Số năm 2020 giữ theo
kỳ quan sát từ tháng 3.

## So với mua ngoài tín hiệu và bỏ các đợt thắng lớn

Mỗi lệnh được so với trung bình các cửa BUY 24h cùng quý, thứ, giờ UTC,
qua cap và lot, nằm ngoài các cửa funding nhóm thấp theo lịch. Áp cùng
giá trị vào lệnh và cách tính phí. Giữ riêng các lệnh không có đối
chứng đủ điều kiện. Drift là trung bình BTC từ 00:00 tới 00:00 hôm sau
trên mọi ngày có giá trong phạm vi. Đối chứng này đo lợi thế tăng thêm
trên tập ghép, còn các đợt thị trường vẫn có thể phụ thuộc nhau.

| Năm | Ghép được | Stress sổ ghép / đối chứng, USD | Chênh lệch USD | BTC drift 24h, bp | Net toàn sổ bỏ top 3 đợt, USD |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2020 từ 08/03 | 15/17 | +677,97 / −20,04 | +698,01 | +52,54 | +416,59 |
| 2021 | 14/14 | −147,51 / −87,73 | −59,78 | +21,77 | −147,51 |
| 2022 | 21/22 | −101,85 / −445,62 | +343,77 | −22,49 | −574,22 |
| 2023 | 9/12 | +148,05 / −111,36 | +259,41 | +28,38 | +45,42 |
| **2021–2023** | **44/48** | **−101,30 / −644,70** | **+543,40** | **+9,20** | **−676,31** |

Ba đợt stress lãi cao nhất bắt đầu 27/02/2022, 23/03/2020 và
17/03/2020, đóng góp **504,34 / 469,21 / 323,90 USD**. Bỏ ba đợt
khỏi tổng cả phần 2020 và 2021–2023, sổ chuyển từ **+1.037,74 USD**
sang **−259,72 USD**. Giai đoạn ba năm đầy đủ có chênh dương với
đối chứng trên 44 lệnh ghép, nhưng cả sổ stress vẫn lỗ và 2021 còn
thua đối chứng. Giữ bằng chứng này như tín hiệu hồi có điều kiện,
chưa có cơ sở đầu tư tiếp vào stop replay hoặc ghép tài khoản.

Đối soát bằng Fraction độc lập cho 4.181 xếp hạng, 248 markout và
65 lệnh nhận. Kiểm timestamp, thứ tự vị thế, lot, từng thành phần phí
và các cửa đối chứng. Dữ liệu và công cụ tái hiện nằm ở
ai-engine-jobs/prop-btc-funding-low-tail-20261119 trên ổ E.
Manifest lưu SHA256 bản đăng ký, raw, kết quả Zstandard và nguồn
Bitstamp. Dữ liệu giá và funding đã dùng đều kết thúc năm 2023.

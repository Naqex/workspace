# EURUSD · BUY trước tin Mỹ sau ngày đấu giá Treasury

**Dừng ở Stage-0.** Trên Development 2018–2023 có **190 cơ hội theo lịch
lưu trữ, 177 có đủ giá và 174 qua bộ lọc** khi tính rollover FX theo giờ
New York. Mỗi năm chỉ có 26–37 cơ hội trước lọc, dưới mức 40 đã đăng ký.
Sau phí stress và quy đổi khối lượng, hai cụm đều âm, **−10,28 USD**
(2018–2020) và **−54,35 USD** (2021–2023). Kết luận `ECONOMIC_FAIL`,
`CADENCE_OR_SAMPLE_SHORTFALL`, `DATA_PATH_INCOMPLETE` và
`PROP_UNMEASURED`. Danh mục tiếp tục `BASE_GUARD · NOT_QUALIFIED`.

## Giả thuyết và mẫu kiểm

Krohn và Vala ghi nhận ngoại tệ thường tăng so với USD trong ngày có tin
kinh tế Mỹ nếu trước đó có đấu giá Treasury. Mức khoảng 8 bp thuộc danh
mục ngoại tệ và cửa sổ cả ngày của nghiên cứu. Pilot này chỉ đo EURUSD
**trước 08:30 ET**. Luật cố định BUY ở 17:15 New York ngày đấu giá và thoát
08:15 hôm sau nếu hôm sau có CPI, Employment Situation hoặc Initial
Jobless Claims phát hành 08:30. Chiều BUY được khóa trước. Lịch đấu giá
nominal coupon 2, 3, 5, 7, 10, 20, 30 năm lấy từ sổ Treasury đã lưu.
Chỉ xét ngày đã thông báo đấu giá trước đó và đã qua giờ đóng nhận giá
đấu. Đây là giả thuyết về lịch, độc lập với luật cũ dùng tỷ lệ bid-to-cover.
[Paper Krohn và Vala](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5207418) ·
[Sổ Treasury trước đây](PROP-EUR-CLOCK-AND-TREASURY-AUCTION-RESULTS-20261118.md).

- BLS có 72 CPI và 72 Jobs. DOL có 313 Initial Claims. Sau khi gộp
  những thông cáo trùng ngày còn **437 ngày**. Loại 7 ngày không có
  hai ngày làm việc liền nhau, 3 ngày vướng cổng lịch Good Friday
  của repo và 1 ngày thiếu giờ đóng đấu giá đủ điều kiện. Còn 190 ngày
  có đấu giá và 236 ngày đưa vào tập ghép đối chứng. Trong 190 ngày,
  có 130 Claims đơn, 40 CPI đơn, 18 Claims trùng CPI, 2 Jobs đơn.
- BLS trả 403 ở đường tải trực tiếp nên lấy văn bản từ bản chuyển đổi của
  chính các trang lịch BLS và đối chiếu với trang chính thức. DOL dùng
  mục lục ETA chọn từng năm, rồi xác minh ngoại lệ. Ngày 03/01/2019 nằm
  trong tệp mang tên 010318, còn 17/10/2019 bị thiếu link trong mục lục.
  Cả hai ngày và mốc 08:30 được lấy từ tiêu đề thông cáo. Phát hiện chín
  ngày Claims chuyển khỏi thứ Năm trong 2018–2023, dùng ngày phát hành
  trong lịch thay vì ngày cuối tuần của số liệu. [Lịch BLS](https://www.bls.gov/bls/archived_sched.htm) ·
  [Lịch và archive DOL](https://oui.doleta.gov/unemploy/archive.asp) ·
  [Thông cáo 03/01/2019](https://oui.doleta.gov/press/2019/010318.pdf) ·
  [Thông cáo 17/10/2019](https://www.dol.gov/sites/dolgov/files/OPA/newsreleases/ui-claims/20191832.pdf).
- Giai đoạn shutdown cuối 2018–đầu 2019, BLS xác nhận lịch của mình
  vẫn tiếp tục. Hai ngày JOBS trúng điều kiện (10/01/2020 và 10/03/2023)
  có lịch ngày ghi trong thông cáo tháng trước. Mốc 08:30 của ngày
  10/03/2023 cũng được ghi trước. Lịch lưu trữ thiếu bản theo thời điểm
  quyết định cho các ngày còn lại. Báo **190** là tổng có điều kiện và
  chưa xác nhận số lệnh lịch sử thực thi. [Thông báo shutdown của BLS](https://www.bls.gov/bls/does-the-lapse-of-appropriation-for-some-federal-agencies-impact-bls-data-or-release-dates.htm) ·
  [Lịch đã nêu ngày 10/01/2020](https://www.bls.gov/news.release/archives/empsit_12062019.htm) ·
  [Lịch đã nêu ngày 10/03/2023](https://www.bls.gov/news.release/archives/empsit_02032023.htm).

## Hai đồng hồ và chi phí

Khớp theo tick native, Ask vào và Bid ra, báo giá đầu trong 60 giây.
Chỉ đọc lát EURUSD đã lưu của sáu năm. Báo cáo có 13/190 ngày thiếu giá
vào trong dung sai, gồm 1 ngày năm 2021, 3 ngày năm 2022 và 9 ngày
năm 2023. Cả 13 có giá thoát. Bốn ngày đối chứng cũng thiếu giá vào.
Các báo giá kế tiếp đến sau 62–606 giây trên nhóm thiếu, có cả giờ mùa
hè và mùa đông. Giữ nguyên dung sai và trạng thái thiếu. Lịch nghỉ
là lịch mô hình đã khai báo của repo, chưa có lịch tài khoản đích xác
nhận lịch sử.

- **FX theo FTMO.** FTMO ghi rollover FX lúc **17:00 New York**, theo nửa
  đêm của máy chủ MetaTrader. Giữ từ 17:15 đến 08:15 ở ngày liền sau
  đi qua **0 rollover** theo quy ước này, kể cả tuần Mỹ và châu Âu đổi
  DST lệch nhau. Commission tham chiếu **0,7 pip** mỗi vòng. Stress thêm
  **0,2 pip** trượt giá mỗi vòng. Spread đã nằm trong Ask/Bid. Lấy 2×
  Wilder ATR20 trên nến D1 UTC đã đóng để quy mô stop, risk 125 USD trên
  vốn danh nghĩa 50.000 USD, lot bước 0,01, cổng 12%. Stop chỉ dùng cho
  quy mô và chi phí dự kiến. [Giờ rollover FX của FTMO](https://ftmo.com/en/blog/market-conventions-and-rollovers-on-nzd/) ·
  [Cập nhật DST và giờ reset lỗ ngày từ FTMO](https://ftmo.com/en/blog/trading-updates/trading-update-09-mar-2023/).
- **Giả định bảo thủ đã khóa ban đầu.** Nửa đêm Prague là đồng hồ reset
  lỗ ngày. Nếu dùng mốc này để giả lập thu swap –40 USD/lot, 47 cơ hội
  có một khoản tài trợ ngày và 143 chịu hệ số ba, tính theo thứ Tư NY.
  Theo giả định đó, 156 lượt qua cổng, tổng **−1.031,63 USD chuẩn** và
  **−1.052,23 USD stress**, gồm **−996,00 USD swap**. Bỏ khoản funding
  trên đúng 156 lượt và lot cũ còn **−56,23 USD stress**. Bảng tiếp theo
  tính lại cổng phí và lot với đúng đồng hồ FX, giữ nguyên giá, tín hiệu
  và giờ. Thông số của từng tài khoản lịch sử chưa được xác nhận.

## Kết quả theo năm

Markout là trung bình pip trên các ngày đủ hai giá. Cột USD là tổng sau
khi định lại lot theo giới hạn risk. Cả USD chuẩn lẫn stress theo đồng hồ
FX New York.

| Năm | Ngày thô / tuần | Có giá / qua cổng | Gộp pip | Sau spread pip | Net stress pip | USD chuẩn | USD stress | R/lượt cần để góp 1.000 USD/năm |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2018 | 27 / 23 | 27 / 24 | +8,31 | +7,57 | +6,67 | +3,30 | +0,02 | 0,333R |
| 2019 | 26 / 21 | 26 / 26 | −3,47 | −4,22 | −5,12 | −143,58 | −148,88 | 0,308R |
| 2020 | 30 / 25 | 30 / 30 | +8,07 | +7,39 | +6,49 | +142,96 | +138,58 | 0,267R |
| 2021 | 35 / 28 | 34 / 34 | −0,57 | −1,54 | −2,44 | −39,30 | −44,44 | 0,235R |
| 2022 | 37 / 31 | 34 / 34 | −5,89 | −7,34 | −8,24 | −176,91 | −180,81 | 0,235R |
| 2023 | 35 / 30 | 26 / 26 | +11,92 | +10,43 | +9,53 | +174,62 | +170,90 | 0,308R |
| **Tổng** | **190 / 158** | **177 / 174** | **+2,64** | **+1,62** | **+0,72** | **−38,91** | **−64,63** | |

Ba tín hiệu năm 2018 thiếu warmup. Stop trung vị theo năm 111,55–202,70
pip. Tỷ lệ trung vị phí kế hoạch trên stop trung vị dưới mô hình FX là
1,07–2,22%. Trên sổ có lot, gross midpoint đạt **+178,24 USD**, sau spread
**+51,11 USD** và sau phụ phí stress **−64,63 USD**. Bình quân pip thô
dương 0,72 nhưng tổng bằng tiền âm do lot khác nhau theo ATR. Tần suất
thô hụt ở cả sáu năm. 13 ngày thiếu giá vào đưa độ phủ chung xuống
93,2%. Năm thấp nhất là 2023, 26/35 (74,3%).

## Lợi thế so với đối chứng và độ tập trung

Ghép từng ngày có đấu giá với ngày có đúng bộ loại tin, cùng thứ,
cùng năm, ưu tiên cùng quý rồi gần nhất về lịch. Cho phép dùng lại ngày
đối chứng. Khóa 141 đối chứng ghép trước khi đọc giá, trên 109 ngày phân
biệt. Có 128 cặp giá đủ và 126 cặp có lot của cơ hội chính. Cùng một lot
được dùng cho cả hai vế. Dòng dưới dùng chi phí theo đồng hồ FX.

| Cụm | Thô / có giá / qua cổng | Net stress | USD/năm | Bỏ 3 tuần lãi nhất | So sánh ghép, BUY có đấu giá / BUY không đấu giá / chênh lệch |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2018–2020 | 83 / 83 / 80 | −10,28 USD | −3,43 | −217,82 | 62 cặp · −173,73 / −28,45 / **−145,28 USD** |
| 2021–2023 | 107 / 94 / 94 | −54,35 USD | −18,12 | −176,32 | 64 cặp · −51,32 / −348,35 / **+297,03 USD** |

Ba tuần mạnh nhất toàn kỳ là 2020-W09 (+96,00), 2020-W37 (+58,24),
2019-W41 (+53,30 USD). Bỏ ba tuần đó, kết quả **−272,17 USD**. Tổng ghép
hơn đối chứng **151,75 USD**, nhưng lợi thế đổi dấu giữa hai cụm và nhóm
cơ hội chính vẫn âm. Cụm đầu chỉ góp −3,43 USD/năm, cụm sau −18,12 USD/năm
so với mục tiêu 1.000 USD/năm. Gác luật hiện tại trước kiểm đường chạm
stop, tài khoản 10k/25k và Reward.

## Đối soát

Job `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/prop-eur-auction-prenews-20261119/`.
Card và census có SHA256 lần lượt
`8da95df4c4764a3c088319e6ce470617114280b49b306fee6ded45afb68070c2` và
`0183cadc0105276e175dd22d3e5ba98c191c4a7d1b15ab3f3e0c66bdd3d80cbd`.
Đọc 598 tick tại 598 mốc tìm kiếm, 581 đúng dung sai, và 2.234.862 M1
trong Development để tính ATR. Đối chiếu 6 SHA đầu ra, 13 SHA nguồn lịch
và tiền/giờ của cả 177 cơ hội định giá được. Giá 2024–2026 giữ đóng.

- `manifest.json` SHA256 `d2b3aabcd0e67d63e6d29466c4332581e238e8b640460058ce6dad0c491f50ff`.
- `clock-accounting-audit.json` SHA256 `256cc67ce881650b3b4e06e59432871dab834fc9eebd1b35502a8a66428b3968`
  lưu phép hạch toán lại trên giá đã khóa và bằng chứng lịch bổ sung.

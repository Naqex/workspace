# WTI F1 − F4 · chẩn đoán trên cùng một hợp đồng futures

**Gác tìm thêm feed chi phí cho luật này.** Tín hiệu chỉ đạt khoảng
**+0,70 USD/thùng trước phí** ở mỗi cụm, thua đối chứng luôn BUY
trong 2021–2023, và hụt mốc đóng góp 1.000 USD/năm ở cả hai ví dụ
sizing của card. Kết quả định giá CFD/FTMO vẫn chưa đo.
[Card và kiểm nguồn CFD](PROP-WTI-CURVE-CFD-ADMISSION-20261118.md).

## Cách đo

Giữ dấu F1 − F4 ở settlement đầu tiên mỗi tháng, BUY khi dương,
SELL khi âm, đứng ngoài khi bằng 0. Ngày vào là phiên settlement
kế tiếp, ngày ra là phiên settlement đầu tiên tháng sau. Chỉ đổi giờ
định giá từ **11:00 New York** của card sang settlement, thường gần
**14:30 New York**. Settlement CME là giá tham chiếu, có thể được suy
từ spread lịch kỳ hạn, và không xác nhận giá khớp.

Khóa **tháng/năm giao cụ thể của F2 tại entry**. Mỗi endpoint được
ánh xạ theo thứ tự tháng giao và ngày hết hạn NYMEX. Trong cả 71
cửa sổ, tháng đã chọn hiện ở cột F1 tại exit theo lịch, vì cả hai
điểm đều nằm đầu tháng và qua đúng một kỳ hết hạn. Không nối mức
F2 ngày vào với F2 ngày ra. Mỗi phép đối chứng luôn BUY giữ cùng
tháng giao, cùng cửa sổ và cùng một thùng.
[EIA định nghĩa F1–F4](https://www.eia.gov/dnav/pet/tbldefs/pet_pri_fut_tbldef2.asp) ·
[CME kỳ hạn](https://www.cmegroup.com/trading/files/WTI-Fact-Card.pdf) ·
[CME settlement](https://www.cmegroup.com/trading/energy/files/NYMEX_Energy_Futures_Daily_Settlement_Procedure.pdf).

## Kết quả trước phí (USD/thùng)

Mỗi ô kết quả ghi **cộng dồn / bình quân mỗi cửa sổ có tín hiệu**.

| Tập | Cửa sổ đo / đăng ký | BUY / SELL | Theo tín hiệu | Luôn BUY | Phần hơn luôn BUY |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2018–2020 | 34/35 | 16 / 18 | +23,76 / +0,699 | −26,20 / −0,771 | +49,96 / +1,469 |
| 2021–2023 | 35/35 | 32 / 3 | +24,76 / +0,707 | +41,44 / +1,184 | −16,68 / −0,477 |
| Toàn kỳ | 70/71 | 48 / 22 | +46,34 / +0,662 | +17,42 / +0,249 | +28,92 / +0,413 |
| Bỏ mọi cửa sổ giữ vị thế chạm 2020 | 57/58 | 46 / 11 | +37,16 / +0,652 | +41,72 / +0,732 | −4,56 / −0,080 |

Một cửa sổ tháng 08/2019 đứng ngoài vì spread bằng 0, không thiếu
giá. Cửa sổ tháng 12/2020 đến 04/01/2021 góp −2,18 USD/thùng theo
tín hiệu và +2,18 USD/thùng ở đối chứng. Cửa sổ này chỉ nằm trong tổng
toàn kỳ và phân tích 2020, không vào một trong hai cụm.

### Lệnh lớn nhất, 2020 và lỗ đuôi đã quan sát

- **Lệnh lớn nhất là SELL kỳ giao 05/2020.** Giá từ 47,33 ngày
  03/03 xuống 20,31 ngày 01/04, lãi +27,02 USD/thùng và hơn BUY
  +54,04 USD/thùng. Đây cũng là lệnh đóng góp nhiều nhất vào phần
  vượt đối chứng. Bỏ lệnh này, toàn kỳ còn **+19,32 USD/thùng
  gross và −25,12 USD/thùng so với BUY**. Cụm 2018–2020 còn
  −3,26 USD/thùng gross và −4,08 USD/thùng so với BUY. Bỏ lệnh
  thắng lớn nhất của cụm 2021–2023 còn +8,04 USD/thùng gross, vẫn
  kém BUY 16,68 USD/thùng.
- **13 cửa sổ chạm năm 2020** đóng góp +9,18 USD/thùng gross
  và +33,48 USD/thùng phần hơn BUY, lớn hơn phần hơn BUY của toàn
  kỳ. Cửa sổ đi qua 20/04 giữ **kỳ giao 06/2020**, giá settle
  **20,43 USD/thùng** hôm đó. Giá âm **−37,63 USD/thùng** thuộc
  kỳ giao 05/2020 đã thoát từ 01/04. Cửa sổ tháng 04 góp
  +8,27 USD/thùng theo tín hiệu và +16,54 USD/thùng hơn BUY. Bỏ
  riêng cửa sổ này vẫn hơn BUY +12,38 USD/thùng toàn kỳ. Bỏ toàn
  bộ cửa sổ chạm 2020 thì phần hơn BUY thành âm.
- **Lỗ khi đóng lớn nhất** là −12,71 USD/thùng ở cụm đầu và
  −16,87 USD/thùng ở cụm sau. Đây cũng là hai mức bất lợi lớn nhất
  quan sát tại các lần settlement trong từng cụm. Có 9/70 đường
  giữ thiếu một mốc định giá theo quy tắc bảo thủ khi hai cách
  dựng lịch hết hạn không đồng ý. Cả 70 lệnh có hai endpoint.
  Lỗ đuôi intraday và lỗ thực thi chưa đo.
  [EIA về hợp đồng tháng 05/2020](https://www.eia.gov/Todayinenergy/detail.php?id=43875).

## So với mục tiêu 1.000 USD/năm

Dùng risk danh nghĩa 150 USD của card để tính ngược. Hai ví dụ
giả sử mức dừng 5 hoặc 10 USD/thùng, tương ứng 30 hoặc 15 thùng
lý thuyết, chưa xét lot, margin, stop fill hay đường giá CFD.

| Cụm | Cần gross tối thiểu ở chi phí 0, USD/thùng (30 / 15 thùng) | Gross quan sát | Ngân sách phí để vẫn đạt mục tiêu, USD/thùng (30 / 15 thùng) |
| --- | ---: | ---: | ---: |
| 2018–2020 · 34 lệnh | 2,94 / 5,88 | 0,699 | −2,24 / −5,18 |
| 2021–2023 · 35 lệnh | 2,86 / 5,71 | 0,707 | −2,15 / −5,01 |

Ở 34 lệnh, mục tiêu cần 88,24 USD ròng/lệnh. Ở 35 lệnh cần
85,71 USD. Ngân sách phí âm nghĩa là ngay cả ở phí 0, gross
tham chiếu vẫn hụt mốc. Nếu ngoại suy cơ học theo gross này, cần
126,26 hoặc 121,16 thùng mỗi vị thế trước phí. Với 150 USD risk,
mức dừng tương ứng chỉ khoảng 1,19 hoặc 1,24 USD/thùng, chưa có
bằng chứng là hợp cấu trúc. Các phép tính là thước đo quy mô,
không phải số lot, PnL tài khoản, hoặc cận trên cho CFD.

**Quyết định:** lợi thế tương đối không lặp lại ở cả hai cụm và
gross hụt quy mô trong hai ví dụ đã khóa. Gác đúng luật này ở
bước chẩn đoán. Bid/Ask đích, khoản điều chỉnh đổi tháng, swap và
kết quả CFD vẫn chưa đo. `BASE_GUARD` giữ `NOT_QUALIFIED`.

## Nguồn, chỉnh lịch và đối soát

Dùng API công khai EIA theo chính sách sử dụng của nguồn, server
lọc `2018-01-01` đến `2023-12-31` trước khi tải. Hai trang có
6.100 hàng, tương ứng 1.525 nhãn ngày × bốn tenor. Không đọc tập
giá 2024–2026. Artifact nguồn giữ riêng, kèm checksum hai phản hồi.
[EIA API](https://www.eia.gov/opendata/documentation.php) ·
[Chính sách sử dụng](https://www.eia.gov/opendata/terms-of-service.php).

Đối soát phát hiện **17 nhãn nghỉ lễ 2018–2019** lặp đúng cả bốn
giá từ phiên trước. Trong đó ba nhãn rơi đúng mốc đầu tháng.
Phép đo cuối dùng **1.508 phiên settlement thực** sau bỏ nhãn
carry-forward. Giữ bản chạy đầu và nhật ký chỉnh nguồn riêng.
Quy tắc chọn phiên settlement, dấu tín hiệu, tenor và đủ 71 cửa
sổ giữ theo bản đăng ký. Việc chỉnh lịch làm tổng gross từ
+48,06 thành +46,34 USD/thùng và không đổi quyết định.
[CME Labor Day 2018](https://www.cmegroup.com/tools-information/holiday-calendar/files/2018-labor-day-advisory.pdf) ·
[CME New Year 2019](https://www.cmegroup.com/tools-information/holiday-calendar/files/2019-new-years-advisory.pdf) ·
[CME Labor Day 2019](https://www.cmegroup.com/tools-information/holiday-calendar/files/2019-labor-day-advisory.pdf).

- Private run: `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/prop-wti-curve-futures-20261118/`.
- Protocol trước PnL: `0c487d24629b20a935b395015ac1128ec088fe611f46d2629f6bed78bd3cf7c9`.
- SHA256 nguồn nén: `ec31550d4ed486a9cc39145a3d24376d1d543e0fb40240a5f559e3e434ed7dd9`.
- SHA256 kết quả nén: `053c4fcc6dee125018dbeab69ea8b555e1dce3d9c6d5f855ade17b8a86859f7f`.
- `verify-settlement.py` kiểm 71 định danh kỳ giao, 70 lệnh bằng
  số nguyên cent, ba bảng tổng và case hợp đồng kỳ giao 06/2020.

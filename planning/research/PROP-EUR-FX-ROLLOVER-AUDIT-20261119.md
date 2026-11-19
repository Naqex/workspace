# EURUSD · hồi cứu ảnh hưởng của đồng hồ rollover

**Không có ứng viên được mở lại. Các kết quả Reward mô phỏng V15,
V4 và BASE_GUARD trong 2018–2023 giữ nguyên theo phép đổi đồng hồ
EURUSD này.** Catalogue13 giữ nguyên tiền swap. F2 bị bỏ sót 32,00 USD
phí trên một lệnh. RSI37 thoát theo luật bot từng bị tính thừa 54,00 USD
trên một lệnh tick. Hai cụm F2 và RSI37 vẫn âm sau khi tính lại.

## Phạm vi và hợp đồng tính phí

Đối chiếu **22:00 UTC** đã dùng trong từng sổ với phiên bản tham chiếu
`EURUSD_NY1700_WEEKDAY_WED3_V1`. Phiên bản này dùng 17:00 New York,
thứ Hai đến thứ Sáu, thứ Tư hệ số ba. 17:00 New York là 22:00 UTC khi Mỹ
dùng giờ mùa đông và 21:00 UTC khi Mỹ dùng giờ mùa hè. Chuyển múi giờ
theo ngày New York, kể cả khi Mỹ và châu Âu đổi giờ lệch nhau.
Nửa đêm Prague tiếp tục là mốc reset lỗ ngày. Phí tính nếu
`entry < rollover <= exit`, theo thứ tự ghi phí trước xử lý quote tại
mốc đó. Trạng thái mở ở cutoff tính qua thời điểm cuối trước cutoff.
[Giờ rollover FX theo FTMO](https://ftmo.com/en/blog/market-conventions-and-rollovers-on-nzd/) ·
[Giờ MT5 và reset Prague theo FTMO](https://ftmo.com/en/blog/trading-updates/trading-update-09-mar-2023/).

- Giữ side, giá Bid/Ask, entry/exit, spread, commission, slippage và lot.
  Giữ nguyên mức swap của từng sổ. Catalogue13 chuẩn trừ 9,30 USD/lot
  BUY và cộng 0,31 USD/lot SELL mỗi đêm tính phí, stress trừ 20/20 USD.
  F2 và RSI37 trừ 40/40 USD. Giữ cách làm tròn mỗi sự kiện của Catalogue13.
  Một lần thứ Tư có trọng số ba đêm trong cột lot-đêm.
- Các phí này là giả định đóng băng và đã được khai báo trong nguồn.
  Mốc NY là chuẩn tham chiếu, chưa xác nhận swap lịch sử của tài khoản
  đích. Có 23 ngày trùng ngày nghỉ liên bang Mỹ, Good Friday hoặc lịch
  cuối năm trong danh sách sự kiện dời giờ. Cả 23 chỉ dời thời điểm,
  không thêm/bớt đêm nào trong sổ so. Giữ lịch ngày nghỉ của từng sổ và
  đánh dấu lịch swap broker chưa xác minh. [Lịch nghỉ liên bang Hoa Kỳ](https://www.opm.gov/policy-data-oversight/pay-leave/federal-holidays/).
- Đây là thay đồng hồ trên sổ đã có. Nguồn cũ ghi rõ 22 UTC là proxy nên
  giữ artifact và code lịch sử. Chưa thay clock dùng chung cho vàng, chỉ
  số, crypto hay cặp khác. Phần kết quả V4 giữ giới hạn và trạng thái
  đóng đã công bố.

## Kết quả trên cùng tập lệnh và lot

Số âm ở cột swap là chi phí. “Thừa / thiếu” đếm vị thế có ít nhất một
ngày bị thừa hoặc thiếu theo đồng hồ cũ, trước khi bù hai phía. Tổng
Catalogue13 là **năm sổ 10.000 USD riêng với risk 25 USD/lệnh**, gồm
phần đang mở ở cutoff. F2 và RSI37 là sổ lệnh tham chiếu **risk 150 USD**,
không quy đổi sang tài khoản 50k hoặc kết quả Challenge.

| Sổ | Lượt | Thừa / thiếu | Lot-đêm cũ → NY | Swap cũ → NY | Net cũ → NY | Quyết định |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Catalogue13 H4 SMA20/80 chuẩn 2018–2022 | 101 | 0 / 0 | 34,97 → 34,97 | −107,67 → −107,67 USD | −416,75 → −416,75 USD | Gác |
| Catalogue13 H4 SMA20/80 stress 2018–2022 | 101 | 0 / 0 | 34,65 → 34,65 | −693,00 → −693,00 USD | −999,05 → −999,05 USD | Gác |
| Catalogue13 H4 Pullback20/80 chuẩn 2018–2022 | 118 | 0 / 0 | 47,05 → 47,05 | −169,63 → −169,63 USD | −36,32 → −36,32 USD | Gác |
| Catalogue13 H4 Pullback20/80 stress 2018–2022 | 118 | 0 / 0 | 47,02 → 47,02 | −940,40 → −940,40 USD | −820,40 → −820,40 USD | Gác |
| F2 P0 2018–2023 · lệnh đã định giá | 524 | 0 / 1 | 49,74 → 50,54 | −1.989,60 → −2.021,60 USD | −43.380,90 → −43.412,90 USD | Gác |
| RSI37 native · thoát theo luật bot | 383 | 1 / 0 | 72,00 → 70,65 | −2.880,00 → −2.826,00 USD | −5.469,17 → −5.415,17 USD | Gác |
| RSI37 native · thoát +8h | 341 | 1 / 12 | 90,75 → 99,60 | −3.630,00 → −3.984,00 USD | −2.992,11 → −3.346,11 USD | Đối chứng vẫn âm |
| V15 Calibrated/Cushion, V4 Harvest, V19 BASE_GUARD | Xem chứng cứ bên dưới | 0 / 0 | 0 → 0 (EURUSD) | 0 → 0 USD (EURUSD) | Không có delta đồng hồ EURUSD | Reward lịch sử giữ nguyên trong phạm vi audit |

### Catalogue13 và giao dịch mở cuối năm

Giờ ghi swap dời sớm một giờ trong ít nhất một sự kiện của 61/101 vị
thế SMA và 70/118 vị thế Pullback. Ngày thu phí và hệ số giữ nguyên,
kể cả stop H1 chỉ biết khoảng thoát. Trong stress, BUY/SELL có
12,20/22,45 lot-đêm ở SMA và 19,15/27,87 ở Pullback. Trong phí chuẩn,
phần ghi có phía SELL là +7,22 USD và +9,15 USD. Cả hai mô hình đều giữ
nguyên các khoản ghi có đó.

SMA stress có **2 vị thế mở** tại cutoff trong năm sổ, swap đã ghi
−10,80 USD và phần equity đóng góp gồm mark sau phí +29,44 USD.
Pullback có **4 vị thế mở**, swap −60,20 USD và phần equity +209,29 USD.
Phần net của lệnh đã đóng lần lượt **−1.028,49 và −1.029,69 USD**.
Ở phí chuẩn, swap từ các vị thế còn mở lần lượt −5,01 và −28,21 USD.
Không giả định khớp đóng ở cutoff. Bộ lọc quyết định và sizing coarse
dùng mệnh giá vốn đầu năm và khoảng stop đã biết. Tiền swap chỉ đi vào
cash của sổ này. [Kết quả Catalogue13 gốc](EURUSD-CATALOGUE13-RESULTS-20261108.md).

### Thay đổi thực sự ở từng năm

| Năm | C13 SMA stress, USD | C13 Pullback stress, USD | F2 P0 USD cũ → NY | RSI37 native thoát bot USD cũ → NY | RSI37 native +8h USD cũ → NY |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2018 | −387,81 | −482,34 | −7.175,11 → −7.175,11 | −298,49 → −298,49 | +1.937,50 → +1.733,50 |
| 2019 | −429,98 | −501,66 | −4.779,86 → −4.811,86 | +90,58 → +144,58 | +77,62 → +83,62 |
| 2020 | −134,37 | +133,63 | −7.497,12 → −7.497,12 | −401,47 → −401,47 | −3.009,00 → −3.009,00 |
| 2021 | −176,82 | +110,37 | −3.636,70 → −3.636,70 | −2.423,81 → −2.423,81 | −1.488,23 → −1.488,23 |
| 2022 | +129,93 | −80,40 | −10.836,99 → −10.836,99 | −2.906,54 → −2.906,54 | −2.939,05 → −3.041,05 |
| 2023 | — | — | −9.455,12 → −9.455,12 | +470,56 → +470,56 | +2.429,05 → +2.375,05 |

- **F2.** Có 300/365 lệnh được nhận có kết quả P0 trong 2018–2020 và
  224/432 trong 2021–2023. 273 đường thiếu giữ trạng thái chưa biết.
  Lệnh BUY 13/05/2019, 0,80 lot, thoát 21:00:59,999 UTC nên phát sinh
  thêm 0,80 lot-đêm (−32 USD). 251 lệnh SELL giữ nguyên tổng swap.
  Hai cụm sau sửa là **−19.484,09 / −23.928,81 USD**, khác quỹ đạo tài
  khoản. Cổng 12% và lot ở F2 chỉ dùng cấu trúc và ma sát thực thi,
  chưa lệ thuộc swap. Kiểm riêng 1.376 cặp giá endpoint, 4 bị ghi thừa
  và 1 bị bỏ sót. Mean net của chiều đảo vẫn âm từng năm.
  [Chẩn đoán F2 và nguồn thiếu](PROP-EURUSD-F2-DIRECTION-20261119.md).
- **RSI37.** BUY 31/07/2019 mở lúc 21:00:00,025 UTC, ngay sau rollover
  thật theo mốc NY nhưng trước 22:00 UTC. Vì đó là thứ Tư, sổ cũ thu
  1,35 lot-đêm trên 0,45 lot. Hạch toán theo NY hoàn 54 USD. Trong
  nhánh +8h cũng có 8 BUY và 4 SELL bị ghi thiếu, lần lượt 7,80 và 2,40
  lot-đêm, nên tổng điều chỉnh là −354 USD. Cùng lot, nhánh thoát theo
  luật bot còn **−555,38 / −4.859,79 USD** cho hai cụm. +8h cho
  **−1.191,88 / −2.154,23 USD**. Với cùng vị thế và thứ tự entry,
  cập nhật phí dự phòng theo deadline làm đổi lot của 11 lệnh thoát bot
  và 9 lệnh +8h. Không đổi lượt nhận. Tổng sau đổi lot là
  **−5.314,58 / −3.337,60 USD** cho hai cách thoát. Hai thứ tự M1 cho
  cùng kết quả, lần lượt −6.310,01 và −4.850,97 USD sau đổi lot.
  [Sổ RSI37 đã chặn entry cuối tuần](PROP-EURUSD-RSI37-ENTRY-CALENDAR-RESULTS-20261119.md).

## Tại sao Reward trong sổ đã đo giữ nguyên

| Sổ Reward | Bằng chứng đã kiểm trên tape EURUSD | Kết luận |
| --- | --- | --- |
| V15 Calibrated/Cushion | 194 lệnh mỗi thứ tự OHLC/OLHC. 0 rollover theo cả hai mốc từ entry đến exit và từ entry đến deadline dùng trong reserve. Runner V6 có hành động swap riêng, tách với reset Prague. | Không thay cash, reserve, chuỗi pha hay Reward do đổi clock EURUSD. |
| V4 Harvest | 386 lệnh mỗi tape 2018–2021 và 236 lệnh EUR native trong Dev 2022–2023. Kiểm ghép qua đầu 2022 theo danh tính, gồm 97 lệnh EUR sau ranh trên mỗi tape ghép. Tất cả khoảng giữ và khoảng reserve đều có 0 sự kiện ở cả hai mốc. | Giữ kết quả của các sổ được kiểm, gồm các cửa sổ 10k/25k vượt ranh năm. V4 vẫn đóng. |
| V19 BASE_GUARD | 194 lệnh EUR mỗi gói Dev PRIMARY/STRICT × OHLC/OLHC. Đường pack khai báo no-swap. Kiểm độc lập không có rollover EUR theo cả hai mốc, kể cả deadline dự phòng. | Đường no-swap vẫn hợp lệ cho EURUSD và sổ BASE giữ verdict ban đầu. |

Khoảng dự phòng được kiểm vì phí có thể đổi tình trạng nhận lệnh, equity
và Reward ngay cả khi tổng phí lúc đóng kết sổ giống nhau. Ở các tape
trên không có sự kiện ở cả hai đồng hồ trong **cả hai khoảng**, nên không
cần replay. Với mốc đủ 12 tháng, V15 Calibrated và Cushion vẫn mỗi cấu
hình có một mốc Reward mô phỏng trong từng giả định phí. V4 và BASE vẫn
ở kết luận cũ. Phạm vi này chỉ bao gồm Development và nhánh EURUSD.
[Audit Reward gốc](PROP-CHALLENGE-REWARD-MILESTONES-20261119.md) ·
[Kết quả V4 ghép ranh](PROP-V4-HARVEST-BACKWARD-RESULTS-20261119.md) ·
[Đường replay đồng hồ](../../tooling/ai-engines/prop_v6_replay.py) ·
[Đường pack BASE](../../tooling/ai-engines/prop_v18_blocks.py).

## Bằng chứng

- Job `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/prop-eur-fx-rollover-audit-20261119/`.
  Giữ `registration.md`, sổ `ledgers.json.zst`, `summary.json` chi tiết
  theo năm, cụm và chiều, `reward-clock-census.json.zst`,
  `verification.json` và `manifest.json`. Không giải nén nguồn giá
  kéo dài sau năm 2023. Audit tiêu thụ sổ Development có sẵn.
- SHA256 card `7e7aa58a593cf1c26cd2a785d03ba52af26b2f6ecfc7bb54977fb58205034d30`.
  SHA256 manifest `c08cc8c831a7ddd1e3b72f915a48409fa56923251bb20445be06773723e579a3`.
  Độc lập đếm lại clock và tiền của **3.170 dòng sổ** và kiểm hai khoảng
  tài trợ của **2.172 dòng tape Reward**, có lặp giữa các chế độ.
- Phép đo tiền 1,63 s, kiểm tape 0,90 s, đối chiếu độc lập 1,12 s.
  Fixture bao phủ giờ mùa hè/mùa đông, hai tuần lệch DST, rollover
  thứ Tư, cuối tuần và trường hợp entry/exit đúng mốc.

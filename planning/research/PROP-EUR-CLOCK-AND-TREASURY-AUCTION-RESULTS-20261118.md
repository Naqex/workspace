# EURUSD — hiệu chỉnh giờ HistData và kiểm tín hiệu đấu giá Treasury

**Kết quả cho quyết định thi quỹ.** Số thiếu trung vị vòng 1 sau 12 tháng
trong phép tính độ nhạy đã hiệu chỉnh là **4.873,10 USD PRIMARY** và **4.926,57
USD STRICT**. Luật đấu giá Treasury trượt Stage‑0. BASE_GUARD vẫn
`NOT_QUALIFIED`. Dữ liệu giá 2024–2026 được giữ đóng.

## 1. Lỗi đồng hồ của dữ liệu EURUSD dùng cho đối chiếu F5

Tái dùng ZIP đã kiểm SHA256. So các phút quanh điểm vào, điểm thoát và
khoảng trống với tick Dukascopy cung cấp theo epoch UTC. Kiểm đồng thời
timestamp đến mili giây, Bid và Ask ở ba độ dịch từ timestamp theo giả
định UTC−5 của HistData. Dùng việc khớp chuỗi giá và giờ để quyết định
offset. [Đặc tả HistData](https://www.histdata.com/f-a-q/data-files-detailed-specification/)

| Ngày | Tick HistData trong các phút được so | Trùng ở 0h | Trùng ở −1h | Trùng ở +1h |
|---|---:|---:|---:|---:|
| 26/05/2021 | 519 | 0 | 438 | 0 |
| 14/07/2021 | 331 | 0 | 287 | 0 |
| 03/01/2022 | 289 | 289 | 0 | 0 |

Ngày 26/05 và 14/07/2021, 89 tick từng được dùng làm giá ở bốn phút
thiếu thực ra trùng với tick của **một giờ trước**. Đặt lại về giờ
UTC thì cả bốn phút này vẫn rỗng, cùng với sáu phút của 03/01/2022.
Hai lần định giá lại cả lệnh vẫn chạm deadline trên chuỗi được kiểm,
với lần lượt +330,97 và +509,19 USD. Ngày 03/01/2022 giữ +242,40 USD.
Cả ba đường giữ lệnh vẫn có các phút thiếu, nằm trong
dung sai tối đa ba phút của phép tính độ nhạy. Việc trùng Bid, Ask
và mili giây là bằng chứng trùng chuỗi báo giá tại mẫu. Giá và stop
thực tế trên tài khoản đích vẫn chưa được xác nhận.

Rà đúng hai mốc đã dùng để định giá **16 lệnh EURUSD** trong phép tính
cũ. Xác nhận lệch −1 giờ ở 11 lệnh trên tháng 05/2019, 05/2021,
07–09/2021 và 05/2022. Năm lệnh giữ nguyên đồng hồ ở 02/2021,
11/2021, 01/2022, 03/2022 và 11/2023. Với 05/11/2021, mở rộng mốc
thoát thêm hai phút kề vì phút chính chỉ có hai tick. Cả 17 tick
trong cửa sổ thoát trùng ở 0h. Mười lệnh lệch đã định giá lại với tick
đúng phút vào/ra và xác minh hai endpoint. Ngày 13/09/2021, giá thoát
đúng giờ chưa tìm thấy trong dung sai nên loại khỏi phép thay giá,
giữ kết quả sổ gốc cho lệnh đó. Hai lệnh XAUUSD của phép tính ban đầu
được giữ theo số liệu cũ. Không dùng offset suy ra từ các mốc đó
cho archive hoặc tài sản ngoài mẫu.

### Số dư 12 tháng sau hiệu chỉnh

Cùng các cửa sổ chưa qua vòng 1, số lot cố định và journal gốc.
17 lệnh có giá thay thế, gồm mười lệnh được sửa giờ, năm EURUSD còn
lại và hai XAUUSD. Đây là phép đo độ nhạy số dư có điều kiện.
[Báo cáo gốc](PROP-GAP-FULL-DEV-RESULTS-20261118.md)

| Kịch bản | Số cửa sổ | Thiếu trung vị sổ gốc | Thiếu trung vị ở phép tính cũ | Thiếu trung vị sau sửa giờ | Số dư chạm 55.000 USD sau sửa |
|---|---:|---:|---:|---:|---:|
| PRIMARY | 55 | 4.929,17 USD | 4.712,35 USD | **4.873,10 USD** | 0/55 |
| STRICT | 58 | 5.870,60 USD | 4.744,54 USD | **4.926,57 USD** | 0/58 |

Tại lot tham chiếu của bảng 150 USD risk, tổng tiền sổ đối chiếu
sau sửa là +3.679,61 USD PRIMARY và +2.717,25 USD STRICT. Sổ mô phỏng
Challenge gốc không dùng các giá HistData này. Việc cần chạy lại là
phép thay tiền trên 113 cửa sổ. Kết luận về tiến độ vòng 1 giữ nguyên.
Số đếm 26/43 khoảng từ audit cũ là kết quả đọc theo đồng hồ cũ, chưa
được chứng nhận lại trên toàn 43 khoảng.

## 2. EURUSD sau kết quả đấu giá Treasury

Luật định trước tại `4d2f546`. So tỷ lệ khối lượng đặt mua trên khối
lượng được chấp nhận với trung vị bốn kỳ trước cùng kỳ hạn. Cao hơn
thì BUY EURUSD, thấp hơn thì SELL. Vào 15 phút sau giờ đóng đấu giá
và đo tới 16:30 New York. Câu hỏi là liệu dòng hedge và điều chỉnh
tồn kho có tiếp tục tạo lợi thế sau công bố. Nghiên cứu gốc cho thấy
phản ứng quanh đấu giá. Phép đo này thử riêng phần sau mốc có thể vào.
[Card](PROP-EUR-TREASURY-AUCTION-CARD-20261118.md) ·
[Bank of Canada](https://publications.gc.ca/collections/collection_2025/banque-bank-canada/FB3-5-2025-29-eng.pdf)

Nguồn Fiscal Data có 721 bản ghi Notes/Bonds từ 2017–2023. Xét 452
ngày Development có đấu giá nominal thuộc tập kỳ hạn đã khóa. Có
9 ngày hòa BTC, 4 ngày năm 2020 thiếu lịch sử 20 năm và 1 ngày thiếu
giờ công bố xác nhận. Kiểm tám thông báo XML chính thức. Cả tám tỷ lệ
trùng, bảy giờ công bố có mặt sớm hơn buffer 15 phút, một thông báo
trống giờ và ngày đó được loại. Với các kỳ còn lại, thời gian công bố
được mô phỏng bằng buffer đã khóa. Một tín hiệu (25/08/2021) thiếu giá
thoát tại 20:30 UTC, và ba tín hiệu đã định giá không
có stop đủ dữ liệu hoặc ở đúng phía. Dùng M1 Bid lịch sử và Ask proxy
1 pip trong gói V14 Development. Ma sát stress là 1,9 pip vòng lệnh.
[Treasury Fiscal Data](https://fiscaldata.treasury.gov/datasets/treasury-securities-auctions-data/) ·
[XML công bố mẫu](https://www.treasurydirect.gov/xml/R_20220111_1.xml)

| Năm | Tín hiệu | Có giá | Stop trung vị | Qua phí | Markout stress (pip/lệnh) |
|---|---:|---:|---:|---:|---:|
| 2018 | 68 | 68/68 | 13,40 pip | 27/68 (39,7%) | −1,54 |
| 2019 | 66 | 66/66 | 9,80 pip | 14/66 (21,2%) | −0,68 |
| 2020 | 70 | 70/70 | 12,05 pip | 25/70 (35,7%) | −1,21 |
| 2021 | 77 | 76/77 | 9,30 pip | 19/77 (24,7%) | +0,30 |
| 2022 | 77 | 77/77 | 16,30 pip | 39/77 (50,6%) | −2,74 |
| 2023 | 80 | 80/80 | 12,40 pip | 28/80 (35,0%) | −1,40 |

**`ECONOMIC_FAIL`**, kèm `DATA_PATH_INCOMPLETE` vì độ phủ năm 2021 là
98,70%, dưới sàn 99%. Có 438 tín hiệu thô, 437 định giá được và 152
qua phí (34,7%). Trung bình −1,22 pip/lệnh sau phí và −1,84 pip
ở nhóm qua phí. Sau spread và trước commission/slippage, mức bình quân
vẫn âm khoảng 0,32 pip. Chỉ 2022 đạt cả cổng quy mô và giữ mẫu.
Cả sáu năm hụt sàn markout. Gác đúng luật đã khóa. Cổng cho replay
cùng risk chưa đạt, nên chưa có số đếm mới về hai vòng hoặc drawdown.

## Bằng chứng tái lập

Nhánh `codex/prop-research-roadmap`. Audit dùng 93 giờ tick ở các mốc
cần thiết của 16 lệnh, cộng các cửa sổ quanh mười khoảng thiếu tại ba
ngày ưu tiên. Đã đối chiếu đúng số cent của phép tính cũ, cohort cũ,
giá và giờ ở hai đầu mỗi lệnh được giữ sau sửa. Các kiểm tra chạy lại
dùng số hữu tỷ để kiểm chiều, chi phí và cổng phí trên toàn bộ 437
tín hiệu có giá của phép đo Treasury. Artifact và script tư nhân ở
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/prop-eur-clock-and-auction-20261118/`. Kiểm thử hồi quy xử lý khoảng thiếu đạt 12/12.

| Manifest Zstandard | SHA256 |
|---|---|
| `eur-clock-audit-complete-manifest.json` | `ded0d782255f10703296ea9a0ba5ca7479f21c7e17ac09ebb4072568d46fc112` |
| `eur-clock-cash-correction-v2-manifest.json` | `7054a771dd05ae15c94e2699a8131d2f8a39f2965bb587045f1be29194dcf343` |
| `treasury-stage0-complete-manifest.json` | `5333104b39d600d5d455e592428694fdb5dd0d3578e13144d060de4a4c94fdb7` |

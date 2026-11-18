# Stocks in Play và đảo chiều vàng quanh phiên đấu giá London PM

**Chưa có ứng viên đủ điều kiện replay tài khoản 50.000 USD.** Pilot TSLA
đo được khối lượng khớp và cơ hội phá biên trên thị trường cổ phiếu, nhưng
chưa đủ dữ liệu thực thi CFD. Nhánh độc lập Gold PM trượt Stage‑0. Giữ
`BASE_GUARD` làm đối chứng ở `NOT_QUALIFIED`.
[Bài đo khoảng thiếu](PROP-PAYOUT-REPLAY-DECISION-20261118.md)

## 1. Stocks in Play — có tín hiệu thật, thiếu giá thực thi đích

Zarattini, Barbon và Aziz lấy khối lượng 09:30–09:34 New York chia cho
bình quân đúng cửa sổ đó của 14 phiên trước. Tại 09:35, lấy các mã RVOL
≥1 và xếp 20 mã cao nhất trong universe đủ điều kiện. Mỗi mã chỉ giao
dịch nếu phá biên theo hướng nến mở cửa. SL cách fill 0,1 ATR14 ngày, còn
vị thế thì đóng cuối phiên. Ở phần phân rã của bài, nhóm RVOL trên 1 đạt
khoảng +0,08R/lệnh sau commission 0,0035 USD/share mỗi chiều. Kết quả
phân rã này khác với kết quả portfolio top 20 và chưa bao gồm điều kiện
CFD của FTMO. QuantConnect có bản triển khai đối chiếu trên năm 2016.
[Paper §2, §3, §4](https://alexandria.unisg.ch/server/api/core/bitstreams/3c2989c4-688d-4d78-8a71-f02690990d51/content) ·
[QuantConnect](https://www.quantconnect.com/research/18444/opening-range-breakout-for-stocks-in-play/)

**Universe và điều kiện quỹ.** FTMO xác nhận đã có TSLA trong thông báo
tháng 8/2022, áp dụng cho Challenge, Verification và FTMO Account. Tài
liệu FTMO công bố Equities CFD ở Swing 1:1 và Standard khoảng 1:3,3.
Dùng 100% và 30% margin làm hai kịch bản của phép kiểm tiền. Trang
Symbols hiện hành có nhóm Equities CFD. Chưa thu được contract size,
lot min/step, commission, lịch giờ và giới hạn short TSLA trên đúng
server FTMO 2-Step hiện tại, hay lịch thay đổi các thông số đó trong
2018–2023. Giờ NYSE/Nasdaq dùng làm đồng hồ tín hiệu, chưa chứng nhận
giờ mở/đóng CFD. Thông báo FTMO ngày 19/03/2026 xác nhận KO và nhiều
mã khác chỉ mới được thêm ở đợt đó. Không dùng danh sách hiện tại làm
universe lịch sử. Mẫu free có TSLA, KO, SPY và TWTR, nhưng chỉ TSLA có
xác nhận FTMO đương thời trong lượt này. Các ngày đầu mẫu trước mốc
thông báo vẫn được đếm ở lớp cash pilot, chưa xác minh khả năng giao
dịch FTMO những ngày đó.
[FTMO đòn bẩy theo tài sản](https://ftmo.com/en/blog/a-few-answers-to-your-questions/) ·
[FTMO TSLA tháng 8/2022](https://ftmo.com/vi/blog/trading-update-18-08-2022/) ·
[FTMO bổ sung mã](https://ftmo.com/en/blog/trading-updates/trading-update-19-mar-2026/) ·
[Symbols hiện hành](https://ftmo.com/en/symbols/)

**Thử dữ liệu mới.** Dùng mẫu 1 phút HistoricalData.net 07–12/2022, số
cổ phần giao dịch từ cột `volume`. Kiểm ZIP/manifest và đủ mọi phút
cash của 127 phiên, kể cả 25/11 phiên ngắn 210 phút. Một nguồn dữ liệu
cổ phiếu và một nguồn quote CFD là hai đầu vào khác nhau. Chỉ dùng raw
price/volume, quy đổi 3:1 tại ngày hiệu lực 25/08 để các phiên trước
cùng đơn vị, không dùng cột điều chỉnh theo sự kiện về sau. Sau đủ 14
phiên quá khứ và một close để tính TR, bỏ phiên ngắn khỏi giao dịch,
còn 111 ngày. Mẫu một mã có thiên lệch chọn tên và chỉ dài nửa năm.
Giữ raw ở private evidence theo quyền dùng mẫu để đánh giá.
[Mẫu và điều khoản](https://historicaldata.net/samples.html) ·
[Điều khoản](https://historicaldata.net/terms.html) ·
[Phương pháp dữ liệu](https://historicaldata.net/methodology.html) ·
[Tesla split](https://www.nasdaq.com/press-release/tesla-announces-a-three-for-one-stock-split-2022-08-05) ·
[Lịch cash](https://www.nasdaqtrader.com/content/technicalsupport/2022tradingcalendar.pdf)

| Phễu và khả năng chứa lệnh TSLA | Kết quả 07–12/2022 |
|---|---:|
| Phiên có đủ lịch / ngày đủ điều kiện xét | 127 / 111 |
| Đủ RVOL và các điều kiện trước phá biên | 47 |
| Phá biên cash theo hướng nến mở cửa | 42 · 22 BUY / 20 SELL |
| Tháng 7 → 12, số lần phá biên | 1 / 4 / 10 / 9 / 4 / 14 |
| Phá biên trong nến 09:35–09:49 / trước 10:30 ET | 38 / 41 |
| Vị thế đồng thời tối đa trong pilot một mã | 1 |
| Stop 0,1 ATR trung vị ở 42 lần phá, USD/share | 1,13 |
| Đủ margin cho size làm tròn xuống ở risk 150 USD, riêng TSLA | 42/42 ở cả hai kịch bản |
| Margin trung vị Swing / Standard proxy | 27.932 / 8.380 USD |
| Margin Swing lớn nhất | 42.028 USD |
| Risk danh nghĩa sau làm tròn, trên lưới giả định 1 share | 6.271,73 USD tổng · 149,33 USD/lần |
| Fill CFD đã xác minh / margin thực còn lại khi chạy chung BASE | Chưa đo được |

Các lần phá biên dùng High/Low M1 sau 09:35. Nếu Open đã vượt trigger,
lấy Open làm giá vào minh họa, còn lại dùng mức trigger. Số lần có
overshoot đo được bằng Open M1 là 0/42. M1 không xác định vị trí trong
hàng chờ, spread lúc stop kích hoạt hoặc giá khớp đầu tiên trong phút.
Không suy slippage bằng 0. Cỡ mẫu một mã cũng chưa đo được việc nhiều
mã tranh nhau margin ngay lúc mở cửa. Với khoảng 27.932 USD margin
trung vị ở Swing, hai lệnh cỡ trung vị cùng lúc đã cần hơn 50.000 USD.

**Ngưỡng tiền.** Nếu nhịp nửa năm lặp nguyên và cả 42 lần phá đều
chuyển thành fill CFD, 84 fill/năm ở risk đo được cần **0,07972R net mỗi
fill** để góp 1.000 USD/năm. Gắn 0,08R của paper vào phép độ nhạy cho
1.003,48 USD/năm và chỉ chừa 3,48 USD/năm cho phần chi phí tăng thêm
so với paper. Với giả định riêng 0,004% notional/side, phí gộp tăng
khoảng 120,68 USD/năm so với commission paper, cho khoảng 882,80 USD/năm
trước spread, stop slippage và cạnh tranh risk. Đây là kịch bản phí
để thấy độ nhạy, chưa xác thực mức commission TSLA của FTMO. Dữ liệu
cash chưa cho biết TSLA có đúng kỳ vọng 0,08R, hay thêm mã nào làm tăng
lợi nhuận sau khi dùng chung margin. Phí và fills ở cap 12% vẫn unknown.

| Nguồn tra thêm | Kết quả admission |
|---|---|
| Hồ sơ local AAPL/MSFT | 390 phút Bid/Ask mỗi mã của một ngày 2019. Volume chưa xác nhận là cổ phần khớp. Không ghép được hai file đó với phiên TSLA. |
| Dukascopy TSLA | Đã thử tick và Ask M1 đúng ngày trong mẫu qua hai URL chính thức, HTTP 429. Ngay cả khi truy cập được, đây là giá CFD phía Dukascopy cần xác minh clock, split và sai khác với FTMO. |
| AlgoSeek trên QuantConnect | US SIP và security master có cấu trúc phù hợp. Không tìm thấy archive M1 2018–2023 được cấp quyền sử dụng local miễn phí trong lượt này. |
| Alpaca và HF Data Library | Alpaca yêu cầu tài khoản và phân quyền feed. HF Data Library bắt đầu 03/2022, IEX một venue và giới hạn cho nghiên cứu học thuật. Không dùng một venue làm đại diện cho RVOL toàn thị trường hoặc thay nguồn quote đích. |

[Fixture cũ](STOCK-INFORMATION-SOURCE-RESULTS-20261109.md) ·
[Dukascopy](https://www.dukascopy.com/api/data/get/historical-data-export) ·
[AlgoSeek](https://www.quantconnect.com/docs/v2/writing-algorithms/datasets/algoseek/us-equities) ·
[Alpaca](https://docs.alpaca.markets/us/v1.1/docs/about-market-data-api) ·
[HF Data Library](https://hfdatalibrary.com/)

**Quyết định.** `DATA_PATH_INCOMPLETE` ở quy mô 2018–2023 và ở lớp khớp
CFD. Giữ lại phép kiểm volume và capacity. Cần đồng thời universe
point-in-time, khối lượng 5 phút và Bid/Ask CFD có đường giá quanh
stop-market, cộng spec của tài khoản đích. Khi có nguồn hợp lệ, dùng
cùng rule đã khóa để đo cả 12% cost cap và ít nhất 50% retention trước
khi dành lượt replay 50k.

## 2. Hướng độc lập đã chạy — XAUUSD đảo chiều quanh 15:00 London

ICE mở phiên đấu giá vàng PM lúc 15:00 London. Nghiên cứu của Caminschi
và Heaney tìm thấy phản ứng giá quanh thời điểm công bố của cơ chế
lịch sử. Phép thử ở đây đặt câu hỏi riêng: biến động mạnh qua khung
quanh giờ đấu giá có hồi lại sau đó đủ để nuôi chiến lược hay không.
Dùng giờ theo lịch. Không có giá đấu giá, mất cân bằng lệnh hoặc giờ
kết thúc của từng ngày. Khác phép đo vô điều kiện R054/R055 trước đây.
[ICE](https://www.ice.com/iba/lbma-precious-metals) ·
[Nghiên cứu gốc](https://api.research-repository.uwa.edu.au/ws/portalfiles/portal/4725264/A0205_use_this.pdf) ·
[Luật R054/R055](GOLD-SESSION-COMPONENT-PROTOCOL-20261108.md)

Khóa cùng đăng ký trước số liệu. Đo Bid Open 14:30 tới Bid Close
15:14. Nếu giảm từ 0,30% thì BUY, nếu tăng từ 0,30% thì SELL, ở M1
Open 15:15. Đo markout đúng M1 Open 17:15. Stop tự nhiên để đo độ chịu
phí lấy extreme cửa sổ trước entry, chừa 0,001 USD/oz, chưa kích hoạt
SL. Stress dùng Bid M1 đã nhận, Ask proxy +0,338 USD/oz, commission
0,0007% notional/side, slippage 0,20 USD/oz/side và không swap. Ngày
London theo DST và holiday England/Wales, giao với guard giờ đóng
hiện có của Gold. Cổng đã khóa yêu cầu ≥40 tín hiệu/năm, ≥99% predictor
và endpoint, tỷ lệ phí/stop trung vị ≤12%, giữ ít nhất 50% tín hiệu ở
cap 12%, mean net dương và ≥mean phí stress từng năm.
[Lịch GOV.UK](https://www.gov.uk/bank-holidays) ·
[Cổng hiện hành](../../.agents/skills/strategy-qualification/references/validation-gates.md)

| Năm | Predictor đủ | Tín hiệu có giá | Qua 12% | Stop trung vị USD/oz | Phí/SL trung vị | Net stress USD/oz | CI 95% theo tuần |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2018 | 247/247 | 19/19 | 0 | 1,03 | 73,4% | −1,86 | [−3,25; −0,44] |
| 2019 | 246/247 | 30/30 | 1 | 1,24 | 61,0% | +0,74 | [−0,95; +2,34] |
| 2020 | 248/248 | 78/78 | 8 | 2,61 | 29,3% | −1,73 | [−4,01; +0,16] |
| 2021 | 244/245 | 76/76 | 3 | 1,80 | 42,5% | −0,06 | [−1,52; +1,76] |
| 2022 | 246/246 | 65/65 | 2 | 1,88 | 40,5% | −1,99 | [−3,57; −0,46] |
| 2023 | 246/247 | 67/67 | 3 | 1,84 | 41,6% | −2,43 | [−4,24; −0,84] |

**335/335** tín hiệu có giá, **17/335 (5,1%)** đạt cap phí. Net gộp
bình quân **−1,33 USD/oz**. Năm 2019 là năm duy nhất dương, vẫn thấp
hơn 0,7581 USD/oz ma sát stress trung bình của năm. Sổ đối chiếu 150 USD
dùng 17 tín hiệu qua phí, làm tròn xuống nguyên oz và dự phòng phí
entry trong risk. Cho khoảng +182 USD tổng sáu năm, chưa kích hoạt
SL hay kiểm account. Chỉ 13/72 tháng có tín hiệu qua cap. Nhịp 2,83
lệnh/năm sẽ đòi khoảng 2,35R ròng/lệnh ở risk 150 USD để góp
1.000 USD/năm ngay cả khi đủ size. Kết quả hụt cadence 2018/2019 và hụt
scale lẫn markout mọi năm. Gắn `ECONOMIC_FAIL` +
`CADENCE_OR_SAMPLE_SHORTFALL`. Không mở biến thể.

## 3. Đối soát và quyết định

Không có đầu mối đủ để mở replay 50k hoặc ghi nhận payout tăng thêm.
Không đọc giá 2024–2026, không đổi risk hay lot, không truy cập broker
và không mua dữ liệu. Không xuất dữ liệu cổ phiếu nguồn lên Git.

Đăng ký `registration.md` được niêm phong trước tính toán (SHA256
`c91e6d84f2cc7a3ffcbcff1d7647cea9dc47caf161a512bb60eb49d302ffadae`).
Private evidence tại
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/prop-stocks-in-play-20261118/`.
`stock-pilot.py` kiểm từng file và lịch cash 127 phiên. `verify.py`
đọc lại M1 Gold bằng binary struct, đối chiếu clock bằng công thức DST
riêng, tái lập stop, cost, size và markout bằng Decimal trên cả 335
tín hiệu, kiểm lại tổng risk/công thức USD của 42 trigger cash. Cả
`stock-pilot.private.json.zst` và `gold-stage0.json.zst` giải nén
khớp bytes. Dấu SHA256 nguồn, script và kết quả trong `receipt.json`
và `gold-stage0-manifest.json`. Chỉ sửa đọc schema manifest stock và
cắt warm-up nguồn Gold theo phạm vi đã khóa trước khi chạy số thành
công. Không thay luật nghiên cứu.

# WTI → USD/CAD — pilot nguồn và kết quả Stage‑0

**`ECONOMIC_FAIL` · 0/6 năm qua sàn markout** Luật khóa tại `ece222b`, chỉ dùng Development
2018–2023. [Card đã khóa](PROP-OIL-CAD-STAGE0-CARD-20261118.md)

## Nguồn và đồng hồ

- WTI dùng `LIGHT.CMD/USD` CFD của Dukascopy. Mua/bán được quyết định từ
  hai nến H1 14:00 và 15:00 UTC sau khi nến sau đóng vào 16:00. Entry USD/CAD
  ở ngày thứ Hai–thứ Sáu kế tiếp. Hai nến WTI nằm trong cùng phiên và
  trước giờ nghỉ dùng để đổi hợp đồng. Chuỗi CFD đại diện cho nguồn báo giá
  của Dukascopy, còn CME settlement và EIA spot có cơ chế thời điểm riêng.
  [Dukascopy về roll](https://www.dukascopy.com/swiss/cz/marketwatch/calendars/cfd-price-adjustment-calendar/) ·
  [CME settlement](https://www.cmegroup.com/trading/energy/files/NYMEX_Energy_Futures_Daily_Settlement_Procedure.pdf)
- Đối chiếu M1 ở sáu ngày, gồm ba ngày 2019 từng thiếu mốc trong bài kiểm
  toàn phiên. Cửa sổ 14:00–16:00 có 120/120 phút nguồn ở mỗi phía của
  cả sáu ngày. Open/Close H1 khớp nến M1 ở ba ngày có bảng so giá.
  Nguồn H1 trả về 72/72 tháng, 35.400 nến UTC gốc. Trong 1.564 lịch
  ngày trước lọc nghỉ, có 17 ngày thiếu ít nhất một nến tín hiệu và 498
  tín hiệu đo được. Giữ nguyên 17 ngày thiếu trong số đếm.
- HistData tải được ba ZIP USD/CAD. Ngày 17/05/2023 có đủ điểm giá ở
  hai đầu nhưng thiếu 120 phút giữa cửa sổ theo cách đọc UTC−5 của
  tài liệu. Có **3.468 tick** ở hai giờ đọc ra 18:00 và 20:00 UTC
  trùng cả Bid, Ask và mili giây với Dukascopy khi dịch lùi một giờ.
  Đối chiếu không dịch cho 0 tick trùng ở hai khối đó. Dùng tick trực
  tiếp Dukascopy cho cả phép đo sáu năm, giữ ZIP HistData làm bằng chứng
  sự cố đồng hồ. Kết quả này chỉ kiểm các khối USD/CAD đã lấy mẫu.
  [Đặc tả HistData](https://www.histdata.com/f-a-q/data-files-detailed-specification/)
- Ma sát tính theo pip USD/CAD. Một lot chuẩn có 10 CAD/pip. Hai lần
  commission 2,50 USD/lot/side được đổi sang CAD bằng mid tại mỗi đầu rồi
  chia 10. Spread lấy từ Bid/Ask, trượt stress là 0,10 pip mỗi phía.
  Markout đã dùng Bid/Ask nên chỉ trừ commission và slippage thêm.
  Giá thoát 20:00 UTC trước mốc rollover 17:00 New York. Commission là
  proxy từ công bố FTMO Free Trial. Báo giá là feed lịch sử Dukascopy và
  slippage là giả định stress.
  [FTMO Free Trial](https://ftmo.com/en/blog/trading-updates/trading-update-11-sep-2025/) ·
  [Giờ rollover Dukascopy](https://www.dukascopy.com/wiki/en/manuals/jforex4-desktop/trading-sessions-logic/)

## Kết quả từng năm

Markout là thay đổi giá theo chiều tín hiệu từ tick vào ở phút 16:01
đến tick thoát ở phút 20:00 UTC. Stop chỉ đo biên cấu trúc và khả năng
chịu phí, chưa tham gia quyết định thoát trong phép đo này. Phí và stop
trong bảng là trung vị. Số giữ qua phí chia trên toàn bộ tín hiệu.
Mẫu thiếu giờ giữ ở mẫu số bảo thủ. [Card và tiêu chí](PROP-OIL-CAD-STAGE0-CARD-20261118.md)

| Năm | BUY / SELL | Có giá vào và ra | Stop (pip) | Ma sát (pip) | Ma sát/stop | Qua phí | Gross sau spread (pip) | Net (pip) | Net nhóm qua phí (pip) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2018 | 46 / 34 | 80/80 | 19,05 | 1,81 | 9,48% | 43/80 (53,75%) | +1,36 | +0,51 | −5,13 |
| 2019 | 36 / 31 | 66/67 | 16,40 | 1,87 | 11,41% | 32/67 (47,76%) | +0,06 | −0,80 | +3,06 |
| 2020 | 54 / 44 | 98/98 | 22,60 | 1,98 | 8,76% | 65/98 (66,33%) | −1,36 | −2,24 | −1,52 |
| 2021 | 33 / 40 | 73/73 | 20,25 | 1,83 | 9,02% | 42/73 (57,53%) | −4,41 | −5,24 | −3,77 |
| 2022 | 59 / 54 | 113/113 | 21,50 | 2,04 | 9,51% | 67/113 (59,29%) | −0,79 | −1,64 | −1,40 |
| 2023 | 35 / 32 | 66/67 | 19,40 | 2,02 | 10,43% | 35/67 (52,24%) | −2,71 | −3,58 | −5,73 |

Hai ngày không có giá khớp là 01/01/2019 và 25/12/2023. Mỗi ngày
có bốn giờ tick rỗng và nằm vào kỳ nghỉ công bố. Bảng giữ số đo bảo
thủ 66/67 ở mỗi năm vì chưa có bảng cutoff USD/CAD lịch sử khớp đủ
cho cả kỳ. Nếu bỏ đúng hai ngày này khỏi mẫu số, độ phủ hai năm
thành 66/66. Số giữ ở 2019 thành 32/66 (48,48%) và kết luận
markout ở cả hai năm giữ nguyên. Bốn ngày khác có đủ giá vào/ra nhưng
thiếu phút trước entry nên vẫn được định giá thô và không qua cổng
phí. Năm ngày có stop nằm sai phía lúc vào.
[Thông báo nghỉ 2018–2019](https://www.dukascopy.com/swiss/english/about/ournews/market-closures-on-christmas-and-new-year-/) ·
[Lịch FX 2018–2019 Swissquote](https://resources.swissquote.com/sites/swissquote.eu/files/2018-12/forex-hours-end-of-year-2018-2019-ltd-en.pdf) ·
[Thông báo nghỉ 2023](https://www.dukascopy.com/swiss/english/about/ournews/market-closures-on-christmas-and-new-year-dbl202761)

## Quyết định

**Dừng đúng luật `OIL-CAD-1PCT` ở Stage‑0.** Cả sáu năm có 67–113
tín hiệu thô. Định giá được 496/498 tín hiệu và 284/498 qua cap phí
(57,03%). Cổng quy mô trung vị đạt 6/6 năm, còn cổng giữ ≥50% đạt
5/6. Markout ròng trung bình toàn mẫu là **−2,09 pip**, và nhóm
qua phí là **−2,37 pip**. Gross sau spread toàn mẫu là −1,23 pip.

Có một năm net dương (+0,51 pip năm 2018) và **0/6 năm** đạt
sàn markout. Bốn năm đã âm ngay sau spread. Do đó đưa phí về mức thấp
hơn cũng chưa đủ để chứng minh tín hiệu ổn định. Giữ BASE_GUARD ở
`NOT_QUALIFIED` làm đối chứng. Replay cùng risk là bước có điều kiện
và điều kiện Stage‑0 không đạt. Khóa giá 2024–2026 được giữ.

## Đối soát và lưu kết quả

Có 1.992 gói giờ tick 14, 15, 16 và 20, gồm tám gói rỗng có ghi nhận. Tick 14:00–16:00
xác minh đủ 120 phút để dựng stop theo đúng phía giá. Bộ đọc kiểm SHA256
từng giờ, thứ tự thời gian, spread không âm và số lượng. Bộ kiểm tra riêng
dùng decoder native cho 18 mẫu BUY/SELL và đối chiếu giá vào, ra, stop,
và markout với bộ tính số hữu tỷ. Kiểm cận 1% của tất cả cửa sổ có giá
bằng hai cách tính. Biểu phí, phiên tin và khớp thực tế của tài khoản FTMO
chưa được kiểm qua broker.

Dữ liệu gốc, script, báo cáo JSON và bản nén Zstandard lưu dưới
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/prop-oil-cad-source-pilot-20261118/`.
`source-and-stage0-receipt.json` giữ hash đầu ra và các script.
SHA256 JSON kết quả `99ae207519488ebbbba3738848ab2755df55fa01b5c36c1408c1ea80b220017a`. SHA256 bản nén `3dde452a99b5a61621a91e4f073ccda25c57188653aa977f90af18109c438835`.

# US500 ETF đòn bẩy và EURUSD COT — kết quả Development

**Hai công thức đã chạy đủ 2018–2023 và dừng ở Stage‑0.** BASE_GUARD
giữ vai trò đối chứng với trạng thái `NOT_QUALIFIED`. Giá 2024–2026
vẫn đóng. Hồ sơ đính chính EURUSD F5 giữ số thiếu vòng 1 đã sửa là
4.873,10 USD PRIMARY và 4.926,57 USD STRICT.
[Hồ sơ đồng hồ và số dư](PROP-EUR-CLOCK-AND-TREASURY-AUCTION-RESULTS-20261118.md)

## 1. Quy mô UPRO/SPXU có tăng lợi thế của US500 cuối phiên?

**Kết luận.** Luật chọn ngày theo quy mô ETF âm cả sáu năm. Vùng so
cùng biến động chỉ phủ 78/751 tín hiệu ETF có giá. Chênh +0,71 point
trong vùng nhỏ này chưa đủ bằng chứng về giá trị thêm của dữ liệu quỹ.
[Card tại `7136c62`](PROP-US500-LETF-AUM-CARD-20261118.md)

Barbon và cộng sự ước lượng ảnh hưởng trên cổ phiếu thành phần, có
trọng số mỗi ETF và độ thanh khoản riêng. Ivanov–Lenkey chỉ ra dòng
vốn vào hoặc ra có thể giảm nhu cầu tái cân bằng cơ học. Ta đo một
proxy tập trung vào US500 CFD từ hai quỹ cùng chỉ số. Với quỹ +3x và
−3x, hệ số tài sản lần lượt là 6 và 12. Cả hai dương. Khi giá tăng,
mô hình cơ học hàm ý cả hai cùng mua thêm exposure. Khi giá giảm,
cả hai cùng giảm exposure. Hướng đó đã nằm trong luật momentum.
Quy mô tài sản từ hai phiên trước chỉ quyết định **có nhận ngày đó
hay không**. Phép đo chưa biết creations/redemptions, lượng quỹ đã
hedge trước 15:30, hay quy mô lệnh thực của toàn thị trường.
[Barbon và cộng sự, Eq. (6)](https://abarbon.com/assets/Liquidity_Provision_to_Rebalancing_Flows_from_Leveraged_ETFs_and_Equity_Options.pdf) ·
[Ivanov–Lenkey](https://www.sciencedirect.com/science/article/pii/S1386418117302604)

Nguồn ProShares có 1.509 phiên mỗi quỹ, từ 02/01/2018 đến 29/12/2023,
khớp toàn bộ lịch NYSE đã khóa. Dùng HTTP Range gắn ETag. Các probe
biên đọc ngày để định vị, chỉ giải mã và lưu giá/NAV/AUM của
2018–2023. NAV nhân số cổ phần khớp AUM với sai khác tối đa 0,0048%.
Đã rà split UPRO 3:1 và SPXU 1:4 ngày 24/05/2018, SPXU 1:5 ngày
21/01/2021, UPRO 2:1 ngày 13/01/2022. Dùng AUM tính trực tiếp để
tránh cú nhảy giả do bảng giá/cổ phần đã chỉnh split. Độ trễ hai
phiên chừa một ngày đầy đủ sau NAV. Archive hiện tại chưa chứng minh
thời điểm công bố hoặc revision cho mỗi dòng trong quá khứ.
[ProShares Data Downloads](https://prod.proshares.com/resources/data-downloads) ·
[Lịch split chính thức](https://accounts.profunds.com/etfdata/etf_splits.csv)

Cả hai phía dùng giá vào 15:31 và giá ra 15:59 New York, cùng phí.
Ma sát stress thêm 2,50 points ngoài spread. Cột **Net** và **Chênh**
là bình quân points mỗi tín hiệu có giá. **Chênh** đo ETF trừ đối
chứng giá-only đã cân cùng số ngày theo chiều, |return| và ATR quá khứ.

| Năm | ETF thô | Có giá | Có stop | SL trung vị | Phí trung vị | Qua phí | Net | Số ngày so được | Chênh |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2018 | 100 | 99 | 22 | 12,78 | 2,86 | 0 | −2,88 | 3 | 2,18 |
| 2019 | 172 | 171 | 10 | 10,69 | 2,81 | 0 | −2,72 | 0 | — |
| 2020 | 112 | 112 | 35 | 15,41 | 2,87 | 5 | −1,43 | 6 | −5,47 |
| 2021 | 159 | 159 | 16 | 14,39 | 2,91 | 0 | −2,92 | 2 | 0,44 |
| 2022 | 105 | 105 | 73 | 20,71 | 2,98 | 12 | −2,29 | 30 | 2,96 |
| 2023 | 105 | 105 | 61 | 14,75 | 3,01 | 0 | −2,77 | 37 | −0,21 |

- **753 tín hiệu ETF**, 751 định giá được và 17 qua cap phí (2,26%).
  Gộp **−2,54 points/lệnh** sau phí và −0,04 ngay sau spread, trước
  commission và slippage. Đối chứng giá-only dùng cùng hướng return
  tới 15:29. Bài close-momentum cũ dùng hướng tới 10:00 với cùng khung
  giờ thực thi. Sổ cũ cũng âm dưới stress ở các năm đã báo cáo.
  [Kết quả close-momentum](US500-CLOSE-MOMENTUM-RESULTS-20261108.md)
- Thiếu ít nhất một phút ở một trong các phiên quá khứ làm hỏng phần
  dựng 14 TR liền nhau, hoặc thiếu giá close để dựng TR. Chỉ 217/751
  tín hiệu có giá dựng được stop. 78 ngày có đủ ngày đối chứng trong
  cùng ô, tức **10,39%** so với yêu cầu 90%. Trong vùng này, chênh
  mức |return| là −3,15 bp và chênh ATR là +0,83 bp. Chênh markout
  dương 3/6 năm, một năm không có ô chung. Khoảng bootstrap theo
  tháng có điều kiện là **[−1,48, +3,19] points**.
- **Quyết định.** Gác `US500-LETF-AUM`. Cổng kinh tế thất bại 6/6
  năm, kể cả khi bỏ yêu cầu stop để nhìn markout thô. Thiếu độ phủ
  quy mô giới hạn phép quy thuộc. Kết quả không phân xử giữa hai
  nghiên cứu hoặc đo được ảnh hưởng của lượng rebalance thật.

## 2. Phép thử độc lập EURUSD theo vị thế hợp đồng EUR

**Kết luận.** `EUR-COT-LEV-DELTA` âm năm năm, trung bình **−2,83
pip/lệnh** sau phí, kể cả nhóm qua phí còn −4,00 pip. Chỉ 2023 qua
toàn bộ cổng cho một năm. [Card tại `0649d0b`](PROP-EUR-COT-LEV-DELTA-CARD-20261118.md)

Dùng CFTC TFF Futures Only mã CME 099741. Mỗi thứ Tư, theo hướng
thay đổi vị thế ròng của nhóm dùng đòn bẩy qua hai báo cáo tuần
trước, vào 10:30 và ra 16:30 New York. Câu hỏi là phần dòng lệnh
còn tiếp diễn sau khi dữ liệu đã được công bố. Nguồn có 313 tuần
trong 2018–2023. Một tuần cuối nằm ngoài kỳ entry. Loại 19 tuần
có nguy cơ công bố trễ theo hai khoảng khóa trước. Thay đổi tính
từ long trừ short khớp cột changes của CFTC ở mọi tuần được xét.
Public Reporting API trả HTTP 403, dùng ZIP chính thức theo năm.
[Kho CFTC](https://www.cftc.gov/MarketReports/CommitmentsofTraders/HistoricalCompressed/index.htm) ·
[Phân tích RBNZ](https://www.rbnz.govt.nz/research-and-publications/research/our-research-and-analysis/analytical-notes/2018/an2018-03)

| Năm | Tín hiệu | Có giá | Stop trung vị (pip) | Qua phí | Net stress (pip/lệnh) |
|---|---:|---:|---:|---:|---:|
| 2018 | 48 | 48/48 | 20,25 | 30/48 | −9,82 |
| 2019 | 39 | 39/39 | 10,70 | 13/39 | −0,92 |
| 2020 | 52 | 52/52 | 15,15 | 25/52 | −2,11 |
| 2021 | 52 | 51/52 | 13,00 | 20/52 | −3,00 |
| 2022 | 52 | 52/52 | 20,40 | 32/52 | −3,57 |
| 2023 | 44 | 44/44 | 18,10 | 24/44 | +3,32 |

Có 287 tín hiệu, 286 có giá, 144 qua phí. Spread 1 pip là Ask
proxy, tổng stress 1,9 pip như các nghiên cứu EURUSD trước. Năm
2019 hụt cadence với 39 tín hiệu sau khi bỏ các tuần công bố trễ và
ngày nghỉ. Ngày 25/08/2021 còn thiếu giá ở giờ khớp đã đăng ký.
Cột markout đã sửa lỗi bản chạy đầu dùng nhầm 15:30 làm giờ ra.
Giữ artifact đó làm lần thử bị loại và kiểm 16:30 qua giờ New York
trên mọi tín hiệu ở bản chính thức.
`ECONOMIC_FAIL`, `CADENCE_OR_SAMPLE_SHORTFALL`, `DATA_PATH_INCOMPLETE`.

## 3. Quyết định danh mục và đối soát

Cả hai công thức hụt cổng replay ở cùng risk. Chưa có phép đo mới
về số lần qua hai vòng trong 12 tháng, daily/overall loss hay payout.
Bằng chứng định lượng vẫn ủng hộ gác đúng hai công thức đã khóa.

Đã chạy **22/22 test tập trung** về Stage‑0, lịch và nguồn H1/M1.
Bộ so riêng kiểm cả hai giờ thực thi theo New York, phép tính phí
và PnL, AUM trễ đúng hai phiên, và cộng lại chênh của đối chứng theo
trọng số từng ô. Hồ sơ cục bộ giữ inputs, script, registration và
hai lần chạy COT trong
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/prop-us500-etf-20261118/`.

| Manifest Zstandard | SHA256 |
|---|---|
| `us500-etf-stage0-manifest.json` | `aa9141814cce17695dcb4d310f442d52e9d39341ceb7caea07d847ec8aa437ab` |
| `eur-cot-stage0-v2-manifest.json` | `8b4db0b5bff29cb0491d5c2518151b7d6ea3a6419ffdee489708eaee028b8fcc` |

# TSLA ORB không RVOL — ngân sách phí và phép kiểm Gold COMEX

**TSLA ORB chưa xác minh được ngoài nửa cuối 2022.** Sổ cũ chịu được
thêm 0,289–0,489 USD/cổ phần mỗi vòng để còn 500 USD trong mô hình
khớp tại mức SL. Khi tính khớp tại cực trị phút chạm, sổ còn 23,33 USD
trước spread. Chưa có báo giá tại cửa sổ đã khóa để xác định mô hình
nào gần thực thi. Hướng độc lập Gold COMEX trượt Stage‑0.
[Đối chứng TSLA gốc, b6b9c91](PROP-TSLA-2022H2-CASH-PATH-RESULTS-20261118.md)

## 1. TSLA ORB — dư địa phí trên 103 lệnh đã biết

Đóng băng toàn bộ đối chứng không RVOL, hai chiều, 103 lệnh tại
b6b9c91. Đây là giả thuyết hậu chọn để kiểm ở kỳ khác. Dùng cùng
breakout 5 phút, cửa sổ vào, các điều kiện giá/thanh khoản, SL
0,1 ATR14, 150 USD/lệnh, số cổ phần đã làm tròn và giờ thoát 15:59
New York. Không chọn riêng SELL hay RVOL thấp. Tổng risk định mức
sau làm tròn 15.369,42 USD, tổng 11.375 cổ phần tính theo lượt vào.
Phí bên dưới dùng proxy 0,004% notional mỗi chiều trên giá gốc
mô phỏng, chưa xác nhận cho FTMO. Không cộng phí paper vào bảng.

| Thứ tự và giả định khớp | Net sau commission proxy | Khoản còn để trả spread và slip mà vẫn giữ 500 USD | USD/lệnh, hai đầu | USD/cổ phần, hai đầu | USD/cổ phần mỗi đầu nếu chia đều |
|---|---:|---:|---:|---:|---:|
| Open → Low → High → Close, khớp tại SL trừ gap đầu phút | +3.788,01 | +3.288,01 | 31,92 | 0,28906 | 0,14453 |
| Open → High → Low → Close, khớp tại SL trừ gap đầu phút | +6.067,81 | +5.567,81 | 54,06 | 0,48948 | 0,24474 |
| Khớp SL tại cực trị bất lợi phút chạm | +23,33 | Thiếu 476,67 ngay cả ở spread bằng 0 | — | — | — |

Trong sổ này, lấy kết quả thấp/cao theo từng lệnh cho cùng tổng
với hai thứ tự đồng nhất ở bảng. Đây là trùng khớp của mẫu. Gọi B
là số tiền sau proxy commission trừ 500 USD. Khi mọi lệnh chịu chi
phí mỗi vòng bằng nhau trên cổ phần, ngưỡng là B / 11.375. Khi
phí khác nhau giữa lệnh stop và lệnh đóng phiên, dùng tổng phí
hai đầu thực tế theo cỡ lệnh và so với B.

| Nhóm chịu chi phí | OLHC, mẫu bất lợi | OHLC, mẫu thuận lợi |
|---|---:|---:|
| Lệnh SL / số cổ phần một chiều | 80 / 8.722 | 78 / 8.429 |
| Lệnh đóng phiên / số cổ phần một chiều | 23 / 2.653 | 25 / 2.946 |
| Nếu toàn bộ B chỉ dành cho exit SL, USD/cổ phần | 0,3770 | 0,6606 |
| Nếu toàn bộ B chỉ dành cho lệnh đóng phiên, USD/cổ phần mỗi vòng | 1,2394 | 1,8900 |

Hai hàng cuối minh họa trường hợp những phần còn lại chịu chi phí
bằng 0. Khi có chi phí ở cả hai đầu, cả hai phải cùng dùng chung B.
Kịch bản cực trị lấy thêm 3.764,68 USD từ các exit SL so với đầu
bất lợi theo giá liên tục, tương đương 0,4316 USD trên mỗi cổ phần
đóng bằng SL. Chênh lệch này đo thiết kế stress, không đo slippage
thực. Phần ma sát quan sát được vẫn chưa có.

**Độ tập trung.** Ba lệnh thắng lớn nhất đóng góp 4.408,66 USD ở
cả hai thứ tự, xấp xỉ 25–28% tổng lãi của các lệnh thắng. Bỏ lệnh
thắng lớn nhất, hai kết quả còn **+2.090,99 / +4.370,79 USD**.
Bỏ ba lệnh thắng lớn nhất, còn **−620,65 / +1.659,15 USD**.
Đầu bất lợi mất dư địa 500 USD ngay cả khi chưa trả thêm ma sát.
Đây là phép đo độ nhạy. Tiêu chí và danh sách 103 lệnh giữ nguyên.

## 2. Kỳ TSLA mới và báo giá — chặn ở nguồn

Ưu tiên nguồn consolidated cash M1 TSLA trọn 2023H1, sau đó là
sáu tháng ngoài kỳ đã dùng theo thứ tự khả dụng đã khóa. Fallback
là tháng 1/2023, có warm-up từ cuối 2022. Thiếu lát đủ quyền truy cập
và đủ scope nên chưa tính PnL ngoài mẫu. Mẫu một tháng, nếu có,
chỉ là chẩn đoán, không đủ để kết luận mốc 500 USD/sáu tháng.

| Nguồn đã kiểm | Quyết định |
|---|---|
| HistoricalData.net, cùng nhà cung cấp | Lát free 07–12/2022 chính là kỳ đã biết. Kho lịch sử chính cần mua. |
| Marilux | Công bố mẫu tối đa 31 ngày và hạn mức theo tài khoản. Request cho tháng 1/2023 trả 403. Không có dữ liệu đã admit. |
| FirstRate / MarketParquet / FinzData | FirstRate công bố mẫu hai tuần tháng 9–10/2026, MarketParquet chỉ một tuần intraday công khai, FinzData chỉ 10 nến ở đường công khai. Không đủ khoảng đã khóa. |
| AlgoSeek và NYSE Daily TAQ | NYSE directory không có NBBO/trade đúng sáu ngày đã chọn. Có admin mẫu 2022 khác ngày và dữ liệu giá 2026 ngoài scope. AlgoSeek Sandbox có demo và guest flow nhưng license demo hạn chế mục đích ra quyết định, chưa có quyền dùng bộ TSLA cần thiết. |
| HF Data Library | IEX một venue, không đáp ứng universe consolidated và không phải báo giá CFD. |
| Dukascopy | Request tick TSLA của cửa sổ trung lập đầu tiên trả HTTP 429, không retry để ép truy cập. Chưa có Bid/Ask proxy được admit. |

[Mẫu HistoricalData.net](https://historicaldata.net/samples.html) ·
[Marilux](https://marilux.dev/en/data) ·
[FirstRate](https://firstratedata.com/free-intraday-data) ·
[MarketParquet](https://marketparquet.com/documentation) ·
[FinzData](https://finzdata.com/samples) ·
[NYSE sample index](https://ftp.nyse.com/Historical%20Data%20Samples/DAILY%20TAQ/) ·
[AlgoSeek TAQ](https://algoseek.com/dataset/us-equities-trade-and-quote/) ·
[AlgoSeek Sandbox](https://sandbox.algoseek.com/) ·
[HF Data Library](https://hfdatalibrary.com/)

Chọn đúng lệnh đầu tiên theo thời gian của mỗi tháng trước khi xem
quote. Giờ ET, cột cuối gộp stop theo hai thứ tự. Sáu lệnh được chọn
đều thuộc nhóm SL trong mô hình, vì vậy phép lấy mẫu không đo spread
lúc 15:59 của các lệnh còn mở.

| Ngày 2022 | Vào | Thoát trong hai đường OHLC |
|---|---|---|
| 25/07 | 09:35 | 09:44 |
| 01/08 | 09:35 | 09:35 hoặc 10:35 |
| 01/09 | 10:17 | 10:22 |
| 03/10 | 09:37 | 10:02 |
| 01/11 | 09:44 | 09:47 |
| 01/12 | 09:35 | 09:36 |

**0/12 phút riêng biệt có quote hai chiều được admit.** Không ước
lượng spread từ biên High–Low. Khi có Bid/Ask thì vẫn cần so clock,
trade/quote và gap, đồng thời giữ slippage ngoài spread là biến riêng.
Nhãn hiện tại `DATA_PATH_INCOMPLETE`, chưa có bằng chứng lặp lại
hay khả năng góp thêm tiền trên tài khoản. Không nối thực thi, mua
nguồn hoặc replay 50k dựa trên 103 lệnh đã biết.

## 3. Hướng độc lập — XAUUSD đi tiếp quanh mốc COMEX

CME tính settlement của hợp đồng vàng GC chủ động theo giao dịch
13:29–13:30 ET. Nghiên cứu của Ready & Ready ghi nhận đặc tính
khối lượng và tác động giá khác quanh giờ settlement ở futures
hàng hóa. Phép này chỉ dùng chuyển động spot làm proxy trước mốc
GC. Luật mới kiểm xem biến động có tiếp tục sau mốc thanh toán hằng
ngày. Bằng chứng futures chưa xác nhận dấu lợi thế trên CFD.
[CME quy trình settlement](https://www.cmegroup.com/tools-information/lookups/advisories/market-regulation/SER-5147.html) ·
[Ready & Ready](https://robertready.github.io/files/ready_ready_order_flows.pdf)

Khóa trước một luật. Đo từ Bid Open 12:30 tới Bid Close 13:29 New
York, cần đủ 60 phút. Nếu biến động từ ±0,20%, vào cùng chiều ở
13:30 và đo tới 15:30. Lấy stop theo extreme còn lại của giờ trước
để đo quy mô phí. Sổ markout không kích hoạt stop. Dùng nguồn Bid
M1 V14 Development, Ask proxy 0,338 USD/oz, trượt 0,20 USD/oz/side
và commission 0,0007%/side. Không swap. Giao lịch NYSE phiên thường
với guard phiên vàng đã đăng ký.

| Năm | Predictor đủ | Tín hiệu có giá | Qua cap 12% | Median stop USD/oz | Median phí / median stop | Net stress USD/oz, trung bình |
|---|---:|---:|---:|---:|---:|---:|
| 2018 | 247/247 | 38/38 | 6 | 4,27 | 17,72% | −1,907 |
| 2019 | 248/248 | 25/25 | 6 | 4,92 | 15,41% | −0,414 |
| 2020 | 250/250 | 62/62 | 40 | 7,11 | 10,72% | −3,020 |
| 2021 | 248/248 | 28/28 | 11 | 5,88 | 12,99% | −2,016 |
| 2022 | 249/250 | 45/45 | 20 | 6,17 | 12,38% | −1,210 |
| 2023 | 247/248 | 43/43 | 22 | 6,50 | 11,78% | +0,0007 |

Toàn mẫu có **241 tín hiệu có giá**, **105/241** qua cap, net stress
trung bình **−1,58 USD/oz**. Năm 2020 cho thấy stop đủ rộng chưa đảm
bảo có lãi. Năm 2023 lọt quy mô lẫn retention, nhưng mean net gần 0
và thấp hơn ma sát trung bình 0,7655 USD/oz. **0/6 năm vượt cửa
markout**. Sổ markout size tham chiếu 150 USD trên các tín hiệu qua
cap cho **−794,43 USD/năm 2018–2020** và **−203,36 USD/năm
2021–2023**. So với mục tiêu +1.000 USD/năm ở cả hai cụm, không đạt.
Gác đúng công thức `ECONOMIC_FAIL` và
`CADENCE_OR_SAMPLE_SHORTFALL`. Không dùng giá 2024–2026.

## 4. Hồ sơ kiểm chứng

Đăng ký trước số liệu mới tại SHA256
`5700860213098a9678a8432599dd2d68b9dd6fad453b6ad1bcf3809d274aeed4`
trong
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/prop-tsla-orb-confirmation-20261118/`.
Quote availability probe, nguồn gốc sổ cũ, scripts và manifest đều
lưu tại đó. Kiểm Zstandard round-trip cho cả hai artifact. Script
`verify.py` đối chiếu 103 lệnh, 12 cửa sổ quote, 1.491 mốc giờ và
tính lại 241 markout/105 tín hiệu qua cap từ binary gốc và Fraction.
Rollout này chưa chạy account, thay risk, mua dữ liệu hay truy cập
broker. `BASE_GUARD` vẫn `NOT_QUALIFIED`.

# BTC/USD tiếp diễn 24 giờ và đường cong VIX — kết quả Stage‑0

**Gác cả hai công thức.** BTC/USD đạt tần suất và quy mô stop, nhưng
markout toàn mẫu âm trong cả sáu năm ngay ở kịch bản chỉ trừ
commission. US500 mua sau khi đường cong VIX đảo ngược có một năm
tham chiếu vượt 1.000 USD, nhưng hụt tần suất 4/6 năm và không đạt
1.000 USD/năm trong bất kỳ cụm ba năm nào. Chưa có cơ sở replay cùng
BASE_GUARD. [Mốc so quy mô và mục tiêu](PROP-PAYOUT-REPLAY-DECISION-20261118.md)

## BTC/USD — dùng cùng mức phơi nhiễm để đo lợi thế tăng thêm

Bài Liu–Tsyvinski trên dữ liệu CoinDesk tới 31/05/2018 ước lượng một
độ lệch chuẩn lợi suất hôm nay gắn với mức tăng dự báo khoảng 0,33
điểm phần trăm ngày sau. Kết quả đó là hệ số hồi quy trong mẫu của
tác giả. Phép thử của dự án dùng Bitstamp và một quy tắc định trước.
Lúc 00:00 UTC, lấy lợi suất close-to-close ngày vừa kết thúc. Nếu
độ lớn ít nhất bằng một độ lệch chuẩn của **30 lợi suất trước đó**,
đi theo dấu. Vào bằng H1 Open 01:00 UTC sau một giờ chờ, ra cùng
giờ hôm sau. Chỉ nhận từ thứ Hai tới thứ Năm, tối đa một vị thế,
đóng trước khi mở tiếp ở cùng timestamp. Stop tự nhiên ở ngoài
extreme ngày vừa đóng một cent. Chưa kích hoạt stop trong phép đo
markout. [Liu–Tsyvinski, §2 và §4.1](https://www.nber.org/system/files/working_papers/w24877/w24877.pdf)

### Nguồn, phí và điều kiện đích

- **Bitstamp BTC/USD.** 74 request có đầu và cuối xác định, đủ
  **52.584/52.584** khóa H1, 2.191 ngày UTC. Bảy nến do nguồn trả
  về có volume 0. Chúng không nằm trên 312 đường nắm giữ và bỏ
  chúng khỏi phép tổng hợp vẫn cho cùng OHLC ngày. Đối chiếu
  Coinbase BTC-USD tại 12 mốc 01:00 UTC khóa trước. Chênh Open
  tuyệt đối trung vị 1,88 bp, lớn nhất 8,71 bp. Đây là chênh giữa hai
  sàn spot. Binance BTC/USDT không được lấy làm chứng cứ spread
  BTC/USD. [Bitstamp](https://www.bitstamp.net/api/) ·
  [Coinbase](https://docs.cdp.coinbase.com/api-reference/exchange-api/rest-api/products/get-product-candles)
- **Commission có nguồn.** FTMO công bố BTCUSD 1 BTC/lot, tối đa
  5 lot/lệnh và 0,0325% notional **mỗi chiều** từ 28/07/2025.
  Dùng làm giá tham chiếu triển khai trên lịch sử, không gán là
  phí FTMO 2018–2023. Mỗi giao dịch tính theo giá vào và ra.
  [FTMO Trading Update](https://ftmo.com/en/blog/trading-updates/trading-update-24-jul-2025/)
- **Spread, slip và swap.** Ngoài commission, reference giả định
  5 bp giá vào cho spread+slip vòng lệnh và 5 bp carry. Stress dùng
  15 + 15 bp, cả BUY lẫn SELL đều debit. Mỗi cửa giữ đi qua một
  mốc nửa đêm Prague. Giờ post swap, số điểm từng chiều và ngày
  charge nhiều lần của BTCUSD trên đúng server chưa xác minh.
  Markout stress chịu trung bình khoảng 36,51 bp trên nhóm giữ được.
  Chưa xác minh mức spread, gap hoặc slippage thực thi CFD.
- **Ký quỹ và phiên.** Dùng Swing 1:1 theo tài liệu FTMO, lot step
  0,01 là giả định. Cỡ tối đa trong mẫu chiếm 4.357,95 USD ký quỹ
  ở 1:1. FTMO cho Swing giữ qua kỳ đóng dài. Giờ crypto và bảo
  trì có thể đổi theo nền tảng. Mặt nạ thứ Hai–thứ Năm giảm rủi ro
  giờ cuối tuần thường lệ, chưa chứng nhận mốc 01:00, lịch cũ
  hay các ngày bảo trì bất thường. Chưa có bằng chứng mức dừng
  tối thiểu và quy tắc stop-market của tài khoản đích.
  [FTMO đòn bẩy theo nhóm](https://ftmo.com/en/blog/a-few-answers-to-your-questions/) ·
  [FTMO giờ phiên](https://ftmo.com/en/symbols/) ·
  [FTMO giữ qua kỳ đóng](https://ftmo.com/en/faq/can-i-hold-positions-overnight-or-over-the-weekend/)

### Kết quả 2018–2023

Đủ đầu vào cả **1.232** ngày được xét sau warm-up. Đủ endpoint và
path H1 cho **312/312** tín hiệu. 22 tín hiệu bị loại bởi cap phí,
còn **290 (92,9%)** ở stress. `bp` là một phần trăm của một điểm
phần trăm (100 bp = 1%). Cột USD dùng size làm tròn xuống trong
ngân sách risk 150 USD gồm dự phòng phí. PnL chốt ở mốc cố định,
khác tiền rút tài khoản.

| Năm | Raw / qua cap | Phí stress / stop trung vị | Raw mean sau commission / reference / stress (bp) | USD stress ở nhóm qua cap |
|---|---:|---:|---:|---:|
| 2018 | 46 / 45 | 5,48% | −15,53 / −25,53 / −45,53 | −590,76 |
| 2019 | 44 / 43 | 4,73% | −97,30 / −107,30 / −127,30 | −740,07 |
| 2020 | 57 / 50 | 6,40% | −3,04 / −13,04 / −33,04 | +30,03 |
| 2021 | 62 / 62 | 5,44% | −1,47 / −11,47 / −31,47 | −223,35 |
| 2022 | 52 / 47 | 6,14% | −21,85 / −31,85 / −51,85 | −684,79 |
| 2023 | 51 / 43 | 8,38% | −36,12 / −46,12 / −66,12 | −1.233,22 |

**Tách lợi thế tín hiệu khỏi BTC tăng giá.** Đối chứng all-long
dùng chính các ngày và đơn vị BTC mà mô hình giao dịch, cùng phí.
Đối chứng xáo dấu là kỳ vọng khi hoán đổi BUY/SELL trong từng
tháng, giữ thời điểm, size, số lượng theo chiều và phí. Cả hai
đo quy thuộc lợi thế, không được dùng ra quyết định vào lệnh.

| Cụm | BTC stress USD/năm | All-long USD/năm | Xáo dấu USD/năm | Chênh BTC so với all-long / xáo dấu |
|---|---:|---:|---:|---:|
| 2018–2020 | −433,60 | −245,51 | +133,11 | −188,10 / −566,71 |
| 2021–2023 | −713,79 | −86,35 | −441,44 | −627,44 / −272,34 |
| Cả 6 năm | −573,69 | −165,93 | −154,17 | −407,77 / −419,53 |

Phí bằng 0 vẫn âm ở cỡ vị thế đã chọn. Gross tính theo notional
bình quân có trọng số là **−16,87 bp**, nên không tồn tại mức phí
không âm để hòa vốn trên nhóm này. Sau commission cần một khoản
bù 23,38 bp mới về 0. Tổng reference **−2.152,45 USD**, stress
**−3.442,16 USD**. BUY 162 lệnh **−1.207,69 USD**, SELL 128 lệnh
**−2.234,47 USD** dưới stress. Không chọn lại một chiều.

Phần trùng **lịch** mẫu tác giả tới 31/05/2018 có 17 lệnh qua cap
và −409,56 USD stress. Từ sau mẫu tới trước ngày bản làm việc SSRN
06/08/2018 có 12 lệnh, +163,81 USD. Từ ngày công bố đó có 261 lệnh,
**−3.196,41 USD stress**. Giá Bitstamp và quy tắc riêng của dự án
khác bộ CoinDesk và hồi quy của tác giả.
[Ngày bản làm việc](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3226952)

### Chỗ trống rủi ro và khoảng đệm

Trong hai sổ V19 PRIMARY/STRICT dùng tham chiếu cố định, có
**64/290** cửa BTC chồng thời gian với vị thế BASE. Tối đa 3 vị thế
cùng lúc khi đếm BTC. Với 150 USD/vị thế, mức tham chiếu là
450 USD risk định mức. Giả định rất chặt chỉ nhận lệnh BTC hoàn
toàn không chồng BASE còn **226**, và stress vẫn **−2.983,46 USD**
toàn kỳ, khoảng **−497,24 USD/năm**. Đây là phép kiểm sự cạnh
tranh thời gian và ngân sách, chưa đo fill, margin hay PnL khi ghép
ở cấp tài khoản.

Đường tài khoản BTC riêng trên vốn 50.000 USD giữ nguyên cửa 24h
không kích hoạt SL. Dùng biên bất lợi H1 và tính lỗ ngày theo
balance lúc reset Prague, đã dự phòng chi phí mô hình. Lỗ ngày
xấu nhất **408,12 USD (0,82%)**, dưới mốc đệm 3%. Lỗ sâu nhất
dưới vốn đầu **3.597,03 USD (7,19%)**, vượt mốc đệm 6,5%.
Peak-to-valley theo số dư chốt kỳ **3.822,58 USD (7,65%)**.
Có 38 lệnh mà biên H1 đi qua mức stop đo được. Lần chạm đầu
trên H1 không có trường hợp Open đã vượt stop. Giá đi trong giờ
và gap CFD vẫn chưa biết. Các con số là chẩn đoán spot cho
markout, chưa đo hoặc chứng nhận Daily/Overall Loss FTMO.

**Phán quyết BTC.** `ECONOMIC_FAIL`, 0/6 năm vượt cổng markout.
Mẫu đạt cadence, retention và natural scale. Thiếu nguồn CFD
vẫn chặn thực thi, nhưng bổ sung giá đích chưa có cơ sở đổi
quyết định kinh tế ở phép thử này. Không replay BASE hay tăng risk.

## Phép thử độc lập — US500 khi VIX 30 ngày vượt VIX 3 tháng

Chỉ dùng VIX và VIX3M cuối **phiên trước**, không dùng giá cổ phiếu
làm điều kiện như nghiên cứu VIX/price divergence. Khi VIX > VIX3M,
mua US500 phiên đầy đủ tiếp theo ở 10:30 New York và đo đến 15:30.
Tín hiệu thể hiện biến động kỳ vọng tập trung ở đầu đường cong.
Nghiên cứu về VIX futures là động cơ cho giả thuyết hồi phục,
chưa chứng minh chính biện pháp VIX/VIX3M spot này. Giá US500
Bid/Ask M1 native có spread, phí cộng ngoài spread là
2,50 điểm/vòng. Stop tham chiếu dưới đáy giờ mở phiên, chưa kích
hoạt SL. [Cboe kỳ hạn](https://www.cboe.com/tradable_products/vix/term_structure) ·
[FRED VIX](https://fred.stlouisfed.org/series/VIXCLS) ·
[FRED VIX3M](https://fred.stlouisfed.org/series/VXVCLS) ·
[Nghiên cứu VIX futures](https://www.mdpi.com/1911-8074/12/3/113) ·
[Phép thử VIX/giá cũ](PROP-US500-VIX-DIVERGENCE-RESULTS-20261118.md)

| Năm | Tín hiệu có giá | Qua cap 12% | Phí/stop trung vị | Net stress điểm/lệnh thô | USD ở nhóm qua cap |
|---|---:|---:|---:|---:|---:|
| 2018 | 51/51 | 6 | 28,29% | −3,99 | −994,02 |
| 2019 | 14/14 | 3 | 24,53% | +10,10 | +168,05 |
| 2020 | 53/53 | 22 | 12,68% | −7,80 | −932,01 |
| 2021 | 2/2 | 2 | 7,64% | +11,27 | +66,38 |
| 2022 | 15/15 | 8 | 10,49% | +10,23 | +1.097,42 |
| 2023 | 0 | 0 | — | — | 0 |

Đủ dữ liệu kỳ hạn cho 1.496 phiên sau warm-up, đủ đầu–cuối
cho **135/135** tín hiệu, 5 thiếu 60 phút mở phiên cần để đo
stop. Có **41/135** qua cap. Cụm 2018–2020 cho **−585,99 USD/năm**
so với −432,55 USD/năm của đối chứng mua mọi ngày đủ điều kiện,
đã quy cùng tổng risk theo năm. Cụm 2021–2023 cho **+387,94 USD/năm**
so với +35,95 USD/năm của đối chứng. 2022 có kết quả dương lớn,
nhưng chỉ 8 lệnh qua cap và 2023 không có tín hiệu. Không đáp
ứng mục tiêu 1.000 USD/năm qua cả hai cụm hoặc 40 tín hiệu/năm.
Gác công thức, giữ số dương lẫn âm trong lịch sử lựa chọn.

### Reproducibility

Khóa quy tắc trước outcome. SHA256 bản đăng ký
`39e1435a3b8d64be9428f2a6a14bf666198b1ffa21bd8a72b82fc109f41dda65`.
Lưu API ranges, source hashes, cross-venue probes, scripts và hai
kết quả Zstandard tại
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/prop-btc-momentum-and-vix-curve-20261118/`.
Verify bằng Fraction tái lập 1.232 quyết định, 312 tín hiệu BTC và
đối chiếu 135 tín hiệu VIX cùng nhóm risk/cost. Kiểm riêng ảnh hưởng
bảy dòng volume 0. Phép chạy VIX đầu dừng trước đọc giá vì index
có partition warm-up 2017. Lượt chính chọn đúng partitions
2018–2023, giữ nguyên luật. Không truy cập thị trường live,
tài khoản hay giá 2024–2026. Giữ BASE_GUARD `NOT_QUALIFIED`.

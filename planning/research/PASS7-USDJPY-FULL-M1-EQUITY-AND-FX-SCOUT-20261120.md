# Pass 7 · USDJPY M1 và FX Tokyo-box scout

**USDJPY M1 và equity chờ dữ liệu QDM. Cả ba mã FX scout rớt Stage-0.**
Đã kiểm protocol [QDM CLI-only](PASS7-USDJPY-FULL-M1-EQUITY-AND-FX-SCOUT-PROTOCOL-20261120.md) tại `9b806c2` trước khi
chạy shortlist. Development 2018–2024, A 2018–2020, B 2021–2024.
Giá từ 01/01/2025 giữ khóa. Mọi kết quả dưới đây thuộc Development
đã có exposure.

## USDJPY · Kênh QDM CLI và khoảng trống dữ liệu

Hai yêu cầu thử kênh trực tiếp trước chỉ thị sửa trả HTTP 429. Pass 7 chuyển
sang QDM CLI theo chỉ thị của owner. Giá gốc của QDM vẫn là Dukascopy.
Kiểm bộ cài local **125.2692** qua `-h` và `-symbol action=list`.
CLI trả **5 symbol, 0 USDJPY**. Các đường dẫn đã kiểm chỉ tìm được
một bộ cài QDM. Chỉ đọc metadata, không xuất giá. Các cache trực tiếp
R084/R085 gắn với kết quả lịch sử Pass 6 và nằm ngoài input Pass 7.

StrategyQuant xác nhận `-data action=update` bỏ qua `dateto`. Dùng
`datefrom/dateto` trong lệnh export chỉ giới hạn khoảng xuất. Pass 7
cần cache USDJPY sẵn có hoặc QDM CLI có cổng khóa cả khoảng tải.
[StrategyQuant về điều kiện update](https://strategyquant.com/forum/topic/qdmcli-exe-update-resume-ohne-uberschreiben/).

| Cụm | Ngày trong tuần | Ngày QDM M1 Bid/Ask đủ chuẩn | Ngày đủ phút ở Pass 6 để tham chiếu |
| --- | ---: | ---: | ---: |
| A 2018–2020 | 784 | 0 | 147 |
| B 2021–2024 | 1.043 | 0 | 227 |
| Toàn kỳ | 1.827 | 0 | 374 |

Pass 5 H1 Bid với Ask proxy đạt **+29,09R/năm**, 6/7 năm dương và
drawdown lệnh đóng **23,82R**. Pass 6 H1 stress mạnh nhất còn **+9,38R/năm**,
5/7 năm dương và DD đóng **37,65R**. 339 cặp H1/M1 của Pass 6 giữ
`+54,51R / +60,50R` trên mẫu ngày rời rạc đã dùng trước đây.
Các phép đo QDM `M1_Real_Base`, thêm **0,50 pip** và **1,00 pip**,
floating DD theo R và số phút mơ hồ ở Pass 7 đều chưa có kết quả.
[Pass 5](PASS5-USDJPY-TOKYO-BOX-STAGE0-20261120.md) ·
[Pass 6](PASS6-USDJPY-HIRES-AND-XAUUSD-PORTFOLIO-20261120.md).

| Risk/lệnh | 10k Swing 1:30 | 25k Swing 1:30 | 50k Standard 1:100 |
| --- | --- | --- | --- |
| 0,20% | Chưa đo | Chưa đo | Chưa đo |
| 0,25% | Chưa đo | Chưa đo | Chưa đo |
| 0,30% | Chưa đo | Chưa đo | Chưa đo |
| 0,40% | Chưa đo | Chưa đo | Chưa đo |

Net %/USD mỗi năm, equity peak-to-trough, Daily Loss theo balance
00:00 Prague, lỗ tĩnh, biên margin và làm tròn 0,01 lot cần replay
cùng chuỗi Bid/Ask. Cả Swing và Standard `PROP_UNMEASURED`. Mốc
5% Daily / 10% Static thuộc FTMO 2-Step, chưa có kết luận sống sót.
[FTMO Comparison Table](https://ftmo.com/en/comparison-table/) ·
[FTMO Academy về Daily Loss](https://academy.ftmo.com/lesson/maximum-daily-loss/).

## Scout Stage-0 · EURJPY, EURUSD, GBPUSD

Dùng H1 Bid/D1 native FTMO đã seal theo SHA. Tái dùng hộp Pass 5
00:00–03:00 UTC, OCO đến trước 10:00 UTC, ba mốc thoát đã đăng ký.
Các phép đo Breakout và Fade dùng cùng sự kiện. Phí 5 USD khứ hồi mỗi
lot, slip 0,20 pip mỗi phía, swap 0, và spread proxy từ 36f1535.
EURJPY quy tiền từ JPY theo open USDJPY đồng thời tại exit. EURUSD
và GBPUSD có quote currency USD. Một lượt quy ước 100.000 đơn vị
đồng cơ sở. Bảng ghi tổng net USD trước sizing.

| Mã | Mẫu | H1 dual-touch ngay lần đầu | Stop trung vị pip | Median phí/stop +4h | Số cơ hội ≤12% |
| --- | ---: | ---: | ---: | ---: | ---: |
| EURJPY | 1720 | 26 | 30,60 | 6,09% | 92,03% |
| EURUSD | 1768 | 30 | 15,50 | 6,45% | 91,63% |
| GBPUSD | 1740 | 48 | 19,80 | 8,08% | 81,78% |

| Mã | Mốc | Breakout A | Fade A | Breakout B | Fade B | Năm Breakout dương | Breakout bỏ hai năm tốt nhất | Breakout bỏ Top 10 ngày |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| EURJPY | +4 giờ | -18.569,15 | -6.063,01 | 1.410,42 | -31.074,65 | 3/7 | -19.715,86 | -29.207,83 |
| EURJPY | +8 giờ | -22.745,52 | -1.885,53 | -16.162,85 | -13.497,72 | 1/7 | -37.637,42 | -53.828,03 |
| EURJPY | 18:00 EET/EEST | -25.895,93 | 1.265,26 | -17.437,78 | -12.223,34 | 1/7 | -45.293,48 | -58.943,55 |
| EURUSD | +4 giờ | -12.459,50 | -2.580,50 | -10.813,50 | -9.506,50 | 1/7 | -24.411,50 | -33.416,00 |
| EURUSD | +8 giờ | -11.532,50 | -3.507,50 | -20.359,50 | 39,50 | 3/7 | -39.008,00 | -44.873,00 |
| EURUSD | 18:00 EET/EEST | -11.073,50 | -3.966,50 | -11.541,50 | -8.778,50 | 2/7 | -38.219,50 | -37.900,00 |
| GBPUSD | +4 giờ | -8.956,00 | -14.404,00 | -14.919,00 | -17.401,00 | 1/7 | -27.276,00 | -36.338,00 |
| GBPUSD | +8 giờ | 2.282,00 | -25.642,00 | -41.807,00 | 9.487,00 | 1/7 | -47.939,00 | -57.960,00 |
| GBPUSD | 18:00 EET/EEST | -8.061,00 | -15.299,00 | -34.501,00 | 2.181,00 | 2/7 | -44.465,00 | -67.765,00 |

Cả ba mã qua cổng quy mô phí. Nút thắt là lợi thế định hướng sau phí.
EURJPY +4h chỉ dương cụm B. GBPUSD +8h chỉ dương cụm A. GBPUSD +4h
thắng Fade và gross dương ở cả hai cụm nhưng net âm ở cả hai.
Cả ba mã `REJECTED_AT_STAGE0`, không có mã `PROMOTE_TO_PASS8_M1_CHECK`.
Cổng đóng trước SL-active. Tương quan ngày USDJPY lỗ chưa đo.

### Bảng năm và chiều giao dịch

Mỗi hàng ghi `net tổng (BUY / SELL)` theo USD. Cột Fade phân chiều
theo lệnh Fade, do đó BUY của Fade ứng với SELL của Breakout.

| Mã | Mốc | Năm | N | Breakout net (BUY / SELL) | Fade net (BUY / SELL) |
| --- | --- | ---: | ---: | ---: | ---: |
| EURJPY | +4 giờ | 2018 | 244 | -1.580,36 (-4.005,24 / 2.424,88) | -6.603,95 (-5.981,31 / -622,64) |
| EURJPY | +4 giờ | 2019 | 233 | -9.076,08 (-4.106,17 / -4.969,92) | 1.187,09 (1.211,06 / -23,97) |
| EURJPY | +4 giờ | 2020 | 249 | -7.912,70 (-4.022,92 / -3.889,79) | -646,15 (-542,88 / -103,27) |
| EURJPY | +4 giờ | 2021 | 251 | -1.734,54 (-1.455,17 / -279,37) | -6.718,86 (-3.760,51 / -2.958,34) |
| EURJPY | +4 giờ | 2022 | 249 | 587,83 (101,16 / 486,66) | -8.030,32 (-3.723,94 / -4.306,38) |
| EURJPY | +4 giờ | 2023 | 249 | 927,37 (1.002,63 / -75,26) | -8.033,46 (-3.011,07 / -5.022,39) |
| EURJPY | +4 giờ | 2024 | 245 | 1.629,76 (278,38 / 1.351,38) | -8.292,02 (-4.240,54 / -4.051,49) |
| EURJPY | +8 giờ | 2018 | 244 | -7.264,83 (-9.127,91 / 1.863,08) | -919,27 (-5.419,40 / 4.500,13) |
| EURJPY | +8 giờ | 2019 | 233 | -10.663,49 (-7.363,59 / -3.299,90) | 2.774,47 (-458,84 / 3.233,31) |
| EURJPY | +8 giờ | 2020 | 249 | -4.817,20 (1.927,63 / -6.744,83) | -3.740,74 (2.312,48 / -6.053,22) |
| EURJPY | +8 giờ | 2021 | 251 | -1.811,42 (-1.320,01 / -491,41) | -6.641,46 (-3.548,06 / -3.093,40) |
| EURJPY | +8 giờ | 2022 | 249 | 540,48 (237,21 / 303,26) | -7.981,71 (-3.540,15 / -4.441,56) |
| EURJPY | +8 giờ | 2023 | 249 | -7.921,30 (-4.276,95 / -3.644,35) | 816,18 (558,17 / 258,01) |
| EURJPY | +8 giờ | 2024 | 245 | -6.970,60 (-2.245,95 / -4.724,65) | 309,28 (1.836,37 / -1.527,09) |
| EURJPY | 18:00 EET/EEST | 2018 | 244 | -5.955,74 (-12.336,53 / 6.380,79) | -2.229,09 (-9.938,22 / 7.709,13) |
| EURJPY | 18:00 EET/EEST | 2019 | 233 | -15.624,69 (-9.126,40 / -6.498,30) | 7.736,26 (2.740,24 / 4.996,02) |
| EURJPY | 18:00 EET/EEST | 2020 | 249 | -4.315,50 (936,42 / -5.251,92) | -4.241,90 (819,66 / -5.061,56) |
| EURJPY | 18:00 EET/EEST | 2021 | 251 | -6.447,53 (-5.564,25 / -883,29) | -2.005,74 (-3.156,04 / 1.150,30) |
| EURJPY | 18:00 EET/EEST | 2022 | 249 | 6.275,26 (3.854,51 / 2.420,75) | -13.716,65 (-5.657,60 / -8.059,06) |
| EURJPY | 18:00 EET/EEST | 2023 | 249 | -11.225,50 (-5.616,76 / -5.608,75) | 4.120,34 (2.522,51 / 1.597,83) |
| EURJPY | 18:00 EET/EEST | 2024 | 245 | -6.040,01 (-3.275,19 / -2.764,82) | -621,28 (-123,70 / -497,58) |
| EURUSD | +4 giờ | 2018 | 251 | -7.412,50 (-6.260,50 / -1.152,00) | 2.392,50 (-1.048,00 / 3.440,50) |
| EURUSD | +4 giờ | 2019 | 250 | -6.930,50 (-3.793,00 / -3.137,50) | 1.930,50 (797,50 / 1.133,00) |
| EURUSD | +4 giờ | 2020 | 251 | 1.883,50 (-1.609,50 / 3.493,00) | -6.903,50 (-5.573,00 / -1.330,50) |
| EURUSD | +4 giờ | 2021 | 255 | -1.124,50 (115,00 / -1.239,50) | -3.975,50 (-1.580,50 / -2.395,00) |
| EURUSD | +4 giờ | 2022 | 252 | -745,00 (1.899,50 / -2.644,50) | -4.295,00 (24,50 / -4.319,50) |
| EURUSD | +4 giờ | 2023 | 253 | -3.534,00 (-3.294,00 / -240,00) | -1.526,00 (-2.220,00 / 694,00) |
| EURUSD | +4 giờ | 2024 | 256 | -5.410,00 (-3.184,00 / -2.226,00) | 290,00 (-374,00 / 664,00) |
| EURUSD | +8 giờ | 2018 | 251 | -11.629,50 (-11.919,50 / 290,00) | 6.609,50 (-2.490,00 / 9.099,50) |
| EURUSD | +8 giờ | 2019 | 250 | -6.027,50 (-4.094,00 / -1.933,50) | 1.027,50 (-406,50 / 1.434,00) |
| EURUSD | +8 giờ | 2020 | 251 | 6.124,50 (2.784,50 / 3.340,00) | -11.144,50 (-5.420,00 / -5.724,50) |
| EURUSD | +8 giờ | 2021 | 255 | 991,50 (1.565,00 / -573,50) | -6.091,50 (-2.246,50 / -3.845,00) |
| EURUSD | +8 giờ | 2022 | 252 | 578,00 (-2.429,50 / 3.007,50) | -5.618,00 (-5.627,50 / 9,50) |
| EURUSD | +8 giờ | 2023 | 253 | -8.764,00 (-7.635,00 / -1.129,00) | 3.704,00 (-1.331,00 / 5.035,00) |
| EURUSD | +8 giờ | 2024 | 256 | -13.165,00 (-9.333,00 / -3.832,00) | 8.045,00 (1.232,00 / 6.813,00) |
| EURUSD | 18:00 EET/EEST | 2018 | 251 | -16.809,50 (-16.050,50 / -759,00) | 11.789,50 (-1.441,00 / 13.230,50) |
| EURUSD | 18:00 EET/EEST | 2019 | 250 | -2.543,50 (-4.647,00 / 2.103,50) | -2.456,50 (-4.443,50 / 1.987,00) |
| EURUSD | 18:00 EET/EEST | 2020 | 251 | 8.279,50 (1.860,50 / 6.419,00) | -13.299,50 (-8.499,00 / -4.800,50) |
| EURUSD | 18:00 EET/EEST | 2021 | 255 | -2.709,50 (-3.159,00 / 449,50) | -2.390,50 (-3.269,50 / 879,00) |
| EURUSD | 18:00 EET/EEST | 2022 | 252 | 7.325,00 (3.597,50 / 3.727,50) | -12.365,00 (-6.347,50 / -6.017,50) |
| EURUSD | 18:00 EET/EEST | 2023 | 253 | -6.761,00 (-7.612,00 / 851,00) | 1.701,00 (-3.311,00 / 5.012,00) |
| EURUSD | 18:00 EET/EEST | 2024 | 256 | -9.396,00 (-8.363,00 / -1.033,00) | 4.276,00 (-1.567,00 / 5.843,00) |
| GBPUSD | +4 giờ | 2018 | 251 | -9.110,00 (-9.518,00 / 408,00) | 1.078,00 (-3.896,00 / 4.974,00) |
| GBPUSD | +4 giờ | 2019 | 227 | -3.285,50 (-4.633,50 / 1.348,00) | -3.978,50 (-4.804,00 / 825,50) |
| GBPUSD | +4 giờ | 2020 | 252 | 3.439,50 (4.259,00 / -819,50) | -11.503,50 (-3.244,50 / -8.259,00) |
| GBPUSD | +4 giờ | 2021 | 253 | -38,50 (1.473,00 / -1.511,50) | -8.057,50 (-2.680,50 / -5.377,00) |
| GBPUSD | +4 giờ | 2022 | 250 | -7.263,00 (-3.478,00 / -3.785,00) | -737,00 (-567,00 / -170,00) |
| GBPUSD | +4 giờ | 2023 | 252 | -7.251,50 (-8.411,50 / 1.160,00) | -812,50 (-5.000,00 / 4.187,50) |
| GBPUSD | +4 giờ | 2024 | 255 | -366,00 (543,00 / -909,00) | -7.794,00 (-3.251,00 / -4.543,00) |
| GBPUSD | +8 giờ | 2018 | 251 | -6.132,00 (-7.590,00 / 1.458,00) | -1.900,00 (-4.946,00 / 3.046,00) |
| GBPUSD | +8 giờ | 2019 | 227 | -526,50 (-3.442,50 / 2.916,00) | -6.737,50 (-6.372,00 / -365,50) |
| GBPUSD | +8 giờ | 2020 | 252 | 8.940,50 (6.260,00 / 2.680,50) | -17.004,50 (-6.744,50 / -10.260,00) |
| GBPUSD | +8 giờ | 2021 | 253 | -10.289,50 (-686,00 / -9.603,50) | 2.193,50 (5.411,50 / -3.218,00) |
| GBPUSD | +8 giờ | 2022 | 250 | -8.509,00 (-9.755,00 / 1.246,00) | 509,00 (-5.598,00 / 6.107,00) |
| GBPUSD | +8 giờ | 2023 | 252 | -17.403,50 (-13.802,50 / -3.601,00) | 9.339,50 (-239,00 / 9.578,50) |
| GBPUSD | +8 giờ | 2024 | 255 | -5.605,00 (-3.958,00 / -1.647,00) | -2.555,00 (-2.513,00 / -42,00) |
| GBPUSD | 18:00 EET/EEST | 2018 | 251 | -9.964,00 (-9.777,00 / -187,00) | 1.932,00 (-3.301,00 / 5.233,00) |
| GBPUSD | 18:00 EET/EEST | 2019 | 227 | 23,50 (-1.550,50 / 1.574,00) | -7.287,50 (-5.030,00 / -2.257,50) |
| GBPUSD | 18:00 EET/EEST | 2020 | 252 | 1.879,50 (1.216,00 / 663,50) | -9.943,50 (-4.727,50 / -5.216,00) |
| GBPUSD | 18:00 EET/EEST | 2021 | 253 | -12.447,50 (-6.063,00 / -6.384,50) | 4.351,50 (2.192,50 / 2.159,00) |
| GBPUSD | 18:00 EET/EEST | 2022 | 250 | -6.481,00 (-7.610,00 / 1.129,00) | -1.519,00 (-5.481,00 / 3.962,00) |
| GBPUSD | 18:00 EET/EEST | 2023 | 252 | -12.085,50 (-10.049,50 / -2.036,00) | 4.021,50 (-1.804,00 / 5.825,50) |
| GBPUSD | 18:00 EET/EEST | 2024 | 255 | -3.487,00 (-3.046,00 / -441,00) | -4.673,00 (-3.719,00 / -954,00) |

## Kiểm chứng và đường tiếp tục

29 unit tests đạt, 0 skip. Sau khi tái dùng code Pass 5 cho quy đổi
FX, **ba tệp Pass 5 khớp từng byte** với kết quả cũ, gồm 1.645 lệnh
SL-active. Scout tái cộng gross, spread, commission, slippage, cost và
net theo từng năm/chiều từ 5.228 sự kiện. Holdout đọc 0 tệp giá,
OrderSend 0. Thay kênh lấy giá trong [workflow](../../tooling/ai-engines/STRATEGY-WORKFLOW.md)
và protocol trước dùng giá mới. Tệp archive và receipt cũ chỉ phục vụ
đối soát các lượt trước.

Ưu tiên giải quyết nguồn USDJPY cache QDM Bid/Ask 2018–2024. Sau đó
chạy đúng protocol M1/equity đã khóa cho USDJPY. M1 và equity vẫn là
cổng trước mô phỏng Challenge; Pass 7 chưa có mã ghép rổ.

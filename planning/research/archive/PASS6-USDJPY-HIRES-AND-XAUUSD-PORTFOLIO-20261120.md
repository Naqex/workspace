# Pass 6 · USDJPY độ phân giải cao, Stage-0 XAUUSD và chẩn đoán ghép rổ

**Giữ USDJPY để kiểm tiếp. Gác cấu hình XAUUSD đã đăng ký.**
USDJPY dương trong cả hai cụm dưới stress H1 mạnh nhất nhưng giảm từ
**+29,09 xuống +9,38R/năm** và DD lệnh đóng tăng từ **23,82 lên 37,65R**.
Đối chiếu M1 cùng ngày cũng giảm từ **+60,50 xuống +54,51R**.
Danh mục hai mã dừng tại cổng đầu vào. Swing và Standard đều `PROP_UNMEASURED`.

Development 2018–2024. Cụm A 2018–2020, cụm B 2021–2024.
[Protocol khóa trước khi chạy](PASS6-USDJPY-HIRES-AND-XAUUSD-PROTOCOL-20261120.md)
tại `e6cec0a`. [Sổ Pass 5](PASS5-USDJPY-TOKYO-BOX-STAGE0-20261120.md)
tại `52a824c`. Tỷ trọng 80/20 là trọng tâm nghiên cứu Swing/Standard.
Cả hai cấu hình nghiên cứu đóng trong ngày, mô hình swap bằng 0.
Phân vùng giá từ 01/01/2025 giữ nguyên khóa.

## 1. Nguồn giá và giới hạn

Các đường dẫn private dưới `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs`.
Kiểm tra metadata/locator cho các nguồn ngoài lát chạy. Chỉ đọc giá ở ba
nguồn Development ghi dưới đây. Các view tick khác nhau có giao nhau.

| Mã và nguồn | Giá, độ phủ | Vai trò |
| --- | --- | --- |
| USDJPY `bottleneck2-monfri-20261119/development` | Native FTMO H1 Bid 2018–2024, 43.553 nến, Ask proxy | Stress toàn kỳ, replay từ phân vùng seal |
| USDJPY `challenge-discovery4-20261108/execution-v1/jpy-tokyo-source-v1` và `jpy-postfix-source-v1` | Dukascopy M1 Bid/Ask R084/R085, 487 ngày lịch fix rời rạc 2018–2024 | 374 ngày có đủ phút nguồn, 113 ngày thiếu ít nhất một phút. Không tính nến do adapter điền |
| USDJPY fixture, file rời | Fixture 2013/2019 và 4 file M15 năm 2022 | Không đủ để xác minh cả chuỗi |
| XAUUSD `challenge-discovery4-20261108/execution-v1/gold-continuous-B2-20261113-v1/source-cache` | QDM M1 Bid, 2.480.606 nến từ 01/01/2018 23:00 đến 31/12/2024 21:58 UTC, Ask proxy +0,35 USD/oz | Stage-0. Cache Development gắn hash manifest, cutoff exclusive `1735689600` |
| XAUUSD tick Bid/Ask đã lưu tại các job B0 và H1 execution | B0 761/753/741 giờ chọn trước năm 2022/23/24. H1 execution 6.972/6.384 giờ năm 2022/23 và validation 6.416 giờ năm 2024 | View chọn theo giờ của các nghiên cứu cũ. Chưa có chuỗi tick liên tục cả bảy năm |
| XAUUSD nguồn V14 | Bid, Ask proxy 0,338 USD/oz. Bản Development kết thúc đầu 2024 | File bin gộp ngoài phạm vi chưa mở |

Chưa tìm thấy chuỗi USDJPY M1/M5/tick Bid/Ask liên tục 2018–2024 hay
XAUUSD Ask/tick liên tục cùng kỳ trong kho đã kiểm kê. Chênh lệch giữa H1
và M1 gồm cả feed khác nhau, spread quan sát được và cách dựng biên hộp.
Cực trị Bid/Ask M1 có thể xảy ra ở các tick khác nhau. Vì vậy cực trị mid
từ OHLC là xấp xỉ và thứ tự nội phút vẫn cần tick để xác minh.

## 2. USDJPY · SL đối diện hộp Tokyo

Giữ hộp 00:00–03:00 UTC, kích hoạt OCO 03:00–10:00 UTC và flat 18:00
Europe/Helsinki. M1 dùng Ask mở BUY/đóng SELL và Bid mở SELL/đóng BUY.
Trường hợp cả hai cạnh chạm ở lần đầu dùng kết quả xấu hơn. Nếu phút mở
cũng chạm SL, buộc đóng tại SL. Dùng 5 USD/lot commission khứ hồi và
0,20 pip slippage mỗi phía. 1R là khoảng cách từ entry đến stop tự nhiên
quy đổi theo notional mô hình.

| Năm | Ngày R084/R085 | Đủ phút Bid/Ask | Fills M1 | Ngày ghép H1/M1 | H1 R ghép | M1 R ghép |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2018 | 70 | 59 | 54 | 54 | +4,46 | +4,34 |
| 2019 | 69 | 47 | 40 | 39 | +2,39 | +1,32 |
| 2020 | 69 | 41 | 38 | 38 | +14,93 | +14,54 |
| 2021 | 69 | 32 | 32 | 30 | +0,56 | -3,53 |
| 2022 | 70 | 67 | 62 | 62 | +31,26 | +30,63 |
| 2023 | 70 | 65 | 61 | 60 | -7,35 | -7,39 |
| 2024 | 70 | 63 | 58 | 56 | +14,25 | +14,61 |

Trong 374 ngày đủ phút, 345 khớp và 29 không chạm. Có 1 ngày
first-minute dual-touch (0,27%), xử lý bảo thủ. M1 đầy đủ trong tập rời
rạc đạt +49,90R, DD đóng 22,96R, win rate 45,22%. Trên 339 ngày ghép,
hai nguồn cùng chiều 337/339. Tổng R **+60,50 → +54,51**, DD đóng
**20,91 → 20,90R**, win rate **46,31% → 45,72%**. Hình học lệnh thắng
structural/lucky đổi **81/76 → 82/73**. Đây là nhãn điều kiện từ excursion
trong lịch đóng đã khóa. Phân loại chính thức của winner hard-flat cần
paired continuation. Không annualize mẫu lịch fix.

| Spread pip | Slip entry thêm pip | N | Net R/năm | DD đóng R | Win rate | SL ép nội H1 entry | 405 winner cũ chuyển lỗ |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0,30 | 0,00 | 1660 | +26,83 | 23,82 | 45,18% | 15 | 0 |
| 0,60 | 0,50 | 1666 | +17,70 | 25,95 | 44,12% | 16 | 18 |
| 0,60 | 1,00 | 1666 | +12,36 | 30,69 | 43,64% | 16 | 26 |
| 0,90 | 0,50 | 1669 | +14,64 | 33,04 | 43,56% | 16 | 24 |
| 0,90 | 1,00 | 1669 | +9,38 | 37,65 | 43,14% | 16 | 31 |

Hộp giữ biên gốc ở spread 0,30 pip. Stress nới Ask ở cửa kích hoạt,
nên số sự kiện có thể đổi. Nếu H1 chạm entry và SL, ép entry rồi SL.
Nếu cả hai entry khả thi, giữ nhánh lỗ hơn. Stress spread gốc trùng
kinh tế từng lệnh trên 1.645 ngày chung với Pass 5. H1 stress có thêm
15 ngày first-touch mơ hồ và tính lỗ ở tất cả các ngày này.
Pass 5 có 45,59% win rate, 6/7 năm dương.

Case 0,90/1,00 giữ **+15,77R cụm A và +49,87R cụm B**, 5/7 năm
dương, chuỗi thua dài nhất 11, 31/405 winner lucky/noise cũ thành lỗ.
Tốc độ tích R giảm 67,8% so với Pass 5. Tiêu chí dương hai cụm theo
protocol đạt. Mức bằng chứng của `SURVIVED_HIRES_CHECK` là stress H1
toàn kỳ kèm đối chiếu M1 rời rạc.

| Năm | Pass 5 số lệnh | Pass 5 net R | H1 0,90/1,00 số lệnh | H1 0,90/1,00 net R | H1 0,90/1,00 DD đóng R |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2018 | 231 | +44,75 | 234 | +26,15 | 15,46 |
| 2019 | 223 | -6,01 | 228 | -32,91 | 37,19 |
| 2020 | 233 | +52,72 | 235 | +22,53 | 14,79 |
| 2021 | 248 | +18,68 | 253 | -6,91 | 21,34 |
| 2022 | 236 | +52,43 | 239 | +40,12 | 7,11 |
| 2023 | 243 | +14,28 | 244 | +3,22 | 26,08 |
| 2024 | 231 | +26,80 | 236 | +13,45 | 14,97 |

## 3. XAUUSD · Hộp trước phiên Âu, một cấu hình

Hộp 03:00–06:00 Europe/Helsinki, tương ứng 01:00–04:00 UTC mùa đông
và 00:00–03:00 UTC mùa hè. Kích hoạt đến trước 10:00 Europe/London.
Một lần phá đầu tiên. +4h/+8h tính từ cuối phút phát hiện. Hard-flat
18:55 Helsinki tương ứng 16:55/15:55 UTC. Dùng Open M1 tại endpoint.
Giữ cùng cohort cho cả ba mốc khi đủ đường phút từ đầu hộp tới endpoint
muộn nhất. Stage-0 đo Breakout và Fade trên cùng giá mid và thời điểm.
Chiều BUY/SELL của Fade ngược chiều breakout.

Trong 1.827 ngày thứ Hai–thứ Sáu có 1.629 ngày đủ đường phút, 198 ngày
thiếu ít nhất một phút, 57 ngày đủ dữ liệu nhưng không phá hộp và 1.572
sự kiện chung. Trong 198 ngày thiếu có các ngày lịch thị trường đóng.
Có 1 ngày chạm hai cạnh trong cửa kích hoạt và 0 ngày chạm hai cạnh
ngay phút phá đầu tiên. Năm 2019 có tỷ lệ phủ thấp nhất, 165/261 ngày.

| Năm | Ngày thứ Hai–thứ Sáu | Đủ phút | Thiếu phút | Sự kiện |
| --- | ---: | ---: | ---: | ---: |
| 2018 | 261 | 233 | 28 | 229 |
| 2019 | 261 | 165 | 96 | 159 |
| 2020 | 262 | 237 | 25 | 224 |
| 2021 | 261 | 247 | 14 | 239 |
| 2022 | 260 | 253 | 7 | 245 |
| 2023 | 260 | 242 | 18 | 232 |
| 2024 | 262 | 252 | 10 | 244 |

Mỗi lượt giả định 1 lot 100 oz. Tiền USD trong bảng là tổng của
các lượt, chưa áp lot theo vốn. Gross tính từ mid. Spread 0,35 USD/oz,
slippage 0,20 USD/oz mỗi phía, commission 0,0007% notional mỗi phía.
Net trừ cả ba khoản. Median ma sát 0,7753 USD/oz so với stop tự nhiên
5,937 USD/oz, tức 13,06%. Chỉ 42,30% sự kiện nằm trong trần 12%,
thấp hơn cổng 50%. JSON giữ tên trường `*_pips` kế thừa từ runner
Pass 5. Với Vàng, các trường này có đơn vị USD/oz.

| Mốc | Cụm | Kiểu | N | Gross USD | Phí USD | Net USD | Net BUY | Net SELL |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| +4h | A | Breakout | 612 | +10.235,30 | 47.176,77 | -36.941,47 | -5.496,35 | -31.445,13 |
| +4h | A | Fade | 612 | -10.235,30 | 47.176,77 | -57.412,07 | -16.639,93 | -40.772,15 |
| +4h | B | Breakout | 960 | +19.702,70 | 74.667,94 | -54.965,24 | -23.179,02 | -31.786,21 |
| +4h | B | Fade | 960 | -19.702,70 | 74.667,94 | -94.370,64 | -40.990,61 | -53.380,02 |
| +8h | A | Breakout | 612 | +2.526,20 | 47.176,78 | -44.650,58 | -9.184,32 | -35.466,25 |
| +8h | A | Fade | 612 | -2.526,20 | 47.176,78 | -49.702,98 | -12.618,85 | -37.084,12 |
| +8h | B | Breakout | 960 | +51.398,10 | 74.667,89 | -23.269,79 | -10.910,21 | -12.359,58 |
| +8h | B | Fade | 960 | -51.398,10 | 74.667,89 | -126.065,99 | -60.416,98 | -65.649,01 |
| 18:55 EET/EEST | A | Breakout | 612 | +21.144,50 | 47.176,84 | -26.032,34 | +4.493,48 | -30.525,82 |
| 18:55 EET/EEST | A | Fade | 612 | -21.144,50 | 47.176,84 | -68.321,34 | -17.559,22 | -50.762,12 |
| 18:55 EET/EEST | B | Breakout | 960 | +98.666,70 | 74.667,78 | +23.998,92 | +4.649,48 | +19.349,44 |
| 18:55 EET/EEST | B | Fade | 960 | -98.666,70 | 74.667,78 | -173.334,48 | -92.125,56 | -81.208,92 |

### +4h theo năm

| Năm | Kiểu | BUY/SELL (n) | Gross USD | Phí USD | Net USD | Net BUY | Net SELL |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2018 | Breakout | 106/123 | +10.200,30 | 17.582,87 | -7.382,57 | -3.668,58 | -3.713,99 |
| 2018 | Fade | 123/106 | -10.200,30 | 17.582,87 | -27.783,17 | -15.173,99 | -12.609,18 |
| 2019 | Breakout | 71/88 | +3.362,10 | 12.237,69 | -8.875,59 | -406,91 | -8.468,67 |
| 2019 | Fade | 88/71 | -3.362,10 | 12.237,69 | -15.599,79 | -5.078,87 | -10.520,91 |
| 2020 | Breakout | 123/101 | -3.327,10 | 17.356,21 | -20.683,31 | -1.420,85 | -19.262,46 |
| 2020 | Fade | 101/123 | +3.327,10 | 17.356,21 | -14.029,11 | +3.612,94 | -17.642,05 |
| 2021 | Breakout | 129/110 | +2.638,80 | 18.527,28 | -15.888,48 | -7.552,41 | -8.336,07 |
| 2021 | Fade | 110/129 | -2.638,80 | 18.527,28 | -21.166,08 | -8.718,27 | -12.447,81 |
| 2022 | Breakout | 115/130 | -7.559,10 | 18.992,56 | -26.551,66 | -9.510,85 | -17.040,80 |
| 2022 | Fade | 130/115 | +7.559,10 | 18.992,56 | -11.433,46 | -3.115,00 | -8.318,45 |
| 2023 | Breakout | 109/123 | +13.520,50 | 18.031,66 | -4.511,16 | -6.225,53 | +1.714,37 |
| 2023 | Fade | 123/109 | -13.520,50 | 18.031,66 | -31.552,16 | -20.834,63 | -10.717,53 |
| 2024 | Breakout | 139/105 | +11.102,50 | 19.116,45 | -8.013,95 | +109,76 | -8.123,71 |
| 2024 | Fade | 105/139 | -11.102,50 | 19.116,45 | -30.218,95 | -8.322,71 | -21.896,24 |

### +8h theo năm

| Năm | Kiểu | BUY/SELL (n) | Gross USD | Phí USD | Net USD | Net BUY | Net SELL |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2018 | Breakout | 106/123 | +5.149,30 | 17.582,89 | -12.433,59 | -5.040,57 | -7.393,01 |
| 2018 | Fade | 123/106 | -5.149,30 | 17.582,89 | -22.732,19 | -11.495,01 | -11.237,17 |
| 2019 | Breakout | 71/88 | +7.505,70 | 12.237,69 | -4.731,99 | +1.910,37 | -6.642,36 |
| 2019 | Fade | 88/71 | -7.505,70 | 12.237,69 | -19.743,39 | -6.905,16 | -12.838,23 |
| 2020 | Breakout | 123/101 | -10.128,80 | 17.356,20 | -27.485,00 | -6.054,12 | -21.430,88 |
| 2020 | Fade | 101/123 | +10.128,80 | 17.356,20 | -7.227,40 | +5.781,32 | -13.008,72 |
| 2021 | Breakout | 129/110 | +30.799,90 | 18.527,20 | +12.272,70 | +1.122,63 | +11.150,07 |
| 2021 | Fade | 110/129 | -30.799,90 | 18.527,20 | -49.327,10 | -28.204,13 | -21.122,97 |
| 2022 | Breakout | 115/130 | +748,10 | 18.992,50 | -18.244,40 | -9.137,76 | -9.106,65 |
| 2022 | Fade | 130/115 | -748,10 | 18.992,50 | -19.740,60 | -11.049,05 | -8.691,56 |
| 2023 | Breakout | 109/123 | -7.084,90 | 18.031,71 | -25.116,61 | -13.190,48 | -11.926,13 |
| 2023 | Fade | 123/109 | +7.084,90 | 18.031,71 | -10.946,81 | -7.194,33 | -3.752,48 |
| 2024 | Breakout | 139/105 | +26.935,00 | 19.116,48 | +7.818,52 | +10.295,39 | -2.476,87 |
| 2024 | Fade | 105/139 | -26.935,00 | 19.116,48 | -46.051,48 | -13.969,47 | -32.082,01 |

### 18:55 EET/EEST theo năm

| Năm | Kiểu | BUY/SELL (n) | Gross USD | Phí USD | Net USD | Net BUY | Net SELL |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2018 | Breakout | 106/123 | +18.053,50 | 17.582,88 | +470,62 | +699,69 | -229,06 |
| 2018 | Fade | 123/106 | -18.053,50 | 17.582,88 | -35.636,38 | -18.658,86 | -16.977,51 |
| 2019 | Breakout | 71/88 | -6.198,70 | 12.237,74 | -18.436,44 | -1.084,91 | -17.351,54 |
| 2019 | Fade | 88/71 | +6.198,70 | 12.237,74 | -6.039,04 | +3.803,86 | -9.842,91 |
| 2020 | Breakout | 123/101 | +9.289,70 | 17.356,21 | -8.066,51 | +4.878,70 | -12.945,22 |
| 2020 | Fade | 101/123 | -9.289,70 | 17.356,21 | -26.645,91 | -2.704,22 | -23.941,70 |
| 2021 | Breakout | 129/110 | +57.128,90 | 18.527,18 | +38.601,72 | +12.555,65 | +26.046,07 |
| 2021 | Fade | 110/129 | -57.128,90 | 18.527,18 | -75.656,08 | -43.099,93 | -32.556,15 |
| 2022 | Breakout | 115/130 | -19.076,20 | 18.992,56 | -38.068,76 | -14.851,02 | -23.217,75 |
| 2022 | Fade | 130/115 | +19.076,20 | 18.992,56 | +83,64 | +3.061,85 | -2.978,22 |
| 2023 | Breakout | 109/123 | -4.065,00 | 18.031,64 | -22.096,64 | -16.578,75 | -5.517,89 |
| 2023 | Fade | 123/109 | +4.065,00 | 18.031,64 | -13.966,64 | -13.602,49 | -364,15 |
| 2024 | Breakout | 139/105 | +64.679,00 | 19.116,40 | +45.562,60 | +23.523,60 | +22.039,00 |
| 2024 | Fade | 105/139 | -64.679,00 | 19.116,40 | -83.795,40 | -38.485,00 | -45.310,40 |

| Mốc | Năm Breakout dương | Net toàn kỳ | Net bỏ hai năm tốt nhất | Net bỏ Top 10 ngày toàn kỳ | Net cụm B bỏ Top 10 ngày cụm B |
| --- | ---: | ---: | ---: | ---: | ---: |
| +4h | 0/7 | -91.906,71 | -80.012,98 | -114.721,91 | -75.108,73 |
| +8h | 2/7 | -67.920,36 | -88.011,59 | -109.575,13 | -63.456,20 |
| 18:55 EET/EEST | 3/7 | -2.033,41 | -86.197,74 | -56.768,56 | -26.909,01 |

Breakout thắng Fade trên cả hai cụm ở từng mốc. Net Breakout âm ở cụm A
trên cả ba mốc. Dương ở cụm B chỉ khi đóng 18:55, sau bỏ Top 10 của cụm
thì âm 26.909 USD. Cả ba mốc đều rớt tại cổng đã khóa.
`XAUUSD_REJECTED_AT_STAGE0`. SL-active, DD sau SL, streak, hình học
winner và khả thi 0,01 lot với ngân sách 25–50 USD đều chưa đo.

## 4. Ghép rổ · Tương quan mô tả

USDJPY dùng sổ SL Pass 5. Vàng dùng net +4h chia tiền rủi ro tự nhiên
trên cùng quy ước 100 oz. Ngày theo UTC, tuần ISO. Cột lịch hợp gán 0
cho nhánh vắng sự kiện, kể cả ngày thiếu giá. Cột cùng sự kiện dùng
giao hai sổ, kiểm độ nhạy với cách gán 0.

| Mẫu | Số quan sát | Pearson |
| --- | ---: | ---: |
| Ngày, lịch hợp | 1777 | +0,0447 |
| Ngày JPY âm, lịch hợp | 895 | -0,0251 |
| Tuần, lịch hợp | 366 | +0,0835 |
| Tuần JPY âm, lịch hợp | 160 | +0,0590 |
| Ngày, cùng có sự kiện | 1440 | +0,0490 |
| Ngày JPY âm, cùng có sự kiện | 773 | -0,0284 |

`NOT_RUN_GATE_FAILED`. Double-SL, Equal-Risk, Inverse-DD, mức nén DD
và margin khi hai lệnh mở cùng lúc chưa có kết quả. Tương quan trên
markout Vàng thiếu SL không xác minh khả năng bảo vệ vốn. DD đã nêu là
peak-to-trough của R tại thời điểm đóng lệnh. Vạch 5% ngày và 10% tĩnh
của FTMO 2-Step dùng equity tài khoản và chưa được replay ở đây.
[Giới hạn FTMO 2-Step](https://ftmo.com/en/comparison-table/) ·
[Cách tính Maximum Daily Loss](https://academy.ftmo.com/lesson/maximum-daily-loss/)

## 5. Đối soát và Pass 7

40 tests đạt, 0 skip. Hai lần chạy cho checksum trùng cả bốn tệp.
Đối soát lại 1.645 lệnh baseline, 339 cặp M1/H1, sổ R và DD, cùng
phép cộng độc lập gross/phí/net từng năm và từng chiều cho Vàng.
Tệp tổng hợp và SHA256 nằm cạnh báo cáo. Sổ chi tiết và manifest ở
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/pass6-breakout-execution-20261120`.
Giá holdout đọc 0 tệp, OrderSend 0. Lượt này chạy offline.

**Pass 7 ưu tiên xác minh nguồn USDJPY Bid/Ask liên tục trước 2025.**
Giữ nguyên recipe Pass 5 và ghép cùng ngày để phân rã sai số do feed,
spread và trình tự khớp. Tick có thể phân xử trường hợp hai bên chạm
trong một phút. Chỉ xét sizing và equity prop sau khi kiểm đủ độ phủ,
khả năng khớp entry/SL và sức chịu phí trên cả hai cụm.

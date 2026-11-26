# Pass 5 · USDJPY Tokyo box Stage-0

**ADVANCE_SL_ACTIVE theo cổng đã đăng ký.** +4h và +8h qua cổng.
18:00 EET/EEST dương cả hai cụm nhưng âm khi bỏ hai năm tốt nhất.
Đã chạy đúng một lát SL cạnh đối diện hộp. Kết quả là +29,09R/năm
với DD lệnh đóng 23,82R. Tiếp tục ở mức nghiên cứu. Prop fit chưa đo.

## 1. Delta với nghiên cứu Tokyo cũ

1. **R084** mua USDJPY 09:26–09:54 JST trên các ngày thanh toán danh
   nghĩa. Gross dương nhưng stress âm 2019 và 2022, lần lượt −125,18
   và −142,93 USD trên 100k/lượt. [R084](USDJPY-TOKYO-COMPONENT-RESULTS-20261109.md)
2. **R085** bán 09:56–10:24 JST sau fix trên lịch tương tự. Chỉ 6/13
   năm mở rộng dương sau stress, hai block âm, nên gác exact recipe.
   [R085](USDJPY-POSTFIX-EXTENSION-RESULTS-20261109.md)
3. **Pass 5** không dùng lịch thanh toán hay bias cố định. Đặt hai
   cạnh sau khi hộp Tokyo đóng, ghi cú phá đầu tiên trong cửa
   03:00–10:00 UTC, đo +4h, +8h và hard flat, với Fade tại cùng sự kiện.
   Đây là cơ chế breakout theo giá giữa nến. Các nghiên cứu cũ
   khớp theo giờ M1 open cố định. [Protocol](PASS5-USDJPY-TOKYO-BOX-PROTOCOL-20261120.md)

## 2. Nguồn và phạm vi

Nguồn đủ liên tục đã xác minh là **43.553 H1 USDJPY Bid native** và
**1.817 D1** để tính ATR, lấy đúng hai file Development đã seal.
Tìm thấy M1 Bid/Ask ngày rời rạc từ R084/R085 và fixture upstream.
Chưa có chuỗi M1/M5/M15 liên tục đủ 2018–2024 trong kho đã tra.
H1 first-touch là xấp xỉ. Ask dùng spread cố định 0,30 pip từ
snapshot London 36f1535, không có spread lịch sử ở thời điểm khớp.
Phí thêm 5 USD/lot khứ hồi và slippage 0,20 pip mỗi phía.
Swap 0, toàn bộ exit cùng ngày và trước rollover New York.

FTMO H1 dùng đồng hồ server dịch theo **DST Mỹ**, đã đổi về UTC.
Hộp 09:00–12:00 JST là 00:00–03:00 UTC quanh năm.
Hard flat 18:00 EET/EEST dịch theo **DST châu Âu**, ra 16:00 hoặc
15:00 UTC. Không đồng nhất giờ FTMO, London, New York và Headway.
[FTMO về tuần lệch DST](https://ftmo.com/en/blog/trading-updates/trading-update-7-mar-2024/)

Từ **1.827 ngày trong tuần**, có 1.813 ngày đủ hộp và cửa kích hoạt.
**77/1.813 (4,25%)** có ít nhất một H1 chạm hai cạnh trong cửa kích hoạt.
**15/1.813 (0,83%)** chạm hai cạnh ngay ở H1 first touch và bị loại.
Có 152 ngày không chạm, 14 thiếu hộp/cửa kích hoạt và 1 thiếu giá
trên đường markout. Còn **1.645 sự kiện** chung cho mọi phép đo, gồm
864 BUY và 781 SELL. Cadence 235/năm, khoảng 223–248/năm.
Timestamp entry dùng cuối H1 chạm và fill mô hình ở stop hoặc opening
quote nếu gap. Markout +h vì vậy có độ lệch tới một giờ so với fill thật.
D1 ATR chỉ dùng nến đã đóng. Dải width/ATR có 454 / 928 / 251 sự kiện
và 12 chưa đủ warmup. Median tỷ lệ stress friction / natural stop
là **4,75%**, 96,6% nằm trong 12%. Không lọc bằng biến này.

| Năm | Ngày trong tuần | Hộp và cửa đủ | Có H1 dual-touch | First touch mơ hồ | Có giá đủ ba mốc |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2018 | 261 | 258 | 6 | 2 | 231 |
| 2019 | 261 | 257 | 13 | 2 | 223 |
| 2020 | 262 | 260 | 6 | 0 | 233 |
| 2021 | 261 | 260 | 18 | 4 | 248 |
| 2022 | 260 | 259 | 8 | 1 | 236 |
| 2023 | 260 | 259 | 15 | 1 | 243 |
| 2024 | 262 | 260 | 11 | 5 | 231 |

## 3. Breakout và Fade

Đơn vị USD cộng gộp theo **100k notional mỗi lượt**, chưa sizing. Gross
từ mid, phí là spread + commission + slippage, net = gross − phí.
Fade dùng giá tham chiếu của cùng sự kiện nhưng đổi phía Bid/Ask để khớp,
nên trả đủ phí. BUY/SELL là chiều thực thi của mỗi mô hình.

| Mốc | Cụm | Lượt mỗi mô hình | Kiểu | Gross | Phí stress | Net | Net BUY | Net SELL |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| +4h | A | 687 | Breakout | 9.619,42 | 7.861,30 | 1.758,11 | 1.207,03 | 551,08 |
| +4h | A | 687 | Fade | -9.619,42 | 7.861,30 | -17.480,72 | -8.549,97 | -8.930,75 |
| +4h | B | 958 | Breakout | 24.349,09 | 9.917,36 | 14.431,73 | 10.139,48 | 4.292,25 |
| +4h | B | 958 | Fade | -24.349,09 | 9.917,36 | -34.266,44 | -13.245,13 | -21.021,31 |
| +8h | A | 687 | Breakout | 12.764,61 | 7.860,53 | 4.904,09 | 8.679,47 | -3.775,38 |
| +8h | A | 687 | Fade | -12.764,61 | 7.860,53 | -20.625,14 | -4.222,93 | -16.402,21 |
| +8h | B | 958 | Breakout | 30.951,02 | 9.916,44 | 21.034,58 | 22.652,04 | -1.617,46 |
| +8h | B | 958 | Fade | -30.951,02 | 9.916,44 | -40.867,46 | -7.334,85 | -33.532,62 |
| 18:00 EET/EEST | A | 687 | Breakout | 16.596,57 | 7.860,89 | 8.735,68 | 7.756,98 | 978,70 |
| 18:00 EET/EEST | A | 687 | Fade | -16.596,57 | 7.860,89 | -24.457,45 | -8.977,62 | -15.479,84 |
| 18:00 EET/EEST | B | 958 | Breakout | 24.715,17 | 9.916,93 | 14.798,24 | 14.066,92 | 731,32 |
| 18:00 EET/EEST | B | 958 | Fade | -24.715,17 | 9.916,93 | -34.632,10 | -9.683,80 | -24.948,31 |

| Mốc | Năm dương Breakout / Fade | Phí / gross Breakout | Top 10 / pool net dương Breakout | Net bỏ hai năm tốt nhất | Qua cổng |
| --- | ---: | ---: | ---: | ---: | --- |
| +4h | 5/7 · 0/7 | 52,34% | 10,09% | 1.409,26 | Đạt |
| +8h | 5/7 · 1/7 | 40,67% | 8,38% | 1.779,01 | Đạt |
| 18:00 EET/EEST | 4/7 · 1/7 | 43,03% | 8,56% | -3.470,36 | Rớt |

+4h có BUY và SELL dương trong cả hai cụm. Ở +8h, SELL âm cả hai
cụm, phần dương đến từ BUY. Cụm A mỏng hơn rõ. Bỏ 10 ngày có
net dương lớn nhất **trong riêng cụm A** thì +4h còn −3.532,77 USD và
+8h còn −4.956,82 USD. Đây là kiểm tra tập trung và giới hạn của kết quả.
Tiêu chí cổng đã khóa dùng hai **năm** tốt nhất và vẫn đạt cho +4h/+8h.
Chưa có kết luận về độ bền ngoài Development.

### Theo từng năm và chiều khớp

Bảng dưới ghi gross / phí / net. JSON chứa cả breakdown từng chiều,
tỷ lệ chi phí/gross, Top 10 và từng dải width/ATR.

#### +4h

| Năm | Lượt | Breakout gross / phí / net | Fade gross / phí / net | Breakout BUY / SELL net | Fade BUY / SELL net |
| --- | ---: | --- | --- | --- | --- |
| 2018 | 231 | 5.313,92 / 2.619,97 / 2.693,95 | -5.313,92 / 2.619,97 / -7.933,89 | 821,10 / 1.872,85 | -4.235,03 / -3.698,86 |
| 2019 | 223 | -1.549,41 / 2.547,41 / -4.096,82 | 1.549,41 / 2.547,41 / -998,00 | -872,03 / -3.224,79 | 597,00 / -1.595,00 |
| 2020 | 233 | 5.854,91 / 2.693,92 / 3.160,99 | -5.854,91 / 2.693,92 / -8.548,83 | 1.257,96 / 1.903,02 | -4.911,94 / -3.636,89 |
| 2021 | 248 | 2.970,75 / 2.820,14 / 150,61 | -2.970,75 / 2.820,14 / -5.790,89 | 697,34 / -546,73 | -1.996,78 / -3.794,11 |
| 2022 | 236 | 12.012,86 / 2.444,10 / 9.568,76 | -12.012,86 / 2.444,10 / -14.456,96 | 3.170,81 / 6.397,96 | -8.553,40 / -5.903,56 |
| 2023 | 243 | 1.927,96 / 2.427,42 / -499,46 | -1.927,96 / 2.427,42 / -4.355,39 | 4.236,70 / -4.736,16 | 2.353,21 / -6.708,60 |
| 2024 | 231 | 7.437,51 / 2.225,70 / 5.211,81 | -7.437,51 / 2.225,70 / -9.663,21 | 2.034,63 / 3.177,18 | -5.048,17 / -4.615,04 |

#### +8h

| Năm | Lượt | Breakout gross / phí / net | Fade gross / phí / net | Breakout BUY / SELL net | Fade BUY / SELL net |
| --- | ---: | --- | --- | --- | --- |
| 2018 | 231 | 7.477,45 / 2.619,67 / 4.857,78 | -7.477,45 / 2.619,67 / -10.097,13 | 4.194,07 / 663,71 | -3.025,73 / -7.071,40 |
| 2019 | 223 | -5.188,87 / 2.547,30 / -7.736,17 | 5.188,87 / 2.547,30 / 2.641,58 | -1.808,80 / -5.927,37 | 3.299,93 / -658,35 |
| 2020 | 233 | 10.476,03 / 2.693,56 / 7.782,47 | -10.476,03 / 2.693,56 / -13.169,59 | 6.294,20 / 1.488,28 | -4.497,13 / -8.672,46 |
| 2021 | 248 | 1.443,77 / 2.820,17 / -1.376,40 | -1.443,77 / 2.820,17 / -4.263,95 | -360,26 / -1.016,14 | -1.527,31 / -2.736,64 |
| 2022 | 236 | 18.820,79 / 2.443,61 / 16.377,18 | -18.820,79 / 2.443,61 / -21.264,40 | 11.354,47 / 5.022,71 | -7.178,04 / -14.086,36 |
| 2023 | 243 | 3.292,11 / 2.427,30 / 864,81 | -3.292,11 / 2.427,30 / -5.719,41 | 6.100,88 / -5.236,07 | 2.853,18 / -8.572,59 |
| 2024 | 231 | 7.394,35 / 2.225,36 / 5.168,99 | -7.394,35 / 2.225,36 / -9.619,71 | 5.556,96 / -387,96 | -1.482,68 / -8.137,03 |

#### 18:00 EET/EEST

| Năm | Lượt | Breakout gross / phí / net | Fade gross / phí / net | Breakout BUY / SELL net | Fade BUY / SELL net |
| --- | ---: | --- | --- | --- | --- |
| 2018 | 231 | 12.453,80 / 2.620,08 / 9.833,73 | -12.453,80 / 2.620,08 / -15.073,88 | 3.460,16 / 6.373,56 | -8.736,31 / -6.337,58 |
| 2019 | 223 | -7.454,57 / 2.547,27 / -10.001,84 | 7.454,57 / 2.547,27 / 4.907,30 | -2.746,34 / -7.255,49 | 4.628,22 / 279,07 |
| 2020 | 233 | 11.597,33 / 2.693,54 / 8.903,79 | -11.597,33 / 2.693,54 / -14.290,87 | 7.043,17 / 1.860,63 | -4.869,53 / -9.421,33 |
| 2021 | 248 | 1.215,64 / 2.820,17 / -1.604,54 | -1.215,64 / 2.820,17 / -4.035,81 | -463,84 / -1.140,69 | -1.402,74 / -2.633,06 |
| 2022 | 236 | 19.614,52 / 2.443,97 / 17.170,55 | -19.614,52 / 2.443,97 / -22.058,48 | 8.038,00 / 9.132,55 | -11.288,28 / -10.770,21 |
| 2023 | 243 | -1.546,04 / 2.427,32 / -3.973,36 | 1.546,04 / 2.427,32 / -881,28 | 3.258,26 / -7.231,63 | 4.848,99 / -5.730,27 |
| 2024 | 231 | 5.431,06 / 2.225,47 / 3.205,58 | -5.431,06 / 2.225,47 / -7.656,53 | 3.234,50 / -28,91 | -1.841,76 / -5.814,77 |

## 4. Một lát SL-active đã đăng ký

Giữ nguyên entry và tập sự kiện. SL ở cạnh đối diện hộp, không TP,
hard flat 18:00 EET/EEST. Khi open của H1 vượt stop, dùng side quote
opening và thêm stress. R định nghĩa theo khoảng cách giá vào tới
stop cấu trúc với quy đổi tại entry. Phí đi vào tử số. DD đo trên
đường R đã đóng. Số 26,50R ở Pass 4 dùng SL hiển thị của EA trên
một kỳ khác, nên so 23,82R với 26,50R chỉ để định hướng.

| Phạm vi | Lệnh | Net R | Net R/năm | Max DD R đã đóng | Chuỗi thua dài nhất |
| --- | ---: | ---: | ---: | ---: | ---: |
| Cụm A | 687 | 91,47 | 30,49 | 15,51 | 8 |
| Cụm B | 958 | 112,20 | 28,05 | 23,82 | 10 |
| Toàn kỳ | 1645 | 203,66 | 29,09 | 23,82 | 10 |
| 2018 | 231 | 44,75 | 44,75 | 10,54 | 8 |
| 2019 | 223 | -6,01 | -6,01 | 15,51 | 8 |
| 2020 | 233 | 52,72 | 52,72 | 9,72 | 7 |
| 2021 | 248 | 18,68 | 18,68 | 12,44 | 10 |
| 2022 | 236 | 52,43 | 52,43 | 6,68 | 6 |
| 2023 | 243 | 14,28 | 14,28 | 23,82 | 7 |
| 2024 | 231 | 26,80 | 26,80 | 14,75 | 9 |

**642 SL, 1.003 hard flat**. Sáu trên bảy năm net R dương. Có 750 lệnh
thắng, đều đóng theo lịch. Selective Win Diagnosis giữ **750 unknown**
do chưa có exit tiếp diễn ghép cùng entry/SL sau cutoff. Trên cùng path
H1 nếu chỉ xét hình học, 345 lệnh qua ngưỡng structural và 405 vào
nhóm lucky/noise. Đây là nhãn mô tả ngưỡng, chưa xác nhận nguyên nhân
hay lệnh nào may mắn. Không tính cực trị H1 chạm đầu tiên vào MAE/MFE
vì chưa biết thứ tự trước/sau fill. Nhãn cutoff chính thức giữ unknown.

## 5. Phán quyết

**Đề xuất Pass 6 nghiên cứu XAUUSD riêng để kiểm khả năng ghép rổ.**
USDJPY giữ cấu hình đã đăng ký và vẫn cần kiểm lại ordering, spread
và fill bằng M1 Bid/Ask hoặc tick trước khi nối sizing hay replay quỹ.
Kết quả này đo tiếp diễn trên dữ liệu Development đã có exposure.
Daily Loss, Overall Loss và margin cho Swing/Standard chưa được đo.
Không suy ra chiến lược của EA nguồn hay khả năng vượt Challenge.

## Kiểm chứng và lưu

Protocol đã commit tại `f2f02e8` trước khi đọc giá.
Stage‑0 ở lần chạy đầu trùng kết quả với lần chạy bổ sung SL.
Đã đối soát 1.645 cặp Breakout/Fade theo từng event, gross dấu ngược,
phí đối xứng và tổng theo năm. 26 test PASS, 0 skip.
Giữ nguyên holdout từ 2025, pin Trader và WIP VI Dubber.
OrderSend = 0, không mở MT5, không trao đổi dữ liệu ngoài kho.

[JSON đối soát](PASS5-USDJPY-TOKYO-BOX-STAGE0-20261120.json) · [SHA256](PASS5-USDJPY-TOKYO-BOX-STAGE0-20261120.sha256).
`research_inventory.py --key pass5-usdjpy-tokyo-box-20261120` tra manifest chứa output riêng.

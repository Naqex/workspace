# Pass 7B · USDJPY QDM Bid/Ask và FTMO floating equity

**ENGINE_1_NEEDS_PARTNER**. Stress_05 còn dương ở hai cụm trên tập ngày đủ đường giá. Tốc độ thấp và DD khiến các sổ đã thử chưa đạt cổng đi tiếp một mình.

Protocol khóa trước giá tại `f2bbf3b`. [Protocol](PASS7B-USDJPY-FULL-M1-FLOATING-EQUITY-PROTOCOL-20261120.md).
Development 2018–2024 đã có exposure. Cụm A 2018–2020, B 2021–2024.
Scope 80% Swing 10k/25k và 20% Standard 50k là ưu tiên nghiên cứu.

## 1. QDM và khóa giá từ 2025

QDM CLI 125.2692 liệt kê `update` và `export`. Owner cho phép update
vào symbol thô `USDJPY_PASS7B_QUARANTINE`. QDM giữ symbol đó riêng
trong cache của chính QDM. Các script nghiên cứu chỉ dùng bảy CSV
export theo năm và không mở file cache thô.
Lần update gặp HTTP 429 ở đuôi cache sau mốc holdout. Sau khi QDM
nhả cache, chạy lại riêng export 2018–2024. Mỗi năm qua kiểm clock
và SHA256 trước khi ghi Parquet/Zstd.
Tất cả tick Development có timestamp trước 01/01/2025 và 0 giá
từ 2025 vào phân tích. Holdout native vẫn khóa.
[StrategyQuant về giới hạn update](https://strategyquant.com/forum/topic/qdmcli-exe-update-resume-ohne-uberschreiben/).

| Năm | Tick QDM | M1 có giá | Ngày trong tuần có quote | Ngày đủ đường tới flat | Ngày H1 active thiếu phút | Lệnh |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2018 | 19.581.512 | 372.794 | 261 | 210 | 49 | 194 |
| 2019 | 20.851.844 | 372.700 | 261 | 163 | 95 | 145 |
| 2020 | 24.321.113 | 373.333 | 262 | 159 | 101 | 143 |
| 2021 | 14.822.017 | 370.563 | 260 | 106 | 154 | 104 |
| 2022 | 39.593.910 | 372.717 | 260 | 236 | 23 | 216 |
| 2023 | 43.463.937 | 371.964 | 260 | 231 | 28 | 218 |
| 2024 | 40.969.081 | 373.383 | 262 | 229 | 31 | 208 |

Cụm A có 784 ngày có quote và 532 ngày đủ đường. Trên 775 ngày có cửa H1, 530 ngày đủ M1 (68,39%).

Cụm B có 1042 ngày có quote và 802 ngày đủ đường. Trên 1038 ngày có cửa H1, 802 ngày đủ M1 (77,26%).

Đủ đường ít nhất một ngày trong **84/84 tháng**. Có 481 ngày H1 active thiếu phút, trong đó 0 ngày thiếu cả đường giá.
Đã loại nguyên ngày thiếu phút trước khi xét entry. File gaps lưu ngày và
độ dài khe trống. Giữ giờ thị trường đóng ở ngoài mẫu số coverage H1.
Có 221 ngày chỉ thiếu một phút. Khe liền dài hơn 15 phút xuất hiện ở 1 ngày. Khe lớn nhất là 54 phút ngày 2023-09-25.
2021 chỉ có 106/260 ngày H1 với đường M1 đủ phút. Đây là giới hạn
quan trọng khi suy rộng kết quả. Dữ liệu phủ 84 tháng nhưng còn thiếu
26,5% số ngày cửa H1. Không suy đoán kết quả giá ở các ngày bị loại.

| Spread theo tick | Quan sát | Median pip | P95 pip |
| --- | ---: | ---: | ---: |
| Tokyo | 27.043.065 | 0,60 | 1,20 |
| London | 38.058.414 | 0,50 | 1,00 |

Tokyo 00:00–03:00 UTC. London 08:00–12:00 giờ London. Mốc FTMO-Demo
36f1535 cho USDJPY là median 0,30 pip ở snapshot London. Đây là
đối chiếu giữa hai nguồn và hai cách lấy mẫu.

## 2. Đối soát nguồn và kết quả M1

Kiểm **339 ngày Pass 6**, 313.541/313.599 phút cùng timestamp. Có 313.533 phút khớp đủ 8 giá OHLC,
313.538 phút khớp cả hai giá open và 313.537 phút khớp cả hai giá close.
Số quote QDM đảo Bid/Ask là 0. Sai lệch open Bid trung bình theo lệch giờ, tính bằng pip:

| Dịch timestamp QDM | Số phút so sánh | Mean absolute error pip |
| --- | ---: | ---: |
| -1 giờ | 293.201 | 11,0909 |
| +0 giờ | 313.541 | 0,0000 |
| +1 giờ | 313.540 | 11,2549 |

Có 337 lệnh cùng ngày, 337 cùng chiều và 337 cùng phút entry.
Trên giao lệnh đó, Pass 6 +50,39R và QDM +50,39R. Sai khác vendor export và
cách cắt tick có thể làm khác OHLC. Tập Pass 6 chỉ là oracle đối soát.
Trên 1211 lệnh cùng ngày H1/M1, H1 Pass 5 +122,49R và QDM M1 Base +117,77R. Cùng chiều 1204 ngày.
434 lệnh H1 ở ngày thiếu đường M1 đóng góp +81,17R trong mô hình H1. Mức giảm R/năm toàn kỳ phản ánh cả độ phủ và thực thi. Đây là số R
chia theo số năm lịch, không ngoại suy lãi của các ngày thiếu path.

| Profile | Lệnh | R/năm A | R/năm B | R/năm toàn kỳ | Năm dương | DD nổi R | Phút entry mơ hồ | Streak thua |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| H1 Pass 5 | 1645 | +30,49 | +28,05 | +29,09 | 6/7 | Chưa đo | Chưa đo | 10 |
| M1_Real_Base | 1228 | +10,94 | +17,73 | +14,82 | 5/7 | 23,38 | 1 | 9 |
| M1_Real_Stress_05 | 1228 | +7,40 | +15,00 | +11,74 | 5/7 | 24,32 | 1 | 9 |
| M1_Real_Stress_10 | 1228 | +3,86 | +12,27 | +8,67 | 5/7 | 26,04 | 1 | 9 |

| Profile | BUY lệnh / R | SELL lệnh / R | Top 10 / tổng thắng | Bỏ Top 10 R | Dual-entry | Entry và SL cùng phút | Structural / Lucky |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| M1_Real_Base | 636 / +74,51 | 592 / +29,22 | 10,39% | +33,98 | 1 | 1 | 248 / 318 |
| M1_Real_Stress_05 | 636 / +63,26 | 592 / +18,93 | 10,50% | +12,65 | 1 | 1 | 240 / 319 |
| M1_Real_Stress_10 | 636 / +52,01 | 592 / +8,65 | 10,62% | -8,69 | 1 | 1 | 231 / 322 |

Hai cột mơ hồ có thể cùng xảy ra. Phút entry mơ hồ là hợp hai loại.
Nhãn Structural/Lucky mô tả hình học; nhiều winner hard-flat vẫn cần
bằng chứng cùng lệnh sau cutoff cho taxonomy đầy đủ.
H1 Pass 5 chỉ có DD lệnh đóng 23,82R.
1R giữ khoảng stop structural gốc ở cả ba profile. Sizing dùng stop
cash có cộng phí. Spread nằm trong Bid/Ask, phí 5 USD khứ hồi mỗi lot,
slip hai phía 0,20 pip và stress thêm 0/0,50/1,00 pip ở entry. Swap 0.

| Năm | H1 Pass 5 R | M1 Base R | M1 Stress_05 R | M1 Stress_10 R |
| --- | ---: | ---: | ---: | ---: |
| 2018 | +44,75 | +24,20 | +20,22 | +16,24 |
| 2019 | -6,01 | -12,30 | -15,76 | -19,22 |
| 2020 | +52,72 | +20,91 | +17,73 | +14,55 |
| 2021 | +18,68 | -3,22 | -5,77 | -8,31 |
| 2022 | +52,43 | +43,49 | +40,84 | +38,18 |
| 2023 | +14,28 | +7,54 | +4,58 | +1,63 |
| 2024 | +26,80 | +23,12 | +20,35 | +17,58 |

## 3. FTMO floating equity và lot

Tính lỗ ngày theo balance ở nửa đêm Europe/Prague và equity có phí.
Tính lỗ tĩnh từ vốn đầu. Peak-to-trough trong bảng dùng % vốn đầu.
DD dùng envelope high-then-low M1. Khi nến thiếu ordering, số liệu
là mô phỏng bảo thủ trong phạm vi giá được nhận. Không có lệnh qua
mốc reset. Sổ được giữ liên tục để đo DD và thời gian dưới đỉnh.
Margin Swing dựa trên 3.333,33 USD/lot xác minh ở 8fd77ef. Standard
dùng 1.000 USD/lot theo 36f1535, áp spec 10k đã đo sang 50k.
[FTMO về daily equity](https://academy.ftmo.com/lesson/maximum-daily-loss/) · [FTMO 2-Step 5% / 10% static](https://ftmo.com/en/ftmo-free-trial/).

### M1_Real_Base

| Sổ | Risk | %/năm A / B / cả kỳ | USD/năm A / B / cả kỳ | Daily % | Peak DD % | Static % | Underwater tháng / ngày GD | Margin đỉnh % | Bỏ min lot / margin |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Swing 10k | 0,20% | +2,01 / +3,06 / +2,61 | +201 / +306 / +261 | 0,20 | 4,19 | 0,46 | 9,36 / 177 | 8,67 | 2 / 0 |
| Swing 10k | 0,25% | +2,47 / +4,00 / +3,34 | +247 / +400 / +334 | 0,25 | 5,27 | 0,52 | 13,93 / 159 | 11,00 | 0 / 0 |
| Swing 10k | 0,30% | +3,01 / +4,93 / +4,11 | +301 / +493 / +411 | 0,30 | 6,35 | 0,60 | 10,43 / 154 | 13,00 | 0 / 0 |
| Swing 10k | 0,40% | +4,04 / +6,60 / +5,50 | +404 / +660 / +550 | 0,40 | 8,76 | 0,82 | 9,44 / 132 | 17,67 | 0 / 0 |
| Swing 25k | 0,20% | +2,04 / +3,35 / +2,79 | +510 / +836 / +696 | 0,20 | 4,43 | 0,39 | 9,44 / 132 | 8,80 | 0 / 0 |
| Swing 25k | 0,25% | +2,61 / +4,14 / +3,48 | +652 / +1.035 / +871 | 0,25 | 5,55 | 0,51 | 9,44 / 132 | 11,07 | 0 / 0 |
| Swing 25k | 0,30% | +3,08 / +5,08 / +4,22 | +769 / +1.271 / +1.056 | 0,30 | 6,59 | 0,62 | 9,44 / 132 | 13,20 | 0 / 0 |
| Swing 25k | 0,40% | +4,15 / +6,72 / +5,62 | +1.038 / +1.680 / +1.405 | 0,40 | 9,03 | 0,80 | 9,44 / 132 | 17,60 | 0 / 0 |
| Standard 50k | 0,20% | +2,08 / +3,36 / +2,81 | +1.038 / +1.680 / +1.405 | 0,20 | 4,51 | 0,40 | 9,44 / 132 | 2,64 | 0 / 0 |
| Standard 50k | 0,25% | +2,59 / +4,23 / +3,53 | +1.295 / +2.117 / +1.765 | 0,25 | 5,60 | 0,51 | 9,44 / 132 | 3,32 | 0 / 0 |
| Standard 50k | 0,30% | +3,13 / +5,12 / +4,26 | +1.563 / +2.559 / +2.132 | 0,30 | 6,73 | 0,60 | 9,44 / 132 | 3,98 | 0 / 0 |
| Standard 50k | 0,40% | +4,17 / +6,79 / +5,67 | +2.084 / +3.396 / +2.833 | 0,40 | 9,04 | 0,81 | 9,44 / 132 | 5,30 | 0 / 0 |

### M1_Real_Stress_05

| Sổ | Risk | %/năm A / B / cả kỳ | USD/năm A / B / cả kỳ | Daily % | Peak DD % | Static % | Underwater tháng / ngày GD | Margin đỉnh % | Bỏ min lot / margin |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Swing 10k | 0,20% | +1,37 / +2,69 / +2,12 | +137 / +269 / +212 | 0,20 | 4,17 | 0,48 | 21,10 / 222 | 8,33 | 2 / 0 |
| Swing 10k | 0,25% | +1,65 / +3,47 / +2,69 | +165 / +347 / +269 | 0,25 | 5,42 | 0,53 | 21,40 / 229 | 10,33 | 0 / 0 |
| Swing 10k | 0,30% | +2,07 / +4,10 / +3,23 | +207 / +410 / +323 | 0,30 | 6,50 | 0,66 | 21,12 / 223 | 12,67 | 0 / 0 |
| Swing 10k | 0,40% | +2,76 / +5,54 / +4,35 | +276 / +554 / +435 | 0,40 | 8,90 | 0,90 | 21,07 / 221 | 16,67 | 0 / 0 |
| Swing 25k | 0,20% | +1,36 / +2,85 / +2,21 | +339 / +712 / +552 | 0,20 | 4,53 | 0,46 | 21,12 / 223 | 8,40 | 0 / 0 |
| Swing 25k | 0,25% | +1,75 / +3,47 / +2,73 | +437 / +868 / +683 | 0,25 | 5,73 | 0,55 | 21,10 / 222 | 10,53 | 0 / 0 |
| Swing 25k | 0,30% | +2,09 / +4,29 / +3,35 | +523 / +1.072 / +836 | 0,30 | 6,80 | 0,69 | 21,09 / 222 | 12,67 | 0 / 0 |
| Swing 25k | 0,40% | +2,76 / +5,74 / +4,46 | +690 / +1.435 / +1.116 | 0,40 | 9,21 | 0,93 | 21,09 / 222 | 16,93 | 0 / 0 |
| Standard 50k | 0,20% | +1,38 / +2,87 / +2,23 | +690 / +1.435 / +1.116 | 0,20 | 4,60 | 0,47 | 21,09 / 222 | 2,54 | 0 / 0 |
| Standard 50k | 0,25% | +1,74 / +3,58 / +2,79 | +870 / +1.788 / +1.395 | 0,25 | 5,75 | 0,57 | 21,10 / 222 | 3,18 | 0 / 0 |
| Standard 50k | 0,30% | +2,10 / +4,28 / +3,35 | +1.048 / +2.142 / +1.673 | 0,30 | 6,92 | 0,69 | 21,10 / 222 | 3,82 | 0 / 0 |
| Standard 50k | 0,40% | +2,81 / +5,76 / +4,49 | +1.403 / +2.879 / +2.247 | 0,40 | 9,25 | 0,92 | 21,09 / 222 | 5,08 | 0 / 0 |

### M1_Real_Stress_10

| Sổ | Risk | %/năm A / B / cả kỳ | USD/năm A / B / cả kỳ | Daily % | Peak DD % | Static % | Underwater tháng / ngày GD | Margin đỉnh % | Bỏ min lot / margin |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Swing 10k | 0,20% | +0,73 / +2,23 / +1,59 | +73 / +223 / +159 | 0,20 | 4,45 | 0,65 | 21,99 / 241 | 8,00 | 2 / 0 |
| Swing 10k | 0,25% | +0,78 / +2,92 / +2,01 | +78 / +292 / +201 | 0,25 | 5,69 | 1,23 | 22,40 / 250 | 10,00 | 0 / 0 |
| Swing 10k | 0,30% | +0,94 / +3,38 / +2,33 | +94 / +338 / +233 | 0,30 | 6,79 | 1,47 | 21,99 / 241 | 12,00 | 0 / 0 |
| Swing 10k | 0,40% | +1,50 / +4,44 / +3,18 | +150 / +444 / +318 | 0,40 | 9,27 | 1,35 | 21,99 / 241 | 16,00 | 0 / 0 |
| Swing 25k | 0,20% | +0,69 / +2,41 / +1,67 | +172 / +602 / +418 | 0,20 | 4,59 | 0,80 | 21,99 / 241 | 8,13 | 0 / 0 |
| Swing 25k | 0,25% | +0,95 / +2,90 / +2,06 | +236 / +725 / +515 | 0,25 | 5,84 | 0,89 | 21,98 / 241 | 10,13 | 0 / 0 |
| Swing 25k | 0,30% | +1,11 / +3,48 / +2,46 | +277 / +870 / +616 | 0,30 | 7,12 | 1,08 | 21,98 / 241 | 12,13 | 0 / 0 |
| Swing 25k | 0,40% | +1,44 / +4,70 / +3,30 | +359 / +1.174 / +825 | 0,40 | 9,43 | 1,53 | 21,99 / 241 | 16,27 | 0 / 0 |
| Standard 50k | 0,20% | +0,72 / +2,35 / +1,65 | +359 / +1.174 / +825 | 0,20 | 4,71 | 0,77 | 21,99 / 241 | 2,44 | 0 / 0 |
| Standard 50k | 0,25% | +0,94 / +2,91 / +2,07 | +469 / +1.455 / +1.033 | 0,25 | 5,95 | 0,91 | 21,98 / 241 | 3,04 | 0 / 0 |
| Standard 50k | 0,30% | +1,09 / +3,50 / +2,47 | +547 / +1.751 / +1.235 | 0,30 | 7,15 | 1,14 | 21,98 / 241 | 3,66 | 0 / 0 |
| Standard 50k | 0,40% | +1,49 / +4,67 / +3,30 | +743 / +2.334 / +1.652 | 0,40 | 9,56 | 1,45 | 21,98 / 241 | 4,88 | 0 / 0 |

### Stress_05 trên 10k Swing

| Risk | Lệnh dùng <90% ngân sách do lot | Có làm tròn | Free margin thấp nhất USD |
| --- | ---: | ---: | ---: |
| 0,20% | 319/1226 | 1226/1226 | 9.493,04 |
| 0,25% | 209/1228 | 1228/1228 | 9.350,12 |
| 0,30% | 162/1228 | 1228/1228 | 9.208,49 |
| 0,40% | 60/1228 | 1228/1228 | 8.953,23 |

Bảng có margin đỉnh theo vốn đầu. JSON ghi thêm đỉnh theo equity,
số lệnh không mua được min lot, từng năm, cờ breach và kiểm ngưỡng
2,5% Daily / 7,5% hoặc 8% Peak DD. Đường vốn lưu dưới dạng mark USD
mỗi lot theo phút. Nhân với lot và cộng balance_before trong sổ
account-lots để tái tạo mọi điểm vốn của một sổ. Reset lỗ ngày
ở Prague không tác động tới equity lũy kế. Underwater cuối kỳ được right-censor.

## 4. Phán quyết và giới hạn

Stress_05 còn dương ở hai cụm trên tập ngày đủ đường giá. Tốc độ thấp và DD khiến các sổ đã thử chưa đạt cổng đi tiếp một mình.
Mốc xét chính là Stress_05: dương hai cụm và >=5/7 năm, daily <=3%,
peak DD <=8%, lợi nhuận >=8%/năm, cùng hai vạch cứng FTMO.
Không sổ nào chạm 5% Daily hoặc 10% Static trên đường giá được nhận.
Giới hạn peak DD 8% là cổng nội bộ. Với Stress_05 và risk 0,30%,
cả ba sổ có DD dưới 8% và tốc độ chỉ 3,23–3,35%/năm. Tại risk 0,40%,
cả ba sổ vượt 8% peak DD và tốc độ chỉ 4,35–4,49%/năm.
Pass 7B chưa mô phỏng các vòng Challenge, thời gian tới payout, news
trading, OOS hay tài khoản thật. Feed Dukascopy với phí FTMO là
mô hình nghiên cứu. Hộp dùng proxy mid từ extrema hai side để giữ
quy ước trước, đồng thời lưu mid đo từ tick để đối soát.

36 tests đạt, 0 skip. Đối soát timestamp, SHA, 36 sổ, gross/phí/net,
curve và balance giữa các lệnh. OrderSend 0, không MT5.
Các output private thuộc `pass7b-usdjpy-qdm-equity-20261120`.

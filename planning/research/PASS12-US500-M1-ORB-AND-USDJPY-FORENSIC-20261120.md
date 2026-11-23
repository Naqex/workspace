# Pass 12 · US500 NY ORB M1 và pháp y USDJPY

**US500: US500_M1_DATA_UNAVAILABLE. USDJPY: USDJPY_COST_HYGIENE_NOT_RETAINED.**
[Protocol trước outcome](PASS12-US500-M1-ORB-AND-USDJPY-FORENSIC-PROTOCOL-20261120.md) tại fdef13d.
Development 2018–2024 đã có exposure. A 2018–2020, B 2021–2024.

## 1. US500 · kiểm trực tiếp M1 Bid/Ask

QDM CLI 125.2692 cho mã cách ly USA500IDXUSD_PASS12_QUARANTINE bị chặn tốc độ HTTP 429 liên tục trên cdn.strategyquantcdn.com ở cả ba lượt thử (20/11 lượt 1: 429 tại 2011.09.25–26; 20/11 lượt 2: 12 lỗi 429 đến 2011.10.19; 23/11 lượt khôi phục: 3 lỗi 429 tại 2011.09.19–21, chỉ ghi được 2 ngày năm 2011 sau 10 phút). Vì action=update của QDM 125.2692 tải từ 2011 và bỏ qua datefrom, kho QDM vẫn còn 0 bản ghi cho giai đoạn Development 2018–2024 (không đọc cache thô, 0 bản ghi holdout >= 01/01/2025). Ghi chú cho Pass sau: ổ E hiện đã có kho Dukascopy M1 Bid/Ask đã niêm phong từ kênh cũ (us500-long-explicit-source-v1, 2013–2024) nhưng nằm ngoài phạm vi QDM đã khóa ở Protocol fdef13d nên không tự thay thế.

Coverage 2018–2024, spread và hiệu suất đều N/A.
Track 1 chưa có Stage-0, lát SL hay danh mục. Phán quyết hiện tại
là thiếu đầu vào và chưa có kết luận kinh tế về US500 NY ORB.
[Giới hạn update QDM](https://strategyquant.com/forum/topic/qdmcli-exe-update-resume-ohne-uberschreiben/).

## 2. USDJPY · pháp y trước khi vào lệnh

Tái lập đủ **1.228 lệnh/1.334 ngày** mẫu chặt và **1.437 lệnh/1.564 ngày**
mẫu mở rộng. Stress 0,50 pip cộng ở entry, phí gốc 5 USD/lot
và 0,20 pip/side. Cost/hộp dùng spread đầu phút trigger,
commission quy đổi theo midpoint cùng phút và slippage mô hình.
Đây là điều kiện thử để bỏ lần first-touch đã ghi trên tape. Để
dùng với pending broker cần xác minh thứ tự cập nhật quote và khớp.
ATR D1 Wilder 14 chỉ dùng nến đã đóng lúc 03:00 UTC. 11 lệnh đầu
thiếu warmup ATR trong Development nên giữ unknown.

### Trước và sau đúng một cổng 12%

| Mẫu | Nhánh | Số lệnh A / B | Net R/năm A / B / cả kỳ |
| --- | --- | ---: | ---: |
| strict | baseline | 482 / 746 | +7,40 / +15,00 / +11,74 |
| strict | cost12 | 437 / 702 | +9,03 / +16,03 / +13,03 |
| extended | baseline | 601 / 836 | +6,50 / +14,24 / +10,92 |
| extended | cost12 | 523 / 765 | +1,47 / +15,55 / +9,51 |

| Mẫu | Sổ | Risk | Nhánh | Net %/năm A / B / cả kỳ | Floating DD % | Dưới đỉnh tháng |
| --- | --- | --- | --- | ---: | ---: | ---: |
| strict | Swing 10k | 0.30% | baseline | +2,07 / +4,10 / +3,23 | 6,50 | 21,12 |
| strict | Swing 10k | 0.30% | cost12 | +2,46 / +4,40 / +3,57 | 6,50 | 22,86 |
| strict | Swing 10k | 0.40% | baseline | +2,76 / +5,54 / +4,35 | 8,90 | 21,07 |
| strict | Swing 10k | 0.40% | cost12 | +3,31 / +5,93 / +4,81 | 8,90 | 22,86 |
| strict | Swing 25k | 0.30% | baseline | +2,09 / +4,29 / +3,35 | 6,80 | 21,09 |
| strict | Swing 25k | 0.30% | cost12 | +2,51 / +4,58 / +3,69 | 6,80 | 22,86 |
| strict | Swing 25k | 0.40% | baseline | +2,76 / +5,74 / +4,46 | 9,21 | 21,09 |
| strict | Swing 25k | 0.40% | cost12 | +3,31 / +6,13 / +4,92 | 9,21 | 22,86 |
| strict | Standard 50k | 0.30% | baseline | +2,10 / +4,28 / +3,35 | 6,92 | 21,10 |
| strict | Standard 50k | 0.30% | cost12 | +2,51 / +4,58 / +3,69 | 6,92 | 22,86 |
| strict | Standard 50k | 0.40% | baseline | +2,81 / +5,76 / +4,49 | 9,25 | 21,09 |
| strict | Standard 50k | 0.40% | cost12 | +3,36 / +6,15 / +4,96 | 9,25 | 22,86 |
| extended | Swing 10k | 0.30% | baseline | +1,67 / +3,88 / +2,93 | 9,08 | 41,16 |
| extended | Swing 10k | 0.30% | cost12 | +0,42 / +4,27 / +2,62 | 9,22 | 41,62 |
| extended | Swing 10k | 0.40% | baseline | +2,23 / +5,23 / +3,95 | 12,15 | 41,12 |
| extended | Swing 10k | 0.40% | cost12 | +0,57 / +5,75 / +3,53 | 12,39 | 41,59 |
| extended | Swing 25k | 0.30% | baseline | +1,69 / +4,05 / +3,04 | 9,27 | 41,12 |
| extended | Swing 25k | 0.30% | cost12 | +0,44 / +4,44 / +2,72 | 9,45 | 41,59 |
| extended | Swing 25k | 0.40% | baseline | +2,22 / +5,42 / +4,05 | 12,40 | 41,13 |
| extended | Swing 25k | 0.40% | cost12 | +0,55 / +5,93 / +3,63 | 12,63 | 41,59 |
| extended | Standard 50k | 0.30% | baseline | +1,69 / +4,04 / +3,03 | 9,34 | 41,13 |
| extended | Standard 50k | 0.30% | cost12 | +0,43 / +4,43 / +2,72 | 9,51 | 41,59 |
| extended | Standard 50k | 0.40% | baseline | +2,26 / +5,43 / +4,07 | 12,52 | 41,13 |
| extended | Standard 50k | 0.40% | cost12 | +0,59 / +5,95 / +3,65 | 12,75 | 41,59 |

Mẫu chặt loại **89 lệnh**, khiến Net R/năm tăng từ **11,74 lên 13,03**.
Nhóm bị loại trong mẫu mở rộng là **149 lệnh**. Bỏ chúng làm Cụm A
giảm từ **6,50 xuống 1,47R/năm**, net toàn kỳ giảm **10,92 xuống 9,51R/năm**.
Trên Swing 10k risk 0,30%, DD mẫu mở rộng tăng **9,08% → 9,22%**.
Nút thắt xuất hiện trên mẫu có coverage cao hơn và cổng 12% không xử lý được.

### Nguồn drawdown và thời gian dưới đỉnh

**9,08–9,34% DD** là mẫu mở rộng tại risk **0,30%** trên ba sổ.
**Khoảng 21 tháng** là mẫu chặt. Mẫu mở rộng có **41,12–41,16 tháng**
dưới đỉnh, tùy sổ và mức risk. Bảng sau dùng Swing 10k 0,40%
để soi lệnh. Timestamp của sổ 0,30% và toàn bộ sổ khác ở JSON.

| Mẫu | Đoạn | Bắt đầu UTC | Đáy/hồi UTC | Lệnh có giao đoạn | Biến động DD hoặc thời gian |
| --- | --- | --- | --- | ---: | ---: |
| strict | peak_dd | 2023-03-01T12:08+00:00 | 2023-06-20T14:33+00:00 | 74 | 889,89 USD |
| strict | underwater | 2020-08-21T08:03+00:00 | 2022-05-24T14:31+00:00 | 210 | 21,07 tháng |
| extended | peak_dd | 2018-12-20T14:53+00:00 | 2020-01-30T14:36+00:00 | 211 | 1.214,97 USD |
| extended | underwater | 2018-12-20T14:53+00:00 | 2022-05-25T07:18+00:00 | 637 | 41,12 tháng |

Bốn trục dùng chung lệnh và mỗi trục có mẫu số riêng. R lỗ là tổng
độ lớn của các lệnh net âm, trước khi bù bằng lệnh thắng. Lệnh giao
ranh giới được tính đầy đủ vào phân rã nhóm. Drawdown của từng nhóm
được tính như sổ riêng, nên không cộng thành drawdown của sổ gốc.

| Mẫu | Đoạn | Trục | Bucket | n | Winrate | Net R | R lỗ |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| strict | peak_dd | cost_bucket | 6–12% | 25 | 24,0% | -8,09 | 20,12 |
| strict | peak_dd | cost_bucket | <6% | 49 | 38,8% | -11,59 | 28,37 |
| strict | peak_dd | atr_bucket | <0.25 | 21 | 23,8% | -6,47 | 16,98 |
| strict | peak_dd | atr_bucket | 0.25–<0.50 | 46 | 32,6% | -14,27 | 29,92 |
| strict | peak_dd | atr_bucket | ≥0.50 | 7 | 71,4% | +1,07 | 1,59 |
| strict | peak_dd | direction | SELL | 40 | 27,5% | -17,05 | 29,01 |
| strict | peak_dd | direction | BUY | 34 | 41,2% | -2,63 | 19,48 |
| strict | peak_dd | entry_window | 03:00–06:59 | 70 | 34,3% | -16,90 | 45,37 |
| strict | peak_dd | entry_window | 07:00–09:59 | 4 | 25,0% | -2,78 | 3,12 |
| strict | underwater | cost_bucket | >12% | 23 | 30,4% | -4,14 | 15,81 |
| strict | underwater | cost_bucket | 6–12% | 113 | 42,5% | -12,21 | 60,19 |
| strict | underwater | cost_bucket | <6% | 74 | 52,7% | +16,29 | 24,12 |
| strict | underwater | atr_bucket | <0.25 | 30 | 30,0% | -8,92 | 21,27 |
| strict | underwater | atr_bucket | 0.25–<0.50 | 131 | 46,6% | +7,75 | 60,85 |
| strict | underwater | atr_bucket | ≥0.50 | 49 | 49,0% | +1,11 | 18,01 |
| strict | underwater | direction | SELL | 96 | 41,7% | -6,18 | 49,26 |
| strict | underwater | direction | BUY | 114 | 47,4% | +6,12 | 50,87 |
| strict | underwater | entry_window | 03:00–06:59 | 174 | 43,1% | -2,93 | 87,09 |
| strict | underwater | entry_window | 07:00–09:59 | 36 | 52,8% | +2,87 | 13,03 |
| extended | peak_dd | cost_bucket | 6–12% | 128 | 38,3% | -23,10 | 66,40 |
| extended | peak_dd | cost_bucket | >12% | 32 | 34,4% | +1,09 | 19,38 |
| extended | peak_dd | cost_bucket | <6% | 51 | 41,2% | -4,57 | 17,21 |
| extended | peak_dd | atr_bucket | 0.25–<0.50 | 124 | 35,5% | -23,01 | 67,05 |
| extended | peak_dd | atr_bucket | <0.25 | 46 | 41,3% | +0,30 | 23,73 |
| extended | peak_dd | atr_bucket | ≥0.50 | 41 | 43,9% | -3,86 | 12,20 |
| extended | peak_dd | direction | SELL | 114 | 36,8% | -17,74 | 57,70 |
| extended | peak_dd | direction | BUY | 97 | 40,2% | -8,84 | 45,28 |
| extended | peak_dd | entry_window | 03:00–06:59 | 164 | 37,8% | -22,88 | 81,54 |
| extended | peak_dd | entry_window | 07:00–09:59 | 47 | 40,4% | -3,70 | 21,44 |
| extended | underwater | cost_bucket | 6–12% | 362 | 43,1% | -17,16 | 180,21 |
| extended | underwater | cost_bucket | >12% | 102 | 36,3% | +3,56 | 63,49 |
| extended | underwater | cost_bucket | <6% | 173 | 50,9% | +19,05 | 58,60 |
| extended | underwater | atr_bucket | 0.25–<0.50 | 382 | 43,7% | -5,20 | 186,67 |
| extended | underwater | atr_bucket | <0.25 | 134 | 40,3% | +5,70 | 75,09 |
| extended | underwater | atr_bucket | ≥0.50 | 121 | 49,6% | +4,95 | 40,53 |
| extended | underwater | direction | SELL | 325 | 42,8% | -11,87 | 160,63 |
| extended | underwater | direction | BUY | 312 | 45,5% | +17,32 | 141,66 |
| extended | underwater | entry_window | 03:00–06:59 | 510 | 42,2% | -8,27 | 254,57 |
| extended | underwater | entry_window | 07:00–09:59 | 127 | 52,0% | +13,71 | 47,72 |

### Năm và quý trong thời gian dưới đỉnh

| Mẫu | Năm hoặc quý mở lệnh | Lệnh trong đoạn | Net R | R lỗ |
| --- | --- | ---: | ---: | ---: |
| strict | 2020 | 31 | -7,83 | 16,72 |
| strict | 2021 | 104 | -5,77 | 53,75 |
| strict | 2022 | 75 | +13,54 | 29,66 |
| strict | 2020-Q3 | 14 | -3,13 | 7,60 |
| strict | 2020-Q4 | 17 | -4,70 | 9,12 |
| strict | 2021-Q1 | 24 | +5,06 | 9,04 |
| strict | 2021-Q2 | 13 | -6,67 | 9,35 |
| strict | 2021-Q3 | 23 | +1,36 | 12,68 |
| strict | 2021-Q4 | 44 | -5,52 | 22,67 |
| strict | 2022-Q1 | 45 | +3,14 | 19,41 |
| strict | 2022-Q2 | 30 | +10,40 | 10,25 |
| extended | 2018 | 6 | -0,44 | 4,26 |
| extended | 2019 | 191 | -23,98 | 93,25 |
| extended | 2020 | 189 | +18,14 | 86,94 |
| extended | 2021 | 167 | -6,23 | 85,49 |
| extended | 2022 | 84 | +17,96 | 32,35 |
| extended | 2018-Q4 | 6 | -0,44 | 4,26 |
| extended | 2019-Q1 | 49 | -12,50 | 27,03 |
| extended | 2019-Q2 | 50 | +1,88 | 20,10 |
| extended | 2019-Q3 | 55 | +1,92 | 21,15 |
| extended | 2019-Q4 | 37 | -15,27 | 24,98 |
| extended | 2020-Q1 | 47 | +15,62 | 16,67 |
| extended | 2020-Q2 | 55 | +2,13 | 25,99 |
| extended | 2020-Q3 | 53 | +6,76 | 27,04 |
| extended | 2020-Q4 | 34 | -6,37 | 17,25 |
| extended | 2021-Q1 | 40 | +7,90 | 14,73 |
| extended | 2021-Q2 | 29 | -5,28 | 16,82 |
| extended | 2021-Q3 | 38 | -2,84 | 22,22 |
| extended | 2021-Q4 | 60 | -6,03 | 31,72 |
| extended | 2022-Q1 | 52 | +6,41 | 22,10 |
| extended | 2022-Q2 | 32 | +11,54 | 10,25 |

### Phân tầng A/B của toàn sổ

| Mẫu | Cụm | Trục | Bucket | n | Winrate | Net R | Floating DD R của bucket |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| strict | A | cost_bucket | >12% | 45 | 31,1% | -4,90 | 16,73 |
| strict | A | cost_bucket | 6–12% | 270 | 45,9% | +15,41 | 17,56 |
| strict | A | cost_bucket | <6% | 167 | 54,5% | +11,69 | 9,39 |
| strict | A | atr_bucket | unknown | 11 | 45,5% | -0,43 | 5,96 |
| strict | A | atr_bucket | 0.25–<0.50 | 277 | 46,6% | +9,85 | 18,08 |
| strict | A | atr_bucket | <0.25 | 91 | 38,5% | -0,90 | 16,24 |
| strict | A | atr_bucket | ≥0.50 | 103 | 58,3% | +13,67 | 5,95 |
| strict | A | direction | SELL | 245 | 45,7% | +13,92 | 13,54 |
| strict | A | direction | BUY | 237 | 49,4% | +8,27 | 14,64 |
| strict | A | entry_window | 03:00–06:59 | 394 | 46,4% | +5,44 | 24,50 |
| strict | A | entry_window | 07:00–09:59 | 88 | 52,3% | +16,75 | 5,91 |
| strict | B | cost_bucket | <6% | 425 | 48,9% | +47,02 | 19,08 |
| strict | B | cost_bucket | >12% | 44 | 27,3% | -4,12 | 25,97 |
| strict | B | cost_bucket | 6–12% | 277 | 39,7% | +17,11 | 15,81 |
| strict | B | atr_bucket | ≥0.50 | 123 | 57,7% | +19,30 | 5,23 |
| strict | B | atr_bucket | <0.25 | 190 | 35,8% | +12,05 | 19,39 |
| strict | B | atr_bucket | 0.25–<0.50 | 433 | 44,1% | +28,65 | 22,04 |
| strict | B | direction | SELL | 347 | 40,3% | +5,02 | 26,43 |
| strict | B | direction | BUY | 399 | 47,6% | +54,99 | 17,90 |
| strict | B | entry_window | 03:00–06:59 | 629 | 42,4% | +48,12 | 24,62 |
| strict | B | entry_window | 07:00–09:59 | 117 | 53,8% | +11,88 | 6,95 |
| extended | A | cost_bucket | >12% | 78 | 38,5% | +15,08 | 16,38 |
| extended | A | cost_bucket | 6–12% | 342 | 43,3% | -5,15 | 29,66 |
| extended | A | cost_bucket | <6% | 181 | 52,5% | +9,56 | 9,72 |
| extended | A | atr_bucket | unknown | 11 | 45,5% | -0,43 | 5,96 |
| extended | A | atr_bucket | 0.25–<0.50 | 347 | 42,9% | -12,11 | 29,57 |
| extended | A | atr_bucket | <0.25 | 127 | 43,3% | +19,22 | 16,28 |
| extended | A | atr_bucket | ≥0.50 | 116 | 55,2% | +12,81 | 6,89 |
| extended | A | direction | SELL | 308 | 42,9% | +1,06 | 24,68 |
| extended | A | direction | BUY | 293 | 48,1% | +18,43 | 16,12 |
| extended | A | entry_window | 03:00–06:59 | 485 | 44,3% | +5,55 | 29,44 |
| extended | A | entry_window | 07:00–09:59 | 116 | 50,0% | +13,94 | 9,93 |
| extended | B | cost_bucket | <6% | 434 | 48,6% | +44,54 | 19,08 |
| extended | B | cost_bucket | >12% | 71 | 32,4% | -5,23 | 27,07 |
| extended | B | cost_bucket | 6–12% | 331 | 40,8% | +17,65 | 19,47 |
| extended | B | atr_bucket | ≥0.50 | 131 | 56,5% | +17,11 | 6,94 |
| extended | B | atr_bucket | <0.25 | 221 | 35,7% | +11,35 | 21,77 |
| extended | B | atr_bucket | 0.25–<0.50 | 484 | 44,6% | +28,49 | 22,04 |
| extended | B | direction | SELL | 390 | 40,0% | -2,32 | 26,43 |
| extended | B | direction | BUY | 446 | 47,8% | +59,27 | 21,01 |
| extended | B | entry_window | 03:00–06:59 | 701 | 41,9% | +42,02 | 22,93 |
| extended | B | entry_window | 07:00–09:59 | 135 | 55,6% | +14,94 | 6,80 |

Ở đáy DD mẫu mở rộng, nhóm phí/hộp 6–12% đóng góp **−23,10R net**
trên **66,40R lỗ gộp**. Nhóm >12% còn **+1,09R net** trong cùng đoạn.
Các lệnh trước 07:00 UTC chiếm **81,54R / 102,98R** lỗ gộp.
Nhóm này cũng có nhiều lệnh hơn. BUY/SELL và giờ vào ở đây phục vụ
quy kết kế toán, chưa là bằng chứng cho một bộ lọc mới.

## 3. Quyết định và kiểm chứng

Giữ USDJPY Tokyo-box gốc làm chuẩn Engine #1. Gác variant 12%.
Giữ ENGINE_1_NEEDS_PARTNER. Track US500 cần QDM Development đủ hai cụm trước khi ra phán quyết kinh tế.

Bộ quant đầy đủ đạt **1.511 test, 0 skip, 0 lỗi**.
Lần chạy đầu có fixture quét tên toàn đường dẫn, bị tên asset trong
thư mục tạm nhiễu. Chạy lại ở thư mục tạm trung tính, giữ log cũ.
Khóa giá từ 01/01/2025, OrderSend = 0, hai gitlink và WIP VI Dubber
được kiểm trước commit. SHA của báo cáo/JSON tính trên blob Git LF.

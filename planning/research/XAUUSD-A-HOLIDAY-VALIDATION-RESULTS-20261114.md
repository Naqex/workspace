# A BOTH/no hard TP — lịch đóng sớm, Validation 2024 và tài khoản liên tục

Ngày hoàn tất: 14/11/2026. [Protocol đã khóa](XAUUSD-A-HOLIDAY-VALIDATION-PROTOCOL-20261114.md) / [Lịch đã khóa](XAUUSD-A-SESSION-CALENDAR-20261114.json) / [JSON đầy đủ](XAUUSD-A-HOLIDAY-VALIDATION-RESULTS-20261114.json).

**2024:** SYM 1.845R; ASYM 2.645R. 
Đây là kết quả mô phỏng có điều kiện trên nguồn giá và giả định đã khai báo, chưa phải FTMO-qualified hoặc bằng chứng đã nhận payout. 2024 là Historical Validation đã có exposure trước đó; 2025–2026 vẫn đóng hoàn toàn.

**Quyết định đề xuất: gác A BOTH khỏi đường Challenge hiện tại, giữ làm benchmark nghiên cứu.** Tần suất đã đủ dùng nhưng tốc độ tích lũy R còn thấp, phụ thuộc đuôi phải; không cửa sổ nào hoàn tất cả hai vòng. Không đề xuất tăng risk tiếp hoặc mở 2025–2026 để cứu kết quả.

## 1. Phạm vi và cơ chế được giữ nguyên

PR77 (`dc121db`) đã merge vào `main` tại `3406ed1`; nhánh cũ đã xóa. Lượt mới chỉ A BOTH/no hard TP, không chạy C, TP2R, SELL-only hay tìm tham số mới.

Nói đơn giản: dùng H4 để biết hướng; đợi nến H1 phá biên phiên Á cùng hướng; vào tại Bid/Ask quan sát được sau nến đóng. SL vẫn ở phía đối diện vùng Á cộng đệm ATR H1 đã đăng ký. Không có TP cứng: thoát khi SL bị chạm, đủ 48 giờ lịch hoặc tới mốc đóng bắt buộc, tùy điều gì xảy ra trước. Tối đa một tín hiệu A mỗi ngày; các vị thế khác ngày có thể chồng nhau.

Luồng tính: M1 được nhận diện nguồn → H1/H4 và tín hiệu cố định → tick Bid/Ask → SL/lịch đóng → commission, slippage, swap → equity chung của mọi vị thế → reset 00:00 Prague → điều kiện từng vòng. Không cộng MAE riêng của các lệnh và không ghép các sổ reset theo năm thành tài khoản liên tục.

210 tín hiệu Development khớp hoàn toàn parent; 98 tín hiệu Validation. Sau sửa nguồn M1, toàn bộ 308 bản ghi tín hiệu và SL vẫn giống trước sửa. Chưa có outcome tài chính trong lượt sửa dữ liệu đầu tiên.

## 2. Lịch đóng sớm và độ phủ

Thứ Sáu thường đóng trước 20:30 UTC; ngày lễ/đóng sớm dùng guard cố định 17:00 UTC, hoặc mốc sớm hơn đã xác minh. Good Friday đóng từ tối thứ Năm; ngày thị trường đóng không nhận entry. Giờ nghỉ rollover thông thường không kích hoạt holiday exit. Mốc hạn là `min(entry + 48 giờ lịch, mốc flat kế tiếp)`, dùng quote đầu tiên trong tối đa 60 giây; không chọn quote cuối cùng bằng hindsight hoặc đẩy lệnh sang thứ Hai.

Guard 17:00 là quyết định thận trọng đã khóa trước khi mở giá 2024, không phải khẳng định mọi ngày lễ FTMO đều đóng lúc 17:30. Lịch bao phủ các ngày lễ được liệt kê trong protocol; giờ đóng chính xác của một số ngày vẫn thiếu nguồn FTMO lịch sử. Không nâng coverage của nguồn giá thành chứng nhận toàn bộ lịch tài khoản đích.

Lệnh BUY **24/11/2023**: entry 24/11/2023 11:00:00 UTC, exit 24/11/2023 17:00:00 UTC, lý do `HOLIDAY_FLAT`. Net SYM 0.673R / ASYM 0.673R. [Thông báo FTMO](https://ftmo.com/en/blog/trading-updates/trading-update-23-nov-2023/) ghi metals đóng 20:45 GMT+2 = 18:45 UTC hôm đó; guard của nghiên cứu thoát sớm hơn.

So với PR77, chỉ ba lệnh Development đổi điểm thoát: 17/01/2022 và 04/07/2022 do holiday flat, cùng 24/11/2023 được khôi phục. ASYM năm 2022 giảm từ +9,421R xuống +5,901R: lệnh SELL 04/07 từng +3,921R khi giữ qua kỳ đóng cửa, nay −0,333R; lệnh 17/01 bớt lỗ. Năm 2023 thêm +0,673R từ lệnh Black Friday. Đây là tác động của lịch đóng đã khóa, không do sửa tín hiệu hay chọn lại tham số.

| Năm | Tín hiệu gốc | BUY | SELL | Có đường thoát | Bị loại bởi lịch |
| --- | --- | --- | --- | --- | --- |
| 2022 | 103 | 54 | 49 | 103/103 | 0 |
| 2023 | 107 | 57 | 50 | 107/107 | 0 |
| 2024 | 98 | 61 | 37 | 98/98 | 0 |

Dùng 9,502 giờ nguồn, 79,537,988 tick được yêu cầu; ledger chung đo 52,026,392 tick khi có vị thế. Không có khoảng trống quote >2 giờ lúc đang giữ lệnh trên nguồn quan sát. Có 222 lần reset khi đang giữ lệnh; 209 lần quote gần nhất cũ hơn 60 giây. Không suy diễn giá giữa các tick hoặc coi nguồn Dukascopy là lịch sử khớp lệnh FTMO.

Anchor balance tại reset được giữ riêng, không cộng floating vào balance. Floating tại reset giữ quote quan sát gần nhất khi chưa có quote mới; đó không phải fresh mark. Các con số DD/daily và “không breach” chỉ đúng trên đường mark đã khai báo; chưa có bound cho biến động không quan sát hoặc bằng chứng tương đương đường giá tài khoản FTMO. Coverage 308/308 nói về các endpoint và tick đã nhận, không biến phần chưa quan sát thành an toàn.

## 3. Thông số đích và chi phí

| Thông số | Giá trị dùng | Mức xác minh |
| --- | --- | --- |
| Contract size | 100 oz/lot | Có đối chiếu chính thức FTMO 26/09/2024; chưa có snapshot tài khoản cụ thể |
| Min/step lot | 0,01 / 0,01 | Giả định nghiên cứu; chưa xác minh snapshot tài khoản đích |
| Commission | 0,0007% notional mỗi side, làm tròn cent | Nguồn FTMO công khai, hiệu lực từ 29/09/2025; không giả là lịch phí thực tế 2022–24 |
| Spread | Bid/Ask tick quan sát | Dukascopy; chưa xác minh parity với FTMO |
| Slippage stress | 0,20 USD/oz mỗi side | Giả định giữ nguyên, gồm market/SL/time/holiday exit |
| Swap SYM | BUY −40 / SELL −40 USD/lot/đơn vị rollover | Stress khai báo, không phải biểu phí đã đo |
| Swap ASYM | BUY −45 / SELL −5 USD/lot/đơn vị rollover | Proxy khai báo, không phải khoảng swap thực tế đã xác minh |
| Clock swap | 22:00 UTC ngày trong tuần; thứ Tư ×3 | Proxy; chưa có lịch swap thực tế theo ngày/holiday/DST |

Nguồn: [contract size](https://ftmo.com/en/blog/trading-updates/trading-update-26-sep-2024/), [commission](https://ftmo.com/en/blog/trading-updates/trading-update-25-sep-2025/), [swap thay đổi và cần xem trong contract specification](https://ftmo.com/en/blog/trading-updates/trading-update-10-sep-2026/). Không hạ phí để cứu kết quả; cũng không gọi các proxy là mức stress đã bao trùm mọi swap thực tế.

Risk giá tới SL cố định 150 USD hoặc 200 USD trên sổ 50.000 USD; khối lượng `floor(risk / khoảng SL)` oz. Không compounding, không nhân kết quả 0,30% lên 0,40%; lot được tính lại. Phí, swap và gap có thể làm lỗ vượt risk danh nghĩa.

## 4. Kết quả từng năm

Mỗi năm bắt đầu riêng từ 50k. DD đỉnh–đáy tính trên equity gồm floating; static loss tính phần equity thấp hơn vốn đầu; daily loss tính từ balance đầu ngày Prague, không lấy equity đầu ngày làm anchor. % dùng mẫu số 50k cố định.

### Risk 0.30%/lệnh (150 USD)

| Năm | Phí | Số lệnh | Net R | Mean R/lệnh | Lãi ròng % | Equity DD R / % | Static loss % | Worst daily % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2022 | SYM −40/−40 | 103 | 4.050 | 0.039 | 1.215 | 16.617 / 4.985 | 1.112 | 0.686 |
| 2023 | SYM −40/−40 | 107 | 13.795 | 0.129 | 4.138 | 22.177 / 6.653 | 3.202 | 0.799 |
| 2024 | SYM −40/−40 | 98 | 1.845 | 0.019 | 0.554 | 13.233 / 3.970 | 3.486 | 0.623 |
| 2022 | ASYM −45/−5 | 103 | 5.901 | 0.057 | 1.770 | 15.975 / 4.792 | 1.112 | 0.698 |
| 2023 | ASYM −45/−5 | 107 | 16.462 | 0.154 | 4.939 | 20.893 / 6.268 | 2.818 | 0.731 |
| 2024 | ASYM −45/−5 | 98 | 2.645 | 0.027 | 0.793 | 12.977 / 3.893 | 3.409 | 0.624 |

### Risk 0.40%/lệnh (200 USD)

| Năm | Phí | Số lệnh | Net R | Mean R/lệnh | Lãi ròng % | Equity DD R / % | Static loss % | Worst daily % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2022 | SYM −40/−40 | 103 | 4.210 | 0.041 | 1.684 | 16.858 / 6.743 | 1.492 | 0.924 |
| 2023 | SYM −40/−40 | 107 | 13.565 | 0.127 | 5.426 | 22.184 / 8.874 | 4.276 | 1.071 |
| 2024 | SYM −40/−40 | 98 | 1.199 | 0.012 | 0.480 | 13.475 / 5.390 | 4.706 | 0.811 |
| 2022 | ASYM −45/−5 | 103 | 6.064 | 0.059 | 2.426 | 16.147 / 6.459 | 1.492 | 0.925 |
| 2023 | ASYM −45/−5 | 107 | 16.242 | 0.152 | 6.497 | 20.890 / 8.356 | 3.758 | 0.979 |
| 2024 | ASYM −45/−5 | 98 | 2.004 | 0.020 | 0.801 | 13.271 / 5.308 | 4.604 | 0.813 |

### Sổ liên tục 2022–2024, không reset mỗi năm

| Risk | Phí | Net R | Lãi % | Equity DD R / % | Static loss % | Worst daily % | Vị thế đồng thời tối đa |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0.30% | SYM −40/−40 | 19.690 | 5.907 | 22.177 / 6.653 | 1.987 | 0.799 | 3 |
| 0.30% | ASYM −45/−5 | 25.007 | 7.502 | 20.893 / 6.268 | 1.112 | 0.731 | 3 |
| 0.40% | SYM −40/−40 | 18.974 | 7.590 | 22.184 / 8.874 | 2.592 | 1.071 | 3 |
| 0.40% | ASYM −45/−5 | 24.310 | 9.724 | 20.890 / 8.356 | 1.492 | 0.979 | 3 |

## 5. Lợi nhuận tập trung ở đâu?

Top 3 theo từng mô hình swap, tại risk 150 USD. Đây chỉ là chẩn đoán độ phụ thuộc vào đuôi phải, không lọc bỏ hay chọn lại hướng giao dịch.

| Năm | Phí | Hạng | Chiều | Entry UTC | Exit UTC | Lý do | Net R |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2022 | SYM −40/−40 | 1 | SELL | 2022-07-05 08:00:00 | 2022-07-07 08:00:00 | TIME_48H | 9.052 |
| 2022 | SYM −40/−40 | 2 | BUY | 2022-02-11 12:00:00 | 2022-02-11 20:30:00 | FRIDAY_CLOSE | 7.151 |
| 2022 | SYM −40/−40 | 3 | BUY | 2022-11-08 15:00:00 | 2022-11-10 15:00:00 | TIME_48H | 4.990 |
| 2022 | ASYM −45/−5 | 1 | SELL | 2022-07-05 08:00:00 | 2022-07-07 08:00:00 | TIME_48H | 9.267 |
| 2022 | ASYM −45/−5 | 2 | BUY | 2022-02-11 12:00:00 | 2022-02-11 20:30:00 | FRIDAY_CLOSE | 7.151 |
| 2022 | ASYM −45/−5 | 3 | BUY | 2022-11-08 15:00:00 | 2022-11-10 15:00:00 | TIME_48H | 4.974 |
| 2023 | SYM −40/−40 | 1 | SELL | 2023-09-26 10:00:00 | 2023-09-28 10:00:00 | TIME_48H | 9.281 |
| 2023 | SYM −40/−40 | 2 | SELL | 2023-02-03 08:00:00 | 2023-02-03 20:30:00 | FRIDAY_CLOSE | 8.446 |
| 2023 | SYM −40/−40 | 3 | BUY | 2023-08-28 14:00:00 | 2023-08-30 14:00:00 | TIME_48H | 6.436 |
| 2023 | ASYM −45/−5 | 1 | SELL | 2023-09-26 10:00:00 | 2023-09-28 10:00:00 | TIME_48H | 9.654 |
| 2023 | ASYM −45/−5 | 2 | SELL | 2023-02-03 08:00:00 | 2023-02-03 20:30:00 | FRIDAY_CLOSE | 8.446 |
| 2023 | ASYM −45/−5 | 3 | BUY | 2023-08-28 14:00:00 | 2023-08-30 14:00:00 | TIME_48H | 6.413 |
| 2024 | SYM −40/−40 | 1 | BUY | 2024-11-20 15:00:00 | 2024-11-22 15:00:00 | TIME_48H | 4.910 |
| 2024 | SYM −40/−40 | 2 | BUY | 2024-03-04 08:00:00 | 2024-03-06 08:00:00 | TIME_48H | 4.477 |
| 2024 | SYM −40/−40 | 3 | BUY | 2024-07-15 11:00:00 | 2024-07-17 11:00:00 | TIME_48H | 4.453 |
| 2024 | ASYM −45/−5 | 1 | BUY | 2024-11-20 15:00:00 | 2024-11-22 15:00:00 | TIME_48H | 4.890 |
| 2024 | ASYM −45/−5 | 2 | BUY | 2024-03-04 08:00:00 | 2024-03-06 08:00:00 | TIME_48H | 4.465 |
| 2024 | ASYM −45/−5 | 3 | BUY | 2024-07-15 11:00:00 | 2024-07-17 11:00:00 | TIME_48H | 4.445 |

| Năm | Phí | <−1R | =−1R | (−1,0)R | [0,1)R | [1,3]R | >3R |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2022 | SYM −40/−40 | 38 | 0 | 29 | 20 | 9 | 7 |
| 2022 | ASYM −45/−5 | 35 | 0 | 32 | 20 | 9 | 7 |
| 2023 | SYM −40/−40 | 53 | 0 | 16 | 13 | 17 | 8 |
| 2023 | ASYM −45/−5 | 53 | 0 | 15 | 14 | 17 | 8 |
| 2024 | SYM −40/−40 | 30 | 1 | 30 | 12 | 21 | 4 |
| 2024 | ASYM −45/−5 | 27 | 1 | 33 | 12 | 21 | 4 |

Các nhóm không chồng nhau; phí/slippage/swap có thể đẩy lệnh SL xuống dưới −1R, nên không gộp tất cả vào đúng −1R. Zero nằm ở [0,1), 3R nằm ở [1,3].

| Năm | Phí | Tổng Net R | Top 3 R | Phần còn lại R |
| --- | --- | --- | --- | --- |
| 2022 | SYM −40/−40 | 4.050 | 21.192 | -17.142 |
| 2022 | ASYM −45/−5 | 5.901 | 21.391 | -15.490 |
| 2023 | SYM −40/−40 | 13.795 | 24.164 | -10.369 |
| 2023 | ASYM −45/−5 | 16.462 | 24.514 | -8.052 |
| 2024 | SYM −40/−40 | 1.845 | 13.840 | -11.995 |
| 2024 | ASYM −45/−5 | 2.645 | 13.800 | -11.155 |

## 6. Vòng đời Challenge và funded

36 mốc bắt đầu theo tháng, mỗi mốc bắt đầu flat, giữ state qua năm. 12 mốc quý là tập con, không phải 12 bằng chứng độc lập mới. Hai risk × hai phí = 144 kịch bản cùng họ; đây không phải 144 thử nghiệm tìm tham số.

Dùng scenario [FTMO 2-Step](https://ftmo.com/en/trading-objectives/): vòng 1 +10%, vòng 2 +5%, ít nhất 4 ngày mở lệnh Prague mỗi vòng, daily loss 5%, overall static loss 10%; breach được xét trước pass. Chỉ pass khi flat rồi reset về 50k; tín hiệu cũ không được dùng lại, không auto-retry. Không mô phỏng thời gian xét duyệt/admin, margin hoặc lịch tin. Funded bắt đầu 50k, theo dõi hai giới hạn lỗ; chưa mô phỏng rút lợi nhuận, phí challenge, chia profit hay payout.

Theo [FAQ FTMO](https://ftmo.com/en/faq/can-i-hold-positions-overnight-or-over-the-weekend/), Challenge/Verification được miễn hạn chế giữ qua market break >2 giờ. Lượt này vẫn dùng cùng lịch flat thận trọng cho cả Challenge và funded để giữ cùng một cách giao dịch. News restriction của funded Standard vẫn chưa được kiểm.

### 36 mốc tháng

| Risk | Phí | Qua vòng 1 | Qua cả 2 | Median vòng 1 (tháng) | Median vòng 2 (tháng) | Median tổng (tháng) | Breach challenge / funded |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0.30% | SYM −40/−40 | 0/36 | 0/36 | — | — | — | 0 / 0 |
| 0.30% | ASYM −45/−5 | 0/36 | 0/36 | — | — | — | 0 / 0 |
| 0.40% | SYM −40/−40 | 2/36 | 0/36 | 12.82 | — | — | 0 / 0 |
| 0.40% | ASYM −45/−5 | 5/36 | 0/36 | 15.67 | — | — | 0 / 0 |

### 12 mốc quý — tập con

| Risk | Phí | Qua vòng 1 | Qua cả 2 | Median vòng 1 (tháng) | Median vòng 2 (tháng) | Median tổng (tháng) | Breach challenge / funded |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0.30% | SYM −40/−40 | 0/12 | 0/12 | — | — | — | 0 / 0 |
| 0.30% | ASYM −45/−5 | 0/12 | 0/12 | — | — | — | 0 / 0 |
| 0.40% | SYM −40/−40 | 1/12 | 0/12 | 4.36 | — | — | 0 / 0 |
| 0.40% | ASYM −45/−5 | 3/12 | 0/12 | 15.67 | — | — | 0 / 0 |

Median chỉ tính các cửa sổ đã hoàn thành đúng chặng; dấu — nghĩa không có cửa sổ hoàn thành. Các cửa sổ cuối 2024 có thời gian quan sát ngắn. Không diễn giải tỷ lệ trên thành xác suất pass thật hoặc thời gian hoàn tất bảo đảm.

Các mô hình phí có tập cửa sổ hoàn tất khác nhau; median thấp hơn của nhóm ít passer không có nghĩa mô hình phí cao hiệu quả hơn. Chưa hoàn tất khi hết dữ liệu là right-censored, khác vi phạm tài khoản.

| Risk | Phí | Chưa xong vòng 1 / 2 tại cutoff | Chạm daily / overall | Daily lớn nhất % | Static loss lớn nhất % | Funded còn hoạt động tại cutoff |
| --- | --- | --- | --- | --- | --- | --- |
| 0.30% | SYM −40/−40 | 36 / 0 | 0 / 0 | 0.799 | 5.271 | Chưa có funded |
| 0.30% | ASYM −45/−5 | 36 / 0 | 0 / 0 | 0.731 | 4.895 | Chưa có funded |
| 0.40% | SYM −40/−40 | 34 / 2 | 0 / 0 | 1.071 | 7.234 | Chưa có funded |
| 0.40% | ASYM −45/−5 | 31 / 5 | 0 / 0 | 0.979 | 7.083 | Chưa có funded |

Không có cửa sổ vào funded trong dữ liệu này, nên chưa có PnL/thời gian sống funded thực nghiệm để báo. Nhánh funded của bộ mô phỏng đã có fixture kiểm reset vốn và theo dõi, nhưng fixture không thay kết quả thị trường.


## 7. Kiểm chứng, provenance và điểm còn thiếu

14 fixture mới + 18 regression execution + 12 regression Stage-0 đạt; hai negative CLI guard chặn dữ liệu 2025 và sai holdout fence trước network. Phép tính riêng đối soát 308 điểm thoát, 1232 cost bridges bằng phân số, 12 annual cost-books tại hai risk trên 104,052,784 tick marks; 144 lifecycle records kiểm invariants và native terminal oracle. Đây là **self-audit bằng cách tính khác**, không phải independent/ASTRA review.

Lượt 1 dừng trước PnL do 11 M1 revisions năm 2024. Lượt 2 dùng working correction có SHA/raw provenance; original không bị ghi đè. Có hai phút tick tồn tại nhưng nguồn M1 không có (09/10/2024 23:05 và 12/12/2024 00:58 UTC); không tạo thêm M1 để thay tín hiệu đã khóa. Tick vẫn được dùng cho đường vốn. Không thiếu tick cho bất kỳ phút M1 đã nhận nào trong các giờ bổ sung.

Private job: `E:\BACKUP-TRADINGWORKSPACE\ai-engine-jobs\challenge-discovery4-20261108\execution-v1\xauusd-a-validation-20261114`. Attempt hiện hành: `attempt-2`; config `execution-config-v2.json`, code `source-snapshot-v1`, input correction `source-snapshot-v2`. Giữ `attempt-1/failure.json`, source review, calendar freeze, signal parity, guards và hash bindings trong JSON báo cáo. Nguồn năm 2025–2026 không được mở; broker/model calls = 0.

Các giới hạn còn lại: lịch FTMO lịch sử chưa xác minh đủ từng giờ đóng/reopen/maintenance; min/step lot tài khoản, swap thực và rollover clock; parity spread/fill với FTMO; margin/hedging/admission; lịch tin và forbidden-practice checks; lựa chọn nhiều cơ chế/horizon trước đây và 2024 đã có exposure; phụ thuộc các lệnh thắng lớn; chưa có fresh/prospective validation hoặc payout simulation đầy đủ. Worst Daily Loss đo trong quá khứ không đồng nghĩa an toàn tuyệt đối trong tương lai.

## 8. Hậu kiểm kỹ thuật và bước tiếp

| Điểm | Bằng chứng / quyết định |
| --- | --- |
| Đúng dữ liệu | Guard bắt 11 M1 khác tick trước PnL; sửa working copy, giữ 308/308 signals và SL; không chọn lại luật |
| Tái sử dụng | Kế thừa 6.294 giờ binary, 425 giờ raw; chỉ tải phần còn thiếu. Ledger giữ tick extrema theo thứ tự và các tập vị thế để reuse mốc bắt đầu |
| Độ tin cậy | Attempt lỗi và config/snapshot riêng được giữ; không ghi đè pin hoặc chạy lặp strategy sweep |
| Môi trường | Python PATH thiếu tzdata; chuyển sang bundled runtime đã có, không cài thêm package |
| Phạm vi | Không thêm skill/engine quản lý mới: workflow hiện có đã yêu cầu pin-before-outcome, coverage và self-audit; chỉ bổ sung adapter/replay và regression cần thiết |

**Kết luận:** có dấu hiệu lợi nhuận dương trong mô hình đã đo, nhưng chưa chứng minh edge bền vững hoặc đáp ứng time-fit cho Challenge/thu nhập chính. Không gắn ECONOMIC_FAIL chỉ vì chưa pass Challenge, cũng không gắn PROP_VIOLATED khi mô phỏng chưa có breach. Giữ cấu hình và bằng chứng làm benchmark; gác khỏi danh sách triển khai Challenge hiện tại. Không chạy thêm chiến lược, risk, holdout hoặc broker trong lượt này. Cần quyết định nghiên cứu riêng trước bước mới; skill/workflow hiện có không bảo đảm tìm được alpha chỉ nhờ kiểm định đúng.

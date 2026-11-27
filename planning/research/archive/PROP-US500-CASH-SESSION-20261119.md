# US500 · Mua gần trọn phiên cash có đủ tiến độ thi quỹ?

**Gác chuẩn BUY 09:31 → 15:59 New York đã khóa.** Phép thử đạt nhịp gần
mỗi phiên nhưng biên độ gộp ở mức risk 125 USD chỉ đạt 185 và 594 USD/năm
qua hai cụm. Giữ tới phút cuối lỗ sau phí ở cả hai cụm. Mẫu có đủ
đường stop cũng âm, và mô hình lạc quan cho phần thiếu vẫn không đạt
ngưỡng. `BASE_GUARD` giữ `NOT_QUALIFIED`.

## Chuẩn so sánh

R053 luôn LONG theo lịch tháng và có phí qua đêm. R051 và R076 dùng
cửa sổ ngắn với ngày được chọn theo giá hoặc lịch của từng nghiên cứu.
Các sổ đó giúp đối chiếu giả thuyết, chưa trả lời câu hỏi mua gần trọn
phiên trên mọi ngày NYSE ở cùng mức vốn. R120 là đối chứng M15 duy nhất
được đăng ký cho phần chồng lấn 2022–2023.
[R053](US500-MONTHLY-TREND-RESULTS-20261108.md) ·
[R051](FTMO-INDEX-COMMISSION-RESULTS-20261108.md) ·
[R076](INDEX-REST-OF-DAY-PROTOCOL-20261109.md) ·
[R120](US500-R120-SAVED-REVIEW-20261112.md).

- Vào Ask Open M1 đúng 09:31 New York mỗi phiên, trượt +0,75 điểm. Đóng
  Bid Open 15:59 hoặc 12:59 ngày đóng sớm, trượt −0,75 điểm. Stop thấp
  hơn fill 1% và làm tròn xuống lưới 0,001 điểm. Khi Bid Low chạm stop,
  khớp tại mức thấp hơn giữa Bid Open và stop, trừ trượt. Ngừng xét Low
  ngay trước Open dùng để đóng phiên. Thiếu giá entry ghi phiên không
  vào. Thiếu phút trước khi xác nhận lần chạm stop hoặc thoát đúng hạn
  giữ outcome chưa rõ.
- Vốn 50.000 USD, risk dự tính tối đa 125 USD mỗi phiên ở mức stop,
  đã dự phòng trượt. Dùng 1 USD/điểm/lot và min/step 0,01 lot làm
  giả định mô phỏng, làm tròn lot xuống. Spread nằm trong Bid/Ask.
  Commission 0 theo công bố cho US500.cash. 12 phiên đóng sớm được giữ
  theo lịch NYSE. Tất cả thời điểm thoát đã khóa trước 17:00 New York
  và trước reset Prague cùng ngày, nên ghi funding 0 cho phép đo này.
- Giá thuộc Dukascopy USA500.IDX/USD, M1 có Bid/Ask nguồn ở cả sáu năm
  qua proof V11. Dùng IANA New York cho DST và fixture lịch 2018–2023.
  Quote M1 là Opens của hai phía. Chưa xác nhận khớp tick, biểu phí
  lịch sử hay giờ mở cửa từng ngày của tài khoản FTMO. Mốc cash luôn
  theo NYSE trong phép đo này.
  [Nguồn V11](ENSEMBLE-AND-STORAGE-V11-RESULTS-20261115.md) ·
  [Đặc tả US500.cash đã lưu](FTMO-SYMBOL-AND-CLOCK-ADMISSION-20261108.md) ·
  [FTMO về commission chỉ số](https://ftmo.com/en/blog/zero-commissions-on-indices/).

## 1. Nhịp đủ, tiền trong phiên không đủ

| Năm | Phiên lịch / vào / có endpoint | Midpoint, bp/phiên | Gộp midpoint, USD | Spread, USD | Trượt, USD | Net endpoint, USD | Đủ đường stop / đã vào | Net có stop, USD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2018 | 251 / 250 / 250 | −6,78 | −2.063,85 | 460,76 | 1.659,92 | −4.184,54 | 141/250 | −4.740,78 |
| 2019 | 252 / 252 / 252 | +5,54 | +1.693,69 | 365,06 | 1.583,81 | −255,17 | 114/252 | −822,99 |
| 2020 | 253 / 248 / 248 | +3,09 | +924,10 | 412,31 | 1.423,13 | −911,35 | 209/248 | −3.060,98 |
| 2021 | 252 / 252 / 252 | +3,96 | +1.221,64 | 312,79 | 1.089,45 | −180,64 | 195/252 | −1.472,87 |
| 2022 | 251 / 251 / 251 | −5,18 | −1.600,56 | 339,69 | 1.130,21 | −3.070,47 | 249/251 | −2.158,12 |
| 2023 | 250 / 250 / 249 | +7,09 | +2.160,12 | 361,34 | 1.072,94 | +725,93 | 241/250 | +546,77 |
| **Cả kỳ** | **1.509 / 1.503 / 1.502** | **+1,28** | **+2.335,15** | **2.251,95** | **7.959,44** | **−7.876,24** | **1.149/1.503** | **−11.708,97** |

Gộp midpoint nhân với lot của đúng phiên. Mỗi giao dịch làm tròn USD
đến cent nên tổng bảng có sai lệch làm tròn nhỏ. Có ít nhất một lệnh
vào trong cả 313 tuần có phiên lịch. 24 tuần thiếu toàn bộ kết quả
stop do đường giá, tập trung ở 2018–2020.

| Cụm | Gộp midpoint / năm | Net endpoint / phiên định giá | Net endpoint / năm | Còn thiếu để đạt +5.000 USD/năm theo endpoint |
| --- | ---: | ---: | ---: | ---: |
| 2018–2020 | +184,65 USD | −7,13 USD | −1.783,69 USD | 6.783,69 USD/năm, khoảng 27,13 USD/phiên |
| 2021–2023 | +593,74 USD | −3,36 USD | −841,73 USD | 5.841,73 USD/năm, khoảng 23,31 USD/phiên |

Ngay ở giá giữa trước phí, cả hai cụm đều dưới mốc 1.000 USD/năm để
đầu tư kiểm định kế tiếp. Chênh giá trung bình trước phí chỉ +0,03 và
+0,64 điểm/phiên. Mỗi vòng lệnh chịu riêng trượt 1,50 điểm.

## 2. Stop thay đổi bao nhiêu và 354 phiên thiếu có thể cứu kết quả không?

| Cụm | Đủ đường / đã vào | Chạm stop | Net quan sát có stop | Tác động stop trên cùng mẫu có giá | Nếu mỗi lệnh thiếu lỗ 125 USD |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2018–2020 | 464/750 (61,9%) | 157 | −8.624,75 USD | −1.499,97 USD | −44.374,75 USD |
| 2021–2023 | 685/753 (91,0%) | 169 | −3.084,22 USD | +488,74 USD | −11.584,22 USD |
| **Cả kỳ** | **1.149/1.503 (76,4%)** | **326** | **−11.708,97 USD** | **−1.011,23 USD** | **−55.958,97 USD** |

Cột tác động stop dùng đúng 1.149 lệnh có cả giá thoát theo stop và
endpoint. 354 đường thiếu vẫn đi vào mẫu số. Trong nhóm này, 353 lệnh
có cặp giá vào/ra, tổng endpoint **+2.821,50 USD**. Nhóm đủ đường vì
thế có thành phần khác nhóm thiếu. Không gán tiền endpoint thành PnL
đã xác nhận của lệnh có stop. Phép mất 125 USD mỗi lệnh thiếu chỉ là
độ nhạy, vì giá mở sau gap có thể xuyên stop. Lệnh lỗ lớn nhất trong mẫu đủ đường
mất 149,91 USD sau gap, so với risk dự tính tối đa 125 USD.

Để hòa vốn khi cộng phần thiếu vào sổ quan sát, mỗi lệnh thiếu phải
lời bình quân **30,16 USD** ở cụm đầu và **45,36 USD** ở cụm sau. Có
thể kiểm thêm bằng giả định thuận lợi nhất trong chính mô hình đã
khóa. Với mỗi lệnh thiếu nhưng có endpoint, chọn số lớn hơn giữa
endpoint và giả định stop khớp đúng mức stop trừ trượt. Tổng vẫn
**−6.568,59 USD** ở 2018–2020 và **−2.036,44 USD** ở 2021–2023, còn
một phiên 2023 thiếu cả giá ra. Phiên đó phải lời hơn 2.036,44 USD mới
lật dấu cụm sau trong giả định thuận lợi này. Đây là giới hạn có điều
kiện của phép tính, còn kết quả chính xác của từng đường thiếu vẫn
chưa biết.

Trên 1.149 lệnh đã định giá: trung vị −10,96 USD, phân vị 5/95 là
−124,95 / +158,16 USD. Top 10 lệnh thắng đóng góp 4.173,60 USD,
10,1% tổng tiền từ lệnh thắng. Bỏ top 10, net quan sát còn
−15.882,57 USD. Khoản lỗ tổng không phụ thuộc việc giữ vài lệnh lớn.

## 3. Phần chuyển động nằm ngoài thời gian giữ

So midpoint Open 15:59 hoặc 12:59 với midpoint Open 09:31 của phiên lịch
liền sau. Chỉ dùng cùng các cặp có đủ giá ở cả ba mốc, giữ nguyên các
phiên bị thiếu ở mẫu số. Một bp là 0,01%. Các cột là trung bình lợi
suất trên cùng tập, close-to-close nối hai chân theo tích.

| Cụm | Cặp đủ / cặp lịch | Sau giờ giữ → vào phiên sau | Trong giờ giữ | Close-to-close |
| --- | ---: | ---: | ---: | ---: |
| 2018–2020 | 746/755 | +6,85 bp | +0,51 bp | +7,46 bp |
| 2021–2023 | 751/753 | +1,84 bp | +1,96 bp | +3,79 bp |
| **Cả kỳ** | **1.497/1.508** | **+4,33 bp** | **+1,24 bp** | **+5,62 bp** |

Ở cụm đầu, phần lớn mức tăng close-to-close nằm ngoài cửa sổ giữ.
Cụm sau, hai phần gần ngang nhau. Các giá này mô tả chuyển động,
chưa tính spread/funding qua đêm hay giả định mở thêm chiến lược.

## 4. So BASE và phần M15 đã có

Sổ BASE là V19 Development với yêu cầu risk stop giá 125 USD/lệnh
qua bước lot, cùng đơn vị vốn 50.000 USD. Sizer BASE dùng khoảng stop
giá, còn chuẩn US500 tính trượt trong dự phòng stop. PRIMARY dùng
đường cơ sở, STRICT mô phỏng bất lợi ở phần nguồn thiếu. Đây là so
hai sổ riêng cùng kỳ, không cộng vốn hay tính tương tác vị thế.
[Đối chứng V19](ASYMMETRIC-RECOVERY-V19-RESULTS-20261116.md).

| Cụm | US500 stop quan sát | BASE PRIMARY | BASE STRICT |
| --- | ---: | ---: | ---: |
| 2018–2020 | −8.624,75 USD | +1.157,80 USD | +745,65 USD |
| 2021–2023 | −3.084,22 USD | +1.830,33 USD | −1.723,20 USD |
| Cả kỳ | −11.708,97 USD | +2.988,13 USD | −977,55 USD |
| Cash DD đỉnh–đáy cả kỳ | 12.744,51 USD | 1.395,55 USD | 4.157,31 USD |

61 cửa sổ đủ 12 tháng, bắt đầu theo đầu tháng từ 01/2018 đến 01/2023.
Mốc là đỉnh lợi nhuận từ lệnh đóng 5.000 USD. Hai pha FTMO dùng
mục tiêu 10% và 5% với ít nhất 4 ngày mở lệnh mỗi pha. Daily Loss 5%
so equity theo ngày Prague và Overall Loss 10% tĩnh. FTMO không giới
hạn thời gian. Bảng sau chỉ đo nhịp tích lũy trên sổ cash.
[FTMO 2-Step](https://ftmo.com/en/2-step-challenge/) ·
[Trading Objectives](https://ftmo.com/en/trading-objectives/).

| Sổ cash 12 tháng | Cửa sổ có đỉnh +5.000 | Đỉnh tốt nhất | Thiếu trung vị |
| --- | ---: | ---: | ---: |
| US500 stop, phần có đường | 0/61 | 1.602,64 USD | 4.878,98 USD |
| US500, mỗi lệnh chưa rõ tính −125 USD | 0/61 | 1.405,87 USD | 4.953,01 USD |
| BASE PRIMARY | 0/61 | 2.284,39 USD | 4.464,55 USD |
| BASE STRICT | 0/61 | 1.576,55 USD | 4.669,20 USD |

### R120 trên đúng 11 lệnh cũ 2022–2023

Cả 11 giá vào và ra sổ stress khớp với cùng M1 Open và trượt 0,75
điểm mỗi phía. Tất cả thoát theo giờ trưa trong sổ. Đối chứng giữ
khối lượng và thời điểm rồi đổi hướng thành BUY. Phần cùng giờ ở
bảng dưới tính trước khi làm tròn tiền từng lệnh.

| Năm | Lệnh BUY / SELL | Net R120 đã lưu | Cùng hướng R120, cùng giờ | Luôn BUY cùng giờ | Chênh riêng do chọn hướng |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2022 | 3 / 6 | +2,81 USD | +2,80 USD | −87,44 USD | +90,24 USD |
| 2023 | 2 / 0 | +11,99 USD | +11,99 USD | +11,99 USD | 0,00 USD |
| Tổng | 5 / 6 | +14,80 USD | +14,79 USD | −75,45 USD | +90,24 USD |

Trên đúng 11 ngày đó, BUY gần trọn phiên với stop 1% cho **−521,65 USD**
ở sizer 125 USD, hoặc **−113,77 USD** khi giữ khối lượng R120. Phiên
cash BUY ở cả hai năm 2022–2023 cho **−1.611,35 USD** trên 490 đường
đủ. Chênh giữa giao dịch R120 và BUY cả phiên gồm thời gian giữ,
giờ vào, stop và sizing. Chỉ phép so cùng giờ/cùng khối lượng đo
riêng phần chọn hướng. Tín hiệu M15 đã giúp trong 6 lệnh SELL của
2022 trên mẫu này, nhưng 11 lệnh và 14,80 USD thực đo còn quá nhỏ
để thay đổi kết luận Challenge.

## Quyết định và khả năng tái lập

Dừng ở sổ cash vì lợi nhuận gộp thô hụt quy mô, net stop đã đo âm hai
cụm, độ phủ thấp và không có cửa sổ cash chạm mục tiêu. Không có replay
mới về Daily Loss, hai pha hoặc payout. Phạm vi kết luận là đúng luật
BUY, stop 1% và giờ đã khóa trong Development 2018–2023. Một cơ chế
khác muốn đi tiếp phải chứng minh được giá trị của thời điểm, hướng
hoặc cách thoát trên chính lịch và chi phí mà nó giao dịch.

Private evidence ở
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/prop-us500-cash-session-20261119/`.
Đã kiểm 1.926.201 M1 hai phía, hash proof theo năm, 61 cửa sổ, sổ R120
niêm phong và đối soát cent bằng Decimal. Kiểm độc lập phép tính trên
sổ đã phát hiện một lỗi làm tròn số thực đúng nửa cent. Đã chuyển sang
số nguyên millipoint × cent-lot, chạy lại cùng nguồn và giữ attempt
trước trong thư mục private. Kết luận và tổng sáu năm giữ nguyên.

| Bằng chứng | SHA256 |
| --- | --- |
| `registration.md` | `4ee529f80483d77cb4c8c751194e368c073b0e5750470b148d56e916bb0d65a8` |
| `endpoint-first.json` | `2b86e18e34bf99d2a49a7775605f2f0072dac071c38a7a9dbedb38ba66698ab9` |
| `detail.private.json.zst` | `a3ea06b081fcfcf6e50be97573624c62a407f6a83f5fe33833a3da7a385e7405` |
| `summary.json` | `c7463bc75de53617c127578f09181c0838f7e7cf51db0b579620949c9e68c54c` |

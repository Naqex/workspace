# US500 R094 · đóng 12:01 hay 15:59 New York?

**Gác bản thoát 15:59.** Giữ sang buổi chiều cải thiện sổ R094
**+808,98 USD năm 2022** và **+422,76 USD năm 2023** dưới phí stress,
nhưng tổng năm chỉ **+16,57R** và **−6,31R**. Cả hai vẫn cách xa quy mô
60R của một chiến lược tự gánh hai vòng. Năm 2023 còn phụ thuộc vào
vài tuần cải thiện mạnh. Giữ R094 12:01 làm đối chứng và kết thúc
pilot ở Development 2022–2023.

## Trần của việc chỉ lọc bớt lệnh R094

Xếp net USD từ cao xuống thấp trên đúng sổ stress cũ, giữ nguyên lot,
giá và giờ thoát. Đây là trần tính bằng hindsight đối với từng sổ đã
quan sát. Bỏ các đường giá thiếu thì kết quả chỉ áp cho phần còn lại.

| Năm / mẫu cũ | Top 144 | Top 192 | Số lệnh lớn nhất còn tổng ≥60R |
| --- | ---: | ---: | ---: |
| 2022, cả 231 lệnh mô hình | 70,8952R | 23,1608R | 154 |
| 2022, 230 lệnh có đường đủ | 67,5736R | 19,8320R | 151 |
| 2023, cả 222 lệnh mô hình | 54,6564R | 6,7728R | 138 |
| 2023, 219 lệnh có đường đủ | 50,8144R | 2,9260R | 134 |

Ngay cả chọn hậu nghiệm, 192 lệnh đều dưới 60R, và 144 lệnh không đạt
trong 2023. Kết quả chỉ giới hạn phương án chọn một tập con của sổ cũ.
[Luật và sổ R094](US500-M15-OPENING-SCREEN-RESULTS-20261111.md).

## Một thay đổi về payoff

A đóng lúc Open M1 12:01 New York. B dùng Open M1 15:59 trên đúng
phiên NYSE đủ 390 phút. Cùng lần đầu phá vùng 15 phút, chiều, giá
entry, lot bước 0,01, một vị thế, stop theo độ rộng vùng, phí
0,25/0,75 điểm mỗi chiều và 0 commission. Vốn danh nghĩa 10k, risk
25 USD. Những lệnh đã dừng trước khi A đóng theo giờ giữ nguyên.
Tại mốc thoát, stop ở giá Open có ưu tiên. Nếu Open chưa chạm stop,
đóng ở Open trước khi xét phần còn lại của nến đó. B dùng stop cũ cả
buổi chiều, không giữ qua đêm. Động lực nghiên cứu là kết quả liên hệ
giữa đầu và cuối phiên trên SPY của Gao và cộng sự. Ở đây đo điều
kiện riêng của R094 với nguồn CFD M1 Bid/Ask. [Nghiên cứu Gao và cộng sự](https://profiles.wustl.edu/en/publications/market-intraday-momentum/).

| Năm / phí | Lệnh A = B | A net USD | B net USD | B net R / ROI 10k | Thêm từ buổi chiều |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2022 chuẩn | 231 | −108,25 | +758,28 | +30,33R / +7,58% | +866,53 USD |
| 2022 stress | 231 | −394,62 | +414,36 | +16,57R / +4,14% | +808,98 USD |
| 2023 chuẩn | 222 | −106,31 | +356,73 | +14,27R / +3,57% | +463,04 USD |
| 2023 stress | 222 | −580,59 | −157,83 | −6,31R / −1,58% | +422,76 USD |

- **Giữ thêm có đổi payoff.** 141/123 lệnh còn mở khi A đóng theo giờ
  trong 2022/2023. Trong B, 46/42 chạm stop sau mốc Open 12:01 (kể cả
  diễn biến trong nến 12:01), còn 95/81 đến được 15:59. Trên các cặp
  có đường đủ, phần chiều tăng **852,68/413,49 USD stress**. Gộp sau
  spread của B, trước trượt, là **845,87/548,69 USD**. Trượt stress
  **432,12/707,03 USD**, đã tính cả hai chiều. Giá Bid/Ask đã chứa
  spread. PnL dùng giá thoát thực sự của mô hình, không dùng mức giá
  tốt nhất xuất hiện trong buổi chiều.
- **Kiểm riêng hướng giá.** Midpoint cuối phiên so với 12:01 đi cùng
  hướng breakout ở **85/140** và **69/121** cơ hội có endpoint và
  đoạn trước trưa đủ giá. Dịch chuyển có dấu bình quân **+0,98/+1,18
  điểm**. Tương quan giữa dịch chuyển entry→12:01 và 12:01→15:59
  sau khi nhân cùng dấu lần lượt **+0,147/−0,035**. Phép đo điểm cuối
  này bao gồm lệnh B đã chạm stop trước 15:59. Bảng PnL xét stop
  trên đường giữ lệnh.
- **Khi bỏ ba tuần tăng thêm nhiều nhất.** Delta stress của riêng năm
  2022 còn **+343,06 USD**. Năm 2023 còn **−5,20 USD**, hoặc
  **+5,70 USD** nếu chỉ xét các đường đủ. Ba tuần tốt nhất gộp hai
  năm đóng góp 512,63 USD trong 1.231,74 USD cải thiện mô hình.
  R094 B có **46/42 stop buổi chiều** cùng với các stop trước trưa.
  Cash DD stress đỉnh–đáy A→B là **536,33→377,77 USD** và
  **717,85→426,79 USD**. Đây là số dư lệnh đóng. Floating equity,
  giới hạn lỗ ngày và đường chuyển pha chưa được đo.

### Khoảng thiếu và quy mô còn lại

| Năm | A / B có đường chưa rõ | A / B stress, cùng phần đủ | B nếu mỗi đường chưa rõ là −25 USD | B nếu lấy tốt hơn giữa mô hình và stop thường cho phần thiếu | Thiếu để tới 60R theo B mô hình |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2022 | 1 / 3 | −514,10 / +338,58 USD | +263,58 USD | +414,36 USD | 43,43R / 1.085,64 USD |
| 2023 | 3 / 4 | −624,39 / −210,90 USD | −310,90 USD | −157,83 USD | 66,31R / 1.657,83 USD |

B thêm 2 đường thiếu năm 2022 và 1 đường thiếu năm 2023. Mọi lệnh
có giá đóng mô hình. Bằng chứng thiếu giá giữa lúc giữ khiến net
trọn năm chưa xác nhận. Hai cột gán tiền cho phần thiếu là kịch
bản có điều kiện, vì gap có thể làm giá khớp xấu hơn stop thường.
Muốn đạt 60R, phần thiếu phải đóng góp bình quân **387,14/427,73
USD mỗi lệnh**. Mean net stress của B chỉ **+0,072/−0,028R/lệnh**
ở 231/222 fill. Bảng 10k chưa có kết quả lot/fill 25k. Phần chiều
thêm tiền nhưng chưa đủ quy mô và chưa lặp được lợi nhuận stress
qua hai năm. Gác B trước khi mở thêm 2018–2021 hoặc replay tài khoản.
[Phép tính quy mô 12 tháng](PROP-US500-12M-VIABILITY-20261119.md).

## Bằng chứng

- Card khóa trước khi đọc giá chiều. Dùng 194.730 phút Bid/Ask trong
  các phiên cash 2022–2023 đã niêm phong, không đọc giá năm 2024+.
  A khớp toàn bộ trường lưu của R094, ngoài timer. Tái kiểm B bằng
  runner chung với đúng một thay đổi lịch thoát, khớp 906 dòng về
  entry, side, stop, lot, giá thoát, lý do, gap và tiền từng lệnh.
  Fixture kiểm BUY/SELL và thứ tự stop tại Open trước mốc thoát.
- Job `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/prop-us500-r094-afternoon-20261119/`.
  Phép đo 23,08 giây gồm đọc nguồn, tái lập A, B và ghi JSON/Zstandard.
  SHA256 card `7744538b9ed066faaec8834958669f04ab43c255d8a9b38f86387ca9080af089`.
  SHA256 manifest `b08cb2b4642efc84dbd03d6c3497bd05b2cb1b1332374bb04ba7a43b5a73fb04`.
  SHA256 verifier receipt `984a69c5cf717de00b2bb50731ad83ffc49c71a16116295102c0e9063c7b3f2d`.

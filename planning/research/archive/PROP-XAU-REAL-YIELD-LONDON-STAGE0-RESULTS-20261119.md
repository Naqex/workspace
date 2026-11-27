# XAUUSD · cú sốc lợi suất thực Mỹ 10 năm và phiên London kế tiếp

**Dừng ở Stage-0 — `ECONOMIC_FAIL`, `PROP_UNMEASURED`.** Cả 454 tín hiệu
có giá vào/ra, giữ được 100% qua cổng chi phí và có 70–86 cơ hội mỗi năm.
Tuy vậy, markout stress chỉ dương năm 2020 và 2021. Với quy đổi khối lượng
theo ngân sách 125 USD trên sổ tham chiếu 50.000 USD, tổng net là
**−222,40 USD phí chuẩn và −721,60 USD phí stress**. Cả hai cụm Development
đều âm. Cấu hình đã khóa dừng trước mô phỏng chạm stop, tài khoản 10k/25k
và payout. Quyết định danh mục vẫn là `BASE_GUARD · NOT_QUALIFIED`.

## Câu hỏi và quy tắc đã khóa

Sau khi Treasury công bố thay đổi mạnh trong lợi suất thực 10 năm, giá vàng
có còn đi đủ xa theo hướng kỳ vọng ở phiên London kế tiếp để bù chi phí?
Dùng chuỗi **10-year Treasury par real yield** từ đường cong TIPS,
chuyển phần trăm sang điểm cơ bản (0,01 điểm phần trăm = 1 bp). Sáu XML
theo năm 2018–2023 trả 249 / 250 / 251 / 251 / 249 / 250 quan sát.
Treasury đổi phương pháp nội suy vào 06/12/2021. Cùng một luật được dùng
cho toàn kỳ. [Treasury XML feed](https://home.treasury.gov/treasury-daily-interest-rate-xml-feed) ·
[Chuỗi lợi suất thực và mốc đổi phương pháp](https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?type=daily_treasury_real_yield_curve).

- Lấy chênh lệch giữa hai quan sát kế tiếp. Khi độ lớn thay đổi đạt ít nhất
  một độ lệch chuẩn mẫu của **20 thay đổi trước đó**, lợi suất giảm → BUY
  vàng, lợi suất tăng → SELL. Cửa sổ chỉ lấy quá khứ và không điền ngày thiếu.
  Trong 1.500 quan sát có 21 mốc khởi tạo, 1.014 dưới ngưỡng và 465 cú sốc.
- Vào 08:00, thoát 15:55 giờ London ở ngày giao dịch XLON kế tiếp, có xét
  DST và lịch chặn giao dịch vàng V8. Nếu nhiều quan sát trỏ vào cùng phiên,
  quan sát mới nhất quyết định, kể cả khi nó dưới ngưỡng. Luật này loại
  11 cú sốc trùng lịch, còn 454 phiên. XLON cung cấp ngày phiên. Mốc thoát
  kiểm bằng báo giá XAUUSD và lịch V8.
- Treasury mô tả báo giá tham chiếu quanh 15:30 New York và dữ liệu thường
  có vào 18:00, đôi lúc trễ. Bài đo dùng **18:00 New York** làm giả định
  thời điểm biết. XML lịch sử thiếu giờ đăng từng dòng và bản giá trị lần
  công bố đầu, nên 454 là số cơ hội **có điều kiện**, số thực thi được theo
  thời điểm công bố thật còn chưa xác minh. [Phương pháp Treasury](https://home.treasury.gov/policy-issues/financing-the-government/interest-rate-statistics/treasury-yield-curve-methodology).

### Giá, chi phí và khối lượng

Lấy Open M1 đúng hai mốc từ Bid XAUUSD đã khóa của V14, với Ask mô hình
= Bid + 0,338 USD/oz. BUY vào Ask và ra Bid, SELL vào Bid và ra Ask.
Commission 0,0007% giá trị mỗi phía. Chuẩn dùng 0 slippage, stress dùng
0,20 USD/oz mỗi phía. Đóng cùng ngày nên swap bằng 0. Có **454/454 cặp
giá**, 449/454 phiên đủ nến giữa hai đầu mốc. Năm phiên thiếu tổng cộng
5/216.104 phút, giữ nguyên khoảng trống. Markout chỉ dùng hai đầu mốc.

Khoảng stop tham chiếu là 2× Wilder ATR20 của nến D1 UTC đủ ít nhất
20 giờ H1 hoàn chỉnh, đã đóng khi vào. Dùng khoảng này để kiểm quy mô và
quy đổi khối lượng theo bước 1 oz (0,01 lot, 100 oz/lot), trần 125 USD
lỗ dự kiến theo mô hình stop và phí. Khối lượng thực tế của phép quy đổi
là 1–5 oz, trung vị 2 oz. Khoảng stop nằm trong quy đổi risk, giá thoát
của phép đo luôn ở 15:55. [Tiền lệ ATR20 và lịch London](PROP-XAU-SHANGHAI-PREMIUM-PREFLIGHT-20261119.md) ·
[Cổng Stage-0](../../.agents/skills/strategy-qualification/references/validation-gates.md#stage-0-unconditional-markout--scale-screen).

## Kết quả theo năm

Ba cột markout là **bình quân USD/oz mỗi tín hiệu**. Hai cột cuối là
**tổng USD với khối lượng đã làm tròn theo lot**.

| Năm | Tín hiệu (BUY / SELL) | Gộp midpoint | Sau spread | Net stress | Tổng USD chuẩn | Tổng USD stress |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2018 | 86 (38 / 48) | −0,9657 | −1,3037 | −1,7214 | −525,77 | −682,97 |
| 2019 | 70 (38 / 32) | −0,2311 | −0,5691 | −0,9886 | −138,21 | −238,61 |
| 2020 | 75 (41 / 34) | +5,0391 | +4,7011 | +4,2763 | +605,77 | +550,97 |
| 2021 | 72 (37 / 35) | +2,6314 | +2,2934 | +1,8681 | +371,90 | +314,70 |
| 2022 | 73 (25 / 48) | −0,4053 | −0,7433 | −1,1686 | −111,34 | −172,94 |
| 2023 | 78 (36 / 42) | −2,0719 | −2,4099 | −2,8370 | −424,75 | −492,75 |
| 2018–2023 | **454 (215 / 239)** | **+0,6101** | **+0,2721** | **−0,1511** | **−222,40** | **−721,60** |

Stop trung vị theo năm là 24,23–57,16 USD/oz. Tỷ lệ phí stress kế hoạch
trung vị trên stop trung vị là 1,33–3,12% theo năm, dưới cổng 12%.
Phí stress bình quân toàn kỳ khoảng 0,761 USD/oz. Hai chiều đều âm
trên toàn kỳ sau quy đổi, BUY **−576,93 USD**, SELL **−144,67 USD**.
Bốn năm đã âm ngay trước spread. Phí stress cũng lớn hơn phần gộp bình
quân khi tính chung 454 tín hiệu.

### Độ bền và đối chứng

| Cụm | Tín hiệu | Net stress USD | USD/năm (mục tiêu ≥ 1.000) | Bỏ 3 tuần lãi nhất | Luôn BUY cùng phiên/khối lượng | Đảo chiều ngẫu nhiên, trung vị [P05, P95] |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2018–2020 | 231 | −370,61 | −123,54 | −880,81 | −1.325,46 | −617,94 [−1.392,04, +168,37] |
| 2021–2023 | 223 | −350,99 | −117,00 | −657,16 | −84,23 | −370,97 [−1.064,69, +264,93] |

Trong 1.000 hoán vị chiều mỗi cụm, giữ cùng ngày, khối lượng và số BUY/SELL,
kết quả thật bằng hoặc cao hơn 701/1.000 và 524/1.000 lượt. Đây là đối chứng
mô tả. Ba tuần đóng góp cao nhất ở cụm đầu là 2020-W46 (+214,72),
2020-W11 (+208,78), 2020-W13 (+86,70) USD. Cụm sau là 2021-W31
(+126,16), 2022-W24 (+98,61), 2022-W20 (+81,40) USD. Khi bỏ ba tuần
lãi nhất toàn kỳ (2020-W46, 2020-W11, 2021-W31), còn −1.271,26 USD.

## Đồng biến theo thời điểm và giới hạn kết luận

Phép đối chiếu hồi cứu có giá ở 459/465 cú sốc. Từ khoảng 15:30 New York
ngày quan sát trước đến 15:30 ngày quan sát hiện tại, tương quan giữa
thay đổi lợi suất và thay đổi giá vàng là **−0,552**, và biến động vàng gộp theo
chiều tín hiệu là **+10,03 USD/oz**. Khoảng đo này trùng với khoảng
hình thành cú sốc. PnL của luật giao dịch chỉ đo từ 08:00 London hôm sau
và âm dưới stress. Kết quả xác định giới hạn của cửa sổ London đã đăng ký.
Thời điểm thị trường hấp thụ toàn bộ thông tin chưa được đo.
[Chicago Fed, mối liên hệ theo ngày](https://www.chicagofed.org/publications/chicago-fed-letter/2021/464).

Nguồn Treasury có thể dùng cho một phép quan sát tiến về trước nếu có
nghiên cứu cần nó. Khi đó lưu thời điểm thấy dòng lần đầu, bản XML và hash
của mỗi lần quan sát để phân biệt bản công bố đầu với bản sửa đổi. Hậu kiểm
này dừng ở việc lưu kết quả lịch sử, không chạy biến thể/đổi cửa sổ sau khi
biết kết quả.

## Bằng chứng và đối soát

- Parent `5bd99d3`. Dữ liệu giá đọc cho Development 2018–2023, 2.124.715
  hàng M1, không dùng giá từ 2024 trở đi. Đây là nghiên cứu Stage-0 độc lập
  với các sổ Challenge/Reward đã lưu.
- Thư mục đối soát `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/prop-xau-real-yield-london-20261119/`.
  Giữ card khóa trước khi đo, sáu XML, `yield-input.json`, `stage0.py`,
  `summary.json` và `rows.json.zst`.
- SHA256 card `a77fc3d56907fc03febac96717a4f736debeb7c1f60fb6c804b25ecd50f4dddc`.
  SHA256 manifest `972813420cba3abb4239aa2ec2dd094cfde3e0eb7179f2eaec928077efa294db`.
  Đối soát 4 đầu ra, 12 đầu vào, 1.500 quyết định tín hiệu, 908 trường hợp
  giá và phí BUY/SELL, tổng USD từng năm và giờ dân sự cho 454 phiên.

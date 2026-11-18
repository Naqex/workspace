# AUD/USD 01:20–02:00 UTC | Dư địa sau phí quanh fixing CFETS

19/11/2026 · **Hạ ưu tiên thu thêm nguồn fixing và USD/CNH.** Chỉ
21/79 ngày có ít nhất một chiều đạt trần phí. Trong hai tháng năm
2019, ngay cả khi biết trước ngày và chiều có lợi, phần đo được chỉ
còn +45,93 USD (+0,306R). `CFETS → AUD/USD` vẫn
`DATA_PATH_INCOMPLETE`. BASE_GUARD vẫn `NOT_QUALIFIED`.
[Kiểm tra nguồn của phép thử gốc](PROP-CFETS-AUD-SOURCE-PREFLIGHT-20261119.md).

## Mẫu và kiểm tra đồng hồ

Khóa mẫu trước khi tính kết quả. Chọn tháng 4 và 11 của năm giữa
mỗi cụm Development, 2019 và 2022. Hai tháng đại diện các giai đoạn
giờ mùa hè khác nhau. Chỉ nhận ngày thứ Hai đến thứ Sáu có bản ghi
fixing USD/CNY trong truy vấn CFETS giới hạn theo tháng. Loại ngày
mùng 1 đồng nhất để tránh cần ZIP tháng trước khi đổi ngày UTC.
Lấy ngày từ bản lưu CFETS. Giờ công bố thực tế vẫn chưa xác minh.
[Kho CFETS](https://www.chinamoney.com.cn/english/bmkcpr/index.html?tab=2).

Tải một ZIP Bid/Ask HistData qua biểu mẫu công khai, đối chiếu được
hai ngày mẫu rồi mới tải ba ZIP còn lại. 24 truy vấn tới kho tick
Dukascopy trực tiếp, dùng riêng để neo giờ, trả HTTP 503. Đối chiếu
thay thế dùng nến Bid/Ask H1 UTC đã niêm phong. Ở cả tám ngày neo cố
định, một độ dịch duy nhất khớp đúng cả tám trường OHLC ở cả ba mốc
00:00, 01:00 và 02:00 UTC.

Trước khi tính tiền, bổ sung kiểm từng ngày để tránh áp một độ dịch
qua tuần đổi giờ. Cả 79 ngày đều có một độ dịch duy nhất khớp ít nhất
hai trong ba giờ. So với cách đọc UTC−5 trong tài liệu HistData, cả
hai tháng 4 cần lùi một giờ và cả hai tháng 11 giữ nguyên, kể cả ngày
mẫu đầu tháng 11/2022. Bằng chứng áp dụng cho các ngày đã so trên
AUD/USD. Nến UTC được đọc từ cache riêng. Hai kho vẫn có thể dùng chung
nguồn báo giá thị trường.
[Đặc tả HistData](https://www.histdata.com/f-a-q/data-files-detailed-specification/).

Hai ngày bị loại khỏi phần tính tiền nhưng giữ trong mẫu số.
19/04/2019 thiếu tick phút 00:44 UTC. 15/04/2022 thiếu tick ở
00:10, 00:30, 00:31 và 01:28 UTC. Các cửa sổ dùng để dựng stop và
kiểm đường giữ lệnh yêu cầu ít nhất một báo giá mỗi phút.

## Kinh tế của cùng một cửa sổ

Vào tại tick đầu trong phút 01:20 UTC. Trước 01:14, lấy đáy Bid
hoặc đỉnh Ask và đệm 1 pip để đặt SL tự nhiên. Thoát tại báo giá
khớp SL đầu tiên hoặc tick đầu trong phút 02:00. Sử dụng đúng Ask
khi mua và Bid khi bán. Phí stress thêm 9 USD/lot/vòng. Cổng phí
tại entry lấy spread quan sát lúc vào cộng 0,9 pip rồi chia cho
khoảng cách từ giá vào đến SL, trần 12%. Chênh giá thực tế được tính
một lần qua Bid/Ask. Sử dụng 150 USD cho 1R với lot tính liên tục.

Đối chứng chọn hướng từ biến động mid AUD/USD trong khoảng 00:00
đến trước 01:14. Bỏ qua ngày hòa hoặc chiều dự báo trượt cổng phí.
Cận biết trước chọn chiều lãi cao nhất sau khi nhìn giá, và được
đứng ngoài nếu cả hai chiều đều lỗ hoặc bị loại. Bảng giữ thêm
kịch bản phải vào mỗi ngày có chiều hợp lệ.

| Mẫu | Có đủ giá | Qua ≥1 chiều | Qua cả hai chiều | Biết trước, được bỏ ngày lỗ | Biết trước, phải vào nếu đủ phí | Đối chứng trước tin |
|---|---:|---:|---:|---:|---:|---:|
| 04/2019 | 19/20 | 4/20 (20,0%) | 0 | +0,263R / +39,49 USD | −0,229R / −34,35 USD | −0,316R / −47,39 USD (3 lệnh) |
| 11/2019 | 20/20 | 4/20 (20,0%) | 0 | +0,043R / +6,44 USD | −0,771R / −115,64 USD | −0,771R / −115,64 USD (4 lệnh) |
| **2019 (hai tháng)** | **39/40** | **8/40 (20,0%)** | **0/40** | **+0,306R / +45,93 USD** | **−1,000R / −149,99 USD** | **−1,087R / −163,03 USD (7 lệnh)** |
| 04/2022 | 17/18 | 6/18 (33,3%) | 0 | +1,078R / +161,75 USD | −1,444R / −216,59 USD | −0,753R / −112,98 USD (4 lệnh) |
| 11/2022 | 21/21 | 7/21 (33,3%) | 0 | +1,114R / +167,03 USD | −0,342R / −51,30 USD | −0,342R / −51,30 USD (7 lệnh) |
| **2022 (hai tháng)** | **38/39** | **13/39 (33,3%)** | **0/39** | **+2,192R / +328,78 USD** | **−1,786R / −267,89 USD** | **−1,095R / −164,28 USD (11 lệnh)** |

Ở các ngày đủ giá, tổng số chiều qua cổng là 6 BUY và 15 SELL.
Có 2 lệnh chạm SL và 19 lệnh thoát theo giờ. SL trung vị trong
các chiều có SL hợp lệ là 5,75 / 9,30 pip (BUY / SELL) ở hai tháng
2019 và 11,25 / 12,60 pip ở hai tháng 2022. Ma sát thực hiện trung
vị giữa hai đầu của nhóm qua cổng là 1,75 / 1,85 pip ở 2019 và
2,05 / 2,375 pip ở 2022. Có 2/21 lệnh vượt 12% khi tính lại ma sát
thực hiện với spread lúc thoát. Cổng trước khi vào giữ theo thông
tin biết tại entry. Toàn bộ tiền trong bảng đã tính theo spread
thực hiện và stress, kể cả hai lệnh này.

Cận cho phép bỏ ngày lỗ hơn đối chứng **1,393R / 208,96 USD**
trong mẫu 2019 và **3,287R / 493,07 USD** trong mẫu 2022. Đối
chứng tự nó âm ở cả hai nên chưa chiếm phần dương của cận. Chênh
lệch là khoảng cách từ đối chứng đến lựa chọn biết trước, và chưa
quy cho fixing.

## Quyết định và phạm vi

Cả hai mẫu hụt ngưỡng 50% cơ hội, ngay cả nếu mỗi ngày thiếu giá
đều qua cổng (tối đa 9/40 và 14/39). Mẫu 2019 có +45,93 USD cận
quan sát so với mốc nghiên cứu hai tháng +166,67 USD. Mẫu 2022
có dư địa +328,78 USD nhờ được chọn lại ngày có lợi. Mốc hai tháng
dùng để quyết định công tìm dữ liệu. Bốn tháng này chưa cho phép
suy lợi nhuận hằng năm hoặc cận của cả giai đoạn 2018–2023.

Gác tìm thêm giờ công bố từng ngày và dữ liệu USD/CNH cho nhánh
này. Chưa chạy phép thử tín hiệu CFETS, và kết quả chỉ ràng buộc
các ngày, feed, clock, SL và phí đã đo. Giá 2024–2026 vẫn đóng.
Chưa kiểm khả năng khớp theo biểu phí, lot và điều kiện của tài
khoản quỹ.

Bằng chứng riêng tại `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/prop-aud-fixing-window-20261119/`.
Bốn receipt nguồn giữ hash ZIP, `daily-clock.json` giữ từng điểm
đối chiếu UTC, `pilot-results.json.zst` giữ từng ngày và từng chiều.

| File | SHA256 |
|---|---|
| `registration.md` | `e42a58cf79c602efbd17134bd93cd2cfcd1358b2f21da30e1dc2679e7940b011` |
| `utc-addendum.md` | `3c416e4823eb4d70bb6704ec6f819286ec50b59206b20ee381b955e178358470` |
| `daily-clock.json` | `eed0524b1b714ef941a3fd033c2e47d211e0b18872ea22084c493a76585d620c` |
| `pilot-results.json.zst` | `0b31bd15a0487a1fa13e23bd408599881f0e75dddaf2cb1c7870ee44c0813abb` |

Kiểm lại bằng bộ tính NumPy riêng trên 79 dòng lịch, gồm điều kiện
phút, hai phía Bid/Ask, thứ tự chạm SL, phí và tổng R theo nhóm.
Kết quả khớp phép đo chính.

# EURUSD H1 · gộp sáu mẫu nến RSI37 và kiểm luật thoát

**Gác cấu hình gộp.** Cơ chế thoát theo source làm kết quả kém hơn phép
đo +8 giờ trên cùng 433 cơ hội có đủ hai mức giá thoát. Khi chỉ cho
phép một vị thế tại một thời điểm, cơ chế thoát mới vẫn âm cả hai cụm
2018–2020 và 2021–2023 dưới phí stress. Chưa thấy bằng chứng bộ lọc +8
giờ đã gác nhầm một cấu hình khả thi trong trường hợp này.
`ECONOMIC_FAIL` · `DATA_PATH_INCOMPLETE` · `PROP_UNMEASURED`.
[Audit sàng lọc trước đó](PROP-SCREEN-MISS-AUDIT-20261119.md).

## Tín hiệu và cách đo

Giữ đủ sáu file EA ở rank 1–6, RSI37 trên giá đóng. Đã đối chiếu hash
từng file. Tái lập đúng số tín hiệu **85 Engulfing, 219 Harami, 111
Hammer, 2 BlackCrows, 0 MeetingLines, 38 StarDoji**. Rank 1 khớp giờ,
chiều, hạn và trạng thái định giá từng dòng với V25. Rank 2–6 khớp
số tín hiệu, số định giá được và markout bình quân từng năm với V26.
Hồ sơ V26 của rank 2–6 chỉ lưu thống kê, nên không đối chiếu định
danh từng dòng với sổ cũ.
[Card V26](CORPUS-BATCH-V26-CARD-20261118.json) ·
[Card V25](CORPUS-ENGULFING-RSI-CARD-20261118.md).

Gộp 9 bản sao cùng giờ/cùng chiều, còn **446 cơ hội trên 325 ngày**,
không có xung đột hai chiều. Rank nhỏ nhất sở hữu vị thế. Cả sáu source
có cùng quy tắc RSI qua 30/70 với điều kiện loại tín hiệu đóng nếu mẫu
sở hữu đang báo vào. Xử lý SL/TP trước khi xét lệnh mới tại báo giá
chạm mức. Khi đóng theo RSI, thời hạn hoặc lịch, vị thế có sẵn chặn
entry cùng báo giá theo thứ tự xử lý MQL. Sổ chỉ giữ một vị thế.

Dùng quy đổi V26, **200 point = 20 pip** cho hai mức SL/TP tính từ
giá vào, với sàn spread có sẵn trong source. Thời hạn là 10 mốc H1 đầy
đủ sau quyết định, chặn bằng lịch cũ và 48 giờ. Native `BarsHold`
dùng `CopyRates` theo đồng hồ MT5, vì vậy phép đếm 10 H1 của benchmark
chưa đối soát với terminal. Nguồn cũng mặc định **0,1 lot**. Pilot
tính kích thước floored theo bước 0,01 lot, ngân sách stop tối đa
**150 USD** gồm phí và swap dự kiến đến hạn đã biết. Stress **9
USD/lot** gồm commission và trượt giá, kể cả TP. Giữ swap mô hình
−40 USD/lot khi qua rollover 22h UTC, thứ Tư nhân ba. Bid/Ask đã tính
spread. Cổng phí là (spread + 9 point) chia khoảng stop ≤12%.
Lệnh stop trên tick khớp tại báo giá quan sát đầu tiên chạm/vượt mức,
TP ghi tại mức đặt và vẫn chịu trượt giá kế toán stress.

Tín hiệu giữ nguyên từ Bid H1 của derivative V14 đã khóa, dùng seed
2017 có sẵn. Dựng lại từ Bid native cho kết quả **454/455** danh tính
giống nhau, thiếu duy nhất Engulfing BUY 31/08/2018 20:00 UTC. Giữ
tín hiệu đó trong roster khóa trước. Định giá chính dùng Bid/Ask tick
thật năm 2018–2023. Đối chứng riêng dùng M1 legacy và Ask proxy 1 pip,
với hai thứ tự OHLC. Mỗi sổ dùng nhất quán một nguồn giá khớp.

## Kết quả theo năm và theo cụm

Theo phép sàng lọc cũ trên roster gộp, số tín hiệu thô đạt 40 mỗi
năm, trung vị tỷ lệ phí/stop **9,5%** và tỷ lệ giữ theo phí vượt 50%.
Mean net +8 giờ trên M1 legacy sau stress theo năm lần lượt
**+0,43, −0,44, −8,51, −7,12, −8,18, +4,53 pip**, so với phí dự
kiến 1,90 pip. Có ba mốc thiếu giá vào hoặc giá thoát. Cổng Stage-0
cũ vẫn trượt. Probe này đã đo luật thoát dù +8 giờ trượt để trả lời
câu hỏi về khả năng bỏ sót.

| Năm | Cơ hội / số ngày | Cặp cùng timestamp và lot | +8h net trên cùng cặp | Source exit net trên cùng cặp | Sổ một vị thế · source exit lệnh / net |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2018 | 96 / 70 | 93 | +1.386,45 USD | −195,85 USD | 83 / −333,99 USD |
| 2019 | 76 / 58 | 72 | +364,47 USD | −288,25 USD | 60 / +25,18 USD |
| 2020 | 75 / 50 | 73 | −3.790,78 USD | −723,02 USD | 65 / −401,47 USD |
| 2021 | 62 / 45 | 60 | −2.303,81 USD | −3.431,79 USD | 50 / −2.573,62 USD |
| 2022 | 68 / 49 | 67 | −3.236,48 USD | −3.016,48 USD | 63 / −2.906,54 USD |
| 2023 | 69 / 53 | 68 | +2.961,98 USD | +305,54 USD | 65 / +470,56 USD |
| **Tổng** | **446 / 325** | **433** | **−4.618,17 USD** | **−7.349,85 USD** | **386 / −5.719,88 USD** |

Hai cột cùng cặp cho phép cơ hội chồng lấn để đo riêng hiệu ứng giá
thoát. Sổ một vị thế là kịch bản liên tục có một lần thoát muộn ở
2019, giải thích bên dưới. Trên 433 cặp, net mean/median của source
exit là **−0,114R / −0,240R** so với **−0,072R / −0,064R** ở +8 giờ.
Chỉ giữ 321 cặp có đủ phút quan sát ở cả hai đường vẫn âm
**−4.863,25 USD** theo source exit và **−880,48 USD** ở +8h.
Không suy từ độ đầy đủ theo phút thành bảo đảm mọi tick đã được lưu.

| Cụm | Lệnh source exit · số nhận / số dương | Net / net R | USD/năm | Bỏ ba tuần tốt nhất | Mục tiêu 1.000 USD/năm cần mỗi lệnh |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2018–2020 | 208 / 101 | −710,28 USD / −4,77R | −236,76 | −1.523,94 USD | +14,42 USD / +0,096R |
| 2021–2023 | 178 / 74 | −5.009,60 USD / −33,73R | −1.669,87 | −5.912,79 USD | +16,85 USD / +0,112R |

Sổ source exit tick có **−0,100R/lệnh**, median **−0,234R**,
p05/p95 **−1,012R / +0,914R**. Kết quả 386 lệnh gồm 152 SL, 150 TP,
61 hết 10 H1, 5 RSI, 17 đóng lịch và một đóng muộn theo kịch bản.
Gross sau spread −583,16 USD, commission và trượt 2.232,72 USD, swap
2.904,00 USD. Các tổng là phiên bản tham chiếu theo risk từng lệnh,
chưa có máy mô phỏng tài khoản.

Trong hai sổ một vị thế, +8h nhận **344 lệnh, −3.230,75 USD**,
chặn 90 do overlap. Source exit nhận **386 lệnh, −5.719,88 USD**,
chặn 48. Có **334 lệnh chung**, thay giá thoát làm giảm **3.236,32
USD**. 52 lệnh chỉ xuất hiện ở source exit thêm **398,64 USD**,
10 lệnh chỉ xuất hiện ở +8h lỗ **348,55 USD**. Hiệu ứng thay thành
phần lệnh bù **747,19 USD**, thua phần giảm từ giá thoát. Kịch bản
M1 OHLC và OLHC cho cùng kết quả kinh tế, với **395 lệnh /
−6.715,84 USD** cho source exit và **353 lệnh / −4.777,96 USD** ở
+8 giờ. Hai thứ tự đều âm cả hai cụm. Không có nến giữ lệnh chạm
đồng thời hai mức trên lát proxy này.

## Độ phủ, ngoại lệ cuối tuần và kiểm chứng

- Tick native có 444/446 mốc vào định giá được (**99,6%**), loại 10
  theo phí. Trong 434 mốc đủ điều kiện, 433 (**99,8%**) có cả hai giá
  thoát đúng hạn. Hai mốc thiếu entry là 02/03/2018 và 26/02/2021
  cùng 22h UTC. Một lệnh SELL 27/12/2019 21h UTC đã vào sau mốc
  hard-flat thứ Sáu cũ. Lịch kế thừa lấy mốc đóng kế tiếp nên lệnh
  đi vào giờ cuối tuần. Hạn +8h và hạn 48h đều không có báo giá hợp
  lệ trong 60 giây. Đây là một giới hạn thực thi của lịch đã khóa.
- Bản đọc lát tick ban đầu thiếu báo giá mở cửa lại, nên giữ sổ liên
  tục ở trạng thái chưa biết sau lệnh đó. Kiểm lại cùng raw CSV cho
  thấy báo giá đầu sau cả hai hạn vào **29/12/2019 22:03:26,782 UTC**.
  Giữ kết quả đúng hạn là unknown. Sổ liên tục trong bảng giả định
  đóng tại báo giá đầu quan sát được với **−65,40 USD** trên tick
  hoặc **−21,00 USD** trên M1 proxy. Một bước đóng muộn chỉ để
  thấy kết quả năm sau khi sổ có thể giao dịch lại. Loại riêng
  khoản −65,40 USD khỏi tổng của cụm đầu vẫn âm **−644,88 USD**.
  Kết quả ghép đúng hạn độc lập với giả định khôi phục này.
- 77/433 đường source exit tick ghép cặp (**17,8%**) có ít nhất một
  phút thiếu tick, 111/433 ở +8h. Trên phần định giá đúng hạn, bộ
  kiểm gap loại giờ nghỉ thường lệ và không tìm thấy gap bất thường
  trên 15 phút khi đang giữ lệnh. Ca cuối tuần nằm ngoài phần đó.
  Chưa kiểm điều kiện MT5, margin, tài khoản quỹ hay khả năng nhận
  Reward.

Ràng buộc SHA-256 cho card, sáu source, bản M1 và sáu CSV năm. Chỉ đọc
các lát 2018–2023 cần thiết, **18.214.865 tick**. Lượt chính mất **59,33
giây**. Đối chiếu tiền đến cent, thứ tự SL/TP trên fixture, lot và số
trường hợp nhận/chặn. Dữ liệu ngoài Development, remote và hệ thống
Trader không tham gia phép đo. Không kích hoạt sổ 10k/25k vì âm cả
hai cụm và thiếu đường giá đầy đủ. Không suy tỷ lệ bỏ sót của toàn
framework từ một cấu hình gộp hậu chọn.

Private receipt tại
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/prop-eurusd-rsi37-pool-20261119/`.
Khóa protocol SHA-256 `aa7ba9cc22aa4f6e69fd849173a5b9d74228131ea2383372da5c47fedab43743`.
Tổng hợp chính `a5d327376ca93da13b9b6514dc39d956c8d7a84395b2dada09438612dfbf4ba8`.
Đối soát và sổ liên tục thoát muộn `8a6bd334c5b6b47ee685770238ea906cb1950acaecabc652c5ff58187a33b73e`.

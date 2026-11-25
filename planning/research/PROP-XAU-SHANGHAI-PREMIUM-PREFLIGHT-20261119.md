# XAUUSD · chênh lệch Thượng Hải–London có đáng thành một nhánh giao dịch?

**Gác ở bước kiểm nguồn và tần suất.** Dựng được proxy trên 1.181/1.182
ngày giao nhau giai đoạn 2018–2022. Chuỗi năm 2023 còn thiếu SHAU PM
theo tháng. Một vị thế giữ đủ 10 phiên cho 3–23 lượt theo lịch mỗi năm
trong năm năm đã đo. Chưa tính lợi nhuận, chưa có ứng viên mới và
`BASE_GUARD` vẫn `NOT_QUALIFIED`.

## Luật đã khóa

- Metals Focus thử hai ngưỡng +1% và −0,2% trên lịch sử đến 2015. Tương
  quan đơn biến ở độ trễ một ngày rất nhỏ và thiếu ý nghĩa thống kê.
  Kết quả có kiểm soát USD chỉ cho cơ sở đặt giả thuyết. Lượt này chuyển
  sang SHAU PM sau 2016 với ngưỡng gốc, BUY từ +1%, SELL từ −0,2% trở
  xuống. Chỉ xét một luật, ưu tiên xác minh nguồn trước khi tính return.
  [Metals Focus trên LBMA](https://www.lbma.org.uk/alchemist/issue-83/links-between-the-chinese-and-international-gold-prices).
- Proxy lấy giá **SHAU PM theo CNY/gram**, nhân 31,1034768 gram/troy oz,
  chia tỷ giá **CNY/USD** theo đơn vị CNY trên một USD, rồi so với
  XAUUSD midpoint Open M1 tại 10:00 giờ London. FX là USD/CNY nội địa
  CFETS lúc đồng thời, **17:00 Thượng Hải khi London dùng BST** và
  **18:00 khi London dùng GMT**. CFETS lấy giao dịch liên ngân hàng
  trong 30 giây ngay trước mốc hoặc dùng báo giá khi thiếu giao dịch.
  [Phương pháp CFETS](https://www.chinamoney.com.cn/english/hombtbrrthdt/) ·
  [Giờ công bố tại SAFE](https://www.safe.gov.cn/en/2015/1230/1179.html).
- Chỉ vào lúc 10:00 London của phiên chung kế tiếp, sau ngày xác lập
  dữ liệu. Giữ tối đa một vị thế, hết cửa sổ sau 10 phiên chung tại cùng
  giờ. Bản chọn trước cho bước PnL dùng stop 2×ATR20 ngày đã đóng,
  risk all-in 125 USD/50k, ma sát thực thi trần 12%, lot làm tròn xuống.
  Nếu tới bước đo, dùng phí vàng tham chiếu trong repo gồm commission
  0,0007% mỗi phía, trượt 0,20 USD/oz mỗi phía, swap SYM −40/−40 hoặc
  ASYM −45/−5 USD/lot mỗi đơn vị rollover và thứ Tư nhân ba.
  Các thông số này là kịch bản mô phỏng. Chưa xác minh biểu phí hoặc
  khả năng hold qua cuối tuần ở tài khoản đích.
  [Mô hình swap V19](ASYMMETRIC-RECOVERY-V19-PROTOCOL-20261116.md).

Không thấy phép thử trùng đúng cơ chế này trong chỉ mục và code
research. Lượt CFETS trước đo tác động fixing lên AUD/USD, với một
mốc giờ, tỷ giá và kết quả khác. [Kiểm nguồn CFETS trước đó](PROP-CFETS-AUD-SOURCE-PREFLIGHT-20261119.md).

## Kiểm nguồn và giờ khả dụng

1. **SGE.** Có giá SHAU PM cả 8/8 ngày pilot 2019/2022 ở bảng chính thức,
   khớp với lượt cuối trong bảng tiếng Trung của bản tin ngày. Hai
   bản tin 12/01/2022 và 12/10/2022 ghi sai nhãn tiếng Anh của bảng
   buổi chiều thành Session 1. Đã kiểm lại đúng cột PM lần lượt
   373,60 và 392,63 CNY/g. Phiên PM bắt đầu 14:15 Thượng Hải,
   giá hình thành ở lượt cuối, và sở công bố qua website, terminal
   và các kênh thông tin. Bản tin ghi ngày, thiếu giờ đăng từng bản ghi.
   Độ trễ đến hôm sau trong phép thử dựa trên lịch công bố, không
   xác nhận website đã phát đúng giờ ở từng ngày.
   [Quy tắc SGE](https://en.sge.com.cn/upload/file/202001/17/RnByn7qMIWiZca3s.pdf) ·
   [Bản tin 12/01/2022](https://www.sge.com.cn/sjzx/shjzjhq/10002426?top=791887794807676928) ·
   [Bản tin 12/10/2022](https://www.sge.com.cn/sjzx/shjzjhq/10003740?top=791887794807676928).
2. **CFETS.** Truy vấn theo ngày rồi theo từng năm, dùng mã đúng
   `USD.CNY`. Cặp, ngày và đúng cột giờ khớp cả tám ngày mẫu.
   Sáu file theo năm trả 242–244 ngày mỗi năm. Quy định công bố theo
   các mốc giờ có bằng chứng từ SAFE, còn archive không có timestamp
   nhận/phát riêng cho từng mức giá. Thời gian trong header là lúc
   phục vụ request hiện tại.
   [CFETS](https://www.chinamoney.com.cn/english/hombtbrrthdt/) ·
   [SAFE](https://www.safe.gov.cn/en/2015/1230/1179.html).
3. **London.** Cache XAUUSD Development V10 có đủ Open 10:00 và 10:30
   ở tám ngày mẫu. Ask V10 là Bid +0,338 USD/oz, nên midpoint và
   spread đều thuộc proxy. So đúng cùng numerator, chỉ đổi mốc spot
   từ 10:00 sang 10:30, độ chênh premium quy quanh ngưỡng +1% là
   khoảng 0,005–0,166 điểm phần trăm trong pilot. Mức lớn nhất gần
   bằng độ lớn ngưỡng SELL 0,2%. Đây chỉ là độ nhạy theo đồng hồ.
   Chưa có sổ LBMA AM được phép và đủ dữ liệu để kiểm phân loại
   ngay tại hai ngưỡng. IBA xác định phiên LBMA AM bắt đầu 10:30,
   còn LBMA chuyển bảng lịch sử sang portal có điều kiện truy cập.
   Phương pháp WGC ghi các điểm theo ngày nhưng công bố theo kỳ
   và có thể mang giá ngày trước qua ngày nghỉ.
   [V10](ENTERPRISE-ALPHA-V10-RESULTS-20261115.md) ·
   [IBA](https://www.ice.com/iba/lbma-precious-metals) ·
   [LBMA về dữ liệu lịch sử](https://www.lbma.org.uk/articles/lbma-benchmark-prices-data-tables-are-moving) ·
   [Phương pháp WGC](https://www.gold.org/sites/default/files/downloads/2019-01/Chinese-premium-discount-methodology.pdf).

Bảng SGE có yêu cầu giới hạn theo ngày qua `/sjzx/everjzj`. Lấy được
60/72 gói tháng, trọn 2018–2022. Cả 12 tháng năm 2023 trả HTTP 403 ở
lượt lấy theo tháng và lượt thử lại. Hai kiểm tra ngày lẻ năm 2023
trả giá đúng ngày, chưa đủ để xác nhận cả chuỗi. Endpoint đồ thị
`/graph/DayilyJzj` bỏ qua giới hạn ngày/tháng đã gửi và trả 2.571
điểm. Đã loại payload ngay theo số dòng, không trích ngày hay mức
giá từ đó và không dùng endpoint này cho batch. Từng gói được nhận
vào phép tính đều được kiểm biên ngày trước 2024.

## Quy mô trước khi tính PnL

Mẫu số là giao giữa lịch XSHG và XLON của `exchange_calendars 4.13.2`,
đối chiếu dữ liệu nguồn trên từng ngày. Hai lịch là đại diện cho ngày
làm việc Shanghai/London. Lượt này chỉ đếm trên proxy, chưa đối chiếu
toàn bộ ngoại lệ lịch hợp đồng XAUUSD của quỹ. `Đợt` là một chuỗi liên
tiếp cùng hướng trên lịch chung. `Vị thế theo lịch` là số lượt giữ đủ
10 phiên, cho phép vào mới sau khi vị thế cũ hết cửa sổ. Các số này
chưa qua phí, lot, margin, giá khớp hay stop. Stop sớm có thể đổi số
lượt, cần một phép đo riêng nếu cổng nguồn được giải quyết.

| Năm | Cặp đủ / phiên lịch | Ngày BUY / SELL | Đợt BUY / SELL | Vị thế theo lịch | R/lượt để thêm 1.000 / 5.000 USD |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2018 | 236/236 | 2/1 | 2/1 | 3 | 2,67 / 13,33 |
| 2019 | 237/237 | 65/1 | 30/1 | 16 | 0,50 / 2,50 |
| 2020 | 236/236 | 3/197 | 3/9 | 23 | 0,35 / 1,74 |
| 2021 | 237/238 | 4/21 | 4/9 | 8 | 1,00 / 5,00 |
| 2022 | 235/235 | 59/22 | 9/15 | 13 | 0,62 / 3,08 |
| 2023 | 0/235 trong batch tháng | Chưa biết | Chưa biết | Chưa biết | Chưa biết |

Ngày thiếu XAU ở 2021 giữ unknown. Dòng 2023 chỉ phản ánh độ phủ nguồn
đã ghép cho census. 235/235 ngày có FX và XAU nhưng chưa có sổ SHAU
đủ cho năm đó. 197 ngày SELL năm 2020 thuộc chín đợt và tạo 21 lượt
SELL theo lịch. Đây là cùng trạng thái kéo dài qua nhiều ngày.

Giữ đủ 10 phiên giới hạn khoảng **24 lượt/năm** ngay cả khi có tín
hiệu mỗi ngày, dưới sàn 60 lệnh/năm cho nhánh daytrading chủ lực.
Ở mức 125 USD, 24 lượt cần bình quân tối thiểu **0,33R ròng/lượt** để
thêm 1.000 USD/năm và **1,67R/lượt** để thêm 5.000 USD/năm. Sau bước
lot và phí, số lượt thực tế có thể thấp hơn. Các mức trong bảng
tính theo 1R định mức 125 USD và chưa là kỳ vọng thị trường.

## Quyết định

Trạng thái `DATA_PATH_INCOMPLETE`. Đã định lượng giới hạn tần suất
của luật giữ đủ 10 phiên. Tương quan, gross/net markout, lợi thế
so với luôn BUY, stop, overlap BASE, drawdown và thời gian qua vòng
đều chưa đo. Chưa có căn cứ coi premium là nguồn PnL mới cho danh
mục hiện tại. Muốn dùng như một nhánh bổ sung cần đủ chuỗi SHAU PM
năm 2023 và làm rõ sai lệch phân loại của proxy. Kết quả về mục
tiêu Challenge giữ nguyên.

Bằng chứng riêng
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/prop-xau-shanghai-premium-20261119/`.
Có đăng ký, pilot, gói source giới hạn theo năm/tháng, census và manifest
SHA256. Đối chiếu múi giờ, tám cặp PM/FX, source hash, kỳ dữ liệu và
quy mô risk. Dữ liệu giá đưa vào phép đo nằm trước năm 2024.

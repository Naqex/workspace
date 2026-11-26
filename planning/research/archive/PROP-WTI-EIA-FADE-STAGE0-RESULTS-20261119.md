# WTI · đảo chiều sau 5 phút tin EIA

**Dừng ở Stage-0.** Luật đảo chiều âm ngay trước phí trong cả 2019 và
2022. Sau phí stress, 2019 lỗ **8,087 USD** và 2022 lỗ **15,224 USD** với
một thùng giả định mỗi tín hiệu. Cổng phí 12% giữ 0/43 và 1/44 tín hiệu.
Luật này chưa có lợi thế sau phí hoặc quy mô đủ để bổ sung cho danh mục
thi quỹ. Trạng thái `ECONOMIC_FAIL` + `CADENCE_OR_SAMPLE_SHORTFALL`, với
`PROP_UNMEASURED`.

## Luật đã khóa

Giữ đúng **88 thứ Tư** của R083, 44 ngày mỗi năm 2019 và 2022. R082/R083
dùng dấu phản ứng 30 phút theo chiều tiếp diễn và vào muộn. Pilot này
dùng dấu thay đổi midpoint từ **Open 10:30 tới Close 10:34**, bán khi
giá tăng, mua khi giá giảm, đứng ngoài khi bằng nhau. Vào ở Open 10:36,
thoát ở Open 14:29 cùng ngày, giờ New York. Giá khớp mô hình dùng Ask
vào/Bid ra cho BUY và Bid vào/Ask ra cho SELL. Hợp đồng tương lai WTI
trong bài Rousse–Sévi có phản ứng đảo lại một phần sau bất ngờ tồn kho
đo bằng kỳ vọng của nhà phân tích. Ở đây tín hiệu chỉ dùng giá từ CFD
proxy Dukascopy `LIGHT.CMD/USD`. [Rousse và Sévi](https://doi.org/10.5547/01956574.40.2.orou) ·
[R082](WTI-WEDNESDAY-COMPONENT-RESULTS-20261109.md) ·
[R083](WTI-SETTLEMENT-COMPONENT-RESULTS-20261109.md).

BUY dùng đáy Bid thấp nhất trong năm nến đã đóng, trừ 0,001 USD/thùng.
SELL dùng đỉnh Ask cao nhất, cộng 0,001. Khoảng cách cấu trúc tính từ
Bid vào cho BUY và Ask vào cho SELL tới stop. Nếu phía giá thoát đã
chạm hoặc vượt stop lúc vào, giữ tín hiệu trong bảng markout thô và
loại khỏi phần quy đổi risk. Cổng 12% dùng spread 10:36 làm ước lượng
spread vòng lệnh cộng phụ phí, chia cho khoảng cách cấu trúc. Khoảng
lỗ tại stop để quy đổi 150 USD risk gồm khoảng cách đó, spread vào và
phụ phí một lần. Không chuẩn hóa lot hay giả định khớp stop.
[Quy tắc Stage-0](../../.agents/skills/strategy-qualification/references/validation-gates.md#stage-0-unconditional-markout--scale-screen).

## Kết quả tại hai điểm giá

Các cột tiền là tổng USD nếu giao dịch giả định đúng một thùng trên
mỗi tín hiệu. Net trừ spread qua giá đúng phía và phụ phí vòng lệnh
**0,05 USD/thùng chuẩn, 0,10 USD/thùng stress**. Đơn vị chỉ để đối chiếu
kinh tế. Đa số tín hiệu chưa đủ điều kiện đặt risk.

| Năm | BUY / SELL / đứng ngoài | Gross midpoint | Spread | Net trước phụ phí | Net chuẩn | Net stress |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2019 | 22 / 21 / 1 | −1,463 | 2,324 | −3,787 | −5,937 | −8,087 |
| 2022 | 21 / 23 / 0 | −8,605 | 2,219 | −10,824 | −13,024 | −15,224 |

- Bình quân stress là **−0,1881 / −0,3460 USD/thùng/lượt** (2019 / 2022).
  Riêng spread đã đưa mức phụ phí hòa vốn xuống **−0,0881 / −0,2460
  USD/thùng/lượt**. Luật vẫn âm nếu phụ phí bằng 0. Tổng gross midpoint
  cần đạt để hòa vốn stress là 6,624 USD năm 2019 và 6,619 USD năm 2022.
- Đối chứng **luôn BUY** ở đúng các ngày có tín hiệu cho **−9,187 USD**
  năm 2019 và **−12,456 USD** năm 2022 dưới stress. Với cả 44 ngày mỗi
  năm, lần lượt **−9,837 / −12,456 USD**. Luật đảo chiều hơn đối chứng
  ở năm đầu và kém ở năm sau. Mọi cột đều âm.
- Cùng giờ ở ngày phi EIA, có 3 cặp/năm lấy từ pilot WTI đã có dữ liệu.
  Ghép trong cùng tháng theo thứ và khoảng cách ngày, khóa trước khi
  đọc giá. Cả sáu cặp phải ghép thứ Hai hoặc thứ Ba với thứ Tư. Net
  stress giao dịch cùng luật trên ngày thường là **+1,180 / −3,956 USD**,
  trên sáu ngày EIA tương ứng là **+0,690 / +0,330 USD**. Mẫu nhỏ và lệch
  thứ trong tuần khiến hiệu ứng riêng của EIA chưa xác định được.
  [Nguồn ngày thường](WTI-SESSION-SOURCE-RESULTS-20261109.md).

## Khoảng stop, tần suất và mục tiêu 1.000 USD/năm

| Năm | Tín hiệu thô | Vượt/chạm stop lúc vào | Stop tự nhiên trung vị | Phí stress kế hoạch trung vị / stop trung vị | Giữ chuẩn / stress | Net endpoint stress của nhóm giữ |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2019 | 43 | 8 | 0,1660 USD/thùng | 0,150 / 0,1660 = 90,4% | 0 / 0 | N/A |
| 2022 | 44 | 8 | 0,2745 USD/thùng | 0,150 / 0,2745 = 54,6% | 2 / 1 | +1,506R, tương đương +225,86 USD ở risk tham chiếu |

Cổng cấu trúc loại 8 tín hiệu mỗi năm. Cổng phí stress loại tiếp 35/35
tín hiệu còn lại năm 2019 và 35/36 năm 2022. Luật giữ **2,27%** tín hiệu
thô năm 2022. Lượt duy nhất là BUY **13/04/2022**, stop tự nhiên 1,327
USD/thùng. Với phí chuẩn, 2 lượt năm 2022 cho tổng endpoint **+1,057R**
tương đương **+158,62 USD** ở risk tham chiếu. Các số R sử dụng giá
thoát 14:29 và chưa xác minh giá có chạm stop giữa phiên. Năm 2019
không có cơ hội qua cổng. Với một lượt stress năm 2022, muốn góp
**1.000 USD/năm** cần **+1.000 USD/lượt**, tức **+6,67R** ở 150 USD
risk. Kết quả +1,506R của một lượt không đủ quy mô hoặc bằng chứng lặp.

## Giờ công bố và chất lượng nguồn

- **88/88** ngày có đủ cặp giá tại bốn mốc và đủ năm nến phản ứng. Từ
  10:36 tới 14:29 có đầy đủ cặp Open/Close theo phút ở **36/44 ngày
  2019** và **44/44 ngày 2022**. Năm 2019 thiếu 11/10.296 phút ghép
  Bid/Ask hợp lệ. Độ phủ tính từ nến xuất hiện rõ trong nguồn. Các mốc
  Open là quan sát đầu trong phút trên từng phía giá, có thể lệch tick
  và đã phản ứng với tin. Kho tick được đối chiếu không có cặp kiểm
  trước 10:30 trên các ngày pilot. Phép đo giữ mốc đã khóa.
  [Phạm vi tick cũ](WTI-GAP-TICK-RESULTS-20261110.md).
- **29/06/2022** là một ngày sự kiện. EIA báo trước ngày 28/06 sẽ phát
  hành theo giờ thường lệ ngày hôm sau, và xác nhận phát hành dữ liệu
  hai tuần trong sáng 29/06. Hai tuần dữ liệu không tạo hai tín hiệu.
  Giờ **10:30** là lịch công bố, thời điểm phát hành thực tế đến phút
  chưa xác minh được. Tín hiệu SELL hôm đó có markout stress
  **+3,814 USD/thùng**, nhưng tỷ lệ phí kế hoạch trên khoảng stop
  **40,43%** vượt trần. Toàn bộ 88 ngày giữ nhãn hồi cứu theo lịch.
  [Thông cáo trước sự kiện](https://www.eia.gov/pressroom/releases/press506.php) ·
  [Xác nhận ngày công bố](https://www.eia.gov/pressroom/releases/press507.php) ·
  [Kiểm giờ lịch sử](EIA-HISTORICAL-CLOCK-RESULTS-20261109.md).

Đã khóa luật, danh sách ngày và ghép đối chứng trước khi tính giá.
Tái dùng bằng chứng gốc 176 file ngày/phía giá R082/R083 và 12 file đối
chứng. Kiểm 199 SHA-256, 526 đối chiếu số học độc lập bằng Fraction và
các ca DST, đứng ngoài, thiếu giá, stop SELL. Một lượt endpoint mất
**4,38 giây**. Phiên Python hệ thống đầu tiên thiếu timezone New York
và dừng trước khi đọc giá. Runtime cache có `tzdata` đã chạy lại offline
và tạo một bộ kết quả. Không cần mô phỏng SL hoặc mở thêm năm vì cả
kỳ vọng sau phí và quy mô đều trượt. `BASE_GUARD` giữ `NOT_QUALIFIED`.

Hồ sơ riêng ở
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/prop-wti-eia-fade-stage0-20261119/`,
gồm card, cohort, script, kết quả từng ngày và manifest. SHA-256 card
`55d5a27af9278a06132c80a6d090c84be9c488ab76d3c86bd50e62863540490e`.
SHA-256 tổng hợp
`e2246de75505f11b4df25d407432ba6a14bc8e0f0100c706b88b72bbbf10cd8d`.

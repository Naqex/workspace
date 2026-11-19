# Audit Reward từ Challenge · Development 2018–2023

**V15 từng nhận Reward trong 12 tháng trên sổ mô phỏng 50k. Chưa có bản
nào đủ hai đợt 12 tháng không chồng lấn và có xác nhận ở kịch bản bất lợi.**
Giữ V4 và BASE_GUARD làm đối chứng. Dừng khai thác kho sổ cũ cho quyết
định mua Challenge. Với mục tiêu 12 tháng, hướng nghiên cứu tiếp theo
cần thêm nguồn lợi nhuận có thể kiểm định.

## Bảng quyết định

Mỗi ô là **qua P1 / qua P2 / nhận Reward đầu** trước hạn. Mỗi cấu hình
50k có 72 đầu tháng trong Development, dừng trước 01/01/2024 UTC.
Các tập đủ 12, 24 và 36 tháng có cùng mốc bắt đầu khi so các cấu hình
trong từng cột. Cột ngắn 12 tháng ghi sự kiện đã thấy ở 11 mốc từ
02/2023. Sổ chưa có sự kiện tới cutoff ở nhóm này vẫn chưa biết kết
quả đúng hạn. Vì tập mốc đủ thời gian khác nhau, số đếm giữa các cột
12, 24 và 36 tháng không nhất thiết tăng.

| Cấu hình 50k | Phí và đường giá | 12 tháng · 61 mốc | 24 tháng · 49 mốc | 36 tháng · 37 mốc | Mốc ngắn · đã thấy trong 12 tháng | Quyết định |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| V14 Original A | PRIMARY SYM | 2 / 0 / 0 | 1 / 0 / 0 | 4 / 0 / 0 | 2 / 0 / 0 | Nhanh nhất 41,72 tháng |
| V14 Original A | PRIMARY ASYM | 2 / 0 / 0 | 3 / 0 / 0 | 9 / 0 / 0 | 2 / 0 / 0 | Nhanh nhất 41,72 tháng |
| V15 Calibrated | PRIMARY SYM | 8 / 2 / 1 | 14 / 0 / 0 | 36 / 1 / 1 | 3 / 2 / 2 | Một đợt 12 tháng có đường chồng lấn |
| V15 Calibrated | PRIMARY ASYM | 9 / 2 / 1 | 15 / 0 / 0 | 37 / 1 / 1 | 3 / 2 / 2 | Cùng các mốc Reward trong 12 tháng |
| V15 Cushion | PRIMARY SYM | 16 / 2 / 1 | 19 / 5 / 1 | 33 / 11 / 6 | 8 / 3 / 3 | Nhanh nhất 4,27 tháng, một đợt 12 tháng |
| V15 Cushion | PRIMARY ASYM | 19 / 2 / 1 | 25 / 5 / 1 | 35 / 13 / 6 | 8 / 3 / 3 | Cùng các mốc Reward trong 12 tháng |
| V16 | PRIMARY, hai swap | 7 / 0 / 0 | 7 / 0 / 0 | 7 / 0 / 0 | 2 / 0 / 0 | Nhanh nhất 66,72 tháng |
| V16 | STRICT, hai swap | 3 / 0 / 0 | 3 / 0 / 0 | 3 / 0 / 0 | 1 / 0 / 0 | Không có Reward tới cutoff |
| V17 đã freeze | PRIMARY, hai swap | 7 / 0 / 0 | 8 / 0 / 0 | 7 / 0 / 0 | 2 / 0 / 0 | Nhanh nhất 66,72 tháng |
| V17 đã freeze | STRICT, hai swap | 5 / 0 / 0 | 4 / 0 / 0 | 4 / 0 / 0 | 2 / 0 / 0 | Không có Reward tới cutoff |
| V19 BASE_GUARD | PRIMARY, phí 1× | 6 / 0 / 0 | 6 / 0 / 0 | 7 / 0 / 0 | 2 / 0 / 0 | Nhanh nhất 66,72 tháng |
| V19 BASE_GUARD | PRIMARY, phí 1,5× | 4 / 0 / 0 | 4 / 0 / 0 | 4 / 0 / 0 | 2 / 0 / 0 | Không có Reward tới cutoff |
| V19 BASE_GUARD | STRICT, phí 1× | 3 / 0 / 0 | 3 / 0 / 0 | 3 / 0 / 0 | 1 / 0 / 0 | Không có Reward tới cutoff |
| V19 BASE_GUARD | STRICT, phí 1,5× | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 | 1 / 0 / 0 | Không có Reward tới cutoff |
| V26 P80_ISO_EXACT | PRIMARY 1× / 1,5×, STRICT 1× | N/A | N/A | N/A | N/A | Thiếu sổ hoặc mốc Reward Development tách riêng |

PRIMARY là đường mô phỏng chính với giả định nguồn của từng phiên
bản. STRICT áp xử lý bất lợi các đoạn thiếu giá đã đăng ký. Với V14,
dùng sổ Development mang nhãn `V14` trong audit V15. V14 Original và
Primary Bridge khớp trên đối chứng công bố. V16 và V19 BASE_GUARD dùng
cùng họ tín hiệu nhưng khác guard dự phòng theo ngày và cho số qua P1
khác nhau. Bảng giữ cả hai phiên bản. SYM và ASYM là hai chế độ phí đã
lưu. V16 và V17 giao dịch trong ngày nên hai chế độ cho cùng các mốc
trên bảng. V19 dùng SYM và kiểm thêm phí thực thi 1,5×.
[V14/V15](BRIDGE-AND-VELOCITY-V15-RESULTS-20261115.md) ·
[V16](GAP-IMMUNE-MULTIASSET-V16-RESULTS-20261116.md) ·
[V17](ADAPTIVE-VELOCITY-V17-RESULTS-20261116.md) ·
[V19](ASYMMETRIC-RECOVERY-V19-RESULTS-20261116.md).

**Các kịch bản chưa đo được trong phạm vi này.** V14 Original, V15
Calibrated và V15 Cushion thiếu sổ STRICT cùng policy tách riêng
Development. Báo N/A cho cả ba ở 12/24/36 tháng trong STRICT. Với V26,
có bảng Development theo lệnh và hồ sơ vòng đời toàn kỳ, nhưng thiếu
partition Development theo tài khoản hoặc bảng thời điểm Reward đủ
chi tiết. Số lệnh, số qua vòng hoặc payout ở sổ đã Funded sẵn không điền
được ô này. [Hồ sơ V26](BATCH-EXACT-ISO-V26-RESULTS-20261118.md).

V4 đối chứng 10k/25k có 0 P2 và 0 Reward ở 61 mốc đủ năm. Trong 11 mốc
ngắn, V4 vào Funded trong một đợt tháng 10/2023, với Reward 0 USD tới
cutoff. Cỡ vốn và policy khác bảng 50k. Các chân trời 24/36 của V4 chưa
được đo trong bộ sổ đối chứng này.
[V4 đã chốt](PROP-V4-HARVEST-BACKWARD-RESULTS-20261119.md#khép-61-mốc-đủ-12-tháng--nối-2021-sang-2022).

## Các lần nhận Reward đáng chú ý

- **V15 Calibrated.** Bắt đầu 01/2023 qua P2 ngày 09/11 và nhận
  **1.255,38–1.257,30 USD** ngày **11/12/2023 20:30 UTC**, sau 11,33
  tháng. Mốc 02/2023 đi cùng chuỗi giao dịch Funded và nhận cùng ngày.
  Mốc 03/2023 qua P2 ngày 29/11, nhận **526,66 USD** ngày **15/12/2023
  20:30 UTC** sau 9,52 tháng, với chuỗi Funded khác. Ba khoảng từ bắt
  đầu Challenge đến Reward đều chồng lấn. Mỗi sổ 12 tháng có Reward
  đã đi qua 11–12 lệnh có cờ bất định nguồn trước lần rút.
- **V15 Cushion.** Bắt đầu 01/2023 qua P2 ngày 25/04 và nhận
  **261,83–263,35 USD** ngày **10/05/2023 20:30 UTC**, sau **4,27 tháng**.
  Các mốc 02, 03 và 04/2023 nhận lần lượt **419,12–419,92 USD** ngày
  **13/06**, **526,66 USD** ngày **15/12** và **64,65 USD** ngày
  **22/12**, cùng giờ 20:30 UTC. Chúng có các chuỗi Funded khác nhau,
  nhưng cả bốn đường Challenge → Reward đã bắt đầu trước lần rút sớm
  nhất. Mỗi đường có 2–11 lệnh gắn cờ bất định nguồn trước lần rút.
- **Chân trời dài hơn.** Ở 24 tháng, Cushion có đúng một mốc đủ thời
  gian nhận Reward. Bắt đầu 01/2022, nhận **64,65 USD** ngày
  **22/12/2023** sau **23,68 tháng**. Ở 36 tháng, các mốc Cushion có
  Reward mất **27,59–35,67 tháng**. Những sổ mở 01, 03, 05 và 06/2018
  hội tụ vào hai chuỗi nhận đầu ngày **17/09/2020** hoặc **30/10/2020**
  tùy phí và mốc bắt đầu, tiền mỗi sổ **24,46–47,30 USD**. Chúng tách
  được khỏi đường bắt đầu 01/2023, nhưng mất hơn hai năm. Calibrated ở
  36 tháng chỉ có mốc 01/2021 nhận đầu vào **15/12/2023** ASYM hoặc
  **22/12/2023** SYM, sau khoảng **35,44–35,67 tháng**. Trên cùng 37 mốc
  bắt đầu đến 01/2021, cả bốn cấu hình V15 có **0 Reward trong 12 và
  24 tháng**. Các kết quả dương ở 12 và 24 tháng trong bảng do có thêm
  các mốc bắt đầu muộn hơn.
- **V14, V16, V17 và V19 ở chân trời dài.** V14 bắt đầu 07/2020, lần
  nhanh nhất là **44,45 USD** ngày **22/12/2023** sau **41,72 tháng**.
  V16, V17 và V19 PRIMARY 1× cùng có mốc nhanh nhất bắt đầu 06/2018,
  nhận ngày **22/12/2023** sau **66,72 tháng**. Tiền tương ứng
  **64,65 / 40,40 / 64,65 USD**. V16 và V19 trùng mốc này nhưng hồ
  sơ admission toàn dải khác nhau. Các bản STRICT có sổ xác minh
  được đều không có Reward từ Challenge trước cutoff.

Tiền trên là **phần trader sau chia 80%**, trước phí mua/retry, chi phí
vận hành và thuế. Sổ đã qua P2, không còn lệnh mở lúc rút, có lãi đóng
tối thiểu 20 USD và đã qua 14 ngày kể từ giao dịch Funded đầu. Ví dụ,
Cushion SYM 01/2023 rút từ 50.327,29 USD về 50.000 USD, debit 327,29
USD gồm 261,83 USD trader và 65,46 USD phần hãng. Không cộng tiền giữa
các sổ chồng lấn. Trong 61 mốc đủ năm, tiền **lần rút đầu mô phỏng trung
bình có tính các sổ 0 USD** là 20,58–20,61 USD ở Calibrated và 4,29–4,32
USD ở Cushion. Giới hạn thời gian chờ ở 12 tháng cho trung bình **11,99**
và **11,87** tháng. Hai số này tính các trường hợp chưa nhận tiền đến
hạn. Các cặp mẫu số, tiền từng mốc gồm 0 và thời gian chờ giới hạn cho
24/36 tháng có trong receipt.

Đối với **sổ đã Funded từ 01/2018**, V15 nhận lần đầu 06/02/2018,
**80,77–86,53 USD**, kiểu Calibrated và Cushion cho cùng kết quả vì
cushion dùng riêng trong P1. Tổng phần trader của sổ Funded trong
sáu năm là **6.916,91–7.401,11 USD**, trước chi phí ngoài giao dịch.
Đó là một mốc bắt đầu và thời gian quan sát khác, dùng để kiểm sự
khác nhau giữa hai điểm xuất phát.
[Quy tắc và sổ Funded của V15](BRIDGE-AND-VELOCITY-V15-RESULTS-20261115.md).

## Nguồn đối soát và phán quyết

Dùng 20 file sổ Development và audit kèm theo. Đối chiếu 36 tổ hợp
policy/phí/đường giá × 72 mốc challenge-origin, cùng 36 sổ Funded khởi
tạo để đối chứng. Kiểm timestamp trước cutoff, ghép từng event với
sổ/audit, số dư khi qua pha, số ngày giao dịch, điều kiện chờ, đường
giá có cờ bất định, debit và chia tiền đến cent. Cả hai thứ tự nến
khớp số đếm theo hạn, thời điểm và tiền Reward đầu. Có khác ở chi tiết
một số chuỗi khớp và hai timestamp P1 của V14 SYM. Các đường PRIMARY
có Reward 12 tháng không ghi nhận breach trước Reward nhưng còn đoạn
giá thiếu và mô hình Bid/Ask giả định. Trên toàn bộ 72 mốc, sụt equity
dưới vốn đầu cao nhất của V15 PRIMARY SYM là **8,131%**. Giới hạn
quan sát và dữ liệu giữ nguyên từ từng báo cáo nguồn.

Private receipt chứa khóa thí nghiệm, script đọc sổ, 58 SHA-256 nguồn,
36 tổ hợp và khóa truy vết từng lần rút ở
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/prop-challenge-reward-milestones-20261119/`.
Trường `event_id` là khóa truy vết dẫn xuất từ mốc bắt đầu, thứ tự lần
rút và timestamp. Đối soát đọc sổ mất **41,43 giây**. SHA-256 của
`milestones.json` là
`416ccbf8dacea10bc52a040368ac5f966f7b5c277ef5764248d6401efa7c4f30`.
Phép đo không mở giá hoặc sổ trộn đường giá 2024–2026. Không cần replay
10k/25k vì chưa có cấu hình vượt cổng lặp lại 12 tháng và có xác nhận
bất lợi. `BASE_GUARD` giữ `NOT_QUALIFIED`.

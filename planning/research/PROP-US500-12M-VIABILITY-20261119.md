# US500 M15 · Sàn lợi thế cho Swing 10k/25k trong 12 tháng

**Nhịp 3–5 phải là lệnh thực nhận.** Với risk cố định **0,25% vốn đầu**,
một vị thế, cần 40R ở Vòng 1 và 20R ở Vòng 2 trên hai sổ reset.
1R là **25 USD ở 10k**, **62,50 USD ở 25k**. Tổng mục tiêu lần lượt là
1.000 + 500 USD hoặc 2.500 + 1.250 USD trên hai sổ. 12 tháng là mục
tiêu của dự án. FTMO cho thời gian không giới hạn và yêu cầu ≥4 ngày
mở lệnh ở từng vòng. [FTMO 2-Step](https://ftmo.com/en/2-step-challenge/) ·
[Trading Objectives](https://ftmo.com/en/trading-objectives/?affiliates=3682).

| Ngân sách thời gian | Lệnh thực nhận | Net cần/lệnh | USD/lệnh 10k / 25k | Thiếu so với mean R094 stress · R/lệnh / R/tháng lịch | Thiếu USD trong 12 tháng · 10k / 25k |
| --- | ---: | ---: | ---: | ---: | ---: |
| 52 tuần × 3 | 156 | +0,385R | 9,62 / 24,04 | 0,471 / 6,12 | 1.835,83 / 4.589,58 |
| 52 tuần × 5 | 260 | +0,231R | 5,77 / 14,42 | 0,317 / 6,87 | 2.059,72 / 5.149,31 |
| 48 tuần × 3 | 144 | +0,417R | 10,42 / 26,04 | 0,503 / 6,03 | 1.810,00 / 4.525,00 |
| 48 tuần × 5 | 240 | +0,250R | 6,25 / 15,63 | 0,336 / 6,72 | 2.016,67 / 5.041,67 |

Công thức là 60R chia số lệnh đã khớp. Cột thiếu minh họa cùng kỳ vọng
R094 stress **−0,0861R/lệnh** theo đúng nhịp giả định. 260 lệnh là phép
tính lý tưởng. Với trần một entry/phiên và lịch NYSE chỉ 250–253 phiên
mỗi năm trong 2018–2023, ngay cả khớp mọi phiên cũng cần khoảng
**+0,237–0,240R/lệnh**. Kịch bản 48 tuần dành bốn tuần lịch cho chuyển
pha và Funded, đây là ngân sách thiết kế. Nếu 5 cơ hội/tuần mà chỉ 4
lệnh thực nhận trong 48 tuần, **192 lệnh cần +0,3125R/lệnh**. USD 25k
trong bảng là quy đổi risk lý thuyết. Số khớp và bước lot ở 25k chưa đo.
[Tần suất US500](US500-FREQUENCY-LANDSCAPE-20261111.md) ·
[Lịch 2018–2023 dùng trong chuẩn cash](PROP-US500-CASH-SESSION-20261119.md).

### R094 · đủ nhịp, chưa có lợi thế

Phá biên 15 phút đầu phiên New York, một lần thử/ngày, thoát theo stop
hoặc gần trưa. Đọc đúng các sổ 10k của 2022–2023, 0,25% risk theo vốn
đầu, lot xuống lưới của sổ gốc. 2022 có **231/251** phiên vào, 2023
**222/250**. Cả hai năm **0/52 tuần trống, 0/12 tháng trống**. Tháng có
16/19/23 lệnh và 16/18/22 lệnh (min/trung vị/max). Số lệnh là fill mô
hình từ sổ, chưa xác minh fill broker. [Protocol và sổ R094](US500-M15-OPENING-SCREEN-RESULTS-20261111.md).

| Năm / phí | Lệnh đủ đường / mô hình | Thắng / thua | Thắng TB / lỗ TB (R) | Tỷ lệ thắng / payoff | Gộp sau spread / trượt (R) | Net R (USD) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2022 chuẩn | 230 / 231 | 101 / 130 | +0,960 / −0,779 | 43,72% / 1,23× | +1,77 / 6,10 | −4,33 (−108,25) |
| 2022 stress | 230 / 231 | 96 / 135 | +0,905 / −0,760 | 41,56% / 1,19× | +1,47 / 17,26 | −15,78 (−394,62) |
| 2023 chuẩn | 219 / 222 | 98 / 124 | +1,066 / −0,877 | 44,14% / 1,22× | +6,16 / 10,41 | −4,25 (−106,31) |
| 2023 stress | 219 / 222 | 95 / 127 | +0,914 / −0,867 | 42,79% / 1,05× | +5,04 / 28,26 | −23,22 (−580,59) |

Phân phối stress từ dưới −1R, [−1; −0,5), [−0,5; 0), hòa, (0; 0,5),
[0,5; 1), [1; 2), ≥2R lần lượt là **0 / 100 / 35 / 0 / 42 / 23 / 23 / 8**
năm 2022 và **1 / 108 / 18 / 0 / 32 / 29 / 28 / 6** năm 2023. Receipt
giữ cả histogram chuẩn.

Spread nằm trong giá Bid/Ask. Với 140/121 lệnh thoát theo giờ có đường
đủ hai năm, spread gộp theo hai midpoint là **0,436/0,504 điểm mỗi
vòng**, cộng trượt mô hình 0,50 điểm chuẩn hoặc 1,50 điểm stress.
Ma sát stress của mẫu này bình quân **0,093/0,167R/lệnh**. Chưa có
quote đồng thời tại stop để tách spread cho toàn sổ. Lot thay đổi theo
kịch bản phí, nên hiệu hai cột net cũng bao gồm khác biệt lot. Riêng
phần gộp sau spread đã rất nhỏ ngay trước khi trừ trượt.

Ở 231/222 fills, lý thuyết cần **+0,260/+0,270R/lệnh**. So với mean
stress **−0,068/−0,105R**, còn thiếu **0,328/0,375R/lệnh**,
**6,32/6,94R/tháng**, hay **1.894,62/2.080,59 USD** ở sổ 10k.
Nếu thắng và thua bình quân giữ nguyên đúng như sổ stress, dùng
`p = (mean_net_R_cần + |lỗ trung bình|) / (lãi trung bình + |lỗ trung bình|)`.
Tỷ lệ thắng cần **61,26%/63,85%** ở nhịp đã đo, **68,76%/70,27%** ở
156 fills và **59,52%/61,63%** ở 260 fills. Các ngưỡng chỉ mô tả yêu cầu
về payoff kèm tỷ lệ thắng. Thay luật có thể đổi đồng thời cả hai.

Sổ trọn năm vẫn thiếu 1/3 đường giữ lệnh. Chỉ cộng lệnh đủ đường, stress
là **−452,91/−601,88 USD**. Nếu các lệnh thiếu lỗ đúng −1R, tổng minh
họa là −477,91/−676,88 USD. Để đủ +60R trên mỗi năm, mỗi lệnh thiếu
phải đóng góp bình quân **+1.952,91/+700,63 USD**. Đây là phép đo phần
thiếu, gap có thể lỗ hơn −1R. Năm 2023 cash DD đỉnh–đáy đã là 717,85 USD
trong mô hình stress, khoảng 7,18% của 10k. Sổ hiện thiếu đo equity
Daily/Overall để đánh giá hai quy tắc đó.

### Khi nào số học thành đường thi quỹ khả thi?

- 60R là tổng hai đích riêng. Cần qua 40R trước, flat và đủ ngày ở
  Vòng 1 rồi bắt đầu một sổ mới để kiếm 20R. Lãi vượt đích ở Vòng 1
  không chuyển sang Vòng 2. Mức lỗ ngày 5% và lỗ tĩnh 10% tương đương
  20R và 40R ở risk cố định. Phải đo trên equity theo thời gian, kể cả
  floating và reset Prague. Mô hình gap và thứ tự thắng/thua quyết định
  có vi phạm trước khi chạm đích hay không. [FTMO 2-Step](https://ftmo.com/en/2-step-challenge/).
- Funded cần có lãi riêng, lần xin Reward đầu từ ngày 14 sau lệnh
  Funded đầu, cần đóng vị thế và lệnh chờ. FTMO công bố mức chia mặc
  định 80% ở 2-Step và hoàn phí lần mua với Reward đầu. Tính thu nhập
  theo phần thực nhận sau phí thử lại và vận hành. Chưa có con số thu
  nhập mục tiêu từ chủ dự án. [Điều kiện nhận Reward](https://ftmo.com/en/faq/how-do-i-withdraw-my-profits/?affiliates=haJaFmeFdIhINEqaYyOC) ·
  [Hoàn phí](https://ftmo.com/en/faq/what-fees-do-you-charge-and-are-they-recurrent/).
- V15 Calibrated/Cushion mỗi bản từng có **1/61** mốc PRIMARY nhận
  Reward 12 tháng trên **50k**, chưa chứng minh hai đợt độc lập. Phép
  thử **+7.500 USD/năm** dùng lệnh giả định thêm vào BASE 50k, quy
  chiếu risk **300 USD** với +0,625R tại 40 lệnh và +0,417R tại 60 lệnh.
  Đó là mốc đầu tiên trong lưới cho hơn nửa cửa sổ nhận Reward ở cả
  PRIMARY/STRICT. Các cửa sổ chồng lấn và lệnh giả định. Hai mốc này
  không cho xác suất pass hay lý do nâng risk benchmark.
  [Reward V15](PROP-CHALLENGE-REWARD-MILESTONES-20261119.md) ·
  [Bài độ nhạy 7.500 USD](PROP-TWO-PHASE-SENSITIVITY-20261119.md).

### Ví dụ sàng nhanh · lực mua từ cổ tức

Bài Hartzmark–Solomon ghi nhận khoảng **8 bp** lợi suất cả ngày của danh
mục cổ phiếu có trọng số vốn hóa ở nhóm ngày chi trả cổ tức cao nhất.
Giả sử chuyển nguyên 8 bp vào đúng cửa sổ US500 và có **50 fills/năm**.
Với stop **1% = 100 bp** từ chuẩn cash, gross lý tưởng **0,08R/lệnh**,
tức **4R/năm** theo lot lý thuyết trước phí. Quy đổi **100 / 250 USD**
ở 10k/25k. Dùng ma sát trung bình của 1.502 endpoint cash đã đo tại
125 USD risk làm proxy, spread khoảng 0,0120R và trượt khoảng 0,0141R
chuẩn hoặc 0,0424R stress. Khi đó còn **2,69R chuẩn / 1,28R stress/năm**
hay **67 / 168 USD chuẩn**, **32 / 80 USD stress** ở 10k/25k.
Mục tiêu 60R ở nhịp này cần **1,20R/lệnh**, tương đương khoảng
**120 bp net/lệnh** với stop 1%. Đây là kịch bản chuyển nguyên hiệu
ứng cả ngày và dùng ma sát trung bình, chưa đo riêng ngày cổ tức.
Quy mô trước phí đã hụt **56R**. Gác ví dụ này ngay trên giấy.
[NBER working paper, Figure 1](https://www.nber.org/system/files/working_papers/w30688/w30688.pdf) ·
[Chuẩn cash-session](PROP-US500-CASH-SESSION-20261119.md).

### Điều kiện để cấp một lượt Development tiếp theo

Một tài sản **US500**, một tín hiệu biết trước entry, một cửa sổ giữ,
một stop tự nhiên, một vị thế, dữ liệu Bid/Ask sẵn và cô lập 2018–2023.
Đếm fill sau lịch, nguồn, spread, lot và overlap trước. Mốc để xem xét
**144–240 fills/48 tuần và net stress ≥60R/năm quy đổi trong mỗi cụm
2018–2020 và 2021–2023**. Dùng **+0,417R đến +0,250R mỗi fill** tùy
tần suất thực nhận và ghi tuần/tháng trống. Giữ cổng phí/stop 12%–15%
đã đăng ký, ≥50% tín hiệu tự nhiên đi qua, stress markout dương ở từng
năm và đủ lớn so với phí. Nếu qua sàng, giữ luật cố định và chứng minh
trình tự 40R rồi 20R theo giới hạn equity, độ phủ và khung thời gian.
Chưa cấp suất chạy cho một tín hiệu cụ thể trong lượt này.

Private receipt `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/prop-us500-12m-viability-20261119/`.
Đã kiểm **31 SHA nguồn**, **906 dòng giao dịch** (453 fill × 2 phí),
cầu nối từng net, histogram, công thức payoff bằng phân số và Zstd
roundtrip. Manifest SHA256
`7529e40d28f39472cd5db59c6cb8cc326e100b8c1143681b203fc599a80c1e50`.
Dùng ledger R094 2022–2023 và summary cash Dev 2018–2023 đã khóa.

# V4 Harvest A · kiểm tra lặp lại trên 2018–2021

**Giữ V4 Harvest làm đối chứng nghiên cứu. Chưa có cơ sở dùng danh mục này
để mua Challenge 10k hay 25k.** Trong 37 mốc bắt đầu đủ 12 tháng, cả hai
cỡ vốn chỉ qua vòng 1 ở 1–2 mốc tùy swap. Không có mốc qua vòng 2 hoặc
nhận Reward. Đợt tháng 10/2023 vẫn là đợt duy nhất đã quan sát qua cả hai
vòng ở hai cỡ vốn, và các sổ đó hết dữ liệu khi chưa nhận Reward.
[Đối chiếu 2022–2023](PROP-V4-HARVEST-SWING-CAPITAL-RESULTS-20261119.md).

## Phạm vi và cách đo

- Giữ Gold A0 + EURUSD SAT1 (`EURUSD.SWEEP.ASIA.LONDON.DAY`), tín hiệu,
  stop, cách thoát, phí, sizing theo pha, bước lot, trần risk, sàn dự
  phòng và quy tắc rút lời từ `4e80dd6`. Dùng bố cục đánh giá 2-Step
  Swing, reset lỗ ngày theo Prague, mục tiêu vòng 1 là +10% và vòng 2
  là +5%. Risk định mức mỗi nhánh qua P1/P2/Funded lần lượt là
  40/35/25 USD ở 10k và 100/87,50/62,50 USD ở 25k, trước giới hạn
  theo equity và làm tròn lot. SYM giữ swap vàng −40/−40 USD/lot/rollover,
  ASYM giữ −45/−5, theo thứ tự BUY/SELL.
- 37 mốc đầu tháng từ 01/2018 đến 01/2021 được theo dõi đủ 12 tháng.
  11 mốc từ 02/2021 đến 12/2021 được theo dõi đến ngày 01/01/2022
  (loại trừ mốc cuối). Các cửa sổ chồng lấn và dùng lại cùng diễn biến
  giá. Đếm mốc qua vòng chỉ mô tả mẫu lịch sử đã được dùng trong nghiên cứu.
- EURUSD dùng các tick Bid/Ask gốc đã xác minh SHA-256, dựng H1 từ Bid,
  giữ thứ tự tick thật khi khớp. Vàng dùng Bid M1 từ bản V8 đã sửa lịch,
  dựng Ask bằng spread cố định 0,338 USD/oz và đo hai thứ tự giả định
  Open–Low–High–Close, Open–High–Low–Close. Lịch V8 là proxy.
  [Đối chứng Gold V8, mục 6](PROP-GOLD-V8-RESULTS-20261115.md#6-baseline-control-annual-và-lifecycle).
- Khởi tạo chỉ báo từ dữ liệu trong phạm vi 2018 trở đi. So với V8 đã có
  warmup từ 11/2017, 342/343 dòng vàng khớp giờ quyết định, chiều và stop.
  Dòng còn lại là BUY 04/01/2018 09:00 UTC, chỉ có trong V8. Tín hiệu vàng
  đầu tiên tái lập được là 12/01/2018 10:00 UTC. Vì vậy cửa sổ 01/2018
  chịu giới hạn warmup tại đầu mẫu. Giá 2022–2023 chỉ dùng để
  kiểm tái lập trên đoạn đã biết. Giá được đọc cho nghiên cứu nằm trong
  2018–2023.

## Kết quả tài khoản

| Vốn | Swap | Qua P1 / P2 / Reward, 37 mốc | Lỗ ngày lớn nhất | Sụt dưới vốn đầu lớn nhất | Sụt đỉnh–đáy lớn nhất |
| --- | --- | ---: | ---: | ---: | ---: |
| 10.000 USD | SYM | 1 / 0 / 0 | 1,2977% | 8,0041% | 13,9757% |
| 10.000 USD | ASYM | 2 / 0 / 0 | 1,3012% | 8,0227% | 14,0954% |
| 25.000 USD | SYM | 1 / 0 / 0 | 1,3502% | 8,0430% | 14,3017% |
| 25.000 USD | ASYM | 2 / 0 / 0 | 1,3538% | 8,0275% | 14,3444% |

Cực trị trên lấy theo Open–Low–High–Close. Thứ tự còn lại chỉ đổi một
cực trị trong bảng, sụt đỉnh–đáy 25k SYM còn 14,2999%. Mọi cỡ vốn và phí
đều ghi nhận 0 P1 / 0 P2 / 0 Reward ở 11 mốc muộn trước cutoff. Các sổ
đều ghi 0 USD Reward và 0 USD hoàn phí. Thời gian tới P2 và Reward chưa
quan sát được.

Mốc 01/2018 qua P1 ngày 25/04/2018 lúc 08:00 UTC ở cả 10k/25k và cả hai
swap. Với ASYM, mốc 02/2018 cũng qua P1 ngày 28/09/2018 lúc 09:00 UTC ở
cả hai cỡ vốn. Hai lần qua P1 này thuộc các cửa sổ cùng đi qua phần lớn năm
2018. Không có đường nào tới Funded trong 2018–2021. Trong 2022–2023, các
mốc đủ 12 tháng cũng có 0 P2, còn các mốc ngắn hơn đã quan sát qua P2 đều
hội tụ ngày 20/10/2023. P2 là bước vào Funded trong mô phỏng, Reward cần
lãi đủ điều kiện sau đó. [FTMO 2-Step](https://ftmo.com/en/2-step-challenge/).

Cả hai đường M1 đều không ghi nhận vi phạm giới hạn lỗ ngày 5% hoặc sụt
dưới vốn đầu 10%. Sụt đỉnh–đáy trên 14% đo mức mất từ đỉnh lợi nhuận
trong từng pha. Giới hạn 10% trong sổ đo so với vốn đầu pha. Kiểm margin
tại thời điểm vào theo đòn bẩy giả định Gold 1:15, EUR 1:30 cho mức dùng
cao nhất khoảng 33,67% equity và 0 lượt vượt equity.

## Bốn sổ năm không chồng lấn

Số dưới đây là **equity cuối kỳ theo pha đang chạy**, USD. Mốc 01/2018
đã qua P1 nên các số cuối kỳ nằm sau reset về vốn đầu ở P2. Ba mốc còn
lại đều kết thúc ở P1. Cả hai thứ tự trong nến cho cùng số trong bảng.

| Năm bắt đầu | 10k SYM | 10k ASYM | 25k SYM | 25k ASYM |
| --- | ---: | ---: | ---: | ---: |
| 2018 | 9.408,36 | 9.531,06 | 23.513,86 | 23.653,60 |
| 2019 | 9.207,04 | 9.209,55 | 23.017,66 | 23.025,48 |
| 2020 | 9.202,69 | 9.200,41 | 23.014,09 | 23.008,15 |
| 2021 | 9.204,99 | 9.203,39 | 23.016,37 | 23.023,91 |

Để tìm nhánh nào tạo hoặc kéo giảm lợi nhuận, đối chiếu mỗi nhánh ở
risk cố định P1 100 USD/lượt của sổ 25k, sau phí và làm tròn lot.
Bảng tham chiếu này bỏ state chung của tài khoản.

| Năm | Gold A0 định giá được | Gold SYM / ASYM, USD | EUR SAT1 tín hiệu / định giá được | EUR dưới cả hai swap, USD |
| --- | ---: | ---: | ---: | ---: |
| 2018 | 83 | −3.205,54 / −2.829,69 | 133 / 125 | +4.015,34 |
| 2019 | 55 | −1.363,61 / −1.240,76 | 141 / 105 | −1.840,84 |
| 2020 | 98 | −307,51 / −252,76 | 122 / 116 | −2.539,57 |
| 2021 | 106 | −1.093,93 / −884,98 | 44 / 40 | −1.783,29 |

Gold âm cả bốn năm theo hai giả định swap. EUR bù được Gold ở năm 2018
trong bảng tham chiếu, phù hợp với việc danh mục có một vài mốc qua P1.
Sau 2018 cả hai nhánh đều âm. V8 Gold-only cũng âm bốn năm và có 0/48
mốc qua P1 ở 50k với lát quan sát khác. So sánh V8 để kiểm hướng của
kết quả Gold. Phán quyết cho danh mục dựa trên sổ đã mô phỏng cap, reset
và sizing của từng pha. [Đối chứng Gold V8](PROP-GOLD-V8-RESULTS-20261115.md).

## Độ phủ và kiểm chứng

| Năm | H1 EUR có quan sát | H1 EUR có đủ 60 phút | EUR bị cổng phí 15% loại | EUR thiếu giá thoát định kỳ |
| --- | ---: | ---: | ---: | ---: |
| 2018 | 6.227 | 6.142 | 8 | 0 |
| 2019 | 6.224 | 6.070 | 36 | 0 |
| 2020 | 6.250 | 5.878 | 6 | 0 |
| 2021 | 6.240 | 5.051 | 3 | 1 |

Tổng nguồn EUR có 104.696.330 tick. Trong 440 tín hiệu có 53 bị cổng phí
loại, 386 định giá được và một tín hiệu BUY 13/09/2021 lúc 09:00 UTC thiếu
báo giá tại hạn thoát theo quy tắc V3. Tỷ lệ giờ có đủ phút giảm đáng kể
trong 2021. 44 tín hiệu quan sát được năm đó là kết quả trên nguồn hiện
có. Cửa kiểm gap không tìm thấy khoảng thiếu trên 15 phút trên các đường
giữ lệnh đã dựng sau khi loại giờ nghỉ thường lệ. Điều này vẫn để ngỏ
giá Ask và thứ tự giao dịch trong từng phút đối với vàng.

Trên Development 2022–2023, tái lập 247 danh tính tín hiệu EUR. Lát
01/2023 có 9 lệnh vàng và 13 lệnh EUR khớp thời điểm, giá vào/ra, lý do
thoát, hạn thoát và tiền tới cent khi dùng cùng tick gốc. Trên đúng lát
đó, đổi sang proxy M1 cho tổng tiền vàng từ −170,02 thành −183,56 USD,
EUR từ −948,02 thành −1.103,80 USD tại risk thử 100 USD. Giá thoát M1 chỉ
trùng tick ở 2/9 lệnh vàng và 3/13 lệnh EUR. Đây là đo sai khác nguồn trên
một lát, chưa có biên sai số chung cho lịch sử 2018–2021.

Đối soát độc lập với vòng replay bằng `verify_summary.py`: 384 sổ, giới
hạn thời gian theo từng cửa sổ, cash bridge tới cent, risk theo pha, bước
lot và trần risk chung. Bản chạy chỉ đọc dựng lại `summary.json` từ hai
sổ Zstandard và xác minh 12 SHA-256 trong `manifest.json`. Mỗi thứ tự
trong nến xử lý 36.983.140 cập nhật báo giá. Artifact cục bộ ở
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/prop-v4-harvest-backward-20261119/`.
SHA-256 của `summary.json` là
`9b8b935e84c564d4654a20c088c96d6db0eea1bceac867da4833728717f0ceb0`.

**Phán quyết nghiên cứu.** Thất bại chính trong phép đo là thiếu lợi
nhuận tích lũy để lặp lại đường qua hai vòng. Đổi swap chỉ thêm một mốc
qua P1 và chưa tạo P2. Mức lỗ mô phỏng không chạm trần nhưng vẫn còn
bất định về đường giá vàng và độ phủ EUR. Giữ V4 Harvest A làm đối chứng
và trạng thái BASE_GUARD `NOT_QUALIFIED`. Phép đo bổ sung dùng đúng
policy cũ để trả lời câu hỏi lịch sử, với mức xác nhận giới hạn ở hai
đường giả định M1.

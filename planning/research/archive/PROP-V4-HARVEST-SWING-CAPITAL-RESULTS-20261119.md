# V4 Harvest · FTMO 2-Step Swing 10k và 25k

**Có đường qua hai vòng ở 10k/25k, vẫn chưa thấy Reward từ Challenge.**
Trong 13 mốc đủ trọn 12 tháng của phép đo gốc, mọi size và swap đều
0/13 qua vòng 2. Khi bổ sung đủ 11 mốc bắt đầu muộn trong 2023, các
mốc 02 và 03/2023 qua hai vòng trước cutoff ở cả 10k lẫn 25k. Mốc
07/2023 cũng qua ở 25k ASYM. Tất cả hội tụ vào cùng đợt lịch sử và
đều chưa có Reward hoặc hoàn phí trong thời gian quan sát. Sổ đã
Funded từ đầu có dòng tiền mô phỏng, trình bày riêng bên dưới.
Bằng chứng vẫn chưa đủ để mua Challenge. BASE_GUARD giữ NOT_QUALIFIED.

## Giữ chiến lược, đổi đúng quy mô tài khoản

Dùng arm A tại 24e7b82, Gold A0 và EURUSD SAT1, 446 tín hiệu trên tick
Development 2022–2023. Mỗi sổ chính bắt đầu từ một trong 13 đầu tháng
01/2022 đến 01/2023, dừng đúng 12 tháng sau. Các cửa sổ chồng lấn, nên
4/13 chỉ là số đường đã quan sát qua vòng. SYM dùng swap Gold −40/−40,
ASYM −45/−5 USD/lot/rollover. Hai nhánh giữ nguyên commission, trượt giá
và stop từ arm A. [Arm A và giới hạn dữ liệu](PROP-V4-HARVEST-FX-SPLIT-20261119.md).

| Tham số USD | Vốn 10k | Vốn 25k | Đối chứng 50k |
| --- | ---: | ---: | ---: |
| Risk P1 / P2 / Funded mỗi nhánh | 40 / 35 / 25 | 100 / 87,50 / 62,50 | 200 / 175 / 125 |
| Trần stop mở / dừng lỗ thực hiện ngày | 160 / 200 | 400 / 500 | 800 / 1.000 |
| Sàn dự phòng trên projected stop | 9.200 | 23.000 | 46.000 |
| Equity giảm tới mức / trần risk tương ứng | 9.600 → 30, 9.400 → 18 | 24.000 → 75, 23.500 → 45 | 48.000 → 150, 47.000 → 90 |
| Target P1 / P2 và giới hạn Daily / Overall | 1.000 / 500 và 500 / 1.000 | 2.500 / 1.250 và 1.250 / 2.500 | 5.000 / 2.500 và 2.500 / 5.000 |
| Ngưỡng đóng băng / khóa lời Funded trên vốn đầu | +100 / +200 | +250 / +500 | +500 / +1.000 |

Giữ bước lot 0,01, min/max lot, tick size, phí trên từng lot, làm tròn
cent, 4 ngày giao dịch tối thiểu, buffer 48h, chu kỳ yêu cầu 14 ngày
và ngưỡng lãi đóng 20 USD. Tái tính lots, risk thực, admission, reset
Prague và đường equity từ tick, dùng state machine V6 trên một traversal.
Runner gốc chưa có margin admission. Đối chiếu bổ sung 18.402 lượt vào
với proxy Swing XAU 1:15, EUR 1:30 và ask notional tại entry. Không lượt
nào vượt equity theo proxy, mức dùng cao nhất ở sổ thi
**34,29% / 35,20% / 38,29%** cho 10k/25k/50k. Đây là kiểm ngay tại
entry với đặc tả tham chiếu, chưa đo margin intrabar hoặc đặc tả tài
khoản đích. [Đặc tả Swing đã lưu](FTMO-SYMBOL-AND-CLOCK-ADMISSION-20261108.md).

## Bắt đầu từ Challenge · 13 mốc đủ 12 tháng

| Size / swap | Qua P1 / P2 / payout đầu | Thưởng sau chia, mỗi sổ | Trung vị ngày qua P1 | Thiếu P1 / P2 tại cuối kỳ, USD | Daily / Static / Peak DD lớn nhất |
| --- | ---: | ---: | ---: | ---: | ---: |
| 10k SYM | 4/13 · 0/13 · 0/13 | 0 USD | 215,35 | 1.527,64 / 1.259,52 | 1,236% / 7,943% / 14,305% |
| 10k ASYM | 5/13 · 0/13 · 0/13 | 0 USD | 212,85 | 1.165,20 / 1.299,68 | 1,197% / 7,997% / 14,369% |
| 25k SYM | 3/13 · 0/13 · 0/13 | 0 USD | 240,85 | 2.919,48 / 3.245,89 | 1,304% / 7,989% / 14,579% |
| 25k ASYM | 6/13 · 0/13 · 0/13 | 0 USD | 226,85 | 3.640,43 / 3.240,79 | 1,245% / 8,022% / 14,188% |
| 50k SYM | 4/13 · 0/13 · 0/13 | 0 USD | 256,35 | 6.327,59 / 6.087,23 | 1,341% / 7,901% / 14,468% |
| 50k ASYM | 6/13 · 0/13 · 0/13 | 0 USD | 226,85 | 7.306,33 / 6.447,87 | 1,280% / 7,936% / 14,276% |

Thiếu P1/P2 là trung vị tới số dư mục tiêu trong các sổ dừng ở chính
pha đó. Thời gian tới P2 và payout đầu chưa quan sát được. Trong các
sổ tới P2 ở 10k/25k, thiếu hụt trung vị cuối kỳ là **12,60–13,00%**
vốn đầu, dù mục tiêu pha chỉ 5%. 0 đường breach quan sát được. Cả
78/78 cửa sổ có vị thế chạm ít nhất một trong 148 khoảng đường giá Gold
chưa xác định, 21–80 khoảng trong mỗi sổ. Static đo phần hụt so với
vốn đầu, còn Peak đo sụt giảm từ đỉnh equity. Phần ngoài quote quan sát
giữ bất định.

**Sổ 50k che khác biệt ở lot và pha.** 10k bị từ chối bởi lưới lot
25/28 lượt SYM/ASYM, gồm 15 lượt mỗi swap được nhận trong sổ 50k.
Ở 10k, 1.735/1.745 lượt chung dù có cùng risk theo tỷ lệ nhưng
khối lượng khác phép nhân 0,2 do lưới lot. Ở 25k, không có reject vì
lưới lot, nhưng vẫn có 1.139/1.100 lượt chung khác phép chia đôi
do làm tròn. Các số đếm tính theo cửa sổ và lặp cơ hội thị trường.
Ngoài tác động trực tiếp của lot, lãi/lỗ khác làm đổi throttle, guard
và ngày qua pha. Những lệch pha thực sự quan sát được so với 50k:

- **10k SYM** có mốc 02/2022 qua P1 ngày 06/09 thay cho 29/09/2022.
  Mốc 03/2022 thêm một lần qua vào 29/09/2022. Mốc 01/2023 mất
  lần qua 24/10/2023.
- **10k ASYM** có mốc 01/2022 và 02/2022 qua ngày 06/09 thay cho
  29/09/2022. Mốc 01/2023 mất lần qua 13/10/2023.
- **25k SYM** có mốc 01/2023 mất lần qua 24/10/2023.
  **25k ASYM** có mốc đó vẫn qua nhưng trễ từ 13/10 tới 20/10/2023.

## Bắt đầu đã ở Funded

Mỗi năm ở bảng dưới là một sổ Funded riêng bắt đầu ngày 01/01.
Không mang lợi nhuận, vốn hay ngày đủ điều kiện từ Challenge.
Đếm tháng theo UTC. Mỗi bộ số theo thứ tự **kỳ thưởng / USD của trader
sau chia 80% / tháng 0 / chuỗi tháng 0 dài nhất**.

| Size / swap | 2022 | 2023 |
| --- | --- | --- |
| 10k SYM | 9 / 577,53 / 6 / 3 | 5 / 590,20 / 8 / 4 |
| 10k ASYM | 9 / 627,84 / 6 / 3 | 5 / 626,96 / 8 / 4 |
| 25k SYM | 9 / 1.343,79 / 6 / 3 | 5 / 1.621,36 / 8 / 4 |
| 25k ASYM | 10 / 1.489,87 / 5 / 2 | 6 / 1.751,42 / 7 / 4 |
| 50k SYM | 9 / 2.644,34 / 6 / 3 | 6 / 3.306,25 / 7 / 4 |
| 50k ASYM | 10 / 2.909,94 / 5 / 2 | 6 / 3.550,89 / 7 / 4 |

Kỳ thưởng đầu của sổ Funded ở khoảng ngày 42 trong 2022 và ngày
80–81 trong 2023, tính từ đầu sổ. Ở 10k/25k, có 5–8 tháng 0 mỗi năm
và chuỗi có thể dài tới 4 tháng. V6 ghi thưởng ngay khi đến hạn, flat
và đủ lãi. FTMO hiện yêu cầu ngày 14 sau lệnh đầu, đóng vị thế và
pending, qua review. Mặc định chia 80% cho 2-Step, 90% khi đủ điều kiện.
Mức tối thiểu lãi đóng công khai là 20 USD với một số kênh và 50 USD
với crypto. Các con số trên giữ điều kiện 20 USD và 80% của phép
mô phỏng, chưa dự phòng review hay chọn kênh khác.
[Điều kiện Reward FTMO](https://ftmo.com/faq/how-do-i-withdraw-my-profits/).

## Tiền của người bắt đầu thi và bước quyết định

Bảng giá CFD 2-Step công khai cho vốn USD niêm yết từ **€89 / €250 /
€345** cho 10k / 25k / 50k. Trước đây owner thấy Swing chỉ hiện 10k và
25k khi chọn USD/MT5. Bảng công khai chưa xác minh checkout hiện tại
của owner. Hạch toán một lần đóng phí đầu mỗi kịch bản thử. Sau 12 tháng
mọi sổ đều **0 USD thưởng, 0 EUR hoàn**, nên dòng tiền trước tỷ giá
là **−€89, −€250 hoặc −€345** theo giá tham chiếu, tùy size. Mỗi cửa
sổ là một kịch bản độc lập cho một lần thi. FTMO công bố hoàn phí 2-Step
cùng lần rút Reward đầu, và thời gian đánh giá không giới hạn. Phí ở
đây là **chưa thu hồi tại cutoff**. Các sổ hết kỳ quan sát, chưa giả
định thất bại và mua lại.
[Giá 2-Step](https://ftmo.com/en/2-step-challenge/) ·
[Hoàn phí lần rút đầu](https://ftmo.com/faq/is-the-entry-fee-refunded/) ·
[Ghi nhận Client Area cũ](PROP-FIRM-FIT-20261102.md).

Khoảng trống lớn nhất là khả năng **từ P2 đi tới Reward đầu** ở đúng
quy mô 10k/25k trong thời gian người vận hành chấp nhận. 78 sổ tái tính
đều chưa qua P2 trong nhóm đủ 12 tháng. Lợi nhuận trong sổ bắt đầu đã Funded chưa trả lời được
bài toán đó. Giữ được nguồn Gold đủ kín và chứng minh có đóng góp ổn
định sau phí ở P2 là điều kiện để tin vào kết quả tính sau này.

Receipt ở ai-engine-jobs/prop-v4-harvest-capital-20261119 trên ổ E.
Private adapter chỉ đổi các hằng số USD theo danh sách đã kiểm trong
các bản module cô lập, dùng nguyên replay V6 và không sửa mã runner
trong repo. Tái lập 26/26 sổ 50k với entry, exit, số tiền, pha, DD và
gap đúng receipt. Tái kiểm 90 sổ và 18.402 admissions bằng Decimal,
11 tests V6 đạt. Một traversal gồm 70.871.030 cập nhật quote, chỉ
dùng dữ liệu 2022–2023 và giữ các khoảng thiếu.

## Bổ sung · 11 mốc bắt đầu muộn trong 2023

Chạy đủ 11 đầu tháng từ 02 đến 12/2023, dừng trước 00:00 UTC
01/01/2024. Giữ 13 mốc cũ ở đúng giới hạn 12 tháng và dùng nguyên
cấu hình A, size, costs, rule và 148 khoảng Gold chưa xác định.
Cả 66 sổ mới và 78 sổ cũ đều gặp ít nhất một khoảng Gold khi có
vị thế. Bất định giá trong các khoảng đó khác với thời gian quan sát
bị ngắn. Không quan sát thấy breach trong mô hình. Dữ liệu sử dụng
kết thúc năm 2023. Không dùng Reward được báo sau 2023 trong các
nghiên cứu dài hơn.

**Chỉ các mốc đủ quan sát.** Mỗi ô đếm lần qua P1 / P2 / Reward đầu
trước chân trời, trên 22 mốc đủ 3 tháng, 19 đủ 6 tháng và 13 đủ
12 tháng. Cộng tháng theo lịch, hạn là mốc loại trừ. Giữ mọi sổ đủ
thời gian trong mẫu số, kể cả sổ lỗ.

| Size / swap | 3 tháng / 22 | 6 tháng / 19 | 12 tháng / 13 |
| --- | ---: | ---: | ---: |
| 10k SYM | 2 / 0 / 0 | 3 / 0 / 0 | 4 / 0 / 0 |
| 10k ASYM | 3 / 0 / 0 | 5 / 0 / 0 | 5 / 0 / 0 |
| 25k SYM | 2 / 0 / 0 | 3 / 0 / 0 | 3 / 0 / 0 |
| 25k ASYM | 4 / 0 / 0 | 5 / 1 / 0 | 6 / 0 / 0 |
| 50k SYM | 2 / 0 / 0 | 3 / 0 / 0 | 4 / 0 / 0 |
| 50k ASYM | 4 / 0 / 0 | 5 / 1 / 0 | 6 / 0 / 0 |

**Toàn bộ 24 mốc.** Mỗi ô lần lượt là **đã tới / biết chưa tới khi
hết hạn hoặc đã breach / thiếu thời gian nên còn chưa biết**.
Một mốc ngắn vẫn có thể ghi nhận sự kiện xảy ra trước khi hết dữ liệu.
Các nhóm được phân loại riêng cho từng đích.

| Size / swap | P1 · 3 tháng | P1 · 6 tháng | P1 · 12 tháng | P2 · 3 tháng | P2 · 6 tháng | P2 · 12 tháng |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 10k SYM | 2 / 20 / 2 | 5 / 16 / 3 | 10 / 9 / 5 | 0 / 22 / 2 | 0 / 19 / 5 | 2 / 13 / 9 |
| 10k ASYM | 3 / 19 / 2 | 7 / 14 / 3 | 12 / 8 / 4 | 0 / 22 / 2 | 0 / 19 / 5 | 2 / 13 / 9 |
| 25k SYM | 2 / 20 / 2 | 5 / 16 / 3 | 9 / 10 / 5 | 0 / 22 / 2 | 0 / 19 / 5 | 2 / 13 / 9 |
| 25k ASYM | 4 / 18 / 2 | 7 / 14 / 3 | 13 / 7 / 4 | 0 / 22 / 2 | 1 / 18 / 5 | 3 / 13 / 8 |
| 50k SYM | 2 / 20 / 2 | 5 / 16 / 3 | 10 / 9 / 5 | 0 / 22 / 2 | 0 / 19 / 5 | 2 / 13 / 9 |
| 50k ASYM | 4 / 18 / 2 | 7 / 14 / 3 | 13 / 7 / 4 | 0 / 22 / 2 | 1 / 18 / 5 | 3 / 13 / 8 |

Reward đầu giống nhau ở cả sáu tổ hợp. Sau 3 tháng là **0 / 22 / 2**,
sau 6 tháng **0 / 19 / 5** và sau 12 tháng **0 / 13 / 11**.
Các cửa sổ dùng chung nhiều tháng dữ liệu. Đây là số đếm trên lịch sử
quan sát, chưa dự báo xác suất từng đường trong tương lai.

### Đường Funded đã quan sát và lý do chưa có Reward

Mọi sổ qua hai vòng đều qua P1 **29/09/2023 13:14:42 UTC**,
qua P2 **20/10/2023 20:30:00 UTC**. Với mốc tháng 2, tháng 3
và tháng 7, thời gian từ lúc bắt đầu tới P2 lần lượt **261,85 /
233,85 / 111,85 ngày**. Sau P2 còn **72,15 ngày** quan sát,
trong đó **55,67 ngày** sau khi đủ điều kiện chờ. Lệnh đầu ở Funded
ngày **23/10 08:00 UTC**, đủ 14 ngày vào **06/11 08:00 UTC**.
Tất cả sổ Funded đều flat và đang lỗ tại thời điểm đó.
Đỉnh số dư flat trước hạn vào 24/10 và sau hạn vào 10/11.

| Size / swap | Tháng bắt đầu đã qua P2 | Lãi flat cao nhất trước hạn | Lãi/lỗ flat ngay khi đủ 14 ngày | Lãi/lỗ flat tốt nhất sau hạn | Số dư cuối, USD |
| --- | --- | ---: | ---: | ---: | ---: |
| 10k SYM | 02, 03/2023 | +31,28 USD | −117,60 USD | −3,17 USD | 9.770,64 |
| 10k ASYM | 02, 03/2023 | +31,23 USD | −117,65 USD | +3,78 USD | 9.779,34 |
| 25k SYM | 02, 03/2023 | +80,08 USD | −321,33 USD | −34,19 USD | 24.318,70 |
| 25k ASYM | 02, 03, 07/2023 | +79,93 USD | −321,48 USD | −16,14 USD | 24.343,70 |
| 50k SYM | 02, 03/2023 | +143,29 USD | −662,04 USD | −53,99 USD | 48.607,87 |
| 50k ASYM | 02, 03, 07/2023 | +142,94 USD | −662,39 USD | −15,14 USD | 48.661,87 |

Các sổ từng có lãi đóng trên 20 USD lúc chưa đủ thời gian chờ.
Sau hạn, số dư flat cao nhất vẫn dưới mức **vốn đầu +20 USD**.
Reward và hoàn phí ghi nhận đều bằng 0 tới cutoff. Với sổ bắt đầu
muộn, chưa biết kết quả vào đúng ngày đủ 12 tháng.

Đối chiếu 22 sổ 50k muộn với V4 Development khớp toàn bộ dòng
lệnh trước và sau Funded, thời điểm chuyển pha, số dư cuối, Reward.
Các mốc 50k qua P2 tái lập đúng mốc đã công bố của V4/V6 trong
đoạn đến hết 2023. Trong từng tổ hợp size/swap, các mốc qua P2
khớp cả trạng thái sau reset, chuỗi lệnh, equity ở reset và payout
sau khi vào Funded. Giữa cả sáu tổ hợp, chúng cùng 40 định danh
lệnh Funded và một thời điểm chuyển pha. Có **một đợt lịch sử**,
chưa có đợt lặp độc lập. 10k mất riêng mốc tháng 7 ASYM mà 25k/50k
còn giữ, nhưng giảm vốn không làm đợt nào đi hết tới Reward.
[V4 lịch sử](PROP-COCORE-V4-RESULTS-20261114.md) ·
[V6 lịch sử](PROP-V4-HARVEST-V6-RESULTS-20261115.md).

Private receipt tại ai-engine-jobs/prop-v4-harvest-late-starts-20261119
trên ổ E. SHA256 khóa phương án và dữ liệu, 66 sổ chạy lại từ
26.494.991 cập nhật quote. Đối soát cash qua 144 sổ gộp, kiểm lại
trạng thái flat và lãi đóng tại hạn Reward trên 14 lượt qua hai vòng.
Kết quả sổ Funded từ đầu ở mục trước tiếp tục là phép đo riêng.

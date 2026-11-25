# Nhịp 1 — Kết quả sàng lọc tín hiệu và đối soát giá thiếu

18/11/2026. **Gác cả hai cơ chế.** Hai công thức đều đủ tín hiệu thô,
nhưng lợi nhuận trung bình sau phí stress âm trong cả sáu năm ở cả hai
chân trời. Cổng ma sát cũng loại quá nửa tín hiệu ở từng năm. BASE_GUARD
tiếp tục là danh mục đối chứng. [Task](PROP-STAGE0-NEXT-SLEEVE-TASK.md) ·
[Protocol khóa tại `50b757d`](PROP-N1-PROTOCOL-20261118.md)

## 1. Tín hiệu có đi đúng hướng sau phí không?

Mẫu Development 2018–2023. Markout đo mức giá đi theo chiều tín hiệu
từ lúc vào đến sau 4 giờ, đã trừ phí stress. Mốc 2 giờ dùng chẩn đoán.
Mỗi tín hiệu là một ngày riêng trong từng cơ chế. SL tự nhiên dùng để
đo bậc độ lớn. Đường giá giữa hai đầu mốc chưa được chạy qua SL.

**N1-GOLD-EQUITY.** Mua vàng sau giờ đầu phiên Mỹ nếu US500 giảm ít nhất
0,25% trong giờ đó. Đơn vị tiền trong bảng là USD/oz.

| Năm | Giờ có đủ dữ liệu / lịch | Tín hiệu có giá 4h / thô | Tháng trống | Ngày ngoài BASE | SL trung vị | Ma sát/SL | Qua cổng phí | Phí TB | Net TB 4h | Net TB 2h | Khoảng bootstrap 95% của TB 4h |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2018 | 244/258 | 44/46 | 0 | 36 | 2,05 | 36,9% | 2,2% | 0,756 | −0,380 | −0,026 | [−1,579; +0,605] |
| 2019 | 245/258 | 40/40 | 0 | 30 | 3,87 | 19,6% | 17,5% | 0,758 | −1,490 | −1,058 | [−3,206; +0,096] |
| 2020 | 249/259 | 57/57 | 0 | 39 | 5,11 | 14,9% | 28,1% | 0,763 | −1,227 | −1,344 | [−4,282; +1,566] |
| 2021 | 251/258 | 49/50 | 0 | 39 | 4,28 | 17,8% | 34,0% | 0,763 | −0,327 | −0,245 | [−1,898; +1,204] |
| 2022 | 258/258 | 85/86 | 0 | 65 | 3,94 | 19,4% | 27,9% | 0,763 | −0,098 | −0,031 | [−1,738; +1,571] |
| 2023 | 251/257 | 47/47 | 0 | 38 | 4,49 | 17,0% | 31,9% | 0,765 | −0,809 | −1,039 | [−2,905; +1,593] |

**N1-EUR-PEERS.** Giao dịch EURUSD theo chiều GBPUSD và AUDUSD khi hai
cặp cùng đi mạnh và EURUSD mới đi được tối đa một nửa. Lấy giờ H1 đủ
dữ liệu và đủ điều kiện đầu tiên quan sát được. Đơn vị trong bảng là pip.

| Năm | Giờ có đủ dữ liệu / lịch | Tín hiệu có giá 4h / thô | Tháng trống | Ngày ngoài BASE | SL trung vị | Ma sát/SL | Qua cổng phí | Phí TB | Net TB 4h | Net TB 2h | Khoảng bootstrap 95% của TB 4h |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2018 | 2.319/2.322 | 44/45 | 0 | 42 | 13,95 | 13,6% | 37,8% | 1,90 | −1,205 | −1,566 | [−11,949; +8,019] |
| 2019 | 2.318/2.322 | 50/51 | 1 | 38 | 9,75 | 19,5% | 11,8% | 1,90 | −2,156 | −5,514 | [−8,991; +4,453] |
| 2020 | 2.329/2.331 | 117/117 | 1 | 95 | 12,50 | 15,2% | 29,1% | 1,90 | −3,833 | −2,036 | [−10,676; +2,580] |
| 2021 | 2.314/2.322 | 100/100 | 0 | 76 | 9,85 | 19,3% | 12,0% | 1,90 | −3,719 | −4,030 | [−8,092; +0,761] |
| 2022 | 2.320/2.322 | 105/105 | 0 | 83 | 13,90 | 13,7% | 41,0% | 1,90 | −5,170 | −4,463 | [−12,165; +2,958] |
| 2023 | 2.312/2.313 | 96/96 | 0 | 70 | 11,75 | 16,2% | 24,0% | 1,90 | −0,036 | −0,240 | [−5,178; +4,840] |

- **Tần suất.** Vàng có 326 ngày tín hiệu, 247 ngày nằm ngoài ngày vào
  lệnh của BASE_GUARD theo UTC. EURUSD có 514 và 404 tương ứng. Hai cơ chế
  đạt sàn 40 tín hiệu thô mỗi năm. Số ngày bổ sung đo thời điểm có cơ hội,
  còn giá trị bổ sung của chúng cần lợi thế sau phí và replay danh mục.
- **Kinh tế.** Cả hai gắn `ECONOMIC_FAIL`. Cửa chính cần net trung bình
  dương và ít nhất bằng phí stress trung bình, ma sát trung vị không quá
  12% SL trung vị, và ít nhất 50% tín hiệu thô đạt cổng phí. Cả hai trượt
  các điều kiện này trong toàn bộ sáu năm. Một mốc gần hòa vốn vẫn cách
  cổng khá xa. Khoảng bootstrap 95% theo tuần ở mốc chính đều chứa số 0.
  Các phân vị 10/50/90 và số mẫu từng chân trời lưu trong JSON của job.
- **Độ phủ.** Mốc +4h có giá cho 322/326 mẫu vàng và 512/514 mẫu EURUSD.
  Với sàn 99% từng năm, vàng gắn thêm `DATA_PATH_INCOMPLETE` năm 2018,
  2021, 2022 và EURUSD năm 2018, 2019. Mẫu thiếu định giá gồm khả năng quá
  guard lịch hoặc thiếu điểm giá trong 60 giây. Phễu đầu vào đủ
  1.498/1.548 giờ vàng–US500 và 13.912/13.932 giờ EURUSD–GBPUSD–AUDUSD.
- **Chi phí.** V14 dùng spread Ask mô phỏng cố định 0,338 USD/oz với
  XAUUSD và 1 pip với EURUSD. Vàng cộng 0,40 USD/oz trượt giá vòng lệnh
  và commission 0,0007% mỗi chiều. EURUSD cộng 0,9 pip commission và
  trượt giá mỗi vòng. Báo cáo dùng các giả định stress này và mức spread
  proxy để đánh giá quy mô, chưa đo spread biến thiên hay khớp lệnh FTMO.

## 2. Khoảng thiếu giá nào có thể đổi kết quả BASE_GUARD?

Ghép bốn sổ Development từ V19 theo chiến lược và sự kiện nguồn. Giữ số
lot làm tròn xuống theo mức rủi ro 150 USD của sổ PRIMARY và dùng cùng số
lot cho STRICT. Xếp khoảng theo chênh PnL lớn nhất của lệnh chồng lên nó
giữa PRIMARY và STRICT qua hai thứ tự nến OLHC/OHLC. STRICT là kịch bản
thử sức chịu đựng khi thiếu đường giá. Chênh lệch phản ánh mức nhạy của
lệnh với kịch bản đó, và không xác định phần tác động của từng phút.

Có **43 khoảng riêng trên 25 lệnh** trong Development, ghép đủ hai thứ
tự. 39 khoảng gắn với một lệnh kém hơn trong STRICT. Bốn khoảng có chênh
bằng 0. Toàn bộ 10 khoảng đứng đầu thuộc **ba lệnh EURUSD F5**. Ở cả hai
thứ tự, ba lệnh thoát theo thời hạn ở PRIMARY và chạm SL giả định ở STRICT.

| Ngày UTC | Các phút thiếu UTC, xếp theo tác động của lệnh | Lệnh mở UTC | PRIMARY − STRICT mỗi lệnh |
|---|---|---|---:|
| 2021-07-14 | 04:19, 20:18 | 04:00 | 661,20 USD |
| 2021-05-26 | 19:38, 20:19 | 08:00 | 481,06 USD |
| 2022-01-03 | 04:11, 04:39, 04:44, 05:12, 06:02, 06:47 | 04:00 | 391,68 USD |

Mười khoảng đều còn thiếu. Chênh tổng của ba lệnh là 1.533,94 USD trong
đối chiếu cố định, tính mỗi lệnh một lần. Lượt rà dùng tên file và metadata
trong job V20–V26 cùng evidence của lane solo ở chế độ chỉ đọc:

- V26 MFI dùng thống kê H1 có gốc từ bộ tick EURUSD cũ. Log V19 xác nhận
  chính CSV 2021 và 2022 đã được đọc trong các cửa sổ cần thiết và cho
  0 dòng. Cả 10 khoảng cũng có `NO_ADMITTED_HOUR` trong manifest tick V19.
- Các Parquet observer V20 là artifact quan sát hoặc replay có sẵn.
  Hồ sơ V21–V26 không chỉ ra một feed tick mới cho ba ngày trên. Các thư
  mục tick trong evidence lane solo thuộc GBPUSD. Audit lịch XAU ở lane
  đó dựa vào timestamp và lịch phiên, chưa bổ sung Bid/Ask EURUSD.
- **0 nguồn giá mới đạt điều kiện để mở, 0 quote bổ sung, 0 chứng nhận
  đường giá mới.** Kết quả áp dụng cho phạm vi kiểm cục bộ của nhịp này.
  [Đối soát V19](ASYMMETRIC-RECOVERY-V19-RESULTS-20261116.md)

## 3. Bàn giao

**Quyết định duy nhất là gác nhóm cơ chế vừa thử.** Kết quả này chưa đưa
ra một ứng viên cho Nhịp 2 và chưa giảm bất định đường giá của BASE_GUARD.
Chương trình vẫn ở `NOT_QUALIFIED` cho mục tiêu Challenge. Những file
giá Development có sẵn phần đầu từ 2017. Tín hiệu, điểm định giá và
sổ so PnL đều thuộc 2018–2023. Tập giá 2024–2026 nằm ngoài lượt chạy.

Đã kiểm 29 test hiện có của scanner, bộ đọc nguồn và gap replay, bảy
assertion tổng hợp về biên giờ và trigger, cùng đối soát 840 tín hiệu ở
cả hai chân trời về hash, số đếm từng năm, markout, qua phí và mốc UTC.
Đã giải nén và kiểm SHA256 gốc/nén của bốn bảng tín hiệu và bảng xếp hạng.
Bằng chứng cục bộ nằm dưới `execution-v1/prop-n1-stage0-20261118/`.

| Artifact | Nhánh job | SHA256 của JSON hoặc manifest |
|---|---|---|
| `registration.json` | `screen/749687b9be70` | `d23d5c62259a0a5eac6f94a61603365313afe2a5a9323b4a93c9262e0367ec3f` |
| `screen-results.json` và bốn bảng tín hiệu có manifest riêng | `screen/749687b9be70` | `d35f19f4dd2215b1565f14b4bfdb52443ac44b54a380eb3ab0fdecd3aaf1331e` |
| `gap-ranking.json.zst` và `gap-ranking-manifest.json` | `gaps/749687b9be70` | `becdd11182a709caa3cf2ed257ae73c59d918225fa6b07952eff696dfc60414f` |

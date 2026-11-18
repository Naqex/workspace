# EURUSD phiên Mỹ theo lợi suất hai năm — trượt Stage‑0

**Gác công thức.** Có 988 tín hiệu thô và 987 tín hiệu có giá. Chỉ
342/988 tín hiệu qua cổng phí theo đúng chiều được chọn trước entry.
Net markout trung bình đạt ngưỡng kinh tế ở 2/6 năm. Công thức được
khóa ở `658290e` trước khi đọc dữ liệu nguồn hay đo kết quả.
[Protocol](PROP-EURUSD-US-RATES-PROTOCOL-20261118.md)

Tại 10:30 New York, lợi suất Mỹ hai năm tăng ít nhất 2 bp giữa hai
quan sát trước ngày giao dịch thì chọn SELL EURUSD, giảm ít nhất
2 bp thì chọn BUY. Giá được đo lúc 14:30 và tính phí stress 1,9 pip
gồm spread mô phỏng. Đây là markout đến mốc đã khóa. Stop tự nhiên
chỉ dùng để đo quy mô ma sát ở bước này.

| Năm | Phiên | Thiếu lợi suất / dưới ngưỡng | BUY / SELL | Thiếu endpoint / stop | Rớt phí | Qua phí | SL trung vị (pip) | Net TB (pip) | Net TB nhóm qua phí (pip) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2018 | 248 | 2 / 96 | 63 / 87 | 0 / 0 | 106 | 44 (29,3%) | 10,95 | +0,006 | −5,59 |
| 2019 | 249 | 0 / 66 | 99 / 84 | 0 / 2 | 145 | 36 (19,7%) | 8,70 | −2,53 | +0,06 |
| 2020 | 251 | 0 / 137 | 68 / 46 | 0 / 0 | 65 | 49 (43,0%) | 13,20 | +2,62 | +6,91 |
| 2021 | 251 | 0 / 140 | 48 / 63 | 0 / 0 | 92 | 19 (17,1%) | 7,90 | +0,45 | +1,33 |
| 2022 | 250 | 0 / 35 | 84 / 131 | 0 / 0 | 109 | 106 (49,3%) | 15,70 | +3,41 | +3,91 |
| 2023 | 248 | 0 / 33 | 97 / 118 | 1 / 1 | 125 | 88 (40,9%) | 12,30 | −3,24 | −1,82 |

- **Đủ số tín hiệu.** Từng năm có 111–215 cơ hội và ít nhất 99,5% có
  giá ở hai đầu mốc. Hai phiên đầu mẫu chưa đủ lịch sử lợi suất. Có
  507 phiên đứng ngoài vì lợi suất đổi dưới 2 bp. Một tín hiệu thiếu
  endpoint và ba tín hiệu có endpoint nhưng thiếu hình học stop.
- **Stop thường quá ngắn so với phí.** Với 1,9 pip và cap 12%, quy mô
  tối thiểu là 15,9 pip trên lưới 0,1 pip. Trung vị cả sáu năm nằm
  dưới mức đó. Ngay năm 2022, 106/215 đạt cap, vẫn dưới sàn 50%.
  Tổng cộng 642 tín hiệu có stop đo được và rớt phí.
- **Cổng kinh tế trượt cả trên tập thô và tập qua phí.** Tập thô
  đạt ngưỡng 1,9 pip chỉ năm 2020 và 2022. Sau khi xét phí/stop,
  nhóm đủ quy mô vẫn âm năm 2018 và 2023. Khoảng bootstrap tuần 95%
  của markout thô chứa 0 ở 5/6 năm. Năm 2023 nằm hoàn toàn phía âm
  [−5,89 đến −0,88 pip].

**Quyết định.** Giữ BASE_GUARD và `NOT_QUALIFIED`. Gác hướng dùng
thay đổi lợi suất hai năm qua ngày để chọn chiều EURUSD trong đúng
cửa sổ này. Tạm dừng quét thêm các tín hiệu cùng hình học stop một
giờ. Khi có cơ chế mới, ưu tiên đo cấu trúc stop và độ dài giữ lệnh
tương thích với phí trước khi chọn bộ dự báo hướng. Giữ cổng Stage‑0
và cả hai ca đối chứng cũ. Cổng đã trượt nên chưa có phép replay tài
khoản ghép hoặc số liệu thay đổi tỷ lệ qua vòng 1. Giá 2024–2026 vẫn đóng.
[Bằng chứng quy mô phiên Mỹ](PROP-SESSION-FEASIBILITY-RESULTS-20261118.md)

## Đối soát

40 test hiện có và sáu kiểm tra fixture đã pass. Đối soát đủ 1.497 phiên,
kiểm ngày quan sát lợi suất trước ngày lệnh. So 984 tín hiệu có đủ dữ liệu
chung với artifact phiên Mỹ trước đó, khớp cap phí và net markout theo đúng
chiều. Chuỗi 1.500 quan sát DGS2 dùng bản FRED tải hiện tại, chưa tái dựng
vintage từng ngày. Giá Ask của EURUSD là proxy cố định 1 pip.
[DGS2](https://fred.stlouisfed.org/series/DGS2) ·
[Lịch công bố H.15](https://www.federalreserve.gov/feeds/H15.html)

Artifact `execution-v1/prop-eurusd-us-rates-20261118/749687b9be70/`.
SHA256 `stage0-results.json` là
`a66cbd8d2067751b128619ea423ab4f0b628198c24bbb387eec8f89d9f9ea554`.
SHA256 `rates-session-rows-manifest.json` là
`7e80b2aa663a9ff51e0dd6d80a05b9da240404d6e58ba0a1107db898d772b293`.

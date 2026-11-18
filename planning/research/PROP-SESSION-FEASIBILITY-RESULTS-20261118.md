# EURUSD còn đủ ngày để xét tín hiệu trong cửa sổ Mỹ đã khóa

18/11/2026. **Trong phép đo 10:30–14:30 New York, EURUSD là tài sản duy
nhất có ít nhất 40 ngày thỏa ma sát/SL ở mọi năm Development.** Kết quả
chỉ cho phép ưu tiên thiết kế một tín hiệu mới trên EURUSD trong cửa sổ
này. [Phạm vi và công thức](PROP-SESSION-FEASIBILITY-20261118.md)

## Các ngày có stop đủ rộng

Đếm ngày mà **ít nhất một chiều** có phí stress không quá 12% khoảng
cách từ entry tới stop tự nhiên. Cột `Biên độ đủ` còn yêu cầu chiều đó
đã có markout net ≥ chi phí stress ở mốc 14:30. Cột này biết giá sau
sự kiện, chỉ mô tả dư địa và không phải kết quả của tín hiệu giao dịch.

| Năm | EURUSD qua phí / biên độ đủ | XAUUSD qua phí / biên độ đủ | US500 qua phí / biên độ đủ |
|---|---:|---:|---:|
| 2018 | 145 / 69 | 12 / 4 | 17 / 6 |
| 2019 | 80 / 43 | 39 / 19 | 9 / 3 |
| 2020 | 174 / 89 | 157 / 65 | 64 / 29 |
| 2021 | 107 / 45 | 135 / 55 | 57 / 28 |
| 2022 | 211 / 117 | 151 / 60 | 154 / 70 |
| 2023 | 179 / 89 | 143 / 59 | 40 / 20 |

EURUSD có **80–211 ngày/năm** mà ít nhất một chiều qua phí, nhưng chỉ
**1–30 ngày/năm** mà hai chiều đều qua. Chiều do tín hiệu chọn sẽ có
ảnh hưởng lớn tới số cơ hội thật. Báo cáo Stage‑0 tiếp theo phải tách
số lần rớt do hướng đã chọn khỏi số lần rớt vì tín hiệu không có lợi thế.
XAUUSD và US500 thiếu quy mô ở một số năm trong chính cửa sổ và công
thức stop này. Kết quả không áp dụng cho cửa sổ khác hoặc stop khác.

## Đường tiếp được chọn

Ưu tiên **EURUSD trong phiên Mỹ** với một cơ chế xác định hướng trước
khi áp cổng phí. Giữ cả F4 lẫn US500–VIX làm đối chứng từ hồ sơ cũ.
Trước khi dùng dữ liệu để chọn luật, ghi rõ nguồn lợi nhuận có thể kiểm
tra, giờ đã biết thông tin, cách vào và cách tính phí. Mọi công thức
mới chịu sàn 40 tín hiệu thô, độ phủ điểm định giá và cổng kinh tế
Stage‑0 đã khóa. Chỉ chuyển sang replay chung khi có ứng viên vượt cổng.
[Lộ trình](PROP-SYSTEM-ROADMAP.md)

Mẫu có 1.497 phiên cash đầy đủ trên lịch, trong đó EURUSD có đủ điểm
và giờ đầu ở 1.491 phiên, XAUUSD ở 1.494 và US500 ở 1.466. Các phiên
thiếu giữ trạng thái chưa định giá trong artifact. Kiểm tuple hai chiều
và fixture thiếu endpoint, rồi đối soát toàn bộ số đếm và cap 12% bằng
Decimal. Attempt đầu dừng do sai dạng timestamp; attempt hai đã sửa
đúng interface cost, giữ quy tắc. Giá 2024–2026 vẫn đóng.

Artifact `execution-v1/prop-session-feasibility-20261118/attempt-2/749687b9be70/`.
SHA256 `session-feasibility.json`
`164e43b12dd4687cd2decff94c7864075c55ba634dd00e86f96823fb7ea21eaf`.

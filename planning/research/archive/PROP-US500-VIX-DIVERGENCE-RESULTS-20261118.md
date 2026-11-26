# US500 và VIX cùng chiều phiên trước — kết quả Stage‑0

18/11/2026. **Gác `US500-VIX-DIVERGENCE-B0`.** Cả sáu năm Development có
đủ tín hiệu thô, nhưng năm năm âm sau phí. Năm duy nhất dương vẫn dưới
mức ma sát yêu cầu. Chỉ 31/313 tín hiệu qua cổng phí. Không có ứng viên
để chuyển sang replay. [Công thức khóa tại `ca2fe5f`](PROP-US500-VIX-DIVERGENCE-PROTOCOL-20261118.md)

## Phép thử

Khi US500 và VIX cùng tăng giữa hai phiên liền trước, giả thuyết dự báo
US500 giảm trong phiên sau. Khi cùng giảm, giả thuyết dự báo US500 tăng.
Đo từ open M1 quanh 10:30 New York đến sau 4 giờ, trước cash close.
Stop tự nhiên dùng đáy/đỉnh của giờ đầu phiên để so độ lớn với phí.
Không mô phỏng chạm stop hoặc chạy sổ lệnh.

VIX đo biến động kỳ vọng từ quyền chọn SPX. Dữ liệu khóa đầu vào là
1.521 giá đóng cửa VIXCLS có giá trị từ 02/01/2018 đến 29/12/2023, tải
qua truy vấn FRED giới hạn cứng. VIX theo ngày có thể dùng giờ chốt khác
CFD. Quan sát từ hai phiên đã kết thúc, giữ ngày nghỉ và phiên đóng sớm
của NYSE. Nguồn VIX là bản dữ liệu tải hiện tại, chưa tái lập bản phát
hành từng ngày. [Cboe](https://www.cboe.com/tradable_products/vix/faqs) ·
[FRED, CSV 2018–2023](https://fred.stlouisfed.org/graph/fredgraph.csv?id=VIXCLS&cosd=2018-01-01&coed=2023-12-31)

Giá US500 dùng M1 Bid/Ask có nguồn V11. Phí stress 2,50 điểm/vòng ngoài
spread, gồm 1,00 điểm commission và 1,50 điểm slippage. Spread đã phản
ánh qua giá vào/ra. Đây là biểu phí nghiên cứu kế thừa, chưa đối chiếu
với dịch vụ đích. Giá BID/ASK mở nến là đại diện cho giá khớp tại mốc đo.

## Kết quả theo năm

Các cột giá, phí và markout tính theo điểm US500. BUY/SELL là số tín
hiệu thô. Khoảng 95% dùng bootstrap theo block tuần ở mốc 4 giờ.

| Năm | BUY / SELL | Có giá / thô | Có predictor | SL tự nhiên trung vị | Ma sát/SL | Qua cap 12% | Phí TB | Net markout TB 4h | Khoảng 95% |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2018 | 31 / 22 | 53/53 | 100,0% | 5,66 | 52,3% | 1,9% | 2,90 | −6,57 | [−11,44; −2,37] |
| 2019 | 19 / 28 | 47/47 | 100,0% | 4,31 | 64,0% | 0,0% | 2,81 | −4,86 | [−7,73; −1,92] |
| 2020 | 19 / 25 | 43/44 | 98,0% | 8,02 | 37,4% | 18,2% | 3,01 | −3,76 | [−11,90; +3,64] |
| 2021 | 20 / 27 | 47/47 | 100,0% | 8,20 | 36,2% | 6,4% | 2,89 | −1,15 | [−4,67; +2,36] |
| 2022 | 49 / 14 | 63/63 | 100,0% | 15,21 | 19,7% | 27,0% | 2,95 | −4,75 | [−14,25; +5,56] |
| 2023 | 29 / 30 | 59/59 | 99,2% | 8,36 | 36,0% | 3,4% | 3,00 | +0,83 | [−4,28; +5,98] |

**Tần suất.** 44–63 tín hiệu/năm, với một tháng trống trong 2020. Có
244/313 ngày tín hiệu nằm ngoài ngày vào lệnh của BASE_GUARD. Lượt đọc
sổ 150 USD risk chỉ để chẩn đoán độ bổ sung sau khi công thức đã khóa.
Trong các tháng BASE_GUARD lỗ, markout của 177 tín hiệu có giá trung
bình **−5,05 điểm**, so với −1,10 điểm từ 135 tín hiệu có giá trong
các tháng BASE_GUARD lãi. Đây là so sánh markout theo nhóm tháng đã
quan sát, chưa đo đóng góp của ứng viên vào tài khoản dùng chung.

**Kinh tế.** `ECONOMIC_FAIL` cả sáu năm. Năm 2023 +0,83 điểm sau phí
vẫn cách xa yêu cầu net ít nhất bằng 3,00 điểm ma sát trung bình. Tỷ
lệ phí/stop trung vị đều trên 12%, và tỷ lệ giữ mẫu cao nhất chỉ 27,0%.
Riêng năm 2022, stop tự nhiên rộng tới 15,21 điểm ở trung vị mà kết quả
vẫn âm. Công thức thiếu cả độ lớn stop phù hợp lẫn lợi thế định hướng
sau phí trong phạm vi đã thử.

**Nguồn.** `DATA_PATH_INCOMPLETE` ở 2020. Năm phiên thiếu ít nhất một
close US500 trước đó, dù VIX có đủ các ngày cần ghép. Một tín hiệu
thiếu endpoint, còn 43/44 tín hiệu định giá được. Năm 2023 thiếu hai
predictor nhưng vẫn qua sàn 99%. Không nội suy giá. Các năm khác có
đủ endpoint; chỉ hai tín hiệu có giá nhưng thiếu hình học stop hợp lệ.

## Bàn giao

Giữ BASE_GUARD làm đối chứng và giữ `NOT_QUALIFIED` cho Challenge.
Gác đúng công thức VIX vừa chạy, giữ cả kết quả âm trong lịch sử thử.
Không đổi chiều, ngưỡng, thời gian giữ hoặc mở thêm ứng viên trong
lượt này. Dữ liệu giá 2024–2026 nằm ngoài phạm vi.
[Yêu cầu cho ứng viên bổ sung](PROP-PHASE1-SHORTFALL-20261118.md)

Đã chạy 44 bài test có sẵn và sáu kiểm tra fixture cho tín hiệu, thứ tự
thời gian, chi phí, nguồn thiếu và chặn holdout. Đối soát 1.509 dòng
lịch và 312 tín hiệu có giá bằng công thức Decimal độc lập cho markout
và xác minh SHA256 của dữ liệu, protocol và artifact. [Mã tái lập](../../tooling/ai-engines/prop_us500_vix_divergence.py)

Bằng chứng nằm ở `execution-v1/prop-us500-vix-stage0-20261118/749687b9be70/`.

| Artifact | SHA256 |
|---|---|
| `VIXCLS-2018-2023.csv` | `bbbd82fa10c6f26c04d100e3d7bb71b2f6cf17db10eba90b4ad5988be59578bc` |
| `registration.json` | `929a7e3ad90ff037e4680241dac14925713a8aaa71370173c0ff18c002ddb6a4` |
| `stage0-results.json` | `c0668a9ca13de82d80199d4f64828199246c7c6443dd40e009a27f5743457f2f` |
| `session-observations-manifest.json` | `648e9782f27b80ae19080b48d7f75d7874f7e4620cebd5b6dff8b1173d7c2548` |

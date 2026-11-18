# Đối chiếu đủ 43 khoảng giá thiếu Development

18/11/2026. **HistData có tick trong 26/43 khoảng. Mức thiếu vòng 1 sau
12 tháng vẫn gần 4.700 USD khi giữ nguyên khối lượng trong sổ.** Đây là
đối chiếu khác nguồn giá, chưa chứng nhận dữ liệu hoặc kết quả tài khoản
đích. [Protocol](PROP-GAP-FULL-DEV-PROTOCOL-20261118.md)

## Các khoảng đã kiểm và lần phục hồi

| Tài sản | Khoảng đã rà | Có tick trong khoảng | Chưa thấy tick | Lệnh đủ giá để so toàn lệnh |
|---|---:|---:|---:|---:|
| EURUSD | 36 | 20 | 16 | 16/18 |
| XAUUSD | 7 | 6 | 1 | 2/7 |
| **Tổng** | **43** | **26** | **17** | **18/25** |

Có 990 tick trong 26 khoảng và không tick nào trong số đó chạm mức stop
hoặc mức bảo vệ gốc tại khoảng tương ứng trên HistData. Trong 18 phép
đo toàn lệnh, 17 lệnh thoát theo giờ và một lệnh EURUSD chạm stop ở
ngoài các phút thiếu. Hai lệnh EURUSD chưa định giá trọn đường vì thiếu
endpoint hoặc có đoạn trống hơn ba phút. Năm lệnh Gold F4 dùng stop động
P1, nên chỉ so ngưỡng đã ghi tại gap, chưa replay toàn lệnh. Giữ giá
gốc, chênh nguồn và các trường hợp không tìm thấy giá trong báo cáo.
[Đặc tả HistData](https://www.histdata.com/f-a-q/data-files-detailed-specification/)

Đã dùng ba archive cũ và tải 16 archive mới về kho tư nhân. Lần đầu đọc
được 42 khoảng. Archive vàng 10/2023 có một lần lùi timestamp ngày
29/10. Giữ nguyên archive và chỉ cho phép ngoại lệ đúng cặp timestamp
này khi so cửa sổ **02/10/2023**, xảy ra trước bất thường. Tìm thêm
86 tick trong khoảng đó. Hai phút kề có giá, với sai khác tuyệt đối
ở bốn trường Bid Open/Close từ 1,38 đến 2,13 USD/oz. Phép này xác minh
hiện diện và giá trong đoạn hẹp của HistData. Nó không xác minh thứ tự
phần còn lại của archive hoặc nguồn nào là giá của broker đích.

## Chênh lệch có giải quyết bài toán vòng 1 không?

Đặt PnL của 18 lệnh đã đối chiếu vào đúng dòng ở bảng tham chiếu risk
150 USD. PRIMARY đổi từ **+3.577,86** thành **+4.111,44 USD**, còn
STRICT đổi từ **−1.192,90** thành **+3.296,32 USD**. Đây là phép thay
số tiền trên bảng lệnh cố định. Các kết quả dương này không dùng để
tính lại drawdown, thời gian hay tỷ lệ vượt hai vòng.

Sau đó, tính riêng trên các cửa sổ chưa qua vòng 1. Giữ các quyết định
vào lệnh, chuyển pha và đúng số lot đã ghi nhận. Thay chênh PnL ở lệnh
có giá đối chiếu, rồi đọc khoảng cách từ số dư cuối 12 tháng tới 55.000
USD. Số dư ban đầu khớp từng cửa sổ tới cent. Phép tính giữ nguyên vị
thế và lịch sử trạng thái, nên chỉ đo độ nhạy số dư.

| Cohort cố định | Số cửa sổ | Thiếu trung vị trước | Thiếu trung vị sau | Số dư chạm mốc 55.000 USD sau điều chỉnh |
|---|---:|---:|---:|---:|
| PRIMARY | 55 | 4.929,17 USD | **4.712,35 USD** | 0/55 |
| STRICT | 58 | 5.870,60 USD | **4.744,54 USD** | 0/58 |

Giảm bất định nguồn có ích, nhất là với STRICT. Ngay cả phép so thuận
lợi hơn cho sổ tham chiếu vẫn còn thiếu khoảng 9,4% vốn ban đầu sau 12
tháng. Vì thế giải quyết path nên phục vụ độ tin cậy. Lợi nhuận mới
sau chi phí là điều kiện còn thiếu để tăng tốc.

## Rà lại bằng chứng về ứng viên

| Hồ sơ đã có | Quyết định hiện hành |
|---|---|
| [V13](PATH-RESOLUTION-AND-DEDUP-V13-RESULTS-20261115.md) | 19 cấu hình trọng tâm được định giá lại. Danh mục 3 nhánh còn 43 và 47 tín hiệu ở hai năm đầu, dưới sàn 50. Cohort đã chọn từ V12 và còn gap. |
| [V16](GAP-IMMUNE-MULTIASSET-V16-RESULTS-20261116.md) | 29 cấu hình Gold/EUR qua endpoint nhưng đều bị loại ở các cửa sau. US500 0/202 đạt, GBP/AUD thiếu path. Danh sách bổ sung rỗng. |
| [V26](BATCH-EXACT-ISO-V26-RESULTS-20261118.md) | Không có ứng viên corpus qua Stage‑0, ISO chưa cải thiện vòng đời chuẩn, GBP S01 đã gác. |
| [F4 và US500–VIX](PROP-REPLAY-REGRESSION-RESULTS-20261118.md) | Giữ F4 làm đối chứng dương hẹp, VIX là đối chứng âm. F4 thưa cơ hội và VIX rớt kinh tế. |

Không hồi sinh cấu hình từ bảng này. Giữ BASE_GUARD và `NOT_QUALIFIED`.
Ưu tiên nghiên cứu một nguồn lợi nhuận mới có sàn tần suất và ma sát
hợp lý trước khi code chiến lược. Chỉ mở lại gap cũ nếu có bằng chứng
đủ căn chỉnh với nguồn đích hoặc thử nghiệm toàn lệnh trên nguồn mới
có thể đổi một quyết định cụ thể.

## Kiểm và tái lập

76 kiểm thử hiện có và sáu kiểm tra fixture về timestamp và chi phí.
Kiểm hash archive phục hồi, cả hai manifest Zstd, 43 danh tính riêng và
113 cửa sổ ghép sổ. Không mở giá 2024–2026 hoặc chạy tài khoản broker.

| Artifact trong `execution-v1/prop-gap-full-dev-20261118` | SHA256 manifest |
|---|---|
| `749687b9be70/full-sensitivity-manifest.json` | `dd39d50a0e3d880421719a4ea23838ed947546fd45df02c88becedb010684fe7` |
| `followup/749687b9be70/source-followup-manifest.json` | `07ab010e5a7216c884f3bc2fe0120e04a5b735e00fcc47746aa491d0fe82d0c4` |

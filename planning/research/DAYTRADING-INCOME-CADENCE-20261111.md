# Daytrading làm nguồn thu chính: tần suất và các mức thu nhập

11/11/2026. Owner nhắc rõ cần đánh giá số lệnh/ngày/tuần theo mục tiêu daytrading
và nguồn thu chính. Owner **chưa chốt mức thu nhập**, yêu cầu so sánh nhiều mức.
Các con số dưới là kế hoạch và tính toán giả định, không dự báo R123 hoặc lời
hứa có payout. Không thay trading grant, risk hoặc số lệnh của batch đã khóa.

## Mục tiêu vận hành tạm thời để chọn ý tưởng

| Hạng mục | Mốc đề xuất cho campaign | Cách dùng |
|---|---|---|
| Lệnh hợp lệ mỗi tuần |3–8|Ưu tiên ý tưởng có đủ cơ hội quan sát/kiểm định; không quota|
| Một ngày thường gặp |0–2|Ngày không có setup thì0; không bắt buộc kiếm tiền mỗi ngày|
| Trong tháng minh họa4tuần |12–32|Chưa là dự báo số lệnh tháng tới|
| Thời gian giữ |Intraday, đóng trong phiên theo spec|Daytrading không đồng nghĩa ngày nào cũng phải trade|
| Edge |Lãi kỳ vọng sau đầy đủ costs, uncertainty và OOS|Không dùng số lệnh hoặc winrate riêng để chứng nhận|
| Risk |Giữ ưu tiên thấp;0,25% chỉ scenario đang nghiên cứu|Không tăng risk để bù ít lệnh hoặc thiếu thu nhập|

Dải3–8/tuần là **đề xuất của agent theo mục tiêu owner**, không chuẩn quỹ hoặc
con số đã được nghiên cứu chứng minh tối ưu. Thay đề xuất2–5/tuần trước đó về
fit khi owner nhấn mạnh nguồn thu chính; không sửa frozenprotocols lịch sử.
Không tự tăng cap1attempt/day của R123 thành2trades/day. Những giới hạn execution
và account-wide budget cần thiết kế riêng trước một phiên bản mới.

Mẫu lệnh cần trải qua nhiều thời kỳ và không phụ thuộc quá mạnh. Không cộng
variants/cost scenarios thành quan sát độc lập; không giảm chuẩn edge chỉ vì
cần thu nhập. Số lệnh cao có thể làm tăng tổng lỗ nếu expectancy âm.

## Giả định cho bảng thu nhập

- Chỉ xét giai đoạn **FTMO Account sau khi đã qua evaluation** và đáp ứng terms,
  không tính simulated profit trong Challenge thành tiền sinh hoạt.
- FTMO2-Step mặc định Reward Ratio80%, có thể90%khi đủ điều kiện; bảng dùng80%
  theo [FAQ chính thức](https://ftmo.com/en/faq/how-do-i-withdraw-my-profits/),
  kiểm11/11/2026. Accountcapital là vốn mô phỏng, không tiền owner sở hữu.
- Quy đổi minh họa1USD=25.000VNĐ, **không phải tỷ giá hiện hành**.
- Chi phí minh họa1triệuVNĐ/tháng gồm phân bổ challenge/retry/operations;
  chưa phải số chi thực tế. Chưa tính thuế/chênh lệch đổi tiền hoặc thanh toán.
- Vì chưa biết chi phí thực và nghĩa vụ thuế, “ròng” dưới đây chỉ nghĩa sau
  reward split và khoản chi giả định, không take-home đã được xác nhận.

`Thu nhập mô hình = lãi mô phỏng sau trading costs ×80% ×25.000 −1.000.000`.

| Mục tiêu mỗi tháng sau khoản chi giả định | Lãi mô phỏng cần có | Trên10k | Trên50k | Trên100k | Trên200k |
|---|---:|---:|---:|---:|---:|
|10triệuVNĐ|550USD|5,50%|1,10%|0,55%|0,275%|
|20triệuVNĐ|1.050USD|10,50%|2,10%|1,05%|0,525%|
|30triệuVNĐ|1.550USD|15,50%|3,10%|1,55%|0,775%|

Các account sizes chỉ là mẫu số của kịch bản, không xác nhận owner đã có/đủ
điều kiện mua hoặc vận hành các account đó. Tỷ suất trong bảng là **cần đạt**,
không lợi nhuận khả thi đã chứng minh. Không lấy bảng này ép bot phải đạt mỗi
tháng; sẽ có tháng âm/không reward, ảnh hưởng trực tiếp khả năng chi sinh hoạt.

## Cùng tần suất, vốn/edge khác nhau cho thu nhập khác nhau

Ví dụ giả định20lệnh/tháng, risk0,25%/lệnh, lợi thế sau trading costs0,1R/lệnh:

- Trên10k:1R=25USD →50USD lãi mô phỏng →40USD Reward →1triệuVNĐ;
  trừ1triệu chi giả định thì còn0.
- Trên100k:1R=250USD →500USD lãi mô phỏng →400USD Reward →10triệuVNĐ;
  trừ1triệu chi giả định thì còn9triệu.

Đây là phép nhân kỳ vọng, không phân bố thu nhập, xác suất sống sót/pass/payout
hoặc bằng chứng có strategy đạt0,1R. Trên100k/20lệnh/risk0,25%, mức10/20/30triệu
ở bảng trên cần bình quân khoảng0,11/0,21/0,31R/lệnh sau trading costs trước split.
Nhiều vốn chỉ scale một lợi thế đã có; với expectancy âm thì scale tổng lỗ.

## Đối chiếu với nghiên cứu hiện tại

[R123](US500-MA-RECLAIM-RESULTS-20261111.md) có165lệnh/3năm,58/50/57 từng năm,
khoảng1,1lệnh mỗi5phiên lịch. Nó chưa fit dải3–8/tuần và không bền qua costs:
tổng independentcentnet+4,83USD chuẩn,−307,03USD stress trên3sổ năm riêng.
Không dùng R123 làm mô hình thu nhập, không tăng lot hoặc chỉ giữ subgroup lời.

**Ưu tiên kế tiếp:** admission ý tưởng cần kiểm cả cơ chế/độ đúng, tần suất phù
hợp và lợi thế sau costs; economic screening nhỏ khác deep edge validation.
Giữ US500/M15 làm hướng chính theo owner, chưa tự mở rộng sản phẩm hoặc mua quỹ.

Số liệu máy đọc/assumptions đã lưu cùng campaign:
`execution-v1/us500-ma-reclaim-cost-screen-v1/income-cadence-scenarios.json`.
Đây là planning receipt, không tự thay numerical strategy protocol.

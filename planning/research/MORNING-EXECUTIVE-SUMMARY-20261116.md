# Báo cáo buổi sáng — chốt V16, V17 và V18

**Hệ thống kiểm định đã tiến bộ; chưa có chiến lược đủ bằng chứng để mua Challenge hoặc bật bot tự giao dịch Free Trial.** Mình không ép chọn một “Champion” khi đường giá còn chỗ chưa kiểm chứng.

## 1. Ba ca chạy đêm đã giải quyết gì?

V16 đưa danh mục về đóng trong ngày, tìm thêm nhiều nhánh nhưng không có nhánh mới đủ chuẩn. V17 thử chia mức cược hợp lý hơn và thêm dự phòng lỗ ngày; sụt vốn giảm nhưng chưa kiếm đủ nhanh. Cả hai vẫn còn đoạn giá thiếu chứng cứ.

V18 gom lại 17 chiến dịch, phân biệt bản cũ đo 3 năm với bản mới đo gần 9 năm; khóa một cách tuyển chọn, rồi chạy 5.000 chuỗi mô phỏng giữ nguyên diễn biến từng lệnh/quý và stress phí. Không tìm thêm tham số để cứu kết quả. V16 là bản tham chiếu tốc độ, V17 là dự phòng Funded **trong mô hình**; chưa bản nào được chứng nhận đủ an toàn. Các bản yếu và failed attempts đều được giữ.

## 2. Ổ cứng và tốc độ đã cải thiện bao nhiêu?

| Kho | Trước GiB | Nay GiB | Files nay |
|---|---|---|---|
| D | 208,59 | 197,23 | 575.771 |
| E | 319,68 | 215,00 | 557.620 |

Phần đọc được giảm ròng khoảng **116,04 GiB** và **156.924 tệp** so snapshot gốc có biên nhận. Không gọi toàn bộ chênh lệch này là “rác đã xóa”: đã có nén lạnh, dữ liệu mới phát sinh và những thư mục cần giữ. Riêng các đợt xóa cache/build có chứng cứ ghi nhận **153.058 lượt tệp**. Chưa đo lượng ổ đĩa vật lý thực sự giải phóng. Hai thư mục pytest của VI không đọc được vẫn được giữ nguyên.

Hiện có **1.153 bài test PASS, 0 skip**, giữ đủ toàn bộ 1.148 test cũ. Full suite chạy **22,062 giây**; V17 là 21,14 giây, trước đó V16 khoảng 28,23 giây. Smoke 10 lần, chậm nhất **0,853 giây**; **7/10 lần dưới 0,80 giây, chưa đạt yêu cầu 10/10**. Cả 10 lần đều chạy đúng chức năng; giữ nguyên các lần chậm và không thử lại để lấy chuỗi đẹp. Đây là tốc độ bài kiểm thử, chưa phải phép đo toàn máy hay tốc độ khớp MT5.

## 3. Sức mạnh thật của bản tốt nhất hiện tại

V16 có **42,30R** ở sổ tham chiếu 150 USD/lệnh sau phí, từ 2018 đến 13/10/2026. R là điểm lời/lỗ theo mức cược, không phải % lợi nhuận tài khoản. 2026 chưa đủ năm; có năm yếu/âm và đường giá chưa đủ chứng cứ. Sổ reference không có toàn bộ hạn mức/harvester của tài khoản.

Mô hình chính: **71/105** mốc xuất phát hoàn tất hai vòng, trung vị **47,08 tháng**, chỉ tính các mốc đã hoàn tất. Khi stress đoạn giá chưa kiểm chứng: còn **1/105**. Sổ tham chiếu tương ứng chuyển từ +42,30R thành **−5,05R**. Các 33 mốc bắt đầu từ 2024 đều chưa hoàn tất hai vòng ở kết quả gốc. 105 mốc chồng lấn không phải 105 bài thi độc lập.

Một sổ Funded 50k chạy riêng từ đầu mẫu mô phỏng **40 lần rút / 6.457,11 USD**. Tổng payout của nhiều mốc chồng lấn không phải thu nhập của owner. **Tiền payout thực nhận trong dự án vẫn bằng 0.**

Monte Carlo là 5.000 cách xếp lại quý lịch sử, dùng để nhìn độ nhạy; không phải lời hứa xác suất đậu ngoài thị trường:

| Thời gian | Qua vòng 1 — chính % | Qua cả 2 — chính % | Qua cả 2 — stress giá thiếu % |
|---|---|---|---|
| 12 tháng | 22,68 | 1,24 | 0,06 |
| 18 tháng | 39,22 | 6,08 | 0,40 |
| 24 tháng | 52,24 | 14,32 | 1,48 |
| 36 tháng | 67,88 | 33,36 | 4,54 |

Payout bình quân mỗi năm của sổ Funded mô phỏng: P25/P50/P75=**544,92/908,19/1.301,19 USD**. Đã tính cả các đường không rút được tiền. P50 nghĩa là một nửa đường mô phỏng thấp hơn mức đó, không phải thu nhập được bảo đảm. Chưa trừ phí mua/retry Challenge, vận hành hoặc thuế.

Phí tăng 50% làm số mốc hoàn tất hai vòng trên lịch sử gốc giảm từ 71 xuống **7/105**. Không đường mô phỏng nào chạm trần lỗ, nhưng điều đó chưa chứng minh rủi ro thực tế bằng 0.

Bảng phí 1,25×/1,50×, các năm thuận lợi/đi ngang, mức sụt vốn và tỷ lệ vi phạm nằm trong [báo cáo chi tiết](FINAL-CONVERGENCE-V18-RESULTS-20261116.md). Thiếu lịch news/đường giá và phí/fill tài khoản đích vẫn là điểm yếu thật; xáo trộn dữ liệu không tự lấp các lỗ hổng đó.

## 4. Sáng nay nên làm gì?

**Chưa mua Challenge và chưa bật bot tự gửi lệnh.** Có thể chuẩn bị một Free Trial đúng program để thu quote/spec và đối chiếu đồng hồ, sau khi tài khoản/binding được xác nhận. Điều khoản hiện hành chưa truy cập lại thành công; 14 ngày là mốc tham chiếu từ snapshot cũ/yêu cầu, cần kiểm trên Client Area.

Đã có [bộ spec cụ thể](FTMO-FREE-TRIAL-EXECUTION-SPEC-20261116.md): ba sleeve, SL/P1, giờ đóng, lot/risk, phí và log đối soát. Bộ này chưa phải EA. Muốn đo slippage phải có log gửi lệnh và khớp lệnh dưới quyền thực thi riêng; chỉ thu giá chưa đo được slippage. Cần hoàn tất adapter/parity, news guard và owner handover trước khi bật giao dịch chiến lược.

PR96 đã merge; PR97 giữ mở để xem kết quả và bằng chứng. Không đăng ký tài khoản mới, giao dịch broker, mua Challenge hoặc deploy trong đợt này. VI WIP và Trader pin giữ nguyên.

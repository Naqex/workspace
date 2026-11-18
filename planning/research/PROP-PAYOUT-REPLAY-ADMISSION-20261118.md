# Cửa quyết định cho một lượt replay bổ sung ở vốn 50.000 USD

Phạm vi định lượng mới chỉ Development 2018–2023, dùng sổ đã lưu.
Không thử tín hiệu, exit, tham số và phí mới. Giữ BASE_GUARD, lot
và ngân sách rủi ro hiện hành làm đối chứng. Tách sổ tham chiếu rủi
ro cố định khỏi sổ rolling có sizing và hạn mức account.

Phương án duy nhất chưa được kiểm là **giữ F5 + F4, thay Gold F3
bằng R043 nguyên bản cả BUY và SELL ở risk đã đo 125 USD**. Chỉ
thiết kế ở cấp ghép nhánh để kiểm mức khả thi. Hai nhánh còn lại
giữ nguyên. Không phân bổ lại risk F3 sang F5/F4/R043. Việc bỏ F3
riêng đã đo ở V23. Đổi trọng số đã đo ở V26. R043 riêng và
Gold/EURUSD tiền thân đã có hồ sơ, khác bản thay đúng F3 này.
Tái sử dụng các kết quả âm đó.

Khóa tiêu chí trước khi đọc các dòng R043 Development cho phép so.
Mức cần bổ sung cho một vai trò đủ lớn để dành lượt replay là
**ít nhất 1.000 USD/năm**, xấp xỉ một phần năm mức thiếu
4.873,10 USD của phép đo nhạy đã hiệu chỉnh. Đây là mức ưu tiên
nghiên cứu. Một nhánh có thể cung cấp một phần, và thiếu hụt gốc
của BASE ở PRIMARY vẫn là 4.929,17 USD trên 55 cửa sổ chưa qua.

1. Tính chênh kinh tế tĩnh `R043 stress − F3` theo từng năm và
   gộp sáu năm, ở risk đã đo và so cả F3 PRIMARY / STRICT. Điều
   kiện vào lượt tiếp ở mức tối thiểu là chênh bình quân đạt
   1.000 USD/năm ở cả hai, cùng bản thân R043 dương ở cả hai cụm
   2018–2020 và 2021–2023 dưới phí bảo thủ. Đây là phép định cỡ
   trước phí carry/overlap của danh mục, không là cận toán học
   của thay đổi admission hoặc prop pass.
2. Nếu có cơ sở về quy mô, kiểm lịch phiên và swap phù hợp, đường
   equity và reset, trùng lệnh Gold, giai đoạn có thể khớp cùng
   risk. Áp dụng các cổng qualification đang có. R043 là nhánh
   giữ nhiều ngày theo hồ sơ Swing, cần cùng account contract
   hợp lệ mới được ghép. Chỉ replay nếu vượt các cổng.
3. Nếu replay được, dùng cùng 61 cửa sổ đủ 12 tháng ở Development,
   cùng 50.000 USD và risk từng pha, cả PRIMARY và STRICT. Cần
   ít nhất hai cửa sổ qua cả hai vòng tăng thêm ở PRIMARY (khoảng
   3,3 điểm phần trăm) và ít nhất một ở STRICT. DD ngày và lỗ
   dưới vốn đầu không xấu hơn tương ứng. Xem thêm payout thực
   sự phát sinh sau khi vào funded và tháng trắng. Không nhân
   tỷ lệ đỗ với thu nhập của sổ đã Funded từ đầu.

[Kết quả thiếu hụt gốc](PROP-PHASE1-SHORTFALL-20261118.md) ·
[Đính chính độ nhạy](PROP-EUR-CLOCK-AND-TREASURY-AUCTION-RESULTS-20261118.md) ·
[V23](SLEEVE-ABLATION-MT5-V23-RESULTS-20261117.md) ·
[V26](BATCH-EXACT-ISO-V26-RESULTS-20261118.md)

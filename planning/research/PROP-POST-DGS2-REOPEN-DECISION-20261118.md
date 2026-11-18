# Quyết định sau DGS2 — gác lượt tìm setup hiện tại

**Chưa có setup đủ cơ sở để đăng ký một lượt Stage‑0 mới với nguồn và
ngân sách hiện tại.** Giữ BASE_GUARD làm đối chứng ở `NOT_QUALIFIED`.
Đã đọc các hồ sơ và kết quả lưu sẵn để đánh giá khả năng chuyển bước.
Tập giá 2024–2026 vẫn đóng. Lượt này không phát sinh phép đo PnL mới.

| Hồ sơ | Bằng chứng có thể dùng | Lý do chưa mở lại |
|---|---|---|
| [EURUSD DGS2](PROP-EURUSD-US-RATES-RESULTS-20261118.md) và [biên độ phiên Mỹ](PROP-SESSION-FEASIBILITY-RESULTS-20261118.md) | 80–211 ngày/năm có ít nhất một chiều qua phí. Luật DGS2 causal tạo 988 tín hiệu và giữ 342, tức 34,6%. | Cả sáu năm giữ dưới 50%. Chỉ 2/6 năm đạt ngưỡng net markout. Phép đếm hai chiều không cung cấp một luật chọn chiều có thể giao dịch. |
| [Gold A BOTH, không TP cứng](XAUUSD-A-HOLIDAY-VALIDATION-RESULTS-20261114.md#4-kết-quả-từng-năm) | Phá biên phiên Á theo H4, SL tự nhiên và thoát theo lịch. Sổ standalone SYM ở risk 150 USD có 103/107 lệnh và +4,05R/+13,80R trong 2022/2023. | Cấu hình cũ đã qua replay và gác vì time-fit. Bằng chứng về cadence trên 2022–2023 không trả lời sàn từng năm trên 2018–2023. Lặp lại công thức không giải quyết khoảng lợi nhuận còn thiếu. |
| [GBPUSD S01](CORPUS-ISOLATION-V25-RESULTS-20261118.md) | Có stop/thoát gốc. Chẩn đoán H1 20:00 có 830/883 cơ hội qua phí, với cap đã dùng khi đó là 15%. | Kịch bản H1 đứng riêng âm −30,20R cụm 2018–2020. Ghép 0,25x tăng DD từ 12,21R lên 15,56R và tăng risk mở, với thứ tự giá trong giờ chưa xác minh. [V26 đã đóng S01](BATCH-EXACT-ISO-V26-RESULTS-20261118.md). |
| [Gold R043](GOLD-R043-FINANCING-PATH-AUDIT-20261112.md) và [Gold F4](PROP-REPLAY-REGRESSION-RESULTS-20261118.md) | Có quy tắc và logic giữ lệnh cụ thể. R043 có 220 lệnh đóng trên 15 sổ năm. F4 dương hai cụm Development dưới STRICT. | R043 trung bình khoảng 14,7 lệnh đóng/năm trong hồ sơ gốc và nhạy với financing. F4 có 6–21 lệnh/năm và đã nằm trong BASE_GUARD. |
| [V13](PATH-RESOLUTION-AND-DEDUP-V13-RESULTS-20261115.md), [V16](GAP-IMMUNE-MULTIASSET-V16-RESULTS-20261116.md) và [V26](BATCH-EXACT-ISO-V26-RESULTS-20261118.md) | V13 có 19 cấu hình trọng tâm định giá lại. V16 có 29 cấu hình Gold/EUR qua endpoint. V26 có danh sách cổng riêng cho corpus và replay ISO. | V13 thiếu cadence theo cổng của đợt và còn gap. V16/V26 không đưa thêm nhánh qua cổng. ISO là thay trọng số, không cung cấp cơ chế tín hiệu mới. |

**Bằng chứng đủ để mở lại** là một card nêu được nguồn tạo cơ hội,
thời điểm biết tín hiệu, mốc cấu trúc làm SL và thời điểm thoát phát
sinh từ chính cơ chế đó. Card phải trỏ tới dữ liệu Development có thể
đối soát. Trước PnL, cần đo số cơ hội trên chiều thực sự chọn và quy
mô của stop trước mọi lọc phí. Với cổng đã dùng, từng năm cần tối
thiểu 40 tín hiệu thô, 99% có điểm định giá, median phí stress/median
stop ≤12% và ≥50% tín hiệu thô qua cap 12%. Chỉ chạy replay cùng risk
khi markout sau phí cũng qua cổng từng năm.

Riêng EURUSD phiên Mỹ, ở ma sát mô phỏng 1,9 pip, card mới cần giải
thích vì sao cấu trúc tự nhiên có thể tạo stop khoảng **15,9 pip trở
lên** ở đủ tín hiệu đã chọn chiều. Bằng chứng này có thể đến từ cấu
trúc thị trường và thời gian nắm giữ khác, hoặc từ đo Bid/Ask đúng
nguồn cùng biểu phí có xác minh đủ để đổi phép đo. Giá từ phía tốt
hơn sau khi xem kết quả và stop nới thêm không giải quyết câu hỏi.

Vòng 1 là ràng buộc thực tế của vai trò bổ sung. Ngay phép điều chỉnh
tĩnh theo 18 lệnh khác nguồn vẫn để thiếu trung vị **4.712 USD** trên
sổ 50.000 theo PRIMARY. Bằng chứng nguồn mới đáng làm khi có thể đổi
một quyết định về stop, chi phí hoặc khả năng chấp nhận ứng viên.
[Đối chiếu 43 khoảng](PROP-GAP-FULL-DEV-RESULTS-20261118.md)

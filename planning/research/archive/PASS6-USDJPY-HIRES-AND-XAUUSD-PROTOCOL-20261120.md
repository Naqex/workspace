# Pass 6 · Protocol xác minh USDJPY và Stage-0 XAUUSD

Phạm vi USDJPY/XAUUSD, 01/01/2018–31/12/2024 UTC, cụm A 2018–2020
và B 2021–2024. Dữ liệu Development đã có exposure. Hai profile chi phí
tham chiếu 36f1535 và 8fd77ef. Giá từ 01/01/2025 niêm phong. Không MT5,
không lệnh thật, không sweep tín hiệu hay tối ưu phân bổ.

## USDJPY

- Đối soát bằng sổ Pass 5 tại 52a824c. Giữ hộp 00:00–03:00 UTC, OCO
  03:00–10:00 UTC, một lần phá, stop đối diện hộp, flat 18:00
  Europe/Helsinki. Đối chiếu những ngày M1 Bid/Ask có đủ cả đường.
  Mid của open đồng bộ. Cực trị mid dựng từ hai side OHLC là giới hạn
  xấp xỉ. Khi entry và SL có thể cùng xảy ra trong một phút, dùng stop
  trước và ghi số ca. Ghép so sánh cùng ngày. Mẫu lịch fix là mẫu chọn
  trước theo lịch, không đại diện toàn năm. Giữ thống kê H1 cùng ngày.
- Chạy thêm stress toàn kỳ H1 vì nguồn M1 rời rạc. Giữ mức hộp của
  spread 0,30 pip và thời gian gốc. Dùng lưới kịch bản stress đã chỉ
  định, spread 0,60/0,90 pip × entry slippage thêm 0,50/1,00 pip.
  Commission 5 USD/lot khứ hồi, slippage nền 0,20 pip mỗi phía.
  Stress baseline riêng dùng spread 0,30 và không thêm slip để tách
  ảnh hưởng ordering. Chọn kết quả xấu hơn nếu hai biên chạm cùng
  H1 đầu. Nếu H1 entry cũng chạm SL, buộc cho entry rồi SL cùng H1.
  Khi stop sau entry gap, dùng giá mở khả thi của side. Mọi mốc flat
  trước rollover. Đối chiếu 405 winner hình học Pass 5 theo ngày,
  ghi loss, còn dương, hòa hoặc thiếu cặp.
- Phán quyết sống qua stress khi case mạnh nhất net dương cả hai
  cụm. Với mẫu hi-res rời rạc, ghi riêng mức bằng chứng. FAIL chỉ
  mô tả cấu hình dưới stress đã khóa, không kết luận mọi biến thể
  breakout hay feed thật đều thua.

## XAUUSD

- Dùng cache M1 QDM có giới hạn độc quyền 01/01/2025 đã niêm phong.
  Giá Bid thật, Ask proxy cộng spread median 36f1535. Các tập tick
  Bid/Ask 2022–2024 được chọn cho nghiên cứu trước, không dùng trộn feed
  hoặc chọn ngày đẹp. Báo rõ bất định việc thiếu Ask liên tục.
- Từ 03:00 đến 06:00 Europe/Helsinki dựng hộp mid từ M1 đã đóng,
  tương ứng 01:00–04:00 UTC mùa đông và 00:00–03:00 UTC mùa hè.
  Kích hoạt 06:00 đến trước 10:00 Europe/London. Một lần phá đầu.
  Buy theo Ask high, Sell theo Bid low. Loại first-minute dual-touch
  khỏi Stage-0 và ghi số ca. Gap ở đầu phút dùng quote mở cạnh hợp lệ.
- Đo +4h, +8h từ cuối phút phát hiện và hard flat 18:55
  Europe/Helsinki (16:55/15:55 UTC). Báo giá mở M1 đúng endpoint.
  Yêu cầu không thiếu phút từ đầu hộp đến endpoint muộn nhất,
  loại cả ngày khỏi cohort chung nếu thiếu. Fade đổi side tại cùng
  giá mid, cùng thời điểm. Commission đúng 0,0007% notional mỗi phía,
  stress 0,20 USD/oz mỗi phía và spread snapshot. Swap 0.
- Cổng ít nhất một mốc net dương và thắng Fade ở cả hai cụm, gross
  cả hai cụm dương, net toàn kỳ dương sau khi bỏ hai năm tốt nhất,
  median friction/median stop ≤12% và ≥50% lệnh giữ được ở trần 12%.
  Báo số năm dương và độ nhạy bỏ Top 10 ngày, không chọn lại rule.
  Qua cổng mới chạy một lát stop cạnh kia, flat 18:55, ép stop đối
  diện khi cùng phút với entry. Báo R đóng, winner taxonomy có đủ
  chứng cứ, thêm min lot 0,01 và ngân sách 25/50 USD.
- Tính chẩn đoán ghép trên lịch UTC ngày có ít nhất một sleeve có
  quan sát. Khi một nhánh rớt, tương quan dùng gross risk-normalized
  markout +4h ròng phí của Vàng và sổ USDJPY có SL, ghi metric và mẫu
  số. Double-SL và phân bổ chỉ chạy khi cả hai có sổ SL và qua cổng.
  Nếu qua, lấy tổng risk cap 1% vốn đầu, hai cách 50/50 và nghịch đảo
  DD Development. Làm tròn lot xuống, kiểm margin đồng thời theo spec
  từng mã và giữ DD/lỗ ngày closed-only tách khỏi ngưỡng equity FTMO.

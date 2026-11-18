# Kiểm sai số chi phí của Gold sweep London DAY

Phép kiểm chỉ dùng `XAUUSD.SWEEP.PREVDAY.LONDON.DAY` với 107 tín hiệu
Development 2022–2023 của V8. Giữ nguyên luật, giờ, mức giá SL cấu trúc,
exit, risk và phí stress. Giá fill hai chiều, nếu thay được bằng nguồn
quan sát, có thể đổi khoảng cách từ fill tới cùng mức SL. Không xét
24H/48H. Khóa phép kiểm trước khi đọc PnL từng lệnh.

1. Dựng lại retention trên toàn bộ raw cohort. Cổng V8 gồm 100%
   endpoint theo mô hình, ít nhất 20 lệnh/năm, ≥50% tín hiệu giữ lại,
   median friction / median natural SL ≤15% và net dương cả hai năm,
   hai swap models, các ngân sách cũ. Tách khỏi chuẩn hiện hành với
   cap từng intent 12%, giữ ≥50%, median scale trong dải đã khóa
   12%–15% và raw markout sau stress ở horizon chính. Chỉ cần một
   cổng cần thiết hụt là dừng. Không đổi cap thực thi hoặc verdict V8.
2. Giữ stress slippage 0,40 USD/oz vòng lệnh và commission 0,0007%
   notional/side theo V8. So bid/ask tại đúng giờ, giữ Bid V8 và đặt
   spread bằng 0 chỉ ở entry dùng Ask proxy để tính cận chẩn đoán.
   BUY tính lại khoảng cách từ cùng Bid tới cùng mức SL, SELL giữ
   nguyên khoảng cách. Commission ước lượng theo giá entry ứng với
   cùng công thức. Dựng thêm cận mọi entry spread bằng 0 để phân biệt
   giới hạn phí và giới hạn sửa proxy. Quote native giữ nguyên ở cận
   sửa proxy. Báo spread tối đa mỗi intent còn lọt cap nếu hữu ích.
   Các giá giả lập này không dùng làm fill, không chứng minh qua cổng.
3. Nếu cận sửa proxy đủ cho cả hai năm, kiểm nguồn paired Bid/Ask
   bổ sung tại đúng timestamps/giờ proxy và dữ liệu đủ để xác nhận
   phí thay được. Không tìm giờ, lệnh hay phí dựa theo PnL. Chỉ đọc
   2022–2023, dùng nguồn local; thiếu giá hay spec thì ghi blocker.
   Chỉ mở bước 2018–2021 có exposure nếu đúng cơ chế vượt cổng bằng
   chứng cứ, rồi mới kiểm đóng góp sau phí, overlap và risk với BASE.
   Việc replay 50k còn cần triển vọng cải thiện đáng kể ở cả hai
   kịch bản đã khóa. Giữ 2024–2026 đóng và mọi thao tác offline.

[Nguồn V8](PROP-GOLD-V8-PROTOCOL-20261115.md) ·
[Cổng hiện hành](../../.agents/skills/strategy-qualification/references/validation-gates.md)

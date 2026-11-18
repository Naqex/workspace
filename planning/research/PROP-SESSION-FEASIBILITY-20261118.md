# Kiểm biên độ trước khi chọn cơ chế tín hiệu

Sau [đối chiếu 43 khoảng](PROP-GAP-FULL-DEV-RESULTS-20261118.md), kiểm
đầu vào kinh tế trước khi đặt công thức mới. Đây là phép đếm ngày đủ
biên độ, chưa dùng tín hiệu dự báo hoặc chọn bên giao dịch.

- Cùng 2018–2023, phiên NYSE đủ 390 phút, cùng 10:30→14:30 New York. Đòi
  hỏi cả 60 bar M1 09:30–10:29 và giá open đúng mốc 10:30/14:30. Giữ ngày
  thiếu trong bảng. So XAUUSD/EURUSD từ nguồn V14 và US500 paired M1 V11.
- BUY lấy đáy Bid 60 bar trừ một bước giá. SELL lấy đỉnh Ask cộng một
  bước. Cả hai đo từ giá vào đúng chiều. Trần chi phí dùng spread đầu
  kỳ và phí stress mô phỏng V19/V26, tính commission vàng ở giá vào
  cho hai phía để phép đo độ rộng chỉ dùng thông tin có tại entry.
- Báo số ngày cả hai chiều hoặc ít nhất một chiều có stop đủ rộng để
  ma sát chiếm tối đa 12%. Với vai trò tối đa một tín hiệu/ngày, ít
  hơn 40 ngày có thể vào một chiều là tín hiệu cảnh báo về biên độ của
  chính cửa sổ này. Đủ 40 ngày chưa cho biết một quy tắc thật giữ được
  đủ ngày hay có lợi thế. Cơ chế mới vẫn cần Stage‑0 đầy đủ.
- Minh họa giới hạn biên độ bằng số ngày có ít nhất một phía mà giá
  ở mốc thoát sinh markout net ít nhất bằng phí ước tính, đồng thời
  đạt quy mô stop. Cột này nhìn hai chiều sau khi biết giá, chỉ đo dư
  địa. Không dùng dấu outcome làm tín hiệu hoặc đổi khung giờ.
- Dữ liệu ngoài 2023 đóng. Không tạo sổ lệnh hay đổi cash, risk, exits
  hoặc verdict của ứng viên đã gác. Nếu một thị trường không đủ độ
  rộng/độ phủ, ghi giới hạn cho đúng cửa sổ. Nếu có thị trường đủ,
  giữ đó làm đầu vào chọn cơ chế trong đợt sàng lọc kế tiếp.

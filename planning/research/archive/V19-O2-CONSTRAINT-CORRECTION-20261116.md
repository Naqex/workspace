# V19 O2 — sửa thiếu sót giữa heuristic và objective của owner

Self-review trước final delivery phát hiện O2 mới chỉ dùng inverse-volatility
mean matching. Bản đó ineligible, nhưng chưa giải đầy đủ yêu cầu của owner:
minimum portfolio variance với cùng expected daily PnL. Giữ nguyên protocol,
freeze `9aaaf29`, mọi kết quả và batch đang chạy; không sửa lịch sử O2 cũ.

Đây là một correction/supplement có exposure được khai báo, không phải claim
rằng chưa ai thấy Validation. V18 và các bảng V19 baseline đã exposed.
Không dùng chúng để fit weights hoặc chọn cơ chế. Chỉ dùng Dev 2018–2023.

## Công thức và ngân sách trước numeric

Giải đúng `min w'Σw`, ràng buộc `μ'w = μ'1` và `0.25 <= w_i <= 2.0`.
Ba sleeve nên có thể kiểm 27 active sets bằng linear algebra; không cần thêm
dependency hay chọn shrinkage/ridge/lookback từ outcome. Đây là một nghiệm
ước lượng covariance cố định, không phải 27 strategy trials.
Nếu covariance không positive definite hoặc residual/feasibility không đạt,
ghi ineligible; không thêm regularization để cứu kết quả.

Chỉ bổ sung ba O2 cells trong ngân sách sáu profile ban đầu:
`O2`, `O1_G035_O2`, `O1_G050_O2`. Giữ gamma/bonus/caps/guard như protocol.
Bản heuristic bị bác vẫn tính vào exposure history; không gộp heuristic
và nghiệm covariance thành “một lần chưa từng nhìn dữ liệu”.

Đo đúng tám Dev cost/source/order cases trên mỗi profile, mọi sổ qua oracle.
So với ba profiles đã chạy. **Giữ `BASE_GUARD` nếu không thắng hai tiêu chí
chính mà không làm DD xấu hơn**, theo rule giữ incumbent đã đăng ký.
Nếu chỉ tie-break payout tốt hơn thì ghi diagnostic, không đổi bản V19.
Không chọn theo Validation hoặc PnL tương lai.

Nếu có upgrade đủ điều kiện, phải khóa correction/code/weights trước khi
chạy Validation/Monte Carlo mới của nó; giữ toàn bộ bản cũ và cập nhật report
phân biệt các versions. Nếu không có upgrade, không rerun 5.000 paths cho
một profile đã fail promotion; báo correction Dev bên cạnh kết quả baseline.
Không mở thêm grid, strategy, risk factors hoặc gap-filter threshold.

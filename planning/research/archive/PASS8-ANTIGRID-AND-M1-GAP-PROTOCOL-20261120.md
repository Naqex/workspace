# Pass 8 · Protocol anti-grid và phút thiếu USDJPY

Baseline `0517738`. Track 1 public MQL5 Statistics/Distribution, MT5 rồi
MT4. Chỉ GET public, mỗi request cách ít nhất hai giây, dừng khi 403,
429 hoặc challenge. Loại 8 ID Pass 2/3. Rà nhiều trang DD thấp và bảng
xếp hạng chung, gộp ID. Dùng số liệu bảng để sơ tuyển. Xác nhận Real,
tuổi theo dõi >=364 ngày, >=150 lệnh, lệnh gần nhất <=30 ngày,
Algo >=80%, max DD chi tiết <=20%. Chọn DD max của balance/equity
relative và các DD cực đại theo tiền kèm phần trăm nếu hiển thị.
Tầng 2 yêu cầu Avg Profit/abs(Avg Loss) >=0,85. Win >72% cần tỷ số
>=1. Dùng số lớn hơn giữa Trades per week hiển thị và trades/tuần
theo tuổi tài khoản khi cùng phạm vi, trần 20. Max Deposit Load
<=20% nếu hiển thị, Equity DD <=1,5 lần Balance DD. Lấy đúng cặp
relative DD để so. Thiếu số bắt buộc giữ unverified. Mô tả dùng grid,
DCA, hedge basket hay martingale là bằng chứng để loại, phân biệt
mô tả phủ định. Distribution/holding là proxy khác USDJPY Tokyo-box.
Chỉ mở link History công khai khi cần kiểm guest availability. Không
login, không bypass, không lấy CSV yêu cầu quyền. Sàng lọc công khai
không xác nhận grid-free hoặc prop-fit.

Track 2 chỉ dùng Parquet Development QDM 2018–2024 gắn hash Pass 7B
và các bản metadata đã lưu. Tái dựng đúng 481 ngày đã loại. Nhóm A
chẩn đoán các ngày có <=5 phút trống, mọi chỗ trống đều đơn lẻ và
nằm giữa hai nến quan sát, hai side Bid/Ask đổi không quá 0,1 pip
từ close trước sang open sau. Mốc mở hộp UTC 00:00, activation 03:00,
hết activation 10:00 và hard-flat phải có quote. Chỉ gọi A là tương
thích phút thưa, nguyên nhân chưa được chứng minh từ M1. Nhóm C cần
dấu đóng cửa theo lịch được xác minh và không có quote sau thời điểm
đóng cho phần đến hard-flat. Nhóm B giữ các ngày còn lại, ghi riêng
khe >15 phút và nhóm không đủ bằng chứng suy nguyên nhân. Thống kê
UTC theo đoạn 00:00–03:00, 03:00–10:00 và 10:00–flat, nêu riêng
2021. Không đọc cache thô QDM hoặc giá 2025+.

Sensitivity trên đúng Stress +0,50 pip và risk 0,30%. Giữ trình tự
giá quan sát, chạy cùng engine Pass 7B theo offset M1 thật. Không tạo
nến hay carry-forward quote. Giữ setup, stop, sizing, USD margin và
điểm flat cũ. Loại thêm ngày A nếu phút trống kề phút entry/exit
hoặc hai đầu gap có thể vắt qua ngưỡng đang kích hoạt/SL. Tái chạy
đường vốn cả sổ thay vì cộng PnL rời. Đối chiếu baseline trên cùng
engine khi chỉ nhận 1.334 ngày đủ path. Ghi delta, no-touch, năm và
giới hạn residual. Không mở vòng tối ưu, Challenge, MT5 hoặc OOS.

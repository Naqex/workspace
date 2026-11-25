# Pass 9 · Protocol audit Round 2 và DNA giao dịch

Baseline `955633b`. Chỉ audit CSV MQL5 mới trong inbox Round 2 và
file chưa audit ở inbox chính. Loại 8 ID và SHA của Pass 3 khỏi
leaderboard. `2283078` chỉ làm tham chiếu tương quan log-only.
CSV không được đưa vào Git. Không chạy chiến lược mới.
Khóa holdout 01/01/2025 giữ nguyên, OrderSend 0, không MT5/web login.

Dùng parser/auditor hiện có. Dòng cash-flow và pending không tính
lệnh khớp. Trống commission/swap là unknown. Tách cash proxy khi giả định
trống bằng 0. Dùng cùng phép đếm nhồi theo giá fill như Pass 3 để so
tỷ lệ. Một lệnh thêm bất lợi có thể nối nhiều vị thế cũ, ghi cả số
event và số cặp. Phân biệt lệnh cùng timestamp. Tăng lot >=1,5x sau
hai lệnh đã đóng thua cùng mã. Báo mẫu net đầy đủ và proxy dấu gross
riêng. Kiểm khoảng giá tới SL hiển thị, USD risk khi có spec. SL
hiển thị không xác nhận SL initial. Trường hợp tăng lot nhưng USD risk
theo SL không tăng tương ứng không tự động gán martingale. Khi grid
lặp lại theo bằng chứng fill, giữ cờ độc tố theo cùng định nghĩa Pass 3.
Không gán clean chỉ từ thiếu chứng cứ.

Định giá trên fills gốc, giữ spread đã nằm trong fill. Dùng snapshot
Standard 36f1535 và Swing 8fd77ef, commission, swap có dấu và ngày 3×
theo rollover 17:00 New York. Stress 0,20 pip/side FX, 0,20 USD/oz/side
XAUUSD, 0,25 index point/side US500.cash. Quote USD dùng trực tiếp,
quote chéo dùng tỷ giá khóa, USDJPY và cặp đảo dùng giá giao dịch khi
cùng cặp quy đổi. Hai giả định clock UTC và Europe/Helsinki, chỉ thêm
bằng chứng timezone từ lịch hoặc giá <2025. Giá cuối tuần là proxy
theo clock, không tự sửa exit để giả Standard tuân thủ. Mã ngoài rổ
13 chỉ tra hỗ trợ sản phẩm, không gán phí. Tính DD đóng, không giả
equity nổi hay payout.

DNA từ timestamp nguồn, holding, chiều, pending đã hủy nếu có và
SL/TP hiển thị. Khớp stop/target trong một tick theo spec hoặc tag
đóng; phân biệt tag lệch, trailing/BE, exit thời gian/tín hiệu và
thiếu cột. R proxy chỉ trên lệnh có SL nằm phía rủi ro và ghi coverage.
Có thể so đường giá chỉ trước 2025, chỉ khi nguồn/clock đủ chứng cứ.
Đo tương quan ngày/tuần trên giao khoảng thời gian log-only 2025–2026
với `2283078`, hoặc USDJPY Pass 7B trước 2025 khi có đủ dữ liệu.
Nêu số cửa sổ giao nhau và độ nhạy UTC/EET. Đây là proxy bổ trợ,
không chứng minh tương quan USDJPY Tokyo-box thực tế ngoài mẫu.

Giữ tối đa hai giả thuyết clean-room từ ứng viên sạch, đủ khả thi,
cash dương sau phí nơi định giá được. Thiếu SL initial, quy tắc
tạo setup hay spec mã đích thì ghi unknown và khóa fail-fast trước
Stage-0. Không chạy Stage-0 hoặc backtest ở Pass 9.

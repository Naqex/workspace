# Lấy trade log live cho Bot Lab

## Lọc trước khi tải

1. **Real và có xác minh của nền tảng.** Myfxbook cần cả Track Record lẫn
   Trading Privileges. MQL5 kiểm Real trên hồ sơ. Chọn nguồn có ít nhất 12
   tháng theo dõi kiểm được, ưu tiên 24 tháng, với ≥150 lệnh. Ghi riêng ngày
   bắt đầu theo dõi và tuổi tài khoản khi chúng khác nhau.
2. **DD tối đa có chứng cứ ≤20%, ưu tiên ≤15%.** Kiểm cả balance và equity.
   Lấy số cao hơn khi hai cách đo cùng có sẵn. Loại đường vốn tăng dồn vào
   vài ngày hoặc không thấy đoạn lỗ nổi. Hạ sizing cần mô phỏng lại đường vốn
   và margin.
3. **Ít chồng vị thế.** Ưu tiên ≤3 và loại khỏi đợt đầu nếu >5 vị thế đồng
   thời. Xem lot qua chuỗi thua, các lần mua thêm ở giá thấp hơn hoặc bán
   thêm ở giá cao hơn, và thời gian giữ lệnh thua so với thắng. Dấu hiệu
   martingale/grid hoặc thiếu dữ liệu cần kiểm lại. Đường vốn mượt và lời
   mô tả của tác giả không xác nhận hai điều này.
4. **Public History và có quyền tải.** Cần symbol, side, open/close time
   có múi giờ, lot theo đơn vị thực, hai giá fill, SL ban đầu/TP, commission,
   swap và profit. Lưu rõ gross/net, account currency, full history hay
   khoảng thời gian đã lọc. Nếu CSV thiếu SL ban đầu, lấy broker statement
   và lịch sử lệnh từ người có quyền. Giữ file nguồn riêng.

## Mẻ đầu trong 5 phút

| Phút | Myfxbook | MQL5 Signals |
| --- | --- | --- |
| 1 | Mở [Systems](https://www.myfxbook.com/systems). Chọn Real và Automated nếu bộ lọc có sẵn. | Mở [MT5 dạng bảng](https://www.mql5.com/en/signals/mt5/list) hoặc [MT4 dạng bảng](https://www.mql5.com/en/signals/mt4/list). Dùng Weeks, Trades và Drawdown để lọc tay nếu danh sách không có mọi bộ lọc. |
| 2 | Giữ ≥12 tháng, ≥150 lệnh, DD ≤20%. Kiểm 2 dấu xác minh trên hồ sơ. | Giữ ≥52 tuần, ≥150 lệnh và DD ≤20%. Trong Statistics kiểm DD balance/equity và nguồn là Real. |
| 3 | Mở History, bỏ hồ sơ giấu lot, giá hoặc giờ. So lot và holding của thắng/thua. | Mở Trading history và Risks. Bỏ hồ sơ có biến động lot, lệnh chồng hoặc lời dồn vài ngày. |
| 4–5 | Dùng export chính thức của tài khoản mình được phép truy cập. Nếu tài khoản công khai thiếu nút tải, xin chủ khoản xuất thay. | Tải bằng Export to CSV → History khi UI hiện nút và quyền truy cập cho phép. Bỏ hồ sơ nếu không lấy được export đúng quyền. |

Đây là link vào bảng và preset áp tay. Môi trường hiện tại không xác minh được
URL chia sẻ lưu đầy đủ bộ lọc. Không mua thuê bao chỉ để thực hiện bước sàng
lọc. Mẻ 5–10 file ưu tiên các hệ thống khác nhau, demo/fixture để riêng.
[Myfxbook verification](https://www.myfxbook.com/help/knowledge-base/verification/) ·
[Myfxbook export](https://www.myfxbook.com/help/knowledge-base/exporting-trading-history/) ·
[MQL5 CSV](https://www.mql5.com/en/articles/3166).

## Kết quả rà nguồn công khai 20/11/2026

Myfxbook Systems trả **403** trong phiên tra cứu. Tài liệu export mô tả thao
tác trên trang tài khoản. MQL5 dạng bảng và một số trang thống kê truy cập
được. Các trang chi tiết đã xem hiển thị lời mời đăng nhập để xem giao dịch
realtime. Môi trường này chưa xác minh được bản CSV công khai đủ cột trên
các hồ sơ đó. Không tiếp tục qua login. Darwinex công bố bộ dữ liệu
DARWIN có mục TRADES. Chưa xác minh record nào có đủ lot gốc, SL và phí
broker cho bước so khớp FTMO. [Darwinex data guide](https://help.darwinex.com/migration/raw-darwin-data-user-guide).

| Hồ sơ đã xem | Tuần hiển thị / lệnh | DD tương đối equity / balance | Kết quả |
| --- | ---: | ---: | --- |
| [Longtime Strategy](https://www.mql5.com/en/signals/2207885) | 208 / 12.679 | 83,85% / 46,94% | DD vượt ngưỡng, chưa xác minh export. |
| [Multi EA Trading](https://www.mql5.com/en/signals/2375343) | 73 / 606 | 33,14% / 23,49% | DD vượt ngưỡng, lời dồn vào ít ngày, chưa xác minh export. |
| [Range Breakout EA Live](https://www.mql5.com/en/signals/2271995) | 105 / 2.140 | 8,96% / 28,29% | Balance DD vượt ngưỡng, 80% growth trong 11 ngày, chưa xác minh export. |
| [Techno Long Term](https://www.mql5.com/en/signals/2307342) | 115 / 4.918 | 13,77% / 38,63% | Balance DD vượt ngưỡng, chưa xác minh export. |
| [Maximum drawdown 10 percent](https://www.mql5.com/en/signals/2398696) | 2 / 39 | Chưa cần xét | Thiếu cả tuổi và số lệnh, chưa xác minh export. |

**0 hồ sơ đủ chuẩn để nạp.** Số tuần và DD là thống kê nền tảng hiển thị tại
lúc tra cứu. Bảng lưu các trường hợp đã loại để tránh chọn chỉ vì tên, DD
equity thấp riêng lẻ hoặc growth cao.

Khi có quyền tải, thả bản CSV/HTML/HTM vào
[inbox live_signals](../../research/bot_reverse_lab/inbox/live_signals/README.md).
Không bỏ credential vào thư mục. Với log thời gian từ 01/01/2025 trở đi,
CLI vẫn chấm được cash và hành vi từ log. Mục kiểm cần đường giá sẽ ghi rõ
độ phủ và trạng thái unknown.

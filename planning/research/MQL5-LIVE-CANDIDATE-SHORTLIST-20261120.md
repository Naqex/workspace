# MQL5 Signals · Shortlist công khai 20/11/2026

**8 tài khoản Real qua vòng thống kê công khai. Tất cả cần đăng nhập để kiểm lịch sử.**
MQL5 công bố tuổi và số lệnh của tài khoản. Cột Theo dõi là số ngày nền tảng
ghi trong trường thống kê, dùng để tránh lấy DD equity ghi nhận quá ngắn đại
diện cho cả tuổi tài khoản. Cột Algo lấy từ hồ sơ chi tiết.

| Hồ sơ Real | MT | Tuần | Theo dõi (ngày) | Lệnh | DD list | DD balance tương đối | DD equity tương đối | DD balance tại mức sụt tiền lớn nhất | Max DD chi tiết | Win | PF | Algo |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| [Rua Kate Nz](https://www.mql5.com/en/signals/2308133) | MT5 | 81 | 400 | 491 | 4% | 1.68% | 4.48% | 1.53% | **4.48%** | 73.72% | 1.85 | 98% |
| [MPDU Europe DARWINEX](https://www.mql5.com/en/signals/2266387) | MT4 | 110 | 540 | 6,338 | 2% | 1.52% | 1.74% | 1.52% | **1.74%** | 61.91% | 1.21 | 99% |
| [Balanced Blend 2](https://www.mql5.com/en/signals/2229611) | MT4 | 285 | 653 | 5,922 | 12% | 9.00% | 11.68% | 15.43% | **15.43%** | 81.05% | 1.64 | 99% |
| [SCR EURAUD advanced](https://www.mql5.com/en/signals/2201028) | MT4 | 379 | 720 | 3,067 | 9% | 7.45% | 8.93% | 7.45% | **8.93%** | 70.45% | 1.37 | 99% |
| [Innolife 4](https://www.mql5.com/en/signals/2237614) | MT4 | 142 | 630 | 1,048 | 16% | 16.16% | 8.56% | 16.75% | **16.75%** | 71.08% | 1.18 | 63% |
| [EA Happy Trend FM](https://www.mql5.com/en/signals/2311977) | MT4 | 240 | 386 | 308 | 18% | 18.25% | 13.45% | 17.81% | **18.25%** | 76.62% | 2.70 | 100% |
| [PAI Unique Mode No Limits with AI Filter](https://www.mql5.com/en/signals/1919885) | MT4 | 381 | 944 | 6,803 | 18% | 17.06% | 17.94% | 17.06% | **17.94%** | 65.72% | 1.51 | 99% |
| [Live Account Breakout EA](https://www.mql5.com/en/signals/2283078) | MT4 | 97 | 481 | 779 | 20% | 19.66% | 1.62% | 14.75% | **19.66%** | 48.78% | 1.38 | 100% |

Max DD chi tiết lấy giá trị lớn nhất trong ba số DD chưa làm tròn trên hồ
sơ. DD list là số nguyên dùng ở vòng lọc đầu. Các mẫu đều có giao dịch gần
nhất trong ba ngày theo snapshot. Chưa có trade log để kiểm grid, martingale,
lot tăng sau chuỗi lỗ, SL lúc vào, hay độ phù hợp FTMO.

## Điểm cần đối chiếu khi lấy được log

- **Rua Kate Nz** · Giữ trung bình 2 ngày. Xác minh lệnh cuối tuần, số vị thế chồng và SL ban đầu.
- **MPDU Europe DARWINEX** · Giữ trung bình 3 ngày. Trong 7 ngày gần nhất, MQL5 báo 101 lệnh/tuần. Kiểm chồng lệnh và 80% tăng trưởng dồn trong 29 ngày.
- **Balanced Blend 2** · Giữ trung bình 7 giờ. Tác giả quy một khoản lỗ cho sự cố terminal. Kiểm đối soát lệnh và SL từ log.
- **SCR EURAUD advanced** · Giữ trung bình 1 giờ. Max deposit load 34,02% tại broker nguồn. Kiểm margin đích và 80% tăng trưởng trong 62 ngày.
- **Innolife 4** · Giữ trung bình 16 giờ. 80% tăng trưởng trong 19 ngày và PF 1,18. Đo sức chịu phí và tập trung lợi nhuận.
- **EA Happy Trend FM** · Giữ trung bình 13 ngày, ưu tiên kiểm Swing. MQL5 cảnh báo tài khoản chỉ giao dịch trong 162 ngày.
- **PAI Unique Mode No Limits with AI Filter** · Giữ trung bình 19 giờ. MQL5 ghi nhận đòn bẩy thay đổi trong khoảng 1:300–1:500. Kiểm khả năng giữ cùng mức risk ở Swing 1:30.
- **Live Account Breakout EA** · Giữ trung bình 8 giờ. DD sát trần và 80% tăng trưởng trong 18 ngày. Con số 22,9% do tác giả nêu là backtest khác kỳ.

## Lấy log có quyền truy cập

Đăng nhập MQL5 bằng tài khoản của bạn, mở hồ sơ trong bảng rồi chọn
**Trading history → Export to CSV**, nếu nút xuất hiện và bạn có quyền tải.
Lưu bản full history và ghi lại URL, thời điểm tải UTC, timezone hiển thị,
tiền tệ tài khoản và SHA256. Nếu vẫn thiếu quyền hoặc cột cần thiết,
dùng export chính thức từ chủ hồ sơ. [Hướng dẫn MQL5](https://www.mql5.com/en/articles/3166).

Thả CSV vào [inbox live_signals](../../research/bot_reverse_lab/inbox/live_signals/README.md).
Chạy theo nhóm file có cùng múi giờ và tiền tệ đã xác minh để khai
`--timezone` và `--currency` đúng nguồn. Dùng `--decimal-mark ","` khi
file dùng dấu phẩy thập phân. Cần bằng chứng riêng nếu muốn dùng SL
hiển thị làm SL lúc vào lệnh.
[JSON shortlist](MQL5-LIVE-CANDIDATE-SHORTLIST-20261120.json) · [Báo cáo Pass 2](BOT-LAB-MQL5-SOURCING-PASS2-20261120.md).

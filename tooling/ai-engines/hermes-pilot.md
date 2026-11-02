# Phản biện nghiên cứu NAQ-6

Đọc hồ sơ bên dưới. Viết báo cáo tiếng Việt tối đa 700 từ, gồm:
1. Kết luận workflow và kết luận về chiến lược, tách riêng.
2. Bảng ngắn đối chiếu BTC/ETH, 15/30 bps và buy-and-hold.
3. Những gì đã kiểm chứng, những gì chưa chứng minh; tránh suy diễn số liệu.
4. Đề xuất đúng một thí nghiệm tiếp theo: giả thuyết, dữ liệu, chia thời gian,
   baseline, chi phí, tiêu chí đạt/bác bỏ định trước và cách tránh tune vào OOS cũ.
5. Một bài học có thể dùng cho các lần nghiên cứu sau.

Chưa cấp quyền giao dịch, tải thêm dữ liệu hoặc chạy thử nghiệm. Đây chỉ là
phản biện bằng chứng. Nếu có tool memory, lưu đúng một bài học tổng quát,
không lưu toàn bộ hồ sơ. Nếu có research_publish, dùng nó đăng báo cáo vào
công việc hiện tại; nếu không có tool, trả báo cáo trực tiếp.

## Hồ sơ cố định

Nguồn: native Paperclip NAQ-6, run 2193750a-cb69-47c9-88b3-9c9e0bceaa0f.
Report SHA256: 90e043c64cbe8564e1e67902b27a6f1b000469b735f11a35117460effa8663d0.
Manifest SHA256: 1136529b04f9a5e48ae2a3874889a1e9ac558a604e8e663b100687c64c33d110.

- Một candidate cố định, không tìm/tối ưu tham số: close(t)/close(t-3)-1.
- Factor > 0 thì long, ngược lại giữ tiền; khớp vị thế từ nến tiếp theo.
- BTCUSDT và ETHUSDT, 2922 dòng daily UTC, 2021–2024; 1461 dòng mỗi tài sản.
- Chỉ dùng snapshot lịch sử công khai đã kiểm nguồn/hash/quality; không bảo đảm
  vintage của dữ liệu được nhà cung cấp sửa lại. Không lấp nến thiếu.
- RD-Agent kiểm shape, index, finite values, row count; factor khớp oracle độc
  lập. Prefix invariance, future perturbation invariance và negative controls đạt.
- Quant Lab replay quy tắc tương đương đã xác minh, trên các prefix theo thời gian.
- Mỗi return dưới đây là median của 4 cửa sổ OOS 180 ngày, KHÔNG là return toàn
  kỳ. Drawdown là mức xấu nhất trong các cửa sổ. Tail chưa đủ cửa sổ được ghi
  unused_tail_bars, không tự nối vào OOS.

| Tài sản | Candidate 15 bps | Candidate 30 bps | Buy-and-hold 15/30 bps | Worst DD candidate 15 bps |
|---|---:|---:|---:|---:|
| BTC | 27.52% | 17.74% | 51.71% / 51.71% | -17.94% |
| ETH | 1.50% | -6.17% | 36.90% / 36.90% | -28.73% |

- Cash baseline 0%. Chi phí cơ sở mỗi lượt: 10 bps phí + 5 bps trượt giá;
  stress gấp đôi. Không mô phỏng order book, partial fills hay market impact.
- Các chỉ số là OOS hồi cứu, chưa là final holdout kín. Chưa có kiểm định ý
  nghĩa thống kê, parameter stability, forward paper trading hoặc broker demo.
- Chọn trước hai tài sản lớn cho pilot; không suy rộng toàn thị trường.
- Workflow completed; strategy_qualified=false; execution_authorized=false.

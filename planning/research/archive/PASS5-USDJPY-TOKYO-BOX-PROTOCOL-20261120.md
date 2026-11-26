# Pass 5 · Đăng ký Stage-0 USDJPY Tokyo box

Khóa trước phép tính, kế thừa [Pass 4](BOT-LAB-BREAKOUT-EA-FORENSIC-DNA-20261120.md).
Chỉ USDJPY, cả hai chiều, một cấu hình, Development 2018–2024.
Cụm A 2018–2020, cụm B 2021–2024. Dữ liệu cũ đã có exposure nghiên cứu.
[NATIVE lock](NATIVE_FTMO_HOLDOUT_LOCK.json) giữ nguyên.

| Hạng mục | Quy tắc |
| --- | --- |
| Nguồn | USDJPY H1 và D1 từ bản Parquet Development đã khóa, SHA khớp lock. M1 Bid/Ask ngày rời rạc và fixture không đủ cho hai cụm. H1 là Bid OHLC, dùng Ask tổng hợp bằng spread USDJPY đo được từ snapshot 36f1535. |
| Giờ | Chuyển FTMO wall time qua lịch DST New York, UTC+2 mùa đông và UTC+3 mùa hè theo DST Mỹ. Hộp Tokyo dùng 09:00–12:00 JST (00:00–03:00 UTC). Hard flat dùng 18:00 Europe/Helsinki, ra 16:00/15:00 UTC theo DST châu Âu. Ghi giờ London và New York theo IANA. |
| Hộp và activation | Hộp high/low proxy mid của đúng ba H1 đã đóng. Buy Stop ở đỉnh, Sell Stop ở đáy. Hiệu lực 03:00–10:00 UTC, loại trừ đúng mốc 10:00. Tối đa một trigger mỗi ngày. Ghi width theo pip và ATR Wilder D1(14) đã đóng tại giờ activation. Không lọc trước theo ATR hay width. |
| H1 first touch | Buy kiểm Ask high và Sell kiểm Bid low. Nếu cùng H1 đầu tiên chạm cả hai biên, loại khỏi hiệu suất vì thiếu thứ tự. Ghi cả số ngày có dual-touch trong cửa sổ H1 và số ngày mơ hồ ở first touch. Nếu một biên được chạm, dùng giá stop hoặc opening side quote nếu gap vượt mức. Entry time là cuối H1 chạm cho mục đích đặt mốc, với thời điểm fill thật trong giờ chưa biết. |
| Markout | +4h, +8h tính từ timestamp proxy cuối H1 chạm và hard flat theo lịch đã khóa. Exit dùng H1 open đúng mốc. Yêu cầu đủ H1 từ 00:00 qua mốc exit muộn nhất, nếu thiếu ghi lý do và loại khỏi cả ba bảng. Mọi điểm trước 17:00 New York và trong cùng ngày UTC. |
| Fade | Cùng ngày, trigger và giá tham chiếu mid suy ra từ stop candidate. Khớp phía ngược bằng Bid/Ask đối ứng tại cùng mid. Gross ở mid cho hai hướng. H1 không xác nhận được spread hay thứ tự thực tế tại fill. |
| Phí | 100.000 USD notional mỗi lượt, PnL JPY đổi theo exit mid từng lượt. 36f1535: spread median 0,30 pip (snapshot London), commission 5 USD/lot RT, thêm stress 0,20 pip/side, swap 0. Spread đã nằm trong executable quotes. Báo gross trước spread và phí, từng cấu phần, net và tỷ lệ %. Không sizing. |
| Phân tầng | Năm, cụm, chiều khớp của riêng Breakout/Fade, Top 10 ngày theo đóng góp dương / tổng net dương. Width/ATR theo ba dải <0,25 / 0,25–<0,50 / ≥0,50 và unknown. Mọi lớp chỉ chẩn đoán. |
| Cổng | Có ít nhất một trong ba mốc với gross dương ở cả hai cụm, net stress dương ở cả hai cụm, net Breakout lớn hơn Fade ở cả hai cụm, và net tổng sau khi bỏ hai năm có net đóng góp cao nhất vẫn dương. Báo số năm dương và +4h là mốc chính. Không đổi giờ hoặc horizon. |
| SL nếu qua | Dùng đúng các entry đã giữ và một stop cạnh đối diện hộp, thoát ở 18:00 Europe/Helsinki, không TP. H1 không đủ ordering thì giữ unknown/cách bảo thủ như trên. Báo net R/năm, max DD R, losing streak và winner taxonomy trong phạm vi đủ path. Nếu fail, không chạy bước này, XAUUSD hoặc biến thể cứu kết quả. |

Chỉ đọc dữ liệu Development đã khóa. Không broker, không MT5, không lệnh
thật. Ba mốc exit là các phép đo song song trên cùng sự kiện và mỗi mốc
giữ nguyên trong toàn kỳ.

[FTMO lịch DST Mỹ 2024](https://ftmo.com/en/blog/trading-updates/trading-update-7-mar-2024/) ·
[FTMO chi phí 36f1535](FTMO-DEMO-10K-STANDARD-FULL13-AND-EXECUTION-20261119.md) ·
[Pass 4 clock của EA nguồn](BOT-LAB-BREAKOUT-EA-FORENSIC-DNA-20261120.md).

# Pass 10 · Protocol Stage-0 cho Engine #2

Baseline `d004497`. Development 2018–2024, A 2018–2020, B 2021–2024.
Ưu tiên nghiên cứu Swing 10k/25k, đối chứng Standard 50k. Dùng native
Development Parquet đã niêm phong, chỉ đọc giá từ 2018 và trước
01/01/2025, xác minh SHA và clock trước khi đọc OHLC. Kiểm cutoff ở cả
timestamp nguồn và timestamp đã quy đổi. Không đọc archive hỗn hợp.
OrderSend = 0. Không MT5, MQL5 intake, Monte Carlo, grid hoặc holdout.

## Rà lineage và nhập liệu trước outcome

| Recipe | Lineage đã rà qua inventory và báo cáo | Khác biệt cố định |
| --- | --- | --- |
| London ORB EURUSD/GBPUSD | R016/R017, Catalogue13, Discovery7, Pass 7 FX scout | Discovery7/Catalogue13 dùng H1 close breakout và SL 1,5 ATR. Pass 7 dùng hộp Tokyo 3h. Lượt này dùng first-touch OCO hộp London 1h, đối chứng cùng tín hiệu và phí snapshot. |
| US500 NY Cash ORB | R094/R095, R100–R121, R094 afternoon follow-up | R094/R095 dùng hộp 15 phút, xác nhận close M15 và đóng trưa. Multiframe dùng bias/setup/retest. Lượt này dùng hộp cash 1h, first-touch OCO và không SL ở Stage-0. |
| US500 TOM | R025 v2, source correction và long-source monthly input | R025 v2 tách close-to-close/overnight và mô phỏng từng ngày cash, không giữ vị thế liên tục hay áp swap thật. Long-source monthly xét momentum/tháng và bị chặn input. Lượt này mua một vị thế, giữ xuyên 4 phiên cash theo lịch. |

Không tìm thấy exact recipe dưới hồ sơ phí `36f1535`. Đây là nghiên
cứu có lineage và đã có exposure từ các study trước. Không gọi clean OOS.

QDM CLI 125.2692 hiện trả 6 symbol, không có USA500IDXUSD hoặc US500.
`US500.cash` H1 native có 258, 259, 259 hàng trong 2018, 2019, 2020,
toàn bộ ở 00:00 giờ server. QDM chỉ được export quãng đã có cache trong
2018–2024. Không gọi update khi CLI không áp được cận trên trước 2025.
Metadata listing được phép. Giữ các nguồn trực tiếp cũ ngoài input;
khi thiếu QDM Bid/Ask đủ hai cụm ghi
`US500_INTRADAY_DATA_GAP_2018_2020`, không chạy NY ORB. Nhãn này
chỉ tình trạng đầu vào hợp lệ, không kết luận nhà cung cấp thiếu lịch sử.
[QDM CLI](https://strategyquant.com/de/doc-new/einfuhrung-zu-cli/) ·
[Giới hạn update](https://strategyquant.com/forum/topic/qdmcli-exe-update-resume-ohne-uberschreiben/) ·
[Danh mục CFD nguồn của QDM](https://www.dukascopy.com/swiss/english/cfd/range-of-markets/?lang=en).

## Quy tắc và chi phí khóa trước

- **London ORB**. 08:00–09:00 Europe/London theo DST. Một OCO mỗi ngày
  trong khoảng 09:00–13:00, loại timestamp 13:00. Dùng mô hình Bid OHLC +
  spread cố định như Pass 5. Cạnh hộp là Bid high/low cộng nửa spread,
  Buy Stop chạm trên Ask và Sell Stop chạm trên Bid. Fill gap bất lợi
  tại giá mở executable. Nếu bar first-touch chạm cả hai cạnh, bỏ ngày
  và đếm riêng. H1 không xác định phút fill. Neo +4h/+8h từ close của
  bar trigger theo Pass 5. Exit tại open H1 chính xác, dùng toàn đường
  H1 từ hộp tới đích. Bỏ riêng horizon nếu thiếu đường hoặc chạm
  rollover 17:00 New York. Horizon chính là 17:00 London, hai mốc
  còn lại chỉ chẩn đoán. Fade đổi chiều trên cùng mốc cơ hội, tái đặt
  Bid/Ask và phí đầy đủ. Không có SL/TP ở Stage-0, zero swap.
- **NY ORB**. Nếu nguồn đủ điều kiện, chỉ dùng ngày NYSE cash đủ 390
  phút theo lịch repo. Hộp 09:30–10:30 New York. OCO first-touch
  10:30–14:00, loại timestamp 14:00. Dùng Bid/Ask M1, loại first-touch
  kép cùng bar, fill gap bất lợi. Fade cùng cơ hội. Mốc chính 15:55
  New York, +2h/+4h neo close của phút trigger, chỉ tính đúng mốc còn
  trong phiên. Spread nằm trong Bid/Ask, không tính hai lần. Zero swap.
- **TOM**. Official-date proxy theo frozen NYSE cash calendar. Mua tại
  **native D1 open của ngày cash cuối tháng**, bán native D1 close của
  ngày cash thứ ba tháng sau. D1 được gắn theo nhãn ngày server của
  broker. Đây là giá open/close D1 (phiên gần 17:00 New York), không
  phải quote tại 09:30/16:00 NYSE. Bỏ cửa cắt biên Development, giữ
  riêng count. Nếu thiếu bất kỳ D1 ngày cash trong cửa, không bù giá.
  Standard clamp của đối chứng là close D1 thứ Sáu đầu tiên nằm trước
  exit dự kiến, không vào lại. Đây là Friday proxy, chưa có quote sát
  cut-off, historical news/closure calendar hoặc equity nội ngày.
  REST lấy mọi cửa 4 phiên cash liên tiếp hoàn toàn ngoài ngày TOM,
  áp cùng entry/exit, phí và clamp tương ứng. Cửa REST có chồng lấn,
  báo mean bps trên mỗi phiên giữ làm thống kê mô tả. TOM không chứng
  minh nguồn vốn thể chế từ OHLC.
- **Phí**. Profile Standard `36f1535`, Swing `8fd77ef`, khóa SHA.
  FX commission 5 USD/lot round trip, slip stress 0,20 pip/side, spread
  snapshot 0,10 pip EURUSD và 0,70 pip GBPUSD. US500 commission 0,
  spread D1 proxy 0,60 point, slip 0,75 point/side. TOM swap BUY
  theo point và contract đích, tính mỗi lần qua 17:00 New York trong
  cửa giữ. Cột `swap_rollover3days=5` của **cả hai** snapshot US500
  dùng thứ Sáu 3×, thay vì giả định chung thứ Tư. Swap BUY Swing
  −138,03 points và Standard −87,25 points. Carry chưa gồm corporate
  action/dividend và biến động phí lịch sử, nên là phân tích scenario.
  [McConnell & Xu](https://business.purdue.edu/faculty/mcconnell/publications/Equity-Returns-at-the-Turn-of-the-Month.pdf).

## Cổng duy nhất và lát được phép

Qua cổng khi horizon chính có net stress dương ở A và B, ít nhất 5/7
năm dương, tổng còn dương sau khi bỏ hai năm tốt nhất. Net mean phải
ít nhất bằng mean ma sát stress. Ở từng cụm yêu cầu vượt đối chứng
ít nhất một mean friction cùng đơn vị (USD/lot/lệnh cho ORB, bps/phiên
giữ cho TOM). Mọi năm phải có quan sát. Đo box width và natural
opposite stop trước lọc cho ORB, 2×Wilder ATR14 trên D1 đã đóng trước
entry cho TOM. Yêu cầu median friction / median stop ≤12% và ít nhất
50% mẫu individually ≤12%. Không loại lệnh bằng cổng phí ở Stage-0,
không chọn lại horizon hay side. Cadence là chẩn đoán vận hành.

Chỉ khi đạt mới dùng **một** SL slice của horizon chính: opposite
edge + hard flat mỗi ngày trên ORB (stop gap bất lợi, giữ 1 entry/ngày),
2×ATR14 tại entry và scheduled D1 exit trên TOM. Báo giới hạn path
H1/D1, ghi floating chưa đo. Kiểm sizing 0,30% risk danh nghĩa trên
Swing 10k/25k với step/min/max theo spec, round down không ép min
và so margin snapshot. Không tối ưu risk. Ghép cash đóng lệnh theo
ngày UTC và tuần ISO với Pass 7B Stress_05, cùng 0,30% hoặc cùng đơn
vị tiền trên 10k, vắng giao dịch gán 0 khi ngày nguồn đủ điều kiện.
Không trộn ngày Pass 7B thiếu đường với ngày no-trade. Báo paired
coverage, Pearson chung/theo ngày hoặc tuần Engine #1 lỗ,
double-loss, thời gian dưới đỉnh (kể cả cuối mẫu), Net / Max DD
trước/sau. Không có survivor thì không chạy SL hoặc ghép danh mục.

## Đính chính đối chứng Standard sau lần chạy đầu

Protocol gốc trước outcome ở `99b3051`. Bản đo đầu phát hiện 5 rollover
thứ Sáu 3× ở TOM Standard. Khi thứ Sáu là ngày NYSE nghỉ, lịch cash
bỏ ngày đó và điều kiện chỉ tìm thứ Sáu đã để cửa giữ qua cuối tuần.
Áp lại đúng ràng buộc hard-flat bằng cách đóng tại close D1 của phiên
cash cuối cùng trước đứt tuần đầu tiên trong cửa. Bình thường là thứ
Sáu, còn thứ Sáu nghỉ thì là phiên cash liền trước. Lưu riêng số cũ
và số đã sửa. Tín hiệu, đầu vào, phí và tiêu chí của TOM Swing và ORB
giữ nguyên. Đối chứng tiếp tục dùng D1 close proxy.

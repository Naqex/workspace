# Pass 11 · GBPUSD M1 và điều kiện ghép hai động cơ

Baseline `8242f8e`. Development UTC 2018–2024, A 2018–2020, B
2021–2024. Holdout giá nghiên cứu từ 01/01/2025 giữ khóa. Không MT5,
broker, Stage-2 Challenge, tối ưu hoặc Monte Carlo. OrderSend = 0.

## QDM 125.2692 và admission

Dùng duy nhất QDM CLI/Dukascopy qua symbol riêng
`GBPUSD_PASS11_QUARANTINE` theo quyền Pass 7B. Update chỉ chạm symbol
này. QDM quản lý cache thô, có thể tải đến ngày hiện tại vì CLI update
bỏ qua dateto. Research không mở cache đó. Export từng năm UTC
2018–2024 theo Generic tick CSV Bid/Ask. Kiểm metadata cửa sổ, sau đó
đọc clock-only và chặn toàn năm nếu bất kỳ dòng ngoài năm. Chỉ sau
admission mới đọc giá. Đối chiếu số tick, Bid/Ask, grid, thứ tự và SHA
giữa các bước. Sinh M1 OHLC [Bid, Ask] Parquet/Zstd và manifest.
Không nạp cache kênh Dukascopy trực tiếp. Khi QDM update lỗi có thể
thử export phạm vi hợp lệ đã tải, coverage vẫn phải được đo độc lập.
Không có giá ở một năm thì báo blocked, không thay bằng nguồn khác.

## GBPUSD đông hồ London, giữ nguyên recipe Pass 10

- Hộp 08:00–09:00 Europe/London. Vì Pass 10 đặt hai cạnh trên trục
  midpoint, trên tick QDM dùng min/max midpoint thật trong hộp. OCO
  Buy Stop Ask chạm đỉnh, Sell Stop Bid chạm đáy từ 09:00 đến trước
  13:00 London. Chỉ một entry. Gap dùng giá mở bất lợi. SL cạnh còn
  lại, BUY thanh lý Bid, SELL thanh lý Ask. Flat tại quote mở phút
  17:00 London, zero swap. Không chọn chiều/giờ theo kết quả.
- Chạm cả hai entry cùng phút thì xét hai thứ tự khả dĩ, chọn loss
  lớn hơn theo 1R cấu trúc ở Base và giữ path đó cho ba phí. Nếu
  trong phút entry có cả SL thì ghi SL bảo thủ tại cạnh, vì open
  của phút có thể sớm hơn entry. Stop ở phút sau dùng gap nếu giá
  open đã vượt. M1 extrema chỉ là bounds, không suy thứ tự tick.
- Base +0,20 pip/side, commission 5 USD/lot, spread trong Bid/Ask.
  Stress thêm +0,50 hoặc +1,00 pip bất lợi ở entry, giữ nguyên path.
  R là khoảng entry tới SL trước slippage và commission. DD nội
  phút dùng envelope high→low bảo thủ, pre-entry không lấy high.
- Phân loại weekday clock đủ từng phút gồm cả hard flat. Nhóm A
  tối đa 5 phút thiếu rời rạc, đủ phút 08:00/09:00/13:00/17:00,
  cả hai side bước nhảy close→open ≤0,2 pip. Chỉ nhận khi hai đầu
  khe không chứa cạnh entry/SL đang active, và không kề phút fill
  hoặc exit. Không bơm quote. Các khe còn lại là Nhóm B hoặc A chưa
  thể replay. Ngày không có giá toàn cửa sổ ghi riêng trong B.
- Dual-touch H1 xác định lại chính xác từ native GBPUSD khóa SHA và
  cùng first-touch Pass 10. Báo đủ mẫu replay được và ngày thiếu
  theo Strict và +A. Đánh dấu rõ M1 dual/entry-SL còn mơ hồ.
- Chỉ mở Track 3 nếu Strict và +A tại Stress_05 dương A/B, ≥5/7
  năm dương, bỏ Top-10 ngày vẫn dương toàn kỳ. Các kịch bản chi phí
  không tạo signal mới. Giữ mọi kết quả và không cứu bằng tham số.

## Track 3 có điều kiện

USDJPY giữ tape Pass 7B Stress_05 và sensitivity Pass 8. Dùng giao
của lịch đủ dữ liệu theo cohort, gồm ngày có coverage và không có lệnh.
Trục UTC M1, lỗ ngày so balance tại reset Prague, đo high/low envelope
tổng các vị thế đồng phút, tiền mặt và equity, account profiles
`36f1535`/`8fd77ef` khóa SHA. Risk dựa vốn đầu cố định để chung
thước đo, floor lot theo spec và kiểm free margin theo các vị thế còn
mở khi có entry mới. Không tự cắt lệnh để chữa DD sau outcome.

Solo 0,25% và 0,30%, Equal 0,15+0,15 và 0,20+0,20%. Inverse DD
đo floating DD mỗi sleeve trên Cluster A của mẫu chặt ở risk
tham chiếu bằng nhau, khóa ratio cho cả hai cohort và sổ, dùng tại
tổng 0,40% và 0,50%. Mốc so bằng ngân sách là Solo 0,30% vs
Equal 0,30%, các mức cao hơn đối chiếu cùng trần DD 8%. Gate
ADVANCE yêu cầu ≥8% net/năm, A/B dương, Daily ≤3%, DD ≤8%, không
lỗi margin 10k, underwater ngắn hơn solo 0,30% ở cả Strict và +A,
Static <10%. Vùng 6–8% ghi riêng. Nếu sống sót mà chậm, giữ ứng
viên lõi có điều kiện và báo bottleneck. Không chạy Challenge.

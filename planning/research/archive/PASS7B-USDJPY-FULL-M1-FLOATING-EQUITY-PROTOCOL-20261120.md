# Pass 7B · Protocol USDJPY M1 và floating equity

Kế thừa Pass 5 `52a824c`, Pass 6 `268f3a4`, Pass 7 `10ba5a9`.
Phạm vi [2018-01-01, 2025-01-01) UTC. A 2018–2020, B 2021–2024.
Không scout. Không MT5, OrderSend 0, không lifecycle, không mở holdout native.

## Nhập giá

QDM CLI 125.2692, upstream Dukascopy. Bản cài không liệt kê
`action=download`. Owner cấp quyền `update` vào symbol tick riêng
`USDJPY_PASS7B_QUARANTINE`. Cache QDM thô nằm ngoài nghiên cứu, không
đọc trực tiếp và không export từ năm 2025. Chỉ export tick UTC từng năm
2018–2024, `Generic tick format (comma delimited)`, giữ millisecond và
thứ tự dòng. Kiểm timestamp trước parse cột giá của mỗi batch, từ chối
cả năm nếu phạm biên. Hash CSV và assertion thời gian trước khi ghi
Parquet/Zstd. Bảo toàn Bid/Ask và mid OHLC theo tick thực, không điền
phút. Tính spread Tokyo 00:00–03:00 UTC, London 08:00–12:00 giờ London.
Đối chiếu 339 ngày đã ghép Pass 6, giữ nguyên nguồn gốc và hash. Ghi rõ
độ phủ lịch, ngày có quote, ngày đủ path tới flat và gap. Cache QDM thô
chỉ được dùng lại qua export Development có guard.

## Replay

Hộp Tokyo 00:00–03:00 UTC, OCO 03:00–10:00 UTC exclusive, một lệnh/ngày,
SL cạnh đối diện và flat 18:00 Europe/Helsinki. Box M1 chính lấy trung
bình extrema hai side như Pass 6 để giữ quy ước. Mid tick thật lưu để đo
lệch extrema, không đổi signal. Đủ tất cả M1 từ 00:00 đến hard-flat
inclusive mới nhận ngày. BUY mở Ask/đóng Bid, SELL mở Bid/đóng Ask.
Gap dùng opening quote khả thi. Entry và SL cùng phút xử lý SL sau fill,
hai entry cùng phút chọn kết quả tệ hơn ở Base và giữ cùng chiều ở stress.
Phí 5 USD/lot khứ hồi, slip 0,20 pip mỗi phía, thêm 0/0,50/1,00 pip
tại entry. Swap 0. Giữ R structural gốc qua ba mức phí để so sánh.
Đối chiếu PnL/taxonomy với Pass 6 khi cùng khóa ngày. Nhãn dựa hình học
ghi riêng với taxonomy cần thêm evidence ngoài hard-flat.

## Equity và phán quyết

Vốn 10k/25k Swing và 50k Standard. Risk cố định theo vốn đầu 0,20/0,25/
0,30/0,40%, lot làm tròn xuống theo step/min/max. Stop-risk dự kiến gồm
hai phía slip và commission, margin USD 1:30 / 1:100 theo snapshot
8fd77ef / 36f1535 (Standard 50k ngoại suy từ spec 10k đã đo). Bỏ lệnh
khi min lot hoặc margin không đủ, đếm số lệnh và rủi ro bị làm tròn.
Sổ liền kỳ, không reset năm hoặc dừng sau breach. Mark lệnh mở bằng side
liquidation, commission chia hai phía. Dùng M1 open/close và envelope
high-then-low trong phút giữ, entry dùng biên xấu khả thi sau entry,
stop minute đến fill. Dựng snapshot theo phút và lưu phần có vị thế.
Prague midnight reset theo balance, strict daily 5% và static 10% vốn
đầu. Peak-to-trough báo riêng. Báo thời gian dưới đỉnh đến hồi hoặc hết
mẫu theo ngày giao dịch và ngày lịch. Ghi giới hạn do thiếu tick ordering
trong phép thử M1.

Chỉ chọn Pass 8 khi Stress_05 có một sổ/risk dương A và B, >=5/7 năm
dương, daily <=3%, peak DD <=8%, net >=8%/năm và không vi phạm vạch
cứng. Báo riêng mục tiêu 10% và khoảng đệm daily 2,5% / peak DD 7,5%.
Nếu dương hai cụm nhưng thiếu tốc độ hoặc đệm, giữ Engine 1 cần đối tác.
Nếu Stress_05 âm một cụm trong tập đủ năm, dừng nhánh. Thiếu coverage
trọng yếu hoặc thiếu nguồn thì chưa gán ba verdict kinh tế.

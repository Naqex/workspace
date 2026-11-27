# Nhịp 1 — hai giả thuyết liên thị trường và rà nguồn thiếu giá

Đăng ký trước số đếm và markout. [Task](PROP-STAGE0-NEXT-SLEEVE-TASK.md) ·
[Lộ trình](PROP-SYSTEM-ROADMAP.md). Baseline đối chứng là BASE_GUARD V19/V26.

| ID | Tài sản và giả thuyết | Quy tắc duy nhất |
|---|---|---|
| N1-GOLD-EQUITY | XAUUSD. Sau cú giảm của cổ phiếu Mỹ, có thể còn nhu cầu chuyển sang vàng. Baur–Lucey đưa ra động cơ kiểm quan hệ vàng và cổ phiếu, còn độ trễ và ngưỡng dưới đây là giả thuyết của nhịp này. | Ngày thứ Hai–thứ Sáu, lúc 10:30 New York. Nếu US500 Bid giảm ít nhất 0,25% từ open M1 09:30 đến close M1 10:29 và cả 60 phút có mặt ở hai nguồn, tạo một BUY vàng. SL tự nhiên là đáy Bid vàng của cùng giờ trừ một đơn vị lưới giá. |
| N1-EUR-PEERS | EURUSD. Khi GBPUSD và AUDUSD dịch chuyển cùng chiều, EURUSD có thể phản ứng trễ. Nghiên cứu yếu tố chung của thị trường FX chỉ gợi ý cơ chế, chưa cho bằng chứng lợi thế H1. | Mỗi giờ đóng từ 08:00 đến 16:00 UTC, thứ Hai–thứ Sáu. Hai cặp phụ phải cùng tăng hoặc cùng giảm ít nhất 0,10% open–close H1. Độ dịch chuyển EURUSD theo chiều đó phải nằm từ 0 đến một nửa mức nhỏ hơn của hai cặp. Lấy tập đủ điều kiện đầu tiên trong ngày. SL nằm ngoài low/high Bid/Ask thích hợp của H1 EURUSD một đơn vị lưới. |

Hai cơ chế dùng biến từ thị trường ngoài tài sản vào lệnh. F3/F4/F5 dùng biến
động, nén hoặc phá biên của chính tài sản. Đối chiếu thêm V23 transfer F5,
V26 mẫu nến, R035 pair formation, R026 fixing và post-FOMC. N1-EUR-PEERS
khác pair formation ở chỗ chỉ đo phản ứng chậm của EURUSD và dùng một lệnh
một chân. Dùng đúng hai cấu hình. Hiệu quả theo tháng yếu của baseline chưa
được xem để chọn giờ, chiều hoặc tham số.

Nguồn động cơ: [Baur và Lucey](https://doi.org/10.1111/j.1540-6288.2010.00244.x)
và [Lustig, Roussanov và Verdelhan](https://www.nber.org/papers/w14082).

## Dữ liệu và cổng chốt

- Điểm bắt đầu 01/01/2018 và điểm cắt loại trừ 01/01/2024 UTC. XAUUSD/EURUSD
  dùng bản V14 Development kiểm hash qua `bars_for`, có spread Ask proxy
  kế thừa. US500 M1 và GBPUSD/AUDUSD H1 dùng bản dữ liệu V11 kiểm seal.
  Nến H1 phụ được biết ở cuối giờ UTC. Hai chuỗi mục tiêu dùng M1 đủ 60
  timestamp liên tiếp khi tạo tín hiệu. H1 chỉ dùng tạo tín hiệu.
- Quyết định lúc giờ đóng. Entry tại open M1 đầu tiên từ lúc quyết định
  đến 60 giây sau. BUY vào Ask ra Bid, SELL ngược lại. Chân trời tính từ
  entry, +4h chính, +2h chẩn đoán, phạm vi cùng phiên. Mốc định giá dùng
  open M1 trong 60 giây sau deadline, trước điểm cắt dữ liệu và không
  muộn hơn giờ đóng nội ngày 20:30 UTC hoặc guard ngày lễ sớm hơn theo
  lịch V16. Mốc cố định rơi ngoài phiên được đánh dấu thiếu điểm định giá.
  EUR lấy giờ đủ dữ liệu và đủ điều kiện đầu tiên quan sát được, đồng
  thời báo số giờ thiếu dữ liệu để thấy giới hạn của phép đếm. Giữ ngày có lệnh,
  tháng trống, mẫu thiếu dữ liệu và guard lịch khai báo. Không dựng lệnh
  SL-active. Cost SYM của scanner hiện tại, đã gồm lãi qua rollover nếu
  có. Trần phí xét spread vào lệnh + phí vòng theo biểu mô phỏng. Gross
  Bid/Ask đã trả spread một lần, nên chỉ trừ commission và slippage khi
  tính net. Spread Ask mô phỏng không đo được độ giãn spread thực tế.
- Count-only báo cơ hội thô từng năm, sàn 40/năm. Stage-0 báo mọi cơ chế
  đã đăng ký để đối chiếu, ngay cả khi rớt tần suất. Mỗi năm cần đủ 99%
  điểm định giá trên raw signals để xét qua. Mean net stress dương từng năm
  và ít nhất bằng mean ma sát stress cùng mẫu. Tỷ lệ median phí/median SL
  trên raw cohort có thể định giá phải ≤12% từng năm. Ít nhất 50% toàn bộ
  raw signals mỗi năm đạt cap 12%; unknown vẫn nằm trong mẫu số.
  Báo số mẫu, phân vị, độ bất định với bootstrap theo tuần, 2.000 lượt
  và seed 261118. Khoảng bootstrap là chẩn đoán, không đổi cửa đã khóa.
- So thời điểm cơ hội với ngày có entry BASE_GUARD Development để mô tả
  phần bổ sung. Lệnh trùng ngày hoặc chồng kỳ không phải mẫu độc lập.

## Rà thiếu giá

Đọc danh tính gap toàn kỳ đã lưu và chỉ so PnL từng lệnh từ bốn sổ Dev
PRIMARY/STRICT × OLHC/OHLC. Ghép theo strategy và source event, tính PnL
bằng lot floor tham chiếu 150 USD của sổ PRIMARY, dùng cùng lot ở bản STRICT.
Xếp hạng khoảng theo mức giảm USD lớn nhất qua hai thứ tự giá của lệnh
đi qua nó. Giữ đồng hạng theo UTC, và ghi lại nhóm khoảng cùng lệnh.
Chọn tối đa 10 khoảng, không cộng lại các mất mát bị gán lặp theo lệnh.
Tìm trên metadata nguồn có hash/provenance và khác các nguồn V19 đã thử.
Mở tối đa hai nguồn và tuân theo ngân sách 90 phút của task. Đầu vào thứ
nhất ưu tiên dựa trên khả năng phủ các khoảng top và tính độc lập của feed.

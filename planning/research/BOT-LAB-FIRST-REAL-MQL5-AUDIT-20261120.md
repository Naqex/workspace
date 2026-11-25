# Bot Lab · Audit batch MQL5 thật đầu tiên · 20/11/2026

**8/8 file nạp thành công, 24.725 lệnh đã đóng, 0 ứng viên đạt cổng FTMO.**
Bảy hồ sơ bị cờ nhồi lệnh theo giá fill. Hồ sơ còn lại là Live Account
Breakout EA, giữ làm đối chứng. Chưa có SL lúc mở, timezone đã xác minh hay
đường equity đủ phủ để dùng bất kỳ hồ sơ nào cho Challenge.

## 1. Nạp file và đối soát

| Dữ liệu | Số lượng |
| --- | ---: |
| File người dùng cung cấp | 8 |
| Dòng dữ liệu sau header | 25.897 |
| Lệnh đóng hợp lệ | 24.725 |
| Dòng balance / nạp vốn | 124 |
| Dòng lệnh chờ hết hiệu lực, không có PnL | 1.048 |
| Lệnh có ngày mở hoặc đóng từ 01/01/2025 theo giờ nguồn | 13.382 |
| Lệnh trước mốc theo giờ nguồn, thiếu timezone | 11.343 |
| Lệnh ngoài rổ 13 spec đã khóa | 14.806 |

Bảy bản MT4 `.history.csv` có 13 cột, thêm `Comment` sau `Profit`. Bản
MT5 `.positions.csv` của Rua Kate Nz có 11 cột, với volume mở và đóng
trùng nhau ở 487/487 lệnh. Cả tám file là UTF‑8 BOM, phân cách chấm phẩy,
giờ `yyyy.MM.dd HH:mm:ss` không kèm offset và dấu chấm thập phân. Giá,
SL và một số giá trị profit có nhóm hàng nghìn cách bằng dấu cách.
Adapter đọc nhóm số đúng định dạng, loại dòng balance/pending khỏi lệnh
khớp, giữ commission/swap trống là unknown và chỉ nhận lot đóng nếu
đối soát được hai volume trong bản positions. [MQL5 mô tả hai bản CSV](https://www.mql5.com/en/articles/5913)

Các mã như `EURUSD+`, `EURUSD.fx` và `XAUUSD+` được quy về spec tương ứng.
Có test cho cả `.m`, `.pro` và `US500c`. Mã như NZDCAD, AUDCAD, EURAUD,
USTEC hoặc GER40 được giữ để phân tích hành vi và gắn
`OUT_OF_FTMO_13_UNIVERSE` khi định giá. Nhãn mô tả phạm vi 13 spec của
dự án. Số lệnh trong bảng dưới là số từ CSV và có thể khác snapshot
Pass 2. JSON giữ số dòng, phân loại, SHA256 mỗi file và mã ngoài rổ.

## 2. Leaderboard và dấu hiệu rủi ro ẩn

| Hồ sơ | Lệnh | Lần thêm ở giá bất lợi | Số lệnh cũ bất lợi tối đa | Tăng lot sau hai lệnh net thua | Lỗ TB / lãi TB gross | Trống SL hiển thị | Phán quyết |
| --- | ---: | ---: | ---: | --- | ---: | ---: | --- |
| PAI Unique Mode | 6.801 | 2.522 | 8 | 0/122 | 1,22× | 1/6.801 | REJECTED_TOXIC |
| SCR EURAUD advanced | 3.060 | 72 | 2 | 3/606, đỉnh 2,50× | 1,66× | 1/3.060 | REJECTED_TOXIC |
| Balanced Blend 2 | 5.918 | 1.109 | 11 | 6/112, đỉnh 6,00× | 3,29× | 4.025/5.918 | REJECTED_TOXIC |
| Innolife 4 | 1.047 | 207 | 7 | 0 chuỗi đủ net | 2,08× | 914/1.047 | REJECTED_TOXIC |
| MPDU Europe DARWINEX | 6.328 | 3.929 | 68 | 3/419, đỉnh 3,00× | 1,26× | 6.300/6.328 | REJECTED_TOXIC |
| Live Account Breakout EA | 776 | 0 | 0 | 0 chuỗi đủ net | 0,68× | 0/776 | INSUFFICIENT_DATA_UNKNOWN |
| Rua Kate Nz | 487 | 206 | 5 | 0/83 | 1,32× | 487/487 | REJECTED_TOXIC |
| EA Happy Trend FM | 308 | 98 | 7 | 0 chuỗi đủ net | 1,22× | 0/308 | REJECTED_TOXIC |

Mỗi lần thêm là một lệnh mới khớp thấp hơn giá mua hoặc cao hơn giá bán
của ít nhất một vị thế cùng mã và cùng chiều còn mở. Dùng thứ tự
timestamp trong cùng export. Phép đo từ giá fill ước lượng hướng lỗ nổi.
Nó chưa có giá thanh lý Bid/Ask hay chi phí của vị thế cũ tại thời điểm đó.
Cờ martingale dùng hai lệnh cùng mã đã được tất toán thua ròng trước
lệnh mới, rồi phát hiện lot mới từ 1,5× lệnh thua gần nhất. Mẫu số là số lần có đủ dữ liệu kiểm hai lệnh
đã tất toán, gồm mọi kết quả. **3/8 hồ
sơ** có cờ tăng lot theo quy tắc này. Ví dụ MPDU có **37.554 cặp**
thêm bất lợi, chia thành 3.929 lệnh thêm riêng biệt.

Có **11.728 ô SL trống** và **0 giá trị SL bằng 0**. Trống có thể do
export hoặc việc quản lý lệnh, nên **0 hồ sơ xác nhận được thiếu stop
cứng** từ riêng trường này. Cờ liên quan stop của Balanced Blend 2
đến từ tỷ số lỗ/lãi gross 3,29×. Cả batch có **0/24.725 lệnh**
xác nhận được SL ban đầu. Chỉ 7.970 lệnh có đủ ba trường gross,
commission và swap để tính net nguồn theo từng dòng.

| Tổng trạng thái | Số hồ sơ |
| --- | ---: |
| PASS_SWING / PASS_BOTH | 0 / 0 |
| REJECTED_TOXIC | 7 |
| REJECTED_COST_OR_DD độc lập | 0 |
| INSUFFICIENT_DATA_UNKNOWN | 1 |

## 3. Đổi sang biểu phí FTMO và kiểm luật quỹ

Định giá nhạy cảm trên đúng fills và lot trong CSV. Gross được tính lại
theo contract size từ snapshot. Spread đã nằm trong hai giá fill. Thay
commission bằng **5 USD/lot FX**, **0 cho US500.cash** và
**0,0007% notional mỗi phía cho XAUUSD**. Áp swap có dấu và ngày 3× theo
spec đích, với giờ rollover New York. Stress thêm **0,20 pip mỗi phía**
cho FX và **0,20 USD/oz mỗi phía** cho Vàng. Hai giả định clock
`UTC` và `Europe/Helsinki` chỉ dùng để đo độ nhạy. Quy đổi USD theo giá
đóng nếu giao dịch cùng cặp quy đổi, hoặc mid của snapshot khóa nếu
cần cặp khác. Đây là mô hình cùng fills với tỷ giá quy đổi proxy.
[Spec Standard](FTMO-DEMO-10K-STANDARD-FULL13-AND-EXECUTION-20261119.md) ·
[Spec Swing](SWING-10K-AUDIT-MULTIWEEK-AND-WIN-TAXONOMY-20261120.md)

| Hồ sơ | Lệnh định giá / tổng | Swing net cơ sở USD | Swing net stress USD | Standard net stress USD | Phiên qua thứ Bảy, rổ đủ spec |
| --- | ---: | ---: | ---: | ---: | ---: |
| PAI Unique Mode | 2.141 / 6.801 | 4.654 → 4.668 | 4.212 → 4.226 | 4.216 → 4.229 | 156 |
| SCR EURAUD advanced | 285 / 3.060 | 43 → 218 | −345 → −170 | −335 → −170 | 0 |
| Balanced Blend 2 | 5.288 / 5.918 | 1.854 → 1.859 | 1.174 → 1.178 | 1.184 → 1.190 | 116 |
| Innolife 4 | 1.039 / 1.047 | 1.422 → 1.472 | 772 → 822 | 770 → 820 | 66 |
| MPDU Europe DARWINEX | 72 / 6.328 | xấp xỉ −680 | −701 → −700 | −701 → −700 | 26 |
| Live Account Breakout EA | 776 / 776 | 9.870 | 9.116 | 9.116 | 0 |
| Rua Kate Nz | 0 / 487 | — | — | — | — |
| EA Happy Trend FM | 308 / 308 | 10.873 → 10.886 | 10.726 → 10.739 | 11.029 → 11.041 | 185 |

Khoảng min→max theo hai giả định giờ nguồn. Cột Standard chỉ đổi biểu phí
trên fills gốc, chưa phản ánh thoát bắt buộc hay Điều khoản FTMO. 10 lệnh
Balanced mở và đóng trong cùng giây bị loại khỏi phép định giá vì chưa có
thứ tự đủ chi tiết. Toàn bộ có **9.909/24.725** lệnh định giá được ở cả hai
mô hình. Cột qua thứ Bảy đếm lệnh giữ qua trưa thứ Bảy theo proxy, giữ
cùng số ở hai giả định giờ. Holiday clamp và tin tức ở chế độ funded
cần lịch xác minh theo mã và đồng hồ nguồn.

- **SCR EURAUD** chuyển từ dương sang âm dưới stress. Tác động thấy trên
  285 lệnh thuộc rổ spec, trong 3.060 lệnh nguồn.
- **MPDU** có −546,71 USD gross ngay trên nhóm 72 lệnh được định giá.
  Chi phí làm âm thêm khoảng 154 USD. Phần lớn lệnh nằm ở NZDCAD,
  AUDCAD và AUDNZD. Log chưa trả lời được kinh tế toàn hệ thống ở FTMO.
- **Breakout và EA Happy Trend** là hai hồ sơ có đủ độ phủ spec và net
  stress dương trong phép đo. Happy Trend có cờ nhồi lệnh và 185 lệnh
  giữ qua mốc cuối tuần. **Không có hồ sơ được xác nhận rớt Standard
  chỉ vì cuối tuần.** Quy tắc nghỉ >2 giờ áp cho funded Standard, với
  ngoại lệ cho Swing và hai vòng đánh giá. [FTMO quy tắc giữ lệnh](https://ftmo.com/faq/can-i-hold-positions-overnight-or-over-the-weekend/)

Batch chuẩn tạo tám tổ hợp mỗi hồ sơ. Swing 10k/25k và Standard 10k/50k,
mỗi vốn chạy tại risk 0,50% và 1,00%. **Cả 64 tổ hợp thiếu đủ dữ liệu
chuẩn hóa risk**, với 0 lệnh được sizing theo SL lúc vào. Daily 5%, static
10% và margin 1:30/1:100 đều unknown. Model 80/20 chỉ xếp hạng sau khi
qua cổng bằng chứng. [FTMO 2-Step](https://ftmo.com/en/trading-objectives/#2-step)

## 4. Đối chứng và khả năng chuyển giao

File `BEHAVIORAL_BLUEPRINT` do CLI xuất có 0 mục đạt cổng. **Live Account
Breakout EA** là hồ sơ đáng ưu tiên để đối soát chứng từ.

| Chỉ số | Live Account Breakout EA |
| --- | --- |
| Tài sản | USDJPY 610 lệnh, XAUUSD 166 lệnh |
| Net stress theo fill và lot nguồn | +6.594,75 USD USDJPY, +2.521,06 USD XAUUSD |
| Winrate gross và payoff | 48,3%, Avg Win / Avg Loss 1,47× |
| Giữ lệnh theo giờ nguồn | Trung vị 9,04h, P90 12,83h |
| Tần suất | 33,7 lệnh/tháng lịch |
| Giờ mở trong file | Cụm 05:00–08:59, 510/776 lệnh. Nhóm Asia chiếm 382/776 hoặc 567/776 dưới hai giả định clock. |
| Chồng lệnh | Tối đa 1 vị thế cùng mã, cùng chiều ở thời điểm thêm |
| Kiểm tăng lot theo gross | 37/772 chuỗi, tối đa 3,875×. Với SL hiển thị, tỷ lệ rủi ro tiền giá-về-stop có trung vị 0,992×, P90 1,019× và 0/37 từ 1,5×. |
| Selective Win Diagnosis | Toàn bộ lệnh từ 2025 theo ngày nguồn. 0 lệnh đủ điều kiện đọc path. |

Số tiền theo SL hiển thị gợi ý lot lớn hơn đi cùng stop hẹp hơn.
Cần SL lúc mở để xác nhận cơ chế. Log closed trades cũng thiếu điều kiện
sinh tín hiệu và các cơ hội không khớp. **Chưa đề xuất đóng gói chiến
lược mới từ batch này.** Bước ngắn nhất là đối soát timezone, SL khi đặt
lệnh, lịch sử sửa stop và commission/swap của Breakout trước khi quyết
định có đáng đăng ký một giả thuyết độc lập hay không. Các hồ sơ
grid-like chỉ dùng để làm đối chứng rủi ro.

Trong 11.343 lệnh trước khóa theo ngày nguồn có mã trùng kho Development,
nhưng timezone của export và SL lúc mở vẫn thiếu. Vì vậy batch mở **0 file
nến/tick local** và **0 lệnh được gán nhãn thắng dựa trên path**. Không dùng
mẫu hậu 2025 để đo MAE/MFE hoặc hiệu chỉnh rule.

## 5. Kiểm chứng và lưu bằng chứng

| Kiểm chứng | Kết quả |
| --- | --- |
| Parser trước/sau | Mẫu 12 cột cũ giữ nguyên. Đã thêm hai layout thực, giá có nhóm nghìn, tách pending, volume mở/đóng và chuẩn hóa symbol. |
| Clock / dữ liệu | Test tách thứ tự wall-clock khỏi UTC và chặn gọi market khi clock chưa xác minh. |
| Đối soát batch | 25.897 = 24.725 + 124 + 1.048. Xác minh SHA256 tám file, thử cả hai giả định clock ở phép đổi phí. |
| Test liên quan | 76 PASS, 0 skip. |
| Repo và thực thi | Holdout lock giữ nguyên, `OrderSend = 0`, MT5 đóng, không đọc .env, không backtest chiến lược mới. Pin Trader và WIP VI Dubber giữ nguyên. |

```powershell
uv run --project tooling/strategy-engines/observer --no-sync python -m tooling.ai_engines.bot_live_auditor --currency USD --leaderboard-dir .runtime/bot-lab-batch
```

`--currency USD` dựa vào thống kê công khai gắn đúng ID ở Pass 2.
Tám CSV đang giữ trong inbox ignored. Leaderboard đầy đủ chứa đối soát
từng dòng, cùng hai file Behavioral Blueprint lưu riêng, có hash trong
manifest `bot-lab-mql5-pass3-20261120/manifest.json`. Repo chỉ ghi kết
quả tổng hợp. Checksum cho tài liệu tracked dùng byte LF chuẩn Git.

[JSON đối soát](BOT-LAB-FIRST-REAL-MQL5-AUDIT-20261120.json) ·
[SHA256](BOT-LAB-FIRST-REAL-MQL5-AUDIT-20261120.sha256) ·
[Shortlist Pass 2](MQL5-LIVE-CANDIDATE-SHORTLIST-20261120.md)

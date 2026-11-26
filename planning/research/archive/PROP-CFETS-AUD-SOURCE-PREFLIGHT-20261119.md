# CFETS fixing → AUD/USD | Kiểm tra nguồn Development

19/11/2026 · `DATA_PATH_INCOMPLETE` · 0 lượt tính PnL · BASE_GUARD `NOT_QUALIFIED`.

## Câu hỏi và phép thử đã khóa

Sau khi CFETS công bố tỷ giá tham chiếu USD/CNY lúc 01:15 UTC theo
lịch, phần bất ngờ của tỷ giá đó có dự báo được hướng AUD/USD còn
giao dịch được từ 01:20 đến 02:00 UTC hay không? Chỉ dùng Development
2018–2023, đối chiếu hai cụm 2018–2020 và 2021–2023.

Ước lượng fixing bằng midpoint USD/CNH cuối cùng trước 01:14 UTC,
cũ tối đa 60 giây, nhân trung vị 20 tỷ lệ fixing/CNH đã công bố trước
đó. Fixing thực tế thấp hơn ước lượng thì BUY AUD/USD, cao hơn thì
SELL. Đây là ước lượng nhân quả đơn giản của nghiên cứu. CFETS lấy
báo giá từ market maker để tính fixing. Các nghiên cứu về CNY và
đồng biến tiền tệ chỉ tạo cơ sở cho giả thuyết.
[Nguồn CFETS](https://www.chinamoney.com.cn/english/bmkcpr/index.html?tab=2) ·
[Giờ công bố](https://www.chinamoney.com.cn/english/rarfmrrudrgl/20221230/2526819.html) ·
[New York Fed](https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr828.pdf) ·
[BIS](https://www.bis.org/publications/working-paper-727-recent-rmb-policy-and-currency-co-movements).

Chờ xác nhận fixing đã khả dụng trước 01:20, rồi vào theo báo giá hai
chiều đầu tiên trong [01:20, 01:21). Thoát lúc 02:00 hoặc khi chạm SL
tự nhiên theo biên Bid/Ask 00:00–01:13:59 với đệm 1 pip. Stress là
spread thực tế cộng 9 USD/lot/vòng. Trần phí là 12% rủi ro và cần giữ
ít nhất 50% tín hiệu. Đối chứng lấy hướng biến động AUD/USD trước
01:14 trên cùng ngày, giờ khớp, quy tắc thoát và ngân sách rủi ro.

## Kết quả kiểm tra nguồn

| Điều kiện đã khóa | Bằng chứng | Kết quả |
|---|---|---|
| Có fixing và bằng chứng khả dụng trước 01:20 | Hai truy vấn đầu dùng ngày ISO trả 10 dòng, sai phạm vi. Truy vấn lại bằng định dạng ngày trên giao diện CFETS trả đúng một dòng cho mỗi ngày 02/01/2019 và 04/01/2023, với hai trường `date` và `values` | Có bản ghi theo ngày. Chưa xác minh được giờ công bố thực tế của từng bản ghi |
| USD/CNH trước 01:14 và đường giá AUD/USD từ trước công bố tới thoát | Tám gói báo giá xin qua Dukascopy Jetta cho đúng hai ngày mẫu trả HTTP 403. Không nhận được gói nào. Kho local xác minh được cặp Bid/Ask AUD/USD H1 | Chưa có nguồn đủ độ phân giải cho các thời điểm bắt buộc |
| Tần suất, markout sau phí và lợi thế so với đối chứng | 0 ngày đạt điều kiện nguồn để đưa vào phép đo, 0 lượt tính PnL | Tần suất khả thi, lợi nhuận và chênh lệch với đối chứng đều chưa đo |

12 file H1 Bid/Ask năm 2018–2023 được chọn từ metadata trước khi đọc
giá và được kiểm SHA256. Có 37.407 giờ ghép cặp, 0 giờ chỉ có một phía.
Mẫu số bên dưới là ngày thứ Hai đến thứ Sáu, gồm cả ngày lễ. Nến 01:00
chứa cả thời gian trước và sau fixing, nên không thể suy ra biên giá
trước 01:14, báo giá khớp lúc 01:20 hoặc thứ tự chạm SL.

| Năm | Ngày trong tuần | Có H1 ở 00:00 / 01:00 / 02:00 UTC | Đủ cả ba mốc (%) | Spread mở nến 01:00 trung vị (pip) | Sàn SL minh họa ở 12% (pip) |
|---|---:|---:|---:|---:|---:|
| 2018 | 261 | 260 / 260 / 260 | 99,62 | 0,9 | 15,00 |
| 2019 | 261 | 260 / 260 / 260 | 99,62 | 1,0 | 15,83 |
| 2020 | 262 | 261 / 261 / 261 | 99,62 | 1,0 | 15,83 |
| 2021 | 261 | 260 / 260 / 260 | 99,62 | 1,0 | 15,83 |
| 2022 | 260 | 260 / 260 / 260 | 100,00 | 1,3 | 18,33 |
| 2023 | 260 | 260 / 260 / 260 | 100,00 | 1,0 | 15,83 |

Với AUD/USD, 9 USD/lot là 0,9 pip nếu 1 pip/lot bằng 10 USD. Sàn SL
lý thuyết khi spread bằng 0 là 7,5 pip. Cột minh họa lấy
`(0,9 pip + spread mở nến H1) / 0,12`. Spread đó là bối cảnh
đầu giờ, còn ma sát thật cần Bid/Ask ở cả hai đầu lệnh. Chưa đo được
tỷ lệ qua cổng phí.

## Mục tiêu nghiên cứu 2%/năm theo quy mô tài khoản

Dùng rủi ro cố định 0,30% vốn danh nghĩa cho mỗi lệnh. Để đóng góp
2% vốn mỗi năm sau chi phí giao dịch, nhánh cần 6,667R/năm, với 1R
là mức rủi ro định mức của một lệnh.

| Vốn tham chiếu (USD) | 1R (USD) | 2%/năm (USD) | Cần trung bình ở 40 lệnh/năm | Cần trung bình ở 60 lệnh/năm |
|---|---:|---:|---:|---:|
| 10.000 | 30 | 200 | 0,1667R / 5,00 USD | 0,1111R / 3,33 USD |
| 25.000 | 75 | 500 | 0,1667R / 12,50 USD | 0,1111R / 8,33 USD |
| 50.000 | 150 | 1.000 | 0,1667R / 25,00 USD | 0,1111R / 16,67 USD |

Đây là mục tiêu phần đóng góp của nhánh trong nghiên cứu. Chưa xác
nhận mức khối lượng sau làm tròn lot, ký quỹ hoặc điều kiện tài khoản.
FTMO công bố đòn bẩy tối đa 1:30 cho Swing và 1:100 cho Standard.
Theo ghi nhận lịch sử trong Client Area, owner từng thấy Swing 10k/25k
trên 2-Step USD MT5. Sổ 50k dùng để đối chiếu nghiên cứu.
[Thông số FTMO](https://ftmo.com/en/faq/what-are-the-account-specifications/) ·
[Ghi nhận quy mô tài khoản](PROP-FIRM-FIT-20261102.md).

FAQ hiện hành miễn cửa sổ hạn chế tin ±2 phút cho Challenge,
Verification và Swing. Funded Standard tính cả SL/TP trên mã chịu
ảnh hưởng của tin được chọn. CFETS fixing không có trong danh sách
công khai đã kiểm. Nếu mở lại phép thử, cần xét các sự kiện AUD/USD
trùng giờ và lịch áp dụng theo loại tài khoản.
[Quy tắc tin tức FTMO](https://ftmo.com/en/faq/can-i-trade-news/).

## Quyết định

Gác phép thử ở bước xác minh nguồn. Chỉ mở lại khi có bằng chứng
giờ công bố hoặc giờ nhận fixing theo từng ngày, báo giá USD/CNH
trước 01:14 và đường Bid/Ask AUD/USD đủ để dựng SL, khớp và thoát.
Giữ nguyên phép thử đã khóa khi nguồn đủ. Giá 2024–2026 vẫn đóng.
Lượt này chỉ kiểm nguồn và quy mô, chưa chạy Stage-0 kinh tế hoặc mô
phỏng tài khoản.

Bằng chứng riêng tại
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/prop-cfets-aud-source-20261119/`.

| File | SHA256 |
|---|---|
| `registration.md` | `ea447c8e6a820f01611eaac53907b6d1d69303529c746138324101546c5d248f` |
| `source-probes.json.zst` | `328611bb9d1c65eb619351221afdaaef91fdcb1e6fc1a426c3aa49f05d44b6ed` |
| `source-geometry.json.zst` | `5e4c96e00702e9bd33131a21215059c575f19c3dc9401cd7acd4df09e7cd6fee` |

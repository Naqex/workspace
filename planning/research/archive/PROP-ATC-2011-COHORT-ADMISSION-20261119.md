# ATC 2011 — kiểm nguồn cho 12 robot được công bố

**Gác nguồn này ở bước xác minh đầu vào.** Định danh được đủ 12/12 robot
trên biểu đồ MetaQuotes. Có 1/12 hồ sơ với mô tả trực tiếp về logic bản
2011. Với cả 12 hồ sơ, chưa xác minh được bản chạy đầy đủ cùng cấu hình và
lịch sử từng lệnh của đúng tài khoản thi. **0/12 được đưa vào Stage-0**.
Trạng thái là `SOURCE_REVIEW_REQUIRED`. Lãi/lỗ sau phí, tần suất,
drawdown và độ tập trung vẫn chưa đo.

## Phạm vi đã khóa

Cohort là 12 người bật chia sẻ EX5 hoặc MQ5 trong bài ngày 24/11/2011.
Danh sách được lấy theo thứ tự chú thích của biểu đồ, gồm cả các tài khoản
có equity giảm. 12 người này tự chọn chia sẻ trong số 395 robot lúc khai
mạc. Công bố chỉ bao phủ đến tháng 11, trước khi giải kết thúc. Tập này
vẫn có thiên lệch tự chọn chia sẻ và khả năng hồ sơ còn tồn tại.
[Bài công bố](https://www.mql5.com/en/forum/5412) ·
[Biểu đồ gốc](https://c.mql5.com/3/6/OpenEAs_chart__1.png) ·
[Số robot khai mạc](https://www.metaquotes.net/en/company/news/3710).

Điều kiện nhận một cơ chế trước khi xem Development là luật có thể tái
hiện, phiên bản và tham số thi truy được, quyền đọc/tái hiện rõ, sổ lệnh
demo khớp phiên bản, có tần suất, lot và giới hạn lỗ gốc, có nguồn giá và
khác cơ chế đã đo. Nếu có nhiều hồ sơ đủ, ưu tiên bằng chứng nguồn, rủi ro
và dữ liệu, không dùng lợi nhuận xếp hạng để chọn. Ngân sách tối đa một
cơ chế. Cổng kinh tế đăng ký là +1.000 USD/năm trên sổ 50.000 USD dưới
phí stress ở từng cụm 2018–2020 và 2021–2023, cùng kiểm số lệnh và
rủi ro tập trung trước khi xét replay.

## Hồ sơ trong cohort

Mỗi dòng có đường equity tổng hợp trên biểu đồ. Các con số về lot,
lịch sử sửa bản thi, số lệnh và DD cấp lệnh chỉ được ghi khi nối được
với đúng robot đã chạy.

| Định danh | Bằng chứng bổ sung và điểm dừng |
|---|---|
| enivid | Phỏng vấn tháng 10/2011 xác nhận đảo chiều theo lệnh trước, hướng đầu chọn tay, lot cố định và ATR trailing. Thiếu bộ tham số từng cặp, lệnh gốc và stop ban đầu. [Phỏng vấn](https://www.mql5.com/en/articles/543) |
| GeorgMLNK | Có tên `Roc_Ocs_MA_Ch2012` cho AUDUSD H4 ở mùa 2012. Chưa khớp bản 2011. [Danh sách 2012](https://www.mql5.com/en/forum/8083) |
| abbeysworld | Có `golddust` EURUSD M30 ở danh sách 2012. Chưa khớp bản 2011. [Danh sách 2012](https://www.mql5.com/en/forum/8083) |
| ShurikAn | Khớp định danh. Thiếu mã, tham số và sổ lệnh bản thi. |
| TorBar | Khớp định danh. Thiếu mã, tham số và sổ lệnh bản thi. |
| Zyama | Bài về bộ lọc tương quan giá cùng tác giả. Chưa có liên kết với phiên bản thi và sổ lệnh. [Bài tác giả](https://www.mql5.com/en/articles/269) |
| firestrand | Khớp định danh. Thiếu mã, tham số và sổ lệnh bản thi. |
| Toyota | Có `MultiCurrency2012` ở mùa sau. Profile hiện tại theo alias trả về 404. Bản 2011 chưa khôi phục. [Danh sách 2012](https://www.mql5.com/en/forum/8083) |
| andrehowe | Có `Volume4H` EURUSD H4 ở danh sách 2012. Chưa khớp bản 2011. [Danh sách 2012](https://www.mql5.com/en/forum/8083) |
| isemaster | Khớp định danh. Thiếu mã, tham số và sổ lệnh bản thi. |
| pulfik | Khớp định danh. Thiếu mã, tham số và sổ lệnh bản thi. |
| SHOOTER777 | Có bốn chỉ báo MT5 năm 2010 và một EA MT4 năm 2008. Chưa có hồ sơ robot MT5 thi 2011. [Bài và mã đã công bố](https://www.mql5.com/en/users/shooter777/publications) |

Với **enivid**, tác giả nêu bảy tham số cho mỗi cặp và thêm một tham số
chung nhưng không đưa đầy đủ giá trị. Trailing theo ATR chưa xác nhận
mức lỗ tối đa ngay khi vào lệnh. Việc luân phiên BUY/SELL cũng chưa cho
phép tách lợi thế hướng vào lệnh khỏi cách trailing quyết định thời điểm
đóng và đảo vị thế. Đây là hồ sơ có mô tả cùng mùa rõ nhất. Tự chọn chu
kỳ ATR, danh sách cặp, lot, hướng khởi đầu hoặc stop mới sẽ tạo luật khác.
[Phỏng vấn enivid](https://www.mql5.com/en/articles/543).

**Đối chứng `cs2011` đứng ngoài 12 định danh đã khóa.** CodeBase ghi
tên bản thi, ngày đăng 31/10/2011 và ngày cập nhật trang tiếng Anh
22/11/2016. Tác giả xác nhận dùng MACD trên EURUSD H1, tăng vị thế mạnh
và không có SL. Bản này bị loại theo điều kiện rủi ro đã khóa và chưa
được chạy. Không dùng trường hợp này để suy ra rủi ro của 12 robot.
[CodeBase](https://www.mql5.com/en/code/611) ·
[Phỏng vấn tác giả](https://www.mql5.com/en/articles/547).

## Đối soát và quyết định

- Đã mở 12 hồ sơ giải đấu cũ và tra profile/publications hiện hành của
  12 alias. Mọi URL giải đấu cũ đều chuyển về trang chủ MQL5. Có 11/12
  profile hiện hành trả nội dung. Wayback Availability trả thông tin hai
  bản lưu EN/RU ngày 27/11/2011. HTTP 429 chặn phần đọc nội dung lưu,
  nên chưa xác minh được danh sách liên kết tải hoặc sổ lệnh từ các bản
  lưu đó. Kho chỉ mục khác cũng chưa cung cấp snapshot nội dung kiểm được.
  Chưa xác minh các bản lưu còn giữ file EA hay lịch sử từng lệnh.
  [Điểm vào giải đấu cũ](https://championship.mql5.com/2011/en/news/123) ·
  [Bản lưu EN được liệt kê](https://web.archive.org/web/20111127012117/http://championship.mql5.com:80/2011/en/news/123).
- Dùng quy trình xác minh nguồn có sẵn của [Bot Lab](BOT-REVERSE-LAB-PLAYBOOK.md).
  [V26](CORPUS-BATCH-V26-CARD-20261118.json) gồm 24 tổ hợp sáu mẫu nến
  × bốn oscillator. Mô tả đảo chiều + ATR trailing của enivid khác
  cấu trúc đó, nhưng thiếu phiên bản để khóa và so luật chính xác. Không
  có tệp nguồn bản thi nào đủ điều kiện đưa vào static parser.
- Việc cho tải công khai xác nhận quyền truy cập tài liệu công bố trong
  bối cảnh đó. Quyền dùng phái sinh hoặc thương mại cần căn cứ riêng.
  FTMO cảnh báo việc dùng EA bên thứ ba có thể gây vướng trần phân bổ
  nếu nhiều tài khoản dùng cùng chiến lược. FTMO không bắt buộc đặt SL;
  giới hạn lỗ trong lượt này là tiêu chí nghiên cứu của dự án.
  [Điều khoản MQL5](https://www.mql5.com/en/about/terms) ·
  [Quy tắc FTMO](https://ftmo.com/en/faq/which-instruments-can-i-trade-and-what-strategies-am-i-allowed-to-use/).
- Dừng trước khi đọc bất kỳ giá giao dịch nào. Đếm **0** lượt Stage-0
  và **0** replay tài khoản. Không đổi danh mục `BASE_GUARD` hoặc
  trạng thái `NOT_QUALIFIED`. Chỉ mở lại khi có cấu hình và lịch sử
  lệnh cùng phiên bản của một robot trong đúng 12 định danh đã khóa.

Bằng chứng local tại
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/prop-atc-2011-cohort-20261119/`.
Đã kiểm lại 12 định danh, 24 URL hồ sơ, liên kết báo cáo, giải nén JSON và
SHA256 của bảy đầu vào.

| Artifact | SHA256 |
|---|---|
| `registration.md` | `fbdf71afc98a4a3cecf70c923272ff366a0763c7f75b5d5ecb83370264349f8c` |
| `official-equity-chart.png` | `42864f9dd421f8e00c0fb9f43ed91b1dd34f6c7c04ad2d1b9b2a8ddd84145954` |
| `atc-2011-admission.json.zst` | `3a0d6e9138d81f7617d61c4aa4b486b8f3c6028690009533d8a0bedc23cb99c6` |

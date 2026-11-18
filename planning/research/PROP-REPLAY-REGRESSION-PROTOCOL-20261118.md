# Đợt hồi quy BASE_GUARD và nguồn giá độc lập

18/11/2026. Mở một đợt có nhiều bước nối tiếp. Giữ hồ sơ các lần chạy
cũ, tự xử lý lỗi tái hiện được rồi kiểm ảnh hưởng trước khi quyết định
có cơ sở nối portfolio replay. Tập giá 2024–2026 vẫn khóa. Đợt này không
thêm tín hiệu, đổi sizing, đổi điều kiện Stage‑0 hay gửi lệnh.

1. **Hồi quy kỹ thuật.** Sửa bộ chọn điểm định giá M1/H1 để cả điểm yêu
   cầu lẫn giá được trả hợp lệ đều nằm trước cutoff loại trừ. Index dự
   phòng khi thiếu giá cũng phải thuộc phần đã cho phép. Tái hiện giá
   đúng tại cutoff được chấp nhận trong bản cũ. Đối soát các caller và
   chạy focused tests. Chỉ sửa kết quả đã công bố khi xác định được
   input thực sự bị ảnh hưởng.
2. **Đối chứng Stage‑0 với sổ đã có.** Giữ toàn bộ 340 lệnh đã nhận của
   BASE_GUARD Development và nguồn V14 M1 có SHA. Từ cùng giá vào, chiều
   và số lot tham chiếu theo risk 150 USD, đo một đối chứng chỉ thoát
   theo deadline nhân quả của V19, gồm cả lịch/timeout đã có nếu phát
   sinh. Chọn M1 Open từ mốc đó đến tối đa 60 giây sau, trong cùng ngày,
   rồi đối chiếu PnL sau phí với sổ PRIMARY và STRICT được lưu. Không
   bỏ mẫu thiếu giá, không đổi deadline hoặc chi phí. Báo theo nhánh,
   từng năm, hai cụm 2018–2020 / 2021–2023 và cùng các lệnh đủ định giá.
   So chi phí/SL tự nhiên, lập bảng so sánh điều kiện markout, cadence
   và net SL-active. Đây là cohort đã qua cổng của incumbent, không
   dùng để ước lượng tỷ lệ Stage‑0 bỏ sót trên tín hiệu thô mới. Không
   xếp hạng các biến thể hoặc sửa luật từ phản thực này.
3. **Nguồn tick độc lập cho 10 khoảng ưu tiên.** Dùng `gap-ranking`
   của Nhịp 1, đúng ba lệnh EURUSD F5 trong tuần ISO 2021-W21, 2021-W28,
   2022-W01. Lấy ba file FXCM công khai phục vụ nghiên cứu cá nhân,
   chỉ lưu raw tại E và kiểm SHA. Đọc UTC, thứ tự, lưới giá, Bid/Ask
   và phạm vi. Đếm giá trong từng phút thiếu và hai phút kề có giá.
   Kiểm phía thoát có chạm SL gốc không. Nếu các giao dịch dùng P0,
   định giá một sensitivity toàn vị thế trên **riêng feed FXCM**, từ
   quote đầu tiên không sớm hơn entry đã khóa (tối đa 60 giây), tới
   quote đầu tiên không sớm hơn deadline đã khóa (tối đa 60 giây),
   dùng stop nguyên gốc và giá đầu tiên thực sự xuyên stop để thoát.
   Dùng cùng lot và phí chuẩn của V19. Giữ unknown nếu thiếu đầu mốc
   hoặc có khoảng gián đoạn giữa tick quá ba phút trong khi giữ lệnh.
   FXCM là nguồn indicative. Bằng chứng có đoạn giá từ FXCM kiểm được
   độ nhạy khác nguồn, không chứng nhận first touch của Dukascopy hay
   FTMO. Không ghép nến hai nhà cung cấp hoặc điền lại source V19.
   [Timeline khoảng ưu tiên](PROP-N1-RESULTS-20261118.md) ·
   [FXCM TickData](https://github.com/fxcm/MarketData/blob/master/TickData/README.md)

Kết quả hồi quy xác định việc tiếp theo trong đợt. Có lỗi ảnh hưởng thì
kiểm lại đường bị ảnh hưởng. Có giá nguồn độc lập thì thực hiện phép
kiểm độ nhạy ba lệnh trong bước 3. Chỉ cân nhắc chạy lại toàn danh mục
nếu có đủ dữ liệu và quy tắc admission để kết quả có thể dùng ra quyết
định. Giữ baseline, sample split và lịch sử đã xem ở mốc bàn giao.

# S01 — chẩn đoán sai lệch nguồn trước economics

Đăng ký ngày15/11/2026, sau source admission và trước mọi kết quả tài chính
mới. Không thay protocol/registration hoặc proof đã khóa của S01.

Admission tại source commit `8e354d5` đọc3.576giờ/25.537.048tick: không giờ rỗng,
không held gap>15phút trên300tín hiệu. Có4 OHLC mismatches, hai phía Bid/Ask tại
2022-10-18 12:00 và15:00UTC. Trạng thái giữ `SOURCE_REVIEW_REQUIRED`;
economics-v1 chưa register/chạy. Không loại ngày này hoặc chấp nhận sai số.

Nguồn H1 cũ là candle endpoint riêng, không phải tick aggregation. Review
độc lập giải mã integer/struct hai payload tick khớp binary byte-for-byte,
13.581 và17.936records. Hai giờ đều sau decision08:00UTC của ngày đó; Wilder
ATR có thể ảnh hưởng SL của ngày sau. Vì vậy không suy ra cohort không đổi
chỉ vì entry hiện tại đã xảy ra trước sai lệch.

## Câu hỏi và ngân sách source-only

1. Fetch độc lập tối đa4public requests: đúng hai giờ tick và hai candle books
   H1 BID/ASK tháng10/2022, cache mới dưới `source-discrepancy-review/` của S01.
   Một call/endpoint, concurrency1, deadline10phút; auth/rate-limit/error giữ
   unknown, không lách hoặc retry thêm. Khóa request list trước fetch.
   So hash/OHLC với payload cũ để phân biệt lỗi local và khác biệt backend.
2. Tạo một diagnostic overlay **chỉ hai giờ** trong bản sao H1 dùng để sinh
   tín hiệu; OHLC lấy đúng tick nguồn đã đối soát, không chọn theo lợi nhuận.
   Dùng warmup2021-11-01 và toàn Dev2022–2023 với generator hiện có, một cell
   `GBPUSD.SWEEP.ASIA.LONDON.DAY`; mọi rule, thời gian, ATR, hệ số SL giữ nguyên.
3. So exact event census/decision/side/SL giữa original và overlay. Kiểm baseline
   generator tái lập300events vàstop của registration trước; không khớp thì
   dừng chẩn đoán, chưa mở một nhánh strategy mới. Báo ngày/bars/stop thay đổi,
   không tính entry/exit economics, winrate, DD hoặc chọn bỏ lệnh.

Overlay này là phép hỏi độ ảnh hưởng nguồn, chưa là dữ liệu mới được admit
cho PnL. Mọi sealed artifacts/V3 giữ nguyên. Nếu cần source-corrected study,
phải freeze revision mới, input/producers/cohort/acceptance trước outcomes;
giữ đầy đủ khác biệt với S01. Không tự sửa proof cũ thành PASS.

Không đọc giá2024–2026, không V4, không paid provider hay broker. Mọi output
đều ở thư mục riêng của chiến dịch solo; chi phí/phương pháp chiến lược không
thay đổi trong diagnostic này.

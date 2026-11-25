# Stage‑0 US500 — phân kỳ giữa giá chỉ số và VIX

Một cấu hình `US500-VIX-DIVERGENCE-B0` để kiểm tra vai trò bổ sung cho
BASE_GUARD. [Bài đo thiếu hụt vòng 1](PROP-PHASE1-SHORTFALL-20261118.md)

## Giả thuyết và lịch sử thử

VIX lấy giá quyền chọn SPX để đo biến động kỳ vọng trong 30 ngày. Nghiên
cứu về quan hệ đồng thời giữa VIX và giá S&P 500 ghi nhận mối quan hệ
âm trung bình. Giả thuyết mới đặt câu hỏi khi hai biến cùng tăng hoặc
cùng giảm giữa hai phiên đã đóng, liệu US500 có đảo ngược chiều biến
động đó trong phiên sau. VIX đo kỳ vọng biến động, nên bản thân việc VIX
tăng không cho biết hướng. Quy tắc đảo chiều và chân trời dưới đây là
giả thuyết kiểm định riêng, chưa có bằng chứng cho CFD hoặc phí đích.
[Cboe](https://www.cboe.com/tradable_products/vix/faqs) ·
[Nghiên cứu quan hệ đồng thời giữa VIX và S&P 500](https://www.sciencedirect.com/science/article/pii/S0378426613004172)

F3/F4 dùng vùng nén hoặc động lượng từ chính giá vàng. F5 dùng quét
biên EURUSD. N1 dùng thay đổi giá spot/index liên thị trường trong giờ.
Ứng viên này dùng thêm quyền chọn qua chỉ số VIX cuối ngày. Họ US500
đảo chiều đã có R075, RS08 và reversion theo ngày. Các bản đó dùng gap
qua đêm, xác nhận mở phiên hoặc biến giá US500. R080/R081 đã xem xét ý
tưởng dùng VIX nhưng đo cửa sổ EU từ giá US500; không mở lại các công
thức đó. Không dùng lịch sử tháng yếu của BASE_GUARD để chọn giờ, chiều
hay ngưỡng. [R075](US500-OVERNIGHT-REVERSAL-PROTOCOL-20261109.md) ·
[R081](US500-INVENTORY-CONDITION-PROTOCOL-20261109.md) ·
[Nhịp 1](PROP-N1-RESULTS-20261118.md)

## Công thức duy nhất

- Development 01/01/2018–31/12/2023; hai phiên lịch đầu mẫu làm warmup.
  VIX dùng FRED `VIXCLS`, chuỗi giá đóng cửa Cboe theo ngày. Dùng CSV
  giới hạn cứng đến 31/12/2023 và lưu hash. Đây là chuỗi lịch sử tải
  hiện tại, chưa đối soát snapshot phát hành từng phiên. Giá VIX mang
  ngày phiên trước trở về trước, không dùng quan sát ngày đang xét.
  US500 dùng M1 Bid/Ask native qua index V11 và lịch cash NYSE địa phương
  có hash. Cặp cash-close CFD và daily close VIX có thể khác giờ.
- Mỗi phiên NYSE thường, lấy mức đóng cửa của **hai phiên cash liền
  trước** theo lịch, kể cả mốc kết thúc sớm của phiên trước. US500 dùng
  Bid Close của nến M1 cuối cùng của mỗi phiên, VIX dùng daily close
  cùng ngày. Thiếu một quan sát thì predictor unknown. Xét thay đổi
  của hai chuỗi từ phiên cũ tới phiên gần hơn. Hai thay đổi cùng dương
  thì `SELL`, cùng âm thì `BUY`. Các trường hợp khác đứng ngoài. Không
  dùng ngưỡng biên độ, bộ lọc phụ, hoặc chọn bên theo outcome.
- Quyết định 10:30 New York, sau khi đóng đủ 60 nến phiên mở cửa
  09:30–10:29 để đo stop tự nhiên. BUY đặt thước đo dưới đáy Bid giờ
  đầu một bước lưới native, SELL trên đỉnh Ask một bước. Thiếu phút
  trong giờ đầu giữ tín hiệu thô và markout nếu có giá, với stop chưa
  biết và không đạt cap phí. Không nới stop hoặc mô phỏng chạm stop.
- Chọn M1 Open đầu tiên trong 60 giây từ quyết định. Thoát ở M1 Open
  đầu tiên trong 60 giây sau đúng **4 giờ** kể từ entry. Một mốc đo.
  BUY Ask→Bid, SELL Bid→Ask. Phiên kết thúc trước 16:00 bị bỏ qua theo
  lịch vì không đủ thời gian. Định giá trong cùng ngày UTC, trước giờ
  cash close. Không phát sinh swap. Giữ các trường hợp thiếu endpoint
  trong mẫu số. Không dùng lịch tin làm biến đầu vào.
- Phí stress kế thừa V11/V26 với spread Bid/Ask quan sát trên M1,
  commission 0,50 điểm/chiều và slippage 0,75 điểm/chiều. Tổng ngoài
  spread 2,50 điểm/vòng. Net đã gánh spread qua cặp giá. Dùng spread
  entry và 2,50 điểm để đo trần ma sát. Phí là giả định nghiên cứu,
  chưa đối chiếu dịch vụ đích. Một điểm là một đơn vị giá của chỉ số.

## Cửa chuyển bước

- Từng năm cần ít nhất 40 tín hiệu thô, đủ predictor cho 99% phiên có
  lịch sau warmup và đủ endpoint cho 99% tín hiệu thô. Báo BUY/SELL,
  tháng trống và số ngày có cơ hội khi BASE_GUARD không mở lệnh. Đếm
  lệnh BASE_GUARD từ sổ Development đã lưu.
- Net markout stress trung bình dương và ít nhất bằng ma sát stress
  trung bình mỗi năm. `Median friction / median natural SL ≤ 12%` và
  ít nhất 50% tập tín hiệu thô qua cap 12%, tính unknown vào mẫu số.
  Báo quantile và CI 95% theo block tuần (2.000 lượt, seed 261118).
- Mọi cửa đạt mới chuyển giao thiết kế replay cùng ngân sách risk.
  Có cửa rớt thì giữ kết quả và gác đúng công thức. Không đổi ngưỡng,
  hướng, thời gian, asset, hoặc chạy bot, Challenge hay dữ liệu 2024–2026.

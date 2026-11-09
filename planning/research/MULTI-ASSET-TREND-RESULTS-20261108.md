# Trend ba thị trường: chưa giữ để phát triển bot challenge

Đã chạy và kiểm lại theo [protocol khóa trước kết quả](MULTI-ASSET-TREND-COMPONENT-20261108.md).
**Bản mixed 1/3/12 tháng không đạt tiêu chí nghiên cứu tiếp.** Giữ bản âm và
benchmark; không giảm phí giữ lệnh, tăng đòn bẩy hoặc chọn lại thị trường để cứu
kết quả. Goal tìm ứng viên vẫn active; đây không phải kết luận mọi trend đều thua.

## Kết quả và cách hiểu

Vốn toán học ban đầu 10.000 USD, NAV liên tục trong 84 tháng 2018–2024.
Đây là proxy phân bổ EURUSD/vàng/US500, không phải tài khoản có lot tối thiểu,
SL, margin hoặc đường equity đủ để kiểm luật quỹ. December 2024 còn mở và được
mark, không đóng giả cuối mẫu. Các năm là attribution theo tháng phân bổ,
không phải return tài khoản theo ngày lịch; dữ liệu đã exposed, không clean OOS.

| Recipe / kịch bản phí | Gross USD, đã gồm Bid/Ask | Funding USD | Net USD | Số năm dương | Drawdown tại điểm tháng |
|---|---:|---:|---:|---:|---:|
| Mixed trend / reference | +679,62 | 1.768,92 | −1.138,18 | 2/7 | 18,37% |
| Mixed trend / stress | +494,21 | 3.918,86 | −3.519,01 | 0/7 | 36,90% |
| Always long / reference | +2.367,35 | 3.140,14 | −843,46 | 4/7 | 24,80% |
| Always long / stress | +1.794,90 | 5.386,84 | −3.722,27 | 2/7 | 42,23% |

Net còn trừ commission/slippage: primary reference 15,89/33,11 USD;
stress 13,56/80,96 USD. CostModel round net từ các số chưa round; vì vậy cộng
các cột tiền đã round có thể lệch vài cent so net. Không sửa ledger để ép khớp.
Final open mark chỉ ghi entry fees và funding, cash/floating báo riêng.

Primary stress theo cohort year: 2018 −950,16; 2019 −910,13; 2020 −173,37;
2021 −485,31; 2022 −420,46; 2023 −529,96; 2024 −49,62 USD. Hai block đã khóa
2018–2020 / 2021–2024 lần lượt −2.033,66 / −1.485,35 USD. Không đạt ending NAV
dương, ≥5/7 năm stress dương hoặc hai block dương; không promote.

**Bài học có giới hạn:** trong recipe và hai kịch bản đã khai báo, lợi nhuận
giá không bù phí giữ exposure nhiều tháng. Các phí này chưa được xác minh là
historical FTMO/The5ers hoặc cận trên phổ quát. Kết quả không bác bỏ paper
futures/forwards, mọi CFD broker, các thị trường khác hoặc một recipe khác.
Benchmark cũng âm; inverse-vol tự nó không tạo lợi thế sau phí. Không lấy
funding bằng 0 làm ứng viên mới hoặc suy ra lợi thế khi bỏ phí.

## Đã kiểm, lưu và tối ưu gì?

- Sáu focused tests đạt: tín hiệu/weights, history thiếu hoặc biết trong tương
  lai, execution price không làm đổi weights, funding/triple, final open mark,
  84 tháng NAV liên tục bằng shared CostModel. Code commit `4c2e15e` sau protocol
  commit `0a9861a`; lỗi scope biến trong test được sửa trước numeric, không đổi rules.
- Bốn books đều đủ 84 tháng × 3 assets: **1.008 weights và 1.008 allocations**
  được kiểm bằng float sample standard deviation và Fraction money/funding,
  không import producer signal/cost functions. Nguồn entry/exit, clock,
  continuous sizing, cash/floating, cohort và endpoint DD khớp.
- Năm mutations bị chặn: false authority, thiếu tháng, sai weight, sai net,
  tính exit fee ở final mark. Đây là cùng agent/provider dùng code khác;
  chưa là independent human/model/feed review hoặc full account validation.
- Dùng lại [864 source records đã review](MULTI-ASSET-MONTHLY-INPUT-RESULTS-20261108.md),
  kiểm hash dataset/config/quality/manifest/source-review. Không đọc raw 14 GB
  lần nữa cho số học; giữ nguyên source/raw hashes và lịch sử âm. Không thêm
  database, service, RAG hoặc dashboard trùng Paperclip.

| Lát | Thời gian thực đo |
|---|---:|
| Chuẩn bị source chung, từ lượt trước | 154,861 giây |
| Kiểm nguồn riêng, từ lượt trước | 15,442 giây |
| Numeric + preflight + ghi 4 books | 1,416 giây wall / 0,891 giây CPU |
| Từng book | 0,184–0,199 giây |
| Review số học/state và mutations | 1,488 giây |

Đây là tái sử dụng dữ liệu hợp lệ; không so 1,4 giây với full tick replay như
speedup cùng workload. Bốn books tính nhanh; nút thắt hiện tại là chất lượng
giả thuyết và economics/target contract, chưa có lý do tối ưu kernel/GPU.
Không có failed numeric attempt hoặc worker nền còn chạy trong lát này.

Private root:
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`.
`execution-v1/multiasset-monthly-trend-component-v1` giữ config/manifest,
source snapshots, 4 books, result/events/progress/arithmetic-review.
Runner và reviewer ở campaign root. Result SHA
`09c148b1fbf009d54649f7a3c2d43b3c0b32b02be9cf2fd230494e368902560a`;
reviewer SHA `609aaffce9ca4257cb83ca57bc6c9eb37a76606054dd9778b368f1c2580c530d`.
0 network/model/broker calls; không mở 2025+.

## Quyết định và bước kế tiếp

Giữ R010 exact adaptation ở mức negative component; không tăng số policy
bot đã triển khai bằng hai proxy books. C1/C2 vẫn chưa đạt. Thay đổi tiếp phải
có lý do khác với hạ phí hoặc tuning trên cùng kết quả. Ưu tiên khảo sát một
cơ chế có holding ngắn, có thể thực thi bằng nguồn hiện có và chưa lặp exact
versions đã gác; khóa hypothesis/data/cost/retention trước outcome mới. Gold
SMA50k vẫn là survivor lịch sử có gaps, không được tự nâng thành challenge.

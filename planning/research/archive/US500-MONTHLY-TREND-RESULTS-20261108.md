# Xu hướng tháng US500: âm theo phí đã khai báo, dữ liệu chưa đủ cho toàn kỳ

**Admission đã kiểm lại trên source-only:** [long correction/results](INDEX-LONG-EXPLICIT-RESULTS-20261108.md)
ghi32/132tháng eligible,2014–17 không có tháng đủ input. Cảhai policy bị guard
chặn trước portfolio simulation,0simulationcalls; không rerun PnL hoặc bỏ năm
thiếu. Các bảng dưới giữ historical expanded-view/unadmitted semantics, không
là economic verdict của một chiến lược monthly chạy trên dữ liệu đầy đủ.

**Chưa đủ cơ sở giữ làm ứng viên challenge.** Lượt đã chạy theo
[protocol trước kết quả](US500-MONTHLY-TREND-PREPARATION-20261108.md), không
tune horizon/stop/risk/phí sau outcome. Một tài khoản 10.000 USD liên tục,
2013 warmup và 2014–2024 đánh giá, planned risk 25 USD/lệnh; không reset mỗi năm.

| Phiên bản | Net chuẩn, USD | Net stress, USD | Entry / đã đóng | Cuối 2024 |
|---|---:|---:|---:|---|
| R009: xu hướng 12 tháng | −675,49 | −1.408,24 | 31 / 30 | 1 vị thế mở |
| R053: benchmark luôn long, cùng lịch/SL/risk | −421,62 | −1.111,62 | 21 / 20 | 1 vị thế mở |

Net đã gồm funding và floating cuối kỳ; không tạo lệnh đóng giả. Momentum
stress có 2 năm dương, các block 2014–2017 / 2018–2020 / 2021–2024 lần lượt
−94,11 / −902,91 / −411,22 USD. Benchmark cũng âm ở cả ba block. Không đạt
heuristic đã đăng ký, không chứng minh cả họ xu hướng vô dụng.

Funding chuẩn/stress của momentum là 747,68 / 1.477,62 USD; benchmark
699,80 / 1.388,72 USD. Phí giữ lệnh là giả định cố định theo calendar day,
**chưa phải lịch sử swap/dividend của FTMO**. Không giảm phí để cứu outcome;
khi có thông số thực thì cần version cost/input mới và giữ kết quả cũ.

## Thiếu sót admission đã tìm và sửa sau lượt chạy

132 tháng đánh giá chỉ có **83 tháng** đủ lịch sử tín hiệu và có quote ở phút
khớp đã quy định. 2015–2016 đều 0 tháng hợp lệ; 2014 chỉ 2/12, 2017 chỉ 1/12.
Các năm sau: 2018 12; 2019 12; 2020 10; 2021 11; 2022 12; 2023 11; 2024 12.
Thiếu month-end close hoặc daily ranges làm lịch sử 13 tháng/ATR không hợp lệ.
Hai năm 0 USD **không là bằng chứng kinh tế của chiến lược**.

Lượt đầu chỉ kiểm raw/calendar/accounting, chưa chặn việc đưa cả năm không
dùng được vào scope nghiên cứu. Đã bổ sung `prepare`/`input_coverage` trong
policy: giữ nguyên tín hiệu, xuất lý do thiếu history/ATR và kiểm coverage
riêng; `simulate` chặn trước numerical book nếu có evaluation year không có
tháng dùng được. Năm đầu chỉ warmup, không bị tính nhầm là năm lỗi.

Quote phút khớp là audit lịch sử, **không được đưa thành điều kiện biết trước
ở lúc phát tín hiệu**. Bảy policy tests gồm future-prefix, dấu return, 13 mốc
tháng, ATR tính tay, missing month, no-dispatch gate và missing future fill đạt.
Fixture ATR ban đầu bỏ sót gap giữa tháng; đã sửa expected value theo tính tay
2,625 trước PnL, không sửa stop multiplier để test pass.

Post-run audit trên raw hashes thực đối chiếu **576 decision records** của hai
policy × hai costs: time/side/distance exact với source preparation mới, trong
26,60 giây, 0 simulation/network calls. Source admission mới sẽ chặn chính bộ
input này; không ghi đè/relabel attempt cũ thành đã được admission trước đó.
Không có rerun backtest hoặc chọn bỏ hai năm để báo retention tốt hơn.

## Kỹ thuật và bằng chứng

| Lát đo | Thời gian / phạm vi |
|---|---|
| Load/hash input một lần | 25,36 giây, 4.744.227 M1 pairs |
| 4 numerical scenarios + 2 null controls | Khoảng 333,35 giây trong shared book |
| Toàn job | 370,32 giây wall; 368,42 giây CPU |
| RAM quan sát | Khoảng 5 GB working set; chưa đo peak |
| Post-run input/plan audit | 26,60 giây; không chạy lại numerical scenarios |

Cả sáu scenarios đối soát entry/lot/SL/cost/funding/cash/floating và null0;
annual marks cộng lại đúng final equity. Hai fixtures BUY/SELL xuyên năm tính
tay kiểm funding đúng năm và chặn final-equity tamper. Reviewer có 9 tests
liên quan đạt sau vá; không independent human/model sign-off. Mỗi policy có
1 entry/exit record ở phút cả hai volume bằng 0; không tự coi đó là quote mới
hay broker-fill proof. M1 stops và missing paths chưa native index/prop DD.

Artifacts: private campaign `execution-v1/us500-monthly-trend-v1` giữ protocol,
source snapshots/input seals/results/reviews/progress/log; source trước admission
guard được giữ trong snapshot. `us500-monthly-input-review-v1` bind source mới,
parent source/result và actual raw hashes. Không 2025+, broker hoặc model calls.

## Quyết định tiếp

Ưu tiên **data/clock và target-cost fit**, chưa mở grid horizon/SL hoặc tải thị
trường mới hàng loạt. Cần phân biệt missing month endpoint, lịch cash reference
với CFD sessions và unavailable provider requests; không điền close giả. Có
thể kiểm bổ sung đúng phút thiếu từ raw ticks nếu source audit/protocol cho phép;
giữ dataset version cũ và đánh giá lại phần thực sự bị ảnh hưởng.

Kiểm 08/11: [FTMO account specifications](https://ftmo.com/faq/what-are-the-account-specifications/)
chỉ tới specification trong platform hoặc [Symbols](https://ftmo.com/en/symbols/).
Bản đọc web chưa expose US500. Browser thực tải lỗi `ERR_CONNECTION_CLOSED`,
sau đó URL policy chặn trang lỗi `data:`; không thay cấu hình mạng để bypass.
Không thấy listener8010/owned MT5 trong lần kiểm local; snapshot FTMO02/11
đã tìm là EURUSD, không được gắn nhãn US500 hoặc coi là giá/phí hiện tại.
Chưa xác minh được target geometry/financing/dividends. Các kết quả trên giữ
nhãn declared scenario; **C1/C2 campaign chưa hoàn tất**.

# Hai phép thử local-flow: chưa đủ để viết bot challenge

Thực hiện [protocol](LOCAL-FLOW-TWO-FX-PROTOCOL-20261108.md), commit `7499d0d`
trước số mới. **Cả R059 và R060 đều không đạt tiêu chí giữ đã đăng ký.**
Không đảo side, đổi giờ hoặc chọn control để cứu kết quả.

## Kết quả dễ đọc

Đây là tổng pip của các cơ hội theo **1 standard lot**, không là lợi nhuận
account 10k hoặc bot có risk 0,25%. Giá dùng source H1 Open proxy; chưa xác
minh actual joint tick/fill time. Commission 5USD roundtrip, BidAsk embedded;
reference slip0, stress0,00002 mỗi side. Costs vẫn là kịch bản khai báo.

| Recipe primary, 2010–2024 | Có kết quả / weekdays | Net phí chuẩn, pip | Net phí cao, pip | Năm dương phí cao |
|---|---:|---:|---:|---:|
| R059 BUY GBPUSD 08–16 New York | 3.894 / 3.913 | −181,0 | −1.738,6 | 7/15 |
| R060 SELL AUDUSD 10–16 Sydney | 3.879 / 3.913 | −11.854,2 | −13.405,8 | 1/15 |

| Block phí cao | GBPUSD, pip | AUDUSD, pip |
|---|---:|---:|
| 2010–2012 | −763,2 | −2.136,7 |
| 2013–2015 | +245,8 | −3.062,5 |
| 2016–2018 | −448,6 | −2.871,5 |
| 2019–2024 | −772,6 | −5.335,1 |

GBPUSD có 19 missing entry. AUDUSD có 33 missing entry và 1 entry hợp lệ nhưng
missing exit; giữ toàn bộ ngày, không xóa khỏi denominator hoặc ghi lãi/lỗ=0.
Trong component này không endpoint Open nào bị crossed; nguồn tổng thể vẫn
[chưa full joint admission](FX-H1-HISTORY-RESULTS-20261108.md). Sydney boundary
được tra qua các năm UTC đã có; thiếu năm 2009 không tự bù hoặc download.

Không đạt không có nghĩa mọi local-flow strategy đều vô dụng. Nó bác việc
ưu tiên viết risk-wrapper cho **hai exact recipes** này, trên feed/costs đã
khóa. Paper SNB cũng cảnh báo costs xóa phần lớn trading returns; nghiên cứu
cũ không bảo đảm hiện nay có lợi nhuận. Không SL/account/prop/clean OOS ở đây.

## Kiểm chứng và hậu kiểm kỹ thuật

| Lát | Bằng chứng | Quyết định |
|---|---|---|
| Trước PnL | 12 preflight checks: cost/side, missing/crossed Open, DST New York/Sydney, UTC previous-year, future-exit không lọc entry | Đạt trong scope component |
| Nguồn và phiên bản | Bind 60 source books, source review/quality/rawbindings, protocol, runner/reviewer và helpers trước số; không sửa raw | Reuse, không tải lại |
| Kiểm chéo | 7.826 events, 31.092 financial cases và 120 summaries; calendar/Fraction code khác kiểm tất cả rows | Khớp; cùng agent/provider, không independent audit hoặc tick proof |
| Test phá dữ liệu | 7 mutations giá, fake tick time, sai clock, sai side, sai net, lọc entry theo exit, false authority đều bị reject | Đạt phạm vi đã kiểm |
| Tính số | 5,431s wall / 5,109s CPU | Đã đủ nhanh, chưa có lý do thêm GPU/Rust |
| Review | 2,919s wall | Không rerun numeric hoặc full source history |
| Vận hành | PID7048 terminal0; reviewer terminal0; không failure/retry, network/model/broker calls=0 | Không còn job của lượt này để chờ |

Đã áp guard quan trọng cho dữ liệu đa múi giờ: source lookup theo UTC timestamp
xuyên các file năm, thay vì ép ngày Sydney vào file cùng năm local. Đây là
phần triển khai recipe mới, không phải kết luận backtests trước bị lỗi. Giữ
raw/frozen artifacts và các bài cũ nguyên vẹn. Không cần skill/framework/RAG
mới: source-transformations và research/qualification đã bao phủ workflow.

## Evidence và bước tiếp

Private campaign root:
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`.
Output `execution-v1/local-flow-two-fx-v1` có config/manifest/source-snapshot,
per-year events, summary/result/review, progress/events. Runner
`run-local-flow-two-fx-v1.py`, reviewer `check-local-flow-two-fx-v1.py`.
Result SHA `87c0687f2f61108097ef132feb7ba1ecf3791fe7015b584856a8fa64b9cd20c5`;
reviewer SHA `7cbb57165563e95750acfb9546e9d519bb6c5edc6d768fa58abb151d914b77af`.

Catalogue: **60 hồ sơ / 42 research policy versions**, không tăng policy count
bằng pricecomponents. Chưa có ứng viên challenge-qualified, Goal C1/C2 active.
Lát tiếp cần cơ chế khác fixed-hour unconditional flow; so relative/cross-market
signals với data hiện có và costs/funding phù hợp trước khi đăng ký economic
experiment mới. Không scan controls/giờ hoặc mở thêm dữ liệu chỉ để tiếp tục.

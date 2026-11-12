# Phá kênh20: kiểm tần suất trên quá khứ sâu hơn

12/11/2026. Owner yêu cầu kiểm FP07 trên các năm cũ. **Chỉ cùng tín hiệu và
đơn vị frequency-only đã khóa**, không PnL, exit/risk/cap/account changes.
Parent [protocol](US500-OPPORTUNITY-SCREEN-PROTOCOL-20261112.md),
[kết quả2022–2024](US500-OPPORTUNITY-SCREEN-RESULTS-20261112.md).

## Phạm vi trước số đếm

- Chín năm**2013–2021**, tất cả đều phải báo, không chọn lại năm theo outcome.
  Reuse cache `us500-long-explicit-source-v1`, đã sửa carried-close padding và
  kiểm source/native decoder ở [long source correction](INDEX-LONG-EXPLICIT-RESULTS-20261108.md).
  Không2012: chưa có accepted full-year explicit-source proof; không tải thêm.
- Accepted source receipt `result.json` SHA256
  `30cdcf5be9eed1e84953e5d0fd72bbb63028904eb01062a5908b60d4b7e0831f`;
  manifest `ed9aab08e0d89fddee0e20ee76b83dc6e0ab8a119c7dd88e8eab8d8c18683edc`.
  Lấy proof/reader/native-oracle hashes từng năm từ receipt đã accepted, không
  tự tính hash một nguồn bất kỳ rồi coi là được admit.
- Chỉ dùng frozen cash calendar có hash trong source proof của chính năm đó.
  Nguồn không đủ/binding sai thì giữ failure, không synthesize hoặc xóa gaps.
- Data2013–2021 đã consumed bởi research khác; đây là mở rộng mô tả theo thời
  kỳ, **không clean OOS**, không coi chiến lược đã chứng minh ngoài mẫu.
-2022–2024 reuse savedFP07 metrics/events/hash và kiểm source rule identity,
  không chạy lại numerical study không đổi. **2025+ vẫn đóng**.

## Giữ nguyên luật

Reuse nguyên hàm FP07 `triggers` và `cadence`, cùng native-indicator preparation:
M15 cash-only, prior20high/low, current closedATR14Wilder/đệm0,10ATR, BUY/SELL,
decision10–15NY, fullsession, causal gap block và20barhistory reset sau missingM15.
History qua ngày cash; mỗi năm reset như parent2022–24, không warmup năm trước.
One event/breakout episode; báo raw events và signal đầu ngày có đủ cặp quote
tại decision/decision+60s. Không chọn signal sau nếu signal đầu thiếu quote.
Không orders/fills/positions/SL/fees/edge hoặc broker compliance.

`us500_year_source` thêm explicit registered-year scope cho caller; default
cũ giữ, dù override cũng không đọc2025+. Receipt/proof/canonical4quarter
guards giữ nguyên. Consumer cũ không được tự mở lịch sử chỉ vì helper mở rộng.

## Dữ liệu thiếu và cách báo

Mẫu số chính giữ toàn bộ cash calendar, không chỉ ngày có lệnh. Báo từng năm:
rawtriggers, firstsignal/day, quoteavailable, tuần0, monthly min/median/max,
per5scheduledsessions; pairedcashM1 observed/expected; normal/short sessions,
ngày có thiếu giá trước/trong cửa10–15NY, ngày có đủ dữ liệu cả cửa/phiên.
Coverage full-day chỉ chẩn đoán sau count, **không lọc entry bằng tương lai**.

Nếu source gaps làm mất readiness/blocked ngày, tần suất quan sát thấp không
tự chứng minh thị trường ít cơ hội hoặc rule không bền. Không đổi denominator
sang ngày “đẹp”, điền giá thiếu, bỏ năm0signal hoặc gọi no-data là true-no-setup.
Nhịp và lợi nhuận là hai câu hỏi riêng; không chọn thêm thresholds theo count.

## Kiểm chứng và vận hành

Kiểm default/explicit-year guard, wrongproof và holdout-before-I/O; kiểm
source receipt/reader/oracle/calendar/canonical hashes; rule/preparation/runtime
lock hashes phải khớp parent cho semantics không đổi. Thống kê periods/cap và
BUY/SELL timestamp/clock census. Reuse9signaltests đã đạt vì rules không đổi.

Một writer, output mới, manifest/snapshots/inputadmission và từng năm được ghi
ngay khi xong; PID/events/progress/CANCEL, deadline600s. Không auto retry,
không sửa source giữa job. Failure giữ kết quả các năm đã xong; không claim
resume đang hỗ trợ chỉ vì có completed-year files.

Kết luận chỉ về cadence/coverage qua thời kỳ. Account catalogue123/88/53 giữ;
đây là additional window của **FP07 hiện có**, không frequency design hoặc edge
mới. Chưa mở financial screen hoặc tự promote sang challenge.

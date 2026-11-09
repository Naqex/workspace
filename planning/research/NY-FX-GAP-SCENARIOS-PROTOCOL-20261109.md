# NYFX: hai kịch bản có điều kiện cho phút không có quote

Đăng ký trước kết quả mới. [Bản strict](NY-FX-PAIRED-LATENCY-RESULTS-20261109.md)
vẫn là annual PnL chưa xác định; không sửa kết quả, dữ liệu hoặc protocol cũ.
Mục tiêu của lượt này là đo độ nhạy với mô hình khoảng trống, chưa xác nhận
khả năng chạy challenge.

## Căn cứ và phạm vi bằng chứng

Đã đọc lại tài liệu chính thức ngày 09/11:

- [Nautilus backtesting](https://nautilustrader.io/docs/latest/concepts/backtesting/)
  mô tả xử lý dòng sự kiện lịch sử. Điều này không chứng minh archive đầy đủ
  mọi biến động của thị trường hoặc target broker.
- [LEAN Immediate Fill Model](https://www.quantconnect.com/docs/v2/writing-algorithms/reality-modeling/trade-fills/supported-models/immediate-model),
  mục Stop Market Orders, phân biệt tick/bar và tránh dùng dữ liệu stale cho
  stop fills. Không sao chép fill model của LEAN hoặc lấy nó làm chứng nhận
  kết quả của mình.

Archive đã kiểm có 10 phút không có tick, 15.379 tick ở 10 giờ xung quanh và
1.180 nến theo side ở các phút có quote khớp hoàn toàn. Đây là nguồn để tạo
**mô hình có điều kiện**, không phải quyền điền giá vào các phút trống.

## Giữ nguyên chiến lược và định nghĩa hai kịch bản

Giữ MA4, TR14×1,5, các quyết định 10–13 New York, độ trễ 15/60 phút,
đóng lúc 15:00, SL, sizing, rủi ro 25 USD, commission/slippage, hai năm
2019/2022, control và null như paired protocol. Không điều chỉnh sau outcome.

Chỉ áp dụng cho đúng 10 phút trong source-only gap census đã freeze. Nguồn
M1, tick, review, raw seals và source H1 phải còn đúng hash; minute phải thiếu
cả hai side và không có tick. Minute có dữ liệu hoặc có intent/scheduled exit
không được dùng nhánh này; vẫn giữ unknown/rejection của mô hình strict.

1. **Observed events:** ở phút được xác minh không có event trong archive,
   không tạo nến, mark, fill hoặc cập nhật cash. Vị thế và SL vẫn tồn tại.
   Quote/bar tiếp theo được xử lý open-gap protection trước intent như cũ.
   Giả định: không có executable price event bị bỏ ngoài observed feed.
2. **Adverse envelope:** cùng cơ chế, nhưng giả sử có biến động không quan sát
   được trong phút trống, nằm trong cùng-side H1 envelope đã kiểm. Nếu low
   của BUY hoặc high của SELL chạm SL, đóng tại cực trị bất lợi đó, tính đủ
   phí/slippage. Ghi rõ đây là giá giả định, không quote/fill đã quan sát.
   H1 có dữ liệu sau decision chỉ dùng cho sensitivity của gap, không được
   đưa vào entry signal, sizing hoặc feature readiness.

Kịch bản 2 là một stress path xác định, **không phải lower bound toàn cục**:
đóng sớm có thể đổi re-entry, margin và cash về sau. Không suy hai kịch bản
bao trùm mọi đường giá hoặc cả hai dương là đủ proof edge. Không khẳng định
planned risk 25 USD giới hạn được gap loss. Cash giữ nguyên khi thiếu quote
không có nghĩa equity đã được đo hoặc không có daily drawdown.

## Cửa quyết định khóa trước

2 năm ×2 directions ×2 lags ×2 costs ×2 nulls ×2 gap scenarios =64 books.
Chỉ reversal15min là primary; phải known-flat **trong từng mô hình có điều
kiện**, net>0 và ≥100 closed trades ở cả hai stress years của cả hai scenarios
mới được ưu tiên nghiên cứu tiếp. Không promote momentum/control hoặc lag60
để cứu primary. Không nâng conditional PnL thành original exact PnL hoặc prop pass.

Nếu primary không đạt: gác exact recipe theo sensitivity evidence, giữ strict
unknown. Nếu đạt: tiếp selection-aware/OOS, gap uncertainty và native prop/
prospective checks trước bất kỳ đề xuất challenge nào. Không mở holdout mới,
provider/account/payment hoặc broker permissions trong lượt này.

## Kiểm chứng và dữ liệu

- Reuse runner/helper hiện có; nhánh strict mặc định giữ nguyên behavior.
  Code revision mới phải được ghi, giữ snapshot cũ và kiểm một actual strict
  book cùng focused tests trước scenarios. Không sửa pin của bản cũ để reuse.
- Synthetic BUY/SELL: không fill/mark trong observed silence; next-quote gap
  SL; adverse SL/extreme/cost; intent/exit/crossed/unregistered gap vẫn blocked;
  null cash và causal feature không nhận H1 future envelope.
- Reviewer Fraction riêng dựng signal/TR, gap paths, sizing/cost/cash/state
  cho đủ64books, mutations về gap claims/fill/quantity/net/authority; so closed
  prefix trước first gap với frozen strict outputs theo economic fields.
- Không download lại. Output mới `execution-v1/ny-fx-gap-scenarios-v1`, một
  writer/CANCEL/deadline300s, snapshots/config/pins/events/progress/timing/
  allbooks/result/review. Có log model assumptions và mọi gap event.

Đây là thay đổi mô hình nghiên cứu offline. Trader/runtime, live freshness,
risk grants và strict source policy không được nới. Existing research,
qualification, continuity và retrospective skills đủ cho lượt này.

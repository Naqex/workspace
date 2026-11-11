# Đếm cơ hội US500 trước khi chọn bộ luật tiếp

12/11/2026. Owner đồng ý làm bước đếm/phân loại cơ hội sau trao đổi về việc
thử có chọn lọc và vì sao US500 ít lệnh. **Chỉ frequency-only**, không backtest
PnL, không thay bot/runtime/risk/cap tài khoản. Khóa thiết kế trước số đếm mới.

## Câu hỏi và lineage

- Baseline ORB: reuse [R094 cadence đã lưu](US500-FREQUENCY-LANDSCAPE-20261111.md),
  không chạy lại financial screen hoặc phục hồi verdict kinh tế.
- Baseline reclaim: replay signal-only exact R123, đối chiếu saved FP05 traces.
- **FP06**: sau reclaim attempt bị expire/cancel, cho tìm setup mới ở **bar
  sau**, dừng mọi arm mới sau confirmation đầu ngày. Cùng R123 về MA20/80,
  arm10–14NY, confirm≤15NY/60phút, frozenATR14 và đệm0,10. Không rearm cùng bar,
  không retry sau confirmation/thiếu quote, không tính exits/positions.
- **FP07**: close M15 vượt đỉnh20 M15 **trước nến hiện tại** +0,10ATR hiện tại
  → BUY; dưới đáy20−0,10ATR → SELL. Đếm một lần khi bắt đầu một đợt ở ngoài
  kênh; phải quay vào kênh/đổi phía mới có đợt tiếp. History cash bars qua ngày,
  reset khi M15 thiếu. Related R001/Donchian; chưa là Donchian20/10 strategy.
- **FP08**: SMA20 vừa chuyển từ≤SMA80 sang>SMA80 → BUY; đối xứng SELL. Hai nến
  đóng liên tiếp cùng session, đủ hai MA. Related R002/SMA; không phải edge mới.

FP07/08 xét M15 closes10:00–15:00NY (slot30–330), BUY/SELL; không grid MA,
lookback, threshold, giờ hoặc holdout. FP07 cập nhật trạng thái trên mọi nến
đã đóng, kể cả trước giờ vào, để không coi một đợt đang có sẵn là đợt mới.
Các lookback/đệm là baseline có chủ đích tái sử dụng, chưa chứng minh tối ưu.

Lý do: phân biệt vấn đề một-attempt với điều kiện setup/confirmation quá hẹp;
đối chiếu hai trigger xu hướng đơn giản không đòi một chuỗi pullback. Đây là
ba related frequency designs, không ba independent edges hoặc account policies.
[Donchian upstream](https://www.quantconnect.com/docs/v2/writing-algorithms/indicators/supported-indicators/donchian-channel)
giữ khái niệm kênh high/low; quy tắc dùng **prior** bars ở đây do protocol khóa,
không coi indicator cập nhật currentbar là executable breakout không lookahead.

## Dữ liệu, timing và đơn vị

Chỉ accepted paired M1/cache/cash calendars2022–2024, shared source loader và
native-indicator preparation của parent. Exposure đã development; không2025+,
không fetch/rawdecoder mới, broker/model/account/provider. Shortsession không
emit; gap đã xuất hiện chặn ngày theo causal prefix, không xóa tín hiệu trước
gap tương lai. Warmup đúng từng rule, không yêu cầu common161/H1 không dùng.

Tín hiệu tại nến đóng. Quote check riêng ở decision và decision+60giây sau
khi tín hiệu tồn tại; đây là **availability**, không gửi lệnh/margin/fill.
Không dùng quote tương lai để thay đổi signal. Báo riêng:

1. Tổng trigger events (đợt rõ, không mỗi nến vẫn đúng điều kiện).
2. Trigger có đủ cặp quote cho model entry clock.
3. Chỉ giữ **confirmation/trigger đầu ngày**, rồi check quote riêng để so
   trần1/ngày; không chọn trigger sau khi trigger đầu thiếu quote.
4. Weekly/monthly/quarterly counts, giữ0, mean/median, tuần trống và chuỗi
   phiên không có tín hiệu dài nhất trong từng annual book.
5. Decision-slot reasons và unique days từng reason; days có thể chồng nhau,
   không cộng chúng thành unique-day census. Setup/arm khác confirm khác fill.

FP07/08 có thể có nhiều trigger/ngày; vì chưa mô hình exit/position/risk nên
không gọi raw triggers hoặc bản first/day là số trade có thể thực thi.
Tất cả calendar days vẫn giữ; không tự gọi warmup/gap là thị trường không setup.

## Kiểm trước và sau đếm

Fixtures BUY/SELL, strict equality, currentbar excluded khỏi kênh, episode
dedup, prior same-session cho MA cross, expiry/cancel→rearm bar sau, cap sau
confirmation, quote missing không đổi signal, gap/shortsession, future-prefix
invariance. Baseline reclaim confirm/arm trace phải khớp saved frequency attempt;
FP06 phải giữ các ngày baseline từng confirm, không mặc định nhiều hơn có lời.
Calendar/period sums và daily first-signal cap phải đối soát.

Một writer/output mới, pins/snapshots/input hashes, progress/events/PID,
CANCEL và600s deadline. Reuse controller save/source admission; không sửa
source khi run. Giữ failure attempt nếu có; không automatic retry.

## Quyết định cho phép

So dải ưu tiên3–5cơ hội/tuần5phiên và độ đều như **planning preference**, không
floor thống kê/edge. Không chọn theo PnL (không tính), không sửa các floor200
đã khóa của FP04/R123 hoặc chạy lại negatives để cứu. Kết quả chỉ quyết định
có đáng thiết kế một economic screen **đăng ký riêng** không. Chưa dispatch
financial/native orders trong task này; catalogue account counts giữ123/88/53,
thêm FP06–08 vào frequency-only history dù kết quả thấp/cao/failed.

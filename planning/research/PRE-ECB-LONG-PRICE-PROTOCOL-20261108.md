# PreECB: khóa kiểm tra lợi nhuận giá qua 13 năm trước risk wrapper mới

Tiếp [attribution](PRE-ECB-WRAPPER-ATTRIBUTION-RESULTS-20261108.md) và
[path risk](PRE-ECB-PATH-RISK-RESULTS-20261108.md): giá02NY→14Berlin từng dương
ở2019/2022, nhưng parent1,5ATR và cùng lot không cho kết quả tốt. Trước khi
thiết kế cách thoát mới, kiểm **clock/side/cost cũ** trên2010–2022. Không đổi
SL/lot/risk của parent, không lấy noSL component làm tài khoản challenge.

## Câu hỏi và các lựa chọn giữ nguyên

- Primary: SELL EURUSD mỗi weekday, entry02:00America/New_York, exit14:00
  Europe/Berlin cùng ngày; first actual quote at/after mỗi target≤60s.
  IANA clocks giữ riêng DST; không giữ tới14:15 hoặc chọn lại tháng/side.
- Opposite BUY cùng endpoints làm control, không được thay primary sau số.
- Tất cả weekdays2010–2022 có mặt trong denominator. Missing/late giữ unknown,
  không fill0/carry/interpolate/drop rồi gọi full-year account. Không SL/TP/
  lotsizing/portfolio/prop; mỗi phép đo1standardlot chỉ là đơn vị price/cost.
- Costs giữ observedBidAsk, contract100k,2,5USD/lot/side,slip0(reference) hoặc
 0,00002/side(stress),quote→USD1,sharedCostModel round2. Windows không qua
  declared22UTC funding event; không thay đổi phí historical carrybooks.
  Không nhận phí này là xác minh contract target FTMO/The5ers.
- Dùng raw-bound H1 cache được native loader hiện hành nhận: raw SHA, cache
  SHA/payload/schema/runtime/producer/count/order/grid đều phải đạt. Không
  rebuild/rebind old cache để ép pass. Parent`eurusd-observed-history-v2`
  có13datasets đã sealed. Mismatch thì halt/inconclusive, không fallback im lặng.
- Reuse baseline1400 events2019/2022 từ `fixing-clock-transfer-v1` đã reviewed,
  kiểm pins/source links và identity với exact rule; không tính lại economic
  outcomes đã có.11năm còn lại đọc cache qua native loader. Toàn bộ đã exposed
  trong chiến dịch, không clean OOS; không đọc2023+ hoặc bất kỳ2025+ holdout.

## Metric và tiêu chí trước outcomes mới

Mỗi year/view/scenario có all weekdays, entryeligible, resolved/unavailable,
netpips sum/mean/min/max, win/loss và top5positive share. Một pip=10USD per
standardlot, không là accountprofit hoặc 1R. Giữ actualtime/sequence/BidAsk.

Ưu tiên đăng ký risk wrapper mới chỉ khi primary stress tổng>0,≥9/13years
dương, từng block2010–12/13–15/16–18/19–22dương và mỗi năm≥200resolved.
Đây là retention heuristic trước số, chưa statistical/prop qualification;
blocks/costs/control không là independent samples. Không tăng risk để ép target.
Nếu không đạt, giữ exactcomponent negative/inconclusive trong scope; không
bác bỏ toàn bộ fixing mechanism hoặc tìm giờ đẹp trên cùng outcomes.

## Run, review, dữ liệu và timing

Pin script/protocol/core/helper/runtime/parentseals/cacheproofs trước đo.
Root mới một writer, deadline300s,status/PID/events/failure/CANCEL; kiểm pins
sau mỗi năm. Per-year artifacts seal trước năm kế; gặp lỗi giữ output trước,
không tự restart13years. Không framework/service/skill mới cho phép thử này.

Kế thừa unit fixtures của fixing-clock/local-session helpers, không sửa code
financial đang dùng. Runtime preflight kiểm clocks mùađông/mùahè/tuần lệchDST,
BUY/SELL zero movement và source binding trước newyears.

Separate implementation cùng agent: kiểm census/clocks, Fraction costs và
summaries trên mọi event, đối chiếu cache payload và firstquotes cho mọi
endpoint. Source pass đã fullhash raw qua loader; reviewer bổ sung rawfirst-
after/predecessor tại **ngày resolved sớm nhất mỗi newyear** (11dates), chỉ
scan prefix cần thiết, giữ fileidentity trước/sau. Không gọi prefix là full-
year source oracle; old2019/22reuse đã có rawreview. Nếu candidate giữ được,
trước riskwrapper qualification sẽ quyết định có cần mở rộng source/tick checks.
Mutations: futuretimestamp, sai side/net, thiếu row, falseauthority.

Sau kết quả ghi diagnostics/negatives/timing và quyết định vào cùng campaign.
Tách correctness, endpointpriceedge, account-risk, OOS, prop và execution.
Goal C1/C2 chưa hoàn tất từ bài này; holdout/broker/account/provider/payment
và production giữ gates riêng. Không bỏSL để biến bảngprice thànhbot.

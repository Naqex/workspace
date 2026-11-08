# Đợt mới: giữ câu hỏi phiên Mỹ, chưa viết bot retest — 08/11/2026

Thực hiện đợt admission tối đa hai hypothesis đã giao trong
[campaign](CHALLENGE-CANDIDATE-CAMPAIGN-20261108.md). Lượt Goal trước là
**progress**: tạo Goal, cập nhật tiêu chí dừng và commit c86c1c6. Lượt này
đọc baseline/catalogue, nguồn chính thức và nhận một phép thử mới; không mở
lại các study đã hoàn tất hoặc gọi sửa tài liệu là phát hiện edge.

## So hai giả thuyết trước outcome mới

| Giả thuyết | Khác bản đã thử ở đâu? | Nguồn và khả năng kiểm | Quyết định |
|---|---|---|---|
| R019: phá mức giá rồi quay lại kiểm mức đó | Thêm state retest/expiry vào R015 prior-day break | NY Fed125 giải thích orders quanh round levels; không chứng minh prior-day level, bar-confirmation hoặc retest entry của project. Chưa có exact recipe có cơ sở tốt hơn để ưu tiên | Defer specification/numeric trong đợt này, không reject mọi retest và không nhận nó có edge |
| R023: dòng tiền theo phiên địa phương | BUY EURUSD08–16NewYork bao gồm phần08–11NY mà post-London cũ thường bỏ; SELL07Dublin→08NY làm context, gần trùng PreECB ở nhiều ngày | SNB2011-04 có cửa sổ/side cụ thể, giá BidAsk và chú ý lệch DST. EURUSD2019/2022 đã consumed có raw-bound H1 dùng được | Admit **price/cost component** trước wrapper. Không xem hai legs/costs là independent edges hoặc paper replication |

Đối chiếu nguồn08/11: [NYFed125](https://www.newyorkfed.org/research/staff_reports/sr125.html)
và [SNB2011-04 PDF](https://www.snb.ch/public/asset/en/www-snb-ch/publications/research/working-papers/2011/working_paper_2011_04/publications0_en/working_paper_2011_04.n.pdf).
SNB Table1/2 và §2.2 mô tả giờ địa phương, EURUSD short trong phiên châu Âu,
long trong phiên Mỹ, tính BidAsk trên EBS1997–2007. Đó là wholesale market;
project dùng quote feed khác và thêm commission/slippage. Không sao chép data
hoặc code hãng, không nhận historical trading return thành khả năng pass quỹ.
Đọc nguồn để chốt method, không dùng một abstract hứa lời làm tiêu chí pass.

## Protocol khóa trước numeric: local-session-component-v1

- **Primary:** BUY EURUSD, weekday theo New York,08:00→16:00 America/New_York.
- **Context:** SELL07:00 Europe/Dublin→08:00 America/New_York cùng ngày.
  Europe local giờ07 theo Table1, không thay bằng Berlin07 hoặc offsetNY+5
  quanh mọi tuần DST. Context không được thay primary nếu primary thất bại.
- **Opposite control:** SELL cùng08–16NY. Không chọn hướng sau khi thấy số.
- Dùng first observed quote at/after target≤60s, từ raw-bound H1 cache hiện
  hành. Whole UTC hour; first_time/sequence/BidAsk của cache là endpoint.
  Thiếu/late entry hay exit giữ `unresolved` với clocks/quote evidence; không
  fill0, dời cửa sổ hoặc drop ngầm. Mọi weekday2019/2022 giữ denominator521.
  Hai năm đã exposed, không cleanOOS hoặc paper-sample replication.
- Costs giữ BidAsk embedded,100kcontract, commission2,50USD/lot/side,
  reference slip0 và stress0,00002/side; không funding trong price component
  này. Không SL/TP/sizing/margin/account/propDD. Per1standardlot không phải
  lãi/rủi ro của account10k hoặc quyền gửi lệnh. Không cộng legs thành bot
  composite có thể đảo ngay ở cùng quote; đó cần native execution riêng.
- Metrics: từng view/year/cost có all dates/eligible/resolved/unresolved,
  sum/mean/min/max netpips, positive/negative events và top3positive share.
  Primary có thêm hai calendar-half sums trên cùng resolved mask; không dùng
  halves để chọn giờ/tháng hoặc gọi độc lập. Chi phí không là exposure mới.
- **Retention heuristic:** chỉ ưu tiên xét risk-wrapper nếu primary stress
  sum dương cả2019/2022 và mỗi năm có ít nhất200resolved weekdays; mọi missing
  và concentration vẫn phải review, không auto promote. Mốc200 chỉ tránh
  giữ một mẫu quá nhỏ trong hai năm sẵn có, không statistical edge threshold.
  Một năm stress≤0 thì không ưu tiên wrapper trong đợt này; không cứu bằng
  giờ/side/calendar/SL grid. Chưa có risk-safe strategy hoặc pass probability.

## Kiểm chứng và giới hạn

Reuse numeric cost core và read/cache validators hiện có, không thêm engine.
Fixtures trước compute: hand-calculated BUY/SELL/spread/commission/slip,
zero-movement/control identity, Dublin/NY DST mismatch, weekend rejection,
missing/late endpoint, duplicate/order/quote grid và source mismatch.
Manifest pin protocol/tests/source/fixtures/input seals trước outcome; output
mới `execution-v1/local-session-component-v1`, không overwrite/retry tự động.
Numeric deadline180s/status/events/failure/CANCEL; expected cache reuse ~10s
chỉ dự kiến, không claim benchmark trước đo.

Separate implementation kiểm Fraction arithmetic và summaries mọi resolved
event; raw scan/hash toàn2datasets nhưng chỉ parse **4primary resolved dates
sớm nhất/năm**, lấy entry/exit/predecessor và kiểm first-after bằng source
sequence. Kiểm context endpoints ở cùng8dates và4negative mutations. Deadline
review180s, log tiến độ. Cùngagent bằng code khác, không independent audit
hoặc whole-year fill oracle. Không so khớp timestamps với giá đồ thị thủ công.

Không thay parent recipes/SL/risk hoặc current catalogue policy count. Kết thúc
ghi results/decision/timing/failures và hậu kiểm gọn; Goal chỉ được đóng theo
acceptance A/B thực sự, không vì bài component này xong. Holdout2025+, broker,
newaccount/paidproviders/challenge purchase/production vẫn ngoài scope.

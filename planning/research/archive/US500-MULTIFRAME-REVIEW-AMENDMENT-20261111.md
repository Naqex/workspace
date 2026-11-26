# Hậu kiểm: sửa false-positive missing path — 11/11/2026

Original protocol/source/results v1/v2 giữ nguyên. V2 hoàn tất162financial+
9nullbooks, nhưng bảng đầu có gần mọi scheduled-exit trade bị đánh unresolved.
Source coverage chỉ thiếu182cashminutes/292590expected, nên đã điều tra thay
vì kết luận chiến lược/dữ liệu không dùng được.

Root cause: `on_quote_tick` đã cập nhật `last_minute=t` trước khi gửi market
exit ởopen. CustomFillModel kiểm `last_minute+M != t` lần nữa, coi cùngminute
làgap. Stop trigger trước callback vẫn cần phát hiện gap; sửa chấp nhận
`last_minute in (t,t−M)`. Flag này chỉ ghi chất lượng path, không được đọc để
chọn side/size/fill/stop/exit. Không đổi rules/k/MA/costs hoặc economic decision.

Trước postreview: thêm test scheduled BUY/SELL exits phải known; reviewer
kiểm cả false-positive và false-negative path flags bằng rawminute coverage;
giữ tests gap→native stop, missing entry/exit và repeated NETTING closures.
Synthetic comparison old snapshot→fixed native engine phải giữ toàn bộ
fills/trades/cash trừ qualityflag. Không chạy lại162financial simulations.

Postreview dùng savedbooks còn sealed và admitted inputproofs, replay/review
execution bằng separate Fraction/Decimal path. Chỉ thay trade.unresolved theo
entry→exitminute raw coverage; so canonical fingerprint của tất cả field còn
lại trước/sau, assert modelednet/nativecash/fills không đổi. Ghi correctedbooks,
reviews, seals và summary trong output mới `us500-multiframe-native-v3-review-*`;
mọi old files giữ nguyên, không lấy known subset làm fullnet khi có gap thật.

Postreview vẫn không là fresh native run, independent human reviewer, cleanOOS,
verified FTMO execution, intraminute equityDD hoặc qualification. Không đổi
giả thuyết sau khi thấy outcome. Lỗi metadata được sửa bằng audit đã ràng buộc,
không nhân trials hoặc bắt owner chờ fullbatch không đổi thêm lần nữa.

Metadata-only delta thêm: progress denominator lấy actualyearsessioncount,
thay hard-coded253. Đây không đổi financialstate; no economic rerun required.

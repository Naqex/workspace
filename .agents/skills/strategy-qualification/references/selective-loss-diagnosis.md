# Chẩn đoán nguyên nhân lỗ có chọn lọc

Dùng sau screening khi cần giải thích chi phí, lợi nhuận yếu hoặc chọn việc
cải tiến. Không chạy lại toàn catalogue, tạo bộ lọc tham số mới hoặc biến một
phân rã kế toán thành bằng chứng edge/prop. Reuse sealed books/receipts trước.

## Chọn công việc trước khi đo sâu

1. **Đọc nhanh:** gross/net, coverage, costs, verdict và lỗi đã biết từ sổ
   hiện có. Không cần raw rescan hay simulation chỉ để phân loại lại.
2. **Đi sâu có lý do:** ưu tiên bản từng qua cửa giữ, hoặc near-miss có cơ
   chế và một bất định cụ thể có thể giải quyết. Ghi candidate/version,
   baseline, câu hỏi, mức công sức và tiêu chí chuyển bước trước số liệu mới.
   Không thêm ngưỡng tùy ý để loại tất cả hoặc cứu bản ưa thích.
3. **Lỗi đúng/sai:** material data/code/accounting bug luôn được xử lý dù
   strategy lỗ; đây khác việc tối ưu profitability cho một bản yếu.

Giữ riêng economic failure, data unknown và research-priority gate failure.
Một stage chọn công việc không tự là statistical test, actual edge hoặc quyền
chạy broker. Ghi cả lý do không đầu tư thêm; tránh phân tích sâu mọi loser.

## Phân rã không đếm trùng

- Khóa cohort và units: closed trades hay equity gồm open positions, account
  liên tục hay tổng annual-reset books. Hai cost scenarios không độc lập.
- Tách price PnL, spread, commission, slippage, financing debit/credit và
  rounding. Bid/Ask gross đã chứa spread; muốn trình bày spread riêng phải
  chuyển về một benchmark có căn cứ rồi reconcile. Unknown không thành0.
- Ghi benchmark và những gì chỉ là declared model. Revalue trên cùng path
  không là simulation xóa phí: đổi costs có thể đổi lot, SL, eligibility và
  cơ hội giao dịch. Không claim implementation shortfall thật khi thiếu
  decision/arrival/filled-order evidence hoặc suy market impact từ nến.
- “% gây lỗ” cần mẫu số. Với budget bất lợi, lấy tổng các khoản debit không
  âm, báo credits/winners riêng; mẫu số0→N/A. Share của costs dùng cost pool
  riêng. Không chia tùy ý cho net loss, nhất là khi net dương/gần0, hoặc gọi
  accounting contribution là tỷ lệ causal lỗi có thể loại bỏ.
- Không cộng exit-reason losses, losing-trade losses và fees thành cùng pie
  nếu chúng overlap. BUY/SELL, holding, years/regimes chỉ diagnostics; thấy
  subgroup lời không cho phép loại subgroup thua rồi gọi OOS.
- Closed net − open financing + terminal floating phải reconcile equity
  theo contract sổ. Không force close để làm đẹp profit target.

## Phân tầng và mẫu số

Khi owner cần xem từ tổng thể xuống lệnh, dùng cây không đếm trùng và
`hierarchical_attribution.py:build_hierarchy` trên sealed trades/books đã có.
Contract và ví dụ đã kiểm ở [hierarchical PnL](../../../../planning/research/HIERARCHICAL-PNL-ATTRIBUTION-20261109.md):

- Strategy/version → cost scenario → annual book → side → exit reason →
  holding bucket → composite trade ID. Scenarios là phương án thay thế, không
  cộng thành tổng financial tại strategy root. Các facets khác nhau không
  cộng chéo; chỉ cộng con của cùng cha, kiểm đầy đủ membership/count/components.
- Mỗi % giữ tử số, mẫu số, unit và scope. Tách % trong pool của nhóm, cùng
  khoản so với cha/kịch bản, net winning/losing pools và win/loss/hòa rate.
  Chỉ cộng tiền/count rồi tính tỷ lệ cha; không lấy mean tỷ lệ con.
- Net nhóm/vốn là contribution vào sổ nguồn, không ROI riêng. Vốn invalid
  làm tỷ lệ N/A; mean annual return N/A nếu bất kỳ sổ nào thiếu vốn. Annual
  reset khác tài khoản liên tục/CAGR. Mẫu số pool0→N/A, làm tròn ở cuối.
- Open financing/floating chỉ vào book/scenario equity bridge, không ép
  phân bổ vào closed cohorts. Giữ locator/hash và ID ghép scenario/year/position.
  Review độc lập số học + mutations trước diễn giải; đây không là new trial,
  causal proof, actual broker fee hoặc lý do đổi strategy từ subgroup đẹp.

## Từ phát hiện đến thay đổi

Xếp vấn đề theo tiền ảnh hưởng, độ chắc của bằng chứng, khả năng tác động
thật và công sức. Lỗi/spec chưa rõ sửa trước tuning. Giảm turnover/holding có
thể bỏ cả các lệnh thắng lớn; đòi hypothesis và replay mới thay vì cộng khoản
phí giả định tiết kiệm vào kết quả cũ. Không bỏ SL, nới risk, chọn side/ngày
đẹp hoặc hạ gate từ breakdown hồi tố.

Chốt một câu hỏi thử tiếp, version/protocol mới và đúng validation stage;
giữ baseline/negatives/exposure. Lưu ledger decomposition, denominator, pins,
timing và remaining gaps ở report/artifact owner. Tính lại bằng số học/cách
khác và mutation cases; kiểm numbers không thay clean OOS hoặc target terms.

Workflow đã áp vào [Gold selective diagnosis](../../../../planning/research/SELECTIVE-LOSS-DIAGNOSIS-RESULTS-20261109.md),
khóa [protocol](../../../../planning/research/SELECTIVE-LOSS-DIAGNOSIS-PROTOCOL-20261109.md).
Helper `tooling/ai-engines/forex_screen_diagnostics.py:adverse_budget` chỉ
reconcile components và shares; không tự chọn cohort hoặc cấp promotion.

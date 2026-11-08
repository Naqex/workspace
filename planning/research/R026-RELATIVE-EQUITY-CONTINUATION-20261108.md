# R026 component v1: giữ rules, thêm bốn năm exposed

Đăng ký sau [kết quả2019/2022](R026-RELATIVE-EQUITY-RESULTS-20261108.md),
trước lấy outcomes mới. Đây là continuation sau chọn survivor; không clean
OOS hoặc sửa lại primary để che selection. Goal thuộc campaignv2, không đợtB.

- Giữ nguyên [recipe](R026-RELATIVE-EQUITY-COMPONENT-20261108.md):instruments,
  first/penultimate NYSEclose,currency conversion,direction,London15:01→16:03,
  costs,missingpolicy,baselines,price-component-only scope. Không bổ sung
  filter/time/threshold/SL hoặc đổi cửa sổ để né hai missingmonths cũ.
- Năm mới **2020,2021,2023,2024**,48months được giữ trong census. Calendar
  fixtures hiện có được hash/pin; metadata/common ETFstart2018 nên không mở
  một năm2018partial chỉ để có sample trước xem outcomes.2025+ vẫn đóng.
- Bốn năm mới có **672 logical instrument-side/day requests**:
  48months×(2signal-days×3instruments×2sides+1FXday×2sides)=672.
  Nếu trùng raw URL thì reuse hash; không tải lại336parts cũ hoặc rerun
 2019/2022. Source-only admission bằng tool đã kiểm, raw native giữ nguyên.
- Cùng existing public provider/pinned1.51.1. Native retry0; helper≤2retries
  transient timeout/5xx, cumulative failurecap12,deadline1800s,CANCEL/status/
  logs/seals/onewriter; no auth/WAF/429/schema retry, no new provider/payment.
- Trước thu data: config/code/protocol/calendarpins, snapshot, owned output
  mới. Mỗi daysealed reuse được khi bindings đúng; failure giữ phần xong,
  chỉ attempt mới theo recoverydelta, không loop vô hạn. Không thay private
  data files hoặc source pins của batch đang terminal để hợp thức hóa run mới.
- Triage tiếp:≥10/12 resolved mỗi năm mới, primary stress positive ít nhất3/4
  năm mới và cumulative stresspositive cả4 năm; báo từng năm và worstyear,
  resolved/missing,trades,concentration và costfragility. Đây chỉ research
  priority, không claim calibrated pass probability hoặc edgecertificate.
  Nếu không đạt thì parked exactadaptation; không retune từ sameoutcomes.
- Reviewer riêng Fraction/raw-delta giữ allmonths/raw/financial/summary,
  testmutation và source/causal checks; logic dùng lại phải được sửa scope
  fouryears/monthcensus một cách explicit trước numeric. Không tái dùng test
  result22trades như chứng nhận48months hoặc tự reuse report cũ vào source mới.

Sau continuation mới quyết định native SL/sizing/tick/prop-path/timefit và
exact unseen/forward protocol; không tự mở broker/holdout. Không cần vectorDB,
benchmarkcalendarfeed trả phí hay layer quản lý khác cho câu hỏi hiện tại.

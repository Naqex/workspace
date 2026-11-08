# Paper-window v2: implementation và preflight, chưa market outcome

[Economic protocol](INDEX-PAPER-WINDOW-ECONOMIC-PROTOCOL-20261109.md) `170e9bd`
đã freeze trước code/outcomes. `index_cash_close_tick_component.py` là opt-in
tooling, không đổi bot/native broker path, parent consumers hoặc source đang chạy.

Luồng chính: frozen parent features → xác nhận late predictor bằng raw ticks
→ first quote sau decision+delay có expiry → existing BidAsk/cost core →
summary theo asset/year/delay → reviewer raw-selection/Fraction riêng.
Chỉ đọc projections có seals/binding từ full source review; không dùng
RAG/LLM chọn giá hoặc quyết định vào lệnh. Price component vẫn chưa account
sizing/SL/intrabar equity/prop/OOS/prospective/handover.

## Kiểm trước market PnL

- 6 new tests đạt; 120 role/cost cases qua hai assets/hai sides/ba delays,
  đối chiếu Fraction với gross/sub-cent/cents/slip/net, expiry inclusive,
  missing entry/exit, future mutation, flat/no exposure, scope/identity/units,
  census và all-delay gate. 8 existing parent tests đạt; parent code không đổi.
- Reviewer không import producer/cost helpers: raw delta scanner chọn first
  quotes bằng arithmetic riêng, Fraction cho endpoints/costs/net/summary.
  Preflight 120 cost-role cases, 48 actual pilot quote locators khớp sealed
  reviewers và 5 monetary mutations reject; 0,641 s. Scanner giữ ba locators và
  late price mỗi giờ, không giữ toàn history Fraction objects trong RAM.
- Một test-fixture fail `ordered_unique_calendar_required` do labels giả không
  sort theo lịch; giữ failure trong preflight receipt, đổi fixture sang calendar
  labels đã có, không nới gate hoặc chạy numeric để chữa test.
- Producer chỉ chạy khi full source terminal/reviewed, đúng hashes/code và
  không common-price conflicts; 3.018 cashday-delay records dự kiến cho hai
  assets, không 3.018 trades độc lập. Không tính market PnL trước source gate.

Private base giữ source artifacts đã chỉ định. Saved scripts:
`run-index-paperwindow-components-v2.py`, `review-index-paperwindow-components-v2.py`;
receipts `paperwindow-component-preflight-v2.json` và
`paperwindow-reviewer-preflight-v2.json`. Output economic dự kiến mới
`execution-v1/index-paperwindow-components-v2/`. Chưa chạy ở checkpoint này.

## Recovery đã xảy ra thật, không chỉ unit test

Intake source invocation đầu dừng `TypeError: fetch failed` sau **1.353/1.996**
hours, 826,533 s; upstream error không giữ cause/stack chi tiết, chưa xác minh
loại lỗi mạng cụ thể. Không tự thêm broad retry hoặc gán thành 403/429/socket
đã biết. Một invocation tiếp cùng code/config/protocol kiểm toàn prefix trong
10,486 s, rồi fetch tiếp đúng hour còn thiếu, không resimulate/refetch prefix.
Reviewer dừng theo producer và đã resume từ 1.353 reports, giữ hashes/source
bindings; 5,337 s startup gồm canonical load và prefix verification.

Failures/events cũ giữ trong `failures.jsonl`, run/PID riêng; lock được release
đúng owner. Cache-only preflight trước long run: 16 exports raw/output hashes
exact; actual second invocation reuse16, 7 forged-seal/prefix mutations reject.
Intake/reviewer đang chạy tiếp: status hiện hành ở hai private `progress.json`,
không lấy số checkpoint này làm final count hoặc whole-history admission.

Hậu kiểm: correctness trước PnL có bounded fixtures/raw reviewer; recovery
đã bảo toàn phần xong khi lỗi mạng. Gap log `fetch failed` thiếu cause cần
đánh giá sau khi pinned source workers terminal; không sửa live code/pins.
Không cần skill/framework mới: workflow evidence/research/qualification/performance
đã cover quyết định này. Goal vẫn active, chưa strategy challenge-qualified.

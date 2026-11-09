# Cơ chế tiếp theo: chọn nguồn trước khi viết thêm bot

Research sau [commission0 results](FTMO-INDEX-COMMISSION-RESULTS-20261108.md),
08/11/2026. Không có backtest/policy mới ở tài liệu này, không mở dataset2025+.

| Hướng | Primary source đã đọc | Quyết định hiện tại |
|---|---|---|
| Turn-of-month | [McConnell/Xu2008, bản tác giả ở Purdue](https://business.purdue.edu/faculty/mcconnell/publications/Equity-Returns-at-the-Turn-of-the-Month.pdf), intro/định nghĩa; [author SSRN record](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1135217) | Ưu tiên method/cost/data preflight cho R025 calendar family đã có; chưa triển khai hoặc gọi có edge |
| Overnight drift | [NYFed staff report917](https://www.newyorkfed.org/research/staff_reports/sr917), abstract và author-paper search excerpt | Không code theo headline cũ trước kiểm cập nhật |
| Overnight drift sau công bố | [NYFed/LibertyStreet,01/07/2026](https://libertystreeteconomics.newyorkfed.org/2026/07/the-disappearing-overnight-drift/), title/abstract từ Fed record và trang primary | Latest authors' update báo hiệu ứng đã yếu đi; không ưu tiên một unconditional2–3ET bot chỉ vì paper cũ tốt |

Turn-of-month gốc xét return ngày cuối tháng và ba tradingdays đầu tháng sau;
sample CRSP/indices, không phải CFD intraday có hardSL và phí của project.
Paper không xác nhận volume/fund inflows là nguyên nhân của hiệu ứng. Không
biến một giải thích dòng tiền nghe hợp lý thành cơ chế đã được chứng minh.
Nếu chỉ giữ cash-open→cash-close để hạn chế carry, đó là adaptation **khác**
close-to-close; cần đăng ký trước outcome và so benchmark cùng clock/risk/cost.

Overnight drift gốc nói cửa sổ2–3giờ ET; bài cập nhật2026 là bằng chứng research
sau công bố cần xét, không kết luận cho mọi CFD/điều kiện. Nguồn mới có thể
tổng hợp giai đoạn sau2024: đây là **public knowledge exposure** có ảnh hưởng
tới chọn hypothesis, không là kết quả local holdout. Không đọc/tải local2025+
bars, không được gọi lựa chọn có dùng nguồn này là hoàn toàn mù với literature
giai đoạn sau2024. Mọi holdout tiếp theo vẫn cần frozen protocol/gate riêng.

## Method đã đọc và component đã kiểm

[Frozen component protocol](US500-TURN-OF-MONTH-COMPONENT-PROTOCOL-20261108.md)
đăng ký trước outcome, code6e5795f; [kết quả/hậu kiểm](US500-TURN-OF-MONTH-COMPONENT-RESULTS-20261108.md)
kiểm1510sessions2019–2024. Intradaypriority không đạt cả hai block/costs; chưa
triển khai R025bot, không tăng policycount hoặc promote. Dòng method/preflight
trong bảng trên là decisiontrước run, đã được thay bằng kết quả ở đây.

### Lát đã thực hiện trước numerical outcomes

Đọc đúng method/calendar endpoints trong paper2008; xác định signal component
được kiểm, holding/SL/benchmark và tính chi phí theo profile mới. Reuse raw/
calendar/financial book hiện có, trước hết kiểm data có đủ cho clock/lookback
đã chọn; không lặp monthly mistake (năm không dùng được bị tính economic0).
Không định thêm market/provider/account, không tuning losers hoặc import repo
trading có credential/order tools. Chưa freeze recipe nên **chưa dispatch PnL**.

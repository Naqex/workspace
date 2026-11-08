# Tìm ứng viên challenge và kiểm lại quy trình — 08/11/2026

Owner giao tiếp tục tìm ứng viên đủ bằng chứng và hậu kiểm quá trình; sửa lỗi
rồi kiểm lại cho đến khi cả hai tiêu chí đạt. Đây là nhiệm vụ đang thực hiện,
không phải lời bảo đảm thị trường sẽ cung cấp một chiến lược có lợi thế.
AI plan/receipt hiện có giữ trạng thái và bằng chứng; file này giữ tiêu chí.

Owner nhắc lại08/11: checkpoint/báo cáo từng batch không làdừngcampaign.
Nếu chưa đạt C1/C2, thực thi lát kế tiếp có căn cứ trong scope đãduyệt;
không tự chuyển “chưa tìmra” thành “complete”, cũngkhông épmarketphảicówinner.

## Hai tiêu chí tách biệt

| Tiêu chí | Bằng chứng cần trước khi kết luận đạt |
|---|---|
| C1. Ứng viên đủ để đề xuất vào challenge | Rule/source/config bất biến; lợi nhuận sau chi phí có độ bền, uncertainty và trial history được review; đối chiếu tick/risk/prop; phù hợp mốc3/6/12tháng và mục tiêu risk thấp; forward/reconciliation và điều kiện hãng đủ cho đúng bước đề xuất |
| C2. Quá trình đủ chuẩn trong phạm vi kiểm | Protocol trước outcome, data roles/consumption đúng; causal timing; oracle/fixtures/negative controls; số học/cost/risk/state khớp; selection/overlap/multiple trials được xử lý; không còn lỗi material hoặc gap che giấu; nguồn và acceptance có thể tái hiện |

Một năm dương, một lần mô phỏng pass hoặc một checklist xanh không tự đạt C1.
Số lần chạy không tự làm C2 tốt hơn. Khi lỗi nằm ở code/data/report thì sửa và
rerun phần bị ảnh hưởng, giữ attempt cũ; không loại ý tưởng vì lỗi kỹ thuật.
Khi economics không đạt, giữ negative version và chuyển hypothesis, không
nới risk/cost/tiêu chí để cứu nó. Sửa rules sau outcome là trial mới.

## Phạm vi và profile ban đầu

- EURUSD, tự động bằng rules/code; AI phục vụ research/code/review, không
  quyết định lệnh theo từng tick. Có thể mở rộng cơ chế/timeframe khi có lý do.
- FTMO2-Step Swing là profile nghiên cứu đầu tiên; so The5ers riêng, không
  gắn cùng một nhãn compliance cho cả hai. Terms chính thức kiểm08/11:
  FTMO target10%/5%, daily5%/overall10%,4tradingdays, thời hạn unlimited;
  Swing leverage1:30, cho phép news/holding trong forbidden-practice rules.
  The5ers terms yêu cầu written approval cho automated software; chưa có
  account/approval nên không gọi bản auto là sẵn sàng The5ers.
- Giữ initial10k, planned25USD/lệnh (0,25%), internal daily100/overall500,
  một vị thế. Đây là mức ban đầu để so economics, không tăng risk để ép target.
  Khi đủ evidence mới đăng ký sizing sensitivity riêng, không tối ưu grid risk.
- Research/offline code, data đã consumed và chuẩn bị metadata được làm ngay.
 2025+ còn đóng tới exact frozen holdout protocol/user gate; không broker
  OrderCheck/OrderSend, mua challenge/account mới, paid provider hoặc deployment.

## Vòng thực hiện

1. Khoá một đợt hypothesis nhỏ, cơ chế/recipe/exit/clock/cost/risk rõ. Giữ toàn
   bộ candidates và relation với8rules cũ; không gọi các variants độc lập.
2. Fixtures/causal state/prefix/restoration trước numeric outcome. Dùng H1
   summaries exact cho tín hiệu/warmup; native Bid/Ask tick core cho execution.
   Không nhân simulator/risk owner. H4 cũ phải giữ golden parity.
3. Screen đã consumed để sắp ưu tiên, gồm cả cost stress; không dùng H1model
   để chứng nhận DD hoặc loại cứng cả family. Nhóm được giữ và một bản định
   gác được tick check theo cách chọn trước outcome.
4. Robustness theo periods/3–6–12months và tập trung PnL; review uncertainty,
   cost/delay/gap, exit/risk sensitivity có đăng ký. Tách development/exposed
   robustness và holdout thực sự; không đọc holdout để sửa rules rồi gọi là OOS.
5. Chỉ frozen survivors qua exact holdout protocol, native prop path và
   prospective shadow/demo/reconciliation theo quyền riêng. Không suy xác suất
   pass hiệu chỉnh từ vài account paths; fees/permissions/historical realism
   chưa đủ phải ghi unknown.
6. Hậu kiểm C2 tại mỗi batch có evidence mới; fix/verify phần bị ảnh hưởng.
   C1/C2 chưa đạt thì tiếp vòng hypothesis theo câu hỏi đã ghi; không đổi tiêu
   chí sau outcome hoặc mở vòng tối ưu không có evidence. Cả hai đạt mới đóng
   nhiệm vụ tìm ứng viên; mua/thực thi challenge vẫn là quyền riêng của owner.

Đánh giá time-fit báo3/6/12tháng, cả phase1 và phase2, drawdown/headroom,
profit concentration và daily/overall paths. Không mặc định phải pass trong
3tháng hoặc tăng lot vì thời gian dài; owner chưa chốt deadline cá nhân.

## Nguồn vừa kiểm và giới hạn

- [FTMO2-Step](https://ftmo.com/en/2-step-challenge/): objectives.
- [FTMO Swing](https://ftmo.com/en/faq/what-is-the-swing-account-type-and-how-does-it-work/): leverage/holding/news.
- [FTMO strategies](https://ftmo.com/en/faq/which-instruments-can-i-trade-and-what-strategies-am-i-allowed-to-use/): EA và điều kiện trading thực tế; không bảo đảm một bot được duyệt.
- [The5ers terms,28/10/2026](https://the5ers.com/en/terms-and-conditions/), §11: software approval; chưa cấp quyền tự động thay owner.
- [QuantConnect research guide](https://www.quantconnect.com/docs/v2/cloud-platform/backtesting/research-guide): hypothesis-driven/trial history/OOS. Không cung cấp một ngưỡng thống kê chung bảo đảm edge.
- [Khung review của project](STRATEGY-VALIDATION-FRAMEWORK-20261105.md) và
  [gates](../../.agents/skills/strategy-qualification/references/validation-gates.md)
  tiếp tục được áp dụng, không lấy artifact integrity thay G3/G4/G5.

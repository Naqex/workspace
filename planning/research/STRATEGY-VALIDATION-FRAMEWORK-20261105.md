# Khung kiểm chứng chiến lược: căn cứ, hiện trạng và cửa trước validation

Kiểm05/11/2026 theo owner hỏi làm sao biết test đúng quy trình và chính khung
có đáng tin không. Scope: review nguồn chuyên môn + source/protocol/tests và
artifacts đã giữ; không mở window giá/validation/holdout mới, không mua challenge
hoặc gửi lệnh. [AI plan](../trader/AI-RESEARCH-UI-PROTOTYPE-20261031.md) giữ scope,
[receipt AI](../checkpoints/ai-integrations-20261031/RECEIPT.md) giữ trạng thái.

## Kết luận về chữ “chuẩn”

Project có **protocol nội bộ dựa trên phương pháp nghiên cứu được công bố**,
chưa được bên độc lập chứng nhận. Không có bằng chứng một checklist, engine,
paper, Sharpe threshold hoặc số test pass nào bảo đảm chiến lược có lợi nhuận.
Khung tốt cần làm rõ assumptions, tạo kết quả bác bỏ được, ghi cả thất bại,
kiểm trên dữ liệu không dùng để sửa rules và so với hành vi thực tế.
Độ tin cậy tăng bằng evidence và thử phá assumptions; không lấy lời agent xác nhận.

Nguồn chính thức/chuyên môn đã đối chiếu:

- [Bailey et al., Probability of Backtest Overfitting](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf),
 bản02/2015, đọc05/11: chọn từ nhiều backtest tạo false positives; một holdout
 đơn lẻ không tự giải quyết việc thử/chọn nhiều lần. PBO/CSCV là phương pháp
 có assumptions và data requirements, không phải tem chuẩn cho mọi dataset.
- [Bailey/López de Prado, Deflated Sharpe Ratio](https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf),
 bản07/2014, đọc05/11: số trials và non-normality ảnh hưởng mức tin vào Sharpe.
 Đếm sai/thiếu trials hoặc dùng sample không phù hợp thì không tự ra kết luận chắc.
- [Fed, revised model-risk guidance](https://www.federalreserve.gov/frrs/guidance/supervisory-guidance-on-model-risk-management.htm)
 và [SR26-2,17/04/2026](https://www.federalreserve.gov/supervisionreg/srletters/sr2602.htm),
 đọc05/11: conceptual soundness, validation/outcomes, monitoring và effective
 challenge có ích làm nguyên tắc. SR26-2 thay SR11-7; đối tượng là banking
 organizations, không biến project cá nhân thành đối tượng phải tuân thủ hay
 tự nhận compliance/certification ngân hàng. Chỉ áp dụng nguyên tắc vừa scope.
- [QuantConnect reconciliation](https://www.quantconnect.com/docs/v2/cloud-platform/live-trading/reconciliation),
 đọc05/11: platform own khuyến nghị phân tích chênh lệch backtest/live; engine
 đáng tin vẫn có data/fill/live differences. Đây là kinh nghiệm của nhà cung
 cấp, không là xác nhận Naqex đã đạt cùng mức hoặc lý do phải chuyển engine.
- [Duke publication record: Arnott/Harvey/Markowitz, A Backtesting Protocol in the Era of Machine Learning](https://scholars.duke.edu/publication/1518184)
 xác minh tác giả/ấn phẩm2019. PDF published copy timeout trong lượt này;
 **không** nói đã đối chiếu toàn paper hoặc gán checklist dưới đây là exact
 reproduction của paper. Không dựa forum/upvote để công nhận methodology.

## Project đã áp dụng gì, còn thiếu gì?

| Cửa / câu hỏi | Bằng chứng project | Trạng thái đúng scope |
|---|---|---|
| G0. Chốt thí nghiệm trước nhìn kết quả? | Protocol round1/round2, frozen copies, Git/run/source/input/cost pins; giữ các attempt âm/lỗi | Có workflow và records; protocol hash riêng không attest timing/prereg độc lập |
| G1. Dữ liệu và code có sai timing/tính toán? | QDM BidAsk hash/header/order/grid/date checks; closed-H4/next-quote/causal entry tests; fixed known-PnL probe cases; independent ledger accounting | Có guard/tests cho implementation đã kiểm; chưa independent toàn bộ model/data audit |
| G2. Mô phỏng có đúng assumptions thực thi? | Spread embedded, commission/slippage/financing reference+stress, lot/risk và cash/equity/open positions | Declared scenarios; historical broker cost/fill/spec và full intrabar rule coverage còn thiếu |
| G3. Có edge trên dữ liệu chưa dùng? | Q1 đã consumed, trial-history policy; planned dev/validation/final holdout split | Chưa kiểm OOS. Availability/consumed toàn2023+ chưa được xác lập; chưa freeze final validation criteria/window |
| G3. Đã chống chọn may mắn/tự khớp quá khứ? | Protocol giữ trials/negative variants; DSR/PBO/walk-forward chỉ khi phù hợp | Chưa statistical validation.5candidate/2costs không là10independent trials; cùng họ/overlap phụ thuộc |
| G4. Có phù hợp FTMO/The5ers cụ thể? | Có research rule profile và pilot internal25/100/500USD; per-firm unknowns đã ghi | Internal budgets không là chứng nhận luật hãng; chưa đầy đủ historical broker/rule reconciliation |
| G5. Chạy shadow/demo có khớp mô phỏng? | Có bằng chứng vận hành riêng, process/recovery checks | Không gộp system-demo test hoặc numeric pass thành proof strategy-forward gap đã đóng |
| G6. Có quyền execution? | Grant/runner ownership và fail-closed authority riêng | Research/dossier không cấp quyền; không gửi lệnh trong review này |

Nguồn nội bộ: [strategy workflow](../../tooling/ai-engines/STRATEGY-WORKFLOW.md),
[round1 §5–6](PROP-STRATEGY-ROUND1-20261105.md), [round2](PROP-STRATEGY-ROUND2-20261105.md),
`forex_h4_pilot.py`, `forex_h4.py`, `forex_pilot_risk.py`, `strategy_evidence.py`
và các test Forex được receipt dẫn tới. Q1gốc source814e1135, code mới ac3c0572
chỉ có scoped regressions/bounded parity; không đổi bằng chứng cũ thành fullQ1
acceptance cho code mới. Current dossier source comparison sẽ báo drift đúng.

66product tests và11controller tests là bằng chứng software trong scope đã chạy,
không là con số có ý nghĩa statistical profitability.5,84triệutickQ1 vẫn chỉ có
5–49closed trades/candidate; ticks/trades cũng không mặc định là mẫu độc lập.
Không bịa ngưỡng universal như30/100trades hoặc Sharpe>2 để tự pass.

## Biết mình test sai bằng cách nào?

| Failure mode | Cách phát hiện/chống | Nếu phát hiện |
|---|---|---|
| Dùng giá/tin tương lai, vào ngay giá đóng vừa dùng để quyết định | Availability timestamps, prefix invariance/causal cases, next-quote fill oracle | Invalidate affected runs, sửa implementation, regression rồi rerun phần bị tác động |
| Bỏ phí, fill đẹp, sai lot/clock, giả flat cuối mẫu | Known-PnL examples, independent recalculation, broker/spec evidence, adverse scenarios | Giữ assumptions rõ hoặc sửa cost/fill/data version; không gọi artifact hash là realism |
| Xem validation rồi sửa rules đến khi đẹp | Freeze + consumed/trial register; mọi variant/failure giữ lại | Trial mới; window đó đã consumed, không còn final unseen test cho bản sửa |
| Chỉ chọn winner từ nhiều thử, giấu losing attempts | Trial inventory gồm abandoned/baselines/variants; dependence-aware stats khi đủ assumptions | Giảm confidence/không promote; không reset search count theo agent/ngày/batch |
| Hai đoạn code sai cùng kiểu rồi xác nhận nhau | Case tính tay/simple oracle, kiểm thử lỗi cố ý, objective review hoặc independent implementation khi đáng giá | Đóng bug/tính lại bằng evidence độc lập; LLM judge thứ hai không tự chứng minh đúng |
| Nhầm “runner xong”/“hash khớp” thành “đạt chiến lược” | Dossier report tách mechanical checks và review chưa thực hiện | Báo inconclusive/unknown đúng stage; không tự promote hoặc mở authority |

Source/input hashes cho reproducibility/integrity, không chứng minh input đúng
thị trường, code không lookahead hoặc protocol đã freeze trước outcome. Một
metric chống selection bias không sửa được dữ liệu/implementation sai.

## Cửa trước lần validation tiếp theo

1. Inventory metadata/receipts để ghi dev/validation/final holdout và những vùng
   từng nhìn; còn unknown thì không gọi là unseen. Không đọc PnL/price holdout
   để chọn window. Dữ liệu chấm lặp sau feedback có vai trò development/selection.
2. Freeze candidate rules/code, benchmark, price/cost/risk/firm assumptions,
   primary metrics, uncertainty method và quyết định pass/reject/inconclusive
   **trước** outcome. Date split lịch sử chỉ là dự kiến khi chưa audit consumption.
3. Kiểm material correctness và realism assumptions phù hợp stage bằng targeted
   tests/oracles; không chặn research scenario chỉ vì chưa đủ mọi live capability,
   nhưng kết luận phải giữ trong assumptions đó. Không mở validation để debug engine.
4. Chạy riêng window/attempt; reviewer chấm theo tiêu chí đã khóa, báo remaining
   gaps. Đổi rules sau kết quả là trial mới, không sửa tiêu chí để chọn winner.
5. Chỉ đề xuất shadow/demo theo evidence và quyền tương ứng. Mọi kết luận có
   scope/version/date/locator, không hứa profitable/prop survival chắc chắn.

Đây là protocol review áp dụng theo stage, không một validator tự động bao hết
mọi cửa. [Validation gates reference](../../.agents/skills/strategy-qualification/references/validation-gates.md)
giữ hướng dẫn cho agent; `strategy_evidence.py inspect` giờ trả `review_checks`
để thể hiện phần đã scan và phần chưa được tool đánh giá. Skills không thay
code guards, independent review, data audit hoặc future out-of-sample evidence.

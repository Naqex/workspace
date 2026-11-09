# IBS02: khác biệt source ở nhánh RSI, trước numerical outcomes

Kế thừa [protocol](IBS02-EXPLICIT-SOURCE-CORRECTION-20261108.md). Attemptv1
đã failclosed0,047s ở ASTguard, **0simulations**, trước khi dispatch2022.
Driver/failure/events giữ nguyên; không sửa pin để tiếp tục v1.

`rsi3` có ASTexact. `plans_for` chỉ khác điều kiện safetyEXIT của candidateRSI:
old đòi đồng thời có IBS và RSI rồi mới xét exit; current cho exit nếu một
indicator khả dụng yêu cầu thoát. Đây là correctnessfix riêng R050 đã kế thừa
trong longreview, không là thay đổi rule của R049IBS02.

V2 chỉ nhận compatibility nếu AST của **toàn function sau bỏ đúng nhánh
`candidate==RSI` vốn không thể chạy khi candidateIBS** là exact cho cả ba
source snapshots cũ/mới; `rsi3` vẫn exact, allotherAST/matching names giữ.
Không bỏ nhánh risk/exit của IBS hoặc nới numeric tolerance. FulloriginalAST
và vị trí delta vẫn được giữ; không tuyên bố fullfunctionparity cho RSI.

Exactraw/current/old source hashes, transformsource và specializedASTchecks
lưu manifestv2 trước numerical. Lượt này là R049only; phát hiện khác biệt
khác thì dừng và review riêng. ExistingCLI/financial/sourceproofguard vẫn nguyên.
Không thêm risk/cost/strategyvariant, không đọc outcome mới để chọn tham số.

Privateoutput `execution-v1/us500-ibs02-source-corrected-v2`; reuse existing
sourceviews, rules/cost/calendar/deadlines và tiêu chí protocolv1. Không sửa
frozen protocol hoặc failedattemptv1. C1/C2overall chưa hoàn tất.

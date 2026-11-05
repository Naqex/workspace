# Prop terms snapshot for time-fit registration — 2026-11-06

Đây là snapshot nguồn chính thức để thiết kế evaluator; không thay account
contract và không phải tư vấn pháp lý.

| Profile | Đã xác minh từ nguồn chính thức | Còn phải pin trước numerical run |
|---|---|---|
| FTMO 2-Step | Profit target 10%/5%, max daily loss 5%, max loss 10%, tối thiểu 4 trading days mỗi phase, unlimited trading period; Swing cho phép giữ qua overnight/weekend/news trong phạm vi forbidden practices | Account size/checkout snapshot, reset/equity semantics theo profile cụ thể, phí/commission/financing lịch sử |
| The5ers High Stakes | Max loss 10% initial; daily loss 5% theo mức cao hơn giữa balance/equity ngày trước tại 00:00 server; profitable day 0,5% initial; Terms yêu cầu written approval trước automated software | Program/version/size cụ thể, server timezone/DST, news window, payout/eligibility, automation approval và cost/fill profile |

FTMO sources:

- <https://ftmo.com/en/2-step-challenge/>
- <https://ftmo.com/en/trading-objectives/page/68/>
- <https://ftmo.com/en/faq/ftmo-swing-account-type/>
- <https://ftmo.com/faq/how-long-does-it-take-to-become-an-ftmo-trader/>

The5ers sources:

- <https://the5ers.com/faqs/what-is-the-drawdown-rule-for-high-stakes/>
- <https://the5ers.com/faqs/how-do-you-define-a-profitable-day-in-the-high-stakes-program/>
- <https://the5ers.com/en/terms-and-conditions/>

Trạng thái: **FTMO profile đủ để thiết kế evaluator sơ bộ; The5ers chỉ là
comparison profile pending account/program pin**. Chưa mở numerical run, holdout
hay automation authority.

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
| G3. Có edge trên dữ liệu chưa dùng? | Q1 đã consumed; audit metadata và registration độ bền Q1/2023 được dẫn bên dưới | Chưa kiểm OOS. Owner không nhớ exposure2023–2024; bài kế tiếp đã freeze nhưng là historical robustness, chưa chạy |
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

## Delta sau audit metadata và câu trả lời owner05/11

[Audit/registration bài kế tiếp](PROP-HISTORICAL-ROBUSTNESS-20261105.md) khóa
Q1/2023, warmup11–12/2022, cả5candidate và tiêu chí trước giá mới. Metadata
inventory đã thực hiện; clean-unseen status vẫn **không xác lập** vì owner
không nhớ lịch sử và scanner có phạm vi/format limits. Vì vậy không gọi bài
này là clean OOS hoặc coi nó đóng G3. AvailabilityQDM đã kiểm riêng bằng CLI
metadata, không bảo đảm quality. Tại thời điểm freeze ban đầu, runner chưa hỗ trợ window này;
registration file riêng chưa là code enforcement. Giữ các cửa kiểm còn lại nguyên
trạng thái cho tới khi có đúng bằng chứng, không tự đánh dấu đạt từ protocol.

## Đối chiếu tiếp: version/reuse và mức độ quant,05/11

Owner giao tiếp implementation registration, đồng thời hỏi lịch sử/phiên bản,
đối chiếu docs/cộng đồng/quỹ và cách gọi quant trading. Review này không mở
giá2023 mới, không thay signal/risk/cost hoặc tiêu chí của protocol đã freeze.
Delta implementation nằm ở receipt; paragraph “runner chưa hỗ trợ” phía trên
là snapshot trước implementation, không dùng nó để bắt đầu lại audit.

### Nguồn đối chiếu thêm

| Nguồn đọc05/11 | Nội dung dùng được / giới hạn |
|---|---|
| [MLflow Tracking](https://mlflow.org/docs/latest/ml/tracking/), kèm official tracking API qua Context7 | Phân biệt experiment/run, code version/parameters/metrics/artifacts; parent–child runs có hỗ trợ. Không cần cài MLflow chỉ để có versioning, không tự là validation phương pháp |
| [QuantConnect Research Guide](https://www.quantconnect.com/docs/v2/cloud-platform/backtesting/research-guide) | Hypothesis trước kết quả, ghi quá trình thử/chọn và vùng OOS. Bảng heuristic số backtests/parameters/giờ research trên trang không là statistical theorem; không copy thành quota hay tem pass |
| [QuantConnect reconciliation](https://www.quantconnect.com/docs/v2/cloud-platform/live-trading/reconciliation) | Cần so hành vi live với backtest; không suy đổi engine là hết simulation–execution gap |
| [AQR Trading Costs,2018](https://www.aqr.com/Insights/Research/Working-Paper/Trading-Costs) | Nghiên cứu dùng executions thực để hiệu chỉnh chi phí theo size/thời điểm/điều kiện. Bài về institutional equities; không đem số đo của AQR gán thành chi phí Forex/prop của mình. Đã đọc trang tóm tắt, chưa audit lại full paper |
| [FTMO objectives](https://ftmo.com/en/trading-objectives/) và [strategy/EA FAQ](https://ftmo.com/en/faq/which-instruments-can-i-trade-and-what-strategies-am-i-allowed-to-use/) | 2-Step daily loss theo equity và balance tại midnight CE(S)T; overall static, khác1-Step/Instant. Algorithmic/EA được phép trong điều kiện và prohibited-practices rules; third-party EA có allocation concern. Phải pin đúng program/phase, không thay internal pilot budget bằng nhãn FTMO |
| [The5ers Terms §11,update28/10/2026](https://the5ers.com/terms-and-conditions/), [EA FAQ](https://the5ers.com/faqs/can-i-use-an-ea-expert-advisor-can-i-set-a-stealth-mode-stop-loss/), [High Stakes](https://the5ers.com/high-stakes/) | Terms yêu cầu prior written approval cho automated software và có hạn chế third-party ownership/development. FAQ không tự thay Terms hoặc cấp duyệt cho bot này; nội dung EA/prohibited styles/visible SL cũng cần xét. Chưa có account/bot-specific approval. Đây là điều kiện đã phát hiện trước đó, nay kiểm lại, không phải phát hiện mới |
| [Reddit: Forward Testing Validation](https://www.reddit.com/r/algotrading/comments/1wuh1ls/forward_testing_validation/) | Có người chia sẻ freeze trước demo và đối soát signal/size/order/cost; cũng có khuyến nghị50trades/AI đánh giá rất khác nhau. Đây là tự thuật, không audit được profitability, không lấy50 hoặc AI nói ready làm gate |

Hai URL FAQ cũ không truy cập được; đã dùng trang chính thức hiện truy cập được
ở trên. Thread tracking `1rdcb7o` được mở nhưng post đã removed; không lấy search
snippet của post đó làm evidence cộng đồng. Không có mẫu thống kê đại diện cho
“mọi quỹ/cộng đồng đều làm thế”, không xác nhận lợi nhuận từ số upvote.

### Nên version và reuse thế nào?

| Loại thay đổi | Cách lưu phù hợp project | Được reuse gì? |
|---|---|---|
| Sửa engine hoặc hạ tầng | Git commit/branch có scope; run pin actual file hashes và numerical runtime | Artifact hoàn tất còn khớp bindings; source/env drift không tự coi tương đương |
| Thay entry/exit/threshold | Candidate/version mới, giữ quan hệ với baseline và lý do trong native task/protocol | Data cache và core đã kiểm còn đúng; không mượn PnL của rules cũ |
| Giữ rules, đổi window/cost/risk | Study/run/attempt mới với input/protocol/spec pins; giữ trial history | Dùng lại dữ liệu bất biến và verified completed jobs/scenarios khi mọi binding khớp |

Project đã có candidate IDs,v1,run UUID,Git/source/input/protocol/spec hashes và
scenario/job reuse. Lượt này bổ sung registration binding và Python/Pydantic/
Decimal binding; không tạo fork repo cho mỗi variant hoặc dịch vụ tracking mới.
Parent–child research lineage toàn bộ search vẫn chủ yếu ở protocol/task, chưa
là queryable trial catalogue hoàn chỉnh; chỉ bổ sung derived index nếu có nhu
cầu tìm kiếm thật, không tạo tracker cạnh tranh Paperclip. Pin/hash giúp kiểm
đúng identity; tốc độ đến từ reuse data/artifacts, không phải bản thân Git fork.

### Khoảng trống cần đóng theo thứ tự

| Hạng mục | Hiện trạng / hành động |
|---|---|
| Correctness và độc lập | Có unit cases, causal/accounting checks; thêm independent sample oracle khi mở logic mới. Chưa independent audit toàn engine; không cần build engine thứ hai chỉ để có checklist |
| Data quality/representativeness | QDM không là feed broker lịch sử; phải kiểm gaps/session và chọn thêm regimes theo protocol trước outcome, không tự điền khoảng trống |
| Equity path/risk metrics | Chưa có peak-to-trough maxDD/underwater/concentration đầy đủ trong report; cần đo có coverage, không thay bằng minimum equity |
| Edge/uncertainty/selection | Q1/2022 đã consumed,2023 exposure unverified, sample trade nhỏ. Cần historical multi-regime rồi prospective/controlled unseen window, trial count/dependence-aware uncertainty khi đủ assumptions |
| Execution realism | Commission/slippage/financing đang declared/current-spec counterfactual; cần sensitivity hợp lý và đối soát demo, không hiệu chỉnh từ giả định để làm đẹp PnL |
| Prop fit | Cần đúng firm/program/phase/reset/DST/news/permission profile và first breach;100/500USD nội bộ chưa chứng minh pass. The5ers approval vẫn chưa có |
| Forward và nhiều strategy | Cần đối soát strategy frozen với demo đúng thời gian; nhiều chiến lược phải cùng account-wide risk/positions/pending, không nhân budget theo số run |

Đa số gaps này đã được audit trước đó ghi nhận; đối chiếu mới xác nhận chúng
vẫn cần thiết, không có bằng chứng phải rewrite engine hoặc cài thêm framework.
Screen “quý này dương ở hai cost scenarios” chỉ là tiêu chí bài đã đăng ký,
không là quy luật mọi strategy tốt phải xanh mọi quý. Không sửa tiêu chí cũ;
bài nhiều regimes về sau phải đăng ký riêng, giữ cả quý lỗ và trial thất bại.

### Đã là quant trading chưa?

**Đã là quantitative strategy research và systematic/algo trading pipeline
ở giai đoạn kiểm định.** Có giả thuyết→rules rõ→dữ liệu→mô phỏng→đối soát→
quyết định dựa evidence; không đòi ML hoặc công thức phức tạp mới được gọi quant.
Chưa có evidence cho một chiến lược prop đủ điều kiện đem kiếm tiền/scale.

Trong luồng đang có, AI hỗ trợ research/spec/code/review và điều phối. Runner
số học chạy rules/sizing/fills/costs/risk bằng code; không hỏi LLM mỗi tick để
chọn lệnh. Sau bài lịch sử vẫn cần các cửa strategy/prop/forward/authority trước
execution. System-demo evidence trước đây không tự đóng strategy-forward gap.

## Sau bài lịch sử Q1/2023, cùng05/11

Đã chạy đủ5candidate×2costs, qua artifact/accounting/state checks, giữ nguyên
rules. Numbers/quality/recovery và source/runtime pins ở [receipt AI](../checkpoints/ai-integrations-20261031/RECEIPT.md).
Q1/2023 nay là consumed; prior-exposure trong frozen registration giữ nguyên
trạng thái lúc đăng ký, không sửa để tự công nhận cleanOOS. Z-score/UTCrange
dương ở cả2costs; các bản khác không đạt screen của window. Đây chưa đóng G3/
G4/G5 hoặc quyền execution. Kết quả giữa hai quý đã thử thay đổi theo candidate;
không chuyển một quý dương thành winner bền vững hoặc bỏ các quý lỗ.

## Delta thời gian challenge — 05/11/2026

[Time-fit research](PROP-FIRM-FIT-20261102.md#thời-gian-challenge-và-độ-phù-hợp-chiến-lược--kiểm-lại-05112026)
đối chiếu FTMO/The5ers và ledger đã có: research unlimited/minimum days đã tồn
tại, nhưng screen PnL/cost chưa đủ đánh giá thời gian đạt vốn/thưởng. G4 còn
thiếu lifecycle target→đủ ngày→phase reset→phase2→payout, activation/inactivity
và đúng day boundary/equity semantics. `semantics/prop_profile.py` hiện chỉ
evaluate loss floors; không suy fields trong docs đã được runtime hỗ trợ.

Study kế tiếp phải freeze time-fit metrics/horizons cùng risk trước outcome.
Owner chọn so sánh3/6/12tháng, chưa chốt hạn cá nhân; protocol phải khóa exact
dates/calendar, không mặc định tháng=30ngày. Đây không là hạn hãng; thiếu coverage
báo chưa đủ quan sát, không tự fail hoặc dự báo pass từ quarterly return.
Ghi first breach, not-reached/censoring và trial/window dependence. Hậu kiểm
ledger vừa có là diagnostic post-hoc, không thay frozen criteria hoặc cleanOOS.
SMA có entry gap55,5ngày; UTC range chưa có cash day≥0,5% trong các day partitions
đã kiểm. Vì vậy cost-screen dương chưa chứng minh prop/time-fit hay winner.

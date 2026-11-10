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

## Ưu tiên dữ liệu gần — quyết định của owner ngày 10/11/2026

**Các nghiên cứu đăng ký mới ưu tiên từ 01/01/2022 trở đi**, theo dữ liệu được
phép dùng và phù hợp instrument/cơ chế; không mặc định mở lại lịch sử dài cho
mọi ứng viên. Mục tiêu là bằng chứng có thể áp dụng vào challenge và vận hành
sắp tới, sau chi phí và giới hạn quỹ. Không yêu cầu lời ở mọi thời kỳ/thị trường,
không có bài kiểm nào chứng minh chắc chắn lợi nhuận tương lai.

2022 là mốc ưu tiên owner chọn, không structural-break date đã được chứng minh.
Không mặc định mọi dữ liệu trước đó vô dụng hoặc thị trường gần sẽ giữ nguyên.
Research mechanisms có thể cũ nhưng vẫn cần kiểm hiện tại; phân biệt tuổi paper
với tuổi dữ liệu và khả năng thực thi. Không nâng năm xuất bản thành evidence mới.

[Đối chiếu tuổi thọ/window và trade tay-bot10/11](RECENT-WINDOWS-EDGE-DECAY-AND-DISCRETION-20261110.md)
lưu thống kê/scope và readinglist. Các khoảng3–5năm/12–24tháng/3–6tháng trong đó
là đề xuất theo vai trò, không minimumsample, protocol mới hoặc quyền mở2025+.

| Vai trò dữ liệu | Cách dùng từ nay | Điều không được suy |
|---|---|---|
| 2022–2024 trong phạm vi đã được phép | Ưu tiên development và kiểm độ bền gần theo các đoạn liên tiếp; phân tích riêng năm/quý và đóng góp sau phí | Không tự gọi 2023/2024 là clean OOS: nhiều strategies/markets đã consumed hoặc prior exposure chưa rõ |
| 2025 trở đi, gồm năm hiện tại 2026 | Giữ reserved holdout theo gate hiện có; chỉ chạy đúng window/candidate/protocol được cho phép sau freeze | Ưu tiên dữ liệu gần chưa tự cấp quyền tải/đọc/tuning holdout hoặc biến năm chưa kết thúc thành full year |
| Trước 2022 | Reuse evidence cũ; chỉ mở phần có câu hỏi stress/tail/regime, thiếu mẫu hoặc warmup/fit cần thiết đã đăng ký | Không dùng total profit dài hạn che kết quả gần yếu, cũng không xóa tail loss hoặc negatives cũ |
| Dữ liệu mới đến sau khi khóa rules | Shadow/forward/reconciliation và giám sát đúng scope đã cấp | Forward không có lệnh thật nếu chưa có authority; thời gian trôi qua không tự tạo đủ bằng chứng |

Trong nhiều component gần đây, 2019/2022 là discovery comparison đã khóa.
Hai năm rời nhau **chưa chứng minh relevance năm2026**. Các kết quả này giữ
nguyên scope/verdict; không sửa frozen gates hoặc tự promote bản lỗ2019 bằng
cách bỏ năm đó. Với hypothesis mới: chốt recent window/split trước outcomes,
audit consumed map và source quality; coverage thiếu giữ unknown. Những helper
chỉ nhận2019/2022 cần amendment, tests và version riêng trước dùng2023/2024,
không chỉ đổi nhãn năm hoặc nới holdout guard.

Thứ tự: recent development → freeze rules/cost/risk → temporal validation phù
hợp exposure → stress chọn lọc → portfolio/prop equity/time-fit → prospective
reconciliation. Bài cần huấn luyện dùng chronological rolling/expanding windows
đã khóa; rules cố định không bắt buộc retrain. Purge/embargo chỉ khi overlap
features/labels/positions cần; split theo ngày không tự loại hết leakage.
Warmup trước2022 có thể hợp lệ, nhưng không tính PnL warmup vào evaluation.

Không mặc định một độ dài 3–5năm là đủ: 12eventwindows/năm khác hàng nghìn
giao dịch có thể vẫn phụ thuộc. Báo trade/event counts, effective dependence,
uncertainty và regimes thực sự đã có; ít dữ liệu thì inconclusive hoặc mở thêm
phạm vi có cơ sở, không ép recent-only để ra winner. Nhiều ticks không tự là
nhiều cơ hội độc lập. Chưa khóa train/test dates chung cho mọi chiến lược.

Nếu chỉ có lợi thế trong một trạng thái thị trường, điều kiện bật/tắt phải
quan sát được **trước quyết định**, được freeze và kiểm ngoài dữ liệu dùng chọn
điều kiện. Không gắn nhãn retrospective “năm thuận lợi” rồi bỏ các đoạn lỗ.
Khác biệt trước/sau2022 cần nguyên nhân có bằng chứng hoặc ghi unknown; kể một
câu chuyện regime không thay statistical/causal evidence. Tail breach cũ vẫn
phải giải thích/quản trị trước deployment, không xóa vì nằm ngoài recent scope.

Portfolio áp cùng recent-first policy nhưng vẫn kiểm joint downside/exposure
và shared equity; nhiều sleeves cùng hợp2022–24 có thể cùng thất bại khi đổi
regime. Không dùng riêng correlation gần thấp làm chứng nhận đa dạng hóa.

Đối chiếu10/11: [QuantConnect Research Guide](https://www.quantconnect.com/docs/v2/writing-algorithms/key-concepts/research-guide)
về chọn nhiều factors rồi chấm lại cùng mẫu/forward paper test; [scikit-learn
TimeSeriesSplit](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html)
về chronological validation (công cụ không tự hiểu financial leakage); [AQR
trend attribution](https://www.aqr.com/Insights/Research/Journal-Article/You-Cant-Always-Trend-When-You-Want)
landing summary về biến động hiệu suất theo cơ hội thị trường, không bằng chứng
mọi thay đổi là permanent. Không đọc fullpaper AQR hoặc sao chép return/data/code.
Đây là ưu tiên research áp cho study mới, chưa backtest/holdout/strategy sửa mới.

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
| Equity path/risk metrics | Report06/11 đã có ledger-event DD/underwater/concentration; chưa full tick-path hoặc firm DD. [Annual review](TIME-FIT-RESULTS-20261106.md) giữ scope; không thay bằng minimum equity |
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

### Phạm vi thị trường, lệnh thua, risk/RR và tần suất — 06/11

Owner hỏi về scale từEURUSD, phân loại lệnh thua đúng rules và cấu hình hiện
tại. Đây là diễn giải/đọc artifacts đã consumed, không thay frozen rules hoặc
đăng ký risk/exit/market variants mới.

- Hiện tập trung EURUSD/H4. Một family có thể dùng nhiều instrument, với spec/
  cost/data và validation riêng; không bắt mỗi pair là một thuật toán khác.
  Giữ rules trước khi thử khả năng chuyển giao; sửa rules/filter/parameters là
  version/trial mới. Nhiều pair cùngUSD có thể tăng risk tương quan, không tự
  là diversification hoặc quyền nhân budget. Không ép mọi family thắng mọi asset.
- Tách **tuân thủ/quy trình** khỏi **outcome tiền**. Lệnh đúng rules nhưng thua
  là valid losing observation, tính trong win/loss/expectancy của strategy, không
  xóa hoặc tự sửa rules vì một outcome. Nó không chứng minh nguyên nhân là
  randomness thuần túy: regime/edge degradation cần xem trên sample và điều kiện
  giám sát đã định trước. Lệnh lỗi code/size/data/execution cần tag/root cause
  và quarantine evidence bị ảnh hưởng; mọi loss vẫn thuộc account PnL thực tế.
  Có thể báo valid-strategy subset riêng với denominator/gaps minh bạch, không
  giấu operational losses để công bố kết quả. Open/unknown chưa chấm win/loss;
  vẫn giữ floating PnL/exposure/risk. Đây là quy ước phân tích, chưa là claim
  đã có một classifier tự động phân biệt mọi bad trade.
- Current numerical budget:10.000USD initial,25USD risk dự kiến/trade gồm model
  costs (~0,25% initial; không tự compound theo current equity),1position,
  daily100/overall500USD **nội bộ**, không phải FTMO loss rules hay broker grant.
  Lot rounding/gaps/SL fill có thể làm actual loss khác planned1R.
- Các bản dùng initialSL2×ATR14, exit theo channel/crossover/reversion/time/range
  rules; không cùng fixed take-profit/RR1:2 hoặc1:3. Planned RR nếu có target,
  average realized win/loss ratio và net R per trade là ba khái niệm khác.
  Hiện so5candidate×2costs, không search grid nhiềurisk%/RR. Thay sizing không
  tạo edge cho rules âm; size calibration ảnh hưởng lot/cost/risk/time-to-target
  nên không mặc định scale PnL tuyến tính. Đổi TP/exit là strategy variant mới.

Làm rõ risk calibration06/11 theo câu hỏi owner:0,25% là **research baseline**,
chưa phải mức tối ưu cho FTMO/The5ers. Khóa sizing rule trong một experiment;
không cần khóa một mức tiền/risk% cho mọi giai đoạn dự án. Fixed25USD theo
initial10.000 khác0,25% current equity có compounding. Đổi mức hoặc rule sizing
là cấu hình/thí nghiệm mới: reuse data/indicator/code checks còn đúng, nhưng
phải tính lại quantity/lot rounding/cost/margin/account risk/phase path và
reconcile; không chỉ nhân ending PnL. Risk stops và min-lot có thể đổi cả tập
lệnh được phép khớp. Giữ0,25% cho bài đang freeze; chỉ hiệu chỉnh ít mức risk
trên ứng viên đáng kiểm, trước fresh validation, giữ trial history và tiêu chí
survival/drawdown/time-fit thay vì chọn mức có PnL cao nhất. Đây là khuyến nghị
workflow, chưa đăng ký/dispatch risk-grid hoặc cấp execution budget mới.

Đối chiếu nguồn06/11: [FTMO2-Step objectives](https://ftmo.com/en/trading-objectives/)
giữ daily5% initial với anchor balance00:00CE(S)T và static overall10% initial;
[The5ers High Stakes FAQ](https://the5ers.com/faqs/what-is-the-drawdown-rule-for-high-stakes/)
giữ daily5% của max(balance,equity) ngày trước tại00:00server và overall10%
initial. Các trần account này không xác định risk/trade tối ưu; không đồng nhất
reset/basis giữa hãng hoặc suy account-specific permission. The5ers vẫn cần
program/size/terms pin riêng, như snapshot đã lưu.

Tần suất **entry fills**, reference scenario, đọc results và ledger của hai bài
Q1 đã lưu (3tháng/window; không phải số tín hiệu, số lệnh đã đóng hoặc cả năm):

| Candidate | Q1/2022 entries | Q1/2023 entries | Bình quân tháng, hai quý này |
|---|---:|---:|---|
| Donchian | 13 | 12 | 4,0–4,3 |
| SMA | 6 | 6 | 2,0 |
| Z-score | 32 | 25 | 8,3–10,7 |
| Pullback | 7 | 5 | 1,7–2,3 |
| UTC range | 49 | 48 | 16,0–16,3 |

Nguồn private: `prop-q1-comparison-20261105/attempt-3/comparison.json` và
`prop-q12023-robustness-20261105/attempt-2/comparison.json`, theo từng `result_dir`
đến `results.json`/`reference-checkpoint.json`. Không phải independent samples,
forecast tần suất tương lai hoặc số liệu annual batch. Q1/2023 SMA có tháng02
không entry và gap entry55,5ngày; average2/tháng không nghĩa hai lệnh đều mỗi tháng.

Không có quota lệnh/ngày hoặc RR/risk% chuẩn cho mọi strategy. Frequency cần
xét net expectancy/uncertainty, costs, correlation, drawdown, inactivity rules và
time-fit3/6/12tháng đã chọn. Ít lệnh làm tích lũy evidence chậm; nhiều lệnh có thể
chỉ tăng phí/cùng exposure. Không ép tín hiệu, tăng size hoặc gọi một sample
trade count tùy ý là đủ. [FTMO Academy về backtesting](https://academy.ftmo.com/lesson/how-to-backtest-trading-strategies/)
phân biệt expected return/win rate/average win-loss/RRR/drawdown; không dùng các
câu marketing về historical performance hoặc automated precision trên trang
để tự khẳng định future success hay engine không có bias.

## Sau bài lịch sử Q1/2023, cùng05/11

Đã chạy đủ5candidate×2costs, qua artifact/accounting/state checks, giữ nguyên
rules. Numbers/quality/recovery và source/runtime pins ở [receipt AI](../checkpoints/ai-integrations-20261031/RECEIPT.md).
Q1/2023 nay là consumed; prior-exposure trong frozen registration giữ nguyên
trạng thái lúc đăng ký, không sửa để tự công nhận cleanOOS. Z-score/UTCrange
dương ở cả2costs; các bản khác không đạt screen của window. Đây chưa đóng G3/
G4/G5 hoặc quyền execution. Kết quả giữa hai quý đã thử thay đổi theo candidate;
không chuyển một quý dương thành winner bền vững hoặc bỏ các quý lỗ.

### Bước quyết định sau annual batch 2023 — owner đồng ý 06/11

Giữ nguyên batch đã đăng ký, không mở thêm tối ưu CPU/GPU/Rust hoặc candidate/
tham số mới trong lúc nó chạy. Dùng `horizon-report.json` và bản Markdown cùng
tên từ pipeline để đọc chung 5 ứng viên × 2 costs × 3 horizons; đó là một view
derived từ artifact đã seal, không phải ledger/task mới.

| Kết quả sau đối soát | Hành động tiếp |
|---|---|
| Lỗi correctness/binding/causal snapshot | Khoanh đúng phần bị ảnh hưởng, sửa và reuse kết quả hợp lệ; chưa đánh giá kinh tế từ evidence lỗi |
| Cả năm không dương ở ít nhất một cost scenario | Không promote phiên bản này theo cost-screen đã đăng ký; không tăng lot/sửa tham số để cứu kết quả |
| Cả hai costs dương nhưng sample/coverage/độ bền chưa đủ | Giữ nghiên cứu ở mức inconclusive; annual PnL chưa là lý do gửi demo |
| Có ứng viên đáng kiểm tiếp sau review đầy đủ | Freeze bản đó và tiêu chí, audit dữ liệu trước khi chạy validation; xử lý prop/time-to-pass ở đúng consumer |
| Không ứng viên nào còn đáng kiểm | Báo rõ đợt này chưa tìm được chiến lược; quay lại hypothesis research thành trial mới, không ép chọn winner |

Trước khi chốt giữ/loại: đọc cả Q1/2022, Q1/2023 và full-2023, lưu ý Q1/2023
nằm trong cả năm nên không cộng làm mẫu độc lập. Primary hiện tại là equity
delta sau phí, cùng trạng thái position/pending/internal stops. Còn thiếu thì
ghi gap về drawdown/tail/concentration/OOS; không tự coi chúng đã đạt từ ending
PnL. Khác biệt sample count/holding giữa các họ cần diễn giải, không áp một
ngưỡng số trade tùy ý để chọn thắng.

Không triển khai thêm full prop simulator cho cả 5 bản trước khi biết còn ứng
viên đáng nghiên cứu hay không. Native lifecycle đã có; phần nối H4 vào phase
reset/equity boundary vẫn cần cho kết luận pass quỹ, không phải điều kiện để
đọc cost-screen hiện tại. Chỉ mở dữ liệu mới sau protocol/scope đã pin; không
gọi 2024/2025 là clean OOS chỉ vì không tìm thấy metadata cũ.

### Sàng lọc ứng viên tiềm năng — đối chiếu primary sources 06/11

Owner giao sửa bottleneck kiểm lịch sử và research lại cách sàng lọc. Hai việc
khác nhau: bản sửa engine phải giữ kết quả và guards; research này làm rõ cách
chọn bước tiếp, **không thay tiêu chí hoặc candidate của annual batch đang chạy**.

**Kết luận:** khung G0–G6 đúng hướng cho nghiên cứu tái hiện được, nhưng project
chưa đủ bằng chứng để gọi một strategy đã qua kiểm định lợi thế/prop. Đợt5bản
trên EURUSD/H4 là một tập prototype nhỏ: Donchian/SMA/Pullback còn cùng họ trend,
Z-score là reversal, UTC range là breakout theo giờUTC. Có5tên không có nghĩa
đã khảo sát5nguồn lợi thế độc lập hoặc đã tìm trong toàn thị trường. Quy tắc
rõ và có thể tự động hóa là lý do chọn thử; không phải bằng chứng chúng là5bản
tốt nhất hoặc phù hợp nhất cho prop.

#### Nguồn đã đối chiếu và delta so với05/11

| Primary source kiểm06/11 | Nội dung áp dụng / giới hạn |
|---|---|
| [Arnott, Harvey, Markowitz: A Backtesting Protocol, published PDF, pp.68–73](https://people.duke.edu/~charvey/Research/Published_Papers/P138_A_backtesting_protocol.pdf) | Nay đã truy cập được full published copy, thay khoảng trống truy cập05/11. Protocol nhấn mạnh nền tảng trước outcome, giữ trials thất bại, chất lượng dữ liệu, chống sửa theo OOS, costs, đơn giản và văn hóa tìm sự thật. Cũng phải tránh loại nhầm nhiều ý tưởng tốt; không suy một năm lỗ là cả họ strategy vô dụng. Không tự nhận đây là chứng nhận project |
| [Bailey et al.: PBO](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf), [DSR](https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf) | Kiểm lại selection/multiple trials và phụ thuộc giữa các phép thử. Chọn bản cao nhất từ một tập backtests có selection bias; cùng cost/horizon không thành mẫu độc lập. PBO/DSR chỉ dùng khi trial/return/dependence assumptions đủ; chưa tính một con số giả chính xác cho5prototype hiện tại |
| [CFA Institute Research Foundation: Investment Model Validation, Joseph Simonian2024, ch.2–4,7–9](https://rpc.cfainstitute.org/sites/default/files/-/media/documents/article/rf-brief/investment-model-validation.pdf) | Backtest chỉ là một phần của validation; cần benchmark, risk, stress và kiểm cơ sở kinh tế/tài liệu. Tên search-result của PDF bị gán sai thành private equity; đã xác minh title/author từ chính PDF. Là chuyên khảo tác giả, không phải certification hoặc nghĩa vụ pháp lý của project |
| [QuantConnect Research Guide](https://www.quantconnect.com/docs/v2/cloud-platform/backtesting/research-guide) | Xác nhận workflow hypothesis→test, tránh sửa rules để khớp dữ liệu và bảo vệ OOS. Các mốc số backtests/parameters/giờ trên trang là heuristic của platform; không copy thành universal pass/fail hoặc quota |
| [FTMO Trading Objectives](https://ftmo.com/en/trading-objectives/) | Kiểm lại mục tiêu/loss/day theo2-Step và equity/reset. Xếp hạng lợi nhuận cuối mẫu chưa trả lời khả năng sống qua đường đi/phase. Không đổi terms snapshot hay tuyên bố account-certified từ trang công khai |

Đây là synthesis cho case cá nhân Forex/prop; không có bằng chứng phải mua
framework, thêm ML/LLM vào từng tín hiệu hoặc cài dịch vụ tracking mới.

#### “Tiềm năng” nghĩa là đáng chi thêm một bước kiểm, chưa phải winner

| Lát sàng lọc, nối vào G0–G6 | Câu hỏi quyết định | Hiện trạng / hành động nhỏ nhất |
|---|---|---|
| Ý tưởng và khả năng triển khai — G0 | Vì sao có thể có lợi thế, khi nào giả thuyết sai; code hóa và thực thi trong luật mục tiêu được không? | Có rules/candidate IDs; mức chuyển giao từ research ngoài sang EURUSD/H4 còn yếu. Giữ lý do và counterexample, không gắn nhãn proven từ paper khác thị trường |
| Correctness và chi phí — G1/G2 | Kết quả có do lookahead, sai tiền, gap, phí thiếu hoặc sizing sai không? | Dùng causal/accounting/seal tests và reference/stress hiện có. Lỗi bằng chứng thì quarantine; negative cost-screen thì không promote bản đang thử. Không loại cả cơ chế từ một window |
| Lợi nhuận đi kèm rủi ro — G2/G3 | Sau phí có hơn không giao dịch; mức lỗ, thời gian hồi phục, số cơ hội và lợi nhuận tập trung thế nào? | Delta07/11: hai survivors đã đo tickDD/native headroom ở annual2023 và Q2–Q3/2022; các bản legacy khác chỉ có ledger scope. Cash/floating/concentration đã có diagnostics; không gọi minimum equity là maxDD, observed quote coverage là lịch sử đầy đủ hoặc PnL cuối dương là risk tốt |
| Độ bền và sự chọn lọc — G3 | Có tái hiện qua các giai đoạn phù hợp, không chỉ nhờ tham số/window may mắn? | Đọc2023 như robustness, không OOS. Bài sau cần freeze windows/regimes, cost/delay/sensitivity và trial history trước outcome. Không bắt xanh mọi quý, không tối ưu hàng nghìn biến thể rồi chỉ giữ bản thắng |
| Phù hợp mục tiêu vốn quỹ — G4 | Với cùng mức risk, có sống qua daily/overall loss, reset và đạt các phase trong3/6/12tháng không? | Delta07/11: prop-enabled H4 đã nối native subset target/days/loss/reset; thực tế hai survivors chưa đạtphase1. Ghi not-reached/censored/unknown; không suy full firm/inactivity/payout compliance hoặc dự báo pass từ quarterly return. The5ers cần program/account/permission riêng; scope ở [period-results](PERIOD-RESULTS-20261106.md) |
| Tái hiện khi vận hành — G5/G6 | Strategy frozen có khớp signal→order→fill/cost/risk trên shadow/demo và có authority đúng không? | System demo trước đây không là strategy forward test. Chỉ mở bước này theo evidence/scope và gate execution hiện hành |

Không chấm một điểm tổng hợp tùy ý để bù correctness/OOS thiếu bằng PnL cao.
Được chấp nhận “chưa đủ bằng chứng”; tiền nghiên cứu/công sức tiếp theo dành
cho phép kiểm có khả năng phân biệt giả thuyết, không dành cho bản có chart đẹp.

#### Gói quyết định sau annual batch hiện tại

Một bảng5ứng viên dùng số đã seal, kèm cho mỗi bản: candidate/version và họ,
equity/cash/cost sensitivity, count/open exposure/internal risk stops, dữ liệu đã
dùng và gaps, quyết định cùng lý do và bước nhỏ tiếp theo. So cả các windows đã
có nhưng không cộng Q1/2023 vào cả năm như mẫu độc lập. Benchmark “không giao
dịch” trong tài khoản mô phỏng không trả lãi là0PnL; nó chỉ là mốc cơ hội/risk,
không là chiến lược có thể hoàn thành challenge.

- Không đạt tiêu chí frozen của bài: không promote **version/window đó**; lưu
  negative result. Giữ việc reject economic screen khác reject evidence do bug.
- Dương cả hai costs: chỉ qua sàng lọc sơ bộ; kiểm sample/độ bền/risk/gaps trước
  quyết định bỏ công validation. Không tự nâng sang demo hoặc mua challenge.
- Mẫu yếu/coverage/metrics thiếu: inconclusive; ghi chính xác evidence cần thêm.
- Không còn bản đáng kiểm: kết luận chưa tìm được strategy; đăng ký hypothesis
  mới có lý do, thay vì nới ngưỡng, tăng lot hoặc chọn winner bằng mọi giá.

Các tiêu chí robustness/uncertainty cụ thể của bài tiếp phải freeze **trước**
outcome mới. Khảo sát neighborhood tham số là trial/sensitivity có đăng ký,
không dùng holdout để tìm vùng đẹp. Cross-market chỉ thử khi cơ chế có lý do
chuyển giao và dữ liệu/spec phù hợp, không ép mọi ý tưởng phải thắng mọi tài sản.
Bootstrap/MonteCarlo phải giữ dependency và replay account/risk tương ứng;
shuffle trades độc lập hoặc cộng trừ vài lệnh không tự là xác suất pass quỹ.

#### Giảm chi phí sàng lọc mà giữ đúng kết luận

Ưu tiên đọc/reuse artifacts, lọc khả năng thực thi và giả thuyết trước job đắt.
Một coarse/bar-level screen trong tương lai phải có protocol riêng, nêu sai số
fill/intrabar và cách xử lý ambiguous; chưa có implementation được chấp nhận.
Nó chỉ giúp triage, không thay tick/cost/risk validation hoặc tự loại một bản
vì mô hình xấp xỉ sai. Giữ fast screening và high-fidelity qualification có
consumer/bằng chứng rõ; chưa rewrite batch hiện tại sang mô hình khác.

## Delta thời gian challenge — 05/11/2026

[Time-fit research](PROP-FIRM-FIT-20261102.md#thời-gian-challenge-và-độ-phù-hợp-chiến-lược--kiểm-lại-05112026)
đối chiếu FTMO/The5ers và ledger đã có: research unlimited/minimum days đã tồn
tại, nhưng screen PnL/cost chưa đủ đánh giá thời gian đạt vốn/thưởng. Lifecycle
offline hiện đã có target→đủ ngày→phase reset→phase2, daily/overall loss,
trailing HWM, DST/day boundary và position policy trong
`trading_workspace_v2/prop_session.py`; G4 vẫn thiếu activation/inactivity,
news/hold exceptions, payout/eligibility, historical fills và live
reconciliation. `semantics/prop_profile.py` chỉ là loss-floor oracle đơn giản,
không thay evaluator lifecycle.

Study kế tiếp phải freeze time-fit metrics/horizons cùng risk trước outcome.
Owner chọn so sánh3/6/12tháng, chưa chốt hạn cá nhân; protocol phải khóa exact
dates/calendar, không mặc định tháng=30ngày. Đây không là hạn hãng; thiếu coverage
báo chưa đủ quan sát, không tự fail hoặc dự báo pass từ quarterly return.
Ghi first breach, not-reached/censoring và trial/window dependence. Hậu kiểm
ledger vừa có là diagnostic post-hoc, không thay frozen criteria hoặc cleanOOS.
SMA có entry gap55,5ngày; UTC range chưa có cash day≥0,5% trong các day partitions
đã kiểm. Vì vậy cost-screen dương chưa chứng minh prop/time-fit hay winner.

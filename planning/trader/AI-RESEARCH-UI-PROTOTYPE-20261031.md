# AI workspace — native Paperclip UI và prototype lịch sử

## Thực thi đợt nghiên cứu mở rộng — owner giao 07/11/2026

Owner giao triển khai liên tiếp tasks kể cả discovery, vá bugs và cải tiến có
bằng chứng. [Protocol Discovery3](../research/DISCOVERY-ROUND3-20261107.md) khóa
3rules mới trước outcome;5old+3new=8implemented,2research directions cần thêm
data/contracts giữ deferred. Task này không tự coi đủ edge hoặc buộc tìm winner.

| Lát | Scope thực thi hiện tại | Acceptance / giới hạn |
|---|---|---|
| Fast triage | Reuse causal H4inspection caches, same rules, flat probes/lot feasibility | Đã đo8bản<1s; không portfolio/PnL/DD/winrate/trade-count simulator. Zero probe không loại cả họ; initial3new+UTC đều deep-check |
| Correctness / reuse | Candidate fixtures, original Forex suite, legacy4cases, independent raw→cached probes |154suite pass ở revision phát triển;8focused final candidate tests,1report integration/20controller/12horizon pass. Four232.578tick oldcases exact,8ruleprobes raw/cache match; không chứng nhận edge |
| Discovery numerical | Native finite4worker batch3new+UTC, Q1/2022consumed,2costs, sharedprep | Đã completed10:35:46VN, 4/4 verified/8rows, 13phút6giây; [kết quả/hậu kiểm](../research/DISCOVERY-RESULTS-20261107.md). Compression và UTC còn đáng kiểm, chưa edge |
| Historical robustness | OriginalUTC2024 và unchangedCompression2023; 3/6/12 tháng/native prop observations | Hai recovery v2 chạy song song từ10:50VN sau sửa holiday-before-first-quote. Raw/cache reuse, oldfailed/canceledattempts giữ riêng. Prior exposure unknown, không cleanOOS;2025+closed |
| Qualification tiếp | Đọc outcome cả hai bài theo registered criteria, giữ reject/inconclusive | Không tự risk/TP grid/broker/purchase. Live forward và execution authority vẫn riêng; không thêm skill/service/UI cạnh tranh |

Đây là scope/acceptance hiện hành cho owner request07/11, thay trạng thái
proposal-only của phần mở rộng bên dưới; receipt giữ actual hashes/run state.
Không thay frozen protocol sau outcome. Cache/probe speed khác tick economics;
không claim<1sđã đánh giá lợi nhuận hoặc baseline/full-batch speedup chưa đo.

## Sau period batch: chuẩn bị tiến tới vốn prop và payout — 06/11/2026

**Delta thực thi hậu batch:** [kết quả Q2–Q3/2022](../research/PERIOD-RESULTS-20261106.md)
đã audit completed2/2jobs/8rows. Tạm gác Z-score version hiện tại, giữ UTC range
để review validation; chưa đủ edge/prop. Đã nối UTC vào coordinator/CLI offline,
có typed state/source pin/restart và consumed-data batch parity; actual MT5
runner vẫn fixed. Lát tiếp là khóa bài validation kinh tế đúng data role/consumed
map và tiêu chí trước outcome; chưa mở2024/2025+/holdout/broker hoặc risk/TP grid.

Owner yêu cầu làm rõ mục tiêu ngắn/trung/dài hạn và chuẩn bị trong lúc batch
Q2–Q3/2022 chạy. Đích là tìm, kiểm định và vận hành lợi thế sau chi phí để tiếp
cận/duy trì vốn prop với risk kiểm soát; không phải thử mọi biến thể hoặc ép có
winner. FTMO 2-Step Swing là chuẩn chính, The5ers là nhánh so sánh chưa pin đủ.
Các horizons là mốc bằng chứng, chưa là cam kết ngày hoàn thành.

Phương pháp/tooling đã có ở [workflow](../../tooling/ai-engines/STRATEGY-WORKFLOW.md)
và [G0–G6](../../.agents/skills/strategy-qualification/references/validation-gates.md).
Bảng này giữ thứ tự scope/acceptance tiếp theo, receipt giữ trạng thái thực thi;
các bảng annual bên dưới là lịch sử và không tự dispatch risk/exit variants.

| Lát / ưu tiên | Đã có để dùng lại | Phần thiếu và kết quả cần đạt | Chuẩn bị lúc chờ |
|---|---|---|---|
| 1. Chốt batch, quyết định tiếp | Protocol, hashes, seals, accounting, tick-risk/native lifecycle, báo cáo 3/6 tháng | Đã đóng/audit: Z-score tạm gác; UTC range còn đáng kiểm nhưng inconclusive | Kết quả và scope ở period-results, không rerun để đọc report |
| 2. Chuẩn bị ứng viên dự phòng | Version/trial history, annual artifacts của cả 5 candidates, hypothesis list | Chỉ chọn phép kiểm có lý do. SMA ít mẫu/nhạy phí; Pullback lợi nhuận từ giá mỏng; Donchian version hiện tại có price PnL âm | Đã đối soát decomposition 6 annual rows, không replay; diagnostic ở receipt và survivor review |
| 3. Kiểm định kinh tế ngoài mẫu | Consumption auditor, frozen registration/runner, cost scenarios, G0–G3 | Chưa có clean-OOS evidence hoặc bộ data split cho final validation. Cần exact candidate/version, data role/coverage/exposure, metrics/baseline/stop/decision và freeze trước outcome | Giữ checklist hồ sơ bên dưới; chưa chọn/mở 2024/2025+ hoặc tạo đăng ký giả |
| 4. Risk / exit phù hợp | Fixed25USD baseline; thiết kế sensitivity12,50/25 và TP2R trong backlog | Chỉ kiểm một trục nếu diagnostic/câu hỏi kinh tế đủ lý do; mọi biến thể là trial mới, validation sau freeze | Chưa chạy risk×TP grid; không bắt đổi TP/risk để được qua stage |
| 5. Prop-fit và lợi ích owner | Declared FTMO 2-Step profile, tick DD/headroom/reset/target/day observations, time-fit research3/6/12 | Pin đúng program/account/terms/costs, các rule áp dụng/miễn trừ và inactivity/eligibility; xem survival/thời gian/fees/payout economics. Không suy xác suất pass từ vài runs | Lập evidence checklist theo profile; không mua challenge hoặc tự tạo news engine khi không có rule cần nó |
| 6. Strategy → forward/shadow → demo | Quote coordinator/CLI đã nhận UTC range offline với typed state/source pin/restart; reuse MT5 execution/grant/risk/reconciliation owners | Còn actual observed-market shadow, model-vs-broker costs/fills/recovery và strategy-specific broker handoff sau qualification/gate. MT5 runner vẫn fixed | Offline12core+6CLItests và232.578consumed ticks×2costs/two restores khớp batch; không broker calls |
| 7. Vận hành / mở rộng | Status/logs, finite supervisors, completed reuse, local recovery evidence có scope | Sau khi strategy đủ evidence: giám sát drift/risk/fills, tổng exposure account; challenge/funded/reward và mở rộng vốn theo quyền/terms | Reuse nền hiện có; cloud backup, máy dự phòng, GPU/Rust và orchestration mới vẫn để sau nếu chưa có bottleneck thực |

### Quyết định ngay sau batch, không cần chạy lại để đọc báo cáo

- Material lỗi evidence: giữ artifacts và quarantine đúng phần; sửa/reuse consumer
  khi có thể, không biến lỗi báo cáo thành lý do replay toàn bộ.
- Còn candidate đáng kiểm: tổng hợp Q1/2022, Q2–Q3/2022 và annual2023 đúng
  version/cost/account scope, tránh double-count horizons/window chồng nhau.
  Chọn một bài giải quyết bất định lớn nhất trước; không tự promote từ net dương.
- Cả hai chưa đủ: kết luận đợt này chưa tìm được bản đủ evidence. Dùng review
  dự phòng hoặc hypothesis có cơ chế rõ; không nới criteria/tăng lot để giữ winner.
- Sample thiếu: inconclusive; trước khi mở thêm data, nói rõ cần kiểm giả thuyết
  gì và coverage nào. Không lặp backtest cùng sample để tăng độ tin cậy giả.

### Hồ sơ cần khóa trước validation tiếp theo

Một hồ sơ ngắn trong protocol/dossier hiện có: (1) giả thuyết và version bất
biến; (2) consumed map và exact split/warmup/cutoff; (3) source/spec/cost/risk/
clock bindings; (4) primary net/risk/coverage cùng baseline, failure/stop/decision;
(5) cách đọc uncertainty, trial/serial dependence và prop/time-fit riêng. Nếu
chưa đủ assumptions cho bootstrap/DSR/PBO thì để unknown, không tạo tem pass.
Không áp ngưỡng win rate hoặc số trades chung cho mọi candidate; không đốt
final holdout để chọn tham số. Hồ sơ này đã chuẩn bị cấu trúc, **chưa là một
registration có data window và permission được khóa**.

### Acceptance cho việc nối research candidate vào forward

Audit trước implementation06/11: `trading_workspace_v2/forex_forward.py` dùng `FixedH4Candidate`
và `H4CandidateState`; `scripts/forex_forward.py` chỉ nhận `fixed-eurusd-h4`;
`scripts/mt5_forward_session.py` cũng khởi tạo fixed candidate. Hai research
classes đã có export/from_state, nhưng điều đó chưa chứng minh forward hỗ trợ.
Delta sau period batch: UTC range đã được nối vào offline coordinator/CLI và
kiểm parity/restart; Z-score không được thêm và actual MT5 runner chưa thay đổi.

Khi chọn version đủ điều kiện, mở rộng các entrypoints/state hiện có thay vì
viết runner/risk/UI khác. Binding phải pin exact candidate/version, spec/cost/
warmup/calendar và input role; dùng đúng candidate state, `position_id`, tuổi
vị thế/time-exit của Z-score và day/range/entry latch của UTC range. Chốt candle
watermark/next-quote causality, account reset và restart state rõ ràng.

Trước observed-market shadow: cùng frozen input/config phải khớp batch về
closed-H4 signals/stop distance/sizing/decisions/accounting trong scope, kể cả
chunk boundaries, missing bar, midnight, interrupted vs uninterrupted restore
và position mới cùng side. Đây là kiểm phần mềm trên consumed/synthetic input,
không tạo economic sample mới. Sau đó mới đối chiếu live source/identity/clock/
spread/cost; broker demo cần execution gate riêng và evidence signal→order→deal.
Chưa tự chạy chiến lược trên broker hoặc nâng trạng thái toàn sản phẩm từ plan.

Không cần skill, tracker hoặc service mới: research/qualification/evidence-
continuity và native Paperclip/runner đã giữ đúng các vai trò. Chỉ bổ sung
workflow khi gặp gap lặp thực tế; không thêm automation chỉ để có đủ các tầng.

## Đề xuất mở rộng khảo sát — 07/11/2026, chưa dispatch

Owner hỏi5ứng viên đã đủ chưa và nên dùng nền mới thế nào. Đánh giá: đủ cho
pilot kiểm integration/screening, chưa đủ gọi là khảo sát rộng để chọn strategy
thực tế. Donchian/SMA/Pullback cùng họ trend; Z-score reversion; UTC range
session breakout, vẫn giao thoa với trend/breakout. Số tên không là số edge
độc lập, chưa có minimum candidate count chung bảo đảm tìm được lợi thế.

Khuyến nghị triển khai, **chưa phải target thống kê hoặc scope được duyệt**:
mở danh mục tổng lên khoảng8–12bộ luật có cơ chế rõ (tính cả5bản cũ), thuộc
3–4hướng nghiên cứu; triển khai từng nhóm3–4thay vì hàng trăm parameter variants.
Chọn nhóm theo nguồn/cơ chế, yêu cầu dữ liệu, khả năng tự động hóa, chi phí/
holding và prop applicability. Timeframe/session mới cần contract/tests đúng;
không gọi D1momentum là exact paper replication trên EURUSD/H4.

| Lát đề xuất | Cách làm | Tình trạng công cụ |
|---|---|---|
| Lọc ý tưởng | Cơ chế/luật tái lập, data/cost/permission/holding khả thi; ghi lý do giữ/gác | Danh mục/protocol/skills đã có, chưa chọn thêm candidate cụ thể |
| Sàng lọc ít tốn tài nguyên | Reuse consumed artifacts/cached bars để triage, các giai đoạn định trước, giữ chi phí và uncertainty | Đã reuse artifacts; coarse bar-screen engine chưa có implementation/parity được chấp nhận |
| Kiểm sâu | Chỉ bản có lý do qua tick Bid/Ask/cost/risk/account path; xử lý bar ambiguity ở đây | Native tick core/registration/cache/supervisor đã có |
| Validation riêng | Freeze trước outcome; giữ trial history và dữ liệu ngoài phần dùng để chọn/sửa | Công cụ đã có; exact fresh split/permission/registration vẫn thiếu |
| Forward/demo | State/stream parity rồi observed-market/broker reconciliation theo gate | UTC offline đã kiểm; actual broker strategy handoff chưa có |

Nếu triển khai coarse screen, nó chỉ ưu tiên việc cần kiểm: không mặc định dùng
fill giả/same-bar ordering hoặc thiếu intrabar DD để loại cả họ strategy. Cần
đối chứng với tick core trên positive/negative/ambiguous cases trước khi dựa vào
nó; không bỏ chi phí để làm đẹp. Development/selection data dùng chung giữa các
ứng viên; final holdout giữ riêng, không liên tục mở để chọn bản đẹp. Ghi cả
failed/abandoned trials; nhiều variants tăng selection risk chứ không tự tăng
độ tin cậy.

Giữ UTC range validation và discovery mới là hai nhánh có mục đích riêng;
không chờ UTC fail mới bắt đầu đọc/chọn hypothesis khác, cũng không vì nó còn
dương mà coi nó là winner. Tài nguyên/concurrency phải đăng ký theo bài mới,
không sửa completed protocols hoặc tự mở2024/2025+/holdout/broker từ đề xuất này.

Primary source refresh07/11:
[QuantConnect Research Guide](https://www.quantconnect.com/docs/v2/cloud-platform/backtesting/research-guide)
ủng hộ hypothesis-driven research, hạn chế tuning/backtest selection và giữ OOS.
Con số8–12/3–4ở trên là đề xuất quy mô công việc cho project, không do nguồn đó
chứng nhận. Duke PDF timeout lượt này; giữ ngày kiểm06/11ở research cũ, không
gán lại ngày xác minh hoặc dùng timeout làm lý do thay đổi kết luận phương pháp.

### Ưu tiên cải tiến testing — rà 07/11, chưa triển khai screen mới

Owner hỏi có cần tối ưu thêm sàng lọc/testing. Khuyến nghị ưu tiên quy trình
và sai số lựa chọn trước core rewrite; giữ cache/source-bound reuse, parallel
workers, logs/seals/accounting và UTC offline parity đã kiểm. Không rerun các
suite hoặc full batch không đổi chỉ để xác nhận lại tài liệu.

| Ưu tiên | Thay đổi đề xuất | Điều kiện để dùng kết quả |
|---|---|---|
| P1 | Hai tầng: triage bằng cached bars/artifacts, tick kiểm sâu cho bản có lý do hoặc bar ambiguity | Screen mới phải được kiểm với tick core trên positive/negative/missing/ambiguous cases; nêu rõ sai khác. Không hứa exact fills/DD từ OHLC hoặc loại cứng bằng mô hình xấp xỉ chưa kiểm |
| P1 | Reason cho từng verdict: evidence lỗi, không đạt cost/risk, ít mẫu/coverage, thiếu data/permission, hoặc giữ cho review tiếp | Version/window/risk/cost và bằng chứng đi cùng; ít lệnh không đồng nghĩa không có edge, failed version không loại cả họ |
| P1 | Đăng ký trước các windows/primary metrics/stop/decision và giữ validation/holdout riêng | Không gọi reused/overlapping data là OOS, không sửa ngưỡng sau outcome hoặc thử tới khi thắng |
| P2 | Kiểm chéo cả một phần bản được giữ và bản bị gác theo cách chọn mẫu xác định trước | Đo coarse-vs-tick mismatch và lý do, không chỉ kiểm winner. Đây không là tỷ lệ bỏ sót true edge ngoài thị trường khi chưa có ground truth |
| P2 | Đo lợi ích của chính pipeline | Cùng workload: thời gian chuẩn bị/screen/tick/report, cache hit, rerun/rework, số cases phải escalate và sai khác. Chưa có benchmark mới thì không hứa speedup |
| P2 | Prop-fit kiểm applicability từ lúc chọn ý tưởng rồi đo account path ở vòng sâu | Giữ internal budgets khác luật hãng; đầy đủ equity/DD/reset, not-reached/time-fit/costs; exemptions/permissions chưa pin giữ unknown |

Ngưỡng verdict cụ thể phải theo bài đã freeze, không thêm một winrate/trade-count/
Sharpe minimum chung. Coarse screen chưa có implementation; ba ưu tiên P1trên
là proposal cho đợt mở rộng, không báo đã tối ưu xong hoặc tự chạy discovery.
Không thêm GPU/Rust, dashboards, simulator/risk engine cạnh tranh hoặc replay
toàn bộ artifacts cũ nếu chưa có bottleneck/regression thực tế cần xử lý.

## Thứ tự sau annual batch — lịch sử owner giao sắp lại 06/11/2026

Owner tiếp tục06/11 giao thực hiện [period robustness](../research/PERIOD-ROBUSTNESS-20261106.md)
trước risk/TP calibration: hai rules hiện tại,Apr–Sep2022,hai costs/risk25.
Scope này kế thừa proposal bên dưới; registration/preflight/dispatch phải đúng
protocol mới, actual state ở receipt AI. Không mở final holdout hoặc broker.

**Delta review06/11:** [review survivors](../research/SURVIVOR-REVIEW-20261106.md)
đã tổng hợp savedQ1/2022/annual2023và costs/sizing/concentration. Cả hai vẫn
inconclusive. Đề xuất kiểm thêmApr–Sep2022với rules/risk/exits cũ trước calibration
risk/TP; chưa owner-approved data window hoặc executable registration. Giữ risk/
exit tasks bên dưới trong backlog, không mặc định chạy chúng ngay sau prop-path.
Receipt giữ actual review evidence; frozen protocols/outcomes không đổi.

Delta thực thi06/11: owner giao làm đủ tick-risk/exit/short-path checks rồi chạy
hai survivors. Native evaluator adapter và actual account reset đã có source/
fixture proof,4consumed-data parity cases đạt; [study mới](../research/PROP-PATH-SURVIVORS-20261106.md)
đã dispatch13:26VN và completed16:09VN, cùng rules/risk/costs cũ. Receipt AI giữ
12verified observations: không breach declared profile, cả hai chưa đạtphase1.
Đây là full-year result trong declared scope, chưa cleanOOS/edge. Không mở risk/exit grid,
holdout hoặc broker từ dispatch này; các mục tương ứng bên dưới vẫn là lát sau.

Mục tiêu giữ nguyên: tìm và vận hành strategy Forex tự động có evidence, tiếp
cận/duy trì vốn prop với risk kiểm soát, hướng tới reward thực nhận. Không lấy
batch-complete, engine nhanh hoặc pass challenge làm mục tiêu cuối thay payout/
survival. [Workflow giải thích ngắn](../../tooling/ai-engines/STRATEGY-WORKFLOW.md#từ-ý-tưởng-đến-payout--cách-hiểu-và-vai-trò) giữ vai trò từng lớp;
[receipt](../checkpoints/ai-integrations-20261031/RECEIPT.md) giữ actual state.

| Thứ tự | Công việc / kết quả cần có | Phụ thuộc |
|---|---|---|
| 0 — ngay trong lúc chạy | Đối soát tốc độ/deadline/process và chốt handoff của current annual attempt; chuẩn bị source/config và recovery cho bản sửa `86eade80`. Không chỉ chờ timeout, không thay source của writer đang chạy | Receipt06/11 giữ stop/rollout; sau khi writer dừng đã áp main86eade80; attempt mới cần source-bound registration/config |
| 1 — đóng attempt có kiểm soát | Nếu completed, kiểm terminal/seals/accounting rồi đọc kết quả. Nếu failed/timed-out, giữ attempt/log, xác nhận writer dừng và phân loại phần dùng lại; không gọi partial checkpoint là resume | Reuse chỉ đúng bindings; source mới cần execution binding/registration và parity review phù hợp, không nới hash |
| 2 — quyết định5ứng viên | Một bảng cash/equity/cost/count/risk/gaps; từng version: không tiếp tục / inconclusive / đáng kiểm bước sau. Không có bản đạt thì trở lại hypothesis mới | Dùng outcome verified; không đổi tiêu chí frozen, ép winner hoặc tăng lot |
| 3 — kiểm chéo và khóa bài tiếp | Tận dụng independent arithmetic/causal oracles; bổ sung đúng gaps drawdown/underwater/concentration. Chọn phép kiểm robustness/OOS và freeze rules/data/cost/risk/decision trước outcome | Chỉ ứng viên đáng kiểm; audit consumed/availability, không tự mở holdout |
| 4 — phù hợp quỹ | Nối candidate vào lifecycle đúng firm/program/phase/reset; xem breach, survival và not-reached theo3/6/12tháng, cùng chi phí/thời gian thực tế | Không suy pass từ ending PnL; news/inactivity/payout/spec thiếu giữ unknown |
| 5 — forward demo | Frozen strategy chạy giá thực trong phạm vi được cấp; đối chiếu signal→risk→order→fill/cost, ngắt/kết nối lại và unknown | G3/G4 review và execution authority; system open→close test cũ không thay strategy-forward |
| 6 — challenge rồi funded/reward | Xét mua/terms/budget riêng; vận hành đúng version/risk, giữ monitoring và kiểm eligibility/reward thực nhận | Không tự mua hoặc gửi lệnh từ roadmap; payout/KYC/agreement thuộc hãng/owner |

Owner xác nhận06/11 lưu bổ sung vào việc sau batch, trước khi chọn cấu hình demo:

- **Review tránh bỏ sót:** phân biệt evidence lỗi, chưa đủ sample, cấu hình risk
  chưa phù hợp và không đạt cost-screen. Kết quả0,25% không loại cả họ strategy;
  giữ lý do không tiếp tục/tạm gác trong dossier. Không tính được tỷ lệ false
  negatives thật khi chưa biết ground truth; không tự sửa frozen verdict.
- **Risk sensitivity có đăng ký:** với bản đáng kiểm hoặc inconclusive có lý
  do cụ thể, so một nhóm nhỏ mức risk đã freeze trên development/selection data;
  giữ nguyên entry/exit để tách hiệu ứng sizing. Kiểm cả lot/cost/risk-stop/
  min-lot làm đổi tập fills, account path và time-fit. Sống qua nhiều mức risk
  là operating robustness, không thêm các mẫu edge độc lập hoặc tự promote.
- **Gói chứng cứ sàng lọc cho owner:** dùng lại G0–G6/receipt/tests để giao bảng
  claim→bằng chứng/source revision→đã kiểm/chưa kiểm→giới hạn. Có manual/independent
  cash-and-cost oracle, causal/tamper cases, kiểm report trên positive/negative/
  no-trade/insufficient samples và model mismatch; các controls mới chỉ là task
  cho tới khi có kết quả thực thi. Tách tests phần mềm khỏi validation kinh tế,
  OOS, full prop path và strategy forward; không lấy tổng số tests làm chứng nhận.
- **RR/win-rate trong dossier:** mỗi candidate giữ SL/exit version riêng đã
  đăng ký; tách planned TP/SL, realized average win/loss và net R. Báo win/loss/
  flat/open counts, net expectancy/uncertainty, losing streak/tail/drawdown và
  time-to-target. Không dùng win-rate minimum chung, không đổi TP để đạt winrate
  đẹp. Chưa coi gói chứng cứ đã xong hoặc strategy có edge từ việc lưu task này.
- **Củng cố gói chứng cứ end-to-end:** owner yêu cầu tối ưu phần chưa đủ proof
  về hệ thống sàng lọc, không chỉ tốc độ. Sau batch, rà đúng gap theo G0–G6 và
  dựng một journey mẫu có trace: raw quote/candle đã biết lúc quyết định →
  indicator/rule → signal/quantity/protection → modeled fill/cost/risk → ledger/
  verdict. Đối chiếu các điểm chọn trước với tính tay/oracle phù hợp; demo về
  sau kiểm thêm actual MT5 order/deal/cost. Phân biệt source tests, runtime đã
  kiểm, strategy qualification và payout readiness; chưa full acceptance từ hash
  hoặc một end-to-end fixture. Reuse report/trace native, không tạo UI quản lý mới.
- **So cách thoát có kiểm soát:** không thay5baseline đang chạy. Với candidate
  có hypothesis/diagnostic đủ lý do, đăng ký baseline exit hiện tại và một nhóm
  nhỏ fixed-target variants trên development đã consumed trước fresh validation.
  Cố định entry/SL/risk/cost để tách effect của exit; ví dụ thêm TP ở2×khoảng
  initialSL khi fill chỉ là đề xuất, chưa thông số được đăng ký. Protocol phải
  nói TP thay exit cũ hay thêm TP và đóng theo điều kiện hợp lệ nào đến trước,
  pin gross price-distance R khác net R sau phí, gap/tick-grid/timing/end-sample.
  Chạy lại account path vì TP có thể đổi holding/cơ hội vào sau, không cắt riêng
  trade PnL cũ. Giữ original và mọi trial; chỉ mở OOS sau freeze, không search
  đồng thời risk×TP×SL×indicator/pair hoặc chọn solely highest winrate/PnL.

Trong lúc chờ kết quả có thể chuẩn bị checklist/bộ đối chứng, dossier/report và
protocol template chưa chọn outcome; không cần mở thêm window/strategy, benchmark
đắt hoặc service. Task không phụ thuộc result thì làm trước; nhiệm vụ lựa chọn
candidate phải chờ evidence. Research strategy mới có thể tiếp tục trong lane
tách biệt về sau, nhưng không sửa bot đang được đánh giá/vận hành giữa chừng.

**Kết thúc06/11:** recovery5/5jobs verified11:31VN, pipeline/report11:32VN;
[result và hậu kiểm](../research/TIME-FIT-RESULTS-20261106.md) giữ30observations,
triage5version,4trace raw→signal→cash, proof G0–G6 và thiết kế lát tiếp.
Đã sửa numerical calendar tail cho source tương lai,127Forex+7report tests đạt;
legacy source/artifacts giữ nguyên. Sau triage, ưu tiên full risk/prop path trước
batch sensitivity; risk/exit/OOS/forward chưa thực thi và không tự cấp permission.
Receipt giữ trạng thái kiểm chứng/commit. Không mở lại cùng annual job để đổi report.

**Thực thi06/11 trước recovery:** owner giao làm phần hậu batch có thể làm ngay
rồi chạy lại. Đã thêm report diagnostics từ sealed snapshots: net trade sau
timed financing, win/loss/flat/open, average win/loss, profit factor, budgetR,
streak/concentration/monthly fills và ledger-mark drawdown/underwater. Report
giữ gap risk-path đầy đủ, không gắn DD này thành luật quỹ. Gói proof có5fixture
với oracle tiền độc lập,6report tests,7registration tests và20case quý cũ được
đối soát lại. Registration recovery và launcher mới đã khởi động; receipt giữ
actual state. Chưa chọn winner, chạy risk/TP variants, mở OOS hoặc broker; đó là
việc phụ thuộc outcome/các gate, không đánh dấu toàn bộ roadmap đã hoàn tất.

Đây là thứ tự scope/acceptance, không phải ledger thứ hai. Các phần bên dưới
giữ lịch sử; ưu tiên06/11 này thay cách diễn giải chỉ đợi annual complete rồi
mới xem xét failure path. Chưa công nhận whole-product, edge hoặc payout readiness.

## Ưu tiên chọn chiến lược — owner làm rõ 05/11/2026

Owner tiếp05/11 giao triển khai đầy đủ workflow/skills đã đề xuất và chủ động
quản lý skills. [Strategy workflow](../../tooling/ai-engines/STRATEGY-WORKFLOW.md)
reuse code/risk/Paperclip hiện có, thêm hai skill research/qualification cùng
preflight/dossier; không tạo risk engine/UI/ledger cạnh tranh. Native publication
và source validation ghi riêng trong receipt; scope không tự mở broker grant.

Tiếp05/11: owner giao khảo sát tools/MCP của FTMO/The5ers/TradingView và thực
thi đề xuất research trước. [Tool survey](../research/PROP-AGENT-TOOLS-20261105.md)
giữ quyết định reuse/defer; owner chưa có TVpaid/The5ers. [Protocol round2](../research/PROP-STRATEGY-ROUND2-20261105.md)
đăng ký hai candidate mới và hướng auto có giám sát; chỉ offline, không thay
round1 đã freeze hoặc tự cấp grant broker/OAuth/chi phí từ đề xuất.

Mục tiêu chính là tiếp cận và duy trì quy mô tài khoản prop firm lớn hơn bằng
chiến lược có lợi thế đã kiểm chứng, với rủi ro giao dịch và chi phí tham gia/
thử lại được kiểm soát. Không tối đa hóa return hoặc tốc độ vượt challenge bằng
cách tăng rủi ro. Forex/MT5, FTMO 2-Step Swing tiếp tục là hướng và chuẩn mô phỏng
đã chọn; điều kiện hãng/loại tài khoản phải xác minh lại trước khi áp dụng.

Sàng lọc theo thứ tự: quy tắc hãng và khả năng dùng bot → edge sau chi phí có
bằng chứng ngoài mẫu → daily/overall equity drawdown, tail risk và khoảng đệm
trước breach → khả năng vượt đánh giá và duy trì tài khoản/điều kiện nhận thưởng
trên nhiều cửa sổ → phí tham gia/thử lại và thời gian → sở thích vận hành.
Giữ riêng chất lượng edge và kết quả mô phỏng prop; không chọn chiến lược chỉ
vì một đường giá may mắn vượt challenge. Quy mô danh nghĩa không là ngân sách
chịu lỗ hoặc vốn owner sở hữu; không suy rằng tài khoản lớn tự làm rủi ro nhỏ.

Owner có thể để máy chạy 24/7 trừ sự cố bất khả kháng; chưa giới hạn thời gian
giữ lệnh, chọn theo bằng chứng và điều kiện tài khoản. Khả năng chịu chuỗi lỗ/
profit giveback/ít giao dịch chưa xác định, sẽ quan sát trong demo. Đây là
thông tin mới ưu tiên hơn các giả định hồ sơ cũ; không tự gán mức chịu lỗ hoặc
risk budget. Khả năng bật máy không chứng minh uptime hoặc cấp quyền gửi lệnh.
Khảo sát/đăng ký thí nghiệm tiếp theo phải bám các ưu tiên này; chưa mua challenge,
thêm phí hoặc mở phiên execution từ việc xác nhận mục tiêu.

Owner giao tiếp khảo sát/protocol 05/11; đợt đầu chọn FTMO 2-Step Swing làm
chuẩn chính và The5ers High Stakes làm đối chiếu. Đề xuất/nguồn, danh mục ý tưởng
và thí nghiệm đầu ở [protocol nghiên cứu prop](../research/PROP-STRATEGY-ROUND1-20261105.md).
Đánh giá riêng từng chương trình, không bắt candidate thắng mọi hãng; chưa xây
engine prop tổng quát hoặc mở execution từ đợt nghiên cứu này.

## Điều chỉnh 05/11/2026 — kiểm nhanh trước, quan sát dài theo nhu cầu

Owner yêu cầu cách kiểm nhanh hơn thay vì chờ cả ngày. Thay phạm vi phiên bên
dưới bằng kiểm nhanh: dùng lại clock/fault/continuity tests, replay lỗi đã lưu
và short native read khi source/runtime liên quan không đổi. Không lặp thêm
một giờ hoặc qua đêm chỉ để xác nhận lại code fix đã có bằng chứng phù hợp.

Phiên rollover được dừng có kiểm soát; giữ registration, deadline, raw capture
và lifecycle gốc. Native task có thể hoàn tất **công việc theo phạm vi mới**
bằng resolution, không biến stopped thành overnight pass. Chỉ mở quan sát dài
mới khi có hành vi môi trường cụ thể chưa chứng minh; rollover thật, downtime
thật và uptime 24/7 vẫn khác synthetic time, chưa được công nhận từ kiểm nhanh.
Receipt hiện có giữ kết quả và phần qualification còn lại; không mở thêm ledger.

## Phạm vi lịch sử 05–06/11/2026 — vận hành qua rollover, đã rút gọn

Owner duyệt tiếp giai đoạn vận hành có giám sát: Exness/FTMO chỉ đọc, một lần
ngắt/tiếp tục worker từ checkpoint và báo cáo native. Run
`7a97177c-11f4-4792-820f-0c3e25418a65`, native NAQ-89/90/91/92. Capture tới
05:15VN06/11, controllerdeadline05:20; không model/grant/OrderCheck/OrderSend,
không đổi chiến lược hoặc bật auto-boot/service. Native task/report và receipt
hiện có own trạng thái; mục này chỉ giữ scope của phiên.

Mục tiêu thu raw qua rollover độc lập với bar qualification: quarantine_v1 giữ
rawcursor khi lịch sử/nến cầnreview. Exness có boundary12:00VN05/11. Chỉ H1
hợp lệ mới seed warmup; nếu predecessor hoàn tất raw nhưng projectionheld,
handoff_policy=raw_if_held_v1 được chọn rõ để kế tiếp bằng raw session mới,
không kế thừa tín hiệu/indicator và không công nhận H1 handoff đạt. Hard
source/binding/checksum/runtime failure không được dùng nhánh này. Mọi deadline
và group/input có pin; không sửa expectedhash để resume khác nguồn.

Trong lúc chạy, giữ nguyên các sourcefiles mà registration pin. Controller-only
revision có snapshot và gate riêng; không thay pin capture hoặc tác động worker
đang sống. Không tự gọi một phiên hoàn tất có qualityhold là dữ liệu/chiến lược
đạt. Khi kết thúc, đối soát actual coverage, downtime/recovery, raw/projected
status và publication; các giới hạn không được chứng minh phải giữ rõ trong
native resolution.

## Phạm vi owner giao — hoàn thiện hệ thống, 03/11/2026

Owner giao hoàn thiện các khoảng thiếu từ dữ liệu đến vận hành giao dịch, ưu
tiên năng lực hệ thống thay vì lặp pilot hoặc tuning chiến lược. Mục này mở rộng
phạm vi offline/source của pilot bên dưới; Product Plan tiếp tục own sản phẩm,
receipt AI hiện có own trạng thái và bằng chứng. Không tạo thêm progress ledger.
Goal tự tiếp tục của Codex chưa được tạo; không cần Goal để thực thi phần đã giao.

### Kết quả cần đạt

| Lát | Acceptance hệ thống |
|---|---|
| Dữ liệu/spec/cost | Input giữ provenance, cutoff, chất lượng và điều kiện chi phí; không dùng unknown như zero hoặc phí hiện tại như lịch sử đã xác minh |
| Research và backtest | Thí nghiệm pin protocol/source/data/spec/cost và giới hạn engine; kết quả phải được kiểm chứng trước khi dùng cho bước sau |
| Promotion và forward | Handoff có artifact binding, criteria và mode rõ; system fixture không tự thành chiến lược đạt, báo cáo model không cấp quyền |
| Risk admission | Đường tự động có policy đóng băng, scope tài khoản/version, limits và stale/unknown gates trước send; không tự đổi semantics của giao dịch thủ công |
| Execution | Reuse native command idempotency, account/generation fencing, unknown reconciliation và kiểm kết quả broker; không thêm đường gọi SDK bỏ qua native API |
| Paper/forward | Có adapter đúng asset/cost/lot semantics, checkpoint/cursor và state có thể khôi phục; không gọi long-only spot accounting là Forex demo |
| Vận hành | Readiness phản ánh process đang sống nhưng mất phản hồi, degraded/recovery có bằng chứng; backup/restore và stop/restart không gửi lại lệnh không rõ kết quả |
| Trải nghiệm | Khép các chuỗi còn thiếu theo owner audit hiện có, ưu tiên tài khoản/dữ liệu/thực thi và giữ management UI native của Paperclip |

Triển khai theo dependency: nối các contract sẵn có và độ tin cậy runtime →
handoff dữ liệu/kết quả và risk/forward adapter → tích hợp native và kiểm đúng
đường vận hành → quan sát dài ngày trong phạm vi được cấp. Gộp kiểm chứng vào
thay đổi thật, focused trước; không redispatch workflow đã hoàn tất chỉ để
thử báo cáo, không thêm engine/framework/agent khi chưa có capability gap.

### Quyền và giới hạn của lần giao

- Được triển khai source, offline fixtures, tài liệu, phối hợp lane và bảo trì
  local theo standing grant trong Trader AGENTS; giữ dữ liệu/account/runtime
  ownership và rollback. Không có quyền ghi đè WIP của task khác.
- Demo order execution là gate riêng: trước một lượt gửi lệnh cần hợp đồng cụ
  thể gồm demo account, symbols, thời hạn, số lệnh/position, ngân sách rủi ro
  và stop/reconcile. Không dùng quyền thử Exness ngày29/10 cho lượt mới.
- Live/Real, challenge trả phí, provider/OAuth mới, migration dữ liệu owner,
  public deployment và service tự chạy lâu dài giữ gate tương ứng. Tiếp phần
  độc lập an toàn khi gặp gate; không tự điền risk budget của owner.
- Hoàn tất source/offline không đồng nghĩa runtime/broker/soak hoặc whole-product
  acceptance. Tiền lãi và strategy qualification là mục tiêu sau, không là
  tiêu chí ép hệ thống phải tạo kết quả có lời.

**Owner duyệt tiếp 03/11:** triển khai tách quyền Owner/runner tự động; được
migration local sau khi có backup được kiểm chứng. Giữ UI Paperclip native;
runner chỉ vào đường Demo có grant bất biến, ngân sách và account/generation
cụ thể. Quyền này cho phép xây và rollout ranh giới bảo mật, không tự cấp grant,
điền risk budget hoặc gửi lệnh demo/Real. Kiểm auth/grant/risk bằng fixture cách
ly trước; owner DB chỉ migration sau quiesce, backup DB/artifact và rollback.

### Kiểm độ bền trước vận hành Demo — owner giao 04/11/2026

Ưu tiên kiểm chặt bằng code production cùng fixture trước, rồi vận hành Demo
có quan sát để tìm lỗi môi trường thực. Không chờ 1–2 năm để kiểm logic thời
gian; không coi hai năm mô phỏng là hai năm uptime. Nhiều máy dự phòng để sau.

- Reuse runner/native receipts và backup helpers để kiểm: thời hạn theo UTC/
  offset, crash trước/sau intent và fill, lỗi ghi checkpoint, mất phản hồi,
  reconcile nhiều lần không gửi trùng; checkpoint/dữ liệu phục hồi không làm
  sống lại quyền đã thu hồi/hết hạn.
- PostgreSQL disposable: committed ledger qua crash thật và restore; so row
  counts/hash và chạy lại native admission trên dữ liệu đã hồi phục. Không dùng
  DB owner làm chaos target. Chỉ tăng workload để trả lời rủi ro cụ thể.
- Regression cần thiết vào CI hiện có; dùng receipt AI hiện hành để ghi nguồn,
  phạm vi, thất bại và kết quả. Không thêm engine, scheduler hoặc ledger mới.
- Sau gate offline, kiểm runtime Demo theo điều kiện dừng/cảnh báo và authority
  cụ thể. Đọc/quan sát không mở grant hay OrderSend. Backup ngoài máy, kênh gửi
  cảnh báo, task tự khởi động lâu dài hoặc giao dịch mới cần cấu hình/quyền đúng
  phạm vi trước khi bật; chưa có thì báo rõ, không tự chọn cloud/tài khoản mới.

Owner trả lời tiếp04/11: chưa có đích backup ngoài máy/kênh cảnh báo; hoàn tất
local trước. Hai phần external này để sau, không là quyền chọn provider mới.
Owner sau đó xác nhận G là ổ rời nhưng giao tiếp phần hệ thống, để việc backup
ổ rời/cloud lại khi cần; chưa bật copy, retention hoặc lịch backup mới.

### Tiếp nguồn dữ liệu forward — owner giao tiếp 04/11

Sau khi khép lỗi snapshot/clock, tiếp nguồn quote có thể khôi phục: reuse native
API/owned worker và identity/generation/terminal lock để đọc lịch sử tick theo
đoạn có giới hạn. Consumer ghi đoạn bất biến cùng provenance/hash trước cursor,
resume kiểm prefix và đọc lại đoạn cuối; lỗi, đổi nguồn hoặc broker sửa đoạn đã
ghi phải chặn tiến tiếp. Kiểm offline crash/network/disk/concurrency và một lượt
đọc Demo ngắn, không gửi lệnh hoặc chạy chiến lược. Requested-range cursor không
là bằng chứng đủ tick, source watermark, forward profitability hoặc 24/7 uptime.
Không cài daemon, lịch, UI quản lý hoặc state quyền giao dịch song song; continuous
forward/coverage qualification vẫn là acceptance riêng. Receipt AI giữ kết quả.

### Phiên forward shadow có giám sát — owner duyệt tiếp 04/11

Owner giao làm tiếp phiên hữu hạn: nối nguồn observed vào ứng viên H4 cố định,
quy tắc chất lượng/đóng nến rõ, Rust quản lý start/stop/deadline/recovery, rồi
kiểm một lượt chỉ đọc có gián đoạn và báo cáo native Paperclip. Không tuning,
fill/P&L giả, OrderCheck/OrderSend, lịch tự boot hoặc service 24/7 mới.

Reuse capture/provenance và owned-process Job hiện có. Requested cursor không
thành watermark: chỉ đưa giờ được yêu cầu đầy đủ, qua thời gian chờ và đọc lại
không đổi vào shadow; gap vượt chính sách chặn thay vì tạo nến. Quality vẫn là
mẫu quote quan sát, không chứng nhận đủ tick. Giờ đầu/cuối chưa đủ giữ partial;
thiếu warmup thì báo warming_up, không ép tín hiệu. Python giữ reducer/SDK path,
Rust giữ lifecycle hữu hạn; checkpoint vận hành không thay task/run Paperclip.
Receipt AI giữ source/offline/runtime và giới hạn acceptance riêng.

Owner giao tiếp04/11: hoàn thiện warmup giữa các phiên shadow hữu hạn. Phiên
kế tiếp được nhận state chỉ báo từ predecessor hoàn tất, hash đã pin, cùng
account/generation/source và nối đúng mốc H1; dừng giữa giờ phải resume phiên
cũ. Kiểm chuỗi nhiều ngày bằng dữ liệu tổng hợp trên reducer production,
không gọi đó là nhiều ngày uptime hay warmup thị trường thật. Không tự cài
scheduler, gia hạn quyền giao dịch hoặc chuyển sang tuning chiến lược.

## Hướng hiện hành — owner tự setup,01/11

### Chốt một đợt để vận hành Demo có giám sát — owner giao 04/11

Owner yêu cầu gom phần hệ thống còn thiếu thành một task hoàn chỉnh, không
tiếp tục sửa/test từng mẩu mà không có đích vận hành. Reuse issue
[`Naqex/workspace#8`](https://github.com/Naqex/workspace/issues/8); trạng thái và
bằng chứng vẫn ở receipt AI hiện có. NAQ-80 chỉ own phép kiểm shadow/handoff,
không đại diện cho toàn vòng giao dịch. Không tạo thêm ledger hoặc UI quản lý.

**Đích chốt:** một phiên Demo hữu hạn, có giám sát, đi từ dữ liệu đúng tài khoản
qua candidate cố định, intent và native risk admission đến receipt/vị thế/exit,
dừng và đối soát; khôi phục đúng khi gián đoạn, không gửi trùng. Không yêu cầu
fixture có lãi, không tuning chiến lược, không đặt mục tiêu autonomous24/7 ở đợt này.

| Thứ tự / lát | Điều kiện hoàn tất của đợt |
|---|---|
| 1. Runtime và source đang chạy | Khôi phục đúng owner API/UI/Paperclip/account, kiểm identity/generation/profile/hash và pending submissions; dùng bản shadow mới cùng registration/policy rõ. Không bật daemon, đổi auth hoặc bỏ guard để lấy green |
| 2. Dữ liệu → warmup → decision | Pin nguồn, basis/cutoff và quality policy. Reuse saved replay cho bug; nếu nạp warmup thị trường gần đây thì dùng cùng nguồn/basis, chỉ nến đã đóng trước decision, giữ lineage/known-at. Không lấy warmup2022 áp vào2026 hoặc chờ80giờ wall-clock chỉ để debug |
| 3. Decision → position/exit → native command | Rà và nối phần còn thiếu bằng coordinator/risk/native runner hiện có. Shadow flat-state không được giả thành paper/execution trader. Một decision có identity bền vững; vị thế, pending intent, SL, quantity và EXIT phải khôi phục/đối soát được, không suy unknown cost thành0 |
| 4. Stop, lỗi và tiếp tục | Chặn mở mới khi stale/identity/source/generation/risk không hợp lệ; unknown chỉ reconcile. STOP/revoke/expiry không đồng nghĩa flat. Báo exposure và hành động owner cần làm; không hồi sinh quyền hoặc tự dùng Owner/manual endpoint khi runner bị chặn |
| 5. Tiến độ và bàn giao | Native Paperclip giữ report/run, local checkpoint/log giữ bằng chứng kỹ thuật. Owner thấy phase/heartbeat/cursor/stale/error và lý do dừng. Publication lỗi sửa riêng, không thu lại dữ liệu hoặc chạy lại model |
| 6. Gate kết thúc | Reuse bằng chứng đã đạt, chỉ kiểm phần sửa và các ranh giới mới; một kiểm xuyên suốt offline/failure/recovery trên cùng code. Sau đó chuẩn bị phiên Demo cụ thể cho owner duyệt, mới kiểm đường broker còn thiếu. Không lặp open→close đã đạt nếu không có hành vi mới cần chứng minh |

Trước khi viết adapter mới, chỉ ra capability thực sự thiếu và consumer chạy nó;
reuse `forex_forward.py`, coordinator, shadow, `mt5_demo_session.py` và native
grants/receipts theo đúng vai trò. Vòng open→close tức thì không phải strategy
scheduler; không kéo dài/bẻ semantics manifest của nó để giả quản lý vị thế.
Nếu còn cần đổi contract đáng kể để nối execution, đưa proposal cụ thể vào task
trước khi triển khai theo gate hiện hành; không âm thầm đổi risk/authority.
Không ép candidate tạo tín hiệu trên broker cho đủ test. Tình huống không có
tín hiệu vẫn phải báo đúng; dùng fixture/replay để kiểm entry/exit offline,
phân biệt với receipt fill thật đã có hoặc phép kiểm broker được duyệt sau này.

Không lấy H1 live handoff hoặc80giờ warmup làm vòng debug mặc định. Phép kiểm live
cuối chỉ nhằm hành vi môi trường còn thiếu được gọi tên; có checkpoint, observer,
deadline và một attempt rõ, không tự restart từ đầu khi report/logic hỏng. Tái
hiện/sửa bằng saved data và synthetic clock trước khi cân nhắc attempt tiếp.

**Giữ gate quyền:** các grant Demo cũ đã hết hạn/thu hồi; câu hỏi readiness và
lệnh lên task không phải quyền gửi lệnh mới. Chuẩn bị đủ account/symbol/time/
volume/attempt/SL/risk/stop/reconcile để owner duyệt ở bước cuối. Backup G/cloud,
external alerts, nhiều máy, failover, scale account, provider/model mới và tuning
chiến lược tiếp tục để sau. Không dùng các phần hoãn này để chặn đợt Demo local.

**Owner ủy quyền tiếp 04/11, sau khi khôi phục Paperclip:** yêu cầu hoàn tất toàn
bộ mục tiêu Demo có giám sát, tự động thực hiện và không xin duyệt lại từng bước.
Lời giao hiện tại thay gate hỏi lại owner cho phiên Demo của chính đợt này;
không biến thành quyền Real/challenge/phí/provider mới hoặc bỏ native guards.
Agent chọn phạm vi bảo thủ kế thừa phép kiểm trước: Exness Demo hiện có,
EURUSDm, 0.01 lot, một vị thế, tối đa hai submissions, SL bắt buộc, downside
mô hình tối đa 2 USD, unknown chỉ đối soát. Mỗi grant vẫn phải pin account /
generation / artifact / expiry; không gia hạn hoặc cấp mới để né kết quả chưa rõ.
Phiên hữu hạn không ép candidate phát tín hiệu; reuse fill thật đã đạt và kiểm
entry/exit/failure xuyên suốt offline trên cùng code, rồi quan sát native Demo
với input thực. Kết quả không có tín hiệu vẫn được ghi đúng là không giao dịch.

Nối execution bằng snapshot chỉ đọc scope theo grant; không trao Owner key cho
runner. Warmup và decision dùng chung native H1 Bid/UTC, khác midpoint shadow /
QDM và có pin basis/source/SDK/clock. Bootstrap không gửi lệnh quá khứ; H1 đóng
qua30giây mới dùng, decision mới không quá60giây; receipt và inventory broker
là nguồn vị thế. Fixed H4 giữ nguyên, thêm close ở deadline hữu hạn đã đăng ký.
Contract/CLI: `projects/trader/foundation_v2/docs/LOCAL-CAPABILITIES.md`, phần
**Decision-driven finite forward session**. Không công nhận phép kiểm này là
H1 shadow handoff hoặc uptime dài ngày; không nới guard để hoàn tất task.

### Nhiều phiên độc lập — owner giao tiếp 04/11

Owner duyệt tiếp vận hành nhiều phiên cấu hình khác nhau và hỏi chi phí/quota.
Đợt này reuse Rust shadow lifecycle, checkpoint và observer native Paperclip:
khởi chạy nhiều phiên chỉ đọc, tách registration/state/log/PID, dừng/resume một
phiên không restart phiên khác; lỗi publication được sửa riêng. Kiểm hai phiên
Demo đồng thời trong cửa sổ ngắn, không thu lại1giờ hoặc yêu cầu tín hiệu H4.
Chưa mở quyền gửi lệnh mới hoặc nhiều chiến lược cùng chia sẻ vị thế tài khoản.

Execution giữ một grant đang hoạt động cho mỗi workspace/account/server Demo,
kể cả alias connection; dùng PostgreSQL transaction/advisory lock hiện có để
chống cấp quyền trùng đồng thời. Khác tài khoản vẫn độc lập. Không đổi native
order/risk/idempotency, không thêm migration hoặc portfolio allocator.

Session/run/checkpoint là trạng thái kỹ thuật của runner; native Paperclip giữ
management UI/task/report. Không thêm service/scheduler/daemon hoặc bảng budget
ngoài. Phiên quan sát/candidate cố định không gọi model; research/model workflow
dùng usage/provider_usage hiện có, thiếu usage/cost/cache vẫn unknown. Giữ quyết
định bỏ cap10lượt/ngày; chưa tự bật hard money/token budget khi owner chưa chọn.
Tối ưu gọn: tránh inference/retry trùng, reuse artifact hợp lệ, theo dõi request /
token/cache khi upstream cung cấp; subscription quota không suy từ bảng giá API.
Receipt AI hiện có own kết quả; task mới dẫn về đây, không mở lại issue#8 đã đạt.

### Ưu tiên hiện hành — hoàn thiện hệ thống AI, 02/11

Research dài hạn04/11: [nền run dài và gói qua đêm được đề xuất](../research/DEMO-LONG-RUN-FOUNDATIONS-20261104.md).
Tài liệu phân biệt nền đã có, khoảng thiếu và thứ tự nâng cấp; chưa là quyền
khởi chạy qua đêm, thay runtime đang chạy hoặc mở scope giao dịch mới.

**Owner duyệt tiếp04/11,22:42VN:** bắt đầu toàn bộ gói qua đêm và phần nền đã
chốt. Được chạy detached hữu hạn tới07:00VN05/11: Exness read-only predecessor /
successor đúng H1, FTMO read-only song song, offline failure fixtures cách ly,
resource preflight/monitor, runbook và native morning report. Không cần xin lại
từng bước trong gói. Không tạo grant, OrderCheck/OrderSend, đổi runtime/terminal
giữa capture, renew deadline, service tự boot hoặc thay scope hoãn cloud/alerts /
multi-machine/portfolio execution. Một lane lỗi không restart sibling; partial
H1 giữ checkpoint cùng phiên. Manager resume đối soát lifecycle/PID trước khi
gắn lại, không chạy lại từ đầu; mất điện/OS restart không là quyền tự boot.

Owner làm rõ: chưa muốn dành thời gian tối ưu chiến lược; ưu tiên hệ thống AI
và workflow vận hành. Đề xuất validation2023 trước đó được gác lại. Giữ nguyên
candidate EURUSD/H4, dữ liệu đã dùng và kết quả đã lưu làm fixture kỹ thuật;
không tuning, tìm candidate mới hoặc mở thêm dữ liệu để chứng minh lợi nhuận.

Lát tiếp theo: nối workflow Forex offline qua cơ chế native Paperclip đã có,
reuse QDM CLI, runner và worker phản biện hiện có. Bắt đầu từ luồng owner nhìn
được trên UI: giao nhiệm vụ → chuẩn bị dữ liệu → mô phỏng → phản biện → báo cáo.
Đối chiếu implementation/evidence hiện có trước khi sửa; bổ sung đúng mắt xích
còn thiếu, không chạy lại toàn bộ pilot crypto hoặc tạo engine/UI song song.

Acceptance hệ thống:

- Một nhiệm vụ dẫn được tới đúng input/spec/config/output bằng run ID và hash;
  kết quả hiển thị trong native task/report của Paperclip nhúng trong Trader.
- Bước sau chỉ nhận output hợp lệ của dependency đã thành công; nguồn thiếu,
  lỗi, sửa hash hoặc hủy phải chặn handoff và hiển thị hành động tiếp theo rõ.
- Owner xem được tiến độ, kết quả/lỗi và hủy; retry có kiểm tra trạng thái để
  không tạo worker trùng hoặc làm mất lịch sử lượt trước. Dùng cơ chế khôi phục
  đã có, ghi rõ phần nào chỉ hỗ trợ chạy lại và phần nào tiếp tục từ checkpoint.
- Một lượt fixture offline xuyên suốt và các failure/cancel checks cần thiết
  chứng minh luồng; kiểm latency/resource theo bottleneck đo được, không mở
  benchmark hoặc refactor rộng khi chưa có vấn đề thực tế.
- Source, runtime, workflow/provider và strategy qualification có bằng chứng
  riêng trong receipt hiện có. Workflow đạt không đòi fixture phải có lãi và
  không mở demo orders/live, scheduler hoặc quyền dùng tiền.

Thứ tự: rà luồng hiện có và biểu diễn trên UI → nối điểm thiếu → kiểm một lượt
xuyên suốt → xử lý lỗi vận hành còn lại. Không cần thêm repo/engine chỉ để đủ
thành phần. Phát triển/đánh giá chiến lược là giai đoạn tiếp theo, có giao việc
và tiêu chí riêng. [Receipt](../checkpoints/ai-integrations-20261031/RECEIPT.md)
giữ trạng thái và bước tiếp; mục này chỉ giữ scope/acceptance.

Điểm tiếp tục sau pilot02/11: mục **Workflow Forex native xuyên suốt** trong
receipt. Hoàn thiện cách owner tạo mẫu/hủy cả graph qua UI bằng khả năng native
trước; không chạy lại pilot đã thành công hoặc coi task review là duyệt paper.

### Studio — điều khiển quy trình, 02/11

**Owner điều chỉnh02/11:** dùng thẳng UI native Paperclip trong **Studio → Đội AI**;
bỏ dialog/nút Quy trình và HTTP bridge ngoài để tránh hai UI quản lý cùng task.
Trader chỉ giữ phần nhúng, preference và kết nối. Helper CLI giữ contract riêng
của graph, kiểm dữ liệu giữa engine, đối soát receipt và hủy cả nhóm bước.
Receipt mục **Studio: điều khiển workflow từ UI** giữ lịch sử lát đã thực hiện;
mục **Studio: vận hành native, đối soát run/receipt** ghi thay đổi thay thế và
kiểm chứng hiện hành. Không chạy lại model chỉ để kiểm UI.

Thứ tự tiếp theo cho hệ thống:

1. Hoàn thiện visibility về quota/chi phí và kết quả chưa xác định; đối soát
   native run/receipt trước mọi retry. Chi phí chưa biết phải hiện unknown.
2. Chỉ thêm lịch chạy khi đã có giới hạn số lượt/chi phí, chống chạy trùng,
   khôi phục sau restart và đường dừng được kiểm chứng. Lịch hiện vẫn tắt.
3. Sau đó mới xét nghiên cứu tự chủ trong phạm vi đăng ký. Tối ưu chiến lược,
   qualification và paper/demo/live là những acceptance riêng, chưa khởi động.

### Bằng chứng nền — Forex/prop offline, 02/11

Owner đã đăng nhập FTMO demo; thông số EURUSD được đọc/pin. Contract mục10
đăng ký chạy lại hai tuần và mở development quý I/2022, cả hai đã hoàn tất;
validation/holdout chưa đọc. Python offline có timed cash events, phí theo lot,
entry sau decision và stop từ actual fill. Kết quả, code/input/spec hashes và
giới hạn ở receipt; chưa là strategy/Prop qualification. Các đoạn tiếp sau giữ
lịch sử những lát trước, không phải trạng thái hay thứ tự thực thi hiện hành.
Các mô tả capability/phạm vi bên dưới giữ lịch sử của các lát trước;
không dùng chúng để chạy lại probe hoặc thu hẹp quyền dữ liệu owner vừa duyệt.

Owner đã chuyển ưu tiên sang Forex major/MT5, FTMO 2-Step Swing làm chuẩn mô
phỏng. Hoàn thành lát nhỏ: đăng ký [contract nghiên cứu](../research/FOREX-PROP-PILOT-20261102.md)
trước outcome Forex, reuse Prop domain của Trader và kiểm balance anchor độc
lập với equity. EURUSD/H4/10.000 USD và risk25 USD là giả định offline của
agent, chưa là lựa chọn tài khoản/risk budget tiền thật do owner duyệt.
[Receipt hiện có](../checkpoints/ai-integrations-20261031/RECEIPT.md) giữ source/test
results và lượt export M1/tick ngày03/01/2022 qua
[QDM CLI đã có](../../projects/trader/docs/quantdatamanager.md). Tick Bid/Ask đã
kiểm format; cost/spec còn thiếu cho Forex runner, chưa backtest outcome, workflow dispatch, UI preset
hoặc rollout; không tự mở trial/challenge/broker.
Bổ sung02/11: owner cho phép tải toàn bộ tick EURUSD vào cache QDM để reuse;
CLI đã tải xong cache và export chỉ03/01/2022 (65.215 ticks), giữ15 phút không
có quote để review. Risk guard25/100/500 USD đã có source candidate và focused
tests; chưa nối runner/runtime. Probe BUY/SELL baseline/stress đã đối soát
accounting trên giờ development đăng ký. Lượt đầu dùng terminal valuation;
lượt tiếp đã có queued causal exit với proof/JSON restart, đối soát lại4 scenarios.
Lát này còn PARTIAL ở broker spec/cost, timed financing và H4 runner;
bằng chứng/source revision/cách resume ở receipt AI được dẫn trên.
Quyền tải cache không mở quyền phân tích validation/holdout.
Các workflow crypto bên dưới giữ lịch sử và không là adapter Forex.

### Lát được giao tiếp — workflow crypto spot nối tiếp, 02/11

Owner đã chọn ưu tiên crypto và giao triển khai workflow spot: nghiên cứu →
RD-Agent/Quant Lab → Hermes phản biện → owner xem kết quả. Dùng native tasks,
parent/dependency wakeup của Paperclip; giữ đội và UI gốc. Lượt kiểm tích hợp
dùng lại contract BTC/ETH D1 cố định đã có, không tune hoặc coi dữ liệu cũ là
holdout mới. Một lần chạy lại phục vụ kiểm handoff, không tìm số đẹp hơn.

Acceptance: tạo graph idempotent; bước phản biện chỉ đọc đúng output/hash/run
thành công của dependency; dữ liệu sửa/lỗi/cancel chặn bước sau trước inference;
báo cáo nguồn và kết quả hiển thị trong Trader. Parent chờ owner review, paper
giữ NOT_RUN và không mở broker/live/lịch. Kiểm lifecycle/cancel và failure bằng
fixture offline; một real workflow qua Gemini đủ để xác minh đường tích hợp.
Source/research qualification/paper acceptance tiếp tục ghi riêng trong receipt
owner hiện có. Không cần thêm agent, engine hay vá Paperclip core.

**Kết quả:** [NAQ-20](http://127.0.0.1:17860/NAQ/issues/NAQ-20) có research
NAQ-21 và phản biện NAQ-22 nhận tự động qua native dependency. Đã sửa lỗi bàn giao
thiếu human review path bằng fixture NAQ-24, không gọi lại model; parent hiện
`in_review` giao Board, paper NAQ-23 vẫn blocked/NOT_RUN. Receipt giữ run lỗi gốc,
recovery và giới hạn browser; chưa là chiến lược đạt hoặc toàn bộ AI autonomy.

### Tiếp tục 02/11 — kiểm ứng viên cũ và mức sẵn sàng dùng tiền

Owner hỏi hệ thống đã kiếm tiền được chưa và giao tiếp tục. Lát này kiểm lại
Donchian100/50 + vol30% đã có trên snapshot BTC/ETH cũ, không tìm tham số, gọi
model hoặc mở holdout/broker. Contract ghi trước đánh giá; kết quả là chẩn đoán
dữ liệu đã xem, không phải qualification. Tái hiện rồi sửa lỗi đơn vị timestamp
ở quality audit Quant Lab; reissue manifest từ đúng CSV/hash cũ, giữ lịch sử.

Kết quả và giới hạn trong [báo cáo owner](../checkpoints/ai-integrations-20261031/STRATEGY-READINESS-20261102.md)
và receipt cùng thư mục; bản đọc đã đăng vào tài liệu NAQ-20, parent vẫn chờ
owner, paper NOT_RUN. Bước sau ưu tiên kiểm giá khớp/accounting thực tế và tiêu
chí rủi ro trước forward paper; không thêm engine hay coi lợi nhuận backtest là
quyền dùng tiền thật. Lỗi timestamp đã có focused regression, chưa phải audit
toàn bộ Quant Lab hoặc toàn sản phẩm.

### Bổ sung 02/11 — Hermes như worker tùy chọn

Owner duyệt giữ native workers và thử thêm Hermes. Acceptance: profile riêng,
Gemini qua gateway project, một task phản biện hồ sơ NAQ-6 so với cùng model/input
gọi trực tiếp; kiểm memory qua lượt mới, đăng native document và hủy SDK đang chờ
bằng fixture offline. Không thay engine số liệu, không mở broker/holdout/lịch.
Thực thi qua SDK Hermes + native process của Paperclip; CLI của release hiện hành
tự mở daemon nên không chọn làm đường worker. [Guide](../../tooling/ai-engines/hermes.md)
giữ setup/boundaries; [receipt](../checkpoints/ai-integrations-20261031/RECEIPT.md)
giữ benchmark, lỗi đã gặp và giới hạn. Không suy rộng pilot thành toàn bộ autonomy.

### Lát được giao tiếp ngày 02/11 — một workflow nghiên cứu có dữ liệu thật

Owner giao triển khai cả luồng: snapshot lịch sử cố định → một factor RD-Agent
→ Quant Lab kiểm chứng → native Paperclip hiển thị báo cáo. Dùng contract nhỏ
`crypto-momentum-3d-v1`, BTC/ETH spot khung ngày, một candidate, không tune theo
OOS. Đây là lựa chọn fixture kỹ thuật để chứng minh workflow, chưa chốt thị
trường/vốn cho hệ thống dài hạn. Không mở protected holdout hoặc broker/demo/live.

Acceptance: snapshot có nguồn/hash/cutoff và quality preflight; factor khớp
oracle/causal checks; Quant Lab so cash/buy-hold cùng timing/cost và chronological
OOS/stress; Paperclip giao việc, hủy được và giữ native report/provenance qua
reload. Source/test, real provider run, native dispatch và strategy qualification
ghi riêng trong [receipt](../checkpoints/ai-integrations-20261031/RECEIPT.md).
Không cần thêm UI hoặc engine. Worker chỉ mở sau focused checks, không scheduler.

**Kết quả 02/11:** workflow đã hoàn tất qua native task
[NAQ-6](http://127.0.0.1:17860/NAQ/issues/NAQ-6), gồm 2.922 nến BTC/ETH,
một candidate Gemini, RD-Agent kiểm factor và Quant Lab đánh giá bốn cửa sổ
OOS cùng chi phí/stress. Native cancel đã kiểm riêng, báo cáo giữ qua reload
trong iframe Trader. Candidate chưa đủ điều kiện chuyển sang demo; worker hiện
idle, timer off. Các dòng paused/chưa nối bên dưới mô tả thời điểm trước đó;
[receipt](../checkpoints/ai-integrations-20261031/RECEIPT.md#0211--workflow-market-factor-qua-native-paperclip)
giữ kết quả, giới hạn và bằng chứng hiện hành.

### Bổ sung sau owner giao nối engine,01/11

Owner đã giao triển khai TradingAgents trước rồi RD-Agent, và chọn **các model
Gemini** cho lượt chạy thực tế; key Opus5.5 trước đó đã hết hạn. Scope mới cho
phép tạo worker engine qua API gốc của Paperclip, không thay agent do owner tạo.
Native process adapter giữ dispatch/cancellation; wrapper giới hạn input, dùng
API upstream engine và trả báo cáo về tài liệu công việc trong UI Paperclip.

Acceptance lát tiếp: một yêu cầu phân tích được giao đúng worker → model Gemini
qua gateway project → báo cáo VI và provenance trong công việc; chặn input sai,
không chạy lại outcome chưa rõ và không có broker execution. Source/fixture,
Paperclip dispatch và model success phải có bằng chứng riêng trong receipt owner
hiện có. Không đồng nhất báo cáo phân tích với backtest/chiến lược đạt.

Owner đã cho phép cài runtime RD-Agent ngày 02/11. Package và container smoke
đã đạt trên WSL2 Ubuntu 24.04 + Docker Engine riêng; chi tiết trong
[runtime guide](../../tooling/ai-engines/rd-agent-runtime.md) và receipt hiện có.
Trước workflow thị trường bên trên, pilot factor giả lập ngày 02/11 đã đạt: một candidate Gemini chạy qua upstream
workspace/evaluators trong Docker, oracle và kiểm tra nhân quả đạt. Worker tiếp
tục paused tại thời điểm pilot; lúc đó còn data adapter thị trường, vòng finance
và native dispatch trước khi mở worker. Không chạy code sinh trên host Windows; pilot chưa là bằng chứng
chiến lược có lợi nhuận. Recipe và evidence theo runtime guide/receipt bên trên.
Hướng dẫn adapter: [engine jobs](../../tooling/ai-engines/README.md).

Các đoạn cleanup/tự setup sau đây giữ lịch sử trước phần bổ sung này.

Owner yêu cầu lưu kết quả test, dọn đội/config/custom UI mẫu và giữ Việt hóa.
Đã dùng API upstream dọn company pilot Naqex AI cùng dữ liệu thử; instance không
còn company. Đã bỏ ResearchTeamPreview và bản vá adapter Windows phục vụ pilot;
giữ localization, bridge ngôn ngữ, static embedding và fix giữ navigation/state.
Gateway project17852 đã dừng/phục hồi override; tài khoản project giữ nguyên.

Owner tự tạo organization → project → một agent qua UI gốc; chỉ giao task sau
khi runtime Test Environment đạt. Không tự provision lại. Native Copilot trong
bản pin bị giới hạn production ACPX trên Windows; Antigravity pending upstream.
MCP có sẵn nhưng cần authenticated deployment/public origin/experimental gate
và OAuth; instance local hiện chưa cấu hình, không đổi auth trong lượt cleanup.

[Hướng dẫn và nghiên cứu](../../tooling/paperclip/README.md),
[kết quả pilot và cleanup](../checkpoints/ai-integrations-20261031/RECEIPT.md)
giữ bằng chứng/giới hạn. UI audit rộng tiếp tục pause. Các mục sau là lịch sử.

## Lịch sử mở rộng UI — 01/11

Đã mở rộng bản dịch VI/EN sang các trang/menu/dialog chuyên sâu của fork bằng
catalog i18next riêng. Trang Agents có **Xem đội và nhiệm vụ mẫu**: sơ đồ ba
vai trò và một nhiệm vụ nghiên cứu để owner duyệt, chưa provision agent/job.
Source Paperclip `11d41b6`; runtime local đã cập nhật cùng revision, giữ DB.
Phạm vi kiểm chứng và giới hạn nằm trong mục ngày01/11 của
[receipt tích hợp](../checkpoints/ai-integrations-20261031/RECEIPT.md).

Tại thời điểm lát UI này, còn cần review trước khi cấu hình agents, provider và
contract chạy job engine. Các mục31/10 dưới đây
giữ lịch sử, không thay coverage và trạng thái mới trong receipt.

## Lát localization tiếp nối — 31/10

Đã nối VI/EN từ Trader preview tới native Paperclip bằng preference message
kiểm origin/source; đổi ngôn ngữ giữ document, bản nháp và search. Fork dùng
i18next namespace `workspace` riêng, giữ locale upstream và tên/nội dung do
người dùng nhập. Phạm vi hiện tại: navigation desktop/mobile, account actions,
task breadcrumb/search/empty/create và trường chính của new-task dialog.
Đây là bản dịch từng phần; filters/composer settings và các trang khác còn EN.

Browser preview5218: 9 cases trên1920/1440/390px; source review độc lập;
focused unit/component, UI typecheck và build đã kiểm. Token gate toàn fork
còn106 lỗi upstream, không thêm lỗi so với pin cũ. Receipt chi tiết nối vào
`planning/checkpoints/ai-integrations-20261031/RECEIPT.md`.
Chưa cấu hình agents/provider hoặc chạy engine job. UI audit rộng vẫn pause;
tiếp theo hoàn thiện các luồng UI cần dùng và cấu hình company/roles cho owner
review trước khi nối job. Root gitlink Trader vẫn giữ baseline để tránh đưa WIP
audit vào lát integration; host feature checkout được ghi ở receipt.

## Lát adoption được owner giao — fork, source và AI environment

Issue: [Naqex/workspace#6](https://github.com/Naqex/workspace/issues/6).
Owner chọn fork Paperclip gốc, RD-Agent, TradingAgents và LangGraph; giao thực
hiện fork/tích hợp và rà skill dài hạn. Thứ tự UI trước engine vẫn áp dụng.

Acceptance lát nền source/runtime:

- Paperclip có fork Naqex và upstream remote riêng; giữ revision đã kiểm chứng,
  không tự nhảy lên master mới nhất khi tạo fork.
- Source ngoài dưới `projects/integrations/`, giữ submodule/layout/license; RD-Agent
  được pin source. LangGraph giữ là dependency TradingAgents, Quant Lab giữ nguyên.
- Paperclip đang nhúng vẫn hoạt động sau chuyển đường dẫn; giữ nguyên company,
  dữ liệu, cổng và preference sidebar. Backup và rollback được ghi trước cutover.
- Hướng dẫn gần source, một skill repo cho workflow upstream đã được thực hiện;
  không tạo skill nghiên cứu AI từ luồng chưa chạy hoặc thay global config.
- Kiểm topology/đường dẫn, dependency/import và native browser phù hợp với thay đổi.

Lát này không chứng minh RD-Agent/TradingAgents đã chạy job model hay toàn vòng
autonomy. Các lát nối engine sau phải có contract job thực tế, authority cho
dispatch/retry và evidence riêng; không khai agent chạy được chỉ vì đã clone source.
Checkpoint của lát này: `planning/checkpoints/ai-integrations-20261031/RECEIPT.md`.

## Lát được giao tiếp theo — native Paperclip

Owner xác nhận nối UI gốc và lưu source trong `projects/`. Đã tích hợp submodule
upstream `projects/paperclip` tại pin `42fd568cf8f588334cacc6004aa23aff54daa52b`,
giữ source nguyên bản. Trader mở AI→Paperclip bằng iframe toàn vùng nội dung;
rail bên ngoài giữ lựa chọn của owner, bên trong dùng điều hướng và dialogs gốc. Dữ liệu
Paperclip có instance riêng; chưa nối engine nghiên cứu/giao dịch.

[Setup/runtime boundaries](../../tooling/paperclip/README.md).
Evidence/source/runtime và các giới hạn được giữ trong receipt
`projects/trader/foundation_v2/evidence/paperclip-ui-20261031/RECEIPT.md`.
Implementation ban đầu ở Trader `98a0871b`, điều chỉnh port/sidebar ở `18e9348d`; gitlink Trader của root
chưa nâng vì HEAD hiện tại còn chứa lịch sử ngoài phạm vi tích hợp này.
Owner yêu cầu tách cổng khỏi app Windows: Paperclip hiện dùng API17860/DB17861/
HMR27860; CLIProxyAPI managed giữ17852, không chạm instance Windows8317.
`foundation_v2/local-services.json` trong Trader giữ cấu hình dùng chung;
`docs/LOCAL-SERVICES.md` và receipt `PORTS-SIDEBAR.md` giữ hướng dẫn/bằng chứng.
Preview owner tại
`http://127.0.0.1:5218/?workspace=tenant-a&view=ai&area=ai&section=paperclip&lang=vi`.
Các đoạn phía dưới giữ lịch sử quyết định/prototype, không thay trạng thái mới.

## Điều chỉnh hướng sau owner review, 31/10

Owner yêu cầu thiết kế UI từ tổng thể vào chi tiết: khung workspace → điều
hướng → UI upstream → các hành trình trading riêng. Ưu tiên nhúng UI gốc
Paperclip như cách Trader nhúng CLIProxyAPI; không tiếp tục dựng các màn quản
lý công việc/agents riêng để thay thế Paperclip.

Prototype `5aafd680` bên dưới giữ làm bản khám phá workflow, chưa được owner
chấp nhận làm giao diện đích. Build/browser receipt của prototype không chứng
minh Paperclip đã tích hợp. UI audit rộng vẫn pause.

Lát tiếp theo đề xuất: Trader giữ điều hướng cấp sản phẩm; khu AI dành vùng
nội dung cho Paperclip với điều hướng nội bộ của chính nó. Khi ở khu này, thu
gọn điều hướng Trader để tránh hai sidebar đầy đủ cạnh nhau. Chốt khung và
chuyển qua lại trước khi làm màn nghiên cứu riêng hoặc nối engine.

Nguồn kiểm tra: [repo upstream](https://github.com/paperclipai/paperclip),
[server](https://github.com/paperclipai/paperclip/blob/master/server/src/app.ts),
[API client](https://github.com/paperclipai/paperclip/blob/master/ui/src/api/client.ts)
và [MIT license](https://github.com/paperclipai/paperclip/blob/master/LICENSE).
UI gọi `/api` trên origin của Paperclip, nên hướng thử đầu là iframe nguyên
ứng dụng tại origin local riêng; không copy riêng bundle vào origin Trader.
Đây là đánh giá từ source, chưa xác nhận iframe/auth bằng runtime. Cần pin
revision và kiểm framing headers, login/cookies, điều hướng, sự kiện và layout
trên đúng bản chạy trước khi kết luận tương thích.

UI gốc cần API/storage của Paperclip để hoạt động; chạy instance local phục vụ
review UI là một lát riêng với dữ liệu riêng và không tự giao việc cho agent.
Chưa cài/chạy instance hoặc nối trading engine từ lần điều chỉnh này. Không
đặt tối ưu hiệu năng giả định thành điều kiện chặn; mount khi mở lần đầu và
giữ state nếu phù hợp, đo bottleneck thật sau. Ẩn UI không có nghĩa dừng agents.

## Scope prototype lịch sử

Owner giao ngày31/10: làm UI trong Trader trước để review workflow; backend và
services chỉ tiếp sau feedback. Owner cho phép thử CLIProxyAPI/Gemini, nhưng lát
UI này không cần gọi model. Brief kiến trúc: [autonomy](../research/AUTONOMOUS-TRADING-SYSTEM-BRIEF.md).

## Phạm vi

- Khu AI có mục Nghiên cứu, dùng shell và design system hiện có.
- Danh sách có tìm kiếm/lọc; chi tiết có quy trình, thử nghiệm và nhật ký.
- Dialog tạo bản nháp với mục tiêu, data/baseline mẫu và giới hạn số lần thử.
- Trạng thái mẫu: đang chạy, hoàn tất/chờ review, thiếu bằng chứng, lỗi và dừng.
- Quyết định demo chỉ là preview; không tạo run, gọi broker hoặc ghi DB.
- State lưu local theo workspace, có báo lỗi lưu và khôi phục mẫu có xác nhận.

UI phải ghi rõ dữ liệu minh họa; không dùng metric giả như bằng chứng nghiên cứu.
Reuse LegacyModal, FxSelect, SearchInput, AppIcon, palette và compact controls.
Giữ VI–EN, dark/light, keyboard/focus và layout desktop/mobile. Không resume
owner-system audit đang pause hoặc stage WIP của nó.

## Kiểm chứng và bàn giao

Build ở output riêng; browser journey trên UI hiện hành với API fixture/deny
cho writes và external traffic. Kiểm create→reload, search/filter, tabs,
stop/decision preview, empty/error, Escape/focus và mobile/light. Review ảnh
thực tế. Receipt source/build/fixture tách khỏi backend/provider acceptance.

Trạng thái/evidence và hướng mở preview giữ trong receipt tại
`projects/trader/foundation_v2/evidence/ai-research-ui-20261031/`.
Source checkpoint trong repo Trader: `5aafd680`.
[Preview UI riêng](http://127.0.0.1:5218/?workspace=tenant-a&view=ai&area=ai&section=research&lang=vi).
Owner xem prototype trước khi giao lát backend/services. Plan này chỉ own scope,
không đóng Product Plan/U/Y/W hoặc cấp quyền live.

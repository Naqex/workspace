# Workflow chiến lược

[AI plan](../../planning/trader/AI-RESEARCH-UI-PROTOTYPE-20261031.md) giữ scope;
[receipt](../../planning/checkpoints/ai-integrations-20261031/RECEIPT.md) giữ
bằng chứng. Paperclip own task/run/report; không thêm tracker/UI riêng.

| Chặng | Skill/tool | Bàn giao |
|---|---|---|
| Ý tưởng/spec | [strategy-research](../../.agents/skills/strategy-research/SKILL.md), research index | Candidate/version, hypothesis, nguồn/license/unknowns |
| Rule/data/risk | Profile/spec/QDM/validator hiện có | Program/phase, source date, cost/risk/consumed map |
| Code/check/run | Opt-in runner/tests/preflight | Manifest/quality/results/receipt/decisions |
| Qualification | [strategy-qualification](../../.agents/skills/strategy-qualification/SKILL.md), `strategy_evidence.py inspect` | Correctness/edge/prop/operations/authority và next stage |
| Hậu kiểm batch | [engineering-retrospective](../../.agents/skills/engineering-retrospective/SKILL.md) | Sau screening/validation có evidence mới: sửa bounded theo bottleneck, đo parity/timing, giữ bài học cho lượt sau; không ép tối ưu mỗi lần |
| Shadow/demo/operate | [Studio](../../.agents/skills/studio-operations/SKILL.md), runtime/grant/lifecycle | Binding/quote/risk/reconciliation/recovery |
| Context/skills | [evidence continuity](../../.agents/skills/evidence-continuity/SKILL.md), [maintenance](../../docs/development/SKILL-MAINTENANCE.md) | Locator/revision/delta, không copy ledger/raw logs |

Không cần agent/task riêng mỗi hàng. Fixed process worker không tự nhận câu hỏi
mới từ Markdown; coding agent chạy study riêng, lead delegate theo capability.

## Từ ý tưởng đến payout — cách hiểu và vai trò

**Ý tưởng → quy tắc rõ → thử quá khứ → kiểm chéo/ngoài mẫu → demo → challenge
→ funded account → reward thực nhận.** Đây là đường đi mục tiêu; project hiện
ở nghiên cứu/sàng lọc, chưa có strategy được công nhận đủ evidence đi hết luồng.

| Thành phần | Công việc |
|---|---|
| AI agents | Tìm/đọc research, giúp viết và review code, lập thí nghiệm, giải thích kết quả, điều phối và phân tích sự cố |
| Bot chiến lược | Đọc dữ liệu mới, tính tín hiệu và đề nghị mở/đóng theo bộ rules đã khóa. Có bot không có nghĩa đã có edge |
| Risk và execution owner | Kiểm account/quote/quyền/lot/exposure/budget trước khi gửi; quản lý pending/unknown và đối soát phản hồi MT5. Signal không tự là permission |
| Paperclip và bằng chứng | Native task/run/report; logs/checkpoint/artifacts ghi quá trình. Không biến Markdown/report hoặc LLM thành authority gửi lệnh |
| Owner | Chọn mục tiêu/ngân sách, theo dõi, xử lý quyết định account/terms/reward; không cần tự bấm mọi tín hiệu trong mode auto được cấp quyền |

Luồng giao dịch dự kiến: **giá MT5 → bot tính tín hiệu → risk/authority kiểm
→ runner gửi qua MT5 → nhận kết quả và đối soát → ghi trạng thái**. Offline
backtest hiện tại dùng lịch sử và mô phỏng execution, không gửi broker/model.
Shadow chỉ quan sát/mô phỏng theo mode; broker demo mới gửi lệnh trong tài khoản
demo theo grant. Production dùng tài khoản đích và đúng gate/version; không
đồng nhất khả năng research hoặc system-demo với việc đã sẵn sàng production.

LLM không nằm trong quyết định mỗi tick/lệnh ở numeric strategy hiện tại. AI
có thể tiếp tục research/monitoring bên cạnh bot; đề xuất thay rules là version
mới phải qua kiểm định và handoff, không tự sửa bot đang chạy. ML offline có
[thí nghiệm bounded](../../planning/research/DISCOVERY5-RESULTS-20261108.md), hai
policies thất bại và chưa nối native broker path. LLM-in-the-loop chưa thuộc
đường hiện tại; không suy model export thành quyền hoặc edge.

Edge là evidence cho lợi thế sau chi phí, vẫn có lệnh lỗ và có thể suy giảm.
Monitoring tiếp tục sau demo/challenge/funded: kiểm execution, risk, drift và
điều kiện dừng/giảm rủi ro đã định trước; không tự tuning sau mỗi lệnh thua.
Lỗi/mất kết nối không bảo đảm vị thế đã flat; chặn mở mới theo gate, đối soát
pending/unknown trước khi gửi lại. Logs/backup/recovery là phần vận hành,
không chứng minh strategy có lời hoặc CLI research resume đã hỗ trợ.

Với FTMO CFD, **funded account vẫn dùng simulated capital**; Reward có thể là
tiền thật khi đáp ứng trading objectives/terms và qua quy trình hãng. Lãi trên
màn hình, pass evaluation và tiền đã nhận là ba trạng thái khác nhau. Đã đọc
[FAQ reward chính thức06/11](https://ftmo.com/en/faq/how-do-i-withdraw-my-profits/);
không suy luật FTMO sang The5ers hoặc tự động hóa yêu cầu/rút reward. Phí challenge,
retry và chi phí vận hành cần tách khỏi simulated PnL khi đánh giá lợi ích owner.

Khung/checklist theo stage ở
[validation gates](../../.agents/skills/strategy-qualification/references/validation-gates.md),
căn cứ và current gaps ở [framework audit](../../planning/research/STRATEGY-VALIDATION-FRAMEWORK-20261105.md).
Protocol/data/source hashes và exit0 không tự chứng minh preregistration timing,
causality, OOS hoặc prop fit. Dossier `review_checks` tách mechanical checks khỏi
phần chưa được tool đánh giá; dùng bảng gate/evidence trong mọi đề xuất đổi stage.

## Preflight cùng runner

Trước đổi window, dùng `research_consumption.py --root <explicit-root>` (lặp
`--root` khi cần) `--output <new-audit.json>` để inventory bounded JSON metadata.
Không mở CSV, không đi theo directory links ra ngoài root, không xuất PnL/quotes;
vẫn parse toàn JSON trong size limit. Output ghi coverage gaps và phân biệt
planned registration với executed-run metadata. Absence không chứng minh unseen,
record có dates cũng không tự chứng minh đã xem giá. Owner history chưa rõ thì
ghi unverified. [Protocol hiện hành](../../planning/research/PROP-HISTORICAL-ROBUSTNESS-20261105.md)
giữ nhãn/cutoff/tiêu chí/pins của bài kế tiếp. Runner đã có opt-in registration
support và synthetic integration evidence theo receipt; chưa có market run mới.
Không đổi dates để vượt guard2022 hoặc tự gọi registration là quyền holdout.

Để chạy registration đã hỗ trợ, thêm `--study-registration <registration.json>
--study-registration-sha256 <registered-hash>` cùng candidate/input/protocol/spec.
Batch job config dùng `study_registration` và `study_registration_sha256` để
forward đúng pair đó; trước dispatch kiểm pin/role/candidate. Dossier nhận schema
historical riêng, giữ exposure unverified và không auto-promote. File registration
freeze cũ không sửa để cập nhật trạng thái; receipt/implementation binding giữ delta.

Từ `projects/trader/foundation_v2`, Python `.venv` đã có:

```powershell
& .venv/Scripts/python.exe scripts/forex_h4_pilot.py --input-dir <input-root> --input-manifest <pinned-inputs.json> --output-dir <new-preflight-dir> --candidate <registered-id> --research-protocol <protocol.md> --preflight-only
```

Giữ account-spec/hash nếu có như [runner guide](../../projects/trader/foundation_v2/docs/FOREX-RESEARCH.md).
Output mới chặn hai writer cùng attempt, không chứng minh dedup mọi job ở các
output khác nhau. Preflight kiểm contract/hash/coverage/warmup và account fields
được hỗ trợ; không simulation/orders/OOS mới. Nó đọc development để kiểm data
nên phải ghi consumption. Output chỉ manifest/quality/receipt, không results.
Run thật dùng output khác; không lặp preflight bên ngoài khi runner đã thực hiện
cùng checks và inputs không đổi. Không sửa hash để ép input đạt.

### Batch development hữu hạn trên Windows

`forex_study_batch.py --config <registered-config.json> --output-dir <batch-dir>
--max-workers 3 --worker-seconds 1800 --deadline-seconds 5400` chạy bằng Python
venv Trader đã có. Config giữ từng candidate/input manifest/protocol/hash/spec
và tick count đã đăng ký, không nhận command/provider/broker tùy ý. Đọc lại
protocol cho phép deadline/concurrency trước chạy; các số trên là trần của
đợt Q1 hiện tại, không phải ETA hoặc default nghiên cứu chung.

Candidate đầu chạy một mình trước; sau khi kiểm kết quả mới mở đủ số slot.
Đây là mặc định của các bài đã freeze, không phải yêu cầu phải lặp full probe
cho mọi study tương lai. Bài mới có baseline phù hợp và protocol cho phép có
thể dùng `--parallel-start`; option được pin trong batch manifest, từng worker
vẫn full preflight/accounting. Không sửa option trong attempt đã có.
Quality/H4 warmup có thể chuẩn bị một lần bằng
`scripts/forex_prepare_inspections.py --input-manifest <pinned-inputs.json>
--cache-dir <private-cache>` trong Trader foundation_v2. Job config thêm
`inspection_cache_dir`; chuẩn bị xong trước dispatch. Reader vẫn hash raw bytes,
kiểm source/runtime/window/checksum; missing/corrupt/drift fail rõ, không rebuild
trong worker. Simulation vẫn đọc đủ ticks của từng scenario, không chia sẻ risk
hoặc candidate state. Với nhiều candidate/cost scenario, thêm `--include-ticks`
và đặt cùng `prepared_inputs_dir` trong batch jobs; runner chuẩn bị quality/H4 và
lossless development tick cache một lần trước worker. Mỗi worker vẫn rehash
raw/cache và kiểm thứ tự/grid/schema; cache không thay source QDM hoặc artifact
strategy. [Chi tiết và recovery](../../projects/trader/foundation_v2/docs/FOREX-RESEARCH.md#shared-quality-and-h4-warmup-inspections).
Supervisor dùng lại Windows JobObject của runtime với stdin gate, interpreter
thật và import paths của venv: child không làm nghiên cứu trước khi thuộc job.
Cancel/timeout/crash đóng cả cây; `CANCEL` trong batch-dir dừng việc chưa xong.
Không cần terminal MT5, Paperclip service hoặc model cho batch offline này.

`progress.json`/`PROGRESS.md` cập nhật5giây từ worker receipt và terminal riêng.
Exit0 chỉ được `completed_verified` sau dossier/accounting/bindings check.
Chạy lại đúng config/output sẽ kiểm và reuse **job đã hoàn tất**, không chạy lại
chúng. Job chưa xong/lỗi cần attempt mới có chủ đích; giữ thư mục cũ, không tự
retry/overwrite hoặc gọi đây là resume giữa mô phỏng. Lock còn sau crash phải
đối soát process và artifacts trước xử lý, không tự xóa để chạy đè.
`--reuse-from <older-batch-dir>` cho một attempt mới kiểm và tham chiếu các job
đã hoàn tất của batch cũ; các job cũ failed/partial không được reuse. Result
locator từng hàng ở `progress.json` có thể trỏ về batch cũ; không copy hoặc ghi
đè artifacts đó. Supervisor failure có source frames và terminal riêng; projection
cũ còn `running` phải đối soát, không tự kết luận worker còn sống.

Job config có thể đặt `reuse_scenarios_from` thành đường dẫn `replay` của attempt
đã dừng để CLI kiểm và dùng lại scenario có completed seal. Output luôn mới;
không tự retry failed job và không sửa raw attempt cũ. Thiếu seal hoặc mismatch
là lỗi rõ ràng, không âm thầm tính lại toàn bộ. Đây là scenario-boundary reuse,
khác restore giữa simulation. Legacy outputs và source-version drift cần
review riêng, không tự công nhận tương đương. Xem
[contract runner](../../projects/trader/foundation_v2/docs/FOREX-RESEARCH.md#reuse-a-completed-scenario-after-interruption).

Với source9fd6cd00 trở đi, `resume_scenarios_from` trong batch config forward
CLI `--resume-scenarios-from`: reuse completed seals và restore complete
`<scenario>-resume.json` của scenario còn dở. Không đặt cùng `reuse_scenarios_from`.
Packet phải đủ strategy/builder/execution/risk/observer/phase/input cursor và
source/data/protocol/cost/runtime vẫn khớp; revalidate prefix trước tính tiếp.
Missing legacy packet fail rõ, không tự restart hoặc nâng cấp checkpoint cũ.
[Bằng chứng và phạm vi](../../planning/research/NATIVE-RESUME-REVIEW-20261108.md)
giữ interrupted/uninterrupted parity và phần chưa đo; không là quyền broker.

## Dossier từ artifact

Status/log/failure conventions: [observability](OBSERVABILITY.md).
`strategy_evidence.py status --run-dir <attempt>` đọc progress và last-update age,
không xác minh process sống hoặc tự restart job.

```powershell
python -X utf8 tooling/ai-engines/strategy_evidence.py inspect --run-dir <completed-study-dir>
```

`--verify-inputs` hash CSV khi cần integrity check; `--source-root <foundation_v2>`
so source hiện tại. Drift không xóa evidence lịch sử, chỉ hạn chế tái hiện.
Tool kiểm invariants/bindings, không thay core accounting, statistical review
hoặc chứng thực nguồn artifact. Không overwrite run hoặc sửa ledger để tự pass.
Development dossier luôn `promotion_authorized:false`, kể cả PnL dương.
Historical-robustness dossier cũng giữ false và không tự thành clean OOS.
Reuse completed job/scenario cần khớp Python/Pydantic/Decimal binding ngoài
source/input/protocol/cost. Environment cũ chưa ghi thì không tự suy tương đương.
Không tính maxDD từ minimum equity rời rạc; giữ open PnL và coverage rõ.

## Tái sử dụng từ ý tưởng đến bằng chứng edge

Owner hỏi06/11 cách làm lần sau nhanh/chính xác hơn và liệu test liên tục hoặc
rules thắng mọi thị trường có chứng minh edge không. Cách tổ chức dùng lại các
owner hiện có, không tạo catalogue/score/ledger riêng:

| Tài sản dùng lại | Phần riêng của mỗi giả thuyết / ranh giới |
|---|---|
| Protocol và candidate version | Hypothesis, cơ chế/điều kiện kỳ vọng, phạm vi asset/timeframe/session, entry/exit/sizing, điều gì bác bỏ nó, benchmark/cost/risk và quyết định trước outcome. Đổi logic/threshold/filter là version/trial mới, không sửa bản cũ |
| Engine và bộ đối chứng | Core data/timing/fill/cost/risk/accounting và regressions dùng chung; chỉ thêm rule-specific tests. Đổi asset/order/cost semantics chưa được hỗ trợ phải kiểm lại đúng boundary, không mặc định core dùng được mọi nơi |
| Dữ liệu/preparation/cache | Reuse raw/quality/warmup/tick cache và completed artifacts khi identity/source/runtime bindings khớp; không dùng cache state cũ cho rules mới hoặc hạ checks để hit cache |
| Dossier và lịch sử thử | Native task/protocol giữ cả thất bại/abandoned variants và quan hệ version; dossier lưu metrics/gaps/quyết định. Tra bằng chứng cũ trước run; chưa có queryable catalogue đầy đủ, không tuyên bố tự động tránh mọi nghiên cứu trùng |
| Hậu kiểm kỹ thuật | Root cause và regression ở code/tests; benchmark/giới hạn ở receipt; workflow delta ở runbook. Mỗi run học cách làm đúng/nhanh hơn, không tự tuning candidate theo vài lệnh lỗ |

Thẻ hypothesis là nội dung trong protocol/dossier hiện có, chưa phải schema/tool
tự động mới. Độ tin cậy đến từ test đúng câu hỏi và đối chứng độc lập; tốc độ đến
từ reuse dữ liệu/core/kết quả và chỉ chạy phần bị thay đổi, không từ việc bỏ gates.

### Nhật ký quyết định để kiểm lại việc tối ưu và chọn chiến lược

Owner nhắc08/11: log phải cho phép người/agent sau đánh giá **đổi có đúng
không**, không chỉ biết process đã chạy. Ghi trong protocol/results/engineering
review của chính study và link từ catalogue/index; không tạo ledger/UI khác.

| Phần phải truy ngược được | Nội dung tối thiểu |
|---|---|
|Quyết định và lý do|ID/version, ngày, lỗi/câu hỏi kích hoạt, giả thuyết và kỳ vọng trước khi đo; vì sao chọn/đổi/gác, điều gì sẽ bác bỏ quyết định|
|Baseline → thay đổi|Parent candidate/code/data/cost/risk/clock và source pins; phân biệt sửa lỗi/đổi data semantics/đổi strategy/tối ưu cùng semantics. Đổi rules hoặc assumptions kinh tế cần protocol/version mới trước outcome|
|Thực thi thật|Run/attempt/command, environment/concurrency/cache state, input exposure, logs/source snapshots; giữ cả fail/cancel/abandoned và lý do retry/reuse|
|Kết quả và kiểm lại|Trước/sau cùng scope, timings đo thật hoặc unknown, metric/check/parity và remaining gaps; giảm thời gian nhờ bớt phạm vi không gọi là speedup giữ nguyên độ đúng|
|Quyết định sau bằng chứng|Giữ/reject/inconclusive/superseded và lý do; impacted books cần kiểm lại, rollback/source locator và bước tiếp. Không xóa kết quả âm hoặc sửa bản freeze để phù hợp kết quả|

Hash/commit giúp truy vết, không tự chứng minh quyết định đúng. Nếu chỉ sửa
report thì không rerun numerical job; nếu input/rules đổi làm thay state, không
chỉ xóa vài trade rồi sửa tổng PnL. Một reviewer cùng agent phải được ghi đúng
phạm vi; không tự gắn independent sign-off. Khi thiếu bằng chứng về parity,
correctness hoặc economic edge, giữ gap và ghi cách giải quyết cụ thể.

### Edge không phải “chạy thử đến khi có lời”

Edge là lợi thế kỳ vọng sau chi phí trong một phạm vi và điều kiện cụ thể,
không phải lệnh nào cũng thắng hoặc lợi nhuận chắc chắn tương lai. Ví dụ giả định:
1R=25USD;100lệnh có40lệnh lời50USD và60lệnh lỗ25USD, tổng trước phí500USD;
tổng phí200USD thì còn300USD, trung bình3USD/lệnh trong mẫu. Số này là mô tả
mẫu giả định, chưa chứng minh expectation tương lai, drawdown hoặc khả năng pass.

Chuỗi evidence cần có: cơ chế hợp lý được nêu trước → implementation/data đúng
→ net outcome so baseline/risk với uncertainty rõ → giữ rules trên dữ liệu không
dùng để chọn/sửa → cost/parameter/regime robustness phù hợp → forward/reconciliation.
Đếm cả trials thất bại; sample/dependence và selection ảnh hưởng độ tin cậy. Không
có một số trades, Sharpe hoặc test-pass count chung bảo đảm edge. Nếu uncertainty
còn lớn, verdict là inconclusive; không gắn0lợi thế hoặc confidence giả chính xác.

Lặp lại cùng data/rules hữu ích cho software regression nhưng không thêm một mẫu
kinh tế độc lập. Sửa theo kết quả validation làm window đó trở thành dữ liệu đã
dùng trong lựa chọn; giữ lịch sử, không tiếp tục gọi nó unseen. New holdout cần
protocol/authority trước outcome, không liên tục đốt holdout để chọn bản đẹp.

Không yêu cầu mọi strategy thắng mọi asset/regime. Scope và điều kiện bật/tắt
phải định nghĩa causal trước outcome; rules cố định có thể phản ứng theo volatility/
trend đã quan sát, khác tự đổi rules sau khi thấy thua. Không chọn lại riêng các
năm/thị trường có lãi rồi gọi đó là robustness. Edge và prop fit là hai cửa riêng:
expectancy dương vẫn có thể breach, quá chậm hoặc không phù hợp reward/fee economics.

Căn cứ kiểm06/11: [Arnott/Harvey/Markowitz](https://people.duke.edu/~charvey/Research/Published_Papers/P138_A_backtesting_protocol.pdf)
về hypothesis/selection/robustness; [PBO](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf)
và [DSR](https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf) về trials và
uncertainty. Đây là synthesis phương pháp, không statistical qualification cho
5candidate hiện tại; gaps và tiêu chí bài đã freeze giữ ở framework/receipt.

## Risk và concurrency

Trước ưu tiên candidate cho prop, dùng
[time-fit research](../../planning/research/PROP-FIRM-FIT-20261102.md#thời-gian-challenge-và-độ-phù-hợp-chiến-lược--kiểm-lại-05112026)
để pin deadline/activation/inactivity, minimum trading/profitable days, hold/news,
phase reset và payout riêng theo program/version. Đăng ký horizons kinh tế và
time-to-target trước outcome; báo chưa đạt trong observation hoặc unknown khi
thiếu coverage, không ngoại suy tuyến tính/tăng lot/thêm lệnh cho đủ ngày.
Native `prop_session.py` sở hữu lifecycle simulation. Delta06/11: registered
H4 studies có `prop_profile` đã nối tick-risk, native target/day/breach và actual
phase-account reset trong declared subset; daily guard reset Europe/Prague.
Thiếu inactivity/eligibility/reward/firm-specific exceptions giữ unknown;
không lấy PnL hoặc internal budgets làm chứng nhận hai phase/time-to-payout.
Horizon-only studies cũ không có prop profile giữ scope cũ. [Execution 2023](../../planning/research/TIME-FIT-EXECUTION-20261106.md)
giữ source/input/cost/risk đã pin của bài 3/6/12 tháng. Một annual replay/scenario
ghi ba horizon causal vào `<scenario>-horizons.json`; files được seal và kiểm
trong dossier/reuse. `forex_time_fit.py --batch <complete-batch> --output <new.json>`
đối soát account state và last-quote age; không force-close hoặc giả phase reset.

Source audit05/11: Trader `api-rust/src/automation_grants.rs::create_grant` khóa
workspace/server/login, chặn execution owner trùng; transaction giữ attempts/
reservations, unknown không release. Research/observation có thể song song;
nhiều strategy cùng account phải qua cùng owner/budget, không nhân grants.
Đây là source-confirmed boundary, không là portfolio allocator/correlation
model hoặc runtime acceptance hôm nay. Không thêm engine risk cạnh tranh.

## Opt-in index M1 development lane

`index_noise_study.py` là entry point nghiên cứu cho
[US500noise14 recipe](../../planning/research/US500-NOISE-STUDY-20261108.md)
và orchestration dùng chung của các index policy wrappers,
không nới EURUSD-only `ForexPilotSnapshot`. Nó reuse `InstrumentSpec`,
`CostModel`, `size_for_market_stop`, `calculate_round_trip_cost` và
`protective_exit_for_bar`; không là engine native index hoặc prop certifier.

Explicit inputs: `--source-root <foundation_v2> --data-root <sealed-year-dir>
--calendar <nyse-year.json> --protocol <frozen.md> --output <new-attempt-dir>`.
CLI hỗ trợ frozen calendars2013–2024, chặn2025+ trước đọc input. Protocol và
consumption/gates vẫn giới hạn exact years được dùng; CLI support không tự là
quyền đọc mọi năm. Không tự download hoặc gọi broker.
`sealed_m1_review.py` kiểm quarter-side seals/schema/calendar/gaps;
native legacy view được ghi `source_presence_verified:false`, chỉ có coverage
timestamp sau decode. Study CLI hiện yêu cầu source-only proof; không nhận
label riêng trên manifest hoặc dùng native decoder padding làm quote nguồn.
Tạo view mới bằng `explicit_m1_view.py --parent <sealed-old-year> --calendar
<frozen-calendar> --protocol <registered-correction> --output <new-view>`.
Tool chỉ dùng local raw cache đã pin, giữ giá nến nguồn và journal unpaired,
không network fallback/fill/gaprepair. Source-proof/reader đổi thì revalidate
attempt mới, không sửa hashes của old books. [Recipe và phạm vi](../../planning/research/INDEX-EXPLICIT-QUARTERLY-PREFLIGHT-20261108.md).
`review_index_noise.py --run <attempt> --data-root <sealed-year-dir>
--output <new-review.json>` đối soát closed-book arithmetic/quote binding,
không resimulate hoặc certifyedge. Unfunded noise reviewer chặn open/pending
và cross-day carry; funded policy metadata chọn riêng nhánh funding/open-mark
review. Không nhận carry thiếu phí chỉ vì closed-trade cash đã cộng khớp.

Cost scenario phải hiện rõ trong protocol/manifest/result:
- Default `us500-declared-commission05-v1` giữ legacy0,5USD/lot/chiều.
- Opt-in `--cost-scenario ftmo-index-zero-commission-public-20261108` chỉ đổi
  commission0 theo nguồn công bố hiện hành. Không đặt spread/slippage/swap0,
  không xác nhận historical broker geometry/fees hoặc thay current-account spec.
- Sizing và reviewer nhận cùng profile; amount/profile/manifest lệch bị chặn.
  Đổi cost có thể đổi lot nên không hoàn phí trực tiếp vào old PnL. Output mới,
  giữ old trials/seals; [registered review/results](../../planning/research/FTMO-INDEX-COMMISSION-RESULTS-20261108.md).

Output có source/protocol/calendar snapshot, results/data review/manifest;
status `progress.json`/`PROGRESS.md`, `events.jsonl` qua existing bounded event
logger và source-frame failure diagnostics. Không có auto retry hoặc auto
promotion; directory đã tồn tại bị từ chối. Xem
[results/limitations](../../planning/research/US500-NOISE-RESULTS-20261108.md).

## Skill consumers

`paperclip_strategy_skills.py` preview/bundle source và sync qua native API;
mặc định không ghi app. Attach research/qualification cho native lead phù hợp,
không gắn process worker/đổi permission của họ. Không start service hoặc gọi
model chỉ để test instruction. Runtime unavailable thì giữ bundle/receipt,
resume publish qua API, không ghi trực tiếp DB. Xem [operations](OPERATIONS.md).

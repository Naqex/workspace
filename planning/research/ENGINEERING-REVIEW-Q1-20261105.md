# Hậu kiểm kỹ thuật Q1 và vòng cải tiến sau vận hành

Kiểm05/11/2026 theo owner yêu cầu review vượt ra ngoài chiến lược: chất lượng,
vận hành, kỹ thuật, performance và học từ thực thi. [Receipt AI](../checkpoints/ai-integrations-20261031/RECEIPT.md)
giữ run state/acceptance; tài liệu này giữ phân tích và đề xuất, không là ledger
hoặc quyền nâng engine/broker. Dùng lại [observability](../../tooling/ai-engines/OBSERVABILITY.md),
[strategy workflow](../../tooling/ai-engines/STRATEGY-WORKFLOW.md) và
[skill maintenance](../../docs/development/SKILL-MAINTENANCE.md).

## Bằng chứng thực tế

Product814e1135; supervisor executed8976ba8, stdout-only fixad13b36 sau numeric
completion. Private root:
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/prop-q1-comparison-20261105/`.
Donchian ở attempt2,4candidate còn lại attempt3. Tính phase từ first event theo
event_sequence của events.jsonl và rotation backups, đối chiếu terminal.json.
Đây là một lượt/candidate trên máy6core, không phải benchmark tail/capacity.

| Worker | Tổng giây | Chuẩn bị/xác minh giây | Reference giây | Stress giây | Tỷ trọng scenario |
|---|---:|---:|---:|---:|---:|
| Donchian, chạy riêng | 1165,20 | 71,34 | 541,94 | 551,22 | 93,8% |
| SMA,4worker song song | 1308,75 | 83,12 | 595,14 | 629,48 | 93,6% |
| Z-score | 1238,08 | 81,84 | 561,89 | 593,52 | 93,3% |
| Pullback | 1296,88 | 80,86 | 590,80 | 624,31 | 93,7% |
| UTC range | 1118,58 | 81,33 | 505,34 | 530,86 | 92,6% |

Scenario gồm đọc/parse tick, risk, khớp lệnh/accounting, checkpoint/report;
**chưa có function profile mới sau parser fix để quy phần nào chiếm đa số**.
Parser benchmark100.000tick riêng nhanh1,79× không phải whole-scenario speedup.
Tối ưu riêng chuẩn bị/xác minh có trần tiết kiệm khoảng6–7% của các lượt đã đo,
chưa tính cache-construction/lookup/invalidation cost. Không hứa cache làm toàn
bộ nhanh gấp nhiều lần. Dev CSV hiện được đọc bởi quality scan và hai scenarios;
typed parsed-data reuse chỉ đáng làm khi đo đúng chi phí/correctness.

Reuse5completed jobs:0,704s,35artifact/process identity hashes giữ nguyên,
0numerical worker directories mới. Điều này chỉ áp dụng **đúng workload đã xong**;
đổi strategy/data/cost/source liên quan vẫn cần computation hoặc invalidation.
Máy quan sát khoảng1CPU/67–68MiB mỗi worker;4jobs mới xong trong1309,25s wall.
Không có baseline sequential tương đương để gọi đó là measured4×speedup.

## Review theo từng lát

| Lát | Đã có / gap xác minh | Ưu tiên / đề xuất | Xác nhận có ích |
|---|---|---|---|
| Chất lượng software/harness | Tests nhỏ từng pass nhưng terminal→progress merge thật bị TypeError; đã sửa và9focused tests pass | P0: thêm test mini-batch của queue/handoff/failure/cancel/reuse trước chạy đắt; không thêm research task giả trong UI | Dùng real terminal shape, lỗi không báo completed, job đã xong không chạy lại |
| Profile và numerical correctness | 10scenario accounting/dossier đạt; sample/coverage/historical costs còn thiếu | Giữ golden outputs/trade events/final positions; đổi engine phải parity trên cùng inputs | Timing/quantity/cost/risk/position không thay ngoài contract mới có chủ đích |
| Performance simulation | 92,6–93,8% elapsed trong scenarios, chưa function profile mới | P1: profile một đoạn development đại diện trong scenario; ưu tiên hotspot thật trước cache/framework/Rust rewrite | Chỉ rõ phần CPU/read/validation/write; benchmark before/after cùng outputs |
| Reuse/cache | Completed reuse thật đã nhanh; preparation scan lặp qua candidates | P1: giữ completed reuse; cân nhắc cache typed inputs/quality theo content+reader version+window khi measured benefit đáng kể | Hit/miss/invalidation đều đúng; fresh workload không lấy nhầm result cũ |
| Recovery | JobObject/kill/crash đã kiểm thật; partial checkpoint chưa CLIresume | P1: thiết kế resume tại scenario hoàn tất trước; full mid-scenario chỉ nếu lặp mất nhiều thời gian | Restore candidate/builder/risk/financing/decisions/cursor đủ và khớp uninterrupted run |
| Artifact/attempt binding | Source/protocol/input/spec pin có; result reuse đang phụ thuộc source/version khá rộng | P1: phân biệt numerical-source vs presentation/supervisor changes bằng dependency đã audit, không bỏ mọi drift check | Sửa wording không ép mô phỏng lại; sửa risk/cost/data phải invalidate đúng |
| Quan sát và UX | Phase/ticks/status/terminal có; validation chưa progress count, ETA chưa lưu trong projection; stdout đã gọn | P1: counters/rate-limited validation progress, ETA điều kiện, last-progress tách liveness; Markdown projection lỗi không nên giết numeric worker | Không bịa %/ETA; unknown không tự failed, log có rotation, mất UI không mất result |
| Điều phối/tài nguyên | Probe riêng rồi4workers, finite deadlines; chưa là scheduler theo capacity | Giữ bounded concurrency; dùng baseline đã đủ thay vì probe lại mọi batch nếu environment/workload tương đương | Không oversubscribe, không thêm slot từ cảm giác, CPU/RAM/UI còn dùng được |
| AI/research/report quality | Numerical batch0LLM calls; chưa benchmark chất lượng agent độc lập | P1: tập eval nhỏ từ lỗi thật về reuse/context/report/authority; calibrate bằng reviewer khi cần | Tách numbers đúng, claims đúng scope, nguồn/cutoff và output dễ hiểu; không chỉ check keywords |
| Skills/context/learning | Evidence/maintenance/debug/performance đã có nhưng chưa có owner hậu kiểm đa chiều | Đã thêm engineering-retrospective như protocol dùng lại; dẫn existing skills, không copy toàn bộ | Positive real Q1 walkthrough; negative status/trivial question không full-audit; native delivery kiểm riêng |
| Native integration | Paperclip API cuối lượt connection refused; source skills không đồng nghĩa published | Delivery gap độc lập, sửa khi runtime được vận hành hợp lệ | Native API/readback và loader version; không ghi thẳng DB hoặc tạo UI/task store cạnh tranh |
| Infra/tools | Một máy, existing stdlib/pytest/JobObject đủ cho scope hiện tại | Defer collector/dashboard mới, distributed cluster, background upgrade daemon | Chỉ nhận công cụ mới khi có capability gap và đo thắng maintenance/data-flow cost |

P0/P1 là ưu tiên đề xuất, không claim các improvement chưa triển khai đã xong.
Một review có thể kết luận giữ nguyên; không phải run nào cũng phải sửa code,
tạo skill hoặc nâng dependency. Regressions ưu tiên trước tối ưu throughput.

## Vòng học và cải tiến

`run → evidence → review/triage → fix hoặc giữ nguyên → targeted verification
→ benchmark/parity nếu performance đổi → update code/runbook/skill đúng owner`.

Lưu lỗi thành case hồi quy; cách đã kiểm chứng thành hướng dẫn; fact/version
thành context có nguồn. Giữ incident history ở receipt, không nhồi log/timeline
vào skill. Trigger sau batch đáng kể, lỗi/correction hoặc repeated friction;
không full audit sau mọi command và không tự gọi thêm model mỗi lần kết thúc.
Workflow khi agent làm việc không bảo đảm luôn chạy nền lúc không có agent.

Skill repo [engineering-retrospective](../../.agents/skills/engineering-retrospective/SKILL.md)
điều phối bước review. `fullstack-performance` own đo/benchmark;
`evidence-debugging` own root cause; `evidence-continuity` own evidence;
`ai-environment-maintainer`/skill-creator own thay instruction/tool environment.
Không đổi quyền của bounded workers hoặc nới acceptance để tự ghi improvement.

## Hermes: tính năng upstream và cấu hình trong project

[Hermes skills docs](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills)
ngày05/11 mô tả procedural memory qua skill_manage, memory facts, background
review và write approval. Đây là lưu/cải tiến cách làm bằng knowledge/procedure;
không cần suy rằng model tự huấn luyện weights từ một run.

Source local `tooling/ai-engines/hermes_worker.py` tạo AIAgent chỉ với
naqex_research/memory/session_search, skip_context_files=True và
skip_background_review=True; tool inventory còn qua allowlist.
[Integration guide](../../tooling/ai-engines/hermes.md) giải thích reviewer không
có terminal/files/code/delegation/cron/broker và skills không promote tự động.
Vì vậy không quảng cáo project đã bật native Hermes self-improvement đầy đủ.
Repo skill mới không tự được SDK reviewer/Paperclip catalog nạp. Giữ delivery
gap này thay vì mở quyền skill_manage/terminal chỉ để giống upstream.

## Nguồn và giới hạn best practice

- [Anthropic: Demystifying evals for AI agents](https://www.anthropic.com/research/demystifying-evals-for-ai-agents),
 09/01/2026, đọc05/11: biến lỗi/manual checks thành eval, đọc actual outcome/
 traces và đo quality cùng latency/cost. Áp dụng có chọn lọc; không buộc một
 người có20–50eval hoặc thuê platform trước khi có consumer.
- [Google SRE: Postmortem culture](https://sre.google/workbook/postmortem-culture/),
 đọc05/11: bài học cần action cụ thể/owner/verification để ngăn tái diễn;
 dùng postmortem gọn cho một owner, không chép quy trình tổ chức lớn nguyên bộ.
- [Hermes official skills](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills),
 đọc05/11 và đối chiếu local source: lessons/procedures on-demand, maintenance
 và write gates. Website mới không chứng minh runtime pin đang bật tính năng.

Không thu số liệu doanh nghiệp/cộng đồng để xếp hạng tool, không cài package,
đổi stack, gọi provider/model mới hoặc đọc OOS trong review này. Đây là review
source + actual retained run metadata; không phải audit toàn API/UI/DB/broker.
Refresh khi dependency/runtime/worker contracts đổi hoặc có lượt comparable mới.

## Lát triển khai sau review — 05/11

Owner giao làm tiếp. Đã thêm mini-batch trên scheduler/ThreadPool thực với worker
stub số học: probe→parallel handoff, một job fail giữ job khác đã xong, cancel
không dispatch pending; process-tree ownership vẫn có tests Windows riêng.
Không gọi test này là full broker/product acceptance hoặc research task mới.

Profile có giới hạn200.000tick đầu của developmentQ1 đã consumed, commonwarmup
1.404.696tick. Mẫu có1entry/1closed trade, fixed diagnostic financing6,22/3,14,
không mặc định đó là full-study broker terms. Profiler20,09s: model_copy600.162
calls/~6,32s cumulative; replay/cost/risk cũng có chi phí. Cumulative timers
lồng nhau nên không cộng các dòng thành percentages độc lập. Giữ file.prof và
source bindings; chưa profile mọi phase hoặc fullQ1 sau sửa.

Sửa nhỏ `_PilotGuard._observe`: vẫn tính equity, min và xét daily/overall loss
mỗi quote; chỉ copy frozen risk state khi min/stop history thật sự thay đổi.
Không bỏ một tick/guard hoặc đổi sizing/SL/calendar/risk budget để lấy tốc độ.
Benchmark không profiler, một warmup pair +3sample pairs đảo thứ tự,200.000tick,
full-file SHAcheck và cùng checkpoint/report writes, callback progress no-op:
median **7,812→6,735s**, latency giảm **13,79%**, speedup1,160×. Result và các
checkpoint/decisions/candidate file hashes khớp từng pair. Đây là consumed-prefix
benchmark (giờ cuối có thể partial), không là measured fullQ1/CLI speedup hoặc
qualification của chiến lược. Không chạy lại fullQ1 chỉ để tạo con số nhanh hơn.

Đã thêm `--reuse-scenarios-from` trong pilot và `reuse_scenarios_from` trong
batch config. Completed seal sau result/accounting pin source/input/cost/spec/
protocol/quality và artifact bytes. Source attempt phải dừng; kiểm final snapshot
và accounting, giữ evidence gốc và provenance sang attempt mới. Metadata/code/
cost/input drift, tamper, source active hoặc thiếu seal bị từ chối trước simulation.
CLI vẫn không restore giữa scenario; full source hash còn conservative nên
không auto reuse legacy/no-seal hoặc cross-version source changes.

Smoke riêng bằng CSV **generated fixture**, không market research: ngắt thực
callback ở cost-stress sau khi reference được seal; attempt mới chỉ tính stress.
7files numeric/result/state/decisions/candidate khớp fresh uninterrupted run,
raw failed attempt hashes không đổi. Numeric source khác sourcepin814e1135 của
Q1 gốc nên chỉ dùng bounded equivalence/regressions làm acceptance cho lát này;
không nói Q1 cũ vừa chạy trên code mới.

Private artifacts nằm trong `engineering-profile-20261105/` dưới private Q1 root:
`profile_scenario.py`, `scenario-baseline.prof/.txt`, `profile-binding.json`,
`forex_pilot_risk.baseline.py`, `benchmark_guard.py`, `guard-benchmark.json`,
samples, `scenario_reuse_smoke.py` và `scenario-reuse-smoke/recovery-proof.json`.
Những đề xuất khác trong bảng review vẫn là đề xuất nếu không ghi triển khai ở đây.

## Delta performance Q1/2023 — 05/11, sau câu hỏi vì sao chạy lâu

Owner muốn tăng tốc mà giữ độ đúng. Đây là measurement/recommendation slice,
chưa sửa numerical source, concurrency hoặc frozen registration. Reuse closure
Q1/2023 và profile ngắn trên200.000tick đầu Q1/2022 đã consumed; không chạy lại
cả quý, mở window mới hoặc gọi model/broker. Máy hiện tại i5-9400F,6core/6thread.

| Lát | Số đo / source-confirmed | Kết luận |
|---|---|---|
| Toàn candidate | Donchian1.489,718s; bốn bản còn lại1.549,781–1.683,406s | Khoảng25–28phút/candidate; không phải AI suy nghĩ trong khoảng đó |
| Scheduling | Probe Donchian riêng rồi bốn job song song: tổng phase wall times tương ứng3.173,124s≈52,9phút, chưa overhead/rework | Đây là tổng từ lịch đã quan sát, không phải measured baseline cho scheduler mới. Bài tiếp cân nhắc bounded parity/preflight thay full probe khi workload/environment tương đương; phải đăng ký trước, không sửa bài cũ |
| Validation | Donchian174,703s; parallel jobs361,641–363,984s, chiếm11,7–23,4% total | Repeated quality/warmup có cơ hội reuse. Concurrent phase chậm hơn không tự quy nguyên nhân cho disk/CPU nếu chưa đo resource |
| Parse lặp | Mỗi candidate đọc warmup một lượt, development quality một lượt rồi reference/stress hai lượt; năm candidate tổng175.376.920tick-decodes với các lượt đủ, chưa tính recovery | Shared immutable decoded inputs/quality có tiềm năng; không tự bỏ integrity/ordering/grid/coverage validation hoặc chia sẻ mutable strategy state |
| Profile hiện hành |200.000tick,1entry/1closed,16,721s có profiler; `read_qdm_ticks`5,429s gồm full-file hash2,411s; `_liquidation_pnl`4,148s/148.634calls; `model_copy`2,250s/200.454calls | Nested cumulative times không cộng thành percentages. Prefix có hash overhead không tỷ lệ theo số tick và chỉ1trade, chưa đại diện mọi candidate/fullQ1 |
| Correctness probe | Checkpoint/decisions/candidate JSON khớp byte với prefix baseline đã giữ | Chỉ bounded artifact equivalence; không gọi đó là new full-study acceptance hoặc controlled speedup từ profile cũ sang mới |
| Completed reuse | Bài đã xong được kiểm/reuse5jobs trong0,636s,0numeric workers theo receipt | Giữ reuse, không tính lại để đọc số/viết báo cáo; khác source/data/cost/rules thì phải review/invalidate đúng |

Evidence private:
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/prop-q1-comparison-20261105/engineering-speed-review-20261105/`
giữ copied bounded profiler, `scenario-current.prof/.txt`, `profile-binding.json`,
`speed-review.json` và3prefix artifacts. Closure source là Q1/2023attempt2 đã dẫn
trong receipt. Không dùng20,09s profile cũ so16,72s mới làm speedup A/B: thời điểm,
cache/I/O và source khác. Không mở numeric worker nào còn chạy sau profile này.

### Thứ tự tối ưu đề xuất cho bài kế tiếp

1. **Giảm việc lặp và chờ:** giữ completed/scenario reuse; thử scheduling không
   full probe riêng khi baseline đủ; quality/H4 warmup/decoded-input reuse theo
   content+schema+reader/runtime+window bindings. Cache cần kiểm corruption,
   invalidation, một writer và cùng financial semantics. Chi phí tạo/cache miss
   phải tính riêng; chưa có speedup đo được cho các đề xuất này.
2. **Tối ưu hot loop nhỏ trước:** thử reuse floating PnL cho đúng cùng quote và
   position không đổi trong một transition; giảm state allocation khi tương đương.
   Giữ kiểm mọi tick, rounding/Decimal, spread, financing, event ordering và risk.
   Golden outputs gồm fills/quantities/costs/stops/open positions, không chỉ PnL
   cuối. Benchmark paired cùng workload/cache state rồi mới nhận thay đổi.
3. **Native kernel nếu vẫn cần:** isolate phần parse/replay/valuation đo được
   sang Rust, giữ Python điều phối/research; không rewrite cả hệ thống hay chuyển
   Decimal→float âm thầm. Cần parity về tiền/causal timing/risk/recovery và lợi ích
   end-to-end đủ bù build/maintenance. Chưa có native-kernel prototype/benchmark.

Không tăng mù lên10workers trên6cores, dùng GPU cho loop tuần tự có state, bỏ
tick/đổi sangM1 để gọi cùng bài nhanh hơn, hoặc lấy cost-stress bằng cách trừ
tiền từ reference trades: phí/slippage có thể đổi fills/risk/trade path. Screening
thô có thể là study khác được đăng ký rõ, không thay final tick-level evidence.
Mục tiêu thực tế là giảm thời gian workload mới và giữ reuse cho workload cũ;
chưa có căn cứ hứa một quý đầy đủ chạy trong vài giây hoặc một hệ số tối đa.

## Triển khai tăng tốc có giới hạn — 05/11, owner giao tiếp task

Trader **60fac3ed** reuse floating valuation theo đúng Bid/Ask/side/quantity/
original-quantity/entry prices trong một execution window. Costs/instrument cố
định trong window; không cache risk decision, không bỏ tick hoặc đổi Decimal/
rounding. Giữ lời/lỗ realized và cost breakdown theo đường cũ. Regression mới
BUY/SELL có giá lặp, nhiều quote cùngms, breach rồi close đúng sequence.

Trader **3137f654** thêm explicit prepared inspection cache, CLI chuẩn bị và
opt-in pilot loader. Cache chỉ chứa quality/H4, không strategy state hoặc toàn
tick đã decode. Key bind rawSHA/window/helper-reader-tick sources/runtime; mỗi
hit hash lại raw input và kiểm payload checksum. Cache miss/corrupt/drift fail
rõ, không âm thầm rebuild ở worker. Một preparer có lockPID, publish qua temp
rename; orphan lock/temp sau crash cần đối soát trước xử lý. Manifest ghi cache
locator/digest/helper source. Không biến checksum thành proof data authenticity.

Workspace controller thêm `--parallel-start`, pin trong batch manifest và từ
chối đổi binding trên attempt đã có. Default full-candidate probe giữ nguyên;
study mới cho phép option có thể dispatch bounded jobs ngay, mỗi worker vẫn
full preflight/accounting. Barrier test chứng minh hai job bắt đầu trước khi
job nào xong và vẫn giữ output good khi job khác fail. Config job forward
`inspection_cache_dir`; chuẩn bị xong trước parallel dispatch. Chưa đo end-to-end
full-quarter batch với scheduler mới, không hứa53phút sẽ giảm còn một ETA cụ thể.

### Số đo và độ đúng

| Đo trên cùng inputs | Baseline median | Candidate median | Kết luận đúng scope |
|---|---:|---:|---|
|200.000tick consumed, gồm CSV parse/hash và scenario writes|8,331s|8,044s|Giảm3,44%;3sample pairs sau1warmup pair, có dao động I/O/load; chưa stable tail/fullQ1 gain|
|Cùng200.000tick đã parse chung vào memory, replay/guards/writes|8,734s|6,815s|Giảm21,97%,1,282× ở kernel fixture; không gồm parse/quality và không là whole-study speedup|
|Quality/H4 warmup12/2021,1.404.696tick, hit vẫn hash toàn raw|22,471s|0,200s|112,43× cho **inspection cache hit**; miss ban đầu22,662s, không là simulation speedup|

Ba benchmark đều alternating3measured pairs sau1warmup pair. Hai valuation
benchmarks khớp result cùng3artifact SHA từng lượt. Quality và DecimalH4bars
khớp hoàn toàn ở mọi cached/fresh pair. Các benchmark riêng không chạy đồng
thời với nhau; không suy hệ số kết hợp bằng cách nhân các dòng. Prefix chỉ có
1entry/1closed trade, financing diagnostic cố định; không chứng minh mọi strategy/
regime/cost hoặc fullQ1 mới. Cache miss/setup cần tính khi đánh giá bài mới.

Private artifacts:
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/prop-q1-comparison-20261105/engineering-valuation-cache-20261105/`
giữ baseline source, paired scripts/samples/benchmarkJSON, outputs; `parsed-kernel/`
giữ replay-only comparison và `inspection/` giữ cache/quality comparison.
Không đọc window mới, không numerical full-quarter rerun hoặc model/broker calls.

Focused verification:69tests/34subtests cho tick execution/service, pilot risk/
entry/financing;12tests/12subtests cho scenario reuse/registration;10tests cho
inspection/cache/preflight/CLI;15controller tests. Tổng106tests/46subtests trong
scope, không full-product/broker acceptance. Cache tests gồm exact restore, raw
change, checksum corruption, runtime/window/source drift, writer lock, invalid
input không publish, CLI hai roles, runner provenance và no simulation preflight.
Controller giữ cancel/timeout/Windows lock/reuse checks; không nới gates để lấy tốc độ.

Lát này hoàn tất source+focused parity/benchmark. Decoded-tick sharing/nativeRust
kernel vẫn chưa triển khai; hoãn tới khi bài tiếp thực sự cần và có representative
profile. Study frozen/source pins cũ không sửa; protocol mới phải bind source/
options hiện hành và time-fit3/6/12tháng trước mở dữ liệu chưa dùng.

## Tối ưu tiếp parser và risk counters — 05/11

Owner giao tối ưu thêm và cập nhật bảng thời gian. Trader **d8e5199d** đổi hai
hotspots, không thêm package/native kernel/service hoặc mở dữ liệu mới:

- CSV reader dùng fixed header/index thay dictionary từng row. Cache duy nhất
  UTC epoch của giây gần nhất, vẫn kiểm grammar/date/milliseconds/order/grid và
  quote model mỗi record. Giữ blank-line ordinal, BOM/CRLF, quoted fields, legacy
  accepted timestamp grammar và Decimal text/precision; không sort/dedup/downsample.
- `_PilotGuard` giữ last-tick/count trong instance riêng của atomic window,
  check ordering theo quote gần nhất và kiểm risk mỗi tick như cũ. Chỉ ghi hai
  field đó vào immutable checkpoint sau khi toàn window hợp lệ; risk latch/min/
  entry/exit quyết định ngay trong loop. Invalid final quote không publish partial
  counters; snapshot schema/recovery boundary và financing semantics giữ nguyên.

Private evidence:
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/prop-q1-comparison-20261105/engineering-parser-20261105/`.
Baseline source, `benchmark_parser.py`, `benchmark.json`, `progress.json` giữ
parser comparison; `combined/` giữ paired scenario với cả old-parser/old-guard
và new-parser/new-guard; `planning-estimate.json` giữ công thức/assumptions của ETA.
Các benchmark hữu hạn có PID/status/sample log, chạy lần lượt; đều đã kết thúc.

| Đo thực tế trên cùng consumed inputs | Trước | Sau | Kết luận |
|---|---:|---:|---|
| Parser500.000tick, gồm full rawSHA mỗi sample |7,045s|6,365s|Giảm9,65%; kiểm riêng500kquote khớp time/sequence/Decimal text hoàn toàn |
| Parser riêng trong scenario200k, risk engine cùng bản |10,338s|9,267s|Giảm10,36% trong benchmark riêng, không so absolute time với lượt khác |
| Cả parser+counters, scenario200k |7,007s|5,617s|Giảm19,84%,1,247×; CPU median6,219→4,953s; output/result và3artifact hashes khớp mọi pair |

Mỗi comparison có1warmup pair và3measured pairs đảo thứ tự, concurrency1;
scenario giữ CSV/hash/checkpoint writes và common warmup đã kiểm. Prefix có
1entry/1closed trade, fixed diagnostic financing, không representative toàn
candidate/regime/quý. Chạy benchmark parser riêng xong mới đổi risk code, rồi
chạy combined; không trộn source giữa các sample. Baseline/current source hashes
trong report khớp file đã dùng. Không nhân các hệ số riêng để claim tổng speedup.

Focused verification mới:50tests/58subtests cho parser/runner/risk/entry/financing/
scenario reuse;31tests/15subtests cho forward/restart/CLI/preflight/registration/
inspection cache. Tổng81tests/73subtests của hai nhóm không trùng, không cộng
19parser/cache tests đã chạy trước đó vào count. Không lặp toàn product suite
hoặc fullQ1. Cache cũ bind reader-source trước thay đổi phải prepare entry mới;
không sửa checksum/registration/source pins để ép reuse qua source drift.

### Bảng thời gian kế hoạch cập nhật

| Cấu hình5candidate×2costs, workloadQ1 tương đương | Thời gian | Mức bằng chứng |
|---|---:|---|
| Cũ: full probe riêng rồi4worker |≈53phút|Tổng phase durations cũ, chưa overhead/sự cố/rework |
| Đợt tối ưu trước, chưa có inspection cache |30–40phút|Ước tính cũ, nay thay bằng khoảng dưới |
| Hiện tại: chuẩn bị cache mới rồi parallel-start |25–35phút|Ước tính, chưa chạy full batch |
| Hiện tại: inspection cache đúng source đã sẵn, parallel-start |20–30phút|Ước tính, chưa chạy full batch |

Cơ sở estimate: khoảng warm-cache25–35phút đã nêu trước ×0,8016 từ bounded
combined comparison =20,0–28,1phút, làm tròn20–30 với margin; cold-cache thêm
preparation/host-load margin thành25–35. Đây là **estimate dựa trên estimate**,
không performance forecast đã hiệu chỉnh hoặc acceptance fullQ1. Cold setup
phải tính riêng và exact new-study source/options phải được đăng ký. Cùng máy,
data volume/concurrency tương đương, không sự cố/rework; CPU/disk load, trade
path và workload dài có thể làm ngoài khoảng. So với mốc53, hai khoảng tương
ứng giảm khoảng34–53%/43–62%, đều là ước tính.

Dừng lát tối ưu này sau measured gain/parity. Decoded columnar tick sharing và
Rust/GPU/cluster chưa triển khai; chỉ xét khi bài mới có measured bottleneck
đáng maintenance. Không chạy lại một quý chỉ để tạo ETA hoặc trì hoãn phần
challenge lifecycle3/6/12tháng vì tiếp tục micro-optimize.

## Nút thắt tổng thể và lát tích hợp — 05/11

### Xếp hạng theo bằng chứng hiện có

| Hạng | Nút thắt | Số đo / tác động | Quyết định |
|---:|---|---|---|
| 1 | Replay + risk/accounting từng tick, tạo Pydantic/event/cost objects | Profile integrated: `advance_tick_execution`4,563s/200k; `_liquidation_pnl`1,955s; cost function1,833s | Đã giảm counter state-copy và quote valuation lặp; vẫn giữ kiểm từng tick. Rust/typed kernel chỉ xét sau benchmark đại diện |
| 2 | Decode/convert/reconstruct quote lặp cho mỗi worker/scenario | Prepared Parquet dictionary cache đọc500k median≈2,962s so CSV≈3,688s (1,245×), exact tick parity | Đã thêm lossless prepared tick cache + source/hash/schema/order/grid guards |
| 3 | Quality/H4 inspection lặp | Warmup1.404.696tick22,471s fresh→0,200s hit | Đã có inspection cache và shared preparation |
| 4 | Probe tuần tự/chờ trước khi mở worker | Batch cũ probe→4 worker, khoảng53phút theo phase durations | Đã có `--parallel-start`; bài mới pin option, attempt cũ giữ nguyên |
| 5 | Rework sau lỗi/projection/partial attempt | Từng có progress read làm cancel; recovery Donchian reuse0,636s | Giữ sealed scenario reuse và preparation fail-closed |
| 6 | Quan sát không đủ để biết đang chậm ở đâu | Trước chỉ stage/tick; CPU/phase coverage thiếu | Receipt/progress ghi phase wall/CPU, worker CPU coverage và input-preparation progress |

### Lát tích hợp đã làm

Trader thêm `forex_qdm_ticks.py` (Parquet lossless) và
`forex_input_preparation.py` (một recipe cho quality/H4/ticks), CLI
`--include-ticks`, pilot `--tick-cache-dir`, batch `--prepare-inputs` và
`prepared_inputs_dir`. Cache bind raw/window/runtime/decoder; mỗi read rehash
raw+cache rồi validate schema/count/coverage/order/grid. One preparer lock/publish
atomic; temp/lock sau crash cần reconcile PID trước dọn.

Controller deduplicates preparation theo `(kind, cache, input, hash, window)`,
ghi `input-preparation.json`, rate-limited progress và không dispatch numerical
worker sau preparation CANCEL/deadline. Projection errors được ghi mà không
invalidate cache hợp lệ. Completed jobs skip preparation; bundle và individual
cache fields không được trộn.

Smoke Windows trên generated fixture:2 candidates×2 scenarios,3 shared entries,
prepared/raw numeric artifacts byte-identical, reuse0 numeric dispatch. Smoke
wall1,41s, CPU coverage2/2,0,75s; không market evidence. Integrated prefix:
old4,061s→new3,490s, **giảm14,06%**, CPU4,031→3,484s, exact parity3 pairs.
Preparation500k4,664s, Parquet≈2,63MB. Đây là bounded prefix, không full Q1.

Focused tests mới/liên quan: **72 passed,42 subtests** ở lượt cuối; không broker,
model, holdout hay market-window mới. PyArrow đã có sẵn, không cài dependency/
service. Official Arrow docs đã kiểm ParquetWriter/row groups/dictionary/
iter_batches; dùng `use_threads=False` để giữ thứ tự kiểm rõ ràng.

### Hướng tiếp theo

Integrated profile vẫn cho thấy replay/risk/cost/validation chiếm phần lớn, không
phải Parquet I/O. Giữ prepared cache như tính năng vận hành; chưa rewrite kernel,
thêm GPU/cluster hay tăng worker mù. Chạy study mới với `--prepare-inputs
--parallel-start`, lấy số đo full batch thật, rồi mới cân nhắc Rust. Ưu tiên kế
tiếp vẫn là challenge lifecycle/time-fit3/6/12tháng.

## Lõi valuation sau yêu cầu tối ưu thêm — 05/11

Profile cho thấy floating gọi `_liquidation_pnl`/`calculate_round_trip_cost`
và dựng cost dictionary nhiều lần dù floating risk check chỉ cần net P/L. Trader
đã thêm `_liquidation_net_account` và dùng nó riêng cho floating path. Hàm nhận
InstrumentSpec/CostModel đã validate, giữ Decimal/rounding/partial quantity,
spread Bid/Ask, commission, slippage và financing; protective close vẫn gọi
`_liquidation_pnl` đầy đủ để không đổi event breakdown/accounting.

Parity tests cover BUY/SELL, partial positions, fee minimum và rounding; core
suite mới nhất **96 passed,52 subtests**. Chưa gán speedup full study: paired
scenario harness sau thay đổi chưa tạo được A/B result đáng tin, nên không báo
phần trăm từ microbenchmark. Giữ fast path vì parity/code scope rõ, đo lại bằng
runner batch chính thức ở study mới. Nếu còn nút thắt, Rust kernel chỉ xét sau
full-batch profile và golden artifact parity.

## Full-batch benchmark chính thức và golden event parity — 06/11

Đã chạy bài benchmark đã đăng ký trên source Trader `0d831471`, với cùng
registration `eurusd-h4-q12023-historical-robustness-v1`, warmup 11–12/2022 và
development Q1/2023. Lượt chạy dùng `--prepare-inputs --parallel-start`, cache
prepared đã kiểm hash/schema/order/grid, 4 worker tối đa trên máy hiện tại và
không gọi model/broker/holdout.

| Đo | Kết quả | Ý nghĩa |
|---|---:|---|
| Ứng viên × scenario | 5 × 2 = 10 | Full batch của registration, không phải 10 thử nghiệm độc lập |
| Tick mỗi worker | 9.038.771 | Đủ declared development window |
| Worker | 5/5 `completed_verified` | Accounting, bindings và artifact đều đạt |
| Wall time | 1.800,48 giây (30,0 phút) | Có 4 worker song song; ứng viên thứ 5 chạy sau khi slot trống |
| CPU worker mới | 4.021,98 giây | Đo diagnostic, không phải quota/token |
| Cache preparation | Đã hoàn tất trước dispatch | Không tính nhầm cache hit là simulation speedup |

So với attempt cũ, không dùng wall time để claim speedup trực tiếp vì attempt cũ
đã reuse Donchian và không ghi phase timing tương đương. Per-worker current
elapsed khoảng 12,7–14,6 phút; số này là mô tả workload hiện tại, không phải
capacity forecast cho mọi cửa sổ.

Golden là artifact Q1/2023 đã freeze ở attempt-2 (Donchian lấy locator attempt-1
do reuse). Comparator mới tại
`tooling/ai-engines/golden_event_parity.py` tách ba lớp:

| Lớp | Kết quả |
|---|---|
| Kết quả/decision/candidate semantic | PASS 5/5 |
| Event ledger: sequence, kind, cursor, fills, risk, accounting | PASS 10/10 |
| Byte/hash tuyệt đối | FAIL có chủ ý |

Byte/hash khác chỉ ở scale của Decimal string (`-0.30` và `-0.3`, hoặc
`9993.00` và `9993.0`); comparator xác nhận numeric semantic equality và không có
khác biệt key/value nào ngoài representation. Đây là **semantic golden event
parity đạt**, còn **byte parity chưa đạt**; không sửa golden cũ hoặc làm tròn
ngầm để che sai lệch. Report đầy đủ nằm tại
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/prop-q12023-robustness-20261105/official-benchmark-20261106/golden-parity-v2.json`.

Benchmark này xác nhận tối ưu hiện tại không đổi đường đi tài chính trên fixture
đã đăng ký. Nó chưa xác nhận OOS, edge, historical broker cost, intrabar đầy đủ,
prop pass hay live readiness. Bước tiếp theo hợp lý là giữ parity receipt này,
đọc time-fit 3/6/12 tháng và chỉ mở một cửa sổ mới đã đăng ký; chưa cần Rust/GPU
rewrite chỉ vì full batch đã chạy xong.

### Hậu kiểm nút thắt sau full batch

Receipt mới cho thấy nút thắt đã chuyển rõ về simulation loop:

| Nhóm | Đo được trên 5 worker | Kết luận |
|---|---:|---|
| Reference + cost-stress | 99,41–99,50% wall/worker | Đây là chi phí replay/risk/accounting từng tick |
| Manifest + warmup + development validation | 0,50–0,59% | Prepared cache đã loại phần lặp; không đáng tối ưu tiếp trước |
| CPU/wall của worker | 96,76–98,52% | Workload hiện tại CPU-bound, không phải chờ I/O chính |
| Scenario cost-stress | 352–433 giây | Không thể gộp mù với reference vì cost có thể đổi fill/risk path |
| Scheduling | 4 worker đầu song song, worker thứ 5 nối đuôi | Tăng lên 5 chỉ là giả thuyết; chưa đủ số đo để đổi mặc định |

Vì vậy không thêm Parquet/cache/UI/collector ở lát này. Nút thắt đáng nghiên cứu
tiếp là allocation và Decimal/Pydantic/event work trong replay loop; profile cũ đã
chỉ đúng hướng nhưng chưa đủ để chọn Rust kernel. Lát tiếp theo nên là một profile
đại diện có golden output, rồi benchmark A/B bounded trước khi đụng numerical
kernel. Nếu không đạt lợi ích end-to-end đủ lớn, giữ Python path và chuyển sang
time-fit/qualification 3–6–12 tháng.

Profile bounded tiếp theo đã được chuẩn bị nhưng hủy trước khi có sample vì máy
local là máy tương tác của owner (game/media). Thư mục attempt được đánh dấu
`cancelled_by_operator_constraint`; không dùng partial file để claim hotspot mới.
Lần profile sau phải chạy low-priority trong cửa sổ idle, output mới và giữ
golden/parity checks.

Profile bounded đã chạy lại ở Normal priority theo yêu cầu owner, source
`669c9093`, 200.000 tick Q1/2023, mất **7,63 giây**. Đây là prefix chẩn đoán,
không phải full-study benchmark; output chỉ có checkpoint/candidate partial và
không được dùng làm kết quả chiến lược.

| Hotspot trong profile | Cumulative time | Cách hiểu |
|---|---:|---|
| `read_qdm_ticks` + raw hash | 3,82 giây | Parser/hash vẫn đáng kể trên prefix |
| `hourly_quotes` | 4,12 giây | Xây quote/H4 từ tick |
| `advance_tick_execution` | 3,27 giây | Tick replay/state transition |
| Pydantic validation | 1,02 giây | Object validation/allocations |
| `_liquidation_net_account` | 0,30 giây | Fast floating valuation hiện không còn hotspot chính |

Cumulative timers lồng nhau nên không cộng thành phần trăm. Lát tối ưu tiếp có
thể là giảm parse/quote allocation hoặc typed kernel Rust, nhưng phải benchmark
A/B cùng input và golden event parity trước khi đổi numerical path. GPU chưa có
backend trong source; không thêm CUDA chỉ từ profile này.

### A/B thử giảm allocation trong `hourly_quotes` — 06/11

Đã thử một candidate tính OHLC trong một vòng thay vì tạo thêm list `mids`, giữ
nguyên tick list, Decimal và thứ tự event. Trên cùng 200.000 tick, 1 warmup + 3
sample mỗi nhánh:

| Nhánh | Median |
|---|---:|
| Baseline | 3,940 giây |
| Candidate | 4,018 giây |

Checkpoint/JSON artifact parity đạt, nhưng candidate chậm hơn khoảng 1,96% nên
đã loại và không sửa source. Evidence prototype và report giữ tại
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/prop-q12023-robustness-20261106/ab-hourly-quotes-20261106/`.

### Đối chiếu research cộng đồng/agent — 05/11

Các nguồn được dùng để quyết định lát này:

- [GlowBack](https://github.com/LatencyTDH/GlowBack): Rust engine, Python bindings,
  event-driven simulation và Arrow/Parquet storage. Đây là kiến trúc tham khảo,
  không phải lý do tự thay Trader.
- [Bullet](https://github.com/No-Trade-No-Life/Bullet): deterministic event-driven
  Rust research/execution với Parquet runner. Củng cố hướng tách data layer/kernel
  sau khi có parity, không chứng minh mọi workload của mình hợp bar/vector.
- [Reddit: vectorized vs event-driven](https://www.reddit.com/r/algotrading/comments/1x8tw1t/eventdriven_vs_vectorized_backtesting_which/)
  và [forward parity](https://www.reddit.com/r/algotrading/comments/1q6vyxr/vectorized_vs_event_driven_backtesting/): cộng đồng thường dùng
  vectorized cho screening, event-driven làm nguồn sự thật vì path-dependence,
  stop/fill order và lookahead. Đây là kinh nghiệm cộng đồng, không phải proof
  hiệu suất hay chuẩn compliance.
- [OpenAI Codex performance guidance](https://cdn.openai.com/pdf/6a2631dc-783e-479b-b1a4-af0cfbd38630/how-openai-uses-codex.pdf): dùng profile,
  benchmark và kiểm reliability khi tối ưu; áp dụng như quy trình, không coi
  Codex/model identity là nguyên nhân tạo speedup.

Quyết định áp dụng: giữ event-driven tick replay làm oracle; chuẩn hóa input bằng
Parquet có hash; tối ưu hot loop nhỏ với golden parity; chỉ làm Rust kernel khi
full-batch profile cho thấy lợi ích đủ lớn. Không vectorize path-dependent fill/risk
để thay oracle, không tin throughput từ repo khác, và không dùng agent tự đánh giá
“nhanh hơn” khi chưa có cùng fixture/output.

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

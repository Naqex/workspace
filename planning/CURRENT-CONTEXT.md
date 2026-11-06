# Current context — Naqex Workspace

## Research kế thừa — 05/11/2026

Điểm định hướng 06/11 sau câu hỏi owner về tổng thể: mục tiêu vẫn là tìm chiến
lược Forex tự động có lợi thế sau chi phí, phù hợp FTMO 2-Step Swing trước,
tiếp cận vốn prop với rủi ro kiểm soát. Hệ thống đã đủ chạy research offline;
không đồng nghĩa toàn sản phẩm/live hoàn chỉnh. Đang screening 5 bộ quy tắc
cố định, chưa có winner hoặc clean-OOS/prop qualification. Annual batch 2023
chỉ thêm observations 3/6/12 tháng; **chưa mô phỏng đủ phase1→reset→phase2**.
Owner đồng ý hướng điều phối 06/11: để batch đã launch hoàn tất; ưu tiên
quyết định giữ/loại/inconclusive và nối đánh giá prop còn thiếu. Không mở thêm
nhánh GPU/Rust/benchmark nếu không có lỗi hoặc bottleneck chặn bước đó. Đây là
hướng giữ trọng tâm đã được owner xác nhận; các quyền broker/holdout giữ riêng.

Delta06/11 sau annual slowdown: attempt `execution-v1` đã dừng có kiểm soát
07:49VN, 0/5job và0scenario hoàn tất; không có annual result được công nhận.
Đã xác nhận toàn bộ process owner/worker dừng rồi fast-forward main Trader lên
`86eade80`; bốn file khớp byte với worktree đã kiểm108tests. **Chưa có annual
attempt mới chạy.** Lượt mới phải có source-bound registration/config/deadline;
không sửa frozen registration cũ hoặc giả resume partial. Receipt AI giữ evidence,
benchmark/parity, worktree locator và cách tiếp tục an toàn. Khung
[sàng lọc cập nhật](research/STRATEGY-VALIDATION-FRAMEWORK-20261105.md#sàng-lọc-ứng-viên-tiềm-năng--đối-chiếu-primary-sources-0611)
giữ kết luận:5prototype EURUSD/H4 chưa là khảo sát toàn thị trường; screen phí
chỉ chọn phép kiểm tiếp, chưa đóng OOS/risk/prop. Không sửa frozen tiêu chí batch.

Trước mở window mới, đọc [audit consumption và protocol Q1/2023](research/PROP-HISTORICAL-ROBUSTNESS-20261105.md).
Owner không nhớ đã xem2023–2024; nhãn hiện hành là historical robustness với
prior exposure unverified, không clean OOS. Registration đã khóa5candidate,
dates/metrics/cost/risk và source pins. Bài Q1/2023 đã chạy đủ5candidate×2cost
scenarios; window này nay consumed. Receipt AI giữ numbers/quality, recovery
Windows progress và implementation/source bindings. Không promote hoặc mở broker
từ kết quả này; đọc receipt trước đăng ký giai đoạn tiếp, không chạy lại bài đã xong.

Trước ưu tiên candidate hoặc mở bài tiếp, đọc
[time-fit05/11](research/PROP-FIRM-FIT-20261102.md#thời-gian-challenge-và-độ-phù-hợp-chiến-lược--kiểm-lại-05112026).
Unlimited challenge khác trial/inactivity/minimum days và thời gian ra tiền.
UTC range mới qua cost-screen, chưa chứng minh prop/time-fit; diagnostic ledger
chỉ hậu kiểm, full challenge lifecycle chưa được evaluator hiện có hỗ trợ.

Lát performance kế tiếp đã có valuation reuse, opt-in prepared quality/H4 cache
và parallel-start; delta mới nhất giảm parser/counter copies. Đọc
[số đo/giới hạn](research/ENGINEERING-REVIEW-Q1-20261105.md#tối-ưu-tiếp-parser-và-risk-counters--0511)
và workflow trước cấu hình study mới; không lặp fullQ1 để đọc lại report hoặc
sửa frozen protocol cũ để nhận nguồn/options mới. Full challenge lifecycle vẫn
là gap khác với tốc độ; decoded-tick cache/Rust chưa triển khai.

Shared tick preparation đã triển khai và smoke bằng fixture: `prepared_inputs_dir`
+ `--prepare-inputs --parallel-start` dùng chung quality/H4/lossless development
ticks, ghi phase wall/CPU. Full batch chính thức Q1/2023 đã chạy 5 candidate × 2
scenario trên source `0d831471` trong 1.800,48 giây, tất cả `completed_verified`;
golden event parity đạt ở mức semantic, byte khác chỉ do Decimal scale. Đọc
[benchmark/parity](research/ENGINEERING-REVIEW-Q1-20261105.md#full-batch-benchmark-chính-thức-và-golden-event-parity--0611)
trước study mới. Raw source/cache drift vẫn fail-closed; không sửa frozen attempt.
Hậu kiểm batch cho thấy simulation loop chiếm khoảng99,4–99,5% wall/worker và
CPU/wall khoảng96,8–98,5%; validation/cache chỉ còn0,5–0,6%. Chưa đổi mặc định
concurrency hoặc rewrite Rust khi chưa có profile A/B bounded giữ golden parity.
Profile bounded sau đó đã chạy Normal priority: 200.000 tick/7,63 giây; hotspot
là parse/hash + `hourly_quotes` và `advance_tick_execution`, chưa phải bằng chứng
whole-study speedup. GPU vẫn chưa có backend; giữ CPU oracle.
Đối với bước chiến lược tiếp theo, Trader đã có lifecycle evaluator offline cho
phase target/loss/reset/DST/minimum days/carry; activation, inactivity, payout,
historical fills và live reconciliation vẫn là gap firm-specific.
Thiết kế time-fit đã có [exact execution 2023](research/TIME-FIT-EXECUTION-20261106.md)
và [registration](research/TIME-FIT-HISTORICAL-20261106.json), hash
`ce7de7f0d60ace46dc72884d6c8b00a3f6c36fb8bd7630a82909409f4b1bb659`.
Metadata exports cũ không phải inventory toàn cache: QDM có đủ dates. Đã export
năm 2023 một lần, data preflight 27.549.175 ticks/1.504 H4 đạt; warmup 255 H4
reuse. Q1 consumed; Q2–Q4 đã đọc quality, prior exposure unverified, không OOS;
không mở 2024/2025+. Trader `3af69a73` ghi causal snapshots 3/6/12 tháng trong
một annual replay, giữ pending/positions và seal/reuse. Pipeline hữu hạn đã
khởi động; xem receipt AI và private `prop-time-fit-20261106/execution-v1/`
`pipeline.json` → `batch-1/progress.json` trước tác động. Không dispatch job trùng
hoặc đổi source numerical khi worker đang chạy. Chưa có kết quả cả năm và chưa
phải full phase1→phase2/time-to-payout.
Terms snapshot FTMO/The5ers đã ghi ở [PROP-TERMS-SNAPSHOT-20261106](research/PROP-TERMS-SNAPSHOT-20261106.md);
FTMO đủ cho evaluator sơ bộ, The5ers còn pin account/program và automation approval.

Owner giao triển khai workflow/skills và chủ động quản lý skill. Đọc
[strategy workflow](../tooling/ai-engines/STRATEGY-WORKFLOW.md) cho research,
qualification, preflight/dossier và delivery; [maintenance](../docs/development/SKILL-MAINTENANCE.md)
giữ trigger tự xét cập nhật/gộp/retire. Không tự sinh skill mỗi task hoặc thêm
service. Trạng thái source/native delivery và kiểm chứng thuộc receipt AI.

Owner đã mở lại nghiên cứu chiến lược prop theo
[protocol round1](research/PROP-STRATEGY-ROUND1-20261105.md); các ưu tiên
chỉ kiểm hệ thống ngày02–03/11 bên dưới là snapshot trước thay đổi này.
[Research trade tay/semi-auto/auto](research/PROP-AUTOMATION-AND-STRATEGY-EVIDENCE-20261105.md)
giữ nguồn, giới hạn và hướng auto có giám sát; owner tiếp đó giao triển khai
offline theo [round2](research/PROP-STRATEGY-ROUND2-20261105.md), chưa cấp grant
broker mới. [Tool survey](research/PROP-AGENT-TOOLS-20261105.md) xác minh MCP
chính thức TV/The5ers; owner chưa có TVpaid/The5ers nên chưa kết nối.
Lưu ý delta Terms The5ers §11 trước triển khai; chi tiết ở protocol/research.
Tra [chỉ mục research](research/README.md) và dùng
[workflow kế thừa](../.agents/skills/evidence-continuity/SKILL.md) để kiểm delta
và lưu kết quả ngoài chat. Scope/run/acceptance vẫn theo AI plan và receipt
được dẫn ở dưới; không suy quyền broker/holdout từ research hoặc context.

## Ưu tiên hiện hành — audit Trader cho một owner, 31/10/2026

**Trạng thái 01/11:** owner đã giao tiếp tục audit cùng Studio. Dùng
[checkpoint audit](../projects/trader/foundation_v2/evidence/owner-system-audit-20261031/CHECKPOINT.md)
và [review tổng hợp](../projects/trader/foundation_v2/evidence/owner-system-audit-20261031/OWNER-REVIEW-20261101.md)
để chọn lát tiếp; các snapshot tạm dừng bên dưới receipts là lịch sử.
Chưa có whole-product acceptance hoặc rollout runtime owner của đợt này.
Key Opus 5.5 đã hết hạn theo owner; pilot trước đó không chứng minh provider
còn dùng được. Tiếp source/fixture offline, không tự đổi provider để chạy job.

Phạm vi audit: đồng bộ toàn UI reference/frontend/backend/DB, workflow, VI–EN
và tốc độ phản hồi cho một người dùng, theo
[phụ lục audit](trader/OWNER-SYSTEM-AUDIT-20261031.md) thuộc Product Plan.
Không dùng % cảm quan hay task accepted lịch sử làm % hoàn thiện sản phẩm.

## Nghiên cứu giai đoạn AI tự chủ — 31/10/2026

**Owner làm rõ 02/11:** ưu tiên hoàn thiện hệ thống AI và workflow vận hành;
chưa dành thời gian tối ưu hoặc qualification chiến lược. Gác đề xuất chạy
validation2023 sang sau. Giữ candidate H4 hiện có làm fixture kiểm tích hợp:
giao việc → lấy dữ liệu → mô phỏng → phản biện → báo cáo trong UI, với trạng
thái/lỗi/hủy/retry và provenance rõ. Acceptance là hệ thống chạy đúng, quan sát
và tiếp tục được; lợi nhuận của fixture không là điều kiện hoàn thành hệ thống.
[AI plan](trader/AI-RESEARCH-UI-PROTOTYPE-20261031.md) giữ scope/acceptance mới;
receipt bên dưới giữ kết quả và bước tiếp. Không mở broker execution.

Owner đã giao nghiên cứu, fork/tích hợp Paperclip và thiết kế lại Studio.
Source/runtime ownership theo [integration guide](../tooling/integrations/README.md);
pilot đã có receipt; key Opus5.5 hết hạn được thay bằng Gemini theo quyết định
owner03/11. Kết quả provider/runtime hiện hành ở receipt AI, không suy từ catalog.
Kiến trúc/workflow dài hạn
đọc [brief hiện hành](research/AUTONOMOUS-TRADING-SYSTEM-BRIEF.md):
đích là tự động hóa nghiên cứu lẫn vận hành, ưu tiên B (tự quyết có giới hạn),
chuyển được sang A (chờ duyệt chiến lược mới). Brief giữ lựa chọn/câu hỏi và map
research cũ; không thay Product Plan/ledger hoặc mở quyền live. Trader khoảng 80%
là đánh giá cảm quan của owner, không phải acceptance đã kiểm chứng.
Đã chốt nghiên cứu mở trong phạm vi nhỏ; khởi đầu chỉ mô phỏng/demo, xét tiền
thật sau khi chiến lược có bằng chứng đạt tiêu chí và quyền tương ứng.

Bổ sung 02/11 — **owner đã chốt Forex major qua MT5, FTMO 2-Step Swing làm
chuẩn mô phỏng** theo [khảo sát prop](research/PROP-FIRM-FIT-20261102.md).
Offline trước, rồi free trial; chưa mua challenge hoặc duyệt phí/risk budget.
Crypto spot giữ làm baseline nghiên cứu. [Contract Forex/prop offline](research/FOREX-PROP-PILOT-20261102.md)
đã đăng ký với defaults tạm của agent; kết quả rule checks/source và bước tiếp
nằm trong receipt AI hiện có. Không tự tiếp execution crypto hoặc mở quyền
tài khoản/giao dịch từ quyết định này.

Tiếp nối02/11: owner đã đăng nhập FTMO demo; thông số EURUSD hiện tại đã đọc
và pin. Contract mục10 đăng ký chạy lại hai tuần rồi mở development quý I/2022
từ cache QDM, giữ nguyên strategy; validation/holdout chưa đọc vì chưa cần.
Swap hiện tại áp vào giá2022 là declared scenario, chưa phải phí lịch sử.
Receipt AI giữ source/job/results và các giới hạn xác minh. Owner đã cho phép
bảo trì/restart local trong AGENTS của Trader; quyền này không mở execution.

Khi tiếp tục: [AI plan](trader/AI-RESEARCH-UI-PROTOTYPE-20261031.md) giữ scope,
[receipt AI](checkpoints/ai-integrations-20261031/RECEIPT.md) giữ kết quả/bước tiếp;
[QDM guide](../projects/trader/docs/quantdatamanager.md) giữ đường lấy lịch sử
Forex đã có. Brief dài ở trên giữ cả thảo luận lịch sử, không thay các nguồn này.

Điểm resume03/11: đọc các mục mới nhất trong receipt AI, đặc biệt **Studio:
khôi phục runtime, Gemini và bàn giao native**. Dùng UI Paperclip trong Studio;
dialog/nút Quy trình và HTTP bridge ngoài đã được bỏ theo quyết định owner.
Cap10lượt/ngày đã gỡ; giữ concurrency1/agent, timer tắt, chống trùng và retry
có giới hạn. Đối soát native task/run/receipt trước retry; không redispatch
fixture đã hoàn tất để kiểm UI. Scheduler và nghiên cứu tự chủ vẫn cần gate
vận hành riêng; chưa tuning chiến lược.

## Naqex migration — 29/10/2026

Owner approved the Naqex ecosystem migration: `Naqex/workspace` plus independent
product submodules `trader`, `vi-dubber`, `quant-trading`, and `TradingAgents`.
Forks preserve upstream layout/attribution. Current work covers cleanup, visual
READMEs, paths, public CI/PR gates, local search and the requested Live controls.
Packaging, public application releases and production deployment are deferred.
First-party licensing changes use a new commit; historical MIT grants remain.
Canonical Trader source: `projects/trader`; product plan: `trader/PRODUCT-COMPLETION-PLAN.md`.
See the migration section in `trader/REPO-CLEANUP-PLAN.md`. Current runtime and
unrelated WIP can remain in the previous checkout until guarded cutover; the
old path is not the canonical source. Public release and active-runtime rollout
retain their approval gates. The snapshot below is historical and does not
report the new migration or today's process health.

**Historical snapshot:** các phần từ đây trở xuống được cập nhật lần cuối trong execution liên project 2026-10-02, trừ khi dòng đó ghi ngày khác. Đây là file điều hướng, không phải acceptance ledger và không thay runtime state. [Checkpoint đối chiếu PLAN](checkpoints/workspace-next-stage/ALL-PLAN-EXECUTION-20261002/CHECKPOINT.md) giữ requirement/evidence/gate và WIP.

**Ưu tiên owner ngày 02–03/10 (lịch sử):** tập trung MT5; VI Dubber để sau, không mở thêm lane
VI. Root tiếp quản WIP sau interruption; fresh agent inventory chỉ còn root.
Continuation được chốt sau00:00+07 ngày03/10; folders giữ execution date02/10.

## Chuỗi đọc bắt buộc

1. `AGENTS.md` áp dụng.
2. File này.
3. `WORKSPACE-NEXT-STAGE-PLAN.md` cho điều phối liên project.
4. `checkpoints/workspace-next-stage/RESUME.md` cho trạng thái execution mới nhất.
5. PLAN/ledger/checkpoint đúng project và đúng task.

Không đọc toàn archive để bắt đầu task. Archive chỉ mở để kiểm tra nguyên nhân, hash, regression hoặc quyết định lịch sử.

## Authority map

| Phạm vi | Authority | Vai trò |
|---|---|---|
| Workspace routing | `CURRENT-CONTEXT.md` | Baseline, priority, permission boundary và link đọc tiếp |
| Cross-project handoff | `WORKSPACE-NEXT-STAGE-PLAN.md` | Milestone, dependency, acceptance scope và worker workflow |
| Current execution | `checkpoints/workspace-next-stage/RESUME.md` | WIP, owner, last verified gate, blocker và next action |
| MT5 product | `trader/PRODUCT-COMPLETION-PLAN.md` | Product scope, U/Y gates, PATH-2 và acceptance nghiệp vụ |
| MT5 UI | `trader/TRADER-UI-MASTER-PLAN.md` | W0–W8 UI scope, visual/a11y/performance gates |
| MT5 runtime | Operational ledger/`STATE.json`/receipts được `EXECUTION-ENTRYPOINT.md` dẫn | Attempt state; không copy vào PLAN |
| VI Dubber | `../projects/vi-dubber/PLAN.md` + source/tests/checkpoints | Product phase, contracts và acceptance |
| Quant/TradingAgents | Project README/AGENTS/ledger riêng | Offline research/regression; không mở provider/broker |
| Shared UI | `UI-Systems/docs/` tại workspace root + accepted-scoped release receipt | Foundation/contracts; không suy release từ snapshot |

`CONTEXT-LIFECYCLE.md` là policy về authority, compact, archive và resume-read test. Không tạo ledger hoặc master PLAN thứ hai.

## Trạng thái đã xác minh theo snapshot (02–29/10)

Mỗi dòng giữ ngày/commit của bằng chứng riêng; ưu tiên hiện hành và audit 31/10 nằm ở đầu file.

- **Current Trader scope (29/10/2026):** dùng code/evidence FX-aligned trong `projects/trader/foundation_v2` theo [current scope amendment](trader/CURRENT-SCOPE-20261029.md). Figma Make/Y26 và Miro/Y12 được tạm hoãn, không phải điều kiện chặn hiện tại; các receipt cũ vẫn giữ nguyên để truy vết. U1/U3/U4/U9 và U2/U5/U6/U7/U8 chỉ được ghi nhận theo đúng phạm vi evidence, không tự chuyển thành full-product acceptance.
- **MT5 recovery/research:** U5b predeclared manual protective parity `b03304e`, U5a native feasibility `55add2e`, synthetic restore15checks `c418a07`, clean tracked-source Windows warm-cache setup `6265dc3`. Ledger/STATE r389 có37 tasks accepted ở scope đã đăng ký; các additions này không tự ledger-accept. U5a durable crash-state restore chưa đạt. Learn bridge đã accepted-scoped; QA404 là `learn_not_configured`, không là mất backend.
- **MT5 heap:** `c26d425` giữ final receipt của Analytics fixture5.000rows, measured3.601.275ms/2.620iterations/61precise samples. Post-GC12,62→13,69MiB, delta1,0653MiB, DOMdelta0, zeroerrors/overflow: scoped one-hour PASS. Framep95=33,2ms không có verdict60Hz. Historicalcoarse-heapFAIL vẫn giữ; đây chưa là whole-chart performance. Manual UI/Learn remediation và whole U/Y/W gates xem checkpoint hiện tại.
- **Job12/VI provider:** artifact-level completion không đồng nghĩa media QA. Current audit giữ `qa.passed=false`, `full_track_skipped=true`, `final_failed=122`; không `--fresh`, không xóa cache/receipt/lock, không đổi provider/model và không claim whole-pipeline.
- **VI Dubber — để sau:** `317ced9` chốt preview403/500 intent/retry, explicit Final/QA verdict và keyboard/contrast;22browser tests,30state captures/18axe scans không có violations. Không có independent final-r6 sign-off hoặc fullWCAG verdict. `af07c92` diagnostic143windows đã xong, canonical122QAfailures giữ nguyên; không inference resume hoặc mở M0-VI-ready/M5.
- **MT5 U5b margin:** `544e422` opt-in replay-execution-v2, fixed original starting-balance admission tại next-open; v1 bytes/behavior giữ nguyên.166offline tests/23subtests, root35core/service pass với hashes không drift. [Margin receipt](../projects/trader/foundation_v2/evidence/U5B-replay-margin-v2-CHECKPOINT.md) giữ rollback-v2 limits; PostgreSQL integration/horizon/manual-no-signal/floating-path và fullU5 còn mở.
- **MT5 chart states:** `d0267d5`, [bounded W8 receipt](../projects/trader/foundation_v2/evidence/wm-all-plan-20261002/chart-states/CHECKPOINT.md) giữ8/8cases ×5types, mixedOHLC/crosshair/wheel/pan/type-switch/Volume/SMA/history-reload trên2themes/4widths. UI source8205c89b… unchanged; root viewed7images, finalrawhashes equal. Independent approval/touch/pinch/manualWCAG/performance/fullW8 còn mở; canonical fixture/goldens không đổi.
- **Quant:** imported paper-soak safety-field validation `c498399`,35focused/257full tests; actual30–60day soak/recovery/alerts còn mở. Không live/execution.
- **TradingAgents:** HEAD `94e11a4`,133focused offline regression tests/socket denial; không mở provider/API key/network.
- **BR-01:** `65b5eb6` đính chính H2 filter count từ stored events và cập nhật research pointers; reject/P&L giữ nguyên,2021 đã consumed as development. Không đổi learner progress hoặc mở2022/2025.
- **Shared UI:** `annam-productivity` và Figma Make là accepted-scoped evidence; không coi đó là global theme/product-runtime acceptance.

## Quyết định sống

- **Execution override đã ghi nhận 27/09/2026:** trong phiên được giao chạy `WORKSPACE-NEXT-STAGE-PLAN.md`, owner cho phép làm song song vượt cap 3 children; runtime khi đó resolve `ch/linxaq` thành GPT-6 Astra `ultra`, dùng host pool trong trần cấu hình. Giữ override khi tiếp nối đúng execution đó; kiểm tra runtime thực tế, không tự sửa global config. Đây không phải model/cap mặc định cho task cleanup hoặc một lần giao plan mới.
- Reuse → adapt → shared khi có nhiều consumer thật và rollback rõ; không thêm framework chỉ vì có thư mục foundation.
- PATH-2 MT5 vẫn là foundation authority; không quay lại legacy Flask làm nguồn chính.
- UI global ở `UI-Systems/` trong repo; trading UI ở `UI/` và MT5; media UI ở VI Dubber. [Checkpoint chuyển thư mục](checkpoints/ui-systems-relocation-20261005/CHECKPOINT.md) giữ bằng chứng; đường dẫn D: cũ trong receipts/archive là lịch sử.
- TypeSafe/Jev chỉ là typed advisory judgment; không sở hữu arithmetic, fills, risk, ledger hoặc execution.
- Provider, broker, wallet, OAuth, holdout, public upload, paid service, deploy và destructive cleanup đều fail-closed.
- Các plan frontier, SaaS/multiuser, distributed compute, AI factory, SDK expansion và cloud connector là future reference; không thuộc execution hiện tại.

## Snapshot resume vận hành 02–03/10/2026 (lịch sử)

1. Đọc `RESUME.md`, sau đó đọc đúng domain PLAN.
2. MT5 margin đã commit `544e422`; W8 mixedOHLC/all5types/mousegestures đã scopedPASS. Tiếp independent visual review/touch-keyboard/chartlong-session hoặc remainingU5 gaps theo dependencies; giữ fixture/goldens/ledger. Scoped Vite5186PID18572/tool34774 đã teardown sau exactcommandcheck; fresh listeners5180/5186/8020/8030 absent. Không restart/reseed backend.
3. VI UI-state audit đã commit `317ced9`, diagnostic143/143 đã xong. Owner ưu tiên MT5; để VI lại sau và giữ provider/TTS/rerender/human gates.
4. Quant/TradingAgents giữ offline regression và evidence; không mở external authority.
5. Mỗi worker ghi receipt tại project/checkpoint owner, không append raw log vào file này.

Bản đầy đủ trước cleanup được giữ tại `archive/2026-10-01-cleanup/planning__CURRENT-CONTEXT.md`; SHA-256 nằm trong `ORIGINAL-BYTES-MANIFEST.json`.

# Current context — Naqex Workspace

Review ngày 09/11/2026 · `REVIEWED-PARTIAL / COMPACTED-RESUMABLE`.
File này giữ trạng thái hiện hành và đường đọc tiếp; không là task ledger,
chứng nhận runtime, hoặc lịch sử từng job. Đọc đúng PLAN/receipt của việc được giao.

## Việc hiện tại: Goal mới tìm ứng viên challenge

Owner giao tìm ứng viên đủ C1/C2, chuẩn hóa dữ liệu và cải tiến có bằng chứng.
Goal đang active; [campaign v2](research/CHALLENGE-CANDIDATE-CAMPAIGN-V2-20261108.md)
giữ scope, quyết định B cũ không kết thúc chiến dịch mới. **Chưa challenge-qualified.**

Lát mới nhất: [R065 opening5 datarevision](research/NASDAQ-OPENING5-ORB-DATA-REVISION-RESULTS-20261109.md)
đã fullFractionreviewed2022:243closedtrades,reference+714,71USD/stress+568,12
trên10k, knownflat.2019giữunknown từ25Jan14:49UTC,16closed/partialprofits;
khôngcopy0/khôngdropyear. Twoyeargate chưađạt, chưachallengecandidate.
Catalogue65records/45researchpolicyversions/25native, chưa newversion vìdatarev.

Datarepair có [protocol](research/NASDAQ-TICK-DERIVED-HOUR-PROTOCOL-20261108.md)
trướcbuild/replay. [8tickhours review](research/NASDAQ-M1-GAP-TICK-RESULTS-20261108.md)
cho22missingcashminutes:15noquotes,7Oct2022cóquotes nhưng2commonOpenkhác
firsttick nênmissing-onlygatefalse. Whole15UTC18Oct2022derivedfromticks có
120sidebars/480pricefields reviewed,2mixed2022books thêm7minutes/bên;mọifield
ngoàihour exact, volumeconversionerror0. Oldsource/pins/falsegate giữnguyên.

R065v2reuse4books2019 exactbyte/review;replay4books2022 với exactcoded5aad5b/
risk25/TP10R/costs/latency.191closedtradeprefix vànullstate exactold;8bookcensus
giữ đủ. Closedcash3/6/12months stress+83,15/+395,47/+568,12USD;maxclosednet
981,44USD/closedbalanceDD595,93,khôngintrabarDD/proppass. Khôngraise risk để
target. Prefix/reviewdiagnostics không là cleanOOS hoặc newblindtrial.

**Tiếp:** alternateofficialarchive transport/sourceadmission cho đúng2019first
missinghour. Cần kiểmprimaryURL/format vàregisterboundedfixture trướcfetch,
không tựđoánbi5schema hoặc kéo cảhistory. Nếu rawarchive cũngthiếu,giữunknown,
khônginterpolate quote/relaxfrozencriteria hoặc bật broker/own2025+holdout.
Giải data/method uncertainty có evidence, không retune R065 khi thấy2022dương.

Private root `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`;
`execution-v1/nasdaq-opening5-orb-v1` original8books/review;`nasdaq-M1-gap-ticks-v1`
rawfidelity/failedbridgegate;`nasdaq-tick-derived-hour-v1` approvednewmixedview;
`nasdaq-opening5-orb-v2` fournew/fourreusedbooks+full2022review/prefixparity;
`nasdaq-opening5-2022-cash-diagnostics-v1` cashprefix/peak/concentration.
PIDs21080/12496/25656/7808 vàreviewers terminal0, khôngworker chờ. Sourcebuild
11,265s/review4,221s;affectedreplay7,777s/review5,544s,khôngwholeperformanceclaim.
Trader83731fc8 untouched;no runtime/skills/globalconfig mutation. Source/native
primitives vàcurrentplans được reuse;C1/C2/cleanOOS/prop/forward/handover cònmở.

Các kết quả trước và negatives tra [research index](research/README.md) hoặc
campaignv2; không mở lại raw/numeric batch không đổi. [Data/retrieval review](research/AGENT-DATA-RETRIEVAL-20261108.md)
đã xong trong scope, [search CLI](../tooling/search/README.md) dùng localindex
để tìm tài liệu rồi đọc source; không cần vectorDB/service mới. Numerical
artifacts có hash là nguồn cho số liệu, không lấy đoạn search làm kết quả.

## Baseline: đợt Goal trước đã kết thúc theo B

[Báo cáo owner, mục8](research/OWNER-EVIDENCE-REPORT-20261108.md) là quyết định
kết thúc đợt: chưa có ứng viên đủ bằng chứng để đề xuất challenge. Đã rà53hồ sơ/
41versions và đối soát các artifacts chính. Đây không là đạt C1/C2 hoặc chứng
minh không có chiến lược phù hợp. [Campaign](research/CHALLENGE-CANDIDATE-CAMPAIGN-20261108.md)
giữ tiêu chí và pins lịch sử. Owner đã mở Goal mới; tiếp campaign v2, không
chạy lại study không đổi hay ép ra winner.

- [R023local session](research/LOCAL-SESSION-RESULTS-20261108.md): primary phiên
  Mỹ không đạt retention; context châu Âu không được thay primary sau outcome.
- [PreECBpath risk](research/PRE-ECB-PATH-RISK-RESULTS-20261108.md): đã đo xong;
  giữ parent parked, không bỏ/nới SL hoặc đổi lot từ counterfactual.
- [GoldSMA50k](research/GOLD-SMA50K-REVIEW-20261108.md): còn research survivor,
  chưa challenge-ready;12tháng không là deadline cá nhân mới của owner.
- Các numerical jobs của đợt Goal đã terminal khi review; đây không là kiểm
  sức khỏe app/MT5 hiện tại. Ownerhandover mới prepared_not_demonstrated.

## Đọc theo đúng phạm vi

| Việc | Nguồn chính |
|---|---|
| Research/kết quả/đã kiểm gì | [Research index](research/README.md) → tài liệu chủ đề và private artifacts được dẫn |
| Nghiên cứu → kiểm định → vận hành | [Strategy workflow](../tooling/ai-engines/STRATEGY-WORKFLOW.md), repo skills tương ứng |
| Trader source và scope | `projects/trader/`, [Product Plan](trader/PRODUCT-COMPLETION-PLAN.md) → [entrypoint](trader/EXECUTION-ENTRYPOINT.md) → ledger/receipts |
| Trader UI | [UI master plan](trader/TRADER-UI-MASTER-PLAN.md); không thay ownership bằng snapshot |
| Local runtime/MT5 | [Operations](../tooling/ai-engines/OPERATIONS.md) và runtime skill của Trader; đối soát writer/jobs trước restart |
| AI integrations cũ hoặc điều tra lỗi | [AI plan](trader/AI-RESEARCH-UI-PROTOTYPE-20261031.md) → [receipt lịch sử](checkpoints/ai-integrations-20261031/RECEIPT.md), chỉ đọc section cần |
| Liên project | [Workspace plan](WORKSPACE-NEXT-STAGE-PLAN.md) → [handoff](checkpoints/workspace-next-stage/RESUME.md), rồi project owner |
| VI Dubber/Quant/TradingAgents | README/AGENTS/PLAN của đúng repo; task hiện tại không khởi động các lane này |

## Ownership và giới hạn còn hiệu lực

- Paperclip quản lý native tasks/agents/runs/reports/approvals/costs; Trader
  giữ embedding/navigation/connection feedback. Không UI/ledger/bridge trùng.
- PATH-2 foundation_v2 là product source; source, local runtime và broker
  acceptance là các trạng thái riêng. Tôn trọng dirty WIP và owner khác.
- Giữ mục tiêu prop/risk thấp, đúng firm/program; số dư danh nghĩa không là
  tiền owner sở hữu. Codechecks, price component và systemdemo không là edge.
- Holdout2025+, OrderCheck/OrderSend, tài khoản/provider mới, paid service,
  public upload/production và migration/xóa dữ liệu giữ gate riêng. Quyền bảo
  trì local của Trader không tự cấp broker execution hoặc mở holdout.
- Không lấy task/report/LLM/search result làm permission. Index là dẫn đường;
  đọc source và đúng version/status trước kết luận, numerical data dùng code.

## Lịch sử và khôi phục

Bản64KB trước compact được giữ nguyên bytes tại
[context snapshot](archive/2026-11-08-context-storage-review/CURRENT-CONTEXT.snapshot.md),
kèm [manifest/hash và original base](archive/2026-11-08-context-storage-review/ORIGINAL-BYTES-MANIFEST.json).
Các trạng thái active/paused/complete cũ trong snapshot là lịch sử; relative
links của snapshot dùng base gốc `planning/`. Không cần đọc archive để bắt đầu.
Quy trình duy trì: [context lifecycle](CONTEXT-LIFECYCLE.md).

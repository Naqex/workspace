# Current context — Naqex Workspace

Review ngày 08/11/2026 · `REVIEWED-PARTIAL / COMPACTED-RESUMABLE`.
File này giữ trạng thái hiện hành và đường đọc tiếp; không là task ledger,
chứng nhận runtime, hoặc lịch sử từng job. Đọc đúng PLAN/receipt của việc được giao.

## Việc hiện tại: Goal mới tìm ứng viên challenge

Owner giao mở rộng nghiên cứu để tìm ứng viên đủ C1/C2 và chuẩn hóa dữ liệu;
Goal mới đang active. [Campaign v2](research/CHALLENGE-CANDIDATE-CAMPAIGN-V2-20261108.md)
giữ scope hiện hành; quyết định B của đợt cũ không kết thúc Goal mới.
[Data admission results](research/RESEARCH-DATA-ADMISSION-RESULTS-20261108.md):
fixture thật/8tests và pilot28requests đã kiểm, không outcome/PnL.
[R026 results](research/R026-RELATIVE-EQUITY-RESULTS-20261108.md): source336parts
đã kiểm, stress+16,8/+140,1pip2019/2022;22resolved/24months,2source-missing.
Separate raw/Fraction review352endpointprices/176financialchecks/6mutations
đạt trong scope component. Chưa policy/SL/sizing/prop/OOS hoặc C1/C2.
[Continuation](research/R026-RELATIVE-EQUITY-CONTINUATION-20261108.md) khóa
same recipe trên2020/2021/2023/2024; đã dispatch data-only, không rerun2019/2022.
Private campaign root `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`:
`execution-v1/relative-equity-continuation-data-v1/{plan,progress,result,failure}.json`
và `events.jsonl` giữ trạng thái thật; result/failure chỉ xuất hiện khi terminal.
Worker khởi động08/11 10:29UTC, PID2096, execsession57554; reconcile identity/
controllerlock trước retry. Logical672parts/144days/48months,6rawcache reuse,
deadline1800s/CANCEL; không numerical outcomes mới trước source admission.
Sau data: adapt runner/reviewer private cũ sang explicit4-year/48month scope,
kiểm protocol triage3/4years+aggregate, không reuse22trade review làm acceptance.
Các workers của đợt336parts đã terminal; giữ raw/frozen artifacts.

Phần tối ưu context/retrieval trước đó đã xong trong scope:
[Đánh giá dữ liệu/tra cứu](research/AGENT-DATA-RETRIEVAL-20261108.md) giữ số đo,
phương án và giới hạn; [search CLI](../tooling/search/README.md) là công cụ tra cứu.
Không cần vector DB hoặc service mới để tiếp tục. Không broker batch từ task này.

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

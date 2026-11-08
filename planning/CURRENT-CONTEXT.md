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
[R026 long results](research/R026-RELATIVE-EQUITY-CONTINUATION-RESULTS-20261108.md):
gác exactpriceproxy sau6years, stress−227,6pip/66of72resolved;3/4năm mới âm.
Source672parts và numeric48months đã terminal,768presence/704price/352financial
checks,8mutations đạt trong scope; chưa policy/prop/edge. Không rescue bằng
clock/side/SL hoặc rerun baseline2019/2022.
[R010 source results](research/MULTI-ASSET-TREND-DATA-RESULTS-20261108.md):
2018–2024monthlyhistory84/84, oldATRfullsessions chỉ32eligiblemonths.
As-of120s không tăng140/144monthlyendpoints; không adopt/nới cap/gates.
Sourceprobe12years/96sideseals terminal0, không newPnL hoặc broker/holdout.
Private campaign root `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`:
`execution-v1/relative-equity-continuation-{data,component}-v1` giữ R026;
`execution-v1/multiasset-trend-admission-v1` giữ diagnosis/asofsource.
Các workers của hai lát này terminal; không rerun hoặc sửa oldartifacts.
[Monthly input results](research/MULTI-ASSET-MONTHLY-INPUT-RESULTS-20261108.md):
`execution-v1/multiasset-monthly-input-v1` có864records/859observed/5missing,
2018–2024 đủ504/504; source-review1430prices/4mutations đạt. Inputphase0a9861a
đã terminal; không parse14GBraw lại cho arithmetic. GoldAsk vẫnnull/unknown.
[Frozen component](research/MULTI-ASSET-TREND-COMPONENT-20261108.md) đăng ký
primarymixedsign1/3/12 +12monthlyreturnSD/inversevol,benchmarklong,2018–24,
continuousnormalizedNAV10k/gross≤1,2declaredcosts,fullmonthlyroll và finalopenmark.
[Component results](research/MULTI-ASSET-TREND-RESULTS-20261108.md):4books đã
terminal/reviewed; primary reference−1.138,18/stress−3.519,01USD trên10kproxy,
stress0/7years dương, khôngretained.1.008weights/allocations kiểm bằng code
khác,5mutations; numeric1,416s/review1,488s, không đọc lại14GBraw.
Không actualaccount/lotstep/SL/prop; financing vẫn declaredscenarios.
**Lát tiếp:** khảo sát cơ chế holding ngắn có dữ liệu hợp lệ, khác exactrecipes
đã gác; freeze trước outcome, không hạfunding/increaseleverage cứu R010.

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

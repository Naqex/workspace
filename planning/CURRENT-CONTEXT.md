# Current context — Naqex Workspace

Review ngày 09/11/2026 · `REVIEWED-PARTIAL / COMPACTED-RESUMABLE`.
File này giữ trạng thái hiện hành và đường đọc tiếp; không là task ledger,
chứng nhận runtime, hoặc lịch sử từng job. Đọc đúng PLAN/receipt của việc được giao.

## Việc hiện tại: Goal mới tìm ứng viên challenge

Owner giao tìm ứng viên đủ C1/C2, chuẩn hóa dữ liệu và cải tiến có bằng chứng.
Goal đang active; [campaign v2](research/CHALLENGE-CANDIDATE-CAMPAIGN-V2-20261108.md)
giữ scope, quyết định B cũ không kết thúc chiến dịch mới. **Chưa challenge-qualified.**

Lát mới nhất: [R068/R069 stopped-label ML](research/GOLD-ML-SL-LABELS-RESULTS-20261109.md)
đã train/review16books:0lệnh/0PnL, mọi747/750decisions được score nhưng không
vượt frozen0,10R. Gác exactrecipe, không hạthreshold/refit; no-signal không là
bug hoặc proof mọiML vô dụng. Catalogue69records/48policyversions/25native,
4controls. [R067](research/GOLD-SILVER-FORMATION-RESULTS-20261109.md) giữ negative.

Protocol06c6972/implementation3232d0c trước actual outcomes. Reviewed newsource
XAU2019/2022:23.650bars/118.250fields; train2018/2021 reuse sealedR067. Fullreview
2.994opportunities/1.497training-label census, float32trees và16books;8focusedtests
đạt. H1intervalproxy/declaredcosts/exposeddevelopment không là broker/prop/OOS.
Resulta986deb11477637e188d4707b01b2ed2506f8fc2ff77caa1f5ae85c902c9ea23;
review22afd3be4b958a9a1f0a25fbae69a7174e45321814f2cf1d83d7673e5b6930a3.

Private root `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`;
`execution-v1/gold-ml-source-v1` và `gold-ml-sl-labels-v1` giữ source/packs/census/
books/pins/progress/events/timing/review/no-signal-diagnostic. Jobs terminal0,
không phải chờ. Source22,841s/CPU0,859s;producer7,894s/CPU7,563s;review3,988s.
Không bottleneck cầnGPU/Rust/framework mới. Trader83731fc8/skills/runtime/global
config giữ nguyên; không rawoverwrite/data deletion/paidprovider/account/broker.

**Tiếp:** method admission cho stock-specific information/abnormal activity,
khác unconditional price-only signals. Paper Stocks in Play cần relative
traded-share volume; quote-CFD volume chưa được chứng minh tương đương. Chưa
đăng ký/fetch/train/PnL một stock strategy; cần source/clock/adjustment/universe
và exactprotocol trước numerical. Không chọn beststock/event hồi tố làm edge.
Ownholdout2025+ vẫn đóng. Không retune R068 để ép winner.

R065/R066 cũng đã gác theo conditional2019negative; exactunknowns vẫn giữ.
Tra [R065](research/NASDAQ-OPENING5-BOUNDS-RESULTS-20261109.md) hoặc
[R066](research/NASDAQ-NOISE14-RESULTS-20261109.md) khi cần, không replay hoặc
archive chase không đổi chỉ vì source chưa complete. Chưa ứng viên challenge.

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

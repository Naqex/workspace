# Current context — Naqex Workspace

Review ngày 09/11/2026 · `REVIEWED-PARTIAL / COMPACTED-RESUMABLE`.
File này giữ trạng thái hiện hành và đường đọc tiếp; không là task ledger,
chứng nhận runtime, hoặc lịch sử từng job. Đọc đúng PLAN/receipt của việc được giao.

## Việc hiện tại: Goal mới tìm ứng viên challenge

Owner giao tìm ứng viên đủ C1/C2, chuẩn hóa dữ liệu và cải tiến có bằng chứng.
Goal đang active; [campaign v2](research/CHALLENGE-CANDIDATE-CAMPAIGN-V2-20261108.md)
giữ scope, quyết định B cũ không kết thúc chiến dịch mới. **Chưa challenge-qualified.**

Lát mới nhất: [R065 conditional bounds](research/NASDAQ-OPENING5-BOUNDS-RESULTS-20261109.md)
đã hoàn tất và kiểm lại bằng Fraction: **gác exact opening5 recipe**. Trên vốn
10.000 USD/năm, conditional 2019 net chuẩn −351,20→−339,70 USD; stress
−925,72→−914,80 USD. Ngay đầu biên có lợi vẫn âm. Năm 2022 có 243 lệnh,
+714,71/+568,12 USD, từng lệnh khớp parent. Không thay risk25USD/SL/TP/cost.

Đây là outer bounds **có điều kiện** theo H1 cùng side và parent execution,
không phải khôi phục giá hay actual PnL. [Exact parent](research/NASDAQ-OPENING5-ORB-DATA-REVISION-RESULTS-20261109.md)
vẫn giữ annual2019 N/A, unknown từ 25/01 14:49 UTC và two-year gate inconclusive.
Không biến sensitivity verdict thành original pass/fail hoặc challenge candidate.
Catalogue vẫn 65 records / 45 research policy versions / 25 native rules.

Archive BI5 probe có một GET timeout trước HTTP response sau 21,608s, không
binary payload; đã terminal, không retry không đổi. [H1 fixture protocol](research/NASDAQ-H1-GAP-ENVELOPE-PROTOCOL-20261109.md)
và kết quả trong bounds report xác nhận envelope chứa 16.624 ticks/59M1,
nhưng không phục hồi được quote phút thiếu. Không tiếp tục archive chase cho
recipe đã bị gác theo conditional economics.

**Tiếp:** [NASDAQ noise14 method admission](research/NASDAQ-NOISE14-METHOD-20261109.md).
Reuse band helper R048 và source-only NASDAQ M1/warmup/calendar. Khóa recipe,
known-at/halfday/required14 sessions/cost/risk/gap semantics, rồi kiểm fixtures
trước outcomes. Đây là trial chuyển thị trường, chưa code/backtest; giữ
negatives US500 của R048, không grid hoặc gọi dev2019/2022 là clean OOS.
Không đọc own2025+ holdout hoặc bật broker.

Private root `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`;
`execution-v1/nasdaq-opening5-bounds-v2` giữ đủ8 books/pins/progress/review.
V1 failed do Decimal event serialization, giữ failure/scripts; v2 sửa logger
và reuse book đầu nguyên bytes, không chạy lại. 8 unit tests mới +12 parent
regressions và12 synthetic Fraction cases đạt; full8-book Fraction review/
6 mutations đạt. V2 24,335s/review7,652s; không whole-engine speedup claim.
H1 audit và numerical/reviewer PIDs đã terminal; không worker để chờ.
Trader83731fc8 không đổi; không runtime/skills/global config/data deletion.

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

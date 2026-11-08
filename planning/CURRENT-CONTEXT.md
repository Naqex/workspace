# Current context — Naqex Workspace

Review ngày 08/11/2026 · `REVIEWED-PARTIAL / COMPACTED-RESUMABLE`.
File này giữ trạng thái hiện hành và đường đọc tiếp; không là task ledger,
chứng nhận runtime, hoặc lịch sử từng job. Đọc đúng PLAN/receipt của việc được giao.

## Việc hiện tại: Goal mới tìm ứng viên challenge

Owner giao tìm ứng viên đủ C1/C2, chuẩn hóa dữ liệu và cải tiến có bằng chứng.
Goal đang active; [campaign v2](research/CHALLENGE-CANDIDATE-CAMPAIGN-V2-20261108.md)
giữ scope, quyết định B cũ không kết thúc chiến dịch mới. **Chưa challenge-qualified.**

Lát hiện tại: [NASDAQ M1 history](research/NASDAQ-M1-HISTORY-PROTOCOL-20261108.md)
đã đăng ký calendar và 8books/1.704rawdays trước tải. V1 dừng vì producer
thiếu `format:json`, không phải timestamp nguồn sai; cache-only diagnostic
đã kiểm54.977bars/61rawdays. [Recovery v2](research/NASDAQ-M1-HISTORY-RECOVERY-20261108.md)
reuse raw/calendar exacthash, thêm output-shape preflight và16tests đạt.
Đầu ra tại `execution-v1/nasdaq-m1-history-v2` dưới private root; đọc status/
failure/result/review để biết tiến độ, chưa economics hoặc challenge.

Lát trước: [R062FOMCcomponent](research/FOMC-NASDAQ-COMPONENT-RESULTS-20261108.md)
20officialcalendarpages/16events/32windows đãterminal/reviewed64costcases/
128quotes/6mutations.2019stress−0,12USD/unit,pairedcontrol−103;2022positive
nhưngjointfilterfail. ChưaSL/sizing/account/prop/OOS. Không clock/fee/controlrescue.
Catalogue62records/44researchversions/25native; chưa challengecandidate.
**Tiếp:** [NASDAQdailyreversion method/source](research/NASDAQ-DAILY-REVERSION-METHOD-20261108.md):
2cashM1fixtureswinter/summer đủ390min/side/day+16:01quotes;780presencechecks/
4mutations. Đăngký cashcalendar/holiday/earlyclose và source-onlyM1history
cho exactquestion trước economicrecipe. Không dựng09:30cashbar từH1 hoặc
claim CFD/quotevolume là ETF/exchangevolume. Chưa thêmNASDAQR050policy.

Private root `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`;
`execution-v1/fomc-nasdaq-component-v1` và `nasdaq-cash-session-fixture-v1`
giữ pins/results/reviews/status/events. PIDs21920/22636/29228 vàreviewers
terminal0, khôngworker chờ. FOMCcalendar11,081s/numeric0,536s/review0,261s,
không totalresearchtimer. [R035](research/FX-PAIR-FORMATION-RESULTS-20261108.md)
GBP/AUDformation chưađạt,khôngpairgrid;[R061](research/NASDAQ100-H4-SMA-RESULTS-20261108.md)
và[R019](research/PRIOR-DAY-RETEST-RESULTS-20261108.md) khôngretained,khôngrerun.
Trader pin83731fc8. Isolatedstatvenv/hashlock đãcó, khôngproductmutation.

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

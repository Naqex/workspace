# Current context — Naqex Workspace

Review ngày 09/11/2026 · `REVIEWED-PARTIAL / COMPACTED-RESUMABLE`.
File này giữ trạng thái hiện hành và đường đọc tiếp; không là task ledger,
chứng nhận runtime, hoặc lịch sử từng job. Đọc đúng PLAN/receipt của việc được giao.

## Việc hiện tại: Goal mới tìm ứng viên challenge

Owner giao tìm ứng viên đủ C1/C2, chuẩn hóa dữ liệu và cải tiến có bằng chứng.
Goal đang active; [campaign v2](research/CHALLENGE-CANDIDATE-CAMPAIGN-V2-20261108.md)
giữ scope, quyết định B cũ không kết thúc chiến dịch mới. **Chưa challenge-qualified.**

Lát mới nhất: [closing-tick source/timing pilot](research/INDEX-CLOSING-TICK-CALIBRATION-RESULTS-20261109.md)
đã thu/review đủ 8 giờ theo protocol `08501da`: 115.502 joint ticks,
577.510 field checks, 960 common M1 side bars exact, 0 conflict; cả 8 late
signal closes khớp tick aggregate. 64 timestamp targets có quote; không PnL.
Đây không phải actual delivery/broker latency, full history hoặc edge proof.
Package/bundle/lock/helper pins giữ nguyên bản 1.51.1 đã audit, không upgrade.
Producer 19,158 s /reviewer 8,820 s; mọi job terminal, raw/seals đã giữ để reuse.

**Performance đã đo:** [integer tick/scoped pin checks](research/INDEX-TICK-REVIEW-OPTIMIZATION-RESULTS-20261109.md)
khớp 577.510 fields / 960 M1 side OHLC / 64 locators và age; 32 actual mutations
reject, 19 tests đạt. Inspect median 2,891 → 0,726 s (3,98×); Node cached replay
12,799 → 1,819 s (7,04×), cùng export hashes; không full-history ETA.
Giữ helpers mới cho future consumers, old collectors/oracle/raw giữ nguyên.
**Tiếp:** source admission bổ sung 16:00–17:00 trên cùng 4 dates × 2 assets;
sau đó freeze full-history intake + economic recipe riêng. Không fetch lại
8 giờ cũ hoặc rerun books không đổi. Source quote availability khác asset,
không chọn latency bằng PnL hoặc tự nới live freshness/risk.
Cần chốt method window trước economics: parent exit Open15:59 khác paper
cash close16:00; đổi exit là recipe/model revision. Pilot chỉ tới16:00,
chưa source admission cho quote sau cash close; không chỉ giảm delay rồi
gọi là paper replication.

[R076/R077 rest-of-day review](research/INDEX-REST-OF-DAY-RESULTS-20261109.md)
đã terminal: primary stress USD/unit 2019/2022 US500 −404,96 /−371,12;
NASDAQ −536,99 /−17,80. US5002019 còn missing entry15:31 ngày23/12, tổng là
known-partial; giữ unknown. NASDAQ2022 reference+232,20 nhưng stress âm.
Gác exact components. 8 tests mới +11 regressions, 28 synthetic cases,
full Fraction review: 1.006 rows /9.950 cost-role cases /18 mutations. Shared code
`d1503ce` giữ R074/R075: 1.006 old rows/summaries exact; producer 19,237 s /review 14,132 s.

Catalogue **77 records /58 policy-model versions /25 native /9 controls**;
chưa challenge-qualified, Goal active. Source pilot không thêm strategy version.
Consensus filter mới ở queue, chưa chạy group PnL. Không own2025+ /broker /new provider.

[R075 recovery](research/US500-OVERNIGHT-REVERSAL-RESULTS-20261109.md) giữ v1
failure/v2 frozen-source admission. Guard `748b9d9` chặn missing input/forged
null hash; 4 actual source admissions không đổi, không repin old snapshots.
R074/R075 negatives và [NYFX conditional](research/NY-FX-GAP-SCENARIOS-RESULTS-20261109.md)
negative giữ nguyên; [strict FX annual N/A](research/NY-FX-PAIRED-LATENCY-RESULTS-20261109.md)
không bị clear bằng conditional model.

Private root `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`;
`execution-v1/index-closing-tick-calibration-v1/` giữ source/review/status;
`index-restofday-components-v1/` giữ economic books/rows/diagnostic/status;
raw ở existing `source-hour-cache-v1/`. Preflight stdin SyntaxError trước import
đã giữ failure/script v2. Trader `83731fc8`, runtime, skills/global config không
đổi; không migration/xóa raw. [Data/retrieval review](research/AGENT-DATA-RETRIEVAL-20261108.md)
giữ ownership, không cần vector DB mới.

[R068/R069 ML](research/GOLD-ML-SL-LABELS-RESULTS-20261109.md) giữ0signalnegative,
khôngthresholdrescue;[R067](research/GOLD-SILVER-FORMATION-RESULTS-20261109.md)
giữformationnegatives. [Stock fixture](research/STOCK-INFORMATION-SOURCE-RESULTS-20261109.md)
đãreviewnhưngvolume/adjustment/PIT/targetfit gaps;gácbulkstockhistory/PnL.
The5ersstocks chỉBootcamp/ProGrowththeoFAQđọc09Nov;khôngtựđổiHighStakes.

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

# Current context — Naqex Workspace

Review ngày 09/11/2026 · `REVIEWED-PARTIAL / COMPACTED-RESUMABLE`.
File này giữ trạng thái hiện hành và đường đọc tiếp; không là task ledger,
chứng nhận runtime, hoặc lịch sử từng job. Đọc đúng PLAN/receipt của việc được giao.

## Việc hiện tại: Goal mới tìm ứng viên challenge

Owner giao tìm ứng viên đủ C1/C2, chuẩn hóa dữ liệu và cải tiến có bằng chứng.
Goal đang active; [campaign v2](research/CHALLENGE-CANDIDATE-CAMPAIGN-V2-20261108.md)
giữ scope, quyết định B cũ không kết thúc chiến dịch mới. **Chưa challenge-qualified.**

Lát mới nhất: [R078/R079 consensus](research/INDEX-CONSENSUS-RESULTS-20261109.md)
đã terminal/reviewed, cả hai không retained. Primary1s stress USD/unit2019/2022:
US500 −363,40/−370,05; NASDAQ −611,10/−774,42. 3.018 rows /22.440 role-cost
cases, 4 mutations reject; producer2,563s/review2,757s, không raw/source rerun.
Selected firsthalf=primary là invariant, không impossible performance gate.
Parent [paper-windowv2](research/INDEX-PAPER-WINDOW-RESULTS-20261109.md) và
3unknown US5002019/60s vẫn giữ. Chưa challenge, Goal active.

Full source1.996hours/16.080.264ticks đã thu/review, 80.401.320integer field checks;
20hours/1.213.185fields qua Fraction riêng. 149.218commonM1sideOHLC exact,
0conflict sau [quarter correction](research/INDEX-PAPER-WINDOW-SOURCE-CORRECTION-20261109.md).
V1 reviewer copy pilot1/3 bỏ Q2/Q4 US500; raw economic review chặn wrong mask.
Source viewv2 sửa498hours,1.498reports bytes exact; NASDAQ1.509economicrows reuse
exact. Corrected economic review:3.018rows/29.850rolecostcases,6mutations reject.
Không new fetch/raw rewrite; source network failure đã resume từ1.353prefix.

[Boundary pilot](research/INDEX-CASH-CLOSE-BOUNDARY-RESULTS-20261109.md) đã terminal:
8 giờ16:00–17:00 mới /14.847 ticks /74.235 fields /240 M1 side bars exact,
32 targets có quote, 0 conflict. Reuse 8 giờ cũ15:00–16:00 đã review115.502ticks,
không fetch lại. Chỉ archived quote availability, chưa broker latency/edge.
Native package1.51.1/pins không upgrade, raw/frozen sources giữ nguyên.

**Performance đã đo:** [integer tick/scoped pin checks](research/INDEX-TICK-REVIEW-OPTIMIZATION-RESULTS-20261109.md)
khớp 577.510 fields / 960 M1 side OHLC / 64 locators và age; 32 actual mutations
reject, 19 tests đạt. Inspect median 2,891 → 0,726 s (3,98×); Node cached replay
12,799 → 1,819 s (7,04×), cùng export hashes; không full-history ETA.
Giữ helpers mới cho future consumers, old collectors/oracle/raw giữ nguyên.
**Tiếp R080:** [EU-open protocol](research/US500-EU-OPEN-COMPONENT-PROTOCOL-20261109.md)
`2f04156` đã freeze trước outcomes, chưa implementation/numeric. Fixed BUY
23:30→03:30 NewYork/exitdate, M1Open proxies23:31/03:31; no VIX/ATR/clockgrid.
[Source pilot](research/EU-OPEN-SOURCE-PILOT-RESULTS-20261109.md) 8dates/
32sidebars/192raw fields exact +3mutations, 4,042s/calls0, full-quarter loader.
Chỉ fixture source admission, annual endpoints/census/fees/gap trước PnL.
[Method/queue](research/EU-OPEN-AND-OIL-METHOD-20261109.md) giữ Cambridge clock
và oil/EIAETF mapping gap; chưa chuyển USO result sang WTI CFD/bulk fetch.
Không retune consensus negatives hoặc coi consumed2019/2022 là unseen.

[R076/R077 rest-of-day review](research/INDEX-REST-OF-DAY-RESULTS-20261109.md)
đã terminal: primary stress USD/unit 2019/2022 US500 −404,96 /−371,12;
NASDAQ −536,99 /−17,80. US5002019 còn missing entry15:31 ngày23/12, tổng là
known-partial; giữ unknown. NASDAQ2022 reference+232,20 nhưng stress âm.
Gác exact components. 8 tests mới +11 regressions, 28 synthetic cases,
full Fraction review: 1.006 rows /9.950 cost-role cases /18 mutations. Shared code
`d1503ce` giữ R074/R075: 1.006 old rows/summaries exact; producer 19,237 s /review 14,132 s.

Catalogue **80 records /58 policy-model versions /25 native /9 controls**;
R076/R077 có thêm component revisions reviewed_not_retained, chưa account policies hoặc
challenge-qualified. Goal active; source pilot không thêm policy version.
R078/R079 đã gác; R080 economic registered/source pilot only. Không own2025+ /broker /new provider.

[R075 recovery](research/US500-OVERNIGHT-REVERSAL-RESULTS-20261109.md) giữ v1
failure/v2 frozen-source admission. Guard `748b9d9` chặn missing input/forged
null hash; 4 actual source admissions không đổi, không repin old snapshots.
R074/R075 negatives và [NYFX conditional](research/NY-FX-GAP-SCENARIOS-RESULTS-20261109.md)
negative giữ nguyên; [strict FX annual N/A](research/NY-FX-PAIRED-LATENCY-RESULTS-20261109.md)
không bị clear bằng conditional model.

Private root `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`;
`execution-v1/index-consensus-components-v1/` giữ latest result/review;
`us500-euopen-source-pilot-v1/` giữ pilot R080, chưa economic output.
`execution-v1/index-paperwindow-tick-source-v1/` giữ full intake;
`index-paperwindow-tick-review-v2/` là corrected source view;
`index-paperwindow-components-v2-corrected1/` là economic result/review hiện hành.
Old source-reviewv1/economicv2 giữ lỗi US500Q2/Q4, không dùng verdict đó.
Mọi jobs terminal, không cần poll/resume lại. `index-closing-tick-calibration-v1/` giữ pilot;
`index-restofday-components-v1/` giữ economic books/rows/diagnostic/status;
raw ở existing `source-hour-cache-v1/`. Preflight stdin SyntaxError trước import
đã giữ failure/script v2. Trader `83731fc8`, runtime/global config không đổi;
repo source-transformations reference đã cập nhật/audit theo quarter correction.
Không migration/xóa raw. [Data/retrieval review](research/AGENT-DATA-RETRIEVAL-20261108.md)
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

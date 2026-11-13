# Current context — Naqex Workspace

13/11/2026 · `RESEARCH: ACTIVE_STAGE0_H1 · REVIEW: PENDING · DOC: RESUMABLE`.

## Việc hiện tại

**Lượt mới được owner mở:** [XAUUSD H1 Stage-0](research/XAUUSD-H1-STAGE0-PROTOCOL-20261113.md),
3 recipe cố định (Asian breakout/H4-trend H1 reclaim/momentum), BUY/BOTH views,
Development2022–23 +seedNov2021; không giá2024–26 hoặc bot SL/TP/account replay.
Rawcounts BOTH2022/23:103/107,116/136,61/85; chưa markout. Primary8h/24h/8h,
đo thêm4/8/24/48h; financing proxy20/40USD/lot weekdays22UTC,Wed×3, target chưaverified.
Job `execution-v1/xauusd-h1-stage0-20261113`, một downloader đang thu2286hours,
reuse616/new1670; status/log/deadline có trongjob. Branch `codex/xauusd-h1-stage-zero`.
Đây là campaign mới được giao, không phục hồi các B1 đã hủy hoặc tự bật Goal.

**Chiến dịch cũ đã đóng theo owner:** [STRATEGY-E2E](research/CHALLENGE-CANDIDATE-CAMPAIGN-V2-20261108.md).
Owner chốt No-Go XAUUSD B1, hủy lượt chưa dùng; EURUSD B1 cũng đã hủy.
PR74 đã merge `f0aadae`, nhánh cũ đã xóa. Không mở biến thể, batch, holdout
hoặc goal mới. C1/C2 chưa đạt, chưa có ứng viên challenge; đóng chiến dịch
khác đạt mục tiêu lợi nhuận. AppGoal kiểm khi chốt sổ=null.
[Stage-0](../.agents/skills/strategy-qualification/references/validation-gates.md#stage-0-unconditional-markout--scale-screen)
là chính sách mới cho nghiên cứu sau này; không chạy hồi tố hoặc tự mở lại.
Các checkpoint và backlog bên dưới giữ làm bằng chứng lịch sử.

**PR69 đã merge, chuyển sang thiết kế từ ràng buộc:** mergeSHA`920b48a`,
nhánh`codex/gold-eurusd-portfolio` đã xóa local/remote. [R043fixture](research/GOLD-R043-REGRESSION-FIXTURE-20261113.json)
đóng băng source/evidence: `CADENCE_OR_SAMPLE_SHORTFALL` + `PROP_TIMEFIT_REJECTED`;
dừng tối ưu challenge, giữ làm regression khi có correctness/sourcecompatibility need.
[B2report](research/GOLD-CONTINUOUS-B2-20261113.md) giữ720conditionalpaths,
36tests/7parity,120stresscached30,81s;0nhóm hoàn tất2vòng trong24tháng.

**Checkpoint mới — Scale & Horizon Audit, chỉ Development 2022–2023:**
PR73 đã merge `f1fa995`, nhánh cũ đã xóa local/remote.
[Báo cáo](research/XAUUSD-SCALE-HORIZON-AUDIT-RESULTS-20261113.md) /
[JSON](research/XAUUSD-SCALE-HORIZON-AUDIT-RESULTS-20261113.json):
ma sát median0,3486USD/oz chuẩn,0,7486stress; slip chiếm53,43% median.
772/813tínhiệu loại phí; SLrawmedian1,958USD/oz, sàn liên tục≈5,935,
fillsmedian7,02. Giữ cùng37fills tới18UTC vẫn stress−211,86USD;
14fills SL6,5–8 tới18UTC:1TP/6SL/7right-censored. Median toàncohort chưa xác định.
Rawmarkout18UTC meanstress+0,365USD/oz, dayclusterCI[−0,845;+1,731], chưa edge;
không bác mọi tínhiệu M15. **Owner đã chốt No-Go/hủy B1**, không dispatch.
B0 vẫn ECONOMIC_FAIL + CADENCE_OR_SAMPLE_SHORTFALL,
PROP_UNMEASURED. 10fixtures/2sourceguards/153passage/2.401markoutchecks đạt;
23.829.464ticks chỉ2022–23, không2024design/2025–26giá/ASTRA/broker.
Privatejob `execution-v1/xauusd-scale-horizon-audit-20261113/attempt-1` completed;
branch audit đã merge/xóa ở PR74; Traderpin/VIWIP giữ nguyên.

**Bằng chứng kế thừa — XAUUSD Intraday B0/A0:**
PR72 đã merge `7ee9ace`; nhánh `codex/intraday-funnel-audit` đã xóa.
Owner hủy EURUSD B1, không chuyển quota. [Kết quả XAU B0](research/XAUUSD-INTRADAY-B0-RESULTS-20261113.md)
/ [JSON](research/XAUUSD-INTRADAY-B0-RESULTS-20261113.json): chỉ A0, Development2022–23
và historicalvalidation2024. Raw399/414/390 → fills24/13/30; stress
+156,13/−425,93/−451,15USD. ECONOMIC_FAIL + CADENCE_OR_SAMPLE_SHORTFALL;
PROP_UNMEASURED, strictfunded còn calendar/targetspecblocked. Không A1/B1.
30.403.243ticks đã kiểm;135.281phútOHLC khớp sau3sourcecorrections trướcoutcomes,
giữ originalcache/failedviews/snapshot.11fixtures +134scenario-trade bridges,
2.035.213floatingmarks self-audit đạt; không independentagentreview.
Privateattempt `execution-v1/xauusd-intraday-b0-20261113/attempt-1` completedconditional;
registration và source-snapshot-v2 đóng băng. Branch cũ đã merge/xóa ở PR73;
Traderpin/runtime và VIWIP giữ nguyên;2025–26giáclosed, không ASTRA/broker.

**Bằng chứng kế thừa — audit Development EURUSD:** PR71 đã merge
`7d29ce4`; nhánh `codex/eurusd-b0-study` đã xóa local/remote. Owner gác EURUSD B0
với `CADENCE_OR_SAMPLE_SHORTFALL` + `DATA_PATH_INCOMPLETE`; prop vẫn unmeasured.
[Audit phễu](research/EURUSD-FUNNEL-AUDIT-RESULTS-20261113.md) / [JSON](research/EURUSD-FUNNEL-AUDIT-RESULTS-20261113.json):
chỉ EURUSD2022–23,517zones→62ngày/67signals→24fills;455zones không confirmation.
43costrejects có medianSL6pip, cần median9pip theo spread/lotfloor.
NO-GO dispatchB1; owner đã hủy lượt chưa dùng, không chuyển quota sang Gold.
[Card XAUUSD Intraday B0/A0](research/XAUUSD-INTRADAY-B0-PROPOSAL-20261113.md)
đã được owner duyệt và thực thi theo protocol mới dẫn ở trên. M1timestampquality2022–24 cho10/11/12ngày
thiếu đoạn>15phút, không gapnộiphiên>15phút; chưa certify calendar/Ask/tick.
Không EURUSD2024diagnostic hoặc giá2025–26; GoldA0 là scope được duyệt riêng.

**Bằng chứng B0 đã được kế thừa:** PR70 đã merge `0a8542ba`, nhánh
`codex/prop-target-envelope` đã xóa. [Protocol B0](research/EURUSD-B0-PROTOCOL-20261113.md)
và [registration](research/EURUSD-B0-REGISTRATION-20261113.json) khóa duy nhất
EURUSD H1→M15 breakout/retest: Development2022–23 + historicalvalidation2024.
Nativecost/sizing + observedtickpath. [Kết quả B0](research/EURUSD-B0-RESULTS-20261113.md)
và [JSON](research/EURUSD-B0-RESULTS-20261113.json): 13/11/6 lệnh ở2022/23/24,
stressmodel +22,01/+864,84/+12,59USD;95pre-costsignals,65costrejects.
CADENCE_OR_SAMPLE_SHORTFALL;2023 có sourcegap54,54phút lúc giữlệnh,
DATA_PATH_INCOMPLETE. Strictfunded còn BLOCKED_BY_CALENDAR/PROP_UNMEASURED;
không gọi conditionalnet là edge, fullpathDD hoặc khả năngchallenge.
Không EURUSDB1/GoldA1 hoặc risk0,40%. Privateattempt:
`execution-v1/eurusd-b0-20261113/attempt-1`: completedconditional,17fixtures,
60scenario-trade checks/19.482bar parity; giữ frozenattempt/reviews, không rerun
unchangedbatch. Numericalcheckpoint `d33d917`; postrun chỉ sửa writer/reviewguards.
[Prop Target Envelope](../.agents/skills/strategy-qualification/references/validation-gates.md#prop-target-envelope--profile-owner-ngày-13112026)
là ownerdesignprofile, khônguniversalstandard/officialFTMOrule hoặc runner đãenforce.
F/Rplan ưu tiên≤10%,trần12%;cadence≥60/năm ưu tiên120;25–40netR0/năm là dảikhởiđầu.
Planning12tháng cần50R0 ở0,30% hoặc37,5R0 ở0,40%;6tháng cần gấpđôi. DD15R0
không bảo đảm Daily; giữ daily<2,5%/staticloss<6,5%,strict6% làdesignaspiration.

Trần4alpha versions mới toànchiếndịch;B0+tốiđa1diag,A0+tốiđa1diag chỉdựphòng,
khôngreset priortrialhistory hoặcdispatchA tựđộng. Dev2022–23 vàhistoricalvalidation2024
đều previouslyexposed.2025–26 **CLOSED**, chưa chứng nhậnglobalcleanOOS; khôngđọcgiá.
ExactEURCatalogue13 gác,khôngportfolio. US500overlaypaused; chưapayout/candidatechallenge.
Không còn branch audit cần giữ sau khi merge; không gửiASTRA,
broker/ordercalls hoặcđổiTraderpin/runtime. Publichistory2022–24 đã cache theo grantA0.
VIWIP vàotherownedworktrees giữ nguyên. Không Goal/skill mới hoặcglobalconfig.
[Hồ sơ Bước1–2](research/STRATEGY-STATUS-AND-CANDIDATE-DOSSIERS-20261112.md)
giữ taxonomy/gap/testdesign; đề xuất US500overlay cũ đã được owner gác.

Research mở rộng US500/EURUSD và cách dùng cả năm engine đã được khảo sát.
[Báo cáo chiều sâu/engine/milestones](research/STRATEGY-DEPTH-ENGINES-AND-MILESTONES-20261112.md)
đề xuất US500 chính/EURUSD phụ (80/20 công sức), một hypothesis mỗi lane;
FX trước hết rà oldevidence/readiness, chưa numericalprotocol mới. Đây là
đề xuất phân bổ, không tự đổi exactmethod hoặc bật nhiều broker runtimes.

Owner bổ sung: [lọc feasibility sớm](../tooling/ai-engines/STRATEGY-WORKFLOW.md#lọc-độ-phù-hợp-trước-khi-triển-khai-sâu)
trước code sâu/financialbatch; reuse/count-only khi thiếu cadence. Bản có edge
được xét sizing khác nếu stressDD/prop cho phép;0,25% chỉ baseline, chưa đổi risk thật.

**T1 US500 lịch sử vẫn chưa freeze card mới**, không tự chạy study sau hậu kiểm: hypothesis →
H1bias/clock/carry → M15zone/available_at → setup → trigger → risk/entry/exit.
US500/intraday/Standard là scope trước đợtA; lượt hiện tại ưu tiên GoldSwing
continuous/EUR economics/portfolio theo chỉ thị mới, không tự mở US500overlay.
Đề xuất chính là confirmedM15level→break→retest, giữ MA-arm comparator;
đây chưa là exactrecipe đã được owner chốt. [Research/spec gaps](research/H1-M15-ZONES-AND-AI-VALIDATION-20261112.md)
và [oldB/C spec](research/US500-MULTITIMEFRAME-DRAFT-20261111.md) dẫn luật cũ.

Owner đã chỉnh rõ H1→M15; không tự chuyển sang thống kê20ngày/market khác
ngoài phạm vi research mở rộng vừa giao; numeric mới vẫn cần protocol riêng.
R120 làM15laneA, R121 mới là counterpart cóH1. Bias cũ là closedcashH1close
soSMA20; trước10:30 cócarryphiên trước. Không giả đó là nativeMT5H1 hoặc
manualstructure đã được xác nhận. Zone cũ là nến hồi quanhMA, không OB/FVG.

## Bằng chứng nghiên cứu cần kế thừa

- [Catalogue](research/STRATEGY-CATALOGUE-20261107.md):123historicalrecords/
  88versions/53native, cộng scopedstudies; không đếm chúng là independentedges.
- [R120 savedreview](research/US500-R120-SAVED-REVIEW-20261112.md):15lệnh/3năm,
  stress+48,87USD trên3sổreset10k; cadence142/157tuần vắng, giữ researchphụ.
- [TC01 same-clock](research/US500-SAME-CLOCK-RESULTS-20261112.md):673signals,
  endpointstressâm3năm;park exactcomponent, giữnegativehistory, không lanechính.
- [BR01/RS02 diagnostics](research/US500-CONTINUATION-DIAGNOSTIC-RESULTS-20261112.md)
  giữnegative/unknowns; không quét tiếp ATR/channel/exitgrid để cứu.
- [Recent8setups](research/US500-RECENT-SCREEN-RESULTS-20261112.md):2025selection,
  RS01/RS07 đã2026diagnostics; fullnetN/A doheldgaps. [Gap probe](research/US500-RECENT-GAP-RESULTS-20261112.md)
  chưa khôi phục phút thiếu; khôngdrop/ffill. Exposure/permission tùy protocol.
- GoldR043/FX/portfolio và các nhánh khác ở [researchindex](research/README.md)
  và [backlogQ1–Q12 của task](research/CHALLENGE-CANDIDATE-CAMPAIGN-V2-20261108.md#những-việc-xét-sau-đã-đưa-vào-task),
  không tự resume từ “bước tiếp” lịch sử.

Privateevidencebase `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`.
Giữ failedattempt/raw/seals/snapshots. Reuse khi đúngbinding; sửa luật là trial
mới, sửa bug chỉ rerun affectedscope. Không nối annualreset thành CAGR hoặc
pricecomponent thành accountPnL. Dataset đã xem không tự thành cleanOOS.

## Đọc theo phạm vi và quyền

| Việc | Authority / đường đọc |
|---|---|
|Task nghiên cứu hiện tại|TaskSTRATEGY-E2E → đúngstage → protocol/results/artifacts; [workflow](../tooling/ai-engines/STRATEGY-WORKFLOW.md) giữ phương pháp|
|Trader source/UI|[ProductPlan](trader/PRODUCT-COMPLETION-PLAN.md) → [entrypoint](trader/EXECUTION-ENTRYPOINT.md) → ledger; không thay bằng researchplan|
|Runtime/MT5/Paperclip|[Operations](../tooling/ai-engines/OPERATIONS.md), đúngruntime skill/owner; reconcile jobs/unknown submissions trước restart|
|Context/skills|[Lifecycle](CONTEXT-LIFECYCLE.md), [maintenance](../docs/development/SKILL-MAINTENANCE.md); không globalconfig/manager mới|
|Project khác|AGENTS/README của đúngrepo; không sửa/commit WIP VI Dubber hoặc restart integration từ audit này|

Auditdoctor đọc được4integration sources đúngpin/license; configuredPaperclip
health endpoint unavailable. Không kết luận mọi runtime hỏng, không tự start/
restart trong audit. Broker/target account/production chưa được acceptance.
Lượt mới đã có fixed-trade M1diagnostic được owner giao; không strategyjob mới,
holdout2025–26, install hoặc lệnh broker. Không promote/runtime từ kết quả này.

Ngoài nativePaperclip task/runstate và existingreceipts không tạo tracker/UI
cạnh tranh. Research/plan không cấp OrderCheck/OrderSend/account/provider/
paid/deploy/delete quyền mới. Giữ đúng authorization/accountscope khi tớiT7–T9.

## Lịch sử và khôi phục

[Snapshot trước audit](archive/2026-11-12-strategy-e2e/CURRENT-CONTEXT.before.md),
[campaign trước audit](archive/2026-11-12-strategy-e2e/CAMPAIGN-V2.before.md) và
[manifest](archive/2026-11-12-strategy-e2e/MANIFEST.json) giữ trạng thái/nextactions
cũ; chỉ đọc khi truy why/regression. OriginalGit`2b52c79763b1653ea9cf96dba40ce5eaafa3e341`.
Các archive cũ hơn vẫn được giữ; ưu tiên task/stage hiện hành để resume.

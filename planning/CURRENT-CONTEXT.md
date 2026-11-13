# Current context — Naqex Workspace

13/11/2026 · `WORK: ACTIVE/PARTIAL · REVIEW: SCOPED · DOC: RESUMABLE`.

## Việc hiện tại

**Một task chính:** [STRATEGY-E2E: chiến lược tới challenge/payout](research/CHALLENGE-CANDIDATE-CAMPAIGN-V2-20261108.md).
Owner yêu cầu rà hệ thống/workflow và gom mọi bước, kể cả việc xét sau, vào
một task. Audit/plan không là strategy accepted. C1/C2 chưa đạt; chưa có
ứng viên challenge. AppGoal vừa kiểm=null; không tự bật lại.

**B2 đã hoàn tất, chờ owner review trước merge:** [Gold ledger/rolling2010–2024](research/GOLD-CONTINUOUS-B2-20261113.md)
và [số liệu/hashes](research/GOLD-CONTINUOUS-B2-RESULTS-20261113.json). Sửa adapter
cashreset khi thiếuquote;36fixtures đạt,7directcentparitycases đạt.308potential
entryepisodes mỗi risk giữ causalflat/exit; không chỉlọcglobaltrades.60quarterstarts
×2risk125/200×3swapdeclared×Original/BUYOnly=720conditionalpaths đã chạy.
**0nhóm hoàn tất2vòng trong24tháng.** Stress40/40,risk200:Original1/60,
BUYOnly3/60 modeltwo-step; median7,22/14,53năm, chỉ1/60 mỗi bản giữinternalbuffer.
Risk125stress:Original0/BUYOnly0two-step. LongOnly là1exposeddiagnostic, chưaOOS.

PhaseB720paths178,58s;đo riêng120Original/stress30,81s saupreparecache. Coldprepare
vàbuildước110s từartifacttimestamps; không dùng16–22h forecast cũ nhưbenchmark.
Oldslowbaseline dừng ở≈440vìentrycostbreach handler, khôngclaim720oldnewparity.
RawM1/source/failedattempts/coverage giữ nguyên; no2025–26/provider/broker calls.
Cashanchor/dailyclock luôn tiến; NO_FRESH_QUOTE_AT_RESET khácchứngminhfullsurvival.
Modelpass không là certifiedFTMO/candidatechallenge. Actualtargetcost và
fundedwithdrawalcontract còn thiếu; chưapayoutseries hoặcstableincome.

**Owner chốt gác exactEURUSD Catalogue13; không ghép portfolio.** ĐợtA vàB1
ở[researchindex](research/README.md), [B1report](research/GOLD-CONTINUOUS-B1-RESULTS-20261113.md)
giữ history/oldhashes. CanonicalseedNov2009 thay100H4;cashanchorvspricequality và
rewardearliesteligibility đãtách. Internalcapdaily<2,5%/staticloss<6,5%,peakDDriêng.
US500overlay vẫnpaused. Mộtbranch/PR69, khôngmerge hoặcgửiASTRA; VIWIP/pins/runtime
giữ nguyên. Chưa tự mởoptimizationgrid/nhánhstrategy mới. C1/C2 vẫnchưađạt.
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

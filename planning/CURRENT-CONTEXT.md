# Current context — Naqex Workspace

12/11/2026 · `WORK: ACTIVE/PARTIAL · REVIEW: SCOPED · DOC: RESUMABLE`.

## Việc hiện tại

**Một task chính:** [STRATEGY-E2E: US500 H1–M15 tới challenge/payout](research/CHALLENGE-CANDIDATE-CAMPAIGN-V2-20261108.md).
Owner yêu cầu rà hệ thống/workflow và gom mọi bước, kể cả việc xét sau, vào
một task. Audit/plan không là strategy accepted. C1/C2 chưa đạt; chưa có
ứng viên challenge. AppGoal vừa kiểm=null; không tự bật lại.

**Lượt hiện tại: hậu kiểm Bước1–2 đã được owner phê duyệt**, chuẩn hóa nguyên
nhân dừng và contract Alpha–Sizing–Exit. [Hồ sơ Gold +5US500 / gap và testplan](research/STRATEGY-STATUS-AND-CANDIDATE-DOSSIERS-20261112.md)
giữ kết quả, JSON dẫn xuất và blockers. Không financialrun/runner mới;
Bước3–5 chưa bắt đầu, chờ owner chọn scope/đối tượng. C1/C2 chưa đạt.

Research mở rộng US500/EURUSD và cách dùng cả năm engine đã được khảo sát.
[Báo cáo chiều sâu/engine/milestones](research/STRATEGY-DEPTH-ENGINES-AND-MILESTONES-20261112.md)
đề xuất US500 chính/EURUSD phụ (80/20 công sức), một hypothesis mỗi lane;
FX trước hết rà oldevidence/readiness, chưa numericalprotocol mới. Đây là
đề xuất phân bổ, không tự đổi exactmethod hoặc bật nhiều broker runtimes.

Owner bổ sung: [lọc feasibility sớm](../tooling/ai-engines/STRATEGY-WORKFLOW.md#lọc-độ-phù-hợp-trước-khi-triển-khai-sâu)
trước code sâu/financialbatch; reuse/count-only khi thiếu cadence. Bản có edge
được xét sizing khác nếu stressDD/prop cho phép;0,25% chỉ baseline, chưa đổi risk thật.

**T1 chiến lược vẫn chưa freeze card mới**, không tự chạy study sau hậu kiểm: hypothesis →
H1bias/clock/carry → M15zone/available_at → setup → trigger → risk/entry/exit.
Giữ US500/intraday, FTMO CFD2-StepStandard chính, risk thấp; The5ers nhánh riêng.
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
Chỉ sửa docs/skill workflow; không numericaljob, holdout mới, install hoặc lệnh.

Ngoài nativePaperclip task/runstate và existingreceipts không tạo tracker/UI
cạnh tranh. Research/plan không cấp OrderCheck/OrderSend/account/provider/
paid/deploy/delete quyền mới. Giữ đúng authorization/accountscope khi tớiT7–T9.

## Lịch sử và khôi phục

[Snapshot trước audit](archive/2026-11-12-strategy-e2e/CURRENT-CONTEXT.before.md),
[campaign trước audit](archive/2026-11-12-strategy-e2e/CAMPAIGN-V2.before.md) và
[manifest](archive/2026-11-12-strategy-e2e/MANIFEST.json) giữ trạng thái/nextactions
cũ; chỉ đọc khi truy why/regression. OriginalGit`2b52c79763b1653ea9cf96dba40ce5eaafa3e341`.
Các archive cũ hơn vẫn được giữ; ưu tiên task/stage hiện hành để resume.

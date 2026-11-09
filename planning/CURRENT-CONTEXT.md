# Current context — Naqex Workspace

09/11/2026 · `WORK: ACTIVE / REVIEW: REVIEWED-PARTIAL / DOC: RESUMABLE`.
Owner đã yêu cầu tiếp tục và cho tạo Goal mới; tool xác nhận `active`.
Đích: ứng viên đủ bằng chứng để đề xuất challenge FTMO/The5ers và quy trình
được kiểm/sửa theo C1/C2 của [campaign v2](research/CHALLENGE-CANDIDATE-CAMPAIGN-V2-20261108.md).
Không reset trials, negatives hoặc exposure; chưa có ứng viên challenge.

## Việc hiện tại

- [R086 FOMC price momentum](research/US500-FOMC-PRICE-MOMENTUM-RESULTS-20261109.md)
  đã terminal/reviewed:32books/256cases;net cơ sở2019+60,55/2022+151,62USD/unit,
  stress−63,33/−14,66 nên không qua gate.126mốc/252rawsideinputs đủ;250raws
  reuse+2tailGETs. Sourcefinalprogress vượt180s được giữfailure/recoveryreceipt,
  khôngrerun;economics0,665s/review0,314s.86records/58versions, chưa challenge.
  Publictarget-index funding/spec đãrà, thiếu exactaccountpackage nên chưa
  repricing; chỉ mở lại khi có source mới. Tiếp method/source admission cơ hội
  khác; không fee0/horizon/lookbackgrid cứu outcome hoặc lặp publicpages.
- [FOMC source review](research/FOMC-SURPRISE-SOURCE-RESULTS-20261109.md):
  historicalsource pin2024/359rows có1extra2024row đãquarantine/exposure;
  16focus/240cells reviewed nhưng không intraday-known-at/accessproof.
  [Stock residual](research/RESIDUAL-REVERSION-METHOD-ADMISSION-20261109.md)
  đã đọc fullmethods; deferred universe/PIT/actions/hedge/program/cost, chưaPnL.
- Rà workflow hữu hạn đã xong: audit workspace/Trader 0 errors/warnings;
  16 repo skill entrypoints có vai trò riêng, 76 local links hợp lệ. Chưa có
  lý do gộp/xóa thêm skill hoặc thêm framework. Chi tiết tại
  [skill maintenance](../docs/development/SKILL-MAINTENANCE.md).
- [GitHub workflow gọn](../tooling/github-workflow/README.md) đã merge;
  source Trader/pin workspace ở `930fa768`, workspace `aec89c5` trước lượt này.
  Một đợt liên quan dùng chung branch/PR; issue theo nhu cầu, bảo vệ nhánh giữ.
- [NHP/Fury desk research](research/PAID-EA-MARKET-REVIEW-20261109.md) chưa
  chứng minh exact executable/preset hoặc source ownership. Không mua/cài EA.
  Bài học áp dụng: kiểm chi phí từ joint quotes, SL/risk/account-wide exposure
  và timing thực thi; không suy ra logic vào lệnh đóng mã từ quảng cáo.
- [R083WTIsettlement](research/WTI-SETTLEMENT-COMPONENT-RESULTS-20261109.md)
  đã40books/88datesfullroles,strict/endpointviewsidentical;2019stress−6,298,
  2022stress−1,297USD/researchbarrel. Gác exactrecipe, khônghour/feegrid.
  Cache-onlyconsumer6,330s,0requests;khôngjobnền. R082giữnegative/unknown.
- Chuyểnsang [TokyoUSDJPYmethod](research/TOKYO-FIX-METHOD-ADMISSION-20261109.md):
  importerflow/paydates,9:55reference/10hbankannouncement; liênquanR020/R021,
  khôngindependentedge hoặcretailalpha từdealerprofit. OfficialholidayCSVđãcó,
  chưaallbank/PITcalendar. [Sourcepilot](research/USDJPY-TOKYO-SOURCE-RESULTS-20261109.md)
  đủ61roleminutes×2dates/26.980fields,1,226s;0returns/strategy,khôngjobnền.
- [R084 USDJPY component](research/USDJPY-TOKYO-COMPONENT-RESULTS-20261109.md)
  đã terminal/reviewed:32books/139dates,1.899.620rawfield checks, không gap.
  Mua chính stress2019−125,18/2022−142,93USD trên100knotional; không đạt.
  Lịch phụ dương và diagnostic bán sau fix dương, chỉ là follow-up flags.
  Source+consumer145,106s, không còn job R084; chưa account/prop/edge.
- [R085 extension protocol](research/USDJPY-POSTFIX-EXTENSION-PROTOCOL-20261109.md)
  đã freeze `55fe25d`; [kết quả](research/USDJPY-POSTFIX-EXTENSION-RESULTS-20261109.md)
  terminal/reviewed:240books/15years gồm13năm mở rộng, chỉ6/13năm stressdương,
  2/4blockprimaryâm;gác exactrecipe. Primary625lượt mới chỉ+204,25USD/100k
  notional, chưa SL/account/prop/OOS/forward.12.402.580newfields và139old days
  reuse;calendarcrossyear sửa trước quotes, failure giữ. Source+consumer22phút07s,
  không còn job. [Residual-reversion admission](research/RESIDUAL-REVERSION-METHOD-ADMISSION-20261109.md)
  đã rà và deferred như trên, không mặc định USstock→FX/index
  hoặc tiếp Tokyo grid. Không khôi phục R065 đã gác chỉ để cứu outcome.

## Bằng chứng nghiên cứu cần kế thừa

| Lát | Kết luận / bước tiếp |
|---|---|
| Catalogue | 86 hồ sơ / 58 policy-model versions / 25 native / 9 controls; [mechanism plan](research/MECHANISM-FIRST-EXECUTION-20261109.md). Component/biến thể không tự là edge độc lập |
| FX NYMA4 | [Conditional results](research/NY-FX-GAP-SCENARIOS-RESULTS-20261109.md) âm ở hai năm; strict annual vẫn unknown. Không đổi clock/SL/risk để cứu exact recipe |
| Gold R043 | [Cost admission](research/GOLD-TARGET-COST-ADMISSION-20261109.md) và [loss diagnosis](research/SELECTIVE-LOSS-DIAGNOSIS-RESULTS-20261109.md): funding/spec đích chưa verified; không zero-swap hoặc rerun để cứu outcome |
| R080/R081 | [EU-open](research/US500-EU-OPEN-COMPONENT-RESULTS-20261109.md), [conditional](research/US500-INVENTORY-CONDITION-RESULTS-20261109.md): known net âm, giữ unknowns, gác exact recipes |
| EIA | [Date census](research/EIA-RELEASE-DATE-CENSUS-RESULTS-20261109.md): 103 ngày, actual/PIT exceptions chưa verified; normalclock có thêm archivedPDF proof. [Oil pilot](research/OIL-EIA-SOURCE-PILOT-RESULTS-20261109.md) thiếu USO16:00 Open; chưa bulk/economic admission |
| Phân rã PnL | [Hierarchical attribution](research/HIERARCHICAL-PNL-ATTRIBUTION-20261109.md) đã review; chỉ phân tích sâu survivor/near-miss có câu hỏi |

Private evidence root: `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`.
Các jobs trước đã terminal; không đợi hoặc poll job cũ. Source mới cần đọc
status/progress/result của đúng attempt, giữ pins/raw/seals/failures. Không
rerun unchanged history hoặc thu lại 16 triệu ticks đã kiểm chỉ để đổi observer.

## Đọc theo phạm vi và quyền

| Việc | Cửa vào |
|---|---|
| Research / quyết định | [Index](research/README.md) → protocol/results/private artifacts đúng chủ đề |
| Ý tưởng → kiểm định → vận hành | [Strategy workflow](../tooling/ai-engines/STRATEGY-WORKFLOW.md), skills theo stage; không agent/task riêng cho mỗi hàng |
| Trader source / UI | [Product Plan](trader/PRODUCT-COMPLETION-PLAN.md) → [entrypoint](trader/EXECUTION-ENTRYPOINT.md) → ledger; [UI plan](trader/TRADER-UI-MASTER-PLAN.md) |
| Runtime / MT5 / Paperclip | [Operations](../tooling/ai-engines/OPERATIONS.md), runtime skill; reconcile writer/jobs trước restart; Paperclip giữ native task/run/report |
| Project khác | README/AGENTS của đúng repo; task này không khởi động VI Dubber hoặc integrations khác |

Source, local runtime, broker acceptance và edge là các trục khác nhau.
Holdout2025+, OrderCheck/OrderSend, account/provider mới, chi phí, migration/
xóa dữ liệu và production giữ gate riêng; research report/Goal không cấp quyền.
Tối ưu chỉ khi có bug/nút thắt thực tế; không thêm DB/RAG/UI/skill quản lý mới.

## Lịch sử và khôi phục

[Snapshot trước resume](archive/2026-11-09-workflow-resume/CURRENT-CONTEXT.snapshot.md)
và [manifest original bytes/hash/base](archive/2026-11-09-workflow-resume/MANIFEST.json)
giữ các trạng thái Goal và chi tiết cũ. Link snapshot dùng base gốc `planning/`.
[Context lifecycle](CONTEXT-LIFECYCLE.md) giữ quy trình; không đọc archive mặc định.

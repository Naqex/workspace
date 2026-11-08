# R035 GBPUSD/AUDUSD: chưa đủ cơ sở cointegration, chưa chạy bot

Theo [protocol](RELATIVE-VALUE-METHOD-ADMISSION-20261108.md), commit`4bbcaa3`
trước outcomes; implementation`214471e` và5fixtures đạt trước read8sourcebooks.
**Không giữ exactpair/formations để thiết kế economic pilot lượt này.** Chưa
accountpolicy mới hoặc challenge candidate; Goal C1/C2 vẫn active.

## Kết quả dễ hiểu

Hai cặp tiền cùng có USD không có nghĩa chênh lệch giữa chúng chắc chắn quay
về cân bằng. Mình kiểm điều kiện này trước khi viết bot mua một bên/bán bên
kia. Dữ liệu đủ theo lịch đã chốt, nhưng phép kiểm không đạt filter.

| Formation | Đủ lịch /expected | OLSbeta | Cointegrationt | p-value | Đăng ký |
|---|---:|---:|---:|---:|---|
|2018|259/259|0,8498|−2,6025|0,2358|Không đạtp<=0,05|
|2021|260/260|0,4185|−2,5217|0,2696|Không đạtp<=0,05|

Khôngreject null no-cointegration **không chứng minh** không có equilibrium
hoặc không thể kiếm tiền theo cách khác. ADFlevels khôngreject, differences
reject cho2legs/2windows; không chứng minh I(1). Beta khác hai năm là mô tả,
chưa formalbreaktest. Không mở pair/lag/window/OLSorientationgrid để cứu.

## Đã kiểm và giới hạn

| Lát | Bằng chứng |
|---|---|
| Source/roles |8immutableGBP/AUDBidAskbooks, hash/identity/year/proof/count;16UTCsourceH1Close known17UTC. 519calendarrows/1.038BidClosechecks, khôngmissing/crossed ởsample |
| Upstreamgap |60books cũ có AUDAskJan2013missing/30crossedhours2010; không tự nâng thành fullhistoryadmitted. Formation2018/21 không gặp blocker đó |
| Before numeric |5tests: syntheticcointegration/independentrandomwalk, clock/grid/crossed/missingcalendar, noholdoutyear, degeneracy/nonfinite |
| Statistics |Fixed yGBP/xAUD log, EngleGrangerconstant/maxlag1/autolagNone. SeparateDecimal80log/OLS/residualADF review8coefficient/SD/tstatchecks, tolerance1e−11, t1e−8 |
| Negative controls |5mutations price/date/stat/falseauthority/hash reject; calendar vẫn giữ ngày thiếu nếu có |
| Inference scope |MacKinnonp/criticalcurves cùng pinnedstatsmodels, không independentstatisticalimplementation; legADF chưa separateDecimalreview. Cùng agent/provider, không independenthuman/modelsignoff |
| Economics/prop |0trades/PnLbook/brokercalls; chưa sizing/SL/legsfill/margin/fees/prop/OOS. Statisticalpass cũng không tự chứng minh edge |

Không đọc pairPnL2019/22 hoặc ownholdout2025+. External literatureaggregates
2025/26 đã thấy, không giả blind với literature. Không import NBERstockcode/
data hoặc dùng stockpaper làm bằng chứng FXcointegration.

## Capability, data và hậu kiểm

Product/bundled/MLvenvs thiếu statsmodels. Tạo isolated
`.runtime/research-statistics`, không đổi product/global/MCP/service.
OfficialPyPIwheelsonly:statsmodels0.15.0,numpy2.5.4,scipy1.18.1,pandas3.1.1;
13dependencies. Metadata/license/publicSHA đã so, không`.pth`/`.data/scripts`
hoặcsdistinstallscript; không fullsecurityaudit của mọi dependency. Offline
install bằng [hashlock](../../tooling/ai-engines/requirements-statistics.lock.txt),
smoke5tests trên nhu cầu thật đạt. Explicit`result_object=False` giữ pinnedAPI,
không suppress mọi warnings. Lock choWindowsCPython3.12/amd64, không universal.

Manifest snapshot giữ wheel-audit và upstreamstattools/adfvalues source;
sample/source/protocol/results cóhash/known-at/exposure/units và attempt riêng.
Không rawrewrite/migration hoặc dùng searchpassage làm numerical source.

| Phase | Wall /CPU thực đo | Quyết định |
|---|---|---|
| Driverpreflight/hash/sampling/statistics |2,243s /2,047s|Reuse8books, khôngdownload/fulltickparse |
| Source+Decimal/statreview |1,901s /CPUkhôngđo|Đủfixedscope, chưaPnL/replay |
| Install/code/research |Chưa timerđầyđủ|Không gọi4,14s là toànquytrình hoặc nativebacktestspeedup |

PID20132/reviewerterminal0, source/rawhash không đổi. Chưa bottleneck cầnGPU/
Rust/parallel hoặc skill/framework mới;4existing workflows đủ. Khôngcleanup
data; rollback capability chỉ bỏ isolatedruntime khi khôngjobowned.

## Evidence và bước tiếp

Private root`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`:
`execution-v1/fx-pair-formation-v1`:2samples/2diagnostics/inputbindings/
preflight/manifest/source-snapshot/result/review/status/events. Driver
`run-fx-pair-formation-v1.py`, reviewer`review-fx-pair-formation-v1.py`.
ResultSHA`aded6681197ededa72a5d66913072af5afc63b6e6fc4b3c263fe12c8407e332e`;
reviewerSHA`ada8fd2527e8d0c35367f5bcde9b2b871a0d4eacd2f948bc9983dec79fcf26ca`.

R035 từ chưa auditedmethod/data sang exactformation không đạtprecondition;
candidate_idnull/implementations[], vẫn61records/44versions. Chưa tradingbot.

Tiếp methodadmission **scheduledmacro-event equity premium**, khác surprise
newsR027/28 và fixed-hourunconditionalflow. [Methodfollow-up](RELATIVE-VALUE-METHOD-ADMISSION-20261108.md#hướng-kế-scheduled-macro-event-không-nhầm-surprise-news)
giữ nguồn/câu hỏi; chưa registeredPnL hoặc edge. Cần reconcile literature,
announcementclock, published-beforecalendar, source/cost/holding trước recipe.

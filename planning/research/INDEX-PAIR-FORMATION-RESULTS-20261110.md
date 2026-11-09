# R092 S&P–Nasdaq: chưa đủ căn cứ cho fixed equilibrium bot

10/11/2026. [Protocol](INDEX-PAIR-FORMATION-PROTOCOL-20261110.md) freeze
`f522477` trước numericaloutcomes; [source](INDEX-PAIR-SOURCE-RESULTS-20261110.md)
đãreviewed503dates. **Không giữ exactfixedformations để thiết kế economic
pilot lần này.** Không có trades/PnL/accountpolicy hoặc challengecandidate.

## Hiểu đơn giản

Hai chỉ số cùng thị trường Mỹ không bảo đảm chênh lệch luôn quay lại một
mức cân bằng cố định. Mình kiểm điều kiện đó trước khi viết bot mua bên này,
bán bên kia. Nguồn đủ, nhưng cảhai formationwindows chưa qua bộlọc đãkhóa.

| Formation | Đủ ngày | OLSbeta | Cointegrationt | p-value | Gate p≤0,05 |
|---|---:|---:|---:|---:|---|
|2018|251/251|0,659581|−1,953362|0,552720|Không đạt|
|2021|252/252|0,827925|−2,225777|0,411114|Không đạt|

Các gate beta/residual/ADFlegs khác đều đạt theo registeredheuristic.
Khôngreject nullno-cointegration **không chứng minh không có equilibrium**, và
không loại mọi intraday/time-varying/nonlinear pairstrategy. Chưa cóprofit
number nên không quy thất bại cho spread/funding; đây là statisticalpriority
gatefail, khác economicsnegative hoặc sourcefailure. Không mởwindow/lag/
orientation/Kalman/SVMgrid để cứu version này.

Orientationy=ln(USA500sourceBidClose),x=ln(USATECHsourceBidClose), cùng16UTC
H1Close/known17UTC. FixedOLSconstant/Engle–Grangerlag1/autolagNone; mỗileg
ADFlevelnonreject/difference reject không chứng minhI(1). Pvaluekhôngđược
điềuchỉnhcho91historicalrecords hoặc dùng như xác suấtbotkiếmtiền. Related
R035/R067giữnegative;92records không là92independentstrategies.

## Đã kiểm

- Existing5formationtests đạt trước numericalrun, body2,961s: syntheticknown
  equilibrium/randomwalk/degenerate/nonfinite vàsource/date/grid/missingguard.
  Chạy vì newconsumer/mapping, khôngfulltestunchangedproduct.
- 1.006sampleBidClose đối chiếu8sealedsourcebooks, calendarcensus riêng từ
  holidays/weekday, exacttime/knownat/sourceidentity/sidepresence/crossed.
  Sample/source/manifest/code/runtime/version/lock/parentreviewhashes giữ.
- SeparateDecimal80log/OLS/intercept/SD/residualADF tstat đủ8checks ở hai
  formations, tolerancecoefficients/SD1e−11/tstat1e−8. Pvalue/criticalcurves
  vàlegADF dùngcùngpinnedstatsmodels, khôngindependentinferenceimplementation.
- 6actualmutations price/date/count/authority/statistic/hash bịreject.
  Sameagent/provider, không independentfeed/human/modelreview hoặcC1C2full.

| Phase | Wall | CPU |
|---|---:|---:|
|Formationproducer (gồm libraryimport/pins)|1,866s|1,750s|
|Source/sample/Decimalreview|1,875s|1,844s|
|Tổng hai phase|3,740s|3,594s|

Đây không là toàn thời gianresearch/code/Git hoặcnativebacktestspeedup.
Sourcephase trước47,373s; tổng source+statisticsworkerphases51,113s, không
gồm test/research/manualreview. Khôngjobnền, producer/reviewerexit0,
0newGET/returns/PnL/broker/model/holdout2025+ tại statisticalstep.

## Dấu vết và quyết định

Privatecampaignbase, `execution-v1/index-pair-formation-v1/`:manifest/snapshots/
source/calendar/sample/diagnosticseals/result/review/progress/events.
Scripts `run-index-pair-formation-v1.py`, `review-index-pair-formation-v1.py`
reuseexisting `fx_pair_formation` numericalcore vàDecimalreviewer; legacylabels
chỉmaptườngminh ở adapter, không dùng FXsource/grid hoặcbrokercontract.
ResultSHA`e05bfdbf0f9170ef3c061b3eb60cd9cd4dc8dedcd1c5c86298bb2dc71f9221f0`;
reviewSHA`fe8f96b046d3c2d664a04920497c0c630c285eb0ef1dbdbb913a39fc3a9c1464`.

Catalogue92records/58policy-modelversions/25native/9controls. R092làformation
probe, không bot hoặcaccountpolicy; C1/C2chưađạt/Goalactive. Gác exactpair/
fixedformation, không yêu cầu mọi nghiên cứu khác phải cointegrated.
Không rerun503samples/96sources để đọc lại verdict. Tiếp primarymechanism có
đường causaldata/cost/risk rõ hoặcmaterialsurvivorblocker cóevidence mới;
không rút một sidewinner/fee0/lotgrid từ cohortđãxem.

Hậu kiểm: earlyformationfilter tránh triển khai2legexecutionkhitínhiệuchưa
đủcơsở. Reusehelper/runtime/rawseeds giảm công lặp; chưa bottleneck thực đo
cầnRust/GPU/parallel/skillframework hoặc sourcecleanup. Giữ exploratory
exposure/negatives vàsource packet để reuse khi **có giảthuyết mới đủ căn cứ**.

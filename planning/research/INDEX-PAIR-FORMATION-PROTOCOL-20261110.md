# S&P–Nasdaq: fixed formation trước thống kê, chưa trading recipe

10/11/2026. [Nguồn](INDEX-PAIR-SOURCE-RESULTS-20261110.md) đã reviewed503dates;
[methodadmission](INDEX-PAIR-METHOD-ADMISSION-20261110.md) không nhận exact
paperrecipe. Đây là ownlinearformationhypothesis dự kiếnR092, relatedR035/R067,
không sửa các negative đó hoặc gọipair mới làindependentedge.

## Phép kiểm khóa trước outcomes

- Hai formationwindows calendar2018/2021, exact503samples từ acceptedsource,
 16UTCH1Close known17UTC. y=ln(USA500sourceBidClose), x=ln(USATECHsourceBidClose).
 Không reverseorientation, đổiwindow/hour/lag/transform hoặc thêmpairs.
- Reuse `fx_pair_formation.diagnose` cho numericalvectors, khôngFXsampler
 hoặcFXgrid. Explicitmap legacylabels gbpusd→usa500idxusd(y),audusd→usatechidxusd(x)
 trongoutput; actualstoreddata giữ đúnginstrument. Isolatedstatisticsruntime
 statsmodels0.15.0/numpy2.5.4/scipy1.18.1/pandas3.1.1 vàhashlockđãcó, khônginstall.
- OLS y=a+bx, Engle–Grangerconstant/maxlag1/autolagNone; eachlegADFlevel và
 firstdifference constant/maxlag1/autolagNone. Tstat/pvalue/criticals/beta/
 residualSD/AR1 đềuphảifinite/nondegenerate; source/split/known-atgiữ.
- Retain **chỉ để thiết kế economicpilot** nếu cả2windows: cointp≤0,05,
 beta0,1..10, residualSD>0, mỗi leglevelADF p≥0,05 vàdifferenceADF p<0,05.
 Đây là heuristicprefilter kếthừa, khôngpvaluechứngnhậnI(1)/meanreversion hoặc
 thửmọichiếnlượcphảipasscoint. Multiplehistoricaltrials/pairfamily giữrõ;
 passkhônglàeconomicedge,failkhôngchứngminh khôngmọi nonlinearrelationship.
- Missing/crossed/sourcebindingfail →inconclusivedata, khôngfit dropna.
 Mộtwindow khôngđạt→gác exactfixedformation, khôngthreshold/lag/Kalman/SVMgrid
 đểcứu. Chưasizing/stop/twolegfill/funding/SL/account/prop/OOS/forward.

## Kiểm chứng và lưu

Trước marketstatistics: fixedsyntheticcointegrated/randomwalk/degenerate/
nonfinitechecks của existing5testmodule; chỉ rerun bộ này vì consumer/mapping
mới, khôngbroadtestunchangedengine. Source/rawđãreview khôngfetch/reparsefull
history lại; rehash acceptedresult/review/samples/seals, đối chiếu503dates/
prices với8exports. Rawbinding giữ để trace, khôngrawcopy/cleanup.

SeparateDecimal80log/OLS/residualADF đốichiếu coefficients/intercept/SD1e−11,
tstat1e−8; p/criticalcurves và legADF cùng pinnedlibrary, khôngindependent
inferenceimplementation. Actualprice/date/stat/authority/hashmutations reject.
Sameagent/providerphảirõ. Khônggọiselfreviewlàindependentreviewer.

Private `execution-v1/index-pair-formation-v1/`:nooverwrite/onewriter/PID/
progress/events/CANCEL/deadline60s,protocol/scripts/helper/runtime/packages/
source/seals/pins/snapshots trước diagnostics; mỗiresult có source/protocol
lineage/timing/verdict/limits. Catalogue tăngR092record khi đã thực hiện
hypothesis, khôngaccountpolicyversion hoặc bot.0network/broker/model/2025+.

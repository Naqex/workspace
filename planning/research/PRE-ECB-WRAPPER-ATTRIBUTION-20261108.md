# Giữ14:00: tách stop, khối lượng và coverage — 08/11/2026

Owner giao tiếp từ [clockresults](FIXING-CLOCK-TRANSFER-RESULTS-20261108.md).
Đợt này là matched-trade attribution, không đổi parentstrategy, không nâng
readiness hoặc mở Goal C1/C2 đã clear. Không chạy lại catalogue hoặc simulator.

## Câu hỏi và exposure

Parent exact `eurusd-h1-pre-ecb02ny-14berlin-atr14x1p5-r025-v1` đã gác sau
frozen13yearcostscreen.2019/2022 đãexposed; số tổng và firsttrade đã xem khi
thiết kế attribution. Có unitcomponent(noSL/constant1lot) dương nhưng parent
SL/riskweights stressâm. Đây là câu hỏi phát sinh từ outcomes, không cleanOOS
hoặc preregistereddiscovery ban đầu. Giữentry02NY/exit14Berlin/costs cũ.

## Inputs và commonmask đã khóa trước tính mới

-Catalogue13annualresult/completedseals2019/2022 và2costs; kiểmconfig/source/
  sha/matrix, cùngactualparent. Quotecomponent/sourceproof/reviews của
  `fixing-clock-transfer-v1`; phải exactbind `result.json` với raw/Fraction và
  linkage reviews. Không sửa seals/pins hoặc chạy lại financialproducer.
-Một trade/day, SELL, exactentrytime/entrybid vàlot của parent. Ngày component
  thiếuentry/exit hoặc parentthiếutrade không được biến thành0PnL hoặc drop
  ngầm: partition matched/excluded, guard duplicate/mismatch.2019Dec25 dự kiến
  excluded vìmissing14:00quote; ngoàicommonmask giữ parentPnL, khônginventexit.
-NoSLendpoint đã có firstat/after14:00≤60s. Không đọcrawđể sinh entry/exit mới.
  ParentSLfill vẫn H1modeled, không nhận là first-crossingtick cho toànbook.
-Commission2,50USD/lot/side, slip0/reference hoặc0,00002/side stress, sameUSD/
  100kcontract, funding theo originalrow; parentcurrentcase đãknown0/flat,
  nếu cófunding/open/pending ngoàiscope phải fail/inconclusive, không tựlược.

## Phân rã số học, không tạo chiến lược bỏSL

Trên commonmask, `q_i` là lot quan sát tại entry, `r_i` netUSD/standardlot nếu
đến14:00 khôngSL, `s_i` netUSD/standardlot theo exitSL/strategy của parent.
Kiểm quantitygrid/costmath trước normalize; giữ exactFraction khi tính.

| Cell | Công thức | Ý nghĩa |
|---|---|---|
|A|mean(q)×sum(r)|Equal-lot normalization, cùng tổnglot; mean(q) tínhhậunghiệm, không executablepolicy hoặc riskconfig|
|B|mean(q)×sum(s)|Parentexit, equal-lot normalization|
|C|sum(q×r)|NoSLendpoint theo **lot đã quan sát**; không được gọi làaccountbacktest|
|D|sum(q×s)|Actualparentprice-net trêncommonmask, phải khớp artifacts|

Đường1: D=A+(C−A)+(D−C): weightingkhôngSL rồi parentexit ởweightsđãcó.
Đường2: D=A+(B−A)+(D−B): parentexitởequalweight rồi weighting.
Interaction=D−C−B+A phải được báo; không tự nhận attribution causal/unique.
Unweighted/lot-weighted meanpips ghi riêng để không nhầm giảm lot là mấtedge.
D+excludedparent=fullparentnet khi flat/funding0. Không sum khácunits hoặc
gọi per1lot thành PnL10k/risk25USD. Commonmask2019cònpathunknown nên noSL
portfolio carry/reentry/DD vẫn chưa được mô phỏng hoặc cấp quyền.

Nếu C dương mà D âm thì có câu hỏi stop/exit trongscope; nếu C âm mặc dù A
dương thì weightingcũnglàvấnđề. Kết quả này không cho phép tự bỏSL, tănglot,
đổiATR hoặc chọn riêngtrade/ngày/regime sauoutcome. Chỉ ghi câu hỏi tiếp có
căn cứ; không thresholdsearch hay promote từ counterfactual.

## Bounded rawstop check và review

Chọn **tối đa4parentreference stop_loss trades sớm nhất/năm trong commonmask** theo
entrytime, trước đoattribution; không chọn theo lời/lỗ. Cùngdates ởstress nếu
có cùngentry/stopdistance. Đọc/hashraw đúngseal, chỉ parseprice trongselected
windows. Dựng SELLstop=ceil((entry+registereddecisiondistance)/0,00001)×tick;
kiểm firstobservedAsk>=stop và fillintervalsource, lưuovershoot soH1level.
Đây là8paths/subset, không annualbiasbound hay fullnativeprop/replay.

Focusedfixtures: hand-calculated2×2/interaction, uniformweights, scaleinvariant
means, malformedq/Nan/duplicate/sourceentrymismatch, missingexitpartition và
identityD+excluded. Actual4books/everymatchedtrade được kiểm lại bằng reviewer
khácimplementation, cùngagent label. Cópositive/negativecontrols, không épwinner.

Status/phase/log/finite deadline180s, terminalfailure vẫn ghi khicancel hoặc
deadline; outputmới`execution-v1/pre-ecb-wrapper-attribution-v1`. Reuse existing
report/helper/costcore; khôngengine/riskowner/framework mới. Exactsource/
protocol/fixtures/inputpins snapshottrướccompute; nooverwrite/noautomaticretry.
Kết thúc lưutable,failures/limits,decision/nextaction ngoài chat. Không mở2025+,
OrderCheck/OrderSend,newaccount/paidprovider/challenge/production.

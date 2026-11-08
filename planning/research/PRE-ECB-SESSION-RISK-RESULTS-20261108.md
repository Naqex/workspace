# R056 có lãi trong coarse book, chưa qua tiêu chí ưu tiên tick

Thực hiện [protocol](PRE-ECB-SESSION-RISK-PROTOCOL-20261108.md), commit
`ca907a4` trước outcomes, implementation `39f9b69`. Một variant mới dùng
stop2×RMS20phiên quákhứ, ngân sách25USD/lệnh, entrySELL02NY→14Berlin.
**Không đạt frozen retention** vì2/4stressblocks âm; không tự hạ tiêu chí
hoặc chạy SLgrid để cứu. Có lãi trong scope coarse, chưa challenge-ready.

## Kết quả dễ hiểu

Continuous researchbook10.000USD,2010–2022,khôngresetnăm, khôngcompoundrisk.
Lotfloor0,01,tick0,00001,contract100k,declaredleverage30/fees/funding giữ rõ.
Đây là H1stop-level approximation, không nativefirstcrossing/prop/broker.

| Chỉ số | Phí chuẩn | Phí cao |
|---|---:|---:|
|NetUSD toàn13năm|+1.535,95|+1.078,12|
|Equity cuối / floating|11.535,95 /0|11.078,12 /0|
|Lệnh đóng|3.171|3.171|
|Nămcohort dương|11/13|10/13|
|Lệnh thắng /thua/hòa|1.609/1.558/4|1.597/1.570/4|
|Funding debitUSD,âm làcredit|−0,16|10,20|
|Lệnh tệ nhất/tốt nhất,USD|−24,96/+96,35|−24,99/+96,15|
|Cashoverallhalt tại9.500USD|Không|Không|

| Stressblock | NetUSD |
|---|---:|
|2010–2012|−38,34|
|2013–2015|+506,94|
|2016–2018|+631,64|
|2019–2022|−22,12|

Netdương và≥9/13nămdương,≥2.000trades,khôngcashhalt đạt; **all4blockspositive
không đạt**. Không đổi định nghĩa pass theo tổng dương. Kết quả này không
bác bỏ cảhọfixing, cũng không là bằng chứng một SL khác sẽ giải quyết được.
ParentATRH1vẫnparked; không chỉnh oldoutcomes hoặc coi2costs là2edges.

Ngân sách25USD làplannedloss dướimodel, khôngguarantee khi gap. Trong mẫu
chưa có realizedloss>25USD, nhưng H1levelfill chưa đo nativegapovershoot.
Giá trị diagnostic: minH1conservativeequitybound9.862,98/9.839,38USD,
H1closeDD3,32%/3,53%; **chưa independentlyreplayed các diagnosticfields này**,
không coi là maxintradayDD/fullFTMOloss hoặc actualbreach. Core cash/trades,
features/fills/cohort và financialsummaries đã có review bên dưới.

## Causality, missing và đối soát

-3.391plannedweekdays:3.171opened/cost;220known-at-entryskip do thiếu20history
  liền trước, gồm warmup đầu2010. Không dùng futureexit để chọn eligibility,
  không tìm20ngày xa hơn hoặc bùprice0 cho ngày thiếu.
-Khối lượngstress0,01–0,11lot, tính lại theo distance/fees; mọi plannedrisk≤25.
  Giữ phaseentrytime/sequence/stop/lot và historyknown-at. Không dùng MAEp95
  trong dữ liệu đã xem làm multiplier hoặc referenceprice tương lai.
-197SL/2.974scheduledexits mỗi cost.8scheduledexits trễ>60s,7trades có
  missinghourinterval,6fundingevents/cost. Lệnh đã vào không bị xóa vì thiếu
  futureexit; giữ đến stop hoặc quoteđầu sau exit, có carry/fees. Cuối mẫuflat.
-Native loader kiểm13yearrawSHA/cachebytes/payload/runtime/producer/count/
  order/grid, mộtsourcepass/mỗiyear dùngcho2costs. Không đổi source/runtime
  đangpin của các bài cũ hoặc sửa activeproduct/livepath.
-4focusedfixtures đạt:causal20dayRMS/missing/future,currentpriceindependence,
  cost-awarelot/stop,delay/carrygapvượtbudget,funding/openmark/cashhalt.
-Reviewcode khác khôngimportproducer:floatRMS+Fractionmoney/sizing/roundstop,
  firstcoarseAskcrossing vàscheduledexit,6.342trades/6.782decisions,cash/noforce
  reset/26cohorts,12fundingevents vàfrozenretention khớp.5mutationsreject:
  wrongstop/quantity/net,dropdelayedexit,wrongfeature.
-Reviewattempt1 thiếu import`timedelta`,dừng trướcseal; lưufailure, sửa riêng
  reviewer vàrerunreview3,946s, khôngrerunnumeric hoặc đổioutcomes. Cùngagent/
  provider,khácimplementation;không independenthuman/model/feed hoặc rawtick
  firstcrossing. Sourceextrema chung chưa chứng nhận fullpath/no gaps.

## Performance và quyết định engineering

| Lát | Thời gian thực đo |
|---|---:|
|Toànnumeric/source/ghi13yearcheckpoints|41,053s wall /40,406sCPU|
|Feature/tradepath/Fraction/cashreview sauimportfix|3,946s|
|Compute trên mỗi cachedyear,2costs|khoảng0,27–0,39s; exacttimers trongresult|

Sourcehash/load/validate chiếm phần lớn; numericbook không có bottleneck cần
GPU/Rust. Không bỏvalidation để nhanh, không benchmarklại batchkhôngđổi.
Yearcheckpoints làevidence/accountstate, **chưa claim CLIresume equivalence**.
Không thêmservice/RAG/UI/skill. Existingresearch/qualification/retrospective
skills đủworkflow; chưa có lýdo thêm một lớp quản lý.

Private`execution-v1/pre-ecb-session-risk-v1` dưới campaignroot giữ config/
manifest/source-snapshots/plans/peryear-checkpoints/source-receipts/books/
result/events/progress/review vàreview-attempt1-failure. NumericPID25216/
session12249,reviewđãterminal0.0network/broker/modelcalls,không2023+/holdout.
ResultSHA`3c8734ec330696509504e95774cbd1faf96bc4c813152588ffcbb618d648fe50`;
reviewerSHA`6e9165abb6f5fcdbb86753ffba152a594a14f58f78fdecccc4c8d048067e2a1f`.

## Bước tiếp và không suy quá bằng chứng

Không ưu tiênfullnative13yearreplay choexactversionđãkhôngđạt frozenblock
gate. Không mở2023/24wrapper chỉ để làm sumđẹp hoặc sửa thành đạt10%nhanh.
Priceedge14/15years không bảođảm wrapper phùhợp challenge/time-fit. Chiến
lược có thể có lời nhưngmỏng/chậm; chưa có prospective/OOS/targetcontract.

Tiếp khảo sát **chuyển giao cơ chế sang thị trường khác với budget danh mục
chung**, thay vìretuneSL. QDMmetadata read-only hiệnchỉ có EURUSD/vàng; chưa
cóGBPUSD/AUDUSDhistorycached. NativeDukascopylibrary đã có H1monthsource,
phù hợp admissionpilot hữuhạn: kiểm mapping/time/side/sourcepadding trước
outcome mới. Hai USDquotedpairs giúp giữ đơn vịUSD/cost conversion rõ; chung
USDfactor nên không coi là2edgesđộc lập hoặc tự nhânbudget theo symbols.
Chỉ sourceadmission trước; không tự nhận pricecoarse giống actualfills.

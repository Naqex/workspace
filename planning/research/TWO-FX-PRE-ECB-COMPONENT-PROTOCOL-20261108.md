# Chuyển giao cơ chế PreECB sang GBPUSD/AUDUSD: trước outcomes

Source[historyreview](FX-H1-HISTORY-RESULTS-20261108.md) đãreviewobservedvalues,
fulljointadmission vẫnfalse. Thínghiệm này chỉ **endpointprice/costcomponent**
trênOpenroleshợplệ,giữunknown/crossed trongdenominator;khôngaccount/SL/prop.
KhôngsửaR056,khôngtunegiờ/stop hoặcnhânrisk theoasset.

## Hai hypotheses riêng, không là hai independentedges

| ID | Primary | Control |
|---|---|---|
|R057|SELLGBPUSD02:00NewYork→14:00Berlin mỗiweekday|BUYcùngendpoints|
|R058|SELLAUDUSDcùngclock|BUYcùngendpoints|

BoC2021-48cơchếG9/pre-fixUSDdemand đãreview,nhưng2pairs/costs/clock/retailfeed
không làpaperreplication;chungUSDfactor,cóselectionhistoryvớiEURUSD trước đó.
GBP/AUDđượcchọn vìUSDquote/mapping/sourcefeasibility,cốđịnh trướcPnL mới.

- Toànbộweekdays01Jan2010–31Dec2024đượcgiữ.2010–22và2023–24báo blockriêng
  nhưng khônggọiblindOOS;giá nguồn đãđượcđọc trongadmission,relatedtrials và
  publishedsample đãexposed.2025+đóng. Khôngđổiwindow theooutcome.
- ExactOpenH1tạitargetUTCquaIANAclocks,sideBid/Askđúngsource/month/year.
  Bid≤Ask vàpricegrid/positivefinitephảihợplệ cho **Openfield**;crossedClose
  đượcgiữquality nhưngkhông tựrepair hay dùng làm priceOpen. Khôngasof/carry/
  missing→0. Missingentry,missingexit hoặccrossedOpen cóstatusriêng.
- Entryeligibility chỉtừentryOpenrole;missingfutureexit khônglọcentry.
  Componentchỉtínhnetkhiđủhaiprices,giữeligible-but-unresolved riêng.
  AskAUDJan2013unknown;AUD28Apr2010exitcross giữunresolved,khôngspread0.
- H1Openlàpriceproxy trong`[hour,hour+1h)`,khôngactualjointtick hoặcfirstquote
  ≤60s. Outputkhông có actualfilltimestamp,khôngso như nativeEURUSDticks.
  Quyếtđịnhcalendar trướcnominalentry,không dùng futureclose/price đểchọnside.
- Per1standardlot,contract100k,accountUSD/quoteUSDconversion1. Observedside
  H1Open Bid/Askproxy;commission2,5USD/lot/side,slip0(reference)/0,00002stress.
  SharedCostModel/netround2;financing0 vìwindows trướcdeclared22UTCrollover,
  khônghistoricalFTMO/The5ersverifiedcost hoặcactualholding.1pip=10USD/lot.
  Không lấyperlotPnLthành10kaccountreturn hoặcbudgetowner.

## Retention, reports và verification

Mỗiprimaryriêng đángđăngkýrisk/accountreview khi stresssum>0,≥10/15years
stressdương,cảblocks2010–12/13–15/16–18/19–24stressdương,mỗiyear≥200resolved.
Khôngchọnoppositecontrol thayprimary sauoutcome;khôngbuộccả2assetpass hoặc
cộngtwopricepaths thànhaccountportfolio. Missing/crossedsource vẫnlimitation,
retainedchỉlàưu tiênbướckiểm,tuyệtđốikhôngfullhistory/native/edgecertificate.

Báo eachasset/view/year/cost:allweekdays/entryeligible/resolved/unavailable/
crossed,statuscounts,sum/mean/min/max/netwins/losses/top5positive share,
blocks/positiveyears,tổng2010–22/2023–24. Haiasset/cost/control khônglàtrial
độc lập;giữmọinegatives. Không tínhstatsblind hoặcpassprobabilitytừnămxanh.

Reusefinancialpricehelper/Fractionoracle/canonicalclocks,không thêmengine.
Runtimefixtures trướcsố thật:constantprice/BUYSELL/spread/cost,unknownentry/
futureexit,crossedOpen vàfieldroleisolation. Bind60books+sourcequality/
review/rawreceipt/protocol/helper/runtimeSHA trướccompute;khôngdownloadlại.
Rootmới1writer,deadline120s/PID/status/events/failure/CANCEL.0network/model/
broker/holdoutcalls trongnumeric. Separateimplementation cùngagent kiểmmọi
row/clock/side/metadata/Fractionnet/summary/counts/retention và5mutations.
Nếuretained,đăngkýbudgetchung/risk/sizing/margin/path/tick/OOS/prop/time-fit/
forward/handover trướcqualify;GoalC1/C2khôngcomplete từcomponent.

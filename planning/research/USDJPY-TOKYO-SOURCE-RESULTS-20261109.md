# USDJPY Tokyo source: đủ fixture, chưa chạy chiến lược

[Protocol](USDJPY-TOKYO-SOURCE-PROTOCOL-20261109.md), commit`1b9f516`
trước4requests. Hai dates2019-01-10/2022-07-15 chọnwinter/summer vànominal
paydates trướcquotes, khôngtheoPnL. ExistingDukascopy1.51.1, khôngnewprovider/
account, cài mới, own2025+, broker/modelcalls. Không returns/strategy mới.

| Fixture | Roleminutes09:25–10:25JST | 4endpoints | Grid |
|---|---:|---|---|
|10/01/2019|61/61pairedBidAsk|Đủ/noncrossedOpenClose|0,001JPY/USD|
|15/07/2022|61/61pairedBidAsk|Đủ/noncrossedOpenClose|0,001JPY/USD|

Rawdelta/Fraction/native full26.980OHLCVfields khớp; sameTokyo00:25–01:25UTC
khôngDST, rawday/grid/order/pricebounds/paddingexplicit phânbiệt. Piperule
USDJPY0.01 không lấyEURUSD0.0001; sourcepoint0.001 khácpip, notMT5verified
contractspec. SideOpenM1interval khôngjointquote/fillableTTM; noohlcaverage
đểgiảmidextrema. 6mutations price/time/padding/missingrole/wronggrid/authority
bịchặn. Sameagent/feed,khôngindependentfeed/certificate hoặcbankfixprices.

Source4requests0,732s; reviewer0,494s/0,484sCPU; tổng**1,226s** khôngresearch/
code/Git. Noerror/retry/fullhistory. Progressđãcompleted_reviewed,khôngjobnền.
Reuseexistinghelpers, khôngGPU/framework/skill mới. Fixturekhôngchứngminh
mọipayday/lịchbank/cleanOOS/edge/SL/equity hoặcpropfit. Catalogue83/58giữnguyên.

Private`execution-v1/usdjpy-tokyo-source-pilot-v1/` trongcampaignroot có
config/manifest/pins/source-snapshot/rawcache/exports/seals/result/review/
progress/events. ResultSHA
`a7ed8202f3a9fed8474ef12e6976ebe5b24aee870504ca0ba63966dc63db0f00`;
reviewerSHA`0be7f6b9fe61f5b6a6eab5e27dc762b82f074107c2182a331dfbfbd2be51954b`.

## Bước tiếp có điều kiện

[Primarymethod](TOKYO-FIX-METHOD-ADMISSION-20261109.md) đủcơsởđểđăngký một
ownrule thử nghiệm; chưa được suy outcome từpaperbankprofit. Chốt nextprotocol:
Japanesebusinessdays/holidaybanks vàGotobishiftconvention; pre-fixBUYUSDJPY
window lấy từhedgingmechanism, post-fixSELLchỉdiagnostic nếuđăngký; nohourgrid.
CurrencyconversionUSDbase/JPYquote/feeUSD/chênhlệchpip vàsourcecoverage phải
chốttrước outcomes. Giáquákhứ2019/2022 khôngcleanOOS,selectionhistorygiữ.

Nếubankcalendar chưa đủ, report declaredcalendarmodel/diagnosticcounterpart,
không tựđóng dấuPIT. Khôngtựdùngcommercialpreset/EA hoặcmuaquỹđểthử. Chỉ
sau frozencomponentđạt mới xét historyrobustness/riskwrapper/prop/timefit/
prospective theo C1/C2, không tạo thêm sourcefixture không cóconsumer.

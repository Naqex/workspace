# USDJPY Tokyo source pilot — đăng ký09/11 trước fetch

Theo [method](TOKYO-FIX-METHOD-ADMISSION-20261109.md). Source-only, chưacandidate
hoặcnumerictrials. Twodates **2019-01-10 và2022-07-15** đềuweekday/paydaynominal
10/15, khôngnationalholiday trongofficialCSVđãlưu. Chọnwinter/summer đểkiểm
TokyoUTCoffset bấtbiến, khôngtheoquotes/PnL. Khôngclaimdatecensus/PITbankcalendar.

4requestsUSDJPYBid/AskfullUTCdayM1,existingDukascopy-node1.51.1/helpers,
rawpricegrid0.001/pip0.01,volumesmillions,ignoreFlatsfalse/nativepaddinggiữ.
SourceUTCdaycóJapan09:25–10:25cùnglocaldate,khôngfetchpreviousyear hoặc2025+.
NoWAF/auth/account/provider/paid/runtime/broker/modelchange; retry0/cumulative
failurecap1/deadline180s/CANCEL/onewriter/nooverwrite. Privateoutput
`execution-v1/usdjpy-tokyo-source-pilot-v1/` trongcampaignbase.

Đây làcandidate**geometryenvelope**, khôngentry/exitstrategyđãchọn: paired
minutes09:25–10:25JSTinclusive61bars; 4endpoints09:25/09:54/09:56/10:25. Hai
khoảngtrướcvàsau09:55 khácexactfixingfill. Opens làquotestronginterval1phút,
chỉknownsauinterval; noexacttick/executablespread hoặcTTMpricecertification.
Sourcegate đủ61roleminutes/cả2sides/cả2dates, endpointsnoncrossedOpen/Close;
thiếu/crossedunknown, khôngfill/dynamicendpoint hoặcđổidates đểđạt.

ReusegetCachedM1/native validate/buffer/cache; pins/scripts/protocol/lock/native
vàsnapshot, mỗioutputsealvàrawcachehash. IndependentFractiondelta decoder so
fullnative/sourceOHLCV; explicitvolume0giữ, paddingkhôngsource. Grid đúng
JPYkhácEURUSD, unitvàTokyo00:25/01:25UTCcheck; wholeUTCdaydiagnostic không
đòifull1440rawbars nếu đúnbindinggaps. Sourceunknown khôngthành0PnL.

Mutations nativeprice/timestamp/padding vàmissingrole/wronggrid/authority sai
bịchặn; no numericalreturns. Results/timing/progress/events/bindings giữ ở
output/receipt. Nếuđạt chỉđủsourcepilot đểđăngkýhistory, không edge/prop/OOS,
newaccountpolicy/candidatecount. Nếukhôngđạt giữfailedgate, khôngbulkfetch.

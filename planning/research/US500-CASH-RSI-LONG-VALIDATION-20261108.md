# Frozen RSI3+IBS cash daily — retrospective2013–2024 review

Kế thừa [corrected2022–24](US500-CORRECTED-REPLAY-20261108.md): RSIstress
+21,09/+6,43/+77,77USD,59entries/58closed,2024openmark. Đủ chọn đểkiểmthêm,
khôngđủedge/challenge. GiữexactID `us500-d1-cutler3-10-40-ibs05-atr14x1p5-r025-v1`
và [rules/cost/funding](US500-DAILY-REVERSION-20261108.md),khôngtunecho2013.

12annualbooks2013–2024 riêng10k/plannedrisk25/oneposition,minlot/margin/funding
đãfreeze. First14consecutive cashTR trongmỗiannualbook chỉwarmup. **Reuse**
corrected2022/23/24 numericseals saubindingverify,khôngrerun9years đãchạy.
Chỉnew2013–21×2costs=18newrows,+9nullcontrols;rawM1unfiltered cùngprovider,
giữvolume0 nhưngkhôngcoi làexchangevolume/fillcertainty. Chỉquote-basedM1model,
ngày/SLfill/overnightpathunknownsphảibáo;khôngnativepropDDcertificate.

Source:completedyearseals củaus500-long-m1-v5;exactcachedsource/package1.51.1,
ignoreFlatsfalse. KhôngH1/D1providerownrange,không2025+ hoặcnewbroker/paiddata.
Nămđầucache2012Q4chỉcapability,khôngoutcome2012. Data2013–21 làretrospective
extension sauselectionlateryears,khôngunseenOOS,khôngindependentofpaper/trials.

Calendar:isolated exchange_calendars4.13.2/purePythonwheels/hashes/ApacheMITBSD
audit,khôngproduct/globalvenvchange. ExportXNYS2012–24,bản2022–24 khớpexact
mọisessionUTCminutesvớiofficialNYSEfrozenfiles;2018-12-05closure vàSandy2012
crosscheckofficialICE/Nasdaqannouncements. 2013–21rules từtestedlibrary,không
claimđãđọc từngofficialyear. DerivedcalendarJSON vào fixtures2013–21 cósource
provenance;khôngdùngNYSEhoursđểgiảbrokerhours. Yearholdoutguard2025vẫnđóng.

## Đánh giá trước outcome mới

- Integrity/causal/accounting/funding/mark/queue correctness trước economics.
 Missingyear/outcomefailed khôngcoi0vàkhôngloạimẫuđểđạtretention.
- Deepreview nếu totalnetdương cảcosts,stresspositive≥8/12annualyears vàtổng
 stresscủatừngblock2013–15/2016–18/2019–21/2022–24 đều>0. Heuristictrước
 newoutcomes,khôngpvalue hoặccalibratedpassprobability. Existing3positive
 triagekhôngtrởthànhđòi mọinămsauthắngvĩnhviễn.
- Báoallannualrows,open/floating/counts,gaps/fills/activityflags,meanR/trade,
 concentrationvàuncertaintyphùhợp;khôngbootstrap12annualsđểtựđóngdấuedge.
 Multipletrials/clockadaptations/historyexposuregiữrelationship,cầnreview.
- Khôngđạt thìgiữnegative/inconclusiveversion,khôngtănglot/cắtlosingyears/
 funding0hoặcchuyểnparamschođẹp. Đạt chỉeligibleđăngkýnativeindex/tick
 brokercontract/prop3–6–12month/forward/holdoutgatesriêng,khôngC1.

Worker/supervisortrướcđọcyear phảiverifyrawseals/schema/side/calendar/flag và
hashconfig/source/protocol/runtime;sourceimmutabletrongnumericjob. Outputmới,
status/events/deadline/cancel,onewriter. Reuseverifiedyear/rows,transportdelay
khôngbuộcnumericrerun;khôngchỉnhliveworker khiđangcompute.

Nguồncalendar vừađọc08/11:
[NYSE2022–24](https://ir.theice.com/press/news-details/2021/NYSE-Group-Announces-2022-2023-and-2024-Holiday-and-Early-Closings-Calendar/default.aspx),
[NYSEBushclosure](https://ir.theice.com/press/news-details/2018/New-York-Stock-Exchange-to-Honor-President-George-H-W-Bush/default.aspx),
[Sandyannouncement](https://ir.theice.com/press/news-details/2012/IntercontinentalExchange-Announces-Hurricane-Sandy-Market-Update/default.aspx),
[package](https://pypi.org/project/exchange_calendars/4.13.2/).

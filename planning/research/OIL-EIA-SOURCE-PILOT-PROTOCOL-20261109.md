# Oil/EIA source pilot: same-dayETF/CFDdata trước economic transfer

Scope từ [mechanism plan](MECHANISM-FIRST-EXECUTION-20261109.md),09/11.
Khôngsignal/PnL hoặc giảthuyết đổi giờ sauR081. PrimaryUSOpaper/mapping gaps
ở [method](EU-OPEN-AND-OIL-METHOD-20261109.md); underlyingideas tham khảo,
khôngcopy/redistribute paper/code/data. Existingprovider/library đãpin1.51.1.

## Fixture khóa trước fetch

Hai dates2019-01-09/2022-07-13 từEIAarchive, chọnmộtnămwinter/mộtnămsummer
đểkiểmNYclock, khôngchọn vìreturn. USO.US/USD=`usoususd` vàLIGHT.CMD/USD=
`lightcmdusd`, haiBidAsk/symbol/date=8requests/8rawday-sideURLs. FullUTCdayM1,
volumesnative millions/ignoreFlatsfalse/utcOffset0/formatJSON, nativeexpanded
view giữnguyên đểreviewpadding. Sourcegrid lấyrawmultiplier, không hardcode
MT5point/contract/tickvalue. ETFadjustment/roll/CFDfunding vàexchangesharevolume
unknown, không đưavolume vàoinformedtradingfilter.

So originaldeltaOHLC/volume/timestamp với nativefullview bằngexisting
`candle_source_provenance.inspect_expansion`; explicit0volume giữ, padding
không làquotes. Trongregularcashsession09:30–16:00NY báoexpected390minutes/
pairedpresence/unpaired vànoncrossedOpen/Close, khôngclaimhighlowjointspread.
Kiểm endpoints10:30/11:00 và15:30/16:00(M1Open), exactmissing giữ, không
nextquote/sort/forwardfill. Chỉcensus/geometrykhôngđọcreturnsigns hoặcnet.

Đòi cảhai asset/date có≥98%pairedcashminute và4endpointsđủ/noncrossed để
đềxuấtboundedhistoryregistration; không cónghĩa toànhistory đạt. Actualdata
mutation ởdisposablecopy phải bịchặn; raw/frozenbytes bấtbiến.8URLs strict,
nohiddenretry/WAF/auth, maxfailures1/deadline180s/CANCEL/onewriter/nooverwrite;
PID/progress/events/sourcepins/package/lockfile/snapshot/result/review/timings.
Private `execution-v1/oil-eia-source-pilot-v1/`;0broker/modelcalls/no2025+.

## Sources và các cửa chưa được vượt

[Official2019-01-09](https://www.eia.gov/petroleum/supply/weekly/archive/2019/2019_01_09/wpsr_2019_01_09.php)
và [2022-07-13](https://www.eia.gov/petroleum/supply/weekly/archive/2022/2022_07_13/wpsr_2022_07_13.php)
xácminhrelease date. Chưa lịchall2019/22/PITreleaseexceptions/actualrelease
timestamps. KhôngfallbackmọiWednesday10:30; June2022duplicatereportdates
cần1event. [USCF](https://www.uscfinvestments.com/disclosures) và
[CME](https://www.cmegroup.com/education/lessons/wti-futures-versus-etfs) xácnhận
ETFfutures/rollmapping cầnphânbiệt. Sourcefixture khôngchứngminhCFD giữedgeETF,
actualfills/SL/prop/targetcost hoặcđộđộc lập vớiindex/FXsources.

Nếuđạt: đăngkýcalendar/history/window/costmodel riêng trướcsignal/outcomes.
Nếukhôngđạt: giữgap, khôngfetchbulk hoặcnới98%đểtránhfail. Đây làdata task,
khôngcộngthànhcandidate/accountpolicy; chưađượcauto-promote/gửilệnh.

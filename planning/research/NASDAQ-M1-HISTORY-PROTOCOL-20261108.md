# NASDAQ M1 history: calendar và source admission trước daily reversion

Tiếp [method/2fixtures đãkiểm](NASDAQ-DAILY-REVERSION-METHOD-20261108.md),
không đổiR062/R061rules hoặc tính strategyPnL. Câu hỏi: có đủ explicitM1
cashbars/afterclosequotes và đườnggiángoàiphiên cho một dailyreversionpilot
liênquanR050không? Không tải history chỉ đểsearchmọirecipe.

## Calendar đã đối chiếu primary, không lấy từ outcome

Cash chart09:30–16:00America/New_York, earlyclose13:00. Reuse
`sealed_m1_review.cash_sessions`, schema`cash-session-calendar-v1`, UTC/ms.
NYSEcashcalendar làm declared UScash proxy cho nghiên cứu NASDAQCFD; không
chứng nhận targetbrokerhours hoặc exactETF/futures/CFD equivalence. Nasdaq
calendar2021/22 PDFs đã tìm ở officialindex, nhưng không coi text extraction
chứng minh màuholiday củaPDF; không dùngSIFMAbondcalendar làm equitycalendar.

Primary kiểm08/11/2026:

- [ICE/NYSE2016publication](https://ir.theice.com/press/news-details/2016/NYSE-Group-announces-2018-and-2019-holiday-and-early-closings-calendar/default.aspx):2018/19closures/halfdays.
- [NYSE2018publication2019/20/21](https://s2.q4cdn.com/154085107/files/doc_news/archive/15638cee-2935-4422-bcb4-a3733587eb8b.pdf):2019/21dates,2021Nov26earlyclose.
- [ICE/NYSE2021publication2022–24](https://ir.theice.com/press/news-details/2021/NYSE-Group-Announces-2022-2023-and-2024-Holiday-and-Early-Closings-Calendar/default.aspx):2022Juneteenth20June,Nov25halfday; noobservedNewYearholiday2022.
- [Nasdaq2018-99](https://www.nasdaqtrader.com/TraderNews.aspx?id=ETA2018-99):05Dec2018closed,specialmourning. Warmupnotoutcome, noticepublic03Dec.

Exactregisteredlists trong `nasdaq_cash_calendar.py`:2018fullclosures10 kể
cả05Dec,2019nine,2021nine,2022nine. Halfdays2018Jul3/Nov23/Dec24,
2019Jul3/Nov29/Dec24,2021Nov26,2022Nov25. Only2018/2021NovDecwarmup dùng.
Không xóa ngày thiếuquotes bằng cách tự gọi holiday; quotequality tách khỏi
calendar. Không lấy calendarstatus hoặc data cóquotes làm causalnewsfilter.

## Source windows và exposure

ExistingDukascopy`usatechidxusd`,source-onlyBid/AskM1,8books:

| Role | UTC interval,endexclusive | Calendar days/side |
|---|---|---:|
|warmup2019|2018-11-01→2019-01-01|61|
|development2019|2019-01-01→2020-01-01|365|
|warmup2022|2021-11-01→2022-01-01|61|
|development2022|2022-01-01→2023-01-01|365|

852days×2sides=**1.704rawday sources**, gồm weekend/holiday. Chỉ lấy cashdays
sẽ thiếu overnight/protectivepath, nên giữ toàn source interval và flaggaps.
ValidemptyrawJSONdays là observedemptyresponse, không inventedquotes hoặc
transportmissing; malformed/HTTPfail không tự đổi thànhempty. Fullmonth URL
enumeration đã kiểm nofetchJan2019 có31dayrequests, khôngskipweekends.

Reuse4M1rawsources từ2pilotdays nếu exacthash; không producerrebind oldproofs.
Cache`source-hour-cache-v1` chungprovider, filename/path/hash giữexact. Raw
USDindexCFDpricegrid0.001, volumemillions, noexchangevolume/adjustedtotalreturn.
Openintervalproxy, OHLCknownbarend; khôngobservedjointmid/extrema hoặc fill.
No2025+,historicaldevelopment/exposed,cleanOOSfalse;no broker/account/provider/
paidservice/package/runtime/globalconfig/newMCP. Rawprivatekhôngredistribute.

## Source execution và recovery

Reuse installeddukascopy-node1.51.1 và `dukascopy_cached_m1.cjs` unchanged,
`sourceCandlesOnly:true`,ignoreFlatsfalse,keep explicitvolume0, no decoderpadding.
Clone request trước nativevalidation vì dates cómutation. Nativebatch2URLs,
pause300ms giữa noncachebatches; onebook/time, không nhiềuwriter cho cùngjob.
Retries chỉexistingtransienthelper3attempts/request,cumulativebudget6;
auth/WAF/403/429/schema khôngretry. Drainsinflight, nohiddenfallback.

Deadline1.800s, CANCEL,PID/events/progress/logs/failure/lastsealedbook. Mỗi book
seal ngay; workerfail khôngautooverwrite/rerun completedbooks. Bước recovery
nếu cần phải bind oldsource/config/proof/raw và dùngattempt mới, khôngsnapshot
roundtrip làCLIresume. Khôngrerununchanged history đểlàmbenchmark. Preliminary
ETA chưa đo1704-sourceworkload, không hứa xong trongseconds hoặc1hour.

Driver`prepare-nasdaq-m1-history-v1.cjs`, reviewer
`review-nasdaq-m1-history-v1.py`, outputmới
`execution-v1/nasdaq-m1-history-v1` tại existingcampaignroot. Pinprotocol,
driver/reviewer/helpers/package/lock/calendars/pilotresult/review trướcfetch.
Calendarpublicsourcecaptures cóURL/date/hash/role, khôngindependentWaybackPIT.

## Source/quality review, không economics

Reuse `validate_rows`,`explicit_candles`, existingproofs; independentFraction
rawdelta decoder cho toànrawsources/mọi OHLC/volume; M1volume giữsourceprecision,
không tự áp H1round4. So hash/sourceidentity/side/time/units/order/count,
explicit/padding/volume0 và rawemptyshape. Wholecalendarbars knownafterend;
khônginventmissingminute. Check pairedOpen/Closecrossed/allpairedtimestamps,
giữ rawmissing-one-side/crossed flags; khôngclamp/spreadzero hoặc tự xóabar.

Quality tách4roles:sidebars/pairedminutes/adjacentgaps; everyexpectedcashday,
390regular/210halfday expectedminutes, source presence/crossed, barclose+1min
quoteavailability, rolling14TR/4close readiness. Không lấy390barcount chứng
minh no missingticks. Crossed outsidecash vẫn report, không fulladmissionpass.

**Admit để exacteconomicregistration** chỉ khi8books/1704rawresponses đủ và
source transforms khớp; mỗidevyear>=200cashdays đủbothsides/khôngcrossed với
afterclosequote, mỗiwarmup>=20, và cóít nhất1eligible14-consecutivecomplete
lookback/day ởmỗidevyear. Những ngày thiếu vẫn ởdenominator; không gate theo
PnL. Fulljointadmissionfalse nếu cócrossed/one-side gaps; sourcecorrectness
khácstrategyreadiness, nativeprop/tick/targetcost/OOS/forward/handover vẫn riêng.

Mutation giá/count/sourcehash/futureclock/falseauthority phải reject. Same
agent/provider, codepatharithmetickhác, khôngindependenthuman/modelsignoff.
Lưu timing/quality/bounds/nextaction. ChưaIBS/RSI/PnL hoặc policycount mới;
gatefail thì resolve data/methodgaps trước, khôngloosenfilter/cost/risk đểwinner.

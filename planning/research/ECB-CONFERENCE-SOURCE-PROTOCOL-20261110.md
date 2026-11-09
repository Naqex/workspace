# ECB conference: pilot clock và joint quotes trước tín hiệu

10/11/2026, tiếp [method](ECB-POSTDRIFT-METHOD-ADMISSION-20261110.md). Chưa
candidate/R093 hoặc economictrial; catalogue92/58giữ. SourceEUS.IDX-EUR từ
existingDukascopy1.51.1, khôngnewaccount/provider/dependency hoặc2025+.

## Fixture chốt trước requests

4dates: firstscheduledconference của2019/2022 vàfirstSeptemberconference
của hai năm đó, chọn từ lịch khônggiá:24/01/2019,12/09/2019,03/02/2022,
08/09/2022. [24/01/2019](https://www.ecb.europa.eu/press/pr/date/2019/html/ecb.mp190124~5c00d09d5d.en.html),
[12/09/2019](https://www.ecb.europa.eu/press/pr/date/2019/html/ecb.mp190912~08de50b4d2.en.html),
[03/02/2022](https://www.ecb.europa.eu/press/pr/date/2022/html/ecb.mp220203~90fbe94662.en.html),
[08/09/2022](https://www.ecb.europa.eu/press/pr/date/2022/html/ecb.mp220908~c1b6839378.en.html)
và[clockchange](https://www.ecb.europa.eu/press/pr/date/2022/html/ecb.pr220627~73acedf868.en.html)
đốichiếu event/oldnewtime. Đây retrospectivecalendarcheck, không chứngnhận
mọiPITschedulepublication hoặc actualeventend; không dựatimepageupdated.

Own relativewindows theo conferenceEurope/Berlin:
- Pre: [start−15min,start−5min), post:[start+70min,start+80min).
- Decision=start+80min, **chưatínhiệu**; simulatedentrylocator đầu tiên tại
  hoặc sau decision+60s, chỉtìm tới decision+120s inclusive. Khôngfillthật.
- Old14:30→pre14:15–25/post15:40–50/locator15:51; new14:45→pre14:30–40/
  post15:55–16:05/locator16:06. Shift15min là ownwindowadaptation sauclockchange,
  khôngpaperreplication. BerlinDST chịu trách nhiệmUTCwinter/summer.

Raw9fullUTCtickhours:2019-01-24 13/14;2019-09-12 12/13;
2022-02-03 13/14;2022-09-08 12/13/14. Fullhour exposureghi rõ, không2019/22
holdingreturns/features/PnL. Khôngswitchasset hoặc bỏdates nếudatafail.

## Cửa nguồn đã khóa

JointBidAsk/grid0,001, giữsame-msordinal vàobservedzero-volume. Không lấy
separateM1sideOpen làm jointquote. Mỗi10minwindow:ít nhất9/10phút cóquote,
firstquote<start+60s,lastquote≥end−60s, maxgapgồmhaiendpoints≤120s.
Entrylocatorphảicóquote [decision+60s,decision+120s]. Cả8windows và4locators
đủ mới admit khả năngthiết kế feature; empty/missingkhôngthànhzerochange.
Không tínhmedianchange/direction hoặc priceprofits từpilot.

Nguồnrawhour/fullnative/export/proof/seal, nofilter/carry/interpolation;
private`execution-v1/ecb-conference-source-pilot-v1/`, cachemới,0seedmặcđịnh.
9GETtốiđa,tuầntự300ms/retry0/WAFoff/failurecap1/deadline180s/CANCEL/PID/
lock/progress/events/nooverwrite. Bindprotocol/config/scripts/helper/native/
lock/calendar trướcrequests vàfinal. Nativeempty xửlýabsence,schemafail làlỗi.

Preflightsynthetic: winter/summer/newclock/straddledpostwindow,9hourcensus,
halfopenboundaries/expiryinclusive/same-ms/empty/one-twoholes/120sboundary,
knownatfuturetimestamp/grid/nonfinite. Reuse `index_tick_review.py` integer
0,001decoder vàseparateFractiondecoder pinned, calendaroracleUTC explicit.
Fullrawtimestamp/BidAsk/volume đối chiếunative, toàn4eventroles/censuses bằng
arithmetic riêng; actualprice/time/count vàfalseauthority/hashmutations reject.
Sameagent/provider, không independentfeed hoặcbrokerspec/availabilityproof.

Outputcollectorpendingreview; reviewer nói rõ từngwindow/locator/admission,
rawcounts/wallCPU/limits. Fail→giữgap,khôngrelaxcoverage hoặcđổihoursđểpass.
Pass→đăngkýfullcalendar/ownrecipe/costs trướcfinancialfeatures, khôngautopromote.
0broker/model/PnL/holdout; không thayquyền,skill/runtime hoặcphíquỹđích.

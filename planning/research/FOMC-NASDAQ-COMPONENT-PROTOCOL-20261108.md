# R062: pre-FOMC NASDAQ price component, before outcomes

Tiếp [method admission](RELATIVE-VALUE-METHOD-ADMISSION-20261108.md), Goal
C1/C2 active. Một conditional event recipe, hai exposed developmentyears và
một matched-week control. Chưa SL/accountpolicy hoặc broker authority.
Không tune NasdaqSMA, pair/lag/windowgrid hay dùng announcedpolicycontents
làm tín hiệu. Bước nhỏ này kiểm cơ chế trước chi phí xây bot/riskwrapper.

## Cơ chế và giới hạn literature

[NYFed512](https://www.newyorkfed.org/research/staff_reports/sr512.html)
mô tả pre-FOMC equity returns trong sample cũ.
[NYFed26/11/2018](https://libertystreeteconomics.newyorkfed.org/2018/11/the-pre-fomc-announcement-drift-more-recent-evidence/)
phân biệt pressconference meetings và nêu giờ14ET từ2013; đã public trước
hai năm này. [Kurov/Wolfe/Gilbert2020](https://www.skidmore.edu/economics/documents/KurovWolfeGilbert-TheDisappearingPre-FOMC-Announce-Drift-200914.pdf)
abstract báo yếu đi sau2015. [FEDS2026-023 §5.2–5.5/figure3](https://www.federalreserve.gov/econres/feds/files/2026023pap.pdf)
thảo luận evidence theo các samples/windows khác và chưa consensus cơ chế.
Không lấy một abstract làm verdict chung hoặc premium thành CFDnetprofit.

Hypothesis kiểm: scheduled-event23h BUY trên NASDAQCFD có positive net và
cao hơn cùng localweekday/hour tuần trước ở cả2019/22 trong declaredcosts.
NASDAQ100Dukascopy khácS&P500/futures/paper; exit13ET thay14ET làm adaptation,
không replication. Eventcount8/năm rất ít, chỉ có thể là sleeve nghiên cứu,
không riêng nó chứng minh time-fit3/6/12tháng hoặc passquỹ. Không tăngrisk để
bù tần suất. Rule khác news-surpriseR027/28, calendarweekdayR025 và R061trend.

## Calendar trước giá

Original public tentative schedules:

| Year | Published | Registered scheduled decision dates |
|---|---|---|
|2019|25/05/2018 12EDT|30Jan,20Mar,01May,19Jun,31Jul,18Sep,30Oct,11Dec|
|2022|04/06/2021 11EDT|26Jan,16Mar,04May,15Jun,27Jul,21Sep,02Nov,14Dec|

[2019source](https://www.federalreserve.gov/newsevents/pressreleases/monetary20180525a.htm),
[2022source](https://www.federalreserve.gov/newsevents/pressreleases/monetary20210604a.htm).
All8meetings, không chọn theo pressconference/reaction/decisiondirection.
2018schedule ban đầu nói quarterlypressconferences; không dùng field đó để
lọc2019 vì practice đổi sau publication. Dates là input; sau đó đối chiếu
[actual2019archive](https://www.federalreserve.gov/monetarypolicy/fomchistorical2019.htm)
và [actualcalendar2022](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm),
16statement metadata dates/release14:00ET. Unscheduled2019Oct4 không predicted
bởi originalcalendar và không nhận như scheduledsignal. Audit không dùng
ratechange/statementtext làm feature hoặc chọn events.

Fetch20publicHTMLpages:2tentative+2actualindexes+16linkedstatements, link lấy
từ officialindex, không đoán URL. Lưu bytes/hash/URL/fetchUTC/published/asofrole,
chỉ parse metadata. Noauth/account/key/providerpaid/newfeed. Perrequesttimeout15s,
overalldeadline180s, nohiddenretry/WAFbypass. Bị chặn thì giữpartialfailure,
không đi tiếp economics. Trang capture hiện tại không là independentWayback
snapshot chứng thực mọi bytes ngày xưa; original datedpublication và prior
NYFedclock là scope bằng chứng. Calendardate mismatch=>inconclusive trướcPnL.

## Frozen component

Primary BUY: entry **14:00 America/New_York ngày trước**, exit **13:00 ngày
FOMC**,23h. Control BUY: hai endpoints dịch7calendar days, localNY hours giữ
nguyên, recomputeDST; không trừ168UTC hours qua DSTweek. Không chọn control
theo giá/volume/tin khác; không tự loại NFP/CPI/holiday để làm đẹp.

Original calendarpublication phải trước entry cảprimary/control. 14ETstatement
clock và13ETexit chừa1hour; H1Open là quote intervalproxy[start,start+1hour),
không khẳng định firsttick đúnggiờ hoặc targetfill. EntryAsk/exitBid. Exact
sourcehour/side cần có, crossedOpen reject; thiếu thì unresolved row retained,
không nextavailable/asof/padding. Pricepathgap report từ observedH1, không gọi
maintenance hoặc unknowngap là continuousquotes hay brokeroutage đã biết.
KhôngSL/TP/sizing/forceclose hoặc nativeprop ởcomponent này.

Reuse4sealed developmentBidAskbooks2019/2022 của
`execution-v1/nasdaq-history-v1` tại private campaignroot. Source-only,
USATECH.IDX/USD,UTC/ms/grid0.001, source-reviewed; no2025+ownholdout,
cleanOOS=false. Không tải/parse fulltickhistory hoặc sửa raw/pins.

Hypothetical1researchunit worth1USD/priceunit, **không lot/broker spec**.
Reuse canonical USD financialmodel như R061; observed separate-side spread.

| Cost | Slip/side priceunit | Commission | Calendar funding |
|---|---:|---:|---|
|Reference|0.25|0|EntryAsknotional ×8%/365/debit at22UTC/day|
|Stress|0.75|0|EntryAsknotional ×16%/365/debit at22UTC/day|

CentHALF_UP mỗifundingevent/trade; fundingboundary entry<boundary<=exit.
No targetswap/credit/tripleweekday/dividend claim; zeroindexcommission là
declaredpublicscenario, không historicalterms proof. Không niêm yết rawprice
componentUSD thành lãi10kaccount hoặc projectedchallengeincome.

Output32rows (16events×primary/control),64financialcases. Báo peryear/cost
resolved/unresolved/net/funding/paired-delta/positiveevents/concentration,
controls khácdates không independentsamples và không phép đo causalFOMCeffect.

**Chỉ retain để nghiên cứu tiếp** khi cả2years:>=7/8eventpairs resolved,
primary stresssum>0, primaryminuscontrol stresssum>0 trên commonmask. Missing
rows nằm denominator, không coi0hoặcdrop bất lợi. Mẫu ít/unknownPITcost/paths
vẫn hạn chế mọi kết luận; dùpass không statcertificate/prop/OOS/promotion.
Failgiữnegative, không dịchgiờ/side/cost để cứu; không loại cảeventfamily.

## Implementation và review

Fixtures trước outcomes: winter/summer/DSTcontrol, publicationfutureguard,
calendaridentity/date/clock, absent/crossed endpoints, funding22UTC/boundaries,
BidAsk/slip/centaccounting, denominator/commonmask và noauthority.
Reuse existingsourcevalidators/financialprimitives, không thêm engine/UI/skill.
Code`tooling/ai-engines/fomc_price_component.py`; driver/reviewer private,
pin protocol/currentcode/deps/8bookparentseals/calendarbytes trướcnumeric.

SeparateFractionfinancial và independentcalendar/source/census kiểm toàn64
cases, mutationswrongquote/time/missingrow/funding/authority/hash reject.
Cùngagent/feed không independenthuman/model/targetbroker. NoLLMsignal calls.
Output mới`execution-v1/fomc-nasdaq-component-v1`,1writer/PID/progress/events/
CANCEL/failure/deadline,source-snapshot. Calendar pass trước price outcomes.
Giữ failures/partials, không overwrite hoặc gọi observer timeout làworkerdead.
Lưu timing/decision/nextaction, updateexistingcatalogue/index/context và hậu
kiểmengineering; nooptimization nếu khôngbottleneck, noGoalcomplete vìpassstudy.

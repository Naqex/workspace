# US500 first-half-hour → last-half-hour — một hypothesis có nguồn khác

Nghiên cứu song song với longRSI, không tune bản noise14/RSI. Reuse canonical
M1Bid/Ask2022–24 và verifiedNYSEcalendars;không download/model/broker/2025+.

Nguồnprimaryđọc08/11: [Gao,Han,Li,Zhou2018,JFE](https://www.sciencedirect.com/science/article/pii/S0304405X18301351)
abstract/intro/market-timingsection;[authoruniversityrecord](https://profiles.wustl.edu/en/publications/market-intraday-momentum/).
Paperfirst-half-hourreturn **bao gồmovernight**: priorcashclose→10:00,không
chỉ09:30→10:00. Tínhiệudương thì longlast-half-hour,âmthìshort. Đây là
SPYTAQ1993–2013/ETFpaper;US500CFD+hardstop+lotrisk/latency khôngreplication,
không nhậpcode/data hoặc chuyểnheadlineperformance thànhproof.

## Frozen rule trước outcome

Candidate `us500-cash-firstlast30-atr14quarter-r025-v1`.
Chỉ full390mincashsessions;halfdayđượcnhậndiện bằngcalendar vàskip**trước**
outcome. Priorcashclose bắtbuộc làBidclosephútcuối đúngpreviouscashsession,
kểcảhalfday;missingpreviouslastbar thì khôngsignalngàytiếp. M1Bidclose09:59
cho10:00first-half-hour. Điềukiện: giá10:00>previousclose→BUY,<→SELL,=→none.
Khôngvolume/highvol/newsfilter,chưaexchangevolume/point-in-timenews đủ.

Decision15:30NY khiđãbiết09:59close vàpriorclose;khôngnhìngiá15:59 hoặc
đòingàyhiệntạiđủ390bars trướcchoentry. Ghi signal lúc15:30dù1barcuốingày
saucònunknown. Fillopen15:31,one-minute latency;expireifminuteunavailable.
SLdistance=0,25×mean14**past**cashdailyTR (sqrt-durationmotivation,rounded
frozenfraction,khôngthresholdfit), khôngTP/trailing. PastcashTR phảiđúng14
consecutivesessions,fullbars;gaps làmunavailable lịch sửtheocausalclock.
Thời gianngắn hơnholdingkhông làquyềnnângplannedrisk. Entry/lotcost/margin
reuseexactbookprimitives:10k/25USD,1USD/point/lot,grid0,001,min/step0,01,
max50/leverage10,commission0,5/lot/side,slippage0,25/0,75reference/stress.

PlannedEXITdecision15:58→open15:59,không phải pricecloseđãnhìntrước.
Lệnhthoáttheocalendarkhôngđòilaterdatavalid. Missingexitminute hếtpending,
positionđượctheoSLvànextavailablecashsessionopen queueEXITdecisionlúcopen,
fill1phútsauopen;khôngfakeclose/cuốimẫu. ThêmsafetyEXITởmọicashopen;
khinormalflatthìno-op. Overnightunresolvedpath/funding giữ nhưsharedbook
1/2USDperlot/calendar-day declared nếuexposurecarryunexpectedly;khônghistorical
brokerfunding/dividendverified. Bid/AskM1stops khôngfirstcrossingtick.

## Kiểm và quyết định

Trướcnumeric:correctovernight-includedsign;full-vshalfday;NYDSTclock;
currentfuturebarlosskhôngđổientrydecision;exactpast14TR;exitclock/queue;
synthetichandpath/sizing/funding/oneposition đãreuse sharedbooktested.
6rows3years×2costs,+3nullcontrols,source/protocol/inputhashes vàoutputmới.
Giữmọioutcome;đủưu tiênhistoricalextension nếu netdươngmọinămcảcosts,
khôngmaterialdefect;gaps/sample/concentrationgiữunknown. KhôngqualifiedC1,
khôngchọnslmodifierđểcứuoutcome hoặc gọi3yearstreatedascleanOOS.

# R087 — ownCFD adaptation: Nhật phản ứng ngược phiên Mỹ

09/11/2026, sau [sourcepilot](JAPAN-US-SOURCE-RESULTS-20261109.md) đủmốc.
Ownhypothesis, **không replication paper futures**, khôngindependentedge
chỉ vì đổi instrument; liên quan crossmarket/openingreversal. ChưaR087PnL
hoặc catalogue tăng trước run. Không sửa R086; không dùng08:45 như alternative.

## Câu hỏi và rule khóa trước outcome

Giả thuyết bác bỏ được: dấu close-to-close của phiên Mỹ đã hoàn tất dự báo
phản ứng ngược của JPNsourceCFD quanh **cash09JST**, đủ bù BidAsk và phí
khai báo trong hai nămdevelopment2019/2022. Motivation từ
[primarypaper](https://doi.org/10.1016/j.finr.2026.100108), fullmethod chưa đọc
do publisher403/redirecterror. Không tự nhận kết quả paper áp vào sourceCFD.

- Japan calendar: mọiweekday2019/2022 trừ Cabinetnationalholidays và01–03Jan/
  31Dec theo [JPXcashrules](https://www.jpx.co.jp/english/equities/trading/domestic/01.html).
  Reuse CSV đãpin SHA`cec37a743c96995cdb9cb52b685c9003634682a9b0e1a640a6b9b96881fe964a`.
  Buildfullcalendar, không dùng subsetpaydaysTokyo. Coverage/calendar là declared
  exchangeproxy, chưa actualallhalts/CFDaccountavailability; không dropgaps.
- US calendars: accepted2018/19/2021/22 exchangecashcalendars; hai phiên hoàn
  tất gần nhất trước Japan09:00JST, sessionclose16NY hoặc13NYearlyclose.
  LastM1Close ở close−1minute, known-at upperbound đúngclose. Warmup chỉ
  priorNov/Dec2018/2021, không lấy tương lai hoặc latestUTCday mặc định.
- LatestUSclose phải đã biết trước decision và age≤72h; calendarstale>72h
  →plannedrow/noentry, không priceoutcome exclusion. Giữ count/lýdo riêng,
  không chọnUSreturntừ phiên khác để lấp pricegap. Hai priceendpoints thiếu/
  crossed →signalunknown (khácflat), không dùng closeadjacent.
- Predictor midpointClose_latest − midpointClose_prior. Dương→SELLJPN,
  âm→BUY, bằng0→flat. Không magnitude/VIX/day/quarterfilters hoặc fit.
- Decision09:00JST, entryM1Open09:01, exitdecision09:28/exitM1Open09:29;
  holdingrole source28minutes09:01…09:28 vàexit09:29. Strictsource cần mọi
  Bid/AskOpen trong28minutes+exit; crossed/missingrole→unknown, không ffill.
  Source interval `[t,t+1min)` proxy, khôngexacttick/instantfill.
- Source `jpnidxjpy`/`JPN.IDX/JPY`, quotesJPYindexprice. **1researchunit =
  1JPY/pricepoint**, không USD/account/tradablelot/JPXtickvalue. Hai costscenarios:
  reference slippage1JPYpricepoint/side, stress3/side, sourceBidAskembedded,
  commission0declared, funding0 vìwindowkhôngqua declared22UTCrollover.
  Không tuyên bố fees/specFTMO/The5ersverified hoặc availableticker.
- Phân rã midpointPnL, spread, extra/slippage, funding vànet, giữrawfraction
  sourceprecision; không autoUScentround JPY. Khôngtargetaccountcashrounding.
  Midpointbenchmark chỉ accounting; khôngexecutablemid hoặc marketimpact.
-5rules: primarycontrarian, oppositecontinuation diagnostic, alwaysBUY,
  alwaysSELL vànull. Control không được tựpromote; primary/opposite signal
  thiếu làunknown, long/shortkhôngđòifeature, null0khôngđòigiá, flat0khôngtrảphí.
  Stale calendarskip áp cảexposedrules, không fakeunknown/noevent thànhlệnh.

## Cohort, sources và gate

Full calendarexpected trước fetch; **20books** =2years×5rules×2costs, planned
financialcases=10×totalJapansessions. Không cases=independenttrades; dates
có sameUSsignal/alternativecostcontrols. Inheritedexposure/pilotdates ghi rõ;
không gọi2019/22hoặcselectedperiod cleanOOS. Không2025+.

Reuse pilotJPNraws đúngselectedUTCdate; fetchonly Japan00UTCdate cho09JST
session, mỗiBid/Ask. Không cần previousUTCday vì08:45khôngrecipe. Tối đa
1100day-sideURLs,2inflight, existinghelper/cache/packagepins; requests đãseal
reuse và kiểmhash, khôngfetchlạifullhistoryUS. USpricepair từacceptedcanonical
fullquarters/proofs, nămpriorwarmup chỉ selectedsealedraws đúngclock.
Không nới`us500_year_source`yearguard hoặc đổi canonicalhistory.

Sourcebookcensus/selectedsignal/holdingcoverage phát ra trước economics.
Frozenpriority: cảhaiyear strictresolved≥95%calendar-eligiblewindows,
strictprimarynetstress>0, primarystress−alwaysBUYstress>0 trên commonresolved
cohort. Unknowns giữplannedrows; tỷ lệ<95% thìinconclusive, khôngtựadmit
knownsubset làmwholeyear. Netreportedknownsubsetvàcoverage riêng; 95%không
là chứng minh ngàyunknown không thể đảo dấu. Survivor chỉ đủreviewbound/gaps,
chưa strategyqualified hoặc automaticpromotion. Khôngrule/control/hourgrid
để cứu nếu khôngđạt; khôngtăngrisk, bỏSL hoặc mởholdout.

## Run và review

Buildcalendar và preflight trước sourceoutcome: nationalholiday/special2019,
weekend/yearboundary/USearlyclose/DST/72hstale, signalBUY/SELL/flat/unknown,
BidAskcosts/null và sourcegaps. SeparateFractioncalendar/fulldeltareviewer
đủsourcefields vàfinancialcases, actualtamper/mutationchecks. Bind raw/proof/
code/protocol/config/output; PID/progress/events/deadline/CANCEL/nooverwrite,
reusepartialsealedrequests. Fetchdeadline900s, cost/review180s riêng; nohidden
retry/auth/WAFchanges, transientcap3theoworkspacehelper. Sourceguard perrequest,
observerkhôngđánh đồngstale vớidead; khôngrestart từtimeoutquan sát.

KhôngSL/sizing/margin/intrabaraccount/prop/time-fit/OOS/prospective hoặc
broker/OrderCheck/OrderSend. Nếugiữ đượccomponentthì mới đăng ký riskwrapper
phùhợpchallenge và kiểm thật cácgates; không so trực tiếp JPYcomponentPnL
với USDcomponent/goldaccount. Catalogueaccountversions58giữnguyên.

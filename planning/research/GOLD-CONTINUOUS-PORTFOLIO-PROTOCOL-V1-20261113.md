# Protocol v1 dự thảo: Gold liên tục, rolling starts và portfolio cùng tài khoản

Đợt A,13/11/2026. [JSON contract](GOLD-CONTINUOUS-PORTFOLIO-PROTOCOL-V1-20261113.json)
là cấu hình draft có version; [bằng chứng/gap đợt A](GOLD-EURUSD-PORTFOLIO-STAGE-A-20261113.md)
giữ kết quả economics. **Chưa dispatch continuous/portfolio hoặc merge trước ASTRA
review.** Chỉ125/200USD stoprisk trên50k (0,25/0,40%); không alpha/SL/exit grid.
Chỉ dataGold2010–24, Catalogue13FX2010–22 và warmup cũ đã được phép;2025–26 đóng.

## Câu hỏi, population và điểm bắt đầu

R043 exact`xauusd-h4-sma20-80-atr14-r025-v1`: SMA20/80, WilderATR14/SL2ATR,
giữ nhiều ngày, mất hướng thì thoát. Không long-only hoặc đổi sangintraday.
Đo thời gian đạt từng phase, firstbreach và reward eligibility của đúngmodel;
chưa chứng minh edge mới hoặc tỷ lệ pass thị trường tương lai.

-60starts cố định:00:00UTC Jan1/Apr1/Jul1/Oct1 mỗi năm2010–24. Hai sizing
 endpoints, tối đa120start×risk cases; không thêm starts đẹp sau outcomes.
-Mỗistart50k/flat/no pending, không nhận position trước start. Warmup100H4
 complete/admitted kết thúc trướcstart, giữpreviousclose/ATRseed đúngcanonical.
 Dữ liệuNov–Dec2009 cũ cho2010; không đủ100bars thì ineligible, không padding.
-Warmup chỉ cập nhật indicator, không trade/position hoặc mang pending intent
 từ trướcstart. Saustart đợi causal crossing mới theo frozenrules, không tự
 mua vìMAfast đangtrên MAslow. Indicatorstate không reset tạiJanuary1.
-Giữ sourceclockUTC/baravailable_at/fill-after-intent. Không nói M1baropen là
 quote thực cómillisecond. Ask mô hình phải có nhãn, không biến thànhobserved.
-Chạy tới cutoff2025-01-01exclusive hoặcfirstterminalevent. Lưuactual lastquote;
 các cash events sau quote không tạo observation mới. Được follow nhiều năm,
 không ép12tháng là hạn thi.3/6/12/24tháng là mốc báo cáo.

Các cohort overlap; hai sizing chung data/trialhistory. Không IIDbinomialCI,
không chia“năm pass/tổngnăm” thành calibratedchance. Censoring theo cutoff
khác breach thật/dataunknown. Sốstart đủ thời gian lịch cho3/6/12/24tháng tối
đa60/59/57/53; actualquote/coverage có thể giảm mẫu đo hợp lệ tiếp.

## State qua năm, phase và sự cố

Một eventloop giữ indicator/H4builder, previousdifference, position/SL,
pending/exit, financing nextevent+dedupids, cash, equity, dailyanchor/reset,
qualifyingdays, firstbreach, phase/accountid và inputcursor. Không nối15trade
lists cũ vì chúng đã reset account/position/warmup và cắt winner ởyearend.

Reuse `ResearchH4Candidate.export_state/from_state`, native execution ledger,
`ForexPropObserver`→`prop_session`/`money_oracle`; không tạo lifecycle thứ hai.
Native observer hỗ trợ50k qua explicitinitialbalance/profile, nhưng runner
Forex vẫn hardcode10k/EURUSD trong initialization/reconcile/_PilotGuard và
timedfinancingwrapper. `MetalStudyMarket` mới admit coarse, không là Goldnative
qualification. Gap nhỏ nhất: typedmarket/sizing/accountadapter tại runner,
giữ primitiveexecution/cost/lifecycle đã có; fixtureparity trước financialbatch.
`PilotLimits` default25USD/trade,100daily/500overall vàUTCinternalday không
được âm thầm đi vào50kGold. Bind125/200 và exactprofile/firstbreach/comparator;
không để oldinternalbrakes đổialphapath rồi gọi là cùngchiếnlược.

| Sự kiện | State được đổi / điều không được làm |
|---|---|
|January1|Chỉ tiếp clock/cash/funding; không reset indicator/position/phase|
|Prague00:00|Balanceanchor mới, DST23/25h; floatingmark cầnquotequality; không resetoverall|
|Fundingrollover|Đúngcalendar/mode/rate/effective-time, signeddebit/credit; dedup quaresume|
|Phase1target+10%/phase2+5%|Balance đủ,flat/pending0,min4entrydays và khôngbreach; không forceclose đểpass|
|Nextphase|Retireaccount, new50kinitial/anchor/min-days, clearposition/pending latches; giữ causalindicator, không phát lạioldintent|
|Firstbreach|Latch trước target cùngevent, không xóa sauhồi; thiếuordering/path thìunknown|
|Restart|Checkpoint/cursor/input/source/profilecosthash khớp; khôngdoublefill/funding, không migratelegacy silent|

Giữaphase có độ trễ hành chính chưa biết. Model0market-time transition chỉ
là sensitivity lạc quan được ghi rõ, không thậtpass/instantfunded. Nếu intended
adapter khôngđủstate dùngcallback mới tại boundary, không recreatebuilder
mỗi năm; không gắn lại phiên bản source mới lên pins cũ.

## Loss, coverage và quyền kết luận

FTMO CFD2-Step/Swing theo [objectives hiện hành](https://ftmo.com/en/trading-objectives/):
Daily5%initial với balanceanchor00:00CE(S)T; overallstatic10%initial;targetbalance
10%/5%,flat,min4tradingdays. Dùng currentterms counterfactual cho2010–24,
không lịch sử điều khoản. Reset-before-fees đúngtimestamp là convention
draft đã khóa; source targetclock phải xác minh trước brokerclaim.

**Cap owner:** daily<2,5%initial (1.250USD) và overall **staticinitialloss**
<6,5% (3.250USD). Báo equitypeak-to-trough riêng; không thaymetric sauoutcome.
Đợt B đo capcrossing/eligibility trước; không thêm emergencyexit/brakes đổi
alphapath nếu chưa đăng ký accountpolicy. Jointaccountstage cần sharedbudget.

-M1High/Low không có ordering; stop/target/phase event ambiguous phải giữ
 branches/envelope/unknown, không tùy chọn O→H→L→C để tạo winner.
-Pricegap không fill/drop; distinguish historicalclosure cónguồn với unknown.
 Coverage calendar và session có mẫu số; oldwithin-observed-hour98,89% không
 thànhfullcoverage. Missingresetquote: balanceanchor từcash có thể biết nhưng
 floatingcontemporaneous unknown. Cấm lastquote_asof được gắn observed/full.
-Đo firstsupportedbreach kể cả nhữngđoạn khácunknown; no-observedbreach khác
 survival. Censor data-gap first uncertainty riêng administrativecutoff.
-Open/pending tạicutoff rightcensored, không forceclose hoặc dùngfloating
 để đạtclosedtarget. Báo cash/floating/knownmargin/stalemarks riêng.

## Cost admission và funded reward

Không có fullverifiedtargetspec trong đợt A. Golddeclared20/40 và45/5 không
là FTMO. Có thể đề xuất legacy40/40 comparator lane riêng; presenttarget lane
chỉ sau đủspecs. Không tự mở feegrid hoặc dùng currentrate thành2010–24rates.

Sourcepackage cần đúng firm/CFD2-Step/Swing/platform/server/accountcurrency/
symbol/time-effective: contract/digits/point/ticksize/tickvalueprofit-loss,
swapmode/signedrates/triple-day/calendar/conversion, commission per-sidebasis,
quantitylimits/leverage/margin, symbolsession/news/holiday/maintenance.
Public [metals0,0007%volume/side,Forex2,50USD/lot/side](https://ftmo.com/en/blog/trading-updates/trading-update-25-sep-2025/)
khác oldGoldfixedfee. PublicXAUrowSwing1:15 không trở thành1:30baseleverage.
Khônglogin/accountcalls để đóng gap đợt A; spec thiếu thì N/A, tiếp fixtures.

Funded không có profit target nhưng **“chỉ cần dương là rút” là thiếu**.
[RewardFAQ](https://ftmo.com/en/faq/how-do-i-withdraw-my-profits/) quy định
request từngày14 saufirsttrade củaaccount,flat/pending0,tuântradingobjectives/
terms,xétduyệt/invoice.2-Step baseline80%,90% chỉ khi đủscaling/premium.
[Newaccount sau reward/phase](https://ftmo.com/en/faq/can-i-modify-my-platform-or-account-type/)
ngăn carryposition trực tiếp; indicatorcausal có thểcarry khi adapter giữ đúng.

Draft rewardpolicy: mỗi14ngày từfirsttrade account, đợi naturalflat hợp lệ
đầu tiên saueligibility; khôngforceexit. Zero/no-eligible cycles phải hiện.
Full cashdistribution/no-rollover baseline; không pretend còn100%profit làm
reserve trênnextaccount. Rollover nếu sau này bật: ratioáp trước rollover,
withdrawrolledreward khônghaircut lần2; phải contract/version riêng.
Nextaccount balance/floor/paid-out/rollover chưa bind đúngaccount thì stop
`payout_contract_incomplete`, không tạo rewardseries bằng assumptions ẩn.

Simulatedprofit→rewardeligibleprofit→grossreward80%→receivable sauapproval→
actualcashreceived (unknown trướcbankreceipt). Phíchallenge/retry/refund,
vận hành/chuyểnđổi/thuế tách riêng và cóunknown; nominal50k không là tiền owner.
Requesteligibility không là stableincome; processing1–2businessday từngbước
là mô tảpublic, không guarantee hoặcsimulatepaid khi mớirequest.

## Portfolio readiness và so sánh công bằng

Đợt A **chưa chọn counterpartEURUSD**: cả15candidates vẫn thiếu netrobustness/
targetcost/path; dươnggrosssau spread không là positiveedge. Khôngnewdiscovery
để buộc có leg2. Khi một leg đủfeasibility, commonwindow hiện2010–22,clockPrague.

Reuse native `replay_portfolio.py` sharedclock/account/per-instrumentstate,
analytics/immutablecheckpoint;3fixtureswallet/inactiveSLTP/stalequote đã đạt.
Tuy nhiên currentReplayService từ chối multiasset tick/marginmode và per-leg
barstate cóasofsemantics, **chưa** commonaccountGold/FXtick-risk/financing/prop.
Không thêmmanager trước khi nốicontract/gap này và có counterpart.

DailyMTM increments: tạicùngvalidmarktime, `equity(t)-equity(t-1)-externalflows`;
chuẩn hóa theoinitialcapital/budget đãpin. EURexistingH1Bid/Askcache đủ dựng
selecteddaily-close diagnostic, GoldM1 cósource; nhưng chưa cócontinuous
position/cashseries hai leg. Không nốiannualMTM ởJan1 hoặc coi resetPnL làreturn.
Missingmark legbấtkỳ→jointincrementN/A, khôngdrop ngày thua/zero-fill/stalecarry.
Không correlationequity tích lũy hoặc15annualnets, không gọi rho thấp là edge.

Jointaccount50k: accountcashsingletruth, sharedmargin/freeequity/positions/
pending/reservations, USDexposure, netting/hedgingmode, bothcosts,clock/reset,
phase/min-days/firstbreach/withdrawals. Phiênsimultaneous cập nhậtatomic:
knowncash/reset→marksalllegs→breach→exits→cash/margin→intents. TieGold-beforeFX
được đăngký, khôngliquidateasset theooutcome. Không chia2budgetfulllimit.

CompareGoldalone/EURalone/joint với **cùngtotalstoprisk125 hoặc200USD**;
jointdraft50/50 tức62,50+62,50 hoặc100+100, không mỗileg125/200 rồi gọidiversify.
Báo dailyincrementPearson/rank vớicoverage/dependence, loss-dayoverlap,
tailcooccurrence, jointstaticloss/peakDD, timefit/turnover/rewardwaiting và
cost/riskcontribution. LongGold+shortEUR có thể cùngUSDexposure; tickerkhác
không tựđộc lập. Allocationkhác là policytrial mới, khônggridtốiưu trọng số.

## Fixtures tối thiểu và budget đợt B đề xuất

| ID | Test / expectation trước chạy dài |
|---|---|
|CF01|Goldmarket100oz/0,001sourcegrid vsFX100k/0,00001; rejectwronggeometry,50k không rơi về10k|
|CF02|Continuous2010shortprefix so frozen producer cùngrules/model; splitatDec31 vàuninterrupted cùngfullstate/cash/intents|
|CF03|Warmup100closedH4, nofuture/partial/padding; no-prestartposition/pending; missingbarineligible|
|CF04|Heldposition/pending/funding quaJanuary1, restartbefore/afterfunding khôngdoublepost|
|CF05|PragueDST23/25h, balanceanchor vsfloating, feeexactreset/lastquote gap vàrightcensor|
|CF06|Firstbreach-beforetarget cùngevent; min4entrydays,flat/pending0 vàphase2new50k/indicatorcarry|
|CF07|SLtraversalM1 ambiguous/fullquotecontradiction; no wrong intraminuteordering tựpass|
|CF08|Risk125/200 freshlot/cost/margin/rounding; stopbudget vàaggregateexposure không resettheoyear|
|CF09|Funded14days/naturalflat,negativecycles,noeligibility,80%ratio,newaccount/withdrawals/reserve;unknowncontract stops|
|CF10|Twolegsamebudget,simultaneousintents/inactivepositionmark/stalemark rejection/jointmargin,sharedbreach andwithdrawal|

17existingobserver/resume +4StageAfeasibility +3portfoliofixturechecks đã đạt;
bảngCF01–10 là thiết kế acceptance tiếp theo, không claim tấtcả đã implement.

Budget draft sau ASTRAreview: boundedfixtures≤15phútwall/job,1writer, checkpoint/
cancel/phaseprogress, khôngprovider. Chưa có Goldcontinuouskernel benchmark nên
**ước tính** preprocessingM1/H4 reuse≤1–3phút; conditionalM1continuous60starts×2
endpoints khoảng5–30phút máy này nếuvector/reusebatches. Đây khôngnative-tickETA:
margin/lifecyclecallbacks có thể chậm hơn; đo1start boundedprefix rồi chốt cap.
FulltickGold chưa đủ nguồn; không dùng benchmarkM1 cũ16s để hứa120replays16s.
Khôngdispatchlongbatch chỉ vìprotocol có file/hash; ASTRA duyệtđợtA rồi giaoB.

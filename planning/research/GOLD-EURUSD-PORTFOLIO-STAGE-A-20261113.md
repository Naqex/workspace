# Đợt A: Gold continuous khả thi có điều kiện; chưa chọn leg EURUSD cho portfolio

13/11/2026. WorkerSol, ASTRA điều phối/review. Đã xác minh trong threadASTRA
lời owner cho phép giao trực tiếp và worker gửi báo cáo về; không suy quyền
chỉ từ promptđiềuphối. Đợt A chỉ diagnosis/sourceadmission/protocol trước run
dài; [campaign](CHALLENGE-CANDIDATE-CAMPAIGN-V2-20261108.md) vẫn ownmission.
**Chưa continuous/rolling/portfolio financialbatch, chưa merge để ASTRAreview.**

Kết quả mới: đã bind **76.750 closedtradecases +50open** của15EURUSDversions
×2costs trên13annualresetbooks2010–22 vào causalintent/size/quote summaries;
không rawtickscan/2025–26 hoặc sửaalpha. Đây là repeatedcost/versioncases,
không76.750cơhội độc lập. [JSON số liệu/hashes](GOLD-EURUSD-PORTFOLIO-STAGE-A-20261113.json) giữ104side/year
records, distributions/risk và bridges. [Protocolv1](GOLD-CONTINUOUS-PORTFOLIO-PROTOCOL-V1-20261113.md),
[config](GOLD-CONTINUOUS-PORTFOLIO-PROTOCOL-V1-20261113.json) chờreview.

## 1. Gold: sửa cách hiểu trước khi chạy continuous

[M1diagnostic trước](GOLD-M1-PATH-AND-EURUSD-POSTMORTEM-20261113.md) khớp declared
cash/equity nhưng **không phải Gold đã passquỹ hoặc dailybuffer dùng được**.
15annualresets cần genuinecontinuousreplay, không bỏ boundary trongbáocáo.
Các năm trước đều reseedindicator và resetposition/cash, nên concatenation
sẽ làm sai winners/cadence/sizing/funding/eligibility và timefit.

| Hạng mục audit lại | Bằng chứng / giới hạn |
|---|---|
|Nguồn/denominator|Oldrawhash`d209df9…471b9` và original15books khớp. Mỗiannual50k. M1Bid +Ask1USD mô hình; calendarcoverage68,1741%, within-observed-hour98,8939% không thay fullsessioncoverage|
|Stop/extremaordering|135stopminutes cófullminuteextrema vượtfrozenSL; ordering có thểsaufill. Bao biên thậntrọng đãghi đúngscope, không actualheldMAE. Witness2012coarse-7 lúc30/04/2012 12:31UTC: extraadverse76,176USD có thể sau thoát; rawprices chỉ ởprivateevidence|
|Resetquote|4.072ngày cóM1,3.823ngày cóbarđúngmidnightPrague,**249ngày thiếuđúngresetmark**. Cashbalanceanchor biết từevents không chứngminh floating tạireset. Lastquote không được nângthành fullobserved|
|Commission/slip|Oldcash postsroundtripfees lúcclose; openliquidationequity reserveshai chiều. Reserveperposition cao nhất7,20USD. Khônggiống actualper-deal commission; freshaccountmodel phảipinposting|
|Funding/lastquote|Funding sauquote cuối tổng13,20USD/15stressbooks đãđượcbridge vào terminalnet nhưngkhông tạoM1observation. Cash/reset event khi stalequote cầnqualityunknown|
|Openpositions/carry|5terminalopen, khôngforceclose. Nativephase reset khác calendarreset; fundingdedup/queuedstate/ATR/H4builder phảicarry quaJanuary1|

**Không phát hiện thêm lỗi số học material trong declaredscope cũ.** Không
rewrite oldreports/seals hoặc thu hẹpSLbound theo outcome. Scopecorrection
trong packet này là cấm dùng observedlowDD như fullpath/brokerproof; review
ASTRA có thể yêu cầu bổ sung affectedtest nếu phát hiện defect khác.

### Reuse source và gap nhỏ nhất

| Thành phần hiện có | Đã kiểm / cần nối |
|---|---|
|`ResearchH4Candidate`/H4Builder|SMA/ATR state export/restore; cầnseedonce,carry năm và clearpositionlatch chỉ khi phaseaccount thay|
|`ForexPropObserver` +`prop_session`/moneyoracle|ReusePragueDST/balanceanchor/firstbreach/flat/min-days/reset; **50k dùng được khi truyền explicitinitialbalance**, default10k phải tránh|
|`forex_h4_pilot.initial_state/reconcile` +`ForexPilotSnapshot`/`_PilotGuard`|StillEURUSD/100kcontract/10k,default25risk/100daily/500overall vàUTCinternalday; Goldnative bịrejectđúng. Cầntypedmarket/accountadapter, không đểoldbrakes đổialphapath|
|`MetalStudyMarket`/coarseGold|100oz/sourcegrid0,001/lotstep0,01, legacy50ksizing đãcó; chỉcoarsecontract, khôngverifiedmargin/Ask/tickGold|
|`forex_financing`|Signedrates/known_at/dedup đãcó nhưngwrapper gắnForexPilotSnapshot; cầngenericexecutioncash binding vàmodelclock riêng|
|`run_scenario` resume/phase reset|Đã cócheckpointcandidate/builder/observer/cursor vàindicatorcarry; reusevàtestGold, không thêmstateowner cạnhtranh|
|US500`Policy`|Alpha/entry/exit injection usefulpattern; khôngportMA/cashsessionrule sangGold. US500overlay vẫnpaused|

4feasibilityfixtures đã chạy: observer50kexplicit, heldposition quaNewYear,
Gold rejectEURpilot, protocolcaps/cutoff.17existingobserver/resumecases đạt:
phasecashreset/min-days/firstbreach/DST/funding/resume/pending. Đây là source
acceptance nhỏ, chưa Goldcontinuous pricepath đã qualification.

## 2. EURUSD SMA/Pullback H4: phí bất đối xứng không chữa được mọi chiều

Mỗiannualbook10k/risk25USD,13resetyears2010–2022; không50kaccount hoặcCAGR.
Swap được ghi theo **signed debit**: âm là credit, không lấyabs. Reference
BUYdebit9,30/SELLcredit0,31USD/lot/lần; stressdebit20/20,Wed×3/22UTC.
Comm2,50USD/lot/side cảhai,slipreference0/stress0,00002price/side. Historical
BidAsk thật nhưng executioncosts/counterfactualspec chưa historicalFTMO.

| Bản | Phí | Chiều | Lệnh | Gross sau spread USD | Comm/slip USD | Swap debit USD | Closed net USD | Open floating /swap USD | Equity contribution USD |
|---|---|---|---|---|---|---|---|---|---|
| h4-sma20-80-atr14 | reference | BUY | 102 | -195,47 | 16,60 | 273,28 | -485,35 | 70,09 /10,24 | -425,50 |
| h4-sma20-80-atr14 | reference | SELL | 122 | 291,05 | 20,55 | -14,19 | 284,69 | 32,58 /-0,11 | 317,38 |
| h4-sma20-80-atr14 | cost-stress | BUY | 102 | -172,06 | 29,61 | 582,40 | -784,07 | 69,33 /22,00 | -736,74 |
| h4-sma20-80-atr14 | cost-stress | SELL | 122 | 301,06 | 36,72 | 845,60 | -581,26 | 32,50 /5,20 | -553,96 |
| h4-pullback20-80-atr14 | reference | BUY | 143 | -396,65 | 23,60 | 388,18 | -808,43 | 331,22 /33,25 | -510,46 |
| h4-pullback20-80-atr14 | reference | SELL | 158 | 602,33 | 27,35 | -18,92 | 593,90 | 82,71 /-0,10 | 676,71 |
| h4-pullback20-80-atr14 | cost-stress | BUY | 143 | -404,48 | 42,30 | 824,20 | -1.270,98 | 330,34 /71,00 | -1.011,64 |
| h4-pullback20-80-atr14 | cost-stress | SELL | 158 | 522,18 | 48,60 | 1.125,40 | -651,82 | 82,51 /9,20 | -578,51 |

HaiLong đều **âm grosssau spread**, chưa nói commission/swap; Shortgross
dươngnhưng stressswap làm âm. Không tựbỏLong,đổiexit hoặccoi referenceShort
dương là candidate độc lập đã được validation. Openfloating khôngclosedcash.

-SMA: totalnetreference−108,12USD, stress−1.290,70USD; netequitydương5/13
  và4/13năm. Stressbeforefinancing+164,50USD là tổng gồmterminalfloating,
  khôngtruepositiveexpectancy hoặc“thắng suốt13năm”.
-Pullback: reference+166,25USD, stress−1.590,15USD; dương7/13và5/13năm.
  Stressbeforefinancing+439,65USD, cũng cóopenbridge. Lợi nhuận mỏng/same-data
  selection và yearsdispersion vẫn còn dù swap đích có thể ít hơnstress.

| Bản | Chiều | Mean giờ | Median giờ | p90 giờ | Năm sideequity dương chuẩn/stress |
|---|---|---|---|---|---|
| h4-sma20-80-atr14 | BUY | 204,4 | 88,0 | 638,4 | 4/3 |
| h4-sma20-80-atr14 | SELL | 258,5 | 130,5 | 698,4 | 6/3 |
| h4-pullback20-80-atr14 | BUY | 208,1 | 117,0 | 524,0 | 4/3 |
| h4-pullback20-80-atr14 | SELL | 234,7 | 101,5 | 642,0 | 7/4 |

Holdingclosed earliestmodelinterval, mean/median/p90 theo giờlịch. Thờiđiểm
open cuối năm chỉ lưuwhole-second; reviewerbind uniqueH1firstquote cùnggiây,
khônginventmillisecond. Openholds rightcensored trong JSON, khôngđưa vào
closedpercentile.104side/yeargroups trongJSON có đủgross/comm/slip/swap/net/
holding/openbridge; bảng năm phía cuối để thấy dispersion rõ.

## 3.13bản positivegross nhưng ma sát vượt biên lãi

Bindmỗiclosedtrade vào latestqueuedintent cùngside trướcfill, verifyquantity
theofrozen`size_for_stop`: `floor(25/((distance+tick+2slip)×100000+5)/0,01)×0,01`.
SL tạifill được làmtròn ra ngoài tick0,00001; riskgia roundedstop×100k×lot.
**R trong bảng là initialpricestoprisk của từngtrade**, khácbudget25USD và
không phải observedgaploss. Rounding/feesrisk vẫn≤25USD ởmọi binding; actual
brokerstop/declaredgap/financingloss có thể vượt, không gọiSL bảo đảm lỗ tốiđa.

| Bản | Closed | SL median pip | Risk median USD | Comm+slip median/p90 %R | Gross mean R/trade | Gross USD/lot | Hòa vốn USD/lot cóswap |
|---|---|---|---|---|---|---|---|
| h4-failed20-atr14-time6 | 1353 | 69,2 | 21,80 | 1,30 /2,10 | 0,0019 | 5,30 | 31,67 |
| h1-shock2-reclaim-atr14x1p5-time12 | 322 | 26,8 | 23,59 | 3,36 /5,32 | 0,0296 | 7,09 | 12,63 |
| h1-prior-day-break-atr14x1p5-close20 | 2249 | 24,1 | 23,76 | 3,73 /6,12 | 0,0240 | 5,47 | 9,00 |
| h1-prior-day-fade-atr14x1p5-close20 | 1883 | 24,0 | 23,76 | 3,75 /6,16 | 0,0031 | 0,93 | 9,00 |
| h1-bb20-reentry-atr14x1p5-time12 | 3157 | 25,4 | 23,70 | 3,54 /5,90 | 0,0173 | 4,23 | 16,56 |
| h1-europe-am-short-atr14x1p5-close13 | 3383 | 20,7 | 23,90 | 4,35 /7,20 | 0,0203 | 3,90 | 9,06 |
| h1-london-postfix16-20-atr14x1p5 | 3376 | 27,6 | 23,63 | 3,26 /5,29 | 0,0208 | 5,27 | 9,00 |
| h1-pre-ecb02ny-14berlin-atr14x1p5 | 3383 | 20,7 | 23,90 | 4,35 /7,20 | 0,0368 | 7,21 | 9,06 |
| h1-post-london16-16ny-atr14x1p5 | 3376 | 27,6 | 23,63 | 3,26 /5,29 | 0,0323 | 8,19 | 9,00 |
| h1-fixing-composite-atr14x1p5 | 9461 | 24,1 | 23,76 | 3,73 /6,29 | 0,0165 | 3,64 | 9,02 |
| h1-london-orb08-09-atr14x1p5 | 2497 | 23,5 | 23,76 | 3,83 /6,34 | 0,0139 | 3,08 | 9,00 |
| h1-asia09-15tokyo-london-break-atr14x1p5 | 2939 | 22,1 | 23,87 | 4,07 /6,87 | 0,0093 | 2,09 | 9,00 |
| h1-bb20-reentry-flat80-atr14x1p5-time12 | 471 | 25,2 | 23,64 | 3,57 /5,70 | 0,0003 | 0,69 | 17,04 |

Comm+slipstress **9USD/lot roundtrip =0,9pip**, trước financing và spread
đãembedded. Closedgrosssau spread/lot trong13bản khoảng0,69–8,19USD; ngay cả
gầnnhấtpostLondon≈8,19 cũng<9. PreECB≈7,21; failed20≈5,30 dùSLmedian69,2pip.
So lot-normalized cho thấy **biên lãi sau spread quá mỏng là nút thắt trực tiếp**,
không thấylotbug khiến mọi trade vượtbudget25 hoặc mộtSLsiêungắn chung.

Cost/Rmedian1,30–4,35%,p90≈2,10–7,20%,p99≈2,94–10,59%; entryspread/Rmedian
≈0,51–1,98% (đãởgross, không cộngdouble vào stopbudget). Mean gross/R của
cả13bản thấp hơnmeancomm+slip/R trướcswap. Median actualinitialriskinclfees
≈21,80–23,90USD; lotrounding làm **dưới**budget chứkhôngphìnhrisk.

Failed20có93minlotclosedtrades;13bản không cóskipped-minimum-lot decisions
trongscreen đãghi. Composite có3queuedentries chưa thànhposition tạicutoff;
khôngxóa khỏiintenthistory/cadence. Pips/risk/entryspread/break-evenlot và
tailpercentiles giữ trong JSON/privateforensics; spreadexit chỉknown khi
exactopenquote, stopintrahourkhôngđủ oppositequote nên fulltradepreadN/A.
Grosstrướcmọi phí chưađược táidựng, khôngclaim X% do spread hay wideningSL
causally sẽ tăng lợi nhuận.13versions overlap, khôngnhân sốmẫu vìcùngtrades.

## 4. Target fees, Swing và payout: sourceadmission chưa đủaccountcontract

Đãđọc lại primarysources hiệnhành; không đụng browser tab owner,khônglogin/
broker/OrderCheck hoặcAccountArea. [Sourcepacket trongJSON](GOLD-EURUSD-PORTFOLIO-STAGE-A-20261113.json)
tách publicannouncement, publicrow08/11, searchindex và actualaccountunknown.

| Thành phần | Verifiedpublic / cònthiếu |
|---|---|
|Commission|[FTMO25/09/2025](https://ftmo.com/en/blog/trading-updates/trading-update-25-sep-2025/):FX2,50USD/lot/side,metals0,0007%notional/side từ29/09/2025; chưa actualaccount/historical2010–24|
|Publicsymbolrows|Snapshot08/11:EUR100k/Swing1:30;XAU100/Swing1:15,swappoints khác nhau. Không nângngàyverified lên13/11. Freshtextfetch không cóXAUrow, searchindexEUR−10,88/+0,51points chỉđối chiếu, khôngreprice|
|Specmissing|Đúngserver/platform/program/size/currency/symbol,effectivedate,digits/point/ticksize/tickvaluesprofit-loss,swapmode/signedrates/triple-day/calendar/conversion,feevolume/lotbasis,leverage/margin/lotlimits/session/tier/slip|
|Availability|50k làresearchcapital. Owner trướcđó thấySwing10k/25k; publicSwingbase1:30 không xácnhận owner muađượcSwing50k hoặcGoldleverage30|
|History|Currentquotespec chỉ đủpresenttermscounterfactual; không thay lịch sử2010–24 hoặc ápdeclared−45/−5 thànhverifiedFTMO|

[Rewardofficial](https://ftmo.com/en/faq/how-do-i-withdraw-my-profits/) quy định
request từday14 saufirsttrade củaaccount,flat/pending0,objectives/terms và
xétduyệt/invoice;2-Step80%baseline,90%conditional. Bankminclosedprofit20USD,
crypto50USD; khôngpromise mỗi14ngàyđều cólãi/đủđiềukiện/nhậncash. [Newaccount](https://ftmo.com/en/faq/can-i-modify-my-platform-or-account-type/)
sauphase/reward khôngcarryposition; indicatorcausal có thểcarry tạiadapter.
Rollover phảiáp split trước và khônghaircutrewardđãsplit lần2khiwithdraw.
Simprofit/rewardeligible/receivable/actualcashsauphí owner là cácđại lượngriêng.
Chỉ dương làthiếu; Goldlongholds có thể phảiđợi naturalflat lâuhơneligibility.

## 5. Portfolio: chưa có counterpartđủcăn cứ, nhưng có nềnreuse thật

**Đề xuất0EURcounterpart ởđợtA**, khôngbuộc chọn1 tronglosers. EURPullbackH4
reference+166USD,Short củaSMA/Pullback dương trongreference làsame-data
diagnostic; stress toànrecipeâm, chưa targetcostOOS/path. Nếu sau này đủ
costevidence có thểreview một comparator; không chọnShort-only hoặcdiscovery
mới chỉ để cóportfolio. Correlationthấp khôngsửa đượcnegativeexpectancy.

`replay_portfolio.py` đã có sharedwallet/commonclock/per-instrument immutable
state và inactiveSLTP/analytics.3pytestfixtures đạt. Nhưng `ReplayService`
hiện rejectmultiasset tick+researchmargin vàbarstep dùngasofmarks; chưa
sharedGoldFXmargin/funding/riskobserver/prop/reset/withdrawal. Gap này phải
đóng ởexecutionowner trướccommonaccountstudy, không thêmUI/manager khác.

Data commonwindow2010–22:GoldBidM1 córawhash,EUR có13sealedH1BidAsk caches
(đãhash55bindings kểcảsổ/parents); khôngcầnfull517triệu tick chỉ đểdesign.
Có đủsource đểđăngký selecteddailyMTMconstruction, **chưa cóalignedcontinuous
returnseries**. Khôngproduce rho từcumulativeequity/annualPNL, không nốireset
Jan1 rồi gọicontinuousincrements. Missinglegmark giữN/A vàcoverage,khôngzero
hoặcdropdays; sourceUSDexposure/correlation có thểđổi régime.

Protocol commonaccount50k với **daily<2,5%,staticinitialloss<6,5%**, peakDD
riêng. Goldalone/EURalone/joint so cùngtotalstoprisk125/200USD; jointdraft
50/50=62,50+62,50 hoặc100+100. Hai legs cùngfullbudget sẽ tăngrisk thayvì
chứngminh diversification. Sharedpositions/pending/reservations/margin/fees/
phase/reset/withdrawal; deterministicordering trướcoutcomes. Chỉsaukhi có
counterpart mới đojointlossday/tailoverlap/timefit/rewardwait cùngriskbudget.

## 6. Sản phẩmđợt A và scopeđợt B đề xuất

[Protocolv1](GOLD-CONTINUOUS-PORTFOLIO-PROTOCOL-V1-20261113.md) khóa60quarterly
starts2010–24,2risk endpoints,100causalH4warmup,50kflat/noinheritedposition;
continuousstate quacalendar,phase1+10%→reset→phase2+5%/min4entrydays/firstbreach;
3/6/12/24monthhorizons và rightcensor. Funded14-day/naturalflat/noforcedexit,
80%rewardscenario,accountreplacement/cashflowgap. CF01–10giữtestplan nhỏ,
source/cost/gap/phase/portfolio trước longbatch; chưaclaim đãimplementhết.

Đề nghị ASTRA giaoB: (1)reviewsemanticchoices/reset/fees/warmup;
(2)pinmodel-sourcepackage hoặccholegacycounterfactual lane rõ;
(3)boundedGoldnative/continuityfixtures vàmeasure1startprefix;
(4)chỉsaufixturesđạt mớifreeze cap/dispatch120cases. Jointportfolio chờleg2,
fundedmoneyseries chờwithdrawal/newaccountcontract. Không thêmcase để cứuPnL.

Wall estimate chưabenchmark:fixtures≤15phút/job; preprocessreuse1–3phút;
conditionalM1continuous120cases khoảng5–30phút, **chưa là native-tickETA**.
ThựcđođợtA:EURanalysis13,784s, Fractionreview4,331s,
Goldscopereview10,639s;17existingchecks2,244s+4feasibility0,010s+
3portfolio1,14s. Không tính agentresearch/Git/webtime vào computebenchmark.

Sameagentarithmetic/source review khác ASTRAreview/independentfeed. Giữ lỗ,
hash/source và unknown; không promote,trading,raw2025–26,longfinancialreplay.
Mộtactivebranch/PR cho mission; WIPVI/pins/runtime giữ nguyên. Existingstrategy
qualification/evidence/githubskills đủ dùng; không tạo skill/manager mới.

## Phụ lục: equity contribution theo năm/chiều

Gross/fees/swap/holding từngyearside có trong104JSONrecords; bảng này gồm
closednet+openfloating−openfinancing. Không gộpcùngrowLongShort thànhcaseđộc lập.

| Bản | Năm | Chuẩn Long equityUSD | Chuẩn Short equityUSD | Stress Long equityUSD | Stress Short equityUSD |
|---|---|---|---|---|---|
| h4-pullback20-80-atr14 | 2010 | -107,12 | 206,98 | -125,68 | 156,83 |
| h4-pullback20-80-atr14 | 2011 | 31,89 | 32,43 | 8,21 | 11,10 |
| h4-pullback20-80-atr14 | 2012 | -37,64 | -75,81 | -76,96 | -139,18 |
| h4-pullback20-80-atr14 | 2013 | 26,11 | -121,56 | -14,57 | -186,24 |
| h4-pullback20-80-atr14 | 2014 | -89,70 | 625,47 | -134,30 | 349,72 |
| h4-pullback20-80-atr14 | 2015 | -128,21 | 50,17 | -142,67 | -30,59 |
| h4-pullback20-80-atr14 | 2016 | -127,55 | -134,16 | -163,30 | -197,66 |
| h4-pullback20-80-atr14 | 2017 | 207,39 | -156,12 | 132,90 | -217,36 |
| h4-pullback20-80-atr14 | 2018 | -200,36 | -172,80 | -238,75 | -243,59 |
| h4-pullback20-80-atr14 | 2019 | -175,42 | -140,17 | -228,25 | -273,41 |
| h4-pullback20-80-atr14 | 2020 | 254,35 | 25,33 | 202,61 | -68,98 |
| h4-pullback20-80-atr14 | 2021 | -127,40 | 455,37 | -162,33 | 272,70 |
| h4-pullback20-80-atr14 | 2022 | -36,80 | 81,58 | -68,55 | -11,85 |
| h4-sma20-80-atr14 | 2010 | 170,21 | 286,63 | 149,20 | 224,52 |
| h4-sma20-80-atr14 | 2011 | -47,17 | 20,79 | -52,87 | -14,06 |
| h4-sma20-80-atr14 | 2012 | -14,96 | 96,53 | -42,08 | 49,73 |
| h4-sma20-80-atr14 | 2013 | 9,70 | -97,07 | -25,88 | -129,23 |
| h4-sma20-80-atr14 | 2014 | -143,56 | -32,74 | -152,84 | -81,57 |
| h4-sma20-80-atr14 | 2015 | -25,07 | 38,94 | -36,69 | -25,57 |
| h4-sma20-80-atr14 | 2016 | -201,04 | -11,54 | -219,38 | -81,81 |
| h4-sma20-80-atr14 | 2017 | 248,81 | 10,17 | 187,19 | -40,31 |
| h4-sma20-80-atr14 | 2018 | -223,48 | -58,88 | -241,11 | -146,70 |
| h4-sma20-80-atr14 | 2019 | -139,60 | -85,21 | -159,11 | -270,87 |
| h4-sma20-80-atr14 | 2020 | 115,58 | -196,84 | 79,43 | -213,80 |
| h4-sma20-80-atr14 | 2021 | -72,05 | -10,60 | -113,30 | -63,52 |
| h4-sma20-80-atr14 | 2022 | -102,87 | 357,20 | -109,30 | 239,23 |

Privatebase: `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/execution-v1/`
→`gold-eurusd-portfolio-stageA-20261113-v1/`:authorization/economics/tradeforensics/
Goldaudit/targetsource/nativechecks/Fractionreview/scripts vàtimings. Hashes ởJSON;
khôngcommittickprices,rawbars hoặcaccountsecrets. Resume qua protocoldraft,
đợi ASTRAreview; không tự chạyB hoặcmerge.

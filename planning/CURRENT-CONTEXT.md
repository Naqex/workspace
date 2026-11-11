# Current context — Naqex Workspace

11/11/2026 · `WORK: ACTIVE / REVIEW: REVIEWED-PARTIAL / DOC: RESUMABLE`.
Owner đã xóa app Goal rồi yêu cầu tiếp tục task và nghiên cứu portfolio.
Tool xác nhận không còn Goal; không tự tạo lại. Task hiện tại tiếp tục theo giao việc.
Đích: ứng viên đủ bằng chứng để đề xuất challenge FTMO/The5ers và quy trình
được kiểm/sửa theo C1/C2 của [campaign v2](research/CHALLENGE-CANDIDATE-CAMPAIGN-V2-20261108.md).
Không reset trials, negatives hoặc exposure; chưa có ứng viên challenge.

## Việc hiện tại

- **Owner11/11 đồng ý hướng M15, giữ vài giờ intraday, kiểm FTMO 2-Step
  Standard cả funded để hướng tới vốn lớn.** [Quyết định hiện hành](research/PROP-FIRM-FIT-20261102.md#hướng-hiện-hành--owner-đồng-ý-ngày-11112026)
  thay hướng nghiên cứu Swing; không đổi account/leverage/old protocols.
  **Owner đã chọn US500 để nghiên cứu tiếp11/11**; EURUSD giữ tham chiếu.
  Owner đã đồng ý US500 chính/EURUSD khảo sát nhẹ và cho screening11/11.
  [R094/R095 M15 opening-range đã chạy](research/US500-M15-OPENING-SCREEN-RESULTS-20261111.md):
  18books/18reviews,6null0;22,289s,19focusedtests/3actualmutations đạt.
  R094cost-sensitive/fullannualunknown, R095known2022/24âm; không giữ ứng viên
  challenge. Catalogue95records, không reset93records cũ. Không rerununchanged/
  SL/TP/hourgrid. v1calendarnewlinefail0books giữ; v2acceptedproofreuse/4quarters,
  postreview đã sửa field knownclosed để loại unresolved khỏi knownsubset.
  EURUSD đã rà related break/retest dossier, chưa cơ sở mở trialM15 mới.
  Risk/size thật chưa chốt;25USD/10k chỉ offline. `prop_profile.py` chỉ đánh giá
  DD/headroom, chưa news/closures compliance.2025+reserved,khôngbroker/jobnền.
  Owner yêu cầu reuse khung/code mẫu: [5nguồn/17files đã pin và đọc](research/STRATEGY-TEMPLATE-REUSE-REVIEW-20261111.md),
  **đã clone đủ5repo** ở `.runtime/strategy-references/` sau yêu cầu lấy hết;
  README/manifest/index local đã có,12962files/593MiBsource. Ưu tiênLEAN làm
  nguồn EMA/Bollinger/ORB reference. **Owner sau đó yêu cầu full framework cả5**:
  [native runtime guide](../tooling/strategy-engines/README.md) giữ commands/locks;
  đã cài và chạy nativefixtures của cả5, chưa US500migration/parity/cutover.
  Nautilus stable1.x reuse productlock; source2.x chỉ reference, không trộnAPI.
  3Python smoke cùngnet3USD giả lập; LEANSPY2013samplecompleted; Nautilus4direct
  testsđạt,4DBintegrationtestsbịTRUNCATEsetupgatechặn,khôngbypass.
  [Adoption/shortlist](research/STRATEGY-TEMPLATE-REUSE-REVIEW-20261111.md#owner-chon-dung-framework-day-du-ca-nam-engine)
  đề xuất trendpullback trước, bandreentry dựphòng; chưa freeze/newtrial/PnL.
  Giữ R003/R004/R094lineage/negatives và2025+gate; không coi upstreamdemo làedge.
  **Owner tiếp đó đề nghị tập trung xu hướng**: [research delta](research/STRATEGY-TEMPLATE-REUSE-REVIEW-20261111.md#xu-hướng-phá-giả-và-giờ-us500--làm-rõ-theo-owner-1111)
  tách causal falsebreak detection khỏi forecast, giữ shift của pivotconfirmation;
  chưa có majority-success census hoặc proofM15 từ58futures1–12monthpaper.
  NYSEcashclock đã kiểm; FTMOUS500 exactserverhours còn chưa account-verified.

- **Owner10/11 đã thấy Client Area chỉ có Swing10k/25k** cho2-Step/USD/MT5.
  [Standard/Swing và scale](research/PROP-FIRM-FIT-20261102.md#standard-swing-và-đích-vốn-lớn--làm-rõ-ngày-10112026)
  lưu owner-observed availability, official market-break/news rules và đề xuất
  kiểm fundedStandard từ đầu cho đích50k–200k; owner đã đồng ý11/11 ở trên.
  Giữ oldprotocols/costs và account. Không hiểu Standard cấm mọiovernight;
  marketbreak>2giờ khác holding>2giờ. M15khôngđồngnghĩagiữ15phút.

- **Owner10/11 đã chọn thử onlyone và chốt khung tín hiệu M15**,11/11 chọn US500;
  cơ chế/exact exit/risk/frequency/winrate còn cần chọn. [Hồ sơ lựa chọn](research/PROP-FIRM-FIT-20261102.md#only-one-hồ-sơ-mục-tiêu-và-các-case-để-owner-chọn--10112026)
  giữ confirmed/proposed/unknown: incomechính/propvốn/riskthấp,1lane kiểm sâu;
  [researchtimeframe](research/TIMEFRAME-SELECTION-ONLYONE-20261110.md) giữ quyết định
  **M15**, thay tư vấnH1 cũ. **Owner yêu cầu research sản phẩm trước, rút ưu tiên
  EURUSD chỉ vì reuse**; [so sánh instrument](research/INSTRUMENT-SELECTION-ONLYONE-20261110.md)
  đề xuất so cuối EURUSD/USDJPY, US500, vàng theo cơ chế/cost/risk; chưa đo
  target costs/account; US500 và intraday đã được đồng ý11/11, chưa chốt pullback.
  [Đã kiểm sâu offline](research/FOUR-INSTRUMENT-M15-FIT-RESULTS-20261110.md):
  32requests/128M15,4ngày2022 đủcả4assets; cost/rangeproxy khôngFTMOspread/
  edge. Targetminlot/margin của3assets chưađủ; nghiêngUS500đểhoànthiệnhồsơ,
  owner đã chốt US500 sau đó11/11, chưa dispatchstrategy. 4,680s source+review,khôngjobnền.
  [Đối chiếu challenge](research/INSTRUMENT-SELECTION-ONLYONE-20261110.md#đối-chiếu-riêng-ftmo-challenge--bổ-sung-theo-yêu-cầu-owner-1011)
  đã xác nhận published Forex5USD/lot roundtrip, index0, metals0,0007%/chiều;
  spread thả nổi/account-specific vẫn chưa đo, không đổi old costs/outcomes.
  Không dispatch, riskgrid, sửaoldverdict hoặc mởholdout/broker từ hồ sơ tư vấn này.

- **Owner10/11 yêu cầu phân tích vì làm2–3tháng chưa thấy kết quả.**
  [Hậu kiểm delivery](research/OWNER-EVIDENCE-REPORT-20261108.md#12-làm-lâu-nhưng-chưa-có-kết-quả-hậu-kiểm-delivery-ngày1011)
  tách tài sản kỹ thuật khỏi evidence kinh tế; economics/transfer và phạm vi
  dàn trải cùng cản mục tiêu. Đề xuất shortlist tối đa3 và blocker quyết định,
  chưa dispatch hoặc đổi protocol/risk/gates; không tiếp discovery từ audit.

- **Ưu tiên owner10/11: nghiên cứu từ2022 trở đi**, trước2022 là stress/mẫu/
  warmup chọn lọc và reuse. [Cách thực thi](research/STRATEGY-VALIDATION-FRAMEWORK-20261105.md#ưu-tiên-dữ-liệu-gần--quyết-định-của-owner-ngày-10112026)
  áp study mới; không sửa frozen2019/2022 outcomes hoặc bắt thắngmọinăm.
  Development2022–24 giữ exposed/unverified;2025+ vẫn reserved/gate riêng,
  chưa mở data/chạy study mới. Cặp2019/2022 không tự đại diện thị trường2026.

- [R093 options-week](research/OPTIONS-WEEK-RESULTS-20261110.md) đã terminal/
  reviewed:48windows/96cases/8books, stress2019+279,41USD/unit,2022−708,85;
  2022âmtrướcphí nên gác exactalpha.96locators đủ/3.026.580fields/10mutations;
  4workerphases51,181s, khôngjobnền. Catalogue**93/58**,C1C2chưađạt.
  [Portfolio admission](research/PORTFOLIO-RESEARCH-AND-ADMISSION-20261110.md)
  áp dụng P0→P6 vào workflow; chưaalignedequitypanel/sharedaccountproof hoặc
  portfolioPnL. Không yêu cầu mọi sleeve thắng mọi năm; supportedhedge phải
  đăngkýjointtest mới, khôngallpairs/weightsgridcứulosers. NguồnThe5ers03/11
  cóbulk/concurrent/correlatedexposure limits, TermsEAapprovalgiữ; khônggrant.

- [ECB archived source](research/ECB-ARCHIVED-SURPRISE-SOURCE-RESULTS-20261110.md)
  đã terminal/reviewed: 3 sheets × 308 dates tới 12/2024, 1.709 numeric cells
  parser parity, 8 focus cells đủ; cả 4 ngày chưa admit intraday-known-at/access.
  Source 2,593s/3GET; offline review 87,052s/0GET. Giữ v1 citation-link failure,
  v2 chỉ cho đúng inert citation, chặn mạng/external data. Tick pilot vẫn false
  (3/4 ngày đủ), không financial trial hoặc job nền. Catalogue **92/58**, Goal
  active/C1C2 chưa đạt. Không retry package hoặc relax source/fee/holding gates;
  tiếp primary-supported cơ chế khác hoặc material survivor gap có evidence mới.

- [R092 indexpairformation](research/INDEX-PAIR-FORMATION-RESULTS-20261110.md)
  terminal/reviewed10/11:503dates đủ,2018p0,55272/2021p0,41111;khôngretained
  fixedlinearformation,khôngPnL/bot. 1.006pricechecks/8Decimalstats/6mutations;
  source47,373s(stateless88GET/8reuse),statistics3,740s,khôngjobnền.
  [WTItickgapreview](research/WTI-GAP-TICK-RESULTS-20261110.md):6sampledholes
  khôngtick/6controlsđủ,548commonM1sidebarskhớp,9.980fields;khôngpatch/bulk.
  Catalogue**92/58**,Goalactive/C1C2chưađạt. KhôngretryunchangedWTI/indexpair
  hoặcpair/window/lag/model/feegrid đểcứu; tiếp primarysupportedmechanism hoặc
  materialsurvivorblocker cóevidence mới. Source/formationpasskhônglàedge.

- [WTI sourcefixture](research/WTI-SESSION-SOURCE-RESULTS-20261109.md) terminal/
  reviewed10/11:20GET,1.614/1.656pairedroles,2019cả3phiên dưới98%,2022cả3đủ.
  Exact endpoints đủ nhưng fullsessionadmissionfalse; khôngPnL/bulk/R092.
  106.510rawfields/4mutations,source10,338s/review1,725s,khôngjobnền.
  Catalogue91/58/C1C2chưađạt/Goalactive. Khôngpadding/clock/coveragegateđểcứu;
  tiếp source mới cócơsở hoặc cơchếkhác, khôngretryunchanged20requests.
  [Costdiagnosis](research/COST-HEADROOM-DIAGNOSTIC-20261109.md) thêmcáchđọc
  owner:priceâm/costăn hết/netdương/unknown; khôngfeegrid hoặcđổiverdict.

- [R091 round-level](research/FX-ROUND-LEVEL-RESULTS-20261109.md) đã terminal/
  reviewed, không retained:153/227primary opportunities, stress2019−1.466USD/
  2022−2.779USDper100kEURnotional; mid+331/+102,5 nhưng spread420/838,5 đã
  lớn hơn. 1.042geometry-dayrows/6.252cases/24books,7actualmutations;9tests và
  positive/emptycalendar preflight đạt. Source43.764slots/43.583valid,
  3.801reuse+39.963newfromoldraw/0GET,source112,389s/economic5,992s.
  Catalogue**91/58**/C1C2chưađạt/Goalactive/khôngjobnền. Khôngoffset/hour/lag/
  holding/feegrid cứu hoặc promote placebo2019. Tiếp supportedmechanism chưa
  trùng catalogue hoặc materialsurvivorblocker được gỡ bằngsource mới;
  reuse sealed M5packet, không reread oldraw để đọc lại kết quả.

- [Gold SMA signal review](research/GOLD-SMA-SIGNAL-REVIEW-RESULTS-20261109.md)
  đã terminal exit0:30 old books/40.662 H4 evaluations/616 decisions,
  450 entries/166 strategy exits khớp oracle riêng;5 tests/6 actual mutations,
  41,207s, không PnL/fee/rule change. Chỉ conditional recorded-position-path
  audit; Gold vẫn low challenge priority vì time-fit/target costs gaps.
  [Vàng–bạc method delta](research/GOLD-SILVER-METHOD-DELTA-20261109.md) đã đọc
  full CESifo12559, không ex-post regime gate hoặc rerun R067. Catalogue90/58
  giữ/C1C2 chưa đạt/Goal active/không job nền. **Tiếp source-supported cơ chế
  chưa trùng catalogue hoặc material survivor blocker khi có evidence mới**;
  không lặp old signal review, full-sample regime/timing/fee grid để cứu outcome.

- [R090 hourly shock continuation](research/FX-INTRADAY-SHOCK-RESULTS-20261109.md)
  đã terminal/reviewed, không retained:2019stress+592USD/18cơ hội,
  2022−1.583USD/26cơ hội trên100.000EURnotional;2022mid đãâmtrướcphí.
  521weekdayrows/3.126financialcases/12books reviewed,10actualmutations;
  5focusedtests và84syntheticcases/9mutations đạt. Pilot122/122,fullsource
  11.021slots/10.985within60s,36unavailablegiữ,1.990reuse+9.031mới/0GET.
  Fullsource112,748s/economic3,357s/preflight0,275s,khôngjobnền. Catalogue90/58,
  Goalactive/C1C2chưađạt. **Tiếp admission cơ chếkhác hoặc blocker material
  của survivor khi cósource mới**, khônglag/hour/k/side/feegridcứuR090;
  reuse targetpackets trướcthêmrawscan, chưa có recipe tiếp đượcfreeze.
- [R089 temporalresults](research/FX-ABNORMAL-DAY-TEMPORAL-RESULTS-20261109.md)
  đãterminal/reviewed, **not_retained**:13extensionyears164opportunities,
  stress+549USDper100kEURnotional,8/13nămdương/2blocksâm. Data/sample gatesđạt,
  khôngphải enginefail. Annualbootstrapmean95%range−810,92→+769,77USD/unit,
  khôngselectionadjusted/probabilitypass. [Vol-scale diagnosis](research/FX-ABNORMAL-DAY-VOL-SCALE-DIAGNOSTIC-20261109.md)
  vẫn2blocksâm/7nămdương, khôngbasisrủirowrapper;gác exactreversal.
  Source14.126slots/14.034valid,42warmup2009unknown+50late giữ;1954sourcebridge/
  521financialrowsdiscoveryreuseexact. 13testsđạt,23.478cases/90booksreviewed.
  Controlledcheckpoint2010/resume vàOSlockchặnsecondwriter đãkiểm, source701s/
  economic12,357s/diagnostic0,385s. Mọi handle4968/26808vàsessions80717/91023
  đãterminal;**khôngjobnền**. Catalogue89/58,C1C2chưađạt,Goalactive.
  Same-daycausal shockcontinuation đãthựcthi ởR090trên; đây làcheckpoint
  trướcđó. Không nhận diện shockbằngfutureClose hoặcgridcứuR089.
- [R089 FX abnormal-day results](research/FX-ABNORMAL-DAY-RESULTS-20261109.md)
  đãterminal/reviewed:521weekdayrows/3.126financialcases/12books;27selected
  opportunities,stress2019+493/2022+962USDper100kEURnotional,0selectedunknown.
  Qua frozenpriority≥8/netstresspositive đểkiểmrobustness, chưaSL/account/prop/
  cleanOOS/challenge. Source1.954slots/1.947within60s,7unavailable giữ;2019
  unavailablehistory21days giữskipbiếttrướcentry, khôngdrop. Fullworkerphases
  178,088s≈2phút58s. Đây làdiscoverycheckpointtrước temporalresultsởtrên;
  không rerun hoặc giữrecommendationriskwrapper sau gatefail. Catalogue89/58.
- [FX abnormal-day sourcefixture](research/FX-ABNORMAL-DAY-SOURCE-FIXTURE-RESULTS-20261109.md)
  đã88/88slotsreviewed/4mutations,14,723s;5causalfeaturetests đạt. Dự kiếnR089,
  chưarealfeatures/PnL hoặcnewaccountpolicy, catalogue88/58giữ. Runtime đổi
  Python3.12.14/Pydantic2.14.2 nên nativecachev1fail; registeredsourceview riêng
  giữoriginalpins. V2Friday23UTC thiếu8slots, v320UTCchoallweekdays đủ; lineage
  và failures giữ, khôngđổi theoPnL. [Protocol](research/FX-ABNORMAL-DAY-PROTOCOL-20261109.md)
  active20hproxyv2/mean-variance20days/k2/reversal01–08UTC; minimum8 chỉtriage.
  Fullsource/economics đãđượcthựcthiởR089trên; đây làcheckpointnguồn trướcđó.
  Khôngrefetch/rebuild hoặcpilot→fullclaim.
- [R088 EURUSD sau FOMC](research/EURUSD-POST-FOMC-RESULTS-20261109.md) đã
  terminal/reviewed:32windows/24books/192financialcases,459.780sourcefields;
  stress2019+1.013/2022+545USD trên100.000EURnotional, khôngaccountreturn.
  So matchedweek+718/+2.441, eventgate2022 khôngđạt; khôngpromote FOMCmask.
  Successfulfullworkerphases18,662s;khôngjob. Catalogue88/58, C1/C2chưađạt.
  Đã đối chiếu existingR021wrapper/pathrisk/R056: weightshelp/parentexithurts
  không cho bỏSL; R0562/4stressblocksâm. Clocks khác, khônggộpPnL hoặc
  mởstop/lotgrid. [Costdiagnosis](research/COST-HEADROOM-DIAGNOSTIC-20261109.md)
  tách signalâm/costăn hết/netdươngnhưngchưaedge/unknown; chỉrevisit khi có
  source hoặc giảthuyết triển khai cócơsở mới, khônglặp nguồn unchanged.
- [R087 Nhật–Mỹ](research/JAPAN-US-CASH-REACTION-RESULTS-20261109.md) đã
  terminal/reviewed:485phiên/20books/4.850plannedcases,4.322resolved.
  Known stressnet2019−1.432,202/2022−3.705,824JPY/unit;2019mid dương nhưng
  spreadăn hết,2022midđãâm.66phiên thiếu giữunknown, khôngannualPnL;
  gác exactrecipe.5.437.930sourcefieldchecks,962GET+8reuse,successfulphases
  7phút13s, khôngjob. Catalogue87/58 tại checkpointR087, chưa challenge;
  khôngclock/side/feegridcứu hoặc lặp source đã kiểm.
- [Cost headroom](research/COST-HEADROOM-DIAGNOSTIC-20261109.md) đã8books/
  64cases/Fractionreview, khôngmarketreplay. R086funding~94–95%stresscostpool;
  fixedpathbreak-even11,62%/15,26%annual theo model, khôngbrokerfee hoặc safe
  live rate. Ưu tiênphí thật khi cósource mới; khônggiảmspreadđểcứu fundingloss.
  [Nhật–Mỹpilot](research/JAPAN-US-SOURCE-RESULTS-20261109.md)3,193s đãreview;
  [R086guardfix](research/US500-FOMC-PRICE-MOMENTUM-RESULTS-20261109.md#guardprogress-đã-sửa-không-chạy-lại-market-history)
  10transitiontests đạt, giữoldfailure, khôngrerunmarket. Runtimeownershipmanifest
  không ở standardpath checkout này; khôngguessport/account hoặc gọibroker.
- [R086 FOMC price momentum](research/US500-FOMC-PRICE-MOMENTUM-RESULTS-20261109.md)
  đã terminal/reviewed:32books/256cases;net cơ sở2019+60,55/2022+151,62USD/unit,
  stress−63,33/−14,66 nên không qua gate.126mốc/252rawsideinputs đủ;250raws
  reuse+2tailGETs. Sourcefinalprogress vượt180s được giữfailure/recoveryreceipt,
  khôngrerun;economics0,665s/review0,314s.86records/58versions, chưa challenge.
  Publictarget-index funding/spec đãrà, thiếu exactaccountpackage nên chưa
  repricing; chỉ mở lại khi có source mới. Tiếp method/source admission cơ hội
  khác; không fee0/horizon/lookbackgrid cứu outcome hoặc lặp publicpages.
- [FOMC source review](research/FOMC-SURPRISE-SOURCE-RESULTS-20261109.md):
  historicalsource pin2024/359rows có1extra2024row đãquarantine/exposure;
  16focus/240cells reviewed nhưng không intraday-known-at/accessproof.
  [Stock residual](research/RESIDUAL-REVERSION-METHOD-ADMISSION-20261109.md)
  đã đọc fullmethods; deferred universe/PIT/actions/hedge/program/cost, chưaPnL.
- Rà workflow hữu hạn đã xong: audit workspace/Trader 0 errors/warnings;
  16 repo skill entrypoints có vai trò riêng, 76 local links hợp lệ. Chưa có
  lý do gộp/xóa thêm skill hoặc thêm framework. Chi tiết tại
  [skill maintenance](../docs/development/SKILL-MAINTENANCE.md).
- [GitHub workflow gọn](../tooling/github-workflow/README.md) đã merge;
  source Trader/pin workspace ở `930fa768`, workspace `aec89c5` trước lượt này.
  Một đợt liên quan dùng chung branch/PR; issue theo nhu cầu, bảo vệ nhánh giữ.
- [NHP/Fury desk research](research/PAID-EA-MARKET-REVIEW-20261109.md) chưa
  chứng minh exact executable/preset hoặc source ownership. Không mua/cài EA.
  Bài học áp dụng: kiểm chi phí từ joint quotes, SL/risk/account-wide exposure
  và timing thực thi; không suy ra logic vào lệnh đóng mã từ quảng cáo.
- [R083WTIsettlement](research/WTI-SETTLEMENT-COMPONENT-RESULTS-20261109.md)
  đã40books/88datesfullroles,strict/endpointviewsidentical;2019stress−6,298,
  2022stress−1,297USD/researchbarrel. Gác exactrecipe, khônghour/feegrid.
  Cache-onlyconsumer6,330s,0requests;khôngjobnền. R082giữnegative/unknown.
- Chuyểnsang [TokyoUSDJPYmethod](research/TOKYO-FIX-METHOD-ADMISSION-20261109.md):
  importerflow/paydates,9:55reference/10hbankannouncement; liênquanR020/R021,
  khôngindependentedge hoặcretailalpha từdealerprofit. OfficialholidayCSVđãcó,
  chưaallbank/PITcalendar. [Sourcepilot](research/USDJPY-TOKYO-SOURCE-RESULTS-20261109.md)
  đủ61roleminutes×2dates/26.980fields,1,226s;0returns/strategy,khôngjobnền.
- [R084 USDJPY component](research/USDJPY-TOKYO-COMPONENT-RESULTS-20261109.md)
  đã terminal/reviewed:32books/139dates,1.899.620rawfield checks, không gap.
  Mua chính stress2019−125,18/2022−142,93USD trên100knotional; không đạt.
  Lịch phụ dương và diagnostic bán sau fix dương, chỉ là follow-up flags.
  Source+consumer145,106s, không còn job R084; chưa account/prop/edge.
- [R085 extension protocol](research/USDJPY-POSTFIX-EXTENSION-PROTOCOL-20261109.md)
  đã freeze `55fe25d`; [kết quả](research/USDJPY-POSTFIX-EXTENSION-RESULTS-20261109.md)
  terminal/reviewed:240books/15years gồm13năm mở rộng, chỉ6/13năm stressdương,
  2/4blockprimaryâm;gác exactrecipe. Primary625lượt mới chỉ+204,25USD/100k
  notional, chưa SL/account/prop/OOS/forward.12.402.580newfields và139old days
  reuse;calendarcrossyear sửa trước quotes, failure giữ. Source+consumer22phút07s,
  không còn job. [Residual-reversion admission](research/RESIDUAL-REVERSION-METHOD-ADMISSION-20261109.md)
  đã rà và deferred như trên, không mặc định USstock→FX/index
  hoặc tiếp Tokyo grid. Không khôi phục R065 đã gác chỉ để cứu outcome.

## Bằng chứng nghiên cứu cần kế thừa

| Lát | Kết luận / bước tiếp |
|---|---|
| Catalogue | 93 hồ sơ / 58 policy-model versions / 25 native / 9 controls; [catalogue](research/STRATEGY-CATALOGUE-20261107.md). Component/biến thể không tự là edge độc lập |
| FX NYMA4 | [Conditional results](research/NY-FX-GAP-SCENARIOS-RESULTS-20261109.md) âm ở hai năm; strict annual vẫn unknown. Không đổi clock/SL/risk để cứu exact recipe |
| Gold R043 | [Cost admission](research/GOLD-TARGET-COST-ADMISSION-20261109.md) và [loss diagnosis](research/SELECTIVE-LOSS-DIAGNOSIS-RESULTS-20261109.md): funding/spec đích chưa verified; không zero-swap hoặc rerun để cứu outcome |
| R080/R081 | [EU-open](research/US500-EU-OPEN-COMPONENT-RESULTS-20261109.md), [conditional](research/US500-INVENTORY-CONDITION-RESULTS-20261109.md): known net âm, giữ unknowns, gác exact recipes |
| EIA | [Date census](research/EIA-RELEASE-DATE-CENSUS-RESULTS-20261109.md): 103 ngày, actual/PIT exceptions chưa verified; normalclock có thêm archivedPDF proof. [Oil pilot](research/OIL-EIA-SOURCE-PILOT-RESULTS-20261109.md) thiếu USO16:00 Open; chưa bulk/economic admission |
| Phân rã PnL | [Hierarchical attribution](research/HIERARCHICAL-PNL-ATTRIBUTION-20261109.md) đã review; chỉ phân tích sâu survivor/near-miss có câu hỏi |

Private evidence root: `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`.
Các jobs trước đã terminal; không đợi hoặc poll job cũ. Source mới cần đọc
status/progress/result của đúng attempt, giữ pins/raw/seals/failures. Không
rerun unchanged history hoặc thu lại 16 triệu ticks đã kiểm chỉ để đổi observer.

## Đọc theo phạm vi và quyền

| Việc | Cửa vào |
|---|---|
| Research / quyết định | [Index](research/README.md) → protocol/results/private artifacts đúng chủ đề |
| Ý tưởng → kiểm định → vận hành | [Strategy workflow](../tooling/ai-engines/STRATEGY-WORKFLOW.md), skills theo stage; không agent/task riêng cho mỗi hàng |
| Trader source / UI | [Product Plan](trader/PRODUCT-COMPLETION-PLAN.md) → [entrypoint](trader/EXECUTION-ENTRYPOINT.md) → ledger; [UI plan](trader/TRADER-UI-MASTER-PLAN.md) |
| Runtime / MT5 / Paperclip | [Operations](../tooling/ai-engines/OPERATIONS.md), runtime skill; reconcile writer/jobs trước restart; Paperclip giữ native task/run/report |
| Project khác | README/AGENTS của đúng repo; task này không khởi động VI Dubber hoặc integrations khác |

Source, local runtime, broker acceptance và edge là các trục khác nhau.
Holdout2025+, OrderCheck/OrderSend, account/provider mới, chi phí, migration/
xóa dữ liệu và production giữ gate riêng; research report/Goal không cấp quyền.
Tối ưu chỉ khi có bug/nút thắt thực tế; không thêm DB/RAG/UI/skill quản lý mới.

## Lịch sử và khôi phục

[Snapshot trước resume](archive/2026-11-09-workflow-resume/CURRENT-CONTEXT.snapshot.md)
và [manifest original bytes/hash/base](archive/2026-11-09-workflow-resume/MANIFEST.json)
giữ các trạng thái Goal và chi tiết cũ. Link snapshot dùng base gốc `planning/`.
[Context lifecycle](CONTEXT-LIFECYCLE.md) giữ quy trình; không đọc archive mặc định.

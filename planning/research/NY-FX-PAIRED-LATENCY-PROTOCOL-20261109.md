# R072/R073: paired M1 timing15/60minutes trên NYFXMA4

Đăng ký trước fullM1sourcefetch/signals/path/outcomes. [Fixture](NY-FX-TIMING-SOURCE-RESULTS-20261109.md)
đủ registeredsource semantics trong4ngày; khôngproofedge. ParentH1R070/R071
negative khôngđổi. Câu hỏi: giảmđộtrễ, giữcùng mô hìnhM1, có làmMA4reversal
usable saucosts không? Khônghạgates hoặcchọnvariant tốt hậu nghiệm.

## History trước economics

- EURUSD Bid/Ask explicitM1 calendar2019/2022,4exports/1.460dailyURLs. Reuse
 12fixture rawdays bằng cachepathđúngbinding, còn lại existingDukascopy1.51.1.
  Không warmupyear/newinstrument/provider/own2025+. IgnoreFlatsfalse/UTCms/
  volume native millions; canonicalsourceview giữ explicitvolume0/khôngpadding.
- 1writer/CANCEL/events/progress/checkpointseals,deadline900s cumulativephase,
  retry0/cumulativefailurecap1,WAF/token-cacheoff. Nativehelper batches2URLs,
  drainbeforefailure. Khôngskipmissingdays,đổiURLscope,auth hoặc sourcepadding.
  Failure giữ sealedbooks/raw; recovery cần rõ sourcepins/identity,khôngrestart
  chỉ vì observationtimeout. Fullreviewraw/hash/canonical/Fraction trước numeric.
- H1features dựng từ **đủ60explicitM1/side/hour**; không được có minutehole để
  nhậnfeaturebar. Same pairedH1signals cho cảlags, không reuse oldH1features
  nếu M1-derivedbar khác. Coverage report giữ mọiweekday; missingfeature
  unavailable,khôngimpute/nextobserved. Chưa actual ticks/targetbrokerfidelity.

## Exact paired policy

- R072 EURUSDNYMA4reversal15min; R073momentum15mincontrol. Lag60M1baselines
  giữparentstrategy clock với sourceresolution revision, không edgeđộc lập.
  **Không promote control hoặc lag60 để cứu primary15min.** Record mọiversions/
  source revisions/failures,không xóa oldH1negative. Không MA/ATR/SL/costgrid.
- Decisions10/11/12/13America/New_YorkvớiDST từ15pastBidH1+4midpointcloses như
  parent; MA4mean/current included, contra sign/equalityflat; SL1,5meanTR14.
  Intentavailableatdecision,execute exact sourceM1Open tại+15 hoặc+60minutes.
  Scheduledflat15:00NY cho cảlags,khôngdời exitđểgiữholdingtimebằngnhau.
- Cùngpastfeatures/signalcode, cost/geometry vàaccountbook engine cho cảlags:
 10k/year,fixed25USDplannedrisk,1position,minstep0,01/max50,contract100k,
  leverage30declared; commission2,5USD/lot/side,embeddedBidAsk,
  slip0reference/0,00002stress/side,noovernightfunding. Chưaactualtargetspec.
- Processing everyheldminute: missing/crossedcurrentOpen/Close→unknownfreeze
  annualnetN/A. Open-gapSL trướcscheduledclose/queuedintent; same-sidehold,
  opposite/flat closeoldcost/cashtrướcnewentry. IntrabarM1stop/noTP,SLovershoot
  chỉOpengapmodel; notfirsttick. No withinminute reentry; nextqueuedintent
  mới mởlại sauSL. FlatmissingentryOpen skiprecord,khôngfutureClosefilter;
  enteredminuteClosebad→unknownsauentry,khônghindsightentryselection.
- Nulls same decisions/source,0entries.4factors:2years×2directions×2lags×2costs
  ×2null=32books. Paired delta tính từfullaccountbooks gồmpositions/cash/risk
  divergence,không ghép riêngtrades. OldH1/M1delta chỉresolutiondiagnostic,
  không quy toàn bộ cho latency hoặcproofbug nếu không parity.

## Review/gates

Trước actualPnL: syntheticBUY/SELL/cost/15v60intenttime/heldminuteSL/gap/
same-side/flip/equality/DST/pastfeature/futuremutation/missingfreeze/null/margin
fixtures. Reuse parentfinancialhelper/tests; separateFraction source/signal/
path/cost/cashreview đủ32books và5mutations trước promote.

PrimaryR07215min cần cả2stressyears knownflat/net>0/≥100closedtrades mỗi năm
đểưu tiênresearchtiếp. Researchtriage khôngedgecertificate: chưafullpropintrabar
DD/rules/time-fit/OOS/selection/forward/ownerhandover.1day/weekendfixturekhông
thayfullhistory;unknowngiữunknown,khônggiảmqualityđểpass. Khôngincrease risk,
choosesubyears,MA/SL/hour tuning hoặc đảo control thành winner sauoutcomes.

Outputs `execution-v1/ny-fx-timing-M1-history-v1` và `ny-fx-paired-latency-v1`:
immutable raw/seals/source/packs/config/code/protocol pins/census/allbooks/
attemptlogs/events/timing/result/review. Deadline300s cho numericphase sau
sourceadmission. Existing research/qualification/continuity/retrospective
skills đủ;khôngglobalconfig/runtime/service/DB/RAG/UI/broker/accountmới.
GoalC1/C2active;chỉđạt source hoặc32books khônglàhoànthành mục tiêu.

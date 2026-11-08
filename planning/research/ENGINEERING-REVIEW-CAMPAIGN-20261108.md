# Hậu kiểm campaign: đúng kết quả, giảm việc lặp, giữ tiến độ

**C1 chưa đạt; C2 còn giới hạn.** Chưa có strategy đủ bằng chứng để khuyên mua
challenge. [Campaign](CHALLENGE-CANDIDATE-CAMPAIGN-20261108.md) giữ hai tiêu chí;
report này giữ phát hiện engineering và cách tiếp tục, không thay authority.

## Những gì đã kiểm và sửa

| Lát | Phát hiện | Hành động và bằng chứng | Còn thiếu |
|---|---|---|---|
| Native execution | Asia→London2023 dừng gần cuối reference: cash checkpoint sau quyết định che canonical entry checkpoint | Trader `f8879b32`: giữ decision và kiểm cùng pending operation qua cash event; thực tế Dec2023 442.341 ticks/accounting/roundtrip đạt | Asia2023recovery đã completed_verified cả2costs; không đồng nghĩa edge |
| Validation performance | Mỗi validation quét lại cả history để tìm entry/exit source; pilot lại validate typed execution vừa được validate | `edbd1e5f` index chỉ trong một pass; `043656a2` reuse đúng local typed result rồi vẫn kiểm limits/risk/pilot constraints trước observer commit | Không dùng persistent validation cache, không suy speedup cả năm |
| Process/source ownership | Bản sửa isolated không thể dùng runner mặc định trỏ D: và reviewer lại import source D: | Workspace `f781550`: explicit `--source-root`, chặn đổi source sau model import, reviewer theo cùng root; test subprocess thật và negative case đạt | Source D: đã fastforward9fd6cd00 sau nativewriters kết thúc; Discovery12đang pin,không sửa numerical files |
| Metadata | JSON cha còn text Compression/recovery cũ và cap1 khác protocol2workers | Giữ file cha; [recovery](H1-ASIA-RECOVERY-20261108.md)/JSON mới ghi đúng lineage, source, cap1 và deadline. Workspace `758613b` chặn worker/deadline/parallel vượt registration trước preparation/dispatch;5negative cases đạt | Không tự parse free-text protocol để làm authority; old runtime giữ code đã load, không retroactively nhận guard mới |
| Preparation | Recoveryv2 tạo xong quality/tick cache nhưng fail trước simulation vì H1 warmup cache source mới chưa có | `758613b` chuẩn bị/dedup H1 warmup trước worker. Test thực3quotes→2H1hours cho2jobs và load trước dispatch; recoveryv3 reuse quality/tick cache trong7,4s thay vì tạo lại594s | V3đãverified; counter dict của callback cũ chỉ ảnh hưởng telemetry lúc prep, đã sửa và có regression |
| Trial history | Catalogue chưa ghi 6 gold policies dù outcomes đã có | Catalogue đồng bộ47records/34versions:24native FX+4MLcoarse+6metalcoarse; giữ2controls và toàn bộ negatives | Không coi34versions là34alpha độc lập; chưa có selection-adjusted proof |
| Skill | Có workflow hậu kiểm phù hợp, không cần skill mới trùng vai trò | Cập nhật reference của engineering-retrospective: source isolation, metadata inheritance và cash/decision regression | Manual workflow walkthrough; chưa independent model forward-test hoặc native package republish |

## Thời gian theo phạm vi thực sự đã đo

| Phần | Baseline | Bản mới/actual | Phạm vi |
|---|---:|---:|---|
| 6 flat advance windows, state có6.832 ledger events/1.022 ticks |8,89–9,02s|Indexed3,33–3,38s; thêm single-validation1,66–1,84s|Initial/final serialized SHA exact; không observer/calendar và không cả năm |
| Gold H4 long history |Chưa có A/B tương đương|117,19s wall/111,22s CPU|180rows,15annualbooks,2costs,2sizes; coarse indicative |
| Gold H1 intraday |Chưa có A/B tương đương|102,21s wall/100,86s CPU|90rows,15annualbooks,2costs; coarse indicative |
| Đọc lại3 sealed native reference states bằng current validator |Không rerun mô phỏng|0,37–0,38s/state|6.957–7.031events/state; whole-history validation/canonical roundtrip exact |
| Native annual batches |Hai Londonstressparents timeout7200s;Asia2024completed6555,77sworker|Asia2023fixedsource3150,45sworker|Không chuyển latency microbenchmark thành dự báo5× cho cả batch |
| Recovery Asia2023 |Attempt cũ lỗi ở27.223.813ticks/reference;v2prep594s rồi fail cacheH1 trước simulation|V3completed3228,88sbatch gồm prep,3150,45sworker|Không CLI resume giữa scenario; chưa có completed seal để reuse |
| Research/code/review toàn campaign |Không đo active time từ đầu|Unknown|Không suy từ timestamps commit hoặc cộng các khoảng chạy song song |

Private evidence root:
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/execution-v1/`.
`retained-ledger-optimization-v1/` giữ raw A/B; `entry-checkpoint-diagnostic-v3-fixed/result.json`
giữ regression thật; `h1-survivor-tick/recovery-v2-historical-state-compatibility.json`
giữ đọc lại3states. Three single-pass samples chưa ABBA đầy đủ; chỉ gọi là
observed latency range, không benchmark whole-product/annual được chứng nhận.

## Kiểm chứng lần tiếp tục này

- Focused product suite: `test_forex_pilot_entry.py`, `test_forex_pilot_risk.py`,
  `test_forex_financing.py`, `test_forex_horizons.py`, `test_forex_prop_candidates.py`,
  `test_replay_tick_execution.py`:77tests+66subtests đạt. Scope là timing/risk/
  accounting và retained-state guards, không edge.
- Workspace batch/evidence suite đầu:32tests+9subtests đạt, isolated-source fixture
  đầu thiếu dependency module nên một test mới lỗi. Sửa fixture copy package
  thực; hai source-selection tests đạt. Không lỗi numerical engine, không xóa
  failure để gọi lần đầu xanh. Sau H1/cache/cap changes:35tests+9subtests đạt;
 5new cap cases ban đầu dùng sai expectation return-code thay vì exception,
 sửa fixture expectation và5/5đạt; telemetry regression thêm1test đạt. Tổng
 36test cases/14subtests đã kiểm qua các lượt, không rerun unrelated suite.
- Skill environment audit:0errors/0warnings; active combined22.412bytes,
  project10.133/65.536bytes, reserve55.403bytes. Validator skill đạt bằng bundled
  Python; Python nghiên cứu thiếuPyYAML nên không cài dependency vào engine chỉ
  để chạy validator. Scoped skill links0errors.

## C1/C2 và thứ tự tiếp tục

| Gate | Hiện trạng | Bước tiếp |
|---|---|---|
| G0: protocol/trials | Có freeze/pins/trialhistory; metadata defect của parent đã ghi; execution cap có guard mới | Giữ history, không sửa registration đã dùng; legacy outcomes không được tự nâng cấp acceptance |
| G1: timing/state | Có synthetic negatives, actual failure regression và sealed-state compatibility | Chờ annual recovery; kiểm integrity/cash/horizons của đúng source |
| G2: realism | Native EURUSD có observed Bid/Ask; metal chỉ indicative M1Bid+declaredAsk; costs/spec là declared/current counterfactual | Không suy live fills hoặc historical broker realism; phải đối chiếu khi đi forward |
| G3: edge | Hai survivors coarse conditional95%interval đều chứa0, đã selection trên2023/2024 | Chưa đủ edge. Không mở holdout chỉ để kiếm một lần pass; chọn câu hỏi/hypothesis tiếp bằng lý do đã lưu |
| G4: prop/time-fit | Asia2023/2024đãcompleted cảcosts,khôngbreach/chưa phase1target;Londonstressincomplete | Review target/DD/phase/first-breach trước quyết định; không tăngrisk cứu kết quả |
| G5/G6: forward/quyền | System-demo trước đây không là strategy forward; chưa đủ C1 | Chỉ frozen qualified survivor mới đề xuất shadow/demo và gate tương ứng |

Xác nhận lại nguồn hiện hành08/11: [QuantConnect research guide](https://www.quantconnect.com/docs/v2/cloud-platform/backtesting/research-guide)
nhấn mạnh hypothesis/OOS/trial history; số backtests không chứng minh edge.
[FTMO EA/strategy FAQ](https://ftmo.com/en/faq/which-instruments-can-i-trade-and-what-strategies-am-i-allowed-to-use/)
yêu cầu thực thi theo điều kiện thị trường và lưu ý same-EA/allocation; cho phép
EA không đồng nghĩa một bot đã được challenge-approved. Đây là refresh phương
pháp/permission context, không thay terms snapshot của registrations.

Ba locator native sau đã kết thúc; chỉ dùng để đọc bằng chứng lịch sử:
`h1-survivor-tick/batch-2023-v1/PROGRESS.md`, `batch-2024-v1/PROGRESS.md`,
`batch-asia-2023-recovery-v3/PROGRESS.md`. V2 giữ failure trước simulation; V3
giữ nguyên economic/source registrationv2, chỉ sửa supervisor preparation. Chỉ nhận completed_verified sau
dossier/seals/accounting. Nếu không còn ứng viên đủ economics, kết luận chưa
tìm được và chuyển hypothesis; không bảo đảm sẽ có winner sau một số vòng.


## Delta sau khi nativejobs kết thúc

[Nativeresults](H1-NATIVE-SURVIVORS-RESULTS-20261108.md) giữ finalAsia2023/
2024 vàLondonincomplete. [Completeresume](NATIVE-RESUME-REVIEW-20261108.md)
đãcode/test/actual442.341tickparity; rollout **source local**D:9fd6cd00 sau khi
workers đãstop,không đồng nghĩa APIruntime/broker/strategy acceptance.
[Discovery11](EURUSD-DISCOVERY11-RESULTS-20261108.md)52indicativecases74,56s
và[observedhistory12](EURUSD-OBSERVED-HISTORY-20261108.md)đangchạy táchcostmodels;
không sửa phí sauoutcome để gọi qualified. Fullcatalogue13 dùng source-boundcache,
52rowsreuse+572newcases,protocol trướcoutcomes;không nhân rawparse cho24strategies.

Delta mới hơn: [624cases final](EURUSD-CATALOGUE13-RESULTS-20261108.md) đã hoàn tất,
0/24versions qua frozenretention; source đã nhận guard7ab57907 sau khi hếtwriters.
Trạng thái “đang chạy” trong các đoạn lịch sử bên dưới không là job hiện hành.

CustomDiscovery12v1driver lỗi trướcaggregation sauexport vì helpertham sốpath
trùngrawpathfield;v2đổi têntham số,smokejsonwriter vàrawhashadoptionđạt,giữv1.
Singletonguard thử trênjob thật:controller2bịchặn,lockowner khôngđổi,khôngdispatch
child2. Đó là kiểm singlewriter,không fullfaultinjection/restoretest của private
pipeline. Deadlines/processownership dùng helper JobObject đã kiểm.


## Selection review trong lúc catalogue13 chạy

Refreshprimarydocs08/11: [QuantConnect hypothesis/OOS guide](https://www.quantconnect.com/docs/v2/cloud-platform/backtesting/research-guide)
đề nghị giữ thesis/trials/OOS; các mốcbacktest/time của platform chỉheuristic,
không quota hoặc thangchuẩn phải copy. [arch SPA API](https://bashtage.github.io/arch/multiple-comparison/generated/arch.bootstrap.SPA.html)
nhận benchmarknobs và modelnobs×k loss arrays,blockbootstrap và variance options;
[multiplecomparison overview](https://bashtage.github.io/arch/multiple-comparison/multiple-comparison-reference.html)
giải thích so bestmodelvớibenchmark cóxétdependence. Không càiARCH hoặc tự tính
pvalue chỉ từ24annualtotals rồi gọi correctededge. Panel hiện có annualreset,
open/floating ởmột sốH4books và coarseSLuncertainty; chưa là validateddailyP&L
panel cho inferencemới. Chọn actualeligiblecases theo frozenheuristic rồi kiểm
causal/risk/uncertainty phù hợp; không biến624casecountthành624independenttrials.

Catalogue13 reuse52parentrows và572newrows, chỉraw/cachereadvalidation mộtlần
mỗi yearload. Ví dụ observed2010/2011/2016wholeyearscreen17,36/19,34/23,05s,
new44rowscompute15,37/14,99/15,06s. Các sốđo chỉ samecoarseworkload,không so
speedratio với nativefulltick hoặc annualruntime chưađo. Chưa cầnGPU/Rustrewrite
đểtốiưu phasecompute~15s/year. Thời gianchờ dataset thuộc parentpreparation,
không ghi nhầm làCPUcompute. Khi đủ624rows mới chốt bảng/timing cuối.

## Hậu kiểm US500 noise14 — cả2022/23/24 đã hoàn tất

[Kết quả và pins](US500-NOISE-RESULTS-20261108.md) giữ negative version: năm2022
dương nhưng2023/24âm cảcosts, chưa C1. Giữ908closedtrades/3nullcontrols và mọi
raw gaps; không bỏ trade cómissingpath hoặc chọn lại điều kiện giữ survivors.

| Ưu tiên / lát | Phát hiện | Thay đổi/kiểm chứng và giới hạn |
|---|---|---|
| P0: quyết định economics | Noise14failed frozenretention; catalogueFX0/24 | Không promote/tune hoặc mởholdout cứu; chọn economicmechanism khác trước code |
| P0: dữ liệu/path | Cashgaps12/108/62phút qua3năm;5positions cóexposuregap | Bộseal/schema/calendar/DST/sidecheck; khônggapfill. Nativeindex/firstcrossing/risk/targetbrokerspec vẫnthiếu, không DD/prop certification |
| P1: timing/causality | Synthetic test bắt xửlýpending sớm hơnfillminute | Sửa trướcPnL2022;7strategy/orchestrationtests gồmfutureprefix,expiry,hardstopgap,halfday,closedholdoutguard |
| P1: accounting/review | Cần đốisoát ngoài simulator | Reuse financialprimitives;checkerDecimal riêng khớp908trades.4tests bắt net/quote/risk/cash/timing/openbooktamper;không independenthuman/model signoff |
| P1: observability | Statusoverwrite không đủ lịch sử phase | Source2024reuse eventlogger/failurehelper,35events;negativeCLI missinginput giữframes/no-secret diagnostics/release lock, khôngsimulation hoặcfalsecomplete |
| P2: performance/reuse | Download~5phút/năm,verify/load~5s;fullstudy8,56–9,27s | Existing pinnedpackage/calendar,source-bound rawreuse/costcore;không GPU/Rustrewrite hoặc framework mới cho~2s/scenario. Không so native tick speedup |

5data/calendar tests+7strategy/orchestration+4reviewer=16focusedtests đạt qua
các lượt thay đổi;1expectedfailureCLI smoke. Không chạy lạisuite/batch khôngđổi
hoặc tuyênbố mọi lần firstpass. Nguồnpaper/calendar đãlưu ở recipe/qualitydocs;
không đổi installedprovider/model/globalconfig. Existingretrospective/evidence/
research/qualification skills đủroute workflow này; không tạo skill mới trùng.

Data controller20976 và numerical workers đã kết thúc, không lock còn sống
ở các attemptsUS500. Context/index/receipt/catalogue đồng bộ;2025+ vẫnđóng,
zero broker/modelcalls. C2 chỉ scoped engineeringevidence, chưa toànkhungđạt.

## Continuation: lỗi lọc nguồn, range oracle và phục hồi tải theo request

**Các bảng US500 trước correction chỉ còn giá trị truy vết.**
[Kết quả hiện hành](US500-CORRECTED-REPLAY-20261108.md) đã kiểm lại đúng3policies
trên inputcanonical,không đổi rules/risk/costs. Lessonworkflow đã nối vào
`strategy-research/references/source-transformations.md`;khôngtạoskill mới trùng.

| Lát | Phát hiện có bằng chứng | Cách xử lý / bằng chứng |
|---|---|---|
| Loader, P0 | `ignoreFlats:true` loại volume0, không chỉflatprice;1975movingbarsQ4/2012 bịbỏ | Explicitfalse +missing/trueflagnegativeguard;offlinecachedecode9,687s/network0;rerun9affectedbooks122,391s,allchecked |
| Marketdata, P0 | ProviderH1/D1low khôngchứa134tickquotes trong phút18/10/2022 | M1OHLCexact,quarantinerangeupstream;3quotebaroracletests,gapskhônggiải thíchlowcaohơnactualtick |
| Fill/data semantics | Providerzero-volume bars cóthểstale/placeholder;khôngtựfillable | Giữbarnguyên,0stressentry/exitcảhai sidevolume0cả9correctedbooks;khôngclaimtickfills hoặcexchangevolume |
| Funding/state, P0 | Openbook cầnphí calendar giữa lastquote và exclusivehorizon | Thêmendboundaries/lastmarkage;syntheticweekendfee7,68USD,actual2024numericalparity;no forcedclose |
| Recovery, P1 | Quarterly retrycap bịăn bởi lỗi khácngày; từngresponsecache đãsẵn | DùngnativeBufferFetcher/CacheManager perURL,twoURLbatch/drain/explicitfalse;8tests+actual108780rowparity/network0;cap2/URL và24cumulative/start6,không403/WAF/429retry |
| Source reuse | Yearready cóthểcompute khiparenttảinămtiếp | LongRSIrunner reuse3books2022–24,verify+simulate+reviewreadyyears;khôngsource mutation củaactivejobs |
| Calendar capability | Cashsessionhistoryphải cóspecialclosures/DST | Isolated4reviewedpurePythonwheels,khôngglobal/productvenvchange;exportXNYS2013–21,official2022–24everyminuteexact,special2018/2012checked |

Sourcefix/checker/primitives/protocols checkpoint`552f530`;C1/C2campaigntiếp tục.
LỗiV1downloadunknownkhôngclaimfixed;V2timeout/V3/4HTTP500retained. Native
helper khôngrewriteupstream/library hoặc thêmnewprovider/account/keyservice.

FTMOtargetcontractread08/11:public[Symbols](https://ftmo.com/en/symbols/)
textfetch không exposeUS500row/swap, nên không nângdeclaredfees/contractthành
brokerverified. FTMOxOANDA/UStermskhácglobal,khôngcopyUSunit/dividendtermsvào
globalSwingprofile. Gatebrokercontract/financing/dividends vẫnunknown;không
đổicostsauoutcomeđểcứu. Source/paper/currentreadlocatorsgiữ ở study/receipt.

## Delta sau source OR-exit và actual fill availability

IndependentFractionoracle bắt missingEXIT khi một trong RSI/IBS unavailable;
source`82f5ed9` sửa biểu thức OR,10strategychecks+4oraclecases và1SELLhandcase
đạt qua các thay đổi. Failed-regression trước fix được giữ. LongV1cancel lúc
chờinput,old5books giữ;V2rerunaffectedyears rồi soPnL/trades vẫn exact,decision
eventsđượcbổsung. V3hash/source/data/reviewverified6completedbooks rồicontinue,
khôngrerunvì transport đổiattempt. CurrentloopC1/C2 không tự đóng ở checkpoint.

Parent2016 có13BUYsignals nhưng0fills: dữ liệu không có quote saucashclose ở
exactfillminute. Đây là operationalcoverage/inconclusive,chưa lànegativeedge.
[Preclosevariant](US500-PRECLOSE-REVERSION-20261108.md) được đăng ký mới trước
outcome,không dùngfull-dayfuturebars;[results](US500-PRECLOSE-REVERSION-RESULTS-20261108.md)
giữnearzerostress2022,khôngrescuebằngfees/threshold.3prefix/halfday/futuretests
vàrealfinancialreviews đạt. [First→last30](US500-CLOSE-MOMENTUM-RESULTS-20261108.md)
độc lậpmechanismtrial cũngâmcả3years,khôngpromote. PrivateentrypointV1 bịguard
chặntrướcPnL;V2sửaargv giữfailure,khôngclaimallfirstpassgreen.

V6sourceavailabilitykhôngcònrestartquarterkhi1ngàyunavailable:giữrawsidefiles,
unpairedrows vàjournalcóexactpublicURLpath;view chỉtimestampintersection,
originalorder,khônginventquote.11helpertests gồmnegativeauth/rate/schema và
actual2016rawhash/intersection/unpairedlineagereviewđạt. Sourcecompletefalse
đượcgiữ;đủđọcmôphỏngcógap không đủcertifyintrabar/prop. Retrycap không tăng:
qua24cumulativefailthìkhôngretry,URLchưađọcvẫncófirstGET;403/WAF/429/schema
vẫndừng. V5failurevàpartialcacheđượckếthừa,V6khônggửilạiexhaustedASK10/04/2016.

## Lượt tiếp tục 08/11: đóng long studies, sửa reviewer và admission

| Lát | Bằng chứng / thay đổi | Kiểm chứng và giới hạn |
|---|---|---|
| Economic selection | [RSI long](US500-LONG-REVIEW-20261108.md) stress tổng −165,69/−351,21 USD, cả hai không đạt heuristic | 24 annual books, không CAGR; giữ operationally inconclusive years và negatives |
| Reviewer correctness | Entry fill tamper, duplicate ID và closed counter sai từng được chấp nhận | Ba negative regressions fail trước vá; 9 tests đạt sau vá, gồm open Bid/Ask binding; actual24books/72scenarios recheck24,68s, 0 simulations |
| Research scope | [Monthly study](US500-MONTHLY-TREND-RESULTS-20261108.md) là account liên tục, không annual reset | Hai policies×2costs+2null, all arithmetic/annual marks reconcile; fees/gaps/native DD chưa đủ C1 |
| Input admission | 83/132 tháng usable; 2015–16 không có tháng đủ history | `prepare`/`input_coverage` trước book; guard không dispatch unusable year; 7 tests và actual576decision parity26,60s, không rerun numerical |
| Clock/source oracle | [4 intervals](INDEX-MONTH-END-QUOTE-RESULTS-20261108.md): ba rỗng, 2016 có304ticks, Bid exact/Ask thiếu | No quote invention hoặc dataset mutation; UTC-year fix cho private comparisonV2, V1/source giữ; không chứng minh market closed |
| Time/resources | DownloadV6 2.200,38s, new monthly total370,32s/load25,36s/CPU368,42s; RAM quan sát~5GB | Reuse dữ liệu, không model/broker calls. Chưa peak RAM hoặc native speed comparison; chưa cần GPU/rewrite để chạy tiếp cùng negative study |

**Điều chỉnh quy trình:** ngoài raw hash/schema/calendar, phải kiểm dữ liệu có
đủ cho chính lookback/clock/decision/fill mà strategy yêu cầu. Timestamp cash
đủ không tự là quote mới; không dùng hindsight fill-availability làm tín hiệu.
Admission là kiểm năng lực input, không thêm điều kiện kiếm lời sau outcome.
Current monthly source mới chặn bộ input thiếu; source/runs trước guard giữ
nguyên và không được relabel thành pre-admitted. Không rerun để hợp thức hóa.

Đã dùng lại skills evidence/research/qualification/retrospective; những rule
source transformation và timing hiện có vẫn phù hợp, không cần skill mới trùng
hoặc sửa global AI config cho ba guard cục bộ. Context/catalogue/index tiếp tục
route về evidence owners. C1/C2 chưa hoàn tất; bước ưu tiên data/clock/target-cost
fit, không tăng risk, nới costs hoặc mở2025+ để tìm winner. Broker runtime chưa
cung cấp US500 spec trong lần đọc; snapshot EURUSD02/11 không thay thế được.

## Goal turn: commission scenario và false acceptance khi carry

[Source-backed commission results](FTMO-INDEX-COMMISSION-RESULTS-20261108.md)
giữ six-book experiment86,05s và tất cả outcomes âm/dương. Official FTMO index
commission0 khác legacy declared0,5; chỉ component commission có nguồn hiện
hành, chưa historical/wholebroker proof. Code75f7ecf giữ legacy default và
named profile qua sizing/book/manifest/reviewer, không sửa nguồn tài chính
Trader/production hoặc giá/risk/strategy rules.48 focused tests đạt,6actual
books/18scenarios có independent arithmetic implementation review, không
independent human/model sign-off. Bothpolicies vẫn fail frozen triage.

Actualequal-total-costcomparison:1.143trades/10.279decisions và cash/state
exact trong0,21s;reference rẻ hơn có1.041quantitychanges, chứng minh không chỉ
hoàn phí vàoPnL. Legacyactualnoise2022 vẫn qua checker mới, không resimulate.
Guard879344a chặn unfundedcrossdaycarry sau case tái hiện fail;10reviewtests
đạt sau fix. Actual6books khôngcarry nên không numericrerun/acceptance rewrite.

Documentation đã sửa stale2022–24-only CLI claim thành actualcalendar2013–24
support và nhấn mạnh protocol vẫn own data authority. Không cần skill mới hoặc
GPU/framework; existing source/cost/evidence/retrospective workflows đủ route.
Research tiếp [calendar hypotheses](EQUITY-CALENDAR-HYPOTHESES-REVIEW-20261108.md),
đọc method và inputclock trước code/PnL; không grid stop/phí để cứu losers.

## R025 component: kiểm trước khi xây bot

[Protocol](US500-TURN-OF-MONTH-COMPONENT-PROTOCOL-20261108.md) và
[results](US500-TURN-OF-MONTH-COMPONENT-RESULTS-20261108.md) giữ fullcounts/means
và nguồn.1510sessions/2.728.293M1rows mỗi side, nativecalendar/loaderreuse.
TOM không đạt registeredpriority; không bot/SL/risk/accountPnL hoặc policy mới.

| Lát | Phát hiện | Xử lý và bằng chứng |
|---|---|---|
| Gridinput, P0 | PrivateV1 dùng0,01 trong khi sourceUS500/loader dùng0,001 | Validator dừng0,703s trước outcomes;V2 dùng đúng existinggrid, giữfailure/snapshot;không sửa giá/tolerance |
| Missing/clock | CTC cần exactprevioussession, metricmasks khác nhau;halfday/DST |6tests0,035s trước outcomes,fullcalendarlabels trước prices;missingunknown và inputadmission theo năm |
| Arithmetic/lineage | Component phải bind actualraw, không chỉhash cachedsummary | Reviewer codepath riêng bind4709pairs/1510rows/50rawfiles trong11,906s;3tampercasesreject; không independentmodel review |
| Fillrealism | 3days có both-side-volume0 tạientry/exit | Giữflag/source,không gọifillabletick;no numericalrerun hoặc điềnvolume |
| Economics |2/4prioritychecksđạt;2019–21fail | Giữnegative/inconclusive research,không chọnblock đẹp/overnight hoặc rerun thêm ngàygiờ |
| Performance | Validate+component+artifact27,906s | Chỉ giữexactendpoints sau fullrawvalidation, không đọc lại raw chomỗi metric;không cần GPU/Rustrewrite |

Reuse source-transformation/evidence/qualification/retrospective skills đủ;
lỗi drivergrid local không là lý do thêm skill/framework mới. Numeric source
không đổi sauoutcomes. Không rerun completedstudy; khôngjobnền/protocolgate mở.

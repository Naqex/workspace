# R081 — một causal closing-pressure condition trên R080 đã freeze

Đăng ký09/11 trước selectedoutcomes; [plan](MECHANISM-FIRST-EXECUTION-20261109.md).
ExactID `us500-prior-close-negative-euopen-price-component-v1`.
ParentR080 giữnegative/unknown, không sửa originalrule/cost/data. Hypothesis:
negativepreviousclosingreturn là weakobservableproxy choinventorypressure;
BUYovernight chỉsaupressure đó có thểgiữnet tốt hơn. Khôngreplicate signedflow
terciles NYFed, không biếtdealerinventory, không claim độc lập vớiR080.

## Rule duy nhất

Development2019/2022consumed, 503calendarrows từparent, no2025+. Với mỗi
regular exitdate củaR080, lấy **previous expected NYSE cashsession** trong
sameyearcalendar, không lastavailablequote/day. Firstsession chưa cóprior
trongscope→predictorunknown. Previoushalfday→knownabstain, không backtrack
đếnngàyregular cũ. Weekend/holiday dùng đúngprevioussession, giữ date/crossing.

Predictor=midClose15:59−midOpen15:30 previousregularsession; midpoint mỗi
endpoint=(Bid+Ask)/2. M1Close known16:00NY phải≤entrydecision23:30ngàytrước
exitdate. Đòi exactbar/time/grid/finitepositiveBidAsk/noncrossed ởhaipredictor
endpoints; thiếu/crossed→unknown, khôngforwardfill hoặc dùngfutureexit.
Chọn BUY iff predictor<0; zero/positive→noexposure. Khôngmagnitudequantile,
ATR/VIX/spreadfilter/rollingwindow hoặcthreshold khác.

Holding/quotes/funding/costs củaselectedR080 reusebytes:23:31→03:31NY M1Open,
1USD/indexpoint, observedBidAsk,0,25/0,75slip mỗi side,commission0,declaredNY17
funding0. Missingselectedentry/exit vẫnplannedunknown. Unselected khôngfake
fills/net; counts/nullnoexposure rõ. NoSL/sizing/account/equityauthority.

Parentunconditional trênallregisteredrows là diagnosticbaseline; BUYcontrol
trênselectedmask bằngprimary dođịnhnghĩa, khônggatephảivượt chínhnó. Selected
oppositeSELL vànull0 giữđểreview. Trướcđọccost:fullcalendar/predictorcensus/
knownat/selectedmask/sourcecounts; sau đó reuseparentoutcomes khôngreruncost.

## Retention và diễn giải

Mỗi năm≥50selected; ≥98%predictors hợp lệ trong eligiblepriorregularsessions;
≥98%selectedwindowresolved; knownstressnet>0 và>selectedopposite/null. Đây là
triageheuristickhóa trước, khôngsignificance/prop/passcertificate. Báo prior
outofscope/halfday/unknown, positive/zero/negativecohorts, count, net/selected,
midgross→embeddedspread→slip/commission/funding/net cho đủselected vàparent.
Grossmid diagnostic khôngexecutablePnL; spreadembedded khôngtrừlần2.

Nếuyearcoveragefail, giữinconclusive vềfullannualnet; knownsubsetnegative
khôngbácmissingoutcomes. Khôngretain nếugatechưađạt, khôngnới hoặc chọn
riêngnăm tốt. Nếuretainedmớiprotocolrobustness/risk/prop/OOS/forward,không
auto-promote hoặcmua challenge. Khôngcorrelationportfolio khi chưaadmitted.

## Kiểm chứng và outputs

Test beforeeconomic:negative/positive/zero/missing/crossed;calendarpreceding
weekend/holiday/halfday/firstsession;futureprice/netmutation khôngđổiselection;
knownat/units/authority/census;parentimmutable/selectedunknown giữ. Separate
reviewer khôngimportselector:rawM1 reconstruction/Fractionmid/sign, ownprior
calendarlookup; kiểmall503rows/mask/summary/costdecomposition vàactualmutations.
Parentresult/reviewhashes bindR080; full4quartersloader khôngcopy pilotmask.

Private `execution-v1/us500-inventory-condition-v1/`; savedproducer/reviewer,
source/protocol/codepins,config/snapshots/sourcefacts/predictors,rows/summary,
result/review,PID/events/progress/CANCEL;onewriter/nooverwrite/deadline180s.
No newsourcefetch,network/model/brokercalls0. Giữfailure/reviewattempts;
chi phíresearch/code khácwallcompute. Hậukiểmgọn, chỉsửaphầncóevidence.

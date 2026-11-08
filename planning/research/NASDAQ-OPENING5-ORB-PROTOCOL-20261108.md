# R065: NASDAQ opening5 direction, fixed bracket, risk25USD

Đăng ký trước numeric, tiếp [primary method](NASDAQ-OPENING5-ORB-METHOD-20261108.md).
Một recipe, không5/15/30grid hoặc đổi10R sau outcome. Candidate
`nasdaq-cash-opening5-direction-10R-r025-m1-v1`, workspace modeled M1 prototype,
không native broker bot. Source/cost/latency/risk khác QQQ paper, không replication.

## Scope và causal rule

Existing source `USATECH.IDX/USD`, sealed historyv2 resultSHA
`3058b26de169c11ff0fbb841ec11d74df1c81b1035de4cad4d1aad901a0006e7`, reviewSHA
`8b0bced9723138d52242552a66ed74c33f5a43d8d3013288b515d2db7c4b9703`.
Chỉ development2019/2022; first5rule không indicator lookback nên warmup books
đã giữ nhưng không phải numeric input. Closed/exposed development, no2025+.

- Mỗi registered cashsession một row, regular hoặc calendarhalfday. Đủ đúng
 5pairedM1 09:30..09:34, chartBidOpen09:30 và BidClose09:34: tăng BUY, giảm
 SELL, bằng nhau noentry. High/low từ5Bidbars. Không đợi breakout high/low,
 không nhìn fullcurrentday hoặc volume/news để quyết định. Missingopeningbar
 =>skip/no exposure, giữ sourcegapreason, nextday vẫn có thể trade.
- Signal known09:35NY, fill exactM1Open09:36. Missing/crossed entry=>cancel,
 không nextquote/retry. BUYentryAsk, SELLentryBid. Stop first5BidLow/High;
 distance từ entryquote thực tế tới stop phải dương. TP entry±10distance.
 Grid0.001 giữexact. Không TPpartial/trailing/reentry; tối đa1entry/day.
- Từng observedM1 từentry: kiểm openinggap protection trước intrabar. BUY
 dùng BidOHLC, SELL AskOHLC, spread0 với native protective primitive vì side
 prices đã embedded. GapSL ở giá open xấu hơn; TPgap không fill tốt hơn target.
 BothSL/TPreachable sameM1 mà opening không giải quyết=>unresolved, không
 stopfirst/profitfirst. Event intrabar giữ interval, không firstcrossingtick.
- ScheduledEXIT decision close−2minutes, exactOpen close−1minute:15:59regular,
 12:59halfday. Kiểm openingprotection trước scheduledEXIT; không inspect
 intrabar sau scheduled marketexit. Không fakeclose hoặc futurefill cuối mẫu.

## USD market, risk và state

Reuse NASDAQdeclared geometry: initial10.000USD/year, unitcontract1USD/point,
min/step0.01, max50, leverage10, sourcegrid0.001. Reference/stress observed
BidAsk/slip0.25/0.75mỗi side/commission0. Targetbroker geometry/costs/delays
chưa verified. Không paper1%risk/no-slip hoặc TQQQ leverage, không broker call.

Riskbudget cố định25USD/entry,0,25%initialcapital, không compound hoặc tăng
lot sau thua. `size_for_market_stop` reserve grid+2slips và commission, floor
quantitystep; reject invalidbracket/minlot/>50/margin>knownbalance hoặc cash<25.
Stopgap có thể vượt planned25, không hardmaxloss. Cảprofit vàloss dùng canonical
roundtripcost, centsHALF_UP, không doublecharge spread/slip.

Normal day flat trước22UTC nên modeledfunding0. Nếu missing minute khi đang
holding, crossed endpoints hoặc ambiguousprotection: **unknownexposure**,
giữ position/lastknownmark, freeze mọi laterentry trong cùng annualaccount.
Không coi unknowntrade là0/đã đóng, không cộng partialresults thành annualnet.
Knowncash từclosedtrades vẫn báo; netequity/funding sauunknown=null. Year2
là independent resetbook, không inherit unknownyear1. No-reset tại month/day
khi source/trade unknown; restore cần registered evidence, không sửa state.

## Run, review và quyết định đã khóa

2years×2costs×active/null=8books. Null quan sát cùng opening inputs nhưng
không action, cash10k/net0, không chứng minh edge. Source read/pair/index1lần/
year, share read-only input qua scenarios. Pin code/protocol/data/financial
dependencies/paper hash trước PnL; one writer, progress/events/CANCEL/failure,
deadline120s, output mới`execution-v1/nasdaq-opening5-orb-v1` tại campaignroot.

Fixtures trước numeric: opening5/doji/missing/currentfuture mutation, delayed
fill và SELLAskstop, halfday/DST, TP10R/stopgap/bothhit ambiguity, exactEOD
openingexit không dùng laterbar, sizing/cost/margin/risk25, unknownfreeze và
no nextdayresume giả, annualcash/closedbalanceDD/null/noauthority. Reuse native
financial/protection primitives, không US500/XAUfinancial relabel.

Separate Fraction signal/size/firstprotection/ledger oracle kiểm mọi trade,
unknownblockedday, sourceanchors và bothcostsummaries; mutations quote/side/
stop/qty/timing/fees/missingtrade/authority reject. Sameagent/provider, không
independenthuman/modelaudit. Unknown state là data/execution inconclusive,
không negative hoặc positive strategy edge.

**Retain để nghiên cứu tiếp** chỉ khi cả2stressbooks accountstate known,
>=100closedtrades/year và netequity>0; otherwise no promotion. Với knownstate
âm, gác exactrecipe; unknownstate thì giải data/ordering bằng registeredtargeted
source review trước verdict. Báo tradecount/closedcashDD/concentration và
financialsample roles, không dùng closedbalanceDD thay intrabar equity/prop.
ChưacleanOOS/targetterms/prop3–6–12month/forward/handover/C1C2 từ8bookpass.

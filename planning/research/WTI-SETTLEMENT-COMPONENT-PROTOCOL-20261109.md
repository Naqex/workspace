# R083 — WTI pre-settlement reaction component, own related trial

Freeze09/11 trước đọc returns của slot mới. Parent
[R082](WTI-WEDNESDAY-COMPONENT-RESULTS-20261109.md) giữ negative2022 và
unknown2019, không chuyển target/rules rồi ghi đè. R083 là **related timing/
venue-transfer trial**, được chọn sau outcomesR082; không independentedge hoặc
cleanOOS. Không hour/SL/cost grid; một slot chính và hai source scopes đã khóa.

## Cơ chế và primary admission

[CME SER4867](https://www.cmegroup.com/tools-information/lookups/advisories/market-regulation/SER-4867.html)
notice26May2009/effective1Jun2009, [2017filing17-384](https://www.cmegroup.com/market-regulation/rule-filings/2017/10/17-384.pdf)
§current/newprocedure và [dailyprocedure](https://www.cmegroup.com/trading/energy/files/NYMEX_Energy_Futures_Daily_Settlement_Procedure.pdf)
mô tả normalWTI futures settlement window14:28–14:30ET. Hỏi liệu phản ứng
sáng có tiếp tục tới giai đoạn benchmark/rebalancing của chính underlying,
thay vì slot gầnETFclose16h không. Venueclock là cơ sở thử, không nguyênnhân
lỗ đã chứng minh hoặc bảo đảmalpha. Settlementwindow không endoftradingday;
last2tradingdays/expiry/holidays có exceptions; chưa mapped specificCLmonth
hoặc actualCFDsettlement. Không lấy futuresVWAP làm giá khớp CFD.

## Giữ nguyên từ parent

- Retrospective88Wednesdayreleasedates2019/2022,44/year, existingEIAcalendar
  SHA`36aa7870ba27016a4d68fbbe84464cea7eca908c2e860f577f6b661950b204f9`;
  noactualtime/PITallproof. Normalclockdoc không tự biến cohort thành causal.
- SameLIGHT.CMD/USD DukascopyCFDproxy, pinned1.51.1, sourceM1Open interval,
  rawgrid0.001, notCLspecificcontract/tickfills. Reuse176raw/exports/accepted
  full1.162.180fieldreview. **0newmarketrequests**, no2025+, broker/model0.
- Signal sign of10:30→11:00midOpens, equalityflat, feature known after11:01.
  BUYAsk→Bid/SELLBid→Ask; fixed1researchbarrel, notlot/account. SameRTextra
  fees0.05reference/0.10stressUSD/unit; observed-sidecross alreadycharges
  spread. Feesdeclared, nofinancingintradayslot, no SL/equity/prop/permission.
- Controls opposite/alwayslong/alwaysshort/null same plannedcohort; no control
  promotion, no side change afteroutcome. Preserve everymissingdate, nofill0.

## Điểm thay và hai source scopes

Slot duy nhất: scheduleentry14:00, modeledentry sourceOpen14:01; scheduleexit
14:28, modeledexit14:29. Sameone-minuteactionlag and28minuteholding as R082,
exit within nominalsettlement window, notactualexacttimestamp/VWAP. Nofeature
fromfuture; sourceOpen firstquote within1minute can beasynchronous between sides.

1. **Primary strict role**: same31featureminutes10:30–11:00inclusive and29
   holdingminutes14:01–14:29inclusive. Any missing/crossed role → unknown,
   not skipped. Wholeannualnet=N/A if anyplanneddayunknown.
2. **Endpoint-only sensitivity**: same four endpoint Opens; require both
   sides/noncrossed/positive at10:30,11:00,14:01,14:29. Internal gaps do not
   mathematically invalidate a fixed-endpoint price difference; **this scope
   cannot certify intrabar/SL/equity/tradability**. Preserve/report rolegaps
   and cross-close diagnostics; nofillinterpolation or changingprimarygate.
   Added after parent2019roleunknowns, explicitly selection-aware sensitivity.

40books=2sourceviews×2years×5directions×2fees; not40strategies/independent
trades. Primary nextresearchpriority only when both strictstressannualknown,
net>0 and>=35trades/year, no materialbug. Endpointpositive cannot passprimary
or C1; only a separate needs-price-path-reconciliation flag if worth further
checking. Neither viewisPIT/cleanOOS/propready or autoexecutionauthority.

## Correctness/reuse/binding and output

Before numeric: pin thisprotocol/newconsumer and acceptedparent result/rows/
source-review/day-scope-review/raw/native/sourcepins. Rebind exactfrozen
snapshots for LF/CRLF-only drift; record currenthash separately, reject other
content drift. Do notnormalize raw, rewrite oldhashes, recopy missing data or
rerun R082economicbooks. Exactrawhash+acceptedfullreview reused; decode only
for newrole/endpoint consumers, no repeated newfeed/fullsource certification.

Reuse parent trade/signal/financial-review primitives. Synthetic BUY/SELL/
flat/cost/DST/causality; extra tests internalgap=>strictunknown/endpointsunchanged,
endpointmissing=>bothunknown,crossedendpointreject, wrongnewslot. All40books
rebuild Fractionledger independently, allrows/costs/counts/priority/authority;
mutate signal/net/cost/count/view/authority and sourcebindings to reject.
Sameagent/feed, not independenthuman/model certificate.

Private `execution-v1/wti-settlement-component-v1/` in campaignroot. One writer,
nooverwrite, progress/events/pins/snapshots/rows/review/results, deadline180s/
CANCEL. ExistingsealedR082andraws preserved. Separate source-bind/load/compute/
review wall/CPU; no A/Bspeedup claim or newframework. If fails, park exactrecipe;
no furtherclockgrid. If eligible, preregister nextdata/path/risk/prop/PIT stage
before changingrule or accessingholdout. GoalC1/C2 stillunproven.

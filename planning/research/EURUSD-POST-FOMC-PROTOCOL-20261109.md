# R088 — SELL EURUSD sau FOMC, đăng ký trước quotes/PnL

09/11/2026, theo [methodadmission](FX-POST-FOMC-METHOD-ADMISSION-20261109.md).
Own calendar sleeve, không jump/policy-surprise replication, không rescue
R086/R087 hoặc proofindependentedge. Chưa được mô phỏng tại registration.

## Quy tắc và clocks

- All16scheduled events2019/2022 từ acceptedR062calendar SHA
  `fe6fa164e5b81281172d73dccfc773f2dd3f3b37ccd04835417243d3a539a307`,
  datedoriginalschedule và actual14NY đã kiểm. Không unscheduled/selection.
- Primaryanchor là event; matchedanchor là7localcalendar days trước, tính lại
  NY/DST. Mỗi anchor: decision+12h, entrysourceM1Open+12h+1min; exitdecision
  +24h−2min, exitproxyM1Open+24h−1min. Với14NY:02:01→13:59NY ngày sau,
  modeled1minlag, không giảfill tại exactdecisionprice.
-3rules mỗianchor: primarySELL, oppositeBUY vànull. Control không tựpromote.
  Không pricejump/first30min sign/threshold/factorfit hoặc policycontents.
- SourceEURUSD `eurusd`/`EUR/USD`, rawlistedM1UTC Bid/Ask, grid0,00001 theo
  source/previousmetadata, chưa actualtargettickfill. Nativepadding không
  là quan sát; explicitvolume0 giữ. M1sideOpen interval `[t,t+1min)`,
  not jointtick/executablefill. Timestamps/side/units/hash phải admitted.

## Costs, coverage và ưu tiên

Một researchunit=100.000EURnotional, PnLUSD; không actualsafe1lot hoặcaccount.
ObservedBidAskembedded; commission5USD/roundtrip/unit, referenceextraslip0,
stress0,4piproundtrip=4USD/unit. Pip0,0001=10USD/unit. Funding0 **chỉ** vì
window không crossing declared17NYrollover; assertclock trướcPnL, không
copy swap0 sang overnight. Targetbrokerfees/fills và historicalspec chưa verified.

Endpoint-only pricecomponent: đúng2M1Opens là đủ cho fixedunitendpointPnL;
holdingM1coverage/missingminutes được census riêng trước costs, không ffill,
không chứng minh SL/equity/path. Thiếu/crossed endpoint →unknown giữrow;
null0khôngđòiquote. Chưaaccountpolicy, không đặtSL/risk rồi ngầm bỏ intrabar.

2years×2anchors×3rules×2costs=**24books/192plannedfinancialcases**.
16events/32windows không192independenttrades; exposeddevelopment, khôngOOS.
Frozenpriority chỉ khi **cảhaiyear** primary+matched8/8resolved, primary
stressnet>0 và primary−matchedstress>0 trên fullcohort. Thiếu →inconclusive;
negative →khôngưu tiênexactrecipe. Không chọnBUY/control, changingclock hoặc
thêm filter/fees/riskgrid sau khi thấyoutcome. Pass chỉ là reviewrisk tiếp,
không challengequalification, authority hoặc bảo đảm lợi nhuận.

## Source pilot trước history/economics

Đầu tiên4day-sideURLs:31/01/2019 và28/07/2022, mỗiBid/Ask, source-only không
returns/direction/PnL. Kiểm entry02:01/exit13:59NY tương ứng07:01/18:59UTC
mùađông,06:01/17:59UTC mùahè. FullrawOHLCVFractionreview/nativepadding,
endpointclock/grid/side và coverage minh bạch, missing/crossed/tamper tests.
Noauth/WAF/globalconfig/newprovider; max4GET/deadline90s/nohiddenretries,
giữraw/seals/snapshots/status/failure/nooverwrite. No2025+/broker.

Chỉ khi pilot đạt mới chuẩn bị đủ32windowdates/64day-sides (reusepilot/cached
đúngraws), không pilotJan/Julthànhfull16cohort. Đăng ký source/consumer pins
vàpreflight BUY/SELLspread/commission/slip/null/missing/DST/futuretiming;
reviewtấtcảraw/endpoints vàfinancialcases bằng cách số học khác trước verdict.
Native helper/runtime sẵn có, không thêm framework/MCP hoặc account.

Catalogue chỉ thêmR088 khi có implementation/outcome, accountversions58giữ.
Giữ Gold/R021 và cácnegative đã có; nếu cósurvivor mới xétselectionhistory,
coststress/riskwrapper/prop-timefit/OOS/prospective/ownerhandover theo C1/C2.

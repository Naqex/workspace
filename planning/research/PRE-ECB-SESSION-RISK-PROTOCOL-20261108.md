# PreECB R056: một stop theo độ biến động cả phiên, trước outcomes

Tiếp [price survivor2010–24](PRE-ECB-RECENT-PRICE-RESULTS-20261108.md).
Đăng ký **một** adaptation mới, không sửa parent1,5ATRH1 hoặc chọn SL bằng
MAEp95 đã thấy. Cơ chế entry giữ short trước giờ fix; risk wrapper tách khỏi
nguồn edge.20sessions là một tháng giao dịch gần đúng; multiplier2 là tail
protection có chủ đích, không claim 95%coverage hoặc mức SL tối ưu.

## Rule và inputs khóa trước số

Candidate`eurusd-pre-ecb-session-rms20x2-r025-r056-v1`:

1. SELL mỗi weekday, entry target02:00America/New_York, scheduled exit14:00
   Europe/Berlin cùng ngày. Decision tại entrytarget−1ms dựa **chỉ**20planned
   weekdays liền trước. Với từng ngày history, lấy first actual Mid quote
   at/after hai targets≤60s; history endpoints phải valid và exitknown<decision.
   Dùng20days **không nhảy qua ngày thiếu**, không lấy future ngày đang trade.
2. `distance=2*sqrt(mean((exit_mid-entry_mid)^2))` của20historydays; không
   center returns, không ATRH1, không mean BidHigh/AskHigh hoặc futureMAE.
   Positivefinite distance; thiếu history/endpoint thì known-at-entry skip,
   không thay bằng zero/floor hoặc tìm20ngày xa hơn.2010đầu mẫu warmup tự nhiên,
   không PnL trước20days. Không dùng2009hoặc2025+.
3. Quantity tại decision bằng native`size_for_stop(distance,slippage,budget=25)`:
   lotfloor0,01/min0,01/max50,contract100k,tick0,00001,roundingstop ra phía ngoài
   bằng`_stop_at_fill`. SELL stop=entryBid+distance roundedup. Tính lại lot khi
   distance/cost đổi, không giữ lot cũ. Plannedrisk gồm tick allowance và5USD/
   lotcommission+2side slippage,≤25USD; gap có thể vượt, không claim loss cap.
4. Entry firstquote at/aftertarget≤60s; thiếu/lateentry skip sau deadline,
   không xem futureexit để quyết định có vào. Giao dịch tối đa1position, noTP,
   không vào lại sauSL cùng ngày. Pending không tự biến mất khi thiếuquote.
5. Source H1 Bid/Ask extremes/opens đã bound raw, shared
   `protective_exit_for_bar`: stop gap tại actualhourfirstquote, intrahour
   touch tại modeledlevel và timeinterval, **chưa nativefirstcrossing**. Stop
   được kiểm ở opening trước scheduledexit, sau đó intrahour theo sideAsk.
   Scheduledexit dùng first observedquote≥exit, dù trễ hơn60s; ghi delay/path
   gap/carry rõ. Không drop lệnh đã vào do futuremissingexit, không forceclose
   cuối mẫu. Nếu còn mở, báo cash/floating và mark lastobservedBidAsk.

## Phạm vi và book

- Lượt đầu2010–2022 đãconsumed, source13datasets/nativecurrentboundH1cache
  của`eurusd-observed-history-v2`; không2023/24features chưaadmitted.
  Mỗi rawhash/cachepayload/runtime/producer/count/order/grid phải đạt. One
  pass mỗiyear/2costs reusehours,không sửaoldpins hoặc rerunoldparent.
- Reference observedBidAsk,commission2,5USD/lot/side,slip0; stressslip0,00002/
  side. Funding nếu delayedexit qua22UTC:referenceSELLcredit0,31USD/lot,
  stressSELLdebit20USD/lot; weekdays,Wed×3, event trước cùngtimestampquote.
  Reuse sharedCostModel và native financing calendar, không tự gọi brokerverified.
- Continuousbalance10.000USD từ2010, không resetnăm hoặc compoundrisk. Fixed
  leverage30/fixedstartingbalance margin như researchcore, không dynamicbroker.
  Không tự nhân25USD theo năm hoặc account. Từngcohortyear chỉ attribution.
- Internalbudgets giữ100USD/day và500USD từstartingbalance, Praguecalendar.
  ConservativeH1min-equity **diagnostic** có thể vượt floor trước modeledstop;
  không tự coi là actual breach hoặc dùng để simulate native daily/overall
  halt. Cashfloor actualresolvedbook≤9.500 thì halt mởmới; ghifirstcashbreach.
  Dailycashloss≥100 thì stop mởmới ngàyđó. No broad prop compliance claim.
  Không tự đóng forcedlevel khi không cóquote;stopgap/funding vẫn có thể vượtbudget.
- Báo balance/equity/cost/funding/trades/quantity/risk/entryskips/missing/delays/
  pathgaps/openstate và annualattribution. Nội bộriskdiagnostic khác native
  FTMO/The5ers daily reset/loss/payout; 3/6/12monthchallenge chưa đánh giá lượt này.

## Retention trước kết quả

Ưu tiên raw/native tick replay khi primaryreference và stress netequity>0,
stress≥9/13cohortyears dương,cảblocks2010–12/13–15/16–18/19–22stressdương,
khôngcashoverallhalt và≥2.000trades total. Nếu thiếu/gap/riskdiagnostic chưa
chứng minh thì chỉeligibleboundedreview, khôngpromotion. Không cần beat old
parent bằng metric chọn sauoutcome. Nếu khôngđạt giữnegative, không SLgrid
hoặc tăngrisk. Reference/stress là1policy/2costs, không2independentedges.

## Kiểm, trạng thái và giới hạn

Focusedsynthetics trước numeric:historymissing/future/causalRMS,20daysđúng,
SLlotrounding/riskbudget,shortstop atAsk/intrahourgap,exitdelayno-drop,funding/
cash/openmark vànoreset/halt. Reuse financialhelpers, không thêm dependency/
service/UI hoặc sửa activeproduct/livepath. Stage làcoarseresearchprototype.

Pin protocol/helpers/code/tests/runtime/parentseals trướcrun. Rootmới1writer,
deadline300s,status/events/PID/failure/CANCEL,peryearaccountsnapshot+features
vàlogs. Reviewer khácimplementation trong cùngagent kiểm independentRMS/
weights/lot/stop/Fractionmoney/funding/tradepath/cohorts/continuouscash và
mutations. Nativefirstcrossing/prop/unseen/forward/handover vẫn riêng;retained
chưa C1/C2. Giữ0broker/model/networkcalls,holdout2025+đóng.

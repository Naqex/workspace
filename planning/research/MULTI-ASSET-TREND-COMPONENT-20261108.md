# R010 mixed monthly trend: frozen allocation proxy, trước outcomes

Thuộc campaignv2, kế thừa [input đã review](MULTI-ASSET-MONTHLY-INPUT-RESULTS-20261108.md).
Đây là **normalized monthly allocation/cost component**, không broker/account
replay, không SL/lotstep/margin hoặc prop-equitypath. Không mở2025+.

## Recipe và lý do

Một primary:EURUSD/XAUUSD/US500, equal-risk price-trend adaptation. Dùng
average của signs1/3/12tháng theo nguồn AQR đã review; portfolio/signalmix
chưa có trong41policies trước. Baseline:alwayslong với cùng inversevol/cost/
clock, không là independentedge. Không grid/lookback/side/fee/SL tuning.

- Input864records đã freeze và source-review; chỉ đọc normalizedsnapshot và
  pins của nó. Data2013–2017 hỗ trợ warmup; đánh giá **2018–2024** vì prior
  metadata cho đủ commoninputs sau2018, không chọn years bằng returns.
- Tại allocationmonth`t`, dùng13consecutive monthly Bidcloses`t−13…t−1`.
  Giá phải known trước rebalanceobservation10:00NY. Với mỗi asset:
  `trend=(sign(P[-1]/P[-2]−1)+sign(P[-1]/P[-4]−1)+sign(P[-1]/P[-13]−1))/3`.
- Volatility là sampleSD(ddof1) của12simplemonthlyreturns trên13prices;
  **không ATR**, không intradayrangeimputation hoặc futurevol. Vol0/missing
  là inputinconclusive, không chọn floor/regularizer sau outcome.
- `base_weight_i=(1/vol_i)/sum_j(1/vol_j)`; primaryweight=baseweight×trend,
  benchmarkweight=baseweight. Cashresidual0interest; grossabsweights≤1,
  **không scaleup để ép10%target**, không resetportfolio hàng năm.
- StartingnormalizedNAV10.000USD là denominator toán học. Mỗi tháng **fullroll**:
  đóng exposureproxy cũ trước tạo exposure mới; targetUSDnotional=NAV×absweight,
  units=notional/entrymid,continuousquantity=units/contractsizes. Không round
  lên minlot hoặc coi đây là tài khoản10k tradeable. Flatweight không gửi/cost.
- Entry là firstNYsession10:00observation của tháng; exit cùng observation
  tháng sau. Weight chỉ phụ thuộc signalcloses đã có; availability/fillprice
  tương lai không đổi eligibility. Thiếu entry/exit/mark sẽ haltchain và ghi
  inconclusive, không bỏ tháng lỗ, fill0 hoặc reweight riêng survivors.
- SourceEURUSD observedtick; US500M1proxy; GoldBidM1+declaredAsk theo costs
  dưới. M1/asynchronoussource quotes chưa là jointportfolio actualfills.

## Costs đã khóa: declared scenarios, không target contract

Giữ assumptions đã có để so component; không gọi chúng là historicalFTMO,
currentaccountverified hoặc conservativebaoquát mọi broker. Futures/forwards
excessreturns của literature khác spotCFDprice+funding; không claimreplication.

| Asset | Contractsize | Reference / stress slippage mỗi side | CommissionUSD/lot/side | FinancingdebitUSD/lot |
|---|---:|---:|---:|---|
|EURUSD|100000|0 /0,00002|2,50|refBUY9,30/SELL−0,31;stressBUY/SELL20;weekday22UTC,Wed×3|
|Gold|100|0,10 /0,20|2,50|20 /40;weekday22UTC,Wed×3|
|US500|1|0,25 /0,75|0|1 /2 mỗi calendarday22UTC;không triple|

GoldAsk=Bid+0,50(reference)/+1,00(stress). Hai assets khác giữ observedAsk,
không charge spread thêm. US500commission0 là declaredpubliccurrent-profile
scenario đã có trước đó, không sửa phí historicalbooks cũ. Financing đúng
eventtime trong `(entry,exit]`, không zero, không inferpoints→USD. Targetpoint/
swapmode/dividends vẫn unknown; gross-vs-cost decomposition phải báo rõ.

Fullmonthcost dùng sharedCostModel/calculate_round_trip_cost:pricePnL±BidAsk,
quantity/commission/slippage/funding,roundmoney2digits. Close old proxy→NAV
mới→quantitymonthmới, NAV không reset; NAV≤0 là failedcomponent, không bỏ đoạn.

**Cuối2024:** giữ Decemberexposures mở, mark bằng lastNYSEclose2024Bid/Ask
(GoldAskdeclared). Chỉ entrycommission/slippage và funding tới cutoff,
**không exitfee/slippage hoặc forcedclose**. Báo cash/floating/endmark riêng.
Metric là normalizedmonthlyproxy, không daily/intrabar equityminimum hoặc
calibratedchallengeprobability. Cohortyear attribution theo allocationmonth;
exitJanuarythuộc Decembercohort, không giả calendarJan1/Dec31accountreturn.

## Acceptance và review

- Cả84allocationmonths cần source/history/price inputs hợp lệ trước numeric;
  thiếu thì inconclusive/correctaffectedinput, không silent skip.
- Ưu tiên nghiên cứu native/risk tiếp khi primary reference&stress finalNAV
  >10k,stresspositive≥5/7cohortyears và cảblocks2018–2020/2021–2024positive.
  Báo benchmark/exposure/returncontribution/funding/tails/monthlyendpointDD;
  heuristictriage không edge/propcertificate. Không cần beatbenchmark bằng
  một riskmetric chưa có; reportdifference rõ vì primaryexposure có thể thấp hơn.
- Test tính tay weights/known-at/missing/funding/endmark/continuousNAV trước
  numeric. Separate floatvol/weights +Fractionmoney/cost/funding review trên
  toàn allocations,sourcebindings/census/mutations. Không gọi reviewer khác
  implementation trong cùng agent là independenthuman/modelsign-off.
- Hai candidates×2costscenarios,1writer,deadline120s,CANCEL/status/log/pins/
  source-snapshot và elapsedwall/CPU.0network/LLMworker/broker/holdout.
  Không auto rerun failedattempt hoặc chọnscenario tốt sau outcome.

Survivor vẫn cần actuallotgeometry/SL/jointquotes, nativeprop/DD/timefit,
selection-aware/unseen và prospectiveforward/handover trước C1/C2. Nếu không
đạt, giữ economics/assumptiongaps và negativeversion, không tự hạ financing
hoặc tăngleverage để tạo challengecandidate. Source_data là fixedartifact;
hash nó và reviewedreceipts, không parse14GBraw lại cho arithmetic này.

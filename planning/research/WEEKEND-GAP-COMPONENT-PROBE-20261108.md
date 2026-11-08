# R024: component probe trước khi viết strategy

Đăng ký sau [metadataadmission](WEEKEND-GAP-DATA-RESULTS-20261108.md), trước
khi tính bất kỳ gap/return/PnL mới. Chưa triển khai strategy. Câu hỏi: với
quote đủ đúng giờ và khoảng gap lớn hơn chi phí biết lúc vào, **fadegap giữ
12giờ** có còn return dương sau declaredcosts trong hai năm đã chọn không?
Không exactpaperreplication, không gọi kết quả exposed là cleanOOS.

## Scope, clocks và sample trước outcome

- Reuse đúng EURUSD2019/2022 rawCSV/H1bindings từ admissionv1;103weekends
  cùngdenominator, không chọn lại năm từ payoff. Không2023+/provider/network
  data mới,2025+holdout, OrderCheck/OrderSend, account/payment hoặc production.
- ReferenceFriday17:00NY/Sunday17:00NY với America/New_York/DST, scopeboundaries
  như metadata. Fridaylastquote phải nằm trong5phút trước Friday17NY;
  Sundayfirstquote phải trong5phút sauSunday17NY. Unknown/late giữ trong report,
  không đổi firstquote sau khi đã xem returns. Qualitywindow dựa trên độ mới
  quote và publictargetopen cách reference5phút, không tune theo gap/PnL.
- Entryclock Sunday17:10NY, exit Monday05:10NY:12giờ sau. Chọn sau10phút để
  tránh pretendfill tại firstspread/openauction; fixedhorizon để test cơ chế,
  không chọnexit từ path. Đây là declaredresearch timing, không chứng nhận
  broker/holiday tradeability. Firstobservedtick tại/sau mỗiclock phải tới
  trong60giây; không có thì missing/unresolved, không carrygiá hayfillbackward.
- Không dùng H1high/low làm thứ tựtick. Đọc exactrawticks cho4quote events:
  Fridaylast,Sundayfirst,entry,exit. Save sourceordinal/time/BidAsk/hash,
  không sửa source/export/cache. Quotechoices causal và monotonic.

## Signal, costs và controls

1. Gap = midSundayfirst−midFridaylast. Directionfade SELL khi gap>0, BUY khi
   gap<0; gap0 ghi no-direction, không lấy eventualreturn chọnside.
2. Primarygating biết tại entry: abs(gap)≥3×(entryspread +5USD/100.000 +
   2×0,00002). Đây là requiredpotentialmove lớn hơn ba lần exanteestimated
   roundtripcost với stressslippage; futureexitspread không vào filter. Không
   đổi factor3 sau outcome. Sameeligibility cho cảcostscenarios/controls.
3. Referencecommission2,50USD/lot/side, slippage0; stresssamecommission và
   slippage0,00002/side. ActualrawentryAsk/Bid và exitBid/Ask theoBUY/SELL;
   netprice includes cả hai spread sides, slippage và commission. Initial
   estimate dùng entryspread để gate, **realizednet dùng actualexitquote**.
4. Declaredrollover17NY:entry17:10Sunday→exit05:10Monday không đi qua boundary
   kế tiếp, nên funding0 chỉ trong declaredsingletradingdaycomponent này.
   Không áp0 cho overnightstrategy hoặc gọi đã xác minh historicalFTMOswaps.
5. Followgapdirection là directionalcontrol, cùngquotes/filter/cost; flatcash
   baseline0. Secondary ungatedfade cho tất cả nonzerogaps có đủ data để mô tả
   tác dụng filter, không thay primary bằng bản đẹp hơn. Hai view/controls có
   liên hệ, không independentedges hoặc tăng strategycount.

Primarymetrics theo từngyear/cost: eligible/missing/late/zero/cost-filtered,
netpips/bps bình quân/tổng, dispersion/concentration/positiveeventcount.
Không PnL account10k/50k, sizing/SL/risk0,25%, drawdown/proppassrate hoặc
holdoutclaim vì chưa có tradingpolicy/riskpath. Có thể báo perstandardlot
chỉ như unitconversion, không giả mỗi lệnh risk25USD.

## Kiểm và quyết định

- Before actualnumerics: deterministicfixture BUY/SELL, spread/commission/
  slippage, nofutureexitdata trong eligibility, exactdeadline/latequote,
  boundary/DST, missingevent và nullbaseline. Oracle độc lập arithmetic;
  keep script/protocol/source/runtime/rawpins, allfailures và attempts.
- Chỉ ưu tiên viết specstrategy nếu primarynet dương ở cảhai years/costs và
  không materialerror; báo sample/uncertainty và concentration trước chuyển.
  Đây là localdevelopmenttriage hữu hạn, không edgecertificate hoặc hard
  rejection cảfamily. Không lift threshold, thêm giờ/TP/risk hoặc chọn chỉ
  weekend đẹp để tạo survivor. Nếu không đạt giữ negative và reviewreason.
  Không có eligibleevents hoặc sample quá ít thì ghi inconclusive/undefined
  cho expectancy, không biến thiếuquan sát thành economic0 hoặc tựdropyear.
- Một worker,deadline300s, CANCEL/status/log, outputmới
  `execution-v1/weekend-gap-component-v1`. Rawline scan reuse quoteindices khi
  bindings đúng; không re-export/QDMdownload hoặc tạo executionengine thứhai.
  Existing financialsemantics là tham chiếu units; component là priceprobe,
  không replacement shared risk/executionowner hoặc authority gửi lệnh.

Chưa numericaloutcomes tại lúc đăng ký. Native/targetcost/prop/selection/fresh
holdout/forward gates vẫn cần cho C1; C2 chỉ được nâng trong scope đã kiểm.

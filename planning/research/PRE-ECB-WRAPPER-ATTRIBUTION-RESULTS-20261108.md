# Đã tách được: weights giúp, parentexit/SL làm giảm kết quả — 08/11/2026

Thực hiện [protocol68a9014](PRE-ECB-WRAPPER-ATTRIBUTION-20261108.md) sau
[clockprobe](FIXING-CLOCK-TRANSFER-RESULTS-20261108.md).7tests trước numerical;
không strategy/backtest mới, không đổi parent1,5ATR/risk25USD hoặc broker.

## Kết quả dễ đọc

Trên **cùng lệnh đã quan sát, cùng tổnglot, cùngentry02NY/clock14Berlin/cost**:
weights của parent giúp so với equal-lot normalization; phần exit theoSL của
parent làm mất nhiều return so với giữ đến14:00. Cảhai thứtự phân rã đều có
signs này, không cần chọn riêng thứtự đẹp. Đây là matchedarithmetic, không
causalproof hoàn chỉnh hoặc chiến lược bỏSL đủ điều kiện quỹ.

USD trong bảng là các cells giả định trên commonmask, **không accountPnL hoặc
backtestcủa bot khôngSL**. Equal-lot dùng meanquantity hậu nghiệm, không phải
cấu hình trade được đề xuất. Risk của noSL chưa được kiểm.

| Năm / phí | Equal-lot, tới14:00 khôngSL (A) | Lotđãquan sát, tới14:00 khôngSL (C) | Parentexit/SL, lotđãquan sát (D) | Weightingeffect C−A | Parentexiteffect D−C |
|---|---:|---:|---:|---:|---:|
|2019 chuẩn|+793,62|+903,41|−153,54|+109,79|−1.056,95|
|2019 cao|+570,46|+674,68|−340,52|+104,22|−1.015,20|
|2022 chuẩn|+334,73|+522,05|+3,18|+187,32|−518,87|
|2022 cao|+223,74|+364,97|−134,86|+141,23|−499,83|

Mẫu2019:259matchedtrades/cost,2019Dec25 vẫn thiếuquote14:00 và bịexclude khỏi
contrast, **giữ parent−24,00/−24,36USD** riêng. CộngD với excluded khớp parent
fullnet−177,54/−364,88USD.2022:260matchedtrades/cost,khôngexcluded.1038rows là
519dates×2costs, không1038independenttrials hoặc hai freshvalidations.

Equal-lot parentexit(B):2019−210,59/−399,08USD,2022−205,64/−306,51USD.
Đườngphânrãngược cũng cho weightingafterexit dương+57,05/+58,56 và
+208,82/+171,65USD; stopeffectởequalweight âm−1.004,21/−969,54 và
−540,37/−530,25USD. Interaction lần lượt−52,74/−45,66/+21,50/+30,42USD;
không tự nhận một attributionunique không phụ thuộc thứtự.

## Đã kiểm điều gì?

-4parentbooks2019/2022/2costs đúngseal/config/source/input; typedcostdiagnostic
  kiểmgross/commission/slip/cash/funding/count. Trong scope này parentfunding0,
  flat, khôngpending; nếu khác toolreject chứ không tự bỏ khỏi mô hình.
-Từngmatchedentrytime/bid/side/quantity khớp source-boundendpoint packet;
  duplicate/foreign/misalignedentryfail. Unitcosts và originalprice-net được
  tính lại; exactFraction giữ repeatingmeanlot và cả2decompositionidentities.
-Reviewer riêng không import attribution/costhelper:2076pricechecks cho
  1038matchedtrades,4cells/interaction vàpartitionD+excluded=fullparent khớp.
-8stopdates được chọn trước bằngearliest4reference/year, không theooutcome:
  rawhash giữ, registeredSLgeometry và firstobservedAskcrossing nằm trong
  parentH1exitinterval.4/8fills cùngmodeledlevel;4/8quote vượtSL, overshoot
  reference0,12/0,55/0,14/0,28USD (sum1,09,max0,55USD) trênsample này.
  Cross-cost packet xác nhận sameentry/distance/interval cho8dates ởstress,
  lượnglotstress riêng được dùng tínhpriceproxy, không đọcrawlại.
-Đó là raw-firstquote evidence, **không brokerfill hoặc fullnativeannual
  replay**. Không dùng1,09USD làm annualbiascorrection/errorbound. Fullannual
  firstcrossing/internalrisk/prop/DD còn chưa kiểm; oldH1SLxấp xỉ giữlabel.
-Source/profile/test/protocol/inputpins snapshot trướccompute; reviewer/source
  và hashes giữ trongprivatepacket. Sameagentreview, không độc lậphuman/model.

## Quyết định và điều chưa được phép suy

1. **Chưa có lý do đổi cách chia lot chỉ để cứu bản này.** Trong scope đã
   tính, weights đang giúp. Kết luận này cụ thể cho parent/cost/window/commonmask,
   không chứng minh sizing tối ưu trên thị trường khác hoặc dữ liệu mới.
2. **Cách thoát theo1,5ATR là chỗ đáng nghiên cứu tiếp.** Chưa có nghĩa mọiSL
   đều có hại hoặc có thể bỏSL. NoSLcounterfactual chưa có intradayMAE/DD/
   margin/headroom/unknowncarry;2019missingexit không cho dựng portfolio liên tục.
3. **Không tự nớiSL mà giữ lot cũ.** Nếu đổiSL, sizing/risk/lotgrid và account
   path cũng phải kiểm lại. Một rulemới vẫn cần freeze/trial/exposure, costs,
   uncertainty/tick/prop/forward; không chọn ATRmultiple theo PnLđãxem.
4. Bước tiếp có ích là đo adverse/favorableexcursion trước14:00 trên chính
   observedquotes, bound vào stopdistance/risk đã có, rồi mới đăng ký một
   sensitivity nhỏ có cơ chế. Đo path/risk trước, không mởgridSL hoặc nới
   tiêu chí để biến bảngcounterfactual này thànhchallengecandidate.

Oldparent vẫnparked, khôngpolicyimplementation/riskchange/promote. Đây là
decisiondelta từ “chưa biết SLhayweights” sang “weightshelp/parentexithurts
trong arithmeticcommonmask”; C1/C2dài hạn chưa đạt.

## Thời gian và receipt

| Lát | Actualwall | Ghi chú |
|---|---:|---|
|7focusedtests|0,263s|2×2tính tay,uniform/scale,exactrepeatingmean,invalidq/Nan,entrytamper/duplicate/missingexit,CLIbadbinding/nooverwrite|
|4bookattribution|0,895s|Reuse sealeddata, khôngrawread/simulator/LLM/broker|
|Independentarithmetic +boundedrawstops|9,438s|Rawhash+chỉparseprefix/windows támstopdates; khôngfullannualtickreplay|
|Cross-costsamplebinding|Chưa timer riêng|Readonlyreceipt, khôngrawscan hoặcfinancialrerun|

Không suy thời gian toàn phiên research/code/review từ các timer này. Không
cần rewriteCPU/GPU/Rust hoặc dependency mới cho phép tính nhỏ như vậy.

Private root:
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/execution-v1/pre-ecb-wrapper-attribution-v1`.
Manifest/source-snapshot,`result.json`,progress/events/failureconventions,
`review.py`/`review-result.json`,`review-acceptance.json` giữfullreceipt.
ResultSHA`022207cb47559cb2f7f99f84c166321218e68f7a1f0c343ee01a286d38a7bb8d`;
reviewerSHA`04fad6c78cff5f554617fb17e276cf10088b883510d89ac96469b89505a4e464`.
Cáccommands đãterminalexit0; khôngjobnền, không newGoal tựsinh, không2025+,
OrderCheck/OrderSend/newaccount/paidprovider/challenge/production.

# Discovery9 — lịch sử dài và tính khả thi theo size

Sau indicativeDiscovery8outcomes2021–2024, SMAđược giữ để research nhưng mẫu46
lệnh và minlot skips chưa đủ C1. Các rules trend/meanreversion khác vẫn giữ
negativehistory. Không tune entry/exit/ATR/timeframe theo kết quả đã xem.

## Câu hỏi trước outcomes bổ sung

1. Giữ exact3rules trêngoldH4 có bền qua nhiều regimes hơn không?
2. 10kminlot skip có làm test chỉ thực hiện được một tập con tín hiệu? Với
   **50k cùng0,25%** (125USDplanned/trade) số lệnh/edge thay đổi thế nào?
   Size50k không phải permissionmua account hoặc tăngriskpercent để ép target.
3. Economics có còn khispread/fees/stress đã frozen? Sourcebasis/tick/proprisk
   gaps củaDiscovery8 vẫn ghi nguyên, không gọi coarse là challenge path.

## Frozen test

ReuseQDMM1cacheXAUUSD, export2009.11.01–2024.12.31 vào output mới, không update
hoặc đọc2025+. Eval15annualbooks2010–2024 riêng, warmupNov–Decnăm trước;
2021–24đã consumed,2010–20là retrospective extension sau xem lateroutcomes,
không gán cleanOOS. Data/cost/spec/source hashes phải khóa trước numeric.

Ba exactpolicyIDs và entry/exit/clock giữ [Discovery8](METAL-DISCOVERY8-SCREEN-20261108.md).
Market100oz/lot,grid0,001,minimum/step0,01,leverage10; costs0,50/1,00spread,
0,10/0,20slippageperside,2,50commissionperside/lot,20/40financingat22UTCWed×3.
Giữ observedBidM1,declaredAskH1approximation, gaps và noforceclose. Không tự
roundrawquotes, nớiSL/risk hoặc bỏphí. Cả3×2costs×15years×2sizes=180rows hữu hạn.
Annualaccounts không cộng thành continuousportfolio. Một inputaggregation cho
mọi rows, timer/status/failure/cancel/deadline900s, attempts mới, source snapshot.

Initial10k/risk25 và50k/risk125, normalize net%/meanR theo từngrow denominator.
Commission/quantity/lotfloor làm normalizedcurves có thể khác; không scaling
coarsePnL10k×5 để giả kết quả50k. Defaults legacyEURUSD/metal10k không đổi;
explicittypedmarket cho50k/lot sizing, geometry/profilebound failclosed.

Ưu tiên deepreview tối đa2rule-size versions có totalnetdương ở cảcosts và
stressdương ít nhất10/15years; rank weakest-five-yearstresssum (2010–14/15–19/
20–24), normalized theo accountsize. Samefamily/sizes không independenttrials;
không chọnsize chỉvìnominalUSD cao.0trades/minlot infeasible làunknown/inconclusive.
Không sửa thresholds hoặc sampleyears sau outcome; giữ tất cảfails. Descriptive
selection khác inferentialtest, không calibratedpassprobability/edgeproof.

Survivors phải qua actualBid/Ask/tick risk, prop3/6/12month path, uncertainty/
selection, frozenfreshholdout và prospective reconciliation trước C1. Không
tạo18tháng “đủconfidence” từ syntheticresamples; C2review fixes riêng. Existing
EURUSDnativebatches giữ source78a8397f; chỉ isolatedmetalsworktree được đổi.

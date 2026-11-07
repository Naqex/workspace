# Discovery12 — observed Bid/Ask history, fixed survivors

Kế thừa [Discovery11](EURUSD-DISCOVERY11-RESULTS-20261108.md): fixed1/2pipAsk
khác observednativecosts nên chưa thể bác bỏ hai cơ chế từ M1model. Mục tiêu
là kiểm lại các policies **không đổi** trên observedBid/Ask trước2023. Không
tune tham số/risk hoặc tự hứa sẽ tìm được winner để đóng C1.

## Phạm vi trước outcome

- Local licensed QDM cache `EURUSD_TICK_TW`, chỉ export UTCNov–Dec2009 cho
  warmup rồi từng annual2010–2022. Không update/download, asset/account/provider
  mới hoặc2025+. Đó là exposed historicaldevelopment, không cleanholdout.
- Source Trader9fd6cd00, exact code/runtime/protocol/driver hashes trong config
  và source snapshot. Numeric kernel `simulate_coarse` với **observed_bidask**;
  hourlymidextrema từ actualmids, không cộng fixedspread lênBid nữa.
- Giữ London16–20 và Asia→London recipes/version hiện tại; Nov–Decnăm trước
  làm100causalH1warmup,13annualaccounts riêng10k/risk25,minimumlotstep0,01,
  oneposition/noTP/no terminalforceclose. Không cộng books thànhCAGR/portfolio.
- Reference/stress cùng observedhistoricalspread; commission2,50USD/lot/side,
  slippage0/0,00002 mỗi side; financingBUY9,30/SELL−0,31reference và20/20stress,
  Wed×3/22UTC. Financing/spec là declaredcurrentcounterfactual, không lịch sử
  broker target. Không đổi costs sau outcome để cứu policy.
- CoarseSL vẫn modeledlevel/hourOpengap, không actualfirst-crossing fill hoặc
  fulltickDD/prop. Actualspread/mid cũng có thể đổi signals, nên không gán mọi
  khác biệt với M1study chỉ cho spreadcost. Survivors vẫn cần native review.

## Quy trình hữu hạn và phục hồi

Một ownedworker; QDM export/aggregation tuần tự, không hai QDMinstances.
Warmup2009 là dataset đầu, sau đó13years×2policies×2costs=52rows. Export raw,
hash, stricttimestamp/order/grid, source-bound H1cache một lần/dataset; reuse
cho nhiều candidates/costs và nghiên cứu sau. Không sort/dedup/fillgaps.

Perdatasetdeadline3600s,total28800s là ceilings, không ETA; quan sát thực tế
chưa đủ để dự đoán toàn13years. Giữ≥32GiBfree trênE:, không xóa dữ liệu để
đạt ngưỡng. `PROGRESS.md`/progress.json/stdout/childlogs ghi stage/year/ticks.
`CANCEL` dừng childtree thuộc job; export chỉ đọc cache, giữ rawoutput dở.

Parent dùng JobObject của supervisor hiện có; crash/timeout/cancel không để
childPython/QDM chạy mồ côi. Controllerlock ngăn writer thứ hai; lock sau hard
crash phải đối soát PID trước gỡ. Không tự retry failed dataset. Khi explicit
resume cùng config/source, năm đã sealed được kiểm rồi reuse; attempt dở giữ
nguyên, raw đã có seal hợp lệ có thể reuse ở attempt mới. Không gọi aggregation
partial là mid-file resume. Các source/input drift fail rõ, không sửa hashes.

## Quyết định trước kết quả

Giữ cả52rows/negativeyears, netbalance/equity/floating/trades/financing và ba
bands2010–14/2015–19/2020–22. Same heuristicretention củaDiscovery11: totalnet
dương hai costs, stresspositive≥9/13years, cả3bands stressdương. Đây chỉ là
triage, không edge/passprobability hoặc automaticrejection cảfamily.

Cuối job có artifact integrity/cash/source review tự động và summary mô tả;
không thay agent review về selection/dependence/uncertainty. Không auto mở
holdout/OrderCheck/OrderSend/mua challenge. C1/C2 giữ ACTIVE tới đúng evidence,
không coi tiến độ/exit0 hoặc positivebacktest là đủ. Giữ nguồn/log/artifacts
trong private campaignroot `eurusd-observed-history-v1/`.

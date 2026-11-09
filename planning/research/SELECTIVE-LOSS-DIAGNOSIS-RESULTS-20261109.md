# Chẩn đoán sâu: ưu tiên funding/spec của SMA vàng, chưa chỉnh chiến lược

[Protocol](SELECTIVE-LOSS-DIAGNOSIS-PROTOCOL-20261109.md) `1a5191f` chọn R043
trước breakdown mới. Helper `a74c6ab`; không rerun simulation hoặc đọc lại
5,4 triệu nến phút. Đọc 30 sổ đã được kiểm: 15 năm2010–2024 × 2 costscenarios,
mỗi sổ bắt đầu50.000USD, plannedrisk125USD/lệnh. **Không là một account15năm,
lợi nhuận một năm hoặc kết quả challenge.** Bản này giữ research survivor;
chưa chứng minh edge ngoài mẫu/prop-fit, không đổi verdict từ bảng tỷ trọng.

## Bước mới trong workflow

| Bước | Phạm vi | Kết quả lượt này |
|---|---|---|
|D0: đọc nhanh sổ cũ|Mọi bản khi quyết định chuyển bước, không thêm raw/compute|R080/R081 yếu rõ: giữ gác, không phân tích thêm filters/regimes. R056 reuse attribution/path đã có|
|D1: chẩn đoán sâu|Bản từng giữ hoặc near-miss có câu hỏi cụ thể|Chọn một bản SMA vàng vì đã qua frozen screen, còn funding/time-fit gaps|
|D2: thử cải tiến|Chỉ khi thấy tác động có cơ sở, protocol/version mới|Chưa đổi holding/side/SL. Ưu tiên xác minh target funding/spec trước; không cộng savings giả định|

Đây là cửa ưu tiên công việc, không thêm một ngưỡng tự động loại strategy.
Materialbug vẫn sửa cho mọi bản, kể cả lỗ. Không gọi gate này là đã đo được
tỷ lệ bỏ sót hoặc tiêu chuẩn thống kê universal.

## Tiền đi đâu? — lệnh đã đóng

Primary dưới đây là **220lệnh đã đóng của phí cao**, gộp15sổ năm riêng biệt.
Pricebenchmark được định giá lại cùngfillpath với declaredspread; khônglà
actual executablemid. Tỷ trọng chia cho tổng khoản bất lợi26.578,88USD,
**không chia cho lỗ ròng** vì bản này tổngclosednet vẫn dương.

| Khoản làm giảm kết quả theo mô hình | USD | % tổng khoản bất lợi |
|---|---:|---:|
|Những lệnh có mid-price PnL âm|15.377,13|57,85%|
|Giữ qua đêm, lệnh đã đóng|8.709,20|32,77%|
|Spread khai báo|1.719,00|6,47%|
|Trượt giá khai báo|687,60|2,59%|
|Commission|85,95|0,32%|
|Roundingdebit|0|0%|
|**Tổng khoản bất lợi**|**26.578,88**|**100%**|

Các lệnh mid-price dương đóng góp29.158,50USD; sau tất cả khoản trên còn
closednet **+2.579,62USD**. Cộngfloatingcuốicácsổ1.697,04 và trừ241,60funding
củavịthếcònmở→annualnetsum **+4.035,06USD**, khớp oldreview. Khôngforceclose
hoặc coi floating làcash đạt target. Credits/rounding đượcgiữriêng, không
doublecountspread đãtrongBidAsk gross. % này là accounting shares dưới
declaredmodel, không phải %lỗi gâyra thualỗ hoặc khoản chắc chắn loại bỏ được.

| Diagnostic closedtrades | Phí chuẩn | Phí cao |
|---|---:|---:|
|Sốlệnh|219|220|
|Midbenchmark gains / losses,USD|29.270,96 /16.023,04|29.158,50 /15.377,13|
|Tổngcostdragdebits,USD|5.719,95|11.201,75|
|Funding trongcostdrag|77,28%|77,75%|
|Spread trongcostdrag|15,15%|15,35%|
|Slippage trongcostdrag|6,06%|6,14%|
|Commission trongcostdrag|1,51%|0,77%|
|Closednet,USD|+7.527,97|+2.579,62|

Costdrag pool khác totaladversepool, vì không gồm cácprice-losses. Không cộng
hai scenario hoặc diễn giải reference→stress là causal cost-only effect:
quantity/entry/stop/timing có thể đổi theo phí; đếm219/220đã cho thấykhácpath.

## Nút thắt và hành động hợp lý

| Ưu tiên | Phát hiện | Việc nên làm / giới hạn |
|---|---|---|
|1|Funding chiếm77,75%costdrag trongstressmodel; targetswap/mode/point/historicalrate chưaverified|Xác minh public/accountspec đúngquỹ/program/symbol vàunits trước địnhgiá lại. Không giả declared40USD/lot là phí broker thật hoặc có thể giảm tùy ý|
|2|Các lệnh giữ>5ngày đóngnet+15.071,46USD, cũng trả8.136,80funding|Giảmholding có thểcắtcảwinner. Khôngđặtmax5days từbreakdown; muốnthửphảipinningnewrule/replaychi phí/risk|
|3|BUYclosednet+6.142,85,SELL−3.563,23 trongstress|Chỉdiagnostic trongmẫuđãxem; khôngtựchuyểnlong-only hoặc gọi đó làOOSedge|
|4|135stoploss+2gapstop cónetâm17.544,68;83strategyexitsnet+20.124,30|SLcắtlosers là cơchếquảntrịrủiro, không vìphầnlớnlỗởSL màbỏ/nớiSL. Exitreason/feesoverlap, khônggộpvàocùngpie|
|5|Closedcash/time-fit vàconcentration cũvẫnthiếu|Không tăngrisk đểchạytarget. Chỉsau economics/specsđủmớiactualprop/tick/selection-awarevalidation/prospective|

>5days dựa earliestmodeledexitinterval, khôngactualtickholdingduration. Không
lấycáccohorts này thànhentryfilter. Đây là lý do ưu tiênthứtự, chưacausal
optimization hoặc cam kết cải thiện lợi nhuận sau khi đổi rule.

## Kiểm chứng, thời gian và reuse

-4tests mới cho adversebudget: positive/negative net,mẫu số0, credits/rounding,
  invalid/nonfinite/unknown/doublecount mismatch;7EURUSDdiagnosticregressions đạt.
-Actual30books/439trade-costcases kiểm từsealedbooks; producer reuses frozen
  financialreviewer, reviewer Fraction riêng khôngimportproducer/helper.
-6actualmutations net/spread/funding/holding/percent/authority bịchặn. Summary/
  cohort/denominator/closed-open reconciliation đều khớp, oldnet giữexact.
-Producer0,632s,review0,259s≈0,891s;0new simulations/rawrescans/network/model/
  brokercalls/no2025+. Khôngwhole-engine speedup hoặc tính thờigianresearch vào.
-Sameagent, khôngindependenthuman/feed; source/declaredmodel acceptance táisử
  dụng từoldreview, không giảđãreviewrawhoặcverifybroker lầnmới.

Private `execution-v1/gold-selective-loss-v1/` giữmanifest/source snapshots,
trades/books/summary/result/review/events/progress; savedproducer/reviewer ở
campaignbaseE:. ResultSHA`3bd9ba0354e6ca5e402eac4ce65a6126d9b742b4b3e45290ac6d2e82b1561301`;
reviewerSHA`5bcea45cf3f7e653ef7ea191fd6539b4895c78c357e3389b4c71b3b25a89e26a`.

## Research và skills

Phương pháp TCA/implementation shortfall đối chiếu[AQR2018](https://www.aqr.com/Insights/Research/White-Papers/Transactions-Costs-Practical-Application),
[CFM2018](https://www.cfm.com/wp-content/uploads/2022/12/168-2018-Improving-Trade-Execution-Systematically.pdf),
[CME/FIA2011](https://www.cmegroup.com/education/files/TCA-4.pdf). Chỉ dùng cách
phân biệt signal vớicost/execution vàbenchmark; khôngclaim đã đo actual IS/
marketimpact hoặc nhữngnguồn này xác nhận Goldrecipe. MốcD0/D1/D2 do project
thiết kế, chưaexternal audit hayuniversalquantstandard.

Cập nhật nhánh[skillkiểmđịnh](../../.agents/skills/strategy-qualification/references/selective-loss-diagnosis.md),
khôngskillmanager/service/config mới. Positivewalkthrough:Goldretained→D1;
negative:R081gross/netyếu→gác;materialbugsourcequarter→correctnessreview
bấtkểPnL. Đây làmanual/source-confirmedrouting, khôngindependentmodeltest.

Skill validation đã chạy: `quick_validate.py` đạt, scopedskilllinks0errors/
0warnings; maintaineraudit0errors/0warnings. Global12.279B,project10.133/65.536B,
projectreserve55.403B,combined22.412B không đổi; thêm conditionalreference,
không globalinstructions/config/hook/MCP. Repo skill đã sửa, chưa publish/
assign package Paperclip hoặc chứng minh một boundedworker đã nhận nhánh mới.

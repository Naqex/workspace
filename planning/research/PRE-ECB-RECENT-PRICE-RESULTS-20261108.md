# PreECB giữ qua 2023–2024: tiếp risk wrapper, chưa challenge-ready

Đã hoàn tất [protocol](PRE-ECB-RECENT-PRICE-PROTOCOL-20261108.md), commit
`12f7bb6` trước outcomes mới. **Giữ để đăng ký một risk wrapper.** Cùng SELL
02NY→14Berlin và costs cũ, không chọn lại side/clock. Hai năm gần đây dương,
combined2010–2024stress14/15năm dương và cả4blocks dương. Chưa có account
equity/SL/native prop/cleanOOS/forward, không đề xuất mua hoặc chạy challenge.

## Số mới và combined

Đơn vị pip per1standardlot, **không phải lợi nhuận tài khoản10k/risk25USD**.
Một bot có stop phải tính lại lot; tổng trên những cơ hội1lot không chứng minh
được trade1lot an toàn.16ngày thiếu của giai đoạn cũ và3ngày mới không bị xóa.

| Mẫu | Resolved / weekdays | Primary reference, pip | Primary stress, pip |
|---|---:|---:|---:|
|2010–2022, reuse [kết quả trước](PRE-ECB-LONG-PRICE-RESULTS-20261108.md)|3.375/3.391|+6.359,8|+5.009,8|
|2023|259/260|+290,7|+187,1|
|2024|260/262|+288,9|+184,9|
|**Combined2010–2024**|**3.894/3.913**|**+6.939,4**|**+5.381,8**|

2023–24stresssum+372,0pip; từng năm≥200resolved, combined≥10/15stressyears
dương và total>0 đạt. Fourblocks2010–12/13–15/16–18/19–24 là+424,0/+1.951,9/
+1.854,3/+1.151,6pip. Không tăng số mẫu độc lập bằng cách cộng13yearstudy và
2yearcontinuation hoặc hai costs.19ngày unavailable/late giữ trong artifacts;
không interpolate/carry/forceclose hay ghiPnL0.2023min/maxstress−82,5/+180,6pip,
2024−51,8/+73,7pip; tails lớn hơn mean rất nhiều, không bỏ SL/giữ lot cũ.

Đây là exposed robustness, không cleanOOS, chưa selection-adjusted edge.
Positive2010–24 chỉ giúp ưu tiên một bước code/risk; không tự làm C1/C2 đạt.
Hướng và giờ đã biết từ nghiên cứu trước; không có claim blind discovery.

## Nguồn, correctness và review

- Read/hash/order/count toàn raw2023/24 trong explicit scanner hiện có:
  27.549.175/20.687.149ticks. Native H1 cache2023/24 có producer cũ; không
  sửa binding, không executeoldproducer hoặc épcurrentguard nhận.
- Scanner giữ first-after/predecessor proofs cho3targets/ngày theo helper cũ;
  chỉ entry/14:00 dùng numeric.14:15 không được tính outcome, không thay exit
  khi thiếu. Missing/late giữ explicit trong522plannedrows.
- Separate code đối chiếu1.044endpointslots với source proofs và frozen H1
  firstquotes làm read-onlyoracle, independent clock arithmetic/Fraction:
  2.076financial cases/8annual summaries và60combinedsummary rows khớp.
- Strict prior result/review/summary/manifest/dataset hashes được kiểm trước
  compute, không dùng expected=current fallback. Không rerun13oldyears.
- Reviewer v1 có kiểm normal weekdaycensus đúng nhưng mutation mấtrow chỉ
  so length trực tiếp, chưa gọi guard thật. Giữ `review-v1.json` và source
  snapshot; v2 cho mutation đi qua cùng calendarcensus guard và bị reject.
  Không rerun numeric hoặc sửa outcome. `review-v2.json` là review hiện hành:
  sourceprice/futuretime/wrongnet/falseauthority/missingrow đều bị chặn.
- Cùngagent/provider, khác codepaths; chưa independenthuman/feed/model,
  fulltickSL/accountpath hoặc thực thi broker. Không thay currentcostprofile
  hay nhận declaredfee là current/historical FTMO/The5ers cashcontract.

| Lát | Giây thực đo |
|---|---:|
|2023rawscan + numeric + seal|16,506|
|2024rawscan + numeric + seal|12,118|
|Toàn lượt|28,835wall /28,547CPU|
|Separate review v2|0,334|

Không có numeric failure/retry; reviewerfix chỉ chạy lại review bị tác động.
Numeric PID25372/session6206 và reviewer terminal0. Không worker còn chạy
của lượt này.0network/model/broker calls, không đọc2025+.

Private`execution-v1/pre-ecb-recent-price-v1` dưới campaignroot giữ config,
manifest,source snapshots,peryear sourceproof/events,summary/combined-summary,
result/events/progress/review-v1/review-v2. Runner/reviewer tại campaignroot.
ResultSHA`5a7db14720f3c1a7c3e9cd0f522b5a220df8743f3ca53538be909d9bd8d8a4df`;
reviewer-v2SHA`07e549a0d752fc1ba755a3be637b6e0df7c08a5f622cde4179abae82ae63d8f7`.

## Tiếp tục đúng mục tiêu

Giữ55researchrecords/41accountpolicies; endpointcomponent không là policy
mới đã native-integrated. Parent1,5ATRH1 vẫn parked. Bước tiếp ưu tiên **một
wrapper** với volatility của cả holding-session, risk25USD/cơ hội trên
normalized10k và lot giảm theo stopdistance; không SLgrid, không tăng risk
để ép target. Freeze exact warmup/known-at/gap/stop/lot/margin/accountwide
limits/endstate và acceptance trước economics mới.

Ưu tiên reuse financial/risk/prop semantics hiện có; nghiên cứu/helper không
tự mở live path hay sửa activeproduct/runtime. Native/tick validation phải
đi sau một candidatewrapper cụ thể đáng kiểm.2023/24nếu cần H1features phải
có source-admission riêng, không tái dùng oldcache bằng cách sửaproducerpin.
Holdout2025+,broker/account/provider/payment/production vẫn gates riêng.
Goal C1/C2 vẫn active; không cần tạo goal/skill/data service mới.

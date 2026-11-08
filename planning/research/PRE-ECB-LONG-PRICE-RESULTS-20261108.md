# PreECB giữ được lợi nhuận giá qua 13 năm; chưa là bot challenge

Đã hoàn tất [protocol](PRE-ECB-LONG-PRICE-PROTOCOL-20261108.md), commit
`5255c69` trước các outcomes mới. **Đạt tiêu chí ưu tiên đăng ký risk wrapper**:
primary stress dương12/13năm, cả4blocks dương và mỗi năm≥200resolved. Chưa
có account equity/SL/prop hoặc clean OOS; không đề xuất bỏ SL hay mua challenge.

Giữ SELL02:00NewYork→14:00Berlin, first observed quotes≤60s, source/cost/side
không đổi.2019/2022reuse exact baseline outcomes và quotes đã review, không
rerun.11năm còn lại qua native raw-bound cache loader hiện hành, không sửa
old producer pins hoặc rebuild cache để ép nhận.

## Kết quả trong phạm vi price/cost

Pip ở đây là cộng các cơ hội **1standardlot**; không là tài khoản10k/risk25USD.
Nếu một cơ hội có net1pip thì tương đương10USD/standardlot, còn bot thực phải
giảm lot theo stop/risk. Không lấy tổng bảng làm lợi nhuận được phép giao dịch.

| Năm | Ngày đủ giá / weekdays | Primary stress net, pip |
|---|---:|---:|
|2010|261/261|+314,0|
|2011|260/260|−362,9|
|2012|260/261|+472,9|
|2013|259/261|+167,1|
|2014|259/261|+667,3|
|2015|259/261|+1.117,5|
|2016|260/261|+712,9|
|2017|259/260|+592,9|
|2018|259/261|+548,5|
|2019|259/261|+301,9|
|2020|260/262|+39,8|
|2021|260/261|+215,7|
|2022|260/260|+222,2|
|**Tổng**|**3.375/3.391**|**+5.009,8**|

Primary reference+6.359,8pip; opposite control reference−12.708,9/stress
−14.058,9pip. Spread/phí làm cả hai sides không là hai số đối dấu hoàn hảo.
Stressmean khoảng1,484pip/resolvedevent; lợi thế trung bình nhỏ so tails:
có ngày−160,0pip dù tổng nhiều năm dương. Không giữ nguyên lot cũ rồi bỏSL.

Four stress blocks2010–12/13–15/16–18/19–22 lần lượt+424,0/+1.951,9/
+1.854,3/+779,6pip. Đây là robustness của một hypothesis đã exposed, không
13independent tests, không adjusted pass probability hay proof tương lai.
16ngày thiếu/late giữ trong denominator và artifacts, không tính0 hoặc nhận
chắc là ngày nghỉ. Chưa dựng account liên tục qua các missingexit đó.

## Kiểm và hindsight boundaries

- Clock/source:3.391weekday events,6.782endpoint slots kiểm với cache first
  time/sequence/BidAsk và independent calendar arithmetic. Native loader kiểm
  full raw SHA/cache payload/runtime/producer cho11newyears.2019/22 dùng
  original raw/quote linkage receipts, không tự reattest raw hiện tại bằng reuse.
- Fraction review13.500resolvedevent×view×cost cases và52annual summaries:
  unit conversion,spread/commission/slip,counts/min/max/mean/concentration,
  blocks và frozen retention. Không import producer price/cost để tính oracle.
- Raw oracle bổ sung22quotes/11earliest-resolved dates, source prefix first-
  after +predecessor/sequence; fileidentity trước/sau giữ nguyên. Không gọi
  source prefix là full-year firstcrossing/SL hoặc tick-equity oracle.
- Năm mutations reject:futuretimestamp,wrongside,wrongnet,missingrow,falseauthority.
  Cùngagent/provider, khác implementation; chưa independent human/model/feed.
- Hậu kiểm phát hiện một reuse assertion trong private runner dùng fallback
  expected=current nên chưa đủ bảo vệ original linkage. **Reviewer bổ sung
  strict check mọi original linkage pins, old result/review/manifest hashes và
  identity từng quote/primary outcome**, đều đạt. Không rerun số học không đổi,
  không sửa script/manifest đã freeze; next wrapper phải dùng strict linkage
  ngay preflight. Numeric verdict không dựa vào assertion yếu đó một mình.

Không có thay đổi SL/risk/holding hoặc bug trong số tiền/giờ được phát hiện ở
lát này. Parent1,5ATRH1 vẫn parked; catalogue không tăng policy count bằng
endpoint probes. Không gọi retention là thực thi an toàn hoặc full strategy edge.

## Hiệu suất và lưu bằng chứng

| Lát | Thực đo |
|---|---:|
|Toàn numeric/preflight/source checks/ghi13year artifacts|50,583s wall /31,469s CPU|
|Reuse2019/2022 mỗi năm|0,069/0,072s trước shared pin-check overhead|
|Separate cache/raw-prefix/clock/Fraction review|5,237s|

Không rerun accepted2019/22 economics hoặc parse toàn rawticks cho returns.
Giữ full raw hash guard cho newyears; cache reuse không là native tick replay
speedup. Chưa cần GPU/Rust hoặc refactor engine chỉ cho phép đo này. Source/
receipt lookup và review gọn đủ dùng; không tạo service/RAG/dashboard mới.

Private `execution-v1/pre-ecb-long-price-v1` dưới campaignroot giữ config/
manifest/source snapshots/peryear events/source-receipts/summary/result/events/
progress/review. Numeric PID8332/session38252 và reviewer terminal0; không
worker còn chạy của lát này.0network/model/broker calls, không đọc2023+.
ResultSHA `5870edefde0522ee791256d06989a8e08585f4192d135e6d5336f7d6c6a846a3`;
reviewerSHA `77fed8a6d1954a1fd01f0922f8067376cb17258be8b4b99a8477c242034c8817`.

## Bước được phép tiếp

Đăng ký **một** wrapper với scale volatility theo cả phiên giữ lệnh thay vì
ATR một giờ. Không grid SL, không giữ lot cũ khi stop rộng hơn. Cần chốt trước
outcome: history/known-at/gap policy, stop definition, cost-aware sizing và
lotgrid/margin, oneposition, pending/unknown/endmark, continuouscash/equity,
internalrisk/prop/time-fit, controls và retention. Chọn điểm dừng/risk phải có
lý do vận hành, chưa có nghĩa chọn được mức tối ưu từ MAEp95 đã thấy.

Ưu tiên source-bound features và coarse bounds để triage hữu hạn; retained
wrapper vẫn cần native firstcrossing/tick-account oracle, selection-aware
unseen protocol, prospective reconciliation và ownerhandover. Không mở2025+
để tuning, không gửi broker từ kết quả price component này. Goal C1/C2 active.

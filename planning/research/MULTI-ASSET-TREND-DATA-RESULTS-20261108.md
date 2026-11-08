# R010: thiếu ATR đầy đủ là nút chặn; chưa backtest portfolio

Thực hiện [source admission](MULTI-ASSET-TREND-DATA-ADMISSION-20261108.md),
không tính tín hiệu return, PnL, financing hoặc portfolio mới. Kết quả chỉ
giúp thiết kế thí nghiệm tiếp theo; không sửa/admit lại R009/R053 đã freeze.

## Đã xác định được gì?

| Giai đoạn | Tháng kiểm | Đủ13monthlycloses | ĐủATR14fullsessions | Đủ cả hai theo rule cũ |
|---|---:|---:|---:|---:|
|2014–2017|48|3|4|0|
|2018–2021|48|48|7|7|
|2022–2024|36|36|25|25|
|Tổng|132|87|36|32|

Năm2018–2024 đủ monthlyhistory **84/84**, nhưng chỉ32months có ATR từ14
cashsessions đầy đủ từng phút. Đây là constraint của **old ATR/risk recipe**,
không tự là lỗi engine, proof dailyvol vô dụng hoặc lý do bỏ qualitygate.
Thêm quan sát tháng không giải quyết phần thiếu extrema/range trong ATR.

Đã bind/review12sourceyears2013–2024,48quarterpairs/96canonical side seals và
proof lineage; chọn140/144exactmonthendpoints. Thử observation-asof mới với
upperbound120s **vẫn140/144**, không giúp thêm monthlyhistory. Giữ negative
feasibility này, không thử cap lớn hơn hoặc tạo reusable asofplatform/skill
cho một tối ưu không có lợi ích ở dữ liệu đang dùng.

Giá nguồn không bị pad/fill/rewrite. Known-at=baropen+60s, latest completed
Bid observation trong cùng session; không dùng Ask để đo Bid-only signal
hoặc coi đó là tick executable. Canonicalinput là retainedpairedprojection;
unilateral rawBid bị parent bỏ chưa được phục hồi, không claim fullrawBid.
Selected exactcloses khớp dailyfacts cũ; đoạn asof không làm eligibility cũ đạt.

## Data fit cho hướng nhiều tài sản

| Market | Có gì | Cần xử lý trước component/portfolio |
|---|---|---|
|US500|Source-bound retainedBidAskM1/cashcalendar2013–2024; monthlyhistory sau2018 tốt|ATRfullsession gap; targetfinancing/point/corporateactions chưa xác minh; không suy0PnL là evidence|
|EURUSD|ObservedBidAsk tickhistory2010–2024, config/receipts/caches đã có|Pin subset/commoncutoff/monthlyextraction, fundingclock và jointprice semantics; metadata phase chưa rereadraw |
|XAUUSD|ObservedBidM1, long2010–2024 và oldsource receipts|Ask cũ là declaredscenario, không observedAsk/tick; currency/geometry/funding/commission khác, không merge im lặng |

Inventory chỉ từ metadata đã có, không chứng thực lại toàn bộ rawFX/Gold hoặc
cho phép dispatch strategy. Fundingtarget còn unknown; không giảm oldfees để
cứu kết quả hoặc gọi một declaredrate là conservative khi chưa có point/mode.

## Hậu kiểm và bước tiếp

Metadata diagnosis0,024s; toàn sourceprobe76,933s wall/25,875s CPU.0network,
0simulation/broker/model,0holdout. Sourceproof/hash/JSONread chiếm lượt này,
không benchmark của nativebacktest và không có lý do GPU/Rust ở đây.
Selector có future-prefix/stale/session negativefixtures; fullsourceprice/
lineage dùng reviewer đã có, chưa independent human/model sign-off.

R010 có thể dùng risk estimator dựa trên **returns đã có**, phù hợp nhánh
volatility-scaling trong nguồn AQR, thay vì mượn ATRfullsession của một rule
khác rồi không có data. Đây là **thiết kế/phiên bản nghiên cứu mới**, chưa chọn
estimator/horizon/stop hoặc nới gate. Trước PnL phải:

1. Pin và chuẩn bị common monthly observations cho EURUSD/Gold/US500, giữ
   source/units/cutoffs/availability/observed-vs-declared sides rõ.
2. Freeze exact 1/3/12 signal hoặc baseline được chọn, volestimator và warmup,
   weights/caps/financing/cost scenarios/denominators; không tự lấy10%voltarget
   paper làm propbudget. Giữ reasons/oldbaseline, không grid tham số.
3. Component declaredscenario trước, native jointaccount/SL/prop/markrisk và
   genuinelyunseen/prospective sau; không cộng annualresetbooks để giả account.

Không resurrect R026 hoặc đóng Goal bằng một feasibility report. C1chưađạt;
continuation tiếp từ data-normalization slice trên, không rerun sourceprobe
không đổi hoặc re-audit accepted41versions.

Private artifact `execution-v1/multiasset-trend-admission-v1`:manifest/source
snapshots,metadata-result,monthly-observations,result/status/events; producer
`diagnose-multiasset-input-v1.py` ở privatecampaignroot. Originalproofs,
quarterseals,protocol và input metadata hashes nằm trong result/manifest.
Process21844/exec10612 đã terminalexit0; không còn worker của sourceprobe.

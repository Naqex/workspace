# R010: kiểm dữ liệu cho xu hướng nhiều tài sản trước strategy mới

Đăng ký sau [R026 continuation](R026-RELATIVE-EQUITY-CONTINUATION-RESULTS-20261108.md).
Đây là source/capability admission, **không numerical strategy outcomes**,
không sửa R009/R053 hoặc claim AQR replication. Goal thuộc campaignv2.

## Vì sao đổi lát nghiên cứu?

| Hướng | Evidence/capability | Quyết định |
|---|---|---|
|R010:multiasset trend/volatility budget|AQR2017method là nhiều markets, excessreturns,1/3/12month và inversevol/portfolio risk; hiện có EURUSD/Gold/US500 nguồn đã dùng|Nhận source-feasibility; chưa khóa signal/horizon/cost/risk recipe|
|R033:cross-sectional FX momentum|BIS366abstract có mechanism, khác carry; chưa đọc full89pages lần này; cần common FXuniverse,funding/currency-conversion/rebalancing|Defer numerical, không dùng abstract10% làm target/edge của project|

Không xem R026fail là lý do retuneclock/side; R010 cũng không tự được nhận
vì literature đẹp. Old US500monthly có32/132eligible sau source correction,
chưa có economic verdict trên input đầy đủ. Phân tích nguyên nhân cụ thể
trước lựa chọn sample/protocol; không bỏ năm/giảm phí để cứu strategy.

## Lát1: reuse metadata đã kiểm, không simulation

- Đọc registered monthly source-only admission result/dailyfacts/inputpins
  ở `execution-v1/us500-monthly-explicit-input-review-v1`, lịch2013–2024 và
  manifest của FX/Gold đã consumed. Bind originals bằng hash, không sửa.
- Phân rã132evaluation-months: thiếu13consecutiveclosepoints, ATR14 cần14full
  cashsessions, futurefillavailability, hoặc nhiều nguyên nhân. Futurefill
  coverage là ex-post diagnostic, không điều kiện biết trước ở signal.
- Inventory scope/units/price semantics/timezone/coverage/sides/quality hiện
  có của3markets; GolddeclaredAsk khác observedBidAsk, funding khác, không
  silently merge thành observedCFDportfolio. Metadata thiếu giữ unknown.
- Output mới `execution-v1/multiasset-trend-admission-v1`, pins/source/log/
  phase timing; source-only,0network/0broker/0model/0simulation,deadline300s.

## Lát2: khả năng dùng quan sát as-of, chỉ sau đăng ký này

Monthly signal không nhất thiết cần đúng một timestamp M1; có thể dùng giá
nguồn đã biết gần cutoff. Đây là **semantics mới cho một strategy tương lai**,
không sửa lại eligibility của frozenR009/R053 hoặc gắn cờ oldbooks thànhpass.

Đo trên canonical source-only US500M1/cashcalendar2013–2024, chưa tính returns:

- Chỉ Bid close cần cho Bid-only signal. Chọn nến nguồn cuối đã hoàn tất
  **trước hoặc tại cutoff cashclose**, cùng ngày/session. Không forward join,
  carriedclose, padding, interpolation hoặc ghép side không dùng tới để loại
  Bid hợp lệ. Ask/fill/execution có contract riêng, không được dùng Bid thay.
- Đóng băng **price-age upper bound120s tính từ sourcebaropen tới cutoff**;
  known-at=sourcebaropen+60s. Đây là bound của observation, không tuyên bố
  biết chính xác timestamp tick cuối trong M1. Không thử thêm nhiều agecaps
  hoặc chọn cap theo PnL. Giữ missing ngoài cap rõ ràng.
- Báo exact/capped/unknown monthly endpoints, đủ13consecutivepoints hay
  không, year/month census và source locators/hashes. Không tái tạo nến thiếu.
  Báo riêng ATRfullsession gating; as-of close không sửa được missingrange.
- Input sparse/unusable vẫn inconclusive trong phần đó. Không triển khai
  bot hoặc nới daily-risk/ATR/completeness gates từ kết quả coverage này.

Trước numerical R010 phải freeze exactrecipe/volestimator/portfolio budget,
cost/financing/currency geometry, signal/fill and mark clocks, quality/data
roles, missing/stop/unknown và tiêu chí. Không lấy equity curves từng account
reset rồi cộng thành một portfolio hoặc nhân riskbudget theo số symbols.
Không holdout2025+, tài khoản/provider mới, paiddata, migration hoặc broker.

## Nguồn đã đọc

[AQR2017PDF](https://www.aqr.com/-/media/AQR/Documents/Insights/Journal-Article/AQR-JPM-Fall-2017.pdf)
Data/strategypp1–2:67markets/fourassetclasses, monthly aggregation of1/3/12month
excessreturn signals, equalrisk/portfolio voltarget. Không tự nhập10%voltarget
của paper thành allowedpropDD hoặc cho rằng spotCFDprice có futurescarry.
[BIS366](https://www.bis.org/publications/working-paper-366-currency-momentum-strategies):
abstract/methodscope only, cần fullmethod trước R033. Sources kiểm08/11;
không tải factorreturns, full benchmarkhistory hoặc source2025+.

# Uncertainty của hai survivors — kế hoạch phân tích trước thống kê

Point estimates của2023/2024 đã xem khi chọn London16–20 và Asia→London; đây
là **conditional exploratory analysis**, không preregistered hypothesis test.
Không mở thêm prices/holdout, không tuning rules hoặc chọn bootstrap theo CI.

Từ coarse sealed-by-hash reports đã cash/count/snapshot review: bốn series
(hai candidates×hai costs), giữ cùng time blocks khi resample để không giả
cost scenarios/candidates độc lập. Mỗi năm là account riêng; pooling chỉ cho
thống kê closed-trade expectancy, không dựng một portfolio/equitycurve liên tục.

- Chỉ closed trades, full timed financing của mỗi trade,0floating cho cả hai
  selected policies/years; sourcepacket/input hashes/report protocol được pin.
- Group realized net/count vào7calendar-day bins từ01/01 mỗi năm; có bins0trade
  và bin cuối ngắn1/2days. Ghi rõ closed-trade outcome, không weeklyequity/DD.
- Circular moving blocks4bins/28days trong từng year, không nối block giữa hai
  annualaccounts.10.000draws, seed42, cùng sampled indices cho mọi series.
  Mỗi draw giữ số bins từng năm; metric sum(net)/(25×sum(closed trades)).
- Report point meanR/trade, empirical2,5%/97,5% quantiles, tradecounts và
  source/panel/exposure assumptions. Không thêm IIDtradeCI hoặc chọnblocklength
  khác sau outcome chỉ để CI dương. Hand fixtures và input rejects trước stats.

CI chỉ mô tả bất định dưới giả định dependence captured bởi4weeks/observed
two-year distribution; regimes dài hơn, tails, sampling/simulation/model error
chưa được hiệu chỉnh. **Không điều chỉnh hết multipletrials/selection**, không
calibratededgeprobability hoặc pass probability; fulltrial history/data coverage
không đủ để ép DSR/PBO/realitycheck. Native tick/prop/forward review giữ owner
riêng. Không auto promote ngay cả nếu lowerquantile>0; nếu includes0 thì evidence
kinh tế chưa tách rõ khỏi noise, cần nghiên cứu/fresh evidence theo đúng gate.

## Kết quả actual — source a98597a

| Bản/cost | Closed trades hai annual books | MeanR/trade | Conditional bootstrap95%intervalR |
|---|---:|---:|---:|
| London reference |519|0,0480|[−0,0143;0,1075]|
| London stress |519|0,0270|[−0,0338;0,0857]|
| Asia reference |454|0,0414|[−0,0798;0,1689]|
| Asia stress |454|0,0175|[−0,1006;0,1406]|

Cả4intervals bao gồm0. Đây chưa là bằng chứng edge bền vững hoặc lý do mua challenge; cũng không chứng minh expectation chính xác bằng0.10.000draws là syntheticresamples, không10.000bài kiểm độc lập, không95%chancewin. Cả hai nativeannualbatches tiếp tục để kiểm execution/risk/time-fit, không đọc2025+ hoặc promote vì coarse dương. Fourbehavior/inputreject tests đạt trước phân tích, actualrun1,6s process wall. Private artifact h1-uncertainty-v1/config.json/result.json dưới campaign execution-v1 giữ report/config/source hashes.

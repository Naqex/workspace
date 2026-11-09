# FX quote-cost fixture: nguồn đủ kiểm, chưa chứng minh edge

Theo [protocol](FX-QUOTE-COST-ADMISSION-PROTOCOL-20261109.md), commit `d9851ee`
trước fetch. Reuse existing Dukascopy1.51.1/cache/native formatter/Fraction
raw decoder. Chỉ 4 giờ EURUSD đã đăng ký; không strategy, lợi nhuận hoặc
broker/model calls. Catalogue vẫn81/58; chưa candidate challenge mới.

## Số đo từ joint quotes

| Ngày / giờ New York | Quote | Phút có quote | Spread p50 / p95 (pip) | Gap nguồn lớn nhất |
|---|---:|---:|---:|---:|
|09/01/2019 16–17|3.535|60/60|0,4 / 0,6|24,728 giây|
|09/01/2019 17–18|2.966|60/60|1,5 / 3,1|19,960 giây|
|13/07/2022 16–17|1.794|60/60|0,5 / 1,1|51,153 giây|
|13/07/2022 17–18|452|58/60|2,2 / 4,6|101,305 giây|

Percentiles theo **số quote**, nearest-rank; không time-weighted. Same-ms
quotes giữ riêng. Gap tính cả đầu/cuối giờ; không giả last price luôn fresh,
forwardfill hoặc kết luận thị trường/broker không có quote chỉ vì feed thiếu.
Bốn giờ/two dates không đại diện mọi ngày, broker hoặc thanh khoản toàn FX.

Kịch bản minh họa giữ spread tại quote +0,5pip commission roundtrip +0,4pip
slippage stress: p95 costproxy trước/sau17h lần lượt **1,5/4,0pip** năm2019
và **2,0/5,5pip** năm2022. Không là actual entry/exit costs, fill/slippage đã
đo hoặc phí quỹ verified. Với EURUSD USDaccount giả định, 0,01lot có pipvalue
0,10USD: 5,5pip tương đương0,55USD; chưa có lệnh/TP hay lợi nhuận trong study.

## Correctness và lineage

- 8.747 joint ticks, 43.735 timestamp/Bid/Ask/volume fields khớp full raw
  Fraction decode; đúng 4 UTC scopes và America/New_York winter/summer.
- Clock/order/grid/noncrossed và exact seals/pins giữ đúng. Không lấy hai
  Open của nến Bid/Ask không đồng thời làm joint spread.
- 8 synthetic checks: arithmetic, nearest-rank, same-ms/edge-gap và invalid
  quotes. 5 mutations raw price/clock/count/hash/authority đều bị chặn.
- Quantiles/costs được đối chiếu lại bằng Fraction trực tiếp trên raw decoded
  ticks. Cùng agent/feed, không independent model/human/broker certification.
- Source4requests/retry0/noholdout; producer2,534s wall, reviewer0,695s/0,625s
  CPU, source+review3,229s. Không gồm research/code/Git; không gọi speedup A/B.
- `progress.json` đã cập nhật `completed_reviewed`; result/review và raw giữ
  nguyên hashes. Không job nền cần đợi hoặc chạy lại dữ liệu cũ.

Private root `execution-v1/fx-quote-cost-fixture-v1/` trong campaign evidence
base; producer/reviewer scripts nằm ở base, manifest pins và source-snapshot
bind protocol/scripts/native/lock/helper/config, mỗi giờ có raw proof/seal.
Result SHA256 `54320fd09f0b52f717a4360a31a20a1ec76244628f6a044d759ea7ce79864c4f`;
reviewer SHA256 `75a2689a3a725dd2c685f1911fb0627957457d5ab885d5f2af837874a4daf5f8`.

## Quyết định và bước tiếp

Giữ fixture làm bằng chứng về **source capacity/cost assumptions**, không
promote một EA/chiến lược. Không tune spread cutoff/entry/TP theo bốn giờ hoặc
coi “né rollover” là đủ có edge. Nếu thiết kế own-code: cần exact entry/exit,
causal quote age, Bid/Ask fills, pending/cancel/SL, exposure và cost stress;
đăng ký trước economics. Không clone NHP/Fury hoặc nhập outcome record họ
thành evidence cho code mình.

[BIS WP836](https://www.bis.org/publications/working-paper-836-fx-spot-and-swap-market-liquidity-spillovers)
hỗ trợ câu hỏi funding liquidity/spot spreads, chưa cung cấp retail alpha.
Các exact NYMA4 versions [đã gác](NY-FX-GAP-SCENARIOS-RESULTS-20261109.md) giữ
nguyên; một quiet-session rule mới nếu gần họ reversion phải ghi related trial,
không independent edge chỉ vì khác giờ hoặc có spread filter.

EIA lane chưa mở economics: [schedule hiện hành](https://www.eia.gov/petroleum/supply/weekly/schedule.php)
chỉ hiển thị exceptions2025/26 trong lượt refresh; [thông cáo29/06/2022](https://www.eia.gov/pressroom/releases/press507.php)
chỉ nói phát hành trong buổi sáng, không exact timestamp. Hai historical PHP
pilot pages không truy cập được bằng web tool. Giữ actual-release/PIT và
USO16:00endpoint unknown; không bulk fetch để vượt gate nguồn.

Bước Goal tiếp: method admission cho một own-code hypothesis có cơ chế rõ và
khác exact negatives; ưu tiên nguồn primary có rule/khả năng kiểm dữ liệu,
không mua thêm bot, grid thresholds hoặc mở lại unchanged batch. Hậu kiểm
lát này không thấy bottleneck cần engine/GPU/framework/skill mới.

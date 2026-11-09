# R067: source history và fixed formation của vàng/bạc

Đăng ký trước history fetch và statistical outcomes. Parent
[source pilot](GOLD-SILVER-SOURCE-RESULTS-20261109.md) đạt một ngày, chưa đủ
formation. Không triển khai hedge/riskwrapper hoặc đọc pairPnL trong lát này.

## Source trước statistics

- Hai formations calendar2018 và2021, mỗi năm01Jan→01Jan năm sau exclusive;
  XAU/XAG × Bid/Ask H1:8exports,96raw month sources. Reuse bốn cachedNov2018
  responses đã kiểm; không fetch lại nếu cache/proof còn đúng.
- Existing provider/package1.51.1/H1 explicit-only helper, UTC/grid0,001,
  volumes millions/round4; source-listed volume0 vẫn giữ. WAF/token-cache off,
  retries0, cumulative transient failure budget1, không retry fail/auth/403/
  429; không thêm năm/tài sản hoặc bỏ tháng thiếu. One writer, CANCEL,
  deadline240s cho source job, mỗi complete export có seal/progress.
- Output mới `execution-v1/gold-silver-history-v1`; pin protocol, producer/
  reviewer/helper/package/runtime/lock và parent result/review trước network.
  Chỉ reuse source pilot nếu original raw hashes còn đúng, không overwrite.
- Full canonical+Fraction integer-delta rawreview cho8exports/96months,
  UTC/order/OHLC/grid/count/side pairing và padding census. Các crossed hours
  phải ghi rõ, không xóa. Year-level data admission tách statistical sampling;
  source còn thiếu thì không tự gọi full joint history admitted.

## Fixed sample và diagnostics

- y=ln(XAU source BidClose),x=ln(XAG source BidClose), không đảo orientation.
  Sample16UTC H1 bar, close known17UTC. Dùng đúng dates của frozen
  `nasdaq_cash_calendar.calendar_for(2018/2021)` /`cash_sessions` như thiết kế
  mẫu business dates, không mô tả calendar đó là giờ mở cửa metals.
- Giữ census mọi ngày định trước. Bid/Ask của cả hai legs phải có timestamp
  đúng và Open/Close không crossed. Thiếu/crossed bất kỳ ngày định trước hoặc
  <240paired observations → sample inconclusive, không drop/asof/fill, không
  thử đổi giờ/calendar sau outcome. Source năm có crossed ở giờ ngoài sample
  vẫn phải báo, không giấu thành "full joint history verified".
- Reuse pinned `fx_pair_formation.diagnose`: Engle–Granger constant/maxlag1/
  autolagNone, OLS y~x+constant. Leg labels cũ của helper phải map tường minh
  gbpusd→xauusd(y),audusd→xagusd(x) khi xuất; không dùng FX sampler/grid.
  Log từ giá nguồn; libraries statsmodels0.15.0/numpy2.5.4/scipy1.18.1/
  pandas3.1.1 trong isolated statistics runtime đã có, không install/update.
- Giữ filter của method: coint p<=0,05, beta0,1..10, residual không degenerate,
  levelsADF không reject và differenceADF reject tại0,05. Đây là prefilter
  nghiên cứu có giới hạn, không chứng minh I(1), edge hoặc pass challenge.
  Chỉ cả hai formations đạt mới ưu tiên đăng ký economic design; một hoặc
  cả hai không đạt thì gác exact pair/formations cho recipe này, không bác bỏ
  mọi quan hệ nonlinear/time-varying hoặc mở pair/lag/window grid.
- Source/sample fixtures trước statistical outcomes. Separate reviewer dùng
  Decimal80log/OLS/residualADF, tolerance1e−11 coefficients/SD và1e−8 tstat.
  P-value/critical curves dùng cùng pinned library, ghi rõ không independent
  inference implementation. Kiểm count/date/source/stat/hash/authority mutations.

Stat output mới `execution-v1/gold-silver-formation-v1`: sample/census/diag/
binding/runtime/packages/source snapshots/result/review/status/events/timing.
Source fullreview phải đạt đúng sampling scope trước stats; deadline60s/stat
job. No returns/account PnL/model/broker calls, no2025+ hoặc provider/account
mới. Không tăng policy count chỉ vì statistical probe; catalogueR067 giữ
source/formation hypothesis. Goal C1/C2 còn active dù một filter được pass.
